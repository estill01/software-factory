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

    def write_report_for_records(self, name: str, record_ids: list[str]) -> Path:
        value = json.loads(self.report.read_text())
        for items in value["cognitive_review"]["sections"].values():
            for item in items:
                item["evidence"] = list(record_ids)
        return self.write_json(name, value)

    def build(self, *, reports: list[Path] | None = None, events: list[Path] | None = None) -> dict[str, object]:
        return factory_evolution.build_learning_packet(
            report_paths=reports or [self.report],
            event_paths=events or [self.events],
        )

    def reroot(self, packet: dict[str, object]) -> None:
        material = {
            key: value
            for key, value in packet.items()
            if key not in {"packet_id", "packet_root"}
        }
        packet_root = factory_evolution.digest(material)
        packet["packet_root"] = packet_root
        packet["packet_id"] = "learning-" + packet_root[:20]

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

    def test_event_must_belong_to_every_claimed_source_ledger(self) -> None:
        fourth = event_record("EVT-04", previous=None)
        other = self.write_events("events-other.jsonl", [fourth])
        packet = self.build(events=[self.events, other])
        other_root = next(
            item["ledger_root"]
            for item in packet["sources"]["event_ledgers"]
            if item["record_count"] == 1
        )
        first_event = packet["evidence"]["events"][0]
        first_event["source_ledger_roots"] = sorted(
            first_event["source_ledger_roots"] + [other_root]
        )
        self.reroot(packet)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "every claimed source ledger"
        ):
            factory_evolution.verify_learning_packet(packet)

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

    def test_conflicting_reports_for_one_source_root_are_rejected(self) -> None:
        value = json.loads(self.report.read_text())
        value["cognitive_review"]["headline"] = "A conflicting derivative report."
        conflict = self.write_json("report-conflict.json", value)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "conflicting report content"
        ):
            self.build(reports=[self.report, conflict])

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
        report = self.write_report_for_records("unknown-report.json", ["EVT-01"])

        packet = self.build(reports=[report], events=[path])

        self.assertEqual(packet["coverage"]["unsupported_event_kinds"], 1)
        self.assertEqual(packet["coverage"]["retained_event_records"], 0)

    def test_report_evidence_must_resolve_to_an_explicit_canonical_event(self) -> None:
        value = json.loads(self.report.read_text())
        value["cognitive_review"]["sections"]["exceptions"][0]["evidence"] = [
            "EVT-NOT-PRESENT"
        ]
        dangling = self.write_json("dangling.json", value)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "does not resolve"
        ):
            self.build(reports=[dangling])

    def test_record_identity_is_rejected_rather_than_rewritten(self) -> None:
        long_id = "E" * 200 + "01"
        value = event_record(long_id, previous=None)
        path = self.write_events("long-id.jsonl", [value])

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "exact bounded identifier"
        ):
            self.build(events=[path])

    def test_text_and_evidence_are_bounded_and_reasoning_is_not_retained(self) -> None:
        long_text = "x" * 2_000
        value = event_record(
            "EVT-01",
            previous=None,
            summary=long_text,
            evidence=[f"reference-{index}-" + long_text for index in range(20)],
        )
        path = self.write_events("bounded.jsonl", [value])
        report = self.write_report_for_records("bounded-report.json", ["EVT-01"])
        packet = self.build(reports=[report], events=[path])
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

    def test_verifier_rejects_rerooted_raw_content(self) -> None:
        packet = self.build()
        packet["raw_transcript"] = "x" * 10_000
        self.reroot(packet)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "forbidden raw-content"
        ):
            factory_evolution.verify_learning_packet(packet)

    def test_aggregate_inputs_and_retained_arrays_are_bounded(self) -> None:
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "Too many explicit report"):
            self.build(
                reports=[self.report]
                * (factory_evolution.MAX_EXPLICIT_REPORT_INPUTS + 1)
            )

        packet = self.build()
        event = packet["evidence"]["events"][0]
        packet["evidence"]["events"] = [event] * (
            factory_evolution.MAX_PACKET_EVENTS + 1
        )
        self.reroot(packet)
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "bounded array"):
            factory_evolution.verify_learning_packet(packet)

    def test_aggregate_canonical_record_index_is_bounded(self) -> None:
        packet = self.build()
        ledger = packet["sources"]["event_ledgers"][0]
        index = list(ledger["record_index"])
        for number in range(
            len(index), factory_evolution.MAX_PACKET_CANONICAL_RECORDS + 1
        ):
            record_id = f"IDX-{number:05d}"
            index.append(
                {
                    "record_id": record_id,
                    "record_sha256": factory_evolution.digest(
                        {"synthetic_record": record_id}
                    ),
                }
            )
        hashes = [item["record_sha256"] for item in index]
        ledger["record_index"] = index
        ledger["record_count"] = len(index)
        ledger["first_record_sha256"] = hashes[0]
        ledger["last_record_sha256"] = hashes[-1]
        ledger["ledger_root"] = factory_evolution.digest({"record_hashes": hashes})
        packet["coverage"]["canonical_event_records"] = len(index)
        self.reroot(packet)

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "aggregate bound"
        ):
            factory_evolution.verify_learning_packet(packet)

    def test_verifier_rejects_empty_or_reordered_rerooted_packets(self) -> None:
        empty = self.build()
        empty["sources"]["reports"] = []
        empty["sources"]["event_ledgers"] = []
        empty["evidence"]["report_hypotheses"] = []
        empty["evidence"]["events"] = []
        empty["coverage"] = {
            "report_roots": 0,
            "event_ledger_roots": 0,
            "canonical_event_records": 0,
            "retained_event_records": 0,
            "retained_report_hypotheses": 0,
            "unsupported_event_kinds": 0,
        }
        self.reroot(empty)
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "bounded array"):
            factory_evolution.verify_learning_packet(empty)

        reordered = self.build()
        reordered["evidence"]["report_hypotheses"].reverse()
        self.reroot(reordered)
        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "deterministically ordered"
        ):
            factory_evolution.verify_learning_packet(reordered)

    def test_inputs_are_required_and_never_discovered_implicitly(self) -> None:
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "explicit report"):
            factory_evolution.build_learning_packet(report_paths=[], event_paths=[self.events])
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "explicit event"):
            factory_evolution.build_learning_packet(report_paths=[self.report], event_paths=[])

    def test_stale_packet_identity_is_rejected(self) -> None:
        packet = self.build()
        packet["coverage"]["retained_event_records"] = 9000

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "coverage.*stale"):
            factory_evolution.verify_learning_packet(packet)


class EvolutionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        records: list[dict[str, object]] = []
        previous: str | None = None
        for record_id, kind, summary in (
            ("EVT-000001", "check", "Productive bounded execution preserved capability."),
            ("EVT-000002", "incident", "An exception exposed product underreach."),
            ("EVT-000003", "checkpoint-review", "Review identified a reusable capability gap."),
            ("EVT-000004", "resolution", "A bounded correction preserved architecture."),
        ):
            record = event_record(
                record_id,
                previous=previous,
                kind=kind,
                summary=summary,
            )
            records.append(record)
            previous = str(record["record_sha256"])
        event_path = self.root / "events.jsonl"
        event_path.write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in records),
            encoding="utf-8",
        )
        source_root = factory_evolution.digest(
            {"record_hashes": [item["record_sha256"] for item in records]}
        )
        report = report_record(source_root)
        for items in report["cognitive_review"]["sections"].values():
            for item in items:
                item["evidence"] = ["EVT-000001", "EVT-000002"]
        report_path = self.root / "report.json"
        report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
        self.packet = factory_evolution.build_learning_packet(
            report_paths=[report_path], event_paths=[event_path]
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def dimensions(self) -> dict[str, object]:
        return {
            name: {
                "rating": "high" if name in {"effect", "product_gain", "reversibility"} else "medium",
                "rationale": f"Visible {name} evidence remains separately reviewable.",
                "evidence_ids": ["EVT-000001"],
            }
            for name in factory_evolution.SELECTION_DIMENSIONS
        }

    def candidate(self, candidate_id: str, candidate_type: str) -> dict[str, object]:
        selected = candidate_id == "candidate-skill-method"
        return {
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "capability_gap": "The factory lacks source-backed target-product capability review.",
            "effect": "Make product underreach and overarchitecture visible before acceptance.",
            "meta_pattern_ids": ["meta-product-alignment"],
            "evidence_ids": ["EVT-000001", "EVT-000002", "EVT-000003"],
            "protected_capabilities": ["bounded execution", "canonical ownership"],
            "applicability": "Consequential tracker authoring and implementation decisions.",
            "tradeoffs": ["Adds one explicit review step"],
            "uncertainty": "Current evidence covers a bounded set of supervised runs.",
            "counterexample_case_ids": ["EVT-000002"],
            "counterexample_posture": "observed",
            "counterexample_search": "Compared the underreach incident with the bounded resolution.",
            "implementation_owner": "implementer-1" if selected else "detector-implementer",
            "evaluation_owner": "evaluator-1" if selected else "detector-evaluator",
            "smaller_change_insufficient": "A local reminder would not bind acceptance evidence.",
            "proportionality": "Extend existing skill owners without adding a service or daemon.",
            "selection_dimensions": self.dimensions(),
        }

    def review_submission(self) -> dict[str, object]:
        hypotheses = [
            item["hypothesis_id"]
            for item in self.packet["evidence"]["report_hypotheses"]
        ]
        return {
            "schema_version": 1,
            "kind": factory_evolution.REVIEW_KIND,
            "packet_id": self.packet["packet_id"],
            "packet_root": self.packet["packet_root"],
            "reviewer_id": "semantic-reviewer-1",
            "observations": [
                {
                    "observation_id": "observation-exception",
                    "summary": "An accepted-looking path underreached the intended product.",
                    "valence": "exception",
                    "event_ids": ["EVT-000002"],
                },
                {
                    "observation_id": "observation-productive",
                    "summary": "Bounded architecture-aware review preserved capability.",
                    "valence": "productive",
                    "event_ids": ["EVT-000001", "EVT-000004"],
                },
            ],
            "lessons": [
                {
                    "lesson_id": "lesson-exception",
                    "statement": "Mechanical completion can coexist with product underreach.",
                    "observation_ids": ["observation-exception"],
                    "supporting_case_ids": ["EVT-000002"],
                    "report_hypothesis_ids": hypotheses[:1],
                    "counterexample_case_ids": ["EVT-000004"],
                    "counterexample_posture": "observed",
                    "counterexample_search": "Compared the bounded architecture-preserving resolution.",
                    "goals_advanced": [],
                    "goals_threatened": ["target-product capability"],
                    "causal_hypothesis": "Acceptance omitted an explicit product-capability comparison.",
                    "confidence": "medium",
                    "applicability": "Consequential implementation-path decisions.",
                    "unresolved_questions": ["How often does underreach recur?"],
                },
                {
                    "lesson_id": "lesson-productive",
                    "statement": "Architecture-aware bounded review can preserve intended capability.",
                    "observation_ids": ["observation-productive"],
                    "supporting_case_ids": ["EVT-000001", "EVT-000004"],
                    "report_hypothesis_ids": hypotheses[1:2],
                    "counterexample_case_ids": ["EVT-000002"],
                    "counterexample_posture": "observed",
                    "counterexample_search": "Inspected the contrary underreach incident.",
                    "goals_advanced": ["target-product capability"],
                    "goals_threatened": [],
                    "causal_hypothesis": "A visible capability comparison changes path selection.",
                    "confidence": "medium",
                    "applicability": "Consequential tracker and implementation reviews.",
                    "unresolved_questions": ["Which changes are consequential?"],
                },
            ],
            "meta_patterns": [
                {
                    "meta_pattern_id": "meta-product-alignment",
                    "statement": "Product-capability judgment is distinct from mechanical correctness.",
                    "lesson_ids": ["lesson-exception", "lesson-productive"],
                    "supporting_case_ids": ["EVT-000001", "EVT-000002", "EVT-000004"],
                    "counterexample_lesson_ids": ["lesson-productive"],
                    "applicability": "Changes with material product or architecture consequences.",
                    "uncertainty": "The evidence does not justify a general runtime control platform.",
                }
            ],
            "candidates": [
                self.candidate("candidate-skill-method", "skill-method"),
                self.candidate("candidate-detector", "detector"),
                self.candidate("candidate-tracker-method", "tracker-method"),
            ],
            "selection": {
                "candidate_id": "candidate-skill-method",
                "compared_candidate_ids": ["candidate-detector", "candidate-tracker-method"],
                "rationale": "The gap spans authoring, implementation, and closure, so a tracker-only reminder and a detector both underreach.",
                "dimensions_considered": list(factory_evolution.SELECTION_DIMENSIONS),
            },
            "experiment": {
                "experiment_id": "experiment-target-product-alignment",
                "candidate_id": "candidate-skill-method",
                "proposer_id": "proposer-1",
                "implementer_id": "implementer-1",
                "evaluator_id": "evaluator-1",
                "baseline_revision": "a" * 40,
                "candidate_revision": "b" * 40,
                "positive_case_ids": ["case-bounded-fit"],
                "exception_case_ids": ["case-overarchitecture", "case-underreach"],
                "expected_effects": ["Distinguish bounded fit, underreach, and overarchitecture without adding a platform."],
                "resource_bounds": ["Three paired cases and one independent evaluator."],
                "rollback_condition": "Revert the method if it causes lower-value architecture churn.",
                "success_measures": [
                    "The underreach case is rejected when intended capability is absent.",
                    "The overarchitecture case selects the existing-owner change without adding a service.",
                    "The bounded-fit case proceeds without generalized redesign.",
                ],
                "regression_measures": ["No bypass of canonical tracker or implementation owners."],
                "evidence_capture": "Record revision-bound evidence roots for separate baseline and candidate case results.",
                "stop_condition": "Stop after one exact-candidate disposition.",
                "comparison_mode": "improvement",
                "minimum_expected_delta": "Candidate passes all three cases while baseline misses at least one.",
                "non_inferiority_justification": "",
            },
        }

    def evaluation_submission(self, review: dict[str, object]) -> dict[str, object]:
        def result(
            case_id: str, outcome: str, evidence_id: str, revision: str
        ) -> dict[str, object]:
            value = {
                "case_id": case_id,
                "evidence_class": "observed",
                "evidence_ids": [evidence_id],
                "outcome": outcome,
                "observed_effect": f"Observed {outcome} for {case_id}.",
                "resource_cost": "One bounded review pass.",
                "regressions": [],
                "condition_revision": revision,
            }
            value["evidence_root"] = factory_evolution.experiment_result_evidence_root(
                value
            )
            return value

        return {
            "schema_version": 1,
            "kind": factory_evolution.EVALUATION_KIND,
            "packet_id": self.packet["packet_id"],
            "packet_root": self.packet["packet_root"],
            "review_id": review["review_id"],
            "review_root": review["review_root"],
            "experiment_id": "experiment-target-product-alignment",
            "candidate_id": "candidate-skill-method",
            "evaluator_id": "evaluator-1",
            "baseline_results": [
                result("case-bounded-fit", "pass", "EVT-000001", "a" * 40),
                result("case-overarchitecture", "mixed", "EVT-000002", "a" * 40),
                result("case-underreach", "fail", "EVT-000002", "a" * 40),
            ],
            "candidate_results": [
                result("case-bounded-fit", "pass", "EVT-000004", "b" * 40),
                result("case-overarchitecture", "pass", "EVT-000003", "b" * 40),
                result("case-underreach", "pass", "EVT-000003", "b" * 40),
            ],
            "contrary_evidence_ids": ["EVT-000002"],
            "regression_findings": [],
            "disposition": "promote",
            "rationale": "The candidate passed both cases with observed evidence and no regression.",
        }

    def build_review(self) -> dict[str, object]:
        return factory_evolution.build_evolution_review(
            self.packet, self.review_submission()
        )

    def refresh_result_root(self, result: dict[str, object]) -> None:
        material = {
            key: value for key, value in result.items() if key != "evidence_root"
        }
        result["evidence_root"] = factory_evolution.experiment_result_evidence_root(
            material
        )

    def test_review_can_identify_a_broad_capability_gap(self) -> None:
        review = self.build_review()

        selected = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == review["selection"]["candidate_id"]
        )
        self.assertEqual(selected["candidate_type"], "skill-method")
        self.assertEqual(
            set(selected["selection_dimensions"]),
            set(factory_evolution.SELECTION_DIMENSIONS),
        )
        self.assertNotIn("score", review["selection"])
        self.assertEqual(factory_evolution.verify_evolution_review(self.packet, review), review)

    def test_every_supported_candidate_type_is_accepted(self) -> None:
        for candidate_type in factory_evolution.CANDIDATE_TYPES:
            submission = self.review_submission()
            submission["candidates"][0]["candidate_type"] = candidate_type
            with self.subTest(candidate_type=candidate_type):
                factory_evolution.build_evolution_review(self.packet, submission)

    def test_lesson_requires_exact_cases_and_counterexample_posture(self) -> None:
        report_only = self.review_submission()
        report_only["lessons"][0]["supporting_case_ids"] = []
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "must not be empty"):
            factory_evolution.build_evolution_review(self.packet, report_only)

        missing_posture = self.review_submission()
        missing_posture["lessons"][0]["counterexample_posture"] = ""
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "posture"):
            factory_evolution.build_evolution_review(self.packet, missing_posture)

        dangling = self.review_submission()
        dangling["lessons"][0]["supporting_case_ids"] = ["EVT-999999"]
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "dangling"):
            factory_evolution.build_evolution_review(self.packet, dangling)

        contradictory = self.review_submission()
        contradictory["lessons"][0]["supporting_case_ids"] = ["EVT-000001"]
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "contradict"):
            factory_evolution.build_evolution_review(self.packet, contradictory)

        inconsistent_posture = self.review_submission()
        inconsistent_posture["lessons"][0][
            "counterexample_posture"
        ] = "searched-none-found"
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "cannot cite"):
            factory_evolution.build_evolution_review(
                self.packet, inconsistent_posture
            )

    def test_candidate_admission_requires_counterexample_evidence_or_search(self) -> None:
        submission = self.review_submission()
        submission["candidates"][0]["counterexample_case_ids"] = []

        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "requires an exact case"
        ):
            factory_evolution.build_evolution_review(self.packet, submission)

    def test_opaque_scoring_is_rejected(self) -> None:
        submission = self.review_submission()
        submission["selection"]["aggregate_score"] = 0.9

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "unexpected"):
            factory_evolution.build_evolution_review(self.packet, submission)

    def test_selected_experiment_requires_exception_rollback_and_distinct_owners(self) -> None:
        no_exception = self.review_submission()
        no_exception["experiment"]["exception_case_ids"] = []
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "must not be empty"):
            factory_evolution.build_evolution_review(self.packet, no_exception)

        no_rollback = self.review_submission()
        no_rollback["experiment"]["rollback_condition"] = ""
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "rollback"):
            factory_evolution.build_evolution_review(self.packet, no_rollback)

        self_review = self.review_submission()
        self_review["experiment"]["evaluator_id"] = "implementer-1"
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "identities collapse"):
            factory_evolution.build_evolution_review(self.packet, self_review)

    def test_evaluation_keeps_baseline_and_candidate_results_separate(self) -> None:
        review = self.build_review()
        evaluation = factory_evolution.build_candidate_evaluation(
            self.packet, review, self.evaluation_submission(review)
        )
        report = factory_evolution.build_evolution_machine_report(
            self.packet, review, evaluation
        )

        self.assertNotEqual(
            report["result_roots"]["baseline"], report["result_roots"]["candidate"]
        )
        self.assertEqual(evaluation["disposition"], "promote")
        self.assertEqual(
            factory_evolution.verify_candidate_evaluation(self.packet, review, evaluation),
            evaluation,
        )

    def test_evaluation_rejects_unsupported_or_unsafe_promotion(self) -> None:
        review = self.build_review()
        unsupported = self.evaluation_submission(review)
        unsupported["disposition"] = "auto-promote"
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "unsupported"):
            factory_evolution.build_candidate_evaluation(self.packet, review, unsupported)

        regression = self.evaluation_submission(review)
        regression["candidate_results"][0]["regressions"] = ["Lost composability."]
        self.refresh_result_root(regression["candidate_results"][0])
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "regression"):
            factory_evolution.build_candidate_evaluation(self.packet, review, regression)

        synthetic = self.evaluation_submission(review)
        for item in synthetic["baseline_results"] + synthetic["candidate_results"]:
            item["evidence_class"] = "synthetic"
            self.refresh_result_root(item)
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "alone"):
            factory_evolution.build_candidate_evaluation(self.packet, review, synthetic)

        synthetic_exception = self.evaluation_submission(review)
        synthetic_exception["candidate_results"][1]["evidence_class"] = "synthetic"
        self.refresh_result_root(synthetic_exception["candidate_results"][1])
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "alone"):
            factory_evolution.build_candidate_evaluation(
                self.packet, review, synthetic_exception
            )

        no_delta = self.evaluation_submission(review)
        for item in no_delta["baseline_results"]:
            item["outcome"] = "pass"
            self.refresh_result_root(item)
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "baseline delta"):
            factory_evolution.build_candidate_evaluation(self.packet, review, no_delta)

        stale_evidence = self.evaluation_submission(review)
        stale_evidence["candidate_results"][0]["observed_effect"] = (
            "Changed after the result root was recorded."
        )
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "root is stale"):
            factory_evolution.build_candidate_evaluation(
                self.packet, review, stale_evidence
            )

        wrong_revision = self.evaluation_submission(review)
        wrong_revision["candidate_results"][0]["condition_revision"] = "a" * 40
        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "condition revision"):
            factory_evolution.build_candidate_evaluation(
                self.packet, review, wrong_revision
            )

    def test_bundle_and_manifest_exactly_rebuild(self) -> None:
        review = self.build_review()
        evaluation = factory_evolution.build_candidate_evaluation(
            self.packet, review, self.evaluation_submission(review)
        )
        bundle = factory_evolution.build_evolution_bundle(
            self.packet, review, evaluation
        )

        self.assertEqual(factory_evolution.verify_evolution_bundle(bundle), bundle)
        rebuilt = factory_evolution.build_evolution_bundle(
            self.packet, review, evaluation
        )
        self.assertEqual(bundle, rebuilt)

        bundle["machine-report.json"]["counts"]["lessons"] = 99
        with self.assertRaises(factory_evolution.FactoryEvolutionError):
            factory_evolution.verify_evolution_bundle(bundle)

    def test_manifest_rejects_oversized_artifacts(self) -> None:
        oversized = {"payload": "x" * factory_evolution.MAX_ARTIFACT_BYTES}

        with self.assertRaisesRegex(factory_evolution.FactoryEvolutionError, "byte bound"):
            factory_evolution.build_evolution_manifest(
                {"oversized.json": oversized}
            )


if __name__ == "__main__":
    unittest.main()
