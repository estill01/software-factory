from __future__ import annotations

import datetime as dt
import subprocess
import tempfile
from pathlib import Path

import pytest

from software_factory import CoreService, LeaseConflict, RoleConflict, StaleLease, Store


def git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    )
    return process.stdout.strip()


@pytest.fixture()
def factory() -> tuple[Store, CoreService, Path, str, str, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository = root / "repo"
        repository.mkdir()
        git(repository, "init", "-b", "main")
        git(repository, "config", "user.name", "Software Factory Test")
        git(repository, "config", "user.email", "factory@example.invalid")
        (repository / "README.md").write_text("baseline\n")
        git(repository, "add", "README.md")
        git(repository, "commit", "-m", "baseline")
        revision = git(repository, "rev-parse", "HEAD")

        store = Store(root / "state" / "factory.db")
        core = CoreService(store)
        project = core.create_project("project")
        mission = core.create_mission(
            project_id=project,
            title="Build feature",
            objective="Produce a tested feature",
        )
        repository_id = core.register_repository(
            repository,
            project_id=project,
            default_branch="main",
            current_revision=revision,
            workspace_policy={"workspace_root": str(root / "worktrees")},
        )
        yield store, core, repository, repository_id, mission, revision


def make_work(
    core: CoreService,
    mission: str,
    *,
    scope: list[str],
    acceptance_spec: dict | None = None,
    title: str = "feature",
) -> tuple[str, str]:
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description=f"Implement {title}",
    )
    work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="implementation",
        title=title,
        description=title,
        writable_scope=scope,
        acceptance_spec=acceptance_spec,
    )
    core.select_work(work, expected_version=1, selected_by="selector", basis={"reason": "required"})
    return obligation, work


def make_lane(
    core: CoreService,
    repository_id: str,
    mission: str,
    work: str,
    base_revision: str,
    *,
    role: str = "implementer",
    scope: list[str] | None = None,
) -> tuple[str, str, str]:
    workspace = core.create_workspace(
        repository_id=repository_id,
        mission_id=mission,
        work_item_id=work,
        workspace_type="candidate_lane",
        base_revision=base_revision,
        writable_scope=scope or ["src"],
    )
    session = core.create_agent_session(
        mission_id=mission,
        provider="test",
        role=role,
        model="test-model",
    )
    assignment = core.assign_work(
        work_item_id=work,
        agent_session_id=session,
        workspace_id=workspace,
        role=role,
        assignment_scope={"paths": scope or ["src"]},
    )
    return session, assignment, workspace


def run_feature_implementation(
    core: CoreService,
    repository_id: str,
    mission: str,
    work: str,
    session: str,
    assignment: str,
    workspace: str,
    *,
    suffix: str = "",
) -> tuple[str, int, dict]:
    execution = core.queue_execution(
        mission_id=mission,
        execution_type="implementation",
        idempotency_key=f"impl:{work}:{suffix or 'first'}",
        work_item_id=work,
        agent_session_id=session,
        assignment_id=assignment,
        workspace_id=workspace,
        strategy_key=f"write-feature-{suffix or 'first'}",
    )
    generation = core.acquire_leases(
        execution,
        [
            {"kind": "work", "key": work, "mode": "exclusive"},
            {
                "kind": "path",
                "repository_id": repository_id,
                "path": "src",
                "mode": "exclusive",
            },
        ],
    )
    script = (
        "mkdir -p src; "
        f"printf 'VALUE = {1 if not suffix else 2}\\n' > src/feature.py; "
        "git add src/feature.py; "
        f"git commit -m 'feature{suffix}'"
    )
    result = core.run_command(
        execution,
        ["bash", "-lc", script],
        generation=generation,
        timeout_seconds=60,
    )
    return execution, generation, result


def test_real_workspace_observed_execution_revision_bound_qa_and_acceptance(factory) -> None:
    store, core, _, repository_id, mission, base = factory
    acceptance = {
        "candidate": [
            {"type": "command", "command": ["python", "-m", "py_compile", "src/feature.py"]},
            {"type": "independent_review", "role": "independent_reviewer"},
        ]
    }
    _, work = make_work(core, mission, scope=["src"], acceptance_spec=acceptance)
    implementer, assignment, workspace = make_lane(
        core, repository_id, mission, work, base, scope=["src"]
    )
    execution, _, observed = run_feature_implementation(
        core, repository_id, mission, work, implementer, assignment, workspace
    )
    assert observed["status"] == "succeeded"
    assert observed["changed_files"] == ["src/feature.py"]
    assert core.artifacts.read(observed["stderr_artifact_id"]) == b""

    submitted = core.submit_candidate(execution, expected_work_version=2)
    requirements = submitted["requirements"]
    command_req = next(row for row in requirements if row["qa_type"] == "command")
    review_req = next(row for row in requirements if row["qa_type"] == "independent_review")
    qa = core.run_qa_command(command_req["id"])
    assert qa["passed"] is True

    reviewer = core.create_agent_session(
        mission_id=mission,
        provider="test",
        role="independent_reviewer",
    )
    review = core.record_independent_review(
        review_req["id"],
        reviewer_session_id=reviewer,
        disposition="accept",
    )
    assert review["disposition"] == "accept"
    accepted = core.accept_candidate(work, expected_work_version=3)
    assert accepted["qa_status"] == "passed"
    assert accepted["acceptance_status"] == "candidate_accepted"
    assert accepted["integrated_revision"] is None
    assert store.verify_event_chain(mission)["valid"] is True


def test_hierarchical_path_leases_allow_disjoint_work_and_reject_conflicts(factory) -> None:
    _, core, _, repository_id, mission, base = factory
    _, first = make_work(core, mission, scope=["src"], title="first")
    _, second = make_work(core, mission, scope=["docs"], title="second")
    _, conflict = make_work(core, mission, scope=["src/api"], title="conflict")
    lanes = [
        make_lane(core, repository_id, mission, first, base, scope=["src"]),
        make_lane(core, repository_id, mission, second, base, scope=["docs"]),
        make_lane(core, repository_id, mission, conflict, base, scope=["src/api"]),
    ]
    executions = []
    for work, (session, assignment, workspace) in zip((first, second, conflict), lanes):
        executions.append(
            core.queue_execution(
                mission_id=mission,
                execution_type="implementation",
                idempotency_key=f"lease:{work}",
                work_item_id=work,
                agent_session_id=session,
                assignment_id=assignment,
                workspace_id=workspace,
            )
        )
    core.acquire_leases(
        executions[0],
        [{"kind": "path", "repository_id": repository_id, "path": "src", "mode": "write"}],
    )
    core.acquire_leases(
        executions[1],
        [{"kind": "path", "repository_id": repository_id, "path": "docs", "mode": "write"}],
    )
    with pytest.raises(LeaseConflict):
        core.acquire_leases(
            executions[2],
            [{"kind": "path", "repository_id": repository_id, "path": "src/api", "mode": "write"}],
        )


def test_expired_agent_is_fenced_recovered_and_reassigned(factory) -> None:
    store, core, _, repository_id, mission, base = factory
    obligation, work = make_work(core, mission, scope=["src"])
    session, assignment, workspace = make_lane(
        core, repository_id, mission, work, base, scope=["src"]
    )
    execution = core.queue_execution(
        mission_id=mission,
        execution_type="implementation",
        idempotency_key="lost:first",
        work_item_id=work,
        obligation_id=obligation,
        agent_session_id=session,
        assignment_id=assignment,
        workspace_id=workspace,
    )
    generation = core.acquire_leases(
        execution,
        [{"kind": "work", "key": work, "mode": "exclusive"}],
    )
    expired = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat()
    with store.transaction() as db:
        db.execute("UPDATE leases SET expires_at=? WHERE owner_execution_id=?", (expired, execution))
    assert core.recover_expired_leases(mission_id=mission) == [execution]
    assert store.one("SELECT status FROM executions WHERE id=?", (execution,))["status"] == "abandoned"
    assert store.one("SELECT status FROM work_assignments WHERE id=?", (assignment,))["status"] == "expired"
    assert store.one("SELECT observed_status FROM agent_sessions WHERE id=?", (session,))["observed_status"] == "lost"
    assert store.one("SELECT execution_status FROM work_items WHERE id=?", (work,))["execution_status"] == "abandoned"
    assert store.one("SELECT status FROM obligations WHERE id=?", (obligation,))["status"] == "open"
    with pytest.raises(StaleLease):
        core.complete_external_execution(execution, generation=generation, result={"late": True}, succeeded=True)

    replacement = core.create_agent_session(
        mission_id=mission, provider="test", role="implementer"
    )
    replacement_assignment = core.assign_work(
        work_item_id=work,
        agent_session_id=replacement,
        workspace_id=workspace,
        role="implementer",
        assignment_scope={"paths": ["src"]},
    )
    replacement_execution = core.queue_execution(
        mission_id=mission,
        execution_type="implementation",
        idempotency_key="lost:replacement",
        work_item_id=work,
        obligation_id=obligation,
        agent_session_id=replacement,
        assignment_id=replacement_assignment,
        workspace_id=workspace,
    )
    assert core.acquire_leases(
        replacement_execution,
        [{"kind": "work", "key": work, "mode": "exclusive"}],
    ) >= 1


def test_candidate_change_stales_prior_qa(factory) -> None:
    store, core, _, repository_id, mission, base = factory
    acceptance = {"candidate": [{"type": "command", "command": ["python", "-m", "py_compile", "src/feature.py"]}]}
    _, work = make_work(core, mission, scope=["src"], acceptance_spec=acceptance)
    session, assignment, workspace = make_lane(core, repository_id, mission, work, base)
    first_execution, _, _ = run_feature_implementation(
        core, repository_id, mission, work, session, assignment, workspace
    )
    first = core.submit_candidate(first_execution, expected_work_version=2)
    old_requirement = first["requirements"][0]
    assert core.run_qa_command(old_requirement["id"])["passed"] is True

    replacement_session = core.create_agent_session(
        mission_id=mission, provider="test", role="implementer"
    )
    replacement_assignment = core.assign_work(
        work_item_id=work,
        agent_session_id=replacement_session,
        workspace_id=workspace,
        role="implementer",
        assignment_scope={"paths": ["src"]},
    )
    second_execution, _, _ = run_feature_implementation(
        core,
        repository_id,
        mission,
        work,
        replacement_session,
        replacement_assignment,
        workspace,
        suffix="-v2",
    )
    second = core.submit_candidate(second_execution, expected_work_version=3)
    assert second["revision"] != first["revision"]
    assert store.one("SELECT status FROM qa_requirements WHERE id=?", (old_requirement["id"],))["status"] == "stale"
    assert any(row["candidate_revision"] == second["revision"] for row in second["requirements"])


def test_implementer_cannot_self_review(factory) -> None:
    _, core, _, repository_id, mission, base = factory
    acceptance = {"candidate": [{"type": "independent_review", "role": "independent_reviewer"}]}
    _, work = make_work(core, mission, scope=["src"], acceptance_spec=acceptance)
    implementer, assignment, workspace = make_lane(core, repository_id, mission, work, base)
    execution, _, _ = run_feature_implementation(
        core, repository_id, mission, work, implementer, assignment, workspace
    )
    submitted = core.submit_candidate(execution, expected_work_version=2)
    requirement = submitted["requirements"][0]
    with pytest.raises(RoleConflict):
        core.record_independent_review(
            requirement["id"], reviewer_session_id=implementer, disposition="accept"
        )
