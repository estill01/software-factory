# Bounded candidate lane

This is the operational contract for one `compare-candidate` decision. The
shared identity, evidence, currentness, role, and terminal rules remain defined
by `adaptive-decision-control.md`; this reference defines the executable lane
boundary without creating a second controller or ledger.

## Contents

- [Eligibility](#eligibility)
- [Exact lane record](#exact-lane-record)
- [Authority and disposition](#authority-and-disposition)
- [Recovery and Stop](#recovery-and-stop)

## Eligibility

All of the following are required before a lane exists:

- a source-backed Block 4 `compare-candidate` / `material-better-path` trigger;
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
Source semantics that already decide the result route to inline correction;
the retained compression exercise opens a lane only because the representative
artifact-size delta, runtime posture, and exact protected-capability result
require executing the bounded alternatives. The representative workload and
validation runtime are canonical rooted records, not unbound test inputs.

Eligibility is a transparent comparison, not a confidence score. The retained
record contains exact boolean findings for source-backed uncertainty,
implementation-evidence necessity, read-only resolvability, and isolation;
exact evidence roots for those findings and reversibility; and integer minutes
for avoidable rework, the candidate ceiling, review ceiling, and isolation
recovery. The lane may open only when all boolean gates pass and
`rework_avoided_minutes` is greater than the sum of those three bounded costs.
Reversibility is therefore an input to admission, not a fact added after work
starts.

Before candidate work begins, one committed pre-run contract freezes the
accepted tracker revision and blob root, candidate trigger, hypothesis and
scope, representative workload, exact validation runtime and executable root,
performance protocol, materiality thresholds and rationale, capability and
protected-capability contract, resource ceilings, cleanup posture, and Stop.
The lane-start and implementation-start observations must follow that exact
checkpoint and precede focused proof. Later source, results, or reviews may
resolve the frozen inputs but cannot tune them after observing the candidate.

The lane source freezes the accepted tracker revision and blob root, target and
incumbent revisions, canonical content manifests, capability contract,
hypothesis and affected scope, six-dimension order, role identities, writable
scope and exclusions, positive resource ceilings, Stop, and cleanup posture.
Every JSON integer is an integer rather than a boolean or string; every ID,
root, list, and object has a closed shape. Paths are normalized absolute paths,
contain no `.` or `..`, and, when they name real artifacts, are resolved under
the exact target or isolated owner before use. JSON parsing rejects duplicate
keys, floats, non-finite values, non-NFC strings, unknown keys, and noncanonical
array order before applying the bounded RFC 8785 projection.

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

Candidate identity is the SHA-256 root of its revision and sorted file manifest;
each file entry binds its canonical path and exact byte root. A focused result
binds the candidate root, command, time, exit, output, and protected result. A
mapped result additionally binds the incumbent, the already-frozen focused
result, its later timestamp, command, exit, output, and raw metrics. Mapped work
cannot begin or become current before a coherent focused pass.

Retained focused and mapped claims are checked by executing the bounded
candidate bytes with a restricted embedded runtime. Semantic output identity,
artifact size, a repeated alternating process-time comparison, protected API
posture, changed lines, decision points, exact compatibility obligations, and
named protected regressions are derived from those bytes; fixture strings
cannot override a different observable result. A candidate is materially
better only when it clears the frozen absolute and proportional artifact-size
thresholds, is not materially slower under the frozen runtime ceiling, adds no
maintenance/protected/compatibility regression, and stays within the explicit
changed-line and restoration-step ceilings.
The performance result retains the exact incumbent and candidate samples,
medians, ratio, interquartile spread, protocol root, workload root, runtime
root, candidate root, timestamp, and result root. The runtime identity binds
the resolved interpreter bytes, language and zlib versions, operating system,
release, and machine. An unstable sample spread is `inconclusive`; a posture
label without the retained measurements is never review evidence.
Validating an unchanged retained result recomputes its sample statistics and
content roots; it does not rerun the noisy timing producer merely for generic
confidence. A later benchmark is new adjudicating evidence and follows the
normal predecessor/currentness path.
File count, changed lines, executed commands, reviewer passes, and elapsed time
are likewise recomputed from retained files and the actual lane-start,
implementation-start, focused, mapped, and review chronology and bound into
resource/currentness evidence. A review outside its own time ceiling cannot
become current by asserting a smaller elapsed value. It is retained only as
late process evidence; the method creates a cause-bound Stop-review packet,
retires the candidate with a complete closed record, and emits no handoff.

The raw comparison is a six-record ordered array. Each record has exactly
`dimension`, `unit`, `incumbent_evidence_root`, `candidate_evidence_root`,
`incumbent_value`, `candidate_value`, and `relation`; relation is exactly
`candidate-better`, `incumbent-better`, `equivalent`, or `inconclusive` and is
derived from the retained raw values. The review input binds the target,
incumbent, candidate, focused, mapped, comparison, capability, and protected
roots while excluding case labels, expected actions, expected dispositions,
and implementer preference. A distinct reviewer owns a separately retained,
content-bound result containing the exact input root, reviewer identity,
timestamp, comparison disposition, Block 4 review disposition, retirement
posture, and result root; the method verifies that its disposition follows the
raw six dimensions before using it.

The immutable common stage order is `selected`, `implementing`, `validated`,
then `reviewed`. A `candidate-better` result stops this Block at
`cutover-eligible` with `retirement_posture=eligible-cutover`; it cannot be
`closed` until Block 9 actually cuts over or retires it. Every losing,
non-beneficial, or inconclusive result proceeds from `reviewed` to `closed`
with its exact retirement posture. Candidate and current target roots are
absent until their evidence exists, and later stages refresh currentness
without changing the adjudicating decision fingerprint. `focused_validation`
must pass before `mapped_validation` or review becomes eligible. Review evidence
binds the candidate root, reviewer identity, comparison conclusion, and raw
comparison root.

Every stage is the complete Block 4 record, not a lane-specific summary. The
record uses the Block 4 fingerprint and currentness projections, exact
evidence-manifest and stage-linked validation/review/outcome claims, and
`currentness_refresh_of` linkage. The fingerprint binds the accepted
tracker/Block source, target owner and revision, incumbent revision/content,
capability and expected effect, hypothesis/scope, comparison order,
eligibility, isolation, and Stop. Candidate, validation, review, outcome, and
retirement facts advance currentness without silently replacing that decision
identity.

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

The Block 9 handoff is one canonical, rooted, non-mutating record binding the
decision fingerprint/currentness, target/incumbent/candidate, review and raw
comparison, target owner, protected results, exact destination Block, and
cutover preconditions. It explicitly grants no cutover, publish, tracker, or
policy authority. Equivalent current fingerprint, candidate, and review roots
are compared to the independently accepted lane head before lane creation; an
exact match emits no new lane, review, or handoff. The accepted head must be
frozen outside the candidate source that consumes it, so a caller cannot label
its own duplicate or coordinate a source-and-head rewrite.

## Recovery and Stop

Stop the lane immediately on isolation drift, comparison-basis drift, ceiling
expiry, focused failure, protected-capability regression, cancellation, or
review currentness loss. Mapped failure and hypothesis falsification are also
terminal retirement results, distinct from an actual focused-before-mapped
order violation. Each post-creation Stop emits a complete closed Block 4
record with the exact failed/stale evidence, immutable currentness, cleanup and
retirement posture. Its externally owned review input binds cause-specific
evidence: exceeded derived resources, changed incumbent/isolation/review roots,
cancellation authority, failed focused/mapped roots, named protected
regressions, or the falsifying comparison. It emits no handoff or production
authority. Preserve the
incumbent and unrelated work. Reuse valid
candidate evidence after interruption only when the exact hypothesis, roots,
scope, ceiling, and current comparison basis remain unchanged; otherwise retire
it as stale. A merge conflict is candidate evidence, never permission to mutate
the incumbent or broaden scope.

The Block Stop is before cutover, tracker amendment, policy change, publication,
or external release. For a full-tracker request it is an internal audited
checkpoint and execution continues automatically.
