# Adaptive implementation decision control

This reference defines how one active implementation owner classifies a live
implementation decision without changing the mission or silently rewriting the
tracker. It is a semantic contract for later runtime work, not a controller,
service, scheduler, policy mutation, or authority grant.

## Contents

- [Decision ladder](#decision-ladder)
- [Triggers and non-triggers](#triggers-and-non-triggers)
- [Common decision record](#common-decision-record)
- [Canonical record grammar](#canonical-record-grammar)
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
implementation/supervision evidence owner. The embedded v1 grammar below is
normative; this prose is an operator index. Common fields are:

- `decision_id`, `schema_version`, `decision_stage`, `disposition`, and
  `recorded_at`;
- `predecessor_decision_id` and `currentness_refresh_of`;
- `mission_root`, `tracker_path`, `tracker_sha256`, `block_number`, and
  `block_contract_root`;
- `authority_effect`, nullable `authority_claim_id`, `authority_evidence_refs`,
  `prior_mission_root`, and `proposed_mission_root`;
- `target_class`, `target_repository_root`, frozen
  `decision_target_state_root`, current `target_revision`,
  `target_revision_root`, and `current_target_state_root`;
- `capability_statement`, `capability_frame_root`, and
  `protected_capability_results`;
- `evidence_refs`, `adjudicating_evidence_ref_ids`,
  `adjudicating_evidence_root`, `evidence_manifest_root`, and
  `decision_fingerprint`;
- `compared_paths`, `selected_path`, and `rejected_paths`;
- `affected_scope`, `valid_work_refs`, `stale_proof_refs`, and
  `safe_frontier`;
- `adaptive_decision_mode`, `proposer_author_id`, `implementation_owner_id`,
  `reviewer_id`, and `evaluator_id` where applicable;
- nullable `external_boundary` for one exact `reserved-external` condition;
- `stop_boundary`, `policy_root`, `event_head_root`,
  `accepted_decision_head`, `accepted_revision_head`, `currentness_root`, and
  `revisit_trigger`.

`evidence_refs` attach exact source or observable-effect references to the
claims they support; a free-text evidence list does not establish behavior.
`adjudicating_evidence_ref_ids` selects only the evidence that determines the
disposition. Later implementation, validation, review, or outcome evidence may
extend `evidence_refs` and `evidence_manifest_root` without fabricating a new
decision fingerprint.
`compared_paths` records the smallest local, bounded-general, and existing-owner
options or states why one is unavailable. `rejected_paths` preserves the
reason a lower-power shortcut or speculative generalization lost.

`continue-unchanged` normally emits no new object. When a durable trace is
required, it may reference the accepted `decision_id`, fingerprint, and
currentness root without copying the complete record.

## Canonical record grammar

The following JSON object is the exact v1 interchange specification. `required`
means the key is always present. `nullable` means its value may be JSON `null`;
absence is never a substitute for null. Arrays are ordered, contain no duplicate
IDs or roots, and obey `min_items`. Objects reject unknown keys. `id` and
`sha256` values obey the named regular expressions. A `timestamp` is UTC RFC
3339 with exactly six fractional digits and a terminal `Z`.

<!-- contract-spec-v1 -->
```json
{
  "schema_version": 1,
  "closed_objects": true,
  "named_types": {
    "id": {"kind": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$"},
    "sha256": {"kind": "string", "pattern": "^[0-9a-f]{64}$"},
    "repo-path": {"kind": "string", "absolute": true, "contained": true},
    "timestamp": {"kind": "string", "format": "YYYY-MM-DDTHH:MM:SS.ffffffZ"},
    "evidence-ref": {
      "kind": "object",
      "fields": {
        "ref_id": {"type": "id", "required": true, "nullable": false},
        "source_class": {"type": "enum:evidence-source-class", "required": true, "nullable": false},
        "adjudication_posture": {"type": "enum:evidence-posture", "required": true, "nullable": false},
        "root_sha256": {"type": "sha256", "required": true, "nullable": false},
        "claim_ids": {"type": "array:id", "required": true, "nullable": false, "min_items": 1}
      }
    },
    "protected-result": {
      "kind": "object",
      "fields": {
        "capability_id": {"type": "id", "required": true, "nullable": false},
        "result": {"type": "enum:protected-result", "required": true, "nullable": false},
        "evidence_ref_ids": {"type": "array:id", "required": true, "nullable": false, "min_items": 1}
      }
    },
    "path-comparison": {
      "kind": "object",
      "fields": {
        "path_id": {"type": "id", "required": true, "nullable": false},
        "kind": {"type": "enum:path-kind", "required": true, "nullable": false},
        "posture": {"type": "enum:path-posture", "required": true, "nullable": false},
        "rationale": {"type": "string", "required": true, "nullable": false, "min_length": 1},
        "evidence_ref_ids": {"type": "array:id", "required": true, "nullable": false, "min_items": 1}
      }
    },
    "scope-ref": {
      "kind": "object",
      "fields": {
        "owner_id": {"type": "id", "required": true, "nullable": false},
        "path": {"type": "repo-path", "required": true, "nullable": false},
        "content_root": {"type": "sha256", "required": true, "nullable": false}
      }
    },
    "external-boundary": {
      "kind": "object",
      "fields": {
        "boundary_id": {"type": "id", "required": true, "nullable": false},
        "posture": {"type": "string", "required": true, "nullable": false, "const": "reserved-external"},
        "boundary_class": {"type": "enum:external-boundary-class", "required": true, "nullable": false},
        "evidence_ref_ids": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
        "blocked_scope": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 1},
        "safe_frontier": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 0},
        "revisit_trigger": {"type": "string", "required": true, "nullable": false, "min_length": 1}
      }
    }
  },
  "enums": {
    "disposition": ["continue-unchanged", "correct-inline", "compare-candidate", "amend-structure"],
    "decision-stage": ["selected", "implementing", "validated", "reviewed", "cutover-eligible", "closed"],
    "target-class": ["target-repository", "software-factory"],
    "authority-effect": ["none", "mission-preserving-clarification", "direct-goal-change"],
    "external-boundary-class": ["unavailable-credential", "spend-authority", "destructive-permission", "external-communication", "external-release", "direct-goal-change"],
    "adaptive-decision-mode": ["fixed", "recommend", "reviewed-autonomous", "full-autonomous"],
    "mission-authority-source-class": ["direct-user", "system"],
    "evidence-source-class": ["direct-user", "system", "repository", "tracker", "canonical-event", "observed-outcome", "validation", "independent-review", "independent-evaluation"],
    "evidence-posture": ["adjudicating", "process", "current-outcome"],
    "protected-result": ["preserved", "regressed", "reopened"],
    "path-kind": ["local", "bounded-general", "architectural-owner"],
    "path-posture": ["selected", "rejected", "unavailable"],
    "isolation-kind": ["git-branch", "git-worktree", "temporary-repository", "equivalent-isolated-lane"],
    "review-disposition": ["accepted", "revise", "rejected", "inconclusive"],
    "retirement-posture": ["active-isolated", "eligible-cutover", "retired-loser", "retired-inconclusive", "cut-over"],
    "authoring-review-disposition": ["pending", "accepted", "revise", "rejected"],
    "comparison-dimension": ["observable-outcome", "implementation-cost", "maintenance-cost", "reversibility", "compatibility", "protected-capability"]
  },
  "common_fields": {
    "schema_version": {"type": "integer", "required": true, "nullable": false, "const": 1},
    "decision_id": {"type": "id", "required": true, "nullable": false},
    "decision_stage": {"type": "enum:decision-stage", "required": true, "nullable": false},
    "disposition": {"type": "enum:disposition", "required": true, "nullable": false},
    "recorded_at": {"type": "timestamp", "required": true, "nullable": false},
    "predecessor_decision_id": {"type": "id", "required": true, "nullable": true},
    "currentness_refresh_of": {"type": "id", "required": true, "nullable": true},
    "mission_root": {"type": "sha256", "required": true, "nullable": false},
    "authority_effect": {"type": "enum:authority-effect", "required": true, "nullable": false},
    "authority_claim_id": {"type": "id", "required": true, "nullable": true},
    "authority_evidence_refs": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "prior_mission_root": {"type": "sha256", "required": true, "nullable": false},
    "proposed_mission_root": {"type": "sha256", "required": true, "nullable": true},
    "tracker_path": {"type": "repo-path", "required": true, "nullable": false},
    "tracker_sha256": {"type": "sha256", "required": true, "nullable": false},
    "block_number": {"type": "integer", "required": true, "nullable": false, "minimum": 0},
    "block_contract_root": {"type": "sha256", "required": true, "nullable": false},
    "target_class": {"type": "enum:target-class", "required": true, "nullable": false},
    "target_repository_root": {"type": "repo-path", "required": true, "nullable": false},
    "decision_target_state_root": {"type": "sha256", "required": true, "nullable": false},
    "target_revision": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "target_revision_root": {"type": "sha256", "required": true, "nullable": false},
    "current_target_state_root": {"type": "sha256", "required": true, "nullable": false},
    "capability_statement": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "capability_frame_root": {"type": "sha256", "required": true, "nullable": false},
    "protected_capability_results": {"type": "array:protected-result", "required": true, "nullable": false, "min_items": 1},
    "evidence_refs": {"type": "array:evidence-ref", "required": true, "nullable": false, "min_items": 1},
    "adjudicating_evidence_ref_ids": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
    "adjudicating_evidence_root": {"type": "sha256", "required": true, "nullable": false},
    "evidence_manifest_root": {"type": "sha256", "required": true, "nullable": false},
    "decision_fingerprint": {"type": "sha256", "required": true, "nullable": false},
    "compared_paths": {"type": "array:path-comparison", "required": true, "nullable": false, "min_items": 3, "max_items": 3},
    "selected_path": {"type": "id", "required": true, "nullable": true},
    "rejected_paths": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "affected_scope": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 0},
    "valid_work_refs": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "stale_proof_refs": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "safe_frontier": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 0},
    "adaptive_decision_mode": {"type": "enum:adaptive-decision-mode", "required": true, "nullable": false},
    "proposer_author_id": {"type": "id", "required": true, "nullable": true},
    "implementation_owner_id": {"type": "id", "required": true, "nullable": false},
    "reviewer_id": {"type": "id", "required": true, "nullable": true},
    "evaluator_id": {"type": "id", "required": true, "nullable": true},
    "stop_boundary": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "policy_root": {"type": "sha256", "required": true, "nullable": false},
    "event_head_root": {"type": "sha256", "required": true, "nullable": false},
    "accepted_decision_head": {"type": "sha256", "required": true, "nullable": true},
    "accepted_revision_head": {"type": "sha256", "required": true, "nullable": true},
    "currentness_root": {"type": "sha256", "required": true, "nullable": false},
    "revisit_trigger": {"type": "string", "required": true, "nullable": true},
    "external_boundary": {"type": "external-boundary", "required": true, "nullable": true}
  },
  "candidate_fields": {
    "hypothesis": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "hypothesis_scope": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 1},
    "incumbent_root": {"type": "sha256", "required": true, "nullable": false},
    "candidate_root": {"type": "sha256", "required": true, "nullable": true},
    "isolation_kind": {"type": "enum:isolation-kind", "required": true, "nullable": false},
    "isolated_writable_scope": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 1},
    "shared_resource_exclusions": {"type": "array:scope-ref", "required": true, "nullable": false, "min_items": 0},
    "resource_ceiling": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "time_ceiling": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "stop_condition": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "production_authority_owner_id": {"type": "id", "required": true, "nullable": false},
    "focused_validation": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
    "mapped_validation": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "validation_order": {"type": "string", "required": true, "nullable": false, "const": "focused-then-mapped"},
    "comparison_dimensions": {"type": "array:enum:comparison-dimension", "required": true, "nullable": false, "min_items": 6, "max_items": 6},
    "independent_reviewer_id": {"type": "id", "required": true, "nullable": false},
    "review_root": {"type": "sha256", "required": true, "nullable": true},
    "review_disposition": {"type": "enum:review-disposition", "required": true, "nullable": true},
    "cutover_owner_id": {"type": "id", "required": true, "nullable": false},
    "cutover_preconditions": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
    "retirement_posture": {"type": "enum:retirement-posture", "required": true, "nullable": false}
  },
  "structural_fields": {
    "revision_id": {"type": "id", "required": true, "nullable": false},
    "structural_reason": {"type": "string", "required": true, "nullable": false, "min_length": 1},
    "proposed_mutations": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
    "old_to_new_block_map": {"type": "object:string-to-array:integer", "required": true, "nullable": false},
    "dependency_closure": {"type": "array:integer", "required": true, "nullable": false, "min_items": 1},
    "accepted_history_boundary": {"type": "sha256", "required": true, "nullable": false},
    "proposed_tracker_root": {"type": "sha256", "required": true, "nullable": true},
    "invalidated_evidence_refs": {"type": "array:id", "required": true, "nullable": false, "min_items": 0},
    "preserved_evidence_refs": {"type": "array:id", "required": true, "nullable": false, "min_items": 1},
    "resume_point": {"type": "integer", "required": true, "nullable": false, "minimum": 0},
    "author_owner_id": {"type": "id", "required": true, "nullable": false},
    "authoring_reviewer_id": {"type": "id", "required": true, "nullable": false},
    "authoring_review_root": {"type": "sha256", "required": true, "nullable": true},
    "authoring_review_disposition": {"type": "enum:authoring-review-disposition", "required": true, "nullable": false}
  },
  "evidence_reference_rules": {
    "unique_fields": ["evidence_refs.ref_id", "evidence_refs[].claim_ids"],
    "resolve_fields": ["authority_evidence_refs", "adjudicating_evidence_ref_ids", "protected_capability_results[].evidence_ref_ids", "compared_paths[].evidence_ref_ids", "external_boundary.evidence_ref_ids?", "valid_work_refs", "stale_proof_refs", "invalidated_evidence_refs?", "preserved_evidence_refs?"],
    "claim_bindings": [
      {"refs": "authority_evidence_refs", "claim": "authority_claim_id"},
      {"refs": "protected_capability_results[].evidence_ref_ids", "claim": "protected_capability_results[].capability_id"},
      {"refs": "compared_paths[].evidence_ref_ids", "claim": "compared_paths[].path_id"},
      {"refs": "external_boundary.evidence_ref_ids?", "claim": "external_boundary.boundary_id?"}
    ]
  },
  "identity_evidence_rules": {
    "reviewer_id": {"when_nonnull_source_class": "independent-review", "claim_id_field": "reviewer_id"},
    "evaluator_id": {"when_nonnull_source_class": "independent-evaluation", "claim_id_field": "evaluator_id"}
  },
  "stage_rules": {
    "allowed_transitions": {
      "selected": ["implementing", "validated", "closed"],
      "implementing": ["validated", "closed"],
      "validated": ["reviewed", "cutover-eligible", "closed"],
      "reviewed": ["cutover-eligible", "closed"],
      "cutover-eligible": ["closed"],
      "closed": []
    },
    "required_evidence_source_classes": {
      "selected": [],
      "implementing": [],
      "validated": ["validation"],
      "reviewed": ["validation", "independent-review"],
      "cutover-eligible": ["validation", "independent-review", "observed-outcome"],
      "closed": []
    },
    "closed_required_by_disposition": {
      "continue-unchanged": ["observed-outcome"],
      "correct-inline": ["validation", "observed-outcome"],
      "compare-candidate": ["validation", "independent-review", "observed-outcome"],
      "amend-structure": ["validation", "independent-review"]
    },
    "cutover-eligible": {"disposition": "compare-candidate", "nonnull": ["candidate_root", "review_root", "review_disposition"], "equals": [["review_disposition", "accepted"], ["retirement_posture", "eligible-cutover"]]},
    "nonnull_by_disposition_stage": {
      "compare-candidate.validated": ["candidate_root"],
      "compare-candidate.reviewed": ["candidate_root", "review_root", "review_disposition"],
      "compare-candidate.closed": ["candidate_root", "review_root", "review_disposition"],
      "amend-structure.validated": ["proposed_tracker_root"],
      "amend-structure.reviewed": ["proposed_tracker_root", "authoring_review_root"],
      "amend-structure.closed": ["proposed_tracker_root", "authoring_review_root"]
    },
    "validation_claim_fields": {
      "correct-inline": ["decision_id", "current_target_state_root"],
      "compare-candidate": ["decision_id", "candidate_root"],
      "amend-structure": ["decision_id", "proposed_tracker_root"]
    },
    "observed_outcome_claim_fields": ["decision_id", "current_target_state_root", "target_revision_root"],
    "candidate_observed_outcome_additional_claim_fields": ["candidate_root"],
    "candidate_review_binding": {"source_class": "independent-review", "root_field": "review_root", "claim_fields": ["decision_id", "candidate_root", "reviewer_id", "review_disposition"]},
    "structural_review_binding": {"source_class": "independent-review", "root_field": "authoring_review_root", "claim_fields": ["decision_id", "proposed_tracker_root", "authoring_reviewer_id", "authoring_review_disposition"]},
    "candidate_closed_retirement": {
      "accepted": ["cut-over", "retired-loser"],
      "revise": ["retired-inconclusive"],
      "rejected": ["retired-loser"],
      "inconclusive": ["retired-inconclusive"]
    },
    "software-factory-additional-evidence": {"stages": ["reviewed", "cutover-eligible", "closed"], "source_classes": ["independent-review", "independent-evaluation"], "claim_fields": ["decision_id", "reviewer_id", "evaluator_id"]}
  },
  "array_order": {
    "authority_evidence_refs": "id-ascending",
    "protected_capability_results": "capability_id-ascending",
    "evidence_refs": "ref_id-ascending",
    "adjudicating_evidence_ref_ids": "id-ascending",
    "evidence-ref.claim_ids": "id-ascending",
    "protected-result.evidence_ref_ids": "id-ascending",
    "compared_paths": "path-kind-enum-order",
    "path-comparison.evidence_ref_ids": "id-ascending",
    "rejected_paths": "compared-path-order",
    "affected_scope": "owner_id,path,content_root-ascending",
    "valid_work_refs": "id-ascending",
    "stale_proof_refs": "id-ascending",
    "safe_frontier": "owner_id,path,content_root-ascending",
    "external-boundary.evidence_ref_ids": "id-ascending",
    "external-boundary.blocked_scope": "owner_id,path,content_root-ascending",
    "external-boundary.safe_frontier": "owner_id,path,content_root-ascending",
    "hypothesis_scope": "owner_id,path,content_root-ascending",
    "isolated_writable_scope": "owner_id,path,content_root-ascending",
    "shared_resource_exclusions": "owner_id,path,content_root-ascending",
    "focused_validation": "id-ascending",
    "mapped_validation": "id-ascending",
    "comparison_dimensions": "comparison-dimension-enum-order",
    "cutover_preconditions": "id-ascending",
    "proposed_mutations": "id-ascending",
    "old_to_new_block_map.values": "integer-ascending",
    "dependency_closure": "integer-ascending",
    "invalidated_evidence_refs": "id-ascending",
    "preserved_evidence_refs": "id-ascending"
  },
  "fingerprint_projection": ["schema_version", "mission_root", "authority_effect", "authority_claim_id", "authority_evidence_refs", "prior_mission_root", "proposed_mission_root", "tracker_path", "block_number", "block_contract_root", "target_class", "target_repository_root", "decision_target_state_root", "capability_statement", "capability_frame_root", "protected_capability_results", "adjudicating_evidence_ref_ids", "adjudicating_evidence_root", "compared_paths", "affected_scope", "implementation_owner_id", "stop_boundary"],
  "candidate_fingerprint_projection": ["hypothesis", "hypothesis_scope", "incumbent_root", "isolation_kind", "isolated_writable_scope", "shared_resource_exclusions", "resource_ceiling", "time_ceiling", "stop_condition", "production_authority_owner_id", "focused_validation", "mapped_validation", "validation_order", "comparison_dimensions", "independent_reviewer_id", "cutover_owner_id", "cutover_preconditions"],
  "structural_fingerprint_projection": ["structural_reason", "proposed_mutations", "old_to_new_block_map", "dependency_closure", "accepted_history_boundary", "invalidated_evidence_refs", "preserved_evidence_refs", "resume_point", "author_owner_id", "authoring_reviewer_id"],
  "currentness_projection": ["decision_fingerprint", "decision_stage", "evidence_manifest_root", "tracker_sha256", "policy_root", "event_head_root", "target_revision", "target_revision_root", "current_target_state_root", "safe_frontier", "adaptive_decision_mode", "external_boundary", "accepted_decision_head", "accepted_revision_head", "candidate_root?", "review_root?", "review_disposition?", "retirement_posture?", "proposed_tracker_root?", "authoring_review_root?", "authoring_review_disposition?"],
  "role_rules": {
    "target-repository": {
      "continue-unchanged": {"must_be_null": ["proposer_author_id", "reviewer_id", "evaluator_id"]},
      "correct-inline": {"must_be_null": ["proposer_author_id", "reviewer_id", "evaluator_id"]},
      "compare-candidate": {"must_be_nonnull": ["reviewer_id"], "must_be_null": ["proposer_author_id", "evaluator_id"], "equal": [["reviewer_id", "independent_reviewer_id"], ["implementation_owner_id", "production_authority_owner_id"]], "not_equal": [["reviewer_id", "implementation_owner_id"], ["reviewer_id", "cutover_owner_id"]]},
      "amend-structure": {"must_be_nonnull": ["reviewer_id"], "must_be_null": ["proposer_author_id", "evaluator_id"], "equal": [["reviewer_id", "authoring_reviewer_id"]], "not_equal": [["reviewer_id", "author_owner_id"], ["reviewer_id", "implementation_owner_id"]]}
    },
    "software-factory": {
      "continue-unchanged": {"must_be_null": ["proposer_author_id", "reviewer_id", "evaluator_id"]},
      "correct-inline": {"must_be_nonnull": ["proposer_author_id", "reviewer_id", "evaluator_id"], "distinct": ["proposer_author_id", "implementation_owner_id", "reviewer_id", "evaluator_id"]},
      "compare-candidate": {"must_be_nonnull": ["proposer_author_id", "reviewer_id", "evaluator_id"], "equal": [["reviewer_id", "independent_reviewer_id"], ["implementation_owner_id", "production_authority_owner_id"]], "distinct": ["proposer_author_id", "implementation_owner_id", "reviewer_id", "evaluator_id", "cutover_owner_id"]},
      "amend-structure": {"must_be_nonnull": ["proposer_author_id", "reviewer_id", "evaluator_id"], "equal": [["proposer_author_id", "author_owner_id"], ["reviewer_id", "authoring_reviewer_id"]], "distinct": ["proposer_author_id", "implementation_owner_id", "reviewer_id", "evaluator_id"]}
    }
  },
  "cross_field_rule_ids": ["exact-three-paths", "selected-path-membership", "rejected-path-membership", "evidence-reference-integrity", "evidence-claim-binding", "identity-evidence-binding", "adjudicating-evidence-subset", "evidence-manifest-root", "stage-transition", "stage-evidence", "fresh-decision-link", "currentness-refresh-link", "links-mutually-exclusive", "authority-none", "mission-preserving-clarification", "direct-goal-change-reject", "reserved-external-bounded", "candidate-fields-by-disposition", "structural-fields-by-disposition", "software-factory-role-separation"]
}
```

Canonical bytes use the JSON Canonicalization Scheme (RFC 8785), encoded as
UTF-8 with no BOM or trailing newline. Inputs first reject duplicate keys,
floats, non-finite numbers, strings outside Unicode NFC, unknown object keys,
and values that fail the embedded grammar. Every array is sorted by its exact
`array_order` rule before hashing; a submitted noncanonical order is rejected.
`decision_fingerprint` is SHA-256 of canonical bytes for exactly the common
`fingerprint_projection`, plus a `candidate` object containing exactly the
`candidate_fingerprint_projection` for `compare-candidate` or a `structural`
object containing exactly the `structural_fingerprint_projection` for
`amend-structure`. `currentness_root` is SHA-256 of canonical bytes for exactly
the `currentness_projection`; `?` fields are included, with null retained, only
for their owning disposition. Roots are lowercase hexadecimal.

The cross-field rules are:

- `exact-three-paths`: `compared_paths` has exactly one `local`, one
  `bounded-general`, and one `architectural-owner`, ordered as shown in the
  enum.
- `selected-path-membership`: `selected_path` is null only for unresolved
  candidate/structural selection; otherwise it names the sole `selected` path.
- `rejected-path-membership`: `rejected_paths` equals the ordered IDs of every
  `rejected` comparison and no other path.
- `evidence-reference-integrity`: `evidence_refs.ref_id` values are unique;
  every `claim_ids` list is unique; and every ID named by a
  `evidence_reference_rules.resolve_fields` path resolves exactly once in
  `evidence_refs`. Optional `?` paths are skipped only when their owning
  disposition/object is absent.
- `evidence-claim-binding`: for every `claim_bindings` entry, every resolved
  evidence object contains the paired claim value in its `claim_ids`. A dangling
  reference or evidence for a different claim rejects the record.
- `identity-evidence-binding`: every non-null identity named in
  `identity_evidence_rules` has at least one complete evidence object with the
  exact required `source_class` and that identity in `claim_ids`. A role label
  without attributable evidence does not establish independent participation.
- `adjudicating-evidence-subset`: every
  `adjudicating_evidence_ref_ids` value resolves exactly once in
  `evidence_refs`. The set equals all and only refs used by authority,
  protected-capability, and compared-path claim bindings, plus external-boundary
  refs only when `boundary_class == direct-goal-change`; every member has
  `adjudication_posture == adjudicating`. Other external-boundary and
  observed-outcome refs are `current-outcome`; every other nonmember is
  `process`. `adjudicating_evidence_root` is SHA-256 of canonical bytes for the
  complete member objects in ID order. Omission, addition, or posture mismatch
  rejects the record; changing a member creates a successor decision.
- `evidence-manifest-root`: `evidence_manifest_root` is SHA-256 of canonical
  bytes for the complete ordered `evidence_refs` array.
- `stage-transition`: decision records are immutable. A changed
  `decision_stage` appends a new record linked by `currentness_refresh_of`, keeps
  the same `decision_fingerprint`, follows `stage_rules.allowed_transitions`,
  and changes `currentness_root`. Regression or transition from `closed` is
  rejected.
- `stage-evidence`: the complete evidence catalog contains every source class
  required for the current stage, using `process` for validation/review and
  `current-outcome` for observed outcomes. Each required validation and outcome
  object contains the exact configured claim fields. Candidate and structural
  review evidence additionally has `root_sha256` equal to its configured review
  root and contains every configured claim. `cutover-eligible` satisfies its
  exact disposition, non-null, accepted-review, and eligible-retirement rules.
  A closed candidate satisfies `candidate_closed_retirement`; therefore
  `active-isolated` and `eligible-cutover` are never terminal. `software-factory`
  stages listed in
  `software-factory-additional-evidence` additionally contain both an
  independent-review and independent-evaluation reference bound to the current
  record.
- `fresh-decision-link`: new adjudicating evidence requires non-null
  `predecessor_decision_id` and null `currentness_refresh_of`.
- `currentness-refresh-link`: context-, stage-, validation-, review-, or
  outcome-only refresh requires non-null `currentness_refresh_of`, null
  `predecessor_decision_id`, and the same `decision_fingerprint`; its changed
  `evidence_manifest_root` and currentness outputs are retained in the new
  immutable record.
- `links-mutually-exclusive`: both linkage fields cannot be non-null.
- `authority-none`: `authority_claim_id` is null,
  `authority_evidence_refs` is empty, `prior_mission_root == mission_root`, and
  `proposed_mission_root` is null.
- `mission-preserving-clarification`: at least one exact eligible direct
  authority reference is present, each resolves to an `evidence_ref` whose
  `source_class` is in `mission-authority-source-class`, non-null
  `authority_claim_id` is bound through `evidence-claim-binding`, and
  `prior_mission_root == proposed_mission_root == mission_root`.
- `direct-goal-change-reject`: at least one exact eligible direct authority
  reference meeting the same source-class and claim-binding rules and a non-null
  `proposed_mission_root != mission_root` classify a direct goal change. No
  adaptive disposition may authorize mutation; fail
  closed to the separate mission-binding owner. Routed, review, supervisor, or
  Factory preference never proves this rule.
- `reserved-external-bounded`: `external_boundary` is null unless an exact
  current boundary in `external-boundary-class` is proven. When non-null, its
  posture is exactly `reserved-external`; the record binds evidence, the
  smallest blocked scope, continuing safe frontier, and revisit trigger. It
  cannot authorize the blocked action, stop unaffected work, or create a
  repeated human request. `direct-goal-change` requires both this boundary and
  `authority_effect == direct-goal-change`; all other classes require
  `authority_effect != direct-goal-change`.
- `candidate-fields-by-disposition`: candidate fields are present only and all
  present for `compare-candidate`.
- `structural-fields-by-disposition`: structural fields are present only and
  all present for `amend-structure`.
- `software-factory-role-separation`: apply the exact `role_rules` entry for the
  target class and disposition. `must_be_nonnull`, `must_be_null`, `equal`,
  `not_equal`, and `distinct` are exhaustive; `distinct` means every listed
  identity is pairwise unequal, while `not_equal` applies only to its named
  pairs. Null never proves equality or separation.

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
- `author_owner_id`, `authoring_reviewer_id`, `authoring_review_root`, and
  `authoring_review_disposition`.

The packet is proposed evidence, not a tracker edit. It cannot change the
mission root or product doctrine. Accepted Blocks, commits, reviews, findings,
and completion evidence remain historical truth. An accepted structural delta
selectively invalidates only evidence whose contract or dependency basis
changed, then resumes from the earliest affected dependency-safe point.

## Currentness and conflict rules

The `decision_fingerprint` freezes the mission and Block-contract identity,
`decision_target_state_root`, capability/protected-capability projection, exact
adjudicating evidence, compared paths, affected scope, implementation owner,
and Stop. It intentionally excludes the mutable whole-tracker hash, current
target state, safe frontier, policy mode, and external boundary. The
`currentness_root` binds those mutable values plus stage, complete evidence
manifest, current policy/event heads, target revision/root, current target-state
root, candidate/review or structural-review outputs, and accepted decision or
revision heads.

- Equal fingerprint plus equal currentness is idempotent and is not
  reconsidered.
- Changed tracker status/evidence, implementation state, safe frontier, policy
  mode, or external-boundary posture without new adjudicating evidence refreshes
  currentness but does not reopen the decision.
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
