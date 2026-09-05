# Native runtime selection and boot

The native backend reuses the target host's running Codex app-server Unix socket.
It owns recurring wake state in SQLite and delivers to the same persistent role
tasks. The helper remains the sole semantic policy and evidence owner. The app
backend remains supported when its actual controls are callable; it uses the
ordinary skill boot procedure. A laptop controlling a remote task must discover
the owner on that remote host before creating anything locally.

## Discover before mutation

Run the installed `scripts/supervision_runtime.py discover --target-thread ID`.
Its default native root is `/srv/patent-studio/private/gcp-supervision`; pass
`--native-root` for another configured host location. It reads the legacy
`config.json` and immediate `groups/*/config.json` records without opening a
writable database. Existing exact-target ownership wins over app availability.
Multiple matching owners, unreadable owner records or an unavailable bound
socket require reconciliation; they never authorize a duplicate group.

Without an existing group, pass `--app-tools-available` only after discovering
callable app creation, reading, sending and automation controls. Otherwise the
script probes the explicit `--socket` or the current `CODEX_HOME` app-server
control socket and proves it can read the exact target. `owner-access-required`
means neither supported path was proven; name the missing capability precisely.
Do not invent automation IDs or infer successful supervision from code alone.

## Native bootstrap

Use the host's storage preflight before writes. On Patent Studio GCP all state,
role working directories, databases and substantial temporary data belong on
the mounted `/srv/patent-studio` disk. Preserve an existing group's config,
service, schedules and history. New groups use `groups/<exact-target-id>`.

Create a small immutable mission source document containing the exact current
user objective, required effects, boundaries and completion condition. Bind its
hash and exact direct-source record; do not bind a mutable tracker status as
if every progress edit created a new mission. Include later tracker dependencies
without granting authority to implement unrelated programs.

Run the following using absolute installed paths and the exact same arguments
on subsequent calls:

```text
python3 /installed/supervise-tracker-runs/scripts/supervision_runtime.py bootstrap
  --config /native/root/groups/ID/config.json
  --target-thread ID --label "short target label"
  --socket /actual/codex-home/app-server-control/app-server-control.sock
  --helper /installed/supervise-tracker-runs/scripts/supervision_log.py
  --mission-file /native/root/groups/ID/mission.md
  --mission-source-record direct-user:exact-source-record
```

The displayed command wraps for readability; use structured subprocess argv or
proper shell continuation. Each call advances one bounded step. Allow an active
initialization turn to finish before the next call; do useful independent work
while waiting. Five role tasks receive initialization-only turns before resume,
then receive the full role through `thread/settings/update` collaboration
settings and complete their bound full-role initialization. `thread/resume`
alone does not reliably replace instructions on an already loaded task. Observe
an actual bounded role action after activation; `INITIALIZED` alone cannot prove
that later scheduled turns use the assignment. The bootstrap retains exact
task/turn IDs and never creates another task after an ambiguous create response.
Resolve such uncertainty from the native owner's exact request/task evidence.

When a bound role is no longer loaded, delivery reuses the same model, working
directory, instructions, reasoning, sandbox and approval settings as role boot.
The native response must confirm writable helper access before any work is
queued; a rejected restoration leaves a new delivery failed for owner reconciliation.
An earlier possibly accepted send stays uncertain until its original native
receipt can be reconciled after role access is restored; it is never resent.
The existing runtime health store retains the role's restoration requirement
across later delivery IDs, transport failures and runtime restarts. Only a
confirmed native response clears that requirement.
Resuming the implementation target does not replace its own settings.

Reviewer sealing uses the existing account's `.codex/software-factory-release-authority`
and `.codex/software-factory-release-private` stores. The reviewer key identity
is unchanged. macOS retains its exact reviewed Homebrew verifier; Linux has an
exact `/usr/bin/openssl` binary profile. Missing keys, changed binaries, or a
private key deriving a different public identity fail closed. Provisioning the
existing key belongs to its external custodian; native boot does not generate
replacement keys, copy credentials, or infer successful sealing from review prose.

Once roles are initialized, bootstrap creates three paused schedules, initializes
and binds the maintained semantic helper, and verifies actual initialization,
role identity, mission and schedule agreement. Repeating a ready bootstrap
verifies the same group; it does not replace it. A `ready` response means bound
and paused, not active monitoring.

## Persistent service and activation

Reuse `gcp_supervision.py` with an explicit `--config` in every service and role
command. On GCP install a distinct systemd unit rendered by
`supervision_runtime.systemd_unit`, with explicit account, Codex home, persistent
temporary path, storage preflight and only this group's writable state root.
Review the unit and run `systemd-analyze verify` before installing/enabling it.
Never repoint the legacy `gcp-codex-supervision.service` to a different target.
The host service owns scheduling; it does not require a connected desktop.

Start the service while schedules are paused, then run the explicit-config
runtime's `resume`. This verifies the complete binding before enabling schedules.
Observe a scheduled wake and actual role-gated delivery; queued/uncertain is not
delivery. Verify restarting only the new service retains IDs, due times and
receipts without duplicate messages. Report physical laptop compatibility as
unverified unless observed there; fake tests are not physical deployment proof.

The runtime's `status`, `read`, `turns`, `helper --`, `send`, `pause` and `resume`
operate only within the selected group. `send` authenticates the calling bound
role using its native task environment and invokes `thread-route-gate` itself.
Use `send --action <concise-exact-action> --message <full-evidence-packet>`:
the helper's 240-character action field describes the requested operation;
the message retains the complete bounded evidence packet. Recipient, purpose,
source and authority checks still run before delivery. Omitting `--action`
preserves the earlier short-message behavior.
For `status-broadcast`, the action must remain the exact message because its
canonical broadcast envelope binds the payload hash; differing text is rejected.
Completion-review role prompts include the exact maintained reconciliation
schema; do not guess its wire shape.
Never set another role's `CODEX_THREAD_ID` or manufacture a successful receipt.
An explicitly authorized target-owner bootstrap may dispatch the first ordinary
watcher check through the runtime; all subsequent role communication is gated.

Native schedule IDs belong to SQLite, not app `automation.toml` files. Native
pause/resume proves schedule state; it does not manufacture the helper's legacy
app-owner semantic resume or terminal-shutdown receipt. Keep those claims distinct.
Send email only under explicit user authorization; without it retain material
findings locally and use permitted task steering. Routine unchanged wakes stay
quiet. Do not introduce notification setup as a new user gate.

## Installation boundary

Preserve accepted releases. Install the reviewed native runtime and skill files
as a retained host release with a stable discovery entry point. Do not replace
newer semantic helpers with the older native prototype or disturb another
group's installed runtime. Source files and desktop-path instructions must also
be committed and pushed so the same skill repair can be installed on the laptop.

Archive every repository-relative path in `assets/native-release-paths.json`
from the same reviewed source commit, preserving their sibling layout beneath
the release root. The range owner loads `program_revision.py` and its full
tracker verifier from `author-implementation-trackers/scripts`; installing only
the supervision directory omits those required dependencies. Include every
archived file in the host installation hash manifest. Keep the existing verifier
implementations and resolution rules; do not copy their logic into supervision
or substitute a mutable source checkout for the retained release.
