#!/usr/bin/env python3
"""Behavioral contract for one selective bounded candidate lane."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from pathlib import Path, PurePosixPath


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL_ROOT / "references" / "bounded-candidate-lane.md").read_text(
    encoding="utf-8"
)
ADAPTIVE = (
    SKILL_ROOT / "references" / "adaptive-decision-control.md"
).read_text(encoding="utf-8")
SPEC = json.loads(
    ADAPTIVE.split("<!-- contract-spec-v1 -->", 1)[1]
    .split("```json", 1)[1]
    .split("```", 1)[0]
)
EXERCISE = json.loads(
    (SKILL_ROOT / "fixtures" / "bounded_candidate_v1.json").read_text(
        encoding="utf-8"
    )
)

EXPECTED_EXERCISE_ROOT = "b179022792ce28335c1d3b460321899f74534c2cee9b02462b7c8ffcbf239359"
DISPOSITIONS = {
    "candidate-better",
    "incumbent-better",
    "non-inferior-no-benefit",
    "inconclusive",
}
RETIREMENT_BY_DISPOSITION = {
    "candidate-better": "eligible-cutover",
    "incumbent-better": "retired-loser",
    "non-inferior-no-benefit": "retired-loser",
    "inconclusive": "retired-inconclusive",
}
DIMENSIONS = {
    "observable-outcome",
    "implementation-cost",
    "maintenance-cost",
    "reversibility",
    "compatibility",
    "protected-capability",
}
STAGES = ["selected", "implementing", "validated", "reviewed", "closed"]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def root(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def case_index() -> dict[str, dict[str, object]]:
    cases = EXERCISE["cases"]
    indexed = {str(case["case_id"]): case for case in cases}
    if len(indexed) != len(cases):
        raise ValueError("candidate case identity is duplicated")
    return indexed


def validate_exercise() -> None:
    if root(EXERCISE) != EXPECTED_EXERCISE_ROOT:
        raise ValueError("candidate exercise source root differs")
    if (
        EXERCISE["schema_version"] != 1
        or EXERCISE["kind"] != "software-factory-bounded-candidate-exercise"
        or EXERCISE["block_number"] != 6
    ):
        raise ValueError("candidate exercise identity differs")
    incumbent = EXERCISE["incumbent"]
    lane = EXERCISE["lane"]
    if lane["implementation_owner_id"] != incumbent["production_authority_owner_id"]:
        raise ValueError("candidate bypasses the normal target owner")
    if lane["independent_reviewer_id"] in {
        lane["implementation_owner_id"],
        lane["cutover_owner_id"],
    }:
        raise ValueError("candidate reviewer is not independent")
    if set(EXERCISE["comparison_dimensions"]) != DIMENSIONS:
        raise ValueError("candidate comparison dimensions differ")
    production = set(incumbent["writable_scope"])
    isolated = {scope["path"] for scope in lane["isolated_writable_scope"]}
    exclusions = {scope["path"] for scope in lane["shared_resource_exclusions"]}
    if production.intersection(isolated) or not production.issubset(exclusions):
        raise ValueError("candidate isolation overlaps production authority")
    lane_root = PurePosixPath(lane["root"])
    for path in isolated:
        try:
            PurePosixPath(path).relative_to(lane_root)
        except ValueError as error:
            raise ValueError("candidate writable scope escapes lane") from error


def canonical_case(case_id: str) -> dict[str, object]:
    validate_exercise()
    try:
        return copy.deepcopy(case_index()[case_id])
    except KeyError as error:
        raise ValueError("candidate case is absent") from error


def decision_value(case: dict[str, object]) -> dict[str, int]:
    value = case["decision_value"]
    benefit = value["outcome_uncertainty"] + value["rework_avoided"] + value["evidence_gain"]
    cost = value["duplicate_cost"] + value["review_cost"] + value["isolation_risk"]
    return {"named_benefit": benefit, "named_cost": cost, "net": benefit - cost}


def decision_fingerprint(case: dict[str, object]) -> str:
    value = case["decision_value"]
    return root(
        {
            "trigger": case["trigger"],
            "implementation_evidence_required": case["implementation_evidence_required"],
            "read_only_resolvable": case["read_only_resolvable"],
            "decision_value": value,
            "hypothesis": EXERCISE["hypothesis"],
            "hypothesis_scope": EXERCISE["hypothesis_scope"],
            "incumbent_root": EXERCISE["incumbent"]["content_root"],
            "capability": EXERCISE["capability"],
            "protected_capabilities": EXERCISE["protected_capabilities"],
            "isolation": EXERCISE["lane"],
        }
    )


def ceiling_exceeded(case: dict[str, object]) -> bool:
    usage = case["usage"]
    ceiling = EXERCISE["lane"]["resource_ceiling"]
    return (
        usage["files"] > ceiling["max_files"]
        or usage["changed_lines"] > ceiling["max_changed_lines"]
        or usage["commands"] > ceiling["max_commands"]
        or usage["review_passes"] > ceiling["max_review_passes"]
        or usage["elapsed_minutes"] > EXERCISE["lane"]["time_ceiling_minutes"]
    )


def comparison_records(case: dict[str, object], candidate_root: str) -> list[dict[str, object]]:
    comparison = case["comparison"]
    if set(comparison) != {
        "observable_outcome",
        "implementation_cost",
        "maintenance_cost",
        "reversibility",
        "compatibility",
        "protected_capability",
    }:
        raise ValueError("raw comparison is incomplete")
    result: list[dict[str, object]] = []
    for dimension in EXERCISE["comparison_dimensions"]:
        key = dimension.replace("-", "_")
        result.append(
            {
                "dimension": dimension,
                "incumbent_evidence_root": root(
                    {"dimension": dimension, "path": "incumbent", "root": EXERCISE["incumbent"]["content_root"]}
                ),
                "candidate_evidence_root": root(
                    {"dimension": dimension, "path": "candidate", "root": candidate_root}
                ),
                "relation": comparison[key],
            }
        )
    return result


def validate_scope_refs(scopes: object, *, contained_by: str) -> None:
    if not isinstance(scopes, list):
        raise ValueError("candidate scope references differ")
    container = PurePosixPath(contained_by)
    for scope in scopes:
        if not isinstance(scope, dict) or set(scope) != {"owner_id", "path", "content_root"}:
            raise ValueError("candidate scope reference differs")
        if not ID_RE.fullmatch(str(scope["owner_id"])):
            raise ValueError("candidate scope owner differs")
        if not SHA256_RE.fullmatch(str(scope["content_root"])):
            raise ValueError("candidate scope root differs")
        path = PurePosixPath(str(scope["path"]))
        if not path.is_absolute():
            raise ValueError("candidate scope path is not absolute")
        try:
            path.relative_to(container)
        except ValueError as error:
            raise ValueError("candidate scope path is not contained") from error


def validate_candidate_fields(values: dict[str, object]) -> None:
    if set(values) != set(SPEC["candidate_fields"]):
        raise ValueError("candidate field set differs from Block 4")
    for key in ("incumbent_root", "candidate_root", "review_root"):
        if not SHA256_RE.fullmatch(str(values[key])):
            raise ValueError(f"candidate {key} differs")
    for key in ("hypothesis", "resource_ceiling", "time_ceiling", "stop_condition"):
        if not isinstance(values[key], str) or not values[key]:
            raise ValueError(f"candidate {key} differs")
    for key in (
        "production_authority_owner_id",
        "independent_reviewer_id",
        "cutover_owner_id",
    ):
        if not ID_RE.fullmatch(str(values[key])):
            raise ValueError(f"candidate {key} differs")
    for key in ("focused_validation", "mapped_validation", "cutover_preconditions"):
        refs = values[key]
        if (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or not all(ID_RE.fullmatch(str(ref)) for ref in refs)
        ):
            raise ValueError(f"candidate {key} differs")
    if values["validation_order"] != "focused-then-mapped":
        raise ValueError("candidate validation order differs")
    if values["comparison_dimensions"] != EXERCISE["comparison_dimensions"]:
        raise ValueError("candidate comparison dimensions differ")
    if values["review_disposition"] != "accepted":
        raise ValueError("candidate review disposition differs")
    if values["retirement_posture"] not in set(RETIREMENT_BY_DISPOSITION.values()):
        raise ValueError("candidate retirement posture differs")
    validate_scope_refs(
        values["hypothesis_scope"],
        contained_by=EXERCISE["target_repository_root"],
    )
    validate_scope_refs(values["isolated_writable_scope"], contained_by=EXERCISE["lane"]["root"])
    validate_scope_refs(
        values["shared_resource_exclusions"],
        contained_by=EXERCISE["target_repository_root"],
    )


def candidate_fields(
    case: dict[str, object], candidate_root: str, comparison: list[dict[str, object]]
) -> dict[str, object]:
    lane = EXERCISE["lane"]
    disposition = case["comparison_disposition"]
    raw_comparison_root = root(comparison)
    review_root = root(
        {
            "candidate_root": candidate_root,
            "incumbent_root": EXERCISE["incumbent"]["content_root"],
            "raw_comparison_root": raw_comparison_root,
            "reviewer_id": case["reviewer_id"],
            "comparison_disposition": disposition,
        }
    )
    isolated_scope = copy.deepcopy(lane["isolated_writable_scope"])
    for scope in isolated_scope:
        scope["content_root"] = candidate_root
    values = {
        "hypothesis": EXERCISE["hypothesis"],
        "hypothesis_scope": EXERCISE["hypothesis_scope"],
        "incumbent_root": EXERCISE["incumbent"]["content_root"],
        "candidate_root": candidate_root,
        "isolation_kind": lane["isolation_kind"],
        "isolated_writable_scope": isolated_scope,
        "shared_resource_exclusions": lane["shared_resource_exclusions"],
        "resource_ceiling": "files<=3;changed-lines<=120;commands<=6;review-passes<=1",
        "time_ceiling": "elapsed-minutes<=20",
        "stop_condition": lane["stop_condition"],
        "production_authority_owner_id": EXERCISE["incumbent"]["production_authority_owner_id"],
        "focused_validation": [f"validation-focused-{candidate_root[:16]}"],
        "mapped_validation": [f"validation-mapped-{raw_comparison_root[:16]}"],
        "validation_order": "focused-then-mapped",
        "comparison_dimensions": EXERCISE["comparison_dimensions"],
        "independent_reviewer_id": case["reviewer_id"],
        "review_root": review_root,
        "review_disposition": "accepted",
        "cutover_owner_id": lane["cutover_owner_id"],
        "cutover_preconditions": [
            "block-9",
            f"review-{review_root}",
            f"candidate-{candidate_root}",
        ],
        "retirement_posture": RETIREMENT_BY_DISPOSITION[str(disposition)],
    }
    validate_candidate_fields(values)
    return values


def stage_chain(
    fingerprint: str, fields: dict[str, object], review_disposition: str
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    previous: str | None = None
    for stage in STAGES:
        record = {
            "stage": stage,
            "decision_fingerprint": fingerprint,
            "candidate_root": fields["candidate_root"] if stage != "selected" else None,
            "review_root": fields["review_root"] if stage in {"reviewed", "closed"} else None,
            "review_disposition": review_disposition if stage in {"reviewed", "closed"} else None,
            "production_authority_owner_id": fields["production_authority_owner_id"],
            "retirement_posture": fields["retirement_posture"] if stage == "closed" else "active-isolated",
            "previous_record_root": previous,
        }
        record["currentness_root"] = root(record)
        previous = root(record)
        records.append(record)
    return records


def _evaluate(case: dict[str, object], expected_exercise_root: str) -> dict[str, object]:
    if root(EXERCISE) != expected_exercise_root:
        raise ValueError("candidate exercise source root differs")
    validate_exercise()
    case_id = str(case.get("case_id", ""))
    if canonical(case) != canonical(case_index().get(case_id)):
        raise ValueError("candidate case differs from repository source")
    fingerprint = decision_fingerprint(case)
    duplicate = case.get("duplicate_of_case_id")
    if duplicate is not None:
        source = case_index()[str(duplicate)]
        if fingerprint != decision_fingerprint(source):
            raise ValueError("duplicate trigger fingerprint differs")
        return {"action": "deduplicate", "lane_created": False, "review_cycle": False, "fingerprint": fingerprint}

    value = decision_value(case)
    if (
        case["trigger"] != "material-better-path"
        or not case["implementation_evidence_required"]
        or case["read_only_resolvable"]
        or value["net"] <= 0
        or not case["isolation_safe"]
    ):
        return {"action": "reject-before-lane", "lane_created": False, "review_cycle": False, "fingerprint": fingerprint, "decision_value": value}
    if ceiling_exceeded(case):
        return {"action": "stop-retire", "lane_created": True, "review_cycle": False, "retirement_posture": "retired-loser", "fingerprint": fingerprint}
    if case["incumbent_progress_conflict"]:
        return {"action": "stop-stale-basis", "lane_created": True, "review_cycle": False, "retirement_posture": "retired-inconclusive", "fingerprint": fingerprint}
    if case["focused_status"] != "passed" or case["protected_result"] != "preserved":
        return {"action": "stop-retire", "lane_created": True, "review_cycle": False, "retirement_posture": "retired-loser", "fingerprint": fingerprint}
    if case["mapped_status"] != "passed":
        raise ValueError("mapped comparison ran before coherent focused proof")
    if (
        not case["review_blinded"]
        or case["reviewer_id"] != EXERCISE["lane"]["independent_reviewer_id"]
        or case["reviewer_id"] in {
            EXERCISE["lane"]["implementation_owner_id"],
            EXERCISE["lane"]["cutover_owner_id"],
        }
        or case["comparison_disposition"] not in DISPOSITIONS
    ):
        raise ValueError("candidate independent review differs")
    candidate_root = root(
        {"case_id": case["case_id"], "hypothesis": EXERCISE["hypothesis"], "usage": case["usage"]}
    )
    comparison = comparison_records(case, candidate_root)
    fields = candidate_fields(case, candidate_root, comparison)
    comparison_disposition = str(case["comparison_disposition"])
    action = "handoff-block-9" if comparison_disposition == "candidate-better" else "retire-candidate"
    records = stage_chain(fingerprint, fields, comparison_disposition)
    return {
        "action": action,
        "lane_created": True,
        "review_cycle": True,
        "fingerprint": fingerprint,
        "decision_value": value,
        "candidate_fields": fields,
        "raw_comparison_records": comparison,
        "comparison_disposition": comparison_disposition,
        "stage_records": records,
        "candidate_authoritative": False,
        "incumbent_authoritative": True,
        "cutover_performed": False,
        "tracker_mutated": False,
    }


def evaluate(case_id: str) -> dict[str, object]:
    case = canonical_case(case_id)
    return _evaluate(case, EXPECTED_EXERCISE_ROOT)


class BoundedCandidateContractTests(unittest.TestCase):
    def test_all_cases_route_exactly_and_never_create_two_authorities(self) -> None:
        for case in EXERCISE["cases"]:
            result = evaluate(case["case_id"])
            self.assertEqual(result["action"], case["expected_action"])
            if result.get("lane_created") and result.get("review_cycle"):
                self.assertTrue(result["incumbent_authoritative"])
                self.assertFalse(result["candidate_authoritative"])
                self.assertFalse(result["cutover_performed"])
                self.assertFalse(result["tracker_mutated"])
                self.assertEqual(
                    result["candidate_fields"]["retirement_posture"],
                    case["expected_retirement_posture"],
                )

    def test_winner_has_exact_candidate_fields_review_and_block9_handoff(self) -> None:
        result = evaluate("winning-candidate")
        fields = result["candidate_fields"]
        self.assertEqual(set(fields), set(SPEC["candidate_fields"]))
        self.assertEqual(fields["validation_order"], "focused-then-mapped")
        self.assertEqual(
            fields["independent_reviewer_id"], "reviewer-candidate-independent"
        )
        self.assertEqual(result["action"], "handoff-block-9")
        self.assertEqual(fields["retirement_posture"], "eligible-cutover")
        self.assertEqual(
            [record["stage"] for record in result["stage_records"]], STAGES
        )
        self.assertEqual(
            len({record["decision_fingerprint"] for record in result["stage_records"]}),
            1,
        )
        self.assertEqual(len({record["currentness_root"] for record in result["stage_records"]}), 5)
        self.assertEqual(result["comparison_disposition"], "candidate-better")
        self.assertEqual(len(result["raw_comparison_records"]), 6)
        self.assertEqual(fields["review_disposition"], "accepted")

    def test_losing_inconclusive_and_novel_candidates_retire(self) -> None:
        for case_id, posture in (
            ("losing-candidate", "retired-loser"),
            ("non-inferior-no-benefit", "retired-loser"),
            ("novelty-bias", "retired-loser"),
            ("inconclusive-comparison", "retired-inconclusive"),
        ):
            result = evaluate(case_id)
            self.assertEqual(result["action"], "retire-candidate")
            self.assertEqual(result["candidate_fields"]["retirement_posture"], posture)

    def test_eligibility_isolation_ceiling_failure_and_conflict_stop_early(self) -> None:
        for case_id in (
            "read-only-decidable",
            "unsafe-isolation",
            "ceiling-expired",
            "incumbent-conflict",
            "focused-failure",
            "protected-regression",
        ):
            result = evaluate(case_id)
            self.assertFalse(result["review_cycle"], case_id)
            self.assertNotIn("candidate_fields", result, case_id)

    def test_duplicate_trigger_has_no_lane_or_review_cycle(self) -> None:
        duplicate = evaluate("duplicate-trigger")
        original = evaluate("winning-candidate")
        self.assertEqual(duplicate["fingerprint"], original["fingerprint"])
        self.assertEqual(duplicate["action"], "deduplicate")
        self.assertFalse(duplicate["lane_created"])
        self.assertFalse(duplicate["review_cycle"])

    def test_fixture_or_authority_mutation_fails_closed(self) -> None:
        case = canonical_case("winning-candidate")
        mutated = copy.deepcopy(case)
        mutated["reviewer_id"] = EXERCISE["lane"]["implementation_owner_id"]
        with self.assertRaisesRegex(ValueError, "differs from repository source"):
            _evaluate(mutated, EXPECTED_EXERCISE_ROOT)

        saved = copy.deepcopy(EXERCISE)
        try:
            EXERCISE["lane"]["isolated_writable_scope"] = EXERCISE["incumbent"]["writable_scope"]
            with self.assertRaisesRegex(ValueError, "source root"):
                evaluate("winning-candidate")
        finally:
            EXERCISE.clear()
            EXERCISE.update(saved)

    def test_method_is_selective_bounded_and_stops_before_cutover(self) -> None:
        normalized_skill = " ".join(SKILL.split())
        for phrase in (
            "Use `compare-candidate` only after the inline loop proves",
            "Open exactly one branch, worktree, temporary repository, or equivalent lane",
            "The lane has no publish, production, cutover",
            "without a novelty bonus or opaque aggregate score",
            "do not cut over here",
            "Never retain two live implementations or force adoption",
        ):
            self.assertIn(phrase, normalized_skill)
        normalized_reference = " ".join(REFERENCE.split())
        for phrase in (
            "Failure of any condition returns to the incumbent without creating a lane",
            "`focused_validation` must pass before `mapped_validation`",
            "The incumbent is the only production authority",
            "The Block Stop is before cutover, tracker amendment, policy change",
        ):
            self.assertIn(phrase, normalized_reference)


if __name__ == "__main__":
    unittest.main()
