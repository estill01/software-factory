from __future__ import annotations

import pytest

from rsi_core import CommandObservation, RSIKernel, RSITransitionError


def test_hypothesis_updates_distinguish_support_counterexample_and_null() -> None:
    hypotheses = RSIKernel().hypotheses
    proposal = hypotheses.propose(
        scope_id="system-a",
        statement="  generation checks prevent stale callback reuse  ",
        causal_model={"cause": "stale generation"},
        prediction={"recurrence": "zero"},
        confidence=0.5,
    )
    support = hypotheses.apply_evidence(
        current_confidence=proposal.confidence,
        evidence_type="support",
        evidence_id="experiment-pass",
        weight=0.7,
    )
    counterexample = hypotheses.apply_evidence(
        current_confidence=support.confidence,
        evidence_type="counterexample",
        evidence_id="experiment-fail",
        weight=0.7,
    )
    null = hypotheses.apply_evidence(
        current_confidence=counterexample.confidence,
        evidence_type="null",
        evidence_id="experiment-invalid",
        weight=0.0,
    )

    assert proposal.statement == "generation checks prevent stale callback reuse"
    assert support.confidence > proposal.confidence
    assert counterexample.status == "weakened"
    assert null.confidence == counterexample.confidence


def test_reflections_and_hypotheses_require_bounded_exact_evidence() -> None:
    kernel = RSIKernel()
    identity = kernel.reflections.identify(
        reflection_type="checkpoint",
        source_type="incident",
        source_id="incident-1",
        evidence_ids=["trace-b", "trace-a"],
        observations={"recurrence": 2},
        confidence=0.7,
    )
    assert identity.evidence_ids == ("trace-a", "trace-b")
    with pytest.raises(ValueError, match="exact evidence"):
        kernel.reflections.identify(
            reflection_type="checkpoint",
            source_type="incident",
            source_id="incident-1",
            evidence_ids=[],
            observations={},
            confidence=0.7,
        )
    with pytest.raises(ValueError, match="confidence"):
        kernel.hypotheses.propose(
            scope_id="scope",
            statement="candidate",
            causal_model={},
            prediction={},
            confidence=1.1,
        )
    with pytest.raises(ValueError, match="exact evidence id"):
        kernel.hypotheses.apply_evidence(
            current_confidence=0.5,
            evidence_type="support",
            evidence_id="",
            weight=0.5,
        )


def test_hypothesis_thresholds_and_qualifying_evidence_are_explicit() -> None:
    policy = RSIKernel().hypotheses
    supported = policy.apply_evidence(
        current_confidence=0.7,
        evidence_type="support",
        evidence_id="strong-pass",
        weight=0.5,
    )
    rejected = policy.apply_evidence(
        current_confidence=0.25,
        evidence_type="counterexample",
        evidence_id="strong-failure",
        weight=0.5,
    )
    bounded = policy.apply_evidence(
        current_confidence=0.5,
        evidence_type="boundary",
        evidence_id="scope-boundary",
        weight=0.4,
    )
    assert supported.status == "supported"
    assert rejected.status == "rejected"
    assert bounded.status == "testing"


def test_experiment_policy_interprets_valid_pass_failure_and_invalid_run() -> None:
    experiments = RSIKernel().experiments
    command_input = experiments.command_input(
        experiment_id="experiment-1",
        experiment_type="command",
        status="designed",
        design={"isolation": "subprocess"},
        success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["OK"]},
        command=["python", "probe.py"],
        cwd="/workspace",
    )
    passed = experiments.evaluate_command_result(
        exact_input_root=command_input.exact_input_root,
        success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["OK"]},
        observation=CommandObservation(exit_code=0, stdout="OK\n", stderr=""),
    )
    failed = experiments.evaluate_command_result(
        exact_input_root=command_input.exact_input_root,
        success_criteria={"accepted_exit_codes": [0]},
        observation=CommandObservation(exit_code=7, stdout="", stderr="assertion failed"),
    )
    invalid = experiments.evaluate_command_result(
        exact_input_root=command_input.exact_input_root,
        success_criteria={"accepted_exit_codes": [0]},
        observation=CommandObservation(exit_code=None, stdout="", stderr="timed out", invalid=True),
    )

    assert passed.hypothesis_evidence_type == "support"
    assert failed.hypothesis_evidence_type == "counterexample"
    assert invalid.hypothesis_evidence_type == "null"
    assert invalid.hypothesis_evidence_weight == 0.0


def test_experiment_execution_requires_the_reviewed_design_state() -> None:
    with pytest.raises(RSITransitionError, match="awaiting execution"):
        RSIKernel().experiments.command_input(
            experiment_id="experiment-1",
            experiment_type="command",
            status="running",
            design={"isolation": "subprocess"},
            success_criteria={"accepted_exit_codes": [0]},
            command=["python", "probe.py"],
            cwd="/workspace",
        )


def test_experiment_design_and_command_input_fail_closed() -> None:
    policy = RSIKernel().experiments
    with pytest.raises(ValueError, match="design and success criteria"):
        policy.validate_design(design={}, success_criteria={})
    with pytest.raises(RSITransitionError, match="not a command"):
        policy.command_input(
            experiment_id="experiment-1",
            experiment_type="simulation",
            status="designed",
            design={"isolation": "model"},
            success_criteria={"score": 1},
            command=["python"],
            cwd="/workspace",
        )
    with pytest.raises(ValueError, match="nonempty argv"):
        policy.command_input(
            experiment_id="experiment-1",
            experiment_type="command",
            status="designed",
            design={"isolation": "subprocess"},
            success_criteria={"accepted_exit_codes": [0]},
            command=[],
            cwd="/workspace",
        )
