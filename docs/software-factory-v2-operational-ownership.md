# Software Factory v2 operational ownership

This document fixes the Block 1 operational boundary. Software Factory v2 is
one modular monolith backed by one SQLite deployment. `Database` is the sole
persistence implementation; `DatabaseStore` and `Store` are compatibility
names for that same class, not alternate writers.

## Dependency direction

Dependencies flow in one direction:

1. `errors`, `util`, and `schema` define support and migration contracts.
2. `database` owns connections, transactions, migrations, and event/audit
   persistence; `store` only exports its compatibility alias.
3. Operational services own lifecycle transitions and accept the canonical
   store through explicit constructors.
4. Coordinators compose services and may join an owner's transaction only for
   a documented coupled invariant.
5. Hosts call the composed core. They do not write lifecycle tables directly.

Persistence modules must never import an operational service. Operational
services must never import a host. This is enforced by the focused Block 1
dependency test.

## Lifecycle owners

`software_factory.ownership.LIFECYCLE_OWNERS` is the executable form of this
table. A transaction participant is not a second authority: it may update an
owner table only as part of the named coupled transition and must use the same
database transaction.

| Concern | Primary owner | Authoritative state | Transaction participants |
|---|---|---|---|
| Mission and authority | `MissionService` | projects, repositories, missions, authority records | continuation terminalization; audit use consumption |
| Capability and obligation | `CapabilityService` | capabilities, obligations, obligation dependencies | continuation, controller, QA |
| Program | `ProgramService` | programs and accepted revisions | none |
| Work | `WorkItemService` | work items and work dependencies | controller, execution, QA |
| Execution | `ExecutionService` | executions, leases, provider callbacks | controller, QA evidence, reflection experiments, and supervision containment |
| QA | `QAService` | QA requirements and results | none |
| Acceptance evidence | `AcceptanceService` | exact-revision acceptance runs and case results | none |
| Acceptance decision | `GovernanceService` | acceptance contracts, probes, independent reviews, decisions | none |
| Supervision | `SupervisionService` | assignments, checks, incidents | none |
| Delivery/operator effects | `ReportingService` | schedules, reports, notifications, operator tokens and decisions | governance delivery disposition |
| Release and recovery | `OperationsService` | immutable releases and recovery cases | governed release facade |

`CoreService` is the composition root. It builds one instance of each owner and
injects those same objects into coordinators and hosts. `AdvancedServices` may
also compose a standalone graph, but it has no schema and no alternate
lifecycle.

## Migration lineage

The active lineage is exactly `0001_core.sql` through
`0020_acceptance_fencing.sql`, with one file per contiguous version. Every SQL
migration file must be present in `MIGRATIONS`, and every catalog entry must
have one matching file. Applied name or checksum drift, version gaps, unknown
applied versions, duplicate files, or inert SQL files fail initialization.

The retired `0008_supervision.sql` alternate schema is not part of this
lineage. Its monitor/incident/action tables and retained-adaptive-case table are
not created. The canonical owners are `supervision_assignments`,
`supervision_checks`, `incidents`, `strategy_outcomes`, and `adaptive_actions`.

## Semantic separation

Reflections, hypotheses, experiments, learned signals, evolution candidates,
and selections are evidence and reasoning records. They may cite operational
identifiers, but no operational lifecycle row may depend on a semantic row for
identity, current status, authority, fencing, acceptance, delivery, or release.
Semantic adoption must pass through the relevant operational owner's explicit
transition; inserting or updating a semantic row alone has no operational
effect.

There is deliberately no universal entity table. Domain-neutral behavior comes
from explicit service contracts and adapters, not by collapsing distinct
lifecycle, evidence, and semantic records into one model.

## Later cutovers

Block 1 establishes internal ownership only. Embedded/service host exposure is
Block 2. Target-profile authoritative effects are Block 5, libRSI semantic
cutover is Block 7, and legacy migration/retirement is Block 11. Compatibility
aliases remain non-authoritative until those later parity and cutover proofs.
