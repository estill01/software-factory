#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

FACTORY_TEST_SUPPORT_PATH = Path(__file__).with_name("test_factory_evolution.py")
FACTORY_TEST_SUPPORT_SPEC = importlib.util.spec_from_file_location(
    "factory_evolution_test_support", FACTORY_TEST_SUPPORT_PATH
)
assert (
    FACTORY_TEST_SUPPORT_SPEC is not None
    and FACTORY_TEST_SUPPORT_SPEC.loader is not None
)
factory_test_support = importlib.util.module_from_spec(FACTORY_TEST_SUPPORT_SPEC)
FACTORY_TEST_SUPPORT_SPEC.loader.exec_module(factory_test_support)


class FactoryEvolutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = HELPER_PATH.parent.parent.joinpath(
            "references", "factory-evolution-contract.md"
        ).read_text(encoding="utf-8")

    def test_reports_nominate_hypotheses_but_canonical_evidence_adjudicates(self) -> None:
        normalized = " ".join(self.contract.split()).lower()

        self.assertIn("canonical event records", normalized)
        self.assertIn("directly observed outcomes", normalized)
        self.assertIn("reports nominate hypotheses", normalized)
        self.assertIn("do not become authority", normalized)
        self.assertIn("not sufficient promotion evidence", normalized)

    def test_contract_preserves_positive_and_negative_pattern_learning(self) -> None:
        normalized = " ".join(self.contract.split()).lower()

        self.assertIn("productive patterns", normalized)
        self.assertIn("harmful patterns", normalized)
        self.assertIn("avoided regressions", normalized)
        self.assertIn("conflicting observations remain visible", normalized)
        self.assertIn("a lesson is not a control", normalized)
        self.assertIn("not itself a capability", normalized)

    def test_candidate_space_is_broader_than_detectors_and_controls(self) -> None:
        for candidate_type in (
            "authoring guidance",
            "architecture, interface, or ownership-boundary change",
            "removal, simplification, or lower-power substitution",
            "experiment or evaluation capability",
            "detector, control, or enforcement mechanism",
        ):
            self.assertIn(candidate_type, self.contract)

    def test_candidate_admission_has_evidence_and_counterexample_floor(self) -> None:
        normalized = " ".join(self.contract.split()).lower()

        self.assertIn("at least one exact, hash-bound supporting source", normalized)
        self.assertIn("known counterexamples or a documented counterexample search", normalized)
        self.assertIn("single instance may nominate a candidate", normalized)
        self.assertIn("cannot by itself establish broad applicability", normalized)

    def test_candidate_cannot_self_promote(self) -> None:
        normalized = " ".join(self.contract.split()).lower()

        self.assertIn("cannot promote itself", normalized)
        self.assertIn("evaluator must be independent", normalized)
        for disposition in ("`promote`", "`advisory`", "`revise`", "`reject`"):
            self.assertIn(disposition, self.contract)
        self.assertIn("not permission for autonomous edits", normalized)

    def test_target_product_alignment_is_seeded_not_preapproved(self) -> None:
        normalized = " ".join(self.contract.split()).lower()

        self.assertIn("first seeded capability candidate", normalized)
        self.assertIn("does not pre-approve promotion", normalized)
        self.assertIn("independent-evaluation gates", normalized)

    def test_skill_and_policy_separate_evolution_roles_and_authority(self) -> None:
        skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        for text in (skill, policy):
            normalized = " ".join(text.split()).lower()
            self.assertIn("reports nominate hypotheses", normalized)
            self.assertIn("observed outcomes adjudicate", normalized)
            self.assertIn("gpt-5.6-sol", normalized)
            self.assertIn("existing", normalized)
            self.assertIn("independent", normalized)
            self.assertIn("not automatic", normalized)
            self.assertIn("target", normalized)
        self.assertIn("prepare → finalize → evaluate → verify", policy)
        self.assertIn("scripts/supervision_log.py", skill)
        self.assertIn("immutable-or-identical", skill)
        self.assertIn("uv run --python 3.14 python", skill)
        self.assertIn("Python 3.11+", skill)
        self.assertIn("gpt-5.6-sol", skill)
        self.assertIn(
            "no implementation or target-write action", " ".join(policy.split())
        )
        self.assertIn("## Exact submission wire shapes", self.contract)
        self.assertIn("result_without_root", self.contract)
        self.assertIn("`schema_version` is the JSON integer `1`", self.contract)
        self.assertIn("`skill-method`", self.contract)
        self.assertIn("`non-inferiority`", self.contract)
        self.assertIn("`observed`, `shadow`, or `synthetic`", self.contract)


class FactoryEvolutionCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = factory_test_support.EvolutionReviewTests(
            methodName="test_review_can_identify_a_broad_capability_gap"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target_thread = "target-test"
        self.evolution_id = "evolution-test"

    def args(self, action: str, **overrides: object) -> argparse.Namespace:
        values: dict[str, object] = {
            "root": str(self.root),
            "target_thread": self.target_thread,
            "evolution_id": self.evolution_id,
            "action": action,
            "report_paths": [],
            "event_paths": [],
            "review_json": None,
            "evaluation_json": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def run_action(self, action: str, **overrides: object) -> dict[str, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_factory_evolution(self.args(action, **overrides))
        return json.loads(output.getvalue())

    @property
    def artifact_directory(self) -> Path:
        return (
            self.root
            / self.target_thread
            / "learning"
            / "factory-evolution"
            / self.evolution_id
        )

    def prepare(self) -> dict[str, object]:
        return self.run_action(
            "prepare",
            report_paths=[str(self.fixture.root / "report.json")],
            event_paths=[str(self.fixture.root / "events.jsonl")],
        )

    def finalize(self) -> tuple[dict[str, object], Path]:
        review_path = self.root / "review-submission.json"
        review_path.write_text(
            json.dumps(self.fixture.review_submission(), sort_keys=True),
            encoding="utf-8",
        )
        return self.run_action("finalize", review_json=str(review_path)), review_path

    def evaluate(self) -> tuple[dict[str, object], Path]:
        review = json.loads(
            (self.artifact_directory / "review.json").read_text(encoding="utf-8")
        )
        evaluation_path = self.root / "evaluation-submission.json"
        evaluation_path.write_text(
            json.dumps(self.fixture.evaluation_submission(review), sort_keys=True),
            encoding="utf-8",
        )
        return (
            self.run_action("evaluate", evaluation_json=str(evaluation_path)),
            evaluation_path,
        )

    def test_full_workflow_is_ordered_verifiable_and_idempotent(self) -> None:
        prepared = self.prepare()
        finalized, review_path = self.finalize()
        evaluated, evaluation_path = self.evaluate()
        verified = self.run_action("verify")

        self.assertEqual(prepared["stage"], "prepared")
        self.assertEqual(finalized["stage"], "finalized")
        self.assertEqual(evaluated["stage"], "evaluated")
        self.assertEqual(evaluated["disposition"], "promote")
        self.assertEqual(verified["stage"], "evaluated")
        self.assertEqual(
            set(item.name for item in self.artifact_directory.glob("*.json")),
            {
                "learning-packet.json",
                "prepare-manifest.json",
                "review.json",
                "finalize-manifest.json",
                "evaluation.json",
                "machine-report.json",
                "manifest.json",
            },
        )
        self.assertFalse((self.root / self.target_thread / "events.jsonl").exists())
        self.assertFalse((self.root / self.target_thread / "policy.json").exists())

        reused_prepare = self.prepare()
        reused_finalize = self.run_action(
            "finalize", review_json=str(review_path)
        )
        reused_evaluate = self.run_action(
            "evaluate", evaluation_json=str(evaluation_path)
        )
        self.assertEqual(reused_prepare["written"], [])
        self.assertEqual(reused_finalize["written"], [])
        self.assertEqual(reused_evaluate["written"], [])

    def test_finalize_before_prepare_is_rejected(self) -> None:
        review_path = self.root / "review.json"
        review_path.write_text("{}\n", encoding="utf-8")

        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "out of order"):
            self.run_action("finalize", review_json=str(review_path))

    def test_changed_content_under_existing_id_is_rejected(self) -> None:
        self.prepare()
        changed = json.loads(
            (self.fixture.root / "report.json").read_text(encoding="utf-8")
        )
        changed["cognitive_review"]["headline"] = "Changed derivative hypothesis."
        changed_path = self.root / "changed-report.json"
        changed_path.write_text(json.dumps(changed, sort_keys=True), encoding="utf-8")

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Existing factory evolution artifact differs",
        ):
            self.run_action(
                "prepare",
                report_paths=[str(changed_path)],
                event_paths=[str(self.fixture.root / "events.jsonl")],
            )

    def test_command_rejects_unsafe_identity_and_has_no_promotion_action(self) -> None:
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "Invalid"):
            supervision_log.factory_evolution_directory(
                self.root, "../escape"
            )

        action = next(
            item
            for item in supervision_log.parser()._actions
            if isinstance(item, argparse._SubParsersAction)
        ).choices["factory-evolution"]._option_string_actions["--action"].choices
        self.assertEqual(tuple(action), ("prepare", "finalize", "evaluate", "verify"))

    def test_nested_owner_symlink_escape_is_rejected(self) -> None:
        target = self.root / self.target_thread
        learning = target / "learning"
        outside = self.root / "outside-owner"
        learning.mkdir(parents=True)
        outside.mkdir()
        (learning / "factory-evolution").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "escaped the target directory"
        ):
            self.prepare()
        self.assertFalse((outside / self.evolution_id / "learning-packet.json").exists())

    def test_verify_rejects_unexpected_artifacts_in_the_set(self) -> None:
        self.prepare()
        self.finalize()
        self.evaluate()
        (self.artifact_directory / "promotion.json").write_text(
            "{}\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "unexpected artifacts"
        ):
            self.run_action("verify")


class UserFacingBlockSummaryPolicyTests(unittest.TestCase):
    def test_skill_requires_self_contained_block_purpose(self) -> None:
        skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Block purpose — Block <N>:", skill)
        self.assertIn("do not expect the operator to open the tracker", skill)
        self.assertIn("each materially discussed Block", skill)

    def test_notification_roles_require_bounded_plain_language_context(self) -> None:
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        self.assertIn("normally no more than 40 words", policy)
        self.assertIn("operator must be able to understand", policy)
        self.assertIn("heading, Objective, and Stop", policy)
        self.assertGreaterEqual(policy.count("Block purpose — Block <N>"), 6)
        for heading in (
            "## Notice-reviewer role prompt",
            "## Gmail reply-processor role prompt",
            "## Roundup-writer role prompt",
            "## Watcher role prompt",
            "## Reviewer role prompt",
            "## Meta-review heartbeat prompt",
        ):
            self.assertIn(heading, policy)

    def test_generic_mission_charter_contract_is_documented_without_overclaim(self) -> None:
        skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        for text in (skill, policy):
            self.assertIn("mission-plan", text)
            self.assertIn("generic completion meta-charter", text)
            self.assertIn("unsupported goal-preventing stop", text)
        self.assertIn("observable outcome", skill.lower())
        self.assertIn("observable completion", policy.lower())
        self.assertIn("not every pause", skill)
        self.assertIn(
            "not automatically catastrophic",
            " ".join(policy.split()),
        )

    def test_terminal_outcome_gate_is_durable_in_both_skills(self) -> None:
        supervision_skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        implementation_skill = HELPER_PATH.parent.parent.parent.joinpath(
            "implement-tracker-blocks", "SKILL.md"
        ).read_text(encoding="utf-8")
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Bind observable outcome closure", implementation_skill)
        self.assertIn("created-current", implementation_skill)
        self.assertIn("ready to merge only", implementation_skill)
        self.assertIn("completion-record", supervision_skill)
        self.assertIn("completion_permitted=true", supervision_skill)
        self.assertIn("terminal-report", supervision_skill)
        self.assertIn("supervision_pause_permitted=true", supervision_skill)
        self.assertIn("terminal-shutdown", supervision_skill)
        self.assertIn("operator-visible result", policy)
        self.assertIn("rejects a completed lifecycle", policy)
        self.assertIn("terminal-report prepare", policy)
        self.assertIn("report of\nreports", policy)
        self.assertIn("both verified PDFs attached", policy)

    def test_terminal_capability_reconciliation_is_documented_end_to_end(
        self,
    ) -> None:
        supervision_skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        readme = HELPER_PATH.parent.parent.parent.joinpath("README.md").read_text(
            encoding="utf-8"
        )
        reconciliation_contract = HELPER_PATH.parent.parent.joinpath(
            "references", "terminal-capability-reconciliation.md"
        ).read_text(encoding="utf-8")

        required_concepts = (
            "requested capability",
            "protected capabilities",
            "selected architecture level",
            "accepted tradeoffs",
            "current behavior",
            "operator-visible effects",
        )
        for text in (supervision_skill, policy):
            for concept in required_concepts:
                self.assertIn(concept, text)
            self.assertIn("reopen only the narrow", text)
        self.assertIn("evolution disposition", supervision_skill)
        self.assertIn("populated artifacts", policy)
        self.assertIn("reopen only the narrow owner", readme)
        self.assertIn("--capability-reconciliation-json", supervision_skill)
        self.assertIn("--capability-reconciliation-json", policy)
        for evidence_class in (
            "direct-authority",
            "current-repository",
            "observed-outcome",
        ):
            self.assertIn(evidence_class, reconciliation_contract)
        self.assertIn('"owner_class"', reconciliation_contract)
        self.assertIn("source JSON remains caller-owned", policy)


class SuccessorTransitionContractTests(unittest.TestCase):
    target = "target-1234"
    transition_id = "TRANSITION-1234"
    tracker_sha256 = "a" * 64
    source_mission_root = "b" * 64
    successor_mission_root = "c" * 64

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.policy = {"policy_sha256": "d" * 64}

    def transition_args(self, phase: str, *extra: str) -> argparse.Namespace:
        return supervision_log.parser().parse_args(
            [
                "successor-transition-record",
                "--target-thread",
                self.target,
                "--transition-id",
                self.transition_id,
                "--phase",
                phase,
                "--tracker-sha256",
                self.tracker_sha256,
                "--tracker-source-record",
                "commit-94c8118-blob-9e6b6d1",
                "--requested-block-range",
                "Blocks 0-13",
                "--first-eligible-block",
                "Block 0",
                "--source-mission-root",
                self.source_mission_root,
                "--governing-authority-source-class",
                "direct-user",
                "--governing-authority-source-record",
                "item-340",
                "--state-fingerprint",
                f"state-{phase}",
                "--evidence",
                f"evidence-{phase}",
                *extra,
            ]
        )

    def record(self, phase: str, *extra: str) -> dict[str, object]:
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(self.directory, self.policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_successor_transition_record(
                self.transition_args(phase, *extra)
            )
        return json.loads(output.getvalue())

    def gate(self, authority: str = "unavailable") -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "successor-transition-gate",
                "--target-thread",
                self.target,
                "--transition-id",
                self.transition_id,
                "--task-creation-authority",
                authority,
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(self.directory, self.policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_successor_transition_gate(args)
        return json.loads(output.getvalue())

    def test_transition_remains_open_until_successor_work_actually_starts(self) -> None:
        self.record("required")

        unavailable = self.gate()
        available = self.gate("available")
        self.assertFalse(unavailable["source_stop_permitted"])
        self.assertTrue(unavailable["direct_task_creation_authority_required"])
        self.assertEqual(
            unavailable["next_action"],
            "keep-open-await-direct-task-creation-authority",
        )
        self.assertEqual(available["next_action"], "create-successor-task")

        successor = ["--successor-thread", "successor-1234"]
        bound = [
            *successor,
            "--successor-mission-root",
            self.successor_mission_root,
            "--successor-group-id",
            "group-1234",
        ]
        handed_off = [*bound, "--handoff-record", "HANDOFF-1234"]
        acknowledged = [
            *handed_off,
            "--acknowledgement-record",
            "ACK-1234",
        ]
        self.record("successor-created", *successor)
        self.record("successor-bound", *bound)
        self.record("handoff-sent", *handed_off)
        self.record("target-acknowledged", *acknowledged)

        before_start = self.gate()
        self.assertFalse(before_start["source_stop_permitted"])
        self.assertEqual(before_start["next_action"], "start-first-eligible-block")

        self.record("work-started", *acknowledged, "--started-block", "Block 0")
        started = self.gate()
        self.assertTrue(started["source_stop_permitted"])
        self.assertFalse(started["transition_open"])

    def test_transition_rejects_skips_identity_drift_and_early_claims(self) -> None:
        self.record("required")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "is not allowed"
        ):
            self.record(
                "successor-bound",
                "--successor-thread",
                "successor-1234",
                "--successor-mission-root",
                self.successor_mission_root,
                "--successor-group-id",
                "group-1234",
            )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "cannot claim later"
        ):
            self.record(
                "successor-created",
                "--successor-thread",
                "successor-1234",
                "--handoff-record",
                "HANDOFF-1234",
            )

        created = self.transition_args(
            "successor-created", "--successor-thread", "successor-1234"
        )
        created.tracker_sha256 = "e" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "preserve tracker sha256"
        ):
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_successor_transition_record(created)

    def test_routed_provenance_cannot_create_governing_transition_authority(self) -> None:
        args = self.transition_args("required")
        args.governing_authority_source_class = "codex_delegation"
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "governing direct authority"
        ):
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_successor_transition_record(args)

    def test_completed_lifecycle_is_rejected_while_transition_is_open(self) -> None:
        self.record("required")
        args = supervision_log.parser().parse_args(
            [
                "record",
                "--target-thread",
                self.target,
                "--kind",
                "lifecycle",
                "--status",
                "completed",
                "--state-fingerprint",
                "state-required",
                "--summary",
                "Incorrectly claimed completion after handoff.",
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "open successor transition"
        ):
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_record(args)

    def test_lifecycle_and_status_expose_the_open_transition(self) -> None:
        self.record("required")
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": "EVT-000002",
                "timestamp": "2026-08-08T18:00:00+00:00",
                "target_thread_id": self.target,
                "kind": "lifecycle",
                "status": "paused",
                "state_fingerprint": "state-required",
                "user_action_required": "no",
            },
        )
        lifecycle_args = supervision_log.parser().parse_args(
            [
                "lifecycle-gate",
                "--target-thread",
                self.target,
                "--lifecycle-state",
                "paused",
                "--source-record",
                "EVT-000002",
            ]
        )
        status_args = supervision_log.parser().parse_args(
            ["status", "--target-thread", self.target]
        )
        with mock.patch.object(
            supervision_log,
            "load_policy",
            return_value=(self.directory, self.policy),
        ):
            lifecycle_output = io.StringIO()
            with redirect_stdout(lifecycle_output):
                supervision_log.cmd_lifecycle_gate(lifecycle_args)
            status_output = io.StringIO()
            with redirect_stdout(status_output):
                supervision_log.cmd_status(status_args)
        lifecycle = json.loads(lifecycle_output.getvalue())
        status = json.loads(status_output.getvalue())

        self.assertFalse(lifecycle["source_stop_permitted"])
        self.assertEqual(lifecycle["completion_action"], "resume-successor-transition")
        self.assertEqual(status["successor_transition_count"], 1)
        self.assertEqual(len(status["open_successor_transitions"]), 1)

    def test_incident_can_store_a_structured_failure_mode_taxonomy(self) -> None:
        args = supervision_log.parser().parse_args(
            [
                "record",
                "--target-thread",
                self.target,
                "--kind",
                "incident",
                "--category",
                "goal-preventing-procedural-stop",
                "--summary",
                "A task boundary was mistaken for outcome completion.",
                "--failure-mode",
                "--failure-mode-id",
                "FM-HANDOFF-WITHOUT-CONTINUATION",
                "--failure-layer",
                "control-plane",
                "--failure-mechanism",
                "Boundary conflation",
                "--failure-trigger",
                "Execution required a successor task.",
                "--failure-effect",
                "The requested implementation did not start.",
                "--failure-detection",
                "Source stopped while successor transition gate was false.",
                "--failure-correction",
                "Keep source active through successor work-started evidence.",
                "--failure-recurrence-invariant",
                "Handoff is not completion.",
                "--failure-human-scheduling-leak",
                "yes",
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(self.directory, self.policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_record(args)
        record = json.loads(output.getvalue())["record"]
        self.assertEqual(record["failure_mode"]["layer"], "control-plane")
        self.assertTrue(record["failure_mode"]["human_scheduling_leak"])
        incident = next((self.directory / "incidents").glob("*.md"))
        self.assertIn("Failure Mode", incident.read_text(encoding="utf-8"))

    def test_transition_and_failure_mode_contracts_are_documented_end_to_end(self) -> None:
        supervision_skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        implementation_skill = HELPER_PATH.parent.parent.parent.joinpath(
            "implement-tracker-blocks", "SKILL.md"
        ).read_text(encoding="utf-8")
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        readme = HELPER_PATH.parent.parent.parent.joinpath("README.md").read_text(
            encoding="utf-8"
        )

        for text in (supervision_skill, implementation_skill, policy):
            self.assertIn("successor-transition-gate", text)
            self.assertIn("source_stop_permitted", text)
            self.assertIn("work-started", text)
            self.assertIn("handoff", text.lower())
        self.assertIn("--failure-mode", supervision_skill)
        self.assertIn("FM-HANDOFF-WITHOUT-CONTINUATION", policy)
        self.assertIn("handoff is not completion", policy.lower())
        self.assertIn("human-scheduling leak", readme)


class ReusableLaneDispositionTests(unittest.TestCase):
    target = "target-economy-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.policy = {
            "policy_sha256": "e" * 64,
            "execution_economy": supervision_log.execution_economy_contract(),
        }
        self.sequence = 0

    def run_record(self, arguments: list[str]) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["record", "--target-thread", self.target, *arguments]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(self.directory, self.policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_record(args)
        return json.loads(output.getvalue())

    def open_failure_mode(
        self,
        *,
        category: str = "execution-economy-invocation",
        layer: str = "execution",
        failure_mode_id: str = "FM-INVOCATION-ENVELOPE-MAINTENANCE-OMISSION",
    ) -> str:
        self.sequence += 1
        result = self.run_record(
            [
                "--kind",
                "incident",
                "--category",
                category,
                "--summary",
                "A maintained invocation envelope was incomplete.",
                "--dedup-key",
                f"economy-episode-{self.sequence}",
                "--failure-mode",
                "--failure-mode-id",
                failure_mode_id,
                "--failure-layer",
                layer,
                "--failure-mechanism",
                "The outer launcher was omitted from setup proof.",
                "--failure-trigger",
                "A repository-owned focused command was first invoked.",
                "--failure-effect",
                "The first proof invocation failed before test collection.",
                "--failure-detection",
                "The exact maintained command chain was incomplete.",
                "--failure-correction",
                "Resolve and reuse the complete repository-owned envelope.",
                "--failure-recurrence-invariant",
                "Every invoked launcher belongs to the frozen envelope.",
                "--failure-human-scheduling-leak",
                "no",
            ]
        )
        return str(result["record"]["incident_id"])

    def closure_arguments(self, incident_id: str, *extra: str) -> list[str]:
        return [
            "--kind",
            "resolution",
            "--incident-id",
            incident_id,
            "--status",
            "corrected",
            "--notice-disposition",
            "terminal",
            "--summary",
            "The current-run correction was effective.",
            *extra,
        ]

    def test_execution_economy_closure_requires_an_explicit_disposition(self) -> None:
        incident_id = self.open_failure_mode(category="runtime-invocation")

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an explicit reusable lane disposition",
        ):
            self.run_record(self.closure_arguments(incident_id))

    def test_observing_resolution_defers_reusable_lane_until_effectiveness(self) -> None:
        incident_id = self.open_failure_mode(category="runtime-invocation")
        observing = self.run_record(
            [
                "--kind",
                "resolution",
                "--incident-id",
                incident_id,
                "--status",
                "observing",
                "--notice-disposition",
                "correction-issued",
                "--summary",
                "The current-run correction awaits effectiveness evidence.",
            ]
        )

        self.assertEqual(observing["record"]["status"], "observing")
        self.assertNotIn("reusable_lane", observing["record"])

        effective_arguments = [
            "--kind",
            "resolution",
            "--incident-id",
            incident_id,
            "--status",
            "effective",
            "--notice-disposition",
            "correction-issued",
            "--summary",
            "The current-run correction is now effective.",
        ]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an explicit reusable lane disposition",
        ):
            self.run_record(effective_arguments)

        effective = self.run_record(
            [
                *effective_arguments,
                "--reusable-lane-disposition",
                "existing-owner-sufficient",
                "--reusable-lane-owner",
                "implement-tracker-blocks",
                "--reusable-lane-evidence",
                "EVT-001182",
            ]
        )
        self.assertEqual(effective["record"]["status"], "effective")
        self.assertEqual(
            effective["record"]["reusable_lane"]["disposition"],
            "existing-owner-sufficient",
        )

    def test_effectiveness_finding_also_requires_the_disposition(self) -> None:
        incident_id = self.open_failure_mode(failure_mode_id="FM-OTHER-EXECUTION")
        arguments = [
            "--kind",
            "meta-review",
            "--incident-id",
            incident_id,
            "--status",
            "effective",
            "--summary",
            "The correction stopped the current waste.",
        ]

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an explicit reusable lane disposition",
        ):
            self.run_record(arguments)

        arguments[arguments.index("effective")] = "observing"
        result = self.run_record(arguments)
        self.assertEqual(result["record"]["status"], "observing")

    def test_candidate_and_existing_owner_require_exact_owner_evidence(self) -> None:
        for disposition in ("candidate-opened", "existing-owner-sufficient"):
            with self.subTest(disposition=disposition):
                incident_id = self.open_failure_mode()
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "requires an owner and evidence",
                ):
                    self.run_record(
                        self.closure_arguments(
                            incident_id,
                            "--reusable-lane-disposition",
                            disposition,
                            "--reusable-lane-owner",
                            "implement-tracker-blocks",
                        )
                    )

                result = self.run_record(
                    self.closure_arguments(
                        incident_id,
                        "--reusable-lane-disposition",
                        disposition,
                        "--reusable-lane-owner",
                        "implement-tracker-blocks",
                        "--reusable-lane-evidence",
                        "EVT-001171",
                    )
                )
                lane = result["record"]["reusable_lane"]
                self.assertEqual(lane["disposition"], disposition)
                self.assertEqual(lane["owner"], "implement-tracker-blocks")
                self.assertEqual(lane["evidence"], ["EVT-001171"])

    def test_not_applicable_and_pending_require_bounded_explanations(self) -> None:
        incident_id = self.open_failure_mode()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires rationale",
        ):
            self.run_record(
                self.closure_arguments(
                    incident_id,
                    "--reusable-lane-disposition",
                    "repository-specific-not-applicable",
                )
            )
        result = self.run_record(
            self.closure_arguments(
                incident_id,
                "--reusable-lane-disposition",
                "repository-specific-not-applicable",
                "--reusable-lane-rationale",
                "The defect is confined to a repository-owned launcher.",
            )
        )
        self.assertEqual(
            result["record"]["reusable_lane"]["disposition"],
            "repository-specific-not-applicable",
        )

        pending_id = self.open_failure_mode()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires rationale and a next evidence trigger",
        ):
            self.run_record(
                self.closure_arguments(
                    pending_id,
                    "--reusable-lane-disposition",
                    "evidence-pending",
                    "--reusable-lane-rationale",
                    "A second supported episode has not been adjudicated.",
                )
            )
        pending = self.run_record(
            self.closure_arguments(
                pending_id,
                "--reusable-lane-disposition",
                "evidence-pending",
                "--reusable-lane-rationale",
                "A second supported episode has not been adjudicated.",
                "--reusable-lane-evidence",
                "next-trigger:second-adjudicated-episode",
            )
        )
        self.assertEqual(
            pending["record"]["reusable_lane"]["evidence"],
            ["next-trigger:second-adjudicated-episode"],
        )

    def test_non_economy_failure_mode_preserves_existing_closure_behavior(self) -> None:
        incident_id = self.open_failure_mode(
            category="goal-preventing-procedural-stop",
            layer="control-plane",
            failure_mode_id="FM-HANDOFF-WITHOUT-CONTINUATION",
        )

        result = self.run_record(self.closure_arguments(incident_id))

        self.assertEqual(result["record"]["status"], "corrected")
        self.assertNotIn("reusable_lane", result["record"])

    def test_exact_legacy_policy_defers_enforcement_until_bind_upgrade(self) -> None:
        self.policy["execution_economy"] = (
            supervision_log.legacy_execution_economy_contract_without_reusable_lane()
        )
        incident_id = self.open_failure_mode()

        result = self.run_record(self.closure_arguments(incident_id))

        self.assertEqual(result["record"]["status"], "corrected")
        self.assertNotIn("reusable_lane", result["record"])

    def test_contract_is_documented_in_skill_policy_and_cli(self) -> None:
        skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        for text in (skill, policy):
            for disposition in supervision_log.REUSABLE_LANE_DISPOSITIONS:
                self.assertIn(disposition, text)
            self.assertIn("reusable lane", text.lower())
        parsed = supervision_log.parser().parse_args(
            [
                "record",
                "--target-thread",
                self.target,
                "--kind",
                "resolution",
                "--incident-id",
                "INC-TEST-1234",
                "--summary",
                "CLI schema probe.",
                "--reusable-lane-disposition",
                "candidate-opened",
                "--reusable-lane-owner",
                "implement-tracker-blocks",
                "--reusable-lane-evidence",
                "EVT-001171",
            ]
        )
        self.assertEqual(parsed.reusable_lane_disposition, "candidate-opened")


class NoticeGateCorrelationTests(unittest.TestCase):
    incident_id = "INC-20260801-123456-ABCDEF"
    alert_source = "EVT-000001"
    terminal_source = "EVT-000002"

    def run_terminal_gate(
        self,
        event_records: list[dict[str, object]],
        source_record: str | None = None,
        notice_disposition: str = "terminal",
        user_action_required: str = "no",
        severity: str = "info",
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            incidents = directory / "incidents"
            incidents.mkdir()
            (incidents / f"{self.incident_id}.md").write_text(
                "# Test incident\n", encoding="utf-8"
            )
            args = argparse.Namespace(
                incident_id=self.incident_id,
                source_record=source_record or self.terminal_source,
                notice_disposition=notice_disposition,
                resolution_owner="none",
                user_action_required=user_action_required,
                severity=severity,
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

    def run_status(self, event_records: list[dict[str, object]]) -> dict[str, object]:
        output = io.StringIO()
        args = argparse.Namespace(target_thread="target-1234")
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(
                    Path("/tmp/test-supervision"),
                    {"policy_sha256": "test-policy"},
                ),
            ),
            mock.patch.object(supervision_log, "events", return_value=event_records),
            redirect_stdout(output),
        ):
            supervision_log.cmd_status(args)
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

    def test_later_terminal_source_is_suppressed_without_substantive_reopen(self) -> None:
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
                    "incident_id": self.incident_id,
                    "category": "gmail",
                    "status": "sent",
                    "notice_disposition": "terminal",
                    "dedup_key": f"gmail:{self.terminal_source}",
                    "evidence": [self.terminal_source, "gmail-outcome-id"],
                },
                {
                    "kind": "resolution",
                    "record_id": "EVT-000005",
                    "incident_id": self.incident_id,
                    "status": "closed",
                    "notice_disposition": "terminal",
                },
            ]
        )

        result = self.run_terminal_gate(records, source_record="EVT-000005")

        self.assertTrue(result["previously_alerted"])
        self.assertTrue(result["duplicate"])
        self.assertFalse(result["send_now"])
        self.assertEqual(result["channel"], "none")
        self.assertIsNone(result["banner"])

    def test_substantive_nonterminal_reopen_allows_new_terminal_outcome(self) -> None:
        records = self.incident_records()
        records.extend(
            [
                {
                    "kind": "notification",
                    "record_id": "EVT-000003",
                    "incident_id": self.incident_id,
                    "category": "gmail",
                    "status": "sent",
                    "notice_disposition": "terminal",
                    "dedup_key": f"gmail:{self.terminal_source}",
                    "evidence": [self.terminal_source, "gmail-outcome-id"],
                },
                {
                    "kind": "resolution",
                    "record_id": "EVT-000004",
                    "incident_id": self.incident_id,
                    "status": "awaiting-target-evidence",
                    "notice_disposition": "intermediate",
                },
                {
                    "kind": "resolution",
                    "record_id": "EVT-000005",
                    "incident_id": self.incident_id,
                    "status": "corrected",
                    "notice_disposition": "terminal",
                },
            ]
        )

        result = self.run_terminal_gate(records, source_record="EVT-000005")

        self.assertTrue(result["previously_alerted"])
        self.assertFalse(result["duplicate"])
        self.assertTrue(result["send_now"])
        self.assertEqual(result["channel"], "primary-outcome")
        self.assertEqual(result["banner"], "SUPERVISION OUTCOME")

    def test_terminal_head_ignores_later_routing_only_escalations(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "corrected",
                "notice_disposition": "terminal",
            },
            {
                "kind": "notification",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "gmail",
                "status": "sent",
                "notice_disposition": "terminal",
                "evidence": [self.terminal_source, "gmail-outcome-id"],
            },
            {
                "kind": "escalation",
                "record_id": "EVT-000004",
                "incident_id": self.incident_id,
                "category": "incident-routing",
                "status": "routed",
            },
            {
                "kind": "escalation",
                "record_id": "EVT-000005",
                "incident_id": self.incident_id,
                "category": "notice-review",
                "status": "routed",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["open_incident_ids"], [])
        self.assertEqual(result["open_incidents"], [])

    def test_resolved_terminal_head_is_not_open(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "check",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "resolved",
                "notice_disposition": "terminal",
            },
            {
                "kind": "notification",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "gmail",
                "status": "sent",
                "evidence": [self.terminal_source, "gmail-outcome-id"],
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["open_incident_ids"], [])
        self.assertEqual(result["open_incidents"], [])

    def test_resolved_status_is_terminal_without_notice_disposition(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "resolved",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["open_incident_ids"], [])
        self.assertEqual(result["open_incidents"], [])

    def test_substantive_nonterminal_head_reopens_status(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "resolved",
                "notice_disposition": "terminal",
            },
            {
                "kind": "check",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "intermediate",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["open_incident_ids"], [self.incident_id])
        self.assertEqual(result["open_incidents"], [records[-1]])

    def test_target_read_availability_preserves_awaiting_evidence_head(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "correction-issued",
            },
            {
                "kind": "check",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "target-read-availability",
                "status": "unavailable",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["event_count"], len(records))
        self.assertEqual(result["open_incident_ids"], [self.incident_id])
        self.assertEqual(result["open_incidents"], [records[1]])

    def test_target_read_availability_does_not_reopen_terminal_head(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "corrected",
                "notice_disposition": "terminal",
            },
            {
                "kind": "check",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "target-read-availability",
                "status": "unavailable",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["event_count"], len(records))
        self.assertEqual(result["open_incident_ids"], [])
        self.assertEqual(result["open_incidents"], [])

    def test_substantive_reopen_after_target_read_availability_is_head(self) -> None:
        records = [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "resolution",
                "record_id": self.terminal_source,
                "incident_id": self.incident_id,
                "status": "corrected",
                "notice_disposition": "terminal",
            },
            {
                "kind": "check",
                "record_id": "EVT-000003",
                "incident_id": self.incident_id,
                "category": "target-read-availability",
                "status": "unavailable",
            },
            {
                "kind": "resolution",
                "record_id": "EVT-000004",
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "intermediate",
            },
        ]

        result = self.run_status(records)

        self.assertEqual(result["event_count"], len(records))
        self.assertEqual(result["open_incident_ids"], [self.incident_id])
        self.assertEqual(result["open_incidents"], [records[-1]])

    def correction_records(
        self,
        *,
        current_fingerprint: str = "state-1234",
        receipt_status: str = "sent",
        receipt_has_incident_id: bool = True,
    ) -> list[dict[str, object]]:
        receipt: dict[str, object] = {
            "kind": "notification",
            "record_id": "EVT-000003",
            "category": "gmail",
            "status": receipt_status,
            "dedup_key": "gmail:EVT-000002",
            "evidence": ["EVT-000002", "gmail-correction-id"],
        }
        if receipt_has_incident_id:
            receipt["incident_id"] = self.incident_id
        return [
            {
                "kind": "incident",
                "record_id": self.alert_source,
                "incident_id": self.incident_id,
                "status": "detected",
            },
            {
                "kind": "steer",
                "record_id": "EVT-000002",
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "correction-issued",
                "state_fingerprint": "state-1234",
            },
            receipt,
            {
                "kind": "resolution",
                "record_id": "EVT-000004",
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "correction-issued",
                "state_fingerprint": current_fingerprint,
            },
        ]

    def test_same_fingerprint_correction_receipt_suppresses_second_email(self) -> None:
        for receipt_has_incident_id in (False, True):
            with self.subTest(receipt_has_incident_id=receipt_has_incident_id):
                records = self.correction_records(
                    receipt_has_incident_id=receipt_has_incident_id
                )

                result = self.run_terminal_gate(
                    records,
                    source_record="EVT-000004",
                    notice_disposition="correction-issued",
                )

                self.assertTrue(result["previously_alerted"])
                self.assertTrue(result["duplicate"])
                self.assertFalse(result["send_now"])
                self.assertEqual(result["channel"], "none")
                self.assertIsNone(result["banner"])

    def test_changed_fingerprint_correction_remains_eligible(self) -> None:
        records = self.correction_records(current_fingerprint="state-5678")

        result = self.run_terminal_gate(
            records,
            source_record="EVT-000004",
            notice_disposition="correction-issued",
        )

        self.assertFalse(result["duplicate"])
        self.assertTrue(result["send_now"])
        self.assertEqual(result["channel"], "primary-immediate")

    def test_intervening_new_steer_keeps_correction_outcome_eligible(self) -> None:
        records = self.correction_records()
        records.insert(
            -1,
            {
                "kind": "steer",
                "record_id": "EVT-000003B",
                "incident_id": self.incident_id,
                "status": "awaiting-target-evidence",
                "notice_disposition": "correction-issued",
                "state_fingerprint": "state-1234",
            },
        )

        result = self.run_terminal_gate(
            records,
            source_record="EVT-000004",
            notice_disposition="correction-issued",
        )

        self.assertFalse(result["duplicate"])
        self.assertTrue(result["send_now"])
        self.assertEqual(result["channel"], "primary-immediate")

    def test_critical_or_user_action_correction_remains_eligible(self) -> None:
        for severity, user_action_required in (("critical", "no"), ("info", "yes")):
            with self.subTest(
                severity=severity, user_action_required=user_action_required
            ):
                result = self.run_terminal_gate(
                    self.correction_records(),
                    source_record="EVT-000004",
                    notice_disposition="correction-issued",
                    severity=severity,
                    user_action_required=user_action_required,
                )

                self.assertFalse(result["duplicate"])
                self.assertTrue(result["send_now"])
                self.assertEqual(result["channel"], "primary-immediate")

    def test_failed_exact_source_receipt_allows_retry(self) -> None:
        records = self.correction_records(receipt_status="failed")[:-1]

        result = self.run_terminal_gate(
            records,
            source_record="EVT-000002",
            notice_disposition="correction-issued",
        )

        self.assertFalse(result["duplicate"])
        self.assertTrue(result["send_now"])
        self.assertEqual(result["channel"], "primary-immediate")

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
        self.assertTrue(
            policy["execution_economy"][
                "effectiveness_or_closure_requires_reusable_lane_disposition"
            ]
        )
        self.assertEqual(
            policy["execution_economy"]["reusable_lane_dispositions"],
            list(supervision_log.REUSABLE_LANE_DISPOSITIONS),
        )
        self.assertEqual(
            policy["outcome_completion"],
            supervision_log.outcome_completion_contract(),
        )
        self.assertEqual(
            policy["cross_thread_routing"],
            supervision_log.cross_thread_routing_contract(),
        )
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
            current_policy = json.loads(json.dumps(policy))
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log, "load_policy", return_value=(directory, policy)
                ),
                mock.patch.object(
                    supervision_log, "read_json", return_value=current_policy
                ),
                mock.patch.object(supervision_log, "atomic_json"),
                mock.patch.object(supervision_log, "append_raw_locked"),
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
        policy.pop("outcome_completion")
        policy.pop("decision_resolution")
        policy.pop("cross_thread_routing")
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
        self.assertEqual(
            policy["outcome_completion"],
            supervision_log.outcome_completion_contract(),
        )
        self.assertTrue(policy["decision_resolution"]["continuation_first"])
        self.assertEqual(
            policy["cross_thread_routing"],
            supervision_log.cross_thread_routing_contract(),
        )
        self.assertFalse(policy["permissions"]["allowlisted_skill_maintenance"])
        self.assertFalse(policy["permissions"]["gmail_priority_notification"])
        self.assertFalse(policy["notifications"]["gmail_priority"]["enabled"])
        self.assertNotIn("mission_binding", policy)
        write.assert_called_once()

    def test_bind_upgrades_exact_predecessor_completion_contract(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["outcome_completion"] = (
            supervision_log.legacy_outcome_completion_contract_without_capability()
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.validate_policy(policy)
        args = supervision_log.parser().parse_args(
            ["bind", "--target-thread", "target-1234"]
        )

        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(args)

        self.assertEqual(
            policy["outcome_completion"],
            supervision_log.outcome_completion_contract(),
        )
        write.assert_called_once()

    def test_bind_upgrades_intermediate_capability_completion_contract(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["outcome_completion"] = (
            supervision_log.legacy_outcome_completion_contract_with_unvalidated_capability()
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.validate_policy(policy)
        args = supervision_log.parser().parse_args(
            ["bind", "--target-thread", "target-1234"]
        )

        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(args)

        self.assertEqual(
            policy["outcome_completion"],
            supervision_log.outcome_completion_contract(),
        )
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

    def test_bind_upgrades_only_the_exact_predecessor_economy_contract(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["execution_economy"] = (
            supervision_log.legacy_execution_economy_contract_without_reusable_lane()
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        supervision_log.validate_policy(policy)
        changed = supervision_log.ensure_execution_economy_policy(policy)

        self.assertTrue(changed)
        self.assertEqual(
            policy["execution_economy"],
            supervision_log.execution_economy_contract(),
        )

    def test_policy_validation_rejects_outcome_completion_drift(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["outcome_completion"]["process_proxies_sufficient"] = True
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Outcome-completion contract differs",
        ):
            supervision_log.validate_policy(policy)

    def test_policy_validation_rejects_thread_routing_contract_drift(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["cross_thread_routing"]["routine_status_behavior"] = "broadcast"
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Cross-thread routing contract differs",
        ):
            supervision_log.validate_policy(policy)

    def test_policy_validation_accepts_missing_legacy_routing_for_bind_upgrade(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy.pop("cross_thread_routing")
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        supervision_log.validate_policy(policy)


class CrossThreadRoutingGateTests(unittest.TestCase):
    def policy(self) -> dict[str, object]:
        args = argparse.Namespace(
            target_thread="target-1234",
            target_label="target",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread="notice-1234",
            fix_executor_thread="fixer-1234",
        )
        policy = supervision_log.default_policy(args)
        policy["runtime"].update(
            {
                "gmail_processor_thread_id": "gmail-processor-1234",
                "roundup_thread_id": "roundup-1234",
            }
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        return policy

    def route(
        self,
        policy: dict[str, object],
        *,
        recipient: str,
        purpose: str,
        action: str = "Review the exact changed-state packet.",
    ) -> dict[str, object]:
        args = argparse.Namespace(
            target_thread="target-1234",
            recipient_thread=recipient,
            purpose=purpose,
            source_record="EVT-000001",
            action=action,
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_thread_route_gate(args)
        return json.loads(output.getvalue())

    def test_exact_configured_action_owner_is_allowed(self) -> None:
        result = self.route(
            self.policy(),
            recipient="base-1234",
            purpose="changed-state-review",
        )

        self.assertTrue(result["send_allowed"])
        self.assertEqual(result["recipient_role"], "base_reviewer")
        self.assertEqual(result["source_record"], "EVT-000001")

    def test_target_action_is_allowed_without_echoing_action_text(self) -> None:
        action = "Apply the exact bounded correction and report acknowledgement."
        result = self.route(
            self.policy(),
            recipient="target-1234",
            purpose="target-action",
            action=action,
        )

        self.assertTrue(result["send_allowed"])
        self.assertEqual(result["recipient_role"], "target")
        self.assertEqual(result["action_sha256"], supervision_log.digest(action))
        self.assertNotIn(action, json.dumps(result))

    def test_role_refresh_is_limited_to_configured_runtime_roles(self) -> None:
        policy = self.policy()
        recipients = {
            "base-1234": "base_reviewer",
            "fixer-1234": "fix_executor",
            "gmail-processor-1234": "gmail_processor",
            "notice-1234": "notice_reviewer",
            "reviewer-1234": "reviewer",
            "roundup-1234": "roundup_writer",
            "watcher-1234": "watcher",
        }
        for recipient, role in recipients.items():
            with self.subTest(role=role):
                result = self.route(
                    policy,
                    recipient=recipient,
                    purpose="role-refresh",
                    action="Reread the accepted routing policy.",
                )
                self.assertEqual(result["recipient_role"], role)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "purpose does not match",
        ):
            self.route(
                policy,
                recipient="target-1234",
                purpose="role-refresh",
                action="Reread the accepted routing policy.",
            )

    def test_unrelated_side_thread_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not a configured action owner",
        ):
            self.route(
                self.policy(),
                recipient="side-conversation-1234",
                purpose="target-action",
            )

    def test_purpose_must_match_exact_recipient_role(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "purpose does not match",
        ):
            self.route(
                self.policy(),
                recipient="reviewer-1234",
                purpose="changed-state-review",
            )

    def test_missing_action_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an exact action",
        ):
            self.route(
                self.policy(),
                recipient="reviewer-1234",
                purpose="semantic-escalation",
                action="   ",
            )

    def test_ambiguous_role_binding_fails_closed(self) -> None:
        policy = self.policy()
        policy["runtime"]["watcher_thread_id"] = "target-1234"
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "ambiguous configured roles",
        ):
            self.route(
                policy,
                recipient="target-1234",
                purpose="target-action",
            )

    def test_legacy_unbound_policy_must_be_rebound_before_routing(self) -> None:
        policy = self.policy()
        policy.pop("cross_thread_routing")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "run bind first",
        ):
            self.route(
                policy,
                recipient="target-1234",
                purpose="target-action",
            )

    def test_unmaintained_status_purpose_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Unsupported cross-thread routing purpose",
        ):
            self.route(
                self.policy(),
                recipient="target-1234",
                purpose="routine-status",
            )


class MissionContainmentContractTests(unittest.TestCase):
    target = "target-1234"
    mission_root = "m" * 64

    def init_args(self, *, bound: bool = True) -> argparse.Namespace:
        values: dict[str, object] = {
            "target_thread": self.target,
            "target_label": "target",
            "watcher_thread": "watcher-1234",
            "reviewer_thread": "reviewer-1234",
            "base_reviewer_thread": "base-1234",
            "notice_reviewer_thread": None,
            "fix_executor_thread": "fixer-1234",
        }
        if bound:
            values.update(
                mission_root=self.mission_root,
                mission_source_record="TRACKER-MISSION-1234",
            )
        return argparse.Namespace(**values)

    def policy(self, *, bound: bool = True) -> dict[str, object]:
        return supervision_log.default_policy(self.init_args(bound=bound))

    def containment_args(self, *extra: str) -> argparse.Namespace:
        return supervision_log.parser().parse_args(
            [
                "thread-route-gate",
                "--target-thread",
                self.target,
                "--recipient-thread",
                self.target,
                "--purpose",
                "target-action",
                "--source-record",
                "EVT-ROUTE-1234",
                "--action",
                "Hold one exact operation until its stop event.",
                "--containment",
                "--mission-root",
                self.mission_root,
                "--authority-source-class",
                "supervisor-steer",
                "--authority-source-record",
                "EVT-STEER-1234",
                "--impact-class",
                "material",
                "--affected-width",
                "one-operation",
                "--duration",
                "until-stop-event",
                "--reversibility",
                "reversible",
                "--ordinary-means-disabled",
                "no",
                "--independent-mission-review",
                "no",
                "--operation-scope",
                "operation-a",
                "--scope-identity",
                "scope-a-1234",
                "--expiry-event",
                "EVENT-STOP-1234",
                "--carry-forward",
                "false",
                "--successor-effects",
                "allowed",
                *extra,
            ]
        )

    def route(
        self, args: argparse.Namespace, policy: dict[str, object]
    ) -> dict[str, object]:
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_thread_route_gate(args)
        return json.loads(output.getvalue())

    def test_future_init_requires_and_records_exact_mission_binding(self) -> None:
        missing = supervision_log.parser().parse_args(
            [
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "target",
                "--watcher-thread",
                "watcher-1234",
                "--reviewer-thread",
                "reviewer-1234",
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "New supervision requires",
        ):
            supervision_log.mission_binding_from_args(missing, required=True)

        policy = self.policy()
        self.assertEqual(policy["mission_binding"]["mission_root"], self.mission_root)
        self.assertEqual(
            policy["mission_binding"]["mission_source_record"],
            "TRACKER-MISSION-1234",
        )
        alignment = policy["mission_binding"]["alignment_operating_contract"]
        self.assertEqual(alignment["mode"], "independent-mission-charter")
        self.assertFalse(alignment["target_native_alignment_required"])
        self.assertEqual(
            alignment["target_native_alignment_role"],
            "optional-read-only-corroboration",
        )
        self.assertFalse(alignment["target_native_alignment_may_authorize_or_block"])
        self.assertFalse(alignment["target_native_alignment_writes_allowed"])
        self.assertNotIn("semantic_owner", policy["mission_binding"])
        self.assertFalse(policy["mission_binding"]["aggregate_score"])

    def test_mission_plan_is_deterministic_and_source_bound(self) -> None:
        def plan(source_hash: str) -> dict[str, object]:
            args = supervision_log.parser().parse_args(
                [
                    "mission-plan",
                    "--target-thread",
                    self.target,
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "TRACKER-MISSION-1234",
                    "--mission-source-sha256",
                    source_hash,
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_mission_plan(args)
            return json.loads(output.getvalue())

        first = plan("a" * 64)
        repeat = plan("a" * 64)
        changed = plan("b" * 64)

        self.assertEqual(first, repeat)
        self.assertNotEqual(first["mission_root"], changed["mission_root"])
        binding = first["mission_binding"]
        self.assertEqual(binding["contract_version"], 3)
        self.assertEqual(
            binding["mission_derivation"]["mode"],
            "derived-from-versioned-meta-charter",
        )
        self.assertFalse(
            binding["alignment_operating_contract"][
                "target_native_alignment_required"
            ]
        )

        app_authored_source = (
            "[$implement-tracker-blocks]"
            "(/Users/example/.codex/releases/current/implement-tracker-blocks/SKILL.md)"
        ).encode("utf-8")
        source_sha256 = hashlib.sha256(app_authored_source).hexdigest()
        exact = plan(source_sha256)
        self.assertEqual(exact["mission_source_sha256"], source_sha256)
        self.assertEqual(
            exact["mission_binding"]["mission_derivation"]["controlling_source"][
                "sha256"
            ],
            source_sha256,
        )

    def test_init_derives_binding_without_manual_mission_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "init",
                    "--target-thread",
                    self.target,
                    "--target-label",
                    "target",
                    "--watcher-thread",
                    "watcher-1234",
                    "--reviewer-thread",
                    "reviewer-1234",
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "TRACKER-MISSION-1234",
                    "--mission-source-sha256",
                    "a" * 64,
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_init(args)
            policy = json.loads(
                Path(temporary, self.target, "policy.json").read_text(
                    encoding="utf-8"
                )
            )
            supervision_log.validate_policy(policy)
            self.assertEqual(policy["mission_binding"]["contract_version"], 3)
            self.assertEqual(
                policy["mission_binding"]["mission_derivation"]["mode"],
                "derived-from-versioned-meta-charter",
            )

    def test_derived_binding_rejects_mismatched_supplied_root(self) -> None:
        args = supervision_log.parser().parse_args(
            [
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "target",
                "--watcher-thread",
                "watcher-1234",
                "--reviewer-thread",
                "reviewer-1234",
                "--mission-root",
                "f" * 64,
                "--mission-source-class",
                "tracker",
                "--mission-source-record",
                "TRACKER-MISSION-1234",
                "--mission-source-sha256",
                "a" * 64,
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "differs from deterministic derivation",
        ):
            supervision_log.mission_binding_from_args(args, required=True)

    def test_mission_derivation_rejects_supervisor_created_authority(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires a direct-user, system, repository, or tracker source",
        ):
            supervision_log.derive_mission_binding(
                target_thread=self.target,
                source_class="supervisor-steer",
                source_record="EVT-SUPERVISOR-1234",
                source_sha256="a" * 64,
            )

    def test_mission_meta_charter_is_hash_bound_and_fail_closed(self) -> None:
        profile = supervision_log.mission_meta_charter_profile()
        self.assertEqual(
            profile["primary_directive"],
            "complete-the-explicit-governing-outcome",
        )
        self.assertEqual(
            profile["unsupported_goal_preventing_stop"]["severity"], "critical"
        )
        self.assertIn("observable-completion", profile["valid_stop_conditions"])
        self.assertIn("checkpoint-freeze-alone", profile["invalid_stop_bases"])
        self.assertFalse(profile["target_native_alignment"]["required"])

        with tempfile.TemporaryDirectory() as temporary:
            changed = dict(profile)
            changed["primary_directive"] = "pass-the-tests"
            path = Path(temporary, "mission-meta-charter.json")
            path.write_text(json.dumps(changed), encoding="utf-8")
            with (
                mock.patch.object(
                    supervision_log, "MISSION_META_CHARTER_PATH", path
                ),
                self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "hash is stale"
                ),
            ):
                supervision_log.mission_meta_charter_profile()

    def test_legacy_policy_upgrades_only_with_exact_bind_pair(self) -> None:
        policy = self.policy(bound=False)
        self.assertNotIn("mission_binding", policy)
        incomplete = supervision_log.parser().parse_args(
            ["bind", "--target-thread", self.target, "--mission-root", self.mission_root]
        )
        with mock.patch.object(
            supervision_log,
            "load_policy",
            return_value=(Path("/tmp/supervision-test"), policy),
        ), mock.patch.object(supervision_log, "read_json", return_value=policy):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "requires both"
            ):
                supervision_log.cmd_bind(incomplete)

        complete = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                self.target,
                "--mission-root",
                self.mission_root,
                "--mission-source-record",
                "TRACKER-MISSION-1234",
            ]
        )
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(complete)
        self.assertEqual(policy["mission_binding"]["mission_root"], self.mission_root)
        write.assert_called_once()

    def test_mission_successor_preserves_history_and_rebinds_exact_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            init = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "init",
                    "--target-thread",
                    self.target,
                    "--target-label",
                    "target",
                    "--watcher-thread",
                    "watcher-1234",
                    "--reviewer-thread",
                    "reviewer-1234",
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "TRACKER-MISSION-1234",
                    "--mission-source-sha256",
                    "a" * 64,
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_init(init)
            initial_policy = json.loads(
                Path(temporary, self.target, "policy.json").read_text(
                    encoding="utf-8"
                )
            )
            old_root = initial_policy["mission_binding"]["mission_root"]
            supervision_log.append_raw(
                Path(temporary, self.target, "events.jsonl"),
                {
                    "record_id": "EVT-LIFECYCLE-A",
                    "kind": "lifecycle",
                    "status": "completed",
                    "policy_sha256": initial_policy["policy_sha256"],
                },
            )
            history_path = Path(temporary, self.target, "policy-history.jsonl")
            predecessor_history = history_path.read_bytes()
            successor = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "mission-successor",
                    "--target-thread",
                    self.target,
                    "--from-mission-root",
                    old_root,
                    "--mission-source-class",
                    "direct-user",
                    "--mission-source-record",
                    "item-827",
                    "--mission-source-sha256",
                    "b" * 64,
                    "--predecessor-disposition",
                    "completed",
                    "--first-eligible-work",
                    "Block 0",
                    "--reason",
                    "The prior mission ended and the user supplied a new mission.",
                    "--evidence",
                    "item-827",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_mission_successor(successor)

            result = json.loads(output.getvalue())
            self.assertEqual(result["predecessor"]["mission_root"], old_root)
            self.assertNotEqual(result["successor"]["mission_root"], old_root)
            self.assertEqual(result["successor"]["mission_source_record"], "item-827")
            self.assertEqual(result["mission_activation"]["phase"], "pending")
            self.assertEqual(
                result["mission_activation"]["first_eligible_work"], "Block 0"
            )
            self.assertEqual(
                result["mission_activation"]["policy_sha256"],
                result["policy"]["policy_sha256"],
            )
            history = [
                json.loads(line)
                for line in history_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(history_path.read_bytes().startswith(predecessor_history))
            self.assertEqual(history[-1]["kind"], "policy-mission-successor")
            self.assertIn("EVT-LIFECYCLE-A", history[-1]["evidence"])
            self.assertEqual(
                history[-2]["policy"]["mission_binding"]["mission_root"], old_root
            )
            supervision_log.validate_policy(result["policy"])

    def test_mission_successor_rejects_stale_predecessor_and_open_state(self) -> None:
        policy = self.policy()
        stale = supervision_log.parser().parse_args(
            [
                "mission-successor",
                "--target-thread",
                self.target,
                "--from-mission-root",
                "c" * 64,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "item-827",
                "--mission-source-sha256",
                "b" * 64,
                "--predecessor-disposition",
                "superseded",
                "--first-eligible-work",
                "first-work-1234",
                "--reason",
                "New direct mission.",
                "--evidence",
                "item-827",
            ]
        )
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "read_json", return_value=policy),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "Predecessor mission root differs",
            ):
                supervision_log.cmd_mission_successor(stale)

        current = supervision_log.parser().parse_args(
            [
                "mission-successor",
                "--target-thread",
                self.target,
                "--from-mission-root",
                self.mission_root,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "item-827",
                "--mission-source-sha256",
                "b" * 64,
                "--predecessor-disposition",
                "superseded",
                "--first-eligible-work",
                "first-work-1234",
                "--reason",
                "New direct mission.",
                "--evidence",
                "item-827",
            ]
        )
        open_decision = {
            "kind": "decision",
            "decision_id": "DECISION-1234",
            "phase": "decision-ready",
        }
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "read_json", return_value=policy),
            mock.patch.object(supervision_log, "events", return_value=[open_decision]),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "requires closed incidents, decisions, successor transitions, and current mission activation",
            ),
        ):
            supervision_log.cmd_mission_successor(current)

    def test_completed_succession_cannot_reuse_an_older_mission_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            init = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "init",
                    "--target-thread",
                    self.target,
                    "--target-label",
                    "target",
                    "--watcher-thread",
                    "watcher-1234",
                    "--reviewer-thread",
                    "reviewer-1234",
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "MISSION-A",
                    "--mission-source-sha256",
                    "a" * 64,
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_init(init)
            policy_a = json.loads(
                Path(temporary, self.target, "policy.json").read_text(
                    encoding="utf-8"
                )
            )
            supervision_log.append_raw(
                Path(temporary, self.target, "events.jsonl"),
                {
                    "record_id": "EVT-LIFECYCLE-A",
                    "kind": "lifecycle",
                    "status": "completed",
                    "policy_sha256": policy_a["policy_sha256"],
                },
            )
            to_b = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "mission-successor",
                    "--target-thread",
                    self.target,
                    "--from-mission-root",
                    policy_a["mission_binding"]["mission_root"],
                    "--mission-source-class",
                    "direct-user",
                    "--mission-source-record",
                    "MISSION-B",
                    "--mission-source-sha256",
                    "b" * 64,
                    "--predecessor-disposition",
                    "superseded",
                    "--first-eligible-work",
                    "Block 0",
                    "--reason",
                    "Mission B replaced mission A.",
                    "--evidence",
                    "item-b",
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_mission_successor(to_b)
            policy_b = json.loads(
                Path(temporary, self.target, "policy.json").read_text(
                    encoding="utf-8"
                )
            )
            activation = supervision_log.mission_activation_heads(
                supervision_log.events(
                    Path(temporary, self.target, "events.jsonl")
                )
            )
            activation_head = list(activation.values())[-1]
            supervision_log.append_raw(
                Path(temporary, self.target, "events.jsonl"),
                {
                    "record_id": "EVT-WORK-B",
                    "target_thread_id": self.target,
                    "kind": "escalation",
                    "status": "changed-state-review",
                    "evidence": ["item-work-b"],
                    "policy_sha256": policy_b["policy_sha256"],
                },
            )
            start = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "mission-activation-start",
                    "--target-thread",
                    self.target,
                    "--mission-root",
                    policy_b["mission_binding"]["mission_root"],
                    "--activation-policy-sha256",
                    activation_head["activation_policy_sha256"],
                    "--first-eligible-work",
                    "Block 0",
                    "--source-record",
                    "EVT-WORK-B",
                    "--evidence",
                    "item-work-b",
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_mission_activation_start(start)
            to_c = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "mission-successor",
                    "--target-thread",
                    self.target,
                    "--from-mission-root",
                    policy_b["mission_binding"]["mission_root"],
                    "--mission-source-class",
                    "direct-user",
                    "--mission-source-record",
                    "MISSION-C",
                    "--mission-source-sha256",
                    "c" * 64,
                    "--predecessor-disposition",
                    "completed",
                    "--first-eligible-work",
                    "Block 0",
                    "--reason",
                    "Mission C follows mission B.",
                    "--evidence",
                    "item-c",
                ]
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "exact predecessor lifecycle",
            ):
                supervision_log.cmd_mission_successor(to_c)

    def test_gate_ignores_predecessor_mission_watermark(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            init = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "init",
                    "--target-thread",
                    self.target,
                    "--target-label",
                    "target",
                    "--watcher-thread",
                    "watcher-1234",
                    "--reviewer-thread",
                    "reviewer-1234",
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "MISSION-A",
                    "--mission-source-sha256",
                    "a" * 64,
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_init(init)
            policy_a = json.loads(
                Path(temporary, self.target, "policy.json").read_text(
                    encoding="utf-8"
                )
            )
            supervision_log.append_raw(
                Path(temporary, self.target, "events.jsonl"),
                {
                    "record_id": "EVT-CHECK-A",
                    "kind": "check",
                    "category": "semantic-review",
                    "model": "gpt-5.6-sol",
                    "reasoning": "xhigh",
                    "state_fingerprint": "same-fingerprint",
                    "policy_sha256": policy_a["policy_sha256"],
                },
            )
            successor = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "mission-successor",
                    "--target-thread",
                    self.target,
                    "--from-mission-root",
                    policy_a["mission_binding"]["mission_root"],
                    "--mission-source-class",
                    "direct-user",
                    "--mission-source-record",
                    "MISSION-B",
                    "--mission-source-sha256",
                    "b" * 64,
                    "--predecessor-disposition",
                    "superseded",
                    "--first-eligible-work",
                    "Block 0",
                    "--reason",
                    "Mission B replaced mission A.",
                    "--evidence",
                    "item-b",
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_mission_successor(successor)
            gate = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "gate",
                    "--target-thread",
                    self.target,
                    "--state-fingerprint",
                    "same-fingerprint",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_gate(gate)
            result = json.loads(output.getvalue())
            self.assertTrue(result["changed"])
            self.assertIsNone(result["prior_state_fingerprint"])

    def test_policy_writer_rejects_a_stale_predecessor_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            init = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "init",
                    "--target-thread",
                    self.target,
                    "--target-label",
                    "target",
                    "--watcher-thread",
                    "watcher-1234",
                    "--reviewer-thread",
                    "reviewer-1234",
                    "--mission-source-class",
                    "tracker",
                    "--mission-source-record",
                    "MISSION-A",
                    "--mission-source-sha256",
                    "a" * 64,
                ]
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_init(init)
            directory = Path(temporary, self.target)
            first = json.loads(
                directory.joinpath("policy.json").read_text(encoding="utf-8")
            )
            stale = json.loads(json.dumps(first))
            supervision_log.write_policy_version(
                directory,
                first,
                kind="policy-test",
                reason="First writer won.",
                evidence_values=["test-first"],
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "changed concurrently",
            ):
                supervision_log.write_policy_version(
                    directory,
                    stale,
                    kind="policy-test",
                    reason="Stale writer must fail.",
                    evidence_values=["test-stale"],
                )
            stale_event = {
                "record_id": "EVT-STALE",
                "kind": "check",
                "policy_sha256": stale["policy_sha256"],
            }
            with (
                supervision_log.append_lock(directory),
                self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "rebuild the event",
                ),
            ):
                supervision_log.append_event_locked(
                    argparse.Namespace(root=temporary, target_thread=self.target),
                    directory,
                    stale_event,
                )

    def test_accepted_legacy_binding_remains_readable_and_bind_upgrades_it(self) -> None:
        policy = self.policy()
        policy["mission_binding"] = supervision_log.legacy_mission_binding_contract(
            self.mission_root, "TRACKER-MISSION-1234"
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.validate_policy(policy)

        args = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                self.target,
                "--mission-root",
                self.mission_root,
                "--mission-source-record",
                "TRACKER-MISSION-1234",
            ]
        )
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(args)

        self.assertEqual(policy["mission_binding"]["contract_version"], 3)
        self.assertNotIn("semantic_owner", policy["mission_binding"])
        write.assert_called_once()

    def test_candidate_v2_binding_remains_readable_and_upgrades(self) -> None:
        policy = self.policy()
        policy["mission_binding"] = supervision_log.legacy_mission_binding_contract_v2(
            self.mission_root, "TRACKER-MISSION-1234"
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.validate_policy(policy)

        args = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                self.target,
                "--mission-root",
                self.mission_root,
                "--mission-source-record",
                "TRACKER-MISSION-1234",
            ]
        )
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version") as write,
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(args)

        self.assertEqual(policy["mission_binding"]["contract_version"], 3)
        write.assert_called_once()

    def test_policy_validation_rejects_mission_contract_drift(self) -> None:
        policy = self.policy()
        policy["mission_binding"]["aggregate_score"] = True
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "Mission binding contract differs"
        ):
            supervision_log.validate_policy(policy)

    def test_unbound_policy_allows_observation_and_simple_target_action(self) -> None:
        policy = self.policy(bound=False)
        route = supervision_log.parser().parse_args(
            [
                "thread-route-gate",
                "--target-thread",
                self.target,
                "--recipient-thread",
                self.target,
                "--purpose",
                "target-action",
                "--source-record",
                "EVT-ROUTE-1234",
                "--action",
                "Apply one simple bounded correction.",
            ]
        )
        self.assertTrue(self.route(route, policy)["send_allowed"])

        gate = argparse.Namespace(
            target_thread=self.target,
            state_fingerprint="state-1234",
            thread_updated_at="",
            thread_status="",
            active_block="",
            latest_item="",
            checkpoint="",
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), policy),
            ),
            mock.patch.object(supervision_log, "events", return_value=[]),
            redirect_stdout(output),
        ):
            supervision_log.cmd_gate(gate)
        self.assertTrue(json.loads(output.getvalue())["changed"])

    def test_consequential_containment_requires_current_complete_envelope(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "exact bound mission"
        ):
            self.route(self.containment_args(), self.policy(bound=False))

        stale = self.containment_args()
        stale.mission_root = "n" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "stale mission root"
        ):
            self.route(stale, self.policy())

        cases = {
            "operation_scope": None,
            "scope_identity": None,
            "expiry_event": None,
            "carry_forward": "true",
            "successor_effects": "blocked",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                args = self.containment_args()
                setattr(args, field, value)
                with self.assertRaises(supervision_log.SupervisionLogError):
                    self.route(args, self.policy())

    def test_bounded_operation_hold_expires_without_blocking_successor(self) -> None:
        first = self.route(self.containment_args(), self.policy())
        successor_args = self.containment_args()
        successor_args.operation_scope = "operation-b"
        successor_args.scope_identity = "scope-b-1234"
        successor_args.expiry_event = "EVENT-STOP-5678"
        successor = self.route(successor_args, self.policy())

        self.assertTrue(first["send_allowed"])
        self.assertTrue(successor["send_allowed"])
        self.assertFalse(first["containment"]["carry_forward"])
        self.assertEqual(first["containment"]["successor_effects"], "allowed")
        self.assertNotEqual(
            first["containment_sha256"], successor["containment_sha256"]
        )

    def test_goal_reversing_supervisor_action_fails_closed(self) -> None:
        args = self.containment_args()
        args.impact_class = "goal-reversing"
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "cannot reverse"
        ):
            self.route(args, self.policy())

    def test_critical_goal_blocking_hold_is_one_operation_and_reviewed(self) -> None:
        args = self.containment_args()
        args.impact_class = "goal-blocking"
        args.severity = "critical"
        args.incident_id = "INC-CRITICAL-1234"
        args.independent_mission_review = "yes"
        result = self.route(args, self.policy())

        self.assertTrue(result["send_allowed"])
        self.assertEqual(result["containment"]["operation_scope"], "operation-a")
        self.assertTrue(result["containment"]["independent_mission_review"])
        self.assertFalse(result["containment"]["carry_forward"])

    def test_existing_event_ledger_preserves_structured_containment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = supervision_log.parser().parse_args(
                [
                    "record",
                    "--target-thread",
                    self.target,
                    "--kind",
                    "steer",
                    "--summary",
                    "Recorded one bounded containment.",
                    "--containment",
                    "--mission-root",
                    self.mission_root,
                    "--authority-source-class",
                    "supervisor-steer",
                    "--authority-source-record",
                    "EVT-STEER-1234",
                    "--impact-class",
                    "material",
                    "--affected-width",
                    "one-operation",
                    "--duration",
                    "until-stop-event",
                    "--reversibility",
                    "reversible",
                    "--ordinary-means-disabled",
                    "no",
                    "--independent-mission-review",
                    "no",
                    "--operation-scope",
                    "operation-a",
                    "--scope-identity",
                    "scope-a-1234",
                    "--expiry-event",
                    "EVENT-STOP-1234",
                    "--carry-forward",
                    "false",
                    "--successor-effects",
                    "allowed",
                ]
            )
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(directory, self.policy()),
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_record(args)
            record = json.loads(output.getvalue())["record"]
            self.assertEqual(record["containment"]["expiry_event"], "EVENT-STOP-1234")
            self.assertFalse(record["containment"]["carry_forward"])


class MissionActivationContractTests(unittest.TestCase):
    target = "target-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / self.target
        init = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "target",
                "--watcher-thread",
                "watcher-1234",
                "--reviewer-thread",
                "reviewer-1234",
                "--base-reviewer-thread",
                "base-1234",
                "--fix-executor-thread",
                "fixer-1234",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "MISSION-A",
                "--mission-source-sha256",
                "a" * 64,
            ]
        )
        with redirect_stdout(io.StringIO()):
            supervision_log.cmd_init(init)

    def policy(self) -> dict[str, object]:
        return json.loads(
            (self.directory / "policy.json").read_text(encoding="utf-8")
        )

    def successor(self, *, first_work: str = "Block 0") -> dict[str, object]:
        policy = self.policy()
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "mission-successor",
                "--target-thread",
                self.target,
                "--from-mission-root",
                policy["mission_binding"]["mission_root"],
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "MISSION-B",
                "--mission-source-sha256",
                "b" * 64,
                "--predecessor-disposition",
                "superseded",
                "--first-eligible-work",
                first_work,
                "--reason",
                "Mission B replaced mission A.",
                "--evidence",
                "item-mission-b",
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_mission_successor(args)
        return json.loads(output.getvalue())

    def append_source(
        self, record_id: str, evidence: str, *, policy: dict[str, object] | None = None
    ) -> None:
        current = policy or self.policy()
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "record_id": record_id,
                "target_thread_id": self.target,
                "kind": "escalation",
                "status": "changed-state-review",
                "evidence": [evidence],
                "policy_sha256": current["policy_sha256"],
            },
        )

    def start_args(
        self,
        activation: dict[str, object],
        *,
        mission_root: str | None = None,
        activation_policy_sha256: str | None = None,
        first_work: str | None = None,
        source_record: str = "EVT-WORK-B",
        evidence: str = "item-work-b",
    ) -> argparse.Namespace:
        return supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "mission-activation-start",
                "--target-thread",
                self.target,
                "--mission-root",
                mission_root or str(activation["mission_root"]),
                "--activation-policy-sha256",
                activation_policy_sha256
                or str(activation["activation_policy_sha256"]),
                "--first-eligible-work",
                first_work or str(activation["first_eligible_work"]),
                "--source-record",
                source_record,
                "--evidence",
                evidence,
            ]
        )

    def start(
        self, activation: dict[str, object], **overrides: object
    ) -> dict[str, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_mission_activation_start(
                self.start_args(activation, **overrides)
            )
        return json.loads(output.getvalue())

    def status(self) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "status",
                "--target-thread",
                self.target,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_status(args)
        return json.loads(output.getvalue())

    def test_successor_creates_pending_activation_and_terminal_gate_fails_closed(
        self,
    ) -> None:
        result = self.successor()
        activation = result["mission_activation"]
        status = self.status()

        self.assertEqual(activation["phase"], "pending")
        self.assertEqual(status["mission_activation_count"], 1)
        self.assertEqual(len(status["open_mission_activations"]), 1)
        self.assertEqual(
            status["mission_activation_action"],
            supervision_log.MISSION_ACTIVATION_START_ACTION,
        )
        self.assertEqual(
            status["mission_activation_required_target_posture"], "in-progress"
        )

        for state in ("completed", "paused", "stopped"):
            with self.subTest(state=state):
                record_id = f"EVT-{state.upper()}-B"
                supervision_log.append_raw(
                    self.directory / "events.jsonl",
                    {
                        "record_id": record_id,
                        "target_thread_id": self.target,
                        "kind": "lifecycle",
                        "status": state,
                        "state_fingerprint": f"state-{state}-b",
                        "user_action_required": "no",
                        "policy_sha256": result["policy"]["policy_sha256"],
                    },
                )
                gate = supervision_log.parser().parse_args(
                    [
                        "--root",
                        str(self.root),
                        "lifecycle-gate",
                        "--target-thread",
                        self.target,
                        "--lifecycle-state",
                        state,
                        "--source-record",
                        record_id,
                    ]
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    supervision_log.cmd_lifecycle_gate(gate)
                lifecycle = json.loads(output.getvalue())
                self.assertFalse(lifecycle["source_stop_permitted"])
                self.assertEqual(
                    lifecycle["completion_action"],
                    supervision_log.MISSION_ACTIVATION_START_ACTION,
                )
                self.assertEqual(len(lifecycle["open_mission_activations"]), 1)

        completed = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "record",
                "--target-thread",
                self.target,
                "--kind",
                "lifecycle",
                "--status",
                "completed",
                "--state-fingerprint",
                "state-completed-b",
                "--summary",
                "Incorrectly claimed completion before first work.",
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "current mission first work has not started",
        ):
            supervision_log.cmd_record(completed)

    def test_pending_activation_does_not_change_failed_or_blocked_handling(
        self,
    ) -> None:
        result = self.successor()
        for state in ("failed", "blocked"):
            with self.subTest(state=state):
                record_id = f"EVT-{state.upper()}-B"
                supervision_log.append_raw(
                    self.directory / "events.jsonl",
                    {
                        "record_id": record_id,
                        "target_thread_id": self.target,
                        "kind": "lifecycle",
                        "status": state,
                        "state_fingerprint": f"state-{state}-b",
                        "user_action_required": "no",
                        "policy_sha256": result["policy"]["policy_sha256"],
                    },
                )
                args = supervision_log.parser().parse_args(
                    [
                        "--root",
                        str(self.root),
                        "lifecycle-gate",
                        "--target-thread",
                        self.target,
                        "--lifecycle-state",
                        state,
                        "--source-record",
                        record_id,
                    ]
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    supervision_log.cmd_lifecycle_gate(args)
                lifecycle = json.loads(output.getvalue())
                self.assertTrue(lifecycle["source_stop_permitted"])
                self.assertNotEqual(
                    lifecycle["completion_action"],
                    supervision_log.MISSION_ACTIVATION_START_ACTION,
                )

    def test_exact_later_work_start_closes_activation_idempotently(self) -> None:
        activation = self.successor()["mission_activation"]
        self.append_source("EVT-WORK-B", "item-work-b")

        result = self.start(activation)
        duplicate = self.start(activation)
        status = self.status()

        self.assertEqual(result["record"]["phase"], "work-started")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(status["open_mission_activations"], [])
        self.assertEqual(status["mission_activation_action"], "none")
        self.assertIsNone(status["mission_activation_required_target_posture"])

    def test_start_rejects_stale_identity_prebinding_and_divergent_evidence(
        self,
    ) -> None:
        policy_a = self.policy()
        self.append_source("EVT-PRE-BIND", "item-pre-bind", policy=policy_a)
        activation = self.successor()["mission_activation"]

        for overrides, message in (
            ({"mission_root": "f" * 64}, "different mission root"),
            ({"activation_policy_sha256": "e" * 64}, "policy identity differs"),
            ({"first_work": "Block 1"}, "first work identity differs"),
            (
                {
                    "source_record": "EVT-PRE-BIND",
                    "evidence": "item-pre-bind",
                },
                "pre-binding evidence",
            ),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                supervision_log.SupervisionLogError, message
            ):
                supervision_log.cmd_mission_activation_start(
                    self.start_args(activation, **overrides)
                )

        self.append_source("EVT-WORK-B", "item-work-b")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not bound to its source record",
        ):
            supervision_log.cmd_mission_activation_start(
                self.start_args(activation, evidence="item-not-in-source")
            )

        self.start(activation)
        self.append_source("EVT-WORK-B-2", "item-work-b-2")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "already closed with different evidence",
        ):
            supervision_log.cmd_mission_activation_start(
                self.start_args(
                    activation,
                    source_record="EVT-WORK-B-2",
                    evidence="item-work-b-2",
                )
            )

    def test_initial_and_existing_current_missions_are_not_retroactively_blocked(
        self,
    ) -> None:
        policy = self.policy()
        status = self.status()
        self.assertEqual(status["mission_activation_count"], 0)
        self.assertEqual(status["open_mission_activations"], [])

        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "record_id": "EVT-COMPLETED-A",
                "target_thread_id": self.target,
                "kind": "lifecycle",
                "status": "completed",
                "state_fingerprint": "state-completed-a",
                "user_action_required": "no",
                "policy_sha256": policy["policy_sha256"],
            },
        )
        gate = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "lifecycle-gate",
                "--target-thread",
                self.target,
                "--lifecycle-state",
                "completed",
                "--source-record",
                "EVT-COMPLETED-A",
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_lifecycle_gate(gate)
        lifecycle = json.loads(output.getvalue())
        self.assertTrue(lifecycle["source_stop_permitted"])
        self.assertEqual(lifecycle["open_mission_activations"], [])
        self.assertNotEqual(
            lifecycle["completion_action"],
            supervision_log.MISSION_ACTIVATION_START_ACTION,
        )

    def test_same_target_activation_is_documented_without_task_or_resume_expansion(
        self,
    ) -> None:
        skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        for text in (skill, policy):
            self.assertIn("mission-activation-start", text)
            self.assertIn("first eligible work", text)
            self.assertIn("in-progress", text)
            self.assertIn("manual Resume", text)
            self.assertIn("successor-task transition", text)
        self.assertIn(
            supervision_log.MISSION_ACTIVATION_START_ACTION,
            policy,
        )


class OutcomeCompletionRecordTests(unittest.TestCase):
    mission_root = "a" * 64

    def setUp(self) -> None:
        self.reconciliation_temporary = tempfile.TemporaryDirectory()
        self.reconciliation_path = Path(
            self.reconciliation_temporary.name, "capability-reconciliation.json"
        )
        self.write_reconciliation()

    def tearDown(self) -> None:
        self.reconciliation_temporary.cleanup()

    def write_reconciliation(self, **overrides: object) -> Path:
        authority_id = "authority-1234"
        repository_id = "repository-1234"
        outcome_id = "outcome-1234"
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": supervision_log.CAPABILITY_RECONCILIATION_KIND,
            "target_thread_id": "target-1234",
            "mission_root": self.mission_root,
            "state_fingerprint": "state-1234",
            "current_revision": "2" * 40,
            "implementation_owner_id": "target-1234",
            "reviewer_id": "base-1234",
            "requested_capability": {
                "statement": "Deliver the requested visible capability.",
                "evidence_ids": [authority_id],
            },
            "protected_capabilities": [
                {
                    "statement": "Preserve the existing supported path.",
                    "evidence_ids": [repository_id],
                }
            ],
            "selected_architecture_level": {
                "level": "existing-owner",
                "owner_ref": "supervise-tracker-runs",
                "evidence_ids": [repository_id],
            },
            "accepted_tradeoffs": [
                {
                    "statement": "Keep the change bounded to the current owner.",
                    "evidence_ids": [authority_id, repository_id],
                }
            ],
            "current_behavior": {
                "statement": "The frozen candidate supplies the requested behavior.",
                "evidence_ids": [outcome_id],
            },
            "operator_visible_effects": [
                {
                    "statement": "The operator can use the result as requested.",
                    "evidence_ids": [outcome_id],
                }
            ],
            "supported_gaps": [],
            "completion_posture": "verified",
            "evidence": [
                {
                    "evidence_id": authority_id,
                    "evidence_class": "direct-authority",
                    "source_root": "3" * 64,
                },
                {
                    "evidence_id": repository_id,
                    "evidence_class": "current-repository",
                    "source_root": "4" * 64,
                },
                {
                    "evidence_id": outcome_id,
                    "evidence_class": "observed-outcome",
                    "source_root": "5" * 64,
                },
            ],
        }
        value.update(overrides)
        self.reconciliation_path.write_text(
            json.dumps(value, sort_keys=True), encoding="utf-8"
        )
        return self.reconciliation_path

    def policy(self) -> dict[str, object]:
        policy = supervision_log.default_policy(
            argparse.Namespace(
                target_thread="target-1234",
                target_label="target",
                watcher_thread="watcher-1234",
                reviewer_thread="reviewer-1234",
                base_reviewer_thread="base-1234",
                notice_reviewer_thread=None,
                fix_executor_thread="fixer-1234",
            )
        )
        policy["mission_binding"] = supervision_log.mission_binding_contract(
            self.mission_root, "mission-source-1234"
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        return policy

    def completion_args(self, **overrides: object) -> argparse.Namespace:
        values = {
            "target_thread": "target-1234",
            "state_fingerprint": "state-1234",
            "current_revision": "2" * 40,
            "mission_root": self.mission_root,
            "status": "verified",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "outcome_manifest_sha256": "b" * 64,
            "artifact_currentness_sha256": "c" * 64,
            "effect_reconciliation_sha256": "d" * 64,
            "open_item_compatibility_sha256": "e" * 64,
            "independent_challenge_sha256": "f" * 64,
            "capability_reconciliation_json": str(self.reconciliation_path),
            "active_block": "Block-64",
            "checkpoint": "checkpoint-1234",
            "summary": "Current operator-visible outcome verified.",
            "evidence": ["source-1234"],
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_completion_record_is_append_only_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = self.policy()
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log, "load_policy", return_value=(directory, policy)
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_completion_record(self.completion_args())
            record = json.loads(output.getvalue())["record"]
            self.assertEqual(
                record["category"], supervision_log.OUTCOME_COMPLETION_CATEGORY
            )
            reconciliation = json.loads(
                self.reconciliation_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                record["capability_reconciliation_sha256"],
                supervision_log.digest(reconciliation),
            )
            self.assertEqual(
                record["capability_reconciliation_reviewer_id"], "base-1234"
            )

            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log, "load_policy", return_value=(directory, policy)
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_completion_record(self.completion_args())
            self.assertTrue(json.loads(output.getvalue())["duplicate"])

            lifecycle_args = argparse.Namespace(
                target_thread="target-1234",
                kind="lifecycle",
                model="gpt-5.6-terra",
                reasoning="max",
                state_fingerprint="state-1234",
                status="completed",
                severity="info",
                category="lifecycle",
                active_block="Block-64",
                checkpoint="checkpoint-1234",
                summary="Target reported completion.",
                evidence=[],
                estimated_risk="",
                action="",
                resolution="",
                dedup_key="lifecycle:completed",
                incident_id=None,
                review_id=None,
                notice_disposition="",
                resolution_owner="",
                user_action_required="no",
                containment=False,
            )
            output = io.StringIO()
            with (
                mock.patch.object(
                    supervision_log, "load_policy", return_value=(directory, policy)
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_record(lifecycle_args)
            lifecycle = json.loads(output.getvalue())["record"]
            self.assertEqual(
                lifecycle["outcome_completion_record_id"], record["record_id"]
            )

    def test_completion_record_rejects_wrong_mission_or_missing_hash(self) -> None:
        policy = self.policy()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ):
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "stale mission root"
                ):
                    supervision_log.cmd_completion_record(
                        self.completion_args(mission_root="0" * 64)
                    )
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "must be an exact"
                ):
                    supervision_log.cmd_completion_record(
                        self.completion_args(artifact_currentness_sha256="missing")
                    )
                self.write_reconciliation(state_fingerprint="state-old")
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "stale state fingerprint"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())
                self.write_reconciliation(current_revision="9" * 40)
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "stale current revision"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())

    def test_verified_completion_rejects_gap_or_self_review(self) -> None:
        policy = self.policy()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ):
                self.write_reconciliation(
                    supported_gaps=[
                        {
                            "gap_id": "gap-1234",
                            "statement": "The requested effect is not current.",
                            "owner_class": "supervision",
                            "owner_ref": "supervise-tracker-runs",
                            "evidence_ids": ["outcome-1234"],
                        }
                    ],
                    completion_posture="reopen-narrow-owner",
                )
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "supported capability gap"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())

                self.write_reconciliation(reviewer_id="target-1234")
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "not independent"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())

                self.write_reconciliation(reviewer_id="watcher-1234")
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "not an eligible bound"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())

                self.write_reconciliation()
                process_only = json.loads(
                    self.reconciliation_path.read_text(encoding="utf-8")
                )
                process_only["evidence"][2]["evidence_class"] = "validation"
                self.reconciliation_path.write_text(
                    json.dumps(process_only, sort_keys=True), encoding="utf-8"
                )
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, "required evidence class"
                ):
                    supervision_log.cmd_completion_record(self.completion_args())

    def test_oversized_reconciliation_rejects_before_json_parsing(self) -> None:
        with self.reconciliation_path.open("wb") as handle:
            handle.truncate(supervision_log.MAX_CAPABILITY_RECONCILIATION_BYTES + 1)
        policy = self.policy()

        with (
            mock.patch.object(supervision_log.json, "loads") as loads,
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "exceeds its byte bound"
            ),
        ):
            supervision_log.load_capability_reconciliation(
                str(self.reconciliation_path),
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )
        loads.assert_not_called()

    def test_completion_contract_requires_product_capability_reconciliation(
        self,
    ) -> None:
        contract = supervision_log.outcome_completion_contract()

        self.assertIn(
            "capability_reconciliation_sha256", contract["required_bindings"]
        )
        self.assertEqual(
            contract["capability_reconciliation_required_fields"],
            [
                "requested_capability",
                "protected_capabilities",
                "selected_architecture_level",
                "accepted_tradeoffs",
                "current_behavior",
                "operator_visible_effects",
                "supported_gaps",
            ],
        )
        self.assertEqual(
            contract["supported_gap_posture"],
            "reject-completed-and-reopen-narrow-owner",
        )

    def test_completed_lifecycle_cannot_enter_ledger_without_proof(self) -> None:
        policy = self.policy()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = argparse.Namespace(
                target_thread="target-1234",
                kind="lifecycle",
                model="gpt-5.6-terra",
                reasoning="max",
                state_fingerprint="state-1234",
                status="completed",
                severity="info",
                category="lifecycle",
                active_block="Block-64",
                checkpoint="checkpoint-1234",
                summary="Target reported completion.",
                evidence=[],
                estimated_risk="",
                action="",
                resolution="",
                dedup_key="lifecycle:completed",
                incident_id=None,
                review_id=None,
                notice_disposition="",
                resolution_owner="",
                user_action_required="no",
                containment=False,
            )
            with mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ):
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "Completed lifecycle rejected",
                ):
                    supervision_log.cmd_record(args)


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
        *,
        include_completion: bool = True,
    ) -> dict[str, object]:
        event_records = list(records or [])
        completion_record_id = None
        if state == "completed" and include_completion:
            mission_root = "a" * 64
            policy["mission_binding"] = supervision_log.mission_binding_contract(
                mission_root, "mission-source-1234"
            )
            completion_record_id = "EVT-000000"
            event_records.insert(
                0,
                {
                    "kind": "check",
                    "record_id": completion_record_id,
                    "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                    "status": "verified",
                    "state_fingerprint": "state-1234",
                    "mission_root": mission_root,
                    "model": "gpt-5.6-sol",
                    "reasoning": "xhigh",
                    "evidence": ["evidence-1234"],
                    **{
                        field: "b" * 64
                        for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                    },
                    "capability_reconciliation_reviewer_id": "base-1234",
                    "capability_reconciliation_implementation_owner_id": "target-1234",
                    "capability_reconciliation_revision": "c" * 40,
                    "capability_reconciliation_posture": "verified",
                    "capability_reconciliation_gap_count": 0,
                },
            )
        elif state == "completed":
            supplied_completion = next(
                (
                    item
                    for item in reversed(event_records)
                    if item.get("category")
                    == supervision_log.OUTCOME_COMPLETION_CATEGORY
                ),
                None,
            )
            if supplied_completion is not None:
                completion_record_id = str(supplied_completion["record_id"])
        source = {
            "kind": "lifecycle",
            "record_id": "EVT-000001",
            "status": state,
            "state_fingerprint": "state-1234",
            "user_action_required": "yes",
        }
        if completion_record_id is not None:
            source["outcome_completion_record_id"] = completion_record_id
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
                return_value=[*event_records, source],
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

    def test_paused_remains_on_primary_thread(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail"].update(
            {
                "enabled": True,
                "reply_message_id": "gmail-primary-1234",
            }
        )

        result = self.run_lifecycle_gate(policy, "paused")

        self.assertTrue(result["send_now"])
        self.assertEqual(result["channel"], "primary-status")
        self.assertEqual(result["notification_category"], "gmail-lifecycle")

    def test_completed_waits_for_terminal_report_attachments(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail"].update(
            {
                "enabled": True,
                "reply_message_id": "gmail-primary-1234",
            }
        )

        result = self.run_lifecycle_gate(policy, "completed")

        self.assertTrue(result["completion_permitted"])
        self.assertFalse(result["send_now"])
        self.assertFalse(result["supervision_pause_permitted"])
        self.assertEqual(
            result["completion_action"],
            "prepare-finalize-verify-email-and-record-terminal-reports",
        )
        self.assertEqual(result["reply_message_id"], "gmail-primary-1234")

    def test_completed_refuses_missing_outcome_completion(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        policy["notifications"]["gmail"].update(
            {"enabled": True, "reply_message_id": "gmail-primary-1234"}
        )

        result = self.run_lifecycle_gate(
            policy, "completed", include_completion=False
        )

        self.assertFalse(result["completion_permitted"])
        self.assertFalse(result["send_now"])
        self.assertEqual(
            result["completion_action"], "open-critical-false-completion-review"
        )

    def test_completed_refuses_failed_or_stale_outcome_completion(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        mission_root = "a" * 64
        policy["mission_binding"] = supervision_log.mission_binding_contract(
            mission_root, "mission-source-1234"
        )
        base = {
            "kind": "check",
            "record_id": "EVT-000002",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "status": "failed",
            "state_fingerprint": "state-1234",
            "mission_root": mission_root,
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "evidence": ["evidence-1234"],
            **{
                field: "b" * 64
                for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
            },
            "capability_reconciliation_reviewer_id": "base-1234",
            "capability_reconciliation_implementation_owner_id": "target-1234",
            "capability_reconciliation_revision": "c" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }

        failed = self.run_lifecycle_gate(
            policy, "completed", [base], include_completion=False
        )
        self.assertFalse(failed["completion_permitted"])

        stale = dict(base, status="verified", state_fingerprint="state-old")
        stale_result = self.run_lifecycle_gate(
            policy, "completed", [stale], include_completion=False
        )
        self.assertFalse(stale_result["completion_permitted"])

    def test_completed_refuses_missing_binding_or_wrong_mission(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        mission_root = "a" * 64
        policy["mission_binding"] = supervision_log.mission_binding_contract(
            mission_root, "mission-source-1234"
        )
        completion = {
            "kind": "check",
            "record_id": "EVT-000002",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "status": "verified",
            "state_fingerprint": "state-1234",
            "mission_root": "c" * 64,
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "evidence": ["evidence-1234"],
            **{
                field: "b" * 64
                for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
            },
            "capability_reconciliation_reviewer_id": "base-1234",
            "capability_reconciliation_implementation_owner_id": "target-1234",
            "capability_reconciliation_revision": "c" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }

        wrong_mission = self.run_lifecycle_gate(
            policy, "completed", [completion], include_completion=False
        )
        self.assertFalse(wrong_mission["completion_permitted"])

        completion["mission_root"] = mission_root
        del completion["artifact_currentness_sha256"]
        missing_binding = self.run_lifecycle_gate(
            policy, "completed", [completion], include_completion=False
        )
        self.assertFalse(missing_binding["completion_permitted"])

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

    def test_policy_validation_rejects_incomplete_enabled_decision_context(self) -> None:
        policy = supervision_log.default_policy(self.init_args())
        priority = policy["notifications"]["gmail_priority"]
        priority.update(
            {
                "enabled": True,
                "reply_message_id": "gmail-priority-1234",
                "project_key": "Main",
                "subject": "PRIORITY - Main",
                "decision_context_enabled": True,
            }
        )
        priority.pop("required_decision_fields")
        policy["permissions"]["gmail_priority_notification"] = True
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires every maintained decision field",
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
    mission_root = "m" * 64

    def init_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            target_thread=self.target,
            target_label="target",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread=None,
            fix_executor_thread="fixer-1234",
            mission_root=self.mission_root,
            mission_source_record="TRACKER-MISSION-1234",
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
        mission_root: str | None = None,
        authority_source_class: str = "tracker",
        authority_source_record: str = "TRACKER-BOUNDARY-1234",
        impact_class: str = "material",
        affected_width: str = "decision-subject",
        duration: str = "decision-lifecycle",
        reversibility: str = "conditional",
        ordinary_means_disabled: str = "no",
        independent_mission_review: str = "no",
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
                "--mission-root",
                mission_root or self.mission_root,
                "--authority-source-class",
                authority_source_class,
                "--authority-source-record",
                authority_source_record,
                "--impact-class",
                impact_class,
                "--affected-width",
                affected_width,
                "--duration",
                duration,
                "--reversibility",
                reversibility,
                "--ordinary-means-disabled",
                ordinary_means_disabled,
                "--independent-mission-review",
                independent_mission_review,
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

    def notification(
        self,
        directory: Path,
        policy: dict[str, object],
        *,
        status: str,
        dedup_key: str,
        source_record: str,
    ) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "record",
                "--target-thread",
                self.target,
                "--kind",
                "notification",
                "--status",
                status,
                "--category",
                "gmail-priority-decision",
                "--dedup-key",
                dedup_key,
                "--state-fingerprint",
                "state-1234",
                "--evidence",
                source_record,
                "--summary",
                f"Decision notification {status}.",
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log, "load_policy", return_value=(directory, policy)
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_record(args)
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
            self.assertEqual(result["required_target_posture"], "in-progress")
            self.assertFalse(result["manual_resume_required"])

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
            self.assertFalse(ready["blocking_permitted"])
            self.assertEqual(ready["required_target_posture"], "in-progress")
            self.assertFalse(ready["manual_resume_required"])

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

    def test_premature_selection_and_safe_deferral_fail_closed(self) -> None:
        for classification, phase, outcome in (
            ("human-preference", "resolved", "selected"),
            ("missing-fact", "safe-deferred", "safe-deferred"),
        ):
            with self.subTest(classification=classification):
                with tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary)
                    policy = supervision_log.default_policy(self.init_args())
                    self.record(
                        directory,
                        policy,
                        classification=classification,
                        phase="decision-ready",
                    )
                    self.record(
                        directory,
                        policy,
                        classification=classification,
                        phase="attempt-started",
                        attempt=1,
                    )
                    self.record(
                        directory,
                        policy,
                        classification=classification,
                        phase="attempt-unresolved",
                        attempt=1,
                        now="2026-08-01T12:01:00+00:00",
                    )

                    with self.assertRaisesRegex(
                        supervision_log.SupervisionLogError,
                        "requires all attempts and the user window",
                    ):
                        self.record(
                            directory,
                            policy,
                            classification=classification,
                            phase=phase,
                            attempt=1,
                            outcome=outcome,
                            now="2026-08-01T12:02:00+00:00",
                        )

    def test_failed_decision_notification_remains_retryable(self) -> None:
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
            eligible = self.gate(directory, policy, "2026-08-01T12:20:00+00:00")
            failed = self.notification(
                directory,
                policy,
                status="failed",
                dedup_key=eligible["notification_dedup_key"],
                source_record=unresolved["record_id"],
            )

            retry = self.gate(directory, policy, "2026-08-01T12:20:01+00:00")
            sent = self.notification(
                directory,
                policy,
                status="sent",
                dedup_key=retry["notification_dedup_key"],
                source_record=unresolved["record_id"],
            )
            complete = self.gate(directory, policy, "2026-08-01T12:20:02+00:00")

            self.assertFalse(failed["duplicate"])
            self.assertTrue(retry["notification_send_now"])
            self.assertFalse(retry["notification_duplicate"])
            self.assertFalse(sent["duplicate"])
            self.assertFalse(complete["notification_send_now"])
            self.assertTrue(complete["notification_duplicate"])

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
            self.assertEqual(result["required_target_posture"], "in-progress")

            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="safe-deferred",
                safe_frontier="empty",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:00+00:00",
            )
            deferred = self.gate(directory, policy, "2026-08-01T14:20:01+00:00")
            self.assertFalse(deferred["blocking_permitted"])
            self.assertEqual(deferred["required_target_posture"], "in-progress")

            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="handoff-sent",
                safe_frontier="empty",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:02+00:00",
            )
            handed_off = self.gate(
                directory, policy, "2026-08-01T14:20:03+00:00"
            )
            self.assertTrue(handed_off["blocking_permitted"])
            self.assertEqual(handed_off["required_target_posture"], "blocked")
            self.assertFalse(handed_off["manual_resume_required"])

            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="target-acknowledged",
                safe_frontier="empty",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:04+00:00",
            )
            acknowledged = self.gate(
                directory, policy, "2026-08-01T14:20:05+00:00"
            )
            self.assertTrue(acknowledged["blocking_permitted"])
            self.assertEqual(acknowledged["required_target_posture"], "blocked")
            self.assertFalse(acknowledged["manual_resume_required"])

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

    def test_only_direct_sources_can_create_reserved_authority(self) -> None:
        for source_class in supervision_log.DIRECT_AUTHORITY_SOURCE_CLASSES:
            with self.subTest(source_class=source_class):
                with tempfile.TemporaryDirectory() as temporary:
                    result = self.record(
                        Path(temporary),
                        supervision_log.default_policy(self.init_args()),
                        classification="reserved-authority",
                        phase="decision-ready",
                        authority_source_class=source_class,
                    )
                    self.assertFalse(result["duplicate"])
                    self.assertEqual(
                        result["record"]["authority_source_class"], source_class
                    )

        for source_class in (
            "supervisor-steer",
            "codex_delegation",
            "derived-inference",
        ):
            with self.subTest(source_class=source_class):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaisesRegex(
                        supervision_log.SupervisionLogError,
                        "Reserved authority requires",
                    ):
                        self.record(
                            Path(temporary),
                            supervision_log.default_policy(self.init_args()),
                            classification="reserved-authority",
                            phase="decision-ready",
                            authority_source_class=source_class,
                        )

    def test_generic_project_needs_no_native_alignment_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = self.init_args()
            args.target_label = "unrelated-tracker-project"
            args.mission_source_record = "GOAL-DOCUMENT-1234"
            policy = supervision_log.default_policy(args)

            self.record(
                directory,
                policy,
                classification="delegable",
                phase="decision-ready",
                authority_source_class="repository",
                authority_source_record="GOAL-DOCUMENT-1234",
            )
            result = self.gate(directory, policy, "2026-08-01T12:00:01+00:00")

            self.assertEqual(result["action"], "resolve-immediately-and-continue")
            self.assertTrue(result["mission_binding_valid"])
            self.assertEqual(
                result["alignment_operating_mode"], "independent-mission-charter"
            )
            self.assertFalse(result["target_native_alignment_required"])
            self.assertEqual(
                result["target_native_alignment_role"],
                "optional-read-only-corroboration",
            )
            self.assertEqual(
                result["missing_target_alignment_posture"], "unavailable-open"
            )

    def test_supervision_helper_has_no_patent_studio_alignment_dependency(self) -> None:
        helper = HELPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("patent_studio", helper)
        self.assertNotIn("objective_alignment", helper)

    def test_synthetic_supervisor_containment_cannot_circularly_become_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "Reserved authority requires",
            ):
                self.record(
                    Path(temporary),
                    supervision_log.default_policy(self.init_args()),
                    classification="reserved-authority",
                    phase="decision-ready",
                    authority_source_class="supervisor-steer",
                    authority_source_record="EVT-CONTAINMENT-1234",
                    ordinary_means_disabled="yes",
                )

    def test_goal_level_decision_requires_direct_authority_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            accepted = self.record(
                directory,
                policy,
                classification="reserved-authority",
                phase="decision-ready",
                impact_class="goal-blocking",
                independent_mission_review="yes",
            )
            self.assertEqual(accepted["record"]["impact_class"], "goal-blocking")

        for source_class, independent in (
            ("supervisor-steer", "yes"),
            ("tracker", "no"),
        ):
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(supervision_log.SupervisionLogError):
                    self.record(
                        Path(temporary),
                        supervision_log.default_policy(self.init_args()),
                        classification="human-preference",
                        phase="decision-ready",
                        authority_source_class=source_class,
                        impact_class="goal-reversing",
                        independent_mission_review=independent,
                    )

    def test_mission_provenance_persists_across_every_transition_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            transitions = (
                ("decision-ready", 0, "", "2026-08-01T12:00:00+00:00"),
                ("attempt-started", 1, "", "2026-08-01T12:00:01+00:00"),
                ("attempt-unresolved", 1, "", "2026-08-01T12:01:00+00:00"),
                ("attempt-started", 2, "", "2026-08-01T12:01:01+00:00"),
                ("attempt-unresolved", 2, "", "2026-08-01T12:02:00+00:00"),
                ("attempt-started", 3, "", "2026-08-01T12:02:01+00:00"),
                ("attempt-unresolved", 3, "", "2026-08-01T12:03:00+00:00"),
                ("safe-deferred", 3, "safe-deferred", "2026-08-01T12:22:00+00:00"),
                ("handoff-sent", 3, "safe-deferred", "2026-08-01T12:22:01+00:00"),
                ("target-acknowledged", 3, "safe-deferred", "2026-08-01T12:22:02+00:00"),
            )
            for phase, attempt, outcome, now in transitions:
                self.record(
                    directory,
                    policy,
                    classification="missing-fact",
                    phase=phase,
                    safe_frontier="empty",
                    attempt=attempt,
                    outcome=outcome,
                    now=now,
                )

            decision_records = supervision_log.decision_events(
                supervision_log.events(directory / "events.jsonl"), self.decision
            )
            self.assertEqual(len(decision_records), len(transitions))
            for record in decision_records:
                for field in supervision_log.MISSION_IMPACT_FIELDS:
                    self.assertIn(field, record)

            result = self.gate(directory, policy, "2026-08-01T12:22:03+00:00")
            self.assertTrue(result["mission_binding_valid"])
            self.assertTrue(result["authority_provenance_valid"])
            self.assertTrue(result["blocking_permitted"])
            for field in supervision_log.MISSION_IMPACT_FIELDS:
                self.assertEqual(result[field], decision_records[-1][field])

            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "must preserve"
            ):
                self.record(
                    directory,
                    policy,
                    classification="missing-fact",
                    phase="target-acknowledged",
                    safe_frontier="empty",
                    attempt=3,
                    outcome="safe-deferred",
                    authority_source_record="TRACKER-OTHER-1234",
                    now="2026-08-01T12:22:04+00:00",
                )

    def test_stale_mission_root_cannot_validate_consequential_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="reserved-authority",
                phase="decision-ready",
            )
            policy["mission_binding"] = supervision_log.mission_binding_contract(
                "n" * 64, "TRACKER-MISSION-5678"
            )

            result = self.gate(directory, policy, "2026-08-01T12:00:01+00:00")

            self.assertFalse(result["mission_binding_valid"])
            self.assertFalse(result["blocking_permitted"])
            self.assertEqual(result["action"], "challenge-mission-provenance")

    def test_unbound_policy_rejects_new_decision_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            policy = supervision_log.default_policy(self.init_args())
            policy.pop("mission_binding")
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "exact bound mission"
            ):
                self.record(
                    Path(temporary),
                    policy,
                    classification="human-preference",
                    phase="decision-ready",
                )

    def test_role_and_execution_contracts_preserve_provenance_and_successors(self) -> None:
        skill_root = HELPER_PATH.parent.parent.parent
        supervision_policy = skill_root.joinpath(
            "supervise-tracker-runs", "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        implementation_skill = skill_root.joinpath(
            "implement-tracker-blocks", "SKILL.md"
        ).read_text(encoding="utf-8")
        author_skill = skill_root.joinpath(
            "author-implementation-trackers", "SKILL.md"
        ).read_text(encoding="utf-8")
        tracker_template = skill_root.joinpath(
            "author-implementation-trackers",
            "assets",
            "implementation-tracker-template.md",
        ).read_text(encoding="utf-8")

        self.assertIn("Preserve any containment's exact authority source", supervision_policy)
        self.assertIn("never relabel either as direct", supervision_policy)
        self.assertIn("no inferred carry-forward across a Block", implementation_skill)
        self.assertIn("predecessor for proof, not every successor revision", implementation_skill)
        self.assertIn("constrains exact X rather than a later operation", implementation_skill)
        self.assertIn("never substitute for the requested substantive", implementation_skill)
        self.assertIn("tracker-level mission frame", author_skill)
        self.assertIn("### Mission frame", tracker_template)
        self.assertIn("`carry-forward: false`", tracker_template)


if __name__ == "__main__":
    unittest.main()
