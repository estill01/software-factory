#!/usr/bin/env python3
"""Mechanical checks for the repository reconciliation contract and fixtures."""

from __future__ import annotations

import json
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
        self.assertGreaterEqual(len(cases), 11)
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
            self.assertTrue(case["required_proof"])
            self.assertTrue(case["forbidden_claims"])

    def test_negative_cases_preserve_unknown_and_functionality(self) -> None:
        by_id = {case["case_id"]: case for case in self.fixture["cases"]}
        self.assertEqual(by_id["unique-committed-work"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["dirty-and-local-bytes"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["moved-ref-after-plan"]["expected_posture"], "replan")
        conflict = by_id["conflict-drops-functionality"]
        self.assertEqual(conflict["proposed_disposition"], "retain")
        self.assertIn("distinct-semantic-review", conflict["required_proof"])


if __name__ == "__main__":
    unittest.main()
