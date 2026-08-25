from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from librsi import Hypothesis, HypothesisPolicy, deserialize_record

from software_factory import CoreService, InvalidTransition, Store
from software_factory.reflection import ReflectionService
from software_factory.util import canonical_json, new_id, utc_now


def make_runtime(root: Path) -> tuple[Store, CoreService, ReflectionService, str]:
    store = Store(root / "factory.sqlite3")
    core = CoreService(store)
    project = core.create_project("reflection")
    mission = core.create_mission(
        project_id=project,
        title="Reflect on implementation",
        objective="Learn from observed outcomes without stopping the mission",
    )
    return store, core, ReflectionService(store, work_items=core.work_items), mission


def add_selected_work(core: CoreService, mission: str, *, strategy: str) -> tuple[str, str]:
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description=f"Implement with {strategy}",
        priority=80,
    )
    work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        work_type="implementation",
        title=f"Implement {strategy}",
        description=f"Attempt implementation strategy {strategy}",
        expected_effect={"strategy_key": strategy},
        acceptance_spec={"candidate": [{"type": "focused_validation", "required": True}]},
        strategy_key=strategy,
    )
    core.select_work(
        work,
        expected_version=1,
        selected_by="selector",
        basis={"strategy_key": strategy, "problem_key": obligation},
    )
    return obligation, work


def observed_execution(
    store: Store,
    mission: str,
    obligation: str,
    work: str,
    *,
    strategy: str,
    status: str,
    error: str | None = None,
    unexpected_success: bool = False,
) -> str:
    execution = new_id("exe")
    now = utc_now()
    with store.transaction() as db:
        db.execute(
            """INSERT INTO executions(
                id,mission_id,obligation_id,work_item_id,execution_type,status,
                strategy_key,attempt_number,idempotency_key,input_json,result_json,
                error_json,limits_json,usage_json,observed_effect_json,created_at,
                started_at,finished_at,state_version
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                execution,
                mission,
                obligation,
                work,
                "implementation",
                status,
                strategy,
                1,
                f"test:{execution}",
                "{}",
                canonical_json({"unexpected_success": unexpected_success}),
                canonical_json({"message": error} if error else {}),
                "{}",
                canonical_json({"input_tokens": 10, "output_tokens": 4}),
                canonical_json(
                    {
                        "unexpected_success": unexpected_success,
                        "capability_delta": 1 if status == "succeeded" else 0,
                    }
                ),
                now,
                now,
                now if status in {"succeeded", "failed", "abandoned", "cancelled"} else None,
            ),
        )
    return execution


def test_failure_reflection_is_idempotent_and_retains_competing_hypotheses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="incumbent")
        execution = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="incumbent",
            status="failed",
            error="same failure",
        )

        first = reflection.reflect_execution(execution)
        second = reflection.reflect_execution(execution)

        assert first["reflection_execution_id"] == second["reflection_execution_id"]
        assert first["recommended_next_action"] == "run_discriminating_experiment"
        assert first["hypothesis_roots"] == second["hypothesis_roots"]
        assert len(first["hypothesis_roots"]) == 2
        hypotheses = [
            deserialize_record(
                store.one("SELECT canonical_json FROM librsi_records WHERE root=?", (root,))[
                    "canonical_json"
                ]
            )
            for root in first["hypothesis_roots"]
        ]
        assert all(isinstance(item, Hypothesis) for item in hypotheses)
        assert all(item.predictions for item in hypotheses if isinstance(item, Hypothesis))
        assert store.one("SELECT COUNT(*) AS count FROM hypotheses") == {"count": 0}
        assert store.one(
            "SELECT COUNT(*) AS count FROM work_items WHERE lane_key=?",
            (f"librsi-experiment:{execution}",),
        ) == {"count": 1}
        assert store.one(
            """SELECT COUNT(*) AS count FROM events
               WHERE event_type='librsi.semantic_slice_cut_over' AND subject_id=?""",
            (execution,),
        ) == {"count": 1}
        receipt = store.one(
            "SELECT * FROM librsi_cutover_receipts_v2 WHERE source_execution_id=?",
            (execution,),
        )
        assert receipt["receipt_root"] == first["cutover_receipt_root"]
        assert receipt["parity_disposition"] == "matched"
        assert receipt["authority_posture"] == "authoritative"
        assert receipt["source_commit"] == "1d81f6180b40435e10145756a2d99e6f334d31bc"
        assert execution not in first["hypothesis_roots"]
        assert (
            store.one(
                "SELECT COUNT(*) AS count FROM executions WHERE idempotency_key LIKE 'reflection:%'"
            )["count"]
            == 1
        )


def test_shadow_parity_is_independent_and_fails_before_semantic_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MutatingPolicy(HypothesisPolicy):
        def create(self, **kwargs: object) -> Hypothesis:
            kwargs["statement"] = f"wrong semantic statement: {kwargs['statement']}"
            return super().create(**kwargs)  # type: ignore[arg-type]

    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="incumbent")
        execution = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="incumbent",
            status="failed",
            error="same failure",
        )
        monkeypatch.setattr(
            "software_factory.integrations.librsi.service.HypothesisPolicy", MutatingPolicy
        )
        with pytest.raises(InvalidTransition, match="shadow comparison"):
            reflection.reflect_execution(execution)
        assert store.one("SELECT COUNT(*) AS count FROM librsi_records") == {"count": 0}
        assert store.one(
            "SELECT COUNT(*) AS count FROM work_items WHERE lane_key=?",
            (f"librsi-experiment:{execution}",),
        ) == {"count": 0}
        assert store.one("SELECT COUNT(*) AS count FROM librsi_cutover_receipts_v2") == {"count": 0}


def test_unexpected_success_and_ordinary_success_choose_different_routes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="fast-path")
        unexpected = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="fast-path",
            status="succeeded",
            unexpected_success=True,
        )
        result = reflection.reflect_execution(unexpected)
        assert result["recommended_next_action"] == "bounded_replay_and_counterexample_search"
        assert len(result["hypothesis_roots"]) == 2

        obligation2, work2 = add_selected_work(core, mission, strategy="normal-path")
        ordinary = observed_execution(
            store,
            mission,
            obligation2,
            work2,
            strategy="normal-path",
            status="succeeded",
        )
        ordinary_result = reflection.reflect_execution(ordinary)
        assert ordinary_result["recommended_next_action"] == "retain_current_strategy"
        assert ordinary_result["hypothesis_roots"] == []


def test_unexpected_success_changes_work_only_after_bounded_supporting_evidence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="bounded-reuse")
        source = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="bounded-reuse",
            status="succeeded",
            unexpected_success=True,
        )
        semantic = reflection.reflect_execution(source)
        current_root = semantic["hypothesis_roots"][0]

        first_execution = observed_execution(
            store,
            mission,
            obligation,
            semantic["experiment_work_item_id"],
            strategy="matched-replay-1",
            status="succeeded",
        )
        first = reflection.semantic_integration.record_experiment_outcome(
            experiment_execution_id=first_execution,
            hypothesis_root=current_root,
            disposition="supported",
            data={"replicate": 1, "benefit_recurred": True},
        )
        assert first["status"] != "supported"
        assert first["followup_work_item_id"] is None

        second_execution = observed_execution(
            store,
            mission,
            obligation,
            semantic["experiment_work_item_id"],
            strategy="matched-replay-2",
            status="succeeded",
        )
        second = reflection.semantic_integration.record_experiment_outcome(
            experiment_execution_id=second_execution,
            hypothesis_root=first["hypothesis_root"],
            disposition="supported",
            data={"replicate": 2, "benefit_recurred": True},
        )
        assert second["status"] == "supported"
        assert second["followup_work_item_id"]
        assert store.one(
            "SELECT planning_status,acceptance_status FROM work_items WHERE id=?",
            (second["followup_work_item_id"],),
        ) == {"planning_status": "proposed", "acceptance_status": "pending"}
        assert store.one("SELECT status FROM obligations WHERE id=?", (obligation,)) == {
            "status": "open"
        }


def test_experiment_evidence_rejects_unassigned_and_cross_mission_executions() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="bounded-reuse")
        source = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="bounded-reuse",
            status="succeeded",
            unexpected_success=True,
        )
        semantic = reflection.reflect_execution(source)
        hypothesis_root = semantic["hypothesis_roots"][0]

        unrelated = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="unassigned-replay",
            status="succeeded",
        )
        with pytest.raises(InvalidTransition, match="experiment binding"):
            reflection.semantic_integration.record_experiment_outcome(
                experiment_execution_id=unrelated,
                hypothesis_root=hypothesis_root,
                disposition="supported",
                data={"replicate": "unassigned"},
            )

        other_project = core.create_project("other-reflection")
        other_mission = core.create_mission(
            project_id=other_project,
            title="Other mission",
            objective="Do not accept cross-mission experiment evidence",
        )
        other_obligation, other_work = add_selected_work(
            core, other_mission, strategy="cross-mission"
        )
        cross_mission = observed_execution(
            store,
            other_mission,
            other_obligation,
            other_work,
            strategy="cross-mission",
            status="succeeded",
        )
        with pytest.raises(InvalidTransition, match="same-mission experiment binding"):
            reflection.semantic_integration.record_experiment_outcome(
                experiment_execution_id=cross_mission,
                hypothesis_root=hypothesis_root,
                disposition="supported",
                data={"replicate": "cross-mission"},
            )


def test_experiment_evidence_rejects_forged_lineage_without_host_admission() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="bounded-reuse")
        source = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="bounded-reuse",
            status="succeeded",
            unexpected_success=True,
        )
        semantic = reflection.reflect_execution(source)
        original = deserialize_record(
            store.one(
                "SELECT canonical_json FROM librsi_records WHERE root=?",
                (semantic["hypothesis_roots"][0],),
            )["canonical_json"]
        )
        assert isinstance(original, Hypothesis)
        forged = Hypothesis(
            target=original.target,
            statement="Forged content that merely names the expected root in lineage",
            causal_model=original.causal_model,
            predictions=original.predictions,
            confidence=original.confidence,
            status=original.status,
            lineage=(*original.lineage, original.ref),
            metadata=original.metadata,
        )
        reflection.semantic_integration._persist_records((forged,))
        experiment_execution = observed_execution(
            store,
            mission,
            obligation,
            semantic["experiment_work_item_id"],
            strategy="forged-lineage",
            status="succeeded",
        )
        with pytest.raises(InvalidTransition, match="admitted immutable descendant"):
            reflection.semantic_integration.record_experiment_outcome(
                experiment_execution_id=experiment_execution,
                hypothesis_root=forged.root,
                disposition="supported",
                data={"replicate": "forged"},
            )


def test_reflection_rejects_nonterminal_execution_and_bad_timescale() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="running")
        execution = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="running",
            status="running",
        )
        with pytest.raises(InvalidTransition, match="terminal observed"):
            reflection.reflect_execution(execution)
        with pytest.raises(ValueError, match="timescale"):
            reflection.reflect_mission(mission, timescale="hourly")


def test_checkpoint_and_terminal_reflection_detect_recurrence_and_are_idempotent() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        for index in range(2):
            obligation, work = add_selected_work(core, mission, strategy=f"repeat-{index}")
            execution = observed_execution(
                store,
                mission,
                obligation,
                work,
                strategy="repeated-strategy",
                status="failed",
                error="same fingerprint",
            )
            core.adaptive.observe_execution(execution)

        checkpoint = reflection.reflect_mission(mission, timescale="checkpoint")
        duplicate = reflection.reflect_mission(mission, timescale="checkpoint")
        terminal = reflection.reflect_mission(mission, timescale="terminal")

        assert checkpoint["reflection_execution_id"] == duplicate["reflection_execution_id"]
        assert checkpoint["outcome_count"] == 2
        assert checkpoint["recurring_sequences"][0]["count"] == 2
        assert checkpoint["recommended_next_action"] == "evaluate_reusable_candidates"
        assert terminal["recommended_next_action"] == "terminal_verify_open_items"
        assert terminal["reflection_execution_id"] != checkpoint["reflection_execution_id"]


def test_failed_experiment_is_null_evidence_not_falsification_or_authorization() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store, core, reflection, mission = make_runtime(Path(directory))
        obligation, work = add_selected_work(core, mission, strategy="hypothesis")
        execution = observed_execution(
            store,
            mission,
            obligation,
            work,
            strategy="hypothesis",
            status="failed",
            error="needs evidence",
        )
        semantic = reflection.reflect_execution(execution)
        hypothesis = semantic["hypothesis_roots"][0]
        experiment_execution = observed_execution(
            store,
            mission,
            obligation,
            semantic["experiment_work_item_id"],
            strategy="discriminator",
            status="failed",
            error="experiment harness did not produce a valid observation",
        )
        update = reflection.semantic_integration.record_experiment_outcome(
            experiment_execution_id=experiment_execution,
            hypothesis_root=hypothesis,
            disposition="counterexample",
            data={"harness": "failed"},
        )
        assert update["status"] != "rejected"
        assert update["operational_transition_authorized"] is False
        assert store.one(
            "SELECT acceptance_status FROM work_items WHERE id=?",
            (semantic["experiment_work_item_id"],),
        ) == {"acceptance_status": "pending"}
        assert store.one("SELECT status FROM obligations WHERE id=?", (obligation,)) == {
            "status": "open"
        }
