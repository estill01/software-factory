#!/usr/bin/env python3
"""Focused tests for verify_tracker.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_tracker.py")
SPEC = importlib.util.spec_from_file_location("verify_tracker", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def tracker(block_one_dependency: str = "0", block_one_status: str = "not-started") -> str:
    consequential_sections = """### Objective
Outcome.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: Users can complete the bounded workflow.
- Potential capability loss or regression: Existing deterministic behavior could regress; preserve it.
- Protected-capability effect: Preserve the canonical writer boundary.
- Architecture and operating-model effect: Extend the existing owner without adding a service.
- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.

### Inputs and dependencies
Inputs.

### Required work
Work.

### Scope and non-goals
One owner; adjacent work excluded.

### Deliverables and recorded state
Output.

### Resource and economy contract
Bounded.

### QA and independent review
Review.

### Acceptance
Accepted.

### Negative tests
Reject corruption.

### Completion evidence
Pending.

### Stop
Stop before the next Block.
"""
    routine_sections = consequential_sections.replace(
        "- Posture: `consequential`.\n"
        "- Intended capability gain: Users can complete the bounded workflow.\n"
        "- Potential capability loss or regression: Existing deterministic behavior could regress; preserve it.\n"
        "- Protected-capability effect: Preserve the canonical writer boundary.\n"
        "- Architecture and operating-model effect: Extend the existing owner without adding a service.\n"
        "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.\n",
        "- Posture: `routine`.\n"
        "- Routine or not-applicable justification: Documentation-only cleanup changes no product behavior or owner.\n",
    )
    return f"""# Tracker

- Tracker sequence: Blocks 0–1

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: The work changes user-visible workflow behavior.
- Direct product sources: `docs/product.md` at revision `abc123`.
- Product thesis and intended effect: Keep the bounded workflow reliable for its users.
- Protected capabilities: Deterministic output and one canonical writer.
- Architecture strategy: Extend the existing owner.
- Requested capability: Complete the bounded workflow.
- Proportionality: Use the narrowest source-supported change.
- Tradeoffs: Preserve determinism instead of adding speculative flexibility.
- Uncertainty: Repository evidence does not establish future remote use.

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | First | — | `not-started` |
| 1 | Second | {block_one_dependency} | `{block_one_status}` |

## Block 0 — First

Status: `not-started`

{consequential_sections}

## Block 1 — Second

Status: `not-started`

{routine_sections}
"""


class VerifyTrackerTests(unittest.TestCase):
    def verify_text(self, text: str, profile: str = "full") -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracker.md"
            path.write_text(text, encoding="utf-8")
            return MODULE.verify(path, profile)

    def test_valid_full_tracker(self) -> None:
        result = self.verify_text(tracker())
        self.assertEqual([], result["errors"])

    def test_duplicate_block_heading_fails(self) -> None:
        result = self.verify_text(tracker() + "\n## Block 1 — Duplicate\n")
        self.assertTrue(any("duplicate Block" in error for error in result["errors"]))

    def test_gap_or_reordering_fails(self) -> None:
        result = self.verify_text(tracker().replace("## Block 1", "## Block 2"))
        self.assertTrue(any("not continuous" in error for error in result["errors"]))

    def test_nonpreceding_dependency_fails(self) -> None:
        result = self.verify_text(tracker(block_one_dependency="1"))
        self.assertTrue(any("non-preceding dependency" in error for error in result["errors"]))

    def test_status_mismatch_fails(self) -> None:
        result = self.verify_text(tracker(block_one_status="in-progress"))
        self.assertTrue(any("does not match block status" in error for error in result["errors"]))

    def test_missing_full_section_fails(self) -> None:
        text = tracker().replace("### Negative tests", "### Failure examples", 1)
        result = self.verify_text(text)
        self.assertTrue(any("negative tests" in error for error in result["errors"]))

    def test_missing_scope_boundary_fails(self) -> None:
        text = tracker().replace("### Scope and non-goals", "### Notes", 1)
        result = self.verify_text(text)
        self.assertTrue(any("scope and non-goals" in error for error in result["errors"]))

    def test_core_profile_accepts_intentional_minimal_contract(self) -> None:
        text = tracker().replace("### Inputs and dependencies", "### Inputs", 1)
        start = text.index("### Target-product capability frame")
        end = text.index("## Status and required order")
        text = text[:start] + text[end:]
        text = text.replace("### Target-product capability delta", "### Notes")
        result = self.verify_text(text, profile="core")
        self.assertEqual([], result["errors"])

    def test_full_profile_requires_target_product_frame(self) -> None:
        text = tracker()
        start = text.index("### Target-product capability frame")
        end = text.index("## Status and required order")
        result = self.verify_text(text[:start] + text[end:])
        self.assertTrue(any("missing section 'target-product capability frame'" in error for error in result["errors"]))

    def test_consequential_frame_requires_direct_product_sources(self) -> None:
        text = tracker().replace(
            "- Direct product sources: `docs/product.md` at revision `abc123`.",
            "- Direct product sources: Not applicable: no source was inspected.",
        )
        result = self.verify_text(text)
        self.assertTrue(any("requires direct product sources" in error for error in result["errors"]))

    def test_justified_not_applicable_frame_is_accepted(self) -> None:
        text = tracker().replace(
            "- Applicability: `consequential`.",
            "- Applicability: `not-applicable`.",
        ).replace(
            "- Applicability rationale: The work changes user-visible workflow behavior.",
            "- Applicability rationale: This inherited-record cleanup changes no product capability.",
        ).replace(
            "- Direct product sources: `docs/product.md` at revision `abc123`.",
            "- Direct product sources: Not applicable: no product doctrine is asserted.",
        )
        result = self.verify_text(text)
        self.assertEqual([], result["errors"])

    def test_consequential_delta_requires_losses_and_tradeoffs(self) -> None:
        text = tracker().replace(
            "- Potential capability loss or regression: Existing deterministic behavior could regress; preserve it.\n",
            "",
            1,
        ).replace(
            "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.\n",
            "",
            1,
        )
        result = self.verify_text(text)
        self.assertTrue(any("potential capability loss or regression" in error for error in result["errors"]))
        self.assertTrue(any("tradeoff and source evidence" in error for error in result["errors"]))

    def test_routine_delta_requires_justification(self) -> None:
        text = tracker().replace(
            "- Routine or not-applicable justification: Documentation-only cleanup changes no product behavior or owner.\n",
            "",
        )
        result = self.verify_text(text)
        self.assertTrue(any("routine or not-applicable justification" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
