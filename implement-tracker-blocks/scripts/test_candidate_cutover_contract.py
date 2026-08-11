#!/usr/bin/env python3
"""Focused Block 9 reviewed target-owner cutover contract."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
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
BLOCK9_HEADING = "## Block 9 — Cut over a winning candidate, reconcile currentness, and resume"
BLOCK10_HEADING = "## Block 10 — Bind the same protocol to target repositories and Software Factory self-work"
BLOCK11_HEADING = "## Block 11 — Dogfood all decision paths and document demonstrated operation"


def block9_program_snapshot(source: str) -> str:
    """Freeze the accepted Block 9 status frontier after the live tracker advances."""

    replacements = (
        (
            "| 9 | Cut over a winning candidate, reconcile currentness, and resume | 6, 7 | `completed` |",
            "| 9 | Cut over a winning candidate, reconcile currentness, and resume | 6, 7 | `in-progress` |",
        ),
        (
            "| 10 | Bind the same protocol to target repositories and Software Factory self-work | 8, 9 | `completed` |",
            "| 10 | Bind the same protocol to target repositories and Software Factory self-work | 8, 9 | `not-started` |",
        ),
        (
            "| 11 | Dogfood all decision paths and document demonstrated operation | 10 | `in-progress` |",
            "| 11 | Dogfood all decision paths and document demonstrated operation | 10 | `not-started` |",
        ),
        (
            f"{BLOCK9_HEADING}\n\nStatus: `completed`",
            f"{BLOCK9_HEADING}\n\nStatus: `in-progress`",
        ),
        (
            f"{BLOCK10_HEADING}\n\nStatus: `completed`",
            f"{BLOCK10_HEADING}\n\nStatus: `not-started`",
        ),
        (
            f"{BLOCK11_HEADING}\n\nStatus: `in-progress`",
            f"{BLOCK11_HEADING}\n\nStatus: `not-started`",
        ),
    )
    for current, historical in replacements:
        if source.count(current) != 1:
            raise AssertionError("current tracker status frontier differs")
        source = source.replace(current, historical, 1)
    return source


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
        self.tracker.write_text(
            block9_program_snapshot(SOURCE_TRACKER.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
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

    def _init_supervision(self, source_text: str = "Implement this tracker.") -> None:
        module = cutover._supervision_module()
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
        directory = self.supervision_root / self.owner_id
        policy = module.read_json(directory / "policy.json")
        range_state = module.implementation_range_state(policy)
        assert range_state is not None
        mission = module.bound_mission(policy)
        assert mission is not None
        transition = module.parser().parse_args(
            [
                "--root",
                str(self.supervision_root),
                "successor-transition-record",
                "--target-thread",
                self.owner_id,
                "--transition-id",
                cutover.CONTINUATION_TRANSITION_ID,
                "--phase",
                "required",
                "--tracker-sha256",
                range_state["tracker_sha256"],
                "--tracker-source-record",
                "implementation-range-history:"
                + range_state["range_history_head_sha256"],
                "--requested-block-range",
                module.format_implementation_block_set(
                    list(range_state["requested_blocks"])
                ),
                "--first-eligible-block",
                "Block 9",
                "--source-mission-root",
                mission["mission_root"],
                "--governing-authority-source-class",
                "direct-user",
                "--governing-authority-source-record",
                "direct-block9-target",
                "--governing-authority-source-sha256",
                source_sha,
                "--topology-posture",
                "same-task-new-run",
                "--topology-basis",
                "same-task-default",
                "--topology-rationale",
                "Continue the exact current Block 9 range in this task.",
                "--state-fingerprint",
                cutover.object_root(range_state),
                "--evidence",
                "implementation-range:" + cutover.object_root(range_state),
            ]
        )
        with redirect_stdout(io.StringIO()):
            module.cmd_successor_transition_record(transition)

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
            "implementation_range_root": proposal["implementation_range_root"],
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
        self.assertEqual(
            review["implementation_range_root"],
            proposal["supervision_context"]["implementation_range_root"],
        )
        self.assertEqual(
            proposal["supervision_context"]["implementation_range"]["eligible_blocks"],
            [9],
        )
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
        producer_calls = 0
        producer = cutover._run_observable_effect

        def count_effect(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            nonlocal producer_calls
            producer_calls += 1
            return producer(source, exercise)

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=count_effect):
            result = cutover.apply_cutover(self.target, self.tracker, review)
            duplicate = cutover.apply_cutover(self.target, self.tracker, review)
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
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["execution_key"], result["execution_key"])
        self.assertEqual(duplicate["next_action"], result["next_action"])
        self.assertEqual(duplicate["continuation_root"], result["continuation_root"])
        self.assertEqual(duplicate["continuation_state"], "work-started")
        self.assertEqual(duplicate["continuation_start_count"], 1)
        self.assertEqual(producer_calls, 1)
        module = cutover._supervision_module()
        gate = module.parser().parse_args(
            [
                "--root",
                str(self.supervision_root),
                "successor-transition-gate",
                "--target-thread",
                self.owner_id,
                "--transition-id",
                cutover.CONTINUATION_TRANSITION_ID,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            module.cmd_successor_transition_gate(gate)
        gate_result = json.loads(output.getvalue())
        self.assertEqual(gate_result["phase"], "work-started")
        self.assertEqual(gate_result["next_action"], "continue-same-task-run")
        self.assertFalse(gate_result["source_stop_permitted"])

    def test_affected_staged_work_rejects_before_preparation(self) -> None:
        incumbent = (self.target / self.relative).read_bytes()
        (self.target / self.relative).write_text("# user staged change\n", encoding="utf-8")
        self._git("add", "--", self.relative)
        (self.target / self.relative).write_bytes(incumbent)
        with self.assertRaisesRegex(cutover.CutoverError, "index contains user changes"):
            self._prepare()
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)

    def test_unrelated_canonical_range_rejects_before_proposal(self) -> None:
        shutil.rmtree(self.supervision_root)
        with self.assertRaisesRegex(
            Exception, "no dependency-safe first Block"
        ):
            self._init_supervision("Implement Block 1.")
        self.assertFalse(cutover._proposal_path(self.target).exists())

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

    def test_unaccepted_future_contract_change_rejects_without_target_write(self) -> None:
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
        with self.assertRaisesRegex(
            cutover.CutoverError, "canonical supervision context"
        ):
            cutover.apply_cutover(self.target, self.tracker, review)
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
        original = cutover._write_atomic_if_unchanged
        calls = 0

        def fail_second(
            path: Path,
            expected: bytes,
            raw: bytes,
            **kwargs: object,
        ) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture write failure")
            original(path, expected, raw, **kwargs)

        with mock.patch.object(
            cutover, "_write_atomic_if_unchanged", side_effect=fail_second
        ):
            with self.assertRaisesRegex(cutover.CutoverError, "write failed"):
                cutover.apply_cutover(self.target, self.tracker, review)
        _full, _relative, incumbent = cutover._artifact_file(
            cutover.load_accepted_bundle(), "incumbent"
        )
        self.assertEqual((self.target / self.relative).read_bytes(), incumbent)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(self._git("status", "--short", "--", self.relative, cutover.PROOF_RELATIVE), "")

    def test_changed_affected_bytes_at_write_boundary_are_preserved(self) -> None:
        _prepared, review = self._reviewed()
        original = cutover._write_atomic_if_unchanged
        changed = b"# concurrent caller bytes\n"

        def change_before_replace(path: Path, expected: bytes, raw: bytes) -> None:
            if path == self.target / self.relative:
                path.write_bytes(changed)
            original(path, expected, raw)

        with mock.patch.object(
            cutover, "_write_atomic_if_unchanged", side_effect=change_before_replace
        ):
            with self.assertRaisesRegex(cutover.CutoverError, "bytes changed"):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual((self.target / self.relative).read_bytes(), changed)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)

    def test_per_path_recovery_preserves_changed_path_and_restores_other_owned_path(self) -> None:
        _prepared, review = self._reviewed()
        restore = cutover._restore_owned_replacements
        caller_target = self.target / "caller-proof-target.json"
        caller_target.write_text("caller proof bytes\n", encoding="utf-8")

        def change_one_path_before_recovery(
            repo: Path,
            head: str,
            previous: dict[str, bytes | None],
            replacements: dict[str, bytes],
            expected_index: bytes,
        ) -> None:
            self.proof_path.unlink()
            self.proof_path.symlink_to(caller_target)
            restore(repo, head, previous, replacements, expected_index)

        with mock.patch.object(
            cutover,
            "_restore_owned_replacements",
            side_effect=change_one_path_before_recovery,
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "concurrent affected paths were preserved"
            ):
                cutover.apply_cutover(
                    self.target, self.tracker, review, failpoint="after-write"
                )
        _full, _relative, incumbent = cutover._artifact_file(
            cutover.load_accepted_bundle(), "incumbent"
        )
        self.assertEqual((self.target / self.relative).read_bytes(), incumbent)
        self.assertTrue(self.proof_path.is_symlink())
        self.assertEqual(self.proof_path.resolve().read_text(), "caller proof bytes\n")
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(
            self._git("diff", "--cached", "--name-only", "--", self.relative), ""
        )

    def test_pre_ref_concurrent_ref_move_restores_owned_paths_against_surviving_head(self) -> None:
        prepared, review = self._reviewed()
        target_git = cutover._git
        moved = False
        concurrent_head = ""

        def move_ref_before_reviewed_compare_and_swap(
            repo: Path,
            args: list[str],
            **kwargs: object,
        ) -> bytes:
            nonlocal moved, concurrent_head
            if (
                not moved
                and args[:2] == ["update-ref", "refs/heads/main"]
                and len(args) == 4
                and args[2] == prepared["prepared_commit"]
            ):
                moved = True
                base_tree = self._git("rev-parse", f"{self.base_head}^{{tree}}")
                created = subprocess.run(
                    [
                        cutover.GIT,
                        "-C",
                        str(self.target),
                        "commit-tree",
                        base_tree,
                        "-p",
                        self.base_head,
                    ],
                    input="Concurrent ref owner commit\n",
                    text=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                concurrent_head = created.stdout.strip()
                subprocess.run(
                    [
                        cutover.GIT,
                        "-C",
                        str(self.target),
                        "update-ref",
                        "refs/heads/main",
                        concurrent_head,
                        self.base_head,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            return target_git(repo, args, **kwargs)

        with mock.patch.object(
            cutover, "_git", side_effect=move_ref_before_reviewed_compare_and_swap
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "Git target-owner operation failed"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(moved)
        self.assertEqual(self._git("rev-parse", "HEAD"), concurrent_head)
        self.assertNotEqual(concurrent_head, prepared["prepared_commit"])
        self.assertEqual(
            (self.target / self.relative).read_bytes(),
            cutover._tree_path_state(self.target, concurrent_head, self.relative)[
                "content"
            ],
        )
        self.assertEqual(
            self.proof_path.read_bytes(),
            cutover._tree_path_state(
                self.target, concurrent_head, cutover.PROOF_RELATIVE
            )["content"],
        )
        self.assertEqual(
            self._git(
                "status", "--short", "--", self.relative, cutover.PROOF_RELATIVE
            ),
            "",
        )

    def test_affected_index_change_during_promotion_is_preserved_and_rejected(self) -> None:
        prepared, review = self._reviewed()
        caller_bytes = b"# caller staged index bytes\n"
        blob = subprocess.run(
            [cutover.GIT, "-C", str(self.target), "hash-object", "-w", "--stdin"],
            input=caller_bytes,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()
        temporary_index = self.root / "caller.index"
        temporary_index.write_bytes(cutover._index_bytes(self.target))
        caller_environment = dict(os.environ)
        caller_environment["GIT_INDEX_FILE"] = str(temporary_index)
        subprocess.run(
            [
                cutover.GIT,
                "-C",
                str(self.target),
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{self.relative}",
            ],
            env=caller_environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        caller_index = temporary_index.read_bytes()
        target_git = cutover._git
        changed = False

        def replace_index_during_ref_update(
            repo: Path,
            args: list[str],
            **kwargs: object,
        ) -> bytes:
            nonlocal changed
            if (
                not changed
                and args[:2] == ["update-ref", "refs/heads/main"]
                and len(args) == 4
                and args[2] == prepared["prepared_commit"]
            ):
                changed = True
                cutover._index_path(self.target).write_bytes(caller_index)
            return target_git(repo, args, **kwargs)

        with mock.patch.object(
            cutover, "_git", side_effect=replace_index_during_ref_update
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "target ref or index changed during promotion"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(changed)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(cutover._index_bytes(self.target), caller_index)
        self.assertEqual(
            subprocess.run(
                [cutover.GIT, "-C", str(self.target), "show", f":{self.relative}"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout,
            caller_bytes,
        )

    def test_affected_index_change_during_recovery_is_preserved(self) -> None:
        _prepared, review = self._reviewed()
        caller_bytes = b"# caller staged during recovery\n"
        blob = subprocess.run(
            [cutover.GIT, "-C", str(self.target), "hash-object", "-w", "--stdin"],
            input=caller_bytes,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()
        restore = cutover._restore_owned_replacements_to_current_head
        staged = False

        def stage_before_recovery(*args: object, **kwargs: object) -> None:
            nonlocal staged
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{self.relative}",
            )
            staged = True
            restore(*args, **kwargs)

        with mock.patch.object(
            cutover,
            "_restore_owned_replacements_to_current_head",
            side_effect=stage_before_recovery,
        ):
            with self.assertRaisesRegex(cutover.CutoverError, "after reviewed write"):
                cutover.apply_cutover(
                    self.target, self.tracker, review, failpoint="after-write"
                )
        self.assertTrue(staged)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(
            subprocess.run(
                [cutover.GIT, "-C", str(self.target), "show", f":{self.relative}"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout,
            caller_bytes,
        )

    def test_unrelated_index_change_preserves_stage_and_restores_owned_entries(self) -> None:
        _prepared, review = self._reviewed()
        caller_bytes = b"caller staged unrelated bytes\n"
        blob = subprocess.run(
            [cutover.GIT, "-C", str(self.target), "hash-object", "-w", "--stdin"],
            input=caller_bytes,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()

        def stage_unrelated_then_fail(
            source: bytes, exercise: dict[str, object]
        ) -> dict[str, object]:
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},staged.txt",
            )
            raise cutover.CutoverError("fixture effect validation failure")

        with mock.patch.object(
            cutover, "_run_observable_effect", side_effect=stage_unrelated_then_fail
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "fixture effect validation failure"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual(
            subprocess.run(
                [cutover.GIT, "-C", str(self.target), "show", ":staged.txt"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout,
            caller_bytes,
        )
        self.assertEqual(
            self._git(
                "diff",
                "--cached",
                "--name-only",
                "--",
                self.relative,
                cutover.PROOF_RELATIVE,
            ),
            "",
        )

    def test_surviving_symlink_tree_mode_is_restored_exactly(self) -> None:
        prepared, review = self._reviewed()
        link_target = b"surviving-target.py"
        link_blob = subprocess.run(
            [cutover.GIT, "-C", str(self.target), "hash-object", "-w", "--stdin"],
            input=link_target,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()
        temporary_index = self.root / "symlink.index"
        temporary_index.write_bytes(cutover._index_bytes(self.target))
        environment = dict(os.environ)
        environment["GIT_INDEX_FILE"] = str(temporary_index)
        subprocess.run(
            [
                cutover.GIT,
                "-C",
                str(self.target),
                "update-index",
                "--add",
                "--cacheinfo",
                f"120000,{link_blob},{self.relative}",
            ],
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tree = subprocess.run(
            [cutover.GIT, "-C", str(self.target), "write-tree"],
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()
        concurrent_head = subprocess.run(
            [
                cutover.GIT,
                "-C",
                str(self.target),
                "commit-tree",
                tree,
                "-p",
                self.base_head,
            ],
            input="Concurrent symlink owner commit\n",
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        target_git = cutover._git
        moved = False

        def move_ref_before_reviewed_compare_and_swap(
            repo: Path,
            args: list[str],
            **kwargs: object,
        ) -> bytes:
            nonlocal moved
            if (
                not moved
                and args[:2] == ["update-ref", "refs/heads/main"]
                and len(args) == 4
                and args[2] == prepared["prepared_commit"]
            ):
                moved = True
                target_git(
                    repo,
                    ["update-ref", "refs/heads/main", concurrent_head, self.base_head],
                )
            return target_git(repo, args, **kwargs)

        with mock.patch.object(
            cutover, "_git", side_effect=move_ref_before_reviewed_compare_and_swap
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "Git target-owner operation failed"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        path = self.target / self.relative
        self.assertTrue(moved)
        self.assertEqual(self._git("rev-parse", "HEAD"), concurrent_head)
        self.assertTrue(path.is_symlink())
        self.assertEqual(os.readlink(path), link_target.decode())
        self.assertEqual(
            self._git("ls-tree", concurrent_head, "--", self.relative).split()[0],
            "120000",
        )
        self.assertEqual(
            self._git("status", "--short", "--", self.relative),
            "",
        )

    def test_post_promotion_recovery_preserves_changed_bytes_and_restores_owned_proof(self) -> None:
        _prepared, review = self._reviewed()
        caller_bytes = b"# caller bytes after promotion\n"

        def change_target_then_fail(
            source: bytes, exercise: dict[str, object]
        ) -> dict[str, object]:
            (self.target / self.relative).write_bytes(caller_bytes)
            raise cutover.CutoverError("fixture effect validation failure")

        with mock.patch.object(
            cutover, "_run_observable_effect", side_effect=change_target_then_fail
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "fixture effect validation failure"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertEqual((self.target / self.relative).read_bytes(), caller_bytes)
        expected_proof = self._git("show", f"{self.base_head}:{cutover.PROOF_RELATIVE}")
        self.assertEqual(self.proof_path.read_text(encoding="utf-8").strip(), expected_proof)

    def test_post_ref_concurrent_ref_move_restores_owned_paths_against_surviving_head(self) -> None:
        prepared, review = self._reviewed()
        concurrent_head = ""

        def move_ref_then_fail(
            source: bytes, exercise: dict[str, object]
        ) -> dict[str, object]:
            nonlocal concurrent_head
            base_tree = self._git("rev-parse", f"{self.base_head}^{{tree}}")
            created = subprocess.run(
                [
                    cutover.GIT,
                    "-C",
                    str(self.target),
                    "commit-tree",
                    base_tree,
                    "-p",
                    str(prepared["prepared_commit"]),
                ],
                input="Concurrent ref owner commit\n",
                text=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            concurrent_head = created.stdout.strip()
            branch_ref = self._git("symbolic-ref", "-q", "HEAD")
            self._git(
                "update-ref",
                branch_ref,
                concurrent_head,
                str(prepared["prepared_commit"]),
            )
            raise cutover.CutoverError("fixture post-ref currentness failure")

        with mock.patch.object(
            cutover, "_run_observable_effect", side_effect=move_ref_then_fail
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "fixture post-ref currentness failure"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), concurrent_head)
        self.assertNotEqual(concurrent_head, prepared["prepared_commit"])
        self.assertEqual(
            (self.target / self.relative).read_bytes(),
            cutover._tree_path_state(self.target, concurrent_head, self.relative)[
                "content"
            ],
        )
        self.assertEqual(
            self.proof_path.read_bytes(),
            cutover._tree_path_state(
                self.target, concurrent_head, cutover.PROOF_RELATIVE
            )["content"],
        )
        self.assertEqual(
            self._git(
                "status", "--short", "--", self.relative, cutover.PROOF_RELATIVE
            ),
            "",
        )

    def test_changed_target_before_continuation_start_withholds_authoritative_result(self) -> None:
        _prepared, review = self._reviewed()
        retain = cutover._retain_review_copy
        retain_calls = 0
        caller_bytes = b"# changed before continuation start\n"

        def retain_then_change(repo: Path, record: dict[str, object]) -> None:
            nonlocal retain_calls
            retain_calls += 1
            retain(repo, record)
            if retain_calls == 2:
                (self.target / self.relative).write_bytes(caller_bytes)

        with mock.patch.object(
            cutover, "_retain_review_copy", side_effect=retain_then_change
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "current target differs"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        module = cutover._supervision_module()
        records = module.successor_transition_events(
            module.events(self.supervision_root / self.owner_id / "events.jsonl"),
            cutover.CONTINUATION_TRANSITION_ID,
        )
        self.assertEqual(records[-1]["phase"], "required")
        self.assertEqual((self.target / self.relative).read_bytes(), caller_bytes)

    def test_changed_target_during_transition_append_is_canonically_corrected(self) -> None:
        _prepared, review = self._reviewed()
        module = cutover._supervision_module()
        append = module.append_raw_locked_at
        changed = False
        caller_bytes = b"# changed at continuation append\n"

        def change_before_start_append(*args: object, **kwargs: object) -> str:
            nonlocal changed
            value = args[2] if len(args) > 2 else {}
            if (
                not changed
                and isinstance(value, dict)
                and value.get("kind") == "successor-transition"
                and value.get("phase") == "work-started"
            ):
                changed = True
                (self.target / self.relative).write_bytes(caller_bytes)
            return append(*args, **kwargs)

        with mock.patch.object(cutover, "_supervision_module", return_value=module):
            with mock.patch.object(
                module, "append_raw_locked_at", side_effect=change_before_start_append
            ):
                with self.assertRaisesRegex(
                    cutover.CutoverError, "current target differs"
                ):
                    cutover.apply_cutover(self.target, self.tracker, review)
        records = module.successor_transition_events(
            module.events(self.supervision_root / self.owner_id / "events.jsonl"),
            cutover.CONTINUATION_TRANSITION_ID,
        )
        self.assertEqual(
            [item["phase"] for item in records],
            ["required", "work-started", "corrected"],
        )
        gate = module.parser().parse_args(
            [
                "--root",
                str(self.supervision_root),
                "successor-transition-gate",
                "--target-thread",
                self.owner_id,
                "--transition-id",
                cutover.CONTINUATION_TRANSITION_ID,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            module.cmd_successor_transition_gate(gate)
        gate_result = json.loads(output.getvalue())
        self.assertEqual(gate_result["phase"], "corrected")
        self.assertEqual(
            gate_result["next_action"],
            "continue-governing-outcome-in-source-task",
        )
        self.assertFalse(gate_result["source_stop_permitted"])

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
        producer = cutover._run_observable_effect
        producer_calls = 0

        def count_effect(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            nonlocal producer_calls
            producer_calls += 1
            return producer(source, exercise)

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=count_effect):
            with self.assertRaisesRegex(cutover.CutoverError, "before current outcome"):
                cutover.apply_cutover(
                    self.target, self.tracker, review, failpoint="before-outcome-write"
                )
            self.assertTrue(cutover._effect_path(self.target).is_file())
            recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), prepared["prepared_commit"])
        self.assertTrue(recovered["duplicate"])
        self.assertTrue(cutover._outcome_path(self.target).is_file())
        self.assertEqual(producer_calls, 1)

    def test_effect_result_spool_survives_final_record_write_interruption(self) -> None:
        _prepared, review = self._reviewed()
        producer = cutover._run_observable_effect
        writer = cutover._write_atomic
        producer_calls = 0
        final_write_failed = False

        def count_effect(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            nonlocal producer_calls
            producer_calls += 1
            return producer(source, exercise)

        def fail_first_final_effect_write(path: Path, raw: bytes) -> None:
            nonlocal final_write_failed
            if path == cutover._effect_path(self.target) and not final_write_failed:
                final_write_failed = True
                raise OSError("fixture final effect write interruption")
            writer(path, raw)

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=count_effect):
            with mock.patch.object(
                cutover, "_write_atomic", side_effect=fail_first_final_effect_write
            ):
                with self.assertRaisesRegex(
                    cutover.CutoverError, "effect validation failed after promotion"
                ):
                    cutover.apply_cutover(self.target, self.tracker, review)
                self.assertTrue(cutover._effect_pending_path(self.target).is_file())
                recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(recovered["candidate_authoritative"])
        self.assertEqual(producer_calls, 1)
        self.assertTrue(cutover._effect_path(self.target).is_file())
        self.assertFalse(cutover._effect_pending_path(self.target).exists())

    def test_unsigned_precreated_effect_record_cannot_replace_producer_evidence(self) -> None:
        prepared, review = self._reviewed()
        proposal = cutover._load_json(Path(str(prepared["proposal_path"])))
        synthetic: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-candidate-cutover-effect-validation",
            "proposal_root": proposal["proposal_root"],
            "integration_commit": proposal["prepared_commit"],
            "integration_review_root": cutover._load_json(review)["review_root"],
            "candidate_content_root": proposal["candidate_content_root"],
            "producer_recorded_at": "2026-08-11T06:24:40.000000Z",
            "observable_effect": cutover._expected_effect(
                cutover.load_accepted_bundle()["exercise"]
            ),
            "owner_hmac_sha256": "0" * 64,
        }
        synthetic["effect_validation_root"] = cutover.object_root(synthetic)
        cutover._effect_path(self.target).write_bytes(cutover._json_bytes(synthetic))
        with mock.patch.object(
            cutover,
            "_run_observable_effect",
            side_effect=AssertionError("producer must not be reached"),
        ):
            with self.assertRaisesRegex(
                cutover.CutoverError, "effect validation provenance differs"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)

    def test_missing_review_copy_is_repaired_without_repeating_effect(self) -> None:
        _prepared, review = self._reviewed()
        producer = cutover._run_observable_effect
        producer_calls = 0
        retain = cutover._retain_review_copy
        retain_calls = 0

        def count_effect(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            nonlocal producer_calls
            producer_calls += 1
            return producer(source, exercise)

        def fail_first_copy(repo: Path, record: dict[str, object]) -> None:
            nonlocal retain_calls
            retain_calls += 1
            if retain_calls == 1:
                raise OSError("fixture review-copy interruption")
            retain(repo, record)

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=count_effect):
            with mock.patch.object(cutover, "_retain_review_copy", side_effect=fail_first_copy):
                with self.assertRaisesRegex(cutover.CutoverError, "owner cutover failed"):
                    cutover.apply_cutover(self.target, self.tracker, review)
            self.assertTrue(cutover._outcome_path(self.target).is_file())
            self.assertFalse(cutover._review_copy_path(self.target).exists())
            recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertTrue(recovered["duplicate"])
        self.assertTrue(cutover._review_copy_path(self.target).is_file())
        self.assertEqual(producer_calls, 1)

    def test_continuation_start_rehydrates_after_interrupted_return(self) -> None:
        _prepared, review = self._reviewed()
        with self.assertRaisesRegex(cutover.CutoverError, "after continuation start"):
            cutover.apply_cutover(
                self.target,
                self.tracker,
                review,
                failpoint="after-continuation-start",
            )
        module = cutover._supervision_module()
        events = module.events(
            self.supervision_root / self.owner_id / "events.jsonl"
        )
        retained = module.successor_transition_events(
            events, cutover.CONTINUATION_TRANSITION_ID
        )[-1]
        self.assertEqual(retained["phase"], "work-started")
        recovered = cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(recovered["continuation_root"], retained["record_sha256"])
        self.assertEqual(recovered["continuation_state"], "work-started")
        self.assertEqual(recovered["continuation_start_count"], 1)

    def test_tracker_change_during_effect_withholds_acceptance_and_rolls_back(self) -> None:
        _prepared, review = self._reviewed()
        producer = cutover._run_observable_effect

        def change_program(source: bytes, exercise: dict[str, object]) -> dict[str, object]:
            result = producer(source, exercise)
            text = self.tracker.read_text(encoding="utf-8")
            self.tracker.write_text(
                text.replace("## Block 10 —", "## Block 10 — changed ", 1),
                encoding="utf-8",
            )
            return result

        with mock.patch.object(cutover, "_run_observable_effect", side_effect=change_program):
            with self.assertRaisesRegex(
                cutover.CutoverError, "canonical supervision context|current context"
            ):
                cutover.apply_cutover(self.target, self.tracker, review)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_head)
        self.assertFalse(cutover._outcome_path(self.target).exists())

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

    def test_current_proof_cannot_depend_on_stale_proof(self) -> None:
        proof = cutover._load_json(self.proof_path)
        proof["records"].extend(
            [
                {
                    "proof_id": "stale-incumbent-proof",
                    "subject_root": cutover.load_accepted_bundle()["handoff"]["incumbent_root"],
                    "depends_on": [],
                    "currentness": "stale",
                },
                {
                    "proof_id": "current-dependent-on-stale",
                    "subject_root": "f" * 64,
                    "depends_on": ["stale-incumbent-proof"],
                    "currentness": "current",
                },
            ]
        )
        proof["records"] = sorted(proof["records"], key=lambda item: item["proof_id"])
        material = {key: value for key, value in proof.items() if key != "graph_root"}
        proof["graph_root"] = cutover.object_root(material)
        self.proof_path.write_bytes(cutover._json_bytes(proof))
        self._git("add", "--", cutover.PROOF_RELATIVE)
        self._git("commit", "-q", "-m", "Add incoherent target proof")
        with self.assertRaisesRegex(cutover.CutoverError, "depends on stale"):
            self._prepare()


if __name__ == "__main__":
    unittest.main()
