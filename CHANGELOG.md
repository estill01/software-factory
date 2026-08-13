# Software Factory changelog

This is the human-consumable history of significant Software Factory
capabilities, operating contracts, authority boundaries, compatibility changes,
and implementation programs. It is intentionally more descriptive than a list
of commit subjects, but it is not a second operational ledger.

High-precision evidence remains in Git history, implementation-tracker
completion evidence, canonical supervision events, verified `report.json`
artifacts, tests, and exact candidate reviews. Changelog entries summarize those
sources and link or cite exact revisions when that materially improves
traceability.

## Maintenance contract

Update this file at the coherent checkpoint where any of the following becomes
planned, implemented, adopted, materially corrected, deprecated, or removed:

- a reusable Software Factory capability or workflow;
- operator-visible behavior or a public skill contract;
- an authority, autonomy, supervision, evidence, or outcome-closure boundary;
- a compatibility, migration, installation, or runtime requirement; or
- a significant implementation tracker that changes the intended product
  direction.

Every entry must distinguish `Proposed`, `Planned`, `Implemented`,
`Demonstrated`, `Corrected`, and `Removed` truthfully. A planned tracker is not
implemented behavior; a passing experiment or `promote` disposition is not
automatic adoption; and process evidence is not an operator-visible outcome.

Include the capability effect, important boundaries or compatibility posture,
and the strongest useful evidence reference. Do not add every test fixture,
review-only successor, evidence-only checkpoint, typo, or internal refactor
unless it changes how a material result should be understood. Tracker authors
should include a changelog update in the terminal documentation Block whenever
the completed program materially changes Software Factory.

## Unreleased

### Implemented

- **Exact-acceptance-triggered release orchestration.** The supervision owner
  now consumes one reviewer-signed canonical acceptance for the exact
  clean source HEAD/tree, invokes only the flagless `skill_release.py promote`
  owner in a fixed canonical-account/Python/Git environment, revalidates its
  returned active release and three installed roots
  through live status, and retains one deduplicated result. A durable
  requirement binds the prior live identity before the effect so interruption
  recovery cannot lose or repeat the one activation. When independent review
  advances before any effect, an immutable successor requirement may bind the
  newer acceptance only after exact prior release, installed-root,
  verification-root, and history currentness is revalidated. Missing, stale,
  changed-policy, changed-byte, unverified or caller-asserted review,
  divergent-result, and
  caller-selected release identity cases reject before they can become
  canonical promotion evidence.

- **Provenance-bound authority across internal task routing.** A direct-user
  implementation instruction no longer loses its actionable authority merely
  because Software Factory carries it to the configured target through
  `codex_delegation`. The canonical delegation envelope binds the original
  task/turn/item and exact bytes, current target mission and policy, the current
  pending mission-activation source through fresh range admission, and the
  owner-produced target-action route result
  and projection. The mission retains the route owner's canonical action
  digest while provenance separately retains the complete originating direct
  instruction's raw UTF-8 byte count and SHA-256. The dedicated owner derives
  the action identity from the current mission and accepts the source only as a
  separate canonical-base64 input; no caller reconstructs action text from a
  retained digest, and neither identity substitutes for the other. Mission identity alone
  remains nonauthorizing; an independent base-or-Max acceptance precedes the
  existing authority event, receipt, and range-owner consumption. The
  recipient starts the full-tracker range automatically without a same-thread
  repetition or manual Resume.
  Unbound internal packets, changed route/action/source evidence, supervisor
  language, and scope expansion remain nonauthorizing.

- **Automated, self-checking local skill promotion.** Ordinary updates to the
  three Software Factory skills now use one `promote` command over an exact
  clean commit. The release owner runs the four repository-owned test suites,
  validates and seals every skill, records deterministic assurance, atomically
  swaps one `current` pointer, verifies the installed roots in a fresh process,
  and restores the prior pointer automatically on failure. The prior signed
  review and quiescent-permit path remains optional for a deliberately required
  separation-of-duties boundary instead of blocking routine local maintenance.

- **Current-authority reconciliation for stale decision deferrals.** A later
  canonical direct-authority correction of the exact successor-topology premise
  now retires the matching safe-deferral posture in the shared governing-outcome
  reducer immediately. The relation is mission-, source-, state-, lineage-, and
  currentness-bound: the transition genesis must predate and be cited by the
  decision-ready record; every later decision phase preserves that frozen
  identity; and exactly one cited lineage may match. Unrelated or ambiguous
  later evidence remains ineligible. A new
  append-only `corrected` decision phase preserves the explicit history while
  the target continues without user scheduling or a manual Resume. The public
  replay and focused decision/control regressions cover automatic convergence,
  exact correction recording, and mismatched-source/state, uncited-later, and
  ambiguous-lineage rejection.

- **Reviewed three-skill releases with one-pointer activation.** Mutable
  repository work no longer changes installed Codex behavior by default. A
  bounded local release owner rebuilds exactly three skills from a clean Git
  commit, runs content-pinned validators, requires a separately signed exact
  review, stages an immutable complete set, and accepts only a current signed
  quiescent permit from a distinct external operator-ledger head. Bootstrap
  migrated the prior content-identical direct links; activation changed one
  `current` pointer and fresh-process verification accepted release
  `b7269cc0d71f-eb1269660b3e` with exact author, implementation, and supervision
  roots. The sealed baseline `dba8274f3f06-f17ebeafde01` remains the eligible
  rollback target. Already-loaded tasks keep their loaded instructions; new
  resolutions see the active set.
- **Replay-certified control-posture convergence.** The repeated early-return
  history is now represented by one content-minimized immutable fixture rather
  than private narrative. The observed transition sequence replays through the
  public control gate from stale distinct-task requirement, unavailable
  authority and safe deferral, through handoff/acknowledgement, current direct
  correction, autonomous same-task continuation, and exact observable
  completion. A 60-case state matrix covers absent/open/retired transitions,
  safe/nonblocking/blocking decisions, current/stale completion, and authorized/
  unauthorized stop claims. Every case returns one deterministic posture;
  invalid terminal claims reconcile and ordinary continuation never asks the
  human to schedule it. This demonstrates the Blocks 0–3 control plane only;
  adaptive implementation and autonomous evolution remain later work.
- **Adaptive implementation decision semantics.** The implementation owner now
  maintains one exact four-disposition contract: reuse a sound unchanged path,
  correct a bad approach inline inside the active Block, compare one isolated
  bounded candidate only when behavior must decide, or package an exceptional
  structural amendment when the Block contract or later graph is invalidated.
  The contract fixes common evidence/currentness fields, candidate ceilings and
  ownership, structural history preservation, four autonomy modes, and one
  protocol for target repositories and Software Factory self-work with stricter
  self-change role separation. This is the accepted Block 4 semantic boundary;
  it does not yet activate correction, candidate execution, tracker mutation,
  policy changes, or autonomous evolution owned by later Blocks. The reviewed
  contract is installed in active release `96974ea056a9-bd814c616698` with
  verification root
  `e1f16091e78fd438423ceef7bc830773570b44cc686e744907375a7b0d293f19`.
- **Autonomous inline correction during implementation.** The active
  implementation skill now detects a source-backed wrong owner, lower-power
  shortcut, unnecessary abstraction, wasteful retry, invalid validation, or
  protected-capability regression that remains inside the current Block;
  preserves valid work; compares the local, bounded-general, and architectural
  owner paths; implements the lowest-complexity complete path; retains exact
  staged decision/currentness evidence; and continues the Block automatically.
  A sound or equivalent decision takes the O(1) no-review fast path. Fresh
  installed-skill dogfood selected an existing naming owner over both duplicated
  logic and an unsupported registry, produced the current observable filename,
  preserved the later adapter, and passed independent retained-evidence review
  plus 25 adversarial probes. Active release:
  `75a3f3e4f39b-3adc588d1dbb`; accepted source:
  `75a3f3e4f39bcdaaa809951e9c15db91af3d7de2`.
- **Selective bounded candidate comparison.** The implementation owner can now
  checkpoint a sound incumbent, freeze one pre-run hypothesis/workload/runtime/
  materiality contract, and build exactly one safely isolated candidate when
  read-only evidence cannot decide a materially better path. Focused proof
  precedes mapped comparison; raw size, semantic, API, timing, cost,
  compatibility, protected-capability, and restoration evidence is retained
  for a distinct reviewer. A materially better result emits only a non-mutating
  Block 9 handoff, while losing, inconclusive, failed, stale, cancelled,
  over-ceiling, and late-review lanes retire without acquiring production
  authority. The retained exercise demonstrates a bounded 88-byte improvement
  under criteria frozen at pre-run revision
  `c8b92ac48920b86587a1e39f5f16702de8b65554`; the accepted candidate remains
  isolated and non-authoritative behind one immutable Block 9 handoff. Exact
  repeat evidence now resolves the externally signed accepted head and reuses
  that handoff without another lane, producer, or reviewer cycle. The method is
  installed in active release `3d984d9094c3-c689901b7413` with verification
  root `67703c07d630e9b10e9d47d55bc74484c3ec79c224524096bd9d67280cabc409`.

- **Successor-transition continuity and structured failure-mode records.** A
  requested implementation that must cross into a distinct task now remains an
  open append-only transition through `required`, task creation, isolated
  mission/group binding, handoff, target acknowledgement, and first-Block work
  start. `successor-transition-gate` prohibits treating the source as stopped
  or complete before current `work-started` evidence, while preserving the
  exact tracker, mission, Block range, authority, and successor identities.
  Routed supervisor provenance cannot manufacture the direct authority needed
  to create a user-owned task. Incident records can also carry a reusable
  failure-mode envelope describing mechanism, trigger, effect, detection,
  correction, recurrence invariant, and any human-scheduling leak in the same
  canonical ledger. The initiating event is
  `INC-20260808-180850-C22F9D` / `EVT-000067`; focused regression coverage is in
  `SuccessorTransitionContractTests`.

### Corrected

- **Critical unauthorized early-return recurrence.** The root failure is
  recorded as unauthorized requested-range contraction followed by false
  terminalization at an internal Block or procedural boundary; later routed
  authority precedence was contributory, not causal. A bare or unbounded
  `implement-tracker-blocks` request now freezes the complete current tracker in
  canonical policy history, survives prerequisite insertion and renumbering,
  and must pass the same range/outcome gate at every Block Stop, terminal
  lifecycle write, and final response. Exact one-Block requests remain bounded,
  but incidental Block mentions cannot contract full-tracker intent. New direct
  authority can narrow a range only after a separately ingested, hash-chained
  owner event binds verified task/item provenance and content hash; the range
  helper cannot mint that authority from caller strings. Concrete recurrence
  fixtures include this run and task
  `019fb18f-3d03-7ca0-9fe9-68353f0405ce`; behavioral coverage is in
  `ImplementationRangeControlTests`.

### Planned

- **Adaptive implementation decision control and autonomous Factory
  evolution.** An eighteen-Block program plans a
  near-zero-overhead unchanged path, inline correction of bad implementation
  decisions, selective isolated candidate comparison, exceptional supervised
  tracker amendment, configurable full autonomy, single-authority cutover, and
  shared operation for target repositories and Software Factory self-work. It
  then couples the accepted on-demand evolution workflow to maintained report
  and terminal checkpoints through deterministic eligibility, existing-owner
  candidate implementation, independent evaluation, policy-gated reversible
  adoption, outcome feedback, and recurrence suppression. Reports remain
  nominators rather than authority; the evolution helper never edits or
  promotes a skill. This is planning, not implemented functionality. Initial plan:
  `765c32bd15a52f8eb0f0bb48f07217d0851ebac5`; provenance-corrected successor:
  `851bc1aa5150eaa4de7fc5346c45abf892002a1f`; independently accepted frozen
  plan: `94c8118adca77b574b1e6ef5a1f2a5aad0aa9d91`, blob
  `9e6b6d1d03369c84ff9ca48c2df35dcac79e2f64`, SHA-256
  `426a7a60074c464640dfc3657b87bb082cdf7a2b4408c3245e2d5a29b02960fd`; tracker:
  [`docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md`](docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md).
- **Pre-implementation tracker-authoring supervision.** A five-Block program
  plans independent, repository-grounded challenge of capability selection,
  architecture/owner reuse, Block decomposition, acceptance evidence, and
  implementation readiness before implementation begins. This remains planned,
  not implemented. Planning commit:
  `a01417376b458325b6554ab6007d2a7d145a785d`; tracker:
  [`docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`](docs/software-factory-tracker-authoring-supervision-implementation-tracker.md).

### Documentation

- **Changelog established.** Added this project-level capability history and
  the maintenance contract above. Run-specific reports and machine-readable
  evidence remain the precise underlying sources; this file is their durable
  human-oriented summary.

## 2026-08-08

### Implemented and demonstrated

- **Evidence-grounded Factory evolution MVP.** Software Factory can build a
  deterministic learning packet from explicit verified weekly `report.json`
  and canonical `events.jsonl` sources; validate bounded observations, lessons,
  counterexamples, meta-patterns, capability candidates, selection dimensions,
  and experiments; independently compare baseline and candidate behavior; and
  record `promote`, `advisory`, `revise`, or `reject`. The workflow is on-demand
  and derived: reports nominate hypotheses, canonical evidence adjudicates,
  the evolution command never edits skills or targets, and a disposition does
  not automatically adopt or deploy a candidate. Accepted tracker evidence:
  `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`; accepted implementation candidate:
  `363596ce10c4c3a39ead387bc9db493c12128c8b`; tracker:
  [`docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md`](docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md).
- **Target-product capability framing during tracker authoring.** New
  full-profile trackers reconstruct the direct product capability, protected
  behavior, architecture strategy, proportionality, tradeoffs, and uncertainty
  before consequential Block decomposition. The verifier rejects structural
  contradictions and preserves an inherited core-profile compatibility path.
  Accepted candidate: `c777c9c9b97787ad49d6dace328ca5b5041961b7`;
  acceptance evidence: `9e0062b8f76d6f2a0aba7636e81e17ab7e6bdeb8`.
- **Bounded product-capability review during Block execution.** Consequential
  Blocks compare a local path, bounded-general path, and available architectural
  owner; protect canonical behavior and composability; reject lower-power
  underreach and speculative generalization; and retain the routine fast path.
  Accepted candidate: `17a7571873cff82b4190db1ffe75216cac75937f`;
  acceptance evidence: `3bed4013d48f2e36418f4a0b50c0d657d9fcd424`.
- **Terminal capability reconciliation.** Outcome completion now validates a
  bounded semantic reconciliation of requested capability, protected behavior,
  architecture owner, tradeoffs, current behavior, operator-visible effects,
  exact evidence, source revision, and independent reviewer identity. A
  verified posture requires zero supported gaps; tests, commits, reports, and
  process records cannot substitute for current behavior. Accepted candidate:
  `363596ce10c4c3a39ead387bc9db493c12128c8b`; acceptance evidence:
  `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`.

### Corrected

- **Critical full-tracker continuation and early-return control.** Recorded the
  recurring root failure as unauthorized requested-range contraction followed
  by false terminalization at an internal Block/procedural boundary
  (`FM-UNAUTHORIZED-EARLY-RETURN`), with routed-precedence shadowing retained as
  a contributing mechanism. Added a canonical, policy-history-anchored direct
  range binding, dynamic full-tracker amendment coverage, reviewed direct-user-
  only contraction, dependency-safe continuation, reducer-derived terminal
  currentness, and fail-closed lifecycle rules across tracker authoring,
  implementation, and supervision. Regression fixtures include this Software
  Factory run and task `019fb18f-3d03-7ca0-9fe9-68353f0405ce`, where a bare
  skill invocation was incorrectly reduced to Block 0. Hardened the successor
  correction against polarity-blind range parsing, caller-selected replacement
  trackers, fabricated distinct-task topology, canonical range/mission drift,
  event-ledger symlink escape, policy/event history truncation, and correction
  evidence attached before a terminal disposition. The final hardening adds a
  status-independent tracker structural root, exact distinct-task request-byte
  proof, canonical range-history provenance, lazy legacy-root migration, and an
  externally HMAC-bound append-only owner-root history that detects coordinated
  policy/event/root replacement, pins its latest external sequence/head against
  authentic-prefix rollback, and cannot be disabled by policy rewrite.
  A surviving external head now rejects key loss as tampering instead of being
  overwritten through legacy migration, and direct-task topology accepts only
  unconditional exact source semantics rather than feasibility-dependent or
  contradictory prose.
  Frozen transition identity now survives status/evidence-only tracker
  amendments while structural drift still fails closed.

- **Adaptive tracker provenance.** Corrected the planned adaptive-decision
  tracker so routed `codex_delegation` advice remains advisory rather than being
  represented as direct product authority. Direct requirements are bound to the
  eligible user thread and hash-bound repository/tracker sources. Successor:
  `851bc1aa5150eaa4de7fc5346c45abf892002a1f`; corrected tracker blob:
  `1e60d8312f77cd6880b3818fd8418e3087137fa3`.

## 2026-08-03 to 2026-08-04

### Implemented

- **Evidence-backed supervision reports.** Added deterministic weekly
  supervision metrics, bounded cognitive review, machine-readable report state,
  executive-readable Markdown/PDF projections, and report-density controls.
  Reports remain derived views rather than operational authority.
- **Observable outcome closure and terminal supervision.** Added explicit
  reconciliation of requested deliverables and current effects, terminal report
  evidence, lifecycle/shutdown proof, and Gmail ownership boundaries. Green
  tests or terminal process state alone no longer establish completion.

## 2026-08-01 to 2026-08-02

### Implemented

- **Autonomous continuation around bounded decisions.** Added dependency cuts,
  maximal safe-frontier continuation, bounded independent resolution attempts,
  fail-closed blocking gates, and automatic consumption of resolved handoffs so
  ordinary Block boundaries or preferences do not become human scheduling
  gates.
- **Independent supervision and corrective recovery hardening.** Added strict
  cross-thread action routing, role-refresh gates, exact mission provenance,
  producer-output preservation, stable test invocation envelopes, incident
  lifecycle reconciliation, and current-run correction before reusable skill
  maintenance.

## Earlier foundation

- **Three-skill Software Factory.** Established independently usable tracker
  authoring, bounded Block implementation, and independent tracker-run
  supervision skills with Git durability, canonical event/incident state,
  verification, correction, and reporting owners. Exact granular history begins
  with repository commit `c1ab52c` and remains available in Git.
