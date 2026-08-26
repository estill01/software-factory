# Software Factory Operations Dashboard

The dashboard is a local, single-operator control room. Its Factory Floor,
project/run/task drill-downs, tracker review, reports, metrics, Admin health,
and owner-gated controls are backed by typed loopback APIs to the current
tracker, Git, supervision, report, automation, and Codex App Server owners. It
stores only project discovery metadata and process-local operation correlation;
it does not keep a second operational ledger or infer completion.

## Prerequisites

- Python 3.11 or newer and `uv`
- Node.js 24 and npm 11
- Codex CLI 0.147.0 and the exact internal `codex-app-server-client` 0.1.0 wheel
  accepted by the Factory pin

The dashboard is not an independently resolvable public package. Its server is
composed with the sibling `runtime` package by `dashboard/server/pyproject.toml`'s
local uv source. The shared client is an unpublished, no-license internal artifact;
never resolve either dependency from a bare registry name/version.

No global frontend package installation is required.

The frozen frontend family is React 19.2, TypeScript 7.0, Vite 8.1, React
Router 8.2, TanStack Query 5.101, Jotai 2.20, Zod 4.4, Tailwind 4.3,
Recharts 3.9, Vitest 4.1, and Playwright 1.61. Exact installed versions are in
`dashboard/web/package-lock.json`.

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
SOFTWARE_FACTORY_CODEX_CLIENT_WHEEL=/absolute/qualified/codex_app_server_client-0.1.0-py3-none-any.whl \
  uv run --project dashboard/server software-factory-dashboard --port 8787
SOFTWARE_FACTORY_DASHBOARD_PORT=8787 npm --prefix dashboard/web run dev
```

Open `http://127.0.0.1:5188`. Vite proxies `/api` to the Python service.

## Build and run the production shell

```bash
npm --prefix dashboard/web run build
SOFTWARE_FACTORY_CODEX_CLIENT_WHEEL=/absolute/qualified/codex_app_server_client-0.1.0-py3-none-any.whl \
  uv run --project dashboard/server software-factory-dashboard --port 8787
```

Open `http://127.0.0.1:8787`. Choose another free port with `--port`; the
service rejects non-loopback hosts. The production server serves the Vite build,
SPA routes, `/api/v1/health`, security headers, and per-launch mutation-nonce
plumbing. Project, tracker, supervision, report, metrics, task, operation, and
Factory Floor APIs share that origin. Read projections remain distinct from
mutation: every consequential request uses the nonce-protected operation
boundary and a maintained external owner.

Startup loads `software_factory.provider_provenance` from the exact sibling
runtime composition and verifies the configured client wheel's filename, SHA-256,
content root, member count, byte count, version, protocol identity, and accepted
utils producer roots before import. `--codex-client-wheel` may be used instead of
the environment variable. Omitting the exact artifact leaves app-server features
unavailable; it never falls back to a package registry.

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
client validates list/detail responses with closed Zod schemas and renders the
exact maintained-verifier Block total, status counts, dependency order,
current task/tracker/supervision active-Block claims, source disagreement, Git
posture, evidence, diagnostics, source links, and bounded semantic source diff.
The workspace never edits Markdown, changes Block status, accepts work, or
calculates a synthetic progress percentage. Author/review/revise/implement
buttons are separate owner-mediated operations.

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

The read projection service reads canonical supervision and automation roots,
does not inspect automation prompt bodies, and does not generate or mutate
operational truth. Separate operation definitions can request maintained
supervision checks/reviews, policy adjustment, binding repair, pause/resume,
mission/task continuity, reporting, evolution evaluation, and terminal
shutdown. Each preview names its owner and exact postcondition; the dashboard
reports `applied` only after that owner state is re-read. Each target and report
still fails locally so one damaged source cannot erase healthy operations data.

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
must reconstruct its result from its canonical task, ledger, automation,
report, or catalog source. The closed registry exposes only named typed
definitions for task control, tracker workflows, supervision attach/check/
review/adjust/binding/lifecycle, reporting, Factory evolution, succession, and
terminal handling. A source-ineligible definition is absent or marked
unavailable with its owner-local reason.

## Inspect and control Codex tasks

At process start the server requires `--codex-client-wheel` and loads it only
through the Factory verifier. The verifier binds producer revision
`a5659745a7cbcbb002b5f06051f6ed9826f721a7`, package version 0.1.0, accepted
source/tree identities, and wheel SHA-256
`1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`.
Bare registry name/version resolution and copied client source are rejected.
The shared package owns binary inspection, schema compatibility, JSON-RPC,
stdio lifecycle, correlation, event/callback coordination, bounds, and cleanup.
The dashboard retains only Factory projections and owner-gated workflow policy.
A package, version, schema, handshake, transport, or message failure disables
every task mutation without affecting file-backed project, tracker,
supervision, report, or metric reads.

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
current approval/input response. The UI exposes only the corresponding closed
operation definitions, bounded prompt builders, current task/request
fingerprints, specific confirmation, and canonical postcondition checks. Admin
also exposes the exact same-origin, nonce-gated shared-client restart and shows
the qualified package identity, resolved CLI version, protocol/schema posture,
capability matrix, last error, pending request count, and reconnect state. Raw
protocol methods, arbitrary
prompts or payloads, model settings, general tools, remote transports, task
forking, and permission-profile grants are not exposed.

Supply the exact accepted wheel with `--codex-client-wheel`. Override only the
executable path, not protocol arguments, with `--codex-binary`; use
`--codex-home` when the canonical session owner root is not `~/.codex`. The
qualified artifact is unpublished and has no selected license, so this internal
pin is not public installability, reuse, redistribution, or release authority.

## Operation and recovery guidance

Use [`RUNBOOK.md`](RUNBOOK.md) for the concise operating sequence, source-truth
interpretation, consequential-control checklist, compatibility recovery, and
explicit authorization boundaries. In particular, interrupt, semantic pause,
resume, request-stop, terminal reporting, and terminal shutdown remain separate
operations and cannot prove one another.

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
