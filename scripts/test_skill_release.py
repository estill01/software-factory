from __future__ import annotations

import argparse
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
        self.validator = self.root / "validator.py"
        self.validator.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "raise SystemExit(0 if (pathlib.Path(sys.argv[1]) / 'SKILL.md').is_file() else 1)\n",
            encoding="utf-8",
        )
        self.validator.chmod(0o755)
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

    def stage_args(self, commit: str, **overrides: str) -> argparse.Namespace:
        values = {
            "repo": str(self.repo),
            "release_root": str(self.release_root),
            "install_root": str(self.install_root),
            "source_commit": commit,
            "reviewer_id": "independent-reviewer-1234",
            "review_record": f"review-{commit[:12]}",
            "review_root": hashlib.sha256(
                f"independent-review:{commit}".encode("utf-8")
            ).hexdigest(),
            "validator": str(self.validator),
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def activate_args(
        self,
        release_id: str,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            release_root=str(self.release_root),
            install_root=str(self.install_root),
            release_id=release_id,
            quiescent_boundary_record="quiescent-boundary-1234",
            quiescent_boundary_root=hashlib.sha256(
                b"no concurrent skill resolution during cutover"
            ).hexdigest(),
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
        first = self.stage(first_commit)
        self.assertEqual(first["stage"], "created")
        repeated = self.stage(first_commit)
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
            self.activate_args(str(second["release_id"]))
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

        rollback_args = self.activate_args("unused")
        rollback_args.release_id = None
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

        with self.assertRaisesRegex(skill_release.ReleaseError, "review root"):
            skill_release.stage_release(self.stage_args(commit, review_root=""))

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
        args.quiescent_boundary_root = ""
        with self.assertRaisesRegex(skill_release.ReleaseError, "quiescent-boundary root"):
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
        with self.assertRaisesRegex(skill_release.ReleaseError, "content drifted"):
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

    def test_failed_post_swap_reload_restores_prior_pointer(self) -> None:
        first_commit = self.git("rev-parse", "HEAD")
        first = self.stage(first_commit)
        skill_release.bootstrap_release(self.activate_args(str(first["release_id"])))
        for name in skill_release.SKILLS:
            (self.repo / name / "VERSION").write_text("candidate\n", encoding="utf-8")
        second_commit = self.commit("candidate")
        second = self.stage(second_commit)
        with (
            mock.patch.object(
                skill_release,
                "child_reload_verify",
                side_effect=skill_release.ReleaseError("reload unavailable"),
            ),
            self.assertRaisesRegex(skill_release.ReleaseError, "reload unavailable"),
        ):
            skill_release.activate_release(
                self.activate_args(str(second["release_id"]))
            )
        self.assertEqual(
            skill_release.current_release_id(self.release_root.resolve()),
            first["release_id"],
        )
        self.assertEqual(len(skill_release.history(self.release_root.resolve())), 1)

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

        rollback_args = self.activate_args("unknown-release")
        with self.assertRaisesRegex(skill_release.ReleaseError, "prior accepted"):
            skill_release.rollback_release(rollback_args)

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
