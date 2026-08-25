from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from librsi import Evidence, Hypothesis, deserialize_record

from software_factory.database import Database
from software_factory.errors import InvalidTransition
from software_factory.learning import LearningService


def service() -> LearningService:
    temporary_directory = TemporaryDirectory()
    database = Database(Path(temporary_directory.name) / "factory.sqlite3")
    now = "2026-01-01T00:00:00Z"
    with database.transaction() as db:
        db.execute(
            """INSERT INTO missions(
                   id,title,objective,status,autonomy_mode,created_at,updated_at
               ) VALUES('mission-1','mission','learn','active','full_autonomous',?,?)""",
            (now, now),
        )
        db.execute(
            """INSERT INTO agent_sessions(
                   id,mission_id,provider,role,desired_status,observed_status,
                   metadata_json,started_at
               ) VALUES(
                   'evaluator-1','mission-1','test','evaluator','running','active','{}',?
               )""",
            (now,),
        )
    learning = LearningService(database)
    learning._test_temporary_directory = temporary_directory  # type: ignore[attr-defined]
    return learning


def evaluated_candidate(learning: LearningService) -> dict[str, Any]:
    candidate = learning.create_candidate(
        mission_id="mission-1",
        signal_kind="failure",
        name="provider failure",
        detector_spec={
            "event_types": ["provider-finished"],
            "classifications": ["failure"],
            "where": [{"path": "attributes.exit_code", "op": "ne", "value": 0}],
        },
        response_spec={"action": "remediate", "mode": "governed"},
        discovery_evidence={"event_ids": ["historical-1", "historical-2"]},
    )
    for phase in ("historical_replay", "shadow", "canary", "qa"):
        learning.record_evaluation(
            candidate["id"],
            phase=phase,  # type: ignore[arg-type]
            disposition="passed",
            metrics={"precision": 1.0, "recall": 1.0},
            evidence_ids=[f"{phase}-evidence"],
            evaluator_session_id="evaluator-1",
        )
    return learning.store.one(
        "SELECT * FROM learned_signal_candidates WHERE id=?", (candidate["id"],)
    )  # type: ignore[return-value]


def test_historical_events_never_route_live_effects() -> None:
    learning = service()
    candidate = evaluated_candidate(learning)
    learning.promote_candidate(candidate["id"], activated_by_session_id="evaluator-1")
    event = learning.record_event(
        mission_id="mission-1",
        source_type="execution",
        source_id="old-execution",
        event_type="provider-finished",
        classification="failure",
        attributes={"exit_code": 1},
        historical_only=True,
    )
    assert learning.route_event(event["id"]) == []
    assert learning.store.all("SELECT id FROM signal_occurrences") == []


def test_recurring_unknown_sequences_become_candidates_not_active_rules() -> None:
    learning = service()
    for attempt in range(3):
        learning.record_event(
            mission_id="mission-1",
            source_type="execution",
            source_id=f"execution-{attempt}",
            event_type="candidate-submitted",
            classification="progress",
        )
        learning.record_event(
            mission_id="mission-1",
            source_type="qa",
            source_id=f"qa-{attempt}",
            event_type="integration-regressed",
            classification="failure",
        )
    candidates = learning.discover_recurring_sequences(
        "mission-1", min_support=3, sequence_length=2
    )
    matching = [row for row in candidates if row["signal_kind"] == "failure"]
    assert matching
    assert matching[0]["status"] == "candidate"
    assert learning.store.all("SELECT id FROM active_signal_bundles") == []


def test_promotion_requires_replay_shadow_canary_and_qa() -> None:
    learning = service()
    candidate = learning.create_candidate(
        mission_id="mission-1",
        signal_kind="success",
        name="fast stable migration",
        detector_spec={"event_types": ["migration-complete"]},
        response_spec={"action": "generalize", "mode": "governed"},
        discovery_evidence={"event_ids": ["event-1"]},
    )
    with pytest.raises(InvalidTransition, match="replay, shadow, canary, and QA"):
        learning.promote_candidate(candidate["id"])


def test_detector_and_route_promote_atomically_then_match_later_event() -> None:
    learning = service()
    candidate = evaluated_candidate(learning)
    bundle = learning.promote_candidate(candidate["id"], activated_by_session_id="evaluator-1")
    assert bundle["status"] == "active"
    assert learning.store.one(
        "SELECT status FROM learned_signal_candidates WHERE id=?", (candidate["id"],)
    ) == {"status": "promoted"}
    event = learning.record_event(
        mission_id="mission-1",
        source_type="execution",
        source_id="new-execution",
        event_type="provider-finished",
        classification="failure",
        attributes={"exit_code": 9},
        evidence_ids=["execution-log"],
    )
    occurrences = learning.route_event(event["id"])
    assert len(occurrences) == 1
    assert '"action":"remediate"' in occurrences[0]["routed_action_json"]


def test_harmful_or_false_positive_route_rolls_bundle_back() -> None:
    learning = service()
    candidate = evaluated_candidate(learning)
    bundle = learning.promote_candidate(candidate["id"])
    event = learning.record_event(
        mission_id="mission-1",
        source_type="execution",
        source_id="execution",
        event_type="provider-finished",
        classification="failure",
        attributes={"exit_code": 1},
    )
    occurrence = learning.route_event(event["id"])[0]
    learning.record_occurrence_effectiveness(
        occurrence["id"],
        disposition="false_positive",
        metrics={"target_was_actually_healthy": True},
        evidence_ids=["later-health-probe"],
    )
    assert learning.store.one(
        "SELECT status FROM active_signal_bundles WHERE id=?", (bundle["id"],)
    ) == {"status": "rolled_back"}


def test_reflection_hypothesis_and_counterexample_remain_distinct_records() -> None:
    learning = service()
    reflection = learning.create_reflection(
        mission_id="mission-1",
        reflection_type="checkpoint",
        source_type="incident",
        source_id="incident-1",
        evidence_ids=["execution-1", "qa-1"],
        observations={"same_strategy_failed_twice": True},
        conclusions={"causal_level": "architecture"},
        proposed_actions=[{"action": "compare_candidates"}],
        confidence=0.7,
    )
    hypothesis = learning.create_hypothesis(
        mission_id="mission-1",
        statement="The adapter boundary causes stale callback reuse",
        causal_model={"adapter": "callback", "failure": "stale result"},
        prediction={"new_generation_check": "prevents recurrence"},
        reflection_id=reflection["id"],
        confidence=0.6,
    )
    updated = learning.add_hypothesis_evidence(
        hypothesis["id"],
        evidence_type="counterexample",
        evidence_id="trace-with-valid-generation",
        weight=0.8,
        rationale={"observed": "failure persisted"},
    )
    assert updated["status"] == "weakened"
    assert updated["confidence"] < 0.6
    assert learning.store.all("SELECT id FROM hypotheses_v2") == []


def test_command_experiment_executes_real_process_and_updates_hypothesis() -> None:
    learning = service()
    hypothesis = learning.create_hypothesis(
        mission_id="mission-1",
        statement="The candidate emits the required observable marker",
        causal_model={"candidate": "command"},
        prediction={"stdout_contains": "FACTORY_OK"},
    )
    experiment = learning.design_experiment(
        mission_id="mission-1",
        experiment_type="command",
        hypothesis_id=hypothesis["id"],
        design={"command_kind": "isolated-python"},
        success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["FACTORY_OK"]},
        safety_constraints={"network": False, "shell": False},
    )
    run = learning.run_command_experiment(
        experiment["id"],
        command=[sys.executable, "-c", "print('FACTORY_OK')"],
        cwd=Path.cwd(),
    )
    assert run["disposition"] == "passed"
    assert run["exit_code"] == 0
    assert run["evidence_root"]
    updated_row = learning.store.one(
        """SELECT records.canonical_json
           FROM librsi_record_bindings AS bindings
           JOIN librsi_records AS records ON records.root=bindings.librsi_root
           WHERE bindings.operational_subject_type='learning_experiment'
             AND bindings.operational_subject_id=?
             AND bindings.semantic_role='hypothesis_update'""",
        (experiment["id"],),
    )
    updated = deserialize_record(updated_row["canonical_json"])
    assert isinstance(updated, Hypothesis)
    assert updated.status in {"testing", "supported"}
    assert updated.confidence > 0.5


def test_failed_experiment_is_counterevidence_not_a_supported_claim() -> None:
    learning = service()
    hypothesis = learning.create_hypothesis(
        mission_id="mission-1",
        statement="The command exits successfully",
        causal_model={"command": "false"},
        prediction={"exit_code": 0},
    )
    experiment = learning.design_experiment(
        mission_id="mission-1",
        experiment_type="command",
        hypothesis_id=hypothesis["id"],
        design={"command_kind": "isolated-python"},
        success_criteria={"accepted_exit_codes": [0]},
    )
    run = learning.run_command_experiment(
        experiment["id"],
        command=[sys.executable, "-c", "raise SystemExit(7)"],
        cwd=Path.cwd(),
    )
    assert run["disposition"] == "failed"
    evidence_row = learning.store.one(
        """SELECT records.canonical_json
           FROM librsi_record_bindings AS bindings
           JOIN librsi_records AS records ON records.root=bindings.librsi_root
           WHERE bindings.operational_subject_type='learning_experiment'
             AND bindings.operational_subject_id=?
             AND bindings.semantic_role='experiment_evidence'""",
        (experiment["id"],),
    )
    evidence = deserialize_record(evidence_row["canonical_json"])
    assert isinstance(evidence, Evidence)
    assert evidence.evidence_type == "counterexample"
    assert learning.store.all("SELECT id FROM hypothesis_evidence_v2") == []
