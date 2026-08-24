# Software Factory v2 engine and host contract

Block 2 exposes one `FactoryEngine` through two thin facades. The engine owns
no provider or target-profile behavior; it delegates mission lifecycle state to
the Block 1 owners and persists only the idempotency-key-to-mission binding
needed for safe submission and restart.

## Typed operations

The contract version is `software-factory-engine/1`.

| Operation | Input | Result | Authoritative effect |
|---|---|---|---|
| `start` | `MissionSubmission` | `MissionRef` | atomically creates one mission and one durable submission binding |
| `status` | mission ID | `MissionSnapshot` | none |
| `continue_mission` | mission ID | `MissionSnapshot` | reattaches and exposes the current safe frontier; Block 3 owns scheduling |
| `cancel` | mission ID and reason | `CancelResult` | uses `MissionService` to cancel only when no provider execution is active |
| `outcome` | mission ID | `MissionOutcome` | none; reports only canonical completed or authority-cancelled state |
| `events` | mission ID, cursor, limit | tuple of `EventRecord` | none; limit is required to remain between 1 and 1,000 |

`runtime/src/software_factory/engine.py` is the typed schema. The service wire
facade returns those exact fields plus `contract_version`. Submission request
roots are canonical and a reused idempotency key with different bytes fails
closed. Mission creation, submission binding, and the submission audit event
commit in one transaction.

## Host ownership

`EmbeddedFactoryHost` has no provider-process ownership. The embedding product
is the outer host and calls the typed engine directly. `StandaloneFactoryService`
is the outer local service host and is the only shape permitted to own provider
processes when later provider Blocks enable them. Block 2 launches no provider.

Neither facade stores mission state. A mission started through either facade
can be reopened through the other against the same database without a new ID,
host-specific acceptance state, cursor, or outcome. The loopback-only
`software-factory-api` entrypoint exposes the service operations at
`POST /api/engine/{start,status,continue,cancel,outcome,events}`.

## Boundaries

Block 2 adds the bounded `software-factory-api` service entrypoint but preserves
the existing `software-factory`, `software-factoryd`, and `sf-skill` targets.
Cutting those targets over to adaptive tick/dispatch owners would activate
scheduling and provider effects and therefore belongs to later Blocks. This
Block does not consume `embedded-service-contract`, `runtime-manifest`, or any
utils package. It does not implement autonomous scheduling, provider effects,
public multi-tenancy, billing, hosted deployment, or public authentication.
