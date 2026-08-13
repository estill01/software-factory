# Software Factory Selection-Quality RSI and Supervision Implementation Tracker

- Tracker status: `planning`
- Tracker sequence: Blocks 0–6
- Repository: `/Users/ethanstillman/code/software_factory`
- Planning source revision: `f7bf6b88aff8ec2edcb78e968691f4a5248fec1a`
- Governing objective: Direct-user requirement that Software Factory not only
  select features, implementations, refactors, and programs, but independently
  catch poor feature/design choices before authoring and continually improve the
  quality of its selector from the realized results of existing features and
  implementation trackers being planned, implemented, completed, rejected,
  retired, or superseded.

## 1. Purpose and intended outcome

Make feature/program selection a supervised and recursively improving product
capability rather than a one-time ranking step. The current-cycle selector must
produce an inspectable choice that an independent supervisor can accept, revise,
reject, or defer before tracker authoring. Later, independently observed product,
implementation, supervision, and resource outcomes must determine whether that
selection was effective and whether the selector policy should change. A revised
selector policy must earn acceptance against retained historical cases and a
subsequent or shadow cycle before it becomes current.

Completion means:

- every consequential feature, design, or program selection is bound to the
  exact product and tracker inventory, candidate set, rejected alternatives,
  expected effects, uncertainty, resource posture, and direct mission that
  produced it;
- the existing supervision owner independently challenges the selection before
  any tracker-authoring or implementation handoff and prevents unsupported or
  stale choices from becoming canonical work;
- current requested implementation continues while prospective selection review,
  correction, or learning remains open, except where exact evidence proves a
  prerequisite or protected-capability defect in the current program;
- later observable outcomes are linked to the exact selection and evaluated on
  separate product, capability, rework, incident, rollback, correction, resource,
  coordination, and missed-opportunity dimensions rather than an opaque score;
- evidence-supported selector-policy changes are versioned, independently
  reviewed, compared with the incumbent on retained cases and a forward cycle,
  and adopted only through existing owners;
- one frozen two-cycle dogfood run demonstrates a poor feature/design choice
  rejected before authoring, a sound choice implemented without derailing current
  work, an outcome-driven selector-policy improvement, and an unchanged no-op;
  and
- the accepted four-skill release and compatible running supervisors use the
  resulting selection-supervision and selector-learning capability at safe
  boundaries, with normal release-owner rollback available.

### Mission frame

- Primary outcome: Software Factory continually gets better at choosing what to
  work on, while independent supervision catches bad current selections before
  they become implementation programs.
- Observable completion: exact current evidence shows the chain `existing product
  and tracker inventory -> candidate set -> selection and forecasts -> independent
  review -> authoring and implementation -> observable outcome -> selection-
  effectiveness evaluation -> selector-policy revision -> old/new comparison ->
  next cycle`, including one rejected poor choice and one accepted improvement.
- Ordinary effect classes needed: source and contract implementation, derived
  artifact generation, canonical supervision policy/event extension, tracker-
  authoring handoff integration, isolated dogfood, exact review, Git checkpoint
  and push, flagless release-owner promotion, safe supervisor refresh, and
  rollback verification.
- Hard direct authority or safety boundaries: direct-user product intent remains
  governing; selection and its review are nonauthorizing; tracker structure is
  written only by `author-implementation-trackers`; target source is written only
  by its implementation owner; supervision policy/events are written only by
  `supervise-tracker-runs`; release activation is performed only by
  `scripts/skill_release.py`; credentials, spend, destructive effects, external
  communication, deployment, and material goal changes retain their separate
  owners.
- Material goal alteration or reversal: replacing direct-user intent, deleting an
  expressly requested capability, converting estimates into spend authority,
  authorizing external or destructive action, allowing a selector or supervisor
  to adopt its own choice, or using prospective work to cancel an active requested
  range requires renewed exact direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this changes Software Factory's operating model from
  evidence-grounded feature/program selection with later generic feedback to a
  supervised, outcome-calibrated selector whose own policy can improve.
- Direct product sources: direct-user source records
  `direct-user-019ff991-feature-selector-supervision` and
  `direct-user-019ff991-selection-quality-union`; the active recursive product-
  program tracker at planning source `f7bf6b88aff8ec2edcb78e968691f4a5248fec1a`;
  `evolve-product-program/references/product-program-evolution-contract.md` at
  that source; and the current `supervise-tracker-runs` role, effectiveness,
  adaptive-decision, and Factory-evolution contracts.
- Product thesis and intended effect: recursive improvement is incomplete if the
  system merely generates more work. It must choose proportionate, valuable work,
  reject weak or harmful choices before they consume authoring/implementation
  capacity, and learn which selection methods produce useful product outcomes.
- Protected capabilities: first-loop user cold start; direct semantic scope;
  exact current requested ranges; accepted and rejected history; current-run
  correction priority; one writer per authority boundary; generator/selector/
  reviewer/evaluator separation; transparent evidence dimensions; cheap no-op
  convergence; safe continuation; terminal reporting; release rollback; and the
  ability to conclude that no further work is justified.
- Architecture strategy: extend `evolve-product-program` with selection-decision,
  effectiveness, and selector-policy artifacts; reuse the canonical supervision
  policy/event ledger and Terra/XHigh/Max topology for an explicit selection
  profile; reuse existing tracker authoring, implementation, outcome, reporting,
  and release owners. Add no second selector ledger, tracker writer, supervision
  system, scheduler service, telemetry database, release pointer, or opaque agent.
- Requested capability: the union of feature/program selection, independent
  online supervision of consequential selection/design, and cross-cycle RSI on
  selector quality.
- Proportionality: the online gate and cross-cycle learning are separate because
  they have different evidence, timing, owners, and acceptance. They share the
  same existing supervision and evolution infrastructure so the separation does
  not create parallel machinery.
- Tradeoffs: deeper review and learning can improve product value and resource
  allocation, but can also delay useful work, overfit historical cases, reward
  monitor-visible proxies, or create recursive self-approval. Cheap currentness
  gates, bounded review, vector evidence, held-out comparison, and distinct roles
  control those costs.
- Uncertainty: counterfactual outcomes are often unavailable, projected token/cost
  data may not be provider-reported, and a small number of cycles cannot establish
  broad causal superiority. Missing evidence remains `unavailable` or
  `inconclusive`; it is never manufactured to force a policy revision.

## 2. Target architecture and authority boundaries

```text
current product behavior + feature inventory + tracker inventory + direct mission
                                  |
                                  v
                     evolve-product-program generator
                                  |
                     candidate set + counterexamples
                                  |
                                  v
                     independent portfolio selector
                                  |
              selection + rejected alternatives + forecasts
                                  |
                                  v
          supervise-tracker-runs product-program-selection profile
            Terra currentness -> Sol XHigh semantic -> Sol Max if needed
                                  |
                  accepted | revise | rejected | deferred
                                  |
                     accepted only v
                  author-implementation-trackers
                                  |
                     implement-tracker-blocks
                                  |
              observable product/program/resource outcome
                                  |
                                  v
                 independent selection evaluator
                                  |
       effective | mixed | ineffective | inconclusive + supported misses
                                  |
                                  v
              bounded selector-policy revision candidate
                                  |
          retained historical comparison + forward shadow cycle
                                  |
                         accepted or rejected
                                  |
                          next selection cycle
```

Authority rules:

1. `evolve-product-program` owns derived candidate, selection, selection-
   effectiveness, selector-policy proposal, and comparison artifacts. None is a
   canonical tracker/source/release effect.
2. The selection generator and selector remain distinct. The selector does not
   evaluate its own realized outcome or accept its own policy revision.
3. `supervise-tracker-runs` owns the canonical online selection-review profile,
   currentness gate, semantic review events, findings, adjudication, and later
   effectiveness observations. It cannot generate/select features or write the
   tracker/source it reviews.
4. Terra performs only mechanical change/currentness routing. Sol XHigh reads the
   exact bounded selection delta and source inventory. Sol Max adjudicates only a
   supported consequential uncertainty or tradeoff.
5. `author-implementation-trackers` remains the sole tracker writer. An accepted
   selection review is a required input, not tracker bytes or range authority.
6. `implement-tracker-blocks` continues every exact current requested range and
   consumes only an author-owned, range-bound program. Prospective selection never
   becomes an early-return, cancellation, or manual-Resume condition.
7. Outcome evidence remains in existing target, supervision, report, and terminal-
   reconciliation owners. The selection evaluator retains exact roots and typed
   conclusions rather than copying transcripts, repositories, or hidden reasoning.
8. Selector-policy changes use the existing source owner, Git, independent review,
   release owner, and safe monitor-refresh path. Neither a favorable evaluation nor
   a better comparison root activates code.
9. Historical selector decisions, reviews, findings, outcomes, and rejected policy
   candidates remain append-only. New schemas emit only the current form; no legacy
   aliases, dual readers, or compatibility shims are added for unimplemented
   selector-quality artifacts.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Evidence packet, reflection, candidate set, resource projection, portfolio selection, placement | `evolve-product-program` and `product-program-evolution-contract.md` | extend without a second decision store |
| Product and protected-capability reasoning | tracker capability frames plus `implement-tracker-blocks/references/product-capability-review.md` | reuse |
| Current implementation range and structural amendments | implementation-range and active-program revision owners | reuse unchanged |
| Tracker structure and implementation readiness | `author-implementation-trackers` | reuse as sole tracker writer |
| Online watcher/reviewer/adjudicator topology | `supervise-tracker-runs` canonical policy, event ledger, route gate, incidents, and lifecycle | adapt with a selection profile |
| Supervisor effectiveness and false-negative sampling | four-hour effectiveness review and weekly cognitive review | reuse for the selection supervisor's own quality |
| Product outcome and current behavior | observable-outcome completion and terminal capability reconciliation | reuse as adjudicating evidence |
| Implementation/resource evidence | supervision events, implementation evidence, candidate use, reports, and execution-economy projections | adapt with exact evidence classes |
| Recursive Factory maintenance | Factory Evolution admission, review, evaluation, outcome, and correction lineage | reuse only for reusable Software Factory policy/source changes |
| Release, installed roots, refresh, and rollback | flagless `scripts/skill_release.py promote` and accepted automatic monitor-refresh owner | reuse; supervisors never write the pointer |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Recursive Product-Program Evolution tracker | `f7bf6b88aff8ec2edcb78e968691f4a5248fec1a` | adapt | 0–6 | make the complete selector-supervision and selector-quality loop explicit |
| Product-program evolution contract and role separation | `f7bf6b88aff8ec2edcb78e968691f4a5248fec1a:evolve-product-program/references/product-program-evolution-contract.md` | extend | 0, 3, 4 | add review/effectiveness/policy identities without weakening nonauthorization |
| Existing Block 3 typed outcome/resource priors | recursive tracker at `f7bf6b88…`, Block 3 | reuse | 0, 3 | bind them to exact selections and later outcomes |
| Existing Block 4 independent portfolio selection | recursive tracker at `f7bf6b88…`, Block 4 | reuse | 0–2 | preserve forecasts and require online review before authoring |
| Existing Block 7 supervision/effectiveness plan | recursive tracker at `f7bf6b88…`, Block 7 | refactor | 1, 3 | separate online selection review from authoring review and cross-cycle learning |
| Existing Blocks 10–11 dogfood and final proof | recursive tracker at `f7bf6b88…`, Blocks 10–11 | extend | 5, 6 | prove two-cycle learning and installed monitor use |
| Consequential tracker-authoring profile | accepted plan mapped in recursive tracker revision `5a0e8347…` | reuse | 2, 5 | keep post-selection tracker-quality review distinct |
| Supervision changed-state and effectiveness machinery | installed three-role/four-role supervision contract at release `75481f37c3b6-e3e2f2705136` | adapt | 1, 3, 5 | bind selection-specific inputs, dispositions, and outcomes |
| Factory Evolution RSI/evaluator separation | accepted Factory-evolution contracts through planning source `f7bf6b88…` | reuse | 3, 4 | evaluate and improve the selector without self-approval |

### Preferred integration map into the active recursive tracker

This tracker is a source plan for the active implementation thread. The active
tracker author applies the final program revision through its existing authoring
and supervision owner. The preferred map preserves active Blocks 0–4 byte-for-byte
and inserts only future work:

| Existing recursive tracker Block | Revised Block | Treatment |
|---:|---:|---|
| 0–4 | 0–4 | preserve exact status, contracts, and accepted/in-flight evidence |
| new | 5 | insert online feature/program selection supervision; consume Block 4 and stop before tracker authoring |
| 5 | 6 | retain tracker-evolution owner; add exact accepted selection-review input |
| 6 | 7 | retain implementation invocation and non-derailment |
| 7 | 8 | retain supervision triggers and tracker-authoring profile; remove any ambiguity with the distinct selection profile |
| 8 | 9 | retain portfolio orchestration |
| 9 | 10 | retain four-skill release-owner changes |
| 10 | 11 | extend dogfood with current-choice review and frozen selection forecasts/outcomes |
| new | 12 | insert selection-effectiveness and supported-counterfactual evaluation |
| new | 13 | insert selector-policy revision plus incumbent/candidate comparison and forward shadow cycle |
| 11 | 14 | retain final exact review, release, safe refresh, rollback, and terminal proof |

If the active author proves a smaller map satisfies the same independent outcomes,
it may merge necessary plumbing into an adjacent future Block. It must not merge
online selection supervision with selector-policy learning, or selection evaluation
with policy adoption, because those have different evidence, timing, writers,
reviewers, and Stops. The exact old-to-new map, source map, verification matrix,
terminal count, and prose references must change atomically.

## 5. Scope, non-goals, and proportionality

### In scope

- Consequential feature, design, refactor, remediation, architecture, and program-
  portfolio selections produced by `evolve-product-program` or a compatible
  user-seeded selection/authoring flow.
- Current product behavior and feature inventory plus planned, active, completed,
  rejected, retired, and superseded tracker state as selection context.
- Online independent selection/design review before authoring or application.
- Exact selection forecasts, rejected/deferred alternatives, realized outcomes,
  supported counterfactuals, missed opportunities, and typed resource evidence.
- Versioned selector-policy proposal, retained comparison, independent review,
  forward shadow/current cycle, and bounded adoption through existing owners.
- Integration into existing authoring, implementation, supervision, reporting,
  release, refresh, and rollback paths.

### Out of scope

- A generic product-management platform, public roadmap UI, prioritization SaaS,
  autonomous spend allocator, continuous cognition loop, new scheduler, new
  telemetry database, second supervision ledger, second tracker writer, or second
  release pointer.
- Fabricated counterfactual results, inferred user preference, automatic material
  goal change, external deployment, Gmail about ordinary candidates, credentials,
  destructive actions, or replacing direct-user product intent.
- A single opaque utility, quality, reward, or confidence score that hides
  product, evidence, resource, risk, uncertainty, and protected-capability
  dimensions.
- Mandatory deep selection supervision for routine, explicit, low-consequence
  user instructions whose product choice is already fixed; currentness and owner
  checks still apply.
- Compatibility readers or aliases for pre-capability selector-quality artifacts;
  immutable historical evidence remains readable only through its established
  owner and is never rewritten.

### Proportionality

Reuse one selection packet, one canonical supervision review, one outcome-linked
evaluation, and at most one selector-policy candidate/comparison per eligible
cycle. A weak or unsupported episode produces a no-op or inconclusive result, not
new machinery. Expand evidence only after a cheap identity/currentness check proves
that an acceptance-critical source changed.

## 6. Block execution contract

1. Execute Blocks 0–6 in dependency order.
2. Re-read the selected Block and inspect the live repository before editing.
3. Change both the status table and Block status to `in-progress` when the first
   implementation-producing edit, artifact, validation, or review handoff begins.
4. Preserve unrelated work, current requested ranges, accepted/rejected history,
   and the active recursive tracker implementation.
5. Apply this source tracker to the active recursive tracker only through
   `author-implementation-trackers` and its canonical program-revision review/
   application path. A routed instruction or this planning artifact is not
   authority to edit the active tracker from another writer.
6. Keep online selection supervision, post-outcome evaluation, selector-policy
   revision, and release/refresh as distinct acceptance boundaries.
7. Reuse existing schemas, policy/event ledger, outcome owners, release owner,
   and role topology. Add a field or event kind only when an exact required fact
   has no current representation.
8. Run focused proof before mapped proof. Complete likely-mutating independent
   review, freeze the candidate revision, then run each broad suite once.
9. Reuse exact current source snapshots and retained producer output. Unchanged
   checkpoints, reviews, outcomes, and comparisons perform no model or producer
   call.
10. Keep evidence dimensions separate. Label values `observed`, `provider-
    reported`, `estimated`, `inferred`, or `unavailable`; never promote an
    estimate or inference into an observed result.
11. Keep findings open until a later exact selection, tracker, source, or policy
    delta proves correction. A steer, favorable prose, self-hash, or green
    structural verifier is insufficient.
12. Audit and accept one Block before advancing. A Block Stop is an internal
    owner/review boundary, not permission to abandon an authorized full range.
13. Continue unaffected current implementation while prospective selection or
    selector learning is revised, rejected, deferred, or inconclusive.
14. Freeze and push cohesive validated checkpoints non-force. Rejected candidates
    remain immutable; corrections use successor commits and rerun only affected
    proof before exact review.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<selection, review, outcome, policy, or not-applicable root>`
- Inputs: `<paths, record IDs, versions, roots>`
- Outputs: `<paths, artifact/event/review roots>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<bounds, actual use, widening or not-applicable>`
- Independent review: `<review identity, exact disposition, findings, recheck>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<current range, safe frontier, handoff, resumed evidence>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze selection-review and selector-learning contracts | — | `not-started` |
| 1 | Gate consequential feature/design selection through existing supervision | 0 | `not-started` |
| 2 | Integrate accepted selections with tracker authoring and current-work preservation | 1 | `not-started` |
| 3 | Evaluate selection effectiveness and supported counterfactuals | 2 | `not-started` |
| 4 | Revise and compare selector policy without self-evaluation | 3 | `not-started` |
| 5 | Dogfood current-choice supervision and cross-cycle improvement | 4 | `not-started` |
| 6 | Freeze, review, release, refresh, and prove effectiveness | 5 | `not-started` |

Required order:

`0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6`

## Block 0 — Freeze selection-review and selector-learning contracts

Status: `not-started`

### Objective

Define one exact, replayable contract that binds a feature/program selection to
its source inventory, forecasts, independent review, realized outcomes, and any
later selector-policy revision without creating a new canonical ledger.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: every selection and later learning claim has one
  exact causal identity that independent owners can rehydrate.
- Potential capability loss or regression: excessive schemas could duplicate
  existing artifacts or convert uncertain outcomes into false causal claims.
- Protected-capability effect: preserves nonauthorization, role separation,
  currentness, typed evidence, append-only history, and no-op replay.
- Architecture and operating-model effect: extends the existing product-program
  artifact set and canonical supervision event vocabulary; adds no writer.
- Tradeoff and source evidence: explicit lineage costs more bytes and validation
  than prose, but is necessary to distinguish improving the selector from merely
  observing implementation activity.

### Inputs and dependencies

- The direct-user union requirement and exact planning source `f7bf6b88…`.
- Existing product-program evidence, reflection, resource, selection, portfolio,
  and placement artifacts.
- Existing supervision policy/events and observable-outcome reconciliation.

### Required work

- Define exact current-schema artifacts or projections for:
  `selection-review-packet`, `selection-review-result`, `selection-effectiveness`,
  `selector-policy`, `selector-policy-candidate`, and `selector-comparison`.
- Make the review packet bind the direct mission, target/product profile, current
  feature and behavior inventory root, repository revision/tree, tracker inventory
  root with planned/active/completed/rejected/retired/superseded states, candidate-
  set root, selected portfolio, rejected/deferred alternatives, product and
  protected-capability forecasts, resource forecasts, uncertainty, dependencies,
  Stops, current requested range, and selector/generator identities.
- Make outcome lineage bind exact authored tracker/program roots, implementation
  revisions, observable-outcome completion, selection review, and current policy/
  event heads. Distinguish a missing outcome from a negative result.
- Define finite selection-review dispositions `accepted`, `revise`, `rejected`,
  and `safe-deferred`; finite effectiveness dispositions `effective`, `mixed`,
  `ineffective`, and `inconclusive`; and exact allowed next actions.
- Define vector evidence dimensions and evidence classes. Prohibit a hidden
  aggregate score and retain uncertainty/contrary evidence explicitly.
- Define immutable-or-identical writing, exact roots, byte ceilings, stable reads,
  correction/supersession lineage, currentness, duplicate replay, and deletion of
  derived artifacts without loss of canonical evidence.
- Update the source map and sibling-owner interface contracts. Preserve existing
  API/schema names that remain current; emit no legacy selector-quality aliases.

### Scope and non-goals

- In scope: exact derived artifacts, canonical event shapes, roots, transitions,
  dispositions, and owner interfaces required by later Blocks.
- Not in scope: cognitive review, tracker/source mutation, policy improvement,
  dogfood, release, or a generic metrics framework.
- New fields must bind acceptance-critical facts unavailable from current owners.

### Deliverables and recorded state

- Versioned contract/reference, deterministic schemas/fixtures, source map,
  validators/builders, and contract tests.

### Resource and economy contract

One bounded inventory/selection packet per exact candidate-set root. Store roots
and typed facts rather than copied source. Reuse unchanged sibling artifacts and
return a deterministic no-op for identical fingerprint/currentness.

### QA and independent review

Mechanical exact-schema/root/currentness tests plus independent semantic review
of causal sufficiency, underreach, opaque-score avoidance, duplicate ownership,
and unsupported product doctrine.

### Acceptance

- An independent reader can trace an exact selection through review, authoring,
  implementation outcome, effectiveness, policy candidate, comparison, and next
  cycle while each artifact remains nonauthorizing and currentness-bound.

### Negative tests

- Reject missing candidate alternatives, unbound tracker inventory, selector/
  reviewer/evaluator role collapse, arbitrary dispositions, extra keys, stale
  source roots, self-root-only evidence, estimated-as-observed values, opaque
  scores, and policy candidates without exact predecessor lineage.

### Completion evidence

Pending.

### Stop

Stop before binding a live supervision profile or performing semantic selection
review.

---

## Block 1 — Gate consequential feature/design selection through existing supervision

Status: `not-started`

### Objective

Use the existing supervision owner and role topology to independently accept,
revise, reject, or safely defer each consequential feature/design/program choice
before tracker authoring.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: poor feature selection and design decisions are
  detected in the current cycle before they consume canonical authoring or
  implementation capacity.
- Potential capability loss or regression: an overactive supervisor could become
  a second selector, impose optional preferences, or starve supported work.
- Protected-capability effect: preserves direct intent, selector independence,
  current-range continuation, target-owned correction, and quiet no-op economy.
- Architecture and operating-model effect: adds a `product-program-selection`
  profile/phase to canonical supervision policy/status/events using existing role
  and lifecycle owners.
- Tradeoff and source evidence: mandatory independent review is warranted for
  consequential choices; routine explicit user choices keep the cheaper path.

### Inputs and dependencies

- Block 0 contracts and one exact selection-review packet.
- Existing `supervise-tracker-runs` mission, policy, event, role, routing,
  incident, decision, and effectiveness owners.

### Required work

- Add an explicit fail-closed `product-program-selection` target profile or
  equivalent policy-bound phase to canonical supervision. Bind exact selection
  target thread, source revision/root, candidate-set root, selection/portfolio
  root, reviewer roles, currentness, and resource ceiling.
- Make it automatically consumable by `evolve-product-program` after selection
  freeze and directly bootable for consequential user-seeded feature/program
  selection without requiring an RSI-generated candidate.
- Preserve Terra as mechanical/currentness-only. Route each materially changed
  exact selection delta to an independent Sol XHigh reviewer; use Sol Max only
  for a supported consequential unresolved tradeoff or deterministic sample.
- Require review against direct mission, current product behavior and feature
  inventory, every relevant tracker state, candidate omissions, rejected
  alternatives, expected effects, protected capabilities, architecture/owner
  mapping, dependencies, resource/coordination cost, Stops, and current-work
  preservation.
- Detect duplicate existing capability, conflict/duplication with current or
  planned work, omitted required work, weak/unnecessary features, underreach,
  unsupported overreach, poor architecture, novelty bias, false parallelism,
  current-work starvation, protected regression, and mission drift.
- Record exact finite review disposition, findings, supported alternatives,
  evidence/currentness roots, and next action in the existing event ledger.
  Findings remain open until a later exact selection delta proves correction.
- Make unchanged/unsupported cycles cheap no-ops. Do not run continuous cognition
  or turn one supervisor preference into product evidence.

### Scope and non-goals

- In scope: online pre-authoring selection currentness, semantic review,
  adjudication, correction lineage, events, status, and lifecycle.
- Not in scope: generating/selecting features, editing trackers/source, evaluating
  realized outcomes, revising selector policy, or sending ordinary candidate mail.
- A supervisor may hold a prospective handoff, not current unaffected work.

### Deliverables and recorded state

- Supervision policy/profile, helper commands, event/reducer/status projections,
  role prompts, docs, focused tests, and exact review receipt.

### Resource and economy contract

Cheap identity/currentness gate first; one XHigh review per materially changed
selection root; at most one Max adjudication per unresolved root; deterministic
reuse for identical retries; no model call for unchanged or unsupported evidence.

### QA and independent review

Different-role review of bad-choice, sound-choice, revise, reject, defer, unchanged,
self-selection, stale-source, and current-work preservation cases. The reviewer
must inspect the exact selection delta and bounded owner sources, not a watcher
summary or selector conclusion.

### Acceptance

- No consequential selection reaches authoring without one current accepted
  independent review; revise/rejected/deferred selections remain nonauthorizing;
  sound choices proceed once; unchanged state is a no-op; current implementation
  remains active.

### Negative tests

- Reject caller-supplied reviewer identity, selector self-review, missing feature/
  tracker inventory, later product or policy drift, unbound rejected alternatives,
  authoring before acceptance, optional preference as a finding, correction
  closure without changed selection evidence, duplicate review, and supervisor
  tracker/source writes.

### Completion evidence

Pending.

### Stop

Stop before tracker authoring, application, implementation, or selector-policy
learning.

---

## Block 2 — Integrate accepted selections with tracker authoring and current-work preservation

Status: `not-started`

### Objective

Make the accepted selection review an unavoidable, current input to tracker
authoring while preserving the exact current implementation program and every
existing ownership boundary.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: accepted choices flow automatically to the correct
  author while unsupported choices cannot create or modify implementation plans.
- Potential capability loss or regression: a new gate could contract the active
  range, duplicate tracker-authoring review, or deadlock safe work.
- Protected-capability effect: preserves full-range binding, accepted history,
  inserted prerequisites, exact program revision, one tracker writer, and
  automatic safe continuation.
- Architecture and operating-model effect: extends the existing placement-to-
  authoring handoff and program-revision precondition; does not create a writer.
- Tradeoff and source evidence: selection quality and tracker structural quality
  need separate reviews because a good feature choice may still produce a bad
  tracker, and a valid tracker may encode the wrong feature.

### Inputs and dependencies

- Block 1 current accepted review or explicit unchanged/no-authoring disposition.
- Existing placement handoff, tracker-authoring profile, program revision,
  implementation-range, successor-transition, and control-posture owners.

### Required work

- Extend the placement handoff and authoring input to bind exact selection packet,
  accepted selection review, findings lineage, policy/event heads, authoring
  target, current tracker/range, and application preconditions.
- Require selection-review currentness at authoring start and again at program-
  revision application. A later direct mission, product, tracker-inventory,
  selection, policy, or target change rejects/retries before canonical write.
- Keep the distinct tracker-authoring supervision profile responsible for
  program/feature/Block/architecture/dependency/acceptance/Stop quality of the
  exact tracker delta. It cannot substitute for the pre-authoring selection
  review, and the selection review cannot accept tracker structure not yet built.
- Preserve active remediation priority. Route a defect in accepted/current work
  through its existing local/program-revision owner; append nonblocking
  prospective work after current completion or to a separately authored
  successor/portfolio lane.
- Preserve exact direct ranges through insert/split/merge/renumbering. A reviewed
  selection, handoff, commit, task, Stop, or successor cannot terminalize or
  displace remaining requested Blocks.
- Make retry/interruption rehydrate the same authoring next action and safe
  frontier without duplicate tracker application or manual Resume.

### Scope and non-goals

- In scope: selection-review-to-placement/authoring binding, currentness,
  fail-closed application, range preservation, routing, and retry.
- Not in scope: authoring the selected tracker inside the selection owner,
  implementing selected work, outcome evaluation, or selector-policy change.
- Do not add a parallel tracker format, request ledger, or legacy compatibility
  path.

### Deliverables and recorded state

- Updated sibling interfaces, authoring packet/preconditions, range/program-
  revision checks, handoff/status projections, docs, real tracker fixtures, and
  focused/mapped tests.

### Resource and economy contract

Rehydrate the exact selection/review once, parse each affected tracker once, and
verify affected surfaces plus the full structural verifier. Unaffected accepted
proof is reused; a stale selection rejects before expensive authoring validation.

### QA and independent review

Independent end-to-end review of current revision, one successor, multi-tracker
portfolio, active defect, unrelated prospective work, interruption, duplicate,
stale review, range amendment, and final-response gating.

### Acceptance

- Accepted current selection reaches exactly one correct existing author;
  unaccepted/stale selection reaches none; resulting tracker work keeps its
  separate authoring review and exact range; unaffected current work continues.

### Negative tests

- Reject selection acceptance as tracker acceptance, selection-review omission,
  wrong author/target, stale inventory/policy/tracker, accepted-history rewrite,
  range contraction, open-to-completed map collision, duplicate application,
  prospective-work early return, and user scheduling leak.

### Completion evidence

Pending.

### Stop

Stop before implementing selected tracker Blocks or evaluating their outcome.

---

## Block 3 — Evaluate selection effectiveness and supported counterfactuals

Status: `not-started`

### Objective

Independently determine how well an exact selection performed after its canonical
program reaches a current observable outcome, preserving uncertainty and only
evidence-supported missed opportunities.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: the system learns whether it chose valuable work,
  not merely whether implementation completed or tests passed.
- Potential capability loss or regression: retrospective narratives could assign
  false causality, fabricate counterfactuals, or optimize for activity proxies.
- Protected-capability effect: preserves independent outcome proof, typed evidence,
  contrary evidence, uncertainty, product value, and no self-evaluation.
- Architecture and operating-model effect: adds a derived selection-effectiveness
  evaluator over existing canonical outcomes and supervision/resource evidence.
- Tradeoff and source evidence: full causal proof is often unavailable; bounded,
  explicit `inconclusive` evidence is more truthful than an always-positive score.

### Inputs and dependencies

- Block 2 exact accepted selection/review/authoring lineage.
- Current observable-outcome completion and relevant implementation, supervision,
  report, resource, incident, rollback, and user-correction evidence.

### Required work

- Build a deterministic evaluation packet that binds the exact original selection
  and forecasts, implemented tracker/program roots, actual current outcome, product
  and protected-capability effects, elapsed/token/command/tool/validation/review
  use, rework, incidents, rollbacks, user corrections, integration/coordination
  cost, abandoned work, and returned capacity.
- Require a distinct evaluator to classify each dimension and submit contrary
  evidence before deriving `effective`, `mixed`, `ineffective`, or `inconclusive`.
  Completion, release, test success, activity count, or supervisor praise alone
  cannot establish effectiveness.
- Compare forecast and actual values without converting unavailable values into
  zero or estimates into actuals. Record calibration/forecast error only on
  commensurate evidence.
- Retain selected-work false positives when independently observed value fails,
  duplication or protected regression appears, or resource/coordination costs
  materially exceed the bounded forecast.
- Retain rejected/deferred-work false negatives or missed opportunities only
  when later independent canonical evidence establishes the relevant product
  effect and the original candidate identity. Do not simulate unobserved worlds.
- Distinguish selection error from implementation defect, outcome-evidence gap,
  later mission change, external/reserved blocker, and supervisor false finding.
- Append corrections when later outcome evidence reopens or supersedes a prior
  evaluation; only one current head contributes to learning.

### Scope and non-goals

- In scope: outcome-linked selection evaluation, forecast calibration, supported
  counterfactual/missed-opportunity evidence, dispositions, corrections, and
  projections.
- Not in scope: changing the selector, ranking candidates again, reopening a
  completed program without a concrete defect, or claiming causal certainty.
- A negative evaluation does not roll back or delete a useful implemented feature;
  remediation follows its ordinary owner if current behavior is defective.

### Deliverables and recorded state

- Evaluation packet/result schemas, deterministic builders/validators, exact
  outcome linkage, current projection, tests, and reviewer evidence.

### Resource and economy contract

One evaluation per new current outcome head. Reuse the frozen selection packet and
canonical outcome roots; read only mapped implementation/supervision evidence;
unchanged or nonterminal state returns a no-op/inconclusive result without deep
review.

### QA and independent review

Blind evaluation cases cover effective, mixed, ineffective, inconclusive,
implementation-failure-not-selection-error, later mission change, corrected
outcome, supported missed opportunity, unavailable counterfactual, proxy gaming,
and selector/evaluator identity conflict.

### Acceptance

- Every learning-eligible selection has one current, independently reviewed,
  outcome-bound effectiveness disposition whose evidence dimensions and
  limitations can be reconstructed without relying on implementation completion
  or self-asserted value.

### Negative tests

- Reject outcome from another selection/program, noncurrent completion, arbitrary
  positive category, generic praise, self-evaluation, aggregate quality score,
  fabricated counterfactual, estimated-as-observed resource use, missing contrary
  evidence, duplicate current head, and effectiveness used as rollback authority.

### Completion evidence

Pending.

### Stop

Stop before proposing or applying a selector-policy change.

---

## Block 4 — Revise and compare selector policy without self-evaluation

Status: `not-started`

### Objective

Turn accumulated current selection-effectiveness evidence into at most one bounded
selector-policy candidate and accept it only when independent comparison shows a
supported improvement without protected regressions.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: candidate generation, evidence thresholds, ranking,
  uncertainty handling, portfolio composition, and resource budgeting improve
  from observed selection results.
- Potential capability loss or regression: the selector could overfit retained
  cases, optimize monitor-visible proxies, erase useful diversity, or self-approve.
- Protected-capability effect: preserves direct intent, divergent generation,
  independent selection/evaluation, separate evidence dimensions, no-op eligibility,
  bounded resources, and reversible policy changes.
- Architecture and operating-model effect: adds a versioned selector-policy
  artifact and separately evaluated policy-candidate path through existing source,
  review, Git, and release owners.
- Tradeoff and source evidence: explicit versioned policy supports real learning;
  limiting each cycle to one bounded candidate avoids unreviewed recursive churn.

### Inputs and dependencies

- Block 3 current effectiveness evidence from one or more exact selection cycles.
- Current selector contract/policy, retained historical selection cases, and
  current operator/resource ceilings.

### Required work

- Represent the current selector policy explicitly: candidate-source coverage,
  divergence rules, evidence admission thresholds, dimension comparison rules,
  uncertainty/contrary-evidence treatment, portfolio/dependency/resource rules,
  current-work preservation, Stops, and revisit triggers.
- Build at most one policy candidate per eligible evidence root. Bind exact
  predecessor policy, supporting and contrary effectiveness records, hypothesized
  improvement, affected rules, protected invariants, rollback, and expiry/revisit.
- Permit changes to generation coverage, explicit thresholds, dimension-specific
  comparisons, portfolio/resource heuristics, and evidence widening only when
  supported. Do not introduce a hidden learned utility or unbounded model prompt.
- Create chronological retained comparison sets that prevent candidate policy
  construction from reading the held-out expected dispositions. Include sound,
  poor, no-op, current-work, multi-tracker, uncertainty, and goal-boundary cases.
- Compare incumbent and candidate on each declared dimension, false positive/
  negative posture, missed supported work, resource use, protected behavior,
  and no-op economy. A different independent evaluator adjudicates the comparison.
- Require one subsequent or shadow live cycle under identical input/currentness
  before accepting a consequential candidate. Shadow output remains nonauthorizing
  and cannot alter the live selection.
- Accept only a supported vector improvement with no protected regression and no
  new human-scheduling leak. `mixed`, inconclusive, or overfit candidates remain
  rejected/deferred; identical evidence produces no candidate.
- Apply an accepted policy only through the existing source owner, exact Git
  review, release owner, and safe monitor refresh. Preserve immutable predecessor
  policy and exact rollback identity.
- Feed supervisor review misses/false interventions to the existing supervision-
  effectiveness and Factory Evolution owners rather than letting the selector
  modify its reviewer.

### Scope and non-goals

- In scope: selector-policy representation, bounded candidate generation,
  retained/forward comparison, independent acceptance, application handoff, and
  rollback identity.
- Not in scope: online selection review, target feature implementation, continuous
  automatic tuning, arbitrary prompt mutation, training a general model, or
  changing supervisor policy from selector evidence alone.
- No policy change is required when evidence is sparse or outcomes disagree.

### Deliverables and recorded state

- Current policy artifact, policy-candidate and comparison schemas/builders,
  retained case corpus, shadow-cycle receipt, acceptance review, application
  handoff, and rollback metadata.

### Resource and economy contract

At most one candidate and one retained comparison per new effectiveness root,
plus one forward shadow cycle. Reuse immutable case inputs/results. Stop early on
any protected regression; unchanged evidence performs zero policy work.

### QA and independent review

Independent review challenges training/held-out leakage, reward gaming, benchmark
overfit, self-evaluation, hidden score, reduced candidate diversity, missed
required work, current-range displacement, resource inflation, stale predecessor,
duplicate application, and rollback currentness.

### Acceptance

- One exact candidate either proves a dimension-visible, independently reviewed,
  forward-confirmed improvement without protected regression and becomes eligible
  for existing-owner application, or remains rejected/deferred with the incumbent
  unchanged.

### Negative tests

- Reject policy self-approval, selector also acting as evaluator, held-out leakage,
  pass-count optimization, one-episode overgeneralization, opaque weights/score,
  missing contrary evidence, stale or replaced predecessor, protected regression,
  inconclusive-as-improved, shadow output used as authority, and direct live edit.

### Completion evidence

Pending.

### Stop

Stop before integrated dogfood, release promotion, or active supervisor refresh.

---

## Block 5 — Dogfood current-choice supervision and cross-cycle improvement

Status: `not-started`

### Objective

Prove in one isolated, reproducible two-cycle run that online supervision catches
a bad feature/design selection and later outcome evidence improves the selector
without displacing canonical implementation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: demonstrate actual closed-loop behavior rather than
  schema-valid artifacts or favorable reviewer prose.
- Potential capability loss or regression: synthetic or unstable dogfood could
  overclaim selection quality, mutate live work, or teach to its own fixtures.
- Protected-capability effect: verifies role separation, current-work continuation,
  product outcome, resource bounds, no-op economy, and no live/reserved effects.
- Architecture and operating-model effect: supplies the first retained selection-
  quality calibration and selector-policy comparison evidence.
- Tradeoff and source evidence: one high-precision raw run plus deterministic
  semantic projection is sufficient for initial acceptance; broad repeated live
  experimentation is not.

### Inputs and dependencies

- Blocks 0–4 exact candidate implementation and fixtures.
- Isolated Git repositories/workspaces and fixed current source/skill identities.

### Required work

- Build a Git-less reproducible dogfood runner with run-specific raw evidence and
  a separately rooted deterministic nonauthorizing semantic projection.
- Freeze a realistic existing-feature/current-behavior and mixed tracker inventory,
  including planned, active, completed, rejected, retired, and superseded work.
- Cycle A: generate multiple feature/refactor/design/program candidates, preserve
  rejected alternatives and forecasts, and independently reject or revise one bad
  choice before any authoring handoff. Include at least duplication/poor design or
  current-work starvation, plus one sound alternative that proceeds.
- Author and implement the accepted sound choice through the existing isolated
  owners while the frozen current requested range continues. Prove separate
  selection and tracker-authoring reviews.
- Produce an independently observed product/program/resource outcome. Evaluate
  the original choice, including at least one forecast correction and one
  supported or explicitly unavailable counterfactual.
- Derive one bounded selector-policy candidate, compare it with the incumbent on
  chronologically retained cases, run one shadow/subsequent Cycle B, and accept or
  reject it from exact evidence.
- Show Cycle B improves a supported selection behavior without protected
  regression, or truthfully retain the incumbent if the evidence is inconclusive.
  Then rerun unchanged inputs and prove zero generation/review/evaluation/policy
  producer calls.
- Exercise interruption/retry after selection review, authoring handoff, outcome,
  effectiveness, policy candidate, comparison, and shadow result. Preserve one
  canonical transition and no duplicated implementation/effect.
- Assert every live/release/Gmail/deployment/credential/destructive/lifecycle flag
  false. Clean all disposable workspaces.

### Scope and non-goals

- In scope: isolated two-cycle live-behavior proof, reproducible evidence,
  negative/recovery cases, and deterministic projection.
- Not in scope: live product changes, production release, external effects,
  generalized benchmarking, continuous ideation, or manufacturing a favorable
  second-cycle result.
- The dogfood may prove `inconclusive` policy learning if evidence does not support
  improvement, but that cannot satisfy final selector-improvement acceptance.

### Deliverables and recorded state

- Raw and projected dogfood evidence, exact source/role roots, selection review,
  tracker artifacts, outcomes, effectiveness records, policy candidate/comparison,
  shadow-cycle result, recovery proof, and cleanup receipt.

### Resource and economy contract

Predeclare total model, elapsed, token, command, validation, review, and workspace
ceilings. Retain completed producer results across interruption. Run exactly two
material cycles and one unchanged replay; no third cycle merely to obtain a pass.

### QA and independent review

Separate reviewers inspect candidate diversity, original bad/sound choices,
selection supervision, authoring quality, current-work preservation, observed
outcome, counterfactual limits, effectiveness, incumbent/candidate policy
comparison, shadow cycle, raw/projection integrity, and all Stops.

### Acceptance

- Exact evidence demonstrates the complete union: sound feature/program selection,
  bad-choice prevention before authoring, and outcome-driven improvement of future
  selection quality, with canonical current work and authority boundaries intact.

### Negative tests

- Reject pre-labeled reviewer conclusions, selector/evaluator collapse, authoring
  before review, process-only effectiveness, fabricated counterfactual, fixture-
  aware policy, training leakage, root-consistent semantic mutation, unstable
  projection, repeated producer work, current-range displacement, and any live or
  reserved effect.

### Completion evidence

Pending.

### Stop

Stop before final source acceptance, release promotion, installed monitor refresh,
or terminal completion claim.

---

## Block 6 — Freeze, review, release, refresh, and prove effectiveness

Status: `not-started`

### Objective

Accept one exact integrated implementation, promote it through the single release
owner, refresh compatible supervisors at safe boundaries, and prove the installed
selection-quality loop remains current and effective.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates, installs, and
  observes the already implemented capability without adding another selection or
  learning mechanism.

### Inputs and dependencies

- Block 5 frozen source and independently reviewed dogfood evidence.
- Current flagless release-owner and automatic safe monitor-refresh contracts.

### Required work

- Run focused selection/supervision/effectiveness/policy tests, mapped four-skill
  suites, all skill validators, tracker verifier, compile, diff, exact archive,
  clean-tree, ancestry, currentness, and full maintained validation warranted by
  the final affected surface.
- Freeze and non-force push the exact candidate. Obtain independent exact-revision
  review of code, contracts, negative cases, raw/projection evidence, and this
  tracker; remediate findings in successor commits with affected proof rerun.
- After exact independent acceptance, ask the single release owner to run the
  standard flagless promotion for that exact revision. Consume only its verified
  activated four-skill release identity and roots.
- Refresh compatible running supervisors at their next actual safe boundaries,
  preserving mission, tracker/range, events, cursors, incidents, automations,
  Gmail bindings, schedules, models, policy, and manual release pins.
- Verify installed roots, selection profile binding, role separation, supervisor
  health, current implementation continuation, selection review, and selector-
  policy identity after refresh. On failure, request release-owner rollback and
  restore prior supervisor binding.
- Run one current material selection checkpoint and one later outcome/effectiveness
  checkpoint using the installed release. Prove accepted/rejected/no-op behavior,
  exact policy identity, no duplicated review/effect, and no regression of current
  work.
- At genuine governing-tracker completion, use the normal terminal capability
  reconciliation, deliver/read back both terminal reports, record delivery, then
  pause/terminate the associated monitor and automations. Do not stop supervision
  merely because this source tracker or a release commit exists.

### Scope and non-goals

- In scope: exact acceptance, promotion, installed-root verification, compatible
  safe refresh, rollback, installed-effectiveness observation, and normal terminal
  lifecycle.
- Not in scope: unrelated Software Factory changes, forced monitor refresh, direct
  supervisor pointer writes, manual pin override, generalized deployment, or a new
  product program chosen merely to demonstrate recursion.
- Ordinary promotion uses exact independent acceptance and the normal release
  owner; do not require or recreate a separate signed-review/quiescence-permit
  subsystem unless the current release primitive itself requires it.

### Deliverables and recorded state

- Exact accepted source/tree, release/manifest/skill roots, refresh and rollback
  receipts, installed selection-review/policy identities, current outcome/effective-
  ness evidence, terminal lifecycle proof, and final tracker evidence.

### Resource and economy contract

Reuse unchanged proof roots; validate affected slices before one final broad run;
promote once; refresh each compatible supervisor once at its safe boundary; use
cheap installed/currentness checks before any deep checkpoint.

### QA and independent review

Independent exact source, release, installed-root, supervisor-refresh, role/profile,
selection-decision, selector-policy, rollback, effectiveness, and terminal-
lifecycle reviews.

### Acceptance

- Exact accepted source and installed roots agree; compatible supervisors use the
  same selection profile and selector policy without lost mission/range/cursors;
  one current selection/effectiveness cycle behaves as reviewed; rollback restores
  the prior accepted release; and genuine tracker completion delivers reports and
  shuts down only its associated monitoring.

### Negative tests

- Reject unreviewed or changed source, partial install, direct pointer write,
  unsafe refresh, lost mission/range/cursor, manual-pin override, stale profile or
  policy, duplicate review/cycle, changed evidence accepted as no-op, rollback to
  an unaccepted release, report-less terminalization, and active automation after
  verified completion shutdown.

### Completion evidence

Pending.

### Stop

Stop after exact installed effectiveness and governing-tracker terminal proof; do
not select or begin another program solely to keep the recursive loop active.

## 8. Verification matrix

| Capability or invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Exact selection-to-review-to-outcome-to-policy lineage | 0 | 1–5 | 6 |
| Current feature and all tracker states inform selection | 0 | 1, 5 | 6 |
| Consequential feature/design choice is independently reviewed before authoring | 1 | 2, 5 | 6 |
| Terra/XHigh/Max roles remain separated and existing supervision owner is reused | 1 | 5 | 6 |
| Bad choices revise/reject without derailing current canonical work | 1 | 2, 5 | 6 |
| Accepted choice reaches only the correct tracker author and preserves range/history | 2 | 5 | 6 |
| Selection quality is judged from current observable outcomes, not process proxies | 3 | 5 | 6 |
| Supported false positives, false negatives, and missed opportunities remain typed | 3 | 4, 5 | 6 |
| Selector policy changes are versioned, bounded, independently compared, and reversible | 4 | 5 | 6 |
| Held-out and forward comparison reject gaming, leakage, and protected regression | 4 | 5 | 6 |
| Two-cycle dogfood proves current-choice supervision and future-choice improvement | 5 | 6 | 6 |
| Unchanged replay performs no generation, review, evaluation, or policy work | 0 | 1, 3–5 | 6 |
| Installed supervisors use the accepted profile/policy and rollback remains exact | 6 | — | 6 |

## 9. Final completion definition

This tracker is complete only when all seven Blocks are accepted at exact current
revisions; the active recursive product-program tracker has consumed an exact,
independently reviewed integration map without rewriting its accepted or in-flight
Blocks; every consequential feature/design/program selection is currentness-bound
and independently reviewed before authoring; selection review and tracker-authoring
review remain distinct; exact observable outcomes independently establish
selection effectiveness or truthful inconclusiveness; supported missed
opportunities and counterfactual limits remain explicit; at least one bounded
selector-policy candidate is compared with its incumbent on retained and forward
evidence and either proves a protected-regression-free improvement or is rejected
without changing the incumbent; dogfood proves both bad-choice prevention and a
later improved selection; unchanged replay performs no deep work; the accepted
release is promoted and compatible supervisors refresh through their existing
owners; current programs, ranges, history, direct intent, roles, external
boundaries, and rollback remain intact; and governing-tracker completion—not a
candidate, review, commit, or release alone—controls terminal report delivery and
monitor shutdown.
