#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
import pwd
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
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

    def test_automation_runtime_tracks_the_stable_accepted_release(self) -> None:
        supervision_skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        release_contract = HELPER_PATH.parent.parent.parent.joinpath(
            "docs", "software-factory-skill-releases.md"
        ).read_text(encoding="utf-8")

        stable_path = (
            "~/.codex/software-factory-releases/current/"
            "supervise-tracker-runs/"
        )
        for text in (supervision_skill, policy, release_contract):
            self.assertIn(stable_path, text)
            self.assertIn("next scheduled", text)
            self.assertIn("software-factory-release-promote", text)
        self.assertIn("scripts/skill_release.py promote --repo <repo>", policy)
        self.assertIn("--source-commit <commit>", policy)
        self.assertIn("software-factory-release-acceptance", policy)
        self.assertIn(
            "without asking for another user confirmation",
            " ".join(supervision_skill.split()),
        )
        self.assertIn(
            "Legacy release-pinned automation prompts",
            " ".join(release_contract.split()),
        )

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
        self.assertIn("--capability-reconciliation-base64", supervision_skill)
        self.assertIn("--capability-reconciliation-base64", policy)
        self.assertIn("--capability-reconciliation-base64", reconciliation_contract)
        for text in (supervision_skill, policy, reconciliation_contract):
            self.assertIn("forbids file creation", text)
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
    authority_request = "Implement this tracker in a distinct successor task."
    authority_sha256 = hashlib.sha256(authority_request.encode("utf-8")).hexdigest()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        init = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Transition target",
                "--watcher-thread",
                "transition-watcher-1234",
                "--reviewer-thread",
                "transition-reviewer-1234",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "item-340",
                "--mission-source-sha256",
                self.authority_sha256,
            ]
        )
        with redirect_stdout(io.StringIO()):
            init.func(init)
        self.directory = self.root / self.target
        self.policy = supervision_log.read_json(self.directory / "policy.json")

    def transition_args(self, phase: str, *extra: str) -> argparse.Namespace:
        topology = (
            []
            if "--topology-posture" in extra or "--topology-basis" in extra
            else [
                "--topology-posture",
                "distinct-task",
                "--topology-basis",
                "direct-request",
                "--topology-rationale",
                "The direct request requires one isolated successor task.",
                "--topology-request-text",
                self.authority_request,
            ]
        )
        return supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
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
                "--governing-authority-source-sha256",
                self.authority_sha256,
                *topology,
                "--state-fingerprint",
                f"state-{phase}",
                "--evidence",
                f"evidence-{phase}",
                *extra,
            ]
        )

    def record(self, phase: str, *extra: str) -> dict[str, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_successor_transition_record(
                self.transition_args(phase, *extra)
            )
        return json.loads(output.getvalue())

    def gate(self, authority: str = "unavailable") -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
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
                "load_control_snapshot",
                return_value=(
                    self.directory,
                    self.policy,
                    None,
                    supervision_log.events(self.directory / "events.jsonl"),
                    None,
                    None,
                ),
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

        correction_sha_only = self.transition_args("required")
        correction_sha_only.transition_id = "TRANSITION-SHA-ONLY-1234"
        correction_sha_only.correction_authority_source_sha256 = "e" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "cannot claim a correction disposition",
        ):
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(io.StringIO()),
            ):
                supervision_log.cmd_successor_transition_record(
                    correction_sha_only
                )

        nonterminal_sha_only = self.transition_args(
            "successor-created", "--successor-thread", "successor-1234"
        )
        nonterminal_sha_only.correction_authority_source_sha256 = "e" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "valid only on terminal dispositions",
        ):
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(io.StringIO()),
            ):
                supervision_log.cmd_successor_transition_record(
                    nonterminal_sha_only
                )

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

    def test_distinct_technical_isolation_requires_canonical_owner_event(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not in the canonical owner event ledger",
        ):
            self.record(
                "required",
                "--topology-posture",
                "distinct-task",
                "--topology-basis",
                "technical-isolation",
                "--topology-rationale",
                "A separate filesystem owner is required.",
            )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "migration-only",
        ):
            self.record(
                "required",
                "--topology-posture",
                "distinct-task",
                "--topology-basis",
                "legacy-linear",
                "--topology-rationale",
                "Caller-selected legacy posture must fail.",
            )

        event_record = "EVT-000001"
        supervision_log.append_raw(
            self.directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": event_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": supervision_log.SUCCESSOR_TOPOLOGY_EVENT_KIND,
                "transition_id": self.transition_id,
                "topology_posture": "distinct-task",
                "topology_basis": "technical-isolation",
                "topology_rationale": "A separate filesystem owner is required.",
                "governing_authority_source_class": "direct-user",
                "governing_authority_source_record": "item-340",
                "governing_authority_source_sha256": self.authority_sha256,
                "verifier_id": "transition-reviewer-1234",
                "provenance_status": "accepted-before-entry",
                "policy_sha256": self.policy["policy_sha256"],
                "evidence": ["independent-technical-isolation-review"],
            },
        )
        result = self.record(
            "required",
            "--topology-posture",
            "distinct-task",
            "--topology-basis",
            "technical-isolation",
            "--topology-rationale",
            "A separate filesystem owner is required.",
            "--topology-decision-event-record",
            event_record,
        )
        self.assertEqual(
            result["record"]["topology_decision_event_record_id"], event_record
        )

    def test_direct_request_topology_requires_exact_source_bytes_and_semantics(self) -> None:
        generic_request = "Implement this tracker."
        generic_sha = hashlib.sha256(generic_request.encode("utf-8")).hexdigest()
        other_target = "generic-request-target-1234"
        init = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                other_target,
                "--target-label",
                "Generic request target",
                "--watcher-thread",
                "generic-watcher-1234",
                "--reviewer-thread",
                "generic-reviewer-1234",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "generic-item-1234",
                "--mission-source-sha256",
                generic_sha,
            ]
        )
        with redirect_stdout(io.StringIO()):
            init.func(init)
        args = self.transition_args("required")
        args.target_thread = other_target
        args.governing_authority_source_record = "generic-item-1234"
        args.governing_authority_source_sha256 = generic_sha
        args.topology_request_text = generic_request
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "does not explicitly require a distinct task",
        ):
            with redirect_stdout(io.StringIO()):
                args.func(args)

        args = self.transition_args("required")
        args.topology_request_text = "Create a separate successor task."
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "does not match its canonical direct source",
        ):
            with redirect_stdout(io.StringIO()):
                args.func(args)

        for forbidden in (
            "Implement this tracker without a new task.",
            "Implement this tracker in the current task; avoid a separate thread.",
            "Implement this tracker; use a new task only if technically necessary.",
            "Create a new task for this when technically necessary.",
            "Create a new task for this provided it is feasible.",
            "Create a new task for this depending on feasibility.",
            "Create a new task for this, or stay here.",
            "Create a new task for this. That is at your discretion.",
            "Create a new task for this. Either option is acceptable.",
            "Create a new task for this. Staying here is also acceptable.",
        ):
            self.assertFalse(
                supervision_log.direct_request_requires_distinct_task(forbidden)
            )
        self.assertTrue(
            supervision_log.direct_request_requires_distinct_task(
                self.authority_request
            )
        )

    def test_transition_writer_rejects_conditional_direct_task_sources(self) -> None:
        forbidden_requests = (
            "Create a new task for this when technically necessary.",
            "Create a new task for this provided it is feasible.",
            "Create a new task for this depending on feasibility.",
            "Create a new task for this, or stay here.",
            "Create a new task for this. That is at your discretion.",
            "Create a new task for this. Either option is acceptable.",
            "Create a new task for this. Staying here is also acceptable.",
        )
        for index, request_text in enumerate(forbidden_requests, start=1):
            source_sha256 = hashlib.sha256(request_text.encode("utf-8")).hexdigest()
            target = f"conditional-target-{index}-1234"
            source_record = f"conditional-item-{index}-1234"
            init = supervision_log.parser().parse_args(
                [
                    "--root",
                    str(self.root),
                    "init",
                    "--target-thread",
                    target,
                    "--target-label",
                    "Conditional topology target",
                    "--watcher-thread",
                    f"conditional-watcher-{index}-1234",
                    "--reviewer-thread",
                    f"conditional-reviewer-{index}-1234",
                    "--mission-source-class",
                    "direct-user",
                    "--mission-source-record",
                    source_record,
                    "--mission-source-sha256",
                    source_sha256,
                ]
            )
            with redirect_stdout(io.StringIO()):
                init.func(init)
            args = self.transition_args("required")
            args.target_thread = target
            args.governing_authority_source_record = source_record
            args.governing_authority_source_sha256 = source_sha256
            args.topology_request_text = request_text
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "does not explicitly require a distinct task",
            ):
                with redirect_stdout(io.StringIO()):
                    args.func(args)

    def test_transition_writer_rejects_event_ledger_symlink(self) -> None:
        outside = self.root / "outside-ledger.jsonl"
        outside.write_text("", encoding="utf-8")
        (self.directory / "events.jsonl").symlink_to(outside)
        with self.assertRaises(supervision_log.SupervisionLogError):
            self.record(
                "required",
                "--topology-posture",
                "same-task-new-run",
                "--topology-basis",
                "same-task-default",
                "--topology-rationale",
                "",
            )
        self.assertEqual(outside.read_text(encoding="utf-8"), "")

    def test_public_lazy_owner_migration_rejects_stale_anchor_before_any_mutation(self) -> None:
        policy_path = self.directory / "policy.json"
        history_path = self.directory / "policy-history.jsonl"
        history_path.write_bytes(b"")
        stale_anchor = supervision_log.event_ledger_anchor([])
        stale_anchor["event_count"] = 1
        supervision_log.atomic_json(
            self.directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            stale_anchor,
        )
        policy_before = policy_path.read_bytes()
        history_before = history_path.read_bytes()
        owner_history_path = (
            self.directory / supervision_log.OWNER_ROOT_HISTORY_NAME
        )
        owner_key_directory = (
            self.root / supervision_log.OWNER_ROOT_KEY_DIRECTORY
        )
        owner_artifacts_before = (
            sorted(path.name for path in owner_key_directory.iterdir())
            if owner_key_directory.exists()
            else []
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "event-ledger head is stale or replaced",
        ):
            self.record("required")

        self.assertEqual(policy_path.read_bytes(), policy_before)
        self.assertEqual(history_path.read_bytes(), history_before)
        self.assertFalse(owner_history_path.exists())
        owner_artifacts_after = (
            sorted(path.name for path in owner_key_directory.iterdir())
            if owner_key_directory.exists()
            else []
        )
        self.assertEqual(owner_artifacts_after, owner_artifacts_before)

    def test_legacy_unanchored_transition_is_migrated_once_and_advanced(self) -> None:
        required = self.record("required")["record"]
        policy = supervision_log.read_json(self.directory / "policy.json")
        policy.pop("owner_root_history_required", None)
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.atomic_json(self.directory / "policy.json", policy)
        history = supervision_log.events(self.directory / "policy-history.jsonl")
        history[-1]["policy"] = policy
        previous = None
        rebuilt = []
        for item in history:
            material = {
                key: value
                for key, value in item.items()
                if key not in {"previous_record_sha256", "record_sha256"}
            }
            material["previous_record_sha256"] = previous
            material["record_sha256"] = supervision_log.digest(material)
            previous = material["record_sha256"]
            rebuilt.append(material)
        (self.directory / "policy-history.jsonl").write_bytes(
            b"".join(supervision_log.canonical(item) + b"\n" for item in rebuilt)
        )
        (self.directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME).unlink()
        (self.directory / supervision_log.OWNER_ROOT_HISTORY_NAME).unlink()
        key = (
            self.root
            / supervision_log.OWNER_ROOT_KEY_DIRECTORY
            / (hashlib.sha256(self.target.encode("utf-8")).hexdigest() + ".key")
        )
        key.unlink()

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "survives without its key|cannot be downgraded",
        ):
            self.record(
                "successor-created",
                "--successor-thread",
                "successor-1234",
            )

        key.with_suffix(".state.json").unlink()

        advanced = self.record(
            "successor-created",
            "--successor-thread",
            "successor-1234",
        )["record"]
        self.assertEqual(advanced["phase"], "successor-created")
        migrated = supervision_log.read_json(self.directory / "policy.json")
        self.assertTrue(migrated["owner_root_history_required"])
        self.assertGreater(migrated["policy_version"], policy["policy_version"])
        self.assertEqual(required["transition_id"], advanced["transition_id"])

    def test_caller_strings_cannot_mint_governing_or_correction_authority(self) -> None:
        governing = self.transition_args("required")
        governing.governing_authority_source_record = "invented-governing-item"
        governing.governing_authority_source_sha256 = "e" * 64
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "governing authority is not canonical",
        ):
            with (
                mock.patch.object(
                    supervision_log,
                    "load_policy",
                    return_value=(self.directory, self.policy),
                ),
                redirect_stdout(io.StringIO()),
            ):
                supervision_log.cmd_successor_transition_record(governing)

        required = self.record("required")["record"]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "correction authority is not canonical",
        ):
            self.record(
                "cancelled",
                "--prior-record",
                required["record_id"],
                "--disposition-reason",
                "Invented authority must not retire the transition.",
                "--correction-authority-source-class",
                "direct-user",
                "--correction-authority-source-record",
                "invented-correction-item",
                "--correction-authority-source-sha256",
                "e" * 64,
                "--governing-outcome-effect",
                "continue-same-task",
            )

    def test_same_task_is_default_continuation_and_never_stops_the_source(self) -> None:
        self.record(
            "required",
            "--topology-posture",
            "same-task-new-run",
            "--topology-basis",
            "same-task-default",
            "--topology-rationale",
            "",
        )
        ready = self.gate()
        self.assertEqual(ready["next_action"], "start-same-task-new-run")
        self.assertFalse(ready["human_input_required"])
        self.record(
            "work-started",
            "--topology-posture",
            "same-task-new-run",
            "--topology-basis",
            "same-task-default",
            "--topology-rationale",
            "",
            "--started-block",
            "Block 0",
        )
        started = self.gate()
        self.assertFalse(started["source_stop_permitted"])
        self.assertFalse(started["transition_open"])
        self.assertEqual(started["next_action"], "continue-same-task-run")

    def test_direct_cancellation_retires_control_without_closing_outcome(self) -> None:
        required = self.record("required")["record"]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "correction authority is not canonical"
        ):
            self.record(
                "cancelled",
                "--prior-record",
                required["record_id"],
                "--disposition-reason",
                "The distinct-task premise was invalid.",
                "--correction-authority-source-class",
                "supervisor-steer",
                "--correction-authority-source-record",
                "routed-steer-1234",
                "--correction-authority-source-sha256",
                self.authority_sha256,
                "--governing-outcome-effect",
                "continue-same-task",
            )
        self.record(
            "cancelled",
            "--prior-record",
            required["record_id"],
            "--disposition-reason",
            "The distinct-task premise was invalid.",
            "--correction-authority-source-class",
            "direct-user",
            "--correction-authority-source-record",
            "item-340",
            "--correction-authority-source-sha256",
            self.authority_sha256,
            "--governing-outcome-effect",
            "continue-same-task",
        )
        result = self.gate()
        self.assertFalse(result["transition_open"])
        self.assertFalse(result["source_stop_permitted"])
        self.assertEqual(
            result["next_action"], "continue-governing-outcome-in-source-task"
        )
        self.assertEqual(result["required_target_posture"], "in-progress")

    def test_replacement_is_inactive_until_exact_forward_supersession(self) -> None:
        old = self.record("required")["record"]
        replacement_args = self.transition_args(
            "required", "--replaces-transition", self.transition_id
        )
        replacement_args.transition_id = "TRANSITION-REPLACEMENT-1234"
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(self.directory, self.policy),
            ),
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_successor_transition_record(replacement_args)
        all_events = supervision_log.events(self.directory / "events.jsonl")
        self.assertEqual(
            set(supervision_log.successor_transition_heads(all_events, open_only=True)),
            {self.transition_id},
        )
        self.record(
            "superseded",
            "--prior-record",
            old["record_id"],
            "--disposition-reason",
            "The replacement carries the corrected topology.",
            "--correction-authority-source-class",
            "direct-user",
            "--correction-authority-source-record",
            "item-340",
            "--correction-authority-source-sha256",
            self.authority_sha256,
            "--replacement-transition",
            "TRANSITION-REPLACEMENT-1234",
            "--governing-outcome-effect",
            "continue-replacement-transition",
        )
        all_events = supervision_log.events(self.directory / "events.jsonl")
        self.assertEqual(
            set(supervision_log.successor_transition_heads(all_events, open_only=True)),
            {"TRANSITION-REPLACEMENT-1234"},
        )
        result = self.gate()
        self.assertEqual(result["next_action"], "continue-replacement-transition")
        self.assertFalse(result["source_stop_permitted"])

    def test_expiry_is_bounded_and_cannot_expire_the_outcome_early(self) -> None:
        required = self.record(
            "required",
            "--now",
            "2026-08-09T00:00:00+00:00",
            "--expires-at",
            "2026-08-09T01:00:00+00:00",
        )["record"]
        disposition = (
            "--prior-record",
            required["record_id"],
            "--disposition-reason",
            "The bounded transition window elapsed.",
            "--correction-authority-source-class",
            "direct-user",
            "--correction-authority-source-record",
            "item-340",
            "--correction-authority-source-sha256",
            self.authority_sha256,
            "--governing-outcome-effect",
            "continue-same-task",
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "cannot expire before"
        ):
            self.record(
                "expired",
                "--now",
                "2026-08-09T00:30:00+00:00",
                *disposition,
            )
        self.record(
            "expired",
            "--now",
            "2026-08-09T01:00:00+00:00",
            *disposition,
        )
        result = self.gate()
        self.assertEqual(
            result["next_action"], "continue-governing-outcome-in-source-task"
        )
        self.assertEqual(result["required_target_posture"], "in-progress")

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
                    "load_policy_directory_snapshot",
                    return_value=(self.directory, self.policy, None, None),
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
            "load_control_snapshot",
            return_value=(
                self.directory,
                self.policy,
                None,
                supervision_log.events(self.directory / "events.jsonl"),
                None,
                None,
            ),
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


class PolicyHistoryCompatibilityTests(unittest.TestCase):
    target = "history-target-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "HistoryTarget",
                "--watcher-thread",
                "history-watcher-1234",
                "--reviewer-thread",
                "history-reviewer-1234",
                "--mission-source-class",
                "tracker",
                "--mission-source-record",
                "history-source-1234",
                "--mission-source-sha256",
                "a" * 64,
            ]
        )
        with redirect_stdout(io.StringIO()):
            args.func(args)
        self.base_policy = supervision_log.read_json(
            self.root / self.target / "policy.json"
        )

    def policy(self, version: int) -> dict[str, object]:
        policy = copy.deepcopy(self.base_policy)
        policy["policy_version"] = version
        policy["updated_at"] = f"2026-08-01T00:{version:02d}:00+00:00"
        policy["permissions"]["gmail_self_notification"] = True
        if version >= 8:
            gmail = {
                "delivery_policy": "material-alerts-and-new-evidence-meta-digest",
                "enabled": True,
                "recipient": "me",
                "reply_message_id": "gmail-seed-1234",
                "subject": "Codex Tracker Supervision",
            }
            if version >= 9:
                gmail.update(
                    {
                        "project_key": "MainProject",
                        "thread_scope": "monitored-project",
                    }
                )
            policy["notifications"] = {"gmail": gmail}
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        return policy

    def history(self) -> list[dict[str, object]]:
        return [
            {
                "schema_version": 1,
                "record_id": f"POLICY-{version}",
                "timestamp": f"2026-08-01T00:{version:02d}:00+00:00",
                "kind": "policy-bind",
                "policy": self.policy(version),
            }
            for version in range(1, 35)
        ]

    def rehash(self, policy: dict[str, object]) -> None:
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

    def test_v34_history_accepts_exact_legacy_gmail_scope_upgrade_only(self) -> None:
        history = self.history()
        supervision_log.validate_policy_history_sequence(history, history[-1]["policy"])
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Primary Gmail binding is incomplete",
        ):
            supervision_log.validate_policy(history[7]["policy"])

    def test_v34_history_rejects_legacy_boundary_attacks(self) -> None:
        cases: list[tuple[str, object, str]] = []

        malformed = self.history()
        malformed[7]["policy"]["notifications"]["gmail"]["recipient"] = "other"
        self.rehash(malformed[7]["policy"])
        cases.append(("malformed", malformed, "invalid embedded policy"))

        stale_hash = self.history()
        stale_hash[7]["policy"]["notifications"]["gmail"]["subject"] = "Changed"
        cases.append(("stale-hash", stale_hash, "invalid embedded policy"))

        re_rooted = self.history()[1:]
        cases.append(("re-rooted", re_rooted, "truncated or re-rooted"))

        reordered = self.history()
        reordered[7], reordered[8] = reordered[8], reordered[7]
        cases.append(("reordered", reordered, "sequence or owner differs"))

        owner_divergent = self.history()
        owner_divergent[7]["policy"]["target_thread_id"] = "other-target-1234"
        self.rehash(owner_divergent[7]["policy"])
        cases.append(("owner-divergent", owner_divergent, "sequence or owner differs"))

        semantically_forged = self.history()
        semantically_forged[8]["policy"]["permissions"]["bounded_thread_steer"] = False
        self.rehash(semantically_forged[8]["policy"])
        cases.append(
            ("semantically-forged", semantically_forged, "invalid embedded policy")
        )

        type_confused_reply = self.history()
        for index in (7, 8):
            type_confused_reply[index]["policy"]["notifications"]["gmail"][
                "reply_message_id"
            ] = 1234
            self.rehash(type_confused_reply[index]["policy"])
        cases.append(
            ("type-confused-reply", type_confused_reply, "invalid embedded policy")
        )

        type_confused_project = self.history()
        type_confused_project[8]["policy"]["notifications"]["gmail"][
            "project_key"
        ] = True
        self.rehash(type_confused_project[8]["policy"])
        cases.append(
            (
                "type-confused-project",
                type_confused_project,
                "invalid embedded policy",
            )
        )

        type_confused_subject = self.history()
        for index in (7, 8):
            type_confused_subject[index]["policy"]["notifications"]["gmail"][
                "subject"
            ] = 1234
            self.rehash(type_confused_subject[index]["policy"])
        cases.append(
            (
                "type-confused-subject",
                type_confused_subject,
                "invalid embedded policy",
            )
        )

        malformed_permissions = self.history()
        for index in (7, 8):
            malformed_permissions[index]["policy"]["permissions"] = [
                "gmail_self_notification"
            ]
            self.rehash(malformed_permissions[index]["policy"])
        cases.append(
            (
                "malformed-permissions",
                malformed_permissions,
                "invalid embedded policy",
            )
        )

        current_incompatible = self.history()
        current_incompatible[-1]["policy"]["notifications"]["gmail"] = copy.deepcopy(
            current_incompatible[7]["policy"]["notifications"]["gmail"]
        )
        self.rehash(current_incompatible[-1]["policy"])
        cases.append(
            ("current-incompatible", current_incompatible, "invalid embedded policy")
        )

        for name, history, message in cases:
            with self.subTest(name=name), self.assertRaisesRegex(
                supervision_log.SupervisionLogError, message
            ):
                supervision_log.validate_policy_history_sequence(
                    history, history[-1]["policy"]
                )


class ImplementationRangeControlTests(unittest.TestCase):
    target = "range-target-1234"
    initial_source = "direct-item-100"
    initial_mission_request = "Begin the current implementation mission."
    initial_mission_sha = hashlib.sha256(
        initial_mission_request.encode("utf-8")
    ).hexdigest()
    initial_range_source = "direct-range-item-101"
    initial_request = "implement this tracker"
    initial_sha = hashlib.sha256(initial_request.encode("utf-8")).hexdigest()
    successor_source = "direct-mission-item-300"
    successor_mission_request = "Begin the separately authorized successor mission."
    successor_mission_sha = hashlib.sha256(
        successor_mission_request.encode("utf-8")
    ).hexdigest()
    successor_range_source = "direct-range-item-301"
    successor_range_request = "implement this tracker"
    successor_range_sha = hashlib.sha256(
        successor_range_request.encode("utf-8")
    ).hexdigest()
    later_source = "direct-item-200"
    later_request = "Block 0"
    later_sha = hashlib.sha256(later_request.encode("utf-8")).hexdigest()
    reviewer = "range-reviewer-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tracker = self.root / "tracker.md"
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Range target",
                "--watcher-thread",
                "range-watcher-1234",
                "--reviewer-thread",
                self.reviewer,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                self.initial_source,
                "--mission-source-sha256",
                self.initial_mission_sha,
            ]
        )
        with redirect_stdout(io.StringIO()):
            args.func(args)

    def write_tracker(self, statuses: list[str]) -> None:
        rows = []
        headings = []
        for number, status in enumerate(statuses):
            dependency = "—" if number == 0 else str(number - 1)
            rows.append(
                f"| {number} | Scope {number} | {dependency} | `{status}` |"
            )
            headings.append(
                f"## Block {number} — Scope {number}\n\nStatus: `{status}`\n\n"
                "### Completion evidence\n\nPending.\n\n"
                "### Stop\n\nStop at this Block boundary.\n"
            )
        self.tracker.write_text(
            "| Block | Scope | Depends on | Status |\n"
            "|---:|---|---:|---|\n"
            + "\n".join(rows)
            + "\n\n"
            + "\n".join(headings),
            encoding="utf-8",
        )

    def test_status_table_header_ignores_unrelated_numeric_table_and_normalizes_complete(
        self,
    ) -> None:
        self.tracker.write_text(
            "| Attempt | Duration | Result | Note |\n"
            "|---:|---:|---:|---|\n"
            "| 0 | 12 | 99 | diagnostic |\n"
            "| 1 | 13 | 98 | diagnostic |\n\n"
            "| Block | Scope | Depends on | Owner | Status |\n"
            "|---:|---|---:|---|---|\n"
            "| 0 | Foundation | — | target | `complete` |\n"
            "| 1 | Follow-on | 0 | target | `not-started` |\n\n"
            "## Block 0 — Foundation\n\nStatus: `complete`\n\n"
            "### Completion evidence\n\nAccepted.\n\n"
            "### Stop\n\nStop at this Block boundary.\n\n"
            "## Block 1 — Follow-on\n\nStatus: `not-started`\n\n"
            "### Completion evidence\n\nPending.\n\n"
            "### Stop\n\nStop at this Block boundary.\n",
            encoding="utf-8",
        )
        self.bind()
        gate = self.gate("block-boundary")
        self.assertEqual(gate["accepted_blocks"], [0])
        self.assertEqual(gate["remaining_blocks"], [1])
        self.assertEqual(gate["eligible_blocks"], [1])
        self.assertEqual(gate["next_action"], "continue-next-eligible-block")

    def call(self, *arguments: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), *arguments]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def bind(self, request_text: str = initial_request) -> dict[str, object]:
        source_record = self.initial_range_source
        source_sha256 = self.initial_sha
        if request_text == self.initial_request:
            policy = supervision_log.read_json(
                self.root / self.target / "policy.json"
            )
            if not any(
                item.get("source_record") == source_record
                and item.get("source_sha256") == source_sha256
                for item in policy.get("direct_authority_receipts", [])
            ):
                self.retain_successor_range_authority(
                    source_record=source_record,
                    request_text=request_text,
                )
        else:
            source_sha256 = hashlib.sha256(request_text.encode("utf-8")).hexdigest()
            source_record = f"direct-variant-{source_sha256[:16]}"
            intent, _requested = supervision_log.classify_implementation_request(
                request_text, set(range(32))
            )
            if intent == "full-tracker":
                self.retain_successor_range_authority(
                    source_record=source_record,
                    request_text=request_text,
                )
            else:
                authority_event = self.ingest_direct_authority_event(
                    source_record=source_record,
                    source_sha256=source_sha256,
                )
                self.call(
                    "implementation-range-authority-receipt",
                    "--target-thread",
                    self.target,
                    "--authority-event-record",
                    authority_event,
                )
        return self.call(
            "implementation-range-bind",
            "--target-thread",
            self.target,
            "--range-id",
            "RANGE-1234",
            "--tracker",
            str(self.tracker),
            "--request-text",
            request_text,
            "--authority-source-record",
            source_record,
            "--authority-source-sha256",
            source_sha256,
        )

    def ingest_direct_authority_event(
        self, *, source_record: str, source_sha256: str
    ) -> str:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        current_events = supervision_log.events(directory / "events.jsonl")
        event_record = f"EVT-{len(current_events) + 1:06d}"
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": event_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": supervision_log.DIRECT_AUTHORITY_EVENT_KIND,
                "source_class": "direct-user",
                "source_record": source_record,
                "source_sha256": source_sha256,
                "source_task_id": self.target,
                "source_item_id": source_record,
                "verifier_id": self.reviewer,
                "provenance_status": "verified-before-entry",
                "policy_sha256": policy["policy_sha256"],
                "evidence": [f"app-readback:{self.target}:{source_record}"],
            },
        )
        return event_record

    def ingest_tracker_amendment_event(
        self,
        *,
        old_contract: dict[str, object],
        new_tracker: Path | None = None,
        block_number_map: dict[str, int] | None = None,
    ) -> str:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        current_events = supervision_log.events(directory / "events.jsonl")
        event_record = f"EVT-{len(current_events) + 1:06d}"
        (
            tracker_path,
            tracker_sha256,
            tracker_structure_sha256,
            blocks,
        ) = supervision_log.implementation_tracker_snapshot(
            str(new_tracker or self.tracker)
        )
        old_blocks = list(old_contract["tracker_blocks"])
        new_blocks = sorted(blocks)
        mapping = block_number_map or {str(item): item for item in old_blocks}
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": event_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": supervision_log.TRACKER_AMENDMENT_EVENT_KIND,
                "old_tracker_path": old_contract["tracker_path"],
                "old_tracker_sha256": old_contract["tracker_sha256"],
                "old_tracker_structure_sha256": old_contract[
                    "tracker_structure_sha256"
                ],
                "old_blocks": old_blocks,
                "new_tracker_path": str(tracker_path),
                "new_tracker_sha256": tracker_sha256,
                "new_tracker_structure_sha256": tracker_structure_sha256,
                "new_blocks": new_blocks,
                "block_number_map": mapping,
                "verifier_id": self.reviewer,
                "provenance_status": "accepted-before-entry",
                "policy_sha256": policy["policy_sha256"],
                "evidence": [f"accepted-tracker-amendment:{tracker_sha256}"],
            },
        )
        return event_record

    def gate(self, response_kind: str = "outcome-terminal") -> dict[str, object]:
        return self.call(
            "implementation-range-gate",
            "--target-thread",
            self.target,
            "--response-kind",
            response_kind,
        )

    def admit(
        self,
        *,
        include_binding_inputs: bool = False,
        range_id: str = "RANGE-ADMISSION-1234",
        rollover_records: tuple[str, str, str] | None = None,
        source_record: str | None = None,
        source_sha256: str | None = None,
        request_text: str | None = None,
    ) -> dict[str, object]:
        if (
            include_binding_inputs
            and rollover_records is None
            and source_record is None
            and supervision_log.implementation_range_contract(
                supervision_log.read_json(
                    self.root / self.target / "policy.json"
                )
            )
            is None
        ):
            self.retain_successor_range_authority(
                source_record=self.initial_range_source,
                request_text=self.initial_request,
            )
        arguments = [
            "implementation-range-admit",
            "--target-thread",
            self.target,
        ]
        if include_binding_inputs:
            bound_source_record = source_record or (
                self.successor_range_source
                if rollover_records is not None
                else self.initial_range_source
            )
            bound_request_text = request_text or (
                self.successor_range_request
                if rollover_records is not None
                else self.initial_request
            )
            bound_source_sha256 = source_sha256 or (
                self.successor_range_sha
                if rollover_records is not None
                else self.initial_sha
            )
            arguments.extend(
                [
                    "--range-id",
                    range_id,
                    "--tracker",
                    str(self.tracker),
                    "--request-text",
                    bound_request_text,
                    "--authority-source-record",
                    bound_source_record,
                    "--authority-source-sha256",
                    bound_source_sha256,
                ]
            )
        if rollover_records is not None:
            outcome, lifecycle, activation = rollover_records
            arguments.extend(
                [
                    "--predecessor-outcome-record",
                    outcome,
                    "--predecessor-lifecycle-record",
                    lifecycle,
                    "--mission-activation-record",
                    activation,
                ]
            )
        return self.call(*arguments)

    def append_successor_range_authority_review(
        self,
        *,
        source_record: str | None = None,
        request_text: str | None = None,
        source_kind: str = supervision_log.DIRECT_AUTHORITY_SOURCE_KIND,
    ) -> dict[str, object]:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        current_events = supervision_log.events(directory / "events.jsonl")
        source_record = source_record or self.successor_range_source
        request_text = request_text or self.successor_range_request
        source_bytes = request_text.encode("utf-8")
        provenance: dict[str, object] = {
            "schema_version": 1,
            "kind": supervision_log.DIRECT_AUTHORITY_PROVENANCE_KIND,
            "target_thread_id": self.target,
            "source_task_id": self.target,
            "source_turn_id": "direct-range-turn-301",
            "source_item_id": source_record,
            "source_kind": source_kind,
            "source_text": request_text,
            "source_byte_count": len(source_bytes),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "policy_version": policy["policy_version"],
            "policy_sha256": policy["policy_sha256"],
            "verifier_id": self.reviewer,
            "authorization_record_id": f"EVT-{len(current_events) + 1:06d}",
        }
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": provenance["authorization_record_id"],
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "meta-review",
                "category": supervision_log.DIRECT_AUTHORITY_REVIEW_CATEGORY,
                "status": "accepted",
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": policy["policy_sha256"],
                "evidence": supervision_log.direct_authority_review_evidence(
                    provenance
                ),
            },
        )
        return provenance

    def append_delegated_range_authority_review(
        self,
        *,
        source_task_id: str = "origin-user-thread-5678",
        source_record: str | None = None,
        request_text: str | None = None,
        route_action: str = "continue-current-full-tracker",
    ) -> dict[str, object]:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        source_record = source_record or "origin-user-item-5678"
        request_text = request_text or "implement this tracker"
        self.complete_predecessor_and_start_successor(
            retain_range_authority=False,
            mission_source_record=source_record,
            mission_source_sha256=supervision_log.digest(route_action),
        )
        policy = supervision_log.read_json(directory / "policy.json")
        current_events = supervision_log.events(directory / "events.jsonl")
        route_sources = [
            item
            for item in supervision_log.mission_activation_heads(
                current_events
            ).values()
            if item.get("mission_root")
            == policy["mission_binding"]["mission_root"]
            and item.get("mission_source_record") == source_record
        ]
        self.assertEqual(len(route_sources), 1)
        route_source = route_sources[0]
        route_record_result = self.call(
            "delegated-direct-authority-route-record",
            "--target-thread",
            self.target,
            "--source-record",
            str(route_source["record_id"]),
            "--source-task",
            source_task_id,
            "--source-turn",
            "origin-user-turn-5678",
            "--source-item",
            source_record,
            "--source-text-base64",
            base64.b64encode(request_text.encode("utf-8")).decode("ascii"),
        )
        route_record = next(
            item
            for item in supervision_log.events(directory / "events.jsonl")
            if item.get("record_id") == route_record_result["record_id"]
        )
        self.assertEqual(
            route_record["route_result"]["action_sha256"],
            policy["mission_binding"]["mission_derivation"][
                "controlling_source"
            ]["sha256"],
        )
        source_bytes = request_text.encode("utf-8")
        provenance: dict[str, object] = {
            "schema_version": 1,
            "kind": (
                supervision_log.DELEGATED_DIRECT_AUTHORITY_PROVENANCE_KIND
            ),
            "target_thread_id": self.target,
            "source_task_id": source_task_id,
            "source_turn_id": "origin-user-turn-5678",
            "source_item_id": source_record,
            "source_kind": supervision_log.DIRECT_AUTHORITY_SOURCE_KIND,
            "source_text": request_text,
            "source_byte_count": len(source_bytes),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "policy_version": policy["policy_version"],
            "policy_sha256": policy["policy_sha256"],
            "verifier_id": self.reviewer,
            "authorization_record_id": "",
            "transport_kind": (
                supervision_log.DELEGATED_DIRECT_AUTHORITY_TRANSPORT_KIND
            ),
            "route_purpose": (
                supervision_log.DELEGATED_DIRECT_AUTHORITY_ROUTE_PURPOSE
            ),
            "route_source_record_id": route_source["record_id"],
            "route_source_record_sha256": route_source["record_sha256"],
            "route_record_id": route_record["record_id"],
            "route_record_sha256": route_record["record_sha256"],
            "route_action_sha256": supervision_log.digest(route_action),
            "route_projection_sha256": "",
        }
        provenance["route_projection_sha256"] = supervision_log.digest(
            supervision_log.delegated_direct_authority_route_projection(
                provenance, policy_sha256=policy["policy_sha256"]
            )
        )
        current_events = supervision_log.events(directory / "events.jsonl")
        provenance["authorization_record_id"] = (
            f"EVT-{len(current_events) + 1:06d}"
        )
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": provenance["authorization_record_id"],
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "meta-review",
                "category": (
                    supervision_log.DELEGATED_DIRECT_AUTHORITY_REVIEW_CATEGORY
                ),
                "status": "accepted",
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": policy["policy_sha256"],
                "evidence": supervision_log.direct_authority_review_evidence(
                    provenance
                ),
            },
        )
        return provenance

    def start_current_delegated_activation(self) -> dict[str, object]:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        all_events = supervision_log.events(directory / "events.jsonl")
        activation = next(
            item
            for item in supervision_log.mission_activation_heads(
                all_events
            ).values()
            if item.get("mission_root")
            == policy["mission_binding"]["mission_root"]
        )
        work_record = f"EVT-{len(all_events) + 1:06d}"
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": work_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "escalation",
                "status": "changed-state-review",
                "evidence": ["block-0-work-started"],
                "policy_sha256": policy["policy_sha256"],
            },
        )
        result = self.call(
            "mission-activation-start",
            "--target-thread",
            self.target,
            "--mission-root",
            str(activation["mission_root"]),
            "--activation-policy-sha256",
            str(activation["activation_policy_sha256"]),
            "--first-eligible-work",
            str(activation["first_eligible_work"]),
            "--source-record",
            work_record,
            "--evidence",
            "block-0-work-started",
        )
        return dict(result["record"])

    def retain_successor_range_authority(
        self,
        *,
        source_record: str | None = None,
        request_text: str | None = None,
        source_kind: str = supervision_log.DIRECT_AUTHORITY_SOURCE_KIND,
    ) -> tuple[dict[str, object], dict[str, object]]:
        provenance = self.append_successor_range_authority_review(
            source_record=source_record,
            request_text=request_text,
            source_kind=source_kind,
        )
        encoded = base64.b64encode(supervision_log.canonical(provenance)).decode(
            "ascii"
        )
        ingested = self.call(
            "direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            encoded,
        )
        receipt = self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            str(ingested["record_id"]),
        )
        return ingested, receipt

    def complete_predecessor_and_start_successor(
        self,
        *,
        retain_range_authority: bool = True,
        mission_source_record: str | None = None,
        mission_source_sha256: str | None = None,
    ) -> tuple[str, str, str, dict[str, object]]:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        predecessor_root = policy["mission_binding"]["mission_root"]
        outcome_record = "EVT-RANGE-OUTCOME-100"
        lifecycle_record = "EVT-RANGE-LIFECYCLE-100"
        fingerprint = "a" * 64
        outcome: dict[str, object] = {
            "schema_version": 1,
            "record_id": outcome_record,
            "timestamp": supervision_log.utc_now(),
            "target_thread_id": self.target,
            "kind": "check",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "status": "verified",
            "model": "gpt-5.6-sol",
            "reasoning": "max",
            "state_fingerprint": fingerprint,
            "mission_root": predecessor_root,
            "capability_reconciliation_reviewer_id": self.reviewer,
            "capability_reconciliation_implementation_owner_id": self.target,
            "capability_reconciliation_revision": "b" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
            "evidence": ["predecessor-range-complete"],
            "policy_sha256": policy["policy_sha256"],
        }
        for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS:
            outcome[field] = "c" * 64
        supervision_log.append_raw(directory / "events.jsonl", outcome)
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": lifecycle_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "lifecycle",
                "status": "completed",
                "state_fingerprint": fingerprint,
                "outcome_completion_record_id": outcome_record,
                "evidence": [outcome_record],
                "policy_sha256": policy["policy_sha256"],
            },
        )
        successor = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "mission-successor",
                "--target-thread",
                self.target,
                "--from-mission-root",
                predecessor_root,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                mission_source_record or self.successor_source,
                "--mission-source-sha256",
                mission_source_sha256 or self.successor_mission_sha,
                "--predecessor-disposition",
                "completed",
                "--first-eligible-work",
                "Block-0-freeze-current-baseline",
                "--reason",
                "The completed predecessor is followed by a new direct mission.",
                "--evidence",
                lifecycle_record,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            successor.func(successor)
        result = json.loads(output.getvalue())
        activation = result["mission_activation"]["record_id"]
        if retain_range_authority:
            self.retain_successor_range_authority()
        return outcome_record, lifecycle_record, activation, result

    def test_admission_binds_once_from_canonical_direct_request(self) -> None:
        self.write_tracker(["completed", "not-started"])

        first = self.admit(include_binding_inputs=True)
        second = self.admit()

        self.assertEqual(first["binding"]["range_intent"], "full-tracker")
        self.assertIn("mission_identity", first["binding"])
        self.assertTrue(second["admitted"])
        self.assertTrue(second["duplicate"])
        self.assertTrue(second["implementation_start_permitted"])
        self.assertTrue(second["final_response_gate_required"])
        self.assertEqual(second["range_state"]["remaining_blocks"], [1])

    def test_absent_range_rejects_mission_source_on_bind_and_admit_without_mutation(
        self,
    ) -> None:
        self.write_tracker(["not-started"])
        directory = self.root / self.target
        protected = (
            "policy.json",
            "policy-history.jsonl",
            "events.jsonl",
            supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            supervision_log.OWNER_ROOT_HISTORY_NAME,
        )
        before = {
            name: (
                (directory / name).read_bytes()
                if (directory / name).exists()
                else None
            )
            for name in protected
        }
        tracker_before = self.tracker.read_bytes()

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "identity only, not range authority",
        ):
            self.call(
                "implementation-range-bind",
                "--target-thread",
                self.target,
                "--range-id",
                "RANGE-MISSION-SOURCE-REJECTED",
                "--tracker",
                str(self.tracker),
                "--request-text",
                self.initial_request,
                "--authority-source-record",
                self.initial_source,
                "--authority-source-sha256",
                self.initial_sha,
            )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "identity only, not range authority",
        ):
            self.admit(
                include_binding_inputs=True,
                range_id="RANGE-MISSION-SOURCE-REJECTED",
                source_record=self.initial_source,
                source_sha256=self.initial_sha,
                request_text=self.initial_request,
            )

        for name, raw in before.items():
            self.assertEqual(
                (directory / name).read_bytes()
                if (directory / name).exists()
                else None,
                raw,
            )
        self.assertEqual(self.tracker.read_bytes(), tracker_before)
        self.assertIsNone(
            supervision_log.implementation_range_contract(
                supervision_log.read_json(directory / "policy.json")
            )
        )

    def test_admission_rejects_missing_canonical_binding_inputs(self) -> None:
        self.write_tracker(["not-started"])

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "cannot start without canonical range binding inputs",
        ):
            self.admit()

    def test_admission_advances_status_only_tracker_currentness(self) -> None:
        self.write_tracker(["not-started", "not-started"])
        self.bind()
        self.write_tracker(["completed", "not-started"])

        amended = self.admit()
        current = self.admit()

        self.assertFalse(amended["contraction"])
        self.assertEqual(amended["binding"]["history"][-1]["operation"], "tracker-amended")
        self.assertTrue(current["range_binding_current"])
        self.assertEqual(current["range_state"]["accepted_blocks"], [0])

    def test_admission_fails_closed_on_unaccepted_structural_change(self) -> None:
        self.write_tracker(["not-started", "not-started"])
        self.bind()
        self.tracker.write_text(
            self.tracker.read_text(encoding="utf-8").replace(
                "Stop at this Block boundary.",
                "Stop after exact acceptance.",
                1,
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an accepted structural amendment",
        ):
            self.admit()

    def test_completed_predecessor_rolls_to_fresh_mission_range_atomically(
        self,
    ) -> None:
        self.write_tracker(["completed", "completed"])
        predecessor = self.bind()["binding"]
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        events_before = (directory / "events.jsonl").read_bytes()
        history_before = supervision_log.events(
            directory / "policy-history.jsonl"
        )
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)

        result = self.admit(
            include_binding_inputs=True,
            range_id="RANGE-SUCCESSOR-5678",
            rollover_records=records,
        )

        current = supervision_log.read_json(directory / "policy.json")
        history_after = supervision_log.events(
            directory / "policy-history.jsonl"
        )
        self.assertEqual((directory / "events.jsonl").read_bytes(), events_before)
        self.assertEqual(len(history_after), len(history_before) + 1)
        self.assertEqual(
            history_after[-2]["policy"]["implementation_range"], predecessor
        )
        self.assertEqual(
            current["implementation_range"]["range_id"],
            "RANGE-SUCCESSOR-5678",
        )
        self.assertNotEqual(
            current["implementation_range"]["genesis_sha256"],
            predecessor["genesis_sha256"],
        )
        self.assertEqual(
            current["implementation_range"]["history"][0]["sequence"], 1
        )
        self.assertEqual(
            current["implementation_range"]["history"][0][
                "predecessor_range"
            ]["range_id"],
            predecessor["range_id"],
        )
        self.assertEqual(result["mission_activation_record"], records[2])
        duplicate = self.admit(
            include_binding_inputs=True,
            range_id="RANGE-SUCCESSOR-5678",
            source_record=self.successor_range_source,
            source_sha256=self.successor_range_sha,
            request_text=self.successor_range_request,
        )
        self.assertTrue(duplicate["duplicate"])
        gate = self.gate("final-response")
        self.assertTrue(gate["range_binding_current"])
        self.assertEqual(gate["requested_blocks"], list(range(8)))
        self.assertEqual(gate["accepted_blocks"], [])
        self.assertEqual(gate["eligible_blocks"], [0])
        self.assertFalse(gate["final_response_permitted"])

    def test_mission_source_digest_cannot_substitute_for_range_authority(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor(
            retain_range_authority=False
        )[:3]
        directory = self.root / self.target
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "identity only, not range authority",
        ):
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
                source_record=self.successor_source,
                source_sha256=self.successor_mission_sha,
                request_text=self.successor_mission_request,
            )

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_terminal_delivery_and_routed_sources_cannot_be_ingested(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        self.complete_predecessor_and_start_successor(
            retain_range_authority=False
        )
        directory = self.root / self.target
        cases = (
            (
                "direct-item-3209",
                "Deliver the terminal reports, verify readback, and shut down supervision.",
                supervision_log.DIRECT_AUTHORITY_SOURCE_KIND,
                "does not establish full-tracker|does not authorize the full tracker",
            ),
            (
                "routed-item-3209",
                "codex_delegation: implement this tracker",
                "codex-delegation",
                "source kind|Routed codex_delegation",
            ),
        )
        for source_record, request_text, source_kind, message in cases:
            with self.subTest(source_record=source_record):
                provenance = self.append_successor_range_authority_review(
                    source_record=source_record,
                    request_text=request_text,
                    source_kind=source_kind,
                )
                before = {
                    name: (directory / name).read_bytes()
                    for name in (
                        "policy.json",
                        "policy-history.jsonl",
                        "events.jsonl",
                        supervision_log.EVENT_LEDGER_ANCHOR_NAME,
                    )
                }
                encoded = base64.b64encode(
                    supervision_log.canonical(provenance)
                ).decode("ascii")
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, message
                ):
                    self.call(
                        "direct-authority-ingest",
                        "--target-thread",
                        self.target,
                        "--provenance-base64",
                        encoded,
                    )
                for name, raw in before.items():
                    self.assertEqual((directory / name).read_bytes(), raw)

    def test_exact_direct_authority_ingestion_is_idempotent_and_one_source(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        self.complete_predecessor_and_start_successor(
            retain_range_authority=False
        )
        directory = self.root / self.target
        provenance = self.append_successor_range_authority_review()
        encoded = base64.b64encode(
            supervision_log.canonical(provenance)
        ).decode("ascii")

        first = self.call(
            "direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            encoded,
        )
        first_events = (directory / "events.jsonl").read_bytes()
        first_anchor = (
            directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME
        ).read_bytes()
        duplicate = self.call(
            "direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            encoded,
        )

        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["record_id"], first["record_id"])
        self.assertEqual((directory / "events.jsonl").read_bytes(), first_events)
        self.assertEqual(
            (directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME).read_bytes(),
            first_anchor,
        )

        changed = copy.deepcopy(provenance)
        changed["source_text"] = "implement this tracker!"
        changed_bytes = changed["source_text"].encode("utf-8")
        changed["source_byte_count"] = len(changed_bytes)
        changed["source_sha256"] = hashlib.sha256(changed_bytes).hexdigest()
        changed_encoded = base64.b64encode(
            supervision_log.canonical(changed)
        ).decode("ascii")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "review does not bind|different provenance",
        ):
            self.call(
                "direct-authority-ingest",
                "--target-thread",
                self.target,
                "--provenance-base64",
                changed_encoded,
            )
        self.assertEqual((directory / "events.jsonl").read_bytes(), first_events)

    def test_exact_delegated_direct_authority_starts_full_tracker_range(
        self,
    ) -> None:
        self.write_tracker(["not-started"] * 8)
        request_text = (
            "DIRECT-USER ROUTED CONTINUATION — move all work into this main "
            "thread.\nThis is a new full-tracker mission/range.\n"
            "Invoke $implement-tracker-blocks and execute the COMPLETE Blocks "
            "0–7 objective automatically.\n"
            + ("Preserve the exact current evidence and owner boundaries. " * 70)
        )
        provenance = self.append_delegated_range_authority_review(
            request_text=request_text
        )
        encoded = base64.b64encode(
            supervision_log.canonical(provenance)
        ).decode("ascii")

        ingested = self.call(
            "direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            encoded,
        )
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            str(ingested["record_id"]),
        )
        bound = self.call(
            "implementation-range-admit",
            "--target-thread",
            self.target,
            "--range-id",
            "RANGE-DELEGATED-5678",
            "--tracker",
            str(self.tracker),
            "--request-text",
            str(provenance["source_text"]),
            "--authority-source-record",
            str(provenance["source_item_id"]),
            "--authority-source-sha256",
            str(provenance["source_sha256"]),
        )
        gate = self.gate("final-response")

        self.assertEqual(
            ingested["source_record"], provenance["source_item_id"]
        )
        self.assertGreater(provenance["source_byte_count"], 1200)
        self.assertNotEqual(
            provenance["route_action_sha256"],
            supervision_log.digest(provenance["source_text"]),
        )
        self.assertEqual(
            bound["binding"]["range_intent"], "full-tracker"
        )
        self.assertEqual(gate["requested_blocks"], list(range(8)))
        self.assertEqual(gate["eligible_blocks"], [0])
        self.assertFalse(gate["final_response_permitted"])

    def test_delegated_route_owner_rejects_changed_direct_source_bytes(
        self,
    ) -> None:
        provenance = self.append_delegated_range_authority_review()
        directory = self.root / self.target
        before = (directory / "events.jsonl").read_bytes()

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "different owner evidence",
        ):
            self.call(
                "delegated-direct-authority-route-record",
                "--target-thread",
                self.target,
                "--source-record",
                str(provenance["route_source_record_id"]),
                "--source-task",
                str(provenance["source_task_id"]),
                "--source-turn",
                str(provenance["source_turn_id"]),
                "--source-item",
                str(provenance["source_item_id"]),
                "--source-text-base64",
                base64.b64encode(b"implement the complete tracker").decode(
                    "ascii"
                ),
            )

        self.assertEqual((directory / "events.jsonl").read_bytes(), before)

    def test_delegated_authority_rejects_changed_route_packet(
        self,
    ) -> None:
        self.write_tracker(["not-started"] * 2)
        provenance = self.append_delegated_range_authority_review()
        directory = self.root / self.target
        before = {
            name: (directory / name).read_bytes()
            for name in (
                "policy.json",
                "policy-history.jsonl",
                "events.jsonl",
                supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            )
        }
        cases = {
            "action": {**provenance, "route_action_sha256": "f" * 64},
            "projection": {
                **provenance,
                "route_projection_sha256": "e" * 64,
            },
            "source": {
                **provenance,
                "route_source_record_sha256": "d" * 64,
            },
            "unowned-record": {
                **provenance,
                "route_record_id": provenance["route_source_record_id"],
                "route_record_sha256": provenance[
                    "route_source_record_sha256"
                ],
            },
        }
        for case, changed in cases.items():
            with self.subTest(case=case):
                encoded = base64.b64encode(
                    supervision_log.canonical(changed)
                ).decode("ascii")
                with self.assertRaises(
                    supervision_log.SupervisionLogError
                ):
                    self.call(
                        "direct-authority-ingest",
                        "--target-thread",
                        self.target,
                        "--provenance-base64",
                        encoded,
                    )
                for name, raw in before.items():
                    self.assertEqual((directory / name).read_bytes(), raw)

    def test_delegated_ingest_rejects_nonhead_activation_source(self) -> None:
        provenance = self.append_delegated_range_authority_review()
        self.start_current_delegated_activation()
        directory = self.root / self.target
        before = (directory / "events.jsonl").read_bytes()
        encoded = base64.b64encode(
            supervision_log.canonical(provenance)
        ).decode("ascii")

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "current activation head",
        ):
            self.call(
                "direct-authority-ingest",
                "--target-thread",
                self.target,
                "--provenance-base64",
                encoded,
            )

        self.assertEqual((directory / "events.jsonl").read_bytes(), before)

    def test_delegated_admission_rejects_nonhead_activation_source(self) -> None:
        self.write_tracker(["not-started"] * 8)
        provenance = self.append_delegated_range_authority_review()
        encoded = base64.b64encode(
            supervision_log.canonical(provenance)
        ).decode("ascii")
        ingested = self.call(
            "direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            encoded,
        )
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            str(ingested["record_id"]),
        )
        self.start_current_delegated_activation()
        directory = self.root / self.target
        before = {
            name: (directory / name).read_bytes()
            for name in (
                "policy.json",
                "policy-history.jsonl",
                "events.jsonl",
                supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            )
        }

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "current activation head",
        ):
            self.call(
                "implementation-range-admit",
                "--target-thread",
                self.target,
                "--range-id",
                "RANGE-DELEGATED-STALE-5678",
                "--tracker",
                str(self.tracker),
                "--request-text",
                str(provenance["source_text"]),
                "--authority-source-record",
                str(provenance["source_item_id"]),
                "--authority-source-sha256",
                str(provenance["source_sha256"]),
            )

        for name, raw in before.items():
            self.assertEqual((directory / name).read_bytes(), raw)

    def test_delegated_route_owner_rejects_removed_action_input(
        self,
    ) -> None:
        provenance = self.append_delegated_range_authority_review()
        directory = self.root / self.target
        before = (directory / "events.jsonl").read_bytes()

        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            supervision_log.parser().parse_args(
                [
                    "--root",
                    str(self.root),
                    "delegated-direct-authority-route-record",
                    "--target-thread",
                    self.target,
                    "--source-record",
                    str(provenance["route_source_record_id"]),
                    "--source-task",
                    str(provenance["source_task_id"]),
                    "--source-turn",
                    str(provenance["source_turn_id"]),
                    "--source-item",
                    str(provenance["source_item_id"]),
                    "--action",
                    "different-target-action",
                    "--source-text-base64",
                    base64.b64encode(
                        str(provenance["source_text"]).encode("utf-8")
                    ).decode("ascii"),
                ]
            )

        self.assertEqual((directory / "events.jsonl").read_bytes(), before)

    def test_delegated_route_owner_rejects_unrelated_source_event(self) -> None:
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        current_events = supervision_log.events(directory / "events.jsonl")
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": f"EVT-{len(current_events) + 1:06d}",
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "notification",
                "category": "gmail",
                "status": "observed",
                "policy_sha256": policy["policy_sha256"],
                "evidence": [self.initial_source],
            },
        )
        route_source = supervision_log.events(directory / "events.jsonl")[-1]
        before = (directory / "events.jsonl").read_bytes()

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "exact current-mission activation",
        ):
            self.call(
                "delegated-direct-authority-route-record",
                "--target-thread",
                self.target,
                "--source-record",
                str(route_source["record_id"]),
                "--source-task",
                "origin-user-thread-5678",
                "--source-turn",
                "origin-user-turn-5678",
                "--source-item",
                self.initial_source,
                "--source-text-base64",
                base64.b64encode(
                    self.initial_mission_request.encode("utf-8")
                ).decode("ascii"),
            )

        self.assertEqual((directory / "events.jsonl").read_bytes(), before)

    def test_stale_or_ambiguous_receipt_rejects_fresh_admission(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        receipt = copy.deepcopy(policy["direct_authority_receipts"][-1])
        ambiguous = copy.deepcopy(policy)
        ambiguous["direct_authority_receipts"].append(receipt)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "one exact retained authority receipt",
        ):
            supervision_log.retained_full_tracker_authority(
                ambiguous,
                all_events=supervision_log.events(directory / "events.jsonl"),
                policy_history=supervision_log.events(
                    directory / "policy-history.jsonl"
                ),
                source_record=self.successor_range_source,
                source_sha256=self.successor_range_sha,
                require_current_receipt=True,
                request_text=self.successor_range_request,
            )
        supervision_log.write_policy_version(
            directory,
            policy,
            kind="test-authority-currentness-drift",
            reason="Advance policy to prove that a stale receipt cannot bind a range.",
            evidence_values=[str(receipt["source_event_record_id"])],
        )
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "authority receipt is stale",
        ):
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
            )

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_gate_reports_predecessor_range_noncurrent_after_mission_change(
        self,
    ) -> None:
        self.write_tracker(["completed", "completed"])
        self.bind()
        self.complete_predecessor_and_start_successor()

        result = self.gate("final-response")

        self.assertFalse(result["range_binding_current"])
        self.assertEqual(result["range_binding_posture"], "noncurrent")
        self.assertIn("different mission", result["suppression_cause"])
        self.assertFalse(result["final_response_permitted"])
        self.assertEqual(result["required_target_posture"], "in-progress")

    def test_same_mission_replacement_is_rejected_without_policy_mutation(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        directory = self.root / self.target
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()
        self.tracker = self.root / "same-mission-replacement.md"
        self.write_tracker(["not-started"])

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Same-mission admission cannot replace",
        ):
            self.admit(
                include_binding_inputs=True,
                rollover_records=("EVT-A", "EVT-B", "EVT-C"),
            )

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_nonterminal_predecessor_rejects_rollover_without_policy_mutation(
        self,
    ) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires a completed predecessor range",
        ):
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
            )

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_wrong_activation_and_reused_range_id_reject_without_mutation(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        predecessor = self.bind()["binding"]
        outcome, lifecycle, _activation, _successor = (
            self.complete_predecessor_and_start_successor()
        )
        directory = self.root / self.target
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "pending current-mission activation|evidence chronology",
        ):
            self.admit(
                include_binding_inputs=True,
                rollover_records=(outcome, lifecycle, lifecycle),
            )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "cannot reuse an implementation range ID",
        ):
            self.admit(
                include_binding_inputs=True,
                range_id=predecessor["range_id"],
                rollover_records=(outcome, lifecycle, _activation),
            )

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_rollover_revalidates_event_head_and_tracker_under_owner_lock(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()

        with mock.patch.object(
            supervision_log, "write_policy_version"
        ) as write_policy:
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
            )
        validator = write_policy.call_args.kwargs["pre_mutation_validator"]
        current_policy = supervision_log.read_json(directory / "policy.json")
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": "EVT-CONCURRENT-RANGE-CHANGE",
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "check",
                "category": "concurrent-state",
                "policy_sha256": current_policy["policy_sha256"],
            },
        )
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "event state changed before range rollover",
            ):
                validator(directory_fd, current_policy)
        finally:
            os.close(directory_fd)

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_rollover_revalidates_retained_authority_under_owner_lock(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()

        with mock.patch.object(
            supervision_log, "write_policy_version"
        ) as write_policy:
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
            )
        validator = write_policy.call_args.kwargs["pre_mutation_validator"]
        current_policy = supervision_log.read_json(directory / "policy.json")
        current_policy["direct_authority_receipts"] = []
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "retained authority receipt",
            ):
                validator(directory_fd, current_policy)
        finally:
            os.close(directory_fd)

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_rollover_rejects_tracker_drift_under_owner_lock(self) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)
        policy_before = (directory / "policy.json").read_bytes()
        history_before = (directory / "policy-history.jsonl").read_bytes()

        with mock.patch.object(
            supervision_log, "write_policy_version"
        ) as write_policy:
            self.admit(
                include_binding_inputs=True,
                rollover_records=records,
            )
        validator = write_policy.call_args.kwargs["pre_mutation_validator"]
        current_policy = supervision_log.read_json(directory / "policy.json")
        self.tracker.write_text(
            self.tracker.read_text(encoding="utf-8").replace(
                "Scope 7", "Drifted scope 7", 1
            ),
            encoding="utf-8",
        )
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "tracker changed before range rollover",
            ):
                validator(directory_fd, current_policy)
        finally:
            os.close(directory_fd)

        self.assertEqual((directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (directory / "policy-history.jsonl").read_bytes(), history_before
        )

    def test_absent_range_returns_structured_nonterminal_repair(self) -> None:
        result = self.gate("final-response")

        self.assertFalse(result["range_binding_current"])
        self.assertEqual(result["range_binding_posture"], "absent")
        self.assertFalse(result["final_response_permitted"])
        self.assertFalse(result["implementation_start_permitted"])
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(
            result["next_action"],
            "continue-local-safe-frontier-and-repair-binding",
        )
        self.assertEqual(
            result["failure_mode_if_returned"],
            "FM-UNAUTHORIZED-EARLY-RETURN",
        )
        self.assertFalse(result["manual_resume_required"])
        self.assertFalse(result["human_input_required"])

    def test_noncurrent_tracker_returns_structured_nonterminal_repair(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        self.tracker.write_text(
            self.tracker.read_text(encoding="utf-8").replace(
                "Scope 1", "Changed scope 1"
            ),
            encoding="utf-8",
        )

        result = self.gate("final-response")

        self.assertFalse(result["range_binding_current"])
        self.assertEqual(result["range_binding_posture"], "noncurrent")
        self.assertFalse(result["final_response_permitted"])
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(
            result["next_action"],
            "continue-local-safe-frontier-and-repair-binding",
        )
        self.assertIn("changed without an accepted", result["suppression_cause"])

    def test_fresh_range_with_missing_receipt_returns_structured_repair(
        self,
    ) -> None:
        self.write_tracker(["completed"])
        self.bind()
        records = self.complete_predecessor_and_start_successor()[:3]
        directory = self.root / self.target
        self.tracker = self.root / "successor-tracker.md"
        self.write_tracker(["not-started"] * 8)
        self.admit(
            include_binding_inputs=True,
            range_id="RANGE-SUCCESSOR-5678",
            rollover_records=records,
        )
        policy = supervision_log.read_json(directory / "policy.json")
        policy["direct_authority_receipts"] = []
        supervision_log.write_policy_version(
            directory,
            policy,
            kind="test-authority-receipt-removal",
            reason="Prove that a fresh range fails closed when its receipt is absent.",
            evidence_values=["missing-range-authority-receipt"],
        )

        result = self.gate("final-response")

        self.assertFalse(result["range_binding_current"])
        self.assertFalse(result["implementation_start_permitted"])
        self.assertFalse(result["final_response_permitted"])
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertIn(
            "retained authority receipt", result["suppression_cause"]
        )

    def test_remaining_range_rejects_every_process_and_response_boundary(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()

        for response_kind in supervision_log.IMPLEMENTATION_RANGE_RESPONSE_KINDS:
            with self.subTest(response_kind=response_kind):
                result = self.gate(response_kind)
                self.assertFalse(result["final_response_permitted"])
                self.assertEqual(
                    result["required_target_posture"], "in-progress"
                )
                self.assertEqual(
                    result["next_action"], "continue-next-eligible-block"
                )
                self.assertFalse(result["process_boundary_implies_completion"])
                self.assertFalse(result["manual_resume_required"])
                self.assertFalse(result["human_input_required"])

    def test_exact_completed_block_request_keeps_its_block_return_boundary(self) -> None:
        self.write_tracker(["completed", "completed"])
        self.bind("Block 1")

        boundary = self.gate("block-boundary")
        final = self.gate("final-response")

        self.assertTrue(boundary["range_binding_current"])
        self.assertTrue(boundary["final_response_permitted"])
        self.assertEqual(
            boundary["next_action"], "requested-block-boundary-satisfied"
        )
        self.assertTrue(final["final_response_permitted"])
        self.assertEqual(
            final["next_action"], "requested-range-final-response-satisfied"
        )

    def test_completed_multi_block_request_cannot_use_an_internal_block_return(self) -> None:
        self.write_tracker(["completed", "completed"])
        self.bind("Blocks 0-1")

        result = self.gate("block-boundary")

        self.assertFalse(result["final_response_permitted"])
        self.assertEqual(result["next_action"], "continue-governing-outcome")

    def test_push_boundary_is_explicit_and_never_implies_completion(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()

        result = self.gate("push-boundary")

        self.assertFalse(result["final_response_permitted"])
        self.assertFalse(result["process_boundary_implies_completion"])
        self.assertEqual(result["next_action"], "continue-next-eligible-block")

    def test_durability_pending_cannot_false_block_remaining_range(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        baseline = self.gate("final-response")
        directory = self.root / self.target
        before = {
            path.name: path.read_bytes()
            for path in directory.iterdir()
            if path.is_file()
        }

        for publication_status in ("unavailable", "failed"):
            with self.subTest(publication_status=publication_status):
                release = self.call(
                    "skill-release-publication-gate",
                    "--target-thread",
                    self.target,
                    "--publication-status",
                    publication_status,
                    "--publication-retry-trigger",
                    "Retry the exact non-force upstream publication.",
                )
                after = self.gate("final-response")
                for field in (
                    "final_response_permitted",
                    "required_target_posture",
                    "next_action",
                    "governing_outcome_currentness_sha256",
                ):
                    self.assertEqual(after[field], baseline[field])
                self.assertTrue(release["durability_pending"])
                self.assertFalse(release["remote_durability_claim_permitted"])
                self.assertTrue(
                    release["signed_local_activation_publication_eligible"]
                )
                self.assertTrue(
                    release[
                        "post_activation_role_refresh_publication_eligible"
                    ]
                )
                self.assertTrue(
                    release["local_effectiveness_publication_eligible"]
                )
                self.assertEqual(release["final_response_effect"], "none")
                self.assertEqual(
                    release["required_target_posture_effect"], "none"
                )

        after_files = {
            path.name: path.read_bytes()
            for path in directory.iterdir()
            if path.is_file()
        }
        self.assertEqual(after_files, before)

    def test_durability_pending_cannot_false_block_satisfied_range(self) -> None:
        self.write_tracker(["completed", "completed"])
        self.bind("Block 1")
        baseline = self.gate("final-response")

        release = self.call(
            "skill-release-publication-gate",
            "--target-thread",
            self.target,
            "--publication-status",
            "failed",
            "--publication-retry-trigger",
            "Retry the exact non-force upstream publication.",
        )
        after = self.gate("final-response")

        self.assertTrue(baseline["final_response_permitted"])
        self.assertEqual(after, baseline)
        self.assertEqual(
            release["publication_blocks_only"], "remote-durability-claim"
        )

    def test_publication_projection_requires_an_autonomous_pending_retry(self) -> None:
        self.write_tracker(["completed"])
        self.bind("Block 0")

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires an autonomous publication retry trigger",
        ):
            self.call(
                "skill-release-publication-gate",
                "--target-thread",
                self.target,
                "--publication-status",
                "unavailable",
            )

        published = self.call(
            "skill-release-publication-gate",
            "--target-thread",
            self.target,
            "--publication-status",
            "published",
        )
        self.assertFalse(published["durability_pending"])
        self.assertTrue(published["remote_durability_claim_permitted"])
        self.assertFalse(published["publication_retry_required"])
        self.assertIsNone(published["publication_retry_trigger_sha256"])

    def rewrite_owner_root_without_external_authority(self) -> None:
        directory = self.root / self.target
        history = supervision_log.events(directory / "policy-history.jsonl")
        all_events = supervision_log.events(directory / "events.jsonl")
        material = {
            "schema_version": 1,
            "record_id": "OWNER-ROOT-000001",
            "timestamp": supervision_log.utc_now(),
            "kind": "supervision-owner-root",
            "sequence": 1,
            **supervision_log.owner_root_material(history, all_events),
            "previous_record_sha256": None,
            "owner_hmac_sha256": "0" * 64,
        }
        material["record_sha256"] = supervision_log.digest(material)
        (directory / supervision_log.OWNER_ROOT_HISTORY_NAME).write_bytes(
            supervision_log.canonical(material) + b"\n"
        )

    def test_skill_only_full_range_survives_inserted_prerequisites_and_continues(self) -> None:
        self.write_tracker(["completed", "not-started"])
        request_text = (
            "[$implement-tracker-blocks]"
            "(/repo/implement-tracker-blocks/SKILL.md)\n "
        )
        binding = self.bind(request_text)["binding"]
        self.assertEqual(
            binding["history"][0]["request_text_sha256"],
            hashlib.sha256(request_text.encode("utf-8")).hexdigest(),
        )
        self.write_tracker(["completed", "not-started", "not-started"])
        amendment_event = self.ingest_tracker_amendment_event(
            old_contract=binding
        )
        self.call(
            "implementation-range-amend",
            "--target-thread",
            self.target,
            "--tracker",
            str(self.tracker),
            "--amendment-event-record",
            amendment_event,
        )
        result = self.gate()
        self.assertEqual(result["requested_blocks"], [0, 1, 2])
        self.assertEqual(result["eligible_blocks"], [1])
        self.assertEqual(result["next_action"], "continue-next-eligible-block")
        self.assertEqual(result["severity_if_returned"], "critical")

    def test_exact_skill_invocation_binds_full_tracker_without_changing_source_bytes(self) -> None:
        self.write_tracker(["completed", "not-started"])
        request_text = (
            "[$implement-tracker-blocks]"
            "(/Users/ethanstillman/code/software_factory/"
            "implement-tracker-blocks/SKILL.md) for the implementation tracker\n"
        )
        source_sha256 = hashlib.sha256(request_text.encode("utf-8")).hexdigest()

        self.assertEqual(len(request_text.encode("utf-8")), 137)
        self.assertEqual(
            source_sha256,
            "ff144b6e23b4fb416d8fac84731a9f26c2ef3d2dc9d8ba9d59ffdd029a3aa601",
        )
        binding = self.bind(request_text)["binding"]
        self.assertEqual(binding["range_intent"], "full-tracker")
        self.assertEqual(binding["explicit_blocks"], [])
        self.assertEqual(
            binding["history"][0]["request_text_sha256"], source_sha256
        )

    def test_skill_invocation_masks_no_path_outside_its_exact_target(self) -> None:
        invocation = (
            "[$implement-tracker-blocks]"
            "(/Users/example/implement-tracker-blocks/SKILL.md)"
        )
        rejected = (
            f"{invocation} for the implementation tracker /Users/example/other",
            "[$implement-tracker-blocks](/Users/example/unclosed for the implementation tracker",
            "[$implement-tracker-blocks](\n/Users/example/SKILL.md) for the implementation tracker",
            "/Users/example/implement-tracker-blocks/SKILL.md",
            "file:///Users/example/implement-tracker-blocks/SKILL.md",
            r"C:\Users\example\implement-tracker-blocks\SKILL.md",
        )

        for request_text in rejected:
            with self.subTest(request_text=request_text):
                with self.assertRaises(supervision_log.SupervisionLogError):
                    supervision_log.classify_implementation_request(
                        request_text, {0, 1}
                    )

    def test_caller_selected_tracker_replacement_cannot_truncate_full_range(self) -> None:
        self.write_tracker(["completed", "not-started", "not-started"])
        self.bind()
        replacement = self.root / "replacement.md"
        original = self.tracker
        self.tracker = replacement
        try:
            self.write_tracker(["completed"])
        finally:
            self.tracker = original
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical tracker-amendment event record",
        ):
            self.call(
                "implementation-range-amend",
                "--target-thread",
                self.target,
                "--tracker",
                str(replacement),
            )
        gate = self.gate()
        self.assertEqual(gate["requested_blocks"], [0, 1, 2])
        self.assertEqual(gate["remaining_blocks"], [1, 2])

    def test_same_block_set_contract_change_requires_structural_amendment(self) -> None:
        self.write_tracker(["completed", "not-started", "not-started"])
        binding = self.bind()["binding"]
        original = self.tracker.read_text(encoding="utf-8")
        changed = original.replace(
            "| 2 | Scope 2 | 1 | `not-started` |",
            "| 2 | Changed scope | — | `not-started` |",
        ).replace(
            "## Block 2 — Scope 2",
            "## Block 2 — Changed scope",
        )
        self.tracker.write_text(changed, encoding="utf-8")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical tracker-amendment event record",
        ):
            self.call(
                "implementation-range-amend",
                "--target-thread",
                self.target,
                "--tracker",
                str(self.tracker),
            )
        event_record = self.ingest_tracker_amendment_event(
            old_contract=binding
        )
        result = self.call(
            "implementation-range-amend",
            "--target-thread",
            self.target,
            "--tracker",
            str(self.tracker),
            "--amendment-event-record",
            event_record,
        )
        self.assertNotEqual(
            result["binding"]["tracker_structure_sha256"],
            binding["tracker_structure_sha256"],
        )

    def test_incidental_block_mentions_cannot_contract_full_tracker_intent(self) -> None:
        blocks = {0, 1, 2}
        for request in (
            "Do not stop at Block 1; implement this tracker.",
            "Implement this tracker; Block 1 was already reviewed.",
            "Do not implement only Block 1; implement this tracker.",
        ):
            intent, requested = supervision_log.classify_implementation_request(
                request, blocks
            )
            self.assertEqual(intent, "full-tracker")
            self.assertEqual(requested, [0, 1, 2])
        intent, requested = supervision_log.classify_implementation_request(
            "Implement Blocks 1 and 2.", blocks
        )
        self.assertEqual(intent, "explicit-blocks")
        self.assertEqual(requested, [1, 2])
        intent, requested = supervision_log.classify_implementation_request(
            "Implement this tracker, but only Block 1.", blocks
        )
        self.assertEqual(intent, "explicit-blocks")
        self.assertEqual(requested, [1])
        for request in (
            "Do not implement this tracker; implement only Block 1.",
            "Implement only Block 1; do not implement the full tracker.",
            "Implement Block 1 only.",
            "[$implement-tracker-blocks](/repo/implement-tracker-blocks/SKILL.md) Implement Block 1 only.",
            "$implement-tracker-blocks: implement only Block 1.",
            "Use implement-tracker-blocks for Block 1.",
        ):
            intent, requested = supervision_log.classify_implementation_request(
                request, blocks
            )
            self.assertEqual(intent, "explicit-blocks")
            self.assertEqual(requested, [1])
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "contradictory full and bounded",
        ):
            supervision_log.classify_implementation_request(
                "Implement this tracker; implement only Block 1.", blocks
            )
        with self.assertRaises(supervision_log.SupervisionLogError):
            supervision_log.classify_implementation_request(
                "Make the small Block 1 correction.", blocks
            )

    def test_exact_range_uses_completed_prerequisites_outside_requested_set(self) -> None:
        self.write_tracker(["completed", "not-started", "not-started"])
        result = self.bind("Block 1")
        self.assertEqual(result["binding"]["range_intent"], "explicit-blocks")
        gate = self.gate("block-boundary")
        self.assertEqual(gate["requested_blocks"], [1])
        self.assertEqual(gate["accepted_blocks"], [])
        self.assertEqual(gate["completed_prerequisite_blocks"], [0])
        self.assertEqual(gate["eligible_blocks"], [1])
        self.assertEqual(gate["next_action"], "continue-next-eligible-block")

    def test_successor_genesis_must_match_canonical_range_and_mission(self) -> None:
        self.write_tracker(["completed", "not-started"])
        binding = self.bind()["binding"]
        policy = supervision_log.read_json(
            self.root / self.target / "policy.json"
        )
        mission = supervision_log.bound_mission(policy)
        self.assertIsNotNone(mission)

        def transition_args(tracker_sha256: str) -> argparse.Namespace:
            return supervision_log.parser().parse_args(
                [
                    "--root",
                    str(self.root),
                    "successor-transition-record",
                    "--target-thread",
                    self.target,
                    "--transition-id",
                    "RANGE-TRANSITION-1234",
                    "--phase",
                    "required",
                    "--tracker-sha256",
                    tracker_sha256,
                    "--tracker-source-record",
                    "implementation-range-history:"
                    + str(binding["history_head_sha256"]),
                    "--requested-block-range",
                    "Blocks 0-1",
                    "--first-eligible-block",
                    "Block 1",
                    "--source-mission-root",
                    str(mission["mission_root"]),
                    "--governing-authority-source-class",
                    "direct-user",
                    "--governing-authority-source-record",
                    str(binding["authority"]["source_record"]),
                    "--governing-authority-source-sha256",
                    str(binding["authority"]["source_sha256"]),
                    "--topology-posture",
                    "same-task-new-run",
                    "--topology-basis",
                    "same-task-default",
                    "--evidence",
                    "canonical-range-handoff-test",
                ]
            )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical implementation range: tracker sha256",
        ):
            with redirect_stdout(io.StringIO()):
                transition_args("f" * 64).func(transition_args("f" * 64))
        unbound_source = transition_args(str(binding["tracker_sha256"]))
        unbound_source.tracker_source_record = "caller-selected-tracker-record"
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical implementation range: tracker source record",
        ):
            with redirect_stdout(io.StringIO()):
                unbound_source.func(unbound_source)
        valid = transition_args(str(binding["tracker_sha256"]))
        output = io.StringIO()
        with redirect_stdout(output):
            valid.func(valid)
        self.assertEqual(json.loads(output.getvalue())["record"]["phase"], "required")

        self.tracker.write_text(
            self.tracker.read_text(encoding="utf-8").replace(
                "Pending.", "Accepted status-only evidence.", 1
            ),
            encoding="utf-8",
        )
        amendment = self.call(
            "implementation-range-amend",
            "--target-thread",
            self.target,
            "--tracker",
            str(self.tracker),
        )["binding"]
        self.assertNotEqual(
            amendment["tracker_sha256"], binding["tracker_sha256"]
        )
        self.assertEqual(
            amendment["tracker_structure_sha256"],
            binding["tracker_structure_sha256"],
        )
        continued = transition_args(str(binding["tracker_sha256"]))
        continued.phase = "work-started"
        continued.started_block = "Block 1"
        continued.state_fingerprint = "state-work-started"
        continued.evidence = ["status-only-range-amendment-continuity"]
        continued_output = io.StringIO()
        with redirect_stdout(continued_output):
            continued.func(continued)
        self.assertEqual(
            json.loads(continued_output.getvalue())["record"]["phase"],
            "work-started",
        )

    def test_fabricated_direct_user_string_cannot_contract_but_accepted_receipt_can(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not in the canonical owner event ledger",
        ):
            self.call(
                "implementation-range-authority-receipt",
                "--target-thread",
                self.target,
                "--authority-event-record",
                "EVT-INVENTED-9999",
            )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "newer canonical direct-user"
        ):
            self.call(
                "implementation-range-amend",
                "--target-thread",
                self.target,
                "--tracker",
                str(self.tracker),
                "--request-text",
                "Block 0",
                "--authority-source-record",
                "invented-item-999",
                "--authority-source-sha256",
                "c" * 64,
            )
        authority_event = self.ingest_direct_authority_event(
            source_record=self.later_source,
            source_sha256=self.later_sha,
        )
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            authority_event,
        )
        amended = self.call(
            "implementation-range-amend",
            "--target-thread",
            self.target,
            "--tracker",
            str(self.tracker),
            "--request-text",
            self.later_request,
            "--authority-source-record",
            self.later_source,
            "--authority-source-sha256",
            self.later_sha,
        )
        self.assertTrue(amended["contraction"])
        result = self.gate("block-boundary")
        self.assertEqual(result["requested_blocks"], [0])
        self.assertTrue(result["final_response_permitted"])

    def test_initial_request_text_must_match_canonical_source_bytes(self) -> None:
        self.write_tracker(["completed", "not-started"])
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "request text does not match its canonical direct source",
        ):
            self.call(
                "implementation-range-bind",
                "--target-thread",
                self.target,
                "--range-id",
                "RANGE-FABRICATED-1234",
                "--tracker",
                str(self.tracker),
                "--request-text",
                "Block 0",
                "--authority-source-record",
                self.initial_source,
                "--authority-source-sha256",
                self.initial_sha,
            )

    def test_authority_receipt_rejects_owner_event_path_substitution(self) -> None:
        self.write_tracker(["completed", "not-started"])
        authority_event = self.ingest_direct_authority_event(
            source_record=self.later_source,
            source_sha256=self.later_sha,
        )
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            authority_event,
        )
        self.bind()
        directory = self.root / self.target
        ledger = directory / "events.jsonl"
        outside = self.root / "outside-events.jsonl"
        ledger.rename(outside)
        ledger.symlink_to(outside)
        with self.assertRaises(supervision_log.SupervisionLogError):
            self.gate()

    def test_policy_history_truncation_is_rejected(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        history_path = directory / "policy-history.jsonl"
        material = {
            "schema_version": 1,
            "record_id": "POLICY-1",
            "timestamp": supervision_log.utc_now(),
            "kind": "rewritten-policy-history",
            "policy": policy,
            "previous_record_sha256": None,
        }
        material["record_sha256"] = supervision_log.digest(material)
        history_path.write_bytes(supervision_log.canonical(material) + b"\n")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "truncated or re-rooted|owner-root history differs",
        ):
            self.gate()

    def test_event_suffix_deletion_is_rejected(self) -> None:
        self.write_tracker(["completed", "not-started"])
        authority_event = self.ingest_direct_authority_event(
            source_record=self.later_source,
            source_sha256=self.later_sha,
        )
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            authority_event,
        )
        self.bind()
        directory = self.root / self.target
        ledger = directory / "events.jsonl"
        supervision_log.append_raw(
            ledger,
            {
                "schema_version": 1,
                "record_id": (
                    f"EVT-{len(supervision_log.events(ledger)) + 1:06d}"
                ),
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "check",
                "status": "observed",
                "summary": "Later owner event that must remain append-only.",
            },
        )
        first = ledger.read_text(encoding="utf-8").splitlines()[0]
        ledger.write_text(first + "\n", encoding="utf-8")
        truncated_events = supervision_log.events(ledger)
        supervision_log.atomic_json(
            directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            supervision_log.event_ledger_anchor(truncated_events),
        )
        self.rewrite_owner_root_without_external_authority()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "external authority",
        ):
            self.gate()

    def test_fabricated_valid_policy_history_is_rejected_by_owner_root(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        directory = self.root / self.target
        policy_snapshots = [
            copy.deepcopy(item["policy"])
            for item in supervision_log.events(
                directory / "policy-history.jsonl"
            )
        ]
        records = []
        previous = None
        for index, embedded in enumerate(policy_snapshots, start=1):
            material = {
                "schema_version": 1,
                "record_id": f"POLICY-{index}",
                "timestamp": supervision_log.utc_now(),
                "kind": "fabricated-policy-history",
                "policy": embedded,
                "previous_record_sha256": previous,
            }
            material["record_sha256"] = supervision_log.digest(material)
            previous = material["record_sha256"]
            records.append(material)
        (directory / "policy-history.jsonl").write_bytes(
            b"".join(supervision_log.canonical(item) + b"\n" for item in records)
        )
        self.rewrite_owner_root_without_external_authority()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "external authority",
        ):
            self.gate()

    def test_policy_replacement_and_tracker_symlink_are_rejected(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        directory = self.root / self.target
        policy_path = directory / "policy.json"
        policy = supervision_log.read_json(policy_path)
        contract = policy["implementation_range"]
        contract["range_intent"] = "explicit-blocks"
        contract["explicit_blocks"] = [0]
        contract["history"][-1]["range_intent"] = "explicit-blocks"
        contract["history"][-1]["explicit_blocks"] = [0]
        material = {
            key: contract["history"][-1][key]
            for key in contract["history"][-1]
            if key != "entry_sha256"
        }
        contract["history"][-1]["entry_sha256"] = supervision_log.digest(material)
        contract["history_head_sha256"] = contract["history"][-1]["entry_sha256"]
        contract["genesis_sha256"] = supervision_log.digest(
            {
                "range_id": contract["range_id"],
                "authority": contract["history"][0]["authority"],
                "request_text_sha256": contract["history"][0]["request_text_sha256"],
                "initial_tracker_sha256": contract["history"][0]["tracker_sha256"],
                "initial_tracker_structure_sha256": contract["history"][0][
                    "tracker_structure_sha256"
                ],
                "initial_tracker_blocks": contract["history"][0]["tracker_blocks"],
                "initial_range_intent": "explicit-blocks",
                "initial_explicit_blocks": [0],
                "mission_identity": contract["history"][0][
                    "mission_identity"
                ],
            }
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.atomic_json(policy_path, policy)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "history is stale or replaced"
        ):
            self.gate()

        # Restore the policy from its canonical append-only history.
        canonical_policy = supervision_log.events(
            directory / "policy-history.jsonl"
        )[-1]["policy"]
        supervision_log.atomic_json(policy_path, canonical_policy)
        outside = self.root / "outside-tracker.md"
        outside.write_bytes(self.tracker.read_bytes())
        self.tracker.unlink()
        self.tracker.symlink_to(outside)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "non-symlink file"
        ):
            self.gate()

    def test_owner_root_enforcement_cannot_be_removed_from_bound_range(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        policy.pop("owner_root_history_required")
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.atomic_json(directory / "policy.json", policy)
        history = supervision_log.events(directory / "policy-history.jsonl")
        history[-1]["policy"] = policy
        previous = None
        rebuilt = []
        for item in history:
            material = {
                key: value
                for key, value in item.items()
                if key not in {"previous_record_sha256", "record_sha256"}
            }
            material["previous_record_sha256"] = previous
            material["record_sha256"] = supervision_log.digest(material)
            previous = material["record_sha256"]
            rebuilt.append(material)
        (directory / "policy-history.jsonl").write_bytes(
            b"".join(supervision_log.canonical(item) + b"\n" for item in rebuilt)
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "requires owner-root history|cannot be downgraded",
        ):
            self.gate()

    def test_authentic_owner_root_prefix_rollback_is_rejected_externally(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        directory = self.root / self.target
        event_path = directory / "events.jsonl"
        anchor_path = directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME
        roots_path = directory / supervision_log.OWNER_ROOT_HISTORY_NAME
        preserved = {
            event_path: event_path.read_bytes() if event_path.exists() else None,
            anchor_path: anchor_path.read_bytes(),
            roots_path: roots_path.read_bytes(),
        }
        current_events = supervision_log.events(event_path)
        supervision_log.append_raw(
            event_path,
            {
                "schema_version": 1,
                "record_id": f"EVT-{len(current_events) + 1:06d}",
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "check",
                "status": "later-authentic-event",
            },
        )
        for path, raw in preserved.items():
            if raw is None:
                path.unlink()
            else:
                path.write_bytes(raw)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "external owner-root head rejects rollback",
        ):
            self.gate()

    def test_fabricated_terminal_roots_have_no_input_surface_and_cannot_close(self) -> None:
        self.write_tracker(["completed"])
        self.bind()
        result = self.gate()
        self.assertFalse(result["final_response_permitted"])
        self.assertEqual(result["next_action"], "continue-governing-outcome")
        self.assertRegex(result["governing_outcome_currentness_sha256"], r"^[0-9a-f]{64}$")
        gate_help = supervision_log.parser().format_help()
        self.assertNotIn("terminal-evidence-json", gate_help)

    def test_nonterminal_range_rejects_completed_lifecycle_before_other_claims(self) -> None:
        self.write_tracker(["completed", "not-started"])
        self.bind()
        args = supervision_log.parser().parse_args(
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
                "range-state-1234",
                "--summary",
                "Attempted early completion.",
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "critical implementation-range gate: continue-next-eligible-block",
        ):
            with redirect_stdout(io.StringIO()):
                args.func(args)

    def test_critical_range_contract_is_encoded_across_all_three_owners(self) -> None:
        repository = HELPER_PATH.parent.parent.parent
        implementation = repository.joinpath(
            "implement-tracker-blocks", "SKILL.md"
        ).read_text(encoding="utf-8")
        authoring = repository.joinpath(
            "author-implementation-trackers", "SKILL.md"
        ).read_text(encoding="utf-8")
        supervision = repository.joinpath(
            "supervise-tracker-runs", "SKILL.md"
        ).read_text(encoding="utf-8")
        policy = repository.joinpath(
            "supervise-tracker-runs", "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        changelog = repository.joinpath("CHANGELOG.md").read_text(encoding="utf-8")
        for text in (implementation, supervision, policy):
            self.assertIn("implementation-range-gate", text)
            self.assertIn("FM-UNAUTHORIZED-EARLY-RETURN", text)
            self.assertIn("critical", text.lower())
        self.assertIn("newer exact direct-user", authoring)
        self.assertIn("unauthorized requested-range contraction", changelog)
        self.assertIn("019fb18f-3d03-7ca0-9fe9-68353f0405ce", changelog)


class SoftwareFactoryReleaseOrchestrationTests(unittest.TestCase):
    target = "release-orchestration-target-1234"
    reviewer = "release-orchestration-reviewer-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "supervision"
        self.repo = Path(self.temporary.name) / "repository"
        self.repo.mkdir()
        self.repo = self.repo.resolve(strict=True)
        self.repo.joinpath("scripts").mkdir()
        self.repo.joinpath("scripts", "skill_release.py").write_text(
            "#!/usr/bin/env python3\n",
            encoding="utf-8",
        )
        subprocess.run(["/usr/bin/git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "config", "user.name", "Test"],
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(self.repo),
                "config",
                "user.email",
                "test@example.invalid",
            ],
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "add", "."], check=True
        )
        subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "commit", "-qm", "source"],
            check=True,
        )
        self.source = subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.tree = subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Release orchestration target",
                "--watcher-thread",
                "release-orchestration-watcher-1234",
                "--reviewer-thread",
                self.reviewer,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "release-orchestration-source-1234",
                "--mission-source-sha256",
                "1" * 64,
            ]
        )
        with redirect_stdout(io.StringIO()):
            args.func(args)
        self.owner_actions: list[str] = []
        self.promotion, self.status = self.owner_results()
        self.prior_status = copy.deepcopy(self.status)
        prior_release = self.promotion["activation"]["previous_release_id"]
        self.prior_status["active_release_id"] = prior_release
        self.prior_status["source_commit"] = "a" * 40
        self.prior_status["activation_history_records"] = 1
        prior_installed = {
            **self.prior_status["current_verification"],
            "release_id": prior_release,
        }
        prior_material = {
            key: value
            for key, value in prior_installed.items()
            if key != "verification_root_sha256"
        }
        prior_installed["verification_root_sha256"] = (
            supervision_log.digest(prior_material)
        )
        self.prior_status["current_verification"] = prior_installed

    def call(self, *arguments: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), *arguments]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def owner_results(self) -> tuple[dict[str, object], dict[str, object]]:
        roots = {
            name: hashlib.sha256(name.encode("utf-8")).hexdigest()
            for name in supervision_log.SOFTWARE_FACTORY_RELEASE_SKILLS
        }
        checks = []
        for item in (
            "release-owner",
            "tracker-authoring",
            "tracker-execution",
            "tracker-supervision",
        ):
            check_material = {
                "id": item,
                "status": "passed",
                "test_count": 1,
                "failure_count": 0,
                "baseline_failure_count": 0,
            }
            checks.append(
                {
                    **check_material,
                    "result_sha256": supervision_log.digest(check_material),
                }
            )
        assurance_material: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-skill-release-automated-assurance",
            "record_id": f"AUTOMATED-{self.source[:12]}-{'3' * 12}",
            "source_commit": self.source,
            "candidate_root_sha256": "4" * 64,
            "checks": checks,
            "outcome": "passed",
        }
        assurance = {
            **assurance_material,
            "assurance_root_sha256": supervision_log.digest(assurance_material),
        }
        release_id = (
            f"{self.source[:12]}-"
            f"{supervision_log.digest({'candidate_root_sha256': assurance['candidate_root_sha256'], 'assurance_root_sha256': assurance['assurance_root_sha256']})[:12]}"
        )
        installed_material: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-post-swap-resolution",
            "release_id": release_id,
            "installed_roots": roots,
        }
        installed = {
            **installed_material,
            "verification_root_sha256": supervision_log.digest(installed_material),
        }
        promotion = {
            "promotion": "completed",
            "stage": "created",
            "release_id": release_id,
            "source_commit": self.source,
            "automated_assurance": assurance,
            "activation": {
                "action": "activate",
                "active_release_id": release_id,
                "previous_release_id": f"{'5' * 12}-{'6' * 12}",
                "installed": installed,
                "activation_record": {"record_id": "release-owner-record-1234"},
            },
        }
        status = {
            "active_release_id": release_id,
            "source_commit": self.source,
            "skills": {
                name: {"content_root_sha256": root, "file_count": 1}
                for name, root in roots.items()
            },
            "installed_links": {
                name: {"stable": True} for name in roots
            },
            "installed_complete": True,
            "activation_history_records": 2,
            "current_verification": installed,
        }
        return promotion, status

    def acceptance(self, *, reviewer: str | None = None, tree: str | None = None) -> str:
        selected_reviewer = reviewer or supervision_log.ADAPTIVE_REVIEWER_ID
        directory = self.root / self.target
        policy = json.loads(
            directory.joinpath("policy.json").read_text(encoding="utf-8")
        )
        existing = supervision_log.events(directory / "events.jsonl")
        review_material: dict[str, object] = {
            "schema_version": 1,
            "kind": supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
            "record_id": f"signed-release-review-{len(existing) + 1:04d}",
            "reviewer_id": selected_reviewer,
            "disposition": "accepted",
            "target_thread_id": self.target,
            "source_commit": self.source,
            "source_tree": tree or self.tree,
            "reviewed_at": supervision_log.utc_now(),
            "evidence": ["review-findings:none"],
            "authority_key_sha256": supervision_log.ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256,
        }
        review: dict[str, object] = {
            **review_material,
            "acceptance_root_sha256": supervision_log.digest(review_material),
        }
        review["signature_base64"] = base64.b64encode(b"x" * 64).decode("ascii")
        record = {
            "schema_version": 1,
            "record_id": f"EVT-{len(existing) + 1:06d}",
            "timestamp": supervision_log.utc_now(),
            "target_thread_id": self.target,
            "kind": supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
            "category": supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_CATEGORY,
            "status": "accepted",
            "policy_sha256": policy["policy_sha256"],
            "source_commit": self.source,
            "source_tree": tree or self.tree,
            "acceptance_review": review,
            "acceptance_root_sha256": review["acceptance_root_sha256"],
            "reviewer_authority_id": selected_reviewer,
        }
        supervision_log.append_raw(directory / "events.jsonl", record)
        return str(record["record_id"])

    def promote(self, acceptance: str) -> dict[str, object]:
        with mock.patch.object(
            supervision_log, "verify_adaptive_review_signature"
        ):
            return self.call(
                "software-factory-release-promote",
                "--target-thread",
                self.target,
                "--repo",
                str(self.repo),
                "--source-commit",
                self.source,
                "--acceptance-record",
                acceptance,
            )

    def fake_owner(
        self, _repository: Path, *, source_commit: str, action: str
    ) -> dict[str, object]:
        self.assertEqual(source_commit, self.source)
        promoted = "promote" in self.owner_actions
        self.owner_actions.append(action)
        if action == "promote":
            return copy.deepcopy(self.promotion)
        return copy.deepcopy(self.status if promoted else self.prior_status)

    def test_exact_acceptance_invokes_flagless_owner_and_deduplicates(self) -> None:
        accepted = self.acceptance()
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            first = self.promote(accepted)
            second = self.promote(accepted)

        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(
            self.owner_actions, ["status", "promote", "status", "status"]
        )
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                ]
            ),
            1,
        )

    def test_later_review_waits_until_promotion_result_is_retained(self) -> None:
        accepted = self.acceptance()
        writer_started = threading.Event()
        writer_finished = threading.Event()
        writer: threading.Thread | None = None

        def append_later_review() -> None:
            writer_started.set()
            directory = self.root / self.target
            with supervision_log.append_lock(directory):
                existing = supervision_log.events(directory / "events.jsonl")
                source = next(
                    item
                    for item in existing
                    if item.get("record_id") == accepted
                )
                record = {
                    key: value
                    for key, value in source.items()
                    if key not in {"previous_record_sha256", "record_sha256"}
                }
                record.update(
                    {
                        "record_id": f"EVT-{len(existing) + 1:06d}",
                        "timestamp": supervision_log.utc_now(),
                    }
                )
                review = copy.deepcopy(record["acceptance_review"])
                review["record_id"] = "later-signed-release-review-1234"
                root_material = {
                    key: value
                    for key, value in review.items()
                    if key not in {"acceptance_root_sha256", "signature_base64"}
                }
                review["acceptance_root_sha256"] = supervision_log.digest(
                    root_material
                )
                review["signature_base64"] = base64.b64encode(
                    b"y" * 64
                ).decode("ascii")
                record["acceptance_review"] = review
                record["acceptance_root_sha256"] = review[
                    "acceptance_root_sha256"
                ]
                supervision_log.append_raw_locked(
                    directory / "events.jsonl", record
                )
            writer_finished.set()

        def owner(
            repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            nonlocal writer
            if action == "promote":
                writer = threading.Thread(target=append_later_review)
                writer.start()
                self.assertTrue(writer_started.wait(timeout=2))
                self.assertFalse(writer_finished.is_set())
            return self.fake_owner(
                repository, source_commit=source_commit, action=action
            )

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            result = self.promote(accepted)
        self.assertFalse(result["duplicate"])
        self.assertIsNotNone(writer)
        writer.join(timeout=2)
        self.assertTrue(writer_finished.is_set())
        release_records = [
            item
            for item in supervision_log.events(
                self.root / self.target / "events.jsonl"
            )
            if item.get("kind")
            in {
                supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
                supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND,
                supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND,
            }
        ]
        self.assertEqual(
            [item["kind"] for item in release_records],
            [
                supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
                supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND,
                supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND,
                supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
            ],
        )

    def test_interruption_after_owner_rehydrates_one_requirement(self) -> None:
        accepted = self.acceptance()
        original = supervision_log.validate_software_factory_owner_result
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ), mock.patch.object(
            supervision_log,
            "validate_software_factory_owner_result",
            side_effect=supervision_log.SupervisionLogError(
                "injected result interruption"
            ),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "result interruption"
            ):
                self.promote(accepted)
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ), mock.patch.object(
            supervision_log,
            "validate_software_factory_owner_result",
            side_effect=original,
        ):
            recovered = self.promote(accepted)
        self.assertFalse(recovered["duplicate"])
        self.assertEqual(
            self.owner_actions,
            ["status", "promote", "status", "status"],
        )
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                ]
            ),
            1,
        )

    def test_new_acceptance_supersedes_no_effect_requirement(self) -> None:
        acceptance_a = self.acceptance()
        promotion_attempts = 0
        effect_performed = False

        def owner(
            _repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            nonlocal effect_performed, promotion_attempts
            self.assertEqual(source_commit, self.source)
            self.owner_actions.append(action)
            if action == "status":
                return copy.deepcopy(
                    self.status if effect_performed else self.prior_status
                )
            promotion_attempts += 1
            if promotion_attempts == 1:
                raise supervision_log.SupervisionLogError(
                    "injected interruption before owner effect"
                )
            effect_performed = True
            return copy.deepcopy(self.promotion)

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "before owner effect",
            ):
                self.promote(acceptance_a)
            acceptance_b = self.acceptance()
            recovered = self.promote(acceptance_b)
            actions_after_recovery = list(self.owner_actions)
            duplicate = self.promote(acceptance_a)

        self.assertFalse(recovered["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(
            actions_after_recovery,
            ["status", "promote", "status", "promote", "status"],
        )
        self.assertEqual(
            self.owner_actions,
            ["status", "promote", "status", "promote", "status", "status"],
        )
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        requirements = [
            item
            for item in records
            if item.get("kind")
            == supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND
        ]
        promotions = [
            item
            for item in records
            if item.get("kind")
            == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
        ]
        self.assertEqual(len(requirements), 2)
        self.assertIsNone(requirements[0]["supersedes_required_record_id"])
        self.assertEqual(
            requirements[1]["supersedes_required_record_id"],
            requirements[0]["record_id"],
        )
        self.assertEqual(
            requirements[1]["acceptance_record_id"], acceptance_b
        )
        self.assertEqual(len(promotions), 1)
        self.assertEqual(
            promotions[0]["required_record_id"],
            requirements[1]["record_id"],
        )
        self.assertEqual(promotions[0]["acceptance_record_id"], acceptance_b)

    def test_requirement_supersession_rejects_changed_prior_state(self) -> None:
        acceptance_a = self.acceptance()

        def interrupting_owner(
            _repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            self.assertEqual(source_commit, self.source)
            self.owner_actions.append(action)
            if action == "promote":
                raise supervision_log.SupervisionLogError(
                    "injected interruption before owner effect"
                )
            return copy.deepcopy(self.prior_status)

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=interrupting_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "before owner effect",
            ):
                self.promote(acceptance_a)

        acceptance_b = self.acceptance()
        changed_prior = copy.deepcopy(self.prior_status)
        changed_prior["activation_history_records"] = 2
        actions_before = list(self.owner_actions)
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            return_value=changed_prior,
        ) as owner:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "prior state differs",
            ):
                self.promote(acceptance_b)
        self.assertEqual(owner.call_count, 1)
        self.assertEqual(self.owner_actions, actions_before)
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND
                ]
            ),
            1,
        )
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in records
            )
        )

    def test_changed_prior_during_owner_effect_is_retained_once(self) -> None:
        accepted = self.acceptance()
        changed_promotion = copy.deepcopy(self.promotion)
        changed_promotion["activation"]["previous_release_id"] = (
            f"{'7' * 12}-{'8' * 12}"
        )
        changed_status = copy.deepcopy(self.status)
        changed_status["activation_history_records"] = 3

        def owner(
            _repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            self.assertEqual(source_commit, self.source)
            self.owner_actions.append(action)
            if action == "promote":
                return copy.deepcopy(changed_promotion)
            return copy.deepcopy(
                changed_status
                if "promote" in self.owner_actions
                else self.prior_status
            )

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "effect was retained"
            ):
                self.promote(accepted)
            actions_after_rejection = list(self.owner_actions)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "previously retained with changed currentness",
            ):
                self.promote(accepted)

        self.assertEqual(
            self.owner_actions,
            ["status", "promote", "status"],
        )
        self.assertEqual(self.owner_actions, actions_after_rejection)
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REJECTED_KIND
                ]
            ),
            1,
        )
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in records
            )
        )

    def test_interrupted_effect_with_later_dirty_source_is_retained_once(self) -> None:
        accepted = self.acceptance()
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ), mock.patch.object(
            supervision_log,
            "validate_software_factory_owner_result",
            side_effect=supervision_log.SupervisionLogError(
                "injected result interruption"
            ),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "result interruption"
            ):
                self.promote(accepted)

        self.repo.joinpath("dirty-after-effect.txt").write_text(
            "dirty\n", encoding="utf-8"
        )
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "effect was retained"
            ):
                self.promote(accepted)
            owner_actions_after_recovery = list(self.owner_actions)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "previously retained with changed currentness",
            ):
                self.promote(accepted)

        self.assertEqual(
            self.owner_actions,
            ["status", "promote", "status", "status"],
        )
        self.assertEqual(self.owner_actions, owner_actions_after_recovery)
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REQUIRED_KIND
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in records
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REJECTED_KIND
                ]
            ),
            1,
        )
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in records
            )
        )

    def test_missing_or_unbound_acceptance_rejects_before_owner(self) -> None:
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "missing or ambiguous"
            ):
                self.promote("EVT-009999")
            unbound = self.acceptance(reviewer="different-reviewer-1234")
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "not exact and accepted"
            ):
                self.promote(unbound)
        self.assertEqual(self.owner_actions, [])

    def test_generic_checkpoint_review_cannot_authorize_promotion(self) -> None:
        generic = self.call(
            "record",
            "--target-thread",
            self.target,
            "--kind",
            "checkpoint-review",
            "--status",
            "accepted",
            "--category",
            supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_CATEGORY,
            "--model",
            "gpt-5.6-sol",
            "--reasoning",
            "max",
            "--summary",
            "Caller assertion must not become release acceptance.",
            "--evidence",
            f"source-commit:{self.source}",
            "--evidence",
            f"source-tree:{self.tree}",
            "--evidence",
            f"reviewer-thread:{self.reviewer}",
            "--evidence",
            "review-findings:none",
        )
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "current exact review|not exact and accepted",
            ):
                self.promote(str(generic["record"]["record_id"]))
        self.assertEqual(self.owner_actions, [])

    def test_unverified_signed_acceptance_is_rejected(self) -> None:
        accepted = self.acceptance()
        record = next(
            item
            for item in supervision_log.events(
                self.root / self.target / "events.jsonl"
            )
            if item.get("record_id") == accepted
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "signature verification failed",
        ):
            supervision_log.validate_software_factory_release_signed_acceptance(
                record["acceptance_review"],
                target_thread_id=self.target,
                source_commit=self.source,
                source_tree=self.tree,
            )

    def test_signed_acceptance_command_appends_once(self) -> None:
        review_material: dict[str, object] = {
            "schema_version": 1,
            "kind": supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
            "record_id": "signed-release-review-command-1234",
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "disposition": "accepted",
            "target_thread_id": self.target,
            "source_commit": self.source,
            "source_tree": self.tree,
            "reviewed_at": supervision_log.utc_now(),
            "evidence": ["review-findings:none"],
            "authority_key_sha256": supervision_log.ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256,
        }
        review: dict[str, object] = {
            **review_material,
            "acceptance_root_sha256": supervision_log.digest(review_material),
            "signature_base64": base64.b64encode(b"z" * 64).decode("ascii"),
        }
        evidence = Path(self.temporary.name) / "signed-acceptance.json"
        evidence.write_bytes(supervision_log.canonical(review) + b"\n")
        arguments = (
            "software-factory-release-accept",
            "--target-thread",
            self.target,
            "--repo",
            str(self.repo),
            "--source-commit",
            self.source,
            "--review-evidence",
            str(evidence),
        )
        with mock.patch.object(
            supervision_log,
            "verify_adaptive_review_signature",
        ):
            first = self.call(*arguments)
            second = self.call(*arguments)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(
            first["record"]["kind"],
            supervision_log.SOFTWARE_FACTORY_RELEASE_ACCEPTANCE_KIND,
        )

    def test_later_source_review_retires_prior_acceptance(self) -> None:
        accepted = self.acceptance()
        self.acceptance()
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "current exact review"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, [])

    def test_policy_advance_retires_prior_acceptance(self) -> None:
        accepted = self.acceptance()
        self.call(
            "bind",
            "--target-thread",
            self.target,
            "--base-reviewer-thread",
            "release-base-reviewer-1234",
        )
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "stale for the current policy",
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, [])

    def test_invalid_automated_assurance_check_rejects(self) -> None:
        accepted = self.acceptance()
        invalid = copy.deepcopy(self.promotion)
        invalid["automated_assurance"]["checks"][0]["failure_count"] = 1
        assurance_material = {
            key: value
            for key, value in invalid["automated_assurance"].items()
            if key != "assurance_root_sha256"
        }
        invalid["automated_assurance"]["assurance_root_sha256"] = (
            supervision_log.digest(assurance_material)
        )

        def owner(
            repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            result = self.fake_owner(
                repository, source_commit=source_commit, action=action
            )
            return copy.deepcopy(invalid if action == "promote" else result)

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "assurance check is invalid"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, ["status", "promote", "status"])

    def test_changed_source_or_tree_rejects_before_owner(self) -> None:
        wrong_tree = self.acceptance(tree="f" * 40)
        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "not exact and accepted"
            ):
                self.promote(wrong_tree)
        self.repo.joinpath("changed.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "exact and clean"
        ):
            self.promote(wrong_tree)
        self.assertEqual(self.owner_actions, [])

    def commit_repository_change(self, name: str) -> None:
        self.repo.joinpath(name).write_text("changed\n", encoding="utf-8")
        subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "add", name],
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "-C", str(self.repo), "commit", "-qm", name],
            check=True,
        )

    def test_clean_head_advance_before_owner_rejects(self) -> None:
        accepted = self.acceptance()
        exact_checkout = supervision_log.software_factory_release_exact_checkout

        @contextmanager
        def advancing_checkout(repository: Path, source_commit: str):
            with exact_checkout(repository, source_commit) as checkout:
                self.commit_repository_change("advanced-before-owner.txt")
                yield checkout

        with mock.patch.object(
            supervision_log,
            "software_factory_release_exact_checkout",
            side_effect=advancing_checkout,
        ), mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "stale for the current HEAD"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, ["status"])

    def test_dirty_source_before_owner_rejects(self) -> None:
        accepted = self.acceptance()
        exact_checkout = supervision_log.software_factory_release_exact_checkout

        @contextmanager
        def dirty_checkout(repository: Path, source_commit: str):
            with exact_checkout(repository, source_commit) as checkout:
                self.repo.joinpath("dirty-before-owner.txt").write_text(
                    "dirty\n", encoding="utf-8"
                )
                yield checkout

        with mock.patch.object(
            supervision_log,
            "software_factory_release_exact_checkout",
            side_effect=dirty_checkout,
        ), mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=self.fake_owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "exact and clean"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, ["status"])

    def test_clean_head_advance_before_append_rejects_record(self) -> None:
        accepted = self.acceptance()

        def owner(
            repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            result = self.fake_owner(
                repository, source_commit=source_commit, action=action
            )
            if action == "status" and "promote" in self.owner_actions:
                self.commit_repository_change("advanced-before-append.txt")
            return result

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "effect was retained"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, ["status", "promote", "status"])
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in supervision_log.events(
                    self.root / self.target / "events.jsonl"
                )
            )
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in supervision_log.events(
                        self.root / self.target / "events.jsonl"
                    )
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REJECTED_KIND
                ]
            ),
            1,
        )

    def test_dirty_source_before_append_rejects_record(self) -> None:
        accepted = self.acceptance()

        def owner(
            repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            result = self.fake_owner(
                repository, source_commit=source_commit, action=action
            )
            if action == "status" and "promote" in self.owner_actions:
                self.repo.joinpath("dirty-before-append.txt").write_text(
                    "dirty\n", encoding="utf-8"
                )
            return result

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "effect was retained"
            ):
                self.promote(accepted)
        self.assertEqual(self.owner_actions, ["status", "promote", "status"])
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in supervision_log.events(
                    self.root / self.target / "events.jsonl"
                )
            )
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in supervision_log.events(
                        self.root / self.target / "events.jsonl"
                    )
                    if item.get("kind")
                    == supervision_log.SOFTWARE_FACTORY_RELEASE_REJECTED_KIND
                ]
            ),
            1,
        )

    def test_owner_invocation_is_exactly_flagless(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"{}", stderr=b""
        )
        with mock.patch.dict(
            os.environ,
            {
                "HOME": "/tmp/synthetic-release-home",
                "PYTHONPATH": "/tmp/synthetic-python-path",
                "GIT_CONFIG_GLOBAL": "/tmp/synthetic-git-config",
            },
            clear=False,
        ), mock.patch.object(
            supervision_log.subprocess, "run", return_value=completed
        ) as run:
            supervision_log.run_software_factory_release_owner(
                self.repo, source_commit=self.source, action="promote"
            )
        self.assertEqual(
            run.call_args.args[0],
            [
                "/usr/bin/python3",
                str(self.repo / "scripts" / "skill_release.py"),
                "promote",
                "--repo",
                str(self.repo),
                "--source-commit",
                self.source,
            ],
        )
        owner_environment = run.call_args.kwargs["env"]
        self.assertEqual(
            owner_environment,
            {
                "HOME": str(
                    Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
                ),
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
                "LANG": "C",
                "PYTHONNOUSERSITE": "1",
            },
        )

    def test_divergent_owner_status_never_becomes_canonical(self) -> None:
        accepted = self.acceptance()
        divergent = copy.deepcopy(self.status)
        divergent["source_commit"] = "f" * 40

        def owner(
            _repository: Path, *, source_commit: str, action: str
        ) -> dict[str, object]:
            promoted = "promote" in self.owner_actions
            self.owner_actions.append(action)
            if action == "promote":
                return copy.deepcopy(self.promotion)
            return copy.deepcopy(divergent if promoted else self.prior_status)

        with mock.patch.object(
            supervision_log,
            "run_software_factory_release_owner",
            side_effect=owner,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "live status differs"
            ):
                self.promote(accepted)
        records = supervision_log.events(
            self.root / self.target / "events.jsonl"
        )
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.SOFTWARE_FACTORY_RELEASE_PROMOTION_KIND
                for item in records
            )
        )
        self.assertEqual(self.owner_actions, ["status", "promote", "status"])

    def test_pointer_and_caller_active_identity_inputs_are_absent(self) -> None:
        for option, value in (
            ("--release-id", "caller-release-1234"),
            ("--manual-pin-release", "0123456789ab-0123456789ab"),
        ):
            with self.subTest(option=option), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    supervision_log.parser().parse_args(
                        [
                            "--root",
                            str(self.root),
                            "software-factory-release-promote",
                            "--target-thread",
                            self.target,
                            "--repo",
                            str(self.repo),
                            "--source-commit",
                            self.source,
                            "--acceptance-record",
                            "EVT-000001",
                            option,
                            value,
                        ]
                    )


class LegacyDirectAuthorityIngestTests(unittest.TestCase):
    target = "019fdfe4-dabe-7130-ac93-f8fa8e3bce12"
    source_turn = "019fe245-6c79-7f82-94d5-9ec6a4b684cc"
    source_item = "item-340"
    transition_record = "EVT-000069"
    transition_id = "TRANSITION-94c8118-BLOCKS-0-13"
    reviewer = "legacy-max-reviewer-1234"
    watcher = "legacy-watcher-1234"
    fix_executor = "legacy-fix-executor-1234"
    source_text = (
        "[$author-implementation-trackers]"
        "(/Users/ethanstillman/code/software_factory/"
        "author-implementation-trackers/SKILL.md) for this all / make sure "
        "the tracker is up to date with what we've discussed. then "
        "[$implement-tracker-blocks]"
        "(/Users/ethanstillman/code/software_factory/"
        "implement-tracker-blocks/SKILL.md) for that tracker\n"
    )
    source_sha256 = (
        "897a606e4602b95c875bb1563b331026bc09eead35beb7eb78ebcf8fa65b6b74"
    )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tracker = self.root / "tracker.md"
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Legacy authority target",
                "--watcher-thread",
                self.watcher,
                "--reviewer-thread",
                self.reviewer,
                "--fix-executor-thread",
                self.fix_executor,
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "initial-item-1234",
                "--mission-source-sha256",
                "a" * 64,
            ]
        )
        with redirect_stdout(io.StringIO()):
            args.func(args)
        self.assertEqual(len(self.source_text.encode("utf-8")), 324)
        self.assertEqual(
            hashlib.sha256(self.source_text.encode("utf-8")).hexdigest(),
            self.source_sha256,
        )
        self.write_tracker()
        self.append_legacy_transition()

    @property
    def directory(self) -> Path:
        return self.root / self.target

    def write_tracker(self) -> None:
        rows = []
        headings = []
        for number in range(18):
            status = "completed" if number < 9 else "not-started"
            dependency = "—" if number == 0 else str(number - 1)
            rows.append(
                f"| {number} | Scope {number} | {dependency} | `{status}` |"
            )
            headings.append(
                f"## Block {number} — Scope {number}\n\n"
                f"Status: `{status}`\n\n"
                "### Completion evidence\n\nPending.\n\n"
                "### Stop\n\nStop at this Block boundary.\n"
            )
        self.tracker.write_text(
            "| Block | Scope | Depends on | Status |\n"
            "|---:|---|---:|---|\n"
            + "\n".join(rows)
            + "\n\n"
            + "\n".join(headings),
            encoding="utf-8",
        )

    def append_event(self, record: dict[str, object]) -> dict[str, object]:
        current = supervision_log.events(self.directory / "events.jsonl")
        value = {
            "schema_version": 1,
            "record_id": f"EVT-{len(current) + 1:06d}",
            "timestamp": supervision_log.utc_now(),
            "target_thread_id": self.target,
            **record,
        }
        supervision_log.append_raw(self.directory / "events.jsonl", value)
        return supervision_log.events(self.directory / "events.jsonl")[-1]

    def append_legacy_transition(
        self,
        *,
        transition_id: str | None = None,
        modern: bool = False,
    ) -> dict[str, object]:
        policy = supervision_log.read_json(self.directory / "policy.json")
        current = supervision_log.events(self.directory / "events.jsonl")
        value: dict[str, object] = {
            "schema_version": 1,
            "record_id": (
                self.transition_record
                if not current
                else f"EVT-{len(current) + 1:06d}"
            ),
            "timestamp": supervision_log.utc_now(),
            "target_thread_id": self.target,
            "kind": "successor-transition",
            "transition_id": transition_id or self.transition_id,
            "phase": "required",
            "tracker_sha256": "b" * 64,
            "tracker_source_record": (
                "commit:94c8118adca77b574b1e6ef5a1f2a5aad0aa9d91:"
                "blob:9e6b6d1d03369c84ff9ca48c2df35dcac79e2f64"
            ),
            "requested_block_range": "Blocks-0-13",
            "first_eligible_block": "Block-0",
            "source_mission_root": supervision_log.bound_mission(policy)[
                "mission_root"
            ],
            "governing_authority_source_class": "direct-user",
            "governing_authority_source_record": self.source_item,
            "policy_sha256": policy["policy_sha256"],
            "evidence": ["legacy-direct-authority-migration"],
        }
        if modern:
            value.update(
                {
                    "governing_authority_source_sha256": self.source_sha256,
                    "topology_posture": "same-task-new-run",
                    "topology_basis": "same-task-default",
                }
            )
        supervision_log.append_raw(self.directory / "events.jsonl", value)
        return supervision_log.events(self.directory / "events.jsonl")[-1]

    def provenance(
        self,
        *,
        source_text: str | None = None,
        transition_record: str | None = None,
        transition_id: str | None = None,
        verifier: str | None = None,
    ) -> dict[str, object]:
        policy = supervision_log.read_json(self.directory / "policy.json")
        text = self.source_text if source_text is None else source_text
        return {
            "schema_version": 1,
            "kind": supervision_log.LEGACY_DIRECT_AUTHORITY_PROVENANCE_KIND,
            "target_thread_id": self.target,
            "source_task_id": self.target,
            "source_turn_id": self.source_turn,
            "source_item_id": self.source_item,
            "source_text": text,
            "source_byte_count": len(text.encode("utf-8")),
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "policy_version": policy["policy_version"],
            "policy_sha256": policy["policy_sha256"],
            "verifier_id": verifier or self.reviewer,
            "authorization_record_id": "pending-review-1234",
            "legacy_transition_record_id": (
                transition_record or self.transition_record
            ),
            "legacy_transition_id": transition_id or self.transition_id,
        }

    def append_review(
        self,
        provenance: dict[str, object],
        *,
        kind: str = "meta-review",
        status: str = "accepted",
    ) -> dict[str, object]:
        event = self.append_event(
            {
                "kind": kind,
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "status": status,
                "category": (
                    supervision_log.LEGACY_DIRECT_AUTHORITY_REVIEW_CATEGORY
                ),
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": provenance["policy_sha256"],
                "evidence": (
                    supervision_log.legacy_direct_authority_review_evidence(
                        provenance
                    )
                ),
            }
        )
        provenance["authorization_record_id"] = event["record_id"]
        return event

    def encode(self, provenance: dict[str, object]) -> str:
        return base64.b64encode(supervision_log.canonical(provenance)).decode(
            "ascii"
        )

    def call(self, *arguments: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), *arguments]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def ingest(self, provenance: dict[str, object]) -> dict[str, object]:
        return self.call(
            "legacy-direct-authority-ingest",
            "--target-thread",
            self.target,
            "--provenance-base64",
            self.encode(provenance),
        )

    def bind_legacy_full_range(self) -> None:
        provenance = self.provenance()
        self.append_review(provenance)
        source = self.ingest(provenance)
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread", self.target,
            "--authority-event-record", str(source["record_id"]),
        )
        self.call(
            "implementation-range-bind",
            "--target-thread", self.target,
            "--range-id", "RANGE-ITEM-340",
            "--tracker", str(self.tracker),
            "--request-text", self.source_text,
            "--authority-source-record", self.source_item,
            "--authority-source-sha256", self.source_sha256,
        )

    def transition_args(
        self,
        phase: str,
        *,
        transition: dict[str, object] | None = None,
        extra: tuple[str, ...] = (),
    ) -> argparse.Namespace:
        prior = transition or supervision_log.successor_transition_events(
            supervision_log.events(self.directory / "events.jsonl"),
            self.transition_id,
        )[-1]
        disposition = []
        if phase in supervision_log.SUCCESSOR_TRANSITION_TERMINAL_PHASES:
            disposition = [
                "--prior-record", str(prior["record_id"]),
                "--disposition-reason", "Retire the stale pre-contract transition.",
                "--correction-authority-source-class", "direct-user",
                "--correction-authority-source-record", self.source_item,
                "--correction-authority-source-sha256", self.source_sha256,
                "--governing-outcome-effect",
                (
                    "continue-replacement-transition"
                    if phase == "superseded"
                    else "continue-same-task"
                ),
            ]
        return supervision_log.parser().parse_args(
            [
                "--root", str(self.root),
                "successor-transition-record",
                "--target-thread", self.target,
                "--transition-id", str(prior["transition_id"]),
                "--phase", phase,
                "--tracker-sha256", str(prior["tracker_sha256"]),
                "--tracker-source-record", str(prior["tracker_source_record"]),
                "--requested-block-range", str(prior["requested_block_range"]),
                "--first-eligible-block", str(prior["first_eligible_block"]),
                "--source-mission-root", str(prior["source_mission_root"]),
                "--governing-authority-source-class", "direct-user",
                "--governing-authority-source-record", self.source_item,
                "--governing-authority-source-sha256", self.source_sha256,
                *disposition,
                "--state-fingerprint", "legacy-terminal-state-1234",
                "--evidence", "legacy-terminal-compatibility-proof",
                *extra,
            ]
        )

    def state(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file() and path.name != ".append.lock"
        }

    def assert_rejected_without_mutation(
        self,
        provenance: dict[str, object],
        message: str,
    ) -> None:
        before = self.state()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, message
        ):
            self.ingest(provenance)
        self.assertEqual(self.state(), before)

    def test_exact_item_340_ingests_idempotently_and_binds_full_blocks_0_17(self) -> None:
        provenance = self.provenance()
        self.append_review(provenance)

        result = self.ingest(provenance)
        duplicate = self.ingest(provenance)

        self.assertFalse(result["duplicate"])
        self.assertEqual(result["source_record"], self.source_item)
        self.assertEqual(result["source_sha256"], self.source_sha256)
        self.assertEqual(
            result["classification"],
            supervision_log.LEGACY_DIRECT_AUTHORITY_CLASSIFICATION,
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["record_id"], result["record_id"])
        receipt = self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            str(result["record_id"]),
        )
        self.assertFalse(receipt["duplicate"])
        self.assertTrue(self.ingest(provenance)["duplicate"])
        binding = self.call(
            "implementation-range-bind",
            "--target-thread",
            self.target,
            "--range-id",
            "RANGE-ITEM-340",
            "--tracker",
            str(self.tracker),
            "--request-text",
            self.source_text,
            "--authority-source-record",
            self.source_item,
            "--authority-source-sha256",
            self.source_sha256,
        )["binding"]
        self.assertEqual(binding["range_intent"], "full-tracker")
        self.assertEqual(binding["tracker_blocks"], list(range(18)))
        self.assertEqual(binding["explicit_blocks"], [])
        self.assertEqual(
            binding["history"][0]["request_text_sha256"],
            self.source_sha256,
        )

    def test_exact_legacy_terminal_correction_bypasses_only_range_history_compatibility(self) -> None:
        self.bind_legacy_full_range()
        before_policy = (self.directory / "policy.json").read_bytes()
        arguments = self.transition_args("corrected")
        output = io.StringIO()
        with redirect_stdout(output):
            arguments.func(arguments)
        result = json.loads(output.getvalue())

        self.assertFalse(result["duplicate"])
        self.assertEqual(result["record"]["phase"], "corrected")
        self.assertEqual(result["record"]["prior_record_id"], self.transition_record)
        self.assertEqual((self.directory / "policy.json").read_bytes(), before_policy)
        records = supervision_log.successor_transition_events(
            supervision_log.events(self.directory / "events.jsonl"),
            self.transition_id,
        )
        self.assertEqual([item["phase"] for item in records], ["required", "corrected"])

    def test_legacy_terminal_predicate_rejects_wrong_receipt_source_transition_and_currentness(self) -> None:
        self.bind_legacy_full_range()
        before = self.state()
        policy = supervision_log.read_json(self.directory / "policy.json")
        all_events = supervision_log.events(self.directory / "events.jsonl")
        policy_history = supervision_log.events(self.directory / "policy-history.jsonl")
        prior = supervision_log.successor_transition_events(
            all_events, self.transition_id
        )[-1]
        record = {
            **prior,
            "phase": "corrected",
            "governing_authority_source_sha256": self.source_sha256,
            "prior_record_id": prior["record_id"],
            "disposition_reason": "Retire the stale pre-contract transition.",
            "correction_authority_source_class": "direct-user",
            "correction_authority_source_record": self.source_item,
            "correction_authority_source_sha256": self.source_sha256,
            "governing_outcome_effect": "continue-same-task",
        }
        contract = supervision_log.implementation_range_contract(policy)
        range_state = supervision_log.implementation_range_state(policy)
        self.assertIsNotNone(contract)
        self.assertIsNotNone(range_state)

        def eligible(
            candidate_policy: dict[str, object],
            candidate_events: list[dict[str, object]],
            candidate_prior: dict[str, object],
            candidate_record: dict[str, object],
        ) -> bool:
            return supervision_log.legacy_terminal_range_compatibility_eligible(
                candidate_policy,
                all_events=candidate_events,
                policy_history=policy_history,
                prior=candidate_prior,
                record=candidate_record,
                contract=contract,
                range_state=range_state,
            )

        self.assertTrue(eligible(policy, all_events, prior, record))
        for phase in supervision_log.SUCCESSOR_TRANSITION_TERMINAL_PHASES:
            terminal = {
                **record,
                "phase": phase,
                "governing_outcome_effect": (
                    "continue-replacement-transition"
                    if phase == "superseded"
                    else "continue-same-task"
                ),
            }
            self.assertTrue(eligible(policy, all_events, prior, terminal), phase)
        variants = []
        missing_receipt = copy.deepcopy(policy)
        missing_receipt["direct_authority_receipts"] = []
        variants.append((missing_receipt, all_events, prior, record))
        wrong_receipt = copy.deepcopy(policy)
        wrong_receipt["direct_authority_receipts"][0]["source_sha256"] = "f" * 64
        variants.append((wrong_receipt, all_events, prior, record))
        stale_policy = copy.deepcopy(policy)
        stale_policy["policy_version"] = 1
        variants.append((stale_policy, all_events, prior, record))
        missing_source = [
            item
            for item in all_events
            if item.get("kind") != supervision_log.DIRECT_AUTHORITY_EVENT_KIND
        ]
        variants.append((policy, missing_source, prior, record))
        wrong_source = copy.deepcopy(all_events)
        next(
            item
            for item in wrong_source
            if item.get("kind") == supervision_log.DIRECT_AUTHORITY_EVENT_KIND
        )["source_sha256"] = "f" * 64
        variants.append((policy, wrong_source, prior, record))
        wrong_prior = {**prior, "record_id": "EVT-999999"}
        variants.append((policy, all_events, wrong_prior, record))
        nonterminal = {**record, "phase": "successor-created"}
        variants.append((policy, all_events, prior, nonterminal))
        ordinary = {
            **prior,
            "governing_authority_source_sha256": self.source_sha256,
            "topology_posture": "same-task-new-run",
            "topology_basis": "same-task-default",
        }
        variants.append((policy, all_events, ordinary, record))
        for candidate in variants:
            self.assertFalse(eligible(*candidate))
        self.assertEqual(self.state(), before)

    def test_nonterminal_and_modern_incompatible_transitions_remain_fail_closed(self) -> None:
        modern = self.append_legacy_transition(
            transition_id="TRANSITION-MODERN-1234", modern=True
        )
        self.bind_legacy_full_range()
        before = self.state()
        attempts = (
            self.transition_args(
                "successor-created",
                extra=("--successor-thread", "successor-1234"),
            ),
            self.transition_args("corrected", transition=modern),
        )
        for arguments in attempts:
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "not structurally compatible",
            ):
                with redirect_stdout(io.StringIO()):
                    arguments.func(arguments)
            self.assertEqual(self.state(), before)

    def test_concurrent_close_rejects_terminal_candidate_without_extra_mutation(self) -> None:
        self.bind_legacy_full_range()
        before_policy = (self.directory / "policy.json").read_bytes()
        original_lock = supervision_log.owner_append_lock

        @contextmanager
        def close_before_candidate(root, target_thread, directory_snapshot):
            with original_lock(root, target_thread, directory_snapshot) as directory_fd:
                current, snapshot = supervision_log.events_snapshot(
                    Path("events.jsonl"), directory_fd=directory_fd
                )
                supervision_log.append_raw_locked_at(
                    directory_fd,
                    "events.jsonl",
                    {
                        "schema_version": 1,
                        "record_id": f"EVT-{len(current) + 1:06d}",
                        "timestamp": supervision_log.utc_now(),
                        "target_thread_id": self.target,
                        "kind": "successor-transition",
                        "transition_id": self.transition_id,
                        "phase": "cancelled",
                        "evidence": ["deterministic-concurrent-close"],
                        "policy_sha256": policy["policy_sha256"],
                    },
                    previous_record_sha256=str(current[-1]["record_sha256"]),
                    expected_file_snapshot=snapshot,
                    require_event_anchor=True,
                )
                yield directory_fd

        policy = supervision_log.read_json(self.directory / "policy.json")
        arguments = self.transition_args("corrected")
        with mock.patch.object(
            supervision_log, "owner_append_lock", side_effect=close_before_candidate
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "event state changed before append",
            ):
                with redirect_stdout(io.StringIO()):
                    arguments.func(arguments)
        self.assertEqual((self.directory / "policy.json").read_bytes(), before_policy)
        records = supervision_log.successor_transition_events(
            supervision_log.events(self.directory / "events.jsonl"),
            self.transition_id,
        )
        self.assertEqual([item["phase"] for item in records], ["required", "cancelled"])

    def test_generic_classifier_still_rejects_local_paths(self) -> None:
        self.assertEqual(
            supervision_log.classify_implementation_request(
                "implement this tracker", set(range(18))
            ),
            ("full-tracker", list(range(18))),
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "must not contain a local path",
        ):
            supervision_log.classify_implementation_request(
                self.source_text, set(range(18))
            )

    def test_wrong_identity_hash_policy_and_ineligible_verifier_reject_without_mutation(self) -> None:
        provenance = self.provenance()
        self.append_review(provenance)
        variants = []
        for field, value in (
            ("target_thread_id", "wrong-target-1234"),
            ("source_task_id", "wrong-task-1234"),
            ("source_turn_id", "wrong-turn-1234"),
            ("source_item_id", "wrong-item-1234"),
            ("source_byte_count", 323),
            ("source_sha256", "f" * 64),
            ("policy_version", 999),
            ("policy_sha256", "e" * 64),
            ("verifier_id", self.watcher),
            ("authorization_record_id", "fabricated-review-1234"),
            ("legacy_transition_record_id", "EVT-999999"),
            ("legacy_transition_id", "TRANSITION-WRONG-1234"),
        ):
            changed = copy.deepcopy(provenance)
            changed[field] = value
            variants.append((field, changed))
        for field, changed in variants:
            with self.subTest(field=field):
                self.assert_rejected_without_mutation(changed, ".+")

    def test_normalized_and_altered_skill_link_forms_reject_without_mutation(self) -> None:
        variants = {
            "normalized": "implement this tracker\n",
            "label": self.source_text.replace(
                "$author-implementation-trackers",
                "$author-implementation-tracker",
            ),
            "destination": self.source_text.replace(
                "author-implementation-trackers/SKILL.md",
                "other-skill/SKILL.md",
            ),
            "order": self.source_text.replace(
                "[$author-implementation-trackers]",
                "[$temporary-link]",
            ),
            "clause": self.source_text.replace(
                "for that tracker", "for Blocks 0-17"
            ),
            "other-local-path": (
                "[$author-implementation-trackers](/Users/example/other/SKILL.md) "
                "for this all / make sure the tracker is up to date with what we've "
                "discussed. then [$implement-tracker-blocks]"
                "(/Users/example/implement-tracker-blocks/SKILL.md) for that tracker\n"
            ),
        }
        for label, text in variants.items():
            with self.subTest(label=label):
                provenance = self.provenance(source_text=text)
                self.append_review(provenance)
                self.assert_rejected_without_mutation(
                    provenance, "allowlisted skill-link form|destinations differ"
                )

    def test_routed_fabricated_nonlegacy_and_replayed_authority_reject_without_mutation(self) -> None:
        routed = self.provenance()
        self.append_review(routed, kind="escalation")
        self.assert_rejected_without_mutation(routed, "independent exact provenance")

        modern = self.append_legacy_transition(
            transition_id="TRANSITION-MODERN-1234", modern=True
        )
        nonlegacy = self.provenance(
            transition_record=str(modern["record_id"]),
            transition_id="TRANSITION-MODERN-1234",
        )
        self.append_review(nonlegacy)
        self.assert_rejected_without_mutation(nonlegacy, "not the exact unbound legacy")

        accepted = self.provenance()
        authorization = self.append_review(accepted)
        self.ingest(accepted)
        replay = copy.deepcopy(accepted)
        replay["source_text"] = self.source_text.replace("this all", "all this")
        replay["source_byte_count"] = len(
            str(replay["source_text"]).encode("utf-8")
        )
        replay["source_sha256"] = hashlib.sha256(
            str(replay["source_text"]).encode("utf-8")
        ).hexdigest()
        replay["authorization_record_id"] = authorization["record_id"]
        self.assert_rejected_without_mutation(replay, ".+")

    def test_closed_legacy_transition_rejects_without_mutation(self) -> None:
        provenance = self.provenance()
        self.append_review(provenance)
        policy = supervision_log.read_json(self.directory / "policy.json")
        self.append_event(
            {
                "kind": "successor-transition",
                "transition_id": self.transition_id,
                "phase": "cancelled",
                "governing_authority_source_class": "direct-user",
                "governing_authority_source_record": self.source_item,
                "policy_sha256": policy["policy_sha256"],
                "evidence": ["legacy-transition-cancelled-before-ingestion"],
            }
        )
        self.assert_rejected_without_mutation(
            provenance, "not the exact unbound legacy|no longer the open"
        )

    def test_review_before_legacy_transition_cannot_become_retroactive_authority(self) -> None:
        future_transition_id = "TRANSITION-FUTURE-1234"
        future_record_id = (
            f"EVT-{len(supervision_log.events(self.directory / 'events.jsonl')) + 2:06d}"
        )
        provenance = self.provenance(
            transition_record=future_record_id,
            transition_id=future_transition_id,
        )
        self.append_review(provenance)
        transition = self.append_legacy_transition(
            transition_id=future_transition_id
        )
        self.assertEqual(transition["record_id"], future_record_id)

        self.assert_rejected_without_mutation(
            provenance,
            "transition must precede its independent authorization",
        )

    def test_transition_cancellation_between_classification_and_write_rejects_policy_mutation(self) -> None:
        provenance = self.provenance()
        self.append_review(provenance)
        ingested = self.ingest(provenance)
        self.call(
            "implementation-range-authority-receipt",
            "--target-thread",
            self.target,
            "--authority-event-record",
            str(ingested["record_id"]),
        )
        policy_before = (self.directory / "policy.json").read_bytes()
        history_before = (self.directory / "policy-history.jsonl").read_bytes()
        original_write = supervision_log.write_policy_version

        def cancel_then_write(*args: object, **kwargs: object) -> None:
            policy = supervision_log.read_json(self.directory / "policy.json")
            self.append_event(
                {
                    "kind": "successor-transition",
                    "transition_id": self.transition_id,
                    "phase": "cancelled",
                    "governing_authority_source_class": "direct-user",
                    "governing_authority_source_record": self.source_item,
                    "policy_sha256": policy["policy_sha256"],
                    "evidence": ["deterministic-cancel-before-range-write"],
                }
            )
            original_write(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "write_policy_version",
            side_effect=cancel_then_write,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "event state changed before range bind",
            ):
                self.call(
                    "implementation-range-bind",
                    "--target-thread",
                    self.target,
                    "--range-id",
                    "RANGE-ITEM-340",
                    "--tracker",
                    str(self.tracker),
                    "--request-text",
                    self.source_text,
                    "--authority-source-record",
                    self.source_item,
                    "--authority-source-sha256",
                    self.source_sha256,
                )

        self.assertEqual((self.directory / "policy.json").read_bytes(), policy_before)
        self.assertEqual(
            (self.directory / "policy-history.jsonl").read_bytes(),
            history_before,
        )
        self.assertIsNone(
            supervision_log.read_json(self.directory / "policy.json").get(
                "implementation_range"
            )
        )
        transitions = supervision_log.successor_transition_events(
            supervision_log.events(self.directory / "events.jsonl"),
            self.transition_id,
        )
        self.assertEqual(transitions[-1]["phase"], "cancelled")


class ControlPostureReducerTests(unittest.TestCase):
    owner = "owner-1234"
    child = "child-1234"
    owner_mission = "a" * 64
    child_mission = "b" * 64

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def create_target(self, target: str, mission_root: str) -> tuple[Path, dict[str, object]]:
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
                mission_root,
                "--mission-source-record",
                f"mission-{target}",
            ]
        )
        policy = supervision_log.default_policy(args)
        directory = self.root / target
        directory.mkdir()
        supervision_log.atomic_json(directory / "policy.json", policy)
        return directory, policy

    def append(self, directory: Path, value: dict[str, object]) -> None:
        supervision_log.append_raw(directory / "events.jsonl", value)

    def reduce(self, directory: Path, policy: dict[str, object]) -> dict[str, object]:
        return supervision_log.reduce_control_posture(
            directory=directory,
            policy=policy,
            owner_events=supervision_log.events(directory / "events.jsonl"),
        )

    def record_public_transition(self, phase: str, *extra: str) -> dict[str, object]:
        directory = self.root / self.owner
        topology_events = [
            item
            for item in supervision_log.events(directory / "events.jsonl")
            if item.get("kind") == supervision_log.SUCCESSOR_TOPOLOGY_EVENT_KIND
        ]
        if not topology_events:
            policy = supervision_log.read_json(directory / "policy.json")
            current_events = supervision_log.events(directory / "events.jsonl")
            topology_record = f"EVT-{len(current_events) + 1:06d}"
            supervision_log.append_raw(
                directory / "events.jsonl",
                {
                    "schema_version": 1,
                    "record_id": topology_record,
                    "timestamp": supervision_log.utc_now(),
                    "target_thread_id": self.owner,
                    "kind": supervision_log.SUCCESSOR_TOPOLOGY_EVENT_KIND,
                    "transition_id": "TRANSITION-PUBLIC-1234",
                    "topology_posture": "distinct-task",
                    "topology_basis": "technical-isolation",
                    "topology_rationale": "A separate target owner is required.",
                    "governing_authority_source_class": "direct-user",
                    "governing_authority_source_record": f"mission-{self.owner}",
                    "governing_authority_source_sha256": self.owner_mission,
                    "verifier_id": f"base-{self.owner}",
                    "provenance_status": "accepted-before-entry",
                    "policy_sha256": policy["policy_sha256"],
                    "evidence": ["independent-public-transition-review"],
                },
            )
        else:
            topology_record = str(topology_events[0]["record_id"])
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "successor-transition-record",
                "--target-thread",
                self.owner,
                "--transition-id",
                "TRANSITION-PUBLIC-1234",
                "--phase",
                phase,
                "--tracker-sha256",
                "c" * 64,
                "--tracker-source-record",
                "tracker-public-1234",
                "--requested-block-range",
                "Block 0",
                "--first-eligible-block",
                "Block 0",
                "--source-mission-root",
                self.owner_mission,
                "--governing-authority-source-class",
                "direct-user",
                "--governing-authority-source-record",
                f"mission-{self.owner}",
                "--governing-authority-source-sha256",
                self.owner_mission,
                "--topology-posture",
                "distinct-task",
                "--topology-basis",
                "technical-isolation",
                "--topology-rationale",
                "A separate target owner is required.",
                "--topology-decision-event-record",
                topology_record,
                "--state-fingerprint",
                f"state-{phase}",
                "--evidence",
                f"evidence-{phase}",
                *extra,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def record_public_stop_decision(
        self, phase: str, *, outcome: str = ""
    ) -> dict[str, object]:
        arguments = [
            "--root",
            str(self.root),
            "decision-record",
            "--target-thread",
            self.owner,
            "--decision-id",
            "DEC-PUBLIC-STOP-1234",
            "--classification",
            "reserved-authority",
            "--phase",
            phase,
            "--safe-frontier",
            "empty",
            "--attempt",
            "0",
            "--decision-packet-hash",
            "d" * 64,
            "--blocked-scope-hash",
            "e" * 64,
            "--safe-frontier-hash",
            "f" * 64,
            "--state-fingerprint",
            "state-stop-1234",
            "--evidence",
            f"evidence-{phase}",
            "--mission-root",
            self.owner_mission,
            "--authority-source-class",
            "direct-user",
            "--authority-source-record",
            "item-stop-1234",
            "--impact-class",
            "goal-blocking",
            "--affected-width",
            "governing-outcome",
            "--duration",
            "until-stopped",
            "--reversibility",
            "reversible",
            "--ordinary-means-disabled",
            "yes",
            "--independent-mission-review",
            "yes",
        ]
        if outcome:
            arguments.extend(["--outcome", outcome])
        args = supervision_log.parser().parse_args(arguments)
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def test_identity_types_remain_separate_on_the_default_continue_path(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        identities = result["identities"]
        self.assertEqual(
            identities["governing_outcome"]["root"], self.owner_mission
        )
        member = identities["members"][0]
        self.assertEqual(member["task_id"], self.owner)
        self.assertRegex(
            member["supervision_group_id"],
            r"^supervision-group-[0-9a-f]{24}$",
        )
        self.assertRegex(member["execution_run_id"], r"^[0-9a-f]{64}$")
        self.assertIsNone(member["active_block"])
        self.assertEqual(result["member_count"], 1)
        self.assertFalse(result["human_input_required"])
        self.assertEqual(result, self.reduce(directory, policy))

    def test_public_gate_emits_the_canonical_default_posture(self) -> None:
        self.create_target(self.owner, self.owner_mission)
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "control-posture-gate",
                "--target-thread",
                self.owner,
            ]
        )
        output = io.StringIO()

        with redirect_stdout(output):
            args.func(args)

        result = json.loads(output.getvalue())
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(result["next_action"], "continue-governing-outcome")
        self.assertEqual(result["member_count"], 1)

    def test_later_exact_transition_correction_reconciles_topology_decision(self) -> None:
        target = "owner-reconciliation-1234"
        directory, policy = self.create_target(target, self.owner_mission)
        authority_record = f"mission-{target}"
        transition = {
            "record_id": "EVT-000001",
            "kind": "successor-transition",
            "transition_id": "TRANSITION-RECONCILIATION-1234",
            "phase": "required",
            "tracker_sha256": "c" * 64,
            "source_mission_root": self.owner_mission,
            "state_fingerprint": "state-topology-1234",
            "governing_authority_source_class": "tracker",
            "governing_authority_source_record": authority_record,
        }
        decision_ready = {
            "record_id": "EVT-000002",
            "kind": "decision",
            "decision_id": "DEC-RECONCILIATION-1234",
            "phase": "decision-ready",
            "classification": "reserved-authority",
            "outcome": "",
            "safe_frontier": "empty",
            "state_fingerprint": "state-topology-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "tracker",
            "authority_source_record": authority_record,
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
            "evidence": ["EVT-000001"],
        }
        decision = {
            **decision_ready,
            "record_id": "EVT-000003",
            "kind": "decision",
            "decision_id": "DEC-RECONCILIATION-1234",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "safe-deferred",
            "safe_frontier": "empty",
            "state_fingerprint": "state-topology-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "tracker",
            "authority_source_record": authority_record,
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }
        correction = {
            **transition,
            "record_id": "EVT-000004",
            "phase": "corrected",
            "prior_record_id": "EVT-000001",
            "correction_authority_source_class": "tracker",
            "correction_authority_source_record": authority_record,
            "correction_authority_source_sha256": self.owner_mission,
            "governing_outcome_effect": "continue-same-task",
            "evidence": ["current-direct-correction-1234"],
        }
        for record in (transition, decision_ready, decision, correction):
            self.append(directory, record)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(result["next_action"], "continue-governing-outcome")
        self.assertEqual(result["open_decision_records"], [])
        self.assertEqual(result["blocking_decision_records"], [])
        self.assertEqual(
            result["reconciled_decisions"][0]["correction_record_id"],
            "EVT-000004",
        )
        self.assertEqual(
            result["reconciled_decisions"][0]["reconciliation_posture"],
            "append-explicit-decision-correction",
        )

        mismatch_target = "owner-reconciliation-mismatch-1234"
        mismatch_directory, mismatch_policy = self.create_target(
            mismatch_target, self.owner_mission
        )
        mismatch_authority = f"mission-{mismatch_target}"
        for record in (
            {**transition, "governing_authority_source_record": mismatch_authority},
            {
                **decision_ready,
                "authority_source_record": mismatch_authority,
            },
            {
                **decision,
                "authority_source_record": mismatch_authority,
                "state_fingerprint": "different-decision-state-1234",
            },
            {
                **correction,
                "correction_authority_source_record": mismatch_authority,
            },
        ):
            self.append(mismatch_directory, record)
        mismatch = self.reduce(mismatch_directory, mismatch_policy)
        self.assertEqual(mismatch["required_target_posture"], "blocked")
        self.assertEqual(mismatch["reconciled_decisions"], [])

    def test_later_uncited_transition_cannot_reconcile_safe_deferral(self) -> None:
        target = "owner-later-transition-1234"
        directory, policy = self.create_target(target, self.owner_mission)
        authority_record = f"mission-{target}"
        decision_ready = {
            "record_id": "EVT-000001",
            "kind": "decision",
            "decision_id": "DEC-LATER-TRANSITION-1234",
            "phase": "decision-ready",
            "classification": "reserved-authority",
            "outcome": "",
            "safe_frontier": "empty",
            "state_fingerprint": "state-later-transition-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "tracker",
            "authority_source_record": authority_record,
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
            "evidence": ["missing-transition-premise-1234"],
        }
        decision = {
            **decision_ready,
            "record_id": "EVT-000002",
            "phase": "target-acknowledged",
            "outcome": "safe-deferred",
        }
        transition = {
            "record_id": "EVT-000003",
            "kind": "successor-transition",
            "transition_id": "TRANSITION-LATER-1234",
            "phase": "required",
            "tracker_sha256": "c" * 64,
            "source_mission_root": self.owner_mission,
            "state_fingerprint": "state-later-transition-1234",
            "governing_authority_source_class": "tracker",
            "governing_authority_source_record": authority_record,
        }
        correction = {
            **transition,
            "record_id": "EVT-000004",
            "phase": "corrected",
            "prior_record_id": "EVT-000003",
            "correction_authority_source_class": "tracker",
            "correction_authority_source_record": authority_record,
            "correction_authority_source_sha256": self.owner_mission,
            "governing_outcome_effect": "continue-same-task",
            "evidence": ["current-direct-correction-1234"],
        }
        for record in (decision_ready, decision, transition, correction):
            self.append(directory, record)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "blocked")
        self.assertEqual(result["open_decision_records"], ["EVT-000002"])
        self.assertEqual(result["blocking_decision_records"], ["EVT-000002"])
        self.assertEqual(result["reconciled_decisions"], [])

    def test_ambiguous_cited_transition_lineage_cannot_reconcile_safe_deferral(
        self,
    ) -> None:
        target = "owner-ambiguous-transition-1234"
        directory, policy = self.create_target(target, self.owner_mission)
        authority_record = f"mission-{target}"
        transitions = []
        for index in (1, 2):
            transitions.append(
                {
                    "record_id": f"EVT-00000{index}",
                    "kind": "successor-transition",
                    "transition_id": f"TRANSITION-AMBIGUOUS-{index}-1234",
                    "phase": "required",
                    "tracker_sha256": "c" * 64,
                    "source_mission_root": self.owner_mission,
                    "state_fingerprint": "state-ambiguous-transition-1234",
                    "governing_authority_source_class": "tracker",
                    "governing_authority_source_record": authority_record,
                }
            )
        decision_ready = {
            "record_id": "EVT-000003",
            "kind": "decision",
            "decision_id": "DEC-AMBIGUOUS-TRANSITION-1234",
            "phase": "decision-ready",
            "classification": "reserved-authority",
            "outcome": "",
            "safe_frontier": "empty",
            "state_fingerprint": "state-ambiguous-transition-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "tracker",
            "authority_source_record": authority_record,
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
            "evidence": ["EVT-000001", "EVT-000002"],
        }
        decision = {
            **decision_ready,
            "record_id": "EVT-000004",
            "phase": "target-acknowledged",
            "outcome": "safe-deferred",
        }
        corrections = []
        for index, transition in enumerate(transitions, start=5):
            corrections.append(
                {
                    **transition,
                    "record_id": f"EVT-00000{index}",
                    "phase": "corrected",
                    "prior_record_id": transition["record_id"],
                    "correction_authority_source_class": "tracker",
                    "correction_authority_source_record": authority_record,
                    "correction_authority_source_sha256": self.owner_mission,
                    "governing_outcome_effect": "continue-same-task",
                    "evidence": ["current-direct-correction-1234"],
                }
            )
        for record in (*transitions, decision_ready, decision, *corrections):
            self.append(directory, record)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "blocked")
        self.assertEqual(result["blocking_decision_records"], ["EVT-000004"])
        self.assertEqual(result["reconciled_decisions"], [])

    def test_cited_transition_requires_nonempty_decision_ready_fingerprint(
        self,
    ) -> None:
        target = "owner-empty-transition-state-1234"
        directory, policy = self.create_target(target, self.owner_mission)
        authority_record = f"mission-{target}"
        transition = {
            "record_id": "EVT-000001",
            "kind": "successor-transition",
            "transition_id": "TRANSITION-EMPTY-STATE-1234",
            "phase": "required",
            "tracker_sha256": "c" * 64,
            "source_mission_root": self.owner_mission,
            "state_fingerprint": "",
            "governing_authority_source_class": "tracker",
            "governing_authority_source_record": authority_record,
        }
        decision_ready = {
            "record_id": "EVT-000002",
            "kind": "decision",
            "decision_id": "DEC-EMPTY-TRANSITION-STATE-1234",
            "phase": "decision-ready",
            "classification": "reserved-authority",
            "outcome": "",
            "safe_frontier": "empty",
            "state_fingerprint": "",
            "mission_root": self.owner_mission,
            "authority_source_class": "tracker",
            "authority_source_record": authority_record,
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
            "evidence": ["EVT-000001"],
        }
        decision = {
            **decision_ready,
            "record_id": "EVT-000003",
            "phase": "target-acknowledged",
            "outcome": "safe-deferred",
        }
        correction = {
            **transition,
            "record_id": "EVT-000004",
            "phase": "corrected",
            "prior_record_id": "EVT-000001",
            "correction_authority_source_class": "tracker",
            "correction_authority_source_record": authority_record,
            "correction_authority_source_sha256": self.owner_mission,
            "governing_outcome_effect": "continue-same-task",
            "evidence": ["current-direct-correction-1234"],
        }
        for record in (transition, decision_ready, decision, correction):
            self.append(directory, record)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "blocked")
        self.assertEqual(result["reconciled_decisions"], [])

    def test_cyclic_successor_membership_fails_into_reconciliation(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.owner,
                "successor_mission_root": self.owner_mission,
                "successor_group_id": "group-owner-1234",
            },
        )

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(
            result["next_action"], "reconcile-control-membership-or-evidence"
        )
        self.assertIn(
            "successor-membership-cycle-or-duplicate",
            {item["kind"] for item in result["issues"]},
        )

    def test_escaped_successor_path_fails_into_reconciliation(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        (self.root / self.child).symlink_to(Path(external.name), target_is_directory=True)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": "group-child-1234",
            },
        )

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertIn(
            "member-state-unavailable-or-invalid",
            {item["kind"] for item in result["issues"]},
        )

    def test_successor_membership_stops_at_the_eight_member_bound(self) -> None:
        targets = [f"member-{index:04d}" for index in range(9)]
        missions = [f"{index:x}" * 64 for index in range(9)]
        created = [
            self.create_target(target, mission)
            for target, mission in zip(targets, missions, strict=True)
        ]
        for index in range(8):
            directory, _policy = created[index]
            _successor_directory, successor_policy = created[index + 1]
            self.append(
                directory,
                {
                    "record_id": "EVT-000001",
                    "kind": "successor-transition",
                    "transition_id": f"TRANSITION-{index:04d}",
                    "phase": "work-started",
                    "tracker_sha256": "c" * 64,
                    "successor_thread_id": targets[index + 1],
                    "successor_mission_root": missions[index + 1],
                    "successor_group_id": (
                        supervision_log.supervision_group_identity(successor_policy)[0]
                    ),
                },
            )

        owner_directory, owner_policy = created[0]
        result = self.reduce(owner_directory, owner_policy)

        self.assertEqual(result["member_count"], 8)
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertIn(
            "member-bound-exceeded",
            {item["kind"] for item in result["issues"]},
        )

    def test_open_transition_overrides_a_locally_blocking_decision(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "decision",
                "decision_id": "DEC-1234",
                "phase": "handoff-sent",
                "classification": "reserved-authority",
                "outcome": "safe-deferred",
                "safe_frontier": "empty",
                "mission_root": self.owner_mission,
                "authority_source_class": "direct-user",
                "authority_source_record": "item-340",
                "impact_class": "goal-blocking",
                "ordinary_means_disabled": True,
                "independent_mission_review": True,
            },
        )
        self.append(
            directory,
            {
                "record_id": "EVT-000002",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-1234",
                "phase": "required",
                "tracker_sha256": "c" * 64,
            },
        )

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(result["next_action"], "continue-open-successor-transition")
        self.assertEqual(result["blocking_decision_records"], ["EVT-000001"])
        self.assertEqual(result["open_transition_records"], ["EVT-000002"])

    def test_exact_direct_safe_deferral_can_block_after_safe_work_is_exhausted(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "decision",
                "decision_id": "DEC-1234",
                "phase": "target-acknowledged",
                "classification": "reserved-authority",
                "outcome": "safe-deferred",
                "safe_frontier": "empty",
                "mission_root": self.owner_mission,
                "authority_source_class": "direct-user",
                "authority_source_record": "item-340",
                "impact_class": "goal-blocking",
                "ordinary_means_disabled": True,
                "independent_mission_review": True,
            },
        )

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "blocked")
        self.assertEqual(
            result["next_action"],
            "preserve-safe-deferral-and-revisit-on-authority-change",
        )
        self.assertEqual(result["blocking_decision_records"], ["EVT-000001"])

    def test_routed_authority_cannot_turn_a_safe_deferral_into_a_stop(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "decision",
                "decision_id": "DEC-1234",
                "phase": "target-acknowledged",
                "classification": "reserved-authority",
                "outcome": "safe-deferred",
                "safe_frontier": "empty",
                "mission_root": self.owner_mission,
                "authority_source_class": "supervisor-steer",
                "authority_source_record": "EVT-ROUTED",
                "impact_class": "goal-blocking",
                "ordinary_means_disabled": True,
                "independent_mission_review": True,
            },
        )

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(
            result["next_action"], "continue-safe-frontier-or-resolve-decision"
        )
        self.assertEqual(result["blocking_decision_records"], [])

    def test_exact_successor_edge_joins_one_member_without_scanning(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        _child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": supervision_log.supervision_group_identity(
                    child_policy
                )[0],
                "started_block": "Block 0",
            },
        )

        result = self.reduce(owner_directory, owner_policy)

        self.assertEqual(result["member_count"], 2)
        self.assertEqual(result["issues"], [])
        self.assertTrue(result["snapshot_stable"])
        self.assertEqual(result["identities"]["tracker_program_roots"], ["c" * 64])
        self.assertEqual(
            {item["task_id"] for item in result["identities"]["members"]},
            {self.owner, self.child},
        )

        records = supervision_log.events(owner_directory / "events.jsonl")
        records[0]["successor_group_id"] = "wrong-group-1234"
        mismatched = supervision_log.reduce_control_posture(
            directory=owner_directory,
            policy=owner_policy,
            owner_events=records,
        )
        self.assertIn(
            "member-group-mismatch",
            {item["kind"] for item in mismatched["issues"]},
        )

    def test_public_transition_writer_produces_a_successfully_joined_group(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        _child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        successor = ["--successor-thread", self.child]
        bound = [
            *successor,
            "--successor-mission-root",
            self.child_mission,
            "--successor-group-id",
            str(child_policy["supervision_group_id"]),
        ]
        handed_off = [*bound, "--handoff-record", "HANDOFF-PUBLIC-1234"]
        acknowledged = [
            *handed_off,
            "--acknowledgement-record",
            "ACK-PUBLIC-1234",
        ]

        self.record_public_transition("required")
        self.record_public_transition("successor-created", *successor)
        self.record_public_transition("successor-bound", *bound)
        self.record_public_transition("handoff-sent", *handed_off)
        self.record_public_transition("target-acknowledged", *acknowledged)
        self.record_public_transition(
            "work-started", *acknowledged, "--started-block", "Block 0"
        )

        result = self.reduce(owner_directory, owner_policy)
        self.assertEqual(result["member_count"], 2)
        self.assertEqual(result["issues"], [])
        child_member = next(
            item
            for item in result["identities"]["members"]
            if item["task_id"] == self.child
        )
        self.assertEqual(child_member["supervision_group_binding"], "policy")

    def test_legacy_literal_group_claim_remains_readable(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        child_policy.pop("supervision_group_id")
        child_policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(child_policy)
        )
        supervision_log.atomic_json(child_directory / "policy.json", child_policy)
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-LEGACY-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": "group-1234",
            },
        )

        result = self.reduce(owner_directory, owner_policy)

        self.assertEqual(result["issues"], [])
        child_member = next(
            item
            for item in result["identities"]["members"]
            if item["task_id"] == self.child
        )
        self.assertEqual(child_member["supervision_group_id"], "group-1234")
        self.assertEqual(
            child_member["supervision_group_binding"], "legacy-transition"
        )
        self.assertEqual(
            child_member["execution_run_id"],
            supervision_log.digest(
                {
                    "kind": "execution-run",
                    "governing_outcome_root": self.child_mission,
                    "task_id": self.child,
                    "supervision_group_id": "group-1234",
                }
            ),
        )

    def test_malformed_persisted_group_cannot_downgrade_to_a_legacy_claim(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        child_policy["supervision_group_id"] = "not valid"
        child_policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(child_policy)
        )
        supervision_log.atomic_json(child_directory / "policy.json", child_policy)
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-MALFORMED-GROUP-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": "attacker-group",
            },
        )

        result = self.reduce(owner_directory, owner_policy)

        self.assertEqual(result["member_count"], 1)
        self.assertIn(
            "member-state-unavailable-or-invalid",
            {item["kind"] for item in result["issues"]},
        )

    def test_join_rejects_symlinked_canonical_policy_file(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_policy = Path(external.name) / "policy.json"
        supervision_log.atomic_json(external_policy, child_policy)
        (child_directory / "policy.json").unlink()
        (child_directory / "policy.json").symlink_to(external_policy)
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-POLICY-LINK-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": child_policy["supervision_group_id"],
            },
        )

        result = self.reduce(owner_directory, owner_policy)
        self.assertEqual(result["member_count"], 1)
        self.assertIn(
            "member-state-unavailable-or-invalid",
            {item["kind"] for item in result["issues"]},
        )

    def test_join_rejects_symlinked_canonical_event_file(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_events = Path(external.name) / "events.jsonl"
        supervision_log.append_raw(
            external_events,
            {"record_id": "EVT-000001", "kind": "check", "status": "ok"},
        )
        (child_directory / "events.jsonl").symlink_to(external_events)
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-EVENT-LINK-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": child_policy["supervision_group_id"],
            },
        )

        result = self.reduce(owner_directory, owner_policy)
        self.assertEqual(result["member_count"], 1)
        self.assertIn(
            "member-state-unavailable-or-invalid",
            {item["kind"] for item in result["issues"]},
        )

    def test_event_file_link_replacement_fails_the_snapshot_recheck(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {"record_id": "EVT-000001", "kind": "check", "status": "ok"},
        )
        owner_events, event_snapshot = supervision_log.events_snapshot(
            directory / "events.jsonl"
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_events = Path(external.name) / "events.jsonl"
        supervision_log.append_raw(
            external_events,
            {"record_id": "EVT-000001", "kind": "check", "status": "ok"},
        )
        (directory / "events.jsonl").unlink()
        (directory / "events.jsonl").symlink_to(external_events)

        result = supervision_log.reduce_control_posture(
            directory=directory,
            policy=policy,
            owner_events=owner_events,
            owner_event_snapshot=event_snapshot,
        )

        self.assertFalse(result["snapshot_stable"])
        self.assertEqual(result["next_action"], "retry-control-currentness")
        self.assertIn(
            "member-event-file-changed-during-read",
            {item["kind"] for item in result["issues"]},
        )

    def test_member_directory_link_replacement_cannot_redirect_canonical_reads(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-DIRECTORY-RACE-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": child_policy["supervision_group_id"],
            },
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_directory = Path(external.name)
        supervision_log.atomic_json(
            external_directory / "policy.json", child_policy
        )
        original_open = supervision_log.open_member_directory
        replaced = False

        def open_then_replace(root: Path, target: str):
            nonlocal replaced
            result = original_open(root, target)
            if target == self.child and not replaced:
                preserved = self.root / f"{self.child}-preserved"
                child_directory.rename(preserved)
                child_directory.symlink_to(external_directory, target_is_directory=True)
                replaced = True
            return result

        with mock.patch.object(
            supervision_log,
            "open_member_directory",
            side_effect=open_then_replace,
        ):
            result = self.reduce(owner_directory, owner_policy)

        self.assertTrue(replaced)
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertFalse(result["snapshot_stable"])
        self.assertIn(
            "member-directory-changed-during-read",
            {item["kind"] for item in result["issues"]},
        )

    def test_owner_directory_link_replacement_cannot_supply_terminal_outcome(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_directory = Path(external.name)
        supervision_log.atomic_json(
            external_directory / "policy.json", owner_policy
        )
        self.append(
            external_directory,
            {
                "record_id": "EVT-000001",
                "kind": "check",
                "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                "status": "verified",
                "state_fingerprint": "external-state-1234",
                "mission_root": self.owner_mission,
                "model": "gpt-5.6-sol",
                "reasoning": "xhigh",
                "evidence": ["external-behavior-proof-1234"],
                **{
                    field: "d" * 64
                    for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                },
                "capability_reconciliation_reviewer_id": f"base-{self.owner}",
                "capability_reconciliation_implementation_owner_id": self.owner,
                "capability_reconciliation_revision": "e" * 40,
                "capability_reconciliation_posture": "verified",
                "capability_reconciliation_gap_count": 0,
            },
        )
        self.append(
            external_directory,
            {
                "record_id": "EVT-000002",
                "kind": "lifecycle",
                "status": "completed",
                "state_fingerprint": "external-state-1234",
                "outcome_completion_record_id": "EVT-000001",
            },
        )
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "control-posture-gate",
                "--target-thread",
                self.owner,
            ]
        )
        original_open = supervision_log.open_member_directory
        replaced = False

        def open_then_replace(root: Path, target: str):
            nonlocal replaced
            result = original_open(root, target)
            if target == self.owner and not replaced:
                preserved = self.root / f"{self.owner}-preserved"
                owner_directory.rename(preserved)
                owner_directory.symlink_to(
                    external_directory, target_is_directory=True
                )
                replaced = True
            return result

        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "open_member_directory",
                side_effect=open_then_replace,
            ),
            redirect_stdout(output),
        ):
            args.func(args)

        result = json.loads(output.getvalue())
        self.assertTrue(replaced)
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertFalse(result["snapshot_stable"])
        self.assertEqual(result["completion_candidates"], [])
        self.assertIn(
            "member-directory-changed-during-read",
            {item["kind"] for item in result["issues"]},
        )

    def test_changed_member_head_returns_retry_currentness(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {"record_id": "EVT-000001", "kind": "check", "status": "ok"},
        )

        with mock.patch.object(
            supervision_log, "event_head_hash", return_value="f" * 64
        ):
            result = self.reduce(directory, policy)

        self.assertFalse(result["snapshot_stable"])
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(result["next_action"], "retry-control-currentness")

    def test_changed_policy_returns_retry_currentness(self) -> None:
        directory, _policy = self.create_target(self.owner, self.owner_mission)
        original_reader = supervision_log.read_json_snapshot

        def read_then_replace(path: Path, *, directory_fd: int | None = None):
            value, snapshot = original_reader(path, directory_fd=directory_fd)
            replacement = dict(value)
            replacement["updated_at"] = "2026-08-09T00:00:00+00:00"
            replacement["policy_sha256"] = supervision_log.digest(
                supervision_log.policy_material(replacement)
            )
            supervision_log.atomic_json(directory / "policy.json", replacement)
            return value, snapshot

        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "control-posture-gate",
                "--target-thread",
                self.owner,
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "read_json_snapshot",
                side_effect=read_then_replace,
            ),
            redirect_stdout(output),
        ):
            args.func(args)

        result = json.loads(output.getvalue())
        self.assertFalse(result["snapshot_stable"])
        self.assertEqual(result["next_action"], "retry-control-currentness")
        self.assertIn(
            "member-directory-changed-during-read",
            {item["kind"] for item in result["issues"]},
        )

    def test_completed_lifecycle_writer_rejects_post_reducer_policy_mutation(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "check",
                "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                "status": "verified",
                "state_fingerprint": "state-1234",
                "mission_root": self.owner_mission,
                "model": "gpt-5.6-sol",
                "reasoning": "xhigh",
                "evidence": ["behavior-proof-1234"],
                **{
                    field: "d" * 64
                    for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                },
                "capability_reconciliation_reviewer_id": f"base-{self.owner}",
                "capability_reconciliation_implementation_owner_id": self.owner,
                "capability_reconciliation_revision": "e" * 40,
                "capability_reconciliation_posture": "verified",
                "capability_reconciliation_gap_count": 0,
            },
        )
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "record",
                "--target-thread",
                self.owner,
                "--kind",
                "lifecycle",
                "--status",
                "completed",
                "--state-fingerprint",
                "state-1234",
                "--summary",
                "Attempted completion during policy replacement.",
            ]
        )
        original_reduce = supervision_log.reduce_control_posture

        def reduce_then_mutate(**values: object):
            result = original_reduce(**values)
            policy_path = directory / "policy.json"
            original_stat = policy_path.stat()
            original_snapshot = supervision_log.path_snapshot(policy_path)
            replacement = json.loads(json.dumps(policy))
            replacement["mission_binding"]["mission_root"] = "f" * 64
            serialized = (
                json.dumps(
                    replacement, ensure_ascii=False, sort_keys=True, indent=2
                )
                + "\n"
            )
            self.assertEqual(len(serialized.encode("utf-8")), original_stat.st_size)
            policy_path.write_text(serialized, encoding="utf-8")
            os.utime(
                policy_path,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
            self.assertEqual(
                supervision_log.path_snapshot(policy_path), original_snapshot
            )
            return result

        with (
            mock.patch.object(
                supervision_log,
                "reduce_control_posture",
                side_effect=reduce_then_mutate,
            ),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "governing-outcome control: retry-control-currentness",
            ),
        ):
            args.func(args)
        self.assertFalse(
            any(
                item.get("status") == "completed"
                for item in supervision_log.events(directory / "events.jsonl")
            )
        )

    def test_completed_lifecycle_append_rejects_owner_directory_replacement(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "check",
                "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                "status": "verified",
                "state_fingerprint": "state-1234",
                "mission_root": self.owner_mission,
                "model": "gpt-5.6-sol",
                "reasoning": "xhigh",
                "evidence": ["behavior-proof-1234"],
                **{
                    field: "d" * 64
                    for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                },
                "capability_reconciliation_reviewer_id": f"base-{self.owner}",
                "capability_reconciliation_implementation_owner_id": self.owner,
                "capability_reconciliation_revision": "e" * 40,
                "capability_reconciliation_posture": "verified",
                "capability_reconciliation_gap_count": 0,
            },
        )
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "record",
                "--target-thread",
                self.owner,
                "--kind",
                "lifecycle",
                "--status",
                "completed",
                "--state-fingerprint",
                "state-1234",
                "--summary",
                "Attempted completion during owner replacement.",
            ]
        )
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        external_directory = Path(external.name)
        supervision_log.atomic_json(external_directory / "policy.json", policy)
        original_reduce = supervision_log.reduce_control_posture
        replaced = False

        def reduce_then_replace(**values: object):
            nonlocal replaced
            result = original_reduce(**values)
            preserved = self.root / f"{self.owner}-preserved-after-reduce"
            directory.rename(preserved)
            directory.symlink_to(external_directory, target_is_directory=True)
            replaced = True
            return result

        with (
            mock.patch.object(
                supervision_log,
                "reduce_control_posture",
                side_effect=reduce_then_replace,
            ),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "governing-outcome control: retry-control-currentness",
            ),
        ):
            args.func(args)

        self.assertTrue(replaced)
        self.assertEqual(
            supervision_log.events(external_directory / "events.jsonl"), []
        )
        self.assertFalse((external_directory / ".append.lock").exists())
        preserved_events = supervision_log.events(
            self.root
            / f"{self.owner}-preserved-after-reduce"
            / "events.jsonl"
        )
        self.assertFalse(
            any(item.get("status") == "completed" for item in preserved_events)
        )

    def test_relative_terminal_append_rejects_regular_file_replacement(self) -> None:
        directory, _policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {"record_id": "EVT-000001", "kind": "check", "status": "ok"},
        )
        _opened_directory, directory_fd, _directory_snapshot = (
            supervision_log.open_member_directory(self.root, self.owner)
        )
        try:
            event_snapshot = supervision_log.path_snapshot_at(
                directory_fd, "events.jsonl"
            )
            original_events = supervision_log.events(directory / "events.jsonl")
            preserved = directory / "events-preserved.jsonl"
            (directory / "events.jsonl").rename(preserved)
            replacement_directory = self.root / "replacement-events"
            replacement_directory.mkdir()
            self.append(
                replacement_directory,
                {
                    "record_id": "EVT-000001",
                    "kind": "check",
                    "status": "replacement",
                },
            )
            (replacement_directory / "events.jsonl").replace(
                directory / "events.jsonl"
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "stale or replaced|changed before append|owner-root history differs",
            ):
                supervision_log.append_raw_locked_at(
                    directory_fd,
                    "events.jsonl",
                    {
                        "record_id": "EVT-000002",
                        "kind": "lifecycle",
                        "status": "completed",
                    },
                    previous_record_sha256=str(
                        original_events[-1]["record_sha256"]
                    ),
                    expected_file_snapshot=event_snapshot,
                )
        finally:
            os.close(directory_fd)

        self.assertFalse(
            any(
                item.get("status") == "completed"
                for item in supervision_log.events(directory / "events.jsonl")
            )
        )

    def test_terminal_append_serializes_a_maintained_policy_writer(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        self.append(
            directory,
            {
                "record_id": "EVT-000001",
                "kind": "check",
                "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
                "status": "verified",
                "state_fingerprint": "state-1234",
                "mission_root": self.owner_mission,
                "model": "gpt-5.6-sol",
                "reasoning": "xhigh",
                "evidence": ["behavior-proof-1234"],
                **{
                    field: "d" * 64
                    for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
                },
                "capability_reconciliation_reviewer_id": f"base-{self.owner}",
                "capability_reconciliation_implementation_owner_id": self.owner,
                "capability_reconciliation_revision": "e" * 40,
                "capability_reconciliation_posture": "verified",
                "capability_reconciliation_gap_count": 0,
            },
        )
        terminal_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "record",
                "--target-thread",
                self.owner,
                "--kind",
                "lifecycle",
                "--status",
                "completed",
                "--state-fingerprint",
                "state-1234",
                "--summary",
                "Complete while a maintained policy writer waits.",
            ]
        )
        proposed_policy = json.loads(json.dumps(policy))
        proposed_policy["mission_binding"] = (
            supervision_log.mission_binding_contract(
                "f" * 64, "replacement-mission-source-1234"
            )
        )
        reducer_paused = threading.Event()
        release_reducer = threading.Event()
        policy_waiting_on_lock = threading.Event()
        errors: list[BaseException] = []
        original_reduce = supervision_log.reduce_control_posture
        original_append_lock_at = supervision_log.append_lock_at

        def paused_reduce(**values: object):
            result = original_reduce(**values)
            reducer_paused.set()
            if not release_reducer.wait(5):
                raise AssertionError("Timed out waiting to release terminal reducer")
            return result

        @contextmanager
        def observed_append_lock_at(directory_fd: int):
            if threading.current_thread().name == "maintained-policy-writer":
                policy_waiting_on_lock.set()
            with original_append_lock_at(directory_fd):
                yield

        def run_terminal() -> None:
            try:
                terminal_args.func(terminal_args)
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        def run_policy_writer() -> None:
            try:
                supervision_log.write_policy_version(
                    directory,
                    proposed_policy,
                    kind="policy-test",
                    reason="Exercise maintained writer serialization.",
                    evidence_values=["threaded-regression"],
                )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        with (
            mock.patch.object(
                supervision_log,
                "reduce_control_posture",
                side_effect=paused_reduce,
            ),
            mock.patch.object(
                supervision_log,
                "append_lock_at",
                side_effect=observed_append_lock_at,
            ),
            mock.patch("builtins.print"),
        ):
            terminal = threading.Thread(target=run_terminal, name="terminal-writer")
            terminal.start()
            self.assertTrue(reducer_paused.wait(5))
            policy_writer = threading.Thread(
                target=run_policy_writer, name="maintained-policy-writer"
            )
            policy_writer.start()
            self.assertTrue(policy_waiting_on_lock.wait(5))
            self.assertEqual(
                supervision_log.read_json(directory / "policy.json")[
                    "policy_sha256"
                ],
                policy["policy_sha256"],
            )
            release_reducer.set()
            terminal.join(5)
            policy_writer.join(5)

        self.assertFalse(terminal.is_alive())
        self.assertFalse(policy_writer.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(
            any(
                item.get("status") == "completed"
                for item in supervision_log.events(directory / "events.jsonl")
            )
        )
        current_policy = supervision_log.read_json(directory / "policy.json")
        supervision_log.validate_policy(current_policy)
        self.assertEqual(
            current_policy["mission_binding"]["mission_root"], "f" * 64
        )

    def test_completion_requires_current_observable_outcome_binding(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        completion = {
            "record_id": "EVT-000001",
            "kind": "check",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "status": "verified",
            "state_fingerprint": "state-1234",
            "mission_root": self.owner_mission,
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "evidence": ["behavior-proof-1234"],
            **{
                field: "d" * 64
                for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
            },
            "capability_reconciliation_reviewer_id": f"base-{self.owner}",
            "capability_reconciliation_implementation_owner_id": self.owner,
            "capability_reconciliation_revision": "e" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }
        self.append(directory, completion)
        self.append(
            directory,
            {
                "record_id": "EVT-000002",
                "kind": "lifecycle",
                "status": "completed",
                "state_fingerprint": "state-1234",
                "outcome_completion_record_id": "EVT-000001",
            },
        )

        completed = self.reduce(directory, policy)
        self.assertEqual(completed["required_target_posture"], "completed")

        records = supervision_log.events(directory / "events.jsonl")
        records[-1]["outcome_completion_record_id"] = "EVT-WRONG"
        stale = supervision_log.reduce_control_posture(
            directory=directory,
            policy=policy,
            owner_events=records,
        )
        self.assertEqual(stale["required_target_posture"], "in-progress")
        self.assertIn(
            "completion-lifecycle-binding-mismatch",
            {item["kind"] for item in stale["issues"]},
        )

    def test_subordinate_completion_does_not_close_the_governing_outcome(self) -> None:
        owner_directory, owner_policy = self.create_target(
            self.owner, self.owner_mission
        )
        child_directory, child_policy = self.create_target(
            self.child, self.child_mission
        )
        self.append(
            owner_directory,
            {
                "record_id": "EVT-000001",
                "kind": "successor-transition",
                "transition_id": "TRANSITION-1234",
                "phase": "work-started",
                "tracker_sha256": "c" * 64,
                "successor_thread_id": self.child,
                "successor_mission_root": self.child_mission,
                "successor_group_id": child_policy["supervision_group_id"],
            },
        )
        completion = {
            "record_id": "EVT-000001",
            "kind": "check",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "status": "verified",
            "state_fingerprint": "state-1234",
            "mission_root": self.child_mission,
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "evidence": ["behavior-proof-1234"],
            **{
                field: "d" * 64
                for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
            },
            "capability_reconciliation_reviewer_id": f"base-{self.child}",
            "capability_reconciliation_implementation_owner_id": self.child,
            "capability_reconciliation_revision": "e" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }
        self.append(child_directory, completion)
        self.append(
            child_directory,
            {
                "record_id": "EVT-000002",
                "kind": "lifecycle",
                "status": "completed",
                "state_fingerprint": "state-1234",
                "outcome_completion_record_id": "EVT-000001",
            },
        )

        result = self.reduce(owner_directory, owner_policy)

        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertEqual(result["completion_candidates"], [])
        self.assertEqual(
            result["subordinate_completion_candidates"][0]["target_thread_id"],
            self.child,
        )

    def test_owner_direct_stop_requires_exact_acknowledged_direct_authority(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        decision = {
            "record_id": "EVT-000001",
            "kind": "decision",
            "decision_id": "DEC-STOP-1234",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "user-supplied",
            "safe_frontier": "empty",
            "state_fingerprint": "state-stop-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "direct-user",
            "authority_source_record": "item-stop-1234",
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }
        lifecycle = {
            "record_id": "EVT-000002",
            "kind": "lifecycle",
            "status": "stopped",
            "state_fingerprint": "state-stop-1234",
            "evidence": ["EVT-000001"],
        }
        self.append(directory, decision)
        self.append(directory, lifecycle)

        stopped = self.reduce(directory, policy)
        self.assertEqual(stopped["required_target_posture"], "stopped")
        self.assertEqual(
            stopped["next_action"], "close-governing-outcome-at-direct-stop"
        )
        gate_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "lifecycle-gate",
                "--target-thread",
                self.owner,
                "--lifecycle-state",
                "stopped",
                "--source-record",
                "EVT-000002",
                "--state-fingerprint",
                "state-stop-1234",
            ]
        )
        gate_output = io.StringIO()
        with redirect_stdout(gate_output):
            gate_args.func(gate_args)
        gate = json.loads(gate_output.getvalue())
        self.assertTrue(gate["source_stop_permitted"])
        self.assertEqual(gate["required_target_posture"], "stopped")

        routed = supervision_log.events(directory / "events.jsonl")
        routed[0]["authority_source_class"] = "supervisor-steer"
        rejected = supervision_log.reduce_control_posture(
            directory=directory,
            policy=policy,
            owner_events=routed,
        )
        self.assertEqual(rejected["required_target_posture"], "in-progress")
        self.assertIn(
            "direct-stop-authority-missing-or-invalid",
            {item["kind"] for item in rejected["issues"]},
        )

    def test_public_writers_produce_an_exact_current_direct_stop(self) -> None:
        self.create_target(self.owner, self.owner_mission)
        self.record_public_stop_decision("decision-ready")
        self.record_public_stop_decision("user-responded")
        self.record_public_stop_decision("resolved", outcome="user-supplied")
        self.record_public_stop_decision("handoff-sent", outcome="user-supplied")
        acknowledged = self.record_public_stop_decision(
            "target-acknowledged", outcome="user-supplied"
        )["record"]
        lifecycle_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "record",
                "--target-thread",
                self.owner,
                "--kind",
                "lifecycle",
                "--status",
                "stopped",
                "--state-fingerprint",
                "state-stop-1234",
                "--evidence",
                str(acknowledged["record_id"]),
                "--summary",
                "Recorded the exact governing direct stop.",
            ]
        )
        lifecycle_output = io.StringIO()
        with redirect_stdout(lifecycle_output):
            lifecycle_args.func(lifecycle_args)

        gate_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "control-posture-gate",
                "--target-thread",
                self.owner,
            ]
        )
        gate_output = io.StringIO()
        with redirect_stdout(gate_output):
            gate_args.func(gate_args)
        result = json.loads(gate_output.getvalue())

        self.assertEqual(result["required_target_posture"], "stopped")
        self.assertEqual(
            result["direct_stop_candidates"][0]["decision_record_id"],
            acknowledged["record_id"],
        )

    def test_direct_stop_rejects_missing_or_mismatched_currentness(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        decision = {
            "record_id": "EVT-000001",
            "kind": "decision",
            "decision_id": "DEC-STOP-1234",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "user-supplied",
            "safe_frontier": "empty",
            "state_fingerprint": "old-state-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "direct-user",
            "authority_source_record": "item-stop-1234",
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }
        self.append(directory, decision)
        self.append(
            directory,
            {
                "record_id": "EVT-000002",
                "kind": "lifecycle",
                "status": "stopped",
                "state_fingerprint": "",
                "evidence": ["EVT-000001"],
            },
        )

        missing = self.reduce(directory, policy)
        self.assertEqual(missing["required_target_posture"], "in-progress")
        records = supervision_log.events(directory / "events.jsonl")
        records[-1]["state_fingerprint"] = "new-state-1234"
        mismatched = supervision_log.reduce_control_posture(
            directory=directory,
            policy=policy,
            owner_events=records,
        )
        self.assertEqual(mismatched["required_target_posture"], "in-progress")

    def test_direct_stop_controls_a_separate_wait_posture(self) -> None:
        directory, policy = self.create_target(self.owner, self.owner_mission)
        stop_decision = {
            "record_id": "EVT-000001",
            "kind": "decision",
            "decision_id": "DEC-STOP-1234",
            "phase": "target-acknowledged",
            "classification": "reserved-authority",
            "outcome": "user-supplied",
            "safe_frontier": "empty",
            "state_fingerprint": "state-stop-1234",
            "mission_root": self.owner_mission,
            "authority_source_class": "direct-user",
            "authority_source_record": "item-stop-1234",
            "impact_class": "goal-blocking",
            "ordinary_means_disabled": True,
            "independent_mission_review": True,
        }
        blocking_decision = {
            **stop_decision,
            "record_id": "EVT-000002",
            "decision_id": "DEC-WAIT-1234",
            "outcome": "safe-deferred",
        }
        lifecycle = {
            "record_id": "EVT-000003",
            "kind": "lifecycle",
            "status": "stopped",
            "state_fingerprint": "state-stop-1234",
            "evidence": ["EVT-000001"],
        }
        for record in (stop_decision, blocking_decision, lifecycle):
            self.append(directory, record)

        result = self.reduce(directory, policy)

        self.assertEqual(result["required_target_posture"], "stopped")
        self.assertEqual(result["blocking_decision_records"], ["EVT-000002"])

    def test_contracts_route_terminal_posture_through_one_reducer(self) -> None:
        supervision_skill = HELPER_PATH.parent.parent.joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        implementation_skill = HELPER_PATH.parent.parent.parent.joinpath(
            "implement-tracker-blocks", "SKILL.md"
        ).read_text(encoding="utf-8")
        policy = HELPER_PATH.parent.parent.joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")

        for text in (supervision_skill, implementation_skill, policy):
            normalized = " ".join(text.split())
            self.assertIn("control-posture-gate", normalized)
            self.assertIn("sole required target posture", normalized)
        self.assertIn("at most eight", policy)
        self.assertIn("event-head hash", policy)
        self.assertIn("never scans the supervision root", policy)
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
                "load_control_snapshot",
                return_value=(
                    Path("/tmp/test-supervision"),
                    {"policy_sha256": "test-policy"},
                    None,
                    event_records,
                    None,
                    None,
                ),
            ),
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
            supervision_log.atomic_json(directory / "policy.json", policy)
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
                    supervision_log,
                    "load_policy",
                    return_value=(directory, policy),
                ),
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

    def critical_incident_head(
        self,
        *,
        record_id: str = "EVT-CRITICAL-HEAD-1234",
        incident_id: str = "INC-CRITICAL-1234",
        failure_mode_id: str = "FM-CRITICAL-1234",
        status: str = "under-review",
        action: str = "Observe the next natural boundary and evaluate effectiveness.",
        resolution_owner: str = "supervisor",
        user_action_required: str = "no",
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "schema_version": 1,
            "record_id": record_id,
            "timestamp": supervision_log.utc_now(),
            "target_thread_id": "target-1234",
            "kind": "incident",
            "incident_id": incident_id,
            "status": status,
            "severity": "critical",
            "notice_disposition": "intermediate",
            "resolution_owner": resolution_owner,
            "user_action_required": user_action_required,
            "action": action,
            "failure_mode": {
                "failure_mode_id": failure_mode_id,
                "layer": "control-plane",
                "mechanism": "A route preceded durable incident ownership.",
                "trigger": "A critical correction was ready to send.",
                "effect": "The correction had no durable recurrence owner.",
                "detection": "Require the current incident head before routing.",
                "correction": "Record or exact-deduplicate the incident first.",
                "recurrence_invariant": "Record first, then route.",
                "human_scheduling_leak": False,
            },
            "policy_sha256": self.policy()["policy_sha256"],
            "previous_record_sha256": None,
        }
        record["record_sha256"] = supervision_log.digest(record)
        return record

    def critical_route(
        self,
        all_events: list[dict[str, object]],
        *,
        source_record: str = "EVT-CRITICAL-HEAD-1234",
        incident_id: str | None = "INC-CRITICAL-1234",
        failure_mode_id: str | None = "FM-CRITICAL-1234",
    ) -> dict[str, object]:
        args = argparse.Namespace(
            target_thread="target-1234",
            recipient_thread="target-1234",
            purpose="target-action",
            source_record=source_record,
            action="Apply the exact critical correction.",
            severity="critical",
            incident_id=incident_id,
            failure_mode_id=failure_mode_id,
            containment=False,
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/supervision-test"), self.policy()),
            ),
            mock.patch.object(
                supervision_log, "events", return_value=all_events
            ),
            mock.patch.object(supervision_log, "validate_event_ledger_anchor"),
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

    def test_critical_route_requires_an_existing_incident_head(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "pre-existing canonical incident head",
        ):
            self.critical_route([])

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "exact canonical incident ID",
        ):
            self.critical_route([], incident_id=None)

    def test_critical_route_rejects_stale_and_mismatched_incident_state(self) -> None:
        first = self.critical_incident_head(record_id="EVT-CRITICAL-OLD-1234")
        current = self.critical_incident_head()
        current["previous_record_sha256"] = first["record_sha256"]
        current["record_sha256"] = supervision_log.digest(
            {key: value for key, value in current.items() if key != "record_sha256"}
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not the current canonical incident head",
        ):
            self.critical_route(
                [first, current], source_record="EVT-CRITICAL-OLD-1234"
            )

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "failure mode does not match",
        ):
            self.critical_route([current], failure_mode_id="FM-DIFFERENT-1234")

    def test_critical_route_rejects_terminal_and_triggerless_heads(self) -> None:
        terminal = self.critical_incident_head(status="closed")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "terminal or closed",
        ):
            self.critical_route([terminal])

        triggerless = self.critical_incident_head(action="")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "next effectiveness trigger",
        ):
            self.critical_route([triggerless])

    def test_critical_route_rejects_non_autonomous_ownership(self) -> None:
        user_owned = self.critical_incident_head(
            resolution_owner="user", user_action_required="yes"
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "autonomous resolution owner",
        ):
            self.critical_route([user_owned])

    def test_exact_open_or_deduplicated_incident_head_allows_critical_route(self) -> None:
        head = self.critical_incident_head()

        result = self.critical_route([head])
        repeated = self.critical_route([head])

        self.assertTrue(result["send_allowed"])
        incident = result["critical_incident_head"]
        self.assertEqual(incident["incident_id"], "INC-CRITICAL-1234")
        self.assertEqual(
            incident["incident_head_record_id"], "EVT-CRITICAL-HEAD-1234"
        )
        self.assertEqual(incident["resolution_owner"], "supervisor")
        self.assertEqual(incident["user_action_required"], "no")
        self.assertRegex(
            incident["incident_currentness_root_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertEqual(
            repeated["critical_incident_head"][
                "incident_currentness_root_sha256"
            ],
            incident["incident_currentness_root_sha256"],
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
            "(/Users/example/.codex/releases/current/implement-tracker-blocks/SKILL.md)\n "
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
            mock.patch.object(
                supervision_log,
                "policy_owner_lock",
                return_value=nullcontext((-1, (1, 1, 1, 1))),
            ),
            mock.patch.object(
                supervision_log,
                "read_json_snapshot",
                return_value=(policy, (1, 1, 1, 1)),
            ),
            mock.patch.object(
                supervision_log, "validate_range_policy_history_at"
            ),
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
            mock.patch.object(
                supervision_log,
                "policy_owner_lock",
                return_value=nullcontext((-1, (1, 1, 1, 1))),
            ),
            mock.patch.object(
                supervision_log,
                "read_json_snapshot",
                return_value=(policy, (1, 1, 1, 1)),
            ),
            mock.patch.object(
                supervision_log, "validate_range_policy_history_at"
            ),
            mock.patch.object(
                supervision_log,
                "events_snapshot",
                return_value=([open_decision], (1, 1, 1, 1)),
            ),
            mock.patch.object(
                supervision_log, "validate_event_ledger_anchor_at"
            ),
            mock.patch.object(
                supervision_log,
                "mission_scoped_events",
                return_value=[open_decision],
            ),
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

    def test_cmd_record_rejects_stale_policy_after_winning_mutation(self) -> None:
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
            stale_policy = supervision_log.read_json(directory / "policy.json")
            record = supervision_log.parser().parse_args(
                [
                    "--root",
                    temporary,
                    "record",
                    "--target-thread",
                    self.target,
                    "--kind",
                    "check",
                    "--model",
                    "gpt-5.6-sol",
                    "--reasoning",
                    "xhigh",
                    "--status",
                    "no-intervention",
                    "--state-fingerprint",
                    "stale-record-fingerprint",
                    "--summary",
                    "This stale record must not enter the canonical ledger.",
                ]
            )
            record_waiting = threading.Event()
            winner_finished = threading.Event()
            outcome: dict[str, object] = {}
            real_append_lock = supervision_log.append_lock

            @contextmanager
            def delayed_record_lock(path: Path):
                record_waiting.set()
                if not winner_finished.wait(timeout=5):
                    raise AssertionError("Winning policy mutation did not finish")
                with real_append_lock(path):
                    yield

            def run_stale_record() -> None:
                try:
                    with redirect_stdout(io.StringIO()):
                        supervision_log.cmd_record(record)
                except Exception as exc:  # noqa: BLE001 - captured for thread assertion
                    outcome["error"] = exc

            with mock.patch.object(
                supervision_log, "append_lock", delayed_record_lock
            ):
                thread = threading.Thread(target=run_stale_record)
                thread.start()
                try:
                    self.assertTrue(record_waiting.wait(timeout=5))
                    winning_policy = supervision_log.read_json(
                        directory / "policy.json"
                    )
                    supervision_log.write_policy_version(
                        directory,
                        winning_policy,
                        kind="policy-test",
                        reason="Winning mutation advances the canonical policy.",
                        evidence_values=["test-winning-policy"],
                    )
                finally:
                    winner_finished.set()
                    thread.join(timeout=5)

            self.assertFalse(thread.is_alive())
            self.assertIsInstance(
                outcome.get("error"), supervision_log.SupervisionLogError
            )
            self.assertRegex(str(outcome["error"]), "changed concurrently")
            current_policy = supervision_log.read_json(directory / "policy.json")
            self.assertNotEqual(
                current_policy["policy_sha256"], stale_policy["policy_sha256"]
            )
            self.assertEqual(
                supervision_log.events(directory / "events.jsonl"), []
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
                self.assertFalse(lifecycle["source_stop_permitted"])
                self.assertEqual(
                    lifecycle["required_target_posture"], "in-progress"
                )
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
        self.assertFalse(lifecycle["source_stop_permitted"])
        self.assertEqual(lifecycle["required_target_posture"], "in-progress")
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


class WatcherAvailabilityContractTests(unittest.TestCase):
    target = "target-watcher-1234"
    state = "state-watcher-1234"
    trigger = "compact-thread-read-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = "Supervise the complete tracker outcome."
        init = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "init",
                "--target-thread",
                self.target,
                "--target-label",
                "Watcher availability target",
                "--watcher-thread",
                "watcher-thread-1234",
                "--reviewer-thread",
                "reviewer-thread-1234",
                "--base-reviewer-thread",
                "base-reviewer-thread-1234",
                "--fix-executor-thread",
                "fix-executor-thread-1234",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "item-watcher-1234",
                "--mission-source-sha256",
                hashlib.sha256(request.encode("utf-8")).hexdigest(),
            ]
        )
        with redirect_stdout(io.StringIO()):
            init.func(init)
        self.directory = self.root / self.target

    def invoke(self, read_status: str, *extra: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "watcher-availability",
                "--target-thread",
                self.target,
                "--read-status",
                read_status,
                "--state-fingerprint",
                self.state,
                "--now",
                "2026-08-12T12:00:00+00:00",
                *extra,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_watcher_availability(args)
        return json.loads(output.getvalue())

    def unavailable(self, trigger: str | None = None) -> dict[str, object]:
        return self.invoke(
            "unavailable",
            "--read-trigger",
            trigger or self.trigger,
        )

    def concurrent_cli(self, arguments: list[str]) -> list[dict[str, object]]:
        command = [
            sys.executable,
            str(HELPER_PATH),
            "--root",
            str(self.root),
            "watcher-availability",
            "--target-thread",
            self.target,
            "--state-fingerprint",
            self.state,
            "--now",
            "2026-08-12T12:00:00+00:00",
            *arguments,
        ]
        processes = [
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        result: list[dict[str, object]] = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            result.append(json.loads(stdout))
        return result

    def open_incident(self) -> str:
        first = self.unavailable()
        second = self.unavailable("compact-thread-read-retry-2-1234")
        third = self.unavailable("compact-thread-read-retry-3-1234")
        self.assertEqual(first["next_action"], "retry-compact-read")
        self.assertEqual(second["next_action"], "retry-compact-read")
        self.assertTrue(third["route_required"])
        return str(third["record"]["incident_id"])

    def test_threshold_opens_one_incident_and_identical_retries_are_silent(self) -> None:
        incident_id = self.open_incident()
        before = supervision_log.events(self.directory / "events.jsonl")

        duplicate = self.unavailable("compact-thread-read-retry-3-1234")
        after = supervision_log.events(self.directory / "events.jsonl")

        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(duplicate["record_required"])
        self.assertFalse(duplicate["route_required"])
        self.assertEqual(duplicate["incident_id"], incident_id)
        self.assertEqual(len(before), len(after))
        incidents = [
            item
            for item in after
            if item.get("category")
            == supervision_log.WATCHER_AVAILABILITY_INCIDENT_CATEGORY
            and item.get("kind") == "incident"
        ]
        self.assertEqual(len(incidents), 1)

    def test_changed_trigger_records_new_retry_under_the_same_incident(self) -> None:
        incident_id = self.open_incident()

        changed = self.unavailable("compact-thread-read-after-route-1234")

        self.assertFalse(changed["duplicate"])
        self.assertTrue(changed["route_required"])
        self.assertEqual(changed["record"]["incident_id"], incident_id)
        head = supervision_log.watcher_availability_incident_head(
            supervision_log.events(self.directory / "events.jsonl")
        )
        self.assertIsNotNone(head)
        assert head is not None
        self.assertEqual(head["incident_id"], incident_id)

    def test_three_changed_triggers_share_one_target_state_threshold(self) -> None:
        first = self.unavailable("compact-trigger-a-1234")
        second = self.unavailable("compact-trigger-b-1234")
        third = self.unavailable("compact-trigger-c-1234")

        self.assertFalse(first["route_required"])
        self.assertFalse(second["route_required"])
        self.assertTrue(third["route_required"])
        self.assertEqual(third["record"]["watcher_unavailable_read_count"], 3)
        self.assertEqual(
            len(
                {
                    first["record"]["watcher_availability_state_fingerprint"],
                    second["record"]["watcher_availability_state_fingerprint"],
                    third["record"]["watcher_availability_state_fingerprint"],
                }
            ),
            1,
        )
        self.assertEqual(
            len(
                {
                    first["record"]["watcher_availability_attempt_fingerprint"],
                    second["record"]["watcher_availability_attempt_fingerprint"],
                    third["record"]["watcher_availability_attempt_fingerprint"],
                }
            ),
            3,
        )

    def test_concurrent_threshold_and_verified_recovery_append_once(self) -> None:
        self.unavailable("compact-concurrent-trigger-a-1234")
        self.unavailable("compact-concurrent-trigger-b-1234")
        threshold_results = self.concurrent_cli(
            [
                "--read-status",
                "unavailable",
                "--read-trigger",
                "compact-concurrent-trigger-c-1234",
            ]
        )
        self.assertEqual(
            sorted(bool(item["duplicate"]) for item in threshold_results),
            [False, True],
        )
        incident_records = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind") == "incident"
            and item.get("category")
            == supervision_log.WATCHER_AVAILABILITY_INCIDENT_CATEGORY
        ]
        self.assertEqual(len(incident_records), 1)
        incident_id = str(incident_records[0]["incident_id"])

        verified_results = self.concurrent_cli(
            [
                "--read-status",
                "available-verified",
                "--incident-id",
                incident_id,
                "--read-source-record",
                "concurrent-read-before-1234",
                "--verification-source-record",
                "concurrent-read-after-1234",
                "--observed-state-fingerprint",
                "concurrent-observed-state-1234",
                "--verification-state-fingerprint",
                "concurrent-verified-state-1234",
                "--observed-thread-status",
                "active",
                "--verification-thread-status",
                "active",
            ]
        )
        self.assertEqual(
            sorted(bool(item["duplicate"]) for item in verified_results),
            [False, True],
        )
        verified_records = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("category") == supervision_log.WATCHER_VERIFIED_CATEGORY
        ]
        self.assertEqual(len(verified_records), 1)

    def test_verified_read_requires_distinct_next_state_and_routes_review(self) -> None:
        incident_id = self.open_incident()
        common = [
            "--incident-id",
            incident_id,
            "--observed-state-fingerprint",
            "observed-state-1234",
            "--verification-state-fingerprint",
            "verified-state-1234",
            "--observed-thread-status",
            "active",
            "--verification-thread-status",
            "active",
        ]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "distinct next-state"
        ):
            self.invoke(
                "available-verified",
                *common,
                "--read-source-record",
                "thread-read-1234",
                "--verification-source-record",
                "thread-read-1234",
            )

        result = self.invoke(
            "available-verified",
            *common,
            "--read-source-record",
            "thread-read-before-1234",
            "--verification-source-record",
            "thread-read-after-1234",
        )
        duplicate = self.invoke(
            "available-verified",
            *common,
            "--read-source-record",
            "thread-read-before-1234",
            "--verification-source-record",
            "thread-read-after-1234",
        )

        self.assertTrue(result["review_required"])
        self.assertEqual(result["next_action"], "route-effectiveness-review")
        self.assertEqual(
            result["route_recipient_thread_id"], "reviewer-thread-1234"
        )
        self.assertTrue(result["record"]["next_state_verified"])
        self.assertTrue(duplicate["duplicate"])
        self.assertIsNotNone(
            supervision_log.watcher_availability_incident_head(
                supervision_log.events(self.directory / "events.jsonl")
            )
        )

        recurrence = self.unavailable("compact-thread-read-retry-3-1234")
        repeated_recurrence = self.unavailable(
            "compact-thread-read-retry-3-1234"
        )
        self.assertFalse(recurrence["duplicate"])
        self.assertTrue(recurrence["route_required"])
        self.assertEqual(recurrence["record"]["incident_id"], incident_id)
        self.assertEqual(recurrence["record"]["status"], "recurrence-current")
        self.assertTrue(repeated_recurrence["duplicate"])

    def test_verified_read_rejects_unknown_or_closed_incident(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "one current availability incident"
        ):
            self.invoke(
                "available-verified",
                "--incident-id",
                "INC-WATCHER-UNKNOWN-1234",
                "--read-source-record",
                "thread-read-before-1234",
                "--verification-source-record",
                "thread-read-after-1234",
                "--observed-state-fingerprint",
                "observed-state-1234",
                "--verification-state-fingerprint",
                "verified-state-1234",
                "--observed-thread-status",
                "active",
                "--verification-thread-status",
                "active",
            )

    def test_watcher_availability_contract_is_documented(self) -> None:
        skill = Path(supervision_log.__file__).parents[1].joinpath("SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = Path(supervision_log.__file__).parents[1].joinpath(
            "references", "supervision-policy.md"
        ).read_text(encoding="utf-8")
        for text in (skill, policy):
            self.assertIn("watcher-availability", text)
            self.assertIn("three consecutive", text)
            self.assertIn("distinct next-state verification", text)
            self.assertIn("suppress identical", text)


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
            "capability_reconciliation_base64": None,
            "active_block": "Block-64",
            "checkpoint": "checkpoint-1234",
            "summary": "Current operator-visible outcome verified.",
            "evidence": ["source-1234"],
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def reconciliation_base64(self) -> str:
        return base64.b64encode(self.reconciliation_path.read_bytes()).decode("ascii")

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
                    supervision_log,
                    "load_policy_directory_snapshot",
                    return_value=(directory, policy, None, None),
                ),
                redirect_stdout(output),
            ):
                supervision_log.cmd_record(lifecycle_args)
            lifecycle = json.loads(output.getvalue())["record"]
            self.assertEqual(
                lifecycle["outcome_completion_record_id"], record["record_id"]
            )

    def test_file_and_base64_inputs_produce_identical_root_and_record(self) -> None:
        policy = self.policy()

        def completion_record(args: argparse.Namespace) -> dict[str, object]:
            with tempfile.TemporaryDirectory() as temporary:
                output = io.StringIO()
                with (
                    mock.patch.object(
                        supervision_log,
                        "load_policy",
                        return_value=(Path(temporary), policy),
                    ),
                    mock.patch.object(
                        supervision_log,
                        "utc_now",
                        return_value="2026-08-11T07:34:22+00:00",
                    ),
                    redirect_stdout(output),
                ):
                    supervision_log.cmd_completion_record(args)
                return json.loads(output.getvalue())["record"]

        file_record = completion_record(self.completion_args())
        encoded = self.reconciliation_base64()
        base64_record = completion_record(
            self.completion_args(
                capability_reconciliation_json=None,
                capability_reconciliation_base64=encoded,
            )
        )

        self.assertEqual(file_record, base64_record)
        reconciliation = json.loads(self.reconciliation_path.read_text(encoding="utf-8"))
        self.assertEqual(
            file_record["capability_reconciliation_sha256"],
            supervision_log.digest(reconciliation),
        )
        serialized = json.dumps(base64_record, sort_keys=True)
        self.assertNotIn("requested_capability", serialized)
        self.assertNotIn(str(self.reconciliation_path), serialized)
        self.assertNotIn(encoded, serialized)

    def test_legacy_file_input_remains_explicit_and_uses_shared_validation(self) -> None:
        policy = self.policy()
        expected = supervision_log.load_capability_reconciliation(
            str(self.reconciliation_path),
            target_thread="target-1234",
            mission_root=self.mission_root,
            state_fingerprint="state-1234",
            current_revision="2" * 40,
            policy=policy,
        )
        actual = supervision_log.load_capability_reconciliation_input(
            str(self.reconciliation_path),
            None,
            target_thread="target-1234",
            mission_root=self.mission_root,
            state_fingerprint="state-1234",
            current_revision="2" * 40,
            policy=policy,
        )
        self.assertEqual(actual, expected)

        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "not an explicit file"
        ):
            supervision_log.load_capability_reconciliation(
                str(self.reconciliation_path.parent),
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )

    def test_completion_record_requires_exactly_one_reconciliation_input(self) -> None:
        policy = self.policy()
        encoded = self.reconciliation_base64()
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path(temporary), policy),
            ):
                for path_value, base64_value in (
                    (None, None),
                    (str(self.reconciliation_path), encoded),
                ):
                    with self.subTest(
                        path=path_value,
                        base64=base64_value is not None,
                    ):
                        with self.assertRaisesRegex(
                            supervision_log.SupervisionLogError,
                            "requires exactly one",
                        ):
                            supervision_log.cmd_completion_record(
                                self.completion_args(
                                    capability_reconciliation_json=path_value,
                                    capability_reconciliation_base64=base64_value,
                                )
                            )

    def test_base64_input_rejects_invalid_and_noncanonical_text(self) -> None:
        policy = self.policy()
        invalid_values = ("%%%", self.reconciliation_base64() + "=")
        for value in invalid_values:
            with self.subTest(value=value[-8:]):
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "not valid canonical base64",
                ):
                    supervision_log.load_capability_reconciliation_base64(
                        value,
                        target_thread="target-1234",
                        mission_root=self.mission_root,
                        state_fingerprint="state-1234",
                        current_revision="2" * 40,
                        policy=policy,
                    )

    def test_oversized_base64_reconciliation_rejects_before_json_parsing(self) -> None:
        encoded = base64.b64encode(
            b"x" * (supervision_log.MAX_CAPABILITY_RECONCILIATION_BYTES + 1)
        ).decode("ascii")
        policy = self.policy()
        with (
            mock.patch.object(supervision_log.json, "loads") as loads,
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "exceeds its byte bound"
            ),
        ):
            supervision_log.load_capability_reconciliation_base64(
                encoded,
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )
        loads.assert_not_called()

    def test_base64_input_rejects_malformed_json(self) -> None:
        encoded = base64.b64encode(b"{").decode("ascii")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "not valid JSON"
        ):
            supervision_log.load_capability_reconciliation_base64(
                encoded,
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=self.policy(),
            )

    def test_base64_input_reuses_schema_evidence_and_currentness_failures(self) -> None:
        policy = self.policy()

        self.write_reconciliation(unexpected="field")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "unexpected or missing fields"
        ):
            supervision_log.load_capability_reconciliation_base64(
                self.reconciliation_base64(),
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )

        self.write_reconciliation(state_fingerprint="state-old")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "stale state fingerprint"
        ):
            supervision_log.load_capability_reconciliation_base64(
                self.reconciliation_base64(),
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )

        self.write_reconciliation()
        process_only = json.loads(self.reconciliation_path.read_text(encoding="utf-8"))
        process_only["evidence"][2]["evidence_class"] = "validation"
        self.reconciliation_path.write_text(
            json.dumps(process_only, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "required evidence class"
        ):
            supervision_log.load_capability_reconciliation_base64(
                self.reconciliation_base64(),
                target_thread="target-1234",
                mission_root=self.mission_root,
                state_fingerprint="state-1234",
                current_revision="2" * 40,
                policy=policy,
            )

    def test_completion_record_rejects_wrong_mission_or_missing_hash(self) -> None:
        policy = self.policy()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(directory, policy),
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
                supervision_log,
                "load_policy_directory_snapshot",
                return_value=(directory, policy, None, None),
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
                "load_control_snapshot",
                return_value=(
                    Path("/tmp/supervision-test"),
                    policy,
                    None,
                    [*event_records, source],
                    None,
                    None,
                ),
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
                "project_key": "target",
                "subject": "Codex Tracker Supervision - target",
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
                "project_key": "target",
                "subject": "Codex Tracker Supervision - target",
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
        state_fingerprint: str = "state-1234",
        mission_root: str | None = None,
        authority_source_class: str = "tracker",
        authority_source_record: str = "TRACKER-BOUNDARY-1234",
        impact_class: str = "material",
        affected_width: str = "decision-subject",
        duration: str = "decision-lifecycle",
        reversibility: str = "conditional",
        ordinary_means_disabled: str = "no",
        independent_mission_review: str = "no",
        prior_record: str = "",
        disposition_reason: str = "",
        correction_authority_source_class: str = "",
        correction_authority_source_record: str = "",
        correction_authority_source_sha256: str = "",
        governing_outcome_effect: str = "",
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
                state_fingerprint,
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
                *(
                    ["--prior-record", prior_record]
                    if prior_record
                    else []
                ),
                *(
                    ["--disposition-reason", disposition_reason]
                    if disposition_reason
                    else []
                ),
                *(
                    [
                        "--correction-authority-source-class",
                        correction_authority_source_class,
                    ]
                    if correction_authority_source_class
                    else []
                ),
                *(
                    [
                        "--correction-authority-source-record",
                        correction_authority_source_record,
                    ]
                    if correction_authority_source_record
                    else []
                ),
                *(
                    [
                        "--correction-authority-source-sha256",
                        correction_authority_source_sha256,
                    ]
                    if correction_authority_source_sha256
                    else []
                ),
                *(
                    ["--governing-outcome-effect", governing_outcome_effect]
                    if governing_outcome_effect
                    else []
                ),
                "--now",
                now,
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(directory, policy),
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
                supervision_log,
                "load_control_snapshot",
                return_value=(
                    directory,
                    policy,
                    None,
                    supervision_log.events(directory / "events.jsonl"),
                    None,
                    None,
                ),
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

    def use_lower_input_mode(self, policy: dict[str, object]) -> None:
        policy["adaptive_decision_control"] = (
            supervision_log.adaptive_decision_control_contract("recommend")
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )

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
            self.use_lower_input_mode(policy)
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

    def test_full_autonomous_unresolved_attempt_never_opens_human_window(self) -> None:
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
            gated = self.gate(directory, policy, "2026-08-01T12:20:00+00:00")
            self.assertEqual(unresolved["human_input_requested_at"], "")
            self.assertEqual(unresolved["user_deadline_at"], "")
            self.assertFalse(gated["notification_send_now"])
            self.assertFalse(gated["human_input_eligible"])
            self.assertEqual(gated["adaptive_decision_mode"], "full-autonomous")

    def test_first_unresolved_attempt_requests_input_and_starts_next_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.use_lower_input_mode(policy)
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
            self.use_lower_input_mode(policy)
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
                        "requires all maintained attempts",
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
            self.use_lower_input_mode(policy)
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

    def test_current_direct_correction_retires_exact_safe_deferral(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            policy["direct_authority_receipts"] = [
                {
                    "source_class": "direct-user",
                    "source_record": "DIRECT-CORRECTION-1234",
                    "source_sha256": self.hash_c,
                    "accepted": True,
                }
            ]
            common = {
                "classification": "missing-fact",
                "safe_frontier": "empty",
                "authority_source_class": "tracker",
                "authority_source_record": "TRACKER-MISSION-1234",
            }
            self.record(directory, policy, phase="decision-ready", **common)
            for attempt in (1, 2, 3):
                self.record(
                    directory,
                    policy,
                    phase="attempt-started",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:00:00+00:00",
                    **common,
                )
                self.record(
                    directory,
                    policy,
                    phase="attempt-unresolved",
                    attempt=attempt,
                    now=f"2026-08-01T1{attempt + 1}:20:00+00:00",
                    **common,
                )
            self.record(
                directory,
                policy,
                phase="safe-deferred",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:01+00:00",
                **common,
            )
            self.record(
                directory,
                policy,
                phase="handoff-sent",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:02+00:00",
                **common,
            )
            acknowledged = self.record(
                directory,
                policy,
                phase="target-acknowledged",
                attempt=3,
                outcome="safe-deferred",
                now="2026-08-01T14:20:03+00:00",
                **common,
            )["record"]
            before = self.gate(directory, policy, "2026-08-01T14:20:04+00:00")
            self.assertTrue(before["blocking_permitted"])

            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "exact current prior record",
            ):
                self.record(
                    directory,
                    policy,
                    phase="corrected",
                    attempt=3,
                    outcome="safe-deferred",
                    prior_record="EVT-WRONG-1234",
                    disposition_reason="Later canonical evidence resolved the premise.",
                    correction_authority_source_class="direct-user",
                    correction_authority_source_record="DIRECT-CORRECTION-1234",
                    correction_authority_source_sha256=self.hash_c,
                    governing_outcome_effect="continue-governing-outcome",
                    now="2026-08-01T14:20:05+00:00",
                    **common,
                )

            corrected = self.record(
                directory,
                policy,
                phase="corrected",
                attempt=3,
                outcome="safe-deferred",
                prior_record=str(acknowledged["record_id"]),
                disposition_reason="Later canonical evidence resolved the premise.",
                correction_authority_source_class="direct-user",
                correction_authority_source_record="DIRECT-CORRECTION-1234",
                correction_authority_source_sha256=self.hash_c,
                governing_outcome_effect="continue-governing-outcome",
                now="2026-08-01T14:20:06+00:00",
                **common,
            )["record"]
            after = self.gate(directory, policy, "2026-08-01T14:20:07+00:00")

            self.assertEqual(corrected["phase"], "corrected")
            self.assertFalse(after["blocking_permitted"])
            self.assertFalse(after["local_blocking_permitted"])
            self.assertEqual(after["required_target_posture"], "in-progress")
            self.assertEqual(
                after["action"],
                "continue-governing-outcome-after-decision-correction",
            )
            self.assertEqual(
                after["control_posture"]["reconciled_decisions"][0][
                    "reconciliation_posture"
                ],
                "recorded",
            )

    def test_decision_transition_rejects_changed_frozen_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            policy = supervision_log.default_policy(self.init_args())
            self.record(
                directory,
                policy,
                classification="missing-fact",
                phase="decision-ready",
                safe_frontier="empty",
                state_fingerprint="state-ready-1234",
            )

            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "frozen decision identity",
            ):
                self.record(
                    directory,
                    policy,
                    classification="missing-fact",
                    phase="attempt-started",
                    safe_frontier="empty",
                    attempt=1,
                    state_fingerprint="state-later-1234",
                )

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
        self.assertIn("unbound `codex_delegation`", supervision_policy)
        self.assertIn("helper-validated delegation envelope", supervision_policy)
        self.assertIn("without a same-thread repetition", supervision_policy)
        self.assertIn("no inferred carry-forward across a Block", implementation_skill)
        self.assertIn("predecessor for proof, not every successor revision", implementation_skill)
        self.assertIn("constrains exact X rather than a later operation", implementation_skill)
        self.assertIn("never substitute for the requested substantive", implementation_skill)
        self.assertIn("tracker-level mission frame", author_skill)
        self.assertIn("### Mission frame", tracker_template)
        self.assertIn("`carry-forward: false`", tracker_template)


if __name__ == "__main__":
    unittest.main()
