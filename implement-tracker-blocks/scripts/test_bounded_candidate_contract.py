#!/usr/bin/env python3
"""Evidence-bound behavior for one selective bounded candidate lane."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
TRACKER_PATH = REPO_ROOT / "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL_ROOT / "references/bounded-candidate-lane.md").read_text(encoding="utf-8")
ADAPTIVE = (SKILL_ROOT / "references/adaptive-decision-control.md").read_text(encoding="utf-8")
SPEC = json.loads(ADAPTIVE.split("<!-- contract-spec-v1 -->", 1)[1].split("```json", 1)[1].split("```", 1)[0])
EXERCISE = json.loads((SKILL_ROOT / "fixtures/bounded_candidate_v1.json").read_text(encoding="utf-8"))
REVIEW_FIXTURE = json.loads((SKILL_ROOT / "fixtures/bounded_candidate_reviews_v1.json").read_text(encoding="utf-8"))

EXPECTED_EXERCISE_ROOT = "17d076a11041a4ec5e82f0fa17f81c726178da3cf11d68435808606989b496dc"
EXPECTED_REVIEW_FIXTURE_ROOT = "a033723e885c838f94d29f5aa5149ca33127e58b13d4b8a708cd4f9bba13694e"
GIT_EXECUTABLE = "/usr/bin/git"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
DIMENSIONS = [
    "observable-outcome",
    "implementation-cost",
    "maintenance-cost",
    "reversibility",
    "compatibility",
    "protected-capability",
]
RELATIONS = {"candidate-better", "incumbent-better", "equivalent", "inconclusive"}
COMPARISON_DISPOSITIONS = {"candidate-better", "incumbent-better", "non-inferior-no-benefit", "inconclusive"}
BLOCK4_REVIEW = {
    "candidate-better": "accepted",
    "incumbent-better": "accepted",
    "non-inferior-no-benefit": "accepted",
    "inconclusive": "inconclusive",
}
RETIREMENT = {
    "candidate-better": "eligible-cutover",
    "incumbent-better": "retired-loser",
    "non-inferior-no-benefit": "retired-loser",
    "inconclusive": "retired-inconclusive",
}
ELIGIBILITY_FIELDS = {
    "outcome_uncertainty_supported",
    "outcome_uncertainty_evidence_root",
    "implementation_evidence_required",
    "implementation_evidence_root",
    "read_only_resolvable",
    "rework_avoided_minutes",
    "candidate_ceiling_minutes",
    "review_ceiling_minutes",
    "isolation_recovery_minutes",
    "reversibility_posture",
    "reversibility_evidence_root",
    "isolation_safe",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def root(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_root(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def exact_string(value: object, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value or (pattern is not None and pattern.fullmatch(value) is None):
        raise ValueError(f"{label} differs")
    return value


def exact_int(value: object, label: str, *, minimum: int = 0, maximum: int = 100000000) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ValueError(f"{label} differs")
    return value


def exact_path(value: object, label: str, *, contained_by: str | None = None) -> str:
    path = exact_string(value, label)
    pure = PurePosixPath(path)
    if not pure.is_absolute() or any(part in {".", ".."} for part in pure.parts) or str(pure) != path:
        raise ValueError(f"{label} is not canonical")
    if contained_by is not None:
        container = PurePosixPath(contained_by)
        try:
            pure.relative_to(container)
        except ValueError as error:
            raise ValueError(f"{label} escapes owner") from error
    return path


def validate_scope_refs(value: object, label: str, *, contained_by: str, min_items: int) -> list[dict[str, object]]:
    if type(value) is not list or len(value) < min_items:
        raise ValueError(f"{label} differs")
    if len({canonical(item) for item in value}) != len(value):
        raise ValueError(f"{label} contains duplicates")
    for item in value:
        if type(item) is not dict or set(item) != {"owner_id", "path", "content_root"}:
            raise ValueError(f"{label} shape differs")
        exact_string(item["owner_id"], f"{label} owner", ID_RE)
        exact_path(item["path"], f"{label} path", contained_by=contained_by)
        exact_string(item["content_root"], f"{label} root", SHA_RE)
    return value


def tracker_sha256() -> str:
    relative = TRACKER_PATH.relative_to(REPO_ROOT).as_posix()
    probe = subprocess.run([GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"], cwd=REPO_ROOT, capture_output=True, text=True)
    frozen = subprocess.run([GIT_EXECUTABLE, "show", f"{EXERCISE['tracker_source_revision']}:{relative}"], cwd=REPO_ROOT, capture_output=True)
    if frozen.returncode == 0:
        return hashlib.sha256(frozen.stdout).hexdigest()
    if probe.returncode == 0:
        raise ValueError("frozen tracker source cannot be resolved in live repository")
    return exact_string(EXERCISE["tracker_sha256"], "archive tracker root", SHA_RE)


def file_manifest(files: object, *, contained_by: str) -> list[dict[str, str]]:
    if type(files) is not list or not files:
        raise ValueError("artifact files differ")
    result: list[dict[str, str]] = []
    for item in files:
        if type(item) is not dict or set(item) != {"path", "content_utf8"}:
            raise ValueError("artifact file shape differs")
        path = exact_path(item["path"], "artifact path", contained_by=contained_by)
        content = exact_string(item["content_utf8"], "artifact bytes")
        result.append({"path": path, "content_sha256": bytes_root(content)})
    result.sort(key=lambda item: item["path"])
    if len({item["path"] for item in result}) != len(result):
        raise ValueError("artifact path is duplicated")
    return result


def artifact_root(artifact: dict[str, object]) -> str:
    revision = exact_string(artifact["revision"], "candidate revision", REV_RE)
    return root({"revision": revision, "files": file_manifest(artifact["files"], contained_by=EXERCISE["lane"]["root"])})


def incumbent_root() -> str:
    incumbent = EXERCISE["incumbent"]
    revision = exact_string(incumbent["revision"], "incumbent revision", REV_RE)
    return root({"revision": revision, "files": file_manifest(incumbent["files"], contained_by=EXERCISE["target_repository_root"])})


def target_revision_root() -> str:
    return root({"target_repository_root": EXERCISE["target_repository_root"], "target_revision": EXERCISE["target_revision"], "incumbent_root": incumbent_root()})


def parse_time(value: object, label: str) -> datetime:
    raw = exact_string(value, label)
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ValueError(f"{label} differs") from error
    return parsed


def result_id(prefix: str, candidate_root: str) -> str:
    return f"{prefix}-{candidate_root[:20]}"


def focused_result(artifact: dict[str, object], candidate_root: str) -> dict[str, object]:
    value = artifact["focused"]
    if type(value) is not dict or set(value) != {"recorded_at", "command", "exit_code", "output", "protected_result"}:
        raise ValueError("focused result shape differs")
    result = {
        "schema_version": 1,
        "kind": "software-factory-candidate-focused-result",
        "result_id": result_id("focused", candidate_root),
        "candidate_root": candidate_root,
        "recorded_at": exact_string(value["recorded_at"], "focused time"),
        "command": exact_string(value["command"], "focused command"),
        "exit_code": exact_int(value["exit_code"], "focused exit", maximum=255),
        "output_sha256": bytes_root(exact_string(value["output"], "focused output")),
        "protected_result": exact_string(value["protected_result"], "protected result"),
    }
    parse_time(result["recorded_at"], "focused time")
    result["result_root"] = root(result)
    return result


def validate_metrics(metrics: object) -> dict[str, object]:
    if type(metrics) is not dict or list(metrics) != DIMENSIONS:
        raise ValueError("mapped metrics differ")
    outcome = metrics["observable-outcome"]
    if type(outcome) is not dict or set(outcome) != {"output_sha256", "peak_memory_bytes"}:
        raise ValueError("observable metric differs")
    exact_string(outcome["output_sha256"], "observable output", SHA_RE)
    if outcome["peak_memory_bytes"] is not None:
        exact_int(outcome["peak_memory_bytes"], "peak memory", minimum=1)
    for dimension, field in (
        ("implementation-cost", "changed_lines"),
        ("maintenance-cost", "decision_points"),
        ("reversibility", "restore_steps"),
        ("compatibility", "api_breaks"),
    ):
        value = metrics[dimension]
        if type(value) is not dict or set(value) != {field}:
            raise ValueError(f"{dimension} metric differs")
        exact_int(value[field], dimension)
    protected = metrics["protected-capability"]
    if type(protected) is not dict or set(protected) != {"regressions"} or type(protected["regressions"]) is not list:
        raise ValueError("protected metric differs")
    if any(type(item) is not str or not item for item in protected["regressions"]):
        raise ValueError("protected regression differs")
    return metrics


def mapped_result(artifact: dict[str, object], candidate_root: str, focused: dict[str, object]) -> dict[str, object] | None:
    value = artifact["mapped"]
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"recorded_at", "command", "exit_code", "output", "metrics"}:
        raise ValueError("mapped result shape differs")
    metrics = value["metrics"]
    if metrics is not None:
        validate_metrics(metrics)
    result = {
        "schema_version": 1,
        "kind": "software-factory-candidate-mapped-result",
        "result_id": result_id("mapped", candidate_root),
        "candidate_root": candidate_root,
        "incumbent_root": incumbent_root(),
        "focused_result_root": focused["result_root"],
        "recorded_at": exact_string(value["recorded_at"], "mapped time"),
        "command": exact_string(value["command"], "mapped command"),
        "exit_code": exact_int(value["exit_code"], "mapped exit", maximum=255),
        "output_sha256": bytes_root(exact_string(value["output"], "mapped output")),
        "metrics": metrics,
    }
    if parse_time(result["recorded_at"], "mapped time") <= parse_time(focused["recorded_at"], "focused time"):
        raise ValueError("mapped result does not follow frozen focused proof")
    result["result_root"] = root(result)
    return result


def validate_exercise() -> None:
    if root(EXERCISE) != EXPECTED_EXERCISE_ROOT or root(REVIEW_FIXTURE) != EXPECTED_REVIEW_FIXTURE_ROOT:
        raise ValueError("bounded candidate source root differs")
    if type(EXERCISE["schema_version"]) is not int or EXERCISE["schema_version"] != 2 or EXERCISE["kind"] != "software-factory-bounded-candidate-exercise" or type(EXERCISE["block_number"]) is not int or EXERCISE["block_number"] != 6:
        raise ValueError("bounded candidate identity differs")
    exact_string(EXERCISE["tracker_source_revision"], "tracker source revision", REV_RE)
    if EXERCISE["tracker_sha256"] != tracker_sha256():
        raise ValueError("tracker source root is stale")
    for key in ("mission_root", "policy_root", "event_head_root", "block_contract_root"):
        exact_string(EXERCISE[key], key, SHA_RE)
    target_root = exact_path(EXERCISE["target_repository_root"], "target repository root")
    exact_string(EXERCISE["target_revision"], "target revision", REV_RE)
    contract = EXERCISE["capability_contract"]
    if type(contract) is not dict or set(contract) != {"statement", "protected_capabilities", "expected_observable_effect", "success_criteria", "cleanup_retention_posture"}:
        raise ValueError("capability contract differs")
    for key in ("statement", "expected_observable_effect", "cleanup_retention_posture"):
        exact_string(contract[key], f"capability {key}")
    for key in ("protected_capabilities", "success_criteria"):
        values = contract[key]
        if type(values) is not list or not values or values != sorted(set(values)) or any(type(item) is not str or not item for item in values):
            raise ValueError(f"capability {key} differs")
    lane = EXERCISE["lane"]
    exact_path(lane["root"], "lane root")
    if lane["isolation_kind"] not in SPEC["enums"]["isolation-kind"]:
        raise ValueError("isolation kind differs")
    for key in ("implementation_owner_id", "independent_reviewer_id", "cutover_owner_id"):
        exact_string(lane[key], key, ID_RE)
    if lane["implementation_owner_id"] != EXERCISE["incumbent"]["production_authority_owner_id"] or lane["independent_reviewer_id"] in {lane["implementation_owner_id"], lane["cutover_owner_id"]}:
        raise ValueError("candidate roles differ")
    ceiling = lane["resource_ceiling"]
    if type(ceiling) is not dict or set(ceiling) != {"max_files", "max_changed_lines", "max_commands", "max_review_passes"}:
        raise ValueError("resource ceiling differs")
    for key, maximum in (("max_files", 100), ("max_changed_lines", 10000), ("max_commands", 100), ("max_review_passes", 10)):
        exact_int(ceiling[key], key, minimum=1, maximum=maximum)
    exact_int(lane["time_ceiling_minutes"], "time ceiling", minimum=1, maximum=120)
    exact_string(lane["stop_condition"], "stop condition")
    validate_scope_refs(EXERCISE["hypothesis_scope"], "hypothesis scope", contained_by=target_root, min_items=1)
    validate_scope_refs(lane["isolated_writable_scope"], "isolated scope", contained_by=lane["root"], min_items=1)
    validate_scope_refs(lane["shared_resource_exclusions"], "shared exclusions", contained_by=target_root, min_items=0)
    production = set(EXERCISE["incumbent"]["writable_scope"])
    excluded = {item["path"] for item in lane["shared_resource_exclusions"]}
    isolated = {item["path"] for item in lane["isolated_writable_scope"]}
    if production.intersection(isolated) or not production.issubset(excluded):
        raise ValueError("candidate isolation overlaps production authority")
    exact_string(EXERCISE["hypothesis"], "hypothesis")
    if EXERCISE["comparison_dimensions"] != DIMENSIONS:
        raise ValueError("comparison dimension order differs")
    validate_metrics(EXERCISE["incumbent"]["metrics"])
    incumbent_root()
    artifacts = EXERCISE["artifacts"]
    if type(artifacts) is not dict or not artifacts:
        raise ValueError("candidate artifacts differ")
    for artifact in artifacts.values():
        candidate = artifact_root(artifact)
        focused = focused_result(artifact, candidate)
        mapped_result(artifact, candidate, focused)
    if type(EXERCISE["cases"]) is not list or len({case["case_id"] for case in EXERCISE["cases"]}) != len(EXERCISE["cases"]):
        raise ValueError("case identity differs")


def case_index() -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in EXERCISE["cases"]}


def canonical_case(case_id: str) -> dict[str, object]:
    validate_exercise()
    try:
        return copy.deepcopy(case_index()[case_id])
    except KeyError as error:
        raise ValueError("candidate case is absent") from error


def eligibility(case: dict[str, object]) -> dict[str, object]:
    override = case["eligibility"]
    if type(override) is not dict or not set(override).issubset(ELIGIBILITY_FIELDS):
        raise ValueError("eligibility override differs")
    value = {**EXERCISE["eligibility_default"], **override}
    if set(value) != ELIGIBILITY_FIELDS:
        raise ValueError("eligibility fields differ")
    for key in ("outcome_uncertainty_supported", "implementation_evidence_required", "read_only_resolvable", "isolation_safe"):
        if type(value[key]) is not bool:
            raise ValueError(f"eligibility {key} differs")
    for key in ("outcome_uncertainty_evidence_root", "implementation_evidence_root", "reversibility_evidence_root"):
        exact_string(value[key], key, SHA_RE)
    for key in ("rework_avoided_minutes", "candidate_ceiling_minutes", "review_ceiling_minutes", "isolation_recovery_minutes"):
        exact_int(value[key], key, maximum=120)
    if value["candidate_ceiling_minutes"] != EXERCISE["lane"]["time_ceiling_minutes"]:
        raise ValueError("eligibility candidate ceiling differs")
    if value["reversibility_posture"] != "checkpoint-restore":
        raise ValueError("eligibility reversibility differs")
    value["bounded_cost_minutes"] = value["candidate_ceiling_minutes"] + value["review_ceiling_minutes"] + value["isolation_recovery_minutes"]
    value["net_avoidable_minutes"] = value["rework_avoided_minutes"] - value["bounded_cost_minutes"]
    value["eligibility_root"] = root(value)
    return value


def lane_eligible(value: dict[str, object]) -> bool:
    return bool(value["outcome_uncertainty_supported"] and value["implementation_evidence_required"] and not value["read_only_resolvable"] and value["isolation_safe"] and value["net_avoidable_minutes"] > 0)


def candidate_root_for(case: dict[str, object]) -> tuple[dict[str, object], str]:
    artifact_id = case["artifact_id"]
    if type(artifact_id) is not str or artifact_id not in EXERCISE["artifacts"]:
        raise ValueError("candidate artifact is absent")
    artifact = EXERCISE["artifacts"][artifact_id]
    return artifact, artifact_root(artifact)


def decision_basis(case: dict[str, object], eligible: dict[str, object]) -> dict[str, object]:
    contract = EXERCISE["capability_contract"]
    incumbent = EXERCISE["incumbent"]
    return {
        "tracker_sha256": EXERCISE["tracker_sha256"],
        "block_contract_root": EXERCISE["block_contract_root"],
        "target_repository_root": EXERCISE["target_repository_root"],
        "target_revision": EXERCISE["target_revision"],
        "target_revision_root": target_revision_root(),
        "incumbent_revision": incumbent["revision"],
        "incumbent_root": incumbent_root(),
        "hypothesis": EXERCISE["hypothesis"],
        "hypothesis_scope": EXERCISE["hypothesis_scope"],
        "capability_contract": contract,
        "expected_observable_effect": contract["expected_observable_effect"],
        "comparison_dimensions": DIMENSIONS,
        "eligibility_root": eligible["eligibility_root"],
        "isolation": EXERCISE["lane"],
    }


def source_evidence(case: dict[str, object], eligible: dict[str, object]) -> list[dict[str, object]]:
    refs = [
        {"ref_id": "evidence-capability", "source_class": "tracker", "adjudication_posture": "adjudicating", "root_sha256": root(EXERCISE["capability_contract"]), "claim_ids": ["capability-contract", "protected-contract"]},
        {"ref_id": "evidence-eligibility", "source_class": "repository", "adjudication_posture": "adjudicating", "root_sha256": eligible["eligibility_root"], "claim_ids": ["implementation-evidence-required", "positive-decision-value", "reversibility-bound"]},
        {"ref_id": "evidence-incumbent", "source_class": "repository", "adjudication_posture": "adjudicating", "root_sha256": incumbent_root(), "claim_ids": ["incumbent-authoritative", "incumbent-revision"]},
    ]
    return sorted(refs, key=lambda item: item["ref_id"])


def fingerprint_projection(case: dict[str, object], eligible: dict[str, object]) -> dict[str, object]:
    evidence = source_evidence(case, eligible)
    scope = copy.deepcopy(EXERCISE["hypothesis_scope"])
    paths = [
        {"path_id": "incumbent-local", "kind": "local", "posture": "rejected", "rationale": "read-only evidence cannot decide", "evidence_ref_ids": ["evidence-incumbent"]},
        {"path_id": "bounded-candidate", "kind": "bounded-general", "posture": "selected", "rationale": "one isolated implementation supplies the missing evidence", "evidence_ref_ids": ["evidence-capability", "evidence-eligibility"]},
        {"path_id": "generalized-service", "kind": "architectural-owner", "posture": "rejected", "rationale": "unsupported generalized experiment infrastructure", "evidence_ref_ids": ["evidence-capability"]},
    ]
    basis = decision_basis(case, eligible)
    values = {
        "schema_version": 1,
        "mission_root": EXERCISE["mission_root"],
        "authority_effect": "none",
        "authority_claim_id": None,
        "authority_evidence_refs": [],
        "prior_mission_root": EXERCISE["mission_root"],
        "proposed_mission_root": None,
        "tracker_path": f"{EXERCISE['target_repository_root']}/BLOCK.md",
        "block_number": 6,
        "block_contract_root": EXERCISE["block_contract_root"],
        "target_class": "target-repository",
        "target_repository_root": EXERCISE["target_repository_root"],
        "decision_target_state_root": root(basis),
        "capability_statement": EXERCISE["capability_contract"]["statement"],
        "capability_frame_root": root(EXERCISE["capability_contract"]),
        "protected_capability_results": [{"capability_id": item, "result": "preserved", "evidence_ref_ids": ["evidence-capability"]} for item in EXERCISE["capability_contract"]["protected_capabilities"]],
        "adjudicating_evidence_ref_ids": [item["ref_id"] for item in evidence],
        "adjudicating_evidence_root": root(evidence),
        "compared_paths": paths,
        "affected_scope": scope,
        "proposer_author_id": None,
        "implementation_owner_id": EXERCISE["lane"]["implementation_owner_id"],
        "stop_boundary": "before Block 9 cutover, tracker amendment, policy change, publication, or external release",
    }
    if set(values) != set(SPEC["fingerprint_projection"]):
        raise ValueError("fingerprint projection differs from Block 4")
    return values


def decision_fingerprint(case: dict[str, object], eligible: dict[str, object]) -> str:
    return root(fingerprint_projection(case, eligible))


def metric_relation(dimension: str, incumbent: dict[str, object], candidate: dict[str, object]) -> tuple[str, str]:
    if dimension == "observable-outcome":
        if candidate["output_sha256"] != incumbent["output_sha256"]:
            return "incumbent-better", "bytes-and-peak-memory"
        if candidate["peak_memory_bytes"] is None:
            return "inconclusive", "bytes-and-peak-memory"
        if candidate["peak_memory_bytes"] < incumbent["peak_memory_bytes"]:
            return "candidate-better", "bytes-and-peak-memory"
        if candidate["peak_memory_bytes"] > incumbent["peak_memory_bytes"]:
            return "incumbent-better", "bytes-and-peak-memory"
        return "equivalent", "bytes-and-peak-memory"
    field = {"implementation-cost": "changed_lines", "maintenance-cost": "decision_points", "reversibility": "restore_steps", "compatibility": "api_breaks"}.get(dimension)
    if field is not None:
        left, right = incumbent[field], candidate[field]
        relation = "candidate-better" if right < left else "incumbent-better" if right > left else "equivalent"
        return relation, field
    left = incumbent["regressions"]
    right = candidate["regressions"]
    relation = "candidate-better" if len(right) < len(left) else "incumbent-better" if len(right) > len(left) else "equivalent"
    return relation, "regression-count"


def comparison_records(mapped: dict[str, object]) -> list[dict[str, object]]:
    if mapped["exit_code"] != 0 or mapped["metrics"] is None:
        raise ValueError("mapped comparison is not coherent")
    incumbent_metrics = EXERCISE["incumbent"]["metrics"]
    candidate_metrics = mapped["metrics"]
    records: list[dict[str, object]] = []
    for dimension in DIMENSIONS:
        relation, unit = metric_relation(dimension, incumbent_metrics[dimension], candidate_metrics[dimension])
        if relation not in RELATIONS:
            raise ValueError("comparison relation differs")
        records.append({
            "dimension": dimension,
            "unit": unit,
            "incumbent_evidence_root": root({"incumbent_root": incumbent_root(), "dimension": dimension, "value": incumbent_metrics[dimension]}),
            "candidate_evidence_root": root({"candidate_root": mapped["candidate_root"], "mapped_result_root": mapped["result_root"], "dimension": dimension, "value": candidate_metrics[dimension]}),
            "incumbent_value": copy.deepcopy(incumbent_metrics[dimension]),
            "candidate_value": copy.deepcopy(candidate_metrics[dimension]),
            "relation": relation,
        })
    validate_comparison(records)
    return records


def validate_comparison(records: object) -> None:
    if type(records) is not list or [item.get("dimension") for item in records if type(item) is dict] != DIMENSIONS:
        raise ValueError("comparison dimensions differ")
    exact = {"dimension", "unit", "incumbent_evidence_root", "candidate_evidence_root", "incumbent_value", "candidate_value", "relation"}
    for record in records:
        if type(record) is not dict or set(record) != exact:
            raise ValueError("comparison record shape differs")
        exact_string(record["unit"], "comparison unit")
        exact_string(record["incumbent_evidence_root"], "incumbent evidence", SHA_RE)
        exact_string(record["candidate_evidence_root"], "candidate evidence", SHA_RE)
        if record["relation"] not in RELATIONS:
            raise ValueError("comparison relation differs")


def blind_review_packet(candidate_root: str, mapped: dict[str, object], comparison: list[dict[str, object]]) -> dict[str, object]:
    packet = {
        "schema_version": 1,
        "kind": "software-factory-bounded-candidate-blind-review-input",
        "target_revision_root": target_revision_root(),
        "incumbent_root": incumbent_root(),
        "candidate_root": candidate_root,
        "focused_result_root": mapped["focused_result_root"],
        "mapped_result_root": mapped["result_root"],
        "comparison_root": root(comparison),
        "comparison_dimensions": DIMENSIONS,
        "capability_frame_root": root(EXERCISE["capability_contract"]),
        "protected_capabilities": EXERCISE["capability_contract"]["protected_capabilities"],
    }
    if any(key in packet for key in ("expected_action", "expected_comparison_disposition", "implementer_preference", "case_id")):
        raise ValueError("blind review input leaks implementer preference")
    return packet


def review_fixture_result(case_id: str, packet: dict[str, object], comparison: list[dict[str, object]]) -> dict[str, object]:
    entries = [item for item in REVIEW_FIXTURE["results"] if item["case_id"] == case_id]
    if len(entries) != 1 or REVIEW_FIXTURE["reviewer_id"] != EXERCISE["lane"]["independent_reviewer_id"]:
        raise ValueError("independent review fixture differs")
    entry = entries[0]
    disposition = entry["comparison_disposition"]
    if disposition not in COMPARISON_DISPOSITIONS:
        raise ValueError("comparison disposition differs")
    relations = {item["dimension"]: item["relation"] for item in comparison}
    if disposition == "candidate-better" and (relations["observable-outcome"] != "candidate-better" or relations["compatibility"] == "incumbent-better" or relations["protected-capability"] == "incumbent-better"):
        raise ValueError("candidate-better is unsupported by raw comparison")
    if disposition == "incumbent-better" and "incumbent-better" not in relations.values():
        raise ValueError("incumbent-better is unsupported by raw comparison")
    if disposition == "non-inferior-no-benefit" and ("candidate-better" in relations.values() or "inconclusive" in relations.values()):
        raise ValueError("non-inferior disposition differs from raw comparison")
    if disposition == "inconclusive" and "inconclusive" not in relations.values():
        raise ValueError("inconclusive disposition differs from raw comparison")
    result = {
        "schema_version": 1,
        "kind": "software-factory-bounded-candidate-independent-review",
        "review_id": f"review-{root(packet)[:20]}",
        "reviewer_id": REVIEW_FIXTURE["reviewer_id"],
        "input_root": root(packet),
        "recorded_at": exact_string(entry["recorded_at"], "review time"),
        "comparison_disposition": disposition,
        "review_disposition": BLOCK4_REVIEW[disposition],
        "retirement_posture": RETIREMENT[disposition],
    }
    parse_time(result["recorded_at"], "review time")
    result["review_root"] = root(result)
    return result


def stop_review(case: dict[str, object], candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, stop_reason: str) -> dict[str, object]:
    inconclusive = stop_reason in {"incumbent-basis-drift", "review-currentness-loss", "cancelled", "isolation-drift"}
    disposition = "inconclusive" if inconclusive else "rejected"
    input_root = root({"candidate_root": candidate_root, "focused_result_root": focused["result_root"], "mapped_result_root": mapped["result_root"] if mapped else None, "stop_reason": stop_reason})
    value = {
        "schema_version": 1,
        "kind": "software-factory-bounded-candidate-mechanical-stop-review",
        "review_id": f"review-stop-{input_root[:20]}",
        "reviewer_id": EXERCISE["lane"]["independent_reviewer_id"],
        "input_root": input_root,
        "recorded_at": format_time(parse_time(focused["recorded_at"], "focused time") + timedelta(seconds=2)),
        "comparison_disposition": None,
        "review_disposition": disposition,
        "retirement_posture": "retired-inconclusive" if inconclusive else "retired-loser",
    }
    value["review_root"] = root(value)
    return value


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def candidate_fields(candidate_root: str | None, focused: dict[str, object] | None, mapped: dict[str, object] | None, review: dict[str, object] | None, retirement: str) -> dict[str, object]:
    isolated = copy.deepcopy(EXERCISE["lane"]["isolated_writable_scope"])
    for scope in isolated:
        scope["content_root"] = candidate_root or "0" * 64
    values = {
        "hypothesis": EXERCISE["hypothesis"],
        "hypothesis_scope": copy.deepcopy(EXERCISE["hypothesis_scope"]),
        "incumbent_root": incumbent_root(),
        "candidate_root": candidate_root,
        "isolation_kind": EXERCISE["lane"]["isolation_kind"],
        "isolated_writable_scope": isolated,
        "shared_resource_exclusions": copy.deepcopy(EXERCISE["lane"]["shared_resource_exclusions"]),
        "resource_ceiling": "files<=3;changed-lines<=120;commands<=6;review-passes<=1",
        "time_ceiling": "elapsed-minutes<=20",
        "stop_condition": EXERCISE["lane"]["stop_condition"],
        "production_authority_owner_id": EXERCISE["incumbent"]["production_authority_owner_id"],
        "focused_validation": [focused["result_id"]] if focused else ["focused-stream-export-planned"],
        "mapped_validation": [mapped["result_id"]] if mapped else [],
        "validation_order": "focused-then-mapped",
        "comparison_dimensions": DIMENSIONS,
        "independent_reviewer_id": EXERCISE["lane"]["independent_reviewer_id"],
        "review_root": review["review_root"] if review else None,
        "review_disposition": review["review_disposition"] if review else None,
        "cutover_owner_id": EXERCISE["lane"]["cutover_owner_id"],
        "cutover_preconditions": ["block-9", "current-review", "current-target", "single-authority"],
        "retirement_posture": retirement,
    }
    validate_candidate_fields(values)
    return values


def validate_candidate_fields(values: dict[str, object]) -> None:
    if set(values) != set(SPEC["candidate_fields"]):
        raise ValueError("candidate field set differs from Block 4")
    for key in ("incumbent_root",):
        exact_string(values[key], key, SHA_RE)
    if values["candidate_root"] is not None:
        exact_string(values["candidate_root"], "candidate root", SHA_RE)
    for key in ("hypothesis", "resource_ceiling", "time_ceiling", "stop_condition"):
        exact_string(values[key], key)
    if values["isolation_kind"] not in SPEC["enums"]["isolation-kind"]:
        raise ValueError("candidate isolation kind differs")
    for key in ("production_authority_owner_id", "independent_reviewer_id", "cutover_owner_id"):
        exact_string(values[key], key, ID_RE)
    for key, minimum in (("focused_validation", 1), ("mapped_validation", 0), ("cutover_preconditions", 1)):
        refs = values[key]
        if type(refs) is not list or len(refs) < minimum or refs != sorted(set(refs)) or any(type(ref) is not str or ID_RE.fullmatch(ref) is None for ref in refs):
            raise ValueError(f"candidate {key} differs")
    if values["validation_order"] != "focused-then-mapped" or values["comparison_dimensions"] != DIMENSIONS:
        raise ValueError("candidate validation/comparison order differs")
    if values["review_root"] is not None:
        exact_string(values["review_root"], "review root", SHA_RE)
    if values["review_disposition"] is not None and values["review_disposition"] not in SPEC["enums"]["review-disposition"]:
        raise ValueError("candidate review disposition differs")
    if values["retirement_posture"] not in SPEC["enums"]["retirement-posture"]:
        raise ValueError("candidate retirement posture differs")
    validate_scope_refs(values["hypothesis_scope"], "hypothesis scope", contained_by=EXERCISE["target_repository_root"], min_items=1)
    validate_scope_refs(values["isolated_writable_scope"], "isolated scope", contained_by=EXERCISE["lane"]["root"], min_items=1)
    validate_scope_refs(values["shared_resource_exclusions"], "shared exclusions", contained_by=EXERCISE["target_repository_root"], min_items=0)


def process_evidence(stage: str, decision_id: str, candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, review: dict[str, object], current_state_root: str, target_root: str) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    if stage in {"validated", "reviewed", "cutover-eligible", "closed"}:
        validation_root = root({"focused_result_root": focused["result_root"], "mapped_result_root": mapped["result_root"] if mapped else None})
        evidence.append({"ref_id": f"validation-{stage}", "source_class": "validation", "adjudication_posture": "process", "root_sha256": validation_root, "claim_ids": sorted([decision_id, candidate_root])})
    if stage in {"reviewed", "cutover-eligible", "closed"}:
        evidence.append({"ref_id": f"review-{stage}", "source_class": "independent-review", "adjudication_posture": "process", "root_sha256": review["review_root"], "claim_ids": sorted([decision_id, candidate_root, review["reviewer_id"], review["review_disposition"]])})
    if stage in {"cutover-eligible", "closed"}:
        evidence.append({"ref_id": f"outcome-{stage}", "source_class": "observed-outcome", "adjudication_posture": "current-outcome", "root_sha256": root({"incumbent_authoritative": True, "candidate_authoritative": False, "candidate_root": candidate_root, "target_revision_root": target_root}), "claim_ids": sorted([decision_id, current_state_root, target_root, candidate_root])})
    return evidence


def currentness_projection(record: dict[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    for field in SPEC["currentness_projection"]:
        key = field[:-1] if field.endswith("?") else field
        values[key] = record.get(key)
    return values


def stage_records(case: dict[str, object], eligible: dict[str, object], candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, review: dict[str, object], terminal_stage: str) -> list[dict[str, object]]:
    fingerprint_values = fingerprint_projection(case, eligible)
    fingerprint = root(fingerprint_values)
    base_evidence = source_evidence(case, eligible)
    focused_time = parse_time(focused["recorded_at"], "focused time")
    review_time = parse_time(review["recorded_at"], "review time")
    stages = ["selected", "implementing"]
    if focused["exit_code"] == 0:
        stages.append("validated")
    if review["kind"] == "software-factory-bounded-candidate-independent-review":
        stages.append("reviewed")
    stages.append(terminal_stage)
    stages = list(dict.fromkeys(stages))
    records: list[dict[str, object]] = []
    previous: str | None = None
    times = {"selected": focused_time - timedelta(seconds=2), "implementing": focused_time - timedelta(seconds=1), "validated": focused_time, "reviewed": review_time, terminal_stage: review_time + timedelta(seconds=1)}
    for stage in stages:
        decision_id = f"candidate-{case['case_id']}-{stage}"
        current_state = root({"target_revision_root": target_revision_root(), "incumbent_root": incumbent_root(), "candidate_root": candidate_root, "stage": stage, "candidate_authoritative": False})
        evidence = sorted([*copy.deepcopy(base_evidence), *process_evidence(stage, decision_id, candidate_root, focused, mapped, review, current_state, target_revision_root())], key=lambda item: item["ref_id"])
        terminal = stage == terminal_stage
        retirement = review["retirement_posture"] if terminal else "active-isolated"
        fields = candidate_fields(candidate_root if stage != "selected" else None, focused if stage not in {"selected", "implementing"} else None, mapped if stage in {"reviewed", "cutover-eligible", "closed"} else None, review if stage in {"reviewed", "cutover-eligible", "closed"} else None, retirement)
        record = {
            **fingerprint_values,
            **fields,
            "decision_id": decision_id,
            "decision_stage": stage,
            "disposition": "compare-candidate",
            "recorded_at": format_time(times[stage]),
            "predecessor_decision_id": None,
            "currentness_refresh_of": previous,
            "tracker_sha256": EXERCISE["tracker_sha256"],
            "target_revision": EXERCISE["target_revision"],
            "target_revision_root": target_revision_root(),
            "current_target_state_root": current_state,
            "evidence_refs": evidence,
            "evidence_manifest_root": root(evidence),
            "decision_fingerprint": fingerprint,
            "selected_path": "bounded-candidate",
            "rejected_paths": ["incumbent-local", "generalized-service"],
            "valid_work_refs": ["evidence-incumbent"],
            "stale_proof_refs": [],
            "safe_frontier": [],
            "adaptive_decision_mode": "full-autonomous",
            "reviewer_id": EXERCISE["lane"]["independent_reviewer_id"],
            "evaluator_id": None,
            "policy_root": EXERCISE["policy_root"],
            "event_head_root": EXERCISE["event_head_root"],
            "accepted_decision_head": None,
            "accepted_revision_head": None,
            "revisit_trigger": None,
            "external_boundary": None,
        }
        record["currentness_root"] = root(currentness_projection(record))
        if set(record) != set(SPEC["common_fields"]) | set(SPEC["candidate_fields"]):
            raise ValueError("candidate stage record differs from Block 4")
        if root({key: record[key] for key in SPEC["fingerprint_projection"]}) != fingerprint:
            raise ValueError("candidate stage changed decision fingerprint")
        records.append(record)
        previous = decision_id
    allowed = SPEC["stage_rules"]["allowed_transitions"]
    for left, right in zip(records, records[1:]):
        if right["decision_stage"] not in allowed[left["decision_stage"]]:
            raise ValueError("candidate stage transition differs")
    return records


def handoff_record(records: list[dict[str, object]], comparison: list[dict[str, object]], review: dict[str, object]) -> dict[str, object]:
    final = records[-1]
    if final["decision_stage"] != "cutover-eligible" or final["retirement_posture"] != "eligible-cutover":
        raise ValueError("candidate is not handoff eligible")
    value = {
        "schema_version": 1,
        "kind": "software-factory-block9-cutover-handoff",
        "source_block": 6,
        "destination_block": 9,
        "decision_fingerprint": final["decision_fingerprint"],
        "currentness_root": final["currentness_root"],
        "target_revision_root": final["target_revision_root"],
        "incumbent_root": final["incumbent_root"],
        "candidate_root": final["candidate_root"],
        "review_root": final["review_root"],
        "comparison_root": root(comparison),
        "target_owner_id": final["cutover_owner_id"],
        "protected_capability_results": final["protected_capability_results"],
        "cutover_preconditions": final["cutover_preconditions"],
        "non_mutating": True,
        "cutover_authority": False,
        "publish_authority": False,
        "tracker_authority": False,
        "policy_authority": False,
    }
    value["handoff_id"] = f"block9-handoff-{root(value)[:20]}"
    value["handoff_root"] = root(value)
    return value


def accepted_lane_head(result: dict[str, object]) -> dict[str, object]:
    records = result["stage_records"]
    final = records[-1]
    value = {
        "schema_version": 1,
        "kind": "software-factory-accepted-candidate-lane-head",
        "decision_fingerprint": result["decision_fingerprint"],
        "candidate_root": final["candidate_root"],
        "review_root": final["review_root"],
        "currentness_root": final["currentness_root"],
        "handoff_root": result["handoff"]["handoff_root"] if result["handoff"] else None,
    }
    value["head_root"] = root(value)
    return value


def validate_accepted_head(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != {"schema_version", "kind", "decision_fingerprint", "candidate_root", "review_root", "currentness_root", "handoff_root", "head_root"}:
        raise ValueError("accepted lane head differs")
    raw = dict(value)
    recorded = raw.pop("head_root")
    if recorded != root(raw):
        raise ValueError("accepted lane head is stale")
    for key in ("decision_fingerprint", "candidate_root", "review_root", "currentness_root"):
        exact_string(value[key], key, SHA_RE)
    if value["handoff_root"] is not None:
        exact_string(value["handoff_root"], "handoff root", SHA_RE)
    return value


def ceiling_exceeded(case: dict[str, object]) -> bool:
    usage = case["usage"]
    if type(usage) is not dict or set(usage) != {"files", "changed_lines", "commands", "review_passes", "elapsed_minutes"}:
        raise ValueError("candidate usage differs")
    for key in usage:
        exact_int(usage[key], f"usage {key}")
    ceiling = EXERCISE["lane"]["resource_ceiling"]
    return usage["files"] > ceiling["max_files"] or usage["changed_lines"] > ceiling["max_changed_lines"] or usage["commands"] > ceiling["max_commands"] or usage["review_passes"] > ceiling["max_review_passes"] or usage["elapsed_minutes"] > EXERCISE["lane"]["time_ceiling_minutes"]


def evaluate(case_id: str, *, accepted_head: dict[str, object] | None = None) -> dict[str, object]:
    case = canonical_case(case_id)
    eligible = eligibility(case)
    fingerprint = decision_fingerprint(case, eligible)
    if not lane_eligible(eligible):
        return {"action": "reject-before-lane", "lane_created": False, "review_cycle": False, "decision_fingerprint": fingerprint, "eligibility": eligible}
    artifact, candidate_root = candidate_root_for(case)
    focused = focused_result(artifact, candidate_root)
    mapped = mapped_result(artifact, candidate_root, focused)
    if accepted_head is not None:
        head = validate_accepted_head(accepted_head)
        review_entry = next((item for item in REVIEW_FIXTURE["results"] if item["case_id"] == case_id), None)
        if review_entry is not None and mapped is not None and mapped["exit_code"] == 0:
            comparison = comparison_records(mapped)
            review = review_fixture_result(case_id, blind_review_packet(candidate_root, mapped, comparison), comparison)
            if head["decision_fingerprint"] == fingerprint and head["candidate_root"] == candidate_root and head["review_root"] == review["review_root"]:
                return {"action": "deduplicate", "lane_created": False, "review_cycle": False, "handoff_emitted": False, "decision_fingerprint": fingerprint, "accepted_head_root": head["head_root"]}
    stop_reason = case["stop_reason"]
    if ceiling_exceeded(case):
        stop_reason = "ceiling-expired"
    if focused["exit_code"] != 0:
        stop_reason = "focused-failure"
    if focused["protected_result"] != "preserved":
        stop_reason = "protected-regression"
    if mapped is not None and mapped["exit_code"] != 0:
        stop_reason = "mapped-failure"
    if stop_reason is not None:
        stop_reason = exact_string(stop_reason, "stop reason")
        review = stop_review(case, candidate_root, focused, mapped, stop_reason)
        records = stage_records(case, eligible, candidate_root, focused, mapped, review, "closed")
        return {"action": "stop-retire", "lane_created": True, "review_cycle": False, "decision_fingerprint": fingerprint, "stop_reason": stop_reason, "stage_records": records, "candidate_root": candidate_root, "candidate_authoritative": False, "incumbent_authoritative": True, "isolation_cleanup": "retired-non-authoritative", "retained_evidence": [focused["result_root"], *( [mapped["result_root"]] if mapped else []), review["review_root"]], "handoff": None, "cutover_performed": False, "tracker_mutated": False, "policy_mutated": False}
    if mapped is None or mapped["exit_code"] != 0 or mapped["metrics"] is None:
        raise ValueError("mapped result is absent after focused success")
    comparison = comparison_records(mapped)
    packet = blind_review_packet(candidate_root, mapped, comparison)
    review = review_fixture_result(case_id, packet, comparison)
    terminal = "cutover-eligible" if review["comparison_disposition"] == "candidate-better" else "closed"
    records = stage_records(case, eligible, candidate_root, focused, mapped, review, terminal)
    handoff = handoff_record(records, comparison, review) if terminal == "cutover-eligible" else None
    action = "handoff-block-9" if handoff else "retire-candidate"
    result = {"action": action, "lane_created": True, "review_cycle": True, "decision_fingerprint": fingerprint, "candidate_root": candidate_root, "focused_result": focused, "mapped_result": mapped, "raw_comparison_records": comparison, "blind_review_packet": packet, "review_result": review, "stage_records": records, "candidate_authoritative": False, "incumbent_authoritative": True, "isolation_cleanup": "kept-isolated-for-block-9" if handoff else "retired-non-authoritative", "handoff": handoff, "cutover_performed": False, "tracker_mutated": False, "policy_mutated": False}
    result["lane_head"] = accepted_lane_head(result)
    return result


class BoundedCandidateContractTests(unittest.TestCase):
    def test_source_preflight_and_nonopaque_eligibility_include_reversibility(self) -> None:
        validate_exercise()
        positive = eligibility(canonical_case("winning-candidate"))
        self.assertEqual(positive["bounded_cost_minutes"], 35)
        self.assertEqual(positive["net_avoidable_minutes"], 25)
        self.assertEqual(positive["reversibility_posture"], "checkpoint-restore")
        self.assertTrue(lane_eligible(positive))
        for case_id in ("read-only-decidable", "unsafe-isolation"):
            result = evaluate(case_id)
            self.assertEqual(result["action"], "reject-before-lane")
            self.assertFalse(result["lane_created"])

    def test_coherent_cases_bind_bytes_validation_comparison_and_external_review(self) -> None:
        for case_id in ("winning-candidate", "losing-candidate", "novelty-bias", "inconclusive-comparison"):
            case = canonical_case(case_id)
            result = evaluate(case_id)
            self.assertEqual(result["action"], case["expected_action"])
            self.assertEqual(result["review_result"]["comparison_disposition"], case["expected_comparison_disposition"])
            self.assertEqual(result["candidate_root"], artifact_root(EXERCISE["artifacts"][case["artifact_id"]]))
            self.assertEqual(result["mapped_result"]["focused_result_root"], result["focused_result"]["result_root"])
            self.assertGreater(parse_time(result["mapped_result"]["recorded_at"], "mapped"), parse_time(result["focused_result"]["recorded_at"], "focused"))
            validate_comparison(result["raw_comparison_records"])
            self.assertEqual(result["review_result"]["input_root"], root(result["blind_review_packet"]))

    def test_block4_lifecycle_winner_and_inconclusive_are_valid(self) -> None:
        winner = evaluate("winning-candidate")
        self.assertEqual([item["decision_stage"] for item in winner["stage_records"]], ["selected", "implementing", "validated", "reviewed", "cutover-eligible"])
        self.assertEqual(winner["stage_records"][-1]["review_disposition"], "accepted")
        self.assertEqual(winner["stage_records"][-1]["retirement_posture"], "eligible-cutover")
        inconclusive = evaluate("inconclusive-comparison")
        self.assertEqual(inconclusive["stage_records"][-1]["decision_stage"], "closed")
        self.assertEqual(inconclusive["stage_records"][-1]["review_disposition"], "inconclusive")
        self.assertEqual(inconclusive["stage_records"][-1]["retirement_posture"], "retired-inconclusive")
        for record in [*winner["stage_records"], *inconclusive["stage_records"]]:
            self.assertEqual(record["currentness_root"], root(currentness_projection(record)))
            self.assertEqual(set(record), set(SPEC["common_fields"]) | set(SPEC["candidate_fields"]))

    def test_all_post_creation_stops_close_with_evidence_cleanup_and_no_authority(self) -> None:
        for case_id in ("ceiling-expired", "incumbent-conflict", "focused-failure", "mapped-failure", "protected-regression", "review-currentness-loss", "cancelled", "isolation-drift", "hypothesis-falsified"):
            result = evaluate(case_id)
            self.assertEqual(result["action"], "stop-retire")
            self.assertEqual(result["stage_records"][-1]["decision_stage"], "closed")
            self.assertFalse(result["candidate_authoritative"])
            self.assertTrue(result["incumbent_authoritative"])
            self.assertEqual(result["isolation_cleanup"], "retired-non-authoritative")
            self.assertIsNone(result["handoff"])
            self.assertFalse(result["cutover_performed"] or result["tracker_mutated"] or result["policy_mutated"])
            classes = {item["source_class"] for item in result["stage_records"][-1]["evidence_refs"]}
            self.assertTrue({"validation", "independent-review", "observed-outcome"}.issubset(classes))

    def test_accepted_head_deduplicates_automatically_without_lane_review_or_handoff(self) -> None:
        first = evaluate("winning-candidate")
        repeat = evaluate("winning-candidate", accepted_head=first["lane_head"])
        self.assertEqual(repeat["action"], "deduplicate")
        self.assertFalse(repeat["lane_created"])
        self.assertFalse(repeat["review_cycle"])
        self.assertFalse(repeat["handoff_emitted"])
        stale = copy.deepcopy(first["lane_head"])
        stale["candidate_root"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "stale"):
            evaluate("winning-candidate", accepted_head=stale)

    def test_winner_emits_one_frozen_nonmutating_block9_handoff(self) -> None:
        result = evaluate("winning-candidate")
        handoff = result["handoff"]
        self.assertEqual(handoff["source_block"], 6)
        self.assertEqual(handoff["destination_block"], 9)
        self.assertTrue(handoff["non_mutating"])
        for key in ("cutover_authority", "publish_authority", "tracker_authority", "policy_authority"):
            self.assertFalse(handoff[key])
        raw = dict(handoff)
        recorded_root = raw.pop("handoff_root")
        self.assertEqual(recorded_root, root(raw))

    def test_blind_review_input_excludes_preference_and_disposition_follows_raw_evidence(self) -> None:
        result = evaluate("winning-candidate")
        packet = result["blind_review_packet"]
        for key in ("case_id", "expected_action", "expected_comparison_disposition", "implementer_preference"):
            self.assertNotIn(key, packet)
        changed = copy.deepcopy(result["raw_comparison_records"])
        changed[0]["relation"] = "incumbent-better"
        with self.assertRaisesRegex(ValueError, "unsupported"):
            review_fixture_result("winning-candidate", packet, changed)

    def test_fingerprint_binds_target_incumbent_outcome_dimensions_and_source_basis(self) -> None:
        case = canonical_case("winning-candidate")
        eligible = eligibility(case)
        baseline = decision_basis(case, eligible)
        baseline_root = root(baseline)
        for key, value in (
            ("target_repository_root", "/different-target"),
            ("target_revision", "f" * 40),
            ("incumbent_revision", "e" * 40),
            ("expected_observable_effect", "different effect"),
            ("comparison_dimensions", list(reversed(DIMENSIONS))),
        ):
            changed = copy.deepcopy(baseline)
            changed[key] = value
            self.assertNotEqual(root(changed), baseline_root, key)

    def test_strict_schema_types_and_paths_reject_coercion_empty_scope_and_escape(self) -> None:
        fields = evaluate("winning-candidate")["stage_records"][-1]
        for key, value in (("isolation_kind", "invented"), ("hypothesis_scope", []), ("isolated_writable_scope", []), ("production_authority_owner_id", True), ("independent_reviewer_id", 123), ("focused_validation", [123])):
            invalid = {name: copy.deepcopy(fields[name]) for name in SPEC["candidate_fields"]}
            invalid[key] = value
            with self.assertRaises(ValueError, msg=key):
                validate_candidate_fields(invalid)
        invalid_scope = copy.deepcopy({name: fields[name] for name in SPEC["candidate_fields"]})
        invalid_scope["isolated_writable_scope"][0]["path"] = "/software-factory-candidate-lane/../production/owned.py"
        with self.assertRaisesRegex(ValueError, "canonical"):
            validate_candidate_fields(invalid_scope)
        invalid_owner = copy.deepcopy({name: fields[name] for name in SPEC["candidate_fields"]})
        invalid_owner["isolated_writable_scope"][0]["owner_id"] = True
        with self.assertRaises(ValueError):
            validate_candidate_fields(invalid_owner)

    def test_focused_mapped_order_and_content_currentness_fail_closed(self) -> None:
        artifact = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        candidate = artifact_root(artifact)
        focused = focused_result(artifact, candidate)
        artifact["mapped"]["recorded_at"] = artifact["focused"]["recorded_at"]
        with self.assertRaisesRegex(ValueError, "does not follow"):
            mapped_result(artifact, candidate, focused)
        changed = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        original = artifact_root(changed)
        changed["files"][0]["content_utf8"] += "# changed\n"
        self.assertNotEqual(artifact_root(changed), original)

    def test_method_is_selective_bounded_and_stops_before_cutover(self) -> None:
        skill = " ".join(SKILL.split())
        reference = " ".join(REFERENCE.split())
        for phrase in ("Use `compare-candidate` only after the inline loop proves", "Open exactly one branch, worktree, temporary repository, or equivalent lane", "without a novelty bonus or opaque aggregate score", "do not cut over here", "Never retain two live implementations or force adoption"):
            self.assertIn(phrase, skill)
        for phrase in ("Failure of any condition returns to the incumbent without creating a lane", "The incumbent is the only production authority", "The Block Stop is before cutover, tracker amendment, policy change"):
            self.assertIn(phrase, reference)


if __name__ == "__main__":
    unittest.main()
