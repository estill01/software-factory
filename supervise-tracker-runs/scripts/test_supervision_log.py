#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


HELPER_PATH = Path(__file__).with_name("supervision_log.py")
SPEC = importlib.util.spec_from_file_location("supervision_log", HELPER_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervision_log)


class NoticeGateCorrelationTests(unittest.TestCase):
    incident_id = "INC-20260801-123456-ABCDEF"
    alert_source = "EVT-000001"
    terminal_source = "EVT-000002"

    def run_terminal_gate(self, event_records: list[dict[str, object]]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            incidents = directory / "incidents"
            incidents.mkdir()
            (incidents / f"{self.incident_id}.md").write_text(
                "# Test incident\n", encoding="utf-8"
            )
            args = argparse.Namespace(
                incident_id=self.incident_id,
                source_record=self.terminal_source,
                notice_disposition="terminal",
                resolution_owner="none",
                user_action_required="no",
                severity="info",
            )
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(directory, {"policy_sha256": "test-policy"}),
                ),
                mock.patch.object(
                    supervision_log, "events", return_value=event_records
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_notice_gate(args)
            return json.loads(output.getvalue())

    def incident_records(self) -> list[dict[str, object]]:
        return [
            {
                "kind": "steer",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
            },
        ]

    def test_linked_sent_primary_notification_makes_terminal_eligible(self) -> None:
        records = self.incident_records()
        records.append(
            {
                "kind": "notification",
                "record_id": "EVT-000003",
                "category": "gmail",
                "status": "sent",
                "evidence": [self.alert_source, "gmail-message-id"],
            }
        )

        result = self.run_terminal_gate(records)

        self.assertTrue(result["previously_alerted"])
        self.assertTrue(result["send_now"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["channel"], "primary-outcome")
        self.assertEqual(result["banner"], "SUPERVISION OUTCOME")

    def test_linked_terminal_receipt_suppresses_duplicate(self) -> None:
        records = self.incident_records()
        records.extend(
            [
                {
                    "kind": "notification",
                    "record_id": "EVT-000003",
                    "category": "gmail",
                    "status": "sent",
                    "evidence": [self.alert_source, "gmail-alert-id"],
                },
                {
                    "kind": "notification",
                    "record_id": "EVT-000004",
                    "category": "gmail",
                    "status": "sent",
                    "dedup_key": f"gmail:{self.terminal_source}",
                    "evidence": [self.terminal_source, "gmail-outcome-id"],
                },
            ]
        )

        result = self.run_terminal_gate(records)

        self.assertTrue(result["previously_alerted"])
        self.assertTrue(result["duplicate"])
        self.assertFalse(result["send_now"])
        self.assertEqual(result["channel"], "none")
        self.assertIsNone(result["banner"])

    def test_unalerted_terminal_stays_digest_only(self) -> None:
        records = self.incident_records()
        records.extend(
            [
                {
                    "kind": "notification",
                    "record_id": "EVT-000003",
                    "category": "gmail",
                    "status": "failed",
                    "evidence": [self.alert_source],
                },
                {
                    "kind": "notification",
                    "record_id": "EVT-000004",
                    "category": "gmail-roundup",
                    "status": "sent",
                    "evidence": [self.alert_source],
                },
            ]
        )

        result = self.run_terminal_gate(records)

        self.assertFalse(result["previously_alerted"])
        self.assertFalse(result["send_now"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["channel"], "digest")
        self.assertIsNone(result["banner"])

    def test_direct_incident_id_matching_is_preserved(self) -> None:
        records = self.incident_records()
        records.append(
            {
                "kind": "notification",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "legacy",
                "status": "legacy",
                "evidence": [],
            }
        )

        result = self.run_terminal_gate(records)

        self.assertTrue(result["previously_alerted"])
        self.assertTrue(result["send_now"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["banner"], "SUPERVISION OUTCOME")


class ExecutionEconomyPolicyTests(unittest.TestCase):
    def init_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            target_thread="target-1234",
            target_label="target",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread=None,
            fix_executor_thread="fixer-1234",
        )

    def test_default_policy_detects_economy_but_cannot_edit_other_skills(self) -> None:
        policy = supervision_log.default_policy(self.init_args())

        self.assertTrue(policy["execution_economy"]["enabled"])
        self.assertEqual(policy["skill_maintenance"]["mode"], "propose-only")
        self.assertFalse(policy["permissions"]["allowlisted_skill_maintenance"])
        self.assertEqual(
            policy["skill_maintenance"]["allowlist"],
            supervision_log.ALLOWLISTED_MAINTENANCE_SKILLS,
        )
        self.assertFalse(policy["notifications"]["gmail_priority"]["enabled"])
        self.assertEqual(
            policy["notifications"]["gmail_priority"]["lifecycle_states"],
            ["blocked", "failed", "stopped"],
        )
        self.assertEqual(
            policy["notifications"]["gmail"]["lifecycle_immediate_states"],
            ["completed", "paused"],
        )

    def test_adjust_enables_only_the_exact_reviewed_skill_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            args = argparse.Namespace(
                target_thread="target-1234",
                routine_minutes=None,
                meta_review_hours=None,
                max_sample_denominator=None,
                cooldown_minutes=None,
                max_escalations_per_hour=None,
                gmail_quiet_minutes=None,
                gmail_active_minutes=None,
                gmail_active_window_minutes=None,
                skill_maintenance_mode=(
                    "apply-allowlisted-skill-maintenance-with-review"
                ),
                reason="Operator authorized reviewed allowlisted skill maintenance.",
                evidence=["user-directive"],
            )
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log, "load_policy", return_value=(directory, policy)
                ),
                mock.patch.object(supervision_log, "atomic_json"),
                mock.patch.object(supervision_log, "append_raw"),
                redirect_stdout(output),
            ):
                supervision_log.cmd_adjust(args)

            result = json.loads(output.getvalue())
            adjusted = result["policy"]
            self.assertTrue(
                adjusted["permissions"]["allowlisted_skill_maintenance"]
            )
            self.assertEqual(
                adjusted["skill_maintenance"]["allowlist"],
                supervision_log.ALLOWLISTED_MAINTENANCE_SKILLS,
            )
            self.assertTrue(adjusted["skill_maintenance"]["deprojectize_required"])
            self.assertTrue(
                adjusted["skill_maintenance"]["independent_review_required"]
            )

    def test_bind_backfills_legacy_group_in_propose_only_mode(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy.pop("execution_economy")
        policy.pop("decision_resolution")
        policy.pop("skill_maintenance")
        policy["permissions"].pop("allowlisted_skill_maintenance")
        policy["permissions"].pop("gmail_priority_notification")
        policy["notifications"].pop("gmail_priority")
        args = supervision_log.parser().parse_args(
            ["bind", "--target-thread", "target-1234"]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(output),
        ):
            supervision_log.cmd_bind(args)

        self.assertTrue(json.loads(output.getvalue())["changed"])
        self.assertEqual(policy["skill_maintenance"]["mode"], "propose-only")
        self.assertTrue(policy["execution_economy"]["enabled"])
        self.assertTrue(policy["decision_resolution"]["continuation_first"])
        self.assertFalse(policy["permissions"]["allowlisted_skill_maintenance"])
        self.assertFalse(policy["permissions"]["gmail_priority_notification"])
        self.assertFalse(policy["notifications"]["gmail_priority"]["enabled"])
        write.assert_called_once()

    def test_skill_maintenance_mode_change_requires_evidence(self) -> None:
        cases = (
            ("propose-only", "apply-allowlisted-skill-maintenance-with-review", []),
            (
                "apply-allowlisted-skill-maintenance-with-review",
                "propose-only",
                ["--evidence", "   "],
            ),
        )
        for current_mode, requested_mode, evidence_args in cases:
            with self.subTest(
                current_mode=current_mode, requested_mode=requested_mode
            ):
                policy = supervision_log.default_policy(self.init_args())
                policy["skill_maintenance"] = supervision_log.skill_maintenance_contract(
                    current_mode
                )
                policy["permissions"]["allowlisted_skill_maintenance"] = (
                    current_mode
                    == "apply-allowlisted-skill-maintenance-with-review"
                )
                args = supervision_log.parser().parse_args(
                    [
                        "adjust",
                        "--target-thread",
                        "target-1234",
                        "--skill-maintenance-mode",
                        requested_mode,
                        "--reason",
                        "Operator authorized the change.",
                        *evidence_args,
                    ]
                )
                with mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(Path("/tmp/supervision-test"), policy),
                ):
                    with self.assertRaisesRegex(
                        supervision_log.SupervisionLogError,
                        "requires operator or review evidence",
                    ):
                        supervision_log.cmd_adjust(args)

    def test_policy_validation_rejects_economy_contract_drift(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["execution_economy"]["dimensions"] = ["relevance"]
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Execution-economy contract differs",
        ):
            supervision_log.validate_policy(policy)


class PriorityLifecycleNotificationTests(unittest.TestCase):
    def init_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            target_thread="target-1234",
            target_label="target",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread=None,
            fix_executor_thread="fixer-1234",
        )

    def bind_priority(
        self,
        policy: dict[str, object],
        *,
        message_id: str = "gmail-priority-1234",
        decision_context: bool = False,
    ) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                "target-1234",
                "--gmail-priority-reply-message-id",
                message_id,
                "--gmail-priority-project-key",
                "Main",
                "--gmail-priority-subject",
                "PRIORITY - Codex Implementation Blocked or Stopped - Main",
                *(["--gmail-priority-decision-context"] if decision_context else []),
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version"),
            redirect_stdout(output),
        ):
            supervision_log.cmd_bind(args)
        return json.loads(output.getvalue())

    def run_lifecycle_gate(
        self,
        policy: dict[str, object],
        state: str,
        records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        source = {
            "kind": "lifecycle",
            "record_id": "EVT-000001",
            "status": state,
            "state_fingerprint": "state-1234",
            "user_action_required": "yes",
        }
        args = argparse.Namespace(
            target_thread="target-1234",
            lifecycle_state=state,
            source_record="EVT-000001",
            state_fingerprint="state-1234",
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(
                supervision_log,
                "events",
                return_value=[source, *(records or [])],
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_lifecycle_gate(args)
        return json.loads(output.getvalue())

    def test_bind_priority_is_explicit_and_idempotent(self) -> None:
        policy = supervision_log.default_policy(self.init_args())

        first = self.bind_priority(policy)
        second = self.bind_priority(policy)

        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertTrue(policy["permissions"]["gmail_priority_notification"])
        self.assertEqual(
            policy["notifications"]["gmail_priority"]["reply_message_id"],
            "gmail-priority-1234",
        )

    def test_conflicting_priority_binding_fails_closed(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        self.bind_priority(policy)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "priority reply binding already differs",
        ):
            self.bind_priority(policy, message_id="gmail-priority-5678")

    def test_blocked_failed_and_stopped_use_priority_thread(self) -> None:
        for state in ("blocked", "failed", "stopped"):
            with self.subTest(state=state):
                policy = supervision_log.default_policy(self.init_args())
                self.bind_priority(policy)

                result = self.run_lifecycle_gate(policy, state)

                self.assertTrue(result["send_now"])
                self.assertEqual(result["channel"], "priority-lifecycle")
                self.assertEqual(
                    result["notification_category"], "gmail-priority-lifecycle"
                )
                self.assertEqual(
                    result["banner"], "🚨 IMPLEMENTATION BLOCKED / STOPPED 🚨"
                )
                self.assertEqual(result["reply_message_id"], "gmail-priority-1234")

    def test_completed_and_paused_remain_on_primary_thread(self) -> None:
        for state in ("completed", "paused"):
            with self.subTest(state=state):
                policy = supervision_log.default_policy(self.init_args())
                policy["notifications"]["gmail"].update(
                    {
                        "enabled": True,
                        "reply_message_id": "gmail-primary-1234",
                    }
                )

                result = self.run_lifecycle_gate(policy, state)

                self.assertTrue(result["send_now"])
                self.assertEqual(result["channel"], "primary-status")
                self.assertEqual(result["notification_category"], "gmail-lifecycle")

    def test_priority_transition_refuses_primary_thread_fallback(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail"].update(
            {"enabled": True, "reply_message_id": "gmail-primary-1234"}
        )

        result = self.run_lifecycle_gate(policy, "blocked")

        self.assertFalse(result["send_now"])
        self.assertEqual(result["channel"], "none")
        self.assertIn("not bound", result["reason"])

    def test_priority_delivery_is_deduplicated(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        self.bind_priority(policy)
        receipt = {
            "kind": "notification",
            "record_id": "EVT-000002",
            "category": "gmail-priority-lifecycle",
            "status": "sent",
            "dedup_key": "gmail-priority-lifecycle:EVT-000001",
            "evidence": ["EVT-000001", "gmail-message-1234"],
        }

        result = self.run_lifecycle_gate(policy, "blocked", [receipt])

        self.assertTrue(result["duplicate"])
        self.assertFalse(result["send_now"])

    def test_priority_user_decision_requires_complete_context_when_enabled(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        self.bind_priority(policy, decision_context=True)

        result = self.run_lifecycle_gate(policy, "blocked")

        self.assertTrue(result["decision_context_required"])
        self.assertEqual(
            result["required_decision_fields"],
            supervision_log.gmail_priority_contract()["required_decision_fields"],
        )

    def test_decision_context_requires_bound_priority_seed(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        args = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                "target-1234",
                "--gmail-priority-decision-context",
            ]
        )

        with mock.patch.object(
            supervision_log,
            "load_policy",
            return_value=(Path("/tmp/supervision-test"), policy),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "priority seed before enabling decision context",
            ):
                supervision_log.cmd_bind(args)

    def test_policy_validation_rejects_priority_contract_drift(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail_priority"]["lifecycle_states"] = ["blocked"]
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Gmail priority lifecycle contract differs",
        ):
            supervision_log.validate_policy(policy)

    def test_legacy_priority_policy_can_be_explicitly_upgraded(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        priority = policy["notifications"]["gmail_priority"]
        priority.pop("decision_context_enabled")
        priority.pop("decision_context_policy")
        priority.pop("required_decision_fields")
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        supervision_log.validate_policy(policy)
        self.bind_priority(policy, decision_context=True)

        self.assertTrue(priority["decision_context_enabled"])
        self.assertEqual(
            priority["required_decision_fields"],
            supervision_log.gmail_priority_contract()["required_decision_fields"],
        )

    def test_policy_validation_rejects_incomplete_enabled_priority_binding(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail_priority"]["enabled"] = True
        policy["permissions"]["gmail_priority_notification"] = True
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "priority lifecycle binding is incomplete",
        ):
            supervision_log.validate_policy(policy)


class DecisionResolutionTests(unittest.TestCase):
    target = "target-1234"
    decision = "DECISION-1234"
    hash_a = "a" * 64
    hash_b = "b" * 64
    hash_c = "c" * 64

    def init_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            target_thread=self.target,
            target_label="target",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread=None,
            fix_executor_thread="fixer-1234",
        )

    def record(
        self,
        directory: Path,
        policy: dict[str, object],
        *,
        classification: str,
        phase: str,
        safe_frontier: str = "nonempty",
        attempt: int = 0,
        outcome: str = "",
        now: str = "2026-08-01T12:00:00+00:00",
    ) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "decision-record",
                "--target-thread",
                self.target,
                "--decision-id",
                self.decision,
                "--classification",
                classification,
                "--phase",
                phase,
                "--safe-frontier",
                safe_frontier,
                "--attempt",
                str(attempt),
                "--outcome",
                outcome,
                "--decision-packet-hash",
                self.hash_a,
                "--blocked-scope-hash",
                self.hash_b,
                "--safe-frontier-hash",
                self.hash_c,
                "--state-fingerprint",
                "state-1234",
                "--evidence",
                "EVT-SOURCE-1234",
                "--now",
                now,
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_decision_record(args)
        return json.loads(output.getvalue())

    def gate(
        self,
        directory: Path,
        policy: dict[str, object],
        now: str,
    ) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "decision-gate",
                "--target-thread",
                self.target,
                "--decision-id",
                self.decision,
                "--now",
                now,
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_decision_gate(args)
        return json.loads(output.getvalue())

    def test_default_policy_has_fixed_continuation_first_contract(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        contract = policy["decision_resolution"]

        self.assertTrue(contract["continuation_first"])
        self.assertTrue(contract["attempt_before_user_notification"])
        self.assertTrue(contract["continue_attempts_during_user_window"])
        self.assertEqual(contract["human_response_minutes"], 20)
        self.assertEqual(contract["attempt_minutes"], 20)
        self.assertEqual(contract["max_attempts"], 3)
        self.assertEqual(contract["attempt_model"], "gpt-5.6-sol")
        self.assertEqual(contract["attempt_reasoning"], "max")
        self.assertEqual(
            contract["priority_phase_notifications"],
            ["human-input-requested", "final-disposition", "target-resumed"],
        )

    def test_bind_can_upgrade_exact_wait_first_predecessor_policy(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["decision_resolution"] = (
            supervision_log.legacy_wait_first_decision_resolution_contract()
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        supervision_log.validate_policy(policy)
        changed = supervision_log.ensure_execution_economy_policy(policy)

        self.assertTrue(changed)
        self.assertEqual(
            policy["decision_resolution"],
            supervision_log.decision_resolution_contract(),
        )

    def test_delegable_decision_resolves_immediately_without_human_wait(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(directory, policy, classification="delegable", phase="decision-ready")

            result = self.gate(directory, policy, "2026-08-01T12:00:00+00:00")

            self.assertEqual(result["action"], "resolve-immediately-and-continue")
            self.assertTrue(result["must_continue_safe_frontier"])
            self.assertFalse(result["notification_send_now"])
            self.assertFalse(result["blocking_permitted"])

            self.record(
                directory,
                policy,
                classification="delegable",
                phase="resolved",
                outcome="selected",
            )
            resolved = self.gate(directory, policy, "2026-08-01T12:01:00+00:00")
            self.assertFalse(resolved["notification_send_now"])
            self.assertEqual(resolved["notification_phase"], "")

    def test_first_resolution_attempt_precedes_human_notification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            policy["notifications"]["gmail_priority"].update(
                {
                    "enabled": True,
                    "reply_message_id": "gmail-priority-1234",
                    "decision_context_enabled": True,
                }
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )

            ready = self.gate(directory, policy, "2026-08-01T12:00:00+00:00")

            self.assertEqual(ready["action"], "start-sol-max-attempt")
            self.assertEqual(ready["next_attempt"], 1)
            self.assertTrue(ready["must_continue_safe_frontier"])
            self.assertFalse(ready["notification_send_now"])

            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
            )
            active = self.gate(directory, policy, "2026-08-01T12:19:59+00:00")
            self.assertEqual(
                active["action"], "continue-sol-max-attempt-and-safe-frontier"
            )
            self.assertFalse(active["notification_send_now"])

    def test_first_unresolved_attempt_requests_input_and_starts_next_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            policy["notifications"]["gmail_priority"].update(
                {
                    "enabled": True,
                    "reply_message_id": "gmail-priority-1234",
                    "decision_context_enabled": True,
                }
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
            )
            unresolved = self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-unresolved",
                attempt=1,
                now="2026-08-01T12:20:00+00:00",
            )["record"]

            result = self.gate(directory, policy, "2026-08-01T12:20:00+00:00")

            self.assertEqual(result["action"], "start-sol-max-attempt")
            self.assertEqual(result["next_attempt"], 2)
            self.assertTrue(result["must_continue_safe_frontier"])
            self.assertTrue(result["notification_send_now"])
            self.assertEqual(result["notification_phase"], "human-input-requested")
            self.assertEqual(
                result["required_decision_fields"],
                supervision_log.gmail_priority_contract()["required_decision_fields"],
            )
            self.assertEqual(
                unresolved["human_input_requested_at"],
                "2026-08-01T12:20:00+00:00",
            )
            self.assertEqual(
                unresolved["user_deadline_at"], "2026-08-01T12:40:00+00:00"
            )

    def test_later_attempts_continue_during_human_response_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-unresolved",
                attempt=1,
                now="2026-08-01T12:01:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=2,
                now="2026-08-01T12:01:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-unresolved",
                attempt=2,
                now="2026-08-01T12:02:00+00:00",
            )
            second = self.gate(directory, policy, "2026-08-01T12:02:00+00:00")
            self.assertEqual(second["action"], "start-sol-max-attempt")
            self.assertEqual(second["next_attempt"], 3)

            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=3,
                now="2026-08-01T12:02:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-unresolved",
                attempt=3,
                now="2026-08-01T12:03:00+00:00",
            )
            waiting = self.gate(directory, policy, "2026-08-01T12:03:00+00:00")
            expired = self.gate(directory, policy, "2026-08-01T12:21:00+00:00")

            self.assertEqual(
                waiting["action"], "await-user-and-continue-safe-frontier"
            )
            self.assertEqual(expired["action"], "choose-and-handoff")

    def test_three_unresolved_attempts_force_selection_for_preference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
                now="2026-08-01T11:40:00+00:00",
            )
            for attempt in (1, 2, 3):
                self.record(
                    directory,
                    policy,
                    classification="human-preference",
                    phase="attempt-started",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:00:00+00:00",
                )
                self.record(
                    directory,
                    policy,
                    classification="human-preference",
                    phase="attempt-unresolved",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:20:00+00:00",
                )

            result = self.gate(directory, policy, "2026-08-01T14:20:00+00:00")

            self.assertEqual(result["action"], "choose-and-handoff")
            self.assertEqual(result["attempt"], 3)
            self.assertFalse(result["blocking_permitted"])

    def test_three_unresolved_attempts_safe_defer_missing_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="decision-ready",
                safe_frontier="empty",
                now="2026-08-01T11:40:00+00:00",
            )
            for attempt in (1, 2, 3):
                self.record(
                    directory,
                    policy,
                    classification="missing-fact",
                    phase="attempt-started",
                    safe_frontier="empty",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:00:00+00:00",
                )
                self.record(
                    directory,
                    policy,
                    classification="missing-fact",
                    phase="attempt-unresolved",
                    safe_frontier="empty",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:20:00+00:00",
                )

            result = self.gate(directory, policy, "2026-08-01T14:20:00+00:00")

            self.assertEqual(result["action"], "safe-defer-and-handoff")
            self.assertFalse(result["blocking_permitted"])

    def test_delegable_decision_cannot_start_resolution_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(directory, policy, classification="delegable", phase="decision-ready")

            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "delegable decision must resolve immediately",
            ):
                self.record(
                    directory,
                    policy,
                    classification="delegable",
                    phase="attempt-started",
                    attempt=1,
                )

    def test_first_attempt_can_start_immediately_without_human_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )

            started = self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
                now="2026-08-01T12:00:00+00:00",
            )["record"]

            self.assertEqual(started["deadline_at"], "2026-08-01T12:20:00+00:00")
            self.assertEqual(started["user_deadline_at"], "")

    def test_first_attempt_resolution_never_requests_human_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            policy["notifications"]["gmail_priority"].update(
                {
                    "enabled": True,
                    "reply_message_id": "gmail-priority-1234",
                    "decision_context_enabled": True,
                }
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="resolved",
                attempt=1,
                outcome="selected",
                now="2026-08-01T12:05:00+00:00",
            )

            result = self.gate(directory, policy, "2026-08-01T12:05:00+00:00")

            self.assertEqual(result["action"], "send-exact-handoff")
            self.assertEqual(result["notification_phase"], "")
            self.assertFalse(result["notification_send_now"])

    def test_user_response_during_second_attempt_resolves_without_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="attempt-started",
                attempt=1,
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="attempt-unresolved",
                attempt=1,
                now="2026-08-01T12:05:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="attempt-started",
                attempt=2,
                now="2026-08-01T12:05:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="user-responded",
                attempt=2,
                now="2026-08-01T12:06:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="resolved",
                attempt=2,
                outcome="user-supplied",
                now="2026-08-01T12:06:01+00:00",
            )

            result = self.gate(directory, policy, "2026-08-01T12:06:01+00:00")

            self.assertEqual(result["action"], "send-exact-handoff")
            self.assertEqual(result["attempt"], 2)

    def test_classification_controls_final_disposition(self) -> None:
        cases = (
            ("delegable", "safe-deferred", "safe-deferred"),
            ("human-preference", "safe-deferred", "safe-deferred"),
            ("missing-fact", "resolved", "selected"),
            ("reserved-authority", "resolved", "selected"),
        )
        for classification, phase, outcome in cases:
            with self.subTest(classification=classification, phase=phase):
                with tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary)
                    policy = supervision_log.default_policy(self.init_args())
                    self.record(
                        directory,
                        policy,
                        classification=classification,
                        phase="decision-ready",
                    )
                    with self.assertRaises(supervision_log.SupervisionLogError):
                        self.record(
                            directory,
                            policy,
                            classification=classification,
                            phase=phase,
                            outcome=outcome,
                        )

    def test_legacy_priority_binding_cannot_send_decision_mail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            policy["notifications"]["gmail_priority"].update(
                {"enabled": True, "reply_message_id": "gmail-priority-1234"}
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-started",
                attempt=1,
            )
            self.record(
                directory,
                policy,
                classification="human-preference",
                phase="attempt-unresolved",
                attempt=1,
                now="2026-08-01T12:20:00+00:00",
            )

            result = self.gate(directory, policy, "2026-08-01T12:20:00+00:00")

            self.assertFalse(result["notification_send_now"])
            self.assertEqual(result["required_decision_fields"], [])

    def test_missing_fact_user_response_can_resolve_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="decision-ready",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="user-responded",
                now="2026-08-01T12:05:00+00:00",
            )
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="resolved",
                outcome="user-supplied",
                now="2026-08-01T12:06:00+00:00",
            )

            result = self.gate(directory, policy, "2026-08-01T12:06:00+00:00")

            self.assertEqual(result["action"], "send-exact-handoff")
            self.assertTrue(result["must_continue_safe_frontier"])


if __name__ == "__main__":
    unittest.main()
