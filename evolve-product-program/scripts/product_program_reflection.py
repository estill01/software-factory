#!/usr/bin/env python3
"""Validate and root bounded product-program reflection artifacts."""

from __future__ import annotations

import argparse
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


SCHEMA_VERSION = 1
MAX_RECORDS = 24
MAX_LIST = 32
MAX_TEXT = 2000
CANDIDATE_TYPES = {
    "architecture",
    "capability-area",
    "current-program-revision",
    "experiment",
    "feature",
    "operations",
    "refactor",
    "removal",
    "simplification",
    "successor-program",
}
ALL_CANDIDATE_TYPES = CANDIDATE_TYPES | {"continue-unchanged"}
CATEGORY_DISPOSITIONS = {"out-of-mission", "searched-no-support", "supported"}
COUNTEREXAMPLE_POSTURES = {"bounded-uncertainty", "observed", "searched-none-found"}
ARCHITECTURE_LEVELS = {
    "bounded-reusable",
    "generalized-platform",
    "local",
    "no-change",
    "program-structural",
}
FORBIDDEN_KEYS = {
    "adopted",
    "body",
    "budget",
    "content",
    "credential",
    "credentials",
    "hidden_reasoning",
    "placement",
    "prompt",
    "rank",
    "raw_content",
    "raw_output",
    "raw_transcript",
    "reasoning",
    "schedule",
    "score",
    "secret",
    "secrets",
    "selected",
    "transcript",
    "winner",
}


def semantic_text(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > MAX_TEXT
        or any(ord(character) < 32 and character not in "\n\t" for character in value)
    ):
        raise ProductProgramError(f"{label} must be nonempty normalized bounded text")
    return value


def semantic_ids(
    value: Any,
    label: str,
    *,
    allowed: set[str] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_LIST:
        raise ProductProgramError(f"{label} must be a bounded ID array")
    result = [exact_id(item, f"{label} item") for item in value]
    if not result and not allow_empty:
        raise ProductProgramError(f"{label} must not be empty")
    if result != sorted(set(result)):
        raise ProductProgramError(f"{label} must be sorted and unique")
    if allowed is not None and not set(result) <= allowed:
        raise ProductProgramError(f"{label} has a dangling evidence reference")
    return result


def semantic_strings(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_LIST:
        raise ProductProgramError(f"{label} must be a bounded text array")
    result = [semantic_text(item, f"{label} item") for item in value]
    if not result and not allow_empty:
        raise ProductProgramError(f"{label} must not be empty")
    if result != sorted(set(result)):
        raise ProductProgramError(f"{label} must be sorted and unique")
    return result


def reject_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ProductProgramError("reflection contains selection or hidden-output state")
            reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            reject_forbidden(item)


def evidence_sets(packet: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    adjudicating = set(packet["outcome"]["evidence_ids"])
    adjudicating.update(item["capability_id"] for item in packet["protected_capabilities"])
    for field in ("product_sources", "decisions", "incidents"):
        adjudicating.update(item["source_id"] for item in packet[field])
    reports = {item["source_id"] for item in packet["reports"]}
    return adjudicating, adjudicating | reports


def evidence_ids(
    value: Any,
    label: str,
    *,
    allowed: set[str],
    adjudicating: set[str],
    allow_empty: bool = False,
) -> list[str]:
    result = semantic_ids(value, label, allowed=allowed, allow_empty=allow_empty)
    if result and not set(result) & adjudicating:
        raise ProductProgramError(f"{label} relies only on report hypotheses")
    return result


def normalize_observations(
    value: Any, *, allowed_evidence: set[str], adjudicating: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_RECORDS:
        raise ProductProgramError("observations must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(raw, {"evidence_ids", "observation_id", "summary", "valence"}, "observation")
        valence = item["valence"]
        if valence not in {"contrary", "exception", "harmful", "mixed", "productive"}:
            raise ProductProgramError("observation valence is unsupported")
        result.append(
            {
                "evidence_ids": evidence_ids(
                    item["evidence_ids"],
                    "observation evidence IDs",
                    allowed=allowed_evidence,
                    adjudicating=adjudicating,
                ),
                "observation_id": exact_id(item["observation_id"], "observation ID"),
                "summary": semantic_text(item["summary"], "observation summary"),
                "valence": valence,
            }
        )
    result.sort(key=lambda item: item["observation_id"])
    if len({item["observation_id"] for item in result}) != len(result):
        raise ProductProgramError("observations repeat an ID")
    return result


def normalize_lessons(value: Any, *, observation_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_RECORDS:
        raise ProductProgramError("lessons must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(
            raw,
            {
                "applicability",
                "confidence",
                "counterexample_observation_ids",
                "counterexample_posture",
                "counterexample_search",
                "lesson_id",
                "observation_ids",
                "statement",
                "uncertainty",
            },
            "lesson",
        )
        posture = item["counterexample_posture"]
        if posture not in COUNTEREXAMPLE_POSTURES:
            raise ProductProgramError("lesson counterexample posture is unsupported")
        contrary = semantic_ids(
            item["counterexample_observation_ids"],
            "lesson counterexample observation IDs",
            allowed=observation_ids,
            allow_empty=True,
        )
        if (posture == "observed") != bool(contrary):
            raise ProductProgramError("lesson counterexample posture contradicts its observations")
        result.append(
            {
                "applicability": semantic_text(item["applicability"], "lesson applicability"),
                "confidence": semantic_text(item["confidence"], "lesson confidence"),
                "counterexample_observation_ids": contrary,
                "counterexample_posture": posture,
                "counterexample_search": semantic_text(item["counterexample_search"], "lesson counterexample search"),
                "lesson_id": exact_id(item["lesson_id"], "lesson ID"),
                "observation_ids": semantic_ids(
                    item["observation_ids"], "lesson observation IDs", allowed=observation_ids
                ),
                "statement": semantic_text(item["statement"], "lesson statement"),
                "uncertainty": semantic_text(item["uncertainty"], "lesson uncertainty"),
            }
        )
    result.sort(key=lambda item: item["lesson_id"])
    if len({item["lesson_id"] for item in result}) != len(result):
        raise ProductProgramError("lessons repeat an ID")
    return result


def normalize_meta_patterns(value: Any, *, lesson_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_RECORDS:
        raise ProductProgramError("meta-patterns must be a bounded array")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(
            raw,
            {
                "applicability",
                "counterexample_lesson_ids",
                "lesson_ids",
                "meta_pattern_id",
                "statement",
                "uncertainty",
            },
            "meta-pattern",
        )
        linked = semantic_ids(item["lesson_ids"], "meta-pattern lesson IDs", allowed=lesson_ids)
        if len(linked) < 2:
            raise ProductProgramError("meta-pattern must relate at least two lessons")
        result.append(
            {
                "applicability": semantic_text(item["applicability"], "meta-pattern applicability"),
                "counterexample_lesson_ids": semantic_ids(
                    item["counterexample_lesson_ids"],
                    "meta-pattern counterexample lessons",
                    allowed=lesson_ids,
                    allow_empty=True,
                ),
                "lesson_ids": linked,
                "meta_pattern_id": exact_id(item["meta_pattern_id"], "meta-pattern ID"),
                "statement": semantic_text(item["statement"], "meta-pattern statement"),
                "uncertainty": semantic_text(item["uncertainty"], "meta-pattern uncertainty"),
            }
        )
    result.sort(key=lambda item: item["meta_pattern_id"])
    if len({item["meta_pattern_id"] for item in result}) != len(result):
        raise ProductProgramError("meta-patterns repeat an ID")
    return result


def normalize_category_search(
    value: Any, *, allowed_evidence: set[str], adjudicating: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) < 2 or len(value) > len(CANDIDATE_TYPES):
        raise ProductProgramError("candidate category search must compare at least two bounded categories")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(raw, {"candidate_type", "disposition", "evidence_ids", "rationale"}, "category search")
        candidate_type = item["candidate_type"]
        disposition = item["disposition"]
        if candidate_type not in CANDIDATE_TYPES or disposition not in CATEGORY_DISPOSITIONS:
            raise ProductProgramError("candidate category search value is unsupported")
        refs = evidence_ids(
            item["evidence_ids"],
            "category-search evidence IDs",
            allowed=allowed_evidence,
            adjudicating=adjudicating,
            allow_empty=disposition != "supported",
        )
        result.append(
            {
                "candidate_type": candidate_type,
                "disposition": disposition,
                "evidence_ids": refs,
                "rationale": semantic_text(item["rationale"], "category-search rationale"),
            }
        )
    result.sort(key=lambda item: item["candidate_type"])
    if len({item["candidate_type"] for item in result}) != len(result):
        raise ProductProgramError("candidate category search repeats a type")
    return result


def normalize_gaps(
    value: Any,
    *,
    observation_ids: set[str],
    lesson_ids: set[str],
    allowed_evidence: set[str],
    adjudicating: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_RECORDS:
        raise ProductProgramError("capability gaps must be a bounded array")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(
            raw,
            {
                "category_search",
                "desired_capability",
                "evidence_ids",
                "gap_id",
                "lesson_ids",
                "mission_boundary",
                "observation_ids",
                "statement",
                "uncertainty",
            },
            "capability gap",
        )
        result.append(
            {
                "category_search": normalize_category_search(
                    item["category_search"],
                    allowed_evidence=allowed_evidence,
                    adjudicating=adjudicating,
                ),
                "desired_capability": semantic_text(item["desired_capability"], "desired capability"),
                "evidence_ids": evidence_ids(
                    item["evidence_ids"],
                    "capability-gap evidence IDs",
                    allowed=allowed_evidence,
                    adjudicating=adjudicating,
                ),
                "gap_id": exact_id(item["gap_id"], "capability-gap ID"),
                "lesson_ids": semantic_ids(item["lesson_ids"], "capability-gap lesson IDs", allowed=lesson_ids),
                "mission_boundary": semantic_text(item["mission_boundary"], "capability-gap mission boundary"),
                "observation_ids": semantic_ids(
                    item["observation_ids"], "capability-gap observation IDs", allowed=observation_ids
                ),
                "statement": semantic_text(item["statement"], "capability-gap statement"),
                "uncertainty": semantic_text(item["uncertainty"], "capability-gap uncertainty"),
            }
        )
    result.sort(key=lambda item: item["gap_id"])
    if len({item["gap_id"] for item in result}) != len(result):
        raise ProductProgramError("capability gaps repeat an ID")
    return result


def normalize_candidates(
    value: Any,
    *,
    generator_id: str,
    gaps: Sequence[Mapping[str, Any]],
    allowed_evidence: set[str],
    adjudicating: set[str],
    capability_ids: set[str],
    candidate_ceiling: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > candidate_ceiling:
        raise ProductProgramError("candidates must be nonempty and within the declared ceiling")
    gap_ids = {item["gap_id"] for item in gaps}
    result: list[dict[str, Any]] = []
    expected = {
        "affected_capability_ids",
        "affected_user_ids",
        "architecture_evidence_ids",
        "architecture_level",
        "architecture_rationale",
        "author_owner",
        "candidate_id",
        "candidate_type",
        "counterexample_evidence_ids",
        "counterexample_posture",
        "counterexample_search",
        "desired_effect",
        "evaluation_owner",
        "evidence_ids",
        "falsifiable_outcome",
        "gap_ids",
        "implementation_owner",
        "protected_behavior",
        "selector_id",
        "smallest_sufficient_change",
        "uncertainty",
    }
    for raw in value:
        item = exact_keys(raw, expected, "candidate")
        candidate_type = item["candidate_type"]
        if candidate_type not in ALL_CANDIDATE_TYPES:
            raise ProductProgramError("candidate type is unsupported")
        linked_gaps = semantic_ids(
            item["gap_ids"],
            "candidate gap IDs",
            allowed=gap_ids,
            allow_empty=candidate_type == "continue-unchanged",
        )
        if (candidate_type == "continue-unchanged") != (not linked_gaps):
            raise ProductProgramError("continue-unchanged and change candidates have inconsistent gaps")
        posture = item["counterexample_posture"]
        if posture not in COUNTEREXAMPLE_POSTURES:
            raise ProductProgramError("candidate counterexample posture is unsupported")
        counterexamples = evidence_ids(
            item["counterexample_evidence_ids"],
            "candidate counterexample evidence IDs",
            allowed=allowed_evidence,
            adjudicating=adjudicating,
            allow_empty=posture != "observed",
        )
        if (posture == "observed") != bool(counterexamples):
            raise ProductProgramError("candidate counterexample posture contradicts its evidence")
        roles = {
            generator_id,
            exact_id(item["author_owner"], "candidate author owner"),
            exact_id(item["evaluation_owner"], "candidate evaluation owner"),
            exact_id(item["implementation_owner"], "candidate implementation owner"),
            exact_id(item["selector_id"], "candidate selector ID"),
        }
        if len(roles) != 5:
            raise ProductProgramError("generator, selector, author, implementer, and evaluator must be distinct")
        architecture_level = item["architecture_level"]
        if architecture_level not in ARCHITECTURE_LEVELS:
            raise ProductProgramError("candidate architecture level is unsupported")
        architecture_refs = evidence_ids(
            item["architecture_evidence_ids"],
            "candidate architecture evidence IDs",
            allowed=allowed_evidence,
            adjudicating=adjudicating,
            allow_empty=architecture_level == "no-change",
        )
        if candidate_type == "continue-unchanged" and architecture_level != "no-change":
            raise ProductProgramError("continue-unchanged candidate must use no-change architecture")
        if candidate_type != "continue-unchanged" and architecture_level == "no-change":
            raise ProductProgramError("change candidate cannot use no-change architecture")
        if architecture_level == "generalized-platform" and len(architecture_refs) < 2:
            raise ProductProgramError("generalized platform lacks independent architecture support")
        result.append(
            {
                "affected_capability_ids": semantic_ids(
                    item["affected_capability_ids"],
                    "candidate affected capability IDs",
                    allowed=capability_ids,
                    allow_empty=True,
                ),
                "affected_user_ids": semantic_ids(item["affected_user_ids"], "candidate affected user IDs"),
                "architecture_evidence_ids": architecture_refs,
                "architecture_level": architecture_level,
                "architecture_rationale": semantic_text(item["architecture_rationale"], "candidate architecture rationale"),
                "author_owner": exact_id(item["author_owner"], "candidate author owner"),
                "candidate_id": exact_id(item["candidate_id"], "candidate ID"),
                "candidate_type": candidate_type,
                "counterexample_evidence_ids": counterexamples,
                "counterexample_posture": posture,
                "counterexample_search": semantic_text(item["counterexample_search"], "candidate counterexample search"),
                "desired_effect": semantic_text(item["desired_effect"], "candidate desired effect"),
                "evaluation_owner": exact_id(item["evaluation_owner"], "candidate evaluation owner"),
                "evidence_ids": evidence_ids(
                    item["evidence_ids"],
                    "candidate evidence IDs",
                    allowed=allowed_evidence,
                    adjudicating=adjudicating,
                ),
                "falsifiable_outcome": semantic_text(item["falsifiable_outcome"], "candidate falsifiable outcome"),
                "gap_ids": linked_gaps,
                "implementation_owner": exact_id(item["implementation_owner"], "candidate implementation owner"),
                "protected_behavior": semantic_strings(item["protected_behavior"], "candidate protected behavior"),
                "selector_id": exact_id(item["selector_id"], "candidate selector ID"),
                "smallest_sufficient_change": semantic_text(
                    item["smallest_sufficient_change"], "candidate smallest sufficient change"
                ),
                "uncertainty": semantic_text(item["uncertainty"], "candidate uncertainty"),
            }
        )
    result.sort(key=lambda item: item["candidate_id"])
    if len({item["candidate_id"] for item in result}) != len(result):
        raise ProductProgramError("candidates repeat an ID")
    if sum(item["candidate_type"] == "continue-unchanged" for item in result) != 1:
        raise ProductProgramError("candidate set requires exactly one no-change comparison")
    if not gaps and len(result) != 1:
        raise ProductProgramError("no-gap reflection may contain only continue-unchanged")
    if gaps and not any(item["candidate_type"] != "continue-unchanged" for item in result):
        raise ProductProgramError("supported gaps require at least one change candidate")
    by_gap = {gap_id: set() for gap_id in gap_ids}
    for candidate in result:
        for gap_id in candidate["gap_ids"]:
            by_gap[gap_id].add(candidate["candidate_type"])
    for gap in gaps:
        supported = {
            search["candidate_type"]
            for search in gap["category_search"]
            if search["disposition"] == "supported"
        }
        if not supported or by_gap[gap["gap_id"]] != supported:
            raise ProductProgramError("supported candidate categories and emitted candidates differ")
    return result


def reflection_fields() -> set[str]:
    path = SCRIPT_DIR.parents[0] / "fixtures" / "product_program_contract_v1.json"
    contract = load_json_bytes(path.read_bytes(), "contract fixture")
    return set(contract["artifact_schemas"]["product-program-reflection"])


def normalize_submission(packet: Mapping[str, Any], submission: Mapping[str, Any]) -> dict[str, Any]:
    verify_packet(packet)
    reject_forbidden(submission)
    item = exact_keys(
        submission,
        {
            "candidate_ceiling",
            "candidates",
            "capability_gaps",
            "counterexample_widening_used",
            "generation_pass_count",
            "generator_id",
            "kind",
            "lessons",
            "meta_patterns",
            "observations",
            "packet_id",
            "packet_root",
            "schema_version",
        },
        "reflection submission",
    )
    if item["schema_version"] != SCHEMA_VERSION or item["kind"] != "product-program-reflection-submission":
        raise ProductProgramError("reflection submission identity differs")
    if item["packet_id"] != packet["packet_id"] or item["packet_root"] != packet["artifact_root"]:
        raise ProductProgramError("reflection submission is stale for its packet")
    if type(item["generation_pass_count"]) is not int or item["generation_pass_count"] != 1:
        raise ProductProgramError("reflection requires exactly one high-resolution generation pass")
    if type(item["counterexample_widening_used"]) is not bool:
        raise ProductProgramError("counterexample widening posture must be boolean")
    candidate_ceiling = item["candidate_ceiling"]
    if type(candidate_ceiling) is not int or not 1 <= candidate_ceiling <= 12:
        raise ProductProgramError("candidate ceiling must be between 1 and 12")
    generator_id = exact_id(item["generator_id"], "reflection generator ID")
    adjudicating, allowed_evidence = evidence_sets(packet)
    observations = normalize_observations(
        item["observations"], allowed_evidence=allowed_evidence, adjudicating=adjudicating
    )
    observation_ids = {entry["observation_id"] for entry in observations}
    lessons = normalize_lessons(item["lessons"], observation_ids=observation_ids)
    lesson_ids = {entry["lesson_id"] for entry in lessons}
    meta_patterns = normalize_meta_patterns(item["meta_patterns"], lesson_ids=lesson_ids)
    gaps = normalize_gaps(
        item["capability_gaps"],
        observation_ids=observation_ids,
        lesson_ids=lesson_ids,
        allowed_evidence=allowed_evidence,
        adjudicating=adjudicating,
    )
    capability_ids = {entry["capability_id"] for entry in packet["protected_capabilities"]}
    candidates = normalize_candidates(
        item["candidates"],
        generator_id=generator_id,
        gaps=gaps,
        allowed_evidence=allowed_evidence,
        adjudicating=adjudicating,
        capability_ids=capability_ids,
        candidate_ceiling=candidate_ceiling,
    )
    return {
        "candidate_ceiling": candidate_ceiling,
        "candidates": candidates,
        "capability_gaps": gaps,
        "counterexample_widening_used": item["counterexample_widening_used"],
        "generator_id": generator_id,
        "lessons": lessons,
        "meta_patterns": meta_patterns,
        "observations": observations,
    }


def build_reflection(packet: Mapping[str, Any], submission: Mapping[str, Any]) -> dict[str, Any]:
    material = normalize_submission(packet, submission)
    currentness_root = digest(
        {
            "kind": "product-program-reflection-currentness",
            "packet_currentness_root": packet["currentness_root"],
            "packet_root": packet["artifact_root"],
        }
    )
    reflection: dict[str, Any] = {
        "artifact_root": "",
        "authority": {
            "direct_effects_allowed": False,
            "posture": "derived-nonauthorizing",
            "selection_allowed": False,
        },
        **material,
        "currentness_root": currentness_root,
        "kind": "product-program-reflection",
        "packet_id": packet["packet_id"],
        "packet_root": packet["artifact_root"],
        "schema_version": SCHEMA_VERSION,
    }
    if set(reflection) != reflection_fields():
        raise ProductProgramError("reflection implementation differs from the frozen schema")
    reflection["artifact_root"] = digest({key: reflection[key] for key in reflection if key != "artifact_root"})
    verify_reflection(packet, reflection)
    return reflection


def verify_reflection(packet: Mapping[str, Any], reflection: Mapping[str, Any]) -> dict[str, Any]:
    verify_packet(packet)
    reject_forbidden(reflection)
    exact_keys(reflection, reflection_fields(), "reflection")
    if reflection["schema_version"] != SCHEMA_VERSION or reflection["kind"] != "product-program-reflection":
        raise ProductProgramError("reflection identity differs")
    if reflection["packet_id"] != packet["packet_id"] or reflection["packet_root"] != packet["artifact_root"]:
        raise ProductProgramError("reflection is stale for its packet")
    authority = exact_keys(
        reflection["authority"],
        {"direct_effects_allowed", "posture", "selection_allowed"},
        "reflection authority",
    )
    if authority != {
        "direct_effects_allowed": False,
        "posture": "derived-nonauthorizing",
        "selection_allowed": False,
    }:
        raise ProductProgramError("reflection asserts selection or downstream authority")
    normalized = normalize_submission(
        packet,
        {
            "candidate_ceiling": reflection["candidate_ceiling"],
            "candidates": reflection["candidates"],
            "capability_gaps": reflection["capability_gaps"],
            "counterexample_widening_used": reflection["counterexample_widening_used"],
            "generation_pass_count": 1,
            "generator_id": reflection["generator_id"],
            "kind": "product-program-reflection-submission",
            "lessons": reflection["lessons"],
            "meta_patterns": reflection["meta_patterns"],
            "observations": reflection["observations"],
            "packet_id": reflection["packet_id"],
            "packet_root": reflection["packet_root"],
            "schema_version": reflection["schema_version"],
        },
    )
    for key, value in normalized.items():
        if reflection[key] != value:
            raise ProductProgramError("reflection semantic records are not normalized")
    expected_currentness = digest(
        {
            "kind": "product-program-reflection-currentness",
            "packet_currentness_root": packet["currentness_root"],
            "packet_root": packet["artifact_root"],
        }
    )
    if reflection["currentness_root"] != expected_currentness:
        raise ProductProgramError("reflection currentness is stale")
    expected_root = digest({key: reflection[key] for key in reflection if key != "artifact_root"})
    if reflection["artifact_root"] != expected_root:
        raise ProductProgramError("reflection artifact root is stale")
    return {"artifact_root": expected_root, "currentness_root": expected_currentness, "verified": True}


def reuse_reflection(packet: Mapping[str, Any], reflection: Mapping[str, Any]) -> dict[str, Any]:
    verified = verify_reflection(packet, reflection)
    return {
        "action": "reflection-reused",
        "artifact_root": verified["artifact_root"],
        "cognitive_work_started": False,
        "model_calls": 0,
        "reflection": reflection,
    }


def read_json(path: str, label: str) -> Mapping[str, Any]:
    return read_json_file(path, label)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--packet", required=True)
    build.add_argument("--submission", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--packet", required=True)
    verify.add_argument("--reflection", required=True)
    reuse = commands.add_parser("reuse")
    reuse.add_argument("--packet", required=True)
    reuse.add_argument("--reflection", required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        packet = read_json(args.packet, "packet")
        if args.command == "build":
            output = {
                "action": "reflection-prepared",
                "cognitive_work_started": True,
                "reflection": build_reflection(packet, read_json(args.submission, "reflection submission")),
            }
        else:
            reflection = read_json(args.reflection, "reflection")
            output = verify_reflection(packet, reflection) if args.command == "verify" else reuse_reflection(packet, reflection)
    except (OSError, ProductProgramError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
