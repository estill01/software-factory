#!/usr/bin/env python3
"""Focused tests for Block 2 divergent product-program reflection."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("product_program_reflection.py")
FIXTURES = SCRIPT.parents[1] / "fixtures"
SPEC = importlib.util.spec_from_file_location("product_program_reflection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def role_fields() -> dict[str, str]:
    return {
        "author_owner": "tracker-author",
        "evaluation_owner": "independent-evaluator",
        "implementation_owner": "implementation-owner",
        "selector_id": "portfolio-selector",
    }


def candidate(candidate_id: str, candidate_type: str, *, gap: bool = True) -> dict[str, object]:
    no_change = candidate_type == "continue-unchanged"
    return {
        "affected_capability_ids": ["cold-start"],
        "affected_user_ids": ["operator"],
        "architecture_evidence_ids": [] if no_change else ["inventory-1"],
        "architecture_level": "no-change" if no_change else "local",
        "architecture_rationale": "Preserve the current bounded owner." if no_change else "Use the current product owner.",
        **role_fields(),
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "counterexample_evidence_ids": [],
        "counterexample_posture": "searched-none-found",
        "counterexample_search": "Searched current outcomes and contrary observations.",
        "desired_effect": "Continue current work without a prospective change." if no_change else "Improve the evidenced operator outcome.",
        "evidence_ids": ["inventory-1"],
        "falsifiable_outcome": "No new regression appears at the next exact checkpoint." if no_change else "The next exact outcome records the intended improvement.",
        "gap_ids": ["gap-1"] if gap and not no_change else [],
        "generator_posture": "divergent-only",
        "protected_behavior": ["Preserve direct mission and current requested work."],
        "selection_claim": "none",
        "smallest_sufficient_change": "No change." if no_change else "Change only the bounded behavior named by the gap.",
        "uncertainty": "Later outcome evidence may change this posture.",
    }


def base_submission(packet: dict[str, object]) -> dict[str, object]:
    return {
        "candidate_ceiling": 6,
        "candidates": [
            candidate("candidate-feature", "feature"),
            candidate("candidate-no-change", "continue-unchanged"),
            candidate("candidate-simplify", "simplification"),
        ],
        "capability_gaps": [
            {
                "category_search": [
                    {
                        "candidate_type": "architecture",
                        "disposition": "searched-no-support",
                        "evidence_ids": [],
                        "rationale": "No evidence requires a broader architecture.",
                    },
                    {
                        "candidate_type": "feature",
                        "disposition": "supported",
                        "evidence_ids": ["inventory-1"],
                        "rationale": "Current product evidence supports a bounded feature change.",
                    },
                    {
                        "candidate_type": "simplification",
                        "disposition": "supported",
                        "evidence_ids": ["outcome-1"],
                        "rationale": "Outcome evidence supports testing a simpler path.",
                    },
                ],
                "desired_capability": "Produce the operator outcome with less avoidable friction.",
                "evidence_ids": ["inventory-1", "outcome-1"],
                "gap_id": "gap-1",
                "lesson_ids": ["lesson-contrary", "lesson-current"],
                "meta_pattern_ids": ["pattern-bounded-change"],
                "mission_boundary": "Improve the current product without displacing the requested range.",
                "observation_ids": ["observation-contrary", "observation-current"],
                "statement": "The current behavior leaves an evidenced operator gap.",
                "uncertainty": "The smallest effective intervention still requires comparison.",
            }
        ],
        "counterexample_widening_used": True,
        "generation_pass_count": 1,
        "generator_id": "reflection-generator",
        "kind": "product-program-reflection-submission",
        "lessons": [
            {
                "applicability": "Current bounded operator workflow.",
                "confidence": "moderate",
                "counterexample_observation_ids": ["observation-contrary"],
                "counterexample_posture": "observed",
                "counterexample_search": "Compared the current outcome with the contrary incident.",
                "lesson_id": "lesson-current",
                "observation_ids": ["observation-current"],
                "statement": "A bounded change may improve the current outcome.",
                "uncertainty": "The causal mechanism needs outcome evaluation.",
            },
            {
                "applicability": "Only the current program and product evidence.",
                "confidence": "low",
                "counterexample_observation_ids": [],
                "counterexample_posture": "bounded-uncertainty",
                "counterexample_search": "Searched the retained decision and incident identities.",
                "lesson_id": "lesson-contrary",
                "observation_ids": ["observation-contrary", "observation-current"],
                "statement": "Contrary evidence narrows the safe architecture level.",
                "uncertainty": "A future outcome may defeat this lesson.",
            },
        ],
        "meta_patterns": [
            {
                "applicability": "This target product and current program.",
                "counterexample_lesson_ids": ["lesson-contrary"],
                "lesson_ids": ["lesson-contrary", "lesson-current"],
                "meta_pattern_id": "pattern-bounded-change",
                "statement": "Useful change requires both outcome support and bounded architecture.",
                "uncertainty": "Only one current program is represented.",
            }
        ],
        "observations": [
            {
                "evidence_ids": ["EVT-INCIDENT-1"],
                "observation_id": "observation-contrary",
                "summary": "A contrary incident narrows the safe change.",
                "valence": "contrary",
            },
            {
                "evidence_ids": ["inventory-1", "outcome-1"],
                "observation_id": "observation-current",
                "summary": "Current product evidence exposes an operator outcome gap.",
                "valence": "mixed",
            },
        ],
        "packet_id": packet["packet_id"],
        "packet_root": packet["artifact_root"],
        "schema_version": 1,
    }


def no_op_submission(packet: dict[str, object]) -> dict[str, object]:
    result = base_submission(packet)
    result["candidate_ceiling"] = 1
    result["candidates"] = [candidate("candidate-no-change", "continue-unchanged", gap=False)]
    result["capability_gaps"] = []
    result["counterexample_widening_used"] = False
    result["lessons"] = [
        {
            "applicability": "Current exact product/program checkpoint.",
            "confidence": "moderate",
            "counterexample_observation_ids": [],
            "counterexample_posture": "searched-none-found",
            "counterexample_search": "Searched retained current and contrary evidence IDs.",
            "lesson_id": "lesson-no-change",
            "observation_ids": ["observation-current"],
            "statement": "No supported prospective change exceeds current work.",
            "uncertainty": "A material later outcome can reopen reflection.",
        }
    ]
    result["meta_patterns"] = []
    result["observations"] = [
        {
            "evidence_ids": ["inventory-1", "outcome-1"],
            "observation_id": "observation-current",
            "summary": "Current evidence supports continuing the program unchanged.",
            "valence": "productive",
        }
    ]
    return result


def review_submission(reflection: dict[str, object], *, decision: str = "accepted") -> dict[str, object]:
    accepted = decision == "accepted"
    return {
        "category_dispositions_truthful": accepted,
        "decision": decision,
        "divergent_only": accepted,
        "finding_ids": [] if accepted else ["finding-selection-authority"],
        "kind": "product-program-reflection-review",
        "no_selection_or_adoption_claim": accepted,
        "reflection_root": reflection["artifact_root"],
        "reviewer_id": "independent-reflection-reviewer",
        "schema_version": 1,
    }


def accepted_reflection(
    packet: dict[str, object], submission: dict[str, object], inventory: dict[str, object]
) -> dict[str, object]:
    unreviewed = MODULE.build_reflection(packet, submission, inventory)
    return MODULE.apply_semantic_review(packet, unreviewed, inventory, review_submission(unreviewed))


class ProductProgramReflectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads((FIXTURES / "program_evidence_reflection_v1.json").read_text(encoding="utf-8"))
        cls.inventory = json.loads((FIXTURES / "product_program_inventory_v1.json").read_text(encoding="utf-8"))

    def test_positive_reflection_is_deterministic_divergent_and_nonauthorizing(self) -> None:
        submission = base_submission(self.packet)
        reflection = accepted_reflection(self.packet, submission, self.inventory)
        replay = accepted_reflection(self.packet, deepcopy(submission), self.inventory)
        self.assertEqual(MODULE.canonical(reflection), MODULE.canonical(replay))
        self.assertEqual({"feature", "simplification", "continue-unchanged"}, {item["candidate_type"] for item in reflection["candidates"]})
        self.assertFalse(reflection["authority"]["selection_allowed"])
        self.assertTrue(MODULE.verify_reflection(self.packet, reflection, self.inventory)["verified"])

    def test_committed_positive_contrary_and_noop_fixtures_verify(self) -> None:
        for name in (
            "program_reflection_positive_v1.json",
            "program_reflection_contrary_v1.json",
            "program_reflection_noop_v1.json",
        ):
            reflection = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
            self.assertTrue(MODULE.verify_reflection(self.packet, reflection, self.inventory)["verified"])

    def test_observed_contrary_evidence_remains_visible(self) -> None:
        reflection = accepted_reflection(self.packet, base_submission(self.packet), self.inventory)
        lesson = next(item for item in reflection["lessons"] if item["lesson_id"] == "lesson-current")
        self.assertEqual("observed", lesson["counterexample_posture"])
        self.assertEqual(["observation-contrary"], lesson["counterexample_observation_ids"])

    def test_noop_reflection_has_no_gap_or_change_candidate(self) -> None:
        reflection = accepted_reflection(self.packet, no_op_submission(self.packet), self.inventory)
        self.assertEqual([], reflection["capability_gaps"])
        self.assertEqual(["continue-unchanged"], [item["candidate_type"] for item in reflection["candidates"]])

    def test_search_can_support_one_change_without_a_novelty_quota(self) -> None:
        submission = base_submission(self.packet)
        submission["capability_gaps"][0]["category_search"][2]["disposition"] = "searched-no-support"
        submission["capability_gaps"][0]["category_search"][2]["evidence_ids"] = []
        submission["capability_gaps"][0]["category_search"][2]["rationale"] = "Current evidence does not justify simplification at this checkpoint."
        submission["candidates"] = [
            candidate("candidate-feature", "feature"),
            candidate("candidate-no-change", "continue-unchanged"),
        ]
        reflection = accepted_reflection(self.packet, submission, self.inventory)
        self.assertEqual(2, len(reflection["candidates"]))

    def test_single_unexplained_or_missing_no_change_candidate_rejects(self) -> None:
        single = base_submission(self.packet)
        single["candidates"] = [candidate("candidate-feature", "feature")]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "no-change comparison"):
            MODULE.build_reflection(self.packet, single, self.inventory)

        unmatched = base_submission(self.packet)
        unmatched["candidates"] = [
            candidate("candidate-feature", "feature"),
            candidate("candidate-no-change", "continue-unchanged"),
        ]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "emitted candidates differ"):
            MODULE.build_reflection(self.packet, unmatched, self.inventory)

    def test_invented_or_report_only_evidence_rejects(self) -> None:
        dangling = base_submission(self.packet)
        dangling["observations"][0]["evidence_ids"] = ["invented-doctrine"]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "dangling evidence"):
            MODULE.build_reflection(self.packet, dangling, self.inventory)

        report_only = base_submission(self.packet)
        report_only["observations"][0]["evidence_ids"] = ["report-1"]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "report hypotheses"):
            MODULE.build_reflection(self.packet, report_only, self.inventory)

        invented_user = base_submission(self.packet)
        invented_user["candidates"][0]["affected_user_ids"] = ["invented-user"]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "dangling evidence"):
            MODULE.build_reflection(self.packet, invented_user, self.inventory)

        missing_capability = base_submission(self.packet)
        missing_capability["candidates"][0]["affected_capability_ids"] = []
        with self.assertRaisesRegex(MODULE.ProductProgramError, "must not be empty"):
            MODULE.build_reflection(self.packet, missing_capability, self.inventory)

        incomplete_inventory = deepcopy(self.inventory)
        incomplete_inventory["tracker_states"] = incomplete_inventory["tracker_states"][:-1]
        forged_packet = deepcopy(self.packet)
        forged_packet["product_sources"][0]["sha256"] = MODULE.hashlib.sha256(
            MODULE.canonical(incomplete_inventory)
        ).hexdigest()
        forged_packet["product_sources"][0]["byte_length"] = len(MODULE.canonical(incomplete_inventory))
        with self.assertRaisesRegex(MODULE.ProductProgramError, "every required tracker state"):
            MODULE.normalize_inventory(forged_packet, incomplete_inventory)

        empty_behavior = deepcopy(self.inventory)
        empty_behavior["behaviors"] = []
        forged_packet["product_sources"][0]["sha256"] = MODULE.hashlib.sha256(
            MODULE.canonical(empty_behavior)
        ).hexdigest()
        forged_packet["product_sources"][0]["byte_length"] = len(MODULE.canonical(empty_behavior))
        with self.assertRaisesRegex(MODULE.ProductProgramError, "observable behaviors"):
            MODULE.normalize_inventory(forged_packet, empty_behavior)

        duplicate_tracker = deepcopy(self.inventory)
        active_tracker = duplicate_tracker["tracker_states"][1]["tracker_ids"][0]
        duplicate_tracker["tracker_states"][3]["tracker_ids"].append(active_tracker)
        duplicate_tracker["tracker_states"][3]["tracker_ids"].sort()
        forged_packet["product_sources"][0]["sha256"] = MODULE.hashlib.sha256(
            MODULE.canonical(duplicate_tracker)
        ).hexdigest()
        forged_packet["product_sources"][0]["byte_length"] = len(MODULE.canonical(duplicate_tracker))
        with self.assertRaisesRegex(MODULE.ProductProgramError, "more than one state"):
            MODULE.normalize_inventory(forged_packet, duplicate_tracker)

        wrong_length_packet = deepcopy(self.packet)
        wrong_length_packet["product_sources"][0]["byte_length"] += 1
        with self.assertRaisesRegex(MODULE.ProductProgramError, "content differs"):
            MODULE.normalize_inventory(wrong_length_packet, self.inventory)

    def test_counterexample_generalized_platform_and_role_conflicts_reject(self) -> None:
        missing_posture = base_submission(self.packet)
        missing_posture["candidates"][0]["counterexample_posture"] = ""
        with self.assertRaisesRegex(MODULE.ProductProgramError, "counterexample posture"):
            MODULE.build_reflection(self.packet, missing_posture, self.inventory)

        platform = base_submission(self.packet)
        platform["candidates"][0]["architecture_level"] = "generalized-platform"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "lacks independent architecture support"):
            MODULE.build_reflection(self.packet, platform, self.inventory)

        self_selecting = base_submission(self.packet)
        self_selecting["candidates"][0]["selector_id"] = "reflection-generator"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "must be distinct"):
            MODULE.build_reflection(self.packet, self_selecting, self.inventory)

        selection_prose = base_submission(self.packet)
        selection_prose["candidates"][0]["desired_effect"] = "This candidate is the winner and should be adopted."
        with self.assertRaisesRegex(MODULE.ProductProgramError, "asserts selection or adoption"):
            MODULE.build_reflection(self.packet, selection_prose, self.inventory)

        hidden_selection_prose = base_submission(self.packet)
        hidden_selection_prose["observations"][0]["summary"] = "This proves the feature is the winner."
        with self.assertRaisesRegex(MODULE.ProductProgramError, "asserts selection or adoption"):
            MODULE.build_reflection(self.packet, hidden_selection_prose, self.inventory)

        synonym_selection = base_submission(self.packet)
        synonym_selection["candidates"][0]["desired_effect"] = "This is the preferred proposal and must be implemented now."
        unreviewed = MODULE.build_reflection(self.packet, synonym_selection, self.inventory)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "lacks exact independent semantic acceptance"):
            MODULE.verify_reflection(self.packet, unreviewed, self.inventory)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "semantic review rejected"):
            MODULE.apply_semantic_review(
                self.packet, unreviewed, self.inventory, review_submission(unreviewed, decision="rejected")
            )

        self_claim = base_submission(self.packet)
        self_claim["candidates"][0]["selection_claim"] = "winner"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "asserts selection authority"):
            MODULE.build_reflection(self.packet, self_claim, self.inventory)

    def test_ladder_and_contrary_coverage_are_closed(self) -> None:
        no_pattern = base_submission(self.packet)
        no_pattern["meta_patterns"] = []
        with self.assertRaisesRegex(MODULE.ProductProgramError, "dangling evidence|orphaned"):
            MODULE.build_reflection(self.packet, no_pattern, self.inventory)

        orphaned_contrary = base_submission(self.packet)
        orphaned_contrary["observations"].append(
            {
                "evidence_ids": ["EVT-INCIDENT-1"],
                "observation_id": "observation-orphaned",
                "summary": "A second contrary observation must not disappear.",
                "valence": "contrary",
            }
        )
        with self.assertRaisesRegex(MODULE.ProductProgramError, "orphaned|remain visible"):
            MODULE.build_reflection(self.packet, orphaned_contrary, self.inventory)

        orphaned_noop = no_op_submission(self.packet)
        orphaned_noop["observations"].append(
            {
                "evidence_ids": ["outcome-1"],
                "observation_id": "observation-unused",
                "summary": "A second productive observation still requires a lesson link.",
                "valence": "productive",
            }
        )
        with self.assertRaisesRegex(MODULE.ProductProgramError, "orphaned observation"):
            MODULE.build_reflection(self.packet, orphaned_noop, self.inventory)

        contradictory_disposition = base_submission(self.packet)
        contradictory_disposition["capability_gaps"][0]["category_search"][2]["disposition"] = "searched-no-support"
        contradictory_disposition["capability_gaps"][0]["category_search"][2]["evidence_ids"] = []
        with self.assertRaisesRegex(MODULE.ProductProgramError, "contradicts its disposition"):
            MODULE.build_reflection(self.packet, contradictory_disposition, self.inventory)

        per_gap_omission = base_submission(self.packet)
        per_gap_omission["capability_gaps"][0]["lesson_ids"] = ["lesson-current"]
        per_gap_omission["capability_gaps"][0]["observation_ids"] = ["observation-current"]
        with self.assertRaisesRegex(MODULE.ProductProgramError, "meta-pattern closure|lesson closure"):
            MODULE.build_reflection(self.packet, per_gap_omission, self.inventory)

    def test_selection_budget_schedule_and_authority_fields_reject(self) -> None:
        selected = base_submission(self.packet)
        selected["candidates"][0]["selected"] = True
        with self.assertRaisesRegex(MODULE.ProductProgramError, "selection or hidden-output"):
            MODULE.build_reflection(self.packet, selected, self.inventory)

        reflection = accepted_reflection(self.packet, base_submission(self.packet), self.inventory)
        reflection["authority"]["selection_allowed"] = True
        reflection["artifact_root"] = MODULE.digest({key: reflection[key] for key in reflection if key != "artifact_root"})
        with self.assertRaisesRegex(MODULE.ProductProgramError, "asserts selection"):
            MODULE.verify_reflection(self.packet, reflection, self.inventory)

    def test_generation_ceiling_and_pass_bounds_reject(self) -> None:
        passes = base_submission(self.packet)
        passes["generation_pass_count"] = 2
        with self.assertRaisesRegex(MODULE.ProductProgramError, "exactly one"):
            MODULE.build_reflection(self.packet, passes, self.inventory)

        ceiling = base_submission(self.packet)
        ceiling["candidate_ceiling"] = 2
        with self.assertRaisesRegex(MODULE.ProductProgramError, "declared ceiling"):
            MODULE.build_reflection(self.packet, ceiling, self.inventory)

    def test_exact_reuse_is_zero_work_and_stale_packet_rejects(self) -> None:
        reflection = accepted_reflection(self.packet, base_submission(self.packet), self.inventory)
        reused = MODULE.reuse_reflection(self.packet, reflection, self.inventory)
        self.assertEqual("reflection-reused", reused["action"])
        self.assertEqual(0, reused["model_calls"])
        self.assertFalse(reused["cognitive_work_started"])

        stale_packet = deepcopy(self.packet)
        stale_packet["artifact_root"] = "0" * 64
        with self.assertRaises(MODULE.ProductProgramError):
            MODULE.reuse_reflection(stale_packet, reflection, self.inventory)

    def test_cli_build_verify_and_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            packet_path = root / "packet.json"
            submission_path = root / "submission.json"
            inventory_path = root / "inventory.json"
            packet_path.write_bytes(MODULE.canonical(self.packet))
            inventory_path.write_bytes(MODULE.canonical(self.inventory))
            submission_path.write_bytes(MODULE.canonical(base_submission(self.packet)))
            built = subprocess.run(
                [sys.executable, str(SCRIPT), "build", "--packet", str(packet_path), "--inventory", str(inventory_path), "--submission", str(submission_path)],
                check=True,
                capture_output=True,
            )
            reflection = json.loads(built.stdout)["reflection"]
            reflection_path = root / "reflection.json"
            reflection_path.write_bytes(MODULE.canonical(reflection))
            review_path = root / "review.json"
            review_path.write_bytes(MODULE.canonical(review_submission(reflection)))
            reviewed = subprocess.run(
                [sys.executable, str(SCRIPT), "review", "--packet", str(packet_path), "--inventory", str(inventory_path), "--reflection", str(reflection_path), "--review", str(review_path)],
                check=True,
                capture_output=True,
            )
            reflection = json.loads(reviewed.stdout)["reflection"]
            reflection_path.write_bytes(MODULE.canonical(reflection))
            for command in ("verify", "reuse"):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), command, "--packet", str(packet_path), "--inventory", str(inventory_path), "--reflection", str(reflection_path)],
                    check=True,
                    capture_output=True,
                )
                self.assertTrue(json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
