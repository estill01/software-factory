from __future__ import annotations

from datetime import UTC, datetime
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
    DEFAULT_EVOLUTION_OWNER,
    DEFAULT_SUPERVISION_OWNER,
    DEFAULT_TERMINAL_OWNER,
    DEFAULT_WEEKLY_OWNER,
    OperationsProjectionService,
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
        self.service = OperationsProjectionService(
            supervision_root=self.supervision_root,
            automations_root=self.automations_root,
            supervision_owner=DEFAULT_SUPERVISION_OWNER,
            weekly_owner=DEFAULT_WEEKLY_OWNER,
            terminal_owner=DEFAULT_TERMINAL_OWNER,
            evolution_owner=DEFAULT_EVOLUTION_OWNER,
            now=lambda: datetime(2026, 8, 9, 10, 35, tzinfo=UTC),
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
        serialized = json.dumps(snapshot)
        self.assertNotIn("PRIVATE PROMPT", serialized)
        self.assertNotIn('"prompt"', serialized)

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
