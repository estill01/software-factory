#!/usr/bin/env python3
"""Evidence-bound behavior and static contracts for inline correction."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
EXERCISE = json.loads(
    (SKILL_ROOT / "fixtures" / "inline_correction_v1.json").read_text(
        encoding="utf-8"
    )
)
REFERENCE = (SKILL_ROOT / "references" / "adaptive-decision-control.md").read_text(
    encoding="utf-8"
)
SPEC = json.loads(
    REFERENCE.split("<!-- contract-spec-v1 -->", 1)[1]
    .split("```json", 1)[1]
    .split("```", 1)[0]
)


PATH_ORDER = {"local": 0, "bounded-general": 1, "architectural-owner": 2}
TRIGGER_SOURCE_CLASSES = {"repository", "tracker", "canonical-event", "validation"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_root(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evidence_index(case: dict[str, object]) -> dict[str, dict[str, object]]:
    evidence = case["evidence_refs"]
    assert isinstance(evidence, list)
    indexed = {str(item["ref_id"]): item for item in evidence}
    if len(indexed) != len(evidence):
        raise ValueError("duplicate evidence ref")
    return indexed


def path_rejection_reasons(
    case: dict[str, object], path: dict[str, object]
) -> list[str]:
    reasons: list[str] = []
    indexed = evidence_index(case)
    refs = path["evidence_ref_ids"]
    if not refs or any(ref not in indexed for ref in refs):
        reasons.append("missing-source-evidence")
    elif not any(
        f"path:{path['path_id']}" in indexed[str(ref)]["claim_ids"] for ref in refs
    ):
        reasons.append("evidence-does-not-bind-path")
    if path["owner_id"] != case["canonical_owner_id"]:
        reasons.append("wrong-owner")
    if not path["capability_complete"]:
        reasons.append("capability-underreach")
    if not path["protected_preserved"]:
        reasons.append("protected-capability-regression")
    if not path["within_block"]:
        reasons.append("outside-block-contract")
    if not path["validation_suitable"]:
        reasons.append("invalid-validation")
    if not path["current_consumers"]:
        reasons.append("unsupported-generality")
    if path["requires_implementation_evidence"]:
        reasons.append("implementation-evidence-required")
    return reasons


def supported_trigger(case: dict[str, object]) -> bool:
    trigger = str(case["trigger"])
    if trigger in {"none", "equivalent-fingerprint"}:
        return False
    claim = f"trigger:{trigger}"
    return any(
        item["source_class"] in TRIGGER_SOURCE_CLASSES
        and claim in item["claim_ids"]
        for item in case["evidence_refs"]
    )


def decide(case: dict[str, object], current_block: int) -> dict[str, object]:
    indexed = evidence_index(case)
    valid = set(case["valid_work_refs"])
    stale = set(case["stale_proof_refs"])
    if valid.intersection(stale):
        raise ValueError("valid and stale proof overlap")
    if not valid.union(stale).issubset(indexed):
        raise ValueError("work classification does not resolve")
    for name in ("decision_fingerprint", "currentness_root"):
        if not SHA256_RE.fullmatch(str(case[name])):
            raise ValueError(f"invalid {name}")

    if (
        case["decision_fingerprint"] == case["accepted_fingerprint"]
        and case["currentness_root"] == case["accepted_currentness_root"]
    ):
        disposition = "continue-unchanged"
        selected = str(case["incumbent_path_id"])
    else:
        paths = case["paths"]
        assert isinstance(paths, list)
        static_eligible = [path for path in paths if not path_rejection_reasons(case, path)]
        evidence_candidates = [
            path
            for path in paths
            if path_rejection_reasons(case, path) == ["implementation-evidence-required"]
        ]
        incumbent = next(
            path for path in paths if path["path_id"] == case["incumbent_path_id"]
        )
        trigger_is_supported = supported_trigger(case)
        if case["block_contract_root"] != case["live_block_contract_root"]:
            if not trigger_is_supported:
                raise ValueError("block contract changed without source-backed trigger")
            disposition = "amend-structure"
            selected = None
        elif not trigger_is_supported:
            if path_rejection_reasons(case, incumbent):
                raise ValueError("no supported in-contract correction or candidate")
            disposition = "continue-unchanged"
            selected = str(incumbent["path_id"])
        elif static_eligible:
            selected_path = min(static_eligible, key=lambda path: PATH_ORDER[str(path["kind"])])
            disposition = "correct-inline"
            selected = str(selected_path["path_id"])
        elif evidence_candidates:
            disposition = "compare-candidate"
            selected = None
        else:
            raise ValueError("no supported in-contract correction or candidate")

    stages = {
        "continue-unchanged": [],
        "correct-inline": ["selected", "implementing", "validated", "closed"],
        "compare-candidate": ["selected"],
        "amend-structure": ["selected"],
    }[disposition]
    continuation = (
        f"block:{current_block}:remaining-work"
        if disposition in {"continue-unchanged", "correct-inline"}
        else f"block:{current_block}:safe-frontier"
    )
    paths = case["paths"]
    rejected = {
        str(path["path_id"]): path_rejection_reasons(case, path)
        or (["higher-complexity-complete-path"] if path["path_id"] != selected else [])
        for path in paths
        if path["path_id"] != selected
    }
    return {
        "disposition": disposition,
        "selected_path": selected,
        "rejected_paths": rejected,
        "valid_work_refs": sorted(valid),
        "stale_proof_refs": sorted(stale),
        "decision_stages": stages,
        "continue_to": continuation,
        "extra_cycle": disposition != "continue-unchanged",
    }


class InlineCorrectionContractTests(unittest.TestCase):
    def test_exercise_is_block4_bound_and_routes_source_backed_cases(self) -> None:
        self.assertEqual(EXERCISE["schema_version"], 2)
        self.assertEqual(len(EXERCISE["cases"]), 10)
        self.assertEqual(
            EXERCISE["target_revision_root"],
            canonical_root({"target_revision": EXERCISE["target_revision"]}),
        )
        for field in (
            "decision_fingerprint",
            "target_revision_root",
            "valid_work_refs",
            "stale_proof_refs",
        ):
            self.assertIn(field, SPEC["currentness_projection"])
        self.assertIn("block_contract_root", SPEC["fingerprint_projection"])
        self.assertIn("compared_paths", SPEC["fingerprint_projection"])
        for case in EXERCISE["cases"]:
            for evidence in case["evidence_refs"]:
                self.assertEqual(
                    set(evidence),
                    {
                        "ref_id",
                        "source_class",
                        "adjudication_posture",
                        "root_sha256",
                        "claim_ids",
                    },
                )
                self.assertEqual(evidence["adjudication_posture"], "adjudicating")
                self.assertRegex(evidence["root_sha256"], SHA256_RE)
                self.assertTrue(evidence["claim_ids"])
            result = decide(case, EXERCISE["current_block"])
            self.assertEqual(result["disposition"], case["expected_disposition"])
            self.assertEqual(result["selected_path"], case["expected_selected_path"])
            self.assertEqual(result["decision_stages"], case["expected_decision_stages"])
            self.assertEqual(result["continue_to"], case["expected_continue_to"])
            self.assertEqual(result["extra_cycle"], case["expected_extra_cycle"])
            self.assertEqual(result["valid_work_refs"], sorted(case["valid_work_refs"]))
            self.assertEqual(result["stale_proof_refs"], sorted(case["stale_proof_refs"]))
            self.assertNotIn("user", result["continue_to"])
            self.assertNotIn("lifecycle", result["continue_to"])
            for rejected_path, reasons in result["rejected_paths"].items():
                self.assertTrue(reasons, rejected_path)

    def test_owner_and_capability_mutations_change_selection(self) -> None:
        original = next(
            case for case in EXERCISE["cases"]
            if case["case_id"] == "lower-power-shortcut"
        )
        self.assertEqual(decide(original, 5)["selected_path"], "bounded-general")

        changed_owner = copy.deepcopy(original)
        changed_owner["canonical_owner_id"] = "owner-other"
        for path in changed_owner["paths"]:
            if path["path_id"] == "architectural-owner":
                path["owner_id"] = "owner-other"
                path["current_consumers"] = ["consumer-current"]
        self.assertEqual(decide(changed_owner, 5)["selected_path"], "architectural-owner")

        local_now_complete = copy.deepcopy(original)
        local_now_complete["paths"][0]["capability_complete"] = True
        local_now_complete["paths"][0]["current_consumers"] = ["consumer-current"]
        self.assertEqual(decide(local_now_complete, 5)["selected_path"], "local")

    def test_invalid_evidence_and_work_overlap_fail_closed(self) -> None:
        original = next(
            case for case in EXERCISE["cases"] if case["case_id"] == "wrong-owner"
        )
        overlap = copy.deepcopy(original)
        overlap["valid_work_refs"] = ["ev-local"]
        with self.assertRaisesRegex(ValueError, "valid and stale"):
            decide(overlap, 5)

        dangling = copy.deepcopy(original)
        dangling["paths"][2]["evidence_ref_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "no supported"):
            decide(dangling, 5)

        unsupported_trigger = copy.deepcopy(original)
        unsupported_trigger["evidence_refs"][0]["claim_ids"] = ["unrelated"]
        with self.assertRaisesRegex(ValueError, "no supported"):
            decide(unsupported_trigger, 5)

    def test_unchanged_path_has_no_meta_cycle_and_returns_to_work(self) -> None:
        for case_id in ("justified-incumbent", "unchanged-repeat"):
            case = next(case for case in EXERCISE["cases"] if case["case_id"] == case_id)
            result = decide(case, EXERCISE["current_block"])
            self.assertEqual(result["disposition"], "continue-unchanged")
            self.assertIs(result["extra_cycle"], False)
            self.assertEqual(result["decision_stages"], [])
            self.assertEqual(result["continue_to"], "block:5:remaining-work")
        self.assertIn("zero model, reviewer, candidate, or authoring work", SKILL)
        self.assertIn("Never convert\n   `continue-unchanged` into a user-facing return", SKILL)

    def test_inline_preserves_contract_valid_work_and_existing_owner(self) -> None:
        for phrase in (
            "Stop only the causal bad process or write owner",
            "Preserve\n   coherent code, tests, artifacts, commits, accepted evidence",
            "original objective, dependencies,\n   acceptance, and Stop remain unchanged",
            "smallest focused\n   proof first",
            "immediately continue its remaining dependency-safe work",
        ):
            self.assertIn(phrase, SKILL)

    def test_comparison_rejects_underreach_and_unsupported_generality(self) -> None:
        self.assertIn("smallest local correction", SKILL)
        self.assertIn("smallest\n   bounded-general path", SKILL)
        self.assertIn("available architectural owner", SKILL)
        self.assertIn("lowest-complexity path that\n   supplies the complete", SKILL)
        self.assertIn("unsupported generalized layer lost", SKILL)
        lower = next(
            case for case in EXERCISE["cases"]
            if case["case_id"] == "lower-power-shortcut"
        )
        result = decide(lower, 5)
        self.assertIn("capability-underreach", result["rejected_paths"]["local"])
        self.assertIn(
            "higher-complexity-complete-path",
            result["rejected_paths"]["architectural-owner"],
        )

    def test_inline_does_not_invent_meta_workflow_and_escalates_exactly(self) -> None:
        for prohibited in (
            "No\n   tracker edit, authoring thread, separate supervision lifecycle, human prompt",
            "do not create a correction registry or second ledger",
            "not a new task, authoring pass, supervisor lifecycle, or approval gate",
        ):
            self.assertIn(prohibited, SKILL)
        candidate = next(
            case for case in EXERCISE["cases"] if case["case_id"] == "requires-candidate"
        )
        structural = next(
            case for case in EXERCISE["cases"]
            if case["case_id"] == "requires-structural-amendment"
        )
        self.assertEqual(decide(candidate, 5)["disposition"], "compare-candidate")
        self.assertEqual(decide(structural, 5)["disposition"], "amend-structure")


if __name__ == "__main__":
    unittest.main()
