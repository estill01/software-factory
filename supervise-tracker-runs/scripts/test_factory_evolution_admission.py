#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("supervision_log.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("supervision_log", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervision_log)


class FactoryEvolutionAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.supervision_root = self.root / "supervision"
        self.repository = self.root / "factory"
        self.repository.mkdir()
        self.git("init")
        (self.repository / "factory.txt").write_text("current\n", encoding="utf-8")
        self.git("add", "factory.txt")
        self.git("-c", "user.name=Factory Test", "-c", "user.email=factory@example.test", "commit", "-m", "Initial")
        self.target_thread = "factory-target-1234"
        self.initialize()
        self.set_policy(mode="full-autonomous", target_class="software-factory")

    @property
    def directory(self) -> Path:
        return self.supervision_root / self.target_thread

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["/usr/bin/git", "-C", str(self.repository), *arguments],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()

    def command(self, values: list[str]) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.supervision_root), *values]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def initialize(self) -> None:
        self.command(
            [
                "init",
                "--target-thread",
                self.target_thread,
                "--target-label",
                "Factory target",
                "--watcher-thread",
                "watcher-1234",
                "--reviewer-thread",
                "reviewer-1234",
                "--base-reviewer-thread",
                "base-reviewer-1234",
                "--fix-executor-thread",
                "fix-executor-1234",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "direct-user-mission-1234",
                "--mission-source-sha256",
                "a" * 64,
                "--adaptive-target-repository-root",
                str(self.repository),
            ]
        )

    def set_policy(
        self,
        *,
        mode: str | None = None,
        target_class: str | None = None,
        max_admissions: int | None = None,
    ) -> None:
        values = [
            "adjust",
            "--target-thread",
            self.target_thread,
            "--reason",
            "Bind the bounded Factory evolution admission test policy.",
            "--evidence",
            "test-policy-evidence-1234",
        ]
        if mode is not None:
            values.extend(["--adaptive-decision-mode", mode])
        if target_class is not None:
            values.extend(["--adaptive-target-class", target_class])
        if max_admissions is not None:
            values.extend(
                ["--factory-evolution-max-admissions", str(max_admissions)]
            )
        self.command(values)

    def append_event(
        self,
        *,
        kind: str = "check",
        status: str = "observed",
        category: str = "productive-pattern",
        summary: str = "Bounded execution preserved the intended Factory capability.",
    ) -> str:
        current = supervision_log.events(self.directory / "events.jsonl")
        record_id = f"EVT-{len(current) + 1:06d}"
        policy = supervision_log.read_json(self.directory / "policy.json")
        productive = (
            kind in {"check", "checkpoint-review", "resolution"}
            and category in supervision_log.FACTORY_EVOLUTION_PRODUCTIVE_CATEGORIES
        )
        mission = supervision_log.bound_mission(policy)
        assert mission is not None
        record_kind = "check" if productive else kind
        record_status = "verified" if productive else status
        record_category = (
            supervision_log.OUTCOME_COMPLETION_CATEGORY if productive else category
        )
        record: dict[str, object] = {
            "schema_version": 1,
            "kind": record_kind,
            "record_id": record_id,
            "target_thread_id": self.target_thread,
            "timestamp": f"2026-08-11T12:00:{len(current):02d}+00:00",
            "status": record_status,
            "severity": "info",
            "category": record_category,
            "active_block": "Block 12",
            "checkpoint": "factory-evolution-admission",
            "summary": summary,
            "resolution": "Current canonical evidence retained.",
            "evidence": ["test-evidence-1234"],
            "policy_sha256": policy["policy_sha256"],
        }
        if productive:
            state_fingerprint = f"factory-state-{len(current):04d}"
            record.update(
                {
                    "model": supervision_log.outcome_completion_contract()[
                        "reviewer_model"
                    ],
                    "reasoning": "xhigh",
                    "state_fingerprint": state_fingerprint,
                    "mission_root": mission["mission_root"],
                    "capability_reconciliation_reviewer_id": policy["runtime"][
                        "base_reviewer_thread_id"
                    ],
                    "capability_reconciliation_implementation_owner_id": self.target_thread,
                    "capability_reconciliation_revision": self.git("rev-parse", "HEAD"),
                    "capability_reconciliation_posture": "verified",
                    "capability_reconciliation_gap_count": 0,
                }
            )
            for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS:
                record[field] = supervision_log.digest(
                    {"record_id": record_id, "field": field}
                )
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            record,
        )
        return record_id

    def write_report(
        self,
        record_ids: list[str],
        *,
        name: str,
        section: str = "resource_efficiency",
        assessment: str = "A bounded productive Factory pattern is supported.",
    ) -> Path:
        records = supervision_log.events(self.directory / "events.jsonl")
        source_root = supervision_log.digest(
            {"record_hashes": [item["record_sha256"] for item in records]}
        )
        report_id = f"weekly-{name}-{source_root[:12]}"
        report = {
            "schema_version": 1,
            "kind": "supervision-weekly-review-record",
            "report_id": report_id,
            "source_root": source_root,
            "coverage": {
                "start": "2026-08-11T12:00:00+00:00",
                "end": "2026-08-11T13:00:00+00:00",
            },
            "metrics": {
                "report_id": report_id,
                "source": {"source_root": source_root},
            },
            "cognitive_review": {
                "schema_version": 1,
                "kind": "supervision-weekly-review-cognitive-review",
                "report_id": report_id,
                "source_root": source_root,
                "headline": "Bounded Factory evidence nomination.",
                "executive_assessment": assessment,
                "overall_posture": "bounded",
                "sections": {
                    section: [
                        {
                            "title": "Bounded evidence",
                            "assessment": assessment,
                            "evidence": record_ids,
                        }
                    ]
                },
            },
        }
        report_directory = self.directory / "reports" / "weekly" / report_id
        report_directory.mkdir(parents=True, exist_ok=True)
        path = report_directory / "report.json"
        path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
        return path

    def admit(self, report: Path) -> dict[str, object]:
        return self.command(
            [
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "admit",
                "--report-json",
                str(report),
                "--events-jsonl",
                str(self.directory / "events.jsonl"),
            ]
        )

    def append_prior_admission(
        self,
        *,
        novelty_key: str,
        record_hashes: list[str],
        evolution_id: str,
        context_root: str = "b" * 64,
    ) -> str:
        current = supervision_log.events(self.directory / "events.jsonl")
        policy = supervision_log.read_json(self.directory / "policy.json")
        mission = supervision_log.bound_mission(policy)
        assert mission is not None
        record_id = f"EVT-{len(current) + 1:06d}"
        eligibility = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="explicit-factory-maintenance",
            eligible=True,
            admission_authorized=True,
            disposition="admitted",
            next_revisit_condition=(
                "the prepared packet enters its separately governed review path"
            ),
            packet_root="c" * 64,
            novelty_key=novelty_key,
            context_root=context_root,
            evolution_id=evolution_id,
            admission_record_id=record_id,
            signal_classes=["supported-productive-result"],
            canonical_record_count=len(record_hashes),
            packet_builds=1,
            prepared=True,
        )
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "schema_version": 1,
                "kind": "factory-evolution-admission",
                "record_id": record_id,
                "timestamp": f"2026-08-11T12:01:{len(current):02d}+00:00",
                "target_thread_id": self.target_thread,
                "policy_sha256": policy["policy_sha256"],
                "mission_root": mission["mission_root"],
                "checkpoint_kind": "explicit-factory-maintenance",
                "adaptive_decision_mode": "full-autonomous",
                "disposition": "admitted",
                "canonical_evidence_novelty_key": novelty_key,
                "canonical_record_sha256s": record_hashes,
                "context_root": context_root,
                "packet_root": "c" * 64,
                "evolution_id": evolution_id,
                "target_revision": self.git("rev-parse", "HEAD"),
                "eligibility_result": eligibility,
                "eligibility_result_root": eligibility["result_root"],
                "human_request_count": 0,
                "model_calls": 0,
                "reviewer_calls": 0,
            },
        )
        return record_id

    def test_supported_productive_evidence_is_admitted_once_without_cognition(self) -> None:
        first = self.append_event()
        second = self.append_event(category="owner-method-effect")
        result = self.admit(self.write_report([first, second], name="productive"))

        self.assertTrue(result["eligible"])
        self.assertTrue(result["admission_authorized"])
        self.assertEqual(result["disposition"], "admitted")
        self.assertEqual(result["packet_builds"], 1)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["reviewer_calls"], 0)
        self.assertFalse(result["candidate_started"])
        evolution = (
            self.directory
            / "learning"
            / "factory-evolution"
            / str(result["evolution_id"])
        )
        self.assertEqual(
            {item.name for item in evolution.glob("*.json")},
            {"learning-packet.json", "prepare-manifest.json"},
        )
        admissions = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind") == "factory-evolution-admission"
        ]
        self.assertEqual(len(admissions), 1)

    def test_repackaged_report_and_changed_checkpoint_are_one_novelty_no_op(self) -> None:
        first = self.append_event()
        second = self.append_event(category="economy-gain")
        initial = self.admit(self.write_report([first, second], name="initial"))
        event_count = len(supervision_log.events(self.directory / "events.jsonl"))
        repackaged = self.admit(
            self.write_report(
                [first, second],
                name="repackaged",
                assessment="The same evidence is described with different report prose.",
            )
        )
        direct_args = argparse.Namespace(
            root=str(self.supervision_root), target_thread=self.target_thread
        )
        changed_checkpoint = supervision_log.factory_evolution_checkpoint_admission(
            direct_args,
            checkpoint_kind="terminal-report-verification",
            report_paths=[self.write_report([first, second], name="terminal")],
            event_paths=[self.directory / "events.jsonl"],
        )

        self.assertEqual(
            initial["canonical_evidence_novelty_key"],
            repackaged["canonical_evidence_novelty_key"],
        )
        self.assertFalse(repackaged["eligible"])
        self.assertIn("currentness-revalidation", repackaged["disposition"])
        self.assertFalse(changed_checkpoint["eligible"])
        self.assertEqual(
            len(supervision_log.events(self.directory / "events.jsonl")),
            event_count,
        )
        self.assertEqual(
            len(list((self.directory / "learning" / "factory-evolution").iterdir())),
            1,
        )
        (self.repository / "unrelated.txt").write_text("new context\n", encoding="utf-8")
        self.git("add", "unrelated.txt")
        self.git(
            "-c",
            "user.name=Factory Test",
            "-c",
            "user.email=factory@example.test",
            "commit",
            "-m",
            "Unrelated Factory revision",
        )
        changed_revision = self.admit(
            self.write_report([first, second], name="revision")
        )
        self.assertFalse(changed_revision["eligible"])
        self.assertIn("currentness-revalidation", changed_revision["disposition"])
        self.assertEqual(
            len(supervision_log.events(self.directory / "events.jsonl")),
            event_count,
        )

    def test_fixed_mode_is_zero_producer_and_recommend_is_non_authorizing(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="mode")
        self.set_policy(mode="fixed")
        with mock.patch.object(
            supervision_log,
            "factory_evolution_module",
            side_effect=AssertionError("packet producer called"),
        ):
            fixed = self.admit(report)
        self.assertEqual(fixed["disposition"], "fixed-mode-record-only")
        self.assertEqual(fixed["packet_builds"], 0)

        self.set_policy(mode="recommend")
        recommended = self.admit(
            self.write_report([record_id], name="recommend")
        )
        self.assertTrue(recommended["eligible"])
        self.assertFalse(recommended["admission_authorized"])
        self.assertEqual(recommended["disposition"], "recommendation-only")

    def test_gap_and_productive_meta_pattern_are_both_supported(self) -> None:
        incident = self.append_event(
            kind="incident",
            status="failed",
            category="capability-gap",
            summary="Canonical Factory evidence exposes a bounded gap.",
        )
        gap_packet = self.packet_for(self.write_report([incident], name="gap"))
        gap_key, gap = self.novelty(gap_packet)
        self.assertIsNotNone(gap_key)
        self.assertIn("supported-gap", gap["coverage"]["signal_classes"])

        first = self.append_event(category="productive-pattern")
        second = self.append_event(category="capability-preserved")
        meta_packet = self.packet_for(
            self.write_report(
                [first, second], name="meta", section="recurring_patterns"
            )
        )
        meta_key, meta = self.novelty(meta_packet)
        self.assertIsNotNone(meta_key)
        self.assertIn(
            "supported-productive-meta-pattern",
            meta["coverage"]["signal_classes"],
        )

    def test_report_packaging_cannot_change_canonical_novelty(self) -> None:
        incident = self.append_event(
            kind="incident",
            status="failed",
            category="capability-gap",
        )
        unrelated = self.append_event(
            kind="notification",
            status="observed",
            category="report-context",
        )
        gap_only = self.packet_for(self.write_report([incident], name="gap-only"))
        gap_with_context = self.packet_for(
            self.write_report([incident, unrelated], name="gap-with-context")
        )
        first_key, first_projection = self.novelty(gap_only)
        second_key, second_projection = self.novelty(gap_with_context)
        self.assertEqual(first_key, second_key)
        self.assertEqual(
            first_projection["coverage"]["record_sha256s"],
            second_projection["coverage"]["record_sha256s"],
        )

        first = self.append_event(category="productive-pattern")
        second = self.append_event(category="capability-preserved")
        productive_only = self.packet_for(
            self.write_report(
                [first], name="productive-only", section="resource_efficiency"
            )
        )
        productive_with_context = self.packet_for(
            self.write_report(
                [first, unrelated],
                name="productive-with-context",
                section="resource_efficiency",
            )
        )
        productive_key, _productive_projection = self.novelty(productive_only)
        contextual_key, contextual_projection = self.novelty(
            productive_with_context
        )
        self.assertEqual(productive_key, contextual_key)
        self.assertEqual(contextual_projection["coverage"]["record_count"], 1)

        recurring = self.packet_for(
            self.write_report([first, second], name="recurring")
        )
        efficiency = self.packet_for(
            self.write_report(
                [first, second], name="efficiency", section="resource_efficiency"
            )
        )
        recurring_key, _recurring_projection = self.novelty(recurring)
        efficiency_key, _efficiency_projection = self.novelty(efficiency)
        self.assertEqual(recurring_key, efficiency_key)

    def test_reviewed_autonomous_may_admit_without_review_or_candidate_work(self) -> None:
        self.set_policy(mode="reviewed-autonomous")
        record_id = self.append_event(category="capability-preserved")
        result = self.admit(self.write_report([record_id], name="reviewed"))

        self.assertTrue(result["eligible"])
        self.assertTrue(result["admission_authorized"])
        self.assertEqual(result["disposition"], "admitted")
        self.assertEqual(result["reviewer_calls"], 0)
        self.assertFalse(result["candidate_started"])

    def test_consumed_coverage_and_resource_exhaustion_are_no_ops(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="consumed-source")
        packet = self.packet_for(report)
        novelty_key, novelty = self.novelty(packet)
        assert novelty_key is not None
        hashes = novelty["coverage"]["record_sha256s"]
        self.append_prior_admission(
            novelty_key=novelty_key,
            record_hashes=hashes,
            evolution_id="terminal-cycle-1234",
        )
        current_report = self.write_report([record_id], name="consumed-current")
        with mock.patch.object(
            supervision_log,
            "factory_evolution_cycle_inventory",
            return_value=[
                {"evolution_id": "terminal-cycle-1234", "state": "terminal"}
            ],
        ):
            consumed = self.admit(current_report)
        self.assertEqual(
            consumed["disposition"], "already-consumed-canonical-coverage"
        )
        self.assertFalse(consumed["eligible"])

        self.set_policy(max_admissions=1)
        new_record = self.append_event(category="economy-gain")
        exhausted = self.admit(
            self.write_report([new_record], name="exhausted")
        )
        self.assertEqual(
            exhausted["disposition"], "admission-resource-exhausted"
        )
        self.assertFalse(exhausted["eligible"])

    def packet_for(self, report: Path) -> dict[str, object]:
        module = supervision_log.factory_evolution_module()
        return module.build_learning_packet(
            report_paths=[report], event_paths=[self.directory / "events.jsonl"]
        )

    def novelty(
        self, packet: dict[str, object]
    ) -> tuple[str | None, dict[str, object]]:
        return supervision_log.factory_evolution_supported_novelty(
            packet,
            policy=supervision_log.read_json(self.directory / "policy.json"),
            source_events=supervision_log.events(self.directory / "events.jsonl"),
        )

    def test_report_only_theme_is_ineligible_and_writes_nothing(self) -> None:
        record_id = self.append_event(
            kind="notification",
            category="positive-theme",
            summary="Report prose praises the current Factory process.",
        )
        result = self.admit(self.write_report([record_id], name="prose"))

        self.assertFalse(result["eligible"])
        self.assertEqual(result["disposition"], "unsupported-report-nomination")
        self.assertFalse((self.directory / "learning" / "factory-evolution").exists())
        self.assertFalse(
            any(
                item.get("kind") == "factory-evolution-admission"
                for item in supervision_log.events(self.directory / "events.jsonl")
            )
        )

    def test_generic_productive_label_is_not_adjudicating_evidence(self) -> None:
        recorded = self.command(
            [
                "record",
                "--target-thread",
                self.target_thread,
                "--kind",
                "check",
                "--status",
                "observed",
                "--category",
                "productive-pattern",
                "--summary",
                "Everything looks excellent.",
            ]
        )
        record_id = str(recorded["record"]["record_id"])
        result = self.admit(
            self.write_report(
                [record_id], name="generic-positive-label", section="resource_efficiency"
            )
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["disposition"], "unsupported-report-nomination")

    def test_conflicting_active_cycle_rejects_a_distinct_novelty(self) -> None:
        first = self.append_event()
        self.admit(self.write_report([first], name="first"))
        second = self.append_event(category="economy-gain")
        result = self.admit(self.write_report([second], name="second"))

        self.assertFalse(result["eligible"])
        self.assertEqual(result["disposition"], "conflicting-active-cycle")

    def test_outside_report_path_is_rejected(self) -> None:
        record_id = self.append_event()
        canonical = self.write_report([record_id], name="contained")
        outside = self.root / "outside-report.json"
        outside.write_bytes(canonical.read_bytes())

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "outside its owner"
        ):
            self.admit(outside)

    def test_source_change_during_packet_build_is_rejected(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="currentness")
        original = supervision_log.factory_evolution_call

        def changed(module: object, name: str, *args: object, **kwargs: object) -> object:
            result = original(module, name, *args, **kwargs)
            if name == "build_learning_packet":
                report.write_bytes(report.read_bytes() + b" ")
            return result

        with mock.patch.object(
            supervision_log, "factory_evolution_call", side_effect=changed
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "admission source changed"
            ):
                self.admit(report)

    def test_source_owner_change_during_packet_build_is_rejected(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="owner-currentness")
        original = supervision_log.factory_evolution_call

        def changed(module: object, name: str, *args: object, **kwargs: object) -> object:
            result = original(module, name, *args, **kwargs)
            if name == "build_learning_packet":
                moved = self.root / "moved-weekly-report"
                report.parent.rename(moved)
                report.parent.symlink_to(moved, target_is_directory=True)
            return result

        with mock.patch.object(
            supervision_log, "factory_evolution_call", side_effect=changed
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "outside its owner|source path differs|source changed",
            ):
                self.admit(report)

    def test_interrupted_event_append_reuses_one_prepared_packet(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="interruption")
        original = supervision_log.append_raw_locked_at
        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=supervision_log.SupervisionLogError(
                "simulated append interruption"
            ),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "append interruption"
            ):
                self.admit(report)
        evolution_root = self.directory / "learning" / "factory-evolution"
        prepared = list(evolution_root.iterdir())
        self.assertEqual(len(prepared), 1)
        self.assertTrue((prepared[0] / "learning-packet.json").is_file())
        self.assertFalse(
            any(
                item.get("kind") == "factory-evolution-admission"
                for item in supervision_log.events(self.directory / "events.jsonl")
            )
        )

        with mock.patch.object(
            supervision_log, "append_raw_locked_at", wraps=original
        ):
            recovered = self.admit(report)
        self.assertTrue(recovered["eligible"])
        self.assertTrue(recovered["reused"])
        self.assertEqual(len(list(evolution_root.iterdir())), 1)
        self.assertEqual(
            sum(
                item.get("kind") == "factory-evolution-admission"
                for item in supervision_log.events(self.directory / "events.jsonl")
            ),
            1,
        )

    def test_interrupted_prepare_set_completes_from_the_exact_packet(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="prepare-interruption")
        original = supervision_log.atomic_json
        failed = False

        def interrupted(path: Path, value: object) -> None:
            nonlocal failed
            if path.name == "prepare-manifest.json" and not failed:
                failed = True
                raise supervision_log.SupervisionLogError(
                    "simulated prepare-set interruption"
                )
            original(path, value)

        with mock.patch.object(
            supervision_log, "atomic_json", side_effect=interrupted
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "prepare-set interruption"
            ):
                self.admit(report)
        evolution_root = self.directory / "learning" / "factory-evolution"
        prepared = list(evolution_root.iterdir())
        self.assertEqual(len(prepared), 1)
        self.assertTrue((prepared[0] / "learning-packet.json").is_file())
        self.assertFalse((prepared[0] / "prepare-manifest.json").exists())

        recovered = self.admit(report)
        self.assertTrue(recovered["eligible"])
        self.assertTrue(recovered["reused"])
        self.assertTrue((prepared[0] / "prepare-manifest.json").is_file())

    def test_post_append_target_change_records_currentness_rejection(self) -> None:
        record_id = self.append_event()
        report = self.write_report([record_id], name="post-append-currentness")
        current = self.git("rev-parse", "HEAD")
        with mock.patch.object(
            supervision_log,
            "factory_evolution_target_revision",
            side_effect=[
                (self.repository, current),
                (self.repository, current),
                (self.repository, "f" * 40),
            ],
        ):
            result = self.admit(report)
        self.assertFalse(result["eligible"])
        self.assertEqual(
            result["disposition"], "currentness-changed-during-admission"
        )
        phases = [
            item["kind"]
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind", "").startswith("factory-evolution-admission")
        ]
        self.assertEqual(
            phases,
            [
                "factory-evolution-admission",
                "factory-evolution-admission-currentness-rejected",
            ],
        )
        events = supervision_log.events(self.directory / "events.jsonl")
        correction = events[-1]
        self.assertEqual(
            correction["eligibility_result_root"], result["result_root"]
        )
        status = supervision_log.factory_evolution_admission_status(
            self.directory,
            supervision_log.read_json(self.directory / "policy.json"),
            events,
        )
        self.assertEqual(status["state"], "idle")
        self.assertEqual(status["active_cycles"], [])
        self.assertEqual(status["latest_admission"]["record_id"], correction["record_id"])

        next_record = self.append_event(category="economy-gain")
        next_result = self.admit(
            self.write_report([next_record], name="after-currentness-rejection")
        )
        self.assertNotEqual(next_result["disposition"], "conflicting-active-cycle")

    def test_legacy_policy_migration_is_explicit_and_bounded(self) -> None:
        policy = supervision_log.read_json(self.directory / "policy.json")
        policy.pop("factory_evolution_admission")
        self.assertTrue(
            supervision_log.ensure_factory_evolution_admission_policy(policy)
        )
        supervision_log.validate_factory_evolution_admission(
            policy["factory_evolution_admission"]
        )
        self.assertFalse(
            supervision_log.ensure_factory_evolution_admission_policy(policy)
        )

    def test_eligibility_result_rejects_non_exact_types_and_changed_summary(self) -> None:
        result = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="explicit-factory-maintenance",
            eligible=False,
            admission_authorized=False,
            disposition="unsupported-report-nomination",
            next_revisit_condition="canonical evidence changes",
        )
        for field, replacement in (
            ("schema_version", True),
            ("packet_builds", False),
            ("canonical_record_count", False),
            ("signal_classes", [1]),
            ("summary", "Changed summary."),
        ):
            changed = dict(result)
            changed[field] = replacement
            changed["result_root"] = supervision_log.digest(
                {key: value for key, value in changed.items() if key != "result_root"}
            )
            with self.assertRaises(supervision_log.SupervisionLogError):
                supervision_log.validate_factory_evolution_admission_result(changed)

        impossible = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="explicit-factory-maintenance",
            eligible=True,
            admission_authorized=True,
            disposition="admitted",
            next_revisit_condition="canonical evidence changes",
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "semantics differ"
        ):
            supervision_log.validate_factory_evolution_admission_result(impossible)

        invented = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="explicit-factory-maintenance",
            eligible=True,
            admission_authorized=True,
            disposition="invented-authoritative-state",
            next_revisit_condition="canonical evidence changes",
        )
        with self.assertRaises(supervision_log.SupervisionLogError):
            supervision_log.validate_factory_evolution_admission_result(invented)

    def test_reserved_admission_event_kind_requires_its_exact_schema(self) -> None:
        record_id = self.append_event()
        admitted = self.admit(self.write_report([record_id], name="reserved-kind"))
        policy = supervision_log.read_json(self.directory / "policy.json")
        mission = supervision_log.bound_mission(policy)
        assert mission is not None
        current = supervision_log.events(self.directory / "events.jsonl")
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "schema_version": 1,
                "kind": "factory-evolution-admission-currentness-rejected",
                "record_id": f"EVT-{len(current) + 1:06d}",
                "timestamp": "2026-08-11T12:59:00+00:00",
                "target_thread_id": self.target_thread,
                "policy_sha256": policy["policy_sha256"],
                "mission_root": mission["mission_root"],
                "supersedes_record_id": admitted["admission_record_id"],
                "evolution_id": admitted["evolution_id"],
            },
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "correction event shape differs"
        ):
            supervision_log.factory_evolution_admission_status(
                self.directory,
                policy,
                supervision_log.events(self.directory / "events.jsonl"),
            )

    def test_weekly_finalization_retains_a_non_authoritative_summary(self) -> None:
        report_id = "weekly-integration-" + "1" * 12
        report_directory = self.directory / "reports" / "weekly" / report_id
        report_directory.mkdir(parents=True)
        metrics = {
            "report_id": report_id,
            "source": {"source_root": "1" * 64},
        }
        packet = {
            "report_id": report_id,
            "source_root": "1" * 64,
            "metrics": metrics,
            "event_records": [{"record_id": "EVT-000001"}],
        }
        review = {"schema_version": 1, "kind": "test-review"}
        (report_directory / "metrics.json").write_text(
            json.dumps(metrics, sort_keys=True), encoding="utf-8"
        )
        (report_directory / "review-packet.json").write_text(
            json.dumps(packet, sort_keys=True), encoding="utf-8"
        )
        encoded = base64.b64encode(json.dumps(review).encode("utf-8")).decode(
            "ascii"
        )
        admission = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="weekly-report-finalization",
            eligible=False,
            admission_authorized=False,
            disposition="fixed-mode-record-only",
            next_revisit_condition="canonical evidence changes",
        )

        class WeeklyModule:
            class WeeklyReportError(ValueError):
                pass

            @staticmethod
            def validate_review(
                value: object, *, report_id: str, source_root: str, record_ids: set[str]
            ) -> object:
                return value

            @staticmethod
            def machine_report(metrics: object, review: object) -> dict[str, object]:
                return {
                    "schema_version": 1,
                    "kind": "supervision-weekly-review-record",
                    "report_id": report_id,
                    "source_root": "1" * 64,
                    "metrics": metrics,
                    "cognitive_review": review,
                    "coverage": {},
                }

            @staticmethod
            def markdown_report(metrics: object, review: object) -> str:
                return "# Weekly report\n"

            @staticmethod
            def atomic_write(path: Path, data: bytes) -> None:
                path.write_bytes(data)

            @staticmethod
            def render_pdf(
                path: Path,
                metrics: object,
                review: object,
                *,
                factory_evolution_eligibility: object = None,
            ) -> None:
                if factory_evolution_eligibility is None:
                    raise AssertionError("Factory-evolution eligibility is absent")
                path.write_bytes(b"%PDF-1.4\n%%EOF\n")

            @staticmethod
            def manifest_for(**paths: Path) -> dict[str, object]:
                files = {
                    path.name: {
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "bytes": path.stat().st_size,
                    }
                    for path in paths.values()
                }
                return {
                    "schema_version": 1,
                    "kind": "supervision-weekly-review-manifest",
                    "files": files,
                    "manifest_root": supervision_log.digest(files),
                }

        args = argparse.Namespace(
            root=str(self.supervision_root),
            target_thread=self.target_thread,
            report_id=report_id,
            review_base64=encoded,
        )
        output = io.StringIO()
        with (
            mock.patch.object(supervision_log, "load_policy", return_value=(self.directory, {})),
            mock.patch.object(
                supervision_log,
                "load_weekly_artifacts",
                return_value=(report_directory, metrics, packet),
            ),
            mock.patch.object(supervision_log, "weekly_report_module", return_value=WeeklyModule),
            mock.patch.object(
                supervision_log,
                "factory_evolution_checkpoint_admission",
                return_value=admission,
            ) as gate,
            redirect_stdout(output),
        ):
            supervision_log.cmd_weekly_report_finalize(args)
        result = json.loads(output.getvalue())
        self.assertEqual(
            result["factory_evolution_eligibility"]["result_root"],
            admission["result_root"],
        )
        self.assertIn(
            admission["summary"],
            (report_directory / "report.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "factory-evolution-eligibility.json",
            supervision_log.read_json(report_directory / "manifest.json")["files"],
        )
        self.assertEqual(
            gate.call_args.kwargs["checkpoint_kind"], "weekly-report-finalization"
        )

    def test_terminal_verification_invokes_only_the_bounded_checkpoint(self) -> None:
        admission = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="terminal-report-verification",
            eligible=False,
            admission_authorized=False,
            disposition="duplicate-canonical-evidence",
            next_revisit_condition="new canonical evidence appears",
        )
        args = argparse.Namespace(
            root=str(self.supervision_root),
            target_thread=self.target_thread,
            report_set_id="terminal-set-1234",
        )
        output = io.StringIO()
        with (
            mock.patch.object(supervision_log, "load_policy", return_value=(self.directory, {})),
            mock.patch.object(
                supervision_log,
                "verify_terminal_report_set",
                return_value={"valid": True, "report_set_id": args.report_set_id},
            ),
            mock.patch.object(
                supervision_log,
                "terminal_prior_report_inventory",
                return_value=[{"report_id": "weekly-prior-1234"}],
            ),
            mock.patch.object(
                supervision_log,
                "factory_evolution_checkpoint_admission",
                return_value=admission,
            ) as gate,
            redirect_stdout(output),
        ):
            supervision_log.cmd_terminal_report_verify(args)
        result = json.loads(output.getvalue())
        self.assertEqual(
            result["factory_evolution_eligibility"]["result_root"],
            admission["result_root"],
        )
        self.assertEqual(
            gate.call_args.kwargs["checkpoint_kind"],
            "terminal-report-verification",
        )

    def test_status_surfaces_current_admission_without_becoming_an_owner(self) -> None:
        policy = supervision_log.read_json(self.directory / "policy.json")
        record_id = self.append_event()
        admitted = self.admit(self.write_report([record_id], name="status"))
        projection = supervision_log.factory_evolution_admission_status(
            self.directory,
            policy,
            supervision_log.events(self.directory / "events.jsonl"),
        )
        self.assertEqual(projection["state"], "active")
        self.assertEqual(projection["active_cycles"], [admitted["evolution_id"]])
        self.assertEqual(
            projection["latest_admission"]["record_id"],
            admitted["admission_record_id"],
        )


if __name__ == "__main__":
    unittest.main()
