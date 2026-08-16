# Software Factory Systemic Supervision Recovery Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–6
- Repository: `/Users/ethanstillman/code/software_factory`
- Governing objective: Direct-user requirement that a Software Factory inconsistency or defect which blocks or stops an implementation run be detected, owned, corrected, activated, and used to resume that same run automatically, while reusable prevention remains distinct from current-run recovery.

## 1. Purpose and intended outcome

Make recovery from Software Factory-owned control-plane defects a closed-loop
product capability. A supervisor that observes a target implementation stop must
distinguish a target defect from a Factory defect, preserve the target's valid
work and in-progress mission, route the Factory repair through its existing
review and release owners, restore canonical range and tracker currentness, and
wake the same implementation task exactly once at its next safe frontier.

Completion means:

- A maintained regression of the August 13, 2026 incident proves that an
  incompatible current helper, stale or absent canonical range binding, or
  Factory-owned supervision defect opens one owned recovery lifecycle instead of
  turning the target stop into a user handoff.
- The repair candidate is based on the current accepted Software Factory source,
  receives exact independent review, activates through the existing release
  owner, and refreshes compatible roles only at a current safe boundary.
- Canonical full-tracker range and accepted tracker state reconcile through their
  existing owners without replaying accepted proof or inferring completion from
  process evidence.
- The same target task resumes exactly once, advances from its preserved safe
  frontier, and produces an effectiveness record; unchanged watcher state causes
  no repeated reads, no-change commentary, or duplicate wake.

### Mission frame

- Primary outcome: Software Factory failures no longer strand otherwise
  authorized implementation; the Factory restores its own control plane and the
  original target continues automatically.
- Observable completion: one exact incident-derived regression and one isolated
  end-to-end dogfood bind detection, containment, current-source repair,
  acceptance, local activation, range currentness, tracker reconciliation,
  single wake, target advancement, and later effectiveness to exact owner
  records.
- Ordinary effect classes needed: Software Factory source correction, focused
  validation, exact review, local release promotion, role refresh, canonical
  range admission or amendment, tracker-owner reconciliation, routed target wake,
  and effectiveness reporting.
- Hard direct authority or safety boundaries: the direct mission remains the
  governing target authority; `scripts/skill_release.py` remains the only release
  pointer writer; current implementation-range owners remain the only range
  authority; the target implementation owner remains the only target-repository
  writer; supervisors cannot self-accept, alter target permissions, infer Block
  completion, or request a manual Resume for an ordinary Factory-owned defect.
- Material goal alteration or reversal: allowing supervision to edit a target,
  promoting without exact acceptance, replacing the release/range/tracker owners,
  making user intervention the default, or broadening the repair allowlist
  requires renewed direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker changes the Factory operating model from
  detect-and-stop to detect-contain-repair-resume for defects in its own control
  plane, while preserving the target's authority and exact acceptance gates.
- Direct product sources: `README.md`; `supervise-tracker-runs/SKILL.md`;
  `supervise-tracker-runs/references/supervision-policy.md`;
  `implement-tracker-blocks/SKILL.md`;
  `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md`;
  current accepted release source `73d54524ffa3264bbb245bd59875a9f765af5af7`;
  content-minimized incident evidence `EVT-001488`, `EVT-001513`,
  `EVT-001523`, `EVT-001544`, `EVT-001575`, `EVT-001602`, and
  `EVT-001683` under target `019fb18f-3d03-7ca0-9fe9-68353f0405ce`.
- Product thesis and intended effect: independent supervision must not merely
  report that its own machinery is incompatible; it must use the existing
  maintenance, review, release, range, tracker, and routing owners to restore
  operability and continue the original outcome.
- Protected capabilities: exact direct mission and full-tracker scope;
  independent review and single-writer boundaries; immutable accepted/rejected
  evidence; target-repository isolation; release rollback; range
  non-contraction; dependency-safe continuation; no manual Resume; and separate
  closure of current-run recovery and reusable prevention.
- Architecture strategy: add one derived recovery state machine to the existing
  supervision event/policy owner and compose existing repair, release, refresh,
  range, tracker, routing, and effectiveness owners. Add no second watcher,
  release service, range ledger, tracker authority, scheduler, or target writer.
- Requested capability: automatic, evidence-bound recovery and resumption when a
  Factory-owned supervision or implementation-control defect blocks a run.
- Proportionality: policy prose alone cannot close a multi-owner recovery after
  the observed incident, while a generic self-healing service would duplicate
  authority and permit speculative repair. One explicit derived lifecycle plus
  existing owners is the smallest complete seam.
- Tradeoffs: automatic recovery adds strict cause, source-currentness,
  acceptance, range, reconciliation, safe-boundary, deduplication, and
  effectiveness gates; an unresolved or out-of-authority repair remains open
  while unaffected target work continues.
- Uncertainty: the direct sources do not authorize arbitrary code repair,
  cross-repository mutation, automatic release of unaccepted commits, or generic
  support for every historical tracker/receipt format.

## 2. Target architecture and authority boundaries

```text
changed target state
  -> existing watcher and semantic reviewer
  -> current incident head and cause/owner classification
  -> Factory recovery lifecycle in the existing event ledger
  -> existing Sol Max plan and allowlisted fix executor
  -> exact current-source candidate and focused proof
  -> independent exact-revision acceptance
  -> existing software-factory-release-promote orchestration
  -> existing stable-channel role-refresh at a safe boundary
  -> existing implementation-range authority and gate
  -> target-owned tracker reconciliation from preserved evidence
  -> existing thread-route-gate and one target wake
  -> target advancement and existing effectiveness review
```

The recovery lifecycle is a derived coordination record, never a replacement
authority. The incident owner establishes that a Factory-owned defect exists;
the fix executor may change only the currently authorized Software Factory
surface; the exact reviewer accepts or rejects the frozen candidate; the release
owner alone activates or rolls back; the range owner alone binds full-tracker
intent; the target owner alone reconciles tracker status and writes the target;
and the watcher observes later effectiveness. A failure at one boundary retains
the last valid state and continues every dependency-independent target frontier.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Changed-state observation, incidents, routes, policy, and effectiveness | `supervise-tracker-runs/scripts/supervision_log.py` and `supervise-tracker-runs/references/supervision-policy.md` | adapt with one derived recovery lifecycle |
| Semantic cause and repair review | Existing Terra → Sol XHigh → Sol Max supervision roles | reuse unchanged |
| Allowlisted Software Factory repair | Existing Sol Max plan plus Sol XHigh fix executor under `apply-allowlisted-skill-maintenance-with-review` | remediate routing/current-source invariants only |
| Exact accepted local promotion | `software-factory-release-promote` and `scripts/skill_release.py promote/rollback` | reuse unchanged |
| Running-role adoption | `thread-route-gate` purpose `role-refresh` and stable `current` paths | reuse unchanged |
| Canonical tracker scope/currentness | `implementation-range-authority-receipt`, `implementation-range-bind`, `implementation-range-admit`, `implementation-range-amend`, and `implementation-range-gate` | reuse; repair compatibility only through the current owner |
| Tracker status and completion evidence | `author-implementation-trackers` and `implement-tracker-blocks` against the target tracker | reuse; target owner applies reconciliation |
| Same-target wake | `thread-route-gate` with exact target task and required action | reuse with recovery deduplication |
| Release and recovery health | Release-owner status/rollback plus existing supervision effectiveness records | reuse unchanged |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Current active compatibility release source | `73d54524ffa3264bbb245bd59875a9f765af5af7` | reuse | 0 | preserve legacy direct-authority compatibility and current installed behavior |
| Automatic accepted-release and currentness source | `809fbbaf2aa1b6307a3645497ee7e532d8e788cb`, contained by current source | reuse | 0, 3, 5 | reuse accepted promotion/refresh/rollback/currentness behavior without replaying proof |
| Shared predecessor of the current release and orchestration lines | `80e4ec1d44bf981a2eec0ba7dddd5345171efb9e` | reuse | 0 | establish ancestry without rewriting either successor history |
| Automatic release and supervisor refresh tracker | `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md` at `731668eee9f3d47b968950b8965e1d8263beb74b` | reuse | 0, 3, 5 | reuse its completed accepted promotion/refresh/rollback/currentness evidence; do not replay it or infer a new outcome |
| Patent Studio supervision incident | target `019fb18f-3d03-7ca0-9fe9-68353f0405ce`, source `msg_019fe560-cc38-7f41-991a-a1d8b0a5a209`, events listed in the product frame | adapt | 0–6 | de-projectize only control-plane states and expected recovery; exclude patent content and paths |
| Unchanged-outcome corrective-cycle failure mode | `FM-PROCESS-PASS-OUTCOME-UNCHANGED`, content-minimized | adapt | 1, 2, 4, 6 | distinguish process concordance from effectiveness before another expensive same-hypothesis effect; exclude target content and wording |
| Preserved accepted and rejected target proof | Exact commits and event records bound by the incident | reuse | 4, 6 | rehydrate currentness; never replay accepted proof or infer acceptance |

## 5. Scope, non-goals, and proportionality

### In scope

- Detect and classify a Software Factory-owned control-plane blockage.
- Preserve the original target mission, valid evidence, in-progress posture, and
  dependency-safe frontier while the Factory repair proceeds.
- Repair only through the current allowlisted Software Factory owner, exact
  current source, focused proof, and independent review.
- Activate through the existing release owner and refresh compatible roles at a
  safe boundary.
- Restore canonical range/currentness, route tracker reconciliation to the target
  owner, wake the same target once, and assess later effectiveness.
- Suppress unchanged owner polling, no-change commentary, duplicate repair lanes,
  duplicate promotion, and duplicate target wakes.

### Out of scope

- A generic autonomous code-repair service, new daemon, new scheduler, second
  watcher, second release owner, second range ledger, or new tracker authority.
- Supervisor edits to target repositories, patents, tracker status, product
  permissions, release pointers, or protected project data.
- Replaying accepted target tests or reviews merely to reconstruct state.
- Guessing historical compatibility, accepting a patched/unreleased helper,
  force-pushing, or treating remote publication as local activation.
- Fixing target-local implementation defects under the Factory recovery lane.

### Proportionality

A finding authorizes the narrowest correction of its concrete invariant. Reuse
existing owners and omit optional hardening that has no reproduced, in-scope
failure tied to this tracker's objective. The observed incident justifies one
coordination lifecycle and exact regressions; it does not justify generalized
self-healing infrastructure.

## 6. Block execution contract

1. Execute Blocks 0–6 in dependency order.
2. Re-read the selected Block and inspect the live repository before editing.
3. Preserve unrelated, rejected, accepted, and in-flight work; never rewrite an
   incident or candidate to make a later state appear current.
4. Keep current-run recovery and reusable prevention as separately evidenced
   lanes. This tracker owns prevention; it must not claim that its completion
   restored a target unless the same target has distinct resumed evidence.
5. Implement through the narrowest existing owner. A derived recovery record may
   coordinate exact owner outputs but may not accept caller booleans, hashes,
   postures, source revisions, release IDs, Block status, or target identity.
6. Preserve the target's required posture as `in-progress` for an ordinary
   Factory-owned defect. `manual_resume_required` and `human_input_required`
   remain false unless the direct mission reaches an existing reserved boundary.
7. Read the active release/source once on a genuine owner change. Do not poll an
   unchanged owner or emit repeated no-change commentary while waiting.
8. Before candidate validation, prove the repair is based on the current accepted
   source. If the active source changed, freeze the old candidate as diagnostic,
   port only the accepted delta to the current source, and rerun only affected
   proof.
9. Run focused validation and permitted exact review before mapped or expensive
   validation. Before another expensive consequential effect cycle for the same
   open outcome, bind through the existing incident/effectiveness owner the
   primary observable outcome, accepted baseline disposition and material-
   finding-set fingerprint, treatment-hypothesis identity, and predeclared
   effectiveness criterion. Tests, audits, hashes, reviews, commits, releases,
   and process compliance remain supporting proof; none establishes that the
   motivating outcome improved. Reuse exact accepted proof and widen only when
   the changed-path owner requires it.
10. Local activation and remote publication are independent. Publication failure
    becomes durability-pending and does not block an exact accepted local
    release, range repair, role refresh, or target resumption.
11. Reconcile accepted target Blocks only from exact preserved owner evidence and
    current tracker bytes. The target owner writes status; the range gate verifies
    it. Never infer completion from a release, route, test count, narrative, or
    range binding alone.
12. Route at most one wake for one recovery identity. After an outcome-
    effectiveness hold, wake only for a materially different treatment, an
    attempted violation of the hold, or new independent outcome evidence; an
    ordinary process, release, range, tracker, or target revision is not enough.
13. An operation-specific hold states its exact operation or Block scope,
    content-minimized identity, expiry event, successor posture, and
    `carry-forward: false`. It cannot silently survive a current release, range,
    or target revision.
14. Record exact current evidence, audit and accept one Block before advancing,
    and stop at the declared boundary rather than searching for optional
    hardening.
15. This tracker does not duplicate unfinished work in the automatic-release and
    supervisor-refresh tracker. A missing accepted promotion, refresh, or rollback
    capability holds only the dependent recovery composition, cites that exact
    predecessor Block, and preserves every independent safe frontier.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<incident/release/range/target root>`
- Inputs: `<paths, IDs, versions, hashes>`
- Outputs: `<recovery state, release, range, route, effectiveness records>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix>`
- Resource posture: `<reads, routes, owner calls, proof reuse, widening>`
- Independent review: `<exact-revision evidence>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<target posture, safe frontier, wake, outcome>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze the incident regression and current integration baseline | — | `in-progress` |
| 1 | Classify Factory-owned blockages and preserve the target mission | 0 | `not-started` |
| 2 | Route a bounded repair against the current accepted source | 1 | `not-started` |
| 3 | Compose accepted repair, activation, range, and tracker restoration | 2 | `not-started` |
| 4 | Resume the same target exactly once and assess effectiveness | 3 | `not-started` |
| 5 | Freeze, review, integrate, and promote the complete successor | 4 | `not-started` |
| 6 | Dogfood the released lifecycle and close only from observed outcome | 5 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6`

## Block 0 — Freeze the incident regression and current integration baseline

Status: `in-progress`

### Objective

Establish one exact current Software Factory baseline and one content-minimized
incident regression without rewriting either source lineage or target evidence.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block freezes source identity,
  incident facts, owner assignments, and exclusions; it adds no runtime recovery
  behavior.

### Inputs and dependencies

- Historical source revisions `80e4ec1d44bf981a2eec0ba7dddd5345171efb9e`,
  `eaa75be5e739915b181819afede8a35a6e654155`, and
  `f1256468034d323894149ce7e9dc0a770270a6f4`; current accepted source
  `73d54524ffa3264bbb245bd59875a9f765af5af7`; and accepted currentness fix
  `809fbbaf2aa1b6307a3645497ee7e532d8e788cb`.
- The existing automatic-release tracker and exact incident records listed in
  the prior-work map.

### Required work

- Verify by ancestry that the current accepted release contains the automatic-
  promotion/currentness line; preserve both histories and reject a source-only
  copy that drops accepted ancestry.
- Freeze active release ID, source commit, manifest roots, installed roots,
  current branch/tree, and existing tracker status before implementation.
- Translate the incident into a content-minimized fixture containing only owner,
  state transition, revision, range/tracker-currentness, route, and expected
  posture fields. Exclude patent content, project paths, prompts, and findings.
- Map every required effect to an existing owner and document any exact missing
  coordination field before adding it.

### Scope and non-goals

- In scope: integration identity, incident fixture, owner map, and exact baseline.
- Not in scope: repair orchestration, live role refresh, or target wake.
- New machinery is permitted only when the objective cannot be met through an
  existing owner and the acceptance-critical need is stated here.

### Deliverables and recorded state

- Clean integration baseline and one de-projectized incident fixture with an
  exact source-adaptation receipt.

### Resource and economy contract

Use bounded Git ancestry/blob checks and the cited incident records. Do not scan
unrelated supervision groups, repositories, patents, or full event histories.

### QA and independent review

Mechanical identity and fixture-minimization proof; no semantic acceptance until
Block 5.

### Acceptance

- One clean baseline contains both required source lineages, one current release
  identity, no target content, and an exact owner/disposition map.

### Negative tests

- Reject missing ancestry, changed accepted/rejected bytes, copied patent data,
  caller-supplied current-release identity, and a fixture that treats a routed
  stop message as canonical cause evidence.

### Completion evidence

Pending.

### Stop

Stop before changing supervisor classification or target posture.

---

## Block 1 — Classify Factory-owned blockages and preserve the target mission

Status: `not-started`

### Objective

Derive one authoritative cause/owner disposition for a stopped implementation
and keep the original mission active when the blockage belongs to the Factory.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: a Factory-owned incompatibility opens autonomous
  recovery instead of a terminal/user-owned stop.
- Potential capability loss or regression: overbroad classification could hide a
  real target defect or exceed supervision authority.
- Protected-capability effect: preserves direct target scope, current incident
  evidence, dependency-safe work, truthful failure posture, and reserved user
  boundaries.
- Architecture and operating-model effect: adds a derived recovery disposition
  to the existing incident/control-posture owner; no second classifier or ledger.
- Tradeoff and source evidence: fail closed on ambiguous ownership while keeping
  unaffected work active; the incident events demonstrate that a stop alone did
  not identify the responsible owner.

### Inputs and dependencies

- Block 0 baseline, incident fixture, current policy, current target state, and
  current canonical incident head.

### Required work

- Derive exactly `target-owned`, `software-factory-owned`, `mixed`, or
  `reserved-external` from current owner evidence; split mixed subjects rather
  than assigning the whole run to one lane.
- For `software-factory-owned`, record the exact failed owner/contract/revision,
  containment boundary, preserved target frontier, recovery trigger, and
  required target posture in the existing event ledger.
- When consecutive accepted outcome records retain the same disposition and
  material-finding-set fingerprint, compare the next candidate's treatment-
  hypothesis identity before authorizing its consequential effects. If the
  hypothesis is unchanged, record `outcome-unchanged` and `ineffective`, freeze
  the candidate as diagnostic, and hold the next same-hypothesis effect cycle.
- Keep the target `in-progress`, with no manual Resume or human input, unless an
  existing direct-authority boundary independently says otherwise.
- Route target-local defects to the target owner and reserved acts to the
  existing decision owner; do not open a Factory repair for either.

### Scope and non-goals

- In scope: incident classification, containment, target posture, and safe
  frontier projection.
- Not in scope: source changes, release activation, range repair, or target edits.
- Do not add a general defect ontology; use only distinctions needed to select
  an existing owner.

### Deliverables and recorded state

- Recovery disposition and current control-posture projection in the existing
  event/policy history.

### Resource and economy contract

One compact target-state read and one current incident-head read per changed
fingerprint. Equivalent state deduplicates; no polling or commentary on no change.

### QA and independent review

Focused state-machine tests plus Sol review of classification authority and
false-positive/false-negative incident cases.

### Acceptance

- The incident-derived Factory incompatibility selects autonomous recovery and
  preserves the target mission; target-owned and reserved cases do not.
- An unchanged accepted outcome plus the same treatment hypothesis selects the
  bounded effectiveness hold without changing unrelated safe frontiers.

### Negative tests

- Reject caller-selected ownership, stale incident heads, closed incidents,
  route text as cause authority, whole-run blocking with a nonempty safe frontier,
  a Factory repair disposition that requests user Resume, and same-hypothesis
  continuation that ignores an unchanged accepted outcome fingerprint.

### Completion evidence

Pending.

### Stop

Stop before creating or changing a Software Factory repair candidate.

---

## Block 2 — Route a bounded repair against the current accepted source

Status: `not-started`

### Objective

Produce one narrowly scoped, independently reviewable Software Factory repair
from the current accepted source while preserving target and rejected history.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: a supported Factory defect reliably reaches the
  existing reviewer/fix-executor lane and converges on a current-source candidate.
- Potential capability loss or regression: repairing an obsolete source line or
  widening from an incident could create a second incompatibility.
- Protected-capability effect: preserves current release compatibility, exact
  review, allowed file scope, rejected candidates, target isolation, and
  proof-proportionality.
- Architecture and operating-model effect: reuses the existing Sol Max plan and
  allowlisted fix executor; adds current-source admission and stale-candidate
  handling to their coordination.
- Tradeoff and source evidence: one port to current source may supersede a valid
  older candidate, but accepted evidence remains reusable where byte/currentness
  checks prove it unchanged.

### Inputs and dependencies

- Block 1 Factory-owned recovery disposition, exact current release/source, and
  current authorized maintenance mode.

### Required work

- Route one evidence-bound Sol Max fix plan naming the concrete invariant,
  existing owner, exact permitted files, focused proof, acceptance gate, rollback,
  and stop condition.
- Before the first further consequential effect, bind the primary observable
  outcome, exact accepted baseline outcome/finding-set fingerprint, stable
  treatment-hypothesis identity, and measurable effectiveness criterion. A
  materially different treatment receives a new identity and explains the
  causal difference; renaming or mechanically correcting the same treatment
  does not clear an effectiveness hold.
- Admit the candidate only when its base equals or contains the current accepted
  source. If the source changes before acceptance, freeze the candidate as
  diagnostic and port only the reviewed delta to the new current source.
- Permit only the current allowlisted Software Factory maintenance surface; any
  broader permission, target edit, release-pointer write, or model/spend change
  remains reserved.
- Run the affected proof once after all likely-mutating review findings are
  resolved. Preserve unaffected accepted receipts by exact currentness checks.
- If the Block 1 hold applies, retain mechanically valid candidate proof as
  diagnostic only and stop before mapped validation, release, refresh, target
  wake, artifact production, or another expensive same-hypothesis owner cycle.

### Scope and non-goals

- In scope: current-source repair planning, implementation, focused validation,
  and exact candidate freeze.
- Not in scope: target-repository mutation, promotion, range/tracker changes, or
  speculative adjacent hardening.
- Do not build an arbitrary repair engine or let the coordinator synthesize code.

### Deliverables and recorded state

- Exact candidate commit/tree, changed-path envelope, focused receipt, preserved
  evidence map, and immutable rejected/superseded candidate records.

### Resource and economy contract

One active repair lane, one current-source check and one outcome/hypothesis gate
before expensive proof, and one affected proof after the candidate is frozen.
Mapped/full validation runs only when both the maintained changed-path plan and
the predeclared effectiveness path require it.

### QA and independent review

Focused owner tests and distinct exact-revision review. The fix executor cannot
self-accept or activate its candidate.

### Acceptance

- One exact current-source candidate closes the incident invariant without new
  target, permission, owner, or unrelated deltas.
- A held candidate remains diagnostic until an existing-owner record admits a
  materially different treatment against the frozen baseline and criterion.

### Negative tests

- Reject stale-base, dirty, cross-lineage, over-allowlist, target-writing,
  caller-resealed, self-reviewed, changed-after-review, and repeated-proof
  candidates; also reject process-valid proof as evidence that the motivating
  outcome improved.

### Completion evidence

Pending.

### Stop

Stop before local release promotion or running-role refresh.

---

## Block 3 — Compose accepted repair, activation, range, and tracker restoration

Status: `not-started`

### Objective

Turn an exact accepted Factory repair into one verified active control plane and
one current target range/tracker frontier through existing owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: accepted repair automatically becomes usable and
  restores the canonical state needed to continue the target.
- Potential capability loss or regression: activation without current range or
  inferred tracker completion could resume the wrong work under false authority.
- Protected-capability effect: preserves release single-writer/rollback,
  stable-channel refresh, range non-contraction, exact tracker evidence, and
  target-writer ownership.
- Architecture and operating-model effect: composes existing promotion,
  role-refresh, range, tracker, and route owners in one derived recovery gate;
  none of their native records is replaced.
- Tradeoff and source evidence: restoration may pause at an exact owner mismatch,
  but it must route that mismatch as the next Factory repair rather than use a
  patched helper or ask the user to Resume.

### Inputs and dependencies

- Block 2 exact accepted candidate, current release-owner status, exact direct
  full-tracker source, current target tracker bytes, and preserved accepted
  evidence.
- Exact accepted/current predecessor evidence for the promotion, safe-boundary
  refresh, and rollback owners from
  `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md`.
  If any prerequisite remains unfinished, hold this Block and route its existing
  owner rather than implementing a substitute here.

### Required work

- Invoke only `software-factory-release-promote`; verify returned source, release,
  manifest, installed roots, history, and rollback posture. Treat remote
  publication independently.
- Refresh compatible running roles only through the existing safe-boundary
  `role-refresh`; preserve mission, policy, event, incident, range, cursor,
  schedule, model, Gmail, and automation identities.
- Rehydrate the current full-tracker source through the current released range
  owner. Create/admit/amend only through its canonical operations; never invoke
  an unreleased or patched helper.
- When target tracker status is stale, build a reconciliation packet from exact
  accepted commits, reviews, tracker bytes, and owner receipts; route it to the
  same target owner. The target owner changes tracker state, and the range gate
  independently verifies the result.
- Compare release/range/tracker owner records before and after every step; an
  interruption or failure must be idempotent and leave one current next action.

### Scope and non-goals

- In scope: local activation, role refresh, canonical range currentness, and
  target-owned tracker reconciliation.
- Not in scope: manual pointer writes, proof replay, supervisor tracker edits,
  publication-as-activation, or target implementation work.
- A new coordinator record may contain only exact references and derived state;
  it may not duplicate owner payloads or become another authority.

### Deliverables and recorded state

- Verified promotion/refresh receipts, current range gate, target reconciliation
  packet/acknowledgement, and one eligible safe frontier.

### Resource and economy contract

At most one promotion per accepted source, one role refresh per compatible
running role, one canonical range admission/amendment, and one reconciliation
route per exact recovery identity. Unchanged owner state is not reread.

### QA and independent review

Owner-boundary tests with release failure/rollback, range incompatibility,
status divergence, interruption, deduplication, and no-target-write attacks.

### Acceptance

- The active release is exact, the current range binds the full direct request,
  accepted Blocks equal the target owner's current tracker evidence, and exactly
  one next eligible target frontier exists.

### Negative tests

- Reject unaccepted promotion, false returned identity, unsafe refresh, legacy or
  patched helper use, contracted range, inferred Block acceptance, missing
  accepted evidence, supervisor tracker writes, duplicate routes, and partial
  restoration presented as current.
- Reject docs, an observed manual owner call, or this tracker itself as a
  substitute for accepted predecessor promotion/refresh/rollback behavior.

### Completion evidence

Pending.

### Stop

Stop before waking the implementation task or claiming recovery effectiveness.

---

## Block 4 — Resume the same target exactly once and assess effectiveness

Status: `not-started`

### Objective

Wake the original implementation task once at its exact restored frontier and
prove that the Factory repair caused effective target continuation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: recovery ends in observable implementation progress,
  not merely a repaired helper or released skill.
- Potential capability loss or regression: duplicate or stale wakes could cause
  competing work, replay, or unrelated invalidation.
- Protected-capability effect: preserves same-task identity, target single-writer
  posture, exact eligible frontier, accepted evidence reuse, and independent
  effectiveness assessment.
- Architecture and operating-model effect: adds recovery identity and owner-state
  deduplication around the existing route gate and effectiveness owner.
- Tradeoff and source evidence: supervision waits silently for a genuine owner or
  target revision; it does not poll or narrate unchanged state.

### Inputs and dependencies

- Block 3 verified release/range/tracker restoration and exact eligible frontier.

### Required work

- Route one content-minimized action to the original target task through
  `thread-route-gate`, binding recovery identity, exact frontier, required posture,
  preserved evidence, prohibited replay, and no-user-action posture.
- Trigger exactly one target turn. A retry requires a new failed/terminated route
  state and a new owner revision; equivalent state deduplicates.
- Observe the next genuine target revision once. Record whether the corrected
  owner was used, preserved evidence remained valid, the same Block advanced,
  and unrelated work stayed unchanged.
- Compare the new independent outcome to the declared baseline and criterion,
  recording the current disposition/material-finding-set delta and whether the
  causal treatment met the predeclared threshold. Preserve an unchanged result
  as current evidence rather than converting supporting process proof into
  effectiveness.
- Keep the incident open for `effective`, `mixed`, `ineffective`, or `unresolved`
  assessment by a different reviewer. Close current-run and reusable lanes
  independently.

### Scope and non-goals

- In scope: one route, one wake, one changed-state read, and effectiveness.
- Not in scope: polling, repeated status messages, target implementation,
  declaring Block acceptance, or waiting for optional prevention work.
- Do not create a replacement target thread when the original task is live and
  current.

### Deliverables and recorded state

- Route/wake receipt, target-advance observation, effectiveness disposition, and
  explicit reusable-lane disposition.

### Resource and economy contract

Exactly one route and wake per recovery identity. After an effectiveness hold,
read or wake only for a materially different treatment, attempted hold violation,
or new independent outcome evidence; no unchanged intermediate read, commentary,
or model call.

### QA and independent review

Focused deduplication and stale-route tests plus independent effectiveness review
of the actual target delta, not the supervisor narrative.

### Acceptance

- The same target moves from the restored frontier without proof replay or user
  action, and a different reviewer binds effectiveness to the resulting target
  evidence.

### Negative tests

- Reject wrong/replacement target, stale frontier, duplicate wake, no-op route,
  unchanged polling, proof replay, target mutation by supervision, same-reviewer
  effectiveness, helper activation without target advancement, a result that
  omits the declared baseline/current delta, and process concordance presented as
  outcome improvement.

### Completion evidence

Pending.

### Stop

Stop before final integration, promotion of the complete tracker-owned batch, or
terminal closure.

---

## Block 5 — Freeze, review, integrate, and promote the complete successor

Status: `not-started`

### Objective

Freeze one complete recovery-capable Software Factory successor, independently
accept it, integrate it durably, and activate it through the existing owner.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates, reviews,
  integrates, and activates behavior implemented in Blocks 1–4; it adds no new
  recovery capability.

### Inputs and dependencies

- Blocks 0–4 and the current accepted Software Factory source/release.

### Required work

- Finish all known in-scope mutations and permitted review findings before final
  validation; freeze exact commit/tree/path and current release lineage.
- Run focused suites, maintained changed-test plan/execution, skill validators,
  tracker verifier, compile, diff, and any release-sensitive gate selected by the
  exact changed-path owner.
- Obtain distinct exact-revision review; record findings and repair only by
  immutable successor commits with affected proof rerun.
- Commit, non-force push to the unambiguous upstream, reconcile the accepted
  source into the canonical branch, and promote through the existing owner.
  Durability-pending may outlive successful local activation.

### Scope and non-goals

- In scope: this tracker's exact Software Factory delta and release.
- Not in scope: target repository changes, unrelated Factory backlog, full-suite
  replay without a changed-path trigger, or manual release-pointer operations.
- Do not widen the candidate after exact review without reopening the affected
  review and proof.

### Deliverables and recorded state

- Accepted commit/tree, pushed branch/canonical ancestry, active release identity,
  installed-root proof, and rollback record.

### Resource and economy contract

Reuse Blocks 0–4 evidence by exact currentness; one mapped validation and one
release promotion for the final frozen candidate. Rerun only proof invalidated by
a successor finding.

### QA and independent review

Exact-revision independent acceptance and owner-returned local release proof are
mandatory. Remote publication is verified separately.

### Acceptance

- Canonical source, accepted commit, active release manifest, installed roots,
  and current supervision behavior reconcile exactly.

### Negative tests

- Reject dirty/nonexact source, stale review, changed candidate, new mapped
  failure, failed ancestry/publication presented as durable, activation identity
  mismatch, and local pointer mutation outside the release owner.

### Completion evidence

Pending.

### Stop

Stop before live dogfood and terminal effectiveness closure.

---

## Block 6 — Dogfood the released lifecycle and close only from observed outcome

Status: `not-started`

### Objective

Prove the released capability across a real owner-backed isolated recovery and
close the tracker only when the implementation outcome resumes as designed.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block exercises and observes the
  released lifecycle; it does not add behavior or broaden authority.

### Inputs and dependencies

- Block 5 accepted active release and one isolated Software Factory-owned tracker
  run that contains no patent/project content and authorizes no external action.

### Required work

- Run one isolated owner-backed incident through classification, containment,
  current-source repair handoff, accepted release identity, safe refresh,
  canonical range/tracker restoration, one wake, and target advancement.
- Inject the observed failure classes: helper/receipt incompatibility,
  active-source drift, absent range, tracker-status divergence, publication
  failure with local activation, duplicate route, unchanged watcher wake, and
  consecutive accepted unchanged outcomes followed by a same-hypothesis
  candidate.
- Prove the unchanged-outcome case freezes the candidate as diagnostic before
  its next expensive effect, rejects an attempted hold violation, and remains
  silent until a materially different treatment or new independent outcome is
  present. The later result must expose the declared baseline/current effect
  delta.
- Verify rollback on unhealthy refresh, no target writes by supervision, no
  user/manual Resume request, no duplicate call, and no proof replay.
- Record final effectiveness by a different reviewer, close the incident and
  reusable lane independently, update product docs/changelog, and reconcile this
  tracker to exact completion evidence.

### Scope and non-goals

- In scope: isolated dogfood, regression proof, documentation, and closure.
- Not in scope: causing a real product/patent failure, live project analysis,
  external communication, arbitrary target repair, or a new monitoring service.
- Do not keep a real implementation run open merely to gather optional recurrence
  evidence after the isolated proof passes.

### Deliverables and recorded state

- End-to-end recovery receipt chain, negative-test matrix, independent
  effectiveness record, updated documentation, and completed tracker evidence.

### Resource and economy contract

One isolated dogfood lifecycle. Batch failure injections around one frozen
fixture and reuse owner outputs; no per-case release, role refresh, or model call
when a deterministic owner fixture suffices.

### QA and independent review

Focused recovery suite, exact mapped gate, owner rollback checks, tracker full
verification, and distinct final outcome review.

### Acceptance

- Every supported Factory-owned failure converges to one verified active release,
  current range/tracker frontier, single target wake, and observed progress—or to
  verified rollback plus one current autonomous next action—with zero user action.
- The target-local, reserved, ambiguous, duplicate, stale, and unauthorized cases
  remain fail closed without being misreported as recovered.

### Negative tests

- Reject closure from process receipts alone, helper activation without target
  progress, partial rollback, open incident, unresolved reusable-lane disposition,
  tracker evidence mismatch, same-hypothesis cycling after an unchanged outcome,
  user/manual Resume request, and any hidden target or protected-project mutation.

### Completion evidence

Pending.

### Stop

Stop. Do not extend this tracker into generic self-healing, target implementation,
or unrelated Software Factory hardening.
