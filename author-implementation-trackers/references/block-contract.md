# Block contract

Use this contract to turn a goal into implementation blocks. The contract is a
planning aid, not a reason to add empty prose or speculative machinery.

## Split on real boundaries

Create a separate block when one of these changes materially:

- authoritative owner or writer;
- dependency or prerequisite;
- mutation boundary;
- independently auditable outcome;
- acceptance or review gate;
- recoverability or rollout posture;
- explicit stop point needed to prevent premature downstream work.

Do not split merely to keep blocks similar in size. Do not combine independent
capabilities merely to reduce the count. Use whole-number identifiers and let
the count follow the design.

## Required core sections

Every block needs:

1. `Status` — one declared tracker status.
2. `Objective` — one outcome, stated without implementation-detail clutter.
3. `Inputs and dependencies` — earlier Blocks and exact external prerequisites.
4. `Required work` — owned implementation changes and explicit reuse.
5. `Scope and non-goals` — the exact bounded area plus adjacent work expressly
   excluded from this block.
6. `Deliverables and recorded state` — concrete code, schemas, records,
   artifacts, or read models produced.
7. `Acceptance` — observable conditions that establish the objective.
8. `Negative tests` — representative failures that must be rejected or remain
   explicitly open.
9. `Completion evidence` — exact commits, inputs, outputs, tests, review, and
   limitations; use `Pending.` before execution.
10. `Stop` — the first downstream action this block must not perform.

Use `Resource and economy contract` when provider calls, large corpora,
rendering, broad scans, long tests, or repeated work require explicit bounds.
When present, state the normal affected-scope path, exact reusable artifacts,
batching, cheap-currentness check before deep work, justified widening triggers,
validation/review order, and measurable stop. Runtime alone is not a relevance
test, and a ceiling is not permission for unnecessary breadth.
Use `QA and independent review` when substantive judgment, consequential
mutation, candidate selection, or repository policy requires a different
reviewer. These sections are optional only when genuinely inapplicable.

## Writing rules

- State what becomes true, not merely what files will be touched.
- Name existing owners before proposing new ones.
- Separate required work from acceptance evidence.
- Make negative tests correspond to supported paths and material failure modes.
- Define currentness, replay, migration, compatibility, and rollback only where
  the block crosses those boundaries.
- Preserve open, deferred, rejected, and reserved outcomes without calling them
  accepted.
- Keep legal, release, security, privacy, multi-user, provider, and runtime
  concerns out unless the block actually crosses an existing such boundary.
- Do not turn a non-goal or inherited safeguard into a new workstream.
- Record resource ceilings using transparent counts or formulas when scale
  could otherwise become unbounded.
- Prefer one shared context/index/snapshot and bounded local deltas over repeated
  whole-scope or per-item work. Require deep recapture only after a cheap exact
  currentness check proves the accepted artifact changed.
- Put likely-mutating review before expensive final validation when possible;
  bind acceptance proof to the frozen candidate and mark pre-correction runs
  diagnostic.
- Make the stop sentence concrete: `Stop before ...`.

## Single-focus test

A Block is properly scoped when its required work is the smallest coherent set
needed to establish one primary outcome through one narrow owner boundary.
Necessary helper changes may remain with that outcome. Split the Block when a
second capability:

- has a different authoritative owner or writer;
- could be accepted, reverted, or reviewed independently;
- has a different dependency or stop condition;
- introduces a separate user-facing or operational outcome;
- needs its own resource ceiling, migration, rollout, or substantive review.

Do not split a tiny helper that has no independent outcome. Do not keep an
independent capability in a Block merely because the same source inspired it.

## Feature-creep gate

For every proposed field, schema, service, registry, ledger, writer, cache,
runtime, workflow, API, CLI surface, generalized helper, test family, or review
gate, require all three:

1. the Block objective cannot reasonably be met without it;
2. no existing owner can represent the needed fact or operation;
3. its expected outcome benefit exceeds implementation, maintenance, review,
   migration, and staleness cost.

If any condition is absent, reuse the existing owner, make the direct
correction, preserve an explicit open item, or omit the mechanism. In
particular:

- inspected source is a translation candidate, not mandatory adoption;
- a non-goal or prohibition constrains work but does not authorize a new audit
  program, schema field, fixture family, or enforcement subsystem;
- an existing owner may be reused without modifying it;
- optional hardening needs one reproduced supported failure tied to the Block;
- adversarial wording does not create a generalized security threat model;
- do not add multi-user, ACL/RBAC, privacy, security, scheduler, runtime,
  telemetry, dashboard, graph, cache, scoring, or remote-access machinery when
  the Block does not cross that boundary;
- negative tests must exercise supported paths and concrete integrity failures,
  not hypothetical product modes;
- once the concrete invariant passes focused regression and required review,
  stop remediation instead of searching for broader hypothetical hardening.

## Dependency discipline

- Every dependency must exist and precede its consumer.
- Prefer the narrowest direct dependency; do not list every transitive ancestor.
- A block may inspect future concerns but cannot perform their mutation or claim
  their acceptance.
- If a later requirement materially changes an accepted earlier invariant,
  append a bounded remediation block or preserved remediation delta rather than
  rewriting historical evidence.

## Tracker-level sections

Use only those that improve execution:

- Purpose and intended outcome
- Target architecture and authority boundaries
- Existing owners to reuse
- Prior-work/source-adaptation map
- Scope, non-goals, and proportionality
- Block execution contract
- Completion-evidence template
- Status and required order
- Blocks
- Verification matrix
- Final completion definition

A small tracker may omit maps and matrices that add no information.
