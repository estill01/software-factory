---
name: supervise-tracker-runs
description: Supervise live Software Factory v2 work, incidents, adaptation, reflection, and acceptance.
---

# Native Software Factory v2 interface

This skill is a thin invocation and role contract. The installed SQL-backed v2
runtime is the only active control-plane owner. Do not write or reactivate files
under `legacy/v1`.

Resolve the governing mission and invoke:

```bash
sf-skill supervise-tracker-runs --mission <mission-id> --payload '<json-object>'
```

Treat the returned record as an observed runtime result, not as authority to
invent completion. Continue through the native runtime until obligations are
accepted, terminal verification passes, or a genuinely reserved external effect
is recorded with its exact blocker. Do not create a parallel file ledger, event
log, scheduler, acceptance owner, or release owner in this skill directory.
