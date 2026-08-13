#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("adaptive_protocol_dogfood.py")
SPEC = importlib.util.spec_from_file_location("adaptive_protocol_dogfood", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
dogfood = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dogfood)


class AdaptiveProtocolDogfoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = dogfood.load_fixture()
        cls.result = dogfood.run_dogfood()

    def indexed(self, key: str) -> dict[str, dict[str, object]]:
        return {str(item["case_id"]): item for item in self.result[key]}

    def test_gitless_archive_source_revision_is_repository_bound(self) -> None:
        unavailable = subprocess.CompletedProcess(
            ["/usr/bin/git", "rev-parse", "HEAD"], 128, "", "no Git database"
        )
        with (
            mock.patch.object(dogfood.subprocess, "run", return_value=unavailable),
            mock.patch.object(dogfood, "ARCHIVE_SOURCE_REVISION", "a" * 40),
        ):
            self.assertEqual(dogfood.source_revision(), "a" * 40)
        with (
            mock.patch.object(dogfood.subprocess, "run", return_value=unavailable),
            mock.patch.object(
                dogfood, "ARCHIVE_SOURCE_REVISION", "$Format:%H$"
            ),
            self.assertRaisesRegex(dogfood.DogfoodError, "source revision"),
        ):
            dogfood.source_revision()

    def test_fixture_is_blind_and_result_is_exactly_rooted(self) -> None:
        forbidden = {"expected_disposition", "intended_disposition", "expected_action"}
        self.assertFalse(
            any(forbidden.intersection(case) for case in self.fixture["cases"])
        )
        rebuilt = dict(self.result)
        root = rebuilt.pop("result_root")
        self.assertEqual(root, dogfood.digest(rebuilt))
        self.assertEqual(self.result["fixture_root"], dogfood.digest(self.fixture))
        blind = self.result["blind_candidate_review_inputs"]
        self.assertEqual(len(blind), 7)
        blind_text = dogfood.canonical(blind).decode("utf-8")
        for disclosed in (
            "winning-candidate",
            "losing-candidate",
            "inconclusive-comparison",
            "expected_action",
            "expected_comparison_disposition",
        ):
            self.assertNotIn(disclosed, blind_text)
        for item in blind:
            rebuilt_input = dict(item)
            root = rebuilt_input.pop("review_input_root")
            self.assertEqual(root, dogfood.digest(rebuilt_input))
        structural = self.result["structural_target_effect"]
        self.assertNotIn("application_commit", structural)
        self.assertNotIn("review_root", structural)
        for item in self.result["target_class_cases"]:
            self.assertNotIn("application_handoff_root", item)
            self.assertNotIn("protocol_root", item)
        ordinary = self.indexed("authority_cases")["full-autonomous-ordinary"]
        self.assertNotIn("target_revision", ordinary["resolution"])

    def test_inline_default_no_change_and_selective_routing_are_demonstrated(self) -> None:
        cases = self.indexed("inline_cases")
        for case_id, selected in (
            ("external-inline-wrong-owner", "architectural-owner"),
            ("external-inline-lower-power", "bounded-general"),
            ("external-inline-generalized-layer", "local"),
        ):
            self.assertEqual(cases[case_id]["disposition"], "correct-inline")
            self.assertEqual(cases[case_id]["selected_path"], selected)
            self.assertEqual(cases[case_id]["decision_stages"][-1], "closed")
            self.assertIsNotNone(cases[case_id]["decision_state_root"])
            self.assertEqual(cases[case_id]["continue_to"], "block:5:remaining-work")
        self.assertEqual(cases["justified-no-correction"]["disposition"], "continue-unchanged")
        self.assertFalse(cases["justified-no-correction"]["extra_cycle"])
        self.assertEqual(cases["justified-no-correction"]["decision_stages"], [])
        self.assertTrue(cases["unchanged-fingerprint-repeat"]["deduplicated"])
        self.assertEqual(cases["candidate-needed"]["disposition"], "compare-candidate")
        self.assertEqual(cases["structural-evidence"]["disposition"], "amend-structure")
        effect = self.result["inline_target_effect"]
        self.assertEqual(effect["baseline_stdout"], "local-shortcut\n")
        self.assertEqual(effect["observed_stdout"], "canonical-owner:bounded\n")
        self.assertEqual(effect["application_state"], "current-effect-observed")
        self.assertEqual(effect["tracker_root_before"], effect["tracker_root_after"])
        rebuilt_effect = dict(effect)
        root = rebuilt_effect.pop("target_effect_root")
        self.assertEqual(root, dogfood.digest(rebuilt_effect))

    def test_candidate_is_bounded_selective_and_never_dual_authority(self) -> None:
        cases = self.indexed("candidate_cases")
        winner = cases["candidate-comparison-a"]
        self.assertEqual(winner["action"], "handoff-block-9")
        self.assertTrue(winner["lane_created"])
        self.assertTrue(winner["review_cycle"])
        self.assertFalse(winner["candidate_authoritative"])
        self.assertTrue(winner["incumbent_authoritative"])
        self.assertFalse(winner["cutover_performed"])
        self.assertIsNotNone(winner["handoff_root"])
        for case_id in (
            "candidate-comparison-b",
            "candidate-comparison-c",
        ):
            self.assertEqual(cases[case_id]["action"], "retire-candidate")
            self.assertFalse(cases[case_id]["candidate_authoritative"])
            self.assertTrue(cases[case_id]["incumbent_authoritative"])
            self.assertIsNone(cases[case_id]["handoff_root"])
        self.assertEqual(cases["candidate-eligibility-a"]["action"], "reject-before-lane")
        self.assertFalse(cases["candidate-eligibility-a"]["lane_created"])
        for case_id in (
            "candidate-stop-a",
            "candidate-stop-b",
            "candidate-stop-c",
        ):
            self.assertEqual(cases[case_id]["action"], "stop-retire")
            self.assertEqual(cases[case_id]["terminal_stage"], "closed")
            self.assertFalse(cases[case_id]["candidate_authoritative"])
        replay = cases["candidate-accepted-replay"]
        self.assertEqual(replay["action"], "deduplicate")
        self.assertFalse(replay["lane_created"])
        self.assertFalse(replay["review_cycle"])

    def test_target_classes_structural_review_and_autonomy_are_demonstrated(self) -> None:
        targets = self.indexed("target_class_cases")
        self.assertEqual(targets["external-target-inline"]["resume_action"], "normal-owner-inline-correction")
        self.assertEqual(targets["external-target-structural"]["resume_action"], "normal-authoring-owner-application")
        self.assertEqual(targets["software-factory-inline"]["resume_action"], "normal-owner-inline-correction")
        self.assertEqual(targets["software-factory-structural"]["resume_action"], "normal-authoring-owner-application")
        self.assertTrue(targets["software-factory-candidate"]["adoption_eligible"])
        self.assertEqual(targets["target-current-no-change"]["resume_action"], "continue-current-block")
        for case in targets.values():
            self.assertFalse(case["application_authorized"])
            self.assertEqual(case["human_request_count"], 0)
            self.assertFalse(case["tracker_mutated"])
            self.assertFalse(case["global_configuration_mutated"])
        authority = self.indexed("authority_cases")
        self.assertEqual(authority["full-autonomous-ordinary"]["application_posture"], "owner-application-ready")
        self.assertTrue(authority["full-autonomous-ordinary"]["application_ready"])
        self.assertEqual(authority["full-autonomous-reserved-external"]["application_posture"], "reserved-external")
        self.assertFalse(authority["full-autonomous-reserved-external"]["application_ready"])
        self.assertEqual(authority["full-autonomous-reserved-external"]["blocked_subjects"], ["credential-boundary"])
        self.assertTrue(authority["full-autonomous-reserved-external"]["safe_frontier"])
        resolution = authority["full-autonomous-ordinary"]["resolution"]
        self.assertEqual(resolution["observed_stdout"], "2\n")
        self.assertEqual(resolution["resolution_state"], "current-effect-observed")
        structural = self.result["structural_target_effect"]
        self.assertEqual(structural["application_state"], "reviewed-delta-applied-and-resume-current")
        self.assertEqual(structural["next_action"], "resume-block-7-without-user-scheduling")
        self.assertNotEqual(structural["previous_tracker_root"], structural["current_tracker_root"])
        self.assertTrue(structural["review_retry_duplicate"])
        self.assertTrue(structural["range_retry_duplicate"])
        remediation = self.result["accepted_block_remediation"]
        self.assertEqual(remediation["preserved_accepted_blocks"], [0, 1])
        self.assertEqual(remediation["remediation_block"], 2)
        self.assertEqual(remediation["resumed_block"], 3)
        self.assertEqual(remediation["current_effect_root"], self.result["inline_target_effect"]["target_effect_root"])
        self.assertEqual(remediation["closure_state"], "accepted-history-preserved-remediation-closed")
        self.assertEqual(authority["fixed-record-only"]["application_posture"], "record-only")
        self.assertEqual(authority["recommend-review-pending"]["application_posture"], "automated-independent-review-required")
        self.assertEqual(authority["recommend-review-complete"]["application_posture"], "recommendation-only")
        self.assertEqual(authority["reviewed-autonomous-consequential"]["application_posture"], "external-application-authority-required")
        self.assertEqual(
            {item["adaptive_decision_mode"] for item in authority.values()},
            {"fixed", "recommend", "reviewed-autonomous", "full-autonomous"},
        )
        self.assertTrue(all(item["human_request_count"] == 0 for item in authority.values()))
        self.assertEqual(self.result["human_request_count"], 0)

    def test_recovery_proof_is_current_and_no_reserved_effect_occurs(self) -> None:
        self.assertEqual(len(self.result["recovery_checks"]), 15)
        self.assertTrue(
            all(item["result"] == "passed" and item["tests_run"] == 1 for item in self.result["recovery_checks"])
        )
        for field in (
            "external_effects_performed",
            "release_mutated",
            "policy_mutated",
            "mission_mutated",
            "lifecycle_mutated",
        ):
            self.assertFalse(self.result[field])
        self.assertTrue(self.result["temporary_target_effects_performed"])


if __name__ == "__main__":
    unittest.main()
