from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("skill_release.py")
SPEC = importlib.util.spec_from_file_location("skill_release", MODULE_PATH)
assert SPEC and SPEC.loader
skill_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skill_release)


class SkillReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.release_root = self.root / "releases-owner"
        self.install_root = self.root / "installed"
        self.repo.mkdir()
        self.install_root.mkdir()
        self.evidence_counter = 0
        self.authority_root = self.root / "authority"
        (self.authority_root / "reviewers").mkdir(parents=True)
        (self.authority_root / "operators").mkdir()
        self.authority_patcher = mock.patch.object(
            skill_release, "AUTHORITY_ROOT", self.authority_root
        )
        self.authority_patcher.start()
        (
            self.reviewer_private,
            self.reviewer_key_sha256,
        ) = self.create_authority(
            "reviewers", skill_release.TRUSTED_AUTHORITY_IDS["reviewers"][0]
        )
        (
            self.operator_private,
            self.operator_key_sha256,
        ) = self.create_authority(
            "operators", skill_release.TRUSTED_AUTHORITY_IDS["operators"][0]
        )
        for directory in (
            self.authority_root,
            self.authority_root / "reviewers",
            self.authority_root / "operators",
        ):
            directory.chmod(0o555)
        self.git("init")
        self.git("config", "user.email", "factory@example.test")
        self.git("config", "user.name", "Factory Test")
        for name in skill_release.SKILLS:
            directory = self.repo / name
            directory.mkdir()
            directory.joinpath("SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test skill\n---\n\n# {name}\n",
                encoding="utf-8",
            )
            os.symlink(directory, self.install_root / name)
        self.commit("initial skills")

    def tearDown(self) -> None:
        self.authority_patcher.stop()
        for base, directory_names, file_names in os.walk(self.root):
            Path(base).chmod(0o755)
            for name in directory_names:
                child = Path(base) / name
                if not child.is_symlink():
                    child.chmod(0o755)
            for name in file_names:
                child = Path(base) / name
                if not child.is_symlink():
                    child.chmod(0o644)
        self.temporary.cleanup()

    def create_authority(self, role: str, principal: str) -> tuple[Path, str]:
        private = self.root / f"{principal}.private.pem"
        public = self.authority_root / role / f"{principal}.pem"
        subprocess.run(
            [
                str(skill_release.TRUSTED_OPENSSL_PATH),
                "genpkey",
                "-algorithm",
                "Ed25519",
                "-out",
                str(private),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                str(skill_release.TRUSTED_OPENSSL_PATH),
                "pkey",
                "-in",
                str(private),
                "-pubout",
                "-out",
                str(public),
            ],
            check=True,
            capture_output=True,
        )
        public.chmod(0o444)
        return private, hashlib.sha256(public.read_bytes()).hexdigest()

    def sign(self, material: dict[str, object], private: Path) -> str:
        self.evidence_counter += 1
        material_path = self.root / f"signed-material-{self.evidence_counter}.json"
        signature_path = self.root / f"signature-{self.evidence_counter}.bin"
        material_path.write_bytes(skill_release.canonical(material))
        subprocess.run(
            [
                str(skill_release.TRUSTED_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(private),
                "-rawin",
                "-in",
                str(material_path),
                "-out",
                str(signature_path),
            ],
            check=True,
            capture_output=True,
        )
        return base64.b64encode(signature_path.read_bytes()).decode("ascii")

    def git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def review_evidence(self, commit: str) -> Path:
        request = skill_release.review_request(
            argparse.Namespace(repo=str(self.repo), source_commit=commit)
        )
        self.evidence_counter += 1
        path = self.root / f"review-{self.evidence_counter}.json"
        material = {
            "schema_version": skill_release.SCHEMA_VERSION,
            "kind": "software-factory-skill-release-review",
            "record_id": f"independent-review-{self.evidence_counter}-1234",
            "reviewer_id": skill_release.TRUSTED_AUTHORITY_IDS["reviewers"][0],
            "implementer_id": "implementation-owner-1234",
            "disposition": "accepted",
            "source_commit": commit,
            "candidate_root_sha256": request["candidate_root_sha256"],
            "reviewed_at": "2026-08-09T12:00:00+00:00",
            "evidence": [f"exact-commit:{commit}", "isolated-review:no-findings"],
            "authority_key_sha256": self.reviewer_key_sha256,
        }
        material["review_root_sha256"] = skill_release.digest(material)
        material["signature_base64"] = self.sign(material, self.reviewer_private)
        path.write_bytes(skill_release.canonical(material) + b"\n")
        return path

    def stage_args(
        self, commit: str, *, review_evidence: Path | None = None
    ) -> argparse.Namespace:
        values = {
            "repo": str(self.repo),
            "release_root": str(self.release_root),
            "install_root": str(self.install_root),
            "source_commit": commit,
            "implementer_id": "implementation-owner-1234",
            "review_evidence": str(review_evidence or self.review_evidence(commit)),
        }
        return argparse.Namespace(**values)

    def activate_args(
        self,
        release_id: str,
        *,
        operation: str = "bootstrap",
        previous_release_id: str | None = None,
    ) -> argparse.Namespace:
        self.evidence_counter += 1
        evidence_path = self.root / f"quiescent-{self.evidence_counter}.json"
        material = {
            "schema_version": skill_release.SCHEMA_VERSION,
            "kind": "software-factory-quiescent-boundary",
            "record_id": f"quiescent-boundary-{self.evidence_counter}-1234",
            "operator_id": skill_release.TRUSTED_AUTHORITY_IDS["operators"][0],
            "operation": operation,
            "release_id": release_id,
            "previous_active_release_id": previous_release_id,
            "observed_at": skill_release.utc_now(),
            "no_concurrent_skill_resolutions": True,
            "evidence": ["isolated-test-boundary", "no-concurrent-resolution"],
            "authority_key_sha256": self.operator_key_sha256,
        }
        material["evidence_root_sha256"] = skill_release.digest(material)
        material["signature_base64"] = self.sign(material, self.operator_private)
        evidence_path.write_bytes(skill_release.canonical(material) + b"\n")
        return argparse.Namespace(
            release_root=str(self.release_root),
            install_root=str(self.install_root),
            release_id=release_id,
            quiescent_evidence=str(evidence_path),
            legacy_source_root=str(self.repo),
        )

    def stage(self, commit: str) -> dict[str, object]:
        return skill_release.stage_release(self.stage_args(commit))

    def test_stage_activate_second_release_and_rollback(self) -> None:
        first_commit = self.git("rev-parse", "HEAD")
        original_targets = {
            name: os.readlink(self.install_root / name)
            for name in skill_release.SKILLS
        }
        first_review = self.review_evidence(first_commit)
        first = skill_release.stage_release(
            self.stage_args(first_commit, review_evidence=first_review)
        )
        self.assertEqual(first["stage"], "created")
        repeated = skill_release.stage_release(
            self.stage_args(first_commit, review_evidence=first_review)
        )
        self.assertEqual(repeated["stage"], "existing")
        self.assertEqual(repeated["manifest_sha256"], first["manifest_sha256"])
        self.assertEqual(
            original_targets,
            {
                name: os.readlink(self.install_root / name)
                for name in skill_release.SKILLS
            },
            "staging must not alter installed behavior",
        )

        first_active = skill_release.bootstrap_release(
            self.activate_args(str(first["release_id"]))
        )
        self.assertEqual(first_active["active_release_id"], first["release_id"])
        stable_targets = {
            name: os.readlink(self.install_root / name)
            for name in skill_release.SKILLS
        }
        self.assertTrue(
            all(
                target
                == skill_release.desired_link(self.release_root.resolve(), name)
                for name, target in stable_targets.items()
            )
        )

        for name in skill_release.SKILLS:
            (self.repo / name / "VERSION").write_text("2\n", encoding="utf-8")
        second_commit = self.commit("second skills")
        second = self.stage(second_commit)
        activated = skill_release.activate_release(
            self.activate_args(
                str(second["release_id"]),
                operation="activate",
                previous_release_id=str(first["release_id"]),
            )
        )
        self.assertEqual(activated["previous_release_id"], first["release_id"])
        self.assertEqual(
            stable_targets,
            {
                name: os.readlink(self.install_root / name)
                for name in skill_release.SKILLS
            },
            "normal activation must mutate only the current pointer",
        )

        rollback_args = self.activate_args(
            str(first["release_id"]),
            operation="rollback",
            previous_release_id=str(second["release_id"]),
        )
        rolled_back = skill_release.rollback_release(rollback_args)
        self.assertEqual(rolled_back["active_release_id"], first["release_id"])
        status = skill_release.status(
            argparse.Namespace(
                release_root=str(self.release_root),
                install_root=str(self.install_root),
            )
        )
        self.assertTrue(status["installed_complete"])
        self.assertEqual(status["active_release_id"], first["release_id"])
        self.assertEqual(status["activation_history_records"], 3)

    def test_stage_rejects_dirty_missing_review_partial_and_symlinked_source(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        (self.repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(skill_release.ReleaseError, "dirty"):
            self.stage(commit)
        (self.repo / "dirty.txt").unlink()

        review_path = self.review_evidence(commit)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["review_root_sha256"] = "0" * 64
        review_path.write_bytes(skill_release.canonical(review) + b"\n")
        with self.assertRaisesRegex(skill_release.ReleaseError, "review"):
            skill_release.stage_release(
                self.stage_args(commit, review_evidence=review_path)
            )

        missing = self.repo / skill_release.SKILLS[-1]
        shutil.rmtree(missing)
        partial_commit = self.commit("partial")
        with self.assertRaisesRegex(skill_release.ReleaseError, "complete three-skill"):
            self.stage(partial_commit)

        self.git("reset", "--hard", commit)
        os.symlink("SKILL.md", self.repo / skill_release.SKILLS[0] / "escape")
        symlink_commit = self.commit("symlink")
        with self.assertRaisesRegex(skill_release.ReleaseError, "symlink"):
            self.stage(symlink_commit)

    def test_hash_drift_and_missing_quiescent_evidence_fail_before_cutover(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        release_id = str(staged["release_id"])
        args = self.activate_args(release_id)
        quiescent = json.loads(Path(args.quiescent_evidence).read_text(encoding="utf-8"))
        quiescent["evidence_root_sha256"] = "0" * 64
        Path(args.quiescent_evidence).write_bytes(
            skill_release.canonical(quiescent) + b"\n"
        )
        with self.assertRaisesRegex(skill_release.ReleaseError, "Quiescent-boundary"):
            skill_release.activate_release(args)
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))

        skill_file = (
            self.release_root
            / "releases"
            / release_id
            / skill_release.SKILLS[0]
            / "SKILL.md"
        )
        skill_file.chmod(0o644)
        skill_file.write_text(skill_file.read_text(encoding="utf-8") + "drift\n")
        with self.assertRaisesRegex(
            skill_release.ReleaseError, "identity or digest|content drifted"
        ):
            skill_release.activate_release(self.activate_args(release_id))
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))

    def test_interrupted_bootstrap_restores_all_links_and_pointer(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        original_targets = {
            name: os.readlink(self.install_root / name)
            for name in skill_release.SKILLS
        }
        with self.assertRaisesRegex(skill_release.ReleaseError, "interruption"):
            skill_release.bootstrap_release(
                self.activate_args(str(staged["release_id"])),
                fail_after_bootstrap_links=1,
            )
        self.assertEqual(
            original_targets,
            {
                name: os.readlink(self.install_root / name)
                for name in skill_release.SKILLS
            },
        )
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))

    def test_restore_error_is_retried_after_pointer_is_removed(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        original_targets = {
            name: os.readlink(self.install_root / name)
            for name in skill_release.SKILLS
        }
        original_replace = skill_release.replace_link
        failed_once = False

        def flaky_restore(path: Path, target: str) -> None:
            nonlocal failed_once
            if target in original_targets.values() and not failed_once:
                failed_once = True
                raise OSError("one restore write failed")
            original_replace(path, target)

        with (
            mock.patch.object(skill_release, "replace_link", side_effect=flaky_restore),
            self.assertRaisesRegex(skill_release.ReleaseError, "interruption"),
        ):
            skill_release.bootstrap_release(
                self.activate_args(str(staged["release_id"])),
                fail_after_bootstrap_links=1,
            )
        self.assertTrue(failed_once)
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))
        self.assertEqual(
            original_targets,
            {
                name: os.readlink(self.install_root / name)
                for name in skill_release.SKILLS
            },
        )

    def test_failed_post_swap_reload_restores_prior_pointer(self) -> None:
        first_commit = self.git("rev-parse", "HEAD")
        first = self.stage(first_commit)
        skill_release.bootstrap_release(self.activate_args(str(first["release_id"])))
        for name in skill_release.SKILLS:
            (self.repo / name / "VERSION").write_text("candidate\n", encoding="utf-8")
        second_commit = self.commit("candidate")
        second = self.stage(second_commit)
        original_swap = skill_release.swap_pointer
        restore_failed_once = False

        def flaky_prior_restore(release_root: Path, release_id: str | None) -> None:
            nonlocal restore_failed_once
            if release_id == first["release_id"] and not restore_failed_once:
                restore_failed_once = True
                raise OSError("one prior-pointer restore failed")
            original_swap(release_root, release_id)

        with (
            mock.patch.object(
                skill_release,
                "child_reload_verify",
                side_effect=skill_release.ReleaseError("reload unavailable"),
            ),
            mock.patch.object(
                skill_release, "swap_pointer", side_effect=flaky_prior_restore
            ),
            self.assertRaisesRegex(skill_release.ReleaseError, "reload unavailable"),
        ):
            skill_release.activate_release(
                self.activate_args(
                    str(second["release_id"]),
                    operation="activate",
                    previous_release_id=str(first["release_id"]),
                )
            )
        self.assertEqual(
            skill_release.current_release_id(self.release_root.resolve()),
            first["release_id"],
        )
        self.assertTrue(restore_failed_once)
        self.assertEqual(len(skill_release.history(self.release_root.resolve())), 1)

    def test_signed_quiescent_boundary_is_single_use(self) -> None:
        first_commit = self.git("rev-parse", "HEAD")
        first = self.stage(first_commit)
        skill_release.bootstrap_release(self.activate_args(str(first["release_id"])))
        for name in skill_release.SKILLS:
            (self.repo / name / "VERSION").write_text("candidate\n", encoding="utf-8")
        second_commit = self.commit("candidate for replay")
        second = self.stage(second_commit)
        state_path = skill_release.release_state_path(self.release_root.resolve())
        authentic_prior_state = state_path.read_bytes()
        first_to_second = self.activate_args(
            str(second["release_id"]),
            operation="activate",
            previous_release_id=str(first["release_id"]),
        )
        skill_release.activate_release(first_to_second)
        back_to_first = self.activate_args(
            str(first["release_id"]),
            operation="rollback",
            previous_release_id=str(second["release_id"]),
        )
        skill_release.rollback_release(back_to_first)
        with self.assertRaisesRegex(skill_release.ReleaseError, "already consumed"):
            skill_release.activate_release(first_to_second)
        history_path = self.release_root / skill_release.HISTORY_NAME
        first_record = history_path.read_bytes().splitlines(keepends=True)[0]
        history_path.write_bytes(first_record)
        state_path.write_bytes(authentic_prior_state)
        with self.assertRaisesRegex(skill_release.ReleaseError, "external release head"):
            skill_release.activate_release(first_to_second)
        self.assertEqual(
            skill_release.current_release_id(self.release_root.resolve()),
            first["release_id"],
        )

    def test_self_hashed_unsigned_authority_records_are_rejected(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        review_path = self.review_evidence(commit)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["signature_base64"] = base64.b64encode(b"fabricated").decode("ascii")
        review_path.write_bytes(skill_release.canonical(review) + b"\n")
        with self.assertRaisesRegex(skill_release.ReleaseError, "signature"):
            skill_release.stage_release(
                self.stage_args(commit, review_evidence=review_path)
            )

    def test_path_substitution_cannot_replace_signature_or_validator_tools(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        review_path = self.review_evidence(commit)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["signature_base64"] = base64.b64encode(b"fabricated").decode("ascii")
        review_path.write_bytes(skill_release.canonical(review) + b"\n")
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        for name in ("openssl", "python3"):
            tool = fake_bin / name
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)
        substituted_path = str(fake_bin) + os.pathsep + os.environ.get("PATH", "")
        with mock.patch.dict(os.environ, {"PATH": substituted_path}):
            with self.assertRaisesRegex(skill_release.ReleaseError, "signature"):
                skill_release.stage_release(
                    self.stage_args(commit, review_evidence=review_path)
                )
            name = skill_release.SKILLS[0]
            (self.repo / name / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n\n# Missing description\n",
                encoding="utf-8",
            )
            invalid_commit = self.commit("invalid skill under substituted path")
            with self.assertRaisesRegex(skill_release.ReleaseError, "validation failed"):
                skill_release.review_request(
                    argparse.Namespace(repo=str(self.repo), source_commit=invalid_commit)
                )
            with self.assertRaisesRegex(skill_release.ReleaseError, "validation failed"):
                skill_release.stage_release(
                    self.stage_args(invalid_commit, review_evidence=review_path)
                )

    def test_mixed_or_escaping_legacy_install_is_rejected(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        outside = self.root / "outside"
        outside.mkdir()
        (self.install_root / skill_release.SKILLS[0]).unlink()
        os.symlink(outside, self.install_root / skill_release.SKILLS[0])
        with self.assertRaisesRegex(skill_release.ReleaseError, "differs"):
            skill_release.bootstrap_release(
                self.activate_args(str(staged["release_id"]))
            )
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))

        (self.install_root / skill_release.SKILLS[0]).unlink()
        os.symlink(
            skill_release.desired_link(
                self.release_root.resolve(), skill_release.SKILLS[0]
            ),
            self.install_root / skill_release.SKILLS[0],
        )
        with self.assertRaisesRegex(skill_release.ReleaseError, "partial"):
            skill_release.bootstrap_release(
                self.activate_args(str(staged["release_id"]))
            )

    def test_manifest_cannot_self_authorize_or_select_unknown_rollback(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        release_id = str(staged["release_id"])
        manifest_path = self.release_root / "releases" / release_id / skill_release.MANIFEST_NAME
        manifest_path.chmod(0o644)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["independent_review"] = {}
        material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        manifest["manifest_sha256"] = skill_release.digest(material)
        manifest_path.write_bytes(skill_release.canonical(manifest) + b"\n")
        with self.assertRaises(skill_release.ReleaseError):
            skill_release.activate_release(self.activate_args(release_id))

        rollback_args = self.activate_args(
            "unknown-release", operation="rollback", previous_release_id=None
        )
        with self.assertRaisesRegex(skill_release.ReleaseError, "prior accepted"):
            skill_release.rollback_release(rollback_args)

    def test_oversized_or_noncanonical_manifest_is_rejected_before_cutover(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        staged = self.stage(commit)
        release_id = str(staged["release_id"])
        manifest_path = (
            self.release_root / "releases" / release_id / skill_release.MANIFEST_NAME
        )
        manifest_path.chmod(0o644)
        with manifest_path.open("ab") as destination:
            destination.write(b" ")
        manifest_path.chmod(0o444)
        with self.assertRaisesRegex(skill_release.ReleaseError, "canonical JSON"):
            skill_release.bootstrap_release(self.activate_args(release_id))
        manifest_path.chmod(0o644)
        with manifest_path.open("ab") as destination:
            destination.write(b" " * (1024 * 1024))
        manifest_path.chmod(0o444)
        with self.assertRaisesRegex(skill_release.ReleaseError, "size limit"):
            skill_release.bootstrap_release(self.activate_args(release_id))
        self.assertIsNone(skill_release.current_release_id(self.release_root.resolve()))

    def test_forged_history_cannot_make_never_active_release_rollback_eligible(self) -> None:
        first_commit = self.git("rev-parse", "HEAD")
        first = self.stage(first_commit)
        skill_release.bootstrap_release(self.activate_args(str(first["release_id"])))
        for name in skill_release.SKILLS:
            (self.repo / name / "NEVER_ACTIVE").write_text("candidate\n", encoding="utf-8")
        second_commit = self.commit("never active candidate")
        second = self.stage(second_commit)
        forged = {
            "record_id": "ACTIVATION-2",
            "release_id": second["release_id"],
            "previous_record_sha256": skill_release.history(
                self.release_root.resolve()
            )[-1]["record_hmac_sha256"],
        }
        forged["record_sha256"] = skill_release.digest(forged)
        skill_release.append_jsonl(
            self.release_root / skill_release.HISTORY_NAME, forged
        )
        args = self.activate_args(
            str(second["release_id"]),
            operation="rollback",
            previous_release_id=str(first["release_id"]),
        )
        with self.assertRaisesRegex(skill_release.ReleaseError, "forged"):
            skill_release.rollback_release(args)

    def test_canonical_validator_rejects_invalid_skill_metadata(self) -> None:
        name = skill_release.SKILLS[0]
        (self.repo / name / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n\n# Missing description\n",
            encoding="utf-8",
        )
        commit = self.commit("invalid skill metadata")
        with self.assertRaisesRegex(skill_release.ReleaseError, "validation failed"):
            self.stage(commit)

    def test_validator_runtime_identity_is_hashed_once_per_candidate(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        with mock.patch.object(
            skill_release,
            "trusted_validator_python",
            wraps=skill_release.trusted_validator_python,
        ) as runtime:
            skill_release.review_request(
                argparse.Namespace(repo=str(self.repo), source_commit=commit)
            )
        self.assertEqual(runtime.call_count, 1)

    def test_releases_directory_symlink_is_rejected(self) -> None:
        outside = self.root / "outside-releases"
        outside.mkdir()
        self.release_root.mkdir()
        os.symlink(outside, self.release_root / "releases")
        commit = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(skill_release.ReleaseError, "real directory"):
            self.stage(commit)


if __name__ == "__main__":
    unittest.main()
