# Software Factory v2 — Autonomous Work, QA, and Delivery Runtime Implementation Plan

**Status:** Active implementation authority for the v2 refactor  
**Repository:** `https://github.com/estill01/software-factory`  
**Implementation branch:** `agent/software-factory-v2-native-refactor`  
**Primary implementation PR:** `#4`  
**Planning revision date:** 2026-08-22

## 1. Purpose and relationship to prior plans

This document is the maintained implementation plan for the v2 program. It preserves the complete functional goals established by the existing repository, completed and incomplete implementation trackers, the v2 architecture specification, and the implementation execution directive while revising two architectural assumptions:

1. the product core is broader than software engineering; and
2. reusable epistemic, experimental, improvement, selection, and recursive-self-improvement semantics belong in `libRSI`, which this repository consumes.

The repository and current product name may remain `software-factory` during implementation. The architectural core is an **autonomous work, QA, supervision, acceptance, and delivery runtime**. Software engineering is the first and most demanding target profile, not the ontology of the core.

One engine must support two first-class hosting modes:

- **embedded mode**, where a product calls the mission runtime through a typed in-process API and retains its domain authority; and
- **standalone service mode**, where an operator or product submits a bounded mission and target/profile binding through maintained service APIs.

The two modes share mission, work, QA, supervision, acceptance, delivery, and recovery semantics. Neither hosting mode is a second controller. A future hosted multi-tenant product may wrap the standalone service, but tenant billing, fleet deployment, public authentication, and commercial control-plane work are a separately activated successor rather than implicit v2 scope.

This plan does not reduce scope. It changes ownership so the same required behaviors are implemented once, in the correct system.

## 2. Governing product objective

Build a production-grade system that can:

```text
authorized mission / goal / requested outcome
    → determine what must become true
    → construct and revise an executable program
    → select the maximal safe set of useful work
    → assign agents and tools with bounded authority
    → execute real effects
    → supervise execution continuously
    → detect failures, successes, drift, and uncertainty
    → adapt plans and approaches
    → independently verify actual outcomes
    → deliver, release, or roll back
    → preserve unresolved obligations and continue
    → improve future planning, execution, and selection through libRSI
```

The runtime must support work whose outputs are source code, documents, analyses, decisions, reports, data products, experiments, operational changes, or other verifiable target-state changes. A target profile supplies the domain-specific capabilities required to inspect, change, validate, apply, and verify a target.

The same mission must be resumable through either the embedded or standalone host without changing its semantic or operational identity. Hosting success, provider completion, and target-profile build success do not establish QA, acceptance, delivery, or mission completion.

## 3. Non-negotiable functional goals

The following goals remain required regardless of module or repository ownership:

- stable missions and protected outcomes;
- durable obligations that remain open when attempts fail;
- implementation-program authoring, dependency ordering, live revision, and range continuity;
- autonomous determination of the next useful action;
- no unsupported early stopping while safe useful work remains;
- multiple concurrent agents with explicit assignments and attribution;
- isolated candidate and cooperative workspaces;
- locks, leases, fencing, heartbeats, stale-result rejection, and reassignment;
- actual command, provider, filesystem, repository, release, and notification effects;
- live independent supervision, incident handling, containment, and later effectiveness review;
- revision-bound QA and distinct candidate, integrated, installed, and terminal acceptance;
- known-signal detection and discovery of previously unknown success, failure, mixed, and opportunity signals;
- adaptation after setbacks and bounded exploitation of unexpected successes;
- evidence-driven hypotheses, experiments, comparison, selection, and learning;
- recursive improvement of planning, routing, supervision, evaluation, and selection policies;
- immutable releases, safe refresh, rollback, systemic self-repair, and exact target resumption;
- no-loss cleanup, repository reconciliation, and unfinished-work restart;
- durable reporting, notifications, API, operator controls, and historical inspection;
- one embedded engine API and one service facade over the same authoritative runtime;
- replaceable Codex app-server, local-process, and external-agent providers whose completion never implies acceptance;
- truthful distinction among designed, implemented, tested, provider-integrated, behaviorally accepted, and production-ready states.

No capability is removed merely because its reusable semantic portion moves to `libRSI` or its domain-specific portion moves to a target profile.

## 4. Product decomposition and ownership

### 4.1 Autonomous mission runtime — this repository's product core

The mission runtime owns operational authority and real execution:

- projects, missions, requested ranges, capabilities, and obligations;
- programs, program revisions, work graphs, dependencies, and safe-frontier continuation;
- work selection, scheduling, concurrency, budgets, and resource policy;
- agent sessions, provider tasks, assignments, roles, and attribution;
- workspaces, branches, leases, fencing, callbacks, and execution telemetry;
- operational supervision, incidents, containment, cancellation, and recovery;
- QA obligations, independent review execution, acceptance, and terminal verification;
- live event ingestion, active classifiers, deployed detector execution, and response routing;
- authority, credentials, effect classes, reserved boundaries, and release authority;
- immutable releases, installed verification, live refresh, rollback, and Factory repair;
- cleanup, reconciliation, reports, notifications, API, UI, and operator commands;
- the outer controller that decides which mission work may run and applies all authoritative effects.
- the embedded and standalone host facades that expose this one controller without duplicating it.

These concerns remain in one modular monolith and one authoritative SQL deployment because their invariants must be transactionally coordinated.

### 4.2 `libRSI` — reusable semantic improvement engine

`libRSI` owns domain-neutral semantics that should not be duplicated here:

- canonical target, target-snapshot, intent, evidence, experiment, intervention, candidate, evaluation, and outcome records;
- claims, questions, goals, constraints, hypotheses, provenance, and epistemic aggregation;
- experiment identity, validity, measurement, metrics, and result interpretation;
- validation and investigation workflows;
- intervention and candidate lifecycle semantics;
- baseline/candidate comparison and evidence-backed selection;
- improvement workflow semantics;
- application, verification, and rollback lifecycle semantics independent of any concrete effect mechanism;
- meta-targeting and stronger governance for changes to improvement machinery;
- reusable outcome and action/result schemas;
- historical, shadow, canary, counterexample, and independent-evaluation policy for self-change.

The dependency direction is always:

```text
software-factory / mission runtime  →  libRSI
```

Never:

```text
libRSI  →  software-factory
```

### 4.3 Target profiles

Domain-specific behavior is implemented behind profiles. The first profile is software:

```text
profiles/software/
    target and multi-repository snapshots
    repository inspection
    Git workspaces and candidate revisions
    command/test/build execution
    integration and merge behavior
    software release/deployment adapters
    repository cleanup and rollback
```

A small invention-neutral content-production profile should be added as the first non-software proof:

```text
profiles/content/
    source collection
    document planning and revision
    rendering and artifact generation
    factual/structural/style review
    publication handoff and verification
```

The content profile is a generic fixture and extension proof. It must not contain Patent Studio, OMNI, Celltonomy, patent-domain schemas, workflow IDs, or product-specific gateway behavior. Patent Studio remains an external consumer that implements its own domain profile/effect adapter against the generic Factory contracts.

Additional research, data, operations, simulation, robotics, or laboratory profiles are later capability packs, not reasons to generalize the core prematurely.

### 4.4 Providers and effect adapters

Provider implementations remain replaceable:

```text
providers/codex_app_server
providers/local_process
providers/external_agent
integrations/notifications
integrations/artifacts
integrations/librsi
```

The mission runtime owns provider lifecycle and authority. A provider never becomes the source of mission truth, QA, acceptance, delivery, or epistemic truth merely by returning a successful response. The Codex app-server provider uses the maintained typed client from `estill01/utils` and owns process/thread/turn/approval/event lifecycle only when Software Factory is the active host. It does not expose app-server as the public Factory API.

## 5. One control plane and one active owner

The final system has:

- one outer mission controller;
- one authoritative operational SQL state plane;
- one active writer for each lifecycle concern;
- Git as source and candidate-history truth;
- content-addressed artifacts for large evidence;
- `libRSI` as a semantic dependency, not a competing scheduler or second autonomous control plane.

When `libRSI` emits or persists a run/action/result workflow, Software Factory hosts it as a bounded nested workflow:

```text
Software Factory obligation
    → libRSI run or semantic decision
    → libRSI action
    → Software Factory work item / assignment / execution
    → observed result and host QA
    → libRSI action result / evidence evaluation
    → libRSI outcome or next action
    → Software Factory authoritative routing or effect
```

`libRSI` does not directly launch Codex tasks, mutate repositories, accept candidates, activate releases, or complete missions. Software Factory does not independently reimplement the generic semantic decision that `libRSI` owns.

## 6. Extraction policy

`libRSI` remains the only major semantic product extraction planned now.

Narrow domain-neutral enabling packages may be consumed from `estill01/utils` when they satisfy that repository's admission rule: at least two concrete consumers or an existing consumer plus an imminent active second implementation, one-way dependencies, independent tests/versioning, and no product authority or policy. The initial justified package is the typed Codex app-server client already implemented inside the dashboard and needed by libRSI and Patent Studio. Shared utilities may never own missions, QA, supervision, acceptance, delivery, libRSI semantics, target profiles, or product persistence.

Do not create additional repositories for the scheduler, QA system, authority model, supervision, release, recovery, or target profiles. First create strong internal module boundaries and prove them with at least two profiles.

A future protocol/SDK package may be extracted only when all of the following are true:

1. at least two independently deployed consumers exist;
2. the wire or capability contract is stable;
3. the package does not require atomic transactions with the runtime;
4. the dependency direction is one-way;
5. independent versioning removes more coupling than it creates;
6. conformance tests prove interchangeability.

Do not create a shared `common-models` package. `libRSI` owns semantic records; the mission runtime owns operational records; adapters explicitly map between them. Utilities may carry transport/version/runtime metadata only when those records are non-authoritative and independently useful to multiple consumers.

### 6.1 Codex app-server provider boundary

Codex app-server is the preferred maintained Codex execution substrate, not a replacement for Software Factory:

- `estill01/utils` owns the domain-neutral typed client, process/transport primitives, schema compatibility, event stream, cancellation, and approval callback contracts;
- Software Factory owns provider reservations, agent assignments, bounded prompts/context, retries, restart/reattachment, QA obligations, supervision, acceptance, and delivery;
- an embedded consumer may let Software Factory own app-server or may supply an already managed provider through the same interface, but exactly one composition owner starts each app-server process;
- app-server thread/turn completion is operational evidence only and cannot accept work or close a mission; and
- WebSocket or other experimental transports do not become required merely because app-server exposes them.

## 7. Target internal architecture

The repository should converge toward this shape without requiring an immediate repository or Python-package rename:

```text
runtime/src/software_factory/
    hosts/
        embedded.py
        service.py

    core/
        missions/
        programs/
        obligations/
        work/
        scheduling/
        agents/
        authority/
        qa/
        supervision/
        continuation/
        release/
        recovery/
        reporting/
        api/

    integrations/
        librsi/
            version.py
            mappings.py
            persistence.py
            actions.py
            capabilities.py
            conformance.py
        notifications/
        artifacts/

    profiles/
        software/
            targets.py
            repositories.py
            workspaces.py
            commands.py
            validation.py
            integration.py
            release.py
            cleanup.py
        content/
            targets.py
            sources.py
            drafting.py
            rendering.py
            validation.py

    providers/
        codex_app_server.py
        local_process.py
        external_agent.py
```

The physical move should be incremental. Behavior and tests move with their owning module; no large mechanical rename is required before a boundary is proven.

## 8. Treatment of current overlapping functionality

| Current area | Permanent Software Factory owner | Future `libRSI` owner | Migration treatment |
|---|---|---|---|
| `reflection.py` | trigger, bounded context, reasoner assignment, operational attribution, work creation | reflection records, hypotheses, evidence relationships, epistemic updates | shadow libRSI results, prove conformance, cut over semantic output, remove local semantic owner |
| `learning.py` | event ingestion, live windows, active detector execution, incidents, operational routes, effect observation | causal/predictive analysis, counterexamples, experiment design/evaluation, promotion/narrow/revise recommendation | split execution from interpretation; retain deployed classifier runtime locally |
| `evolution.py` | apply program revisions, work graph changes, tracker projection, Git effects, validation, commits | materiality, intervention identity, portfolios, comparison, selection, outcomes, meta-policy | make service a host adapter; remove duplicate generic evolution policy after parity |
| `problem_solving.py` | convert semantic actions to obligations/work/executions and preserve mission continuation | validation, investigation, improvement, next epistemic action | stop adding generic semantics locally; retain compatibility path until libRSI workflows stabilize |
| `governance.py` | authenticated identities, role grants, authority scopes, release/effect authorization, acceptance mutation | generic review requirements and self-change evaluation policy | keep host governance authoritative; consume libRSI policy requirements |
| signal classifiers/routes | event execution and governed operational effects | evidence and policy for whether a detector/route should be promoted or changed | no separate signal library; retain one operational runtime |
| Git/workspaces/tests/builds | software profile | none; libRSI sees target/candidate/evidence abstractions | move behind software-profile capabilities |

For each migration, retain old behavior only as a read-only comparator or isolated shadow path with an explicit removal condition.

## 9. `libRSI` integration baseline

At the time of this plan revision, `libRSI` `main` is at `ecef9b671463ab9f70c91e82b7c39acfe8b5661a`. Its canonical tracker records:

- Blocks 0–12 accepted;
- Blocks 13–14 completed;
- Block 15, the complete improvement workflow, as the next unstarted convergence milestone;
- later application, RSI, facade, outcome, protocol, Software Factory integration, dogfood, and release Blocks as remaining.

Software Factory must pin an immutable `libRSI` version or exact commit and record:

```text
package version
source commit
package/content root
supported semantic schema versions
adapter contract version
```

Do not depend on mutable `main` in a release.

## 10. Persistence boundary for libRSI records

Software Factory remains the deployment owner for operational persistence.

The integration may use a small content-addressed record store such as:

```text
librsi_records
    root
    record_type
    schema_version
    canonical_json
    created_at

librsi_record_bindings
    mission_id
    operational_subject_type
    operational_subject_id
    semantic_role
    librsi_root
    currentness_root
```

This is an immutable canonical-record cache and explicit binding layer, not a generic entity/EAV operational model. Mission, work, agent, QA, release, and other operational state remain in their explicit tables.

Operational IDs and semantic roots are linked, never conflated:

```text
Software Factory execution ID != libRSI Observation root
Software Factory work item     != libRSI Intervention root
Software Factory candidate SHA != libRSI Candidate root
```

## 11. Implementation phases

### Phase 0 — Stabilize the exact implementation branch

Before further broad expansion:

- remove stale transport, pending-marker, repair-workflow, and generated-code residue;
- restore green Ruff, formatting, mypy, compilation, complete tests, coverage, wheel, and installed-entrypoint gates at the exact remote head;
- make ordinary CI read-only;
- update the PR body to the exact head and current limitations;
- generate an exact-source artifact from that head.

This phase is required even when a failure is mechanically simple. No later integration should be built on a red or ambiguous branch.

### Phase 1 — Establish the mission-runtime/profile/libRSI boundary

- adopt this implementation plan as the maintained architecture route;
- add `integrations/librsi/` and `profiles/software/` package boundaries;
- document ownership of every current module and table;
- add dependency rules preventing `libRSI` reverse imports and preventing generic core imports of software-profile internals;
- add a treatment matrix with cutover and deletion conditions;
- preserve all existing runtime behavior while creating the boundary.
- define one typed engine contract used unchanged by the embedded and standalone service hosts;
- define host/process ownership so only the outer active host launches provider processes.

### Phase 2 — Integrate verified libRSI semantic foundations

- pin an immutable libRSI revision;
- add canonical-record serialization and binding persistence;
- map Software Factory missions/repositories/executions/candidates into libRSI records;
- map libRSI evidence and outcomes back to operational work and decision records;
- add cross-repository contract tests;
- run the new path in shadow mode without authoritative behavioral change.

### Phase 3 — First authoritative semantic cutovers

Implement two complete vertical slices:

#### A. Failed-execution investigation

```text
failed observed execution
→ exact target snapshot and failure evidence
→ competing libRSI hypotheses
→ immutable discriminating experiment specification
→ Software Factory experiment obligation and real execution
→ exact observation submitted to libRSI
→ supported/refuted/inconclusive evidence
→ alternate strategy, experiment, reframe, or replan work
→ mission continues
```

#### B. Unexpected-success investigation

```text
unexpected capability/resource improvement
→ explanatory and alternative hypotheses
→ bounded replay/counterexample experiment
→ applicability evidence
→ reuse/generalization or rejection
→ later effectiveness observation
```

After conformance proof, make libRSI authoritative for the migrated semantics and remove the corresponding local semantic implementation.

### Phase 4 — Complete and harden the mission host

Continue independently of later libRSI workflow milestones:

- real Codex multi-agent lifecycle and restart/reattachment proof;
- replace dashboard-local app-server process/RPC code with the shared typed utility package and a Factory-owned provider adapter;
- embedded/service equivalence, idempotent mission submission, cancellation, bounded event streaming, and restart proof;
- atomic scheduling, assignment, lease, workspace, execution, and provider reservation;
- authenticated callbacks and exact provider-task correlation;
- crash injection at every SQL/Git/provider boundary;
- stronger acceptance contracts and independent review identity;
- terminal mission verification and false-completion rejection;
- operational supervision, containment, cancellation, replacement, and safe-frontier continuation;
- immutable release, live refresh, rollback, Factory self-repair, and exact-once target resumption;
- no-loss cleanup and repository reconciliation;
- real-state migration, operator UI, reports, and notifications.

These are host responsibilities and must not wait for libRSI.

### Phase 5 — Progressive libRSI semantic cutover

Cut over only after the relevant libRSI capability is accepted and the Software Factory adapter passes host/integration proof:

| libRSI capability maturity | Software Factory migration |
|---|---|
| Current Blocks 0–14 | canonical records, epistemics, experiments, targets, knowledge, run/action foundations, validation, investigation, interventions, goals, comparison/selection |
| Block 15 | replace generic local improvement/problem-solving sequencing |
| Block 16 | adopt generic application/verification/rollback lifecycle while retaining real host effects |
| Block 17 | replace local generic RSI/meta-policy evaluation |
| Blocks 18–20 | adopt stable facade, outcomes, and external-agent protocol where they simplify the host boundary |
| Block 23 | complete the formal Software Factory consumer integration and remove remaining duplicate semantic owners |
| Block 24+ | use maintained dogfood and cross-domain evidence as final integration proof |

Software Factory may integrate accepted lower-level contracts before the complete libRSI product is finished, but it must not depend on planned APIs as though they already exist.

### Phase 6 — Prove the core is broader than software

Add a maintained invention-neutral content-production dogfood using the same mission runtime:

```text
mission
→ program authoring
→ research/source work
→ drafting/revision work
→ independent review
→ rendering
→ artifact verification
→ terminal outcome
```

The content profile must not use Git-specific domain types in generic workflow code. It should reuse mission, obligation, work, scheduling, agent, QA, supervision, release/delivery, and libRSI integration semantics. A second proof must demonstrate that an external domain extension can be registered without importing that domain's code into the Software Factory OSS core; Patent Studio may later supply such a consumer proof, but its code and workflow identities remain outside this repository.

### Phase 7 — Migration, cutover, and duplicate removal

For every replaced owner:

1. freeze characterization and historical regression cases;
2. implement the new owner and adapter;
3. run read-only shadow/conformance evaluation;
4. migrate exact records and lineage;
5. switch the authoritative path once;
6. stop the old writer;
7. delete or make the old owner non-executable;
8. retain only bounded migration readers with explicit removal conditions;
9. prove that removal did not remove required behavior.

The final system must not ship with two active mission, work, acceptance, supervision, signal, improvement, release, or lifecycle authorities.

### Phase 8 — Frozen-revision acceptance and merge preparation

At one exact pushed commit:

- execute the complete behavioral acceptance matrix;
- execute semantic, host, and integration acceptance for every libRSI-backed path;
- execute retained historical regressions;
- inject crashes, stale results, role conflicts, invalid evidence, failed releases, failed cleanup, and rollback;
- run a real software mission end to end;
- run the content-profile mission end to end;
- run real-provider checks where authorized and truthfully label all adapter-only boundaries;
- verify migration, one-writer cutover, rollback, and active-work resumption;
- remove superseded active code;
- build reproducible source, wheel, checksums, migration guide, runbook, and acceptance report;
- update the README and PR from the exact accepted revision.

## 12. Acceptance architecture

Every relevant capability must be proven at three distinct layers.

### Semantic acceptance

Proves the libRSI path correctly handles:

- exact target/currentness;
- intent, claims, hypotheses, and evidence;
- experiment validity versus outcome;
- intervention/candidate/evaluation identity;
- comparison, selection, uncertainty, and outcome;
- next semantic action or terminal semantic result.

### Host acceptance

Proves Software Factory actually:

- selected and scheduled the work;
- acquired authority and leases;
- created the workspace or target context;
- ran the real agent, command, test, or adapter effect;
- observed telemetry and artifacts;
- ran independent QA;
- applied, delivered, or rolled back the effect;
- maintained obligations and continuation correctly.

### Integration acceptance

Proves:

- operational IDs and semantic roots map exactly;
- stale semantic or provider results fail closed;
- interruption and resume preserve both states;
- no action is applied twice;
- neither system becomes a hidden second authority;
- removing the duplicate local semantic owner preserves or strengthens behavior.

The existing minimum 70-case matrix remains required. It must be extended—not reduced—to include libRSI-backed semantic/host/integration cases and at least one non-software mission.

## 13. Immediate dependency-safe milestones

### Milestone 1 — Green exact head

**Outcome:** one ordinary-source branch head with all configured quality gates green and no temporary transport machinery.

### Milestone 2 — Ownership and adapter foundation

**Outcome:** this plan, package boundaries, dependency enforcement, exact libRSI pin, canonical mapping/persistence, and conformance test harness.

### Milestone 3 — Failed-execution semantic cutover

**Outcome:** a failed implementation attempt produces libRSI-bound hypotheses and a real discriminating experiment, and the result changes the operational plan without closing the obligation prematurely.

### Milestone 4 — Unexpected-success semantic cutover

**Outcome:** a surprising success is tested for applicability and changes later routing only after bounded evidence.

### Milestone 5 — Host reliability closure

**Outcome:** real Codex lifecycle, crash reconciliation, acceptance, release, recovery, cleanup, and terminal verification are accepted at one exact revision.

### Milestone 6 — General mission-runtime proof

**Outcome:** software and content missions execute through the same core with profile-specific capabilities and no software ontology in the generic runtime.

### Milestone 7 — Final libRSI and legacy cutover

**Outcome:** all generic semantic overlap is removed, retained state is migrated, one writer remains per concern, and full acceptance is green.

## 14. Status and evidence accounting

Every implementation-plan capability or milestone must record:

```text
status
owner
source requirement
current implementation owner
future owner
exact implementation commit
focused tests
mapped/historical tests
end-to-end scenario
observed postconditions
provider-tested versus adapter-tested boundary
known limitations
cutover state
old-owner removal state
```

Use these terms precisely:

```text
designed
implemented
mechanically tested
integration tested
provider integrated
behaviorally accepted
production ready
```

A module, table, schema, prompt, fixture, or passing agent narrative is not evidence of behavioral completion.

## 15. Commit and PR discipline

- Work only from a real Git branch and reviewable PR.
- Commit and push each coherent vertical slice or small coherent group before beginning the next large slice.
- Do not use encoded source transports or self-modifying ordinary CI.
- Do not leave the only copy of work in a chat sandbox or transient worktree.
- Ordinary CI validates the source visible at the exact branch head.
- Every checkpoint updates the PR with commit, capability effect, tests, limitations, and next dependency.
- A failing but coherent diagnostic checkpoint may be pushed; it must not be described as accepted.
- Use focused proof first, then mapped regressions, then end-to-end acceptance.
- Never weaken tests or intended behavior to obtain a green check.

## 16. Definition of done

The v2 program is complete only when all of the following are true at one exact pushed revision:

1. A mission can be accepted in domain-neutral terms and converted into a durable executable program.
2. The runtime autonomously determines and performs useful next actions until a legitimate terminal boundary.
3. Multiple agents and tools execute concurrently with correct authority, leases, fencing, and recovery.
4. Real effects are observed and revision-bound QA gates candidate, integrated, installed, and terminal acceptance.
5. Failures and successes alter execution based on evidence rather than process completion.
6. `libRSI` is the sole reusable semantic owner for migrated epistemic, experimental, improvement, selection, and RSI behavior.
7. Software Factory remains the sole operational owner for mission state, agents, effects, authority, QA, release, recovery, and operator control.
8. The software profile completes a real software mission end to end.
9. A non-software profile completes a real mission through the same core.
10. All retained historical capabilities and failure/success cases pass directly or map to reviewed stronger behavior.
11. Old file-ledger and duplicate semantic writers are removed from active execution.
12. Migration and rollback are idempotent, verified, and reversible.
13. CI, coverage, build, installation, security, crash, concurrency, and acceptance gates are green.
14. Real-provider and adapter-only validation boundaries are explicitly recorded.
15. The same mission engine is usable through embedded and standalone service hosts with equivalent lifecycle, QA, supervision, acceptance, and delivery outcomes.
16. Codex app-server is a replaceable provider substrate through the shared typed utility client, with one process owner per composition and no provider-completion shortcut to acceptance.
17. The OSS core contains no Patent Studio, OMNI, Celltonomy, or other consumer-specific workflow/schema authority.
18. Hosted/multi-tenant deployment remains an explicit successor unless separately activated; v2 nevertheless exposes a service-ready, restartable, bounded standalone host.
19. The PR, source archive, wheel, checksums, docs, runbook, and acceptance evidence reproduce the same revision.

Until then, the PR remains draft and status reporting must identify the exact partial state.
