# Software Factory operations dashboard validation

Status: accepted local handoff. Block 31 product commit
`5a83a46b498ab636ac79c5c0c79c1003308b3b04` and evidence commit
`4e1fbdd037729e94f3ed0fd1948e083e30b5cf31` received independent exact-
revision acceptance with no material findings. This record remains evidence;
the tracker is completion authority.

## Runtime and lock identity

- Hardware: Apple M1, 16 GiB memory.
- OS: macOS 26.5.1 (25F80).
- Node.js 24.15.0; npm 11.12.1; Python 3.14.4.
- Codex CLI: `codex-cli 0.145.0`.
- Frontend lock SHA-256:
  `a6bf523de250dd03c719cd42ab7a9d704e6f16656138ac1d37a4af5485504ef7`.
- Python lock SHA-256:
  `4351a90ad2a3136c8fda2dbcd9520df16f43ba42a654f0f17023532a06b81035`.
- App Server compatibility artifact SHA-256:
  `8b53cd4e6b14fbe7bcfbaff766c1c4264d542614a5c95257e8a8458e24baf0e6`.
- Generated App Server contract: 273 files, semantic root
  `757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`.
- Consequential product-capability frame: 3,511 bytes, SHA-256
  `736124301d439cf6f143bb8013d53f085e9f3f4748df35451ef1bce5df0d8857`.

## Feature and source matrix

| Surface | Current behavior | Primary source/effect owner | Release posture |
|---|---|---|---|
| Factory Floor | Compact expandable implementation/supervisor rows, exact/partial count chips, attention, conclusions/outcomes, metrics/freshness, active-Block claims and disagreement | composed catalog, tracker/Git, supervision/report/metric, and App Server projections | working; current aggregate is partial because source families retain explicit limitations |
| Projects | Register/update/archive/unarchive discovery metadata; project work, tracker, report, source, and binding views | dashboard catalog for metadata; registered Git/project adapters for truth | working across three current local projects |
| Project/run detail | Current mission, predecessor isolation, topology, roles, automations, events, issues, conclusions, workflows, controls | maintained supervision policy/ledger, automation, tracker/Git, reports, App Server | working; current run honestly exposes an unassigned supervision project claim beside a bound task cwd claim |
| Trackers | Exact maintained-verifier total/status/dependencies, every active claim, evidence, diagnostics, Git posture, source links, semantic diff | tracker Markdown, maintained verifier, Git | working; read-only, no acceptance/editor path |
| Metrics | Per-run delivery/reliability/review/resource data, coverage, source table, accessible trend | maintained weekly metric owner and canonical records | working; six current contracts are mutually incompatible, so aggregate numeric totals are withheld rather than rendered as zero |
| Reports | Verified weekly/terminal/evolution inventory, safe Markdown/PDF/JSON/manifest access, comparison evidence | maintained report and Factory-evolution validators/manifests | working; six report, six terminal-workflow, and six evolution-workflow projections sampled |
| Tasks | Exact list/detail/turn/request state plus typed continue/steer/interrupt/approval/input definitions | version-gated Codex App Server | working and compatible; current sampled task is truthfully `notLoaded`, not relabeled active |
| Start work | Tracker author/review/revise/implement and supervision attach previews | named skills through Codex App Server, then canonical artifacts | supported when exact repository/tracker/task/authority gates pass |
| Supervision admin | Check/review/adjust/binding/pause/resume/report/evolution/succession/terminal workflows with owner semantic diffs | supervision, task, automation, report, evolution, lifecycle owners | 25 operation types supported; exact-source ineligibility disables individual controls |
| Admin health | Runtime, catalog, App Server version/schema/features/reconnect, operation registry, source failure reasons | each adapter and local runtime | working |

Intentionally unavailable in the sampled runtime:

- `factory.supervision-repair-automation-binding`: no maintained versioned
  target-query provider is configured; unrelated manifests are not scanned.
- `factory.tracker-authoring-supervision`: its separate implementation program
  is not accepted.

Intentionally out of scope: remote binding/hosting, multi-user administration,
arbitrary Git/shell/App Server access, general prompts, model/spend changes,
tracker acceptance, direct policy/automation/ledger/report writes, Factory-
evolution adoption, and a second operational store.

## Current three-project source packet

Snapshot window: `2026-08-12T14:53:26Z`–`2026-08-12T14:53:37Z`.

Registered catalog revision:
`b144dfa8547ac23fb03ed5321867945e6217027e74ce5ebd170684dd266446e5`.

| Project | Canonical root | Git source | Discovered trackers | Mutation performed |
|---|---|---:|---:|---|
| Software Factory | `/Users/ethanstillman/code/software_factory` | available | 4 | catalog metadata was already registered |
| Graphy | `/Users/ethanstillman/code/celltonomy/graphy` | available | 13 | registered catalog metadata only |
| Patent Studio | `/Users/ethanstillman/code/celltonomy/patent-studio` | available | 14 | registered catalog metadata only |

No registered repository file or Git state was changed by catalog registration.

| API | Owner identity | Owner revision | Envelope fingerprint | Coverage | Sample count/posture |
|---|---|---|---|---|---|
| `/api/v1/projects` | `software-factory-dashboard/project-catalog` | `b144dfa8547ac23fb03ed5321867945e6217027e74ce5ebd170684dd266446e5` | `ff60b2c69b75b56ab7a9e36b661ca58d5d3ff025ac516ac531e5fb6174dd8287` | partial | 3 projects |
| `/api/v1/trackers` | `software-factory-dashboard/trackers` | `f0f5f18de4ebd52682df6634cc1bcf3121e18a67a72d7f300d9fae45ce33995c` | `25cce83ce2598bd9a64bd6989ad95210e8b70c8cc4d756f41dcb796904b2d1f0` | partial | 31 trackers |
| `/api/v1/runs` | `software-factory-dashboard/runs` | `29545e734de461ed216cdfe766bc76cbf90baeca4df4562240f84cb79210124d` | `139d2f416a16ae3aac33fb331b4d7dc41c067561aadde2b40b130297b2ba7a28` | partial | 6 runs |
| `/api/v1/reports` | `software-factory-dashboard/reports` | `50303e796acd372761b89c2e47f38fd706d90071003491e00874cbddc9a537dc` | `8e391912a3cf65419c5685db595c8e655f9a4e055a5864732a7a74348775a7cb` | partial | 6 report, 6 terminal, 6 evolution projections |
| `/api/v1/metrics` | `software-factory-dashboard/metrics` | `f276c65392d94892bcd843339e042ad70f48f89afd3566270a7e5a748dcbdfb5` | `ef6048e1e4e4fb8510cf2ec752d508236f13433f81acbe4c6d4dfb757760f646` | partial | 6 available but incompatible run contracts; no aggregate numeric value |
| `/api/v1/task-integration` | `software-factory-dashboard/task-integration` | `f463e86b1e0bea9ba9cf40abc5eaf93a2e419f4a37bb4e0eec8631ff669ee0e0` | `55f180bbd2b8f7f42240feb86dd8b424d864c0d56ed635fef0432822854e9ca4` | complete | available and protocol-compatible |
| `/api/v1/operations` | `software-factory-dashboard/operations` | `aaf0b10757ac726a6114627bbf1511d42dc9d1fbac9c7b0069ffc647af452225` | `1f42170302bf6651a9363521e5785c7fb57ba724333727c9e79af6112eea1f43` | partial | 27 definitions: 25 supported, 2 unavailable |
| `/api/v1/factory-floor` | `software-factory-dashboard/factory-floor` | `38669c9c98f2228208ec278615c45246aca1804a6d0de627bd87f1883ceab0c1` | `0b958533c94df756de67a91852f4b367b77d80ed36bb6bd9f1752fed6ff696a4` | partial | 7 untruncated rows; 3 active implementations; 6 supervisor groups; 18 attention items |

Direct source checks:

- Dashboard tracker ID
  `05273c2320e64d0547789dad410b526ccd07687e2ae2f3c121b89263981363e5`
  projects 32 Blocks, 31 accepted and Block 31 active. Its projected content
  SHA-256 at the source-packet snapshot equals the direct file hash
  `53775f8f0cc8094643e644f0105737ae9277be56949b99d4776c778896110191`;
  the maintained full verifier independently returns 32 Blocks, zero errors,
  and zero warnings. After appending this ordered pre-broad evidence, the exact
  current tracker SHA-256 is
  `78cc3efc22b705cca697826bd94928bf4c8a05ec25c83ea4f0c7f61eb70b1bcd`;
  the post-commit source packet must reproject that successor before the broad
  run.
- Current dashboard run source is
  `supervise-tracker-runs/scripts/supervision_log.py`, owner revision
  `10f89443198be2defd8f45169193212f9740743ac031b6c7d5183b14a863cc54`.
  The API event head equals canonical `EVT-000341` record SHA-256
  `a7221298ef750ddb95a08b1c53083e728581bd94738e6a5ae7158e6aa4ccc81b`;
  its policy head equals the `policy.json` embedded SHA-256
  `6157542ae1d1100f11c1286a62aad064a311481379c93bcba299c84a8a28fd2b`.
- The sampled Codex task detail has exact task ID
  `019fe547-e054-7ca0-9940-ec4aa146df78`, cwd
  `/Users/ethanstillman/code/software_factory`, task project binding
  `software-factory`, 10 returned turns without turn truncation, and current
  App Server status `notLoaded`. The supervision projection separately retains
  its unassigned project-binding anomaly rather than merging these claims.

## Disposable operation proof

The existing integration harness creates a temporary Git repository, isolated
catalog, isolated supervision root, fake schema-compatible App Server, and
in-memory task owner. It performs real HTTP preview/execute/postcondition cycles
without paid model work or writes to a user project. The focused Block 31 run
passed 6/6 in 11.081 seconds with `ResourceWarning` fatal:

- closed registry and exact tracker-author prompt;
- read-only tracker review, one bounded implementation start, duplicate-owner
  rejection, and unchanged tracker status;
- task continue distinct from steer and lifecycle;
- wrong-cwd and partial supervision attach fail closed;
- one exact role-task binding through the maintained policy/task/route owners;
- routed steer, interrupt, approval, and input responses with exact owner
  records and explicit no-pause/no-stop/no-acceptance postconditions.

## Beautiful UI source adaptation

The implementation retains the supplied component source provenance and removes
demo semantics:

| Supplied file | Frozen supplied-source SHA-256 | Adapted production file | Removed/retained boundary |
|---|---|---|---|
| `TaskRows.tsx` | `665e31820b041600662fcffff044d6a4994ecd18059d5e8ef1026251bf996b0e` | `dashboard/web/src/components/factory-floor-patterns.tsx` | removed demo data/timers/retry/autonomous transitions; retained native disclosure grammar |
| `FilterTable.tsx` | `4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4` | `dashboard/web/src/components/factory-floor-patterns.tsx` | removed sample business rows; retained keyboard count chips with exact coverage labels |
| `DiffTable.tsx` | `aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2` | `tracker-semantic-diff.tsx`, `operation-semantic-diff.tsx` | removed demo stages/timers/menus; retained explicit semantic rows and non-color cues |

Gallery Sidebar, Chat, Prompt Bar, recommendations, fine-tune, selection actions,
and cosmetic loading components were not adopted. No component is labeled
“Thinking” or “Reasoning,” and no chain-of-thought view exists.

## Representative corpus measurements

Measurement command:

```bash
SOFTWARE_FACTORY_DASHBOARD_URL=http://127.0.0.1:8787 \
  npm --prefix dashboard/web exec -- playwright test \
  e2e/release-performance.spec.ts --workers=1
```

The run passed 6/6 in 22.0 seconds. Timings are observations on the hardware
above, not universal service-level claims.

| Corpus/view | Interactive | First disclosure/page | Render bound |
|---|---:|---:|---:|
| Current live floor, desktop | 2,562.9 ms | 114.4 ms | 7 rows |
| Current live floor, tablet | 4,980.3 ms | 90.0 ms | 7 rows |
| Current live floor, mobile | 4,474.8 ms | 80.9 ms | 7 rows |
| Deterministic 2× history, desktop | 329.3 ms | 117.9 ms | 50 event rows |
| Deterministic 2× history, tablet | 362.5 ms | 89.2 ms | 50 event rows |
| Deterministic 2× history, mobile | 343.0 ms | 108.6 ms | 50 event rows |

The 2× fixture expanded 341 source events to 682 projected events in a
1,815,513-byte typed envelope with unique synthetic record IDs. Only the current
50-row page entered the event DOM; Older/Newer paging worked and no viewport had
document-level horizontal overflow. Product bounds remain 80 Factory Floor
rows, 50 run-event rows per page, 200 semantic diff rows, 500 tracker map rows,
1,000 metric history rows, and 512 ephemeral App Server events.

## Focused correction proof before the broad matrix

- Current backend process was restarted on port 8787 after the Block 30 schema
  addition; 12 previously failing workflow browser cases then passed unchanged.
- The live drill-down test now derives `Issue follow-up` availability from the
  exact current open-incident projection instead of assuming no incident; the
  focused desktop case passed 1/1.
- Mobile active navigation uses the theme text token on the retained green
  active treatment; the semantic tracker/Axe case passed 3/3 across desktop,
  tablet, and mobile.
- Current and deterministic 2× performance/bounds proof passed 6/6.
- No live task, supervision, report, evolution, lifecycle, request-stop, or
  shutdown operation was previewed or executed for this validation record.

## Pre-broad authority and Stop audit

Completed at `2026-08-12T14:58:11Z`, before the final broad matrix. `Complete`
means the current implementation and focused/accepted evidence expose the named
owner, recheck, and postcondition. `N/A—unavailable` means the current registry
fails closed and no action can be requested.

| Likely-mutating boundary | Status | Pre-broad evidence and invariant |
|---|---|---|
| Catalog registration/update/archive | Complete | exact canonical Git root, optimistic catalog fingerprint, same-origin nonce, owner-only atomic file; only discovery metadata changes and archive never touches a repository or stops work |
| HTTP mutation boundary | Complete | loopback Host/origin/nonce, bounded JSON, traversal/backslash/symlink rejection, closed endpoint and operation schemas |
| Operation preview/execute | Complete | exact target/input/source fingerprint, expiry, one-shot token, route gate where required, requested/applied separation, canonical postcondition re-read, no automatic retry or rollback |
| App Server child/restart | Complete | exact CLI/schema/handshake and generation-bound requests/events/callbacks; restart is adapter-only and stale generations cannot affect the replacement child |
| Task continue | Complete | current exact task and fresh source fingerprint; creates one bounded turn, not steer/pause/acceptance/outcome |
| Task steer | Complete | exact active turn plus current maintained route-gate result; does not create a new task or lifecycle record |
| Task interrupt | Complete | exact active turn; explicit verification retains `supervision_paused=false`, `mission_stopped=false`, and `work_accepted=false` |
| Approval/input response | Complete | exact pending request/item/task/turn fingerprint and typed response; removed from pending only after App Server owner acceptance |
| Tracker author/review/revise/implement | Complete | exact project/tracker/Git/content/profile/Block range and single-writer checks; maintained skill prompt and task owner; tracker Markdown status remains unchanged until its own writer/evidence path |
| Supervision attach | Complete | exact implementation task/tracker/range/mission marker plus full configured role/automation/cadence postcondition; partial setup remains unattached |
| Mechanical check and semantic reviews | Complete | watcher versus reviewer roles, exact current record/incident, route purpose, newer canonical record, and no conversion of mechanical activity into a conclusion |
| Policy adjustment | Complete | owner-supplied bounded field diff, independent review, one next policy history record, and separately verified affected automation schedules; no dashboard TOML/JSON write |
| Mission-binding repair | Complete | missing-binding-only direct-source review path; exact full bytes/envelope/client, target/tracker/project/current mission identity, independent reviewer/fix separation, and canonical bind/policy postcondition |
| Role-task binding repair | Complete | same-current-mission candidate history, complete task content/model/project identity, three-way target/reviewer/fix separation, route gate, and dual task/policy postcondition |
| Automation-binding repair | N/A—unavailable | current registry reports no versioned target-query provider and refuses to scan unrelated manifests; therefore no preview or mutation path exists |
| Semantic pause | Complete | current paused lifecycle, exact sent notification, every configured automation represented, ACTIVE-to-PAUSED timestamps after notification, already-paused byte/time preservation, no target interrupt |
| Semantic resume | Complete | accepted canonical resume lifecycle owner plus every represented automation ACTIVE/reconciled/exact; unavailable or partial coverage renders Resume incomplete, never Running |
| Same-target mission succession | Complete | exact current direct source plus independent review, closed heads, preserved task/project/tracker/policy history/automations, pending first-work activation, no successor task creation |
| Successor-task continuity | Complete | evidence-tight direct task-creation authority, canonical transition head/fingerprint, exact phase owner, task/group/route/ack/first-work currentness, source remains active until work-start proof |
| Weekly reporting | Complete | maintained prepare/review/finalize/verify stages, exact retained-review reuse, separate delivery, no review regeneration on late-stage recovery |
| Factory evolution | Complete | verified report/event packet, separate proposer/external implementer/evaluator, revision-bound comparison and disposition, no implementation/adoption/deployment/outcome authority |
| Terminal reporting | Complete | reconciled completion, exact report set, retained review, verified delta/full artifacts, one Gmail/read-back delivery owner, different historical report-set receipts do not block the current set |
| Terminal request-stop/shutdown | Complete | lifecycle/delivery/successor/open-incident/open-decision/event-head/policy/automation gates; exact owner states are re-read under the append lock; helper uses `uv run --python 3.14 python`; no target interrupt and no live shutdown in validation |
| Predecessor mission rendering | Complete | current task/topology/role/automation/report/metric/control state suppressed; only mission-scoped records and historical hashes/times remain |
| Tracker/operation semantic diffs | Complete | owner/Git supplied, bounded and read-only; explicit text/icon change semantics and source/currentness links; never an editor, confirmation, or acceptance path |
| Partial/unavailable truth | Complete | source-local failure and incompatible metric contracts remain partial/unavailable; no zero/green/complete substitution and no exact count from truncated rows |
| Block 31 Stop | Complete | only local catalog metadata, code/docs/tests, process restart, read-only source checks, and isolated fake-owner operations occurred; no live task, supervision, report, evolution, lifecycle, request-stop, shutdown, remote hosting, or multi-user capability was executed or added |

This audit is the release boundary for the single broad run. Later corrections
may receive focused and affected mapped proof only; they do not authorize a
second broad replay.

## Final matrix and independent review

The pre-broad package was committed and pushed as
`4c72dda49e1597c3e9a1c0d5cdd4015690e291d7` before the broad matrix began.
The single broad matrix then produced:

| Gate | Result |
|---|---|
| Python server/integration/security/owner suite | 142/142 passed in 60.737 seconds with `ResourceWarning` fatal |
| Python lint and compilation | Ruff and `compileall` passed |
| Frontend type/unit/component suite | TypeScript passed; 20 files and 116/116 Vitest tests passed in 19.11 seconds |
| Production frontend | Vite transformed 2,590 modules and built successfully |
| Responsive browser matrix | 88/90 passed in 7.7 minutes; the only two failures were the same dark-theme report-link distinction defect at tablet and mobile |
| Tracker/mechanical checks | full profile returned 32 Blocks and zero diagnostics; verifier tests 30/30; 25 relative links resolved; diff check and object checks passed |

One preliminary standalone TypeScript invocation resolved the repository-root
`tsconfig.json` and exited `TS6053`; it did not reach the product. The
package-owned `npm --prefix dashboard/web run check -- --maxWorkers=1` command
then ran the intended compiler and complete unit suite successfully.

The browser finding was corrected only in the affected report-table link style:
links now retain a visible underline in addition to color. The corrected
production build passed, and the exact affected Axe/report-history case passed
3/3 at desktop, tablet, and mobile in 1.2 minutes. The complete browser matrix
was not replayed. The corrected product commit is
`5a83a46b498ab636ac79c5c0c79c1003308b3b04`, tree
`1891ac53e3905a77be7f83aea3de7dace1228e19`, with exact remote divergence
`0/0` at freeze.

Final currentness smoke after correction: loopback health was `ok`; every
health integration was `available`; `/admin` returned HTTP 200; Codex App
Server remained `available` and `compatible` at 273 schemas and semantic root
`757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`.
No live consequential operation was previewed or executed.

The independent implement-tracker-blocks audit ACCEPTED evidence commit
`4e1fbdd037729e94f3ed0fd1948e083e30b5cf31`, tree
`6a8fbc30329051e1753caaa7be32503c06d0a068`, and product commit
`5a83a46b498ab636ac79c5c0c79c1003308b3b04`, tree
`1891ac53e3905a77be7f83aea3de7dace1228e19`, with no material findings. The
review independently confirmed the ordered evidence chain, clean install and
build, all named local routes and APIs, three registered projects, three active
implementations, six supervisor groups, 18 attention items, current Block 31,
explicit partial/missing-binding truth, sparse UI, Beautiful UI provenance,
maintained-owner boundaries, predecessor isolation, bounds, documentation,
remote `0/0`, and the terminal Stop. Its interrupted optional browser rerun was
not counted. No live consequential action or primary-source mutation occurred.
