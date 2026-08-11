#!/usr/bin/env python3
"""Focused Block 9 target-owner cutover and recovery contract."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_cutover as cutover  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKER_PATH = (
    REPO_ROOT
    / "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
)


class CandidateCutoverContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="software-factory-block9-target-"
        )
        self.target = Path(self.temporary.name).resolve()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Block 9 Test Owner")
        self._git("config", "user.email", "block9@local.invalid")
        bundle = cutover.load_accepted_bundle()
        _, incumbent = cutover._artifact_file(bundle, "incumbent")
        (self.target / "stream_export.py").write_bytes(incumbent)
        (self.target / "staged.txt").write_text("base staged\n", encoding="utf-8")
        (self.target / "unstaged.txt").write_text("base unstaged\n", encoding="utf-8")
        self._git("add", "--", "stream_export.py", "staged.txt", "unstaged.txt")
        self._git("commit", "-q", "-m", "Create incumbent target")
        self.mission_root = "a" * 64
        self.policy_root = "b" * 64
        self.event_head_root = "c" * 64
        self.cutover_owner_id = "owner-target-production"
        self.structural_change = False
        self.owner_calls = 0
        self.mutate_on_owner_call = None

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            [cutover.GIT, "-C", str(self.target), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _context_owner(self) -> dict[str, object]:
        self.owner_calls += 1
        target_raw = (self.target / "stream_export.py").read_bytes()
        tracker_raw = TRACKER_PATH.read_bytes()
        head = self._git("rev-parse", "HEAD")
        value = {
            "schema_version": 1,
            "kind": "candidate-cutover-current-context",
            "mission_root": self.mission_root,
            "policy_root": self.policy_root,
            "event_head_root": self.event_head_root,
            "cutover_owner_id": "owner-target-production",
            "structural_change": self.structural_change,
            "target_repository_root": str(self.target),
            "target_head": head,
            "target_state_root": cutover._target_state_root(
                head, "stream_export.py", target_raw
            ),
            "affected_path": "stream_export.py",
            "affected_content_root": cutover.bytes_root(target_raw),
            "tracker_path": str(TRACKER_PATH.resolve(strict=True)),
            "tracker_sha256": cutover.bytes_root(tracker_raw),
            "block9_contract_root": cutover._block9_contract_root(tracker_raw),
        }
        if self.mutate_on_owner_call == self.owner_calls:
            (self.target / "stream_export.py").write_text(
                "# changed during currentness resolution\n", encoding="utf-8"
            )
        return value

    def _apply(self, *, failpoint: Optional[str] = None) -> dict[str, object]:
        return cutover.apply_cutover(
            self.target,
            TRACKER_PATH,
            self._context_owner,
            failpoint=failpoint,
        )

    def _commit_count(self) -> int:
        return int(self._git("rev-list", "--count", "HEAD"))

    def test_exact_accepted_handoff_and_independent_review_are_current(self) -> None:
        bundle = cutover.load_accepted_bundle()
        self.assertEqual(bundle["handoff"]["handoff_root"], cutover.EXPECTED_HANDOFF_ROOT)
        self.assertEqual(bundle["lane_head"]["head_root"], cutover.EXPECTED_LANE_HEAD_ROOT)
        self.assertEqual(
            cutover._block9_contract_root(TRACKER_PATH.read_bytes()),
            cutover.EXPECTED_BLOCK9_CONTRACT_ROOT,
        )
        changed = copy.deepcopy(bundle)
        changed["review"]["review_disposition"] = "inconclusive"
        with self.assertRaisesRegex(cutover.CutoverError, "accepted candidate handoff"):
            cutover.validate_cutover_bundle(changed)

    def test_winner_cuts_over_once_preserves_history_dirty_work_and_resumes(self) -> None:
        (self.target / "staged.txt").write_text("kept staged\n", encoding="utf-8")
        self._git("add", "--", "staged.txt")
        (self.target / "unstaged.txt").write_text("kept unstaged\n", encoding="utf-8")
        (self.target / "untracked.txt").write_text("kept untracked\n", encoding="utf-8")
        dirty_before = self._git(
            "status", "--short", "--", "staged.txt", "unstaged.txt", "untracked.txt"
        )
        result = self._apply()
        self.assertEqual(result["action"], "cutover-applied")
        self.assertFalse(result["duplicate"])
        self.assertTrue(result["single_authority"])
        self.assertTrue(result["candidate_authoritative"])
        self.assertFalse(result["incumbent_authoritative"])
        self.assertFalse(result["manual_resume_required"])
        self.assertEqual(self._commit_count(), 3)
        dirty_after = self._git(
            "status", "--short", "--", "staged.txt", "unstaged.txt", "untracked.txt"
        )
        self.assertEqual(dirty_after, dirty_before)
        bundle = cutover.load_accepted_bundle()
        _, incumbent = cutover._artifact_file(bundle, "incumbent")
        _, candidate = cutover._artifact_file(bundle, "winner")
        self.assertEqual((self.target / "stream_export.py").read_bytes(), candidate)
        self.assertEqual(
            subprocess.run(
                [cutover.GIT, "-C", str(self.target), "show", "HEAD~2:stream_export.py"],
                check=True,
                capture_output=True,
            ).stdout,
            incumbent,
        )
        fixture = cutover._load_json(cutover.CUTOVER_FIXTURE_PATH)
        self.assertEqual(
            result["proof_reconciliation"]["invalidated_proof_ids"],
            fixture["expected_invalidated_proof_ids"],
        )
        self.assertEqual(
            result["proof_reconciliation"]["preserved_proof_ids"],
            fixture["expected_preserved_proof_ids"],
        )
        head = self._git("rev-parse", "HEAD")
        duplicate = self._apply()
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["resume_token"], result["resume_token"])
        self.assertEqual(self._git("rev-parse", "HEAD"), head)
        claimed = cutover.claim_resume(self.target, result["resume_token"])
        self.assertTrue(claimed["execute"])
        self.assertFalse(claimed["duplicate"])
        claim_head = self._git("rev-parse", "HEAD")
        claimed_again = cutover.claim_resume(self.target, result["resume_token"])
        self.assertFalse(claimed_again["execute"])
        self.assertTrue(claimed_again["duplicate"])
        self.assertEqual(self._git("rev-parse", "HEAD"), claim_head)
        self.assertEqual(
            self._git(
                "status", "--short", "--", "staged.txt", "unstaged.txt", "untracked.txt"
            ),
            dirty_before,
        )

    def test_stale_target_or_changed_policy_rejects_without_another_cutover(self) -> None:
        initial = self._git("rev-parse", "HEAD")
        (self.target / "stream_export.py").write_text("# stale incumbent\n", encoding="utf-8")
        with self.assertRaisesRegex(cutover.CutoverError, "incumbent target bytes are stale"):
            self._apply()
        self.assertEqual(self._git("rev-parse", "HEAD"), initial)
        self._git("checkout", "-q", "--", "stream_export.py")
        result = self._apply()
        self.policy_root = "d" * 64
        with self.assertRaisesRegex(cutover.CutoverError, "cutover currentness policy_root"):
            self._apply()
        self.assertEqual(self._commit_count(), 3)
        self.assertTrue(result["candidate_authoritative"])

    def test_context_change_at_write_boundary_rejects(self) -> None:
        initial = self._git("rev-parse", "HEAD")
        self.mutate_on_owner_call = 2
        with self.assertRaisesRegex(
            cutover.CutoverError, "context changed|incumbent target bytes are stale"
        ):
            self._apply()
        self.assertEqual(self._git("rev-parse", "HEAD"), initial)

    def test_unowned_context_or_control_directory_substitution_rejects(self) -> None:
        with self.assertRaisesRegex(cutover.CutoverError, "normal target owner"):
            cutover.apply_cutover(
                self.target,
                TRACKER_PATH,
                lambda: self._context_owner(),
            )
        external = self.target / "external-control"
        external.mkdir()
        (self.target / ".software-factory").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(cutover.CutoverError, "control directory"):
            self._apply()

    def test_structural_change_routes_to_block8_without_target_write(self) -> None:
        initial = self._git("rev-parse", "HEAD")
        before = (self.target / "stream_export.py").read_bytes()
        self.structural_change = True
        result = self._apply()
        self.assertEqual(result["action"], "route-block-8")
        self.assertFalse(result["application_authorized"])
        self.assertEqual(self._git("rev-parse", "HEAD"), initial)
        self.assertEqual((self.target / "stream_export.py").read_bytes(), before)

    def test_precommit_interruptions_restore_exact_incumbent(self) -> None:
        bundle = cutover.load_accepted_bundle()
        _, incumbent = cutover._artifact_file(bundle, "incumbent")
        for failpoint in ("after-write", "before-ref-update"):
            with self.subTest(failpoint=failpoint):
                initial = self._git("rev-parse", "HEAD")
                with self.assertRaisesRegex(cutover.CutoverError, "interruption"):
                    self._apply(failpoint=failpoint)
                self.assertEqual(self._git("rev-parse", "HEAD"), initial)
                self.assertEqual((self.target / "stream_export.py").read_bytes(), incumbent)
                self.assertFalse((self.target / cutover.STATE_RELATIVE).exists())

    def test_postcommit_interruption_resumes_effect_without_reintegration(self) -> None:
        with self.assertRaisesRegex(cutover.CutoverError, "after target-owner commit"):
            self._apply(failpoint="after-ref-update")
        self.assertEqual(self._commit_count(), 2)
        integration = self._git("rev-parse", "HEAD")
        result = self._apply()
        self.assertEqual(result["integration_commit"], integration)
        self.assertEqual(self._commit_count(), 3)
        self.assertEqual(result["next_action"], "continue-block-9-from-current-effect")

    def test_outcome_interruption_reuses_integration_and_effect(self) -> None:
        with self.assertRaisesRegex(cutover.CutoverError, "before outcome commit"):
            self._apply(failpoint="before-outcome-commit")
        integration = self._git("rev-parse", "HEAD")
        self.assertEqual(self._commit_count(), 2)
        result = self._apply()
        self.assertEqual(result["integration_commit"], integration)
        self.assertEqual(self._commit_count(), 3)

    def test_failed_current_effect_keeps_decision_open_without_resume(self) -> None:
        with mock.patch.object(
            cutover,
            "_run_observable_effect",
            side_effect=cutover.CutoverError("current target effect differs"),
        ):
            with self.assertRaisesRegex(cutover.CutoverError, "current target effect differs"):
                self._apply()
        state = cutover._load_json(self.target / cutover.STATE_RELATIVE)
        self.assertEqual(state["status"], "effect-pending")
        self.assertIsNone(state["resume_token"])
        self.assertEqual(self._commit_count(), 2)
        result = self._apply()
        self.assertFalse(result["manual_resume_required"])
        self.assertEqual(self._commit_count(), 3)

    def test_changed_handoff_or_proof_graph_rejects(self) -> None:
        bundle = cutover.load_accepted_bundle()
        changed = copy.deepcopy(bundle)
        changed["handoff"]["cutover_preconditions"] = ["block-9"]
        with self.assertRaisesRegex(cutover.CutoverError, "accepted candidate handoff"):
            cutover.validate_cutover_bundle(changed)
        fixture = cutover._load_json(cutover.CUTOVER_FIXTURE_PATH)
        fixture["proof_records"].append(copy.deepcopy(fixture["proof_records"][0]))
        with self.assertRaisesRegex(cutover.CutoverError, "proof ID repeats"):
            cutover.reconcile_proof(fixture, bundle["handoff"])
        cyclic = cutover._load_json(cutover.CUTOVER_FIXTURE_PATH)
        cyclic["proof_records"][0]["depends_on"] = ["proof-incumbent-descendant"]
        with self.assertRaisesRegex(cutover.CutoverError, "dependency cycle"):
            cutover.reconcile_proof(cyclic, bundle["handoff"])


if __name__ == "__main__":
    unittest.main()
