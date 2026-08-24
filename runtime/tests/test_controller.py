from __future__ import annotations

import datetime as dt
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from software_factory import (
    CoreService,
    DeterministicProvider,
    InvalidTransition,
    LeaseConflict,
    ProcessProvider,
    ProviderObservation,
    ProviderRegistry,
    ProviderRequest,
    StaleLease,
    Store,
)
from software_factory.schema import MIGRATIONS, migration_sql
from software_factory.util import digest_bytes, utc_now

CALLBACK_TOKEN = "factory-test-callback-token"


@pytest.fixture(autouse=True)
def _stable_callback_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "software_factory.controller.secrets.token_urlsafe",
        lambda _bytes: CALLBACK_TOKEN,
    )


def git(repo: Path, *args: str) -> str:
    import subprocess

    process = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return process.stdout.strip()


def make_runtime(
    root: Path,
    provider: DeterministicProvider,
    *,
    resource_limits: dict[str, int] | None = None,
) -> tuple[Store, CoreService, str, str, str, str]:
    repository = root / "repo"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "Software Factory Test")
    git(repository, "config", "user.email", "factory@example.invalid")
    (repository / "README.md").write_text("baseline\n", encoding="utf-8")
    git(repository, "add", "README.md")
    git(repository, "commit", "-m", "baseline")
    revision = git(repository, "rev-parse", "HEAD")

    store = Store(root / "state" / "factory.db")
    providers = ProviderRegistry()
    providers.register("deterministic", provider)
    core = CoreService(store, providers=providers, default_provider="deterministic")
    project = core.create_project("project")
    mission = core.create_mission(
        project_id=project,
        title="Build capability",
        objective="Produce an independently verified capability",
        resource_limits=resource_limits,
    )
    repository_id = core.register_repository(
        repository,
        project_id=project,
        default_branch="main",
        current_revision=revision,
        workspace_policy={"workspace_root": str(root / "worktrees")},
    )
    return store, core, project, mission, repository_id, revision


def add_selected_work(
    core: CoreService,
    mission: str,
    repository_id: str,
    *,
    title: str,
    scope: list[str],
    priority: int = 0,
) -> tuple[str, str]:
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description=f"Implement {title}",
        priority=priority,
    )
    work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        repository_id=repository_id,
        work_type="implementation",
        title=title,
        description=f"Implement {title} end to end",
        writable_scope=scope,
        priority=priority,
        provider_key="deterministic",
        acceptance_spec={
            "candidate": [{"type": "command", "command": ["git", "status", "--porcelain=v1"]}]
        },
    )
    core.select_work(
        work,
        expected_version=1,
        selected_by="selector",
        basis={"reason": "required capability"},
    )
    return obligation, work


def test_controller_dispatches_maximal_disjoint_set_and_fences_conflict() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, api = add_selected_work(
            core, mission, repository_id, title="api", scope=["src/api"], priority=30
        )
        _, docs = add_selected_work(
            core, mission, repository_id, title="docs", scope=["docs"], priority=20
        )
        _, conflict = add_selected_work(
            core, mission, repository_id, title="service", scope=["src"], priority=10
        )

        tick = core.tick_mission(mission)

        assert {item["work_item_id"] for item in tick["dispatches"]} == {api, docs}
        assert len(provider.requests) == 2
        assert tick["posture"]["action"] == "wait_for_active_work"
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (api,))[
                "execution_status"
            ]
            == "running"
        )
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (docs,))[
                "execution_status"
            ]
            == "running"
        )
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (conflict,))[
                "execution_status"
            ]
            == "not_started"
        )
        sessions = store.all(
            "SELECT id FROM agent_sessions WHERE mission_id=? AND observed_status='active'",
            (mission,),
        )
        assert len(sessions) == 2
        assert len({request.assignment_id for request in provider.requests}) == 2
        assert len(store.all("SELECT id FROM leases WHERE status='active'")) == 4


def test_concurrent_dispatchers_create_one_execution_and_one_live_workspace() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="race", scope=["src"])
        barrier = threading.Barrier(2)
        results: list[dict[str, object]] = []
        errors: list[Exception] = []

        def run() -> None:
            try:
                barrier.wait(timeout=5)
                results.append(core.dispatch_work(work))
            except Exception as exc:  # the losing dispatcher must fail closed
                errors.append(exc)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidTransition)
        assert (
            len(
                store.all(
                    """SELECT id FROM executions WHERE work_item_id=?
                   AND status IN ('queued','dispatching','leased','running','verifying')""",
                    (work,),
                )
            )
            == 1
        )
        assert (
            len(
                store.all(
                    """SELECT id FROM workspaces WHERE work_item_id=?
                   AND status IN ('creating','ready','active','frozen','retained')""",
                    (work,),
                )
            )
            == 1
        )


def test_parallel_limit_is_atomic_across_disjoint_concurrent_dispatchers() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(
            Path(directory), provider, resource_limits={"max_parallel": 1}
        )
        _, first = add_selected_work(
            core, mission, repository_id, title="first", scope=["src/first"]
        )
        _, second = add_selected_work(
            core, mission, repository_id, title="second", scope=["src/second"]
        )
        barrier = threading.Barrier(2)
        results: list[dict[str, object]] = []
        errors: list[Exception] = []

        def run(work_id: str) -> None:
            try:
                barrier.wait(timeout=5)
                results.append(core.dispatch_work(work_id))
            except Exception as exc:  # the losing reservation must fail closed
                errors.append(exc)

        threads = [
            threading.Thread(target=run, args=(first,)),
            threading.Thread(target=run, args=(second,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidTransition)
        assert "parallel execution limit" in str(errors[0])
        assert len(provider.requests) == 1
        assert (
            store.scalar(
                """SELECT COUNT(*) FROM executions WHERE mission_id=?
                   AND status IN ('queued','dispatching','leased','running','verifying')""",
                (mission,),
            )
            == 1
        )


def test_resource_policy_bounds_tick_and_survives_runtime_restart() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(
            Path(directory),
            provider,
            resource_limits={
                "max_parallel": 1,
                "max_dispatch_per_tick": 2,
                "max_attempts_per_work": 2,
            },
        )
        _, first = add_selected_work(
            core, mission, repository_id, title="first", scope=["src/first"], priority=2
        )
        _, second = add_selected_work(
            core, mission, repository_id, title="second", scope=["src/second"], priority=1
        )

        tick = core.tick_mission(mission, max_dispatch=20)

        assert [item["work_item_id"] for item in tick["dispatches"]] == [first]
        assert tick["scheduling_policy"] == {
            "max_parallel": 1,
            "max_dispatch_per_tick": 2,
            "max_attempts_per_work": 2,
        }
        assert tick["requested_dispatch_limit"] == 2
        assert tick["posture"]["action"] == "wait_for_active_work"
        assert tick["posture"]["capacity_remaining"] == 0

        restarted = CoreService(
            store,
            providers=core.providers,
            default_provider="deterministic",
        )
        after_restart = restarted.next_action(mission)
        assert after_restart["action"] == "wait_for_active_work"
        assert after_restart["scheduling_policy"]["max_parallel"] == 1

        request = provider.requests[0]
        restarted.accept_provider_callback(
            request.execution_id,
            token=CALLBACK_TOKEN,
            generation=request.lease_generation,
            succeeded=True,
            result={"candidate": first},
        )
        resumed = restarted.tick_mission(mission)
        assert [item["work_item_id"] for item in resumed["dispatches"]] == [second]
        assert len(provider.requests) == 2


def test_attempt_budget_stops_repeat_dispatch_and_leaves_obligation_open() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(
            Path(directory), provider, resource_limits={"max_attempts_per_work": 1}
        )
        obligation, work = add_selected_work(
            core, mission, repository_id, title="bounded", scope=["src"]
        )
        dispatch = core.dispatch_work(work, lease_ttl_seconds=60)
        expired = (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)).isoformat()
        with store.transaction() as db:
            db.execute(
                "UPDATE leases SET expires_at=? WHERE owner_execution_id=?",
                (expired, dispatch["execution_id"]),
            )
        assert core.controller.recover_expired_provider_executions(mission_id=mission)[0] == [
            dispatch["execution_id"]
        ]

        posture = core.next_action(mission)

        assert posture["action"] == "diagnose_reflect_or_replan"
        assert posture["budget_exhausted_work_item_ids"] == [work]
        assert obligation in posture["obligation_ids"]
        assert store.one("SELECT status FROM obligations WHERE id=?", (obligation,))["status"] == (
            "in_progress"
        )
        with pytest.raises(InvalidTransition, match="attempt budget is exhausted"):
            core.dispatch_work(work)
        assert len(provider.requests) == 1


def test_exhausted_conflicting_work_does_not_hide_useful_safe_frontier() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(
            Path(directory), provider, resource_limits={"max_attempts_per_work": 1}
        )
        _, exhausted = add_selected_work(
            core,
            mission,
            repository_id,
            title="exhausted",
            scope=["src/shared"],
            priority=20,
        )
        _, useful = add_selected_work(
            core,
            mission,
            repository_id,
            title="useful",
            scope=["src/shared"],
            priority=10,
        )
        first = core.dispatch_work(exhausted, lease_ttl_seconds=60)
        expired = (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)).isoformat()
        with store.transaction() as db:
            db.execute(
                "UPDATE leases SET expires_at=? WHERE owner_execution_id=?",
                (expired, first["execution_id"]),
            )
        core.controller.recover_expired_provider_executions(mission_id=mission)

        assert [row["id"] for row in core.ready_work(mission)] == [useful]
        posture = core.next_action(mission)
        assert posture["action"] == "dispatch_ready_work"
        assert posture["work_item_ids"] == [useful]
        assert posture["budget_exhausted_work_item_ids"] == [exhausted]

        resumed = core.tick_mission(mission)
        assert [item["work_item_id"] for item in resumed["dispatches"]] == [useful]
        assert len(provider.requests) == 2


def test_provider_callback_is_generation_fenced_single_use_and_atomic() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="callback", scope=["src"])
        dispatch = core.tick_mission(mission)["dispatches"][0]

        with pytest.raises(InvalidTransition, match="token"):
            core.accept_provider_callback(
                dispatch["execution_id"],
                token="wrong-token",
                generation=dispatch["generation"],
                succeeded=True,
                result={"commit": "candidate"},
            )
        assert (
            store.one(
                "SELECT status FROM provider_callbacks WHERE execution_id=?",
                (dispatch["execution_id"],),
            )["status"]
            == "pending"
        )
        with pytest.raises(StaleLease, match="generation"):
            core.accept_provider_callback(
                dispatch["execution_id"],
                token=CALLBACK_TOKEN,
                generation=dispatch["generation"] + 1,
                succeeded=True,
                result={"commit": "candidate"},
            )
        assert (
            store.one(
                "SELECT status FROM provider_callbacks WHERE execution_id=?",
                (dispatch["execution_id"],),
            )["status"]
            == "pending"
        )

        completed = core.accept_provider_callback(
            dispatch["execution_id"],
            token=CALLBACK_TOKEN,
            generation=dispatch["generation"],
            succeeded=True,
            result={"commit": "candidate"},
        )

        assert completed["status"] == "succeeded"
        assert (
            store.one(
                "SELECT status FROM provider_callbacks WHERE execution_id=?", (completed["id"],)
            )["status"]
            == "used"
        )
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (work,))[
                "execution_status"
            ]
            == "submitted"
        )
        assert (
            store.one(
                "SELECT status FROM work_assignments WHERE id=?", (dispatch["assignment_id"],)
            )["status"]
            == "completed"
        )
        assert (
            store.one(
                "SELECT observed_status FROM agent_sessions WHERE id=?",
                (dispatch["agent_session_id"],),
            )["observed_status"]
            == "idle"
        )
        with pytest.raises(InvalidTransition, match="not pending"):
            core.accept_provider_callback(
                completed["id"],
                token=CALLBACK_TOKEN,
                generation=dispatch["generation"],
                succeeded=True,
                result={"duplicate": True},
            )


def test_provider_poll_completion_retains_output_as_content_addressed_evidence() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="poll", scope=["src"])
        dispatch = core.tick_mission(mission)["dispatches"][0]
        provider.set_observation(
            dispatch["execution_id"],
            ProviderObservation(
                status="succeeded",
                result={"commit": "abc123"},
                usage={"input_tokens": 100, "output_tokens": 20},
                stdout=b"implementation complete\n",
                stderr=b"",
            ),
        )

        updates = core.poll_provider_executions(mission)

        assert updates == [{"execution_id": dispatch["execution_id"], "status": "succeeded"}]
        execution = store.one("SELECT * FROM executions WHERE id=?", (dispatch["execution_id"],))
        assert execution["status"] == "succeeded"
        assert core.artifacts.read(execution["stdout_artifact_id"]) == b"implementation complete\n"
        assert core.artifacts.read(execution["stderr_artifact_id"]) == b""
        assert '"input_tokens":100' in execution["usage_json"]
        assert (
            store.one(
                "SELECT status FROM provider_callbacks WHERE execution_id=?", (execution["id"],)
            )["status"]
            == "used"
        )
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (work,))[
                "execution_status"
            ]
            == "submitted"
        )


def test_dispatch_failure_is_observed_without_closing_obligation_or_crashing_tick() -> None:
    def fail(_: ProviderRequest) -> ProviderObservation:
        raise OSError("provider unavailable")

    provider = DeterministicProvider(fail)
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        obligation, work = add_selected_work(
            core, mission, repository_id, title="failure", scope=["src"]
        )

        tick = core.tick_mission(mission)

        assert tick["dispatches"] == []
        assert tick["dispatch_blockers"][0]["error_type"] == "ProviderError"
        execution = store.one("SELECT * FROM executions WHERE work_item_id=?", (work,))
        assert execution["status"] == "abandoned"
        assert "provider unavailable" in execution["error_json"]
        assert (
            store.one("SELECT execution_status FROM work_items WHERE id=?", (work,))[
                "execution_status"
            ]
            == "failed"
        )
        assert (
            store.one("SELECT status FROM obligations WHERE id=?", (obligation,))["status"]
            == "in_progress"
        )
        assert tick["generated_problem_solving_work"]
        assert tick["posture"]["action"] == "dispatch_ready_work"


def test_expired_dispatch_revokes_callback_and_rejects_late_result() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="expiry", scope=["src"])
        dispatch = core.dispatch_work(work, lease_ttl_seconds=60)
        expired = (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)).isoformat()
        with store.transaction() as db:
            db.execute(
                "UPDATE leases SET expires_at=? WHERE owner_execution_id=?",
                (expired, dispatch["execution_id"]),
            )

        recovered = core.tick_mission(mission)

        assert dispatch["execution_id"] in recovered["recovered_execution_ids"]
        assert recovered["recovered_provider_cancellations"] == [
            {"execution_id": dispatch["execution_id"], "status": "cancelled"}
        ]
        assert (
            store.one(
                "SELECT status FROM provider_callbacks WHERE execution_id=?",
                (dispatch["execution_id"],),
            )["status"]
            == "revoked"
        )
        with pytest.raises(InvalidTransition, match="not pending"):
            core.accept_provider_callback(
                dispatch["execution_id"],
                token=CALLBACK_TOKEN,
                generation=dispatch["generation"],
                succeeded=True,
                result={"late": True},
            )
        replacement = store.one(
            """SELECT id FROM executions WHERE work_item_id=? AND id<>?\n               ORDER BY created_at DESC LIMIT 1""",
            (work, dispatch["execution_id"]),
            required=False,
        )
        assert replacement is not None


def test_failed_provider_cancellation_retains_expired_authority_and_blocks_overlap() -> None:
    class RefusesCancellation(DeterministicProvider):
        def __init__(self) -> None:
            super().__init__()
            self.cancel_attempts = 0

        def cancel(self, handle):
            self.cancel_attempts += 1
            raise RuntimeError("provider still running")

    provider = RefusesCancellation()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, first = add_selected_work(
            core, mission, repository_id, title="first", scope=["src/first"]
        )
        _, second = add_selected_work(
            core, mission, repository_id, title="second", scope=["src/second"]
        )
        dispatch = core.dispatch_work(first, lease_ttl_seconds=60)
        expired = (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)).isoformat()
        with store.transaction() as db:
            db.execute(
                "UPDATE leases SET expires_at=? WHERE owner_execution_id=?",
                (expired, dispatch["execution_id"]),
            )

        with pytest.raises(LeaseConflict, match="expired leases require"):
            core.dispatch_work(second)

        assert provider.cancel_attempts == 1
        assert (
            store.one("SELECT status FROM executions WHERE id=?", (dispatch["execution_id"],))[
                "status"
            ]
            == "running"
        )
        assert (
            store.one(
                "SELECT status FROM leases WHERE owner_execution_id=?", (dispatch["execution_id"],)
            )["status"]
            == "active"
        )
        assert len(provider.requests) == 1


def test_existing_schema_upgrades_transactionally_from_v6_to_v7() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "factory.db"
        db = sqlite3.connect(path)
        try:
            db.execute(
                """CREATE TABLE schema_migrations(
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )"""
            )
            for migration in MIGRATIONS[:6]:
                sql = migration_sql(migration)
                checksum = digest_bytes(sql.encode("utf-8"))
                db.executescript("BEGIN IMMEDIATE;\n" + sql + "\nCOMMIT;")
                db.execute(
                    """INSERT INTO schema_migrations(version,name,sha256,applied_at)
                       VALUES(?,?,?,?)""",
                    (migration.version, migration.name, checksum, utc_now()),
                )
                db.commit()
        finally:
            db.close()

        store = Store(path)
        assert store.health()["schema_version"] == MIGRATIONS[-1].version
        columns = {row["name"] for row in store.all("PRAGMA table_info(executions)")}
        assert {"provider_key", "provider_handle_json", "dispatch_attempts"} <= columns
        indexes = {row["name"] for row in store.all("PRAGMA index_list(workspaces)")}
        assert "one_live_workspace_per_work" in indexes


def test_process_provider_is_restart_observable_and_returns_bounded_output() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        provider = ProcessProvider(
            root / "provider",
            lambda _: [sys.executable, "-c", "print('provider-ok')"],
        )
        request = ProviderRequest(
            execution_id="exe_test",
            mission_id="mis_test",
            work_item_id="wrk_test",
            assignment_id="asn_test",
            workspace_id="",
            workspace_path=root,
            lease_generation=1,
            role="implementer",
            prompt="",
        )
        initial = provider.dispatch(request)
        assert initial.status == "running"
        observation = initial
        deadline = time.monotonic() + 10
        while observation.status == "running" and time.monotonic() < deadline:
            time.sleep(0.02)
            observation = provider.poll(initial.handle)
        assert observation.status == "succeeded"
        assert observation.stdout == b"provider-ok\n"
        assert observation.stderr == b""
        with pytest.raises(ValueError, match="escapes root"):
            provider.poll(
                {
                    **dict(initial.handle),
                    "status_path": str(root / "outside-status.json"),
                }
            )


def test_process_provider_proves_group_exit_before_terminal_cancellation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ready = root / "ready"
        post_cancel_effect = root / "post-cancel-effect"
        command = (
            "import signal,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"Path({str(ready)!r}).write_text('ready'); "
            "time.sleep(0.6); "
            f"Path({str(post_cancel_effect)!r}).write_text('effect')"
        )
        provider = ProcessProvider(
            root / "provider",
            lambda _: [sys.executable, "-c", command],
            termination_grace_seconds=0.05,
            kill_grace_seconds=1.0,
        )
        initial = provider.dispatch(
            ProviderRequest(
                execution_id="exe_cancel_proof",
                mission_id="mis_cancel_proof",
                work_item_id="wrk_cancel_proof",
                assignment_id="asn_cancel_proof",
                workspace_id="",
                workspace_path=root,
                lease_generation=1,
                role="implementer",
                prompt="",
            )
        )
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()

        cancelled = provider.cancel(initial.handle)

        assert cancelled.status == "cancelled"
        assert cancelled.result == {
            "process_group_id": initial.handle["pid"],
            "signal": "SIGKILL",
            "escalated": True,
        }
        time.sleep(0.7)
        assert not post_cancel_effect.exists()
