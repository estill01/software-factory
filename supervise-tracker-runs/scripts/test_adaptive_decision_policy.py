#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


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
        self.repository_root = "/tmp/software-factory-adaptive-target"
        self.private_key = self.root / "review-private.pem"
        self.public_key = self.root / "review-public.pem"
        openssl = str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH)
        subprocess.run(
            [openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [openssl, "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.public_key.chmod(0o444)
        self.public_key_sha = hashlib.sha256(self.public_key.read_bytes()).hexdigest()

    def policy(
        self,
        mode: str = "full-autonomous",
        *,
        target_class: str = "target-repository",
        repository_write: bool = True,
    ) -> dict[str, object]:
        permissions = {
            field: False for field in supervision_log.ADAPTIVE_PERMISSION_FIELDS
        }
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
                mode, target_class=target_class
            ),
        }

    def decision_evidence(
        self,
        *,
        decision_id: str = "adaptive-decision-1234",
        disposition: str = "correct-inline",
        target_class: str = "target-repository",
        candidate_evidence_root: str | None = None,
        evidence_root: str = "1" * 64,
        consequence_class: str = "routine",
        judgment_class: str = "ordinary-engineering",
        reversible: bool = True,
        mission_preserving: bool = True,
        blocked_subjects: list[str] | None = None,
        revisit_trigger: str = "",
    ) -> dict[str, object]:
        evidence_refs = [
            {
                "ref_id": "evidence-1234",
                "source_class": "repository",
                "root_sha256": evidence_root,
            }
        ]
        protected_results = [
            {
                "capability_id": "public-contract-1234",
                "result": "preserved",
                "evidence_ref_ids": ["evidence-1234"],
            }
        ]
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-decision-source",
            "decision_id": decision_id,
            "disposition": disposition,
            "judgment_class": judgment_class,
            "consequence_class": consequence_class,
            "reversible": reversible,
            "mission_preserving": mission_preserving,
            "block_contract_root": "2" * 64,
            "tracker_sha256": "3" * 64,
            "target_repository_root": self.repository_root,
            "target_revision": "revision-1234",
            "target_revision_root": supervision_log.digest(
                {"target_revision": "revision-1234"}
            ),
            "decision_target_state_root": "4" * 64,
            "current_target_state_root": "5" * 64,
            "capability_frame_root": "6" * 64,
            "protected_capability_results": protected_results,
            "protected_capability_root": supervision_log.digest(protected_results),
            "adjudicating_evidence_refs": evidence_refs,
            "affected_scope": [
                {
                    "owner_id": self.target,
                    "path": f"{self.repository_root}/owned.py",
                    "content_root": "8" * 64,
                }
            ],
            "implementation_owner_id": self.target,
            "proposer_author_id": (
                "adaptive-proposer-1234" if target_class == "software-factory" else None
            ),
            "stop_boundary": "Stop after the bounded owner action and validation.",
            "safe_frontier": ["block-7-unaffected-work"],
            "blocked_subjects": sorted(blocked_subjects or []),
            "revisit_trigger": revisit_trigger,
            "candidate_evidence_root": candidate_evidence_root,
            "evidence_manifest_root": supervision_log.digest(evidence_refs),
            "accepted_decision_head": None,
            "accepted_revision_head": None,
            "source_root": "",
        }
        material = dict(value)
        material.pop("source_root")
        value["source_root"] = supervision_log.digest(material)
        return value

    def candidate(
        self,
        *,
        decision_id: str = "adaptive-decision-1234",
        usage_updates: dict[str, int] | None = None,
        protected_result: str = "preserved",
        owner_id: str | None = None,
    ) -> dict[str, object]:
        usage = {
            field: 0 for field in supervision_log.ADAPTIVE_CANDIDATE_USAGE_FIELDS
        }
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
                "evidence_root": "a" * 64,
            }
        ]
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-candidate-evidence",
            "decision_id": decision_id,
            "owner_id": owner_id or self.target,
            "source_revision_root": "b" * 64,
            "candidate_root": "c" * 64,
            "candidate_budget_use": usage,
            "candidate_budget_use_root": supervision_log.digest(usage),
            "protected_capability_results": protected,
            "protected_capability_root": supervision_log.digest(protected),
            "validation_root": "d" * 64,
            "comparison_root": "e" * 64,
            "currentness_root": "",
            "evidence_root": "",
        }
        currentness = {
            "decision_id": decision_id,
            "owner_id": value["owner_id"],
            "source_revision_root": value["source_revision_root"],
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

    def packet(
        self,
        policy: dict[str, object],
        *,
        evidence: dict[str, object] | None = None,
        candidate: dict[str, object] | None = None,
        review: dict[str, object] | None = None,
        request_human_input: bool = False,
    ) -> dict[str, object]:
        source = evidence or self.decision_evidence(
            target_class=str(
                policy.get("adaptive_decision_control", {}).get(  # type: ignore[union-attr]
                    "target_class", "target-repository"
                )
            )
        )
        return {
            "decision_evidence": source,
            "candidate_evidence": candidate,
            "independent_review": review,
            "request_human_input": request_human_input,
            "governing_event_head_root": "f" * 64,
        }

    def normalized_review(
        self,
        policy: dict[str, object],
        evidence: dict[str, object],
        *,
        candidate: dict[str, object] | None = None,
        disposition: str = "accepted",
    ) -> dict[str, object]:
        pending = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=evidence, candidate=candidate)
        )
        software_factory = pending["target_class"] == "software-factory"
        return {
            "record_id": "review-record-1234",
            "source_decision_record": "source-decision-1234",
            "source_decision_sha256": "1" * 64,
            "decision_id": pending["decision_id"],
            "decision_fingerprint": pending["decision_fingerprint"],
            "decision_currentness_root": pending["decision_currentness_root"],
            "decision_semantics_root": pending["decision_semantics_root"],
            "disposition": pending["disposition"],
            "target_class": pending["target_class"],
            "effect_class": pending["effect_class"],
            "candidate_evidence_root": pending["candidate_evidence_root"],
            "candidate_owner_id": pending["candidate_owner_id"],
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "evaluator_id": (
                supervision_log.ADAPTIVE_EVALUATOR_ID if software_factory else None
            ),
            "evaluation_evidence_root": "4" * 64 if software_factory else None,
            "review_disposition": disposition,
            "evaluation_disposition": "accepted" if software_factory else None,
            "evidence_root": "2" * 64,
            "review_root": "3" * 64,
            "authority_key_sha256": supervision_log.ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256,
            "policy_sha256": policy["policy_sha256"],
        }

    def write_json(self, name: str, value: dict[str, object]) -> Path:
        path = self.root / name
        path.write_bytes(supervision_log.canonical(value) + b"\n")
        return path

    def init(self) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "init", "--target-thread", self.target,
                "--target-label", "Adaptive policy fixture",
                "--watcher-thread", "watcher-1234",
                "--reviewer-thread", "reviewer-1234",
                "--base-reviewer-thread", "base-reviewer-1234",
                "--fix-executor-thread", "fix-executor-1234",
                "--mission-source-class", "direct-user",
                "--mission-source-record", "direct-item-1234",
                "--mission-source-sha256", "c" * 64,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_init(args)
        return json.loads(output.getvalue())["policy"]

    def adjust(self, *extra: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "adjust", "--target-thread", self.target,
                *extra, "--reason", "Exercise bounded adaptive policy adjustment.",
                "--evidence", "block-7-focused-test",
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adjust(args)
        return json.loads(output.getvalue())["policy"]

    def gate_args(
        self,
        evidence: dict[str, object],
        *,
        candidate: dict[str, object] | None = None,
        review_record: str | None = None,
        request_human: bool = False,
    ):
        evidence_path = self.write_json(
            f"{evidence['decision_id']}-decision.json", evidence
        )
        values = [
            "--root", str(self.root), "adaptive-decision-gate",
            "--target-thread", self.target,
            "--decision-evidence", str(evidence_path),
        ]
        if candidate is not None:
            candidate_path = self.write_json(
                f"{candidate['decision_id']}-candidate.json", candidate
            )
            values.extend(["--candidate-evidence", str(candidate_path)])
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

    def signed_review_json(
        self,
        source: dict[str, object],
        *,
        review_disposition: str = "accepted",
        mutate: dict[str, object] | None = None,
    ) -> dict[str, object]:
        software_factory = source["target_class"] == "software-factory"
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-independent-review",
            "record_id": f"signed-{source['decision_id']}",
            "source_decision_record": source["record_id"],
            "source_decision_sha256": source["record_sha256"],
            "decision_id": source["decision_id"],
            "decision_fingerprint": source["decision_fingerprint"],
            "decision_currentness_root": source["decision_currentness_root"],
            "decision_semantics_root": source["decision_semantics_root"],
            "disposition": source["disposition"],
            "target_class": source["target_class"],
            "effect_class": source["effect_class"],
            "candidate_evidence_root": source["candidate_evidence_root"],
            "candidate_owner_id": source["candidate_owner_id"],
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "evaluator_id": (
                supervision_log.ADAPTIVE_EVALUATOR_ID if software_factory else None
            ),
            "evaluation_evidence_root": "4" * 64 if software_factory else None,
            "review_disposition": review_disposition,
            "evaluation_disposition": "accepted" if software_factory else None,
            "evidence_root": supervision_log.digest(
                {"source_decision_sha256": source["record_sha256"]}
            ),
            "policy_sha256": source["policy_sha256"],
            "authority_key_sha256": self.public_key_sha,
            "review_root": "",
            "signature_base64": "",
        }
        if mutate:
            value.update(mutate)
        value["review_root"] = supervision_log.digest(
            supervision_log.adaptive_external_review_root_material(value)
        )
        content = self.root / "review-to-sign.json"
        signature = self.root / "review.sig"
        content.write_bytes(
            supervision_log.canonical(
                supervision_log.adaptive_external_review_signed_material(value)
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl", "-sign", "-inkey", str(self.private_key), "-rawin",
                "-in", str(content), "-out", str(signature),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        value["signature_base64"] = base64.b64encode(signature.read_bytes()).decode()
        return value

    def run_review(
        self,
        source: dict[str, object],
        *,
        mutate: dict[str, object] | None = None,
    ) -> dict[str, object]:
        review = self.signed_review_json(source, mutate=mutate)
        path = self.write_json(f"{review['record_id']}.json", review)
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "adaptive-decision-review",
                "--target-thread", self.target, "--review-json", str(path),
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH", self.public_key
            ),
            mock.patch.object(
                supervision_log,
                "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256",
                self.public_key_sha,
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_adaptive_decision_review(args)
        return json.loads(output.getvalue())

    def test_new_policy_defaults_to_full_autonomous_with_sealed_effect_ceilings(self) -> None:
        policy = self.init()
        self.assertEqual(
            policy["adaptive_decision_control"]["adaptive_decision_mode"],
            "full-autonomous",
        )
        self.assertEqual(policy["adaptive_decision_control"]["target_class"], "target-repository")
        for field in (
            "production_promotion", "release", "deployment", "destructive_action",
            "spend", "credential_access", "external_action",
        ):
            self.assertIs(policy["permissions"][field], False)
        supervision_log.validate_policy(policy)

    def test_legacy_policy_stays_fixed_until_explicit_migration(self) -> None:
        policy = self.policy()
        del policy["adaptive_decision_control"]
        result = supervision_log.adaptive_decision_posture(policy, self.packet(policy))
        self.assertEqual(result["adaptive_decision_mode"], "fixed")
        self.assertEqual(result["application_posture"], "record-only")
        self.assertTrue(result["legacy_policy_posture"])

    def test_modes_preserve_application_and_review_boundaries(self) -> None:
        fixed_policy = self.policy("fixed")
        source = self.decision_evidence()
        fixed = supervision_log.adaptive_decision_posture(
            fixed_policy, self.packet(fixed_policy, evidence=source)
        )
        self.assertEqual(fixed["application_posture"], "record-only")
        recommend = self.policy("recommend")
        pending = supervision_log.adaptive_decision_posture(
            recommend, self.packet(recommend, evidence=source)
        )
        self.assertEqual(pending["application_posture"], "automated-independent-review-required")
        reviewed = supervision_log.adaptive_decision_posture(
            recommend,
            self.packet(
                recommend,
                evidence=source,
                review=self.normalized_review(recommend, source),
            ),
        )
        self.assertEqual(reviewed["application_posture"], "recommendation-only")
        full = self.policy()
        applied = supervision_log.adaptive_decision_posture(
            full, self.packet(full, evidence=source)
        )
        self.assertTrue(applied["application_authorized"])
        reviewed_policy = self.policy("reviewed-autonomous")
        consequential = self.decision_evidence(consequence_class="consequential")
        held = supervision_log.adaptive_decision_posture(
            reviewed_policy,
            self.packet(reviewed_policy, evidence=consequential),
        )
        self.assertEqual(held["application_posture"], "external-application-authority-required")

    def test_full_autonomy_never_routes_ordinary_judgment_to_a_human(self) -> None:
        policy = self.policy()
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "forbids a human"):
            supervision_log.adaptive_decision_posture(
                policy, self.packet(policy, request_human_input=True)
            )
        notification = supervision_log.decision_notification(
            {
                "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(),
                "notifications": {"gmail_priority": {"enabled": True}},
            },
            [],
            {"record_id": "EVT-000001", "classification": "human-preference", "phase": "attempt-unresolved", "attempt": 1},
            "start-sol-max-attempt",
        )
        self.assertFalse(notification["notification_send_now"])
        reserved = self.decision_evidence(
            judgment_class="reserved-external",
            blocked_subjects=["credential-boundary"],
            revisit_trigger="Credential authority becomes current.",
        )
        posture = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=reserved)
        )
        self.assertEqual(posture["application_posture"], "reserved-external")
        self.assertEqual(posture["human_request_count"], 0)

    def test_effect_class_is_policy_derived_and_permission_specific(self) -> None:
        policy = self.policy()
        candidate = self.candidate()
        source = self.decision_evidence(
            disposition="cutover-candidate",
            candidate_evidence_root=str(candidate["evidence_root"]),
            blocked_subjects=["production-promotion"],
            revisit_trigger="Production promotion authority becomes current.",
        )
        review = self.normalized_review(policy, source, candidate=candidate)
        result = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=source, candidate=candidate, review=review)
        )
        self.assertEqual(result["effect_class"], "production-cutover")
        self.assertFalse(result["permission_results"]["production_promotion"])
        self.assertEqual(result["application_posture"], "reserved-external")
        parser = supervision_log.parser()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "adaptive-decision-gate", "--target-thread", self.target,
                    "--decision-evidence", "decision.json", "--effect-class", "implementation-write",
                ]
            )

    def test_candidate_evidence_is_canonical_owner_current_and_budget_bound(self) -> None:
        candidate = self.candidate()
        path = self.write_json("candidate.json", candidate)
        loaded = supervision_log.load_adaptive_candidate_evidence(
            str(path),
            decision_id="adaptive-decision-1234",
            implementation_owner_id=self.target,
        )
        self.assertEqual(loaded["evidence_root"], candidate["evidence_root"])
        path.write_bytes(supervision_log.canonical(candidate) + b" \n")
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "exact canonical"):
            supervision_log.load_adaptive_candidate_evidence(
                str(path),
                decision_id="adaptive-decision-1234",
                implementation_owner_id=self.target,
            )
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "owner differs"):
            supervision_log.validate_adaptive_candidate_evidence(
                self.candidate(owner_id="invented-owner-1234"),
                decision_id="adaptive-decision-1234",
                implementation_owner_id=self.target,
            )
        over = self.candidate(usage_updates={"files": 4})
        source = self.decision_evidence(
            disposition="compare-candidate", candidate_evidence_root=str(over["evidence_root"])
        )
        result = supervision_log.adaptive_decision_posture(
            self.policy(), self.packet(self.policy(), evidence=source, candidate=over)
        )
        self.assertTrue(result["budget_exceeded"])
        self.assertEqual(result["application_posture"], "stop-and-retire-candidate")

    def test_protected_regression_stops_candidate_before_review(self) -> None:
        candidate = self.candidate(protected_result="regressed")
        source = self.decision_evidence(
            disposition="compare-candidate", candidate_evidence_root=str(candidate["evidence_root"])
        )
        result = supervision_log.adaptive_decision_posture(
            self.policy(), self.packet(self.policy(), evidence=source, candidate=candidate)
        )
        self.assertTrue(result["protected_regression"])
        self.assertEqual(result["application_posture"], "stop-and-retire-candidate")

    def test_signed_review_is_source_bound_current_and_one_use(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source_evidence = self.decision_evidence(decision_id="signed-decision-1234")
        source = self.run_gate(self.gate_args(source_evidence))["record"]
        self.assertEqual(source["application_posture"], "automated-independent-review-required")
        review = self.run_review(source)["record"]
        self.assertEqual(review["decision_semantics_root"], source["decision_semantics_root"])
        applied = self.run_gate(
            self.gate_args(source_evidence, review_record=str(review["record_id"]), request_human=True)
        )["record"]
        self.assertEqual(applied["independent_review_record"], review["record_id"])
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "stale|already has"):
            self.run_review(source)

    def test_fabricated_or_replayed_review_rejects(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source_evidence = self.decision_evidence(decision_id="review-attack-decision")
        source = self.run_gate(self.gate_args(source_evidence))["record"]
        for mutation in (
            {"decision_id": "other-decision-1234"},
            {"decision_semantics_root": "0" * 64},
            {"candidate_owner_id": "invented-owner-1234"},
            {"reviewer_id": "invented-reviewer-1234"},
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "bind|authority|source|signature|shape",
            ):
                self.run_review(source, mutate=mutation)
        unsigned = self.signed_review_json(source)
        unsigned["signature_base64"] = base64.b64encode(b"x" * 64).decode()
        path = self.write_json("forged-review.json", unsigned)
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), "adaptive-decision-review", "--target-thread", self.target, "--review-json", str(path)]
        )
        with (
            mock.patch.object(supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH", self.public_key),
            mock.patch.object(supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256", self.public_key_sha),
            self.assertRaisesRegex(supervision_log.SupervisionLogError, "signature"),
        ):
            supervision_log.cmd_adaptive_decision_review(args)

    def test_post_review_candidate_or_decision_currentness_change_rejects(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        candidate = self.candidate(decision_id="candidate-review-1234")
        evidence = self.decision_evidence(
            decision_id="candidate-review-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(candidate["evidence_root"]),
        )
        source = self.run_gate(self.gate_args(evidence, candidate=candidate))["record"]
        review = self.run_review(source)["record"]
        changed_candidate = copy.deepcopy(candidate)
        changed_candidate["source_revision_root"] = "0" * 64
        changed_currentness = {
            "decision_id": changed_candidate["decision_id"],
            "owner_id": changed_candidate["owner_id"],
            "source_revision_root": changed_candidate["source_revision_root"],
            "candidate_root": changed_candidate["candidate_root"],
            "candidate_budget_use_root": changed_candidate["candidate_budget_use_root"],
            "protected_capability_root": changed_candidate["protected_capability_root"],
            "validation_root": changed_candidate["validation_root"],
            "comparison_root": changed_candidate["comparison_root"],
        }
        changed_candidate["currentness_root"] = supervision_log.digest(changed_currentness)
        candidate_material = dict(changed_candidate)
        candidate_material.pop("evidence_root")
        changed_candidate["evidence_root"] = supervision_log.digest(candidate_material)
        changed_evidence = copy.deepcopy(evidence)
        changed_evidence["candidate_evidence_root"] = changed_candidate["evidence_root"]
        source_material = dict(changed_evidence)
        source_material.pop("source_root")
        changed_evidence["source_root"] = supervision_log.digest(source_material)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "bind the current decision|canonical decision"
        ):
            self.run_gate(
                self.gate_args(
                    changed_evidence,
                    candidate=changed_candidate,
                    review_record=str(review["record_id"]),
                )
            )

    def test_cross_id_same_fingerprint_deduplicates_before_review_cycle(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        first = self.decision_evidence(decision_id="decision-one-1234")
        second = self.decision_evidence(decision_id="decision-two-1234")
        first_result = self.run_gate(self.gate_args(first))
        second_result = self.run_gate(self.gate_args(second))
        self.assertFalse(first_result["duplicate"])
        self.assertTrue(second_result["duplicate"])
        self.assertEqual(second_result["record"]["decision_id"], "decision-one-1234")
        events = [
            json.loads(line)
            for line in (self.root / self.target / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        self.assertEqual(sum(item.get("kind") == "adaptive-decision" for item in events), 1)
        self.assertEqual(sum(item.get("kind") == "adaptive-decision-review" for item in events), 0)

    def test_fingerprint_is_recomputed_from_exact_evidence_not_caller_sha(self) -> None:
        policy = self.policy()
        first = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=self.decision_evidence(decision_id="decision-one-1234"))
        )
        same = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=self.decision_evidence(decision_id="decision-two-1234"))
        )
        changed = supervision_log.adaptive_decision_posture(
            policy,
            self.packet(
                policy,
                evidence=self.decision_evidence(decision_id="decision-three-1234", evidence_root="0" * 64),
            ),
        )
        self.assertEqual(first["decision_fingerprint"], same["decision_fingerprint"])
        self.assertNotEqual(first["decision_fingerprint"], changed["decision_fingerprint"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            supervision_log.parser().parse_args(
                [
                    "adaptive-decision-gate", "--target-thread", self.target,
                    "--decision-evidence", "decision.json", "--state-fingerprint", "f" * 64,
                ]
            )

    def test_software_factory_inline_change_requires_review_and_evaluation(self) -> None:
        policy = self.policy(target_class="software-factory")
        policy["permissions"]["allowlisted_skill_maintenance"] = True
        evidence = self.decision_evidence(target_class="software-factory")
        pending = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=evidence)
        )
        self.assertTrue(pending["independent_review_required"])
        self.assertEqual(pending["application_posture"], "automated-independent-review-required")
        review = self.normalized_review(policy, evidence)
        applied = supervision_log.adaptive_decision_posture(
            policy, self.packet(policy, evidence=evidence, review=review)
        )
        self.assertTrue(applied["application_authorized"])
        bad = copy.deepcopy(review)
        bad["evaluator_id"] = bad["reviewer_id"]
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "roles are not distinct"):
            supervision_log.adaptive_decision_posture(
                policy, self.packet(policy, evidence=evidence, review=bad)
            )
        self_review = copy.deepcopy(review)
        self_review["reviewer_id"] = self.target
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "not independently owned"):
            supervision_log.adaptive_decision_posture(
                policy, self.packet(policy, evidence=evidence, review=self_review)
            )

    def test_structural_target_class_change_requires_evidence_and_is_append_only(self) -> None:
        initial = self.init()
        initial_permissions = copy.deepcopy(initial["permissions"])
        first_history = (self.root / self.target / "policy-history.jsonl").read_bytes()
        adjusted = self.adjust(
            "--adaptive-target-class", "software-factory",
            "--adaptive-decision-mode", "reviewed-autonomous",
        )
        self.assertEqual(adjusted["permissions"], initial_permissions)
        self.assertEqual(adjusted["adaptive_decision_control"]["target_class"], "software-factory")
        self.assertTrue((self.root / self.target / "policy-history.jsonl").read_bytes().startswith(first_history))

    def test_status_reports_adaptive_and_legacy_human_requests_truthfully(self) -> None:
        policy = self.policy("recommend")
        evidence = self.decision_evidence()
        review = self.normalized_review(policy, evidence)
        result = supervision_log.adaptive_decision_posture(
            policy,
            self.packet(policy, evidence=evidence, review=review, request_human_input=True),
        )
        events = [
            {"kind": "adaptive-decision", **result},
            {"kind": "decision", "decision_id": "legacy-decision-1234", "human_input_requested_at": "2026-08-09T00:00:00+00:00", "policy_sha256": "0" * 64},
        ]
        status = supervision_log.adaptive_status_projection(policy, events)
        self.assertEqual(status["human_request_count"], 2)
        self.assertEqual(status["adaptive_human_request_count"], 1)
        self.assertEqual(status["legacy_decision_human_request_count"], 1)

    def test_exact_decision_source_rejects_tamper_duplicate_keys_and_scope_escape(self) -> None:
        policy = self.policy()
        value = self.decision_evidence()
        value["source_root"] = "0" * 64
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "source root"):
            supervision_log.validate_adaptive_decision_evidence(value, policy=policy)
        escaped = self.decision_evidence()
        escaped["affected_scope"][0]["path"] = f"{self.repository_root}/../outside.py"  # type: ignore[index]
        material = dict(escaped)
        material.pop("source_root")
        escaped["source_root"] = supervision_log.digest(material)
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "normalized"):
            supervision_log.validate_adaptive_decision_evidence(escaped, policy=policy)
        duplicate_path = self.root / "duplicate.json"
        duplicate_path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "Duplicate"):
            supervision_log.load_bounded_canonical_json(
                str(duplicate_path), label="adaptive decision evidence", maximum_bytes=1024
            )

    def test_cli_and_docs_expose_decision_evidence_signed_review_and_input_avoidance(self) -> None:
        parsed = supervision_log.parser().parse_args(
            [
                "adaptive-decision-gate", "--target-thread", self.target,
                "--decision-evidence", "decision.json",
            ]
        )
        self.assertEqual(parsed.command, "adaptive-decision-gate")
        text = MODULE_PATH.parent.parent.joinpath("SKILL.md").read_text(encoding="utf-8")
        text += MODULE_PATH.parent.parent.joinpath("references", "supervision-policy.md").read_text(encoding="utf-8")
        for token in (
            "adaptive-decision-review", "--decision-evidence", "--review-json",
            "adaptive-target-class", "full-autonomous",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
