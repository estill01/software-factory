#!/usr/bin/env python3
"""Static contract tests for adaptive implementation decision control."""

from __future__ import annotations

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


class AdaptiveDecisionControlContractTests(unittest.TestCase):
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
