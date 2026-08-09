# Adaptive implementation decision control

This reference defines how one active implementation owner classifies a live
implementation decision without changing the mission or silently rewriting the
tracker. It is a semantic contract for later runtime work, not a controller,
service, scheduler, policy mutation, or authority grant.

## Contents

- [Decision ladder](#decision-ladder)
- [Triggers and non-triggers](#triggers-and-non-triggers)
- [Common decision record](#common-decision-record)
- [Bounded candidate additions](#bounded-candidate-additions)
- [Structural amendment additions](#structural-amendment-additions)
- [Currentness and conflict rules](#currentness-and-conflict-rules)
- [Authority modes](#authority-modes)
- [Target classes and identity separation](#target-classes-and-identity-separation)
- [Owner and evidence boundaries](#owner-and-evidence-boundaries)

## Decision ladder

Classify the smallest decision that addresses the observed evidence. Evaluate
the ladder in this order:

1. `continue-unchanged` — the current path still satisfies the active Block,
   its source-backed capability, protected capabilities, owner boundaries,
   acceptance, and Stop.
2. `correct-inline` — a materially bad path is proven, but the correction
   remains inside the current Block contract and its existing authoritative
   owner.
3. `compare-candidate` — concrete evidence supports a materially better path,
   but implementation behavior is necessary to decide and the two paths can be
   isolated safely under a declared ceiling.
4. `amend-structure` — live evidence invalidates the Block contract itself,
   changes dependencies, acceptance, or Stop, or materially changes later
   Blocks.

These dispositions are exclusive for one current decision fingerprint.
`correct-inline` is the normal correction path. `compare-candidate` is
selective duplicate work. `amend-structure` is exceptional and cannot be used
when the current Block already authorizes a sufficient correction. A
disposition may escalate only when newly recorded evidence proves the smaller
one insufficient.

The unchanged path performs one O(1) comparison of the current decision
fingerprint and currentness root. An equal accepted fingerprint returns
`continue-unchanged` without a model, reviewer, candidate, authoring cycle, or
new decision artifact. A status or completion record may cite the reused
decision identity when traceability is required.

## Triggers and non-triggers

### Inline triggers

Select `correct-inline` for source-backed evidence of any of the following when
the remedy remains within the active Block objective, dependencies, acceptance,
and Stop:

- wrong implementation owner or canonical-owner bypass;
- lower-power shortcut that omits a required capability or current consumer;
- unnecessary abstraction or speculative generalized layer;
- wasteful, repeated, or blind retry after the failure fingerprint is stable;
- scope widening unrelated to the active capability;
- protected-capability regression;
- validation that cannot prove the claimed current effect; or
- another materially bad approach correctable by the existing owner.

Stop only the causal bad path. Preserve valid work, compare the smallest local
path, the smallest source-backed bounded-general path, and the available
architectural owner. Select the lowest-complexity path that supplies the full
capability, validate the affected result, record selected and rejected paths,
and continue the same Block.

### Candidate triggers

Select `compare-candidate` only when all are true:

- concrete current evidence supports a materially better implementation path;
- static reasoning or a local correction cannot settle the decision;
- implementation outcome evidence is necessary;
- incumbent and candidate can be isolated without overlapping production
  authority or writable scope; and
- expected outcome or rework benefit exceeds declared duplicate-work,
  integration, currentness, and review cost.

The incumbent remains authoritative until accepted cutover. One candidate lane
does not create a second canonical owner.

### Structural triggers

Select `amend-structure` only when at least one is proven:

- the objective or required capability cannot be met inside the Block contract;
- a dependency, acceptance criterion, or Stop must change; or
- the decision materially changes one or more later Blocks.

The implementation owner may package the evidence but cannot edit the tracker.
`author-implementation-trackers` remains the sole tracker-writing method and
the `tracker-authoring` supervision profile independently reviews the exact
delta before it can become authoritative.

### Non-triggers

None of the following alone justifies correction, a candidate, or structural
amendment:

- an optional refactor or style preference;
- one transient test failure;
- local implementation difficulty;
- unproven future reuse or a broader scan opportunity;
- a repeated or equivalent accepted fingerprint;
- an alternative whose decision value does not exceed correction,
  exploration, integration, and currentness cost; or
- reviewer, supervisor, or Factory preference unsupported by direct mission or
  repository evidence.

## Common decision record

Every non-unchanged disposition records one bounded object in the existing
implementation/supervision evidence owner. Exact fields are:

- `decision_id`, `schema_version`, `disposition`, and `recorded_at`;
- `mission_root`, `tracker_path`, `tracker_sha256`, `block_number`, and
  `block_contract_root`;
- `target_class`, `target_repository_root`, `target_revision`, and
  `target_state_root`;
- `capability_statement`, `capability_frame_root`, and
  `protected_capability_results`;
- `evidence_refs` and `decision_fingerprint`;
- `compared_paths`, `selected_path`, and `rejected_paths`;
- `affected_scope`, `valid_work_refs`, `stale_proof_refs`, and
  `safe_frontier`;
- `adaptive_decision_mode`, `implementation_owner_id`, `reviewer_id`, and
  `evaluator_id` where applicable;
- `stop_boundary`, `currentness_root`, and `revisit_trigger`.

`evidence_refs` attach exact source or observable-effect references to the
claims they support; a free-text evidence list does not establish behavior.
`compared_paths` records the smallest local, bounded-general, and existing-owner
options or states why one is unavailable. `rejected_paths` preserves the
reason a lower-power shortcut or speculative generalization lost.

`continue-unchanged` normally emits no new object. When a durable trace is
required, it may reference the accepted `decision_id`, fingerprint, and
currentness root without copying the complete record.

## Bounded candidate additions

A `compare-candidate` record additionally requires:

- `hypothesis` and `hypothesis_scope`;
- `incumbent_root` and `candidate_root`;
- `isolation_kind`, `isolated_writable_scope`, and `shared_resource_exclusions`;
- `resource_ceiling`, `time_ceiling`, and `stop_condition`;
- `production_authority_owner_id`;
- `focused_validation`, `mapped_validation`, and `validation_order`;
- `comparison_dimensions` covering current observable outcome,
  implementation cost, maintenance cost, reversibility, compatibility, and
  protected-capability effects;
- `independent_reviewer_id`, `review_root`, and `review_disposition`;
- `cutover_owner_id`, `cutover_preconditions`, and `retirement_posture`.

Focused validation runs before mapped comparison and only after the candidate
is coherent. The candidate has no production authority. The normal target
owner alone may cut over an independently accepted winner. A losing or
inconclusive lane stops and retains only useful non-authoritative evidence; the
system does not retain two live implementations.

## Structural amendment additions

An `amend-structure` packet adds:

- `revision_id` and `structural_reason`;
- `proposed_mutations` and `old_to_new_block_map`;
- `dependency_closure` and `accepted_history_boundary`;
- `proposed_tracker_root` and `invalidated_evidence_refs`;
- `preserved_evidence_refs` and `resume_point`;
- `author_owner_id`, `authoring_reviewer_id`, and
  `authoring_review_disposition`.

The packet is proposed evidence, not a tracker edit. It cannot change the
mission root or product doctrine. Accepted Blocks, commits, reviews, findings,
and completion evidence remain historical truth. An accepted structural delta
selectively invalidates only evidence whose contract or dependency basis
changed, then resumes from the earliest affected dependency-safe point.

## Currentness and conflict rules

The `decision_fingerprint` is the canonical hash of the mission root, tracker
and Block-contract roots, target-state root, capability/protected-capability
projection, exact adjudicating evidence roots, and compared-path identities.
The `currentness_root` additionally binds current policy, event head, target
revision, incumbent/candidate roots when present, and the accepted decision or
revision head.

- Equal fingerprint plus equal currentness is idempotent and is not
  reconsidered.
- Changed context without new adjudicating evidence refreshes currentness but
  does not reopen the decision.
- Changed adjudicating evidence creates a successor decision linked by
  predecessor ID; it never rewrites the prior record.
- A stale fingerprint, tracker root, Block root, policy head, target revision,
  or evidence root fails closed to recompute the smallest affected slice.
- Interruption resumes from the last validated owner checkpoint. Valid work is
  reused; unverified or state-dependent proof is stale.
- One current decision may have at most one active correction, candidate, or
  revision mutation owner. A concurrent attempt with the same fingerprint is a
  no-op; a conflicting fingerprint freezes mutation and recomputes currentness.
- A correction and candidate cannot write the same scope concurrently. A
  structural proposal cannot cut over implementation while its governing
  contract is unresolved.
- Candidate failure retires only that lane. Unaffected incumbent work continues
  where dependencies permit.

## Authority modes

The contract recognizes four policy modes but does not set or mutate them:

- `fixed` — retain ordinary execution and record supported bad-path evidence;
  do not autonomously correct, explore, cut over, or amend.
- `recommend` — form and independently review the applicable recommendation;
  external application authority is required while safe work continues.
- `reviewed-autonomous` — apply inline corrections and permit independently
  reviewed bounded candidate cutover or low-to-moderate structural change;
  genuinely unresolved consequential product tradeoffs remain external.
- `full-autonomous` — apply reversible, mission-preserving inline correction,
  bounded candidate disposition/cutover, and structural delta within existing
  repository authority after required automated independent review.

`full-autonomous` has no ordinary human-request or manual-Resume path.
Engineering judgment, implementation strategy, bounded architecture selection,
candidate disposition, and mission-preserving tracker repair are autonomous.
Only unavailable credentials, spend, destructive permission, external
communication/release authority, or a direct goal change may become
`reserved-external`; such a boundary does not stop unaffected work and does not
permit repeated human requests.

No adaptive mode grants filesystem, credential, spend, external-action,
release, or product-goal authority absent from the governing sources.

## Target classes and identity separation

`target-repository` and `software-factory` use the same decision ladder,
record, currentness, economy, and cutover semantics. They do not use separate
planning systems.

For `software-factory`, self-change additionally requires distinct attributable
roles: proposer/author, implementer, independent reviewer, and evaluator. The
implementation owner cannot review or evaluate its own candidate, the reviewer
cannot become the cutover owner, and no role may self-promote. Existing Factory
evolution evaluation may authorize eligibility for the separately governed
adoption path; it never edits or activates a skill by itself.

## Owner and evidence boundaries

- The normal implementation owner performs inline correction and remains the
  production owner during candidate comparison.
- The normal target Git/write owner performs cutover.
- `author-implementation-trackers` alone writes structural tracker deltas.
- `supervise-tracker-runs` independently observes, challenges, and records
  current decisions; it does not become the implementation, tracker-writing,
  candidate, or cutover owner.
- Existing canonical supervision and tracker histories remain the evidence
  owners. This contract adds no ledger, controller, registry, or service.
- Tests, hashes, reviews, and populated records are process evidence. Current
  observable behavior and protected-capability proof remain necessary for an
  outcome claim.

This reference does not activate correction, candidate execution, tracker
mutation, policy mutation, or Factory evolution. Those effects require their
own accepted implementation Blocks and existing authoritative owners.
