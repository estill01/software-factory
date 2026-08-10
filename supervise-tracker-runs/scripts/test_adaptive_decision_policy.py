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
        policy = {
            "policy_sha256": "a" * 64,
            "permissions": {
                "repository_write": repository_write,
                "command_or_test_execution": repository_write,
            },
            "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(
                mode
            ),
        }
        return policy

    def packet(self, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "decision_id": "adaptive-decision-1234",
            "state_fingerprint": "b" * 64,
            "disposition": "correct-inline",
            "judgment_class": "ordinary-engineering",
            "consequence_class": "routine",
            "reversible": True,
            "mission_preserving": True,
            "required_permission": "repository_write",
            "independent_review_complete": True,
            "request_human_input": False,
            "candidate_budget_use": {
                "active_lanes_for_decision": 0,
                "active_lanes_for_target": 0,
                "files": 0,
                "changed_lines": 0,
                "commands": 0,
                "elapsed_minutes": 0,
                "mapped_comparisons": 0,
                "review_passes": 0,
            },
            "protected_regression": False,
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

    def gate_args(self, *, fingerprint: str = "d" * 64):
        return supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-gate",
                "--target-thread",
                self.target,
                "--decision-id",
                "adaptive-cli-decision-1234",
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
                "--required-permission",
                "repository_write",
                "--independent-review-complete",
                "yes",
                "--request-human-input",
                "--safe-frontier",
                "block-7-unaffected-work",
            ]
        )

    def test_new_policy_defaults_to_full_autonomous_with_one_lane(self) -> None:
        policy = self.init()

        adaptive = policy["adaptive_decision_control"]
        self.assertEqual(adaptive["adaptive_decision_mode"], "full-autonomous")
        self.assertEqual(
            adaptive["candidate_budget"]["max_active_lanes_per_decision"], 1
        )
        self.assertEqual(
            adaptive["candidate_budget"]["max_active_lanes_per_target"], 1
        )
        supervision_log.validate_policy(policy)

    def test_legacy_policy_stays_fixed_until_explicit_migration(self) -> None:
        policy = self.policy()
        del policy["adaptive_decision_control"]

        result = supervision_log.adaptive_decision_posture(policy, self.packet())
        self.assertEqual(result["adaptive_decision_mode"], "fixed")
        self.assertEqual(result["application_posture"], "record-only")
        self.assertTrue(result["legacy_policy_posture"])

        self.assertTrue(supervision_log.ensure_adaptive_decision_policy(policy))
        self.assertEqual(
            policy["adaptive_decision_control"]["adaptive_decision_mode"],
            "full-autonomous",
        )

    def test_modes_preserve_their_exact_application_boundaries(self) -> None:
        fixed = supervision_log.adaptive_decision_posture(
            self.policy("fixed"), self.packet()
        )
        self.assertEqual(fixed["application_posture"], "record-only")

        recommend_review = supervision_log.adaptive_decision_posture(
            self.policy("recommend"),
            self.packet(independent_review_complete=False),
        )
        self.assertEqual(
            recommend_review["application_posture"],
            "automated-independent-review-required",
        )
        recommend = supervision_log.adaptive_decision_posture(
            self.policy("recommend"), self.packet()
        )
        self.assertEqual(recommend["application_posture"], "recommendation-only")

        reviewed_inline = supervision_log.adaptive_decision_posture(
            self.policy("reviewed-autonomous"), self.packet()
        )
        self.assertTrue(reviewed_inline["application_authorized"])
        reviewed_consequential = supervision_log.adaptive_decision_posture(
            self.policy("reviewed-autonomous"),
            self.packet(
                disposition="amend-structure",
                consequence_class="consequential",
            ),
        )
        self.assertEqual(
            reviewed_consequential["application_posture"],
            "external-application-authority-required",
        )

        full = supervision_log.adaptive_decision_posture(
            self.policy("full-autonomous"), self.packet()
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

    def test_permission_ceiling_reserves_without_granting_or_requesting(self) -> None:
        result = supervision_log.adaptive_decision_posture(
            self.policy(repository_write=False),
            self.packet(
                blocked_subjects=["repository-owned-correction"],
                revisit_trigger="Repository write authority becomes current.",
            ),
        )

        self.assertFalse(result["permission_granted"])
        self.assertFalse(result["application_authorized"])
        self.assertEqual(result["application_posture"], "reserved-external")
        self.assertEqual(result["human_request_count"], 0)
        self.assertEqual(
            result["next_action"], "continue-safe-frontier-without-human-request"
        )

        candidate_policy = self.policy()
        candidate_policy["permissions"]["command_or_test_execution"] = False
        candidate = supervision_log.adaptive_decision_posture(
            candidate_policy,
            self.packet(
                disposition="compare-candidate",
                blocked_subjects=["candidate-command-execution"],
                revisit_trigger="Command authority becomes current.",
            ),
        )
        self.assertEqual(candidate["application_posture"], "reserved-external")
        self.assertFalse(
            candidate["permission_results"]["command_or_test_execution"]
        )

    def test_candidate_review_and_resource_stops_fail_closed(self) -> None:
        review = supervision_log.adaptive_decision_posture(
            self.policy(),
            self.packet(
                disposition="compare-candidate",
                independent_review_complete=False,
            ),
        )
        self.assertEqual(
            review["application_posture"], "automated-independent-review-required"
        )

        usage = copy.deepcopy(self.packet()["candidate_budget_use"])
        assert isinstance(usage, dict)
        usage["active_lanes_for_target"] = 2
        stop = supervision_log.adaptive_decision_posture(
            self.policy(),
            self.packet(
                disposition="compare-candidate",
                candidate_budget_use=usage,
            ),
        )
        self.assertTrue(stop["budget_exceeded"])
        self.assertEqual(stop["application_posture"], "stop-and-retire-candidate")
        protected = supervision_log.adaptive_decision_posture(
            self.policy(),
            self.packet(
                disposition="compare-candidate",
                protected_regression=True,
            ),
        )
        self.assertEqual(
            protected["application_posture"], "stop-and-retire-candidate"
        )

    def test_invalid_types_modes_and_permission_claims_reject(self) -> None:
        invalid = supervision_log.adaptive_decision_control_contract()
        invalid["candidate_budget"]["max_files"] = True
        with self.assertRaises(supervision_log.SupervisionLogError):
            supervision_log.validate_adaptive_decision_control(invalid)
        with self.assertRaises(supervision_log.SupervisionLogError):
            supervision_log.adaptive_decision_control_contract("unbounded")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "required permission ceiling"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy(), self.packet(required_permission="none")
            )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "must be a string"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy(), self.packet(decision_id=True)
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
            adjusted["adaptive_decision_control"]["adaptive_decision_mode"],
            "recommend",
        )
        self.assertEqual(
            adjusted["adaptive_decision_control"]["candidate_budget"]["max_files"],
            5,
        )
        history = (self.root / self.target / "policy-history.jsonl").read_bytes()
        self.assertTrue(history.startswith(first_history))
        self.assertEqual(len(history.splitlines()), 2)

    def test_gate_deduplicates_and_refuses_a_repeated_lower_mode_request(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        args = self.gate_args()
        first_output = io.StringIO()
        with redirect_stdout(first_output):
            supervision_log.cmd_adaptive_decision_gate(args)
        first = json.loads(first_output.getvalue())
        self.assertFalse(first["duplicate"])
        self.assertEqual(first["record"]["human_request_count"], 1)

        duplicate_output = io.StringIO()
        with redirect_stdout(duplicate_output):
            supervision_log.cmd_adaptive_decision_gate(args)
        self.assertTrue(json.loads(duplicate_output.getvalue())["duplicate"])

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "already emitted"
        ):
            supervision_log.cmd_adaptive_decision_gate(
                self.gate_args(fingerprint="e" * 64)
            )

        status_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "status",
                "--target-thread",
                self.target,
            ]
        )
        status_output = io.StringIO()
        with redirect_stdout(status_output):
            supervision_log.cmd_status(status_args)
        status = json.loads(status_output.getvalue())["adaptive_decision_control"]
        self.assertEqual(status["adaptive_decision_mode"], "recommend")
        self.assertEqual(status["human_request_count"], 1)
        self.assertEqual(status["decision_count"], 1)

    def test_status_projection_exposes_mode_budget_use_and_deferrals(self) -> None:
        control = self.policy("recommend")["adaptive_decision_control"]
        result = supervision_log.adaptive_decision_posture(
            self.policy("recommend"),
            self.packet(
                judgment_class="reserved-external",
                blocked_subjects=["credential-owned-effect"],
                revisit_trigger="Credential authority is supplied.",
            ),
        )
        event = {"kind": "adaptive-decision", **result}
        status = supervision_log.adaptive_status_projection(
            {"adaptive_decision_control": control}, [event]
        )

        self.assertEqual(status["adaptive_decision_mode"], "recommend")
        self.assertEqual(status["decision_count"], 1)
        self.assertEqual(status["reserved_external_count"], 1)
        self.assertEqual(
            status["last_application_posture"], "reserved-external"
        )
        self.assertEqual(
            status["last_safe_frontier"], ["block-7-unaffected-work"]
        )

    def test_cli_help_exposes_mode_budget_and_input_avoidance_gate(self) -> None:
        help_text = MODULE_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy_text = MODULE_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        parser = supervision_log.parser()
        self.assertEqual(
            parser.parse_args(
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
                    "--required-permission",
                    "none",
                    "--independent-review-complete",
                    "no",
                ]
            ).command,
            "adaptive-decision-gate",
        )
        for token in (
            "adaptive-decision-gate",
            "--adaptive-decision-mode",
            "full-autonomous",
            "reserved-external",
        ):
            self.assertIn(token, help_text + policy_text)


if __name__ == "__main__":
    unittest.main()
