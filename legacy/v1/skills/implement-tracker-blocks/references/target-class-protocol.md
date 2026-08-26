# Target-class adaptive protocol

Use this contract to compose the accepted adaptive-decision, program-revision,
candidate, Factory-evolution, and capability-reconciliation owners without
creating another application or promotion owner.

## Shared decision path

Every invocation is read-only. Load the canonical supervision policy and
mission-scoped ledger internally for one target thread; callers do not supply a
policy, target root, active-candidate frontier, or live-skill root. Bind the
latest exact adaptive-decision event and, when required, its canonical signed
review before interpreting its disposition. The policy-owned target class is
`target-repository` or `software-factory`, and the same dispositions retain the
same meaning for both classes:

- `continue-unchanged` resumes the current Block without a reviewer, candidate,
  skill-source scan, authoring cycle, or application handoff;
- `correct-inline` identifies one normal-owner correction;
- `compare-candidate` retains reviewed comparison evidence while the incumbent
  remains authoritative;
- `amend-structure` requires the exact validated program-revision packet and
  normal authoring owner; and
- `cutover-candidate` identifies a normal target-owner cutover or, for Software
  Factory, evidence eligible for its normal separately governed owner.

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

Structural work must carry the exact program-revision packet plus a valid
independent signature over that packet. Match the full mission, policy,
decision-event, target repository/revision/state, fingerprint/currentness,
candidate, role, precondition, tracker content, and normal application-owner
projection. Candidate comparison never grants production authority; a winning
candidate can only route to the existing target cutover owner.

## Software Factory self-work

For every mutating disposition, resolve and content-hash the three live stable
skill sources exactly once, bracketed by bounded metadata-identity snapshots
and followed by the same cheap identity check at final currentness. Require all
three links to resolve to one release and reject missing, stale, cross-release,
nested-symlink, oversized, or changed manifests. The unchanged path performs no
skill-source scan.

The canonical proposer/author, implementation owner, independent reviewer, and
evaluator must be four distinct identities. The adaptive review remains the
decision review. Inline correction remains a normal-owner correction and cannot
claim adoption eligibility before retained candidate behavior exists. For
candidate comparison and candidate cutover, load the decision-derived, staged
Factory-evolution artifact set from its canonical supervision owner;
do not accept bundle bytes from the caller. Bind its staged manifests,
experiment, baseline, retained candidate, proposer, implementer, evaluator,
review, evaluation, and disposition to the exact decision/currentness and live
skill manifest. Require a sealed evaluator acceptance over those exact roots so
deleting and rebuilding the derived artifact directory cannot replace an
accepted result for the same decision. A
`promote` evaluation means only `adoption_eligible=true`; it grants no edit,
release, install, activation, or promotion authority. Structural work instead
binds its validated program-revision author and application owner.

Every staged artifact read is exact and bounded: the evolution directory and
each retained member keep stable identity, artifacts are regular no-follow
files under that owner, stored JSON bytes use the one canonical writer form,
and the existing per-artifact and aggregate bounds apply before parsing. The
sealed acceptance schema requires an exact integer version and text signature;
lookalike scalar or byte-string forms are invalid. Recheck every retained
artifact and directory snapshot after in-memory manifest/bundle verification.

Keep Factory-alignment findings and target-product findings in separate,
ordered, nonempty rooted lists for mutating paths. Every finding root must be a
claim-bound root from the exact decision, candidate, structural review, live
skill manifest, evolution result, or current outcome. Generic Factory
preference cannot replace product evidence, and product success cannot erase a
Factory ownership finding.

## Current behavior and continuation

Process, test, tracker, review, or evolution records alone cannot establish a
target improvement. When the packet explicitly claims an improvement, resolve
the existing capability-reconciliation record under the same canonical policy,
target thread, mission root, state fingerprint, and exact current revision.
Require the same reconciliation root, owner identities, and revision in the
latest canonical outcome-completion event for the exact state fingerprint, and
carry that event ID/root into the result and handoff. Reject a missing, stale,
mismatched, failed, or reopening reconciliation. Reject an unclaimed
reconciliation as ambiguous.

After the last evidence load, rehydrate the canonical policy/ledger, target
revision and affected content, live skill sources, exact evolution inventory,
and current behavior. After those reads, re-evaluate the canonical decision and
target state once more and require the exact original result. Compare the cheap
live-skill metadata, complete evolution inventory/path identity, and capability
record snapshot again after that decision pass. Each retained identity includes
device, inode, mode/path type, link count, size, modification time, and change
time. The live-skill identity records the stable discovery link and resolved
source directory separately before descendant entries. Reject any changed
source before returning a result. The application handoff binds the
exact decision event, target revision, candidate, structural packet and signed
review, live skill sources, sealed evolution acceptance plus
review/evaluation/experiment, role map, findings, current behavior, action, and
normal owner. Resume
`continue-unchanged` directly. All other paths route to their existing owner
without conferring application authority or creating a second live
implementation.

## Maintained verification

Run `scripts/test_target_class_protocol_contract.py`. It covers both target
classes across unchanged, inline, candidate comparison, structural amendment,
and candidate-cutover routing, plus canonical owner/target identity, exact
evolution binding, signed structural revision/review binding, nonempty
claim-bound findings, canonical current-outcome completion, final currentness,
derived-evolution replacement, and absent planned-file containment.
