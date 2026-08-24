# Software Factory Canonical Implementation Program Index

## Canonical-location contract

`docs/tracker.md` is the stable program entry point. Detailed evidence remains
in its owning tracker; this index routes implementation and cannot accept a
Block or narrow a direct requested range.

## Current program

| Program ID | Role | Detailed tracker | Exact tracker binding | Block range | First eligible Block | Status |
|---|---|---|---|---|---:|---|
| `SFV2` | required current v2 implementation program | `docs/software-factory-v2-implementation-tracker.md` | SHA-256 `a1cd93b5159775c907e2b9380e4e4a7b952bb7858e700cd928be9bc08da9de7a`; Blocks 0–5 accepted; Block 6 in progress; full range `RANGE-SFV2-B0-B12-3901D4F-2079C81D` preserved | `SFV2/B0`–`SFV2/B12` | 6 | `active` |

The maintained architecture authority is
`docs/software-factory-v2-implementation-plan.md` at candidate SHA-256
`0dc5d28f097b2660fce9c8b4857f0992b6bd5fe37813f8e16c396e80a85054af`.
Distinct read-only review thread `01a02da5-caf4-7a02-bf09-dbc7bf774bc1`
accepted exact candidate `65c7bae2e69b25547b2914372ee7b9ee6ea9c1db`
with no material findings. This index activates that reviewed program. Block 0
is accepted at its preserved exact candidate after fresh review under the
current full-range binding. Block 1 is accepted at exact pushed correction
`2172dc4b112ad836bff0a292f63adb74cf61d3c0` after independent review returned
no P0–P2 findings. Block 2 is accepted at exact pushed correction
`c32ac92f0df3c0c884996da8911aa18d8014c7df` after independent review returned
no P0–P2 findings. Block 3 is accepted at exact pushed correction
`c2bc0a2174d077dbe49a94fb58fd61a90d0613fa` after independent review returned
no P0–P2 findings. Block 4 is accepted at exact pushed candidate
`635531016150d77a5de8592592f16420bb538505` after its rejected candidates were
preserved and independent review returned no P0–P2 findings; acceptance is
recorded in pushed successor `1dd84e7510684bf617b35079c2734035e5bae2ca`.
Block 5 is accepted at exact pushed candidate
`96d7d8a0db5bb35d858d9566d91f19b9e057deb7` after its full rejection history
was preserved, all runtime authority findings were closed, and independent
review returned no P0–P2 findings; acceptance is recorded in pushed successor
`d10ca8e292ed0850a1236fad22e1736615e96509`. Block 6 is in progress as the
dependency-safe frontier.

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
