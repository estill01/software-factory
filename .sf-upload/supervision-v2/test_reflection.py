from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from software_factory import CoreService, InvalidTransition, Store
from software_factory.reflection import ReflectionService
from software_factory.util import canonical_json, json_load, new_id, utc_now


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
        assert len(first["hypothesis_ids"]) == 2
        hypotheses = store.all(
            "SELECT * FROM hypotheses WHERE origin_execution_id=? ORDER BY created_at",
            (first["reflection_execution_id"],),
        )
        assert {row["hypothesis_type"] for row in hypotheses} == {"causal", "problem_framing"}
        assert all(json_load(row["expected_evidence_json"], {}) for row in hypotheses)
        assert store.one(
            "SELECT COUNT(*) AS count FROM executions WHERE idempotency_key LIKE 'reflection:%'"
        )["count"] == 1


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
        assert len(result["hypothesis_ids"]) == 2

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
        assert ordinary_result["hypothesis_ids"] == []


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


def test_hypothesis_updates_are_versioned_deduplicated_and_validated() -> None:
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
        hypothesis = reflection.reflect_execution(execution)["hypothesis_ids"][0]

        updated = reflection.update_hypothesis(
            hypothesis,
            expected_version=1,
            status="challenged",
            supporting_evidence=(execution, execution),
            contrary_evidence=("counterexample", "counterexample"),
        )
        assert updated["state_version"] == 2
        assert updated["status"] == "challenged"
        assert json_load(updated["supporting_evidence_json"], []) == [execution]
        assert json_load(updated["contrary_evidence_json"], []) == ["counterexample"]
        assert updated["current_evidence_root"]

        with pytest.raises(Exception):
            reflection.update_hypothesis(
                hypothesis,
                expected_version=1,
                status="supported",
            )
        with pytest.raises(ValueError, match="unsupported"):
            reflection.update_hypothesis(
                hypothesis,
                expected_version=2,
                status="invented",
            )
