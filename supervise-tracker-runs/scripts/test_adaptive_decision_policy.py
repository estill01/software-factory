#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("supervision_log.py")
SPEC = importlib.util.spec_from_file_location("supervision_log", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervision_log)


class AdaptiveDecisionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = "adaptive-target-1234"

    def policy(self, mode: str = "full-autonomous", *, repository_write: bool = True):
        permissions = {field: False for field in supervision_log.ADAPTIVE_PERMISSION_FIELDS}
        permissions["repository_write"] = repository_write
        permissions["command_or_test_execution"] = repository_write
        return {
            "target_thread_id": self.target,
            "policy_sha256": "a" * 64,
            "runtime": {
                "watcher_thread_id": "watcher-1234",
                "reviewer_thread_id": "reviewer-1234",
                "base_reviewer_thread_id": "base-reviewer-1234",
                "fix_executor_thread_id": "fix-executor-1234",
            },
            "permissions": permissions,
            "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(
                mode
            ),
        }

    def review(self, policy: dict[str, object], disposition: str = "accepted"):
        return {
            "record_id": "review-record-1234",
            "source_decision_record": "source-decision-1234",
            "source_decision_sha256": "1" * 64,
            "reviewer_id": "reviewer-1234",
            "review_disposition": disposition,
            "evidence_root": "2" * 64,
            "review_root": "3" * 64,
            "policy_sha256": policy["policy_sha256"],
        }

    def candidate(
        self,
        *,
        decision_id: str = "adaptive-decision-1234",
        fingerprint: str = "b" * 64,
        target_class: str = "target-repository",
        effect_class: str = "candidate-isolated-write",
        usage_updates: dict[str, int] | None = None,
        protected_result: str = "preserved",
    ) -> dict[str, object]:
        usage = {field: 0 for field in supervision_log.ADAPTIVE_CANDIDATE_USAGE_FIELDS}
        usage.update(
            {
                "active_lanes_for_decision": 1,
                "active_lanes_for_target": 1,
                "files": 1,
                "changed_lines": 12,
                "commands": 2,
                "elapsed_minutes": 4,
                "mapped_comparisons": 1,
            }
        )
        if usage_updates:
            usage.update(usage_updates)
        protected = [
            {
                "capability_id": "public-contract-1234",
                "result": protected_result,
                "evidence_root": "4" * 64,
            }
        ]
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-candidate-evidence",
            "decision_id": decision_id,
            "state_fingerprint": fingerprint,
            "target_class": target_class,
            "effect_class": effect_class,
            "owner_id": "candidate-owner-1234",
            "source_revision": "revision-1234",
            "candidate_root": "5" * 64,
            "candidate_budget_use": usage,
            "candidate_budget_use_root": supervision_log.digest(usage),
            "protected_capability_results": protected,
            "protected_capability_root": supervision_log.digest(protected),
            "validation_root": "6" * 64,
            "comparison_root": "7" * 64,
            "currentness_root": "",
            "evidence_root": "",
        }
        currentness = {
            "decision_id": decision_id,
            "state_fingerprint": fingerprint,
            "target_class": target_class,
            "effect_class": effect_class,
            "owner_id": value["owner_id"],
            "source_revision": value["source_revision"],
            "candidate_root": value["candidate_root"],
            "candidate_budget_use_root": value["candidate_budget_use_root"],
            "protected_capability_root": value["protected_capability_root"],
            "validation_root": value["validation_root"],
            "comparison_root": value["comparison_root"],
        }
        value["currentness_root"] = supervision_log.digest(currentness)
        material = dict(value)
        material.pop("evidence_root")
        value["evidence_root"] = supervision_log.digest(material)
        return value

    def write_candidate(self, value: dict[str, object]) -> Path:
        path = self.root / f"{value['decision_id']}-candidate.json"
        path.write_bytes(supervision_log.canonical(value) + b"\n")
        return path

    def packet(self, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "decision_id": "adaptive-decision-1234",
            "state_fingerprint": "b" * 64,
            "disposition": "correct-inline",
            "judgment_class": "ordinary-engineering",
            "consequence_class": "routine",
            "reversible": True,
            "mission_preserving": True,
            "target_class": "target-repository",
            "effect_class": "implementation-write",
            "candidate_evidence": None,
            "independent_review": None,
            "request_human_input": False,
            "blocked_subjects": [],
            "safe_frontier": ["block-7-unaffected-work"],
            "revisit_trigger": "",
        }
        value.update(updates)
        return value

    def init(self) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Adaptive policy fixture",
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
                "direct-item-1234",
                "--mission-source-sha256",
                "c" * 64,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_init(args)
        return json.loads(output.getvalue())["policy"]

    def adjust(self, *extra: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adjust",
                "--target-thread",
                self.target,
                *extra,
                "--reason",
                "Exercise bounded adaptive policy adjustment.",
                "--evidence",
                "block-7-focused-test",
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adjust(args)
        return json.loads(output.getvalue())["policy"]

    def gate_args(
        self,
        *,
        decision_id: str = "adaptive-cli-decision-1234",
        fingerprint: str = "d" * 64,
        review_record: str | None = None,
        request_human: bool = False,
    ):
        values = [
            "--root",
            str(self.root),
            "adaptive-decision-gate",
            "--target-thread",
            self.target,
            "--decision-id",
            decision_id,
            "--state-fingerprint",
            fingerprint,
            "--disposition",
            "correct-inline",
            "--judgment-class",
            "ordinary-engineering",
            "--consequence-class",
            "routine",
            "--reversible",
            "yes",
            "--mission-preserving",
            "yes",
            "--target-class",
            "target-repository",
            "--effect-class",
            "implementation-write",
            "--safe-frontier",
            "block-7-unaffected-work",
        ]
        if review_record:
            values.extend(["--independent-review-record", review_record])
        if request_human:
            values.append("--request-human-input")
        return supervision_log.parser().parse_args(values)

    def run_gate(self, args) -> dict[str, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adaptive_decision_gate(args)
        return json.loads(output.getvalue())

    def run_review(self, source_record: str, *, disposition: str = "accepted"):
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-review",
                "--target-thread",
                self.target,
                "--source-decision-record",
                source_record,
                "--reviewer-id",
                "reviewer-1234",
                "--review-disposition",
                disposition,
                "--evidence-root",
                "8" * 64,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adaptive_decision_review(args)
        return json.loads(output.getvalue())

    def test_new_policy_defaults_to_full_autonomous_with_sealed_effect_ceilings(self) -> None:
        policy = self.init()
        self.assertEqual(
            policy["adaptive_decision_control"]["adaptive_decision_mode"],
            "full-autonomous",
        )
        self.assertEqual(
            policy["adaptive_decision_control"]["candidate_budget"][
                "max_active_lanes_per_decision"
            ],
            1,
        )
        for field in (
            "production_promotion",
            "release",
            "deployment",
            "destructive_action",
            "spend",
            "credential_access",
            "external_action",
        ):
            self.assertIs(policy["permissions"][field], False)
        supervision_log.validate_policy(policy)

    def test_legacy_policy_stays_fixed_until_explicit_migration(self) -> None:
        policy = self.policy()
        del policy["adaptive_decision_control"]
        result = supervision_log.adaptive_decision_posture(policy, self.packet())
        self.assertEqual(result["adaptive_decision_mode"], "fixed")
        self.assertEqual(result["application_posture"], "record-only")
        self.assertTrue(result["legacy_policy_posture"])
        del policy["permissions"]["release"]
        self.assertTrue(supervision_log.ensure_adaptive_decision_policy(policy))
        self.assertFalse(policy["permissions"]["release"])

    def test_modes_preserve_exact_application_and_review_boundaries(self) -> None:
        fixed = supervision_log.adaptive_decision_posture(
            self.policy("fixed"), self.packet()
        )
        self.assertEqual(fixed["application_posture"], "record-only")
        recommend_policy = self.policy("recommend")
        pending = supervision_log.adaptive_decision_posture(
            recommend_policy, self.packet()
        )
        self.assertEqual(
            pending["application_posture"], "automated-independent-review-required"
        )
        reviewed = supervision_log.adaptive_decision_posture(
            recommend_policy,
            self.packet(independent_review=self.review(recommend_policy)),
        )
        self.assertEqual(reviewed["application_posture"], "recommendation-only")
        full = supervision_log.adaptive_decision_posture(
            self.policy(), self.packet()
        )
        self.assertTrue(full["application_authorized"])
        self.assertEqual(full["human_request_count"], 0)

    def test_full_autonomy_never_routes_ordinary_judgment_to_a_human(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "forbids a human request"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy(), self.packet(request_human_input=True)
            )
        notification = supervision_log.decision_notification(
            {
                "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(),
                "notifications": {"gmail_priority": {"enabled": True}},
            },
            [],
            {
                "record_id": "EVT-000001",
                "classification": "human-preference",
                "phase": "attempt-unresolved",
                "attempt": 1,
            },
            "start-sol-max-attempt",
        )
        self.assertEqual(notification["notification_phase"], "")
        self.assertFalse(notification["notification_send_now"])

    def test_effect_specific_permissions_prevent_scope_laundering(self) -> None:
        policy = self.policy()
        candidate = self.candidate(
            effect_class="production-cutover"
        )
        review = self.review(policy)
        result = supervision_log.adaptive_decision_posture(
            policy,
            self.packet(
                disposition="cutover-candidate",
                effect_class="production-cutover",
                candidate_evidence=candidate,
                independent_review=review,
                blocked_subjects=["production-promotion"],
                revisit_trigger="Production promotion authority becomes current.",
            ),
        )
        self.assertFalse(result["permission_granted"])
        self.assertEqual(result["application_posture"], "reserved-external")
        self.assertFalse(result["permission_results"]["production_promotion"])
        skill_policy = self.policy()
        skill_policy["permissions"].update(
            {
                "allowlisted_skill_maintenance": True,
                "production_promotion": True,
                "release": False,
            }
        )
        skill_result = supervision_log.adaptive_decision_posture(
            skill_policy,
            self.packet(
                disposition="cutover-candidate",
                target_class="software-factory",
                effect_class="skill-release-cutover",
                candidate_evidence=self.candidate(
                    target_class="software-factory",
                    effect_class="skill-release-cutover",
                ),
                independent_review=self.review(skill_policy),
                blocked_subjects=["skill-release-authority"],
                revisit_trigger="Release authority becomes current.",
            ),
        )
        self.assertEqual(skill_result["application_posture"], "reserved-external")
        self.assertFalse(skill_result["permission_results"]["release"])
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "disposition and effect"
        ):
            supervision_log.adaptive_decision_posture(
                policy,
                self.packet(effect_class="deployment"),
            )

    def test_candidate_evidence_is_canonical_current_and_budget_bound(self) -> None:
        candidate = self.candidate()
        path = self.write_candidate(candidate)
        loaded = supervision_log.load_adaptive_candidate_evidence(
            str(path),
            decision_id="adaptive-decision-1234",
            state_fingerprint="b" * 64,
            target_class="target-repository",
            effect_class="candidate-isolated-write",
        )
        self.assertEqual(loaded["evidence_root"], candidate["evidence_root"])
        path.write_bytes(supervision_log.canonical(candidate) + b" \n")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "exact canonical"
        ):
            supervision_log.load_adaptive_candidate_evidence(
                str(path),
                decision_id="adaptive-decision-1234",
                state_fingerprint="b" * 64,
                target_class="target-repository",
                effect_class="candidate-isolated-write",
            )
        over = self.candidate(usage_updates={"files": 4})
        result = supervision_log.adaptive_decision_posture(
            self.policy(),
            self.packet(
                disposition="compare-candidate",
                effect_class="candidate-isolated-write",
                candidate_evidence=over,
            ),
        )
        self.assertTrue(result["budget_exceeded"])
        self.assertEqual(result["application_posture"], "stop-and-retire-candidate")

    def test_protected_regression_and_unverified_result_stop_candidate(self) -> None:
        for posture in ("regressed", "unverified"):
            result = supervision_log.adaptive_decision_posture(
                self.policy(),
                self.packet(
                    disposition="compare-candidate",
                    effect_class="candidate-isolated-write",
                    candidate_evidence=self.candidate(protected_result=posture),
                ),
            )
            self.assertTrue(result["protected_regression"])
            self.assertEqual(
                result["application_posture"], "stop-and-retire-candidate"
            )

    def test_review_is_canonical_separate_current_and_one_use(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source = self.run_gate(self.gate_args())["record"]
        self.assertEqual(
            source["application_posture"], "automated-independent-review-required"
        )
        review = self.run_review(source["record_id"])["record"]
        self.assertEqual(review["source_decision_sha256"], source["record_sha256"])
        applied = self.run_gate(
            self.gate_args(
                review_record=review["record_id"], request_human=True
            )
        )["record"]
        self.assertEqual(applied["independent_review_record"], review["record_id"])
        self.assertEqual(applied["human_request_count"], 1)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "stale|already has"
        ):
            self.run_review(source["record_id"], disposition="rejected")

    def test_review_rejects_unbound_or_self_review_identity(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source = self.run_gate(self.gate_args())["record"]
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-review",
                "--target-thread",
                self.target,
                "--source-decision-record",
                source["record_id"],
                "--reviewer-id",
                self.target,
                "--review-disposition",
                "accepted",
                "--evidence-root",
                "8" * 64,
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "not independently owned"
        ):
            supervision_log.cmd_adaptive_decision_review(args)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "does not exist|Canonical adaptive"
        ):
            self.run_gate(self.gate_args(review_record="invented-review-1234"))

    def test_repeated_lower_mode_request_is_keyed_by_state_not_decision_id(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        first_source = self.run_gate(self.gate_args(decision_id="decision-one-1234"))["record"]
        first_review = self.run_review(first_source["record_id"])["record"]
        self.run_gate(
            self.gate_args(
                decision_id="decision-one-1234",
                review_record=first_review["record_id"],
                request_human=True,
            )
        )
        second_source = self.run_gate(
            self.gate_args(decision_id="decision-two-1234")
        )["record"]
        second_review = self.run_review(second_source["record_id"])["record"]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "state already emitted"
        ):
            self.run_gate(
                self.gate_args(
                    decision_id="decision-two-1234",
                    review_record=second_review["record_id"],
                    request_human=True,
                )
            )

    def test_adjustment_is_append_only_and_never_expands_permissions(self) -> None:
        initial = self.init()
        initial_permissions = copy.deepcopy(initial["permissions"])
        first_history = (self.root / self.target / "policy-history.jsonl").read_bytes()
        adjusted = self.adjust(
            "--adaptive-decision-mode",
            "recommend",
            "--candidate-max-files",
            "5",
            "--candidate-max-commands",
            "9",
        )
        self.assertEqual(adjusted["permissions"], initial_permissions)
        self.assertEqual(
            adjusted["adaptive_decision_control"]["candidate_budget"]["max_files"], 5
        )
        history = (self.root / self.target / "policy-history.jsonl").read_bytes()
        self.assertTrue(history.startswith(first_history))
        self.assertEqual(len(history.splitlines()), 2)

    def test_status_reports_adaptive_and_existing_decision_requests_truthfully(self) -> None:
        policy = self.policy("recommend")
        result = supervision_log.adaptive_decision_posture(
            policy,
            self.packet(
                independent_review=self.review(policy),
                request_human_input=True,
            ),
        )
        events = [
            {"kind": "adaptive-decision", **result},
            {
                "kind": "decision",
                "decision_id": "legacy-decision-1234",
                "human_input_requested_at": "2026-08-09T00:00:00+00:00",
                "policy_sha256": "0" * 64,
            },
        ]
        status = supervision_log.adaptive_status_projection(policy, events)
        self.assertEqual(status["human_request_count"], 2)
        self.assertEqual(status["adaptive_human_request_count"], 1)
        self.assertEqual(status["legacy_decision_human_request_count"], 1)

    def test_invalid_types_and_fabricated_review_or_usage_reject(self) -> None:
        with self.assertRaises(supervision_log.SupervisionLogError):
            supervision_log.adaptive_decision_posture(
                self.policy(), self.packet(decision_id=True)
            )
        candidate = self.candidate()
        candidate["candidate_budget_use"]["review_passes"] = 1
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "cannot self-assert"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy(),
                self.packet(
                    disposition="compare-candidate",
                    effect_class="candidate-isolated-write",
                    candidate_evidence=candidate,
                ),
            )
        review = self.review(self.policy())
        review["policy_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "not current"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy("recommend"),
                self.packet(independent_review=review),
            )

    def test_cli_help_exposes_evidence_review_effect_and_input_avoidance(self) -> None:
        parser = supervision_log.parser()
        parsed = parser.parse_args(
            [
                "adaptive-decision-gate",
                "--target-thread",
                self.target,
                "--decision-id",
                "decision-1234",
                "--state-fingerprint",
                "f" * 64,
                "--disposition",
                "continue-unchanged",
                "--judgment-class",
                "ordinary-engineering",
                "--consequence-class",
                "routine",
                "--reversible",
                "yes",
                "--mission-preserving",
                "yes",
                "--target-class",
                "target-repository",
                "--effect-class",
                "no-mutation",
            ]
        )
        self.assertEqual(parsed.command, "adaptive-decision-gate")
        text = MODULE_PATH.parent.parent.joinpath("SKILL.md").read_text(encoding="utf-8")
        text += MODULE_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        for token in (
            "adaptive-decision-review",
            "--candidate-evidence",
            "--target-class",
            "--effect-class",
            "full-autonomous",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
