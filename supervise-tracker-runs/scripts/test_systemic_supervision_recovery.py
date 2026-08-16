#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "systemic_supervision_recovery_v1.json"
)
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class SystemicSupervisionRecoveryBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = FIXTURE_PATH.read_text(encoding="utf-8")
        cls.fixture = json.loads(cls.raw)

    def test_fixture_is_content_minimized_and_owner_bound(self) -> None:
        self.assertEqual(
            self.fixture["kind"],
            "software-factory-systemic-supervision-recovery-regression",
        )
        incident = self.fixture["incident"]
        self.assertEqual(incident["cause_owner"], "software-factory")
        self.assertEqual(incident["required_target_posture"], "in-progress")
        self.assertFalse(incident["manual_resume_required"])
        self.assertFalse(incident["human_input_required"])
        self.assertTrue(incident["safe_frontier"])
        self.assertEqual(
            set(self.fixture["owner_map"]),
            {
                "classification_and_recovery_history",
                "repair",
                "candidate_acceptance",
                "release_activation",
                "role_refresh",
                "range_currentness",
                "tracker_reconciliation",
                "target_wake",
                "effectiveness",
            },
        )
        for forbidden in ("patent", "/users/", "prompt text", "finding set"):
            self.assertNotIn(forbidden, self.raw.lower())

    def test_fixture_freezes_exact_source_adaptation(self) -> None:
        source = self.fixture["source_adaptation"]
        for field in (
            "accepted_source_commit",
            "automatic_currentness_commit",
            "shared_predecessor_commit",
        ):
            self.assertRegex(source[field], COMMIT)
        self.assertEqual(
            source["disposition"], "content-minimized-control-plane-adaptation"
        )

    def test_fixture_declares_the_complete_owner_sequence(self) -> None:
        self.assertEqual(
            self.fixture["expected_transitions"],
            [
                "detected",
                "classified",
                "contained",
                "repair-routed",
                "candidate-current",
                "candidate-accepted",
                "release-active",
                "roles-refreshed",
                "range-current",
                "tracker-reconciled",
                "wake-routed",
                "target-advanced",
                "effectiveness-reviewed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
