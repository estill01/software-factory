#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


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
        self.skills_root = self.root / "skills"
        release = self.root / "release"
        self.skills_root.mkdir()
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
            (self.skills_root / skill_id).symlink_to(source, target_is_directory=True)
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
        self.original_authority = {}
        for name in (
            "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH",
            "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256",
            "ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH",
            "ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256",
        ):
            self.original_authority[name] = getattr(protocol.supervision, name)
        protocol.supervision.ADAPTIVE_REVIEW_PUBLIC_KEY_PATH = self.adaptive.public_key
        protocol.supervision.ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256 = self.adaptive.public_key_sha
        protocol.supervision.ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH = (
            self.adaptive.evaluator_public_key
        )
        protocol.supervision.ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256 = (
            self.adaptive.evaluator_public_key_sha
        )
        self.addCleanup(self.restore_authority)

    def restore_authority(self) -> None:
        for name, value in self.original_authority.items():
            setattr(protocol.supervision, name, value)

    def policy(self, target_class: str) -> dict[str, object]:
        value = self.adaptive.policy(target_class=target_class)
        for field in value["permissions"]:
            value["permissions"][field] = True
        return value

    def decision_packet(
        self,
        policy: dict[str, object],
        disposition: str,
        *,
        decision_id: str,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object] | None]:
        target_class = policy["adaptive_decision_control"]["target_class"]
        candidate = None
        if disposition in {"compare-candidate", "cutover-candidate"}:
            candidate = self.adaptive.candidate(decision_id=decision_id)
        evidence = self.adaptive.decision_evidence(
            decision_id=decision_id,
            disposition=disposition,
            target_class=target_class,
            candidate_evidence_root=(candidate["evidence_root"] if candidate else None),
            consequence_class=(
                "consequential" if disposition != "continue-unchanged" else "routine"
            ),
            judgment_class=(
                "consequential-product-tradeoff"
                if disposition != "continue-unchanged"
                else "ordinary-engineering"
            ),
        )
        if disposition == "continue-unchanged":
            evidence["proposer_author_id"] = None
            material = dict(evidence)
            material.pop("source_root")
            evidence["source_root"] = protocol.digest(material)
        review = None
        if target_class == "software-factory" and disposition != "continue-unchanged":
            review = self.adaptive.normalized_review(
                policy, evidence, candidate=candidate
            )
        elif disposition in {"compare-candidate", "cutover-candidate", "amend-structure"}:
            review = self.adaptive.normalized_review(
                policy, evidence, candidate=candidate
            )
        return (
            self.adaptive.packet(
                policy,
                evidence=evidence,
                candidate=candidate,
                review=review,
            ),
            evidence,
            candidate,
        )

    def evolution_bundle(
        self,
        *,
        proposer: str,
        implementer: str,
        evaluator: str,
    ) -> dict[str, object]:
        submission = self.evolution.review_submission()
        submission["reviewer_id"] = proposer
        submission["experiment"]["proposer_id"] = proposer
        submission["experiment"]["implementer_id"] = implementer
        submission["experiment"]["evaluator_id"] = evaluator
        selected = next(
            item
            for item in submission["candidates"]
            if item["candidate_id"] == submission["selection"]["candidate_id"]
        )
        selected["implementation_owner"] = implementer
        selected["evaluation_owner"] = evaluator
        review = protocol.factory_evolution.build_evolution_review(
            self.evolution.packet, submission
        )
        evaluation_submission = self.evolution.evaluation_submission(review)
        evaluation_submission["evaluator_id"] = evaluator
        evaluation = protocol.factory_evolution.build_candidate_evaluation(
            self.evolution.packet,
            review,
            evaluation_submission,
        )
        return protocol.factory_evolution.build_evolution_bundle(
            self.evolution.packet,
            review,
            evaluation,
        )

    def program_packet(
        self,
        target_class: str,
        policy: dict[str, object],
        evidence: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object]:
        metadata = self.program.metadata()
        metadata.update(
            {
                "target_thread_id": policy["target_thread_id"],
                "target_class": target_class,
                "repository_root": evidence["target_repository_root"],
                "target_revision": evidence["target_revision"],
                "target_revision_root": evidence["target_revision_root"],
                "decision_fingerprint": result["decision_fingerprint"],
                "decision_currentness_root": result["decision_currentness_root"],
                "decision_target_state_root": evidence["decision_target_state_root"],
                "current_target_state_root": evidence["current_target_state_root"],
                "application_owner_id": evidence["implementation_owner_id"],
                "author_id": (
                    evidence["proposer_author_id"]
                    if target_class == "software-factory"
                    else "tracker-author-1234"
                ),
            }
        )
        return protocol.program_revision.build_revision_packet(
            previous_tracker=self.program.previous,
            proposed_tracker=self.program.proposed,
            target_tracker_path=self.program.previous,
            metadata=metadata,
        )

    def capability_context(
        self,
        policy: dict[str, object],
        *,
        current_revision: str,
    ) -> dict[str, object]:
        mission_root = policy["policy_sha256"]
        state_fingerprint = "state-fingerprint-1234"
        evidence = [
            {"evidence_id": "direct-1234", "evidence_class": "direct-authority", "source_root": "1" * 64},
            {"evidence_id": "repository-1234", "evidence_class": "current-repository", "source_root": "2" * 64},
            {"evidence_id": "outcome-1234", "evidence_class": "observed-outcome", "source_root": "3" * 64},
            {"evidence_id": "review-1234", "evidence_class": "independent-review", "source_root": "4" * 64},
        ]
        claim = lambda statement, ids: {"statement": statement, "evidence_ids": ids}
        value = {
            "schema_version": 1,
            "kind": protocol.supervision.CAPABILITY_RECONCILIATION_KIND,
            "target_thread_id": policy["target_thread_id"],
            "mission_root": mission_root,
            "state_fingerprint": state_fingerprint,
            "current_revision": current_revision,
            "implementation_owner_id": policy["target_thread_id"],
            "reviewer_id": policy["runtime"]["base_reviewer_thread_id"],
            "requested_capability": claim("Apply one current target improvement.", ["direct-1234"]),
            "protected_capabilities": [claim("Preserve the accepted target contract.", ["repository-1234"])],
            "selected_architecture_level": {"level": "bounded target-owner composition", "owner_ref": "existing target repository owner", "evidence_ids": ["repository-1234"]},
            "accepted_tradeoffs": [claim("Retain independent review and rollback cost.", ["repository-1234"])],
            "current_behavior": claim("The current revision exhibits the reviewed effect.", ["outcome-1234"]),
            "operator_visible_effects": [claim("The exact current output changed as intended.", ["outcome-1234"])],
            "supported_gaps": [],
            "completion_posture": "verified",
            "evidence": evidence,
        }
        path = self.root / f"capability-{current_revision}.json"
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return {
            "path": str(path),
            "target_thread_id": policy["target_thread_id"],
            "mission_root": mission_root,
            "state_fingerprint": state_fingerprint,
            "current_revision": current_revision,
        }

    def packet(
        self,
        target_class: str,
        disposition: str,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        policy = self.policy(target_class)
        decision_packet, evidence, candidate = self.decision_packet(
            policy,
            disposition,
            decision_id=f"decision-{target_class}-{disposition}",
        )
        result = protocol.supervision._adaptive_decision_posture(
            policy, decision_packet, active_candidate_fingerprints=[]
        )
        program_packet = (
            self.program_packet(target_class, policy, evidence, result)
            if disposition == "amend-structure"
            else None
        )
        capability = (
            self.capability_context(
                policy, current_revision=evidence["target_revision"]
            )
            if disposition == "continue-unchanged"
            else None
        )
        review = decision_packet["independent_review"]
        evolution = None
        if (
            target_class == "software-factory"
            and disposition in protocol.FACTORY_EVALUATED_DISPOSITIONS
        ):
            evolution = self.evolution_bundle(
                proposer=evidence["proposer_author_id"],
                implementer=evidence["implementation_owner_id"],
                evaluator=review["evaluator_id"],
            )
        packet = {
            "schema_version": 1,
            "kind": "software-factory-target-class-protocol",
            "target_class": target_class,
            "decision_packet": decision_packet,
            "program_revision_packet": program_packet,
            "factory_skill_sources": (
                protocol.resolve_live_skill_sources(self.skills_root)
                if target_class == "software-factory"
                and disposition != "continue-unchanged"
                else []
            ),
            "factory_evolution_bundle": evolution,
            "capability_context": capability,
            "claimed_improvement": disposition == "continue-unchanged",
            "factory_alignment_findings": (
                [{"finding_id": "factory-fit-1234", "statement": "The candidate remains inside the existing Factory owners.", "evidence_root": "6" * 64}]
                if target_class == "software-factory"
                else []
            ),
            "target_product_findings": [
                {"finding_id": "target-effect-1234", "statement": "Current target evidence remains separately attributable.", "evidence_root": "7" * 64}
            ],
        }
        return policy, packet, result

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
                    policy, packet, _result = self.packet(target_class, disposition)
                    value = protocol.validate_target_class_protocol(
                        policy, packet, skills_root=self.skills_root
                    )
                    self.assertEqual(value["target_class"], target_class)
                    self.assertEqual(value["disposition"], disposition)
                    self.assertFalse(value["promotion_authorized"])
                    if target_class == "software-factory":
                        self.assertFalse(value["candidate_authoritative"])
                    if disposition == "compare-candidate":
                        self.assertFalse(value["candidate_authoritative"])
                    if disposition == "continue-unchanged":
                        self.assertTrue(value["improvement_established"])
                        self.assertEqual(value["resume_action"], "continue-current-block")
                    else:
                        self.assertFalse(value["candidate_authoritative"])
                        self.assertFalse(value["promotion_authorized"])
                        self.assertIsNotNone(value["application_handoff_root"])

    def test_ordinary_target_cannot_invoke_factory_or_reach_live_skill(self) -> None:
        policy, packet, _result = self.packet("target-repository", "correct-inline")
        packet["factory_skill_sources"] = protocol.resolve_live_skill_sources(
            self.skills_root
        )
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "invoked Factory evolution"
        ):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )

    def test_cross_target_identity_mismatch_rejects(self) -> None:
        policy, packet, _result = self.packet(
            "target-repository", "correct-inline"
        )
        packet["target_class"] = "software-factory"
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "canonical policy"
        ):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )

    def test_candidate_evidence_never_confers_application_authority(self) -> None:
        for target_class in sorted(protocol.TARGET_CLASSES):
            for disposition in ("compare-candidate", "cutover-candidate"):
                with self.subTest(
                    target_class=target_class, disposition=disposition
                ):
                    policy, packet, _result = self.packet(
                        target_class, disposition
                    )
                    value = protocol.validate_target_class_protocol(
                        policy, packet, skills_root=self.skills_root
                    )
                    self.assertFalse(value["application_authorized"])
                    self.assertFalse(value["candidate_authoritative"])
                    self.assertFalse(
                        value["application_handoff"]["application_authorized"]
                    )
        decision = packet["decision_packet"]["decision_evidence"]
        decision["affected_scope"][0]["path"] = str(
            self.skills_root / "implement-tracker-blocks"
        )
        material = dict(decision)
        material.pop("source_root")
        decision["source_root"] = protocol.digest(material)
        packet["factory_skill_sources"] = []
        with self.assertRaises(protocol.TargetClassProtocolError):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )

    def test_software_factory_rejects_collapsed_roles_stale_sources_and_self_promotion(self) -> None:
        policy, packet, _result = self.packet(
            "software-factory", "cutover-candidate"
        )
        review = packet["decision_packet"]["independent_review"]
        review["evaluator_id"] = review["reviewer_id"]
        with self.assertRaises(protocol.TargetClassProtocolError):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )
        policy, packet, _result = self.packet(
            "software-factory", "cutover-candidate"
        )
        packet["factory_skill_sources"][0]["source_manifest_root"] = "0" * 64
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "skill sources are stale"
        ):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )
        policy, packet, _result = self.packet(
            "software-factory", "cutover-candidate"
        )
        packet["promotion_owner_id"] = packet["decision_packet"]["decision_evidence"][
            "implementation_owner_id"
        ]
        with self.assertRaisesRegex(protocol.TargetClassProtocolError, "packet"):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )

    def test_factory_disposition_is_adoption_eligibility_not_promotion(self) -> None:
        policy, packet, _result = self.packet(
            "software-factory", "cutover-candidate"
        )
        value = protocol.validate_target_class_protocol(
            policy, packet, skills_root=self.skills_root
        )
        self.assertEqual(value["factory_evolution_disposition"], "promote")
        self.assertTrue(value["adoption_eligible"])
        self.assertFalse(value["promotion_authorized"])
        self.assertFalse(value["candidate_authoritative"])
        self.assertIsNone(value["next_owner"])
        self.assertEqual(
            value["resume_action"], "separately-governed-factory-adoption"
        )

    def test_process_records_without_current_behavior_do_not_establish_improvement(self) -> None:
        policy, packet, _result = self.packet(
            "target-repository", "cutover-candidate"
        )
        packet["capability_context"] = None
        packet["claimed_improvement"] = True
        with self.assertRaisesRegex(
            protocol.TargetClassProtocolError, "process-only evidence"
        ):
            protocol.validate_target_class_protocol(
                policy, packet, skills_root=self.skills_root
            )


if __name__ == "__main__":
    unittest.main()
