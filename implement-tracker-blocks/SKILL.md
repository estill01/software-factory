---
name: implement-tracker-blocks
description: Execute implementation-plan or roadmap tracker blocks faithfully, one bounded block at a time, audit each completed block before advancing, and preserve scoped Git checkpoints with regular pushes to an available configured remote. Use when the user attaches or references a tracker and asks to implement Block N, continue with the next block, implement a block range, or review whether the previous block was fully implemented.
---

# Implement Tracker Blocks

Turn a tracker reference plus a block number or range into an evidence-bound
implementation loop. Treat the tracker as the scope and completion contract,
while treating live repository instructions and authorities as controlling.

## Resolve the request

1. Resolve the exact referenced tracker and active repository.
2. Read applicable repository instructions before changing files.
3. Extract the requested block's dependencies, objective, required work,
   deliverables, acceptance criteria, stopping point, status rules, and required
   evidence.
4. If the user requested a range, preserve the tracker's dependency order. If
   the user requested one block, do not silently advance to another.
5. Treat the tracker path and requested block number or range as reusable
   inputs. Never bake a demonstrated repository path or block number into the
   workflow.

If the user explicitly asks to monitor, babysit, supervise, periodically audit,
or prevent drift in the implementation run, use `$supervise-tracker-runs` as a
separate optional companion. Do not start supervision merely because a tracker
is present, and do not merge supervisor duties into this implementation loop.

## Activate one block economically

Before editing, form one compact execution brief from the live Block: governing
outcome, existing owner, exact missing delta, reusable accepted evidence,
dependency/currentness check, expected focused and mapped proof, review order,
resource/widening posture, and stop boundary. Do not create a new artifact for
the brief unless the tracker requires it.

Preflight the current Block and its next eligible dependent Block for an
explicit non-delegable decision. Do not stop for an ordinary choice Codex can
resolve from the tracker, current authorities, and bounded judgment. When a
human, counsel-reserved, credential, destructive-ambiguity, or external-
authority gate is genuinely required, surface it as soon as its complete
decision packet is available—normally during the predecessor or at Block start.
State why it is non-delegable, the exact alternatives and recommended rationale,
the deadline/first dependent Block, and the scope it alone blocks. Continue all
safe, independent, pre-decision work; do not wait until the stop boundary to
give the first warning.

Choose the smallest reliable causal path. Reuse current manifests, indexes,
snapshots, exact source copies, prior accepted reviews, and configured runtimes.
Use a cheap exact revision/root/currentness check before a deep scan or
rehydration. Batch coherent work; do not repeat the pipeline per item when one
bounded owner pass suffices. On repeated failure, diagnose or narrow the
implicated path instead of blindly retrying, changing runtimes, or widening the
suite.

## Implement one block

1. Inspect the live tree before planning. Reconcile the tracker against current
   code, configuration, tests, generated artifacts, and Git state.
2. Preserve completed, staged, untracked, and in-flight user work. Keep the
   change set bounded to the block and avoid unrelated cleanup.
3. Classify already-present work as current proof, pending proof, pending
   promotion, or an actual delta when the tracker uses such distinctions. Do
   not recreate working capability merely because it appears in a checklist.
4. Implement every required delta through the narrowest authoritative layer.
   Do not absorb later blocks or invent adjacent infrastructure.
5. Run focused validation during the edit loop. Complete known in-scope changes
   and any review allowed to mutate the candidate before expensive final mapped
   validation when the workflow permits it.
6. Freeze the coherent candidate content root, then run the mapped integration
   validation appropriate to that slice and verify the root did not change.
   Create the scoped checkpoint commit only after the candidate is validated.
   If the candidate changes during or after validation, retain the run as
   diagnostic and rerun only affected proof against the successor.
7. Obtain a distinct reviewer when the tracker or repository requires
   independent review. Keep review read-only until findings are returned and
   bind it to the exact candidate revision.
8. Update the tracker only with evidence that is current. Use its prescribed
   status and completion-evidence format.
9. Stop at the block's explicit stopping point.

Treat a blocked implementation as exceptional. Claim `blocked` only when the
exact non-delegable input is still absent, proceeding would cross a declared
authority or safety boundary, the decision-ready packet has been exposed, and
all safe in-scope work has been exhausted. Report the earliest point at which
the blocker was foreseeable and when it became decision-ready. Do not convert
a preferred confirmation, generic confidence request, unresolved but bounded
engineering choice, or work that can proceed independently into a full-run
stop.

## Apply a live supervision correction

When a current supervisor or the user identifies a supported execution-economy
defect, correct the same active tracker run; do not merely create guidance for a
future tracker or wait for the next Block.

1. Contain only the exact owned wasteful action. Stop its exact process tree or
   decline its next repeated unit when safe; do not interrupt unrelated work or
   cross an irreversible boundary merely to react quickly.
2. Preserve accepted checkpoints and still-valid focused evidence. Mark an
   interrupted or pre-correction run accurately as diagnostic, aborted,
   superseded, or stale rather than claiming it passed for the successor.
3. Identify the smallest current owner of recurrence. Amend the active execution
   brief first; amend the current tracker, changed-test mapping, runner/profile,
   or implementation only when that owner concretely caused or would repeat the
   defect in this run. Do not add a parallel policy or remediation subsystem.
4. Recompute affected scope and validation after the correction. Rerun only the
   proof invalidated by the successor; never restart the same broad action for
   generic confidence or because a reusable skill update is pending.
5. Commit the coherent correction under the ordinary checkpoint contract when
   files changed, obtain any required exact-revision review, and show the
   supervisor later evidence that the active cost stopped and the Block resumed
   from the last valid boundary.
6. Re-read a reviewed reusable-skill correction when notified and apply it to
   the remaining current run immediately at the next safe action boundary. Do
   not retroactively invalidate valid work or reopen accepted Blocks without a
   mapped dependency.

Reusable skill maintenance prevents later recurrence; it never discharges the
current run's correction, evidence, or incident-closure obligations.

## Audit before advancing

After implementation, review the block against its original contract:

- Was every required item faithfully and fully implemented?
- Does every completion claim resolve to live implementation and current proof?
- Were negative cases, compatibility, migration, dirty-tree preservation,
  real-input proof, and independent review handled where required?
- Did the implementation cross the stopping point or leave an unacknowledged
  acceptance gap?

Correct only material defects and high-impact opportunities that remain inside
the block. If the implementation already satisfies the contract, make no
speculative changes. Rerun affected validation after any correction.

For a rejected candidate, maintain a compact closure matrix: each finding,
governing invariant, exact corrective delta, focused regression, affected mapped
proof, and fresh exact-revision review. Close every row or preserve it as an
explicit blocker. Do not rerun unrelated suites, rescan unchanged authorities,
or reopen accepted work without a mapped dependency. Once the corrected Block
passes its declared proof and independent audit, stop remediation.

Do not mark a block complete when required proof is unavailable. Use the
tracker's accurate intermediate status and report the exact gap.

## Preserve Git checkpoints

Treat bounded commits and remote durability as part of the implementation
loop unless the user or repository instructions explicitly prohibit them.

1. Before editing, inspect the current branch, worktree/index state, upstream,
   and configured remotes. Treat unrelated staged, unstaged, and untracked work
   as user-owned.
2. Create a narrowly scoped commit after each coherent validated implementation
   candidate and before exact-commit independent review. For a long block,
   also checkpoint each self-contained slice that passes its focused tests
   before beginning another material slice; label it accurately as in progress
   and do not claim block acceptance.
3. Do not let more than one completed block or one material audited remediation
   accumulate without a commit. If review rejects a candidate, preserve that
   commit and append a new remediation commit; never amend or rewrite reviewed
   history to manufacture acceptance.
4. Commit accepted tracker status and completion evidence at the next coherent
   boundary, separately from implementation when that keeps scope and audit
   history clearer.
5. Stage only the owned block slice and verify the staged diff. Never sweep in
   unrelated work, commit known failing or unexplained state, or interrupt a
   running test or review merely to create a checkpoint.
6. After each coherent checkpoint commit, push the current branch when an
   already configured remote path is unambiguous and repository policy permits
   it. Prefer the existing upstream. If no upstream exists and exactly one safe
   configured remote exists, use a non-force `git push -u <remote> HEAD`.
7. Never add or rewrite a remote, guess among multiple remotes, force-push,
   rewrite history, bypass protected-branch policy, merge, release, or open a
   pull request merely to satisfy this checkpoint rule. If the remote is
   absent, authentication fails, or policy forbids the push, preserve the local
   commit and report the exact blocker; continue locally when otherwise safe.
8. Record each checkpoint commit SHA and push status in the running evidence or
   handoff so the next block starts from an exact durable revision.

## Continue a range

For each subsequent block in the requested range:

1. confirm the prior block passed the audit;
2. reread the next block's contract and live dependencies;
3. implement, validate, independently review where required, and update
   evidence;
4. audit it before advancing again.

End with a concise outcome: completed blocks, material files changed,
validation and review evidence, preserved open items, and the next eligible
block. Do not release, merge, open a pull request, or perform destructive
cleanup unless the user separately authorizes it or the repository's ordinary
implementation workflow explicitly requires it.
