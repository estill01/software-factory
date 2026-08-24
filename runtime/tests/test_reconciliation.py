from __future__ import annotations

import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.errors import InvalidTransition
from software_factory.reconciliation import RepositoryReconciliationService


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("CREATE TABLE missions(id TEXT PRIMARY KEY)")
        self.connection.execute("INSERT INTO missions(id) VALUES('mission-1')")
        migrations = Path(__file__).parents[1] / "src" / "software_factory" / "migrations"
        self.connection.executescript(
            (migrations / "0011_release_recovery_cleanup.sql").read_text(encoding="utf-8")
        )
        self.connection.executescript(
            (migrations / "0017_reconciliation_runtime.sql").read_text(encoding="utf-8")
        )

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


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def make_repo(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import VALUE\n\ndef test_value():\n    assert VALUE > 0\n",
        encoding="utf-8",
    )
    git(root, "add", "--", "app.py", "test_app.py")
    git(root, "commit", "-m", "baseline")


def accepted_item(
    service: RepositoryReconciliationService,
    repository: Path,
    branch: str,
    tmp_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = service.operations.inventory_repository(
        repository_root=repository, mission_id="mission-1"
    )
    bundle = service.operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = service.operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key=branch,
        classification="accepted",
        disposition="integrate",
        evidence={"qa": "passed", "review": "accepted"},
    )
    return item, bundle


def service() -> RepositoryReconciliationService:
    store = TestStore()
    return RepositoryReconciliationService(store)  # type: ignore[arg-type]


def test_accepted_branch_is_validated_published_by_cas_and_lane_retires(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(repository, "add", "--", "app.py")
    git(repository, "commit", "-m", "accepted feature")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-m", "pytest", "-q"],
    )
    assert candidate["status"] == "accepted"
    published = reconciliation.publish_integration(candidate["id"])
    assert published["status"] == "published"
    assert git(repository, "rev-parse", "main") == candidate["candidate_head"]
    assert (repository / "app.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    reconciliation.retire_integration_lane(candidate["id"])
    assert not Path(candidate["integration_worktree"]).exists()
    assert (
        candidate["integration_branch"]
        not in git(repository, "branch", "--format=%(refname:short)").splitlines()
    )


def test_target_advance_after_validation_prevents_publication(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "feature")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-m", "pytest", "-q"],
    )
    (repository / "main-only.txt").write_text("advance\n", encoding="utf-8")
    git(repository, "add", "--", "main-only.txt")
    git(repository, "commit", "-m", "main advanced")
    with pytest.raises(InvalidTransition, match="advanced"):
        reconciliation.publish_integration(candidate["id"])


def test_post_publish_failure_rolls_target_back(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    original = git(repository, "rev-parse", "main")
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "feature")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-m", "pytest", "-q"],
    )
    with pytest.raises(RuntimeError, match="rolled back"):
        reconciliation.publish_integration(
            candidate["id"],
            post_publish_validation=[sys.executable, "-c", "raise SystemExit(9)"],
        )
    assert git(repository, "rev-parse", "main") == original
    assert reconciliation.store.one(
        "SELECT status FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    ) == {"status": "rolled_back"}


def test_unfinished_branch_is_restored_on_new_baseline_worktree(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "unfinished")
    (repository / "unfinished.txt").write_text("partial implementation\n", encoding="utf-8")
    git(repository, "add", "--", "unfinished.txt")
    git(repository, "commit", "-m", "unfinished checkpoint")
    git(repository, "switch", "main")
    (repository / "baseline.txt").write_text("new baseline\n", encoding="utf-8")
    git(repository, "add", "--", "baseline.txt")
    git(repository, "commit", "-m", "new baseline")
    reconciliation = service()
    inventory = reconciliation.operations.inventory_repository(
        repository_root=repository, mission_id="mission-1"
    )
    bundle = reconciliation.operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = reconciliation.operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key="unfinished",
        classification="unfinished",
        disposition="restart",
        evidence={"remaining_obligation": "complete unfinished feature"},
    )
    restarted = reconciliation.restart_unfinished_work(
        item["id"],
        preservation_bundle_id=bundle["id"],
        baseline_branch="main",
        worktree_root=tmp_path / "restart-worktrees",
    )
    worktree = Path(restarted["restart_worktree"])
    assert restarted["status"] == "ready"
    assert (worktree / "baseline.txt").read_text(encoding="utf-8") == "new baseline\n"
    assert (worktree / "unfinished.txt").read_text(encoding="utf-8") == "partial implementation\n"
    assert "A  unfinished.txt" in git(worktree, "status", "--porcelain=v1")


def test_reconciliation_always_preserves_before_planning_destructive_work(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    reconciliation = service()
    result = reconciliation.reconcile(
        repository_root=repository,
        mission_id="mission-1",
        active_writers=[],
        classifications=[
            {
                "item_type": "branch",
                "item_key": "unknown-branch",
                "classification": "unknown",
            }
        ],
        preservation_directory=tmp_path / "preserved",
    )
    assert result["preservation_bundle"]["verified"] == 1
    assert result["items"][0]["disposition"] == "retain"
    assert result["unknown_defaults_to_retain"] is True
