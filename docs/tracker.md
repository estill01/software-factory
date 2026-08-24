# Software Factory Canonical Implementation Program Index

## Canonical-location contract

`docs/tracker.md` is the stable program entry point. Detailed evidence remains
in its owning tracker; this index routes implementation and cannot accept a
Block or narrow a direct requested range.

## Current program

| Program ID | Role | Detailed tracker | Exact tracker binding | Block range | First eligible Block | Status |
|---|---|---|---|---|---:|---|
| `SFV2` | required current v2 implementation program | `docs/software-factory-v2-implementation-tracker.md` | SHA-256 `2079c81dc8494aca0893795fbb141dda566bab067a8db8c8c458b7b605d77f34`; Block 0 implementation checkpoint `bd33086f35f673386a4ad0ff2bcafc340c937323` pending exact-revision confirmation of its tracker-only audit-state successor | `SFV2/B0`–`SFV2/B12` | 0 | `active` |

The maintained architecture authority is
`docs/software-factory-v2-implementation-plan.md` at candidate SHA-256
`0dc5d28f097b2660fce9c8b4857f0992b6bd5fe37813f8e16c396e80a85054af`.
Distinct read-only review thread `01a02da5-caf4-7a02-bf09-dbc7bf774bc1`
accepted exact candidate `65c7bae2e69b25547b2914372ee7b9ee6ea9c1db`
with no material findings. This index activates that reviewed program. Block 0
is in progress at its preserved implementation candidate pending fresh
exact-revision audit; Block 1 has not started.

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

When SFV2 implementation starts, its implementation thread must invoke
`implement-tracker-blocks` for the full active `SFV2/B0`–`SFV2/B12` range.
Before its first implementation-producing Block 0 effect, it receives one
isolated `supervise-tracker-runs` group bound to the exact accepted tracker,
branch, requested range, thread, and active Block. Monitoring is read-only with
respect to implementation and cannot combine consumer repositories or contract
the program. Tracker activation alone starts neither skill-driven implementation
nor Block 0.

## Terminal completion

SFV2 is terminal only when `SFV2/B0`–`SFV2/B12` and the tracker-level
observable outcome are accepted at one current pushed revision. A branch,
commit, review, handoff, provider completion, release candidate, or Block Stop
is nonterminal.
