# Software Factory changelog

This is the human-consumable history of significant Software Factory
capabilities, operating contracts, authority boundaries, compatibility changes,
and implementation programs. It is intentionally more descriptive than a list
of commit subjects, but it is not a second operational ledger.

High-precision evidence remains in Git history, implementation-tracker
completion evidence, canonical supervision events, verified `report.json`
artifacts, tests, and exact candidate reviews. Changelog entries summarize those
sources and link or cite exact revisions when that materially improves
traceability.

## Maintenance contract

Update this file at the coherent checkpoint where any of the following becomes
planned, implemented, adopted, materially corrected, deprecated, or removed:

- a reusable Software Factory capability or workflow;
- operator-visible behavior or a public skill contract;
- an authority, autonomy, supervision, evidence, or outcome-closure boundary;
- a compatibility, migration, installation, or runtime requirement; or
- a significant implementation tracker that changes the intended product
  direction.

Every entry must distinguish `Proposed`, `Planned`, `Implemented`,
`Demonstrated`, `Corrected`, and `Removed` truthfully. A planned tracker is not
implemented behavior; a passing experiment or `promote` disposition is not
automatic adoption; and process evidence is not an operator-visible outcome.

Include the capability effect, important boundaries or compatibility posture,
and the strongest useful evidence reference. Do not add every test fixture,
review-only successor, evidence-only checkpoint, typo, or internal refactor
unless it changes how a material result should be understood. Tracker authors
should include a changelog update in the terminal documentation Block whenever
the completed program materially changes Software Factory.

## Unreleased

### Implemented

- **Integrated local Software Factory operations dashboard.** The loopback
  Python service and React/TypeScript/Vite application now provide the complete
  Factory Floor, project/run/supervisor/task drill-downs, implementation-tracker
  review, cross-project metrics and verified reports, Admin health, and a closed
  owner-gated operation framework. Compact expandable rows preserve exact task,
  run, mission, tracker, Block, supervisor-group, role, automation, issue,
  action, conclusion, and freshness identities. Tracker surfaces show the
  maintained-verifier total and every current task/tracker/supervision
  active-Block claim without coalescing disagreement; counts remain explicitly
  exact, partial, lower-bound, conflicting, none-active, or unavailable. The
  collapsed Factory Floor now also shows exact accepted/done and remaining
  Block counts beside the maintained-verifier total, with `Tracker complete`
  reserved for an exact canonical tracker whose Block statuses and accepted or
  completed header agree; contradictory headers stay visibly conflicting.
  Consequential task, tracker, supervision, binding, lifecycle, reporting,
  evolution, succession, and terminal requests use typed previews, exact source
  fingerprints, owner-supplied semantic diffs, operation-specific confirmation,
  route gates, and canonical postcondition re-reads. The dashboard stores only
  project discovery metadata and process-local operation correlation: it never
  edits primary operational truth, invents progress, treats a report or task
  state as completion, adopts an evolution candidate, exposes arbitrary shell/
  protocol access, or binds beyond loopback. The selected Beautiful UI
  TaskRows, FilterTable, and DiffTable sources were adapted to the existing
  tokens and accessibility contract without adopting the gallery shell or demo
  semantics. Block-by-Block evidence and compatibility roots are in the
  [32-Block implementation tracker](docs/software-factory-operations-dashboard-implementation-tracker.md);
  operating and recovery boundaries are in
  [`dashboard/RUNBOOK.md`](dashboard/RUNBOOK.md). Final independently accepted
  product: `5a83a46b498ab636ac79c5c0c79c1003308b3b04`; acceptance evidence:
  `4e1fbdd037729e94f3ed0fd1948e083e30b5cf31`. Post-acceptance Factory Floor
  progress correction: `f0b4546f0ff4c9d8d4c3534111f358f15ef5597e`.
- **Loopback operations-dashboard foundation.** Added an installable Python
  runtime and a responsive React/TypeScript/Vite shell for the planned Factory
  Floor, Projects, Trackers, Reports, and Admin workspaces. The service binds
  only to loopback, serves a versioned health envelope and production SPA,
  rejects non-loopback startup, and gates local writes by exact origin and a
  per-launch nonce. The shell uses the
  frozen reference stack, preserves keyboard, dark-mode, responsive, loading,
  error, empty, and unavailable states, and labels all operational sources as
  disconnected until their owning Blocks are accepted. Developer commands and
  boundaries are documented in [`dashboard/README.md`](dashboard/README.md);
  implementation scope is Block 1 of the operations-dashboard tracker.
- **Bounded multi-project catalog and discovery.** Added a versioned,
  atomically written owner-only project catalog with optimistic fingerprints,
  prior-file recovery, canonical Git-root enforcement, duplicate and overlap
  protection, deterministic ordering, and explicit archive/restore semantics.
  The Admin and Projects views can register and independently refresh exact
  local roots, show Git revision/branch and tracker candidate paths, and retain
  per-project discovery failures without hiding healthy repositories. The
  catalog stores presentation/discovery metadata only, never scans the
  workstation, never reads tracker contents in this slice, and rejects copied
  operational state, traversal, symlink escape, stale writes, and any wording
  or behavior implying that archive deletes files or stops work. Implementation
  scope is Block 2 of the operations-dashboard tracker.
- **Read-only tracker truth and Git-currentness API.** Added closed Python and
  Zod list/detail contracts that project discovered tracker header, capability
  frames, owner/source maps, Blocks, exact status and evidence-posture counts,
  dependency eligibility, source anchors, maintained-verifier diagnostics, and
  Git HEAD/index/worktree/blob/history/upstream currentness. Full-profile and
  explicitly approved inherited core trackers remain distinct; malformed,
  dirty, untracked, stale-bound, and unavailable sources retain exact local
  diagnostics without hiding healthy trackers. Unchanged analysis is keyed by
  tracker content, verifier content, and profile, while Git reads are batched by
  repository. This slice is read-only: it adds no tracker workspace, status
  mutation, acceptance, task start, or synthetic progress percentage.
  Implementation scope is Block 3 of the operations-dashboard tracker.
- **Read-only supervision, report, and metrics projection.** Added closed
  Python and Zod contracts for current and predecessor mission history,
  supervisor topology, exact role/task/automation bindings, lifecycle and
  successor continuity, incidents, decisions, activity, semantic conclusions,
  verified weekly/terminal/evolution report bundles, and maintained-owner
  metrics. Transparent attention reasons and red/amber/green/neutral rules keep
  source-local failures and unmonitored projects visible without letting one
  damaged target erase healthy data. Cross-run totals aggregate only additive
  dimensions; API-equivalent cost remains an explicitly labeled estimate. This
  slice is read-only and neither inspects automation prompts nor mutates runs,
  lifecycle, supervision, or reports. Implementation scope is Block 4 of the
  operations-dashboard tracker.
- **Version-gated Codex task adapter.** Added one long-lived stdio App Server
  child behind the loopback Python service. Startup requires exact
  `codex-cli 0.145.0` and reproduces the frozen 273-file non-experimental schema
  root before enabling typed task list/read/start/resume, turn start/steer/
  interrupt, approval/input response, and ephemeral same-origin event-stream
  capabilities. Task cwd binds only to canonical registered projects; stale
  request fingerprints, unknown methods, schema drift, malformed or duplicate
  responses, mismatched IDs, timeouts, and child failure disable mutations
  without suppressing file-backed monitoring. Validated protocol errors retain
  explicit not-found, provider-error, terminal, and bounded reconnect truth.
  The event stream resumes from its last consumed cursor, signals replay-window
  gaps before invalidating durable projections, and caps reconnect backoff;
  completed callback records are evicted before live approval/input capacity is
  refused. Adapter failures are generation-bound, so an in-flight request
  cancelled by an intentional restart cannot downgrade or terminate the
  healthy replacement child.
  Admin exposes compact integration health and an adapter-only restart. Task/
  turn mutations remain internal typed capabilities until owner-mediated
  workflows register them; generic prompts, raw protocol, general tool/model
  settings, remote transport, task forking, and permission-profile mutation
  remain unavailable.
  Implementation scope is Block 5 of the operations-dashboard tracker.
- **Cross-project Factory Floor.** Added a read-only composed endpoint and the
  default four-region operating view for implementation/supervisor rows,
  ranked attention, semantic conclusions beside accepted tracker outcomes,
  and bounded metrics/source freshness. It joins only exact current catalog,
  tracker/Git, supervision/report/metric, and Codex task projections; preserves
  unresolved, candidate, ambiguous, unmonitored, orphaned, partial, stale, and
  disagreeing states; and stores no operational data. Every operating light has
  text, reason, source time, and an explicit non-completion posture. Filters
  keep hidden critical counts visible; row, attention, conclusion/outcome,
  source-health, and metric cards retain source-bearing inspector routes; and
  API-equivalent cost remains labeled as an estimate rather than spend. The
  compact interface uses functional region labels without marketing subheaders
  and is validated at desktop, tablet, and mobile widths. Implementation scope
  is Block 6 of the operations-dashboard tracker.
- **Source-grounded project, run, supervisor, and task workspaces.** Added a
  compact Projects operating index; contextual project Overview, Work,
  Trackers, Reports, and Sources views; exact run and supervisor-group
  inspectors; and bounded Codex task detail. Factory Floor links preserve the
  active project/time filters while each workspace keeps canonical task, run,
  tracker, report, policy, role, automation, event, incident, decision, and
  transition identities separate. Long-lived targets can select an exact
  mission segment: predecessor views use only mission-scoped records and
  historical hashes/timestamps, explicitly suppress current lifecycle,
  topology, role-task, automation, report, metric, and source-head state, and
  never issue current task reads for the historical projection. Event filters,
  stable anchors, bounded turn summaries, independent source failures, and
  explicit unavailable/lower-bound states keep the interface useful without a
  dashboard-owned history store or inferred completion. The slice is read-only;
  tracker deep review, report analytics, and owner-gated mutations remain in
  later Blocks. Implementation scope is Block 7 of the operations-dashboard
  tracker.
- **Successor-transition continuity and structured failure-mode records.** A
  requested implementation that must cross into a distinct task now remains an
  open append-only transition through `required`, task creation, isolated
  mission/group binding, handoff, target acknowledgement, and first-Block work
  start. `successor-transition-gate` prohibits treating the source as stopped
  or complete before current `work-started` evidence, while preserving the
  exact tracker, mission, Block range, authority, and successor identities.
  Routed supervisor provenance cannot manufacture the direct authority needed
  to create a user-owned task. Incident records can also carry a reusable
  failure-mode envelope describing mechanism, trigger, effect, detection,
  correction, recurrence invariant, and any human-scheduling leak in the same
  canonical ledger. The initiating event is
  `INC-20260808-180850-C22F9D` / `EVT-000067`; focused regression coverage is in
  `SuccessorTransitionContractTests`.

### Planned

- **Adaptive implementation decision control and autonomous Factory
  evolution.** A fourteen-Block program plans a
  near-zero-overhead unchanged path, inline correction of bad implementation
  decisions, selective isolated candidate comparison, exceptional supervised
  tracker amendment, configurable full autonomy, single-authority cutover, and
  shared operation for target repositories and Software Factory self-work. It
  then couples the accepted on-demand evolution workflow to maintained report
  and terminal checkpoints through deterministic eligibility, existing-owner
  candidate implementation, independent evaluation, policy-gated reversible
  adoption, outcome feedback, and recurrence suppression. Reports remain
  nominators rather than authority; the evolution helper never edits or
  promotes a skill. This is planning, not implemented functionality. Initial plan:
  `765c32bd15a52f8eb0f0bb48f07217d0851ebac5`; provenance-corrected successor:
  `851bc1aa5150eaa4de7fc5346c45abf892002a1f`; independently accepted frozen
  plan: `94c8118adca77b574b1e6ef5a1f2a5aad0aa9d91`, blob
  `9e6b6d1d03369c84ff9ca48c2df35dcac79e2f64`, SHA-256
  `426a7a60074c464640dfc3657b87bb082cdf7a2b4408c3245e2d5a29b02960fd`; tracker:
  [`docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md`](docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md).
- **Pre-implementation tracker-authoring supervision.** A five-Block program
  plans independent, repository-grounded challenge of capability selection,
  architecture/owner reuse, Block decomposition, acceptance evidence, and
  implementation readiness before implementation begins. This remains planned,
  not implemented. Planning commit:
  `a01417376b458325b6554ab6007d2a7d145a785d`; tracker:
  [`docs/software-factory-tracker-authoring-supervision-implementation-tracker.md`](docs/software-factory-tracker-authoring-supervision-implementation-tracker.md).

### Documentation

- **Changelog established.** Added this project-level capability history and
  the maintenance contract above. Run-specific reports and machine-readable
  evidence remain the precise underlying sources; this file is their durable
  human-oriented summary.

## 2026-08-08

### Implemented and demonstrated

- **Evidence-grounded Factory evolution MVP.** Software Factory can build a
  deterministic learning packet from explicit verified weekly `report.json`
  and canonical `events.jsonl` sources; validate bounded observations, lessons,
  counterexamples, meta-patterns, capability candidates, selection dimensions,
  and experiments; independently compare baseline and candidate behavior; and
  record `promote`, `advisory`, `revise`, or `reject`. The workflow is on-demand
  and derived: reports nominate hypotheses, canonical evidence adjudicates,
  the evolution command never edits skills or targets, and a disposition does
  not automatically adopt or deploy a candidate. Accepted tracker evidence:
  `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`; accepted implementation candidate:
  `363596ce10c4c3a39ead387bc9db493c12128c8b`; tracker:
  [`docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md`](docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md).
- **Target-product capability framing during tracker authoring.** New
  full-profile trackers reconstruct the direct product capability, protected
  behavior, architecture strategy, proportionality, tradeoffs, and uncertainty
  before consequential Block decomposition. The verifier rejects structural
  contradictions and preserves an inherited core-profile compatibility path.
  Accepted candidate: `c777c9c9b97787ad49d6dace328ca5b5041961b7`;
  acceptance evidence: `9e0062b8f76d6f2a0aba7636e81e17ab7e6bdeb8`.
- **Bounded product-capability review during Block execution.** Consequential
  Blocks compare a local path, bounded-general path, and available architectural
  owner; protect canonical behavior and composability; reject lower-power
  underreach and speculative generalization; and retain the routine fast path.
  Accepted candidate: `17a7571873cff82b4190db1ffe75216cac75937f`;
  acceptance evidence: `3bed4013d48f2e36418f4a0b50c0d657d9fcd424`.
- **Terminal capability reconciliation.** Outcome completion now validates a
  bounded semantic reconciliation of requested capability, protected behavior,
  architecture owner, tradeoffs, current behavior, operator-visible effects,
  exact evidence, source revision, and independent reviewer identity. A
  verified posture requires zero supported gaps; tests, commits, reports, and
  process records cannot substitute for current behavior. Accepted candidate:
  `363596ce10c4c3a39ead387bc9db493c12128c8b`; acceptance evidence:
  `4a33cd9344f0fbb1d1feaa6caac13521eb3237f3`.

### Corrected

- **Adaptive tracker provenance.** Corrected the planned adaptive-decision
  tracker so routed `codex_delegation` advice remains advisory rather than being
  represented as direct product authority. Direct requirements are bound to the
  eligible user thread and hash-bound repository/tracker sources. Successor:
  `851bc1aa5150eaa4de7fc5346c45abf892002a1f`; corrected tracker blob:
  `1e60d8312f77cd6880b3818fd8418e3087137fa3`.

## 2026-08-03 to 2026-08-04

### Implemented

- **Evidence-backed supervision reports.** Added deterministic weekly
  supervision metrics, bounded cognitive review, machine-readable report state,
  executive-readable Markdown/PDF projections, and report-density controls.
  Reports remain derived views rather than operational authority.
- **Observable outcome closure and terminal supervision.** Added explicit
  reconciliation of requested deliverables and current effects, terminal report
  evidence, lifecycle/shutdown proof, and Gmail ownership boundaries. Green
  tests or terminal process state alone no longer establish completion.

## 2026-08-01 to 2026-08-02

### Implemented

- **Autonomous continuation around bounded decisions.** Added dependency cuts,
  maximal safe-frontier continuation, bounded independent resolution attempts,
  fail-closed blocking gates, and automatic consumption of resolved handoffs so
  ordinary Block boundaries or preferences do not become human scheduling
  gates.
- **Independent supervision and corrective recovery hardening.** Added strict
  cross-thread action routing, role-refresh gates, exact mission provenance,
  producer-output preservation, stable test invocation envelopes, incident
  lifecycle reconciliation, and current-run correction before reusable skill
  maintenance.

## Earlier foundation

- **Three-skill Software Factory.** Established independently usable tracker
  authoring, bounded Block implementation, and independent tracker-run
  supervision skills with Git durability, canonical event/incident state,
  verification, correction, and reporting owners. Exact granular history begins
  with repository commit `c1ab52c` and remains available in Git.
