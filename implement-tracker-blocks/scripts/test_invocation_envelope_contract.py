#!/usr/bin/env python3
"""Static contract tests for repository-owned invocation envelopes."""

from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENT_SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
NORMALIZED_SKILL = " ".join(IMPLEMENT_SKILL.split())


class InvocationEnvelopeContractTests(unittest.TestCase):
    def test_resolves_the_complete_maintained_command_chain_before_execution(self) -> None:
        for requirement in (
            "exact maintained runner command chain",
            "every launcher and executable actually invoked",
            "repository-derived working directory",
            "project or workspace binding",
            "configured runtime",
            "import or module binding",
            "intentional Git environment",
            "before first execution",
        ):
            self.assertIn(requirement, NORMALIZED_SKILL)

    def test_rejects_proxy_checks_and_guessed_workspace_roots(self) -> None:
        self.assertIn("A proxy check is not an envelope check", IMPLEMENT_SKILL)
        self.assertIn("proving Vitest while omitting the `npm`", NORMALIZED_SKILL)
        self.assertIn("guessing a workspace root", NORMALIZED_SKILL)
        self.assertIn("deriving it from repository ownership", NORMALIZED_SKILL)

    def test_reuses_the_corrected_envelope_and_only_invalidated_proof(self) -> None:
        self.assertIn("complete corrected command chain and envelope", NORMALIZED_SKILL)
        self.assertIn("exact audit handoff", NORMALIZED_SKILL)
        self.assertIn("next applicable first invocation", NORMALIZED_SKILL)
        self.assertIn("rerun only proof invalidated by the correction", NORMALIZED_SKILL)

    def test_pre_final_reconciliation_survives_unavailable_supervision(self) -> None:
        for requirement in (
            "Immediately before any final response or terminal posture",
            "exact direct requested Block range and current tracker",
            "current accepted Blocks, remaining requested Blocks",
            "dependency-safe frontier, required producer transitions",
            "safe coordination frontier",
            "missing or unavailable optional supervision binding, helper, or gate",
            "local evidence-bound reconciliation",
            "final return is forbidden: continue automatically",
            "do not ask the user to press Resume",
        ):
            self.assertIn(requirement, NORMALIZED_SKILL)

    def test_pre_final_reconciliation_does_not_invent_or_overlap_authority(self) -> None:
        for prohibition in (
            "never fabricates supervision authority",
            "creates a parallel ledger",
            "narrows the exact direct scope",
            "authorizes overlapping producer writes",
            "single-writer ownership remains controlling",
        ):
            self.assertIn(prohibition, NORMALIZED_SKILL)


if __name__ == "__main__":
    unittest.main()
