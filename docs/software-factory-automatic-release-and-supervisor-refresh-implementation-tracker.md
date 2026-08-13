# Software Factory Automatic Release and Supervisor Refresh Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–7
- Repository: `/Users/ethanstillman/code/software_factory-control-plane-candidate`
- Governing objective: Direct-user request to make exact-accepted Software Factory releases automatically promote through the existing release owner and refresh compatible running supervisors without losing range, mission, cursor, reporting, or shutdown invariants.

## 1. Purpose and intended outcome

Make safe automatic promotion and monitor refresh the default Software Factory
behavior. An independently accepted exact source revision flows through the
existing flagless release primitive, compatible running supervisors consume the
verified activated identity at an actual safe boundary, and failure restores the
prior release/binding. A genuine tracker completion delivers and reads back its
terminal reports before its monitor and automations stop.

Completion means:

- `origin/main`, the accepted source revision, the active release manifest, and
  the stable three-skill installation resolve to one verified lineage.
- Existing and newly admitted tracker runs cannot start or return terminally
  without the existing canonical implementation-range owner being current.
- Compatible active supervisors follow the stable accepted-release channel at
  safe boundaries while preserving their policy, mission, event, cursor,
  incident, Gmail, schedule, model, and automation identities.
- A failed post-refresh health check requests rollback from the same release
  owner and restores the prior effective supervisor binding.
- Genuine completion requires terminal report delivery/readback and owner-backed
  monitor/automation shutdown.

### Mission frame

- Primary outcome: accepted Software Factory fixes become active in compatible
  supervisors automatically and safely, without a manual release/update handoff.
- Observable completion: exact accepted commit, owner-returned release identity,
  installed-root verification, migrated active automation prompts, current
  supervisor health/range posture, rollback regression proof, and terminal
  delivery/shutdown proof.
- Ordinary effect classes needed: source implementation, tests, Git checkpoints
  and push, exact independent acceptance, local promotion, automation refresh,
  policy migration, health verification, and bounded rollback recovery.
- Hard direct authority or safety boundaries: only `scripts/skill_release.py`
  writes the global release pointer; automation updates use the Codex automation
  owner; Gmail uses its maintained owner; supervisors never write the release
  pointer; manual pinning is explicit; no release follows an unaccepted push.
- Material goal alteration or reversal: disabling auto-promotion/refresh by
  default, weakening exact acceptance/currentness, changing the single release
  owner, bypassing terminal delivery, or broadening target permissions requires
  renewed direct-user authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this changes the Software Factory operating model,
  release lifecycle, and how live supervisors receive accepted behavior.
- Direct product sources: the three direct-user requirement sets carried in this
  task, active release `75481f37c3b6-e3e2f2705136`, existing release primitive
  `scripts/skill_release.py`, and existing range/control/terminal owners in
  `supervise-tracker-runs` and `implement-tracker-blocks`.
- Product thesis and intended effect: exact acceptance should be the last manual
  semantic gate; ordinary local activation and compatible monitor adoption then
  converge automatically with rollback safety.
- Protected capabilities: exact clean-commit validation, independent acceptance,
  immutable release/history, atomic pointer ownership, fresh-process verification,
  range non-contraction, mission/cursor preservation, safe-boundary refresh,
  terminal Gmail readback, and owner-backed shutdown.
- Architecture strategy: orchestrate above and after the existing release
  primitive and existing range/control owners; add no second release pointer,
  range ledger, scheduler, or supervision state authority.
- Requested capability: automatic accepted-release promotion and automatic safe
  refresh of compatible running supervisors, with unavoidable range admission
  and terminal gating.
- Proportionality: one orchestration seam plus existing owners is sufficient;
  direct supervisor pointer writes or a parallel release service would be
  broader and less safe.
- Tradeoffs: automatic convergence removes stale monitors but makes exact
  acceptance, compatibility, safe-boundary, health, and rollback checks mandatory.
- Uncertainty: no generic compatibility promise is made for arbitrary historical
  tracker formats; only maintained current tracker shapes and exact evidenced
  migrations are supported.

## 2. Target architecture and authority boundaries

`independent exact acceptance → orchestration → skill_release.py promote →
verified activated release identity → stable-channel safe-boundary refresh →
installed-root and supervisor-health verification`.

On failure after activation: `orchestration → skill_release.py rollback → stable
channel resolves prior release → role refresh restores effective prior binding`.
The release owner alone seals releases, swaps/restores `current`, verifies fresh
process roots, and writes protected release history. Supervision owns policy,
range/currentness, role refresh, terminal reporting, and shutdown. The Codex
automation owner alone changes automation definitions.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Release validation, sealing, pointer swap, verification, rollback | `scripts/skill_release.py promote/rollback` | reuse unchanged |
| Exact requested range and terminal gate | `implementation-range-bind`, `implementation-range-amend`, `implementation-range-gate`, `control-posture-gate` | make unavoidable |
| Role handoff/currentness | `thread-route-gate` purpose `role-refresh` | reuse |
| Supervisor policy and mission state | canonical policy/event/owner-root histories | preserve, never replace |
| Recurring monitor definitions | Codex automation owner | migrate once to stable paths |
| Terminal report and shutdown | `terminal-report`, Gmail readback, `terminal-shutdown` | make default completion path |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Active accepted release | `75481f37c3b64d887fdb7fa72fe2742f033c972d` | reuse | 0 | preserve roots/history while successor is proven |
| Terminal delivery/default and shutdown fixes | `3ad34f9749616582614f5455e453346e576eca12` | reuse | 5 | integrate with automatic release/refresh |
| Main-line ancestry reconciliation | `df6a0e5c84bcca88a167dbed48759c56bbe940e9` | reuse | 0 | retain as parent of final successor |
| Initial stable-channel documentation/tests | `3a777e71d1bdd69b91b569e4bec4f3956fa48a05` | adapt | 2–4 | add executable orchestration and full proof |
| Initial unavoidable range-admission slice | `e7c5fbdb1390f5f7362e04a4b6ad885ed0098bff` | adapt | 1 | wire into execution boundaries and add mapped proof |
| Existing full-range implementation | target `019fdfe4-dabe-7130-ac93-f8fa8e3bce12` | reuse | 1 | enforce at admission/runtime; do not replace |

## 5. Scope, non-goals, and proportionality

### In scope

- All functionality in the three direct-user requirement posts.
- Existing source checkpoint and uncommitted admission-gate slice in branch
  `codex/auto-activation-main-integration` at
  `/private/tmp/sf-auto-activation.8nSZaI`.
- Current active supervisor `019fb18f-3d03-7ca0-9fe9-68353f0405ce` as a real
  refresh/effectiveness case.

### Out of scope

- A second release implementation, global-pointer writer, range subsystem,
  generic legacy parser, generalized deployment service, or per-release forked
  automation fleet.
- Automatic promotion of unaccepted `main` pushes.
- Premature terminal report or shutdown while a target range remains open.

### Proportionality

Reuse the existing release, range, policy, automation, Gmail, and shutdown
owners. Add only the orchestration/currentness seams and regressions needed to
make their composition automatic and fail closed.

## 6. Block execution contract

1. Execute Blocks 0–7 in dependency order as one full-tracker request.
2. Preserve the existing isolated branch/checkpoints; do not rewrite rejected or
   accepted history.
3. Commit each cohesive validated slice and non-force push regularly.
4. Independent exact-revision acceptance is the trigger for ordinary promotion;
   it is not replaced by a push, local test pass, or self-asserted caller field.
5. Invoke only the flagless release primitive for promotion. Do not duplicate
   stage, validation, sealing, swap, verification, history, or rollback logic.
6. Refresh only at a proved safe boundary and preserve mission-specific state and
   cursors byte-for-byte except for explicitly versioned migration fields.
7. At admission and every process/final-response boundary, invoke the existing
   range/control owner. Missing/noncurrent range evidence fails closed.
8. Support maintained tracker shapes only; do not add generic legacy aliases or
   permissive parsing. An evidenced maintained migration may adapt through the
   existing range amendment owner.
9. Do not send terminal mail or pause an incomplete target. On genuine completion,
   delivery, raw readback, and owner-backed shutdown are mandatory and ordered.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Inputs: `<accepted source, prior release, policies, automation IDs>`
- Outputs: `<release identity, installed roots, refreshed bindings, receipts>`
- Focused validation: `<commands and counts>`
- Mapped validation: `<commands and counts>`
- Candidate freeze: `<exact commit/tree>`
- Remediation closure: `<finding-to-proof matrix>`
- Independent review: `<exact-revision disposition>`
- Retained open work: `<none or explicit reserved item>`
- Post-block audit: `<accepted/reopened>`
- Git durability: `<commit and push>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze integrated baseline and ownership contract | — | `completed` |
| 1 | Make existing range admission and runtime gates unavoidable | 0 | `completed` |
| 2 | Implement exact-acceptance-triggered release orchestration | 1 | `completed` |
| 3 | Implement stable-channel safe-boundary supervisor refresh | 2 | `not-started` |
| 4 | Verify health and recover through release-owner rollback | 3 | `not-started` |
| 5 | Integrate terminal report delivery, readback, and shutdown defaults | 1 | `not-started` |
| 6 | Freeze, validate, independently review, merge, and promote | 4, 5 | `not-started` |
| 7 | Refresh real monitors and prove effective automatic operation | 6 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 6 → 7`, with `1 → 5 → 6`.

## Block 0 — Freeze integrated baseline and ownership contract

Status: `completed`

### Objective

Establish one exact implementation baseline containing all inherited terminal
fixes and current orchestration work without losing `origin/main` ancestry.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block freezes identity and ownership; it does not
  change runtime behavior.

### Inputs and dependencies

- Active release `75481f37c3b6-e3e2f2705136`.
- Branch/worktree and prior commits listed in the source-adaptation map.

### Required work

- Reconcile clean worktree, branch, upstream, parents, and current diff.
- Preserve the existing release owner unchanged and classify every current edit
  into Blocks 1–5.

### Scope and non-goals

- In scope: source identity and exact ownership map.
- Not in scope: promotion, automation mutation, or live policy mutation.

### Deliverables and recorded state

- Exact baseline commit/tree/diff and owned-files list.

### Resource and economy contract

Reuse existing Git objects and current release status; no broad history replay.

### QA and independent review

Mechanical identity proof only; semantic review occurs at Block 6.

### Acceptance

- One clean branch contains `origin/main`, the active-release successor line,
  and no unrelated changes.

### Negative tests

- Reject a baseline that drops any terminal fix or rewrites accepted history.

### Completion evidence

- Repository commit: `32f45c82e09b1fbe1366f47960107a5afc3aaa26`;
  tree `9d7ecf1855240813051c3735ce38f8174508abc7`.
- Inputs: `origin/main` at
  `a2f86665842ad9514fa1c38ed8a405f148f2025b`, integrated baseline
  `df6a0e5c84bcca88a167dbed48759c56bbe940e9`, accepted delegated-authority
  correction, and active release predecessor `f9fbd97f6f10-35409d30612a`.
- Outputs: clean upstream-exact branch
  `origin/codex/delegated-authority-integration-corrected`; active accepted
  release `80e4ec1d44bf-c6fe137ec65a`; canonical range
  `RANGE-DIRECT-USER-AUTO-RELEASE-BLOCKS-0-7`; mission work-start
  `EVT-000519` / activation `EVT-000520`.
- Owned-delta classification:
  - Block 1 owns the implementation-range admission/runtime/final-response
    gates in `implement-tracker-blocks` and `supervise-tracker-runs`, including
    their policy, contract, and focused regression surfaces.
  - Block 2 owns exact-acceptance-triggered orchestration above the unchanged
    `scripts/skill_release.py promote` owner and the release-contract prose.
  - Block 3 owns stable-channel safe-boundary role refresh and preservation of
    mission, policy, event, cursor, incident, Gmail, schedule, model, and
    automation identities.
  - Block 4 owns installed-root/health verification, owner-requested rollback,
    and restoration of the prior effective supervisor binding.
  - Block 5 owns default terminal report delivery, raw attachment readback,
    automation-owner lookup, and delivery-before-shutdown enforcement.
  - Shared `supervision_log.py`, supervision policy, SKILL, tests, CHANGELOG,
    and README hunks remain assigned by the five behaviors above; no current
    source hunk introduces a second release, range, scheduler, Gmail, policy,
    or lifecycle owner.
- Focused validation: delegated range/authority `69/69`; release-owner
  assurance `21/21`; author assurance `30/30`; implementation assurance
  `69/69`.
- Mapped validation: supervision `369/369`; all three skill validators and the
  full eight-Block tracker verifier pass.
- Candidate freeze: exact source `80e4ec1d44bf981a2eec0ba7dddd5345171efb9e`.
- Baseline integrity correction: tracker-evidence checkpoint `e430a7f` exposed
  that historical merge `df6a0e5` retained the active-release tree verbatim
  while attaching `origin/main` only as ancestry. Successor `32f45c8`
  restored the 104 main-added dashboard and dashboard-contract paths with
  byte-identical Git blobs; the complete 105-path main-added set now reports
  zero missing and zero changed-byte mismatches. No accepted or rejected
  history was rewritten.
- Remediation closure: rejected `77faa6a` legacy-classification regressions
  are closed by `3481649`; routed action/source identity separation is closed
  by `80e4ec1`.
- Independent review: exact `80e4ec1` accepted with no findings; actual routed
  item-3240 and the preserved negative cases replayed.
- Retained open work: Blocks 1–7 only; Block 1 is the next eligible Block.
- Post-block audit: `origin/main` is an ancestor; the baseline implementation
  head/upstream were exact and clean at `32f45c8` before this evidence-only
  child; the release owner alone promoted and verified the active identity.
- Git durability: the integrated source is committed and non-force pushed;
  this tracker-only completion checkpoint is committed and pushed before the
  Block 1 transition.

### Stop

Stop before changing admission/runtime behavior.

---

## Block 1 — Make existing range admission and runtime gates unavoidable

Status: `completed`

### Objective

Every tracker implementation is bound through the existing canonical range owner
before work starts, and no execution/final-response boundary can bypass its gate.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: existing full-range intent becomes an unavoidable
  runtime invariant rather than an agent convention.
- Potential capability loss or regression: an overbroad migration could accept
  ambiguous tracker/request evidence.
- Protected-capability effect: preserves exact direct request bytes, tracker
  identity/structure, non-contraction, inserted prerequisites, and one-Block
  semantics.
- Architecture and operating-model effect: admission/runtime call existing range
  owners; no second ledger or parser authority.
- Tradeoff and source evidence: fail closed when exact maintained evidence cannot
  establish a binding, as required by the direct-user incident correction.

### Inputs and dependencies

- Block 0 and the accepted range implementation from target `019fdfe4…`.

### Required work

- Add an admission command/path that binds once from canonical direct-user source,
  rehydrates current bindings, and advances status-only currentness through the
  existing amendment owner.
- When a completed predecessor mission already owns a terminal range, replace it
  only through the canonical policy owner as part of the new mission admission:
  retain the predecessor binding/history as immutable evidence, create a fresh
  range ID/genesis from the new direct source and tracker, and never reinterpret
  or contract the predecessor Blocks into the successor range.
- Invoke admission before implementation begins and range/control gates at Block,
  commit, review, handoff, push, final-response, and terminal lifecycle boundaries.
- Cover maintained tracker shapes used by current repositories; reject ambiguous,
  unsupported, or structurally changed inputs without accepted amendment evidence.
- Test against real maintained tracker fixtures in addition to synthetic cases.

### Scope and non-goals

- In scope: unavoidable invocation and exact evidenced migration.
- Not in scope: a new range schema, permissive generic legacy compatibility, or
  reconstructing missing authority from prose.

### Deliverables and recorded state

- Admission/runtime CLI path, integration hooks, real-fixture regressions, docs.

### Resource and economy contract

Read one bounded tracker snapshot and reuse the existing range history/currentness.

### QA and independent review

Focused range suite, real tracker cases, full supervision mapping, exact review.

### Acceptance

- Missing/noncurrent binding prevents implementation start and terminal return.
- Current binding admits idempotently; status-only updates preserve full intent.
- A completed predecessor range remains historical, while this mission resolves
  one distinct current full-tracker binding for Blocks 0–7.

### Negative tests

- Reject missing source bytes, unsupported tracker shape, unaccepted structural
  drift, range contraction, and a direct final return without the gate.
- Reject cross-mission reuse of the predecessor range, replacement while its
  mission is nonterminal, and any rollover that is not atomic with current
  mission/policy/range ownership.

### Completion evidence

- Accepted implementation source: `80e4ec1d44bf981a2eec0ba7dddd5345171efb9e`,
  tree `25d8e4160a53af405e8494618b3fda1a45c63b73`, independently
  reviewed with no material findings; candidate root
  `41381b8f4d02f4f91fc433d6966f7f118a078791f2b67722e80130c44cb0d192`.
  The Block 0 dashboard-restoration and tracker-evidence children do not modify
  the range owner, its tests, either executing skill, or supervision policy.
- Canonical current-mission evidence: owner route `EVT-000515`, independent
  accepted review `EVT-000516`, delegated ingestion `EVT-000517`, authority
  receipt in policy version 17, fresh full-range admission in policy version 18,
  actual Block 0 work-start `EVT-000519`, and mission activation start
  `EVT-000520`. The predecessor range remains immutable history.
- Live range identity:
  `RANGE-DIRECT-USER-AUTO-RELEASE-BLOCKS-0-7`, requested Blocks 0–7. After the
  accepted Block 0 status-only amendment, the gate resolved accepted `[0]`,
  eligible `[1]`, remaining `[1,2,3,4,5,6,7]`, posture `current`, and action
  `continue-next-eligible-block`; manual resume and human input were both false.
- Focused proof: `ImplementationRangeControlTests` passed `55/55`, including
  exact current tracker shapes, canonical direct and delegated source admission,
  idempotent current binding, status-only currentness, fresh cross-mission
  rollover, owner-lock revalidation, structural-drift rejection, range
  non-contraction, and every Block/commit/review/handoff/push/final/terminal
  boundary. Exact-source mapped supervision passed `369/369`; all three skill
  validators, Python compilation, diff checks, and the eight-Block tracker
  verifier passed.
- Acceptance: missing, noncurrent, stale-receipt, wrong-mission, ambiguous,
  replaced-owner, or structurally changed evidence fails closed without
  mutation. Current admission reuses one bounded tracker snapshot and the
  existing policy/range history; no second schema, ledger, parser, or lifecycle
  owner was added.
- Product-capability review:
  - Trigger: Block 1 declares a `consequential` operating-model change.
  - Frame identity:
    `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md`,
    Block 1, tracker-level frame SHA-256
    `ec8d90164c440c07c612794ac1a5e0ca52dfd228b58dd3895fbf88437763942e`.
  - Capability added or preserved: exact full-tracker intent is admitted once
    and mechanically prevents implementation or terminal return whenever its
    current canonical binding cannot be established.
  - Paths compared: local caller/agent convention; bounded-general wrapper or
    compatibility parser; existing implementation-range admission, amendment,
    gate, policy-history, and control-posture owners.
  - Selected level and owner: the existing architectural owners, because they
    already govern canonical source, range history, currentness, lifecycle, and
    response boundaries without adding a competing state authority.
  - Protected-capability result: exact source bytes, tracker structure, Blocks
    0–7, inserted prerequisites, one-Block semantics, non-contraction, owner
    history, and predecessor evidence are preserved; `55/55` focused tests and
    the live current range prove the result.
  - Rejected alternatives: a local convention cannot make runtime/final gates
    unavoidable; a new wrapper/parser would duplicate ownership, accept broader
    unsupported shapes, and create inconsistent currentness.
  - Tradeoffs and uncertainty: supported maintained tracker shapes pay one
    bounded snapshot/currentness check at each required boundary; unsupported or
    ambiguous historical shapes fail closed rather than receiving generic
    compatibility. No unresolved product fact changes the selected owner.
  - Frozen-candidate proof: accepted mutating commit `80e4ec1d44bf981a2eec0ba7dddd5345171efb9e`,
    candidate root
    `41381b8f4d02f4f91fc433d6966f7f118a078791f2b67722e80130c44cb0d192`,
    active release `80e4ec1d44bf-c6fe137ec65a`, focused `55/55`, mapped
    `369/369`, and live accepted `[0,1]` / eligible `[2,5]` range evidence.

### Stop

Stop before invoking the release primitive.

---

## Block 2 — Implement exact-acceptance-triggered release orchestration

Status: `completed`

### Objective

One independently accepted exact source revision automatically invokes the
existing flagless release owner and consumes only its verified activated result.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: accepted fixes no longer wait for a manual activation
  handoff.
- Potential capability loss or regression: promoting a push or self-asserted
  review would weaken release provenance.
- Protected-capability effect: preserves single-writer release ownership,
  exact-clean checks, tests, sealing, activation history, verification, rollback.
- Architecture and operating-model effect: adds orchestration above the primitive,
  not release machinery beside it.
- Tradeoff and source evidence: ordinary promotion drops redundant signed review
  and signed quiescence steps, while exact independent acceptance remains the
  trigger authorization.

### Inputs and dependencies

- Block 1; canonical exact independent acceptance; `scripts/skill_release.py`.

### Required work

- Validate the acceptance against its canonical reviewer/record and exact commit.
- Invoke exactly `scripts/skill_release.py promote --repo ... --source-commit ...`.
- Parse and revalidate the returned active release/source/installed roots; never
  infer success from exit code alone.
- Deduplicate identical accepted revisions and retain manual pinning only as an
  explicit configured exception.

### Scope and non-goals

- In scope: trigger validation, owner invocation, result consumption.
- Not in scope: pointer writes, staging, sealing, test duplication, or a new
  release ledger.

### Deliverables and recorded state

- Orchestration command, exact result schema, trigger/dedup/manual-pin tests.

### Resource and economy contract

One release-owner call per new accepted revision; unchanged identity is a no-op.

### QA and independent review

Mocked owner-boundary tests plus an exact local promotion in Block 6.

### Acceptance

- Only a canonical accepted revision reaches the release owner, and only its
  verified activated identity can feed refresh.

### Negative tests

- Reject push-only, unaccepted, stale, mismatched, duplicate-divergent, and
  caller-supplied activated identities.

### Completion evidence

- Rejected evidence checkpoint: `9b910dad91fe54916f588be5d9bc361005195da3`.
  Invariant: canonical exact acceptance must enter an executable orchestration
  owner that alone invokes the flagless release primitive and validates its
  returned active identity. Input condition: the checkpoint relied on skill and
  policy instructions plus a manually performed owner call. Expected rejection:
  documentation and an observed promotion cannot substitute for the required
  command, result schema, trigger validation, or deduplication behavior.
  Verification evidence: the exact tree exposed only
  `skill-release-publication-gate`; no production command consumed an accepted
  review and invoked `skill_release.py promote`. Release-owner `21/21` tested the
  primitive, not the missing orchestration boundary.
- Preserved proof: the actual `80e4ec1` promotion remains valid owner evidence,
  and Block 1 remains accepted at `289b1ec`; neither closes this missing Block 2
  implementation.
- Repository commits: rejected documentation-only checkpoint
  `9b910dad91fe54916f588be5d9bc361005195da3`; executable owner candidate
  `f1256468034d323894149ce7e9dc0a770270a6f4`; accepted currentness correction
  `c19c5751d1c70b5ca893da9c0e5f1976796305dc`; contract evidence successor
  `7925405b7a2fd347368a32fec4c1adf12cbb553b` / tree
  `e75f2a248549fd9cfb5a752353029dc481700d3d`.
- Inputs: one current canonical `software-factory-release-acceptance`
  checkpoint review, its policy-bound base-or-Max reviewer, exact source
  revision/tree, clean canonical repository, and the unchanged
  `scripts/skill_release.py` owner.
- Outputs: `software-factory-release-promote` invokes exactly the flagless owner,
  accepts no caller active-release identity, validates automated assurance plus
  live active release/source/three installed roots, and appends one exact
  deduplicated promotion result. `--manual-pin-release` is the explicit verified
  current-release hold.
- Focused validation: maintained Python 3.14 orchestration regressions `11/11`;
  changed files compile and `git diff --check` passes.
- Mapped validation: `test_supervision_log.py` `295/295` under maintained Python
  3.14. The first mapped invocation exposed one exact documentation-phrase
  regression; the corrected successor reran that case `1/1` and the full mapped
  module `295/295`.
- Remediation closure: a later rejection of the same source or a newer accepted
  exact revision makes the prior trigger stale; a later unaccepted push does
  not. Changed tree/bytes, dirty source, unbound reviewer, invalid assurance,
  divergent live status, duplicate-divergent state, and caller-selected active
  identity reject. Exact duplicate delivery reuses one stored result without a
  second promotion call.
- Product-capability review:
  - Trigger: consequential release-operating-model change.
  - Frame identity: this tracker, Block 2, SHA-256
    `ec8d90164c440c07c612794ac1a5e0ca52dfd228b58dd3895fbf88437763942e`.
  - Capability added or preserved: independent acceptance is the last semantic
    gate; automatic local promotion remains exact, reversible, and single-owner.
  - Paths compared: a direct caller wrapper; a new generalized release service;
    the existing supervision ledger above the canonical release owner.
  - Selected level and owner: existing supervision owner plus unchanged
    `skill_release.py`, because it supplies canonical acceptance/currentness and
    release ownership without a second pointer, ledger, or service.
  - Protected-capability result: exact clean source, independent acceptance,
    automated assurance, sealing/history, atomic activation, fresh verification,
    rollback, and explicit pinning are preserved.
  - Rejected alternatives: the direct wrapper could self-assert acceptance; the
    generalized service would duplicate release authority.
  - Tradeoffs and uncertainty: only maintained current acceptance records are
    eligible; arbitrary historical formats remain unsupported. A newer
    unaccepted push is not treated as revocation.
  - Frozen-candidate proof: `7925405b7a2fd347368a32fec4c1adf12cbb553b`,
    focused `11/11`, mapped `295/295`.
- Retained open work: one exact real promotion and final independent release
  review remain owned by Block 6; running-supervisor effects remain closed until
  Block 3.
- Post-block audit: accepted. Block 2 changes only trigger/result composition
  above the existing owner and stops before any running-supervisor update.
- Git durability: implementation and corrections are pushed without history
  rewrite; this evidence checkpoint is pushed on the successor branch.

### Stop

Stop before updating a running supervisor.

---

## Block 3 — Implement stable-channel safe-boundary supervisor refresh

Status: `not-started`

### Objective

Every compatible active supervisor adopts the verified release at its next
actual safe boundary without losing mission-specific state or cursors.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: live monitors reliably receive accepted fixes.
- Potential capability loss or regression: mid-action replacement or policy
  recreation could duplicate work or lose state.
- Protected-capability effect: preserves automation IDs/schedules/status/models,
  mission/policy/event histories, cursors, incidents, Gmail bindings, and range.
- Architecture and operating-model effect: automations resolve stable `current`
  paths; already-running roles use existing gated `role-refresh`.
- Tradeoff and source evidence: one-time pinned-prompt migration is allowed; routine
  per-release prompt rewrites are not.

### Inputs and dependencies

- Block 2 verified activated identity and each supervisor's current safe-boundary
  and compatibility projection.

### Required work

- Define compatibility and actual safe-boundary checks using canonical supervisor
  state, not caller booleans.
- Migrate release-pinned prompts once to stable current paths through the Codex
  automation owner while preserving every other field.
- Rehydrate current policy/range/frontier at every wake; remove copied hashes,
  policy versions, and Block/frontier prose as authority.
- Route already-running roles through `role-refresh`; keep explicit manual pins.

### Scope and non-goals

- In scope: compatible scheduled supervisors and their current role contexts.
- Not in scope: supervisors writing the release pointer or schedules being
  recreated per release.

### Deliverables and recorded state

- Refresh plan/status, one-time migration, stable prompts, role-refresh receipts.

### Resource and economy contract

Cheap identity/safe-boundary projection first; one migration per legacy prompt;
no per-release automation churn.

### QA and independent review

Field-preservation and mid-action deferral regressions plus exact automation views.

### Acceptance

- The next wake resolves the verified active release and all mission/cursor state
  remains current and unchanged.

### Negative tests

- Reject incompatible supervisor, unsafe boundary, stale activated identity,
  policy/range drift, and a refresh that changes any preserved automation field.

### Completion evidence

Pending.

### Stop

Stop before declaring refresh health or rollback success.

---

## Block 4 — Verify health and recover through release-owner rollback

Status: `not-started`

### Objective

Post-refresh verification either proves installed roots and supervisor health or
restores the previous effective release/binding through the existing owner.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: automatic refresh is safely reversible.
- Potential capability loss or regression: false health or partial rollback could
  strand a supervisor on mismatched code/state.
- Protected-capability effect: preserves release history, stable links, policy,
  mission, cursor, range, and one effective binding.
- Architecture and operating-model effect: rollback is requested from
  `skill_release.py`; supervision records/rechecks its result.
- Tradeoff and source evidence: rollback may defer new behavior but preserves a
  healthy incumbent automatically.

### Inputs and dependencies

- Block 3 refresh result and Block 2 prior/active release identities.

### Required work

- Verify three installed roots, manifest/source identity, stable links, automation
  definitions, range/control posture, and bounded supervisor health after refresh.
- On failure, invoke release-owner rollback to the exact prior accepted release;
  stable prompts resolve it and running roles receive a gated restoration refresh.
- Make interruption/retry idempotent across activate, refresh, verify, and rollback.

### Scope and non-goals

- In scope: release/supervisor recovery only.
- Not in scope: target implementation rollback or history rewriting.

### Deliverables and recorded state

- Health receipt, rollback request/result, restored-binding verification.

### Resource and economy contract

Bounded root/status checks; deep validation only when cheap identity differs.

### QA and independent review

Failure injection at each transition and exact recovery review.

### Acceptance

- Every supported failure converges to either verified new release or verified
  restored prior release with no split binding.

### Negative tests

- Reject partial roots, stale health, failed rollback, duplicate effects, and
  supervisor state/cursor loss.

### Completion evidence

Pending.

### Stop

Stop before final integrated release/promotion.

---

## Block 5 — Integrate terminal report delivery, readback, and shutdown defaults

Status: `not-started`

### Objective

Every genuinely completed supervised tracker delivers and verifies its terminal
reports, then pauses/terminates its monitor and automations by default.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: completion has an operator-visible report and no
  orphaned monitoring cost.
- Potential capability loss or regression: premature completion could email and
  stop an active run.
- Protected-capability effect: preserves completion/range gating, Gmail ownership,
  real attachment IDs, raw readback, and automation-owner shutdown.
- Architecture and operating-model effect: terminal email is default-in-scope;
  shutdown remains downstream of verified delivery/readback.
- Tradeoff and source evidence: intermediate mail remains independently configured;
  terminal mail is mandatory when a bound primary lane exists.

### Inputs and dependencies

- Block 1 and inherited terminal fixes through `3ad34f9`.

### Required work

- Preserve default terminal delivery, long provider attachment IDs, real automation
  owner lookup, and bind-time migration for current policies/histories.
- Require range/control completion, report prepare/finalize/verify, Gmail send,
  raw MIME/attachment readback, notification receipt, then terminal shutdown.
- Pause every policy-bound automation and mark supervision paused/terminated only
  after verified delivery.

### Scope and non-goals

- In scope: genuine completed lifecycle only.
- Not in scope: emailing or shutting down incomplete/failed/blocked targets.

### Deliverables and recorded state

- Terminal policy defaults, compatibility migration, delivery/readback/shutdown
  receipts and focused tests.

### Resource and economy contract

Generate each report once, reuse verified bytes, and never rerun report production
for a delivery-only retry.

### QA and independent review

Focused terminal/Gmail/shutdown suite plus full supervision mapping.

### Acceptance

- Completion cannot pause before both reports are delivered/read back, and no
  policy-bound automation remains active afterward.

### Negative tests

- Reject incomplete range, missing/duplicate/fake attachments, unread delivery,
  wrong automation owner, partial pause, and premature shutdown.

### Completion evidence

Pending.

### Stop

Stop before promoting the integrated candidate.

---

## Block 6 — Freeze, validate, independently review, merge, and promote

Status: `not-started`

### Objective

One exact integrated successor is accepted, durable on `origin/main`, and promoted
through the flagless release owner with no unrelated work.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block proves and activates prior behavior without
  adding another capability.

### Inputs and dependencies

- Blocks 4 and 5.

### Required work

- Run focused then mapped/full suites, three skill validators, tracker verifier,
  compile, diff, clean-tree, ancestry, and currentness proof.
- Commit/push cohesive successors without rewriting rejected history.
- Obtain exact independent review; remediate findings as successor commits.
- Fast-forward/merge to `origin/main`, observe exact acceptance, then invoke the
  flagless promotion orchestration and verify returned release identity.

### Scope and non-goals

- In scope: this tracker-owned source and release only.
- Not in scope: unrelated later Factory work or manual pointer writes.

### Deliverables and recorded state

- Accepted commit/tree, origin/main identity, release ID/manifest/roots/history.

### Resource and economy contract

Reuse unaffected proof roots; rerun only proof invalidated by remediation.

### QA and independent review

Exact-revision independent review is mandatory before promotion.

### Acceptance

- `origin/main`, accepted source, active release, and installed roots reconcile.

### Negative tests

- Reject dirty/nonexact source, stale acceptance, changed candidate after review,
  failed push, or activation identity mismatch.

### Completion evidence

Pending.

### Stop

Stop before mutating live supervisor automations/policies.

---

## Block 7 — Refresh real monitors and prove effective automatic operation

Status: `not-started`

### Objective

Compatible real supervisors, including `019fb18f-3d03-7ca0-9fe9-68353f0405ce`,
use the accepted stable release channel and exhibit correct range/terminal behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: the capability is current in actual running monitors,
  not only source/tests.
- Potential capability loss or regression: live migration could disturb target
  state or permit a premature lifecycle effect.
- Protected-capability effect: preserves all mission/policy/event/cursor/incident/
  Gmail/automation state and holds incomplete targets in progress.
- Architecture and operating-model effect: establishes auto-update as default and
  manual pin as explicit exception.
- Tradeoff and source evidence: live proof is bounded to compatible monitors and
  actual safe boundaries.

### Inputs and dependencies

- Block 6 verified active release; current supervisor/automation state.

### Required work

- At the next actual safe boundary, migrate pinned prompts to stable paths via the
  automation owner, preserve all fields, and issue role refreshes.
- Bind/migrate terminal defaults and require the existing range admission/runtime
  gate; for missing exact range evidence, fail closed and route the exact repair
  rather than infer authority.
- Verify installed roots, automation views, policy/range/control posture, next wake
  behavior, and absence of duplicate/replayed work.
- Prove rollback/restoration with an isolated compatible fixture; do not induce a
  live failure merely for confidence.
- On later genuine completion, confirm terminal delivery/readback then shutdown;
  while the target remains incomplete, prove those effects remain absent.

### Scope and non-goals

- In scope: compatible current monitors and exact named target.
- Not in scope: forcing incompatible/manual-pinned supervisors or prematurely
  completing the named target.

### Deliverables and recorded state

- Live automation/policy refresh receipts, health/currentness proof, effectiveness
  evidence, and terminal-path readiness.

### Resource and economy contract

One bounded migration pass per compatible monitor; unchanged stable prompts are
no-ops; observe one actual next wake before deeper inspection.

### QA and independent review

Independent readback of live roots, automation definitions, and supervisor health.

### Acceptance

- The named monitor resolves the active release through stable paths, preserves
  state/cursors, keeps its open full range in-progress, and is configured to
  deliver/read back reports then stop automatically on genuine completion.

### Negative tests

- Reject unsafe refresh, missing range authority, changed mission/cursor, active
  terminal effects on an incomplete target, and silent fallback to pinned release.

### Completion evidence

Pending.

### Stop

Stop after all Blocks and live effectiveness proof are accepted; do not start
unrelated Software Factory work.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Existing range owner is unavoidable | 1 | 3, 5, 7 | 7 |
| Exact acceptance triggers only the single release owner | 2 | 6 | 6 |
| Stable-channel safe-boundary refresh preserves state | 3 | 4, 7 | 7 |
| Health failure rolls back and restores binding | 4 | 6, 7 | 7 |
| Completion delivers/readbacks reports before shutdown | 5 | 6, 7 | 7 |
| Main, accepted source, release, and roots reconcile | 6 | 7 | 7 |

## 9. Final completion definition

The tracker is complete only when all eight Blocks are accepted at exact current
revisions, the integrated source is pushed to `origin/main`, an independent exact
review authorizes the flagless release-owner promotion, the returned release and
three installed roots verify, compatible active supervisors refresh at safe
boundaries with all mission-specific state/cursors preserved, rollback recovery is
proven, and genuine terminal completion is enforced as report delivery/readback
followed by owner-backed monitor/automation shutdown. No incomplete target may be
emailed as complete or paused, and no supervisor may write the global release
pointer directly.
