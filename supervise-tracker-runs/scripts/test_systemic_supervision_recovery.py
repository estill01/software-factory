#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import io
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "systemic_supervision_recovery_v1.json"
)
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = Path(__file__).resolve().parents[2]
RELEASE_ROOT = Path.home() / ".codex" / "software-factory-releases"
INSTALL_ROOT = Path.home() / ".codex" / "skills"
RELEASE_OWNER_PATH = REPOSITORY / "scripts" / "skill_release.py"
RELEASE_OWNER_SPEC = importlib.util.spec_from_file_location(
    "systemic_recovery_release_owner", RELEASE_OWNER_PATH
)
assert RELEASE_OWNER_SPEC is not None and RELEASE_OWNER_SPEC.loader is not None
release_owner = importlib.util.module_from_spec(RELEASE_OWNER_SPEC)
RELEASE_OWNER_SPEC.loader.exec_module(release_owner)
RECOVERY_PATH = Path(__file__).with_name("systemic_recovery.py")
RECOVERY_SPEC = importlib.util.spec_from_file_location(
    "systemic_recovery_test_owner", RECOVERY_PATH
)
assert RECOVERY_SPEC is not None and RECOVERY_SPEC.loader is not None
systemic_recovery = importlib.util.module_from_spec(RECOVERY_SPEC)
RECOVERY_SPEC.loader.exec_module(systemic_recovery)
SUPERVISION_LOG_PATH = Path(__file__).with_name("supervision_log.py")
SUPERVISION_LOG_SPEC = importlib.util.spec_from_file_location(
    "systemic_recovery_supervision_log", SUPERVISION_LOG_PATH
)
assert SUPERVISION_LOG_SPEC is not None and SUPERVISION_LOG_SPEC.loader is not None
supervision_log = importlib.util.module_from_spec(SUPERVISION_LOG_SPEC)
SUPERVISION_LOG_SPEC.loader.exec_module(supervision_log)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPOSITORY), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def git_blob_sha256(revision: str, path: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(REPOSITORY), "show", f"{revision}:{path}"],
        check=True,
        capture_output=True,
    )
    import hashlib

    return hashlib.sha256(process.stdout).hexdigest()


def release_owner_baseline(release_id: str) -> tuple[dict, dict]:
    manifest = release_owner.read_manifest(RELEASE_ROOT, release_id)
    acceptance = release_owner.accepted_release_record(RELEASE_ROOT, release_id)
    assert acceptance is not None
    activations = [
        item for item in release_owner.history(RELEASE_ROOT)
        if item["release_id"] == release_id
    ]
    if not activations:
        raise AssertionError("Frozen release lacks canonical activation history")
    activation = activations[-1]
    status = release_owner.status(
        type(
            "StatusArgs",
            (),
            {"release_root": str(RELEASE_ROOT), "install_root": str(INSTALL_ROOT)},
        )()
    )
    derived = {
        "identity_source": "release-owner-status",
        "release_id": release_id,
        "source_commit": manifest["source_commit"],
        "acceptance_record_id": acceptance["record_id"],
        "activation_record_id": activation["record_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "candidate_root_sha256": manifest["candidate_root_sha256"],
        "verification_root_sha256": activation["post_swap_reload_root_sha256"],
        "installed_roots": {
            name: record["content_root_sha256"]
            for name, record in manifest["skills"].items()
        },
    }
    if status["active_release_id"] == release_id:
        derived["release_owner_state_root_sha256"] = status[
            "release_owner_state_root_sha256"
        ]
    return derived, status


class SystemicSupervisionRecoveryBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = FIXTURE_PATH.read_text(encoding="utf-8")
        cls.fixture = json.loads(cls.raw)

    def test_fixture_is_content_minimized_and_owner_bound(self) -> None:
        self.assertEqual(
            self.fixture["kind"],
            "software-factory-systemic-supervision-recovery-regression",
        )
        incident = self.fixture["incident"]
        self.assertEqual(incident["cause_owner"], "software-factory")
        self.assertEqual(incident["cause_authority"], "canonical-owner-evidence")
        self.assertEqual(incident["required_target_posture"], "in-progress")
        self.assertFalse(incident["manual_resume_required"])
        self.assertFalse(incident["human_input_required"])
        self.assertTrue(incident["safe_frontier"])
        self.assertEqual(
            self.fixture["owner_map"],
            {
                "classification_and_recovery_history": "supervision-event-owner",
                "repair": "allowlisted-fix-executor",
                "candidate_acceptance": "independent-exact-reviewer",
                "release_activation": "software-factory-release-owner",
                "role_refresh": "stable-channel-role-refresh-owner",
                "range_currentness": "implementation-range-owner",
                "tracker_reconciliation": "target-implementation-owner",
                "target_wake": "thread-route-owner",
                "effectiveness": "independent-effectiveness-reviewer",
            },
        )
        for forbidden in ("patent", "/users/", "prompt text", "finding set"):
            self.assertNotIn(forbidden, self.raw.lower())

    def test_fixture_freezes_exact_source_adaptation(self) -> None:
        source = self.fixture["source_adaptation"]
        for field in (
            "accepted_source_commit",
            "automatic_currentness_commit",
            "shared_predecessor_commit",
        ):
            self.assertRegex(source[field], COMMIT)
        self.assertEqual(
            source["disposition"], "content-minimized-control-plane-adaptation"
        )
        self.assertEqual(
            git(
                "merge-base",
                "--is-ancestor",
                source["shared_predecessor_commit"],
                source["accepted_source_commit"],
            ).returncode,
            0,
        )
        self.assertEqual(
            git(
                "merge-base",
                "--is-ancestor",
                source["automatic_currentness_commit"],
                source["accepted_source_commit"],
            ).returncode,
            0,
        )

    def test_fixture_freezes_complete_owner_derived_release_baseline(self) -> None:
        baseline = self.fixture["integration_baseline"]
        release = self.fixture["active_release_baseline"]
        self.assertEqual(baseline["branch"], "codex/automatic-release-monitor-refresh")
        self.assertEqual(baseline["tracker_status_before_implementation"], "planning")
        self.assertEqual(baseline["automatic_release_tracker_status"], "completed")
        self.assertEqual(
            git("rev-parse", f'{baseline["commit"]}^{{tree}}').stdout.strip(),
            baseline["tree"],
        )
        derived, current_status = release_owner_baseline(release["release_id"])
        self.assertEqual({key: release[key] for key in derived}, derived)
        self.assertEqual(
            release["source_commit"],
            self.fixture["source_adaptation"]["accepted_source_commit"],
        )
        self.assertRegex(release["release_id"], r"^[0-9a-f]{12}-[0-9a-f]{12}$")
        self.assertRegex(
            release["acceptance_record_id"], r"^RELEASE-ACCEPTANCE-[0-9]+$"
        )
        self.assertRegex(release["activation_record_id"], r"^ACTIVATION-[0-9]+$")
        for field in (
            "manifest_sha256",
            "candidate_root_sha256",
            "verification_root_sha256",
            "release_owner_state_root_sha256",
        ):
            self.assertRegex(release[field], SHA256)
        self.assertEqual(
            set(release["installed_roots"]),
            {
                "author-implementation-trackers",
                "implement-tracker-blocks",
                "supervise-tracker-runs",
            },
        )
        for root in release["installed_roots"].values():
            self.assertRegex(root, SHA256)
        if current_status["active_release_id"] == release["release_id"]:
            self.assertEqual(current_status["source_commit"], release["source_commit"])
            self.assertEqual(
                current_status["manifest_sha256"], release["manifest_sha256"]
            )
            self.assertEqual(
                current_status["acceptance_record"]["record_id"],
                release["acceptance_record_id"],
            )
            self.assertEqual(
                current_status["activation_record"]["record_id"],
                release["activation_record_id"],
            )

    def test_caller_supplied_release_identity_cannot_replace_owner_history(self) -> None:
        release = self.fixture["active_release_baseline"]
        with self.assertRaises(release_owner.ReleaseError):
            release_owner_baseline("f" * 12 + "-" + "e" * 12)
        derived, _status = release_owner_baseline(release["release_id"])
        tampered = dict(derived)
        tampered["manifest_sha256"] = "f" * 64
        self.assertNotEqual(tampered, derived)

    def test_fixture_preserves_accepted_and_rejected_bytes(self) -> None:
        history = self.fixture["immutable_history"]
        source = self.fixture["source_adaptation"]
        self.assertEqual(
            git_blob_sha256(
                history["accepted_tracker_commit"],
                "docs/software-factory-automatic-release-and-supervisor-refresh-implementation-tracker.md",
            ),
            history["accepted_tracker_sha256"],
        )
        self.assertEqual(
            git_blob_sha256(
                source["accepted_source_commit"],
                "supervise-tracker-runs/scripts/supervision_log.py",
            ),
            history["accepted_helper_sha256"],
        )
        self.assertEqual(
            git(
                "rev-parse", f'{history["rejected_candidate_commit"]}^{{tree}}'
            ).stdout.strip(),
            history["rejected_candidate_tree"],
        )
        self.assertEqual(
            git_blob_sha256(
                history["rejected_candidate_commit"],
                "supervise-tracker-runs/scripts/supervision_log.py",
            ),
            history["rejected_helper_sha256"],
        )
        self.assertNotEqual(
            git(
                "merge-base",
                "--is-ancestor",
                history["rejected_candidate_commit"],
                source["accepted_source_commit"],
                check=False,
            ).returncode,
            0,
        )

    def test_fixture_rejects_route_or_caller_identity_as_cause_or_currentness(self) -> None:
        self.assertEqual(
            self.fixture["incident"]["cause_authority"],
            "canonical-owner-evidence",
        )
        self.assertEqual(
            self.fixture["currentness"]["release"],
            "release-owner-derived",
        )
        self.assertNotIn("route", self.fixture["incident"]["cause_authority"])
        self.assertNotIn(
            "caller", self.fixture["active_release_baseline"]["identity_source"]
        )

    def test_fixture_declares_the_complete_owner_sequence(self) -> None:
        self.assertEqual(
            self.fixture["expected_transitions"],
            [
                "detected",
                "classified",
                "contained",
                "repair-routed",
                "candidate-current",
                "candidate-accepted",
                "release-active",
                "roles-refreshed",
                "range-current",
                "tracker-reconciled",
                "wake-routed",
                "target-advanced",
                "effectiveness-reviewed",
            ],
        )


class SystemicRecoveryClassificationTests(unittest.TestCase):
    target = "systemic-recovery-target-1234"
    reviewer = "systemic-recovery-reviewer-1234"
    base_reviewer = "systemic-recovery-base-reviewer-1234"

    def policy(self) -> dict:
        return {
            "target_thread_id": self.target,
            "policy_sha256": "a" * 64,
            "mission_binding": {"mission_root": "b" * 64},
            "runtime": {
                "watcher_thread_id": "systemic-recovery-watcher-1234",
                "reviewer_thread_id": self.reviewer,
                "base_reviewer_thread_id": self.base_reviewer,
                "fix_executor_thread_id": "systemic-recovery-fixer-1234",
            },
        }

    def incident(self, owner_class: str = "software-factory-owned") -> dict:
        subjects = [
            {"subject": "current-supervision-helper", "owner_class": owner_class}
        ]
        return {
            "schema_version": 1,
            "record_id": "EVT-000001",
            "record_sha256": "c" * 64,
            "incident_id": "INC-SYSTEMIC-RECOVERY-1234",
            "status": "detected",
            "severity": "high",
            "failure_mode": {
                "failure_mode_id": "FM-FACTORY-CONTROL-PLANE-1234",
                "owner_class": owner_class,
                "failed_owner": "current-supervision-helper",
                "failed_contract": "canonical-owner-currentness",
                "observed_revision": "diagnostic-source-revision",
                "accepted_revision": "current-accepted-source",
                "recovery_trigger": "owner-currentness-mismatch",
                "safe_frontier": ["preserved-current-block"],
                "ownership_subjects": subjects,
            },
        }

    def packet(self) -> dict:
        hypothesis = {
            "causal_mechanism": "bounded-treatment-mechanism",
            "changed_levers": ["primary-observable-lever"],
            "expected_effect": "material-outcome-improvement",
        }
        return {
            "schema_version": 1,
            "kind": "outcome-effectiveness-admission",
            "implementation_owner_id": self.target,
            "primary_observable_outcome": "independent-outcome-disposition",
            "baseline_outcomes": [
                {
                    "source_record": "OUTCOME-BASELINE-0001",
                    "source_sha256": "d" * 64,
                    "reviewer_id": self.base_reviewer,
                    "disposition": "revise",
                    "material_findings": ["finding-alpha", "finding-beta"],
                },
                {
                    "source_record": "OUTCOME-BASELINE-0002",
                    "source_sha256": "e" * 64,
                    "reviewer_id": self.base_reviewer,
                    "disposition": "revise",
                    "material_findings": ["finding-beta", "finding-alpha"],
                },
            ],
            "prior_treatment_hypothesis": hypothesis,
            "candidate_treatment_hypothesis": copy.deepcopy(hypothesis),
            "effectiveness_criterion": {
                "criterion": "disposition-and-finding-reduction",
                "target_disposition": "accepted",
                "minimum_findings_removed": 1,
            },
            "current_outcome": None,
        }

    def test_factory_owned_incident_preserves_mission_and_opens_recovery(self) -> None:
        incident = self.incident()
        result = systemic_recovery.classify_recovery(
            incident=incident,
            incident_head=incident,
            policy=self.policy(),
        )
        self.assertEqual(result["owner_class"], "software-factory-owned")
        self.assertEqual(result["required_target_posture"], "in-progress")
        self.assertFalse(result["manual_resume_required"])
        self.assertFalse(result["human_input_required"])
        self.assertEqual(result["next_action"], "open-software-factory-recovery")
        self.assertEqual(result["safe_frontier"], ["preserved-current-block"])
        self.assertRegex(result["recovery_id"], r"^RECOVERY-[0-9a-f]{24}$")

    def test_target_reserved_and_mixed_owners_do_not_open_whole_run_repair(self) -> None:
        target = self.incident("target-owned")
        target_result = systemic_recovery.classify_recovery(
            incident=target, incident_head=target, policy=self.policy()
        )
        self.assertEqual(target_result["next_action"], "route-target-owned-subjects")
        reserved = self.incident("reserved-external")
        reserved_result = systemic_recovery.classify_recovery(
            incident=reserved, incident_head=reserved, policy=self.policy()
        )
        self.assertEqual(
            reserved_result["next_action"],
            "route-reserved-subjects-to-decision-owner",
        )
        mixed = self.incident("mixed")
        mixed["failure_mode"]["ownership_subjects"] = [
            {
                "subject": "current-supervision-helper",
                "owner_class": "software-factory-owned",
            },
            {"subject": "target-local-defect", "owner_class": "target-owned"},
        ]
        mixed_result = systemic_recovery.classify_recovery(
            incident=mixed, incident_head=mixed, policy=self.policy()
        )
        self.assertEqual(
            mixed_result["factory_subjects"], ["current-supervision-helper"]
        )
        self.assertEqual(
            mixed_result["next_action"], "split-and-route-subjects-by-owner"
        )

    def test_route_text_or_caller_owner_cannot_become_cause_authority(self) -> None:
        incident = self.incident()
        del incident["failure_mode"]["owner_class"]
        incident["action"] = "Route says the Factory owns this defect."
        with self.assertRaisesRegex(
            systemic_recovery.RecoveryError, "canonical failure owner evidence"
        ):
            systemic_recovery.classify_recovery(
                incident=incident, incident_head=incident, policy=self.policy()
            )
        stale = self.incident()
        stale_head = copy.deepcopy(stale)
        stale_head["record_id"] = "EVT-000002"
        stale_head["record_sha256"] = "f" * 64
        stale_head["incident_id"] = "INC-OTHER-RECOVERY-1234"
        with self.assertRaisesRegex(
            systemic_recovery.RecoveryError, "history differs"
        ):
            systemic_recovery.classify_recovery(
                incident=stale, incident_head=stale_head, policy=self.policy()
            )

    def test_unchanged_outcome_and_same_hypothesis_holds_next_effect(self) -> None:
        result = systemic_recovery.evaluate_outcome_effectiveness(
            self.packet(), policy=self.policy()
        )
        self.assertTrue(result["outcome_unchanged"])
        self.assertTrue(result["same_treatment_hypothesis"])
        self.assertEqual(result["status"], "outcome-unchanged")
        self.assertEqual(result["effectiveness"], "ineffective")
        self.assertEqual(result["candidate_posture"], "diagnostic")
        self.assertFalse(result["effect_allowed"])
        self.assertEqual(
            result["next_wake_triggers"],
            list(systemic_recovery.NEXT_EFFECTIVENESS_TRIGGERS),
        )

    def test_process_proof_does_not_clear_hold_but_different_treatment_does(self) -> None:
        packet = self.packet()
        packet["process_proof"] = {"tests": "passed"}
        with self.assertRaisesRegex(
            systemic_recovery.RecoveryError, "packet shape differs"
        ):
            systemic_recovery.evaluate_outcome_effectiveness(
                packet, policy=self.policy()
            )
        different = self.packet()
        different["candidate_treatment_hypothesis"]["changed_levers"] = [
            "materially-different-lever"
        ]
        result = systemic_recovery.evaluate_outcome_effectiveness(
            different, policy=self.policy()
        )
        self.assertFalse(result["same_treatment_hypothesis"])
        self.assertTrue(result["effect_allowed"])
        self.assertEqual(result["status"], "treatment-admitted")

    def test_later_outcome_exposes_baseline_current_delta(self) -> None:
        packet = self.packet()
        packet["candidate_treatment_hypothesis"]["changed_levers"] = [
            "materially-different-lever"
        ]
        packet["current_outcome"] = {
            "source_record": "OUTCOME-CURRENT-0003",
            "source_sha256": "f" * 64,
            "reviewer_id": self.reviewer,
            "disposition": "accepted",
            "material_findings": ["finding-beta"],
        }
        result = systemic_recovery.evaluate_outcome_effectiveness(
            packet, policy=self.policy()
        )
        self.assertEqual(result["effectiveness"], "effective")
        self.assertEqual(result["material_findings_removed"], ["finding-alpha"])
        self.assertEqual(result["material_findings_added"], [])
        self.assertTrue(result["criterion_met"])

    def test_installed_role_contract_uses_the_executable_gates(self) -> None:
        skill = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(
            encoding="utf-8"
        )
        policy = (
            Path(__file__).resolve().parents[1]
            / "references"
            / "supervision-policy.md"
        ).read_text(encoding="utf-8")
        for text in (skill, policy):
            normalized = " ".join(text.split())
            self.assertIn("outcome-effectiveness-gate", normalized)
            self.assertIn("software-factory-recovery-classify", normalized)
            self.assertIn("effect_allowed=false", normalized)
            self.assertIn("materially different treatment", normalized)
            self.assertIn("manual Resume", normalized)
        changed_contract = policy[
            policy.index("Before another consequential corrective effect"):
            policy.index("Skill-maintenance modes are:")
        ]
        self.assertNotIn("patent", changed_contract.lower())


class SystemicRecoveryOwnerCommandTests(unittest.TestCase):
    target = "systemic-recovery-cli-target-1234"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run_cli(
            "init",
            "--target-thread",
            self.target,
            "--target-label",
            "Systemic recovery CLI target",
            "--watcher-thread",
            "systemic-recovery-cli-watcher-1234",
            "--reviewer-thread",
            "systemic-recovery-cli-reviewer-1234",
            "--base-reviewer-thread",
            "systemic-recovery-cli-base-reviewer-1234",
            "--fix-executor-thread",
            "systemic-recovery-cli-fixer-1234",
            "--mission-source-class",
            "tracker",
            "--mission-source-record",
            "tracker:systemic-recovery-cli",
            "--mission-source-sha256",
            "a" * 64,
        )
        incident = self.run_cli(
            "record",
            "--target-thread",
            self.target,
            "--kind",
            "incident",
            "--incident-id",
            "INC-SYSTEMIC-CLI-1234",
            "--status",
            "detected",
            "--severity",
            "high",
            "--category",
            "software-factory-recovery",
            "--summary",
            "A current owner incompatibility blocks the target.",
            "--resolution-owner",
            "supervisor",
            "--user-action-required",
            "no",
            "--failure-mode",
            "--failure-mode-id",
            "FM-FACTORY-CONTROL-PLANE-1234",
            "--failure-layer",
            "control-plane",
            "--failure-mechanism",
            "The installed owner differs from the accepted owner.",
            "--failure-trigger",
            "Current helper rejects an accepted owner record.",
            "--failure-effect",
            "The target cannot continue its current Block.",
            "--failure-detection",
            "Compare current and accepted owner identities.",
            "--failure-correction",
            "Repair through the current Software Factory owner.",
            "--failure-recurrence-invariant",
            "Only one current owner recovery remains active.",
            "--failure-human-scheduling-leak",
            "no",
            "--failure-owner-class",
            "software-factory-owned",
            "--failure-failed-owner",
            "current-supervision-helper",
            "--failure-failed-contract",
            "canonical-owner-currentness",
            "--failure-observed-revision",
            "diagnostic-source-revision",
            "--failure-accepted-revision",
            "current-accepted-source",
            "--failure-recovery-trigger",
            "owner-currentness-mismatch",
            "--failure-safe-frontier",
            "preserved-current-block",
            "--failure-owner-subject",
            "current-supervision-helper=software-factory-owned",
        )
        self.incident_record = incident["record"]

    def run_cli(self, *arguments: str) -> dict:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), *arguments]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            args.func(args)
        return json.loads(output.getvalue())

    def test_deduplicated_owner_command_appends_classification_and_hold(self) -> None:
        classified = self.run_cli(
            "software-factory-recovery-classify",
            "--target-thread",
            self.target,
            "--incident-id",
            "INC-SYSTEMIC-CLI-1234",
            "--source-record",
            self.incident_record["record_id"],
        )
        self.assertFalse(classified["duplicate"])
        self.assertEqual(
            classified["record"]["classification"]["required_target_posture"],
            "in-progress",
        )
        packet = SystemicRecoveryClassificationTests().packet()
        packet["implementation_owner_id"] = self.target
        for outcome in packet["baseline_outcomes"]:
            outcome["reviewer_id"] = "systemic-recovery-cli-base-reviewer-1234"
        encoded = base64.b64encode(supervision_log.canonical(packet)).decode("ascii")
        held = self.run_cli(
            "outcome-effectiveness-gate",
            "--target-thread",
            self.target,
            "--incident-id",
            "INC-SYSTEMIC-CLI-1234",
            "--source-record",
            classified["record"]["record_id"],
            "--packet-base64",
            encoded,
        )
        self.assertFalse(held["duplicate"])
        self.assertFalse(
            held["record"]["effectiveness_gate"]["effect_allowed"]
        )
        duplicate = self.run_cli(
            "outcome-effectiveness-gate",
            "--target-thread",
            self.target,
            "--incident-id",
            "INC-SYSTEMIC-CLI-1234",
            "--source-record",
            held["record"]["record_id"],
            "--packet-base64",
            encoded,
        )
        self.assertTrue(duplicate["duplicate"])

if __name__ == "__main__":
    unittest.main()
