#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("factory_evolution.py")
SPEC = importlib.util.spec_from_file_location("factory_evolution", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
factory_evolution = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(factory_evolution)


def event_record(
    record_id: str,
    *,
    previous: str | None,
    kind: str = "check",
    summary: str = "Productive bounded execution preserved the intended capability.",
    evidence: list[object] | None = None,
) -> dict[str, object]:
    material: dict[str, object] = {
        "schema_version": 1,
        "kind": kind,
        "record_id": record_id,
        "previous_record_sha256": previous,
        "target_thread_id": "thread-synthetic",
        "timestamp": f"2026-08-07T00:00:{int(record_id[-2:]):02d}+00:00",
        "status": "observed",
        "severity": "info",
        "category": "productive-pattern",
        "active_block": "Block 1",
        "checkpoint": "focused-validation",
        "summary": summary,
        "resolution": "No exception required." if kind != "incident" else "Exception retained.",
        "evidence": evidence or ["test:synthetic-positive"],
        "reasoning": "This field is deliberately not retained.",
    }
    return {**material, "record_sha256": factory_evolution.digest(material)}


def report_record(source_root: str, *, assessment: str = "A productive pattern recurred.") -> dict[str, object]:
    report_id = f"weekly-20260807T000000Z-20260807T010000Z-{source_root[:12]}"
    coverage = {
        "start": "2026-08-07T00:00:00+00:00",
        "end": "2026-08-07T01:00:00+00:00",
    }
    return {
        "schema_version": 1,
        "kind": "supervision-weekly-review-record",
        "report_id": report_id,
        "source_root": source_root,
        "coverage": coverage,
        "metrics": {
            "report_id": report_id,
            "source": {"source_root": source_root},
        },
        "cognitive_review": {
            "schema_version": 1,
            "kind": "supervision-weekly-review-cognitive-review",
            "report_id": report_id,
            "source_root": source_root,
            "headline": "Productive behavior and an exception both need evaluation.",
            "executive_assessment": assessment,
            "overall_posture": "bounded",
            "reviewer_method": "synthetic-fixture",
            "sections": {
                "productive_patterns": [
                    {
                        "title": "Bounded execution",
                        "assessment": assessment,
                        "evidence": ["EVT-01", "EVT-02"],
                    }
                ],
                "exceptions": [
                    {
                        "title": "Retained exception",
                        "assessment": "One conflicting result limits applicability.",
                        "evidence": ["EVT-03"],
                    }
                ],
            },
        },
    }


class LearningPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        first = event_record("EVT-01", previous=None)
        second = event_record("EVT-02", previous=str(first["record_sha256"]))
        third = event_record(
            "EVT-03",
            previous=str(second["record_sha256"]),
            kind="incident",
            summary="An exception constrained the productive pattern.",
        )
        self.events = self.write_events("events-a.jsonl", [first, second, third])
        source_root = factory_evolution.digest(
            {"record_hashes": [item["record_sha256"] for item in (first, second, third)]}
        )
        self.report = self.write_json("report-a.json", report_record(source_root))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_json(self, name: str, value: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path

    def write_events(self, name: str, values: list[dict[str, object]]) -> Path:
        path = self.root / name
        path.write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in values),
            encoding="utf-8",
        )
        return path

    def build(self, *, reports: list[Path] | None = None, events: list[Path] | None = None) -> dict[str, object]:
        return factory_evolution.build_learning_packet(
            report_paths=reports or [self.report],
            event_paths=events or [self.events],
        )

    def test_equivalent_inputs_are_order_independent_and_deduplicated(self) -> None:
        duplicate_report = self.root / "report-duplicate.json"
        duplicate_report.write_bytes(self.report.read_bytes())
        duplicate_events = self.root / "events-duplicate.jsonl"
        duplicate_events.write_bytes(self.events.read_bytes())

        baseline = self.build()
        duplicated = self.build(
            reports=[duplicate_report, self.report, duplicate_report],
            events=[duplicate_events, self.events, duplicate_events],
        )

        self.assertEqual(baseline, duplicated)
        self.assertEqual(baseline["coverage"]["report_roots"], 1)
        self.assertEqual(baseline["coverage"]["event_ledger_roots"], 1)
        self.assertEqual(factory_evolution.verify_learning_packet(baseline), baseline)

    def test_changed_explicit_source_changes_packet_root(self) -> None:
        baseline = self.build()
        changed_report = report_record(str(baseline["sources"]["reports"][0]["source_root"]))
        changed_report["cognitive_review"]["sections"]["productive_patterns"][0][
            "assessment"
        ] = "The productive pattern changed under the candidate."
        changed = self.write_json("report-changed.json", changed_report)

        rebuilt = self.build(reports=[changed])

        self.assertNotEqual(baseline["packet_root"], rebuilt["packet_root"])

    def test_claims_resolve_to_exact_report_or_ledger_identities(self) -> None:
        packet = self.build()
        report = packet["sources"]["reports"][0]
        ledger_root = packet["sources"]["event_ledgers"][0]["ledger_root"]

        self.assertEqual(packet["authority"], "derived-non-authoritative")
        for hypothesis in packet["evidence"]["report_hypotheses"]:
            self.assertEqual(hypothesis["source_report_id"], report["report_id"])
            self.assertEqual(hypothesis["source_root"], report["source_root"])
            self.assertEqual(hypothesis["source_report_sha256"], report["report_sha256"])
        for event in packet["evidence"]["events"]:
            self.assertIn(ledger_root, event["source_ledger_roots"])
            self.assertRegex(event["record_sha256"], r"^[0-9a-f]{64}$")

    def test_malformed_jsonl_and_stale_record_hash_are_rejected(self) -> None:
        malformed = self.root / "malformed.jsonl"
        malformed.write_text('{"not":\n', encoding="utf-8")
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "malformed JSON"):
            self.build(events=[malformed])

        value = json.loads(self.events.read_text().splitlines()[0])
        value["summary"] = "Mutated after hashing."
        stale = self.write_events("stale.jsonl", [value])
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "stale record hash"):
            self.build(events=[stale])

    def test_report_identity_mismatch_is_rejected(self) -> None:
        value = json.loads(self.report.read_text())
        value["cognitive_review"]["source_root"] = "0" * 64
        mismatch = self.write_json("mismatch.json", value)

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "identity"):
            self.build(reports=[mismatch])

    def test_terminal_report_kind_is_explicitly_outside_weekly_loader_contract(self) -> None:
        value = json.loads(self.report.read_text())
        value["kind"] = "supervision-terminal-implementation-report-record"
        terminal = self.write_json("terminal.json", value)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "Unsupported report kind"
        ):
            self.build(reports=[terminal])

    def test_unknown_event_kind_is_excluded_and_counted(self) -> None:
        unknown = event_record("EVT-01", previous=None, kind="future-unknown-kind")
        path = self.write_events("unknown.jsonl", [unknown])

        packet = self.build(events=[path])

        self.assertEqual(packet["coverage"]["unsupported_event_kinds"], 1)
        self.assertEqual(packet["coverage"]["retained_event_records"], 0)

    def test_text_and_evidence_are_bounded_and_reasoning_is_not_retained(self) -> None:
        long_text = "x" * 2_000
        value = event_record(
            "EVT-01",
            previous=None,
            summary=long_text,
            evidence=[f"reference-{index}-" + long_text for index in range(20)],
        )
        path = self.write_events("bounded.jsonl", [value])
        packet = self.build(events=[path])
        retained = packet["evidence"]["events"][0]

        self.assertLessEqual(len(retained["summary"]), factory_evolution.MAX_EVENT_TEXT)
        self.assertEqual(len(retained["evidence_refs"]), factory_evolution.MAX_EVIDENCE_REFS)
        self.assertTrue(all(len(item) <= factory_evolution.MAX_REFERENCE_TEXT for item in retained["evidence_refs"]))
        self.assertNotIn("reasoning", retained)

    def test_raw_transcript_fields_are_rejected(self) -> None:
        value = json.loads(self.report.read_text())
        value["raw_transcript"] = "target conversation"
        unsafe = self.write_json("unsafe.json", value)

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "forbidden raw-content"):
            self.build(reports=[unsafe])

    def test_inputs_are_required_and_never_discovered_implicitly(self) -> None:
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "explicit report"):
            factory_evolution.build_learning_packet(report_paths=[], event_paths=[self.events])
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "explicit event"):
            factory_evolution.build_learning_packet(report_paths=[self.report], event_paths=[])

    def test_stale_packet_identity_is_rejected(self) -> None:
        packet = self.build()
        packet["coverage"]["retained_event_records"] = 9000

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "identity is stale"):
            factory_evolution.verify_learning_packet(packet)


if __name__ == "__main__":
    unittest.main()
