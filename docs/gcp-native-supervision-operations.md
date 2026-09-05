# GCP-native supervision operations

The running GCP Codex daemon owns the tasks. `gcp-codex-supervision.service`
owns recurring wakes and durable delivery receipts. The maintained
`supervision_log.py` owns semantic policy, routing gates and review evidence.
The desktop is not in this control path. This deployment is for one existing
patent task; it does not register desktop management tools or deploy a generic
automation product.

## Installed owners

- Target: `01a06f3e-c732-74b2-bde9-3980430df4de`.
- Native Codex: 0.153.4, using the existing Unix WebSocket at
  `/home/ehs_stillman_gmail_com/.codex-alt/app-server-control/app-server-control.sock`.
- Runtime: `/srv/patent-studio/tooling/gcp-supervision/current`.
- Configuration and SQLite receipts: `/srv/patent-studio/private/gcp-supervision`.
- Canonical semantic records: the `supervision` child of that state directory.
- Unit: `/etc/systemd/system/gcp-codex-supervision.service`, enabled at boot.

| Role | Persistent task | Cadence |
|---|---|---|
| Luna Low liveness | `01a0703f-cf45-7563-844e-23189f5d3573` | 60 seconds |
| Terra Max watcher | `01a0703f-ccd1-7ad2-95a2-9f6052a3d96d` | 1,200 seconds |
| Sol XHigh base reviewer | `01a0703f-c7e6-7ed2-b14b-9543702585c9` | Gated changed-state handoff |
| Sol Max reviewer | `01a07049-61c4-7cf0-b579-8d132303e7c7` | Escalation and 14,400-second effectiveness check |
| Sol XHigh fix executor | `01a0703f-ca57-7023-88c0-b4bb87b951b4` | Gated bounded fix plan only |

The three schedule IDs in `status` are real SQLite owner records. They are
not desktop automation IDs. Five role IDs and three schedule IDs are bound
in canonical policy version 3, group `supervision-group-ddb1c0f5a890b3cd6591602c`.
Routine unchanged checks stay quiet. No Gmail or external notification service
is authorized.

## Inspect and control

Run the storage preflight before state operations:

```sh
/srv/patent-studio/tooling/bin/patent-storage-preflight
python3 /srv/patent-studio/tooling/gcp-supervision/current/gcp_supervision.py status
systemctl status gcp-codex-supervision.service --no-pager
```

`read --thread <bound-id>` returns compact native task state. `turns --thread
<bound-id> --limit 1` returns direct task items with tool outputs omitted.
`helper -- status --target-thread <target-id>` reads canonical semantic status.
The `send` command requires an actual bound role identity and a successful
maintained route gate. A gate approval alone is not a delivery receipt.

`pause` and `resume` toggle future scheduled wakes in this runtime. Pause does
not interrupt already running roles or cancel already owned deliveries. Stop
the service with `sudo systemctl stop gcp-codex-supervision.service` to stop
controller dispatch/reconciliation; existing Codex turns continue. Neither
operation declares the patent mission complete. The legacy helper's desktop
automation/Gmail shutdown workflow is not claimed as supported by this backend.

To recover the controller, use `sudo systemctl restart
gcp-codex-supervision.service`. Reuse the same configuration and SQLite file.
Never delete receipts or recreate role tasks as a retry mechanism. An uncertain
send is reconciled against native queue/history; absence of a receipt never
authorizes a second message. Retained uncertain/failed rows require inspection.
The service retries a temporarily unavailable local daemon and skips a role
while that role is already active. It does not restart the shared Codex daemon.

## Deployment and bootstrap constraints

Install reviewed Python files into a new root-owned release directory, record
their SHA-256 values and source commit in a manifest, atomically replace the
`current` symlink, and restart only this service. Retain the old release. Run
the host preflight and focused tests before installing; validate the unit with
`systemd-analyze verify`. Do not overwrite the independently installed
supervision helper with this worktree's older copy.

For a future explicitly authorized group, use native `thread/start` for each
role with the maintained model/reasoning and rendered role instructions.
Immediately run an initialization-only turn and observe its completed response
before `thread/resume` or configuration changes: a task ID alone does not prove
its first rollout is durable. Create paused schedules, initialize the maintained
canonical group, bind the actual five task and three schedule owner IDs, verify
those bindings, then activate scheduling. Do not reuse this target's IDs.

This bootstrap exposed and retained an unused reviewer ID with no rollout
(`01a0703f-c54e-7052-9068-ce1bb2f6179d`). A replacement was initialized and bound
through the existing canonical policy writer before any schedule delivery.
Policy history and the original task metadata remain intact. The narrowly
guarded bootstrap repair is closed after the first runtime delivery.

Native 0.153.4 `thread/queue/add` can start idle tasks automatically. The runtime
observes native ownership before considering `thread/queue/start`, and retains
the same message identity if a response is lost. Twenty focused tests cover
transport framing/errors, persistence, automatic queue start, ambiguous writes,
active-role handling, pause and rejected routing.

The unit is launched by systemd with an explicit environment and permits only
`AF_UNIX` sockets. Its controller cannot connect to a desktop over IP. Agent
turns execute in the pre-existing GCP daemon. A physical desktop-disconnection
test is not part of this acceptance; local-only transport, actual scheduled
turns and controller restart are directly checked.

## Acceptance evidence

Initial scheduled liveness: turn `01a0704c-b599-74e3-8cfc-7fa5593c0542`.
Initial scheduled watcher: turn `01a0704c-b60f-7c63-941c-89977f1ed24f`.
Changed-state delivery `64112c73-a26b-5c4e-8ed5-18a200ea0bd9` was acknowledged
in base-review turn `01a07054-9676-7161-aed9-7a84f95c16bd`. The reviewer read
the original target delta directly and recorded canonical `EVT-000004`,
`no-intervention`, at 2026-09-05 06:50:30 UTC.

Release and restart evidence is retained in
`/srv/patent-studio/private/gcp-supervision/acceptance.json` once live acceptance
completes. The original patent implementation tracker remains independently
open; installing this monitor does not accept patent content or its dependencies.
