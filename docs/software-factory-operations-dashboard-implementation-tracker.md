# Software Factory Operations Dashboard Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–25
- Repository: `https://github.com/estill01/software-factory.git`
- Governing objective: direct user request in Codex task
  `019fe547-e054-7ca0-9940-ec4aa146df78`, 2026-08-08: provide a dashboard
  that monitors current and historical Software Factory work and metrics across
  projects, supports administration and operation, and makes implementation
  trackers and progress reviewable; use the frontend stack recovered from task
  `019fc4d5-2791-7823-997e-e7a38163ef2a`. Direct refinement in the same task,
  2026-08-09: make the center a factory floor that shows running
  implementations and supervisors, what each supervises, overall state/issues,
  red/green-style operating posture, actions, conclusions, and history at a
  glance.
- Planning baseline: repository commit
  `c7d4efce3e3bf5fb3a8dbc4d9ab0db0ef2cd89bd`. The audit began at predecessor
  `e2b7064a7a226409518a883ecec88661469309b8` while unrelated supervision work
  was in flight; that work settled during planning as `c7d4efc` and added
  general-mission targets plus same-thread mission succession. Every
  implementation Block must still re-inspect and bind its inputs to a fresh
  exact revision.

## 1. Purpose and intended outcome

Create a local, single-operator Software Factory factory-floor dashboard that
answers, without shell archaeology:

1. What is the Factory doing now, in which project, task, run, tracker, and
   Block?
2. What has it done, what evidence establishes the result, and what remains
   open or stale?
3. What do cross-project throughput, availability, review, incident, decision,
   resource, and outcome metrics actually show?
4. Which implementation trackers are ready, active, accepted, invalid,
   inherited, or waiting on exact evidence?
5. What owner-authorized action can the operator take next, and did that action
   have the intended canonical effect?

The default experience is a factory floor: one row/card per running or recently
active implementation, directly paired with the supervisor group watching it,
what that group is supervising, current Block/checkpoint, last and next check,
open issue posture, recent supervisory action, and latest evidence-bound
conclusion.

The dashboard is a maintained projection and control surface over existing
owners. It does not become a second tracker, task system, event ledger,
scheduler, report authority, or completion authority.

Completion means:

- one responsive dashboard can register and inspect multiple local projects;
- the factory floor shows all discoverable running implementations and
  supervisor groups, their exact target relationships, live/idle/paused/
  unavailable posture, current work, traffic-light operating state with reason,
  last/next supervisory activity, and unassigned or multiply-bound anomalies;
- the factory floor distinguishes active work, attention-required work,
  accepted history, stale evidence, unavailable integrations, and merely
  planned capability using current source records;
- project, run, task, tracker, report, incident, decision, transition, role,
  automation, and metric views drill down to exact source identities and
  timestamps;
- supervisor action and conclusion history preserves checks, steering,
  escalations, reviews, incident findings/resolutions, decisions, checkpoint/
  meta-review conclusions, terminal conclusions, superseded conclusions, and
  their exact evidence and target;
- tracker review exposes the capability frame, dependency order, Block status,
  acceptance, negative tests, completion evidence, verifier profile and
  diagnostics, Git currentness, and mapped execution state without rewriting
  tracker truth;
- cross-project metrics preserve source coverage and limitations, label cost as
  an estimate rather than billing telemetry, and let the operator reach the
  underlying records;
- enabled administrative controls can create or continue Codex tasks for
  tracker authoring, Block implementation, supervision, reporting, evolution,
  and bounded lifecycle operations, while unavailable or unproven operations
  are visibly disabled;
- every consequential operation has a preview, expected source fingerprint,
  owner/gate explanation, confirmation, in-flight state, and postcondition
  check against the authoritative owner;
- responsive, keyboard, dark-mode, loading, empty, error, stale, and partial-
  integration states are verified at maintained desktop, tablet, and mobile
  viewports; and
- current observable behavior, not tests, commits, reports, or task terminality
  alone, establishes final acceptance.

### Mission frame

- Primary outcome: give one operator a trustworthy cross-project view and real
  control of Software Factory work while preserving the authority and evidence
  contracts that make the Factory reliable.
- Observable completion: the dashboard is run against at least three real
  registered projects with an active run, historical run, implementation
  tracker, report history, and at least one consequence-bearing operation; the
  named views and interactions are proven with fresh source-bound API, browser,
  and outcome evidence.
- Ordinary effect classes needed: source discovery, deterministic projection,
  local configuration, visualization, task creation and continuation,
  owner-gated administration, validation, documentation, and operator handoff.
- Hard direct authority or safety boundaries: the direct request above;
  canonical tracker Markdown and Git history; the three skill contracts;
  supervision policy, ledger, and gate owners; Codex task/App Server authority;
  Codex automation authority; report contracts; local loopback-only operation;
  and explicit user confirmation for consequential actions.
- Material goal alteration or reversal: remote or multi-user hosting, accounts,
  permissions/tenancy, a replacement tracker/task/scheduler/ledger, autonomous
  background mutation, direct automation-file editing, arbitrary shell access,
  or allowing the dashboard to infer completion or reserved authority would
  require renewed direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker adds a new operator-visible product,
  local runtime, cross-project read model, and controlled operating surface over
  protected Software Factory owners.
- Direct product sources: the governing request above; `README.md` and
  `CHANGELOG.md` at
  `c7d4efce3e3bf5fb3a8dbc4d9ab0db0ef2cd89bd`;
  `author-implementation-trackers/SKILL.md`,
  `implement-tracker-blocks/SKILL.md`, and
  `supervise-tracker-runs/SKILL.md` as re-frozen in Block 0; current scripts and
  contracts named in the owner map below; reference task
  `019fc4d5-2791-7823-997e-e7a38163ef2a`; reference frontend manifest
  `/Users/ethanstillman/code/celltonomy/patent-studio/web/package.json`; and the
  official Codex App Server contract at
  `https://learn.chatgpt.com/docs/app-server`.
- Product thesis and intended effect: a simple, clean, progressively disclosed
  factory-floor dashboard should make Factory truth legible and actionable
  across projects. Observation is broad; mutation remains narrow, explicit,
  gated, and verified through its existing owner.
- Protected capabilities: direct mission authority; tracker and accepted-
  history integrity; mechanical-watcher versus semantic-review boundaries;
  exact Block stops; single-writer Git, automation, Gmail, report, and ledger
  ownership; dependency-safe continuation; cross-thread route gates; safe-
  frontier decisions; successor continuity; evidence-bound outcome closure;
  estimated-versus-measured metric semantics; and planned-versus-implemented
  truth.
- Architecture strategy: add one loopback Python projection/control adapter and
  one React application under `dashboard/`. Reuse repository validators and
  CLIs, read canonical local artifacts in place, integrate Codex through a
  version-gated App Server stdio adapter, and keep only project discovery
  metadata in a small dashboard-owned catalog. Use polling and one ephemeral
  live-event channel rather than a database, durable cache, or second event
  bus.
- Requested capability: current/historical monitoring, cross-project metrics,
  project/run/task administration, tracker and progress review, and real
  workflow initiation and control.
- Proportionality: a read-only report browser would under-deliver the requested
  administration and run capability; a hosted multi-user platform or new
  orchestration backend would exceed it. A local adapter plus explicit task-
  mediated operations is the narrow end-to-end design.
- Tradeoffs: live reads and explicit provenance cost more UI detail than a
  synthetic health score; App Server integration adds version sensitivity but
  provides real task control; a minimal local catalog adds one new writer but
  owns only discovery metadata; staged task-mediated operations are slower than
  direct file mutation but preserve authority, approvals, and evidence.
- Uncertainty: App Server schemas and supported methods are version-specific;
  current automation mutation coverage must be proven in the implementation
  environment; tracker-to-run associations are not always fully represented by
  one canonical record; and currently planned tracker-authoring supervision and
  adaptive Factory-evolution controls must remain unavailable until their
  implementation evidence exists.

## 2. Target architecture and authority boundaries

```text
registered local project roots                     Codex App Server (stdio)
  |                                                      |
  +-- tracker Markdown + Git --------+                   +-- tasks/turns/items
  +-- supervision policy/ledger -----+                   +-- approvals/input
  +-- incidents/reviews/decisions ---+                   +-- bounded operations
  +-- reports/metrics/manifests ------+                              |
  +-- automation projections --------+                              |
                                      v                              v
                         loopback Python adapter
                       deterministic typed projections
                    + explicit operation preview/gates
                                      |
                       JSON API + ephemeral event stream
                                      |
                                      v
                      React/TypeScript/Vite dashboard
              factory floor / projects / trackers / reports / admin
                                      |
                            operator confirmation
                                      |
                   existing owner performs the mutation
                                      |
                   canonical-source postcondition re-read
```

Authority rules:

1. Tracker Markdown owns declared Block order, statuses, and completion
   evidence. The dashboard parses, verifies, and projects it; it does not keep a
   mutable shadow tracker or mark Blocks complete.
2. Git owns repository revision, file currentness, worktree state, and
   durability. Read adapters use argument-vector subprocesses rooted only in
   registered repositories. The dashboard does not provide arbitrary Git or
   shell execution.
3. `supervision_log.py` and its hash-chained artifacts own run policy, events,
   incidents, decisions, successor transitions, and lifecycle records. The
   dashboard imports or invokes the maintained validators; it never edits those
   files directly.
   Long-lived target threads may have sequential mission roots: current floor
   state and gates use only the active mission-scoped records, while predecessor
   missions remain preserved history and never leak completion or conclusions
   into the successor.
4. Weekly, terminal, and Factory-evolution artifacts remain derived and retain
   their own validators, manifests, coverage, and limitations. A report is not
   completion authority, and estimated token/cost fields are not billing
   telemetry.
5. Codex App Server owns live task and turn state. Its generated, version-bound
   schemas are validated at startup. Unsupported or disconnected task control
   degrades to an explicit read-only state rather than a guessed protocol.
6. Codex automation tooling owns automation creation and mutation. TOML files
   may be projected read-only; pause, resume, schedule, or stop requests travel
   through the owner and are accepted only after actual automation and
   lifecycle state are re-read.
7. The dashboard catalog owns only operator-provided project identity,
   repository root, optional tracker discovery patterns, and presentation
   state such as archived/not archived. It may not store copied status,
   evidence, policy, events, reports, or task truth.
8. Same-target task continuation may use the App Server task owner. Any message
   crossing into a different maintained task or role must first pass
   `thread-route-gate` with the exact recipient, purpose, source record, and
   action. A failed or unavailable gate fails closed.
9. A control progresses through `previewed`, `confirmed`, `requested`, and then
   `applied` or `failed/unverified`. Only a canonical postcondition can produce
   `applied`; a successful HTTP response, emitted prompt, terminal task, or
   generated report alone cannot.
10. `Interrupt turn` is distinct from semantic `pause supervision`, `resume`,
    `request stop`, and terminal shutdown. Destructive or authority-sensitive
    actions require specific language and never share a generic Stop control.
11. The HTTP service binds only to `127.0.0.1` by default, serves the built
    application and `/api/v1`, permits mutation only from the same origin with
    a per-launch nonce, and rejects traversal, symlink escape, unregistered
    roots, stale source fingerprints, unknown operations, and shell-shaped
    input.
12. No source available is represented as `unknown` or `unavailable`, never as
    zero, healthy, complete, or inactive. Every projection includes source,
    `observed_at`, source revision/fingerprint, coverage, and limitations.
13. The browser reads and acts only through the loopback `/api/v1` surface and
    its authenticated event stream. Every route selects one closed typed
    adapter and calls the primary owner through a maintained import, exact
    argument-vector subprocess, or version-gated App Server stdio method.
    Runtime routes may not fall back to fixtures, demo rows, frontend filesystem
    access, duplicated owner logic, or hard-coded operational state. Every
    response identifies its owner, version or revision, fingerprint, coverage,
    limitations, and source-local failure posture.

### Operator capability map

| Surface | Required capabilities | Canonical source/effect owner |
|---|---|---|
| Factory Floor | running/recent implementations paired with supervisor groups and targets; red/amber/green/neutral operating posture; last/next check; recent action and conclusion; needs attention; recent accepted work; freshness; bounded cross-project KPIs | composed projections with links to exact owners |
| Projects | register/archive discovery metadata; list repositories, trackers, tasks, runs, reports, current work, and history | dashboard catalog for discovery only; project sources for truth |
| Project/run detail | mission, current Block/checkpoint, event timeline, supervisor group/roles/targets, checks/actions/conclusions, incidents, decisions, transitions, schedules, reports, and outcome posture | supervision artifacts, App Server, Git, tracker |
| Trackers | discovery; full/core verifier posture; capability frame; dependency order; Block details; evidence; Git currentness; mapped run progress | tracker Markdown, verifier, Git, bound run records |
| Metrics | throughput, activity, availability, reviews, incidents, resolution time, resource estimates, coverage, and limitations with filtering and drill-down | verified report metrics and canonical source records |
| Reports | Markdown/PDF/JSON/manifest inventory, preview, download, verification, historical comparison | maintained report/evolution owners |
| Tasks | live status, turns, streamed items, approvals/input, continue, steer, interrupt, and open/deep-link identity | Codex App Server |
| Start work | author/review a tracker; implement selected Block range; attach supervision | the named skill in a Codex task, then its canonical artifacts |
| Supervision admin | status, bind/adjust request, policy/schedule projection, report/evolution workflow, pause/resume/request-stop/terminal workflow | supervisor, automation, report, evolution, and lifecycle owners |
| Admin health | source availability, version compatibility, catalog health, validation failures, data freshness, and disabled-control reasons | each adapter plus dashboard runtime |

### Information architecture and interaction contract

- Primary navigation is limited to `Factory Floor`, `Projects`, `Trackers`,
  `Reports`, and `Admin`; task, implementation, supervisor, and run detail are
  contextual routes or bounded inspectors rather than more primary navigation.
- The default screen shows no more than: the implementation/supervisor floor,
  `Needs attention`, `Latest conclusions and accepted outcomes`, and a compact
  metric/freshness strip. Detailed timelines, raw records, policies, and
  diagnostics use drill-down or a bounded inspector.
- Each floor row preserves separate identities for the implementation task,
  tracker/Block, supervised target, supervisor group, watcher/reviewer/fix roles,
  and their automations. Missing, orphaned, duplicate, or mismatched bindings
  are visible conditions, never joined by label alone.
- Traffic-light posture is a transparent derived view with text and icon, never
  color alone and never a completion claim: `red — action required` for a
  current high/critical incident, pending required approval/input, gate-proven
  empty safe frontier, broken required integrity, or prohibited/incomplete stop
  or successor; `amber — attention` for warning incidents, stale/late required
  checks, nonblocking decisions/transitions, partial integration, or degraded
  bindings; `green — on track` only when required sources are fresh for the
  configured cadence, bindings are valid, work is progressing or legitimately
  idle, and no red/amber rule applies; and neutral labeled states for paused,
  completed/accepted, unmonitored, unavailable, or unknown. Every light exposes
  its triggering facts and observed time.
- Operating-state history is recomputed from immutable source records and shows
  each red/amber/green/neutral transition, trigger, supervisory action, later
  resolution, and conclusion when the source supports them. It is a derived
  timeline, not a new state ledger.
- A `conclusion` is an exact semantic output from an authorized reviewer/
  supervisor owner—for example checkpoint/meta-review disposition, incident
  finding/resolution, decision, terminal outcome reconciliation, report review,
  or evolution evaluation. Mechanical watcher checks and task terminality are
  activity, not semantic conclusions. Conclusions retain author/role, source
  record, target, candidate/source revision, time, disposition, limitations,
  successor/superseded posture, and required next action.
- Attention ranking is a transparent ordered rule set, not a hidden score:
  pending approval/input; verified open critical/high incident; blocking
  decision with empty safe frontier; incomplete successor transition; failing
  source integrity/verifier; stale or unverified claimed completion; active
  warning; unavailable required integration. Items show the rule that placed
  them there.
- Status labels preserve exact source vocabulary. `accepted`, `completed-with-
  open-items`, `in-progress`, `blocked`, `stale`, and `unavailable` are not
  merged into a generic completion percentage. Aggregate progress shows counts
  and denominator rather than inventing weighted percent-complete.
- Every chart has a textual summary or table, exact period/time zone, source
  coverage, and a drill-down path. Empty data and incomplete coverage remain
  distinguishable.
- Desktop uses a bounded content rail and optional inspector; tablet and mobile
  collapse navigation and inspectors without horizontal document overflow.

### Reference frontend stack contract

Use the reference task's frontend family, with versions refreshed only through
an explicit compatibility change in Block 1:

- React `19.2.x`, React DOM, and TypeScript `7.0.x`;
- Vite `8.1.x`;
- React Router `8.2.x`;
- TanStack Query `5.101.x` for server state, polling, invalidation, and action
  lifecycle;
- Jotai `2.20.x` only for ephemeral client state such as filters, inspector,
  and local layout state;
- Zod `4.4.x` for every API and App Server boundary;
- Tailwind CSS `4.3.x`, repository-owned shadcn/ui-style primitives, Radix
  primitives, Lucide icons, CVA, `clsx`, and `tailwind-merge`;
- Recharts `3.9.x` for the bounded metric views;
- Vitest `4.1.x`, Testing Library, `jest-axe`, jsdom, and Playwright `1.61.x`;
  and
- modular route-owned features, accessible keyboard operation, responsive
  behavior, dark mode, and explicit loading/empty/error/stale states.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Tracker authoring and review | `author-implementation-trackers/SKILL.md` and `scripts/verify_tracker.py` | reuse; create/review through a Codex task, never duplicate verifier rules in TypeScript |
| Block execution | `implement-tracker-blocks/SKILL.md` | reuse through an explicit tracker path and Block/range task |
| Supervision operation | `supervise-tracker-runs/SKILL.md` and `references/supervision-policy.md` | reuse after Block 0 freezes the settled live revision |
| Run policy and evidence | `supervise-tracker-runs/scripts/supervision_log.py` and `~/.codex/supervision/tracker-runs/` | reuse validators and CLI; project read-only projections |
| Weekly reports | `supervise-tracker-runs/scripts/weekly_report.py` and report artifacts | reuse metrics/manifest contracts; preserve limitations |
| Terminal reconciliation | `supervise-tracker-runs/scripts/terminal_report.py` and terminal records | reuse; do not infer outcome closure |
| Factory evolution | `supervise-tracker-runs/scripts/factory_evolution.py` and its contract | reuse only where current implementation/authority permits |
| Task state and operation | local `codex app-server` protocol and generated schemas | adapt behind a version-gated stdio client |
| Automation state/mutation | Codex automation tool and `~/.codex/automations/` projection | read files only for status; mutate through the tool owner |
| Repository truth | Git CLI in each registered root | reuse read-only queries; implementation tasks remain Git writer |
| Frontend conventions | reference task `019fc4d5-2791-7823-997e-e7a38163ef2a` and Patent Studio `web/package.json` | adapt stack and quality posture, not product-specific UI |
| Local HTTP pattern | Patent Studio monitor API's `ThreadingHTTPServer`/`BaseHTTPRequestHandler` pattern | adapt narrowly; avoid a second backend framework unless Block 1 proves necessity |
| Dashboard discovery metadata | no existing owner | add the minimal versioned project catalog in Block 2 |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Reference frontend task | `019fc4d5-2791-7823-997e-e7a38163ef2a` | adapt | 1 | reproduce the stack and quality contract; do not copy Patent Studio domain behavior |
| Patent Studio frontend manifest | live manifest inspected 2026-08-08; freeze content hash in Block 0 | adapt | 1 | resolve/install an exact dashboard lockfile and record intentional version differences |
| Patent Studio monitor server | live source inspected 2026-08-09; freeze content hash in Block 0 | adapt | 1 | retain only loopback/static/API patterns justified here |
| Current supervision CLI and artifacts | `c7d4efce3e3bf5fb3a8dbc4d9ab0db0ef2cd89bd` | reuse after reinspection | 0, 4 | preserve implementation/main-thread targets, active mission scoping, policy-history mission succession, and exact settled owner semantics |
| Current authoring verifier | repository revision `c7d4efce3e3bf5fb3a8dbc4d9ab0db0ef2cd89bd` | reuse | 3 | wrap exact JSON diagnostics and full/core profile semantics |
| Current reports/evolution | repository revision `c7d4efce3e3bf5fb3a8dbc4d9ab0db0ef2cd89bd` plus live artifacts | reuse | 4, 9 | project verified metrics, history, manifests, and limitations |
| Existing trackers in `docs/` | live hashes frozen per project scan | reuse | 3, 8 | support new full-profile and inherited core-profile truth without rewriting them |
| Official Codex App Server protocol | installed CLI `codex-cli 0.145.0` observed during planning; regenerate in Block 5 | adapt | 5 | handshake, schema generation, task/turn streaming, approvals/input, and fail-closed compatibility |
| Adaptive decision/evolution tracker | plan current at implementation time | not-adopted as live capability | 0, 22 | show planned/unavailable until independently accepted implementation exists |
| Tracker-authoring supervision tracker | plan current at implementation time | not-adopted as live capability | 0, 11 | do not expose a working control until implementation is proven |

## 5. Scope, non-goals, and proportionality

### In scope

- one local dashboard runtime and maintained frontend;
- multiple explicitly registered local repositories/projects;
- deterministic discovery and projection of trackers, Git currentness, Codex
  tasks, supervision runs, automations, reports, evolution artifacts, and
  current/historical metrics;
- exact attention, freshness, coverage, limitation, and source-provenance states;
- responsive factory-floor, project/run, tracker, metrics/report, task, and
  admin views;
- project-catalog administration;
- consequence-bearing task creation/continuation, tracker authoring/review,
  Block execution, supervision attachment/control, report/evolution, and
  lifecycle workflows where their owners are proven available;
- streamed task items, approvals, and user-input requests needed by those
  workflows;
- local runtime/security, source-integrity, adapter, API, component,
  accessibility, browser, and outcome validation; and
- operator runbook, feature/compatibility matrix, and changelog update.

### Out of scope

- cloud deployment, remote network access, mobile-native applications, or a
  hosted control plane;
- accounts, authentication providers, collaboration, comments, assignments,
  ACL/RBAC, organization tenancy, or simultaneous operators;
- a replacement tracker editor, task system, event ledger, scheduler,
  automation store, report store, Git client, billing system, or telemetry
  service;
- direct mutation of tracker Markdown, supervision JSON/JSONL, report artifacts,
  Git repositories, or automation TOML by dashboard code;
- Gmail message reading/sending in the dashboard; existing Gmail-gated
  supervision may be projected, while message operations stay with their owner;
- generalized plugin management, arbitrary prompt execution, arbitrary shell
  commands, arbitrary filesystem browsing, or arbitrary App Server method
  invocation;
- hidden health/productivity scores, model-performance judgments not present in
  verified artifacts, or treating cost projections as actual spend;
- implementing capabilities that the existing planned trackers have not yet
  delivered; and
- styling breadth, animations, customizable layouts, or chart proliferation
  beyond the named operator decisions.

### Proportionality

The requested outcome requires a real maintained UI and a narrow local adapter;
static generated reports alone cannot operate or monitor current work. The
dashboard nevertheless reuses every canonical owner, stores only discovery
metadata, uses exact source projections instead of a database, limits primary
navigation and charts, and sends mutations through the owner that already has
the relevant authority and evidence contract.

## 6. Block execution contract

1. Execute Blocks 0–25 in dependency order. Parallel work is allowed only
   where the status table has no unmet dependency and each worker has disjoint
   files and one declared integration owner.
2. Re-read the selected Block and inspect the live repository, external
   reference, installed Codex CLI, source artifacts, and dirty-worktree state
   before editing.
3. Preserve unrelated and in-flight work. In particular, do not build against
   or overwrite unresolved supervision changes; freeze an accepted owner
   revision first.
4. Implement through the narrowest existing owner and stop at the Block's
   boundary.
5. A global safeguard, inspected source, existing owner, or exclusion constrains
   work only when the Block crosses that boundary; it does not authorize new
   machinery, fields, tests, or a separate audit dimension.
6. Optional hardening requires a reproduced supported failure tied to the
   Block's objective. Otherwise omit it.
7. Run focused validation, mapped validation, and required independent review.
8. Before expensive final validation, finish all known in-scope work and any
   review permitted to change the candidate. Freeze the candidate revision;
   later changes stale only affected proof.
9. Reuse exact current artifacts and cheap currentness checks before deep scans;
   batch coherent reads and widen only on a declared trigger.
10. Record only exact current evidence. Label aborted, pre-correction, partial-
    source, or changed-during-validation runs diagnostic.
11. Audit and accept one Block before advancing, then stop rather than search
    for optional hardening.
12. A genuine input dependency blocks only its exact subjects and descendant
    closure. Record its decision packet, blocked-scope root, safe-frontier root,
    permitted provisional/common work, prohibited authority effects, and
    revisit trigger; continue every dependency-independent slice.
13. For supervised input gates, run the maintained bounded resolution protocol
    before requesting user guidance. Do not mark a Block or run blocked while
    the safe frontier is nonempty.
14. An operation-specific hold states its exact operation or Block scope,
    content-minimized identity, expiry event, successor posture, and
    `carry-forward: false`. On expiry it remains history only.
15. A dashboard action is incomplete until its named canonical postcondition is
    re-read. Preserve requested-but-unverified and failed actions; do not convert
    them to success because the client received `2xx` or a task stopped.
16. Every Block that changes an API schema updates the shared Zod contract,
    Python fixture, and consumer in the same candidate; no untyped transitional
    payload is accepted.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<value or not-applicable with reason>`
- Inputs: `<paths, IDs, versions, hashes>`
- Outputs: `<paths, IDs, versions, hashes>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<bounds, actual use, widening or not-applicable>`
- Independent review: `<evidence or not-applicable with reason>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<decision packet, blocked scope, safe frontier,
  timed attempts, handoff, resumed evidence, or not-applicable>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Product contract and live-owner baseline | — | `accepted` |
| 1 | Loopback runtime and reference frontend scaffold | 0 | `accepted` |
| 2 | Project catalog and bounded discovery | 1 | `in-progress` |
| 3 | Tracker truth and Git-currentness projection | 2 | `not-started` |
| 4 | Supervision, automation, report, and metrics projection | 2 | `not-started` |
| 5 | Codex task and App Server adapter | 1 | `not-started` |
| 6 | Cross-project factory floor | 3, 4, 5 | `not-started` |
| 7 | Project and run workspaces | 6 | `not-started` |
| 8 | Tracker review and progress workspace | 3, 6 | `not-started` |
| 9 | Metrics and report history workspace | 4, 6 | `not-started` |
| 10 | Gated administrative operation framework | 2, 4, 5 | `not-started` |
| 11 | Author, implement, supervise, and task-control workflows | 8, 10 | `not-started` |
| 12 | On-demand mechanical supervision checks | 7, 10, 11 | `not-started` |
| 13 | Semantic supervision review requests | 7, 10, 11 | `not-started` |
| 14 | Supervision policy and cadence administration | 7, 10, 11 | `not-started` |
| 15 | Mission and target/tracker binding repair | 7, 10, 11 | `not-started` |
| 16 | Role-task binding repair | 7, 10, 11 | `not-started` |
| 17 | Automation binding repair | 7, 10, 11 | `not-started` |
| 18 | Supervision pause and resume | 7, 10, 11 | `not-started` |
| 19 | Same-target mission succession | 7, 10, 11 | `not-started` |
| 20 | Successor-task continuity | 7, 10, 11 | `not-started` |
| 21 | Weekly supervision report workflow | 9, 10, 11, 13 | `not-started` |
| 22 | Factory evolution evaluation and disposition | 9, 10, 11, 13 | `not-started` |
| 23 | Terminal report workflow | 9, 10, 11, 13, 21 | `not-started` |
| 24 | Request-stop and terminal shutdown | 7, 9, 10, 11, 23 | `not-started` |
| 25 | Integrated outcome validation and operator handoff | 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24 | `not-started` |

Required order:

```text
0 → 1 → 2 → {3, 4}
    └───────→ 5
{3, 4, 5} → 6 → 7
{3, 6} → 8
{4, 6} → 9
{2, 4, 5} → 10
{8, 10} → 11
{7, 10, 11} → {12, 13, 14, 15, 16, 17, 18, 19, 20}
{9, 10, 11, 13} → {21, 22}
{9, 10, 11, 13, 21} → 23
{7, 9, 10, 11, 23} → 24
{6–24} → 25
```

Blocks with satisfied direct dependencies may proceed concurrently; exact order
is governed by the dependency table, not diagram layout.

Renumbering note: commit `0fe280cc1deac763b906755265c7d0e53307ff0c`
is preserved as the rejected predecessor for incident
`INC-20260809-073305-B81DCB`. Its old Block 12 was split into current Blocks
12–24 at independent owner, acceptance, recovery, and Stop boundaries; its old
Block 13 moved mechanically to Block 25. Blocks 0–11 remain substantively
unchanged. Exact-review-rejected successor commit
`cbe7c55cc2eae20d3c2bd70704cf5a5fc93546e4` is also preserved: its Block 15
was split into current Blocks 15–17, its Blocks 16–19 moved to 18–21, its Block
20 was narrowed to current Block 22's derived evaluation/disposition owner, and
its Blocks 21–23 moved to 23–25. Prior structural verification/review remains
diagnostic rather than current completion proof.

Data-backing clarification: the direct 2026-08-09 operator request to ensure
that the application is backed by primary Software Factory functionality and
data was reviewed against the existing owner split. No generic backend Block
was added because accepted Block 1 owns loopback transport, Blocks 3–5 own
tracker/Git, supervision/reporting/metrics, and App Server adapters, Block 6
owns their composed read model, and Block 10 owns gated mutations. Those future
slices are strengthened below so each remains independently acceptable and no
second implementation of a primary owner is introduced.

## Block 0 — Product contract and live-owner baseline

Status: `accepted`

### Objective

Freeze the implementation-time capability, source, authority, compatibility,
and truth-label contract before dashboard code adopts any changing owner.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish one reviewable definition of what the
  dashboard may observe, operate, and call complete.
- Potential capability loss or regression: a stale or permissive baseline
  could expose planned functionality as real, adopt transient supervision
  edits, or create duplicate authority.
- Protected-capability effect: preserves direct authority, current source
  binding, exact role/writer boundaries, planned-versus-implemented truth, and
  outcome-based completion.
- Architecture and operating-model effect: selects the live owners and adapter
  compatibility envelope that every later Block must follow.
- Tradeoff and source evidence: an explicit baseline adds one early review but
  avoids building a control plane against assumptions; it is required by the
  direct request, the three skill contracts, the planning-time supervision
  owner transition from `e2b7064` to `c7d4efc`, the reference task, and the
  version-specific App Server contract.

### Inputs and dependencies

- The governing request and planning baseline named above.
- Current repository/worktree, installed Codex CLI, live supervision/report/
  automation artifacts, and reference frontend sources.
- No implementation Block dependency.

### Required work

- Re-inspect `README.md`, `CHANGELOG.md`, the three skills, all named scripts/
  contracts, current trackers, live artifact schemas, and the settled Git
  revisions that own them.
- Record a concise implementation-time feature matrix with `supported`,
  `read-only`, `planned`, `unavailable`, and `out-of-scope` states plus the
  exact evidence for each consequential control.
- Freeze source hashes/versions for the frontend manifest, monitor pattern,
  Codex CLI/generated App Server schema, tracker verifier, supervision owner,
  report/evolution owners, live artifact schema samples, and automation
  projection.
- Define exact terminology and precedence for project, task, target, run,
  tracker, Block, checkpoint, lifecycle, accepted, completed-with-open-items,
  stale, unavailable, and unknown.
- Resolve only genuine source conflicts. When a source is still in flight,
  preserve the dependent capability as unavailable and record the exact revisit
  trigger rather than adopting it provisionally.
- Obtain independent product/architecture review of the frozen contract before
  accepting it.

### Scope and non-goals

- In scope: the capability and owner baseline needed by Blocks 1–25.
- Not in scope: server/frontend implementation or correction of any source
  owner.
- Do not turn source inspection into a generalized audit or require unrelated
  repository cleanup.

### Deliverables and recorded state

- `docs/software-factory-operations-dashboard-contract.md` containing the
  source inventory, version/content roots, terminology, capability matrix,
  owner/postcondition map, unsupported reasons, and revalidation triggers.
- Small redacted representative fixtures only where a live schema cannot be
  deterministically generated during tests; fixtures record their source hash
  and limitation.

### Resource and economy contract

Inspect each named owner once, reuse exact hashes and generated schemas, and
sample at most one valid and one material invalid artifact per schema family.
Widen only when a schema/version conflict is reproduced. Finish likely-mutating
review before freezing the baseline.

### QA and independent review

- Mechanically verify every path/version/hash and check that each enabled
  mutation names one existing owner, gate, and observable postcondition.
- A reviewer other than the baseline author challenges underreach, speculative
  infrastructure, planned-as-implemented claims, duplicate ownership, and
  missing failure states against the exact candidate revision.

### Acceptance

- Every capability row has one truthful posture and evidence source.
- Every future control has one owner, authority/gate, confirmation class,
  expected postcondition, and unavailable behavior.
- No in-flight or merely planned capability is represented as available.
- Independent review reports no unresolved supported capability or authority
  gap.

### Negative tests

- Reject a capability matrix that marks tracker-authoring supervision or
  adaptive autonomous evolution as available using only their planned trackers.
- Reject an enabled operation with no canonical postcondition or an owner bound
  to uncommitted/transient source.

### Completion evidence

- Repository commit: accepted contract candidate
  `ee0837d58f62b3d1e359dffc81a2f58c8b1868d5`; maintained supervision-owner
  input settled separately at
  `08b4f983749b6018eb7169f3a509ea2d43f5c6ed`.
- External/domain revision or root: reference frontend task worktree
  `f924555752cb0efc4acde86cf3d515782939ce05`, Patent Studio selected-file
  revision `640b80f1400fb1a2af0a5971052065812e8cf9c2`, Codex App Server 0.145.0
  semantic schema root
  `757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`,
  active mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`,
  and bounded supervision prefix through `EVT-000030` root
  `af5f70d81a0398682e3a1bf1ec168c146be8386b26a5882dc1bc7ed18b173e77`.
- Inputs: tracker authoring revision `2b73de1`, tracker blob
  `7c9d758bb535687e6a85091b083f4fa2fbb6ddce`, tracker SHA-256
  `dab97d29851453058955cd7b3545ebd8bf96945ee686ce72706e33d18159eed7`,
  capability-frame SHA-256
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`,
  direct-user authority item 44, routed start item 79, policy version 4, and the
  exact owner/source hashes recorded in the contract.
- Outputs:
  `docs/software-factory-operations-dashboard-contract.md`, Git blob
  `17e04c1be7364562934d943ee88ebb73fa83ba7d`, SHA-256
  `4f9a55ef0f0f2b8eb12973d9a2eb393cf0148e99caf18fffa4e7dc12fcf0dfc0`.
- Focused validation: all named repository/reference file hashes matched;
  `git diff --check` passed; the first 30 ledger records reproduced the
  `EVT-000030` prefix and policy/history roots; one fresh and the frozen
  0.145.0 App Server generations each contained 273 files and matched the
  recorded `jq 1.8.1 -S -c` semantic root; current `bind`/`lifecycle-gate` and
  activation behavior were inspected; 137 supervision-helper tests passed.
- Mapped validation: full tracker verifier passed 26 Blocks with 0 errors and
  0 warnings; 30 verifier tests passed; the adaptive tracker passed full with
  14 Blocks, and the evolution and tracker-authoring trackers passed their
  maintained core profiles with 7 and 5 Blocks.
- Candidate freeze: initial contract `fffc853`; provenance successor
  `241469d` rejected; remediated `8929dfa` rejected; exact final candidate
  `ee0837d58f62b3d1e359dffc81a2f58c8b1868d5` remained unchanged after the
  accepting review.
- Remediation closure: first review findings mapped target/tracker repair to
  unavailable, split resume from supported pause, refreshed the bounded event
  sample, and added a reproducible schema algorithm; second review findings
  replaced raw-byte schema hashing with the cross-generation semantic root and
  stopped successor binding at `pending` while making first-work closure
  unavailable. Exact review then accepted both affected slices.
- Resource posture: one bounded valid live sample per available artifact family,
  no copied fixtures, one remediation schema generation, and no runtime or
  dependency manifest. Diagnostic command defects were preserved but not used
  as proof: a zsh variable shadowed command lookup, an escaped `awk` wrapper
  failed before hashing, three external reference paths were corrected, a
  nonexistent expanded commit SHA was rejected, and an append changed the live
  whole-ledger hash before the prefix algorithm was adopted.
- Independent review: `tracker_exact_review` accepted exact commit
  `ee0837d58f62b3d1e359dffc81a2f58c8b1868d5`; it reproduced the 273-file
  semantic root, accepted the supported-binding/unavailable-closure split,
  confirmed the diff was limited to the two cited findings, and reported no
  material remaining issue.
- Retained open work: before executing Blocks 15, 18, or 19, narrowly amend
  those future slices for unavailable target/tracker repair, unavailable
  semantic resume, and evidence-insufficient first-work closure. These are
  explicit descendant gates, not accepted capabilities or Block 0 defects.
- Decision/continuation posture: no current blocked scope; Blocks 1–14 and
  every dependency-safe descendant remain the safe frontier. Continue with
  Block 1 without a new mission, successor task, manual resume, or broad
  reinspection.
- Post-block audit: `accepted`; the contract is source-bound, planned features
  remain planned/unavailable where required, and the Block 0 Stop was honored.
- Git durability: a non-force push advanced
  `origin/codex/evolution-mvp` from `2b73de1` through acceptance checkpoint
  `6ef84c767c7a145fd4283c4d86769c4dabb88085`; local and remote then matched
  exactly with `0 0` divergence. This evidence-finalization successor is
  included in the immediate follow-on non-force push before Block 1 begins.

### Stop

Stop before creating the dashboard runtime or dependency manifests.

---

## Block 1 — Loopback runtime and reference frontend scaffold

Status: `accepted`

### Objective

Establish the maintained local runtime and exact reference frontend foundation
without adding product behavior owned by later Blocks.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: provide one installable, testable loopback service
  and one coherent application shell on the requested frontend stack.
- Potential capability loss or regression: dependency drift, an exposed bind
  address, duplicated backend framework, or premature global state could make
  the dashboard unsafe or inconsistent with the reference.
- Protected-capability effect: preserves local single-operator scope, explicit
  API boundaries, accessible UI foundations, and repository-owned components.
- Architecture and operating-model effect: adds `dashboard/server/` as the
  narrow Python adapter and `dashboard/web/` as the React application; the
  server owns static/API transport, not domain truth.
- Tradeoff and source evidence: a maintained runtime costs more than a static
  page but is necessary for live monitoring and controls; the chosen stack and
  standard-library loopback pattern come from the reference task and inspected
  Patent Studio sources.

### Inputs and dependencies

- Accepted Block 0 contract and frozen reference versions.

### Required work

- Create `dashboard/server/` with a small Python package and CLI that binds
  `127.0.0.1`, serves `/api/v1/health`, and serves a production frontend build;
  allow an explicit alternate loopback port without permitting non-loopback
  hosts by accident.
- Create `dashboard/web/` with React, TypeScript, Vite, React Router, TanStack
  Query, Jotai, Zod, Tailwind, repository-owned shadcn/ui-style primitives,
  Recharts, Vitest/Testing Library/axe, and Playwright at the accepted exact
  lockfile versions.
- Configure the Vite development proxy to the Python service, `@` import alias,
  route-level code splitting, test setup, deterministic scripts, and production
  static fallback for client routes.
- Implement the five-item navigation shell, responsive content rail, theme,
  keyboard-visible focus, error boundary, loading shell, not-found route, and
  connection/integration status region using placeholders only.
- Define a shared API envelope (`data`, `source`, `observed_at`, `fingerprint`,
  `coverage`, `limitations`, structured `error`) with matching Python fixtures
  and Zod validation.
- Add a per-launch mutation nonce and same-origin enforcement plumbing, but no
  mutation endpoint before Block 10.
- Document install, development, test, build, and local-run commands without
  requiring global package installs beyond the documented Codex/runtime
  prerequisites.

### Scope and non-goals

- In scope: runtime, transport, dependency lock, application shell, design
  primitives, and test foundations.
- Not in scope: project discovery, source adapters, real dashboards, metrics,
  or operations.
- Do not add authentication, a database, remote hosting, service workers,
  analytics, or a generalized component system.

### Deliverables and recorded state

- `dashboard/server/`, `dashboard/web/`, exact lockfile, runtime scripts,
  foundational tests, and local developer instructions.
- A built application that renders the shell and exact unavailable/empty
  placeholders through the Python server.

### Resource and economy contract

Install once from the frozen manifest, reuse the lockfile, and run focused
server/unit/component checks before one production build and one shell browser
smoke. Dependency changes outside the accepted stack require a reproduced need
and Block 0 contract amendment.

### QA and independent review

- Verify Python CLI/health/static fallback, API envelope contract, Zod rejection,
  TypeScript, lint/format if configured, unit/component tests, production build,
  axe smoke, and Playwright shell navigation.
- Review the exact build for reference-stack fidelity, local-only exposure,
  minimal navigation, responsive shell behavior, and absence of inert controls.

### Acceptance

- One documented command starts the local service and the built application;
  `/api/v1/health` reports runtime and integration availability without leaking
  local secrets or broad filesystem paths.
- All requested stack owners are present at accepted versions and used for
  their declared roles.
- The shell works by keyboard and at maintained desktop, tablet, and mobile
  viewports with loading, empty, error, and dark-mode states.
- No placeholder looks enabled or claims live data.

### Negative tests

- Reject startup on a non-loopback host without a future direct-authority
  change.
- Reject an API payload that fails its Zod boundary or a mutation request with
  the wrong origin/nonce.

### Completion evidence

- Activation authority: direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
  routed item 79 supplied resume/start-routing evidence only. Work began from
  accepted Block 0 checkpoint
  `6ef84c767c7a145fd4283c4d86769c4dabb88085` and durability successor
  `c0bb5d188fbf3083aae07576c0719b4fbf5bc84a`, without a new mission or
  successor-task requirement.
- Candidate history: exact initial candidate
  `9153dcb7dd5ab9ac3e65e07cf46a3887100596c9` was rejected by independent
  review because a failed health check left a contradictory ready claim on the
  floor and the frontend did not parse the server's structured error envelope.
  The rejected revision remains preserved as diagnostic history.
- Focused remediation: runtime readiness now derives from the shared health
  query, non-success responses pass through a Zod-validated error envelope,
  and regression coverage aborts health at unit and browser boundaries.
  Focused Vitest passed 5 tests; the full frontend check passed 7 tests across
  3 files; the production build passed; and Playwright passed 15 desktop,
  tablet, and mobile cases including the failed-health posture.
- Accepted candidate: exact successor
  `9d8654fc7f4c3543660df599f88cd9f777609503`, tree
  `130a9ac76b6502093e4ff13eb5f4599877afff0d`; the candidate remained
  unchanged after fresh review.
- Delivered behavior: `dashboard/server/` provides the installable
  standard-library loopback CLI, `/api/v1/health`, production SPA fallback,
  shared envelope, security headers, per-launch nonce, same-origin guard, and
  explicit absence of mutations. `dashboard/web/` provides the exact frozen
  React/TypeScript/Vite stack, route-split five-workspace shell, theme,
  loading/error/not-found/unknown states, responsive rails, and honest source
  readiness. Root and dashboard developer documentation expose one local run
  path on port `8787`, not `5173`.
- Validation: Python passed 6 tests with `ResourceWarning` promoted to errors;
  TypeScript and Vitest passed 7 tests across 3 files; the production build
  passed with route-specific chunks; Playwright passed 15 cases across
  desktop, tablet, and mobile, including axe, overflow, navigation, theme,
  fallback, and failed-health truth checks. The full tracker verifier passed
  26 Blocks with 0 errors and 0 warnings, its 30 verifier tests passed, local
  Markdown links resolved, and `git diff --check` passed.
- Live runtime proof at `127.0.0.1:8787`: health was `ok` with explicitly
  partial coverage; the injected nonce was 43 characters; SPA fallback was
  `200`; hashed assets were immutable; invalid Host and traversal were `400`;
  wrong origin and nonce were `403`; a correctly guarded nonexistent mutation
  remained `404`; and CSP, `DENY`, and `no-store` headers were present.
- Independent review: `tracker_exact_review` rejected exact `9153dcb` on the
  two preserved truth-boundary findings, then accepted exact `9d8654f` after
  reproducing focused Vitest 5/5, full frontend 7/7, build, Playwright 15/15,
  Python 6/6, the full tracker verifier, and the focused diff. It reported no
  material finding and confirmed that no catalog, project-source read, or
  later-Block operation was introduced.
- Resource posture: one frozen dependency install and lockfile were reused;
  no additional frontend family or browser engine was installed, and the
  initial browser/accessibility diagnostics were retained as remediation
  evidence rather than completion proof.
- Post-block audit: `accepted`; the requested shell is runnable and truthful,
  all real operational sources remain unavailable, and the Block 1 Stop was
  honored before project catalog creation or source reads.
- Git durability: a non-force push advanced `origin/codex/evolution-mvp` from
  `c0bb5d1` through accepted Block 1 checkpoint
  `0e8ff510e80a1fe0e18693b66503782c43aceeab`; local and remote then matched
  with `0 0` divergence. This evidence-finalization successor is included in
  the immediate follow-on non-force push before Block 2 begins.

### Stop

Stop before creating the project catalog or reading any project source.

---

## Block 2 — Project catalog and bounded discovery

Status: `in-progress`

### Objective

Let the operator register and discover multiple local projects while keeping
all project status and evidence in their canonical owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: establish a stable cross-project namespace and
  bounded roots from which all monitoring views can be assembled.
- Potential capability loss or regression: a catalog that copies status or
  scans arbitrary directories could become stale, leak filesystem scope, or
  become a second source of truth.
- Protected-capability effect: preserves canonical source ownership and local
  path boundaries while enabling multi-project use.
- Architecture and operating-model effect: adds one versioned dashboard-owned
  JSON catalog for discovery metadata and one deterministic discovery adapter.
- Tradeoff and source evidence: explicit registration requires a small operator
  step but avoids broad home-directory discovery and ambiguous project
  inference; no current owner represents dashboard presentation identity.

### Inputs and dependencies

- Accepted Block 1 runtime and API contract.
- Block 0 source/terminology contract.

### Required work

- Define the minimal catalog schema: stable project ID, label, canonical
  repository root, optional tracker include patterns rooted inside the project,
  optional display description, and archived posture. Exclude copied run/task/
  tracker/report/status fields.
- Store catalog state atomically under
  `~/.codex/software-factory/dashboard/projects.json` with versioning,
  permission checks, recoverable prior-file handling, and deterministic ordering.
- Implement list/register/update-presentation/archive/unarchive operations with
  path canonicalization, Git-root detection, duplicate/root-overlap rules,
  symlink/traversal rejection, optimistic source fingerprinting, and explicit
  confirmation for removal from the visible catalog.
- Discover within each registered root only: tracker candidate paths, Git
  identity/current revision, and source families made visible by Blocks 3–5.
  Use accepted default tracker patterns plus project-specific includes; do not
  crawl unrelated descendants or inspect file content outside known sources.
- Return per-project discovery health, observed time, exact failures, and
  partial coverage rather than dropping an unhealthy project.
- Add the Admin project-catalog panel with validated forms and clear distinction
  between archiving dashboard discovery and deleting project data (which is
  never performed).

### Scope and non-goals

- In scope: project discovery metadata, bounded registration, catalog-only
  administration, and project inventory API/UI.
- Not in scope: tracker parsing, live task/run binding, source mutation, or
  recursive workstation discovery.
- Do not add tags, ownership teams, arbitrary custom fields, remote repositories,
  or filesystem deletion.

### Deliverables and recorded state

- Versioned catalog schema/store, discovery service, API routes, Zod contracts,
  Admin catalog panel, fixtures, and focused tests.

### Resource and economy contract

Normal refresh stats the catalog and registered roots, reads Git root metadata,
and evaluates only configured tracker globs. Cache only in memory by source
fingerprint. Widen a project scan only when the operator adds an explicit
pattern; never scan `$HOME` or follow symlinks outside the registered root.

### QA and independent review

- Test atomic writes, stale-fingerprint conflicts, malformed versions,
  duplicate IDs/roots, nested roots, symlink escape, traversal, missing roots,
  non-Git roots, archive/unarchive, partial project failure, and restart replay.
- Independently review that the catalog is necessary and contains no copied
  operational truth or hidden destructive behavior.

### Acceptance

- The operator can register at least three repositories, refresh them
  independently, archive one from normal views, and restore it.
- A missing or invalid project does not prevent healthy projects from loading,
  and its exact limitation remains visible.
- Catalog records contain discovery/presentation metadata only and mutations
  reject stale source fingerprints.

### Negative tests

- Reject a project root outside the explicitly submitted canonical path after
  symlink resolution, a tracker pattern that escapes that root, or a catalog
  field that attempts to store Block/run status.
- Reject any UI wording implying that catalog removal deletes or stops the
  underlying project.

### Completion evidence

- Activation: began automatically from accepted and pushed Block 1 durability
  checkpoint `90f5eaf2f37296e3d7c4d8ef2e5dad19e1326f60` under the same direct-user
  implementation authority and mission root; no new mission, routed authority,
  or manual resume was introduced.
- Candidate, validation, review, checkpoint, and acceptance evidence: pending.

### Stop

Stop before parsing tracker content or aggregating supervision/task state.

---

## Block 3 — Tracker truth and Git-currentness projection

Status: `not-started`

### Objective

Project implementation tracker structure, verification, progress, evidence,
and Git currentness exactly enough for trustworthy review.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make tracker readiness and progress inspectable
  across projects without opening Markdown or interpreting status by hand.
- Potential capability loss or regression: a lossy parser or synthetic percent
  could hide open items, profile compatibility, dependency errors, or stale
  completion evidence.
- Protected-capability effect: preserves tracker Markdown as sole writer,
  exact statuses, Block order/stops, full/core verifier semantics, accepted-
  history integrity, and evidence-bound completion.
- Architecture and operating-model effect: adds a read-only typed tracker/Git
  adapter that invokes the existing verifier and derives only labeled views.
- Tradeoff and source evidence: structured parsing adds maintenance at the UI
  boundary but is required for review; invoking the existing verifier avoids
  duplicating its doctrine.

### Inputs and dependencies

- Accepted Block 2 registered roots and tracker discovery.
- Frozen authoring skill/verifier contract from Block 0.

### Required work

- Parse the tracker header, mission/capability frame, owner/source maps, status
  table, required order, each whole-number Block and required sections,
  verification matrix/final definition when present, and exact Markdown anchors.
  Preserve unknown sections as linked source content rather than discarding
  them.
- Invoke `verify_tracker.py --json` with the declared/default profile policy:
  full for newly authored full-profile trackers and explicit inherited core
  compatibility only where the source contract permits. Return profile,
  command/version, diagnostics, and exit status without relabeling a core-valid
  inherited tracker as full-valid.
- Derive transparent counts by exact status, dependency eligibility, evidence
  presence, and open/stale posture. Do not calculate an opaque weighted percent
  or treat `completed-with-open-items` as accepted.
- Read Git currentness for each tracker: repository HEAD, tracked/untracked,
  worktree change, blob/content hash, last committed change, upstream/durability
  when available, and comparison to a run-bound tracker hash when canonical
  records supply one.
- Produce tracker list/detail APIs with source fingerprint, parser limitations,
  verifier diagnostics, source anchors, and exact raw-file-open path metadata.
- Implement this as a closed Python adapter behind `/api/v1`: the React client
  never reads Markdown or Git directly. HTTP contract tests must compare the
  response with the same registered file, Git revision, and maintained tracker
  verifier invocation, including the owner command/version and source-local
  failure in the response.
- Add fixture coverage for the repository's current full-profile, inherited
  core-profile, malformed, dirty, untracked, and changed-after-binding cases.

### Scope and non-goals

- In scope: read-only tracker structure, verifier output, derived counts,
  dependency eligibility, completion-evidence presence, and Git currentness.
- Not in scope: editing Markdown, assigning status, accepting a Block, generic
  Markdown rendering, or starting work.
- Do not fork the tracker schema into a database or reimplement the verifier in
  frontend code.

### Deliverables and recorded state

- Python tracker/Git adapters, typed API/Zod contracts, exact-source anchors,
  representative fixtures, and unit/contract tests.

### Resource and economy contract

Fingerprint path metadata and content first; reuse a verifier result only for
the same verifier version, profile, and tracker content hash. Batch Git queries
per repository. Run no more than one verifier process per distinct tracker hash
per refresh and widen parsing only for a reproduced supported tracker form.

### QA and independent review

- Cross-check adapter output against direct verifier JSON and Git commands for
  all current repository trackers and representative external-project trackers.
- Independently review status/evidence semantics and confirm no derived field is
  presented as canonical or as proof of observable outcome.

### Acceptance

- Each discovered tracker has a deterministic identity, exact status counts,
  dependency/readiness posture, verifier profile/result, Git currentness, and
  source navigation.
- Full-valid, core-only valid, invalid, dirty, untracked, stale-bound, and
  partially parsed trackers remain visibly distinct.
- Repeated reads at unchanged fingerprints reuse results; changed tracker or
  verifier fingerprints selectively invalidate them.

### Negative tests

- Reject a status-table/Block-line mismatch, duplicate/non-contiguous Block,
  impossible dependency, missing full-profile delta, or malformed completion
  evidence through the maintained verifier and preserve its diagnostic.
- Reject any projection that reports `completed-with-open-items` as accepted or
  hides a dirty/stale tracker behind a green progress summary.

### Completion evidence

Pending.

### Stop

Stop before building tracker pages or initiating authoring/implementation tasks.

---

## Block 4 — Supervision, automation, report, and metrics projection

Status: `not-started`

### Objective

Expose current and historical supervision truth, automation posture, report
artifacts, and deterministic metrics across registered projects without
creating a second operational ledger.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator see active and historical Factory
  work, attention conditions, controls, and measured/estimated outcomes from
  exact canonical records.
- Potential capability loss or regression: partial ledgers, invalid hash chains,
  missing no-op wakes, estimated cost, or stale reports could be flattened into
  false health, availability, or completion claims.
- Protected-capability effect: preserves ledger/policy/report ownership,
  mechanical-versus-semantic role boundaries, incident/decision/successor
  lifecycle semantics, source coverage, and outcome-proof limits.
- Architecture and operating-model effect: adds read-only adapters and composed
  projections over existing supervision, automation, report, and evolution
  owners; no new durable operational state is introduced.
- Tradeoff and source evidence: exact provenance and partial-data states add
  visual complexity but are required by the repository's supervision and report
  contracts and demonstrated metrics posture.

### Inputs and dependencies

- Accepted Block 2 roots/catalog.
- Settled supervision, report, evolution, and automation contracts frozen in
  Block 0.

### Required work

- Discover supervision targets only from the configured supervision root and
  bind them to projects through canonical mission/policy/task cwd/tracker paths;
  where no authoritative association exists, keep an explicit unassigned run
  or operator-confirmed discovery binding without copying its lifecycle state.
- Support both tracker-governed implementation tasks and direct-user/system/
  repository main-thread missions. Tracker and Block are optional for the
  latter; never manufacture them merely to fit the dashboard schema.
- Resolve every policy revision to the mission root active for that revision.
  Project the current mission from the active binding and scope its checks,
  incidents, decisions, successor transitions, lifecycle, conclusions, and
  traffic light through the maintained mission-scoping owner. Preserve each
  predecessor mission as a separate historical segment with its terminal/
  superseded evidence and policy transition; never aggregate predecessor
  completion or issues into the active mission.
- Build an exact implementation-to-supervision topology: implementation task,
  tracker/Block or mission, supervised target, supervisor group, each mechanical
  watcher/semantic reviewer/fix/Gmail role task, role status, automation ID/
  cadence, last recorded wake/check/action, next scheduled wake when established
  by the automation owner, and binding integrity. Preserve orphaned supervisor,
  unmonitored implementation, duplicate owner, stale binding, and unavailable
  task/automation states instead of joining by a friendly label.
- Validate and project policy version/history, event hash chain, incidents and
  terminal/open heads, reviews, completion/lifecycle records, decisions and safe
  frontiers, successor transitions, role bindings, schedules, route-gate
  posture, last checkpoints, and source limitations through maintained owners.
- Project supervisory activity and semantic conclusions separately. Activity
  includes wakes/checks, reads, steering, escalation, correction, routing, and
  lifecycle requests. Conclusions include only reviewer/owner dispositions such
  as checkpoint/meta-review, incident cause/resolution, decision, terminal
  reconciliation, report review, and evolution evaluation, with exact author/
  role, target, candidate/source root, evidence, disposition, next action,
  limitation, and superseded/current posture.
- Project task/run history as exact timelines with event IDs, source record
  paths, timestamps, kinds, severity, category, owner/role, Block/checkpoint,
  mission root, and terminality. Preserve superseded/rejected history and expose
  policy mission-successor records as explicit boundaries, not ordinary events
  within one undifferentiated run.
- Read automation manifests read-only and map automation IDs, enabled state,
  schedule, target/task identity, and last known state only when the source
  contract establishes it. Surface missing/mismatched bindings rather than
  guessing.
- Inventory weekly, terminal, and Factory-evolution artifact bundles; invoke
  their validators; expose Markdown/PDF/JSON/manifest members, exact content
  roots, report/evaluation disposition, coverage, and limitations.
- Normalize verified metric dimensions needed by the capability map:
  accepted/attempted Blocks, events and activity, reviews, incidents opened/
  terminal/open, median/P90 resolution, availability inputs, decision and
  successor posture, role/model/reasoning activity, resource estimates, and
  API-equivalent cost projection. Partition current versus predecessor missions
  before aggregation and retain source units and definitions.
- Compose an attention feed with the explicit precedence rules in Section 2;
  each item includes rule, severity, source identity, observed time, and the
  source-specific detail route. Never use an opaque score.
- Derive the Section 2 traffic-light state for each implementation/supervisor
  pairing and a retrospective transition timeline from immutable events,
  automations, task status, bindings, issues, actions, and conclusions. Return
  all triggered facts, source timestamps, and cadence threshold; never persist
  the light as canonical state or call green complete.
- Implement project/run/report/metrics read APIs and freshness/error aggregation
  so one corrupt or unavailable source does not suppress independent healthy
  sources.
- Have the server call the frozen supervision, reporting, and evolution owners
  through maintained imports or exact argument-vector helpers and return the
  owner identity/root/revision with each projection. Runtime fixtures, copied
  operational JSON, frontend lifecycle interpretation, and duplicated metric
  logic are prohibited.

### Scope and non-goals

- In scope: deterministic validation and read projection of current owners,
  exact attention rules, cross-source project binding, and verified metrics.
- Not in scope: new events, incident decisions, lifecycle mutation, report
  generation, automation mutation, Gmail content, or new metric doctrine.
- Do not synthesize billing spend, infer unrecorded wake success, or treat a
  terminal task/report/test/commit as observable outcome proof.

### Deliverables and recorded state

- Supervision topology, action/conclusion history, traffic-light derivation,
  automation, report/evolution, metric, attention, and binding adapters; typed
  API/Zod contracts; redacted fixtures; validation/currentness tests; and
  source-definition metadata.

### Resource and economy contract

Use cheap directory metadata, policy/event/report fingerprints, and the latest
known validated content roots before reading full histories. Batch one source
family per target and reuse immutable historical prefixes. Normal dashboard
refresh must not regenerate reports or run cognitive review. Widen to a full
chain/report revalidation only after a root/version change, integrity failure,
or explicit manual refresh.

### QA and independent review

- Test valid and invalid hash chains, superseded incidents, open/terminal
  decisions and transitions, paused intervals, missing records, unknown event
  kinds, disabled/missing automations, corrupt/partial reports, cost-label
  semantics, cross-project binding, partial source failure, and selective
  invalidation.
- Test implementation with no supervisor, supervisor with no target, duplicate/
  stale role binding, late check, future/unknown next wake, mechanical activity
  misclassified as conclusion, superseded conclusion, each traffic-light rule,
  competing rules, neutral states, and derived transition history.
- Test trackerless direct missions, completed and explicitly superseded mission
  succession, active-root event scoping, policy hash/root mapping, predecessor
  history, prohibited succession with open incidents/decisions/task transitions,
  and absence of predecessor completion/green/conclusions in successor state.
- Cross-check representative projections against direct `supervision_log.py
  status`, report validators, raw source IDs, and live automation records.
- Independent semantic review must confirm that attention rules and metrics do
  not cross role/authority boundaries or overstate outcome, availability, cost,
  or completion.

### Acceptance

- At least one active, one historical, one incomplete-successor, one incident/
  decision, and one report-bearing run project accurately from their current
  sources with freshness and limitations.
- Invalid or partial source families remain isolated and visible; unaffected
  project data continues to render.
- Every aggregate can be traced to its source records and definition, and cost
  is labeled `API-equivalent estimate` rather than actual spend.
- Every discoverable implementation and supervisor group appears once in the
  topology with exact relationships or an explicit anomaly, and each operating
  light/action/conclusion drills into the records that justify it.
- A long-lived target with two missions shows one current mission and one
  predecessor history segment; its current issues, status, conclusions, and
  metrics contain no predecessor-only records.
- No dashboard-owned durable run, event, metric, or report ledger exists.

### Negative tests

- Reject a broken event/report integrity chain as trusted input and reject an
  aggregate that silently treats an unavailable source as zero.
- Reject a green completion or availability claim derived only from task
  terminality, passing tests, commits, reports, or missing no-op records.

### Completion evidence

Pending.

### Stop

Stop before rendering operator workspaces or mutating any supervision,
automation, report, or evolution owner.

---

## Block 5 — Codex task and App Server adapter

Status: `not-started`

### Objective

Provide a version-gated local Codex task/turn integration that can project live
work and support the exact bounded interactions required by later operations.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: connect dashboard project/run truth to live Codex
  task state and enable real task creation, continuation, streaming, approval,
  input, steering, and interruption.
- Potential capability loss or regression: protocol drift, replay mistakes,
  broad arbitrary method access, or an App Server outage could misroute work or
  make controls appear successful when they are not.
- Protected-capability effect: preserves Codex task authority, recipient
  identity, approval/input boundaries, thread-route gates, and fail-closed
  operation.
- Architecture and operating-model effect: adds one long-lived stdio App Server
  child/client behind the Python adapter and one ephemeral browser event stream;
  no App Server WebSocket is exposed.
- Tradeoff and source evidence: a version-specific adapter requires compatibility
  maintenance but is the official rich-client integration and avoids screen
  scraping or invented task state.

### Inputs and dependencies

- Accepted Block 1 runtime/API/event-channel foundation.
- Block 0 frozen installed CLI and official App Server contract.

### Required work

- Generate TypeScript/JSON schemas from the installed `codex app-server`, record
  CLI/schema version and content hash, and select the minimum supported methods
  from the official protocol. Commit generated compatibility artifacts only if
  their update/review workflow is documented and deterministic.
- Implement a subprocess client that invokes the exact resolved Codex binary by
  argument vector, performs `initialize`/`initialized`, assigns request IDs,
  correlates responses, consumes notifications, bounds buffers, redacts
  diagnostics, and cleanly tears down/restarts after failure.
- Support read methods needed here: `thread/list`, `thread/read`, live status,
  and current turn/items. Support mutation methods only behind internal typed
  capabilities: `thread/start`, `thread/resume`, `thread/fork` only if required
  by an accepted workflow, `turn/start`, `turn/steer`, `turn/interrupt`, and
  approval/user-input responses.
- Validate every inbound and outbound payload against the generated/handwritten
  narrowed schema, reject unknown method exposure, and feature-gate each method
  independently after handshake/probe.
- Correlate task cwd and explicit tracker/target identities to registered
  projects without inventing a binding when data is absent.
- Provide authenticated same-origin Server-Sent Events (or an equally narrow
  one-way browser stream proven simpler) for live task status/items, approval
  requests, input requests, connection state, and operation correlation. Use
  TanStack Query invalidation for durable source rereads; do not turn the stream
  into a durable event ledger.
- Expose only the narrowed task methods through `/api/v1` and the authenticated
  event stream. The browser cannot access raw App Server transport or method
  names, and neither the adapter nor frontend may substitute fixture responses
  when the primary process or negotiated method is unavailable.
- Implement disconnect, CLI-not-installed, incompatible-schema, task-not-found,
  idle/active/terminal, duplicate-response, stream-resume, and bounded-backoff
  states. All mutation capability becomes disabled on incompatibility while
  independent file-backed monitoring remains available.
- Add an Admin integration-health view with resolved CLI version, protocol
  status, supported feature matrix, last error, and restart action limited to
  the adapter child process.

### Scope and non-goals

- In scope: the exact App Server projection and interaction subset needed by
  this tracker.
- Not in scope: a general Codex client, remote WebSocket transport, plugin
  management, arbitrary tool invocation, arbitrary prompts, model settings UI,
  or automation mutation implemented outside owner-mediated tasks.
- Do not expose raw JSON-RPC/App Server method names or payload editors to the
  browser.

### Deliverables and recorded state

- Versioned schema generation command/artifacts, Python App Server client,
  capability matrix, task APIs/event stream, frontend integration health,
  fixtures/fake server, and focused tests.

### Resource and economy contract

Maintain one App Server child per dashboard process, page `thread/list`, and
request full task content only for visible/operation-bound tasks. Cap retained
ephemeral items and reconnect backoff; invalidate durable projections by exact
task/source identifiers. Never poll every historical task body.

### QA and independent review

- Use a deterministic fake protocol server for handshake, interleaving,
  malformed JSON, unknown notifications, timeouts, duplicate IDs, approval/
  input, reconnect, bounded buffers, and unsupported methods.
- Run a focused live smoke against the installed CLI for list/read and one
  disposable bounded task/turn interaction that does not mutate a project.
- Independently review protocol narrowing, redaction, recipient/cwd binding,
  failure degradation, and the absence of remote/general client exposure.

### Acceptance

- Current tasks list with exact IDs, cwd, status, turns/items, and source
  freshness where the installed protocol supports them.
- Supported live interaction works through validated messages and unsupported
  methods are visibly disabled with an exact reason.
- Killing/upgrading/malforming the App Server cannot corrupt file-backed
  monitoring or cause an operation to be labeled applied.
- Approvals and input requests are attributable to one task/turn/item and cannot
  be answered after their source fingerprint is stale.

### Negative tests

- Reject an unknown App Server method, malformed response, mismatched request
  ID, unregistered cwd operation, stale approval/input response, or attempt to
  expose the child transport beyond loopback/server process boundaries.
- Reject any fallback that guesses task status or uses UI scraping when the
  protocol is unavailable.

### Completion evidence

Pending.

### Stop

Stop before exposing workflow-start or lifecycle mutation controls.

---

## Block 6 — Cross-project factory floor

Status: `not-started`

### Objective

Deliver the minimal default factory floor that pairs implementations with their
supervisors and makes operating state, current work, issues, actions,
conclusions, source health, and cross-project metrics immediately legible.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: replace fragmented shell/task/file inspection with
  one trustworthy floor view of what is running, who is supervising what,
  whether it is on track, and what just happened across projects.
- Potential capability loss or regression: an overloaded dashboard, synthetic
  health score, stale polling, or chart-first design could obscure the exact
  issue and source action.
- Protected-capability effect: preserves exact statuses, attention precedence,
  source freshness, limitations, and drill-down to canonical records.
- Architecture and operating-model effect: establishes the primary composed
  projection and frontend information hierarchy; no new canonical data owner is
  added.
- Tradeoff and source evidence: limiting the default surface sacrifices
  simultaneous detail but follows the reference task's simple, clean,
  progressive-disclosure posture and the direct monitoring objective.

### Inputs and dependencies

- Accepted Blocks 3, 4, and 5 read models.
- Block 1 application shell and Block 2 catalog.

### Required work

- Implement `Factory Floor` with exactly four primary regions: the
  implementation/supervisor floor, `Needs attention`, `Latest conclusions and
  accepted outcomes`, and a compact metric/freshness strip.
- The floor groups running and recently active implementation/mission rows by
  project. Each row shows exact implementation task and tracker/Block or mission,
  lifecycle/last activity, supervisor group and role summary, supervised target,
  live/idle/paused posture, last check/action, next scheduled check when known,
  open issue/decision/transition counts, latest current conclusion, source
  freshness, and one detail/inspector action.
- Render the rule-derived red/amber/green/neutral operating light with text,
  icon, triggered reason, and observed time. Green means `on track under current
  recorded checks`, never accepted/complete; paused, completed, unmonitored,
  unavailable, and unknown use distinct neutral labels. Color is never the only
  signal.
- Include unmonitored implementations, orphaned/duplicate/misbound supervisors,
  and supervisor groups whose target cannot be resolved as first-class floor
  rows or attention items. Represent disagreements between task, tracker,
  automation, and ledger sources explicitly rather than choosing a winner.
- `Needs attention` renders the transparent precedence feed from Block 4 with
  reason, severity, age, owner/source, safe-frontier or unavailable posture,
  and drill-down; add project/status/severity filters without changing ranking
  semantics.
- `Latest conclusions and accepted outcomes` distinguishes the supervisor/
  reviewer conclusion stream from accepted implementation outcomes. It shows
  role/author, target, disposition, evidence/source revision, next action,
  superseded/current posture, accepted Block/run/report source where applicable,
  time, later staleness, and retained open work. Do not treat watcher activity
  or task completion as a conclusion or acceptance criterion.
- The metric strip shows a bounded set: active projects/tasks/runs, exact Block
  status counts, active/unmonitored implementations, active/degraded/orphaned
  supervisor groups, red/amber/green/neutral floor counts, open incidents/
  decisions/transitions, supervisor checks/actions/conclusions and review trend,
  availability where covered, and API-equivalent estimated cost where present.
  Show only a bounded subset by default; every item states period, denominator/
  coverage, and unavailable state.
- Add global project/time filtering, source-freshness indicator, refresh,
  keyboard navigation, compact mobile cards, bounded desktop rows, loading/
  empty/partial/error/stale states, and source links.
- Use TanStack Query for read/poll/invalidation, Jotai only for ephemeral filters
  and inspector state, Zod at the API edge, and Recharts only where a trend is
  materially clearer than a number/table.
- Populate every Factory Floor region from live Block 3–5 HTTP projections or
  one server-composed endpoint over them. Runtime sample rows and hard-coded
  operational state are forbidden; independent partial outages remain visible
  in the affected region without suppressing healthy sources.

### Scope and non-goals

- In scope: the default cross-project overview and transparent attention
  workflow.
- Not in scope: detailed project/run/tracker/report pages, mutations, custom
  layouts, notification delivery, or generalized analytics.
- Do not add a single health/productivity score, decorative charts, or controls
  whose effects are not implemented.

### Deliverables and recorded state

- Factory Floor route, implementation/supervisor row and inspector, operating-
  light/conclusion components, composed query contracts, reusable bounded
  status/freshness/attention components, accessible chart summaries, and
  focused UI/browser tests.

### Resource and economy contract

Fetch one aggregate envelope plus visible detail pages; poll active summaries
at the accepted bounded interval and back off for hidden/inactive tabs. Historical
records load on drill-down. Reuse server fingerprints and query invalidation;
do not trigger deep source validation on every render.

### QA and independent review

- Unit/component-test topology, every light rule and neutral state, conclusion
  classification/currentness, attention ordering, source disagreement, exact
  status counts, coverage, time-zone/range, estimated-cost label, partial
  failure, stale data, and filter behavior.
- Browser-test populated, empty, loading, partial-source, error, dark-mode,
  keyboard, and responsive layouts at 390×844, 768×1024, and 1440×900.
- Independent product review must determine whether an operator can answer the
  five Section 1 questions from the overview or one obvious drill-down, without
  relying on implementation knowledge.

### Acceptance

- With at least three live projects, the operator can identify every running
  implementation and supervisor group, what each supervisor watches, current
  Block/checkpoint, operating light/reason, last and next supervisory activity,
  current issues, latest conclusion, highest-priority attention item, recent
  accepted outcome, and data freshness within the maintained view.
- Each card/metric reaches its exact source-bearing detail route and retains
  source coverage/limitations.
- No viewport has horizontal page overflow, clipped primary actions, keyboard
  traps, unreadable dark mode, or a false empty/healthy state during partial
  failure.

### Negative tests

- Reject a critical item hidden by filters/default sorting without a visible
  filtered-count indication, a metric with no period/coverage, or a cost value
  labeled as spend.
- Reject green when required sources are stale/unavailable, an issue rule is
  active, or a supervisor/target binding is invalid; reject any light with no
  textual reason and source timestamp.
- Reject a mechanical watcher wake/check or terminal task labeled as a semantic
  conclusion.
- Reject any accepted-history entry established only by a terminal task, commit,
  test, or generated report.

### Completion evidence

Pending.

### Stop

Stop before adding project/run, tracker, report, or admin detail functionality.

---

## Block 7 — Project and run workspaces

Status: `not-started`

### Objective

Provide source-grounded project, run, and task drill-downs that explain what is
happening, what happened, why attention is needed, and which owner holds the
next decision.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make one project's current and historical work
  reviewable without mixing independent tasks, runs, or authority roles.
- Potential capability loss or regression: merging task, tracker, and
  supervision state into one synthetic lifecycle could hide disagreement,
  successor gaps, or retained incidents.
- Protected-capability effect: preserves exact task/run/tracker identities,
  checkpoint and lifecycle evidence, decision/safe-frontier posture, successor
  continuity, role boundaries, and historical records.
- Architecture and operating-model effect: adds route-owned detail projections
  and contextual inspectors over existing read models; owners remain unchanged.
- Tradeoff and source evidence: separate task/run/source panels take more space
  than one status badge but are necessary to explain discrepancies and satisfy
  evidence-bound supervision.

### Inputs and dependencies

- Accepted Block 6 navigation, summaries, and read projections.

### Required work

- Implement a Projects index with label/root, source health, active work,
  attention count, tracker/report counts, last accepted outcome/activity, and
  archived toggle. Keep missing data distinct from zero.
- Implement Project Overview with current work, tracker inventory, recent
  outcomes, metric snapshot, source/integration health, and history. Add
  contextual tabs/routes for `Overview`, `Work`, `Trackers`, `Reports`, and
  `Sources`, not duplicate primary navigation.
- Implement a run detail workspace with bounded sections for mission/binding,
  current checkpoint/Block, lifecycle and completion posture, event timeline,
  incidents/reviews, decisions/safe frontier, successor transitions,
  roles/routes, schedules/automations, reports, source integrity, and retained
  open work.
- For a long-lived target, add a mission-history selector/timeline keyed by
  exact mission root and policy version. Default to the active mission; show
  predecessor completion/supersession, conclusions, metrics, and events only
  within that historical segment, with an explicit succession boundary and no
  carry-forward into current state.
- Add a supervisor-group inspector/detail route that shows the exact supervised
  implementation/mission and target, group/policy identity, every role task and
  responsibility, live task posture, automation cadence/enabled state, last/
  next check, recent reads/checks/actions/steers/escalations, latest semantic
  conclusion per authorized role, current incidents/decisions/transitions,
  route-gate state, source freshness, and binding anomalies.
- Add derived operating history for the run/supervisor pairing: traffic-light
  transitions with triggering records, actions taken, later resolution, and
  reviewer conclusions. Preserve gaps as unknown and keep this timeline
  explicitly derived from canonical history.
- Implement a task detail workspace with exact App Server status, cwd/project
  association, turn/item timeline, pending approvals/input, linked tracker/run,
  and disconnect/incompatible states. Render tool/command/output items in
  bounded collapsed summaries; do not expose secrets or turn it into a general
  transcript archive.
- Make event timelines filterable by source kind/severity/Block/role and retain
  stable IDs/anchors. Preserve superseded, rejected, and pre-correction history
  with clear posture rather than removing it.
- Render policy/role/automation data as read-only source views with direct
  mismatch/unavailable explanations; administrative controls arrive in Blocks
  10–12.
- Add breadcrumbs/deep links from every Factory Floor item and back links that
  preserve project/time filters.

### Scope and non-goals

- In scope: project, run, and task observation, evidence navigation, and source
  disagreement display.
- Not in scope: tracker deep review, full report analytics, task/supervision
  mutation, raw Gmail content, or an unrestricted event query builder.
- Do not combine separate tasks/runs because they share cwd or label; preserve
  canonical IDs and explicit associations.

### Deliverables and recorded state

- Projects index/detail, run detail, task detail, supervisor-group inspector,
  operating/action/conclusion history, timeline/evidence/source inspectors,
  routing/filter state, and focused component/browser tests.

### Resource and economy contract

Load summary rows first, then page timeline/items for the selected run/task.
Default to the newest bounded window with exact total/continuation information.
Fetch raw/full record bodies only on explicit expansion; never preload all
historical App Server turns or ledger events across projects.

### QA and independent review

- Test multiple tasks per project, task without run, run without live task,
  successor task, source disagreement, paginated history, invalid record,
  superseded incident, open decision, partial automation state, and disconnected
  App Server.
- Test a trackerless main-thread mission and two sequential missions on one
  target, including active default selection, predecessor deep link, exact
  succession evidence, and no cross-mission issue/conclusion/metric leakage.
- Browser-test deep links, preserved filters, keyboard timeline/inspectors,
  bounded long IDs/text/commands, responsive tab behavior, and source failure.
- Independent semantic review checks the latest live artifacts and verifies
  task/run/tracker identities and lifecycle claims against exact source records.

### Acceptance

- The operator can select any registered project and trace current or historical
  work through task, run, tracker, event, attention, and report identities.
- An active run's checkpoint, incidents, decisions, transitions, roles, and
  automation posture match current canonical records, including disagreements
  and missing bindings.
- A supervisor group can be traced role by role to its exact target, cadence,
  last/next check, recent actions, current issues, and latest authorized
  conclusions; derived red/amber/green transitions link to their triggers and
  resolutions.
- Long timelines and task items remain performant, paged, keyboard navigable,
  and visually bounded at maintained viewports.

### Negative tests

- Reject a project history that merges distinct thread/run IDs or hides
  rejected/superseded records.
- Reject a lifecycle/completion badge inferred from the last event timestamp or
  App Server terminal state when its canonical record is absent.

### Completion evidence

Pending.

### Stop

Stop before adding tracker review, report analytics, or operational controls.

---

## Block 8 — Tracker review and progress workspace

Status: `not-started`

### Objective

Make each implementation tracker reviewable as an implementation contract and
show exact source-backed progress without providing a second editor or acceptance
path.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let an operator assess readiness, capability
  coverage, dependency order, Block contract quality, current progress, and
  evidence from one bounded workspace.
- Potential capability loss or regression: checklist theater, a synthetic
  progress bar, or lossy Markdown rendering could make an invalid/stale tracker
  look implementation-ready or complete.
- Protected-capability effect: preserves full-profile capability framing,
  dependency/status exactness, explicit non-goals/stops, completion evidence,
  verifier authority, Git currentness, and review-versus-acceptance separation.
- Architecture and operating-model effect: adds a maintained visual projection
  and ephemeral review navigation over the Block 3 read model; authoring remains
  with its skill/task owner.
- Tradeoff and source evidence: a structured workspace omits free-form inline
  editing but gives safer cross-project review and follows the direct request
  plus authoring skill contract.

### Inputs and dependencies

- Accepted Block 3 tracker/Git projection and Block 6 shell/filter patterns.

### Required work

- Implement a Trackers index with project, tracker status, Block counts by exact
  status, verifier profile/result, current/eligible Block, mapped active run,
  Git dirty/stale/untracked posture, last change, and attention reason.
- Implement tracker detail with a concise Overview: governing objective,
  mission and target-product capability frame, protected capabilities,
  architecture/owner/source map, scope/non-goals, execution contract, and final
  completion definition where present. Preserve links to exact Markdown anchors.
- Render required order as an accessible dependency list and bounded graph only
  when it materially clarifies branching. Mark eligible, active, accepted,
  open-item, blocked, and descendant-blocked nodes without inventing percentage
  weights.
- Render a Block list and selected Block inspector containing exact status,
  objective, capability delta, inputs/dependencies, required work, scope/non-
  goals, deliverables, resource/economy, QA/review, acceptance, negative tests,
  completion evidence, and Stop. Missing/unknown sections remain explicit.
- Add evidence/currentness panels for tracker content hash, Git revision/dirty/
  upstream posture, verifier version/profile/diagnostics, mapped run binding and
  tracker hash, accepted candidate/freeze where recorded, source changes after
  evidence, retained open work, and outcome reconciliation posture.
- Provide `Review readiness` as deterministic facts, not a second validator:
  current verifier result, unresolved diagnostics, source currentness,
  dependency eligibility, completion-evidence presence, and active-run binding.
  Link to the maintained verifier output and label any heuristic as derived.
- Support compare-to-working-tree/last-commit textual diff metadata and an
  exact local-file/open-in-repository affordance where the host permits it;
  sanitize and bound rendered Markdown. Do not implement editing.
- Add print/share-within-local-session layout for a review packet without
  creating a new canonical artifact or external share link.

### Scope and non-goals

- In scope: tracker list/detail, dependency and Block inspection, progress,
  evidence, verification, Git currentness, mapped run posture, and local review
  packet rendering.
- Not in scope: inline editing, comments/assignments, tracker acceptance,
  status mutation, generalized Markdown CMS behavior, or workflow start controls
  before Block 11.
- Do not hide full/core profile differences or reinterpret verifier errors in
  frontend-only doctrine.

### Deliverables and recorded state

- Trackers index/detail routes, dependency/Block/evidence/currentness components,
  sanitized renderer, print layout, query/filter state, and focused tests.

### Resource and economy contract

List responses carry summaries only. Fetch/parse the selected tracker once per
content/verifier fingerprint, lazy-load diff and long completion evidence, and
render only the selected Block's full contract. Do not run verifier processes
from the browser or on every selection rerender.

### QA and independent review

- Component-test exact status counts, branching dependencies, full/core
  posture, diagnostics, missing sections, dirty/stale bindings, long evidence,
  safe Markdown, and print layout.
- Browser-test keyboard Block selection, graph/list equivalence, source anchors,
  filters, narrow viewports, dark mode, and partial/malformed tracker behavior.
- An independent tracker reviewer uses the page on one full-profile and one
  inherited core-profile tracker, compares it with the exact Markdown/verifier,
  and reports any omitted or misleading contract fact.

### Acceptance

- A reviewer can determine the requested capability, owner/dependency design,
  next eligible Block, exact progress statuses, acceptance obligations,
  verification posture, currentness, and mapped evidence without opening the
  raw file; raw source remains one action away.
- The workspace faithfully distinguishes verifier-valid full, verifier-valid
  inherited core, invalid, stale, dirty, untracked, and partially parsed
  trackers.
- No UI control can edit or accept a tracker in this Block.

### Negative tests

- Reject a progress visualization that counts `completed-with-open-items` as
  accepted, hides a failing verifier, or ignores a changed-after-binding hash.
- Reject rendered Markdown containing script/event-handler execution, path
  traversal links, or content outside the selected registered tracker.

### Completion evidence

Pending.

### Stop

Stop before starting authoring/review/implementation tasks or changing tracker
state.

---

## Block 9 — Metrics and report history workspace

Status: `not-started`

### Objective

Provide bounded cross-project and per-project metric analysis plus verified
report/evolution artifact review with exact definitions, coverage, limitations,
and source drill-down.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make Factory throughput, reliability, review,
  incident, availability, resource, and learning history comparable and
  explainable across projects and periods.
- Potential capability loss or regression: mismatched definitions, missing
  denominators, partial histories, or attractive charts could turn derived
  estimates into unsupported performance or billing claims.
- Protected-capability effect: preserves verified report contracts, canonical
  record traceability, source limitations, estimate labels, and report-as-
  projection rather than authority.
- Architecture and operating-model effect: adds frontend analytic/report views
  over Block 4 normalized projections; it does not add telemetry collection or
  recompute cognitive reports.
- Tradeoff and source evidence: a small supported metric set offers less ad hoc
  analysis but remains maintainable and faithful to the repository's
  demonstrated report fields and the requested cross-project metrics.

### Inputs and dependencies

- Accepted Block 4 metric/report projections and Block 6 UI conventions.

### Required work

- Implement Metrics with project/run/time-range/time-zone filters and four
  bounded groups: `Delivery` (Block/status/activity throughput), `Reliability`
  (availability coverage, incidents, resolution latency, decisions/transitions),
  `Review` (supervisor checks/actions/conclusions, reviews/corrections by
  recorded role/category, issue recurrence and resolution where supported), and
  `Resources` (estimated tokens/API-equivalent cost, model/reasoning activity,
  coverage).
- Include bounded factory-floor history: concurrent implementations and
  supervisor groups, monitored versus unmonitored time, time in rule-derived
  red/amber/green/neutral posture, late/missed recorded checks, issue opens/
  resolutions, and conclusion counts. Show only dimensions the canonical
  coverage can support and do not infer an unrecorded no-op wake.
- Present headline values with definitions, period, denominator, coverage,
  observed/generated time, estimated/measured posture, and change only when two
  comparable windows use the same contract. Use charts only for trends or
  comparisons that a table cannot communicate as clearly.
- Support per-project and aggregate comparisons without ranking projects by a
  synthetic productivity score. Make different coverage/contracts incomparable
  rather than coercing them.
- Add source drill-down from a chart point/table row to the underlying report
  metric and, where available, canonical event/incident/review records.
- Implement Reports inventory/detail for weekly, terminal, and Factory-evolution
  bundles: status/type/period/project/run, verifier/integrity posture, manifest,
  limitations, metric summary, Markdown preview, safe same-origin PDF preview/
  download, JSON views, evaluation/disposition, and exact content roots.
- Allow bounded comparison of two compatible verified reports, showing metric
  definition/version and coverage changes before numeric deltas. Keep invalid,
  superseded, diagnostic, and partial reports in history with explicit posture.
- Provide accessible data tables/summaries for all charts and browser print
  behavior for an operator review; do not generate a new report artifact in
  this Block.

### Scope and non-goals

- In scope: current verified metrics, historical comparison, report/evolution
  artifact preview/download, definitions, limitations, and drill-down.
- Not in scope: billing API integration, new telemetry, generalized BI/query
  builder, project ranking, report generation, cognitive evaluation, or
  adoption action.
- Do not treat report verification, `promote` disposition, or favorable trend as
  current outcome acceptance or automatic capability adoption.

### Deliverables and recorded state

- Metrics and Reports routes, supported charts/tables/definitions, report
  previews and comparison, safe artifact-serving endpoints, and focused tests.

### Resource and economy contract

Query pre-normalized verified metrics, lazy-load artifact bodies/previews, and
cap chart point density with transparent aggregation. Compare at most two
reports at once. Never regenerate PDFs/reports or read all raw ledger events for
ordinary chart interaction; widen only on explicit source drill-down.

### QA and independent review

- Test incompatible periods/contracts, missing coverage, unavailable versus
  zero, median/P90 units, paused availability, estimated resource/cost labels,
  invalid/superseded reports, safe artifact paths, PDF/Markdown/JSON fallback,
  and accessible chart/table equivalence.
- Browser-test filters, comparison, drill-down, print, keyboard, dark mode,
  responsive charts/tables, long limitations, and partial artifacts.
- Independent semantic review samples displayed aggregates against exact
  report JSON/manifests and underlying canonical records, and rejects any
  unsupported performance, billing, or outcome claim.

### Acceptance

- The operator can compare supported delivery/reliability/review/resource
  history across at least three projects and explain each number's definition,
  period, coverage, source, and limitation.
- A verified weekly, terminal, and evolution artifact can be inspected and
  downloaded safely; invalid/partial artifacts are never presented as verified.
- Every chart has an accessible table/summary and no metric silently combines
  incompatible definitions or missing sources.

### Negative tests

- Reject a cross-project delta with incompatible metric versions/coverage, an
  unavailable value rendered as zero, or an API-equivalent estimate labeled as
  actual cost.
- Reject artifact serving outside a validated report bundle or rendering that
  executes active report content.

### Completion evidence

Pending.

### Stop

Stop before adding report generation, evolution adoption, or lifecycle
administration controls.

---

## Block 10 — Gated administrative operation framework

Status: `not-started`

### Objective

Establish one typed, fail-closed operation path that previews authority and
consequences, obtains exact confirmation, invokes only an allowlisted owner, and
proves the resulting canonical postcondition.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: turn the dashboard from a read-only monitor into a
  trustworthy administrative surface without granting it arbitrary mutation
  authority.
- Potential capability loss or regression: generic endpoints, stale previews,
  replay, cross-target confusion, or HTTP-success-as-outcome could cause
  unintended operations or false success.
- Protected-capability effect: preserves direct authority, exact target and
  owner boundaries, route/lifecycle/decision gates, single writers, source
  currentness, and evidence-based outcomes.
- Architecture and operating-model effect: adds a narrow operation registry,
  ephemeral request state, and postcondition verifier in the Python adapter;
  canonical effects remain with App Server, skills, automations, and ledgers.
- Tradeoff and source evidence: preview/confirmation/postcondition adds operator
  steps and latency but is required for controls with real consequences under
  the direct request and existing Factory safety contracts.

### Inputs and dependencies

- Accepted Block 2 project/root boundaries.
- Accepted Block 4 canonical-source rereads and gates.
- Accepted Block 5 typed App Server interaction.

### Required work

- Define a closed operation registry. Each operation declares: stable type;
  exact target kind/ID/project; input schema; source fingerprint/preconditions;
  owner; authority/gates; ordinary and failure consequences; confirmation
  class; idempotency/replay rule; requested-state evidence; canonical
  postcondition; timeout/unverified behavior; and supported/unavailable reason.
- Implement `preview` to resolve current sources and return a short human-
  readable effect/diff, owner, recipient, gate, risk/confirmation text,
  expected postcondition, limitations, and an expiring fingerprint-bound token.
  Preview performs no mutation.
- Implement `execute` to require same-origin, launch nonce, exact preview token,
  unchanged source fingerprint, explicit typed confirmation, one registered
  operation, and canonical target authorization. Reject free-form commands,
  paths, App Server methods, recipients, and extra fields.
- Dispatch only to the registry-named maintained owner through its import,
  exact argument-vector helper, version-gated App Server method, or automation
  owner. The browser never invokes primary functionality directly, and the
  HTTP handler may not reproduce a domain mutation owned elsewhere.
- Implement operation-specific correlation and ephemeral state:
  `previewed`, `confirmed`, `requested`, `awaiting-approval`, `awaiting-input`,
  `verifying`, `applied`, `failed`, `unverified`, or `cancelled`. Do not add a
  durable dashboard operation ledger; on restart reconstruct supported results
  from task/turn/ledger/automation/catalog owners or label prior ephemeral state
  unavailable.
- Require `thread-route-gate` before every cross-thread send, with exact
  recipient, maintained purpose, source record, and required action. Bind the
  allowed result to the preview token; any changed recipient/action/source or
  unavailable gate requires a new preview and fails closed.
- Separate operation postconditions. For example, `task-started` requires the
  exact new task/turn; `automation-paused` requires changed automation state and
  required lifecycle evidence; `policy-adjusted` requires the next validated
  policy version and reconciled automation state. Never map these to generic
  `success` or to final implementation outcome.
- Implement cancellation only before an owner mutation has been requested.
  After request, show the true owner state and provide only a separately
  authorized compensating operation where one exists.
- Add a reusable confirmation drawer/dialog, operation activity panel, approval/
  input surfaces, disabled-reason component, stale-preview recovery, and exact
  links to resulting task/source records.
- Redact secrets and minimize prompt/evidence previews; log operational
  diagnostics without request bodies that may contain project content.

### Scope and non-goals

- In scope: generic safety/lifecycle infrastructure strictly needed by the
  explicit operations in Blocks 11–24.
- Not in scope: arbitrary operations, generic workflow DSL, durable job queue,
  user/role authorization system, shell console, implicit retry of mutations,
  or the domain workflows themselves.
- Do not build an undo system; expose a compensating owner operation only when
  that operation is independently specified and gated.

### Deliverables and recorded state

- Closed operation registry/contracts, preview/execute/status endpoints,
  gate/postcondition adapters, ephemeral correlation state, confirmation and
  activity UI, approval/input integration, and adversarial tests.

### Resource and economy contract

Resolve one target and only its named sources per preview; cache nothing beyond
the expiring fingerprint token. Execute exactly once per token and never retry a
mutation automatically. Poll only the operation's named postcondition until its
bounded timeout, then retain `unverified` and offer a source refresh rather than
widening or repeating.

### QA and independent review

- Test origin/nonce, token expiry, fingerprint staleness, replay, duplicate
  submit, cancel boundary, wrong target/project/recipient, gate deny/unavailable,
  approval/input staleness, owner timeout/crash, partial effect, failed
  postcondition, restart, redaction, and schema extra fields.
- Prove each registered operation cannot select arbitrary command, path, App
  Server method, task recipient, or postcondition.
- Independent safety/authority review maps every registry entry to the Block 0
  contract and rejects any generic or duplicate writer.

### Acceptance

- A deterministic test owner demonstrates preview, confirmation, request,
  canonical verification, stale rejection, failure, unverified timeout, and
  restart behavior without a second durable ledger.
- Cross-thread execution cannot proceed without a current allowed route gate
  bound to the exact action.
- UI language distinguishes request acceptance, operation postcondition, and
  eventual workflow/outcome completion.

### Negative tests

- Reject a changed target/input/recipient after preview, a replayed token, an
  unknown operation, an extra shell-shaped field, or a `2xx` response with no
  canonical postcondition.
- Reject cancellation that claims to undo an already requested owner mutation.

### Completion evidence

Pending.

### Stop

Stop before registering tracker/task/supervision/report/lifecycle operations.

---

## Block 11 — Author, implement, supervise, and task-control workflows

Status: `not-started`

### Objective

Enable the operator to start and control the ordinary Software Factory work
loop—tracker authoring/review, bounded Block implementation, supervision
attachment, and exact task continuation—through the maintained skill owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator move from observed project/tracker
  state to real, bounded Factory work without leaving the dashboard.
- Potential capability loss or regression: a weak task template or wrong
  recipient/root/Block could broaden scope, bypass an owner, duplicate active
  work, or mutate when the operator requested review only.
- Protected-capability effect: preserves skill ownership, current tracker/Git
  binding, exact Block/range stops, independent review posture, task recipient
  identity, and Git durability expectations.
- Architecture and operating-model effect: registers explicit owner-mediated
  task workflows in Block 10; the dashboard initiates work but does not execute
  implementation or author tracker content itself.
- Tradeoff and source evidence: task-mediated operations are asynchronous and
  may require approval/input, but they reuse the requested Factory skills and
  official task owner rather than adding an orchestration engine.

### Inputs and dependencies

- Accepted Block 8 tracker readiness/progress workspace.
- Accepted Block 10 operation framework.
- Current accepted author, implement, and supervise skill contracts from Block
  0.

### Required work

- Register `Author tracker` for one registered repository and explicit
  objective/source set. Preview the skill, cwd, direct objective, source
  identities, non-goals, and expected artifact/task outcome. Start a Codex task
  whose first turn explicitly invokes `$author-implementation-trackers` and
  preserves the operator's direct wording.
- Register `Review tracker` as a read-only quality-check task with exact path,
  content hash, verifier profile/result, review scope, and no edit authorization.
  Provide a separately previewed `Revise tracker` operation only when the
  operator explicitly authorizes edits and exact scope.
- Register `Implement Blocks` with one current tracker, exact Block or contiguous
  range, repository root/HEAD/worktree posture, eligibility/dependencies,
  supervision choice, and expected stop. Invoke `$implement-tracker-blocks` in
  the created/selected task. Fail closed on invalid selection, stale content,
  unmet dependency, conflicting active owner, or unsupported profile unless the
  maintained skill contract supplies an explicit safe path.
- Register `Attach supervision` to a selected implementation/mission task using
  `$supervise-tracker-runs`, exact target/tracker/Block range/mission authority,
  current role/automation capabilities, and the skill's boot/bind protocol.
  Mark it attached only after canonical policy/binding/role/automation state is
  observed; preserve partial setup as attention.
- Register exact task interactions: `Continue idle task` via a new turn,
  `Steer active turn` through the supported steer method, `Respond to input`,
  `Respond to approval`, and `Interrupt current turn`. Each preview shows task,
  turn/item, supplied text/choice, and scope. Interruption never claims semantic
  pause/stop or completed work.
- Use route gates for any operation that sends to a maintained task other than
  the task whose operator-owned turn is being continued. Do not routine-cross-
  post status or evidence to unrelated tasks.
- Show operation/task progress in tracker and project workspaces: created task,
  requested/active turn, current items, pending approval/input, linked run,
  source postcondition, and eventual tracker/run/outcome state as separate facts.
- Disable tracker-authoring supervision controls unless Block 0/current evidence
  proves that planned program has been implemented and accepted; surface the
  exact prerequisite instead of simulating it.

### Scope and non-goals

- In scope: explicit Factory task templates and task controls for ordinary
  author/review/implement/supervise work.
- Not in scope: inline code/Markdown editing, choosing implementation decisions
  on behalf of the task, automatic Block acceptance, generic prompt composer,
  auto-commit/push, or planned adaptive decision/evolution behavior.
- Do not start a user-owned task merely to display data; task creation requires
  explicit operator confirmation.

### Deliverables and recorded state

- Closed workflow operation definitions, typed prompt/input builders, currentness
  and conflict gates, tracker/project/task UI controls, task/result links, and
  focused live/fake integration tests.

### Resource and economy contract

Create at most one task per confirmed operation and do not auto-retry creation/
turn start. Reuse an exact eligible idle task only when the operator selected it
and its mission/currentness match. Build prompts from bounded required fields,
not full reports/event histories; owners can fetch exact referenced sources.

### QA and independent review

- Test author versus read-only review versus revise authority, Block/range
  eligibility, dirty/stale tracker, unmet dependency, duplicate active task,
  wrong cwd, route deny, partial supervision attach, pending approval/input,
  task disconnect, steer-versus-continue, interrupt semantics, and unavailable
  planned capability.
- Run live end-to-end smoke in a disposable registered Git fixture: author a
  small tracker, independently review it, start one bounded implementation task,
  attach supervision if current capabilities support it, and observe exact task/
  tracker/run sources without accepting implementation merely because it ran.
- Independent review inspects the exact generated turns and confirms they invoke
  the named skill with the selected scope and no hidden authority expansion.

### Acceptance

- From a project or tracker page, an operator can start each available ordinary
  Factory workflow and reach the exact new task/run/source record.
- Review-only work cannot mutate; implementation cannot start on an ineligible
  or stale Block; supervision cannot appear attached until all required owner
  state exists.
- Continue, steer, approval/input, and interrupt controls have the exact live
  App Server consequence and remain semantically distinct from lifecycle state.
- The UI reports `task/turn started` separately from `Block accepted` and
  `outcome verified`.

### Negative tests

- Reject a read-only tracker review prompt that authorizes edits, a noncontiguous
  or dependency-ineligible implementation range, a second active owner without
  explicit supported handoff, or a task started in an unregistered cwd.
- Reject an interrupted turn presented as paused supervision, stopped mission,
  or accepted work.

### Completion evidence

Pending.

### Stop

Stop before policy/schedule adjustment, report/evolution workflow, successor
administration, or semantic lifecycle controls.

---

## Block 12 — On-demand mechanical supervision checks

Status: `not-started`

### Objective

Let the operator request one immediate mechanical supervision check and verify
the resulting canonical check without duplicating active work or granting the
watcher semantic authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: provide a consequence-bearing `Check now` control
  whose result is one exact new watcher check for the selected target.
- Potential capability loss or regression: duplicate wakes, wrong-target
  routing, or treating a task wake as a completed check could distort cadence
  and supervisor health.
- Protected-capability effect: preserves the watcher as mechanical gate,
  current route-gate evidence, exact target binding, cadence ownership, and the
  separation between mechanical activity and semantic conclusion.
- Architecture and operating-model effect: registers one watcher-owned
  operation and postcondition in the existing Block 10 framework; it adds no
  scheduler or alternative check ledger.
- Tradeoff and source evidence: an on-demand check may consume one extra bounded
  wake, so duplicate/active checks fail closed; the direct Factory-floor request
  and maintained watcher contract justify this narrow operator action.

### Inputs and dependencies

- Accepted Block 7 run/task workspaces.
- Accepted Blocks 10 and 11 operation/task owners.
- Current supported/unavailable feature matrix from Block 0.

### Required work

- Register `Check now` only through the current watcher/automation owner and
  only when it can target one exact implementation/run without duplicating an
  active check. Preview target, watcher role, maintained purpose, cadence/last
  check, route gate, and expected new check record; a task wake/turn alone is not
  a completed check.
- Display requested, awakened, check-recorded, duplicate-active, denied,
  timed-out, and unverified states separately in the run/floor inspector.
- After the wake, re-read only the selected target's canonical ledger and mark
  the operation applied only when a newer check record matches the target,
  route purpose, and preview fingerprint.

### Scope and non-goals

- In scope: one current watcher check request and its exact postcondition.
- Not in scope: semantic review, policy/cadence change, binding repair,
  pause/resume, reports, evolution, continuity, or terminal lifecycle.
- Do not infer a no-intervention conclusion or target health from wake/task
  success alone.

### Deliverables and recorded state

- `Check now` operation entry, preview/postcondition contract, floor/run control,
  progress states, and focused integration tests.

### Resource and economy contract

Touch one target and one watcher only. Reuse the current last-check fingerprint,
issue at most one wake per confirmed operation, never retry automatically, and
poll only for the named newer check until the bounded timeout. Stop at
`unverified` rather than waking again.

### QA and independent review

- Test duplicate/active `Check now`, wrong target/watcher/purpose, route denial,
  stale preview, missing watcher/automation, wake without check record, timeout,
  restart, and newer unrelated event.
- Run live non-destructive status and preview checks on a current supervised run;
  run mutation end to end only in the disposable validation run or with exact
  direct authority for a real target.
- Independent authority review checks the control against the current watcher
  and route-gate contract and verifies that no semantic claim is manufactured.

### Acceptance

- From one supervisor row the operator can preview and request an available
  immediate check, follow its exact watcher activity, and see a matching newer
  canonical check appear in current state/history.
- A missing, duplicate, denied, timed-out, or unmatched check remains disabled,
  failed, or unverified with its exact reason.
- The dashboard never writes the supervision ledger or labels the watcher wake
  itself as a semantic conclusion.

### Negative tests

- Reject `check applied` when only a task turn/wake exists, the check predates
  the preview, or its target/purpose differs.
- Reject a mechanical check rendered as semantic approval, implementation
  acceptance, or green outcome completion.

### Completion evidence

Pending.

### Stop

Stop before registering semantic review or any policy, binding, lifecycle,
continuity, report, or evolution operation.

---

## Block 13 — Semantic supervision review requests

Status: `not-started`

### Objective

Let the operator request one evidence-bound checkpoint, meta, or issue review
from the exact semantic owner and distinguish the request from its eventual
current conclusion.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: provide targeted semantic review requests and make
  their evidence, owner, progress, conclusion, and currentness visible.
- Potential capability loss or regression: routing a request to the wrong role,
  omitting the candidate/delta, or equating request delivery with a conclusion
  could bypass independent review and misstate Factory state.
- Protected-capability effect: preserves mechanical-versus-semantic separation,
  reviewer role ownership, route gates, exact candidate/source binding,
  superseded history, and conclusion currentness.
- Architecture and operating-model effect: adds three closed reviewer-owned
  operation variants to Block 10 and reuses the existing conclusion projection;
  it adds no review ledger or generalized prompt surface.
- Tradeoff and source evidence: explicit candidate/evidence packets make the
  interaction slower than a generic message box but are required by the
  maintained checkpoint, meta-review, incident, and route contracts.

### Inputs and dependencies

- Accepted Block 7 run/supervisor workspaces.
- Accepted Blocks 10 and 11 operation/task owners.
- Current reviewer roles and supported conclusion contract from Blocks 0 and 4.

### Required work

- Register `Request checkpoint review`, `Request meta-review`, and `Request
  issue follow-up` as separate typed variants routed only to their maintained
  reviewer/supervisor owner.
- Require the exact target, candidate or state fingerprint, source/delta or
  incident/decision scope, maintained purpose, expected conclusion fields,
  route gate, and currentness basis in each preview.
- Display requested, routed, active, awaiting conclusion, concluded, rejected,
  stale, superseded, denied, and unverified states without treating a delivered
  task message as review completion.
- Verify a conclusion only from a newer canonical reviewer record bound to the
  exact target, purpose, evidence/candidate root, and eligible reviewer role.
- Link the request and conclusion separately into supervisor action and
  conclusion history; keep no-conclusion and later-superseded outcomes visible.

### Scope and non-goals

- In scope: explicit checkpoint, meta-review, and issue-follow-up requests and
  their current semantic conclusions.
- Not in scope: mechanical checks, policy/cadence changes, binding repair,
  implementation acceptance by the dashboard, reports, evolution, or lifecycle
  mutation.
- Do not expose a generic reviewer prompt or let a mechanical watcher produce a
  semantic conclusion.

### Deliverables and recorded state

- Three semantic-review operation contracts, route/currentness verifiers,
  request/conclusion UI states, history links, and focused tests.

### Resource and economy contract

Send one bounded evidence packet to one exact role per confirmed request. Reuse
an unchanged active review rather than duplicating it; never auto-retry. Poll
only its named conclusion source until the bounded timeout, then retain
`awaiting conclusion` or `unverified` without widening.

### QA and independent review

- Test wrong role/purpose/target, absent candidate or delta, stale source,
  route denial, duplicate active review, no conclusion, ineligible author,
  conclusion for another root, later supersession, timeout, and restart.
- Run non-mutating previews against current checkpoint, meta-review, and open-
  issue examples; use the disposable validation run for an end-to-end request.
- Independent authority review confirms role separation, evidence binding, and
  honest request-versus-conclusion language.

### Acceptance

- The operator can request each supported review from the relevant run/issue,
  follow its exact reviewer task/action, and see a matching current conclusion
  appear separately from the request.
- Wrong-owner, stale, denied, duplicate, missing, rejected, and superseded
  reviews retain exact reasons and never become current conclusions.
- No reviewer operation edits target work or accepts implementation on the
  dashboard's own authority.

### Negative tests

- Reject `review concluded` from message delivery, terminal reviewer task, or a
  conclusion bound to another target/candidate/evidence root.
- Reject a checkpoint/meta/issue request routed to the watcher, fix executor, or
  unrelated task.

### Completion evidence

Pending.

### Stop

Stop before policy/cadence administration, binding repair, lifecycle mutation,
reporting, or Factory evolution.

---

## Block 14 — Supervision policy and cadence administration

Status: `not-started`

### Objective

Let the operator preview and apply one bounded supervision policy or cadence
change while proving both versioned policy history and required automation
reconciliation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: make supported supervision configuration changes
  operable from the dashboard with preserved fields and actual schedule effects.
- Potential capability loss or regression: an overbroad diff, direct TOML edit,
  or policy-only success claim could desynchronize the supervisor and its
  automations.
- Protected-capability effect: preserves policy version/history ownership,
  explicit field authority, automation single-writer boundaries, unchanged
  fields, rollback/compensation posture, and partial-reconciliation attention.
- Architecture and operating-model effect: adds one policy-diff operation and
  owner-specific dual postcondition to the operation framework; it does not add
  a settings database or scheduler.
- Tradeoff and source evidence: staged policy plus automation verification takes
  longer than direct configuration editing but is required by the maintained
  `adjust` and automation-owner contracts.

### Inputs and dependencies

- Accepted Block 7 policy/role/automation projections.
- Accepted Blocks 10 and 11 operation/task owners.
- Current supported policy fields, automations, and authority matrix from Block
  0.

### Required work

- Register `Adjust supervision` as an explicit before/after policy-field diff to
  the current supervisor owner; allow only fields the live owner proves
  adjustable.
- Preview target/group, old/new exact values, preserved fields, affected roles
  and automations, authority, expected policy version, reconciliation steps,
  compensation posture, and unsupported fields.
- Request the change through the maintained owner, never by directly editing
  policy JSON/history or automation TOML.
- Verify the next valid policy version/history and each affected automation's
  actual enabled/schedule/binding state as separate postconditions.
- Render policy-applied/automation-pending, partially reconciled, failed,
  unverified, and fully reconciled states with exact attention and recovery.
- Continue to project Gmail lane ownership/configuration read-only where
  present; this operation may not read messages, send mail, or install a mailbox
  integration.

### Scope and non-goals

- In scope: one bounded supported policy/cadence diff and its automation
  reconciliation.
- Not in scope: binding repair, pause/resume semantics, mission succession,
  arbitrary policy JSON, Gmail body operations, or a generic scheduler UI.
- Do not label policy update alone as a reconciled configuration change.

### Deliverables and recorded state

- Policy-diff schema, preview, owner request, policy/automation postcondition
  verifier, Admin/run UI, recovery state, and focused integration tests.

### Resource and economy contract

Resolve one target/group and only the fields/automations in the submitted diff.
Reuse current policy and automation fingerprints, request once, and poll each
named postcondition to its bounded timeout. Do not scan or reconcile unrelated
automations.

### QA and independent review

- Test unsupported/extra fields, stale policy, preserved-field drift, authority
  denial, direct-file path input, policy success with automation failure,
  partial multi-automation reconciliation, restart, and compensation display.
- Exercise live preview/status read-only on a current group and mutate only the
  disposable validation group or an exactly authorized real target.
- Independent owner review verifies the accepted diff and both postconditions
  against current policy and automation contracts.

### Acceptance

- The operator can preview one supported exact diff, see every affected owner,
  apply it through the maintained owner, and verify the next policy version plus
  actual automation state.
- Partial or failed reconciliation remains attention and exposes an exact safe
  recovery; no unchanged field or unrelated automation is modified.
- Dashboard code never writes policy/history JSON or automation TOML directly.

### Negative tests

- Reject `adjusted` when only the policy version changed but an affected
  automation did not reconcile.
- Reject unknown fields, broad reset/default operations, stale previews, or a
  path/payload that could select arbitrary configuration.

### Completion evidence

Pending.

### Stop

Stop before repairing bindings or performing pause/resume, mission, continuity,
report, evolution, or terminal operations.

---

## Block 15 — Mission and target/tracker binding repair

Status: `not-started`

### Objective

Repair one reproduced canonical mission-to-target/tracker binding mismatch
through the maintained supervision bind/policy owner without changing the
mission or creating a parallel supervision root.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator restore one exact target's
  supervision identity when its active mission, target, and tracker tuple is
  missing or inconsistent.
- Potential capability loss or regression: label-based joining, a stale root,
  or using `bind` to introduce different intent could attach the wrong tracker,
  overwrite mission history, or create duplicate authority.
- Protected-capability effect: preserves direct mission provenance, exact
  target/tracker identity, versioned policy history, current-root scoping, and
  the prohibition on parallel supervision ledgers.
- Architecture and operating-model effect: adds one tuple-repair operation to
  the existing operation registry and reuses the maintained bind/policy owner;
  it adds no reconciliation database or generic repair engine.
- Tradeoff and source evidence: the control can repair only a reproduced
  compatible tuple and cannot reinterpret intent, matching the current bind,
  mission-successor, and tracker-identity contracts.

### Inputs and dependencies

- Accepted Block 7 topology, mission-history, and tracker inspectors.
- Accepted Blocks 10 and 11 operation/task owners.
- Exact tuple anomaly and current bind/policy owner map from Blocks 0 and 4.

### Required work

- Register `Repair mission/target/tracker binding` only when the projection
  reproduces one missing or incompatible field in the selected target's exact
  active tuple and the maintained owner supports a compatible repair.
- Preview current and expected mission root/source, target thread, tracker path
  and content root, governing policy version, anomaly evidence, preserved
  history, prohibited effects, and exact next-policy postcondition.
- Route one repair through the maintained bind/policy owner. Prohibit direct
  policy/ledger/catalog writes, label-only matching, arbitrary paths, broad
  reset, or creation of another group.
- Verify the next canonical policy/history record, exact active tuple, unchanged
  mission semantics, and absence of another active group for that tuple.
- Treat materially different mission intent as Block 19 mission succession,
  never a repair or `bind` overwrite.

### Scope and non-goals

- In scope: one exact mission/target/tracker identity tuple and its compatible
  maintained-owner repair.
- Not in scope: role-task or automation binding, policy tuning, tracker edits,
  mission succession, task creation, or lifecycle change.
- Do not repair a healthy, ambiguous, unsupported, or semantically different
  tuple.

### Deliverables and recorded state

- Tuple-anomaly projection, one repair contract and preview/postcondition
  verifier, run/Admin control, refreshed topology/history, and focused tests.

### Resource and economy contract

Read one target/group policy and one declared tracker, reuse their fingerprints,
issue one owner request, and re-read only the next policy/tuple plus duplicate-
group check. Never scan or reconcile unrelated groups.

### QA and independent review

- Test healthy/no-op, missing target or tracker, wrong mission/source/root,
  tracker path/root drift, label collision, stale policy, duplicate group,
  direct-file input, material-new-mission attempt, partial result, and restart.
- Use a disposable malformed tuple fixture; inspect live targets read-only unless
  exact repair authority is provided.
- Independent mission/binding review confirms exact provenance, compatible
  semantics, preserved history, and single active ownership.

### Acceptance

- One reproduced supported tuple mismatch becomes one exact current canonical
  mission/target/tracker binding through the next valid policy history record.
- No mission semantics, tracker content, historical binding, or unrelated group
  changes, and no duplicate active group remains.
- Healthy, ambiguous, stale, materially different, and unsupported tuples fail
  closed with their exact reason.

### Negative tests

- Reject label-only resolution, arbitrary tracker paths, healthy mutation,
  mission overwrite, second-root creation, or file-existence-only proof.
- Reject success when the active tuple or duplicate-group check does not match
  the preview fingerprint.

### Completion evidence

Pending.

### Stop

Stop before repairing role-task or automation bindings or performing policy,
lifecycle, continuity, report, evolution, or terminal operations.

---

## Block 16 — Role-task binding repair

Status: `not-started`

### Objective

Repair one reproduced supervisor-role-to-task binding mismatch through the
maintained policy/task owner and prove one unambiguous eligible role assignment.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator restore the exact watcher,
  reviewer, fix-executor, notice, Gmail-gate, or target task expected by one
  supervision role.
- Potential capability loss or regression: resolving by label, accepting a task
  with the wrong purpose, or assigning one thread to ambiguous roles could route
  consequential work or conclusions to the wrong authority.
- Protected-capability effect: preserves exact thread IDs, role eligibility,
  purpose-route contracts, task history, single-role routing, and independent
  reviewer/executor separation.
- Architecture and operating-model effect: adds one role-binding repair
  operation through the existing policy/task owners; it does not create tasks
  generically or add a role directory.
- Tradeoff and source evidence: exact one-role repair requires a live task and
  policy cross-check but is the smallest safe path under current routing and
  role-refresh contracts.

### Inputs and dependencies

- Accepted Block 7 role/task/topology inspectors.
- Accepted Blocks 10 and 11 operation/task owners.
- Reproduced role mismatch and current role/purpose eligibility map from Blocks
  0, 4, and 5.

### Required work

- Register `Repair role task binding` only for one exact configured role whose
  missing, terminal-ineligible, wrong-purpose, or mismatched task is reproduced.
- Preview group/mission, role, current and expected task IDs, task lifecycle,
  eligible model/effort/purpose where governed, route-gate implications,
  preserved roles, owner action, and exact policy/task postcondition.
- Use the maintained task owner to identify or create a task only when direct
  task-creation authority exists, then use the maintained policy/bind owner to
  assign that exact task to the one role. Never infer identity from title.
- Verify the live task identity/lifecycle and next canonical role binding as
  separate postconditions; run the route gate for the role's maintained purpose
  before calling the repair applied.
- Retain denied, ambiguous, partial, stale, and task-created-but-unbound states
  with their exact recovery; do not touch any automation binding.

### Scope and non-goals

- In scope: one exact configured supervision role and one eligible Codex task.
- Not in scope: mission/target/tracker repair, automation repair, generic task
  creation, role-policy redesign, implementation handoff, or lifecycle change.
- Do not bind one thread to multiple incompatible roles or repurpose a task with
  conflicting current work.

### Deliverables and recorded state

- Role-anomaly projection, one role-task repair contract, task/policy/route
  postcondition verifier, run/Admin control, and focused tests.

### Resource and economy contract

Read one group, one role, and the exact candidate task. Perform at most one task
owner action and one policy assignment, then re-read only those two sources and
the named route gate. Never search or mutate unrelated roles.

### QA and independent review

- Test missing task, wrong role/purpose/model, terminal-ineligible task,
  conflicting live work, ambiguous multi-role ID, absent creation authority,
  route denial, stale policy/task, task-created-but-unbound, restart, and
  preserved unrelated roles.
- Exercise mutation only in a disposable group/task unless exact authority names
  the live role; use real roles for read-only previews.
- Independent role/route review verifies task eligibility, single-role scope,
  exact owner sequence, and both postconditions.

### Acceptance

- One reproduced role mismatch resolves to one exact eligible current task in
  canonical policy and its maintained route gate accepts the named purpose.
- Task creation or policy change alone remains partial until both postconditions
  match; unrelated roles and task work remain unchanged.
- Missing authority, ambiguity, conflict, stale state, or unsupported role fails
  closed with an exact next owner action.

### Negative tests

- Reject title/label matching, one thread in incompatible roles, wrong-purpose
  routing, generic task creation, or success from only task or policy state.
- Reject any repair that changes the mission tuple or an automation binding.

### Completion evidence

Pending.

### Stop

Stop before automation binding repair, pause/resume, mission succession,
successor-task continuity, reporting, evolution, or terminal lifecycle.

---

## Block 17 — Automation binding repair

Status: `not-started`

### Objective

Repair one reproduced supervision-automation binding mismatch through the
automation and policy owners and prove matching canonical schedule/binding state.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator restore one exact routine, meta,
  Gmail, roundup, or report automation to its selected supervision group and
  maintained role.
- Potential capability loss or regression: direct TOML edits, wrong schedule or
  target, or policy-only success could duplicate checks, disable supervision,
  or send work through the wrong owner.
- Protected-capability effect: preserves automation-tool single writing,
  exact IDs/schedules/targets, policy history, maintained purpose/role, and the
  distinction between configured and actually reconciled state.
- Architecture and operating-model effect: adds one automation-binding repair
  with dual automation/policy postconditions; it adds no scheduler or bulk
  reconciler.
- Tradeoff and source evidence: verifying two canonical owners is slower than a
  configuration edit but is required by the existing automation and policy bind
  contracts.

### Inputs and dependencies

- Accepted Block 7 automation/topology inspectors.
- Accepted Blocks 10 and 11 operation/task owners.
- Reproduced automation mismatch and current automation-role owner map from
  Blocks 0 and 4.

### Required work

- Register `Repair automation binding` only for one exact automation whose ID,
  group/target, role/purpose, enabled state, or schedule differs from the
  canonical policy expectation.
- Preview current/expected automation ID and projection, target/group/role,
  schedule/time zone, policy version, mismatch evidence, preserved automations,
  compensation posture, and both expected postconditions.
- Apply the smallest supported change through the Codex automation owner and
  maintained policy/bind owner; prohibit direct TOML/JSON writes, ID invention,
  broad rebind, or implicit cadence redesign.
- Verify the actual automation configuration and next canonical policy binding
  separately, including no duplicate automation for the same maintained role.
- Preserve automation-changed/policy-pending, policy-changed/automation-pending,
  partial, denied, stale, and unverified states with exact bounded recovery.

### Scope and non-goals

- In scope: one existing or exactly authorized automation and one group-role
  binding.
- Not in scope: policy/cadence tuning, mission/target/tracker or role-task
  repair, bulk reconciliation, pause/resume, Gmail body operations, or a new
  scheduler.
- Do not alter unrelated automation schedules or treat policy state alone as
  reconciliation.

### Deliverables and recorded state

- Automation-anomaly projection, one repair contract, dual postcondition and
  duplicate-role verifier, run/Admin control, recovery state, and focused tests.

### Resource and economy contract

Read one policy and one named automation projection, execute each required owner
action at most once, and re-read only those sources plus the duplicate-role
check. Never enumerate or reconcile unrelated automation families.

### QA and independent review

- Test missing/wrong ID, target, role, purpose, schedule, and time zone; direct-
  file input; stale policy/config; duplicate role automation; one-owner-only
  change; denial; restart; and preserved unrelated schedules.
- Exercise end to end only on a disposable automation/group unless exact current
  authority names a live repair.
- Independent automation/policy review verifies smallest owner actions, both
  canonical postconditions, compensation posture, and no schedule creep.

### Acceptance

- One reproduced automation mismatch reaches matching actual automation and
  canonical policy binding state for the selected group-role.
- Partial, stale, duplicate, denied, and unsupported repairs remain attention
  with exact recovery; unrelated automations remain byte/state unchanged.
- Dashboard code never writes automation TOML or supervision policy directly.

### Negative tests

- Reject direct configuration writes, invented IDs, broad rebind, implicit
  cadence changes, or success from only automation or policy state.
- Reject repair when another active automation still owns the same exact role.

### Completion evidence

Pending.

### Stop

Stop before pause/resume, same-target mission succession, successor-task
continuity, reporting, evolution, or terminal lifecycle operations.

---

## Block 18 — Supervision pause and resume

Status: `not-started`

### Objective

Pause or resume one supervision group through its automation and lifecycle
owners while preserving exact target state and keeping turn interruption
semantically separate.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: provide reversible operator control over scheduled
  supervision without leaving automation and lifecycle state inconsistent.
- Potential capability loss or regression: confusing turn interrupt with pause,
  changing only automation, or broad pausing could silently remove monitoring
  or misstate lifecycle.
- Protected-capability effect: preserves automation single writers, lifecycle
  gates, target/group scope, resume/recovery state, role bindings, and distinct
  App Server turn semantics.
- Architecture and operating-model effect: adds two specific lifecycle
  operations with dual automation/lifecycle postconditions; it adds no generic
  kill switch.
- Tradeoff and source evidence: the dual-state transition is more deliberate
  than toggling a schedule but is required by the maintained pause/resume and
  lifecycle contracts.

### Inputs and dependencies

- Accepted Block 7 run/automation/lifecycle workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Current lifecycle and automation contracts from Block 0.

### Required work

- Register `Pause supervision` and `Resume supervision` as separate operations
  through the exact automation/supervision owners and lifecycle gate.
- Preview target/group, current lifecycle, affected automations, pending owner
  work, preserved target/task state, expected postconditions, and recovery.
- Verify both actual automation enabled/schedule state and the matching canonical
  lifecycle record; expose partial transition and safe recovery without auto-
  retry.
- Keep task/turn `interrupt` and `continue` visibly separate in labels,
  confirmation, history, and postconditions.
- Scope pause/resume to the selected group; preserve Gmail/report ownership and
  target implementation state unless the maintained owner explicitly changes
  them.

### Scope and non-goals

- In scope: semantic pause and resume for one supervision group.
- Not in scope: interrupting/continuing a turn, request-stop, terminal shutdown,
  policy tuning, report generation, or mission/successor transition.
- Do not expose a generic red Stop control or multi-group bulk toggle.

### Deliverables and recorded state

- Pause/resume operation contracts, lifecycle/automation previews and
  postcondition verifiers, run controls, partial/recovery states, and tests.

### Resource and economy contract

Touch one group and only its bound automations. Request once, poll the two named
owners to bounded timeout, and preserve partial state for operator recovery;
never repeat or widen automatically.

### QA and independent review

- Test turn-interrupt confusion, stale lifecycle, gate denial, missing/partial
  automation bindings, already paused/running, one owner changed only, wrong
  group, restart, and recovery.
- Exercise full pause/resume only on the disposable group unless exact current
  authority names a real target.
- Independent authority review verifies dual postconditions and preserved
  target/group state.

### Acceptance

- The selected group reaches matching paused or resumed automation and lifecycle
  state, with exact current records visible in the run/floor history.
- Partial, denied, stale, already-satisfied, and failed transitions remain
  truthful and recoverable.
- A turn interruption can never render or verify semantic supervision pause.

### Negative tests

- Reject `paused` or `resumed` when only a turn or only one canonical owner
  changed.
- Reject bulk, wrong-group, stale-preview, or gate-bypassing pause/resume.

### Completion evidence

Pending.

### Stop

Stop before same-target mission succession, successor-task continuity,
reporting, evolution, request-stop, or terminal shutdown.

---

## Block 19 — Same-target mission succession

Status: `not-started`

### Objective

Move one long-lived target to a materially different directly authorized
mission through `mission-successor` while preserving the predecessor as scoped
history.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let a maintained target and supervision group begin
  a new mission without creating a parallel ledger or contaminating new state
  with predecessor evidence.
- Potential capability loss or regression: using `bind`, accepting unchanged or
  unauthorized intent, or ignoring open heads could overwrite history or carry
  false completion/issues into the new mission.
- Protected-capability effect: preserves direct mission authority, predecessor
  completion/supersession evidence, policy history, closed incident/decision/
  successor-transition gates, active-root event scoping, and one supervision
  root.
- Architecture and operating-model effect: exposes the settled
  `mission-successor` owner as one explicit operation distinct from binding
  repair and successor-task creation.
- Tradeoff and source evidence: strict predecessor and direct-source gates make
  mission reuse deliberate but are required by commit `c7d4efc` and the current
  mission-binding policy.

### Inputs and dependencies

- Accepted Block 7 mission history/current-root workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Current `mission-successor` owner and active mission contract from Blocks 0
  and 4.

### Required work

- Register `Begin successor mission on this target` through the maintained
  `mission-successor` command, not `bind` or a new supervision group.
- Preview target/group, predecessor mission root/source, new direct source
  class/record/hash, reason/evidence, material difference, preserved roles/
  automations, required predecessor completion or supersession, and all
  prohibiting open heads.
- Require direct operator authority for the new mission and exact confirmation;
  reject routed supervisor language as direct mission authority.
- Verify the next policy version/history, active new mission binding, unchanged
  target/group/automations, preserved predecessor segment, and mission-scoped
  current state with no predecessor-only leakage.
- Label this operation and history distinctly from successor-task continuity.

### Scope and non-goals

- In scope: one same-target, same-group mission succession.
- Not in scope: binding repair, creating a new task/group, successor-task
  handoff, report generation, target stop, or implementation work for the new
  mission.
- Do not allow unchanged intent, parallel active roots, or old evidence to
  establish new-mission status.

### Deliverables and recorded state

- Mission-succession operation contract, authority/closed-head preview,
  policy/history/current-root postcondition verifier, mission-history UI, and
  focused tests.

### Resource and economy contract

Read one target's current policy/history and open heads, issue one successor
request, and re-read only the new policy/current mission plus predecessor
segment. Do not scan unrelated groups or retry automatically.

### QA and independent review

- Test wrong predecessor, unchanged mission, absent direct authority, completed
  and explicitly superseded predecessor, open incident/decision/successor-task
  transition, stale policy, parallel root, history preservation, and cross-root
  event/conclusion/metric isolation.
- Execute only in a disposable long-lived target unless exact authority names a
  real mission transition.
- Independent mission/authority review verifies direct-source provenance,
  preserved predecessor history, and new-root isolation.

### Acceptance

- A directly authorized materially new mission becomes the sole active binding
  on the same target/group through a new policy-history version.
- The predecessor remains separately inspectable, and its completion, issues,
  conclusions, and metrics do not become current for the successor.
- Open-head, authority, currentness, and unchanged-mission failures prevent the
  operation with exact reasons.

### Negative tests

- Reject `bind` overwrite, a second active supervision root, unchanged mission,
  routed-provenance-as-direct-authority, or succession with prohibited open
  heads.
- Reject any successor status or green light derived from predecessor-only
  records.

### Completion evidence

Pending.

### Stop

Stop before creating a successor task, generating reports, running Factory
evolution, or changing terminal lifecycle.

---

## Block 20 — Successor-task continuity

Status: `not-started`

### Objective

Carry one required cross-task implementation transition through a started,
bound successor without allowing the source mission to stop prematurely.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator inspect and advance an authorized
  successor-task transition through exact continuity phases from the dashboard.
- Potential capability loss or regression: treating a handoff, created task, or
  acknowledgement as completion could strand requested work and stop the source
  before the successor begins.
- Protected-capability effect: preserves direct task-creation authority,
  tracker/mission/range identity, isolated successor binding, append-only phase
  history, route gates, source activity, and current `work-started` proof.
- Architecture and operating-model effect: exposes the maintained successor-
  transition record/gate and Codex task owner as one staged operation distinct
  from same-target mission succession.
- Tradeoff and source evidence: the multi-phase transition is slower than a
  one-click handoff but is required by the accepted successor-continuity owner
  and prevents false source completion.

### Inputs and dependencies

- Accepted Block 7 run/task/transition workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Current successor-transition and task-creation contracts from Blocks 0 and 4.

### Required work

- Project the exact current transition and its phases: `required`, `successor-
  created`, `successor-bound`, `handoff-sent`, `target-acknowledged`, and `work-
  started`, including source mission/tracker/range, authority, IDs, records, and
  missing next owner action.
- Register operation-specific steps to start or identify the exact successor
  only under direct task-creation authority, bind its isolated mission/group,
  send the route-gated handoff, record acknowledgement, and verify first-
  eligible-Block work start through maintained owners.
- Re-preview current phase and sources before every step; never leap phases,
  invent IDs, repeat a satisfied step, or relabel routed supervisor provenance
  as direct authority.
- Call the maintained successor transition gate and keep the source active until
  `source_stop_permitted=true` from current `work-started` evidence.
- Label successor-task continuity separately from Block 19 same-target mission
  succession in controls, history, metrics, and attention.

### Scope and non-goals

- In scope: one already required or directly authorized successor-task
  transition through verified work start.
- Not in scope: same-target mission succession, generic task creation, source
  terminal shutdown, implementation inside the successor, or a parallel
  transition ledger.
- Do not convert missing direct task-creation authority into an invented ID or
  ordinary status request.

### Deliverables and recorded state

- Transition-detail UI, phase-specific operation contracts, route/authority/
  postcondition verifiers, source-stop gate display, recovery states, and tests.

### Resource and economy contract

Read and mutate one transition head at a time. Reuse satisfied phase records,
perform at most one owner action per confirmed step, and poll only the expected
next record. Stop at missing authority or unverified phase without repeating or
widening.

### QA and independent review

- Test missing/invalid authority, wrong source/tracker/range, out-of-order or
  duplicate phase, stale head, mismatched successor ID/group, handoff without
  acknowledgement, acknowledgement without work start, gate deny, restart, and
  source-stop attempt before work start.
- Execute a full transition only in the disposable validation topology or under
  exact direct authority; use current live transitions for read-only preview.
- Independent continuity review verifies phase evidence, source activity, and
  the exact successor first-work postcondition.

### Acceptance

- The operator can follow one transition from requirement through successor
  work start, and each phase resolves to its current canonical record and owner.
- The source cannot render stoppable/complete before the maintained gate proves
  current successor `work-started` evidence.
- Missing authority, mismatch, stale phase, or partial transition remains open
  with a precise next owner action and no invented state.

### Negative tests

- Reject source stop from successor-created, bound, handoff-sent, or
  acknowledged state without current work-started proof.
- Reject a same-target mission successor presented as a successor task, or a
  supervisor packet relabeled as direct creation authority.

### Completion evidence

Pending.

### Stop

Stop before weekly/terminal reporting, Factory evolution, source request-stop,
or terminal shutdown.

---

## Block 21 — Weekly supervision report workflow

Status: `not-started`

### Objective

Produce, independently review, verify, display, and when configured deliver one
current weekly supervision report through the maintained report owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator initiate and follow a trustworthy
  weekly Factory report from deterministic evidence through verified artifact
  and configured delivery.
- Potential capability loss or regression: regenerating unchanged work,
  skipping cognitive review, or treating file existence/delivery as verification
  could publish stale or misleading metrics.
- Protected-capability effect: preserves report-as-derived-view semantics,
  source/currentness roots, deterministic versus cognitive stages, independent
  writer/reviewer roles, manifest/PDF verification, limitations, and Gmail lane
  ownership.
- Architecture and operating-model effect: exposes the maintained weekly report
  workflow as one staged operation integrated with Block 9 report views; it adds
  no report database or scheduler.
- Tradeoff and source evidence: staged prepare/review/finalize/verify/deliver is
  slower than generating a file, but the current report contract requires those
  distinctions for evidence-bound conclusions.

### Inputs and dependencies

- Accepted Block 9 metrics/report workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Accepted Block 13 semantic-review request/conclusion handling.
- Current weekly-report and delivery contracts from Block 0.

### Required work

- Register `Generate weekly report` with exact target/run, report period/time
  zone, source roots, currentness fingerprint, writer/reviewer roles, configured
  delivery lane, and expected bundle members.
- Preserve explicit stages: deterministic prepare, source/currentness check,
  bounded independent cognitive review, finalize, manifest/Markdown/PDF/JSON
  verification, artifact display, and configured owner-mediated delivery.
- Reuse an unchanged valid prepare/review/artifact by exact source/candidate
  fingerprint; never rerun a valid producer only because display or delivery
  failed.
- Verify each stage through its maintained record/artifact/manifest/delivery
  owner; a generated file, reviewer task, or email receipt alone is insufficient.
- Project Gmail roundup ownership/configuration read-only. Never read message
  bodies or send mail directly from dashboard code; missing Gmail leaves the
  report verified but delivery unavailable/retryable as its owner specifies.
- Show stage progress, limitations, partial failure, recovery, exact artifact
  links, and resulting report/history attention in Reports and run detail.

### Scope and non-goals

- In scope: one weekly report workflow and its configured delivery.
- Not in scope: terminal reporting, Factory evolution, new metrics, direct Gmail
  operations, automatic scheduling, or outcome-completion claims.
- Do not regenerate unchanged source work or equate report verification with
  implementation acceptance.

### Deliverables and recorded state

- Weekly-report operation contract, stage/currentness/postcondition model,
  Reports/run UI, artifact/delivery recovery, and focused integration tests.

### Resource and economy contract

Process one target/period and reuse stage outputs by exact roots. Prepare and
cognitive review each run at most once per unchanged candidate; on later-stage
failure rerun only that stage. Poll named records only and stop at the first
unverified stage.

### QA and independent review

- Test stale/changed sources, invalid period, reused prepare/review, cognitive
  rejection, missing bundle member, bad manifest/PDF, display failure, delivery
  unavailable/failure, retry without regeneration, wrong role, and restart.
- Run end to end only on a disposable/current authorized report target; compare
  displayed metrics and limitations to exact artifacts.
- Independent report review verifies source roots, cognitive disposition,
  artifacts, limitations, and delivery semantics on the frozen candidate.

### Acceptance

- One report advances through every required stage and appears verified in
  report history with exact sources, limitations, manifest, Markdown/PDF/JSON,
  and configured delivery posture.
- A failure at review, finalize, verify, display, or delivery retains valid prior
  stages and offers only the appropriate bounded recovery.
- No file, task, email, or passing validator alone is labeled a verified report
  or implementation outcome.

### Negative tests

- Reject report verification from file existence, writer completion, email
  receipt, or stale pre-correction review alone.
- Reject rerunning deterministic generation/cognitive review solely for a
  display or delivery failure when roots remain current.

### Completion evidence

Pending.

### Stop

Stop before terminal reporting, Factory evolution, request-stop, or shutdown.

---

## Block 22 — Factory evolution evaluation and disposition

Status: `not-started`

### Objective

Produce and verify one source-bound Factory-evolution disposition through the
maintained derived-artifact owner, without implementing, adopting, deploying,
or measuring the candidate on the dashboard's authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator prepare, review, evaluate, verify,
  and inspect trustworthy Factory learning through one explicit `promote`,
  `advisory`, `revise`, or `reject` disposition.
- Potential capability loss or regression: stale sources, collapsed proposer/
  implementer/evaluator roles, or presenting disposition as implementation or
  adoption could create false authority and mutate Factory behavior indirectly.
- Protected-capability effect: preserves deterministic evidence inputs,
  immutable derived artifacts, independent semantic/evaluation roles, exact
  baseline/candidate revisions, rejected paths, and disposition-only authority.
- Architecture and operating-model effect: exposes only the maintained
  `factory-evolution prepare/finalize/evaluate/verify` owner in this Block;
  candidate implementation remains Block 11 work and no adoption engine,
  scheduler, or skill editor is added.
- Tradeoff and source evidence: the cycle must pause for separately owned
  candidate implementation and current evaluation evidence, but this is the
  explicit boundary in the Factory-evolution contract.

### Inputs and dependencies

- Accepted Block 9 evolution/report workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Accepted Block 13 semantic evaluation handling.
- Current Factory-evolution implementation/eligibility/authority matrix from
  Block 0.

### Required work

- Expose `Run Factory evolution` only when the installed derived-artifact
  helper, explicit verified weekly report/event inputs, eligibility, target/
  evolution identity, and eligible proposer/evaluator roles are proven. Keep
  planned autonomous/adaptive controls unavailable with exact prerequisites.
- Preserve the maintained artifact stages exactly: deterministic `prepare`,
  one bounded independent cognitive `finalize`, revision-bound independent
  `evaluate`, and deterministic `verify` of the immutable packet, review,
  evaluation, reports, and manifest.
- After `finalize` selects an experiment, show `awaiting candidate
  implementation` until a separately governed Block 11 author/implement/
  supervise workflow supplies exact baseline/candidate revisions and evidence.
  This Block may link to that owner record but may not launch, accept, or write
  the candidate as part of the evolution operation.
- Bind every artifact stage to exact packet/review/experiment/candidate/
  baseline/evaluation roots and eligible distinct roles; reuse byte-identical
  artifacts and preserve advisory/revise/reject and contrary evidence history.
- Verify only one disposition from the current evaluation set. A reviewer task,
  implemented candidate, favorable comparison, or `promote` alone is not a
  verified artifact set.
- Display stage/currentness, external implementation prerequisite, comparison,
  regressions, disposition, source proof, limitations, and bounded recovery in
  Reports/Admin. Display adoption, installation, routing, scheduling,
  deployment, and later outcome as `not performed by evolution` and link only
  to a separately proven existing owner; otherwise mark them unavailable.

### Scope and non-goals

- In scope: one on-demand derived Factory-evolution artifact set through a
  verified independent disposition.
- Not in scope: weekly/terminal report generation, candidate implementation,
  skill maintenance, adoption, installation, routing, scheduling, deployment,
  outcome/rollback control, direct skill edits, or autonomous evolution.
- Do not treat a selected or implemented candidate, passing experiment, or
  `promote` disposition as adopted capability or current outcome success.

### Deliverables and recorded state

- Evolution artifact-stage operation contract, external-implementation wait
  state, eligibility/currentness/evaluation/disposition verifiers,
  Reports/Admin UI, recovery, and focused tests.

### Resource and economy contract

Run one target/evolution ID at a time. Reuse byte-identical packet, review,
baseline, candidate, evaluation, and manifest roots; never repeat an external
implementation owner or producer for display failure. Respect maintained bounds
and stop at the first unavailable, stale, rejected, or unverified stage.

### QA and independent review

- Test ineligible, missing/changed report or event input, immutable-ID conflict,
  proposer/implementer/evaluator alias, missing external implementation,
  baseline/candidate drift, incomplete cases, synthetic-only promotion,
  regression, invalid manifest, all four dispositions, stale review, restart,
  and attempted adoption/deployment/skill write.
- Exercise end to end only with disposable derived artifacts and separately
  produced candidate evidence or under exact authority for a current cycle.
- Independent evolution review verifies source roots, role separation,
  comparison evidence, disposition, and the absence of implementation,
  adoption, deployment, or outcome claims.

### Acceptance

- An eligible cycle can reach a verified disposition with every source,
  candidate, evaluation, tradeoff, limitation, and rejected path inspectable.
- External candidate implementation is attributable to its independent Block
  11 owner and is neither executed nor accepted by this evolution operation.
- Ineligible, stale, unavailable, rejected, advisory, revise, and promote states
  are truthful; none mutates Factory capability or asserts adoption/outcome.

### Negative tests

- Reject disposition from report nomination, reviewer/evaluator task completion,
  implemented-candidate existence, favorable metrics, stale roots, or a
  non-independent evaluator.
- Reject any implementation, adoption, installation, routing, scheduling,
  deployment, rollback, or outcome mutation presented as part of this Block.

### Completion evidence

Pending.

### Stop

Stop at the verified `promote`, `advisory`, `revise`, or `reject` disposition,
before candidate implementation/maintenance, adoption, installation, routing,
scheduling, deployment, outcome/rollback control, terminal reporting, or final
acceptance.

---

## Block 23 — Terminal report workflow

Status: `not-started`

### Objective

Prepare, independently review, verify, display, and deliver the required
terminal supervision report without stopping or pausing the run.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: give the operator a current verified terminal
  evidence package before any shutdown decision.
- Potential capability loss or regression: conflating file generation,
  cognitive review, delivery, or task terminality with outcome completion could
  support premature shutdown.
- Protected-capability effect: preserves observable-outcome reconciliation,
  full-scope/delta report contracts, verified prior reports, current source
  roots, independent review, PDF/manifest semantics, configured Gmail delivery,
  and shutdown separation.
- Architecture and operating-model effect: exposes the maintained terminal-
  report owner as one staged operation dependent on report history; shutdown
  remains Block 24.
- Tradeoff and source evidence: required currentness, cognitive review,
  verification, and delivery add latency but are mandated by the terminal report
  and supervision lifecycle contracts.

### Inputs and dependencies

- Accepted Block 9 report/history workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Accepted Block 13 semantic-review handling and Block 21 verified prior-report
  workflow.
- Current terminal-report/outcome/delivery contract from Block 0.

### Required work

- Register `Prepare terminal report` with exact target/mission/completed
  fingerprint, report type/full-scope/delta anchor, source roots, prior verified
  reports, current completion reconciliation, writer/reviewer roles, required
  bundle members, and delivery lane.
- Preserve stages: deterministic prepare, currentness/outcome-source check,
  bounded independent cognitive review, finalize, manifest/Markdown/PDF/JSON
  and semantic-projection verification, artifact display, configured owner-
  mediated attachment delivery, and required receipt/readback where current
  policy demands it.
- Reuse valid unchanged sources/stages and rerun only a failed later stage;
  preserve diagnostic/pre-correction bundles without calling them current.
- Verify every stage through its own maintained owner. Keep report readiness
  separate from lifecycle/shutdown permission and expose missing prerequisites,
  limitations, partial delivery, and exact recovery.
- Project Gmail terminal lane ownership/configuration but never read or send
  messages directly from dashboard code.

### Scope and non-goals

- In scope: one terminal report bundle and configured delivery/readback.
- Not in scope: weekly reporting, Factory evolution, target completion decision,
  request-stop, pause, shutdown, or direct Gmail operations.
- Do not treat a verified terminal report as permission to stop.

### Deliverables and recorded state

- Terminal-report operation/stage contract, prerequisite/currentness/artifact/
  delivery postcondition verifiers, Reports/run UI, recovery, and focused tests.

### Resource and economy contract

Process one target/completed fingerprint and reuse current prior reports and
stage artifacts. Generate/review once per unchanged candidate, rerun only the
failed later stage, and stop at the first missing current prerequisite or
unverified output.

### QA and independent review

- Test missing/failed/stale outcome reconciliation, incomplete source scope,
  stale prior reports, cognitive rejection, invalid/missing artifact or semantic
  projection, delivery/readback failure, reuse after late-stage failure, wrong
  role/lane, no shutdown side effect, and restart.
- Execute full delivery only on a disposable/authorized target; validate current
  live terminal prerequisites read-only elsewhere.
- Independent terminal-report review verifies exact sources, outcome posture,
  artifacts, limitations, delivery, and absence of lifecycle mutation.

### Acceptance

- One terminal report reaches current verified artifact and required delivery/
  readback posture with every stage, source, limitation, and prior-report input
  inspectable.
- Partial or failed late stages preserve valid earlier work and offer only the
  exact bounded recovery.
- The run remains active/not-shutdown and report readiness is visibly separate
  from stop permission.

### Negative tests

- Reject a terminal report from file existence, reviewer task completion,
  delivery alone, stale completion evidence, or missing required prior reports.
- Reject any terminal-report operation that pauses automations, changes
  lifecycle, or reports source stop permitted.

### Completion evidence

Pending.

### Stop

Stop before request-stop, automation pause, terminal shutdown, or final
cross-project acceptance.

---

## Block 24 — Request-stop and terminal shutdown

Status: `not-started`

### Objective

Request and verify terminal shutdown for one supervised run only after every
current outcome, issue, decision, successor, report, lifecycle, automation, and
owner gate permits source stop.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: give the operator an exact safe terminal control
  that explains what stops, what remains, and how current outcome and continuity
  permit shutdown.
- Potential capability loss or regression: a generic Stop, stale gate, missing
  successor, unverified report, or partial automation change could abandon work,
  violate ownership, or misstate completion.
- Protected-capability effect: preserves outcome-over-process completion,
  incident/decision/successor gates, report/delivery proof, lifecycle and
  automation postconditions, recovery/resume posture, Gmail ownership, and no
  destructive broad target selection.
- Architecture and operating-model effect: adds one terminal request/shutdown
  workflow that composes current owners and gates; it remains distinct from
  turn interrupt, pause/resume, and terminal report preparation.
- Tradeoff and source evidence: terminal shutdown requires the most deliberate
  preview and verification because the direct Factory request values reliable
  continuation and the supervision contract prohibits false completion.

### Inputs and dependencies

- Accepted Block 7 run/lifecycle/continuity workspace and Block 9 report view.
- Accepted Blocks 10 and 11 operation/task owners.
- Accepted Block 23 verified terminal report workflow.
- Current outcome, incident, decision, successor-transition, lifecycle,
  automation, report/delivery, and stop-gate contracts from Blocks 0 and 4.

### Required work

- Register `Request stop and terminal shutdown` only when the current target/
  mission fingerprint and every named gate can be previewed; provide no generic
  red Stop button.
- Preview current observable-outcome reconciliation, retained open items,
  incidents/decisions, same-target mission and successor-task posture, terminal
  report/delivery, lifecycle, automations/roles, Gmail ownership, what will stop,
  what remains, and recovery/resume consequences.
- Re-run every maintained gate at execute time. Deny on stale fingerprint,
  supported outcome gap, prohibited open head, incomplete required successor,
  unverified terminal report/delivery, missing owner, or lifecycle/automation
  mismatch.
- Request shutdown through the supervisor/automation/lifecycle owners and verify
  the terminal lifecycle record, required shutdown receipt, and actual bound
  automation state separately.
- Preserve partial/failure state without automatic retry; expose only the exact
  supported recovery or separately authorized compensating operation.
- Keep turn interruption, Block 18 pause/resume, Block 23 terminal report, and
  this terminal workflow visibly distinct in UI and history.

### Scope and non-goals

- In scope: one fully gated source stop and terminal supervision shutdown.
- Not in scope: turn interrupt, ordinary pause, report generation, issue/
  decision resolution, successor creation/work, or bulk/multi-project stop.
- Do not infer stop permission from task terminality, tracker status, commit,
  tests, report existence, or a green floor light.

### Deliverables and recorded state

- Terminal preview/gate packet, request and lifecycle/automation/receipt
  postcondition verifiers, specific run control, partial/recovery UI, and tests.

### Resource and economy contract

Resolve one target/mission and reuse current exact gate/report/outcome roots.
Execute once, poll only the named lifecycle/automation/receipt postconditions,
and stop at denial, partial, or unverified state without retrying or widening.

### QA and independent review

- Test every gate denial individually and in combination: outcome gap, retained
  incompatible work, open incident/decision, incomplete successor, stale/new
  mission, missing/unverified terminal report or delivery, lifecycle mismatch,
  automation partial failure, wrong target, stale preview, duplicate execute,
  restart, and recovery.
- Execute end to end only in the disposable terminal validation run or under
  exact direct authority for the selected real target.
- Independent terminal authority/outcome review verifies the complete gate
  packet and each postcondition on the frozen candidate.

### Acceptance

- The operator sees why the selected run is or is not stoppable, with every
  gating source and consequence inspectable before confirmation.
- An eligible run reaches matching terminal lifecycle, shutdown receipt, and
  bound automation state; a partial or denied run remains truthful/recoverable.
- No other target/group/task stops and no process proxy is accepted as current
  observable-outcome completion.

### Negative tests

- Reject shutdown with any current gate failure, stale source, incomplete
  successor, unverified terminal report/delivery, or partial automation/
  lifecycle postcondition.
- Reject a generic/bulk Stop, turn interrupt, ordinary pause, green light, or
  terminal task presented as this workflow.

### Completion evidence

Pending.

### Stop

Stop before final cross-project acceptance, release documentation, or claims
that the dashboard is ready.

---

## Block 25 — Integrated outcome validation and operator handoff

Status: `not-started`

### Objective

Prove the complete dashboard against current multi-project sources and real
bounded operations, close supported findings on the frozen candidate, and hand
off a reproducible local operating workflow.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates, documents, and
  hands off the capability selected and implemented in Blocks 0–24; it may fix
  mapped defects but must not add a new product surface or operating model.

### Inputs and dependencies

- Accepted Blocks 6–24 and all inherited accepted dependencies.
- One frozen release candidate commit, exact runtime/dependency lock, generated
  App Server compatibility root, and current source fixtures.
- At least three authorized registered local projects with collectively: an
  active task/run, historical accepted work, full-profile and inherited-core
  trackers, incidents/decisions/transitions, automations, and verified report
  history. Use a disposable registered Git project/run for consequence-bearing
  mutation proof unless direct authority names a real target.

### Required work

- Build a final source/feature matrix from the live environment and reconcile
  every capability in Section 2 as working, read-only, unavailable with exact
  reason, or intentionally out of scope. Remove or disable any control whose
  owner, gate, or postcondition cannot be proven.
- Run focused Python adapter/security/integrity tests; frontend TypeScript,
  lint/format, unit/component/axe tests; production build; and API/schema/
  generated-App-Server compatibility checks on the frozen candidate.
- Run current full-profile verification on this tracker and the accepted
  implementation completion evidence. Validate inherited trackers with their
  explicitly supported profile rather than rewriting history.
- Execute a multi-project browser matrix at 390×844, 768×1024, and
  1440×900 in light/dark modes. Cover all primary routes, project/run/task
  drill-downs, tracker review, metrics/reports, Admin/integration health,
  loading/empty/partial/error/stale/unavailable states, keyboard/focus, long
  content, source links, and no page-level horizontal overflow.
- In the disposable validation project, prove project registration, tracker
  authoring or read-only review as appropriate, bounded implementation start,
  supervision attach if supported, task continue/steer/interrupt distinctions,
  one safe advanced operation or its exact denied posture, and canonical
  postcondition display. Preserve artifacts and task/run IDs as evidence; clean
  up only through recoverable, authorized operations.
- Sample current real-project factory-floor/project/tracker/report projections
  against raw source IDs and direct validators. Confirm that at least one partial
  or unavailable integration produces honest degradation.
- Trace each sampled workspace from its visible UI region through `/api/v1` to
  the current primary-owner call and compare the returned identity, revision,
  fingerprint, coverage, and failure posture with that owner. Any runtime mock,
  demo row, direct browser source access, or duplicated owner interpretation is
  a release blocker.
- Measure the frozen representative corpus: at least the current live project/
  target/report volume and a deterministic 2× synthetic history expansion. The
  factory floor must become interactive without loading all historical bodies;
  visible interactions remain responsive, paging/bounds hold, and memory/event
  buffers obey their declared limits. Record measurements and hardware rather
  than asserting universal latency.
- Perform an independent product-capability, UI/accessibility, and authority/
  outcome review after all mutating corrections. Map each finding to exact
  change, focused proof, mapped proof, and fresh frozen-revision recheck.
- Update `README.md` with install/run/data-source/control/troubleshooting
  guidance, document compatibility and recovery, add the implemented changelog
  entry, and provide a concise operator runbook including what the dashboard
  cannot authorize or prove.

### Scope and non-goals

- In scope: current integrated proof, mapped remediation, documentation,
  compatibility/recovery posture, and local handoff.
- Not in scope: new features, remote deployment, aesthetic expansion, unrelated
  source-owner correction, or closing open external project work.
- Any newly desired capability becomes a separate direct-authority tracker;
  final QA is not permission for feature creep.

### Deliverables and recorded state

- Frozen release candidate and lock/schema roots; complete validation logs;
  browser screenshots/traces where useful; live source cross-check packet;
  disposable-operation evidence; independent reviews and closure matrix;
  updated README/changelog/runbook; and filled completion evidence in this
  tracker.

### Resource and economy contract

Finish mapped implementation/review changes before broad tests and browser
validation. Run the full matrix once per frozen candidate; after a correction,
rerun focused proof plus only affected mapped suites/views, then one final
smoke/currentness check. Use the fixed representative corpus and three viewports;
widen only for a reproduced supported failure. Do not create paid model/report
work solely to inflate coverage.

### QA and independent review

- Mechanical proof includes exact commands/results for tracker verifier,
  Python/unit/integrity/security tests, TypeScript/lint/unit/axe, production
  build, App Server compatibility, and browser matrix.
- Semantic proof uses reviewers different from the implementation owner for
  target-product capability, authority/outcome semantics, and maintained UI/
  accessibility. Bind each review to the frozen commit and source roots.
- Final outcome audit samples visible claims back to exact current project,
  tracker, task, supervision, automation, Git, and report sources.

### Acceptance

- The complete Section 1 outcome is observed on the frozen candidate across at
  least three projects and the disposable operation project, with no unresolved
  supported capability, authority, accessibility, integrity, or outcome gap.
- The factory floor accounts for every discoverable running implementation and
  supervisor group, proves each target relation or anomaly, and correctly shows
  traffic-light reason, current issue, last/next check, action history, and
  latest conclusion against exact live sources.
- All named frontend stack/runtime owners are present and documented; local
  startup from a clean dependency install is reproducible.
- All enabled controls have current owner/gate/postcondition proof; unsupported
  controls are absent or disabled with exact reasons.
- Fresh browser evidence verifies all named views/interactions/viewports and
  current source cross-checks verify displayed truth.
- Every sampled operational row and enabled action is traceable through
  `/api/v1` to one current primary owner; disabled or unavailable integrations
  expose their exact owner-local reason and never substitute demonstration data.
- Documentation and changelog distinguish implemented behavior, read-only
  projections, unavailable/planned capability, estimates, and out-of-scope work.

### Negative tests

- Reject release when any primary route is unverified at a maintained viewport,
  a control is inert or lacks a postcondition, partial source loss becomes a
  healthy/zero state, or an outcome claim rests only on process evidence.
- Reject stale test/review/browser evidence after the candidate or mapped source
  contract changes.

### Completion evidence

Pending.

### Stop

Stop after the documented local dashboard is independently accepted and pushed;
do not add remote hosting, multi-user administration, or adjacent Factory
capabilities.

## 8. Verification matrix

| Capability/invariant | Focused proof | Mapped proof | Outcome evidence |
|---|---|---|---|
| Local runtime/reference stack | Python health/static tests; manifest/lock checks; TypeScript/build | clean install, server start, shell browser matrix | operator reaches the built dashboard locally with exact stack/integration health |
| Primary-owner API integration | per-adapter HTTP contract tests against the same owner input/command and structured source failure | three-project live owner-to-API cross-check across tracker/Git, supervision/reporting/metrics, App Server, and one gated mutation | every displayed operational row and enabled action traces through `/api/v1` to one current owner with version/revision, fingerprint, coverage, limitations, and no runtime demo fallback |
| Project boundary/catalog | store/path/currentness unit tests | multi-project restart and partial-source integration | three projects register/archive/restore without copied operational truth or filesystem escape |
| Tracker truth | parser fixtures plus maintained verifier JSON | full/core/malformed/dirty/stale tracker comparison | reviewer reaches exact capability, Block, evidence, diagnostics, and source |
| Supervision/history | ledger/policy/report validators and corrupt/partial fixtures | live target source cross-check | active and historical run claims match exact event/incident/decision/transition records |
| Metrics/reports | definition, unit, coverage, estimate, artifact-path tests | cross-project/report comparison against manifests | each displayed number explains period, denominator, source, limitations, and estimate posture |
| Codex task integration | fake App Server protocol suite | version-gated live list/read/disposable task smoke | task/turn/items/approval/input state and controls match the official live owner |
| Factory Floor/UI | component/axe/topology/light/conclusion state tests | three-project, three-viewport, light/dark Playwright matrix | operator identifies each implementation/supervisor/target, operating reason, issues, actions, conclusions, history, and freshness and drills to exact sources |
| Administrative safety | schema, nonce/origin, preview, replay, stale, route-gate, postcondition tests | disposable workflow operations and denied advanced paths | enabled action has intended owner consequence; denied/unavailable action fails closed |
| Supervision check and review actions | watcher/reviewer role, route, candidate, duplicate, and postcondition tests | disposable check plus checkpoint/meta/issue review requests | mechanical checks and semantic conclusions remain separately current and owner-bound |
| Policy and pause/resume administration | policy/automation dual-state, lifecycle, stale-preview, and preserved-state tests | disposable policy diff and pause/resume cycles | policy/cadence and lifecycle operations remain separately owned and prove both canonical postconditions |
| Mission and target/tracker binding repair | exact-root/path/tuple, policy-history, duplicate-group, and mission-overwrite tests | one disposable malformed mission/target/tracker tuple | one compatible tuple is repaired through bind/policy without changing intent or creating a second root |
| Role-task binding repair | role eligibility, task lifecycle, route-purpose, ambiguity, and dual-postcondition tests | one disposable missing or mismatched role task | one role resolves to one exact eligible task without changing other roles or automations |
| Automation binding repair | ID/target/role/schedule, policy/config dual-state, duplicate-role, and direct-write tests | one disposable mismatched automation binding | actual automation and canonical policy agree without cadence creep or unrelated reconciliation |
| Mission and task continuity | mission-root/history and successor-transition phase/gate tests | disposable same-target mission succession and successor-task transition | predecessor history is preserved, successor currentness is isolated, and source stop waits for work start |
| Weekly reporting | prepare/review/finalize/verify/display/delivery stage tests | current authorized report bundle and late-stage recovery | verified weekly artifact, limitations, and delivery posture resolve to exact sources without regeneration waste |
| Factory evolution | eligibility, immutable artifact, role-separation, external-implementation, comparison, disposition, and verify tests | disposable eligible cycle through each disposition with separately supplied candidate evidence | verified disposition remains derived evidence and performs no implementation, adoption, deployment, rollback, or outcome mutation |
| Terminal reporting | outcome/currentness/prior-report/artifact/delivery tests | disposable terminal bundle with late-stage recovery | current verified delivered report exists without pausing or stopping the run |
| Terminal lifecycle/outcome | outcome, incident, decision, successor, report, lifecycle, automation, and receipt gates | disposable allowed and denied shutdown runs | no interrupt/pause/report/task state is mislabeled as stop permission or outcome completion |
| Release/currentness | full tracker verifier, all mapped suites, diff/build checks | independent exact-commit product/UI/authority reviews | zero supported gaps on frozen current candidate and documented local handoff |

## 9. Final completion definition

This tracker is complete only when all Blocks are `accepted`, their exact
completion evidence is filled, and the final frozen candidate demonstrates the
requested cross-project monitoring, tracker/progress review, metrics, and real
owner-gated administration in current observable behavior. The dashboard must
remain local, minimal, progressively disclosed, and truthful under partial
failure. A passing test suite, commit/push, App Server task, verified report,
terminal run, or completed tracker row is necessary evidence where mapped but
is never sufficient by itself.

Retained planned or unavailable capabilities are allowed only when they are not
required by the governing request, are visibly labeled with exact prerequisites,
and no enabled control pretends to provide them. Any supported gap in a named
view, interaction, authority boundary, canonical postcondition, responsive
viewport, or source claim keeps the tracker open.
