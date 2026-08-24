from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest

from software_factory.core import CoreService
from software_factory.database import Database
from software_factory.errors import EvidenceInvalid, InvalidTransition

REVISION = "revision-0123456789abcdef"
CURRENTNESS = "currentness-0123456789abcdef"
EXPECTED = {
    "operator_visible": {"ready": True},
    "protected_capabilities": {"mission_continuation": "preserved"},
}


def _future() -> str:
    return (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat()


@pytest.fixture
def runtime(tmp_path: Path) -> tuple[Database, CoreService, str, str, str, str]:
    store = Database(tmp_path / "factory.sqlite3")
    core = CoreService(store)
    project = core.missions.create_project("Acceptance lifecycle")
    mission = core.missions.create_mission(
        project_id=project,
        title="Observe the actual outcome",
        objective="Do not confuse process success with outcome acceptance",
    )
    implementer = core.agents.create_agent_session(
        mission_id=mission,
        provider="codex",
        role="implementer",
        external_task_id="implementer-provider-task",
    )
    reviewer = core.agents.create_agent_session(
        mission_id=mission,
        provider="codex",
        role="independent_reviewer",
        external_task_id="reviewer-provider-task",
    )
    work = core.work_items.create_work_item(
        mission_id=mission,
        work_type="implementation",
        title="Acceptance target",
        description="One exact revision through all acceptance stages",
    )
    with store.transaction() as db:
        db.execute(
            "UPDATE work_items SET candidate_revision=? WHERE id=?",
            (REVISION, work),
        )
    return store, core, mission, work, implementer, reviewer


def _evidence(
    store: Database,
    *,
    mission: str,
    suffix: str,
    producer: str | None = None,
    subject_type: str = "mission",
    subject_id: str | None = None,
    evidence_type: str = "installed_probe",
    execution_id: str | None = None,
) -> str:
    return store.record_evidence(
        mission_id=mission,
        evidence_type=evidence_type,
        subject_type=subject_type,
        subject_id=subject_id or mission,
        revision=REVISION,
        producer_session_id=producer,
        execution_id=execution_id,
        payload={"suffix": suffix, "passed": True},
    )


def _prepare_decide(
    store: Database,
    core: CoreService,
    *,
    mission: str,
    work: str,
    implementer: str,
    reviewer: str,
    stage: str,
    prior_stage_id: str | None,
    remaining_scope: list[str] | None = None,
) -> tuple[dict[str, Any], str]:
    evidence = _evidence(
        store,
        mission=mission,
        suffix=f"{stage}-process",
        producer=reviewer,
    )
    prepared = core.acceptance_lifecycle.prepare_stage(
        mission_id=mission,
        work_item_id=work,
        stage=stage,
        target_revision=REVISION,
        currentness_root=CURRENTNESS,
        implementer_session_id=implementer,
        required_probes=[{"key": f"{stage}-behavior", "type": "test"}],
        expected_outcome=EXPECTED,
        remaining_scope=remaining_scope or [],
        protected_capabilities=["mission-continuation"],
        prior_stage_id=prior_stage_id,
    )
    core.acceptance_lifecycle.record_probe_result(
        prepared["id"],
        probe_key=f"{stage}-behavior",
        exact_revision=REVISION,
        disposition="passed",
        observed_result={"exit_code": 0, "observed": True},
        evidence_ids=[evidence],
        observer_session_id=reviewer,
    )
    grant = core.governance.issue_role_grant(
        mission_id=mission,
        grantee_session_id=reviewer,
        role="independent_reviewer",
        target_type="acceptance_stage",
        target_id=prepared["id"],
        target_revision=REVISION,
        policy_root=f"policy-{stage}-0123456789abcdef",
        currentness_root=CURRENTNESS,
        expires_at=_future(),
        scope={"effects": ["review"], "stage": stage},
    )
    core.acceptance_lifecycle.record_independent_review(
        prepared["id"],
        grant_id=grant["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        review_contract={
            "reconstruct": ["operator_visible", "protected_capabilities"],
            "stage": stage,
        },
        provider_session_id="reviewer-provider-task",
        transcript_artifact_id=f"transcript-{stage}",
        evidence_ids=[evidence],
        disposition="accepted",
        findings={"blocking": []},
    )
    core.acceptance_lifecycle.decide_stage(prepared["id"], exact_revision=REVISION)
    return prepared, evidence


def _accept_aligned(
    core: CoreService,
    prepared: dict[str, Any],
    *,
    reviewer: str,
    evidence: str,
) -> dict[str, Any]:
    core.acceptance_lifecycle.reconcile_outcome(
        prepared["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        observed_outcome=EXPECTED,
        evidence_ids=[evidence],
    )
    return core.acceptance_lifecycle.accept_stage(
        prepared["id"],
        acceptor_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
    )


def _accepted_chain(
    store: Database,
    core: CoreService,
    mission: str,
    work: str,
    implementer: str,
    reviewer: str,
    *,
    through: tuple[str, ...] = ("candidate", "integrated", "installed"),
) -> dict[str, Any]:
    prior: dict[str, Any] | None = None
    for stage in through:
        prepared, evidence = _prepare_decide(
            store,
            core,
            mission=mission,
            work=work,
            implementer=implementer,
            reviewer=reviewer,
            stage=stage,
            prior_stage_id=None if prior is None else prior["id"],
        )
        prior = _accept_aligned(core, prepared, reviewer=reviewer, evidence=evidence)
    assert prior is not None
    return prior


def test_stages_require_governed_semantic_review_and_reject_same_author_or_stale_review(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    evidence = _evidence(store, mission=mission, suffix="mechanical", producer=reviewer)
    prepared = core.acceptance_lifecycle.prepare_stage(
        mission_id=mission,
        work_item_id=work,
        stage="candidate",
        target_revision=REVISION,
        currentness_root=CURRENTNESS,
        implementer_session_id=implementer,
        required_probes=[{"key": "behavior", "type": "test"}],
        expected_outcome=EXPECTED,
        remaining_scope=["integration", "installation", "terminal"],
    )
    core.acceptance_lifecycle.record_probe_result(
        prepared["id"],
        probe_key="behavior",
        exact_revision=REVISION,
        disposition="passed",
        observed_result={"passed": True},
        evidence_ids=[evidence],
        observer_session_id=reviewer,
    )
    with pytest.raises(InvalidTransition, match="independent"):
        core.acceptance_lifecycle.decide_stage(prepared["id"], exact_revision=REVISION)

    self_grant = core.governance.issue_role_grant(
        mission_id=mission,
        grantee_session_id=implementer,
        role="independent_reviewer",
        target_type="acceptance_stage",
        target_id=prepared["id"],
        target_revision=REVISION,
        policy_root="policy-self-0123456789abcdef",
        currentness_root=CURRENTNESS,
        expires_at=_future(),
        scope={"effects": ["review"]},
    )
    with pytest.raises(InvalidTransition, match="implementer cannot independently review"):
        core.acceptance_lifecycle.record_independent_review(
            prepared["id"],
            grant_id=self_grant["id"],
            reviewer_session_id=implementer,
            exact_revision=REVISION,
            currentness_root=CURRENTNESS,
            review_contract={"reconstruct": ["operator_visible"]},
            provider_session_id="implementer-provider-task",
            transcript_artifact_id="self-review",
            evidence_ids=[evidence],
            disposition="accepted",
            findings={},
        )
    with pytest.raises(InvalidTransition, match="currentness"):
        core.acceptance_lifecycle.record_independent_review(
            prepared["id"],
            grant_id=self_grant["id"],
            reviewer_session_id=reviewer,
            exact_revision=REVISION,
            currentness_root="stale-currentness",
            review_contract={"reconstruct": ["operator_visible"]},
            provider_session_id="reviewer-provider-task",
            transcript_artifact_id="stale-review",
            evidence_ids=[evidence],
            disposition="accepted",
            findings={},
        )


def test_changed_currentness_invalidates_the_prior_stage_and_all_downstream_use(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    prepared, evidence = _prepare_decide(
        store,
        core,
        mission=mission,
        work=work,
        implementer=implementer,
        reviewer=reviewer,
        stage="candidate",
        prior_stage_id=None,
    )
    accepted = _accept_aligned(core, prepared, reviewer=reviewer, evidence=evidence)
    replacement = core.acceptance_lifecycle.prepare_stage(
        mission_id=mission,
        work_item_id=work,
        stage="candidate",
        target_revision=REVISION,
        currentness_root="changed-currentness-0123456789abcdef",
        implementer_session_id=implementer,
        required_probes=[{"key": "candidate-behavior", "type": "test"}],
        expected_outcome=EXPECTED,
        remaining_scope=["integrated", "installed", "terminal"],
        protected_capabilities=["mission-continuation"],
    )
    assert replacement["status"] == "prepared"
    assert store.one(
        "SELECT status FROM acceptance_stage_records_v2 WHERE id=?", (accepted["id"],)
    ) == {"status": "stale"}
    assert store.one(
        "SELECT status FROM acceptance_contracts_v2 WHERE id=?", (accepted["contract_id"],)
    ) == {"status": "stale"}
    with pytest.raises(InvalidTransition, match="accepted candidate at exact revision"):
        core.acceptance_lifecycle.prepare_stage(
            mission_id=mission,
            work_item_id=work,
            stage="integrated",
            target_revision=REVISION,
            currentness_root="changed-currentness-0123456789abcdef",
            implementer_session_id=implementer,
            required_probes=[{"key": "integration", "type": "integration"}],
            expected_outcome=EXPECTED,
            remaining_scope=["installed", "terminal"],
            prior_stage_id=accepted["id"],
        )


def test_process_pass_actual_outcome_disagreement_reopens_only_narrow_owner(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    prepared, evidence = _prepare_decide(
        store,
        core,
        mission=mission,
        work=work,
        implementer=implementer,
        reviewer=reviewer,
        stage="candidate",
        prior_stage_id=None,
    )
    disagreement = core.acceptance_lifecycle.reconcile_outcome(
        prepared["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        observed_outcome={
            "operator_visible": {"ready": False},
            "protected_capabilities": {"mission_continuation": "preserved"},
        },
        evidence_ids=[evidence],
        narrow_owner_type="work_item",
        narrow_owner_id=work,
    )
    assert disagreement["disposition"] == "disagreed"
    assert store.one("SELECT acceptance_status FROM work_items WHERE id=?", (work,)) == {
        "acceptance_status": "regressed"
    }
    assert store.one(
        "SELECT status FROM obligations WHERE id=?", (disagreement["obligation_id"],)
    ) == {"status": "open"}
    assert store.one("SELECT status FROM incidents WHERE id=?", (disagreement["incident_id"],)) == {
        "status": "open"
    }
    with pytest.raises(EvidenceInvalid, match="aligned actual outcome"):
        core.acceptance_lifecycle.accept_stage(
            prepared["id"],
            acceptor_session_id=reviewer,
            exact_revision=REVISION,
            currentness_root=CURRENTNESS,
        )

    aligned_evidence = _evidence(
        store,
        mission=mission,
        suffix="corrected-outcome",
        producer=reviewer,
    )
    core.acceptance_lifecycle.reconcile_outcome(
        prepared["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        observed_outcome=EXPECTED,
        evidence_ids=[aligned_evidence],
    )
    with pytest.raises(InvalidTransition, match="remains unresolved"):
        core.acceptance_lifecycle.accept_stage(
            prepared["id"],
            acceptor_session_id=reviewer,
            exact_revision=REVISION,
            currentness_root=CURRENTNESS,
        )

    obligation_evidence = _evidence(
        store,
        mission=mission,
        suffix="obligation-resolved",
        producer=reviewer,
        subject_type="obligation",
        subject_id=disagreement["obligation_id"],
    )
    core.continuation.satisfy_obligation(
        disagreement["obligation_id"],
        expected_version=1,
        resolution={"actual_outcome": "corrected"},
        evidence_ids=[obligation_evidence],
        actor_session_id=reviewer,
    )
    core.supervision.record_effectiveness(
        disagreement["incident_id"],
        outcome="effective",
        reviewer_session_id=reviewer,
        evidence_ids=[aligned_evidence],
        observations={"operator_visible": {"ready": True}},
    )
    accepted = core.acceptance_lifecycle.accept_stage(
        prepared["id"],
        acceptor_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
    )
    assert accepted["status"] == "accepted"


def test_protected_capability_disagreement_regresses_that_capability_and_routes_incident(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    capability = core.capabilities.add_capability(
        mission_id=mission,
        name="Mission continuation",
        description="The runtime continues until the requested range is complete",
        protected=True,
    )
    local_evidence = _evidence(
        store,
        mission=mission,
        suffix="capability-local",
        subject_type="capability",
        subject_id=capability,
    )
    core.capabilities.set_capability_status(
        capability,
        expected_version=1,
        status="locally_verified",
        evidence_id=local_evidence,
    )
    integrated_evidence = _evidence(
        store,
        mission=mission,
        suffix="capability-integrated",
        subject_type="capability",
        subject_id=capability,
    )
    core.capabilities.set_capability_status(
        capability,
        expected_version=2,
        status="integrated",
        evidence_id=integrated_evidence,
    )
    prepared, _ = _prepare_decide(
        store,
        core,
        mission=mission,
        work=work,
        implementer=implementer,
        reviewer=reviewer,
        stage="candidate",
        prior_stage_id=None,
    )
    observed_evidence = _evidence(
        store,
        mission=mission,
        suffix="capability-regressed",
        producer=reviewer,
        subject_type="capability",
        subject_id=capability,
    )
    reconciliation = core.acceptance_lifecycle.reconcile_outcome(
        prepared["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        observed_outcome={
            "operator_visible": {"ready": True},
            "protected_capabilities": {"mission_continuation": "regressed"},
        },
        evidence_ids=[observed_evidence],
        narrow_owner_type="capability",
        narrow_owner_id=capability,
    )
    assert store.one("SELECT status FROM capabilities WHERE id=?", (capability,)) == {
        "status": "regressed"
    }
    assert store.one(
        "SELECT capability_id FROM obligations WHERE id=?",
        (reconciliation["obligation_id"],),
    ) == {"capability_id": capability}
    assert store.one(
        "SELECT target_type,target_id FROM incidents WHERE id=?",
        (reconciliation["incident_id"],),
    ) == {"target_type": "capability", "target_id": capability}


def test_terminal_reducer_requires_stage_outcome_and_empty_remaining_range(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    installed = _accepted_chain(store, core, mission, work, implementer, reviewer)
    execution = core._executions.queue_execution(
        mission_id=mission,
        execution_type="terminal_verification",
        idempotency_key="terminal-verification",
        agent_session_id=reviewer,
        input_payload={"revision": REVISION},
    )
    with store.transaction() as db:
        db.execute(
            """UPDATE executions SET status='succeeded',started_at=?,finished_at=?
               WHERE id=?""",
            ("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z", execution),
        )
    terminal_evidence = _evidence(
        store,
        mission=mission,
        suffix="terminal",
        producer=reviewer,
        evidence_type="terminal_probe",
        execution_id=execution,
    )
    provider_only = core.continuation.next_action(mission)
    assert provider_only["action"] == "reconcile_terminal_acceptance"

    terminal, process_evidence = _prepare_decide(
        store,
        core,
        mission=mission,
        work=work,
        implementer=implementer,
        reviewer=reviewer,
        stage="terminal",
        prior_stage_id=installed["id"],
        remaining_scope=["SFV2/B12"],
    )
    core.acceptance_lifecycle.reconcile_outcome(
        terminal["id"],
        reviewer_session_id=reviewer,
        exact_revision=REVISION,
        currentness_root=CURRENTNESS,
        observed_outcome=EXPECTED,
        evidence_ids=[process_evidence],
    )
    with pytest.raises(InvalidTransition, match="requested range"):
        core.acceptance_lifecycle.accept_stage(
            terminal["id"],
            acceptor_session_id=reviewer,
            exact_revision=REVISION,
            currentness_root=CURRENTNESS,
        )
    assert core.continuation.next_action(mission)["action"] == "reconcile_terminal_acceptance"
    with pytest.raises(InvalidTransition, match="accepted terminal-stage"):
        core.continuation.complete_mission(
            mission,
            expected_version=1,
            terminal_evidence_id=terminal_evidence,
            verifier_session_id=reviewer,
        )


def test_exact_terminal_chain_completes_only_after_independent_actual_outcome(
    runtime: tuple[Database, CoreService, str, str, str, str],
) -> None:
    store, core, mission, work, implementer, reviewer = runtime
    installed = _accepted_chain(store, core, mission, work, implementer, reviewer)
    execution = core._executions.queue_execution(
        mission_id=mission,
        execution_type="terminal_verification",
        idempotency_key="terminal-verification-complete",
        agent_session_id=reviewer,
        input_payload={"revision": REVISION},
    )
    with store.transaction() as db:
        db.execute(
            """UPDATE executions SET status='succeeded',started_at=?,finished_at=?
               WHERE id=?""",
            ("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z", execution),
        )
    terminal_evidence = _evidence(
        store,
        mission=mission,
        suffix="terminal-complete",
        producer=reviewer,
        evidence_type="terminal_probe",
        execution_id=execution,
    )
    terminal, process_evidence = _prepare_decide(
        store,
        core,
        mission=mission,
        work=work,
        implementer=implementer,
        reviewer=reviewer,
        stage="terminal",
        prior_stage_id=installed["id"],
        remaining_scope=[],
    )
    accepted_terminal = _accept_aligned(
        core,
        terminal,
        reviewer=reviewer,
        evidence=process_evidence,
    )
    assert accepted_terminal["status"] == "accepted"
    posture = core.continuation.next_action(mission)
    assert posture["action"] == "complete_mission"
    completed = core.continuation.complete_mission(
        mission,
        expected_version=1,
        terminal_evidence_id=terminal_evidence,
        verifier_session_id=reviewer,
    )
    assert completed["status"] == "completed"
