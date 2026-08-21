# RSI Core

`rsi_core` is the reusable, host-agnostic decision kernel extracted from Software
Factory's recursive program evolution and selection-quality loop.

It owns the portable part of recursive self-improvement:

- exact-state checkpoint materiality;
- stable program-change and review identities;
- currentness and independent-review guards;
- sequential and parallel improvement portfolios;
- reviewed candidate selection and outcome confidence validation; and
- historical, forward-shadow, independent-review, activation, and rollback gates
  for changes to the selector itself.

It intentionally owns no database schema, filesystem mutation, Git operation,
subprocess, model/provider call, or product-specific ontology. A host records the
kernel's decisions in its existing authoritative store and executes effects through
its own governed adapters. This lets another system reuse the improvement loop
without creating a second ledger or importing Software Factory.

```python
from rsi_core import RSIKernel

kernel = RSIKernel()
decision = kernel.checkpoint(
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
validation, commits, and other effects.
