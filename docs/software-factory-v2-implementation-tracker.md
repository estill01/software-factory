# Software Factory v2 Autonomous Work, QA, and Delivery Runtime Implementation Tracker

- Tracker status: `active`
- Tracker sequence: Blocks 0–12
- Repository: `https://github.com/estill01/software-factory`
- Governing objective: implement the maintained Software Factory v2 plan as one standalone and embeddable autonomous work, QA, supervision, acceptance, and delivery runtime.
- Architecture authority: `docs/software-factory-v2-implementation-plan.md`.
- Activation evidence: distinct read-only review thread `01a02da5-caf4-7a02-bf09-dbc7bf774bc1` accepted exact candidate `65c7bae2e69b25547b2914372ee7b9ee6ea9c1db` with no material findings after the full 13-Block verifier and exact binding checks passed.
- Implementation posture at activation: Block 0 remains `not-started`; activation initiated no implementation effect.

## 1. Purpose and intended outcome

Build one durable mission runtime that can accept an authorized outcome, derive
and execute dependency-safe work, run revision-bound QA and independent
supervision, accept or reject exact candidates, deliver or roll back effects,
and continue until the observable mission outcome is current.

Completion means:

- the same authoritative engine runs through embedded and standalone-service
  hosts without lifecycle, QA, acceptance, or delivery drift;
- the software target profile completes one real repository mission, while an
  invention-neutral content profile and one external extension prove that the
  core is not software- or Patent-Studio-specific;
- Codex app-server, local-process, and external-agent providers are replaceable
  execution substrates whose completion cannot manufacture acceptance;
- libRSI owns reusable semantic improvement workflows while Factory owns
  operational work, QA, supervision, authoritative effects, and delivery; and
- one frozen revision passes the acceptance matrix, migration, restart,
  recovery, package, and independent exact-revision audits.

### Mission frame

- Primary outcome: a production-grade autonomous work, QA, supervision,
  acceptance, and delivery runtime usable as a standalone service or embedded
  engine.
- Observable completion: Blocks 0–12 are accepted at one current pushed
  revision and the terminal dogfoods demonstrate actual operator-visible
  outcomes, not only passing process records.
- Ordinary effect classes needed: runtime/schema implementation, migrations,
  provider and target-profile adapters, fixtures, tests, build/package output,
  isolated Git commits, and pushes.
- Hard direct authority or safety boundaries: no production deployment,
  credential creation, public hosted endpoint, consumer-domain authority,
  Patent Studio workflow implementation, release activation, or external
  communication without its existing owner and separate authority.
- Material goal alteration or reversal: splitting operational authority across
  multiple engines, making Codex or libRSI the mission/acceptance owner, placing
  consumer-domain code in the OSS core, or substituting a hosted-only product
  for the required embedded and standalone modes.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker changes the product architecture,
  execution modes, provider boundary, persistence, QA, acceptance, and delivery
  behavior.
- Direct product sources: `README.md`,
  `docs/software-factory-v2-implementation-plan.md`, and the v2 source branch
  at `b34cdd9fab6830bf2ee5b9ac457e48914082e660`.
- Product thesis and intended effect: authorized missions should progress
  autonomously through work, QA, supervision, acceptance, and delivery without
  routine human scheduling, while retaining explicit authority and observable
  outcome control.
- Protected capabilities: full-tracker continuation, independent supervision,
  exact-revision review, no unsupported early return, safe-frontier work,
  durable incidents and recovery, immutable release/rollback, and current
  installed skill behavior.
- Architecture strategy: one modular operational monolith and SQL authority,
  thin hosts, replaceable providers and target profiles, libRSI as a one-way
  semantic dependency, and narrow non-authoritative utilities.
- Requested capability: standalone mission submission plus embedded use of the
  same engine, with Codex app-server as a first-class provider and QA included
  in the product contract.
- Proportionality: the plan reuses the existing runtime and skills, extracts
  only proven cross-consumer enablers, and defers full hosted multi-tenancy to a
  separately activated successor.
- Tradeoffs: one transactional runtime is less independently deployable by
  subsystem but protects operational invariants; shared utility dependencies
  reduce duplication but require version/conformance discipline.
- Uncertainty: commercial hosting, tenancy, billing, and public authentication
  are not established by current product sources and remain outside this
  tracker.

## 2. Target architecture and authority boundaries

```text
embedded caller ─┐
                 ├─> one Factory engine / operational SQL authority
standalone API ──┘        │
                          ├─ mission/program/work/scheduling
                          ├─ agents/providers/workspaces/effects
                          ├─ QA/supervision/acceptance
                          └─ delivery/release/recovery
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
      libRSI semantic workflows          target profiles/effect adapters
      (no operational authority)         (software, neutral fixture, external)
```

Codex app-server is a provider substrate behind a Factory adapter. The
domain-neutral typed client comes from `estill01/utils`; Factory owns provider
reservation, assignment, retry, bounded context, restart, QA, supervision, and
acceptance. Patent Studio-specific gateways, schemas, workflows, and authority
remain in Patent Studio. In a Factory-managed composition, Factory alone owns
the app-server process. In standalone consumer mode, the consumer may provide
an already managed provider, but exactly one host owns each process.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Tracker authoring/execution/supervision | `author-implementation-trackers/`, `implement-tracker-blocks/`, `supervise-tracker-runs/` | reuse and integrate |
| Runtime mission/work authority | `runtime/src/software_factory/` and migrations | reorganize incrementally; do not create a second runtime |
| Operational QA and acceptance | `runtime/src/software_factory/qa.py`, `acceptance.py`, `audit.py` | adapt behind stable core contracts |
| Agents and execution | `agents.py`, `execution.py`, `providers.py`, `controller.py` | split by owner without semantic duplication |
| Release and recovery | `release.py`, `recovery.py`, `reconciliation.py` | preserve as authoritative effects |
| Codex app-server client | `dashboard/server/src/software_factory_dashboard/app_server.py` | extract generic transport/process code to `estill01/utils`; retain Factory projections locally |
| Embedded/service structural conformance | `estill01/utils` `embedded-service-contract` | consume only after exact utils Block 10 acceptance; Factory retains engine semantics and state |
| Runtime compatibility metadata | `estill01/utils` `runtime-manifest` | consume only after exact utils Block 11 acceptance; descriptive only |
| libRSI integration | current `evolution.py`, `learning.py`, `reflection.py`, and immutable libRSI dependency | map then remove duplicate generic semantics |
| Dashboard/operator views | `dashboard/` | project one runtime; never become authority |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| v2 implementation plan | source branch `b34cdd9fab6830bf2ee5b9ac457e48914082e660` plus this tracker-authoring delta | adopt | 0–12 | convert phases into accepted implementation |
| Existing runtime and 70+ acceptance cases | same source revision | reuse/remediate | 0–12 | classify currentness, gaps, and cutovers |
| Existing dashboard app-server client | same source revision | adapt/extract | 4 | separate generic client from Factory projections |
| Shared utilities program | `estill01/utils` canonical `docs/tracker.md`; resolve exact accepted producer revisions at consumption | consume, never implement from Factory | 4, 9, 12 | bind app client after utils B9, embedded/service after B10, runtime manifest after B11, and terminal qualification after utils B12–B15 with the Block 16 no-license/unpublished terminal posture |
| Current libRSI main | resolve exact accepted revision at Block 7 start | consume | 7 | pin only accepted contracts |
| Historical detailed trackers | repository history | preserve as evidence | 0 | map retained owners; do not replay accepted proof |

## 5. Scope, non-goals, and proportionality

### In scope

- One engine, embedded and standalone hosts, mission/work scheduling, providers,
  workspaces/effects, QA, supervision, acceptance, delivery, release/recovery,
  libRSI integration, target profiles, APIs, migration, and terminal proof.

### Out of scope

- Public hosted deployment, billing, tenant administration, a generic AI
  gateway, a replacement for Codex app-server, Patent Studio-specific code,
  libRSI semantic duplication, or a shared universal authority/ledger.

### Proportionality

Extract to `estill01/utils` only code that is domain-neutral, independently
versionable, imports none of the three products, and has two concrete consumers
or an imminent active second implementation. Everything else remains behind
Factory modules or target profiles.

### Shared-utility dependency contract

The utils repository is a producer only. Its Blocks 9, 10, and 11 provide the
first accepted handoff points for `codex-app-server-client`,
`embedded-service-contract`, and `runtime-manifest`, respectively. Utils Blocks
12–13 prove isolated distribution and neutral composition; Blocks 14–15 qualify
the frozen technical package set and authority/downstream boundary. Software
Factory owns all downstream adapters, pins, migrations, tests, and acceptance.
Unavailable utility work blocks only its mapped adoption; earlier and independent
Factory Blocks continue. Final Factory acceptance records exact producer commit,
distribution/version, artifact and compatibility roots, and the Block 16
no-license/unpublished posture. No public release or redistribution of a dependent
artifact is implied or authorized.

## 6. Block execution contract

### Required implementation and supervision skills

Tracker activation is a documentation and control-plane transition; it does not
start Block 0. The eventual SFV2 implementation thread must invoke
`implement-tracker-blocks` against the exact active canonical index and detailed
tracker for the full requested `SFV2/B0`–`SFV2/B12` range. Before that thread's
first implementation-producing Block 0 effect, initialize one isolated
`supervise-tracker-runs` group bound to its exact thread, active branch, tracker
hash, requested range, and Block 0. These skills preserve the tracker and
supervision contracts; they do not expand implementation authority or permit a
monitor to mutate the implementation target.

1. Execute Blocks 0–12 in dependency order from the exact integrated v2 branch.
2. Re-read the Block and live repository before editing; preserve concurrent
   user work and accepted evidence.
3. Mark the Block `in-progress` at its first implementation-producing effect.
4. Run the three most discriminating negative cases before freezing a candidate.
5. Freeze one exact candidate, run focused then mapped proof, and obtain one
   distinct exact-revision audit before acceptance.
6. On rejection, correct only supported findings and rerun affected proof. A
   second material rejection triggers bounded causal review before another
   candidate.
7. Passing provider calls, tests, builds, commits, or releases cannot substitute
   for operator-visible outcome proof.
8. Push every accepted Block checkpoint without force; a push is durability,
   not terminal completion.
9. A Block Stop is an internal boundary. Continue automatically while the
   requested range remains nonterminal and a safe frontier exists.

### Supervised execution and monitoring

Each implementation target uses one isolated `supervise-tracker-runs` group
bound to its exact thread, mission source, tracker hash, branch, range, and
active Block. The watcher observes changed state; distinct semantic review owns
material judgment; a fix executor may act only from a bounded reviewed plan.
Monitoring never implements target work, combines repositories, treats
unchanged state as a defect, or narrows the tracker range. No supervision group
for this tracker may inspect Patent Studio patent content.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Inputs and dependency versions: `<paths/versions/hashes>`
- Outputs: `<paths/artifact roots>`
- Focused validation: `<commands/results>`
- Mapped validation: `<plan/commands/results>`
- Candidate freeze: `<exact revision/currentness>`
- Remediation closure: `<finding/change/proof or not-applicable>`
- Provider/resource posture: `<adapter/live boundary and bounds>`
- Independent review: `<distinct reviewer and evidence root>`
- Retained open work: `<items or none>`
- Post-block audit: `<accepted/reopened/blocked>`
- Git durability: `<commit/push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Exact baseline, owner inventory, and cutover map | — | `accepted` |
| 1 | Operational authority and persistence boundaries | 0 | `accepted` |
| 2 | One embedded/standalone engine contract | 1 | `accepted` |
| 3 | Work graph, scheduling, continuation, and concurrency | 1, 2 | `accepted` |
| 4 | Agents and replaceable provider runtime | 2, 3 | `accepted` |
| 5 | Target profiles, workspaces, and authoritative effects | 3, 4 | `accepted` |
| 6 | QA, supervision, acceptance, and outcome closure | 3–5 | `accepted` |
| 7 | libRSI semantic integration and duplicate removal | 1, 3, 6 | `accepted` |
| 8 | Delivery, release, recovery, and reconciliation | 5–7 | `accepted` |
| 9 | Service/API/operator and deployment-ready boundaries | 2, 6, 8 | `accepted` |
| 10 | Neutral content profile and external-extension proof | 5–9 | `accepted` |
| 11 | Migration, compatibility cutover, and legacy retirement | 6–10 | `in-progress` |
| 12 | Frozen terminal qualification and handoff | 11 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12`

## Block 0 — Freeze exact baseline and migration map

Status: `accepted`

### Objective

Bind the exact v2 source, current behavior, accepted evidence, module/table
owners, and every required migration/deletion condition.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one executable source-to-target map.
- Potential capability loss or regression: stale or overbroad inventory could
  erase proven behavior.
- Protected-capability effect: accepted skills/runtime evidence remains valid
  until an affected owner changes.
- Architecture and operating-model effect: freezes the branch before physical
  moves.
- Tradeoff and source evidence: v2 plan sections 8–11 require incremental
  boundary proof rather than a mechanical rewrite.

### Inputs and dependencies

- Exact source branch and all current detailed trackers, runtime migrations,
  acceptance matrix, dashboard client, and libRSI pin.

### Required work

- Record current tests/builds, modules/tables, active authorities, duplicate
  owners, compatibility routes, generated residue, and dirty/remote posture.
- Map each path as retain, move, adapt, replace, retire, or evidence-only.

### Scope and non-goals

- In scope: baseline and migration map.
- Not in scope: production code movement or semantic cutover.
- No new registry or database is authorized.

### Deliverables and recorded state

- Rooted baseline, owner map, compatibility matrix, and changed-test plan.

### Resource and economy contract

Read/hash each source once; reuse current accepted evidence after cheap
currentness checks.

### QA and independent review

Distinct review checks completeness, owner conflicts, protected behavior, and
unsupported completion claims.

### Acceptance

- Every current production path and table has one target owner and disposition.

### Negative tests

- Reject an unmapped active writer, duplicate authority, stale branch binding,
  or accepted proof silently reclassified as current implementation.

### Completion evidence

- Acceptance posture: `accepted`; exact independent review under range binding
  `RANGE-SFV2-B0-B12-3901D4F-2079C81D` accepted the unchanged candidate at
  commit `3901d4f6a88ed6c34f6a584c12260cfa84a36920`, tree
  `53a3dc1fe74c9b9932ee2b2b0910c8165a385aa1`, with no P0–P2 findings.
- Frozen source: branch `agent/software-factory-v2-native-refactor`, commit
  `63bb9f3a69bcb5dba0e4b2fe652dce5af7169ae4`, tree
  `79d758db7e36aa45a34d0af96b676344321e953b`, with local/remote parity at
  freeze.
- Implementation checkpoint: commit
  `bd33086f35f673386a4ad0ff2bcafc340c937323`, tree
  `b4d3cf7ac41593ebbd2811b07cc481ae5fbe5fe9`.
- Deliverables:
  `docs/software-factory-v2-baseline.json`,
  `docs/software-factory-v2-baseline-and-migration-map.md`, and
  `runtime/tests/test_v2_baseline_map.py`.
- Focused proof at current head:
  `uv run --python 3.11 --with pytest python -m pytest
  runtime/tests/test_v2_baseline_map.py -q` — `17 passed`; the negative cases
  reject an unmapped active path, omitted source-derived module or table,
  duplicate active authority, stale branch or remote binding, missing exact
  tracker identity, and accepted proof relabeled as current implementation.
- Artifact checks: focused Ruff and format pass; the JSON manifest parses; the
  detailed tracker passes the 13-Block full structural verifier.
- Currentness reconciliation: the three Block 0 artifact files are unchanged
  from implementation checkpoint `bd33086f35f673386a4ad0ff2bcafc340c937323`
  and have SHA-256 roots `57a6682dd81810197416fd97634dcc94c49d89f58bae902d323e86930ba03fc9`,
  `5915f74c881e315d0c5b4cc96c08b97e6db983806b925bc2ec6e625dbaeb2a3e`,
  and `8b0cd3c130930a7c899ff5f0cda934d4887bf37b28c246e562da2d783b58f63a`.
  Independent review found no remaining material issue in those artifacts and
  requested only the narrow audit-state correction recorded at `3901d4f`.
  Fresh review of that exact tracker-only successor supplied the pending
  independent acceptance evidence without rerunning a broad suite.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Frame identity: this tracker, Block 0, SHA-256
    `c2b8110d2cf11edc3d7f52ecc0c6112f0f60ba9d091b6cbeb2e15e9b6bbb3851`.
  - Capability added or preserved: one executable source-to-target inventory
    that detects missing paths, duplicate authority, and stale evidence.
  - Paths compared: prose-only local map; bounded-general manifest plus readable
    map; runtime registry/database owner.
  - Selected level and owner: bounded-general evidence seam owned by the Block 0
    documentation and validator; it proves completeness without creating runtime
    authority.
  - Protected-capability result: accepted historical evidence is preserved and
    cannot be relabeled as current implementation.
  - Rejected alternatives: prose-only cannot reject omissions; a runtime
    registry/database is speculative and crosses the Block Stop.
  - Tradeoffs and uncertainty: the frozen map intentionally retains assigned red
    baselines for later Blocks rather than claiming a green runtime.
  - Frozen-candidate proof: commit `bd33086f35f673386a4ad0ff2bcafc340c937323`,
    tree `b4d3cf7ac41593ebbd2811b07cc481ae5fbe5fe9`, with the three artifact roots
    recorded above and the current 17-test focused result.
- Known red baseline remains assigned rather than hidden: runtime collection,
  whole-runtime Ruff/format/mypy, dashboard test stability, dependency audit,
  and legacy upload-residue gates retain their explicit successor Blocks.
- Independent review: `/root/sfv2_b0_exact_review` accepted exact revision
  `3901d4f6a88ed6c34f6a584c12260cfa84a36920` under the current full-range
  binding after independently confirming the three artifact roots, clean pushed
  parity, remediation history, full `SFV2/B0`–`SFV2/B12` scope, and absence of
  unsupported completion or downstream acceptance claims.
- Retained open work: none in Block 0; the known red baseline remains explicitly
  assigned to Blocks 1, 9, 11, and 12 rather than hidden or relabeled green.
- Decision/continuation posture: Block 0 accepted; continue automatically to
  dependency-eligible Block 1 without narrowing the requested full range.
- Post-block audit: accepted; every frozen production path and table has one
  target owner and disposition, negative cases reject missing or duplicate
  authority, and no operational writer or persistence owner moved in Block 0.
- Git durability: implementation checkpoint `bd33086` and accepted review
  candidate `3901d4f` are pushed with local/remote parity; this tracker-only
  acceptance record must be committed and pushed before any Block 1 effect.

### Stop

Stop before changing operational authority or persistence.

---

## Block 1 — Establish operational authority and persistence boundaries

Status: `accepted`

### Objective

Create one explicit operational core for missions, programs, obligations,
work, authority, QA, acceptance, delivery, and recovery.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one transactional owner for coupled invariants.
- Potential capability loss or regression: over-consolidation could erase
  useful module boundaries.
- Protected-capability effect: full-range continuation, event history, incident
  recovery, and release authority remain intact.
- Architecture and operating-model effect: modular monolith with one SQL
  deployment and explicit internal APIs.
- Tradeoff and source evidence: v2 plan sections 4–7 choose consistency over
  premature service decomposition.

### Inputs and dependencies

- Block 0.

### Required work

- Define and migrate internal owner boundaries and dependency rules.
- Remove conflicting migrations/duplicate writers only after parity proof.

### Scope and non-goals

- In scope: core module/persistence ownership.
- Not in scope: hosts, providers, profiles, or libRSI semantic cutover.
- Do not create a universal entity model.

### Deliverables and recorded state

- Core packages, migration lineage, dependency checks, and owner documentation.

### Resource and economy contract

Use incremental migrations and existing tests; no broad physical move before
its owner proof.

### QA and independent review

Test transaction/fencing/restart invariants and review authority uniqueness.

### Acceptance

- One active writer exists for every operational lifecycle concern.

### Negative tests

- Reject dual active migrations, reverse module dependencies, partial commit
  across coupled state, or semantic records used as operational rows.

### Completion evidence

- Acceptance posture: `accepted`. The first exact-revision review returned
  `REVISE`; its preserved candidates remain unaccepted. The bounded P1/P2
  correction was independently accepted at its exact pushed revision.
- Preserved reviewed history: implementation commit
  `79adac40ffb5650ed46fe78f73d091109b7602e4`, tree
  `0f82f5b0ed23b2e9390505cc755660d54e60df37`, and evidence candidate
  `e9bb020848c1d34ba6ed805487512dbf87404467` are pushed and retained
  unchanged. They are rejected evidence, not accepted checkpoints.
- Accepted correction checkpoint: branch
  `agent/software-factory-v2-native-refactor`, commit
  `2172dc4b112ad836bff0a292f63adb74cf61d3c0`, tree
  `99e78ef5c1050739a0e7776f6da700a930288671`, pushed with a clean worktree
  and zero local/remote divergence.
- Migration and persistence boundary:
  `software_factory.database.Database` is the one implementation;
  `DatabaseStore` and `Store` are exact compatibility aliases. The active
  migration catalog is contiguous and file-exact from 1 through 20, the
  conflicting `0008_supervision.sql` path is retired, and migration 19
  reconciles runtime-referenced acceptance, observation, learning, reflection,
  hypothesis, and experiment tables without reusing legacy semantic rows.
- Operational owner boundary:
  `runtime/src/software_factory/ownership.py` exhaustively registers all 89
  tables written by top-level runtime Python, uses the real
  `acceptance_probe_results_v2` name, declares exactly one primary module for
  each table, and names the bounded coordinators allowed to join its
  transactions. The proof extracts `INSERT`, `INSERT OR ...`, `UPDATE`, and
  `DELETE` targets and requires exact set equality rather than skipping
  undeclared writes. `CoreService` composes one shared owner graph;
  `AdvancedServices`, API, daemon, CLI, and skill entrypoints reuse that graph
  instead of creating alternate supervision, learning, operations, reporting,
  migration, release, or recovery owners.
- Owner documentation:
  `docs/software-factory-v2-operational-ownership.md` records dependency
  direction, lifecycle/table ownership, migration lineage, semantic separation,
  and the later Block 2/5/7/11 cutovers. It explicitly rejects a universal
  entity model.
- Coupled-transition safety: nested database transactions use savepoints on the
  active connection, and reads inside the transaction reuse that connection.
  The real operator path now re-reads the decision, invokes the owning service,
  records its audit event, and marks the decision applied inside one outer
  transaction. A focused injected failure after the schedule effect proves the
  effect and event roll back before the decision is marked failed; a successful
  decision applies once and idempotent re-entry does not repeat the effect.
- Focused Block 1 pytest evidence is recorded verbatim in
  `docs/sfv2-b1-focused-evidence.json`, SHA-256
  `5ebdbad0b5719b9e79ca7eff30fc28e496af050ea2b8a1f31bcb73990ff872f6`.
  Its exact 13-file command over core, composition, controller, execution, QA,
  supervision, acceptance, learning, migration, API, reporting, entrypoint,
  and boundary tests completed `83 passed` with one harmless legacy pytest
  collection warning. Repository collection completed `159 tests collected`.
  `runtime/tests/test_v2_entrypoints.py` is explicitly excluded because legacy
  console-script cutover belongs to Block 2 and crosses the Block 1 Stop; no
  broad runtime matrix was run.
- Static baseline closure:
  `ruff check runtime/src runtime/tests` passes; `ruff format --check
  runtime/src runtime/tests` reports all 78 files formatted; mypy reports no
  issues across all 52 `runtime/src/software_factory` modules. Mechanical
  formatting closes the exact Block 0-assigned static debt and changes no
  lifecycle ownership.
- Negative proof:
  `runtime/tests/test_operational_boundaries.py` rejects inert or duplicate
  migrations, applied checksum/name drift, unknown/gapped histories, reverse
  persistence/service or service/host imports, any unregistered or undeclared
  runtime writer, partial nested commits, partial real operator effects, and
  operational foreign-key dependence on semantic tables. The advanced
  integration proof also asserts that the retired alternate
  supervision/adaptive tables are absent.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Frame identity: this tracker, Block 1 planning bytes at SHA-256
    `0ab15838469d8fa62140b7f36522152e79aef5f4a2e45514b2434aba525b0fa4`.
  - Capability added or preserved: one transactional persistence owner and one
    explicit lifecycle-owner graph while preserving event history, incident
    recovery, release authority, and full-range continuation.
  - Paths compared: retain implicit multi-writer composition; collapse all
    lifecycle state into one universal service/model; retain modular services
    with one SQL deployment, declared primary owners, and bounded transaction
    participants.
  - Selected level and owner: the modular-monolith boundary owned by
    `Database`, the lifecycle services, and `CoreService` composition.
  - Protected-capability result: no host/provider/profile/libRSI cutover and no
    accepted historical evidence rewrite occurred.
  - Rejected alternatives: implicit writers cannot reject authority drift; a
    universal entity model erases lifecycle/evidence distinctions; premature
    host exposure crosses the Block 1 Stop.
  - Tradeoffs and uncertainty: compatibility aliases remain callable but are
    the same class identity; later Blocks still own host exposure, semantic
    cutover, delivery qualification, and legacy retirement.
- Independent review: the preserved `e9bb020848c1d34ba6ed805487512dbf87404467`
  review returned two P1 findings (incomplete owner registry and non-atomic
  operator effects) plus one P2 evidence-record finding. The existing
  independent reviewer `/root/sfv2_b0_exact_review` then reviewed exact
  correction `2172dc4b112ad836bff0a292f63adb74cf61d3c0`, independently
  reconciled `89 written = 89 owned`, reproduced `83 passed`, Ruff, formatting,
  and mypy, and returned `ACCEPT` with no P0, P1, or P2 findings.
- Retained open work: none in Block 1. Blocks 2–12 remain unaccepted and inside
  the current full requested range.
- Decision/continuation posture: advance automatically to dependency-eligible
  Block 2 without narrowing the full bound range.

### Stop

Stop before exposing embedded or service hosts.

---

## Block 2 — Implement one embedded and standalone engine contract

Status: `accepted`

### Objective

Expose the same engine through typed in-process and standalone-service facades.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: products can embed Factory or submit missions to a
  service without semantic drift.
- Potential capability loss or regression: host-specific state could become a
  second controller.
- Protected-capability effect: one mission identity, range, authority, and
  terminal reducer survive mode changes and restart.
- Architecture and operating-model effect: thin hosts over the core.
- Tradeoff and source evidence: direct user requirement and v2 plan sections
  1–3 and 6.1.

### Inputs and dependencies

- Block 1.

### Required work

- Define engine/start/status/continue/cancel/outcome contracts and host adapters.
- Prove durable idempotent submission, event streaming, restart, and transfer
  between permitted hosts.

### Scope and non-goals

- In scope: local embedded and bounded standalone hosts.
- Not in scope: public multi-tenancy, billing, or hosted deployment.
- Do not duplicate the core state machine in transport code.

### Deliverables and recorded state

- Engine API, service facade, schemas, local entrypoints, and equivalence tests.

### Resource and economy contract

Use one canonical fixture across both hosts and compare semantic/operational
roots.

### QA and independent review

Review state ownership, idempotency, restart, cancellation, and error parity.

### Acceptance

- The same mission can be driven through either host with equivalent current
  state and outcome.

### Negative tests

- Reject session-only state, host-specific acceptance, duplicate submission,
  unbounded event retention, or restart loss.

### Completion evidence

- Start posture: `in-progress` from clean pushed Block 1 acceptance successor
  `3429a4be1ba019736a9c04a0bdf26c92cfe49bf7` on branch
  `agent/software-factory-v2-native-refactor`, with zero local/remote
  divergence and the full `SFV2/B0`–`SFV2/B12` range preserved.
- Implemented bounded candidate: `FactoryEngine` defines typed start, status,
  continue, cancel, outcome, and cursor/limit-bounded event operations.
  `EmbeddedFactoryHost` and `StandaloneFactoryService` delegate those exact
  operations without retaining host-local mission state. The loopback API
  exposes the same service operations at `POST /api/engine/{operation}`.
- Durable identity and restart: additive migration
  `0021_engine_host_contract.sql` stores only the canonical request-root and
  idempotency-key-to-mission binding. Mission creation, binding, and submission
  event commit atomically; concurrent exact duplicates resolve to one mission,
  while a changed request under the same key fails closed. A restarted runtime
  and the other host recover the same mission ID, state, frontier, events, and
  outcome.
- Lifecycle ownership: cancellation routes through `MissionService`, refuses
  to strand an active provider execution, and produces canonical mission state
  and an audit event. `continue_mission` is deliberately a durable reattachment
  to the current safe frontier; Block 3 owns autonomous scheduling and this
  candidate starts no provider effect.
- Contract and ownership documentation:
  `docs/software-factory-v2-engine-contract.md`, SHA-256
  `df9ba45729d2576ad65daa3999da20b4b7cecdf2926b1d215fc12b1134c24692`,
  records the operation schemas, host/process shape, loopback route, and Stop.
  The executable ownership registry reconciles `90 written = 90 owned` after
  adding the one Block 2 table.
- Focused evidence: `docs/sfv2-b2-focused-evidence.json`, SHA-256
  `6a5254b753933b10c4cd5c44259f5e958431372ebb261299a48cad39205228e7`,
  records the exact seven-file command and `27 passed`, repository collection
  at `164 tests`, Ruff and 83-file format success, and mypy success across 56
  source files. No broad runtime suite was run.
- Installed-entrypoint proof: an ephemeral wheel for version `2.0.0.dev6`,
  SHA-256 `f73018904fb836b3b23e04d15fbfad3f939d6d0306e4b3dc6d03e2b766e9cb6b`,
  installed into an isolated environment; `software-factory`,
  `software-factoryd`, `software-factory-api`, and `sf-skill` were present and
  all four installed `--help` probes passed. Only the bounded service API is a
  new target; the CLI, daemon, and skill targets remain on their pre-Block-2
  owners so adaptive ticking and provider dispatch are not activated across
  this Stop. The wheel is qualification evidence, not a release artifact.
- Producer boundary: Block 2 does not consume `embedded-service-contract`,
  `runtime-manifest`, or any other utils artifact. Those accepted producer
  outputs remain reserved for their tracker-assigned Blocks 4, 9, 11, and 12.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Capability added or preserved: one durable mission identity can be started,
    inspected, reattached, cancelled, and observed through either permitted
    local host without changing operational or terminal truth.
  - Paths compared: duplicate host controllers; a transport-owned session
    model; thin hosts over the Block 1 engine and state plane.
  - Selected level and owner: thin hosts over `FactoryEngine`, `Database`, and
    the canonical lifecycle services.
  - Protected-capability result: host transfer and restart retain mission ID,
    state version, safe frontier, event sequence, and outcome; no host-specific
    acceptance or provider-success shortcut exists.
  - Rejected alternatives: host controllers duplicate authority, session state
    loses restart identity, and pulling the utils structural contract into this
    Block violates the assigned consumer lanes.
  - Tradeoff and uncertainty: `continue_mission` reattaches but does not yet
    schedule; Block 3 owns atomic frontier execution, and Block 9 later adopts
    the accepted structural package and hardens the service boundary.
- Preserved reviewed history: exact candidate
  `891ae0723c8b5d522f92f95ab8f1aae63a00851a` returned `REVISE` with two P1
  findings and no P0/P2: cancellation did not fence a later dispatch, and the
  three legacy entrypoint cutovers activated scheduling/provider paths beyond
  the Block 2 Stop. The bounded correction checks active mission state both
  before dispatch preparation and atomically inside reservation; a negative
  cancel/dispatch race plus restart probe proves a cancelled mission never
  reaches the provider. The three entrypoint cutovers are reverted while the
  bounded service entrypoint remains. That candidate is rejected evidence and
  remains preserved.
- Accepted correction checkpoint: branch
  `agent/software-factory-v2-native-refactor`, commit
  `c32ac92f0df3c0c884996da8911aa18d8014c7df`, tree
  `0644e8b121c32d9b0a56fa2c13326b0442d9d136`, pushed with a clean worktree
  and zero local/remote divergence.
- Independent review: the existing reviewer `/root/sfv2_b0_exact_review`
  reviewed exact correction `c32ac92f0df3c0c884996da8911aa18d8014c7df`,
  reproduced `27 passed`, verified both cancellation race orderings and the
  installed entrypoint delta, and returned `ACCEPT` with no P0, P1, or P2
  findings.
- Acceptance posture: `accepted`. Retained open work: none in Block 2; Blocks
  3–12 remain unaccepted inside the current full range. Continue automatically
  to dependency-eligible Block 3.

### Stop

Stop before autonomous scheduling or provider effects.

---

## Block 3 — Implement work graph, scheduling, continuation, and concurrency

Status: `accepted`

### Objective

Turn authorized missions into durable dependency-safe work that continues while
useful safe work exists.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: autonomous next-work selection and parallel safe
  execution.
- Potential capability loss or regression: scheduler heuristics could narrow
  mission range or race authority.
- Protected-capability effect: obligations survive failed attempts; safe
  frontier and no-early-return behavior remain controlling.
- Architecture and operating-model effect: atomic work selection, leases,
  fencing, budgets, and reassignment in the core.
- Tradeoff and source evidence: v2 plan non-negotiable goals and existing
  continuation/scheduling owners.

### Inputs and dependencies

- Blocks 1–2.

### Required work

- Implement program revisions, dependency graph, ready frontier, assignments,
  concurrency/resource policy, heartbeats, expiry, and restart.

### Scope and non-goals

- In scope: operational work selection and scheduling.
- Not in scope: provider implementation or semantic improvement selection.
- No generic distributed scheduler service.

### Deliverables and recorded state

- Work graph, lease/fencing runtime, continuation reducer, and crash fixtures.

### Resource and economy contract

Bound parallelism and retries; unchanged waiting produces no repeated work.

### QA and independent review

Test race/crash/stale/partial/failure scenarios and review range preservation.

### Acceptance

- Maximum safe useful work proceeds; failed attempts leave obligations open.

### Negative tests

- Reject stale assignment effects, lease theft, unsafe overlap, false blocked
  state with a nonempty frontier, or Block Stop as mission completion.

### Completion evidence

- Start baseline: clean pushed Block 2 acceptance successor
  `53c926aaf03c5cc88ce2420273661e13df39de82`; Blocks 0–2 accepted and Block 3
  is the sole dependency-eligible frontier.
- Implemented bounded scheduling policy: `SchedulingPolicy` derives positive
  `max_parallel`, `max_dispatch_per_tick`, and `max_attempts_per_work` limits
  from canonical `missions.resource_limits_json`, with bounded defaults of
  4/4/3. Mission creation validates the known policy fields before persistence;
  unrelated resource-limit fields remain owned by their later consumers.
- Atomic and durable enforcement: attempt eligibility is applied before the
  dependency-safe, scope-compatible maximal frontier is constructed; continuation
  then bounds that useful frontier by current capacity. The controller applies
  the tick limit and rechecks both parallel
  capacity and attempt count inside its `BEGIN IMMEDIATE` reservation before
  creating an execution, so concurrent direct dispatchers cannot oversubscribe.
  Restart reconstructs the same policy and active capacity from durable state.
- Continuation and range preservation: a capacity-full mission waits for active
  work rather than advertising dispatch. Exhausted work is routed to diagnosis
  or replanning without closing its obligation or repeating the same attempt.
  Program proposals validate accepted-history shape and cannot omit any accepted
  work recorded by their current parent revision; the program's requested range
  remains canonical and unchanged.
- Existing graph/runtime audit: the canonical work graph retains acyclic
  dependency enforcement, acceptance-gated readiness, maximal nonconflicting
  writable-scope selection, durable assignments, hierarchical leases,
  generation fencing, heartbeats, expiry recovery, and stale-result rejection.
  Block 3 adds no alternate scheduler, state store, or provider authority.
- Focused evidence: `docs/sfv2-b3-focused-evidence.json`, SHA-256
  `433b7323bc87c17cdbc8b14144398eba41ea134456499f7703ca1bb9f354cc4c`,
  records the four-file command and `39 passed`, repository collection at `172
  tests`, Ruff and 84-file format success, and mypy success across 57 source
  files. No broad runtime suite was run.
- Artifact proof: an ephemeral wheel for version `2.0.0.dev6`, SHA-256
  `38182c2befc00bc1b29213172ec605d5ba4673053879a1598747f608d50b8f9b`,
  contains the scheduling, work-item, controller, continuation, and program
  modules. It is local qualification evidence, not a release artifact.
- Negative proofs: under `max_parallel=1`, two disjoint concurrent dispatchers
  create exactly one active execution and one deterministic-provider request;
  a restarted runtime waits at zero capacity and dispatches the next safe item
  only after capacity releases; an expired final attempt remains an open
  obligation and rejects another direct dispatch; a revision that drops prior
  accepted history fails before persistence. An exhausted high-priority item is
  removed before scope selection, so a conflicting lower-priority unattempted
  item remains visible and dispatches.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Capability added or preserved: the engine advances the maximum bounded safe
    frontier, survives restart, and never treats capacity, retry exhaustion, or
    a Block Stop as mission completion.
  - Paths compared: tick-only advisory limits; a separate scheduler service;
    durable policy with atomic reservation enforcement.
  - Selected level and owner: durable policy interpreted by the canonical
    continuation and controller services, with the database transaction as the
    final concurrency fence.
  - Protected-capability result: requested range and accepted history cannot
    narrow, failed attempts leave obligations open, and stale lease/result
    fencing remains authoritative.
  - Rejected alternatives: advisory-only limits race, a scheduler service
    duplicates state ownership, and provider-owned retry truth crosses the Block
    3 Stop.
  - Tradeoff and uncertainty: defaults intentionally bound local concurrency;
    Block 4 supplies replaceable live providers while preserving these Factory
    reservations and budgets.
- Preserved reviewed history: exact pushed candidate
  `908fd11f09513e926fb6b020bd14777a67da5caa`, tree
  `fd02d9ef028383b4fa9ef859ac08256d3bc0556b`, returned `REVISE` with one P1
  and no P0/P2. The reviewer proved that filtering attempt-exhausted work after
  greedy scope selection let an exhausted high-priority item hide useful
  conflicting work. That candidate is rejected evidence and remains preserved.
- Corrected candidate posture: `candidate`; attempt exhaustion is now excluded
  before maximal-frontier scope selection and the exact mixed-frontier
  regression passes.
- Accepted correction checkpoint: branch
  `agent/software-factory-v2-native-refactor`, commit
  `c2bc0a2174d077dbe49a94fb58fd61a90d0613fa`, tree
  `7d7e04dafccc48d2ce2acaebc9b74003ec590f46`, pushed with a clean worktree
  and zero local/remote divergence.
- Independent review: the existing reviewer `/root/sfv2_b0_exact_review`
  reviewed exact correction `c2bc0a2174d077dbe49a94fb58fd61a90d0613fa`,
  reproduced `39 passed`, reran the mixed-frontier proof, and returned `ACCEPT`
  with no P0, P1, or P2 findings. Atomic capacity/attempt fencing, restart,
  dependency/scope safety, obligation preservation, accepted-history lineage,
  immutable requested range, and the Block 3 Stop remain sound.
- Acceptance posture: `accepted`. Retained open work: none in Block 3; Blocks
  4–12 remain unaccepted inside the current full range. No utils artifact is
  consumed and no live agent/provider lifecycle is started in this Block.
  Continue automatically to dependency-eligible Block 4.

### Stop

Stop before live agent/provider lifecycle.

---

## Block 4 — Implement agents and replaceable providers

Status: `accepted`

### Objective

Run attributable bounded agents through Codex app-server, local process, and
external-agent providers without giving providers mission authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: real replaceable worker execution, restart, and
  reattachment.
- Potential capability loss or regression: provider completion or approval
  could bypass Factory QA/authority.
- Protected-capability effect: assignments, reservations, budgets, cancellation,
  and review separation remain Factory-owned.
- Architecture and operating-model effect: provider adapters implement one core
  contract; shared app-server mechanics move to `estill01/utils`.
- Tradeoff and source evidence: v2 plan sections 4.4 and 6.1 plus the existing
  dashboard app-server client.

### Inputs and dependencies

- Blocks 2–3 and an exact pushed `codex-app-server-client` revision accepted
  by utils Block 9.

### Required work

- Pin the exact accepted shared client; extract/move the generic source through
  the utils owner rather than retaining a second Factory implementation.
- Implement Factory provider adapters, process ownership, bounded context,
  callbacks, retries, cancellation, restart/reattachment, and attribution.

### Scope and non-goals

- In scope: provider lifecycle and Factory mappings.
- Not in scope: Patent Studio gateways, public app-server proxying, or provider
  truth/acceptance.
- Experimental transports remain optional.

### Deliverables and recorded state

- Shared-client pin, provider adapters, compatibility matrix, fake server, and
  bounded real-provider diagnostic.

### Resource and economy contract

Offline fakes and replay are normal; any live provider check is separately
bounded and recorded.

### QA and independent review

Review process ownership, schema pinning, approvals, cancellation, secrets,
restart, and provider-success/acceptance separation.

### Acceptance

- Each provider can execute the same assignment contract and return evidence;
  only Factory routes its consequences. The shared-client pin binds its utils
  commit, distribution/version, artifact hash, and protocol/schema root.

### Negative tests

- Reject two process owners, provider objects in canonical mission state,
  app-server turn completion as acceptance, stale callback, approval bypass, or
  consumer-domain code in the OSS adapter. Also reject a pre-utils-B9 client,
  mutable branch dependency, copied utility source, or stale producer root.

### Completion evidence

- Start baseline: clean pushed Block 3 acceptance successor
  `61ddd8d986f7d61e13b7ad399f9d96458b1a4b42`; Blocks 0–3 accepted and Block 4
  is the sole dependency-eligible frontier.
- Start checkpoint: clean pushed tracker transition
  `924bae3e8a9850708c1e55763b082fb85dd31386`; no Block 5 effect began.
- Accepted producer handoff: consume only `codex-app-server-client==0.1.0`
  from utils producer revision `a5659745a7cbcbb002b5f06051f6ed9826f721a7`.
  Bind its accepted source commit, package tree/content root, wheel hash,
  qualification/currentness roots, API/protocol roots, and unpublished/no-license
  boundary in a Factory-owned pin. Do not resolve by registry name/version, copy
  package source, modify utils, consume the Block 9 structural packages, or
  retire the dashboard path reserved for Block 11.
- Exact Factory-owned pin: the packaged pin binds producer revision
  `a5659745a7cbcbb002b5f06051f6ed9826f721a7`, accepted source commit/tree
  `08c416da4202b7036110e33e43d34ea590054e2e` /
  `794650275e9a583c9f47276a271f65cc1020c4e8`, package tree
  `17772f61da62b41d6d3551deebc474792aafe922`, qualification matrix/root,
  version `0.1.0`, wheel SHA-256 `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`,
  wheel content root, and exact Codex/protocol roots. Wheel verification rejects
  an incorrect filename, symlink, byte hash, content root, member count, or
  uncompressed byte count before import; import then verifies version and
  pinned protocol identity. Bare registry and copied-source resolution remain
  prohibited, and the unpublished/no-license boundary remains explicit.
- Provider lifecycle: deterministic, local-process/Codex CLI, exact app-server,
  and injected external-agent providers implement one `ProviderRequest` /
  `ProviderObservation` contract. The registry rejects duplicate process-owner
  keys, closes replacement owners, and lets `CoreService` close provider-owned
  resources. Provider prompt/output/event/callback/operation bounds remain
  explicit; Factory scheduling and attempt limits from Block 3 remain the retry
  authority.
- Exact app-server adapter: one owned async loop contains typed stdio clients,
  process/session lifecycle, durable execution-to-thread/turn mapping,
  restart/reattachment, polling, and exact cancellation. Canonical state stores
  only JSON identities and exact producer roots—not client/session/callback
  objects or callback tokens. Command/file approval callbacks are declined;
  external input interrupts and fails closed. A completed turn returns
  `provider_success_only` evidence and leaves work acceptance pending.
- Compatibility and diagnostic: `docs/software-factory-v2-provider-compatibility.md`,
  SHA-256 `ea2a8581327c2282c9f2cbb24455ab164df45e4da01dd0442b40c77c7ba5384e`,
  records ownership, restart, cancellation, bounds, and qualification for all
  four provider lanes. The bounded real-host diagnostic verified exact Codex
  `0.147.0`, executable SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`,
  retained schema/surface roots, initialized one owned generation, executed one
  typed `thread/list(limit=1)`, observed one result, and closed it. It started no
  generative turn and read or wrote no target repository.
- Focused evidence: `docs/sfv2-b4-focused-evidence.json`, SHA-256
  `5387daa78b00e6bc7e222fe9540c955cd696b59c917795563f1d0d7737e2803b`,
  records `46 passed`, repository collection at `179 tests`, Ruff and 87-file
  format success, mypy success across 59 source files, compilation, exact
  producer identity, diagnostic results, and Stop-boundary checks. No broad
  runtime suite was run.
- Artifact proof: an ephemeral Factory wheel for `2.0.0.dev6`, SHA-256
  `cb8487ebdb14ff52d05a59f76fd9f41d7ce1836db025c1959a5e798d5de44787`,
  contains the app-server adapter, provenance verifier, and packaged exact pin.
  It is qualification evidence, not a release artifact.
- Negative proofs: duplicate process owners fail; replacement closes its former
  owner; a tampered producer wheel or stale durable producer root fails closed;
  a replaced provider reattaches to the same exact thread/turn; unrouted
  approval is declined; engine cancellation durably fences new dispatch before
  cancelling every exact provider handle; the local-process lane waits for
  process-group exit and escalates a SIGTERM-ignoring child to SIGKILL before
  returning terminal cancellation; failed recovery cancellation retains the
  expired active lease and blocks overlap; callback authentication material is
  absent from both `ProviderRequest` and the durable handle; and provider success
  cannot set work acceptance.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Capability added or preserved: real replaceable worker execution can start,
    survive adapter restart, be cancelled, and return attributable evidence
    without becoming mission or acceptance authority.
  - Paths compared: keep the dashboard-local generic client; resolve a public
    package name/version; copy utils source; consume the exact qualified wheel
    behind a Factory adapter.
  - Selected level and owner: exact shared mechanics from utils plus
    Factory-owned pins, provider mappings, bounds, callbacks, and consequence
    routing.
  - Protected-capability result: reservations, scheduling/attempt budgets,
    callbacks, QA, acceptance, and target effects remain Factory-owned.
  - Rejected alternatives: duplicate clients drift, registry resolution can
    select an unrelated public wheel, and source copying destroys the producer
    boundary.
  - Tradeoff and uncertainty: exact Codex `0.147.0` compatibility is
    intentionally fail-closed; later protocol adoption requires a newly
    qualified producer artifact and an updated Factory pin.
- Preserved rejected candidate: exact pushed commit
  `ca101691d8bd8c5300bf40e46c045ad8fa7d4487`, tree
  `307826a17a56eae0de478d1a32c779a4b61fce05`, returned `REVISE` with three P1
  findings and no P0/P2: engine cancellation could not reach active providers,
  lease-expiry recovery released authority before provider cancellation, and
  external dispatch received the Factory callback secret.
- Preserved rejected correction: exact pushed commit
  `aea15d082638bf1d23b4c42822b2024aad6f6320`, tree
  `b554865b413bdf214265a16b4c9dc051d2ee1547`, returned `REVISE` with one P1
  and no P0/P2: `ProcessProvider` and `CodexCLIProvider` reported terminal
  cancellation immediately after SIGTERM without observing process-group exit,
  so a signal-ignoring child could produce effects after Factory authority was
  released. The next correction retains the durable effect fence, cancellation-
  before-release ordering, failure retention, and callback-secret removal while
  adding bounded SIGTERM wait, SIGKILL escalation, and verified group exit.
- Accepted correction checkpoint: branch
  `agent/software-factory-v2-native-refactor`, commit
  `635531016150d77a5de8592592f16420bb538505`, tree
  `9ea8be43835126efdf16966fa68712afd23de427`, pushed with a clean worktree
  and zero local/remote divergence.
- Independent review: the existing reviewer `/root/sfv2_b0_exact_review`
  reviewed exact correction `635531016150d77a5de8592592f16420bb538505`,
  reproduced the SIGTERM-ignoring attack against both `ProcessProvider` and
  inherited `CodexCLIProvider` from original and fresh owners, forced the
  non-terminal exit-proof failure path, reran `46 passed`, collected `179`
  tests, verified the exact internal client and evidence/artifact roots, and
  returned `ACCEPT` with no P0, P1, or P2 findings. The fresh-owner proof
  observed SIGKILL escalation, process-group absence, and no delayed effect;
  the forced failure retained the running execution, active lease, failed
  durable effect fence, and rejected replacement dispatch.
- Acceptance posture: `accepted`. Retained open work: none in Block 4; Blocks
  5–12 remain unaccepted inside the current full range. Block 9 structural/runtime
  packages are not consumed, the dashboard duplicate is not retired, utils is
  unmodified, and no Block 5 target-profile effect has begun. Continue
  automatically to dependency-eligible Block 5.

### Stop

Stop before target-profile authoritative effects.

---

## Block 5 — Implement target profiles, workspaces, and authoritative effects

Status: `accepted`

### Objective

Keep domain inspection, candidate workspaces, validation, application, and
delivery effects behind registered target-profile contracts.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: the core can operate different target classes
  without importing their ontology.
- Potential capability loss or regression: profile effects could bypass core
  authority, fencing, or currentness.
- Protected-capability effect: Git remains source/candidate truth for software;
  effects remain bounded and reversible where required.
- Architecture and operating-model effect: software behavior moves behind the
  first complete profile.
- Tradeoff and source evidence: v2 plan sections 4.3 and 7.

### Inputs and dependencies

- Blocks 3–4.

### Required work

- Complete software target snapshot, workspace, command/test/build,
  integration, release, cleanup, and rollback capabilities.
- Register fixed effect classes and currentness checks.

### Scope and non-goals

- In scope: profile/effect contracts and software profile.
- Not in scope: a universal domain schema or the neutral proof profile.
- Profiles cannot accept their own output.

### Deliverables and recorded state

- Profile registry/contracts, software profile, effect adapters, and isolated
  target fixtures.

### Resource and economy contract

Use disposable repositories and affected validation; no production target.

### QA and independent review

Review isolation, currentness, authority, rollback, and cross-profile leakage.

### Acceptance

- Software operations use profile contracts and the core contains no Git-only
  invariant except through those interfaces.

### Negative tests

- Reject arbitrary command/path injection, worktree as target authority, stale
  apply, unowned effect, or profile self-acceptance.

### Completion evidence

- Start baseline: clean pushed Block 4 acceptance successor
  `1dd84e7510684bf617b35079c2734035e5bae2ca`; Blocks 0–4 are accepted and
  Block 5 is the sole dependency-eligible frontier.
- Start posture: implement a typed profile registry and the first complete
  Factory-owned software profile over the existing workspace, execution,
  integration, release, cleanup, and rollback owners. Register fixed effect
  classes and exact target currentness checks; do not introduce a universal
  target schema, let a profile accept its output, consume Block 9 utils
  packages, or begin Block 6 QA/supervision acceptance integration.
- Preserved rejected candidate: exact commit
  `ccdd3eb4f4d32c05ee8ed35f16de4c97877e1acc`, tree
  `7f1adb26d867b2214fc6164bd0b48b0c959eb258`, remains clean and pushed. Distinct
  exact-revision review returned `REVISE`: dirty bytes were absent from
  currentness; raw profile/workspace paths bypassed the registry; release
  predecessor and rollback state crossed target roots; arbitrary reviewer
  strings could manufacture release acceptance; and the focused evidence did
  not exercise those attacks. The revision and review record are preserved;
  corrections exist only in the successor candidate.
- Preserved rejected successor: exact commit
  `55663ef29e8696ebbf60cc73a0b688c3f3e761d7`, tree
  `acfd613aa9516dcad59e4191c30d265be95bb1e4`, also remains clean and pushed.
  Exact re-review confirmed the first four P1s closed but returned `REVISE`
  because `GovernedReleaseService.activate_and_verify()` still called the
  physical activation owner around the exact-decision predicate, and the
  evidence omitted that convenience-path case. Bounded causal review classified
  this as service-boundary duplication: two public activation routes did not
  share one predicate. The successor correction centralizes both routes on
  `activate()`; the recurrence invariant rejects an accepted physical review
  with no governed decision through either public entrypoint.
- Preserved runtime-sound/index-stale successor: exact commit
  `fd8e7ade288292981cfb88c2209eebb8f694fec5`, tree
  `84d7d0637662f7835c52ca0bc48c34e6e56bad59`, remains clean and pushed.
  Exact review confirmed the runtime correction, all earlier authority defects,
  the `44 passed` evidence, and the Block boundary, then returned `REVISE`
  solely because canonical `docs/tracker.md` still routed Block 4 and its older
  detailed-tracker hash. The correction is index-only: bind this current
  detailed tracker, record Blocks 0–4 accepted, and route Block 5 as candidate.
- Domain-neutral profile contract: `TargetProfileRegistry` owns unique profile
  composition, fixed `EffectClass` admission, exact before/after snapshots, and
  revision/currentness fencing. Unknown profiles, free-form effect strings, and
  effects not owned by the selected profile fail before adapter execution. The
  registry contains no Git, command, release, content, QA, or acceptance schema.
- Complete software profile: `SoftwareTargetProfile` binds registered primary
  Git checkouts and target branch refs, then delegates snapshot, workspace
  create/freeze, registered command/test/build, integration/publish, release
  stage/activate, no-loss cleanup, and evidence-required rollback to the existing
  Factory physical owners. Controller and QA receive the profile workspace
  interface; the raw Git workspace service remains an internal physical adapter.
- Authority/currentness: target snapshots bind exact commit, tree, primary
  checkout status root, checked-out branch, tracked diff bytes, untracked
  path/content roots, repository state version, configured branch, and root.
  The registry supplies a per-composition authority object and direct adapter
  invocation without it fails. Core withholds raw physical-owner objects and
  raw workspace, command, and release facade methods. Commands are fixed
  registered argv/timeout/exit-code contracts executed only on an exact-base
  leased workspace. Target branch, workspace/integration/release/preservation
  roots, argv, environment, and working directory are not caller arguments.
  Integration compare-and-swap and existing release/cleanup guards remain
  authoritative.
- Acceptance separation: the profile can stage and activate a release, but
  staging creates the existing governed acceptance contract and activation
  succeeds only after its exact granted independent review and accepted
  decision. The physical release owner scopes active predecessor selection and
  rollback to the registered release root. `accept` is not an effect class and
  the profile has no acceptance method; Block 6 remains the integrated
  QA/supervision/acceptance owner.
- Contract record: `docs/software-factory-v2-target-profile-contract.md`,
  SHA-256 `14a1720804271e6caf746acc977b4ad3ca703420e056b2029770d5a81d80a0e2`,
  records the fixed effect matrix, physical owners, exact-currentness contract,
  caller argument exclusions, and later-Block boundaries.
- Focused evidence: `docs/sfv2-b5-focused-evidence.json`, SHA-256
  `7b75455d8deee64453cacb8cb53f1dcf606d99655387aeccc5ab971a2dc1a7ae`, records
  `44 passed` across the profile, composition,
  physical release, workspace/execution, governance, governed-release,
  reconciliation, recovery, and advanced-composition slices; repository
  collection at `185 tests`; Ruff and 91-file format success; mypy across 62
  source files; compilation; native entrypoint compatibility; full tracker
  verification; and Stop-boundary checks. No broad runtime suite was run.
- Artifact proof: an ephemeral Factory wheel for `2.0.0.dev6`, SHA-256
  `75b51e2405c0ff179b17f313684788e8decb783c0e339203a895ee4dd1eef895`,
  contains the profile registry/contracts and software profile. It is local
  qualification evidence, not a release artifact.
- Negative proofs: reject caller-supplied command/path roots and unknown command
  keys; linked worktrees as target authority; target revision, checked-out
  branch, same-status dirty-byte, untracked-content, or repository-state drift;
  direct profile calls without registry authority; raw Core effect access;
  workspace changes after candidate freeze; effect classes not owned by the
  profile; cross-root active/superseded/predecessor/rollback state; arbitrary
  reviewer identity; and profile self-acceptance. Real disposable repositories
  prove fixed test/build commands, integration publish, exact governed-review-
  gated activation, two independent release roots, preservation, and rollback.
- Product-capability review:
  - Trigger: consequential Block posture.
  - Capability added or preserved: the domain-neutral core can select a profile
    and safely apply target effects while Git remains software source/candidate
    truth and every physical owner retains its existing fences and rollback.
  - Paths compared: keep direct software calls as the only surface; introduce a
    universal target schema; create new profile-owned effect implementations;
    or register a typed profile that delegates to retained physical owners.
  - Selected level and owner: typed generic registry plus one complete software
    adapter, with command/path configuration owned at composition and no new
    database/effect writer.
  - Protected-capability result: stale targets, arbitrary effects, worktree
    authority, self-acceptance, and irreversible unreviewed release remain
    rejected; existing currentness, no-loss, and rollback guards are reused.
  - Rejected alternatives: direct-only calls keep software ontology exposed;
    a universal schema overgeneralizes before the Block 10 neutral proof; new
    physical effect owners duplicate authority.
  - Tradeoff and uncertainty: target registrations are explicit composition
    inputs, not a new persistent ontology. Block 10 must prove external profile
    extensibility before the generic contract is broadened.
- Independent review: exact candidate
  `96d7d8a0db5bb35d858d9566d91f19b9e057deb7`, tree
  `1ffa9df7112fc49eb902cc462b1debfa82233fb9`, was clean, pushed, and at `0/0`.
  Distinct exact review returned `ACCEPT` with no P0–P2 findings after proving
  the canonical index has one active SFV2 program, binds detailed-tracker SHA
  `bc67a79439e18a44f96ded031835f74508ca38f9473366eace792bd9a24dffa5`,
  preserves the full B0–B12 range, and routes Block 5. The runtime tree was
  byte-identical to reviewed `fd8e7ad`; the `44 passed` evidence and contract
  hashes remained exact.
- Acceptance posture: `accepted`. Retained open work: Blocks 6–12 and the
  terminal observable outcome. No production target was used; Block 6
  integration and Blocks 9/11/12 utils, cutover, and terminal work have not
  begun; utils is unmodified. Post-Block audit found no duplicated target
  effect authority, currentness gap, cross-root release state, self-acceptance,
  or unsupported completion claim.

### Stop

Stop before integrated QA/supervision acceptance.

---

## Block 6 — Integrate QA, supervision, acceptance, and outcome closure

Status: `accepted`

### Objective

Make revision-bound QA, independent supervision, staged acceptance, and actual
outcome reconciliation first-class runtime behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: candidates, integrations, installations, and
  terminal outcomes are separately evaluated.
- Potential capability loss or regression: process receipts could become false
  outcome proof or reviewers could mutate target work.
- Protected-capability effect: independent review, incidents, bounded steering,
  effectiveness review, and no-early-return remain intact.
- Architecture and operating-model effect: existing three skills compose
  through the runtime without becoming duplicate authorities.
- Tradeoff and source evidence: README reliability model and v2 plan sections
  3, 4.1, and 12.

### Inputs and dependencies

- Blocks 3–5.

### Required work

- Implement QA obligations, mechanical and semantic review separation,
  candidate/integrated/installed/terminal acceptance, incident/containment,
  effectiveness review, and capability/outcome reconciliation.

### Scope and non-goals

- In scope: operational quality and acceptance lifecycle.
- Not in scope: patent/legal judgment, universal scoring, or reviewer mutation.
- Do not create a per-action critic.

### Deliverables and recorded state

- QA/acceptance contracts, supervision integration, incident/review fixtures,
  and terminal reducer.

### Resource and economy contract

Review changed state; sample unchanged no-intervention outcomes; avoid replaying
accepted proof.

### QA and independent review

Distinct review must reconstruct operator-visible outcomes and protected
capabilities rather than trust the producer's summary.

### Acceptance

- No stage can promote itself; actual outcome disagreement reopens the narrow
  owner despite green process records.

### Negative tests

- Reject same-author acceptance, stale review, process-pass/outcome-unchanged,
  provider completion as QA, or terminal return with remaining range.

### Completion evidence

- Start baseline: clean pushed Block 5 acceptance successor
  `d10ca8e292ed0850a1236fad22e1736615e96509`; Blocks 0–5 are accepted and
  Block 6 is the sole dependency-eligible frontier.
- Start posture: integrate existing QA, governance, supervision, incident,
  continuation, release, and evidence owners into one revision-bound staged
  acceptance and actual-outcome closure path. Preserve mechanical versus
  semantic reviewer separation; do not create a per-action critic, begin
  libRSI cutover, consume Block 9 utils artifacts, or run the broad runtime
  suite.
- Implemented one `AcceptanceLifecycleService` projection over the existing
  authorities. `GovernanceService` remains the only contract/review/decision
  owner; `WorkItemService`, `CapabilityService`, `SupervisionService`, and
  `ContinuationService` retain their canonical transitions rather than gaining
  a second writer. Work acceptance is now capability-token fenced to the staged
  coordinator, while legacy `QAService.accept_candidate` fails closed and
  `complete_candidate_qa` records QA success without acceptance promotion.
  Migration `0022_acceptance_lifecycle.sql` records exact
  candidate/integrated/installed/terminal stages and actual-outcome
  reconciliations; schema version is 22 and the exhaustive ownership registry
  covers both new tables.
- Currentness and economy: every stage binds exact revision, exact currentness
  root, implementer, governed contract/decision, expected operator/protected
  outcome, remaining range, and exact accepted predecessor. A revision or
  currentness change stales the entire downstream stage chain and governance
  records. Identical observations deduplicate by content root; accepted proof
  is not replayed across stages. Promotion rechecks the stage, reviewer,
  aligned outcome, unresolved remediation, and terminal blockers inside the
  same immediate transaction as the work/stage transition. Contract SHA-256:
  `c8530a521c46cb1fdfbb4c440674abf1981cc1a369223fdbc4ac31770a26c284`.
- QA and supervision: mechanical probes require current exact-revision
  evidence but cannot represent or satisfy semantic review. Exact role grant,
  provider identity, distinct reviewer, and governance decision remain
  required. Actual-outcome reconciliation separately consumes an exact bounded
  `outcome_reviewer` grant and verifies the recorded external provider identity.
  A green process record with a disagreeing actual outcome regresses only the
  named work/capability owner, opens one correction obligation and deduplicated
  incident, and remains blocked until later aligned observation, obligation
  resolution, and an independent effectiveness review. Effectiveness evidence
  must name the exact incident, postdate its rooted correction, bind the
  correction and observation roots, match the candidate revision when present,
  and bind any declared verification execution.
- Terminal reducer: provider-reported terminal execution now yields
  `reconcile_terminal_acceptance`. Terminal preparation and promotion derive
  remaining range from active canonical programs instead of trusting the
  caller's duplicate scope. `ProgramService.complete_program` requires an
  accepted current revision with `range_complete: true`, an empty resume
  frontier, installed selected work, exact program evidence, and independent
  review. Mission completion additionally requires an accepted terminal stage,
  aligned actual outcome, no active program, no required capability gap, no
  open obligation, no selected uncancelled work below installed acceptance, and
  terminal evidence at the accepted exact revision from the declared
  independent verifier.
- Product-capability review:
  - Trigger: consequential Block posture; target-frame SHA-256
    `ee09601b733bbc4fc5c12df5fd1a7bb6f29550b50a2f70b2021feb4aa5e35d0d`.
  - Capability added or preserved: exact candidate, integrated, installed, and
    terminal acceptance now depends on independent semantic review and observed
    outcome rather than process success, while mission continuation remains
    blocked by the canonical requested range.
  - Paths compared: retain legacy QA self-promotion; add a per-action universal
    critic/score; collapse to one terminal verdict; or compose one staged
    coordinator over the existing governance, work, capability, supervision,
    program, and continuation owners.
  - Selected level and owner: the staged lifecycle coordinator owns only stage
    and outcome projections; every operational transition remains with its
    existing owner and every semantic decision remains grant/review bound.
  - Protected-capability result: independent review, exact currentness,
    canonical range preservation, narrow remediation, incident effectiveness,
    no-early-return, and provider/effect boundaries remain fail closed.
  - Rejected alternatives: legacy QA conflates process and acceptance; a critic
    duplicates policy and spends continuously; one terminal verdict loses
    integration/installation evidence and makes rollback diagnosis ambiguous.
  - Tradeoff and uncertainty: four stages add bounded changed-state review and
    record volume, offset by content-root deduplication and no-change reuse;
    Block 12 must still prove terminal composition under the full mapped suite.
- Preserved rejected history: candidate
  `fb3561fe39efa0b8fed10bcb4b470b2d61244085`, tree
  `29147c9c013867c7ab5f5937ca9caeca05938b2d`, was clean and pushed. Distinct
  exact review returned `REVISE`: P1 public work/legacy QA acceptance bypass,
  P1 caller-authored terminal range hiding an active canonical program, P1
  evidence-free effectiveness, and P2 unsupported negative-proof claims. That
  candidate remains immutable, preserved, and unaccepted. The narrow
  correction adds the authority fence, canonical program closure, mandatory
  effectiveness evidence/observations, exact outcome-reviewer grants, and the
  missing negative fixtures without rewriting history. Correction candidate
  `58d51d707b7e15686cb124776abd4a0abe94fd5b`, tree
  `fa9718e69c2ea1daa6ac22d992a5293a9acb33a4`, was also clean and pushed but
  distinct exact re-review returned `REVISE`: P1 stage promotion predicates
  were outside the write transaction, P1 effectiveness accepted stale unrelated
  pre-correction evidence, and P2 evidence/capability-review gaps. It too remains
  immutable, preserved, and unaccepted. The second narrow correction moves every
  promotion predicate into one immediate transaction, serializes new program
  activation behind terminal acceptance, roots and currentness-binds
  effectiveness proof, and records the missing Product-capability review.
- Focused correction proof: `66 passed` across acceptance lifecycle,
  governance, supervision, operational boundaries, composition, advanced
  integration, core, and legacy execution QA; one pre-existing `TestStore`
  collection warning. Negative fixtures now cover direct work/legacy QA bypass,
  mechanical/semantic substitution, same-author/stale review, changed
  currentness, exact outcome-reviewer grant/provider identity,
  process-pass/outcome-wrong, protected-capability regression, evidence-free
  effectiveness, pre-correction/unrelated proof, concurrent currentness and
  active-program races, unresolved remediation, provider completion as QA,
  caller-hidden active programs, reviewed program closure, remaining-range
  terminal return, and the accepted exact terminal chain. Ruff format/check are
  clean across 93 files, mypy is clean across 63 source files, compile is
  clean, and full runtime collection is 196 tests with the documented legacy
  collection warnings only. Full tracker verification is 0 errors/0 warnings;
  no broad runtime suite was run. The isolated build produced wheel SHA-256
  `1faa0b20177a1422663a89d3b979e112942260125d720f330c22361f0bf1d5ec`
  and sdist SHA-256
  `bf783a5c6bc12841d30e08a5a1e57d4b5ca6334185062a9369ba5c0bc4ffa106`.
  Focused evidence JSON SHA-256:
  `d726c0773a24b2135a999cb96295b96fd8f1a967351a8700c88c776d2e99eca7`.
- Independent review: exact candidate
  `5025cf38ea989bb619d9d79facf0386ac5b10c0f`, tree
  `15a96706f83cca1503aea6e96884b15b54fb5ea1`, was clean, pushed, and at `0/0`.
  Distinct exact re-review returned `ACCEPT` with no P0–P2 findings after
  independently reproducing both race orderings, stale/unrelated/unrooted/
  wrong-revision/wrong-verification effectiveness attacks, the correct rooted
  resolution, every earlier bypass closure, and the exact Product-capability
  frame. The reviewer reproduced `66 passed`, 196-test collection, 93-file
  format, Ruff, mypy across 63 sources, tracker verification 0/0, JSON/diff
  integrity, and every recorded contract/evidence/source/migration/tracker hash.
- Acceptance posture: `accepted`. Rejected candidates `fb3561f` and `58d51d7`
  remain immutable pushed history. Retained open work is Blocks 7–12 and the
  terminal observable outcome. No production target was used; no libRSI or
  utils lane was entered, and delivery, service boundary, cutover, and terminal
  program qualification remain outside this accepted Block. Post-Block audit
  found no acceptance bypass, stale promotion, range race, evidence-free
  effectiveness, duplicate writer, early return, or scope bleed.

### Stop

Stop before libRSI semantic cutover.

---

## Block 7 — Integrate libRSI and remove duplicate semantic owners

Status: `accepted`

### Objective

Use exact accepted libRSI contracts for evidence-driven hypotheses,
experiments, comparison, improvement, and self-change while Factory retains
operational authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: reusable semantic improvement without duplicate
  local policy.
- Potential capability loss or regression: libRSI could become a scheduler or
  Factory could keep two semantic writers.
- Protected-capability effect: mission/work/effect/QA/delivery remain Factory;
  invalid experiments remain neutral evidence.
- Architecture and operating-model effect: thin mappings and one-way
  dependency `software-factory → libRSI`.
- Tradeoff and source evidence: v2 plan sections 4.2, 5, 8–10.

### Inputs and dependencies

- Blocks 1, 3, and 6; exact accepted libRSI revisions only.

### Required work

- Pin version/commit/content roots, map records and outcomes, shadow old paths,
  cut over supported semantics, and delete duplicate owners after parity.

### Scope and non-goals

- In scope: semantic integration and duplicate removal.
- Not in scope: importing Factory into libRSI or transferring operational
  persistence/effects.
- Planned libRSI APIs are not treated as accepted.

### Deliverables and recorded state

- Integration package, record bindings, conformance fixtures, cutover receipts,
  and deletion map.

### Resource and economy contract

Reuse libRSI dogfoods; run contract tests before mapped Factory validation.

### QA and independent review

Review both exact repository revisions, dependency direction, owner uniqueness,
semantic/operational identity separation, and outcome use.

### Acceptance

- Failed and unexpectedly successful executions produce competing hypotheses,
  discriminating experiments, evidence updates, and changed work without
  closing obligations prematurely.

### Negative tests

- Reject reverse imports, duplicate semantic ledgers, failed experiment as
  falsification, semantic selection as operational authorization, or mutable
  `main` dependency.

### Completion evidence

- Start baseline: clean pushed Block 6 acceptance successor
  `c204dec95dbb4d9a831b344eb981722ae6135355`; Blocks 0–6 are accepted and
  Block 7 is the sole dependency-eligible frontier.
- Accepted producer handoff: pushed libRSI acceptance-evidence revision
  `dbcb60edfbcab53ff7e5cc25403bfbc33b458329`, accepted implementation/source
  commit `1d81f6180b40435e10145756a2d99e6f334d31bc`, repository tree
  `d9ff421192e3582a6b8e908bf8a02cf2d7678acc`, package tree
  `2653cb551e69bf2f45c95216982f70b50258c92e`, distribution/import/version
  `libRSI`/`librsi`/`0.2.0`, accepted wheel SHA-256
  `6b06612150d2f3a11b23de14870738ea9cd6b704574c8cea2c8e811392454659`,
  and accepted sdist SHA-256
  `e3ca4a817b80043ea59ba153e4d3ba105c86ad74183cb28816d66dd6d0f813c0`.
  Canonical record, outcome-projection, and event-projection schema versions are
  `1`; the Factory adapter contract begins at `software-factory.librsi/v1`.
  The producer branch is pushed at `0/0`; its unrelated untracked `uv.lock`
  remains excluded. Factory will consume only the immutable Git object/artifact
  identity, will not import from or modify that dirty checkout, and makes no
  public installability, license, redistribution, or release claim.
- Start posture: add one-way `software-factory → libRSI` integration, immutable
  canonical-record cache/bindings, exact operational-to-semantic mappings,
  shadow parity, and authoritative failed/unexpected-execution semantic slices.
  Factory retains missions, obligations, work, execution, effects, governance,
  QA, acceptance, delivery, and operational persistence. Do not consume utils,
  begin delivery/release cutover, or run the broad runtime suite.
- Immutable admission: runtime metadata and `runtime/uv.lock` resolve only the
  accepted libRSI source commit. Packaged pin
  `runtime/src/software_factory/semantic_pins/librsi.json` records the producer
  acceptance revision, accepted source commit, repository and package trees,
  package-content-root algorithm, distribution/import/version, accepted wheel
  and sdist SHA-256 values, schema versions, adapter contract, and unpublished/
  no-license boundary. The pin verifier checks import/distribution version and
  exact PEP 610 URL/VCS/requested/installed commit. Missing
  `direct_url.json` fails closed rather than treating a same-name/version wheel
  as accepted. A bare registry name, mutable `main`, producer checkout import,
  source copy, or producer write is absent. Exact producer public conformance from an isolated archive returned
  `22 passed`; its 16 warnings come from producer-owned explicit deprecated
  compatibility tests rather than the Factory adapter.
- Canonical integration: `integrations/librsi` maps the complete observed
  mission/work/execution state to exact composite target and snapshot records.
  Migration `0023_librsi_integration.sql` adds one immutable canonical-record
  cache, explicit operational-subject/semantic-root bindings, and rooted
  shadow/cutover receipts; schema version is 23. Records are immutable by root,
  conflicting bytes or stale bindings fail closed, operational IDs are never
  semantic identities, and no operational table foreign-key depends on the
  semantic cache. The exhaustive owner test now covers integration subpackages
  and assigns all three tables to one writer.
- Authoritative vertical slices: failed/abandoned/cancelled execution and
  unexpected success each yield one exact observation, two competing canonical
  hypotheses, boundary evidence, and one bounded discriminating experiment.
  The adapter creates one idempotent proposed/pending Factory experiment work
  item without closing its obligation. Exact experiment observations update
  the exact hypothesis version; an invalid or failed experiment is zero-weight
  null evidence rather than falsification. Unexpected-success follow-up appears
  only after bounded support reaches libRSI's supported posture, and remains
  proposed/pending because semantic selection grants no dispatch, effect,
  acceptance, or lifecycle authority. Every semantic ingress revalidates live
  mission and known work/execution state versions against its exact snapshot;
  cached equality cannot substitute for host currentness. Persistence/binding
  and operational selection hold an immediate host transaction and repeat the
  currentness gate immediately before commit, so an interleaved host advance
  rolls the complete effect back.
- Supported semantic convergence: `LearningService` maps compatibility
  entrypoints to canonical `Hypothesis`, `Evidence`, and `ExperimentSpec`
  records and the accepted `HypothesisPolicy` and `ExperimentPolicy`.
  `reflections_v2`, `hypotheses_v2`, `hypothesis_evidence_v2`, and
  `selection_outcomes_v2` have no runtime writer or owner claim; experiment
  rows retain host execution state only. Exact
  `CandidateTrialBatch` evidence, `RiskPolicy`, and
  `ComparativeSelectionPolicy` produce canonical comparison decisions without
  an operational transition; a Factory candidate advances only after its
  independent review and exact same-group, selected-root, currentness-matched
  decision binding. A hypothesis is admitted to Learning experiment design only
  under its exact same-mission binding. Evolution checkpoint, program-change, portfolio,
  and selector paths delegate roots, transitions, and gates to the accepted
  policies. Complete `ImprovementResult` and governed `RSIResult` records cross
  one typed binding boundary, with RSI request revalidation by
  `SelfChangePolicy`. Problem solving consumes the exact selected candidate
  roots from one live-current `ImprovementResult`. Each selected candidate must
  carry a byte-exact `software_factory_operation` projection; caller strategy,
  effect, and scope must match it, and one root maps to one active host row. It
  may apply host prerequisites, capacity, and writable-scope conflict gates but
  cannot rank, duplicate, reinterpret, or replace the semantic selection.
  Adaptive outcome handling delegates failed
  and unexpected-success semantics directly to the canonical reflection and
  experiment slice. Learning, evolution, problem-solving, and adaptive tables
  are operational projections; the integration is the only current semantic
  lifecycle owner.
- Shadow, cutover, and deletion: each failed/unexpected source execution first
  compares complete canonical roles, statements, predictions, route, and
  experiment kind against a separately implemented pure legacy projection.
  Mismatch fails before semantic persistence, bindings, Factory work, receipts,
  or cutover events. A match records exact dependency/currentness, shadow, and
  canonical-result roots. The failed/unexpected local proposal and escalation
  algorithms, `_create_hypothesis`, mutable `update_hypothesis` writer, local
  strategy ranking, and local epistemic-next-action choice are deleted. The
  legacy `hypotheses` table and v2 reflection/hypothesis/evidence/selection-
  outcome tables plus `adaptive_actions` are schema-history
  only with no runtime writer or lifecycle-owner claim; Block 11 owns byte
  retirement after preservation proof. The Factory-floor API projects canonical
  reflection bindings alongside preserved legacy history. The exact treatment
  and deletion map is `docs/software-factory-v2-librsi-cutover.md`.
- Preserved rejected candidate: exact pushed commit
  `79374642bdad3581b5a631d228330548489c68c3`, tree
  `5fc629b012bb9355c5399c3b69271e4d1a3c67e5`, remains unaccepted. Distinct
  exact-revision review returned `REVISE` with four P1 findings and no P0: the
  cutover was narrowed to two reflection slices while Learning/Evolution/
  ProblemSolving remained semantic owners; experiment outcomes accepted
  unrelated and cross-mission terminal executions; shadow parity derived its
  expected projection from the candidate adapter itself; and pin verification
  admitted same-name/version installs without exact PEP 610 provenance. This
  next candidate preserved that revision and closed the pin, independent shadow,
  and original unassigned/cross-mission execution attacks without editing pushed
  migration 0023, but did not earn acceptance.
- Preserved rejected successor: exact pushed commit
  `bb1bd62af14f12af82b8dd3a55711e7b5cc4c70e`, tree
  `01308e2e7fae4f1c73f62d85d20b64fdc26e7020`, remains unaccepted. Distinct
  exact-revision review returned `REVISE` with five P1 findings: experiment
  evidence and comparison/selection trusted cached rather than live mission
  currentness; Learning could bind a mission-A hypothesis into a mission-B
  experiment; ProblemSolving/Adaptive still owned generic improvement and
  epistemic-next-action choices; and the operator API read only the retired
  `reflections_v2` table. The current correction closes those exact findings by
  live host revalidation, same-mission hypothesis admission, exact
  `ImprovementResult` consumption, direct adaptive delegation, local-writer and
  decision-path removal, and canonical API projection. That candidate closed
  the five named findings but did not earn acceptance.
- Preserved rejected atomicity/projection candidate: exact pushed commit
  `c5bfce2b3fabcc89c22d96572f9c8c0193aa9e36`, tree
  `78449d51ac291bec8e4b0b5b4b92568ba4ac079a`, remains unaccepted. Distinct
  exact-revision review returned `REVISE` with two P1 findings and independently
  reproduced its `68`-pass focused evidence: live currentness could advance
  after the gate but before semantic persistence or operational selection; and
  one selected semantic root could authorize multiple unrelated caller-authored
  operational rows. The current correction holds and double-checks currentness
  inside the effect transaction, requires a byte-matched operational projection
  embedded in the exact selected `CandidateSnapshot`, and enforces a one-active-
  row invariant plus selection-time duplicate rejection. The rejected candidate
  evidence remains preserved at SHA-256
  `ead2009b2191de6642ff81c37a9f1af143fe4383a5551d99349905e2f58256eb`.
- Product-capability review:
  - Trigger: consequential Block and one-way semantic-owner cutover; frame is
    the exact Block 7 objective, accepted libRSI handoff, v2 plan sections
    4.2/5/8–10, and protected Factory operational-authority boundary.
  - Capability added or preserved: failed work and surprising success now
    generate evidence-driven competing explanations and real discriminators,
    while mission continuation, obligations, work, effects, QA, acceptance,
    delivery, and release remain Factory-owned.
  - Paths compared: retain duplicate local hypotheses; copy libRSI source;
    resolve the same public registry name/version; transfer scheduling/effects
    to libRSI; or use an exact immutable one-way dependency plus thin
    Factory-owned mappings and bindings.
  - Selected level and owner: libRSI owns canonical epistemic, experimental,
    comparison, improvement, and self-change records and transitions; Factory owns complete
    operational observation, persistence hosting, work/effect conversion, and
    every authority-bearing transition.
  - Protected-capability result: failures remain evidence rather than mission
    closure, unexpected success cannot self-promote, exact currentness and
    independent downstream review remain mandatory, and no reverse import or
    duplicate reflection writer exists.
  - Rejected alternatives: local duplication preserves two writers; source
    copying breaks independent ownership/versioning; bare registry resolution
    can select the unrelated public project; authority transfer creates a
    second controller; a universal semantic/operational ledger conflates IDs.
  - Tradeoff and uncertainty: immutable cache/bindings and a pinned VCS
    dependency add records and installation provenance checks, offset by root
    deduplication and one experiment work item per source. Block 12 must still
    prove installed terminal qualification; public release/license authority is
    deliberately absent.
- Proof: successor focused/mapped proof is recorded in
  `docs/sfv2-b7-focused-evidence.json` at SHA-256
  `af63ce0aed84275882b4ce7dd0810719e0bc873422392568fcaf0b00e8c00d7e`;
  no broad runtime suite was run. The
  previously recorded `18`/`75` proof for `7937464` and `68`/`63` proof for
  `c5bfce2` remain preserved historical evidence, not acceptance proof for this
  correction.
- Accepted exact candidate: pushed commit
  `56d2a22bf2a0df53d5bf2c3212187dc1cc9c67a2`, tree
  `d58f2a408e59a01bcbaa86825d8c3f3f31aa22c2`, clean and remote-equal at
  `0/0`. Distinct exact-revision review returned `ACCEPT` with no P0–P2
  findings after reproducing the post-gate currentness advance in semantic,
  Evolution, and ProblemSolving paths plus a forged duplicate operational row;
  every adversarial effect rolled back or failed closed. Targeted reviewer proof
  returned `3 passed`, Ruff format/check were clean, evidence and tracker hashes
  matched, and no utils consumption or later-Block scope bleed was found.
- Acceptance posture: Block 7 is `accepted` at the exact candidate above. No
  utils package was consumed, no production target was used, and delivery/
  release, service/API, neutral-content, migration, and terminal qualification
  remain Blocks 8–12.

### Stop

Stop before delivery/release cutover.

---

## Block 8 — Complete delivery, release, recovery, and reconciliation

Status: `accepted`

### Objective

Deliver accepted outcomes durably and recover or roll back exact effects
without losing unfinished obligations.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: exact delivery, immutable release, live refresh,
  rollback, self-repair, cleanup, and target resumption.
- Potential capability loss or regression: release success could hide stale
  installation or cleanup could delete evidence.
- Protected-capability effect: immutable history, no-loss cleanup, and exact
  resumption remain enforced.
- Architecture and operating-model effect: existing release/recovery owners
  consume accepted results only.
- Tradeoff and source evidence: README reliability model and v2 plan phase 4.

### Inputs and dependencies

- Blocks 5–7.

### Required work

- Integrate delivery manifests, release/installation verification, rollback,
  repair, cleanup, reconciliation, and interrupted-effect recovery.

### Scope and non-goals

- In scope: local/test delivery and release owners.
- Not in scope: production activation or external notification.
- Cleanup cannot erase unresolved or unverified evidence.

### Deliverables and recorded state

- Delivery/release contracts, recovery state, reconciliation reports, and
  fault-injection fixtures.

### Resource and economy contract

Use isolated installs/targets and deterministic crash points.

### QA and independent review

Review exact-once effects, installed bytes, rollback, evidence retention, and
unfinished-work restoration.

### Acceptance

- Every interrupted boundary rehydrates or compensates deterministically and
  resumes the exact target.

### Negative tests

- Reject release receipt without installed equivalence, duplicate effect,
  rollback to unverified bytes, cleanup data loss, or completed mission with
  unresolved delivery.

### Completion evidence

- Start baseline: exact pushed Block 7 acceptance successor
  `c8752129d919edf1b60f3a27ae083e1a89df34f0`, with clean local/remote
  equality at `0/0`; Blocks 5–7 are accepted dependencies and Block 8 is the
  first eligible frontier in the preserved full-range binding
  `RANGE-SFV2-B0-B12-3901D4F-2079C81D`.
- Execution posture: local/test delivery and release owners only, isolated
  targets, deterministic crash points, and focused/mapped proof. Production
  activation, external notification, broad runtime validation, and all utils
  package consumption remain out of scope for this Block.
- Completion proof: corrected implementation and bounded fault evidence are
  complete; a clean pushed correction candidate and distinct exact-revision
  review remain pending.
- Delivery/release implementation: immutable staging now leaves a durable
  stage-root receipt with a file and directory fsync before its physical copy,
  validates exact installed paths, bytes, executable posture, and manifest
  bytes before recording a release, fsyncs every staged file and directory,
  then fsyncs the release root after publication. It deterministically resumes
  the same physical release after an injected filesystem/SQL crash. Schema
  migration `0024_delivery_reconciliation.sql` adds the single-owned
  release-transition journal; activation and rollback serialize on a durable
  root lock, bind an exact pointer payload, predecessor, and transition root,
  reject another unfinished/root-currentness-changing transition, fsync the
  pointer and containing directory, then commit pointer/SQL posture atomically
  on retry.
  Installed probes rehash before and after the command, active use requires a
  committed matching pointer, and rollback refuses a previous release without
  passed installed verification and current exact bytes.
- Recovery/reconciliation implementation: preservation verification now checks
  the archive root, exact safe member set, embedded manifest bytes, and every
  declared member hash and the exact safe untracked-member set immediately
  before cleanup. Physical Git retirement now fails closed for branches,
  worktrees, and stashes because Git exposes no deletion adapter that
  atomically fences both exact object identity and concurrent worktree
  admission. Each refused cleanup-item retirement is recorded once as a failed
  audit effect with `physical_effect=false` and a required preserve/defer
  disposition. Integration prepare failures retain their exact branch,
  worktree, tracked changes, and untracked files, and terminal integration-lane
  retirement likewise preserve/defer-fails. Preparation and post-publication
  validation each run in a fresh retained detached snapshot of the exact
  `candidate_head`, with exact HEAD and tracked/index tree verified before and
  after the command; mutable integration-lane bytes cannot authorize another
  committed tree. Post-publication failure rolls target authority back only
  through ref compare-and-swap and never hard-resets checkout bytes, including
  validation snapshot-creation and process-spawn failures. Successful
  publication requires a final no-op ref compare-and-swap before SQL completion
  plus post-commit reconciliation against the exact `candidate_head`; a missing
  ref is durable `null` currentness rather than an exception that skips evidence.
  Each queued publisher rereads the candidate under the repository lock, and
  every terminal candidate/cleanup transition compare-and-swaps the exact
  expected SQL status so a stale caller cannot resurrect a rollback. The exact
  optional post-publication validation command is durably bound before the Git
  effect; idempotent or queued calls with a different validation policy fail
  closed instead of inheriting another caller's result.
  Once published, that historical fact remains immutable while legitimate later
  target revisions advance. No reconciliation path removes a branch ref,
  checkout, validation snapshot, stash, dirty byte, or untracked byte.
  Integration preparation resumes an exact planned merge/validation workspace;
  publication recognizes an already-applied accepted Git head and reruns its
  post-publication validation before committing SQL. Unfinished restart uses
  one workspace plus an atomically written and directory-fsynced restoration
  receipt bound to baseline, preserved source object, staged patch, complete
  status, and exact untracked-file bytes/modes. For the inventory-root checked
  out branch it replays both the preservation bundle's tracked working-tree
  patch and safe untracked archive after the committed branch delta. Recovery
  reopens the same case even after resolution, returns the original token and
  wake effect without replay, and treats an explicit false/missing `sent`
  result as failure before token consumption; target wakes and agent refreshes
  carry their persisted idempotency keys and redrive the same intent.
- Negative/fault proof: deterministic injections after staged-copy, active
  pointer, integration merge, published ref, restored workspace, target wake,
  and agent refresh all recovered to one durable row, token, intent, or
  workspace. Refused physical retirement produced one durable failed audit and
  no physical effect. Tests also rejected modified installed files,
  forged active pointers, rollback to unverified bytes, post-probe drift,
  tampered preservation archives, target-branch advance, cleanup without exact
  preservation, a cleanup branch advanced before retirement, a new dirty
  worktree admitted after inventory, every unsupported physical Git retirement,
  dirty integration-lane retirement, validation-failure lane cleanup, a
  validator substituting dirty bytes for `candidate_head` before preparation or
  post-publication acceptance, post-validation target-ref advance, missing
  target refs at completion, missing validator executables and snapshot-setup
  failure, historical-publication corruption after a legitimate successor, an
  overtaking concurrent publisher after terminal rollback, an overtaking release
  activation, duplicate resolved recovery, false wake delivery, and arbitrary
  restart state without a restoration receipt. A
  committed plus dirty plus untracked unfinished branch restores the latest
  tracked and exact untracked bytes and replays without duplication.
- Preserved rejected candidate: exact pushed commit
  `4a23d414a3908069161310125042eeb5b4514ba6`, tree
  `5780cd5fbf124523f7892347e66ae6a88a999d6c`, remains immutable and
  unaccepted. Distinct exact-revision review returned `REVISE` with four P1
  findings and one P2 durability finding: retirement could delete a branch
  advanced after preservation; restart omitted dirty tracked and untracked
  bytes; resolved recovery replay allocated a second wake and stranded it at a
  uniqueness conflict; an interrupted activation could be overtaken and later
  supersede newer authority; and staging/restart receipts and release-tree
  publication lacked all required post-rename file/directory fsyncs. The
  current correction closes those exact findings without rewriting the
  rejected history.
- Preserved rejected correction: exact pushed commit
  `76ca892955e24ebca7b5431312c79730b9850327`, tree
  `50c4b3f08b7b26afbcc71279e752a7a2a5f3871e`, remains immutable and
  unaccepted. Its distinct exact-revision review closed the dirty/untracked
  restart, resolved-recovery replay, activation-overtake, and fsync findings,
  and returned `REVISE` on one remaining P1 cleanup race. The reviewer advanced
  `old-complete` to commit `3d1cde8a` after the last identity check but before
  `git branch -D`; that commit was absent from the preservation bundle and the
  old adapter deleted it (`effect_status=succeeded`, `race_injected=true`,
  `branch_exists_after=false`, `advanced_in_bundle_heads=false`). That rejected
  correction replaced the check-then-delete gap with atomic expected-object
  ref deletion and disabled destructive worktree/stash paths that lacked an
  equivalent adapter.
- Preserved rejected successor: exact pushed commit
  `12adc2326ff47d38ceedef985e3ebcd9bcef133b`, tree
  `bdbc8a92681839e8495d7cba26c3e63b06441207`, remains immutable and
  unaccepted. Exact review confirmed that compare-and-delete preserved a
  post-check ref advance and that worktree/stash item retirement failed closed,
  but returned `REVISE` on one P1 worktree-admission race. At the same
  `retirement:after_identity_check` boundary, ordinary `git worktree add`
  created a new dirty checkout that ignored the Factory-private flock; cleanup
  then reported success while deleting its symbolic branch
  (`effect_status=succeeded`, `branch_ref_exists=false`,
  `raced_worktree_exists=true`, `raced_HEAD=refs/heads/old-complete`, with
  tracked and untracked pending bytes). The current successor removes physical
  branch retirement as well, rather than claiming that ref-object CAS fences
  separately admitted worktree authority.
- Preserved rejected no-delete candidate: exact pushed commit
  `52acbaf6abd8cca46d4328edf451bbe3f156a400`, tree
  `610e34055d1bf177ea0391aa019b27d5da15088b`, remains immutable and
  unaccepted. Exact review confirmed `OperationsService` retained branch,
  worktree, stash, symbolic HEAD, tracked, and untracked state with one
  idempotent `physical_effect=false` audit, but returned `REVISE` on one P1
  reconciliation-owner gap. `retire_integration_lane()` and the prepare-failure
  handler still used `git worktree remove --force` plus `git branch -D`.
  Independent reproduction dirtied a published integration worktree and
  observed both the worktree and branch disappear, including tracked and
  untracked pending bytes. The current successor removes both force-deletion
  routes and the hard-reset rollback path without weakening the already closed
  release/recovery findings.
- Preserved rejected mutable-validation candidate: exact pushed commit
  `91b8cacf8bcd30e256182e84c7519a12e7abfbbd`, tree
  `1c3baac068cce779a0913aacf505b418a80941cf`, remains immutable and
  unaccepted. Exact review confirmed every no-delete correction and reproduced
  the `35`-test focused proof, then returned `REVISE` on one P1 validation
  identity gap. A validator replaced committed `COMMITTED_BAD` bytes with dirty
  `VALIDATION_ONLY_GOOD` bytes in the retained integration lane and passed;
  publication still advanced the different committed `candidate_head`.
  Post-publication validation could likewise pass against `DIRTY_GOOD` while
  the target contained the committed bad bytes. The current successor isolates
  both phases in new exact detached snapshots and fails closed if their tracked
  or index bytes diverge through command completion.
- Preserved rejected pre-completion candidate: exact pushed commit
  `7c27b861781d6ca77b0e9564494bed652fe68094`, tree
  `0ea437cc8071569f1e9e7bfd6bb50298122deaf3`, remains immutable and
  unaccepted. Exact review confirmed both prior mutable-byte attacks now failed,
  then returned `REVISE` on two P1 publication-currentness paths. An ordinary
  external `git update-ref` after publication's first ref check could advance
  the target while exact-snapshot validation passed and SQL still reported
  `published`. A nonexistent validator escaped before the prior rollback block,
  leaving the target at `candidate_head`, SQL at `accepted`, and no durable
  post-publication failure. Successor `46631b7` applied one shared durable
  failure path to returned and raised validation failures, added the terminal
  ref CAS and post-commit reconciliation, and also introduced the later-read
  behavior rejected immediately below.
- Preserved rejected missing-ref/history candidate: exact pushed commit
  `46631b7da23b5a2bf6d2d569e975fb1fcf447293`, tree
  `d2cdd0a14bb73b2409de47a06a7259ea7e40fd52`, remains immutable and
  unaccepted. Exact review confirmed concurrent target advance and missing
  validator failures were durably fenced, then returned `REVISE` on two P1
  reconciliation defects. Target-ref deletion caused `_branch_head()` to throw
  before terminal evidence in the completion, rollback, post-SQL, and prior-read
  paths. Separately, an ordinary later target commit caused the old idempotent
  publication call to rewrite valid historical candidate/cleanup rows as
  failed. The current successor records a missing ref as observed `null` and
  preserves successful publication history independently from later target
  currentness.
- Preserved rejected stale-publisher candidate: exact pushed commit
  `eca370fcbfb30fca9e3b66fb6089f26ca2742f30`, tree
  `0e84935a8c09aacf1a5bb9d4fef3659bb1f09ddd`, remains immutable and
  unaccepted. Exact review confirmed the missing-ref and historical-successor
  paths, then returned `REVISE` on one P1 concurrent idempotency race. Two
  callers loaded `accepted`; the first failed post-publication validation and
  durably rolled back, while the queued second caller later reused its stale row,
  republished `candidate_head`, overwrote the failure evidence, and marked the
  cleanup completed. The current successor rereads under the physical lock and
  SQL-CAS-fences accepted-to-terminal candidate and running-to-terminal cleanup
  transitions in the same transaction.
- Preserved rejected validation-intent candidate: exact pushed commit
  `173280de6c973a806e411e0c15cf1ec40fc7f809`, tree
  `70be304a0fa02028dfac399b00684deaf4b0d9fe`, remains immutable and
  unaccepted. Exact review confirmed the queued-stale rollback, missing-ref,
  historical-successor, target-advance, missing-validator, and dirty-tree paths,
  then returned `REVISE` on one P1 publication-identity defect and one P2 index
  overclaim. A first caller could publish with no post validator and a later or
  queued caller requesting a valid failing validator would receive the earlier
  `published` result without executing or recording its stricter policy. The
  current successor adds migration 0025, durably binds the exact command before
  the Git effect, and rejects both later and queued policy mismatches. The index
  now limits post-SQL reconciliation to the actual completion boundary.
- Rejected-candidate closure matrix:

  | Finding | Governing invariant | Corrective delta | Focused regression | Affected mapped proof | Fresh exact review |
  |---|---|---|---|---|---|
  | branch advanced after preservation could be deleted | destructive cleanup binds and rechecks the exact inventoried physical object | repository lock plus exact branch identity and clean-worktree gate | `test_retirement_rejects_branch_advance_after_preservation` | operations, reconciliation, target profiles | closed by exact review of `76ca892` |
  | dirty tracked and untracked work was absent from restart | restart rehydrates every safe byte owned by the inventoried checked-out source | replay verified working-tree patch and safe untracked archive; receipt binds source, patch, status, bytes, modes | `test_unfinished_checked_out_branch_restores_dirty_and_untracked_bytes` | operations and reconciliation | closed by exact review of `76ca892` |
  | resolved replay allocated a duplicate wake and stranded recovery | one defect fingerprint owns one case, token, effect, and delivered wake across terminal replay | include resolved cases in lookup, exact target-state collision check, resolved fast path, explicit `sent` gate | `test_resolved_factory_recovery_replays_without_duplicate_wake_or_case`; `test_unsent_factory_wake_fails_closed_and_redrives_same_intent` | recovery and governed effects | closed by exact review of `76ca892` |
  | interrupted activation could overtake newer authority | one root has one serialized unfinished transition bound to its exact predecessor/current active state | durable root lock, unfinished-root gate, transition-root/payload/predecessor/current-pointer checks | `test_interrupted_activation_blocks_newer_activation_and_resumes_exact_transition` | operations and governed release | closed by exact review of `76ca892` |
  | receipt/release publication omitted durability barriers | no reported durable publication relies on an un-fsynced renamed file or directory entry | `atomic_write` receipts, file/tree directory fsync, release-root post-rename fsync, crash-safe persistent locks | staging and restart crash-recovery fixtures plus exact source audit | operations, governed release, reconciliation | closed by exact review of `76ca892` |
  | branch ref advanced after the last identity check could still be deleted | destructive cleanup must make the identity precondition and deletion one atomic Git operation | `12adc232` used expected-object compare-and-delete; the current successor eliminates physical Git deletion entirely | `test_retirement_rejects_branch_advance_after_preservation`; `test_retirement_preserves_worktrees_and_stashes_without_atomic_adapter` | operations, reconciliation, target profiles | ref-advance reproduction closed at `12adc232`; deletion path superseded safely |
  | a new active worktree could be admitted between branch check and ref deletion | cleanup must not strand live worktree authority on a deleted symbolic branch | record one failed no-physical-effect audit and require preserve/defer for branch, worktree, and stash retirement | `test_branch_retirement_preserves_new_dirty_worktree_admitted_after_inventory`; `test_redundant_branch_retirement_fails_closed_without_atomic_worktree_fence` | operations, reconciliation, target profiles | closed by exact review of `52acbaf` |
  | integration retirement and prepare-failure cleanup could force-delete pending bytes | every reconciliation lane retains tracked/untracked state until one proven no-loss retirement owner exists | preserve failed and terminal lanes; reject explicit lane retirement; rollback only the exact target ref by CAS | `test_accepted_branch_is_validated_published_and_lane_retirement_preserves_bytes`; `test_prepare_failure_preserves_integration_and_validation_lanes_with_pending_bytes`; `test_post_publish_failure_rolls_target_back` | reconciliation, operations, target profiles | closed by exact review of `91b8cac` |
  | mutable integration-lane bytes could pass validation for another committed candidate tree | every publication-authorizing validation observes only one exact immutable candidate identity through command completion | create a fresh detached `candidate_head` snapshot per phase, prove clean exact HEAD before, verify tracked/index currentness after, and retain every snapshot | `test_prepare_rejects_validation_against_bytes_other_than_candidate_head`; `test_post_publish_validation_rejects_dirty_snapshot_and_rolls_target_back` | reconciliation and target profiles | closed by exact review of `7c27b86` |
  | target ref could advance after validation but before terminal SQL publication | terminal publication must fence and reconcile the exact accepted ref at the completion boundary | no-op `update-ref` CAS immediately before SQL plus post-commit ref reconciliation | `test_publication_completion_rejects_concurrent_target_ref_advance` | reconciliation and target profiles | closed by exact review of `46631b7` |
  | validator setup or process spawn failure could bypass rollback and durable evidence | every known post-publication validation failure reaches one exact CAS compensation or explicit failed currentness record | normalize setup/spawn exceptions into bounded failure evidence, CAS rollback, and one terminal candidate/cleanup transition | `test_post_publish_validator_spawn_failure_rolls_back_and_records_failure`; `test_post_publish_failure_rolls_target_back` | reconciliation and recovery | closed by exact review of `46631b7` |
  | target-ref deletion could throw before terminal evidence | missing ref is an observed currentness value at every failure boundary | non-throwing ref observation records JSON `null` before the terminal candidate/cleanup transition | `test_target_ref_deletion_records_terminal_publication_failure` | reconciliation and target profiles | closed by exact review of `eca370f` |
  | later legitimate target successor could rewrite successful history as failed | completed publication and current target-head identity are separate facts | idempotent calls return the immutable published row; terminal completion remains fenced before success | `test_later_target_successor_preserves_historical_publication` | reconciliation and delivery history | closed by exact review of `eca370f` |
  | queued publisher could reuse stale accepted state and resurrect a rollback | one candidate has one monotonic exact publication outcome under concurrent callers | reread under repository lock; candidate and cleanup terminal writes use expected-status SQL CAS in one transaction | `test_concurrent_publisher_cannot_resurrect_rolled_back_candidate` | reconciliation, recovery, and delivery history | closed by exact review of `173280d` |
  | later or queued caller could substitute a different post-publication validation policy | publication idempotency binds the exact validation intent, not only the candidate head | migration 0025 stores the canonical command before Git publication; both published fast paths and the serialized path reject mismatches | `test_published_candidate_rejects_a_different_post_validation_policy`; `test_queued_publisher_rejects_a_conflicting_validation_policy` | reconciliation, target profiles, and delivery history | closed by exact review of `e82ee53` |
- Focused validation: `45 passed` in the operations, governed-release,
  reconciliation, and recovery-coordinator files; the four existing
  `TestStore` collection warnings remain unchanged. Mapped validation across
  advanced integration, controller, core, governed release, operational
  boundaries, operations, reconciliation, recovery, and target profiles:
  `95 passed` with the same four warnings. Runtime collection found `239`
  tests with only the seven existing collection warnings. Ruff format/check, mypy
  across `69` source files, compileall, diff check, and tracker verification are
  clean. The locked dev environment also exposed and the candidate removes one
  obsolete mypy ignore plus one redundant type cast; focused acceptance/libRSI
  regression proof is `11 passed`. No broad runtime suite was run.
- Isolated build/install proof: wheel SHA-256
  `7983cbc779b2c17d056a9a596e2d73f408058eeb9f513fb9197180d323f41c1b`;
  sdist SHA-256
  `3b8e150e919fcf1f7c2221b56437a8f167a01ee64ad070f1a4375733c597c5fc`.
  The exact wheel contains migrations 0024–0025 and a fresh isolated install
  reported both catalog and live database schema version `25`, including the
  durable publication-validation-intent column. The changed runtime-source
  hash-list root is
  `efaa39166064c6fa757158ef3d0de32c196665aac024054d054195b2bfaf2d65`;
  the changed-test hash-list root is
  `4e06cf790226d1b290697d51e5b772059ba11833c80bfae1163f3165a1613a0f`.
- Product-capability review:
  - Trigger: consequential durable delivery/recovery boundary and correction
    of a candidate that could lose unfinished work or overwrite newer release
    authority.
  - Frame identity:
    `docs/software-factory-v2-implementation-tracker.md`, Block 8, exact frame
    bytes at lines 52–84, SHA-256
    `c2b8110d2cf11edc3d7f52ecc0c6112f0f60ba9d091b6cbeb2e15e9b6bbb3851`.
  - Capability added or preserved: interrupted local delivery rehydrates one
    exact release/effect/workspace; unsupported physical Git retirement is
    audited or preserve/defer-fails before deleting branch, integration lane,
    validation snapshot, checkout, stash, dirty, or untracked authority;
    publication-authorizing validation is bound to one exact committed tree;
    terminal publication rechecks and reconciles the accepted ref; rollback
    changes exact ref authority without discarding checkout bytes; dirty and
    untracked work remain recoverable; missing refs still produce evidence;
    successful publication history survives later target successors; concurrent
    publishers cannot revive a rollback or substitute validation intent; a
    resolved case does not resume its target twice.
  - Paths compared: retry from current mutable Git refs; retain only the Git
    bundle; use process-local flags; or bind durable journals, exact inventory
    identities, bundle members, receipts, and external idempotency keys under
    filesystem/repository locks.
  - Selected level and owner: existing Factory release, operations,
    reconciliation, governance-effect, and recovery owners retain authority;
    no new service, provider, production, or semantic owner is introduced.
  - Protected-capability result: immutable evidence and newer release/Git
    authority survive every tested interruption, ref-advance race, and
    worktree-admission race; false delivery never consumes the resume token,
    and unfinished obligations retain their latest bytes.
  - Rejected alternatives: live-ref reconstruction loses the preserved point;
    committed-only restart loses dirty work; selector-only stash deletion can
    shift; ref-object CAS does not fence separate worktree admission; a receipt
    without directory fsync can vanish after reported success; and a new
    recovery row defeats exact-once resumption.
  - Tradeoff and uncertainty: exact hashing adds bounded local I/O, and
    preserve/defer retains redundant Git objects until a future adapter can
    prove one atomic identity-plus-worktree fence. That storage cost is accepted
    over silently stranding active work. Production activation and external
    delivery remain deliberately unqualified.
  - Frozen-candidate proof: exact pushed commit
    `e82ee5325c266d8891e86ab22ca7abfb2e369166`, tree
    `b5be73e4fd137e440ef6c0b72fe13ebb2f2525c1`; distinct exact-revision
    review returned `ACCEPT` with no P0, P1, or P2 findings after reproducing
    11 mandatory and prior regression cases. Current bounded behavioral proof
    is `45` focused and `95` mapped passes, exact installed schema `25`, and the
    artifact/source/test roots above.
- Candidate posture: exact candidate `e82ee53` is accepted. All effects used
  isolated local/test targets; no
  production activation, external notification, utils consumption, service/API
  qualification, migration cutover, or terminal qualification occurred.

### Stop

Stop before service/operator qualification.

---

## Block 9 — Qualify service, API, operator, and deployment-ready boundaries

Status: `accepted`

### Objective

Provide bounded service/API/operator surfaces over the same runtime and prove
deployment readiness without creating a hosted product.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: operators and embedded products can submit,
  inspect, steer within authority, and retrieve outcomes.
- Potential capability loss or regression: transport/UI could become authority
  or expose arbitrary effects/secrets.
- Protected-capability effect: typed workflows, currentness, authorization,
  privacy, and audit remain server-enforced.
- Architecture and operating-model effect: dashboard and APIs become
  projections over one engine.
- Tradeoff and source evidence: v2 plan embedded/service requirement and
  existing dashboard/API owners.

### Inputs and dependencies

- Blocks 2, 6, and 8; exact pushed utils Block 10
  `embedded-service-contract` and Block 11 `runtime-manifest` revisions for
  their mapped adoption. Service work not using those packages may proceed
  before they are available, but its dependent acceptance may not.

### Required work

- Complete service schemas, health/readiness, bounded events, authorization,
  idempotency, graceful shutdown, operator views, and deployment documentation.
- Adopt the shared structural conformance and descriptive runtime-manifest
  packages without moving Factory lifecycle, authority, or state into them.

### Scope and non-goals

- In scope: loopback/internal service readiness and host contracts.
- Not in scope: public auth, tenant billing, fleet control, or Internet
  deployment.
- No arbitrary command surface.

### Deliverables and recorded state

- Service/API/CLI, dashboard projections, runbook, and security/restart tests.

### Resource and economy contract

Use disposable loopback servers and content-minimized fixtures.

### QA and independent review

Review auth/effect boundary, secret/content minimization, restart, API/runtime
equivalence, and false authority.

### Acceptance

- Service and embedded users observe the same current mission state and can
  perform only registered authorized operations. Both hosts pass the accepted
  shared structural contract, and runtime manifests bind exact descriptive
  component/protocol/schema roots without representing authority.

### Negative tests

- Reject session authority, arbitrary commands, secret leakage, oversized
  requests, stale workflow hashes, transport-only completion, a pre-acceptance
  utility package, manifest authorization/acceptance fields, or a shared
  structural contract that owns Factory state.

### Completion evidence

- Start baseline: clean pushed Block 8 acceptance/B9-start successor
  `1afe96ed02da5588de0340cc2abc8e26e67a4ce6`; Blocks 0–8 are accepted and
  Block 9 is the sole dependency-eligible frontier. No Block 0 work was
  reopened and the utils repository was not modified.
- Exact utils adoption: Factory package data now binds qualified producer
  revision `a5659745a7cbcbb002b5f06051f6ed9826f721a7`, producer tree
  `f6b5cd45b6692c98c93bb3f19b2d4f2ddf361ec1`, qualification matrix
  `0888bed363b63842c37baa8187c9883cdddff73d936596e497e4e013341cd849`,
  technical root
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`,
  and the separately accepted source commit/tree, package tree, version, wheel
  SHA-256, content root, size, member count, and public-contract roots for both
  `embedded-service-contract` and `runtime-manifest`. Startup accepts only
  explicitly supplied wheel paths after reproducing exact accepted wheel
  SHA-256 values
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`
  and
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`;
  renamed, modified, pre-acceptance, bare-registry, or copied-source inputs
  fail closed. The accepted unpublished/no-license boundary remains explicit.
- Shared contracts and state: one Factory-owned adapter maps the existing
  embedded and standalone host facades to the exact accepted neutral lifecycle
  values while retaining all mission state and semantics in the Factory engine.
  Both facade shapes pass the package's unmodified structural conformance suite
  against a content-minimized deterministic Factory-owned probe engine, and a
  real durable runtime proves both adapters observe byte-equivalent current
  mission status and events. The adapter retains only its Factory host, shared
  module, and immutable host contract; the shared package gains no Factory
  persistence, process, scheduling, authority, QA, acceptance, or release
  owner.
- Runtime manifest: the accepted package emits canonical descriptive metadata
  for the exact Factory component and exact utility content roots. Current
  database, engine, and loopback-service protocol/schema roots are respectively
  `17883bbecd3e7fd78ff5b2873c0d64d43a46f1e8830f2d6424ee0fc3e7cb3143`,
  `26f1c662aa04418241487c668f8948d1463ab19ab9fcb4037415f4f7ea611725`,
  and `4a755f9c02b51e522540ebaa725523f453603bf49e9e6eddb5df801c1a032cb4`.
  Recursive validation rejects authorization, acceptance, permission, or
  release-authority fields, and the manifest is never consumed as operational
  authority.
- Service/operator boundary: the production entrypoint requires exact utils
  wheel paths, an exact component root, and a private regular non-symlink token
  file. Public routes expose only content-minimal liveness/readiness; every
  `/api/*` route uses constant-time bearer authentication. Every POST also
  binds the exact current service-protocol root, so stale workflow hashes fail
  closed. The general engine route exposes only start, status, continue,
  outcome, and bounded events; arbitrary commands, paths, cancellation, and
  transport-only completion are unavailable. Governed cancellation uses a
  separate scoped, expiring, one-time operator token and the existing canonical
  cancellation owner. Request targets/bodies, query fields, responses, event
  pages, error detail, mission IDs, and cancellation reasons are bounded;
  chunked/malformed/oversized input is rejected. Operator views project explicit
  columns and omit authority/resource/evidence JSON, external task/thread IDs,
  repository paths, commands, and other unbounded content. Browser rendering
  uses text nodes without HTML injection and keeps its transport token only in
  memory. Event cursors are contiguous within each mission even though the
  private SQL ledger retains a global insertion sequence. The declared
  component root is recomputed from every authoritative member of the imported
  Factory package and any caller-supplied mismatch fails before readiness.
  Each accepted socket has a five-second request-read deadline.
  `SIGINT`/`SIGTERM` stop request admission, close the listener, and allow a
  finite ten-second drain, so an idle/partial client or stuck internal handler
  cannot hang process shutdown. An operator decision is durably accepted before
  its effect; if interruption occurs afterward, only a byte-equivalent replay
  with the same consumed token can resume that exact decision. The token cannot
  authorize a different request. Durable mission state survives restart. The
  runbook records the internal/loopback-only posture and exact credential,
  probe, restart, and artifact requirements.
- Product-capability review:
  - Trigger: consequential Block posture; an operator/service interface and two
    accepted shared utility packages become active runtime inputs.
  - Capability added or preserved: embedded products and a local operator can
    use one current engine through bounded typed surfaces while exact
    currentness, privacy, independent authority, durable state, QA, acceptance,
    and terminal outcome ownership remain server-side.
  - Paths compared: retain the unauthenticated Block 2 reference API; let one
    bearer token authorize every engine effect; add public OAuth/multi-tenant
    hosting; copy or reimplement utils contracts locally; or select a
    loopback-only authenticated projection with a separate one-time operator
    authority and exact qualified binary adapters.
  - Selected level and owner: Factory owns transport authentication, protocol
    currentness, adapters, pins, projections, lifecycle semantics, persistence,
    effects, and acceptance. Utils owns only neutral structural values and
    descriptive manifest serialization. Existing Reporting and engine owners
    retain governed effects.
  - Protected-capability result: session identity, stale client hashes, a
    transport success, provider completion, manifest metadata, or shared
    conformance values cannot authorize a Factory effect or manufacture
    acceptance; secrets and arbitrary effects do not enter the projection.
  - Rejected alternatives: the unauthenticated API leaks internal state; a
    bearer-as-authority design collapses transport and governance; hosted auth
    activates an unrequested product; copied/reimplemented utility code loses
    the accepted producer identity and duplicates ownership.
  - Tradeoff and uncertainty: operators must supply two exact internal wheels,
    a private token file, an exact component root, and the current service
    protocol root. This is deliberate fail-closed local deployment friction;
    public distribution, licensing, multi-tenancy, and fleet operation remain
    out of scope.
- Rejected candidate and remediation closure: exact pushed candidate
  `5a2f2260c7491bd2d82c74392087f67daee2eb32`, tree
  `79453a2f608c98d2291f201c03a851d8a6b5aa67`, is preserved and unaccepted after
  independent review returned three P1 findings: the shared adapter exposed the
  global SQL event sequence instead of a run-local cursor; an arbitrary
  syntactically valid component root could enter the runtime manifest; and
  daemon request threads could outlive graceful shutdown after consuming an
  operator token. The bounded successor projects per-mission event ordinals and
  status counts, hashes and rechecks the installed Factory package bytes, and
  uses a draining non-daemon request server. Focused regressions prove two
  interleaved missions retain contiguous shared-contract cursors, false
  component roots reject, and shutdown blocks until the already accepted
  operator action reaches durable `applied` state.
- Exact successor `9c76fc8f96a066eefbe34abb5df4c094fd9b543a`, tree
  `956b416dfb220954bdcfddb9b7f44dead0651fe1`, is also preserved and unaccepted.
  Fresh independent review closed the event-cursor and component-identity
  findings, and confirmed completing operator handlers drain, but returned one
  P1 because idle/partial sockets and an indefinitely blocked handler could make
  graceful shutdown unbounded. The current bounded successor adds exact
  request-read and drain ceilings plus consumed-token replay limited to the
  already accepted request root. Regression coverage admits real idle/partial
  sockets before shutdown and proves the exact accepted decision resumes
  idempotently while a different request remains unauthorized.
- Focused and mapped proof: `50 passed` across API, engine hosts, exact qualified
  utils, reporting/operator authority, operational ownership boundaries,
  entrypoints, and composition; one documented legacy `TestStore` collection
  warning. Negative fixtures cover session-as-authority, absent/wrong service
  credentials, stale service roots, general-route cancel/complete, arbitrary
  command keys, oversized bodies, secret/unbounded projection fields, insecure
  token files, renamed/modified utility artifacts, manifest authority fields,
  shared-package state ownership, cross-mission cursor gaps, arbitrary component
  identities, graceful-shutdown operator stranding, idle/partial socket hangs,
  and consumed-token request substitution. Full runtime collection is 255 tests
  with seven documented legacy collection warnings. Ruff
  format/check are clean across 105 files, mypy is clean across 71 source files,
  compilation is clean,
  and detailed-tracker verification passes. Per the range's economy rule, the
  broad runtime suite remains deferred to Block 12.
- Isolated build and installed-artifact proof: the successor wheel SHA-256 is
  `7ac9fa4b746d2374ceb1291f9a6f2ab4126891f2d948120243f9ac5ae77d48ec`
  and the sdist SHA-256 is
  `b5f42764d4b6243c5ff7d2539573f71347a07427a5df18f23d51a58571ef26b7`.
  The isolated wheel import loaded Factory from its installed wheel path,
  reloaded both exact accepted utils artifacts, recomputed installed component
  root `9683cadba6fa25e6f1e4bbfd4ebdcc6263ed14cd1aa3c1b2a2df54a56b4c8baf`,
  reproduced current engine and service protocol roots, and retained the
  Factory wheel as the actual import source.
- Accepted exact candidate: pushed commit
  `7f4d55f2e87c4eaeae0731fdb22ef7fb2f793b0e`, tree
  `a2ac7a1f1d706f851db5ccb84d768a3af109a36a`, with a clean worktree and
  local/remote parity at review. Distinct read-only replacement review accepted
  that exact revision with no P0, P1, or P2 findings. The review independently
  confirmed finite socket/read deadlines, bounded shutdown drain, exact
  consumed-token replay, mission-local contiguous event cursors, installed
  component-root binding, and no Block 9 scope regression.
- Candidate posture: both rejected candidates, all four findings, and their
  corrective history remain preserved and unaccepted. Exact pushed successor
  `7f4d55f2e87c4eaeae0731fdb22ef7fb2f793b0e` is the accepted Block 9
  implementation checkpoint. This status reconciliation opens Block 10; it
  does not rewrite the reviewed candidate or replay its proof.

### Stop

Stop before cross-domain proof.

---

## Block 10 — Prove neutral content profile and external extension

Status: `accepted`

### Objective

Demonstrate that the full runtime handles a non-software mission and an external
domain extension without embedding consumer code.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: credible domain-neutral operation.
- Potential capability loss or regression: a superficial fixture could hide
  Git/software assumptions or smuggle Patent Studio into the core.
- Protected-capability effect: generic mission/work/QA/supervision/delivery
  contracts remain unchanged.
- Architecture and operating-model effect: one neutral profile lives here; an
  external consumer owns its domain adapter.
- Tradeoff and source evidence: v2 plan phases 6–7 and direct user OSS boundary.

### Inputs and dependencies

- Blocks 5–9.

### Required work

- Complete a maintained invention-neutral content-production mission.
- Prove an external extension can register and run without its domain code,
  identifiers, or schemas entering the OSS core.

### Scope and non-goals

- In scope: neutral fixture and extension conformance.
- Not in scope: Patent Studio implementation or real patent content.
- Do not use OMNI/Celltonomy as the neutral fixture.

### Deliverables and recorded state

- Neutral profile, rooted mission fixture, extension contract, static leakage
  audit, and outcome evidence.

### Resource and economy contract

Use small deterministic content and offline providers.

### QA and independent review

Review semantic neutrality, actual artifact quality, no domain leakage, and
reuse of the real engine.

### Acceptance

- Both proofs reach current delivered outcomes through unchanged core contracts.

### Negative tests

- Reject Git-only core fields, Patent Studio/OMNI/Celltonomy identifiers,
  project-specific branch logic, fixture-only alternate engine, or build success
  without content QA.

### Completion evidence

- Start baseline: exact pushed Block 9 candidate
  `7f4d55f2e87c4eaeae0731fdb22ef7fb2f793b0e`, tree
  `a2ac7a1f1d706f851db5ccb84d768a3af109a36a`, accepted by distinct
  exact-revision review with no P0–P2 findings. Blocks 0–9 are accepted and
  Block 10 is the sole dependency-eligible frontier.
- Maintained neutral profile: `ContentTargetProfile` is composed beside the
  software profile and owns only exact-currentness-fenced physical content
  effects. A registered source set proceeds through source collection, planning,
  drafting, deterministic revision, factual/structural/style review, escaped
  HTML rendering, internal delivery, and exact receipt verification. Its closed
  effect contract accepts no caller path, command, authority, approval,
  acceptance, or arbitrary content. Rendering requires all three current quality
  reviews; delivery and verification reject changed bytes, receipts, definitions,
  symlinks, non-regular members, stale roots, and out-of-order effects.
  Its complete definition is stored with the target state, and a restarted
  CoreService can reopen and resume that exact registration. The shared registry
  holds one target-local lock plus the profile-owned currentness context from its
  last pre-effect observation through the adapter effect and post-effect snapshot;
  the maintained content profile implements that context with a cross-process
  regular lock outside the target tree. Every profile rechecks both expected roots
  inside its authorized effect, and the maintained content revision includes every
  physical target member.
- Real content mission: the maintained operations-brief fixture uses the actual
  CoreService mission, program, capability, obligation, selected work, leased
  execution, target registry, QA, governance, independent
  candidate/integrated/installed/terminal acceptance, program-range closure,
  continuation, and terminal mission-completion owners. Its deterministic final
  target revision is
  `126e2ff39b99c62bb748de009e64b5967614861d9f8c7fd7eecaf3098cdfde10`,
  currentness root
  `77deff99120bb2a2c99e5f30368b33d2780b5648ad49c0147dcf8b2f65f87545`,
  and delivered HTML SHA-256
  `b9844f519ffc5a0b1737c9b70223a211a318d062c7576dd899297948eaf62206`.
  Assertions inspect the delivered title, factual statement, exact source
  citation, and all three review artifacts; build success alone is ineligible.
- Domain-neutral candidate bridge: `QAService.submit_profile_candidate` binds a
  successful non-workspace execution to the work-declared profile/target, exact
  registered snapshot revision/currentness and attributes, acceptance spec, and
  current program revision. Profile or target substitution, a workspace
  candidate, stale target bytes, failed/unbound execution, or changed work
  version fails before submission. The canonical owner always installs one
  required currentness check and one required independent review even if the
  caller's acceptance specification omits them or marks them optional. Every
  requirement/result shares the exact execution-derived candidate root; a
  second execution submitting the same physical revision stales the complete
  earlier QA/evidence lineage and starts new requirements. It also stales every
  prepared or accepted lifecycle stage, governed contract, decision, and review
  rooted in the superseded candidate. Each replacement stage identity and
  material root binds the new execution-derived candidate root, so an accepted
  stage from a same-revision prior execution cannot become the replacement
  candidate's predecessor. Completion requires a passed review for that exact
  root by a non-implementer. The two real missions perform those steps before
  candidate acceptance. Profile-currentness evidence/result recording and
  independent-review execution/evidence/result recording each occur in one
  transaction that rechecks the non-stale exact requirement before any durable
  child record. Work promotion requires the already-passed QA state and no
  longer writes `qa_status='passed'`; every
  candidate/integrated/installed acceptance re-observes the registered physical
  target and holds its profile-owned fence through the authoritative stage and
  work-promotion write. Terminal preparation instead derives one deterministic
  composite scope from every selected, non-cancelled, installed profile work
  item and its exact candidate, revision, and currentness roots. Terminal
  promotion acquires every target fence in that order and rechecks the complete
  set inside the same transaction as the authoritative write; mission
  completion fences and rechecks the same exact set again. Proposed, deferred,
  unselected, and cancelled profile work cannot enter that terminal scope. A
  mission containing canonical profile work rejects an unbound or partial
  terminal stage. The existing staged lifecycle remains the sole
  work-acceptance owner.
- External extension proof: `runtime/tests/external_extension_fixture.py` owns
  its sample observation key, target ID, schema, snapshots, and physical effects
  outside `runtime/src/software_factory`. It registers through the unchanged
  public `TargetProfileRegistry` and runs a second real mission through the same
  generic helper and terminal owners. Its deterministic final revision is
  `3a79243f82538cb658e68055bc4d335a4eaba3d98908c19a399de63cef2fc3d7`,
  currentness root
  `b81063f997c8b9949f0bb957f699db5b0f17912ef8bea46b091a40c551e10e39`,
  and delivered summary SHA-256
  `c22da8a20c8cc99e21ea717dd7399adec7002b6c4ef2b98a7a4af6ec091dd6f4`.
  Static leakage proof scans the Factory package for that extension's key,
  target, and schema markers plus prohibited consumer names, and separately
  rejects repository, branch, or Git snapshot fields in the content profile.
- Contract and packaging: the maintained external registration, ownership, and
  negative boundary is
  `docs/software-factory-v2-content-extension-contract.md`, SHA-256
  `5d07c1c4e724c0f26a71f16887a7916fc3cfefef6d49ebd0a8385f0c8e152633`.
  The corrected repository-native build envelope is `uv build`; the initial
  no-isolation diagnostic was invalid because the selected development venv did
  not contain the declared setuptools backend and was not reused as proof. The
  isolated wheel and sdist SHA-256 values are respectively
  `83402791b7824f01ce5687a0e6beedb619e81da76fbbb7d5a7705651c862d146`
  and
  `fa0bf09a7272c6d2a1fbd5848fbb8777b415136e5b93a40029f7422819c4db9a`.
  A target-directory installation imported version `2.0.0.dev6` from the built
  wheel, exposed the content profile, and composed profile keys `content` and
  `software`; the sdist contains both maintained Block 10 test modules.
- Preserved rejected candidate: exact pushed commit
  `e60b9990a2453888dfff991dc8c46fb5ca251d58`, tree
  `2e301540f53dae67e5f2c55e1980ce1351c348f1`, remains immutable and
  unaccepted. Distinct exact-revision review returned three P1 findings: target
  profile candidates could not complete canonical QA and the dogfoods advanced
  acceptance without it; maintained target definitions could not be reconstructed
  after restart; and target/QA currentness checks did not hold one physical-effect
  fence through their authoritative action. The successor retains every earlier
  capability while adding the canonical non-workspace QA path, durable reopen,
  physical-tree-bound revisions, shared target locks, and adapter-internal dual-root
  rechecks. No rejected history was amended or removed.
- Preserved second rejected candidate: exact pushed commit
  `44f3e83095550b6cf0db18c08ac314cce110e3f3`, tree
  `3a7d7f08943abc0e36bc030d5088a2224e222606`, remains immutable and
  unaccepted. Distinct exact-revision review confirmed the durable target,
  cross-process fencing, extension, neutrality, and package boundaries but
  returned three P1 findings: a caller could omit required independent review;
  a same-revision execution could inherit another execution's QA lineage; and
  staged acceptance trusted pre-drift roots after canonical QA released its
  physical fence. The current bounded successor forces the two canonical
  requirements, binds and invalidates QA by exact execution-derived candidate
  root, requires a passed non-implementer review for that root, and re-observes
  physical currentness under the profile fence through every authoritative
  acceptance write. Negative dogfood weakens the caller specification,
  resubmits the same revision from a new execution, and injects physical drift
  after outcome reconciliation. No rejected history was amended or removed.
- Preserved third rejected candidate: exact pushed commit
  `b408e179b7254ce54aec6ac396dd797159e27fe5`, tree
  `0461453383e041f60ca53195ab8767b62b1e02be`, remains immutable and
  unaccepted. Distinct exact-revision review returned two P1 findings and one P2:
  acceptance-stage identity/material did not bind the active execution-derived
  candidate root; a mission-scoped terminal stage could bypass profile
  currentness; and stale currentness/review attempts could leave orphan durable
  children before detecting the stale requirement. The current successor binds
  every profile stage and predecessor chain to the exact candidate root, stales
  its full staged governance lineage on resubmission, rejects mission-scoped
  terminal bypass, and couples each QA observation to its final stale check in
  one immediate transaction. Ownership remains explicit: the acceptance
  lifecycle invalidates stage rows, governance invalidates its contracts,
  reviews, and decisions, and QA owns only requirements/results. Negative proof
  reuses a same-revision accepted candidate stage, resubmits through a second
  execution, observes every old stage/governance record become stale or
  invalidated, rejects both stale QA calls without adding evidence, executions,
  or results, and completes only through a new candidate-root scope.
- Preserved fourth rejected candidate: exact pushed commit
  `777b2d2a019c89b922469b4cbfb4ac979fbd18fa`, tree
  `f9b1be94e54a5585aaf8c0ee52d5f50f772884a9`, remains immutable and
  unaccepted. Distinct exact-revision review returned one P1 finding: terminal
  acceptance fenced only its primary profile work while another selected target
  in the same mission could drift, and the terminal membership query included
  proposed, deferred, unselected, and cancelled profile rows. The current
  successor replaces the single-work binding with a digest-rooted composite of
  every selected, non-cancelled, installed profile work item and its exact
  candidate, revision, and currentness roots. It acquires all target fences in
  deterministic order through the terminal acceptance write and revalidates the
  identical set under those fences at mission completion. Negative proof drifts
  the non-primary target immediately before terminal acceptance and separately
  proves that proposed and cancelled profile work do not enter terminal scope.
  No rejected history was amended or removed.
- Preserved fifth rejected candidate: exact pushed commit
  `8edf34b917694e6aa9e9942287b0668c1dd07bfd`, tree
  `f2c60649d959e9bfd984afb9b7d4f645106bbff9`, remains immutable and
  unaccepted. Distinct exact-revision review returned one P1 finding: two
  selected installed work items may legitimately bind the same physical target
  at identical revision/currentness but different execution-derived candidate
  roots, and the composite fence loop entered that target twice even though the
  profile contract does not require a reentrant physical fence. The current
  successor preserves both work bindings in terminal identity while grouping
  the physical fence layer by `(profile_key, target_id)`, rejecting conflicting
  revision/currentness roots before any acquisition, and entering each unique
  target once in deterministic order. A deliberately non-reentrant bounded
  regression proves same-target deduplication and zero-entry conflict rejection.
  No rejected history was amended or removed.
- Focused and mapped proof: `70 passed` across content/external profiles, target
  profiles, execution/QA, acceptance lifecycle, core, composition, operational
  boundaries, engine hosts, and v2 entrypoints. Ruff format/check are clean over
  109 files, mypy is clean over 73 source files, compilation is clean, and full
  runtime collection is 269 tests with the seven documented legacy `TestStore`
  collection warnings. Per the range economy contract, the broad runtime suite
  remains deferred to Block 12.
- Product-capability review:
  - Trigger: consequential Block posture and the first maintained non-software
    physical target plus an external consumer registration path.
  - Capability added or preserved: non-software targets now reach current
    delivered outcomes while the same Factory mission, work, QA, supervision,
    independent acceptance, and continuation owners remain authoritative.
  - Paths compared: encode content steps in generic core tables; add a second
    content-specific runtime/engine; use a test-only fixture that writes an
    artifact; or select one bounded maintained content physical adapter plus a
    consumer-owned protocol implementation registered into the existing engine.
  - Selected level and owner: the content profile owns only registered physical
    source/document/render/delivery effects; the external consumer owns its
    domain schema/effects; existing generic services own every operational and
    acceptance transition.
  - Protected-capability result: profile completion, rendered bytes, execution
    success, or registration cannot manufacture QA or acceptance; a host restart
    retains the target's exact definition and progress; physical effect and QA
    recording share one target-local and cross-process currentness fence; and no
    consumer-domain code, identifier, schema, or Git-only field enters generic
    runtime contracts.
  - Rejected alternatives: generic content schemas would overgeneralize the core;
    a second engine would split lifecycle authority; a fixture-only path would
    not prove real mission continuation or outcome closure.
  - Tradeoff: the maintained profile intentionally supports one small
    deterministic cited-document contract rather than a universal document
    platform. New domains remain external extensions until another accepted
    shared need justifies a bounded core contract.
- Independent review: exact pushed candidate
  `5988b3d7dd9bf3fd2720842abfb810f8e0a0cc30`, tree
  `c35773d65cf9040156d70cab31c84047d3b80e85`, was clean and at local/remote
  equality. Distinct exact-revision review returned `ACCEPT` with no P0–P2
  findings after independently confirming full composite work identity, unique
  deterministic physical-target fencing, pre-acquisition conflict rejection,
  acceptance and mission-completion revalidation, bounded duplicate-target
  regressions, and preservation of all five rejected candidates and eleven
  findings.
- Acceptance posture: `accepted`. Rejected exact candidates `e60b999`,
  `44f3e83`, `b408e17`, `777b2d2`, and `8edf34b` and all eleven review findings
  remain immutable and preserved. Blocks 11–12 and the terminal observable
  outcome remain open. No migration, legacy retirement, production activation,
  utils mutation, registry resolution, public-installability claim, or release
  effect occurred in this Block.

### Stop

Stop before migration and legacy retirement.

---

## Block 11 — Migrate, cut over, and retire duplicate legacy paths

Status: `in-progress`

### Objective

Move existing state and consumers to the accepted v2 owners, preserve
compatibility where declared, and remove duplicate active authorities.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one supportable runtime without shadow ownership.
- Potential capability loss or regression: premature deletion could strand
  state or break installed skills/dashboard consumers.
- Protected-capability effect: current releases, historical evidence, migration
  rollback, and user-visible workflows remain available.
- Architecture and operating-model effect: shadow comparators retire after
  exact parity and migration proof.
- Tradeoff and source evidence: v2 plan phases 7–8 and Block 0 map.

### Inputs and dependencies

- Blocks 6–10.

### Required work

- Migrate real representative state, cut over entrypoints, verify installed
  packages/skills/dashboard, remove duplicates, and prove rollback/idempotency.

### Scope and non-goals

- In scope: v2 cutover and declared compatibility.
- Not in scope: production activation outside the isolated acceptance target.
- Historical evidence remains immutable.

### Deliverables and recorded state

- Migration scripts/receipts, compatibility report, deletion ledger, and
  rollback proof.

### Resource and economy contract

Dry-run first; snapshot exact state; execute one frozen migration and one
rollback/reapply cycle.

### QA and independent review

Review no-loss, currentness, one-owner posture, compatibility, and installed
behavior.

### Acceptance

- No mission, work, QA, supervision, semantic, release, or lifecycle concern
  has two active writers.

### Negative tests

- Reject partial migration, orphaned obligations, stale installed release,
  non-idempotent retry, unreviewed deletion, or compatibility route as new
  authority.

### Completion evidence

- Start baseline: exact pushed Block 10 candidate
  `5988b3d7dd9bf3fd2720842abfb810f8e0a0cc30`, tree
  `c35773d65cf9040156d70cab31c84047d3b80e85`, accepted by distinct
  exact-revision review with no P0–P2 findings. Blocks 0–10 are accepted and
  Block 11 is the sole dependency-eligible frontier.
- Start posture: preserve historical and rejected bytes while proving one
  frozen real-state migration plus rollback/reapply, exact installed package,
  skill, entrypoint, and dashboard behavior, one active writer for every
  lifecycle concern, and removal or inert archival of mapped generated residue,
  dashboard-local RPC ownership, and the retired libRSI shadow comparator. The
  exact qualified utils client remains an unpublished/no-license internal
  artifact supplied by path and verified by producer/source/tree/content/version
  and artifact hashes; bare registry resolution and utils repository mutation
  remain prohibited.

### Stop

Stop before terminal qualification or release activation.

---

## Block 12 — Freeze and audit the complete v2 runtime

Status: `not-started`

### Objective

Qualify one exact revision and hand off truthful build/release evidence without
deploying or activating it.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one reproducible release candidate with verified
  observable outcomes.
- Potential capability loss or regression: broad green tests could obscure an
  unproven provider, service, or actual-delivery boundary.
- Protected-capability effect: every retained capability and limitation is
  explicit at handoff.
- Architecture and operating-model effect: terminal proof covers embedded,
  service, software, neutral, libRSI, provider, QA, and delivery paths.
- Tradeoff and source evidence: v2 plan definition of done.

### Inputs and dependencies

- Block 11, one frozen exact commit, current utils Blocks 14–15 qualification
  for every consumed shared package, and the exact Block 16 terminal posture.

### Required work

- Run the acceptance matrix, security/crash/concurrency/migration checks,
  wheel/install/entrypoint proof, real-provider diagnostic if authorized,
  artifacts/checksums/runbook, and independent outcome audit.
- Reconcile every utility pin to its accepted producer commit, package
  version/artifact, compatibility root, and current qualification; record the
  no-license/unpublished consequence for distribution and release.

### Scope and non-goals

- In scope: release-candidate qualification and handoff.
- Not in scope: deployment, release activation, announcement, or hosted
  successor implementation.
- Adapter-only boundaries must be labeled.

### Deliverables and recorded state

- Exact source archive, wheel, checksums, acceptance evidence, independent
  audit, capability reconciliation, and successor recommendation.

### Resource and economy contract

Run focused currentness checks first and the broad frozen matrix once. Reuse
unchanged accepted Block proof.

### QA and independent review

Distinct final review inspects source, installed artifacts, operator-visible
dogfoods, limitations, and actual outcome rather than summaries alone.

### Acceptance

- Every verification-matrix row is current at the same revision; no retained
  gap contradicts the primary outcome. Every consumed utility is current at
  one utils Blocks 14–15-qualified package set and no handoff overstates public
  installability, reuse rights, redistribution, or release authority.

### Negative tests

- Reject mixed revisions, missing artifact provenance, simulated provider
  labeled live, stale migration proof, missing operator outcome, unqualified or
  stale utility pins, license/publication overclaim, or activation without
  authority.

### Completion evidence

Pending.

### Stop

Stop before production deployment, public release, hosted multi-tenant
implementation, or consumer-domain mutation.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| One operational authority | 1 | 3, 6–8, 11 | 12 |
| Embedded/service equivalence | 2 | 3–9 | 12 |
| Autonomous safe continuation | 3 | 4–8 | 12 |
| Replaceable providers/app-server boundary | 4 | 6, 9–10 | 12 |
| Shared utility package currentness | 4, 9 | 10–11 | 12 |
| Target profiles and effects | 5 | 8, 10–11 | 12 |
| QA/supervision/acceptance | 6 | 7–12 | 12 |
| libRSI ownership split | 7 | 8, 10–11 | 12 |
| Delivery/release/recovery | 8 | 9–11 | 12 |
| Service/operator safety | 9 | 10–11 | 12 |
| Domain neutrality | 10 | 11 | 12 |
| Migration/one-owner cutover | 11 | 12 | 12 |

## 9. Final completion definition

The tracker is complete only when every Block is accepted at exact current
revisions, the frozen terminal matrix passes, distinct review confirms the
actual embedded and service outcomes, one-owner and domain-neutrality audits
pass, Git evidence is pushed, and no Block crossed its Stop. Completion does
not deploy a hosted service, activate a release, or grant Patent Studio
authority.
