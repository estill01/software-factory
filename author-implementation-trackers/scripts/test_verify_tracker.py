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
    sections = """### Objective
Outcome.

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
    return f"""# Tracker

- Tracker sequence: Blocks 0–1

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | First | — | `not-started` |
| 1 | Second | {block_one_dependency} | `{block_one_status}` |

## Block 0 — First

Status: `not-started`

{sections}

## Block 1 — Second

Status: `not-started`

{sections}
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
        result = self.verify_text(text, profile="core")
        self.assertEqual([], result["errors"])


if __name__ == "__main__":
    unittest.main()
