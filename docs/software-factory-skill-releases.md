# Software Factory local skill releases

`scripts/skill_release.py` separates mutable Software Factory development from
installed Codex behavior. It owns exactly three skill names:

- `author-implementation-trackers`
- `implement-tracker-blocks`
- `supervise-tracker-runs`

It does not publish remotely, install a plugin, update unrelated skills, or
infer independent acceptance from a commit, manifest, or green test run.

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

~/.codex/skills/
├── author-implementation-trackers -> .../current/author-implementation-trackers
├── implement-tracker-blocks -> .../current/implement-tracker-blocks
└── supervise-tracker-runs -> .../current/supervise-tracker-runs
```

Each manifest binds the exact clean Git commit, all three names, per-skill
content root and file count, the fixed Skill Creator validator's path/content/
result roots, creation time, prior active release, and an externally supplied
independent-review record that names the implementer and exact candidate root.
The release ID is recomputed from that candidate and review; the sealed version
directory is rehashed before every activation and rollback. A separate
HMAC-authenticated acceptance ledger is keyed outside the release root, so a
rewritten manifest cannot authorize itself. The same key authenticates the
semantic activation history used for rollback eligibility.
Manifest and evidence JSON must use exact canonical bytes and remain within
small pre-read limits; acceptance/history ledgers are likewise bounded,
canonical JSONL. Whitespace padding, suffix data, oversized files, and
self-rehashed semantic substitutions reject before cutover.

## Commands and boundaries

`review-request` reads the three trees from an exact 40-character clean Git
commit, runs the fixed installed Skill Creator validator, and emits the exact
candidate projection/root without writing release state. `stage` independently
rebuilds the same projection from Git. It rejects a dirty repository, a missing
skill, any Git symlink or unsupported entry, a failed or substituted validator,
and absent, malformed, same-implementer, stale, repository-owned, or unbound
review evidence. Staging never changes installed discovery paths or `current`.

`bootstrap` is the one-time installation/migration boundary. It requires exact
quiescent-boundary evidence. If legacy direct links exist, all three must point
through the declared legacy source root and their content roots must equal the
reviewed staged baseline. Bootstrap establishes `current`, replaces all three
links with stable links, verifies them in a fresh process, and records the
result. An interruption restores every original link and removes the new
pointer before returning. Partial or mixed installations reject rather than
being repaired speculatively.

`activate` requires the stable-link set already established. It validates the
complete accepted release, atomically renames one temporary `current` symlink,
and never rewrites an installed skill link. A fresh child process resolves and
rehashes all three installed trees after the swap. Any failure restores the old
pointer and removes uncommitted temporary pointers.

`rollback` may select only a release that appears as a prior active release in
the HMAC-authenticated, schema- and transition-validated activation history and
whose external acceptance, manifest, and skill roots still validate. It uses
the same one-pointer cutover and fresh-process verification as activation.
`status` reports the source commit, manifest roots, exact discovery targets,
current resolved roots, and history length without scanning unrelated skills
or repositories.

## Evidence records

The external review JSON has kind
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

Every bootstrap, activation, and rollback similarly consumes an external JSON
record of kind `software-factory-quiescent-boundary`. It binds the operation,
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
  "reviewer_id": "independent-reviewer-1234",
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
  "operator_id": "release-operator-1234",
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

## Reader semantics

The filesystem cutover is atomic at `current`; the Codex host does not expose a
transactional read spanning three skill files. A task that already loaded a
skill continues using that loaded instruction set. A new resolution after the
swap reaches the new complete release. Therefore every bootstrap, activation,
and rollback requires an explicit quiescent-boundary record, and operators must
start a new task or restart Codex when they need the host to load the new
instructions. The generated post-swap proof establishes a new filesystem
resolution; it is not represented as proof that an already-running task
reloaded itself.

## Development-live mode

Pointing discovery links directly at a mutable checkout intentionally restores
immediate live editing. That mode is visibly unsafe: a rejected or unfinished
edit can change the next skill resolution without staging, exact review,
activation, or rollback evidence. Use it only under an explicit development
request; the maintained workflow remains edit/test, freeze, independent review,
stage, bootstrap or activate, verify, and start a new task.
