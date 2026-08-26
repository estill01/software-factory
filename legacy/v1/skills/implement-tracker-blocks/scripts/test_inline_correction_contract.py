#!/usr/bin/env python3
"""Evidence-bound behavior and stage records for inline correction."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path
from unittest import mock


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
ACCEPTED_SNAPSHOT = json.loads(
    (SKILL_ROOT / "fixtures" / "inline_correction_accepted_v1.json").read_text(
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
GIT_EXECUTABLE = "/usr/bin/git"
TARGET_ROOT = "/software-factory-inline-correction-target"
TRACKER_RECORD_PATH = f"{TARGET_ROOT}/{TRACKER_PATH.relative_to(REPO_ROOT).as_posix()}"
EXPECTED_EXERCISE_ROOT = "bc1457ab517d7555df4b177674839b21f8fbd25d8968f82b5aa20357999f4059"
EXPECTED_ACCEPTED_SNAPSHOT_ROOT = (
    "54037ea3771b57346f7d812ee4cfda7bfc791752fa9c0e841d6109280a435ad7"
)


def canonical_root(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def case_source_material(case: dict[str, object]) -> dict[str, object]:
    """Return the exact repository-owned input, excluding expected test outputs."""
    return {
        key: copy.deepcopy(value)
        for key, value in case.items()
        if not key.startswith("expected_")
    }


def case_source_root(case: dict[str, object]) -> str:
    return canonical_root(case_source_material(case))


def validate_exercise() -> None:
    if canonical_root(EXERCISE) != EXPECTED_EXERCISE_ROOT:
        raise ValueError("exercise source root differs")
    if (
        EXERCISE["schema_version"] != 2
        or EXERCISE["kind"] != "software-factory-inline-correction-exercise"
        or EXERCISE["current_block"] != 5
        or EXERCISE["requested_blocks"] != [5, 6]
        or not re.fullmatch(
            r"[0-9a-f]{40}", str(EXERCISE["tracker_source_revision"])
        )
    ):
        raise ValueError("exercise control identity differs")
    if EXERCISE["tracker_sha256"] != tracker_sha256():
        raise ValueError("tracker source root is stale")
    if EXERCISE["target_revision_root"] != canonical_root(
        {"target_revision": EXERCISE["target_revision"]}
    ):
        raise ValueError("target revision root is stale")


def canonical_case(case_id: str) -> dict[str, object]:
    validate_exercise()
    matches = [case for case in EXERCISE["cases"] if case["case_id"] == case_id]
    if len(matches) != 1:
        raise ValueError("case identity is absent or duplicated")
    case = matches[0]
    expected_roots = EXERCISE["case_source_roots"]
    if set(expected_roots) != {item["case_id"] for item in EXERCISE["cases"]}:
        raise ValueError("case source-root catalog is incomplete")
    if case_source_root(case) != expected_roots[case_id]:
        raise ValueError("repository-owned case source root differs")
    return copy.deepcopy(case)


def tracker_sha256() -> str:
    repository_probe = subprocess.run(
        [GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    frozen = subprocess.run(
        [
            GIT_EXECUTABLE,
            "show",
            f"{EXERCISE['tracker_source_revision']}:{TRACKER_PATH.relative_to(REPO_ROOT).as_posix()}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if frozen.returncode == 0:
        return hashlib.sha256(frozen.stdout).hexdigest()
    if repository_probe.returncode == 0:
        raise ValueError("frozen tracker source cannot be resolved in live repository")
    # A Git-less archive has no object database; the whole exercise root still
    # pins this independently reviewed source revision and frozen tracker root.
    return str(EXERCISE["tracker_sha256"])


def validate_accepted_snapshot() -> dict[str, object]:
    if canonical_root(ACCEPTED_SNAPSHOT) != EXPECTED_ACCEPTED_SNAPSHOT_ROOT:
        raise ValueError("accepted decision record root differs")
    exact_fields = {
        "schema_version",
        "kind",
        "record_id",
        "source_revision",
        "case_id",
        "case_source_root",
        "tracker_sha256",
        "block_number",
        "target_revision_root",
        "decision_fingerprint",
        "currentness_root",
        "closed_record_root",
    }
    if set(ACCEPTED_SNAPSHOT) != exact_fields:
        raise ValueError("accepted decision record shape differs")
    if (
        ACCEPTED_SNAPSHOT["schema_version"] != 1
        or ACCEPTED_SNAPSHOT["kind"] != "software-factory-accepted-inline-decision"
        or ACCEPTED_SNAPSHOT["block_number"] != 5
        or ACCEPTED_SNAPSHOT["tracker_sha256"] != tracker_sha256()
        or not re.fullmatch(r"[0-9a-f]{40}", str(ACCEPTED_SNAPSHOT["source_revision"]))
    ):
        raise ValueError("accepted decision identity differs")
    for field in (
        "case_source_root",
        "tracker_sha256",
        "target_revision_root",
        "decision_fingerprint",
        "currentness_root",
        "closed_record_root",
    ):
        if not SHA256_RE.fullmatch(str(ACCEPTED_SNAPSHOT[field])):
            raise ValueError("accepted decision contains an invalid root")
    return copy.deepcopy(ACCEPTED_SNAPSHOT)


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
        "tracker_path": TRACKER_RECORD_PATH,
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


def closure_evidence_is_current(
    record: dict[str, object], case: dict[str, object]
) -> bool:
    """Compare closure to independently derived repository and outcome material."""
    try:
        expected_root = EXERCISE["case_source_roots"][case["case_id"]]
        if case_source_root(case) != expected_root:
            return False
        if EXERCISE["tracker_sha256"] != tracker_sha256():
            return False
        selected = str(record["selected_path"])
        expected = build_inline_stage_records(case, selected)[-1]
    except (AssertionError, KeyError, TypeError, ValueError):
        return False
    return record == expected


def _decide(case: dict[str, object], expected_source_root: str) -> dict[str, object]:
    validate_exercise()
    if case_source_root(case) != expected_source_root:
        raise ValueError("case differs from repository-owned source root")
    disposition, selected = derive_selection(case)
    fingerprint = decision_fingerprint(case, selected)
    deduplicated = False
    records: list[dict[str, object]] = []
    if case["trigger"] == "equivalent-fingerprint":
        if selected is None:
            raise ValueError("equivalent decision has no incumbent")
        snapshot_id = case["accepted_snapshot_case_id"]
        if not isinstance(snapshot_id, str):
            raise ValueError("equivalent decision lacks an accepted snapshot")
        accepted = validate_accepted_snapshot()
        if (
            snapshot_id != accepted["record_id"]
            or case["case_id"] != accepted["case_id"]
            or accepted["case_source_root"] != expected_source_root
            or accepted["tracker_sha256"] != EXERCISE["tracker_sha256"]
            or accepted["target_revision_root"] != EXERCISE["target_revision_root"]
        ):
            raise ValueError("accepted decision does not bind current control identity")
        live_fingerprint, live_currentness = accepted_snapshot_root(case, selected)
        live_closed = build_inline_stage_records(case, selected)[-1]
        if (
            live_fingerprint != accepted["decision_fingerprint"]
            or live_currentness != accepted["currentness_root"]
            or canonical_root(live_closed) != accepted["closed_record_root"]
        ):
            raise ValueError("accepted fingerprint/currentness is stale")
        deduplicated = True
    elif disposition == "correct-inline":
        assert selected is not None
        records = build_inline_stage_records(case, selected)
        closed = records[-1]
        if not closure_evidence_is_current(closed, case):
            raise ValueError("inline closure lacks current validation/outcome")

    rejected = {
        str(path["path_id"]): path_rejection_reasons(case, path)
        or (["higher-complexity-complete-path"] if path["path_id"] != selected else [])
        for path in case["paths"]
        if path["path_id"] != selected
    }
    continuation = (
        f"block:{EXERCISE['current_block']}:remaining-work"
        if disposition in {"continue-unchanged", "correct-inline"}
        else f"block:{EXERCISE['current_block']}:safe-frontier"
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


def decide(case_id: str) -> dict[str, object]:
    case = canonical_case(case_id)
    return _decide(case, EXERCISE["case_source_roots"][case_id])


class InlineCorrectionContractTests(unittest.TestCase):
    def test_source_cases_derive_disposition_identity_stages_and_continuation(self) -> None:
        self.assertEqual(EXERCISE["schema_version"], 2)
        self.assertEqual(len(EXERCISE["cases"]), 10)
        self.assertEqual(EXERCISE["tracker_sha256"], tracker_sha256())
        self.assertEqual(
            EXERCISE["target_revision_root"],
            canonical_root({"target_revision": EXERCISE["target_revision"]}),
        )
        self.assertEqual(
            set(EXERCISE["case_source_roots"]),
            {case["case_id"] for case in EXERCISE["cases"]},
        )
        for source_case in EXERCISE["cases"]:
            case_id = source_case["case_id"]
            case = canonical_case(case_id)
            self.assertEqual(
                case_source_root(case), EXERCISE["case_source_roots"][case_id]
            )
            result = decide(case_id)
            self.assertEqual(result["disposition"], case["expected_disposition"])
            self.assertEqual(result["selected_path"], case["expected_selected_path"])
            self.assertEqual(result["decision_stages"], case["expected_decision_stages"])
            self.assertEqual(result["continue_to"], case["expected_continue_to"])
            self.assertEqual(result["extra_cycle"], case["expected_extra_cycle"])
            self.assertRegex(result["decision_fingerprint"], SHA256_RE)
            for rejected_path, reasons in result["rejected_paths"].items():
                self.assertTrue(reasons, rejected_path)

    def test_inline_records_are_exact_immutable_and_close_on_current_outcome(self) -> None:
        case = canonical_case("lower-power-shortcut")
        result = decide("lower-power-shortcut")
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
        self.assertTrue(closure_evidence_is_current(closed, case))

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
        self.assertFalse(closure_evidence_is_current(missing_outcome, case))

        stale_claim = copy.deepcopy(closed)
        stale_outcome = next(
            item for item in stale_claim["evidence_refs"]
            if item["source_class"] == "observed-outcome"
        )
        stale_outcome["claim_ids"] = [closed["decision_id"]]
        stale_claim["evidence_manifest_root"] = canonical_root(stale_claim["evidence_refs"])
        stale_claim["currentness_root"] = canonical_root(currentness_projection(stale_claim))
        self.assertFalse(closure_evidence_is_current(stale_claim, case))

        for field, replacement in (
            ("target_revision", "unbound-revision"),
            ("target_revision_root", "f" * 64),
            ("decision_fingerprint", "f" * 64),
            ("tracker_sha256", "f" * 64),
            ("block_number", 999),
        ):
            attacked = copy.deepcopy(closed)
            attacked[field] = replacement
            attacked["currentness_root"] = canonical_root(
                currentness_projection(attacked)
            )
            self.assertFalse(closure_evidence_is_current(attacked, case), field)

        invented_outcome = copy.deepcopy(closed)
        attacked_outcome = next(
            item for item in invented_outcome["evidence_refs"]
            if item["source_class"] == "observed-outcome"
        )
        attacked_outcome["root_sha256"] = "f" * 64
        invented_outcome["evidence_manifest_root"] = canonical_root(
            invented_outcome["evidence_refs"]
        )
        invented_outcome["currentness_root"] = canonical_root(
            currentness_projection(invented_outcome)
        )
        self.assertFalse(closure_evidence_is_current(invented_outcome, case))

    def test_repository_sources_select_all_three_paths_and_reject_self_authoring(self) -> None:
        selections = {
            "wrong-owner": "architectural-owner",
            "lower-power-shortcut": "bounded-general",
            "unnecessary-abstraction": "local",
        }
        for case_id, selected in selections.items():
            self.assertEqual(decide(case_id)["selected_path"], selected)

        case = canonical_case("lower-power-shortcut")
        expected_root = EXERCISE["case_source_roots"][case["case_id"]]
        mutations: list[tuple[str, dict[str, object]]] = []

        changed_owner = copy.deepcopy(case)
        changed_owner["canonical_owner_id"] = "invented-owner"
        mutations.append(("owner", changed_owner))

        invented_capability = copy.deepcopy(case)
        local = next(
            path for path in invented_capability["paths"] if path["path_id"] == "local"
        )
        local["capability_complete"] = True
        local["current_consumers"] = ["invented-consumer"]
        mutations.append(("capability", invented_capability))

        changed_contract = copy.deepcopy(case)
        changed_contract["block_contract_root"] = "f" * 64
        changed_contract["live_block_contract_root"] = "f" * 64
        mutations.append(("contract", changed_contract))

        rewritten_evidence = copy.deepcopy(case)
        evidence = rewritten_evidence["evidence_refs"][0]
        evidence["claim_ids"] = sorted([*evidence["claim_ids"], "consumer:invented"])
        evidence["root_sha256"] = evidence_root(
            evidence["source_class"], evidence["claim_ids"]
        )
        mutations.append(("evidence", rewritten_evidence))

        for label, attacked in mutations:
            with self.assertRaisesRegex(ValueError, "repository-owned source root", msg=label):
                _decide(attacked, expected_root)

    def test_stale_or_dangling_evidence_and_overlap_fail_closed(self) -> None:
        wrong_owner = canonical_case("wrong-owner")
        overlap = copy.deepcopy(wrong_owner)
        overlap["valid_work_refs"] = ["ev-local"]
        with self.assertRaisesRegex(ValueError, "valid and stale"):
            derive_selection(overlap)

        dangling = copy.deepcopy(wrong_owner)
        dangling["paths"][1]["evidence_ref_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "dangling"):
            derive_selection(dangling)

        process_trigger = copy.deepcopy(wrong_owner)
        process_trigger["evidence_refs"][0]["adjudication_posture"] = "process"
        with self.assertRaisesRegex(ValueError, "not adjudicating"):
            derive_selection(process_trigger)

        stale_fact = copy.deepcopy(wrong_owner)
        local = next(path for path in stale_fact["paths"] if path["path_id"] == "local")
        local["capability_complete"] = False
        with self.assertRaisesRegex(ValueError, "facts differ"):
            derive_selection(stale_fact)

    def test_equal_fingerprint_fast_path_rejects_stale_live_mutation(self) -> None:
        repeated = canonical_case("unchanged-repeat")
        result = decide("unchanged-repeat")
        self.assertEqual(result["disposition"], "continue-unchanged")
        self.assertTrue(result["deduplicated"])
        self.assertFalse(result["extra_cycle"])
        self.assertEqual(result["continue_to"], "block:5:remaining-work")

        mutated = copy.deepcopy(repeated)
        local = next(path for path in mutated["paths"] if path["path_id"] == "local")
        local["owner_id"] = "owner-wrong"
        local["capability_complete"] = False
        with self.assertRaisesRegex(ValueError, "repository-owned source root"):
            _decide(mutated, EXERCISE["case_source_roots"]["unchanged-repeat"])

        saved_exercise = copy.deepcopy(EXERCISE)
        try:
            source = next(
                item for item in EXERCISE["cases"]
                if item["case_id"] == "unchanged-repeat"
            )
            source["canonical_owner_id"] = "invented-owner"
            rewritten_root = case_source_root(source)
            EXERCISE["case_source_roots"]["unchanged-repeat"] = rewritten_root
            with self.assertRaisesRegex(ValueError, "exercise source root"):
                decide("unchanged-repeat")
        finally:
            EXERCISE.clear()
            EXERCISE.update(saved_exercise)

        saved_accepted = copy.deepcopy(ACCEPTED_SNAPSHOT)
        try:
            ACCEPTED_SNAPSHOT["decision_fingerprint"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "accepted decision record root"):
                decide("unchanged-repeat")
        finally:
            ACCEPTED_SNAPSHOT.clear()
            ACCEPTED_SNAPSHOT.update(saved_accepted)

    def test_top_level_control_identity_is_not_caller_rewritable(self) -> None:
        saved = copy.deepcopy(EXERCISE)
        try:
            EXERCISE["current_block"] = 999
            EXERCISE["target_revision"] = "invented-revision"
            EXERCISE["target_revision_root"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "exercise source root"):
                decide("lower-power-shortcut")
        finally:
            EXERCISE.clear()
            EXERCISE.update(saved)

    def test_continuation_identity_is_canonical_and_not_caller_selected(self) -> None:
        result = decide("lower-power-shortcut")
        self.assertEqual(result["continue_to"], "block:5:remaining-work")
        self.assertTrue(
            all(record["block_number"] == 5 for record in result["stage_records"])
        )
        self.assertEqual(
            TRACKER_RECORD_PATH,
            "/software-factory-inline-correction-target/docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md",
        )
        self.assertTrue(TRACKER_RECORD_PATH.startswith(f"{TARGET_ROOT}/"))
        self.assertNotIn(str(REPO_ROOT), result["stage_records"][0]["tracker_path"])
        with self.assertRaises((TypeError, ValueError)):
            decide(999)  # type: ignore[arg-type]

    def test_frozen_tracker_fails_closed_in_live_git_and_falls_back_only_in_archive(self) -> None:
        live = subprocess.CompletedProcess([], 0, stdout="true\n", stderr="")
        absent = subprocess.CompletedProcess([], 128, stdout=b"", stderr=b"missing")
        with mock.patch.object(subprocess, "run", side_effect=[live, absent]):
            with self.assertRaisesRegex(ValueError, "cannot be resolved"):
                tracker_sha256()

        no_repository = subprocess.CompletedProcess([], 128, stdout="", stderr="missing")
        with mock.patch.object(subprocess, "run", side_effect=[no_repository, absent]):
            self.assertEqual(tracker_sha256(), EXERCISE["tracker_sha256"])

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
        self.assertEqual(decide("requires-candidate")["disposition"], "compare-candidate")
        self.assertEqual(
            decide("requires-structural-amendment")["disposition"],
            "amend-structure",
        )


if __name__ == "__main__":
    unittest.main()
