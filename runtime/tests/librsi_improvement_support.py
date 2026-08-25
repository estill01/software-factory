from __future__ import annotations

from librsi import (
    Action,
    ActionResult,
    Baseline,
    CandidateSnapshot,
    CandidateTrialBatch,
    Constraint,
    DecisionRule,
    EvaluationContract,
    Evidence,
    ExperimentEvaluator,
    Goal,
    Guardrail,
    Hypothesis,
    ImprovementBudget,
    ImprovementCycleProposal,
    ImprovementRequest,
    ImprovementResult,
    InterventionImplementationRequest,
    InterventionSpec,
    Measurement,
    Metric,
    Objective,
    Observation,
    OperationalizationPolicy,
    OperationalizationRequest,
    Question,
    ReasoningResult,
    RiskPolicy,
    StoppingRule,
    TargetSnapshot,
    cycle_request_from_action,
    improve,
    investigate,
    investigation_experiment_request_from_action,
    make_cycle_result,
    make_investigation_experiment_result,
    make_investigation_observation_content,
    make_reasoning_action_result,
    reasoning_request_from_action,
)

from software_factory.integrations.librsi import LibRSIIntegration


class _Reasoner:
    def reason(self, action: Action) -> ActionResult:
        request = reasoning_request_from_action(action)
        return make_reasoning_action_result(
            action=action,
            result=ReasoningResult.propose(
                request=request,
                content=make_investigation_observation_content(request, measurements=("quality",)),
            ),
        )


class _Experimenter:
    def experiment(self, action: Action) -> ActionResult:
        request = investigation_experiment_request_from_action(action)
        relationship = "counterexample" if request.branch.branch_id.endswith("1") else "support"
        evidence = tuple(
            Evidence(
                evidence_type=relationship,
                data={"replicate": index},
                subject_refs=(request.branch.hypothesis.ref,),
                source_refs=(request.experiment.ref,),
                target_snapshot=request.investigation.target_snapshot,
                weight=1.0,
            )
            for index in (1, 2)
        )
        from librsi import InvestigationEvidenceBatch

        return make_investigation_experiment_result(
            action=action,
            batch=InvestigationEvidenceBatch.collected(request=request, evidence=evidence),
        )


class _Provider:
    def __init__(
        self,
        *,
        contract: EvaluationContract,
        baseline: TargetSnapshot,
        candidate_id: str,
    ) -> None:
        self.contract = contract
        self.baseline = baseline
        self.candidate_id = candidate_id

    def resource_claim(self, action: Action) -> float:
        cycle_request_from_action(action)
        return float(action.budget_reservation["units"])

    def improve_cycle(self, action: Action) -> ActionResult:
        cycle = cycle_request_from_action(action)
        investigation = investigate(
            question=cycle.improvement.question,
            target_snapshot=self.baseline,
            investigation_id=f"investigate-{self.candidate_id}",
            initial_hypotheses=cycle.improvement.initial_hypotheses,
            max_hypotheses=2,
            max_experiments=2,
            max_redesigns_per_hypothesis=0,
            reasoner=_Reasoner(),
            experimenter=_Experimenter(),
        )
        supported = next(
            branch for branch in investigation.branches if branch.status == "supported"
        )
        constraint = self.contract.constraints[0]
        intervention = InterventionSpec.create(
            intervention_id=f"intervention-{self.candidate_id}",
            baseline=self.baseline,
            kind="bounded-factory-change",
            specification={"candidate": self.candidate_id},
            rationale=("Test the supported exact-target mechanism",),
            supporting_refs=(supported.hypothesis.ref,),
            evidence=supported.evidence,
            expected_effects={"quality": "increase"},
            risks=("quality regression",),
            constraints=(constraint,),
            validation_plan={"comparison": "exact baseline and candidate"},
            rollback_expectations={"restore": self.baseline.root},
        )
        candidate = CandidateSnapshot.prepared(
            request=InterventionImplementationRequest.for_intervention(
                intervention, candidate_id=self.candidate_id
            ),
            snapshot=TargetSnapshot(
                target=self.baseline.target,
                revision=f"candidate-{self.candidate_id}",
                state={"quality": 82.0, "candidate": self.candidate_id},
                lineage=(self.baseline.ref,),
            ),
        )
        metric = self.contract.objectives[0].metric
        guardrail_metric = self.contract.guardrails[0].metric
        evaluator = ExperimentEvaluator()
        experiment = evaluator.design(
            experiment_id=f"compare-{self.candidate_id}",
            subject=supported.hypothesis,
            kind="deterministic-comparison",
            metrics=(metric, guardrail_metric),
            decision_rules=(
                DecisionRule(
                    metric=metric.ref,
                    kind="baseline_delta",
                    minimum_effect=1.0,
                    required_valid_trials=2,
                ),
                DecisionRule(
                    metric=guardrail_metric.ref,
                    kind="threshold",
                    operator="<=",
                    threshold=0.0,
                    required_valid_trials=2,
                ),
            ),
            baseline_snapshot=self.baseline,
            candidate_snapshot=candidate.snapshot,
            repetitions=2,
            seeds=(1, 2),
        )
        results = []
        for role, snapshot, values in (
            ("baseline", self.baseline, (80.0, 80.0)),
            ("candidate", candidate.snapshot, (82.0, 82.0)),
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
                guardrail_measurement = Measurement(
                    metric=guardrail_metric.metric_id,
                    metric_ref=guardrail_metric.ref,
                    value=0.0,
                    unit=guardrail_metric.unit,
                    target_snapshot=snapshot,
                    observation_refs=(observation.ref,),
                )
                results.append(
                    evaluator.record_result(
                        experiment,
                        trial=trial,
                        disposition="valid",
                        observations=(observation,),
                        measurements=(measurement, guardrail_measurement),
                    )
                )
        batch = CandidateTrialBatch.create(
            contract=self.contract,
            candidate=candidate,
            experiment=experiment,
            results=results,
        )
        proposal = ImprovementCycleProposal.create(
            request=cycle,
            investigation=investigation,
            batches=(batch,),
        )
        return make_cycle_result(action=action, proposal=proposal, resource_units=1.0)


def accepted_improvement_result(
    integration: LibRSIIntegration,
    mission_id: str,
    *,
    candidate_id: str,
) -> tuple[ImprovementResult, TargetSnapshot, CandidateSnapshot]:
    target, baseline = integration.mission_snapshot(
        mission_id=mission_id,
        revision=f"improvement-baseline-{candidate_id}",
        state={"quality": 80.0, "safety_regressions": 0.0},
    )
    metric = Metric(metric_id="quality", direction="increase", unit="points")
    guardrail_metric = Metric(
        metric_id="safety_regressions",
        direction="decrease",
        role="guardrail",
        unit="count",
    )
    goal = Goal(statement="Increase exact-target quality", target=target)
    objective = Objective.create(
        objective_id="increase-quality",
        metric=metric,
        semantics="maximize",
        goal=goal,
        minimum_effect=1.0,
    )
    constraint = Constraint(
        statement="Retain the exact Factory mission boundary",
        target=target,
        lineage=(baseline.ref,),
    )
    contract = EvaluationContract.create(
        contract_id=f"factory-improvement-{candidate_id}",
        goal=goal,
        baseline=Baseline.create(
            snapshot=baseline,
            measurements={"quality": 80.0, "safety_regressions": 0.0},
        ),
        objectives=(objective,),
        constraints=(constraint,),
        guardrails=(
            Guardrail.create(
                guardrail_id="quality-no-regression",
                metric=guardrail_metric,
                semantics="no-regression",
                constraint=constraint,
            ),
        ),
        stopping_rules=(
            StoppingRule(
                rule_id="accepted-candidate",
                kind="criteria-sufficient",
                condition="Stop after one evidence-bound accepted candidate",
            ),
        ),
    )
    operationalization_request = OperationalizationRequest.create(
        request_id=f"operationalize-{candidate_id}",
        goal=goal,
        current_snapshot=baseline,
    )
    operationalization = OperationalizationPolicy().accept_typed(
        operationalization_request, contract
    )
    question = Question(
        prompt="Which exact bounded change improves the objective?",
        target=target,
        lineage=(baseline.ref,),
    )
    seeds = tuple(
        Hypothesis(
            statement=f"{label} mechanism may improve quality",
            target=target,
            causal_model={"mechanism": label},
            predictions=({"quality": "increase"},),
            source_refs=(question.ref,),
            lineage=(question.ref,),
        )
        for label in ("primary", "alternative")
    )
    request = ImprovementRequest.create(
        request_id=f"improve-{candidate_id}",
        operationalization=operationalization,
        question=question,
        initial_hypotheses=seeds,
        risk_policy=RiskPolicy(policy_id=f"risk-{candidate_id}", confidence_multiplier=1.0),
        budget=ImprovementBudget(
            max_iterations=1,
            max_experiments=9,
            max_retries=0,
            max_resource_units=2.0,
            diminishing_return_patience=1,
        ),
    )
    result = improve(
        request,
        provider=_Provider(contract=contract, baseline=baseline, candidate_id=candidate_id),
        current_snapshot=baseline,
    )
    if result.handoff is None or len(result.handoff.selection.selected) != 1:
        raise AssertionError("test improvement did not select exactly one candidate")
    selected_root = result.handoff.selection.selected[0].root
    selected = next(
        batch.candidate
        for iteration in result.iterations
        for batch in iteration.proposal.batches
        if batch.candidate.root == selected_root
    )
    return result, baseline, selected
