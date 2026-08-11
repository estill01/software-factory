#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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

    def test_fixture_is_blind_and_result_is_exactly_rooted(self) -> None:
        forbidden = {"expected_disposition", "intended_disposition", "expected_action"}
        self.assertFalse(
            any(forbidden.intersection(case) for case in self.fixture["cases"])
        )
        rebuilt = dict(self.result)
        root = rebuilt.pop("result_root")
        self.assertEqual(root, dogfood.digest(rebuilt))
        self.assertEqual(self.result["fixture_root"], dogfood.digest(self.fixture))

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
            self.assertIsNotNone(cases[case_id]["current_effect_root"])
            self.assertEqual(cases[case_id]["continue_to"], "block:5:remaining-work")
        self.assertEqual(cases["justified-no-correction"]["disposition"], "continue-unchanged")
        self.assertFalse(cases["justified-no-correction"]["extra_cycle"])
        self.assertEqual(cases["justified-no-correction"]["decision_stages"], [])
        self.assertTrue(cases["unchanged-fingerprint-repeat"]["deduplicated"])
        self.assertEqual(cases["candidate-needed"]["disposition"], "compare-candidate")
        self.assertEqual(cases["structural-evidence"]["disposition"], "amend-structure")

    def test_candidate_is_bounded_selective_and_never_dual_authority(self) -> None:
        cases = self.indexed("candidate_cases")
        winner = cases["candidate-winning-comparison"]
        self.assertEqual(winner["action"], "handoff-block-9")
        self.assertTrue(winner["lane_created"])
        self.assertTrue(winner["review_cycle"])
        self.assertFalse(winner["candidate_authoritative"])
        self.assertTrue(winner["incumbent_authoritative"])
        self.assertFalse(winner["cutover_performed"])
        self.assertIsNotNone(winner["handoff_root"])
        for case_id in (
            "candidate-losing-comparison",
            "candidate-inconclusive-comparison",
        ):
            self.assertEqual(cases[case_id]["action"], "retire-candidate")
            self.assertFalse(cases[case_id]["candidate_authoritative"])
            self.assertTrue(cases[case_id]["incumbent_authoritative"])
            self.assertIsNone(cases[case_id]["handoff_root"])
        self.assertEqual(cases["candidate-read-only-decidable"]["action"], "reject-before-lane")
        self.assertFalse(cases["candidate-read-only-decidable"]["lane_created"])
        for case_id in (
            "candidate-ceiling-stop",
            "candidate-mapped-stop",
            "candidate-review-currentness-stop",
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


if __name__ == "__main__":
    unittest.main()
