#!/usr/bin/env python3
"""Evidence-bound behavior and stage records for inline correction."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
TRACKER_PATH = REPO_ROOT / "docs" / (
    "software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
)
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
MISSION_ROOT = "0" * 64
POLICY_ROOT = "1" * 64
EVENT_HEAD_ROOT = "2" * 64
TARGET_ROOT = "/tmp/software-factory-inline-correction-target"


def canonical_root(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evidence_root(source_class: str, claim_ids: list[str]) -> str:
    return canonical_root({"source_class": source_class, "claim_ids": claim_ids})


def evidence_index(case: dict[str, object]) -> dict[str, dict[str, object]]:
    evidence = case["evidence_refs"]
    assert isinstance(evidence, list)
    indexed = {str(item["ref_id"]): item for item in evidence}
    if len(indexed) != len(evidence):
        raise ValueError("duplicate evidence ref")
    return indexed


def required_path_claims(path: dict[str, object]) -> set[str]:
    return {
        f"path:{path['path_id']}",
        f"owner:{path['owner_id']}",
        f"capability:{'complete' if path['capability_complete'] else 'incomplete'}",
        f"protected:{'preserved' if path['protected_preserved'] else 'regressed'}",
        f"scope:{'within-block' if path['within_block'] else 'outside-block'}",
        f"validation:{'suitable' if path['validation_suitable'] else 'unsuitable'}",
        "implementation-evidence:"
        + ("required" if path["requires_implementation_evidence"] else "not-required"),
        *(f"consumer:{consumer}" for consumer in path["current_consumers"]),
    }


def validate_source_evidence(case: dict[str, object]) -> dict[str, dict[str, object]]:
    indexed = evidence_index(case)
    used_refs: set[str] = set()
    for evidence in indexed.values():
        if set(evidence) != {
            "ref_id",
            "source_class",
            "adjudication_posture",
            "root_sha256",
            "claim_ids",
        }:
            raise ValueError("evidence shape differs from Block 4")
        if evidence["adjudication_posture"] != "adjudicating":
            raise ValueError("decision evidence is not adjudicating")
        claims = evidence["claim_ids"]
        if claims != sorted(set(claims)):
            raise ValueError("evidence claims are not canonical")
        if evidence["root_sha256"] != evidence_root(evidence["source_class"], claims):
            raise ValueError("evidence root is stale")

    path_ids: set[str] = set()
    kinds: set[str] = set()
    for path in case["paths"]:
        path_id = str(path["path_id"])
        if path_id in path_ids or path["kind"] in kinds:
            raise ValueError("path identity or kind is duplicated")
        path_ids.add(path_id)
        kinds.add(str(path["kind"]))
        refs = path["evidence_ref_ids"]
        if not refs or any(ref not in indexed for ref in refs):
            raise ValueError("path evidence is dangling")
        used_refs.update(str(ref) for ref in refs)
        claims = {
            claim
            for ref in refs
            for claim in indexed[str(ref)]["claim_ids"]
        }
        required = required_path_claims(path)
        if not required.issubset(claims):
            raise ValueError("path facts differ from source evidence")
        unsupported_extra = {
            claim for claim in claims - required
            if claim != "protected-existing-effect" and not claim.startswith("trigger:")
        }
        if unsupported_extra:
            raise ValueError("path evidence contains unrelated claims")
    if kinds != set(PATH_ORDER):
        raise ValueError("the exact three path kinds are required")

    trigger = str(case["trigger"])
    if trigger not in {"none", "equivalent-fingerprint"}:
        trigger_claim = f"trigger:{trigger}"
        trigger_refs = {
            ref_id
            for ref_id, evidence in indexed.items()
            if trigger_claim in evidence["claim_ids"]
            and evidence["source_class"] in TRIGGER_SOURCE_CLASSES
        }
        if not trigger_refs:
            raise ValueError("trigger lacks source-backed evidence")
        used_refs.update(trigger_refs)
    if used_refs != set(indexed):
        raise ValueError("unbound evidence remains in decision catalog")

    valid = set(case["valid_work_refs"])
    stale = set(case["stale_proof_refs"])
    if valid.intersection(stale):
        raise ValueError("valid and stale proof overlap")
    if not valid.union(stale).issubset(indexed):
        raise ValueError("work classification does not resolve")
    return indexed


def path_rejection_reasons(
    case: dict[str, object], path: dict[str, object]
) -> list[str]:
    reasons: list[str] = []
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


def derive_selection(case: dict[str, object]) -> tuple[str, str | None]:
    validate_source_evidence(case)
    paths = case["paths"]
    incumbent = next(
        path for path in paths if path["path_id"] == case["incumbent_path_id"]
    )
    if case["block_contract_root"] != case["live_block_contract_root"]:
        if not supported_trigger(case):
            raise ValueError("block contract changed without source-backed trigger")
        return "amend-structure", None

    static_eligible = [path for path in paths if not path_rejection_reasons(case, path)]
    evidence_candidates = [
        path
        for path in paths
        if path_rejection_reasons(case, path) == ["implementation-evidence-required"]
    ]
    if not supported_trigger(case):
        if path_rejection_reasons(case, incumbent):
            raise ValueError("no supported in-contract correction or candidate")
        return "continue-unchanged", str(incumbent["path_id"])
    if static_eligible:
        selected = min(static_eligible, key=lambda path: PATH_ORDER[str(path["kind"])])
        return "correct-inline", str(selected["path_id"])
    if evidence_candidates:
        return "compare-candidate", None
    raise ValueError("no supported in-contract correction or candidate")


def compared_paths(case: dict[str, object], selected: str | None) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in sorted(case["paths"], key=lambda item: PATH_ORDER[str(item["kind"])]):
        reasons = path_rejection_reasons(case, path)
        if path["path_id"] == selected:
            posture = "selected"
            rationale = "lowest-complexity complete source-backed path"
        elif reasons:
            posture = "rejected"
            rationale = ",".join(reasons)
        else:
            posture = "rejected"
            rationale = "higher-complexity-complete-path"
        result.append(
            {
                "path_id": path["path_id"],
                "kind": path["kind"],
                "posture": posture,
                "rationale": rationale,
                "evidence_ref_ids": sorted(path["evidence_ref_ids"]),
            }
        )
    return result


def decision_projection(
    case: dict[str, object], selected: str | None
) -> dict[str, object]:
    evidence = sorted(case["evidence_refs"], key=lambda item: item["ref_id"])
    protected_refs = sorted(ref["ref_id"] for ref in evidence)
    values: dict[str, object] = {
        "schema_version": 1,
        "mission_root": MISSION_ROOT,
        "authority_effect": "none",
        "authority_claim_id": None,
        "authority_evidence_refs": [],
        "prior_mission_root": MISSION_ROOT,
        "proposed_mission_root": None,
        "tracker_path": str(TRACKER_PATH.resolve()),
        "block_number": EXERCISE["current_block"],
        "block_contract_root": case["block_contract_root"],
        "target_class": "target-repository",
        "target_repository_root": TARGET_ROOT,
        "decision_target_state_root": canonical_root(
            {
                "case_id": case["case_id"],
                "incumbent_path_id": case["incumbent_path_id"],
                "target_revision": EXERCISE["target_revision"],
            }
        ),
        "capability_statement": "Supply the complete current consumer capability",
        "capability_frame_root": canonical_root(
            {"case_id": case["case_id"], "capability": "complete-current-consumer"}
        ),
        "protected_capability_results": [
            {
                "capability_id": "protected-existing-effect",
                "result": "preserved",
                "evidence_ref_ids": protected_refs,
            }
        ],
        "adjudicating_evidence_ref_ids": sorted(ref["ref_id"] for ref in evidence),
        "adjudicating_evidence_root": canonical_root(evidence),
        "compared_paths": compared_paths(case, selected),
        "affected_scope": [
            {
                "owner_id": case["canonical_owner_id"],
                "path": TARGET_ROOT,
                "content_root": canonical_root({"case_id": case["case_id"]}),
            }
        ],
        "proposer_author_id": None,
        "implementation_owner_id": case["canonical_owner_id"],
        "stop_boundary": "before candidate lane, tracker amendment, or policy change",
    }
    if set(values) != set(SPEC["fingerprint_projection"]):
        raise ValueError("fingerprint projection differs from Block 4")
    return values


def decision_fingerprint(case: dict[str, object], selected: str | None) -> str:
    return canonical_root(decision_projection(case, selected))


def process_evidence(
    case: dict[str, object], stage: str, decision_id: str, state_root: str
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    if stage in {"validated", "closed"}:
        claims = sorted([decision_id, state_root])
        result.append(
            {
                "ref_id": f"validation-{stage}",
                "source_class": "validation",
                "adjudication_posture": "process",
                "root_sha256": canonical_root(
                    {"case_id": case["case_id"], "stage": stage, "proof": "focused-pass"}
                ),
                "claim_ids": claims,
            }
        )
    if stage == "closed":
        claims = sorted(
            [decision_id, state_root, EXERCISE["target_revision_root"]]
        )
        result.append(
            {
                "ref_id": "observed-outcome-closed",
                "source_class": "observed-outcome",
                "adjudication_posture": "current-outcome",
                "root_sha256": canonical_root(
                    {
                        "case_id": case["case_id"],
                        "stage": stage,
                        "effect": "selected-path-current",
                    }
                ),
                "claim_ids": claims,
            }
        )
    return result


def currentness_projection(record: dict[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    for field in SPEC["currentness_projection"]:
        if field.endswith("?"):
            continue
        values[field] = record[field]
    return values


def build_inline_stage_records(
    case: dict[str, object], selected: str
) -> list[dict[str, object]]:
    fingerprint_values = decision_projection(case, selected)
    fingerprint = canonical_root(fingerprint_values)
    base_evidence = sorted(case["evidence_refs"], key=lambda item: item["ref_id"])
    selected_path = next(path for path in case["paths"] if path["path_id"] == selected)
    stages = ["selected", "implementing", "validated", "closed"]
    records: list[dict[str, object]] = []
    previous_id: str | None = None
    for index, stage in enumerate(stages):
        decision_id = f"inline-{case['case_id']}-{stage}"
        state_root = canonical_root(
            {
                "case_id": case["case_id"],
                "selected_path": selected,
                "stage": stage,
                "target_revision": EXERCISE["target_revision"],
            }
        )
        evidence = sorted(
            [*copy.deepcopy(base_evidence), *process_evidence(case, stage, decision_id, state_root)],
            key=lambda item: item["ref_id"],
        )
        record: dict[str, object] = {
            **fingerprint_values,
            "decision_id": decision_id,
            "decision_stage": stage,
            "disposition": "correct-inline",
            "recorded_at": f"2026-08-09T12:30:0{index}.000000Z",
            "predecessor_decision_id": None,
            "currentness_refresh_of": previous_id,
            "tracker_sha256": EXERCISE["tracker_sha256"],
            "target_revision": EXERCISE["target_revision"],
            "target_revision_root": EXERCISE["target_revision_root"],
            "current_target_state_root": state_root,
            "evidence_refs": evidence,
            "evidence_manifest_root": canonical_root(evidence),
            "decision_fingerprint": fingerprint,
            "selected_path": selected,
            "rejected_paths": [
                path["path_id"] for path in compared_paths(case, selected)
                if path["posture"] == "rejected"
            ],
            "valid_work_refs": sorted(case["valid_work_refs"]),
            "stale_proof_refs": sorted(case["stale_proof_refs"]),
            "safe_frontier": [],
            "adaptive_decision_mode": "full-autonomous",
            "reviewer_id": None,
            "evaluator_id": None,
            "policy_root": POLICY_ROOT,
            "event_head_root": EVENT_HEAD_ROOT,
            "accepted_decision_head": None,
            "accepted_revision_head": None,
            "revisit_trigger": None,
            "external_boundary": None,
        }
        record["currentness_root"] = canonical_root(currentness_projection(record))
        if set(record) != set(SPEC["common_fields"]):
            raise ValueError("stage record differs from Block 4 common record")
        if canonical_root({key: record[key] for key in SPEC["fingerprint_projection"]}) != fingerprint:
            raise ValueError("stage changed decision fingerprint")
        records.append(record)
        previous_id = decision_id
    return records


def accepted_snapshot_root(case: dict[str, object], selected: str) -> tuple[str, str]:
    records = build_inline_stage_records(case, selected)
    return str(records[-1]["decision_fingerprint"]), str(records[-1]["currentness_root"])


def closure_evidence_is_current(record: dict[str, object]) -> bool:
    validation = [
        item for item in record["evidence_refs"]
        if item["source_class"] == "validation"
        and item["adjudication_posture"] == "process"
    ]
    outcomes = [
        item for item in record["evidence_refs"]
        if item["source_class"] == "observed-outcome"
        and item["adjudication_posture"] == "current-outcome"
    ]
    validation_claims = {record["decision_id"], record["current_target_state_root"]}
    outcome_claims = {
        record["decision_id"],
        record["current_target_state_root"],
        record["target_revision_root"],
    }
    return (
        record["decision_stage"] == "closed"
        and any(validation_claims.issubset(set(item["claim_ids"])) for item in validation)
        and any(outcome_claims.issubset(set(item["claim_ids"])) for item in outcomes)
        and record["currentness_root"] == canonical_root(currentness_projection(record))
    )


def decide(case: dict[str, object], current_block: int) -> dict[str, object]:
    disposition, selected = derive_selection(case)
    fingerprint = decision_fingerprint(case, selected)
    deduplicated = False
    records: list[dict[str, object]] = []
    if case["trigger"] == "equivalent-fingerprint":
        if selected is None:
            raise ValueError("equivalent decision has no incumbent")
        expected_fingerprint, expected_currentness = accepted_snapshot_root(case, selected)
        if (
            case["accepted_fingerprint"] != expected_fingerprint
            or case["accepted_currentness_root"] != expected_currentness
        ):
            raise ValueError("accepted fingerprint/currentness is stale")
        deduplicated = True
    elif disposition == "correct-inline":
        assert selected is not None
        records = build_inline_stage_records(case, selected)
        closed = records[-1]
        if not closure_evidence_is_current(closed):
            raise ValueError("inline closure lacks current validation/outcome")

    rejected = {
        str(path["path_id"]): path_rejection_reasons(case, path)
        or (["higher-complexity-complete-path"] if path["path_id"] != selected else [])
        for path in case["paths"]
        if path["path_id"] != selected
    }
    continuation = (
        f"block:{current_block}:remaining-work"
        if disposition in {"continue-unchanged", "correct-inline"}
        else f"block:{current_block}:safe-frontier"
    )
    return {
        "disposition": disposition,
        "selected_path": selected,
        "rejected_paths": rejected,
        "valid_work_refs": sorted(case["valid_work_refs"]),
        "stale_proof_refs": sorted(case["stale_proof_refs"]),
        "decision_fingerprint": fingerprint,
        "stage_records": records,
        "decision_stages": [record["decision_stage"] for record in records]
        or (["selected"] if disposition in {"compare-candidate", "amend-structure"} else []),
        "continue_to": continuation,
        "extra_cycle": disposition != "continue-unchanged",
        "deduplicated": deduplicated,
    }


def refresh_path_evidence(case: dict[str, object], path_id: str) -> None:
    path = next(path for path in case["paths"] if path["path_id"] == path_id)
    claims = sorted({*required_path_claims(path), "protected-existing-effect"})
    for ref_id in path["evidence_ref_ids"]:
        evidence = next(item for item in case["evidence_refs"] if item["ref_id"] == ref_id)
        evidence["claim_ids"] = claims
        evidence["root_sha256"] = evidence_root(evidence["source_class"], claims)


class InlineCorrectionContractTests(unittest.TestCase):
    def test_source_cases_derive_disposition_identity_stages_and_continuation(self) -> None:
        self.assertEqual(EXERCISE["schema_version"], 2)
        self.assertEqual(len(EXERCISE["cases"]), 10)
        self.assertEqual(
            EXERCISE["target_revision_root"],
            canonical_root({"target_revision": EXERCISE["target_revision"]}),
        )
        for case in EXERCISE["cases"]:
            result = decide(case, EXERCISE["current_block"])
            self.assertEqual(result["disposition"], case["expected_disposition"])
            self.assertEqual(result["selected_path"], case["expected_selected_path"])
            self.assertEqual(result["decision_stages"], case["expected_decision_stages"])
            self.assertEqual(result["continue_to"], case["expected_continue_to"])
            self.assertEqual(result["extra_cycle"], case["expected_extra_cycle"])
            self.assertRegex(result["decision_fingerprint"], SHA256_RE)
            for rejected_path, reasons in result["rejected_paths"].items():
                self.assertTrue(reasons, rejected_path)

    def test_inline_records_are_exact_immutable_and_close_on_current_outcome(self) -> None:
        case = next(
            item for item in EXERCISE["cases"]
            if item["case_id"] == "lower-power-shortcut"
        )
        result = decide(case, 5)
        records = result["stage_records"]
        self.assertEqual([record["decision_stage"] for record in records], [
            "selected", "implementing", "validated", "closed"
        ])
        self.assertEqual(len({record["decision_fingerprint"] for record in records}), 1)
        self.assertEqual(len({record["currentness_root"] for record in records}), 4)
        for index, record in enumerate(records):
            self.assertEqual(
                record["currentness_root"], canonical_root(currentness_projection(record))
            )
            if index == 0:
                self.assertIsNone(record["currentness_refresh_of"])
            else:
                self.assertEqual(
                    record["currentness_refresh_of"], records[index - 1]["decision_id"]
                )
        closed = records[-1]
        classes = {item["source_class"] for item in closed["evidence_refs"]}
        self.assertIn("validation", classes)
        self.assertIn("observed-outcome", classes)
        outcome = next(
            item for item in closed["evidence_refs"]
            if item["source_class"] == "observed-outcome"
        )
        self.assertEqual(outcome["adjudication_posture"], "current-outcome")
        self.assertIn(closed["decision_id"], outcome["claim_ids"])
        self.assertIn(closed["current_target_state_root"], outcome["claim_ids"])
        self.assertIn(closed["target_revision_root"], outcome["claim_ids"])
        self.assertTrue(closure_evidence_is_current(closed))

        missing_outcome = copy.deepcopy(closed)
        missing_outcome["evidence_refs"] = [
            item for item in missing_outcome["evidence_refs"]
            if item["source_class"] != "observed-outcome"
        ]
        missing_outcome["evidence_manifest_root"] = canonical_root(
            missing_outcome["evidence_refs"]
        )
        missing_outcome["currentness_root"] = canonical_root(
            currentness_projection(missing_outcome)
        )
        self.assertFalse(closure_evidence_is_current(missing_outcome))

        stale_claim = copy.deepcopy(closed)
        stale_outcome = next(
            item for item in stale_claim["evidence_refs"]
            if item["source_class"] == "observed-outcome"
        )
        stale_outcome["claim_ids"] = [closed["decision_id"]]
        stale_claim["evidence_manifest_root"] = canonical_root(stale_claim["evidence_refs"])
        stale_claim["currentness_root"] = canonical_root(currentness_projection(stale_claim))
        self.assertFalse(closure_evidence_is_current(stale_claim))

    def test_legitimate_owner_and_capability_evidence_changes_selection_and_root(self) -> None:
        original = next(
            case for case in EXERCISE["cases"]
            if case["case_id"] == "lower-power-shortcut"
        )
        base = decide(original, 5)
        self.assertEqual(base["selected_path"], "bounded-general")

        changed_owner = copy.deepcopy(original)
        changed_owner["canonical_owner_id"] = "owner-other"
        owner_path = next(
            path for path in changed_owner["paths"]
            if path["path_id"] == "architectural-owner"
        )
        owner_path["owner_id"] = "owner-other"
        owner_path["current_consumers"] = ["consumer-current"]
        refresh_path_evidence(changed_owner, "architectural-owner")
        owner_result = decide(changed_owner, 5)
        self.assertEqual(owner_result["selected_path"], "architectural-owner")
        self.assertNotEqual(base["decision_fingerprint"], owner_result["decision_fingerprint"])

        local_complete = copy.deepcopy(original)
        local = next(path for path in local_complete["paths"] if path["path_id"] == "local")
        local["capability_complete"] = True
        local["current_consumers"] = ["consumer-current"]
        refresh_path_evidence(local_complete, "local")
        local_result = decide(local_complete, 5)
        self.assertEqual(local_result["selected_path"], "local")
        self.assertNotEqual(base["decision_fingerprint"], local_result["decision_fingerprint"])

    def test_stale_or_dangling_evidence_and_overlap_fail_closed(self) -> None:
        wrong_owner = next(
            case for case in EXERCISE["cases"] if case["case_id"] == "wrong-owner"
        )
        overlap = copy.deepcopy(wrong_owner)
        overlap["valid_work_refs"] = ["ev-local"]
        with self.assertRaisesRegex(ValueError, "valid and stale"):
            decide(overlap, 5)

        dangling = copy.deepcopy(wrong_owner)
        dangling["paths"][1]["evidence_ref_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "dangling"):
            decide(dangling, 5)

        process_trigger = copy.deepcopy(wrong_owner)
        process_trigger["evidence_refs"][0]["adjudication_posture"] = "process"
        with self.assertRaisesRegex(ValueError, "not adjudicating"):
            decide(process_trigger, 5)

        stale_fact = copy.deepcopy(wrong_owner)
        local = next(path for path in stale_fact["paths"] if path["path_id"] == "local")
        local["capability_complete"] = False
        with self.assertRaisesRegex(ValueError, "facts differ"):
            decide(stale_fact, 5)

    def test_equal_fingerprint_fast_path_rejects_stale_live_mutation(self) -> None:
        repeated = next(
            case for case in EXERCISE["cases"] if case["case_id"] == "unchanged-repeat"
        )
        result = decide(repeated, 5)
        self.assertEqual(result["disposition"], "continue-unchanged")
        self.assertTrue(result["deduplicated"])
        self.assertFalse(result["extra_cycle"])
        self.assertEqual(result["continue_to"], "block:5:remaining-work")

        mutated = copy.deepcopy(repeated)
        local = next(path for path in mutated["paths"] if path["path_id"] == "local")
        local["owner_id"] = "owner-wrong"
        local["capability_complete"] = False
        with self.assertRaises(ValueError):
            decide(mutated, 5)

    def test_method_preserves_work_rejects_meta_flow_and_escalates_exactly(self) -> None:
        for phrase in (
            "Stop only the causal bad process or write owner",
            "Preserve\n   coherent code, tests, artifacts, commits, accepted evidence",
            "immediately continue its remaining dependency-safe work",
            "No\n   tracker edit, authoring thread, separate supervision lifecycle, human prompt",
            "do not create a correction registry or second ledger",
            "zero model, reviewer, candidate, or authoring work",
        ):
            self.assertIn(phrase, SKILL)
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
