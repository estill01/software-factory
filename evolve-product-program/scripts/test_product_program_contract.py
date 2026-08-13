#!/usr/bin/env python3
"""Static and mechanical checks for the Block 0 evolution contract."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "evolve-product-program"
CONTRACT = (SKILL_ROOT / "references" / "product-program-evolution-contract.md").read_text(encoding="utf-8")
CONTRACT_FIXTURE = json.loads((SKILL_ROOT / "fixtures" / "product_program_contract_v1.json").read_text(encoding="utf-8"))
SOURCE_MAP = json.loads((SKILL_ROOT / "fixtures" / "product_program_source_map_v1.json").read_text(encoding="utf-8"))


class ProductProgramContractTests(unittest.TestCase):
    def test_shared_ladder_has_profile_specific_adoption(self) -> None:
        self.assertIn("software-factory-capability", CONTRACT_FIXTURE["target_profiles"])
        self.assertIn("target-product-program", CONTRACT_FIXTURE["target_profiles"])
        self.assertNotEqual(*CONTRACT_FIXTURE["target_profiles"].values())
        self.assertIn("without sharing adoption authority", CONTRACT)

    def test_every_transition_has_a_stop(self) -> None:
        transitions = CONTRACT_FIXTURE["state_transitions"]
        self.assertEqual(6, len(transitions))
        for transition in transitions:
            self.assertEqual({"from", "stop", "to"}, set(transition))
            self.assertTrue(transition["stop"])

    def test_dispositions_have_one_fixed_placement(self) -> None:
        expected = {
            "continue-program-unchanged",
            "remediate-current-block",
            "revise-current-program",
            "start-successor-program",
            "start-program-portfolio",
            "run-bounded-experiment",
            "safe-defer-open-fact-or-authority",
            "request-material-goal-authority",
        }
        self.assertEqual(expected, set(CONTRACT_FIXTURE["disposition_placements"]))
        self.assertEqual(
            len(expected), len(set(CONTRACT_FIXTURE["disposition_placements"].values()))
        )

    def test_all_derived_artifacts_are_nonauthorizing(self) -> None:
        for forbidden in ("tracker", "source", "supervision", "release", "automation", "external-effect"):
            self.assertIn(forbidden, CONTRACT_FIXTURE["non_authorizing_writes"])
            self.assertIn(forbidden.replace("-", " "), CONTRACT.lower())
        self.assertIn("It is never an authorization", CONTRACT)

    def test_role_separation_and_noop_are_explicit(self) -> None:
        roles = set(CONTRACT_FIXTURE["roles"])
        self.assertTrue({"reflection-generator", "portfolio-selector", "implementation-owner", "evaluator"} <= roles)
        self.assertIn("without cognition, candidates, selection", CONTRACT)
        self.assertIn("Generator, selector, implementer, and evaluator identities are distinct", CONTRACT)

    def test_source_map_is_exact_and_current(self) -> None:
        for source in SOURCE_MAP["sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            self.assertFalse(path.is_symlink(), source["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])

    def test_contract_rejects_duplicate_owner_surfaces(self) -> None:
        for phrase in (
            "does not create a tracker writer",
            "supervision ledger",
            "release owner",
            "scheduler",
            "or permission\nsystem",
            "Parallel plans remain\nderived",
        ):
            self.assertIn(phrase, CONTRACT)


if __name__ == "__main__":
    unittest.main()
