# Active program revision

Use this method only after implementation has begun and current evidence shows
that the accepted dependency program itself is wrong. It is not a general
redesign lane. Ordinary code corrections, status/evidence refreshes, and ideas
that do not invalidate a Block contract stay with their existing implementation
or adaptive-decision owner.

## Ownership and invariant

- The tracker author owns predecessor inspection, proposed tracker bytes, the
  explicit old-to-new Block map, and the program-revision packet.
- The maintained full tracker verifier owns mechanical tracker validity.
- A distinct configured reviewer owns the semantic disposition and signs the
  exact packet projection outside the author process.
- Supervision owns canonical currentness, append-only acceptance, and the
  implementation-range transition. It does not edit tracker bytes.
- The implementation owner applies only an accepted proposal and resumes the
  dependency-safe Block returned by the accepted packet.

The standing direct requested range survives inserts, removals, splits, merges,
reordering, and renumbering. A full-tracker request remains the complete amended
tracker. An explicit range maps to the union of all successor Blocks. Only a
newer exact eligible direct-user event may contract it.

## Trigger

Open a revision only when one exact learned fact makes at least one of these
structurally false:

- a Block contract or ownership boundary;
- the dependency graph or required order;
- the decomposition into Blocks;
- the terminal Block or current observable-outcome path.

Record why inline correction, a bounded candidate, and unchanged continuation
are insufficient. A local implementation mistake, a status-only change, a new
completion-evidence line, an optional improvement, or an unsupported idea is a
no-op for this method.

## Packet construction

Create a proposed tracker in an isolated noncanonical file. Do not replace the
current tracker before review. Run `scripts/program_revision.py build` with one
canonical metadata object containing:

- current mission, policy, repository, target revision, adaptive decision, and
  exact application-precondition roots;
- author and distinct reviewer identities;
- learned-fact references, capability gains/protections/losses, selected and
  rejected paths, proposed mutations, preserved work, invalidated proof, and
  the structural Stop;
- a complete map from every predecessor Block number to a sorted successor list.

The map supports one-to-one renumbering, one-to-many split, many-to-one merge,
and an empty successor list for removal. Every successor must exist. New Blocks
may be unmapped. Completed Blocks must map one-to-one to a completed successor
with byte-equivalent normalized contract and completion history; they cannot be
silently removed, split, merged, reopened, or rewritten.

The builder derives, rather than accepts from the caller:

- predecessor/proposal byte and structure roots;
- accepted-history root;
- changed predecessor and successor Blocks;
- the successor dependency closure whose proof is invalidated;
- unaffected dependency-safe work;
- the first dependency-safe resume Block;
- the full-verifier result root and packet root.

If predecessor and proposal structure roots are equal, stop and return the
change to the ordinary status or implementation path.

## Independent disposition

The review object is exactly
`software-factory-program-revision-independent-review`. It binds the packet,
both tracker identities, proposal structure, accepted history, map, affected
closure, resume Block, author, reviewer, disposition, finding references,
evidence root, sealed authority key, and review root. The configured reviewer
signs its canonical projection. The author and reviewer identities must differ.

`accepted` makes the exact packet eligible for append-only supervision entry.
`revise` retains findings and returns proposal ownership to the author without
changing the active tracker. `rejected` retains the decision and leaves the
current tracker authoritative. Neither a commit label nor a populated review
file implies acceptance.

## Apply and resume

For an accepted review:

1. Revalidate the predecessor tracker, proposal, packet, review signature,
   current mission/policy/adaptive decision, repository revision, and exact
   application precondition.
2. Append one canonical program-revision event under the supervision owner
   lock. Identical current input is idempotent.
3. Install and commit only the accepted proposal bytes through the normal
   repository owner.
4. Run `implementation-range-amend` against that exact tracker and canonical
   event, supplying the exact application commit. The range owner verifies that
   commit contains the accepted tracker blob and records it in the append-only
   range/program-revision history. Map explicit ranges by successor union;
   preserve full-tracker intent.
5. Retain accepted Blocks, accepted evidence, and unaffected proof. Mark only
   the derived affected closure for revalidation.
6. Resume the packet's dependency-safe Block automatically. Do not return to
   the user at the revision, review, commit, or Block boundary when the standing
   range continues.

Fail closed on stale policy, mission, event head, repository revision,
predecessor bytes, proposal bytes, signature, application precondition, accepted
history, map, or installed tracker. Never infer successor-mission authority from
a release, routed packet, or historical mission root.

## Economy and Stop

Read and hash each bounded input once per validation boundary. Reuse the full
verifier result contained in the packet unless an input changed. Review only the
delta, accepted-history preservation, affected closure, capability effect, and
resume frontier. Do not create a new service, registry, scheduler, or parallel
ledger.

Stop before candidate implementation, cutover, release, deployment, lifecycle
terminalization, Gmail, or unrelated policy mutation. Those effects require
their existing owners and later tracker Blocks.
