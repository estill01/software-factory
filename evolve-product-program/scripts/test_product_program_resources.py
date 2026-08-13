#!/usr/bin/env python3
"""Focused tests for Block 3 resource/outcome evidence."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).with_name("product_program_resources.py")
FIXTURES = SCRIPT.parents[1] / "fixtures"
SPEC = importlib.util.spec_from_file_location("product_program_resources", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

EVOLUTION_SPEC = importlib.util.spec_from_file_location(
    "product_program_evolution_for_resources", SCRIPT.with_name("product_program_evolution.py")
)
assert EVOLUTION_SPEC and EVOLUTION_SPEC.loader
EVOLUTION = importlib.util.module_from_spec(EVOLUTION_SPEC)
sys.modules[EVOLUTION_SPEC.name] = EVOLUTION
EVOLUTION_SPEC.loader.exec_module(EVOLUTION)


class ProductProgramResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(
            (FIXTURES / "program_evidence_completed_v1.json").read_text(encoding="utf-8")
        )
        self.source = self.source_manifest()
        self.rebind()

    def outcome(self, dimension: str, evidence_id: str = "outcome-1") -> dict[str, object]:
        values = {
            "completion": "completed",
            "product_effect": "beneficial",
            "protected_capability_result": "preserved",
            "recurrence_reach": "recurrent",
            "compounding_value": "reusable",
            "reuse": "partial",
            "reversibility": "reversible",
            "opportunity_cost": "medium",
        }
        if dimension == "protected_capability_result":
            evidence_id = "cold-start"
        return {
            "evidence_class": "observed",
            "evidence_ids": [evidence_id],
            "uncertainty": "bounded by retained outcome evidence",
            "value": values[dimension],
        }

    def resource(
        self,
        dimension: str,
        evidence_id: str,
        *,
        evidence_class: str = "observed",
        lower: int = 2,
        upper: int | None = None,
    ) -> dict[str, object]:
        if upper is None:
            upper = lower
        return {
            "evidence_class": evidence_class,
            "evidence_ids": [evidence_id],
            "lower": lower,
            "uncertainty": "bounded by retained source and evidence class",
            "unit": MODULE.RESOURCE_UNITS[dimension],
            "upper": upper,
        }

    def work_class(self, work_class_id: str, resource_id: str) -> dict[str, object]:
        resources = {
            dimension: self.resource(dimension, resource_id)
            for dimension in MODULE.RESOURCE_DIMENSIONS
        }
        if work_class_id == "feature-delivery":
            resources["tokens"] = self.resource(
                "tokens", "resource-a-provider", evidence_class="provider-reported", lower=120
            )
        else:
            resources["tokens"] = self.resource(
                "tokens", "resource-b-estimate", evidence_class="estimated", lower=80, upper=140
            )
            resources["elapsed_time"] = self.resource(
                "elapsed_time", "resource-b-estimate", evidence_class="estimated", lower=30, upper=60
            )
        return {
            "outcomes": {
                dimension: self.outcome(dimension) for dimension in MODULE.OUTCOME_DIMENSIONS
            },
            "resources": resources,
            "useful_yield": {
                "comparison_posture": "dimension-by-dimension-only",
                "outcome_dimensions": list(MODULE.OUTCOME_DIMENSIONS),
                "resource_dimensions": list(MODULE.RESOURCE_DIMENSIONS),
                "uncertainties": [
                    "association does not prove causation",
                    "rare high-value work remains visible",
                ],
            },
            "work_class_id": work_class_id,
        }

    def source_manifest(self) -> dict[str, object]:
        return {
            "estimation_profile": {
                "evidence_ids": ["resource-b-estimate"],
                "method": "bounded token and elapsed-time ranges from retained event counts",
                "profile_id": "bounded-resource-estimation",
                "version": 1,
            },
            "kind": "product-program-resource-source",
            "limitations": list(MODULE.LIMITATIONS),
            "resource_source_id": "resource-manifest",
            "schema_version": 1,
            "transformation_version": MODULE.TRANSFORMATION_VERSION,
            "work_classes": [
                self.work_class("feature-delivery", "resource-a"),
                self.work_class("reliability-remediation", "resource-b"),
            ],
        }

    def retained(self, source_id: str, evidence_class: str, raw: bytes) -> dict[str, object]:
        return {
            "byte_length": len(raw),
            "evidence_class": evidence_class,
            "path_sha256": hashlib.sha256(f"/{source_id}".encode()).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_id": source_id,
        }

    def reroot_packet(self) -> None:
        self.packet["material_change_fingerprint"] = EVOLUTION.digest(
            {
                "kind": "product-program-material-change",
                "value": EVOLUTION._semantic_material_from_packet(self.packet),
            }
        )
        self.packet["packet_id"] = (
            f"program-packet-{self.packet['material_change_fingerprint'][:20]}"
        )
        self.packet["currentness_root"] = EVOLUTION.digest(
            {
                "kind": "product-program-currentness",
                "material_change_fingerprint": self.packet["material_change_fingerprint"],
                "range_head": self.packet["range"]["range_head"],
                "repository": self.packet["repository"],
                "source_currentness": {
                    "product_sources": self.packet["product_sources"],
                    "reports": self.packet["reports"],
                    "resource_sources": self.packet["resource_sources"],
                },
                "supervision": self.packet["supervision"],
                "tracker_sha256": self.packet["tracker"]["sha256"],
            }
        )
        self.packet["artifact_root"] = EVOLUTION.digest(
            {key: self.packet[key] for key in self.packet if key != "artifact_root"}
        )

    def rebind(self) -> None:
        raw = MODULE.canonical(self.source)
        self.packet["resource_sources"] = [
            self.retained("resource-a", "observed", b'{"class":"feature-delivery"}\n'),
            self.retained("resource-a-provider", "provider-reported", b'{"tokens":120}\n'),
            self.retained("resource-b", "observed", b'{"class":"reliability-remediation"}\n'),
            self.retained("resource-b-estimate", "estimated", b'{"elapsed":[30,60],"tokens":[80,140]}\n'),
            self.retained("resource-manifest", "estimated", raw),
        ]
        self.reroot_packet()

    def assert_rejected(self, source: dict[str, object], pattern: str) -> None:
        self.source = source
        self.rebind()
        with self.assertRaisesRegex(MODULE.ProductProgramError, pattern):
            MODULE.build_resource_evidence(self.packet, self.source)

    def test_deterministic_projection_preserves_separate_dimensions_and_authority(self) -> None:
        first = MODULE.build_resource_evidence(self.packet, self.source)
        second = MODULE.build_resource_evidence(self.packet, self.source)
        self.assertEqual(MODULE.canonical(first), MODULE.canonical(second))
        self.assertTrue(MODULE.verify_resource_evidence(self.packet, self.source, first)["verified"])
        self.assertEqual(list(MODULE.OUTCOME_DIMENSIONS), first["work_classes"][0]["useful_yield"]["outcome_dimensions"])
        self.assertEqual(list(MODULE.RESOURCE_DIMENSIONS), first["work_classes"][0]["useful_yield"]["resource_dimensions"])
        self.assertFalse(first["authority"]["allocation_allowed"])
        self.assertFalse(first["authority"]["billing_claim"])
        self.assertNotIn("score", first)
        self.assertTrue(all("score" not in row for row in first["work_classes"]))

    def test_exact_reuse_is_zero_work(self) -> None:
        artifact = MODULE.build_resource_evidence(self.packet, self.source)
        result = MODULE.reuse_resource_evidence(self.packet, self.source, artifact)
        self.assertEqual("resource-evidence-reused", result["action"])
        self.assertEqual(0, result["model_calls"])
        self.assertFalse(result["cognitive_work_started"])

    def test_changed_row_reuses_only_unchanged_prior_row(self) -> None:
        prior = MODULE.build_resource_evidence(self.packet, self.source)
        prior_feature = MODULE.canonical(prior["work_classes"][0])
        changed = deepcopy(self.source)
        changed["work_classes"][1]["resources"]["tokens"]["upper"] = 160
        self.source = changed
        self.rebind()
        successor = MODULE.build_resource_evidence(self.packet, self.source, prior)
        self.assertEqual(prior_feature, MODULE.canonical(successor["work_classes"][0]))
        self.assertNotEqual(
            prior["work_classes"][1]["row_root"], successor["work_classes"][1]["row_root"]
        )

    def test_projected_tokens_cannot_be_labeled_actual(self) -> None:
        invalid = deepcopy(self.source)
        invalid["work_classes"][1]["resources"]["tokens"]["evidence_class"] = "actual"
        self.assert_rejected(invalid, "unsupported evidence class")

    def test_estimation_profile_is_required_and_versioned(self) -> None:
        valid = self.source_manifest()
        missing = deepcopy(valid)
        del missing["estimation_profile"]
        self.assert_rejected(missing, "keys differ")
        invalid = deepcopy(valid)
        invalid["estimation_profile"]["version"] = 0
        self.assert_rejected(invalid, "positive integer")

    def test_estimate_cannot_fabricate_product_effect(self) -> None:
        invalid = deepcopy(self.source)
        invalid["work_classes"][0]["outcomes"]["product_effect"]["evidence_class"] = "estimated"
        self.assert_rejected(invalid, "cannot be fabricated")

    def test_outcome_cannot_rely_only_on_resource_or_report_hypotheses(self) -> None:
        invalid = deepcopy(self.source)
        invalid["work_classes"][0]["outcomes"]["product_effect"]["evidence_ids"] = ["resource-a"]
        self.assert_rejected(invalid, "relies only on report or resource hypotheses")

    def test_duplicate_resource_attribution_rejects(self) -> None:
        invalid = deepcopy(self.source)
        invalid["work_classes"][1]["resources"]["commands"]["evidence_ids"] = ["resource-a"]
        self.assert_rejected(invalid, "attributed to multiple work classes")

    def test_dimension_class_must_match_retained_source_and_profile(self) -> None:
        mismatched = deepcopy(self.source)
        mismatched["work_classes"][0]["resources"]["tokens"]["evidence_ids"] = ["resource-a"]
        self.assert_rejected(mismatched, "evidence class differs from its retained source")
        uncovered = self.source_manifest()
        uncovered["estimation_profile"]["evidence_ids"] = ["resource-b"]
        self.assert_rejected(uncovered, "not covered by the retained estimation profile")

    def test_speed_only_or_aggregate_comparison_rejects(self) -> None:
        speed_only = deepcopy(self.source)
        speed_only["work_classes"][0]["useful_yield"]["outcome_dimensions"] = []
        self.assert_rejected(speed_only, "omits or reorders an outcome dimension")
        aggregate = deepcopy(self.source)
        aggregate["work_classes"][0]["score"] = 0.9
        self.assert_rejected(aggregate, "aggregate, billing, spend, or ranking")

    def test_unavailable_evidence_cannot_carry_a_value(self) -> None:
        invalid = deepcopy(self.source)
        invalid["work_classes"][0]["resources"]["incidents"]["evidence_class"] = "unavailable"
        self.assert_rejected(invalid, "unavailable evidence has a numeric value")

    def test_stale_packet_or_manifest_binding_rejects(self) -> None:
        artifact = MODULE.build_resource_evidence(self.packet, self.source)
        stale_packet = deepcopy(self.packet)
        stale_packet["currentness_root"] = "0" * 64
        with self.assertRaises(MODULE.ProductProgramError):
            MODULE.verify_resource_evidence(stale_packet, self.source, artifact)
        stale_source = deepcopy(self.source)
        stale_source["work_classes"][0]["resources"]["commands"]["lower"] = 3
        with self.assertRaisesRegex(MODULE.ProductProgramError, "bytes differ"):
            MODULE.verify_resource_evidence(self.packet, stale_source, artifact)

    def test_committed_fixture_verifies(self) -> None:
        packet = json.loads((FIXTURES / "program_evidence_resource_v1.json").read_text())
        source = json.loads((FIXTURES / "program_resource_source_v1.json").read_text())
        artifact = json.loads((FIXTURES / "program_resource_evidence_v1.json").read_text())
        self.assertTrue(MODULE.verify_resource_evidence(packet, source, artifact)["verified"])


if __name__ == "__main__":
    unittest.main()
