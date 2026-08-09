#!/usr/bin/env python3
"""Behavior and static contracts for the bounded inline-correction loop."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
CASES = json.loads(
    (SKILL_ROOT / "fixtures" / "inline_correction_v1.json").read_text(
        encoding="utf-8"
    )
)["cases"]


INLINE_TRIGGERS = {
    "wrong-owner",
    "lower-power-shortcut",
    "unnecessary-abstraction",
    "blind-retry",
    "invalid-validation",
    "protected-capability-regression",
}

INLINE_PATHS = {
    "wrong-owner": "architectural-owner",
    "lower-power-shortcut": "bounded-general",
    "unnecessary-abstraction": "local",
    "blind-retry": "architectural-owner",
    "invalid-validation": "local",
    "protected-capability-regression": "bounded-general",
}


def classify(case: dict[str, object]) -> str:
    if case["block_contract_changed"]:
        return "amend-structure"
    if case["implementation_evidence_required"]:
        return "compare-candidate"
    if case["trigger"] in INLINE_TRIGGERS:
        return "correct-inline"
    return "continue-unchanged"


def selected_path(case: dict[str, object]) -> str | None:
    disposition = classify(case)
    if disposition == "correct-inline":
        return INLINE_PATHS[str(case["trigger"])]
    if disposition == "continue-unchanged":
        return "incumbent"
    return None


class InlineCorrectionContractTests(unittest.TestCase):
    def test_fixture_is_closed_and_routes_each_required_case(self) -> None:
        self.assertEqual(len(CASES), 10)
        self.assertEqual(len({case["case_id"] for case in CASES}), len(CASES))
        for case in CASES:
            self.assertEqual(
                set(case),
                {
                    "case_id",
                    "trigger",
                    "block_contract_changed",
                    "implementation_evidence_required",
                    "expected_disposition",
                    "expected_selected_path",
                    "expected_continue",
                },
            )
            self.assertEqual(classify(case), case["expected_disposition"])
            self.assertEqual(selected_path(case), case["expected_selected_path"])
            self.assertIs(case["expected_continue"], True)

    def test_unchanged_path_returns_to_work_not_to_user(self) -> None:
        self.assertIn("zero model, reviewer, candidate, or authoring work", SKILL)
        self.assertIn("Never convert\n   `continue-unchanged` into a user-facing return", SKILL)
        self.assertIn("skipped\n   remainder of the requested Block range", SKILL)
        for case_id in ("justified-incumbent", "unchanged-repeat"):
            case = next(case for case in CASES if case["case_id"] == case_id)
            self.assertEqual(classify(case), "continue-unchanged")

    def test_inline_preserves_contract_and_valid_work(self) -> None:
        for phrase in (
            "Stop only the causal bad process or write owner",
            "Preserve\n   coherent code, tests, artifacts, commits, accepted evidence",
            "original objective, dependencies,\n   acceptance, and Stop remain unchanged",
            "smallest focused\n   proof first",
            "immediately continue its remaining dependency-safe work",
        ):
            self.assertIn(phrase, SKILL)

    def test_comparison_selects_complete_lowest_complexity_owner(self) -> None:
        self.assertIn("smallest local correction", SKILL)
        self.assertIn("smallest\n   bounded-general path", SKILL)
        self.assertIn("available architectural owner", SKILL)
        self.assertIn("lowest-complexity path that\n   supplies the complete", SKILL)
        self.assertIn("unsupported generalized layer lost", SKILL)

    def test_inline_does_not_invent_a_meta_workflow(self) -> None:
        for prohibited in (
            "No\n   tracker edit, authoring thread, separate supervision lifecycle, human prompt",
            "do not create a correction registry or second ledger",
            "not a new task, authoring pass, supervisor lifecycle, or approval gate",
        ):
            self.assertIn(prohibited, SKILL)

    def test_escalation_is_exact_and_difficulty_is_not_enough(self) -> None:
        self.assertIn("route to `compare-candidate`", SKILL)
        self.assertIn("package `amend-structure`", SKILL)
        self.assertIn("merely\n   because the correction is difficult", SKILL)
        candidate = next(case for case in CASES if case["case_id"] == "requires-candidate")
        structural = next(
            case for case in CASES
            if case["case_id"] == "requires-structural-amendment"
        )
        self.assertEqual(classify(candidate), "compare-candidate")
        self.assertEqual(classify(structural), "amend-structure")

    def test_equivalent_fingerprint_is_not_reconsidered(self) -> None:
        self.assertIn("Equivalent fingerprints are deduplicated", SKILL)
        self.assertIn("without new concrete adjudicating evidence", SKILL)
        self.assertIn("at most one named widening fact", SKILL)


if __name__ == "__main__":
    unittest.main()
