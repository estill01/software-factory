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
├── activation-history.jsonl
└── .release.lock

~/.codex/skills/
├── author-implementation-trackers -> .../current/author-implementation-trackers
├── implement-tracker-blocks -> .../current/implement-tracker-blocks
└── supervise-tracker-runs -> .../current/supervise-tracker-runs
```

Each manifest binds the exact clean Git commit, all three names, per-skill
content root and file count, validator result roots, creation time, prior active
release, and an externally supplied independent-review identity/record/root.
The content-addressed version directory is rehashed before every activation and
rollback. A manifest cannot authorize itself.

## Commands and boundaries

`stage` reads the three trees from an exact 40-character Git commit rather than
the worktree. It rejects a dirty repository, a missing skill, any Git symlink or
unsupported entry, a failed validator, and absent or malformed independent
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
the validated activation history and whose manifest and skill roots still
validate. It uses the same one-pointer cutover and fresh-process verification as
activation. `status` reports the source commit, manifest roots, exact discovery
targets, current resolved roots, and history length without scanning unrelated
skills or repositories.

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
