from __future__ import annotations

from pathlib import Path

import pytest
from librsi import (
    Baseline,
    CandidateSnapshot,
    CandidateTrialBatch,
    Claim,
    Constraint,
    DecisionRule,
    EvaluationContract,
    Evidence,
    ExperimentEvaluator,
    Goal,
    Hypothesis,
    InterventionImplementationRequest,
    InterventionSpec,
    Measurement,
    Metric,
    Objective,
    Observation,
    RiskPolicy,
    StoppingRule,
    TargetSnapshot,
)

from software_factory import InvalidTransition, Store
from software_factory.evolution import EvolutionService
from software_factory.integrations.librsi import LibRSIIntegration
from software_factory.util import utc_now


def _runtime(tmp_path: Path) -> tuple[Store, LibRSIIntegration, str]:
    store = Store(tmp_path / "factory.sqlite3")
    now = utc_now()
    with store.transaction() as db:
        db.execute(
            "INSERT INTO projects(id,name,created_at,updated_at) VALUES('project','p',?,?)",
            (now, now),
        )
        db.execute(
            """INSERT INTO missions(
                   id,project_id,title,objective,status,autonomy_mode,created_at,updated_at
               ) VALUES('mission','project','m','compare','active','reviewed_autonomous',?,?)""",
            (now, now),
        )
        db.executemany(
            """INSERT INTO agent_sessions(
                   id,mission_id,provider,role,desired_status,observed_status,started_at
               ) VALUES(?,'mission','test',?,'idle','idle',?)""",
            [(session, session, now) for session in ("proposer", "reviewer", "selector")],
        )
    return store, LibRSIIntegration(store), "mission"


def _comparison_batch(
    integration: LibRSIIntegration, mission_id: str
) -> tuple[EvaluationContract, CandidateTrialBatch, RiskPolicy, TargetSnapshot]:
    target, baseline = integration.mission_snapshot(
        mission_id=mission_id,
        revision="baseline-v1",
        state={"quality": 80.0},
    )
    candidate_snapshot = TargetSnapshot(
        target=target,
        revision="candidate-v1",
        state={"quality": 82.0},
        lineage=(baseline.ref,),
    )
    metric = Metric(metric_id="quality", direction="increase", unit="points")
    goal = Goal(statement="Increase exact-target quality", target=target)
    objective = Objective.create(
        objective_id="increase-quality",
        metric=metric,
        semantics="maximize",
        goal=goal,
        minimum_effect=1.0,
    )
    contract = EvaluationContract.create(
        contract_id="factory-comparison",
        goal=goal,
        baseline=Baseline.create(snapshot=baseline, measurements={"quality": 80.0}),
        objectives=(objective,),
        stopping_rules=(
            StoppingRule(
                rule_id="two-exact-observations",
                kind="criteria-sufficient",
                condition="Stop after two exact baseline and candidate observations",
            ),
        ),
    )
    constraint = Constraint(statement="Retain target currentness", target=target)
    claim = Claim(
        statement="The exact baseline quality was observed",
        target=target,
        lineage=(baseline.ref,),
    )
    evidence = Evidence(
        evidence_type="support",
        data={"quality": 80.0},
        subject_refs=(claim.ref,),
        source_refs=(baseline.ref,),
        target_snapshot=baseline,
        weight=1.0,
        lineage=(claim.ref, baseline.ref),
    )
    intervention = InterventionSpec.create(
        intervention_id="candidate-change",
        baseline=baseline,
        kind="bounded-factory-change",
        specification={"candidate": "v1"},
        rationale=("Compare an exact non-authoritative candidate",),
        supporting_refs=(goal.ref, claim.ref),
        evidence=(evidence,),
        expected_effects={"quality": "increase"},
        risks=("target regression",),
        constraints=(constraint,),
        validation_plan={"comparison": "exact baseline and candidate"},
        rollback_expectations={"restore": baseline.root},
    )
    candidate = CandidateSnapshot.prepared(
        request=InterventionImplementationRequest.for_intervention(
            intervention, candidate_id="candidate-v1"
        ),
        snapshot=candidate_snapshot,
    )
    hypothesis = Hypothesis(
        statement="The exact candidate improves quality",
        target=target,
        predictions=({"quality_delta": ">= 1"},),
        lineage=(candidate.ref, contract.ref),
    )
    evaluator = ExperimentEvaluator()
    experiment = evaluator.design(
        experiment_id="factory-comparison",
        subject=hypothesis,
        kind="deterministic-comparison",
        metrics=(metric,),
        decision_rules=(
            DecisionRule(
                metric=metric.ref,
                kind="baseline_delta",
                minimum_effect=1.0,
                required_valid_trials=2,
            ),
        ),
        baseline_snapshot=baseline,
        candidate_snapshot=candidate_snapshot,
        repetitions=2,
        seeds=(1, 2),
    )
    results = []
    for role, snapshot, values in (
        ("baseline", baseline, (80.0, 80.0)),
        ("candidate", candidate_snapshot, (82.0, 82.0)),
    ):
        for index, value in enumerate(values):
            trial = evaluator.prepare_trial(experiment, index=index, role=role)
            observation = Observation(
                kind="software-factory.quality",
                value=value,
                target_snapshot=snapshot,
                source_refs=(trial.ref,),
            )
            measurement = Measurement(
                metric=metric.metric_id,
                metric_ref=metric.ref,
                value=value,
                unit=metric.unit,
                target_snapshot=snapshot,
                observation_refs=(observation.ref,),
            )
            results.append(
                evaluator.record_result(
                    experiment,
                    trial=trial,
                    disposition="valid",
                    observations=(observation,),
                    measurements=(measurement,),
                )
            )
    batch = CandidateTrialBatch.create(
        contract=contract,
        candidate=candidate,
        experiment=experiment,
        results=results,
    )
    return (
        contract,
        batch,
        RiskPolicy(policy_id="factory-risk", confidence_multiplier=1.0),
        baseline,
    )


def test_evidence_bound_comparison_is_canonical_but_not_operational_authority(
    tmp_path: Path,
) -> None:
    store, integration, mission_id = _runtime(tmp_path)
    contract, batch, risk, currentness = _comparison_batch(integration, mission_id)
    evolution = EvolutionService(store, semantic=integration)
    candidate = evolution.consider_selection(
        mission_id=mission_id,
        selection_group="group-1",
        selection_type="strategy",
        candidate_key="candidate-v1",
        candidate={"librsi_candidate_root": batch.candidate.root},
        evidence={"candidate_trial_batch_root": batch.root},
        expected_value={"quality": "increase"},
        proposer_session_id="proposer",
    )
    evolution.review_selection(
        candidate["id"],
        reviewer_session_id="reviewer",
        disposition="accept",
        findings={"exact_comparison_required": True},
        evidence_ids=[batch.root],
    )
    decision = integration.record_comparison(
        mission_id=mission_id,
        subject_type="selection_group",
        subject_id="group-1",
        selection_id="selection-1",
        contract=contract,
        batches=(batch,),
        risk_policy=risk,
        currentness=currentness,
    )
    assert decision.disposition == "selected"
    assert decision.selected == (batch.candidate.ref,)
    with pytest.raises(InvalidTransition, match="stale"):
        evolution.select_candidate(
            candidate["id"],
            selector_session_id="selector",
            rationale={"decision_root": decision.root},
            decision_root=decision.root,
            currentness_root="stale-currentness",
        )
    selected = evolution.select_candidate(
        candidate["id"],
        selector_session_id="selector",
        rationale={"decision_root": decision.root},
        decision_root=decision.root,
        currentness_root=currentness.root,
    )
    assert selected["status"] == "selected"
    assert store.one(
        """SELECT librsi_root FROM librsi_record_bindings
           WHERE operational_subject_type='selection_group'
             AND operational_subject_id='group-1'
             AND semantic_role='selection_decision'"""
    ) == {"librsi_root": decision.root}
    assert store.one("SELECT COUNT(*) AS count FROM work_items") == {"count": 0}


def test_comparison_and_selection_reject_live_mission_currentness_advance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, integration, mission_id = _runtime(tmp_path)
    contract, batch, risk, currentness = _comparison_batch(integration, mission_id)
    evolution = EvolutionService(store, semantic=integration)
    candidate = evolution.consider_selection(
        mission_id=mission_id,
        selection_group="stale-group",
        selection_type="strategy",
        candidate_key="candidate-v1",
        candidate={"librsi_candidate_root": batch.candidate.root},
        evidence={"candidate_trial_batch_root": batch.root},
        expected_value={"quality": "increase"},
        proposer_session_id="proposer",
    )
    evolution.review_selection(
        candidate["id"],
        reviewer_session_id="reviewer",
        disposition="accept",
        findings={"exact_comparison_required": True},
        evidence_ids=[batch.root],
    )
    decision = integration.record_comparison(
        mission_id=mission_id,
        subject_type="selection_group",
        subject_id="stale-group",
        selection_id="stale-selection",
        contract=contract,
        batches=(batch,),
        risk_policy=risk,
        currentness=currentness,
    )
    original = integration.require_live_currentness
    gates = 0

    def advance_after_first_gate(*, mission_id: str, snapshot: TargetSnapshot) -> None:
        nonlocal gates
        gates += 1
        original(mission_id=mission_id, snapshot=snapshot)
        if gates == 1:
            with store.transaction() as db:
                db.execute(
                    "UPDATE missions SET state_version=state_version+1 WHERE id=?", (mission_id,)
                )

    monkeypatch.setattr(integration, "require_live_currentness", advance_after_first_gate)
    with pytest.raises(InvalidTransition, match="currentness is stale"):
        evolution.select_candidate(
            candidate["id"],
            selector_session_id="selector",
            rationale={"decision_root": decision.root},
            decision_root=decision.root,
            currentness_root=currentness.root,
        )
    assert gates == 2
    assert store.one("SELECT state_version FROM missions WHERE id=?", (mission_id,)) == {
        "state_version": 1
    }
    assert store.one("SELECT status FROM selection_records_v2 WHERE id=?", (candidate["id"],)) != {
        "status": "selected"
    }
    monkeypatch.setattr(integration, "require_live_currentness", original)
    with store.transaction() as db:
        db.execute("UPDATE missions SET state_version=state_version+1 WHERE id=?", (mission_id,))
    with pytest.raises(InvalidTransition, match="currentness is stale"):
        integration.record_comparison(
            mission_id=mission_id,
            subject_type="selection_group",
            subject_id="another-group",
            selection_id="another-selection",
            contract=contract,
            batches=(batch,),
            risk_policy=risk,
            currentness=currentness,
        )
    with pytest.raises(InvalidTransition, match="currentness is stale"):
        evolution.select_candidate(
            candidate["id"],
            selector_session_id="selector",
            rationale={"decision_root": decision.root},
            decision_root=decision.root,
            currentness_root=currentness.root,
        )
