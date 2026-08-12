from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import supervision_log


FIXTURE_PATH = Path(__file__).with_name("fixtures") / "control_posture_replay_v1.json"


class ControlPostureReplayTests(unittest.TestCase):
    mission_root = "a" * 64

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def create_target(self, target: str) -> tuple[Path, dict[str, object]]:
        args = supervision_log.parser().parse_args(
            [
                "init",
                "--target-thread",
                target,
                "--target-label",
                target,
                "--watcher-thread",
                f"watcher-{target}",
                "--reviewer-thread",
                f"reviewer-{target}",
                "--base-reviewer-thread",
                f"base-{target}",
                "--mission-root",
                self.mission_root,
                "--mission-source-record",
                f"mission-{target}",
            ]
        )
        policy = supervision_log.default_policy(args)
        directory = self.root / target
        directory.mkdir()
        supervision_log.atomic_json(directory / "policy.json", policy)
        return directory, policy

    def public_gate(self, target: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "control-posture-gate",
                "--target-thread",
                target,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def materialize(self, value: object) -> object:
        if value == "$MISSION_ROOT":
            return self.mission_root
        if isinstance(value, list):
            return [self.materialize(item) for item in value]
        if isinstance(value, dict):
            return {key: self.materialize(item) for key, item in value.items()}
        return value

    def append(self, directory: Path, record: dict[str, object]) -> None:
        supervision_log.append_raw(directory / "events.jsonl", record)

    def test_fixture_and_owner_contracts_remain_content_minimized(self) -> None:
        self.assertEqual(
            set(self.fixture),
            {
                "schema_version",
                "kind",
                "failure_mode_id",
                "source_event_span",
                "source_rejection",
                "matrix_domains",
                "sequence",
            },
        )
        expected_step_keys = {
            "step_id",
            "state",
            "provenance_class",
            "identity",
            "causal_transition",
            "events",
            "expected_posture",
            "expected_next_action",
            "expected_observable_effect",
        }
        for step in self.fixture["sequence"]:
            self.assertEqual(set(step), expected_step_keys)
            self.assertFalse(
                {"prompt", "transcript", "private_narrative"}
                & set().union(*(set(event) for event in step["events"]))
            )

        repository = Path(__file__).resolve().parents[2]
        owner_files = [
            repository / "author-implementation-trackers" / "SKILL.md",
            repository / "implement-tracker-blocks" / "SKILL.md",
            repository / "supervise-tracker-runs" / "SKILL.md",
        ]
        for path in owner_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("control_posture_replay_v1.json", text)
            self.assertIn("human", text.lower())
        changelog = (repository / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Replay-certified control-posture convergence", changelog)
        self.assertIn("Blocks 0–3 control plane only", changelog)

    def decision(self, state: str, record_id: str) -> dict[str, object] | None:
        if state == "absent":
            return None
        return {
            "record_id": record_id,
            "kind": "decision",
            "decision_id": f"DEC-{record_id}",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "safe-deferred",
            "safe_frontier": "nonempty" if state == "safe-work" else "empty",
            "mission_root": self.mission_root,
            "authority_source_class": (
                "supervisor-steer" if state == "nonblocking" else "direct-user"
            ),
            "authority_source_record": f"AUTH-{record_id}",
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }

    def completion_records(
        self,
        state: str,
        start: int,
        *,
        reviewer_id: str,
        implementation_owner_id: str,
    ) -> list[dict[str, object]]:
        fingerprint = f"matrix-{start}"
        if state == "completed-current":
            check = {
                "record_id": f"EVT-{start:06d}",
                "kind": "check",
                "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                "status": "verified",
                "state_fingerprint": fingerprint,
                "mission_root": self.mission_root,
                "model": "gpt-5.6-sol",
                "reasoning": "xhigh",
                "evidence": ["matrix-observable-effect"],
                "capability_reconciliation_reviewer_id": reviewer_id,
                "capability_reconciliation_implementation_owner_id": implementation_owner_id,
                "capability_reconciliation_revision": "e" * 40,
                "capability_reconciliation_posture": "verified",
                "capability_reconciliation_gap_count": 0,
                **{
                    field: "d" * 64
                    for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                },
            }
            return [
                check,
                {
                    "record_id": f"EVT-{start + 1:06d}",
                    "kind": "lifecycle",
                    "status": "completed",
                    "state_fingerprint": fingerprint,
                    "outcome_completion_record_id": check["record_id"],
                },
            ]
        if state == "completed-stale":
            return [
                {
                    "record_id": f"EVT-{start:06d}",
                    "kind": "lifecycle",
                    "status": "completed",
                    "state_fingerprint": fingerprint,
                    "outcome_completion_record_id": "EVT-MISSING",
                }
            ]
        if state in {"stopped-authorized", "stopped-unauthorized"}:
            decision_id = f"DEC-STOP-{start}"
            decision_record = f"EVT-{start:06d}"
            fingerprint = f"matrix-stop-{start}"
            decision = {
                "record_id": decision_record,
                "kind": "decision",
                "decision_id": decision_id,
                "phase": "target-acknowledged",
                "classification": "reserved-authority",
                "outcome": "user-supplied",
                "safe_frontier": "empty",
                "state_fingerprint": fingerprint,
                "mission_root": self.mission_root,
                "authority_source_class": (
                    "direct-user"
                    if state == "stopped-authorized"
                    else "supervisor-steer"
                ),
                "authority_source_record": f"AUTH-STOP-{start}",
                "impact_class": "goal-blocking",
                "ordinary_means_disabled": True,
                "independent_mission_review": True,
            }
            return [
                decision,
                {
                    "record_id": f"EVT-{start + 1:06d}",
                    "kind": "lifecycle",
                    "status": "stopped",
                    "state_fingerprint": fingerprint,
                    "evidence": [decision_record],
                },
            ]
        return []

    def test_observed_sequence_converges_through_the_public_gate(self) -> None:
        self.assertLess(FIXTURE_PATH.stat().st_size, 16 * 1024)
        self.assertEqual(self.fixture["source_event_span"], ["EVT-000067", "EVT-000084"])
        self.assertEqual(self.fixture["source_rejection"], "EVT-000081")
        self.assertEqual(
            self.fixture["failure_mode_id"], "FM-UNAUTHORIZED-EARLY-RETURN"
        )
        target = "owner-1234"
        directory, _policy = self.create_target(target)
        expected_effects = {
            "replay-1": "keep the source outcome active",
            "replay-2": "retain the open transition without asking the human to schedule it",
            "replay-3": "reject handoff as outcome completion",
            "replay-4": "resume the same task autonomously",
            "replay-5": "permit completion only from current outcome proof",
        }
        for step in self.fixture["sequence"]:
            self.assertEqual(
                step["expected_observable_effect"], expected_effects[step["step_id"]]
            )
            for event in self.materialize(step["events"]):
                self.append(directory, event)
            first = self.public_gate(target)
            second = self.public_gate(target)
            self.assertEqual(first, second, step["step_id"])
            self.assertEqual(first["required_target_posture"], step["expected_posture"])
            self.assertEqual(first["next_action"], step["expected_next_action"])
            self.assertFalse(first["human_input_required"])
            self.assertFalse(first["manual_resume_required"])
            self.assertEqual(first["member_count"], 1)
            if step["step_id"] in {"replay-1", "replay-2", "replay-3"}:
                expected_transition_head = {
                    "replay-1": "EVT-000001",
                    "replay-2": "EVT-000001",
                    "replay-3": "EVT-000003",
                }
                self.assertEqual(
                    first["open_transition_records"],
                    [expected_transition_head[step["step_id"]]],
                )
            elif step["step_id"] == "replay-4":
                self.assertEqual(first["open_transition_records"], [])
                self.assertEqual(first["open_decision_records"], [])
                self.assertEqual(
                    first["reconciled_decisions"][0]["correction_record_id"],
                    "EVT-000004",
                )
            else:
                self.assertEqual(
                    first["completion_candidates"][0]["completion_record_id"],
                    "EVT-000005",
                )
        self.assertEqual(first["required_target_posture"], "completed")

    def test_self_successor_and_subordinate_authority_cannot_override_owner(
        self,
    ) -> None:
        self_target = "self-owner-1234"
        self_directory, self_policy = self.create_target(self_target)
        self.append(
            self_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-SELF-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self_target,
                "successor_mission_root": self.mission_root,
                "successor_group_id": self_policy["supervision_group_id"],
            },
        )
        self_result = self.public_gate(self_target)
        self.assertEqual(self_result["required_target_posture"], "in-progress")
        self.assertEqual(
            self_result["next_action"],
            "reconcile-control-membership-or-evidence",
        )
        self.assertIn(
            "successor-membership-cycle-or-duplicate",
            {item["kind"] for item in self_result["issues"]},
        )

        owner = "governing-owner-1234"
        child = "subordinate-1234"
        owner_directory, owner_policy = self.create_target(owner)
        child_directory, child_policy = self.create_target(child)
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-CHILD-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": child,
                "successor_mission_root": self.mission_root,
                "successor_group_id": child_policy["supervision_group_id"],
            },
        )
        subordinate_decision = {
            "record_id": "EVT-000001",
            "kind": "decision",
            "decision_id": "DEC-SUBORDINATE-1234",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "safe-deferred",
            "safe_frontier": "empty",
            "state_fingerprint": "subordinate-state-1234",
            "mission_root": self.mission_root,
            "authority_source_class": "direct-user",
            "authority_source_record": "SUBORDINATE-DIRECT-1234",
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }
        self.append(child_directory, subordinate_decision)
        decision_result = supervision_log.reduce_control_posture(
            directory=owner_directory,
            policy=owner_policy,
            owner_events=supervision_log.events(owner_directory / "events.jsonl"),
        )
        self.assertEqual(decision_result["member_count"], 2)
        self.assertEqual(decision_result["issues"], [])
        self.assertEqual(decision_result["required_target_posture"], "in-progress")
        self.assertEqual(
            decision_result["next_action"],
            "continue-safe-frontier-or-resolve-decision",
        )
        self.assertEqual(decision_result["blocking_decision_records"], [])
        self.assertEqual(decision_result["open_decision_records"], ["EVT-000001"])

        owner_blocking_decision = {
            **subordinate_decision,
            "record_id": "EVT-000002",
            "decision_id": "DEC-OWNER-1234",
            "state_fingerprint": "owner-state-1234",
            "authority_source_record": "OWNER-DIRECT-1234",
        }
        self.append(owner_directory, owner_blocking_decision)
        owner_blocking_result = supervision_log.reduce_control_posture(
            directory=owner_directory,
            policy=owner_policy,
            owner_events=supervision_log.events(owner_directory / "events.jsonl"),
        )
        self.assertEqual(owner_blocking_result["required_target_posture"], "blocked")
        self.assertEqual(
            owner_blocking_result["next_action"],
            "preserve-safe-deferral-and-revisit-on-authority-change",
        )
        self.assertEqual(owner_blocking_result["blocking_decision_records"], ["EVT-000002"])
        self.assertEqual(
            owner_blocking_result["open_decision_records"],
            ["EVT-000002", "EVT-000001"],
        )

        self.append(
            owner_directory,
            {
                **owner_blocking_decision,
                "record_id": "EVT-000003",
                "outcome": "user-supplied",
            },
        )
        stop_decision = {
            **subordinate_decision,
            "record_id": "EVT-000002",
            "outcome": "user-supplied",
        }
        self.append(child_directory, stop_decision)
        self.append(
            child_directory,
            {
                "record_id": "EVT-000003",
                "kind": "lifecycle",
                "status": "stopped",
                "state_fingerprint": "subordinate-state-1234",
                "evidence": ["EVT-000002"],
            },
        )
        stop_result = supervision_log.reduce_control_posture(
            directory=owner_directory,
            policy=owner_policy,
            owner_events=supervision_log.events(owner_directory / "events.jsonl"),
        )
        self.assertEqual(stop_result["required_target_posture"], "in-progress")
        self.assertEqual(stop_result["next_action"], "continue-governing-outcome")
        self.assertEqual(stop_result["direct_stop_candidates"], [])
        self.assertEqual(stop_result["subordinate_stop_records"], ["EVT-000003"])
        self.assertFalse(stop_result["human_input_required"])
        self.assertFalse(stop_result["manual_resume_required"])

    def test_supported_control_state_matrix_has_one_deterministic_posture(self) -> None:
        domains = self.fixture["matrix_domains"]
        for index, (transition, decision, lifecycle) in enumerate(
            itertools.product(
                domains["transition"], domains["decision"], domains["lifecycle"]
            ),
            start=1,
        ):
            with self.subTest(
                transition=transition,
                decision=decision,
                lifecycle=lifecycle,
            ):
                target = f"matrix-{index:04d}"
                directory, policy = self.create_target(target)
                records: list[dict[str, object]] = []
                if transition != "absent":
                    records.append(
                        {
                            "record_id": "EVT-000001",
                            "kind": "successor-transition",
                            "transition_id": "TRANSITION-MATRIX-1234",
                            "phase": "required" if transition == "open" else "cancelled",
                            "tracker_sha256": "c" * 64,
                        }
                    )
                decision_record = self.decision(
                    decision, f"EVT-{len(records) + 1:06d}"
                )
                if decision_record is not None:
                    records.append(decision_record)
                records.extend(
                    self.completion_records(
                        lifecycle,
                        len(records) + 1,
                        reviewer_id=f"base-{target}",
                        implementation_owner_id=target,
                    )
                )
                for record in records:
                    self.append(directory, record)

                result = supervision_log.reduce_control_posture(
                    directory=directory,
                    policy=policy,
                    owner_events=supervision_log.events(directory / "events.jsonl"),
                )
                if lifecycle in {"completed-stale", "stopped-unauthorized"}:
                    expected = (
                        "in-progress",
                        "reconcile-control-membership-or-evidence",
                    )
                elif lifecycle == "stopped-authorized":
                    expected = ("stopped", "close-governing-outcome-at-direct-stop")
                elif transition == "open":
                    expected = ("in-progress", "continue-open-successor-transition")
                elif decision in {"safe-work", "nonblocking"}:
                    expected = (
                        "in-progress",
                        "continue-safe-frontier-or-resolve-decision",
                    )
                elif decision == "blocking":
                    expected = (
                        "blocked",
                        "preserve-safe-deferral-and-revisit-on-authority-change",
                    )
                elif lifecycle == "completed-current":
                    expected = ("completed", "close-governing-outcome")
                else:
                    expected = ("in-progress", "continue-governing-outcome")
                self.assertEqual(
                    (result["required_target_posture"], result["next_action"]),
                    expected,
                )
                self.assertIn(
                    result["required_target_posture"],
                    {"in-progress", "blocked", "stopped", "completed"},
                )
                self.assertFalse(result["human_input_required"])
                self.assertFalse(result["manual_resume_required"])
                self.assertEqual(result["member_count"], 1)


if __name__ == "__main__":
    unittest.main()
