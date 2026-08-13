# Software Factory Operations Dashboard Contract

- Contract status: `Block 0 frozen candidate`
- Initial source observation: `2026-08-09T08:12:20Z`
- Authority/live-sample refresh: `2026-08-09T08:22:08Z`, through
  `EVT-000030`
- Repository source revision:
  `08b4f983749b6018eb7169f3a509ea2d43f5c6ed`
- Tracker authoring revision:
  `2b73de1f5b706eab4de26785a7489cf52fe586c4`
- Repository branch: `codex/evolution-mvp`
- Tracker Git blob: `7c9d758bb535687e6a85091b083f4fa2fbb6ddce`
- Tracker SHA-256: `dab97d29851453058955cd7b3545ebd8bf96945ee686ce72706e33d18159eed7`
- Tracker-level capability-frame SHA-256:
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`
- Baseline posture: this document freezes owner eligibility for implementation;
  it does not claim that the dashboard runtime or any dashboard control exists.

## 1. Activation and observable-outcome contract

Implementation authority is direct-user item 44 in this target task, which
explicitly invoked `implement-tracker-blocks` for the implementation tracker,
bound to mission root
`45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`.
Routed item 79 from Codex source task
`019fe54b-bbe7-78c3-869d-323c19938bdf` resumed that already-authorized mission,
selected tracker commit `2b73de1` and Block 0, and required dependency-ordered
continuation. It is resume/start-routing evidence only, not implementation or
product authority. This provenance distinction was detected by supervision
incident `INC-20260809-081917-D3A17C`, event `EVT-000028`, and recorded as
corrected in `EVT-000030`.

Current supervised-start evidence is independently visible in target
`019fe547-e054-7ca0-9940-ec4aa146df78`:

- policy version `4`, policy SHA-256
  `02c573313b401bd613f794ad9d4d6349898f76c12165b16d87559827c12be6d5`;
- incident `INC-20260809-080549-6AD6C5` and event `EVT-000022`, whose required
  target action is to resume at Block 0 and whose `user_action_required` is
  `no`; and
- active mission root
  `45549ee8a796601b16c2ce01b50d31b540390434a959cc83418e351ddaf3ac5c`,
  derived from the direct dashboard implementation request. No successor
  mission is required for this implementation start.

The primary operator-visible outcome remains one trustworthy local control room
for current and historical Software Factory work across multiple projects. It
is complete only when the final Block proves the named dashboard views and at
least one owner-gated consequence against current sources in a real browser.

Required ordinary effects are: source discovery; bounded local configuration;
deterministic projections; a responsive built frontend; version-gated Codex
task integration; owner-mediated operations; tests and browser evidence;
documentation; a reproducible local start command; and Git durability.

Reserved or excluded effects are: remote hosting, multi-user identity or
permissions, arbitrary shell/filesystem/App Server access, direct writes to
tracker/supervision/report/automation owners, Gmail message operations,
unimplemented autonomous evolution, release, merge, and deployment.

### Product-capability selection for Block 0

- Trigger: Block 0 is `consequential`.
- Frame identity: dashboard tracker, `Target-product capability frame`, SHA-256
  `26664146d46f0880752bad3252c562232fa8d6a2a19adb7804908d2ee1b562ec`.
- Smallest local path: this repository-owned contract document. It is necessary
  and sufficient for the Block's frozen baseline.
- Bounded-general path: a new shared capability registry or schema. Rejected;
  no current consumer beyond this dashboard needs another registry.
- Existing architectural owner: the three skills, tracker verifier,
  supervision/report helpers, Git, Codex App Server, and Codex automation tool.
  Selected for each underlying behavior instead of duplicating it locally.
- Selected level: the local contract records exact existing owners and
  compatibility roots. It adds no runtime, service, database, or canonical
  state.
- Capability preserved: later Blocks can provide broad observation and narrow
  real control without weakening canonical writers, direct mission authority,
  or process-versus-outcome truth.
- Accepted tradeoff: explicit source and disabled-reason detail costs more UI
  complexity than a synthetic score, but makes decisions trustworthy.
- Current uncertainty: tracker-to-run association is not always canonical;
  App Server is versioned; live targets may lack optional artifacts; and
  several advanced programs remain planned rather than implemented.

## 2. Authority and precedence

For each field, the narrow canonical owner wins. No aggregate row, report,
task state, or UI label can override it.

1. Current direct user/system/repository authority governs product scope and
   reserved actions.
2. Tracker Markdown at an exact Git revision governs declared Blocks, status
   text, dependencies, acceptance, and completion evidence.
3. Git governs file identity, revision, currentness, and durability.
4. Codex App Server governs task/thread, turn, item, approval, and input state.
5. `supervision_log.py` and validated supervision files govern policy, mission,
   event, incident, decision, transition, conclusion, and lifecycle state.
6. Codex automation tooling governs automation mutation; automation TOML is a
   read-only projection.
7. Weekly, terminal, and Factory-evolution helpers govern their derived
   artifacts and verification. Reports nominate or summarize; they do not
   become operational or completion authority.
8. The dashboard catalog governs only project discovery metadata and archive
   presentation state.
9. The dashboard composes these sources. It owns no copied operational truth.

Current state is scoped to the active mission root. A predecessor mission's
events, conclusions, metrics, and completion remain historical and cannot
establish successor current state.

## 3. Terminology and truth labels

| Term | Exact dashboard meaning |
|---|---|
| Project | One operator-registered local Git repository root plus dashboard-owned discovery metadata. |
| Task | A Codex App Server thread and its live session/turn state. The UI may say task; protocol fields retain `threadId`. |
| Target | The exact task/thread or other supported subject named by one supervision policy. |
| Run | One mission-scoped segment of canonical supervision policy/history/events for a target; not merely a process lifetime. |
| Tracker | One Markdown implementation contract at an exact file hash and Git revision, verified with its declared full or inherited core profile. |
| Block | One numbered, bounded tracker unit with its own status, dependencies, acceptance, evidence, and Stop. |
| Checkpoint | An evidence-bound intermediate point inside a run or Block; not terminality by itself. |
| Lifecycle | Canonical supervision state and transitions, distinct from Codex turn/task status. |
| Accepted | The Block's exact candidate passed required proof and post-Block audit. It is not automatically the final product outcome. |
| Completed with open items | Terminal only when every retained item is current and compatible with the primary outcome because it is reserved, external, optional, or expressly excluded. |
| Stale | A source, fingerprint, revision, conclusion, or cadence no longer matches the current identity or freshness contract. |
| Unavailable | A known integration, owner, authority, prerequisite, or compatible version is absent; the reason and revisit trigger are known. |
| Unknown | The source could not be observed or classified. Unknown is never rendered as zero, healthy, complete, or inactive. |

Tracker summary status, Block statuses, Git currentness, execution state, and
supervision lifecycle are separate fields. When they disagree, the dashboard
shows the disagreement and each source instead of choosing an attractive
single label.

Traffic-light posture is a derived navigation aid only:

- `red — action required`: current critical/high issue, pending required input
  or approval, broken required integrity, empty safe frontier proven by gate,
  or prohibited/incomplete stop or successor;
- `amber — attention`: warning, stale/late check, partial integration,
  nonblocking decision/transition, or degraded/mismatched binding;
- `green — on track`: required sources are fresh, bindings valid, work is
  progressing or legitimately idle, and no red/amber rule applies; and
- neutral named states: paused, accepted/completed history, unmonitored,
  unavailable, and unknown.

Green is never completion proof.

## 4. Frozen source inventory

### Repository and maintained owners

The initial working tree was clean and matched
`origin/codex/evolution-mvp` at tracker revision `2b73de1`. During Block 0,
the maintained supervision owner settled at source revision `08b4f98`; every
named source outside this contract's focused remediation is clean at that
revision. Push currentness is recorded separately from source validity.

| Source | File SHA-256 | Last owning Git revision | Treatment |
|---|---|---|---|
| `README.md` | `44c7f895a33b9afc42075edbfe39cdc0f0940dbb6432f9ef9fe44d0478c35346` | `e2b7064a7a226409518a883ecec88661469309b8` | Product/operating model. |
| `CHANGELOG.md` | `5c091ea8a4e169217ad26ceeb6cae9ff2a2fdedcf4cf2a1baf24edbe2acea5b5` | `2b73de1f5b706eab4de26785a7489cf52fe586c4` | Capability posture; never overrides code/current behavior. |
| `author-implementation-trackers/SKILL.md` | `8154687040df4afbae6dc187cd373761c784609b4f9dbec00eb3a80ce21f3ac3` | `d57f8a64f932655acc4373fe947a2cca36269d5c` | Tracker author/reviewer owner. |
| `author-implementation-trackers/scripts/verify_tracker.py` | `f0f5f18de4ebd52682df6634cc1bcf3121e18a67a72d7f300d9fae45ce33995c` | `c777c9c9b97787ad49d6dace328ca5b5041961b7` | Full/core structural diagnostics owner. |
| `implement-tracker-blocks/SKILL.md` | `f8bebb5b3ade941c291216929b7b1124785c968fda79167c862aa48301490b05` | `e2b7064a7a226409518a883ecec88661469309b8` | Block/range execution owner. |
| `supervise-tracker-runs/SKILL.md` | `a8d4b1518288c9aa5956ed192b6d1830c5326454566a887ed2ef2d3e690c0eb9` | `08b4f983749b6018eb7169f3a509ea2d43f5c6ed` | Supervision operating owner, including the first-work activation obligation. |
| `supervise-tracker-runs/references/supervision-policy.md` | `f393c2990670f67a42bbe74ff490096cbe4e3fd7a44ddd379f0d6ed50d79f2cf` | `08b4f983749b6018eb7169f3a509ea2d43f5c6ed` | Roles, routes, lifecycle, reporting, mission, and activation contract. |
| `supervise-tracker-runs/scripts/supervision_log.py` | `ad752ad5839aa00cfa10a0979eb89236710e9596c45f54866017637c5bbfc191` | `08b4f983749b6018eb7169f3a509ea2d43f5c6ed` | Sole public supervision filesystem writer/validator; succession creates structural activation records, but current work-start closure is not evidence-tight. |
| `supervise-tracker-runs/scripts/weekly_report.py` | `e469bebe4fe46aa3c0ff47a7273151441bcac30f49984bdbaeaff3d67c2e3d65` | `75c9c27383efd1f245ab413e22de03b2f72ae4d0` | Weekly report computation/render/verify owner. |
| `supervise-tracker-runs/scripts/terminal_report.py` | `800c2ff04bc3dcefaf124aa57d37ad85b42b5732db6825b8225cbf11a437c138` | `ee4302d450073ccefa54cd0fb41a764716f56951` | Terminal packet/report/manifest owner. |
| `supervise-tracker-runs/scripts/factory_evolution.py` | `c731ed0d03424f9e32d7689038affd8005b8f8f4a9ba97290e204efcf3cdf8b6` | `d773307b4d45f028d50a55f2a2e15aa7d8b5c7a8` | Derived evolution artifact validator; no implementation/adoption writes. |
| `supervise-tracker-runs/references/factory-evolution-contract.md` | `57d25b4f6871262adb6d84be753d46815e39c8133557115882b03d0d5c6a46ac` | `d773307b4d45f028d50a55f2a2e15aa7d8b5c7a8` | Evolution authority/stage boundary. |
| `supervise-tracker-runs/references/terminal-capability-reconciliation.md` | `fbdbdc16592ee397771276c63f582fbcbb187e338fcd1abb1e3d4cb47a97e4ba` | `d773307b4d45f028d50a55f2a2e15aa7d8b5c7a8` | Observable capability closure contract. |

### Current tracker inventory

| Tracker | SHA-256 | Profile/result | Declared/live posture |
|---|---|---|---|
| Adaptive implementation decision control | `426a7a60074c464640dfc3657b87bb082cdf7a2b4408c3245e2d5a29b02960fd` | full; 14 Blocks; 0 errors/warnings | `planning`; controls remain planned/unavailable. |
| Learning and capability evolution MVP | `ecc7b31ebd7bd7bc825746dded4059be2ddcc56377f4a702e1ab7781d09e07c6` | inherited core; 7 Blocks; 0 core errors/warnings | Header says `in-progress`, while all Block rows/evidence are `accepted` and code/changelog show implementation. Preserve this source conflict as attention. |
| Operations dashboard | `dab97d29851453058955cd7b3545ebd8bf96945ee686ce72706e33d18159eed7` | full; 26 Blocks; 0 errors/warnings | `planning` at baseline; this run begins Block 0. |
| Tracker-authoring supervision | `dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424` | inherited core; 5 Blocks; 0 core errors/warnings | `planning`; dedicated profile is unavailable. |

Running the two inherited trackers under the full profile produces expected
missing-frame/delta diagnostics. The dashboard must select the maintained
profile and may display the full-profile incompatibility as an explanation, not
as corruption or implementation failure.

### Reference frontend and local HTTP pattern

Reference Codex task `019fc4d5-2791-7823-997e-e7a38163ef2a` is the maintained
Patent Review Workspace task. Its package sources are clean at task worktree
commit `f924555752cb0efc4acde86cf3d515782939ce05`:

- `web/package.json` SHA-256
  `15884b92e78376186ee02cd241fbe5b4606520efa50781b507491d1dd2870afc`;
- `web/package-lock.json` SHA-256
  `f04f4d6d3e56aaf70cb35c61b8e0b21ddec9a94daac83b8cbe6851d0f67a0742`.

Exact locked stack to adapt in Block 1:

| Package | Version |
|---|---:|
| React / React DOM | `19.2.7` |
| React Router | `8.2.0` |
| TanStack Query | `5.101.2` |
| Jotai | `2.20.2` |
| Zod | `4.4.3` |
| Tailwind CSS / Vite plugin | `4.3.3` |
| Recharts | `3.9.2` |
| TypeScript | `7.0.2` |
| Vite | `8.1.5` |
| Vitest | `4.1.10` |
| Playwright | `1.61.1` |
| jsdom | `29.1.1` |

Radix primitives, Lucide, CVA, `clsx`, `tailwind-merge`, Testing Library, and
`jest-axe`/axe coverage are part of the reference family. Patent-specific
forms, XYFlow, voice behavior, content models, and layout decisions are not
adopted merely because the reference task uses them.

The narrow HTTP pattern comes from three selected tracked files that are
unchanged from Patent Studio main-checkout revision
`640b80f1400fb1a2af0a5971052065812e8cf9c2`. The rest of that checkout is
actively dirty and is neither inspected nor adopted by this contract:

| Source | SHA-256 | Reused principle |
|---|---|---|
| `src/patent_studio/monitor_api/server.py` | `16c2626ceb981113c6e97351c4e284015e2510d1886b49cb143ed118bfa9c33c` | `ThreadingHTTPServer`, bounded bodies, loopback Host/origin checks, security headers, quiet/testable shutdown. |
| `src/patent_studio/monitor_api/web.py` | `d0950cfce29fda364a40e6c89d499db2d6b98ad8bd6cd7c87034abfbbf6a6325` | Built assets, SPA fallback, traversal rejection, CSP, immutable hashed assets/no-store index. |
| `schemas/monitor-api-v1.schema.json` | `0b1505366da85ef8ed706c8c90a6fa53caf901bf3714dfa793f7c31e89cec794` | Reference schema discipline only; dashboard defines its own bounded API. |

Do not copy Patent Studio's domain routers or turn this pattern into a second
backend framework.

### Codex App Server compatibility

- Installed CLI: `codex-cli 0.145.0` at the observed local Node installation.
- Local default transport: `stdio://`.
- Stable schema generation command:
  `codex app-server generate-json-schema --out <temporary-directory>`.
- Generated stable bundle: 273 JSON files; semantic manifest SHA-256
  `757aa191b6d452c6e6d05f6c1f1cb093b9f673da2d185a29ee8d5d96feae67a8`.
- No `--experimental` fields were included.
- Official contract observed 2026-08-09:
  `https://learn.chatgpt.com/docs/app-server`.

The official protocol requires one `initialize`/`initialized` handshake before
other requests; then `thread/start` or `thread/resume`, `turn/start`, streamed
thread/turn/item events, server-initiated approvals/input, and
`turn/completed`. Local generated schemas, not prose recollection, are the
runtime compatibility authority. Experimental fields remain unavailable unless
a later explicit compatibility decision enables them.

The bundle root is reproducible from the generated directory with this exact
semantic manifest. `jq 1.8.1 -S -c` recursively sorts object keys before each
file is hashed, avoiding the generated combined schema's nondeterministic
definition order. File paths are relative, slash-separated paths emitted by
`find`; `LC_ALL=C` defines path ordering; each manifest line is lowercase
semantic SHA-256, two ASCII spaces, relative path, and LF; the final SHA-256
covers all 273 lines:

```sh
(
  cd "$SCHEMA_DIRECTORY"
  find . -type f -name '*.json' -print \
    | LC_ALL=C sort \
    | while IFS= read -r source_file; do
        semantic_sha="$(jq -S -c . "$source_file" \
          | shasum -a 256 | cut -d ' ' -f 1)"
        printf '%s  %s\n' "$semantic_sha" "${source_file#./}"
      done
) | shasum -a 256
```

The root matched across the frozen generation and one fresh 0.145.0 generation;
both contained 273 files. Observed toolchain only; Block 1 may refresh within
its contract: Python `3.14.4`, uv `0.11.9`, Node `24.15.0`, npm `11.12.1`, Git
`2.54.0`, jq `1.8.1`.

### Content-minimized live schema samples

No live artifacts are copied into the repository.

| Family | Exact sample/currentness | Observed contract |
|---|---|---|
| Supervision policy | target `019fe547-e054-7ca0-9940-ec4aa146df78`; file SHA-256 `05ffa0c3671c790294adac9c5a582834644d0ffd3e1956929a9870a41ef81003`; validated status policy SHA-256 `02c573…12be6d5` | Schema version, mission, roles, routes, schedules, reports, permissions, lifecycle/outcome contracts. |
| Supervision events | same target; as-of sample through `EVT-000030` at `2026-08-09T08:22:08Z`; SHA-256 `af5f70d81a0398682e3a1bf1ec168c146be8386b26a5882dc1bc7ed18b173e77` over the first 30 LF-terminated JSONL records | Append-only record/hash chain with target, mission/policy, fingerprint, checkpoint, issue/action/conclusion fields. Reproduce with `head -n 30 events.jsonl \| shasum -a 256`; later appended records do not stale this bounded schema sample. |
| Policy history | same target; SHA-256 `3697358bfcd449aa3cbb4dc5ef7b013b98f72dd50d59ecb9de453aefbbe17b6b` | Versioned preserved policy/mission history. |
| Automation projection | `tracker-watcher-sf-dashboard-plan`; TOML SHA-256 `1749080bbcdb5060b7d84a1c219d45328351eb6b35d23d8b03b5c365f2d425e5` | Keys: version, id, kind, name, prompt, status, rrule, target thread, created/updated time. Values stay owner-private until needed. |
| Verified weekly report | report `weekly-20260801T001853Z-20260803T234400Z-62f881d083b0`; manifest file SHA-256 `500ea0737d9b92ca0aaad2b0db8e3fb1efd4893e8b689773aec531188abc1c8d`; verified manifest root `8046f7ae7223f19c348c9e4205375208bfcf4944905183273272b160c2a9a227` | Verification returned `valid: true`, eight PDF pages, exact report/review/source/PDF roots. |
| Terminal report | no live manifest found in the bounded sample | Reader/workflow owner exists; current artifact state is `unavailable`, never zero or complete. |
| Factory evolution | no live manifest found in the bounded sample | Derived workflow owner exists; current artifact state is `unavailable`; automatic/adaptive adoption remains planned. |

Dashboard tests can generate valid and invalid tracker, supervision, App Server,
and report fixtures deterministically from maintained schemas. Block 0 therefore
adds no copied live fixtures.

## 5. Capability posture matrix

Posture describes whether a current authoritative owner permits a later
dashboard projection/control. It does not describe dashboard implementation;
all dashboard surfaces remain planned until their Blocks are accepted.

| Capability | Posture | Current evidence and boundary | Revisit trigger |
|---|---|---|---|
| Register/archive local project discovery metadata | `supported` | New narrow dashboard catalog owner is authorized by the tracker; operational truth is excluded. | Catalog schema/authority change. |
| Read Git project/revision/worktree state | `read-only` | Git CLI owner is present; later adapter must use registered roots and argument vectors. | Git compatibility or root-boundary change. |
| Discover/verify trackers | `read-only` | Full and inherited core verifier paths are current. | Verifier hash/profile change. |
| Edit tracker status/evidence directly | `out-of-scope` | Tracker Markdown and implementation task remain writers. | Renewed direct authority plus tracker amendment. |
| Read supervision policy/history/events/issues/conclusions | `read-only` | Current helper validates a live target and preserves mission scoping. | Supervision helper/policy/schema change. |
| Read automation status/configuration | `read-only` | TOML projection exists; values are not a mutation API. | Automation schema/tool change. |
| Start/resume/steer/interrupt Codex work | `supported` | App Server 0.145 stable schemas expose thread/turn owners and approvals/input. | CLI/schema root change or handshake failure. |
| Invoke tracker authoring and Block implementation tasks | `supported` | Installed author/implement skills are current; completion remains their canonical evidence, not task terminality. | Skill hash or invocation schema change. |
| Attach/operate ordinary implementation supervision | `supported` | Supervision helper, role bindings, route gates, and automations exist. | Policy/role/helper incompatibility. |
| Dedicated tracker-authoring supervision profile | `planned` | Five-Block tracker is planning/core and has no accepted implementation. Control remains disabled. | That tracker reaches current accepted implementation evidence. |
| Mechanical `Check now` | `supported` | Watcher/automation and canonical event postcondition exist when one exact target binding is current. | Missing/duplicate watcher or route denial. |
| Semantic checkpoint/meta/issue review | `supported` | Bound reviewer roles and route/conclusion contracts exist conditionally per group. | No eligible role, route, or current candidate root. |
| Policy/cadence adjustment | `supported` | `adjust` plus automation owner can establish policy and actual schedule postconditions. | Unsupported field or unavailable automation owner. |
| Mission-source binding repair | `supported` | `bind` owns mission root/source fields for one exact target and policy history supplies the postcondition. | No reproduced compatible mismatch, materially new intent, or unavailable bind/policy owner. |
| Target/tracker association repair | `unavailable` | Current `bind` and policy schemas have no tracker path/root/association field or canonical repair postcondition. | A maintained owner and postcondition are implemented, then Block 15 is narrowly amended before execution. |
| Role-task binding repair | `supported` | Task and policy owners can establish both the live eligible task and canonical role binding. | No exact eligible role/task or one owner unavailable. |
| Automation binding repair | `supported` | Automation and policy owners can establish both actual schedule state and canonical group-role binding. | No exact automation/group-role mismatch or one owner unavailable. |
| Pause supervision | `supported` | `paused` lifecycle gating plus actual bound-automation pause provide two current postconditions. | Missing lifecycle/automation gate or unsatisfied terminal/report prerequisites. |
| Resume supervision | `supported` | The independently accepted maintained `resume-gate`/`resume-finalize` owner establishes one canonical resumed lifecycle postcondition after every exact bound automation is active at its owner-derived configuration. | Missing or stale pause/source/currentness, partial owner activation, or a task/turn-only resume remains unavailable or pending. |
| Create same-target successor mission binding | `supported` | `mission-successor` accepts materially different direct authority and exact first eligible work, then creates the new policy binding and one pending activation. | Open head/activation, unchanged intent, absent direct authority, or missing exact first eligible work. |
| Close or verify successor first-work activation | `unavailable` | Current `mission-activation-start` accepts an arbitrary later same-target/current-mission record and repeated caller evidence; it does not prove that the named first work began. | The maintained owner must bind an eligible canonical work-start source and postcondition to the exact first-work identity. |
| Successor-task continuity | `supported` | Transition helper and App Server task owner exist; source stop waits for current `work-started`. | Missing direct task-creation authority or incomplete phase. |
| Weekly report generation/verification | `supported` | Maintained stages and one live verified bundle exist; delivery may be separately unavailable. | Report/helper hash or source-root change. |
| Terminal report/shutdown owner | `supported` | Maintained helper stages and gates exist. The current target action is unavailable because outcome/report/delivery/incident gates are not satisfied. | Exact terminal prerequisites become current. |
| Factory evolution through verified disposition | `supported` | Derived prepare/finalize/evaluate/verify owner is implemented; candidate implementation is separately owned. | Helper/contract or evidence eligibility change. |
| Autonomous/adaptive evolution or automatic adoption | `planned` | Adaptive tracker is planning; evolution disposition grants no adoption authority. | Accepted independent implementation and owner evidence. |
| Gmail body read/send from dashboard | `out-of-scope` | Gmail remains an optional supervisor-owned lane. Current target Gmail lanes are disabled. | Renewed product authority and owner design. |
| Actual billing/cost telemetry | `unavailable` | Current reports contain bounded estimates, not billing authority. Label estimates explicitly. | A verified billing source/owner is added. |
| Remote hosting, accounts, collaboration, RBAC, tenancy | `out-of-scope` | Direct mission is local and single-operator. | Renewed direct authority and new tracker. |

## 6. Consequential operation owners and postconditions

Every later control must bind its preview to the current source fingerprint,
use same-origin plus the launch nonce, reject extra/free-form fields, and retain
`requested`, `failed`, and `unverified` separately. A `2xx`, task creation,
message delivery, generated file, or stopped task never proves application.

| Operation | Existing owner | Gate / confirmation class | Canonical applied postcondition | Unavailable behavior |
|---|---|---|---|---|
| Register/archive project | Dashboard catalog only | Explicit path preview; ordinary confirmation | Next valid catalog version contains only the exact discovery record. | Explain invalid/non-Git/escaped/symlinked/duplicate root. |
| Start authoring task | App Server + author skill | Direct scope and exact skill/tracker preview; explicit confirmation | Exact new task/turn exists with skill input and registered cwd. | Disable on App Server/schema/root/authority failure. |
| Start implementation task | App Server + implement skill | Exact tracker hash and Block/range; explicit confirmation | Exact new task/turn exists; implementation acceptance remains later tracker/Git evidence. | Disable on invalid tracker/range/dependencies/root. |
| Continue or steer task | App Server | Exact task/active turn and input; explicit confirmation | Matching turn is started or active turn accepts the steer. | Show terminal/no-active/stale/mismatched turn reason. |
| Interrupt turn | App Server | Exact thread and turn; typed confirmation | Matching turn completes as `interrupted`. | Never present as supervision pause/stop. |
| Attach supervision | Supervision helper + task/automation owners | Exact target, mission, roles, policy, schedules; consequential confirmation | Valid policy/history plus exact live role tasks and automation bindings. | Preserve partial owner state and exact next repair. |
| Check now | Bound watcher/automation | Route gate, exact target/purpose, no duplicate; consequential confirmation | Newer matching canonical check record. | Wake/task success without record remains unverified. |
| Request semantic review | Bound reviewer/supervisor | Route gate, exact candidate/evidence/purpose; consequential confirmation | Newer eligible matching canonical conclusion. | Request and no/stale/superseded conclusion remain separate. |
| Adjust supervision | Supervision `adjust` + automation owner | Exact before/after supported fields; consequential confirmation | Next policy history version and every affected actual automation agree. | Partial reconciliation remains attention. |
| Repair mission-source binding | Bind/policy owner | Reproduced compatible mission-field mismatch; consequential confirmation | Exact mission root/source fields for the selected target and no duplicate group in next policy history. | Materially new intent routes to mission succession. |
| Repair target/tracker association | No current canonical owner | Disabled; explain missing owner and postcondition | None until an implemented owner writes and verifies canonical tracker association. | Never send tracker path/root fields through `bind`; amend Block 15 before execution. |
| Repair role task | Task + policy owner | One exact role/task eligibility and route; consequential confirmation | Live eligible task and canonical role binding both match. | Task-only or policy-only result remains partial. |
| Repair automation binding | Automation + policy owner | One exact automation/group-role mismatch; consequential confirmation | Actual automation and canonical policy binding both match with no duplicate role. | No direct TOML fallback. |
| Pause supervision | Automation + lifecycle owners | Exact group and consequence preview; typed lifecycle confirmation | Canonical `paused` lifecycle plus actual paused state for every bound automation. | Turn state or one-owner-only change is insufficient. |
| Resume supervision | Automation owner + accepted helper lifecycle owner | Exact paused group and owner-derived schedules; consequential confirmation | Every exact named automation is active and one helper-verified `supervision-resume` record binds the pause, mission/policy/source fingerprint, and owner configurations. | Dashboard execution remains closed until Block 24; automation or task resume alone remains insufficient. |
| Begin successor mission binding | `mission-successor` policy owner | Direct new-mission authority, predecessor/closed-head proof, and exact first eligible work; typed confirmation | New policy history has the sole active root, predecessor history is preserved, and one matching activation is `pending`. | Do not use `bind`, create a parallel root, or render pending activation as completed continuation. |
| Close or verify successor first work | No evidence-tight current owner | Disabled; explain the weak source/evidence check | None; a structural `work-started` record from the current helper cannot establish that the named work began. | Do not invoke or trust closure until the maintained owner binds an eligible canonical source to the exact first-work identity. |
| Advance successor-task transition | Transition helper + App Server/task owners | Direct task authority and exact phase; confirmation per phase | Exact next canonical phase; source stop only after gate proves `work-started`. | Missing authority/phase stays open; no invented ID. |
| Generate weekly report | Weekly report + semantic reviewer + optional delivery owner | Exact period/sources/roles; consequential confirmation | Current verified manifest/Markdown/PDF/JSON; delivery is a separate named postcondition. | Reuse valid earlier stages; do not regenerate for display/delivery failure. |
| Run Factory evolution | Evolution artifact owner + independent proposer/evaluator | Exact sources/roles/revisions; consequential confirmation | Immutable artifact set verifies with one current disposition. | No implementation, adoption, deployment, or outcome action. |
| Prepare terminal report | Terminal report/reviewer/delivery owners | Current outcome/prior reports/sources; terminal confirmation | Verified current bundle and configured delivery/readback, without lifecycle mutation. | Report readiness never means stop permitted. |
| Request terminal shutdown | Supervisor, lifecycle, automation, report/delivery gates | Complete current gate packet; explicit terminal phrase | Terminal lifecycle, shutdown receipt, and every bound automation state match. | Any stale/open/partial gate disables; no generic Stop. |

## 7. Compatibility and failure contract

- The later Python API and TypeScript consumer share one versioned boundary.
  Every response includes source identity, `observed_at`, fingerprint/revision,
  coverage, limitations, and availability.
- Zod validates every HTTP and App Server boundary. Python fixtures and
  TypeScript consumers change atomically with any schema.
- App Server initialization and generated schemas are version-gated at startup.
  Unsupported versions degrade task control to explicit read-only/unavailable.
- Experimental App Server methods and fields are unavailable by default.
- Source adapters return partial data with exact failures; one unavailable
  source does not erase valid independent sources or become an empty healthy
  collection.
- Filesystem reads remain inside registered canonical roots after symlink and
  traversal resolution. Subprocesses use argument vectors and bounded timeouts.
- The HTTP service remains loopback-only, same-origin for mutation, launch-nonce
  protected, and CSP/security-header constrained.
- No durable dashboard operation ledger is introduced. Restart reconstructs
  owner state where possible and labels prior ephemeral state unavailable where
  not reconstructable.

## 8. Current conflicts, limitations, and unavailable reasons

1. The evolution MVP tracker's header says `in-progress` while all Block rows
   and completion evidence say `accepted`; the code and changelog say
   implemented/demonstrated. Preserve each source and flag the tracker summary
   conflict. Do not rewrite it in this Block.
2. The reference frontend task is active, but its package manifest and lockfile
   are clean at exact commit `f924555…`. Adapt only that frozen stack contract;
   do not adopt ongoing Patent Studio UI/domain changes.
3. No terminal or Factory-evolution manifest exists in the bounded live sample.
   Their readers/workflows are supported by code; current artifact rows are
   unavailable with that exact reason.
4. Tracker-authoring supervision and adaptive/autonomous evolution remain
   planning-only. Their controls are disabled until exact accepted
   implementation evidence exists.
5. Current target Gmail lanes are disabled. Reports may verify locally, but
   configured delivery and terminal shutdown stay unavailable where policy
   requires Gmail evidence.
6. The official App Server documentation is mutable. Local CLI version plus the
   generated stable schema-bundle root is the compatibility freeze.
7. Tracker/run association can be incomplete. Show an unbound anomaly; never
   join by filename, label, or task title alone.
8. Planned Block 15 currently combines supported mission-source repair with
   unavailable target/tracker association repair. Preserve the requested
   product scope, but amend that future Block at its owner/acceptance boundary
   before executing or accepting it; earlier dependency-safe Blocks remain
   available.
9. The baseline's former combined pause/resume Block mixed supported pause with
   then-unavailable resume. Current Block 22 is pause-only, accepted Block 23
   supplies the maintained resume lifecycle/postcondition, and Block 24 exposes
   dashboard resume over that independently accepted owner.
10. Planned Block 19 predates the durable first-work activation obligation in
    source revision `08b4f98`, whose current closure is not evidence-tight.
    Before executing that future Block, amend its preview, acceptance,
    recovery, and Stop to end at the verified `pending` binding and expose
    first-work closure as unavailable unless the maintained owner is hardened.

## 9. Revalidation triggers

Re-run only the affected baseline slice when:

- repository `HEAD`, tracker blob, frame hash, or any named owner hash changes;
- an installed skill-refresh notice changes a skill hash;
- `codex --version` or the stable generated schema bundle root changes;
- the frozen frontend manifest/lock hash changes;
- the HTTP reference file hashes change before Block 1 adapts them;
- verifier output/profile behavior changes;
- supervision policy/helper schema or mission root changes;
- a maintained tracker-association or resumed-lifecycle owner becomes
  available, or execution reaches a required binding, pause/resume, or
  succession plan-amendment gate;
- an automation projection schema or callable owner changes;
- a report/evolution/terminal helper or manifest schema changes;
- a planned capability gains accepted implementation evidence; or
- an unavailable integration becomes available or a supported owner fails its
  compatibility/postcondition probe.

Revalidation never upgrades a plan, report, task, or green light into
operator-visible completion.

## 10. Block 0 boundary

This candidate supplies the required source inventory, exact content/version
roots, terminology, precedence, capability matrix, owner/postcondition map,
unsupported reasons, live schema samples, product-capability selection, and
revalidation triggers.

No fixture is committed because every needed family can be generated from a
maintained schema or exact local owner during later focused tests. No dashboard
runtime, dependency manifest, server, API, catalog, or frontend file is created
in Block 0.

Stop before Block 1 creates the loopback runtime or reference frontend scaffold.
