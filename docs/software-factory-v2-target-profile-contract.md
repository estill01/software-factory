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
Snapshots bind the target commit, tree, checked-out branch, primary-checkout
status root, tracked diff-content root, untracked path/content roots, repository
state version, configured branch, and repository root. A same-path dirty edit
therefore changes currentness even when porcelain status text does not.

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
The registry binds a per-composition authority object into each profile;
invoking the adapter executor directly without that authority fails before a
physical owner runs. Core does not expose the raw workspace, execution,
operations, reconciliation, or profile objects, and its compatibility facade
denies raw workspace, command, and release effect methods.

Integration validates against the registered target branch and rejects a
candidate prepared for another head. Release staging accepts only a frozen
workspace belonging to the target whose observed clean HEAD still equals its
frozen revision. Release staging creates the existing strict governed-release
acceptance contract, and activation requires its exact accepted decision; an
arbitrary reviewer name or evidence string cannot manufacture it. Activation
and rollback additionally require the release source revision to match a
workspace from that target and the immutable release path to belong to its
registered release root. The physical owner selects a prior active release only
from that same root and rejects a rollback whose release or predecessor belongs
elsewhere. Release activation remains gated by the distinct review owner, and
rollback requires evidence. Cleanup uses a configured preservation root and
retains the existing no-loss and active-writer guards.
Both governed activation entrypoints use the same strict decision predicate;
the activate-and-verify convenience path cannot call the physical owner around
that gate.

## Neutral content profile and external extensions

`ContentTargetProfile` is the maintained non-software proof. It collects a
registered factual source set, creates and revises a source-bound document,
performs factual/structural/style review, renders deterministic HTML, and
delivers and verifies an exact internal artifact receipt. Its closed effect
arguments contain no caller paths, commands, acceptance, or release authority.
The current operation and extension-conformance contract is
[`software-factory-v2-content-extension-contract.md`](software-factory-v2-content-extension-contract.md).

The QA owner accepts either the existing frozen software workspace or a current
registered profile snapshot as candidate input. Non-workspace submission binds
the successful execution, work-declared profile and target, exact revision,
exact currentness root, target attributes, acceptance specification, and active
program revision. It does not bypass the same independent
candidate/integrated/installed/terminal acceptance lifecycle.

External consumers register implementations of the same public profile protocol
directly with the composition registry. Their identifiers, schemas, and effect
code remain outside `runtime/src/software_factory`; registration supplies no
mission, QA, supervision, or acceptance authority.

## Boundary

Each profile delegates to its registered physical owner; it does not
create another Git writer, state store, effect ledger, provider, QA system, or
acceptance authority. Core composition supplies the software profile—not the
raw Git workspace owner—to controller and QA workspace interfaces; the raw
owner remains an internal physical adapter. Generic core contracts contain no
universal domain entity schema or consumer-product concepts. Block 6 still
owns integrated QA, supervision, acceptance, and outcome closure. Blocks 9,
11, and 12 still own their assigned utils consumption, cutover, and terminal
qualification work.
