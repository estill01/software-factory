# Software Factory local skill releases

`scripts/skill_release.py` separates mutable Software Factory development from
installed Codex behavior and makes ordinary local promotion one automated,
rollback-safe operation. It owns exactly three skill names:

- `author-implementation-trackers`
- `implement-tracker-blocks`
- `supervise-tracker-runs`

It does not publish remotely, install a plugin, or update unrelated skills.

## State layout

The default release root is
`~/.codex/software-factory-releases` and the default discovery root is
`~/.codex/skills`:

```text
~/.codex/software-factory-releases/
├── releases/<release-id>/
│   ├── release-manifest.json
│   ├── author-implementation-trackers/
│   ├── implement-tracker-blocks/
│   └── supervise-tracker-runs/
├── current -> releases/<release-id>
├── accepted-releases.jsonl
├── activation-history.jsonl
├── installed-link-recoveries.jsonl
├── installed-link-recovery-pending.json  # only while recovery is pending
└── .release.lock

~/.codex/.software-factory-release-keys/
└── <release-root-hash>.key

~/.codex/software-factory-release-authority/operators/
├── software-factory-release-operator-v1.pem
└── software-factory-release-operator-v1.ledger.jsonl

~/.codex/skills/
├── author-implementation-trackers -> .../current/author-implementation-trackers
├── implement-tracker-blocks -> .../current/implement-tracker-blocks
└── supervise-tracker-runs -> .../current/supervise-tracker-runs
```

Each manifest binds the exact clean Git commit, all three names, per-skill
content root and file count, the fixed Skill Creator validator's path/content/
result roots, creation time, prior active release, and either automated check
results or an optional externally supplied independent review. The release ID
is recomputed from that candidate and assurance; the sealed version
directory is rehashed before every activation and rollback. A separate
HMAC-authenticated acceptance ledger is keyed outside the release root, so a
rewritten manifest cannot authorize itself. The same key authenticates the
semantic activation history used for rollback eligibility.
Manifest and evidence JSON must use exact canonical bytes and remain within
small pre-read limits; acceptance/history ledgers are likewise bounded,
canonical JSONL. Whitespace padding, suffix data, oversized files, and
self-rehashed semantic substitutions reject before cutover.

## Commands and boundaries

`promote` is the ordinary path. It reads an exact 40-character clean Git commit,
runs the fixed installed Skill Creator validator and all four repository-owned
test suites in a detached exact-commit checkout, stages a sealed release,
atomically selects it, verifies it from a fresh process, and restores the prior
pointer on any post-swap failure. The HMAC-authenticated ledgers retain the exact
candidate, automated assurance, cutover, and rollback history. A green suite
passes directly. If a suite already fails in the active exact commit, the owner
runs that same suite against the baseline and permits only an identical or
smaller failure set; any new failure blocks promotion. Inherited failures remain
counted and labeled `passed-with-baseline` rather than being called green.

`review-request` and `stage --review-evidence ...` retain the stricter optional
separation-of-duties path. `stage` without review evidence uses the same
automated checks as `promote`. Both paths reject a dirty repository, a missing
skill, Git symlinks or unsupported entries, and failed validation or tests.
Staging never changes installed discovery paths or `current`.

`bootstrap` is the one-time installation/migration boundary. If legacy direct
links exist, all three must point
through the declared legacy source root and their content roots must equal the
staged baseline. Bootstrap establishes `current`, replaces all three
links with stable links, verifies them in a fresh process, and records the
result. An interruption restores every original link and removes the new
pointer before returning. Partial or mixed installations reject rather than
being repaired speculatively.

`recover-installed-links` is a narrowly bounded recovery owner for a complete
development-override link set left in place after an otherwise current release
activation. It is not an alternate promotion or pointer-selection path. The
command accepts only the exact repository, override source commit, expected
candidate child commit, expected current release, and expected activation-record
HMAC. Production always resolves the canonical release, install, and
development-override roots; callers cannot select any of them.

Before mutation and again under the release-owner lock, recovery requires all
three installed links to name one sealed commit-rooted override, verifies its
path, modes, and bytes against `git archive` (including declared
`export-subst` transformations), verifies active-to-override ancestry and the
candidate's exact override parent, and rechecks the current pointer and
activation-history HMAC. Before replacing the first link, it durably records an
HMAC-authenticated recovery intent bound to those identities, the retained
recovery-ledger prefix, and the exact original and desired complete link sets.
It then replaces the complete set with the stable `current/<skill>` links and
performs child-process plus in-process installed verification without moving
`current`.

A retry with that intent deterministically reconciles exact override, partial,
or stable effects under the same owner lock. Partial effects are restored to
and reverified against the exact sealed override before another complete swap;
valid stable effects are freshly reverified before finalization. The verified
intent retains the exact signed receipt while an absent or partially persisted
receipt suffix is completed, so an ambiguous append cannot separate the links
from recoverable owner state. The intent is removed only after the canonical
HMAC-chained `installed-link-recoveries.jsonl` receipt is durably complete. An
exact later retry returns that receipt idempotently, while pointer, activation,
link, archive, lineage, intent, or ledger drift fails closed. Caught failures
before receipt commitment restore and reprove all three original override
links. Release acceptance and activation histories are byte-unchanged by
link-only recovery.

`activate` requires the stable-link set already established. It validates the
complete accepted release, atomically renames one temporary `current` symlink,
and never rewrites an installed skill link. A fresh child process resolves and
rehashes all three installed trees after the swap. Any failure restores the old
pointer and removes uncommitted temporary pointers. The release lock, atomic
swap, fresh-process verification, and automatic restoration are the default
cutover guard. `--quiescent-evidence` remains available when an operator
deliberately requires an independently signed boundary.

`adopt` is the bounded composition used by the separately governed Factory
adoption gate. It first performs exact reviewed staging, requires the active
installed release to match the named baseline commit, then uses the same
one-pointer `activate` boundary. At that locked boundary it compares both the
expected prior release ID and the prior activation-history HMAC, so an
intervening release or an A-to-B-to-A history change rejects before the
operator record is consumed or the pointer is written. If activation completed
before its caller could record the adoption, an identical retry rehydrates the
exact manifest,
acceptance, activation, and installed verification roots without consuming a
second operator record. Rehydration requires one unique activation of that
candidate from the named baseline; later reactivation history rejects as
ambiguous. It does not decide eligibility, expand permissions, or
accept a `promote` artifact as release evidence.

`rollback` may select only a release that appears as a prior active release in
the HMAC-authenticated, schema- and transition-validated activation history and
whose canonical acceptance, manifest, and skill roots still validate. It uses
the same one-pointer cutover and fresh-process verification as activation.
The supervisor-owned health path also supplies the exact current release ID
and current activation-record HMAC that it just observed. The release owner
checks both under its release lock before changing the pointer, so a newer
valid activation wins and a stale health rollback is rejected without
overwriting it. These expected-current inputs are internal owner guards, not a
caller-selectable release or rollback authority.
`status` reports the source commit, manifest roots, exact discovery targets,
current resolved roots, and history length without scanning unrelated skills
or repositories.

## Automatic monitor updates

Scheduled supervisor automations bind to the stable installed paths below, not
to `releases/<release-id>` directories:

```text
~/.codex/software-factory-releases/current/supervise-tracker-runs/SKILL.md
~/.codex/software-factory-releases/current/supervise-tracker-runs/references/supervision-policy.md
~/.codex/software-factory-releases/current/supervise-tracker-runs/scripts/supervision_log.py
```

After an exact accepted commit is available locally, the independent release
reviewer signs the exact `software-factory-release-acceptance` object and
supervision ingests it with `supervision_log.py
software-factory-release-accept`. The canonical event retains the signed source,
tree, reviewer authority, root, and no-findings disposition; a generic
caller-authored checkpoint is nonauthorizing. Its policy version must remain
current when promotion begins. Supervision then runs
`supervision_log.py software-factory-release-promote`. That seam accepts only
the exact clean HEAD and canonical acceptance record, invokes the ordinary
owner's flagless `skill_release.py promote --repo ... --source-commit ...`, and
revalidates the returned active identity and three installed roots through live
owner status. The owner subprocess uses the canonical operating-system account
home and a minimal fixed Python/Git environment; caller `HOME`, `PYTHONPATH`,
and Git overrides cannot redirect the release or installation roots. Identical
accepted revisions reuse the one retained promotion;
there is no caller active-release, pointer, or manual-pin input. An explicit
manual pin is a separate policy-owned exception, not a promotion-command
choice. Before invoking the owner, orchestration retains one canonical
promotion requirement with the exact acceptance and prior live release
identity, three installed roots, verification root, and history count. If a
newer signed acceptance for the same source becomes current before any owner
effect, the lock may append one linear successor requirement only while all of
that prior state remains exact; the retired acceptance never invokes the
owner. The event-owner lock serializes the bounded owner effect and result;
an interrupted retry rehydrates the one completed transition from live owner
status. A changed predecessor or activation-history count observed after the
effect is retained as a canonical currentness rejection, so retry never performs
a second promotion. The returned owner effect is validated before the live
status observation; if a later activation wins between those calls, the exact
effect is still durably recorded as rejected rather than being retried. The
atomic `current` swap updates the
next scheduled monitor wake while preserving its automation ID, target thread,
schedule, model, reasoning, status, and notification posture. An already-running
turn may finish with the instruction bytes loaded before the swap. Legacy
release-pinned automation prompts receive one post-activation migration to the
stable paths; later releases require no prompt rewrite. Each wake rehydrates
policy, mission, requested range, active frontier, and lifecycle posture from
the current helper instead of trusting copied prompt values.

`software-factory-supervisor-refresh-plan` reads only the exact automation IDs
bound by the current supervisor policy. A canonical implementation range is
mandatory; an absent range rejects the plan rather than treating an unbounded
target as refreshable. It verifies that each heartbeat belongs
to a configured runtime role, projects the prompt onto the three stable
`current` paths, removes copied release hashes and policy/range/frontier claims,
and emits the complete non-prompt configuration that the Codex automation owner
must preserve. Paused automations remain paused; explicit
`manual-release-pin:<release-id>` prompts remain pinned. Already-running roles
receive the same activated identity through the existing `role-refresh` route at
their next message boundary.

Refresh health appends `verified` only after checking the installed release,
stable automation-owner bytes, and governing control posture. It then rereads
the policy and exact range root, promotion, complete refresh plan,
automation-owner roots, release activation-history count and record HMAC, and
control posture at the append boundary. Drift is retained under the newly
current policy as a successor `currentness-rejected` event, so retry can finish
the correction even when the policy or range changed. Rollback then requires
both the original promotion history count and an expected-current owner guard.
A same-ID reactivation or newer unrelated release is never rolled back; an
already-restored prior release is recorded without a second owner effect.
Preserved schema-v1 rollback health remains a terminal historical result: a
retry rehydrates its exact record after proving the live prior-release identity
instead of synthesizing an incompatible schema-v2 duplicate.

## Independent acceptance and optional release-owner evidence

The signed `software-factory-release-acceptance` is the exact independent
acceptance trigger itself. It is not a second promotion authorization, and the
ordinary release-owner call still needs neither `--review-evidence` nor signed
quiescence evidence. The release owner's optional external review JSON has kind
`software-factory-skill-release-review`, disposition `accepted`, distinct
`reviewer_id` and `implementer_id`, the exact source commit and candidate root,
a timestamp, bounded exact evidence references, and `review_root_sha256` over
every substantive field before the root/signature are attached. It must live
outside both the source repository and release root. The independent reviewer
signs the complete record (including that root)
with a private Ed25519 key. Staging resolves the corresponding sealed public
key only from the non-CLI-configurable
`~/.codex/software-factory-release-authority/reviewers/<reviewer-id>.pem`
trust root and verifies its content root and detached signature.

When `--quiescent-evidence` is supplied, bootstrap, activation, and rollback
consume an external JSON record of kind
`software-factory-quiescent-boundary`. It binds the operation,
candidate and previous release IDs, operator, observation time, explicit
`no_concurrent_skill_resolutions: true`, bounded evidence references, and an
exact `evidence_root_sha256`. Caller-supplied record/root strings are not an
accepted substitute for either evidence object. A separately trusted release
operator signs this record through the sealed `operators/` public-key root.
The observation must be current (no more than ten minutes old or one minute in
the future) and its record/root is single-use in the authenticated activation
history, so a prior A-to-B boundary cannot be replayed after rollback.

Review evidence shape (the root excludes `review_root_sha256` and
`signature_base64`; the signature covers the canonical object including the
root and excluding only `signature_base64`):

```json
{
  "schema_version": 1,
  "kind": "software-factory-skill-release-review",
  "record_id": "block2-review-a62d8e7",
  "reviewer_id": "software-factory-release-reviewer-v1",
  "implementer_id": "implementation-owner-1234",
  "disposition": "accepted",
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "candidate_root_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reviewed_at": "2026-08-09T12:00:00+00:00",
  "evidence": ["exact-commit review", "focused adversarial validation"],
  "authority_key_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "review_root_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "signature_base64": "<detached Ed25519 signature>"
}
```

Quiescent-boundary shape (root and signature coverage follow the same rule):

```json
{
  "schema_version": 1,
  "kind": "software-factory-quiescent-boundary",
  "record_id": "cutover-boundary-1234",
  "operator_id": "software-factory-release-operator-v1",
  "authority_sequence": 2,
  "previous_authority_record_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "operation": "activate",
  "release_id": "0123456789ab-0123456789ab",
  "previous_active_release_id": "fedcba987654-fedcba987654",
  "observed_at": "2026-08-09T12:05:00+00:00",
  "no_concurrent_skill_resolutions": true,
  "evidence": ["quiescent task boundary", "new resolution allowed after swap"],
  "authority_key_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "evidence_root_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "signature_base64": "<detached Ed25519 signature>"
}
```

## Provision and sign external authority evidence

Provisioning is an out-of-band authority action, not an implementer or release
command. The independent reviewer owns the reviewer private key; the cutover
operator owns a different operator private key. Neither private key belongs in
the repository, release root, evidence JSON, shell history, or activation
ledger. This release pins the exact OpenSSL verifier at
`/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl` and recognizes only the
versioned role IDs shown below.

Run this once from the corresponding authority context, substituting an
external private-key directory that only that role can read:

```bash
AUTHORITY_ROOT=/Users/ethanstillman/.codex/software-factory-release-authority
PRIVATE_ROOT=/absolute/external/private-key-directory
OPENSSL=/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl

mkdir -p "$AUTHORITY_ROOT/reviewers" "$AUTHORITY_ROOT/operators" "$PRIVATE_ROOT"
chmod 700 "$AUTHORITY_ROOT" "$AUTHORITY_ROOT/reviewers" \
  "$AUTHORITY_ROOT/operators" "$PRIVATE_ROOT"

"$OPENSSL" genpkey -algorithm Ed25519 \
  -out "$PRIVATE_ROOT/software-factory-release-reviewer-v1.private.pem"
"$OPENSSL" pkey \
  -in "$PRIVATE_ROOT/software-factory-release-reviewer-v1.private.pem" -pubout \
  -out "$AUTHORITY_ROOT/reviewers/software-factory-release-reviewer-v1.pem"

"$OPENSSL" genpkey -algorithm Ed25519 \
  -out "$PRIVATE_ROOT/software-factory-release-operator-v1.private.pem"
"$OPENSSL" pkey \
  -in "$PRIVATE_ROOT/software-factory-release-operator-v1.private.pem" -pubout \
  -out "$AUTHORITY_ROOT/operators/software-factory-release-operator-v1.pem"

chmod 400 "$PRIVATE_ROOT"/*.private.pem
chmod 444 "$AUTHORITY_ROOT"/*/*.pem
chmod 555 "$AUTHORITY_ROOT" "$AUTHORITY_ROOT/reviewers" \
  "$AUTHORITY_ROOT/operators"
```

Put the SHA-256 of the corresponding public PEM in
`authority_key_sha256`. Create the unsigned material with every field shown in
the applicable schema except its root and `signature_base64`. Then use this
exact canonical root/sign procedure; use `review_root_sha256` for review
evidence or `evidence_root_sha256` for quiescent evidence:

```bash
/usr/bin/python3 - "$UNSIGNED_JSON" "$ROOTED_JSON" "$ROOT_FIELD" <<'PY'
import hashlib, json, pathlib, sys
source, destination, root_field = sys.argv[1:]
value = json.loads(pathlib.Path(source).read_bytes())
canonical = lambda item: json.dumps(
    item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode("utf-8")
value[root_field] = hashlib.sha256(canonical(value)).hexdigest()
pathlib.Path(destination).write_bytes(canonical(value))
PY

/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl pkeyutl -sign \
  -inkey "$PRIVATE_KEY" -rawin -in "$ROOTED_JSON" -out "$SIGNATURE_BIN"

/usr/bin/python3 - "$ROOTED_JSON" "$SIGNATURE_BIN" "$FINAL_JSON" <<'PY'
import base64, json, pathlib, sys
rooted, signature, destination = sys.argv[1:]
value = json.loads(pathlib.Path(rooted).read_bytes())
value["signature_base64"] = base64.b64encode(
    pathlib.Path(signature).read_bytes()
).decode("ascii")
payload = json.dumps(
    value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode("utf-8") + b"\n"
pathlib.Path(destination).write_bytes(payload)
PY
```

For the optional signed mode, the reviewer independently compares
`review-request` output with the exact source commit before signing. The
operator creates quiescent evidence only
after observing the named current release and no concurrent skill resolution;
its timestamp must still be current at cutover. Before rooting it, set
`authority_sequence` to the current operator-ledger length plus one and
`previous_authority_record_sha256` to the prior head's
`evidence_root_sha256` (or `null` for genesis). After signing, the operator—not
the activation caller—appends the exact canonical final JSON as one line and
reseals the ledger:

```bash
OPERATOR_LEDGER="$AUTHORITY_ROOT/operators/software-factory-release-operator-v1.ledger.jsonl"
chmod 755 "$AUTHORITY_ROOT/operators"
test ! -e "$OPERATOR_LEDGER" || chmod 644 "$OPERATOR_LEDGER"
/usr/bin/python3 - "$FINAL_JSON" "$OPERATOR_LEDGER" <<'PY'
import json, pathlib, sys
source, ledger = map(pathlib.Path, sys.argv[1:])
value = json.loads(source.read_bytes())
line = json.dumps(
    value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode("utf-8") + b"\n"
with ledger.open("ab") as destination:
    destination.write(line)
PY
chmod 444 "$OPERATOR_LEDGER"
chmod 555 "$AUTHORITY_ROOT/operators"
```

Verify a final record by
removing only `signature_base64` and running `openssl pkeyutl -verify -pubin`
against the pinned public key and base64-decoded signature; the release command
performs the same check again.

Recovery fails closed: never delete/re-root the external HMAC key, operator
authority ledger, or authority public keys, and never regenerate a private key
under an existing role ID. If a
private key is lost, retain its public key for old-release verification, add a
new versioned role ID/public key only in a newly reviewed release-helper source
revision, and generate new evidence. If the pinned Python, YAML, validator, or
OpenSSL identity changes, update those identities through the same exact-source
review path; do not bypass the check with `PATH` or a CLI override.

## Reader semantics

The filesystem cutover is atomic at `current`; the Codex host does not expose a
transactional read spanning three skill files. A task that already loaded a
skill continues using that loaded instruction set. A new resolution after the
swap reaches the new complete release. Operators must start a new task or
restart Codex when they need the host to load the new instructions. The
generated post-swap proof establishes a new filesystem resolution; it is not
represented as proof that an already-running task reloaded itself. A signed
quiescent record is optional because it cannot make an already-loaded prompt
transactional; the atomic pointer and fresh-process verification protect the
filesystem boundary that the release owner can actually control.

## Development-live mode

Pointing discovery links directly at a mutable checkout intentionally restores
immediate live editing. That mode is visibly unsafe: a rejected or unfinished
edit can change the next skill resolution without staging, exact review,
activation, or rollback evidence. Use it only under an explicit development
request; the maintained workflow remains edit, test, promote, verify, and start
a new task. Use the optional signed path only when separation of duties is a
real requirement for that release.
