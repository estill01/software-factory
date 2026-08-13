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

`activate` requires the stable-link set already established. It validates the
complete accepted release, atomically renames one temporary `current` symlink,
and never rewrites an installed skill link. A fresh child process resolves and
rehashes all three installed trees after the swap. Any failure restores the old
pointer and removes uncommitted temporary pointers. The release lock, atomic
swap, fresh-process verification, and automatic restoration are the default
cutover guard. `--quiescent-evidence` remains available when an operator
deliberately requires an independently signed boundary.

`rollback` may select only a release that appears as a prior active release in
the HMAC-authenticated, schema- and transition-validated activation history and
whose canonical acceptance, manifest, and skill roots still validate. It uses
the same one-pointer cutover and fresh-process verification as activation.
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
a second promotion. The atomic `current` swap updates the
next scheduled monitor wake while preserving its automation ID, target thread,
schedule, model, reasoning, status, and notification posture. An already-running
turn may finish with the instruction bytes loaded before the swap. Legacy
release-pinned automation prompts receive one post-activation migration to the
stable paths; later releases require no prompt rewrite. Each wake rehydrates
policy, mission, requested range, active frontier, and lifecycle posture from
the current helper instead of trusting copied prompt values.

Run `software-factory-supervisor-refresh-plan` with the canonical promotion
record to derive that one-time migration. The command is read-only: it never
writes `current`, an automation file, a schedule, or a role thread. It reopens
the promoted non-HEAD source from an exact checkout, requires the release owner
to return the same active source, release, three installed roots, verification
root, and activation-history count twice, and joins them to the current
mission-owned range plus stable policy/event heads.

For each policy-bound heartbeat, the plan reads the Codex automation owner from
the canonical operating-system account, rejects symlinks, path escapes,
oversized or changing files, and returns the exact prior config identity. A
legacy release-specific or maintained installed-stable prompt is projected
once onto `current`; copied release hashes and mission/policy/Block/frontier
prose are removed as authority. The returned `preserved_config` is every field
except `prompt` and owner-generated `updated_at`, and must be supplied unchanged
to the Codex automation owner. Paused automations and explicit
`manual-release-pin:<release-id>` channels are held. Re-running after the owner
update yields no prompt migration.

The safe boundaries are owner-derived, never caller booleans: a heartbeat sees
the new prompt only at its next scheduled wake, while already-running configured
roles receive a `thread-route-gate` receipt for purpose `role-refresh` and load
the verified release at the next role-message boundary. Existing in-progress
instruction bytes are unchanged. Consumers must re-run the planner at the
write boundary and verify the owner view afterward; the plan is a currentness-
bound action projection, not an automation writer or durable release grant.

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
