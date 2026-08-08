# Software Factory Adaptive Implementation Decision Control Implementation Tracker

- Tracker status: `planning`
- Tracker sequence: Blocks 0–7
- Repository: `https://github.com/estill01/software-factory`
- Planning baseline: `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`
- Governing objective: `Allow Software Factory to notice and correct a materially bad implementation decision inline while executing, selectively compare an isolated alternative when implementation evidence is needed, and amend the active tracker only when live evidence invalidates the Block contract itself, then continue autonomously with configurable authority.`

## 1. Purpose and intended outcome

Add a three-path adaptive decision-control loop to Block execution. The normal
path remains ordinary economical implementation with near-zero added work. When
Software Factory detects a materially bad approach that still fits the current
Block contract, it corrects the decision inline: stop the bad path, preserve
valid work, compare bounded alternatives, select and validate the better
source-backed path, record the decision, and continue without tracker editing,
a new authoring thread, a separate supervision lifecycle, or human input.

When the relative value of an incumbent and a materially better possible path
cannot be established without implementation evidence, Software Factory may
run one isolated, resource-bounded candidate lane. The incumbent remains the
only production authority, safe incumbent work may continue, and an automated
independent comparison either selects one path for cutover or stops the
candidate. The system never keeps two live implementations merely because both
were explored.

Adaptive tracker amendment is the exceptional structural path. It is used only
when live evidence invalidates the Block contract itself, changes dependencies,
acceptance, or the Stop, or materially affects later Blocks. That path uses the
existing tracker-authoring owner and independent authoring supervision. The
tracker remains the active plan, but open program structure may change when the
governing product capability would otherwise be harmed by waterfall adherence.

All three paths apply symmetrically when Software Factory is improving its own
skills and supervision machinery and when it is implementing an unrelated
target product. The target's direct mission, product-capability frame, protected
capabilities, and repository authorities govern either case. `Software Factory`
as target adds self-modification separation and promotion safeguards; it does
not use a different decision model.

Completion means:

- a sound unchanged path incurs only a cheap fingerprint check, no extra model
  or reviewer cycle, no candidate lane, and no tracker churn;
- a wrong owner, lower-power shortcut, unnecessary abstraction, wasteful retry,
  or other bad approach inside the active Block is corrected inline and
  implementation continues automatically;
- equivalent unchanged fingerprints are not reconsidered, and correction
  authority escalates only as far as the actual decision requires;
- a candidate lane opens only when concrete evidence supports a material
  alternative, implementation evidence is necessary to compare it, isolation
  is safe, and expected decision value exceeds duplicate-work cost;
- every candidate has one hypothesis, affected scope, resource/time ceiling,
  Stop, capability/protected-capability contract, focused proof, and independent
  comparison against the incumbent before any cutover;
- a winning candidate cuts over through the normal target owner, while a losing
  candidate stops and leaves only useful non-authoritative evidence;
- one exact structural-revision packet is formed only when the Block contract
  or later program is invalidated, preserving mission, learned facts, paths,
  affected Blocks, valid work, stale proof, safe frontier, and Stop;
- the authoring owner can revise open Blocks while preserving accepted history,
  and the existing authoring-supervision profile independently challenges the
  exact structural delta;
- configurable modes can turn adaptive action down or permit full autonomy
  within the direct mission and already granted repository authority;
- full-autonomous mode treats a request for human input as failed control:
  ordinary product, architecture, decomposition, implementation, comparison,
  and cutover judgments are resolved by the system, while unavailable external
  authority is narrowly deferred without stopping independent work or
  fabricating approval;
- inline correction, candidate cutover, and accepted structural revisions
  selectively invalidate only affected proof and resume automatically; and
- paired target-repository and Software-Factory-self cases demonstrate inline
  correction, bounded parallel comparison, exceptional structural replanning,
  a justified no-correction decision, zero human requests in full-autonomous
  mode, current operator-visible behavior, and no silent mission change or
  self-promotion.

### Mission frame

- Primary outcome: Software Factory notices and corrects materially bad
  implementation decisions early enough to produce a better system, normally
  inside the active Block and without turning correction into tracker
  reauthoring.
- Observable completion: exact external-target and Software-Factory-self cases
  show current inline correction, selective parallel comparison/cutover,
  exceptional tracker amendment, automatic continuation, and a proportionate
  unchanged path with no added reviewer cycle.
- Ordinary effect classes needed: three-path routing, inline correction,
  fingerprint deduplication, bounded candidate isolation and comparison,
  structural revision semantics, authoring and verifier support, independent
  authoring supervision, configurable authority/budgets, selective currentness
  invalidation, automatic resume, dual-target safeguards, tests,
  documentation, and exact-candidate review.
- Hard direct authority or safety boundaries: the direct mission and repository
  instructions remain controlling; independent reviewers do not write the
  tracker or target; accepted evidence is not rewritten; `supervision_log.py`
  remains the public canonical supervision writer; full autonomy cannot invent
  credentials, spending authority, destructive permission, external-release
  authority, or a materially different product goal.
- Material goal alteration or reversal: changing the governing outcome rather
  than its implementation program, discarding a protected capability without
  direct support, granting new external or destructive authority, eliminating
  independent review of Software Factory self-modification, or replacing the
  three-skill system with a general planner service requires renewed direct
  authority and is not a program revision.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker changes how implementation scope,
  architecture strategy, Block decomposition, authority, and continuation can
  change during a live run for both target products and Software Factory.
- Direct product sources: direct user instructions in source thread
  `019fe023-f305-70d2-b69a-7f9565bebe86` on 2026-08-08 that Software Factory
  should (a) remain governed by the implementation tracker while identifying
  different or better implementations that achieve the broader product or
  functionality goal, (b) update open Block content when live learning
  warrants it instead of remaining waterfall-bound, (c) apply the capability
  to both Software Factory and the underlying implemented project, (d) treat
  ordinary human input as a failure mode, and (e) make permissiveness
  configurable through fully autonomous operation; repository `README.md` at
  SHA-256 `992a34de6c894d43c11028e7e2cc5ea4abc7418c896539341542fbd9dabad372`;
  the accepted
  `docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md`
  at SHA-256
  `ecc7b31ebd7bd7bc825746dded4059be2ddcc56377f4a702e1ab7781d09e07c6`;
  `implement-tracker-blocks/SKILL.md` at SHA-256
  `887b3eca6f8ca1219878990c0031c84675a7f6258e321e19dd036b6899366bab`;
  and `supervise-tracker-runs/references/supervision-policy.md` at SHA-256
  `4d3404b4d1426fae61104dc67b33eef5e940b9bf3dfddc0572dc0e8e8b4b9b66`.
- Advisory design inputs, not product authority: routed `codex_delegation`
  items 288 and 289 from side-conversation source thread
  `019fe21e-486e-7c11-90b9-6bfbf19457c1`; the planned
  `docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`
  at SHA-256
  `dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424`;
  and the external
  `software_factory_adaptive_alignment_and_control_implementation_tracker (1).md`.
  These sources may inform bounded authoring choices but cannot create or
  override a requirement, mission, permission, or reserved authority.
- Product thesis and intended effect: Software Factory should autonomously
  deliver the governing capability through an inspectable, dependency-ordered
  program while correcting bad implementation decisions at their smallest
  causal boundary; tracker structure changes only when that boundary is no
  longer sufficient.
- Protected capabilities: direct-mission authority, target-product alignment,
  independent supervision, sole-writer boundaries, accepted-history integrity,
  dependency-safe continuation, maximal autonomous scope, exact Block stops,
  current observable-outcome proof, bounded resource use, and reversible
  evidence-gated Software Factory self-improvement.
- Architecture strategy: the tracker author's proposed source-compatible design
  is to extend the executor with a default inline-correction path and a selective
  isolated candidate lane, use the existing author and supervisor owners only
  for exceptional structural amendment, and reuse Factory evolution for self-
  target changes. This is a reviewable design selection grounded in the direct
  capability objective and current repository owners, not a requirement created
  by the advisory packets. Do not add a fourth skill, planner service, mutable
  shadow tracker, or second event ledger.
- Requested capability: source-backed autonomous implementation decision
  correction, with bounded parallel comparison when necessary and structural
  replanning only when the active program contract is invalidated.
- Proportionality: use the smallest control that can correct the actual defect:
  normal continuation for a sound path, inline correction within the Block,
  bounded candidate comparison when behavior must decide, and supervised
  tracker amendment only for structural effects.
- Tradeoffs: inline correction adds limited decision work; parallel candidates
  intentionally duplicate bounded implementation effort; tracker amendment
  adds revision/currentness cost. Exact triggers, ceilings, deduplication,
  independent cutover review, and selective invalidation keep those costs below
  the expected outcome benefit.
- Uncertainty: the current repository proves capability framing and one Factory
  evolution cycle but not inline decision correction, parallel candidate
  cutover, continuous authoring supervision, or live structural revision. This
  tracker treats accepted authoring supervision as a prerequisite only for the
  exceptional structural path, not for normal or inline execution.

## 2. Target architecture and authority boundaries

```text
direct mission + capability frame + accepted tracker + live repository
                              |
                     active Block execution
                              |
                 cheap exact fingerprint check
                              |
               +--------------+--------------+
               |                             |
       sound/unchanged                 concrete bad decision
               |                             |
      continue normally            classify smallest boundary
                                             |
                      +----------------------+----------------------+
                      |                      |                      |
               inside Block          comparison needs       Block contract or
                  contract          implementation proof     later plan invalid
                      |                      |                      |
                      v                      v                      v
            inline correction       isolated candidate       structural packet
             preserve/compare       incumbent stays owner   affected graph/safe
             select/validate        ceiling + focused proof      frontier
             record/continue                 |                      |
                                             v                      v
                                  independent comparison    author sole writer
                                      /          \          authoring supervision
                                  loses          wins                |
                                    |              |                 v
                               stop lane       cut over       accepted/revise/reject
                                                  |                  |
                                                  +--------+---------+
                                                           |
                                                           v
                                               selective invalidation
                                               and automatic resume
                                                           |
                                                           v
                                             current target behavior and
                                               terminal reconciliation
```

Authority rules:

1. The mission root and materially governing product outcome remain fixed.
   Direct sources may clarify an omitted required capability, but no correction,
   candidate, or amendment can invent or reverse product intent.
2. The sound unchanged path is the default. It performs one cheap exact
   fingerprint/currentness check and continues without an extra model,
   reviewer, authoring, or candidate cycle.
3. Inline correction is the normal response to a wrong owner, lower-power
   shortcut, unnecessary abstraction, wasteful retry, protected-capability
   regression, or other bad approach that remains inside the current Block's
   objective, acceptance, dependencies, and Stop. The implementation owner may
   make that correction under the current Block without editing the tracker.
4. Inline correction preserves valid work, stops only the causal bad path,
   compares bounded alternatives, uses the normal authoritative owner,
   validates the affected result, records selected/rejected paths, and
   continues. It does not require a new authoring thread or supervision
   lifecycle.
5. A parallel candidate is permitted only when concrete evidence supports a
   materially better alternative, implementation evidence is necessary for a
   fair comparison, isolation is safe, and expected decision value exceeds the
   declared duplicate-work cost. The incumbent remains authoritative until
   cutover.
6. A candidate lane has one hypothesis, affected scope, resource/time ceiling,
   Stop, capability contract, protected-capability contract, focused-first
   validation order, and independent comparison. It never gains simultaneous
   production authority or creates a second canonical owner.
7. A winning candidate cuts over through the normal target owner. A losing or
   inconclusive candidate stops; useful evidence may remain as non-authoritative
   history, but two live implementations do not persist.
8. Structural tracker amendment is exceptional. The implementation thread may
   package it only when the Block contract itself is invalidated, dependencies,
   acceptance, or Stop must change, or the decision materially affects later
   Blocks. It cannot silently edit the tracker.
9. `author-implementation-trackers` remains the sole tracker-writing method.
   The `tracker-authoring` supervision profile independently reviews the exact
   structural delta; supervisors remain read-only and cannot implement it.
10. Accepted Blocks, commits, reviews, findings, and evidence remain historical
    truth. A defect in accepted work creates an append-only remediation or
    successor Block; it never rewrites prior acceptance.
11. Adaptive authority is policy-controlled. `full-autonomous` permits every
    reversible in-authority inline correction, candidate decision, cutover, and
    mission-preserving structural amendment after its required automated review.
    It never requires a human rubber stamp or manual Resume.
12. A genuinely unavailable credential, spend, destructive permission,
    external communication, release act, or direct goal change is recorded as
    `reserved-external`; it is not fabricated, does not stop unaffected work,
    and does not create repeated human requests.
13. `supervision_log.py` remains the public canonical supervision writer.
    Decision, candidate, cutover, and program-revision evidence compose current
    mission, checkpoint, decision, steer, resolution, and currentness owners
    rather than creating a separate operational ledger.
14. The same protocol governs `target-repository` and `software-factory`
    targets. A Software Factory self-change additionally requires distinct
    proposer/author, implementer, reviewer, and evaluator identities and the
    existing Factory-evolution promotion posture; it cannot self-certify or
    self-promote.
15. Reports, evolution packets, candidate comparisons, proposed revisions, and
    review narratives are evidence or derived artifacts. None independently
    changes the mission, tracker, target, production authority, or promotion
    state.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Tracker creation, amendment, Block graph, accepted-history preservation, and handoff | `author-implementation-trackers/SKILL.md` and `references/amendment-and-renumbering.md` | adapt |
| Tracker structure and current full-profile validation | `author-implementation-trackers/scripts/verify_tracker.py` | adapt narrowly |
| Inline implementation-path selection, correction, validation, Block audit, and resume | `implement-tracker-blocks/SKILL.md` and `references/product-capability-review.md` | adapt as primary owner |
| Isolated candidate branches/worktrees, checkpoints, comparison, and cutover | current Git checkpoint and target-owner workflow in `implement-tracker-blocks/SKILL.md` | adapt selectively |
| Mission binding, decisions, incidents, checkpoints, steering, currentness, and canonical writes | `supervise-tracker-runs/scripts/supervision_log.py` | adapt for decision/candidate evidence |
| Independent tracker-authoring review | `docs/software-factory-tracker-authoring-supervision-implementation-tracker.md` | require only for structural amendment; reuse after implementation |
| Evidence-grounded Software Factory skill evolution and promotion disposition | `factory_evolution.py` and `references/factory-evolution-contract.md` | reuse for self-target changes only |
| Human-input avoidance, dependency cuts, and bounded continuation | current author, executor, and supervision decision contracts | adapt to configurable authority |
| Public architecture and operating guidance | `README.md` and the three skill metadata owners | update after demonstrated behavior |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Current Software Factory repository | `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3` | adapt | 0–7 | Add inline correction, selective candidate comparison, and exceptional program revision without weakening accepted behavior |
| Accepted learning and capability-evolution MVP | tracker SHA-256 `ecc7b31ebd7bd7bc825746dded4059be2ddcc56377f4a702e1ab7781d09e07c6` | reuse | 0, 6, 7 | Reuse exact evidence and self-change evaluation; do not rerun evolution by default |
| Planned tracker-authoring supervision program | tracker SHA-256 `dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424` | external prerequisite for structural path | 0, 4, 7 | Implement and accept its Blocks before structural amendment is enabled; inline correction remains independent |
| Current authoring amendment method | `author-implementation-trackers/references/amendment-and-renumbering.md`, SHA-256 `28edc9682cbfe87acbd61917a67a780e8bd7b282e16588befb7799f6bbe6067a` | adapt | 0, 4 | Make exceptional live revision exact, machine-checkable, and resumable |
| Current execution capability-review method | `implement-tracker-blocks/references/product-capability-review.md`, SHA-256 `68d255c1cd7c03b61b9278e0d1a20290c7452abb661ba00ae47d15e60bfc3017` | adapt | 0–3, 6 | Correct inside the Block first; open candidate or structural paths only on exact triggers |
| Current Git checkpoint/branch behavior | `implement-tracker-blocks/SKILL.md` at planning baseline | adapt | 2, 6–7 | Add one isolated candidate lane and automated winning-path cutover without dual authority |
| Current supervision decision and continuation contracts | `supervise-tracker-runs/references/supervision-policy.md`, SHA-256 `4d3404b4d1426fae61104dc67b33eef5e940b9bf3dfddc0572dc0e8e8b4b9b66` | adapt | 0, 3–6 | Add bounded correction/candidate evidence, structural disposition, and configurable no-human posture |
| Inline-first and parallel-alternative advisory | routed `codex_delegation` items 288 and 289 from source thread `019fe21e-486e-7c11-90b9-6bfbf19457c1` | advisory-only; not authority | 0–7 | Evaluate the suggested design against eligible direct sources and current owners; no requirement or permission derives solely from these packets |
| Adaptive alignment and control implementation tracker supplied as planning input | external 30-Block document | not adopted as this execution tracker | 0, 4, 7 | Reuse dual-target alignment and configurable authority; defer prospective hooks, event streaming, control libraries, and generalized runtime monitoring |

## 5. Scope, non-goals, and proportionality

### In scope

- Cheap exact recognition of a sound unchanged path.
- Source-backed detection and inline correction of bad approaches within the
  active Block contract.
- Bounded alternative comparison, selected/rejected-path evidence, focused
  validation, and automatic continuation.
- Selective isolated candidate branches/worktrees with one hypothesis, ceiling,
  Stop, independent comparison, and single-authority cutover or retirement.
- Structural replanning triggers only when the Block contract or later program
  is invalidated.
- Mission-preserving revision of current and future Block content, ordering,
  decomposition, dependencies, acceptance, negative tests, and Stops.
- Append-only treatment of accepted history and exact old-to-new mappings.
- One bounded revision packet and exact tracker-delta identity.
- Supervised authoring of structural tracker deltas through the existing
  profile; inline corrections do not start authoring supervision.
- Configurable `fixed`, `recommend`, `reviewed-autonomous`, and
  `full-autonomous` decision/candidate/revision modes and bounded candidate
  budgets.
- Explicit human-input avoidance and reserved-external safe deferral.
- Selective evidence invalidation, dependency-safe continuation, and automatic
  implementation resume.
- One shared protocol for Software Factory self-work and external target work.
- Focused, paired, interrupted-resume, compatibility, and operator-visible
  dogfood proof.

### Out of scope

- Replacing the governing mission with a newly generated product strategy.
- Prospective App Server streams, lifecycle hooks, event-chain engines,
  detector/control registries, adaptive sampling routers, or a general runtime
  control platform.
- A fourth skill, planner service, database, mutable shadow tracker, dashboard,
  scheduler, or second event ledger.
- Hidden chain-of-thought capture or persuasive reasoning as authority.
- Autonomous credentials, spending, destructive actions, external messages,
  release, deployment, or other authority not already granted.
- Rewriting accepted commits, reviews, evidence, or Block history.
- Correction, candidate work, or replanning for optional cleanup, style
  preference, hypothetical future reuse, or a locally passing alternative with
  no material capability benefit.
- Two simultaneous production owners, permanent dual implementations, or a
  candidate lane without isolation and explicit decision value.
- Removing independent review from Software Factory self-modification.

### Proportionality

Build the smallest causal correction through current owners. The default sound
path performs one cheap fingerprint check and no additional model, review,
candidate, or authoring work. A bad decision inside the Block is corrected
inline. Parallel implementation is used only when an evidence-backed material
choice cannot be resolved by read-only comparison and safe isolation plus a
declared ceiling makes the expected decision value positive. Tracker amendment
is used only when inline correction cannot preserve the Block contract or later
program. Every path compares the local correction, bounded-general option, and
available architectural owner without assuming that either the incumbent or
the most general new design should win.

## 6. Block execution contract

1. Execute Blocks 0–7 in dependency order and audit each Block before
   advancing.
2. Inline-correction and candidate foundations may begin from the planning
   baseline. Do not enable Block 4 structural amendment until the separate
   tracker-authoring supervision tracker is implemented and accepted at an
   exact revision. Its planning document remains separate and valid.
3. Re-read the active Block and inspect the live authoring, execution,
   supervision, evolution, tests, policy state, and Git work before editing.
4. Preserve implementation-run defaults, legacy policies, active tracker state,
   unrelated work, accepted evidence, rejected candidates, and exact Git
   history.
5. Treat the mission root as fixed. First ask whether the current path is sound;
   then whether a defect can be corrected inside the active Block; then whether
   a candidate must be built; use structural amendment only after those smaller
   paths are proven insufficient.
6. Stop a bad action at its smallest safe boundary, preserve valid work, inspect
   exact evidence, compare bounded alternatives, select the lowest-complexity
   path that fully supplies the capability, validate the affected result,
   record selected/rejected paths, and continue automatically.
7. Do not reconsider an equivalent unchanged fingerprint. A later attempt needs
   new repository, behavior, capability, dependency, or outcome evidence.
8. Open at most one candidate lane for one decision. Checkpoint the incumbent,
   bind hypothesis/scope/capability/ceiling/Stop, keep the incumbent as sole
   authority, run focused proof first, and permit safe concurrent incumbent
   work only where dependencies do not conflict.
9. Cut over only from current observable outcome, implementation/maintenance
   cost, reversibility, compatibility, protected-capability evidence, and
   automated independent review. Stop a losing/inconclusive lane and do not
   retain two live owners.
10. Form a structural revision packet only when the Block contract or later
    graph is invalidated. Keep the authoring owner as sole tracker writer and
    authoring supervision read-only.
11. Apply canonical authority mode and candidate budget. In
    `full-autonomous`, do not seek human input for ordinary engineering judgment
    or require manual Resume; narrowly defer only acts the system cannot possess
    or perform.
12. Continue the maximal safe frontier during correction, candidate comparison,
    structural review, external deferral, and cutover/application.
13. Mutate only open Blocks. Repair accepted work through an append-only
    remediation or successor Block and preserve prior status and evidence.
14. Invalidate only currentness actually changed by correction, candidate
    cutover, or tracker revision. Reuse exact unaffected proof and producers.
15. Use Factory evolution only when Software Factory skills or methods change;
    do not run it for ordinary target-repository correction or replanning.
16. Finish mutating review before final mapped validation, freeze the candidate,
    obtain exact-revision independent review, and run broad mapped proof only
    once unless a mapped successor change invalidates it.
17. Stop after current operator-visible outcome proof and the declared dogfood
    cases. Do not continue into prospective monitoring or a generalized control
    platform.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/target revision: `<target commit/root or not-applicable>`
- Inputs: `<mission, tracker, policy, repository, evidence paths and hashes>`
- Decision path: `<unchanged, inline, candidate, or structural; trigger and fingerprint>`
- Inline correction: `<bad path stopped, valid work preserved, selected correction>`
- Candidate lane: `<hypothesis, scope, ceiling, stop, incumbent/candidate roots and result>`
- Program revision: `<revision ID, old/new tracker roots, Block mapping, or not-applicable>`
- Selected and rejected paths: `<local, bounded-general, architectural owner>`
- Preserved and invalidated state: `<work/evidence maps and dependency closure>`
- Autonomy posture: `<mode, decisions made, human requests, reserved deferrals>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<bounded reads/reviews/reuse/widening>`
- Independent review: `<identity, exact revision, findings, recheck>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<safe frontier, external deferrals, resumed action>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<branch, commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---|---|
| 0 | Freeze the three-path adaptive decision-control contract | — | `not-started` |
| 1 | Correct bad implementation decisions inline and continue | 0 | `not-started` |
| 2 | Build and independently compare one bounded parallel candidate | 1 | `not-started` |
| 3 | Add configurable adaptive authority, budgets, and human-input posture | 1, 2 | `not-started` |
| 4 | Amend and apply the tracker only for structural invalidation | 0, 3 | `not-started` |
| 5 | Cut over a winning candidate, reconcile currentness, and resume | 2, 3 | `not-started` |
| 6 | Bind the same protocol to target repositories and Software Factory self-work | 4, 5 | `not-started` |
| 7 | Dogfood all decision paths and document demonstrated operation | 6 | `not-started` |

Required order:

```text
0 → 1 → 2
1 + 2 → 3
0 + 3 → 4
2 + 3 → 5
4 + 5 → 6 → 7
```

Block 4 also requires the separately accepted tracker-authoring supervision
predecessor named in its inputs; that external prerequisite does not change the
internal Block numbering or dependency graph.

## Block 0 — Freeze the three-path adaptive decision-control contract

Status: `not-started`

### Objective

Define the exact no-change, inline-correction, bounded-candidate, and structural-
amendment boundaries, plus currentness, autonomy, economy, dual-target, and
authority invariants, before changing any skill or canonical behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish a source-bound decision ladder that
  corrects bad implementation approaches at the smallest sufficient boundary.
- Potential capability loss or regression: a weak ladder could preserve a bad
  waterfall path, turn every correction into tracker churn, duplicate
  implementation authority, or let Factory preferences replace target intent.
- Protected-capability effect: preserve the mission root, target capability,
  sole writers, accepted evidence, independent review, and safe continuation.
- Architecture and operating-model effect: define inline execution as the
  primary owner, one isolated candidate lane as selective evidence gathering,
  and existing authoring supervision as the exceptional structural owner.
- Tradeoff and source evidence: explicit routing adds bounded contract work.
  The inline/candidate/structural ladder is a tracker-authoring design proposal
  selected from the direct adaptive-execution objective, current executor and
  supervision owner boundaries, and bounded-economy principles; routed advisory
  items 288 and 289 supplied comparison input but no governing requirement.

### Inputs and dependencies

- Planning baseline `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`.
- Current authoring amendment, executor capability-review, supervision
  decision/currentness, Factory-evolution, and terminal reconciliation owners.
- Planned authoring-supervision tracker as an external prerequisite for the
  later structural path, not this Block.

### Required work

- Add one concise maintained adaptive decision-control contract under the
  implementation owner. Define four dispositions: `continue-unchanged`,
  `correct-inline`, `compare-candidate`, and `amend-structure`.
- Define inline triggers for wrong owner, canonical-owner bypass, lower-power
  shortcut, unnecessary abstraction, wasteful or blind retry, scope widening,
  protected-capability regression, invalid local validation strategy, and
  another bad approach still correctable inside the Block contract.
- Define candidate triggers: concrete evidence for a materially better path,
  decision requires implementation behavior, paths can be isolated safely, and
  expected outcome/rework benefit exceeds the declared duplicate-work cost.
- Define structural triggers: objective or required capability cannot be met
  inside the current Block contract; dependencies, acceptance, or Stop must
  change; or the decision materially changes later Blocks.
- Define non-triggers: optional refactor, style preference, transient test
  failure, local implementation difficulty, unproven future reuse, broader
  scan opportunity, repeated unchanged fingerprint, and an alternative whose
  decision value does not exceed correction/exploration/currentness cost.
- Define a common decision record with mission, tracker, target-state, Block,
  capability, protected-capability, evidence, fingerprint, compared paths,
  selected disposition, affected scope, valid work, stale proof, safe frontier,
  authority mode, identities, and Stop.
- Define candidate-specific hypothesis, incumbent/candidate roots, isolation,
  resource/time ceiling, production-authority owner, focused/mapped validation
  order, comparison dimensions, independent review, cutover, and retirement.
- Define structural-packet additions: revision ID, proposed mutations,
  old-to-new map, dependency closure, accepted-history boundary, proposed
  tracker root, and resume point.
- Define exact currentness, idempotence, stale-decision rejection,
  interruption recovery, and concurrent correction/candidate/revision conflict
  behavior.
- Define the four authority modes and the full-autonomous no-human invariant at
  contract level without changing policy state yet.
- Define target-class invariants and the additional reviewer/evaluator
  separation required for Software Factory self-change.
- Add static contract tests for all boundaries.

### Scope and non-goals

- In scope: maintained semantic contract and static tests.
- Not in scope: executing a correction, candidate lane, tracker format, helper
  commands, policy mutation, target writes, or dogfood.
- Do not create a standalone controller, candidate service, schema collection,
  or ledger.

### Deliverables and recorded state

- One maintained adaptive decision-control reference owned by the executor.
- Static cross-skill contract tests and exact field/vocabulary definitions.

### Resource and economy contract

Read the current three skill contracts and two predecessor trackers once. The
unchanged runtime path defined here adds one O(1) fingerprint/currentness check
and no model/reviewer call. No provider calls, target repositories, evolution
run, report generation, broad suite, or runtime integration in this Block.

### QA and independent review

Mechanical tests guard exact fields and prohibitions. A distinct reviewer
challenges no-change versus inline, inline versus candidate, candidate versus
structural, mission-preserving clarification versus goal change, and full-
autonomous external deferral.

### Acceptance

- A sound unchanged path incurs no additional model, reviewer, candidate, or
  authoring cycle.
- A bad implementation decision inside the Block selects inline correction.
- A candidate lane requires concrete decision value plus safe isolation; a
  structural amendment requires invalidation beyond the current Block means.
- The common record is sufficient to validate, review when required, and resume
  without trusting the implementer's narrative.
- Accepted work can be remediated without rewriting its original evidence.
- Both target classes share one contract and Software Factory self-work adds
  exact separation rather than a parallel planning system.
- Full-autonomous mode has zero normal human-request path.

### Negative tests

- Reject any decision whose mission root changes or product doctrine lacks
  direct support.
- Reject optional improvement, unchanged evidence, or implementation difficulty
  as sufficient correction/candidate/structural trigger.
- Reject structural amendment when the defect can be corrected inside the
  active Block contract.
- Reject a candidate lane without a ceiling, isolation, or need for
  implementation evidence.
- Reject rewriting accepted status, commits, reviews, or completion evidence.
- Reject `full-autonomous` if an ordinary product or architecture judgment can
  route to a human approval gate.

### Completion evidence

Pending.

### Stop

Stop before changing inline execution behavior.

---

## Block 1 — Correct bad implementation decisions inline and continue

Status: `not-started`

### Objective

Make the executor stop a materially bad path that remains inside the active
Block contract, select and validate the better source-backed implementation,
record the bounded decision, and continue automatically without tracker
reauthoring or a separate supervision lifecycle.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: correct wrong owners, lower-power shortcuts,
  unnecessary abstractions, wasteful retries, and other poor local approaches
  at the moment they are supported by evidence.
- Potential capability loss or regression: over-eager correction could discard
  valid work, thrash between equivalent paths, cross the Block Stop, or convert
  ordinary execution into continuous meta-review.
- Protected-capability effect: preserve valid work, Block scope, direct mission,
  canonical owners, routine fast path, current proof, and automatic
  continuation.
- Architecture and operating-model effect: extend the existing execution brief,
  product-capability comparison, correction, validation, audit, and checkpoint
  loop; do not invoke tracker authoring.
- Tradeoff and source evidence: bounded comparison adds work only after a
  concrete bad-decision trigger. Making inline correction the normal adaptive
  path is the tracker author's proposed economical use of the existing executor
  owner, subject to the Block 0 contract review; it is not authority derived
  from a routed packet.

### Inputs and dependencies

- Block 0.
- Current implementation skill, product-capability review, execution brief,
  focused validation, Git checkpoint, Block audit, outcome closure, and tests.

### Required work

- Add the Block 0 disposition check to the active execution brief. Reuse one
  exact mission/tracker/Block/target fingerprint and return immediately for
  `continue-unchanged`.
- On an inline trigger, stop only the causal bad path at a safe boundary and
  preserve coherent code, tests, artifacts, checkpoints, and accepted evidence.
  Never discard or rewrite unrelated user work.
- Inspect the smallest affected owner and compare the local correction,
  bounded-general path supported by named current/evident consumers, and
  available architectural owner. State capability, protected-capability,
  correctness, maintainability, performance, compatibility, reversibility,
  implementation/review cost, and scope effects without an opaque score.
- Select the lowest-complexity path that fully supplies the source-backed
  capability. Explicitly reject the bad path and unsupported generalized
  alternatives.
- Implement through the existing authoritative owner, run focused validation,
  update the exact decision record, and preserve the Block's original
  objective, dependencies, acceptance, and Stop.
- Continue the remaining Block automatically. Escalate to a candidate or
  structural path only when comparison cannot be resolved without isolated
  implementation evidence or the Block contract is no longer sufficient.
- Deduplicate equivalent fingerprints and require new concrete evidence before
  reconsidering an already selected or rejected path.
- Add focused fixtures for wrong owner, lower-power shortcut, unnecessary
  abstraction, blind retry, overbroad validation, protected-capability
  regression, justified original path, unchanged repetition, and inline-to-
  structural escalation.

### Scope and non-goals

- In scope: inline trigger handling, preservation, comparison, implementation,
  focused validation, decision evidence, deduplication, and continuation.
- Not in scope: isolated candidate work, tracker mutation, new authoring thread,
  separate supervisor lifecycle, policy modes, or later-Block changes.
- Do not add a new correction service, registry, or model call on the unchanged
  path.

### Deliverables and recorded state

- Updated implementation method and bounded inline-decision record.
- Focused cross-skill behavior and static contract tests.
- Current operator-visible correction evidence inside one Block.

### Resource and economy contract

The unchanged path performs one cheap fingerprint/currentness check and zero
extra model or reviewer calls. A triggered correction reads the capability
frame and affected owner once, permits one named widening fact, and runs focused
proof first. No broad suite, authoring thread, or repeated equivalent review.

### QA and independent review

Run focused implementation contract and behavior tests. Blind paired review
checks lower-power underreach, speculative generalization, correct canonical-
owner selection, justified incumbent retention, and preservation of valid work.

### Acceptance

- A supported bad path stops before compounding and the selected correction
  remains inside the Block contract.
- Valid work and unrelated state remain intact.
- Selected and rejected alternatives have source-backed rationale and current
  focused proof.
- The executor continues automatically without tracker edit, authoring thread,
  supervisor lifecycle, human prompt, or manual Resume.
- A sound or unchanged path incurs no extra reviewer/model cycle and no decision
  churn.

### Negative tests

- Reject correction that changes the Block objective, dependencies, acceptance,
  or Stop without structural amendment.
- Reject deleting valid incumbent work or sweeping unrelated dirty-tree state.
- Reject reconsidering an unchanged fingerprint or escalating to a model for a
  sound path.
- Reject an unnecessary authoring/supervision cycle for an inline correction.

### Completion evidence

Pending.

### Stop

Stop before opening a parallel candidate lane or changing policy authority.

---

## Block 2 — Build and independently compare one bounded parallel candidate

Status: `not-started`

### Objective

Let the executor gather implementation evidence for one materially better
possible path in an isolated candidate lane, compare it with the checkpointed
incumbent, and select one authoritative path without forcing adoption or
maintaining duplicate implementations.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: compare incumbent and alternative behavior when
  read-only analysis cannot reliably establish which path produces the better
  system.
- Potential capability loss or regression: duplicate work could consume
  unbounded resources, create two authorities, contaminate current proof, or
  bias cutover toward the newer path merely because it was built.
- Protected-capability effect: preserve the incumbent checkpoint, sole
  production owner, target capability, compatibility, safe incumbent progress,
  currentness, and reversible cutover.
- Architecture and operating-model effect: add one isolated branch/worktree or
  equivalent candidate lane behind the executor's existing Git and review
  owners; do not add a parallel runtime service.
- Tradeoff and source evidence: bounded duplicate implementation cost is
  justified only by concrete expected decision value. The candidate lane and
  focused-first comparison are proposed implementation mechanisms for the
  direct better-implementation objective and remain subject to independent
  Block review; advisory item 289 does not make them mandatory authority.

### Inputs and dependencies

- Block 1.
- Current implementation skill, Git checkpoint/branch behavior,
  product-capability review, outcome closure, independent review, target owner,
  live tracker/repository/tests, and target capability frame.

### Required work

- Require the Block 0 candidate trigger and calculate expected decision value
  from material outcome uncertainty, likely rework avoided, evidence needed,
  duplicate implementation/review cost, isolation risk, and reversibility.
  Reject the lane when read-only evidence can decide or the value is not
  positive.
- Checkpoint the coherent incumbent at an exact revision/content root. Declare
  it the sole production authority and continue only dependency-safe incumbent
  work that cannot invalidate or contaminate the comparison.
- Create one isolated branch/worktree or repository-native equivalent bound to
  one hypothesis, affected scope, target capability/protected capabilities,
  expected observable effect, named owner, resource/time ceiling, Stop,
  success/failure criteria, and cleanup/retention posture.
- Implement only the candidate delta through the normal target owner. Do not
  duplicate canonical state, publish the candidate, or let both paths mutate
  production authority.
- Run candidate-focused validation first. Only after the candidate is coherent,
  compare current observable outcome, capability completeness, protected
  behavior, correctness, compatibility, performance where relevant,
  implementation and maintenance cost, reversibility, migration/cutover cost,
  and affected later work against the exact incumbent.
- Obtain automated independent review blind to any preferred disposition. It
  returns `candidate-better`, `incumbent-better`, `non-inferior-no-benefit`, or
  `inconclusive`, with exact roots and evidence.
- If the candidate is not demonstrably better, stop it and preserve only useful
  non-authoritative evidence. If better, hand one cutover proposal to Block 5;
  structural amendment remains separate and is requested only if current or
  future Block contracts must change.
- Add tests for unsafe isolation, ceiling expiry, incumbent progress conflict,
  focused failure, protected regression, candidate novelty bias, inconclusive
  comparison, winning candidate, losing candidate, and duplicate trigger.

### Scope and non-goals

- In scope: decision-value gate, incumbent checkpoint, isolated candidate,
  ceilings, focused proof, comparison, independent review, and handoff.
- Not in scope: simultaneous production use, tracker mutation, cutover, policy
  configuration, external release, or generalized experimentation.
- Do not open a lane for better style, hypothetical reuse, or a choice already
  resolved by current source evidence.

### Deliverables and recorded state

- Updated implementation method and exact candidate-lane record.
- Isolated candidate fixture, focused/comparison tests, and independent
  disposition.
- Winning-path cutover handoff or losing-path retirement evidence.

### Resource and economy contract

One candidate lane per decision. Record a hard file/change, command, time, and
review ceiling plus early Stops for hypothesis falsification or protected
regression. Run focused proof before mapped comparison. Continue only
dependency-independent incumbent work and never repeat an unchanged comparison
or rerun a producer merely to improve the narrative.

### QA and independent review

Mechanical tests verify isolation, ceilings, authority, roots, and Stops. Blind
independent review compares raw incumbent/candidate outcomes and costs before
viewing either implementer's rationale.

### Acceptance

- A lane opens only when implementation evidence is needed and expected
  decision value justifies bounded duplicate work.
- The incumbent remains checkpointed and solely authoritative throughout
  comparison.
- Candidate scope, resources, validation, comparison, and independent review
  are exact and bounded.
- A losing or inconclusive candidate stops; a winning candidate produces one
  exact cutover handoff.
- No equivalent fingerprint creates another lane or reviewer cycle.

### Negative tests

- Reject candidate creation without safe isolation, explicit hypothesis,
  ceiling, Stop, and protected-capability contract.
- Reject concurrent production authority or duplicate canonical owners.
- Reject cutover from local tests alone or because the candidate is newer.
- Reject retaining both implementations after disposition.

### Completion evidence

Pending.

### Stop

Stop before cutover, tracker amendment, or policy-mode changes.

---

## Block 3 — Add configurable adaptive authority, budgets, and human-input posture

Status: `not-started`

### Objective

Allow operators to turn adaptive decision control down or up through canonical
policy, including bounded candidate budgets and a fully autonomous mode that
resolves every ordinary engineering judgment without human input.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: configure inline authority, candidate exploration,
  structural application, resource ceilings, and human-input avoidance without
  code edits.
- Potential capability loss or regression: permissive settings could disguise
  unauthorized action or unbounded experimentation, while conservative settings
  could create human scheduling gates for ordinary corrections.
- Protected-capability effect: preserve direct authority, independent review
  where required, permission ceilings, safe continuation, resource economy, and
  minimal routine human intervention.
- Architecture and operating-model effect: extend existing supervision policy,
  `adjust`, `status`, decision, and routing owners rather than adding a separate
  adaptive controller.
- Tradeoff and source evidence: explicit modes and candidate ceilings expose
  risk and cost; the standing autonomy objective supports `full-autonomous` for
  new runs while legacy bound policy remains stable until rebound.

### Inputs and dependencies

- Blocks 1 and 2.
- Current supervision policy, permissions, mission binding, `adjust`, `status`,
  decision gate, safe-frontier, policy-history, and compatibility owners.

### Required work

- Add one versioned `adaptive_decision_mode` with exact values:
  - `fixed`: retain ordinary execution and record supported bad-path evidence,
    but do not autonomously correct, explore, cut over, or amend;
  - `recommend`: form and independently review the applicable inline,
    candidate, or structural recommendation but require external application
    authority while continuing the safe frontier;
  - `reviewed-autonomous`: apply inline corrections automatically and permit
    independently reviewed candidate cutover/low-to-moderate structural change,
    while exposing a genuinely unresolved consequential product tradeoff for
    external authority;
  - `full-autonomous`: select and apply every reversible mission-preserving
    inline correction, bounded candidate disposition/cutover, and structural
    delta within existing repository authority after its required automated
    independent review; never ask a human for ordinary engineering judgment.
- Default newly initialized policy to `full-autonomous`. Preserve exact legacy
  behavior for existing bound groups until explicit bind/adjust migration and
  retain historical policy roots.
- Add bounded candidate controls: maximum active lanes per decision and target,
  file/change ceiling, command/time ceiling, mapped-comparison ceiling,
  independent-review requirement, and automatic Stop on resource exhaustion or
  protected regression. Defaults permit one active candidate lane.
- Separate adaptive mode from target-write, skill-maintenance, external-action,
  destructive, spend, release, and production-promotion permissions. A higher
  mode cannot increase those permissions.
- In `full-autonomous`, run an input-avoidance gate before any user-facing
  question. Resolve ordinary ambiguity from sources, choose the safest
  reversible supported option, or record a bounded assumption/revisit trigger.
  A genuinely unavailable act becomes `reserved-external` with exact blocked
  subjects and safe frontier; no request is sent.
- In lower modes, make any allowed request exact and non-repetitive. Never stop
  unrelated work or treat a recommendation as applied authority.
- Record mode, disposition, candidate budget/use, decisions, human-request
  count, reserved deferrals, safe frontier, and application posture through
  existing canonical policy/events and status.
- Add migration, adjustment, invalid-combination, permission-ceiling, budget,
  full-autonomous zero-request, repeated-deferral, and legacy tests.

### Scope and non-goals

- In scope: adaptive mode, candidate budgets, migration, CLI/status,
  input-avoidance, permission ceilings, and tests.
- Not in scope: implementing a new correction, opening/cutting over a candidate,
  tracker mutation, credentials, release, or a general autonomy framework.
- Do not encode autonomy or decision value as an opaque scalar or calibrated
  probability.

### Deliverables and recorded state

- Canonical adaptive-decision mode and candidate-budget policy history.
- Updated adjustment/status/help contracts and focused tests.
- Exact full-autonomous no-human and reserved-external posture.

### Resource and economy contract

Policy validation is constant over a bounded enum and candidate fields. The
unchanged fast path remains a fingerprint check. Input avoidance reuses the
current decision packet and permits one bounded automated independent pass; it
does not start polling, timers, or broad model campaigns.

### QA and independent review

Mechanical tests cover modes, migration, hashes, permission ceilings, budgets,
zero human requests, and status. Independent review challenges ambiguous
product tradeoffs, candidate resource pressure, impossible external acts,
reversible defaults, and attempts to hide mission change behind full autonomy.

### Acceptance

- Operators can move from fixed execution through full autonomy without code
  edits.
- New runs default to `full-autonomous`; existing runs do not change behavior
  silently.
- Full autonomy resolves every in-authority inline, candidate, cutover, and
  structural choice and produces zero human requests.
- Candidate work remains within exact ceilings and one-lane production-
  authority rules.
- Adaptive mode cannot grant broader filesystem, credential, spend,
  destructive, communication, deployment, release, or promotion authority.

### Negative tests

- Reject `full-autonomous` if ordinary judgment routes to a user response window
  or Resume instruction.
- Reject any mode that bypasses required independent candidate/structural
  review.
- Reject unbounded or multiple simultaneous candidate lanes.
- Reject mode migration that rewrites prior policy history or expands unrelated
  permissions.

### Completion evidence

Pending.

### Stop

Stop before structural tracker amendment or candidate cutover.

---

## Block 4 — Amend and apply the tracker only for structural invalidation

Status: `not-started`

### Objective

When live evidence invalidates the active Block contract or materially changes
later work, form one exact structural packet, have the authoring owner produce
the minimal tracker delta, obtain independent authoring-supervision review,
apply it atomically, and resume without turning inline correction into tracker
reauthoring.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: revise and activate objective means, dependencies,
  acceptance, Stop, and later Blocks when the current program structure can no
  longer produce the governing capability reliably.
- Potential capability loss or regression: overuse could turn every local
  correction into planning churn; unchecked deltas could alter mission,
  duplicate ownership, or rewrite accepted history.
- Protected-capability effect: preserve inline fast path, mission root,
  accepted evidence, author/reviewer separation, causal Block graph, and safe
  continuation.
- Architecture and operating-model effect: extend current amendment/verifier
  owners and reuse the accepted `tracker-authoring` supervision profile only for
  structural deltas.
- Tradeoff and source evidence: structural authoring/review adds bounded latency
  but is justified only after the smaller inline and candidate paths cannot
  preserve the active Block/later program contract.

### Inputs and dependencies

- Blocks 0 and 3.
- Accepted exact revision of
  `docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`.
- Exact structural trigger, current decision/candidate evidence, authoring
  skill/template/amendment/verifier, supervisor target profile, current tracker,
  and bounded live repository evidence.

### Required work

- Require proof that inline correction cannot preserve the current Block
  objective, required work, dependencies, acceptance, negative tests, or Stop,
  or that the decision materially changes later Blocks. Reject structural
  escalation otherwise.
- Form one packet with revision ID; target class; mission, tracker, target,
  decision/candidate, and policy roots; learned facts; capability/protected-
  capability effects; selected/rejected paths; proposed mutations; old-to-new
  Block map; accepted-history boundary; affected dependency closure; preserved
  work; invalidated proof; safe frontier; authority mode; identities; Stop; and
  resume point.
- Extend the authoring method with `revise-active-program` behavior. Produce one
  append-only `Program revision history` entry and atomically update sequence,
  headings, status table, dependencies, required order, prose references,
  source map, verification matrix, terminal count, and handoff.
- Permit current/future Block add, remove, split, merge, reorder, renumber, and
  amendment. Repair accepted work through a new remediation/successor Block and
  preserve historical status/evidence.
- Extend full verification with linear checks for unique revision IDs, exact
  predecessor/current roots, complete mappings, dependency acyclicity,
  accepted-history preservation, affected scope, resume point, and status-table
  agreement. Keep unrevised tracker compatibility.
- Invoke a delta-scoped authoring thread and bind it to the accepted
  `tracker-authoring` profile. The author remains sole writer; Terra routes
  mechanically; XHigh independently inspects mission/delta/affected owners;
  Sol Max adjudicates findings without editing or implementing.
- Require review of stale-plan underreach, speculative rearchitecture, mission
  change, protected loss, fake history, Block causality, acceptance, Stops,
  resource posture, and new human dependency. Return `accepted`, `revise`, or
  `rejected` at exact packet/proposed tracker roots.
- Keep findings open until a later exact delta proves correction, and preserve
  the safe execution frontier throughout.
- After `accepted`, verify packet, proposed delta, disposition, policy mode,
  mission, tracker, target-state, and Git roots; reject stale/conflicting input.
  Let the authoring owner write and commit the exact delta atomically and record
  previous/new tracker roots, Block map, unchanged accepted-history root, and
  application commit.
- Reconcile in-flight artifacts, invalidate only mapped proof/descendants,
  retain unaffected evidence, bind the executor to the new tracker/active Block,
  and resume automatically at the first safe eligible action. Guard duplicate
  application/resume after interruption.
- Add split/merge/removal/reordering, remediation, stale/no-op/conflicting
  packet, malformed mapping, reviewer identity, self-review, interruption,
  no-finding, atomic application, selective currentness, duplicate-resume, and
  compatibility tests.

### Scope and non-goals

- In scope: structural packet, revision-aware authoring/verifier, supervised
  delta review, exact disposition, atomic application, selective currentness,
  executor rebind/resume, and focused compatibility tests.
- Not in scope: inline correction, candidate implementation/cutover, target
  implementation beyond the first resumed safe action, terminal acceptance, or
  public docs.
- Do not add a new authoring skill, role topology, revision service, or ledger.

### Deliverables and recorded state

- Revision-aware authoring instructions, amendment reference, verifier, and
  fixtures.
- Exact proposed tracker delta and independent authoring disposition.
- Atomic structural application, affected/preserved/currentness maps, and
  idempotent resume state.

### Resource and economy contract

Reuse the triggering decision/candidate, mission, tracker, and repository roots.
Review only the structural delta, affected Blocks/owners, preserved-history
boundary, and changed dependency closure. Verification remains linear in
document length plus dependency edges. Application walks only declared affected
edges and reuses unaffected proof. No broad scan, producer rerun, report
generation, or unaffected-Block review.

### QA and independent review

Mechanical tests verify structure, identities, currentness, writer separation,
history, mappings, and compatibility. Blind semantic review challenges
underreach, overreach, mission drift, false history, malformed Blocks, a sound
delta, and a local correction incorrectly escalated to structural change.

### Acceptance

- Structural authoring starts only from an exact invalidated Block/later-program
  contract and never for a correctable local implementation decision.
- The authoring owner produces a full-verifier-valid delta and the supervisor
  never writes or implements it.
- Accepted history remains intact and open Block changes have unambiguous
  mappings/dependencies.
- Disposition is bound to current packet, tracker, repository, and distinct
  reviewer identities.
- Rejected/revise findings do not pause an unaffected safe frontier or become
  self-certified resolution.
- The accepted delta applies once at exact roots, invalidates only affected
  proof, and resumes the executor automatically without a human prompt.

### Negative tests

- Reject tracker editing for a defect resolvable inside the current Block.
- Reject global renumbering that corrupts historical references or accepted
  evidence.
- Reject acceptance from author summary, green verifier, target tests, stale
  roots, or same-identity review alone.
- Reject review that widens into unrelated future Blocks or target code.
- Reject broad invalidation, duplicate application, or manual Resume after a
  successful full-autonomous structural transition.

### Completion evidence

Pending.

### Stop

Stop before candidate cutover, dual-target integration, or final dogfood.

---

## Block 5 — Cut over a winning candidate, reconcile currentness, and resume

Status: `not-started`

### Objective

Integrate one demonstrably better candidate through the normal target owner,
preserve unaffected work and proof, retire the losing path, and resume
automatically at the first safe eligible action without requiring structural
tracker amendment when the Block contract remains valid.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make a demonstrably better isolated alternative
  causally effective rather than leaving it as comparison evidence.
- Potential capability loss or regression: non-atomic cutover/application,
  dual production authority, broad invalidation, stale resume, or duplicate
  execution could lose valid work or run the wrong program.
- Protected-capability effect: preserve Git history, accepted evidence,
  unrelated work, exact dependencies, currentness, Stop boundaries, and
  automatic continuation.
- Architecture and operating-model effect: compose existing target-owner Git
  integration/cutover, canonical supervision state, and executor rebind/resume;
  structural authoring remains Block 4's independent path.
- Tradeoff and source evidence: atomic single-authority cutover and selective
  reconciliation add bookkeeping but avoid restarts, dual implementations, and
  broad proof replay.

### Inputs and dependencies

- Blocks 2 and 3.
- A current `candidate-better` disposition; tracker/target/policy/Git roots;
  authority mode; incumbent/candidate roots; preserved-work and invalidation
  maps; affected scope; and safe frontier.

### Required work

- Add one cutover operation that verifies decision/candidate, independent
  disposition, policy mode, mission, tracker, target state, incumbent/candidate,
  and Git roots; reject stale, conflicting, or inconclusive inputs.
- For a winning candidate, integrate through the normal authoritative target
  owner using a narrow merge/cherry-pick/reimplementation path appropriate to
  the repository. Preserve the candidate root and independent comparison, make
  the integrated path the sole authority, and mark the incumbent alternative
  as superseded non-authoritative history.
- If cutover would change current/future Block contracts, stop this operation
  before integration and route the exact structural effects through Block 4.
  Otherwise do not edit the tracker merely because a candidate lane existed.
- Reconcile in-flight implementation artifacts: retain coherent checkpoints,
  label superseded or exploratory work accurately, revert nothing unrelated,
  and remove no user work. An incompatible candidate remains preserved history
  unless a separately authorized recoverable cleanup is required.
- Invalidate only the implementation proof, reviews, generated artifacts,
  completion roots, and descendants actually changed by cutover or structural
  amendment. Retain unaffected exact evidence and avoid rerunning its producers.
- Recompute the dependency-safe frontier, bind the executor to the new tracker
  root and mapped active Block, and automatically continue at the first eligible
  action. Guard against duplicate resume after interruption or event replay.
- Retire losing candidate work after evidence preservation; never leave two live
  implementations or canonical owners. Do not destructively remove recoverable
  history merely for cleanliness.
- Keep the adaptive decision open until current target-state evidence proves
  its intended effect; reopen only the narrow owner on failure.
- Add atomicity, stale-root, inconclusive-candidate, dual-authority,
  cutover-with/without-structural-change, interruption, preserved-dirty-tree,
  selective-currentness, duplicate-resume, remediation-Block, and automatic-
  continuation tests.

### Scope and non-goals

- In scope: exact winning-candidate integration, losing-path retirement,
  currentness, rebind, resume, and effect linkage when the Block contract
  remains valid.
- Not in scope: determining the trigger, implementing another candidate,
  tracker amendment, release, or terminal acceptance.
- Do not restart the run or replay unaffected validation for confidence.

### Deliverables and recorded state

- Atomic single-authority candidate cutover and canonical transition record.
- Selective invalidation/preservation map and idempotent resume state.
- Focused integration and recovery tests.

### Resource and economy contract

Use exact roots and declared affected scope; do not rescan the full tracker or
repository after verified cutover unless a root conflict identifies one missing
fact. Reuse unaffected proof. One disposition produces at most one integration
and one resume.

### QA and independent review

Mechanical tests verify atomicity, hashes, sole authority, history, mappings,
selective invalidation, and idempotence. A distinct reviewer inspects the exact
integrated diff and confirms that resumed execution matches the winning path or
accepted delta without absorbing optional work.

### Acceptance

- A candidate cuts over only from a current `candidate-better` disposition; a
  losing/inconclusive lane never becomes authoritative.
- Accepted history and unrelated work remain intact.
- Only affected proof and descendants become stale or reopened.
- The executor resumes automatically on the new active Block without a human
  prompt or duplicated work.
- One target owner remains after integration and the losing path is historical.
- Later target-state evidence can accept or narrowly reopen the decision's
  causal claim.

### Negative tests

- Reject cutover when tracker, target, policy, mission, comparison, or
  disposition is stale.
- Reject cutover from `non-inferior-no-benefit` or `inconclusive`.
- Reject retaining two live implementations or simultaneous production owners.
- Reject cutover in this Block when the accepted Block contract or later graph
  must change; route that case through Block 4.
- Reject broad invalidation when the declared affected closure is narrower.
- Reject waiting for a manual Resume after a successful full-autonomous
  application.

### Completion evidence

Pending.

### Stop

Stop before adding Software Factory self-target promotion behavior or dogfood.

---

## Block 6 — Bind the same protocol to target repositories and Software Factory self-work

Status: `not-started`

### Objective

Demonstrate one shared adaptive-decision protocol—unchanged, inline, candidate,
and structural—for ordinary target repositories and Software Factory
self-improvement while enforcing the extra independence required for
self-change.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: allow both product implementation and Software
  Factory capability work to correct decisions, compare alternatives, and
  revise structure from live evidence.
- Potential capability loss or regression: special self-target authority could
  let Software Factory self-certify, while external-target coupling could write
  Factory skills or impose Factory product doctrine on the target.
- Protected-capability effect: preserve target sovereignty, target/Factory
  attribution, reviewer separation, evidence-gated skill evolution, and no
  self-promotion.
- Architecture and operating-model effect: add a target-class binding and reuse
  Factory evolution only as the existing evaluation path for self-target skill
  changes.
- Tradeoff and source evidence: one shared protocol reduces divergence; the
  self-target path pays an additional proposer/implementer/reviewer/evaluator
  separation cost supported by the accepted evolution contract.

### Inputs and dependencies

- Blocks 4 and 5.
- Current target identity/mission binding, repository ownership, three live
  skill symlinks, Factory-evolution contracts, promotion dispositions, and
  terminal capability reconciliation.

### Required work

- Bind every decision, candidate, structural packet, cutover, and application to
  `target-repository` or `software-factory`; keep trigger, inline correction,
  isolation, comparison, authoring, review, currentness, safe-frontier, and
  resume semantics identical.
- For `target-repository`, constrain inline/candidate/cutover writes to the
  target's accepted Block scope and structural writes to its tracker. Factory
  skills and global configuration remain untouched unless separately authorized
  by a different Factory capability run.
- For `software-factory`, require exact live skill sources, current repository
  revision, distinct proposer/author, implementer, independent reviewer, and
  evaluator identities, plus current baseline/candidate behavior and a Factory-
  evolution disposition. An inline decision, candidate comparison, revision
  proposal, or authoring review cannot promote its own skill change.
- Keep factory-alignment and target-product findings separately attributable
  when Software Factory is its own target.
- Reconcile terminal behavior through the existing capability-reconciliation
  owner for both target classes; process records alone do not prove the
  revision improved the target.
- Add cross-target identity, authority leak, candidate production-authority,
  same-reviewer, self-promotion, stale-skill-source, process-only, and ordinary-
  target-no-evolution tests.

### Scope and non-goals

- In scope: target-class binding, authority containment, self-change
  independence, Factory-evolution reuse, and terminal reconciliation.
- Not in scope: a new promotion system, global skill installation, external
  release, or cross-target learning index.
- Do not invoke Factory evolution for ordinary target-code revisions.

### Deliverables and recorded state

- Target-class contract and focused compatibility tests.
- Self-target evaluation handoff using existing Factory-evolution owners.
- Exact target/Factory effect reconciliation posture.

### Resource and economy contract

Resolve and hash the three live skill sources once for a self-target change.
Use one bounded baseline/candidate comparison only when skill behavior changes.
External-target inline/candidate/structural decisions make no Factory-evolution
calls. Reuse current terminal evidence and rerun only affected cases.

### QA and independent review

Mechanical tests verify identity and authority containment. Independent paired
review confirms the same program semantics across target classes and challenges
self-certification, Factory-doctrine leakage, and process-only improvement
claims.

### Acceptance

- One protocol handles unchanged, inline, candidate, structural, and resume
  behavior for both target classes.
- Ordinary target work cannot mutate Software Factory skills or invoke
  promotion.
- Software Factory self-work cannot be authored, implemented, reviewed,
  evaluated, and promoted by one identity.
- Target-product evidence governs the target even when generic Factory
  preferences disagree.
- Current behavior—not the revision record—establishes the claimed improvement.

### Negative tests

- Reject a target-repository correction, candidate, cutover, or revision that
  changes a live Software Factory skill or global configuration.
- Reject a Software Factory self-change with collapsed reviewer/evaluator
  identity or stale skill roots.
- Reject a derived Factory-evolution disposition as automatic promotion.
- Reject target success inferred from tests, tracker status, or process records
  alone.

### Completion evidence

Pending.

### Stop

Stop before final dogfood, public documentation, or broader control learning.

---

## Block 7 — Dogfood all decision paths and document demonstrated operation

Status: `not-started`

### Objective

Prove at one frozen revision that inline correction is the effective default,
parallel comparison is selective and bounded, structural amendment is
exceptional, and all paths improve target and Software Factory outcomes without
human scheduling gates, mission drift, dual authority, or self-promotion.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish current operator-visible evidence that
  Software Factory can continue unchanged, correct inline, compare/cut over a
  candidate, structurally replan, and resume autonomously in both target
  classes.
- Potential capability loss or regression: synthetic process success could
  conceal wrong behavior, oversteering, human fallback, stale revisions, or
  compatibility loss.
- Protected-capability effect: preserve static-plan fast path, exact outcome
  proof, independent review, human-input avoidance, target authority, and
  reversible self-evolution.
- Architecture and operating-model effect: exercise inline execution first,
  isolated candidate comparison selectively, and the complete three-owner
  authoring loop only for structural change; document only demonstrated
  behavior.
- Tradeoff and source evidence: a small paired dogfood matrix is sufficient for
  the first vertical proof and avoids adopting the predecessor's 30-Block
  prospective-monitoring system before this core correction capability works.

### Inputs and dependencies

- Block 6.
- Frozen candidate, focused fixtures, current three skills, accepted authoring-
  supervision capability, target-class bindings, full-autonomous policy, and
  terminal capability reconciliation.

### Required work

- Run focused changed tests, mapped suites for affected owners, all three skill
  validators, full tracker verification, and exact-candidate independent review
  after mutating review is complete.
- Dogfood an external-target inline case in which live evidence exposes a wrong
  owner or lower-power shortcut plus an unsupported generalized layer, the
  existing canonical owner supplies the better path, the correction remains
  inside the current Block, implementation continues, the operator-visible
  effect is current, and no tracker edit or later work occurs.
- Dogfood a parallel external-target case in which a materially better path
  cannot be decided read-only. Prove incumbent checkpoint/authority, safe
  isolation, hypothesis/ceiling/Stop, focused-first validation, independent
  outcome/cost/protected-capability comparison, and exactly one winning cutover
  or losing-lane retirement with no dual live implementation.
- Dogfood an exceptional structural case in which live evidence invalidates
  dependencies, acceptance, Stop, or later Blocks. Prove exact authoring-
  supervision review, minimal tracker delta, selective invalidation, and
  automatic resume.
- Dogfood a Software-Factory-self case that exercises at least inline correction
  and one candidate or structural path for a skill-method change. Distinct
  identities author when applicable, implement, review, and evaluate; no
  disposition self-promotes or mutates global configuration.
- Run a blind justified-no-correction case whose current local plan remains
  sufficient; prove only the cheap fingerprint check, with no decision record
  beyond no-op status, model/reviewer call, candidate lane, authoring handoff,
  or Block churn.
- Exercise all authority modes. In `full-autonomous`, include an ordinary
  consequential tradeoff and an unavailable external act; prove the former is
  resolved automatically, the latter is narrowly deferred, human-request count
  remains zero, and the safe frontier continues without a Resume prompt.
- Exercise stale decision/delta, interruption during candidate and after
  accepted structural review, duplicate delivery, losing/inconclusive candidate,
  rejected structural proposal with unchanged safe work, accepted-Block
  remediation, and terminal capability-gap reopening.
- Obtain a final independent review that reads the direct mission, raw paired
  cases, exact tracker revisions/diffs, current target effects, human-request
  records, compatibility evidence, and candidate diff before the completion
  narrative.
- Update `README.md`, skill references, and copyable operating examples only
  with demonstrated modes, triggers, limitations, and evidence boundaries.

### Scope and non-goals

- In scope: focused/mapped validation, paired dogfood, interruption recovery,
  exact outcome proof, independent acceptance, and accurate documentation.
- Not in scope: external release, hook installation, App Server streaming,
  detector/control libraries, broad target corpus, or additional evolution
  candidates.
- Do not claim statistical superiority, general product judgment, or unlimited
  autonomous authority from the bounded cases.

### Deliverables and recorded state

- Frozen inline, candidate, structural, no-correction, self-target, autonomy,
  and recovery evidence sets.
- Current operator-visible outputs and exact decision/cutover/revision/resume
  records.
- Accurate README/skill guidance and final tracker evidence.

### Resource and economy contract

Reuse small existing blind fixtures where possible. Use one inline target case,
one bounded candidate case, one structural case, one self-target case, one no-
correction case, and bounded authority/recovery variants. Each candidate obeys
Block 2 ceilings. Run the broad mapped suite once after all likely-mutating
review. After a finding, rerun only affected proof. No external target content,
secrets, PDF, Gmail, release, or broad benchmark campaign.

### QA and independent review

The final reviewer is distinct from the author and implementer. It must inspect
current behavior from the exact frozen revision, not infer capability from
tests, packet population, commits, tracker status, or self-evaluation.

### Acceptance

- A bad path inside the Block is corrected inline with no tracker authoring or
  separate supervision lifecycle.
- Parallel comparison occurs only when implementation evidence is necessary,
  stays within ceilings, and ends with one authoritative path.
- Structural amendment occurs only for a genuinely invalidated Block/later
  program and produces one exact reviewed delta plus automatic resume.
- A sound original plan produces near-zero adaptive overhead and no
  oversteering.
- Full-autonomous cases produce zero human requests, automatically resolve
  in-authority choices, and narrowly preserve genuinely unavailable authority.
- Accepted history, unaffected evidence, and later work remain intact.
- Existing static trackers, implementation supervision, authoring supervision,
  Factory evolution, and terminal closure remain compatible.
- Documentation distinguishes inline correction, candidate comparison,
  structural program mutability, and fixed mission authority and describes only
  the proven envelope.

### Negative tests

- Reject dogfood that tells the reviewer the intended disposition before its
  independent judgment.
- Reject completion from green tests or tracker records without current target
  behavior.
- Reject dogfood that edits a tracker for an inline correction, opens a
  candidate without decision value, or retains two live implementations.
- Reject any human prompt, waiting window, or manual Resume in the
  full-autonomous cases.
- Reject continuing into prospective monitoring or generalized control
  infrastructure after the declared proof.

### Completion evidence

Pending.

### Stop

Stop before external release, mandatory adaptive correction for unrelated runs,
prospective event/hook integration, or the broader adaptive-control platform.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Mission fixed while implementation decisions/program may change | 0 | 1–7 | 7 |
| Sound-path near-zero-overhead fast path | 0 | 1–7 | 7 |
| Source-backed inline correction and continuation | 1 | 3, 5–7 | 7 |
| Bounded isolated candidate and sole production authority | 2 | 3, 5–7 | 7 |
| Independent outcome/cost/protected-capability comparison | 2 | 5–7 | 7 |
| Configurable authority from fixed through full-autonomous | 3 | 4–7 | 7 |
| Candidate budgets and human-input avoidance | 3 | 5–7 | 7 |
| Exceptional supervised structural authoring | 4 | 5–7 | 7 |
| Revision-aware authoring and accepted-history preservation | 4 | 5–7 | 7 |
| Exact Block mapping and dependency closure | 4 | 5–7 | 7 |
| Single-authority cutover/retirement | 5 | 6–7 | 7 |
| Selective invalidation and automatic resume | 5 | 6–7 | 7 |
| Shared external-target and Software-Factory-self protocol | 6 | 7 | 7 |
| Self-change independence and no self-promotion | 6 | 7 | 7 |
| Current operator-visible outcome proof | 5 | 6–7 | 7 |
| Static-plan, legacy policy, and current-owner compatibility | 1 | 3–7 | 7 |
| No fourth skill, second ledger, or prospective-control platform | 0 | 1–7 | 7 |

## 9. Final completion definition

This tracker is complete only when every Block is accepted at exact current
revisions and frozen dogfood demonstrates that Software Factory can leave a
sound path alone, detect and correct a bad implementation decision inline,
selectively build and independently compare one isolated alternative, cut over
only when it is demonstrably better, amend the tracker only when the Block
contract or later program is invalidated, preserve mission/history/currentness,
and automatically resume to current operator-visible behavior for both target
classes.

Process evidence does not establish this outcome. A decision/candidate/revision
record, green verifier, policy mode, review disposition, commit, test suite, or
tracker status cannot substitute for current behavior at the exact target and
Software Factory revisions. The no-correction fast path, candidate ceilings and
single-authority retirement, zero human requests in `full-autonomous`, reserved-
external boundary, self-change identity separation, compatibility, and declared
Stops must also remain current.

The accepted tracker-authoring supervision capability remains a prerequisite
and independent owner only for structural amendment; inline correction and
bounded candidate comparison do not depend on or invoke it. This tracker neither
merges nor rewrites that predecessor. Broader prospective monitoring, hook
integration, event-chain learning, control libraries, generalized routing,
external release, and mandatory adaptive correction remain future work outside
this program.
