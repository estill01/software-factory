# Software Factory Operations Dashboard Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–31
- Repository: `https://github.com/estill01/software-factory.git`
- Governing objective: direct-user item
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`
  governs the dashboard request first stated in Codex task
  `019fe547-e054-7ca0-9940-ec4aa146df78`, 2026-08-08: provide a dashboard that
  monitors current and historical Software Factory work and metrics across
  projects, supports administration and operation, and makes implementation
  trackers and progress reviewable; use the frontend stack recovered from task
  `019fc4d5-2791-7823-997e-e7a38163ef2a`. Direct refinement in the same task,
  2026-08-09: make the center a factory floor that shows running
  implementations and supervisors, what each supervises, overall state/issues,
  red/green-style operating posture, actions, conclusions, and history at a
  glance. Routed design provenance from task
  `019fef2b-3f0d-7d02-96d5-d1bf3ff1a62d`, 2026-08-10, corroborates selective
  adaptation of the supplied Beautiful UI Task Rows, Filter Table, and Diff
  Table source into the existing sparse shell; it is not authority. Exact
  tracker totals and separate current active-Block claims refine the already
  accepted Block 6 Factory Floor truth and Block 8 tracker-progress contracts.
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
   Block or independently reported active Blocks?
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
what that group is supervising, exact tracker total, every current source-
labeled active Block/checkpoint, last and next check, open issue posture, recent
supervisory action, and latest evidence-bound conclusion.

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
  diagnostics, Git currentness, exact parsed total, separately sourced current
  active-Block claims, and mapped execution state without rewriting tracker
  truth;
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
  `https://learn.chatgpt.com/docs/app-server`; plus the selected source supplied
  by <https://beautiful-ui-five.vercel.app/> through its per-component `Copy`
  actions and frozen in Blocks 17–19 and 21.
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
| Factory Floor | compact expandable running/recent implementation rows paired without identity merging to supervisor groups, missions, roles, and targets; exact/partial status-filter counts; red/amber/green/neutral operating posture; last/next check; recent action and conclusion; needs attention; recent accepted work; freshness; bounded cross-project KPIs | composed projections with links to exact owners |
| Projects | register/archive discovery metadata; list repositories, trackers, tasks, runs, reports, current work, and history | dashboard catalog for discovery only; project sources for truth |
| Project/run detail | mission, current Block/checkpoint, event timeline, supervisor group/roles/targets, checks/actions/conclusions, incidents, decisions, transitions, schedules, reports, and outcome posture | supervision artifacts, App Server, Git, tracker |
| Trackers | discovery; exact/partial high-signal filter counts; full/core verifier posture; capability frame; dependency order; Block details; evidence; bounded semantic source diffs; Git currentness; mapped run progress | tracker Markdown, verifier, Git, bound run records |
| Metrics | throughput, activity, availability, reviews, incidents, resolution time, resource estimates, coverage, and limitations with filtering and drill-down | verified report metrics and canonical source records |
| Reports | Markdown/PDF/JSON/manifest inventory, preview, download, verification, historical comparison | maintained report/evolution owners |
| Tasks | live status, turns, streamed items, approvals/input, continue, steer, interrupt, and open/deep-link identity | Codex App Server |
| Start work | author/review a tracker; implement selected Block range; attach supervision | the named skill in a Codex task, then its canonical artifacts |
| Supervision admin | status; owner-supplied semantic preview diffs; bind/adjust request; policy/schedule projection; report/evolution workflow; pause/resume/request-stop/terminal workflow | supervisor, automation, report, evolution, and lifecycle owners |
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
- Primary operational rows use one keyboard-native collapsed disclosure for
  identity, lifecycle, Block/posture, attention, and freshness, with exact
  checkpoints/issues/recovery/actions/conclusions in expansion. High-signal
  chip counts are exact only for complete untruncated owner coverage and
  otherwise say returned/lower-bound, partial, or unavailable.
- Tracker and consequential-operation semantic diffs show explicit added,
  removed, changed, and materially preserved rows with owner/currentness roots
  and non-color cues. They are read-only evidence views, never editors,
  confirmations, or acceptance paths.
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
| Beautiful UI Task Rows | `components/TaskRows.tsx`; copied source SHA-256 `665e31820b041600662fcffff044d6a4994ecd18059d5e8ef1026251bf996b0e` | adapt | 17 | retain compact disclosure grammar; remove demo timers/data/retry and bind typed Factory Floor truth |
| Beautiful UI Filter Table | `components/FilterTable.tsx`; copied source SHA-256 `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4` | adapt | 17, 18 | retain count-chip/filter interaction; add exact/partial/unavailable coverage semantics |
| Beautiful UI Diff Table | `components/DiffTable.tsx`; copied source SHA-256 `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2` | adapt | 19, 21 | retain compact semantic row grammar; remove demo stages/data and bind Git/operation owners |
| Beautiful UI Sidebar/Chat/Prompt/Recommendation and other gallery components | gallery inspected 2026-08-10 | not adopted | 17–19, 21 | current sparse shell and maintained controls are a better product fit; do not add cosmetic breadth |
| Adaptive decision/evolution tracker | plan current at implementation time | not-adopted as live capability | 0, 28 | show planned/unavailable until independently accepted implementation exists |
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

1. Execute Blocks 0–31 in dependency order. Parallel work is allowed only
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
| 2 | Project catalog and bounded discovery | 1 | `accepted` |
| 3 | Tracker truth and Git-currentness projection | 2 | `accepted` |
| 4 | Supervision, automation, report, and metrics projection | 2 | `accepted` |
| 5 | Codex task and App Server adapter | 1 | `accepted` |
| 6 | Cross-project factory floor | 3, 4, 5 | `accepted` |
| 7 | Project and run workspaces | 6 | `accepted` |
| 8 | Tracker review and progress workspace | 3, 6 | `accepted` |
| 9 | Metrics and report history workspace | 4, 6 | `accepted` |
| 10 | Gated administrative operation framework | 2, 4, 5 | `accepted` |
| 11 | Author, implement, supervise, and task-control workflows | 8, 10 | `accepted` |
| 12 | On-demand mechanical supervision checks | 7, 10, 11 | `accepted` |
| 13 | Semantic supervision review requests | 7, 10, 11 | `accepted` |
| 14 | Supervision policy and cadence administration | 7, 10, 11 | `accepted` |
| 15 | Mission and target/tracker binding repair | 7, 10, 11 | `accepted` |
| 16 | Role-task binding repair | 7, 10, 11 | `accepted` |
| 17 | Factory Floor operational rows and exact count filters | 6, 7 | `accepted` |
| 18 | Tracker review queue and exact count filters | 3, 8 | `accepted` |
| 19 | Tracker semantic source diffs | 3, 8 | `accepted` |
| 20 | Automation binding repair | 7, 10, 11 | `accepted` |
| 21 | Owner-backed operation semantic diffs | 10, 14, 15, 16, 19, 20 | `accepted` |
| 22 | Supervision pause | 7, 10, 11 | `accepted` |
| 23 | Canonical supervision-resume lifecycle owner | 22 | `accepted` |
| 24 | Supervision resume | 7, 10, 11, 22, 23 | `accepted` |
| 25 | Same-target mission succession | 7, 10, 11 | `accepted` |
| 26 | Successor-task continuity | 7, 10, 11 | `accepted` |
| 27 | Weekly supervision report workflow | 9, 10, 11, 13 | `accepted` |
| 28 | Factory evolution evaluation and disposition | 9, 10, 11, 13 | `accepted` |
| 29 | Terminal report workflow | 9, 10, 11, 13, 27 | `in-progress` |
| 30 | Request-stop and terminal shutdown | 7, 9, 10, 11, 29 | `not-started` |
| 31 | Integrated outcome validation and operator handoff | 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 | `not-started` |

Required order:

```text
0 → 1 → 2 → {3, 4}
    └───────→ 5
{3, 4, 5} → 6 → 7
{3, 6} → 8
{4, 6} → 9
{2, 4, 5} → 10
{8, 10} → 11
{6, 7} → 17
{3, 8} → {18, 19}
{7, 10, 11} → {12, 13, 14, 15, 16, 20, 22, 25, 26}
{10, 14, 15, 16, 19, 20} → 21
22 → 23
{7, 10, 11, 22, 23} → 24
{9, 10, 11, 13} → {27, 28}
{9, 10, 11, 13, 27} → 29
{7, 9, 10, 11, 29} → 30
{6–30} → 31
```

Blocks with satisfied direct dependencies may proceed concurrently; exact order
is governed by the dependency table, not diagram layout.

Renumbering note: commit `0fe280cc1deac763b906755265c7d0e53307ff0c`
is preserved as the rejected predecessor for incident
`INC-20260809-073305-B81DCB`. Its old Block 12 was split into current Blocks
12–16, 20, and 22–30 at independent owner, acceptance, recovery, and Stop
boundaries; its old Block 13 moved mechanically to current Block 31. Blocks
0–11 remain substantively unchanged. Exact-review-rejected successor commit
`cbe7c55cc2eae20d3c2bd70704cf5a5fc93546e4` is also preserved: its Block 15
was split into current Blocks 15, 16, and 20, its Block 16 split into current
Blocks 22–24, its Blocks 17–19 moved to current Blocks 25–27, its Block 20 was
narrowed to current Block 28's derived evaluation/disposition owner, and its
Blocks 21–23 moved to current Blocks 29–31. Prior structural verification and
review remain diagnostic rather than current completion proof.

Beautiful UI source-baseline amendment note: the 2026-08-10 direct design
steer first produced rejected authoring commit `8fb09cc9dfe2d5207f9cc3992e7a90924bee0689`,
whose Block 18 combined independently acceptable tracker queue/count discovery
and selected-tracker source-diff inspection. Successor
`027848a591ba78a28a14bccea11382865b230ec3` closed that structural finding but
its diagnostic exact review rejected the routed side-task/action SHA as an
authority basis. The corrected revision keeps the Factory Floor surface in
current Block 17, splits tracker queue/count review and tracker source diffs into
current Blocks 18 and 19, and keeps owner-backed operation diffs in current
Block 21. The former Block 17 moved to current Block 20, former Block 18 split
into current Blocks 22–24, former Blocks 19–25 moved to current Blocks 25–31,
and accepted Blocks 0–16 remain substantively unchanged except mechanically
affected forward references and range language.
Exact-total and plural active-claim presentation is a narrow
refinement of accepted Block 6's current Block/checkpoint, exact status-count,
source-disagreement, and source-drill-down requirements and accepted Block 8's
exact status counts, current/eligible Block, mapped-active-run, and active-node
truth requirements. Its authority remains direct-user item 44 and mission root
`45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
routed side-task provenance supplies no authority. Historical evidence that
names a then-current range or old Block numbers remains evidence for that exact
revision, not current numbering.

Lifecycle-owner amendment note: the Block 22 capability review reproduced the
accepted Block 0 split between supported semantic pause and unavailable resume.
The former combined Block 22 is therefore narrowed to current Block 22 pause;
current Block 23 implements and independently accepts the missing canonical
resume lifecycle owner; and current Block 24 exposes resume only after that
owner exists. Former Blocks 23–29 move mechanically to current Blocks 25–31.
Accepted Blocks 0–21 remain substantively unchanged except mechanically affected
forward references and sequence/count language; historical evidence keeps the
numbers current at its own revision.
Independent exact authoring review accepted commit
`99654a738bad16bc37cf2d751a8a25d0cadfe19c`, tree
`5a7c81b78b566ce3642be5eaf991fb57958d4339`, with no material findings. The
reviewer independently confirmed the pause, resume-owner, and dashboard-resume
slices have distinct owner, acceptance, recovery, and Stop boundaries; resolved
the terminal-only `supervision_pause_permitted` flag separately from ordinary
user-requested pause authority; and reproduced the 32-Block full verifier with
0 errors/warnings, all 30 verifier tests, five relative links, focused diff,
history preservation, remote identity, and no implementation or live
supervision action.

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

Status: `accepted`

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
- Accepted candidate: exact pushed commit
  `dba8274f3f06bbd48fbf9c7703f87ce0baa40448`, tree
  `264c3ce1d05409041c4b84a794ec83f64224d3ad`, parent
  `f1c3e5702db4fd1048e4cf4bc25fe75b2b449b8e`; the 28-file focused diff
  remained unchanged during exact-revision review. Authoritative candidate
  blobs were tracker `6d950479b8f13cb2747e56632884412472f30091`,
  changelog `f3d692605fd17b6897060431cfa976cd66870d1e`, catalog adapter
  `2f401cc149ca298144d5f4d00e81fc6c60acac46`, and Admin catalog UI
  `8a4f6d02e9215a38b3230a654913e9c4db32b8b1`.
- Delivered behavior: the Python loopback service exposes versioned project
  list/detail/register/update/archive/unarchive APIs over an atomically written
  schema-version-1 catalog. The catalog admits only ID, label, canonical Git
  root, tracker patterns, description, and archived posture; enforces owner-only
  current/previous files and directory, deterministic ordering, optimistic
  fingerprints, recovery-read-only posture, canonical/non-overlapping roots,
  bounded tracker-path candidates, and per-project partial failure. React/Zod
  Admin and Projects views expose the same typed boundary and never parse
  tracker content or copy run, task, supervision, report, or completion truth.
- UI abstraction correction: one compact route-specific `h1` now lives in the
  persistent application chrome. Route marketing heroes, explanatory page
  subheaders, and redundant sidebar narration were removed; only functional
  section and state labels remain. Tests enforce one `h1`, keyboard/accessibility
  behavior, and no maintained-viewport horizontal overflow.
- Validation: Python passed 12 tests with `ResourceWarning` promoted to errors;
  TypeScript/Vitest passed 13 tests across 5 files; the production build passed;
  and Playwright passed 18 cases across desktop, tablet, and mobile. The full
  tracker verifier passed Blocks 0–25 with 0 errors and 0 warnings, all 30
  verifier tests passed, 22 implementer-checked local Markdown targets resolved,
  and exact candidate `git diff --check` passed.
- Live outcome proof: an isolated exact-server exercise registered three
  canonical Git repositories, hid one from Projects by archiving it, restored
  it, then retained two healthy projects while one missing root remained visibly
  unavailable. Current and previous catalog files were `0600` in a `0700`
  directory. A deliberately pre-created `0755` catalog directory failed before
  mutation with structured `unsafe_catalog_permissions` rather than weakening
  the storage boundary.
- Independent review: `tracker_exact_review` accepted exact `dba8274` with no
  material findings after reproducing Python 12/12, frontend 13/13, build,
  Playwright 18/18, full-profile tracker verification, 20 relative-link checks,
  diff checks, and the live three-repository/partial-failure workflow. It also
  accepted the requested future data-backing amendment: browser to loopback
  `/api/v1` to closed typed adapter to maintained owner, with no duplicate
  generic backend Block or overall-completion claim.
- Resource and Stop posture: discovery remains confined to registered roots,
  configured bounded globs, and Git metadata. No tracker content was parsed and
  no supervision, task, report, metric, or lifecycle state was aggregated.
- Post-block audit: `accepted`; all Block 2 acceptance and negative conditions
  were demonstrated on the reviewed revision.
- Git durability: a non-force push advanced `origin/codex/evolution-mvp`
  through acceptance-evidence checkpoint
  `38ad817b3b951c25be1629ffa0a40e084acb7d11`, whose tracker blob is
  `01053379da3bc7eae36c3be89245c0a1d6994558`; local and remote matched with
  `0 0` divergence. This evidence-finalization successor records that durable
  checkpoint and is included in the immediate non-force push before Block 3
  implementation changes begin.

### Stop

Stop before parsing tracker content or aggregating supervision/task state.

---

## Block 3 — Tracker truth and Git-currentness projection

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 2 candidate
  `dba8274f3f06bbd48fbf9c7703f87ce0baa40448` and acceptance-evidence
  checkpoint `38ad817b3b951c25be1629ffa0a40e084acb7d11` under direct-user item 44
  and mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  No new mission, successor task, routed authority, or manual resume was used.
- Candidate preparation: added a closed read-only Python tracker/Git adapter,
  deterministic list/detail identities and `/api/v1/trackers` routes, strict
  Zod list/detail contracts, exact source ranges/raw-open metadata, and
  source-local partial failure. The adapter reuses the maintained verifier,
  batches Git HEAD/index/tree/status/history/upstream inspection by repository,
  and caches analysis only by tracker content, verifier content, and profile.
- Exact profile posture: newly authored trackers fail closed to `full`; the
  inherited evolution and tracker-authoring trackers receive `core` only at
  the exact Block-0-approved path and SHA-256 roots. Full/core, invalid, dirty,
  staged, untracked, stale-bound, completed-with-open-items, and unavailable
  cases remain distinct. Invalid verifier output gates derived eligibility,
  and no percentage, synthetic green summary, or duplicate truth owner was
  added.
- Source validation: 17 Python tests passed with `ResourceWarning` promoted to
  errors; 18 TypeScript/Vitest tests and the production build passed; and 18
  Playwright cases passed across desktop, tablet, and mobile. The live 8787
  server projected all four registered repository trackers through the exact
  Zod contracts and reproduced the maintained verifier commands/results as
  full 14 Blocks, inherited core 7 Blocks, full 26 Blocks, and inherited core
  5 Blocks. For every live tracker the raw and committed content hashes matched
  and Git posture was current.
- UI abstraction correction: shared unavailable-page narration is optional,
  stale “tracker not connected” wording was removed, and the Trackers route
  remains a sparse unavailable workspace rather than prematurely rendering a
  tracker page. The existing single compact route `h1` contract remains intact.
- Authority and Stop posture: tracker Markdown and Git remain the writers;
  this slice performs no tracker edit, status transition, Block acceptance,
  task start, tracker-page construction, supervision read, or mutation.
- Accepted candidate: exact pushed commit
  `796de4ff6835f6bc9cd2ae4fef74bf077439c3f0`, tree
  `d56dfd5740344f0ab69a6a6873d06c7d9242c8f2`, parent
  `2f73e9be91e1e4c36b7e6022777b230c1c7a72c9`. Authoritative candidate blobs
  were Python tracker adapter `e1a4180b27b9864fcfda2ea9ebfa932a948477d1`,
  Zod tracker client `eaf06fc780c9453d952d9c1d8dc9271bb321e6e0`, tracker
  `415751be57562d757e9ebad7563ff85d92a2ebc0`, and changelog
  `44650c25ad9496a298fe0c65e8161699ad48a340`.
- Exact validation: Python passed 17/17 with `ResourceWarning` promoted to
  errors; TypeScript/Vitest passed 18/18 across 6 files; the production build
  and Playwright 18/18 across desktop, tablet, and mobile passed. The full
  tracker verifier passed Blocks 0–25 with 0 errors and 0 warnings, its 30
  verifier tests passed, local documentation links resolved, and
  `git diff --check` passed. Live exact-candidate projection matched direct
  verifier JSON for four registered trackers (full 14, inherited core 7, full
  26, inherited core 5), including identical raw/source/committed hashes and
  current Git posture.
- Independent review: `tracker_exact_review` accepted exact candidate
  `796de4ff6835f6bc9cd2ae4fef74bf077439c3f0` with no material findings after
  reproducing the mapped suites and live exact-clone projection. It confirmed
  that the implementation reuses the maintained verifier and Git owners behind
  the loopback typed API, creates no duplicate parser authority or database,
  and performs no tracker UI, mutation, acceptance, or task-start work.
- Post-block audit: `accepted`; all Block 3 acceptance and negative conditions
  were demonstrated on the exact reviewed revision, including selective cache
  invalidation and preserved invalid/dirty/stale/partial distinctions.
- Git durability: a non-force push advanced `origin/codex/evolution-mvp`
  through acceptance-evidence checkpoint
  `3516af68e34584a1b87bf41c48c209e6b92d3710`, tree
  `2f74b5389f22c8e9dc8c734b3a49b4a9792c461c`, whose tracker blob is
  `4a29c457ec45e03c090a7440644cdc61182c2ef0`; local and remote matched at
  `0 0` divergence. This evidence-finalization successor records that durable
  checkpoint and is included in the immediate non-force push before Block 4
  implementation changes begin.

### Stop

Stop before building tracker pages or initiating authoring/implementation tasks.

---

## Block 4 — Supervision, automation, report, and metrics projection

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 3 candidate
  `796de4ff6835f6bc9cd2ae4fef74bf077439c3f0` under direct-user item 44 and
  mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Exact Block 3 acceptance-evidence checkpoint
  `3516af68e34584a1b87bf41c48c209e6b92d3710` and tracker blob
  `4a29c457ec45e03c090a7440644cdc61182c2ef0` were non-force pushed with local
  and remote at `0 0` divergence before implementation changes began. No new
  mission, successor task, routed authority, or manual resume was used.
- Delivered projection: added a bounded read-only Python adapter and closed Zod
  contracts for `/api/v1/runs`, run detail, reports, and metrics. It discovers
  only configured supervision and automation roots; validates policy/history/
  event chains through the maintained supervision owner; verifies weekly,
  terminal, and evolution bundles through their maintained owners; and keeps
  every source-local failure visible without creating a dashboard-owned
  operations ledger.
- Currentness and truth posture: active-mission issues, decisions, conclusions,
  metrics, lifecycle, and project binding are partitioned from predecessor
  missions. Supervisor roles, tasks, automations, schedules, bindings,
  unmonitored projects, orphans, duplicates, unavailable sources, and report
  limitations stay explicit. Mechanical activity is separate from semantic
  conclusions; only dispositive `resolved` or `safe-deferred` decision records
  enter the conclusion stream. Actor attribution and live task state remain
  unavailable rather than inferred until Block 5.
- Health, metric, and privacy posture: transparent precedence facts derive
  red/amber/green/neutral lights without persisting them or calling green
  complete. Failed/blocked/stopped and evidence-insufficient completion remain
  red; paused and unavailable states remain neutral. Cross-run metrics aggregate
  only maintained additive dimensions, never synthesize percentiles, and label
  every cost value `API-equivalent estimate` with actual billing unavailable.
  Automation prompt bodies are never projected.
- Product-capability review: the selected architecture is the smallest
  capability-complete path: one loopback Python adapter over the maintained
  supervision/report/evolution owners and read-only automation manifests, with
  a closed React Zod boundary. A local duplicate parser/metric owner and a new
  generalized telemetry/database/registry were rejected as owner bypass and
  speculative platform expansion. The tradeoff is live validation and a large
  typed envelope; task state/cwd and exact task-actor attribution remain
  intentionally unavailable for Block 5.
- Initial candidate and mapped validation: exact pushed commit
  `6d2f9e4e8ee92465a0504986106d79cd48b92116`, tree
  `63d22118713541ed7ce6c121acc50a4161ef3dcf`, parent
  `68095fb`, passed the dashboard Python suite 37/37 with `ResourceWarning`
  fatal, maintained owner suites 196/196, frontend TypeScript/Vitest 21/21,
  production build, Playwright 18/18 across desktop/tablet/mobile, the
  full-profile tracker verifier with Blocks 0–25 and 0 errors/warnings, all 30
  verifier tests, 21 relative-link checks, and `git diff --check`.
- Live source proof: the exact service on loopback port 8787 projected six
  canonical supervision targets, one explicitly unmonitored registered
  project, source-bearing attention, current/predecessor mission partitioning,
  six covered metric rows, and verified report inventory. One weekly bundle
  independently reproduced maintained-owner verification with source root
  `62f881d083b0e64262f54a81c575d0dd7b7a3e4330ea363f5a2b9414aadfd032`
  and manifest root
  `8046f7ae7223f19c348c9e4205375208bfcf4944905183273272b160c2a9a227`;
  all four API envelopes parsed through the exact Zod contracts.
- Rejected history and bounded remediation: independent review rejected
  `6d2f9e4` because predecessor event paths could contaminate a successor's
  current project binding and non-dispositive decision phases were classified
  as conclusions. The exact successor changes only the operations adapter and
  focused tests: binding now reads current policy plus active-mission events,
  and decision conclusions are limited to `resolved`/`safe-deferred`.
  Regression coverage proves current-project movement, predecessor-only
  unassignment, and all eight maintained decision phases.
- Accepted candidate: exact pushed successor
  `afe3ed10de196bf7cff8f9e693368ba44d320886`, tree
  `dea0d93555808a716f7d814671b023fd8ccf321f`, parent `6d2f9e4`. Authoritative
  accepted blobs are operations adapter
  `784bfa63be3ac7a750ab8154e8ea140123f204ef`, focused operations tests
  `801b1c0808dbe3e478b9e57f5e07167ac7a1efb7`, Zod operations client
  `c7e04722d190c1d857af23c486c0e19fc7f3eece`, and changelog
  `f6ee8e0280cfbade96847826639ea74509428a98`.
- Fresh exact review: `tracker_exact_review` accepted `afe3ed1` with no material
  findings after reproducing current-project and predecessor-only binding,
  all decision-phase classifications, focused operations tests 21/21 with
  `ResourceWarning` fatal, the full dashboard Python suite 39/39, Ruff,
  `git diff --check`, clean isolated status, and local/upstream `0 0`
  divergence. Unchanged frontend, browser, owner, verifier, and link evidence
  remains bound to the rejected parent and the reviewed two-file delta.
- Authority and Stop posture: no task control, workflow page, owner mutation,
  report generation, lifecycle action, automation change, or reconciliation
  file was created. Direct-user item 44 and mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`
  remain the implementation authority; routed messages are start evidence only.
- Post-block audit: `accepted`; every Block 4 acceptance and negative condition
  is satisfied on the exact reviewed successor, with the two rejected findings
  retained as history and no overall implementation-completion claim.
- Git durability: candidate and correction were non-force pushed to
  `origin/codex/evolution-mvp` with local and remote at `0 0` divergence. The
  exact acceptance-evidence checkpoint is
  `7fdbc5db3c83b6a1c3c9f5b25e4321d1ba00f9e0`, tree
  `f9c0ec83869511fbd39275314d4a5515eb262ce3`, with tracker blob
  `b7e9701f1a5d8c9e8d690372275b76a9a4f0c876`. This evidence-finalization
  successor records that durable checkpoint and is included in the immediate
  non-force push before Block 5 implementation changes begin.

### Stop

Stop before rendering operator workspaces or mutating any supervision,
automation, report, or evolution owner.

---

## Block 5 — Codex task and App Server adapter

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 4 candidate
  `afe3ed10de196bf7cff8f9e693368ba44d320886` under direct-user item 44 and
  mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Block 4's exact acceptance-evidence checkpoint
  `7fdbc5db3c83b6a1c3c9f5b25e4321d1ba00f9e0` and tracker blob
  `b7e9701f1a5d8c9e8d690372275b76a9a4f0c876` were frozen and non-force pushed
  with local and remote at `0 0` divergence before implementation changes
  began. No new mission, successor task, routed authority, or manual resume is
  used.
- Accepted implementation: exact pushed commit
  `64e455f370814634d865f1635e673a3761abbab1`, tree
  `1c34cd7b4e7cd84cbd96b02f30bd1c7da5e7e549`, parent
  `9ba4c74954f6d8337f4475f296d848d94e269e51`. The accepted cumulative
  Block 5 scope is ten files: the version-gated Python client and HTTP adapter,
  deterministic fake server and Python tests, closed Zod/task-event contracts,
  compact Admin integration health, focused frontend tests, and the changelog.
  Authoritative accepted blobs include App Server client
  `e5c9df91fb58b820bcd982f281e77a4594538cac`, client tests
  `dc1c64b48cbdee812fe3f1dc5511f02f3fedc6c9`, HTTP adapter
  `e103a6a05749ba2431cf116c6b029af0f8be7de1`, task API
  `33504843d4e72ca015db6da210811600b3bdb91e`, Admin integration panel
  `4df23ec936b8130c0d286c9233bbd9f74245bceb`, and changelog
  `222aa6dffa967e5ef167c4cb6c3cbb6e50f7a360`.
- Delivered behavior: one long-lived exact-binary stdio child performs the
  official initialize handshake, validates every narrowed payload against the
  deterministic 273-file compatibility bundle, projects bounded task/turn/item
  and pending-request truth, binds operations only to registered canonical
  cwd, and exposes authenticated same-origin reads plus a resumable ephemeral
  SSE channel. Each capability is gated by its own schema family. Malformed,
  mismatched, duplicate, timed-out, incompatible, disconnected, missing-task,
  and unsupported-method states fail closed without suppressing independent
  file-backed monitoring. The stream preserves its consumed cursor, reconnects
  with capped backoff, reports retained-window gaps, and invalidates durable
  task/integration projections after a gap. Answered or stale callbacks are
  evicted before live callback capacity is refused.
- Restart/failure integrity: all request failures, transport writes, inbound
  responses, notifications, callbacks, callback-capacity responses, and
  callback resolutions carry their issuing connection generation. Final
  notification publication, callback insertion, request-event publication,
  and turn-completion staling recheck that generation at the side-effect
  linearization point. Forced interleavings prove an old request, cancellation,
  notification, approval callback, or turn-completion event cannot poison,
  terminate, publish into, or stale state owned by the healthy replacement
  child.
- Preserved rejection history: initial candidate
  `63520931c2defba72ab01b4b000c3ea83246d2b7` was rejected because malformed
  negotiated responses left capabilities enabled, SSE lacked cursor-preserving
  recovery/gap truth, and completed callback records exhausted lifetime
  capacity. Successor `688e9f89b78660005bdb7d0b4d78ccec5c2b0452`
  closed those rows but was rejected for a post-cancellation restart race;
  `a1fd4c57ce4856cf64957aeb3a75a25f04582e74` closed that race but was
  rejected for a pre-write cross-generation request;
  `9ba4c74954f6d8337f4475f296d848d94e269e51` generation-bound outbound
  transport but was rejected because old notifications and approval callbacks
  could still publish after restart. Each finding was corrected only at its
  reproduced boundary and all rejected commits remain durable diagnostic
  history, not acceptance evidence.
- Product-capability review: `consequential`; the exact 54-line capability
  frame hashed
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  Screen scraping, task-file guessing, a raw browser JSON-RPC bridge, and a
  general Codex client were rejected. The selected bounded option reuses the
  official installed App Server owner behind one closed Python adapter; no
  larger platform or database is justified. It preserves Codex task authority,
  recipient/cwd identity, approval and input fingerprints, same-origin gates,
  file-backed monitoring, and fail-closed feature availability. The accepted
  tradeoff is explicit compatibility maintenance for exact CLI/schema versions;
  Block 6 is the first named adjacent consumer and receives read-only typed
  projections rather than protocol access.
- Validation: final exact Python validation passed 59 tests with
  `ResourceWarning` promoted to errors and Ruff passed. Unchanged exact-parent
  evidence remained current: TypeScript/Vitest 30/30, production build,
  Playwright 18/18 across desktop/tablet/mobile, full tracker verification for
  Blocks 0-25 with 0 errors and 0 warnings, all 30 verifier tests, link checks,
  and `git diff --check`. Live exact-server proof on port 8787 reproduced
  installed `codex-cli 0.145.0`, 273 schemas and semantic root
  `757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`,
  returned current bounded tasks, and emitted replay-aware SSE `ready` plus
  generation-1 connection events. The earlier disposable bounded task/turn
  ended with its actual `usageLimitExceeded` result and was never relabeled
  successful.
- Independent exact-revision review: `block5_exact_review_retry` accepted
  exact `64e455f370814634d865f1635e673a3761abbab1` with no material finding or
  unclosed uncertainty after replaying every forced restart schedule, delayed
  turn-completion/callback interaction, capacity and resolution writes, the
  59-test Python suite, Ruff, exact diff/remote checks, the three original
  rejection rows, and the Block 5 Stop.
- Resource and Stop posture: one child, bounded task pages/items/events,
  deterministic schema reuse, and capped reconnect/callback buffers were
  preserved. The browser exposes task reads/events and adapter-only restart;
  it has no generic workflow start, task/turn mutation, prompt, approval/input
  response, lifecycle mutation, raw protocol, remote transport, model/tool
  setting, permission-profile, or forking control.
- Post-block audit: `accepted`; all acceptance and negative-test conditions are
  satisfied on the reviewed revision, with rejected evidence preserved and no
  implementation or lifecycle success inferred from process proxies.
- Git durability: non-force pushes advanced `origin/codex/evolution-mvp`
  through the exact accepted candidate; local and remote matched at `0 0`
  divergence before the evidence-only acceptance checkpoint
  `ad27bcbab8da0b201917c1da49cf4f8bf1748063`, tree
  `fa66e72cfe4661101b316da597e1428eb7e5ab12`, tracker blob
  `fe58e4faa7ef8fb9df932508cc6df3c4f406db9b`. That checkpoint was also
  non-force pushed before this durability-finalization successor and before
  Block 6 implementation began.

### Stop

Stop before exposing workflow-start or lifecycle mutation controls.

---

## Block 6 — Cross-project factory floor

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 5 durability
  checkpoint `faa771bfae70036bd86e6740bd02dd3725e8a47c`, tracker blob
  `83f3ae7ed039de8b128efd58277aa59b78727c89`, with accepted Blocks 3, 4,
  and 5 satisfying every dependency. Direct-user item 44, mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`,
  and the user's later `continue` preserve the full-tracker request; no routed
  packet, successor task, manual resume, or range contraction is used.
- Range-control currentness: the newly installed execution helper's transition
  gate returned `Implementation range is not canonically bound` because this
  run predates that helper contract and the live policy has no range record.
  The target did not manufacture a caller-selected binding, alter supervision
  files, or reinterpret a routed record as authority. The exact control-plane
  compatibility gap remains visible while dependency-safe work continues under
  the pre-existing direct full-tracker authority.
- Product-capability review: `consequential`; the exact capability frame is the
  same 54-line source hashed
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  A browser-side join of `/runs`, `/metrics`, `/tasks`, and `/trackers` was
  rejected because it would duplicate association/precedence logic and could
  silently choose a source winner. Expanding the maintained operations owner
  into task/tracker authority or adding a database/general analytics layer was
  also rejected. The selected bounded option is one read-only
  `/api/v1/factory-floor` composer at the existing loopback HTTP boundary over
  unchanged catalog, tracker, supervision, report/metric, and Codex adapters.
  It is view-specific, preserves every source identity/disagreement/limitation,
  exposes explicit truncation and coverage, and stores nothing. Block 7 is the
  one named adjacent consumer for source-bearing detail navigation; no Block 7
  detail is implemented here. The accepted tradeoff is a maintained composed
  response schema in exchange for one bounded request and one canonical place
  for display-only association rules.
- Accepted implementation: exact pushed successor
  `585467f49cc31d63758bddcd0f6c8d3133c69018`, tree
  `4ada75e537d139bef776e662f34cab992c9cd1f1`, parent
  `dad075c725fd22524811415a890c378b5eb42a67`. The cumulative Block 6
  implementation is fifteen files: one read-only Python composer and route,
  closed Zod/query/filter state, the four-region React Factory Floor and
  inspector, responsive styling, exact owner/three-project fixtures, mapped
  Python/frontend/browser tests, README, and changelog. Authoritative blobs
  include composer `2d501f45301bbb4c1ef914ef9e9332d418acb7ac`, HTTP owner
  `050f0c7230771f928dd7c71f6016205f3d329508`, Zod contract
  `83b8d3dc74541198280de2b5a7852ec85bf5ea74`, page
  `7a5c553e0ca1d2ae3e10bfd8e9d13067dd6d955a`, browser proof
  `e0f52f969af2416a3952b3dd1af28bdd051562b8`, README
  `9c85b804b02d299eabf25e64744d1c08acf36778`, and changelog
  `27a1e29076bfe2180d932c76eba5e6a383598aff`.
- Delivered behavior: `/api/v1/factory-floor` composes the unchanged catalog,
  tracker/Git, supervision/report/metric, and version-gated Codex task owners
  behind one loopback read. It stores no operational state and preserves
  exact/candidate/ambiguous/unavailable associations, cross-source
  disagreements, partial failures, source coverage, unmonitored work, orphaned
  supervisors, semantic conclusions, accepted tracker outcomes, and
  non-completion operating lights. The default page has exactly the four
  functional regions required by this Block, no marketing subheader, bounded
  filters and inspectors, hidden-critical disclosure, exact metric
  period/coverage, and source-bearing routes for every operational card.
- Supervisor and bound integrity: every row now exposes the supervisor-group
  identity plus the complete role-label summary. One obvious inspector retains
  each role type/label, thread ID, binding, live task posture, and automation
  posture alongside the exact supervised target. The attention contract
  carries total, returned, truncated, critical-total, critical-returned, and
  critical-omitted counts; summary totals use the uncapped composition and the
  UI visibly reports any critical item omitted by the API bound. Row-derived
  metrics likewise calculate over all composed rows before the display bound.
- Revision and cache integrity: the composed semantic revision includes every
  consumed task name, status, project binding, and recency field plus owner
  revisions/coverage, while excluding read-observation timestamps. Focused
  probes proved status/name/project/recency changes alter the revision and
  read-time-only refreshes do not. One two-second in-process cache coalesces
  simultaneous reads without becoming a canonical source or hiding an
  independent failure.
- Preserved rejection history: initial candidate
  `dad075c725fd22524811415a890c378b5eb42a67`, tree
  `afaee0a2dfd2f2d577f89cac3441c9f61f0243c7`, passed its mapped suites but was
  rejected because group/role identity was not rendered, the 80-item attention
  bound could silently omit critical work, and the task portion of the
  advertised semantic revision hashed IDs only. Successor `585467f` changed
  only the eight composer/schema/UI/test files at those reproduced boundaries;
  the rejected candidate remains diagnostic history, not acceptance evidence.
- Validation: final exact Ruff and Python validation passed 67 tests with
  `ResourceWarning` promoted to errors. TypeScript/Vitest passed 35 tests, the
  production build passed, and Playwright passed 24/24 across 1440x900,
  768x1024, and 390x844. The browser matrix covers populated three-project,
  loading, empty, partial, stale-source, error, dark-mode, filter, refresh,
  keyboard, inspector, accessibility, and overflow states. Full-profile
  verification passed Blocks 0-25 with 0 errors/warnings, all 30 verifier tests
  passed, 20 exact-review relative Markdown links resolved, and
  `git diff --check` passed.
- Live proof: the exact server on `http://127.0.0.1:8787/` projected the current
  registered project, six supervisor groups/rows, partial owner coverage,
  ranked attention, 24 bounded semantic conclusions, 13 accepted outcomes,
  and four trackers. The current dashboard row exposed its exact four-role
  group in the overview and every role/thread/binding/task/automation value in
  one inspector. The maintained three-project closed fixture separately proves
  cross-project row, issue, accepted-outcome, filter, and responsive behavior
  without mutating the canonical project catalog.
- Independent exact-revision review: `block6_exact_review` rejected
  `dad075c`, replayed each finding against successor `585467f`, and accepted
  exact commit/tree/parent `585467f` / `4ada75e` / `dad075c` with no material
  finding or unclosed uncertainty. It independently reproduced the 81-critical
  bound, semantic revision changes/stability, complete live supervisor-role
  inspection, exact frontend/backend suites, remote identity, and Block 6 Stop.
- Resource and Stop posture: one aggregate envelope, 80 displayed rows and
  attention records with exact omitted counts, 24 displayed conclusions and
  outcomes, a bounded 100-task source page, two-second cache, 20-second
  visible-tab polling, and drill-down-only detail are preserved. No project/run
  workspace, tracker/report detail, mutation, lifecycle control, workflow
  start, acceptance path, or canonical owner write was added.
- Post-block audit: `accepted`; the five operator questions are answerable from
  the overview or one obvious inspector, every acceptance and negative-test
  condition has exact proof, and no green/task/test/commit/report proxy is
  treated as implementation completion.
- Git durability: both rejected `dad075c` and accepted `585467f` were
  non-force pushed to `origin/codex/evolution-mvp`; local and remote matched at
  `0 0` divergence before the evidence-only acceptance checkpoint
  `c5426acec56788b9995398a843ded95251337304`, tree
  `0e648e9f3a4de1ec049bf53f835c59d4e7b7f6d2`, tracker blob
  `670a25bfb8bca6c47a1085444f366fe5668e6107`. That checkpoint was also
  non-force pushed and local/remote re-read at `0 0` before Block 7 began.

### Stop

Stop before adding project/run, tracker, report, or admin detail functionality.

---

## Block 7 — Project and run workspaces

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 6 acceptance
  checkpoint `c5426acec56788b9995398a843ded95251337304`, tree
  `0e648e9f3a4de1ec049bf53f835c59d4e7b7f6d2`, tracker blob
  `670a25bfb8bca6c47a1085444f366fe5668e6107`, with local and remote at
  `0 0` divergence. Direct-user item 44, mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`,
  and the user's later `continue` preserve the full-tracker request; no routed
  packet, successor task, manual resume, or range contraction is used.
- Product-capability review: `consequential`; the exact capability frame remains
  the 54-line source hashed
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  A dashboard database/denormalized history store, a generic cross-owner query
  engine, and expansion of the bounded Factory Floor envelope into full detail
  were rejected because each would duplicate current project, tracker, Git,
  supervision, report, metric, or Codex task authority. The selected bounded
  option uses route-owned TanStack queries and contextual inspectors over the
  already closed Block 2-5 list/detail contracts, preserving exact IDs,
  mission segments, source disagreement, pagination/truncation, and independent
  failures. Block 8 owns tracker deep review, Block 9 owns report analytics,
  and Block 10 owns mutations; none is pulled into this slice. The accepted
  tradeoff is visibly separate task/run/source panels instead of one synthetic
  lifecycle badge.
- Implementation checkpoint: pushed commit
  `898070849fa9d09b136ae10d93f375f3fefd6df5`, tree
  `5b76df56520650bd47ad6a3498c240f4cf0a4cc7`, parent
  `64b6cbb193090c46ab6040fdf30065da9c4c4f4f`, changelog blob
  `d72df2c68f6bb096ba48b1184fe4deb7bda31500`, run-workspace blob
  `192000ba5a90cdf54ee13d7eb8d96498fac36dad`, and focused
  mission-boundary-test blob `7c3094c4c8ed9fbabee1b350269a242d0f24589a`
  add only the Block 7 read-only project/run/supervisor/task workspaces,
  Factory Floor navigation/filter preservation, compact shared workspace UI,
  and mapped tests/changelog evidence. Local and upstream reread at `0 0`
  after the non-force push.
- Mission-history correction: source record `EVT-000075` identified that the
  selected predecessor could be rendered beside current run light/topology.
  The preserved successor keeps exact mission-scoped events, incidents,
  conclusions, policy hashes, source record, and timestamps, while current
  lifecycle/light, project/tracker binding, supervisor group, roles/tasks,
  automations, operating history, report association, metrics, source heads,
  owner revision, limitations, and current task reads are suppressed or
  explicitly unavailable. The focused component test seeds unique current-only
  sentinels and proves none render or trigger task API calls in predecessor
  mode; live predecessor `bc955bd48e01db90aeb98fa27256546e2ce1eaf289fd6f630f36374d3c89d810`
  displayed its 13-event segment and two historical incident records without
  current role, automation, light, project, report, or source-head carry-over.
- Delivered behavior: Projects exposes exact/lower-bound operational counts
  and contextual Overview/Work/Trackers/Reports/Sources tabs; run and supervisor
  routes expose mission segments, lifecycle/checkpoint evidence, issues,
  decisions, transitions, role and automation topology, policy hashes/bodies,
  derived operating history, conclusions, filters, stable anchors, reports,
  metrics, and source integrity; task routes expose bounded App Server,
  association, approval/input, turn, item, and capability state. Event/turn
  windows page newest-first without reordering, long text stays bounded, and
  command arguments, message/reasoning bodies, and raw errors remain withheld
  from the dashboard. Tracker/report deep review and every mutation remain
  outside the slice.
- Rejected review history: exact candidate
  `8613225745d079cea97c7c64446b333568b38a03`, tree
  `0649401b2ac2f7c597cd69381428ba7c5c6ab157`, was independently rejected
  after full mapped validation because an unknown mission deep link fell back
  to current state, a hashless predecessor fell back to the current policy
  hash, conflicting run/task project bindings were silently merged and labeled
  as one run binding, and a credential-bearing Git origin was rendered raw.
  The candidate remains reusable history and is not acceptance evidence.
- First focused successor: pushed commit
  `df51788203113701a8cf18c9eea2e375b5b98a1d`, tree
  `f2ede4d45ee0d782c5f9065e74bdc53a58188041`, parent
  `8613225745d079cea97c7c64446b333568b38a03`, workspace-data blob
  `863d86f629dbbb2f4b9062d79915b736722327a7`, run-workspace blob
  `ac230cb8376eff76558bda020d5dbac85eabcff8`, project-workspace blob
  `c12ea8effa971e4bd89ee22f6d5e8e606a7dd251`, and task-workspace blob
  `c7b8afdc617029f6120c6b6ed96873d16b15d1ea` change only eight cited Block 7
  frontend/test files. Explicit unknown missions now fail closed without task
  reads or current projections; predecessor hashes have no current fallback;
  canonical run binding wins association while all run/task/Floor claims are
  separately listed as degraded disagreements; and Git origin display retains
  only a credential-free host with path/credential withholding. Focused tests
  use unknown roots, empty historical hash arrays, contradictory `alpha`/`beta`
  bindings, and HTTP/SSH/SCP origins containing `SUPERSECRET`/`SECRET`. The
  non-force push reread local/upstream at `0 0`.
- Second rejected review history: exact candidate
  `21c6e621982ca975854ed70515ad45c7671ad601`, tree
  `61d814deda13a9fff81a518449d0234aa9c05163`, parent
  `df51788203113701a8cf18c9eea2e375b5b98a1d`, and tracker blob
  `4bd4bcb3ab386e84a8337b3a247ffb6795bd4da8` was independently rejected
  after the reviewer reproduced a canonical run binding to `beta` beside an
  exact task/Factory Floor claim to `software-factory`. Project Overview
  incorrectly reported one exact run while Work correctly reported `0 exact ·
  1 disagreement`. Unknown-mission, hashless-predecessor, detailed Work/report
  association, and credential-safe Git-origin rows all passed. This candidate
  remains immutable diagnostic evidence and is not acceptance evidence.
- Project-count successor: pushed commit
  `b9281d42fd4dfbe0fc44e569b6d0471d184dbf89`, tree
  `677604e36c908e9e60d9957721f0020a95a320f1`, parent
  `21c6e621982ca975854ed70515ad45c7671ad601`, workspace-data blob
  `69b99cf5dacc8724841a37bd170cb6f359ceb33c`, and project-workspace blob
  `b6cb1a7dbbec14eb2c4f081d5dd4804481723df8` introduce one shared
  `exactProjectRunIds` association boundary for Projects inventory, Project
  Overview, Work, and report counts. The contradictory fixture now assigns the
  canonical `beta` run to `beta` and zero exact runs to `alpha`, while retaining
  the `alpha` task/Floor claim only as an explicit disagreement.
- Run-claim correction: source incident `INC-20260810-043221-389CE7` identified
  that a current Run breadcrumb still followed a contradictory target-task
  project while the run/topology binding remained visually bound/valid. Pushed
  successor `aa05e88e5691df135dfe750bd72836cd90efc0c3`, tree
  `a1a275558d3f49e2bf2406bd9b14507ad2bd70ef`, parent
  `b9281d42fd4dfbe0fc44e569b6d0471d184dbf89`, run-workspace blob
  `1a19c06438e1ef34cddf82bab5e03ff82b8e1b0f`, focused-test blob
  `bb636fd5071de8025ae4bf7491ef49b47ca9709d`, and Playwright-config blob
  `305fefe5381929ad5bf60c7565de86f04ad6408e` reuse the same source-separated
  claim helper on the Run route. Contradictory run/task projects now render an
  unlinked `Binding disagreement` breadcrumb, both labeled exact claims, and
  degraded project/topology integrity with no valid marker. The focused route
  test seeds `CURRENT-PROJECT` versus `TASK-PROJECT` and proves that neither
  becomes a project link. Maintained viewport projects run serially against the
  single loopback adapter, preserving all 27 cases without concurrent adapter
  starvation.
- Third rejected review history: exact candidate
  `ee0b537444fdeb0ee4a670d926e13b6aec496c9a`, tree
  `eb62885772d596fa528bc26558c7a002e1e16212`, parent
  `aa05e88e5691df135dfe750bd72836cd90efc0c3`, and tracker blob
  `315418de99292049d3d1c6be8eeac575b046a2a6` was independently rejected
  because a failed run-list read made an explicitly disputed Factory Floor row
  look like an exact composed-only run. The reviewer reproduced Overview
  `Runs 1` while the row was degraded and Inventory was lower-bounded. Every
  requested mission/history, Git-origin, available-source count/report, and
  Run/Supervisor contradiction regression passed. This candidate remains
  immutable diagnostic evidence and is not acceptance evidence.
- Partial-source successor: pushed commit
  `2c6cea801ea863fe4a04d37627cbb66b5764f982`, tree
  `03f5d1981b4f28d3a3702b9195ecaf6794abcffd`, parent
  `ee0b537444fdeb0ee4a670d926e13b6aec496c9a`, workspace-data blob
  `7ed675d1c57d12cb00d0d0c3d7d2257307b0e290`, project-workspace blob
  `42f5fe7566bfc88485b8b6ba1f24ff63d6b3b7e9`, and browser-proof blob
  `d4ea9f54f268252370eaf40e71ff4a386ccda697` require both a successful
  run-list read and a non-disputed composition before an absent run can become
  exact. Under the rejected fixture, Overview now renders `Runs ≥0`, excludes
  one binding disagreement, labels the run source unavailable, and states that
  disputed Factory Floor claims are not exact; reports fail closed to a lower
  bound. Focused unit cases distinguish clean source-confirmed composition,
  source-unavailable composition, and disputed composition, and the browser
  exercises the failure at all three maintained viewports.
- Exact product review of candidate
  `7ebc4f2daf892acc385248fd083d60799f08f603`, tree
  `0d2f61e15d268e57be53f76fa6f15cc1f3d425a3`, returned `ACCEPTED` with no
  material finding. The reviewer reproduced disputed source failure as `Runs
  ≥0`, clean composition after a successful empty run list as exact `Runs 1`,
  normal canonical/disputed/report association, every predecessor and unknown-
  mission boundary, credential-safe origins, both Run/Supervisor conflicting-
  claim routes, and the read-only Stop. Exact identity/remote/clean checks and
  all mapped suites passed. This review is valid product evidence, but the
  candidate was not used to advance because a later harness-scope correction
  required removal of its unrelated global Playwright worker setting.
- Harness-scope correction: source incident `INC-20260810-045558-DF5C85`
  preserved the accepted product proof while rejecting repository-wide
  `workers: 1` as an unrelated validation mutation. Pushed successor
  `244215767c6647bf101b3d071c946eb7050448c2`, tree
  `e561478fdbaa63dbd4009ff033cddf0de41332ca`, parent
  `7ebc4f2daf892acc385248fd083d60799f08f603`, and restored config blob
  `af36f1a8e16d485b172b1b018fa7e32b18d8c759` remove exactly that one line.
  The affected association tests passed 10/10, the production build passed,
  `git diff --check` passed, and the one drill-down fixture passed 3/3 across
  desktop/tablet/mobile with `--workers=1` supplied only for that invocation.
  No unaffected matrix was replayed after the correction.
- Validation: the dashboard Python suite passed 67/67 with `ResourceWarning`
  promoted to errors (the sole collection warning is the pre-existing
  dataclass named `TestResponse`), Ruff passed, TypeScript/Vitest passed 45/45,
  the production build passed, and Playwright passed 27/27 across desktop,
  tablet, and mobile with accessibility and horizontal-overflow checks. The
  full tracker verifier passed Blocks 0-25 with 0 errors and 0 warnings, all 30
  verifier tests passed, five changed-document relative links resolved, and
  `git diff --check` passed. Live loopback `127.0.0.1:8787` exercised project,
  current run, paged event, unknown-mission rejection, predecessor run,
  historical supervisor, and task deep links with one functional route heading
  and no marketing subheader.
- Exact independent review and acceptance evidence: exact candidate
  `bfed4476b51b53a48e8c2f74643644f4150d34e3`, tree
  `732cbd8048aba2114c696df6a61aa91b3cc0663e`, parent
  `244215767c6647bf101b3d071c946eb7050448c2`, and tracker blob
  `745dee0e71299080fc76abe437cd9e06fd11097a` was independently `ACCEPTED`
  with no material findings. The focused reviewer proved the restored config
  matches its pre-global-mutation blob, no product source changed after the
  accepted `7ebc4f2` product revision, affected Vitest passed 10/10, build and
  typecheck passed, the named drill-down passed 3/3 across desktop/tablet/mobile
  with invocation-scoped `--workers=1`, tracker verification passed 0/0 plus
  30/30 tests, and link/diff/clean/remote/Stop checks passed. No unaffected
  matrix was replayed. Block 7 is accepted; Block 8 may activate next.

### Stop

Stop before adding tracker review, report analytics, or operational controls.

---

## Block 8 — Tracker review and progress workspace

Status: `accepted`

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

- Activation: began automatically from accepted and pushed Block 7 checkpoint
  `5821f6f62a8a404f8b3f4e929c142fcdfa920b65`, tree
  `dc016e108964c933165e143ed7998ec52ac22e0e`, parent
  `bfed4476b51b53a48e8c2f74643644f4150d34e3`, and tracker blob
  `7250cd60c25997cdf406c861d90d52e6433f7477`, with local/upstream at `0 0`.
  Direct-user item 44 and mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`
  retain full-tracker authority; no routed steer is treated as user authority.
- Product-capability review: `consequential`; the exact 54-line capability
  frame remains hashed
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  Browser-side raw-Markdown parsing, a duplicate verifier/readiness doctrine,
  inline editing/acceptance, a dashboard database, and a generalized Markdown
  CMS were rejected because they would duplicate maintained tracker authority
  or broaden this read-only workspace. The selected bounded option extends the
  accepted Block 3 projection with line-addressed, size-capped section bodies,
  Git diff metadata, and selected-tracker same-origin source access; the route
  renders a sanitized review view and queries the independent run owner only
  for exact tracker-binding claims. No operational or tracker state is stored.
  The accepted tradeoff is a richer typed detail envelope in exchange for one
  maintained parse and one lazy detail read per tracker fingerprint.
- Implementation candidate: commit
  `099a0f53d297de617dd412aec414cd8831fdf3f0`, tree
  `b4278265d9495a7892c0bc213a8250c976705dcc`, parent
  `786e78af29a0774f57955360dcd959d08263a1fd`; representative owner/UI/browser
  blobs are tracker projection
  `ce9bd34297d65c05728d5a41940ee731a4421914`, tracker workspace
  `efd227a707d36f31d3c3ae51e46dd72768ab5819`, and browser proof
  `54e3f4f20527a8d3c5a4f0e3883dd6d042fface9`. The candidate adds bounded
  section bodies and content hashes, summary-only diff metadata, a lazy exact
  diff endpoint with content/HEAD identity checks, same-tracker source ranges,
  strict Zod contracts, safe inert Markdown projection, index/overview/Block/
  evidence/print views, exact run mapping, missing-section truth, and no
  mutation surface.
- Focused and mapped validation: Python tracker/server tests passed 18 tests
  plus 5 subtests before the aggregate run; the exact aggregate Python suite
  passed 67 tests plus 13 subtests with `ResourceWarning` fatal and Ruff passed.
  TypeScript, all 14 Vitest files/50 tests, and production build passed. The
  invocation-scoped serial Playwright run passed all 33 cases across desktop,
  tablet, and mobile, including one full and one inherited-core tracker,
  filters, default current-Block selection, keyboard selection, safe source
  links, recorded evidence, unavailable candidates, print CSS, accessibility,
  and horizontal overflow. The full-profile tracker verifier reported Blocks
  0–25 with 0 errors/warnings, all 30 verifier tests passed, 21 relative links
  resolved with 0 missing, and staged/final diff checks were clean.
- Remediation closure: live/browser proof found and closed missing-query Block
  zero coercion, disabled deferred queries falsely labeled loading, shared
  amber-warning contrast below WCAG AA, eager diff payloads, and pending
  composed-owner data represented as an empty claim. Focused regression proof
  covers each boundary; one cross-suite concurrent run that exceeded unrelated
  five-second unit-test budgets is retained as diagnostic only, and the exact
  suites passed without cross-suite contention.
- First exact review: reviewer `/root/block6_exact_review` rejected evidence
  revision `0e339cf170058ca321e2d10f24da1b21a8256440`, tree
  `1b50399239481608930fc45ba00981d1a9c1e234`, because the dependency view did
  not derive blocked ancestry, unavailable Git could fall through to a false
  clean claim, partial composed-owner coverage could imply exact absence,
  completed rows counted as active mappings, and invalid zero-Block input
  produced a blank workspace. The review otherwise reproduced Python 67/67,
  Ruff, Vitest 50/50, build, Playwright 33/33, verifier 0/0 plus 30/30 tests,
  links, diff, clean, remote, and Stop proof; those passing results remain
  diagnostic for the rejected revision rather than successor acceptance.
- Corrected implementation candidate: commit
  `59729ebb73c1ab8ed457b529256bcff0edd0835a`, tree
  `77d96ab9a1d7665e7239d6545891d9b6d1e05df5`, parent
  `0e339cf170058ca321e2d10f24da1b21a8256440`; representative blobs are tracker
  projection `06620d5e916f1ec057371f1414fde7adacc42deb`, tracker workspace
  `58e1b7650c1953c4b213f4c74ba799f7c3d0fbd2`, shared status display
  `8e51c05c89863196f45e3995604a16521c9186db`, and focused browser proof
  `7e7fbbcbfc8fe4d5ea2ecdbfe8529292564008e2`. The correction adds transitive
  blocked-ancestor projection, danger and descendant labels, coverage-aware
  lower-bound/absence language, active implementation-or-supervision filtering,
  separate Git-versus-HEAD and run-bound comparisons, and explicit invalid
  zero-Block review state. It introduces no editor, acceptance, or start path.
- Corrected affected proof: exact Python owner/API aggregation passed 68/68
  with `ResourceWarning` fatal and Ruff passed; the affected TypeScript/Zod/
  component selection passed 12/12 and production build passed. Six focused
  browser cases passed across desktop, tablet, and mobile for blocked ancestry,
  unavailable Git/binding, partial coverage, completed-row exclusion, and
  zero-Block invalid state. The full-profile verifier passed Blocks 0–25 with
  0 errors/warnings and its 30 tests passed. Two broader frontend attempts are
  retained as environment-timing diagnostics after unrelated five-second tests
  exceeded their budgets; all affected tests passed independently and the
  unchanged pre-correction aggregate proof remains diagnostic only.
- Corrected freeze, durability, and acceptance:
  `59729ebb73c1ab8ed457b529256bcff0edd0835a` is pushed to
  `origin/codex/evolution-mvp`, remote identity matches, and its exact diff
  check is clean. Independent reviewer `/root/block6_exact_review` accepted
  exact evidence revision `3d6286d498bd21293a148a8f11a88203f472e26e`, tree
  `bb9aca5cae8db1dbe1a2087554d31cd834a78371`, with no material findings after
  reproducing Python 5/5 with fatal `ResourceWarning`, Ruff, affected Vitest
  12/12, production build, focused Playwright 6/6 across three viewports,
  full-profile verifier 0 errors/warnings plus 30/30 verifier tests, remote/
  tree/currentness, clean evidence-only diff, and Stop proof. All five rejected
  rows are closed, so Block 8 is accepted; Block 9 and later remain unstarted at
  this acceptance boundary.

### Stop

Stop before starting authoring/review/implementation tasks or changing tracker
state.

---

## Block 9 — Metrics and report history workspace

Status: `accepted`

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

- Activation: Block 9 started from accepted dashboard checkpoint
  `931ca2d2836d8f981f9684f70ef0e6036ba990a1`; required Blocks 4 and 6 are
  accepted, and Block 8 remains accepted without reopening.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Range-control diagnostic: the maintained installed
  `implementation-range-bind` rejected the exact canonical request before
  classification with `implementation range request text must not contain a
  local path`. The predecessor mission-successor command is preserved as the
  source of the stored `5ef3d610...` hash: it hashed the request with a literal
  escaped `\\n`. The maintained `control-posture-gate` nevertheless returned
  `next_action: continue-governing-outcome`, `human_input_required: false`, and
  `manual_resume_required: false`. This control-plane compatibility defect is
  diagnostic and does not contract or suspend the direct full-tracker request.
- Future failure-mode/recovery insertion: omitted only that planned addition
  because ephemeral side task `019fea24-7698-7df2-9dbd-db272c89f427` cannot
  expose an immutable direct-user turn/item source through the canonical owner.
  No tracker structure, failure registry, recovery workspace, or new-scope work
  was created before that omission; the existing Blocks 0–25 remain the active
  full implementation range.
- Product-capability review: selected the existing maintained weekly-report and
  supervision projection owners behind `OperationsProjectionService`, the
  loopback `/api/v1` boundary, strict Zod contracts, and the existing React
  workspace conventions. A telemetry database, generalized BI/query layer,
  report regeneration, report adoption, and lifecycle controls were rejected
  because they are independently owned outcomes outside this Block.
- Frozen implementation candidate:
  `01efe0d6f5d2abb6f509af5a13e597fac7532204`, tree
  `a7fe043743ac9c5e9f76e11dcd4836277b07a66b`, parent
  `2ed467634c5e4a78c4b57c8a0a9ab4e238d2de24`. The candidate changes exactly
  13 dashboard implementation/test files. Representative blobs are
  `416d358d192aeb5dcc25d94b745871a49274121e` for the normalized operations
  owner, `795d64dd0508f19598258d65ecd2f280a5f698bd` for the loopback server,
  `12e3d8291f7c052923f36cede9caf267b50cd02d` for the Reports workspace,
  `dd22076923a8ac0589d55636827f63ff987bbeeb` for its frontend contract, and
  `854679a7280e65ac1218aa3cc16451b8af0d177a` for browser proof. The remote
  branch resolved to the same exact commit after push.
- Exact live source sample on `127.0.0.1:8787`: weekly report
  `weekly-20260801T001853Z-20260803T234400Z-62f881d083b0` remained currently
  verified with source root
  `62f881d083b0e64262f54a81c575d0dd7b7a3e4330ea363f5a2b9414aadfd032`
  and manifest root
  `8046f7ae7223f19c348c9e4205375208bfcf4944905183273272b160c2a9a227`;
  the served `report.md` bytes independently reproduced SHA-256
  `4d624c74b30ed0898138f4868cbe8a7da2107fc841add0ed701743baeb784998`.
  Live metrics exposed six runs and six distinct exact supervisor-group IDs;
  unsupported concurrency, unmonitored-duration, posture-duration,
  late/missed-check, and generalized recurrence claims remained explicitly
  unavailable.
- Validation: the full Python dashboard suite passed 71/71 with
  `ResourceWarning` fatal and Ruff passed. The full strict TypeScript/Vitest
  run passed 15 files and 58 tests serially, and the production build passed.
  The full Playwright matrix passed 42/42 across desktop, tablet, and mobile.
  After the final distinct-group truth-label correction, affected exact proof
  passed one Python test plus Ruff, six Reports component tests, TypeScript and
  production build, and the live Reports browser case 3/3 across the same
  viewports. The ordinary parallel frontend invocation had earlier produced
  one existing five-second Floor test timeout; the mapped serial run and the
  exact affected successor proof passed, so that timing result remains a
  diagnostic rather than candidate acceptance evidence.
- Mechanical and Stop proof: the full-profile tracker verifier reported Blocks
  0–25 with 0 errors and 0 warnings, all 30 verifier tests passed, staged and
  committed diff checks passed, and the checkout/remote identity was exact.
  Artifact reads remain same-origin, bounded, currently verified, and
  read-only; no report generation, evolution adoption, outcome acceptance, or
  lifecycle administration control was added.
- Independent exact review of evidence revision
  `e147202f60fceb494a5ea979fce218eddf43d4b2` was `REJECTED`. The reviewer
  found four material rows: incompatible schema/coverage contracts were
  silently aggregated, wholly unavailable projections became numeric zero,
  trend rows had no exact metric/event source drill-down, and headline cards
  omitted the definition/period/denominator/observed-time/limitation plus
  supported role/category/decision/transition context. The rejected commit,
  tree, complete passing proportional evidence, and four findings remain
  preserved as immutable history; Block 10 did not start.
- Bounded corrective implementation successor:
  `129457a8983338836ac696e1f13e33cf3d5c3ad6`, tree
  `03177a85dc6490e0a228670cb4d08f30d68e7d0e`, parent
  `e147202f60fceb494a5ea979fce218eddf43d4b2`. Its 11-file affected diff makes
  server aggregates a three-state `available`/`incompatible`/`unavailable`
  contract: numeric headline, resource, and availability totals exist only
  when every included run shares one exact schema, definition, coverage
  interval, timezone, calendar-day set, partial-window posture, and denominator.
  The UI applies the same filtered-cohort rule, renders `Incomparable` or
  `Unavailable` instead of `0`/`$0`, and preserves per-run values independently.
- Explainability/source closure: compact metric cards now state their measured
  definition, while one functional contract panel exposes exact definition and
  schema, period, denominator, observed time, limitations, configured review
  roles, bounded category posture, current conclusions/transitions, metric IDs,
  source roots, and first/latest canonical event IDs. Every trend-table source
  links to the exact run metric anchor and canonical event range; per-run rows
  expose their own decisions, resolutions, conclusions, median/P90, coverage,
  generated time, metric identity, and source route. No actor, compatible
  aggregate, uptime, billing, or outcome posture is inferred.
- Corrective proof: four affected Python tests passed with `ResourceWarning`
  fatal and Ruff passed; the focused Reports/API suite passed 11/11,
  TypeScript and production build passed, and the two affected live browser
  scenarios passed 6/6 across desktop, tablet, and mobile. The live corrected
  API exposed six incompatible contracts with `headline: null`, resource totals
  `null`, and aggregate availability values `null`; selecting one run restored
  its exact metric/table/source views. Full-profile tracker verification remained
  Blocks 0–25 with 0 errors/warnings, all 30 verifier tests passed, diff checks
  passed, and the remote resolved to the exact successor.
- Corrective evidence revision
  `a5b50e76e445173369ab85edb19204a2f42e1f0f`, tree
  `b037c8f45951899fbf4ba12f901d605ab3c5a6e0`, was independently `REJECTED`
  on one residual source-navigation row only. The reviewer closed incompatible
  aggregation, unavailable-as-zero, and metric explainability/context, but
  proved that linking an event range to its first retained record could target
  an event outside the run workspace's mounted newest-50 page. The rejected
  evidence and its three closed rows remain immutable; Block 10 did not start.
- Residual drill-down successor:
  `c7edaa4741149aec0ebc02f931ad0de4697332e0`, tree
  `7da54d3b8dac8b8e619230d1d138b412a692a824`, parent
  `a5b50e76e445173369ab85edb19204a2f42e1f0f`. Both event-range entry points
  retain the full exact first–latest source identity but navigate to the latest
  canonical event, which is guaranteed to be present in the run workspace's
  newest page. The focused Reports component suite passed 8/8, the production
  TypeScript build passed, the exact live drill-down test passed 3/3 across
  desktop, tablet, and mobile, and each browser case proved that the destination
  hash resolved to a mounted element rather than checking the URL alone. Diff
  checks passed and the remote resolved to the exact successor.
- Fresh independent exact-revision review: `block6_exact_review` accepted exact
  evidence revision `8d667b629b72ff3f17ff89d19367d9b76573d1cf`, tree
  `df2ef3c1c17f6260585289bf3c9772ea16676ece`, with no material finding. The
  reviewer reproduced exact live range `EVT-001150–EVT-001301`, followed its
  link to `#EVT-001301`, and proved the destination element was mounted in all
  three maintained viewports. Focused component proof passed 8/8, the production
  build passed, focused live Playwright passed 3/3, full-profile verification
  remained Blocks 0–25 with 0 errors/warnings, all 30 verifier tests passed,
  diff and isolated-checkout checks passed, and remote identity matched. The
  sole residual navigation row and all three previously closed metric rows are
  therefore accepted; Block 9 is accepted without extending past its Stop.

### Stop

Stop before adding report generation, evolution adoption, or lifecycle
administration controls.

---

## Block 10 — Gated administrative operation framework

Status: `accepted`

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
  explicit operations in Blocks 11–30.
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

- Activation: Block 10 started from accepted Block 9 checkpoint
  `ade88f49c8b97df5144762c3580a3483c781bb34`; required Blocks 2, 4, and 5
  remain accepted, the checkout and upstream were exact at `0 0`, and Blocks
  11–25 remain unopened.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Product-capability review activation:
  - Trigger: Block 10 is consequential because it creates the shared boundary
    for all later consequence-bearing dashboard controls.
  - Frame identity: this tracker, Block 10, target-product frame SHA-256
    `ed469a767d27fce1b6d63a10fd34dc55d2d5ba32d0cf53ff216dd9a2a1447ab9`.
  - Capability selected: one typed preview/confirmation/request/verification
    seam that preserves exact domain-owner writes and truthful postconditions.
  - Paths compared: direct per-route mutation endpoints; a bounded shared
    registry and ephemeral correlation seam; the existing domain owners alone.
  - Selected level and owner: the bounded-general dashboard safety seam over
    existing domain owners, demonstrated only by a deterministic test owner in
    this Block. Direct endpoints would duplicate safety rules, while domain
    owners alone do not supply the browser-facing preview/token/replay boundary.
  - Protected-capability posture: preview is non-mutating, execution remains
    allowlisted and same-origin, no durable dashboard ledger is introduced, and
    canonical effects/postconditions remain with maintained owners.
  - Rejected alternatives: no generic workflow DSL, arbitrary App Server or
    shell dispatch, second authority system, durable queue, or prematurely
    registered tracker/task/supervision/report/lifecycle operation.
  - Tradeoff: the extra preview and canonical-verification round trip is
    accepted to prevent stale, replayed, cross-target, or HTTP-success-only
    mutations.
  - Frozen-candidate proof: implementation candidate
    `909946a76d0b67d495fc3d53a68403df6da868e0`, tree
    `7dac9486cdeef652f66e7d3a40830e8ff5a31199`, demonstrates the bounded seam
    through an injected deterministic test owner while the live production
    registry remains empty.
- Frozen implementation candidate:
  `909946a76d0b67d495fc3d53a68403df6da868e0`, tree
  `7dac9486cdeef652f66e7d3a40830e8ff5a31199`, parent
  `db3f6902d5a4c35ce52c2c72a9d6ce24f04afce7`. Representative blobs are
  `b26e6d918997ece366aebfe0c1a8d9e803f40f29` for the closed registry and
  ephemeral coordinator, `05644181b6ec2f92ea6eba107be9789fdfe11632` for
  the same-origin HTTP adapter, `6c7c60889349c054880276c29e28592298005f1f`
  for the strict frontend contract, and
  `dbfff177a413c9af5fd862f508bf8bd4836bfc0b` for the reusable Admin UI. The
  branch and remote both resolved to the exact candidate after push.
- Capability and Stop result: the production registry contains zero domain
  operations. The deterministic owner is injected only in tests. Preview is
  source-fingerprint and route-gate bound and non-mutating; execute requires
  same origin, the per-launch nonce, the exact unexpired token, unchanged
  request/source, and typed confirmation; it consumes the token before one
  named owner dispatch and distinguishes `requested`, approval/input waits,
  verification, `applied`, failure, unverified timeout, and cancellation.
  Activity is capped, process-local, and redacted; restart does not reconstruct
  a second ledger. No tracker, task, supervision, report, evolution, or
  lifecycle operation was registered, and no arbitrary command, path, method,
  recipient, or external result link is selectable.
- Adversarial proof: the deterministic owner covered non-mutating preview,
  allowed/denied/unavailable and mismatched route gates, exact confirmation,
  changed target/input, schema extras, expiry, stale source, duplicate submit,
  replay, owner failure/crash, approval/input waits, failed and timed-out
  postconditions, unsafe owner links, cancellation before/after the request
  boundary, redaction, and restart loss. A forced two-thread execute race
  produced one owner dispatch and one replay rejection. The API integration
  test also proved origin and launch-nonce enforcement plus an exact mounted
  status record.
- Validation: the full Python dashboard suite passed 82/82 with
  `ResourceWarning` fatal, the full serial TypeScript/Vitest suite passed 17
  files and 67 tests, the production build and full Ruff scan passed, and the
  affected Admin browser scenario passed 3/3 across desktop, tablet, and
  mobile with accessibility and horizontal-overflow checks. The direct
  `test_server` selector first exposed its established sibling-import binding;
  no product code ran in that setup attempt, and the corrected maintained
  discovery envelope passed 17/17 before the full suite. The staged candidate
  tree remained exactly `7dac9486cdeef652f66e7d3a40830e8ff5a31199`.
- Mechanical proof: full-profile tracker verification reported Blocks 0–25
  with 0 errors/warnings, all 30 verifier tests passed, diff checks passed, and
  the live server on `127.0.0.1:8787` returned an empty production registry and
  zero session activities without exposing a domain mutation control.
- First exact evidence revision and review: evidence commit
  `faa27791fc54c432f0ea1fceb8657bd83acd938c`, tree
  `91adb0edbd3466b58f42d67f130f4fa7dbdacdbf`, preserved the implementation
  candidate and validation but was rejected on two bounded rows. An allowed
  route-gate result was not proven to hash and echo the exact recipient,
  purpose, source, and action or rechecked for current policy immediately before
  dispatch. Redaction also omitted common secret key families, owner failure
  text and exception logs could disclose owner-controlled strings, and result
  links admitted query or fragment material. No other Block 10 finding was
  reported; production registration remained empty and the Stop held.
- Focused successor: `5d1571ad506374b1675b19b3e5a1dd09b8deeab2`,
  tree `fc5fb16c6ad99d94d9a3a18d47308f2ea5be44be`, parent
  `faa27791fc54c432f0ea1fceb8657bd83acd938c`, changes only the coordinator,
  its focused tests, and the strict frontend route-gate contract and fixtures.
  Representative successor blobs are
  `f30531a4c9871805e11a678c3fbffeadf5e145f6` for the coordinator,
  `2a0ef2a884bacb1fd39ea7f6ddb6f42208307353` for its tests, and
  `6a4a7aebfa8a19b768f27cf94cfd2afb37313b42` for the frontend contract.
- Route-gate closure: allowed results now echo the exact recipient, purpose,
  and source, use the maintained `thread-route-gate` canonical action SHA-256,
  carry the current policy SHA-256, and expose a fingerprint of that complete
  binding. Execute re-resolves the request and re-runs the gate after source
  currentness and immediately before the one owner-dispatch boundary; denial,
  invalid identity/action, or changed policy cancels the unconsumed preview.
  Focused adversarial proof rejected an unrelated all-zero action hash and
  mismatched recipient, then proved that a post-preview denial or policy change
  produced zero dispatches and a cancelled preview.
- Secret-boundary closure: public owner evidence now redacts `api_key`,
  `authorization`, `credential`, `cookie`, `private_key`, bearer and other
  secret-bearing values in addition to the prior families. Owner failure text
  is replaced with bounded framework language, unexpected exceptions log only
  their type without message or traceback, unknown objects never stringify,
  and same-origin result links reject query, fragment, traversal, external
  origins, and sensitive labels. Focused proof placed unique secrets in every
  named evidence family, an owner error, an exception message, and a query plus
  fragment link; none reached the public record or captured logs.
- Focused exact-successor validation: the operation coordinator suite passed
  11/11 with `ResourceWarning` fatal, the mapped HTTP suite passed 17/17 with
  `ResourceWarning` fatal, the affected strict frontend/API suites passed 6/6,
  and Ruff, TypeScript, and the production build passed. Diff checks passed,
  the branch and remote were exact at `0 0`, and the restarted live server on
  `127.0.0.1:8787` returned the closed production registry with zero activity.
- First successor review: exact evidence revision
  `858447939cfb277b205e0127f977a91335b0bb53`, tree
  `1e0f584e7261ea11465e31b96e9312c8fc1b5180`, was rejected on two residual
  secret/link-boundary cases while accepting the route-gate row. Unsupported
  mapping keys still invoked owner-controlled `__str__`, and percent-encoded
  dot/slash or backslash paths could pass server validation before browser URL
  normalization. The review reproduced four such traversal paths; all other
  focused proof, the empty production registry, Block status, and Stop held.
- Second focused successor:
  `4bde685418e116384829f75dd10011445cab478a`, tree
  `26a0be6ae39de8701fd4e7f9a663789cc5f67d75`, parent
  `858447939cfb277b205e0127f977a91335b0bb53`, changes only the coordinator
  and its focused tests. Its exact blobs are
  `cc65e1c087d4144a10a4d35a422017a298498474` and
  `0df8247b7dafc134c12588879af033af5dbae707` respectively. Unsupported
  mapping keys and values now become collision-safe opaque placeholders without
  invoking their string or type representation. Result links must match one
  canonical unescaped internal-path grammar and reject percent escapes,
  backslashes, dot segments, repeated/authority-leading slashes, queries,
  fragments, external origins, and secret-bearing labels before rendering.
- Second-successor focused proof: the exact four traversal reproductions, an
  owner key and value with secret-bearing `__str__`, a sensitive label, and a
  representative canonical task/source-style path were added to the existing
  secret/link regression. The coordinator suite passed 11/11 and the affected
  HTTP suite passed 17/17, both with `ResourceWarning` fatal; Ruff and diff
  checks passed. The unchanged strict frontend/API 6/6 and production-build
  proof from the first successor remain current because no frontend blob
  changed. The branch and remote were exact at `0 0`, and the restarted server
  on `127.0.0.1:8787` again exposed zero registered operations and activity.
- Fresh independent exact-revision safety/authority review: `ACCEPTED` for
  evidence revision `7e15f44d85e5a120aa2219683a329158d88a79e3`, tree
  `8c4a1e7643898088bd5012b57447dadc9b9bce8d`, with no material finding. The
  reviewer independently proved collision-safe opaque handling even when
  hostile `__str__` raised and a normal key collided with the first placeholder;
  rejected all four reproduced traversal forms plus dot segments, repeated
  slashes, queries, fragments, external URLs, and sensitive labels; preserved a
  canonical internal path; and reproduced coordinator 11/11, HTTP 17/17,
  Ruff, diff, full-profile verifier 0 errors/warnings, and verifier tests 30/30.
  The exact checkout and remote were `0 0`, the live production registry and
  activity were empty, and the Block 10 Stop held. Block 10 is accepted; task,
  tracker, supervision, report, evolution, and lifecycle operations remain
  unregistered until their dependency-ordered Blocks.

### Stop

Stop before registering tracker/task/supervision/report/lifecycle operations.

---

## Block 11 — Author, implement, supervise, and task-control workflows

Status: `accepted`

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

- Activation: Block 11 started from accepted Block 10 checkpoint
  `203fcf67da69bbdd4d1155783478da45e1600b43`; required Blocks 8 and 10
  remain accepted, the checkout and upstream were exact at `0 0`, and Blocks
  12–25 remain unopened.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Execution brief: accepted tracker/Git projections already supply exact path,
  hash, profile, Block eligibility, and worktree posture. The accepted App
  Server adapter already owns task start/resume, turn start/steer/interrupt,
  pending approval/input responses, current task state, and registered-cwd
  enforcement. The accepted Block 10 coordinator supplies preview, confirmation,
  replay/currentness, route-gate, owner dispatch, and canonical postcondition
  seams but intentionally has an empty production registry. The missing delta
  is a closed set of ordinary Factory workflow definitions, bounded skill prompt
  builders, exact conflict/readiness gates, workspace controls, and focused
  owner/API/browser proof. No new task system, tracker editor, scheduler, or
  durable operation state is required.
- Product-capability review activation:
  - Trigger: Block 11 is consequential because it introduces the first real
    Software Factory workflow and task-control mutations in the dashboard.
  - Frame identity: this tracker, Block 11, target-product frame SHA-256
    `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  - Capability selected: explicit operator-confirmed author, review, revise,
    implement, supervise, continue, steer, respond, and interrupt workflows that
    reach exact owner task/turn/request records without conflating those records
    with tracker acceptance or mission outcome.
  - Paths compared: direct workflow-specific HTTP mutations; explicit bounded
    operation definitions inside the accepted Block 10 framework; raw use of
    the existing skill and App Server owners without a browser safety seam.
  - Selected level and owner: bounded explicit definitions over the accepted
    operation coordinator, tracker projector, App Server adapter, and maintained
    author/implement/supervise skills. Direct endpoints would duplicate the
    accepted safety lifecycle, while raw owners alone cannot supply the required
    browser preview/confirmation/currentness contract.
  - Protected-capability posture: prompts preserve the operator's exact scope
    and named skill, tracker/Git readiness remains authoritative, registered cwd
    and exact task/turn/request identities remain App Server-owned, review stays
    read-only, and task activity remains distinct from Block or outcome state.
  - Rejected alternatives: no generic prompt composer, workflow engine, inline
    tracker editor, direct skill execution in the HTTP process, inferred task
    reuse, auto-retry, hidden second owner, or premature later-Block policy,
    report, evolution, succession, or lifecycle controls.
  - Tradeoff: explicit definitions and owner postconditions add code and an
    asynchronous confirmation round trip, accepted to prevent stale tracker,
    wrong-cwd, duplicate-owner, steer/continue, or HTTP-success-only mistakes;
    frozen-candidate proof remains pending.
- Frozen implementation candidate: commit
  `9bf58dc8a3c5c15fe7597ec56bd8845b013d04a6`, tree
  `f56a9c9e4f3325290f4be01513692ba2f282c959`, parent/activation
  `e098ced98e04a113c13745139fa7c9366a7de528`. Representative exact blobs are
  `d8e2c232dc2f0188d846364c836988916b492892` for the closed Python workflow
  owner, `d38fe288d0a6fc2c50a0f331bb73b4875c7b9b50` for its owner/API proof,
  `1a03dd5c6a3aadd4e6bd2d8bf18c90a127f90040` for the workspace controls, and
  `38ef0931b7578cc4fa7bf7039e2c964fd058bf5d` for their component proof. The
  candidate changes only the Block 11 Python registry/owner adapter, existing
  App Server fake, workspace controls/styles/routes, and mapped tests; its
  branch and upstream were exact at `0 0` after push.
- Closed workflow proof: production now registers ten supported explicit
  operations—author, read-only review, bounded revise, eligible Block/range
  implementation, supervision attach, continue, steer, approval response,
  input response, and turn interrupt—plus one explicitly unavailable planned
  tracker-authoring-supervision row. Author/review/revise/implement turns name
  the maintained skills, preserve exact operator scope, source/hash/HEAD/
  profile/Stop facts, and start at most one registered-cwd task without retry.
  Current tracker content/Git/profile, clean-writer posture, dependencies,
  contiguous range, exact Stop, bounded active-owner absence, task/turn/request
  identity, and canonical supervised-task route are resolved at preview and
  rechecked at execute by the accepted Block 10 coordinator.
- Consequence and recovery proof: wrong cwd, stale/dirty tracker, invalid range,
  conflicting author/revise/implementation ownership, partial task/turn start,
  route absence/denial, stale one-use approval/input, and incomplete
  supervision setup all fail closed or remain explicit partial/unverified
  attention. The corrected route adapter opens the maintained helper with
  no-follow semantics, pins its exact bytes, and executes that open descriptor;
  replacement or symlink substitution fails closed. Active unmarked repository
  tasks and every live same-tracker implementation/revision owner block a second
  writer because no supported handoff exists. Supervision is `applied` only
  after the exact implementation-task tracker/range/mission marker, canonical
  current policy, mission/project binding, complete four-role family, exact live
  role tasks, lifecycle posture, and both distinct ACTIVE watcher/reviewer
  heartbeat manifests at policy cadence are current. Continue, steer, respond,
  and interrupt use only their typed App Server methods; interruption records no
  supervision pause, mission stop, or work acceptance.
- Operator-interface proof: compact action strips sit directly in project,
  tracker, and task workspaces without a marketing title/subheader row. Typed
  confirmation shows exact target, owner, recipient/gate, source, supplied
  objective/text/choice/range, consequences, and postcondition. Approval and
  input dialogs retain current command/file scope and bounded option text;
  unregistered tasks and missing canonical routes disable mutation controls.
  Result truth reports task/turn start, Block acceptance, and outcome
  verification separately, links the exact task/run when observed, and
  refreshes task/list/run/floor/tracker sources without inventing a second
  ledger or lifecycle state. The live visual check exposed and corrected a
  long-identity collision in the confirmation grid, then added cell-level
  overflow proof across all maintained viewports.
- Focused accessibility successor: the first exact full browser replay passed
  47/48 cases and exposed one serious pre-existing mobile diff-view defect only
  after this uncommitted evidence made the read-only diff long enough to scroll:
  its `<pre>` had no keyboard focus target. Successor
  `f78dcdd37f1c0208fa2c97480a3409760b1b2382`, tree
  `897e18666a8feeacb49612a815fad047e3ef99f4`, parent
  `9bf58dc8a3c5c15fe7597ec56bd8845b013d04a6`, changes only that shared tracker
  diff element to expose a named keyboard focus target. The exact rejected
  mobile scenario then passed 1/1 with Axe and overflow proof; the other 47
  browser cases are unaffected and remain valid.
- Candidate validation: the exact Python suite passed 92/92 with
  `ResourceWarning` fatal and the focused workflow owner/API suite passed 7/7;
  full Ruff passed. TypeScript and all 18 Vitest files/73 tests passed, the
  production build passed, the workflow scenario passed 3/3 across desktop,
  tablet, and mobile, and the proportional browser result is the 47 unaffected
  full-matrix passes plus the corrected affected mobile 1/1. Full-profile
  tracker verification reports Blocks 0–25 with 0 errors/warnings, all 30
  verifier tests pass, and diff checks pass. Independent exact-revision review
  was therefore requested without advancing Block 11.
- Exact rejected evidence revision: commit
  `3e307c6235d0176f0b17c3b9503aedcea5fe139b`, tree
  `a1059a974ae65b6b8a6c86c14d0af0ba6007390d`, parent
  `f78dcdd37f1c0208fa2c97480a3409760b1b2382`, was independently `REJECTED`.
  The review reproduced four material rows: an active unmarked task and a
  nonoverlapping same-tracker implementation could become second writers; the
  route helper could be replaced by a symlink after construction; one arbitrary
  bound role plus one merely readable automation could be reported attached;
  and a committed tracker filename containing newlines could place hidden
  instruction lines in generated skill prompts. The review otherwise confirmed
  exact remote identity, clean diff, Python 92/92, Ruff, build, affected Vitest,
  browser 3/3 plus the corrected mobile case, full-profile verifier 0/0, and
  verifier tests 30/30. Block 12 remained closed.
- Bounded correction successor: commit
  `a0ef88b98edaecac09c4447d8d92320b3b15d3b6`, tree
  `4f0623cfcc15e658077a3c2b555b7d92a0f15983`, parent/rejected evidence
  `3e307c6235d0176f0b17c3b9503aedcea5fe139b`, changes only the workflow owner,
  tracker path boundary, workflow controls, and their mapped backend/frontend
  tests. Representative exact blobs are
  `bdac5c46a7b2d3ca727c44ec5a98424b3547244a` for the corrected owner,
  `a034f8665b87ef83bed0477426923c0a49d76050` for tracker path validation,
  `ba846d5cf7b4cde8bd413253be402ece3ed0b555` for the source-bound controls,
  `67b322d1f361204c98d8bb0546c3149f40e0e985` for backend proof, and
  `35817dcd9a8229ea307909be43ce7c33a8e64c09` for component proof. Structured
  tracker facts and Stops are canonical JSON data in generated turns, and
  control-character tracker paths are rejected before projection or prompt
  construction. Attachment inputs are derived from the implementation task's
  own mission marker in the UI and revalidated by the backend at preview,
  execute, and owner postcondition.
- Correction validation: the exact backend suite passed 95/95 with
  `ResourceWarning` fatal, all 18 Vitest files/73 tests and the production build
  passed, Ruff passed across the full backend source/test tree, and the affected
  workflow browser scenario passed 3/3 across desktop/tablet/mobile. The exact
  full browser replay passed 46/48 in its parallel run; its two unrelated
  project-drilldown and metrics/Axe timeouts then each passed 1/1 in the exact
  failed viewport with invocation-scoped `--workers=1`, preserving a complete
  48-case result without changing the global harness. The full tracker verifier
  remained Blocks 0–25 with 0 errors/warnings, all 30 verifier tests passed, and
  diff checks passed. Fresh independent exact-revision review of the successor
  evidence revision is pending; Block 11 remains `in-progress` and Block 12
  remains `not-started`.
- First successor audit disposition: the independent audit confirmed exact
  `229e8f83a911825522577027a106a411ee1e8b60`, tree
  `8d8dc0dee6d49585192f0cbe401690039e769a4f`, parent/product
  `a0ef88b98edaecac09c4447d8d92320b3b15d3b6`, exact origin, and source-level
  closure of all four rejected rows, but its final verdict was interrupted by a
  platform safety filter. No acceptance was inferred. Its last evidence-bound
  checkpoint identified two residual currentness probes: the child process
  could reread a mutable open helper descriptor after digest verification, and
  an older task preview marker could outrank a later exact turn marker. Block 11
  stayed unaccepted and Block 12 stayed closed.
- Residual currentness successor: commit
  `945ad6f0dd692806493f4b5bb6fc5542421e911d`, tree
  `566a58adf966b538fe32181ee75c6f1b4ddbe7f4`, parent
  `229e8f83a911825522577027a106a411ee1e8b60`, changes only the workflow owner,
  source-bound control parser, and their focused tests. Exact blobs are
  `347216a22dcbd25288518f54977a7bde00251155` for the owner,
  `be7025d99619916d068ad385f5001fbc6d6badff` for backend proof,
  `07cdb5d65e975c4df810e61883222441ecd63852` for the UI parser, and
  `069b10179eebdf363cbccddebd986032e3d00b57` for component proof. The owner
  process reads and verifies the no-follow helper descriptor once, then gives
  the child those immutable in-memory bytes; changing the pathname or
  regular-file bytes
  before child execution cannot alter the executed program. Backend and UI
  marker selection now inspect newest turns first and use preview only as a
  fallback, so a stale preview cannot mask a later exact binding.
- Residual validation: the exact backend suite remained 95/95 with
  `ResourceWarning` fatal, all 18 Vitest files/73 tests and the production build
  passed, full backend Ruff passed, the full-profile tracker verifier remained
  26 Blocks with 0 errors/warnings, all 30 verifier tests passed, and diff checks
  passed. Focused proof replaces the helper file immediately after the verified
  byte read and confirms the original bytes execute, and supplies conflicting
  preview/newer-turn mission markers to both backend and UI and confirms the
  newer turn controls. This revision remained unaccepted pending fresh exact
  review.
- Accepted evidence revision: commit
  `b56e74234515da200e8d1542f6bc76845e9e21f1`, tree
  `b41de6c92c3ef2df76804d60e5c7bcaf3769a3e1`, parent/product
  `945ad6f0dd692806493f4b5bb6fc5542421e911d`, was independently `ACCEPTED`
  with no material product-correctness finding. The review confirmed the four
  rejected owner/currentness rows and the two residual consistency probes are
  closed at the exact revision. The accepted validation archive is Python
  95/95 with `ResourceWarning` fatal, Ruff, all 18 Vitest files/73 tests,
  production build, affected workflow browser 3/3, the complete 48-case
  responsive browser result with the two unrelated timed-out cases replayed
  serially at their exact viewports, full-profile tracker verification with 26
  Blocks and 0 errors/warnings, all 30 verifier tests, and clean diff/remote
  identity. Block 11 stops at maintained author/implement/supervise/task-control
  workflows; it does not claim later supervision, report, continuity, or
  lifecycle controls.

### Stop

Stop before policy/schedule adjustment, report/evolution workflow, successor
administration, or semantic lifecycle controls.

---

## Block 12 — On-demand mechanical supervision checks

Status: `accepted`

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

- Activation: Block 12 started automatically from accepted and pushed Block 11
  checkpoint `8737c0fa37c570c76ac5330f18fbc94fc0ac89a7`; dependencies 7, 10, and 11
  are accepted, the checkout/upstream were exact at `0 0`, and Blocks 13–25
  remain unopened.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Execution brief: reuse the accepted Block 10 coordinator, Block 11 task and
  route-gate owner, current run projection, and canonical supervision ledger.
  Add one explicit watcher-owned operation whose applied postcondition is one
  exact newer current-mission `check` record matching the selected target,
  maintained `watcher-action` purpose, and preview fingerprint. One successful
  wake is only an intermediate state; no dashboard ledger, retry loop, semantic
  conclusion, policy change, or later-Block control is introduced.
- Product-capability review activation: the bounded operation-definition path
  is selected over a direct endpoint or a generic supervisor command because it
  preserves the accepted preview/confirmation/currentness lifecycle and the
  maintained watcher/route owners. Protected behavior is exact target and
  mission binding, duplicate-active exclusion, at-most-one wake, bounded
  postcondition polling, and explicit denied/timed-out/unverified truth.
- Implementation candidate: commit
  `152ad1ecd7709197fa3d0b1f56e1b4344f109dac`, tree
  `90c69d9e566a48d0074eeef84316c951ffc8188a`, parent
  `62f61405609c9acc53f457a48b87db91186cdd3a`, is pushed exactly to
  `origin/codex/evolution-mvp`. The principal owner blobs are
  `8de9b0756265fd8b9ee8a8c47c3b5617ce3e056b` for the watcher workflow,
  `478dcc4074f10f95a0e0153f3f8e17aad79cb8b0` for the App Server adapter,
  `562d3198c39b52cfc1b5677d339dcdbb4201be89` for the action UI, and
  `7421104b5a8a9a973b224ad0c5295228e24a10f6` for responsive browser proof.
  This revision remains unaccepted pending independent exact-revision review.
- Implemented owner path: `factory.supervision-check-now` resolves one exact
  current run, target task, watcher role, active cadence-bound automation,
  current mission/policy/event head, and watcher task/cwd identity; uses the
  maintained `watcher-action` route gate; wakes the exact idle or resumable
  watcher at most once; and reaches `applied` only for one newer canonical
  `check` with the exact mission, policy, source line, purpose, and preview
  evidence. Wake-only, unrelated-newer-event, timeout, missing/active watcher,
  missing automation, stale source, and mismatched evidence paths remain
  failed, disabled, pending, or unverified without a semantic conclusion.
- Currentness and bounded-transport proof: the dedicated internal role-turn
  owner rechecks the canonical watcher cwd device/inode immediately before the
  App Server owner call, including a same-path replacement negative test with
  zero requests. The bounded protocol line limit is 32 MiB so the accepted
  80-turn/250-item projection can shape a long supervised task; a 5 MiB raw
  response is accepted, projected to the tighter text bound, and leaves the
  adapter available. Generic task controls still require registered project
  cwd ownership.
- Candidate validation: the exact frozen diff hash was
  `2d99ad31d6c32e647b64d8907994571a7c3da115`; backend discovery passed 98/98
  with `ResourceWarning` fatal, full Ruff passed, all 18 Vitest files and 74
  tests passed, and the production TypeScript/Vite build passed. The full
  tracker verifier passed all 26 Blocks with 0 errors/warnings, all 30 verifier
  self-tests passed, and staged diff checks were clean. A hard-coded idle-task
  fixture crossed its 24-hour recency window during the first backend run; the
  test now explicitly requests the active task it asserts, its focused rerun
  passed, and the complete serial backend rerun passed without changing
  production recency behavior.
- Rejected exact review: evidence revision
  `7b40cdc1219896818ade1def03eb801365023dd1`, tree
  `7edfe23382d97b9f29b019b53975807fba0edd89`, was rejected because the
  postcondition accepted any newer `kind=check` record, including a verified
  `observable-outcome-completion` record carrying explicit implementation-
  acceptance action and resolution, while reporting
  `semantic_conclusion=false`. The review otherwise reproduced backend 98/98
  with `ResourceWarning` fatal, Ruff, frontend 74/74, production build,
  Playwright 6/6 across three viewports, the tracker verifier at 0 errors and 0
  warnings, and all 30 verifier self-tests. The rejected revision remains
  immutable evidence and does not accept Block 12.
- Corrective successor: commit
  `37c66dd1fc7cc0cdbe82ef056ff417b9f3345e93`, tree
  `55bad865e754264666d065bfaabfd26214aadc02`, parent
  `7b40cdc1219896818ade1def03eb801365023dd1`, is pushed exactly to
  `origin/codex/evolution-mvp`. Its four-file staged diff root was
  `bfbe6cad7f7b8ba4d938313c6dc7698f969e93f4a3fc12f7a6a4167d8432f868`.
  The owner now accepts only a complete canonical mechanical watcher outcome:
  either `check/no-intervention` with empty semantic-control fields, or the
  maintained `escalation/changed-state-review/routed` handoff with its bounded
  routing fields. Semantic/outcome completion, partial projected records,
  wrong severity, intervention-bearing records, and unmatched identity or
  evidence remain pending and never acquire a dashboard-authored conclusion.
  The affected workflow-owner module passed 10/10 with `ResourceWarning`
  fatal, the focused UI passed 3/3, Ruff passed, and diff checks were clean;
  previously valid unaffected proof is preserved. This successor remains
  unaccepted pending fresh exact-revision review.
- Corrective review and identity successor: exact evidence revision
  `a2f3320b78c5d858e457250f0eac4520351f33fc`, tree
  `43da6c60fd2d7f6ea3f19b8ab724828f61e689e1`, confirmed closure of the
  semantic-completion exploit but remained rejected because a projected
  mechanical record with no `record_id` or `timestamp` could still become
  applied while displaying both as unavailable. The two-file successor commit
  `b4d8afc7d38ce8ec72a45f91365896170befc5a2`, tree
  `5510e4f0deadef5d883ce9ee890146a505c4254b`, parent
  `a2f3320b78c5d858e457250f0eac4520351f33fc`, is pushed exactly to
  `origin/codex/evolution-mvp`; its staged diff root was
  `6295e637a894429892eb3b83402598aae7361f01245c3647d4a8b05d35870e5c`.
  It requires the event ID to match the exact canonical source-line sequence
  and requires a parseable timezone-aware timestamp before matching either
  mechanical outcome family. Identityless, mismatched-ID, empty, malformed, or
  timezone-free records therefore remain pending. The affected backend module
  again passed 10/10 with `ResourceWarning` fatal, Ruff passed, and diff checks
  were clean; the prior review's green focused UI, build, tracker, and Stop
  evidence is preserved. At freeze, Block 12 remained unaccepted pending the
  delta-only fresh exact review recorded next.
- Fresh exact acceptance: independent review accepted evidence revision
  `bb23a96ea2497c762270ae520cfa0d58cb194531`, tree
  `2171eb7188041c6f7ebe4d81297424f351543de1`, and product revision
  `b4d8afc7d38ce8ec72a45f91365896170befc5a2`, tree
  `5510e4f0deadef5d883ce9ee890146a505c4254b`, with no material findings.
  Missing, empty, malformed, non-string, timezone-free, and source-line-
  mismatched record identities/timestamps all remained pending; exact UTC and
  offset-aware canonical identities applied for both maintained mechanical
  outcome families; semantic/outcome-completion records remained pending.
  The reviewer reproduced the affected backend 10/10 with `ResourceWarning`
  fatal, Ruff, the full-profile tracker verifier at 26 Blocks and 0 errors or
  warnings, all 30 verifier self-tests, clean product/evidence diffs, a clean
  checkout, and exact local/upstream/remote identity. Block 12 is therefore
  accepted without opening its semantic-review or later-operation Stop.
- Exact live/browser proof: on the rebuilt candidate served at loopback port
  8787, the affected Factory Floor and live run/supervisor/task drill-down
  scenarios passed 6/6 serially across desktop, tablet, and mobile. The current
  run exposed an available source-bound `Check now` preview with
  `watcher-action`, then cancelled it before dispatch; the historical mission
  exposed no control. A separate live task read returned the bounded projected
  long-lived task while the adapter remained available. No watcher was awakened
  during non-destructive live proof.
- Stop proof: the candidate adds no semantic review request, policy/cadence or
  binding mutation, lifecycle/continuity action, report/evolution operation,
  dashboard supervision ledger, automatic retry, semantic approval, Block
  acceptance, or outcome-completion claim.

### Stop

Stop before registering semantic review or any policy, binding, lifecycle,
continuity, report, or evolution operation.

---

## Block 13 — Semantic supervision review requests

Status: `accepted`

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

- Activation: Block 13 started automatically from accepted and pushed Block 12
  checkpoint `47ba53f8be92e1149714fed4fce66a5fd1403fe3`, tree
  `7e64049f11a78f8e1b683c63efc8eef756f6fe56`; dependencies 7, 10, and 11
  are accepted, the checkout/upstream were exact at `0 0`, and Blocks 14–25
  remain unopened. The direct-user full-tracker request remains Blocks 0–25;
  this transition does not contract the remaining range.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Execution brief: extend the accepted typed operation coordinator with three
  closed reviewer-owned variants—checkpoint, meta, and issue follow-up—while
  reusing current run/role/conclusion projection, exact route gates, and the
  internal role-turn owner. Keep delivery, active work, and canonical semantic
  conclusion as separate states; introduce no generic prompt, second review
  ledger, dashboard acceptance authority, or later-Block control.
- Product-capability review: the three closed operation variants are the
  minimally sufficient extension of the accepted operation coordinator. A
  generic reviewer prompt, direct App Server bridge, dashboard review ledger,
  or inferred actor field would weaken owner and truth boundaries. The selected
  path preserves exact target/task/cwd identity, current mission/policy/state,
  variant-specific route purpose and reviewer role, bounded confirmation,
  at-most-one dispatch, canonical conclusion matching, and explicit
  unavailable actor attribution.
- Implementation candidate: commit
  `cfe9bd7dffe3414820a018dd6bb11bd05694f3ff`, tree
  `a0bcceb406d3e5000a2cb067238abbdfcd7e7595`, parent
  `3cc3e1708378d79492b91e25032518aa514ad514`, is pushed exactly to
  `origin/codex/evolution-mvp` at `0 0` divergence. Its exact product diff root
  is `618a54cad97240a075c22104bebac8f738e94ac09b21d150f380aa0ece09b573`.
  Principal blobs are `477ee286c708d5ab396ba6394a025089dab7a3b7` for the owner,
  `2c015487a4d314487f596001c958c065b8260031` for its focused backend proof,
  `564c5251026ece4c4588af2fc647f9646e09fc28` for run actions,
  `56742e60df92d272ff8ee62884bc23c42ef56aeb` for operation truth/preview,
  and `53723b3240d8fe2cb147630ed264e7bcdb001666` for responsive browser proof.
  This revision remains unaccepted pending independent exact-revision review.
- Implemented owner path: checkpoint and meta variants bind only the exact
  current `reviewer` task through `semantic-escalation`; issue follow-up binds
  only one exact open incident and the current `notice_reviewer` task through
  `incident-review`. Each preview exposes the target, state root, source record,
  reviewer role, expected conclusion kind, recipient, route purpose, gate, and
  currentness fingerprint. Dispatch re-resolves all sources and exact cwd
  identity under one lock, starts one bounded role turn, and never retries.
- Conclusion truth: delivery and terminal task state remain request evidence,
  not a conclusion. A postcondition requires a newer canonical record with
  exact source-line identity, timezone-aware timestamp, mission, policy, state,
  variant kind, purpose, preview, source, task and incident evidence. The exact
  dispatched reviewer turn must still contain the request marker before the
  record is correlated. Canonical events do not expose the emitting actor, so
  actor attribution remains `unavailable`; the UI states the exact-turn
  correlation separately. Malformed, wrong-root, wrong-purpose, wrong-role,
  stale, duplicate, missing-source, uncorrelated and identityless records remain
  pending/disabled. Only a later canonical same-kind conclusion can supersede
  the matched conclusion.
- Validation: Ruff passed and the affected workflow-owner module passed 11/11
  with `ResourceWarning` fatal. The three affected frontend files passed 14/14
  Vitest cases, TypeScript and the production Vite build passed, and the focused
  live run/supervisor/task flow passed 3/3 serially across desktop, tablet, and
  mobile. Full-profile tracker verification reported all 26 Blocks with 0
  errors and 0 warnings; all 30 verifier tests and diff checks passed.
- Live non-mutation proof: on the rebuilt exact source served at loopback port
  8787, current checkpoint and meta-review previews resolved to the maintained
  reviewer task and `semantic-escalation` gate, exposed their exact operational
  facts, and were cancelled before dispatch. Issue follow-up remained disabled
  for the current run and its direct invalid example failed closed because no
  current notice-reviewer/open-incident binding exists. The maintained focused
  fixture covers the supported open-incident path. Historical mission views
  exposed none of the four supervision actions. No reviewer turn or supervision
  record was created by live validation.
- Stop proof: the candidate adds no generic reviewer prompt, direct target edit,
  dashboard review ledger, automatic retry, implementation acceptance,
  policy/cadence or binding mutation, lifecycle/continuity control, report
  operation, or Factory-evolution action. Blocks 14–25 remain unopened.
- Rejected exact review: evidence revision
  `1091bb2773e2be545624886683d4fcb27c779500`, tree
  `047b6f574b92ee5473d7ed3b08aaaba6605e810e`, and product revision
  `cfe9bd7dffe3414820a018dd6bb11bd05694f3ff` remain immutable rejected
  evidence. Independent review found three bounded matcher defects: issue
  resolution required an invented `notice-outcome` category absent from the
  maintained owner contract; required evidence was only a subset, so
  contradictory same-namespace bindings could coexist; and any nonempty status
  allowed a routed request record to become a conclusion. The review otherwise
  reproduced backend 11/11 with `ResourceWarning` fatal, Ruff, frontend 14/14,
  production build, the 26-Block verifier at 0 errors/warnings, all 30 verifier
  tests, clean exact diffs, clean checkout, exact remote identity, and the Stop.
  Block 13 remained in progress and Block 14 stayed closed.
- Corrective successor: commit
  `196145e5a713997cb71c4a22048005ae20b98b7f`, tree
  `d2aa3b9c1314d1338a42a67783c45b609a3ce8ce`, parent
  `1091bb2773e2be545624886683d4fcb27c779500`, is pushed exactly to
  `origin/codex/evolution-mvp`. Its two-file diff root is
  `c5b81bc69a4126e3f921489c42230b21f94544f049290b9548c0c52051bf474b`;
  corrected blobs are `22a113a9bd13d87061d4c709a716377624463c5b`
  for the owner and `301c4ac2a18433df0a88ff01c4753aa43567e870`
  for focused proof. The issue path now accepts the incident's actual canonical
  category, while retaining exact incident/kind/task/turn/source binding. The
  four reserved dashboard evidence namespaces must contain exactly one matching
  binding each, so duplicates or contradictory values remain pending while
  unrelated owner evidence is preserved. Requested, routed, active, awaiting,
  denied, queued, delivered, and other non-conclusion statuses cannot match or
  supersede a conclusion. Focused backend proof again passed 11/11 with
  `ResourceWarning` fatal, Ruff and diff checks passed, and the rejected
  review's unaffected frontend/build/browser/tracker/Stop evidence remains
  current. This successor remains unaccepted pending fresh exact delta review.
- Rejected corrective review: exact evidence revision
  `5c5ea030a7f3cc114d941ace39498792ae20a953`, tree
  `36464230c5e32c005b693b8360de58471044474b`, and product revision
  `196145e5a713997cb71c4a22048005ae20b98b7f` remain immutable rejected
  evidence. Fresh independent review confirmed that the actual incident
  category and exact reserved-binding rows were closed, but rejected the
  status matcher because its finite non-conclusion denylist still treated the
  exact states `request`, `awaiting`, and `unverified` as conclusions and later
  superseders. The reviewer reproduced the affected 11/11 backend tests with
  `ResourceWarning` fatal, Ruff, the 26-Block verifier at 0 errors/warnings,
  all 30 verifier tests, clean exact diffs, exact remote identity, and the Stop.
  Block 13 remained in progress and Block 14 stayed closed.
- Closed-taxonomy successor: commit
  `ece13b46f667383b16554c4b884a80a525d1ba61`, tree
  `a6e82b59ab75fd2793c66b9cf652ffcf40a4c490`, parent
  `5c5ea030a7f3cc114d941ace39498792ae20a953`, is pushed exactly to
  `origin/codex/evolution-mvp`. Its two-file diff root is
  `d13a342dcd22adfb6c0cf241740f49313118d2e098b2f6576fe897f47f67c9cd`;
  corrected blobs are `ec4d4a1d146d1ceef1b36d69810f2eb851ee8cf4`
  for the owner and `0213cf3aa228be9543064c8e32322405c9813976` for
  focused proof. The matcher now fails closed through a kind-specific semantic
  conclusion allowlist rather than trying to enumerate non-conclusions, and
  the bounded reviewer request names the exact supported statuses. Initial
  matching and later supersession both reject `routed`, `request`, `awaiting`,
  and `unverified`; maintained checkpoint, meta-review, and incident outcomes
  remain explicit. The affected backend module again passed 11/11 with
  `ResourceWarning` fatal, Ruff and diff checks passed, and no frontend,
  operation-route, tracker-status, or later-Block product surface changed. This
  successor remains unaccepted pending fresh exact delta review.
- Rejected taxonomy review: exact evidence revision
  `345c7a972695a9a1666ff4dd1a92b82814984904`, tree
  `739de33322c1bf7181b9c3ed42f87047621c1a43`, and product revision
  `ece13b46f667383b16554c4b884a80a525d1ba61` remain immutable rejected
  evidence. Independent review confirmed the three workflow states and the
  original category/binding rows were closed, but found the closed resolution
  taxonomy omitted maintained terminal incident status `resolved`, excluding
  it from both matching and the generated owner request. The exact affected
  backend module, Ruff, full-profile verifier, 30 verifier tests, diff checks,
  remote identity, and Stop otherwise remained clean.
- Maintained-terminal successor: commit
  `9542332c8a9fb884bd0dbe56038df843ae0d1cbd`, tree
  `895ef49637ddc9953a3ec1e6a88aea7a00fdd80d`, parent
  `345c7a972695a9a1666ff4dd1a92b82814984904`, is pushed exactly to
  `origin/codex/evolution-mvp`. Its two-file diff root is
  `abe0c389ed4586e67d64e60ebec6b56b9f63889a6bb55a5bdb880d879f605fd9`;
  corrected blobs are `962d2894a6cc52b391b67e4c188d221c70915a8b`
  for the owner and `ef89d43e9368b45ad958f8346f6874fc64c88244`
  for focused proof. The resolution taxonomy now includes the maintained
  terminal `resolved` outcome, and focused proof requires both prompt exposure
  and applied matching for that exact status. The affected backend module again
  passed 11/11 with `ResourceWarning` fatal, Ruff and diff checks passed, and
  the closed workflow-state, category, and exact-binding rows remain unchanged.
  This successor remains unaccepted pending fresh exact delta review.
- Fresh exact acceptance: independent review accepted exact evidence revision
  `bca16feff3fb9eb47f8f53f9b38bf5e49791f8f0`, tree
  `c8c8c433eecb2f3839b8735312caa04a3f187fad`, and product revision
  `9542332c8a9fb884bd0dbe56038df843ae0d1cbd`, tree
  `895ef49637ddc9953a3ec1e6a88aea7a00fdd80d`, with no material finding.
  The exact adversarial probe returned one match for maintained terminal status
  `resolved`, and the bounded owner prompt explicitly exposed it. `request`,
  `awaiting`, `unverified`, `routed`, `active`, and `denied` all returned zero;
  actual incident categories still matched and conflicting reserved bindings
  did not. The reviewer reproduced backend 11/11 with `ResourceWarning` fatal,
  Ruff, full-profile verification for all 26 Blocks with 0 errors/warnings,
  verifier tests 30/30, diff checks, exact remote identity at `0 0`, and the
  Block 13 Stop. No canonical or supervision record was created.

### Stop

Stop before policy/cadence administration, binding repair, lifecycle mutation,
reporting, or Factory evolution.

---

## Block 14 — Supervision policy and cadence administration

Status: `accepted`

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

- Activation: Block 14 started automatically from accepted and pushed Block 13
  checkpoint `9651fc03af2a304ff7cda174155d2e487773ec87`, tree
  `3bc97b5869ae8a96e6c4671551cd0d8e6ec84834`; dependencies 7, 10, and 11
  are accepted, the checkout/upstream were exact at `0 0`, and Blocks 15–25
  remain unopened. The direct-user full-tracker request remains Blocks 0–25;
  this transition does not contract the remaining range.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Execution brief: add one closed `Adjust supervision` operation over the exact
  current policy/group, using only fields proven adjustable by the maintained
  helper and binding schedule fields to their exact affected automations.
  Preview a minimal before/after diff, preserved fields, next policy version,
  owner request, actual automation targets/schedules, and compensation posture;
  verify policy-history and every affected live automation independently. Reuse
  the accepted operation coordinator and current projections. Do not write
  policy/history JSON or automation TOML, add a settings store/scheduler, read
  or send Gmail, or open any Block 15+ control.
- Continuation acknowledgement and work start: routed incident
  `INC-20260811-001923-2AADC3` is continuation evidence only and does not replace
  the direct-user authority above. The earlier platform usage-limit failure did
  not terminalize this run. From exact pushed activation `dbf765c`, Block 14
  work resumed by reading the maintained `adjust` field/range contract, current
  validated policy/history shape, route-purpose/role bindings, and exact
  watcher, meta-review, and optional Gmail automation schedule mappings. No
  accepted Block was reopened, no policy/history or automation manifest was
  mutated, and Blocks 15–25 remain closed.
- Current recovery acknowledgement and affected work start: routed incident
  `INC-20260811-010358-90B60A` and route action
  `60b36fa586670686d571733870637b827735a86ce40e7c6f6fbcb8b774dc0cb7`
  are recovery evidence only; direct-user item 44 and mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`
  remain governing. The interrupted browser assertion was recomputed only for
  the current live run: its canonical lifecycle is `failed`, so the existing
  immediate-check owner correctly returns its exact unavailable alert instead
  of a preview. The affected policy-workflow browser case then passed 3/3 with
  invocation-scoped `--workers=1` at desktop, tablet, and mobile, including the
  exact policy diff, disabled unbound Gmail fields, recovery posture, and no
  historical-mission control leakage. No unaffected browser matrix was replayed.
- Product-capability review:
  - Trigger: Block 14 has consequential posture.
  - Frame identity: this tracker, `Target-product capability frame`, Block 14,
    SHA-256
    `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
  - Capability added or preserved: one operator-confirmed exact policy diff can
    be requested from the current run while policy-history and each affected
    named automation remain separately verified.
  - Paths compared: a local dashboard/settings write, a bounded extension of
    the accepted operation framework, and the existing supervision plus Codex
    automation owners.
  - Selected level and owner: the accepted operation framework coordinates one
    exact reviewer/fix-executor request; `supervision_log.py adjust` and the
    Codex automation owner remain the only canonical writers.
  - Protected-capability result: policy versions/history, route gates,
    unchanged fields, named-automation single-writer ownership, partial-state
    attention, and no automatic rollback are preserved.
  - Rejected alternatives: direct JSON/TOML writes bypass canonical owners; a
    generic settings store or scheduler has no current source-backed consumer.
  - Tradeoffs and uncertainty: task-mediated application is asynchronous and
    canonical records do not expose fix-executor actor attribution; Gmail
    cadence stays unavailable unless its exact gate and automation are bound.
  - Frozen-candidate proof: product commit
    `4690e2a2ae87ea2a12fbdaa50f356574b54b5f7a`, tree
    `56f2278518af234185b7424f4172e8e9deba67a7`, parent
    `e9a8dd6c382ab8646524d1e472291d2e61da6766`, pushed exactly to
    `origin/codex/evolution-mvp`; live preview and mapped proof are recorded
    below.
- Implementation candidate: the 14-file product revision above registers
  `factory.supervision-adjust` as the fifteenth supported closed operation,
  derives the nine-field/range contract from the maintained owner, binds exact
  target/project/mission, reviewer and fix-executor tasks, route source, prior
  policy head, preserved values, next normalized policy root, and only affected
  automations. Dispatch starts one exact reviewer turn after source recheck;
  verification requires its exact marker, one exact next `policy-adjust`
  history record with four correlation values, current policy head, and every
  named active automation schedule/binding. The React run workspace exposes a
  compact functional diff dialog, current values/ranges, conditional Gmail
  availability, reconciliation facts, partial/failure recovery, and no control
  on predecessor missions. The binary diff SHA-256 is
  `00da2f87efa3e3912dec25b860e0c226d6ea9bf67a1c200f79353821d38d0baa`.
- Validation archive: the focused policy-workflow and target-specific
  projection tests pass with the corrected repository-owned Python envelope
  `PYTHONPATH=src:tests:../..`; the complete workflow module passed 12/12, the
  operations module passed 25/25, and full backend discovery passed with
  `ResourceWarning` fatal. Ruff passed the four affected Python files. Focused
  frontend proof passed four files/18 tests, full Vitest passed 18 files/76
  tests, and the TypeScript production build passed. The affected live
  Playwright case passed 3/3 after the lifecycle-aware correction. A live
  current-target preview created operation `op_jeqc-ryjg8-yjdS3`, showed policy
  v5 with its exact previewed SHA-256 to expected v6, routine cadence 20 to 25,
  eight preserved fields, the exact watcher automation,
  semantic-escalation route allowance, and source `EVT-000131`; it was
  cancelled before request, remained
  `cancelled`, and left policy/history/automations unchanged. Direct-write and
  diff scans are clean. Full-profile verification reports all 26 Blocks with 0
  errors/warnings, all 30 verifier tests pass, and the documentation diff check
  is clean. Independent exact-revision acceptance remains pending.
- Rejected exact review: evidence revision
  `90651775142017dc2a6af7d65c2fdad5a92c67c0`, tree
  `2c5b7e85dd2a2a956481cd80098227e60e98d35c`, and product revision
  `4690e2a2ae87ea2a12fbdaa50f356574b54b5f7a`, tree
  `56f2278518af234185b7424f4172e8e9deba67a7`, remain immutable rejected
  history. Independent review found one material row: the maintained
  `gmail-cadence` owner derives one bound automation's desired RRULE from quiet,
  active, and active-window fields, while the candidate mapped only the quiet
  field and assumed quiet mode. Active/window-only changes could therefore
  produce an empty affected set and policy-only success, and quiet changes
  during an active window could reject the owner-correct active RRULE. The
  reviewer reproduced both cases; focused backend 37/37 with `ResourceWarning`
  fatal, Ruff, full-profile 0/0, verifier 30/30, remote identity, diff, and Stop
  proof otherwise passed, with no unaffected browser replay.
- Gmail-cadence successor: product commit
  `0c1b0fdfea9f033c622205df6d257e716f14870a`, tree
  `55e5fecd39f427a74e9b330fc65b3cc613d34903`, parent
  `90651775142017dc2a6af7d65c2fdad5a92c67c0`, is pushed exactly to
  `origin/codex/evolution-mvp`. Its ten-file diff has SHA-256
  `69dcb8949105c284a0314ee4a898766623680188c5bf684e79ee4b4ee5d0d388`.
  All three Gmail cadence fields now identify `gmail_gate`; multiple changed
  fields deduplicate to one named automation. Current projection and
  post-policy verification invoke the maintained `gmail-cadence` owner, retain
  active/quiet mode, and compare the actual manifest to its current
  `desired_rrule`; volatile seconds-to-quiet are excluded from the preview
  fingerprint while mode, active-until, policy values, and source identity
  remain bound. Unavailable cadence fails closed, the UI no longer claims no
  affected schedule owner, and active mode is displayed in reconciliation.
- Successor proof: the exact three adversarial backend cases passed, then the
  complete affected workflow and operations modules passed 38/38 with
  `ResourceWarning` fatal. They prove all three fields map to one automation,
  current active interval 1 is reconciled rather than compared to quiet
  interval 2, a three-field next policy re-resolves active interval 2 exactly
  once, and actual interval 2 is partial while owner-desired interval remains
  1. Ruff and diff checks passed. Affected frontend proof passed three files and
  16 tests plus the run workspace's 3/3, the production build passed, and the
  exact live drill-down Playwright case passed 3/3 across desktop, tablet, and
  mobile with invocation-scoped `--workers=1`. At this successor freeze,
  exact-revision acceptance was pending and Blocks 15–25 remained closed.
- Fresh exact acceptance: independent delta review accepted exact evidence
  revision `58b26b0ff95230ab164219f55af529c949b7afc5`, tree
  `f7ee7de2f02e3fa2a00ec18418fa845d1b9b2954`, and product revision
  `0c1b0fdfea9f033c622205df6d257e716f14870a`, tree
  `55e5fecd39f427a74e9b330fc65b3cc613d34903`, with no material finding. The
  reviewer independently reproduced backend 38/38 with `ResourceWarning`
  fatal, Ruff, affected frontend three files/16 tests, TypeScript/build,
  full-profile verification for all 26 Blocks with 0 errors/warnings, verifier
  tests 30/30, exact diff/hash, clean checkout, remote `0 0`, and the Block 14
  Stop. The recorded live browser 3/3 proof was reused without replay. Policy
  history and every affected automation are separately verified through their
  maintained owners; no direct policy/history/TOML writer or Block 15+ control
  was introduced.

### Stop

Stop before repairing bindings or performing pause/resume, mission, continuity,
report, evolution, or terminal operations.

---

## Block 15 — Mission and target/tracker binding repair

Status: `accepted`

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
- Treat materially different mission intent as Block 25 mission succession,
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

- Activation: Block 15 started automatically from accepted and pushed Block 14
  checkpoint `c3ec9ca4cfd86a510e0fdde4817d60e929076cfc`, tree
  `c238fab2e1ed362be1897f764d26bfff83ab10cb`; dependencies 7, 10, and 11
  are accepted, the checkout/upstream are exact at `0 0`, and Blocks 16–25
  remain unopened. The direct-user full-tracker request remains Blocks 0–25;
  this transition does not contract the remaining range.
- Governing implementation authority: direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  The maintained optional implementation-range gate remains unavailable: the
  persisted item text hashes to
  `ff144b6e23b4fb416d8fac84731a9f26c2ef3d2dc9d8ba9d59ffdd029a3aa601`,
  while the legacy mission binding records source hash
  `5ef3d610b6c78be26652df2b4639fad218dd555765a95683d785097fd521dd21`;
  the owner therefore rejects a range bind rather than accepting normalized
  display text. Mandatory local reconciliation still identifies Block 15 as
  the next required Block and preserves the full remaining range.
- Execution brief: add one closed tuple-repair operation for a reproduced
  missing mission binding only when the selected run already has exact target,
  project, tracker-path, and tracker-root identity. Preview the missing current
  field, exact expected mission root/source, current policy head, preserved
  tracker identity, owner request, prohibited effects, and next policy
  postcondition; route one bounded request to the maintained reviewer and fix
  executor, and verify the next canonical `policy-bind` record plus unchanged
  tracker/target identity and no duplicate group. Existing incompatible
  mission bindings, target/tracker drift, ambiguous groups, arbitrary paths,
  or different intent remain unavailable and fail closed. Do not write policy
  or ledger files, add tracker fields to `bind`, create a repair database, or
  open any Block 16+ control.
- Product-capability review: `consequential`; the maintained `bind` owner can
  derive and add a missing direct-user mission binding, but it has no tracker-
  path, tracker-root, or target-association repair field and refuses a
  different existing mission. The selected implementation therefore exposes
  only that supported missing-field transition and treats the exact target,
  project, tracker path/content root, task marker, policy head, and owner
  revision as immutable proof inputs. Extending `bind`, writing policy/history
  directly, scanning unrelated groups, accepting operator-supplied paths, or
  creating a generic reconciliation store were rejected because each would
  establish a second authority or exceed the maintained postcondition. An
  ephemeral owner preview proves the exact next normalized policy and
  `policy-bind` record while tests prove canonical policy/history bytes remain
  unchanged.
- Implementation candidate: commit
  `a38ab04dfbba8a2e2eab926cc78a4413a73b46bb`, tree
  `87c8356b7d26c530a535a74675806b503dab79bb`, parent
  `120e9fc0283cf067d2aad9a3621f4cb5a9f4fc9e`; representative blobs are
  operation coordinator
  `1a7bbe5123c6584d263229c514c70996f0f677f0`, maintained-owner projection
  `89a704033f1bbec5f4731f84f910b36b6f50d6ba`, run control
  `7a3240482b031e92ae5b45e46e399a87b6825aa2`, and browser proof
  `3683c6d82eccf556320db49c2b7a6fd657b3a4aa`. The closed operation accepts no
  input fields, resolves one exact current dashboard implementation marker and
  direct-user item, previews the maintained owner in a disposable root, routes
  one reviewer request, and verifies the single next policy record plus
  unchanged target/tracker/history/current-owner facts. Existing missions,
  partial task history, source or policy drift, different semantics, and
  unsupported tuple repair remain unavailable.
- Focused and mapped validation: exact owner/API tests passed 27 plus 13 tests
  with `ResourceWarning` fatal, and Ruff passed. The two affected frontend
  suites passed 14 tests, TypeScript and the production build passed, and the
  isolated missing-binding browser fixture passed 3/3 across desktop, tablet,
  and mobile, including current visibility, empty-input preview facts,
  confirmation gating, historical suppression, one heading, and no horizontal
  overflow. The live exact runtime was healthy with App Server available,
  advertised 17 registered operations including this supported descriptor,
  and rejected the current not-loaded target with
  `binding_repair_target_mismatch` before a route request. Owner-focused
  negatives prove healthy and materially different missions reject, partial
  task history and changed owner revision cannot verify, and the disposable
  preview does not mutate canonical bytes. Full-profile tracker verification
  passed all 26 Blocks, all 30 verifier tests passed, diff checks were clean,
  the candidate is pushed, and local/upstream are `0 0`.
- Proportional-replay note: one attempted pre-freeze broad live drill-down run
  stopped at its pre-existing expectation that Issue follow-up be disabled;
  the current live incident posture now enables it. The three affected binding
  cases in that run passed, and the unrelated assertion was neither rewritten
  nor used as Block 15 evidence. The binding assertions were isolated in the
  focused fixture above, which then passed all three viewports without replaying
  the unaffected matrix.
- Rejected exact-revision candidate: the independent audit of evidence commit
  `1bd991da09b888c2597c652767252f8bf062caa6`, tree
  `a4c9b3b172e36bdb9a0cde0decdb558abe491c72`, and product commit
  `a38ab04dfbba8a2e2eab926cc78a4413a73b46bb` rejected acceptance. The App
  Server projection silently bounded user text and treated every projected
  `userMessage` as direct-user authority; the verifier omitted exact source
  item/hash and live-target status from its postcondition; and the source and
  verifier did not require the canonical run-path project claim to agree with
  the task/tracker project. Its green focused suites remain diagnostic only.
- Correction boundary: routed incident
  `INC-20260811-030055-388652` and action root
  `4940242ad5264d9de5b98a9becf01839cda1473206052a06f4b9d883166a619e`
  required the operator action to remain only confirmation to request review,
  never source attestation, provenance, or authority. Governing implementation
  authority remains the direct-user item and mission root recorded above; the
  routed correction is provenance only. Blocks 16–25 stayed closed.
- Corrected product successor: commit
  `2f835f8339e49dd1f23c5066d2954dee4b6e942e`, tree
  `bf15f35cc966055f5738447f5910694aafda6962`, parent rejected evidence
  `1bd991da09b888c2597c652767252f8bf062caa6`. Representative blobs are App
  Server projection `a6838db6ae1cb2e37fdd0b9d3de6c06ba92b96f6`, workflow owner
  `679ff791e5ac97143f54218263890b0239b4df6d`, run-project projection
  `a33935bbbf322e97fada0cfb3540f05e320d6ea5`, operation dialog
  `8523818a6d64d2a3e56098e0fa8bc371a1288370`, run actions
  `7560fff49384ab661dfc0f7015b921abaa2d00f3`, and responsive styles
  `4426ed51ba96f92714a78c9cfc724cf6fe991361`. The projection now retains the
  full-byte user-content root, truncation, transport classification, client ID,
  and an explicitly unverified authority status. Routed and dashboard-generated
  messages are ineligible. The source and postcondition recheck the exact live
  task, full source tuple, tracker, and canonical run/project claim.
- Independent-authority gate: `REQUEST BINDING REVIEW` starts only the bounded
  reviewer request. Dispatch evidence remains
  `unverified-reviewer-verification-required` and contains no attestation. A
  canonical bind is not accepted as this operation's repair until the exact
  configured reviewer turn completes with one full, hash-checked
  `SOFTWARE_FACTORY_DASHBOARD_BINDING_AUTHORITY_REVIEW` result matching the
  source bytes, client, tracker, mission, intent, reviewer, and preview. Missing,
  partial, truncated, wrong, routed, generated, or unverifiable source/review
  evidence yields no verified bind. The dialog labels the candidate and exposes
  exact values without truncating them; it does not call the operator action
  attestation or direct-user proof.
- Corrected affected proof: App Server 19/19, operations 27/27, and workflow
  13/13 tests passed with `ResourceWarning` fatal; Ruff passed. The two affected
  frontend files passed 14/14 tests, TypeScript and the production build passed,
  and the one focused browser case passed 3/3 at desktop, tablet, and mobile
  with full source identities, historical suppression, one heading, and no
  overflow. A diagnostic earlier run exposed generic identity ellipsis in the
  confirmation dialog; the corrected exact-value rendering then passed all
  three viewports. The restarted loopback runtime at port 8787 reported healthy
  App Server compatibility; live item 44 projected root
  `ff144b6e23b4fb416d8fac84731a9f26c2ef3d2dc9d8ba9d59ffdd029a3aa601`,
  `ordinary-user-message`, and `unverified`, while routed item 46 projected root
  `80d12529a3d8a66cd7f0e446b1902130950f968943898f5ac242a518a7459613`,
  `routed-delegation`, and `ineligible`. The full-profile verifier passed all 26
  Blocks with zero errors/warnings, all 30 verifier tests passed, diff checks
  were clean, and the corrected product successor was pushed. Block 15 remains
  `in-progress` pending ordinary exact-revision acceptance.
- Exact review of that successor: independent audit REJECTED exact evidence
  `1b953b0a98c38a7c2fd6e7f2ce36122e127b08f6`, tree
  `68cb7f41e940e1b9fc35e720b0312daa4197df42`, and product
  `2f835f8339e49dd1f23c5066d2954dee4b6e942e`, tree
  `bf15f35cc966055f5738447f5910694aafda6962`, on two remaining rows. First,
  the projection hashed only joined text and bounded the client ID, so a valid
  text-plus-image source or an ellipsized long client identity could be
  accepted without complete source identity. Second, reviewer and fix executor
  were required to differ from each other but not from the implementation
  target, allowing the independent review/writer boundary to collapse. The
  reviewer reproduced both adversarially. Its exact backend 59/59, Ruff,
  frontend 14/14, build, verifier 26/0/0 plus 30/30, diff, remote, and Stop
  proof remains reusable; its browser attempt stopped at an unrelated live
  enablement precondition and is diagnostic only.
- Two-row product successor: commit
  `195387dca16dbbdd20cae11e5deda394b5a019d9`, tree
  `aff978ce0b82a5928499c0804d1b750f682e0c95`, parent rejected evidence
  `1b953b0a98c38a7c2fd6e7f2ce36122e127b08f6`. Representative blobs are App
  Server projection `c62071a75833fa5b3030588183f5cd9e3fae0a2b`, workflow owner
  `740becd5603705c352872e573e9c715441eb5a8c`, exact-value dialog
  `392bc9f79659c30809b59e59f1bc7982efb62cb9`, and browser proof
  `76a097c81eaca6c6f0e908e656605be9a7efa550`. The projection now preserves a
  canonical SHA-256 root for the entire user-content envelope and its ordered
  part types, retains the full client ID without ellipsis, and classifies every
  shape other than one exact text part as ineligible for this owner. The source
  gate recomputes that single-text envelope root and carries it through source,
  request, reviewer verification, fingerprint, preview, UI, and postcondition.
  The implementation target, reviewer, and fix executor must now be three
  distinct exact task IDs before any request can route.
- Delta-only proof for `195387d`: the affected App Server 19/19 and workflow
  13/13 tests passed with `ResourceWarning` fatal, including text-plus-image
  rejection, exact 300-character client retention, complete-envelope identity,
  both target/role collapse variants, and current reviewer proof; Ruff passed.
  The affected frontend suites passed 14/14, TypeScript/production build passed,
  and the single preview case passed 3/3 at desktop, tablet, and mobile while
  rendering the full text root, envelope root, 300-character client ID, neutral
  authority posture, historical suppression, and no horizontal overflow. The
  restarted port-8787 runtime is healthy: live item 44 retains text root
  `ff144b6e23b4fb416d8fac84731a9f26c2ef3d2dc9d8ba9d59ffdd029a3aa601`
  and exact envelope root
  `3788926f90dd6987d405a4f70534583e86b1ae3303b0159cfa664cfe8daf81f2`
  with one text part and unverified authority; routed item 46 retains envelope
  root `8fabdcad02b924baee9c62c753fd0fff61bd15fc74b105574a3e12d1ffd33216`
  and remains ineligible. Unaffected operations and tracker proof were reused
  exactly as permitted by the rejected audit. The product successor is pushed;
  Block 15 remains `in-progress` pending fresh exact-revision acceptance.
- Fresh exact-revision outcome: ACCEPTED for evidence commit
  `7b0584663d670d1fc63b8df6e54234d5b4c2676d`, tree
  `8f5d944855eedc4873f36ec0a70aba9e1d2fc9a9`, and product commit
  `195387dca16dbbdd20cae11e5deda394b5a019d9`, tree
  `aff978ce0b82a5928499c0804d1b750f682e0c95`, with no material finding.
  Exact probes accepted one text part plus a full 300-character client ID and
  rejected two-text, image, skill, mention, and mismatched-envelope sources;
  reviewer/currentness binding retained the envelope and client identity, and
  target/reviewer/fix task collapse rejected before routing. The reviewer
  reproduced affected backend 32/32 with `ResourceWarning` fatal, Ruff,
  frontend 14/14, production build, verifier 26/0/0 plus 30/30 tests, clean
  diffs, clean checkout, remote `0 0`, and the Stop. The exact recorded 3/3
  browser proof remains valid; current external project-unassigned drift
  prevented an unnecessary re-entry through its enablement precondition and
  was not treated as a candidate defect. Block 15 is accepted; Blocks 16–25
  remain unopened at this checkpoint.

### Stop

Stop before repairing role-task or automation bindings or performing policy,
lifecycle, continuity, report, evolution, or terminal operations.

---

## Block 16 — Role-task binding repair

Status: `accepted`

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

- Activation: Block 16 started automatically from accepted and pushed Block 15
  checkpoint `3b960552010bc21edaa3757da84dbbbe42e46e01`, tree
  `6deeccfa2ccfa2e2cf30a7d193e01a231f95e249`; dependencies 7, 10, and 11
  are accepted, checkout/upstream are exact at `0 0`, and Blocks 17–29 remain
  unopened. Governing implementation authority remains direct-user item 44 at
  `codex:019fe547-e054-7ca0-9940-ec4aa146df78:019fe572-0536-7692-8505-c8624eefa7ab:item-44`
  under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
  the requested range remains the full current Blocks 0–29.
- Work-start boundary: inspect the exact maintained task, policy/bind, and route
  owners and select only one supported role/task repair with separate task and
  canonical policy postconditions. Current live project association is
  unavailable, so live state remains read-only and mutation proof will use a
  disposable exact group/task. Do not infer candidates from labels, create a
  generic role directory, touch automation bindings, or open later work.
- Product-capability review: `consequential`; the maintained `bind` owner and
  purpose router jointly support a narrow missing-role repair for base reviewer,
  notice reviewer, fix executor, Gmail processor, and roundup writer. Watcher,
  effectiveness reviewer, target, and Gmail-gate replacement do not have the
  same maintained bind-and-route postcondition and therefore remain explicitly
  unavailable. The implementation derives exactly one prior task ID from the
  hash-chain-validated policy history, requires the current role to be empty,
  rejects current or historical use under another role, and never searches by
  title. It accepts only an exact durable idle or not-loaded OpenAI task with
  complete history, no active turn, no existing dashboard-workflow marker, a
  non-conflicting project claim, and the exact canonical working-directory
  inode. The frozen App Server thread schema exposes provider and the exact
  owner-controlled persisted task path but not model/effort fields. The adapter
  therefore reads only that ID-suffixed, owner-controlled session file's latest
  exact `turn_context` within an 8 MiB tail bound and requires its observed model
  and effort to equal the canonical role contract; missing, partial, unsafe,
  changing, stale, or mismatched evidence is unavailable rather than inferred.
- Owner and recovery boundary: preview exercises the maintained `bind` owner on
  an ephemeral copy and proves that only the selected missing runtime field,
  policy version/hash/time, and next `policy-bind` record would change. Execute
  re-reads the exact task, then under the projection-owner lock rechecks the
  policy hash/version, history head/count, owner revision, lifecycle, exact
  task-observed model/effort, empty role, single-role candidate, and current
  catalog/run-project claim before invoking `cmd_bind` once. Verification
  independently re-reads the unchanged complete task and persisted contract,
  exact next policy/history postcondition, mission, unrelated roles/automations,
  current catalog/run-project claim, and maintained role-purpose route gate.
  Route denial or any partial postcondition remains `unverified` with manual
  inspection recovery; there is no task create, resume, turn-start, retry,
  replacement, direct policy/history write, or automation effect.
- Implementation candidate: initial product commit
  `1c92924e2eb5a8fbd3a711d29e75a32e9ed28e7b`, tree
  `0bc30702b11b2c2525260e1f7488b4710f5728fc`, added the closed operation,
  maintained-owner adapter, run/Admin control, activity facts, and responsive
  proof. First frozen product candidate
  `5973c4c90cf0d8798749a21be982eaab3397a439`, tree
  `634024d61b0c2dc9f49f3e8b46d7d4bf46f77b90`, parent
  `b163e3cd8b8b4510e5bd7f0902e2e7f9975f2023`, preserves that scope while
  replacing a duplicate execution-time ephemeral preview with exact head,
  owner, lifecycle, role, and model rechecks. Representative blobs are
  maintained projection `d77525772e15f23308b139dfc8f1b2520cfedd38`, workflow
  owner `e134b660e43d7bd2d50a09eddba848c7547ddf6e`, workflow proof
  `11839c36988459b959d4cd333abda1756f9200fc`, projection proof
  `9d2efb29f09fd403ed11e4f84660e42cc01ef9f9`, run control
  `03f099bb3881864da1f8ee1942e2b729ffb8986f`, activity panel
  `5fd54f57cf80b6ec8bb071c76be6e970d4661343`, and browser proof
  `34d72b4b266fada154180d5144f1325012b1726c`.
- Exact mapped proof: the full backend suite passed 108/108 with
  `ResourceWarning` fatal and Ruff passed. Projection proof includes an exact
  stale-history-count attempt that raises `role_binding_source_stale` with
  canonical policy bytes unchanged; the disposable HTTP exercise passed through
  the real API, existing task read, maintained `cmd_bind`, canonical
  policy/history, and maintained route gate while proving task before/after
  identity and unrelated roles. The full frontend check passed 18 files and
  80/80 tests, TypeScript and the production build passed, and the isolated
  missing-role browser fixture passed 3/3 at desktop, tablet, and mobile with
  current-mission visibility, exact task/role/lifecycle/model/route facts,
  typed confirmation, historical suppression, one heading, and no horizontal
  overflow. An initial browser fixture lacked a missing-role projection and was
  corrected to model the required source state; its green successor is the only
  browser acceptance evidence. A prior aggregate backend run exposed the
  generic three-second test-client deadline after redundant preview work; the
  exact-head optimization above then passed the focused HTTP path and two
  consecutive 108-test aggregate runs without weakening a currentness gate.
- First-candidate live and Stop proof: the restarted exact loopback runtime at
  port 8787 reports
  healthy runtime, frontend, catalog, tracker, supervision, and App Server
  coverage and advertises 18 operations including the supported role-binding
  descriptor. Its descriptor lists only the five supported role families and
  the unavailable replacements and schema observation limits above. Current
  live project association remains unavailable, so no live policy mutation was
  attempted. The product and proof commits are pushed with local/upstream
  `0 0`; the full-profile verifier passed all 26 Blocks with zero errors and
  warnings, all 30 verifier tests passed, and diff checks are clean. The
  then-current Block 17 automation repair, now Block 20, remained unopened.
  Block 16 stayed `in-progress` pending fresh independent exact-revision review.
- Rejected exact-revision candidate: independent audit REJECTED evidence commit
  `8a9c8f38ae7985d5e9f8647bb18d5ef427acd575`, tree
  `2051c98670b5f49ee839e35e92a694d7eb18bead`, and product
  `5973c4c90cf0d8798749a21be982eaab3397a439`, tree
  `634024d61b0c2dc9f49f3e8b46d7d4bf46f77b90`, on three material rows. The
  task gate accepted per-turn `items_truncated=true` and its fingerprint omitted
  exact retained item history; dispatch/verification did not independently
  recheck the captured catalog/run-project claim at the owner boundary; and the
  UI presented policy-required model/effort as governed task eligibility even
  though actual task model/effort was unavailable. The reviewer reproduced a
  partial-history acceptance and a changed project claim reaching one bind, and
  confirmed any OpenAI-provider task could pass the model gate. Its exact
  backend 43/43, Ruff, frontend 16/16, build, verifier 26/0/0 plus 30/30, clean
  diff/checkout, remote `0 0`, and Stop proof remain reusable only for unaffected
  rows.
- Three-row product successor: commit
  `8ecf0e4667fbc9b6c5024cafe8e8a7d152144263`, tree
  `3d78bf95acb51ace210ca5b0a4af50b4b68617d1`, parent rejected evidence
  `8a9c8f38ae7985d5e9f8647bb18d5ef427acd575`. Representative blobs are App
  Server adapter `8f24747705574fd483e1d98bcc7b70fc326a37b0`, workflow
  owner `25643ecbbb88d37ea7f170ea97677c5458ca5eb1`, App Server proof
  `d391d4c4ab8bbc4de77c02497d76b69fbaca4681`, workflow proof
  `fc0337cefc029e612410848179b6c52e96f15c1e`, truth-labeled dialog
  `7d47494fe3828cff99bb291f0b83e14f7f2706a2`, and browser proof
  `a1fb95f429ee8d521d1d7b05e5a603f628991e77`. That successor added bounded
  persisted-source reading, rejected unsafe or changing sources, and stopped
  returning path or content. Role eligibility now rejects any truncated turn or
  item history, fingerprints the complete retained turn projection, and
  requires exact task-observed model and effort to equal policy. Dispatch
  rechecks catalog and run/project identity immediately before `cmd_bind`;
  verification rechecks it again before the route gate and exposes the separate
  postcondition.
- Final owner-root hardening successor: commit
  `7e9d05efc5e28cc053bccc727b2e76ac35aec46c`, tree
  `96bf1120b898c9780c8f9e81746e30c2302dfbcc`, parent
  `8ecf0e4667fbc9b6c5024cafe8e8a7d152144263`. Current representative blobs are
  App Server adapter `c32beaf0400b4f14846ed0f5d2a3a0ceaba17ef2`, App Server proof
  `fa85d26653edfd783d64b9197eff7d5e9d7ec34b`, workflow owner
  `25643ecbbb88d37ea7f170ea97677c5458ca5eb1`, workflow proof
  `fc0337cefc029e612410848179b6c52e96f15c1e`, truth-labeled dialog
  `7d47494fe3828cff99bb291f0b83e14f7f2706a2`, dialog proof
  `332e7b8d29e8770e5c4b983269b8a2e0a4c67d68`, and browser proof
  `a1fb95f429ee8d521d1d7b05e5a603f628991e77`. The adapter now accepts only an
  exact absolute, non-symlinked, ID-suffixed path beneath the exact
  initialize-time Codex owner root at
  `sessions/YYYY/MM/DD/rollout-*-<task-id>.jsonl`; it requires owner UID,
  rejects group/world-write permission, verifies stable device/inode/size/mtime
  across the bounded read, and clears the root with the App Server generation.
  Missing, changing, stale, oversized, or owner-root-external sources remain
  unavailable and cannot authorize a bind.
- Corrected affected proof: App Server 20/20 and workflow 15/15 tests passed
  with `ResourceWarning` fatal, and Ruff passed. Focused adversarial fixtures
  reject missing/symlinked persisted task sources, `items_truncated=true`, wrong
  observed effort, and changed project claims with zero bind; the postcondition
  also reports project drift as `unverified` and does not call the route gate.
  The affected dialog suite passed 4/4, TypeScript and production build passed,
  and the exact browser case passed 3/3 at desktop, tablet, and mobile while
  showing separate `Required role model` and `Task-observed model` facts,
  historical suppression, one heading, and no overflow. One broad frontend run
  retained 79/80 passing tests but hit the unrelated pre-existing five-second
  timeout in `floor-page.test.tsx`; it changed no source and is diagnostic, not
  successor proof. The prior exact full 80/80 frontend result remains reusable
  for unaffected files.
- Live final-source proof: a fresh exact 0.145.0 App Server read of task
  `019fe547-e054-7ca0-9940-ec4aa146df78` resolved its persisted source within
  the 8 MiB bound and observed `gpt-5.6-sol` with effort `max` plus exact record
  root `0ec629ba08069db750e749ca8d26804ddb8a66d60ef2397189a0e3363bb63022`;
  this deliberately demonstrates that actual effort is distinct from a role's
  required `xhigh` and would fail closed. The final pushed successor
  `7e9d05efc5e28cc053bccc727b2e76ac35aec46c` is running on
  loopback port 8787 with healthy complete coverage and available App Server;
  no live policy mutation was attempted. Local/upstream were `0 0`, the
  then-current Block 17 automation repair, now Block 20, remained unopened, and
  Block 16 remained `in-progress` pending mechanical proof and fresh
  exact-revision review.
- Rejected owner-root successor review: independent exact-revision audit
  REJECTED evidence `a95acfc62f098404653a1c6c73dc12a5ee7b9a0d`, tree
  `ba8696fe8acf0f1a8d7cb63549bb49605079333f`, and parent/product
  `7e9d05efc5e28cc053bccc727b2e76ac35aec46c`, tree
  `96bf1120b898c9780c8f9e81746e30c2302dfbcc`. The three prior rows were
  closed, but the reviewer reproduced one Stop violation: candidate derivation
  scanned role assignments from every policy-history mission and successfully
  bound a task known only to predecessor mission A into current successor
  mission B. Its backend 35/35, Ruff, dialog 4/4, build, browser 3/3, live
  owner-root read, verifier 26/0/0 plus 30/30, exact remote/clean, and three-row
  closure proof remain reusable for unaffected scope only.
- Current-mission correction: product successor
  `e15e95b2c59d7bbc50a93556dbdf7e0ad5c941a0`, tree
  `d9c9b60812e91eb9421aab13a6aee9a4d37cb9aa`, parent rejected evidence
  `a95acfc62f098404653a1c6c73dc12a5ee7b9a0d`. The current operations owner
  blob is `3d605609832b6cacbaf6d006da248cfc79407bdf`; focused proof blob is
  `80b789277ab6c99a45f89789a40f3d88a88fac8a`. Candidate derivation and
  historical cross-role conflict checks now consider only snapshots whose full
  canonical `mission_binding` equals the current policy binding; missing
  current mission identity is unavailable. A predecessor-only notice-reviewer
  fixture now returns `role_binding_task_authority_unavailable` with the policy
  bytes unchanged, while the exact valid same-mission preview/apply regression
  still passes.
- Affected correction proof: the predecessor-only and valid same-mission tests
  passed 2/2; the full operations projection module passed 29/29 with
  `ResourceWarning` fatal; the two mapped HTTP and task/policy/route role-repair
  workflow tests passed; Ruff and diff checks passed. Reusable unchanged proof
  remains bound to the exact rejected candidate as stated above. The exact
  successor is pushed, local/upstream are `0 0`, the loopback runtime was
  restarted at port 8787 and reports complete healthy coverage with App Server
  available, no binding was attempted, all later work remained unopened, and
  Block 16 remained `in-progress` pending fresh exact-revision review.
- Accepted exact-revision outcome: independent delta audit ACCEPTED evidence
  `6754476c07436f8e3e178c60f8a20fc4b36c9063`, tree
  `11beb2a855b4dbb1cebd6c68f6fe2fee964c0d57`, and parent/product
  `e15e95b2c59d7bbc50a93556dbdf7e0ad5c941a0`, tree
  `d9c9b60812e91eb9421aab13a6aee9a4d37cb9aa`. The reviewer verified exact
  full-current-`mission_binding` candidate and conflict scoping, predecessor
  rejection with unchanged bytes and no apply path, valid same-mission repair,
  and an adversarial case where a predecessor's incompatible-role claim could
  not contaminate the current candidate. Focused 2/2 ResourceWarning-fatal,
  Ruff, full-profile 26/0/0, verifier 30/30, diff/clean, and remote `0 0` proof
  passed; the prior accepted owner-root, backend, frontend, build, and browser
  evidence remained exact and reusable. Post-block audit: `accepted`; retained
  open Block 16 work: none. Later Blocks remain unopened.

### Stop

Stop before Factory Floor/tracker/operation presentation refinement, automation
binding repair, pause/resume, mission succession, successor-task continuity,
reporting, evolution, or terminal lifecycle.

---

## Block 17 — Factory Floor operational rows and exact count filters

Status: `accepted`

### Objective

Make implementations, runs, and supervisor groups scannable as compact,
expandable, source-backed operational rows with honest tracker totals, active-
Block claims, and status-filter counts.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator identify current work, its exact
  supervision relationship, attention posture, and freshness from one compact
  row, then disclose only the evidence needed to decide or act.
- Potential capability loss or regression: compacting the current four-column
  view could merge task/run/mission/group identities, hide critical attention,
  imply unsupported progress, or turn returned-row counts into false totals.
- Protected-capability effect: preserves exact project/task/run/mission/group/
  role identity, source-local failure, explicit coverage, source drill-down,
  sparse navigation, and progressive disclosure.
- Architecture and operating-model effect: adapts the existing Factory Floor
  React view and, only where required for exact identity/coverage, its typed
  read-only Block 6 projection; it adds no new status owner or history store.
- Tradeoff and source evidence: the direct design steer selected Beautiful UI's
  compact row and count-chip grammar but rejected its demo semantics and wider
  AI-workspace shell. The smaller collapsed surface improves scanning while
  retaining exact evidence in expansion.

### Inputs and dependencies

- Accepted Blocks 6 and 7 factory-floor composition and drill-downs.
- Beautiful UI `components/TaskRows.tsx`, copied through the site's supplied
  `Copy` action from <https://beautiful-ui-five.vercel.app/> with SHA-256
  `665e31820b041600662fcffff044d6a4994ecd18059d5e8ef1026251bf996b0e`.
- Beautiful UI `components/FilterTable.tsx`, copied through the same supplied
  action with SHA-256
  `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4`.

### Required work

- Adapt the supplied `TaskRows.tsx` baseline into a typed reusable operational
  row. Preserve its compact button, disclosure transition, status marker,
  chevron, detail rail, and keyboard-native button semantics; remove timers,
  autonomous demo transitions, fictitious records, inline demo icons, and
  unsupported retry behavior.
- Make each collapsed Factory Floor row expose exact project and implementation
  task identity, task lifecycle, supervision run/mission/group and named role
  identities, exact total parsed tracker Block count, every current active Block
  number and concise tracker-owned heading, checkpoint or unavailable posture,
  attention/failure state, and observation freshness without merging those
  identities into one label. Derive the total only from the maintained
  tracker/verifier projection, never from returned rows or heading heuristics.
- Preserve tracker-status, current implementation-task, and current supervision-
  mission active-Block claims as separately source-labeled values. If they
  disagree, show each claim and degrade the row as `Conflict`; never coalesce
  them or carry a predecessor mission's active Block into the current row.
  Render `None active`, `Unavailable`, or `Partial` when those are the exact
  source postures.
- Make expansion show only source-backed checkpoints, exact open issues and
  bounded recovery, maintained-owner actions, current conclusions, and safe
  workspace/source links, including the exact tracker heading/status plus the
  task and supervision records supporting each active claim. Reuse existing
  projections and operation activity; add only the minimum typed read-only
  projection fields required for exact current-mission identity, tracker total,
  plural active claims, title, or coverage label.
- Adapt the supplied `FilterTable.tsx` chip structure for `All`,
  `Active/Running`, `Attention`, `Blocked/Failed`, and `Completed`, while
  retaining current project/severity/time controls. Define every category from
  existing exact lifecycle, attention, and accepted-state contracts.
- Label chip counts exact only when the owner coverage is complete and rows are
  untruncated. Otherwise show returned/lower-bound, partial, or unavailable
  posture in the chip and accessible name; never derive an exact total from the
  visible bounded array.
- Preserve current design tokens, sparse shell, URL-restorable filters, fixed
  source inspector, reduced-motion behavior, and existing React/TypeScript/
  Vite stack. Use headings only where they orient a distinct region; add no
  marketing title or explanatory subheader.

### Scope and non-goals

- In scope: Factory Floor primary rows, its high-signal filters/counts, minimum
  typed read-only identity/coverage support, and exact responsive behavior.
- Not in scope: tracker-list refinement, operation diffs, a failure-mode
  workspace, sidebar replacement, chat/prompt/recommendation UI, new progress
  calculation, mutation controls, or a second floor data owner.
- Do not adopt gallery source data, copy its product semantics, or label owner
  activity as thinking/reasoning.

### Deliverables and recorded state

- Adapted operational-row and filter-chip components, Factory Floor
  integration, any minimal typed projection delta, provenance note, and focused
  unit/component/browser/accessibility tests.

### Resource and economy contract

Reuse the current bounded Factory Floor response and lazy/controlled disclosure.
Do not fetch historical bodies for collapsed rows. Widen the read model only
for a reproduced missing exact field; after a correction rerun affected rows,
filters, and viewports rather than unrelated workspaces.

### QA and independent review

- Test exact and conflicting identities; one, multiple, and no active Blocks;
  task/tracker/supervision disagreement; predecessor-only and stale mission
  claims; malformed, zero-Block, partial, and truncated tracker projections;
  active/completed/failed/unavailable lifecycle; missing mission/role/
  checkpoint; critical attention; stale observations; long Block headings,
  IDs, and text; and no invented progress or recovery.
- Browser-test disclosure by pointer and keyboard, `aria-expanded`/controlled
  region linkage, focus visibility, reduced motion, desktop/tablet/mobile, and
  no horizontal overflow.
- Independent UI/truth review compares every collapsed claim and sampled
  expansion fact with the exact current owner response and verifies that the
  supplied source was adapted rather than independently approximated.

### Acceptance

- The collapsed list answers who/what/where/state/attention/freshness for every
  represented implementation and supervisor group without identity merging;
  expansion reaches exact checkpoints, issues/recovery, actions, conclusions,
  and sources.
- Every supported row shows an exact maintained-verifier total such as
  `26 Blocks` and every current active Block as exact number plus tracker-owned
  heading. None, unavailable, partial, and conflicting source claims are
  explicit, and expansion reaches the exact tracker/task/supervision evidence.
- Filter counts and accessible labels are exact, explicitly lower-bound/
  returned, partial, or unavailable according to owner coverage.
- The adapted rows remain usable at all maintained viewports and by keyboard,
  with no page-level overflow, fabricated data, new navigation shell, or
  mutation path.

### Negative tests

- Reject an exact-looking chip count from truncated/partial rows, a progress
  percentage not owned by the tracker, a total derived from visible rows or
  heading heuristics, a plural active set collapsed to one Block, or a current
  active/supervisor label derived from predecessor-only evidence.
- Reject a confident total for a malformed/zero-Block/partial projection or a
  unified active label when tracker, task, and supervision claims disagree.
- Reject disclosure that merges task/run/mission/group IDs, hides a critical
  failure, fetches unbounded history, or exposes demo retry controls.

### Completion evidence

- Activation and authority: started automatically from independently accepted
  and pushed tracker revision
  `d7205631540411cdabb355594f1f231b8cb15271`, tree
  `9aa13cf4e5e597a1694d5a141e69d8e58d408334`; accepted Blocks 6 and 7 satisfy
  every dependency, local/upstream are exact at `0 0`, and Blocks 18–29 remain
  unopened. Governing implementation authority is direct-user item 44 under
  mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
  routed design packets are provenance only.
- Work-start boundary: re-read this Block and inspect the accepted Factory Floor
  projection, React route/contracts/tests, and the exact supplied
  `TaskRows.tsx` and `FilterTable.tsx` baselines. The first implementation work
  is limited to the compact disclosure/filter surface and the minimum typed
  read-only fields needed for exact tracker totals, plural current active claims,
  source disagreement, and coverage. No tracker-review, operation, mutation,
  automation, lifecycle, reporting, or later-Block work is started.
- Frozen product candidate: commit
  `9db88126858ebb7bd3abceacb6fa4e510909db69`, tree
  `27ff467ef47ee9309e07e921b9e8e151000589f4`, parent
  `325bde5c102f312b533a4ecf1f49dfe2a3f2a429`. Its exact 12-file product and
  test delta adds only the typed read-only Block-claim projection, adapted
  operational disclosure/count-chip components, Factory Floor integration,
  responsive styling, and focused proof. The copied-source provenance remains
  explicit in code for Beautiful UI `TaskRows.tsx` SHA-256
  `665e31820b041600662fcffff044d6a4994ecd18059d5e8ef1026251bf996b0e`
  and `FilterTable.tsx` SHA-256
  `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4`;
  demo data, timers, autonomous state, retry controls, and unsupported product
  semantics are absent.
- Product and truth proof: exact tracker totals require one canonical tracker
  association plus a valid, complete, nonzero maintained-verifier Block set;
  malformed, zero-Block, partial, candidate, or ambiguous sources fail to
  partial/unavailable. Tracker status, complete current task marker, and exact
  current supervision-mission activity remain three separately labeled claims;
  plural sets are preserved, disagreement degrades to `Conflict`, and
  predecessor mission claims are excluded. The live loopback response on port
  8787 exercised the real ambiguous four-candidate/current-task-not-loaded
  posture and rendered `Blocks unavailable` with the source claims separated,
  rather than inferring an association.
- Validation: the focused server suite passed 9/9 and the full server suite
  passed 112/112 with `ResourceWarning` fatal; Ruff passed. The exact frontend
  candidate passed 18 files/84 tests invocation-scoped with one worker,
  TypeScript, the production build, and focused API/Floor 10/10. A preceding
  default-parallel frontend run preserved one diagnostic 5-second timeout in
  the interaction-heavy Floor test; the same test passed alone and in the
  unchanged-harness serial run, so no global worker or timeout setting was
  changed. Exact live Playwright passed 3/3 at desktop, tablet, and mobile with
  keyboard disclosure, Axe, and horizontal-overflow checks. Visual inspection
  confirmed compact collapsed rows, readable two-/one-column expansion, sparse
  regional headings, and no marketing subheader. The full-profile tracker
  verifier passed Blocks 0-29 with 0 errors/warnings, all 30 verifier tests
  passed, and staged/committed diff checks are clean.
- Stop proof: no tracker queue or source-diff refinement, operation preview,
  mutation, automation binding, lifecycle, continuity, reporting, evolution,
  or later-Block implementation was added. Block 17 remains `in-progress`
  pending an independent exact-revision product/truth review of this candidate;
  Blocks 18-29 remain unopened.
- Rejected exact-revision outcome: independent audit REJECTED evidence
  `0bcbdbdab383aabc3a59130f7b665a43d36248d2`, tree
  `eedfb8d6020a1bf129bedf68ba2b0a0b531316f6`, and product parent
  `9db88126858ebb7bd3abceacb6fa4e510909db69`. It found two material truth
  rows: task-owner `None active` was excluded from cross-source comparison, so
  tracker/supervision Block 6 plus task None stayed falsely exact/green; and the
  advertised Floor fingerprint omitted the consumed task workflow marker, so a
  Block 6-to-5 marker change altered the rendered conflict posture without
  altering its source revision. Exact remote/diff/Stop proof, focused Python
  9/9, Ruff, frontend 84/84, build, full-profile 0/0, and verifier 30/30 passed;
  an independent full Python run reached 111/112 with one unchanged task-API
  three-second HTTP timeout. The prior exact 112/112 candidate result and all
  unaffected proof remain reusable; the rejected revision is not acceptance.
- Corrected product successor: commit
  `9b8a1d7769958baa480bccae4b718fc227f8fc4f`, tree
  `e5bf7ab6f282231d6c8028fc0920d51f52301062`, parent
  `0bcbdbdab383aabc3a59130f7b665a43d36248d2`. Its exact two-file delta includes
  every explicit `exact` or `none` owner claim in set comparison, keeps
  `notLoaded`/unknown task lifecycle unavailable rather than recasting it as
  none, and binds the semantic fingerprint to task `updated_at`, history/item
  coverage, and the exact consumed workflow marker. The affected Floor suite
  passed 11/11 with `ResourceWarning` fatal, Ruff and diff checks passed, and
  the restarted loopback server at port 8787 reports the current live row as
  partial with tracker/task unavailable and current supervision Block 17 kept
  separate. Unaffected frontend/build/browser and full backend proof remains
  bound to the preserved candidate. Block 17 remains `in-progress` pending a
  fresh independent delta review; Blocks 18-29 remain unopened.
- Accepted exact-revision outcome: independent delta audit ACCEPTED evidence
  `55d5ee9ff788b04038015fc0e864410771ffe16f`, tree
  `84253f3dee0cdd4bd9cdb70b139667df6c07901f`, and product parent
  `9b8a1d7769958baa480bccae4b718fc227f8fc4f`. Exact adversarial proof showed
  task None plus tracker/supervision Block 6 now produces conflict/amber;
  `notLoaded` and unsupported task states remain unavailable/partial; workflow
  marker, turn-coverage, and item-coverage changes each alter the semantic
  fingerprint while read-time-only refresh remains stable. The affected Floor
  suite passed 11/11 with `ResourceWarning` fatal, Ruff passed, full-profile
  verification remained Blocks 0-29 with 0 errors/warnings, verifier tests
  passed 30/30, and remote `0 0`, clean diff, and Stop proof passed. Post-block
  audit: `accepted`; retained open Block 17 work: none. Blocks 19-29 remain
  unopened.

### Stop

Stop before tracker-review refinement, automation binding repair, operation
semantic diffs, pause/resume, continuity, reporting, evolution, or lifecycle.

---

## Block 18 — Tracker review queue and exact count filters

Status: `accepted`

### Objective

Make tracker review a compact source-backed queue whose progress, active-Block
claims, and filter counts remain exact, bounded, and read-only.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator find the tracker needing review
  and understand its exact total, current active work, progress, and attention
  posture without opening a deep inspector.
- Potential capability loss or regression: status normalization or counts from
  bounded rows could hide verifier/task/supervision disagreement, imply
  acceptance, or present one active Block when multiple claims exist.
- Protected-capability effect: preserves tracker Markdown/Git/verifier
  authority, exact content/currentness roots, source drill-down, partial
  coverage, and the absence of a second authoring or acceptance path.
- Architecture and operating-model effect: adapts the existing tracker index
  and read-only progress projection; it introduces no dashboard tracker writer,
  task-state owner, or supervision interpretation.
- Tradeoff and source evidence: the selected Beautiful UI count-chip grammar
  is denser and easier to scan, but every total and active claim must remain
  bound to an exact owner projection rather than visible rows or demo state.

### Inputs and dependencies

- Accepted Blocks 3 and 8 tracker/Git projection and review workspace.
- Supplied Beautiful UI `components/FilterTable.tsx` at SHA-256
  `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4`.

### Required work

- Adapt the supplied filter-chip structure into the tracker index for `All`,
  `Active/Running`, `Attention`, `Blocked/Failed`, and `Completed`, with the
  existing project filter. Map categories explicitly from parsed tracker,
  verifier, Git, and run-binding posture rather than label heuristics.
- Make counts exact only for complete unbounded tracker coverage; otherwise
  render returned/lower-bound, partial, or unavailable posture in visible and
  accessible labels.
- Show the maintained verifier's exact total parsed Block count on every
  supported tracker row and selected-tracker progress summary. Beside it show
  every current active Block as exact number plus concise tracker-owned heading;
  do not assume the set is singular or derive it from visible rows/headings.
- Keep tracker-status, current implementation-task, and current supervision-
  mission active-Block claims separately source-labeled. Display all claims and
  degrade to `Conflict` on disagreement. Exclude predecessor-only claims and
  render `None active`, `Unavailable`, or `Partial` exactly when warranted.
- Provide drill-down from every active claim to the exact tracker heading and
  status plus the task/supervision evidence supporting it; never equate the
  existing accepted-status count with active work.
- Keep the workspace read-only: no content editing, author/review/implement
  start, status mutation, acceptance, staging, or direct Git write. Preserve
  sparse page chrome and avoid redundant page-explaining headers.

### Scope and non-goals

- In scope: tracker list filtering/counts, exact total and plural active-Block
  progress claims, conflict/coverage posture, and exact source navigation.
- Not in scope: tracker source diffs, operation previews, a repository diff
  viewer, tracker editor, acceptance workflow, failure-mode/recovery workspace,
  or revival of the previously omitted side-task scope without canonical
  authority.
- The adapted filter component may be reused later, but this Block owns only
  tracker queue/progress discovery.

### Deliverables and recorded state

- Adapted exact-count filter component, bounded typed tracker/progress contract,
  tracker list/detail integration, provenance note, and focused tests.

### Resource and economy contract

Reuse the maintained tracker/verifier projection and existing current task/
mission bindings. Do not scan history or fetch source bodies for collapsed
rows. Widen only for an explicit exact active-claim drill-down.

### QA and independent review

- Test full/partial/unavailable index coverage; malformed and zero-Block
  trackers; active, blocked, failed, completed, dirty, stale, untracked, and
  verifier-conflict rows; one active Block, multiple active Blocks, none active,
  task/tracker/supervision disagreement, stale/predecessor mission, long titles,
  truncation, safe rendering, and exact source navigation.
- Browser-test chip selection, URL restoration, active-claim links and screen-
  reader labels, keyboard behavior, desktop/tablet/mobile, dark mode, and no
  overflow.
- Independent tracker/UI review compares totals, active claims, counts, and
  coverage labels with exact maintained verifier/task/supervision output and
  verifies no mutation/acceptance path.

### Acceptance

- The operator can find trackers by truthful high-signal posture and every chip
  count discloses exact, lower-bound/returned, partial, or unavailable coverage.
- Every supported tracker row and selected progress surface shows the exact
  parsed total and every current active Block number/title; none, unavailable,
  partial, predecessor, and conflicting claims remain explicit and source-
  drillable.
- No tracker edit, task start, status write, Git write, or acceptance control is
  exposed.

### Negative tests

- Reject counts derived from only visible/truncated rows, a status inferred from
  color, an exact total for malformed/zero-Block/partial data, or a total derived
  from headings rather than the maintained verifier projection.
- Reject a plural active set collapsed to one, accepted count presented as
  active, a predecessor claim presented as current, coalesced disagreement, or
  any UI action that bypasses the maintained authoring/review/implementation
  owner.

### Completion evidence

- Activation and authority: started automatically from independently accepted
  and pushed Block 17 evidence revision
  `55d5ee9ff788b04038015fc0e864410771ffe16f`; accepted Blocks 3 and 8 satisfy
  every direct dependency, local/upstream were exact at `0 0`, and Blocks
  19-29 remain unopened. Governing implementation authority remains direct-user
  item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
  routed design/count packets remain provenance only.
- Work-start boundary: re-read this Block and inspect only the accepted tracker
  list/detail projection, typed API contracts, tracker routes/tests, and the
  already adapted `FilterTable.tsx` count-chip component. The first work is
  limited to truthful tracker queue/count/progress discovery, plural current
  claims, and exact source navigation. No tracker source diff, operation,
  mutation, automation, lifecycle, continuity, reporting, evolution, or later-
  Block work is started.
- Product candidate: commit
  `9464d648d990b62685f91a70dac204f8e1548516`, tree
  `ad0b75dc3b266bacae1e13c559730e67f0a68291`, parent/activation
  `32b9e2415cfc4c815152e6cf2ecbac727bdcd768`, pushed at local/upstream
  `0 0`. The maintained tracker projection now emits each in-progress Block's
  exact number, title, status, heading line, and status line; the strict web
  schema preserves that read-only owner output.
- Queue and progress truth: the tracker index reuses the accepted Beautiful UI
  `FilterTable.tsx` count-chip adaptation at frozen supplied-source SHA-256
  `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4`.
  It shows verifier-established nonzero totals, plural tracker/task/current-
  mission claims, explicit none/partial/unavailable/conflict postures, exact
  source links, and exact or returned/lower-bound filter counts. Noncanonical,
  cross-project, contradictory, truncated, or dynamically relevant unbound
  Floor rows cannot make a count exact; terminal tasks are not inferred failed,
  and header-conflicted all-accepted trackers are not called completed.
- Focused proof: backend tracker projection passed 6/6 with
  `ResourceWarning` fatal and Ruff passed. Exact affected frontend/schema tests
  passed 17/17 and the production TypeScript/Vite build passed; focused cases
  cover one/multiple/no active Blocks, long titles, malformed/zero totals,
  partial/truncated and predecessor claims, source conflict, noncanonical
  associations, successful terminal posture, and task-only mappings without a
  fabricated `/runs/null` link. The full backend suite passed 114/114; the
  reusable full frontend regression passed 88/88 before the final task-only
  guard, whose exact affected suite and build then passed.
- Browser and live proof: the exact candidate's tracker-queue case passed 3/3
  on desktop/tablet/mobile with keyboard chip activation, URL restoration,
  source navigation, one `h1`, Axe serious/critical violations zero, and no
  horizontal overflow. Twelve unaffected tracker workspace/control cases from
  the immediately preceding candidate remained green; the corrected
  unavailable-row case separately passed 3/3. Live loopback `127.0.0.1:8787`
  returned 30 verifier Blocks and current `Block 18 — Tracker review queue and
  exact count filters`; visual inspection confirmed sparse chrome and truthful
  lower-bound/completed/attention labels.
- Mechanical proof: full-profile verification remained Blocks 0-29 with 0
  errors/warnings, all 30 verifier tests passed, `git diff --check` passed, and
  the Block Stop held: no tracker editor, new task-start/acceptance path,
  semantic diff, operation, automation, lifecycle, continuity, reporting, or
  later-Block surface was added. Candidate audit posture: implementation
  complete, independent exact-revision outcome pending.
- Rejected exact review: independent audit rejected evidence revision
  `c2cd6a9d35d62c9d9c86f916c78559f169524194` because inactive completed
  Floor rows could contaminate current claims; maintained App Server
  `systemError`/terminal work was omitted from `Blocked / Failed`; and
  noncanonical idle candidates, recovered previous catalog data, or an unknown
  project URL could still yield apparently exact counts. The rejected product
  and its otherwise valid proof remain immutable diagnostic evidence.
- Correction candidate: commit
  `6f75a88f6aff6f7621ca2f08eba0c3e995bef0b9`, tree
  `cda3b6f46803f7696e0905a763c999bb56e2f200`, parent rejected evidence
  `c2cd6a9d35d62c9d9c86f916c78559f169524194`, pushed at local/upstream
  `0 0`. Current task and current supervision claims are now selected
  independently from active/current owner states; inactive completed/stopped
  associations cannot enter current comparison or run links. Exact associated
  terminal tasks retain the maintained `systemError` failure meaning for the
  blocked filter. Any candidate/ambiguous association or recovered previous
  enumeration makes dynamic/all counts partial, and an unknown project URL
  falls back to the represented all-project set rather than an exact empty set.
- Correction proof: the affected tracker/Floor/schema set passed 26/26, the
  narrower tracker/schema set passed 20/20, TypeScript/Vite production build
  passed, `git diff --check` passed, and six exact desktop/tablet/mobile browser
  cases passed with keyboard, Axe, source-navigation, partial-state, and
  overflow checks. Adversarial fixtures directly prove current Block 1 remains
  exact beside an inactive completed `None active` row; terminal system error
  produces `Blocked / Failed: 1 exact`; idle-green candidate attention and
  recovered catalog enumeration are lower-bound/partial; and an unknown
  project URL renders the known tracker set. Successor exact-review outcome:
  pending.
- Rejected successor review: independent audit rejected evidence revision
  `82990f0d56975d471edbe1b5f4b03d5931f7cd10` on one remaining currentness
  edge: an idle task on an otherwise completed or stopped supervision row
  could still contribute its historical `None active` task claim and create a
  false conflict. The terminal/completed fixture did not exercise that edge;
  every other rejected row was confirmed closed.
- Currentness successor: commit
  `81a3ba98471cdbbe7ade92b675d89d4d2f5f2539`, tree
  `b1b53f18a10b06ceba42746981e598f9ea12593f`, parent rejected evidence
  `82990f0d56975d471edbe1b5f4b03d5931f7cd10`, pushed at local/upstream
  `0 0`. One shared predicate now admits a task claim only when the task is
  active/idle and its supervision lifecycle is neither completed nor stopped;
  supervision claims use their separate current-state predicate. The focused
  tracker workspace passed 15/15, the production build and diff check passed,
  and the adversarial fixture now adds both idle/completed and idle/stopped
  historical rows beside current Block 1 without changing its exact posture.
  Exact-review outcome: pending.
- Accepted exact-revision outcome: independent delta audit ACCEPTED evidence
  `4251ac3f7b233e49e2e85785703231e00c8994d3`, tree
  `7f210f2fe8f0ebb9e49e65076feb85667417fe67`, and product parent
  `81a3ba98471cdbbe7ade92b675d89d4d2f5f2539`, tree
  `b1b53f18a10b06ceba42746981e598f9ea12593f`, with no material finding.
  Exact probes confirmed current Block 1 remains exact beside idle/completed
  and idle/stopped historical rows while current task-only and supervision-
  only claims remain independently represented. Terminal/system-error remains
  `Blocked / Failed: 1 exact`; candidate attention and recovered enumeration
  remain partial; unknown project URLs fall back to represented projects.
  Affected Vitest passed 15/15, production build passed, full-profile verifier
  remained Blocks 0-29 with 0 errors/warnings, verifier tests passed 30/30,
  diff/clean/remote `0 0` and exact remote identity passed, and the Stop held.
  Post-block audit: `accepted`; retained open Block 18 work: none.

### Stop

Stop before tracker source diffs, automation binding repair, operation semantic
diffs, pause/resume, continuity, reporting, evolution, or lifecycle operations.

---

## Block 19 — Tracker semantic source diffs

Status: `accepted`

### Objective

Show bounded, exact semantic changes for one selected tracker without creating
an editor, acceptance path, or generic repository-diff surface.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator inspect what changed in the
  selected tracker and reach the exact before/after source and currentness
  evidence without shell archaeology.
- Potential capability loss or regression: an attractive red/green diff could
  imply acceptance, disclose unrelated repository changes, or present a bounded
  excerpt as the complete change.
- Protected-capability effect: preserves tracker Markdown/Git/verifier
  authority, exact content/currentness roots, partial coverage, safe source
  drill-down, and the absence of a second authoring or acceptance path.
- Architecture and operating-model effect: adapts one read-only detail
  projection through the existing Git/tracker owner; it adds no dashboard
  tracker writer or browser-side diff authority.
- Tradeoff and source evidence: the selected compact semantic row grammar is
  easier to scan than a raw patch, but the owner must supply every comparison
  and unsupported or unavailable bases remain explicit.

### Inputs and dependencies

- Accepted Blocks 3 and 8 tracker/Git projection and review workspace.
- Supplied Beautiful UI `components/DiffTable.tsx`, copied through the site's
  `Copy` action, at SHA-256
  `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2`.

### Required work

- Adapt the supplied `DiffTable.tsx` row structure, semantic added/removed/
  changed styling, compact table grammar, and non-color cues into a bounded
  tracker source-difference view. Remove demo stages, timers, fictitious data,
  and menu-cleanup semantics.
- Project exact tracker-file changes only through the existing Git/tracker
  owner: change kind, before/after text or unavailable posture, source path and
  line/Block anchor, working/committed content roots, owning revision,
  currentness/fingerprint, verifier posture, bounds, and safe source drill-down.
- Keep long or sensitive unrelated repository diffs out of the payload. A
  truncated diff must state its bound and cannot support an exact no-change or
  complete-change claim.
- Keep the view read-only: no content editing, author/review/implement start,
  status mutation, acceptance, staging, or direct Git write. Preserve sparse
  page chrome and avoid redundant page-explaining headers.

### Scope and non-goals

- In scope: one selected tracker's bounded semantic source differences through
  the current tracker/Git owners.
- Not in scope: queue filtering/counts, operation previews, a generic repository
  diff viewer, tracker editor, acceptance workflow, failure-mode/recovery
  workspace, or a second Git/tracker owner.
- The adapted diff component may be reused later, but this Block owns only the
  selected-tracker source comparison.

### Deliverables and recorded state

- Adapted semantic-diff component, bounded typed tracker/Git contract, selected-
  tracker detail integration, provenance note, and focused tests.

### Resource and economy contract

Compute a bounded diff only for the selected tracker and current Git state;
reuse cached tracker/Git currentness keys and lazy-load details. Do not scan or
return unrelated repository changes. Widen only after an explicit source
drill-down and never beyond the declared safe tracker-file bound.

### QA and independent review

- Test added/removed/changed/no-change, rename/unavailable base, dirty/stale/
  untracked and verifier-conflict state, truncation, long lines, hostile text,
  safe rendering, exact source navigation, and partial/unavailable owner state.
- Browser-test semantic table keyboard/screen-reader cues, non-color meaning,
  desktop/tablet/mobile, dark mode, and no overflow.
- Independent tracker/UI review compares diff samples with exact maintained Git
  and verifier output and verifies no unrelated disclosure or mutation/
  acceptance path.

### Acceptance

- A selected tracker shows bounded added/removed/changed source rows with exact
  owner identity, roots/currentness, limitations, and drill-down; truncated or
  unavailable data never becomes a complete/no-change claim.
- No unrelated repository content is exposed and no tracker edit, task start,
  status write, Git write, or acceptance control exists.

### Negative tests

- Reject a diff whose before/after root cannot be tied to the selected tracker
  and current Git state, or whose truncated subset is labeled complete.
- Reject executable/active diff content, unrelated repository disclosure,
  browser-derived semantic authority, or a UI action that bypasses the
  maintained authoring/review/implementation owner.

### Completion evidence

- Activation and authority: started automatically from independently accepted
  and pushed Block 18 evidence revision
  `4251ac3f7b233e49e2e85785703231e00c8994d3`; accepted Blocks 3 and 8 satisfy
  every direct dependency, local/upstream were exact at `0 0`, and Blocks
  20-29 remain unopened. Governing implementation authority remains direct-user
  item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`;
  Beautiful UI source is design provenance only.
- Work-start boundary: re-read this Block and inspect only the accepted lazy
  tracker-file Git diff owner, current tracker/Git typed contracts, selected-
  tracker Evidence view/tests, and the frozen supplied `DiffTable.tsx` source.
  First work is limited to one selected tracker's bounded read-only semantic
  source comparison. No generic repository diff, editor, author/review/
  implement start, acceptance, operation preview, automation, lifecycle,
  continuity, reporting, evolution, or later-Block work is started.
- Product candidate: commit
  `816935d109be7f34b8bc63e6d393497c56cc2bfa`, tree
  `1072088619f1e2604f12ba7833e865b5cc5828e0`, parent Block 18 transition
  `27e91ec21a3d0357d5c0b14cc1ade048b924316a`, pushed with local/upstream
  `0 0` and exact remote identity. The maintained tracker/Git adapter now
  emits at most 200 selected-file semantic rows with 600-character side
  bounds, exact HEAD/working roots, source path and line/Block anchors,
  owning revision, verifier posture, limitations, and a currentness
  fingerprint. Exact-revision and working-root source routes fail closed on
  unsafe files, stale content, missing commits, or mid-projection tracker,
  verifier, or HEAD changes. The client cross-validates every embedded root,
  owner, count, side, and completion claim before rendering.
- Supplied-source adaptation: copied Beautiful UI
  `components/DiffTable.tsx` through the site's built-in source viewer at
  <https://beautiful-ui-five.vercel.app/>, source SHA-256
  `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2`.
  The adaptation retains its compact fixed-column table, semantic row tint,
  status dots, and explicit change cues while removing demo data, staged
  timers, menu semantics, and unsupported controls. It uses typed source rows,
  existing dashboard tokens, plain-text rendering, exact source links, and no
  browser-side diff parser or mutation action.
- Candidate validation: Ruff passed; focused backend tracker/API/currentness
  proof passed 26/26 with `ResourceWarning` fatal; full backend passed 117/117
  serially with `ResourceWarning` fatal. Focused tracker contract/component
  proof passed 23/23; full frontend passed 95/95 with invocation-scoped
  `--maxWorkers=1 --testTimeout=15000`; TypeScript and the production build
  passed. Playwright passed 18/18 across desktop/tablet/mobile, including
  added/removed/changed non-color cues, long and hostile literal text, exact
  before/after links, keyboard focus, theme switching, Axe, no document
  overflow, and no component mutation control. The full-profile verifier
  returned Blocks 0-29 with 0 errors/warnings and its tests passed 30/30;
  `git diff --check` passed. A deliberately parallel full-suite launch first
  produced unrelated five-second DOM and App Server timing failures; isolated
  reruns and the serial full proofs above passed without product or harness
  changes. Live exact-server checks returned a complete zero-row no-change
  semantic projection with matching HEAD/working roots and verified both
  immutable HEAD and content-hash source routes. Exact-review outcome:
  rejected at exact evidence revision
  `f205a046cb470cf4de95230b8d53ea943c83e879`, tree
  `1492414f4febef21b8d88d62658f842de79c9999`. The independent audit preserved
  every valid result above but found two bounded truth failures: historical Git
  blobs were read before enforcing the tracker byte ceiling and semantic
  matching/repeated Block metadata could exceed their resource budget; the
  client also accepted an inconsistent partial empty envelope that the route
  could render as exact no-change. Block 19 remained `in-progress`, later
  Blocks stayed closed, and the rejected candidate remains immutable history.
- Bounded correction product: commit
  `483d64d74eb77976ff8c990440db940dbbbcc9e3`, tree
  `3e24d753a33db393a9ce247d49b5160ef1995c0f`, parent rejected evidence
  `f205a046cb470cf4de95230b8d53ea943c83e879`, pushed with exact remote
  identity. Git blob metadata is now checked before content retrieval and any
  historical source over 4 MiB fails with `tracker_git_blob_too_large` and no
  blob body. Semantic comparison is limited to 512 KiB and 10,000 lines per
  side, uses bounded matching, caps repeated Block titles/anchors at 160/200
  characters with explicit truth labels, and fails unavailable outside the
  declared budget. The typed client rejects returned-row/total-row,
  truncation, metadata-bound, and no-change inconsistencies; the route renders
  no-change only for a complete untruncated zero-row result.
- Correction validation: Ruff passed and the full backend passed 119/119 with
  `ResourceWarning` fatal, including exact oversized-history rejection,
  bounded repeated-metadata response size, and a 6,000-line repetitive-input
  timing probe. Affected typed-contract/workspace tests passed 24/24;
  TypeScript and production build passed. Playwright passed 18/18 across
  desktop/tablet/mobile with keyboard, Axe, theme, safe hostile text, bounded
  heading posture, exact source links, no horizontal overflow, and no mutation
  control. Live exact-server proof returned a 2,994-byte, complete,
  untruncated, zero-row no-change envelope. The full-profile verifier returned
  Blocks 0-29 with 0 errors/warnings, verifier tests passed 30/30, and
  `git diff --check` passed. Fresh exact-review outcome: rejected at evidence
  revision `b00784f2d83780badabac1e58185d96a651a6788`, tree
  `1521769fb002cd2bc7b1ab5db5ac65ec4b5ddd38`. The audit independently closed
  the oversized historical blob, 380 KiB repeated-line, long-heading response,
  and partial/no-change envelope rows, but found one 10,000-line, 90,000-byte
  valid permutation that still held synchronous `SequenceMatcher` beyond ten
  seconds. The evidence stayed reusable; Block 19 remained `in-progress` and
  Blocks 20-29 remained closed.
- Matching-budget correction product: commit
  `b666e5bd25b55a075ab4d3f62ae6cb1d1d24c68d`, tree
  `c477f57971e37415ef604837ef5dbd6673937601`, parent rejected evidence
  `b00784f2d83780badabac1e58185d96a651a6788`, pushed exactly. Both raw and
  semantic tracker line comparisons now use one exact shortest-edit owner with
  a hard 250,000-operation budget; a comparison that exhausts the budget fails
  unavailable with no partial or no-change claim. The cited adversarial
  permutation now returns `tracker_semantic_complexity_exceeded` in 0.02
  seconds, while the useful 6,000-line repeated case remains available with its
  exact one-row addition. A 1,000-case bounded reconstruction probe preserved
  both exact sources. Ruff passed; affected tracker and HTTP tests passed 28/28
  with `ResourceWarning` fatal; `git diff --check` passed. The already accepted
  frontend 24/24, build, 18/18 responsive browser, verifier 30/30, remote, and
  Stop evidence is unaffected and reused. Fresh exact-review outcome: accepted
  with no material findings at exact evidence revision
  `e85154ba936f15878b0abb3c89c9308aa26bb26a`, tree
  `766b6a4552662fa148938121cc253ba0604cff9b`. The independent audit reproduced
  raw and semantic exhaustion in 0.0439 seconds, the useful repeated case in
  0.0055 seconds, the 1,000-case reconstruction/shortest-edit matrix, focused
  Python 12/12 with `ResourceWarning` fatal, Ruff, the 30-Block verifier with 0
  errors/warnings, verifier tests 30/30, links, diff, exact remote identity,
  cleanliness, and every read-only Stop. Block 19 is accepted only at this
  exact reviewed revision.

### Stop

Stop before automation binding repair, operation semantic diffs, pause/resume,
continuity, reporting, evolution, or lifecycle operations.

---

## Block 20 — Automation binding repair

Status: `accepted`

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

- Activation and authority: started automatically from independently accepted
  Block 19 evidence revision
  `e85154ba936f15878b0abb3c89c9308aa26bb26a`; direct dependencies Blocks 7,
  10, and 11 are accepted, local/upstream/remote are exact at `0 0`, and Blocks
  21-29 remain unopened. Governing implementation authority remains direct-user
  item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Work-start boundary: re-read Block 20 and begin with the maintained automation
  projection, automation-tool owner, policy/bind owner, existing operation
  registry, and their current tests. First work is limited to one exact
  automation/group-role mismatch and its dual postconditions; no operation
  semantic diff, pause/resume, continuity, report, evolution, or lifecycle
  surface is started.
- Product candidate: commit
  `95de6d70440bdf87ac2b10800bcb7bfeccff6318`, tree
  `bf89a8ae19fdb206c89a4a84ac2c0ea2335d28f2`, parent accepted Block 19
  transition `6da47ac26ccc55dfc7552abc414cec5765be2aeb`, pushed with exact local,
  upstream, and remote identity at `0 0`. It adds one closed
  `factory.supervision-repair-automation-binding` operation for the maintained
  watcher, reviewer, Gmail-gate, roundup-writer, and enabled weekly-report
  schedule families. The source resolver reads one exact policy and only the
  selected named manifest, derives schedule and timezone from the maintained
  policy/Gmail-cadence owner, hashes protected manifest fields without exposing
  prompts, and scans canonical policy claims only for the required duplicate-
  role proof. Missing/replacement IDs, invalid manifests, wrong kind/purpose,
  unavailable timezone, duplicate claims, terminal groups, stale project/
  policy/task state, and already-reconciled rows fail closed before dispatch.
- Owner and postcondition boundary: one typed confirmation and maintained
  `fix-execution` route gate may start the exact configured fix-executor task
  once. Its bounded prompt permits the Codex automation owner to update only
  active state, RRULE, or role-task target on the existing ID; it prohibits
  creation, replacement, deletion, direct TOML/JSON/history writes, broad
  rebind, cadence redesign, retry, and rollback. Verification separately
  requires the changed named manifest with protected identity preserved, the
  byte-identical policy version/hash/history head and mission/group-role-
  purpose claim, one duplicate-free canonical claim, the exact fix-executor
  marker, and a current route gate. Automation-changed/policy-pending,
  policy-current/automation-pending, denied, stale, duplicate, and unverified
  results remain explicit recovery postures rather than success.
- Operator surface: current-run actions show the repair only for a source-
  projected repairable mismatch, with an exact role/purpose and automation ID,
  current-to-expected target and schedule, timezone posture, dual completion,
  and no-rollback recovery facts. Reconciled, unavailable, unsupported, and
  historical-mission rows expose no repair action. The compact action strip
  remains responsive without adding a page banner or explanatory header.
- Validation: Ruff passed the full server source/tests; focused projection and
  workflow suites passed 31/31 and 16/16 with `ResourceWarning` fatal, and the
  full backend passed 122/122 with `ResourceWarning` fatal. Focused typed-
  contract/action/truth tests passed 20/20; the full frontend passed 97/97 with
  invocation-scoped `--maxWorkers=1 --testTimeout=15000`, and TypeScript plus
  the production build passed. The first parallel full frontend run had one
  unrelated pre-existing five-second Floor-test timeout; the serial full proof
  passed without a harness or product change. Focused Playwright passed 3/3 at
  desktop/tablet/mobile with exact preview facts, disabled consequential
  confirmation, Axe serious/critical 0, one functional `h1`, no horizontal
  overflow, and no historical-mission action. Its first mobile pass exposed a
  16-pixel intrinsic select overflow, which the product candidate corrected by
  bounding action selects and mobile action width before the clean 3/3 rerun.
  Live loopback reads registered the new operation as supported and returned
  reconciled watcher/reviewer rows with exact purposes, interval-timezone
  posture, and no repair action; no live automation or policy mutation was
  attempted. The full-profile verifier returned Blocks 0-29 with 0 errors and
  0 warnings, verifier tests passed 30/30, `git diff --check` passed, and the
  Block 20 Stop remained closed.
- Rejected exact revision retained as evidence: independent review rejected
  exact evidence commit `b35afc0f5438d098331437dad8f4eaa78a8de4f6`, tree
  `074e3ca9fdb262c0fe83df4edc3da13cf64c7947`, for four bounded truth gaps in
  product `95de6d70440bdf87ac2b10800bcb7bfeccff6318`: the canonical role-target task
  was not proven existing/current/same-project; the fix executor was not bound
  to the selected project and repository root; a different-ID active heartbeat
  on the same exact role target escaped the duplicate verifier; and arbitrary
  nonempty roundup timezone text could be treated as supported without a
  separate automation-owner timezone postcondition. The reviewer otherwise
  reproduced Ruff, the 30-Block full verifier with 0 errors and 0 warnings,
  verifier tests 30/30, the recorded backend/frontend/build/browser proof,
  exact remote identity, clean diff, and the Block 20 Stop. The revision was
  not accepted and no later Block was opened.
- Bounded correction product: successor commit
  `6cbde0b70bcd7cd38952baa3ccd5824abd4ef1b4`, tree
  `9b0d02ddec003fc0d9ed323c07fe7bc1f7e24941`, parent rejected evidence
  `b35afc0f5438d098331437dad8f4eaa78a8de4f6`, is pushed with exact local,
  upstream, and remote identity. Source resolution now reads the exact
  canonical role-target task, permits only current App Server states, and
  requires its bound project and canonical cwd to remain inside the selected
  registered root. The fix executor has the same project/root constraint and
  is re-read with the role task at verification. A bounded automation-inventory
  scan proves active owners on the exact target: an unclaimed or same-role
  different ID blocks repair, while a separately claimed sibling role such as
  roundup writer versus weekly report remains distinct. Calendar roles accept
  only the maintained `America/Los_Angeles` contract and separately compare it
  with the local timezone used by the desktop automation owner; missing,
  different, or unsupported timezone truth is unavailable or non-repairable.
  The role task, fix executor, duplicate-owner set, and timezone are included
  in the source fingerprint and required again for applied verification.
- Correction proof: adversarial coverage rejects a missing/different role
  target, wrong-project binding, out-of-project fix cwd, unclaimed active
  duplicate owner, invalid `Mars/Olympus` policy timezone, and different owner
  timezone; it also preserves two independently claimed calendar automations
  on the shared roundup-writer task. The complete affected operations/workflow
  modules passed 48/48 with `ResourceWarning` fatal, Ruff passed all changed
  Python source/tests, the full frontend passed 97/97 with the existing
  invocation-scoped serial command, and TypeScript plus production build
  passed. Focused Playwright passed 3/3 at desktop/tablet/mobile with the exact
  duplicate/timezone preview facts, Axe serious/critical 0, one functional
  `h1`, no horizontal overflow, and no predecessor-mission action. The live
  loopback server was restarted on port 8787; health and App Server integration
  are available, and the current watcher/reviewer rows report exact duplicate
  coverage and reconciled interval-timezone posture. No live automation,
  policy, or task mutation was attempted. The full-profile verifier again
  returned Blocks 0-29 with 0 errors and 0 warnings, verifier tests passed
  30/30, and `git diff --check` passed.
- Rejected corrected revision retained as evidence: independent review rejected
  exact evidence commit `83277df7a2c31bc85f36b76aa911df18167ef96f`, tree
  `a1b849e990663e9dcc12dd697118a2d21e00b036`, and product
  `6cbde0b70bcd7cd38952baa3ccd5824abd4ef1b4` for one remaining resource/truth
  defect. The duplicate-role verifier called the global automation inventory,
  so it enumerated and fully parsed every manifest; one unrelated malformed
  automation therefore made an otherwise valid selected repair unavailable.
  The reviewer reproduced that exact unrelated-family failure while confirming
  the prior role-task, fix-executor, different-ID owner, and timezone findings
  were closed. The revision remains unaccepted and Block 21 stayed closed.
- Target-specific correction product: successor commit
  `edbc01ccb455d79e885a3e54bd958d22c86bd030`, tree
  `21fb66143c80ee735db0828ea3971ec6840a434d`, parent rejected evidence
  `83277df7a2c31bc85f36b76aa911df18167ef96f`, is pushed with exact local,
  upstream, and remote identity. The duplicate-role check now builds a bounded,
  repeatable index from only the canonical `target_thread_id` assignment and
  fully parses only the selected manifest plus manifests naming that exact role
  task. It adds no executable or package dependency. A malformed manifest with
  a different explicit target is neither projected nor reconciled by the
  repair and cannot disable it; a malformed manifest naming the exact selected
  target still fails duplicate coverage closed. General run reconciliation
  likewise scopes an unavailable manifest to its retained exact target hint
  instead of treating unrelated source corruption as selected-repair state.
- Target-specific correction proof: the exact unrelated-malformed fixture keeps
  the selected repair available and proves `_load_automation` received only the
  selected automation ID; changing the malformed fixture to the selected role
  target makes owner coverage unavailable, while the existing valid unclaimed
  duplicate still blocks repair. The complete affected operations/workflow
  suites passed 48/48 with `ResourceWarning` fatal, and Ruff passed the changed
  source/tests. The response and UI schema did not change, so the exact 97/97
  frontend, production build, and 3/3 responsive/Axe evidence above remains
  applicable and was not broadly replayed. The restarted exact server on
  `127.0.0.1:8787` reports service health, Codex App Server, and supervision
  sources available; the automation-binding operation is supported through its
  maintained owner, and current watcher/reviewer rows retain exact duplicate
  coverage and reconciled posture. No live mutation was attempted. The
  full-profile verifier returned Blocks 0-29 with 0 errors and 0 warnings,
  verifier tests passed 30/30, `git diff --check` passed, and the Block 20 Stop
  remained closed.
- Rejected target-specific revision retained as evidence: independent review
  rejected exact evidence commit
  `ace314424e66169ae1319a19beaa62cc063625d9`, tree
  `441ad05ec34f6ce78e26fe7fad9cf8423450cc2a`, and product
  `edbc01ccb455d79e885a3e54bd958d22c86bd030` because its supposedly
  target-specific index still enumerated every automation directory and read
  every manifest twice. The reviewer reproduced an unrelated invalid-UTF-8
  manifest disabling the selected repair while confirming the focused 32/32
  operations proof, Ruff, tracker verifier, exact identity, and Stop gates.
  That revision remains unaccepted and Block 21 stayed closed.
- Contained experiment: after that rejection, a persistent target-index/watch
  prototype was evaluated only as uncommitted work and removed before freeze.
  It was rejected because constructing and maintaining the index still reads
  unrelated automation families, adds a product-owned persistence/currentness
  responsibility, and exceeds this Block's one-policy/one-named-automation
  resource and no-bulk-reconciler boundaries. No watcher, index, manifest, or
  package from that experiment exists in the successor.
- Product-capability review: the exact 3,511-byte tracker capability frame is
  frozen at SHA-256
  `736124301d439cf6f143bb8013d53f085e9f3f4748df35451ef1bce5df0d8857`.
  The smallest local scan/index path was rejected because it couples one repair
  to unrelated sources; the selected bounded-general path is an injected,
  versioned, read-only target-query result with exact candidate IDs and
  expiring source/currentness identity. The maintained automation surface has
  exact-ID view/update ownership but no conforming list-by-target query, so the
  architectural-owner path is intentionally unavailable today rather than
  synthesized in the dashboard. This preserves exact automation/policy owners,
  protected fields, single-repair scope, and later-operation Stops at the cost
  of withholding repair until that dependency exists.
- Versioned-query correction product: successor commit
  `d55c2d6f6ec535fd5d5b3ffae3cac567af6fa679`, tree
  `737cffc6f880145ebd7967c885ba3807637eddb1`, parent rejected evidence
  `ace314424e66169ae1319a19beaa62cc063625d9`, is pushed with exact local,
  upstream, and remote identity. Its four-file delta removes the global target
  scan and defines a version-1 provider envelope containing exact target and
  sorted candidate IDs, source identity/revision, observed/expiry times, and a
  currentness identity. The repair reads only the selected automation plus the
  exact returned candidates, then repeats the query and rejects a changed
  result. Missing providers, incompatible or ambiguous envelopes, stale
  freshness, provider failure, mid-read changes, and unreadable or malformed
  selected-target candidates all leave duplicate coverage and repair
  unavailable. General dashboard inventory remains a separate read-only
  projection and is not called by this repair proof.
- Correction proof: the focused boundary and registry cases passed 5/5, and
  the complete affected operations/workflow modules passed 49/49 with
  `ResourceWarning` fatal. The fixtures prove a missing provider, expired
  result, duplicate/ambiguous candidate set, changed currentness, exact
  selected/candidate loading, malformed selected-target candidate, and an
  unrelated invalid-UTF-8 manifest whose ID is never passed to
  `_load_automation`. Ruff and `git diff --check` pass. The API/UI schemas are
  unchanged, so the prior exact 97/97 frontend, production build, and 3/3
  responsive/Axe evidence remains applicable and was not broadly replayed.
  The exact product server restarted on `127.0.0.1:8787`; health, Codex App
  Server, and supervision sources are available, while the automation-binding
  operation truthfully reports `unavailable` with the missing-provider reason.
  No live policy, automation, task, or supervision mutation was attempted.
- Rejected provider-bound revision retained as evidence: fresh independent
  review rejected exact evidence commit
  `48d391128e64a27a206e0e2267378cefd6507466`, tree
  `47ba1946ec478969c2a67012047442539212fc73`, and product
  `d55c2d6f6ec535fd5d5b3ffae3cac567af6fa679` for one exact-candidate
  consistency defect. A fresh stable provider response could include a valid
  non-selected manifest whose declared target differed from the queried role
  task; the implementation loaded it, silently excluded it from owners, and
  still marked coverage available and repairable. The review otherwise passed
  the affected backend 49/49 with `ResourceWarning` fatal, Ruff, full-profile
  verifier 0/0, verifier tests 30/30, exact remote/diff/fsck/Stop checks, and
  confirmed the persistent scan/index was absent. Block 21 stayed closed.
- Exact-candidate correction product: successor commit
  `f875faadce057e6c0c9be0504ab1d54e302b5ee8`, tree
  `081f0aec79d4fb8a425b23dfc23bb978b38b1d46`, parent rejected evidence
  `48d391128e64a27a206e0e2267378cefd6507466`, is pushed with exact local,
  upstream, and remote identity. Every ID returned by the exact-target provider
  must now load as an available manifest declaring that exact queried target;
  any differing target invalidates coverage with
  `automation_target_query_inconsistent`. The selected automation remains a
  separate named repair input because target mismatch is itself repairable; it
  is no longer falsely added to the provider fixture when its current target is
  known to differ. A valid returned wrong-target heartbeat now fails repair
  unavailable, while the selected manifest and exact returned candidates remain
  the complete read set. The one affected adversarial case passed 1/1 with
  `ResourceWarning` fatal, Ruff and `git diff --check` pass, and the prior exact
  49/49 unaffected provider/owner proof is preserved rather than replayed.
- Independent acceptance: a fresh isolated exact-revision review ACCEPTED
  evidence commit `bfdcb84a9f734c37dd32e596d44bee594d20683a`, tree
  `d8d1f56c2b784919425e55b6774aabaf10646ccc`, and product
  `f875faadce057e6c0c9be0504ab1d54e302b5ee8` with no material findings. The
  reviewer independently reproduced selected wrong-target/provider-empty as a
  selected-only repairable read and a provider-returned wrong-target manifest
  as `automation_target_query_inconsistent` with repair unavailable. Focused
  regression passed 1/1 with `ResourceWarning` fatal, Ruff passed, the full
  verifier returned Blocks 0-29 with 0 errors/warnings, verifier tests passed
  30/30, frame hash and remote identity were exact, and the checkout, diff,
  fsck, resource, and Stop gates were clean. Block 20 is accepted at that exact
  revision; no live owner mutation established acceptance.

### Stop

Stop before operation semantic diffs, pause/resume, same-target mission
succession, successor-task continuity, reporting, evolution, or terminal
lifecycle operations.

---

## Block 21 — Owner-backed operation semantic diffs

Status: `accepted`

### Objective

Show exact semantic before/after changes for policy, binding, and automation
previews without creating another editor, confirmation, or mutation path.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator understand precisely what an
  owner-backed consequential request would add, remove, change, and preserve
  before using its existing typed confirmation.
- Potential capability loss or regression: deriving a diff in the browser,
  omitting unchanged protected fields, or treating preview as applied could
  hide owner scope, stale currentness, or partial postconditions.
- Protected-capability effect: preserves maintained operation owners, preview
  tokens/expiry, route gates, typed confirmation, exact postconditions,
  currentness fingerprints, source drill-down, and direct-write prohibitions.
- Architecture and operating-model effect: adds a typed read-only semantic
  change projection to the existing operation preview envelope and adapts the
  Block 19 diff component; it adds no operation or writer.
- Tradeoff and source evidence: semantic rows are clearer than prose-only risk
  summaries, but the server owner must supply them and unsupported/unavailable
  comparisons remain explicit rather than guessed.

### Inputs and dependencies

- Accepted Block 10 operation framework; accepted Blocks 14–16 policy and
  binding operations; accepted Block 20 automation binding repair.
- Accepted Block 19 adapted semantic-diff component and supplied Beautiful UI
  `components/DiffTable.tsx` source at SHA-256
  `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2`.

### Required work

- Extend the typed preview envelope with a bounded owner-supplied semantic
  change list for the supported policy adjustment, mission-binding repair,
  role-task repair, and automation-binding repair operations. Each row records
  exact field/subject, `added`/`removed`/`changed`/`preserved` posture,
  before/after value or explicit unavailable/redacted posture, canonical owner,
  source identity/revision, currentness fingerprint, and safe drill-down.
- Adapt the supplied `DiffTable.tsx` structure and its compact removed/added/
  unchanged visual grammar to these rows. Remove timed demo stages, fictitious
  menu data, and animation-driven state; add visible text/icons so color and
  strike-through are never the sole change cue.
- Render preview changes from the server envelope only. The browser may format
  but must not infer a change from prose, compare stale snapshots, expose
  automation prompts/private fields, or manufacture a preserved-field claim.
- Keep risk, expected postcondition, failure posture, route gate, source roots,
  preview expiry, and stale-refresh behavior adjacent. The existing exact typed
  confirmation remains the only request path and is neither weakened nor
  replaced by row clicks, approval-card choices, or inline editing.
- Preserve partial owner transitions as separate expected postconditions; an
  automation/policy dual-owner preview must not collapse into one successful
  row.

### Scope and non-goals

- In scope: read-only semantic diffs for the four already owner-backed preview
  families named above and their focused UI/API contracts.
- Not in scope: a generic object diff engine, tracker source diffs, pause/resume
  or later operation families, edit-in-place, bulk operations, Approval Card
  adoption, new confirmation types, or direct writes.
- Do not copy demo data or treat a preview token/green row as an applied or
  verified outcome.

### Deliverables and recorded state

- Closed preview-diff schema, server owner projections, adapted semantic-diff
  UI, exact provenance note, and focused backend/Zod/component/browser tests.

### Resource and economy contract

Build rows from the same already-read operation preview snapshot and cap them
to the operation's supported fields. Do not perform a second broad source scan
or read unrelated policy/automation state. After a finding, rerun only the
affected operation family plus shared schema/component proof.

### QA and independent review

- Test added/removed/changed/preserved, unavailable/redacted values, policy and
  automation dual postconditions, stale/expired preview, owner mismatch,
  partial route/source state, long identifiers, safe rendering, and absence of
  prompt/private content.
- Browser-test pointer/keyboard reading order, non-color cues, source links,
  typed-confirmation isolation, desktop/tablet/mobile, dark mode, reduced
  motion, and no overflow.
- Independent authority/UI review traces each sampled row to the exact preview
  owner and confirms row interaction cannot request or accept an operation.

### Acceptance

- Every supported policy/binding/automation preview states exactly what is
  added, removed, changed, and materially preserved with owner/source/currentness
  evidence or explicit unavailable posture.
- Typed confirmation, expiry, route gate, postcondition, and recovery contracts
  remain unchanged and are visually/semantically distinct from the diff.
- No browser-derived change, private owner field, second editor, row action, or
  alternate acceptance/mutation path exists.

### Negative tests

- Reject a semantic row without exact owner/currentness evidence, a diff built
  from free-form prose, a one-owner success claim for dual-owner repair, or an
  expired preview rendered as current.
- Reject clickable added/removed rows that mutate state, a confirmation bypass,
  or automation prompt/private-field disclosure.

### Completion evidence

- Activation and authority: started automatically after independently accepted
  Block 20 evidence `bfdcb84a9f734c37dd32e596d44bee594d20683a`; all direct
  dependencies Blocks 10, 14, 15, 16, 19, and 20 are accepted. Governing
  implementation authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Work-start boundary: re-read Block 21 and inspected the existing
  `PreviewEffect`/operation coordinator envelope, the Admin preview panel and
  typed client contract, and accepted Block 19's provenance-noted
  `TrackerSemanticDiffTable`. First work is limited to owner-supplied bounded
  semantic preview rows for the four named existing operation families and a
  read-only adaptation of that component. Blocks 22-29 remain unopened; no
  pause/resume, continuity, reporting, evolution, lifecycle, new operation,
  owner dispatch, or mutation is started.
- Product-capability decision: the selected bounded-general path extends the
  existing operation preview snapshot with at most 32 owner-produced semantic
  rows and reuses the accepted local Diff Table grammar. A smaller browser-side
  comparison was rejected because it would infer changes from prose or stale
  snapshots; a larger generic diff service was rejected because no supported
  owner or additional operation needs it. The existing preview token, expiry,
  route gate, typed confirmation, canonical postcondition, operation owner,
  and direct-write prohibitions remain protected and unchanged. The exact
  target-product capability frame remains 3,511 bytes at SHA-256
  `736124301d439cf6f143bb8013d53f085e9f3f4748df35451ef1bce5df0d8857`.
- Candidate product: commit
  `dc83a8b31f4e5f3ec2ebdb629f8dbdb26b503822`, tree
  `2feaf1fb030c19245e36ede4e23f78767f66ffc2`, parent activation evidence
  `29a1093d5c3ae8eda0789333e66558fdf01b93a8`, pushed with local/upstream
  divergence `0 0`. The existing coordinator now validates and publishes a
  closed exact/unavailable/redacted/not-applicable semantic-row contract. The
  four supported maintained owners populate added/changed/preserved scope from
  their already-read preview snapshot, including separate automation and
  policy owner rows. Unsupported operations publish explicit unavailable
  comparison coverage; the browser only formats the typed envelope.
- Supplied-source provenance: the compact table starts from Beautiful UI's
  supplied `components/DiffTable.tsx` baseline at
  `https://beautiful-ui-five.vercel.app/`, frozen SHA-256
  `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2`.
  The adaptation retains its fixed-column table, semantic row tinting, status
  dots, and explicit change cues while removing demo data, timers, staged
  actions, and menu semantics; it adds typed value postures, exact owner/source
  revisions/currentness, safe internal links, keyboard-scroll containment,
  and no row action or editor. It adds no explanatory page heading.
- Candidate validation: Ruff and `git diff --check` passed. The affected
  backend modules passed 28/28 serially with `ResourceWarning` fatal; one
  earlier contended HTTP invocation timed out and its exact test passed 1/1 in
  isolation before the clean full rerun. The full frontend passed 99/99 with
  invocation-scoped `--maxWorkers=1`; its default parallel invocation had only
  unrelated five-second test timeouts, and no harness change was made.
  TypeScript and production build passed. Focused Playwright produced eight
  valid passes across desktop/tablet/mobile; one tablet enablement wait raced
  the live App Server, and the invocation-order-only retry passed 1/1. The
  exact browser proof covers all three viewports, dark mode, reduced motion,
  keyboard-scroll semantics, Axe in the dual-owner preview, source links,
  non-color labels, no component buttons, and no document overflow. The
  full-profile verifier reports 30 Blocks with 0 errors/warnings and its tests
  pass 30/30. The exact product server restarted on loopback port 8787; live
  health is `ok` and its closed registry exposes 19 operation definitions with
  no persisted activity or inferred result.
- First exact-revision review: rejected evidence commit
  `f10ff208c7b83cd4d4136cfc6e953e76c59ce360` because an expired semantic
  preview remained visually current and actionable. The server rejected the
  eventual request, but the browser neither derived expiry while the dialog
  remained open nor mapped `preview_expired` into the existing stale/re-preview
  recovery posture. All other owner, schema, provenance, responsive,
  accessibility, security, resource, and Stop findings were clear; that exact
  evidence and its valid proof remain immutable diagnostic history.
- Expiry correction product: commit
  `c2b6aac6cd3d4ef9d470fd07b91fd6d283bc93da`, tree
  `a162373a0117a59817cffccaca99deda8ff88078`, parent rejected evidence
  `f10ff208c7b83cd4d4136cfc6e953e76c59ce360`, pushed with local/upstream
  divergence `0 0`. The bounded eight-file frontend/test delta derives the
  exact preview expiry, schedules the transition while the dialog remains
  open, resets typed confirmation per preview token, disables dispatch after
  expiry including a click-time recheck, marks the comparison expired, exposes
  the existing Preview again recovery, and maps the canonical
  `preview_expired` error to the same posture. It does not change any operation
  owner, backend schema, route gate, confirmation value, or mutation path.
- Correction proof: the two affected component/runner files passed 20/20;
  TypeScript and the production build passed. The exact mission-binding browser
  fixture now proves already-expired, refreshed-current, source-linked,
  nonmutating semantic previews on desktop, tablet, and mobile, 3/3 serially;
  its run/project claim is fixed to the same exact project used by the preview
  instead of borrowing mutable live task state. The full-profile verifier
  reports 30 Blocks with 0 errors/warnings, all 30 verifier tests pass,
  `git diff --check` passes, and the pushed loopback server on port 8787 reports
  complete health with every integration available. The backend and remaining
  28/28 plus 99/99 proof are unaffected and were not replayed broadly.
- Independent exact-revision review: accepted evidence
  `504b139e78b2db0250271e54bf2eb2eb5f00e3e4`, tree
  `fc42a3f68a02a5aab2d71810cd94d389058fff33`, over product
  `c2b6aac6cd3d4ef9d470fd07b91fd6d283bc93da` with no material findings. The
  reviewer independently reproduced 20/20 affected Vitest tests, the
  production build, and Playwright 3/3 across desktop/tablet/mobile; verified
  both already-expired and expires-while-open postures plus refresh and
  click-time currentness; confirmed no backend, schema, owner, confirmation,
  route-gate, or mutation scope changed; and passed tracker, diff, fsck,
  ancestry, remote-identity, and Stop gates. Block 21 is accepted at that exact
  revision.

### Stop

Stop before pause/resume, mission/task continuity, reporting, evolution,
request-stop, or terminal lifecycle operations.

---

## Block 22 — Supervision pause

Status: `accepted`

### Objective

Pause one supervision group through its existing automation and lifecycle
owners while preserving exact target state and keeping turn interruption and
the currently unsupported semantic-resume path separate.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: let the operator semantically pause one selected
  supervision group without leaving automation and lifecycle state inconsistent.
- Potential capability loss or regression: confusing turn interrupt with pause,
  changing only automation, broad pausing, or implying that automation re-enable
  is already semantic resume could silently remove monitoring or misstate
  lifecycle.
- Protected-capability effect: preserves automation single writers, lifecycle
  gates, target/group scope, resume/recovery state, role bindings, and distinct
  App Server turn semantics.
- Architecture and operating-model effect: adds one specific pause operation
  with dual automation/lifecycle postconditions; it adds no generic kill switch
  and does not invent the missing resume owner.
- Tradeoff and source evidence: the dual-owner pause is more deliberate than
  toggling a schedule, but it is the only supported semantic transition in the
  accepted Block 0 contract; resume remains unavailable until Blocks 23–24.

### Inputs and dependencies

- Accepted Block 7 run/automation/lifecycle workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Current lifecycle and automation contracts from Block 0.

### Required work

- Register `Pause supervision` through the exact automation/supervision owners
  and lifecycle gate. Keep `Resume supervision` disabled with the exact missing-
  owner prerequisite until Blocks 23–24 are accepted.
- Preview target/group, current lifecycle, affected automations, pending owner
  work, preserved target/task state, expected postconditions, and recovery.
- Verify both actual paused automation state and the matching canonical paused
  lifecycle record; expose partial transition and safe recovery without auto-
  retry.
- Keep task/turn `interrupt` and `continue` visibly separate in labels,
  confirmation, history, and postconditions.
- Scope pause to the selected group; preserve Gmail/report ownership and target
  implementation state unless the maintained owner explicitly changes them.

### Scope and non-goals

- In scope: semantic pause for one supervision group and truthful unavailable
  posture for resume.
- Not in scope: interrupting/continuing a turn, request-stop, terminal shutdown,
  semantic-resume owner creation or dashboard execution, policy tuning, report
  generation, or mission/successor transition.
- Do not expose a generic red Stop control or multi-group bulk toggle.

### Deliverables and recorded state

- Pause operation contract, lifecycle/automation preview and postcondition
  verifier, run control, partial/recovery states, explicit disabled-resume
  prerequisite, and tests.

### Resource and economy contract

Touch one group and only its bound automations. Request once, poll the two named
owners to bounded timeout, and preserve partial state for operator recovery;
never repeat or widen automatically.

### QA and independent review

- Test turn-interrupt confusion, stale lifecycle, gate denial, missing/partial
  automation bindings, already paused, one owner changed only, wrong group,
  restart, recovery, and attempted automation-only resume.
- Exercise full pause only on the disposable group unless exact current
  authority names a real target.
- Independent authority review verifies dual postconditions and preserved
  target/group state.

### Acceptance

- The selected group reaches matching paused automation and lifecycle state,
  with exact current records visible in the run/floor history.
- Partial, denied, stale, already-satisfied, and failed transitions remain
  truthful and recoverable.
- A turn interruption can never render or verify semantic supervision pause,
  and automation re-enable can never render or verify semantic resume.

### Negative tests

- Reject `paused` when only a turn or only one canonical owner changed.
- Reject bulk, wrong-group, stale-preview, or gate-bypassing pause, and reject
  any enabled resume path before Blocks 23–24 establish its owner/postcondition.

### Completion evidence

- Activation and authority: Block 22 started automatically after independently
  accepted Block 21 evidence
  `504b139e78b2db0250271e54bf2eb2eb5f00e3e4`; direct dependencies Blocks 7,
  10, and 11 are accepted. Governing implementation authority remains
  direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Work-start boundary: re-read the complete Block 22 contract and began the
  capability review by inspecting the maintained supervision pause/resume,
  lifecycle-gate, automation-owner, and existing operation/task boundaries.
  Work remains limited to one selected supervision group and its exact bound
  automations; Blocks 23-31 remain unopened and no live pause/resume or other
  consequential operation has been requested.
- Capability-review correction: the accepted Block 0 contract and exact helper
  surface confirm semantic pause has lifecycle plus automation postconditions,
  while resume has no canonical resumed lifecycle state, gate, or postcondition.
  The authored successor preserves full scope by narrowing this active Block to
  pause and adding separate owner and dashboard-resume Blocks 23 and 24. No
  implementation or live owner action occurred before this plan correction.
- Product candidate and correction: commit
  `4a41973796d7f7100603de2833d907dfe0155a8a` added the typed, route-gated
  pause operation, exact lifecycle/automation postcondition verifier, semantic
  preview, sparse run controls, disabled resume posture, and focused tests.
  Independent review rejected that immutable revision because it excluded the
  canonical projectless fix-executor shape, could render `Paused` while a
  configured auxiliary automation was unavailable, and did not prove that
  automation pause followed the exact lifecycle notification. Successor
  `c8b3100950f27ea9df481105028695bd907b3af4`, tree
  `c0cb8a238c0cc149de6c49ace574efcb18120bc4`, closed only those three rows:
  exact configured task/cwd identity now permits the projectless fix executor;
  every configured automation remains represented in pause truth; and one
  hash-chained post-lifecycle notification plus strictly later owner timestamps
  gates each `ACTIVE` to `PAUSED` transition while prior `PAUSED` owners remain
  byte/time unchanged.
- Validation and independent acceptance: affected backend suites passed 52/52
  with `ResourceWarning` fatal, focused frontend passed 21/21, production build
  passed, and the semantic-pause browser proof passed 3/3 across desktop,
  tablet, and mobile with Axe serious/critical and overflow assertions. Ruff,
  the 32-Block full-profile verifier, all 30 verifier tests, diff check, fsck,
  exact remote identity, clean checkout, and Stop checks passed. Fresh
  independent exact-revision review accepted `c8b3100` with no material
  findings. No live pause, notification, automation, policy, task, or ledger
  mutation was executed during implementation or review.

### Stop

Stop before implementing the resume lifecycle owner, enabling semantic resume,
same-target mission succession, successor-task continuity, reporting,
evolution, request-stop, or terminal shutdown.

---

## Block 23 — Canonical supervision-resume lifecycle owner

Status: `accepted`

### Objective

Establish one maintained, evidence-tight semantic-resume lifecycle owner so a
paused supervision group can later return to active monitoring without treating
automation or task state as the canonical lifecycle record.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: close the exact Block 0 owner gap with one canonical
  resumed lifecycle record and gate bound to the paused group, current policy,
  and exact automation-owner state.
- Potential capability loss or regression: a permissive recorder, task-resume
  alias, or automation-only inference could erase pause history, accept partial
  monitoring, or authorize the wrong group.
- Protected-capability effect: preserves the hash-chained supervision ledger,
  exact mission/policy/group identity, automation single writers, explicit
  pause intervals, turn-state separation, replay/currentness, and fail-closed
  partial recovery.
- Architecture and operating-model effect: extends the existing maintained
  supervision helper and policy contract with one narrow resume lifecycle owner;
  it adds no dashboard endpoint, scheduler, second ledger, or generic state
  transition engine.
- Tradeoff and source evidence: adding a maintained owner costs a separate
  implementation/review slice, but the accepted Block 0 capability matrix
  explicitly requires it before resume can become supported and the weekly
  report owner already distinguishes canonical `supervision-resume` records.

### Inputs and dependencies

- Accepted Block 22 semantic-pause operation and its exact lifecycle/automation
  contract.
- Accepted Block 0 capability matrix, current `supervision_log.py` lifecycle
  and status owners, supervision policy, and explicit pause-interval report
  contract.

### Required work

- Add one dedicated maintained resume eligibility/currentness gate and one
  append-only resume finalizer/record path. Bind them to the exact target,
  active mission, policy version/hash, current paused lifecycle record, source
  record/fingerprint, and exact bound automation IDs.
- Require every exact bound supervision automation to be current, enabled, and
  configured for its owner-derived schedule before appending the resumed
  lifecycle record. Missing, extra, stale, unreadable, mismatched, or partially
  active automation state remains unavailable or pending.
- Emit a stable hash-chain-valid `supervision-resume` lifecycle record with its
  pause predecessor, group/mission/policy identity, automation-owner evidence,
  currentness root, and preserved target/task state. Make replay/idempotency
  explicit and keep prior pause history intact.
- Update the maintained status projection and weekly availability owner so the
  exact record ends the corresponding explicit pause interval without treating
  a task turn, task resume, automation update, or caller assertion as semantic
  resume.
- Update the maintained skill/policy guidance, helper CLI contract, tests, and
  dashboard capability contract. Change the contract posture to `supported`
  only after the exact owner implementation is independently accepted.

### Scope and non-goals

- In scope: the canonical resume eligibility, record, validation, projection,
  and report-interval owner inside `supervise-tracker-runs`.
- Not in scope: dashboard operation/UI, direct automation mutation, task/turn
  resume, policy tuning, mission succession, request-stop, terminal shutdown,
  or a generalized lifecycle workflow.
- Do not synthesize resume from manifest state, mutate automation files, or
  rewrite/remove the paused lifecycle record.

### Deliverables and recorded state

- Maintained helper command/schema, policy/skill contract, hash-chain record and
  status projection, weekly-report compatibility, exact fixtures/tests, and the
  narrowly refreshed dashboard capability matrix.

### Resource and economy contract

Read one target's validated policy/history and only its exact bound supervision
automation owners. Reuse the pause/currentness roots, perform one append at most,
and re-read only the new lifecycle head and named automations. Never scan or
reconcile unrelated groups and never retry an append automatically.

### QA and independent review

- Test missing or noncurrent pause, already resumed, wrong target/mission/policy,
  stale source, no bound automations, one-owner-only activation, extra/missing
  automation, unreadable/malformed owner, schedule mismatch, replay, restart,
  hash-chain integrity, and explicit pause-interval closure.
- Test that task `thread/resume`, turn start/continue/interrupt, caller-supplied
  `resumed`, and automation enablement alone cannot create or satisfy the
  canonical lifecycle postcondition.
- Independent supervision-owner review verifies the exact state machine,
  currentness, append-only history, owner read set, and absence of dashboard or
  automation writes.

### Acceptance

- The maintained owner can determine one exact paused group's resume eligibility
  and append one canonical current `supervision-resume` lifecycle record only
  after every exact bound automation is active at its maintained configuration.
- Status/history and weekly availability close the exact pause interval from
  that record, while partial, stale, replayed, and already-satisfied attempts
  retain exact truth and recovery.
- No task/turn state, raw manifest edit, dashboard assertion, or automation-only
  state can establish semantic resume.

### Negative tests

- Reject a resumed lifecycle record without its exact pause predecessor,
  current mission/policy/source identity, and complete current automation-owner
  evidence.
- Reject direct ledger/TOML mutation, unrelated automation enumeration, task-
  resume equivalence, duplicate append, or an owner/gate that accepts only one
  side of the postcondition.

### Completion evidence

- Activation and authority: Block 23 started automatically after independent
  acceptance of Block 22 successor
  `c8b3100950f27ea9df481105028695bd907b3af4`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Work-start boundary: re-read this complete Block 23 contract and began with
  the maintained `supervision_log.py` lifecycle/status owner, supervision skill
  and policy contract, weekly pause-interval projection, and exact automation
  read boundary. Work is limited to the canonical resume lifecycle owner;
  dashboard execution in Block 24 and Blocks 25-31 remain unopened.
- Capability review and product candidate: commit
  `9c9fd88573c42eeb6564ba2e6f930c4e07e182de`, tree
  `938848c1153816490005508cc813ddf118b103b7`, extends only the maintained
  supervision helper, its skill/policy contract, weekly-report projection, and
  the dashboard capability matrix. The read-only `resume-gate` binds one exact
  current pause, distinct eligible post-pause semantic check, active mission,
  current policy/history/event heads, source fingerprint, and only the exact
  policy-bound automation owners. `resume-finalize` rechecks that unchanged
  basis under the append owner, requires every named automation `ACTIVE` at its
  owner-derived target and schedule, and appends at most one independently
  verifiable `supervision-resume` lifecycle record. Status and weekly metrics
  consume only helper-verified canonical records; legacy report pairs remain
  readable history but cannot create a new canonical resume.
- Focused and regression proof: the resume-owner plus explicit-pause reporting
  tests passed 10/10; all maintained supervision helper, weekly report,
  terminal report, and Factory-evolution tests passed 205/205 with
  `ResourceWarning` fatal. Ruff, Python bytecode compilation, and
  `git diff --check` passed; the full-profile tracker verifier reports all 32
  Blocks with zero errors/warnings and all 30 verifier tests pass. The tests
  cover partial activation, source/policy/mission currentness, missing/
  duplicate/malformed/schedule-mismatched owners, named-owner-only reads,
  direct generic/task resume rejection, stale active state, hash-chain
  corruption, append-once replay, status projection, and exact canonical
  pause-interval closure.
- Independent rejection and narrow successor: fresh exact-revision review
  rejected immutable evidence `bf45e2cf78741cb8bf283eb0b485cac4b7e78b84`
  because the standalone canonical-record verifier did not reapply the same
  exact resume-source eligibility predicate as the write gate. A fully rehashed
  task/turn-shaped source could therefore reach status and weekly consumers as
  canonical. Successor `896628cdd97e07b677d3635c2d48181cf6bce973`,
  tree `8a7ab193d70457ddd9a9f2262746fcb508c20df7`, changes only that verifier
  boundary and its adversarial regression. The test reconstructs every
  dependent source-currentness, eligibility, resume, predecessor, and record
  hash around an ineligible `thread-resume` source, then proves canonical
  verification rejects it, status retains the current pause, and weekly
  availability leaves the exact interval open. The affected resume-owner suite
  passes 8/8; Ruff and diff checks pass, while the prior 205/205 and mechanical
  proof remain applicable.
- Fresh independent acceptance: exact evidence
  `27091628203d77caf7e95c7e16d3d8fef5aa39df`, tree
  `127039d268c77251126bced281b33e971efee1fe`, and product successor
  `896628cdd97e07b677d3635c2d48181cf6bce973` were accepted with no material
  findings. Independent fully rehashed App Server task/turn and excluded Sol
  Max sources both remained ineligible and noncanonical; status retained the
  pause and weekly reporting left its interval open. Focused 8/8, Ruff,
  compilation, full-profile 32-Block verification, verifier 30/30, diff, fsck,
  exact remote identity, clean checkout, and Stop checks passed. The capability
  contract now marks the maintained lifecycle owner `supported`, but no
  dashboard API/UI/control, automation mutation, direct TOML write, live
  resume, task/turn resume, policy change, or canonical ledger mutation was
  executed in Block 23.

### Stop

Stop before registering or executing dashboard resume, mission/task continuity,
report generation, Factory evolution, request-stop, or terminal shutdown.

---

## Block 24 — Supervision resume

Status: `accepted`

### Objective

Resume one paused supervision group through its exact automation owners and the
accepted canonical resume lifecycle owner while preserving target/task state and
keeping task/turn continuation semantically separate.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: provide reversible operator control that returns
  one paused group to current scheduled supervision with both canonical owner
  postconditions proven.
- Potential capability loss or regression: broad enabling, task-resume
  confusion, stale pause state, or accepting only automation/lifecycle success
  could misstate monitoring and recovery.
- Protected-capability effect: preserves exact group/mission/policy identity,
  named automation single writers, resumed lifecycle evidence, partial-state
  recovery, role bindings, and distinct App Server turn semantics.
- Architecture and operating-model effect: registers one resume operation in
  the existing dashboard coordinator over the accepted automation and Block 23
  lifecycle owners; it adds no generic toggle, scheduler, or direct writer.
- Tradeoff and source evidence: the two-owner sequence is slower than enabling
  schedules alone but is the smallest end-to-end path that satisfies the Block
  0 revisit trigger and prevents false semantic resume.

### Inputs and dependencies

- Accepted Block 22 pause operation and accepted Block 23 canonical resume
  lifecycle owner.
- Accepted Block 7 run/automation/lifecycle workspace and Blocks 10 and 11
  operation/task owners.

### Required work

- Register `Resume supervision` only for one exact canonically paused group
  whose Block 23 gate, current policy, role/task bindings, and complete bound
  automation set are available.
- Preview target/group, pause predecessor, current lifecycle, each affected
  automation and owner-derived active schedule, pending owner work, preserved
  target/task/role/Gmail/report state, expected dual postconditions, and bounded
  recovery.
- Request each named automation owner action at most once, then invoke the
  canonical resume finalizer only when every exact bound automation is current
  and active. Recheck source/currentness and route gates at execution.
- Verify actual automation enabled/schedule state and the matching canonical
  `supervision-resume` lifecycle record separately; preserve automation-active/
  lifecycle-pending, lifecycle-missing, denied, stale, already-running, failed,
  and unverified states without automatic retry.
- Add the compact run control/history/currentness UI while keeping `Continue
  task` and task `thread/resume` labels, confirmations, history, and
  postconditions visibly separate.

### Scope and non-goals

- In scope: semantic resume for one exact paused supervision group.
- Not in scope: semantic pause implementation, turn/task continue or interrupt,
  policy tuning, mission/successor transition, request-stop, terminal shutdown,
  report generation, or bulk/multi-group activation.
- Do not expose a generic toggle or write lifecycle/automation files directly.

### Deliverables and recorded state

- Resume operation contract, automation/lifecycle preview and dual
  postcondition verifier, run control/history state, partial recovery, and
  focused API/component/browser tests.

### Resource and economy contract

Touch one group and only its exact bound automations. Request each owner once,
poll the two named postconditions to bounded timeout, preserve partial state,
and stop without retrying or widening.

### QA and independent review

- Test turn/task-resume confusion, stale or absent pause, gate denial, missing/
  partial/extra automation bindings, already running, one owner changed only,
  wrong group, replay, restart, and recovery.
- Exercise full resume only on the disposable group unless exact current
  authority names a real target.
- Independent authority review verifies both postconditions, the pause-to-
  resume lineage, preserved target/group state, and no direct writes.

### Acceptance

- The selected group reaches matching active automation and canonical resumed
  lifecycle state, with exact current records visible in run/floor history.
- Partial, denied, stale, already-satisfied, and failed transitions remain
  truthful and recoverable without affecting another group or target work.
- Task/turn continue, resume, or interrupt can never render or verify semantic
  supervision resume.

### Negative tests

- Reject `resumed` when only a task/turn, only automations, or only a lifecycle
  record changed.
- Reject bulk, wrong-group, stale-preview, replayed, gate-bypassing, or direct-
  write resume.

### Completion evidence

- Activation and authority: Block 24 started automatically after independent
  acceptance of Block 23 evidence
  `27091628203d77caf7e95c7e16d3d8fef5aa39df` and product
  `896628cdd97e07b677d3635c2d48181cf6bce973`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
- Work-start boundary: re-read the complete Block 24 contract and began with
  the accepted dashboard operation coordinator, semantic pause operation,
  automation owner, and canonical `resume-gate`/`resume-finalize` lifecycle
  owner. Work is limited to one exact paused supervision group; Blocks 25-31
  remain unopened and no live resume or other consequential action has been
  requested.
- Frozen implementation candidate: commit
  `c6d5a25cb1c022ff5fc3bd0f1e2a287dfd9e94bf`, tree
  `ba4af619d5921369cdf6dd9b4697237d52d96d64`, parent
  `935ceab2ed3fce65d732dfc35593dfa7ec8ca0a7`. The eight-file slice registers
  `factory.supervision-resume` over the accepted read-only `resume-gate`, one
  bounded fix-executor request, the exact Codex automation owners, and the
  canonical `resume-finalize` postcondition; it adds no dashboard ledger,
  scheduler, generic toggle, direct owner-file writer, or Block 25 operation.
- Truth and recovery proof: the source contract binds one canonically paused
  group, its pause and post-pause semantic source, current mission/policy/
  project, exact target-task turn state, one distinct configured fix executor,
  and every owner-derived automation/configuration root. Dispatch re-resolves
  that fingerprint and the maintained route gate. Verification accepts only
  the matching canonical resume lineage plus every exact automation ACTIVE at
  its recorded owner schedule, preserves already-ACTIVE owners byte/time
  exactly, requires each prior-PAUSED owner to change after the preview, and
  leaves lifecycle-only, automation-only, denied, changed-task, unavailable,
  and partial transitions pending without retry or rollback. The UI exposes
  separate `Pause`, `Finish pause`, `Resume`, `Finish resume`, and unavailable
  postures and never labels task/turn continuation as supervision resume.
- Validation: full dashboard-server discovery passed 130/130 with
  `ResourceWarning` fatal; the final route-denial and owner-envelope pair passed
  2/2; Ruff and Python compilation passed. The full frontend passed 18 files
  and 102 tests, the production build passed, and focused semantic pause/resume
  Playwright passed 6/6 across desktop, tablet, and mobile with serious/
  critical Axe and horizontal-overflow assertions. The full-profile verifier
  reports 32 Blocks with zero errors/warnings and all 30 verifier tests pass;
  diff and relative-link checks pass. The exact candidate is pushed with local/
  upstream divergence `0 0`.
- Live nonmutating proof: the product server was restarted on loopback port
  8787 from the candidate assets. `/api/v1/health`, `/api/v1/operations`, and
  `/admin` returned HTTP 200; the operation projection reports
  `factory.supervision-resume` `supported`, its typed confirmation class, exact
  dual owner, bounded consequences, and dual postcondition. No live operation
  preview, fix-executor request, automation activation, lifecycle finalization,
  task/turn action, or supervision record mutation was attempted. At that
  candidate freeze, exact-revision review was pending and Blocks 25-31 remained
  unopened.
- Independent rejection and narrow successor: exact review rejected immutable
  evidence `a4d754707203e47ef011a1b8d530d0f80b8e99e8` and product
  `c6d5a25cb1c022ff5fc3bd0f1e2a287dfd9e94bf` for one UI truth defect only:
  a canonical resumed lifecycle plus named ACTIVE rows could render `Running`
  even when one row's owner coverage remained `unavailable`. All backend owner,
  currentness, replay, route, descriptor, mechanical, and Stop proof remained
  valid. Product successor `3d7e28ddc530dcf352032458ad7ccb2aa66b15c9`,
  tree `11913a5f9e00dd0ba515e9e81b85bd9c4fb24b0d`, changes only the completion
  predicate and focused component/browser proof. `Running` now requires every
  represented owner ACTIVE, `reconciled`, and duplicate coverage `exact`; a
  canonical resume with unavailable or partial owner coverage renders disabled
  `Resume incomplete` with the limitation stated explicitly. The affected
  component suite passes 15/15, the production build passes, and the semantic-
  resume Playwright case passes 3/3 across desktop/tablet/mobile. The successor
  was pushed with divergence `0 0`; fresh delta-only review was then requested
  while Block 25 remained closed.
- Fresh independent acceptance: exact evidence
  `6bc47de5cf7da05405e9c1a8f00f39447e40e298`, tree
  `7414865edcf8512a5c86cbaffd4d1a4ed17604a2`, and product successor
  `3d7e28ddc530dcf352032458ad7ccb2aa66b15c9` were accepted with no material
  findings. The reviewer reproduced the exact-coverage completion predicate,
  truthful `Resume incomplete` posture, component 15/15, production build,
  Playwright 3/3 across desktop/tablet/mobile, full-profile 32-Block verifier,
  verifier 30/30, diff/fsck/clean/remote identity, and Block 25 Stop. All
  unaffected backend owner, replay, route, and live-descriptor proof remains
  accepted. No live operation preview, execution, automation activation,
  lifecycle finalization, task/turn action, or canonical supervision mutation
  occurred in Block 24.

### Stop

Stop before same-target mission succession, successor-task continuity,
reporting, evolution, request-stop, or terminal shutdown.

---

## Block 25 — Same-target mission succession

Status: `accepted`

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

- Activation and authority: Block 25 started automatically after independent
  acceptance of Block 24 evidence
  `6bc47de5cf7da05405e9c1a8f00f39447e40e298` and product
  `3d7e28ddc530dcf352032458ad7ccb2aa66b15c9`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Block 25 is limited to one same-target mission succession through the
  maintained owner; Block 26 and later operations remain unopened, and no live
  mission succession has been previewed or requested.
- Capability review and owner boundary: the implementation reuses the exact
  maintained `mission-successor`, policy-history, mission-activation, mission-
  scoped event, Codex task, and route-gate owners. One complete ordinary user
  item is content/envelope/client bound but remains authority-unverified until
  the independent reviewer verifies the direct bytes, material difference, and
  predecessor disposition. The dashboard neither adds a mission registry nor
  calls `bind`, creates a task/group, or writes policy, history, events, or
  automations directly. The applied boundary is one new active policy binding
  plus one pending first-work activation; it does not claim work-start or
  implementation completion.
- Product candidate: commit
  `c853b17b976947d7e7eeb7889c0a419c298023fe`, tree
  `eaf6121875c38f90d4d70b2affa7b30b914cee70`, parent Block 25 activation
  `8ae7abc2c2de53eb826d0a16b4440f182e78a8e6`, pushed with local/upstream
  divergence `0 0`. The nine-file bounded product/test delta adds the exact
  mission-history and successor-plan projections, one closed typed operation,
  complete policy-history-prefix and active-root postcondition checks, a compact
  current-run action/dialog and semantic before/after rows, predecessor-mode
  exclusion, and truth labels for independent review, pending activation, and
  no successor task/work-start claim. Older predecessor `superseded_by` links
  are preserved rather than rewritten to the newest mission.
- Candidate proof: the full backend suite passed 132/132 with
  `ResourceWarning` fatal; the affected workflow/projection suites passed 56/56;
  Ruff passed; the full frontend passed 103/103 serially; TypeScript and the
  production build passed. Focused Playwright passed 3/3 across desktop,
  tablet, and mobile with exact request/semantic-row assertions, predecessor
  exclusion, Axe serious/critical checks, one `h1`, and no horizontal overflow.
  The full-profile verifier reports all 32 Blocks with 0 errors/warnings and its
  tests pass 30/30; diff checks pass. The restarted loopback runtime on port
  8787 reports complete healthy coverage and exposes the supported successor
  descriptor among 22 closed registry entries. No live mission succession,
  owner dispatch, policy/history/event mutation, task creation, or target work
  start was attempted.
- First exact-revision review: rejected evidence
  `585fa6fe60af9055708653b03899e075e7796a8a`, tree
  `829e7fa85f487cbf90c7623a74c6d68d764573ce`, over product
  `c853b17b976947d7e7eeb7889c0a419c298023fe`. The single material finding was
  that successor source construction read every automation ID from runtime and
  therefore omitted a configured weekly-report owner whose canonical ID is
  `reports.weekly.automation_id`; mutating that omitted manifest after preview
  could still verify the successor. All other authority, history, isolation,
  task, UI, resource, and Stop boundaries passed and remain reusable.
- Weekly-owner correction: product successor
  `50fcc42a606ea439d27e0e9f7a6a713669dc342d`, tree
  `33357c00424cfc336ac46447df4dfa00af96f9d3`, parent rejected evidence
  `585fa6fe60af9055708653b03899e075e7796a8a`, changes only the successor
  source/preservation lookup and its focused test. The weekly-report ID now
  comes from the maintained reports-weekly policy source, is included with
  watcher/reviewer in exact source evidence, and a changed weekly manifest or
  timestamp makes verification `unverified`. Focused backend proof passed 2/2
  with `ResourceWarning` fatal; Ruff, full-profile 32-Block verification,
  verifier tests 30/30, and diff checks passed. Unaffected frontend, build,
  responsive/browser, and full backend evidence was reused; no live mutation
  occurred.
- Fresh exact-revision review: independently `ACCEPTED` evidence successor
  `ea004caf0b71e099fcda75663a72d78dc69df6e0`, tree
  `ad70858ce5df457c92208c28a9ff6f53bbfd6de3`, over product successor
  `50fcc42a606ea439d27e0e9f7a6a713669dc342d`. The reviewer reproduced the
  weekly-report policy-source lookup, exact protected-set inclusion, and
  manifest/currentness invalidation; focused backend 2/2, Ruff, the full
  32-Block verifier with 0 diagnostics, verifier tests 30/30, diff, object,
  clean-checkout, and remote `0 0` gates all passed. No live mission succession
  or canonical mutation occurred. Block 25 is accepted only at this exact
  revision.

### Stop

Stop before creating a successor task, generating reports, running Factory
evolution, or changing terminal lifecycle.

---

## Block 26 — Successor-task continuity

Status: `accepted`

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
- Label successor-task continuity separately from Block 25 same-target mission
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

- Activation: Block 26 started automatically after independent acceptance of
  Block 25 evidence `ea004caf0b71e099fcda75663a72d78dc69df6e0` and product
  `50fcc42a606ea439d27e0e9f7a6a713669dc342d`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Work is limited to the accepted successor-task continuity contract; Block 27
  and later operations remain closed, and no live successor transition or task
  creation has been attempted.
- Product candidate: commit
  `05ec47134453ef173735c6a34bff46d9c0f73061`, tree
  `e7085a92de93056c11a0ef7b082e1b5ec7353ff4`, parent Block 26 activation
  `7237897e532fe64c734ce428b7a614b38a06d036`, pushed with local/upstream
  divergence `0 0`. The ten-file product/test delta projects complete canonical
  transition identity and maintained-gate currentness, registers one typed
  `factory.successor-task-transition` operation, dispatches at most one exact
  fix-executor turn for the immediate next phase, independently verifies the
  phase-specific task/group/route evidence, and keeps effective source-stop
  permission false until the `work-started` head also has current first-Block
  task evidence. The current-run workspace shows the exact phase, range,
  successor, mission/group, handoff/acknowledgement, source-stop posture, and a
  single conflict-aware `Advance continuity` control; predecessor missions
  receive only their mission-scoped historical records and no current control.
  The dashboard writes no task, policy, event ledger, supervision group, or
  transition record directly.
- Candidate proof: affected backend owner/projection suites passed 58/58 with
  `ResourceWarning` fatal; focused adversarial coverage rejects malformed or
  discontinuous range claims, wrong-role handoff and acknowledgement markers,
  narrative-only first-work claims, stale phase/source identity, and a
  maintained gate stop claim without current concrete task evidence. Ruff,
  Python compilation, all 104 frontend tests, TypeScript, and the production
  build passed. Focused Playwright passed 3/3 across desktop, tablet, and mobile
  with exact preview/semantic-row assertions, predecessor exclusion, Axe
  serious/critical checks, and no horizontal overflow. The full-profile
  verifier reports all 32 Blocks with 0 errors/warnings, all 30 verifier tests
  pass, and `git diff --check` passes. The restarted loopback runtime on port
  8787 reports complete healthy coverage and exposes the supported continuity
  descriptor among 23 closed registry entries. No live owner dispatch,
  successor creation/binding, route, work-start, policy/history/event mutation,
  or source-stop action was attempted. Independent exact-revision review is
  pending.
- First exact-revision review: independently `REJECTED` evidence
  `1218642a9f9b4a9faba474e656f6c450bbeb6428`, tree
  `63560fa00730ab5a14b31c2d1b4a0e73d001f10e`, over product
  `05ec47134453ef173735c6a34bff46d9c0f73061`. The single material finding was
  that the operation unconditionally supplied `task_creation_authority` as
  available after checking only the canonical head's authority-class enum and
  nonempty source-record string. A fabricated safe record labeled
  `direct-user` could therefore enable the task-creation phase without an exact
  direct-source read. All ordered-phase, one-action, task/group/route/
  acknowledgement/work-start, effective source-stop, UI history-boundary,
  resource, and Stop checks passed and remain reusable. The reviewer also
  identified the arbitrary bootstrap `source_fingerprint` as an affected
  currentness question to close in the same correction.
- Authority/currentness correction: product successor
  `db9f1703634871c8462efb6ed066b979a5f9db05`, tree
  `93bccb8e6b2bfa8d0bc1e5259e0c35e53743a616`, parent rejected evidence
  `1218642a9f9b4a9faba474e656f6c450bbeb6428`, changes only four backend/test
  files. Before passing `available` to the maintained gate, the operation now
  resolves the canonical `codex:<task>:<turn>:<item>` governing record from the
  exact complete current source task; requires one ordinary text-only direct
  user item with matching full-content and envelope hashes, client identity,
  and no routed/generated/truncated posture; binds those identities into the
  preview fingerprint and semantic source revision; and rechecks the item after
  owner dispatch. Unsupported source classes or fabricated, absent, changed,
  partial, routed, or generated records disable the operation. The projection
  also retains the exact transition record sequence, and every successor
  bootstrap marker must match the canonical `successor-created` state
  fingerprint; first-work markers preserve the same governing source record.
  Focused fabricated-source and mismatched-bootstrap probes passed 2/2, the
  full affected backend suites passed 58/58 with `ResourceWarning` fatal, Ruff
  and compilation passed, and the full-profile 32-Block verifier plus all 30
  verifier tests and diff checks passed. Prior 104/104 frontend, production
  build, and responsive browser 3/3 evidence is unaffected and reused. No live
  transition, task creation, route, policy/event mutation, work start, or stop
  occurred. Fresh focused exact-revision review is pending.
- Fresh exact-revision review: independently `ACCEPTED` evidence successor
  `beeddf676b261145a3e70ecc222d9b159ec70e78`, tree
  `83ecf88ec3e6b4b87bdcd1d8969bd20105b161ac`, over corrected product
  `db9f1703634871c8462efb6ed066b979a5f9db05`. The reviewer reproduced complete
  direct-source resolution and post-dispatch currentness, fabricated/routed/
  generated/mixed/truncated/partial-source rejection, canonical
  `successor-created` fingerprint binding, first-work governing-source
  preservation, and concrete work evidence. Focused proof passed 3/3 with
  `ResourceWarning` fatal; Ruff, compilation, full-profile 32-Block
  verification with 0 diagnostics, diff/object/clean/remote `0 0`, and Stop
  checks passed. No live transition, task creation, route, canonical mutation,
  work-start, or source-stop action occurred. Block 26 is accepted only at this
  exact revision.

### Stop

Stop before weekly/terminal reporting, Factory evolution, source request-stop,
or terminal shutdown.

---

## Block 27 — Weekly supervision report workflow

Status: `accepted`

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

- Activation: Block 27 started automatically after independent acceptance of
  Block 26 evidence `beeddf676b261145a3e70ecc222d9b159ec70e78` and product
  `db9f1703634871c8462efb6ed066b979a5f9db05`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Work is limited to the accepted weekly-report workflow contract; Blocks
  28–31 remain closed, and no live report preparation, cognitive review,
  finalization, delivery, or Gmail action has been attempted.
- Product candidate: commit
  `becca0646d1b3d64c88ba2110e3bb3c4c9c1c28e`, tree
  `c920a3a38c7ad162001970ef9c114e813ff34960`, parent Block 27 activation
  `fd8f3e40108bedc0c46bf7e098b18e4c54088068`, pushed with local/upstream
  divergence `0 0`. The 17-file product/test delta registers typed
  `factory.weekly-supervision-report`, derives one current period and source
  root through the maintained metrics owner, projects seven distinct stages,
  and dispatches at most one configured Sol XHigh roundup-writer turn for the
  first incomplete stage. Prepare inputs are reproduced byte-for-byte;
  cognitive review and the manifest/Markdown/PDF/JSON bundle remain separately
  owned and verified; a configured Gmail delivery counts only after exact
  seed/sent raw-MIME and attachment-owner read-back proves the verified
  `report.pdf` in the bound reply thread and the maintained ledger owner appends
  the receipt. The dashboard never reads Gmail, sends mail, writes report
  artifacts or the ledger, schedules work, or treats reporting as
  implementation acceptance.
- Truth, recovery, and resource posture: current policy SHA is part of the
  report source root, changed policy replans to a new report without overwriting
  the prior verified bundle, and partial/corrupt or extra-member bundles fail
  closed. Report projection reads at most 16 members and 64 MiB total, while
  every member remains individually capped. Verification, display, and
  delivery failures retain exact earlier stages and expose only the next
  bounded recovery; exact replay returns the prior result rather than
  regenerating it. Missing Gmail leaves a locally verified report with
  delivery unavailable/retryable. Missing or non-distinct roundup-writer
  configuration leaves the current report plan and stage visible but disables
  the operation with `weekly_report_writer_unavailable`; the live current run
  on port 8787 proves that fail-closed posture.
- Product and UI proof: the maintained weekly-report suite passed 12/12 with
  `ResourceWarning` fatal, including prepare/finalize/verify replay, exact
  directory membership, missing delivery, Gmail raw-MIME/attachment/currentness
  rejection, and receipt replay. The exact backend operations, workflow,
  server, and operation-framework suites passed 89/89 with `ResourceWarning`
  fatal; focused adversarial cases cover changed policy, retained prior bundle,
  member bounds, wrong writer execution identity, changed supervision group,
  one-stage postconditions, route currentness, and no direct writes. Ruff and
  Python compilation passed. All 105 frontend tests, TypeScript, and the
  production build passed. Focused Playwright passed 3/3 across desktop,
  tablet, and mobile with seven-stage/source/writer/period/delivery rendering,
  one exact captured stage request, Axe serious/critical checks, and no
  horizontal overflow. The full-profile verifier reports all 32 Blocks with 0
  errors/warnings, all 30 verifier tests pass, and `git diff --check` passes.
  The restarted loopback runtime on port 8787 reports complete health and 22
  supported operations among 24 closed registry entries. No live prepare,
  cognitive review, finalize, delivery, Gmail, policy, event, or report write
  was attempted. Independent exact-revision review is pending.
- Product-capability review selected the existing deterministic weekly-report
  artifact owner, configured roundup-writer task, canonical event/policy
  sources, typed operation coordinator, and Gmail delivery receipt owner. A
  dashboard-local report generator/delivery registry and a generalized workflow
  engine were rejected because they would duplicate stronger maintained owners
  and broaden this Block beyond one report workflow.
- First exact-revision review: independently `REJECTED` evidence
  `b9fb8c2ec9754512becc296a0d0537dc5e60fb3b`, tree
  `997af28ae3558c6e281f572cb19a263fdb5ba097`, over product
  `becca0646d1b3d64c88ba2110e3bb3c4c9c1c28e`. The sole material finding was
  the restart/recovery state where an exact valid `review.json` survived a
  finalize failure: projection truthfully marked cognitive review complete but
  still exposed `review-finalize`, whose prompt asked Sol XHigh to synthesize
  the review again. That contradicted stage reuse and could strand recovery
  when the second valid synthesis differed byte-for-byte. All other report
  owner, currentness, delivery, bounds, route, UI, mechanical, and Stop proof
  passed and remains reusable; Block 28 stayed closed.
- Retained-review recovery correction: product successor
  `328131782aaa9cb48c85f7cac9b5b34009cf2783`, tree
  `bdc885f2f03ed21b544489b0f2cc5ea3db9af0ee`, parent rejected evidence
  `b9fb8c2ec9754512becc296a0d0537dc5e60fb3b`, changes only eight affected
  projection/operation/schema/UI/test files. A source-valid retained review now
  produces the distinct `finalize-verify` stage/action: cognitive review remains
  complete, finalize is current, the UI says `Finalize & verify`, and the owner
  prompt explicitly forbids producing, regenerating, editing, or reinterpreting
  the review. It reads and base64-encodes the exact retained JSON for the
  maintained replay-safe finalizer, then invokes verification; an absent or
  changed review stops rather than rerunning cognition.
- Correction proof: an exact maintained prepare plus retained canonical review
  restarted into `finalize-verify` with cognitive review `complete` and
  finalize `current`; the operation source and prompt preserved that action and
  contained no synthesis instruction. Focused backend passed 2/2 with
  `ResourceWarning` fatal, focused frontend/schema passed 22/22, production
  TypeScript/Vite build passed, Ruff and Python compilation passed, and focused
  Playwright passed 3/3 across desktop/tablet/mobile with the retained-review
  stage, `Finalize & verify`, exact one-stage request, Axe serious/critical, and
  no-overflow proof. The full-profile verifier remained 32 Blocks with 0
  errors/warnings, all 30 verifier tests and diff checks passed, and remote
  divergence was `0 0`. Prior unaffected report/backend/frontend/delivery proof
  is reused. No live report or Gmail action occurred; fresh focused exact review
  is pending.
- Second exact-revision review: independently `REJECTED` evidence
  `03c7725ce652750620cde0b55354ee624f778caf`, tree
  `e18151c8240d1de3c5b3dd7a0666d3218f655626`, over product
  `328131782aaa9cb48c85f7cac9b5b34009cf2783`. The product recovery was sound,
  but the new browser fixture borrowed the live run's unassigned project
  posture, so `Finalize & verify` was disabled and the claimed three-viewport
  proof was not reproducible. All backend, frontend, build, mechanical,
  currentness, owner, and Stop proof remained valid and reusable.
- Browser-fixture correction: product successor
  `4fcfd7ccc3eccab608cb8b4a14a3b5b127ef2d40`, tree
  `3443c05a0064cbb129ba18b66115b7acdd654585`, parent rejected evidence
  `03c7725ce652750620cde0b55354ee624f778caf`, changes only the focused
  Playwright fixture. The fixture now owns a consistent exact
  `software-factory` project binding matching the asserted operation target
  instead of borrowing mutable live binding posture. The exact rejected test
  reran serially against port 8787 and passed 3/3 across desktop, tablet, and
  mobile, including the captured `finalize-verify` request, Axe checks, and
  no-overflow assertions. No owner dispatch, report artifact, Gmail action, or
  canonical mutation occurred; fresh delta-only exact review is pending.
- Fresh delta-only exact-revision review: independently `ACCEPTED` evidence
  `d1c9ab83471e428450e3f52fd80d809ab31ffc71`, tree
  `b7cb5a7a8e5d0dd5495e741ffae533f33465472c`, over product/test correction
  `4fcfd7ccc3eccab608cb8b4a14a3b5b127ef2d40`, tree
  `3443c05a0064cbb129ba18b66115b7acdd654585`, with no material finding. The
  exact rejected browser case passed 3/3 at desktop, tablet, and mobile with a
  consistent source-owned project binding, enabled `Finalize & verify`, exact
  captured operation target, zero serious/critical Axe findings, and no
  horizontal overflow. Full-profile verification, diff, object, clean-checkout,
  remote `0 0`, and Stop gates passed. Block 27 is accepted at this revision.

### Stop

Stop before terminal reporting, Factory evolution, request-stop, or shutdown.

---

## Block 28 — Factory evolution evaluation and disposition

Status: `accepted`

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

- Activation: Block 28 started automatically after independent acceptance of
  Block 27 evidence `d1c9ab83471e428450e3f52fd80d809ab31ffc71` and
  product/test correction `4fcfd7ccc3eccab608cb8b4a14a3b5b127ef2d40`.
  Governing implementation authority remains direct-user item 44 under mission
  root `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Work is limited to the maintained Factory-evolution derived-artifact and
  disposition owner. Blocks 29–31 remain closed; no evolution artifact,
  external candidate implementation, adoption, deployment, routing,
  scheduling, or outcome mutation has been attempted.
- Frozen implementation candidate: commit
  `e34d92a9c98e4cc8a4ca5e50c1e0beb1a5e71c1e`, tree
  `b7af97cc132fbccb88f1934826e59ba262b10141`, parent
  `65b462994e2a71b46261bff2f246ed9b87f31a7d`. The 17-file slice registers
  `factory.evolution-evaluate`, projects one deterministic packet/current
  stage through the run and report APIs, and adds compact source-backed run,
  Reports, and Admin displays. It invokes only the installed maintained
  `factory-evolution prepare/finalize/evaluate/verify` owner through one
  configured proposer or evaluator turn. External implementation remains an
  exact Block 11 task/Git input and the operation exposes no candidate writer,
  adoption, installation, routing, scheduling, deployment, rollback, or
  outcome owner.
- Truth, authority, and recovery proof: the projection requires one current
  verified weekly report, its exact `report.json`, the canonical event ledger
  head, a deterministically rebuilt packet/evolution identity, immutable
  owner-verified artifact inventory, and three distinct configured proposer,
  implementer, and evaluator identities. Preview binds report/event/packet/
  policy/project/role roots and, for evaluation only, a clean exact baseline
  ancestor/candidate revision pair attributable to the separate current
  implementation task. Dispatch re-resolves that fingerprint and the route
  gate, starts one stage owner once, and verification re-reads both independent
  role contracts, external candidate evidence when applicable, the exact stage
  postcondition, and the route. Missing, changed, aliased, partial, or invalid
  sources remain unavailable or pending; accepted earlier artifacts are reused
  and there is no automatic retry.
- Validation: dashboard-server discovery passed 137/137 with
  `ResourceWarning` fatal before the final role-currentness hardening, whose
  affected projection/coordinator regressions then passed 2/2. The maintained
  Factory-evolution owner suite passed 30/30 across all four dispositions and
  invalid/stale/role/resource cases. Ruff and Python compilation passed. The
  full frontend passed 19 files and 108 tests, TypeScript/Vite production build
  passed, and the focused evolution browser case passed 3/3 across desktop,
  tablet, and mobile while exercising run, Reports, and Admin projections,
  the exact preview request, serious/critical Axe checks, no horizontal
  overflow, and absence of adoption/deployment controls. `git diff --check`
  passed.
- Live nonmutating proof: the exact candidate server was restarted on
  loopback port 8787. Health, Reports, operations, and Admin returned HTTP 200;
  the operation registry reports `factory.evolution-evaluate` supported with
  confirmation class `factory-evolution`, the maintained multi-owner contract,
  and disposition-only postcondition. Six current run-local evolution
  projections are truthfully `unavailable` because their exact prerequisites
  are not all current; no zero, synthetic candidate, or apparent success is
  substituted. No live preview, role request, artifact creation, external
  implementation, disposition, adoption, deployment, or canonical mutation
  was attempted. Exact-revision review is pending and Blocks 29–31 remain
  unopened.
- Rejected exact review retained: independent review rejected evidence
  `d27ceaaa2b4350ea516aa87de65b0dd2d2f4b27c` and product
  `e34d92a9c98e4cc8a4ca5e50c1e0beb1a5e71c1e` only because the verified
  evaluation was validated and then omitted from the dashboard read model.
  Stage, root, disposition, owner, currentness, mutation, and Stop proof remains
  reusable. The correction is limited to a bounded verified comparison summary
  and its Run/Reports/Admin rendering.
- Pre-broad execution brief boundary, recorded after focused correction proof
  and before any broad mapped replay:
  - Maintained owner: complete. The projection consumes only normalized output
    from the existing `verify_evolution_review` and
    `verify_candidate_evaluation` owners; no helper, owner command, operation
    registry, preview, dispatch, verification, or postcondition code changed.
  - Source/currentness: complete. Plan and result fields come only after exact
    owner verification; report/event/packet/review/evaluation/manifest roots,
    the directory tree key, and the existing workflow fingerprint remain the
    currentness boundary. Missing review produces no plan; missing evaluation
    produces no results; invalid owner material still fails unavailable.
  - Authority: source-backed not applicable to this read-only correction. No
    confirmation, route gate, task start, owner request, candidate writer, or
    mutation authority was added or changed.
  - External implementation: source-backed not applicable. Existing Block 11
    task/Git proof remains the sole candidate input; the summary cannot launch,
    accept, retry, or modify that work.
  - Recovery/resource bounds: complete. Recovery is stage-derived read-only
    guidance with preserved exact roots; it performs no retry. Displayed prose,
    lists, candidates, cases, and evidence are already bounded by the maintained
    evolution validator and the existing bounded artifact reader.
  - Security/UI truth: complete. React renders text without raw HTML; exact
    result records preserve condition revision, evidence root, and canonical
    event links. Planned, missing, verified, advisory, revise, reject,
    regression, contrary-evidence, and no-adoption postures have focused proof.
  - Stop: complete. No implementation, adoption, installation, routing,
    scheduling, deployment, rollback, outcome, terminal-report, request-stop,
    or shutdown owner is introduced; Block 29 remains `not-started`.
  - Focused proof before the one broad run: backend comparison/projection tests
    passed 2/2 with `ResourceWarning` fatal; affected frontend schema,
    component, Reports, Run, and Admin tests passed 20/20; production build,
    Python compilation, and Ruff passed. The first focused browser assertion
    incorrectly expected an unshortened identity even though the identity
    control retained it; after narrowing that test-only assertion to the visible
    rejected-path effect, the affected desktop/tablet/mobile exercise passed
    3/3 with planned and verified states, exact source links, regressions,
    contrary evidence, Axe checks, and no horizontal overflow. All
    likely-mutating review is therefore complete or source-backed not applicable
    before the single broad matrix.
- Frozen comparison-workspace successor: product commit
  `5d1e51d408992545fe5465c77cd6d0bc40b2d863`, tree
  `a66361eae8157a4a613758357d1ccc81abb7d876`, parent rejected evidence
  `d27ceaaa2b4350ea516aa87de65b0dd2d2f4b27c`. The 16-file correction retains
  the existing owner and operation coordinator and adds only the bounded
  owner-verified comparison plan/results projection, strict Zod contract,
  compact shared Run/Reports/Admin evidence component, responsive styling, and
  focused proof. Planned state exposes selection rationale, selected and
  compared-not-selected candidates, tradeoffs, uncertainty, resource and Stop
  bounds, explicit unavailable results, and stage recovery. Evaluated state
  separately exposes baseline/candidate case outcomes, evidence class, exact
  condition revision and evidence root, canonical event links, observed effect,
  cost, per-case and aggregate regressions, contrary evidence, evaluation
  rationale, disposition, limitations, and preserved roots. It adds no owner,
  editor, retry, preview, dispatch, acceptance, adoption, or deployment path.
- Single broad mapped run after the pre-broad boundary: dashboard backend
  passed 138/138 with `ResourceWarning` fatal, the maintained evolution owner
  passed 30/30, Ruff passed, frontend passed 20 files/113 tests, and the
  TypeScript/Vite production build passed. The one serial Playwright matrix
  completed 72/78; the corrected Factory-evolution case passed 3/3. Its six
  failures were preserved as unaffected diagnostics rather than hidden by a
  replay: three live drill-down assertions expected issue follow-up unavailable
  after the canonical run made it eligible; two dark-theme report-link checks
  exposed a pre-existing color-only distinction; and one mobile Factory Floor
  inspector fixture raced. No second broad matrix was run and none of those
  unrelated rows was folded into this successor. After an indentation-focused
  review preserved `awaiting-implementation` without requiring a disposition,
  the affected backend 2/2, Ruff, full-profile verifier (32 Blocks, 0 errors,
  0 warnings), verifier tests 30/30, and diff check all passed. The exact server
  is running on loopback port 8787 with the new plan/results/recovery keys and
  truthful unavailable values for all six current source projections. Fresh
  exact-revision review is pending; Block 29 remains closed and no live
  evolution action or canonical mutation occurred.
- Independent exact-revision acceptance: evidence
  `bab551b74ca561dd0053e8c2b2158b321afc52e4`, tree
  `9e58855a6a354ffcb684d4d026c455e91aa9ed33`; product
  `5d1e51d408992545fe5465c77cd6d0bc40b2d863`, tree
  `a66361eae8157a4a613758357d1ccc81abb7d876`. The reviewer found no material
  issue and independently reproduced backend 2/2, affected frontend 40/40,
  build, Ruff, Python compilation, focused browser 3/3, full-profile 32-Block
  verification with 0 diagnostics, verifier tests 30/30, diff/fsck/remote/
  clean gates, and the Block 29 Stop. The pre-broad brief preceded the one
  documented 72/78 matrix; Block 28 passed 3/3, all six unrelated diagnostics
  remain truthful, and no replay, harness mutation, live evolution action, or
  canonical mutation occurred.

### Stop

Stop at the verified `promote`, `advisory`, `revise`, or `reject` disposition,
before candidate implementation/maintenance, adoption, installation, routing,
scheduling, deployment, outcome/rollback control, terminal reporting, or final
acceptance.

---

## Block 29 — Terminal report workflow

Status: `in-progress`

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
  remains Block 30.
- Tradeoff and source evidence: required currentness, cognitive review,
  verification, and delivery add latency but are mandated by the terminal report
  and supervision lifecycle contracts.

### Inputs and dependencies

- Accepted Block 9 report/history workspace.
- Accepted Blocks 10 and 11 operation/task owners.
- Accepted Block 13 semantic-review handling and Block 27 verified prior-report
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

- Activation: Block 29 started automatically after independent acceptance of
  Block 28 evidence `bab551b74ca561dd0053e8c2b2158b321afc52e4` and product
  `5d1e51d408992545fe5465c77cd6d0bc40b2d863`. Governing implementation
  authority remains direct-user item 44 under mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
  Work is limited to the maintained terminal-report artifact and configured
  delivery owners. Blocks 30–31 remain closed; no completion decision,
  request-stop, lifecycle transition, automation pause, shutdown, Gmail read,
  or Gmail send has been attempted.
- Pre-broad execution brief — `2026-08-12T11:51:51Z`, focused proof complete,
  broad validation not started. The bounded product/test worktree contains 15
  files and has binary-diff SHA-256
  `517bb9026f69f4a2941bf236c6f0ba6d69bc2f0e55bc1e106f35dfa83beef060`.
  Before any broad matrix, every likely-mutating boundary was classified and
  checked as follows:
  - **Complete — authority and range:** direct-user item 44 and mission root
    `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`
    remain the implementation authority; only Block 29 is active and Blocks
    30–31 remain closed.
  - **Complete — exact outcome source:** projection requires one current mission,
    the latest current-mission `completed` lifecycle, its exact state
    fingerprint, one maintained outcome-completion record accepted by
    `assess_outcome_completion_record`, and the lifecycle's exact binding to
    that record. Missing, failed, stale, or unreconciled evidence is
    unavailable, never actionable.
  - **Complete — report owner/currentness:** the maintained supervision,
    terminal-report, and policy-owner SHA-256 values are respectively
    `46d225ae949e332b0a6718fb400c8f05818d8ac8462a5aac8bce86fe6e532e78`,
    `800c2ff04bc3dcefaf124aa57d37ad85b42b5732db6825b8225cbf11a437c138`,
    and `31cbe227f1fa91a184f022bfc1ff3ca49c0feac086e20d7bb621adccdcf24a0a`.
    Projection rebuilds the maintained packet, binds the source root/report
    tree/owner revision, verifies every prior weekly report through its
    maintained owner, rejects a changed retained packet, and rechecks owner
    revisions after composition.
  - **Complete — independent writer/reviewer owner:** the terminal contract's
    exact `base_reviewer` role and `base_reviewer_thread_id` are used, with
    `changed-state-review` route purpose. The configured task must be distinct
    from the target, fully read, idle/not-loaded, projectless-capable, and bound
    to the complete Sol XHigh execution contract and exact cwd identity.
    Focused negatives reject a roundup-writer substitution or a terminal
    projection that claims the wrong role.
  - **Complete — consequential action/currentness:** one typed confirmation
    consumes one preview, re-resolves project/group/policy/workflow/task/cwd and
    route-gate state before dispatch, starts at most one exact base-reviewer
    turn, re-reads its exact marker and completed turn, re-runs the route gate,
    and verifies the named postcondition. No automatic retry exists.
  - **Complete — stage and recovery bounds:** prepare, source currentness,
    cognitive review, finalize, JSON/Markdown/PDF/manifest verification,
    display, and delivery remain distinct truth-labeled stages. An exact
    retained review is reused after a later-stage failure; only the first
    incomplete stage is offered and accepted earlier stages must remain
    present.
  - **Complete — delivery ownership:** the dashboard projects only the
    configured primary Gmail lane and canonical delivery/read-back record. The
    base-reviewer prompt routes the verified two-PDF reply and raw-MIME plus
    attachment read-back through the configured Gmail and maintained terminal
    owners; dashboard server/UI code performs no Gmail read, attachment read,
    send, or delivery-ledger write.
  - **Source-backed not-applicable — live delivery mutation:** the current live
    run has no reconciled completed lifecycle, so its workflow correctly
    projects `terminal_report_completion_unavailable`. No live terminal report,
    Gmail reply/read-back, or delivery record is authorized or needed for this
    implementation proof; maintained owner tests supply disposable artifact
    coverage and the browser intercept stops before dispatch.
  - **Complete — lifecycle and Stop:** operation evidence hard-codes direct
    lifecycle/report/Gmail writes, request-stop, automation pause, terminal
    shutdown, and automatic retry as false. The semantic diff preserves those
    actions as not performed, the workflow always projects shutdown through a
    separate owner with `permitted=false`, and no Block 30/31 owner is called.
  - **Complete — UI/history boundary:** only the current run receives the action
    and current terminal workflow; predecessor mode suppresses all current
    report/action state. Run and Reports expose exact stage, completion,
    coverage, prior-report count, source/manifest identity, delivery posture,
    limitations, and the explicit shutdown separation without a second editor
    or direct-write path.
  - **Complete — focused proof:** maintained terminal-report owner passed 11/11;
    focused backend projection/workflow/registry/live-API proof passed 4/4 plus
    the role/currentness test 1/1; focused frontend schema/action/Run/Reports
    proof passed 35/35 and the final affected display pass was 11/11; Ruff,
    Python compilation, TypeScript, production build,
    and diff check passed. The exact restarted loopback runtime on port 8787
    reports complete health coverage, exposes 26 closed registry descriptors
    including the supported terminal operation, and focused Playwright passed
    3/3 at desktop/tablet/mobile with Axe and no-overflow checks. No broad suite
    or broad browser matrix had started when this brief was written.
- Single broad mapped run after the pre-broad checkpoint
  `23e8f43d7281d86ff90ea7c6c863335185ce7169` — `2026-08-12T12:03:00Z`:
  dashboard backend passed 140/140 with `ResourceWarning` fatal, frontend
  passed 20 files/114 tests, and the TypeScript/Vite production build passed.
  The one serial Playwright matrix completed 76/81; the new Block 29 terminal-
  report case passed 3/3 at desktop/tablet/mobile. Its five failures are the two
  already-recorded unaffected Block 28 diagnostic families: three live drill-
  down assertions expected `Issue follow-up` disabled after the canonical run
  made it eligible, and two tablet/mobile Reports checks exposed the existing
  dark-theme link-within-text contrast/style defect. The formerly observed
  mobile Factory Floor fixture race did not recur. No second broad matrix was
  run, no harness/configuration was changed, and neither unrelated diagnostic
  family was folded into Block 29. The loopback health envelope remained
  complete immediately before the browser run; no terminal report, Gmail,
  lifecycle, automation, request-stop, or shutdown mutation occurred.
- Independent exact-revision review rejected evidence
  `c8199876018c7840725287db5dd743f2bd13469b` on two bounded rows: a stale
  append-once delivery was labeled retryable despite having no supported owner
  action, and this consequential Block lacked its compact product-capability
  decision. All other owner, currentness, staged recovery, UI, pre-broad-order,
  single-broad-run, remote, and Stop evidence was accepted as reusable.
- Product-capability decision — `2026-08-12T12:17:45Z`, consequential frame
  3,511 bytes, SHA-256
  `736124301d439cf6f143bb8013d53f085e9f3f4748df35451ef1bce5df0d8857`:
  - Rejected a local dashboard/registry implementation that would generate or
    validate terminal artifacts, read or send Gmail, or write delivery state;
    that path would create duplicate owners and grant the UI report and mail
    authority it does not have.
  - Rejected a generalized weekly/terminal workflow abstraction because the
    terminal family has distinct completed-outcome, prior-report, base-reviewer,
    two-PDF, delivery/read-back, and no-shutdown contracts; a shared action
    would erase independently recoverable stages and owner postconditions.
  - Selected the narrow composition of the maintained terminal prepare/
    finalize/verify owner, current policy and `base_reviewer` task owner,
    changed-state-review route gate, configured Gmail read/send owners, and
    canonical append-once delivery verifier behind the existing typed preview/
    confirmation coordinator and read-only Run/Reports projection.
  - Protected effects are exact outcome and mission currentness, retained-review
    reuse, prior-report verification, independent cognitive review, immutable
    artifact and delivery evidence, predecessor suppression, and the absence of
    direct Gmail, lifecycle, automation, request-stop, or shutdown effects.
    The selected path costs more configuration, owner round trips, and explicit
    unavailable/stale states, but preserves authority and makes partial recovery
    truthful instead of substituting a lower-power local workflow.
- Narrow product successor
  `bf03d8e9e825f6b695670b5e4e9b4ea89ce4bc40`, tree
  `4502e2c7e8f471141f1d9218ecbae2be839c40df`, changes only projection and its
  focused backend/component proof. `delivery-stale` now has no next action,
  `actionable=false`, `retryable=false`, and a structured non-retryable
  `terminal_report_delivery_stale` error explaining that the append-once owner
  cannot replace the receipt. The exact backend regression passed 1/1 with
  `ResourceWarning` fatal; the first invocation named a nonexistent test class
  and executed no product test, after which the corrected invocation passed.
  The affected action component passed 22/22, Ruff, Python compilation, and the
  TypeScript/Vite production build passed. No broad matrix was replayed and no
  live owner action occurred; fresh exact-revision review is pending.
- Exact delta review accepted the capability decision but rejected evidence
  `601d82c90f3aa52ef3bcbffb13385ddc4cf46fed` because delivery lookup was scoped
  only to the lifecycle. A historical receipt for a different report set could
  therefore be mislabeled as an append-once conflict for the current set.
- Exact-set successor `f180e60411c27f8314de83a96e1789a3b91a5a1f`, tree
  `aabf4faad8da84c573880df5761f57d999d8b3ce`, changes only projection and its
  focused backend proof. The dashboard now filters canonical delivery events
  to the exact current `report_set_id` before invoking the maintained latest-
  delivery owner. A different-set historical receipt yields no current-set
  receipt and preserves the supported `delivery` action; an exact same-set
  stale receipt remains `delivery-stale`, non-actionable, and non-retryable.
  The focused case proves an old-only set selects nothing, mixed old/current
  sets select the exact current receipt, no receipt remains pending/deliverable,
  and same-set stale remains closed; it passed 1/1 with `ResourceWarning` fatal,
  Ruff, Python compilation, and diff check. No broad or browser matrix was
  replayed and no live owner action occurred; fresh exact review is pending.

### Stop

Stop before request-stop, automation pause, terminal shutdown, or final
cross-project acceptance.

---

## Block 30 — Request-stop and terminal shutdown

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
- Accepted Block 29 verified terminal report workflow.
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
- Keep turn interruption, Blocks 22 and 24 pause/resume, Block 29 terminal report, and
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

## Block 31 — Integrated outcome validation and operator handoff

Status: `not-started`

### Objective

Prove the complete dashboard against current multi-project sources and real
bounded operations, close supported findings on the frozen candidate, and hand
off a reproducible local operating workflow.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates, documents, and
  hands off the capability selected and implemented in Blocks 0–30; it may fix
  mapped defects but must not add a new product surface or operating model.

### Inputs and dependencies

- Accepted Blocks 6–30 and all inherited accepted dependencies.
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
  content, source links, Factory Floor disclosure/count chips, tracker count
  chips/total-and-active claims/source diffs, operation semantic diffs, and no
  page-level horizontal overflow.
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
- Verify the adapted `TaskRows.tsx`, `FilterTable.tsx`, and `DiffTable.tsx`
  provenance notes and supplied-source hashes, and confirm demo data,
  timer-driven state, unsupported retry/edit controls, gallery navigation, and
  chain-of-thought labels are absent from the production bundle and UI.
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
  latest conclusion against exact live sources through compact accessible
  disclosure; its high-signal counts remain exact/partial/unavailable according
  to live coverage, and its tracker total plus all task/tracker/supervision
  active-Block claims remain exact, current, separately labeled, and conflict-
  aware.
- Tracker filters/source diffs and policy/binding/automation preview diffs trace
  to their exact owners, roots, currentness, bounds, and source links without
  adding an editor, alternate confirmation, or acceptance path; tracker index
  and detail show the maintained-verifier total plus every current active claim
  with explicit none/partial/unavailable/conflict posture.
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
  healthy/zero state, truncated rows produce an exact-looking count, an active-
  Block claim is collapsed/coalesced or crosses a predecessor mission boundary,
  a semantic diff is browser-inferred or color-only, or an outcome claim rests
  only on process evidence.
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
| Tracker truth | parser fixtures, maintained verifier JSON, exact-total/active-claim coverage, and bounded Git/source-diff tests | full/core/malformed/dirty/stale tracker comparison, plural/conflicting active claims, plus semantic diff/source drill-down | reviewer sees exact total and every current source-labeled active Block, then reaches exact capability, evidence, diagnostics, semantic source change, and source without an edit/acceptance path |
| Supervision/history | ledger/policy/report validators and corrupt/partial fixtures | live target source cross-check | active and historical run claims match exact event/incident/decision/transition records |
| Metrics/reports | definition, unit, coverage, estimate, artifact-path tests | cross-project/report comparison against manifests | each displayed number explains period, denominator, source, limitations, and estimate posture |
| Codex task integration | fake App Server protocol suite | version-gated live list/read/disposable task smoke | task/turn/items/approval/input state and controls match the official live owner |
| Factory Floor/UI | adapted operational-row/filter source, component/axe/topology/light/conclusion/count-coverage and total/active-claim tests | three-project, three-viewport, light/dark Playwright matrix with one/multiple/none/conflicting active Blocks | operator identifies each implementation/supervisor/mission/target, exact tracker total, every current active claim, operating reason, issues, actions, conclusions, history, and freshness through keyboard-accessible disclosure and exact/partial counts |
| Administrative safety | schema, nonce/origin, preview, semantic-diff, replay, stale, route-gate, postcondition tests | disposable workflow operations and denied advanced paths | enabled action has intended owner consequence; owner-backed before/after remains distinct from confirmation/applied state; denied/unavailable action fails closed |
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
