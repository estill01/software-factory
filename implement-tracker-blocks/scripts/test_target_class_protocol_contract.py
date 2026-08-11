#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("target_class_protocol.py")
SPEC = importlib.util.spec_from_file_location("target_class_protocol", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ADAPTIVE_TESTS = load_module(
    "target_class_adaptive_tests",
    protocol.ROOT
    / "supervise-tracker-runs"
    / "scripts"
    / "test_adaptive_decision_policy.py",
)
EVOLUTION_TESTS = load_module(
    "target_class_evolution_tests",
    protocol.ROOT
    / "supervise-tracker-runs"
    / "scripts"
    / "test_factory_evolution.py",
)
PROGRAM_TESTS = load_module(
    "target_class_program_tests",
    protocol.ROOT
    / "author-implementation-trackers"
    / "scripts"
    / "test_program_revision.py",
)


class TargetClassProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.codex_root = self.root / "codex"
        self.skills_root = self.codex_root / "skills"
        release = self.root / "release"
        self.skills_root.mkdir(parents=True)
        release.mkdir()
        for skill_id in protocol.SKILL_IDS:
            source = release / skill_id
            source.mkdir()
            (source / "SKILL.md").write_text(
                f"---\nname: {skill_id}\ndescription: fixture\n---\n",
                encoding="utf-8",
            )
            (source / "contract.txt").write_text(
                f"current {skill_id} behavior\n", encoding="utf-8"
            )
            (self.skills_root / skill_id).symlink_to(
                source, target_is_directory=True
            )
        self.adaptive = ADAPTIVE_TESTS.AdaptiveDecisionPolicyTests(
            "test_new_policy_defaults_to_full_autonomous_with_sealed_effect_ceilings"
        )
        self.adaptive.setUp()
        self.addCleanup(self.adaptive.doCleanups)
        self.program = PROGRAM_TESTS.ProgramRevisionTests(
            "test_split_revision_preserves_history_and_derives_resume"
        )
        self.program.setUp()
        self.addCleanup(self.program.doCleanups)
        self.evolution = EVOLUTION_TESTS.EvolutionReviewTests(
            "test_bundle_and_manifest_exactly_rebuild"
        )
        self.evolution.setUp()
        self.addCleanup(self.evolution.tearDown)

        self.target_tracker = Path(self.adaptive.repository_root) / "program-tracker.md"
        self.target_tracker.write_bytes(self.program.previous.read_bytes())
        subprocess.run(
            ["git", "add", self.target_tracker.name],
            cwd=self.adaptive.repository_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add program tracker fixture"],
            cwd=self.adaptive.repository_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.adaptive.target_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.adaptive.repository_root,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        committed_at = subprocess.run(
            ["git", "show", "-s", "--format=%cI", "HEAD"],
            cwd=self.adaptive.repository_root,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        self.adaptive.target_committed_at = dt.datetime.fromisoformat(committed_at)
        self.adaptive.candidate_observed_at = max(
            self.adaptive.target_committed_at,
            dt.datetime.now(dt.timezone.utc),
        )

        self.original_constants = {
            "CANONICAL_CODEX_ROOT": protocol.CANONICAL_CODEX_ROOT,
            "DEFAULT_SKILLS_ROOT": protocol.DEFAULT_SKILLS_ROOT,
            "DEFAULT_SUPERVISION_ROOT": protocol.DEFAULT_SUPERVISION_ROOT,
        }
        protocol.DEFAULT_SKILLS_ROOT = self.skills_root
        protocol.DEFAULT_SUPERVISION_ROOT = self.adaptive.root
        protocol.CANONICAL_CODEX_ROOT = self.codex_root
        self.control_sequence = 0
        self.original_authority = {}
        for name in (
            "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH",
            "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256",
            "ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH",
            "ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256",
        ):
            self.original_authority[name] = getattr(protocol.supervision, name)
        protocol.supervision.ADAPTIVE_REVIEW_PUBLIC_KEY_PATH = (
            self.adaptive.public_key
        )
        protocol.supervision.ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256 = (
            self.adaptive.public_key_sha
        )
        protocol.supervision.ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH = (
            self.adaptive.evaluator_public_key
        )
        protocol.supervision.ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256 = (
            self.adaptive.evaluator_public_key_sha
        )
        self.addCleanup(self.restore_protocol)

    def restore_protocol(self) -> None:
        for name, value in self.original_constants.items():
            setattr(protocol, name, value)
        for name, value in self.original_authority.items():
            setattr(protocol.supervision, name, value)

    def reset_control(self, target_class: str) -> dict[str, object]:
        self.control_sequence += 1
        self.adaptive.target = f"adaptive-target-{self.control_sequence:04d}"
        directory = self.adaptive.root / self.adaptive.target
        policy = self.adaptive.init()
        for field in policy["permissions"]:
            policy["permissions"][field] = True
        policy["adaptive_decision_control"] = (
            protocol.supervision.adaptive_decision_control_contract(
                "full-autonomous",
                target_class=target_class,
                target_repository_root=self.adaptive.repository_root,
            )
        )
        protocol.supervision.write_policy_version(
            directory,
            policy,
            kind="target-class-focused-policy",
            reason="Exercise one canonical target-class composition.",
            evidence_values=["block-10-focused-contract"],
        )
        return json.loads((directory / "policy.json").read_text(encoding="utf-8"))

    def active_events(self, policy: dict[str, object]) -> list[dict[str, object]]:
        directory = self.adaptive.root / self.adaptive.target
        return protocol.supervision.mission_scoped_events(
            directory,
            policy,
            protocol.supervision.events(directory / "events.jsonl"),
        )

    def capability_context(
        self, policy: dict[str, object], *, current_revision: str
    ) -> tuple[dict[str, object], str]:
        mission = protocol.supervision.bound_mission(policy)
        assert mission is not None
        mission_root = mission["mission_root"]
        state_fingerprint = "target-class-state-1234"
        evidence = [
            {
                "evidence_id": "direct-1234",
                "evidence_class": "direct-authority",
                "source_root": "1" * 64,
            },
            {
                "evidence_id": "repository-1234",
                "evidence_class": "current-repository",
                "source_root": "2" * 64,
            },
            {
                "evidence_id": "outcome-1234",
                "evidence_class": "observed-outcome",
                "source_root": "3" * 64,
            },
            {
                "evidence_id": "review-1234",
                "evidence_class": "independent-review",
                "source_root": "4" * 64,
            },
        ]
        claim = lambda statement, ids: {
            "statement": statement,
            "evidence_ids": ids,
        }
        value = {
            "schema_version": 1,
            "kind": protocol.supervision.CAPABILITY_RECONCILIATION_KIND,
            "target_thread_id": policy["target_thread_id"],
            "mission_root": mission_root,
            "state_fingerprint": state_fingerprint,
            "current_revision": current_revision,
            "implementation_owner_id": policy["target_thread_id"],
            "reviewer_id": policy["runtime"]["base_reviewer_thread_id"],
            "requested_capability": claim(
                "Apply one current target improvement.", ["direct-1234"]
            ),
            "protected_capabilities": [
                claim(
                    "Preserve the accepted target contract.",
                    ["repository-1234"],
                )
            ],
            "selected_architecture_level": {
                "level": "bounded target-owner composition",
                "owner_ref": "existing target repository owner",
                "evidence_ids": ["repository-1234"],
            },
            "accepted_tradeoffs": [
                claim(
                    "Retain independent review and rollback cost.",
                    ["repository-1234"],
                )
            ],
            "current_behavior": claim(
                "The current revision exhibits the reviewed effect.",
                ["outcome-1234"],
            ),
            "operator_visible_effects": [
                claim(
                    "The exact current output changed as intended.",
                    ["outcome-1234"],
                )
            ],
            "supported_gaps": [],
            "completion_posture": "verified",
            "evidence": evidence,
        }
        path = self.root / "capability.json"
        path.write_bytes(protocol.supervision.canonical(value) + b"\n")
        arguments = argparse.Namespace(
            root=str(self.adaptive.root),
            target_thread=self.adaptive.target,
            state_fingerprint=state_fingerprint,
            current_revision=current_revision,
            mission_root=mission_root,
            status="verified",
            model="gpt-5.6-sol",
            reasoning="xhigh",
            outcome_manifest_sha256="b" * 64,
            artifact_currentness_sha256="c" * 64,
            effect_reconciliation_sha256="d" * 64,
            open_item_compatibility_sha256="e" * 64,
            independent_challenge_sha256="f" * 64,
            capability_reconciliation_json=str(path),
            active_block="Block-10",
            checkpoint="target-class-current-behavior",
            summary="Current operator-visible outcome verified.",
            evidence=["block-10-focused-current-behavior"],
        )
        output = io.StringIO()
        with redirect_stdout(output):
            protocol.supervision.cmd_completion_record(arguments)
        emitted = json.loads(output.getvalue())["record"]
        record = next(
            item
            for item in reversed(self.active_events(policy))
            if item.get("record_id") == emitted["record_id"]
        )
        capability_root = protocol.digest(value)
        return (
            {
                "path": str(path),
                "target_thread_id": policy["target_thread_id"],
                "mission_root": mission_root,
                "state_fingerprint": state_fingerprint,
                "current_revision": current_revision,
                "completion_record_id": record["record_id"],
                "completion_record_sha256": record["record_sha256"],
                "capability_reconciliation_sha256": capability_root,
            },
            capability_root,
        )

    def decision_evidence(
        self,
        *,
        target_class: str,
        disposition: str,
        decision_id: str,
        candidate_root: str | None,
    ) -> dict[str, object]:
        evidence = self.adaptive.decision_evidence(
            decision_id=decision_id,
            disposition=disposition,
            target_class=target_class,
            candidate_evidence_root=candidate_root,
            consequence_class=(
                "routine" if disposition == "continue-unchanged" else "consequential"
            ),
            judgment_class=(
                "ordinary-engineering"
                if disposition == "continue-unchanged"
                else "consequential-product-tradeoff"
            ),
        )
        if disposition == "amend-structure":
            tracker_root = hashlib.sha256(self.target_tracker.read_bytes()).hexdigest()
            evidence["affected_scope"] = [
                {
                    "owner_id": self.adaptive.target,
                    "path": str(self.target_tracker),
                    "content_root": tracker_root,
                }
            ]
            for item in evidence["adjudicating_evidence_refs"]:
                if item["ref_id"] == "owned-file-1234":
                    item["root_sha256"] = tracker_root
            evidence["evidence_manifest_root"] = protocol.digest(
                evidence["adjudicating_evidence_refs"]
            )
            state_root = protocol.digest(
                {
                    "target_revision_root": evidence["target_revision_root"],
                    "affected_scope": evidence["affected_scope"],
                }
            )
            evidence["decision_target_state_root"] = state_root
            evidence["current_target_state_root"] = state_root
        if disposition == "continue-unchanged":
            evidence["proposer_author_id"] = None
        material = dict(evidence)
        material.pop("source_root")
        evidence["source_root"] = protocol.digest(material)
        return evidence

    def canonical_decision(
        self,
        policy: dict[str, object],
        *,
        target_class: str,
        disposition: str,
        decision_id: str,
    ) -> tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object] | None,
        dict[str, object],
    ]:
        candidate = None
        if disposition in {"compare-candidate", "cutover-candidate"}:
            candidate = self.adaptive.candidate(decision_id=decision_id)
        evidence = self.decision_evidence(
            target_class=target_class,
            disposition=disposition,
            decision_id=decision_id,
            candidate_root=(candidate["evidence_root"] if candidate else None),
        )
        first = self.adaptive.run_gate(
            self.adaptive.gate_args(evidence, candidate=candidate)
        )["record"]
        final = first
        review = None
        if first["independent_review_required"]:
            review_event = self.adaptive.run_review(first)["record"]
            final = self.adaptive.run_gate(
                self.adaptive.gate_args(
                    evidence,
                    candidate=candidate,
                    review_record=review_event["record_id"],
                )
            )["record"]
            review = protocol.supervision.resolve_adaptive_review(
                self.active_events(policy), review_event["record_id"], policy=policy
            )
        packet = self.adaptive.packet(
            policy, evidence=evidence, candidate=candidate, review=review
        )
        packet["governing_event_head_root"] = final["governing_event_head_root"]
        return packet, evidence, candidate, final

    def sign_program_review(
        self, packet: dict[str, object]
    ) -> dict[str, object]:
        review = {
            "schema_version": 1,
            "kind": "software-factory-program-revision-independent-review",
            "record_id": "REVIEW-TARGET-CLASS-1234",
            "revision_id": packet["revision_id"],
            "predecessor_revision_id": packet["predecessor_revision_id"],
            "predecessor_review_root": packet["predecessor_review_root"],
            "resolved_finding_refs": packet["resolved_finding_refs"],
            "packet_root": packet["packet_root"],
            "previous_tracker_sha256": packet["previous_tracker_sha256"],
            "proposed_tracker_sha256": packet["proposed_tracker_sha256"],
            "proposed_tracker_structure_sha256": packet[
                "proposed_tracker_structure_sha256"
            ],
            "accepted_history_root": packet["accepted_history_root"],
            "block_map_root": protocol.digest(packet["block_number_map"]),
            "affected_closure_root": protocol.digest(
                packet["affected_proposed_blocks"]
            ),
            "resume_block": packet["resume_block"],
            "author_id": packet["author_id"],
            "application_owner_id": packet["application_owner_id"],
            "reviewer_id": packet["reviewer_id"],
            "mechanical_watcher_id": packet["mechanical_watcher_id"],
            "adjudicator_id": packet["adjudicator_id"],
            "fix_executor_id": packet["fix_executor_id"],
            "authoring_profile_source_revision": packet[
                "authoring_profile_source_revision"
            ],
            "authoring_profile_source_root": packet[
                "authoring_profile_source_root"
            ],
            "authoring_profile_binding_root": packet[
                "authoring_profile_binding_root"
            ],
            "mechanical_route_record_id": packet["mechanical_route_record_id"],
            "semantic_review_record_id": packet["semantic_review_record_id"],
            "adjudication_root": packet["adjudication_root"],
            "disposition": "accepted",
            "finding_refs": [],
            "evidence_root": packet["packet_root"],
            "authority_key_sha256": self.adaptive.public_key_sha,
            "review_root": "",
            "signature_base64": "",
        }
        review["review_root"] = protocol.program_revision.digest(
            protocol.program_revision.review_root_material(review)
        )
        content = self.root / "program-review.json"
        signature = self.root / "program-review.sig"
        signed = dict(review)
        signed.pop("signature_base64")
        content.write_bytes(protocol.program_revision.canonical(signed))
        subprocess.run(
            [
                str(protocol.supervision.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.adaptive.private_key),
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
        review["signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode()
        return review

    def program_packet(
        self,
        policy: dict[str, object],
        evidence: dict[str, object],
        decision_event: dict[str, object],
    ) -> tuple[dict[str, object], dict[str, object]]:
        mission = protocol.supervision.bound_mission(policy)
        assert mission is not None
        metadata = self.program.metadata()
        metadata.update(
            {
                "target_thread_id": policy["target_thread_id"],
                "target_class": policy["adaptive_decision_control"]["target_class"],
                "mission_root": mission["mission_root"],
                "policy_sha256": policy["policy_sha256"],
                "decision_record_id": decision_event["record_id"],
                "decision_record_sha256": decision_event["record_sha256"],
                "repository_root": evidence["target_repository_root"],
                "target_revision": evidence["target_revision"],
                "target_revision_root": evidence["target_revision_root"],
                "decision_fingerprint": decision_event["decision_fingerprint"],
                "decision_currentness_root": decision_event[
                    "decision_currentness_root"
                ],
                "application_precondition_root": decision_event[
                    "application_precondition_root"
                ],
                "candidate_evidence_root": decision_event[
                    "candidate_evidence_root"
                ],
                "decision_target_state_root": evidence[
                    "decision_target_state_root"
                ],
                "current_target_state_root": evidence[
                    "current_target_state_root"
                ],
                "application_owner_id": evidence["implementation_owner_id"],
                "author_id": evidence.get("proposer_author_id")
                or "tracker-author-1234",
                "reviewer_id": decision_event["independent_reviewer_id"],
                "authority_mode": decision_event["adaptive_decision_mode"],
            }
        )
        packet = protocol.program_revision.build_revision_packet(
            previous_tracker=self.target_tracker,
            proposed_tracker=self.program.proposed,
            target_tracker_path=self.target_tracker,
            metadata=metadata,
        )
        return packet, self.sign_program_review(packet)

    def evolution_bundle(
        self,
        *,
        decision_event: dict[str, object],
        candidate: dict[str, object] | None,
        evidence: dict[str, object],
        live_sources_root: str,
        candidate_effect_suffix: str = "",
        evaluation_disposition: str = "promote",
    ) -> dict[str, object]:
        submission = self.evolution.review_submission()
        proposer = evidence["proposer_author_id"]
        implementer = evidence["implementation_owner_id"]
        evaluator = decision_event["independent_evaluator_id"]
        submission["reviewer_id"] = proposer
        selected = next(
            item
            for item in submission["candidates"]
            if item["candidate_id"] == submission["selection"]["candidate_id"]
        )
        candidate_id = (
            "adaptive-candidate-" + decision_event["decision_fingerprint"][:20]
        )
        selected["candidate_id"] = candidate_id
        selected["implementation_owner"] = implementer
        selected["evaluation_owner"] = evaluator
        submission["selection"]["candidate_id"] = candidate_id
        experiment = submission["experiment"]
        experiment["experiment_id"] = (
            "adaptive-experiment-" + decision_event["decision_fingerprint"][:20]
        )
        experiment["candidate_id"] = candidate_id
        experiment["proposer_id"] = proposer
        experiment["implementer_id"] = implementer
        experiment["evaluator_id"] = evaluator
        candidate_revision = (
            candidate["candidate_root"]
            if candidate is not None
            else protocol.digest(
                {
                    "decision_fingerprint": decision_event[
                        "decision_fingerprint"
                    ],
                    "disposition": evidence["disposition"],
                    "implementation_owner_id": implementer,
                }
            )
        )
        experiment["baseline_revision"] = live_sources_root
        experiment["candidate_revision"] = candidate_revision
        experiment["evidence_capture"] = "target-class-binding:" + protocol.digest(
            {
                "decision_id": decision_event["decision_id"],
                "decision_fingerprint": decision_event["decision_fingerprint"],
                "decision_currentness_root": decision_event[
                    "decision_currentness_root"
                ],
                "target_revision_root": evidence["target_revision_root"],
                "live_skill_sources_root": live_sources_root,
                "adaptive_candidate_evidence_root": decision_event[
                    "candidate_evidence_root"
                ],
                "evolution_candidate_revision": candidate_revision,
            }
        )
        review = protocol.factory_evolution.build_evolution_review(
            self.evolution.packet, submission
        )
        evaluation_submission = self.evolution.evaluation_submission(review)
        evaluation_submission["evaluator_id"] = evaluator
        evaluation_submission["experiment_id"] = experiment["experiment_id"]
        evaluation_submission["candidate_id"] = candidate_id
        evaluation_submission["disposition"] = evaluation_disposition
        for item in evaluation_submission["baseline_results"]:
            item["condition_revision"] = live_sources_root
            self.evolution.refresh_result_root(item)
        for item in evaluation_submission["candidate_results"]:
            item["condition_revision"] = candidate_revision
            item["observed_effect"] += candidate_effect_suffix
            self.evolution.refresh_result_root(item)
        evaluation = protocol.factory_evolution.build_candidate_evaluation(
            self.evolution.packet, review, evaluation_submission
        )
        return protocol.factory_evolution.build_evolution_bundle(
            self.evolution.packet, review, evaluation
        )

    def retain_evolution(
        self, evolution_id: str, bundle: dict[str, object]
    ) -> None:
        directory = protocol.supervision.factory_evolution_directory(
            self.adaptive.root / self.adaptive.target, evolution_id
        )
        packet = bundle["learning-packet.json"]
        review = bundle["review.json"]
        prepare_manifest = protocol.factory_evolution.build_evolution_manifest(
            {"learning-packet.json": packet}
        )
        finalize_manifest = protocol.factory_evolution.build_evolution_manifest(
            {"learning-packet.json": packet, "review.json": review}
        )
        protocol.supervision.write_factory_evolution_set(
            directory,
            {
                **bundle,
                "prepare-manifest.json": prepare_manifest,
                "finalize-manifest.json": finalize_manifest,
            },
        )

    def evolution_acceptance(
        self,
        *,
        evolution_id: str,
        bundle: dict[str, object],
        decision_event: dict[str, object],
        candidate: dict[str, object],
        live_sources_root: str,
    ) -> dict[str, object]:
        review = bundle["review.json"]
        evaluation = bundle["evaluation.json"]
        value = {
            "schema_version": 1,
            "kind": protocol.EVOLUTION_ACCEPTANCE_KIND,
            "decision_id": decision_event["decision_id"],
            "decision_fingerprint": decision_event["decision_fingerprint"],
            "decision_currentness_root": decision_event[
                "decision_currentness_root"
            ],
            "evolution_id": evolution_id,
            "evolution_root": protocol.digest(bundle),
            "evolution_review_root": review["review_root"],
            "evaluation_root": evaluation["evaluation_root"],
            "experiment_root": protocol.digest(review["experiment"]),
            "candidate_root": candidate["candidate_root"],
            "live_skill_sources_root": live_sources_root,
            "evaluation_disposition": evaluation["disposition"],
            "acceptance_authority_id": (
                protocol.supervision.ADAPTIVE_EVALUATOR_ID
            ),
            "acceptance_authority_key_sha256": (
                self.adaptive.evaluator_public_key_sha
            ),
            "acceptance_root": "",
            "acceptance_signature_base64": "",
        }
        return self.sign_evolution_acceptance(value)

    def sign_evolution_acceptance(
        self, value: dict[str, object]
    ) -> dict[str, object]:
        signed = copy.deepcopy(value)
        material = {
            key: item
            for key, item in signed.items()
            if key not in {"acceptance_root", "acceptance_signature_base64"}
        }
        signed["acceptance_root"] = protocol.digest(material)
        content = self.root / "evolution-acceptance.json"
        signature = self.root / "evolution-acceptance.sig"
        content.write_bytes(
            protocol.supervision.canonical(
                {**material, "acceptance_root": signed["acceptance_root"]}
            )
        )
        subprocess.run(
            [
                str(protocol.supervision.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.adaptive.evaluator_private_key),
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
        signed["acceptance_signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode()
        return signed

    def packet(
        self,
        target_class: str,
        disposition: str,
        *,
        reopen_outcome: bool = False,
        evolution_disposition: str = "promote",
    ) -> tuple[dict[str, object], dict[str, object]]:
        policy = self.reset_control(target_class)
        capability = None
        capability_root = None
        if disposition == "continue-unchanged":
            capability, capability_root = self.capability_context(
                policy, current_revision=self.adaptive.target_revision
            )
            if reopen_outcome:
                failed = argparse.Namespace(
                    root=str(self.adaptive.root),
                    target_thread=self.adaptive.target,
                    state_fingerprint=capability["state_fingerprint"],
                    current_revision=capability["current_revision"],
                    mission_root=capability["mission_root"],
                    status="failed",
                    model="gpt-5.6-sol",
                    reasoning="xhigh",
                    outcome_manifest_sha256="0" * 64,
                    artifact_currentness_sha256="c" * 64,
                    effect_reconciliation_sha256="d" * 64,
                    open_item_compatibility_sha256="e" * 64,
                    independent_challenge_sha256="f" * 64,
                    capability_reconciliation_json=capability["path"],
                    active_block="Block-10",
                    checkpoint="target-class-reopened-behavior",
                    summary="Current behavior evidence reopened one gap.",
                    evidence=["block-10-focused-reopened-behavior"],
                )
                with redirect_stdout(io.StringIO()):
                    protocol.supervision.cmd_completion_record(failed)
        decision_packet, evidence, candidate, decision_event = (
            self.canonical_decision(
                policy,
                target_class=target_class,
                disposition=disposition,
                decision_id=f"decision-{target_class}-{disposition}",
            )
        )
        program_packet = None
        program_review = None
        if disposition == "amend-structure":
            program_packet, program_review = self.program_packet(
                policy, evidence, decision_event
            )
        live_sources = (
            protocol.resolve_live_skill_sources(self.skills_root)
            if target_class == "software-factory"
            and disposition != "continue-unchanged"
            else []
        )
        live_sources_root = protocol.digest(live_sources)
        evolution = None
        evolution_id = None
        evolution_acceptance = None
        if (
            target_class == "software-factory"
            and disposition in protocol.FACTORY_EVALUATED_DISPOSITIONS
        ):
            evolution = self.evolution_bundle(
                decision_event=decision_event,
                candidate=candidate,
                evidence=evidence,
                live_sources_root=live_sources_root,
                evaluation_disposition=evolution_disposition,
            )
            evolution_id = (
                "target-class-" + decision_event["decision_fingerprint"][:20]
            )
            self.retain_evolution(evolution_id, evolution)
            evolution_acceptance = self.evolution_acceptance(
                evolution_id=evolution_id,
                bundle=evolution,
                decision_event=decision_event,
                candidate=candidate,
                live_sources_root=live_sources_root,
            )
        product_root = (
            candidate["evidence_root"]
            if candidate is not None
            else program_packet["packet_root"]
            if program_packet is not None
            else capability_root
            if capability_root is not None
            else evidence["current_target_state_root"]
        )
        packet = {
            "schema_version": 1,
            "kind": "software-factory-target-class-protocol",
            "target_class": target_class,
            "decision_record_id": decision_event["record_id"],
            "decision_packet": decision_packet,
            "program_revision_packet": program_packet,
            "program_revision_review": program_review,
            "factory_skill_sources": live_sources,
            "factory_evolution_id": evolution_id,
            "factory_evolution_acceptance": evolution_acceptance,
            "capability_context": capability,
            "claimed_improvement": disposition == "continue-unchanged",
            "factory_alignment_findings": (
                [
                    {
                        "finding_id": "factory-fit-1234",
                        "statement": "The current evidence remains inside the existing Factory owners.",
                        "evidence_roots": [live_sources_root],
                    }
                ]
                if target_class == "software-factory"
                and disposition != "continue-unchanged"
                else []
            ),
            "target_product_findings": [
                {
                    "finding_id": "target-effect-1234",
                    "statement": "Current target evidence remains separately attributable.",
                    "evidence_roots": [product_root],
                }
            ],
        }
        return packet, decision_event

    def validate(self, packet: dict[str, object]) -> dict[str, object]:
        return protocol.validate_target_class_protocol(
            self.adaptive.target, packet
        )

    def test_same_protocol_covers_all_paths_for_both_target_classes(self) -> None:
        for target_class in sorted(protocol.TARGET_CLASSES):
            for disposition in (
                "continue-unchanged",
                "correct-inline",
                "compare-candidate",
                "amend-structure",
                "cutover-candidate",
            ):
                with self.subTest(target_class=target_class, disposition=disposition):
                    packet, event = self.packet(target_class, disposition)
                    value = self.validate(packet)
                    self.assertEqual(value["target_class"], target_class)
                    self.assertEqual(value["disposition"], disposition)
                    self.assertEqual(value["decision_record_id"], event["record_id"])
                    self.assertFalse(value["application_authorized"])
                    self.assertFalse(value["candidate_authoritative"])
                    self.assertFalse(value["promotion_authorized"])
                    if disposition == "continue-unchanged":
                        self.assertTrue(value["improvement_established"])
                        self.assertEqual(value["resume_action"], "continue-current-block")
                    else:
                        self.assertEqual(
                            value["next_owner"],
                            packet["decision_packet"]["decision_evidence"][
                                "implementation_owner_id"
                            ],
                        )
                        self.assertIsNotNone(value["application_handoff_root"])

    def test_canonical_owner_and_target_class_cannot_be_substituted(self) -> None:
        packet, _event = self.packet("target-repository", "correct-inline")
        packet["target_class"] = "software-factory"
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "canonical policy"
        ):
            self.validate(packet)
        packet, _event = self.packet("software-factory", "correct-inline")
        decision = packet["decision_packet"]["decision_evidence"]
        decision["target_repository_root"] = str(self.root)
        material = dict(decision)
        material.pop("source_root")
        decision["source_root"] = protocol.digest(material)
        with self.assertRaises(protocol.TargetClassProtocolError):
            self.validate(packet)

        packet, event = self.packet("target-repository", "correct-inline")
        fake_home = self.root / "synthetic-home"
        fake_home.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(fake_home)}):
            accepted = self.validate(packet)
        self.assertEqual(accepted["decision_record_id"], event["record_id"])

    def test_evolution_is_exact_decision_evidence_not_role_only(self) -> None:
        packet, _event = self.packet("software-factory", "cutover-candidate")
        accepted = self.validate(packet)
        changed_acceptance = copy.deepcopy(packet)
        changed_acceptance["factory_evolution_acceptance"][
            "acceptance_signature_base64"
        ] = base64.b64encode(b"0" * 64).decode()
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "signature differs"
        ):
            self.validate(changed_acceptance)
        for invalid_version in (True, 1.0, "1"):
            changed_acceptance = copy.deepcopy(packet)
            invalid_acceptance = copy.deepcopy(
                changed_acceptance["factory_evolution_acceptance"]
            )
            invalid_acceptance["schema_version"] = invalid_version
            if type(invalid_version) is bool:
                invalid_acceptance = self.sign_evolution_acceptance(
                    invalid_acceptance
                )
            changed_acceptance["factory_evolution_acceptance"] = (
                invalid_acceptance
            )
            with self.assertRaisesRegex(
                protocol.TargetClassProtocolError, "acceptance differs"
            ):
                self.validate(changed_acceptance)
        changed_acceptance = copy.deepcopy(packet)
        changed_acceptance["factory_evolution_acceptance"][
            "acceptance_signature_base64"
        ] = changed_acceptance["factory_evolution_acceptance"][
            "acceptance_signature_base64"
        ].encode()
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "signature differs"
        ):
            self.validate(changed_acceptance)
        evolution_directory = protocol.supervision.factory_evolution_directory(
            self.adaptive.root / self.adaptive.target,
            packet["factory_evolution_id"],
        )
        evaluation_path = evolution_directory / "evaluation.json"
        external_evaluation = self.root / "external-evaluation.json"
        evaluation_path.replace(external_evaluation)
        evaluation_path.symlink_to(external_evaluation)
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "bundle is not current"
        ):
            self.validate(packet)
        evaluation_path.unlink()
        external_evaluation.replace(evaluation_path)
        exact_evaluation = evaluation_path.read_bytes()
        evaluation_path.write_bytes(
            b" " * (protocol.factory_evolution.MAX_ARTIFACT_BYTES + 1)
            + exact_evaluation
        )
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "bundle is not current"
        ):
            self.validate(packet)
        evaluation_path.write_bytes(b" " + exact_evaluation)
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "bundle is not current"
        ):
            self.validate(packet)
        evaluation_path.write_bytes(exact_evaluation)
        replacement = self.evolution_bundle(
            decision_event=_event,
            candidate=packet["decision_packet"]["candidate_evidence"],
            evidence=packet["decision_packet"]["decision_evidence"],
            live_sources_root=accepted["factory_skill_sources_root"],
            candidate_effect_suffix=" Replacement result.",
        )
        with self.assertRaisesRegex(
            protocol.supervision.SupervisionLogError,
            "artifact differs",
        ):
            self.retain_evolution(packet["factory_evolution_id"], replacement)
        shutil.rmtree(evolution_directory)
        self.retain_evolution(packet["factory_evolution_id"], replacement)
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "acceptance differs"
        ):
            self.validate(packet)
        self.assertIsNotNone(accepted["factory_evolution_root"])
        self.assertIn(
            accepted["factory_evolution_root"],
            accepted["application_handoff"].values(),
        )

        rejected_packet, _event = self.packet(
            "software-factory",
            "cutover-candidate",
            evolution_disposition="reject",
        )
        rejected = self.validate(rejected_packet)
        self.assertFalse(rejected["adoption_eligible"])
        self.assertEqual(
            rejected["resume_action"],
            "normal-owner-factory-candidate-retirement",
        )
        self.assertNotIn("adoption", rejected["resume_action"])

    def test_structural_packet_binds_revision_owner_scope_and_review(self) -> None:
        packet, _event = self.packet("software-factory", "amend-structure")
        self.validate(packet)
        changed = copy.deepcopy(packet)
        changed["program_revision_packet"]["target_revision"] = "f" * 40
        changed["program_revision_packet"]["packet_root"] = protocol.digest(
            {
                key: value
                for key, value in changed["program_revision_packet"].items()
                if key != "packet_root"
            }
        )
        with self.assertRaises(protocol.TargetClassProtocolError):
            self.validate(changed)
        changed = copy.deepcopy(packet)
        changed["program_revision_review"]["reviewer_id"] = changed[
            "program_revision_packet"
        ]["application_owner_id"]
        with self.assertRaises(protocol.TargetClassProtocolError):
            self.validate(changed)

    def test_findings_are_nonempty_and_claim_bound_for_mutation(self) -> None:
        packet, _event = self.packet("software-factory", "correct-inline")
        packet["target_product_findings"] = []
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "findings are required"
        ):
            self.validate(packet)

    def test_factory_mutation_hashes_live_skill_content_once(self) -> None:
        packet, _event = self.packet("software-factory", "correct-inline")
        with mock.patch.object(
            protocol,
            "resolve_live_skill_sources",
            wraps=protocol.resolve_live_skill_sources,
        ) as resolver:
            self.validate(packet)
        self.assertEqual(resolver.call_count, 1)
        packet, _event = self.packet("software-factory", "correct-inline")
        packet["factory_alignment_findings"][0]["evidence_roots"] = ["0" * 64]
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "not claim-bound"
        ):
            self.validate(packet)

    def test_current_behavior_requires_canonical_completion_event(self) -> None:
        packet, _event = self.packet("target-repository", "continue-unchanged")
        packet["capability_context"]["completion_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "canonical completion event"
        ):
            self.validate(packet)

        packet, _event = self.packet(
            "target-repository",
            "continue-unchanged",
            reopen_outcome=True,
        )
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "canonical completion event"
        ):
            self.validate(packet)

    def test_newer_target_decision_makes_prior_packet_stale(self) -> None:
        packet, _event = self.packet("target-repository", "correct-inline")
        policy = json.loads(
            (
                self.adaptive.root
                / self.adaptive.target
                / "policy.json"
            ).read_text(encoding="utf-8")
        )
        self.canonical_decision(
            policy,
            target_class="target-repository",
            disposition="continue-unchanged",
            decision_id="newer-target-decision-1234",
        )
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "canonical owner event"
        ):
            self.validate(packet)

    def test_final_currentness_rejects_target_change_during_evidence_load(self) -> None:
        packet, _event = self.packet("target-repository", "continue-unchanged")
        original = protocol.supervision.load_capability_reconciliation
        changed = False

        def load_then_change(*args, **kwargs):
            nonlocal changed
            value = original(*args, **kwargs)
            if not changed:
                self.adaptive.owned_path.write_text("VALUE = 3\n", encoding="utf-8")
                subprocess.run(
                    ["git", "add", self.adaptive.owned_path.name],
                    cwd=self.adaptive.repository_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["git", "commit", "-m", "Currentness mutation"],
                    cwd=self.adaptive.repository_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                changed = True
            return value

        with mock.patch.object(
            protocol.supervision,
            "load_capability_reconciliation",
            side_effect=load_then_change,
        ):
            with self.assertRaisesRegex(
                protocol.TargetClassProtocolError, "currentness changed"
            ):
                self.validate(packet)

    def test_final_currentness_rejects_changed_evolution_artifacts(self) -> None:
        packet, _event = self.packet("software-factory", "cutover-candidate")
        evolution_directory = protocol.supervision.factory_evolution_directory(
            self.adaptive.root / self.adaptive.target,
            packet["factory_evolution_id"],
        )
        original = protocol._canonical_evolution_bundle
        reads = 0

        def load_then_remove(*args, **kwargs):
            nonlocal reads
            value = original(*args, **kwargs)
            reads += 1
            if reads == 1:
                (evolution_directory / "evaluation.json").unlink()
            return value

        with mock.patch.object(
            protocol,
            "_canonical_evolution_bundle",
            side_effect=load_then_remove,
        ):
            with self.assertRaisesRegex(
                protocol.TargetClassProtocolError,
                "Factory evolution bundle is not current",
            ):
                self.validate(packet)
        self.assertEqual(reads, 1)

    def test_planned_new_file_uses_canonical_parent_containment(self) -> None:
        packet, _event = self.packet("target-repository", "correct-inline")
        decision = packet["decision_packet"]["decision_evidence"]
        path = Path(self.adaptive.repository_root) / "planned.py"
        decision["affected_scope"] = [
            {
                "owner_id": self.adaptive.target,
                "path": str(path),
                "content_root": protocol.digest(
                    {
                        "path": str(path),
                        "posture": "planned-new-file",
                        "target_revision_root": decision["target_revision_root"],
                    }
                ),
            }
        ]
        # This mutation is intentionally not accepted by the canonical decision
        # owner; the protocol must reject it as stale rather than raise a raw
        # filesystem exception while resolving the absent path.
        with self.assertRaises(protocol.TargetClassProtocolError) as error:
            self.validate(packet)
        self.assertNotIsInstance(error.exception.__cause__, FileNotFoundError)


if __name__ == "__main__":
    unittest.main()
