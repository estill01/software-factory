from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from software_factory import CoreService, InvalidTransition, RoleConflict, Store
from software_factory.util import canonical_json, digest_json, new_id, utc_now


def runtime() -> tuple[Store, CoreService, str]:
    directory = tempfile.TemporaryDirectory()
    # Keep the directory alive on the store for the duration of each test.
    store = Store(Path(directory.name) / "factory.db")
    store._test_directory = directory
    core = CoreService(store)
    project = core.create_project("supervision")
    mission = core.create_mission(
        project_id=project,
        title="Deliver capability",
        objective="Deliver and independently verify the capability",
    )
    return store, core, mission


def session(core: CoreService, mission: str, role: str) -> str:
    return core.create_agent_session(mission_id=mission, provider="test", role=role)


def obligation_and_work(
    core: CoreService, mission: str, *, strategy: str = "first"
) -> tuple[str, str]:
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description="Implement the capability",
        priority=50,
    )
    work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="implementation",
        title="Implement capability",
        description="Implement the capability end to end",
        expected_effect={"strategy_key": strategy},
        acceptance_spec={"candidate": [{"type": "focused_validation", "required": True}]},
        writable_scope=[],
    )
    core.select_work(
        work,
        expected_version=1,
        selected_by="selector",
        basis={"strategy_key": strategy, "problem_key": obligation},
    )
    return obligation, work


def finished_execution(
    store: Store,
    mission: str,
    work: str,
    obligation: str,
    *,
    status: str,
    strategy: str = "first",
    failure: str | None = None,
    unexpected_success: bool = False,
) -> str:
    execution_id = new_id("exe")
    with store.transaction() as db:
        db.execute(
            """INSERT INTO executions(
                id,mission_id,obligation_id,work_item_id,execution_type,status,
                strategy_key,attempt_number,idempotency_key,input_json,result_json,
                error_json,limits_json,usage_json,observed_effect_json,created_at,
                started_at,finished_at,state_version
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                execution_id,
                mission,
                obligation,
                work,
                "implementation",
                status,
                strategy,
                1,
                f"test:{execution_id}",
                "{}",
                canonical_json({"unexpected_success": unexpected_success}),
                canonical_json({"message": failure} if failure else {}),
                "{}",
                canonical_json({"input_tokens": 10}),
                canonical_json({"unexpected_success": unexpected_success}),
                utc_now(),
                utc_now(),
                utc_now(),
            ),
        )
        db.execute(
            "UPDATE work_items SET execution_status=?,updated_at=? WHERE id=?",
            ("submitted" if status == "succeeded" else status, utc_now(), work),
        )
    return execution_id


def test_material_change_gate_records_cheap_noop_then_finding() -> None:
    store, core, mission = runtime()
    watcher = session(core, mission, "mechanical_watcher")
    assignment = core.create_assignment(
        mission_id=mission,
        role="mechanical_watcher",
        supervisor_session_id=watcher,
        target_type="mission",
        target_id=mission,
        trigger_mode="material_change",
    )

    unchanged = core.run_check(assignment, reviewer_session_id=watcher)
    assert unchanged["status"] == "no_change"
    assert unchanged["material_changed"] is False

    core.add_obligation(
        mission_id=mission,
        obligation_type="diagnose",
        description="Resolve missing path",
    )
    changed = core.run_check(assignment, reviewer_session_id=watcher)
    assert changed["material_changed"] is True
    assert changed["status"] == "finding"
    assert changed["findings"][0]["kind"] == "mission_has_no_selected_supported_path"
    assert store.one("SELECT COUNT(*) AS n FROM supervision_checks")["n"] == 2


def test_failed_execution_keeps_obligation_open_and_routes_diagnosis() -> None:
    store, core, mission = runtime()
    obligation, work = obligation_and_work(core, mission)
    execution = finished_execution(
        store,
        mission,
        work,
        obligation,
        status="failed",
        failure="compile error",
    )

    observed = core.observe_execution(execution)

    assert observed["incident_id"].startswith("inc_")
    action = observed["adaptive_action"]
    assert action["action_kind"] == "diagnose"
    routed = store.one("SELECT * FROM work_items WHERE id=?", (action["selected_work_item_id"],))
    assert routed["planning_status"] == "selected"
    assert routed["work_type"] == "diagnosis"
    assert (
        store.one("SELECT status FROM obligations WHERE id=?", (obligation,))["status"]
        != "satisfied"
    )


def test_repeated_identical_failure_forces_alternative_and_blocks_same_retry() -> None:
    store, core, mission = runtime()
    obligation, work = obligation_and_work(core, mission, strategy="same")
    first = finished_execution(
        store, mission, work, obligation, status="failed", strategy="same", failure="same"
    )
    core.observe_execution(first)

    second_work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        parent_id=work,
        work_type="implementation",
        title="Retry same strategy",
        description="Retry without new evidence",
        expected_effect={"strategy_key": "same"},
    )
    core.select_work(
        second_work,
        expected_version=1,
        selected_by="selector",
        basis={"strategy_key": "same", "problem_key": obligation},
    )
    second = finished_execution(
        store,
        mission,
        second_work,
        obligation,
        status="failed",
        strategy="same",
        failure="same",
    )
    observed = core.observe_execution(second)
    assert observed["adaptive_action"]["action_kind"] == "alternative_strategy"

    third_work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        parent_id=work,
        work_type="implementation",
        title="Retry same strategy again",
        description="Still no new evidence",
        expected_effect={"strategy_key": "same"},
    )
    core.select_work(
        third_work,
        expected_version=1,
        selected_by="selector",
        basis={"strategy_key": "same", "problem_key": obligation},
    )
    with pytest.raises(InvalidTransition, match="identical strategy retry"):
        core.assert_strategy_allowed(third_work)


def test_new_evidence_can_authorize_a_retest_after_repeated_failure() -> None:
    store, core, mission = runtime()
    obligation, work = obligation_and_work(core, mission, strategy="same")
    for index in range(2):
        attempt_work = (
            work
            if index == 0
            else core.create_work_item(
                mission_id=mission,
                obligation_id=obligation,
                work_type="implementation",
                title=f"same {index}",
                description="same",
                expected_effect={"strategy_key": "same"},
            )
        )
        if index:
            core.select_work(
                attempt_work,
                expected_version=1,
                selected_by="selector",
                basis={"strategy_key": "same", "problem_key": obligation},
            )
        execution = finished_execution(
            store,
            mission,
            attempt_work,
            obligation,
            status="failed",
            strategy="same",
            failure="same",
        )
        core.observe_execution(execution)

    retest = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="implementation",
        title="Evidence-backed retest",
        description="Retest after a discriminating observation",
        expected_effect={"strategy_key": "same"},
    )
    core.select_work(
        retest,
        expected_version=1,
        selected_by="selector",
        basis={
            "strategy_key": "same",
            "problem_key": obligation,
            "new_evidence_ids": ["measurement-1"],
        },
    )
    core.assert_strategy_allowed(retest)


def test_narrow_containment_does_not_cancel_unrelated_execution() -> None:
    store, core, mission = runtime()
    supervisor = session(core, mission, "supervisor")
    obligation, work = obligation_and_work(core, mission)
    failed = finished_execution(
        store, mission, work, obligation, status="failed", failure="unsafe mutation"
    )
    observed = core.observe_execution(failed)

    other = new_id("exe")
    with store.transaction() as db:
        db.execute(
            """INSERT INTO executions(
                id,mission_id,execution_type,status,idempotency_key,input_json,result_json,
                error_json,limits_json,usage_json,created_at,state_version
            ) VALUES(?,?,?,'running',?,'{}','{}','{}','{}','{}',?,1)""",
            (other, mission, "implementation", f"test:{other}", utc_now()),
        )
    core.contain_incident(
        observed["incident_id"],
        actor_session_id=supervisor,
        containment={"scope": "causal execution only"},
    )
    assert store.one("SELECT status FROM executions WHERE id=?", (other,))["status"] == "running"
    assert (
        store.one("SELECT status FROM incidents WHERE id=?", (observed["incident_id"],))["status"]
        == "contained"
    )


def test_ineffective_correction_reopens_causal_hypothesis_at_higher_level() -> None:
    store, core, mission = runtime()
    reviewer = session(core, mission, "effectiveness_reviewer")
    obligation, work = obligation_and_work(core, mission)
    execution = finished_execution(
        store, mission, work, obligation, status="failed", failure="same"
    )
    incident = core.observe_execution(execution)["incident_id"]
    core.record_correction(
        incident,
        work_item_id=work,
        expected_effect={"compile": "passes"},
    )

    reviewed = core.record_effectiveness(
        incident,
        outcome="ineffective",
        reviewer_session_id=reviewer,
        observations={"compile": "still fails"},
    )
    assert reviewed["status"] == "open"
    action = store.one(
        """SELECT * FROM adaptive_actions WHERE incident_id=?
           AND action_kind='architecture_review'""",
        (incident,),
    )
    assert action["causal_level"] == "architecture"


def test_unexpected_success_creates_bounded_generalization_not_policy_adoption() -> None:
    store, core, mission = runtime()
    obligation, work = obligation_and_work(core, mission, strategy="fast")
    execution = finished_execution(
        store,
        mission,
        work,
        obligation,
        status="succeeded",
        strategy="fast",
        unexpected_success=True,
    )
    observed = core.observe_execution(execution)
    action = observed["adaptive_action"]
    assert action["action_kind"] == "success_generalization"
    routed = store.one("SELECT * FROM work_items WHERE id=?", (action["selected_work_item_id"],))
    assert routed["work_type"] == "reflection"
    assert "counterexample" in routed["description"].lower()
    assert store.one("SELECT COUNT(*) AS n FROM policies WHERE status='active'")["n"] == 0


def test_supervisor_role_and_mission_separation_are_enforced() -> None:
    _, core, mission = runtime()
    implementer = session(core, mission, "implementer")
    with pytest.raises(RoleConflict, match="supervisor role"):
        core.create_assignment(
            mission_id=mission,
            role="mechanical_watcher",
            supervisor_session_id=implementer,
            target_type="mission",
            target_id=mission,
        )


def test_duplicate_execution_observation_is_idempotent() -> None:
    store, core, mission = runtime()
    obligation, work = obligation_and_work(core, mission)
    execution = finished_execution(store, mission, work, obligation, status="failed", failure="x")
    first = core.observe_execution(execution)
    second = core.observe_execution(execution)
    assert second["duplicate"] is True
    assert second["strategy_outcome_id"] == first["strategy_outcome_id"]
    assert (
        store.one("SELECT COUNT(*) AS n FROM strategy_outcomes WHERE execution_id=?", (execution,))[
            "n"
        ]
        == 1
    )


def test_problem_solving_generation_preserves_no_null_next_action() -> None:
    store, core, mission = runtime()
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="diagnose",
        description="Find a viable path",
    )
    before = core.next_action(mission)
    assert before["action"] == "diagnose_reflect_or_replan"
    created = core.ensure_problem_solving(mission)
    assert created
    after = core.next_action(mission)
    assert after["action"] == "dispatch_ready_work"
    assert (
        store.one("SELECT obligation_id FROM work_items WHERE id=?", (created[0],))["obligation_id"]
        == obligation
    )


def test_target_fingerprint_changes_only_when_authoritative_state_changes() -> None:
    _, core, mission = runtime()
    first = core.target_fingerprint("mission", mission)
    second = core.target_fingerprint("mission", mission)
    assert first == second
    core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description="new obligation",
    )
    third = core.target_fingerprint("mission", mission)
    assert third != first
    assert len(third) == len(digest_json({}))
