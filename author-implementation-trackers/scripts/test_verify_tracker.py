#!/usr/bin/env python3
"""Focused tests for verify_tracker.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_tracker.py")
SKILL = SCRIPT.parents[1] / "SKILL.md"
TEMPLATE = SCRIPT.parents[1] / "assets" / "implementation-tracker-template.md"
BLOCK_CONTRACT = SCRIPT.parents[1] / "references" / "block-contract.md"
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

    def test_duplicate_capability_frame_fails(self) -> None:
        text = tracker()
        start = text.index("### Target-product capability frame")
        end = text.index("## Status and required order")
        frame = text[start:end]
        result = self.verify_text(text[:end] + frame + text[end:])
        self.assertTrue(any("expected one" in error for error in result["errors"]))

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
        ).replace(
            "- Posture: `consequential`.",
            "- Posture: `not-applicable`.\n"
            "- Routine or not-applicable justification: This Block changes no product capability.",
            1,
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

    def test_duplicate_capability_delta_fails(self) -> None:
        text = tracker()
        block_one = text.index("## Block 1")
        first_delta = text.index("### Target-product capability delta")
        delta_end = text.index("### Inputs and dependencies", first_delta)
        duplicate = text[first_delta:delta_end]
        result = self.verify_text(text[:block_one] + duplicate + text[block_one:])
        self.assertTrue(any("capability delta" in error and "expected one" in error for error in result["errors"]))

    def test_capability_delta_must_be_nested_below_block_heading(self) -> None:
        text = tracker().replace("### Target-product capability delta", "## Target-product capability delta", 1)
        result = self.verify_text(text)
        self.assertTrue(any("Block 0 is missing section 'target-product capability delta'" in error for error in result["errors"]))

    def test_tilde_fenced_structural_decoys_are_ignored(self) -> None:
        visible = list(
            MODULE.iter_unfenced_lines(
                [
                    "~~~~markdown",
                    "### Target-product capability frame",
                    "Status: `accepted`",
                    "| Block | Scope | Depends on | Status |",
                    "- Tracker sequence: Blocks 0–9",
                    "~~~~",
                    "visible",
                ]
            )
        )
        self.assertEqual([(6, "visible")], visible)

    def test_tilde_fenced_capability_frame_decoy_fails(self) -> None:
        text = tracker()
        start = text.index("### Target-product capability frame")
        end = text.index("## Status and required order")
        frame = text[start:end]
        decoy = "~~~markdown\n" + frame + "~~~\n\n"
        result = self.verify_text(text[:start] + decoy + text[end:])
        self.assertTrue(any("missing section 'target-product capability frame'" in error for error in result["errors"]))

    def test_tilde_fenced_capability_delta_decoy_fails(self) -> None:
        text = tracker().replace(
            "### Target-product capability delta",
            "~~~markdown\n### Target-product capability delta\n~~~\n\n### Notes",
            1,
        )
        result = self.verify_text(text)
        self.assertTrue(any("Block 0 is missing section 'target-product capability delta'" in error for error in result["errors"]))

    def test_indented_code_fields_do_not_satisfy_frame(self) -> None:
        text = tracker()
        start = text.index("### Target-product capability frame")
        end = text.index("## Status and required order")
        frame = text[start:end].replace("\n- ", "\n    - ")
        result = self.verify_text(text[:start] + frame + text[end:])
        self.assertTrue(any("capability frame is missing field" in error for error in result["errors"]))

    def test_placeholder_prefixes_are_rejected(self) -> None:
        cases = (
            (
                "- Direct product sources: `docs/product.md` at revision `abc123`.",
                "- Direct product sources: TODO: inspect product sources.",
            ),
            (
                "- Intended capability gain: Users can complete the bounded workflow.",
                "- Intended capability gain: TBD later.",
            ),
            (
                "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.",
                "- Tradeoff and source evidence: Evidence pending after implementation.",
            ),
            (
                "- Routine or not-applicable justification: Documentation-only cleanup changes no product behavior or owner.",
                "- Routine or not-applicable justification: N/A",
            ),
        )
        for original, replacement in cases:
            with self.subTest(replacement=replacement):
                result = self.verify_text(tracker().replace(original, replacement, 1))
                self.assertTrue(result["errors"])

    def test_deferred_source_evidence_is_rejected(self) -> None:
        cases = (
            (
                "- Direct product sources: `docs/product.md` at revision `abc123`.",
                "- Direct product sources: Source evidence will be added later.",
            ),
            (
                "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.",
                "- Tradeoff and source evidence: Evidence will be supplied after implementation.",
            ),
            (
                "- Direct product sources: `docs/product.md` at revision `abc123`.",
                "- Direct product sources: Source evidence is deferred until implementation.",
            ),
            (
                "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.",
                "- Tradeoff and source evidence: Source evidence has not yet been collected.",
            ),
        )
        for original, replacement in cases:
            with self.subTest(replacement=replacement):
                result = self.verify_text(tracker().replace(original, replacement, 1))
                self.assertTrue(result["errors"])

    def test_angle_brackets_in_concrete_prose_are_accepted(self) -> None:
        text = tracker().replace(
            "- Intended capability gain: Users can complete the bounded workflow.",
            "- Intended capability gain: A typed `Result<T>` keeps failures below `<1%>` for the `<button>` path.",
        )
        result = self.verify_text(text)
        self.assertEqual([], result["errors"])

    def test_routine_tracker_cannot_contain_consequential_block(self) -> None:
        text = tracker().replace("- Applicability: `consequential`.", "- Applicability: `routine`.")
        result = self.verify_text(text)
        self.assertTrue(any("contradicts tracker applicability 'routine'" in error for error in result["errors"]))

    def test_consequential_tracker_requires_a_consequential_block(self) -> None:
        text = tracker().replace(
            "- Posture: `consequential`.\n"
            "- Intended capability gain: Users can complete the bounded workflow.\n"
            "- Potential capability loss or regression: Existing deterministic behavior could regress; preserve it.\n"
            "- Protected-capability effect: Preserve the canonical writer boundary.\n"
            "- Architecture and operating-model effect: Extend the existing owner without adding a service.\n"
            "- Tradeoff and source evidence: Prefer the direct owner identified in `docs/product.md` over a generalized platform.\n",
            "- Posture: `routine`.\n"
            "- Routine or not-applicable justification: This Block changes no product capability.\n",
            1,
        )
        result = self.verify_text(text)
        self.assertTrue(any("requires at least one consequential Block" in error for error in result["errors"]))

    def test_stray_capability_headings_outside_owned_scope_fail(self) -> None:
        cases = (
            tracker().replace("## Block 0 — First", "### Target-product capability delta\n\n## Block 0 — First", 1),
            tracker().replace("### Objective", "### Target-product capability frame\n\n### Objective", 1),
            tracker().replace("## Block 1 — Second", "## Target-product capability delta\n\n## Block 1 — Second", 1),
        )
        for text in cases:
            with self.subTest():
                result = self.verify_text(text)
                self.assertTrue(any("total sections named" in error for error in result["errors"]))

    def test_duplicate_detection_consumes_input_once(self) -> None:
        class SinglePassNumbers:
            def __init__(self) -> None:
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                if self.iterations > 1:
                    raise AssertionError("duplicate detection rescanned its input")
                yield from (0, 1, 1, 2, 2, 2)

        numbers = SinglePassNumbers()
        self.assertEqual([1, 2], MODULE.duplicate_numbers(numbers))
        self.assertEqual(1, numbers.iterations)

    def test_sparse_large_block_id_is_bounded_by_document_length(self) -> None:
        text = tracker().replace("## Block 1 — Second", "## Block 1000000000 — Second")
        result = self.verify_text(text)
        self.assertTrue(any("not continuous" in error for error in result["errors"]))

    def test_underreach_rejection_is_part_of_the_authoring_contract(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        template = TEMPLATE.read_text(encoding="utf-8")
        contract = BLOCK_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("literal button, endpoint, command, or file is not the whole", skill)
        self.assertIn("not merely literal feature wording", template)
        self.assertIn("Underreach occurs when literal feature wording", contract)

    def test_speculative_overarchitecture_rejection_is_part_of_the_authoring_contract(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        template = TEMPLATE.read_text(encoding="utf-8")
        contract = BLOCK_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("do not invent product ethos, platform doctrine", skill)
        self.assertIn("do not infer\n  a generalized platform", template)
        self.assertIn("Speculative over-architecture occurs", contract)


if __name__ == "__main__":
    unittest.main()
