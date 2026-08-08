#!/usr/bin/env python3
"""Static cross-skill contract tests for bounded product-capability review."""

from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENT_SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
REVIEW = (SKILL_ROOT / "references" / "product-capability-review.md").read_text(encoding="utf-8")
AUTHOR_TEMPLATE = (
    SKILL_ROOT.parent / "author-implementation-trackers" / "assets" / "implementation-tracker-template.md"
).read_text(encoding="utf-8")


class ProductCapabilityContractTests(unittest.TestCase):
    def test_routes_only_consequential_or_concrete_drift(self) -> None:
        self.assertIn("run its bounded review only when the Block is `consequential`", IMPLEMENT_SKILL)
        self.assertIn("`routine` or `not-applicable` Block with no such trigger", IMPLEMENT_SKILL)
        self.assertIn("Product-capability review: not triggered", REVIEW)

    def test_compares_three_levels_without_automatic_generality(self) -> None:
        self.assertIn("Smallest local path", REVIEW)
        self.assertIn("Bounded-general path", REVIEW)
        self.assertIn("Available architectural owner", REVIEW)
        self.assertIn("Select the lowest-complexity eligible level", REVIEW)
        self.assertIn("never the most\ngeneral architecture by default", IMPLEMENT_SKILL)

    def test_checks_both_underreach_and_speculative_generalization(self) -> None:
        self.assertIn("Lower-power substitution", REVIEW)
        self.assertIn("Composability", REVIEW)
        self.assertIn("Speculative generalization", REVIEW)
        self.assertIn("Product framing never overrides either", REVIEW)

    def test_completion_evidence_binds_capability_and_tradeoffs(self) -> None:
        for label in (
            "Capability added or preserved",
            "Paths compared",
            "Selected level and owner",
            "Protected-capability result",
            "Rejected alternatives",
            "Tradeoffs and uncertainty",
            "Frozen-candidate proof",
        ):
            self.assertIn(label, REVIEW)

    def test_author_and_executor_share_capability_contract_names(self) -> None:
        for label in (
            "Target-product capability frame",
            "Target-product capability delta",
            "Protected capabilities",
            "Architecture strategy",
            "Tradeoffs",
            "Uncertainty",
        ):
            self.assertIn(label, AUTHOR_TEMPLATE)
            self.assertIn(label.lower(), (IMPLEMENT_SKILL + REVIEW).lower())


if __name__ == "__main__":
    unittest.main()
