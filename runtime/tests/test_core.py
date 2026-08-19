from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path
from typing import Any

import pytest

from software_factory import (
    AuthorityDenied,
    CommandEnvelope,
    CoreService,
    EvidenceInvalid,
    InvalidTransition,
    StaleState,
    Store,
    StoreError,
)
from software_factory.util import canonical_json, new_id, utc_now


@pytest.fixture()
def runtime() -> tuple[Store, CoreService, str, str]:
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "factory.db")
        core = CoreService(store)
        project = core.create_project("test")
        mission = core.create_mission(
            project_id=project,
            title="Implement capability",
            objective="Produce a verified operator-visible capability",
        )
        yield store, core, project, mission


def add_session(
    store: Store,
    mission_id: str,
    *,
    role: str,
    session_id: str | None = None,
) -> str:
    session_id = session_id or new_id("ses")
    with store.transaction() as db:
        db.execute(
            """INSERT INTO agent_sessions(
                id,mission_id,provider,role,desired_status,observed_status,
                started_at,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                session_id,
                mission_id,
                "test",
                role,
                "running",
                "active",
                utc_now(),
                "{}",
            ),
        )
    return session_id


def add_execution(
    store: Store,
    mission_id: str,
    *,
    execution_type: str,
    status: str = "succeeded",
    session_id: str | None = None,
    result: dict[str, Any] | None = None,
    work_item_id: str | None = None,
    execution_id: str | None = None,
) -> str:
    execution_id = execution_id or new_id("exe")
    with store.transaction() as db:
        db.execute(
            """INSERT INTO executions(
                id,mission_id,work_item_id,agent_session_id,execution_type,status,
                idempotency_key,result_json,created_at,started_at,finished_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                execution_id,
                mission_id,
                work_item_id,
                session_id,
                execution_type,
                status,
                f"test:{execution_id}",
                canonical_json(result or {}),
                utc_now(),
                utc_now(),
                utc_now(),
            ),
        )
    return execution_id


def test_migrations_are_versioned_and_database_is_healthy(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, _, _, _ = runtime
    migrations = store.all("SELECT version,name,sha256 FROM schema_migrations ORDER BY version")
    assert [row["version"] for row in migrations] == [1, 2, 3, 4, 5]
    assert all(len(row["sha256"]) == 64 for row in migrations)
    assert store.health()["integrity"] == "ok"


def test_event_chain_and_authority_non_widening(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    parent = core.add_authority(
        mission_id=mission,
        source_type="direct_user",
        source_ref="request-1",
        effect_classes=["read/observe", "repository_write"],
        scope={"repository": "repo", "paths": ["src", "tests"]},
    )
    child = core.add_authority(
        mission_id=mission,
        source_type="delegation",
        source_ref="delegate-1",
        effect_classes=["read/observe"],
        scope={"repository": "repo", "paths": ["src/component"]},
        parent_id=parent,
    )
    assert child.startswith("auth_")
    with pytest.raises(StoreError, match="widen scope"):
        core.add_authority(
            mission_id=mission,
            source_type="delegation",
            source_ref="delegate-bad-scope",
            effect_classes=["repository_write"],
            scope={"repository": "repo", "paths": ["outside"]},
            parent_id=parent,
        )
    with pytest.raises(StoreError, match="widen effect"):
        core.add_authority(
            mission_id=mission,
            source_type="delegation",
            source_ref="delegate-bad-class",
            effect_classes=["release"],
            scope={"repository": "repo", "paths": ["src"]},
            parent_id=parent,
        )
    assert store.verify_event_chain(mission)["valid"] is True
    mission_row = store.one("SELECT * FROM missions WHERE id=?", (mission,))
    assert mission_row["state_version"] == 3
    assert len(mission_row["authority_root"]) == 64


def test_command_failure_is_durable_and_idempotency_is_bound(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    authority = core.add_authority(
        mission_id=mission,
        source_type="direct_user",
        source_ref="request",
        effect_classes=["repository_write"],
        scope={"repository": "repo", "paths": ["src"]},
    )
    mission_version = store.one("SELECT state_version FROM missions WHERE id=?", (mission,))[
        "state_version"
    ]
    envelope = CommandEnvelope(
        command_id=new_id("cmd"),
        idempotency_key="same-key",
        actor_id="agent",
        authority_record_id=authority,
        mission_id=mission,
        target_type="mission",
        target_id=mission,
        expected_version=mission_version,
        effect_class="repository_write",
        payload={"operation": "write"},
        requested_scope={"repository": "repo", "paths": ["src/file.py"]},
    )

    def fail(_: Any) -> dict[str, Any]:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        store.command(envelope, fail)
    record = store.one("SELECT * FROM commands WHERE id=?", (envelope.command_id,))
    assert record["status"] == "failed"
    assert "boom" in record["error_json"]
    with pytest.raises(StoreError, match="previously failed"):
        store.command(envelope, lambda _: {"unexpected": True})
    changed = CommandEnvelope(
        **{**envelope.__dict__, "payload": {"operation": "different"}}
    )
    with pytest.raises(StoreError, match="different command"):
        store.command(changed, lambda _: {"unexpected": True})


def test_command_enforces_authority_scope_and_expected_version(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    authority = core.add_authority(
        mission_id=mission,
        source_type="direct_user",
        source_ref="request",
        effect_classes=["repository_write"],
        scope={"repository": "repo", "paths": ["src"]},
    )
    current = store.one("SELECT state_version FROM missions WHERE id=?", (mission,))[
        "state_version"
    ]
    bad_scope = CommandEnvelope(
        command_id=new_id("cmd"),
        idempotency_key="scope",
        actor_id="agent",
        authority_record_id=authority,
        mission_id=mission,
        target_type="mission",
        target_id=mission,
        expected_version=current,
        effect_class="repository_write",
        requested_scope={"repository": "repo", "paths": ["docs"]},
    )
    with pytest.raises(AuthorityDenied, match="scope"):
        store.command(bad_scope, lambda _: {})
    stale = CommandEnvelope(
        command_id=new_id("cmd"),
        idempotency_key="stale",
        actor_id="agent",
        authority_record_id=authority,
        mission_id=mission,
        target_type="mission",
        target_id=mission,
        expected_version=current - 1,
        effect_class="repository_write",
        requested_scope={"repository": "repo", "paths": ["src"]},
    )
    with pytest.raises(StaleState):
        store.command(stale, lambda _: {})


def test_attempt_failure_does_not_close_obligation(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    capability = core.add_capability(
        mission_id=mission,
        name="Feature",
        description="Feature works end to end",
    )
    obligation = core.add_obligation(
        mission_id=mission,
        capability_id=capability,
        obligation_type="implement",
        description="Implement feature",
    )
    row = store.one("SELECT * FROM obligations WHERE id=?", (obligation,))
    assert row["status"] == "open"
    action = core.next_action(mission)
    assert action["action"] == "diagnose_reflect_or_replan"
    assert obligation in action["obligation_ids"]


def test_scheduler_returns_maximal_nonconflicting_set(runtime: tuple[Store, CoreService, str, str]) -> None:
    _, core, _, mission = runtime
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description="Build",
    )
    identifiers = []
    for title, scope, priority in [
        ("backend", ["server"], 10),
        ("frontend", ["web"], 9),
        ("conflict", ["server/api"], 8),
    ]:
        work = core.create_work_item(
            mission_id=mission,
            obligation_id=obligation,
            work_type="implementation",
            title=title,
            description=title,
            writable_scope=scope,
            priority=priority,
        )
        core.select_work(
            work, expected_version=1, selected_by="selector", basis={"why": title}
        )
        identifiers.append(work)
    assert identifiers[:2] == [row["id"] for row in core.ready_work(mission)]


def test_candidate_acceptance_does_not_unblock_integrated_dependency(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    obligation = core.add_obligation(
        mission_id=mission, obligation_type="implement", description="Build"
    )
    first = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="implementation",
        title="candidate",
        description="candidate",
    )
    second = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="integration",
        title="integrate",
        description="integrate",
    )
    core.add_work_dependency(second, first)
    core.select_work(second, expected_version=1, selected_by="selector", basis={})
    with store.transaction() as db:
        db.execute(
            "UPDATE work_items SET acceptance_status='candidate_accepted' WHERE id=?",
            (first,),
        )
    assert core.ready_work(mission) == []
    with store.transaction() as db:
        db.execute(
            "UPDATE work_items SET acceptance_status='integrated_accepted' WHERE id=?",
            (first,),
        )
    assert [row["id"] for row in core.ready_work(mission)] == [second]


def test_program_revision_is_review_bound_and_preserves_range(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    program = core.create_program(
        mission_id=mission,
        name="Program",
        requested_range={"kind": "full_program"},
        terminal_criteria={"probe": "e2e"},
    )
    first = core.create_work_item(
        mission_id=mission,
        program_id=program,
        work_type="implementation",
        title="first",
        description="first",
    )
    preview = core.preview_program_revision(
        program,
        mapping={},
        graph={"work": [first]},
        accepted_history={"accepted": []},
        resume_frontier={"first": first},
        source_ref="revision-1",
    )
    reviewer = add_session(store, mission, role="independent_reviewer")
    review = add_execution(
        store,
        mission,
        execution_type="program_review",
        session_id=reviewer,
        result={
            "program_id": program,
            "revision_root": preview["revision_root"],
            "disposition": "accept",
        },
    )
    revision = core.revise_program(
        program,
        expected_version=1,
        mapping={},
        graph={"work": [first]},
        accepted_history={"accepted": []},
        resume_frontier={"first": first},
        source_ref="revision-1",
        author_execution_id=None,
        review_execution_id=review,
        accepted=True,
    )
    program_row = store.one("SELECT * FROM programs WHERE id=?", (program,))
    assert revision == program_row["current_revision_id"]
    assert program_row["requested_range_json"] == '{"kind":"full_program"}'
    revision_row = store.one("SELECT * FROM program_revisions WHERE id=?", (revision,))
    assert revision_row["review_root"]


def test_program_revision_rejects_stale_review(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    program = core.create_program(
        mission_id=mission,
        name="Program",
        requested_range={"kind": "full_program"},
        terminal_criteria={"probe": "e2e"},
    )
    reviewer = add_session(store, mission, role="independent_reviewer")
    review = add_execution(
        store,
        mission,
        execution_type="program_review",
        session_id=reviewer,
        result={"program_id": program, "revision_root": "stale", "disposition": "accept"},
    )
    with pytest.raises(EvidenceInvalid, match="stale"):
        core.revise_program(
            program,
            expected_version=1,
            mapping={},
            graph={},
            accepted_history={"accepted": []},
            resume_frontier={},
            source_ref="revision",
            author_execution_id=None,
            review_execution_id=review,
            accepted=True,
        )


def test_stale_capability_update_rejected_and_evidence_required(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    capability = core.add_capability(
        mission_id=mission, name="Capability", description="works"
    )
    evidence = store.record_evidence(
        mission_id=mission,
        evidence_type="focused_probe",
        subject_type="capability",
        subject_id=capability,
        payload={"passed": True},
    )
    core.set_capability_status(
        capability, expected_version=1, status="partial", evidence_id=evidence
    )
    with pytest.raises(StaleState):
        core.set_capability_status(
            capability, expected_version=1, status="locally_verified", evidence_id=evidence
        )
    with pytest.raises(EvidenceInvalid):
        core.set_capability_status(
            capability,
            expected_version=2,
            status="locally_verified",
            evidence_id="not-real",
        )


def test_expired_lease_recovery_is_mission_scoped(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, project, mission = runtime
    other = core.create_mission(project_id=project, title="Other", objective="Other")
    work = core.create_work_item(
        mission_id=other, work_type="implementation", title="x", description="x"
    )
    execution = add_execution(
        store,
        other,
        execution_type="implementation",
        status="running",
        work_item_id=work,
    )
    expired = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat()
    with store.transaction() as db:
        db.execute(
            """INSERT INTO leases(
                id,resource_key,mode,owner_execution_id,generation,status,
                expires_at,heartbeat_at,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (new_id("lea"), "work:x", "exclusive", execution, 1, "active", expired, expired, expired),
        )
    assert core.next_action(mission)["action"] != "recover_expired_work"
    assert core.next_action(other)["action"] == "recover_expired_work"


def test_terminal_completion_requires_current_evidence_and_verifier(runtime: tuple[Store, CoreService, str, str]) -> None:
    store, core, _, mission = runtime
    capability = core.add_capability(
        mission_id=mission, name="Capability", description="works"
    )
    cap_evidence = store.record_evidence(
        mission_id=mission,
        evidence_type="end_to_end_probe",
        subject_type="capability",
        subject_id=capability,
        payload={"passed": True},
    )
    core.set_capability_status(
        capability,
        expected_version=1,
        status="locally_verified",
        evidence_id=cap_evidence,
    )
    cap_evidence_2 = store.record_evidence(
        mission_id=mission,
        evidence_type="end_to_end_probe",
        subject_type="capability",
        subject_id=capability,
        payload={"passed": True, "phase": "integrated"},
    )
    core.set_capability_status(
        capability,
        expected_version=2,
        status="integrated",
        evidence_id=cap_evidence_2,
    )
    cap_evidence_3 = store.record_evidence(
        mission_id=mission,
        evidence_type="end_to_end_probe",
        subject_type="capability",
        subject_id=capability,
        payload={"passed": True, "phase": "terminal"},
    )
    core.set_capability_status(
        capability,
        expected_version=3,
        status="end_to_end_verified",
        evidence_id=cap_evidence_3,
    )
    reviewer = add_session(store, mission, role="terminal_reviewer")
    terminal = add_execution(
        store,
        mission,
        execution_type="terminal_verification",
        session_id=reviewer,
        result={"passed": True},
    )
    terminal_evidence = store.record_evidence(
        mission_id=mission,
        evidence_type="terminal_probe",
        subject_type="mission",
        subject_id=mission,
        execution_id=terminal,
        producer_session_id=reviewer,
        payload={"passed": True},
    )
    assert core.next_action(mission)["action"] == "complete_mission"
    result = core.complete_mission(
        mission,
        expected_version=1,
        terminal_evidence_id=terminal_evidence,
        verifier_session_id=reviewer,
    )
    assert result["status"] == "completed"


def test_false_terminal_completion_is_rejected(runtime: tuple[Store, CoreService, str, str]) -> None:
    _, core, _, mission = runtime
    core.add_capability(mission_id=mission, name="Capability", description="works")
    with pytest.raises((InvalidTransition, EvidenceInvalid, Exception)):
        core.complete_mission(
            mission,
            expected_version=1,
            terminal_evidence_id="evidence",
            verifier_session_id="reviewer",
        )
