# Portable supervision implementation tracker

- Tracker status: `in-progress`
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
| 1 | Install portable skill and initialize this target | 0 | `in-progress` |
| 2 | Verify live operation and record delivery | 1 | `not-started` |

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

Status: `in-progress`

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

Pending.

### Stop

Stop before live schedule activation owned by Block 2, then continue after audit.

## Block 2 — Verify live operation and record delivery

Status: `not-started`

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

Pending.

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
