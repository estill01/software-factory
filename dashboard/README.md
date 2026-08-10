# Software Factory Operations Dashboard

The dashboard is a local, single-operator control room. It currently provides
the loopback runtime, typed transport, accessible application shell, a bounded
multi-project catalog, and read-only APIs for implementation trackers, Git
currentness, supervision, reports, owner-produced metrics, and a version-gated
Codex task adapter. Its composed Factory Floor is the default operating view;
detailed project, run, tracker, report, and task workspaces remain in later
tracker Blocks.

## Prerequisites

- Python 3.11 or newer and `uv`
- Node.js 24 and npm 11
- Codex CLI 0.145.0 for the frozen App Server compatibility contract

No global frontend package installation is required.

## Install and validate

```bash
npm --prefix dashboard/web ci
uv sync --project dashboard/server
npm --prefix dashboard/web run check
uv run --project dashboard/server python -m unittest discover \
  -s dashboard/server/tests -p 'test_*.py'
```

## Develop

Run the API on a free loopback port, then start Vite. Both defaults deliberately
avoid port 5173.

```bash
uv run --project dashboard/server software-factory-dashboard --port 8787
SOFTWARE_FACTORY_DASHBOARD_PORT=8787 npm --prefix dashboard/web run dev
```

Open `http://127.0.0.1:5188`. Vite proxies `/api` to the Python service.

## Build and run the production shell

```bash
npm --prefix dashboard/web run build
uv run --project dashboard/server software-factory-dashboard --port 8787
```

Open `http://127.0.0.1:8787`. Choose another free port with `--port`; the
service rejects non-loopback hosts. The production server serves the Vite build,
SPA routes, `/api/v1/health`, security headers, and per-launch mutation-nonce
plumbing. Read-only project, tracker, supervision, report, and metrics APIs are
served from the same origin, including the composed Factory Floor.

## Register projects

Open **Admin** and register an exact canonical Git top-level path. The dashboard
never scans the workstation for repositories. Catalog records contain only a
stable ID, display label, canonical root, optional relative Markdown tracker
globs, optional description, and archived posture. They never copy task, run,
tracker, report, supervision, or completion state.

The versioned catalog is stored at:

```text
~/.codex/software-factory/dashboard/projects.json
```

The file is created only on the first mutation, written atomically with
owner-only permissions, deterministically ordered, and protected by an
optimistic source fingerprint. A valid prior file can be projected read-only
when the current file is malformed. Use `--catalog-path /absolute/path.json`
for isolated testing or an alternate local profile.

The project API surface is deliberately narrow:

```text
GET   /api/v1/projects?include_archived=false
GET   /api/v1/projects/{project-id}
POST  /api/v1/projects
PATCH /api/v1/projects/{project-id}
```

Writes require the exact page origin and per-launch nonce. Supported actions
are registration, presentation updates, archive, and unarchive. Archiving only
removes a project from normal dashboard views; it never deletes files, changes
the repository, stops work, or changes source truth.

Discovery is bounded to registered roots and reports Git revision/branch plus
tracker candidate paths. Each project has its own observed time, coverage,
limitations, and exact discovery errors, so a missing repository does not hide
healthy projects.

## Inspect tracker truth

Tracker reads stay behind the loopback service:

```text
GET /api/v1/trackers
GET /api/v1/trackers/{tracker-id}
```

The adapter reads only discovered Markdown files inside active registered
roots, invokes the maintained `author-implementation-trackers` verifier with
the exact full profile or the two Block-0-approved inherited core path/content
roots, and
projects source-linked header/frame/map/Block sections. It derives exact status
and evidence-posture counts, dependency eligibility, verifier diagnostics, and
Git HEAD/index/worktree/blob/history/upstream currentness. It does not calculate
a progress percentage or treat `completed-with-open-items` as accepted.

Tracker identity is deterministic from project ID and relative path. Raw-file
metadata includes the exact local path and line/anchor ranges for local opening;
Markdown remains the sole writer. Dirty, untracked, invalid, stale-bound, and
source-unavailable trackers remain distinct. One tracker or project failure is
returned locally and does not erase healthy projections.

Unchanged analysis is cached only by tracker content hash, verifier hash, and
profile. Git reads are batched per repository for list refreshes. The React
client validates list/detail responses with closed Zod schemas but does not yet
render a tracker workspace; that interface begins in Block 8. No endpoint in
this slice edits a tracker, accepts a Block, changes status, or starts work.

## Inspect supervision, reports, and metrics

The operations adapter exposes maintained owner truth through four read-only
routes:

```text
GET /api/v1/runs
GET /api/v1/runs/{target-thread-id}
GET /api/v1/reports
GET /api/v1/metrics
```

Run projections keep current-mission and predecessor history distinct, show the
supervisor topology and exact role, task, and automation bindings, and separate
mechanical activity from semantic conclusions. Incidents, decisions, lifecycle
transitions, successor continuity, attention reasons, and source-local failures
retain exact source references. Registered projects with no canonical run
binding are returned explicitly as unmonitored rather than silently omitted.

Weekly, terminal, and Factory-evolution reports are included only with their
maintained verification result, manifest members, content hashes, and derived
disposition. Metrics come from the maintained supervision owner for the active
mission only. Cross-run totals aggregate additive dimensions but never
synthesize percentiles, and API-equivalent cost is always labeled as an
estimate with its assumptions.

The service reads canonical supervision and automation roots, does not inspect
automation prompt bodies, and does not create, repair, pause, resume, stop, or
otherwise mutate supervised work. It also does not generate reports. Each
target and report fails locally so one damaged source cannot erase healthy
operations data.

## Operate from the Factory Floor

The default route reads one same-origin aggregate:

```text
GET /api/v1/factory-floor
```

The endpoint composes the catalog, tracker/Git, supervision/report/metric, and
Codex task adapters without storing operational state or choosing a source
winner. It pairs current supervision targets with exact tasks when available,
keeps unmonitored tasks and unresolved or disagreeing bindings visible, and
returns transparent red, amber, green, or neutral posture with a textual
reason, observation time, and `completion_claim: false`. A two-second
process-local response cache coalesces simultaneous page loads; the browser
polls only while visible and can request an explicit refresh.

The page has four bounded operating regions: implementation/supervisor rows,
ranked attention, semantic conclusions beside accepted tracker outcomes, and
metrics/source freshness. Project, time, posture, and severity filters never
change source ranking. Any critical item hidden by filters or the default
limit remains counted visibly. Rows, attention items, conclusions, outcomes,
source states, and metric tiles open an inspector that retains the exact owner
identity plus a source revision or path when supplied. Source states retain
their coverage and limitation reason; metric tiles retain their exact period
and coverage. API-equivalent cost is always an estimate and is never labeled
as actual spend.

Independent source failure remains local. The top envelope becomes partial,
the affected region shows its limitation, and healthy catalog, file-backed
tracker, supervision, report, or task data remain visible. The endpoint accepts
no query parameters and exposes no mutation, lifecycle, workflow-start, or
acceptance control.

## Use the administrative operation boundary

Consequence-bearing dashboard controls use one same-origin, nonce-protected
operation protocol:

```text
GET  /api/v1/operations
GET  /api/v1/operations/{operation-id}
POST /api/v1/operations/preview
POST /api/v1/operations/execute
POST /api/v1/operations/{operation-id}/cancel
```

The closed registry binds every preview to an exact operation type, target,
project, input, current source fingerprint, named owner, confirmation contract,
and route-gate result where cross-task routing is required. Execution consumes
the token once and reports `applied` only after the operation-specific canonical
postcondition is verified. Request acceptance, awaiting approval/input,
verification timeout, owner failure, and eventual workflow completion remain
distinct.

Correlation and activity are process-local; the dashboard does not create a
second durable operation ledger. After restart, a later owner-backed operation
must reconstruct its result from its canonical task, ledger, automation, report,
or catalog source. No tracker, task, supervision, report, evolution, or lifecycle
operation is registered in the generic framework slice itself.

## Inspect and control Codex tasks

At process start the server resolves the configured `codex` executable,
requires exact `codex-cli 0.145.0`, generates the non-experimental App Server
JSON schemas into a temporary directory, and verifies all 273 files against the
frozen semantic manifest root
`757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`.
Only then does it start one long-lived stdio child and perform the required
initialize/initialized handshake. A version, schema, handshake, transport, or
message failure disables every task mutation without affecting file-backed
project, tracker, supervision, report, or metric reads.

Selected request parameters, success results, notifications, callbacks, and
JSON-RPC errors are all validated against that generated bundle. Response IDs
must match exactly. Timeout, disconnect, malformed/oversized message, duplicate
response, and compatibility failures terminate the child, expose a capped
reconnect delay, and never synthesize task state.

The narrowed read surface is:

```text
GET /api/v1/task-integration
GET /api/v1/tasks?limit=50&cursor=<opaque>
GET /api/v1/tasks/{task-id}?include_turns=true
GET /api/v1/task-events
```

Task list/detail responses include exact IDs, cwd, registered-project binding,
status, timestamps, turns/items, truncation, pending approval/input requests,
source revision, coverage, and limitations. The event route is a bounded,
ephemeral same-origin Server-Sent Event stream authenticated with the
per-launch nonce; it is an invalidation channel, not a durable event ledger.
Browsers authenticate the GET with exact loopback Host, launch nonce, and
same-origin fetch metadata when Chromium omits `Origin`; nonce-only and
cross-site requests are rejected. Replay is sequence-based and limited to the
current in-memory window.

The adapter implements typed task start/resume, turn start/steer/interrupt, and
current approval/input response capabilities for later registered owner
workflows. Block 5 does not expose those as generic HTTP or UI controls; their
operation previews, currentness gates, and bounded prompt builders belong to
the operation-framework Blocks. The only mutation exposed here is the exact
same-origin, nonce-gated adapter-child restart. Admin shows the resolved CLI
version, protocol/schema posture, capability matrix, last error, pending request
count, and restart action. Raw protocol methods, arbitrary prompts or payloads,
model settings, general tools, remote transports, task forking, and permission-
profile grants are not exposed.

The compatibility artifact and deterministic regeneration metadata are in
`server/src/software_factory_dashboard/app_server_compatibility.json`. Override
only the executable path, not protocol arguments, with `--codex-binary`.

## Browser tests

With the production service running on port 8787:

```bash
SOFTWARE_FACTORY_DASHBOARD_URL=http://127.0.0.1:8787 \
  npm --prefix dashboard/web run test:e2e
```

The server never performs broad filesystem discovery and never exposes a raw
command/protocol console, remote binding, filesystem deletion, or a second task
store. Read readiness does not imply tracker acceptance, supervision lifecycle,
or implementation completion.
