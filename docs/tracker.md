# Software Factory Canonical Implementation Program Index

## Canonical-location contract

`docs/tracker.md` is the stable program entry point. Detailed evidence remains
in its owning tracker; this index routes implementation and cannot accept a
Block or narrow a direct requested range.

## Current program

| Program ID | Role | Detailed tracker | Exact tracker binding | Block range | First eligible Block | Status |
|---|---|---|---|---|---:|---|
| `SFV2` | required current v2 implementation program | `docs/software-factory-v2-implementation-tracker.md` | SHA-256 `1073633ed89a622301487ec1a6d005cf5a06c50e257d1545460beac46141d517`; Blocks 0–12 accepted; exact accepted Block 12 evidence `935fe88` over source `8672023`; rejected Block 12 evidence `0176ef7`, `e4956b7`, and `e55a0d1` plus all three P1 findings preserved; exact accepted Block 11 candidate `e378f92`; rejected Block 11 candidates `10eea9e`, `0f2ed70`, `bc599d7`, `e8342de`, and `71f965e` plus all cutover and qualification findings preserved; exact accepted Block 10 candidate `5988b3d`; rejected Block 10 candidates `e60b999`, `44f3e83`, `b408e17`, `777b2d2`, and `8edf34b` plus all eleven P1/P2 findings preserved; rejected Block 9 candidates `5a2f226` and `9c76fc8` plus all four P1 findings preserved; exact accepted Block 9 candidate `7f4d55f`; rejected Block 7 candidates `7937464`, `bb1bd62`, and `c5bfce2` plus rejected Block 8 candidates `4a23d41`, `76ca892`, `12adc23`, `52acbaf`, `91b8cac`, `7c27b86`, `46631b7`, `eca370f`, and `173280d` preserved; exact accepted Block 7 candidate `56d2a22`; exact accepted Block 8 candidate `e82ee53`; full range `RANGE-SFV2-B0-B12-3901D4F-2079C81D` preserved | `SFV2/B0`–`SFV2/B12` | — | `completed` |

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
`d10ca8e292ed0850a1236fad22e1736615e96509`. Block 6 is accepted at exact
pushed candidate `5025cf38ea989bb619d9d79facf0386ac5b10c0f` after both rejected
candidates were preserved and independent review returned no P0–P2 findings.
Block 7 is accepted at exact pushed candidate `56d2a22` after distinct review
returned no P0–P2 findings, with acceptance recorded in pushed successor
`c8752129d919edf1b60f3a27ae083e1a89df34f0`. Exact candidate `7937464` is
preserved as rejected evidence after four P1 findings. Exact successor `bb1bd62`
is also preserved and unaccepted after five P1 findings exposed live-currentness,
cross-mission Learning, remaining local improvement decisions, and canonical
reflection-view gaps. Exact candidate `c5bfce2` is preserved and unaccepted
after two P1 findings exposed a validation-to-commit currentness race and reuse
of one selected root for unrelated operational rows. The current correction
retains every closed path while making currentness atomic and selected-candidate
projection byte-exact and one-to-one. Block 8 then became the
dependency-safe frontier. Exact candidate `4a23d41` is preserved and
unaccepted after four P1 findings exposed post-preservation cleanup deletion,
loss of dirty/untracked restart bytes, duplicate resolved recovery wake, and
overtaking release activation, plus one P2 fsync finding. The bounded
correction `76ca892` is also preserved and unaccepted after distinct review
closed four prior findings but reproduced one remaining P1 check/delete race
in destructive branch cleanup. Exact successor `12adc23` is preserved and
unaccepted after closing the ref-advance race but reproducing one P1 concurrent
worktree-admission race. The current bounded successor records refused
retirement as a no-physical-effect audit and preserve/defer-fails branch,
worktree, and stash deletion until one adapter can atomically fence both object
identity and worktree admission. Exact successor `52acbaf` is preserved and
unaccepted after closing that OperationsService race but leaving two physical
deletion routes in the reconciliation owner: prepare-failure cleanup and
terminal integration-lane retirement. The current correction preserves those
lanes and pending bytes, and limits failed post-publication rollback to an exact
ref compare-and-swap without hard-resetting checkout bytes. Refreshed affected
proof is complete. Exact successor `91b8cac` is preserved and unaccepted after
closing those deletion paths but allowing validators to observe dirty mutable
lane bytes while publishing a different committed candidate tree. The current
correction runs each validation phase in a fresh retained detached snapshot of
the exact `candidate_head` and verifies tracked/index currentness through command
completion. Exact successor `7c27b86` is preserved and unaccepted after closing
those mutable-byte substitutions but leaving a post-validation ref-advance race
and letting validator setup/spawn exceptions bypass rollback evidence. The
current correction durably handles every known validator failure, terminally
CAS-fences the exact target ref, and reconciles the ref after SQL completion.
Exact successor `46631b7` is preserved and unaccepted after
closing the advance/spawn cases but throwing before durable evidence when the
target ref was deleted and rewriting valid historical publication after an
ordinary later successor. The current correction represents missing refs as
observed `null` and keeps historical publication independent from later target
currentness. Exact successor `eca370f` is preserved and unaccepted after closing
those paths but letting a queued concurrent publisher reuse stale `accepted`
state and resurrect a terminal rollback. Successor `173280d` reread under the
repository lock and SQL-CAS-fenced every candidate/cleanup terminal transition,
but is preserved and unaccepted after allowing a later or queued caller to
request a different post-publication validator and inherit the first caller's
result. The current correction durably binds the exact validation command before
the Git effect, rejects mismatched retries under the same repository lock, and
removes the rejected candidate's stale later-read reconciliation claim. A clean
correction freeze and distinct exact-revision review accepted exact pushed
candidate `e82ee5325c266d8891e86ab22ca7abfb2e369166`, tree
`b5be73e4fd137e440ef6c0b72fe13ebb2f2525c1`, with no P0–P2 findings.
Block 9 is accepted at exact pushed candidate
`7f4d55f2e87c4eaeae0731fdb22ef7fb2f793b0e`, tree
`a2ac7a1f1d706f851db5ccb84d768a3af109a36a`, after distinct exact-revision
review returned no P0–P2 findings. Exact pushed candidates
`5a2f226` and `9c76fc8` are preserved and unaccepted after independent review
returned four total P1 findings in event-cursor scope, installed component
identity, completing-handler drain, and bounded shutdown/recovery. The accepted
successor closes every finding with mission-local contiguous cursors, installed
component-root verification, finite request/read and drain ceilings, and exact
replay of only the already accepted operator request. Block 10 then became the sole
dependency-safe frontier. Its maintained neutral profile and consumer-owned
external extension both reach delivered and independently accepted terminal
mission outcomes through the real CoreService owners. Focused/mapped/static and
isolated package proof are current at detailed tracker SHA-256
`4065ed0a7afd4b443e58f803cd6d24f0a2b36cea1286f5b46d662aea19288574`.
Exact pushed candidates `e60b9990a2453888dfff991dc8c46fb5ca251d58` and
`44f3e83095550b6cf0db18c08ac314cce110e3f3`, plus exact pushed candidate
`b408e179b7254ce54aec6ac396dd797159e27fe5` and exact pushed candidate
`777b2d2a019c89b922469b4cbfb4ac979fbd18fa`, plus exact pushed candidate
`8edf34b917694e6aa9e9942287b0668c1dd07bfd`, are preserved and unaccepted after
distinct reviews found eleven P1/P2 gaps across canonical non-workspace QA, durable
target restart, physical-effect fencing, exact execution/candidate lineage,
mandatory independent review, post-QA staged currentness, stage-to-candidate
lineage, terminal profile fencing and membership, and stale-QA atomicity. The bounded
successor retains the earlier closures, forces currentness/review through
canonical QA for every profile candidate, invalidates same-revision
cross-execution QA and acceptance lineage, binds every profile stage to the
active candidate root, rejects mission-scoped terminal bypass, records QA
children atomically after the stale check, and binds every selected,
non-cancelled, installed profile target into one deterministic terminal set whose
unique physical targets are each fenced once through acceptance and whose exact
work identity is rechecked at mission completion; conflicting physical-target
roots reject before fence acquisition. Distinct exact-revision review accepted
exact pushed candidate `5988b3d7dd9bf3fd2720842abfb810f8e0a0cc30`, tree
`c35773d65cf9040156d70cab31c84047d3b80e85`, with no P0–P2 findings. Block 10
is accepted. Block 11 then migrated the frozen real-state and historical
supervision snapshot with rollback/reapply proof, cut dashboard and skill
entrypoints to one native owner, retired the libRSI shadow comparator, archived
legacy bytes without losing revision addressability, and qualified the exact
16-wheel offline composition. Exact candidates `10eea9e`, `0f2ed70`,
`bc599d7`, `e8342de`, and `71f965e` remain preserved and unaccepted with every
independent finding. The accepted successor closes complete ZIP and installed
RECORD inventory, stable one-read manifest authority, private artifact and
environment ownership, exact-path/no-registry resolution, compatibility-writer
closure, and archive-addressability gaps. Distinct exact-revision review
accepted exact pushed candidate
`e378f92059395ff802e5d4c3ac1fd1cad0432210`, tree
`8b40685c9838134542187415a95dbbe92b4af5ac`, with no P0–P2 findings and
independently reproduced the ten-test clean-archive slice plus exact receipt
root. Block 11 is accepted. Block 12 froze source
`86720234d09c59e663588baa92854f11d8dd4b7d`, reproducibly built and
qualified its exact source archive and both Factory wheels, verified the
16-wheel no-index/no-deps composition twice, and produced byte-identical
installed-dashboard receipts bound to the exact source, manifest, offline
qualification root, installed RECORD roots, artifact projection, and
source-tree offline-qualifier identity. Exact evidence revisions `0176ef7`,
`e4956b7`, and `e55a0d1` remain preserved and unaccepted after three P1
findings across installed owner resolution, exact-install receipt binding, and
caller-replaceable verifier authority. Distinct exact-revision review accepted
pushed evidence `935fe88bc9b69aa846600d41e7162f16df5c1fb1`, tree
`7bbe3a4b34a2c9954e69567cdf26e461c7c2db04`, with no P0–P2 findings. Blocks
0–12 and the terminal observable outcome are accepted. Nothing was deployed,
activated, published, redistributed, licensed, or granted consumer-domain
authority.

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

SFV2 reached its terminal implementation outcome: `SFV2/B0`–`SFV2/B12`
and the tracker-level observable outcome are accepted under detailed tracker
SHA-256 `1073633ed89a622301487ec1a6d005cf5a06c50e257d1545460beac46141d517`.
The accepted terminal evidence remains an internal qualification candidate;
production deployment, public release, hosted multi-tenancy, and
consumer-domain mutation require separate authority.
