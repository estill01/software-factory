# RSI Core

`rsi-core` is a zero-dependency Python library for bounded recursive
self-improvement. It supplies pure policies for reflection, hypothesis testing,
experiment interpretation, program evolution, reviewed selection, and safe changes
to the selector itself, plus typed ports for host-owned effects.

## Install

From this repository:

```bash
python -m pip install ./rsi-core
```

## Example

```python
from rsi_core import CommandObservation, RSIKernel

rsi = RSIKernel()
hypothesis = rsi.hypotheses.propose(
    scope_id="my-system",
    statement="The new scheduler reduces queue latency",
    causal_model={"change": "fair scheduling"},
    prediction={"p95_latency_delta": "< 0"},
)
experiment = rsi.experiments.command_input(
    experiment_id="latency-comparison-1",
    experiment_type="command",
    status="designed",
    design={"kind": "isolated comparison"},
    success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["IMPROVED"]},
    command=["python", "compare_latency.py"],
    cwd="/workspace",
)

# A host-owned runner executes `experiment` and returns its observation.
evaluation = rsi.experiments.evaluate_command_result(
    exact_input_root=experiment.exact_input_root,
    success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["IMPROVED"]},
    observation=CommandObservation(exit_code=0, stdout="IMPROVED\n", stderr=""),
)
update = rsi.hypotheses.apply_evidence(
    current_confidence=hypothesis.confidence,
    evidence_type=evaluation.hypothesis_evidence_type,
    evidence_id=evaluation.evidence_root,
    weight=evaluation.hypothesis_evidence_weight,
)
```

The library performs no persistence or external effects. See
[`src/rsi_core/README.md`](src/rsi_core/README.md) for the module map and complete
integration boundary.
