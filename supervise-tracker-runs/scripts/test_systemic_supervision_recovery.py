#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "systemic_supervision_recovery_v1.json"
)
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = Path(__file__).resolve().parents[2]


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
        self.assertEqual(git("merge-base", "--is-ancestor", source["shared_predecessor_commit"], source["accepted_source_commit"]).returncode, 0)
        self.assertEqual(git("merge-base", "--is-ancestor", source["automatic_currentness_commit"], source["accepted_source_commit"]).returncode, 0)

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
        self.assertEqual(release["identity_source"], "release-owner-status")
        self.assertEqual(release["source_commit"], self.fixture["source_adaptation"]["accepted_source_commit"])
        self.assertRegex(release["release_id"], r"^[0-9a-f]{12}-[0-9a-f]{12}$")
        self.assertRegex(release["acceptance_record_id"], r"^RELEASE-ACCEPTANCE-[0-9]+$")
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
            git("rev-parse", f'{history["rejected_candidate_commit"]}^{{tree}}').stdout.strip(),
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
        self.assertNotIn("caller", self.fixture["active_release_baseline"]["identity_source"])

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


if __name__ == "__main__":
    unittest.main()
