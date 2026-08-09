# Software Factory Adaptive Implementation Decision Control and Autonomous Evolution Implementation Tracker

- Tracker status: `planning-amended`
- Tracker sequence: Blocks 0–17
- Repository: `https://github.com/estill01/software-factory`
- Planning baseline: `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`
- Autonomous-evolution extension baseline: `6cdea4ff77a88f003739f9d3dbe90807683947d1`
- Control-plane prerequisite baseline: `e2b7064a7a226409518a883ecec88661469309b8`
- Governing objective: `Allow Software Factory to notice and correct a materially bad implementation decision inline while executing, selectively compare an isolated alternative when implementation evidence is needed, amend the active tracker only when live evidence invalidates the Block contract itself, and autonomously turn eligible cross-run evidence into independently evaluated, policy-governed Factory improvements, then continue without ordinary human scheduling gates.`

## 1. Purpose and intended outcome

First repair the execution control plane that keeps this program autonomous.
The governing user outcome, tracker/program, execution run, Codex task,
supervision group, and active Block are distinct identities; an internal task,
mission, group, decision, handoff, or Block boundary cannot silently become the
outcome boundary. One derived posture reducer reconciles every live decision,
transition, lifecycle, and outcome record so separate gates cannot prescribe
contradictory terminal states. Incorrect transition records remain immutable
history but can be append-only corrected, superseded, or cancelled by current
eligible authority, and a task can never be its own successor.

Software Factory skill development must also stop activating unreviewed edits
through live development symlinks. Candidate source remains in an isolated Git
worktree or branch; one exact accepted release is staged and atomically pinned
as the installed three-skill set, with verified rollback. Replays of the actual
handoff/deferral failure sequence and earlier false-closure cases guard these
invariants before the adaptive implementation and evolution program begins.

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

After that within-run control loop is demonstrated, add a coupled cross-run
Factory-evolution loop. Existing weekly-report, canonical-event, outcome,
tracker, and review evidence passes a cheap deterministic eligibility gate at
maintained reporting and terminal checkpoints. A newly eligible evidence root
may automatically enter the existing bounded learning-packet, independent
review, normal-owner candidate implementation, isolated comparison, and
policy-governed adoption path. Unchanged or ineligible evidence does nothing.
Reports remain nominators rather than authority, `factory_evolution.py` remains
a derived evidence/evaluation owner rather than a skill editor, and no
candidate can self-evaluate or self-promote.

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
  self-promotion;
- maintained reporting and terminal workflows can automatically recognize a
  newly eligible evidence root without adding a watcher, schedule, or second
  ledger;
- eligible Factory evidence can progress through the existing packet, review,
  normal-owner implementation, isolated comparison, independent evaluation,
  policy-gated adoption, rollback, and outcome-feedback owners without an
  ordinary human prompt;
- ineligible, unchanged, already-consumed, losing, inconclusive, or regressing
  evidence converges cheaply and cannot cause repeated model/reviewer cycles,
  target writes, or dual live skill implementations; and
- an integrated self-improvement dogfood case proves current installed-skill
  behavior, reversible cutover, recurrence suppression, and truthful changelog
  and human-readable reporting at the frozen terminal revision.

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
  invalidation, automatic resume, dual-target safeguards, deterministic
  evolution eligibility and recurrence control, automatic owner/evaluator
  handoffs, policy-gated adoption and rollback, outcome feedback, tests,
  documentation, exact-candidate review, persistent outcome/task/run/group/Block
  identity separation, one canonical derived posture, correctable transition
  history, and staged accepted-skill activation.
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
  three-skill system with a general planner service, or allowing evidence
  artifacts to edit or promote skills directly requires renewed direct
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
  evidence-gated Software Factory self-improvement; candidate edits must not
  change installed behavior before exact-revision acceptance and activation.
- Architecture strategy: the tracker author's proposed source-compatible design
  is to extend the executor with a default inline-correction path and a selective
  isolated candidate lane, use the existing author and supervisor owners only
  for exceptional structural amendment, and reuse Factory evolution for self-
  target changes. This is a reviewable design selection grounded in the direct
  capability objective and current repository owners, not a requirement created
  by the advisory packets. Do not add a fourth skill, planner service, mutable
  shadow tracker, or second event ledger.
- Requested capability: source-backed autonomous implementation decision
  correction, with bounded parallel comparison when necessary, structural
  replanning only when the active program contract is invalidated, and
  autonomous cross-run Factory learning that reuses those same implementation,
  comparison, review, adoption, and outcome-control boundaries.
- Proportionality: use the smallest control that can correct the actual defect:
  normal continuation for a sound path, inline correction within the Block,
  bounded candidate comparison when behavior must decide, and supervised
  tracker amendment only for structural effects.
- Tradeoffs: inline correction adds limited decision work; parallel candidates
  intentionally duplicate bounded implementation effort; tracker amendment
  adds revision/currentness cost. Exact triggers, ceilings, deduplication,
  independent cutover review, and selective invalidation keep those costs below
  the expected outcome benefit.
- Uncertainty: the current repository proves capability framing and one
  on-demand Factory evolution cycle but not inline decision correction,
  parallel candidate cutover, continuous authoring supervision, live structural
  revision, autonomous evolution eligibility, or unattended governed adoption.
  The control-plane baseline also proves a linear successor-transition record
  but not correctable topology, unified posture, or candidate/active skill
  separation; exact events `EVT-000067`–`EVT-000084` exposed that gap. This
  tracker treats accepted authoring supervision as a prerequisite only for
  the exceptional structural path and consequential evolution-authored tracker
  changes, not for normal, inline, or no-change execution.

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

verified report/event/outcome checkpoint
                              |
                cheap evolution eligibility gate
                    /                     \
          unchanged/ineligible          newly eligible
                  |                           |
             no-op record               existing packet/review
                                              |
                                normal owner implements candidate
                                              |
                                 isolated independent comparison
                                    /                     \
                              loses/revise              wins
                                  |                       |
                             retain evidence       policy-gated cutover
                                                          |
                                                observe outcome/rollback
                                                          |
                                                canonical feedback evidence
```

Authority rules:

1. The governing outcome is persistent across execution topology. The tracker
   root, execution run, Codex task, supervision group, and Block are subordinate
   identities and cannot close, replace, or narrow that outcome merely because
   one of them reaches a boundary.
2. One read-only posture reducer inventories current lifecycle, decision,
   successor-transition, mission, and outcome evidence and returns the sole
   required run posture. Specialized gates may explain their local state but
   cannot independently prescribe a conflicting terminal posture.
   The initial target/group ledger is the governing-outcome locus. Exact
   successor-transition edges in that ledger bind a bounded acyclic set of
   member target/group ledgers; their policy and event-head hashes form one
   currentness root. Missing, divergent, cyclic, or changing members produce
   `in-progress` plus an exact reconciliation action, never an inferred stop.
3. A distinct Codex task is exceptional execution topology, not a default
   continuation mechanism. Reuse the current task with a new run/group when it
   can own the work; create a successor task only when an explicit request or a
   demonstrated technical isolation requirement makes the current task
   ineligible. A task cannot be its own successor.
4. Append-only correction, supersession, cancellation, or expiry changes which
   control record is current without rewriting history or implying outcome
   completion. Only exact eligible direct authority can retire a transition
   whose premise or topology is no longer valid; routed supervision evidence
   may detect and recommend but cannot manufacture that authority.
5. Candidate skill source and installed skill authority are distinct. Editing,
   staging, testing, or reviewing a candidate changes no installed target. Only
   an exact accepted release can atomically become the one active three-skill
   set, and rollback restores one previously accepted set without dual live
   authority.
6. The mission root and materially governing product outcome remain fixed.
   Direct sources may clarify an omitted required capability, but no correction,
   candidate, or amendment can invent or reverse product intent.
7. The sound unchanged path is the default. It performs one cheap exact
   fingerprint/currentness check and continues without an extra model,
   reviewer, authoring, or candidate cycle.
8. Inline correction is the normal response to a wrong owner, lower-power
   shortcut, unnecessary abstraction, wasteful retry, protected-capability
   regression, or other bad approach that remains inside the current Block's
   objective, acceptance, dependencies, and Stop. The implementation owner may
   make that correction under the current Block without editing the tracker.
9. Inline correction preserves valid work, stops only the causal bad path,
   compares bounded alternatives, uses the normal authoritative owner,
   validates the affected result, records selected/rejected paths, and
   continues. It does not require a new authoring thread or supervision
   lifecycle.
10. A parallel candidate is permitted only when concrete evidence supports a
   materially better alternative, implementation evidence is necessary for a
   fair comparison, isolation is safe, and expected decision value exceeds the
   declared duplicate-work cost. The incumbent remains authoritative until
   cutover.
11. A candidate lane has one hypothesis, affected scope, resource/time ceiling,
   Stop, capability contract, protected-capability contract, focused-first
   validation order, and independent comparison. It never gains simultaneous
   production authority or creates a second canonical owner.
12. A winning candidate cuts over through the normal target owner. A losing or
   inconclusive candidate stops; useful evidence may remain as non-authoritative
   history, but two live implementations do not persist.
13. Structural tracker amendment is exceptional. The implementation thread may
   package it only when the Block contract itself is invalidated, dependencies,
   acceptance, or Stop must change, or the decision materially affects later
   Blocks. It cannot silently edit the tracker.
14. `author-implementation-trackers` remains the sole tracker-writing method.
   The `tracker-authoring` supervision profile independently reviews the exact
   structural delta; supervisors remain read-only and cannot implement it.
15. Accepted Blocks, commits, reviews, findings, and evidence remain historical
    truth. A defect in accepted work creates an append-only remediation or
    successor Block; it never rewrites prior acceptance.
16. Adaptive authority is policy-controlled. `full-autonomous` permits every
    reversible in-authority inline correction, candidate decision, cutover, and
    mission-preserving structural amendment after its required automated review.
    It never requires a human rubber stamp or manual Resume.
17. A genuinely unavailable credential, spend, destructive permission,
    external communication, release act, or direct goal change is recorded as
    `reserved-external`; it is not fabricated, does not stop unaffected work,
    and does not create repeated human requests.
18. `supervision_log.py` remains the public canonical supervision writer.
    Decision, candidate, cutover, and program-revision evidence compose current
    mission, checkpoint, decision, steer, resolution, and currentness owners
    rather than creating a separate operational ledger.
19. The same protocol governs `target-repository` and `software-factory`
    targets. A Software Factory self-change additionally requires distinct
    proposer/author, implementer, reviewer, and evaluator identities and the
    existing Factory-evolution promotion posture; it cannot self-certify or
    self-promote.
20. Reports, evolution packets, candidate comparisons, proposed revisions, and
    review narratives are evidence or derived artifacts. None independently
    changes the mission, tracker, target, production authority, or promotion
    state.
21. Evolution eligibility is checked only at maintained weekly-report,
    terminal-report, or explicit Factory-maintenance checkpoints. It is not a
    background watcher or schedule, and an unchanged eligibility fingerprint
    incurs no cognitive review or producer rerun.
22. A newly eligible root opens at most one bounded evolution cycle. The cycle
    reuses the existing packet/review/evaluation artifacts, normal skill owner,
    Block 6 candidate lane, and exact identity separation rather than adding an
    evolution-specific implementation channel.
23. `promote` makes a candidate eligible for a policy-governed adoption
    decision. Adoption still requires current candidate proof, permission,
    exact installed-target roots, reversible single-authority cutover, and
    terminal capability reconciliation. `advisory`, `revise`, and `reject`
    cannot cut over.
24. Every automatic evolution cycle records its eligibility root, consumed
    evidence root, identities, policy mode, outcome, cutover/rollback posture,
    and feedback event through existing canonical owners. The same root is not
    reconsidered without new outcome or source evidence.
25. Full autonomy removes ordinary human scheduling gates but does not collapse
    proposer, author, implementer, reviewer, evaluator, or adoption authority;
    it also cannot exceed existing filesystem, Git, credential, communication,
    release, deployment, or promotion permissions.

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
| Evolution eligibility, cycle identity, recurrence control, adoption evidence, and status | `supervision_log.py`, canonical events, bound policy, weekly/terminal report checkpoints | adapt without a second ledger or scheduler |
| Candidate implementation, installed-skill cutover, and rollback | existing skill owner plus the adaptive candidate/cutover path in `implement-tracker-blocks` | reuse; evolution never writes the skill |
| Human-input avoidance, dependency cuts, and bounded continuation | current author, executor, and supervision decision contracts | adapt to configurable authority |
| Public architecture and operating guidance | `README.md` and the three skill metadata owners | update after demonstrated behavior |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Current Software Factory repository | `e2b7064a7a226409518a883ecec88661469309b8` | remediate then adapt | 0–17 | Repair control-state and activation defects first, then add adaptive decision control and autonomous evidence-gated evolution without weakening accepted behavior |
| Direct diagnosis and implementation request for recurring boundary failures | current source thread `019fe023-f305-70d2-b69a-7f9565bebe86`, items following `INC-20260808-180850-C22F9D` | adopt | 0–3 | Separate persistent outcome from task/run/group/Block identity, unify posture, make stale transitions correctable, prevent self-successors, stage skill activation, and replay observed failures |
| Rejected successor-transition candidate | `e2b7064a7a226409518a883ecec88661469309b8`; rejection `EVT-000081` | remediate; preserve history | 0–1, 3 | Preserve its valid append-only transition and failure-mode work while closing self-successor, stale-transition, and conflicting-posture paths |
| Live three-skill development symlinks | `~/.codex/skills/{author-implementation-trackers,implement-tracker-blocks,supervise-tracker-runs}` resolving into this repository at amendment time | replace after acceptance | 2–3 | Separate candidate edits from the one installed accepted release and prove atomic activation/rollback |
| Accepted learning and capability-evolution MVP | tracker SHA-256 `ecc7b31ebd7bd7bc825746dded4059be2ddcc56377f4a702e1ab7781d09e07c6` | reuse | 4, 10–17 | Reuse exact evidence, identity, evaluation, and self-change boundaries; add orchestration around them rather than another evidence engine |
| Planned tracker-authoring supervision program | tracker SHA-256 `dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424` | external prerequisite for structural path | 4, 8, 11, 13, 17 | Implement and accept its Blocks before structural amendment or consequential evolution-authored tracker change is enabled; inline correction remains independent |
| Current authoring amendment method | `author-implementation-trackers/references/amendment-and-renumbering.md`, SHA-256 `28edc9682cbfe87acbd61917a67a780e8bd7b282e16588befb7799f6bbe6067a` | adapt | 4, 8 | Make exceptional live revision exact, machine-checkable, and resumable |
| Current execution capability-review method | `implement-tracker-blocks/references/product-capability-review.md`, SHA-256 `68d255c1cd7c03b61b9278e0d1a20290c7452abb661ba00ae47d15e60bfc3017` | adapt | 4–7, 10 | Correct inside the Block first; open candidate or structural paths only on exact triggers |
| Current Git checkpoint/branch behavior | `implement-tracker-blocks/SKILL.md` at planning baseline | adapt | 2, 6, 10–11, 13, 15–17 | Add accepted-release activation plus one isolated candidate lane and automated winning-path cutover without dual authority |
| Current supervision decision and continuation contracts | `supervise-tracker-runs/references/supervision-policy.md` at `e2b7064a7a226409518a883ecec88661469309b8` | remediate and adapt | 0–1, 3–4, 7–10, 12–17 | First unify derived posture and correctable topology; later add bounded correction/candidate evidence, structural disposition, evolution orchestration, and configurable no-human posture |
| Inline-first and parallel-alternative advisory | routed `codex_delegation` items 288 and 289 from source thread `019fe21e-486e-7c11-90b9-6bfbf19457c1` | advisory-only; not authority | 4–11 | Evaluate the suggested design against eligible direct sources and current owners; no requirement or permission derives solely from these packets |
| Adaptive alignment and control implementation tracker supplied as planning input | external 30-Block document | not adopted as this execution tracker | 4, 8, 11 | Reuse dual-target alignment and configurable authority; defer prospective hooks, event streaming, control libraries, and generalized runtime monitoring |
| Direct 2026-08-08 request for autonomous Factory evolution integrated with adaptive decision control | current source thread `019fe023-f305-70d2-b69a-7f9565bebe86` | adopt | 12–17 | Add configurable automatic eligibility, existing-owner execution/evaluation/adoption, feedback, and human-readable change history |

## 5. Scope, non-goals, and proportionality

### In scope

- Persistent governing-outcome identity distinct from tracker/program, run,
  Codex task, supervision group, and Block identity.
- One deterministic derived run-posture reducer across lifecycle, decision,
  successor-transition, mission, and outcome evidence.
- Append-only correction, supersession, cancellation, and bounded expiry for
  stale or invalid transition controls, including a direct valid-stop override
  and explicit rejection of self-successors.
- Candidate-versus-active separation for all three installed skills, exact
  accepted-release pinning, atomic activation, and rollback.
- Content-minimized replay fixtures for `EVT-000067`–`EVT-000084` and earlier
  false-closure cases, plus state-space/property regressions.
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
- Cheap deterministic evolution eligibility at maintained report and terminal
  checkpoints, with exact deduplication and bounded automatic-cycle admission.
- Autonomous orchestration through existing packet, authoring, implementation,
  candidate, independent evaluation, cutover, rollback, and outcome owners.
- Policy-controlled Factory adoption from disabled/recommend-only through
  reviewed full autonomy, without expanding unrelated permissions.
- Canonical outcome feedback and useful human-readable changelog/report
  projection without making either report or changelog operational authority.

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
- A new background watcher, autonomous scheduler, model router, learning
  database, self-editing evolution helper, automatic external release, or
  promotion based only on a `promote` disposition.
- A second control ledger, hosted release service, package registry, general
  workflow engine, or automatic activation of a candidate merely because tests
  pass.

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
the most general new design should win. Cross-run learning performs only a
cheap eligibility/currentness check until new evidence justifies one bounded
cycle, then reuses the same candidate and cutover controls. It does not make
continuous cognition the price of ordinary execution.

## 6. Block execution contract

1. Execute Blocks 0–17 in dependency order and audit each Block before
   advancing.
2. Repair and accept Blocks 0–3 before beginning the previously accepted
   adaptive/evolution sequence at Block 4. Candidate source changes remain
   isolated from installed skill authority until Block 2 acceptance and exact
   activation. Inline-correction and candidate foundations may then begin from
   the accepted control-plane revision. Do not enable Block 8 structural amendment until the separate
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
    After Block 12, maintained checkpoints may admit one new exact eligible root
    automatically under policy; unchanged or ineligible roots remain no-ops.
16. Finish mutating review before final mapped validation, freeze the candidate,
    obtain exact-revision independent review, and run broad mapped proof only
    once unless a mapped successor change invalidates it.
17. Stop after current operator-visible outcome proof and the declared dogfood
    cases. Do not continue into prospective monitoring or a generalized control
    platform.
18. Keep evidence synthesis, implementation, evaluation, and adoption
    identities distinct. The evolution helper validates and records derived
    artifacts but never edits or installs a skill.
19. Treat `promote` as eligibility for adoption review, not adoption itself.
    Apply only a current, permission-compatible, independently evaluated winner
    through the normal owner and one reversible cutover; otherwise retain
    non-authoritative evidence and continue.
20. Feed current post-cutover effects, failures, rollbacks, and recurrence into
    canonical events. Do not reopen the same eligibility root without a changed
    source/outcome fingerprint.

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
- Evolution posture: `<eligibility root, cycle/stage, identities, disposition, adoption or no-op>`
- Outcome feedback: `<current effect, recurrence posture, rollback or not-applicable>`
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
| 0 | Separate governing outcome identity and derive one canonical posture | — | `not-started` |
| 1 | Correct, supersede, cancel, or expire invalid execution transitions | 0 | `not-started` |
| 2 | Stage, pin, activate, and roll back one accepted three-skill release | 1 | `not-started` |
| 3 | Replay observed failures and prove control-plane convergence | 0, 1, 2 | `not-started` |
| 4 | Freeze the three-path adaptive decision-control contract | 3 | `not-started` |
| 5 | Correct bad implementation decisions inline and continue | 4 | `not-started` |
| 6 | Build and independently compare one bounded parallel candidate | 5 | `not-started` |
| 7 | Add configurable adaptive authority, budgets, and human-input posture | 5, 6 | `not-started` |
| 8 | Amend and apply the tracker only for structural invalidation | 4, 7 | `not-started` |
| 9 | Cut over a winning candidate, reconcile currentness, and resume | 6, 7 | `not-started` |
| 10 | Bind the same protocol to target repositories and Software Factory self-work | 8, 9 | `not-started` |
| 11 | Dogfood all decision paths and document demonstrated operation | 10 | `not-started` |
| 12 | Admit newly eligible Factory evidence automatically and economically | 11 | `not-started` |
| 13 | Orchestrate one bounded Factory candidate through existing owners | 12 | `not-started` |
| 14 | Independently evaluate the Factory candidate | 13 | `not-started` |
| 15 | Adopt or retire the evaluated candidate under configurable policy | 14 | `not-started` |
| 16 | Feed current outcomes back, suppress recurrence, and support rollback | 15 | `not-started` |
| 17 | Dogfood autonomous evolution and document the integrated system | 16 | `not-started` |

Required order:

```text
0 → 1 → 2
0 + 1 + 2 → 3 → 4 → 5 → 6
5 + 6 → 7
4 + 7 → 8
6 + 7 → 9
8 + 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17
```

Renumbering note: the independently accepted tracker at commit
`94c8118adca77b574b1e6ef5a1f2a5aad0aa9d91` used Blocks 0–13. This amendment
inserts new prerequisite Blocks 0–3 and maps every accepted-planning reference
mechanically as `old 0–13 → current 4–17`; no implementation or acceptance
evidence existed for the old sequence. Earlier historical evidence remains
interpretable under its original numbering. In particular, reviewed planning
commit `998dd9c9fa0c06946a5fb6ec6d9498bdfccdd0a3` used its own old mapping
`10 = evaluation plus adoption`, `11 = outcome feedback`, and
`12 = integrated dogfood`; commit `94c8118` had already split those into its
Blocks 10–13, now current Blocks 14–17.

Block 8 also requires the separately accepted tracker-authoring supervision
predecessor named in its inputs; that external prerequisite does not change the
internal Block numbering or dependency graph. Block 13 reuses that accepted
profile only when the selected Factory candidate requires a consequential
tracker amendment, and Block 17 verifies the boundary; skill-method and direct
implementation candidates continue through their ordinary owner without
manufacturing an authoring cycle.

## Block 0 — Separate governing outcome identity and derive one canonical posture

Status: `not-started`

### Objective

Make the governing requested outcome persist independently of tracker/program,
execution-run, Codex-task, supervision-group, and Block identities, and expose
one deterministic posture that reconciles every current control record.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: prevent an internal boundary or one local gate from
  prematurely stopping or closing the broader requested outcome.
- Potential capability loss or regression: a new status authority could
  duplicate the canonical ledger, conceal local evidence, or weaken legitimate
  completion and reserved-authority stops.
- Protected-capability effect: preserve append-only events, exact mission
  provenance, current observable-outcome completion, bounded decision cuts,
  and specialized gate diagnostics.
- Architecture and operating-model effect: add one read-only reducer over the
  existing canonical ledger; do not add a status service, second ledger, or new
  writer.
- Tradeoff and source evidence: one extra deterministic gate call is justified
  by the observed `decision-gate`/`successor-transition-gate` posture conflict
  and the direct request to diagnose and prevent the repeated failure family.

### Inputs and dependencies

- Direct user outcome and correction request in the current source thread.
- `supervision_log.py`, the bound mission/policy, existing decision,
  lifecycle, successor-transition, and outcome-completion records.
- Rejected candidate `e2b7064a7a226409518a883ecec88661469309b8` as preserved
  predecessor evidence, not accepted behavior.

### Required work

- Define exact separate identities for governing outcome, tracker/program,
  execution run, Codex task, supervision group, and active Block using current
  mission, policy, event, and tracker owners. Persist no duplicate copy where a
  stable existing root already owns the identity.
- Add one public read-only `control-posture-gate` to `supervision_log.py`. It
  treats the invoked initial target/group ledger as the canonical governing-
  outcome locus; inventories its current lifecycle, open decision, mission,
  transition, and observable-outcome evidence; and follows only exact active
  successor-transition edges to bounded member target/group ledgers under the
  same supervision root. It rejects ambiguous duplicate heads and returns one
  required posture, next safe action, controlling evidence, and subordinate
  diagnostics for the whole joined outcome.
- Bind every joined member by the source transition's exact successor task,
  mission root, and group identity. Require a maximum of eight members, reject
  cycles/duplicate ownership/path escape, read each policy and ledger once,
  and compute a currentness root from ordered target IDs, policy hashes, and
  append-only event-head hashes. Recheck heads after the bounded read; if a
  member changed, return an explicit retry-currentness posture instead of
  combining different snapshots.
- Define precedence from the governing outcome: verified observable completion
  or an exact current direct valid-stop may terminate; an authorized unavailable
  external fact may block only when its safe frontier is empty; every other
  unresolved implementation or topology obligation remains `in-progress`.
- Keep existing specialized gates for bounded diagnostics, but require
  executor/supervisor lifecycle decisions to consume the reducer rather than
  independently selecting a conflicting terminal posture.
- Update the three skill/policy contracts only where needed to state the
  identity and reducer boundary.

### Scope and non-goals

In scope: derived posture, identity separation, CLI/schema output, focused
compatibility migration, and current contract text. Out of scope: changing
mission content, inventing a universal workflow engine, implementing adaptive
decision control, creating tasks, or writing any target repository.

### Deliverables and recorded state

- Canonical reducer implementation and CLI help.
- Contract documentation for identities, precedence, and compatibility.
- Focused tests for all terminal and nonterminal precedence cases.

### Resource and economy contract

Read the canonical outcome-owner policy/ledger and at most seven exact joined
member policy/ledgers once each, reduce heads in one linear pass, perform one
cheap event-head stability recheck, and emit bounded content-minimized JSON. Do
not scan the supervision root for possible members, invoke a model, rerun
producers, scan repositories, or create a report. Reject inputs whose cost is
not linear in the explicitly joined ledger bytes and event count.

### QA and independent review

A reviewer distinct from the implementer must inspect the exact frozen commit,
the precedence table, existing-gate compatibility, and one live-shaped conflict
replay. Review remains read-only.

### Acceptance

- The output names all six identities without conflating or fabricating them.
- The same event history can produce only one required target posture.
- A safe-deferred decision cannot return `blocked` while an unsatisfied current
  implementation transition or other safe continuation remains.
- Verified current observable completion and an exact direct valid-stop remain
  eligible terminal outcomes.
- Existing policies and ledgers without new optional evidence remain readable.

### Negative tests

- Reject conflicting current records that cannot be reduced uniquely; do not
  choose whichever specialized gate ran last.
- Reject a routed supervisor packet as governing outcome or valid-stop
  authority.
- Do not let task, group, Block, handoff, acknowledgement, accepted tracker,
  commit, or test completion imply outcome completion.
- Do not create a second writable status/decision ledger.

### Completion evidence

Pending.

### Stop

Stop before correcting historical transition records, staging installed skills,
or implementing the adaptive decision-control Blocks.

---

## Block 1 — Correct, supersede, cancel, or expire invalid execution transitions

Status: `not-started`

### Objective

Allow a stale or incorrectly framed execution-topology transition to be retired
append-only under exact authority so it cannot trap an autonomous run or leak
ordinary scheduling back to the human.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: recover automatically when evidence shows that a
  required successor task, hold, or transition premise was wrong or is no
  longer current.
- Potential capability loss or regression: permissive retirement could erase a
  genuine unfulfilled implementation obligation or turn supervisor advice into
  mission authority.
- Protected-capability effect: preserve immutable event history, direct-source
  provenance, uncompleted outcome obligations, and exact safe-frontier rules.
- Architecture and operating-model effect: extend the existing successor-
  transition owner with terminal correction dispositions rather than adding a
  replacement state machine.
- Tradeoff and source evidence: added correction fields and validation are
  bounded to the reproduced `EVT-000067`–`EVT-000084` failure and direct user
  continuation authority.

### Inputs and dependencies

- Block 0 accepted at an exact revision.
- Existing `successor-transition-record`, decision records, operation holds,
  mission provenance, and failure-mode envelope.
- Exact rejection `EVT-000081` and subsequent direct user correction as the
  reproduced stale-transition case.

### Required work

- Preserve normal phase progression, then add append-only `corrected`,
  `superseded`, `cancelled`, and bounded `expired` terminal dispositions with an
  exact prior record, reason, authority class/source, replacement identity when
  applicable, and governing-outcome effect.
- Add topology posture for `same-task-new-run` versus `distinct-task`. Reuse the
  current task by default; a distinct task requires an explicit request or
  exact technical-isolation reason. Reject `source task == successor task`.
- Allow a current eligible direct user/system/repository/tracker source to
  cancel or correct a transition whose topology premise is invalid. Supervisory
  or `codex_delegation` evidence may trigger review but cannot supply the
  governing authority.
- Make expiry end only the operation-specific control at its declared event;
  never infer that the governing outcome expired or completed. A correction or
  supersession preserves the old record and points to the current head.
- Route transition and decision diagnostics through Block 0's reducer so all
  consumers receive the same final posture and automatic next action.
- Keep legacy linear transition records readable and preserve their exact
  evidence; migration is additive and lazy.

### Scope and non-goals

In scope: existing transition event schema/CLI, correction validation, head
selection, reducer integration, documentation, and focused tests. Out of scope:
creating a Codex task, altering the old live ledger, closing old incidents,
changing the direct mission, or implementing the later adaptive tracker.

### Deliverables and recorded state

- Append-only transition correction contract and CLI.
- Current-head derivation with historical/superseded visibility.
- Same-task default, distinct-task proof, and self-successor rejection.
- Focused replay of the stale transition without mutating the source ledger.

### Resource and economy contract

One correction appends one bounded event and recomputes current heads in a
single linear ledger pass. No model, external task operation, full suite, or
repeated human request is permitted on the normal correction path.

### QA and independent review

A distinct reviewer must inspect exact authority preservation, all terminal
dispositions, self-successor rejection, legacy compatibility, and proof that
retiring a control does not close the outcome.

### Acceptance

- An invalid distinct-task requirement can be cancelled from current direct
  authority and the reducer immediately returns autonomous same-task
  continuation.
- A replacement transition is current only after an exact append-only
  supersession link; both histories remain inspectable.
- Self-successors, missing topology rationale, unauthorized correction,
  correction chains/cycles, and premature expiry are rejected.
- A retired transition no longer blocks lifecycle posture, but the outcome
  remains open until current completion or direct valid-stop proof exists.
- The observed failure requires zero human scheduling input after the direct
  correction is already available.

### Negative tests

- Do not let a supervisor/delegation record cancel a direct-authority
  transition.
- Do not let `handoff-sent`, `target-acknowledged`, `safe-deferred`, or expiry
  become outcome completion.
- Do not accept a successor task equal to the source task or a replacement
  chain that points backward/cyclically.
- Do not rewrite or delete any prior event.

### Completion evidence

Pending.

### Stop

Stop before changing live skill symlinks, implementing adaptive correction, or
creating any successor Codex task.

---

## Block 2 — Stage, pin, activate, and roll back one accepted three-skill release

Status: `not-started`

### Objective

Ensure editing or testing Software Factory source cannot change installed Codex
behavior until one exact independently accepted three-skill release is staged
and atomically activated, with a verified rollback path.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make candidate implementation safe and reviewable
  while retaining one explicit path to update all three live skills together.
- Potential capability loss or regression: pinning could make development
  confusing, activate a partial release, break skill discovery, or lose the
  convenient ability to update installed behavior deliberately.
- Protected-capability effect: preserve the three existing skill names,
  repository ownership, user-controlled activation, rollback, and single live
  authority.
- Architecture and operating-model effect: replace implicit development-
  symlink activation with a small local release/pointer owner; do not package a
  plugin, hosted updater, registry, or daemon.
- Tradeoff and source evidence: explicit staging adds one activation step but
  closes the reproduced path by which rejected repository edits were already
  filesystem-live.

### Inputs and dependencies

- Block 1 accepted at an exact revision.
- Current three repository skill directories and their live symlink targets.
- Existing Skill Creator validators and Git exact-revision owner.

### Required work

- Add one bounded local release command that can `status`, `stage`, `activate`,
  and `rollback` the exact three skills. Stage from an immutable clean Git
  commit into a versioned local release directory and record source commit,
  per-skill content roots, validation, created time, and previous active
  release in one content-minimized manifest.
- Validate all three staged skill trees before activation. Refuse a dirty,
  missing, partial, symlink-escaping, or unreviewed source; acceptance must be
  supplied as an exact external review record/root rather than inferred from
  tests.
- Keep three stable discovery links that traverse one release-root `current`
  pointer into an immutable complete release-set directory. Activation creates,
  validates, fsyncs, and atomically renames that one pointer; it never renames
  three independent live links. On any pre-swap failure the old pointer remains,
  and recovery removes only an uncommitted temporary pointer.
- Define current-reader semantics honestly: an already-loaded task continues
  with its loaded instructions; a new resolution after the pointer swap reaches
  the new immutable set. Because the Codex host does not expose a transactional
  three-skill read, activation requires an explicit quiescent task boundary and
  post-swap reload/restart verification; it must not claim that a reader which
  begins across the swap has an atomic multi-file snapshot.
- Make rollback select only a prior validated accepted release and verify all
  resolved installed targets afterward.
- Document the explicit development workflow: edit/test in candidate source,
  freeze and review, stage accepted commit, activate, verify installed roots.
  An explicitly requested development-live mode may be documented, but must be
  visibly unsafe and cannot be the default.

### Scope and non-goals

In scope: local filesystem release staging, exact manifests, installed symlink
cutover, rollback, validators, tests, and Quick Start migration. Out of scope:
remote publishing, plugin creation, auto-update, background monitoring,
deployment beyond this local Codex skill installation, or adopting an
unreviewed candidate.

### Deliverables and recorded state

- Release activation helper and schema/help.
- Temp-directory tests for stage/status/activate/rollback and interrupted
  cutover.
- Updated installation/development documentation.
- After exact acceptance, one verified local activation record for the current
  accepted release.

### Resource and economy contract

Operate on exactly three known skill directories, hash each regular file once,
and validate each staged skill once. Use local copies and atomic renames; no
network, model, package build, broad home-directory scan, or provider call.

### QA and independent review

Review the frozen source before any live activation. The reviewer must verify
that candidate edits have no installed effect, partial activation rolls back,
the manifest cannot self-authorize acceptance, and installed paths resolve only
inside the accepted release root.

### Acceptance

- Editing the repository candidate leaves installed skill roots/content
  unchanged.
- Staging alone leaves installed behavior unchanged.
- Activation performs one `current`-pointer mutation from one complete accepted
  release set to another or none; stable discovery links are never partially
  rewritten, and status reports exact source/content roots.
- Rollback restores one prior accepted complete release.
- Missing review identity/root, dirty source, partial skill set, path escape,
  hash drift, mixed resolved roots, absent quiescent-boundary evidence,
  interrupted activation, and missing post-swap reload verification fail
  closed.

### Negative tests

- Do not infer acceptance from a commit, green tests, a promotion disposition,
  or the manifest being present.
- Do not activate directly from a mutable repository path by default.
- Do not retain one old and two new active skill links after failure.
- Do not modify unrelated skills or either installation root outside the three
  exact Software Factory names.

### Completion evidence

Pending.

### Stop

Stop before replay certification or implementation of original Block 4.

---

## Block 3 — Replay observed failures and prove control-plane convergence

Status: `not-started`

### Objective

Turn the actual false-stop histories into durable, content-minimized regression
evidence and prove that every supported control-state combination converges to
one safe posture without human scheduling leakage.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: detect recurrence of the failure family before a
  release becomes active and establish current operator-visible recovery.
- Potential capability loss or regression: fixtures could overfit one incident,
  copy sensitive narrative, or mistake test replay for live outcome proof.
- Protected-capability effect: preserve content minimization, general target
  compatibility, append-only history, and the distinction between process
  evidence and current installed behavior.
- Architecture and operating-model effect: add focused fixture/property tests
  to existing test owners, not a replay service or new operational ledger.
- Tradeoff and source evidence: bounded deterministic replay cost is warranted
  by repeated task/outcome-boundary failures and inconsistent local gates.

### Inputs and dependencies

- Blocks 0–2 accepted at exact revisions.
- Content-minimized facts from `EVT-000067`–`EVT-000084`, rejection
  `EVT-000081`, the current direct correction, and at least one prior
  partial-process/false-closure case.
- Exact staged accepted release candidate from Block 2.

### Required work

- Add immutable content-minimized replay fixtures that retain only state,
  provenance class, identity, causal transition, expected posture, and
  observable effect required by the regression.
- Replay the observed sequence through the actual public CLI/reducer: stale
  distinct-task transition, unavailable authority, safe deferral, handoff and
  acknowledgement, direct correction, same-task continuation, and eventual
  completion eligibility.
- Add deterministic state-space/property tests covering supported combinations
  of open/retired transitions, safe-frontier posture, decision disposition,
  lifecycle claim, valid-stop authority, and observable completion. Assert one
  posture, no self-successor, no subordinate-authority override, no terminal
  handoff inference, and no human request for ordinary continuation.
- Exercise staged-versus-active behavior from Block 2, including rejected
  candidate no-op, accepted activation, interrupted cutover rollback, and
  installed-root verification.
- Update `CHANGELOG.md`, `README.md`, and the three skill contracts with the
  demonstrated capability and precise limits. Do not describe Blocks 4–17 as
  implemented.
- Freeze the exact candidate, run focused tests first and mapped affected suites
  once, obtain independent exact-revision review, activate only the accepted
  release, and repeat one current installed-skill observable probe.

### Scope and non-goals

In scope: focused fixtures/tests, mapped validation, documentation/changelog,
exact review, local accepted activation, and one installed behavior probe. Out
of scope: altering the original supervision ledger, closing its incidents,
running Factory evolution, implementing adaptive decision control, background
monitoring, external release, or Gmail.

### Deliverables and recorded state

- Content-minimized replay fixtures and property/state-space tests.
- Exact candidate and review records.
- Accepted local three-skill release manifest and installed-root proof.
- Human-readable failure characterization and capability changelog entry.

### Resource and economy contract

Use one compact fixture per failure class, enumerate only the finite supported
state matrix, and run focused tests before one mapped suite. Reuse Block 0–2
validation; do not reread the live source ledger during tests, run full
unrelated suites, invoke models, or perform network/provider work except the
normal scoped Git push.

### QA and independent review

The reviewer must run the exact frozen replay/property suite independently,
inspect fixture minimization and failure-family breadth, verify activation
separation, and observe the installed exact release. Any source change after
review stales affected proof and requires a successor commit plus focused
recheck.

### Acceptance

- The exact observed sequence ends in autonomous same-task continuation rather
  than `blocked`, false completion, a fabricated task, or a user scheduling
  request.
- Every supported state combination produces one deterministic posture and
  action; contradictory heads fail closed with an actionable correction path.
- Earlier handoff/partial-process false closure remains rejected until current
  outcome proof or direct valid-stop authority exists.
- Candidate edits and rejected revisions have no installed effect; one accepted
  release activates atomically and its current behavior passes the observable
  probe.
- Changelog/report prose accurately separates canonical high-precision data,
  human-readable summaries, planned Blocks 4–17, implemented control-plane
  behavior, and remaining limitations.

### Negative tests

- Do not use fixtures that require the user's private live ledger or narrative.
- Do not accept green replay tests as proof of installed behavior without the
  exact active-release/root probe.
- Do not ask the human to create, resume, or acknowledge an internal task/run.
- Do not begin Block 4 or claim adaptive/evolution lifecycle completion.

### Completion evidence

Pending.

### Stop

Stop before original Block 4, Factory evolution, target-product writes,
external release/deployment, Gmail, or any background automation.

---

## Block 4 — Freeze the three-path adaptive decision-control contract

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

- Block 3 accepted at an exact current control-plane and installed-skill
  revision.
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

## Block 5 — Correct bad implementation decisions inline and continue

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
  owner, subject to the Block 4 contract review; it is not authority derived
  from a routed packet.

### Inputs and dependencies

- Block 4.
- Current implementation skill, product-capability review, execution brief,
  focused validation, Git checkpoint, Block audit, outcome closure, and tests.

### Required work

- Add the Block 4 disposition check to the active execution brief. Reuse one
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

## Block 6 — Build and independently compare one bounded parallel candidate

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

- Block 5.
- Current implementation skill, Git checkpoint/branch behavior,
  product-capability review, outcome closure, independent review, target owner,
  live tracker/repository/tests, and target capability frame.

### Required work

- Require the Block 4 candidate trigger and calculate expected decision value
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
  non-authoritative evidence. If better, hand one cutover proposal to Block 9;
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

## Block 7 — Add configurable adaptive authority, budgets, and human-input posture

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

- Blocks 5 and 6.
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

## Block 8 — Amend and apply the tracker only for structural invalidation

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

- Blocks 4 and 7.
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

## Block 9 — Cut over a winning candidate, reconcile currentness, and resume

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
  structural authoring remains Block 8's independent path.
- Tradeoff and source evidence: atomic single-authority cutover and selective
  reconciliation add bookkeeping but avoid restarts, dual implementations, and
  broad proof replay.

### Inputs and dependencies

- Blocks 6 and 7.
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
  before integration and route the exact structural effects through Block 8.
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
  must change; route that case through Block 8.
- Reject broad invalidation when the declared affected closure is narrower.
- Reject waiting for a manual Resume after a successful full-autonomous
  application.

### Completion evidence

Pending.

### Stop

Stop before adding Software Factory self-target promotion behavior or dogfood.

---

## Block 10 — Bind the same protocol to target repositories and Software Factory self-work

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

- Blocks 8 and 9.
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

## Block 11 — Dogfood all decision paths and document demonstrated operation

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

- Block 10.
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
Block 6 ceilings. Run the broad mapped suite once after all likely-mutating
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

Stop before automatic Factory-evolution eligibility or candidate orchestration.

---

## Block 12 — Admit newly eligible Factory evidence automatically and economically

Status: `not-started`

### Objective

Let maintained report and terminal checkpoints recognize one new evidence-bound
Factory-improvement opportunity automatically, while unchanged or unsupported
evidence converges as a cheap no-op and reports remain non-authoritative.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: move the accepted Factory-evolution workflow from
  operator-only initiation to deterministic, policy-controlled admission at
  existing checkpoints.
- Potential capability loss or regression: eager admission could create a
  cognitive-review tax on every report, treat narrative as authority, repeat
  unchanged cycles, or create a hidden background watcher.
- Protected-capability effect: preserve canonical-event authority, bounded
  source loading, verified-report provenance, no-change economy, immutable
  artifacts, and explicit Factory-only scope.
- Architecture and operating-model effect: add one eligibility/currentness
  gate to the existing `supervision_log.py` Factory-evolution owner and invoke
  it only from maintained report/terminal workflows.
- Tradeoff and source evidence: deterministic packet inspection adds bounded
  checkpoint work, but it eliminates manual initiation without adding a
  scheduler, detector framework, or continuous model loop; the direct autonomy
  request and accepted on-demand MVP support that proportional extension.

### Inputs and dependencies

- Block 11 accepted at an exact revision.
- Accepted learning/evolution packet contract and weekly `report.json` plus
  canonical `events.jsonl` sources.
- Bound adaptive mode, candidate budgets, mission, policy history, and current
  target directory.

### Required work

- Add an exact Factory-evolution eligibility contract under the existing
  supervision policy. Reuse `adaptive_decision_mode`: `fixed` records no
  automatic admission; `recommend` may form a recommendation packet but cannot
  apply; `reviewed-autonomous` and `full-autonomous` may admit one cycle within
  existing permissions and budgets.
- At weekly-report finalization, terminal-report verification, and explicit
  Factory-maintenance checkpoints only, validate explicit report/event paths,
  derive the same bounded learning packet in memory, and compute two distinct
  identities: (a) a canonical-evidence novelty key from the sorted exact
  canonical event/outcome records and their coverage, excluding report IDs,
  prose, hashes, checkpoint kind, and Factory revision; and (b) a context root
  from packet, target/mission/policy, checkpoint, and Factory revision for
  currentness and reproducibility only.
- Mark the evidence novelty key eligible only when sources verify, at least one
  report-nominated hypothesis resolves to canonical evidence not already
  covered by a consumed terminal key, no conflicting active cycle exists,
  Factory scope is explicit, and bounded cycle/review resources remain. A
  repackaged/paraphrased report, overlapping report window, different checkpoint
  kind, or unrelated Factory revision cannot create novelty. Report hypotheses
  nominate; canonical events and outcomes remain adjudicating evidence.
- Derive a safe evolution ID from the canonical-evidence novelty key plus its
  current context root, prepare the existing
  immutable packet/manifests once, and record admission through the canonical
  supervision writer. Reuse the prepared packet in later stages.
- For ineligible, disabled, duplicate, already-consumed, stale, or resource-
  exhausted roots, return an exact reason and next revisit condition without a
  model/reviewer call, artifact churn, target write, repeated event, or human
  request.
- Surface current eligibility/cycle posture in existing status and machine
  reports; add only a concise human-readable nomination/no-op summary to report
  projections. Do not make the projection an operational source.
- Add compatibility and focused tests for every gate, deterministic identity,
  unchanged recurrence, the same canonical events in a new or paraphrased
  report, overlapping report windows, changed checkpoint kind, unrelated
  Factory revision, report-only claims, conflicting active cycles, policy
  modes, path containment, interruption, and legacy policy migration.

### Scope and non-goals

- In scope: deterministic eligibility, separate canonical novelty and context
  roots, exact ID, policy binding,
  checkpoint integration, prepare reuse, canonical admission/no-op evidence,
  status, and focused tests.
- Not in scope: cognitive review generation, candidate implementation,
  evaluation, adoption, rollback, a new schedule, or a background process.
- Do not add an eligibility scoring model, learning database, second event log,
  or terminal-report input support to the weekly-only packet loader.

### Deliverables and recorded state

- Versioned eligibility/policy contract and migration.
- Maintained checkpoint admission path plus exact eligible/no-op result.
- Reused prepared packet/manifests and canonical cycle identity.

### Resource and economy contract

Run at most once per exact canonical-evidence novelty key. Stat and bounded-read inputs
before parsing, derive one packet in memory, and persist it only when eligible.
The duplicate/ineligible path performs zero model/reviewer calls and no producer
rerun. One target may have at most one active cycle; new adjudicating
event/outcome evidence beyond consumed coverage is required after terminal
disposition. A changed context root alone may require currentness revalidation
of an active cycle but cannot admit another cognitive cycle.

### QA and independent review

Mechanical tests cover roots, migration, bounds, containment, modes, and
deduplication. Independent review challenges false-positive admission,
productive-signal preservation, report authority leakage, and hidden recurring
work at the exact candidate revision.

### Acceptance

- A new supported canonical Factory evidence key is admitted automatically at a
  maintained checkpoint under reviewed/full autonomy.
- The identical canonical coverage is a cheap no-op across repackaged reports,
  overlapping windows, checkpoint kinds, and unrelated Factory revisions and
  never causes another reviewer cycle.
- Disabled, unsupported, report-only, stale, or resource-ineligible evidence
  cannot prepare or advance a cycle.
- The existing packet is byte-identical to a direct prepare from the same
  inputs, and no new scheduler, watcher, ledger, or skill writer exists.
- Legacy on-demand `prepare/finalize/evaluate/verify` behavior remains readable
  and callable.

### Negative tests

- Reject eligibility from unverified prose or an event-unbound hypothesis.
- Reject a duplicate or concurrently conflicting active cycle.
- Reject novelty inferred only from report packaging, checkpoint identity,
  overlapping coverage, or an unrelated Factory revision.
- Reject automatic admission in `fixed` mode or beyond existing permission and
  resource ceilings.
- Reject a checkpoint path that reruns cognition or writes outside the target
  supervision owner.

### Completion evidence

Pending.

### Stop

Stop before generating cognitive review or implementing a candidate.

---

## Block 13 — Orchestrate one bounded Factory candidate through existing owners

Status: `not-started`

### Objective

Advance one admitted evolution packet through independent candidate selection
and normal-owner implementation automatically, while keeping evidence,
tracker, skill, and target writers separate.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: turn eligible cross-run evidence into one coherent,
  testable Factory candidate without requiring an operator to manually connect
  the existing workflow stages.
- Potential capability loss or regression: orchestration could let the
  evolution helper edit skills, bypass tracker authoring, collapse identities,
  overgeneralize a weak signal, or start multiple candidates.
- Protected-capability effect: preserve direct-source authority, counterexample
  discipline, normal owner boundaries, candidate ceilings, accepted history,
  safe continuation, and no self-promotion.
- Architecture and operating-model effect: the supervision skill coordinates
  existing reviewer, author, executor, Git, and candidate-lane owners; the
  deterministic helper validates handoffs but does not perform model judgment
  or target edits.
- Tradeoff and source evidence: one automatic bounded handoff chain reduces
  manual scheduling while retaining the independent roles and evidence ladder
  established by the accepted MVP and Blocks 4–7.

### Inputs and dependencies

- Block 12 with one current admitted packet and cycle identity.
- Current authoring-supervision prerequisite when the candidate requires a
  consequential tracker change.
- Current live skill roots, target mission/capability frame, normal owner,
  candidate budget, and proposer/implementer/reviewer/evaluator role bindings.

### Required work

- Add a canonical cycle-stage/action read model that returns the next eligible
  action from packet, policy, identity, artifact, repository, and currentness
  state. It may return `review`, `author`, `implement`, `compare`, `evaluate`,
  `adopt`, `observe`, or a terminal no-op/revise/reject posture; it does not
  execute another owner's mutation.
- In the supervision skill workflow, automatically route an admitted packet to
  a distinct cognitive reviewer using the exact existing review schema,
  counterexample floor, selection dimensions, one experiment, and bounded
  resource/Stop contract. Consequential unresolved selection receives the
  existing independent higher-reasoning review rather than a human gate.
- Validate/finalize the review and bind the selected candidate to exactly one
  current implementation owner. Use `author-implementation-trackers` only when
  a tracker is the required normal owner; use `implement-tracker-blocks` for a
  bounded implementation program; use `supervise-tracker-runs` for its owned
  policy/evidence surfaces.
- Apply Blocks 4–6 to the Factory-as-target implementation itself: leave a
  sound owner path unchanged, correct a bad local approach inline, use one
  isolated candidate lane only when implementation evidence is necessary, and
  structurally amend only when the active program contract is invalidated.
- Checkpoint the incumbent skill/repository state, bind hypothesis/scope/
  capability/protected capabilities/ceiling/Stop and exact identities, and
  preserve one production authority. Candidate work remains isolated until a
  later adoption decision.
- Record exact owner handoffs and acknowledgements through existing canonical
  events. Reject stale roots, alias identities, duplicate action delivery,
  unacknowledged owner results, or candidate writes that bypass the owner.
- Add focused and interrupted-resume tests for direct skill-method, tracker-
  method, supervision, removal/simplification, rejected owner, inline
  correction during candidate implementation, and candidate-lane escalation.

### Scope and non-goals

- In scope: deterministic next-action state, automatic role/owner handoff,
  review finalization, one isolated implemented candidate, acknowledgement,
  interruption recovery, and tests.
- Not in scope: evaluation disposition, adoption/cutover, rollback, multiple
  simultaneous candidates, arbitrary target-product learning, or model routing
  infrastructure.
- Do not let `factory_evolution.py` edit a skill, tracker, repository, Git
  branch, or policy.

### Deliverables and recorded state

- Exact cycle-stage/action output and canonical handoff records.
- Independently authored review and one normal-owner candidate revision.
- Incumbent/candidate roots, budget use, Stop, and preserved-authority state.

### Resource and economy contract

One reviewer submission and one selected candidate per admitted root. Use one
normal owner, one isolated lane, focused proof first, and the Block 6 ceilings.
Reuse packet, review, repository inspection, and current skill roots. Do not
rerun a completed stage or widen candidate type/owner after an unchanged
fingerprint.

### QA and independent review

Mechanically verify stage order, identities, owner acknowledgement, roots,
ceilings, and isolation. A distinct reviewer challenges candidate admission,
smaller-change sufficiency, protected capabilities, and whether the selected
owner/architecture is proportional before broad validation.

### Acceptance

- An eligible cycle reaches one coherent isolated candidate through existing
  review, authoring/implementation, Git, and supervision owners automatically.
- The candidate has explicit hypothesis, scope, capability, protected
  capabilities, resource ceiling, Stop, current roots, and distinct identities.
- The evolution helper validates and records but never performs the owner
  mutation.
- Inline correction remains the normal response to a bad candidate-
  implementation approach, and structural authoring remains exceptional.
- Duplicate, stale, interrupted, or rejected handoffs cannot create a second
  candidate or production authority.

### Negative tests

- Reject proposer/reviewer/implementer identity collapse or an evaluator
  preselected as the implementation judge.
- Reject skill/tracker writes by the evolution helper or a bypass of the normal
  owner.
- Reject a second candidate for an unchanged admitted root.
- Reject implementation beyond the experiment scope, ceiling, or Stop.

### Completion evidence

Pending.

### Stop

Stop before evaluator disposition, adoption, installed-skill cutover, or
rollback.

---

## Block 14 — Independently evaluate the Factory candidate

Status: `not-started`

### Objective

Independently compare the exact incumbent and coherent current candidate and
freeze one evidence-bound disposition without performing adoption or cutover.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish a current independent comparison that can
  distinguish a demonstrably better Factory candidate from an attractive,
  inconclusive, or regressing change.
- Potential capability loss or regression: stale roots, evaluator identity
  collapse, novelty bias, process-only evidence, or incomplete exception cases
  could create an unjustified `promote` disposition.
- Protected-capability effect: preserve evaluator independence, baseline/
  candidate separation, current observable effects, compatibility,
  reversibility, protected capabilities, and all non-promotion dispositions.
- Architecture and operating-model effect: reuse the accepted Factory-
  evolution evaluator and immutable bundle as a read-only judgment owner;
  adoption remains a separate later mutation boundary.
- Tradeoff and source evidence: one independent mapped comparison adds bounded
  review cost but prevents the proposer, implementer, tests, or populated
  artifacts from certifying the candidate.

### Inputs and dependencies

- Block 13 with current incumbent/candidate roots, owner acknowledgement,
  complete review, coherent focused proof, and experiment contract.
- Current incumbent/candidate revisions, independent evaluator binding,
  experiment contract, focused proof, and terminal capability frame.

### Required work

- Automatically request a distinct evaluator only after the candidate is
  coherent. Require revision-bound baseline and candidate results for every
  positive and exception case, current observable effects, cost,
  compatibility, reversibility, protected-capability evidence, contrary
  evidence, and regression findings.
- Validate and record exactly one existing disposition. Treat `promote` as
  candidate eligibility for adoption; `advisory`, `revise`, and `reject` stop
  or return to their exact normal owner and cannot cut over.
- Freeze the exact packet, review, experiment, incumbent/candidate revisions,
  result roots, evaluation, evaluator identity, and disposition before any
  adoption decision. A later change makes only affected evaluation evidence
  stale and requires a fresh disposition.
- Record and expose the evaluated stage through existing immutable artifacts
  and status. Preserve legacy on-demand disposition semantics.
- Add tests for stale/changed roots, evaluator identity collapse, missing cases,
  process-only evidence, protected regression, improvement/non-inferiority,
  contrary evidence, interruption, and exact rebuild verification.

### Scope and non-goals

- In scope: automatic evaluation handoff, raw comparison, disposition
  validation, immutable freeze/currentness, status, and tests.
- Not in scope: adoption policy, skill/tracker/Git mutation, installed-skill
  cutover, retirement, rollback, external release, or new learning candidates.
- Do not make `promote`, a green suite, or an evaluation record sufficient proof
  of adoption or current installed behavior.

### Deliverables and recorded state

- Independent evaluation bundle and disposition.
- Frozen evaluation/currentness identity and exact adoption eligibility only.

### Resource and economy contract

One evaluator per candidate root. Reuse focused proof and run only the declared
mapped comparison after candidate coherence. A stale root rejects before
expensive proof. No cutover validation or broad rerun occurs merely to improve
a narrative.

### QA and independent review

The evaluator is distinct from proposer, author, implementer, and later
adoption executor. Exact-candidate review inspects raw incumbent/candidate
effects before reading either implementer's narrative.

### Acceptance

- Every coherent candidate receives one independent, current disposition.
- Only a complete current comparison can yield `promote`; lower dispositions
  stop or revise without target writes.
- The frozen disposition resolves to the exact incumbent/candidate roots and
  becomes stale if a mapped input changes.
- Existing on-demand evolution and legacy policy behavior remain compatible.

### Negative tests

- Reject evaluation from stale roots, same-identity review, synthetic-only
  process proof, missing cases, unsupported regression, or missing protected-
  capability proof.
- Reject any evaluation action that edits, installs, retires, or promotes a
  skill.

### Completion evidence

Pending.

### Stop

Stop before adoption policy, candidate cutover/retirement, or installed-skill
mutation.

---

## Block 15 — Adopt or retire the evaluated candidate under configurable policy

Status: `not-started`

### Objective

Apply one current, demonstrably better, authorized Factory candidate through
the normal owner or retire it, leaving exactly one authoritative installed path
without a human scheduling gate in full-autonomous mode.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make independently demonstrated Factory
  improvements effective under configurable autonomy rather than stopping at a
  proposal or `promote` artifact.
- Potential capability loss or regression: permission leakage, non-atomic
  cutover, stale evaluation, or dual installed skill paths could degrade the
  Factory while records appear successful.
- Protected-capability effect: preserve frozen independent disposition,
  current behavior, compatibility, reversibility, installed-skill identity,
  normal Git owner, single authority, and non-promotion dispositions.
- Architecture and operating-model effect: compose the adaptive candidate
  cutover, bound policy, normal skill owner, live symlink/currentness owner, and
  terminal reconciliation; do not grant the evolution artifact write power.
- Tradeoff and source evidence: reviewed autonomous adoption increases effect
  and risk together, so exact currentness, permission, rollback, and outcome
  gates remain stricter for Software Factory self-change.

### Inputs and dependencies

- Block 14 accepted with one frozen current evaluation/disposition.
- Current adaptive/evolution mode, permissions, Git state, live skill symlink
  roots, adoption-executor identity, and terminal capability frame.

### Required work

- Add an adoption gate that recomputes mission/tracker/policy/incumbent/
  candidate/evaluation/installed-skill roots, validates identity separation and
  permissions, and maps mode: `fixed` cannot adopt; `recommend` exposes a
  recommendation without application; `reviewed-autonomous` and
  `full-autonomous` apply a reversible in-authority winner after required
  review. Ordinary engineering judgment creates no human gate in full autonomy.
- Treat only a current `promote` disposition as adoption-eligible.
  `advisory`, `revise`, and `reject` record exact retirement/revision posture
  and cannot mutate the installed path.
- Cut over through the normal target/skill Git owner using Block 9 atomicity,
  make the winner the sole authoritative implementation, preserve useful losing
  history as non-authoritative, selectively invalidate affected proof, and
  update live skill symlink/current-root evidence without rewriting global
  configuration unless that path is already authorized.
- Before accepting adoption, reconcile requested capability, protected
  behavior, selected architecture, tradeoffs, current installed behavior, and
  operator-visible effects. If a gap remains, do not call the candidate adopted;
  reopen only its normal owner or roll back.
- Record adoption/recommendation/retirement through the existing canonical
  writer and expose exact stage, disposition, application authority, roots, and
  safe continuation in status.
- Add tests for every mode, stale evaluation, permission ceiling, atomic
  cutover, lower dispositions, interruption, duplicate adoption, dual
  authority, and live-symlink currentness.

### Scope and non-goals

- In scope: adoption gate, policy modes, normal-owner cutover/retirement,
  currentness reconciliation, installed authority, status, and tests.
- Not in scope: new evaluator judgment, outcome learning, prolonged monitoring,
  external release/deployment, unconfigured global installation, policy self-
  expansion, or new candidates.
- Do not make `promote`, a green suite, or an adoption record sufficient proof
  of current installed behavior.

### Deliverables and recorded state

- Exact adoption-gate result and canonical application/retirement evidence.
- One current authoritative installed path or unchanged incumbent, with
  selective invalidation and resume posture.

### Resource and economy contract

One adoption decision per frozen evaluation. A non-promote disposition stops
without cutover validation. A stale root rejects before expensive proof. Reuse
current focused/evaluation evidence, then validate only the affected installed
path. No broad rerun occurs merely to improve a narrative.

### QA and independent review

The adoption executor is distinct from proposer, author, implementer, and
evaluator. Exact-candidate review inspects the frozen disposition, permission
gate, atomic diff, live installed path, and current effects.

### Acceptance

- Only a permission-compatible, current `promote` winner can enter adoption;
  lower dispositions stop or revise without target writes.
- Reviewed/full autonomy can cut over without a human scheduling gate while
  preserving all unrelated permission ceilings.
- Cutover leaves exactly one authoritative live implementation and current
  observable capability proof; failure produces bounded rollback/reopen rather
  than false completion.
- Recommendation/fixed modes and existing on-demand disposition semantics
  remain compatible.

### Negative tests

- Reject adoption from stale evaluation, same-identity execution, unsupported
  regression, or missing current installed-capability proof.
- Reject a `promote` artifact as direct permission to edit or install a skill.
- Reject two live implementations, non-atomic cutover, or broader permission
  inferred from full autonomy.
- Reject a human approval or manual Resume for an ordinary in-authority winner
  in `full-autonomous` mode.

### Completion evidence

Pending.

### Stop

Stop before recurrence adjudication, later learning cycles, or terminal
integrated dogfood.

---

## Block 16 — Feed current outcomes back, suppress recurrence, and support rollback

Status: `not-started`

### Objective

Close each automatic evolution cycle against current effects, return its useful
outcome to canonical evidence, prevent unchanged repetition, and reverse a
regressing adoption through the normal owner.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let Software Factory learn whether an adopted or
  rejected change actually helped and use that fact in later bounded cycles.
- Potential capability loss or regression: a vague feedback loop could certify
  itself, turn reports into reinforcement authority, hide regressions, or
  permanently suppress reconsideration after materially new evidence.
- Protected-capability effect: preserve observable-outcome closure, independent
  evidence, reversible adoption, canonical-event authority, exact recurrence
  keys, and changed-evidence reconsideration.
- Architecture and operating-model effect: append bounded outcome and rollback
  events through `supervision_log.py` and project them into existing reports;
  do not add a learning database, score, or continuous monitor.
- Tradeoff and source evidence: one bounded post-disposition observation adds
  verification cost but prevents proposal/evaluation records from masquerading
  as demonstrated capability and gives later cycles causal evidence.

### Inputs and dependencies

- Block 15 terminal adoption, recommendation, retirement, revise, or reject
  posture at exact roots.
- Current installed Factory behavior, terminal capability reconciliation,
  canonical events, report projections, rollback owner, and cycle identity.

### Required work

- Add one exact outcome record for each terminal cycle with eligibility,
  packet/review/evaluation/adoption roots; selected and rejected paths; intended
  effect; current observed effect; protected regressions; resource cost;
  recurrence posture; rollback/reopen result; identities; and evidence refs.
- Require current operator-visible or independently observed behavior for
  `adopted-effective`. Process records alone support only pending, ineffective,
  regressing, retired, or inconclusive posture.
- On a supported post-cutover regression, stop affected use at the smallest
  safe boundary, invoke the normal owner to restore the preserved incumbent or
  accepted successor, reconcile live skill roots, retain the rejected history,
  and continue unaffected work automatically.
- Mark the canonical-evidence novelty key and its exact coverage consumed only
  after a terminal outcome record. Identical or overlapping canonical coverage
  remains closed regardless of report packaging, checkpoint, or unrelated
  Factory revision. New adjudicating canonical events/outcomes beyond consumed
  coverage may create a new key. A bounded `revise` disposition continues the
  same cycle through a revision lineage and cannot masquerade as new evidence.
- Feed outcome records into future learning packets as canonical evidence and
  include concise exact-cycle summaries in weekly/terminal machine and human
  reports. Reports still nominate; they cannot override outcome or reopen a
  root.
- Expose active, terminal, rolled-back, and next-eligible posture in status.
  Recover interruption idempotently and reject partial, conflicting, or
  duplicate terminal outcomes.
- Add focused tests for effective adoption, no-adoption retirement, regression
  rollback, missing observable proof, duplicate/overlap suppression, materially
  new canonical evidence, report/checkpoint/revision repackaging, revise
  lineage, report projection, interruption, and stale context roots.

### Scope and non-goals

- In scope: terminal cycle outcome, observable-effect gate, rollback/reopen,
  consumed-root recurrence control, future-packet evidence, status/report
  projection, and tests.
- Not in scope: continuous monitoring, reward scores, causal inference beyond
  exact evidence, automatic external deployment, deleting history, or opening
  a later cycle without changed evidence.
- Do not claim that absence of a recorded regression proves general benefit.

### Deliverables and recorded state

- Canonical terminal evolution outcome and consumed-evidence coverage identity.
- Current rollback/reopen or adopted-effective evidence.
- Future packet/report/status projection of exact outcomes.

### Resource and economy contract

Perform one bounded post-disposition effect check using current existing proof;
rehydrate only an affected observable when its root is stale. Reuse preserved
incumbent/candidate evidence. Duplicate roots are constant-time no-ops. Rollback
runs only focused affected validation before mapped proof justified by the
changed installed path.

### QA and independent review

Mechanical tests cover identity, terminal states, recurrence, event linkage,
rollback, and projection. Independent review challenges false effectiveness,
under-observed regressions, stale currentness, and accidental permanent
suppression of materially new evidence.

### Acceptance

- Every cycle reaches one exact terminal outcome without relying on a report or
  evaluation narrative as effect proof.
- A current effective adoption becomes canonical evidence for later cycles; a
  regression rolls back/reopens through the normal owner and remains visible.
- Identical evidence cannot repeat cognition, candidate work, or adoption;
  materially changed evidence can create one new exact cycle.
- Reports and changelog projections remain human-readable derived summaries,
  while canonical events and exact artifacts retain precision.
- Interruption or duplicate delivery cannot create contradictory terminal
  outcomes or lose the preserved incumbent.

### Negative tests

- Reject `adopted-effective` without current observable outcome evidence.
- Reject report prose or a `promote` disposition as a terminal outcome.
- Reject reopening an unchanged consumed root or suppressing a changed root.
- Reject rollback that deletes evidence, bypasses the normal owner, or leaves
  live skill symlinks on a regressing candidate.

### Completion evidence

Pending.

### Stop

Stop before broad dogfood, public capability claims, or another evolution
candidate.

---

## Block 17 — Dogfood autonomous evolution and document the integrated system

Status: `not-started`

### Objective

Demonstrate at one frozen revision that the coupled within-run and cross-run
loops autonomously improve Software Factory when justified, leave unchanged
state alone, recover from a bad candidate, and remain usable through the three
live skills and maintained human-readable documentation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish current operator-visible proof of the
  complete autonomous self-improvement path rather than only isolated contracts
  and process records.
- Potential capability loss or regression: scripted happy-path evidence could
  hide missing owner invocation, stale installed skills, repeated cognition,
  false adoption, rollback failure, or incompatibility with ordinary runs.
- Protected-capability effect: preserve all three live skill entrypoints,
  static/routine fast paths, legacy on-demand evolution, exact autonomy and
  permission boundaries, independent identities, current outcome closure, and
  useful changelog/report separation.
- Architecture and operating-model effect: exercise the integrated system
  through existing skills, helpers, policy, Git owners, and symlinks; document
  the bounded demonstrated envelope without adding deployment machinery.
- Tradeoff and source evidence: a compact paired dogfood matrix and one frozen
  broad validation provide stronger usable evidence than additional framework
  construction or an unbounded corpus.

### Inputs and dependencies

- Block 16 and all accepted Blocks 4–15 at exact revisions.
- Accepted tracker-authoring supervision prerequisite, three live skill
  symlinks, current policy/migration fixtures, isolated target repository,
  report/event fixtures, and terminal reconciliation owner.

### Required work

- Run all likely-mutating review before final validation, freeze the exact
  candidate, then run affected focused tests, all mapped skill suites, all
  three skill validators, full tracker verification, compatibility checks, and
  exact-revision independent review once.
- Resolve and record the three live skill symlinks and invoke current skill
  instructions rather than only calling internal Python functions.
- Dogfood a newly eligible Factory signal that automatically prepares one
  packet, obtains independent candidate review, uses the normal owner to build
  a bounded isolated candidate, independently evaluates it, adopts a
  demonstrably better winner in reviewed/full autonomy, reconciles the installed
  result, records effective outcome feedback, and suppresses an identical
  second checkpoint without a model/reviewer cycle or human request.
- Dogfood an ineligible or justified-no-change signal and prove near-zero added
  work, no artifacts beyond exact no-op status, no candidate, no authoring
  handoff, and no oversteering.
- Dogfood a losing/regressing candidate and prove no adoption or reversible
  rollback, one authoritative installed path, retained non-authoritative
  history, selective invalidation, and continued safe work.
- During candidate implementation, expose one tempting lower-power shortcut
  and one unsupported generalized layer; prove adaptive decision control
  selects the bounded existing owner and that structural tracker authoring is
  invoked only if the Block/program contract actually changes.
- Prove `fixed`, `recommend`, `reviewed-autonomous`, and `full-autonomous`
  postures, including zero ordinary human requests in full autonomy and narrow
  reserved-external deferral without manual Resume.
- Independently inspect current operator-visible CLI/status outputs, exact
  artifacts/events, installed skill behavior, changelog/report projections,
  and isolated target effects. Do not infer success from tests or record
  population alone.
- Update `README.md`, all affected skill/reference guidance, copyable commands,
  `CHANGELOG.md`, and tracker evidence to distinguish high-precision canonical
  data from human-consumable reports and to label planned, implemented,
  demonstrated, corrected, or retained limitations truthfully.

### Scope and non-goals

- In scope: bounded paired dogfood, live-skill access, exact current outcomes,
  compatibility, independent terminal review, README/skill/changelog/report
  guidance, and final tracker evidence.
- Not in scope: external release, Gmail action, deployment, global skill-store
  cleanup, continuous background operation, statistical claims, generalized
  target-product learning, or another capability candidate.
- Do not retain dogfood as a second live implementation or claim unlimited
  autonomous authority.

### Deliverables and recorded state

- Frozen eligible/adopted, no-op, and losing/rollback dogfood evidence sets.
- Current live-skill and isolated-target outputs with exact roots and identities.
- Accurate public guidance, changelog, human-readable report projection, and
  terminal tracker evidence.

### Resource and economy contract

Reuse one existing minimal report/event fixture and one isolated temporary Git
repository. Run one candidate lane and one evaluator per eligible case; reuse
the accepted packet and result roots. The no-op case performs zero model calls.
Run broad mapped validation once after mutating review and rerun only affected
proof after a finding. No Gmail, PDF regeneration unless mapped by an actual
projection change, release, external provider campaign, or broad benchmark.

### QA and independent review

The final reviewer is distinct from tracker author, candidate proposer,
implementer, evaluator, and adoption executor. It inspects exact raw inputs,
current outputs, skill symlinks, installed revisions, selected/rejected paths,
cost, rollback, recurrence, and human-request evidence before the completion
narrative.

### Acceptance

- One newly eligible root progresses automatically through existing owners to
  a current effective adopted capability without ordinary human input or
  self-promotion.
- An unchanged/ineligible root costs no cognitive cycle, and an identical
  consumed root cannot repeat work.
- A losing/regressing candidate cannot remain authoritative and is retired or
  rolled back with current proof.
- Adaptive decision control governs Factory-evolution implementation itself,
  including inline correction, selective candidate comparison, and exceptional
  structural replanning.
- Live skills, legacy on-demand evolution, static tracker execution, target-
  repository supervision, and existing policy histories remain compatible.
- Canonical data retains exact detail while README, reports, and changelog give
  useful human-readable summaries with truthful capability labels.
- Current operator-visible behavior, not test or process records alone,
  establishes terminal completion.

### Negative tests

- Reject terminal acceptance from green tests, populated evolution artifacts,
  `promote`, or changelog prose without current installed behavior.
- Reject a dogfood flow that bypasses a normal owner, collapses independent
  identities, prompts a human for ordinary judgment, or leaves two live paths.
- Reject broad background monitoring, external release, or another candidate
  after the terminal proof boundary.
- Reject documentation that describes planned or evaluated behavior as
  implemented/adopted without exact evidence.

### Completion evidence

Pending.

### Stop

Stop before external release, deployment, Gmail action, continuous background
operation, generalized adaptive-control infrastructure, or a second autonomous
evolution candidate.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Persistent outcome versus tracker/run/task/group/Block identity | 0 | 1–3 | 3 |
| One canonical derived posture across specialized controls | 0 | 1, 3 | 3 |
| Append-only correction/supersession/cancellation/expiry | 1 | 3 | 3 |
| Same-task default and self-successor rejection | 1 | 3 | 3 |
| Candidate-versus-active skill separation | 2 | 3 | 3 |
| Atomic accepted-release activation and rollback | 2 | 3 | 3 |
| Observed failure replay and state-space convergence | 3 | — | 3 |
| Mission fixed while implementation decisions/program may change | 4 | 5–17 | 17 |
| Sound-path near-zero-overhead fast path | 4 | 5–17 | 17 |
| Source-backed inline correction and continuation | 5 | 7, 9–11 | 11 |
| Bounded isolated candidate and sole production authority | 6 | 7, 9–11 | 11 |
| Independent outcome/cost/protected-capability comparison | 6 | 9–11 | 11 |
| Configurable authority from fixed through full-autonomous | 7 | 8–11 | 11 |
| Candidate budgets and human-input avoidance | 7 | 9–11 | 11 |
| Exceptional supervised structural authoring | 8 | 9–11 | 11 |
| Revision-aware authoring and accepted-history preservation | 8 | 9–11 | 11 |
| Exact Block mapping and dependency closure | 8 | 9–11 | 11 |
| Single-authority cutover/retirement | 9 | 10–11 | 11 |
| Selective invalidation and automatic resume | 9 | 10–11 | 11 |
| Shared external-target and Software-Factory-self protocol | 10 | 11 | 11 |
| Self-change independence and no self-promotion | 10 | 11 | 11 |
| Current operator-visible outcome proof | 9 | 10–11 | 11 |
| Static-plan, legacy policy, and current-owner compatibility | 5 | 7–11 | 11 |
| No fourth skill, second ledger, or prospective-control platform | 4 | 5–11 | 11 |
| Deterministic checkpoint eligibility and exact no-op deduplication | 12 | 13–17 | 17 |
| Reports nominate while canonical evidence adjudicates | 12 | 13–17 | 17 |
| Existing-owner autonomous candidate orchestration | 13 | 14–17 | 17 |
| Adaptive control governs Factory-evolution implementation | 13 | 14–17 | 17 |
| Independent evaluation and frozen disposition | 14 | 15–17 | 17 |
| Policy-gated adoption and single installed authority | 15 | 16–17 | 17 |
| Reversible cutover and current installed behavior | 15 | 16–17 | 17 |
| Current outcome feedback, recurrence suppression, and rollback | 16 | 17 | 17 |
| Canonical data versus human-readable report/changelog separation | 16 | 17 | 17 |
| Live-skill integrated operator-visible proof | 17 | — | 17 |

## 9. Final completion definition

This tracker is complete only when every Block is accepted at exact current
revisions and frozen dogfood demonstrates both coupled loops: Software Factory
first keeps one persistent governing outcome across distinct tracker, run,
task, supervision-group, and Block identities; reduces all live control evidence
to one posture; corrects or retires invalid transitions append-only; rejects a
self-successor; and keeps candidate source inert until an exact accepted
three-skill release is atomically activated and rollback-proven. The observed
failure replays must show autonomous continuation without false completion,
conflicting terminal gates, fabricated task identity, or human scheduling
leakage. With that foundation current, Software Factory
can leave a sound path alone, detect and correct a bad implementation decision
inline, selectively build and independently compare one isolated alternative,
cut over only when it is demonstrably better, amend the tracker only when the
Block contract or later program is invalidated, preserve
mission/history/currentness, and automatically resume to current operator-
visible behavior for both target classes; and a newly eligible cross-run
Factory evidence root can progress automatically through the existing learning,
normal-owner implementation, independent evaluation, policy-gated adoption,
outcome, rollback, and recurrence owners while unchanged evidence does nothing.

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
merges nor rewrites that predecessor. Factory evolution remains a derived
evidence/evaluation workflow and never becomes a direct skill writer or
self-promotion authority. Human-readable reports and `CHANGELOG.md` summarize
exact canonical data without replacing it. Broader prospective monitoring,
hook integration, event-chain learning, control libraries, generalized routing,
external release, deployment, and mandatory adaptive correction remain future
work outside this program.
