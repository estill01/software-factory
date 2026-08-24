# Software Factory v2 target-profile contract

Block 5 makes target-specific effects available through one composition-owned
`TargetProfileRegistry`. The registry is domain-neutral: it knows fixed effect
classes, exact target snapshots, ownership, and currentness. It does not know
Git, commands, release formats, content schemas, QA policy, or acceptance.

Every authoritative call binds all of:

- a registered profile key and target ID;
- one fixed `EffectClass` value;
- the exact target revision and currentness root observed immediately before
  the effect; and
- a profile-owned, closed argument contract.

The registry rejects an unknown profile, an effect class the profile does not
own, a free-form effect string, or a stale revision/currentness root before it
calls a target adapter. It returns distinct before/after snapshots and the
physical owner's result. Neither the registry nor a profile exposes an
acceptance operation.

## Software profile

`SoftwareTargetProfile` is the first complete profile. Its target authority is
the registered repository's exact primary Git checkout and configured target
branch ref. A linked worktree cannot be registered as target authority.
Snapshots bind the target commit, tree, primary-checkout status root,
repository state version, branch, and repository root.

| Fixed effect | Registered operation | Physical Factory owner |
| --- | --- | --- |
| `workspace` | create or freeze an exact-base candidate/verification/experiment lane | `WorkspaceService` |
| `command` | run a named fixed argv on an exact-base leased execution | `ExecutionService` |
| `test` | run a named fixed test argv on an exact-base leased execution | `ExecutionService` |
| `build` | run a named fixed build argv on an exact-base leased execution | `ExecutionService` |
| `integration` | prepare with a registered validation command, then compare-and-swap publish | `RepositoryReconciliationService` |
| `release` | stage a frozen candidate or activate an independently accepted release | `OperationsService` |
| `cleanup` | no-loss reconcile/preserve, clean workspace retirement, or verified-item retirement | `RepositoryReconciliationService` / `OperationsService` |
| `rollback` | roll back an active immutable release with evidence | `OperationsService` |

Commands are registered as exact argument vectors with one command/test/build
class, a timeout, and allowed exit codes. Callers supply only a command key,
execution ID, and lease generation; they cannot supply a shell string, argv,
environment, working directory, release root, integration root, preservation
root, target branch, or workspace root. Those values remain composition-owned.

Integration validates against the registered target branch and rejects a
candidate prepared for another head. Release staging accepts only a frozen
workspace belonging to the target whose observed clean HEAD still equals its
frozen revision. Activation and rollback additionally require the release source
revision to match a workspace from that target and the immutable release path to
belong to its registered release root, preventing cross-target reuse of
authority. Release activation remains gated by the existing distinct review
owner, and rollback requires evidence. Cleanup uses a configured preservation
root and retains the existing no-loss and active-writer guards.

## Boundary

The profile delegates to the existing Factory physical owners; it does not
create another Git writer, state store, effect ledger, provider, QA system, or
acceptance authority. Core composition supplies the software profile—not the
raw Git workspace owner—to controller and QA workspace interfaces; the raw
owner remains an internal physical adapter. The profile contains no universal
domain entity schema and no content or Patent Studio concepts. Block 6 still
owns integrated QA, supervision, acceptance, and outcome closure. Blocks 9,
11, and 12 still own their assigned utils consumption, cutover, and terminal
qualification work.
