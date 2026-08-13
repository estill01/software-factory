#!/usr/bin/env python3
"""Build and verify typed product-program resource/outcome evidence."""

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
    RESOURCE_EVIDENCE_CLASSES,
    canonical,
    digest,
    exact_id,
    exact_keys,
    load_json_bytes,
    read_json_file,
    verify_packet,
)


SCHEMA_VERSION = 1
TRANSFORMATION_VERSION = "product-program-resource-evidence-v1"
MAX_WORK_CLASSES = 32
MAX_EVIDENCE_IDS = 32
MAX_TEXT = 1000
OUTCOME_DIMENSIONS = (
    "completion",
    "product_effect",
    "protected_capability_result",
    "recurrence_reach",
    "compounding_value",
    "reuse",
    "reversibility",
    "opportunity_cost",
)
RESOURCE_DIMENSIONS = (
    "elapsed_time",
    "tokens",
    "commands",
    "tools",
    "validation_review",
    "integration",
    "rework",
    "reopened_findings",
    "incidents",
    "rollbacks",
    "user_corrections",
)
RESOURCE_UNITS = {
    "elapsed_time": "seconds",
    "tokens": "tokens",
    "commands": "count",
    "tools": "count",
    "validation_review": "count",
    "integration": "count",
    "rework": "count",
    "reopened_findings": "count",
    "incidents": "count",
    "rollbacks": "count",
    "user_corrections": "count",
}
OUTCOME_VALUES = {
    "completion": {"abandoned", "completed", "failed", "partial", "unavailable"},
    "product_effect": {"beneficial", "harmful", "mixed", "no-detected-effect", "unavailable"},
    "protected_capability_result": {"mixed", "preserved", "regressed", "unavailable"},
    "recurrence_reach": {"broad", "local", "one-off", "recurrent", "unavailable"},
    "compounding_value": {"compounding", "limited", "none", "reusable", "unavailable"},
    "reuse": {"none", "partial", "substantial", "unavailable"},
    "reversibility": {"costly", "irreversible", "reversible", "unavailable"},
    "opportunity_cost": {"high", "low", "medium", "unavailable"},
}
LIMITATIONS = [
    "dimension-by-dimension-prior-not-an-aggregate-score",
    "no-provider-billing-or-spend-authority",
    "observed-association-is-not-causal-proof",
    "rare-high-value-work-must-remain-visible",
]
FORBIDDEN_INPUT_KEYS = {
    "actual_cost",
    "billing",
    "cost",
    "price",
    "rank",
    "ranking",
    "score",
    "spend",
    "total",
    "utility",
    "weighted_score",
}


def bounded_text(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > MAX_TEXT
        or any(ord(character) < 32 and character not in "\n\t" for character in value)
    ):
        raise ProductProgramError(f"{label} must be nonempty normalized bounded text")
    return value


def reject_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_INPUT_KEYS:
                raise ProductProgramError("resource input contains an aggregate, billing, spend, or ranking field")
            reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            reject_forbidden(item)


def evidence_universe(packet: Mapping[str, Any]) -> set[str]:
    result = set(packet["outcome"]["evidence_ids"])
    result.update(item["capability_id"] for item in packet["protected_capabilities"])
    for field in ("product_sources", "reports", "resource_sources", "decisions", "incidents"):
        result.update(item["source_id"] for item in packet[field])
    return result


def evidence_ids(value: Any, label: str, allowed: set[str]) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_EVIDENCE_IDS
        or not all(isinstance(item, str) for item in value)
    ):
        raise ProductProgramError(f"{label} must be a nonempty bounded evidence-ID array")
    result = [exact_id(item, f"{label} item") for item in value]
    if result != sorted(set(result)) or not set(result) <= allowed:
        raise ProductProgramError(f"{label} has duplicate, unsorted, or dangling evidence")
    return result


def normalize_evidence_class(value: Any, label: str) -> str:
    if value not in RESOURCE_EVIDENCE_CLASSES:
        raise ProductProgramError(f"{label} has an unsupported evidence class")
    return str(value)


def normalize_outcome_measure(
    value: Any, dimension: str, allowed_evidence: set[str]
) -> dict[str, Any]:
    item = exact_keys(
        value,
        {"evidence_class", "evidence_ids", "uncertainty", "value"},
        f"{dimension} outcome",
    )
    evidence_class = normalize_evidence_class(item["evidence_class"], f"{dimension} outcome")
    outcome_value = item["value"]
    if outcome_value not in OUTCOME_VALUES[dimension]:
        raise ProductProgramError(f"{dimension} outcome value is unsupported")
    uncertainty = bounded_text(item["uncertainty"], f"{dimension} uncertainty")
    ids = evidence_ids(item["evidence_ids"], f"{dimension} evidence IDs", allowed_evidence)
    if evidence_class == "unavailable":
        if outcome_value != "unavailable":
            raise ProductProgramError(f"{dimension} unavailable evidence has a claimed value")
    elif outcome_value == "unavailable":
        raise ProductProgramError(f"{dimension} available evidence lacks a value")
    if evidence_class == "estimated" and dimension in {
        "completion",
        "product_effect",
        "protected_capability_result",
    }:
        raise ProductProgramError(f"{dimension} cannot be fabricated from an estimate")
    return {
        "evidence_class": evidence_class,
        "evidence_ids": ids,
        "uncertainty": uncertainty,
        "value": outcome_value,
    }


def normalize_resource_measure(
    value: Any, dimension: str, allowed_evidence: set[str]
) -> dict[str, Any]:
    item = exact_keys(
        value,
        {"evidence_class", "evidence_ids", "lower", "uncertainty", "unit", "upper"},
        f"{dimension} resource",
    )
    evidence_class = normalize_evidence_class(item["evidence_class"], f"{dimension} resource")
    ids = evidence_ids(item["evidence_ids"], f"{dimension} evidence IDs", allowed_evidence)
    uncertainty = bounded_text(item["uncertainty"], f"{dimension} uncertainty")
    if item["unit"] != RESOURCE_UNITS[dimension]:
        raise ProductProgramError(f"{dimension} resource unit differs")
    lower, upper = item["lower"], item["upper"]
    if evidence_class == "unavailable":
        if lower is not None or upper is not None:
            raise ProductProgramError(f"{dimension} unavailable evidence has a numeric value")
    else:
        if (
            type(lower) is not int
            or type(upper) is not int
            or lower < 0
            or upper < lower
        ):
            raise ProductProgramError(f"{dimension} resource bounds are invalid")
        if evidence_class in {"observed", "provider-reported"} and lower != upper:
            raise ProductProgramError(f"{dimension} direct evidence cannot claim an estimated range")
    if evidence_class == "provider-reported" and dimension != "tokens":
        raise ProductProgramError("provider-reported evidence is supported only for token counts")
    return {
        "evidence_class": evidence_class,
        "evidence_ids": ids,
        "lower": lower,
        "uncertainty": uncertainty,
        "unit": item["unit"],
        "upper": upper,
    }


def normalize_estimation_profile(value: Any, allowed_evidence: set[str]) -> dict[str, Any]:
    item = exact_keys(
        value,
        {"evidence_ids", "method", "profile_id", "version"},
        "estimation profile",
    )
    if type(item["version"]) is not int or item["version"] < 1:
        raise ProductProgramError("estimation profile version must be a positive integer")
    return {
        "evidence_ids": evidence_ids(
            item["evidence_ids"], "estimation profile evidence IDs", allowed_evidence
        ),
        "method": bounded_text(item["method"], "estimation profile method"),
        "profile_id": exact_id(item["profile_id"], "estimation profile ID"),
        "version": item["version"],
    }


def normalize_useful_yield(value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "comparison_posture",
            "outcome_dimensions",
            "resource_dimensions",
            "uncertainties",
        },
        "useful-yield prior",
    )
    if item["comparison_posture"] != "dimension-by-dimension-only":
        raise ProductProgramError("useful yield must remain dimension-by-dimension")
    if item["outcome_dimensions"] != list(OUTCOME_DIMENSIONS):
        raise ProductProgramError("useful yield omits or reorders an outcome dimension")
    if item["resource_dimensions"] != list(RESOURCE_DIMENSIONS):
        raise ProductProgramError("useful yield omits or reorders a resource dimension")
    uncertainties = item["uncertainties"]
    if (
        not isinstance(uncertainties, list)
        or not uncertainties
        or len(uncertainties) > 16
        or uncertainties != sorted(set(uncertainties))
    ):
        raise ProductProgramError("useful-yield uncertainties must be a sorted nonempty array")
    return {
        "comparison_posture": "dimension-by-dimension-only",
        "outcome_dimensions": list(OUTCOME_DIMENSIONS),
        "resource_dimensions": list(RESOURCE_DIMENSIONS),
        "uncertainties": [bounded_text(item, "useful-yield uncertainty") for item in uncertainties],
    }


def normalize_work_input(value: Any, allowed_evidence: set[str]) -> dict[str, Any]:
    item = exact_keys(
        value,
        {"outcomes", "resources", "useful_yield", "work_class_id"},
        "work-class input",
    )
    outcomes = exact_keys(item["outcomes"], set(OUTCOME_DIMENSIONS), "work-class outcomes")
    resources = exact_keys(item["resources"], set(RESOURCE_DIMENSIONS), "work-class resources")
    return {
        "outcomes": {
            dimension: normalize_outcome_measure(outcomes[dimension], dimension, allowed_evidence)
            for dimension in OUTCOME_DIMENSIONS
        },
        "resources": {
            dimension: normalize_resource_measure(resources[dimension], dimension, allowed_evidence)
            for dimension in RESOURCE_DIMENSIONS
        },
        "useful_yield": normalize_useful_yield(item["useful_yield"]),
        "work_class_id": exact_id(item["work_class_id"], "work-class ID"),
    }


def normalize_source(packet: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    verify_packet(packet)
    reject_forbidden(source)
    item = exact_keys(
        source,
        {
            "estimation_profile",
            "kind",
            "limitations",
            "resource_source_id",
            "schema_version",
            "transformation_version",
            "work_classes",
        },
        "resource source manifest",
    )
    if item["schema_version"] != SCHEMA_VERSION or item["kind"] != "product-program-resource-source":
        raise ProductProgramError("resource source manifest identity differs")
    if item["transformation_version"] != TRANSFORMATION_VERSION:
        raise ProductProgramError("resource source transformation differs")
    source_id = exact_id(item["resource_source_id"], "resource source ID")
    retained = {entry["source_id"]: entry for entry in packet["resource_sources"]}
    if source_id not in retained:
        raise ProductProgramError("resource source manifest is not retained by the packet")
    source_bytes = canonical(source)
    if (
        hashlib.sha256(source_bytes).hexdigest() != retained[source_id]["sha256"]
        or len(source_bytes) != retained[source_id]["byte_length"]
    ):
        raise ProductProgramError("resource source bytes differ from the packet binding")
    if item["limitations"] != LIMITATIONS:
        raise ProductProgramError("resource limitation contract differs")
    allowed_evidence = evidence_universe(packet)
    profile = normalize_estimation_profile(item["estimation_profile"], allowed_evidence)
    if (
        not isinstance(item["work_classes"], list)
        or not item["work_classes"]
        or len(item["work_classes"]) > MAX_WORK_CLASSES
    ):
        raise ProductProgramError("resource source requires bounded work classes")
    work_classes = [normalize_work_input(entry, allowed_evidence) for entry in item["work_classes"]]
    work_classes.sort(key=lambda entry: entry["work_class_id"])
    if len({entry["work_class_id"] for entry in work_classes}) != len(work_classes):
        raise ProductProgramError("resource source repeats a work-class ID")
    outcome_evidence = set(packet["outcome"]["evidence_ids"])
    outcome_evidence.update(entry["capability_id"] for entry in packet["protected_capabilities"])
    for field in ("product_sources", "decisions", "incidents"):
        outcome_evidence.update(entry["source_id"] for entry in packet[field])
    raw_resource_ids = set(retained) - {source_id}
    if not raw_resource_ids:
        raise ProductProgramError("resource source manifest requires separately retained raw resource evidence")
    attributed: set[tuple[str, str]] = set()
    for work_class in work_classes:
        for dimension, measure in work_class["outcomes"].items():
            if not set(measure["evidence_ids"]) & outcome_evidence:
                raise ProductProgramError(
                    f"{dimension} outcome relies only on report or resource hypotheses"
                )
        for dimension, measure in work_class["resources"].items():
            supporting_resources = set(measure["evidence_ids"]) & raw_resource_ids
            if not supporting_resources:
                raise ProductProgramError(
                    f"{dimension} resource lacks a separately retained resource source"
                )
            if not any(
                retained[evidence_id]["evidence_class"] == measure["evidence_class"]
                for evidence_id in supporting_resources
            ):
                raise ProductProgramError(
                    f"{dimension} resource evidence class differs from its retained source"
                )
            if (
                measure["evidence_class"] == "estimated"
                and not supporting_resources & set(profile["evidence_ids"])
            ):
                raise ProductProgramError(
                    f"{dimension} estimate is not covered by the retained estimation profile"
                )
            for evidence_id in supporting_resources:
                attribution = (dimension, evidence_id)
                if attribution in attributed:
                    raise ProductProgramError("resource evidence is attributed to multiple work classes")
                attributed.add(attribution)
    return {
        "estimation_profile": profile,
        "kind": "product-program-resource-source",
        "limitations": list(LIMITATIONS),
        "resource_source_id": source_id,
        "schema_version": SCHEMA_VERSION,
        "transformation_version": TRANSFORMATION_VERSION,
        "work_classes": work_classes,
    }


def artifact_fields() -> set[str]:
    contract = load_json_bytes(
        (SCRIPT_DIR.parents[0] / "fixtures" / "product_program_contract_v1.json").read_bytes(),
        "contract fixture",
    )
    return set(contract["artifact_schemas"]["product-program-resource-evidence"])


def authority() -> dict[str, Any]:
    return {
        "allocation_allowed": False,
        "billing_claim": False,
        "direct_effects_allowed": False,
        "posture": "derived-nonauthorizing",
        "selection_allowed": False,
    }


def normalize_prior_row(value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {"outcomes", "resources", "row_root", "source_input_root", "useful_yield", "work_class_id"},
        "prior work-class row",
    )
    exact_id(item["work_class_id"], "prior work-class ID")
    if item["source_input_root"] != digest(
        {
            "outcomes": item["outcomes"],
            "resources": item["resources"],
            "useful_yield": item["useful_yield"],
            "work_class_id": item["work_class_id"],
        }
    ):
        raise ProductProgramError("prior work-class source root is stale")
    expected = digest({key: item[key] for key in item if key != "row_root"})
    if item["row_root"] != expected:
        raise ProductProgramError("prior work-class row root is stale")
    return dict(item)


def normalize_prior_artifact(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    exact_keys(value, artifact_fields(), "prior resource evidence")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["kind"] != "product-program-resource-evidence"
        or value["transformation_version"] != TRANSFORMATION_VERSION
        or value["authority"] != authority()
        or value["limitations"] != LIMITATIONS
    ):
        raise ProductProgramError("prior resource evidence contract differs")
    if digest({key: value[key] for key in value if key != "artifact_root"}) != value["artifact_root"]:
        raise ProductProgramError("prior resource evidence artifact root is stale")
    if not isinstance(value["work_classes"], list):
        raise ProductProgramError("prior resource evidence work classes differ")
    rows = [normalize_prior_row(row) for row in value["work_classes"]]
    rows.sort(key=lambda row: row["work_class_id"])
    if rows != value["work_classes"] or len({row["work_class_id"] for row in rows}) != len(rows):
        raise ProductProgramError("prior resource evidence rows are not normalized")
    return rows


def build_resource_evidence(
    packet: Mapping[str, Any],
    source: Mapping[str, Any],
    prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_source(packet, source)
    prior_by_id: dict[str, dict[str, Any]] = {}
    if prior is not None:
        prior_by_id = {row["work_class_id"]: row for row in normalize_prior_artifact(prior)}
    rows: list[dict[str, Any]] = []
    for entry in normalized["work_classes"]:
        source_input_root = digest(entry)
        prior_row = prior_by_id.get(entry["work_class_id"])
        if prior_row is not None and prior_row["source_input_root"] == source_input_root:
            rows.append(prior_row)
            continue
        row = {**entry, "source_input_root": source_input_root}
        row["row_root"] = digest(row)
        rows.append(row)
    currentness_root = digest(
        {
            "kind": "product-program-resource-currentness",
            "packet_currentness_root": packet["currentness_root"],
            "packet_root": packet["artifact_root"],
            "resource_source_root": hashlib.sha256(canonical(source)).hexdigest(),
            "transformation_version": TRANSFORMATION_VERSION,
        }
    )
    result: dict[str, Any] = {
        "artifact_root": "",
        "authority": authority(),
        "currentness_root": currentness_root,
        "estimation_profile": normalized["estimation_profile"],
        "kind": "product-program-resource-evidence",
        "limitations": normalized["limitations"],
        "packet_id": packet["packet_id"],
        "packet_root": packet["artifact_root"],
        "schema_version": SCHEMA_VERSION,
        "transformation_version": TRANSFORMATION_VERSION,
        "work_classes": rows,
    }
    if set(result) != artifact_fields():
        raise ProductProgramError("resource artifact implementation differs from the frozen schema")
    result["artifact_root"] = digest({key: result[key] for key in result if key != "artifact_root"})
    verify_resource_evidence(packet, source, result)
    return result


def verify_resource_evidence(
    packet: Mapping[str, Any], source: Mapping[str, Any], artifact: Mapping[str, Any]
) -> dict[str, Any]:
    exact_keys(artifact, artifact_fields(), "resource evidence")
    normalized = normalize_source(packet, source)
    if artifact["schema_version"] != SCHEMA_VERSION or artifact["kind"] != "product-program-resource-evidence":
        raise ProductProgramError("resource evidence identity differs")
    if artifact["transformation_version"] != TRANSFORMATION_VERSION:
        raise ProductProgramError("resource evidence transformation differs")
    if artifact["packet_id"] != packet["packet_id"] or artifact["packet_root"] != packet["artifact_root"]:
        raise ProductProgramError("resource evidence packet binding is stale")
    if artifact["authority"] != authority():
        raise ProductProgramError("resource evidence asserts allocation, billing, selection, or effects")
    if artifact["limitations"] != LIMITATIONS:
        raise ProductProgramError("resource evidence limitation contract differs")
    if artifact["estimation_profile"] != normalized["estimation_profile"]:
        raise ProductProgramError("resource evidence estimation profile differs")
    expected_currentness = digest(
        {
            "kind": "product-program-resource-currentness",
            "packet_currentness_root": packet["currentness_root"],
            "packet_root": packet["artifact_root"],
            "resource_source_root": hashlib.sha256(canonical(source)).hexdigest(),
            "transformation_version": TRANSFORMATION_VERSION,
        }
    )
    if artifact["currentness_root"] != expected_currentness:
        raise ProductProgramError("resource evidence currentness is stale")
    if not isinstance(artifact["work_classes"], list):
        raise ProductProgramError("resource evidence work classes differ")
    actual_rows = [normalize_prior_row(row) for row in artifact["work_classes"]]
    actual_rows.sort(key=lambda row: row["work_class_id"])
    if actual_rows != artifact["work_classes"]:
        raise ProductProgramError("resource evidence rows are not normalized")
    expected_inputs = normalized["work_classes"]
    if [row["work_class_id"] for row in actual_rows] != [row["work_class_id"] for row in expected_inputs]:
        raise ProductProgramError("resource evidence work classes differ from source")
    for row, source_row in zip(actual_rows, expected_inputs):
        if row["source_input_root"] != digest(source_row):
            raise ProductProgramError("resource evidence row is stale")
        for key in ("outcomes", "resources", "useful_yield", "work_class_id"):
            if row[key] != source_row[key]:
                raise ProductProgramError("resource evidence row differs from source")
    expected_root = digest({key: artifact[key] for key in artifact if key != "artifact_root"})
    if artifact["artifact_root"] != expected_root:
        raise ProductProgramError("resource evidence artifact root is stale")
    return {
        "artifact_root": expected_root,
        "currentness_root": expected_currentness,
        "verified": True,
    }


def reuse_resource_evidence(
    packet: Mapping[str, Any], source: Mapping[str, Any], artifact: Mapping[str, Any]
) -> dict[str, Any]:
    verified = verify_resource_evidence(packet, source, artifact)
    return {
        "action": "resource-evidence-reused",
        "artifact_root": verified["artifact_root"],
        "cognitive_work_started": False,
        "model_calls": 0,
        "resource_evidence": artifact,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--packet", required=True)
    build.add_argument("--source", required=True)
    build.add_argument("--prior-evidence")
    verify = commands.add_parser("verify")
    verify.add_argument("--packet", required=True)
    verify.add_argument("--source", required=True)
    verify.add_argument("--resource-evidence", required=True)
    reuse = commands.add_parser("reuse")
    reuse.add_argument("--packet", required=True)
    reuse.add_argument("--source", required=True)
    reuse.add_argument("--resource-evidence", required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        packet = read_json_file(args.packet, "packet")
        source = read_json_file(args.source, "resource source")
        if args.command == "build":
            prior = (
                read_json_file(args.prior_evidence, "prior resource evidence")
                if args.prior_evidence
                else None
            )
            output = {
                "action": "resource-evidence-built",
                "resource_evidence": build_resource_evidence(packet, source, prior),
            }
        else:
            artifact = read_json_file(args.resource_evidence, "resource evidence")
            output = (
                verify_resource_evidence(packet, source, artifact)
                if args.command == "verify"
                else reuse_resource_evidence(packet, source, artifact)
            )
    except (OSError, ProductProgramError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
