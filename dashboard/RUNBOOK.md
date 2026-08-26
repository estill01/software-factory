# Software Factory dashboard runbook

## Start

From the repository root:

```bash
npm --prefix dashboard/web ci
npm --prefix dashboard/web run build
uv sync --project dashboard/server
uv run --project dashboard/server software-factory-dashboard \
  --host 127.0.0.1 \
  --port 8787 \
  --codex-binary "$(command -v codex)"
```

Open `http://127.0.0.1:8787`. The production service serves the built React
application and `/api/v1` from one loopback origin. Use another unused port if
8787 is occupied; non-loopback binds are rejected.

Before relying on task controls, open **Admin** and confirm that the Codex App
Server row is `Available` and `Compatible`. The frozen contract requires
the exact internal `codex-app-server-client` 0.1.0 wheel, Codex 0.147.0, and
the pinned schema root
`eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`
and selected-surface root
`9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.

## Register a project

In **Admin**, register the canonical Git top-level path and optional relative
Markdown tracker globs. Registration writes discovery metadata only. Archive
hides the catalog row; it never changes the repository or stops work.

The default catalog is:

```text
~/.codex/software-factory/dashboard/projects.json
```

Do not copy task, tracker, supervision, report, or completion state into this
file. Use `--catalog-path` for an isolated test catalog.

## Read the floor

- Expand an implementation row for exact task, run, mission, tracker, active
  Block claims, supervisor group, roles, issues, actions, conclusions, and
  source freshness.
- Treat red, amber, green, and neutral as derived operating posture, not
  completion. The adjacent text states the triggering evidence.
- Treat counts as exact only when the chip says exact. Partial, lower-bound,
  truncated, conflict, none-active, and unavailable labels are intentional.
- Open source links before acting on a disagreement. Task, tracker, and
  supervision claims remain separate even when they refer to the same work.
- Select a predecessor mission only for retained history. Current topology,
  tasks, automations, reports, and controls are suppressed there.

## Review trackers and reports

**Trackers** shows maintained-verifier totals and status counts, every current
task/tracker/supervision active-Block claim, Git currentness, dependencies,
evidence, diagnostics, and bounded semantic source changes. It is not a second
Markdown editor or Block-acceptance path.

**Reports** shows owner-verified weekly, terminal, metrics, and Factory-evolution
artifacts. Numeric cards retain period, time zone, denominator, coverage, and
estimate posture. A report, test, commit, task status, or evolution disposition
does not establish implementation or outcome completion.

## Use a control

1. Inspect the current source posture and disabled-control reason.
2. Open the preview. Verify target, project, owner, source revision,
   currentness fingerprint, route gate, ordinary consequences, failure
   consequences, and the owner-supplied semantic diff.
3. Type the operation-specific confirmation only if those exact consequences
   are intended.
4. Request the operation once. There is no hidden retry or rollback.
5. Wait for `Applied` only when the canonical owner postcondition is re-read.
   `Requested`, `Awaiting approval`, `Pending`, `Partial`, `Failed`, and
   `Unverified` are not success.

Task continue, steer, interrupt, approval, and input responses use the
version-gated Codex owner. Tracker author/review/revise/implement, supervision
attach/check/review/adjust/binding, pause/resume, report, evolution, succession,
and terminal controls route through their named maintained owners. The
dashboard never writes tracker Markdown, supervision ledgers, policies,
automation TOML, report manifests, or Git state directly.

`Interrupt turn`, `Pause supervision`, `Resume supervision`, `Request stop`,
terminal reporting, and terminal shutdown are different operations. Never use
one as evidence for another. Terminal shutdown remains unavailable until the
current lifecycle, incident/decision, successor, delivery, automation, event
head, and receipt gates all agree.

## Recover

| Symptom | Response |
|---|---|
| Frontend unavailable | Run `npm --prefix dashboard/web run build`, then restart the Python service. |
| App Server incompatible | Supply the exact hash-verified internal client wheel and Codex CLI 0.147.0, restart the dashboard, and recheck Admin. Never resolve the client by bare registry name/version. File-backed project/tracker/run/report reads remain usable. |
| App Server disconnected | Use the bounded shared-client restart in Admin. In-flight task requests fail; they are not replayed automatically. |
| Project or tracker unavailable | Inspect the source-local path, permissions, Git posture, verifier diagnostics, and coverage. Other projects remain visible. |
| Stale or expired operation preview | Discard it and preview again. Never reuse a token after source drift or restart. |
| Operation requested but not applied | Read the named owner and canonical postcondition. Preserve partial state; do not infer success or retry automatically. |
| Browser event replay gap | The client invalidates durable queries and reloads them from their owners. The SSE buffer is not a ledger. |
| Catalog current file invalid | The service may project a valid prior file read-only. Correct permissions/content before another catalog mutation. |

## Validate

```bash
uv run --project dashboard/server python -m unittest discover \
  -s dashboard/server/tests -p 'test_*.py'
npm --prefix dashboard/web run check
npm --prefix dashboard/web run build
SOFTWARE_FACTORY_DASHBOARD_URL=http://127.0.0.1:8787 \
  npm --prefix dashboard/web run test:e2e -- --workers=1
```

The browser matrix covers desktop, tablet, and mobile. Final release evidence,
source cross-checks, exact commands, and measured corpus results are recorded in
[`../docs/software-factory-operations-dashboard-validation.md`](../docs/software-factory-operations-dashboard-validation.md).

## Boundaries

The dashboard is local and single-operator. It does not provide remote hosting,
multi-user administration, arbitrary shell or Git execution, raw App Server
methods, general prompts, model/spend changes, tracker acceptance, direct
policy/automation writes, Factory-evolution adoption, or a second operational
ledger. Unsupported capability remains absent or explicitly unavailable.
