from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.errors import InvalidTransition
from software_factory.operations import OperationsService


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("CREATE TABLE missions(id TEXT PRIMARY KEY)")
        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0011_release_recovery_cleanup.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))
        self.connection.execute("INSERT INTO missions(id) VALUES('mission-1')")

    @contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        self.connection.execute(f"BEGIN {mode}")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        if row is None:
            if required:
                raise LookupError(sql)
            return None
        return dict(row)

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, parameters).fetchall()]


def service() -> OperationsService:
    return OperationsService(TestStore())  # type: ignore[arg-type]


def git(root: Path, *args: str) -> str:
    process = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return process.stdout.strip()


def make_git_repo(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    git(root, "add", "--", "README.md")
    git(root, "commit", "-m", "initial")


def accepted_release(
    operations: OperationsService,
    source: Path,
    releases: Path,
    revision: str,
) -> dict[str, Any]:
    staged = operations.stage_release(
        source_root=source,
        release_root=releases,
        source_revision=revision,
        source_tree_root=f"tree-{revision}",
        mission_id="mission-1",
        implementer_session_id="implementer",
    )
    operations.review_release(
        staged["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        findings={"manifest_matches": True},
        evidence_ids=[f"review-{revision}"],
    )
    return operations.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (staged["id"],))  # type: ignore[return-value]


def test_release_is_staged_immutably_reviewed_activated_and_verified(tmp_path: Path) -> None:
    operations = service()
    source = tmp_path / "source"
    source.mkdir()
    (source / "runtime.py").write_text("print('HEALTHY')\n", encoding="utf-8")
    releases = tmp_path / "releases"
    release = accepted_release(operations, source, releases, "revision-1")
    active = operations.activate_release(release["id"], release_root=releases)
    assert active["status"] == "active"
    verification = operations.verify_release(
        release["id"],
        command=[sys.executable, "runtime.py"],
        release_root=releases,
    )
    assert verification["disposition"] == "passed"
    pointer = json.loads((releases / "active-release.json").read_text(encoding="utf-8"))
    assert pointer["release_id"] == release["id"]
    assert Path(release["release_path"], "runtime.py").stat().st_mode & 0o222 == 0


def test_failed_fresh_process_verification_restores_previous_release(tmp_path: Path) -> None:
    operations = service()
    releases = tmp_path / "releases"
    first_source = tmp_path / "first"
    first_source.mkdir()
    (first_source / "health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    first = accepted_release(operations, first_source, releases, "revision-1")
    operations.activate_release(first["id"], release_root=releases)
    operations.verify_release(
        first["id"], command=[sys.executable, "health.py"], release_root=releases
    )

    second_source = tmp_path / "second"
    second_source.mkdir()
    (second_source / "health.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    second = accepted_release(operations, second_source, releases, "revision-2")
    operations.activate_release(second["id"], release_root=releases)
    verification = operations.verify_release(
        second["id"], command=[sys.executable, "health.py"], release_root=releases
    )
    assert verification["disposition"] == "failed"
    pointer = json.loads((releases / "active-release.json").read_text(encoding="utf-8"))
    assert pointer["release_id"] == first["id"]
    assert operations.store.one(
        "SELECT status FROM immutable_releases_v2 WHERE id=?", (second["id"],)
    ) == {"status": "rolled_back"}


def test_release_activation_and_rollback_are_scoped_to_one_release_root(
    tmp_path: Path,
) -> None:
    operations = service()
    source_a = tmp_path / "source-a"
    source_b = tmp_path / "source-b"
    source_a.mkdir()
    source_b.mkdir()
    (source_a / "app.py").write_text("TARGET = 'A'\n", encoding="utf-8")
    (source_b / "app.py").write_text("TARGET = 'B'\n", encoding="utf-8")
    root_a = tmp_path / "releases-a"
    root_b = tmp_path / "releases-b"
    release_a = accepted_release(operations, source_a, root_a, "revision-a")
    release_b = accepted_release(operations, source_b, root_b, "revision-b")

    operations.activate_release(release_a["id"], release_root=root_a)
    operations.activate_release(release_b["id"], release_root=root_b)
    current_a = operations.store.one(
        "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_a["id"],)
    )
    current_b = operations.store.one(
        "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_b["id"],)
    )
    assert current_a["status"] == "active"
    assert current_b["status"] == "active"
    assert current_b["previous_release_id"] is None

    operations.rollback_release(release_b["id"], release_root=root_b, evidence_ids=["rollback-b"])
    pointer_b = json.loads((root_b / "active-release.json").read_text(encoding="utf-8"))
    assert pointer_b["release_id"] is None
    assert operations.store.one(
        "SELECT status FROM immutable_releases_v2 WHERE id=?", (release_a["id"],)
    ) == {"status": "active"}
    with pytest.raises(InvalidTransition, match="different target root"):
        operations.rollback_release(
            release_a["id"], release_root=root_b, evidence_ids=["wrong-root"]
        )


def test_factory_recovery_preserves_target_and_resumes_exactly_once(tmp_path: Path) -> None:
    operations = service()
    source = tmp_path / "source"
    source.mkdir()
    (source / "health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    releases = tmp_path / "releases"
    release = accepted_release(operations, source, releases, "repair-revision")
    operations.activate_release(release["id"], release_root=releases)
    operations.verify_release(
        release["id"], command=[sys.executable, "health.py"], release_root=releases
    )
    recovery = operations.open_recovery(
        target_mission_id="mission-1",
        defect_class="factory-control-plane",
        defect_evidence={"exception": "dispatcher crashed"},
        target_state={"obligation": "still-open", "work": "stranded"},
        requested_range_root="range-1234567890abcdef",
        tracker_currentness_root="tracker-1234567890abcdef",
        safe_frontier=[{"work_id": "unrelated-safe-work"}],
    )
    operations.record_repair(
        recovery["id"],
        repair_revision="repair-revision",
        evidence_ids=["qa", "installed-health"],
        release_id=release["id"],
    )
    token = operations.reserve_exact_once_resume(
        recovery["id"],
        requested_range_root="range-1234567890abcdef",
        tracker_currentness_root="tracker-1234567890abcdef",
        wake_payload={"mission_id": "mission-1", "reason": "factory-repaired"},
    )
    duplicate = operations.reserve_exact_once_resume(
        recovery["id"],
        requested_range_root="range-1234567890abcdef",
        tracker_currentness_root="tracker-1234567890abcdef",
        wake_payload={"mission_id": "mission-1", "reason": "factory-repaired"},
    )
    assert duplicate["id"] == token["id"]
    operations.mark_resume_sent(token["id"])
    sent_again = operations.mark_resume_sent(token["id"])
    assert sent_again["status"] == "sent"
    resolved = operations.verify_recovery(
        recovery["id"], target_resumed=True, evidence_ids=["target-progressed"]
    )
    assert resolved["status"] == "resolved"
    assert resolved["resume_count"] == 1


def test_repository_inventory_and_preservation_capture_dirty_and_untracked_state(
    tmp_path: Path,
) -> None:
    operations = service()
    repository = tmp_path / "repo"
    repository.mkdir()
    make_git_repo(repository)
    (repository / "README.md").write_text("dirty\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("important\n", encoding="utf-8")
    inventory = operations.inventory_repository(
        repository_root=repository,
        mission_id="mission-1",
        active_writers=[{"branch": "main", "agent": "worker-1"}],
    )
    assert "README.md" in inventory["status_json"]
    assert "untracked.txt" in inventory["status_json"]
    bundle = operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    assert bundle["verified"] == 1
    assert Path(bundle["bundle_path"]).is_file()


def test_unknown_cleanup_item_defaults_to_retain_and_cannot_retire(tmp_path: Path) -> None:
    operations = service()
    repository = tmp_path / "repo"
    repository.mkdir()
    make_git_repo(repository)
    inventory = operations.inventory_repository(repository_root=repository)
    item = operations.plan_cleanup_item(
        inventory["id"], item_type="branch", item_key="unknown-branch"
    )
    assert item["classification"] == "unknown"
    assert item["disposition"] == "retain"
    with pytest.raises(InvalidTransition, match="proven safe"):
        operations.execute_retirement(item["id"], preservation_bundle_id="missing-bundle")


def test_redundant_branch_retires_only_after_verified_no_loss_bundle(tmp_path: Path) -> None:
    operations = service()
    repository = tmp_path / "repo"
    repository.mkdir()
    make_git_repo(repository)
    git(repository, "branch", "old-complete")
    inventory = operations.inventory_repository(repository_root=repository)
    item = operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key="old-complete",
        classification="redundant",
        disposition="retire",
        evidence={"merged_into": "main", "coverage_preserved": True},
    )
    bundle = operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    effect = operations.execute_retirement(item["id"], preservation_bundle_id=bundle["id"])
    assert effect["status"] == "succeeded"
    assert "old-complete" not in git(repository, "branch", "--format=%(refname:short)").splitlines()
