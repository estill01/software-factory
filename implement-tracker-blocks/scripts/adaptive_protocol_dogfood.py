#!/usr/bin/env python3
"""Run the bounded Block 11 adaptive-protocol dogfood evidence matrix."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
FIXTURE_PATH = SKILL_ROOT / "fixtures" / "adaptive_protocol_dogfood_v1.json"


class DogfoodError(RuntimeError):
    """Raised when the bounded dogfood input or result is inconsistent."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DogfoodError(f"cannot load maintained checkpoint: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_fixture() -> dict[str, object]:
    value = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if type(value) is not dict or set(value) != {
        "schema_version",
        "kind",
        "cases",
        "recovery_checks",
    }:
        raise DogfoodError("dogfood fixture shape differs")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "software-factory-adaptive-protocol-dogfood"
    ):
        raise DogfoodError("dogfood fixture identity differs")
    cases = value["cases"]
    if type(cases) is not list or not cases:
        raise DogfoodError("dogfood cases are absent")
    case_ids = [case.get("case_id") for case in cases if type(case) is dict]
    if len(case_ids) != len(cases) or len(set(case_ids)) != len(case_ids):
        raise DogfoodError("dogfood case identity is absent or duplicated")
    forbidden = {"expected_disposition", "intended_disposition", "expected_action"}
    if any(forbidden.intersection(case) for case in cases):
        raise DogfoodError("dogfood cases disclose an intended disposition")
    return value


def source_revision() -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _inline_results(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    module = load_module(
        "dogfood_inline_contract",
        SKILL_ROOT / "scripts" / "test_inline_correction_contract.py",
    )
    results = []
    for case in cases:
        result = module.decide(str(case["source_case_id"]))
        records = result["stage_records"]
        results.append(
            {
                "case_id": case["case_id"],
                "input_condition": case["input_condition"],
                "disposition": result["disposition"],
                "selected_path": result["selected_path"],
                "decision_fingerprint": result["decision_fingerprint"],
                "decision_stages": result["decision_stages"],
                "current_effect_root": (
                    records[-1]["current_target_state_root"] if records else None
                ),
                "continue_to": result["continue_to"],
                "extra_cycle": result["extra_cycle"],
                "deduplicated": result["deduplicated"],
            }
        )
    return results


def _candidate_results(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    module = load_module(
        "dogfood_candidate_contract",
        SKILL_ROOT / "scripts" / "test_bounded_candidate_contract.py",
    )
    results = []
    for case in cases:
        result = module.evaluate_unaccepted(str(case["source_case_id"]))
        records = result.get("stage_records", [])
        handoff = result.get("handoff")
        results.append(
            {
                "case_id": case["case_id"],
                "input_condition": case["input_condition"],
                "action": result["action"],
                "lane_created": result["lane_created"],
                "review_cycle": result["review_cycle"],
                "stop_reason": result.get("stop_reason"),
                "terminal_stage": (
                    records[-1]["decision_stage"] if records else None
                ),
                "resource_usage": result.get("resource_usage"),
                "candidate_authoritative": result.get("candidate_authoritative"),
                "incumbent_authoritative": result.get("incumbent_authoritative"),
                "isolation_cleanup": result.get("isolation_cleanup"),
                "handoff_root": handoff.get("handoff_root") if handoff else None,
                "cutover_performed": result.get("cutover_performed", False),
                "tracker_mutated": result.get("tracker_mutated", False),
                "policy_mutated": result.get("policy_mutated", False),
                "evidence_root": digest(result),
            }
        )
    first = module.evaluate("winning-candidate")
    second = module.evaluate("winning-candidate")
    if first != second:
        raise DogfoodError("accepted candidate replay is not deterministic")
    results.append(
        {
            "case_id": "candidate-accepted-replay",
            "input_condition": "The exact accepted candidate lane is delivered again.",
            "action": first["action"],
            "lane_created": first["lane_created"],
            "review_cycle": first["review_cycle"],
            "candidate_authoritative": first["candidate_authoritative"],
            "incumbent_authoritative": first["incumbent_authoritative"],
            "existing_handoff_root": first["existing_handoff_root"],
            "next_action": first["next_action"],
            "replay_root": digest(first),
        }
    )
    return results


def _target_class_results(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    module = load_module(
        "dogfood_target_class_contract",
        SKILL_ROOT / "scripts" / "test_target_class_protocol_contract.py",
    )
    case_owner = module.TargetClassProtocolTests(
        methodName="test_same_protocol_covers_all_paths_for_both_target_classes"
    )
    case_owner.setUp()
    try:
        results = []
        for case in cases:
            packet, event = case_owner.packet(
                str(case["target_class"]), str(case["source_case_id"])
            )
            result = case_owner.validate(packet)
            results.append(
                {
                    "case_id": case["case_id"],
                    "input_condition": case["input_condition"],
                    "target_class": result["target_class"],
                    "disposition": result["disposition"],
                    "decision_record_id": result["decision_record_id"],
                    "protocol_root": result["protocol_root"],
                    "improvement_established": result["improvement_established"],
                    "adoption_eligible": result["adoption_eligible"],
                    "application_authorized": result["application_authorized"],
                    "application_handoff_root": result["application_handoff_root"],
                    "resume_action": result["resume_action"],
                    "next_owner": result["next_owner"],
                    "human_request_count": event["human_request_count"],
                    "tracker_mutated": False,
                    "global_configuration_mutated": False,
                }
            )
        return results
    finally:
        case_owner.doCleanups()


def _authority_results(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    module = load_module(
        "dogfood_adaptive_policy_contract",
        REPO_ROOT
        / "supervise-tracker-runs"
        / "scripts"
        / "test_adaptive_decision_policy.py",
    )
    case_owner = module.AdaptiveDecisionPolicyTests(
        methodName="test_full_autonomy_never_routes_ordinary_judgment_to_a_human"
    )
    case_owner.setUp()
    try:
        policy = case_owner.policy()
        results = []
        for case in cases:
            if case["source_case_id"] == "reserved-external":
                evidence = case_owner.decision_evidence(
                    judgment_class="reserved-external",
                    blocked_subjects=["credential-boundary"],
                    revisit_trigger="Credential authority becomes current.",
                )
                packet = case_owner.packet(policy, evidence=evidence)
            else:
                packet = case_owner.packet(policy)
            result = case_owner.posture(policy, packet)
            results.append(
                {
                    "case_id": case["case_id"],
                    "input_condition": case["input_condition"],
                    "application_posture": result["application_posture"],
                    "application_authorized": result["application_authorized"],
                    "application_ready": result["application_ready"],
                    "human_request_count": result["human_request_count"],
                    "safe_frontier": result["safe_frontier"],
                    "blocked_subjects": result["blocked_subjects"],
                    "revisit_trigger": result["revisit_trigger"],
                }
            )
        return results
    finally:
        case_owner.doCleanups()


def _recovery_results(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    for index, check in enumerate(checks):
        module_path = str(check["module"])
        method = str(check["method"])
        class_name = str(check["class"])
        completed = subprocess.run(
            [
                "/usr/bin/python3",
                str(REPO_ROOT / module_path),
                f"{class_name}.{method}",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        report = completed.stdout + completed.stderr
        if (
            completed.returncode != 0
            or "Ran 1 test" not in report
            or "OK" not in report
        ):
            raise DogfoodError(
                f"maintained recovery check failed: {module_path}:{method}"
            )
        results.append(
            {
                "check_id": f"recovery-{index + 1:02d}",
                "module": module_path,
                "method": method,
                "tests_run": 1,
                "result": "passed",
            }
        )
    return results


def run_dogfood() -> dict[str, object]:
    fixture = load_fixture()
    cases = fixture["cases"]
    assert isinstance(cases, list)
    grouped = {
        owner: [case for case in cases if case["owner"] == owner]
        for owner in {
            "inline-correction",
            "bounded-candidate",
            "target-class-protocol",
            "adaptive-decision-policy",
        }
    }
    result = {
        "schema_version": 1,
        "kind": "software-factory-adaptive-protocol-dogfood-result",
        "source_revision": source_revision(),
        "fixture_root": digest(fixture),
        "inline_cases": _inline_results(grouped["inline-correction"]),
        "candidate_cases": _candidate_results(grouped["bounded-candidate"]),
        "target_class_cases": _target_class_results(grouped["target-class-protocol"]),
        "authority_cases": _authority_results(grouped["adaptive-decision-policy"]),
        "recovery_checks": _recovery_results(fixture["recovery_checks"]),
        "external_effects_performed": False,
        "release_mutated": False,
        "policy_mutated": False,
        "mission_mutated": False,
        "lifecycle_mutated": False,
    }
    result["human_request_count"] = sum(
        int(case["human_request_count"])
        for case in result["target_class_cases"] + result["authority_cases"]
    )
    result["result_root"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded read-only adaptive-protocol dogfood matrix."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="indent the result JSON"
    )
    args = parser.parse_args()
    result = run_dogfood()
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
