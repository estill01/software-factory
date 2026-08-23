# Software Factory Canonical Implementation Program Index

## Canonical-location contract

`docs/tracker.md` is the stable program entry point. Detailed evidence remains
in its owning tracker; this index routes implementation and cannot accept a
Block or narrow a direct requested range.

## Current program

| Program ID | Role | Detailed tracker | Exact candidate binding | Block range | First eligible Block | Status |
|---|---|---|---|---|---:|---|
| `SFV2` | required current v2 implementation program | `docs/software-factory-v2-implementation-tracker.md` | SHA-256 `60715c196399ce80dc3d016ee5ba2b1212944be5438307cb08ae4546adddba37`; source parent `b34cdd9fab6830bf2ee5b9ac457e48914082e660` | `SFV2/B0`–`SFV2/B12` | 0 | `planning-candidate` |

The maintained architecture authority is
`docs/software-factory-v2-implementation-plan.md` at candidate SHA-256
`0dc5d28f097b2660fce9c8b4857f0992b6bd5fe37813f8e16c396e80a85054af`.
The candidate becomes active only after distinct exact-revision review and
integration into the implementation branch. Tracker authoring does not start
Block 0.

## Required outcome

Software Factory becomes one standalone and embeddable autonomous work, QA,
supervision, acceptance, and delivery runtime. Codex app-server is a
replaceable provider substrate, libRSI is the one-way semantic improvement
dependency, and consumer-domain integrations remain outside the OSS core.

## Other tracker disposition

Existing detailed trackers under `docs/` retain their accepted, rejected,
open, and historical evidence. They are predecessor/owner evidence for SFV2
unless a current direct program binding explicitly activates one. Their local
Block numbers are not appended to SFV2 and none is inferred complete from this
index.

The full hosted/multi-tenant product is a required design successor only if
separately activated after SFV2 service readiness. It is not an active program
and this index does not authorize deployment, billing, public authentication,
or tenant administration.

## Supervision posture

When SFV2 implementation starts, its implementation thread receives one
isolated `supervise-tracker-runs` group bound to the exact accepted tracker,
branch, requested range, and active Block. Monitoring is read-only with respect
to implementation and cannot combine consumer repositories or contract the
program.

## Terminal completion

SFV2 is terminal only when `SFV2/B0`–`SFV2/B12` and the tracker-level
observable outcome are accepted at one current pushed revision. A branch,
commit, review, handoff, provider completion, release candidate, or Block Stop
is nonterminal.
