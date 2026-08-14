#!/usr/bin/env python3
"""Mechanical checks for the repository reconciliation contract and fixtures."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "references" / "repository-reconciliation-contract.md"
FIXTURE = ROOT / "fixtures" / "repository_reconciliation_v1.json"
SCHEMA = ROOT / "references" / "repository-reconciliation-schema-v1.json"
CURRENTNESS = ROOT / "references" / "source-adaptation-currentness-v1.json"
SCHEMA_CANONICAL_SHA256 = "df766b0288511ed9071941c393b641502cf502db51af1aa88f73d5bb927c4a85"
CURRENTNESS_CANONICAL_SHA256 = "958c6abafac2b1d2da2bfd4267fd193ea993a8eb71516504e758e4d4ea8c7c11"
DISPOSITIONS = {
    "integrated",
    "preserved",
    "validly-superseded",
    "generated-reproducible",
    "retain",
}
POSTURES = {"safe-cleanup", "coordinated-reconciliation", "retain", "replan", "resume-current-run"}
REQUIRED_CASES = {
    "clean-redundant-worktree",
    "unique-committed-work",
    "dirty-and-local-bytes",
    "detached-and-stashed-work",
    "moved-ref-after-plan",
    "merge-ready-accepted-pr",
    "superseded-pr",
    "open-unaccepted-pr",
    "provider-unavailable-pr",
    "active-overlapping-writer",
    "conflict-drops-functionality",
    "interrupted-cleanup",
    "successful-retirement",
    "restart-and-dormancy",
    "unknown-malformed-sensitive-state",
}
REQUIRED_SOURCE_STATES = {
    "staged",
    "unstaged",
    "untracked",
    "ignored",
    "detached",
    "stash",
    "ref-moved",
    "merge-ready-pr",
    "superseded-pr",
    "open-pr",
    "provider-unavailable-pr",
    "overlapping-writer",
    "unaffected-writer",
    "missing-route",
    "partial-effects",
    "eligible-lane",
    "dependency-dormant-lane",
    "unknown",
    "malformed",
    "sensitive",
}
RECORDS = {
    "source-snapshot",
    "inventory",
    "plan",
    "preservation",
    "capability-coverage",
    "integration",
    "validation",
    "publication",
    "deletion",
    "restart",
    "outcome",
    "status",
}
REQUIRED_CONTRACT_CLAUSES = {
    "Deletion eligibility requires both independent dimensions:",
    "| `schema_version` | integer, exactly `1` |",
    "| `inventory` | exhaustive `artifacts`, `artifact_count`, `inventory_root` | source snapshot |",
    "| Deletion eligibility | deterministic manifest plus distinct semantic reviewer and current supervisor deletion gate | eligible only when all three agree on the same roots |",
    "| Accepted-source selection and integration | cleanup writer using Git plus tracker/review acceptance owners | integrate only exact current accepted sources after quiescence |",
    "| Candidate validation and exact review | repository test/build owners plus distinct exact-revision reviewer | freeze and prove the aggregate candidate without publishing it |",
    "repository-reconciliation-schema-v1.json",
    "source-adaptation-currentness-v1.json",
}
CASE_EXPECTATIONS = {
    "merge-ready-accepted-pr": ("coordinated-reconciliation", "integrated"),
    "superseded-pr": ("coordinated-reconciliation", "validly-superseded"),
    "open-unaccepted-pr": ("retain", "retain"),
    "provider-unavailable-pr": ("retain", "retain"),
    "unknown-malformed-sensitive-state": ("retain", "retain"),
}


class ReconciliationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = CONTRACT.read_text(encoding="utf-8")
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.currentness = json.loads(CURRENTNESS.read_text(encoding="utf-8"))

    def test_contract_names_no_loss_and_authority_boundaries(self) -> None:
        required = {
            "## Artifact inventory and disposition",
            "## Byte and functionality preservation",
            "## Owner map",
            "## Phase and gate contract",
            "Unknown bytes are",
            "supervisor repository writes",
            "Record-specific required fields and dependencies",
            "Inventory and source-snapshot production",
            "Deletion eligibility",
            "Successor plan after invalidation",
            "Restart or dormant-path selection",
        }
        required |= REQUIRED_CONTRACT_CLAUSES
        for marker in required:
            self.assertIn(marker, self.contract)

    def test_machine_schema_and_currentness_are_exact(self) -> None:
        self.assertEqual(self.schema["schema_version"], 1)
        self.assertEqual(
            set(self.schema),
            {
                "base_fields",
                "cross_field_rules",
                "item_types",
                "phases",
                "record_field_policy",
                "records",
                "schema_version",
                "statuses",
            },
        )
        schema_canonical = json.dumps(
            self.schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(schema_canonical).hexdigest(), SCHEMA_CANONICAL_SHA256)
        self.assertEqual(set(self.schema["records"]), RECORDS)
        self.assertEqual(
            self.schema["record_field_policy"],
            {"additional_fields": False, "required": "all-declared-fields"},
        )
        self.assertEqual(
            self.schema["base_fields"]["schema_version"],
            {"const": 1, "type": "integer"},
        )
        self.assertEqual(self.schema["records"]["inventory"]["binds"], ["source_snapshot_root"])
        self.assertEqual(
            self.schema["records"]["source-snapshot"]["fields"]["remote_main"],
            {"format": "git-oid-or-null", "type": ["string", "null"]},
        )
        self.assertEqual(self.schema["records"]["deletion"]["phase"], "delete")
        self.assertEqual(
            self.schema["records"]["deletion"]["binds"],
            ["publication_root", "preservation_root", "coverage_root", "deletion_review_root", "deletion_gate_root"],
        )
        for record in self.schema["records"].values():
            self.assertEqual(set(record), {"binds", "fields", "phase"})
            self.assertTrue(record["fields"])
            self.assertIn(record["phase"], self.schema["phases"])
            self.assertFalse(set(record["binds"]) - set(self.schema["base_fields"]) - set(record["fields"]))
            for field in record["fields"].values():
                if "items" in field and field["items"] not in {"string", "integer"}:
                    self.assertIn(field["items"], self.schema["item_types"])
                if "item_ref" in field:
                    self.assertIn(field["item_ref"], self.schema["item_types"])
        for item in self.schema["item_types"].values():
            self.assertEqual(set(item), {"additional_fields", "fields", "required"})
            self.assertFalse(item["additional_fields"])
            self.assertEqual(set(item["fields"]), set(item["required"]))

        no_loss_rule = self.schema["cross_field_rules"][
            "unknown-no-loss-dimension-forces-retain"
        ]
        self.assertEqual(no_loss_rule["item_type"], "no-loss-entry")
        self.assertEqual(
            no_loss_rule["if_any"],
            {"byte_result": ["unknown"], "capability_result": ["unknown"]},
        )
        self.assertEqual(no_loss_rule["then"], {"deletion_eligible": False})
        deletion_fields = self.schema["item_types"]["deletion-effect"]["fields"]
        self.assertTrue(
            {
                "archive_id",
                "coverage_root",
                "dirt",
                "effect_kind",
                "owner_id",
                "pr_number",
                "preservation_root",
            }
            <= set(deletion_fields)
        )

        self.assertEqual(self.currentness["schema_version"], 1)
        currentness_canonical = json.dumps(
            self.currentness, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(currentness_canonical).hexdigest(),
            CURRENTNESS_CANONICAL_SHA256,
        )
        self.assertEqual(self.currentness["observed_at"], "2026-08-14T06:04:27Z")
        self.assertEqual(self.currentness["provider"]["owner"], "github")
        self.assertEqual(self.currentness["provider"]["result_count"], 0)
        self.assertEqual(
            self.currentness["provider"]["payload_sha256"],
            "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
        )
        self.assertEqual(
            self.currentness["provider"]["argv"],
            [
                "gh",
                "pr",
                "list",
                "--repo",
                "estill01/software-factory",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,state,headRefName,baseRefName,isDraft,mergeStateStatus,updatedAt",
            ],
        )
        self.assertEqual(self.currentness["provider"]["canonicalizer"], ["jq", "-cS"])
        self.assertEqual(
            self.currentness["provider"]["selected_fields"],
            [
                "baseRefName",
                "headRefName",
                "isDraft",
                "mergeStateStatus",
                "number",
                "state",
                "updatedAt",
            ],
        )
        self.assertEqual(
            self.currentness["provider"]["tool_version"],
            "gh version 2.92.0 (2026-04-28)",
        )
        self.assertEqual(
            self.currentness["active_owner"]["head"],
            "0b97d661bb8e108963aa34ecaaaa992176f104d6",
        )
        self.assertEqual(
            self.currentness["active_owner"]["status"],
            "dirty-in-progress-nonoverlapping",
        )
        self.assertFalse(self.currentness["active_owner"]["overlap_with_cleanup_paths"])
        self.assertEqual(
            self.currentness["active_owner"]["dirty_paths"],
            [
                "scripts/skill_release.py",
                "scripts/test_skill_release.py",
                "supervise-tracker-runs/scripts/supervision_log.py",
                "supervise-tracker-runs/scripts/test_supervision_log.py",
            ],
        )
        self.assertEqual(
            self.currentness["active_owner"]["dirty_status_sha256"],
            "4a86ee644331a0f210cb8629c4ba339eebfe6e4cf1df655839537ad9fad9430d",
        )

    def test_fixture_is_complete_unique_and_content_minimized(self) -> None:
        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual(set(self.fixture["dispositions"]), DISPOSITIONS)
        self.assertEqual(self.fixture["content_policy"], "synthetic-content-minimized")
        cases = self.fixture["cases"]
        ids = [case["case_id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), REQUIRED_CASES)
        required_fields = {
            "case_id",
            "expected_posture",
            "forbidden_claims",
            "proposed_disposition",
            "required_proof",
            "source_state",
        }
        for case in cases:
            self.assertEqual(set(case), required_fields)
            self.assertIn(case["proposed_disposition"], DISPOSITIONS)
            self.assertIn(case["expected_posture"], POSTURES)
            self.assertTrue(case["required_proof"])
            self.assertTrue(case["forbidden_claims"])
            self.assertEqual(len(case["required_proof"]), len(set(case["required_proof"])))
            self.assertEqual(len(case["source_state"]), len(set(case["source_state"])))

        observed_states = {state for case in cases for state in case["source_state"]}
        self.assertTrue(REQUIRED_SOURCE_STATES <= observed_states)

        self.assertEqual(
            set(self.fixture),
            {"cases", "content_policy", "dispositions", "schema_version"},
        )
        raw = json.dumps(self.fixture, sort_keys=True)
        protected_patterns = (
            r"/Users/",
            r"019f[0-9a-f-]{20,}",
            r"PRIVATE PROJECT CONTENT",
            r"BEGIN [A-Z ]*PRIVATE KEY",
            r"(?i)(password|api[_-]?key|access[_-]?token)\s*[:=]",
        )
        for pattern in protected_patterns:
            self.assertIsNone(re.search(pattern, raw))

        by_id = {case["case_id"]: case for case in cases}
        for case_id, (posture, disposition) in CASE_EXPECTATIONS.items():
            self.assertEqual(by_id[case_id]["expected_posture"], posture)
            self.assertEqual(by_id[case_id]["proposed_disposition"], disposition)

    def test_adversarial_schema_and_currentness_mutations_are_rejected(self) -> None:
        mutations = {
            "byte-hash-type": lambda probe: probe.schema["item_types"]["byte-entry"][
                "fields"
            ].__setitem__("sha256", {"type": "integer"}),
            "forced-unknown-deletion": lambda probe: probe.schema["cross_field_rules"][
                "unknown-no-loss-dimension-forces-retain"
            ]["then"].__setitem__("deletion_eligible", True),
            "orphan-dependency": lambda probe: probe.schema["records"]["plan"][
                "fields"
            ].pop("inventory_root"),
            "missing-remote-fabricated": lambda probe: probe.schema["records"][
                "source-snapshot"
            ]["fields"].__setitem__("remote_main", {"format": "git-oid", "type": "string"}),
            "provider-argv": lambda probe: probe.currentness["provider"].__setitem__(
                "argv", ["gh", "pr", "list", "--repo", "wrong/repository"]
            ),
            "provider-canonicalizer": lambda probe: probe.currentness["provider"].__setitem__(
                "canonicalizer", ["not-jq"]
            ),
            "provider-fields": lambda probe: probe.currentness["provider"].__setitem__(
                "selected_fields", []
            ),
            "provider-version": lambda probe: probe.currentness["provider"].__setitem__(
                "tool_version", "unknown"
            ),
            "dirty-paths": lambda probe: probe.currentness["active_owner"].__setitem__(
                "dirty_paths", ["invented-a", "invented-b", "invented-c", "invented-d"]
            ),
            "dirty-root": lambda probe: probe.currentness["active_owner"].__setitem__(
                "dirty_status_sha256", "0" * 64
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                probe = ReconciliationContractTests(
                    "test_machine_schema_and_currentness_are_exact"
                )
                probe.setUp()
                mutate(probe)
                with self.assertRaises(AssertionError):
                    probe.test_machine_schema_and_currentness_are_exact()

    def test_negative_cases_preserve_unknown_and_functionality(self) -> None:
        by_id = {case["case_id"]: case for case in self.fixture["cases"]}
        self.assertEqual(by_id["unique-committed-work"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["dirty-and-local-bytes"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["moved-ref-after-plan"]["expected_posture"], "replan")
        dirty = by_id["dirty-and-local-bytes"]
        self.assertEqual(
            set(dirty["source_state"]),
            {"staged", "unstaged", "untracked", "ignored"},
        )
        overlap = by_id["active-overlapping-writer"]
        self.assertEqual(overlap["expected_posture"], "coordinated-reconciliation")
        self.assertEqual(overlap["proposed_disposition"], "retain")
        self.assertTrue(
            {"owner-checkpoint", "owner-inactive", "quiescence-gate"}
            <= set(overlap["required_proof"])
        )
        conflict = by_id["conflict-drops-functionality"]
        self.assertEqual(conflict["proposed_disposition"], "retain")
        self.assertIn("distinct-semantic-review", conflict["required_proof"])

        retain_states = {
            "unknown",
            "malformed",
            "sensitive",
            "unaccepted",
            "provider-unavailable-pr",
        }
        for case in self.fixture["cases"]:
            if retain_states & set(case["source_state"]):
                self.assertEqual(case["proposed_disposition"], "retain", case["case_id"])

        self.assertEqual(by_id["open-unaccepted-pr"]["proposed_disposition"], "retain")
        self.assertEqual(by_id["provider-unavailable-pr"]["expected_posture"], "retain")
        unknown = by_id["unknown-malformed-sensitive-state"]
        self.assertIn("caller-selected-task-acceptance", unknown["forbidden_claims"])


if __name__ == "__main__":
    unittest.main()
