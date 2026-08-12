#!/usr/bin/env python3
from __future__ import annotations

import copy
import base64
import concurrent.futures
import datetime as dt
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import time
import threading
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
        self._install_evaluator_authority()
        self.review_support = evolution_test_support.EvolutionReviewTests(
            "test_review_can_identify_a_broad_capability_gap"
        )
        self.review_support.setUp()
        self.addCleanup(self.review_support.tearDown)
        self.packet = self.review_support.packet
        self.evolution_id = "evolution-orchestration-1234"
        self._record_admission()

    def _install_evaluator_authority(self) -> None:
        self.evaluator_private_key = self.admission.root / "evaluator-private.pem"
        self.evaluator_public_key = self.admission.root / "evaluator-public.pem"
        openssl = str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH)
        subprocess.run(
            [
                openssl,
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(self.evaluator_private_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                openssl,
                "pkey",
                "-in",
                str(self.evaluator_private_key),
                "-pubout",
                "-out",
                str(self.evaluator_public_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.evaluator_public_key.chmod(0o444)
        self.evaluator_public_key_sha = hashlib.sha256(
            self.evaluator_public_key.read_bytes()
        ).hexdigest()
        for name, value in (
            ("ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH", self.evaluator_public_key),
            ("ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256", self.evaluator_public_key_sha),
        ):
            patcher = mock.patch.object(supervision_log, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

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
        selected["evaluation_owner"] = supervision_log.ADAPTIVE_EVALUATOR_ID
        policy = supervision_log.read_json(self.directory / "policy.json")
        reviewer = policy["runtime"]["base_reviewer_thread_id"]
        submission["packet_id"] = self.packet["packet_id"]
        submission["packet_root"] = self.packet["packet_root"]
        submission["reviewer_id"] = reviewer
        submission["experiment"]["proposer_id"] = reviewer
        submission["experiment"]["implementer_id"] = owner
        submission["experiment"]["evaluator_id"] = supervision_log.ADAPTIVE_EVALUATOR_ID
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
        if owner_record is not None:
            protected_capabilities = owner_record["payload"]["protected_capabilities"]
        else:
            review = self.review_submission()
            selected = next(
                item
                for item in review["candidates"]
                if item["candidate_id"] == review["selection"]["candidate_id"]
            )
            protected_capabilities = selected["protected_capabilities"]
        owner_directory = Path(path).parts[0]
        self.last_candidate_test_paths: dict[str, str] = {}
        added = [path]
        for index, capability in enumerate(protected_capabilities, start=1):
            capability_id = (
                "capability-"
                + hashlib.sha256(str(capability).encode("utf-8")).hexdigest()[:20]
            )
            test_path = (
                f"{owner_directory}/scripts/"
                f"test_{capability_id.replace('-', '_')}.py"
            )
            self.last_candidate_test_paths[capability_id] = test_path
            test_source = self.repository / test_path
            test_source.parent.mkdir(parents=True, exist_ok=True)
            test_source.write_text(
                "import unittest\n\n"
                f"class CandidateCapabilityProof{index}Tests(unittest.TestCase):\n"
                "    def test_candidate_effect(self):\n"
                f"        self.assertTrue({passing!r})\n",
                encoding="utf-8",
            )
            added.append(test_path)
        self.git("add", *added)
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
            "protected_capability_test_paths": dict(
                self.last_candidate_test_paths
            ),
        }

    def sign_evaluation_submission(
        self, value: dict[str, object]
    ) -> dict[str, object]:
        value = copy.deepcopy(value)
        value["evaluation_signature_base64"] = ""
        content = self.admission.root / "evaluation-to-sign.json"
        signature = self.admission.root / "evaluation.sig"
        content.write_bytes(
            supervision_log.canonical(
                {
                    key: item
                    for key, item in value.items()
                    if key != "evaluation_signature_base64"
                }
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.evaluator_private_key),
                "-rawin",
                "-in",
                str(content),
                "-out",
                str(signature),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        value["evaluation_signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode()
        return value

    def evaluation_submission(
        self,
        handoff: dict[str, object],
        *,
        disposition: str = "promote",
    ) -> dict[str, object]:
        case_ids = sorted(
            set(handoff["positive_case_ids"] + handoff["exception_case_ids"])
        )

        def results(
            *, revision: str, source_root: str, outcome: str, label: str
        ) -> list[dict[str, object]]:
            items: list[dict[str, object]] = []
            for case_id in case_ids:
                material = {
                    "case_id": case_id,
                    "outcome": outcome,
                    "observed_effect": f"{label} observed for {case_id}.",
                    "resource_cost": f"{label} reused the one mapped comparison.",
                    "regressions": [],
                    "condition_revision": revision,
                    "source_evidence_root": source_root,
                }
                items.append(
                    {
                        **material,
                        "evidence_root": supervision_log.digest(
                            {
                                "evaluation_handoff_root": handoff[
                                    "evaluation_handoff_root"
                                ],
                                "result": material,
                            }
                        ),
                    }
                )
            return items

        value: dict[str, object] = {
            "schema_version": 1,
            "kind": factory_evolution.ORCHESTRATED_EVALUATION_SUBMISSION_KIND,
            "evaluation_handoff_root": handoff["evaluation_handoff_root"],
            "evaluator_id": handoff["evaluator_id"],
            "evaluator_authority_key_sha256": self.evaluator_public_key_sha,
            "evaluation_signature_base64": "",
            "baseline_results": results(
                revision=str(handoff["baseline_revision"]),
                source_root=str(handoff["baseline_validation_root"]),
                outcome="fail",
                label="Incumbent",
            ),
            "candidate_results": results(
                revision=str(handoff["candidate_revision"]),
                source_root=str(handoff["candidate_validation_root"]),
                outcome="pass",
                label="Candidate",
            ),
            "contrary_evidence": [
                "The bounded exception cases were inspected and no regression was observed."
            ],
            "regression_findings": [],
            "disposition": disposition,
            "rationale": "The exact mapped comparison supports the retained disposition.",
        }
        return self.sign_evaluation_submission(value)

    def candidate_ready_for_comparison(self) -> dict[str, object]:
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
        candidate_revision = self.create_candidate(owner_record)
        source = self.admission.root / "owner-evaluation-ready.json"
        source.write_bytes(
            supervision_log.canonical(
                self.acknowledgment_source(owner_record, candidate_revision)
            )
            + b"\n"
        )
        return self.command(
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

    def candidate_ready_for_evaluation(
        self,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.candidate_ready_for_comparison()
        comparison = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        return comparison, comparison["record"]["payload"]

    def start_comparison_without_producing(self) -> dict[str, object]:
        policy = supervision_log.read_json(self.directory / "policy.json")
        state = supervision_log.factory_evolution_cycle_state(
            self.directory,
            policy,
            supervision_log.events(self.directory / "events.jsonl"),
            evolution_id=self.evolution_id,
        )
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.admission.supervision_root),
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "orchestrate",
                "--evolution-id",
                self.evolution_id,
            ]
        )
        supervision_log.append_factory_evolution_comparison_start(
            args,
            expected_acknowledgment_root=state["acknowledgment_record"]["payload"][
                "currentness_root"
            ],
            proposed_payload=supervision_log.factory_candidate_comparison_start_payload(
                state
            ),
        )
        return supervision_log.factory_evolution_cycle_state(
            self.directory,
            policy,
            supervision_log.events(self.directory / "events.jsonl"),
            evolution_id=self.evolution_id,
        )

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
            acknowledged["action"]["stage"], "evaluation-handoff-required"
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
        self.assertEqual(
            len(evidence["validation_results"]),
            len(evidence["protected_capability_test_paths"]),
        )
        self.assertEqual(
            {item["test_path"] for item in evidence["validation_results"]},
            set(evidence["protected_capability_test_paths"].values()),
        )
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
        state = supervision_log.factory_evolution_cycle_state(
            self.directory,
            supervision_log.read_json(self.directory / "policy.json"),
            supervision_log.events(self.directory / "events.jsonl"),
            evolution_id=self.evolution_id,
        )
        evidence = state["acknowledgment_record"]["payload"]
        self.assertLess(
            len(evidence["validation_results"]),
            len(evidence["protected_capability_test_paths"]),
        )
        self.assertIn(
            "unverified",
            {item["result"] for item in evidence["protected_capability_results"]},
        )
        self.assertEqual(self.git("rev-parse", "HEAD"), self.baseline_revision)
        self.assertEqual(self.git("status", "--short"), "")

    def test_candidate_validation_uses_one_remaining_lane_deadline(self) -> None:
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
        candidate_revision = self.create_candidate(owner_record)
        source = self.acknowledgment_source(owner_record, candidate_revision)
        time.sleep(2)
        lane_start = dt.datetime.fromisoformat(str(owner_record["timestamp"]))
        midpoint = lane_start + dt.timedelta(seconds=1)
        observed = dt.datetime.now(dt.timezone.utc)
        clock = iter(
            [
                lane_start.isoformat(),
                midpoint.isoformat(),
                midpoint.isoformat(),
                observed.isoformat(),
                observed.isoformat(),
            ]
        )
        original_run = supervision_log.subprocess.run
        timeouts: list[int] = []

        def run_with_observed_timeout(*args: object, **kwargs: object) -> object:
            command = args[0]
            if (
                isinstance(command, list)
                and len(command) > 3
                and command[1:3] == ["-m", "unittest"]
            ):
                timeouts.append(int(kwargs["timeout"]))
                return subprocess.CompletedProcess(command, 0)
            return original_run(*args, **kwargs)

        with mock.patch.object(supervision_log, "utc_now", side_effect=lambda: next(clock)):
            with mock.patch.object(
                supervision_log.subprocess,
                "run",
                side_effect=run_with_observed_timeout,
            ):
                acknowledgment = supervision_log.factory_candidate_acknowledgment(
                    owner_record, source
                )
        self.assertEqual(acknowledgment["stop_disposition"], "candidate-ready-for-comparison")
        self.assertEqual(len(timeouts), 2)
        self.assertLess(timeouts[1], timeouts[0])

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
            supervision_log.SupervisionLogError, "evaluator handoff"
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

    def test_coherent_candidate_receives_one_current_independent_disposition(self) -> None:
        comparison, handoff = self.candidate_ready_for_evaluation()
        self.assertEqual(comparison["action"]["stage"], "evaluation-required")
        self.assertEqual(comparison["action"]["next_action"], "evaluate")
        self.assertNotEqual(
            handoff["baseline_validation_root"], handoff["candidate_validation_root"]
        )
        source = self.admission.root / "evaluation.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        before_head = self.git("rev-parse", "HEAD")
        result = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "evaluate",
            "--evolution-id",
            self.evolution_id,
            "--evaluation-json",
            str(source),
        )
        self.assertEqual(result["action"]["stage"], "evaluated")
        self.assertEqual(result["action"]["disposition"], "promote")
        self.assertTrue(result["action"]["adoption_eligible"])
        self.assertFalse(result["action"]["adoption_authorized"])
        self.assertEqual(result["action"]["next_action"], "stop-before-adoption")
        self.assertEqual(self.git("rev-parse", "HEAD"), before_head)
        duplicate = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "evaluate",
            "--evolution-id",
            self.evolution_id,
            "--evaluation-json",
            str(source),
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["action"], result["action"])

    def test_evaluation_rejects_stale_missing_process_only_and_identity_inputs(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        valid = self.evaluation_submission(handoff)
        mutations: list[tuple[str, dict[str, object], str]] = []
        stale = copy.deepcopy(valid)
        stale["evaluation_handoff_root"] = "0" * 64
        mutations.append(("stale", stale, "binding differs"))
        missing = copy.deepcopy(valid)
        missing["candidate_results"] = missing["candidate_results"][:-1]
        mutations.append(("missing", missing, "cover every experiment case"))
        process_only = copy.deepcopy(valid)
        process_only["candidate_results"][0]["source_evidence_root"] = "0" * 64
        mutations.append(("process-only", process_only, "source evidence is stale"))
        collapsed = copy.deepcopy(valid)
        collapsed["evaluator_id"] = "implement-tracker-blocks"
        mutations.append(("collapsed", collapsed, "evaluator ownership differs"))
        before = supervision_log.events(self.directory / "events.jsonl")
        for label, value, message in mutations:
            with self.subTest(label=label):
                value = self.sign_evaluation_submission(value)
                source = self.admission.root / f"evaluation-{label}.json"
                source.write_bytes(supervision_log.canonical(value) + b"\n")
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError, message
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
                        str(source),
                    )
                self.assertEqual(
                    supervision_log.events(self.directory / "events.jsonl"), before
                )
        invalid_signature = copy.deepcopy(valid)
        invalid_signature["evaluation_signature_base64"] = base64.b64encode(
            b"x" * 64
        ).decode()
        source = self.admission.root / "evaluation-invalid-signature.json"
        source.write_bytes(supervision_log.canonical(invalid_signature) + b"\n")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "signature differs"
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
                str(source),
            )
        self.assertEqual(supervision_log.events(self.directory / "events.jsonl"), before)

    def test_target_change_makes_the_evaluation_handoff_stale(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        source = self.admission.root / "evaluation-stale-target.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        changed = self.repository / "current-target-change.txt"
        changed.write_text("changed after evaluation handoff\n", encoding="utf-8")
        self.git("add", str(changed.relative_to(self.repository)))
        self.git(
            "-c",
            "user.name=Factory Test",
            "-c",
            "user.email=factory@example.test",
            "commit",
            "-m",
            "Change target after evaluation handoff",
        )
        before = supervision_log.events(self.directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "admitted context is not current"
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
                str(source),
            )
        self.assertEqual(supervision_log.events(self.directory / "events.jsonl"), before)

    def test_lower_dispositions_never_claim_adoption(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        expected = {
            "advisory": "retain-advisory",
            "revise": "return-to-normal-owner",
            "reject": "reject",
        }
        for disposition, next_action in expected.items():
            with self.subTest(disposition=disposition):
                evaluation = factory_evolution.build_orchestrated_candidate_evaluation(
                    handoff,
                    self.evaluation_submission(handoff, disposition=disposition),
                )
                self.assertFalse(evaluation["adoption_eligible"])
                self.assertFalse(evaluation["adoption_authorized"])
                self.assertIn(disposition, {"advisory", "revise", "reject"})
                self.assertIn(next_action, {"retain-advisory", "return-to-normal-owner", "reject"})

    def test_interrupted_evaluation_append_rehydrates_exact_disposition(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        source = self.admission.root / "evaluation-interrupted.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        original = supervision_log.append_raw_locked_at

        def append_then_interrupt(*args: object, **kwargs: object) -> str:
            result = original(*args, **kwargs)
            raise OSError("simulated interruption after evaluation append")

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=append_then_interrupt,
        ):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "evaluate",
                    "--evolution-id",
                    self.evolution_id,
                    "--evaluation-json",
                    str(source),
                )
        retried = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "evaluate",
            "--evolution-id",
            self.evolution_id,
            "--evaluation-json",
            str(source),
        )
        self.assertTrue(retried["duplicate"])
        self.assertEqual(retried["action"]["stage"], "evaluated")

    def test_interrupted_comparison_append_reuses_durable_raw_result(self) -> None:
        self.candidate_ready_for_comparison()
        original_execute = supervision_log.factory_candidate_execute_baseline_comparison
        calls = 0

        def counted_execute(*args: object, **kwargs: object) -> object:
            nonlocal calls
            calls += 1
            return original_execute(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=counted_execute,
        ):
            with mock.patch.object(
                supervision_log,
                "append_factory_evolution_evaluation_handoff",
                side_effect=OSError("simulated interruption before handoff append"),
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
            evolution = supervision_log.factory_evolution_directory(
                self.directory, self.evolution_id
            )
            self.assertTrue((evolution / "comparison-pending.json").is_file())
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "unexpected artifacts",
            ):
                supervision_log.verify_factory_evolution_inventory(evolution)
            supervision_log.verify_factory_evolution_inventory(
                evolution, allow_transient=True
            )
            retried = self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "orchestrate",
                "--evolution-id",
                self.evolution_id,
            )
        self.assertEqual(calls, 1)
        self.assertEqual(retried["action"]["stage"], "evaluation-required")
        self.assertFalse((evolution / "comparison-pending.json").exists())
        supervision_log.verify_factory_evolution_inventory(evolution)

    def test_missing_completed_comparison_never_reruns_producer(self) -> None:
        self.candidate_ready_for_comparison()
        original_execute = supervision_log.factory_candidate_execute_baseline_comparison
        calls = 0

        def counted_execute(*args: object, **kwargs: object) -> object:
            nonlocal calls
            calls += 1
            return original_execute(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=counted_execute,
        ):
            with mock.patch.object(
                supervision_log,
                "append_factory_evolution_evaluation_handoff",
                side_effect=OSError("simulated interruption before handoff append"),
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
            evolution = supervision_log.factory_evolution_directory(
                self.directory, self.evolution_id
            )
            (evolution / "comparison-pending.json").unlink()
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "result is missing after its canonical start",
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
        self.assertEqual(calls, 1)
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
                for item in supervision_log.events(self.directory / "events.jsonl")
            )
        )

    def test_interrupted_completed_comparison_cleanup_rehydrates(self) -> None:
        self.candidate_ready_for_comparison()
        original_execute = supervision_log.factory_candidate_execute_baseline_comparison
        original_remove = (
            supervision_log.factory_candidate_remove_completed_pending_comparison
        )
        producer_calls = 0
        remove_calls = 0

        def counted_execute(*args: object, **kwargs: object) -> object:
            nonlocal producer_calls
            producer_calls += 1
            return original_execute(*args, **kwargs)

        def interrupt_once(*args: object, **kwargs: object) -> object:
            nonlocal remove_calls
            remove_calls += 1
            if remove_calls == 1:
                raise OSError("simulated interruption before pending cleanup")
            return original_remove(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=counted_execute,
        ), mock.patch.object(
            supervision_log,
            "factory_candidate_remove_completed_pending_comparison",
            side_effect=interrupt_once,
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
            retried = self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "orchestrate",
                "--evolution-id",
                self.evolution_id,
            )

        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        self.assertEqual(producer_calls, 1)
        self.assertEqual(remove_calls, 2)
        self.assertTrue(retried["duplicate"])
        self.assertEqual(retried["action"]["stage"], "evaluation-required")
        self.assertFalse((evolution / "comparison-pending.json").exists())
        supervision_log.verify_factory_evolution_inventory(evolution)
        handoffs = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind")
            == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
        ]
        self.assertEqual(len(handoffs), 1)

    def test_interrupted_pending_unlink_durability_rehydrates(self) -> None:
        self.candidate_ready_for_comparison()
        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        pending_path = evolution / "comparison-pending.json"
        original_execute = supervision_log.factory_candidate_execute_baseline_comparison
        original_fsync = supervision_log.os.fsync
        producer_calls = 0
        pending_seen = False
        cleanup_fsync_attempts = 0
        cleanup_fsync_successes = 0

        def counted_execute(*args: object, **kwargs: object) -> object:
            nonlocal producer_calls
            producer_calls += 1
            return original_execute(*args, **kwargs)

        def interrupt_first_cleanup_fsync(descriptor: int) -> None:
            nonlocal pending_seen, cleanup_fsync_attempts, cleanup_fsync_successes
            if pending_path.exists():
                pending_seen = True
            elif pending_seen:
                cleanup_fsync_attempts += 1
                if cleanup_fsync_attempts == 1:
                    raise OSError("simulated interruption after pending unlink")
                cleanup_fsync_successes += 1
            original_fsync(descriptor)

        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=counted_execute,
        ), mock.patch.object(
            supervision_log.os,
            "fsync",
            side_effect=interrupt_first_cleanup_fsync,
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
            retried = self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "orchestrate",
                "--evolution-id",
                self.evolution_id,
            )

        self.assertEqual(producer_calls, 1)
        self.assertEqual(cleanup_fsync_attempts, 2)
        self.assertEqual(cleanup_fsync_successes, 1)
        self.assertTrue(retried["duplicate"])
        self.assertEqual(retried["action"]["stage"], "evaluation-required")
        self.assertFalse(pending_path.exists())
        supervision_log.verify_factory_evolution_inventory(evolution)
        handoffs = [
            item
            for item in supervision_log.events(self.directory / "events.jsonl")
            if item.get("kind")
            == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
        ]
        self.assertEqual(len(handoffs), 1)

    def test_pre_start_pending_comparison_is_not_accepted(self) -> None:
        self.candidate_ready_for_comparison()
        policy = supervision_log.read_json(self.directory / "policy.json")
        state = supervision_log.factory_evolution_cycle_state(
            self.directory,
            policy,
            supervision_log.events(self.directory / "events.jsonl"),
            evolution_id=self.evolution_id,
        )
        directory_fd = os.open(
            self.directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            owner_key = supervision_log.owner_root_key_at(
                directory_fd, allow_create=False
            )
        finally:
            os.close(directory_fd)
        material = {
            **supervision_log.factory_candidate_comparison_basis_identity(state),
            "producer_recorded_at": supervision_log.utc_now(),
            "baseline_validation_results": [],
        }
        owner_hmac = hmac.new(
            owner_key, supervision_log.canonical(material), hashlib.sha256
        ).hexdigest()
        rooted = {**material, "owner_hmac_sha256": owner_hmac}
        pending = {
            **rooted,
            "comparison_provenance_root": supervision_log.digest(rooted),
        }
        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        supervision_log.atomic_json(evolution / "comparison-pending.json", pending)
        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=AssertionError("pre-start result must not run or be accepted"),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "comparison provenance differs",
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
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_BASELINE_COMPARISON_START_EVENT_KIND
            ),
            1,
        )
        self.assertNotIn(
            supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND, kinds
        )

    def test_concurrent_comparison_delivery_reuses_one_durable_result(self) -> None:
        self.candidate_ready_for_comparison()
        state = self.start_comparison_without_producing()
        original_execute = supervision_log.factory_candidate_execute_baseline_comparison
        calls = 0
        calls_lock = threading.Lock()

        def counted_execute(*args: object, **kwargs: object) -> object:
            nonlocal calls
            with calls_lock:
                calls += 1
            time.sleep(0.1)
            return original_execute(*args, **kwargs)

        original_atomic_at = supervision_log.atomic_json_at
        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=counted_execute,
        ), mock.patch.object(
            supervision_log,
            "atomic_json_at",
            wraps=original_atomic_at,
        ) as durable_write:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        supervision_log.factory_candidate_load_or_produce_baseline_comparison,
                        self.directory,
                        state,
                        allow_produce=True,
                    )
                    for _ in range(2)
                ]
                retained = [future.result() for future in futures]
        self.assertEqual(calls, 1)
        self.assertEqual(
            retained[0]["comparison_provenance_root"],
            retained[1]["comparison_provenance_root"],
        )
        self.assertEqual(durable_write.call_count, 1)
        self.assertEqual(durable_write.call_args.args[1], "comparison-pending.json")

    def test_unavailable_evaluator_rejects_before_raw_comparison(self) -> None:
        self.candidate_ready_for_comparison()
        with mock.patch.object(
            supervision_log,
            "factory_candidate_execute_baseline_comparison",
            side_effect=AssertionError("comparison must not run"),
        ):
            with mock.patch.object(
                supervision_log,
                "trusted_adaptive_evaluator_key",
                side_effect=supervision_log.SupervisionLogError(
                    "sealed evaluator unavailable"
                ),
            ):
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "sealed evaluator unavailable",
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
        evolution = supervision_log.factory_evolution_directory(
            self.directory, self.evolution_id
        )
        self.assertFalse((evolution / "comparison-pending.json").exists())
        self.assertFalse(
            any(
                item.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
                for item in supervision_log.events(self.directory / "events.jsonl")
            )
        )

    def test_target_change_during_evaluation_handoff_records_correction(self) -> None:
        self.candidate_ready_for_comparison()
        original = supervision_log.append_raw_locked_at
        changed = False

        def change_target_before_append(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2]
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
            ):
                changed = True
                target = self.repository / "evaluation-handoff-currentness-change.txt"
                target.write_text(
                    "changed at evaluation handoff append\n", encoding="utf-8"
                )
                self.git("add", str(target.relative_to(self.repository)))
                self.git(
                    "-c",
                    "user.name=Factory Test",
                    "-c",
                    "user.email=factory@example.test",
                    "commit",
                    "-m",
                    "Change target at evaluation handoff append",
                )
            return original(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=change_target_before_append,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "changed during evaluation handoff append",
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
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
            ),
            1,
        )
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_CORRECTION_EVENT_KIND
            ),
            1,
        )

    def test_interrupted_handoff_correction_never_reactivates_source(self) -> None:
        self.candidate_ready_for_comparison()
        original_revision = self.git("rev-parse", "HEAD")
        original_append = supervision_log.append_raw_locked_at
        changed = False

        def interrupt_correction(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2]
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
            ):
                changed = True
                target = self.repository / "interrupted-handoff-correction.txt"
                target.write_text("changed during handoff append\n", encoding="utf-8")
                self.git("add", str(target.relative_to(self.repository)))
                self.git(
                    "-c",
                    "user.name=Factory Test",
                    "-c",
                    "user.email=factory@example.test",
                    "commit",
                    "-m",
                    "Change target before interrupted handoff correction",
                )
            if (
                isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_CORRECTION_EVENT_KIND
            ):
                raise OSError("simulated handoff correction interruption")
            return original_append(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=interrupt_correction,
        ):
            with self.assertRaisesRegex(
                OSError, "simulated handoff correction interruption"
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
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_EVENT_KIND
            ),
            1,
        )
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_HANDOFF_CORRECTION_EVENT_KIND
            ),
            0,
        )
        self.git("reset", "--hard", original_revision)
        policy = supervision_log.read_json(self.directory / "policy.json")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "target ownership is stale",
        ):
            supervision_log.factory_evolution_cycle_state(
                self.directory,
                policy,
                supervision_log.events(self.directory / "events.jsonl"),
                evolution_id=self.evolution_id,
            )

    def test_target_change_during_evaluation_append_records_correction(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        source = self.admission.root / "evaluation-append-currentness.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        original = supervision_log.append_raw_locked_at
        changed = False

        def change_target_before_append(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2]
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND
            ):
                changed = True
                target = self.repository / "evaluation-currentness-change.txt"
                target.write_text("changed at evaluation append\n", encoding="utf-8")
                self.git("add", str(target.relative_to(self.repository)))
                self.git(
                    "-c",
                    "user.name=Factory Test",
                    "-c",
                    "user.email=factory@example.test",
                    "commit",
                    "-m",
                    "Change target at evaluation append",
                )
            return original(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=change_target_before_append,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "changed during evaluation append"
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
                    str(source),
                )
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND),
            1,
        )
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_CORRECTION_EVENT_KIND
            ),
            1,
        )

    def test_interrupted_evaluation_correction_never_reactivates_source(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        source = self.admission.root / "evaluation-correction-interruption.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        original_revision = self.git("rev-parse", "HEAD")
        original_append = supervision_log.append_raw_locked_at
        changed = False

        def interrupt_correction(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2]
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND
            ):
                changed = True
                target = self.repository / "interrupted-evaluation-correction.txt"
                target.write_text("changed during source append\n", encoding="utf-8")
                self.git("add", str(target.relative_to(self.repository)))
                self.git(
                    "-c",
                    "user.name=Factory Test",
                    "-c",
                    "user.email=factory@example.test",
                    "commit",
                    "-m",
                    "Change target before interrupted correction",
                )
            if (
                isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_CORRECTION_EVENT_KIND
            ):
                raise OSError("simulated correction interruption")
            return original_append(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=interrupt_correction,
        ):
            with self.assertRaisesRegex(OSError, "simulated correction interruption"):
                self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "evaluate",
                    "--evolution-id",
                    self.evolution_id,
                    "--evaluation-json",
                    str(source),
                )
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND), 1
        )
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_CORRECTION_EVENT_KIND
            ),
            0,
        )
        self.git("reset", "--hard", original_revision)
        policy = supervision_log.read_json(self.directory / "policy.json")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "target ownership is stale",
        ):
            supervision_log.factory_evolution_cycle_state(
                self.directory,
                policy,
                supervision_log.events(self.directory / "events.jsonl"),
                evolution_id=self.evolution_id,
            )

    def test_target_aba_during_evaluation_append_never_becomes_active(self) -> None:
        _comparison, handoff = self.candidate_ready_for_evaluation()
        source = self.admission.root / "evaluation-append-aba.json"
        source.write_bytes(
            supervision_log.canonical(self.evaluation_submission(handoff)) + b"\n"
        )
        original_revision = self.git("rev-parse", "HEAD")
        original_append = supervision_log.append_raw_locked_at
        changed = False

        def change_and_restore_target(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2]
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind")
                == supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND
            ):
                changed = True
                target = self.repository / "evaluation-append-aba.txt"
                target.write_text("transient target revision\n", encoding="utf-8")
                self.git("add", str(target.relative_to(self.repository)))
                self.git(
                    "-c",
                    "user.name=Factory Test",
                    "-c",
                    "user.email=factory@example.test",
                    "commit",
                    "-m",
                    "Create transient evaluation revision",
                )
                result = original_append(*args, **kwargs)
                self.git("reset", "--hard", original_revision)
                return result
            return original_append(*args, **kwargs)

        with mock.patch.object(
            supervision_log,
            "append_raw_locked_at",
            side_effect=change_and_restore_target,
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "target ownership is stale",
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
                    str(source),
                )
        kinds = [
            item.get("kind")
            for item in supervision_log.events(self.directory / "events.jsonl")
        ]
        self.assertEqual(
            kinds.count(supervision_log.FACTORY_EVOLUTION_EVALUATION_EVENT_KIND), 1
        )
        self.assertEqual(
            kinds.count(
                supervision_log.FACTORY_EVOLUTION_EVALUATION_CORRECTION_EVENT_KIND
            ),
            0,
        )
        policy = supervision_log.read_json(self.directory / "policy.json")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "target ownership is stale",
        ):
            supervision_log.factory_evolution_cycle_state(
                self.directory,
                policy,
                supervision_log.events(self.directory / "events.jsonl"),
                evolution_id=self.evolution_id,
            )

    def test_same_head_reflog_event_invalidates_evaluation_handoff(self) -> None:
        self.candidate_ready_for_comparison()
        self.git("reset", "--hard", "HEAD")
        self.git("reset", "--hard", "HEAD")
        comparison = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            self.evolution_id,
        )
        self.assertEqual(comparison["action"]["stage"], "evaluation-required")
        policy = supervision_log.read_json(self.directory / "policy.json")
        before = supervision_log.factory_evolution_target_owner_currentness_root(
            policy
        )
        self.git("reset", "--hard", "HEAD")
        after = supervision_log.factory_evolution_target_owner_currentness_root(policy)
        self.assertNotEqual(before, after)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "target ownership is stale",
        ):
            supervision_log.factory_evolution_cycle_state(
                self.directory,
                policy,
                supervision_log.events(self.directory / "events.jsonl"),
                evolution_id=self.evolution_id,
            )

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
