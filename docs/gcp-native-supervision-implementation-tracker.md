# GCP-native supervision implementation tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–3
- Repository: Software Factory, branch `codex/gcp-native-supervision`
- Governing objective: direct user request in task `01a06f3e-c732-74b2-bde9-3980430df4de`: “What's the fix? Did you do it? If not, do it.” Read with the preceding requirement that task coordination and supervision run on GCP without the desktop.

## Purpose and mission frame

Install and activate persistent supervision for the existing patent implementation task on GCP. Completion requires actual role tasks, durable schedules, direct target reads, verified delivery and scheduled execution, and recovery after the service restarts. The desktop must not participate in the service's transport or scheduling. This infrastructure repair does not complete or contract the patent implementation tracker.

Ordinary authorized effects are source changes, focused tests, isolated Git checkpoints, local installation and system service activation. Preserve existing tasks, Codex homes, credentials, patent files, unrelated work, and supervision history. No Gmail, public listener, patent edit, or replacement implementation task is part of this repair.

### Target-product capability frame

Consequential: this repairs the operating model. Source is the direct user request and the verified 0.153.4 native Unix-socket task interface. Reuse Codex task persistence and the existing supervision helper's mission, change, routing, incident and liveness gates. Add only local transport and durable scheduling/delivery ownership. Protected capabilities are exact-target routing, independent semantic review, quiet unchanged-state monitoring, authentic schedule IDs and no duplicate uncertain delivery. The shared 0.147.0 client does not support the current WebSocket-over-Unix protocol; do not silently upgrade its independent contract. The dashboard/runtime are reference implementations, not a reason to deploy their wider product stack.

## Execution and verification contract

Execute 0 → 1 → 2 → 3. Each Stop is an internal checkpoint. Preserve current evidence and run focused tests before integration. Independent review may use the native GCP reviewer once that interface is available; collaboration spawning was attempted and rejected by the environment's task limit. Use Python 3 standard-library unittest from this worktree for new runtime tests, with temporary state below `/srv/patent-studio/private/tmp`. Before writes, database operations or installation, use the host storage preflight. Runtime operational state belongs below `/srv/patent-studio/private`.

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---|---|
| 0 | Direct server transport | — | completed |
| 1 | Persistent scheduler and gated delivery | 0 | completed |
| 2 | Supervisor roles and GCP installation | 1 | in-progress |
| 3 | Live verification and operating handback | 2 | not-started |

## Block 0 — Direct server transport

Status: `completed`

### Objective
Read and coordinate existing Codex tasks using the running GCP daemon.
### Inputs and dependencies
Installed 0.153.4 protocol and previously verified local socket handshake/read.
### Target-product capability delta
Consequential: gain desktop-independent transport while preserving task identity. No daemon restart or public socket is required. Tradeoff: a bounded current-protocol adapter rather than widening the independent shared client's frozen contract.
### Required work
Implement bounded Unix WebSocket JSON-RPC transport, direct task reads with output omission, and native task/message operations. Preserve server errors and timeouts distinctly.
### Scope and non-goals
One local daemon; no remote authentication service or UI.
### Deliverables and recorded state
Runtime transport and meaningful protocol tests.
### Acceptance
Exact target status is read from the current daemon; frames, deadlines and errors are handled correctly.
### Negative tests
Reject failed upgrade, oversized message, closed connection and mismatched response handling.
### Completion evidence
Eight focused transport tests pass, including upgrade verification, fragmentation/ping, bounds, deadline/reset, server errors and response identity. Direct current-daemon compact and latest-turn reads succeeded for the exact target. Initial reset failure corrected and rerun. Independent integration review remains owned by Block 3.
### Stop
Stop before creating production schedules.

## Block 1 — Persistent scheduler and gated delivery

Status: `completed`

### Objective
Own recurring role wakes and exact message delivery on GCP across restarts.
### Inputs and dependencies
Block 0; existing supervision helper and role policy.
### Target-product capability delta
Consequential: gain durable scheduling; preserve helper gates and independent roles. Keep operational schedule/delivery metadata separate from the canonical supervision ledger.
### Required work
Persist schedules and delivery attempts; prevent overlapping role turns and retry only safely reconciled deliveries. Provide view, pause/resume and health controls. Keep failed and uncertain attempts visible. Expose bounded native read and helper-gated message operations to role tasks.
### Scope and non-goals
Only the requested supervision group's fixed role cadences and action messages. No generic workflow engine or desktop automation-file impersonation.
### Deliverables and recorded state
Scheduler owner, service loop, CLI, persisted schedule IDs and receipts.
### Acceptance
Schedules survive restart, due work executes once, role context is reused, and route rejection prevents delivery.
### Negative tests
Reject wrong target/recipient, suppress duplicate delivery, retain uncertain writes, and skip already-active roles.
### Completion evidence
Ten focused runtime tests pass: persistent schedule/receipt restart, lost add/start responses, uncertainty withholding, active-role behavior, pause, wrong-target/content rejection and gated send denial. Semantic gates remain in the existing helper; operational schedule/receipt state has a distinct SQLite owner. Live native dispatch and independent integration checks are Block 3 acceptance.
### Stop
Stop before activating the service.

## Block 2 — Supervisor roles and GCP installation

Status: `in-progress`

### Objective
Run the requested five-role supervision group under a persistent GCP system service.
### Inputs and dependencies
Block 1 accepted and native task creation available.
### Target-product capability delta
Consequential: replace unavailable desktop scheduling with GCP-owned schedules. Preserve model/reasoning roles, direct target evidence, existing helper and quiet notifications.
### Required work
Create real role tasks using the skill prompts and explicit native transport instructions. Initialize one canonical group, bind real role and schedule IDs, install the reviewed runtime, and enable a system service under the existing operating-system account. Reuse the current daemon; keep source and state on the data disk.
### Scope and non-goals
One target. No patent implementation effects or Gmail.
### Deliverables and recorded state
Service unit, installed source identity, role IDs, schedule bindings, operating instructions.
### Acceptance
The service is active without a desktop connection; all bindings resolve to real owner state.
### Negative tests
Installation or binding mismatch fails before activation; unavailable daemon remains a visible retryable failure.
### Completion evidence
Pending.
### Stop
Stop before claiming live acceptance.

## Block 3 — Live verification and operating handback

Status: `not-started`

### Objective
Demonstrate that the installed monitor performs its intended work.
### Inputs and dependencies
Block 2.
### Target-product capability delta
Routine: verify the installed operating result without widening target work.
### Required work
Observe scheduled liveness and watcher turns, a direct target read, a gated role delivery and independent review. Restart only the new service and verify retained schedules/receipts. Validate a service-launched isolated check with no desktop transport/environment. Record precise limits: do not claim a physically disconnected desktop test unless performed.
### Scope and non-goals
Bounded installed-service verification, not a broad product regression.
### Deliverables and recorded state
Current acceptance evidence, tracker statuses and concise operational handback.
### Acceptance
Real wake, read, delivery and restart evidence agree with the configured owner. Supervision is reported active only after these pass.
### Negative tests
Missing/failed/uncertain evidence cannot be labeled successful; an idle task alone cannot prove semantic completion.
### Completion evidence
Pending.
### Stop
Stop infrastructure expansion once the requested GCP monitor is operational; preserve the patent implementation scope and its separate continuation state.
