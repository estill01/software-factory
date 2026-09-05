# Portable supervision implementation tracker

- Tracker status: `complete`
- Tracker sequence: Blocks 0–2
- Repository: `software_factory`, branch `codex/portable-supervision-runtime`
- Governing objective: direct user instruction in task `01a06f3e-7ffc-75b3-873d-675e9b93ae84`: make `supervise tracker runs` work on the laptop and GCP, including necessary scripts and cross-task coordination.

## 1. Purpose and intended outcome

An ordinary skill invocation discovers the actual schedule and transport owner,
reuses an existing exact-target group, or boots an isolated group through the
available backend. Missing desktop tools must not conceal a working native host.

Completion means the portable entry point is installed, the current target has
five initialized roles and three real schedules, and direct reads, gated delivery,
and scheduler restart are verified without changing the patent target's group.

### Mission frame

- Primary outcome: usable persistent supervision across the two supported runtime paths.
- Observable completion: installed entry point, exact bindings, native delivery receipts and live wake evidence; desktop path retained and its selection tested.
- Ordinary effect classes needed: code, focused tests, independent review, isolated installation, task creation, scheduling, coordination, tracker updates, commits and pushes.
- Hard direct authority or safety boundaries: preserve task `01a06f3e-c732-74b2-bde9-3980430df4de` and its running group; obey host storage preflight; no email authorization; no implementation of RRA or SFV2 inferred from this repair.
- Material goal alteration or reversal: replacing the existing patent group or changing patent authority requires a separate instruction.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: changes how the supervision skill discovers and boots its runtime.
- Direct product sources: `supervise-tracker-runs/SKILL.md`, `references/supervision-policy.md`, and accepted native runtime commit `557e6545053a6f710d6fc72d36d65e1de21a4354`.
- Product thesis and intended effect: one supervision policy can use the scheduler that owns the target on the current host.
- Protected capabilities: exact target isolation, direct evidence, gated coordination, retained history, quiet unchanged-state monitoring, existing desktop boot.
- Architecture strategy: reuse native transport, SQLite schedule owner, and semantic helper; add discovery and repeatable bootstrap.
- Requested capability: run the same named skill on laptop or GCP.
- Proportionality: adapt the existing backend instead of adding another scheduler or control service.
- Tradeoffs: native scheduling remains a local persistent service; the desktop path retains app-owned scheduling.
- Uncertainty: a physical laptop is unavailable for live acceptance in this environment; distinguish compatibility tests from observed laptop operation.

## 2. Target architecture and authority boundaries

Read-only discovery resolves the exact target and any existing owner before boot.
The app backend continues to use app tools when available. The native backend
uses the existing Codex app-server socket for tasks, one isolated runtime config
and SQLite database per group, and the maintained helper for semantic authority.
Bootstrap receipts record progress; they do not replace the semantic ledger.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Native transport and schedule delivery | `scripts/gcp_codex_transport.py`, `scripts/gcp_supervision.py` | adapt |
| Role policy and semantic records | `references/supervision-policy.md`, `scripts/supervision_log.py` | reuse |
| Desktop boot | `supervise-tracker-runs/SKILL.md` | preserve |
| Host persistence | systemd and mounted persistent disk | reuse with a distinct unit |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Accepted GCP native runtime | `557e6545053a6f710d6fc72d36d65e1de21a4354` | adapt | 0 | remove single-target assumptions |
| Current range-aware helper | `afbc5f6acb291efb119ddda9974bc29718b60849` | reuse | 0 | preserve helper behavior |
| RRA planning prerequisite | Patent Studio commit `8408489e` | remediate | 2 | correct obsolete missing-controls diagnosis |

## 5. Scope, non-goals, and proportionality

In scope: discovery, isolated bootstrap, installed instructions, live activation,
focused evidence and durability. Out of scope: patent edits, RRA implementation,
SFV2 implementation, a new generic orchestration platform, email, daemon migration.
A finding authorizes only the narrowest correction of its concrete invariant.

## 6. Block execution contract

Execute Blocks 0–2 in order. Re-read the selected Block and inspect current state
before editing. Mark table and Block in progress at the first producing effect.
Preserve unrelated work. Reuse existing owners and keep validation proportional.
Audit each Block before advancing; record exact candidate and evidence. Checkpoint
and push scoped commits without treating a Block stop as termination of this full
direct-user range. Continue every safe downstream Block. Do not invent human gates.
Reconcile requested range, accepted Blocks, remaining work, authorized effects and
observable outcome before any final completion claim.

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Discover owners and bootstrap isolated groups | — | `complete` |
| 1 | Install portable skill and initialize this target | 0 | `complete` |
| 2 | Verify live operation and record delivery | 1 | `complete` |

Required order: `0 → 1 → 2`.

## Block 0 — Discover owners and bootstrap isolated groups

Status: `complete`

### Objective

Make backend selection and native bootstrap repeatable without duplicate groups.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: discover a working native owner when app tools are absent.
- Potential capability loss or regression: duplicate or wrong-target schedules.
- Protected-capability effect: exact config, role, schedule and mission bindings are checked.
- Architecture and operating-model effect: native bootstrap becomes reusable around existing owners.
- Tradeoff and source evidence: source runtime at `557e654` already supplies reliable delivery; adapt it.

### Inputs and dependencies

Accepted native source and current range-aware helper; no predecessor Block.

### Required work

Add read-only owner discovery and resumable bootstrap; remove patent-specific
prompt assumptions; include exact config paths in every command; validate before
enabling schedules; preserve existing desktop workflow.

### Scope and non-goals

Only supervision runtime and entry point. No new semantic ledger or task migration.

### Deliverables and recorded state

Scripts, portable backend instructions, focused tests and review evidence.

### Resource and economy contract

Inspect only known owner config locations and the exact target; bound each RPC and
bootstrap step. No scans of full task histories or unrelated repositories.

### QA and independent review

Run inherited transport/runtime tests and focused isolation, idempotence,
uncertain-creation, configuration quoting and backend-selection tests. An
independent read-only reviewer challenges the candidate before installation.

### Acceptance

Existing target owners are reused; a second target gets separate state; ambiguous
creation is retained as uncertain; schedules cannot activate before binding proof.

### Negative tests

Reject conflicting targets, duplicate owners, missing role initialization and
schedule/policy disagreement. Read-only discovery must create no database.

### Completion evidence

- Exact candidate: `9af6e9c46173ca46d3495c44066685a5b38d572a`.
- Validation: 39 focused native transport/runtime/bootstrap tests pass; full tracker and skill validators pass; `git diff --check` passes.
- Independent review: `portable_supervision_review` accepted that exact clean commit after corrections to Luna rendering, registry isolation, early source validation and full mission binding checks.
- Live discovery: existing patent target resolves to its legacy native config; this target resolves to a distinct new group.
- Remaining open work: installation, initialization and actual delivery belong to Blocks 1–2; physical laptop deployment remains unobserved.
- Decision/continuation posture: no user gate; continue the authorized safe frontier.
- Post-block audit: accepted for scoped installation and live validation.
- Git durability: exact candidate pushed to `origin/codex/portable-supervision-runtime`.


### Stop

Stop before installation owned by Block 1, then continue after the Block audit.

## Block 1 — Install portable skill and initialize this target

Status: `complete`

### Objective

Make the repaired skill available and initialize the exact requested group.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: future invocations find the installed backend.
- Potential capability loss or regression: changing the existing patent service.
- Protected-capability effect: retain its config, unit, schedules and state.
- Architecture and operating-model effect: distinct persistent service per native group.
- Tradeoff and source evidence: reuse host systemd persistence from the accepted GCP unit.

### Inputs and dependencies

Accepted Block 0 candidate and independent review.

### Required work

Install the exact reviewed runtime and instructions through an appropriate retained
release path. Bootstrap five roles and three initially paused schedules for
`01a06f3e-7ffc-75b3-873d-675e9b93ae84`; verify durable initialization and helper binding.

### Scope and non-goals

Only the new group and portable entry point; do not restart the shared Codex daemon.

### Deliverables and recorded state

Installed paths, retained prior release, group config, role and schedule IDs, unit.

### Resource and economy contract

Five persistent roles, three schedules, bounded initialization turns. Preflight
before installation or database writes; all working data stays on the mounted disk.

### QA and independent review

Verify installed bytes and exact owner state, then audit Block acceptance.

### Acceptance

All five real roles are durably initialized; three schedule IDs and semantic
bindings agree; existing patent service configuration is unchanged.

### Negative tests

Repeated bootstrap must reuse IDs and leave the peer group untouched.

### Completion evidence

- Installed successor: `c3328d5255ae84ceb3aef1e93facf5e59d9e1c32`, independently accepted after the real systemd parser caught and the successor corrected scalar path quoting. Two focused unit/parser checks pass; unchanged predecessor transport/bootstrap proof is reused.
- Host release: `/srv/patent-studio/tooling/portable-supervision/releases/c3328d5255ae`; retained `host-installation.json` binds source, review, tests and prior release. Both r0/r2 supervision skill entry points resolve through its stable `current`; other skill channels and the peer runtime are untouched.
- Five native roles completed ten initialization-only turns; exact receipts are in the new group's `config.json`. Repeated ready bootstrap returned the same byte-identical config.
- Three paused schedules and the exact derived mission pass native/helper agreement checks. The distinct `codex-supervision-01a06f3e-7ffc.service` is enabled and running while schedules remain paused.
- Peer preservation: original config SHA-256 `68c68b12a95ff8c02ebdefef11bd1cbad7702df648e1f617a5462cc2979c716d`, unit SHA-256 `97642431c39b370efeebe99c69583b71b701ba5d6432a8c197da618546ddddcf`, native current release `range-afbc5f6acb29`, original service PID `1054787` unchanged at this checkpoint.
- Remaining open work: actual schedule activation, routed delivery and restart proof in Block 2.
- Decision/continuation posture: continue without an additional user gate.
- Post-block audit: accepted; initialization is not misreported as active monitoring.
- Git durability: successor pushed on the existing feature branch.


### Stop

Stop before live schedule activation owned by Block 2, then continue after audit.

## Block 2 — Verify live operation and record delivery

Status: `complete`

### Objective

Demonstrate usable ongoing supervision and make its evidence discoverable.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: acceptance of the runtime installed in Blocks 0–1.

### Inputs and dependencies

Accepted Block 1 and current role/schedule bindings.

### Required work

Enable the isolated service; observe a real scheduled wake and role-gated
cross-task delivery; verify restart preserves schedules and receipts. Update
this tracker and the RRA prerequisite note with the actual runtime owner and
dependency posture. Commit and push the scoped changes.

### Scope and non-goals

No RRA Block begins as a side effect. Do not represent fake tests as live laptop proof.

### Deliverables and recorded state

Current live evidence, tracker/index updates and durable source revisions.

### Resource and economy contract

Use compact state and exact new role turns; avoid repeated unchanged polling.

### QA and independent review

Audit observed outcomes against the direct request; retain the laptop test limitation.

### Acceptance

The group remains active after restart; routing has an actual delivery receipt;
future skill invocations discover its exact config; both trackers report current truth.

### Negative tests

Queued-only delivery or an enabled schedule without an observed wake is insufficient.

### Completion evidence

- Installed code: `6d6f83b55c5074667000bce5dfe88207362fbb3e`, independently accepted; retained host release `/srv/patent-studio/tooling/portable-supervision/releases/6d6f83b55c50`. All 35 installed source files match its manifest.
- Live correction retained: initial initialization receipts did not prove loaded tasks used their full roles. Luna repeated `INITIALIZED`; the watcher loaded generic instructions. Only this group's schedules were paused. Native `thread/settings/update` applied the exact roles, and successor `d4ec1e3` adds that owner to repeatable bootstrap. Actual Luna compact-read/gate execution proved the correction; 20 focused bootstrap/systemd tests pass with ignored-resume behavior modeled. Successor `6d6f83b` also fixes the observed plaintext `--help` wrapper failure, with one real-helper regression passing. Unchanged transport proof is reused.
- Group: `supervision-group-31e6977d466025bd9de56e01`, target `01a06f3e-7ffc-75b3-873d-675e9b93ae84`. Five distinct roles and three enabled schedules retain the exact IDs in `acceptance.json`.
- Scheduled post-restart liveness proof: delivery `876f760b-73a1-5dd8-a42e-7171d7598d12`, completed role turn `01a072a5-177f-7791-a2de-36a868a45c00`, two successful exact-config commands and quiet final.
- Actual gated coordination: watcher-to-base delivery `2e6f464f-746b-50ad-ab99-26b19c6cfc2a`, source `EVT-000001`, acknowledged by native turn `01a072a2-216e-77c2-9d5b-b4c49fdda692`. The base reviewer directly read the target and recorded `EVT-000002` with no supported intervention.
- Persistence: only `codex-supervision-01a06f3e-7ffc.service` restarted, PID `1243749` to `1249890`; exact schedule state and all seven preceding delivery receipts were preserved. The service is enabled and running. Peer configuration/unit hashes, native current release and original PID `1054787` remained unchanged.
- Canonical live evidence: `/srv/patent-studio/private/gcp-supervision/groups/01a06f3e-7ffc-75b3-873d-675e9b93ae84/acceptance.json`, with retained `before-restart.json` and `after-restart.json`. Installed discovery returns `reuse` for this exact config.
- Patent Studio correction: `77e5b8c4` updates the RRA prerequisite note and exact canonical-index hash. Full 28-Block tracker validation and the documentation-scoped changed test plan pass; no web or unrelated runtime suite is selected. RRA remains authoring-only, all Blocks not-started.
- Remaining limitations: physical laptop execution not observed; app control path retained and selection tested. The enabled four-hour reviewer schedule has not reached its first periodic wake. Native schedule controls do not claim a legacy app-owner semantic lifecycle receipt. None is represented as observed proof.
- Decision/continuation posture: all three requested Blocks accepted; no remaining implementation frontier in this bounded repair.
- Post-block audit: `portable_supervision_review` independently accepted the installed GCP outcome after native role reads, read-only SQLite inspection, installed-file verification, restart comparison and peer-preservation checks; no missing required work in this scope.
- Git durability: runtime source pushed to `origin/codex/portable-supervision-runtime`; RRA correction pushed on its existing feature branch. The final tracker checkpoint records accepted local delivery and source durability.


### Stop

Stop after portable supervision delivery; leave RRA implementation to its tracker.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Backend discovery and exact-target reuse | 0 | 1 | 2 |
| Five durable roles and three isolated schedules | 0 | 1 | 2 |
| Direct reads and actual gated delivery | 0 | 1 | 2 |
| Persistent operation and accurate tracker posture | 1 | 2 | 2 |

## 9. Final completion definition

All three Blocks must be accepted at current revisions, installation and actual
native operation verified, protected peer state preserved, and source changes
pushed. Desktop compatibility is bounded to selection/instruction tests until a
physical laptop supplies live proof; no unsupported universal-runtime claim.
