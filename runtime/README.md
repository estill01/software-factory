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
or rollback. The maintained neutral content profile collects registered sources,
plans and revises a cited document, performs factual/structural/style review, renders
and delivers an exact artifact, and verifies its receipt. A consumer-owned external
fixture registers through the same public profile contract without placing its
identifiers, schema, or effects in the Factory package. Both complete real missions
through the ordinary program, work, QA, independent acceptance, and terminal owners.

## State and evidence

- Git owns source and candidate history.
- SQLite/WAL owns current operational state.
- Content-addressed storage owns command, test, report, provider, and other large
  evidence artifacts.
- Canonical libRSI records are stored or projected through the Software Factory
  persistence adapter and explicitly bound to operational records; they are not a
  second operational ledger.

## Staged acceptance and outcome closure

Candidate, integrated, installed, and terminal acceptance are separate exact-revision
stages. Mechanical probes remain evidence inputs; they cannot satisfy the governed
independent semantic review. A stage is promotable only after the governance owner has
accepted its probes and review and a different independent session has reconstructed
the operator-visible and protected-capability outcome at the same currentness root.
Outcome reconstruction consumes an exact bounded reviewer grant and verifies the
reviewer's recorded provider identity. Work acceptance is capability-token fenced to
the lifecycle coordinator; legacy QA can record a passed probe but cannot promote a
candidate.

If the process record is green but the observed outcome disagrees, the runtime records
the mismatch, reopens only the named work/capability/mission owner, and routes an
incident plus a correction obligation. Repeated identical observations deduplicate by
content root. Terminal reduction additionally requires an empty requested range, no
active canonical program, no required capability gaps, no open obligations, and
current terminal evidence at the accepted revision. A program closes only after its
accepted current revision records full-range completion with an empty resume frontier,
installed selected work, exact program evidence, and independent review. A
provider-reported completion is therefore not QA or terminal acceptance by itself.
Selected, uncancelled work below installed acceptance is also remaining work and blocks
terminal reduction even if no execution is active. Incident effectiveness likewise
requires incident-bound evidence created after a rooted correction, exact correction
and observation roots, the candidate revision when present, and observed
post-correction state. Stage promotion rechecks every currentness, outcome,
remediation, and terminal predicate in the same immediate transaction as promotion;
new program activation cannot race a current accepted terminal stage.

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
