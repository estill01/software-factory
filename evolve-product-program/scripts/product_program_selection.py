#!/usr/bin/env python3
"""Build and verify bounded nonauthorizing product-program portfolios."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from product_program_evolution import (  # noqa: E402
    ProductProgramError,
    canonical,
    digest,
    exact_id,
    exact_keys,
    load_json_bytes,
    read_json_file,
    verify_packet,
)
from product_program_reflection import verify_reflection  # noqa: E402
from product_program_resources import verify_resource_evidence  # noqa: E402

SCHEMA_VERSION = 1
MAX_ITEMS = 32
DIMENSIONS = (
    "product_effect",
    "evidence_strength",
    "architecture_fit",
    "protected_capability_effect",
    "risk",
    "resource_cost",
    "uncertainty",
    "reversibility",
    "integration_cost",
    "opportunity_cost",
    "coordination_cost",
    "expected_benefit",
)
DIMENSION_VALUES = {"adverse", "favorable", "mixed", "uncertain"}
MATERIAL_ADJUDICATION_DIMENSIONS = {
    "architecture_fit",
    "integration_cost",
    "opportunity_cost",
    "protected_capability_effect",
    "risk",
    "uncertainty",
}
BUDGET_KEYS = {"execution_units", "exploration_units", "review_units"}
DISPOSITION_PLACEMENTS = {
    "continue-program-unchanged": "none",
    "remediate-current-block": "current-block-owner",
    "request-material-goal-authority": "direct-user",
    "revise-current-program": "current-program-author",
    "run-bounded-experiment": "experiment-owner",
    "safe-defer-open-fact-or-authority": "reserved-effect-owner",
    "start-program-portfolio": "program-portfolio-author",
    "start-successor-program": "successor-program-author",
}
OWNER_BY_PLACEMENT = {
    "none": "none",
    "current-block-owner": "implementation-owner",
    "current-program-author": "tracker-author",
    "direct-user": "direct-user",
    "experiment-owner": "experiment-owner",
    "program-portfolio-author": "tracker-author",
    "reserved-effect-owner": "reserved-effect-owner",
    "successor-program-author": "tracker-author",
}
REJECTION_REASONS = {
    "coordination-cost-not-justified",
    "current-range-risk",
    "duplicate-capability",
    "evidence-weaker-than-selected",
    "higher-risk-than-selected",
    "no-material-gain",
    "protected-capability-risk",
    "resource-ceiling",
}
STOP_IDS = {"outcome-disconfirmed", "resource-ceiling-reached", "scope-overlap", "stale-currentness"}
ROLLBACK_IDS = {"retire-derived-lane", "return-to-current-program", "safe-defer"}
REVISIT_IDS = {"material-outcome-change", "new-direct-authority", "resource-currentness-change"}
FORBIDDEN_KEYS = {
    "authorized",
    "billing",
    "credential",
    "effect_applied",
    "hidden_reasoning",
    "permission",
    "price",
    "prompt",
    "raw_output",
    "secret",
    "spend",
    "transcript",
    "weighted_score",
}
AUTHORITY_PREMISES = {
    "irreversible-reserved-effect",
    "product-purpose-change",
    "user-specific-tradeoff",
}


def reject_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise ProductProgramError("selection contains authority, hidden output, billing, or scalar utility")
            reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            reject_forbidden(item)


def id_list(value: Any, label: str, *, allowed: set[str] | None = None, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ProductProgramError(f"{label} must be a bounded ID array")
    result = [exact_id(item, f"{label} item") for item in value]
    if not result and not empty:
        raise ProductProgramError(f"{label} must not be empty")
    if result != sorted(set(result)):
        raise ProductProgramError(f"{label} must be sorted and unique")
    if allowed is not None and not set(result) <= allowed:
        raise ProductProgramError(f"{label} has a dangling reference")
    return result


def ordered_id_list(value: Any, label: str, *, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        raise ProductProgramError(f"{label} must be a bounded nonempty ID array")
    result = [exact_id(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise ProductProgramError(f"{label} must be unique")
    if allowed is not None and not set(result) <= allowed:
        raise ProductProgramError(f"{label} has a dangling reference")
    return result


def budget(value: Any, label: str) -> dict[str, int]:
    item = exact_keys(value, BUDGET_KEYS, label)
    result: dict[str, int] = {}
    for key in sorted(BUDGET_KEYS):
        if type(item[key]) is not int or item[key] < 0:
            raise ProductProgramError(f"{label} values must be nonnegative integers")
        result[key] = item[key]
    return result


def add_budgets(values: Sequence[Mapping[str, int]]) -> dict[str, int]:
    return {key: sum(item[key] for item in values) for key in sorted(BUDGET_KEYS)}


def subtract_budget(ceiling: Mapping[str, int], used: Mapping[str, int]) -> dict[str, int]:
    result = {key: ceiling[key] - used[key] for key in sorted(BUDGET_KEYS)}
    if any(value < 0 for value in result.values()):
        raise ProductProgramError("aggregate budget exceeds the current operator ceiling")
    return result


def artifact_fields(kind: str) -> set[str]:
    contract = load_json_bytes(
        (SCRIPT_DIR.parents[0] / "fixtures" / "product_program_contract_v1.json").read_bytes(),
        "contract fixture",
    )
    return set(contract["artifact_schemas"][kind])


def evidence_ids(packet: Mapping[str, Any]) -> set[str]:
    result = set(packet["outcome"]["evidence_ids"])
    result.update(item["capability_id"] for item in packet["protected_capabilities"])
    for field in ("product_sources", "reports", "resource_sources", "decisions", "incidents"):
        result.update(item["source_id"] for item in packet[field])
    return result


def normalize_capacity_source(packet: Mapping[str, Any], value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "active_tracker_limit",
            "budget",
            "concurrency_limit",
            "evidence_class",
            "kind",
            "schema_version",
            "source_id",
        },
        "operator capacity source",
    )
    if item["schema_version"] != 1 or item["kind"] != "product-program-operator-capacity":
        raise ProductProgramError("operator capacity source identity differs")
    if item["evidence_class"] not in {"observed", "provider-reported"}:
        raise ProductProgramError("operator capacity must not be presented from estimated evidence")
    source_id = exact_id(item["source_id"], "operator capacity source ID")
    retained = {entry["source_id"]: entry for entry in packet["resource_sources"]}
    if source_id not in retained or retained[source_id]["evidence_class"] != item["evidence_class"]:
        raise ProductProgramError("operator capacity source is not retained with its evidence class")
    raw = canonical(value)
    if retained[source_id]["sha256"] != hashlib.sha256(raw).hexdigest() or retained[source_id]["byte_length"] != len(raw):
        raise ProductProgramError("operator capacity source bytes differ from the packet binding")
    if type(item["active_tracker_limit"]) is not int or item["active_tracker_limit"] < 1 or type(item["concurrency_limit"]) is not int or item["concurrency_limit"] < 1:
        raise ProductProgramError("operator tracker/concurrency ceilings are invalid")
    return {
        "active_tracker_limit": item["active_tracker_limit"],
        "budget": budget(item["budget"], "operator budget ceiling"),
        "concurrency_limit": item["concurrency_limit"],
        "evidence_class": item["evidence_class"],
        "evidence_ids": [source_id],
        "source_root": hashlib.sha256(raw).hexdigest(),
    }


def adjudication_input_root(
    packet: Mapping[str, Any],
    reflection: Mapping[str, Any],
    resource: Mapping[str, Any],
    disposition: str,
    selected: Sequence[str],
    dimensions: Sequence[Mapping[str, Any]],
    rejected: Sequence[Mapping[str, Any]],
    ceiling: Mapping[str, Any],
    lanes: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
) -> str:
    """Root every consequential input without accepting an adjudicator assertion."""
    return digest(
        {
            "capacity": ceiling,
            "dimensions": list(dimensions),
            "disposition": disposition,
            "kind": "product-program-selection-adjudication-input",
            "lanes": list(lanes),
            "packet_root": packet["artifact_root"],
            "reflection_root": reflection["artifact_root"],
            "rejected_candidates": list(rejected),
            "resource_evidence_root": resource["artifact_root"],
            "scheduling_groups": list(groups),
            "selected_candidate_ids": list(selected),
        }
    )


def normalize_submission(
    packet: Mapping[str, Any], reflection: Mapping[str, Any], resource: Mapping[str, Any], capacity_source: Mapping[str, Any], value: Any
) -> dict[str, Any]:
    reject_forbidden(value)
    item = exact_keys(
        value,
        {
            "adjudication",
            "authority_premise",
            "dimensions",
            "disposition",
            "early_stop_rules",
            "kind",
            "lanes",
            "packet_root",
            "reflection_root",
            "rejected_candidates",
            "resource_evidence_root",
            "schema_version",
            "scheduling_groups",
            "selected_candidate_ids",
            "selector_id",
        },
        "selection submission",
    )
    if item["schema_version"] != 1 or item["kind"] != "product-program-selection-submission":
        raise ProductProgramError("selection submission identity differs")
    if item["packet_root"] != packet["artifact_root"] or item["reflection_root"] != reflection["artifact_root"] or item["resource_evidence_root"] != resource["artifact_root"]:
        raise ProductProgramError("selection submission is stale")
    disposition = item["disposition"]
    if disposition not in DISPOSITION_PLACEMENTS:
        raise ProductProgramError("selection disposition is unsupported")
    candidates = {entry["candidate_id"]: entry for entry in reflection["candidates"]}
    candidate_ids = set(candidates)
    selected = id_list(item["selected_candidate_ids"], "selected candidate IDs", allowed=candidate_ids, empty=disposition in {"safe-defer-open-fact-or-authority", "request-material-goal-authority"})
    no_change = next(entry["candidate_id"] for entry in reflection["candidates"] if entry["candidate_type"] == "continue-unchanged")
    if disposition == "continue-program-unchanged" and selected != [no_change]:
        raise ProductProgramError("unchanged disposition must select only the no-change comparison")
    if disposition != "continue-program-unchanged" and no_change in selected:
        raise ProductProgramError("change disposition cannot select the no-change comparison")
    selector_id = exact_id(item["selector_id"], "selector ID")
    prohibited_roles = {reflection["generator_id"]}
    semantic_review = reflection["authority"]["semantic_review"]
    prohibited_roles.add(semantic_review["reviewer_id"])
    for candidate in candidates.values():
        prohibited_roles.update(candidate[field] for field in ("author_owner", "evaluation_owner", "implementation_owner"))
    if selector_id in prohibited_roles:
        raise ProductProgramError("selector conflicts with generator, reviewer, writer, implementer, or evaluator")
    declared_selectors = {candidate["selector_id"] for candidate in candidates.values()}
    if declared_selectors != {selector_id}:
        raise ProductProgramError("selector differs from the frozen candidate-set owner")

    allowed_evidence = evidence_ids(packet)
    dimensions: list[dict[str, Any]] = []
    if not isinstance(item["dimensions"], list) or len(item["dimensions"]) != len(candidates):
        raise ProductProgramError("selection must compare every candidate")
    for raw in item["dimensions"]:
        entry = exact_keys(raw, {"candidate_id", "evidence_ids", "values"}, "candidate dimensions")
        candidate_id = exact_id(entry["candidate_id"], "dimension candidate ID")
        values = exact_keys(entry["values"], set(DIMENSIONS), "candidate dimension values")
        if any(values[name] not in DIMENSION_VALUES for name in DIMENSIONS):
            raise ProductProgramError("candidate dimension value is unsupported")
        dimensions.append({
            "candidate_id": candidate_id,
            "evidence_ids": id_list(entry["evidence_ids"], "dimension evidence IDs", allowed=allowed_evidence),
            "values": {name: values[name] for name in DIMENSIONS},
        })
    dimensions.sort(key=lambda entry: entry["candidate_id"])
    if {entry["candidate_id"] for entry in dimensions} != candidate_ids:
        raise ProductProgramError("selection dimension coverage differs from candidates")
    by_candidate = {entry["candidate_id"]: entry for entry in dimensions}
    for candidate_id in selected:
        if candidate_id == no_change:
            continue
        values = by_candidate[candidate_id]["values"]
        if values["expected_benefit"] != "favorable" or values["coordination_cost"] == "adverse":
            raise ProductProgramError("selected candidate benefit does not exceed coordination cost")
        if values["protected_capability_effect"] == "adverse":
            raise ProductProgramError("selected candidate risks a protected capability")

    rejected: list[dict[str, Any]] = []
    if not isinstance(item["rejected_candidates"], list):
        raise ProductProgramError("rejected candidates must be an array")
    for raw in item["rejected_candidates"]:
        entry = exact_keys(raw, {"candidate_id", "evidence_ids", "reason_id"}, "rejected candidate")
        if entry["reason_id"] not in REJECTION_REASONS:
            raise ProductProgramError("rejected candidate reason is unsupported")
        rejected.append({
            "candidate_id": exact_id(entry["candidate_id"], "rejected candidate ID"),
            "evidence_ids": id_list(entry["evidence_ids"], "rejected candidate evidence IDs", allowed=allowed_evidence),
            "reason_id": entry["reason_id"],
        })
    rejected.sort(key=lambda entry: entry["candidate_id"])
    if len({entry["candidate_id"] for entry in rejected}) != len(rejected) or {entry["candidate_id"] for entry in rejected} != candidate_ids - set(selected):
        raise ProductProgramError("selected and rejected candidates do not partition the candidate set")

    ceiling = normalize_capacity_source(packet, capacity_source)
    placement = DISPOSITION_PLACEMENTS[disposition]
    expected_owner = OWNER_BY_PLACEMENT[placement]

    lanes: list[dict[str, Any]] = []
    if not isinstance(item["lanes"], list) or len(item["lanes"]) > ceiling["active_tracker_limit"]:
        raise ProductProgramError("portfolio lane count exceeds the active-tracker ceiling")
    for raw in item["lanes"]:
        entry = exact_keys(raw, {"budget", "candidate_ids", "dependency_lane_ids", "evidence_ids", "expected_effect_id", "integration_owner", "lane_id", "revisit_id", "rollback_id", "shared_resource_exclusions", "stop_id", "writable_scopes", "writer_id"}, "portfolio lane")
        if entry["stop_id"] not in STOP_IDS or entry["rollback_id"] not in ROLLBACK_IDS or entry["revisit_id"] not in REVISIT_IDS:
            raise ProductProgramError("portfolio lane Stop/rollback/revisit identifier is unsupported")
        lane_candidates = id_list(entry["candidate_ids"], "lane candidate IDs", allowed=set(selected))
        writer_id = exact_id(entry["writer_id"], "lane writer ID")
        integration_owner = exact_id(entry["integration_owner"], "lane integration owner")
        if writer_id != expected_owner or integration_owner not in {"none", expected_owner}:
            raise ProductProgramError("portfolio lane writer or integration owner differs from the fixed placement owner")
        if placement == "current-block-owner" and any(candidates[candidate_id]["implementation_owner"] != writer_id for candidate_id in lane_candidates):
            raise ProductProgramError("current-block lane writer differs from its candidate implementation owner")
        if placement in {"current-program-author", "program-portfolio-author", "successor-program-author"} and any(candidates[candidate_id]["author_owner"] != writer_id for candidate_id in lane_candidates):
            raise ProductProgramError("tracker lane writer differs from its candidate author owner")
        scopes = id_list(entry["writable_scopes"], "lane writable scopes")
        lanes.append({
            "budget": budget(entry["budget"], "lane budget"),
            "candidate_ids": lane_candidates,
            "dependency_lane_ids": id_list(entry["dependency_lane_ids"], "lane dependencies", empty=True),
            "evidence_ids": id_list(entry["evidence_ids"], "lane evidence IDs", allowed=allowed_evidence),
            "expected_effect_id": exact_id(entry["expected_effect_id"], "lane expected-effect ID"),
            "integration_owner": integration_owner,
            "lane_id": exact_id(entry["lane_id"], "lane ID"),
            "revisit_id": entry["revisit_id"],
            "rollback_id": entry["rollback_id"],
            "shared_resource_exclusions": id_list(entry["shared_resource_exclusions"], "lane shared-resource exclusions", empty=True),
            "stop_id": entry["stop_id"],
            "writable_scopes": scopes,
            "writer_id": writer_id,
        })
    lanes.sort(key=lambda entry: entry["lane_id"])
    lane_ids = {entry["lane_id"] for entry in lanes}
    lane_selected = set(selected) - ({no_change} if disposition == "continue-program-unchanged" else set())
    flattened_candidates = [candidate_id for entry in lanes for candidate_id in entry["candidate_ids"]]
    if len(lane_ids) != len(lanes) or set(flattened_candidates) != lane_selected or len(flattened_candidates) != len(set(flattened_candidates)):
        raise ProductProgramError("portfolio lanes repeat IDs or omit selected candidates")
    if len(lanes) > 1 and disposition != "start-program-portfolio":
        raise ProductProgramError("multiple lanes require the program-portfolio disposition")
    if disposition == "start-program-portfolio" and len(lanes) < 2:
        raise ProductProgramError("program-portfolio disposition requires multiple justified lanes")
    if any(set(entry["dependency_lane_ids"]) - lane_ids or entry["lane_id"] in entry["dependency_lane_ids"] for entry in lanes):
        raise ProductProgramError("portfolio lane dependencies are invalid")
    remaining = set(lane_ids)
    resolved: set[str] = set()
    while remaining:
        ready = {entry["lane_id"] for entry in lanes if entry["lane_id"] in remaining and set(entry["dependency_lane_ids"]) <= resolved}
        if not ready:
            raise ProductProgramError("portfolio dependency graph is cyclic")
        resolved.update(ready); remaining -= ready
    aggregate = add_budgets([entry["budget"] for entry in lanes])
    unused = subtract_budget(ceiling["budget"], aggregate)

    groups: list[dict[str, Any]] = []
    if not isinstance(item["scheduling_groups"], list):
        raise ProductProgramError("scheduling groups must be an array")
    scheduled: list[str] = []
    lane_by_id = {entry["lane_id"]: entry for entry in lanes}
    group_ids: list[str] = []
    for raw in item["scheduling_groups"]:
        entry = exact_keys(raw, {"group_id", "lane_ids", "mode"}, "scheduling group")
        if entry["mode"] not in {"parallel", "sequential"}:
            raise ProductProgramError("scheduling mode is unsupported")
        ids = ordered_id_list(entry["lane_ids"], "scheduling group lanes", allowed=lane_ids)
        if entry["mode"] == "parallel" and len(ids) > ceiling["concurrency_limit"]:
            raise ProductProgramError("parallel group exceeds the concurrency ceiling")
        if entry["mode"] == "parallel":
            for index, left_id in enumerate(ids):
                left = lane_by_id[left_id]
                for right_id in ids[index + 1:]:
                    right = lane_by_id[right_id]
                    if left_id in right["dependency_lane_ids"] or right_id in left["dependency_lane_ids"]:
                        raise ProductProgramError("dependent lanes cannot be scheduled in parallel")
                    overlap = set(left["writable_scopes"]) & set(right["writable_scopes"])
                    if overlap and (left["integration_owner"] == "none" or left["integration_owner"] != right["integration_owner"] or not overlap <= set(left["shared_resource_exclusions"]) or not overlap <= set(right["shared_resource_exclusions"])):
                        raise ProductProgramError("parallel lanes have overlapping writers without one integration owner and exclusions")
        scheduled.extend(ids)
        group_id = exact_id(entry["group_id"], "scheduling group ID")
        group_ids.append(group_id)
        groups.append({"group_id": group_id, "lane_ids": ids, "mode": entry["mode"]})
    if len(group_ids) != len(set(group_ids)):
        raise ProductProgramError("scheduling group IDs must be unique")
    if scheduled != list(dict.fromkeys(scheduled)) or set(scheduled) != lane_ids:
        raise ProductProgramError("scheduling groups must cover every lane exactly once")
    schedule_location = {
        lane_id: (group_index, lane_index, group["mode"])
        for group_index, group in enumerate(groups)
        for lane_index, lane_id in enumerate(group["lane_ids"])
    }
    for lane in lanes:
        group_index, lane_index, mode = schedule_location[lane["lane_id"]]
        for dependency in lane["dependency_lane_ids"]:
            dependency_group, dependency_index, _ = schedule_location[dependency]
            if dependency_group > group_index or (dependency_group == group_index and (mode != "sequential" or dependency_index >= lane_index)):
                raise ProductProgramError("portfolio schedule places a dependency after or alongside its dependent")
    if disposition == "continue-program-unchanged" and lanes:
        raise ProductProgramError("unchanged disposition cannot create a work lane")
    if disposition not in {"continue-program-unchanged", "safe-defer-open-fact-or-authority", "request-material-goal-authority"} and not lanes:
        raise ProductProgramError("active change disposition requires a portfolio lane")

    premise_raw = exact_keys(item["authority_premise"], {"evidence_ids", "kind"}, "authority premise")
    premise_evidence = id_list(premise_raw["evidence_ids"], "authority premise evidence IDs", allowed=allowed_evidence, empty=True)
    direct_authority_ids = {entry["source_id"] for entry in packet["product_sources"] if entry["evidence_class"] == "direct-authority"}
    if disposition == "request-material-goal-authority":
        if premise_raw["kind"] not in AUTHORITY_PREMISES or not set(premise_evidence) & direct_authority_ids:
            raise ProductProgramError("material-goal authority request lacks a qualifying direct-authority premise")
    elif premise_raw["kind"] != "none" or premise_evidence:
        raise ProductProgramError("non-authority disposition must have an exact no-op authority premise")
    authority_premise = {"evidence_ids": premise_evidence, "kind": premise_raw["kind"]}

    material_tradeoffs = sorted(
        f"{candidate_id}:{dimension}"
        for candidate_id in selected
        for dimension in MATERIAL_ADJUDICATION_DIMENSIONS
        if by_candidate[candidate_id]["values"][dimension] in {"adverse", "uncertain"}
    )
    expected_reviewed_root = adjudication_input_root(packet, reflection, resource, disposition, selected, dimensions, rejected, ceiling, lanes, groups)
    adjudication_raw = exact_keys(item["adjudication"], {"adjudicator_id", "decision", "finding_ids", "required", "review_root", "reviewed_input_root", "tradeoff_ids"}, "selection adjudication")
    if type(adjudication_raw["required"]) is not bool or adjudication_raw["decision"] not in {"accepted", "not-required", "rejected"}:
        raise ProductProgramError("selection adjudication state is invalid")
    adjudicator_id = exact_id(adjudication_raw["adjudicator_id"], "adjudicator ID")
    findings = id_list(adjudication_raw["finding_ids"], "adjudication finding IDs", empty=True)
    tradeoffs = id_list(adjudication_raw["tradeoff_ids"], "adjudication tradeoff IDs", empty=True)
    reviewed_input_root = exact_id(adjudication_raw["reviewed_input_root"], "adjudication reviewed-input root")
    review_root = exact_id(adjudication_raw["review_root"], "adjudication review root")
    required = bool(material_tradeoffs)
    if adjudication_raw["required"] != required:
        raise ProductProgramError("consequential adjudication requirement differs from the material dimension state")
    if required:
        if adjudicator_id != "consequential-max-adjudicator" or adjudicator_id in prohibited_roles | {selector_id} or adjudication_raw["decision"] != "accepted" or findings or tradeoffs != material_tradeoffs or reviewed_input_root != expected_reviewed_root:
            raise ProductProgramError("consequential adjudication is not independently accepted")
    elif adjudication_raw["decision"] != "not-required" or adjudicator_id != "none" or findings or tradeoffs or reviewed_input_root != "none":
        raise ProductProgramError("unneeded adjudication must be an exact no-op")
    adjudication_without_root = {"adjudicator_id": adjudicator_id, "decision": adjudication_raw["decision"], "finding_ids": findings, "required": required, "reviewed_input_root": reviewed_input_root, "tradeoff_ids": tradeoffs}
    if review_root != digest(adjudication_without_root):
        raise ProductProgramError("selection adjudication review root is stale")
    early = id_list(item["early_stop_rules"], "early-stop rules", allowed=STOP_IDS)
    return {
        "adjudication": {**adjudication_without_root, "review_root": review_root},
        "authority_premise": authority_premise,
        "dimensions": dimensions,
        "disposition": disposition,
        "early_stop_rules": early,
        "lanes": lanes,
        "operator_ceiling": ceiling,
        "rejected_candidates": rejected,
        "scheduling_groups": groups,
        "selected_candidate_ids": selected,
        "selector_id": selector_id,
        "aggregate_budget": aggregate,
        "unused_capacity": unused,
    }


def authority() -> dict[str, Any]:
    return {"application_allowed": False, "direct_effects_allowed": False, "posture": "derived-nonauthorizing"}


def build_artifacts(packet: Mapping[str, Any], inventory: Mapping[str, Any], reflection: Mapping[str, Any], resource_source: Mapping[str, Any], resource: Mapping[str, Any], capacity_source: Mapping[str, Any], submission: Mapping[str, Any]) -> dict[str, Any]:
    verify_packet(packet); verify_reflection(packet, reflection, inventory); verify_resource_evidence(packet, resource_source, resource)
    normalized = normalize_submission(packet, reflection, resource, capacity_source, submission)
    currentness_root = digest({"kind": "product-program-selection-currentness", "packet_currentness_root": packet["currentness_root"], "packet_root": packet["artifact_root"], "reflection_root": reflection["artifact_root"], "resource_evidence_root": resource["artifact_root"]})
    selection: dict[str, Any] = {
        "adjudicator_id": normalized["adjudication"]["adjudicator_id"], "authority": authority(), "currentness_root": currentness_root,
        "dimensions": normalized["dimensions"], "disposition": normalized["disposition"], "kind": "product-program-selection",
        "packet_root": packet["artifact_root"], "rationale": {"adjudication": normalized["adjudication"], "authority_premise": normalized["authority_premise"], "selected_candidate_ids": normalized["selected_candidate_ids"]},
        "reflection_root": reflection["artifact_root"], "rejected_candidates": normalized["rejected_candidates"], "resource_evidence_root": resource["artifact_root"],
        "schema_version": 1, "selection_root": "", "selector_id": normalized["selector_id"],
    }
    if set(selection) != artifact_fields("product-program-selection"):
        raise ProductProgramError("selection artifact differs from frozen schema")
    selection["selection_root"] = digest({key: selection[key] for key in selection if key != "selection_root"})
    placement = DISPOSITION_PLACEMENTS[normalized["disposition"]]
    portfolio: dict[str, Any] = {
        "aggregate_budget": normalized["aggregate_budget"], "authority": authority(), "currentness_root": currentness_root,
        "dependency_edges": sorted([[dependency, lane["lane_id"]] for lane in normalized["lanes"] for dependency in lane["dependency_lane_ids"]]),
        "disposition": normalized["disposition"], "early_stop_rules": normalized["early_stop_rules"], "kind": "product-program-portfolio",
        "lanes": normalized["lanes"], "placement": placement, "portfolio_root": "", "scheduling_groups": normalized["scheduling_groups"],
        "schema_version": 1, "selection_root": selection["selection_root"], "unused_capacity": normalized["unused_capacity"],
    }
    if set(portfolio) != artifact_fields("product-program-portfolio"):
        raise ProductProgramError("portfolio artifact differs from frozen schema")
    portfolio["portfolio_root"] = digest({key: portfolio[key] for key in portfolio if key != "portfolio_root"})
    handoff: dict[str, Any] = {
        "authority": authority(), "currentness_root": currentness_root, "disposition": normalized["disposition"],
        "expected_effect": {"candidate_ids": normalized["selected_candidate_ids"], "evidence_posture": "falsifiable-derived-projection"},
        "handoff_root": "", "kind": "product-program-placement-handoff", "nonauthorization": "receiving-owner-must-revalidate",
        "owner": OWNER_BY_PLACEMENT[placement], "placement": placement, "portfolio_root": portfolio["portfolio_root"],
        "preconditions": {"accepted_blocks": packet["range"]["accepted_blocks"], "currentness_root": currentness_root, "requested_blocks": packet["range"]["requested_blocks"], "resource_ceiling": normalized["operator_ceiling"], "source_roots": [packet["artifact_root"], reflection["artifact_root"], resource["artifact_root"], normalized["operator_ceiling"]["source_root"]]},
        "schema_version": 1, "stop": "before-tracker-task-source-or-external-effect",
    }
    if set(handoff) != artifact_fields("product-program-placement-handoff"):
        raise ProductProgramError("handoff artifact differs from frozen schema")
    handoff["handoff_root"] = digest({key: handoff[key] for key in handoff if key != "handoff_root"})
    result = {"handoff": handoff, "portfolio": portfolio, "selection": selection}
    verify_artifacts(packet, inventory, reflection, resource_source, resource, capacity_source, result)
    return result


def verify_artifacts(packet: Mapping[str, Any], inventory: Mapping[str, Any], reflection: Mapping[str, Any], resource_source: Mapping[str, Any], resource: Mapping[str, Any], capacity_source: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
    exact_keys(value, {"handoff", "portfolio", "selection"}, "selection artifact bundle")
    selection, portfolio, handoff = value["selection"], value["portfolio"], value["handoff"]
    exact_keys(selection, artifact_fields("product-program-selection"), "selection")
    exact_keys(portfolio, artifact_fields("product-program-portfolio"), "portfolio")
    exact_keys(handoff, artifact_fields("product-program-placement-handoff"), "handoff")
    verify_packet(packet); verify_reflection(packet, reflection, inventory); verify_resource_evidence(packet, resource_source, resource)
    for artifact in (selection, portfolio, handoff):
        if artifact["schema_version"] != 1 or artifact["authority"] != authority():
            raise ProductProgramError("selection bundle asserts authority or differs in version")
    if selection["selection_root"] != digest({key: selection[key] for key in selection if key != "selection_root"}):
        raise ProductProgramError("selection root is stale")
    if portfolio["portfolio_root"] != digest({key: portfolio[key] for key in portfolio if key != "portfolio_root"}) or portfolio["selection_root"] != selection["selection_root"]:
        raise ProductProgramError("portfolio root or selection binding is stale")
    if handoff["handoff_root"] != digest({key: handoff[key] for key in handoff if key != "handoff_root"}) or handoff["portfolio_root"] != portfolio["portfolio_root"]:
        raise ProductProgramError("handoff root or portfolio binding is stale")
    rebuilt_submission = {
        "adjudication": selection["rationale"]["adjudication"], "dimensions": selection["dimensions"], "disposition": selection["disposition"],
        "early_stop_rules": portfolio["early_stop_rules"], "kind": "product-program-selection-submission", "lanes": portfolio["lanes"],
        "authority_premise": selection["rationale"]["authority_premise"], "packet_root": selection["packet_root"], "reflection_root": selection["reflection_root"],
        "rejected_candidates": selection["rejected_candidates"], "resource_evidence_root": selection["resource_evidence_root"], "schema_version": 1,
        "scheduling_groups": portfolio["scheduling_groups"], "selected_candidate_ids": selection["rationale"]["selected_candidate_ids"], "selector_id": selection["selector_id"],
    }
    rebuilt = build_artifacts_unverified(packet, reflection, resource, capacity_source, rebuilt_submission)
    if rebuilt != value:
        raise ProductProgramError("selection bundle differs from deterministic reconstruction")
    return {"handoff_root": handoff["handoff_root"], "portfolio_root": portfolio["portfolio_root"], "selection_root": selection["selection_root"], "verified": True}


def build_artifacts_unverified(packet: Mapping[str, Any], reflection: Mapping[str, Any], resource: Mapping[str, Any], capacity_source: Mapping[str, Any], submission: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_submission(packet, reflection, resource, capacity_source, submission)
    currentness_root = digest({"kind": "product-program-selection-currentness", "packet_currentness_root": packet["currentness_root"], "packet_root": packet["artifact_root"], "reflection_root": reflection["artifact_root"], "resource_evidence_root": resource["artifact_root"]})
    selection = {"adjudicator_id": normalized["adjudication"]["adjudicator_id"], "authority": authority(), "currentness_root": currentness_root, "dimensions": normalized["dimensions"], "disposition": normalized["disposition"], "kind": "product-program-selection", "packet_root": packet["artifact_root"], "rationale": {"adjudication": normalized["adjudication"], "authority_premise": normalized["authority_premise"], "selected_candidate_ids": normalized["selected_candidate_ids"]}, "reflection_root": reflection["artifact_root"], "rejected_candidates": normalized["rejected_candidates"], "resource_evidence_root": resource["artifact_root"], "schema_version": 1, "selection_root": "", "selector_id": normalized["selector_id"]}
    selection["selection_root"] = digest({key: selection[key] for key in selection if key != "selection_root"})
    placement = DISPOSITION_PLACEMENTS[normalized["disposition"]]
    portfolio = {"aggregate_budget": normalized["aggregate_budget"], "authority": authority(), "currentness_root": currentness_root, "dependency_edges": sorted([[dependency, lane["lane_id"]] for lane in normalized["lanes"] for dependency in lane["dependency_lane_ids"]]), "disposition": normalized["disposition"], "early_stop_rules": normalized["early_stop_rules"], "kind": "product-program-portfolio", "lanes": normalized["lanes"], "placement": placement, "portfolio_root": "", "scheduling_groups": normalized["scheduling_groups"], "schema_version": 1, "selection_root": selection["selection_root"], "unused_capacity": normalized["unused_capacity"]}
    portfolio["portfolio_root"] = digest({key: portfolio[key] for key in portfolio if key != "portfolio_root"})
    handoff = {"authority": authority(), "currentness_root": currentness_root, "disposition": normalized["disposition"], "expected_effect": {"candidate_ids": normalized["selected_candidate_ids"], "evidence_posture": "falsifiable-derived-projection"}, "handoff_root": "", "kind": "product-program-placement-handoff", "nonauthorization": "receiving-owner-must-revalidate", "owner": OWNER_BY_PLACEMENT[placement], "placement": placement, "portfolio_root": portfolio["portfolio_root"], "preconditions": {"accepted_blocks": packet["range"]["accepted_blocks"], "currentness_root": currentness_root, "requested_blocks": packet["range"]["requested_blocks"], "resource_ceiling": normalized["operator_ceiling"], "source_roots": [packet["artifact_root"], reflection["artifact_root"], resource["artifact_root"], normalized["operator_ceiling"]["source_root"]]}, "schema_version": 1, "stop": "before-tracker-task-source-or-external-effect"}
    handoff["handoff_root"] = digest({key: handoff[key] for key in handoff if key != "handoff_root"})
    return {"handoff": handoff, "portfolio": portfolio, "selection": selection}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__); commands = result.add_subparsers(dest="command", required=True)
    for name in ("build", "verify", "reuse"):
        command = commands.add_parser(name)
        command.add_argument("--packet", required=True); command.add_argument("--inventory", required=True); command.add_argument("--reflection", required=True)
        command.add_argument("--resource-source", required=True); command.add_argument("--resource-evidence", required=True)
        command.add_argument("--capacity-source", required=True)
        command.add_argument("--submission" if name == "build" else "--bundle", required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        packet=read_json_file(args.packet,"packet"); inventory=read_json_file(args.inventory,"inventory"); reflection=read_json_file(args.reflection,"reflection")
        source=read_json_file(args.resource_source,"resource source"); resource=read_json_file(args.resource_evidence,"resource evidence")
        capacity=read_json_file(args.capacity_source,"operator capacity source")
        if args.command == "build": output={"action":"portfolio-handoff-ready","bundle":build_artifacts(packet,inventory,reflection,source,resource,capacity,read_json_file(args.submission,"selection submission"))}
        else:
            bundle=read_json_file(args.bundle,"selection bundle"); verified=verify_artifacts(packet,inventory,reflection,source,resource,capacity,bundle)
            output=verified if args.command == "verify" else {"action":"selection-bundle-reused","bundle":bundle,"cognitive_work_started":False,"model_calls":0,**verified}
    except (OSError,ProductProgramError) as exc:
        print(json.dumps({"error":str(exc)},sort_keys=True),file=sys.stderr); return 2
    sys.stdout.buffer.write(canonical(output)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
