#!/usr/bin/env python3
"""Static contract tests for adaptive implementation decision control."""

from __future__ import annotations

import json
import hashlib
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (SKILL_ROOT / "references" / "adaptive-decision-control.md").read_text(
    encoding="utf-8"
)
IMPLEMENT_SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
AUTHOR_SKILL = (
    SKILL_ROOT.parent / "author-implementation-trackers" / "SKILL.md"
).read_text(encoding="utf-8")
SUPERVISE_SKILL = (
    SKILL_ROOT.parent / "supervise-tracker-runs" / "SKILL.md"
).read_text(encoding="utf-8")
SPEC_TEXT = REFERENCE.split("<!-- contract-spec-v1 -->", 1)[1].split("```json", 1)[1].split("```", 1)[0]
SPEC = json.loads(SPEC_TEXT)


def canonical_test_root(value: object) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AdaptiveDecisionControlContractTests(unittest.TestCase):
    def test_embedded_v1_spec_is_closed_and_machine_readable(self) -> None:
        self.assertEqual(SPEC["schema_version"], 1)
        self.assertIs(SPEC["closed_objects"], True)
        self.assertEqual(
            set(SPEC),
            {
                "schema_version",
                "closed_objects",
                "named_types",
                "enums",
                "common_fields",
                "candidate_fields",
                "structural_fields",
                "evidence_reference_rules",
                "identity_evidence_rules",
                "stage_rules",
                "array_order",
                "fingerprint_projection",
                "candidate_fingerprint_projection",
                "structural_fingerprint_projection",
                "currentness_projection",
                "role_rules",
                "cross_field_rule_ids",
            },
        )

    def test_exact_common_field_types_cardinality_and_nullability(self) -> None:
        fields = SPEC["common_fields"]
        expected_types = {
            "schema_version": "integer",
            "decision_id": "id",
            "decision_stage": "enum:decision-stage",
            "disposition": "enum:disposition",
            "recorded_at": "timestamp",
            "predecessor_decision_id": "id",
            "currentness_refresh_of": "id",
            "mission_root": "sha256",
            "authority_effect": "enum:authority-effect",
            "authority_claim_id": "id",
            "authority_evidence_refs": "array:id",
            "prior_mission_root": "sha256",
            "proposed_mission_root": "sha256",
            "tracker_path": "repo-path",
            "tracker_sha256": "sha256",
            "block_number": "integer",
            "block_contract_root": "sha256",
            "target_class": "enum:target-class",
            "target_repository_root": "repo-path",
            "target_revision": "string",
            "target_state_root": "sha256",
            "capability_statement": "string",
            "capability_frame_root": "sha256",
            "protected_capability_results": "array:protected-result",
            "evidence_refs": "array:evidence-ref",
            "adjudicating_evidence_ref_ids": "array:id",
            "adjudicating_evidence_root": "sha256",
            "evidence_manifest_root": "sha256",
            "decision_fingerprint": "sha256",
            "compared_paths": "array:path-comparison",
            "selected_path": "id",
            "rejected_paths": "array:id",
            "affected_scope": "array:scope-ref",
            "valid_work_refs": "array:id",
            "stale_proof_refs": "array:id",
            "safe_frontier": "array:scope-ref",
            "adaptive_decision_mode": "enum:adaptive-decision-mode",
            "proposer_author_id": "id",
            "implementation_owner_id": "id",
            "reviewer_id": "id",
            "evaluator_id": "id",
            "stop_boundary": "string",
            "policy_root": "sha256",
            "event_head_root": "sha256",
            "accepted_decision_head": "sha256",
            "accepted_revision_head": "sha256",
            "currentness_root": "sha256",
            "revisit_trigger": "string",
            "external_boundary": "external-boundary",
        }
        self.assertEqual({name: spec["type"] for name, spec in fields.items()}, expected_types)
        self.assertTrue(all(spec["required"] is True for spec in fields.values()))
        self.assertEqual(
            {name for name, spec in fields.items() if spec["nullable"]},
            {
                "predecessor_decision_id",
                "currentness_refresh_of",
                "authority_claim_id",
                "proposed_mission_root",
                "selected_path",
                "proposer_author_id",
                "reviewer_id",
                "evaluator_id",
                "accepted_decision_head",
                "accepted_revision_head",
                "revisit_trigger",
                "external_boundary",
            },
        )

    def test_exact_vocabularies_are_stable(self) -> None:
        enums = SPEC["enums"]
        self.assertEqual(
            enums["disposition"],
            ["continue-unchanged", "correct-inline", "compare-candidate", "amend-structure"],
        )
        self.assertEqual(
            enums["adaptive-decision-mode"],
            ["fixed", "recommend", "reviewed-autonomous", "full-autonomous"],
        )
        self.assertEqual(
            enums["review-disposition"],
            ["accepted", "revise", "rejected", "inconclusive"],
        )
        self.assertEqual(
            enums["authoring-review-disposition"],
            ["pending", "accepted", "revise", "rejected"],
        )
        self.assertEqual(
            enums["isolation-kind"],
            ["git-branch", "git-worktree", "temporary-repository", "equivalent-isolated-lane"],
        )
        self.assertEqual(len(enums["comparison-dimension"]), 6)
        self.assertEqual(
            enums["external-boundary-class"],
            [
                "unavailable-credential",
                "spend-authority",
                "destructive-permission",
                "external-communication",
                "external-release",
                "direct-goal-change",
            ],
        )
        self.assertEqual(
            enums["mission-authority-source-class"], ["direct-user", "system"]
        )
        self.assertIn("independent-evaluation", enums["evidence-source-class"])

    def test_root_projections_and_successor_links_are_exact(self) -> None:
        self.assertEqual(SPEC["array_order"]["evidence_refs"], "ref_id-ascending")
        self.assertEqual(
            SPEC["array_order"]["adjudicating_evidence_ref_ids"], "id-ascending"
        )
        self.assertEqual(
            SPEC["array_order"]["compared_paths"], "path-kind-enum-order"
        )
        self.assertEqual(
            SPEC["array_order"]["affected_scope"],
            "owner_id,path,content_root-ascending",
        )
        self.assertEqual(
            SPEC["array_order"]["comparison_dimensions"],
            "comparison-dimension-enum-order",
        )
        self.assertEqual(
            SPEC["array_order"]["dependency_closure"], "integer-ascending"
        )
        self.assertEqual(
            SPEC["fingerprint_projection"],
            [
                "schema_version",
                "mission_root",
                "authority_effect",
                "authority_claim_id",
                "authority_evidence_refs",
                "prior_mission_root",
                "proposed_mission_root",
                "tracker_path",
                "tracker_sha256",
                "block_number",
                "block_contract_root",
                "target_class",
                "target_repository_root",
                "target_state_root",
                "capability_statement",
                "capability_frame_root",
                "protected_capability_results",
                "adjudicating_evidence_ref_ids",
                "adjudicating_evidence_root",
                "compared_paths",
                "affected_scope",
                "safe_frontier",
                "adaptive_decision_mode",
                "implementation_owner_id",
                "stop_boundary",
                "external_boundary",
            ],
        )
        self.assertEqual(
            SPEC["currentness_projection"],
            [
                "decision_fingerprint",
                "decision_stage",
                "evidence_manifest_root",
                "policy_root",
                "event_head_root",
                "target_revision",
                "accepted_decision_head",
                "accepted_revision_head",
                "candidate_root?",
                "review_root?",
                "review_disposition?",
                "retirement_posture?",
                "proposed_tracker_root?",
                "authoring_review_disposition?",
            ],
        )
        self.assertEqual(
            SPEC["candidate_fingerprint_projection"][0:3],
            ["hypothesis", "hypothesis_scope", "incumbent_root"],
        )
        self.assertNotIn("review_root", SPEC["candidate_fingerprint_projection"])
        self.assertEqual(
            SPEC["structural_fingerprint_projection"][0:3],
            ["structural_reason", "proposed_mutations", "old_to_new_block_map"],
        )
        self.assertNotIn(
            "proposed_tracker_root", SPEC["structural_fingerprint_projection"]
        )
        self.assertIn("predecessor_decision_id", SPEC["common_fields"])
        self.assertIn("currentness_refresh_of", SPEC["common_fields"])
        self.assertIn("JSON Canonicalization Scheme (RFC 8785)", REFERENCE)
        self.assertIn("no BOM or trailing newline", REFERENCE)
        self.assertIn("floats, non-finite numbers", REFERENCE)
        self.assertIn("submitted noncanonical order is rejected", REFERENCE)

    def test_process_evidence_changes_currentness_not_decision_identity(self) -> None:
        source = {
            "ref_id": "source-1",
            "source_class": "repository",
            "root_sha256": "a" * 64,
            "claim_ids": ["claim-source"],
        }
        validation = {
            "ref_id": "validation-1",
            "source_class": "validation",
            "root_sha256": "b" * 64,
            "claim_ids": ["claim-validation"],
        }
        common_projection = {
            key: f"value:{key}" for key in SPEC["fingerprint_projection"]
        }
        common_projection["schema_version"] = 1
        common_projection["adjudicating_evidence_ref_ids"] = ["source-1"]
        common_projection["adjudicating_evidence_root"] = canonical_test_root([source])
        fingerprint_before = canonical_test_root(common_projection)

        complete_before = canonical_test_root([source])
        complete_after = canonical_test_root([source, validation])
        self.assertNotEqual(complete_before, complete_after)
        self.assertEqual(fingerprint_before, canonical_test_root(common_projection))

        current_fields = [field.rstrip("?") for field in SPEC["currentness_projection"]]
        current_before = {field: f"value:{field}" for field in current_fields}
        current_before["decision_fingerprint"] = fingerprint_before
        current_before["evidence_manifest_root"] = complete_before
        current_after = {**current_before, "evidence_manifest_root": complete_after}
        self.assertNotEqual(
            canonical_test_root(current_before), canonical_test_root(current_after)
        )
        validated_stage = {**current_after, "decision_stage": "validated"}
        reviewed_stage = {**validated_stage, "decision_stage": "reviewed"}
        self.assertNotEqual(
            canonical_test_root(validated_stage), canonical_test_root(reviewed_stage)
        )
        self.assertEqual(
            validated_stage["decision_fingerprint"], reviewed_stage["decision_fingerprint"]
        )

        second_source = {
            "ref_id": "source-2",
            "source_class": "canonical-event",
            "root_sha256": "c" * 64,
            "claim_ids": ["claim-second"],
        }
        successor_projection = {
            **common_projection,
            "adjudicating_evidence_ref_ids": ["source-1", "source-2"],
            "adjudicating_evidence_root": canonical_test_root([source, second_source]),
        }
        self.assertNotEqual(
            fingerprint_before, canonical_test_root(successor_projection)
        )
        self.assertIn("requires non-null\n  `predecessor_decision_id`", REFERENCE)

    def test_stage_transitions_and_evidence_are_exact(self) -> None:
        stages = SPEC["stage_rules"]
        self.assertEqual(
            stages["allowed_transitions"],
            {
                "selected": ["implementing", "validated", "closed"],
                "implementing": ["validated", "closed"],
                "validated": ["reviewed", "cutover-eligible", "closed"],
                "reviewed": ["cutover-eligible", "closed"],
                "cutover-eligible": ["closed"],
                "closed": [],
            },
        )
        self.assertEqual(
            stages["required_evidence_source_classes"]["reviewed"],
            ["validation", "independent-review"],
        )
        self.assertEqual(
            stages["required_evidence_source_classes"]["cutover-eligible"],
            ["validation", "independent-review", "observed-outcome"],
        )
        self.assertEqual(
            stages["software-factory-additional-evidence"]["source_classes"],
            ["independent-review", "independent-evaluation"],
        )
        self.assertEqual(
            stages["cutover-eligible"]["equals"],
            [
                ["review_disposition", "accepted"],
                ["retirement_posture", "eligible-cutover"],
            ],
        )
        self.assertIn("transition from `closed` is\n  rejected", REFERENCE)

    def test_cross_field_rules_cover_authority_and_disposition_shapes(self) -> None:
        self.assertEqual(
            set(SPEC["cross_field_rule_ids"]),
            {
                "exact-three-paths",
                "selected-path-membership",
                "rejected-path-membership",
                "evidence-reference-integrity",
                "evidence-claim-binding",
                "identity-evidence-binding",
                "adjudicating-evidence-subset",
                "evidence-manifest-root",
                "stage-transition",
                "stage-evidence",
                "fresh-decision-link",
                "currentness-refresh-link",
                "links-mutually-exclusive",
                "authority-none",
                "mission-preserving-clarification",
                "direct-goal-change-reject",
                "reserved-external-bounded",
                "candidate-fields-by-disposition",
                "structural-fields-by-disposition",
                "software-factory-role-separation",
            },
        )
        self.assertIn("prior_mission_root == proposed_mission_root == mission_root", REFERENCE)
        self.assertIn("proposed_mission_root != mission_root", REFERENCE)
        self.assertIn("adaptive disposition may authorize mutation", REFERENCE)
        self.assertIn("posture is exactly `reserved-external`", REFERENCE)
        self.assertIn("complete ordered `evidence_refs` array", REFERENCE)
        self.assertIn("Later implementation, validation, review, or outcome evidence", REFERENCE)
        self.assertEqual(
            SPEC["identity_evidence_rules"],
            {
                "reviewer_id": {
                    "when_nonnull_source_class": "independent-review",
                    "claim_id_field": "reviewer_id",
                },
                "evaluator_id": {
                    "when_nonnull_source_class": "independent-evaluation",
                    "claim_id_field": "evaluator_id",
                },
            },
        )

    def test_role_rules_are_exact_per_target_and_disposition(self) -> None:
        roles = SPEC["role_rules"]
        self.assertEqual(set(roles), {"target-repository", "software-factory"})
        dispositions = {
            "continue-unchanged",
            "correct-inline",
            "compare-candidate",
            "amend-structure",
        }
        self.assertEqual(set(roles["target-repository"]), dispositions)
        self.assertEqual(set(roles["software-factory"]), dispositions)
        self.assertEqual(
            roles["target-repository"]["compare-candidate"]["equal"],
            [
                ["reviewer_id", "independent_reviewer_id"],
                ["implementation_owner_id", "production_authority_owner_id"],
            ],
        )
        self.assertEqual(
            roles["target-repository"]["compare-candidate"]["not_equal"],
            [
                ["reviewer_id", "implementation_owner_id"],
                ["reviewer_id", "cutover_owner_id"],
            ],
        )
        self.assertEqual(
            roles["target-repository"]["amend-structure"]["equal"],
            [["reviewer_id", "authoring_reviewer_id"]],
        )
        self.assertEqual(
            roles["target-repository"]["amend-structure"]["not_equal"],
            [
                ["reviewer_id", "author_owner_id"],
                ["reviewer_id", "implementation_owner_id"],
            ],
        )
        self.assertEqual(
            roles["software-factory"]["correct-inline"]["distinct"],
            ["proposer_author_id", "implementation_owner_id", "reviewer_id", "evaluator_id"],
        )
        self.assertIn(
            "cutover_owner_id",
            roles["software-factory"]["compare-candidate"]["distinct"],
        )
        self.assertIn(
            ["implementation_owner_id", "production_authority_owner_id"],
            roles["software-factory"]["compare-candidate"]["equal"],
        )

    def test_candidate_and_structural_extensions_are_closed(self) -> None:
        candidate = SPEC["candidate_fields"]
        self.assertEqual(
            set(candidate),
            {
                "hypothesis",
                "hypothesis_scope",
                "incumbent_root",
                "candidate_root",
                "isolation_kind",
                "isolated_writable_scope",
                "shared_resource_exclusions",
                "resource_ceiling",
                "time_ceiling",
                "stop_condition",
                "production_authority_owner_id",
                "focused_validation",
                "mapped_validation",
                "validation_order",
                "comparison_dimensions",
                "independent_reviewer_id",
                "review_root",
                "review_disposition",
                "cutover_owner_id",
                "cutover_preconditions",
                "retirement_posture",
            },
        )
        self.assertTrue(all(field["required"] is True for field in candidate.values()))
        self.assertEqual(
            {name for name, field in candidate.items() if field["nullable"]},
            {"candidate_root", "review_root", "review_disposition"},
        )
        self.assertEqual(candidate["validation_order"]["const"], "focused-then-mapped")
        self.assertEqual(candidate["comparison_dimensions"]["min_items"], 6)
        self.assertEqual(candidate["comparison_dimensions"]["max_items"], 6)

        structural = SPEC["structural_fields"]
        self.assertEqual(
            set(structural),
            {
                "revision_id",
                "structural_reason",
                "proposed_mutations",
                "old_to_new_block_map",
                "dependency_closure",
                "accepted_history_boundary",
                "proposed_tracker_root",
                "invalidated_evidence_refs",
                "preserved_evidence_refs",
                "resume_point",
                "author_owner_id",
                "authoring_reviewer_id",
                "authoring_review_disposition",
            },
        )
        self.assertTrue(all(field["required"] is True for field in structural.values()))
        self.assertEqual(
            {name for name, field in structural.items() if field["nullable"]},
            {"proposed_tracker_root"},
        )

    def test_evidence_and_path_records_bind_claims_and_exact_choices(self) -> None:
        evidence_fields = SPEC["named_types"]["evidence-ref"]["fields"]
        self.assertEqual(
            set(evidence_fields),
            {"ref_id", "source_class", "root_sha256", "claim_ids"},
        )
        self.assertEqual(evidence_fields["claim_ids"]["min_items"], 1)
        path_fields = SPEC["named_types"]["path-comparison"]["fields"]
        self.assertEqual(
            set(path_fields),
            {"path_id", "kind", "posture", "rationale", "evidence_ref_ids"},
        )
        self.assertEqual(path_fields["evidence_ref_ids"]["min_items"], 1)

        external_fields = SPEC["named_types"]["external-boundary"]["fields"]
        self.assertIn("boundary_id", external_fields)
        rules = SPEC["evidence_reference_rules"]
        self.assertEqual(
            rules["claim_bindings"],
            [
                {"refs": "authority_evidence_refs", "claim": "authority_claim_id"},
                {
                    "refs": "protected_capability_results[].evidence_ref_ids",
                    "claim": "protected_capability_results[].capability_id",
                },
                {
                    "refs": "compared_paths[].evidence_ref_ids",
                    "claim": "compared_paths[].path_id",
                },
                {
                    "refs": "external_boundary.evidence_ref_ids?",
                    "claim": "external_boundary.boundary_id?",
                },
            ],
        )

    def test_dangling_or_mismatched_evidence_claims_are_rejected(self) -> None:
        evidence = [
            {"ref_id": "ev-authority", "claim_ids": ["claim-authority"]},
            {"ref_id": "ev-capability", "claim_ids": ["capability-safe"]},
            {"ref_id": "ev-path", "claim_ids": ["path-local"]},
            {"ref_id": "ev-boundary", "claim_ids": ["boundary-release"]},
        ]

        def valid(bindings: list[tuple[list[str], str]]) -> bool:
            refs = [item["ref_id"] for item in evidence]
            if len(refs) != len(set(refs)):
                return False
            by_id = {item["ref_id"]: item for item in evidence}
            for ref_ids, claim_id in bindings:
                for ref_id in ref_ids:
                    if ref_id not in by_id or claim_id not in by_id[ref_id]["claim_ids"]:
                        return False
            return True

        accepted = [
            (["ev-authority"], "claim-authority"),
            (["ev-capability"], "capability-safe"),
            (["ev-path"], "path-local"),
            (["ev-boundary"], "boundary-release"),
        ]
        self.assertTrue(valid(accepted))
        self.assertFalse(valid([*accepted, (["missing-evidence"], "path-local")]))
        self.assertFalse(valid([*accepted, (["ev-path"], "path-general")]))

    def test_four_dispositions_form_the_smallest_sufficient_ladder(self) -> None:
        for disposition in (
            "`continue-unchanged`",
            "`correct-inline`",
            "`compare-candidate`",
            "`amend-structure`",
        ):
            self.assertIn(disposition, REFERENCE)
        self.assertIn("Classify the smallest decision", REFERENCE)
        self.assertIn("may escalate only when newly recorded evidence proves", REFERENCE)

    def test_unchanged_path_is_near_zero_cost_and_idempotent(self) -> None:
        self.assertIn("one O(1) comparison", REFERENCE)
        self.assertIn("without a model, reviewer, candidate, authoring cycle", REFERENCE)
        self.assertIn("Equal fingerprint plus equal currentness is idempotent", REFERENCE)
        self.assertIn("does not reopen the decision", REFERENCE)

    def test_inline_candidate_structural_boundaries_are_explicit(self) -> None:
        for trigger in (
            "wrong implementation owner",
            "lower-power shortcut",
            "unnecessary abstraction",
            "blind retry",
            "protected-capability regression",
            "implementation outcome evidence is necessary",
            "a dependency, acceptance criterion, or Stop must change",
        ):
            self.assertIn(trigger, REFERENCE)
        self.assertIn("current Block already authorizes a sufficient correction", REFERENCE)

    def test_non_triggers_reject_preference_difficulty_and_speculation(self) -> None:
        for non_trigger in (
            "optional refactor or style preference",
            "one transient test failure",
            "local implementation difficulty",
            "unproven future reuse",
            "repeated or equivalent accepted fingerprint",
            "broader scan opportunity",
        ):
            self.assertIn(non_trigger, REFERENCE)

    def test_common_record_has_reproducible_scope_and_evidence(self) -> None:
        for field in (
            "mission_root",
            "tracker_sha256",
            "block_contract_root",
            "target_state_root",
            "capability_frame_root",
            "protected_capability_results",
            "evidence_refs",
            "decision_fingerprint",
            "compared_paths",
            "affected_scope",
            "valid_work_refs",
            "stale_proof_refs",
            "safe_frontier",
            "adaptive_decision_mode",
            "stop_boundary",
            "currentness_root",
        ):
            self.assertIn(f"`{field}`", REFERENCE)
        self.assertIn("free-text evidence list does not establish behavior", REFERENCE)

    def test_candidate_is_bounded_isolated_reviewed_and_non_authoritative(self) -> None:
        for field in (
            "hypothesis_scope",
            "isolated_writable_scope",
            "shared_resource_exclusions",
            "resource_ceiling",
            "time_ceiling",
            "production_authority_owner_id",
            "validation_order",
            "comparison_dimensions",
            "independent_reviewer_id",
            "cutover_owner_id",
            "retirement_posture",
        ):
            self.assertIn(f"`{field}`", REFERENCE)
        self.assertIn("The candidate has no production authority", REFERENCE)
        self.assertIn("does not retain two live implementations", REFERENCE)

    def test_structural_packet_preserves_history_and_uses_authoring_owner(self) -> None:
        for field in (
            "revision_id",
            "proposed_mutations",
            "old_to_new_block_map",
            "dependency_closure",
            "accepted_history_boundary",
            "proposed_tracker_root",
            "resume_point",
        ):
            self.assertIn(f"`{field}`", REFERENCE)
        self.assertIn("cannot edit the tracker", REFERENCE)
        self.assertIn("`author-implementation-trackers` remains the sole tracker-writing method", REFERENCE)
        self.assertIn("preserve status and completion evidence", AUTHOR_SKILL)
        self.assertIn("implementation thread authoritative for its tracker", SUPERVISE_SKILL)
        self.assertIn("supervisors inspect and\nsteer but do not implement tracker work", SUPERVISE_SKILL)

    def test_currentness_recovery_and_conflicts_are_fail_closed(self) -> None:
        for phrase in (
            "fails closed to recompute the smallest affected slice",
            "Interruption resumes from the last validated owner checkpoint",
            "at most one active correction, candidate, or",
            "revision mutation owner",
            "cannot write the same scope concurrently",
            "Candidate failure retires only that lane",
        ):
            self.assertIn(phrase, REFERENCE)

    def test_modes_preserve_authority_and_full_autonomy_avoids_human_input(self) -> None:
        for mode in ("`fixed`", "`recommend`", "`reviewed-autonomous`", "`full-autonomous`"):
            self.assertIn(mode, REFERENCE)
        self.assertIn("no ordinary human-request or manual-Resume path", REFERENCE)
        self.assertIn("Only unavailable credentials, spend, destructive permission", REFERENCE)
        self.assertIn("No adaptive mode grants filesystem, credential, spend", REFERENCE)

    def test_one_protocol_covers_both_targets_with_self_change_separation(self) -> None:
        self.assertIn("`target-repository` and `software-factory` use the same decision ladder", REFERENCE)
        for role in ("proposer/author", "implementer", "independent reviewer", "evaluator"):
            self.assertIn(role, REFERENCE)
        self.assertIn("no role may self-promote", REFERENCE)
        self.assertIn("not an activated runtime controller", IMPLEMENT_SKILL)
        self.assertIn("adds no ledger, controller, registry, or service", REFERENCE)


if __name__ == "__main__":
    unittest.main()
