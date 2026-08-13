#!/usr/bin/env python3
"""Static and mechanical checks for the Block 0 evolution contract."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "evolve-product-program"
CONTRACT = (SKILL_ROOT / "references" / "product-program-evolution-contract.md").read_text(encoding="utf-8")
CONTRACT_FIXTURE = json.loads((SKILL_ROOT / "fixtures" / "product_program_contract_v1.json").read_text(encoding="utf-8"))
SOURCE_MAP = json.loads((SKILL_ROOT / "fixtures" / "product_program_source_map_v1.json").read_text(encoding="utf-8"))

EXPECTED_ARTIFACTS = {
    "product-program-evidence-packet",
    "product-program-placement-handoff",
    "product-program-portfolio",
    "product-program-reflection",
    "product-program-resource-evidence",
    "product-program-selection",
}
EXPECTED_ROLES = {
    "consequential-adjudicator",
    "evaluator",
    "evidence-assembler",
    "implementation-owner",
    "portfolio-selector",
    "reflection-generator",
    "release-external-effect-owner",
    "resource-evidence-builder",
    "supervision-owner",
    "tracker-author",
}
EXPECTED_ARTIFACT_SCHEMA_FIELDS = {
    "product-program-evidence-packet": set(
        "artifact_root authority currentness_root decisions incidents kind "
        "material_change_fingerprint mission outcome packet_id product_sources "
        "profile protected_capabilities range reports repository resource_sources "
        "schema_version supervision tracker transformation_version".split()
    ),
    "product-program-placement-handoff": set(
        "authority currentness_root disposition expected_effect handoff_root kind "
        "nonauthorization owner placement portfolio_root preconditions "
        "schema_version stop".split()
    ),
    "product-program-portfolio": set(
        "aggregate_budget authority currentness_root dependency_edges disposition "
        "early_stop_rules kind lanes placement portfolio_root scheduling_groups "
        "schema_version selection_root unused_capacity".split()
    ),
    "product-program-reflection": set(
        "artifact_root authority candidate_ceiling candidates capability_gaps "
        "counterexample_widening_used currentness_root generator_id kind lessons "
        "meta_patterns observations packet_id packet_root schema_version".split()
    ),
    "product-program-resource-evidence": set(
        "artifact_root authority currentness_root estimation_profile kind "
        "limitations packet_id packet_root schema_version transformation_version "
        "work_classes".split()
    ),
    "product-program-selection": set(
        "adjudicator_id authority currentness_root dimensions disposition kind "
        "packet_root rationale reflection_root rejected_candidates "
        "resource_evidence_root schema_version selection_root selector_id".split()
    ),
}
EXPECTED_CHECKPOINT_INPUT_SCHEMA = set(
    "current_outcome mission prior_checkpoint_identity product_sources profile "
    "protected_capabilities range reports repository resource_sources "
    "schema_version supervision tracker".split()
)
EXPECTED_INTERFACES = {
    "author-implementation-trackers": {
        "apply_effect": False,
        "consumer": "tracker-author",
        "input_kind": "product-program-placement-handoff",
        "output_kind": "author-owned-program-revision-or-tracker",
        "revalidates": ["authority", "currentness_root", "mission", "range", "source_roots"],
    },
    "implement-tracker-blocks": {
        "apply_effect": False,
        "consumer": "implementation-owner",
        "input_kind": "product-program-placement-handoff",
        "output_kind": "implementation-owner-decision",
        "revalidates": ["authority", "currentness_root", "mission", "range", "stop"],
    },
    "release-and-external-effect-owners": {
        "apply_effect": False,
        "consumer": "release-external-effect-owner",
        "input_kind": "none",
        "output_kind": "none",
        "revalidates": [],
    },
    "supervise-tracker-runs": {
        "apply_effect": False,
        "consumer": "supervision-owner",
        "input_kind": "product-program-checkpoint-request",
        "output_kind": "canonical-source-identities-only",
        "revalidates": ["mission", "policy_head", "event_head", "target_identity"],
    },
}


def validate_contract(value: dict[str, object]) -> None:
    if value.get("schema_version") != 1 or value.get("kind") != "product-program-evolution-contract":
        raise ValueError("contract identity differs")
    artifacts = value.get("artifact_classes")
    if not isinstance(artifacts, list) or set(artifacts) != EXPECTED_ARTIFACTS or len(artifacts) != len(EXPECTED_ARTIFACTS):
        raise ValueError("artifact classes differ")
    owners = value.get("artifact_owners")
    if not isinstance(owners, dict) or set(owners) != EXPECTED_ARTIFACTS:
        raise ValueError("every artifact must have exactly one owner")
    roles = value.get("roles")
    if not isinstance(roles, list) or set(roles) != EXPECTED_ROLES or len(roles) != len(EXPECTED_ROLES):
        raise ValueError("roles differ")
    if not set(owners.values()) <= EXPECTED_ROLES:
        raise ValueError("artifact owner is not a declared role")
    schemas = value.get("artifact_schemas")
    if not isinstance(schemas, dict) or set(schemas) != EXPECTED_ARTIFACTS:
        raise ValueError("artifact schemas differ")
    for kind, fields in schemas.items():
        if (
            not isinstance(fields, list)
            or fields != sorted(set(fields))
            or set(fields) != EXPECTED_ARTIFACT_SCHEMA_FIELDS[kind]
        ):
            raise ValueError(f"{kind} fields are not exact and sorted")
        if {"schema_version", "kind", "authority", "currentness_root"} - set(fields):
            raise ValueError(f"{kind} omits common identity fields")
        if not any(field.endswith("_root") for field in fields if field != "currentness_root"):
            raise ValueError(f"{kind} omits its artifact root")
    checkpoint = value.get("checkpoint_input_schema")
    if (
        not isinstance(checkpoint, list)
        or checkpoint != sorted(set(checkpoint))
        or set(checkpoint) != EXPECTED_CHECKPOINT_INPUT_SCHEMA
    ):
        raise ValueError("checkpoint input schema differs")
    transitions = value.get("state_transitions")
    if not isinstance(transitions, list) or not transitions:
        raise ValueError("transitions missing")
    for transition in transitions:
        if not isinstance(transition, dict) or set(transition) != {"from", "stop", "to"} or not transition["stop"]:
            raise ValueError("every transition needs one exact Stop")
    interfaces = value.get("interfaces")
    if not isinstance(interfaces, dict) or interfaces != EXPECTED_INTERFACES:
        raise ValueError("sibling interfaces differ")


class ProductProgramContractTests(unittest.TestCase):
    def test_fixture_is_exact_and_self_consistent(self) -> None:
        validate_contract(CONTRACT_FIXTURE)

    def test_shared_ladder_has_profile_specific_adoption(self) -> None:
        self.assertIn("software-factory-capability", CONTRACT_FIXTURE["target_profiles"])
        self.assertIn("target-product-program", CONTRACT_FIXTURE["target_profiles"])
        self.assertNotEqual(*CONTRACT_FIXTURE["target_profiles"].values())
        self.assertIn("without sharing adoption authority", CONTRACT)

    def test_every_transition_has_a_stop(self) -> None:
        transitions = CONTRACT_FIXTURE["state_transitions"]
        self.assertEqual(6, len(transitions))
        for transition in transitions:
            self.assertEqual({"from", "stop", "to"}, set(transition))
            self.assertTrue(transition["stop"])

    def test_dispositions_have_one_fixed_placement(self) -> None:
        expected = {
            "continue-program-unchanged",
            "remediate-current-block",
            "revise-current-program",
            "start-successor-program",
            "start-program-portfolio",
            "run-bounded-experiment",
            "safe-defer-open-fact-or-authority",
            "request-material-goal-authority",
        }
        self.assertEqual(expected, set(CONTRACT_FIXTURE["disposition_placements"]))
        self.assertEqual(
            len(expected), len(set(CONTRACT_FIXTURE["disposition_placements"].values()))
        )

    def test_all_derived_artifacts_are_nonauthorizing(self) -> None:
        for forbidden in ("tracker", "source", "supervision", "release", "automation", "external-effect"):
            self.assertIn(forbidden, CONTRACT_FIXTURE["non_authorizing_writes"])
            self.assertIn(forbidden.replace("-", " "), CONTRACT.lower())
        self.assertIn("It is never an authorization", CONTRACT)

    def test_role_separation_and_noop_are_explicit(self) -> None:
        roles = set(CONTRACT_FIXTURE["roles"])
        self.assertEqual(EXPECTED_ROLES, roles)
        self.assertEqual(EXPECTED_ARTIFACTS, set(CONTRACT_FIXTURE["artifact_owners"]))
        self.assertIn("prior and\ncurrent `material_change_fingerprint`", CONTRACT)
        self.assertIn("prior and current `currentness_root`", CONTRACT)
        self.assertIn("never compared with each other", CONTRACT)
        self.assertIn("Generator, selector, implementer, and evaluator identities are distinct", CONTRACT)

    def test_invalid_owner_schema_and_effect_interfaces_are_rejected(self) -> None:
        missing_owner = deepcopy(CONTRACT_FIXTURE)
        del missing_owner["artifact_owners"]["product-program-resource-evidence"]
        with self.assertRaisesRegex(ValueError, "every artifact"):
            validate_contract(missing_owner)

        extra_key = deepcopy(CONTRACT_FIXTURE)
        extra_key["artifact_schemas"]["product-program-selection"].append("winner_score")
        with self.assertRaisesRegex(ValueError, "exact and sorted"):
            validate_contract(extra_key)

        effect = deepcopy(CONTRACT_FIXTURE)
        effect["interfaces"]["author-implementation-trackers"]["apply_effect"] = True
        with self.assertRaisesRegex(ValueError, "sibling interfaces"):
            validate_contract(effect)

        changed_consumer = deepcopy(CONTRACT_FIXTURE)
        changed_consumer["interfaces"]["implement-tracker-blocks"]["consumer"] = "portfolio-selector"
        with self.assertRaisesRegex(ValueError, "sibling interfaces"):
            validate_contract(changed_consumer)

        missing_checkpoint_field = deepcopy(CONTRACT_FIXTURE)
        missing_checkpoint_field["checkpoint_input_schema"].remove("range")
        with self.assertRaisesRegex(ValueError, "checkpoint input"):
            validate_contract(missing_checkpoint_field)

    def test_invalid_roles_and_stops_are_rejected(self) -> None:
        missing_role = deepcopy(CONTRACT_FIXTURE)
        missing_role["roles"].remove("release-external-effect-owner")
        with self.assertRaisesRegex(ValueError, "roles differ"):
            validate_contract(missing_role)

        missing_stop = deepcopy(CONTRACT_FIXTURE)
        missing_stop["state_transitions"][0]["stop"] = ""
        with self.assertRaisesRegex(ValueError, "exact Stop"):
            validate_contract(missing_stop)

    def test_source_map_is_exact_and_current(self) -> None:
        for source in SOURCE_MAP["sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            self.assertFalse(path.is_symlink(), source["path"])
            revision = source.get("revision")
            if revision is None:
                raw = path.read_bytes()
            else:
                self.assertRegex(revision, r"^[0-9a-f]{40}$")
                raw = subprocess.run(
                    ["git", "show", f"{revision}:{source['path']}"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
            self.assertEqual(hashlib.sha256(raw).hexdigest(), source["sha256"])

    def test_contract_rejects_duplicate_owner_surfaces(self) -> None:
        for phrase in (
            "does not create a tracker writer",
            "supervision ledger",
            "release owner",
            "scheduler",
            "or permission\nsystem",
            "Parallel plans remain\nderived",
        ):
            self.assertIn(phrase, CONTRACT)


if __name__ == "__main__":
    unittest.main()
