#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import factory_evolution
import supervision_log
import test_factory_evolution as evolution_test_support
import test_factory_evolution_admission as admission_test_support


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIRECTORY.parent.parent
TRACKER_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
)


class FactoryEvolutionOwnerRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.support = evolution_test_support.EvolutionReviewTests(
            "test_review_can_identify_a_broad_capability_gap"
        )
        self.support.setUp()
        self.addCleanup(self.support.tearDown)
        self.target_revision = "a" * 40
        self.context = {
            "evolution_id": "evolution-orchestration-1234",
            "target_repository_root": "/tmp/factory-target",
            "target_revision": self.target_revision,
            "mission_root": "1" * 64,
            "policy_sha256": "2" * 64,
            "range_id": "full-tracker-1234",
            "range_history_head_sha256": "3" * 64,
            "tracker_sha256": "4" * 64,
            "capability_frame_root": "5" * 64,
            "skill_source_roots": {
                "author-implementation-trackers": "6" * 40,
                "implement-tracker-blocks": "7" * 40,
                "supervise-tracker-runs": "8" * 40,
            },
            "candidate_budget": {
                "max_files": 3,
                "max_changed_lines": 200,
                "max_commands": 6,
                "max_elapsed_minutes": 20,
                "max_active_lanes_per_decision": 1,
                "max_active_lanes_per_target": 1,
                "max_mapped_comparisons": 1,
                "max_review_passes": 1,
                "independent_review_required": True,
                "stop_on_protected_regression": True,
                "stop_on_resource_exhaustion": True,
            },
        }

    def review_for(self, candidate_type: str) -> dict[str, object]:
        submission = copy.deepcopy(self.support.review_submission())
        selected_id = str(submission["selection"]["candidate_id"])
        owner = factory_evolution.candidate_owner_route(candidate_type)
        selected = next(
            item for item in submission["candidates"] if item["candidate_id"] == selected_id
        )
        selected["candidate_type"] = candidate_type
        selected["implementation_owner"] = owner
        selected["evaluation_owner"] = "independent-evaluator-1234"
        submission["reviewer_id"] = "cognitive-reviewer-1234"
        submission["experiment"]["proposer_id"] = "cognitive-reviewer-1234"
        submission["experiment"]["implementer_id"] = owner
        submission["experiment"]["evaluator_id"] = "independent-evaluator-1234"
        submission["experiment"]["baseline_revision"] = self.target_revision
        submission["experiment"]["candidate_revision"] = "b" * 40
        return factory_evolution.build_evolution_review(
            self.support.packet, submission
        )

    def test_complete_candidate_type_map_routes_once_without_detector_dependency(self) -> None:
        self.assertEqual(
            set(factory_evolution.CANDIDATE_OWNER_ROUTES),
            set(factory_evolution.CANDIDATE_TYPES),
        )
        for candidate_type, owner in sorted(
            factory_evolution.CANDIDATE_OWNER_ROUTES.items()
        ):
            with self.subTest(candidate_type=candidate_type):
                review = self.review_for(candidate_type)
                handoff = factory_evolution.build_candidate_owner_handoff(
                    self.support.packet, review, self.context
                )
                action = factory_evolution.build_cycle_action(
                    self.support.packet, review=review
                )
                self.assertEqual(handoff["normal_owner"], owner)
                self.assertEqual(
                    handoff["owner_action"],
                    "author" if owner == "author-implementation-trackers" else "implement",
                )
                self.assertEqual(action["normal_owner"], owner)

    def test_unknown_type_and_conflicting_owner_claim_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "unsupported"
        ):
            factory_evolution.candidate_owner_route("invented-type")

        review = self.review_for("skill-method")
        review["candidates"] = copy.deepcopy(review["candidates"])
        selected = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == review["selection"]["candidate_id"]
        )
        selected["implementation_owner"] = "supervise-tracker-runs"
        review["experiment"] = copy.deepcopy(review["experiment"])
        review["experiment"]["implementer_id"] = "supervise-tracker-runs"
        review_material = {
            key: value for key, value in review.items() if key not in {"review_id", "review_root"}
        }
        review["review_root"] = factory_evolution.digest(review_material)
        review["review_id"] = "evolution-review-" + review["review_root"][:20]
        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "implementation owner"
        ):
            factory_evolution.build_candidate_owner_handoff(
                self.support.packet, review, self.context
            )

        non_exact = copy.deepcopy(self.support.review_submission())
        non_exact["schema_version"] = True
        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "schema"
        ):
            factory_evolution.build_evolution_review(
                self.support.packet, non_exact
            )

    def test_stale_target_revision_rejects_owner_handoff(self) -> None:
        review = self.review_for("skill-method")
        changed = dict(self.context)
        changed["target_revision"] = "c" * 40
        with self.assertRaisesRegex(
            factory_evolution.FactoryEvolutionError, "baseline revision"
        ):
            factory_evolution.build_candidate_owner_handoff(
                self.support.packet, review, changed
            )


class FactoryEvolutionOrchestrationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admission = admission_test_support.FactoryEvolutionAdmissionTests(
            "test_supported_productive_evidence_is_admitted_once_without_cognition"
        )
        self.admission.setUp()
        self.addCleanup(self.admission.temporary.cleanup)
        self.repository = self.admission.repository
        self.directory = self.admission.directory
        self.target_thread = self.admission.target_thread
        self._install_factory_sources_and_range()
        self.review_support = evolution_test_support.EvolutionReviewTests(
            "test_review_can_identify_a_broad_capability_gap"
        )
        self.review_support.setUp()
        self.addCleanup(self.review_support.tearDown)
        self.packet = self.review_support.packet
        self.evolution_id = "evolution-orchestration-1234"
        self._record_admission()

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["/usr/bin/git", "-C", str(self.repository), *arguments],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()

    def command(self, *arguments: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.admission.supervision_root), *arguments]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def _install_factory_sources_and_range(self) -> None:
        for name in factory_evolution.FACTORY_SKILL_IDS:
            source = self.repository / name
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                f"# {name}\n\nBounded Factory owner fixture.\n", encoding="utf-8"
            )
        tracker = self.repository / "docs" / TRACKER_PATH.name
        tracker.parent.mkdir(parents=True)
        tracker.write_bytes(TRACKER_PATH.read_bytes())
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Factory Test",
            "-c",
            "user.email=factory@example.test",
            "commit",
            "-m",
            "Add Block 13 owner fixtures",
        )
        policy = supervision_log.read_json(self.directory / "policy.json")
        (
            tracker_path,
            tracker_sha,
            structure_sha,
            blocks,
        ) = supervision_log.implementation_tracker_snapshot(str(tracker))
        authority = {
            "source_class": "direct-user",
            "source_record": "direct-user-mission-1234",
            "source_sha256": "a" * 64,
        }
        request = "Implement the full tracker through every remaining Block."
        entry = supervision_log.implementation_range_history_entry(
            sequence=1,
            prior_entry_sha256="",
            operation="bound",
            request_text=request,
            request_bytes=request.encode("utf-8"),
            tracker_sha256=tracker_sha,
            tracker_structure_sha256=structure_sha,
            tracker_path=str(tracker_path),
            tracker_blocks=sorted(blocks),
            range_intent="full-tracker",
            explicit_blocks=[],
            authority=authority,
            authority_policy_version=int(policy["policy_version"]) + 1,
        )
        policy["implementation_range"] = {
            "schema_version": 1,
            "kind": "implementation-range-binding",
            "range_id": "full-tracker-block13-1234",
            "genesis_sha256": supervision_log.digest(
                {
                    "range_id": "full-tracker-block13-1234",
                    "authority": authority,
                    "request_text_sha256": entry["request_text_sha256"],
                    "initial_tracker_sha256": tracker_sha,
                    "initial_tracker_structure_sha256": structure_sha,
                    "initial_tracker_blocks": sorted(blocks),
                    "initial_range_intent": "full-tracker",
                    "initial_explicit_blocks": [],
                }
            ),
            "authority": authority,
            "range_intent": "full-tracker",
            "explicit_blocks": [],
            "tracker_path": str(tracker_path),
            "tracker_sha256": tracker_sha,
            "tracker_structure_sha256": structure_sha,
            "tracker_blocks": sorted(blocks),
            "history": [entry],
            "history_head_sha256": entry["entry_sha256"],
        }
        supervision_log.validate_implementation_range_contract(
            policy["implementation_range"]
        )
        supervision_log.write_policy_version(
            self.directory,
            policy,
            kind="test-block13-range-bind",
            reason="Bind the focused Block 13 orchestration fixture.",
            evidence_values=[tracker_sha, entry["entry_sha256"]],
        )
        self.baseline_revision = self.git("rev-parse", "HEAD")

    def _record_admission(self) -> None:
        module = supervision_log.factory_evolution_module()
        evolution_directory = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        manifest = module.build_evolution_manifest(
            {"learning-packet.json": self.packet}
        )
        supervision_log.write_factory_evolution_set(
            evolution_directory,
            {
                "learning-packet.json": self.packet,
                "prepare-manifest.json": manifest,
            },
        )
        policy = supervision_log.read_json(self.directory / "policy.json")
        mission = supervision_log.bound_mission(policy)
        assert mission is not None
        current = supervision_log.events(self.directory / "events.jsonl")
        record_id = f"EVT-{len(current) + 1:06d}"
        record_hashes = sorted(
            item["record_sha256"] for item in self.packet["evidence"]["events"]
        )
        novelty_key = supervision_log.digest(
            {"record_hashes": record_hashes, "signal": "block13-owner-orchestration"}
        )
        context_root = supervision_log.digest(
            {
                "packet_root": self.packet["packet_root"],
                "target_revision": self.baseline_revision,
                "mission_root": mission["mission_root"],
                "policy_sha256": policy["policy_sha256"],
            }
        )
        result = supervision_log.factory_evolution_admission_result(
            checkpoint_kind="explicit-factory-maintenance",
            eligible=True,
            admission_authorized=True,
            disposition="admitted",
            next_revisit_condition="the admitted packet enters its existing-owner review path",
            packet_root=self.packet["packet_root"],
            novelty_key=novelty_key,
            context_root=context_root,
            evolution_id=self.evolution_id,
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
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target_thread,
                "policy_sha256": policy["policy_sha256"],
                "mission_root": mission["mission_root"],
                "checkpoint_kind": "explicit-factory-maintenance",
                "adaptive_decision_mode": "full-autonomous",
                "disposition": "admitted",
                "canonical_evidence_novelty_key": novelty_key,
                "canonical_record_sha256s": record_hashes,
                "context_root": context_root,
                "packet_root": self.packet["packet_root"],
                "evolution_id": self.evolution_id,
                "target_revision": self.baseline_revision,
                "eligibility_result": result,
                "eligibility_result_root": result["result_root"],
                "human_request_count": 0,
                "model_calls": 0,
                "reviewer_calls": 0,
            },
        )

    def review_submission(self, *, candidate_type: str = "skill-method") -> dict[str, object]:
        submission = copy.deepcopy(self.review_support.review_submission())
        selected_id = str(submission["selection"]["candidate_id"])
        selected = next(
            item for item in submission["candidates"] if item["candidate_id"] == selected_id
        )
        owner = factory_evolution.candidate_owner_route(candidate_type)
        selected["candidate_type"] = candidate_type
        selected["implementation_owner"] = owner
        selected["evaluation_owner"] = "independent-evaluator-1234"
        policy = supervision_log.read_json(self.directory / "policy.json")
        reviewer = policy["runtime"]["base_reviewer_thread_id"]
        submission["packet_id"] = self.packet["packet_id"]
        submission["packet_root"] = self.packet["packet_root"]
        submission["reviewer_id"] = reviewer
        submission["experiment"]["proposer_id"] = reviewer
        submission["experiment"]["implementer_id"] = owner
        submission["experiment"]["evaluator_id"] = "independent-evaluator-1234"
        submission["experiment"]["baseline_revision"] = self.baseline_revision
        submission["experiment"]["candidate_revision"] = "f" * 40
        return submission

    def finalize_review(self, *, candidate_type: str = "skill-method") -> dict[str, object]:
        source = self.admission.root / f"review-{candidate_type}.json"
        source.write_bytes(
            supervision_log.canonical(
                self.review_submission(candidate_type=candidate_type)
            )
        )
        return self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "finalize",
            "--evolution-id",
            self.evolution_id,
            "--review-json",
            str(source),
        )

    def create_candidate(
        self,
        owner_record: dict[str, object] | None,
        path: str = "implement-tracker-blocks/SKILL.md",
        *,
        passing: bool = True,
    ) -> str:
        branch = self.git("branch", "--show-current")
        self.git("switch", "-c", "candidate-block13")
        source = self.repository / path
        source.parent.mkdir(parents=True, exist_ok=True)
        previous = source.read_text(encoding="utf-8") if source.exists() else ""
        source.write_text(previous + "\nCandidate proves one bounded owner change.\n", encoding="utf-8")
        test_path = "implement-tracker-blocks/scripts/test_candidate_owner_proof.py"
        test_source = self.repository / test_path
        test_source.parent.mkdir(parents=True, exist_ok=True)
        test_source.write_text(
            "import unittest\n\n"
            "class CandidateOwnerProofTests(unittest.TestCase):\n"
            "    def test_candidate_effect(self):\n"
            f"        self.assertTrue({passing!r})\n",
            encoding="utf-8",
        )
        self.git("add", path, test_path)
        message = "Build isolated Block 13 candidate"
        if owner_record is not None:
            message += (
                "\n\n"
                f"Software-Factory-Handoff-Record: {owner_record['record_id']}\n"
                f"Software-Factory-Handoff-Root: {owner_record['orchestration_root']}\n"
                "Software-Factory-Handoff-Record-SHA256: "
                f"{owner_record['record_sha256']}"
            )
            commit_time = dt.datetime.now(dt.timezone.utc).isoformat()
        else:
            commit_time = dt.datetime.now(dt.timezone.utc).isoformat()
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_DATE": commit_time,
                "GIT_COMMITTER_DATE": commit_time,
            }
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(self.repository),
                "-c",
                "user.name=Factory Candidate Owner",
                "-c",
                "user.email=factory-candidate@example.test",
                "commit",
                "-m",
                message,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        revision = self.git("rev-parse", "HEAD")
        self.git("switch", branch)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline_revision)
        return revision

    def acknowledgment_source(
        self, owner_record: dict[str, object], candidate_revision: str
    ) -> dict[str, object]:
        handoff = owner_record["payload"]
        return {
            "schema_version": 1,
            "kind": supervision_log.FACTORY_EVOLUTION_OWNER_ACK_INPUT_KIND,
            "owner_handoff_record_id": owner_record["record_id"],
            "owner_handoff_orchestration_root": owner_record[
                "orchestration_root"
            ],
            "owner_handoff_record_sha256": owner_record["record_sha256"],
            "handoff_root": handoff["handoff_root"],
            "target_revision": handoff["target_revision"],
            "candidate_revision": candidate_revision,
            "focused_test_paths": [
                "implement-tracker-blocks/scripts/test_candidate_owner_proof.py"
            ],
        }

    def test_one_candidate_reaches_compare_without_changing_incumbent(self) -> None:
        routed = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.assertEqual(routed["action"]["stage"], "review-required")
        self.finalize_review()
        handed_off = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.assertEqual(handed_off["action"]["stage"], "owner-acknowledgment-required")
        owner_record = handed_off["record"]
        handoff = owner_record["payload"]
        self.assertEqual(handoff["normal_owner"], "implement-tracker-blocks")
        candidate_revision = self.create_candidate(owner_record)
        source = self.admission.root / "owner-ack.json"
        source.write_bytes(
            supervision_log.canonical(
                self.acknowledgment_source(owner_record, candidate_revision)
            )
            + b"\n"
        )
        acknowledged = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "acknowledge",
            "--evolution-id",
            self.evolution_id,
            "--owner-ack-json",
            str(source),
        )
        self.assertEqual(
            acknowledged["action"]["stage"], "candidate-ready-for-comparison"
        )
        self.assertEqual(acknowledged["action"]["next_action"], "compare")
        state = supervision_log.factory_evolution_cycle_state(
            self.directory,
            supervision_log.read_json(self.directory / "policy.json"),
            supervision_log.events(self.directory / "events.jsonl"),
            evolution_id=self.evolution_id,
        )
        evidence = state["acknowledgment_record"]["payload"]
        self.assertEqual(evidence["owner_handoff_record_id"], owner_record["record_id"])
        self.assertEqual(evidence["validation_results"][0]["exit_code"], 0)
        self.assertNotEqual(
            evidence["validation_results"][0]["stdout_sha256"], "0" * 64
        )
        self.assertEqual(
            evidence["validation_root"],
            supervision_log.digest(evidence["validation_results"]),
        )
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline_revision)
        self.assertEqual(self.git("status", "--short"), "")
        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        self.assertFalse((evolution / "evaluation.json").exists())

        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_validations",
            side_effect=AssertionError("completed owner proof must be reused"),
        ):
            duplicate = self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "acknowledge",
                "--evolution-id",
                self.evolution_id,
                "--owner-ack-json",
                str(source),
            )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["action"], acknowledged["action"])

    def test_interrupted_review_handoff_rehydrates_one_record(self) -> None:
        original = supervision_log.append_raw_locked_at

        def append_then_interrupt(*args: object, **kwargs: object) -> str:
            result = original(*args, **kwargs)
            raise OSError("simulated interruption after canonical append")

        with mock.patch.object(
            supervision_log, "append_raw_locked_at", side_effect=append_then_interrupt
        ):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "orchestrate",
                    "--evolution-id",
                    self.evolution_id,
                )
        retry = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.assertTrue(retry["duplicate"])
        records = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind") == supervision_log.FACTORY_EVOLUTION_REVIEW_HANDOFF_EVENT_KIND
        ]
        self.assertEqual(len(records), 1)

        self.finalize_review()
        with mock.patch.object(
            supervision_log, "append_raw_locked_at", side_effect=append_then_interrupt
        ):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "orchestrate",
                    "--evolution-id",
                    self.evolution_id,
                )
        owner_retry = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.assertTrue(owner_retry["duplicate"])
        owner_records = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind") == supervision_log.FACTORY_EVOLUTION_OWNER_HANDOFF_EVENT_KIND
        ]
        self.assertEqual(len(owner_records), 1)

    def test_candidate_scope_and_owner_input_mismatch_reject_without_write(self) -> None:
        self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.finalize_review(candidate_type="tracker-method")
        handed_off = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        owner_record = handed_off["record"]
        candidate_revision = self.create_candidate(owner_record)
        source_value = self.acknowledgment_source(owner_record, candidate_revision)
        source = self.admission.root / "owner-mismatch.json"
        source.write_bytes(supervision_log.canonical(source_value) + b"\n")
        before = supervision_log.events(self.directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "acknowledgment input binding|scope differs",
        ):
            self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "acknowledge",
                "--evolution-id",
                self.evolution_id,
                "--owner-ack-json",
                str(source),
            )
        self.assertEqual(
            supervision_log.events(self.directory / "events.jsonl"), before
        )

    def test_failed_owner_validation_stops_before_comparison(self) -> None:
        self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.finalize_review()
        handed_off = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        owner_record = handed_off["record"]
        candidate_revision = self.create_candidate(owner_record, passing=False)
        source_value = self.acknowledgment_source(owner_record, candidate_revision)
        source = self.admission.root / "owner-stopped.json"
        source.write_bytes(supervision_log.canonical(source_value) + b"\n")
        stopped = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "acknowledge",
            "--evolution-id",
            self.evolution_id,
            "--owner-ack-json",
            str(source),
        )
        self.assertEqual(stopped["action"]["stage"], "candidate-stopped")
        self.assertEqual(stopped["action"]["next_action"], "reject")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline_revision)
        self.assertEqual(self.git("status", "--short"), "")

    def test_candidate_created_before_owner_handoff_is_rejected(self) -> None:
        candidate_revision = self.create_candidate(None)
        self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.finalize_review()
        handed_off = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        source = self.admission.root / "pre-handoff-candidate.json"
        source.write_bytes(
            supervision_log.canonical(
                self.acknowledgment_source(handed_off["record"], candidate_revision)
            )
            + b"\n"
        )
        before = supervision_log.events(self.directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical owner handoff",
        ):
            self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "acknowledge",
                "--evolution-id",
                self.evolution_id,
                "--owner-ack-json",
                str(source),
            )
        self.assertEqual(supervision_log.events(self.directory / "events.jsonl"), before)

    def test_submitted_validation_outcomes_are_rejected(self) -> None:
        self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.finalize_review()
        handed_off = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        candidate_revision = self.create_candidate(handed_off["record"])
        source_value = self.acknowledgment_source(
            handed_off["record"], candidate_revision
        )
        source_value["validation_results"] = [
            {
                "command": "this-command-was-never-run",
                "exit_code": 0,
                "stdout_sha256": "0" * 64,
                "stderr_sha256": "0" * 64,
            }
        ]
        source = self.admission.root / "submitted-results.json"
        source.write_bytes(supervision_log.canonical(source_value) + b"\n")
        before = supervision_log.events(self.directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "input shape differs",
        ):
            self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "acknowledge",
                "--evolution-id",
                self.evolution_id,
                "--owner-ack-json",
                str(source),
            )
        self.assertEqual(supervision_log.events(self.directory / "events.jsonl"), before)

    def test_review_handoff_and_block_stop_precede_later_artifacts(self) -> None:
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "reviewer handoff"
        ):
            self.finalize_review()
        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        self.assertFalse((evolution / "review.json").exists())

        self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.finalize_review()
        later = self.admission.root / "evaluation-too-early.json"
        later.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "current Block Stop"
        ):
            self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "evaluate",
                "--evolution-id",
                self.evolution_id,
                "--evaluation-json",
                str(later),
            )
        self.assertFalse((evolution / "evaluation.json").exists())

    def test_policy_change_makes_the_admitted_cycle_stale(self) -> None:
        self.admission.set_policy(max_admissions=2)
        before = supervision_log.events(self.directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "one current admitted cycle"
        ):
            self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "orchestrate",
                "--evolution-id",
                self.evolution_id,
            )
        self.assertEqual(
            supervision_log.events(self.directory / "events.jsonl"), before
        )


if __name__ == "__main__":
    unittest.main()
