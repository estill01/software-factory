#!/usr/bin/env python3
"""Mechanical checks for the repository reconciliation contract and fixtures."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "references" / "repository-reconciliation-contract.md"
FIXTURE = ROOT / "fixtures" / "repository_reconciliation_v1.json"
DISPOSITIONS = {
    "integrated",
    "preserved",
    "validly-superseded",
    "generated-reproducible",
    "retain",
}
POSTURES = {"safe-cleanup", "coordinated-reconciliation", "retain", "replan", "resume-current-run"}
REQUIRED_CASES = {
    "clean-redundant-worktree",
    "unique-committed-work",
    "dirty-and-local-bytes",
    "detached-and-stashed-work",
    "moved-ref-after-plan",
    "merge-ready-accepted-pr",
    "superseded-pr",
    "open-unaccepted-pr",
    "provider-unavailable-pr",
    "active-overlapping-writer",
    "conflict-drops-functionality",
    "interrupted-cleanup",
    "successful-retirement",
    "restart-and-dormancy",
    "unknown-malformed-sensitive-state",
}
REQUIRED_SOURCE_STATES = {
    "staged",
    "unstaged",
    "untracked",
    "ignored",
    "detached",
    "stash",
    "ref-moved",
    "merge-ready-pr",
    "superseded-pr",
    "open-pr",
    "provider-unavailable-pr",
    "overlapping-writer",
    "unaffected-writer",
    "missing-route",
    "partial-effects",
    "eligible-lane",
    "dependency-dormant-lane",
    "unknown",
    "malformed",
    "sensitive",
}


class ReconciliationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = CONTRACT.read_text(encoding="utf-8")
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_contract_names_no_loss_and_authority_boundaries(self) -> None:
        required = {
            "## Artifact inventory and disposition",
            "## Byte and functionality preservation",
            "## Owner map",
            "## Phase and gate contract",
            "Unknown bytes are",
            "supervisor repository writes",
            "Record-specific required fields and dependencies",
            "Inventory and source-snapshot production",
            "Deletion eligibility",
            "Successor plan after invalidation",
            "Restart or dormant-path selection",
        }
        for marker in required:
            self.assertIn(marker, self.contract)

    def test_fixture_is_complete_unique_and_content_minimized(self) -> None:
        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual(set(self.fixture["dispositions"]), DISPOSITIONS)
        self.assertEqual(self.fixture["content_policy"], "synthetic-content-minimized")
        cases = self.fixture["cases"]
        ids = [case["case_id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), REQUIRED_CASES)
        required_fields = {
            "case_id",
            "expected_posture",
            "forbidden_claims",
            "proposed_disposition",
            "required_proof",
            "source_state",
        }
        for case in cases:
            self.assertEqual(set(case), required_fields)
            self.assertIn(case["proposed_disposition"], DISPOSITIONS)
            self.assertIn(case["expected_posture"], POSTURES)
            self.assertTrue(case["required_proof"])
            self.assertTrue(case["forbidden_claims"])
            self.assertEqual(len(case["required_proof"]), len(set(case["required_proof"])))
            self.assertEqual(len(case["source_state"]), len(set(case["source_state"])))

        observed_states = {state for case in cases for state in case["source_state"]}
        self.assertTrue(REQUIRED_SOURCE_STATES <= observed_states)

        raw = FIXTURE.read_text(encoding="utf-8")
        protected_patterns = (
            r"/Users/",
            r"019f[0-9a-f-]{20,}",
            r"PRIVATE PROJECT CONTENT",
            r"BEGIN [A-Z ]*PRIVATE KEY",
            r"(?i)(password|api[_-]?key|access[_-]?token)\s*[:=]",
        )
        for pattern in protected_patterns:
            self.assertIsNone(re.search(pattern, raw))

    def test_negative_cases_preserve_unknown_and_functionality(self) -> None:
        by_id = {case["case_id"]: case for case in self.fixture["cases"]}
        self.assertEqual(by_id["unique-committed-work"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["dirty-and-local-bytes"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["moved-ref-after-plan"]["expected_posture"], "replan")
        dirty = by_id["dirty-and-local-bytes"]
        self.assertEqual(
            set(dirty["source_state"]),
            {"staged", "unstaged", "untracked", "ignored"},
        )
        overlap = by_id["active-overlapping-writer"]
        self.assertEqual(overlap["expected_posture"], "coordinated-reconciliation")
        self.assertEqual(overlap["proposed_disposition"], "retain")
        self.assertTrue(
            {"owner-checkpoint", "owner-inactive", "quiescence-gate"}
            <= set(overlap["required_proof"])
        )
        conflict = by_id["conflict-drops-functionality"]
        self.assertEqual(conflict["proposed_disposition"], "retain")
        self.assertIn("distinct-semantic-review", conflict["required_proof"])

        retain_states = {
            "unknown",
            "malformed",
            "sensitive",
            "unaccepted",
            "provider-unavailable-pr",
        }
        for case in self.fixture["cases"]:
            if retain_states & set(case["source_state"]):
                self.assertEqual(case["proposed_disposition"], "retain", case["case_id"])

        self.assertEqual(by_id["open-unaccepted-pr"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["provider-unavailable-pr"]["expected_posture"], "retain")
        unknown = by_id["unknown-malformed-sensitive-state"]
        self.assertIn("caller-selected-task-acceptance", unknown["forbidden_claims"])


if __name__ == "__main__":
    unittest.main()
