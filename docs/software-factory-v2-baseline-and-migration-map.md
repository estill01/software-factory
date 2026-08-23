# Software Factory v2 baseline and migration map

This document is the human-readable companion to
[`software-factory-v2-baseline.json`](software-factory-v2-baseline.json). The
JSON file is the executable inventory; this document explains the migration
decisions. Both are Block 0 evidence, not a runtime registry.

## Frozen source

| Field | Frozen value |
|---|---|
| Branch | `agent/software-factory-v2-native-refactor` |
| Commit | `63bb9f3a69bcb5dba0e4b2fe652dce5af7169ae4` |
| Tree | `79d758db7e36aa45a34d0af96b676344321e953b` |
| Remote parity | `origin/agent/software-factory-v2-native-refactor` at the same commit; ahead `0`, behind `0` |
| Tracked files | `366` |
| Main integration | Deliberately deferred until the complete v2 program is accepted |

The frozen commit is the canonical v2 implementation base. Later Block
commits must keep it as an ancestor; they do not rewrite this baseline to make
old proof look current.

## Product-capability decision

Block 0 uses a bounded-general evidence seam: a machine-checkable manifest and
this readable map. A prose-only inventory could not reject an unmapped path or
duplicate table. A new runtime registry or database would add an unrequested
authority before the persistence boundary is repaired. The selected seam is
therefore reusable across later Blocks without changing runtime behavior.

## Current source surfaces

The manifest records immutable tree and path-set roots for all consequential
production surfaces:

| Surface | Files | Target owner | Treatment |
|---|---:|---|---|
| `runtime/src/software_factory` | 71 | mission runtime plus software profile | adapt, then split at typed boundaries |
| dashboard server package | 12 | service/API and provider adapter | adapt |
| dashboard web source | 71 | operator surface | adapt |
| tracker authoring skill | 11 | tracker-authoring capability | adapt |
| tracker implementation skill | 27 | tracker-execution capability | adapt |
| supervision skill | 26 | supervision capability | adapt |
| product-evolution skill | 30 | program-evolution capability | adapt |
| scripts | 14 | qualification and release | adapt |
| workflows | 13 | qualification and release | adapt |

Every tracked path at the frozen commit has exactly one top-level rule in the
manifest. Documentation is evidence-only; the 12 pending markers and four
upload chunks are integration residue assigned to Block 11 retirement.

## Authority and module treatment

| Current path/domain | Current role | Permanent owner | Treatment and removal condition |
|---|---|---|---|
| mission/work core and store | mission, obligation, work, execution state | mission runtime | retain; consolidate persistence in Block 1 |
| `reflection.py` | reflection and hypothesis semantics | libRSI integration | replace in Block 7 after pinned conformance and old-writer shutdown |
| `learning.py` | event ingestion, detectors, interpretation, routes | runtime for execution; libRSI for interpretation | split in Block 7; keep the governed detector runtime local |
| `evolution.py` | selection plus program/Git effects | runtime host adapter; libRSI selection | adapt in Block 7; delete generic local selection policy after parity |
| `problem_solving.py` | generic problem-solving sequence | libRSI integration | replace in Block 7 after operational/restart equivalence |
| `governance.py` | identities, scopes, authorization, acceptance mutation | mission-runtime governance | retain; generic review policy may be consumed from libRSI |
| `workspaces.py` | software-specific workspace effects | software profile | move in Block 5 after dependency-direction proof |
| `providers.py` and controller | provider lifecycle and callback ownership | outer-host provider adapter | adapt in Block 3; only the active outer host launches processes |
| dashboard `app_server.py` | local Codex process and JSON-RPC client | utils client behind a Factory adapter | replace in Block 4 only from an accepted immutable utils handoff |

Local and future implementations are not both declared authoritative. Planned
libRSI and unapplied v2 tables are recorded as overlaps or shadow candidates,
while every domain retains exactly one current writer and one target owner.

## Persistence baseline

`schema.py` applies nine migration files through schema version 9. A fresh
database contains 48 user tables including `schema_migrations`. The SQL source
also contains 51 defined-but-not-applied tables: the orphan
`0008_supervision.sql` branch and migrations `0010` through `0017`. Migrations
`0018` and `0020` alter later tables but are also not applied, and version 19
is absent. Twelve table names are referenced by runtime code without any
`CREATE TABLE` definition.

The complete table lists and their one target owner/disposition are in the
manifest. Block 1 must choose one monotonic migration history, supply every
runtime-required table, preserve checksum drift rejection, and remove inert or
duplicate schema authority. Block 0 does not activate any migration.

## Compatibility matrix

| Route | Current state | Target | Cutover condition |
|---|---|---|---|
| Python entrypoints | legacy CLI, daemon, and skill scripts | typed engine hosts | installed v2 CLI/daemon/API and legacy parity in Block 2 |
| Embedded/service runtime | partially overlapping hosts | one unchanged typed engine contract | embedded/service contract equivalence in Block 2 |
| Dashboard Codex client | dashboard-local subprocess/RPC | accepted utils client plus Factory adapter | immutable pin, compatibility, and restart proof in Block 4 |
| SQLite schema | versions 1–9 active; later SQL inert | one migration authority | fresh/upgrade parity and drift rejection in Block 1 |
| Local semantic runtime | reflection, interpretation, selection, problem solving | pinned libRSI integration | shadow proof, one-writer cutover, duplicate removal in Block 7 |

Compatibility routes are temporary readers/adapters, not permission for two
active writers. Each route has an explicit deletion condition in the manifest.

## External capability inputs

### utils

The observed utils checkout was clean on `main` at exact commit
`08c416da4202b7036110e33e43d34ea590054e2e`; its tracker had Blocks 0–8
completed and Block 9 in progress. It is evidence of the planned capability,
not an accepted consumption revision. Software Factory will:

- consume the Codex app-server client only after utils Block 9 supplies an
  immutable accepted source revision (Software Factory Block 4);
- consume the accepted embedded/service structural contract and runtime
  manifest only when their owning utils Blocks are accepted (Software Factory
  Blocks 9 and 12);
- never copy from or pin an unaccepted producer revision.

### libRSI

The architecture plan names
`ecef9b671463ab9f70c91e82b7c39acfe8b5661a` as its immutable planning
baseline. The observed libRSI worktree was dirty on
`codex/block-20-cli-protocol` at exact commit
`f7ccd7bbc98e335c09df1f5f3779ee4261f5b352`. Block 7 must resolve one
current, accepted immutable revision and record package version, source commit,
content root, semantic schema versions, and adapter contract before shadow
execution or authoritative cutover.

## Baseline behavior

The baseline is intentionally not green:

| Gate | Frozen observation | Assigned repair |
|---|---|---|
| runtime pytest | collection fails on missing `Database` and `IncidentEnvelope` | Block 1 |
| Ruff | 27 errors | Block 1 |
| format | 32 files would be reformatted | Block 1 |
| mypy | 325 errors in 14 files | Block 1 |
| compileall | passes | preserve |
| wheel and sdist build | passes; exact artifact hashes recorded in manifest | preserve through Block 12 |
| dashboard server pytest | 143 tests and 29 subtests pass; two helper-collection errors | Block 9 |
| dashboard web Vitest | 116 pass, one timeout; the failed seven-test file passes alone | Block 9 stability |
| dashboard web build | passes | preserve |
| npm audit | one high-severity finding | Block 9 |
| browser/provider E2E | not run at Block 0 | Block 12 qualification |

These observations are current behavior at the frozen source, not acceptance
claims. The manifest assigns each red or deferred gate to a later Block and
contains the changed-test plan for Blocks 1–12.

## Evidence currentness

Earlier trackers, accepted skills, and the source architecture plan remain
accepted inputs. They are explicitly classified as historical evidence, not as
current implementation. After an owner changes, the affected proof must be
rerun at the exact candidate revision. Unaffected evidence may be reused after
a cheap currentness check.

## Block 0 exit boundary

Block 0 is complete only when its validator proves:

- the exact source commit, tree, tracker frame, and configuration roots;
- exactly one disposition for every frozen tracked path;
- one target owner for every table and authority domain;
- exact active versus inert migration state;
- rejection of an unmapped path, duplicate authority, stale source binding,
  or historical proof relabeled as current implementation.

No production file, operational authority, compatibility route, or persistence
writer is moved or activated by this Block.
