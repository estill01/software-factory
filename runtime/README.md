# Software Factory 2.0 Runtime

`Software Factory` is the current repository and product name. The v2 core is an
**autonomous mission execution runtime**: it turns an authorized goal into a durable
program, coordinates agents and tools to execute it, supervises and adapts the work,
verifies actual outcomes, and continues until a legitimate terminal boundary exists.
Software engineering is the first target profile rather than the ontology of the core.

The maintained implementation plan is:

- [`../docs/software-factory-v2-implementation-plan.md`](../docs/software-factory-v2-implementation-plan.md)

## Architectural boundary

The runtime owns operational control:

- missions, protected capabilities, obligations, programs, work, and continuation;
- agent sessions, assignments, providers, workspaces, leases, fencing, and telemetry;
- supervision, incidents, QA, acceptance, authority, release, recovery, and cleanup;
- real target effects, operator commands, reports, notifications, API, and UI.

[`libRSI`](https://github.com/estill01/libRSI) is the reusable semantic improvement
engine. As its accepted contracts are integrated, it owns domain-neutral target,
intent, evidence, experiment, intervention, comparison, improvement, and governed
recursive-self-improvement semantics. This runtime consumes libRSI through explicit
adapters; libRSI never imports Software Factory and never becomes a competing outer
scheduler or mission authority.

Target-specific behavior belongs behind profiles. The software profile owns Git,
repositories, worktrees, commands, tests, builds, integration, and software release
or rollback. A content profile will provide the first maintained non-software proof
that the mission runtime is genuinely general.

## State and evidence

- Git owns source and candidate history.
- SQLite/WAL owns current operational state.
- Content-addressed storage owns command, test, report, provider, and other large
  evidence artifacts.
- Canonical libRSI records are stored or projected through the Software Factory
  persistence adapter and explicitly bound to operational records; they are not a
  second operational ledger.

## Current implementation state

The branch contains substantial native implementation covering mission, capability,
obligation, program, authority, command, event, workspace, lease, provider, execution,
QA, supervision, signal, reflection, experiment, evolution, release, recovery,
reconciliation, reporting, API, migration, and cutover areas.

The refactor remains in progress. Code or table presence is not acceptance. The branch
must still converge on one exact green revision, prove every behavioral case, integrate
libRSI without duplicate semantic owners, complete retained-state parity and one-writer
cutover, remove superseded active code, and pass real end-to-end software and
non-software mission dogfoods.

The executable acceptance inventory currently begins at:

- [`acceptance-matrix.json`](acceptance-matrix.json)

It must be extended to distinguish semantic, host, and integration acceptance for
libRSI-backed paths while preserving the existing minimum capability coverage.

## Local usage

```bash
python -m pip install -e 'runtime[dev]'
software-factory --home /tmp/software-factory init
software-factory --home /tmp/software-factory health
software-factoryd --home /tmp/software-factory --once
```

The `sf-skill` entrypoint is a thin runtime bridge used by the user-facing skill
interfaces. It owns no parallel ledger or lifecycle.

## Controller and provider lifecycle

The native controller records dependency-ready dispatch as a durable transition:
work selection, agent attribution, workspace ownership, assignment, fenced leases,
provider callback capability, and execution creation are persisted before an external
provider starts. Provider results are generation-fenced, single-use, and bound to the
exact execution. Lost leases preserve the workspace and obligation, revoke stale
callbacks, cancel the prior provider when possible, and permit a replacement lane.

`codex_cli` is the default installed provider adapter. Its executable and argument
prefix are external configuration (`SOFTWARE_FACTORY_CODEX_EXECUTABLE` and
`SOFTWARE_FACTORY_CODEX_ARGS`). Deterministic and local-process providers support
controlled integration tests without claiming that live Codex credentials or tasks
were exercised.
