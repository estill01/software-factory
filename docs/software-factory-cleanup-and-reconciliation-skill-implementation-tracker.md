# Software Factory Cleanup and Reconciliation Skill Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–9
- Repository: `/Users/ethanstillman/code/software_factory`
- Governing objective: Direct-user requirements in task
  `019ffc82-86de-74e2-bdfb-a23403da5c2f` to provide one easy periodic Software
  Factory cleanup skill that reconciles accepted work onto canonical `main`,
  dispositions pull requests, safely retires stale branches and worktrees,
  preserves all useful code and functionality, coordinates running work through
  the supervisor, and restarts unfinished work without user scheduling.

## 1. Purpose and intended outcome

Create and release one `clean-software-factory` skill that a user may invoke
directly and that the existing supervisor may route to a dedicated cleanup
owner when repository drift requires reconciliation. The skill must inspect one
exact Git repository, select a non-disruptive or coordinated path from current
task ownership, preserve every potentially useful candidate, integrate only
accepted work, publish and verify canonical `main`, retire only proven redundant
development topology, and return unfinished work to one writer per fresh lane.

Completion means:

- `$clean-software-factory` is installed through the normal Software Factory
  release owner and one invocation completes the appropriate audit, safe-clean,
  or coordinated-reconciliation path without requiring the user to orchestrate
  Git, pull requests, tasks, or worktrees manually;
- direct-user invocation and supervisor routing are the only entry owners;
  authoring, implementation, product-evolution, and release workflows may emit
  an exact cleanup-needed signal but never start a competing repository writer;
- affected running tasks checkpoint and pause through their existing owner,
  unaffected work may continue, and exactly one cleanup writer mutates the
  target repository under a current supervisor quiescence gate;
- every pre-cleanup branch, worktree, pull request, stash, unique commit, staged
  change, unstaged change, relevant untracked or ignored file, and detached
  candidate has an exact disposition in a no-loss manifest;
- no artifact is retired until both byte preservation and functional/capability
  preservation are established, with `unknown` always resolving to `retain`;
- accepted work and current pull-request dispositions converge on local
  `main == origin/main`, mapped validation passes, and the final repository state
  is independently reviewed at the exact published revision;
- stale branches and worktrees are retired only after a current deletion gate,
  restore proof, and exact revalidation immediately before each effect; and
- every unfinished intended workstream is either verified progressing from the
  normalized main revision with one writer or truthfully dormant behind an exact
  dependency and revisit trigger.

### Mission frame

- Primary outcome: periodic repository consolidation becomes one safe,
  autonomous Software Factory capability that reduces branch/worktree/PR drift
  without losing useful source, functionality, evidence, or intended work.
- Observable completion: a released skill and supervisor-monitored dogfood show
  inventory, preservation, accepted integration, PR disposition, validation,
  non-force publication, deletion gating, topology cleanup, and effective task
  restart from one exact run, including no-loss rejection cases.
- Ordinary effect classes needed: skill authoring, deterministic Git and provider
  inspection, cleanup-owned artifact production, supervisor event/gate changes,
  task checkpoint routing, accepted Git integration, pull-request operations,
  validation, non-force publication, safe ref/worktree retirement, task restart,
  documentation, exact review, release promotion, and role refresh.
- Hard direct authority or safety boundaries: preserve user-owned and in-flight
  state; do not infer acceptance from commits, ancestry, tests, branch age, or PR
  labels; never force-push, force-remove a worktree, run broad `git clean`, invoke
  destructive garbage collection, bypass branch protection, push unknown or
  sensitive dirty bytes, let a supervisor write a target repository, or delete
  an artifact with incomplete no-loss proof.
- Material goal alteration or reversal: making cleanup silently destructive,
  allowing scheduled audit to pause healthy work, merging unaccepted code,
  weakening independent deletion review, replacing existing Git/task/release/
  supervision owners, or treating preservation as permission to abandon intended
  functionality requires renewed direct authority.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker adds a new released skill and changes the
  Factory operating model for repository integration, live-task coordination,
  branch/worktree retirement, and post-cleanup continuation.
- Direct product sources: the direct-user requirements summarized above;
  `README.md`; `clean-software-factory` discussion in this task;
  `docs/software-factory-repository-consolidation-implementation-tracker.md`;
  `docs/software-factory-systemic-supervision-recovery-implementation-tracker.md`;
  `docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md`;
  `supervise-tracker-runs/SKILL.md`;
  `supervise-tracker-runs/references/supervision-policy.md`;
  `implement-tracker-blocks/SKILL.md`; and
  `docs/software-factory-skill-releases.md` at the current implementation
  baseline.
- Product thesis and intended effect: autonomous implementation needs an equally
  reliable convergence path. A repository should return periodically to one
  trustworthy main line and a minimal set of intentional lanes without turning
  active work or uncertain source into collateral cleanup loss.
- Protected capabilities: complete direct implementation ranges; accepted and
  rejected history; user-owned dirty work; useful experimental or deferred
  source; semantic functionality; exact owner-specific acceptance; one writer
  per lane; non-force Git history; pull-request review/protection; supervisor
  read-only boundaries; release rollback; dashboard projections; no manual
  Resume; and truthful retained-open-work state.
- Architecture strategy: add one cleanup skill and one derived repository-
  reconciliation lifecycle in the existing supervision event owner. The cleanup
  skill is the sole repository mutation owner; the supervisor discovers and
  coordinates tasks, gates quiescence/deletion/outcome, and verifies restart;
  Git/GitHub, task, tracker, validation, and release owners remain canonical.
- Requested capability: one easy invocation that safely audits, consolidates,
  validates, cleans, and resumes one exact repository, automatically selecting
  the non-disruptive or coordinated path from live ownership.
- Proportionality: prose-only instructions are inadequate for destructive Git
  currentness and no-loss proofs, while a daemon, branch service, generalized
  provider platform, or second task database would duplicate authority. One
  concise skill, one deterministic helper/artifact owner, and bounded additions
  to the existing supervisor are the smallest complete implementation.
- Tradeoffs: fail-closed retention leaves some uncertain artifacts temporarily
  archived, and coordinated cleanup briefly pauses overlapping work; this costs
  less than silent source/functionality loss or conflicting integration writers.
- Uncertainty: direct sources do not define an arbitrary retention duration,
  authorize pushing sensitive local bytes, guarantee all Git hosting providers,
  or permit automatic semantic acceptance. Uncertain artifacts remain retained,
  and provider-specific mutation is limited to the configured supported owner.

## 2. Target architecture and authority boundaries

```text
direct user request OR supervisor-supported cleanup need
                         |
                         v
              clean-software-factory owner
                         |
       read-only inventory + exact disposition plan
                         |
        active overlapping repository writers?
              | no                    | yes
              v                       v
        safe path          supervisor routes checkpoint/pause
                                      |
                            owner-produced preservation receipts
                                      |
                            supervisor quiescence gate
                              \       |       /
                               v      v      v
                 preserve -> integrate/PR -> validate/publish
                                      |
                           supervisor deletion gate
                                      |
                        retire redundant refs/worktrees
                                      |
                           supervisor outcome gate
                                      |
                   restart unfinished work from current main
                                      |
                         verify actual first useful work
```

Authority rules:

1. The cleanup task is the sole writer for cross-lane repository integration and
   retirement during a coordinated run. It cannot manufacture task, tracker,
   review, PR, release, or product acceptance.
2. Existing implementation tasks own their checkpoints, tracker evidence, and
   candidate semantics. The cleanup owner consumes exact receipts; it does not
   edit another task's tracker to make work mergeable.
3. `supervise-tracker-runs` owns changed-state observation, cross-thread routing,
   operation-specific holds, quiescence/deletion/outcome gates, semantic no-loss
   review, and restart-effectiveness review. Supervisors remain read-only against
   the target repository.
4. The cleanup helper owns immutable run artifacts and deterministic Git/provider
   projections. The existing supervision event ledger stores content-minimized
   roots and transitions; neither artifact set becomes source-code or acceptance
   authority.
5. Git owns commits/refs/worktrees; the configured hosting provider owns pull
   requests and protected-branch effects; the task owner owns task lifecycle;
   `scripts/skill_release.py` alone installs Factory skills.
6. Mechanical reachability is necessary but insufficient for deletion. A
   separate semantic reviewer must verify that candidate functionality is
   integrated, explicitly preserved, reproducible, or validly superseded.
7. Scheduled operation is audit-first. It cannot pause writers or mutate a
   repository merely because a timer fired.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Git repository identity, commits, refs, worktrees, stashes, status, and publication | Git plus the exact configured remote | reuse; no history rewrite |
| Pull-request discovery, review status, merge/close, and branch protection | Configured Git hosting owner; GitHub through existing `gh` capability for this repository | reuse; no provider-general service |
| Task identity, status, and task turns | Existing Codex/App Server task owner | reuse through supervisor routing |
| Tracker range, accepted Blocks, and remaining frontier | `implement-tracker-blocks` plus the canonical range/control owners in `supervise-tracker-runs` | reuse; never infer from Git |
| Changed-state monitoring, incidents, routing, operation holds, lifecycle, and effectiveness | `supervise-tracker-runs/SKILL.md`, policy, and `scripts/supervision_log.py` | adapt with one derived repository-reconciliation lifecycle |
| Skill structure and validation | System Skill Creator plus the repository's existing skill directory convention and fixed validator | reuse |
| Skill staging, activation, installed roots, rollback, and running-role refresh | `scripts/skill_release.py` and accepted automatic-release/supervisor-refresh owner | adapt the exact current skill set by one skill |
| Repository/test currentness and operator projection | Existing repository tests and dashboard generic projections | reuse; add no dashboard authority unless a focused failing contract requires it |
| Historical one-time consolidation behavior | Completed repository-consolidation tracker and its exact Git evidence | adapt into reusable fixtures/contracts; do not treat the historical run as the runtime owner |

## 4. Prior-work and source-adaptation map

This is the authoring snapshot. Block 0 must re-read every mutable identity and
replace stale values before implementation.

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Canonical Software Factory main and completed consolidation outcome | `f4e9108c25cb53ffa65396b5739dedaa2e882cd8` | adapt | 0–9 | Extract generic invariants and dogfood cases; do not duplicate one-time evidence |
| Completed repository-consolidation tracker | `docs/software-factory-repository-consolidation-implementation-tracker.md` at `f4e9108` | adapt | 0, 1, 2, 4–6, 9 | Generalize inventory, preservation, integration, cleanup, and restart behavior |
| Active automatic-release Block 5 worktree | branch `codex/automatic-release-monitor-refresh` at `f4e9108`, with four modified supervision files at authoring time | preserve/wait | 0, 3, 8 | Checkpoint and integrate through its own tracker before overlapping cleanup implementation, or prove exact non-overlap and one-writer ownership |
| Automatic release and supervisor refresh tracker | Blocks 0–4 accepted, Block 5 `in-progress`, Blocks 6–7 `not-started` at `f4e9108` | reuse-if-current | 0, 3, 8 | Consume accepted promotion/refresh/rollback behavior; never implement a substitute here |
| Systemic supervision recovery tracker | Blocks 0–6 `not-started` at `f4e9108` | adapt without duplication | 0, 3, 6, 9 | Reuse Factory-owned recovery/routing semantics if accepted first; keep cleanup no-loss lifecycle independently owned |
| Active installed three-skill release | `2109eeee4646-fb7861d1f68b`, source `2109eeee46468a50c6c1c934628c4f033e7bb1fa` | reuse/migrate | 0, 8, 9 | Add the cleanup skill through the exact live release set while preserving rollback |
| Existing release owner | `scripts/skill_release.py` at `f4e9108`, exact three-skill manifest | adapt | 8 | Add one exact skill without generalized discovery or count-specific stale errors |
| Existing implementation skill | `implement-tracker-blocks/SKILL.md` at `f4e9108` | adapt narrowly | 7 | Emit cleanup-needed signals only at supported admission/terminal boundaries |
| Existing supervision skill/policy/helper | `supervise-tracker-runs/` at `f4e9108` | adapt after active writer reconciliation | 3, 6–9 | Add coordination and monitoring without repository-write authority |
| GitHub state | `origin/main` and local `main` at `f4e9108`; historical merged PR 1 and no open PR at authoring time | fixture/currentness input | 1, 4, 9 | Re-read through configured provider before every live operation |

## 5. Scope, non-goals, and proportionality

### In scope

- One exact Git repository per cleanup run, with canonical repository-root,
  common-dir, main branch, configured remote, provider, and task ownership.
- Read-only inventory of refs, remote refs, worktrees, detached heads, stashes,
  dirty tracked state, relevant untracked/ignored state, PRs, and active tasks.
- Automatic selection between audit-only, non-disruptive safe cleanup, and
  supervisor-coordinated reconciliation.
- Exact preservation, accepted integration, conflict/PR disposition, mapped
  validation, non-force main publication, safe retirement, and effective restart.
- Direct invocation, supervisor routing, narrow cleanup-needed signals, skill
  release, documentation, deterministic fixtures, and released dogfood.

### Out of scope

- A background daemon, new scheduler, general repository registry, branch
  database, task database, Git server, provider abstraction, dashboard status
  authority, or second supervision ledger.
- Automatically deciding whether unreviewed code is good, accepting tracker
  Blocks from Git evidence, merging every PR, or treating old age as staleness.
- Cross-repository atomic transactions, arbitrary Git hosting providers,
  production deployment, credential management, or secret scanning platform.
- Force push, force worktree removal, broad file deletion, `git gc`/prune of
  objects, or automatic expiration of preservation artifacts.
- Modifying unrelated repositories or deleting supervision/release/task history.

### Proportionality

Use one concise skill, one deterministic phase/resume helper, existing Git and
provider owners, one derived supervisor lifecycle, and the existing release
pipeline. Preserve uncertain work rather than adding generalized classification
or security machinery. Add dashboard code only if a focused regression proves
that existing generic event projection cannot represent the cleanup outcome.

## 6. Block execution contract

1. Execute Blocks 0–9 in dependency order.
2. Before Block 0 implementation, re-read all worktrees and active tasks. Do not
   edit `supervise-tracker-runs` or release-owner surfaces while another task has
   uncheckpointed overlapping work. Route that task to checkpoint/integrate or
   preserve it, then begin from the resulting canonical main.
3. Use one implementation writer for this tracker and one cleanup writer per
   dogfood/live run. Supervisors, reviewers, and existing implementation lanes
   remain read-only outside their own owners.
4. Preserve unrelated, staged, unstaged, untracked, ignored, detached, rejected,
   deferred, and in-flight work. Never reset, rewrite, broadly stage, or sweep a
   mixed worktree.
5. Treat every potentially useful artifact as `retain` until an exact disposition
   proves `integrated`, `preserved`, `validly-superseded`, or
   `generated-reproducible`. Unknown never becomes deletion eligibility.
6. Require both byte-level preservation and semantic/capability preservation.
   Commit ancestry or patch equivalence alone cannot establish that conflict
   resolution preserved a route, API, migration, configuration, test, UI flow,
   bug fix, tracker evidence, or future option.
7. Keep raw inventory/manifests with the cleanup artifact owner and only
   content-minimized identities/roots/transitions in the supervision ledger.
   Neither becomes an alternate Git, PR, tracker, task, or acceptance owner.
8. Any ref, worktree, task, PR, or remote-head change after a gate invalidates
   that gate. Replan from current state; never continue from a stale deletion set.
9. Run likely-mutating integration and semantic review before final mapped
   validation. Freeze the candidate revision before exact validation/review and
   rerun only invalidated proof after a correction.
10. Use non-force Git/provider operations through configured owners. A provider
    unavailable or ambiguous result leaves the PR/ref retained and the owning
    phase open; it does not authorize a local substitute.
11. Scheduled use is audit-first and silent on unchanged state. Consequential
    reconciliation requires an exact current user or tracker mission plus the
    supervisor coordination gates; no timer creates destructive authority.
12. Record each operation hold with exact repository/effect scope, expiry on any
    relevant source/owner change or run completion, successor posture, and
    `carry-forward: false`.
13. Audit and accept each Block before advancing. A Block Stop is an internal
    boundary for a full-tracker implementation request, not a user scheduling
    point.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- External/domain revision or root: `<release, supervisor, provider, task, or not-applicable>`
- Inputs: `<paths, refs, worktrees, PRs, tasks, versions, and hashes>`
- Outputs: `<skill files, artifacts, events, manifests, refs, or runtime result>`
- Focused validation: `<commands and results>`
- Mapped validation: `<plan, commands, and results>`
- Candidate freeze: `<commit/content root and whether it changed afterward>`
- Remediation closure: `<finding-to-change-to-proof matrix or not-applicable>`
- Resource posture: `<inventory/read/test/route bounds and widening>`
- Independent review: `<exact-revision or run-root evidence>`
- Retained open work: `<items or none>`
- Decision/continuation posture: `<holds, safe frontier, restart, or not-applicable>`
- Post-block audit: `<accepted, reopened, or blocked with reason>`
- Git durability: `<commit, push, main, and preservation posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Freeze the cleanup contract, live owner baseline, and regression fixtures | — | `completed` |
| 1 | Build the cleanup skill and deterministic read-only inventory/plan | 0 | `not-started` |
| 2 | Implement no-loss preservation and functional coverage proof | 1 | `not-started` |
| 3 | Add supervisor reconciliation coordination and monitoring gates | 2 | `not-started` |
| 4 | Implement accepted integration, PR disposition, validation, and main publication | 3 | `not-started` |
| 5 | Implement independently gated branch/worktree retirement | 4 | `not-started` |
| 6 | Restore unfinished work and verify effective restart | 5 | `not-started` |
| 7 | Wire the simple invocation and cleanup-needed signal contract | 6 | `not-started` |
| 8 | Freeze, review, integrate, release, and refresh the complete skill set | 7 | `not-started` |
| 9 | Dogfood the released lifecycle and close from observable no-loss outcome | 8 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9`

## Block 0 — Freeze the cleanup contract, live owner baseline, and regression fixtures

Status: `completed`

### Objective

Establish one current, non-overlapping implementation baseline and one exact
contract/fixture set for safe repository reconciliation before creating the new
skill or changing supervision.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block freezes source identity,
  ownership, schemas, failure cases, and dependencies; it adds no cleanup or
  supervisor runtime behavior.

### Inputs and dependencies

- Current main, remote refs, worktrees, installed release, active tasks, tracker
  statuses, and the sources in the prior-work map.
- The active automatic-release Block 5 candidate must be accepted/integrated,
  cleanly checkpointed and quiescent, or proven exactly non-overlapping before
  any shared supervision/release file is edited.

### Required work

- Re-read current Git, task, tracker, PR, release, and installed-root identities;
  replace stale authoring-snapshot values in the implementation brief.
- Reconcile all existing writers of `supervise-tracker-runs`,
  `implement-tracker-blocks`, `scripts/skill_release.py`, and related tests.
- Freeze the minimum cleanup run schema: repository identity, source snapshot,
  active-owner snapshot, artifact inventory, disposition, preservation,
  capability coverage, integration, validation, publication, deletion, restart,
  and outcome identities.
- Translate the completed consolidation into content-minimized fixtures for:
  clean redundant work, unique committed work, dirty/untracked work, detached
  work, a moved ref, open/superseded/merge-ready PRs, active overlapping writers,
  conflict resolution that drops functionality, interrupted cleanup, and
  restart.
- Map each effect and decision to the existing owner before allowing a new
  helper field or event transition.

### Scope and non-goals

- In scope: current baseline, owner map, contract/reference, fixtures, and exact
  dependency/admission posture.
- Not in scope: skill execution, repository mutation, supervisor policy changes,
  release migration, or cleanup of the live repository.
- Do not copy task transcripts, private project content, credentials, or
  historical user files into fixtures.

### Deliverables and recorded state

- `clean-software-factory/references/repository-reconciliation-contract.md`.
- Minimal de-projectized fixtures and one source-adaptation/currentness record.

### Resource and economy contract

Use one bounded currentness sweep and only the exact active owner/source files.
Reuse the completed consolidation's generic evidence; do not rescan archived
tasks or historical repositories without a concrete missing identity.

### QA and independent review

Mechanical schema/fixture checks and independent review that the contract covers
both lost bytes and lost functionality without creating duplicate authority.

### Acceptance

- One current baseline has no overlapping unpreserved writer, and the fixture/
  owner map covers every supported cleanup state and no-loss boundary.

### Negative tests

- Reject a baseline with an uncheckpointed overlapping writer, copied protected
  content, caller-selected task/acceptance state, missing dirty/untracked case,
  or ancestry-only definition of preservation.

### Completion evidence

- Repository commit: `e58000fa6894de1452506a000073caf201430082`;
  rejected predecessor commits `e39f3add00234c83ae224805549948c8b3a66aa7`,
  `0885b15c94f35c1c453e0752839da0ee9d8c4622`,
  `d88811d86b032df69db216b7c8cc2e35802dc508` remain in history.
- External/domain revision or root: provider open-PR payload
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`;
  installed release `2109eeee4646-fb7861d1f68b`; currentness root
  `958c6abafac2b1d2da2bfd4267fd193ea993a8eb71516504e758e4d4ea8c7c11`.
- Inputs: `origin/main` `fe2d0c643549239fbe65acd0823520a9fa809540`,
  automatic-release owner task `019ffd59-10b3-73a0-a644-15c5e6ca9db6`
  at committed head `0b97d661bb8e108963aa34ecaaaa992176f104d6`, four
  worktrees, no open PRs, and exact Git/provider/release observation envelopes.
- Outputs: the reconciliation contract, exact machine schema, content-minimized
  15-case fixture, source-adaptation/currentness record, and contract tests.
- Focused validation: `python3 -m unittest
  clean-software-factory/scripts/test_reconciliation_contract.py` passed 5/5;
  JSON parsing, Python compilation, bind-field audit, hostile combined mutation
  rejection, and `git diff --check` passed.
- Mapped validation: all Block 0 schema, byte/functionality, unknown-retain,
  protected-content, owner-boundary, active-writer, and Stop criteria mapped to
  the five-test suite and exact semantic review.
- Candidate freeze: commit `e58000fa6894de1452506a000073caf201430082`,
  pushed unchanged to `origin/codex/clean-software-factory`.
- Remediation closure: stale source/provider envelope, mutation-fragile tests,
  aggregated PR outcomes, and incomplete owner/schema findings were closed at
  `0885b15`; missing typed dependency roots, under-specified deletion identity,
  unknown-loss eligibility, and hostile nested mutations were closed at
  `e58000f`, with all rejected revisions retained.
- Resource posture: one bounded Git/provider/release/task sweep plus current
  nonoverlap read; no historical task rescan and no repository mutation beyond
  this contract/tracker lane.
- Independent review: reviewer session
  `019ffee6-0453-7d71-95f3-e66eb5fd6043` accepted exact `e58000f` with no
  findings after rerunning the permanent tests and independent semantic probes.
- Retained open work: Blocks 1–9; automatic-release Block 6 remains active and
  owns seven current dirty paths with zero cleanup-lane overlap; local `main`
  movement invalidates reuse of the recorded baseline and requires reread before
  any shared edit.
- Decision/continuation posture: continue through Blocks 1–2 only in the new
  cleanup tree; hold shared supervisor/release/implementation-skill edits until
  the upstream lane is accepted, published, quiescent, and this lane is rebased.
- Post-block audit: accepted; Block 0 Stop adhered and no skill entry point,
  runtime helper, supervisor policy, release owner, or live cleanup effect was
  created.
- Git durability: accepted commit and evidence predecessors pushed; worktree
  clean before this acceptance-record update.

### Stop

Stop before creating the new skill entry point or inventory helper.

---

## Block 1 — Build the cleanup skill and deterministic read-only inventory/plan

Status: `not-started`

### Objective

Provide one valid `clean-software-factory` skill whose initial phase deterministically
inventories one exact repository and produces a current, resumable disposition
plan without mutation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one easy skill invocation turns an ambiguous Git/task
  topology into an exact bounded cleanup plan.
- Potential capability loss or regression: incomplete discovery could label
  useful or active work stale before preservation.
- Protected-capability effect: preserves current Git/provider/task ownership,
  user-owned dirty state, and read-only planning before consequential effects.
- Architecture and operating-model effect: adds one skill and deterministic
  cleanup artifact owner; no daemon, repository registry, or second task owner.
- Tradeoff and source evidence: comprehensive current inventory costs one bounded
  repository/provider/task sweep, which is justified before any destructive
  decision; unchanged scheduled checks remain cheap.

### Inputs and dependencies

- Block 0 contract, fixtures, and current exact repository identity.
- System Skill Creator structure and the repository's existing skill conventions.

### Required work

- Scaffold `clean-software-factory/` with a concise `SKILL.md`, matching
  `agents/openai.yaml`, one referenced contract, deterministic scripts, and only
  necessary fixtures/tests.
- Define metadata triggers for direct requests to clean, consolidate, normalize
  main, reconcile PRs, remove stale branches/worktrees, or safely coordinate
  repository cleanup. One invocation chooses audit, safe, or coordinated behavior
  from evidence; the user does not manage internal phases.
- Implement a deterministic helper with immutable/resumable run identity and
  bounded phases for inventory, plan, status, verification, and later exact
  effects. Public inputs must use a canonical absolute repository top level and
  expected main/remote/provider owners.
- Inventory local/remote refs, worktrees, detached heads, stashes, staged/
  unstaged/untracked state, relevant ignored state for removable worktrees,
  submodule/LFS posture when present, PRs, and supervisor-derived task ownership.
- Produce exact dispositions only as proposals. `unknown`, unavailable provider,
  ambiguous remote/main, moving source, or missing task owner remains `retain`
  and prevents mutation.
- Make identical current inputs return the same plan/root and interrupted runs
  resume the same phase rather than opening a duplicate run.

### Scope and non-goals

- In scope: skill interface, run artifact owner, read-only discovery, planning,
  currentness, and deterministic resume.
- Not in scope: preservation writes, merges, PR mutation, branch/worktree
  deletion, task pause, or release installation.
- Do not add a background service, provider plugin framework, global repository
  catalog, or user-facing configuration language.

### Deliverables and recorded state

- Valid skill tree, deterministic inventory/plan helper, fixtures, tests, and
  immutable plan/status artifacts.

### Resource and economy contract

One repository/root resolution, one local Git inventory, one remote/provider
inventory, and one compact task-owner read per changed source snapshot. Use cheap
ref/status fingerprints to no-op unchanged periodic audits; widen to ignored or
unreachable-object inspection only for worktrees/refs proposed for retirement.

### QA and independent review

Skill validation, unit/fixture tests, canonical-path/symlink/bounds tests, and
independent review of discovery completeness and mutation-free behavior.

### Acceptance

- One invocation produces a deterministic complete plan or a truthful retained
  ambiguity, and no read-only path changes Git, provider, task, or supervisor
  state.

### Negative tests

- Reject non-top-level/symlink/root repositories, multiple ambiguous remotes,
  moving refs, omitted stashes or dirty state, unavailable PR/task ownership
  presented as clean, oversized/malformed artifacts, and any planning mutation.

### Completion evidence

Pending.

### Stop

Stop before preserving candidate bytes or asking the supervisor for quiescence.

---

## Block 2 — Implement no-loss preservation and functional coverage proof

Status: `not-started`

### Objective

Ensure every potentially useful candidate is durably recoverable and every
claimed integration/supersession preserves its functionality before any ordinary
branch or worktree can become deletion-eligible.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: cleanup can reduce topology without destroying code,
  behavior, evidence, or future implementation options.
- Potential capability loss or regression: a reachable commit, patch-equivalent
  diff, or green test can hide functionality removed by conflicts, reverts, or
  incomplete validation.
- Protected-capability effect: preserves exact bytes, provenance, intended
  behavior, deferred work, rejected history, and user-controlled sensitive data.
- Architecture and operating-model effect: adds cleanup-owned immutable
  preservation/no-loss artifacts and semantic review inputs; Git and existing
  reviewers remain authoritative.
- Tradeoff and source evidence: uncertain artifacts consume archival space and
  remain retained, deliberately favoring recoverability over aggressive pruning.

### Inputs and dependencies

- Block 1 current inventory and proposed dispositions.

### Required work

- Define the exhaustive no-loss manifest mapping every pre-cleanup artifact to
  `integrated`, `preserved`, `validly-superseded`,
  `generated-reproducible`, or `retain`; allow no implicit/missing disposition.
- Preserve committed history through exact refs or bundles and preserve staged,
  unstaged, untracked, and necessary ignored bytes through a restrictive local
  package/manifest that does not silently push unknown or sensitive content.
- Record byte hashes, modes, paths, origins, object IDs, PR/task/tracker links,
  preservation location, restore command/owner, and durability posture.
- Perform a restore drill into a disposable location before the preservation
  receipt can pass.
- Build a bounded capability coverage map for unique candidates: affected
  routes/APIs, migrations, configuration, UI flows, tests, fixes, tracker or
  review evidence, and explicitly deferred options. Compare those effects with
  resulting main or the preservation package.
- Require independent semantic review for `validly-superseded` and for any
  integration whose conflict/rewrite could change behavior. A cleanup writer
  cannot self-attest functional equivalence.
- Keep preservation refs/packages outside ordinary active branch/worktree lists;
  never expire them automatically in this tracker.

### Scope and non-goals

- In scope: exact preservation, restore proof, no-loss manifest, capability map,
  and semantic disposition review.
- Not in scope: deciding unreviewed product merit, publishing sensitive bytes,
  merging source, deleting refs/worktrees, or adding a secret-management system.
- Do not treat Git reachability, `patch-id`, test success, or reviewer prose alone
  as complete functional preservation.

### Deliverables and recorded state

- Immutable preservation packages/refs, restoration receipts, exhaustive no-loss
  manifests, and capability-coverage review packets.

### Resource and economy contract

Hash/package each unique byte/object once per source snapshot, batch coherent
artifacts by owning candidate, and reuse unchanged roots. Run capability review
only for unique or semantically changed candidates, not already identical trees.

### QA and independent review

Adversarial restore tests plus a distinct semantic reviewer covering dropped
route/API/config/migration/UI/test/evidence and unknown-retain cases.

### Acceptance

- Every candidate can be restored byte-for-byte or is already present exactly;
  every proposed supersession/integration has current functional coverage; and
  any uncertainty remains retained and deletion-ineligible.

### Negative tests

- Reject missing untracked/ignored bytes, bundle/ref mismatch, unrestorable
  archives, sensitive-content remote push, conflict-dropped functionality,
  passing tests with an unmapped capability, self-reviewed supersession, and
  unknown converted to deletion eligibility.

### Completion evidence

Pending.

### Stop

Stop before recording supervisor quiescence or mutating canonical repository
history.

---

## Block 3 — Add supervisor reconciliation coordination and monitoring gates

Status: `not-started`

### Objective

Let the existing supervisor coordinate active tasks and independently gate one
cleanup run without becoming a repository writer or a second acceptance owner.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: cleanup safely works around healthy tasks or
  checkpoints overlapping tasks, then remains monitored through restart.
- Potential capability loss or regression: stale or caller-asserted quiescence
  could permit deletion during active writes, while overbroad pauses could stop
  useful unrelated work.
- Protected-capability effect: preserves direct missions, implementation ranges,
  task-owned checkpoints, one writer, action-routing gates, independent review,
  no manual Resume, and supervisor read-only boundaries.
- Architecture and operating-model effect: adds one derived repository-
  reconciliation state machine to the canonical supervision owner and one
  cleanup-target profile; no second watcher, ledger, task owner, or Git writer.
- Tradeoff and source evidence: four evidence gates add coordination latency only
  to consequential phases and allow ordinary unchanged audits to remain O(1).

### Inputs and dependencies

- Block 2 plan/preservation roots and current task/range/control posture.
- Current accepted automatic-release/supervisor-refresh behavior. If its active
  tracker has not reached an accepted integration boundary, hold overlapping
  implementation and continue only non-overlapping fixture/test work.

### Required work

- Extend the existing supervision helper/policy/skill with one action family or
  equivalent bounded owner for `plan`, `quiescence`, `deletion`, and `outcome`
  gates over one repository-reconciliation identity.
- Bind repository/common-dir, cleanup target task, exact plan/preservation roots,
  affected task IDs/ranges/frontiers, active writer, source refs, remote heads,
  PR currentness, operation hold, and expiry in the existing event ledger.
- Use `thread-route-gate` to request an atomic checkpoint/pause from affected
  owners. Unaffected tasks continue. The target owner—not the supervisor—creates
  the commit/preservation receipt and acknowledges its frontier.
- Issue quiescence only after every overlapping writer is owner-confirmed
  inactive and preserved. Any relevant Git/provider/task change revokes the
  gate and returns one exact replan action.
- Keep supervision active while implementation tasks are held. Record cleanup
  as an operation state, not false target `blocked`, `stopped`, `paused`, or
  `completed` lifecycle.
- Separate mechanical watching from semantic review: Terra checks identity,
  dirt, refs, ownership, receipts, currentness, and phase; Sol XHigh reviews
  acceptance/no-loss/functionality/outcome; Sol Max handles supported material
  ambiguity or intervention.
- Deduplicate unchanged checks and routes. If cleanup fails, route the narrow
  correction to the same cleanup target and retain the same run; never create a
  duplicate writer or convert an internal failure into a user Resume request.

### Scope and non-goals

- In scope: coordination state, task routing, operation holds, four gates,
  changed-state monitoring, correction, and effectiveness posture.
- Not in scope: Git/provider mutation, target tracker edits, cleanup-plan authoring,
  code acceptance, release-pointer writes, or a general task scheduler.
- The supervisor may inspect exact bounded artifacts but stores only minimized
  identities/roots in its ledger.

### Deliverables and recorded state

- Supervisor helper/policy/skill changes, event schema/state machine, role prompts,
  gates, fixtures, and focused regression tests.

### Resource and economy contract

Immediate checks occur only at the four phase gates and on a changed target/
repository fingerprint. Use the normal 20-minute heartbeat only during a long
unchanged phase; no repeated Git scans, target reads, or commentary on equivalent
state.

### QA and independent review

Focused helper/policy tests, control-posture/range regression, route-gate tests,
and independent review of authority separation, narrow pause scope, revocation,
and no-manual-Resume behavior.

### Acceptance

- One cleanup run obtains current coordination gates, affected tasks are safely
  checkpointed without pausing unrelated work, and supervisor observation never
  writes or accepts repository content.

### Negative tests

- Reject caller-asserted quiescence, missing task owner, active second writer,
  stale plan/root/ref/PR, broad whole-project pause, supervisor Git write,
  self-reviewed no-loss, duplicate route/run, false terminal posture, and manual
  Resume leakage.

### Completion evidence

Pending.

### Stop

Stop before merging candidate work, mutating a pull request, or publishing main.

---

## Block 4 — Implement accepted integration, PR disposition, validation, and main publication

Status: `not-started`

### Objective

Make the cleanup owner converge all and only accepted source onto a validated,
non-force canonical `main` while truthfully resolving configured pull requests.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: accepted distributed work becomes one current source
  line and PR state without user-managed merge mechanics.
- Potential capability loss or regression: blind merging or conflict resolution
  could integrate rejected code, drop current behavior, or bypass protection.
- Protected-capability effect: preserves tracker/reviewer acceptance, rejected
  history, provider protection, current remote ancestry, no-loss coverage, and
  mapped repository functionality.
- Architecture and operating-model effect: the cleanup skill orchestrates
  existing Git/provider/test owners; it adds no merge service or acceptance
  ledger.
- Tradeoff and source evidence: merge commits preserve independently reviewed
  ancestry; narrow cherry-picks remain allowed only for exact standalone accepted
  deltas with recorded rationale.

### Inputs and dependencies

- Block 3 current quiescence gate, exact accepted candidate dispositions, and
  Block 2 no-loss/capability maps.

### Required work

- Re-fetch immediately before integration and reject/replan on changed main,
  candidate, PR, review, policy, or task state.
- Order accepted candidates by dependency and canonical tracker/review evidence.
  Do not interpret commit existence, age, green tests, mergeability, or PR labels
  as acceptance.
- Use the repository's permitted merge/PR path. Preserve independent ancestry
  where appropriate; record any exact standalone cherry-pick rationale.
- Resolve conflicts from current owner/contract evidence and update the
  capability map. Require fresh semantic review for conflict-affected behavior.
- Run focused validation after each integration delta, then freeze one candidate
  for mapped repository/product validation and exact review.
- Merge accepted current PRs, close only explicitly superseded PRs with recorded
  disposition, and retain unreviewed/ambiguous/provider-unavailable PRs.
- Publish through a non-force policy-compliant path, update local main
  non-destructively, and prove `main == origin/main` plus accepted ancestry/tree.

### Scope and non-goals

- In scope: accepted integration, conflict correction, configured PR effects,
  focused/mapped validation, and canonical main publication.
- Not in scope: deleting source branches/worktrees, accepting another tracker's
  work, force-pushing, broad refactoring, release activation, or deployment.
- Do not merge every discovered branch or PR merely to make the inventory empty.

### Deliverables and recorded state

- Exact integration graph, PR disposition receipts, frozen validation/review
  candidate, canonical main/remote proof, and updated no-loss coverage.

### Resource and economy contract

Reuse exact accepted validation by currentness; run focused proof after affected
deltas and one mapped suite on the frozen aggregate. Re-fetch once per
consequential provider boundary, not in a polling loop.

### QA and independent review

Focused conflict/PR/publication tests, mapped repository tests, and distinct exact
revision review of semantic preservation and accepted-source selection.

### Acceptance

- Local and remote main agree at one reviewed candidate, every integrated source
  is currently accepted, no merge-ready accepted PR remains open, and no
  conflict-affected capability is unmapped.

### Negative tests

- Reject stale remote/PR state, unaccepted or self-reviewed source, dependency
  inversion, conflict-dropped behavior, non-fast-forward overwrite, protection
  bypass, provider ambiguity, and tests-only acceptance.

### Completion evidence

Pending.

### Stop

Stop before deleting or retiring any source branch, ref, worktree, or task.

---

## Block 5 — Implement independently gated branch/worktree retirement

Status: `not-started`

### Objective

Retire only redundant ordinary branches, worktrees, and stale PR residue after
current mechanical and semantic no-loss proof, leaving every uncertain artifact
recoverable.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: repository topology becomes minimal and legible
  without sacrificing recoverability or functionality.
- Potential capability loss or regression: deletion after a stale or incomplete
  proof could permanently strand code, evidence, or an intended future option.
- Protected-capability effect: preserves archive/restore, active ownership,
  functional coverage, provider links, and published main before retirement.
- Architecture and operating-model effect: adds a deterministic exact deletion
  executor consuming the supervisor gate; no broad filesystem cleaner or Git
  garbage collector.
- Tradeoff and source evidence: ordinary names/worktrees are removed while
  preservation artifacts remain until a later separately reviewed disposition,
  favoring safe steady state over maximal disk reclamation.

### Inputs and dependencies

- Block 4 published main and PR dispositions.
- Block 2 preservation/no-loss manifest and Block 3 deletion gate owner.

### Required work

- Produce a deletion manifest with the exact object ID, path, owner, dirt state,
  PR links, preservation destination/restore receipt, capability disposition,
  and published-main relationship for every proposed effect.
- Require a second read-only reviewer to rebuild and accept the complete deletion
  set before the first effect; the cleanup writer cannot review itself.
- Have the supervisor deletion gate bind the exact manifest/source state and
  reject any task/ref/worktree/PR/remote/currentness change.
- Revalidate each exact target immediately before mutation. Remove only clean
  unowned worktrees without force, delete only eligible refs through exact names/
  object IDs, close only already dispositioned residue, then prune metadata.
- Use two-stage retirement: remove ordinary development topology only after
  verified preservation, and keep archival refs/packages outside ordinary lists.
  Do not run object garbage collection or automatically expire archives.
- Record each effect atomically and make interruption resume only the remaining
  exact eligible set; changed targets return to planning rather than retry.

### Scope and non-goals

- In scope: exact ordinary refs, worktrees, and PR residue approved by the
  deletion manifest/gate.
- Not in scope: source files, unknown/sensitive artifacts, supervision ledgers,
  release directories, unrelated repositories, archives, object GC, or task
  restart.
- Never use `git branch -D`, forced worktree removal, broad `git clean`, recursive
  path deletion, or unresolved globs/environment variables.

### Deliverables and recorded state

- Accepted deletion manifest, supervisor gate, per-effect receipts, retained
  archive manifest, and final compact topology inventory.

### Resource and economy contract

One currentness sweep and review for the batch, followed by O(1) exact-target
revalidation per effect. Stop on the first mismatch and do not rescan unaffected
targets until a new plan is admitted.

### QA and independent review

Disposable-repository destructive tests, interruption/replay tests, and a
distinct complete-set no-loss review before any live retirement.

### Acceptance

- Every retired artifact was exact, clean/unowned, preserved or fully integrated,
  semantically covered, current at deletion, and recoverable; retained topology
  contains only current intentional lanes and archives outside ordinary lists.

### Negative tests

- Reject dirty or task-owned worktrees, moved refs, unpreserved unique commits,
  open PR dependencies, unmapped functionality, stale reviewer/gate, forced or
  broad deletion, archive expiration, and interrupted duplicate effects.

### Completion evidence

Pending.

### Stop

Stop before starting, resuming, or replacing an implementation task.

---

## Block 6 — Restore unfinished work and verify effective restart

Status: `not-started`

### Objective

Return every intended unfinished workstream to one dependency-correct writer
from normalized main and prove actual useful work resumes.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: cleanup ends with useful implementation progress or
  truthful dependency-bound dormancy rather than a cosmetically empty repository.
- Potential capability loss or regression: duplicate or premature restarts could
  replay accepted work, skip dependencies, or reintroduce writer conflicts.
- Protected-capability effect: preserves original mission/range, accepted Blocks,
  exact next frontier, same-task preference, one writer, and no manual Resume.
- Architecture and operating-model effect: composes the existing task/range/
  route owners with cleanup outcome; no new scheduler or task lifecycle.
- Tradeoff and source evidence: create fresh lanes only for currently eligible
  work; dormant work remains durable with exact triggers instead of speculative
  tasks/worktrees.

### Inputs and dependencies

- Block 5 final topology and Block 4 normalized main.
- Current tracker/range/control posture for every preserved active or dormant
  workstream.

### Required work

- Recompute accepted work, remaining exact requested range, dependencies, and
  next safe frontier through existing owners after publication/cleanup.
- Reuse the same task by default. Create a fresh task only under existing exact
  task-creation authority and technical isolation; never restart both old and new.
- Create at most one clean branch/worktree per eligible lane from the exact
  normalized main revision; bind one task/writer and full intended tracker range.
- Route exact restart through `thread-route-gate`, preserving evidence and
  prohibiting replay. A handoff or acknowledgement is not work-start proof.
- Observe the next genuine task/repository delta and require actual first useful
  work at the intended frontier before the supervisor outcome gate passes.
- Record ineligible work as dormant with owner, dependency, safe frontier, and
  revisit trigger. Do not ask the user to schedule it.

### Scope and non-goals

- In scope: lane/task placement, range/currentness, routed restart, and observed
  effectiveness.
- Not in scope: implementing all remaining tracker Blocks, duplicating a live
  task, or treating cleanup as target-implementation acceptance.
- Do not create an empty branch/worktree merely to make a plan look active.

### Deliverables and recorded state

- Final task/lane/frontier map, routed restart receipts, first-work evidence, and
  dormant dependency/revisit records.

### Resource and economy contract

At most one route and one first-work observation per lane/reconciliation identity.
No unchanged polling, repeated wake, or per-Block task creation.

### QA and independent review

Focused same-task/new-lane/deduplication/dependency tests and independent review
that actual work—not task status—resumed from current main.

### Acceptance

- Every intended unfinished workstream is either observed progressing through
  one current writer or truthfully dormant behind an exact trigger, with zero
  manual user scheduling.

### Negative tests

- Reject old-base, duplicate writer, narrowed range, dependency skip, proof
  replay, handoff-only completion, stale first-work evidence, user Resume request,
  and unowned dormant work.

### Completion evidence

Pending.

### Stop

Stop before changing other skills' invocation contracts or releasing the new
skill.

---

## Block 7 — Wire the simple invocation and cleanup-needed signal contract

Status: `not-started`

### Objective

Make direct users and the supervisor the only cleanup initiators while letting
other Factory owners signal an exact need at economical boundaries.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: repository cleanup is easy to invoke periodically
  and automatically routed when supported, without a web of nested skill calls.
- Potential capability loss or regression: broad triggers could interrupt every
  Block, release, or long-running task and create coordination churn.
- Protected-capability effect: preserves skill independence, task ownership,
  scheduled audit safety, release separation, and user intent.
- Architecture and operating-model effect: adds a small trigger/signal contract
  to existing skills and supervisor routing; no scheduler or general workflow
  engine.
- Tradeoff and source evidence: only user/supervisor initiation keeps the call
  graph simple; exact signals retain awareness at admission, terminal, and
  release-prerequisite boundaries.

### Inputs and dependencies

- Block 6 proven cleanup/restart behavior and current installed skill contracts.

### Required work

- Finalize `clean-software-factory` metadata and instructions so direct requests
  for cleanup/consolidation trigger one full run and scheduled use defaults to
  unchanged-state audit.
- Update `supervise-tracker-runs` to route one dedicated cleanup owner only for a
  direct request, a supported repository-coordination incident, or an explicit
  maintenance milestone. The supervisor never executes Git mutation itself.
- Update `implement-tracker-blocks` narrowly: emit cleanup-needed only when
  repository ownership blocks safe admission or when accepted terminal work
  remains distributed and canonical integration is an ordinary required effect.
  Never invoke cleanup per Block/commit/checkpoint.
- Update `author-implementation-trackers` narrowly: when a proposed program
  necessarily creates parallel lanes, require an owned terminal reconciliation
  Block or signal; authoring never runs cleanup.
- Make release/product-program owners return an exact cleanup prerequisite when
  canonical main/source divergence blocks their normal action; they do not merge
  or invoke cleanup within the release/product owner.
- Document the simple ownership rule: cleanup skill owns repositories; supervisor
  owns running-task coordination; all other skills only signal need.
- Reuse existing automation owner for an explicitly scheduled audit; add no
  default schedule or autonomous mutation cadence.

### Scope and non-goals

- In scope: trigger metadata, supervisor routing, narrow signal prose/contracts,
  and invocation tests/docs.
- Not in scope: every skill calling cleanup directly, implicit per-Block cleanup,
  mandatory supervision for ordinary implementation, or a new orchestration API.
- Do not let a cleanup-needed signal carry merge/delete acceptance.

### Deliverables and recorded state

- Updated skill descriptions/contracts, trigger matrix, routing tests, and
  operator invocation documentation.

### Resource and economy contract

Signal checks reuse already-loaded admission/terminal/release state and remain
O(1). Open no cleanup run for an unchanged or nonblocking condition.

### QA and independent review

Trigger/negative-trigger tests and independent review for accidental recursion,
over-triggering, scope expansion, and owner bypass.

### Acceptance

- Direct user and supervisor routes start the correct cleanup behavior; other
  skills emit only exact supported signals; ordinary Blocks and scheduled
  unchanged audits produce no pause or repository mutation.

### Negative tests

- Reject per-commit/per-Block invocation, nested cleanup writers, scheduled
  destructive authority, release-owner merge, signal-as-acceptance, recursive
  supervisor routing, and direct user scheduling leakage.

### Completion evidence

Pending.

### Stop

Stop before final candidate release integration or live installed dogfood.

---

## Block 8 — Freeze, review, integrate, release, and refresh the complete skill set

Status: `not-started`

### Objective

Independently accept the complete cleanup capability, integrate it on canonical
main, and install it through the existing rollback-safe Software Factory release
owner without losing any currently released skill.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: the new cleanup skill and supervisor interactions
  become discoverable and current for real invocations.
- Potential capability loss or regression: an incorrect fixed skill set or
  unsafe release migration could drop an existing skill, break stable links, or
  strand running supervisors.
- Protected-capability effect: preserves exact current skill set, validators,
  assurance suites, acceptance, immutable release history, atomic pointer,
  rollback, stable discovery links, and safe role refresh.
- Architecture and operating-model effect: extends the one existing release set
  by `clean-software-factory`; no second installer, plugin, or mutable checkout
  link.
- Tradeoff and source evidence: the release owner remains exact rather than
  dynamically discovering arbitrary directories; implementation must extend the
  live accepted set by one regardless of whether another planned skill was added
  first.

### Inputs and dependencies

- Blocks 0–7 complete candidate and current accepted main/release.
- Accepted current automatic-release/supervisor-refresh owner behavior.

### Required work

- Finish all likely-mutating review findings, freeze the exact commit/tree/path
  set, and run new-skill, supervisor, execution/authoring signal, release-owner,
  tracker-verifier, compile/diff, and mapped dashboard compatibility proof.
- Obtain distinct exact-revision semantic and destructive-safety review; correct
  findings only through successor commits with affected proof rerun.
- Update `scripts/skill_release.py`, its tests, release docs, README validation/
  invocation/repository map, and stable link/bootstrap/activate/rollback/status
  contracts to extend the exact live skill set by `clean-software-factory`.
  Preserve every current accepted skill; do not assume the stale literal count
  if another accepted skill lands first, and do not add dynamic directory
  discovery.
- Commit and non-force push each accepted slice; reconcile the final candidate
  into canonical main through repository policy.
- Promote only the exact accepted clean main revision through the existing
  release owner, verify all installed roots in a fresh process, preserve the
  prior release, and refresh compatible running supervisors at safe boundaries.

### Scope and non-goals

- In scope: complete tracker delta, exact current skill-set migration, main
  integration, local release, rollback proof, and supervisor refresh.
- Not in scope: remote package/plugin publication, manual symlinks/pointer edits,
  target repository cleanup, or product-program implementation.
- Do not claim release from a pushed branch, green tests, or review without the
  owner-returned installed identity.

### Deliverables and recorded state

- Accepted main commit/tree, expanded release manifest and stable links, active
  release/installed roots, prior rollback release, refresh receipts, and full
  validation/review evidence.

### Resource and economy contract

Use changed-path focused suites before one full release-owner assurance run on
the frozen candidate. Reuse exact Block evidence; rerun only invalidated proof
after a finding. Perform one promotion and one safe refresh per accepted source.

### QA and independent review

Full new-skill and mapped existing-skill suites, release migration/rollback/
interruption tests, exact-revision independent review, and fresh-process installed
root verification.

### Acceptance

- Canonical main, accepted candidate, release manifest, stable skill links,
  installed roots, and refreshed supervision behavior reconcile exactly; the
  prior release remains eligible for rollback.

### Negative tests

- Reject dirty/nonexact source, missing prior skill, dynamic unknown skill,
  count-specific stale migration, partial links, changed candidate/review,
  activation mismatch, rollback failure, manual pointer/link mutation, and
  release before canonical integration.

### Completion evidence

Pending.

### Stop

Stop before using the installed skill on a live Software Factory reconciliation
or claiming terminal capability effectiveness.

---

## Block 9 — Dogfood the released lifecycle and close from observable no-loss outcome

Status: `not-started`

### Objective

Demonstrate that the released skill and supervisor complete safe and coordinated
cleanup without useful-code/functionality loss, then close only from current
operator-visible repository and task outcomes.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block exercises, documents, and
  independently verifies the released behavior; it adds no new cleanup authority
  or feature mechanism.

### Inputs and dependencies

- Block 8 active release and one disposable repository/provider fixture set.
- One read-only live Software Factory audit against current main, tasks,
  worktrees, PRs, and release state.

### Required work

- Run a released-skill matrix covering unchanged audit, safe cleanup, active
  overlapping writer, unaffected continuing writer, dirty/untracked/ignored
  preservation, unique/detached/stashed work, accepted multi-branch integration,
  PR merge/close/retain, conflict-dropped functionality, moving ref/PR/task,
  interrupted resume, deletion rejection, successful retirement, restart, and
  truthful dormancy.
- Use disposable local/bare repositories and provider fixtures for destructive
  cases. Use the live Software Factory repository only for a read-only audit
  unless a separately current direct cleanup mission and all supervisor gates
  authorize mutation.
- Verify restore of every preserved class and show that the semantic reviewer
  blocks deletion when a merge remains reachable but loses behavior.
- Verify supervisor event-driven monitoring, four gates, permit revocation,
  single cleanup writer, no unchanged chatter, no duplicate wake, and actual
  first-work restart evidence.
- Inspect final command output and current operator-visible Git/provider/task/
  release state. Update README, release docs, and `CHANGELOG.md` from planned to
  implemented/demonstrated with exact evidence.
- Obtain an independent final outcome review of the released skill, no-loss
  manifest, test matrix, installed roots, and live read-only audit. Reopen only
  the narrow failed owner.

### Scope and non-goals

- In scope: released disposable dogfood, live read-only audit, documentation,
  exact final review, and tracker evidence/status closure.
- Not in scope: deleting live useful work for demonstration, manufacturing an
  open PR, creating a provider test service, cleaning unrelated repositories,
  or keeping a real task paused after proof.
- Do not treat process receipts alone as proof that useful functionality survived
  or implementation resumed.

### Deliverables and recorded state

- Rooted dogfood results, no-loss/restore/capability matrices, supervisor outcome,
  installed release evidence, live audit, docs/changelog, and exact tracker
  completion evidence.

### Resource and economy contract

One frozen fixture family, one released-skill dogfood run, one live read-only
audit, and one affected final validation/review pass. Batch provider cases through
the deterministic fixture and do not perform real destructive remote effects.

### QA and independent review

Full mapped validation, skill/release verification, disposable destructive tests,
current live readback, and distinct final reviewer reconstruction of the direct
mission and no-loss outcome.

### Acceptance

- The installed skill safely converges every supported case or retains it with
  one exact autonomous next action; no useful bytes/functionality disappear;
  canonical main/publication, safe retirement, and restart are observable; and
  all unsupported, stale, ambiguous, unauthorized, and unknown cases fail closed.

### Negative tests

- Reject terminal closure from green tests, reachability, archive existence,
  clean Git status, supervisor narration, or task status alone; reject any lost
  capability, unrestorable artifact, stale gate, duplicate writer/wake, live
  unauthorized mutation, open cleanup incident, or manual Resume requirement.

### Completion evidence

Pending.

### Stop

Stop. Do not extend this tracker into a background cleanup daemon, generic Git
hosting platform, disk reclamation program, or unrelated Factory hardening.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Current complete repository/task/PR inventory | 1 | 2–7 | 9 |
| Byte preservation and restore | 2 | 4–6 | 9 |
| Functional/capability preservation and unknown-retain | 2 | 4–5 | 9 |
| Supervisor coordination without repository writes | 3 | 4–7 | 9 |
| Single cleanup writer and current quiescence | 3 | 4–6 | 9 |
| Accepted integration, PR disposition, validation, and main publication | 4 | 5–6 | 9 |
| Independently gated safe retirement | 5 | 6 | 9 |
| Effective one-writer restart or truthful dormancy | 6 | 7 | 9 |
| Simple user/supervisor invocation and signal-only composition | 7 | 8 | 9 |
| Exact released skill set, rollback, and live current behavior | 8 | — | 9 |

## 9. Final completion definition

The tracker is complete only when Blocks 0–9 are accepted at exact current
revisions; `clean-software-factory` is installed through the existing release
owner; direct-user and supervisor entry paths work with every other skill limited
to exact cleanup-needed signals; the supervisor independently coordinates and
monitors one cleanup writer through plan, quiescence, deletion, outcome, and
restart; every pre-cleanup artifact has a complete no-loss disposition with
restorable bytes and preserved functionality; only accepted work reaches
canonical main; PR, validation, publication, ref, worktree, task, and release
state reconcile; every deletion is independently gated and current; unfinished
work is observed progressing or truthfully dormant; and final released dogfood
shows no useful-code/functionality loss, no duplicate writer or wake, no manual
Resume requirement, and no retained open item incompatible with the requested
periodic steady-state capability.
