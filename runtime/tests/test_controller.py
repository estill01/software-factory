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
    ProcessProvider,
    ProviderObservation,
    ProviderRegistry,
    ProviderRequest,
    StaleLease,
    Store,
)
from software_factory.schema import MIGRATIONS, migration_sql
from software_factory.util import digest_bytes, utc_now


def git(repo: Path, *args: str) -> str:
    import subprocess

    process = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return process.stdout.strip()


def make_runtime(
    root: Path,
    provider: DeterministicProvider,
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


def test_provider_callback_is_generation_fenced_single_use_and_atomic() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="callback", scope=["src"])
        dispatch = core.tick_mission(mission)["dispatches"][0]
        request = provider.requests[0]

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
                token=request.callback_token,
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
            token=request.callback_token,
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
                token=request.callback_token,
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
        assert tick["posture"]["action"] == "diagnose_reflect_or_replan"


def test_expired_dispatch_revokes_callback_and_rejects_late_result() -> None:
    provider = DeterministicProvider()
    with tempfile.TemporaryDirectory() as directory:
        store, core, _, mission, repository_id, _ = make_runtime(Path(directory), provider)
        _, work = add_selected_work(core, mission, repository_id, title="expiry", scope=["src"])
        dispatch = core.dispatch_work(work, lease_ttl_seconds=60)
        request = provider.requests[0]
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
                token=request.callback_token,
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
        assert store.health()["schema_version"] == 7
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
            callback_token="token",
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
