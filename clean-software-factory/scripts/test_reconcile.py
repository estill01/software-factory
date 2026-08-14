#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("reconcile.py")
SPEC = importlib.util.spec_from_file_location("cleanup_reconcile", SCRIPT)
assert SPEC and SPEC.loader
reconcile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconcile)


def run(
    argv: list[str], cwd: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"},
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


class ReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.artifacts = self.root / "artifacts"
        run(["git", "init", "--bare", str(self.remote)], self.root)
        run(["git", "init", "-b", "main", str(self.repo)], self.root)
        run(["git", "config", "user.email", "test@example.invalid"], self.repo)
        run(["git", "config", "user.name", "Cleanup Test"], self.repo)
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        run(["git", "add", "tracked.txt"], self.repo)
        run(["git", "commit", "-m", "baseline"], self.repo)
        run(["git", "remote", "add", "origin", str(self.remote)], self.repo)
        run(["git", "push", "-u", "origin", "main"], self.repo)
        self.provider = self.root / "provider.json"
        self.tasks = self.root / "tasks.json"
        self.release = self.root / "release.json"
        self.provider.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "complete": True,
                    "kind": "provider-snapshot",
                    "owner": "github",
                    "pull_requests": [],
                }
            ),
            encoding="utf-8",
        )
        self.tasks.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "complete": True,
                    "kind": "task-snapshot",
                    "tasks": [],
                }
            ),
            encoding="utf-8",
        )
        self.release.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "complete": True,
                    "kind": "release-snapshot",
                    "release_id": "fixture-release",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(
        self, command: str, *extra: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return run(
            [
                "python3",
                str(SCRIPT),
                command,
                "--repo",
                str(self.repo),
                "--main",
                "main",
                "--remote",
                "origin",
                "--provider",
                "github",
                "--provider-snapshot",
                str(self.provider),
                "--task-snapshot",
                str(self.tasks),
                "--release-snapshot",
                str(self.release),
                "--artifact-root",
                str(self.artifacts),
                *extra,
            ],
            self.repo,
            check=check,
        )

    def verify_command(
        self, run_dir: str, *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return run(
            [
                "python3",
                str(SCRIPT),
                "verify",
                "--run-dir",
                run_dir,
                "--repo",
                str(self.repo),
                "--main",
                "main",
                "--remote",
                "origin",
                "--provider",
                "github",
                "--provider-snapshot",
                str(self.provider),
                "--task-snapshot",
                str(self.tasks),
                "--release-snapshot",
                str(self.release),
                "--artifact-root",
                str(self.artifacts),
            ],
            self.repo,
            check=check,
        )

    def test_plan_is_deterministic_resumable_and_repository_read_only(self) -> None:
        before = run(["git", "status", "--porcelain=v2", "--branch"], self.repo).stdout
        refs_before = run(["git", "show-ref"], self.repo).stdout
        first = json.loads(self.command("plan").stdout)
        second = json.loads(self.command("plan").stdout)
        self.assertEqual(first, second)
        self.assertEqual(first["path"], "audit")
        self.assertGreater(first["hold_count"], 0)
        self.assertEqual(
            run(["git", "status", "--porcelain=v2", "--branch"], self.repo).stdout,
            before,
        )
        self.assertEqual(run(["git", "show-ref"], self.repo).stdout, refs_before)
        self.assertFalse((self.repo / ".codex").exists())
        verify = json.loads(self.verify_command(first["run_dir"]).stdout)
        self.assertEqual(verify["status"], "retained-deferred-proof")
        self.assertEqual(verify["current"], "bounded-observations-only")

    def test_inventory_then_plan_resumes_one_run(self) -> None:
        inventory = json.loads(self.command("inventory").stdout)
        plan = json.loads(self.command("plan").stdout)
        self.assertEqual(inventory["run_id"], plan["run_id"])
        self.assertEqual(inventory["run_dir"], plan["run_dir"])
        status = json.loads(
            run(
                ["python3", str(SCRIPT), "status", "--run-dir", plan["run_dir"]],
                self.repo,
            ).stdout
        )
        self.assertEqual(status["current_phase"], "plan")

    def test_dirty_untracked_and_ignored_state_is_retained(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text(
            "private-local-byte\n", encoding="utf-8"
        )
        (self.repo / "ignored.txt").write_text("ignored-local-byte\n", encoding="utf-8")
        result = json.loads(self.command("plan").stdout)
        self.assertEqual(result["path"], "audit")
        self.assertGreater(result["hold_count"], 0)
        run_dir = Path(result["run_dir"])
        inventory = json.loads((run_dir / "inventory.json").read_text())
        dirt = {item["dirt"] for item in inventory["artifacts"]}
        self.assertTrue({"unstaged", "untracked", "unknown"} <= dirt)
        all_records = "".join(path.read_text() for path in run_dir.glob("*.json"))
        self.assertNotIn("private-local-byte", all_records)
        self.assertNotIn("ignored-local-byte", all_records)

    def test_missing_provider_and_task_owners_are_not_presented_clean(self) -> None:
        result = run(
            [
                "python3",
                str(SCRIPT),
                "plan",
                "--repo",
                str(self.repo),
                "--artifact-root",
                str(self.artifacts),
                "--provider",
                "unsupported",
            ],
            self.repo,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["path"], "audit")
        status = json.loads(
            (Path(payload["run_dir"]) / "status.json").read_text(encoding="utf-8")
        )
        scopes = {
            scope for hold in status["active_holds"] for scope in hold["effect_scope"]
        }
        self.assertIn("provider-owner-unavailable", scopes)
        self.assertIn("task-owner-unavailable", scopes)

    def test_active_overlapping_writer_selects_coordinated_path(self) -> None:
        self.tasks.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "complete": True,
                    "kind": "task-snapshot",
                    "tasks": [
                        {
                            "changed_paths": ["tracked.txt"],
                            "repository_root": str(self.repo),
                            "status": "active",
                            "task_id": "fixture-task",
                            "worktree": str(self.repo),
                            "writer": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        payload = json.loads(self.command("plan").stdout)
        self.assertEqual(payload["path"], "audit")
        status = json.loads((Path(payload["run_dir"]) / "status.json").read_text())
        scopes = str(status["active_holds"])
        expected = "provider-inventory-incomplete task-inventory-incomplete release-inventory-incomplete task-overlap-unproved remote-currentness-unproved"
        self.assertTrue(all(subject in scopes for subject in expected.split()))

    def test_missing_remote_main_is_null_and_retained(self) -> None:
        run(["git", "update-ref", "-d", "refs/remotes/origin/main"], self.repo)
        payload = json.loads(self.command("plan").stdout)
        source = json.loads(
            (Path(payload["run_dir"]) / "source-snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsNone(source["remote_main"])
        self.assertEqual(payload["path"], "audit")

    def test_moving_source_creates_successor_run(self) -> None:
        first = json.loads(self.command("plan").stdout)
        (self.repo / "tracked.txt").write_text("changed-after-plan\n", encoding="utf-8")
        stale_verify = self.verify_command(first["run_dir"], check=False)
        self.assertEqual(stale_verify.returncode, 2)
        self.assertIn("successor plan required", stale_verify.stdout)
        second = json.loads(self.command("plan").stdout)
        self.assertNotEqual(
            first["source_snapshot_root"], second["source_snapshot_root"]
        )
        self.assertNotEqual(first["run_dir"], second["run_dir"])

    def test_rejects_non_top_level_symlink_and_malformed_or_oversized_snapshots(
        self,
    ) -> None:
        nested = self.repo / "nested"
        nested.mkdir()
        bad = self.command("plan", check=False)
        self.assertEqual(bad.returncode, 0)
        nested_result = run(
            [
                "python3",
                str(SCRIPT),
                "inventory",
                "--repo",
                str(nested),
                "--artifact-root",
                str(self.artifacts),
            ],
            self.repo,
            check=False,
        )
        self.assertEqual(nested_result.returncode, 2)
        symlink = self.root / "repo-link"
        symlink.symlink_to(self.repo, target_is_directory=True)
        symlink_result = run(
            [
                "python3",
                str(SCRIPT),
                "inventory",
                "--repo",
                str(symlink),
                "--artifact-root",
                str(self.artifacts),
            ],
            self.root,
            check=False,
        )
        self.assertEqual(symlink_result.returncode, 2)
        self.provider.write_text("not json", encoding="utf-8")
        malformed = self.command("plan", check=False)
        self.assertEqual(malformed.returncode, 2)
        self.provider.write_bytes(b"x" * (reconcile.MAX_OWNER_SNAPSHOT_BYTES + 1))
        oversized = self.command("plan", check=False)
        self.assertEqual(oversized.returncode, 2)

    def test_verify_rejects_schema_invalid_record_even_with_recomputed_root(
        self,
    ) -> None:
        payload = json.loads(self.command("plan").stdout)
        plan_path = Path(payload["run_dir"]) / "plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["caller_selected_acceptance"] = True
        projection = dict(plan)
        projection.pop("record_root")
        plan["record_root"] = reconcile.sha256(projection)
        plan_path.write_text(
            json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        result = self.verify_command(payload["run_dir"], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("record fields differ", result.stdout)

    def test_preserve_restores_dirty_bytes_without_repository_mutation(self) -> None:
        (self.repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
        run(["git", "add", "tracked.txt"], self.repo)
        (self.repo / "tracked.txt").write_text("unstaged\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text(
            "private-local-byte\n", encoding="utf-8"
        )
        for name in (
            "api-route.py",
            "migration.sql",
            "product-config.yaml",
            "Widget.tsx",
            "feature.test.py",
            "work-tracker.md",
            "semantic-review.txt",
            "deferred-option.md",
        ):
            (self.repo / name).write_text(f"{name}\n", encoding="utf-8")
        before = run(["git", "status", "--porcelain=v2", "--branch"], self.repo).stdout
        refs_before = run(["git", "show-ref"], self.repo).stdout
        plan = json.loads(self.command("plan").stdout)
        preserved = json.loads(
            self.command("preserve", "--run-dir", plan["run_dir"]).stdout
        )
        self.assertEqual(preserved["status"], "preservation-retained-unknown")
        run_dir = Path(plan["run_dir"])
        record = json.loads((run_dir / "preservation.json").read_text())
        coverage = json.loads((run_dir / "capability-coverage.json").read_text())
        inventory = json.loads((run_dir / "inventory.json").read_text())
        self.assertTrue(record["packages"])
        self.assertTrue(all(item["local_only"] for item in record["packages"]))
        self.assertTrue(
            all(
                self.repo not in Path(item["path"]).parents
                for item in record["packages"]
            )
        )
        self.assertTrue(record["restore_receipts"])
        self.assertTrue(
            all(
                item["status"] == "passed"
                and item["disposable_root"] == item["restored_root"]
                for item in record["restore_receipts"]
            )
        )
        self.assertEqual(
            {item["artifact_id"] for item in inventory["artifacts"]},
            {
                artifact_id
                for item in coverage["candidates"]
                for artifact_id in item["source_artifact_ids"]
            },
        )
        self.assertTrue(
            all(item["status"] == "unknown" for item in coverage["candidates"])
        )
        self.assertTrue(
            {
                "api",
                "configuration",
                "deferred-option",
                "migration",
                "review-evidence",
                "route",
                "test",
                "tracker-evidence",
                "ui",
            }
            <= {item["surface_kind"] for item in coverage["surfaces"]}
        )
        records = "".join(path.read_text() for path in run_dir.glob("*.json"))
        self.assertNotIn("private-local-byte", records)
        self.assertEqual(
            run(["git", "status", "--porcelain=v2", "--branch"], self.repo).stdout,
            before,
        )
        self.assertEqual(run(["git", "show-ref"], self.repo).stdout, refs_before)
        untracked_id = next(
            item["artifact_id"]
            for item in inventory["artifacts"]
            if item["artifact_kind"] == "worktree-path"
            and item["path"] == "untracked.txt"
        )
        destination = self.root / "restored-untracked.txt"
        restored = json.loads(
            run(
                [
                    "python3",
                    str(SCRIPT),
                    "restore",
                    "--run-dir",
                    plan["run_dir"],
                    "--artifact-id",
                    untracked_id,
                    "--destination",
                    str(destination),
                ],
                self.repo,
            ).stdout
        )
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(destination.read_text(), "private-local-byte\n")
        overwrite = run(
            [
                "python3",
                str(SCRIPT),
                "restore",
                "--run-dir",
                plan["run_dir"],
                "--artifact-id",
                untracked_id,
                "--destination",
                str(destination),
            ],
            self.repo,
            check=False,
        )
        self.assertEqual(overwrite.returncode, 2)
        status = json.loads(
            run(
                ["python3", str(SCRIPT), "status", "--run-dir", plan["run_dir"]],
                self.repo,
            ).stdout
        )
        self.assertEqual(status["current_phase"], "preserve")

    def test_verify_rejects_tampered_preservation_package(self) -> None:
        (self.repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        run_dir = Path(plan["run_dir"])
        package_file = next((run_dir / "packages").glob("*/*.bin"))
        package_file.write_bytes(b"tampered\n")
        result = self.verify_command(plan["run_dir"], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("preservation package bytes differ", result.stdout)

    def test_verify_rejects_tampered_git_object_pack(self) -> None:
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        pack = next((Path(plan["run_dir"]) / "packages").glob("*/objects.pack"))
        pack.write_bytes(b"tampered-pack\n")
        result = self.verify_command(plan["run_dir"], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("object package bytes differ", result.stdout)

    def test_preserve_rejects_moving_source(self) -> None:
        plan = json.loads(self.command("plan").stdout)
        (self.repo / "tracked.txt").write_text("moved\n", encoding="utf-8")
        result = self.command("preserve", "--run-dir", plan["run_dir"], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("successor plan required", result.stdout)

    def test_verify_rejects_same_status_dirty_byte_drift(self) -> None:
        local = self.repo / "untracked.txt"
        local.write_text("version-one\n", encoding="utf-8")
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        local.write_text("version-two\n", encoding="utf-8")
        result = self.verify_command(plan["run_dir"], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("successor plan required", result.stdout)

    def test_ignored_and_nested_untracked_bytes_are_explicitly_packaged(self) -> None:
        (self.repo / ".gitignore").write_text("ignored-secret.txt\n", encoding="utf-8")
        (self.repo / "ignored-secret.txt").write_text(
            "ignored-local-byte\n", encoding="utf-8"
        )
        nested = self.repo / "local-dir"
        nested.mkdir()
        (nested / "useful.py").write_text("useful = True\n", encoding="utf-8")
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        run_dir = Path(plan["run_dir"])
        inventory = json.loads((run_dir / "inventory.json").read_text())
        preservation = json.loads((run_dir / "preservation.json").read_text())
        by_path = {
            item["path"]: item["artifact_id"]
            for item in inventory["artifacts"]
            if item["artifact_kind"] == "worktree-path"
        }
        self.assertIn("ignored-secret.txt", by_path)
        self.assertIn("local-dir/useful.py", by_path)
        packaged = {item["artifact_id"] for item in preservation["byte_entries"]}
        self.assertIn(by_path["ignored-secret.txt"], packaged)
        self.assertIn(by_path["local-dir/useful.py"], packaged)
        public_records = "".join(path.read_text() for path in run_dir.glob("*.json"))
        self.assertNotIn("ignored-local-byte", public_records)
        self.assertNotIn("useful = True", public_records)

    def test_git_objects_restore_from_one_local_pack(self) -> None:
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        run_dir = Path(plan["run_dir"])
        inventory = json.loads((run_dir / "inventory.json").read_text())
        preservation = json.loads((run_dir / "preservation.json").read_text())
        coverage = json.loads((run_dir / "capability-coverage.json").read_text())
        object_packages = [
            item
            for item in preservation["packages"]
            if item["package_kind"] == "git-objects"
        ]
        self.assertEqual(len(object_packages), 1)
        reference = next(
            item
            for item in inventory["artifacts"]
            if item["artifact_kind"] == "ref" and item["origin"] == "refs/heads/main"
        )
        destination = self.root / "restored-objects.git"
        restored = json.loads(
            run(
                [
                    "python3",
                    str(SCRIPT),
                    "restore",
                    "--run-dir",
                    plan["run_dir"],
                    "--artifact-id",
                    reference["artifact_id"],
                    "--destination",
                    str(destination),
                ],
                self.repo,
            ).stdout
        )
        self.assertEqual(restored["object_id"], reference["object_id"])
        run(["git", "cat-file", "-e", reference["object_id"]], destination)
        self.assertTrue(
            any(len(item["source_artifact_ids"]) > 1 for item in coverage["candidates"])
        )
        self.assertTrue(
            all(not item["deletion_eligible"] for item in coverage["candidates"])
        )

    def test_command_output_bound_rejects_stdout_and_stderr(self) -> None:
        for stream in ("stdout", "stderr"):
            with self.assertRaises(reconcile.CleanupError):
                reconcile.run_command(
                    [
                        "python3",
                        "-c",
                        f"import sys; sys.{stream}.write('x' * 4096)",
                    ],
                    self.root,
                    max_output_bytes=32,
                )

    def test_preserve_resumes_an_interrupted_record_pair(self) -> None:
        (self.repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")
        plan = json.loads(self.command("plan").stdout)
        first = json.loads(
            self.command("preserve", "--run-dir", plan["run_dir"]).stdout
        )
        coverage_path = Path(plan["run_dir"]) / "capability-coverage.json"
        coverage_path.unlink()
        resumed = json.loads(
            self.command("preserve", "--run-dir", plan["run_dir"]).stdout
        )
        self.assertEqual(first["preservation_root"], resumed["preservation_root"])
        self.assertEqual(resumed["status"], "preservation-retained-unknown")

    def test_nonregular_untracked_path_remains_unknown_and_unpackaged(self) -> None:
        (self.repo / "link").symlink_to(self.repo / "tracked.txt")
        plan = json.loads(self.command("plan").stdout)
        self.command("preserve", "--run-dir", plan["run_dir"])
        run_dir = Path(plan["run_dir"])
        inventory = json.loads((run_dir / "inventory.json").read_text())
        record = json.loads((run_dir / "preservation.json").read_text())
        coverage = json.loads((run_dir / "capability-coverage.json").read_text())
        link_id = next(
            item["artifact_id"]
            for item in inventory["artifacts"]
            if item["artifact_kind"] == "worktree-path" and item["path"] == "link"
        )
        self.assertNotIn(
            link_id, {item["artifact_id"] for item in record["byte_entries"]}
        )
        candidate = next(
            item
            for item in coverage["candidates"]
            if item["source_artifact_ids"] == [link_id]
        )
        self.assertEqual(candidate["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
