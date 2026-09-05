# Portable supervision implementation tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–2
- Repository: `software_factory`, branch `codex/portable-supervision-runtime`
- Governing objective: direct user instruction in task `01a06f3e-7ffc-75b3-873d-675e9b93ae84`: make `supervise tracker runs` work on the laptop and GCP, including necessary scripts and cross-task coordination.
- Current installed revision: `8c868ff7717bb3305b5e80c20bef28889e642722`; independently accepted code, retained installation and live target-service verification.
- Remaining work: remove redundant release-key signing from local source admission, install the independently reviewed correction, admit exact canonical sources, supersede the obsolete deferral, and complete current range/outcome reconciliation. The latest direct user explicitly authorizes this correction; no key provisioning is required for local admission.

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
| 2 | Verify live operation and record delivery | 1 | `in-progress` |

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

Status: `in-progress`

### Objective

Demonstrate usable ongoing supervision and make its evidence discoverable.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: complete exact-source admission and preserve writable native role operation across reloads.
- Potential capability loss or regression: admitting stale or altered authority, losing delivery receipts, or changing another task's execution settings.
- Protected-capability effect: preserve independent canonical review, byte-exact provenance, uncertain receipts, mission boundaries and peer isolation; historical signed consumers retain their key identity.
- Architecture and operating-model effect: reuse local direct-authority ingestion and clean semantic review; remove the release-key export dependency from that local path. Retain accepted shared role-resume arguments and runtime health behavior.
- Tradeoff and source evidence: direct human item `01a07397-65b4-7290-aba0-f813d5edbb9e` rejects the redundant signer dependency and requires full implementation. Canonical same-task review is sufficient locally; signed external artifacts retain their existing verification.

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

## Corrective continuation for Block 2 — canonical completion and evidence handoff

`INC-20260905-175134-D612BF` / `EVT-000008` exposed a missing canonical outcome
completion record after the accepted runtime delivery. Preserve the completed
implementation and its historical acceptance above. Reopen only this Block's
completion boundary in the same task/group. The independent base reviewer found
the substantive outcome favorable but guessed a seven-field capability object;
the maintained exact reconciliation schema was not included in its native role
prompt. Its escalation also reproduced a transport mapping defect: the complete
evidence message was passed as the helper's 240-character action field.

Required correction: expose the existing concise action separately from the full
message without changing routing authority; supply the existing schema to only
completion-review roles; validate and independently review the narrow correction,
install the accepted retained successor, and obtain current independent canonical
completion and incident disposition. Reuse all byte-identical prior proof. No
new group, scheduler, semantic ledger, RRA implementation or manual Resume.

Current corrective status: independently accepted source
`c83fbc29c972f2423e7fa1750f3d1b9790e93494` is pushed and installed as retained
release `c83fbc29c972`. All 35 installed hashes match the manifest. Seventeen
focused runtime/prompt checks pass, including full-packet delivery/dedup,
denied-route refusal and exact status-broadcast payload binding; full tracker,
skill and diff validation pass. The independent reviewer rejected the first
candidate's broadcast hashing change; the accepted successor rejects differing
broadcast action/message values before gating or delivery.

All five existing roles received acknowledged native settings updates. The
isolated service restarted from PID `1249890` to `1301368`, preserving the
three enabled schedule IDs and all 52 prior delivery IDs/turn receipts. Peer
configuration and unit hashes remain unchanged. Retained current proofs are
`corrective-c83fbc2-before.json` and `corrective-c83fbc2-after.json` under the
same group root. The historical `EVT-000012` completion for source `6d6f83b`
is preserved but cannot accept this successor. Current full-packet handoff
`7436ec79-5712-5e8d-9ff2-4f47edae2366`, source `EVT-000015`, is acknowledged
in Max turn `01a072cb-9fb4-7be1-9ad9-dadc703850bd`. Independent review verified
the direct receiving message matches the entire 2,043-character payload, stored
hash and client identity. The installed live correction is accepted with no
remaining transport/code findings. Current canonical completion/lifecycle/control
gate and incident disposition remain pending with the existing base and Max
reviewers.


### Installed range-owner dependency correction

`EVT-000016` independently verified the installed c83 outcome and `EVT-000017`
recorded its matching completed lifecycle at fingerprint
`0f9292659759b2f36234edbe5c93ab621b7a3f5b9bf25b2bf8df289040d06d71`.
The mandatory range gate still rejects terminalization because no implementation
range is bound. Preserve these records without using them to bypass that gate.
`EVT-000018` narrowed the repair to current PORTABLE Blocks 0–2 bookkeeping.
The owner rejected the appendix's repeated Block 2 heading; renaming that
appendix preserves its content and the original three-Block scope.

The next real installed bind exposed `Program revision verifier cannot be
loaded`. `EVT-000022` therefore reopens only native release packaging and its
focused verification. The declared native release paths now retain the existing
`author-implementation-trackers/scripts/program_revision.py` and
`verify_tracker.py` beside supervision, from the same reviewed source commit.
No verifier or semantic authority logic is duplicated or changed. Two focused
package checks pass: the range and full-verifier owners load outside the source
checkout, and omission of the required program verifier fails closed. Full
tracker/skill validation and diff check pass. Exact independent review accepted
`0b07dcacbc7f6692e0af8e4b9d90ed2025e527e3`; that source is pushed and installed
as retained release `0b07dcacbc7f`. All 39 archived file hashes match; c83 remains
retained. Runtime, role and helper code is byte-identical, so no service restart
or role refresh was needed.

The real installed bind now passes dependency loading and rejects the original
natural-language request: `Implementation request does not establish full-tracker
or exact Block intent`. Its exact native source is task
`01a06f3e-7ffc-75b3-873d-675e9b93ae84`, turn
`01a0726d-3ff7-73b3-8947-2358e5311615`, item
`01a0726f-31b9-7e80-b46d-ff58184beb50`, 251 UTF-8 bytes, SHA-256
`792e2627e071a097a3807a9d928d2821dd23dd4438f8d37f6d6b9be043fd22ec`.
No source normalization or invented Block command was used. Source admission
through the existing semantic owner remains the exact narrow successor; it
must preserve these original bytes, the same mission/group and accepted work.
This is a machine admission gap, not missing human implementation permission.
Block 2 remains in progress until the real range and terminal gates agree.

### Exact direct source under the descriptive mission

`EVT-000024` authorizes the existing semantic source-admission owner correction.
The same-target `direct-user:<target>:<item>` tuple may differ from the mission's
descriptive source record only with an exact signed canonical Max review. That
review binds the original task, turn, item, record, byte count and hash, current
mission root and policy, full-tracker classification and no findings. Ingestion
and retained authority replay resolve that same review; unsigned events, later
contradictions and changed mission identities are rejected. The generic request
grammar and mission identity are unchanged. Twelve affected checks pass, including
the exact 251-byte source through sign, ingest, receipt and full three-Block bind,
negative provenance/currentness cases, and existing direct/delegated paths.
Independent code review accepted `edf277061e1c2ff4f9bebc05522bad35188ebd0a`
with no findings after conflicting evidence-token and cross-mission duplicate
replay corrections. The clean commit is pushed and installed immutably as
`edf277061e1c`; all 40 release files match. Both 0b07 and c83 remain retained,
and no service restart, schedule change, or peer mutation was required.

The live signing prerequisite is separately unresolved: installed reviewer key
paths and the pinned OpenSSL executable refer to unavailable laptop locations.
The existing Max role is tracing the maintained authority owner using metadata
only. This does not authorize replacement keys, altered trust pins, or a false
completion receipt. Continue the semantic correction and resolve the signing
dependency within the current PORTABLE mission before live terminal closure.

### Remaining host prerequisites

The original writable reviewer profile was restored on the same task, allowing
Max to append `EVT-000029`, SHA-256
`bf7fdf6b79aabffdcfc10d60a347e72f241d4643adb247014fc2f46ff07e1bbe`.
The real installed signer accepts that exact review and then exits 2 with
`Sealed adaptive reviewer signing key is unavailable`. It creates no authority
receipt. `EVT-000031` owns the narrow host-profile successor, preserving the
same mission, source and key identity.

Reviewer key paths now use the account home. The exact Linux OpenSSL profile
is `/usr/bin/openssl`, SHA-256
`f4aa15f2822f670af7b5c1043d7aa6ebbbc64229fd2fae382edfc6a4524749c1`;
the existing macOS profile and reviewer public-key pin are retained. Native role
boot and unloaded-role delivery share the original resume settings, and delivery
requires the native response to confirm writable helper access before queueing.
A rejected restoration leaves a new delivery failed, while an earlier possibly
accepted send remains uncertain and is reconciled without duplication after
restoration. Implementation-target settings are not overridden. Fifty-one
affected source/host/runtime checks pass; four final restoration and receipt
recovery checks also pass. Independent review rejected candidate `2752ae1` for
a restoration requirement scoped only to one delivery. The correction retains
that requirement per recipient in the existing runtime health store, across
new deliveries, RPC failures and restarts; all 21 affected delivery tests pass.
Independent exact review accepted corrected commit
`8c868ff7717bb3305b5e80c20bef28889e642722` with no remaining findings.
It is pushed and installed immutably; all 40 file hashes match. Only the target
service restarted, to PID `1493630`. The three enabled schedule identities,
target configuration, peer PID `1054787`, peer configuration, unit and release
pointer are unchanged. The installed exact Linux verifier passes. Real source
sealing with `EVT-000029` still exits 2 because the existing reviewer key is
unavailable at the correct account-local path. The retained before/after proof
is `host-profile-2752ae1-before.json` and `host-profile-8c868ff-after.json` in
the existing group root; the rejected candidate was never installed.
Existing key provisioning stays with its external custodian; no key is
generated, moved, substituted or claimed available by these changes.

### Current independent nonterminal reconciliation

`EVT-000035` is the current failed outcome review for installed revision
`8c868ff7717bb3305b5e80c20bef28889e642722`, with one supported gap and
`capability_reconciliation_posture=reopen-narrow-owner`. Its record SHA-256 is
`8f16e619d983180ca01c07f488722ebc91e0dda3a591e35a4d616d82b714c42c`;
the frozen current-state fingerprint is
`c0b93fb1718e44e4f998234a97bd208d5188f00cc4b291c8088a8600b2a5898c`.
`EVT-000016/17` remain historical evidence only.

Decision `DEC-20260905-PORTABLE-REVIEWER-KEY` reaches `safe-deferred` at
`EVT-000043`, attempt 3, under full-autonomous control. Its empty safe-frontier
hash is `5e7a6347e19806658d7c67f33fd008d5f4da7d7106e16870c5cff0e447f886cc`.
The exact handoff `bc8d0329-5a1c-5a19-8f6a-a9c36dd4d48d` was received by
this target. Only signing, ingestion/receipt, full-tracker binding and terminal
closure are deferred. On observed availability from the existing custodian,
rerun exact `EVT-000029` signing, ingest and receipt the immutable 251-byte
source, bind current PORTABLE Blocks 0–2, and obtain fresh independent
completion plus matching lifecycle only when the range and control gates agree.
Physical laptop execution remains unobserved. No manual Resume is required.

`EVT-000044` records the actual handoff; `EVT-000046` is the target's canonical
acknowledgement. `EVT-000048` supersedes the transitional `EVT-000045`
with the matching `blocked` lifecycle at the same frozen fingerprint. Its
record SHA-256 is `7acec4531c13473dfec84bc55e80128afbeecffa0bce5e4e2d67761b25797d17`.
The control gate reports `blocked`, with no current
completion candidates and next action
`preserve-safe-deferral-and-revisit-on-authority-change`. The outcome-terminal
range gate still reports `range_binding_posture=absent`,
`final_response_permitted=false`, and
`next_action=continue-local-safe-frontier-and-repair-binding`; this remains a
nonterminal dependency report, not completed PORTABLE acceptance. Both gates
report `manual_resume_required=false`. Preserve all existing schedules and
accepted history while awaiting the exact external availability evidence.

## Local admission correction under renewed direct authority

The direct user item `01a07397-65b4-7290-aba0-f813d5edbb9e` (turn
`01a07397-64ff-7eb3-8f05-a657011a5858`, 193 UTF-8 bytes, SHA-256
`27dd47e2b5c7e0edd1f034c9c262373cf051cc5f08b6c2416e951f020bcc209b`)
supersedes the external-key prerequisite for this local workflow. Earlier failed
completion, deferral, key profiles, and installations remain historical evidence.
No key is created or substituted. The existing local ingestion owner uses the
canonical independent review directly; signed import/export consumers are intact.

- Product-capability review:
  - Trigger: consequential Block 2 correction of an unnecessary local admission dependency.
  - Frame identity: `docs/portable-supervision-implementation-tracker.md`, Block 2, SHA-256 `6b9f92b2a2146dd41b3368faf80316ecaa5ca15a190f402693f010dd2307c036`.
  - Capability added or preserved: locally reviewed direct requests can bind and finish their tracker on either supported host without a release signing credential.
  - Paths compared: local deletion of signed-event validation; bounded new admission command; existing canonical local ingestion and semantic review.
  - Selected level and owner: existing architectural owner, `direct-authority-ingest` and `clean_direct_source_review`; no new command, event shape, ledger, or service.
  - Protected-capability result: exact bytes, target/item/turn, independent Max, current mission/policy, replay and contradiction checks remain enforced.
  - Rejected alternatives: deleting validation would omit required provenance and historical signed behavior; another command duplicates the existing owner.
  - Tradeoffs and uncertainty: local review relies on its authenticated canonical ledger; a physical laptop remains unobserved.
  - Frozen-candidate proof: 23 focused local/signed/delegated authority tests, full tracker and skill validation, and diff check pass. Independent exact-revision review and installed acceptance follow; current completion is not yet claimed.
