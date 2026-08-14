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
                    "branch_protection": {"required_pull_request_reviews": True},
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
        self.assertEqual(verify["status"], "verified")
        self.assertTrue(verify["current"])

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
        self.assertTrue({"unstaged", "untracked"} <= dirt)
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
        self.assertEqual(payload["path"], "coordinated-reconciliation")
        self.assertEqual(
            payload["next_action"], "obtain-owner-checkpoints-and-quiescence-gate"
        )

    def test_missing_remote_main_is_null_and_retained(self) -> None:
        run(["git", "update-ref", "-d", "refs/heads/main"], self.remote)
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

    def test_untracked_content_and_stash_changes_create_successors(self) -> None:
        untracked = self.repo / "untracked.txt"
        untracked.write_text("first\n", encoding="utf-8")
        first = json.loads(self.command("plan").stdout)
        untracked.write_text("other\n", encoding="utf-8")
        second = json.loads(self.command("plan").stdout)
        self.assertNotEqual(first["run_id"], second["run_id"])
        run(["git", "stash", "push", "--include-untracked", "-m", "one"], self.repo)
        third = json.loads(self.command("plan").stdout)
        self.assertNotEqual(second["run_id"], third["run_id"])

    def test_exhaustive_refs_deferred_reflog_and_dual_dirty_dimensions(self) -> None:
        head = run(["git", "rev-parse", "HEAD"], self.repo).stdout.strip()
        run(["git", "update-ref", "refs/custom/preserve", head], self.repo)
        (self.repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
        run(["git", "add", "tracked.txt"], self.repo)
        (self.repo / "tracked.txt").write_text("unstaged\n", encoding="utf-8")
        payload = json.loads(self.command("plan").stdout)
        inventory = json.loads(
            (Path(payload["run_dir"]) / "inventory.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            any(
                item["artifact_kind"] == "ref"
                and item["origin"] == "refs/custom/preserve"
                for item in inventory["artifacts"]
            )
        )
        self.assertTrue(
            any(
                item["artifact_kind"] == "reflog-posture" and item["dirt"] == "unknown"
                for item in inventory["artifacts"]
            )
        )
        dimensions = {
            item["dirt"]
            for item in inventory["artifacts"]
            if item["artifact_kind"] == "worktree-path"
            and item["path"] == "tracked.txt"
        }
        self.assertEqual(dimensions, {"staged", "unstaged"})

    def test_relevant_ignored_state_is_widened_for_linked_worktree(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        run(["git", "add", ".gitignore"], self.repo)
        run(["git", "commit", "-m", "ignore fixture"], self.repo)
        run(["git", "push", "origin", "main"], self.repo)
        linked = self.root / "linked"
        run(["git", "worktree", "add", "-b", "candidate", str(linked)], self.repo)
        (linked / "ignored.txt").write_text("local\n", encoding="utf-8")
        payload = json.loads(self.command("plan").stdout)
        inventory = json.loads(
            (Path(payload["run_dir"]) / "inventory.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            any(
                item["artifact_kind"] == "worktree-path"
                and item["dirt"] == "ignored"
                and item["origin"].find(str(linked)) >= 0
                for item in inventory["artifacts"]
            )
        )

    def test_malformed_complete_owner_snapshots_fail_closed(self) -> None:
        self.provider.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "complete": True,
                    "kind": "provider-snapshot",
                    "owner": "github",
                }
            ),
            encoding="utf-8",
        )
        provider = self.command("plan", check=False)
        self.assertEqual(provider.returncode, 2)
        self.provider.write_text(
            json.dumps(
                {
                    "availability": "available",
                    "branch_protection": {},
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
                    "tasks": {},
                }
            ),
            encoding="utf-8",
        )
        tasks = self.command("plan", check=False)
        self.assertEqual(tasks.returncode, 2)

    def test_plan_never_infers_acceptance_and_covers_every_artifact(self) -> None:
        payload = json.loads(self.command("plan").stdout)
        run_dir = Path(payload["run_dir"])
        inventory = json.loads((run_dir / "inventory.json").read_text(encoding="utf-8"))
        plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [entry["artifact_id"] for entry in plan["dispositions"]],
            [entry["artifact_id"] for entry in inventory["artifacts"]],
        )
        self.assertEqual(
            {entry["disposition"] for entry in plan["dispositions"]}, {"retain"}
        )
        self.assertTrue(all(not entry["proof_refs"] for entry in plan["dispositions"]))

    def test_verify_rejects_derived_roots_noncanonical_and_duplicate_keys(self) -> None:
        payload = json.loads(self.command("plan").stdout)
        run_dir = Path(payload["run_dir"])
        inventory_path = run_dir / "inventory.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        original_inventory = dict(inventory)
        inventory["inventory_root"] = "f" * 64
        projection = dict(inventory)
        projection.pop("record_root")
        inventory["record_root"] = reconcile.sha256(projection)
        inventory_path.write_bytes(reconcile.canonical(inventory) + b"\n")
        derived = self.verify_command(payload["run_dir"], check=False)
        self.assertEqual(derived.returncode, 2)
        self.assertIn("inventory root differs", derived.stdout)

        inventory_path.write_bytes(reconcile.canonical(original_inventory) + b"\n")
        (self.repo / "tracked.txt").write_text("successor\n", encoding="utf-8")
        successor = json.loads(self.command("plan").stdout)
        source_path = Path(successor["run_dir"]) / "source-snapshot.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source_path.write_text(json.dumps(source, indent=2), encoding="utf-8")
        noncanonical = self.verify_command(successor["run_dir"], check=False)
        self.assertEqual(noncanonical.returncode, 2)
        self.assertIn("not canonical", noncanonical.stdout)
        duplicate = (
            b'{"kind":"source-snapshot",' + reconcile.canonical(source)[1:] + b"\n"
        )
        source_path.write_bytes(duplicate)
        duplicated = self.verify_command(successor["run_dir"], check=False)
        self.assertEqual(duplicated.returncode, 2)
        self.assertIn("duplicate keys", duplicated.stdout)

    def test_rejects_noncanonical_repository_and_artifact_paths(self) -> None:
        noncanonical_repo = f"{self.repo.parent}/./{self.repo.name}"
        result = run(
            ["python3", str(SCRIPT), "inventory", "--repo", noncanonical_repo],
            self.root,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        symlink_root = run(
            [
                "python3",
                str(SCRIPT),
                "inventory",
                "--repo",
                str(self.repo),
                "--artifact-root",
                "/tmp/cleanup-artifacts",
            ],
            self.repo,
            check=False,
        )
        self.assertEqual(symlink_root.returncode, 2)

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


if __name__ == "__main__":
    unittest.main()
