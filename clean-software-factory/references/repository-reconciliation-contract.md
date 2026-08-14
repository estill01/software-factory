# Repository reconciliation contract

## Purpose

`clean-software-factory` reconciles one exact Git repository without treating
topology reduction as permission to lose source, behavior, evidence, or intended
work. This contract is the canonical data and authority boundary for cleanup
runs. A caller may request the capability, but cannot assert that a task is
quiescent, work is accepted, functionality is preserved, or an artifact is safe
to delete.

## Current implementation baseline

This implementation baseline was frozen on 2026-08-13 after a bounded current
read of the repository, GitHub, installed release, and active task owner:

- canonical repository: `/Users/ethanstillman/code/software_factory`;
- canonical common directory: `/Users/ethanstillman/code/software_factory/.git`;
- canonical branch and remote: `main` and `origin`;
- local and remote main: `fe2d0c643549239fbe65acd0823520a9fa809540`;
- open pull requests: none; merged pull requests `1` and `2` remain provider
  history rather than cleanup candidates; at `2026-08-14T06:04:27Z`, `gh`
  `2.92.0` ran
  `gh pr list --repo estill01/software-factory --state open --limit 100 --json number,state,headRefName,baseRefName,isDraft,mergeStateStatus,updatedAt`,
  canonicalized the response with `jq -cS`, and returned `[]` with SHA-256
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`;
- active installed release: `2109eeee4646-fb7861d1f68b`, sourced from
  `2109eeee46468a50c6c1c934628c4f033e7bb1fa`, with the three installed skills
  verified complete;
- automatic-release owner task:
  `019ffd59-10b3-73a0-a644-15c5e6ca9db6`, pushed and actively editing on branch
  `codex/automatic-release-monitor-refresh` at
  `0b97d661bb8e108963aa34ecaaaa992176f104d6`; its Block 5 is accepted and
  Block 6 is in progress. At the recorded observation it had four dirty paths
  under its reserved release/supervisor owners and no overlap with the cleanup
  skill tree or cleanup tracker. That exact committed revision has merged the
  cleanup tracker's `fe2d0c6` main baseline;
- cleanup implementation owner: this branch
  `codex/clean-software-factory`, initially based on the exact main revision
  above; and
- current worktrees: canonical main, the cleanup implementation lane, the
  automatic-release lane, and one detached private temporary evidence lane.

The automatic-release owner is the sole writer for its six-file supervisor and
tracker delta. Cleanup Blocks 0-2 use only the new cleanup-skill tree and this
tracker. Any edit to shared supervisor, implementation-skill, authoring-skill,
or release-owner surfaces remains held until that upstream line is accepted,
integrated, and the cleanup lane is rebased. The active owner is therefore
preserved and non-overlapping, not declared idle. This paragraph is an
implementation-time observation, not a reusable cleanup gate: a later branch,
path-set, task, or dirt change must be re-read before shared edits.

The executor's full-range interpretation is Blocks 0-9. The current range owner
rejected the concise direct request as syntactically under-specified for a
canonical binding even though the released execution skill requires unbounded
tracker requests to mean the full current tracker. Local full-range
reconciliation remains mandatory; no range, acceptance, quiescence, deletion,
or completion authority is inferred from this note.

## Canonical identities

A run is admitted only from all of these current, owner-produced identities:

| Identity | Required source | Invalidated by |
|---|---|---|
| `repository_root` | `git rev-parse --show-toplevel`, canonical absolute regular directory | different resolved path, symlink substitution, missing repository |
| `common_dir` | `git rev-parse --git-common-dir`, resolved beneath the repository's owning worktree set | different common directory or unsafe path type |
| `main_ref` | configured expected main branch plus exact object ID | ref move |
| `remote` | one exact configured remote name and normalized URL | ambiguity, removal, or URL change |
| `remote_main` | fetched remote-tracking object ID | ref move or fetch failure |
| `provider_snapshot` | configured provider query and exact result root | PR/review/protection change or unavailable owner |
| `worktree_snapshot` | porcelain worktree inventory plus per-worktree status roots | worktree, HEAD, lock, branch, or dirt change |
| `ref_snapshot` | local/remote refs, object IDs, upstreams, and reachability roots | any relevant ref change |
| `task_snapshot` | supervisor-derived task IDs, ranges, frontiers, writer postures, and evidence roots | task turn, ownership, range, or frontier change |
| `release_snapshot` | release-owner status projection | active pointer, manifest, source, or installed-root change |
| `plan_root` | deterministic plan record | any bound source identity change |

The repository identity is the SHA-256 of canonical JSON containing only
`repository_root`, `common_dir`, `main_ref`, `remote`, and normalized remote URL.
The run ID is `cleanup-` plus the first 24 hexadecimal characters of the SHA-256
of the source snapshot. Identical inputs reuse the identical run and phase;
changed inputs create a successor plan and cannot reuse an old gate.

## Artifact owner and encoding

Raw cleanup evidence belongs under
`~/.codex/software-factory-cleanup/runs/<repository-identity>/<run-id>/`.
Repository source is never copied into the supervision ledger. Every public
artifact is an immutable-or-identical regular file, UTF-8 JSON encoded with
sorted keys, compact separators, one final newline, no NaN values, and a
four-megabyte per-record ceiling unless a preservation package record names a
separately bounded local file.

The run artifact set is:

1. `source-snapshot.json` — repository, refs, worktrees, provider, task, release,
   and invocation currentness;
2. `inventory.json` — exhaustive artifact identities and dirt/provenance;
3. `plan.json` — proposed disposition and required proof for every artifact;
4. `preservation.json` — byte/mode/object receipts and restore owners;
5. `capability-coverage.json` — affected functional surfaces and semantic
   review inputs;
6. `integration.json` — accepted-source and conflict outcomes;
7. `validation.json` — frozen candidate and mapped proof;
8. `publication.json` — local/remote main and provider effects;
9. `deletion.json` — exact eligible targets and per-effect receipts;
10. `restart.json` — lane, task, range, frontier, and first-useful-work proof;
11. `outcome.json` — no-loss and operator-visible reconciliation; and
12. `status.json` — derived current phase and exact next action.

Every record has these required typed fields:

| Field | Type and rule |
|---|---|
| `schema_version` | integer, exactly `1` |
| `kind` | lowercase fixed enum for the named record |
| `repository_identity` | 64-character lowercase SHA-256 |
| `run_id` | `cleanup-` plus 24 lowercase hexadecimal characters |
| `source_snapshot_root` | 64-character lowercase SHA-256 |
| `record_root` | SHA-256 of the canonical record with this field omitted |
| `previous_record_root` | null for the first record of a kind, otherwise the exact prior immutable root |
| `phase` | one value from the monotonic phase enum below |
| `status` | `open`, `passed`, `replan-required`, `rejected`, or `completed` |
| `created_at` | owner-produced RFC 3339 timestamp; excluded from semantic/run identity |

Record-specific required fields and dependencies are:

| Record | Required fields beyond the base | Must bind |
|---|---|---|
| `source-snapshot` | repository/common-dir/main/remote/provider/worktree/ref/task/release identities and roots | live owners directly |
| `inventory` | exhaustive `artifacts`, `artifact_count`, `inventory_root` | source snapshot |
| `plan` | `path`, exhaustive `dispositions`, `holds`, `next_action`, `plan_root` | source snapshot and inventory |
| `preservation` | `packages`, `objects`, `bytes`, `modes`, `restore_receipts`, `preservation_root` | plan and exact artifacts |
| `capability-coverage` | `candidates`, `surfaces`, `unknowns`, `review_requirements`, `coverage_root` | plan and preservation |
| `integration` | accepted source receipts, conflict decisions, semantic reviews, resulting commit/tree | plan, preservation, coverage, quiescence gate |
| `validation` | exact candidate commit/tree, commands, results, mapped surfaces, validation root | integration |
| `publication` | fetched remote head, provider/protection state, non-force effect, local/remote main | validation and exact review |
| `deletion` | exact object/path/owner/dirt/PR/archive/coverage entries and per-effect receipts | publication, preservation, coverage, deletion review/gate |
| `restart` | lane/task/range/frontier/base/route/first-work or dormant-trigger entries | publication and final topology |
| `outcome` | no-loss matrix, restore results, final topology, provider/task/release readback, open items | all applicable prior records and outcome gate |
| `status` | derived current phase, active holds, gate posture, exact next action | current immutable heads only |

Arrays that own artifacts or effects are sorted by stable identity and contain
no duplicate key. Roots bind canonical semantic fields, required dependency
roots, and exact entry counts. A missing field, wrong type, unknown enum,
duplicate, orphan dependency, caller-provided derived root, or non-monotonic
transition rejects the record rather than defaulting it.

`repository-reconciliation-schema-v1.json` is the executable schema authority
for the exact field names, primitive or collection types, formats, item keys,
cardinalities, phase assignments, and dependency roots summarized above. The
Markdown tables explain that machine-readable contract; they cannot weaken or
add fields to it. `source-adaptation-currentness-v1.json` records the exact
implementation-time Git, worktree, provider, release, and active-owner
observation envelope. Neither file is reusable authority for a later live run.

Records store content roots of other records, not mutable path assertions.
Packages may contain sensitive or ignored bytes only locally. Unknown bytes are
never pushed merely to improve durability.

## Artifact inventory and disposition

Inventory is exhaustive across:

- local and remote refs, detached commits, reflog-dependent candidates, tags,
  and stashes;
- every registered worktree and its exact HEAD, branch, lock, prune posture,
  staged/unstaged/untracked state, and relevant ignored files;
- submodule and Git LFS posture when those owners are present;
- configured-provider pull requests, review/protection/merge state, and source
  heads; and
- supervisor-derived active, held, completed, stopped, and dormant task owners.

Every artifact has exactly one proposal from this exhaustive enum:

- `integrated`: exact bytes/objects and mapped capability exist in published
  main through current acceptance;
- `preserved`: exact bytes/objects, provenance, restore owner, and restore drill
  exist outside ordinary development topology;
- `validly-superseded`: independent semantic review proves the candidate's
  supported effects are retained or deliberately replaced by current accepted
  behavior;
- `generated-reproducible`: a current deterministic owner reconstructs the
  artifact from retained inputs and a restore drill proves it; or
- `retain`: deletion is not eligible.

Missing, malformed, unavailable, moving, unowned, sensitive, unreviewed, or
semantically uncertain state resolves to `retain`. Age, cleanliness,
reachability, patch identity, mergeability, tests, PR labels, and task status do
not promote a disposition.

## Byte and functionality preservation

Deletion eligibility requires both independent dimensions:

1. **Byte preservation:** exact Git object IDs or byte hashes, modes, paths,
   origins, durable local preservation location, restore command/owner, and a
   successful disposable restore receipt.
2. **Functional preservation:** a capability map covers affected routes, APIs,
   migrations, configuration, UI flows, tests, bug fixes, tracker/review
   evidence, and deferred options. Conflict/rewrite or
   `validly-superseded` dispositions require distinct semantic review against
   the exact candidate.

An artifact is deletion-ineligible if either dimension is `unknown`, if any
capability is absent or unmapped, or if the reviewer is the cleanup writer.
Archives are excluded from ordinary branch/worktree lists and do not expire
automatically.

## Owner map

| Effect or decision | Canonical owner | Cleanup behavior |
|---|---|---|
| Repository identity, refs, commits, status, worktrees | Git | inspect or execute exact non-force operations |
| PR/review/protection/merge state | configured hosting provider | query and perform only current dispositioned effects |
| Inventory and source-snapshot production | deterministic cleanup helper reading canonical owners | produce evidence; never decide acceptance or quiescence |
| Audit/safe/coordinated path and disposition proposals | deterministic cleanup helper under the contract | propose only; ambiguity is `retain` |
| Tracker acceptance and remaining range | tracker and implementation-range owners | consume exact evidence; never infer acceptance |
| Task identity, checkpoint, pause, wake, first work | task owner routed by supervisor | request exact actions; never edit another task's state |
| Changed-state monitoring and four phase gates | supervision event owner | store minimized roots; never write the repository |
| Byte packages and restore receipts | cleanup artifact owner | create locally and verify before eligibility |
| Functional equivalence/supersession | distinct semantic reviewer | provide exact-revision disposition |
| Deletion eligibility | deterministic manifest plus distinct semantic reviewer and current supervisor deletion gate | eligible only when all three agree on the same roots |
| Successor plan after invalidation | deterministic cleanup helper from newly read owners | append a replan; never replay a stale gate |
| Accepted-source selection and integration | cleanup writer using Git plus tracker/review acceptance owners | integrate only exact current accepted sources after quiescence |
| Conflict resolution | cleanup writer using source-contract owners plus distinct semantic reviewer | correct affected behavior and refresh capability coverage |
| Candidate validation and exact review | repository test/build owners plus distinct exact-revision reviewer | freeze and prove the aggregate candidate without publishing it |
| Canonical main and PR publication | cleanup writer through Git and configured hosting provider | use current protection-aware non-force operations after validation |
| Exact branch/worktree/PR retirement effects | cleanup writer through Git/provider after deletion eligibility and gate | revalidate and execute one named target at a time without force |
| Restart or dormant-path selection | existing tracker/range/task owners coordinated by supervisor | preserve the exact mission and dependency frontier |
| Skill activation and rollback | `scripts/skill_release.py` | invoke owner; never edit pointers/links manually |
| Final capability outcome | supervisor outcome review plus current repository/task readback | close only from observed effects |

## Phase and gate contract

The monotonic phase order is `inventory`, `plan`, `preserve`, `quiescence`,
`integrate`, `validate`, `publish`, `delete`, `restart`, `outcome`. A failed or
changed phase appends a successor plan or correction; it never rewrites a prior
receipt.

- `plan` proves complete inventory, current owners, and retain-on-unknown.
- `quiescence` binds the plan and preservation roots plus every overlapping
  writer's owner-produced inactive checkpoint. Unaffected writers continue.
- `deletion` binds published main, no-loss/capability roots, exact deletion
  manifest, independent review, and unchanged Git/provider/task state.
- `outcome` binds final topology, restore proof, release/readback, task restart
  or dormancy, and no open incompatible item.

Any bound task, ref, worktree, PR, remote, plan, preservation, review, or
release change revokes the relevant gate and yields one exact replan action.
Operation holds are scoped to named effects, expire on source change or run
completion, block successor effects, and never carry forward.

## Supported paths

- **Audit:** read and plan only. Scheduled invocation defaults here and is
  silent when the source fingerprint is unchanged.
- **Safe cleanup:** only exact redundant topology with no active overlapping
  writer and complete preservation/no-loss proof.
- **Coordinated reconciliation:** supervisor routes checkpoint/hold actions to
  overlapping owners; one cleanup writer proceeds only after quiescence.

No path authorizes force push, forced worktree removal, broad `git clean`, Git
object garbage collection, branch-protection bypass, caller-selected
acceptance, supervisor repository writes, or automatic archive expiry.

## Fixture coverage

`../fixtures/repository_reconciliation_v1.json` is deliberately synthetic and
content-minimized. It covers clean redundancy, unique commits,
staged/unstaged/untracked/ignored bytes, detached and stashed work, a moved ref,
merge-ready/superseded/unavailable pull requests, active overlapping and
unaffected writers, conflict-dropped functionality, interrupted cleanup,
successful retirement, restart, and truthful dormancy. Fixture labels and
expected postures test the contract; they do not authorize live dispositions.
