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
| 1 | Operational authority and persistence boundaries | 0 | `in-progress` |
| 2 | One embedded/standalone engine contract | 1 | `not-started` |
| 3 | Work graph, scheduling, continuation, and concurrency | 1, 2 | `not-started` |
| 4 | Agents and replaceable provider runtime | 2, 3 | `not-started` |
| 5 | Target profiles, workspaces, and authoritative effects | 3, 4 | `not-started` |
| 6 | QA, supervision, acceptance, and outcome closure | 3–5 | `not-started` |
| 7 | libRSI semantic integration and duplicate removal | 1, 3, 6 | `not-started` |
| 8 | Delivery, release, recovery, and reconciliation | 5–7 | `not-started` |
| 9 | Service/API/operator and deployment-ready boundaries | 2, 6, 8 | `not-started` |
| 10 | Neutral content profile and external-extension proof | 5–9 | `not-started` |
| 11 | Migration, compatibility cutover, and legacy retirement | 6–10 | `not-started` |
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

Status: `in-progress`

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

- Acceptance posture: `candidate`; independent exact-revision review is
  pending, so Block 1 remains `in-progress`.
- Frozen implementation candidate: branch
  `agent/software-factory-v2-native-refactor`, commit
  `79adac40ffb5650ed46fe78f73d091109b7602e4`, tree
  `0f82f5b0ed23b2e9390505cc755660d54e60df37`, pushed with local/remote
  parity and a clean worktree.
- Migration and persistence boundary:
  `software_factory.database.Database` is the one implementation;
  `DatabaseStore` and `Store` are exact compatibility aliases. The active
  migration catalog is contiguous and file-exact from 1 through 20, the
  conflicting `0008_supervision.sql` path is retired, and migration 19
  reconciles runtime-referenced acceptance, observation, learning, reflection,
  hypothesis, and experiment tables without reusing legacy semantic rows.
- Operational owner boundary:
  `runtime/src/software_factory/ownership.py` declares exactly one primary
  module for each lifecycle table and the bounded coordinators allowed to join
  its transactions. `CoreService` composes one shared owner graph;
  `AdvancedServices`, API, daemon, CLI, and skill entrypoints reuse that graph
  instead of creating alternate supervision, learning, operations, reporting,
  migration, release, or recovery owners.
- Owner documentation:
  `docs/software-factory-v2-operational-ownership.md` records dependency
  direction, lifecycle/table ownership, migration lineage, semantic separation,
  and the later Block 2/5/7/11 cutovers. It explicitly rejects a universal
  entity model.
- Coupled-transition safety: nested database transactions use savepoints, so a
  failed inner transition rolls back only its own writes while an outer failure
  rolls back all nested writes. Operator schedule, work-cancellation, and
  incident-acknowledgement effects now route through `ReportingService`,
  `WorkItemService`, and `SupervisionService` rather than direct API writes.
- Focused Block 1 pytest command over core, composition, controller, execution,
  QA, supervision, acceptance, learning, migration, API, reporting, entrypoint,
  and new boundary tests completed `82 passed` with one harmless legacy
  pytest collection warning; no broad runtime matrix was run.
- Static baseline closure:
  `ruff check runtime/src runtime/tests` passes; `ruff format --check
  runtime/src runtime/tests` reports all 78 files formatted; mypy reports no
  issues across all 52 `runtime/src/software_factory` modules. Mechanical
  formatting closes the exact Block 0-assigned static debt and changes no
  lifecycle ownership.
- Negative proof:
  `runtime/tests/test_operational_boundaries.py` rejects inert or duplicate
  migrations, applied checksum/name drift, unknown/gapped histories, reverse
  persistence/service or service/host imports, undeclared lifecycle writers,
  partial nested commits, and operational foreign-key dependence on semantic
  tables. The advanced integration proof also asserts that the retired
  alternate supervision/adaptive tables are absent.
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
- Independent review: pending exact revision
  `79adac40ffb5650ed46fe78f73d091109b7602e4`; process success and focused green
  results are not acceptance.
- Retained open work: exact-revision independent review and any resulting
  P0–P2 correction only. Blocks 2–12 remain outside this candidate.
- Decision/continuation posture: hold Block 1 `in-progress` until the exact
  candidate is independently accepted; then record acceptance and continue
  automatically to Block 2 without narrowing the full bound range.

### Stop

Stop before exposing embedded or service hosts.

---

## Block 2 — Implement one embedded and standalone engine contract

Status: `not-started`

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

Pending.

### Stop

Stop before autonomous scheduling or provider effects.

---

## Block 3 — Implement work graph, scheduling, continuation, and concurrency

Status: `not-started`

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

Pending.

### Stop

Stop before live agent/provider lifecycle.

---

## Block 4 — Implement agents and replaceable providers

Status: `not-started`

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

Pending.

### Stop

Stop before target-profile authoritative effects.

---

## Block 5 — Implement target profiles, workspaces, and authoritative effects

Status: `not-started`

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

Pending.

### Stop

Stop before integrated QA/supervision acceptance.

---

## Block 6 — Integrate QA, supervision, acceptance, and outcome closure

Status: `not-started`

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

Pending.

### Stop

Stop before libRSI semantic cutover.

---

## Block 7 — Integrate libRSI and remove duplicate semantic owners

Status: `not-started`

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

Pending.

### Stop

Stop before delivery/release cutover.

---

## Block 8 — Complete delivery, release, recovery, and reconciliation

Status: `not-started`

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

Pending.

### Stop

Stop before service/operator qualification.

---

## Block 9 — Qualify service, API, operator, and deployment-ready boundaries

Status: `not-started`

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

Pending.

### Stop

Stop before cross-domain proof.

---

## Block 10 — Prove neutral content profile and external extension

Status: `not-started`

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

Pending.

### Stop

Stop before migration and legacy retirement.

---

## Block 11 — Migrate, cut over, and retire duplicate legacy paths

Status: `not-started`

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

Pending.

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
