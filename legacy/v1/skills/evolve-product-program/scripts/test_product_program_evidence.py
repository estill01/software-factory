#!/usr/bin/env python3
"""Focused tests for the deterministic Block 1 evidence packet."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("product_program_evolution.py")
FIXTURES = SCRIPT.parents[1] / "fixtures"
SPEC = importlib.util.spec_from_file_location("product_program_evolution", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


TRACKER = """# Fixture tracker

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Contract | — | `accepted` |
| 1 | Packet | 0 | `not-started` |

## Block 0 — Contract

Status: `accepted`

### Objective

Freeze the contract.

### Completion evidence

Accepted evidence.

### Stop

Stop before packet work.

## Block 1 — Packet

Status: `not-started`

### Objective

Build the packet.

### Completion evidence

Pending.

### Stop

Stop before reflection.
"""


class ProductProgramEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "fixture@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Fixture"], check=True)
        self.tracker = self.write("tracker.md", TRACKER)
        self.product = self.write("product.json", '{"product":"bounded"}\n')
        self.policy = self.write("policy.json", '{"policy":"current"}\n')
        self.events = self.write(
            "events.jsonl",
            '{"kind":"decision","record_id":"EVT-DECISION-1","summary":"bounded"}\n'
            '{"kind":"incident","record_id":"EVT-INCIDENT-1","summary":"closed"}\n',
        )
        self.report = self.write("report.json", '{"report":"verified"}\n')
        self.resource = self.write("resource.json", '{"elapsed_seconds":12,"tokens_estimated":30}\n')
        self.range_head = self.write(
            "range.json",
            json.dumps(
                {
                    "range_head": "a" * 64,
                    "requested_blocks": [0, 1],
                    "target_thread_id": "target-fixture",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
        )
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "fixture"], check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.write_text(text, encoding="utf-8")
        return path

    def sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source(self, path: Path, source_id: str, evidence_class: str) -> dict[str, object]:
        return {
            "evidence_class": evidence_class,
            "owner_root": str(self.root),
            "path": str(path),
            "sha256": self.sha(path),
            "source_id": source_id,
        }

    def reroot(self, packet: dict[str, object]) -> None:
        packet["material_change_fingerprint"] = MODULE.digest(
            {"kind": "product-program-material-change", "value": MODULE._semantic_material_from_packet(packet)}
        )
        packet["packet_id"] = f"program-packet-{packet['material_change_fingerprint'][:20]}"
        packet["currentness_root"] = MODULE.digest(
            {
                "kind": "product-program-currentness",
                "material_change_fingerprint": packet["material_change_fingerprint"],
                "range_head": packet["range"]["range_head"],
                "repository": packet["repository"],
                "source_currentness": {
                    "product_sources": packet["product_sources"],
                    "reports": packet["reports"],
                    "resource_sources": packet["resource_sources"],
                },
                "supervision": packet["supervision"],
                "tracker_sha256": packet["tracker"]["sha256"],
            }
        )
        packet["artifact_root"] = MODULE.digest({key: packet[key] for key in packet if key != "artifact_root"})

    def checkpoint(self, *, completed: bool = False) -> dict[str, object]:
        tracker_snapshot = MODULE.tracker_snapshot(self.tracker.read_bytes())
        revision = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return {
            "current_outcome": {
                "evidence_ids": ["outcome-1"],
                "root": ("b" if completed else "c") * 64,
                "status": "completed" if completed else "in-progress",
            },
            "mission": {
                "mission_root": "d" * 64,
                "source_record": "direct-user-fixture",
                "source_sha256": "e" * 64,
            },
            "prior_checkpoint_identity": None,
            "product_sources": [self.source(self.product, "product-1", "direct-authority")],
            "profile": "target-product-program",
            "protected_capabilities": [
                {"capability_id": "cold-start", "result": "preserved", "source_root": "f" * 64}
            ],
            "range": {
                "accepted_blocks": [0],
                "range_head_source": self.source(self.range_head, "range-head", "canonical-owner"),
                "requested_blocks": [0, 1],
            },
            "reports": [self.source(self.report, "report-1", "independent-review")],
            "repository": {"revision": revision, "root": str(self.root), "tree": tree},
            "resource_sources": [self.source(self.resource, "resource-1", "estimated")],
            "schema_version": 1,
            "supervision": {
                "event_source": self.source(self.events, "events", "canonical-owner"),
                "policy_source": self.source(self.policy, "policy", "canonical-owner"),
                "target_thread_id": "target-fixture",
            },
            "tracker": {
                "path": str(self.tracker),
                "sha256": self.sha(self.tracker),
                "structural_root": tracker_snapshot["structure_root"],
            },
        }

    def test_running_and_completed_packets_are_deterministic_and_verified(self) -> None:
        running = MODULE.prepare_packet(self.checkpoint())
        replay = MODULE.prepare_packet(self.checkpoint())
        completed = MODULE.prepare_packet(self.checkpoint(completed=True))
        self.assertEqual(MODULE.canonical(running), MODULE.canonical(replay))
        self.assertNotEqual(running["artifact_root"], completed["artifact_root"])
        self.assertEqual("in-progress", running["outcome"]["status"])
        self.assertEqual("completed", completed["outcome"]["status"])
        self.assertTrue(MODULE.verify_packet(running)["verified"])
        self.assertFalse(running["authority"]["direct_effects_allowed"])

    def test_committed_running_and_completed_packet_fixtures_verify(self) -> None:
        running = json.loads((FIXTURES / "program_evidence_running_v1.json").read_text(encoding="utf-8"))
        completed = json.loads((FIXTURES / "program_evidence_completed_v1.json").read_text(encoding="utf-8"))
        self.assertTrue(MODULE.verify_packet(running)["verified"])
        self.assertTrue(MODULE.verify_packet(completed)["verified"])
        self.assertEqual("in-progress", running["outcome"]["status"])
        self.assertEqual("completed", completed["outcome"]["status"])

    def test_unchanged_replay_is_constant_identity_comparison_and_zero_cognition(self) -> None:
        checkpoint = self.checkpoint()
        prior = MODULE.prepare_packet(checkpoint)
        result = MODULE.prepare_result(checkpoint, prior)
        self.assertEqual("continue-program-unchanged", result["action"])
        self.assertFalse(result["changed"])
        self.assertEqual(0, result["model_calls"])
        self.assertFalse(result["cognitive_work_started"])

    def test_governing_semantic_and_currentness_changes_are_detected(self) -> None:
        baseline_checkpoint = self.checkpoint()
        baseline = MODULE.prepare_packet(baseline_checkpoint)

        outcome_changed = deepcopy(baseline_checkpoint)
        outcome_changed["current_outcome"]["root"] = "1" * 64
        outcome_packet = MODULE.prepare_packet(outcome_changed)
        self.assertNotEqual(baseline["material_change_fingerprint"], outcome_packet["material_change_fingerprint"])

        self.policy.write_text('{"policy":"successor"}\n', encoding="utf-8")
        currentness_changed = self.checkpoint()
        currentness_packet = MODULE.prepare_packet(currentness_changed)
        self.assertEqual(baseline["material_change_fingerprint"], currentness_packet["material_change_fingerprint"])
        self.assertNotEqual(baseline["currentness_root"], currentness_packet["currentness_root"])

        self.report.write_text('{"report":"prose-only successor"}\n', encoding="utf-8")
        report_changed = self.checkpoint()
        report_packet = MODULE.prepare_packet(report_changed)
        self.assertEqual(currentness_packet["material_change_fingerprint"], report_packet["material_change_fingerprint"])
        self.assertNotEqual(currentness_packet["currentness_root"], report_packet["currentness_root"])

        self.events.write_text(
            self.events.read_text(encoding="utf-8")
            + '{"kind":"decision","record_id":"EVT-DECISION-2","summary":"changed"}\n',
            encoding="utf-8",
        )
        decision_changed = self.checkpoint()
        decision_packet = MODULE.prepare_packet(decision_changed)
        self.assertNotEqual(baseline["material_change_fingerprint"], decision_packet["material_change_fingerprint"])

    def test_stale_tracker_repository_range_and_target_are_rejected(self) -> None:
        stale = self.checkpoint()
        self.tracker.write_text(TRACKER + "\n", encoding="utf-8")
        with self.assertRaisesRegex(MODULE.ProductProgramError, "tracker is stale"):
            MODULE.prepare_packet(stale)
        self.tracker.write_text(TRACKER, encoding="utf-8")

        wrong_revision = self.checkpoint()
        wrong_revision["repository"]["revision"] = "0" * 40
        with self.assertRaisesRegex(MODULE.ProductProgramError, "repository revision"):
            MODULE.prepare_packet(wrong_revision)

        wrong_range = self.checkpoint()
        wrong_range["range"]["accepted_blocks"] = []
        with self.assertRaisesRegex(MODULE.ProductProgramError, "accepted Blocks are stale"):
            MODULE.prepare_packet(wrong_range)

        wrong_target = self.checkpoint()
        wrong_target["supervision"]["target_thread_id"] = "target-other"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "target mismatches"):
            MODULE.prepare_packet(wrong_target)

    def test_substituted_roots_symlinks_and_unbounded_paths_are_rejected(self) -> None:
        broad = self.checkpoint()
        broad["product_sources"][0]["owner_root"] = "/"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "too broad"):
            MODULE.prepare_packet(broad)

        actual_home = self.checkpoint()
        actual_home["product_sources"][0]["owner_root"] = str(Path.home().resolve())
        with self.assertRaisesRegex(MODULE.ProductProgramError, "too broad"):
            MODULE.prepare_packet(actual_home)

        home = self.checkpoint()
        home["product_sources"][0]["path"] = "$HOME/product.json"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "literal absolute"):
            MODULE.prepare_packet(home)

        link = self.root / "product-link.json"
        link.symlink_to(self.product)
        symlinked = self.checkpoint()
        symlinked["product_sources"][0]["path"] = str(link)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "symlink"):
            MODULE.prepare_packet(symlinked)

        outside = self.root.parent / f"{self.root.name}-outside.json"
        outside.write_text('{"outside":true}\n', encoding="utf-8")
        self.addCleanup(outside.unlink)
        escaped = self.checkpoint()
        escaped["product_sources"][0] = self.source(outside, "product-escaped", "direct-authority")
        escaped["product_sources"][0]["owner_root"] = str(self.root)
        escaped["product_sources"][0]["path"] = str(self.root / ".." / outside.name)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "literal absolute"):
            MODULE.prepare_packet(escaped)

    def test_missing_resource_class_caller_authority_and_hidden_output_reject(self) -> None:
        missing_product = self.checkpoint()
        missing_product["product_sources"] = []
        with self.assertRaisesRegex(MODULE.ProductProgramError, "exact product source"):
            MODULE.prepare_packet(missing_product)

        missing_class = self.checkpoint()
        missing_class["resource_sources"][0]["evidence_class"] = ""
        with self.assertRaisesRegex(MODULE.ProductProgramError, "evidence class"):
            MODULE.prepare_packet(missing_class)

        asserted = self.checkpoint()
        asserted["authority"] = {"may_write": True}
        with self.assertRaisesRegex(MODULE.ProductProgramError, "checkpoint keys"):
            MODULE.prepare_packet(asserted)

        packet = MODULE.prepare_packet(self.checkpoint())
        packet["raw_transcript"] = "hidden target output"
        with self.assertRaisesRegex(MODULE.ProductProgramError, "packet keys"):
            MODULE.verify_packet(packet)

        missing_resource = MODULE.prepare_packet(self.checkpoint())
        missing_resource["resource_sources"] = []
        self.reroot(missing_resource)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "typed resource source"):
            MODULE.verify_packet(missing_resource)

        forged_frontier = MODULE.prepare_packet(self.checkpoint())
        forged_frontier["range"]["accepted_blocks"] = [0, 1]
        forged_frontier["range"]["remaining_blocks"] = []
        forged_frontier["range"]["next_eligible_blocks"] = []
        self.reroot(forged_frontier)
        with self.assertRaisesRegex(MODULE.ProductProgramError, "range partition"):
            MODULE.verify_packet(forged_frontier)

    def test_cli_prepare_and_verify_emit_canonical_results(self) -> None:
        checkpoint_path = self.root / "checkpoint.json"
        checkpoint_path.write_bytes(MODULE.canonical(self.checkpoint()))
        prepared = subprocess.run(
            [sys.executable, str(SCRIPT), "prepare", "--input", str(checkpoint_path)],
            check=True,
            capture_output=True,
        )
        result = json.loads(prepared.stdout)
        self.assertEqual("packet-prepared", result["action"])
        packet_path = self.root / "packet.json"
        packet_path.write_bytes(MODULE.canonical(result["packet"]))
        verified = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", "--packet", str(packet_path)],
            check=True,
            capture_output=True,
        )
        self.assertTrue(json.loads(verified.stdout)["verified"])


if __name__ == "__main__":
    unittest.main()
