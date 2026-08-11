# Active program revision

Use this method only after implementation has begun and current evidence shows
that the accepted dependency program itself is wrong. It is not a general
redesign lane. Ordinary code corrections, status/evidence refreshes, and ideas
that do not invalidate a Block contract stay with their existing implementation
or adaptive-decision owner.

## Ownership and invariant

- The tracker author owns predecessor inspection, proposed tracker bytes, the
  explicit old-to-new Block map, and the program-revision packet.
- Before packet construction, supervision binds one immutable
  `tracker-authoring` profile to the exact authoring target thread. That policy
  binding resolves the mechanical watcher, semantic reviewer, adjudicator, and
  optional fix executor through the existing policy and event owner. It also
  resolves the exact Git revision and blob root of the maintained supervision-
  policy reference; packet strings cannot establish those roles or source.
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

Mappings also preserve causal reachability. A completed successor is reserved
for its one completed predecessor and cannot receive an open predecessor. An
explicitly requested predecessor cannot map to removal, and every incomplete
prerequisite of its mapped successors joins the amended explicit range. This
prevents a map collision or omitted inserted prerequisite from producing a
terminal or dependency-deadlocked range.

The proposed tracker contains one machine-readable control section before the
Block headings. The six index fields enumerate every current Block in exact
numeric order except the scalar terminal and handoff fields. The history table
is append-only:

```markdown
## Active-program revision control

- Terminal Block: `<terminal>`
- Required order: `<comma-separated complete Block order>`
- Prose-reference Blocks: `<comma-separated complete Block order>`
- Source-map Blocks: `<comma-separated complete Block order>`
- Verification-matrix Blocks: `<comma-separated complete Block order>`
- Handoff Block: `<derived resume Block>`

### Program revision history

| Revision ID | Predecessor tracker SHA-256 | Current structure SHA-256 | Block map SHA-256 | Affected Blocks | Resume Block |
|---|---|---|---|---|---:|
| `<revision-id>` | `<previous-tracker-sha256>` | `<current-structure-sha256>` | `<block-map-root>` | `<comma-separated affected Blocks>` | `<resume Block>` |
```

The revised tracker also contains exactly one `## Program source map` and one
`## Program verification matrix`. Each uses a two-column Markdown table whose
first column enumerates every current Block exactly once in the control-field
order and whose second column contains the current non-placeholder source or
verification basis. The full verifier rejects missing, partial, duplicate, or
reordered rows. This makes the control fields completeness indexes over actual
tracker surfaces rather than standalone claims.

The builder requires exactly one new row, preserves every predecessor row
byte-for-byte in parsed order, and proves the row from the packet rather than
accepting it as narrative. The full verifier checks the section linearly while
remaining compatible with trackers that have never had a program revision.

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

A later proposal after `revise` or `rejected` must cite the exact predecessor
revision and review root, resolve every open finding reference, and change the
structural proposal projection. Changing only a revision ID or adding a history
row does not close a finding. Once a predecessor proposal is accepted, another
revision cannot replace that accepted lineage.

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
   the application is a single-parent, tracker-only commit whose parent is the
   exact packet target revision and contains the exact predecessor tracker; the
   the commit contains the exact proposal. It records that commit in the
   append-only range/program-revision history. Map explicit ranges by successor
   union plus incomplete prerequisite closure; preserve full-tracker intent.
5. Retain accepted Blocks, accepted evidence, and unaffected proof. Mark only
   the derived affected closure for revalidation.
6. Resume the packet's dependency-safe Block automatically. Do not return to
   the user at the revision, review, commit, or Block boundary when the standing
   range continues.

An identical retry rehydrates the accepted canonical event and returns the
same resume object without appending another event or executing another
application. This makes interruption after the first policy write recoverable
without a manual scheduling step.

Fail closed on stale current policy, mission, decision/currentness, event head,
repository revision, predecessor bytes, proposal bytes, signature, application
precondition, accepted history, map, application parent/scope, authoring
profile, or installed tracker. Historical events remain readable, but a stale
accepted event cannot authorize a first application. Never infer successor-
mission ownership from a release, routed packet, or historical mission root.

## Economy and Stop

Read and hash each bounded input once per validation boundary. Reuse the full
verifier result contained in the packet unless an input changed. Review only the
delta, accepted-history preservation, affected closure, capability effect, and
resume frontier. Do not create a new service, registry, scheduler, or parallel
ledger.

Stop before candidate implementation, cutover, release, deployment, lifecycle
terminalization, Gmail, or unrelated policy mutation. Those effects require
their existing owners and later tracker Blocks.
