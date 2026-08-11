# Target-class adaptive protocol

Use this contract to compose the accepted adaptive-decision, program-revision,
candidate, Factory-evolution, and capability-reconciliation owners without
creating another application or promotion owner.

## Shared decision path

Every invocation is read-only and binds exactly one canonical policy target
class: `target-repository` or `software-factory`. Validate the complete adaptive
decision packet through the supervision owner before interpreting its
disposition. The same dispositions retain the same meaning for both classes:

- `continue-unchanged` resumes the current Block without a reviewer, candidate,
  skill-source scan, authoring cycle, or application handoff;
- `correct-inline` identifies one normal-owner correction;
- `compare-candidate` retains reviewed comparison evidence while the incumbent
  remains authoritative;
- `amend-structure` requires the exact validated program-revision packet and
  normal authoring owner; and
- `cutover-candidate` identifies a normal target-owner cutover or, for Software
  Factory, a separately governed adoption path.

The protocol result is evidence and routing only. Its application handoff is
rooted, explicitly non-authorizing, and always records
`candidate_authoritative=false`, `application_authorized=false`, and
`promotion_authorized=false`. Actual target integration remains with the Block
9 target owner. Software Factory installation, release, and activation remain
outside this contract.

## Ordinary target repository

Resolve target identity, repository root, revision, affected content, tracker
Block, protected capabilities, candidate evidence, and independent review
through the canonical adaptive policy. Reject a mismatched target class or any
affected path under the current Software Factory repository, the stable live
skill discovery root, or global Codex configuration. An ordinary target packet
must contain no Factory skill manifest, evolution bundle, or Factory-alignment
finding.

Structural work must carry the exact program-revision packet and match its
target, repository, revision, decision fingerprint/currentness, and normal
application owner. Candidate comparison never grants production authority; a
winning candidate can only route to the existing target cutover owner.

## Software Factory self-work

For every mutating disposition, resolve and hash the three live stable skill
sources once. Require all three links to resolve to one release and reject
missing, stale, cross-release, nested-symlink, or oversized manifests. The
unchanged path performs no skill-source scan.

The canonical proposer/author, implementation owner, independent reviewer, and
evaluator must be four distinct identities. The adaptive review remains the
decision review. For inline correction, candidate comparison, and candidate
cutover, additionally verify the accepted Factory-evolution bundle and bind its
proposer, implementer, evaluator, and disposition to the same decision. A
`promote` evaluation means only `adoption_eligible=true`; it grants no edit,
release, install, activation, or promotion authority. Structural work instead
binds its validated program-revision author and application owner.

Keep Factory-alignment findings and target-product findings in separate,
ordered, rooted lists. Generic Factory preference cannot replace product
evidence, and product success cannot erase a Factory ownership finding.

## Current behavior and continuation

Process, test, tracker, review, or evolution records alone cannot establish a
target improvement. When the packet explicitly claims an improvement, resolve
the existing capability-reconciliation record under the same canonical policy,
target thread, mission root, state fingerprint, and exact current revision.
Reject a missing, stale, mismatched, or reopening reconciliation. Reject an
unclaimed reconciliation as ambiguous.

The returned application handoff binds the target class, disposition, decision
fingerprint/currentness, candidate root, structural packet root, action, and
normal owner when applicable. Resume `continue-unchanged` directly. All other
paths route to their existing owner without conferring application authority or
creating a second live implementation.

## Maintained verification

Run `scripts/test_target_class_protocol_contract.py`. It covers both target
classes across unchanged, inline, candidate comparison, structural amendment,
and candidate-cutover routing, plus cross-target identity, Factory reach from
an ordinary target, candidate authority, role separation, stale skill sources,
self-promotion input, adoption-only disposition, and process-only success.
