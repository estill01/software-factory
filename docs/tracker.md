# Software Factory Canonical Implementation Program Index

## Canonical-location contract

`docs/tracker.md` is the stable program entry point. Detailed evidence remains
in its owning tracker; this index routes implementation and cannot accept a
Block or narrow a direct requested range.

## Current program

| Program ID | Role | Detailed tracker | Exact tracker binding | Block range | First eligible Block | Status |
|---|---|---|---|---|---:|---|
| `SFV2` | required current v2 implementation program | `docs/software-factory-v2-implementation-tracker.md` | SHA-256 `c67862c146ca9bf7a620300dbd0f3e140aab8a26514a999c9ae5ddfd7db6f29a`; active content commit `2b394303c58203772a3e80cf4a2a83779fd8deb0` | `SFV2/B0`–`SFV2/B12` | 0 | `active` |

The maintained architecture authority is
`docs/software-factory-v2-implementation-plan.md` at candidate SHA-256
`0dc5d28f097b2660fce9c8b4857f0992b6bd5fe37813f8e16c396e80a85054af`.
Distinct read-only review thread `01a02da5-caf4-7a02-bf09-dbc7bf774bc1`
accepted exact candidate `65c7bae2e69b25547b2914372ee7b9ee6ea9c1db`
with no material findings. This index activates that reviewed program;
activation does not start Block 0.

## Direct-user parallel repair

`PORTABLE/B0`–`PORTABLE/B2` in
`docs/portable-supervision-implementation-tracker.md` is `active-isolated-parallel`
under the direct instruction in task `01a06f3e-7ffc-75b3-873d-675e9b93ae84`.
Blocks 0–1 retain acceptance. Block 2 is reopened only for the recorded canonical completion and evidence-handoff correction. It repairs supervision portability and does not
activate SFV2 implementation or Patent Studio RRA implementation. The detailed
tracker owns status and exact completion evidence. Its current SHA-256 is
`386112f4ee8e683f383fce57a06d029c5d6586065b854f26209c6d496ddfdb6b`.

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
