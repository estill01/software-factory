#!/usr/bin/env python3
"""Run the bounded Block 11 adaptive-protocol dogfood evidence matrix."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
FIXTURE_PATH = SKILL_ROOT / "fixtures" / "adaptive_protocol_dogfood_v1.json"
ARCHIVE_SOURCE_REVISION = "$Format:%H$"


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
        "target_effect",
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
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        revision = completed.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", revision):
            return revision
    if re.fullmatch(r"[0-9a-f]{40}", ARCHIVE_SOURCE_REVISION):
        return ARCHIVE_SOURCE_REVISION
    raise DogfoodError("exact source revision is unavailable")


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
                "decision_state_root": (
                    records[-1]["current_target_state_root"] if records else None
                ),
                "continue_to": result["continue_to"],
                "extra_cycle": result["extra_cycle"],
                "deduplicated": result["deduplicated"],
            }
        )
    return results


def _external_inline_effect(
    target_effect: dict[str, object], inline_cases: list[dict[str, object]]
) -> dict[str, object]:
    exact_fields = {
        "schema_version",
        "kind",
        "relative_path",
        "baseline_source",
        "corrected_source",
        "expected_stdout",
    }
    if type(target_effect) is not dict or set(target_effect) != exact_fields:
        raise DogfoodError("target effect shape differs")
    if (
        type(target_effect["schema_version"]) is not int
        or target_effect["schema_version"] != 1
        or target_effect["kind"] != "software-factory-dogfood-target-effect"
    ):
        raise DogfoodError("target effect identity differs")
    by_id = {str(case["case_id"]): case for case in inline_cases}
    required = {
        "external-inline-wrong-owner": ("correct-inline", "architectural-owner"),
        "external-inline-generalized-layer": ("correct-inline", "local"),
    }
    for case_id, expected in required.items():
        observed = by_id[case_id]
        if (observed["disposition"], observed["selected_path"]) != expected:
            raise DogfoodError("inline target owner selection differs")
    baseline = str(target_effect["baseline_source"]).encode("utf-8")
    corrected = str(target_effect["corrected_source"]).encode("utf-8")
    tracker_path = REPO_ROOT / "docs" / (
        "software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
    )
    tracker_before = hashlib.sha256(tracker_path.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="software-factory-dogfood-target-") as raw:
        target_root = Path(raw)
        path = target_root / str(target_effect["relative_path"])
        path.write_bytes(baseline)
        baseline_run = subprocess.run(
            ["/usr/bin/python3", str(path)],
            cwd=target_root,
            text=True,
            capture_output=True,
        )
        path.write_bytes(corrected)
        observed = subprocess.run(
            ["/usr/bin/python3", str(path)],
            cwd=target_root,
            text=True,
            capture_output=True,
        )
        current_bytes = path.read_bytes()
    tracker_after = hashlib.sha256(tracker_path.read_bytes()).hexdigest()
    if (
        baseline_run.returncode != 0
        or observed.returncode != 0
        or observed.stdout != target_effect["expected_stdout"]
        or current_bytes != corrected
        or tracker_before != tracker_after
    ):
        raise DogfoodError("inline target effect differs")
    result = {
        "owner": "temporary-normal-target-owner",
        "relative_path": target_effect["relative_path"],
        "baseline_bytes_root": hashlib.sha256(baseline).hexdigest(),
        "corrected_bytes_root": hashlib.sha256(current_bytes).hexdigest(),
        "baseline_stdout": baseline_run.stdout,
        "observed_stdout": observed.stdout,
        "tracker_root_before": tracker_before,
        "tracker_root_after": tracker_after,
        "decision_fingerprints": [
            by_id[case_id]["decision_fingerprint"] for case_id in sorted(required)
        ],
        "application_state": "current-effect-observed",
    }
    result["target_effect_root"] = digest(result)
    return result


def _candidate_results(
    cases: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    module = load_module(
        "dogfood_candidate_contract",
        SKILL_ROOT / "scripts" / "test_bounded_candidate_contract.py",
    )
    results = []
    review_inputs = []
    for case in cases:
        index = case.get("source_case_index")
        if type(index) is not int or not 0 <= index < len(module.EXERCISE["cases"]):
            raise DogfoodError("candidate source index differs")
        source_case_id = str(module.EXERCISE["cases"][index]["case_id"])
        result = module.evaluate_unaccepted(source_case_id)
        records = result.get("stage_records", [])
        handoff = result.get("handoff")
        if result.get("blind_review_packet") is not None:
            raw_review = {
                "review_packet": result["blind_review_packet"],
                "raw_comparison_records": result["raw_comparison_records"],
            }
        elif result.get("stop_review_packet") is not None:
            raw_review = {
                "review_packet": result["stop_review_packet"],
                "stop_cause": result["stop_cause"],
            }
        else:
            raw_review = {"eligibility": result["eligibility"]}
        review_input = {
            "case_id": case["case_id"],
            "input_condition": case["input_condition"],
            "raw_evidence": raw_review,
        }
        review_input["review_input_root"] = digest(review_input)
        review_inputs.append(review_input)
        results.append(
            {
                "case_id": case["case_id"],
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
    return results, review_inputs


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


def _structural_effect() -> dict[str, object]:
    module = load_module(
        "dogfood_program_revision_control",
        REPO_ROOT
        / "supervise-tracker-runs"
        / "scripts"
        / "test_program_revision_control.py",
    )
    case_owner = module.ProgramRevisionControlTests(
        methodName="test_accepted_revision_maps_full_range_and_resumes_dependency_safe_block"
    )
    case_owner.setUp()
    try:
        previous = case_owner.fixture.tracker_path.read_bytes()
        accepted = case_owner.record_program_revision()
        application_commit = case_owner.apply_proposal()
        amended = case_owner.range_amend(
            str(accepted["record"]["record_id"]), application_commit
        )
        current = case_owner.fixture.tracker_path.read_bytes()
        program = amended["program_revision"]
        if (
            accepted["record"]["review_disposition"] != "accepted"
            or amended["duplicate"]
            or amended["contraction"]
            or current == previous
            or program["next_action"]
            != "resume-block-7-without-user-scheduling"
        ):
            raise DogfoodError("structural target effect differs")
        result = {
            "owner": "temporary-program-revision-owner",
            "revision_id": accepted["record"]["revision_id"],
            "review_root": accepted["record"]["review_root"],
            "application_commit": application_commit,
            "previous_tracker_root": hashlib.sha256(previous).hexdigest(),
            "current_tracker_root": hashlib.sha256(current).hexdigest(),
            "resume_block": program["resume_block"],
            "next_action": program["next_action"],
            "tracker_blocks": amended["binding"]["tracker_blocks"],
            "application_state": "reviewed-delta-applied-and-resume-current",
        }
        result["structural_effect_root"] = digest(result)
        return result
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
        ordinary = next(
            item for item in results if item["case_id"] == "full-autonomous-ordinary"
        )
        if (
            ordinary["application_posture"] != "owner-application-ready"
            or not ordinary["application_ready"]
            or ordinary["human_request_count"] != 0
        ):
            raise DogfoodError("ordinary full-autonomous posture differs")
        target_path = case_owner.owned_path
        previous = target_path.read_bytes()
        target_path.write_text("VALUE = 2\n", encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                case_owner.repository_root,
                "add",
                target_path.name,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                case_owner.repository_root,
                "commit",
                "-q",
                "-m",
                "Apply ordinary owner correction",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        observed = subprocess.run(
            [
                "/usr/bin/python3",
                "-c",
                "import runpy; print(runpy.run_path('owned.py')['VALUE'])",
            ],
            cwd=case_owner.repository_root,
            text=True,
            capture_output=True,
        )
        current = target_path.read_bytes()
        if observed.returncode != 0 or observed.stdout != "2\n" or current == previous:
            raise DogfoodError("ordinary full-autonomous current effect differs")
        ordinary["resolution"] = {
            "owner": "temporary-normal-target-owner",
            "previous_bytes_root": hashlib.sha256(previous).hexdigest(),
            "current_bytes_root": hashlib.sha256(current).hexdigest(),
            "observed_stdout": observed.stdout,
            "target_revision": subprocess.run(
                [
                    "/usr/bin/git",
                    "-C",
                    case_owner.repository_root,
                    "rev-parse",
                    "HEAD",
                ],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip(),
            "resolution_state": "current-effect-observed",
        }
        ordinary["resolution"]["current_effect_root"] = digest(
            ordinary["resolution"]
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
    inline_results = _inline_results(grouped["inline-correction"])
    candidate_results, candidate_review_inputs = _candidate_results(
        grouped["bounded-candidate"]
    )
    result = {
        "schema_version": 1,
        "kind": "software-factory-adaptive-protocol-dogfood-result",
        "source_revision": source_revision(),
        "fixture_root": digest(fixture),
        "blind_candidate_review_inputs": candidate_review_inputs,
        "inline_cases": inline_results,
        "inline_target_effect": _external_inline_effect(
            fixture["target_effect"], inline_results
        ),
        "candidate_cases": candidate_results,
        "target_class_cases": _target_class_results(grouped["target-class-protocol"]),
        "structural_target_effect": _structural_effect(),
        "authority_cases": _authority_results(grouped["adaptive-decision-policy"]),
        "recovery_checks": _recovery_results(fixture["recovery_checks"]),
        "external_effects_performed": False,
        "temporary_target_effects_performed": True,
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
