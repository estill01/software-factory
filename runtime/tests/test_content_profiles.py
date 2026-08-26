from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from external_extension_fixture import ObservationCardExtensionProfile

from software_factory import (
    AuthorityDenied,
    ContentSection,
    ContentSource,
    CoreService,
    EffectClass,
    EvidenceInvalid,
    InvalidTransition,
    Store,
)


def _future() -> str:
    return (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat()


def _execute(
    core: CoreService,
    profile_key: str,
    target_id: str,
    effect_class: EffectClass,
    operation: str,
) -> dict[str, Any]:
    snapshot = core.target_profiles.snapshot(profile_key, target_id)
    result = core.target_profiles.execute(
        profile_key,
        effect_class,
        target_id,
        expected_revision=snapshot.revision,
        expected_currentness_root=snapshot.currentness_root,
        arguments={"operation": operation},
    )
    return dict(result.result)


def _register_content(core: CoreService, root: Path) -> str:
    target_id = "operations-brief"
    core.register_content_target(
        target_id,
        root=root,
        title="Daily Operations Brief",
        audience="local operations team",
        sources=(
            ContentSource(
                "schedule",
                "Maintained schedule",
                "The morning review begins at 09:00 local time.",
            ),
            ContentSource(
                "inventory",
                "Verified inventory",
                "Three prepared kits are available for the morning review.",
            ),
            ContentSource(
                "handoff",
                "Handoff checklist",
                "The closing handoff records the owner and exact artifact receipt.",
            ),
        ),
        sections=(
            ContentSection(
                "Opening context",
                "Orient the reader with the maintained timing and available materials.",
                ("schedule", "inventory"),
            ),
            ContentSection(
                "Closing handoff",
                "State the observable handoff requirement without adding an unsupported fact.",
                ("handoff",),
            ),
        ),
    )
    return target_id


def _content_steps() -> tuple[tuple[EffectClass, str], ...]:
    return (
        (EffectClass.WORKSPACE, "collect_sources"),
        (EffectClass.COMMAND, "plan"),
        (EffectClass.COMMAND, "draft"),
        (EffectClass.COMMAND, "revise"),
        (EffectClass.TEST, "review_factual"),
        (EffectClass.TEST, "review_structural"),
        (EffectClass.TEST, "review_style"),
        (EffectClass.BUILD, "render"),
        (EffectClass.RELEASE, "deliver"),
        (EffectClass.TEST, "verify_delivery"),
    )


def _accept_stage(
    store: Store,
    core: CoreService,
    *,
    mission_id: str,
    work_item_id: str,
    implementer_id: str,
    reviewer_id: str,
    revision: str,
    currentness_root: str,
    stage: str,
    prior_stage_id: str | None,
    outcome: dict[str, Any],
    evidence_id: str,
    before_accept: Callable[[], None] | None = None,
) -> dict[str, Any]:
    remaining = {
        "candidate": ["integrated", "installed", "terminal"],
        "integrated": ["installed", "terminal"],
        "installed": ["terminal"],
        "terminal": [],
    }[stage]
    prepared = core.acceptance_lifecycle.prepare_stage(
        mission_id=mission_id,
        work_item_id=work_item_id,
        stage=stage,  # type: ignore[arg-type]
        target_revision=revision,
        currentness_root=currentness_root,
        implementer_session_id=implementer_id,
        required_probes=[{"key": f"{stage}-artifact", "type": "operator_visible"}],
        expected_outcome=outcome,
        remaining_scope=remaining,
        protected_capabilities=["mission-continuation", "independent-acceptance"],
        prior_stage_id=prior_stage_id,
    )
    core.acceptance_lifecycle.record_probe_result(
        prepared["id"],
        probe_key=f"{stage}-artifact",
        exact_revision=revision,
        disposition="passed",
        observed_result={"delivered": True, "current": True},
        evidence_ids=[evidence_id],
        observer_session_id=reviewer_id,
    )
    grant = core.governance.issue_role_grant(
        mission_id=mission_id,
        grantee_session_id=reviewer_id,
        role="independent_reviewer",
        target_type="acceptance_stage",
        target_id=prepared["id"],
        target_revision=revision,
        policy_root=f"content-stage-policy-{stage}-{revision}",
        currentness_root=currentness_root,
        expires_at=_future(),
        scope={"effects": ["review"], "stage": stage},
    )
    core.acceptance_lifecycle.record_stage_independent_review(
        prepared["id"],
        grant_id=grant["id"],
        reviewer_session_id=reviewer_id,
        exact_revision=revision,
        currentness_root=currentness_root,
        review_contract={
            "reconstruct": ["delivered_artifact", "receipt", "protected_capabilities"],
            "stage": stage,
        },
        provider_session_id="neutral-review-task",
        transcript_artifact_id=f"transcript-{stage}-{revision}",
        evidence_ids=[evidence_id],
        disposition="accepted",
        findings={"blocking": []},
    )
    core.acceptance_lifecycle.decide_stage(prepared["id"], exact_revision=revision)
    outcome_grant = core.acceptance_lifecycle.issue_outcome_reviewer_grant(
        prepared["id"],
        reviewer_session_id=reviewer_id,
        policy_root=f"content-outcome-policy-{stage}-{revision}",
        expires_at=_future(),
    )
    core.acceptance_lifecycle.reconcile_outcome(
        prepared["id"],
        grant_id=outcome_grant["id"],
        reviewer_session_id=reviewer_id,
        provider_session_id="neutral-review-task",
        exact_revision=revision,
        currentness_root=currentness_root,
        observed_outcome=outcome,
        evidence_ids=[evidence_id],
    )
    if before_accept is not None:
        before_accept()
    return core.acceptance_lifecycle.accept_stage(
        prepared["id"],
        acceptor_session_id=reviewer_id,
        exact_revision=revision,
        currentness_root=currentness_root,
    )


def _complete_profile_mission(
    core: CoreService,
    *,
    profile_key: str,
    target_id: str,
    steps: tuple[tuple[EffectClass, str], ...],
    candidate_spec: list[dict[str, Any]] | None = None,
    resubmit_same_revision: bool = False,
    before_stage_accept: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    store = core.store
    project_id = core.create_project(f"{profile_key} mission project")
    mission_id = core.create_mission(
        project_id=project_id,
        title=f"Deliver {profile_key} target",
        objective="Produce, independently review, deliver, and verify one current artifact",
    )
    capability_id = core.add_capability(
        mission_id=mission_id,
        name="current delivered artifact",
        description="The exact profile artifact and receipt are current and independently observed",
    )
    obligation_id = core.add_obligation(
        mission_id=mission_id,
        capability_id=capability_id,
        obligation_type="delivery",
        description="Deliver and verify the registered target artifact",
    )
    program_id = core.create_program(
        mission_id=mission_id,
        name=f"{profile_key} production program",
        requested_range={"kind": "full_program", "stages": [operation for _, operation in steps]},
        terminal_criteria={"delivered": True, "verified": True},
        work_graph={"sequence": [operation for _, operation in steps]},
    )
    work_id = core.create_work_item(
        mission_id=mission_id,
        program_id=program_id,
        obligation_id=obligation_id,
        work_type="target_production",
        title=f"Produce {profile_key} artifact",
        description="Use the registered target profile through exact-currentness effects",
        expected_effect={"target_profile": profile_key, "target_id": target_id},
        acceptance_spec={
            "candidate": candidate_spec
            if candidate_spec is not None
            else [
                {"type": "profile_currentness", "required": True},
                {
                    "type": "independent_review",
                    "required": True,
                    "role": "independent_reviewer",
                },
            ]
        },
    )
    core.select_work(
        work_id,
        expected_version=1,
        selected_by="factory-scheduler",
        basis={"dependency_safe": True, "target_profile": profile_key},
    )
    implementer_id = core.create_agent_session(
        mission_id=mission_id,
        provider="deterministic",
        role="implementer",
        external_task_id="neutral-implementation-task",
    )
    reviewer_id = core.create_agent_session(
        mission_id=mission_id,
        provider="deterministic",
        role="independent_reviewer",
        external_task_id="neutral-review-task",
    )
    execution_id = core.queue_execution(
        mission_id=mission_id,
        work_item_id=work_id,
        agent_session_id=implementer_id,
        execution_type="target_profile_production",
        idempotency_key=f"{mission_id}:{profile_key}:{target_id}:production",
        expected_effect={"target_profile": profile_key, "target_id": target_id},
    )
    generation = core.acquire_leases(
        execution_id,
        [{"kind": "target_profile", "key": f"{profile_key}:{target_id}", "mode": "exclusive"}],
    )
    results = []
    for effect_class, operation in steps:
        results.append(_execute(core, profile_key, target_id, effect_class, operation))
    final_snapshot = core.target_profiles.snapshot(profile_key, target_id)
    assert final_snapshot.attributes["phase"] == "delivered_verified"
    core.complete_external_execution(
        execution_id,
        generation=generation,
        succeeded=True,
        result={
            "profile_key": profile_key,
            "target_id": target_id,
            "revision": final_snapshot.revision,
            "currentness_root": final_snapshot.currentness_root,
            "steps": results,
        },
    )
    work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
    submitted = core.qa.submit_profile_candidate(
        execution_id,
        profile_key=profile_key,
        target_id=target_id,
        expected_revision=final_snapshot.revision,
        expected_currentness_root=final_snapshot.currentness_root,
        expected_work_version=work["state_version"],
    )
    assert {item["qa_type"] for item in submitted["requirements"]} == {
        "independent_review",
        "profile_currentness",
    }
    requirements = {item["qa_type"]: item for item in submitted["requirements"]}
    work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
    with pytest.raises(EvidenceInvalid, match="QA remains incomplete"):
        core.complete_candidate_qa(work_id, expected_work_version=work["state_version"])
    currentness_result = core.qa.record_profile_currentness(
        requirements["profile_currentness"]["id"]
    )
    assert currentness_result["passed"] is True
    work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
    with pytest.raises(EvidenceInvalid, match="QA remains incomplete"):
        core.complete_candidate_qa(work_id, expected_work_version=work["state_version"])
    review_result = core.qa.record_independent_review(
        requirements["independent_review"]["id"],
        reviewer_session_id=reviewer_id,
        disposition="accept",
    )
    assert review_result["disposition"] == "accept"
    work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
    completed_qa = core.complete_candidate_qa(work_id, expected_work_version=work["state_version"])
    assert completed_qa["qa_status"] == "passed"
    outcome = {
        "operator_visible": {
            "profile_key": profile_key,
            "target_id": target_id,
            "delivered": True,
            "currentness_root": final_snapshot.currentness_root,
        },
        "protected_capabilities": {
            "mission_continuation": "preserved",
            "independent_acceptance": "required",
        },
    }
    superseded_stage: dict[str, Any] | None = None
    if resubmit_same_revision:
        first_candidate_root = submitted["candidate_root"]
        first_requirement_ids = {item["id"] for item in submitted["requirements"]}
        first_stage_evidence = store.record_evidence(
            mission_id=mission_id,
            evidence_type="installed_probe",
            subject_type="work_item",
            subject_id=work_id,
            revision=final_snapshot.revision,
            producer_session_id=reviewer_id,
            payload={"outcome": outcome, "candidate_root": first_candidate_root},
        )
        superseded_stage = _accept_stage(
            store,
            core,
            mission_id=mission_id,
            work_item_id=work_id,
            implementer_id=implementer_id,
            reviewer_id=reviewer_id,
            revision=final_snapshot.revision,
            currentness_root=final_snapshot.currentness_root,
            stage="candidate",
            prior_stage_id=None,
            outcome=outcome,
            evidence_id=first_stage_evidence,
        )
        assert superseded_stage["scope_key"].endswith(first_candidate_root)
        second_execution_id = core.queue_execution(
            mission_id=mission_id,
            work_item_id=work_id,
            agent_session_id=implementer_id,
            execution_type="target_profile_production",
            idempotency_key=f"{mission_id}:{profile_key}:{target_id}:same-revision-resubmit",
            expected_effect={"target_profile": profile_key, "target_id": target_id},
        )
        second_generation = core.acquire_leases(
            second_execution_id,
            [
                {
                    "kind": "target_profile",
                    "key": f"{profile_key}:{target_id}",
                    "mode": "exclusive",
                }
            ],
        )
        core.complete_external_execution(
            second_execution_id,
            generation=second_generation,
            succeeded=True,
            result={
                "profile_key": profile_key,
                "target_id": target_id,
                "revision": final_snapshot.revision,
                "currentness_root": final_snapshot.currentness_root,
                "resubmitted": True,
            },
        )
        work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
        resubmitted = core.qa.submit_profile_candidate(
            second_execution_id,
            profile_key=profile_key,
            target_id=target_id,
            expected_revision=final_snapshot.revision,
            expected_currentness_root=final_snapshot.currentness_root,
            expected_work_version=work["state_version"],
        )
        assert resubmitted["candidate_root"] != first_candidate_root
        placeholders = ",".join("?" for _ in first_requirement_ids)
        stale = store.all(
            f"SELECT id,status FROM qa_requirements WHERE id IN ({placeholders})",
            tuple(sorted(first_requirement_ids)),
        )
        assert {row["status"] for row in stale} == {"stale"}
        old_results = store.all(
            f"SELECT stale_at FROM qa_results WHERE requirement_id IN ({placeholders})",
            tuple(sorted(first_requirement_ids)),
        )
        assert old_results and all(row["stale_at"] for row in old_results)
        stale_stage = store.one(
            "SELECT status,contract_id,decision_id FROM acceptance_stage_records_v2 WHERE id=?",
            (superseded_stage["id"],),
        )
        assert stale_stage["status"] == "stale"
        assert (
            store.one(
                "SELECT status FROM acceptance_contracts_v2 WHERE id=?",
                (stale_stage["contract_id"],),
            )["status"]
            == "stale"
        )
        assert (
            store.one(
                "SELECT decision FROM acceptance_decisions_v2 WHERE id=?",
                (stale_stage["decision_id"],),
            )["decision"]
            == "stale"
        )
        assert {
            row["status"]
            for row in store.all(
                "SELECT status FROM independent_review_executions_v2 WHERE contract_id=?",
                (stale_stage["contract_id"],),
            )
        } == {"invalidated"}
        before_stale_writes = {
            table: store.one(f"SELECT COUNT(*) AS n FROM {table}")["n"]
            for table in ("evidence_records", "executions", "qa_results")
        }
        with pytest.raises(InvalidTransition, match="stale"):
            core.qa.record_profile_currentness(requirements["profile_currentness"]["id"])
        with pytest.raises(InvalidTransition, match="stale"):
            core.qa.record_independent_review(
                requirements["independent_review"]["id"],
                reviewer_session_id=reviewer_id,
                disposition="accept",
            )
        assert {
            table: store.one(f"SELECT COUNT(*) AS n FROM {table}")["n"]
            for table in ("evidence_records", "executions", "qa_results")
        } == before_stale_writes
        with pytest.raises(InvalidTransition, match="not promotable"):
            core.acceptance_lifecycle.accept_stage(
                superseded_stage["id"],
                acceptor_session_id=reviewer_id,
                exact_revision=final_snapshot.revision,
                currentness_root=final_snapshot.currentness_root,
            )
        active_requirements = {
            item["qa_type"]: item
            for item in resubmitted["requirements"]
            if item["status"] != "stale"
        }
        assert {item["acceptance_contract_root"] for item in active_requirements.values()} == {
            resubmitted["candidate_root"]
        }
        work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
        with pytest.raises(EvidenceInvalid, match="QA remains incomplete"):
            core.complete_candidate_qa(work_id, expected_work_version=work["state_version"])
        core.qa.record_profile_currentness(active_requirements["profile_currentness"]["id"])
        core.qa.record_independent_review(
            active_requirements["independent_review"]["id"],
            reviewer_session_id=reviewer_id,
            disposition="accept",
        )
        work = store.one("SELECT state_version FROM work_items WHERE id=?", (work_id,))
        completed_qa = core.complete_candidate_qa(
            work_id, expected_work_version=work["state_version"]
        )
        assert completed_qa["qa_status"] == "passed"
    stage_evidence = store.record_evidence(
        mission_id=mission_id,
        evidence_type="installed_probe",
        subject_type="work_item",
        subject_id=work_id,
        revision=final_snapshot.revision,
        producer_session_id=reviewer_id,
        payload={"outcome": outcome, "currentness_root": final_snapshot.currentness_root},
    )
    prior: dict[str, Any] | None = None
    for stage in ("candidate", "integrated", "installed"):
        observed = core.target_profiles.snapshot(profile_key, target_id)
        assert observed.revision == final_snapshot.revision
        assert observed.currentness_root == final_snapshot.currentness_root
        prior = _accept_stage(
            store,
            core,
            mission_id=mission_id,
            work_item_id=work_id,
            implementer_id=implementer_id,
            reviewer_id=reviewer_id,
            revision=final_snapshot.revision,
            currentness_root=final_snapshot.currentness_root,
            stage=stage,
            prior_stage_id=None if prior is None else prior["id"],
            outcome=outcome,
            evidence_id=stage_evidence,
            before_accept=(
                None
                if before_stage_accept is None
                else lambda stage=stage: before_stage_accept(stage)
            ),
        )
        if stage == "candidate" and superseded_stage is not None:
            assert prior["scope_key"] != superseded_stage["scope_key"]
    assert prior is not None
    with pytest.raises(InvalidTransition, match="profile missions require a work-bound terminal"):
        core.acceptance_lifecycle.prepare_stage(
            mission_id=mission_id,
            work_item_id=None,
            stage="terminal",
            target_revision=final_snapshot.revision,
            currentness_root=final_snapshot.currentness_root,
            implementer_session_id=implementer_id,
            required_probes=[{"key": "terminal", "type": "test"}],
            expected_outcome=outcome,
            remaining_scope=[],
            prior_stage_id=prior["id"],
        )

    obligation_evidence = store.record_evidence(
        mission_id=mission_id,
        evidence_type="end_to_end_probe",
        subject_type="obligation",
        subject_id=obligation_id,
        revision=final_snapshot.revision,
        producer_session_id=reviewer_id,
        payload={"delivered": True, "verified": True},
    )
    core.continuation.satisfy_obligation(
        obligation_id,
        expected_version=1,
        resolution={"profile_key": profile_key, "revision": final_snapshot.revision},
        evidence_ids=[obligation_evidence],
        actor_session_id=reviewer_id,
    )
    capability_evidence = store.record_evidence(
        mission_id=mission_id,
        evidence_type="end_to_end_probe",
        subject_type="capability",
        subject_id=capability_id,
        revision=final_snapshot.revision,
        producer_session_id=reviewer_id,
        payload={"outcome": outcome},
    )
    for version, status in enumerate(
        ("partial", "locally_verified", "integrated", "end_to_end_verified"), start=1
    ):
        core.set_capability_status(
            capability_id,
            expected_version=version,
            status=status,
            evidence_id=capability_evidence,
            actor_id=reviewer_id,
        )

    mapping = {work_id: work_id}
    graph = {"sequence": [operation for _, operation in steps], "work_item_id": work_id}
    accepted_history = {"accepted": [work_id], "range_complete": True}
    preview = core.preview_program_revision(
        program_id,
        mapping=mapping,
        graph=graph,
        accepted_history=accepted_history,
        resume_frontier={},
        source_ref=final_snapshot.revision,
    )
    program_review_id = core.queue_execution(
        mission_id=mission_id,
        agent_session_id=reviewer_id,
        execution_type="program_review",
        idempotency_key=f"{mission_id}:{profile_key}:program-review",
    )
    program_generation = core.acquire_leases(
        program_review_id,
        [{"kind": "review", "key": program_id, "mode": "exclusive"}],
    )
    core.complete_external_execution(
        program_review_id,
        generation=program_generation,
        succeeded=True,
        result={
            "program_id": program_id,
            "revision_root": preview["revision_root"],
            "disposition": "accept",
        },
    )
    program_revision_id = core.revise_program(
        program_id,
        expected_version=1,
        mapping=mapping,
        graph=graph,
        accepted_history=accepted_history,
        resume_frontier={},
        source_ref=final_snapshot.revision,
        author_execution_id=execution_id,
        review_execution_id=program_review_id,
        accepted=True,
    )
    program_revision_root = store.one(
        "SELECT revision_root FROM program_revisions WHERE id=?", (program_revision_id,)
    )["revision_root"]
    program_evidence = store.record_evidence(
        mission_id=mission_id,
        evidence_type="program_outcome",
        subject_type="program",
        subject_id=program_id,
        revision=program_revision_root,
        producer_session_id=reviewer_id,
        payload={"range_complete": True, "work_item_id": work_id},
    )
    core.complete_program(
        program_id,
        expected_version=2,
        reviewer_session_id=reviewer_id,
        evidence_ids=[program_evidence],
    )

    terminal_execution_id = core.queue_execution(
        mission_id=mission_id,
        agent_session_id=reviewer_id,
        execution_type="terminal_verification",
        idempotency_key=f"{mission_id}:{profile_key}:terminal-verification",
    )
    terminal_generation = core.acquire_leases(
        terminal_execution_id,
        [{"kind": "terminal", "key": mission_id, "mode": "exclusive"}],
    )
    core.complete_external_execution(
        terminal_execution_id,
        generation=terminal_generation,
        succeeded=True,
        result={"outcome": outcome, "disposition": "passed"},
    )
    terminal_evidence = store.record_evidence(
        mission_id=mission_id,
        evidence_type="terminal_probe",
        subject_type="mission",
        subject_id=mission_id,
        revision=final_snapshot.revision,
        execution_id=terminal_execution_id,
        producer_session_id=reviewer_id,
        payload={"outcome": outcome},
    )
    terminal = _accept_stage(
        store,
        core,
        mission_id=mission_id,
        work_item_id=work_id,
        implementer_id=implementer_id,
        reviewer_id=reviewer_id,
        revision=final_snapshot.revision,
        currentness_root=final_snapshot.currentness_root,
        stage="terminal",
        prior_stage_id=prior["id"],
        outcome=outcome,
        evidence_id=terminal_evidence,
    )
    assert terminal["status"] == "accepted"
    observed = core.target_profiles.snapshot(profile_key, target_id)
    assert observed.revision == final_snapshot.revision
    assert observed.currentness_root == final_snapshot.currentness_root
    mission = store.one("SELECT state_version FROM missions WHERE id=?", (mission_id,))
    completed = core.continuation.complete_mission(
        mission_id,
        expected_version=mission["state_version"],
        terminal_evidence_id=terminal_evidence,
        verifier_session_id=reviewer_id,
    )
    assert core.continuation.next_action(mission_id) == {
        "posture": "complete",
        "action": "none",
        "reason": "mission_completed",
    }
    return {
        "mission": completed,
        "work": store.one("SELECT * FROM work_items WHERE id=?", (work_id,)),
        "snapshot": final_snapshot,
        "outcome": outcome,
    }


def test_content_profile_enforces_closed_effects_currentness_and_quality(tmp_path: Path) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    target_id = _register_content(core, tmp_path / "content")
    initial = core.target_profiles.snapshot("content", target_id)
    assert initial.attributes["phase"] == "registered"
    assert core.target_profiles.keys() == ("content", "software")

    with pytest.raises(InvalidTransition, match="requires passed reviews|not available"):
        _execute(core, "content", target_id, EffectClass.BUILD, "render")
    with pytest.raises(AuthorityDenied, match="unregistered arguments"):
        core.target_profiles.execute(
            "content",
            EffectClass.WORKSPACE,
            target_id,
            expected_revision=initial.revision,
            expected_currentness_root=initial.currentness_root,
            arguments={"operation": "collect_sources", "accept": True},
        )
    with pytest.raises(AuthorityDenied, match="registry authority"):
        core._content_profile._execute_effect(
            object(),
            EffectClass.WORKSPACE,
            target_id,
            expected_revision=initial.revision,
            expected_currentness_root=initial.currentness_root,
            arguments={"operation": "collect_sources"},
        )

    _execute(core, "content", target_id, EffectClass.WORKSPACE, "collect_sources")
    current = core.target_profiles.snapshot("content", target_id)
    tampered = tmp_path / "content" / "workspace" / "sources.json"
    original = tampered.read_text(encoding="utf-8")
    tampered.write_text(original + " ", encoding="utf-8")
    with pytest.raises(InvalidTransition, match="revision changed|currentness changed"):
        core.target_profiles.execute(
            "content",
            EffectClass.COMMAND,
            target_id,
            expected_revision=current.revision,
            expected_currentness_root=current.currentness_root,
            arguments={"operation": "plan"},
        )


def test_content_profile_rejects_symlink_target_root(tmp_path: Path) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    physical = tmp_path / "physical"
    physical.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(physical, target_is_directory=True)
    with pytest.raises(InvalidTransition, match="root cannot be a symlink"):
        core.register_content_target(
            "symlinked-target",
            root=linked,
            title="Symlinked target",
            audience="test reader",
            sources=(ContentSource("source", "Source", "One maintained statement."),),
            sections=(ContentSection("Section", "Summarize the source.", ("source",)),),
        )


def test_content_profile_reopens_and_resumes_exact_durable_target(tmp_path: Path) -> None:
    database = tmp_path / "factory.sqlite3"
    root = tmp_path / "content"
    first = CoreService(Store(database))
    target_id = _register_content(first, root)
    _execute(first, "content", target_id, EffectClass.WORKSPACE, "collect_sources")
    _execute(first, "content", target_id, EffectClass.COMMAND, "plan")
    before_restart = first.target_profiles.snapshot("content", target_id)

    restarted = CoreService(Store(database))
    assert restarted.reopen_content_target(str(root)) == target_id
    reopened = restarted.target_profiles.snapshot("content", target_id)
    assert reopened == before_restart
    for effect_class, operation in _content_steps()[2:]:
        _execute(restarted, "content", target_id, effect_class, operation)
    assert restarted.target_profiles.snapshot("content", target_id).attributes["phase"] == (
        "delivered_verified"
    )


def test_content_profile_cross_host_fence_serializes_physical_effect(tmp_path: Path) -> None:
    database = tmp_path / "factory.sqlite3"
    root = tmp_path / "content"
    first = CoreService(Store(database))
    target_id = _register_content(first, root)
    second = CoreService(Store(database))
    second.reopen_content_target(str(root))
    snapshot = second.target_profiles.snapshot("content", target_id)
    started = Event()

    def execute_from_second_host() -> dict[str, Any]:
        started.set()
        return _execute(second, "content", target_id, EffectClass.WORKSPACE, "collect_sources")

    with ThreadPoolExecutor(max_workers=1) as executor:
        with first.target_profiles.currentness_fence(
            "content",
            target_id,
            expected_revision=snapshot.revision,
            expected_currentness_root=snapshot.currentness_root,
        ):
            pending = executor.submit(execute_from_second_host)
            assert started.wait(timeout=1)
            with pytest.raises(FutureTimeout):
                pending.result(timeout=0.05)
        assert pending.result(timeout=1)["source_count"] == 3
    assert second.target_profiles.snapshot("content", target_id).attributes["phase"] == (
        "sources_collected"
    )


def test_neutral_content_mission_reaches_current_delivered_outcome(tmp_path: Path) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    target_id = _register_content(core, tmp_path / "content")
    result = _complete_profile_mission(
        core,
        profile_key="content",
        target_id=target_id,
        steps=_content_steps(),
    )
    assert result["mission"]["status"] == "completed"
    assert result["work"]["acceptance_status"] == "installed_accepted"
    delivered = tmp_path / "content" / "delivered" / "document.html"
    rendered = delivered.read_text(encoding="utf-8")
    assert "Daily Operations Brief" in rendered
    assert "The morning review begins at 09:00 local time." in rendered
    assert "[schedule] Maintained schedule" in rendered
    assert (tmp_path / "content" / "reviews" / "factual.json").is_file()
    assert (tmp_path / "content" / "reviews" / "structural.json").is_file()
    assert (tmp_path / "content" / "reviews" / "style.json").is_file()


def test_profile_candidate_forces_review_and_restarts_qa_for_same_revision_resubmission(
    tmp_path: Path,
) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    target_id = _register_content(core, tmp_path / "content")
    result = _complete_profile_mission(
        core,
        profile_key="content",
        target_id=target_id,
        steps=_content_steps(),
        candidate_spec=[{"type": "profile_currentness", "required": False}],
        resubmit_same_revision=True,
    )
    assert result["mission"]["status"] == "completed"
    active = core.store.all(
        """SELECT qa_type,required,acceptance_contract_root FROM qa_requirements
           WHERE work_item_id=? AND phase='candidate' AND status<>'stale'""",
        (result["work"]["id"],),
    )
    assert {(row["qa_type"], row["required"]) for row in active} == {
        ("profile_currentness", 1),
        ("independent_review", 1),
    }
    assert len({row["acceptance_contract_root"] for row in active}) == 1


def test_profile_acceptance_reobserves_physical_currentness_after_qa(
    tmp_path: Path,
) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    root = tmp_path / "content"
    target_id = _register_content(core, root)

    def drift_after_outcome_reconciliation(stage: str) -> None:
        assert stage == "candidate"
        delivered = root / "delivered" / "document.html"
        delivered.write_text(
            delivered.read_text(encoding="utf-8") + "<!-- post-QA drift -->\n",
            encoding="utf-8",
        )

    with pytest.raises(InvalidTransition, match="revision changed|currentness changed"):
        _complete_profile_mission(
            core,
            profile_key="content",
            target_id=target_id,
            steps=_content_steps(),
            before_stage_accept=drift_after_outcome_reconciliation,
        )


def test_external_extension_registers_outside_core_and_uses_same_mission_runtime(
    tmp_path: Path,
) -> None:
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    extension = ObservationCardExtensionProfile(
        tmp_path / "external-target",
        (
            {"observed_at": "2026-08-25T09:00:00Z", "value": 7},
            {"observed_at": "2026-08-25T10:00:00Z", "value": 11},
        ),
    )
    core.target_profiles.register(extension)
    result = _complete_profile_mission(
        core,
        profile_key="observation-card",
        target_id="field-summary",
        steps=(
            (EffectClass.WORKSPACE, "collect"),
            (EffectClass.BUILD, "render"),
            (EffectClass.RELEASE, "deliver"),
            (EffectClass.TEST, "verify"),
        ),
    )
    assert result["mission"]["status"] == "completed"
    assert result["snapshot"].attributes["phase"] == "delivered_verified"
    assert (tmp_path / "external-target" / "delivered" / "summary.json").read_text(
        encoding="utf-8"
    ) == '{"count":2,"maximum":11,"minimum":7}\n'


def test_factory_package_has_no_external_domain_or_git_schema_leakage() -> None:
    source_root = Path(__file__).parents[1] / "src" / "software_factory"
    package_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(source_root.rglob("*.py"))
    ).lower()
    for prohibited in (
        "observation-card",
        "field-summary",
        "patent studio",
        "celltonomy",
        "omni-",
    ):
        assert prohibited not in package_text
    content_source = (source_root / "profiles" / "content.py").read_text(encoding="utf-8").lower()
    for software_only in ("repository_id", "target_branch", "git_revision", "git_tree"):
        assert software_only not in content_source
