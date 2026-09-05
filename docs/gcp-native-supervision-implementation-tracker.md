# GCP-native supervision implementation tracker

- Tracker status: `completed`
- Tracker sequence: Blocks 0–3
- Repository: Software Factory, branch `codex/gcp-native-supervision`
- Governing objective: direct user request in task `01a06f3e-c732-74b2-bde9-3980430df4de`: “What's the fix? Did you do it? If not, do it.” Read with the preceding requirement that task coordination and supervision run on GCP without the desktop.

## Purpose and mission frame

Install and activate persistent supervision for the existing patent implementation task on GCP. Completion requires actual role tasks, durable schedules, direct target reads, verified delivery and scheduled execution, and recovery after the service restarts. The desktop must not participate in the service's transport or scheduling. This infrastructure repair does not complete or contract the patent implementation tracker.

Ordinary authorized effects are source changes, focused tests, isolated Git checkpoints, local installation and system service activation. Preserve existing tasks, Codex homes, credentials, patent files, unrelated work, and supervision history. No Gmail, public listener, patent edit, or replacement implementation task is part of this repair.

### Target-product capability frame

- Applicability: consequential
- Applicability rationale: Task supervision must operate without a desktop control plane.
- Direct product sources: Direct user request and verified native Codex 0.153.4 protocol.
- Product thesis and intended effect: Keep the existing patent task supervised by persistent GCP roles.
- Protected capabilities: Exact-target routing, independent direct-evidence review, quiet unchanged monitoring and durable delivery identity.
- Architecture strategy: Reuse native task persistence and the maintained semantic helper; add a local transport and schedule owner.
- Requested capability: Real GCP role creation, recurring wakes, direct reads and gated messages that recover across controller restart.
- Proportionality: One group, standard-library runtime, fixed existing cadences, focused tests and live evidence.
- Tradeoffs: Separate bounded adapter preserves the shared client's independent 0.147.0 JSONL contract; no dashboard deployment.
- Uncertainty: Native queue auto-start and first-turn durability were tested during bootstrap. Physical desktop disconnection was not tested; local-only service transport was verified.

## Execution and verification contract

Execute 0 → 1 → 2 → 3. Each Stop is an internal checkpoint. Preserve current evidence and run focused tests before integration. Independent review may use the native GCP reviewer once that interface is available; collaboration spawning was attempted and rejected by the environment's task limit. Use Python 3 standard-library unittest from this worktree for new runtime tests, with temporary state below `/srv/patent-studio/private/tmp`. Before writes, database operations or installation, use the host storage preflight. Runtime operational state belongs below `/srv/patent-studio/private`.

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---|---|
| 0 | Direct server transport | — | completed |
| 1 | Persistent scheduler and gated delivery | 0 | completed |
| 2 | Supervisor roles and GCP installation | 1 | completed |
| 3 | Live verification and operating handback | 2 | completed |

## Block 0 — Direct server transport

Status: `completed`

### Objective
Read and coordinate existing Codex tasks using the running GCP daemon.
### Inputs and dependencies
Installed 0.153.4 protocol and previously verified local socket handshake/read.
### Target-product capability delta
- Posture: consequential
- Intended capability gain: Native direct task reads and messages over the running local Unix socket.
- Potential capability loss or regression: Protocol drift could break framing or response matching.
- Protected-capability effect: Exact task identity is required and tool outputs are omitted.
- Architecture and operating-model effect: The current daemon remains the owner; no listener or daemon restart.
- Tradeoff and source evidence: Current 0.153.4 schema and eight transport tests support a bounded adapter.
### Required work
Implement bounded Unix WebSocket JSON-RPC transport, direct task reads with output omission, and native task/message operations. Preserve server errors and timeouts distinctly.
### Scope and non-goals
One local daemon; no remote authentication service or UI.
### Deliverables and recorded state
Runtime transport and meaningful protocol tests.
### Resource and economy contract
One group and the changed runtime only; preserve the data-disk preflight, fixed role cadences and bounded native reads. Do not broaden into unrelated builds or task histories.
### QA and independent review
Focused automated checks validate this Block; Block 3 adds native independent Sol review of direct target deltas and owner-backed live integration evidence. A passing route gate alone is not delivery.
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
- Posture: consequential
- Intended capability gain: Persistent recurring wakes and reconciled delivery receipts.
- Potential capability loss or regression: Ambiguous responses could otherwise duplicate delivery or advance a schedule prematurely.
- Protected-capability effect: Routing stays in the maintained helper; unresolved delivery is withheld.
- Architecture and operating-model effect: SQLite owns operational schedules and receipts, separate from semantic records.
- Tradeoff and source evidence: Twelve runtime tests cover persistence and observed native queue auto-start behavior.
### Required work
Persist schedules and delivery attempts; prevent overlapping role turns and retry only safely reconciled deliveries. Provide view, pause/resume and health controls. Keep failed and uncertain attempts visible. Expose bounded native read and helper-gated message operations to role tasks.
### Scope and non-goals
Only the requested supervision group's fixed role cadences and action messages. No generic workflow engine or desktop automation-file impersonation.
### Deliverables and recorded state
Scheduler owner, service loop, CLI, persisted schedule IDs and receipts.
### Resource and economy contract
One group and the changed runtime only; preserve the data-disk preflight, fixed role cadences and bounded native reads. Do not broaden into unrelated builds or task histories.
### QA and independent review
Focused automated checks validate this Block; Block 3 adds native independent Sol review of direct target deltas and owner-backed live integration evidence. A passing route gate alone is not delivery.
### Acceptance
Schedules survive restart, due work executes once, role context is reused, and route rejection prevents delivery.
### Negative tests
Reject wrong target/recipient, suppress duplicate delivery, retain uncertain writes, and skip already-active roles.
### Completion evidence
Twelve focused runtime tests pass: persistent schedule/receipt restart, lost add/start responses, uncertainty withholding, active-role behavior, pause, wrong-target/content rejection and gated send denial. Semantic gates remain in the existing helper; operational schedule/receipt state has a distinct SQLite owner. Live native dispatch and independent integration checks are Block 3 acceptance.
### Stop
Stop before activating the service.

## Block 2 — Supervisor roles and GCP installation

Status: `completed`

### Objective
Run the requested five-role supervision group under a persistent GCP system service.
### Inputs and dependencies
Block 1 accepted and native task creation available.
### Target-product capability delta
- Posture: consequential
- Intended capability gain: Five persistent supervisor roles and an enabled GCP system service.
- Potential capability loss or regression: Incorrect role bindings or an undurable initial task could defeat monitoring.
- Protected-capability effect: Verify all five roles and three real schedule owner records against canonical policy.
- Architecture and operating-model effect: Systemd launches the controller with AF_UNIX only and the existing daemon executes turns.
- Tradeoff and source evidence: Native initialization, binding and live execution evidence is saved; no desktop callback is used.
### Required work
Create real role tasks using the skill prompts and explicit native transport instructions. Initialize one canonical group, bind real role and schedule IDs, install the reviewed runtime, and enable a system service under the existing operating-system account. Reuse the current daemon; keep source and state on the data disk.
### Scope and non-goals
One target. No patent implementation effects or Gmail.
### Deliverables and recorded state
Service unit, installed source identity, role IDs, schedule bindings, operating instructions.
### Resource and economy contract
One group and the changed runtime only; preserve the data-disk preflight, fixed role cadences and bounded native reads. Do not broaden into unrelated builds or task histories.
### QA and independent review
Focused automated checks validate this Block; Block 3 adds native independent Sol review of direct target deltas and owner-backed live integration evidence. A passing route gate alone is not delivery.
### Acceptance
The service is active without a desktop connection; all bindings resolve to real owner state.
### Negative tests
Installation or binding mismatch fails before activation; unavailable daemon remains a visible retryable failure.
### Completion evidence
Installed release `2fe3f8ef2005e03a3fe4a440c3ef6c39d6b14a21`; manifest hashes match installed files. The systemd unit is enabled and active, with `RestrictAddressFamilies=AF_UNIX` and no SSH environment. All five persistent role IDs and three enabled SQLite schedule IDs match canonical policy version 3. The initial unused reviewer and its policy history were retained during the guarded pre-delivery bootstrap repair. See [operations](gcp-native-supervision-operations.md).
### Stop
Stop before claiming live acceptance.

## Block 3 — Live verification and operating handback

Status: `completed`

### Objective
Demonstrate that the installed monitor performs its intended work.
### Inputs and dependencies
Block 2.
### Target-product capability delta
- Posture: routine
- Routine or not-applicable justification: Verify the installed monitor and restart recovery without expanding its capabilities.
### Required work
Observe scheduled liveness and watcher turns, a direct target read, a gated role delivery and independent review. Restart only the new service and verify retained schedules/receipts. Validate a service-launched isolated check with no desktop transport/environment. Record precise limits: do not claim a physically disconnected desktop test unless performed.
### Scope and non-goals
Bounded installed-service verification, not a broad product regression.
### Deliverables and recorded state
Current acceptance evidence, tracker statuses and concise operational handback.
### Resource and economy contract
One group and the changed runtime only; preserve the data-disk preflight, fixed role cadences and bounded native reads. Do not broaden into unrelated builds or task histories.
### QA and independent review
Focused automated checks validate this Block; Block 3 adds native independent Sol review of direct target deltas and owner-backed live integration evidence. A passing route gate alone is not delivery.
### Acceptance
Real wake, read, delivery and restart evidence agree with the configured owner. Supervision is reported active only after these pass.
### Negative tests
Missing/failed/uncertain evidence cannot be labeled successful; an idle task alone cannot prove semantic completion.
### Completion evidence
Twenty focused tests pass and unit verification passes. Native changed-state delivery `64112c73-a26b-5c4e-8ed5-18a200ea0bd9` was acknowledged in base-review turn `01a07054-9676-7161-aed9-7a84f95c16bd`; independent Sol direct-delta check `EVT-000004` found no supported intervention. After controller restart from PID 1030036 to 1039353, all three schedules and sixteen prior receipts were retained. A new scheduled liveness turn `01a07057-15c7-79e2-b8b4-1811e23f9ea6` completed direct target read and liveness-gate commands with exit code zero. Acceptance assertions and exact identities are retained at `/srv/patent-studio/private/gcp-supervision/acceptance.json`. No physical desktop-disconnection test or patent completion is claimed.
### Stop
Stop infrastructure expansion once the requested GCP monitor is operational; preserve the patent implementation scope and its separate continuation state.
