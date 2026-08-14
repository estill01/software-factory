---
name: clean-software-factory
description: Audit, consolidate, and safely reconcile one Git repository without losing useful code or functionality. Use when Codex is asked to clean or normalize a repository, reconcile work onto main, disposition pull requests, remove stale branches or worktrees, preserve in-flight work, or coordinate repository cleanup with active supervised tasks.
---

# Clean Software Factory

Reconcile one exact repository through a fail-closed, evidence-bound run. Treat
topology reduction as an outcome of preservation and acceptance, never as the
definition of cleanup.

## Read the contract

Read [references/repository-reconciliation-contract.md](references/repository-reconciliation-contract.md)
before operating. Use its owner map, record schema, phase gates, and no-loss
rules as hard boundaries. Never infer acceptance, quiescence, functional
equivalence, or deletion eligibility from age, ancestry, cleanliness, tests,
task status, or a caller assertion.

## Start or resume one run

1. Resolve the canonical absolute repository top level, expected main branch,
   configured remote, and provider owner.
2. Obtain compact owner-produced task and release snapshots when those owners
   are available. Missing or malformed owner state is `unknown`, not clean.
3. Run the deterministic helper's `plan` command. It inventories first and
   reuses the same run for identical source roots.
4. Inspect `status` and the plan's exact holds and next action. Do not open a
   second run for unchanged inputs.

```bash
python3 clean-software-factory/scripts/reconcile.py plan \
  --repo /absolute/repository/top-level \
  --main main \
  --remote origin \
  --provider github \
  --task-snapshot /absolute/owner-produced-task-snapshot.json \
  --release-snapshot /absolute/owner-produced-release-snapshot.json
```

Omit an unavailable optional snapshot; the plan will retain affected artifacts
and name the missing owner. Use `--provider-snapshot` for an already frozen
provider result. The helper writes only to its bounded local run-artifact root;
the repository, provider, tasks, and supervision state remain read-only during
inventory and planning.

Before any integration or topology change, preserve the exact run locally:

```bash
python3 clean-software-factory/scripts/reconcile.py preserve \
  --run-dir /absolute/local/run-directory \
  --repo /absolute/repository/top-level \
  --main main \
  --remote origin \
  --provider github
```

Preservation packages stay outside the repository and Git common directory.
The helper verifies their hashes with a disposable restore drill, maps every
inventoried artifact to an explicit capability candidate, and leaves every
candidate `unknown` and retained until a distinct semantic reviewer supplies
current coverage. It does not push package bytes or make anything eligible for
deletion.

Restore one packaged artifact only to an explicit new local file after verifying
the complete run:

```bash
python3 clean-software-factory/scripts/reconcile.py restore \
  --run-dir /absolute/local/run-directory \
  --artifact-id worktree-path-0123456789abcdef01234567 \
  --destination /absolute/disposable/restored-file
```

The cleanup artifact owner controls the run directory and restore destination.
The command refuses overwrite, re-verifies the immutable package, reapplies the
recorded file mode, and compares the restored bytes before reporting success.

## Choose the path from evidence

- `audit`: use when any owner is unavailable, state is ambiguous or moving, or
  proof is incomplete. Retain every affected artifact.
- `safe-cleanup`: eligible only when the plan has no active overlapping writer
  or current ambiguity. Later preservation and deletion gates still control all
  effects.
- `coordinated-reconciliation`: use when an active writer overlaps the
  repository. Ask the supervisor to route exact checkpoint and pause actions;
  do not message tasks directly or pause unaffected work.

The user selects the desired repository outcome, not internal phases. Continue
the evidence-selected path autonomously while a dependency-safe action remains.

## Verify and report

Use `verify` against the exact run before trusting an artifact and `status` to
derive its current phase. If Git, provider, task, release, or run roots changed,
create a successor plan and never replay a stale gate. Report retained unknowns
and the exact next action; do not describe a plan as completed cleanup.

## Hard prohibitions

Do not force-push, force-remove a worktree, run broad `git clean`, invoke Git
garbage collection, bypass branch protection, push unknown local bytes, edit a
task's tracker on its behalf, let the supervisor write the target repository,
or delete anything before both byte and functional preservation are proven and
the current deletion gate permits the exact effect.
