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
table. At the accepted Block 1 checkpoint it covered all 89 tables written by
top-level runtime Python. Block 2 adds the single `engine_submissions_v2`
idempotency table under `FactoryEngine`, so the current registry covers 90
tables, including
the schema lineage, operational lifecycle, evidence, and semantic records. A
transaction participant is not a second authority: it may update an owner
table only as part of the named coupled transition and must use the same
database transaction.

| Concern | Primary owner | Authoritative state | Transaction participants |
|---|---|---|---|
| Schema lineage | `Database` | schema migrations and schema-version metadata | none |
| Event, command, and evidence ledgers | `AuditMixin` | events, commands, evidence records | doctor command repair; QA evidence disposition |
| Mission and authority | `MissionService` | projects, repositories, missions, authority records | continuation terminalization; audit use consumption |
| Capability and obligation | `CapabilityService` | capabilities, obligations, obligation dependencies | continuation, controller, QA |
| Program | `ProgramService` | programs and accepted revisions | none |
| Engine submission | `FactoryEngine` | durable idempotency key to mission binding | none |
| Work | `WorkItemService` | work items and work dependencies | controller, execution, QA |
| Agent sessions and assignments | `AgentService` | agent sessions and work assignments | controller and execution coordination |
| Workspaces | `WorkspaceService` | workspaces | agent, controller, and execution coordination |
| Execution | `ExecutionService` | executions, leases, provider callbacks | controller, QA evidence, reflection experiments, and supervision containment |
| QA | `QAService` | QA requirements and results | none |
| Artifacts | `ArtifactService` | artifact records | none |
| Acceptance evidence | `AcceptanceService` | exact-revision acceptance runs and case results | none |
| Acceptance governance | `GovernanceService` | acceptance contracts, probes, independent reviews, decisions, effect intents, report links, and role grants | none |
| Acceptance lifecycle and outcomes | `AcceptanceLifecycleService` | candidate/integrated/installed/terminal stage projections and actual-outcome reconciliations | work, capability, supervision, and continuation owners receive bounded routed transitions through their public services |
| Supervision | `SupervisionService` | assignments, checks, incidents | none |
| Delivery/operator effects | `ReportingService` | schedules, notifications, attempts, operator tokens and decisions | none |
| Reports | `ReportingService` | reports | governance delivery disposition |
| Adaptive and reflection semantics | `AdaptiveService`, `ReflectionService` | adaptive actions, strategy outcomes, legacy hypotheses | none |
| Learning semantics | `LearningService` | observations, signals, reflections, hypotheses, experiments, runs, and effectiveness records | migration observation import |
| Evolution semantics | `EvolutionService` | portfolios, checkpoints, candidates, policies, selections, reviews, and outcomes | none |
| Problem-solving semantics | `ProblemSolvingService` | cycles, candidates, next-action decisions, attempts, experiment designs, and verifications | none |
| Migration/cutover | `MigrationService` | migration runs/items, parity cases, path effects, and cutover effects | none |
| Release | `OperationsService` | immutable releases, reviews, and verifications | governed release facade |
| Recovery | `OperationsService` | recovery cases, resume tokens, and agent refreshes | recovery coordinator |
| Preservation and cleanup | `OperationsService` | inventories, preservation bundles, cleanup items, and effects | reconciliation cleanup |
| Reconciliation | `ReconciliationService` | integration candidates and restart workspaces | none |

The boundary test extracts `INSERT`, `INSERT OR ...`, `UPDATE`, and `DELETE`
targets from every top-level runtime module. The extracted set must equal the
registry exactly; an unregistered write or a declared table with no runtime
writer fails instead of being skipped. Every extracted writer must also be the
declared primary module or a named transaction participant. The registry uses
the actual `acceptance_probe_results_v2` table name; no nonexistent probe table
is admitted.

`CoreService` is the composition root. It builds one instance of each owner and
injects those same objects into coordinators and hosts. `AdvancedServices` may
also compose a standalone graph, but it has no schema and no alternate
lifecycle.

Operator decisions use that same transaction boundary. The decision is
re-read, the owning service applies its lifecycle change and audit event, and
the decision is marked applied inside one outer transaction. Nested owner calls
use savepoints on the current connection. An exception after the owned effect
rolls back the effect and event before the decision is separately marked
failed; a process interruption leaves the accepted decision restartable, and
an applied decision is idempotent.

## Migration lineage

The active lineage is exactly `0001_core.sql` through
`0022_acceptance_lifecycle.sql`, with one file per contiguous version. Every SQL
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
