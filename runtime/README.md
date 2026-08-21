# Software Factory 2.0 Runtime

The native runtime is a transactional, SQL-backed control plane for autonomous
multi-agent software implementation. Git owns source history, SQLite owns current
operational and learning state, and a content-addressed artifact store owns command,
test, report, and provider evidence.

Current implemented foundation includes mission/capability/obligation/program state,
authority and idempotent commands, event integrity, real Git workspaces, fenced leases,
observed provider execution, revision-bound candidate QA, live supervision assignments,
material-change gating, incident containment, correction-effectiveness review, and
outcome-driven strategy adaptation. The refactor remains in progress until every case
in `../docs/software-factory-v2-capability-matrix.json` is behaviorally accepted and
the legacy runtime is removed from active execution.

## Local usage

```bash
python -m pip install -e 'runtime[dev]'
software-factory --home /tmp/software-factory init
software-factory --home /tmp/software-factory health
software-factoryd --home /tmp/software-factory --once
```

The `sf-skill` entrypoint is the thin runtime bridge used by the five user-facing skill
interfaces. It does not own a separate ledger or lifecycle.
## Controller and provider lifecycle

The native controller now owns dependency-ready dispatch as one durable transition:
work selection, agent attribution, workspace ownership, assignment, fenced leases,
provider callback capability, and execution creation are recorded before an external
provider starts. Provider results are generation-fenced, single-use, and bound to the
exact execution. Lost leases preserve the workspace and obligation, revoke stale
callbacks, cancel the prior provider when possible, and allow a replacement lane.

`codex_cli` is the default installed provider adapter. Its executable and argument
prefix are external configuration (`SOFTWARE_FACTORY_CODEX_EXECUTABLE` and
`SOFTWARE_FACTORY_CODEX_ARGS`); deterministic and process providers support controlled
integration tests without claiming live Codex credentials were exercised.
