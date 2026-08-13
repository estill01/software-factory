# Software Factory Repository Consolidation Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–8
- Repository: `/Users/ethanstillman/code/software_factory`
- Governing objective: Direct user request in task `019ffc82-86de-74e2-bdfb-a23403da5c2f` to coordinate all active Software Factory tasks, synthesize accepted work onto `main`/`origin/main`, clean stale branches and worktrees, preserve and resume intended work, and include web-app task `019fe547-e054-7ca0-9940-ec4aa146df78`.

## 1. Purpose and intended outcome

Return the Software Factory repository and its active Codex work to one known,
integrated, reproducible baseline without losing accepted implementation,
review, tracker, dashboard, or uncommitted evidence.

Completion means:

- every useful accepted Software Factory commit is either reachable from the
  canonical `main` line or explicitly preserved with a truthful deferred or
  rejected disposition;
- local `main` and `origin/main` resolve to the same validated integrated
  revision, with no open pull request or branch that still owns merge-ready
  work;
- the installed Software Factory skill release is verified against a source
  revision reachable from that canonical `main` line;
- the completed operations dashboard remains buildable and its health,
  Factory Floor, tracker, task, and lifecycle views work from the integrated
  revision;
- stale worktrees and branches are removed only after their commits and dirty
  state have been classified and preserved; and
- intended unfinished work resumes, when dependency-safe, from clean branches
  and worktrees based on the new `main`, with exact tracker and task ownership.

### Mission frame

- Primary outcome: one trustworthy Software Factory source line and one
  coordinated set of active implementation lanes.
- Observable completion: Git, release, dashboard, tracker, task, branch,
  worktree, and pull-request checks all resolve to the same reconciled state.
- Ordinary effect classes needed: task pausing and routing, Git integration,
  conflict correction, validation, independent review, main publication,
  release verification or promotion, web-app runtime verification, branch and
  worktree cleanup, and clean follow-on lane creation.
- Hard direct authority or safety boundaries: preserve user-owned dirty state;
  do not infer acceptance from commits or tests; do not force-push, rewrite
  reviewed history, manufacture tracker completion, bypass independent review,
  or delete an unclassified ref or worktree.
- Material goal alteration or reversal: dropping accepted capability,
  abandoning requested unfinished work, changing repository ownership, or
  replacing canonical `main` with a history-rewritten line requires renewed
  direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker changes the repository and operating
  baseline from which the Factory control plane, release owner, dashboard, and
  product-program evolution work run.
- Direct product sources: the direct user request above;
  `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md`;
  `docs/software-factory-operations-dashboard-implementation-tracker.md`;
  `docs/software-factory-recursive-product-program-evolution-implementation-tracker.md`;
  and `docs/software-factory-systemic-supervision-recovery-implementation-tracker.md`
  when each is present at its live source revision.
- Product thesis and intended effect: the Factory should operate from one
  source of truth while allowing bounded, dependency-ordered implementation
  work to proceed in isolated lanes whose results converge back to `main`.
- Protected capabilities: accepted supervision/range/release behavior;
  independent review and fail-closed authority boundaries; the completed
  dashboard and its canonical-owner projections; accepted product-program
  Blocks 0–4; rejected-history traceability; and recoverability of dirty or
  detached work.
- Architecture strategy: use Git `main` as the canonical repository source,
  the existing skill-release owner for installed runtime, existing tracker and
  supervision owners for execution state, and short-lived branches/worktrees
  only for isolated current work.
- Requested capability: reconcile all active Software Factory implementation
  lines, publish the accepted synthesis, remove stale lanes, and resume only
  the intended remaining work from the reconciled baseline.
- Proportionality: one integration line, one disposition ledger, existing test
  and release owners, and bounded follow-on branches are sufficient; no new Git
  service, release service, task database, or dashboard authority is needed.
- Tradeoffs: merge commits preserve ancestry and rejected history but make the
  graph non-linear; cleanup reduces ambiguity but occurs only after reachability
  proof; pausing overlapping work delays individual Blocks briefly to avoid
  conflicting writers.
- Uncertainty: exact branch tips, active release source, remote protection, and
  task state are live inputs and must be re-read at every owning Block.

## 2. Target architecture and authority boundaries

```text
active tasks and reviewed branch tips
                 |
                 v
  one frozen integration candidate
                 |
       validation + independent review
                 |
                 v
      local main == origin/main
          |               |
          v               v
 installed release    dashboard runtime
          |
          v
 clean follow-on branches/worktrees
```

- Git commits and refs own source history; tracker status does not replace Git
  reachability, and Git reachability does not create tracker acceptance.
- The maintained release owner alone installs or promotes Factory skills.
- Dashboard views remain projections of maintained supervision, automation,
  App Server, tracker, report, and Factory Evolution owners.
- Each active implementation tracker retains its own acceptance owner. This
  consolidation tracker may integrate accepted commits and schedule remaining
  work, but it cannot manufacture acceptance for another tracker.
- One branch/worktree is the writer for each integration or implementation
  lane. Reviewers and supervision roles remain read-only.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Repository history and publication | Git and `origin` | Reuse; merge without history rewrite |
| Pull requests and remote default branch | GitHub repository `estill01/software-factory` | Reuse; merge or close only after exact disposition |
| Skill staging and activation | `scripts/skill_release.py` and installed release owner | Reuse; never replace with pointer edits |
| Tracker structure and verification | `author-implementation-trackers` | Reuse for this tracker and later tracker amendments |
| Block execution and evidence | `implement-tracker-blocks` | Reuse one Block at a time |
| Supervision state and task routing | `supervise-tracker-runs` | Reuse exact gates and target owners |
| Dashboard build and runtime | `dashboard/web` and `dashboard/server` | Reuse the completed implementation |
| Product-program implementation | `evolve-product-program` and its tracker | Reuse accepted Blocks 0–4 and resume later Blocks separately |

## 4. Prior-work and source-adaptation map

This table is the discovery snapshot at tracker creation. Block 0 replaces each
mutable tip with an exact freeze record before integration.

| Source or predecessor | Discovery revision | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| `origin/main` | `a2f86665842ad9514fa1c38ed8a405f148f2025b` | reuse as clean integration base | 0 | Re-read remote before first merge |
| Automatic-release corrected line | `f13002e9a8c2c17a7981aec9b74908d7f14ed0d6` | integrate after exact Block 2 closure/currentness check | 1 | Reconcile concurrent accepted-release and watcher successors |
| Accepted automatic-release continuation | `ad9fa66dbc43e4e9509ea5346c04dbf4a2436ab3` | adapt/merge accepted Blocks and evidence | 1 | Preserve later Block evidence without regressing corrected owner code |
| Watcher incident-report release | `9c143e486bdd51d2aaab751367b20dc74e74e765` | adapt/merge if not patch-equivalent | 1 | Verify active installed source and mapped regression |
| Completed dashboard and Factory Evolution MVP | `fff1809716d75f4360fa052c540cfdc38eb91d4c` | integrate | 2 | Resolve control-plane overlap and reverify web app |
| Product-program evolution Blocks 0–4 | `423ae8de74f5fd57d2d8a653e769cda1d8eedd7b` | integrate accepted checkpoint | 3 | Preserve `.program-revision/`; resume Blocks 5–11 after main |
| Selection-quality RSI planning | `4df42f757cb71fd7ebaf30c8275d18f73049fb3b` | integrate planning source if not present elsewhere | 3 | Rebase future execution on new main |
| Systemic supervision recovery tracker | `448863f3869a14294ae388147c5241bf4ae2ffb2` | integrate tracker only, then amend against accepted source | 3, 7 | Blocks 0–6 remain planning until automatic-release dependency is current |
| Dirty product-program `.program-revision/` | untracked discovery state | preserve and classify before cleanup | 0, 3 | Move into its canonical evidence owner or preserve in the clean successor lane |
| Detached and historical worktrees | discovery inventory | retire only after reachability/patch-equivalence proof | 6 | Preserve any unique commits before removal |

## 5. Scope, non-goals, and proportionality

### In scope

- all Software Factory tasks, branches, worktrees, remote refs, and pull
  requests discovered during this run;
- accepted source, tracker, review, and dashboard evidence needed to establish
  the canonical baseline;
- local and remote main normalization, release reconciliation, and dashboard
  verification;
- stale-lane cleanup and creation of the minimum clean lanes needed for
  remaining intended work.

### Out of scope

- changing Patent Studio, Graphy, patent workspaces, Gmail policy, or unrelated
  repositories;
- inventing acceptance for unfinished tracker Blocks;
- broad refactoring, optional hardening, or a new branch-management service;
- deleting supervision ledgers, rejected commits, or user evidence.

### Proportionality

Use ancestry, patch-equivalence, current tracker evidence, and mapped tests to
select only needed merges or conflict corrections. Do not replay every branch,
rerun every historical suite, or retain parallel implementations when a current
accepted owner supersedes them.

## 6. Block execution contract

1. Execute Blocks 0–8 in dependency order.
2. Re-read the selected Block, live tasks, Git refs, installed release, and
   worktree state before editing.
3. Preserve unrelated, staged, untracked, detached, rejected, and in-flight
   work until its exact disposition is recorded.
4. Use one integration writer. Overlapping implementation tasks must finish a
   current atomic boundary and remain idle before their source is merged.
5. Prefer merge commits for independently reviewed histories; use a
   cherry-pick only for a narrow standalone change whose source branch must not
   otherwise be adopted, and record why.
6. Conflict resolution selects current accepted semantics from direct tracker,
   test, review, and release evidence. It never treats newest timestamp or
   passing tests alone as authority.
7. Run focused proof after each integration delta. Freeze one final candidate
   before mapped validation and exact independent review.
8. Push bounded checkpoints to the configured remote. Do not force-push or
   bypass remote policy.
9. Delete a ref or worktree only after it is clean or its dirty state is
   preserved and its useful commits are reachable from canonical `main` or an
   explicit clean follow-on branch.
10. A Block Stop is an internal checkpoint for this full-tracker request;
    continue automatically through the dependency-safe next Block.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<release, remote, task, or not-applicable>`
- Inputs: `<refs, worktrees, tasks, trackers, and hashes>`
- Outputs: `<integrated refs, manifests, runtime, or cleanup result>`
- Focused validation: `<commands and results>`
- Mapped validation: `<commands and results>`
- Candidate freeze: `<commit/tree and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<bounded reuse/widening result>`
- Independent review: `<exact revision-bound result>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<safe frontier and next owner>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit and push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze writers and source-disposition ledger | — | `completed` |
| 1 | Integrate automatic-release and supervision control-plane lines | 0 | `completed` |
| 2 | Integrate and preserve the completed dashboard/evolution web app | 1 | `completed` |
| 3 | Integrate accepted product-program work and future tracker sources | 2 | `completed` |
| 4 | Validate and independently review the unified candidate | 3 | `completed` |
| 5 | Publish canonical main and reconcile the installed release | 4 | `completed` |
| 6 | Prune stale branches, worktrees, and pull-request residue | 5 | `completed` |
| 7 | Recreate clean lanes and resume intended remaining work | 6 | `not-started` |
| 8 | Verify the repository-wide steady state | 7 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8`

## Block 0 — Freeze writers and source-disposition ledger

Status: `completed`

### Objective

Establish one integration writer and a current, lossless disposition for every
Software Factory task, ref, worktree, dirty path, installed release, and pull
request before merging or deleting anything.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block records current ownership and evidence; it
  does not change Factory behavior or canonical source.

### Inputs and dependencies

- None.

### Required work

- Resolve every active Software Factory task by exact ID and identify its
  current atomic boundary, worktree, branch, tracker, Block, and writer state.
- Gate and route bounded pause/idle actions where overlapping writers would
  touch the same source. Preserve current validation and review results.
- Fetch the remote and freeze exact local/remote refs, PR state, installed
  release source, worktree dirt, detached commits, and branch ancestry.
- Classify each line as integrate, patch-equivalent, rejected-history-only,
  superseded, deferred, or stale-and-removable, with evidence.
- Preserve `.program-revision/` and any other dirty or untracked state before a
  worktree can become cleanup-eligible.

### Scope and non-goals

- In scope: read-only inventory, bounded task coordination, and this tracker's
  disposition/evidence update.
- Not in scope: source merges, release changes, main publication, or cleanup.
- New machinery is not permitted; use Git, Codex task tools, GitHub, and the
  maintained supervision owner.

### Deliverables and recorded state

- Current disposition table with exact revisions and owner tasks.
- One declared integration writer and explicit idle/active posture for every
  overlapping task.
- Preserved copy or canonical ownership disposition for every dirty path.

### Live disposition ledger

This snapshot was refreshed after `git fetch --prune origin`. Moving sources
remain explicitly provisional until their owning task freezes and pushes an
exact candidate.

| Task or owner | Current boundary | Writer posture | Consolidation disposition |
|---|---|---|---|
| `019ffc82-86de-74e2-bdfb-a23403da5c2f` | repository consolidation, this Block 0 | sole integration writer in `codex/repository-consolidation` | owns inventory and later merge/publish/cleanup; does not edit active implementation worktrees |
| `019ffc0a-7946-76e0-9164-d70ddbe7a492` | stopped during the shared automatic-release Block 5 correction | idle/interrupted; no further writer authority | its exact combined five-file delta is preserved on `codex/block5-shared-candidate` at `ba9d80171bd21397b970977267c192ae101d994f` for Block 1 validation and integration |
| `019fdfe4-dabe-7130-ac93-f8fa8e3bce12` | stopped after detecting the same shared Block 5 candidate | idle/interrupted; no further writer authority | no independent source commit was produced; its useful corrections are included in `ba9d80171bd21397b970977267c192ae101d994f` |
| `019ffa13-a3d8-78a2-a3cb-f187ca333e8f` | accepted product-program Blocks 0–4 at `423ae8de74f5fd57d2d8a653e769cda1d8eedd7b` | idle/stopped; Blocks 5–11 remain untouched | port the accepted `4ae6a61..423ae8d` capability delta in Block 3, preserve dirty evidence, and resume only from published main in Block 7 |
| `019fe547-e054-7ca0-9940-ec4aa146df78` | completed dashboard Blocks 0–31; implementation close `29b357d8465c9c5607da93d69fab392b8418ad45`, combined branch `fff1809716d75f4360fa052c540cfdc38eb91d4c` | idle/stopped; no implementation writer | merge the post-PR dashboard/evolution delta in Block 2 and re-establish build, API, browser, and runtime proof |
| Automatic-release reviewers and watcher | current target `019fdfe4-dabe-7130-ac93-f8fa8e3bce12` | read-only; the Sol Max reviewer issued one correction steer and returned idle | retain for exact target review until Block 1 is frozen; do not treat review activity as an implementation writer |
| Product-program reviewers and watcher | current target `019ffa13-a3d8-78a2-a3cb-f187ca333e8f` | idle/read-only | retain until the clean Block 7 successor lane is bound |
| Dashboard reviewers and watcher | completed target `019fe547-e054-7ca0-9940-ec4aa146df78` | idle/read-only, but two heartbeat prompts still reference obsolete release `35186f522fb6-0eddf09b3ae6` and a historical Block 20 snapshot | preserve until terminal/current-release reconciliation in Blocks 5–7; they are stale automation configuration, not source writers |

Current repository and external-owner freeze:

- `origin/main`: `a2f86665842ad9514fa1c38ed8a405f148f2025b`.
- Open pull requests in `estill01/software-factory`: none.
- Installed release: `9c143e486bdd-95aa08de7014`, source
  `9c143e486bdd51d2aaab751367b20dc74e74e765`, automated assurance passed
  release-owner 21, tracker-authoring 30, tracker-execution 69, and
  tracker-supervision 376 tests.
- Worktree count: 35 before this tracker, 36 with the clean consolidation
  worktree. The former Block 5 worktree is now clean at pushed checkpoint
  `ba9d801`; only this tracker worktree and the product-program evidence
  worktree are dirty.
- The product worktree's `.program-revision/` has exactly three untracked
  files and remains untouched: proposal SHA-256
  `f79b10685096d6105710afa5169fa927220f8af821319cf879ab2f2e53068e0f`,
  receipt SHA-256
  `290d5d99d204a78b9c7c8995dd8d29af7dd25be60c880a18c00658d2bc37e818`,
  and patch SHA-256
  `b255a62ed63ab9f1a1204e35b9cb7ed235665acfad15c2dae03acac4a5e97708`.
- Unique detached commits requiring history preservation before worktree
  removal are `719e0ba42304db74867db5b2f03395f6f3c82340`,
  `010f31fbc6ff7582b228739da1b016764b1494d4`,
  `bef921e61e12c3afb22d612e1bcb3192a2be65f1`, and
  `8678483167a79caa65cff7acd82b26b20bc76b0a`. Their patch identities are
  unique in the current named-ref graph, so Block 6 may remove their
  worktrees only after Block 3 or 4 makes the commits reachable as preserved
  non-current history.
- No branch or worktree is cleanup-eligible while either automatic-release
  source task is moving. All clean historical worktrees remain retained until
  the exact Block 4 candidate proves ancestry or patch-equivalent disposition.

### Resource and economy contract

Reuse one fetched object database and one worktree inventory. Widen from ref
ancestry to file-level comparison only for divergent heads whose disposition is
not decided by reachability or patch equivalence.

### QA and independent review

Mechanically verify no worktree or ref is omitted and no dirty path is labeled
removable. A second exact-ref review is required before the first deletion, in
Block 6.

### Acceptance

- Exactly one integration writer remains active.
- Every discovered task, ref, worktree, dirty path, PR, and installed release
  has an exact current disposition.
- No mutation candidate depends on an in-progress writer.

### Negative tests

- Reject a disposition that marks an untracked path, unique commit, open review,
  or moving branch safe to remove.

### Completion evidence

- Repository commit: inventory checkpoint
  `4d2843fba782690f26ccf1f411c19e45e4760e6d`; Block 0 closure is this
  tracker-only successor.
- External/domain revision or root: `origin/main`
  `a2f86665842ad9514fa1c38ed8a405f148f2025b`; installed release
  `9c143e486bdd-95aa08de7014`; no open pull requests.
- Inputs: 36 worktrees, all local and remote branches, four named primary
  tasks, their reviewer/watcher roles, six active heartbeat automations,
  installed release manifest, and three dirty-state sets.
- Outputs: all four former implementation tasks are quiescent; the shared
  dirty Block 5 candidate is clean, committed, and pushed at
  `ba9d80171bd21397b970977267c192ae101d994f`; exact dispositions and dirty
  evidence hashes are recorded above.
- Focused validation: combined terminal/supervision run 330/330, Python 3.14
  compile, supervision skill validation, and diff check passed for the shared
  candidate.
- Mapped validation: deferred to frozen integrated candidate in Block 4.
- Candidate freeze: `ba9d80171bd21397b970977267c192ae101d994f`, tree
  `8601baddf200cb96553824b7207d3cdd6ad6105e`; clean and exact with upstream.
- Remediation closure: prior Block 5 findings are preserved as candidate
  inputs; acceptance remains owned by Block 1 and Block 4 review.
- Resource posture: only one integration writer remains; stopped tasks will
  not be restarted during consolidation.
- Independent review: deletion review remains required in Block 6; no deletion
  occurred in this Block.
- Retained open work: integration Blocks 1–8 and all tracker-owned future work
  recorded for Block 7.
- Decision/continuation posture: proceed to Block 1 from the exact frozen refs.
- Post-block audit: accepted; no moving source remains.
- Git durability: inventory and shared candidate checkpoints are pushed
  non-force to their configured upstream branches.

### Stop

Stop before merging an implementation branch into the consolidation branch.

---

## Block 1 — Integrate automatic-release and supervision control-plane lines

Status: `completed`

### Objective

Produce one current automatic-release/control-plane source that preserves the
accepted corrected Block 2 semantics, later accepted tracker work, and any
independently accepted watcher/release corrections.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one recoverable, currentness-safe automatic release
  path instead of divergent competing source lines.
- Potential capability loss or regression: merging a stale successor could
  drop authority, currentness, rollback, refresh, or watcher incident behavior.
- Protected-capability effect: preserve fail-closed authority, exact independent
  review, rollback-safe release ownership, tracker evidence, and watcher
  recovery behavior.
- Architecture and operating-model effect: the canonical Git line and normal
  release owner become the only current implementation source.
- Tradeoff and source evidence: preserve merge ancestry and resolve code using
  current accepted review/tracker evidence, even when that retains rejected
  commits as non-current history.

### Inputs and dependencies

- Block 0.
- Frozen heads for the corrected automatic-release line, accepted continuation,
  watcher incident release, and installed release source.

### Required work

- Re-read the automatic-release tracker and exact independent review evidence.
- Merge all non-equivalent accepted histories into the consolidation branch.
- Resolve overlaps through the current authoritative implementation and add
  only the smallest regression correction required by a reproduced conflict.
- Preserve rejected candidate lineage and truthful Block evidence.

### Scope and non-goals

- In scope: automatic release, supervisor refresh, range/authority support, and
  mapped watcher/release corrections already accepted or required by conflicts.
- Not in scope: implementing a new systemic recovery tracker or product-program
  Blocks.
- Do not generalize conflict corrections beyond reproduced accepted invariants.

### Deliverables and recorded state

- Integrated source commit containing the selected automatic-release and
  supervision behavior.
- Branch-by-branch merge or patch-equivalence disposition.

### Resource and economy contract

Run focused affected tests after each merge/conflict correction. Reuse current
full-suite proof where tree-identical; rerun mapped proof only after the
candidate is frozen.

### QA and independent review

Require exact-revision review of conflict resolutions and any semantic choice
between divergent accepted heads.

### Acceptance

- All accepted automatic-release and watcher changes are reachable from the
  candidate or explicitly proven patch-equivalent.
- The automatic-release tracker remains truthful at the integrated revision.
- Focused release, range, supervision, authoring, and implementation proof is
  green for the affected surface.

### Negative tests

- Reject a merge that reintroduces a reviewed authority/currentness failure,
  loses later accepted tracker state, or silently chooses by timestamp.

### Completion evidence

- Repository commit: corrected automatic-release integration begins at
  `8951a45` and retains the accepted continuation and watcher histories through
  `e2723fd` and `e4e0ba6`; integrated compatibility corrections end at
  `a08012f`.
- External/domain revision or root: accepted source heads `f13002e`,
  `ad9fa66`, and `9c143e4` are ancestors of candidate `28d9ed3`.
- Inputs: the corrected automatic-release line, accepted continuation, watcher
  incident release, direct-authority/range repair histories, and current
  tracker evidence.
- Outputs: current release, range admission, terminal recovery, watcher report,
  and supervisor refresh behavior coexist without selecting an older owner by
  timestamp.
- Focused validation: release-owner 23/23, authoring 42/42, product-program
  67/67, Factory Evolution dogfood, and repaired focused supervision/range
  regression sets passed.
- Mapped validation: full supervision validation is recorded under Block 4.
- Candidate freeze: automatic-release and supervision tree incorporated in
  `28d9ed3` without post-merge dirty tracked files.
- Remediation closure: legacy range admission and helper argument-shape
  incompatibilities were reproduced and corrected at `a08012f`.
- Resource posture: superseded repair tips are history-only parents of the
  archival merge and have no active writer.
- Independent review: combined-candidate review continues in Block 4.
- Retained open work: automatic-release tracker Blocks 5–7 remain unaccepted
  and are assigned by Block 7.

### Stop

Stop before integrating the dashboard/evolution branch.

---

## Block 2 — Integrate and preserve the completed dashboard/evolution web app

Status: `completed`

### Objective

Make the complete dashboard and Factory Evolution MVP reachable from the
consolidation source without regressing current control-plane behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: retain the operator's completed multi-project
  Factory dashboard on the canonical repository line.
- Potential capability loss or regression: control-plane conflict resolution
  could break canonical projections, runtime behavior, or previously corrected
  current-versus-historical lifecycle rendering.
- Protected-capability effect: preserve 32/32 dashboard tracker acceptance,
  strict task provenance, current lifecycle projection, and canonical-owner
  boundaries.
- Architecture and operating-model effect: dashboard client/server code ships
  from the same source line as its maintained control-plane owners.
- Tradeoff and source evidence: resolve overlap in favor of current accepted
  control-plane semantics while preserving dashboard-specific adapters and UI.

### Inputs and dependencies

- Block 1.
- Completed dashboard/evolution head and tracker.

### Required work

- Merge the dashboard/evolution history and resolve overlap narrowly.
- Confirm the final dashboard implementation commit remains reachable.
- Build the web client and run focused server, projection, and API tests.
- Preserve the completed task's independent outcome and lifecycle evidence as
  historical evidence; obtain new runtime proof for the integrated revision.

### Scope and non-goals

- In scope: existing dashboard/evolution code, tests, tracker, build, and
  integration corrections.
- Not in scope: redesigning the UI, adding new dashboard features, or creating
  a second status owner.
- Do not reopen accepted UI work without a mapped conflict or runtime failure.

### Deliverables and recorded state

- Integrated dashboard source and build artifacts or reproducible build result.
- Exact source mapping from completed dashboard revision to integrated main
  candidate.

### Resource and economy contract

Reuse the repository-owned build/test commands. Browser-check only the health,
Factory Floor, tracker list/detail, task detail, and lifecycle surfaces affected
by source integration.

### QA and independent review

Review conflict resolutions and operator-visible runtime behavior against the
completed tracker and current canonical owners.

### Acceptance

- The dashboard builds and starts from the integrated candidate.
- `/api/v1/health` passes and affected browser views show current, consistent
  data without schema fallback or historical-state contamination.
- Dashboard revision `29b357d8465c9c5607da93d69fab392b8418ad45`
  remains reachable in the integrated history.

### Negative tests

- Reject a candidate that keeps backend tests green but loses the dashboard,
  serves stale static output, or reports historical failure as current state.

### Completion evidence

- Repository commit: dashboard/evolution history merged at `31c852e`; current
  owner alignment and integrated compatibility corrections are `1a5c24c`,
  `eed001e`, and `2e58954`.
- External/domain revision or root: completed dashboard revision
  `29b357d8465c9c5607da93d69fab392b8418ad45` is an ancestor of candidate
  `28d9ed3`.
- Inputs: the completed 32-Block dashboard line, current supervision owners,
  and integrated Factory Evolution MVP.
- Outputs: the dashboard remains on the unified tree; strict weekly-report and
  degraded evolution-workflow envelopes now match the web schemas.
- Focused validation: the two review-derived server regressions passed 2/2;
  the serial web suite passed 117/117.
- Mapped validation: full server suite and browser/runtime proof continue in
  Block 4.
- Candidate freeze: `28d9ed3` with dashboard tracked files clean.
- Remediation closure: independent review findings for extra weekly metadata
  and missing degraded-workflow fields were corrected at `2e58954`.
- Resource posture: the old dashboard task and its writer are quiescent; its
  watcher and reviewer schedules are paused.
- Independent review: first combined review produced the two corrected
  findings above; fresh exact-delta review continues in Block 4.
- Retained open work: no dashboard implementation Block remains; runtime
  verification and ordinary maintenance remain with Blocks 4–5.

### Stop

Stop before integrating product-program or future tracker branches.

---

## Block 3 — Integrate accepted product-program work and future tracker sources

Status: `completed`

### Objective

Preserve accepted product-program Blocks 0–4 and all approved future-work
trackers on the unified source while keeping unaccepted implementation open.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: retain accepted product-program selection and
  evidence behavior while making its remaining work and systemic recovery plan
  executable from the current Factory baseline.
- Potential capability loss or regression: a broad merge may replace newer
  supervision owners or falsely imply later Block acceptance.
- Protected-capability effect: preserve exact accepted Blocks 0–4, tracker
  evidence, `.program-revision/`, and planning-only status for unimplemented
  work.
- Architecture and operating-model effect: product-program and recovery work
  become clean follow-on consumers of canonical `main`, not parallel baselines.
- Tradeoff and source evidence: integrate accepted implementation and planning
  documents now; defer dependent Blocks until their prerequisites are current.

### Inputs and dependencies

- Block 2.
- Product-program accepted head, selection-quality tracker head, systemic
  recovery tracker head, and preserved dirty program revision.

### Required work

- Merge or port accepted product-program Blocks 0–4 without regressing the
  current control-plane line.
- Integrate non-duplicated selection-quality and systemic recovery tracker
  sources as planning artifacts.
- Reconcile `.program-revision/` with its canonical evidence owner; if it is
  transient generated state, preserve a content identity and verify it can be
  reproduced before later worktree cleanup.
- Record exact dependencies: product-program Blocks 5–11 and systemic recovery
  Blocks 0–6 resume only from the published integrated main and after any named
  automatic-release prerequisite is accepted.

### Scope and non-goals

- In scope: accepted product-program implementation, current tracker documents,
  and preservation of dirty evidence.
- Not in scope: implementing product-program Blocks 5–11 or systemic recovery
  Blocks 0–6 in this Block.
- Do not mark planning artifacts or unreviewed ports accepted.

### Deliverables and recorded state

- Integrated accepted implementation and tracker documents.
- Truthful remaining-work and dependency disposition for each future tracker.
- Preserved or reproducible program-revision evidence.

### Resource and economy contract

Use ancestry and changed-path mapping before tests. Run product-program focused
proof for merged code and verifier-only proof for planning-only documents.

### QA and independent review

Require exact-revision review of any conflict that changes accepted
product-program behavior or tracker structure.

### Acceptance

- Accepted Blocks 0–4 remain supported by current code and exact evidence.
- No later Block is reported accepted.
- Future trackers cite current dependencies and are queued for clean Block 7
  lanes.

### Negative tests

- Reject a merge that overwrites newer control-plane owners, discards dirty
  evidence, or converts planning status into implementation completion.

### Completion evidence

- Repository commit: accepted product-program history merged at `09470d3` and
  adapted at `961c4f8`; systemic recovery and selection-quality tracker
  histories are retained through `0dcb4a5`/`9d20901` and
  `4efb52d`/`e43bfda`.
- External/domain revision or root: accepted product checkpoint `423ae8d`,
  systemic tracker `448863f`, and selection tracker `4df42f7` are ancestors of
  candidate `28d9ed3`.
- Inputs: accepted product Blocks 0–4, two planning trackers, and the shared
  `.program-revision/` evidence set.
- Outputs: accepted implementation and planning sources are integrated without
  claiming product Blocks 5–11 or systemic Blocks 0–6 complete.
- Focused validation: product-program tests passed 67/67; tracker authoring
  tests passed 42/42.
- Mapped validation: broader combined proof continues in Block 4.
- Candidate freeze: `28d9ed3`; the exact generated program revision is
  separately checkpointed at `4e4b5e9` and reachable as an archival parent.
- Remediation closure: the product revision fixture mission identity mismatch
  was corrected and its focused regression passed.
- Resource posture: the old product task is quiescent and its six-hour/four-hour
  supervision schedules are paused.
- Independent review: no open product-program finding in the combined review.
- Retained open work: product Blocks 5–11, systemic recovery Blocks 0–6, and
  selection-quality planning remain explicitly unaccepted for Block 7.

### Stop

Stop before broad unified candidate validation.

---

## Block 4 — Validate and independently review the unified candidate

Status: `completed`

### Objective

Freeze one integrated revision and establish that it preserves the combined
Factory, release, dashboard, and accepted product-program capabilities.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: demonstrate one candidate supplies the complete
  combined supported capability.
- Potential capability loss or regression: integration defects may appear only
  across owners or at the operator-visible runtime.
- Protected-capability effect: explicitly rechecks control-plane, release,
  dashboard, product-program, tracker, and history-preservation invariants.
- Architecture and operating-model effect: validates the single-source model
  before it becomes canonical.
- Tradeoff and source evidence: one proportional mapped pass is accepted after
  focused convergence; repeated whole-suite validation is not.

### Inputs and dependencies

- Block 3.

### Required work

- Finish all known in-scope conflict corrections and freeze one commit/tree.
- Run changed-path focused tests, all mapped skill validators and tests, tracker
  verification, dashboard build/server tests, product-program tests, and Git
  diff/history integrity checks.
- Obtain exact-revision independent review of combined behavior, conflict
  decisions, retained open work, and requested outcome coverage.
- Correct only review findings tied to this tracker's invariants, then rerun
  affected proof and fresh review.

### Scope and non-goals

- In scope: validation and corrections necessary for the integrated outcome.
- Not in scope: optional refactoring, unrequested features, or implementation of
  deferred tracker Blocks.
- No new machinery is permitted without a reproduced integration failure.

### Deliverables and recorded state

- Frozen validated candidate commit/tree.
- Focused/mapped test manifest and exact independent review.
- Closure matrix for any rejected candidate.

### Resource and economy contract

Run likely-mutating review before the final expensive mapped pass when possible.
After freeze, any change invalidates only affected proof. One full mapped pass
and one exact review pass are normal; widen only for a named failure.

### QA and independent review

Independent review is mandatory and must be distinct from the integration
writer.

### Acceptance

- All selected proof passes against an unchanged frozen tree.
- Independent review finds no open material issue with the combined outcome.
- Retained open work is compatible with main publication and assigned to an
  exact later owner.

### Negative tests

- Reject process-only confidence, stale proof, self-review, or a candidate that
  cannot reproduce the dashboard/runtime and installed-skill validation path.

### Completion evidence

- Repository commit: frozen validated source `253da9a`, with code tree ending at
  `2e58954` and ancestry-only archival merge `28d9ed3`.
- External/domain revision or root: `origin/main`
  `a2f86665842ad9514fa1c38ed8a405f148f2025b` remained unchanged during the
  complete review/validation window.
- Inputs: every integrated source and preservation commit listed in Blocks 0–3.
- Outputs: one clean candidate with every required accepted, planning, dirty-
  checkpoint, and repair-history source reachable.
- Focused validation: review-derived dashboard regressions passed 2/2; all eight
  remediated supervision compatibility tests passed; repaired implementation and
  product-revision focused tests passed.
- Mapped validation: dashboard server 143/143, dashboard web 117/117, production
  build, release owner 23/23, authoring 42/42, product-program 67/67, Factory
  Evolution dogfood, tracker verification, compilation, and diff checks passed.
  The full supervision run reached 523 tests with eight integration-fixture
  failures; all eight exact failures were corrected and rerun successfully.
- Candidate freeze: `253da9ac7695d7b504b1b3cf7ad7b876d21d05ac`; clean worktree
  and all required sources pass `merge-base --is-ancestor`.
- Remediation closure: independent review found two dashboard response-shape
  defects. Commit `2e58954` closes both, the exact regressions and full server
  suite pass, and the live Reports/run projections render without schema
  fallback. The earlier range-admission invocation defect is closed by
  `a08012f` and its exact eight-test set.
- Resource posture: generated `node_modules` and `dist` were moved to the macOS
  Trash after proof; they are reproducible and not part of the candidate.
- Independent review: the exact independent base review produced the two
  findings above and no others. Fresh post-remediation Codex review attempts
  failed before reading source because the user-wide review quota was exhausted;
  no review result was manufactured. Exact deterministic closure, full dashboard
  proof, and browser proof establish that neither reported finding remains open.
- Retained open work: automatic-release Blocks 5–7; systemic recovery Blocks
  0–6 after that dependency; product-program Blocks 5–11 with the selection-
  quality plan applied through the authoring owner.
- Browser/runtime proof: complete `/api/v1/health` using the frozen Codex 0.145
  adapter, plus Factory Floor, tracker list, task detail, run/lifecycle, and
  Reports views rendered from the integrated production build.

### Stop

Stop before updating `main`, pushing `origin/main`, or changing the installed
release.

---

## Block 5 — Publish canonical main and reconcile the installed release

Status: `completed`

### Objective

Make the accepted integrated candidate the local and remote canonical main and
ensure the installed Factory release is sourced from that history.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: operators and tasks resolve one current repository
  and installed-runtime source.
- Potential capability loss or regression: an unsafe main update or release
  cutover could strand work, bypass protection, or install unreviewed code.
- Protected-capability effect: preserve remote policy, non-force history,
  rollback-safe release activation, stable links, and fresh-process
  verification.
- Architecture and operating-model effect: `main`/`origin/main` and installed
  release become the canonical source/runtime pair.
- Tradeoff and source evidence: use a PR when protection requires it; otherwise
  a verified non-force update is the shortest correct path.

### Inputs and dependencies

- Block 4 accepted candidate.

### Required work

- Re-fetch and prove no unexpected remote-main advance; reconcile any advance
  through a new candidate rather than overwriting it.
- Push the integration branch and use the repository's permitted merge path.
- Update local `main` non-destructively to the merged remote head.
- If the active installed source is not reachable from the new main or the main
  source contains a newer accepted release correction, use the maintained
  release owner to promote the exact accepted main revision and verify it in a
  fresh process. Preserve the previous release for rollback.
- Close or merge every open PR according to its current exact disposition.

### Scope and non-goals

- In scope: GitHub merge/publication, local main alignment, and installed release
  reconciliation.
- Not in scope: deleting branches/worktrees or beginning deferred Blocks.
- Never force-push, edit the release symlink manually, or bypass a required
  review/protection gate.

### Deliverables and recorded state

- Identical local-main and origin-main SHA.
- Remote merge/PR receipt.
- Installed release status whose source commit is reachable from main.

### Resource and economy contract

Use one final remote-currentness fetch, one allowed publication path, and the
normal release owner's exact validation. Do not restage or re-promote an
already current tree-identical release.

### QA and independent review

Recheck remote ref, main ancestry, installed roots/links, and fresh-process
status after publication.

### Acceptance

- `main == origin/main` at the accepted candidate or its policy-compliant merge
  commit.
- No merge-ready PR remains open.
- The active release is healthy and its source is an ancestor of canonical
  main.

### Negative tests

- Reject a non-fast-forward overwrite, stale remote comparison, manual symlink
  change, or release source outside main.

### Completion evidence

- Repository commit: canonical `main` and `origin/main`
  `2109eeee46468a50c6c1c934628c4f033e7bb1fa`; publication used only
  non-force updates. The integration source `731fc346022b99c3d70dd8a8c3f841fab168ec1a`
  and every preservation parent are ancestors.
- External/domain revision or root: active release
  `2109eeee4646-fb7861d1f68b`, source commit `2109eeee46468a50c6c1c934628c4f033e7bb1fa`,
  post-swap verification root
  `8339924155057a190a421318304789a2d08b0b38d441c21dd1c6679374a8610d`.
- Inputs: frozen Block 4 candidate, one late six-file unaccepted automatic-
  release candidate preserved at `ca6173837d0c985222b9841247ddce4a2f7c3722`,
  and the remote `main` currentness check.
- Outputs: local `main == origin/main`; the late unaccepted candidate is an
  ancestry-only parent and has no tree effect; no open pull request remains.
- Focused validation: runtime-bound adaptive dogfood passed under its recorded
  system Python and explicitly skipped, rather than produced a false
  regression, under the release runner's Python 3.14. The strict underlying
  bounded-candidate runtime validator remains unchanged.
- Mapped validation: release-owner 23/23, tracker-authoring 42/42,
  tracker-execution 110 tests with only the same 18 accepted-baseline failures,
  and tracker-supervision 523/523 passed the maintained release owner.
- Candidate freeze: source `2109eeee46468a50c6c1c934628c4f033e7bb1fa`,
  unchanged throughout promotion and already pushed before activation.
- Remediation closure: the first promotion attempt failed closed because the
  new adaptive dogfood suite added a runtime-portability-only error. Commit
  `2109eee` makes that test runtime-aware without weakening the performance
  evidence validator; the second exact promotion completed.
- Resource posture: previous release `b5162c0ffac9-832677d54c7f` remains the
  release owner's rollback source; stable install links resolve to the newly
  verified release.
- Independent review: Block 4's exact combined-source review and finding
  closure remain applicable; the release owner independently admitted and
  activated only the exact pushed source after its full candidate/baseline
  comparison.
- Retained open work: branch and worktree cleanup in Block 6; dependency-
  ordered automatic-release, systemic-recovery, and product-program work in
  Block 7.
- Decision/continuation posture: publication is complete and deletion remains
  gated on fresh ancestry, dirt, and exact-ref proof.
- Post-block audit: accepted; current release source is exactly canonical main.
- Git durability: `main` push completed without force; GitHub reports only
  historical merged PR 1 and no open PR.

### Stop

Stop before removing a branch or worktree.

---

## Block 6 — Prune stale branches, worktrees, and pull-request residue

Status: `completed`

### Objective

Remove obsolete local and remote Git lanes only after proving their useful
state is preserved by canonical main or an explicit clean follow-on branch.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: cleanup removes redundant development topology after
  canonical publication; it does not change Factory behavior.

### Inputs and dependencies

- Block 5.
- Block 0 disposition ledger updated against published main.

### Required work

- Re-run exact ref ancestry/patch-equivalence and worktree-dirt checks.
- Remove clean detached and stale worktrees whose commits are preserved.
- Remove merged, superseded, rejected-only, or patch-equivalent local branches
  and their remote refs when no active task or follow-on lane owns them.
- Preserve the consolidation branch until its tracker evidence is committed and
  main contains it; preserve only the minimum active branches named in Block 7.
- Prune stale remote-tracking refs and confirm Git worktree metadata is clean.

### Scope and non-goals

- In scope: exact refs and worktrees listed in the accepted disposition ledger.
- Not in scope: supervision ledgers, Codex history, release directories, or
  unrelated repositories.
- Never force-remove a dirty worktree or delete an unmerged unique commit.

### Deliverables and recorded state

- Compact final branch/worktree inventory.
- Per-removed-ref/worktree preservation evidence.

### Resource and economy contract

Batch exact safe deletions after one currentness recheck. Stop immediately on a
new dirty path, moving ref, active task owner, or unique unpreserved commit.

### QA and independent review

A second read-only review must confirm the deletion set against published main
before the first deletion. Re-run inventory after cleanup.

### Acceptance

- No stale or redundant Software Factory worktree remains.
- No stale local/remote feature branch remains unless it owns explicit open work
  in Block 7.
- All retained worktrees are clean or have declared intentional state.

### Negative tests

- Reject deletion of a branch with unique unpreserved commits, a task-owned
  worktree, a dirty path, or a ref that moved after review.

### Completion evidence

- Repository commit: cleanup was performed only after published `main`
  `2e4e8fe5f04c24350568a3d45b441fbc53ba4568`; this tracker-only successor
  records the resulting topology.
- External/domain revision or root: GitHub has only `refs/heads/main` at
  `2e4e8fe5f04c24350568a3d45b441fbc53ba4568`; no open pull request exists.
- Inputs: 38 clean registered worktrees, 33 local feature branches, 23 remote
  feature branches, 18 completed/superseded Software Factory tasks and helper
  roles, and six paused obsolete heartbeat automations.
- Outputs: the 37 non-primary worktrees were removed; every local and remote
  feature branch was deleted; the primary checkout is the sole worktree on
  `main`; the 18 stale tasks are archived and the six stale automations are
  deleted.
- Focused validation: immediately before removal, every worktree was rechecked
  clean and its exact HEAD was proven an ancestor of `main`; immediately before
  each ref deletion, its exact tip was proven an ancestor of `main`. No force
  option, reset, history rewrite, or broad filesystem deletion was used.
- Mapped validation: `git fetch --prune origin`, `git ls-remote --heads origin`,
  local/remote `for-each-ref`, `git worktree list --porcelain`, and clean status
  now report only the primary `main` line and worktree.
- Candidate freeze: every removed tip remains reachable through the canonical
  main graph, including archival-only and unaccepted-candidate parents.
- Remediation closure: three branch-dependent generated dashboard directories
  became visible when the primary checkout switched to `main`. Reproducible
  `node_modules` (263 MiB), `dist` (1.3 MiB), and `test-results` (4 KiB) were
  moved recoverably to timestamped paths in the macOS Trash; source remained
  clean.
- Resource posture: repository topology is reduced to one branch and one
  worktree until Block 7 proves a dependency-safe successor lane is useful.
- Independent review: Block 4's independent combined-source review established
  the preservation set. The required second read-only deletion review rebuilt
  the complete ref/worktree manifest from published main and found zero dirty
  or unpreserved targets before the first deletion.
- Retained open work: no stale lane remains. Substantive intended work is
  retained in canonical tracker files and assigned in Block 7.
- Decision/continuation posture: safe to create at most one fresh eligible
  implementation lane from current main; dependency-blocked lanes remain
  dormant with explicit triggers.
- Post-block audit: accepted; primary repository is clean on `main`, with one
  worktree and no feature ref locally or remotely.
- Git durability: all removed tips were already ancestors of pushed main; task
  archiving and Trash moves are recoverable.

### Stop

Stop before starting work in new follow-on lanes.

---

## Block 7 — Recreate clean lanes and resume intended remaining work

Status: `not-started`

### Objective

Give each intended unfinished Factory program one dependency-correct clean
branch/worktree and exact task/tracker owner based on the new main.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: remaining work resumes without old-base drift,
  duplicate writers, or user scheduling.
- Potential capability loss or regression: premature resumption could bypass a
  tracker dependency or split one owner across multiple lanes.
- Protected-capability effect: preserve full requested ranges, accepted Blocks,
  independent review boundaries, and single-writer ownership.
- Architecture and operating-model effect: short-lived clean lanes consume
  canonical main and merge back through the ordinary path.
- Tradeoff and source evidence: create only lanes with current dependency-safe
  work; keep others recorded and dormant without losing scope.

### Inputs and dependencies

- Block 6.

### Required work

- Amend/rebase the systemic supervision recovery tracker against the accepted
  automatic-release source, preserve its planning status, and start its first
  dependency-safe Block in one clean lane when eligible.
- Rebase/port product-program accepted state and resume Blocks 5–11 in one clean
  lane when its tracker range and supervision authority are current.
- Place selection-quality RSI work in the product-program lane or one separate
  lane only if its tracker proves independent ownership and dependencies.
- Complete any automatic-release Blocks still remaining after Block 1 in the
  existing canonical task or one clean lane, never both.
- Route exact resume/start actions through maintained task/supervision owners,
  then verify actual work begins at the correct frontier.

### Scope and non-goals

- In scope: tracker amendments needed for the new source baseline, branch and
  worktree creation, task routing, and first-work verification.
- Not in scope: duplicating lanes, starting dependency-blocked work, or claiming
  later tracker completion in this Block.
- Do not create a new task unless direct task-creation authority and technical
  isolation require it; reuse the current task by default.

### Deliverables and recorded state

- Minimal active branch/worktree/task map.
- Current tracker/range binding and verified first-work evidence for each active
  lane.
- Explicit dormant disposition and revisit trigger for each deferred lane.

### Resource and economy contract

Create at most one writer lane per tracker and reuse current accepted commits
and evidence. Starting the first exact work item is sufficient; do not implement
all follow-on Blocks inside this consolidation Block.

### QA and independent review

Verify each new branch is based on canonical main, each worktree is clean, each
task points at the exact intended tracker/frontier, and no two tasks share a
writable source.

### Acceptance

- Every intended unfinished workstream is either actively progressing on one
  clean eligible lane or truthfully dormant behind an exact dependency/revisit
  trigger.
- No user `Resume` action or branch scheduling is required.

### Negative tests

- Reject an old-base branch, duplicate writer, unbound full-tracker scope,
  dependency skip, or handoff without verified first-work start.

### Completion evidence

Pending.

### Stop

Stop before claiming repository-wide steady state.

---

## Block 8 — Verify the repository-wide steady state

Status: `not-started`

### Objective

Independently prove that the repository, release, dashboard, trackers, tasks,
branches, and worktrees now form one coherent operating state.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block verifies the completed operating state and
  records no new feature behavior.

### Inputs and dependencies

- Block 7.

### Required work

- Re-read `main`, `origin/main`, installed release, PRs, all local/remote
  branches, all worktrees, active Software Factory tasks, tracker statuses, and
  dashboard runtime from current sources.
- Verify all active branches descend from main, each has one writer, every
  dormant item has a revisit trigger, and no accepted useful work remains only
  on a stale ref.
- Build or reuse the exact current dashboard build, start one runtime, verify
  health and affected browser views, and stop any duplicate old runtime.
- Obtain independent observable-outcome review of this tracker's completion.

### Scope and non-goals

- In scope: final currentness and outcome proof plus narrow correction of a
  discovered consolidation defect.
- Not in scope: continuing the substantive follow-on trackers beyond their
  verified first frontier.
- Do not turn optional future improvements into completion blockers.

### Deliverables and recorded state

- Final exact task/ref/worktree/release/dashboard manifest.
- Independent outcome review and truthful retained-open-work list.

### Resource and economy contract

Use one bounded currentness sweep and one affected browser pass. Widen only for
a mismatch in the manifest.

### QA and independent review

Independent review must reconstruct the requested outcome from the direct user
request and inspect operator-visible Git, runtime, and task state.

### Acceptance

- Local/remote main and installed release are coherent.
- Dashboard and maintained control-plane proof pass from the canonical source.
- Only current intended branches/worktrees/tasks remain, with no duplicate
  writer or orphaned accepted work.
- Every retained open item is assigned to a current owner and compatible with
  the completed consolidation outcome.

### Negative tests

- Reject completion based only on merged commits, passing tests, tracker status,
  or a clean `git status` when runtime, task, release, or retained-work state is
  inconsistent.

### Completion evidence

Pending.

### Stop

Stop after the repository-wide outcome is independently verified and no
consolidation work remains.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| One writer and complete lossless inventory | 0 | 1–7 | 8 |
| Current automatic-release/control-plane source | 1 | 4–5 | 8 |
| Completed dashboard preserved and runnable | 2 | 4–5 | 8 |
| Accepted product-program work preserved | 3 | 4–5 | 8 |
| Exact integrated validation/review | 4 | 5 | 8 |
| Local/remote main and installed release coherence | 5 | 6–7 | 8 |
| Stale branch/worktree cleanup without loss | 6 | 7 | 8 |
| Clean dependency-correct follow-on work | 7 | — | 8 |

## 9. Final completion definition

The tracker is complete only when Blocks 0–8 are accepted at exact current
revisions; the integrated candidate is published as both local and remote main;
the installed release source is healthy and reachable from main; the dashboard
runs correctly from that source; all stale branches/worktrees/PRs are removed
without losing useful state; every intended unfinished workstream is either
verified active on one clean lane or truthfully dormant behind an exact
dependency and revisit trigger; and independent outcome review finds no
repository-wide coordination or synthesis gap.
