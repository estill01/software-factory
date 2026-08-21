# RSI Core

`rsi_core` is the reusable, host-agnostic policy library extracted from Software
Factory's recursive program evolution, hypothesis-testing, and selection-quality
loops.

It owns the portable part of recursive self-improvement:

- exact-state checkpoint materiality;
- stable program-change and review identities;
- currentness and independent-review guards;
- sequential and parallel improvement portfolios;
- reviewed candidate selection and outcome confidence validation; and
- historical, forward-shadow, independent-review, activation, and rollback gates
  for changes to the selector itself;
- evidence-bound reflection and falsifiable hypothesis identities;
- configurable support, counterexample, boundary, confounder, and null-evidence
  updates; and
- experiment design validation, exact input roots, deterministic success-criteria
  interpretation, and hypothesis evidence classification.

## Package structure

- `checkpoints.py` — material-change detection;
- `programs.py` — program-change identities and effect gates;
- `portfolios.py` — sequential/parallel lane transitions;
- `reviews.py` — independent-actor rules;
- `selections.py` — candidate selection and outcome confidence;
- `selector_policies.py` — evaluation and rollback of selector self-changes;
- `hypotheses.py` — reflection identities and hypothesis evidence updates;
- `experiments.py` — pure experiment input and result interpretation;
- `ports.py` — typed host interfaces such as `ExperimentRunner`;
- `identity.py`, `models.py`, and `errors.py` — shared primitives; and
- `kernel.py` — a small composition root, not a second implementation.

It intentionally owns no database schema, filesystem mutation, Git operation,
subprocess, model/provider call, or product-specific ontology. A host records policy
decisions in its existing authoritative store and executes experiments and effects
through governed adapters. Invalid experiment execution is classified as null
evidence; infrastructure failure is never treated as falsification.

```python
from rsi_core import RSIKernel

kernel = RSIKernel()
decision = kernel.checkpoints.evaluate(
    state={"quality": 0.82, "revision": "candidate-7"},
    evidence_ids=["eval-19"],
    previous_fingerprint=None,
)

if decision.material:
    # Persist the decision and schedule host-specific evaluation work.
    record_checkpoint(decision)
```

Software Factory's `EvolutionService` is the reference adapter. It persists RSI
records in the existing factory database and retains ownership of tracker changes,
validation, commits, and other effects. `LearningService` is the reference hypothesis
and experiment adapter: it persists hypotheses and invokes commands, while `rsi_core`
interprets their epistemic result. Its default command port is
`software_factory.experiment_runner.SubprocessExperimentRunner`; other hosts can
inject a container, remote-job, simulator, or shadow-traffic runner.
