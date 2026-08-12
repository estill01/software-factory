from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import textwrap
import unittest
from unittest.mock import patch

from software_factory_dashboard.catalog import ProjectRecord
from software_factory_dashboard.operations import (
    AUTOMATION_TARGET_QUERY_VERSION,
    AutomationTargetQueryResult,
    DEFAULT_EVOLUTION_OWNER,
    DEFAULT_SUPERVISION_OWNER,
    DEFAULT_TERMINAL_OWNER,
    DEFAULT_WEEKLY_OWNER,
    OperationsProjectionError,
    OperationsProjectionService,
    _expected_automation_rrule,
    _expected_automation_timezone,
    _factory_evolution_comparison,
)


TARGET = "target-thread-0001"
BROKEN_TARGET = "target-thread-0002"
WATCHER = "watcher-thread-001"
REVIEWER = "reviewer-thread-01"
OLD_MISSION = "a" * 64
NEW_MISSION = "b" * 64


def owner_module():
    spec = importlib.util.spec_from_file_location("test_supervision_owner", DEFAULT_SUPERVISION_OWNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    scripts = str(DEFAULT_SUPERVISION_OWNER.parent)
    sys.path.insert(0, scripts)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class OperationsProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.supervision_root = self.root / "supervision"
        self.automations_root = self.root / "automations"
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        self.unmonitored_root = self.root / "unmonitored"
        self.unmonitored_root.mkdir()
        self.owner = owner_module()
        self._init_target(TARGET, OLD_MISSION, "direct-item-1")
        self._init_target(BROKEN_TARGET, OLD_MISSION, "direct-item-2")
        self._bind_project_and_automation()
        self._append_records()
        self._corrupt_second_target()
        self._make_incomplete_report()
        self.automation_target_ids: dict[str, tuple[str, ...]] = {
            WATCHER + TARGET[-1]: ("watcher-automation-demo",),
        }
        self.service = OperationsProjectionService(
            supervision_root=self.supervision_root,
            automations_root=self.automations_root,
            supervision_owner=DEFAULT_SUPERVISION_OWNER,
            weekly_owner=DEFAULT_WEEKLY_OWNER,
            terminal_owner=DEFAULT_TERMINAL_OWNER,
            evolution_owner=DEFAULT_EVOLUTION_OWNER,
            now=lambda: datetime(2026, 8, 9, 10, 35, tzinfo=UTC),
            automation_timezone=lambda: "America/Los_Angeles",
            automation_target_query=self._automation_target_query,
        )
        self.projects = (
            ProjectRecord(id="demo", label="Demo", root=str(self.project_root)),
            ProjectRecord(
                id="unmonitored",
                label="Unmonitored",
                root=str(self.unmonitored_root),
            ),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_factory_evolution_comparison_preserves_verified_decision_evidence(self) -> None:
        candidate = {
            "candidate_id": "candidate-selected",
            "candidate_type": "skill-method",
            "capability_gap": "The workspace omits exact comparison evidence.",
            "effect": "Expose the maintained comparison read-only.",
            "protected_capabilities": ["maintained owner"],
            "applicability": "Consequential Factory changes.",
            "tradeoffs": ["Requires independent evaluation."],
            "uncertainty": "One bounded cycle.",
        }
        rejected = {
            **candidate,
            "candidate_id": "candidate-detector",
            "candidate_type": "detector",
            "effect": "Detect the omission only.",
            "tradeoffs": ["Does not provide the operator capability."],
        }
        experiment = {
            "experiment_id": "experiment-comparison",
            "comparison_mode": "improvement",
            "positive_case_ids": ["case-positive"],
            "exception_case_ids": ["case-exception"],
            "expected_effects": ["Comparison is inspectable."],
            "resource_bounds": ["Two exact cases."],
            "rollback_condition": "Do not adopt after regression.",
            "success_measures": ["Both cases have results."],
            "regression_measures": ["No owner bypass."],
            "stop_condition": "Stop after disposition.",
            "minimum_expected_delta": "Candidate improves one case.",
            "non_inferiority_justification": "",
        }
        review = {
            "selection": {
                "candidate_id": "candidate-selected",
                "compared_candidate_ids": ["candidate-detector"],
                "rationale": "The selected path supplies the bounded capability.",
                "dimensions_considered": ["effect", "regression_risk"],
            },
            "experiment": experiment,
            "candidates": [candidate, rejected],
        }
        result = {
            "case_id": "case-positive",
            "evidence_class": "observed",
            "evidence_ids": ["EVT-000001"],
            "outcome": "pass",
            "observed_effect": "The comparison is visible.",
            "resource_cost": "One bounded case.",
            "regressions": ["One bounded regression."],
            "condition_revision": "1" * 40,
            "evidence_root": "2" * 64,
        }
        evaluation = {
            "baseline_results": [result],
            "candidate_results": [{**result, "condition_revision": "3" * 40}],
            "contrary_evidence_ids": ["EVT-000002"],
            "regression_findings": ["One bounded regression."],
            "rationale": "Keep the disposition advisory.",
        }

        plan, projected = _factory_evolution_comparison(review, evaluation)

        self.assertEqual(plan["selected_candidate"]["candidate_id"], "candidate-selected")
        self.assertEqual(
            [item["candidate_id"] for item in plan["rejected_paths"]],
            ["candidate-detector"],
        )
        self.assertEqual(projected["contrary_evidence_ids"], ["EVT-000002"])
        self.assertEqual(projected["regression_findings"], ["One bounded regression."])
        self.assertEqual(projected["baseline_results"][0]["evidence_root"], "2" * 64)
        planned, missing = _factory_evolution_comparison(review)
        self.assertEqual(planned, plan)
        self.assertIsNone(missing)

    def _automation_target_query(self, target_thread_id: str) -> AutomationTargetQueryResult:
        automation_ids = self.automation_target_ids.get(target_thread_id, ())
        return AutomationTargetQueryResult(
            version=AUTOMATION_TARGET_QUERY_VERSION,
            target_thread_id=target_thread_id,
            automation_ids=automation_ids,
            source_identity="fixture-target-query",
            source_revision="d" * 64,
            observed_at=datetime(2026, 8, 9, 10, 34, tzinfo=UTC),
            expires_at=datetime(2026, 8, 9, 10, 36, tzinfo=UTC),
            currentness=sha256(
                json.dumps(
                    [target_thread_id, list(automation_ids)],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        )

    def test_roundup_and_weekly_schedule_expectations_preserve_timezone(self) -> None:
        policy = {
            "schedule": {
                "roundup_timezone": "America/Los_Angeles",
                "roundup_local_times": ["07:00", "13:00", "17:00", "23:00"],
            },
            "reports": {
                "weekly": {
                    "enabled": True,
                    "timezone": "America/Los_Angeles",
                    "weekday": "MO",
                    "local_time": "08:00",
                }
            },
        }
        self.assertEqual(
            _expected_automation_rrule(policy, "roundup_writer"),
            "RRULE:FREQ=DAILY;BYHOUR=7,13,17,23;BYMINUTE=0;BYSECOND=0",
        )
        self.assertEqual(
            _expected_automation_rrule(policy, "weekly_report"),
            "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0;BYSECOND=0",
        )
        self.assertEqual(
            _expected_automation_timezone(policy, "roundup_writer"),
            "America/Los_Angeles",
        )
        self.assertEqual(
            _expected_automation_timezone(policy, "weekly_report"),
            "America/Los_Angeles",
        )
        policy["schedule"]["roundup_timezone"] = "Mars/Olympus"
        policy["reports"]["weekly"]["timezone"] = "Mars/Olympus"
        self.assertEqual(
            _expected_automation_timezone(policy, "roundup_writer"),
            "unavailable",
        )
        self.assertEqual(
            _expected_automation_timezone(policy, "weekly_report"),
            "unavailable",
        )

    def test_mission_successor_plan_binds_exact_source_and_fails_on_open_heads(self) -> None:
        target = "successor-target-0001"
        source_record = f"codex:{target}:turn-001:item-001"
        self._init_target(target, OLD_MISSION, "predecessor-source-001")

        planned = self.service.mission_successor_plan_snapshot(
            target,
            source_record=source_record,
            source_sha256="c" * 64,
            predecessor_disposition="superseded",
            first_eligible_work="Block 0 — successor contract",
            reason="The exact direct user source materially replaces the predecessor.",
        )
        self.assertEqual(planned["predecessor"]["mission_root"], OLD_MISSION)
        self.assertNotEqual(planned["successor"]["mission_root"], OLD_MISSION)
        self.assertEqual(
            planned["successor"]["mission_source_record"],
            source_record,
        )
        self.assertEqual(planned["expected_policy_version"], 2)
        self.assertEqual(planned["expected_evidence"], [source_record])
        self.assertEqual(planned["expected_history_kind"], "policy-mission-successor")
        self.assertEqual(planned["open_incident_ids"], [])
        self.assertEqual(planned["open_decision_ids"], [])

        with self.assertRaises(OperationsProjectionError) as completed:
            self.service.mission_successor_plan_snapshot(
                target,
                source_record=source_record,
                source_sha256="c" * 64,
                predecessor_disposition="completed",
                first_eligible_work="Block 0 — successor contract",
                reason="The exact predecessor is complete.",
            )
        self.assertEqual(
            completed.exception.code,
            "mission_successor_completion_unavailable",
        )

        directory = self.supervision_root / target
        policy = self.owner.read_json(directory / "policy.json")
        self.owner.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": "EVT-DECISION-OPEN",
                "timestamp": "2026-08-09T10:20:00+00:00",
                "target_thread_id": target,
                "kind": "decision",
                "decision_id": "DECISION-OPEN-001",
                "phase": "decision-ready",
                "policy_sha256": policy["policy_sha256"],
                "evidence": [source_record],
            },
        )
        with self.assertRaises(OperationsProjectionError) as open_head:
            self.service.mission_successor_plan_snapshot(
                target,
                source_record=source_record,
                source_sha256="c" * 64,
                predecessor_disposition="superseded",
                first_eligible_work="Block 0 — successor contract",
                reason="The exact direct user source materially replaces the predecessor.",
            )
        self.assertEqual(open_head.exception.code, "mission_successor_open_heads")

    def _command(self, *arguments: str) -> dict[str, object]:
        result = subprocess.run(
            [
                sys.executable,
                str(DEFAULT_SUPERVISION_OWNER),
                "--root",
                str(self.supervision_root),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        if result.returncode:
            raise AssertionError(payload)
        return payload

    def _init_target(self, target: str, mission: str, source_record: str) -> None:
        self._command(
            "init",
            "--target-thread",
            target,
            "--target-label",
            target,
            "--watcher-thread",
            WATCHER + target[-1],
            "--reviewer-thread",
            REVIEWER + target[-1],
            "--mission-root",
            mission,
            "--mission-source-record",
            source_record,
        )

    def _bind_project_and_automation(self) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        policy["project_root"] = str(self.project_root)
        policy["runtime"]["routine_automation_id"] = "watcher-automation-demo"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(self.owner.policy_material(policy))
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:01:00+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )
        automation = self.automations_root / "watcher-automation-demo"
        automation.mkdir(parents=True)
        (automation / "automation.toml").write_text(
            textwrap.dedent(
                f'''\
                version = 1
                id = "watcher-automation-demo"
                kind = "heartbeat"
                name = "Demo watcher"
                prompt = "PRIVATE PROMPT MUST NEVER LEAK"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=MINUTELY;INTERVAL=20"
                target_thread_id = "{WATCHER + TARGET[-1]}"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )

    def _record(
        self,
        record_id: str,
        timestamp: str,
        kind: str,
        **fields: object,
    ) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        self.owner.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": record_id,
                "timestamp": timestamp,
                "kind": kind,
                "target_thread_id": TARGET,
                "policy_sha256": policy["policy_sha256"],
                "state_fingerprint": "state-1",
                "evidence": ["source-record-1"],
                **fields,
            },
        )

    def _append_records(self) -> None:
        self._record(
            "EVT-000001",
            "2026-08-09T10:02:00+00:00",
            "check",
            model="gpt-5.6-terra",
            reasoning="max",
            status="no-intervention",
            severity="info",
            category="changed-state-review",
            summary="Predecessor check.",
            active_block="0",
        )
        self._record(
            "EVT-PRE-REVIEW",
            "2026-08-09T10:03:00+00:00",
            "meta-review",
            model="gpt-5.6-sol",
            reasoning="max",
            status="rejected",
            severity="warning",
            category="effectiveness-review",
            summary="Superseded predecessor conclusion.",
            active_block="0",
        )
        self._record(
            "EVT-PRE-INCIDENT",
            "2026-08-09T10:04:00+00:00",
            "incident",
            incident_id="INC-PREDECESSOR",
            status="detected",
            severity="high",
            category="integrity",
            summary="Predecessor-only incident.",
            active_block="0",
        )
        self._record(
            "EVT-PRE-RESOLUTION",
            "2026-08-09T10:05:00+00:00",
            "resolution",
            incident_id="INC-PREDECESSOR",
            status="corrected",
            severity="info",
            category="integrity",
            summary="Predecessor incident corrected.",
            resolution="Predecessor-only correction.",
            active_block="0",
        )
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        policy["mission_binding"] = self.owner.mission_binding_contract(
            NEW_MISSION, "direct-item-2"
        )
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(self.owner.policy_material(policy))
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:10:00+00:00",
                "kind": "policy-mission-successor",
                "policy": policy,
            },
        )
        self._record(
            "EVT-000002",
            "2026-08-09T10:11:00+00:00",
            "check",
            model="gpt-5.6-terra",
            reasoning="max",
            status="no-intervention",
            severity="info",
            category="changed-state-review",
            summary="Current mission check.",
            active_block="1",
        )
        self._record(
            "EVT-000003",
            "2026-08-09T10:12:00+00:00",
            "meta-review",
            model="gpt-5.6-sol",
            reasoning="max",
            status="accepted",
            severity="info",
            category="effectiveness-review",
            summary="Semantic conclusion.",
            active_block="1",
        )
        self._record(
            "EVT-000004",
            "2026-08-09T10:13:00+00:00",
            "incident",
            incident_id="INC-TEST-0001",
            status="detected",
            severity="high",
            category="integrity",
            summary="Current high incident.",
            active_block="1",
        )

    def _corrupt_second_target(self) -> None:
        path = self.supervision_root / BROKEN_TARGET / "events.jsonl"
        path.write_text('{"record_id":"BROKEN"}\n', encoding="utf-8")

    def _make_incomplete_report(self) -> None:
        report = (
            self.supervision_root
            / TARGET
            / "reports"
            / "weekly"
            / "weekly-incomplete-demo"
        )
        report.mkdir(parents=True)
        (report / "metrics.json").write_text("{}\n", encoding="utf-8")

    def test_projects_current_mission_topology_and_semantic_history(self) -> None:
        snapshot = self.service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)

        self.assertEqual(current["status"], "available")
        self.assertEqual(current["current_mission"]["root"], NEW_MISSION)
        self.assertEqual(current["current_event_count"], 3)
        self.assertEqual(current["predecessor_count"], 1)
        self.assertEqual(current["project_binding"]["status"], "bound")
        self.assertEqual(current["project_binding"]["project_id"], "demo")
        self.assertEqual(
            [item["project_id"] for item in snapshot["unmonitored_projects"]],
            ["unmonitored"],
        )
        self.assertEqual(current["light"]["posture"], "red")
        self.assertEqual(current["counts"]["open_incidents"], 1)
        self.assertEqual([item["kind"] for item in current["conclusions"]], ["meta-review"])
        self.assertNotIn(
            "EVT-PRE-REVIEW",
            [item["record_id"] for item in current["conclusions"]],
        )
        predecessor = next(
            segment
            for segment in current["mission_segments"]
            if segment["posture"] == "predecessor"
        )
        self.assertEqual(predecessor["open_incident_count"], 0)
        self.assertEqual(predecessor["superseded_by"], NEW_MISSION)
        self.assertGreaterEqual(predecessor["conclusion_count"], 2)
        self.assertNotIn("check", [item["kind"] for item in current["conclusions"]])
        self.assertNotIn("green", [item["to"] for item in current["operating_history"]])
        self.assertEqual(current["topology"]["roles"][0]["binding_status"], "bound")
        self.assertEqual(current["topology"]["roles"][0]["task_state"]["status"], "unavailable")
        self.assertIsNone(current["topology"]["roles"][0]["last_activity"])
        self.assertEqual(
            current["topology"]["roles"][0]["activity_attribution"]["status"],
            "unavailable",
        )
        self.assertEqual(current["conclusions"][0]["actor"]["status"], "unavailable")
        self.assertEqual(
            current["topology"]["roles"][0]["automation"]["owner_status"],
            "ACTIVE",
        )
        self.assertEqual(current["policy"]["adjustable"]["routine_minutes"], 20)
        self.assertEqual(
            current["policy"]["automation_reconciliation"][0]["state"],
            "reconciled",
        )
        self.assertEqual(
            len(current["policy"]["adjustment_contract"]["fields"]),
            9,
        )
        self.assertFalse(current["weekly_report_workflow"]["actionable"])
        self.assertEqual(
            current["weekly_report_workflow"]["error"]["code"],
            "weekly_report_writer_unavailable",
        )
        serialized = json.dumps(snapshot)
        self.assertNotIn("PRIVATE PROMPT", serialized)
        self.assertNotIn('"prompt"', serialized)

    def test_policy_control_snapshot_is_targeted_and_owner_exact(self) -> None:
        control = self.service.policy_control_snapshot(TARGET)

        self.assertEqual(control["target_thread_id"], TARGET)
        self.assertEqual(control["policy_version"], 3)
        self.assertEqual(control["policy_history_count"], 3)
        self.assertEqual(control["policy_history_head_record"]["record_id"], "POLICY-3")
        self.assertEqual(len(control["policy_history_records"]), 3)
        self.assertEqual(control["adjustable"]["routine_minutes"], 20)
        self.assertEqual(len(control["adjustment_contract"]["fields"]), 9)
        self.assertEqual(
            control["automations_by_role"]["watcher"]["manifest_sha256"],
            sha256(
                (
                    self.automations_root
                    / "watcher-automation-demo"
                    / "automation.toml"
                ).read_bytes()
            ).hexdigest(),
        )
        serialized = json.dumps(control)
        self.assertNotIn("PRIVATE PROMPT", serialized)
        self.assertNotIn('"prompt"', serialized)

    def test_paused_lifecycle_projection_and_gate_keep_terminal_permission_separate(self) -> None:
        paused = self._command(
            "record",
            "--target-thread",
            TARGET,
            "--kind",
            "lifecycle",
            "--status",
            "paused",
            "--severity",
            "info",
            "--category",
            "supervision-pause",
            "--state-fingerprint",
            "pause-state-001",
            "--dedup-key",
            "dashboard-supervision-pause:pause-state-001",
            "--evidence",
            "dashboard-preview:pause-state-001",
            "--summary",
            "Pause the exact disposable supervision group.",
        )
        record = paused["record"]
        notification = self._command(
            "record",
            "--target-thread",
            TARGET,
            "--kind",
            "notification",
            "--status",
            "sent",
            "--severity",
            "info",
            "--category",
            "gmail-lifecycle",
            "--state-fingerprint",
            "pause-state-001",
            "--dedup-key",
            f"gmail-lifecycle:{record['record_id']}",
            "--evidence",
            record["record_id"],
            "--summary",
            "Sent the exact noncritical pause notification.",
        )["record"]

        control = self.service.policy_control_snapshot(TARGET)
        self.assertEqual(control["lifecycle_status"], "paused")
        self.assertEqual(control["lifecycle_record"]["record_id"], record["record_id"])
        record_sha256 = control["lifecycle_record"]["record_sha256"]
        self.assertEqual(control["lifecycle_record_sha256"], record_sha256)
        projected_notification = control["post_lifecycle_notifications"][0]
        self.assertEqual(control["event_head"], projected_notification["record_sha256"])
        self.assertEqual(control["active_event_count"], len(control["policy_history_records"]) + 2)
        self.assertEqual(
            [item["record_id"] for item in control["post_lifecycle_notifications"]],
            [notification["record_id"]],
        )
        self.assertEqual(control["open_successor_transitions"], {})
        self.assertEqual(control["open_mission_activations"], {})

        gated = self.service.lifecycle_gate_snapshot(
            TARGET,
            lifecycle_state="paused",
            source_record=record["record_id"],
            state_fingerprint="pause-state-001",
        )
        self.assertEqual(gated["source_record_sha256"], record_sha256)
        self.assertTrue(gated["gate"]["completion_permitted"])
        self.assertTrue(gated["gate"]["source_stop_permitted"])
        self.assertFalse(gated["gate"]["send_now"])
        self.assertTrue(gated["gate"]["duplicate"])
        self.assertFalse(gated["gate"]["supervision_pause_permitted"])
        self.assertEqual(
            gated["notification_record"]["record_id"], notification["record_id"]
        )

        with self.assertRaises(OperationsProjectionError) as stale:
            self.service.lifecycle_gate_snapshot(
                TARGET,
                lifecycle_state="paused",
                source_record=record["record_id"],
                state_fingerprint="wrong-pause-state",
            )
        self.assertEqual(stale.exception.code, "lifecycle_source_mismatch")

    def test_successor_transition_gate_projection_preserves_phase_and_stop_boundary(self) -> None:
        transition_id = "TRANSITION-PROJECTION-001"
        identity = [
            "--tracker-sha256",
            "1" * 64,
            "--tracker-source-record",
            "commit:tracker-projection",
            "--requested-block-range",
            "26-31",
            "--first-eligible-block",
            "Block 26",
            "--source-mission-root",
            OLD_MISSION,
            "--governing-authority-source-class",
            "direct-user",
            "--governing-authority-source-record",
            "direct-user-item-44",
        ]

        def record(phase: str, *extra: str) -> dict[str, object]:
            return self._command(
                "successor-transition-record",
                "--target-thread",
                TARGET,
                "--transition-id",
                transition_id,
                "--phase",
                phase,
                *identity,
                *extra,
                "--state-fingerprint",
                sha256(f"state-{phase}".encode("utf-8")).hexdigest(),
                "--evidence",
                f"fixture-{phase}",
            )

        required = record("required")["record"]
        control = self.service.policy_control_snapshot(TARGET)
        self.assertEqual(
            control["successor_transitions"][transition_id]["record_id"],
            required["record_id"],
        )
        self.assertIn(transition_id, control["open_successor_transitions"])
        self.assertEqual(
            [item["phase"] for item in control["successor_transition_records"][transition_id]],
            ["required"],
        )
        gated = self.service.successor_transition_gate_snapshot(
            TARGET,
            transition_id=transition_id,
            task_creation_authority="available",
        )
        self.assertEqual(gated["gate"]["phase"], "required")
        self.assertEqual(gated["gate"]["next_action"], "create-successor-task")
        self.assertFalse(gated["gate"]["source_stop_permitted"])

        successor = ("successor-projection-001", "2" * 64, "successor-projection-001")
        created = record("successor-created", "--successor-thread", successor[0])[
            "record"
        ]
        record(
            "successor-bound",
            "--successor-thread",
            successor[0],
            "--successor-mission-root",
            successor[1],
            "--successor-group-id",
            successor[2],
        )
        record(
            "handoff-sent",
            "--successor-thread",
            successor[0],
            "--successor-mission-root",
            successor[1],
            "--successor-group-id",
            successor[2],
            "--handoff-record",
            "HANDOFF-PROJECTION-001",
        )
        record(
            "target-acknowledged",
            "--successor-thread",
            successor[0],
            "--successor-mission-root",
            successor[1],
            "--successor-group-id",
            successor[2],
            "--handoff-record",
            "HANDOFF-PROJECTION-001",
            "--acknowledgement-record",
            "ACK-PROJECTION-001",
        )
        started = record(
            "work-started",
            "--successor-thread",
            successor[0],
            "--successor-mission-root",
            successor[1],
            "--successor-group-id",
            successor[2],
            "--handoff-record",
            "HANDOFF-PROJECTION-001",
            "--acknowledgement-record",
            "ACK-PROJECTION-001",
            "--started-block",
            "Block 26",
        )["record"]
        completed = self.service.successor_transition_gate_snapshot(
            TARGET,
            transition_id=transition_id,
            task_creation_authority="available",
        )
        self.assertEqual(completed["head"]["record_id"], started["record_id"])
        self.assertTrue(completed["gate"]["source_stop_permitted"])
        self.assertFalse(completed["gate"]["transition_open"])
        records = self.service.policy_control_snapshot(TARGET)[
            "successor_transition_records"
        ][transition_id]
        self.assertEqual(len(records), 6)
        self.assertEqual(
            records[1]["state_fingerprint"], created["state_fingerprint"]
        )
        self.assertNotIn(
            transition_id,
            self.service.policy_control_snapshot(TARGET)[
                "open_successor_transitions"
            ],
        )

    def test_resume_gate_projection_validates_exact_owner_envelope_read_only(self) -> None:
        control = self.service.policy_control_snapshot(TARGET)
        mission = control["policy"]["mission_binding"]["mission_root"]
        states = {
            "watcher-automation-demo": {
                "automation_id": "watcher-automation-demo",
                "configuration_sha256": "1" * 64,
                "manifest_sha256": "2" * 64,
                "role": "watcher",
                "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                "status": "ACTIVE",
                "target_thread_id": WATCHER,
                "updated_at": 1_786_000_000_000,
            },
            "reviewer-automation-demo": {
                "automation_id": "reviewer-automation-demo",
                "configuration_sha256": "3" * 64,
                "manifest_sha256": "4" * 64,
                "role": "reviewer",
                "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                "status": "ACTIVE",
                "target_thread_id": REVIEWER,
                "updated_at": 1_786_000_001_000,
            },
        }
        payload = {
            "status": "ready",
            "eligible": True,
            "ready_to_finalize": True,
            "duplicate": False,
            "action": "resume-finalize",
            "activate_automation_ids": [],
            "automation_states": states,
            "eligibility_root": "5" * 64,
            "source_currentness_root": "6" * 64,
            "pause_record_id": "EVT-PAUSE-123",
            "source_record_id": "EVT-SOURCE-123",
            "state_fingerprint": "resume-state-123",
            "group_id": "group-" + "7" * 64,
            "mission_root": mission,
            "policy_version": control["policy_version"],
            "policy_sha256": control["policy_sha256"],
        }
        with patch.object(self.service, "_owner_command", return_value=payload) as owner:
            result = self.service.supervision_resume_gate_snapshot(
                TARGET,
                pause_record="EVT-PAUSE-123",
                source_record="EVT-SOURCE-123",
                state_fingerprint="resume-state-123",
            )

        self.assertEqual(result["gate"]["status"], "ready")
        self.assertRegex(result["currentness"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            owner.call_args.args[0],
            [
                "resume-gate",
                "--target-thread",
                TARGET,
                "--pause-record",
                "EVT-PAUSE-123",
                "--source-record",
                "EVT-SOURCE-123",
                "--state-fingerprint",
                "resume-state-123",
            ],
        )

        invalid = {**payload, "activate_automation_ids": ["watcher-automation-demo"]}
        with (
            patch.object(self.service, "_owner_command", return_value=invalid),
            self.assertRaises(OperationsProjectionError) as malformed,
        ):
            self.service.supervision_resume_gate_snapshot(
                TARGET,
                pause_record="EVT-PAUSE-123",
                source_record="EVT-SOURCE-123",
                state_fingerprint="resume-state-123",
            )
        self.assertEqual(
            malformed.exception.code,
            "supervision_resume_gate_output_invalid",
        )

    def test_mission_bind_preview_uses_ephemeral_owner_and_never_mutates_canonical_policy(self) -> None:
        missing_target = "missing-target-0003"
        source_record = f"codex:{missing_target}:turn-source-001:item-source-001"
        source_text = "Implement this exact tracker.\n"
        source_sha = sha256(source_text.encode("utf-8")).hexdigest()
        source_policy = self.owner.read_json(
            self.supervision_root / TARGET / "policy.json"
        )
        policy = json.loads(json.dumps(source_policy))
        policy["target_thread_id"] = missing_target
        policy["target_label"] = "Missing mission fixture"
        policy["policy_version"] = 1
        policy.pop("mission_binding", None)
        policy.pop("updated_at", None)
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        directory = self.supervision_root / missing_target
        directory.mkdir(parents=True)
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-1",
                "timestamp": "2026-08-09T10:02:00+00:00",
                "kind": "policy-init",
                "policy": policy,
            },
        )
        before_policy = (directory / "policy.json").read_bytes()
        before_history = (directory / "policy-history.jsonl").read_bytes()

        preview = self.service.preview_mission_bind(
            missing_target,
            source_record=source_record,
            source_sha256=source_sha,
        )
        expected = self.owner.derive_mission_binding(
            target_thread=missing_target,
            source_class="direct-user",
            source_record=source_record,
            source_sha256=source_sha,
        )
        self.assertEqual(preview["expected_mission_binding"], expected)
        self.assertEqual(preview["expected_policy_version"], 2)
        self.assertEqual(preview["expected_history_kind"], "policy-bind")
        self.assertEqual(preview["expected_history_evidence"], [])
        self.assertEqual(preview["group_ids"], [missing_target])
        project_binding = self.service.project_binding_snapshot(
            self.projects,
            missing_target,
        )
        self.assertEqual(project_binding["project_binding"]["status"], "bound")
        self.assertEqual(project_binding["project_binding"]["project_id"], "demo")
        self.assertEqual((directory / "policy.json").read_bytes(), before_policy)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(),
            before_history,
        )

        with self.assertRaises(OperationsProjectionError) as healthy:
            self.service.preview_mission_bind(
                TARGET,
                source_record=f"codex:{TARGET}:turn-source-001:item-source-001",
                source_sha256=source_sha,
            )
        self.assertEqual(healthy.exception.code, "binding_repair_not_missing")

    def test_role_bind_preview_and_apply_use_one_prior_exact_task(self) -> None:
        directory = self.supervision_root / TARGET
        candidate = "base-reviewer-prior-0001"
        policy = self.owner.read_json(directory / "policy.json")
        prior = json.loads(json.dumps(policy))
        prior["runtime"]["base_reviewer_thread_id"] = candidate
        prior["policy_version"] += 1
        prior["policy_sha256"] = self.owner.digest(self.owner.policy_material(prior))
        self.owner.atomic_json(directory / "policy.json", prior)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-ROLE-PRIOR",
                "timestamp": "2026-08-09T10:20:00+00:00",
                "kind": "policy-bind",
                "policy": prior,
            },
        )
        missing = json.loads(json.dumps(prior))
        missing["runtime"]["base_reviewer_thread_id"] = None
        missing["policy_version"] += 1
        missing["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(missing)
        )
        self.owner.atomic_json(directory / "policy.json", missing)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-ROLE-MISSING",
                "timestamp": "2026-08-09T10:21:00+00:00",
                "kind": "policy-recovery",
                "policy": missing,
            },
        )

        before_policy = (directory / "policy.json").read_bytes()
        preview = self.service.preview_role_bind(TARGET, role="base_reviewer")

        self.assertEqual(preview["candidate_task_id"], candidate)
        self.assertEqual(preview["candidate_source_records"], ["POLICY-ROLE-PRIOR"])
        self.assertEqual(preview["expected_policy_version"], missing["policy_version"] + 1)
        self.assertEqual(
            preview["expected_model"],
            {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        )
        self.assertEqual((directory / "policy.json").read_bytes(), before_policy)

        apply_arguments = {
            "role": "base_reviewer",
            "candidate_task_id": candidate,
            "prior_policy_sha256": missing["policy_sha256"],
            "prior_policy_version": missing["policy_version"],
            "prior_policy_history_head": preview["control"][
                "policy_history_head"
            ],
            "prior_policy_history_count": len(
                preview["control"]["policy_history_records"]
            ),
            "expected_owner_sha256": preview["owner_sha256"],
            "expected_normalized_policy_sha256": preview[
                "expected_normalized_policy_sha256"
            ],
        }
        with self.assertRaises(OperationsProjectionError) as stale:
            self.service.apply_role_bind(
                TARGET,
                **{
                    **apply_arguments,
                    "prior_policy_history_count": apply_arguments[
                        "prior_policy_history_count"
                    ]
                    + 1,
                },
            )
        self.assertEqual(stale.exception.code, "role_binding_source_stale")
        self.assertEqual((directory / "policy.json").read_bytes(), before_policy)

        applied = self.service.apply_role_bind(TARGET, **apply_arguments)

        current = applied["control"]
        self.assertEqual(
            current["runtime"]["base_reviewer_thread_id"],
            candidate,
        )
        self.assertEqual(current["policy_version"], preview["expected_policy_version"])
        self.assertEqual(
            current["policy_history_head_record"]["kind"],
            "policy-bind",
        )
        self.assertEqual(current["policy_history_head_record"]["evidence"], [])
        with self.assertRaises(OperationsProjectionError) as healthy:
            self.service.preview_role_bind(TARGET, role="base_reviewer")
        self.assertEqual(healthy.exception.code, "role_binding_owner_cannot_replace")

    def test_role_bind_preview_rejects_predecessor_mission_task(self) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        predecessor = json.loads(json.dumps(policy))
        predecessor["mission_binding"] = self.owner.mission_binding_contract(
            "c" * 64,
            "direct-predecessor-item",
        )
        predecessor["runtime"]["notice_reviewer_thread_id"] = (
            "predecessor-notice-reviewer-0001"
        )
        predecessor["policy_version"] += 1
        predecessor["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(predecessor)
        )
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-PREDECESSOR-NOTICE",
                "timestamp": "2026-08-09T10:20:00+00:00",
                "kind": "policy-bind",
                "policy": predecessor,
            },
        )

        successor = json.loads(json.dumps(predecessor))
        successor["mission_binding"] = self.owner.mission_binding_contract(
            "d" * 64,
            "direct-successor-item",
        )
        successor["runtime"]["notice_reviewer_thread_id"] = None
        successor["policy_version"] += 1
        successor["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(successor)
        )
        self.owner.atomic_json(directory / "policy.json", successor)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-SUCCESSOR-NOTICE-MISSING",
                "timestamp": "2026-08-09T10:21:00+00:00",
                "kind": "policy-mission-successor",
                "policy": successor,
            },
        )

        before_policy = (directory / "policy.json").read_bytes()
        with self.assertRaises(OperationsProjectionError) as unavailable:
            self.service.preview_role_bind(TARGET, role="notice_reviewer")

        self.assertEqual(
            unavailable.exception.code,
            "role_binding_task_authority_unavailable",
        )
        self.assertEqual((directory / "policy.json").read_bytes(), before_policy)

    def test_gmail_cadence_uses_active_owner_result_for_all_three_fields(self) -> None:
        self._command(
            "bind",
            "--target-thread",
            TARGET,
            "--gmail-reply-message-id",
            "gmail-seed-0001",
            "--gmail-project-key",
            "demo",
            "--gmail-subject",
            "Demo supervision",
            "--gmail-gate-thread",
            "gmail-gate-thread-0001",
            "--gmail-processor-thread",
            "gmail-processor-thread-0001",
            "--gmail-poll-automation",
            "gmail-automation-demo",
        )
        automation = self.automations_root / "gmail-automation-demo"
        automation.mkdir()
        (automation / "automation.toml").write_text(
            textwrap.dedent(
                '''\
                version = 1
                id = "gmail-automation-demo"
                kind = "heartbeat"
                name = "Demo Gmail gate"
                prompt = "PRIVATE GMAIL PROMPT MUST NEVER LEAK"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=MINUTELY;INTERVAL=1"
                target_thread_id = "gmail-gate-thread-0001"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        self.owner.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": "EVT-GMAIL-ACTIVE",
                "timestamp": datetime.now(UTC).isoformat(),
                "kind": "inbound-message",
                "target_thread_id": TARGET,
                "policy_sha256": policy["policy_sha256"],
                "state_fingerprint": "gmail-active-state",
                "status": "received",
                "severity": "info",
                "category": "gmail",
                "summary": "Current Gmail activity.",
                "evidence": ["gmail-message-id:demo"],
            },
        )

        control = self.service.policy_control_snapshot(TARGET)
        self.assertEqual(control["gmail_cadence"]["mode"], "active")
        self.assertEqual(
            control["gmail_cadence"]["desired_rrule"],
            "RRULE:FREQ=MINUTELY;INTERVAL=1",
        )
        contracts = {
            item["field"]: item["automation_role"]
            for item in control["adjustment_contract"]["fields"]
        }
        self.assertEqual(
            {
                contracts["gmail_quiet_minutes"],
                contracts["gmail_active_minutes"],
                contracts["gmail_active_window_minutes"],
            },
            {"gmail_gate"},
        )
        run = self.service.run(self.projects, TARGET)["selected_run"]
        gmail = next(
            item
            for item in run["policy"]["automation_reconciliation"]
            if item["role"] == "gmail_gate"
        )
        self.assertEqual(gmail["field"], "gmail_cadence")
        self.assertEqual(gmail["mode"], "active")
        self.assertEqual(gmail["state"], "reconciled")
        self.assertEqual(gmail["expected_rrule"], "RRULE:FREQ=MINUTELY;INTERVAL=1")

        manifest = automation / "automation.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "RRULE:FREQ=MINUTELY;INTERVAL=1",
                "RRULE:FREQ=MINUTELY;INTERVAL=2",
            ),
            encoding="utf-8",
        )
        changed = self.service.run(self.projects, TARGET)["selected_run"]
        gmail = next(
            item
            for item in changed["policy"]["automation_reconciliation"]
            if item["role"] == "gmail_gate"
        )
        self.assertEqual(gmail["state"], "partial")
        self.assertEqual(gmail["expected_rrule"], "RRULE:FREQ=MINUTELY;INTERVAL=1")

    def test_current_project_binding_ignores_predecessor_mission_paths(self) -> None:
        old_root = self.root / "old-project"
        old_root.mkdir()
        projects = (
            *self.projects,
            ProjectRecord(id="old", label="Old", root=str(old_root)),
        )
        evidence, _ = self.service._load_target(self.supervision_root / TARGET)
        predecessor = dict(evidence.events[0])
        predecessor["cwd"] = str(old_root)
        current = dict(evidence.active_events[0])
        current["cwd"] = str(self.project_root)
        events = tuple(
            predecessor if item is evidence.events[0] else item
            for item in evidence.events
        )
        active_events = tuple(
            current if item is evidence.active_events[0] else item
            for item in evidence.active_events
        )
        moved = replace(evidence, events=events, active_events=active_events)

        binding = self.service._project_binding(moved, projects)

        self.assertEqual(binding["status"], "bound")
        self.assertEqual(binding["project_id"], "demo")
        self.assertNotIn(
            str(old_root),
            [item["value"] for item in binding["evidence"]],
        )

        unbound = replace(
            moved,
            policy={
                key: value
                for key, value in moved.policy.items()
                if key != "project_root"
            },
            active_events=tuple(
                {
                    key: value
                    for key, value in item.items()
                    if key != "cwd"
                }
                for item in moved.active_events
            ),
        )
        binding = self.service._project_binding(unbound, projects)

        self.assertEqual(binding["status"], "unassigned")
        self.assertIsNone(binding["project_id"])
        self.assertEqual(binding["evidence"], [])

    def test_only_dispositive_decision_phases_are_semantic_conclusions(self) -> None:
        phases = {
            "decision-ready": False,
            "user-responded": False,
            "attempt-started": False,
            "attempt-unresolved": False,
            "resolved": True,
            "safe-deferred": True,
            "handoff-sent": False,
            "target-acknowledged": False,
        }

        for phase, expected in phases.items():
            with self.subTest(phase=phase):
                self.assertEqual(
                    self.service._is_conclusion(
                        {"kind": "decision", "phase": phase},
                        self.owner,
                    ),
                    expected,
                )

    def test_broken_chain_and_partial_report_remain_source_local(self) -> None:
        snapshot = self.service.snapshot(self.projects)
        healthy = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        broken = next(run for run in snapshot["runs"] if run["target_thread_id"] == BROKEN_TARGET)

        self.assertEqual(healthy["status"], "available")
        self.assertEqual(healthy["metrics"]["status"], "available")
        self.assertEqual(healthy["reports"][0]["status"], "unavailable")
        self.assertEqual(
            healthy["reports"][0]["error"]["code"], "report_verification_failed"
        )
        self.assertEqual(broken["status"], "unavailable")
        self.assertEqual(broken["error"]["code"], "supervision_integrity_failed")
        self.assertEqual(broken["light"]["posture"], "red")
        broken_metrics = next(
            item
            for item in snapshot["metrics"]["per_run"]
            if item["target_thread_id"] == BROKEN_TARGET
        )
        self.assertEqual(broken_metrics["status"], "unavailable")
        self.assertEqual(broken_metrics["cost_label"], "API-equivalent estimate")

    def test_metric_workspace_context_and_verified_artifact_boundary(self) -> None:
        snapshot = self.service.snapshot(self.projects)
        metric_run = next(
            item
            for item in snapshot["metrics"]["per_run"]
            if item["target_thread_id"] == TARGET
        )
        history = snapshot["metrics"]["factory_history"]

        self.assertEqual(metric_run["target_label"], TARGET)
        self.assertIsNotNone(metric_run["supervisor_group_id"])
        self.assertEqual(metric_run["project_binding"]["project_id"], "demo")
        self.assertEqual(metric_run["current_mission_root"], NEW_MISSION)
        self.assertEqual(metric_run["cost_label"], "API-equivalent estimate")
        self.assertIn("meta-review", metric_run["conclusion_counts"]["by_kind"])
        self.assertEqual(snapshot["metrics"]["aggregate"]["status"], "available")
        self.assertEqual(snapshot["metrics"]["aggregate"]["contract_count"], 1)
        self.assertEqual(history["bound_project_count"], 1)
        self.assertEqual(history["unmonitored_project_count"], 1)
        self.assertEqual(history["availability"]["status"], "available")
        self.assertFalse(history["availability"]["continuous_uptime_measured"])
        self.assertTrue(
            any("concurrent implementation" in item for item in history["unsupported"])
        )
        self.assertTrue(
            any("late or missed-check" in item for item in history["unsupported"])
        )

        report_root = (
            self.supervision_root
            / TARGET
            / "reports"
            / "weekly"
            / "weekly-verified-test"
        )
        report_root.mkdir(parents=True)
        member_path = report_root / "report.md"
        member_path.write_text("# Verified\n", encoding="utf-8")
        raw = member_path.read_bytes()
        selected = {
            "id": report_root.name,
            "target_thread_id": TARGET,
            "family": "weekly",
            "stage": "verified",
            "status": "available",
            "verification": {"valid": True},
            "members": [
                {
                    "name": member_path.name,
                    "path": str(member_path),
                    "media_type": "text/markdown",
                    "bytes": len(raw),
                    "sha256": sha256(raw).hexdigest(),
                    "read_only": True,
                }
            ],
        }

        loaded, member = self.service._read_selected_report_member(
            selected, member_name="report.md"
        )
        self.assertEqual(loaded, raw)
        self.assertEqual(member["sha256"], sha256(raw).hexdigest())

        member_path.write_text("# Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(OperationsProjectionError, "changed after verification"):
            self.service._read_selected_report_member(
                selected, member_name="report.md"
            )

        unverified = {
            **selected,
            "status": "unavailable",
            "stage": "partial",
            "verification": None,
        }
        with self.assertRaisesRegex(OperationsProjectionError, "currently verified"):
            self.service._read_selected_report_member(
                unverified, member_name="report.md"
            )

        outside_path = self.root / "outside-report.md"
        outside_path.write_text("# Outside\n", encoding="utf-8")
        outside_raw = outside_path.read_bytes()
        outside = {
            **selected,
            "members": [
                {
                    "name": "outside-report.md",
                    "path": str(outside_path),
                    "media_type": "text/markdown",
                    "bytes": len(outside_raw),
                    "sha256": sha256(outside_raw).hexdigest(),
                    "read_only": True,
                }
            ],
        }
        with self.assertRaisesRegex(OperationsProjectionError, "outside its verified bundle"):
            self.service._read_selected_report_member(
                outside, member_name="outside-report.md"
            )

    def test_weekly_report_workflow_advances_exact_stages_and_replans_changed_policy(self) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["roundup_thread_id"] = "roundup-writer-task-001"
        policy["runtime"]["base_reviewer_thread_id"] = "evolution-proposer-task-001"
        policy["notifications"]["gmail_roundup"] = {
            "enabled": True,
            "project_key": "software-factory",
            "reply_message_id": "gmail-seed-message-001",
            "subject": "Software Factory weekly supervision report",
        }
        policy["permissions"]["gmail_roundup_notification"] = True
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:14:00+00:00",
                "kind": "policy-change",
                "policy": policy,
            },
        )

        planned = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(planned["stage"], "prepare")
        self.assertEqual(planned["next_action"], "prepare")
        self.assertEqual(len(planned["stages"]), 7)
        self.assertEqual(planned["writer_task_id"], "roundup-writer-task-001")

        prepared = self._command(
            "weekly-report",
            "--target-thread",
            TARGET,
            "--action",
            "prepare",
            "--start",
            planned["coverage"]["start"],
            "--end",
            planned["coverage"]["end"],
        )
        self.assertEqual(prepared["report_id"], planned["report_id"])
        self.assertEqual(prepared["source_root"], planned["source_root"])

        awaiting_review = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(awaiting_review["stage"], "review-finalize")
        self.assertEqual(awaiting_review["next_action"], "review-finalize")
        self.assertEqual(
            [item["status"] for item in awaiting_review["stages"][:2]],
            ["complete", "complete"],
        )

        weekly = self.service._module("weekly")
        sections = {
            section: [
                {
                    "title": section.replace("_", " ").title(),
                    "assessment": (
                        "The exact supervision records support one bounded operational observation without claiming target quality."
                    ),
                    "evidence": ["EVT-000001"],
                }
            ]
            for section in weekly.REVIEW_SECTIONS
        }
        review = {
            "schema_version": 1,
            "kind": "supervision-weekly-review-cognitive-review",
            "report_id": planned["report_id"],
            "source_root": planned["source_root"],
            "reviewer_method": "bounded-full-window-cognitive-review",
            "overall_posture": "effective-with-findings",
            "headline": "Supervision retained one exact bounded finding",
            "executive_assessment": (
                "The retained source records support one bounded finding; the partial interval does not support a target-quality or causal claim."
            ),
            "sections": sections,
        }
        report_directory = Path(str(prepared["report_directory"]))
        (report_directory / "review.json").write_text(
            json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        retained_review = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(retained_review["stage"], "finalize-verify")
        self.assertEqual(retained_review["next_action"], "finalize-verify")
        retained_stages = {
            item["id"]: item["status"] for item in retained_review["stages"]
        }
        self.assertEqual(retained_stages["cognitive-review"], "complete")
        self.assertEqual(retained_stages["finalize"], "current")
        encoded_review = base64.b64encode(
            json.dumps(review, sort_keys=True).encode("utf-8")
        ).decode("ascii")
        self._command(
            "weekly-report",
            "--target-thread",
            TARGET,
            "--action",
            "finalize",
            "--report-id",
            planned["report_id"],
            "--review-base64",
            encoded_review,
        )
        verified = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(verified["stage"], "delivery", verified)
        self.assertEqual(verified["next_action"], "deliver")
        self.assertEqual(verified["delivery"]["status"], "pending")
        self.assertEqual(
            [item["status"] for item in verified["stages"][:6]],
            ["complete"] * 6,
        )

        evolution = self.service.factory_evolution_workflow_snapshot(TARGET)
        self.assertEqual(evolution["stage"], "prepare", evolution)
        self.assertEqual(evolution["next_action"], "prepare")
        self.assertEqual(evolution["source_report_id"], planned["report_id"])
        self.assertEqual(evolution["source_report_root"], planned["source_root"])
        self.assertEqual(evolution["proposer"]["task_id"], "evolution-proposer-task-001")
        self.assertEqual(
            evolution["evaluator"]["task_id"],
            policy["runtime"]["reviewer_thread_id"],
        )
        self.assertEqual(evolution["implementer"]["task_id"], None)
        self.assertIsNone(evolution["comparison_plan"])
        self.assertIsNone(evolution["comparison_results"])
        self.assertEqual(evolution["recovery"]["posture"], "available")
        self.assertIn("not performed by evolution", " ".join(evolution["limitations"]))
        self._command(
            "factory-evolution",
            "--target-thread",
            TARGET,
            "--evolution-id",
            evolution["evolution_id"],
            "--action",
            "prepare",
            "--report-json",
            str(report_directory / "report.json"),
            "--events-jsonl",
            str(directory / "events.jsonl"),
        )
        prepared_evolution = self.service.factory_evolution_workflow_snapshot(TARGET)
        self.assertEqual(prepared_evolution["stage"], "finalize", prepared_evolution)
        self.assertEqual(prepared_evolution["next_action"], "finalize")
        self.assertEqual(prepared_evolution["packet_root"], evolution["packet_root"])
        self.assertEqual(
            [stage["status"] for stage in prepared_evolution["stages"]],
            ["complete", "current", "pending", "pending", "pending"],
        )

        old_report_id = verified["report_id"]
        policy = self.owner.read_json(directory / "policy.json")
        policy["schedule"]["routine_minutes"] = 21
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:15:00+00:00",
                "kind": "policy-change",
                "policy": policy,
            },
        )
        replanned = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(replanned["stage"], "prepare")
        self.assertNotEqual(replanned["report_id"], old_report_id)
        self.assertTrue(
            (directory / "reports" / "weekly" / str(old_report_id) / "manifest.json").is_file()
        )
        bounded_directory = (
            directory / "reports" / "weekly" / str(replanned["report_id"])
        )
        bounded_directory.mkdir(parents=True)
        for index in range(17):
            (bounded_directory / f"extra-{index:02d}.txt").write_text(
                "bounded fixture\n", encoding="utf-8"
            )
        bounded = self.service.weekly_report_workflow_snapshot(
            TARGET, coverage_days=7
        )
        self.assertEqual(bounded["status"], "unavailable")
        self.assertEqual(
            bounded["error"]["code"], "report_member_limit_exceeded"
        )

    def test_terminal_report_workflow_requires_reconciled_completion_and_reuses_later_stages(self) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["base_reviewer_thread_id"] = "terminal-writer-task-001"
        policy["notifications"]["gmail"].update(
            {
                "enabled": True,
                "reply_message_id": "gmail-terminal-seed-001",
                "project_key": "demo",
                "subject": "Demo terminal report",
            }
        )
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:14:00+00:00",
                "kind": "policy-change",
                "policy": policy,
            },
        )
        state = "terminal-state-001"
        completion = {
            "schema_version": 1,
            "record_id": "EVT-TERMINAL-COMPLETION",
            "timestamp": "2026-08-09T10:15:00+00:00",
            "target_thread_id": TARGET,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": state,
            "status": "verified",
            "severity": "info",
            "category": self.owner.OUTCOME_COMPLETION_CATEGORY,
            "summary": "Observable outcome verified.",
            "evidence": ["direct-item-44"],
            "mission_root": NEW_MISSION,
            "policy_sha256": policy["policy_sha256"],
            **{
                field: "c" * 64
                for field in self.owner.OUTCOME_COMPLETION_HASH_FIELDS
            },
            "capability_reconciliation_reviewer_id": REVIEWER + TARGET[-1],
            "capability_reconciliation_implementation_owner_id": TARGET,
            "capability_reconciliation_revision": "d" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }
        lifecycle = {
            "schema_version": 1,
            "record_id": "EVT-TERMINAL-LIFECYCLE",
            "timestamp": "2026-08-09T10:16:00+00:00",
            "target_thread_id": TARGET,
            "kind": "lifecycle",
            "model": "gpt-5.6-terra",
            "reasoning": "max",
            "state_fingerprint": state,
            "status": "completed",
            "severity": "info",
            "category": "implementation-lifecycle",
            "summary": "Target completed.",
            "evidence": ["direct-item-44"],
            "outcome_completion_record_id": completion["record_id"],
            "policy_sha256": policy["policy_sha256"],
        }
        self.owner.append_raw(directory / "events.jsonl", completion)
        self.owner.append_raw(directory / "events.jsonl", lifecycle)
        incomplete = directory / "reports" / "weekly" / "weekly-incomplete-demo"
        (incomplete / "metrics.json").unlink()
        incomplete.rmdir()

        planned = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(planned["stage"], "prepare", planned)
        self.assertTrue(planned["completion"]["reconciled"])
        self.assertEqual(planned["next_action"], "prepare")
        self.assertFalse(planned["shutdown"]["permitted"])
        self.assertEqual(planned["writer_task_id"], "terminal-writer-task-001")
        self.assertEqual(planned["writer_role"], "base_reviewer")

        prepared = self._command(
            "terminal-report",
            "--target-thread",
            TARGET,
            "--action",
            "prepare",
            "--lifecycle-record",
            lifecycle["record_id"],
        )
        self.assertEqual(prepared["report_set_id"], planned["report_set_id"])
        awaiting_review = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(awaiting_review["stage"], "review-finalize")
        self.assertEqual(
            [item["status"] for item in awaiting_review["stages"][:2]],
            ["complete", "complete"],
        )

        terminal = self.service._module("terminal")
        packet_path = Path(str(prepared["review_packet_path"]))
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        known = [packet["lifecycle_record_id"]]
        prior_ids = [
            item["report_id"] for item in packet.get("prior_report_records", [])
        ]

        def report(title, start, headings):
            return {
                "title": title,
                "coverage_start": start,
                "coverage_end": packet["coverage"]["end"],
                "executive_summary": "The bounded implementation reached its verified observable outcome with explicit limitations.",
                "sections": [
                    {
                        "heading": heading,
                        "narrative": f"{heading} was reconstructed from exact completion and report evidence.",
                        "evidence": (
                            known + prior_ids
                            if title == terminal.FULL_TITLE
                            and heading == "Report synthesis"
                            else known
                        ),
                    }
                    for heading in headings
                ],
                "limitations": [
                    "This derived report grants no lifecycle or shutdown authority."
                ],
            }

        review = {
            "schema_version": 1,
            "kind": f"{terminal.REPORT_KIND}-cognitive-review",
            "report_set_id": packet["report_set_id"],
            "source_root": packet["source_root"],
            "mission_root": packet["mission_root"],
            "state_fingerprint": packet["state_fingerprint"],
            "completion_record_id": packet["completion_record_id"],
            "lifecycle_record_id": packet["lifecycle_record_id"],
            "delta_report": report(
                terminal.DELTA_TITLE,
                packet["coverage"]["delta_start"],
                terminal.DELTA_HEADINGS,
            ),
            "full_report": report(
                terminal.FULL_TITLE,
                packet["coverage"]["full_start"],
                terminal.FULL_HEADINGS,
            ),
        }
        report_directory = Path(str(prepared["report_directory"]))
        (report_directory / "review.json").write_text(
            json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        retained = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(retained["stage"], "finalize-verify")
        self.assertEqual(retained["next_action"], "finalize-verify")
        retained_stages = {
            item["id"]: item["status"] for item in retained["stages"]
        }
        self.assertEqual(retained_stages["cognitive-review"], "complete")
        self.assertEqual(retained_stages["finalize"], "current")
        self.assertFalse(retained["shutdown"]["permitted"])

        encoded = base64.b64encode(
            json.dumps(review, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        self._command(
            "terminal-report",
            "--target-thread",
            TARGET,
            "--action",
            "finalize",
            "--report-set-id",
            packet["report_set_id"],
            "--review-base64",
            encoded,
        )
        (report_directory / "manifest.json").unlink()
        partial = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(partial["stage"], "finalize-verify")
        self.assertEqual(partial["next_action"], "finalize-verify")
        self.assertTrue(any(
            "later-stage terminal bundle is partial" in item
            for item in partial["limitations"]
        ))
        self._command(
            "terminal-report",
            "--target-thread",
            TARGET,
            "--action",
            "finalize",
            "--report-set-id",
            packet["report_set_id"],
            "--review-base64",
            encoded,
        )
        verified = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(verified["stage"], "delivery")
        self.assertEqual(verified["next_action"], "deliver")
        self.assertEqual(verified["delivery"]["status"], "pending")
        self.assertTrue(all(
            item["status"] == "complete" for item in verified["stages"][:6]
        ))
        self.assertFalse(verified["shutdown"]["permitted"])
        loaded_owner = self.service._module("supervision")
        delivery_record = {
            "record_id": "EVT-TERMINAL-DELIVERY",
            "report_set_id": packet["report_set_id"],
            "gmail_message_id": "gmail-terminal-message",
            "gmail_thread_id": "gmail-terminal-thread",
            "gmail_readback_root": "e" * 64,
            "state_fingerprint": state,
            "kind": "notification",
            "category": loaded_owner.TERMINAL_REPORT_DELIVERY_CATEGORY,
            "status": "sent",
            "evidence": [lifecycle["record_id"]],
        }
        historical_delivery = {
            **delivery_record,
            "record_id": "EVT-HISTORICAL-TERMINAL-DELIVERY",
            "report_set_id": "OLD-REPORT-SET",
        }
        self.assertIsNone(
            self.service._latest_terminal_delivery_for_report_set(
                loaded_owner,
                [historical_delivery],
                lifecycle_record_id=lifecycle["record_id"],
                report_set_id=packet["report_set_id"],
            )
        )
        selected_delivery = self.service._latest_terminal_delivery_for_report_set(
            loaded_owner,
            [historical_delivery, delivery_record],
            lifecycle_record_id=lifecycle["record_id"],
            report_set_id=packet["report_set_id"],
        )
        self.assertEqual(
            selected_delivery["record_id"], "EVT-TERMINAL-DELIVERY"
        )
        with (
            patch.object(
                loaded_owner,
                "latest_terminal_delivery",
                return_value=delivery_record,
            ),
            patch.object(
                loaded_owner,
                "terminal_delivery_is_current",
                return_value=False,
            ),
        ):
            stale_delivery = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(stale_delivery["stage"], "delivery-stale")
        self.assertIsNone(stale_delivery["next_action"])
        self.assertFalse(stale_delivery["actionable"])
        self.assertFalse(stale_delivery["delivery"]["retryable"])
        self.assertEqual(
            stale_delivery["error"]["code"], "terminal_report_delivery_stale"
        )
        self.assertFalse(stale_delivery["error"]["retryable"])
        with (
            patch.object(
                loaded_owner,
                "latest_terminal_delivery",
                return_value=delivery_record,
            ),
            patch.object(
                loaded_owner,
                "terminal_delivery_is_current",
                return_value=True,
            ),
        ):
            delivered = self.service.terminal_report_workflow_snapshot(TARGET)
        self.assertEqual(delivered["stage"], "delivered")
        self.assertIsNone(delivered["next_action"])
        self.assertEqual(delivered["delivery"]["record_id"], "EVT-TERMINAL-DELIVERY")
        self.assertEqual(delivered["delivery"]["readback_root"], "e" * 64)
        self.assertFalse(delivered["shutdown"]["permitted"])

    def test_incompatible_metric_contracts_never_produce_cross_run_totals(self) -> None:
        second_target = "target-thread-0003"
        self._init_target(second_target, OLD_MISSION, "direct-item-3")
        directory = self.supervision_root / second_target
        policy = self.owner.read_json(directory / "policy.json")
        for offset, timestamp in enumerate(
            ("2026-08-09T11:00:00+00:00", "2026-08-09T11:01:00+00:00"),
            start=1,
        ):
            self.owner.append_raw(
                directory / "events.jsonl",
                {
                    "schema_version": 1,
                    "record_id": f"EVT-SECOND-{offset}",
                    "timestamp": timestamp,
                    "kind": "check",
                    "target_thread_id": second_target,
                    "policy_sha256": policy["policy_sha256"],
                    "state_fingerprint": f"state-second-{offset}",
                    "evidence": ["source-record-3"],
                    "status": "no-intervention",
                    "severity": "info",
                    "category": "changed-state-review",
                    "summary": "Independent coverage contract.",
                    "active_block": "9",
                },
            )

        snapshot = self.service.snapshot(self.projects)
        aggregate = snapshot["metrics"]["aggregate"]
        availability = snapshot["metrics"]["factory_history"]["availability"]

        self.assertEqual(aggregate["status"], "incompatible")
        self.assertEqual(aggregate["contract_count"], 2)
        self.assertIsNone(aggregate["headline"])
        self.assertIsNone(aggregate["api_equivalent_estimate"]["totals"])
        self.assertEqual(availability["status"], "incompatible")
        self.assertIsNone(availability["scheduled_active_hours"])

    def test_wholly_unavailable_metrics_never_produce_zero_aggregate(self) -> None:
        unavailable = {
            "status": "unavailable",
            "definition_owner": "supervise-tracker-runs/scripts/weekly_report.py",
            "metrics": None,
            "error": {
                "code": "metric_projection_failed",
                "message": "Exact metric unavailable.",
                "retryable": False,
            },
        }
        with patch.object(self.service, "_metrics", return_value=unavailable):
            snapshot = self.service.snapshot(self.projects)

        aggregate = snapshot["metrics"]["aggregate"]
        self.assertEqual(aggregate["status"], "unavailable")
        self.assertEqual(aggregate["contract_count"], 0)
        self.assertIsNone(aggregate["headline"])
        self.assertIsNone(aggregate["api_equivalent_estimate"]["totals"])

    def test_nested_source_symlinks_fail_locally_without_becoming_discovery(self) -> None:
        broken_policy = self.supervision_root / BROKEN_TARGET / "policy.json"
        broken_policy.unlink()
        broken_policy.symlink_to(self.supervision_root / TARGET / "policy.json")

        external_report = self.root / "external-report"
        external_report.mkdir()
        weekly_root = self.supervision_root / TARGET / "reports" / "weekly"
        (weekly_root / "weekly-linked-report").symlink_to(
            external_report,
            target_is_directory=True,
        )

        snapshot = self.service.snapshot(self.projects)
        healthy = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        broken = next(
            run for run in snapshot["runs"] if run["target_thread_id"] == BROKEN_TARGET
        )
        linked = next(report for report in healthy["reports"] if report["id"] == "weekly-linked-report")

        self.assertEqual(broken["error"]["code"], "supervision_source_symlink_rejected")
        self.assertEqual(linked["status"], "unavailable")
        self.assertEqual(linked["error"]["code"], "report_set_invalid")

    def test_cache_reuses_unchanged_sources_and_invalidates_changed_ledger(self) -> None:
        first = self.service.snapshot(self.projects)
        second = self.service.snapshot(self.projects)
        first_run = next(run for run in first["runs"] if run["target_thread_id"] == TARGET)
        second_run = next(run for run in second["runs"] if run["target_thread_id"] == TARGET)
        self.assertEqual(first_run["source"]["cache_status"], "miss")
        self.assertEqual(second_run["source"]["cache_status"], "hit")
        self.assertEqual(first_run["fingerprint"], second_run["fingerprint"])

        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "check",
            model="gpt-5.6-terra",
            reasoning="max",
            status="no-intervention",
            severity="info",
            category="changed-state-review",
            summary="New source record.",
            active_block="1",
        )
        changed = self.service.snapshot(self.projects)
        changed_run = next(run for run in changed["runs"] if run["target_thread_id"] == TARGET)
        self.assertEqual(changed_run["source"]["cache_status"], "miss")
        self.assertNotEqual(changed_run["fingerprint"], second_run["fingerprint"])

    def test_report_verification_cache_tracks_its_supervision_source_root(self) -> None:
        with patch.object(
            self.service,
            "_owner_command",
            wraps=self.service._owner_command,
        ) as owner_command:
            self.service.snapshot(self.projects)
            self.service.snapshot(self.projects)
            self.assertEqual(owner_command.call_count, 1)

            self._record(
                "EVT-000005",
                "2026-08-09T10:14:00+00:00",
                "check",
                model="gpt-5.6-terra",
                reasoning="max",
                status="no-intervention",
                severity="info",
                category="changed-state-review",
                summary="Report verification source changed.",
                active_block="1",
            )
            self.service.snapshot(self.projects)

        self.assertEqual(owner_command.call_count, 2)

    def test_loaded_owner_module_invalidates_when_exact_source_changes(self) -> None:
        owner_path = self.root / "dynamic_owner.py"
        owner_path.write_text("VALUE = 1\n", encoding="utf-8")
        service = OperationsProjectionService(
            supervision_root=self.supervision_root,
            automations_root=self.automations_root,
            supervision_owner=owner_path,
        )

        self.assertEqual(service._module("supervision").VALUE, 1)
        owner_path.write_text("VALUE = 200\n", encoding="utf-8")
        self.assertEqual(service._module("supervision").VALUE, 200)

    def test_target_change_during_projection_isolated_as_retryable(self) -> None:
        original_reports = self.service._reports
        changed = False

        def changing_reports(*args, **kwargs):
            nonlocal changed
            result = original_reports(*args, **kwargs)
            evidence = args[0]
            if evidence.target_thread_id == TARGET and not changed:
                changed = True
                self._record(
                    "EVT-000005",
                    "2026-08-09T10:14:00+00:00",
                    "check",
                    model="gpt-5.6-terra",
                    reasoning="max",
                    status="no-intervention",
                    severity="info",
                    category="changed-state-review",
                    summary="Concurrent source change.",
                    active_block="1",
                )
            return result

        with patch.object(self.service, "_reports", side_effect=changing_reports):
            snapshot = self.service.snapshot(self.projects)

        target = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        self.assertEqual(target["status"], "unavailable")
        self.assertEqual(target["error"]["code"], "supervision_changed_during_projection")
        self.assertTrue(target["error"]["retryable"])

    def test_unavailable_automation_family_does_not_hide_supervision_runs(self) -> None:
        invalid_root = self.root / "automations-not-a-directory"
        invalid_root.write_text("not a directory\n", encoding="utf-8")
        service = OperationsProjectionService(
            supervision_root=self.supervision_root,
            automations_root=invalid_root,
            supervision_owner=DEFAULT_SUPERVISION_OWNER,
            weekly_owner=DEFAULT_WEEKLY_OWNER,
            terminal_owner=DEFAULT_TERMINAL_OWNER,
            evolution_owner=DEFAULT_EVOLUTION_OWNER,
            now=lambda: datetime(2026, 8, 9, 10, 35, tzinfo=UTC),
        )

        snapshot = service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)

        self.assertEqual(current["status"], "available")
        self.assertEqual(current["topology"]["roles"][0]["binding_status"], "missing-automation")
        self.assertEqual(snapshot["orphan_automations"][0]["error"]["code"], "automation_root_invalid")
        self.assertIn("automation-manifests", snapshot["coverage"]["missing"])
        self.assertNotIn("automations", snapshot["coverage"]["observed"])

    def test_owner_status_and_dashboard_projection_match_exact_counts(self) -> None:
        owner_status = self._command("status", "--target-thread", TARGET)
        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["event_count"], owner_status["event_count"])
        self.assertEqual(
            projected["counts"]["open_incidents"],
            len(owner_status["open_incident_ids"]),
        )
        self.assertRegex(projected["source"]["revision"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            projected["metrics"]["metrics"]["resource_estimate"]["measurement_posture"],
            "estimated-from-content-minimized-records",
        )
        self.assertFalse(
            projected["metrics"]["metrics"]["resource_estimate"]["actual_provider_cost_available"]
        )

    def test_competing_attention_rules_preserve_declared_precedence(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "decision",
            decision_id="DECISION-TEST-1",
            phase="attempt-unresolved",
            safe_frontier="empty",
            status="pending",
            severity="high",
            category="decision-resolution",
            summary="Decision blocks the exact subject.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "successor-transition",
            transition_id="TRANSITION-TEST-1",
            phase="successor-created",
            status="pending",
            severity="warning",
            category="successor-continuity",
            summary="Successor transition remains incomplete.",
        )

        snapshot = self.service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        rules = [item["rule"] for item in current["light"]["facts"]]
        ranks = [
            item["rank"]
            for item in snapshot["attention"]
            if item["target_thread_id"] == TARGET
            and item["rule"] in {
                "open-high-or-critical-incident",
                "blocking-decision-empty-safe-frontier",
                "incomplete-successor-transition",
            }
        ]

        self.assertIn("open-high-or-critical-incident", rules)
        self.assertIn("blocking-decision-empty-safe-frontier", rules)
        self.assertIn("incomplete-successor-transition", rules)
        self.assertEqual(ranks, [1, 2, 3])
        self.assertEqual(current["light"]["posture"], "red")

    def test_terminal_incident_and_paused_lifecycle_are_neutral_not_green(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "resolution",
            incident_id="INC-TEST-0001",
            status="corrected",
            severity="info",
            category="integrity",
            summary="Incident was corrected.",
            resolution="Verified correction.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "lifecycle",
            status="paused",
            severity="info",
            category="target-lifecycle",
            summary="Supervision is paused.",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["counts"]["open_incidents"], 0)
        self.assertEqual(projected["light"]["posture"], "neutral")
        self.assertEqual(projected["light"]["label"], "Paused")
        paused_rules = [item["rule"] for item in projected["light"]["facts"]]
        self.assertIn("recorded-check-later-than-configured-cadence", paused_rules)
        self.assertIn("codex-task-state-unavailable", paused_rules)
        self.assertEqual(
            [item["kind"] for item in projected["conclusions"]],
            ["meta-review", "resolution"],
        )

    def test_warning_incident_is_amber_after_prior_high_incident_closes(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "resolution",
            incident_id="INC-TEST-0001",
            status="corrected",
            severity="info",
            category="integrity",
            summary="High incident was corrected.",
            resolution="Verified correction.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "incident",
            incident_id="INC-WARNING",
            status="detected",
            severity="warning",
            category="cadence",
            summary="Noncritical attention is required.",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["light"]["posture"], "amber")
        self.assertIn(
            "open-warning-incident",
            [item["rule"] for item in projected["light"]["facts"]],
        )

    def test_failed_lifecycle_is_red_after_incident_resolution(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "resolution",
            incident_id="INC-TEST-0001",
            status="corrected",
            severity="info",
            category="integrity",
            summary="Incident was corrected.",
            resolution="Verified correction.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "lifecycle",
            status="failed",
            severity="high",
            category="target-lifecycle",
            summary="Implementation failed.",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["light"]["posture"], "red")
        self.assertIn(
            "lifecycle-failed",
            [item["rule"] for item in projected["light"]["facts"]],
        )

    def test_hash_valid_but_unverified_completed_lifecycle_is_red(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "resolution",
            incident_id="INC-TEST-0001",
            status="corrected",
            severity="info",
            category="integrity",
            summary="Incident was corrected.",
            resolution="Verified correction.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "lifecycle",
            status="completed",
            severity="info",
            category="target-lifecycle",
            summary="Unverified completion claim.",
            outcome_completion_record_id="missing-completion-record",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["light"]["posture"], "red")
        self.assertIn(
            "stale-or-unverified-completion",
            [item["rule"] for item in projected["light"]["facts"]],
        )

    def test_duplicate_and_missing_automation_bindings_remain_explicit(self) -> None:
        duplicate = "duplicate-target-001"
        self._init_target(duplicate, OLD_MISSION, "direct-item-3")
        manifest = self.automations_root / "watcher-automation-demo" / "automation.toml"
        manifest.unlink()

        snapshot = self.service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        duplicate_run = next(run for run in snapshot["runs"] if run["target_thread_id"] == duplicate)
        current_watcher = current["topology"]["roles"][0]
        duplicate_watcher = duplicate_run["topology"]["roles"][0]

        self.assertEqual(current_watcher["binding_status"], "automation-unavailable")
        self.assertEqual(current_watcher["automation"]["status"], "unavailable")
        self.assertEqual(duplicate_watcher["binding_status"], "duplicate-thread")
        self.assertIn("reuses a task", " ".join(duplicate_run["topology"]["anomalies"]))

    def test_disabled_mismatched_and_orphan_automations_remain_exact(self) -> None:
        manifest = self.automations_root / "watcher-automation-demo" / "automation.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            .replace('status = "ACTIVE"', 'status = "PAUSED"')
            .replace(
                f'target_thread_id = "{WATCHER + TARGET[-1]}"',
                'target_thread_id = "different-watcher-thread"',
            ),
            encoding="utf-8",
        )
        orphan = self.automations_root / "unreferenced-automation"
        orphan.mkdir()
        (orphan / "automation.toml").write_text(
            textwrap.dedent(
                '''\
                version = 1
                id = "unreferenced-automation"
                kind = "heartbeat"
                name = "Unreferenced"
                prompt = "omitted"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=HOURLY"
                target_thread_id = "orphan-thread-0001"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )

        snapshot = self.service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)
        watcher = current["topology"]["roles"][0]

        self.assertEqual(watcher["binding_status"], "automation-target-mismatch")
        self.assertEqual(watcher["automation"]["owner_status"], "PAUSED")
        self.assertIsNone(watcher["automation"]["next_scheduled_at"])
        self.assertEqual(
            [item["id"] for item in snapshot["orphan_automations"]],
            ["unreferenced-automation"],
        )

    def test_automation_binding_snapshot_is_named_bounded_and_duplicate_safe(self) -> None:
        manifest = self.automations_root / "watcher-automation-demo" / "automation.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            .replace('status = "ACTIVE"', 'status = "PAUSED"')
            .replace(
                'rrule = "RRULE:FREQ=MINUTELY;INTERVAL=20"',
                'rrule = "RRULE:FREQ=MINUTELY;INTERVAL=45"',
            )
            .replace(
                f'target_thread_id = "{WATCHER + TARGET[-1]}"',
                'target_thread_id = "wrong-role-thread"',
            ),
            encoding="utf-8",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = ()
        self.service._target_directories = lambda: (
            self.supervision_root / TARGET,
        )
        loaded_automation_ids: list[str] = []
        load_automation = self.service._load_automation

        def load_named_only(automation_id: str):
            loaded_automation_ids.append(automation_id)
            return load_automation(automation_id)

        self.service._load_automation = load_named_only

        snapshot = self.service.automation_binding_snapshot(TARGET, "watcher")

        self.assertTrue(snapshot["repairable"])
        self.assertEqual(
            set(snapshot["mismatches"]),
            {"enabled state differs", "role target differs", "schedule differs"},
        )
        self.assertEqual(snapshot["expected"]["id"], "watcher-automation-demo")
        self.assertEqual(snapshot["expected"]["target_thread_id"], WATCHER + TARGET[-1])
        self.assertEqual(
            snapshot["expected"]["rrule"],
            "RRULE:FREQ=MINUTELY;INTERVAL=20",
        )
        self.assertEqual(
            snapshot["expected"]["timezone"],
            "not-applicable-to-interval-schedule",
        )
        self.assertRegex(snapshot["current"]["protected_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn("PRIVATE PROMPT", json.dumps(snapshot))
        self.assertEqual(len(snapshot["claims"]), 1)
        self.assertEqual(set(loaded_automation_ids), {"watcher-automation-demo"})
        self.assertEqual(snapshot["active_target_owners"]["status"], "available")

        unrelated = self.automations_root / "unrelated-broken-automation"
        unrelated.mkdir()
        (unrelated / "automation.toml").write_bytes(b"\xffunrelated owner bytes")
        loaded_automation_ids.clear()
        unrelated_broken = self.service.automation_binding_snapshot(
            TARGET,
            "watcher",
        )
        self.assertTrue(unrelated_broken["repairable"])
        self.assertEqual(
            unrelated_broken["active_target_owners"]["status"],
            "available",
        )
        self.assertEqual(set(loaded_automation_ids), {"watcher-automation-demo"})
        run = next(
            item
            for item in self.service.snapshot(self.projects)["runs"]
            if item["target_thread_id"] == TARGET
        )
        watcher_reconciliation = next(
            item
            for item in run["policy"]["automation_reconciliation"]
            if item["role"] == "watcher"
        )
        self.assertTrue(watcher_reconciliation["repairable"])
        self.assertEqual(watcher_reconciliation["duplicate_coverage"], "exact")

        related = self.automations_root / "related-broken-automation"
        related.mkdir()
        related_manifest = related / "automation.toml"
        related_manifest.write_text(
            textwrap.dedent(
                f'''\
                id = "related-broken-automation"
                status = "ACTIVE"
                target_thread_id = "{WATCHER + TARGET[-1]}"
                malformed = [
                '''
            ),
            encoding="utf-8",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = (
            "related-broken-automation",
        )
        related_broken = self.service.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(related_broken["repairable"])
        self.assertEqual(
            related_broken["active_target_owners"]["status"],
            "unavailable",
        )
        related_manifest.write_text(
            related_manifest.read_text(encoding="utf-8").replace(
                WATCHER + TARGET[-1],
                "unrelated-task-0002",
            ),
            encoding="utf-8",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = ()

        second_owner = self.automations_root / "second-watcher-owner"
        second_owner.mkdir()
        second_manifest = second_owner / "automation.toml"
        second_manifest.write_text(
            textwrap.dedent(
                f'''\
                version = 1
                id = "second-watcher-owner"
                kind = "heartbeat"
                name = "Unclaimed second watcher"
                prompt = "omitted"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=MINUTELY;INTERVAL=20"
                target_thread_id = "{WATCHER + TARGET[-1]}"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = (
            "second-watcher-owner",
        )
        second_active = self.service.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(second_active["repairable"])
        self.assertEqual(
            second_active["active_target_owners"]["conflicting_owner_ids"],
            ["second-watcher-owner"],
        )
        self.assertIn(
            "different automation already active on role target",
            second_active["mismatches"],
        )
        second_manifest.write_text(
            second_manifest.read_text(encoding="utf-8").replace(
                'status = "ACTIVE"', 'status = "PAUSED"'
            ),
            encoding="utf-8",
        )

        provider_wrong_target = self.automations_root / "provider-wrong-target"
        provider_wrong_target.mkdir()
        (provider_wrong_target / "automation.toml").write_text(
            textwrap.dedent(
                '''\
                version = 1
                id = "provider-wrong-target"
                kind = "heartbeat"
                name = "Wrong provider target"
                prompt = "omitted"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=MINUTELY;INTERVAL=20"
                target_thread_id = "unrelated-task-9999"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = (
            "provider-wrong-target",
        )
        inconsistent = self.service.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(inconsistent["repairable"])
        self.assertEqual(
            inconsistent["active_target_owners"]["target_query"]["error"]["code"],
            "automation_target_query_inconsistent",
        )
        self.automation_target_ids[WATCHER + TARGET[-1]] = ()

        duplicate = "duplicate-automation-claim"
        self._init_target(duplicate, OLD_MISSION, "direct-item-duplicate")
        directory = self.supervision_root / duplicate
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["routine_automation_id"] = "watcher-automation-demo"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(self.owner.policy_material(policy))
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:40:00+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )
        self.service._target_directories = lambda: (
            self.supervision_root / TARGET,
            directory,
        )
        duplicated = self.service.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(duplicated["repairable"])
        self.assertEqual(len(duplicated["claims"]), 2)
        self.assertIn(
            "duplicate or conflicting canonical role claim",
            duplicated["mismatches"],
        )

    def test_automation_target_query_boundary_fails_closed(self) -> None:
        manifest = self.automations_root / "watcher-automation-demo" / "automation.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                'status = "ACTIVE"', 'status = "PAUSED"'
            ),
            encoding="utf-8",
        )
        service_kwargs = {
            "supervision_root": self.supervision_root,
            "automations_root": self.automations_root,
            "supervision_owner": DEFAULT_SUPERVISION_OWNER,
            "weekly_owner": DEFAULT_WEEKLY_OWNER,
            "terminal_owner": DEFAULT_TERMINAL_OWNER,
            "evolution_owner": DEFAULT_EVOLUTION_OWNER,
            "now": lambda: datetime(2026, 8, 9, 10, 35, tzinfo=UTC),
            "automation_timezone": lambda: "America/Los_Angeles",
        }

        absent = OperationsProjectionService(**service_kwargs)
        absent._target_directories = lambda: (self.supervision_root / TARGET,)
        absent_snapshot = absent.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(absent_snapshot["repairable"])
        self.assertEqual(
            absent_snapshot["active_target_owners"]["target_query"]["error"]["code"],
            "automation_target_query_unavailable",
        )
        self.assertEqual(absent.automation_target_query_posture()["status"], "unavailable")

        fresh = self._automation_target_query(WATCHER + TARGET[-1])
        stale = OperationsProjectionService(
            **service_kwargs,
            automation_target_query=lambda _target: replace(
                fresh,
                expires_at=datetime(2026, 8, 9, 10, 35, tzinfo=UTC),
            ),
        )
        stale._target_directories = lambda: (self.supervision_root / TARGET,)
        stale_snapshot = stale.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(stale_snapshot["repairable"])
        self.assertEqual(
            stale_snapshot["active_target_owners"]["target_query"]["error"]["code"],
            "automation_target_query_stale",
        )

        ambiguous = OperationsProjectionService(
            **service_kwargs,
            automation_target_query=lambda _target: replace(
                fresh,
                automation_ids=("watcher-automation-demo", "watcher-automation-demo"),
            ),
        )
        ambiguous._target_directories = lambda: (self.supervision_root / TARGET,)
        ambiguous_snapshot = ambiguous.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(ambiguous_snapshot["repairable"])
        self.assertEqual(
            ambiguous_snapshot["active_target_owners"]["target_query"]["error"]["code"],
            "automation_target_query_invalid",
        )

        results = iter((fresh, replace(fresh, currentness="e" * 64)))
        changing = OperationsProjectionService(
            **service_kwargs,
            automation_target_query=lambda _target: next(results),
        )
        changing._target_directories = lambda: (self.supervision_root / TARGET,)
        changing_snapshot = changing.automation_binding_snapshot(TARGET, "watcher")
        self.assertFalse(changing_snapshot["repairable"])
        self.assertEqual(
            changing_snapshot["active_target_owners"]["target_query"]["error"]["code"],
            "automation_target_query_changed",
        )

    def test_duplicate_automation_binding_is_explicit(self) -> None:
        duplicate = "automation-duplicate-0009"
        self._init_target(duplicate, OLD_MISSION, "direct-item-3")
        directory = self.supervision_root / duplicate
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["routine_automation_id"] = "watcher-automation-demo"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(self.owner.policy_material(policy))
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:20:00+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )

        snapshot = self.service.snapshot(self.projects)
        current = next(run for run in snapshot["runs"] if run["target_thread_id"] == TARGET)

        self.assertEqual(
            current["topology"]["roles"][0]["binding_status"],
            "duplicate-automation",
        )
        self.assertIn(
            "bound by more than one role",
            " ".join(current["topology"]["anomalies"]),
        )

    def test_calendar_automation_repair_requires_canonical_and_owner_timezone(self) -> None:
        directory = self.supervision_root / TARGET
        self.service._target_directories = lambda: (directory,)
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["roundup_thread_id"] = "roundup-writer-task-001"
        policy["runtime"]["roundup_automation_id"] = "roundup-automation-001"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:42:00+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )
        automation = self.automations_root / "roundup-automation-001"
        automation.mkdir()
        (automation / "automation.toml").write_text(
            textwrap.dedent(
                '''\
                version = 1
                id = "roundup-automation-001"
                kind = "heartbeat"
                name = "Roundup writer"
                prompt = "omitted"
                status = "PAUSED"
                rrule = "RRULE:FREQ=DAILY;BYHOUR=7,13,17,23;BYMINUTE=0;BYSECOND=0"
                target_thread_id = "roundup-writer-task-001"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )
        self.automation_target_ids["roundup-writer-task-001"] = (
            "roundup-automation-001",
        )

        exact = self.service.automation_binding_snapshot(TARGET, "roundup_writer")
        self.assertTrue(exact["repairable"])
        self.assertEqual(exact["current"]["timezone"], "America/Los_Angeles")

        policy = self.owner.read_json(directory / "policy.json")
        policy["notifications"]["gmail_roundup"].update(
            {
                "enabled": True,
                "project_key": "software-factory",
                "reply_message_id": "gmail-message-001",
                "subject": "Software Factory roundup",
            }
        )
        policy["permissions"]["gmail_roundup_notification"] = True
        policy["reports"]["weekly"]["enabled"] = True
        policy["reports"]["weekly"]["automation_id"] = "weekly-report-automation-001"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:42:30+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )
        roundup_manifest = automation / "automation.toml"
        roundup_manifest.write_text(
            roundup_manifest.read_text(encoding="utf-8").replace(
                'status = "PAUSED"', 'status = "ACTIVE"'
            ),
            encoding="utf-8",
        )
        weekly = self.automations_root / "weekly-report-automation-001"
        weekly.mkdir()
        (weekly / "automation.toml").write_text(
            textwrap.dedent(
                '''\
                version = 1
                id = "weekly-report-automation-001"
                kind = "heartbeat"
                name = "Weekly report"
                prompt = "omitted"
                status = "ACTIVE"
                rrule = "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0;BYSECOND=0"
                target_thread_id = "roundup-writer-task-001"
                created_at = 1786270800000
                updated_at = 1786271400000
                '''
            ),
            encoding="utf-8",
        )
        self.automation_target_ids["roundup-writer-task-001"] = (
            "roundup-automation-001",
            "weekly-report-automation-001",
        )
        distinct_sibling = self.service.automation_binding_snapshot(
            TARGET,
            "roundup_writer",
        )
        self.assertEqual(distinct_sibling["mismatches"], [])
        self.assertEqual(
            {
                owner["relation"]
                for owner in distinct_sibling["active_target_owners"]["owners"]
            },
            {"selected-role", "distinct-canonical-role"},
        )

        self.service._automation_timezone = lambda: "UTC"
        wrong_owner_timezone = self.service.automation_binding_snapshot(
            TARGET,
            "roundup_writer",
        )
        self.assertFalse(wrong_owner_timezone["repairable"])
        self.assertIn(
            "automation owner timezone differs",
            wrong_owner_timezone["mismatches"],
        )

        self.service._automation_timezone = lambda: "America/Los_Angeles"
        policy = self.owner.read_json(directory / "policy.json")
        policy["schedule"]["roundup_timezone"] = "Mars/Olympus"
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-09T10:43:00+00:00",
                "kind": "policy-change",
                "policy": policy,
            },
        )
        invalid_policy_timezone = self.service.automation_binding_snapshot(
            TARGET,
            "roundup_writer",
        )
        self.assertFalse(invalid_policy_timezone["repairable"])
        self.assertIn(
            "canonical timezone unavailable",
            invalid_policy_timezone["mismatches"],
        )

    def test_configured_auxiliary_without_automation_id_stays_visible(self) -> None:
        directory = self.supervision_root / TARGET
        policy = self.owner.read_json(directory / "policy.json")
        policy["runtime"]["roundup_thread_id"] = "roundup-writer-missing-owner"
        policy["runtime"]["roundup_automation_id"] = None
        policy["policy_version"] += 1
        policy["policy_sha256"] = self.owner.digest(
            self.owner.policy_material(policy)
        )
        self.owner.atomic_json(directory / "policy.json", policy)
        self.owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": f"POLICY-{policy['policy_version']}",
                "timestamp": "2026-08-11T09:10:00+00:00",
                "kind": "policy-bind",
                "policy": policy,
            },
        )

        run = self.service.run(self.projects, TARGET)["selected_run"]
        roundup = next(
            item
            for item in run["policy"]["automation_reconciliation"]
            if item["role"] == "roundup_writer"
        )
        self.assertIsNone(roundup["automation_id"])
        self.assertEqual(roundup["state"], "unavailable")
        self.assertIn("binding", roundup["reason"])

    def test_terminal_decision_and_successor_heads_close_without_erasing_history(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "decision",
            decision_id="DECISION-CLOSED",
            phase="attempt-unresolved",
            safe_frontier="nonempty",
            status="pending",
            severity="warning",
            category="decision-resolution",
            summary="Decision opened.",
        )
        self._record(
            "EVT-000006",
            "2026-08-09T10:15:00+00:00",
            "decision",
            decision_id="DECISION-CLOSED",
            phase="target-acknowledged",
            safe_frontier="nonempty",
            status="resolved",
            severity="info",
            category="decision-resolution",
            summary="Decision closed.",
        )
        self._record(
            "EVT-000007",
            "2026-08-09T10:16:00+00:00",
            "successor-transition",
            transition_id="TRANSITION-CLOSED",
            phase="successor-created",
            status="pending",
            severity="warning",
            category="successor-continuity",
            summary="Successor opened.",
        )
        self._record(
            "EVT-000008",
            "2026-08-09T10:17:00+00:00",
            "successor-transition",
            transition_id="TRANSITION-CLOSED",
            phase="work-started",
            status="accepted",
            severity="info",
            category="successor-continuity",
            summary="Successor started.",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["counts"]["open_decisions"], 0)
        self.assertEqual(projected["counts"]["open_successor_transitions"], 0)
        self.assertEqual(projected["decisions"][0]["phase"], "target-acknowledged")
        self.assertEqual(projected["successor_transitions"][0]["phase"], "work-started")
        self.assertIn(
            "TRANSITION-CLOSED",
            [item["transition_id"] for item in projected["timeline"]],
        )

    def test_unknown_event_kind_is_timeline_only_not_a_semantic_conclusion(self) -> None:
        self._record(
            "EVT-000005",
            "2026-08-09T10:14:00+00:00",
            "future-owner-kind",
            status="observed",
            severity="info",
            category="future",
            summary="Unknown future record kind.",
        )

        projected = self.service.run(self.projects, TARGET)["selected_run"]

        self.assertEqual(projected["timeline"][-1]["kind"], "future-owner-kind")
        self.assertNotIn(
            "future-owner-kind",
            [item["kind"] for item in projected["conclusions"]],
        )


if __name__ == "__main__":
    unittest.main()
