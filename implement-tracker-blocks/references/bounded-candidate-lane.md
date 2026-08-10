# Bounded candidate lane

This is the operational contract for one `compare-candidate` decision. The
shared identity, evidence, currentness, role, and terminal rules remain defined
by `adaptive-decision-control.md`; this reference defines the executable lane
boundary without creating a second controller or ledger.

## Eligibility

All of the following are required before a lane exists:

- a source-backed material-better-path trigger;
- a named outcome uncertainty that read-only evidence cannot resolve;
- implementation behavior identified as the missing evidence;
- a checkpointed coherent incumbent and exact comparison basis;
- safe isolation with no overlapping production or canonical-state write;
- explicit capability and protected-capability expectations;
- positive expected decision value with each benefit and cost named;
- one normal implementation owner and one distinct automated reviewer; and
- bounded files/changes, commands, elapsed time, review work, and early Stops.

Failure of any condition returns to the incumbent without creating a lane.
Repeated equivalent decision, candidate, or review roots are a no-op.

## Exact lane record

The candidate addition to the Block 4 record contains exactly:

```text
hypothesis, hypothesis_scope, incumbent_root, candidate_root,
isolation_kind, isolated_writable_scope, shared_resource_exclusions,
resource_ceiling, time_ceiling, stop_condition,
production_authority_owner_id, focused_validation, mapped_validation,
validation_order, comparison_dimensions, independent_reviewer_id,
review_root, review_disposition, cutover_owner_id, cutover_preconditions,
retirement_posture
```

`resource_ceiling` fixes maximum files, changed lines, commands, and reviewer
passes. `time_ceiling` is an elapsed-minute bound, not a scheduling estimate.
The six comparison dimensions are exactly `observable-outcome`,
`implementation-cost`, `maintenance-cost`, `reversibility`, `compatibility`,
and `protected-capability`. Each names incumbent evidence, candidate evidence,
and a factual relation; there is no weighted score.

The lane evidence envelope separately records `comparison_disposition` as one
of the four comparison outcomes below and binds it into `review_root` with the
raw six-dimension comparison. The closed Block 4 candidate object retains its
defined `review_disposition`: `accepted` means the independent review accepted
the evidence-bound comparison conclusion. A comparison outcome must never be
inserted into that distinct enum field or smuggled into narrative. The
disposition-to-retirement mapping below is derived by the method, not copied
from an implementer-supplied expected result.

The immutable stage order is `selected`, `implementing`, `validated`,
`reviewed`, then `closed`. Candidate and current target roots are absent until
their evidence exists, and later stages refresh currentness without changing
the adjudicating decision fingerprint. `focused_validation` must pass before
`mapped_validation` or review becomes eligible. Review evidence binds the
candidate root, reviewer identity, disposition, and raw comparison root.

## Authority and disposition

The incumbent is the only production authority throughout this Block. The
candidate implementation owner cannot be its reviewer. The reviewer sees
roots, raw observable outcomes, costs, compatibility, reversibility, and
protected-capability evidence before seeing any implementer preference.

The reviewer returns one exact disposition:

- `candidate-better`: `retirement_posture=eligible-cutover`; emit one frozen
  Block 9 handoff and keep the candidate isolated;
- `incumbent-better`: `retirement_posture=retired-loser`;
- `non-inferior-no-benefit`: `retirement_posture=retired-loser`; or
- `inconclusive`: `retirement_posture=retired-inconclusive`.

Only Block 9 and the normal target owner may cut over an accepted winner. A
losing or inconclusive lane cannot remain active, become an alternate
production owner, or be retained as a second implementation. Useful evidence
may remain immutable and explicitly non-authoritative.

## Recovery and Stop

Stop the lane immediately on isolation drift, comparison-basis drift, ceiling
expiry, focused failure, protected-capability regression, cancellation, or
review currentness loss. Preserve the incumbent and unrelated work. Reuse valid
candidate evidence after interruption only when the exact hypothesis, roots,
scope, ceiling, and current comparison basis remain unchanged; otherwise retire
it as stale. A merge conflict is candidate evidence, never permission to mutate
the incumbent or broaden scope.

The Block Stop is before cutover, tracker amendment, policy change, publication,
or external release. For a full-tracker request it is an internal audited
checkpoint and execution continues automatically.
