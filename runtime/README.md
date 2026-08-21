# Software Factory 2.0 Runtime

The native runtime is a transactional, SQL-backed control plane for autonomous
multi-agent software implementation. Git owns source history, SQLite owns current
operational and learning state, and a content-addressed artifact store owns command,
test, report, and provider evidence.

Current implemented foundation includes mission/capability/obligation/program state,
authority and idempotent commands, event integrity, real Git workspaces, fenced leases,
observed command execution, and revision-bound candidate QA. The refactor remains in
progress until every case in `../docs/software-factory-v2-capability-matrix.json` is behaviorally accepted and
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
