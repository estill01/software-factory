#!/usr/bin/env python3
"""Focused Block 9 reviewed target-owner cutover contract."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_cutover as cutover  # noqa: E402


SOURCE_TRACKER = (
    Path(__file__).resolve().parents[2]
    / "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
)


class CandidateCutoverContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="software-factory-block9-reviewed-target-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.target = self.root / "target"
        self.target.mkdir()
        self.supervision_root = self.root / "supervision"
        self.owner_id = "owner-target-production"
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Block 9 Test Owner")
        self._git("config", "user.email", "block9@local.invalid")
        bundle = cutover.load_accepted_bundle()
        _full, relative, incumbent = cutover._artifact_file(bundle, "incumbent")
        self.relative = relative
        (self.target / relative).write_bytes(incumbent)
        self.tracker = self.target / "tracker.md"
        self.tracker.write_bytes(SOURCE_TRACKER.read_bytes())
        control = self.target / ".software-factory"
        control.mkdir()
        self.proof_path = self.target / cutover.PROOF_RELATIVE
        proof = {
            "schema_version": 1,
            "kind": "target-proof-graph",
            "records": [
                {
                    "proof_id": "incumbent-focused-proof",
                    "subject_root": bundle["handoff"]["incumbent_root"],
                    "depends_on": [],
                    "currentness": "current",
                },
                {
                    "proof_id": "incumbent-descendant-proof",
                    "subject_root": "d" * 64,
                    "depends_on": ["incumbent-focused-proof"],
                    "currentness": "current",
                },
                {
                    "proof_id": "unaffected-proof",
                    "subject_root": "e" * 64,
                    "depends_on": [],
                    "currentness": "current",
                },
            ],
        }
        proof["graph_root"] = cutover.object_root(proof)
        self.proof_path.write_bytes(cutover._json_bytes(proof))
        (self.target / "staged.txt").write_text("base staged\n", encoding="utf-8")
        (self.target / "unstaged.txt").write_text("base unstaged\n", encoding="utf-8")
        self._git("add", "--", ".")
        self._git("commit", "-q", "-m", "Create exact incumbent target")
        self.base_head = self._git("rev-parse", "HEAD")
        self._init_supervision()
        self.private_key = self.root / "integration-review-private.pem"
        authority = self.root / "integration-authority"
        reviewers = authority / "reviewers"
        reviewers.mkdir(parents=True)
        self.public_key = reviewers / "software-factory-release-reviewer-v1.pem"
        openssl = str(cutover.TRUSTED_OPENSSL_PATH)
        subprocess.run(
            [openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                openssl,
                "pkey",
                "-in",
                str(self.private_key),
                "-pubout",
                "-out",
                str(self.public_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.public_key.chmod(0o444)
        reviewers.chmod(0o555)
        authority.chmod(0o555)
        self.addCleanup(lambda: reviewers.chmod(0o755))
        self.addCleanup(lambda: authority.chmod(0o755))
        self.public_key_sha = hashlib.sha256(self.public_key.read_bytes()).hexdigest()
        for name, value in (
            ("SUPERVISION_ROOT", self.supervision_root),
            ("REVIEWER_PUBLIC_KEY_PATH", self.public_key),
            ("REVIEWER_AUTHORITY_DIRECTORY", reviewers),
            ("REVIEWER_AUTHORITY_ROOT", authority),
            ("EXPECTED_REVIEWER_KEY_SHA256", self.public_key_sha),
        ):
            patcher = mock.patch.object(cutover, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _git(self, *args: str) -> str:
        return subprocess.run(
            [cutover.GIT, "-C", str(self.target), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def _init_supervision(self) -> None:
        module = cutover._supervision_module()
        source_text = "Implement this tracker."
        source_sha = hashlib.sha256(source_text.encode()).hexdigest()
        init = module.parser().parse_args(
            [
                "--root",
                str(self.supervision_root),
                "init",
                "--target-thread",
                self.owner_id,
                "--target-label",
                "Block 9 target owner",
                "--watcher-thread",
                "watcher-block9-target",
                "--reviewer-thread",
                "reviewer-block9-target",
                "--base-reviewer-thread",
                "base-reviewer-block9-target",
                "--fix-executor-thread",
                "fix-block9-target",
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "direct-block9-target",
                "--mission-source-sha256",
                source_sha,
                "--adaptive-target-repository-root",
                str(self.target),
            ]
        )
        with redirect_stdout(io.StringIO()):
            module.cmd_init(init)
        bind = module.parser().parse_args(
            [
                "--root",
                str(self.supervision_root),
                "implementation-range-bind",
                "--target-thread",
                self.owner_id,
                "--range-id",
                "block9-target-range",
                "--tracker",
                str(self.tracker),
                "--request-text",
                source_text,
                "--authority-source-record",
                "direct-block9-target",
                "--authority-source-sha256",
                source_sha,
            ]
        )
        with redirect_stdout(io.StringIO()):
            module.cmd_implementation_range_bind(bind)

    def _prepare(self) -> dict[str, object]:
        return cutover.prepare_cutover(self.target, self.tracker)

    def _signed_review(self, proposal_path: str, **changes: object) -> Path:
        proposal = cutover._rooted(
            cutover._load_json(Path(proposal_path)), "proposal_root", "cutover proposal"
        )
        review: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-candidate-cutover-integration-review",
            "record_id": f"block9-integration-{str(proposal['prepared_commit'])[:12]}",
            "proposal_root": proposal["proposal_root"],
            "prepared_commit": proposal["prepared_commit"],
            "integration_diff_root": proposal["integration_diff_root"],
            "handoff_root": proposal["handoff_root"],
            "target_repository_root": proposal["target_repository_root"],
            "target_head": proposal["target_head"],
            "target_state_root": proposal["target_state_root"],
            "tracker_program_root": proposal["tracker_program_root"],
            "proof_before_root": proposal["proof_reconciliation"]["before_graph_root"],
            "proof_after_root": proposal["proof_reconciliation"]["after_graph_root"],
            "reviewer_id": "software-factory-release-reviewer-v1",
            "review_disposition": "accepted",
            "finding_count": 0,
            "authority_key_sha256": self.public_key_sha,
            "observed_at": "2026-08-11T05:45:00.000000Z",
            "review_root": "",
            "signature_base64": "",
        }
        review.update(changes)
        material = {
            key: value
            for key, value in review.items()
            if key not in {"review_root", "signature_base64"}
        }
        review["review_root"] = cutover.object_root(material)
        signed = {key: value for key, value in review.items() if key != "signature_base64"}
        content = self.root / "integration-review-to-sign.json"
        signature = self.root / "integration-review.sig"
        content.write_bytes(cutover.canonical(signed))
        subprocess.run(
            [
                str(cutover.TRUSTED_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.private_key),
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
        review["signature_base64"] = base64.b64encode(signature.read_bytes()).decode()
        path = self.root / "integration-review.json"
        path.write_bytes(cutover._json_bytes(review))
        return path

    def _reviewed(self) -> tuple[dict[str, object], Path]:
        prepared = self._prepare()
        return prepared, self._signed_review(str(prepared["proposal_path"]))

    def test_prepare_is_detached_and_review_binds_target_commit_diff_and_proof(self) -> None:
        prepared, review_path = self._reviewed()
        proposal = cutover._load_json(Path(str(prepared["proposal_path"])))
        review = cutover.load_integration_review(review_path, proposal)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(self._git("rev-parse", f"{prepared['prepared_commit']}^"), self.base_head)
        self.assertEqual(review["proposal_root"], prepared["proposal_root"])
        self.assertEqual(review["integration_diff_root"], prepared["integration_diff_root"])
        self.assertEqual(proposal["accepted_target_revision_root"], cutover.load_accepted_bundle()["handoff"]["target_revision_root"])
        self.assertEqual(proposal["accepted_incumbent_path"], "/software-factory-candidate-target/stream_export.py")
        self.assertEqual(proposal["target_repository_root"], str(self.target))

    def test_reviewed_cutover_preserves_unrelated_dirty_work_updates_real_proof_and_replays(self) -> None:
        prepared, review = self._reviewed()
        (self.target / "staged.txt").write_text("kept staged\n", encoding="utf-8")
        self._git("add", "--", "staged.txt")
        (self.target / "unstaged.txt").write_text("kept unstaged\n", encoding="utf-8")
        (self.target / "untracked.txt").write_text("kept untracked\n", encoding="utf-8")
        dirty_before = self._git("status", "--short", "--", "staged.txt", "unstaged.txt", "untracked.txt")
        result = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(result["action"], "cutover-applied")
        self.assertTrue(result["candidate_authoritative"])
        self.assertFalse(result["incumbent_authoritative"])
        self.assertFalse(result["manual_resume_required"])
        self.assertEqual(self._git("rev-parse", "HEAD"), prepared["prepared_commit"])
        proof = cutover._load_json(self.proof_path)
        currentness = {record["proof_id"]: record["currentness"] for record in proof["records"]}
        self.assertEqual(currentness["incumbent-focused-proof"], "stale")
        self.assertEqual(currentness["incumbent-descendant-proof"], "stale")
        self.assertEqual(currentness["unaffected-proof"], "current")
        self.assertEqual(
            self._git("status", "--short", "--", "staged.txt", "unstaged.txt", "untracked.txt"),
            dirty_before,
        )
        duplicate = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["execution_key"], result["execution_key"])
        self.assertEqual(duplicate["next_action"], result["next_action"])

    def test_affected_staged_work_rejects_before_preparation(self) -> None:
        incumbent = (self.target / self.relative).read_bytes()
        (self.target / self.relative).write_text("# user staged change\n", encoding="utf-8")
        self._git("add", "--", self.relative)
        (self.target / self.relative).write_bytes(incumbent)
        with self.assertRaisesRegex(cutover.CutoverError, "index contains user changes"):
            self._prepare()
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)

    def test_missing_or_changed_canonical_supervision_context_rejects(self) -> None:
        empty = self.root / "empty-supervision"
        empty.mkdir()
        with mock.patch.object(cutover, "SUPERVISION_ROOT", empty):
            with self.assertRaisesRegex(cutover.CutoverError, "supervision context"):
                self._prepare()
        prepared, review = self._reviewed()
        policy = self.supervision_root / self.owner_id / "policy.json"
        changed = json.loads(policy.read_text())
        changed["target_label"] = "changed after review"
        policy.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(cutover.CutoverError, "supervision context|owner"):
            cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertNotEqual(prepared["prepared_commit"], self.base_head)

    def test_changed_future_contract_routes_to_block8_without_target_write(self) -> None:
        prepared, review = self._reviewed()
        text = self.tracker.read_text(encoding="utf-8")
        self.tracker.write_text(
            text.replace(
                "Demonstrate one shared adaptive-decision protocol—unchanged, inline, candidate,",
                "Demonstrate one changed future protocol—unchanged, inline, candidate,",
                1,
            ),
            encoding="utf-8",
        )
        result = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(result["action"], "route-block-8")
        self.assertFalse(result["application_authorized"])
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertNotEqual(prepared["prepared_commit"], self.base_head)

    def test_review_or_target_currentness_change_rejects(self) -> None:
        prepared = self._prepare()
        rejected = self._signed_review(
            str(prepared["proposal_path"]), review_disposition="inconclusive"
        )
        with self.assertRaisesRegex(cutover.CutoverError, "not accepted"):
            cutover.apply_cutover(self.target, self.tracker, rejected)
        valid = self._signed_review(str(prepared["proposal_path"]))
        (self.target / self.relative).write_text("# changed after review\n", encoding="utf-8")
        with self.assertRaisesRegex(cutover.CutoverError, "target bytes changed"):
            cutover.apply_cutover(self.target, self.tracker, valid)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)

    def test_pre_ref_oserror_restores_exact_incumbent_and_index(self) -> None:
        _prepared, review = self._reviewed()
        original = cutover._write_atomic
        calls = 0

        def fail_second(path: Path, raw: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture write failure")
            original(path, raw)

        with mock.patch.object(cutover, "_write_atomic", side_effect=fail_second):
            with self.assertRaisesRegex(cutover.CutoverError, "write failed"):
                cutover.apply_cutover(self.target, self.tracker, review)
        _full, _relative, incumbent = cutover._artifact_file(
            cutover.load_accepted_bundle(), "incumbent"
        )
        self.assertEqual((self.target / self.relative).read_bytes(), incumbent)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(self._git("status", "--short", "--", self.relative, cutover.PROOF_RELATIVE), "")

    def test_post_ref_and_post_effect_interruptions_recover_without_false_state(self) -> None:
        prepared, review = self._reviewed()
        with self.assertRaisesRegex(cutover.CutoverError, "after atomic promotion"):
            cutover.apply_cutover(
                self.target, self.tracker, review, failpoint="after-ref-update"
            )
        self.assertEqual(self._git("rev-parse", "HEAD"), prepared["prepared_commit"])
        recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(recovered["duplicate"])
        self.assertTrue(recovered["candidate_authoritative"])

    def test_missing_outcome_after_reviewed_promotion_is_recomputed_from_current_target(self) -> None:
        prepared, review = self._reviewed()
        with self.assertRaisesRegex(cutover.CutoverError, "before current outcome"):
            cutover.apply_cutover(
                self.target, self.tracker, review, failpoint="before-outcome-write"
            )
        self.assertEqual(self._git("rev-parse", "HEAD"), prepared["prepared_commit"])
        self.assertFalse(cutover._outcome_path(self.target).exists())
        recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(recovered["duplicate"])
        self.assertTrue(cutover._outcome_path(self.target).is_file())

    def test_committed_target_change_during_effect_never_yields_authoritative_result(self) -> None:
        _prepared, review = self._reviewed()
        original = cutover._run_observable_effect
        changed = False

        def move_target(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            nonlocal changed
            if not changed:
                changed = True
                (self.target / self.relative).write_text("def export(rows): return b'wrong'\n")
                self._git("add", "--", self.relative)
                self._git("commit", "-q", "-m", "Concurrent target change")
            return original(source, exercise)

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=move_target):
            with self.assertRaisesRegex(cutover.CutoverError, "current context changed|lost target"):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertFalse(cutover._outcome_path(self.target).exists())

    def test_current_target_proof_is_reviewed_not_a_static_fixture(self) -> None:
        bundle = cutover.load_accepted_bundle()
        proof = cutover._load_json(self.proof_path)
        proof["records"].append(
            {
                "proof_id": "late-current-incumbent-proof",
                "subject_root": bundle["handoff"]["incumbent_root"],
                "depends_on": [],
                "currentness": "current",
            }
        )
        proof_without_root = {key: value for key, value in proof.items() if key != "graph_root"}
        proof["graph_root"] = cutover.object_root(proof_without_root)
        self.proof_path.write_bytes(cutover._json_bytes(proof))
        self._git("add", "--", cutover.PROOF_RELATIVE)
        self._git("commit", "-q", "-m", "Add current target proof")
        prepared, review = self._reviewed()
        result = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertIn(
            "late-current-incumbent-proof",
            result["proof_reconciliation"]["invalidated_proof_ids"],
        )
        self.assertEqual(result["integration_commit"], prepared["prepared_commit"])


if __name__ == "__main__":
    unittest.main()
