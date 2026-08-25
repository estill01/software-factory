from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.database import Database
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
        self.connection.executescript(
            (migrations / "0024_delivery_reconciliation.sql").read_text(encoding="utf-8")
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
    inventory = service._operations.inventory_repository(
        repository_root=repository, mission_id="mission-1"
    )
    bundle = service._operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = service._operations.plan_cleanup_item(
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


def test_accepted_branch_is_validated_published_and_lane_retirement_preserves_bytes(
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
    integration_worktree = Path(candidate["integration_worktree"])
    (integration_worktree / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    (integration_worktree / "untracked-loss.txt").write_text("must survive\n", encoding="utf-8")
    with pytest.raises(InvalidTransition, match="must be preserved or deferred"):
        reconciliation.retire_integration_lane(candidate["id"])
    assert integration_worktree.is_dir()
    assert (integration_worktree / "app.py").read_text(encoding="utf-8") == "VALUE = 3\n"
    assert (integration_worktree / "untracked-loss.txt").read_text(encoding="utf-8") == (
        "must survive\n"
    )
    assert (
        candidate["integration_branch"]
        in git(repository, "branch", "--format=%(refname:short)").splitlines()
    )


def test_prepare_failure_preserves_integration_and_validation_lanes_with_pending_bytes(
    tmp_path: Path,
) -> None:
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

    with pytest.raises(RuntimeError, match="integration validation failed"):
        reconciliation.prepare_integration(
            item["id"],
            preservation_bundle_id=bundle["id"],
            target_branch="main",
            worktree_root=tmp_path / "integration-worktrees",
            validation_command=[
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('app.py').write_text('VALUE = 9\\n'); "
                    "Path('untracked-loss.txt').write_text('must survive\\n'); "
                    "raise SystemExit(9)"
                ),
            ],
        )
    candidate = reconciliation.store.one("SELECT * FROM integration_candidates_v2")
    worktree = Path(candidate["integration_worktree"])
    validation_result = json.loads(candidate["validation_result_json"])
    validation_worktree = Path(validation_result["validation_snapshot"])
    assert candidate["status"] == "failed"
    assert worktree.is_dir()
    assert (worktree / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (worktree / "untracked-loss.txt").exists()
    assert validation_worktree.is_dir()
    assert (validation_worktree / "app.py").read_text(encoding="utf-8") == "VALUE = 9\n"
    assert (validation_worktree / "untracked-loss.txt").read_text(encoding="utf-8") == (
        "must survive\n"
    )
    assert (
        candidate["integration_branch"]
        in git(repository, "branch", "--format=%(refname:short)").splitlines()
    )


def test_prepare_rejects_validation_against_bytes_other_than_candidate_head(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "app.py").write_text("VALUE = 'COMMITTED_BAD'\n", encoding="utf-8")
    git(repository, "add", "--", "app.py")
    git(repository, "commit", "-m", "candidate bytes")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)

    with pytest.raises(RuntimeError, match="exact candidate tree"):
        reconciliation.prepare_integration(
            item["id"],
            preservation_bundle_id=bundle["id"],
            target_branch="main",
            worktree_root=tmp_path / "integration-worktrees",
            validation_command=[
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('app.py').write_text(\"VALUE = 'VALIDATION_ONLY_GOOD'\\n\")"
                ),
            ],
        )
    candidate = reconciliation.store.one("SELECT * FROM integration_candidates_v2")
    result = json.loads(candidate["validation_result_json"])
    validation_worktree = Path(result["validation_snapshot"])
    assert candidate["status"] == "failed"
    assert result["candidate_head"] == candidate["candidate_head"]
    assert result["exact_tree_before"] is True
    assert result["exact_tree_after"] is False
    assert "app.py" in result["tracked_status_after"]
    assert (validation_worktree / "app.py").read_text(encoding="utf-8") == (
        "VALUE = 'VALIDATION_ONLY_GOOD'\n"
    )
    assert git(repository, "show", f"{candidate['candidate_head']}:app.py") == (
        "VALUE = 'COMMITTED_BAD'"
    )
    assert (repository / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"


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


def test_prepare_and_publish_resume_exact_git_effect_after_sql_crashes(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "feature")
    git(repository, "switch", "main")
    store = TestStore()
    armed = {"prepare": True, "publish": True}

    def fault(point: str) -> None:
        if point == "prepare:after_merge" and armed.pop("prepare", False):
            raise SystemExit("injected merge/sql crash")
        if point == "publish:after_ref_update" and armed.pop("publish", False):
            raise SystemExit("injected ref/sql crash")

    reconciliation = RepositoryReconciliationService(  # type: ignore[arg-type]
        store, fault_injector=fault
    )
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    kwargs = {
        "preservation_bundle_id": bundle["id"],
        "target_branch": "main",
        "worktree_root": tmp_path / "integration-worktrees",
        "validation_command": [sys.executable, "-m", "pytest", "-q"],
    }
    with pytest.raises(SystemExit, match="merge/sql"):
        reconciliation.prepare_integration(item["id"], **kwargs)
    candidate = reconciliation.prepare_integration(item["id"], **kwargs)
    assert candidate["status"] == "accepted"
    assert store.one("SELECT count(*) AS count FROM integration_candidates_v2") == {"count": 1}

    with pytest.raises(SystemExit, match="ref/sql"):
        reconciliation.publish_integration(candidate["id"])
    assert git(repository, "rev-parse", "main") == candidate["candidate_head"]
    assert store.one(
        "SELECT status FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    ) == {"status": "accepted"}
    published = reconciliation.publish_integration(candidate["id"])
    assert published["status"] == "published"


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
    assert (repository / "feature.txt").read_text(encoding="utf-8") == "feature\n"
    assert "feature.txt" in git(repository, "status", "--short")
    assert reconciliation.store.one(
        "SELECT status FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    ) == {"status": "rolled_back"}


def test_post_publish_validation_rejects_dirty_snapshot_and_rolls_target_back(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    original = git(repository, "rev-parse", "main")
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "app.py").write_text("VALUE = 'COMMITTED_BAD'\n", encoding="utf-8")
    git(repository, "add", "--", "app.py")
    git(repository, "commit", "-m", "candidate bytes")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-c", "pass"],
    )

    with pytest.raises(RuntimeError, match="rolled back"):
        reconciliation.publish_integration(
            candidate["id"],
            post_publish_validation=[
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('app.py').write_text(\"VALUE = 'DIRTY_GOOD'\\n\")"
                ),
            ],
        )
    stored = reconciliation.store.one(
        "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    )
    result = json.loads(stored["validation_result_json"])
    assert stored["status"] == "rolled_back"
    assert result["candidate_head"] == candidate["candidate_head"]
    assert result["exact_tree_before"] is True
    assert result["exact_tree_after"] is False
    assert git(repository, "rev-parse", "main") == original
    assert (repository / "app.py").read_text(encoding="utf-8") == "VALUE = 'COMMITTED_BAD'\n"


def test_publication_completion_rejects_concurrent_target_ref_advance(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "concurrent-advance")
    (repository / "concurrent.txt").write_text("newer authority\n", encoding="utf-8")
    git(repository, "add", "--", "concurrent.txt")
    git(repository, "commit", "-m", "concurrent target")
    concurrent_head = git(repository, "rev-parse", "HEAD")
    git(repository, "switch", "main")
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("candidate\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "accepted feature")
    git(repository, "switch", "main")
    store = TestStore()
    candidate_head = {"value": ""}

    def fault(point: str) -> None:
        if point == "publish:after_ref_update":
            git(
                repository,
                "update-ref",
                "refs/heads/main",
                concurrent_head,
                candidate_head["value"],
            )

    reconciliation = RepositoryReconciliationService(  # type: ignore[arg-type]
        store, fault_injector=fault
    )
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-c", "pass"],
    )
    candidate_head["value"] = candidate["candidate_head"]

    with pytest.raises(InvalidTransition, match="advanced before publication completion"):
        reconciliation.publish_integration(
            candidate["id"],
            post_publish_validation=[sys.executable, "-c", "pass"],
        )
    stored = store.one("SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate["id"],))
    result = json.loads(stored["validation_result_json"])
    assert stored["status"] == "failed"
    assert result == {
        "candidate_head": candidate["candidate_head"],
        "observed_target_head": concurrent_head,
        "phase": "publication_completion_fence",
    }
    assert git(repository, "rev-parse", "main") == concurrent_head
    assert store.one("SELECT status FROM cleanup_items_v2 WHERE id=?", (item["id"],)) == {
        "status": "failed"
    }


def test_post_publish_validator_spawn_failure_rolls_back_and_records_failure(
    tmp_path: Path,
) -> None:
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
        validation_command=[sys.executable, "-c", "pass"],
    )

    with pytest.raises(RuntimeError, match="rolled back") as failure:
        reconciliation.publish_integration(
            candidate["id"],
            post_publish_validation=["/definitely/not/a/validator"],
        )
    assert isinstance(failure.value.__cause__, FileNotFoundError)
    stored = reconciliation.store.one(
        "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    )
    result = json.loads(stored["validation_result_json"])
    assert stored["status"] == "rolled_back"
    assert result["phase"] == "post_publish"
    assert result["candidate_head"] == candidate["candidate_head"]
    assert result["error_type"] == "FileNotFoundError"
    assert git(repository, "rev-parse", "main") == original
    assert reconciliation.store.one(
        "SELECT status FROM cleanup_items_v2 WHERE id=?", (item["id"],)
    ) == {"status": "failed"}


@pytest.mark.parametrize("validator_succeeds", [True, False])
def test_target_ref_deletion_records_terminal_publication_failure(
    tmp_path: Path,
    validator_succeeds: bool,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("candidate\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "accepted feature")
    git(repository, "switch", "main")
    store = TestStore()
    candidate_head = {"value": ""}

    def fault(point: str) -> None:
        if point == "publish:after_ref_update":
            git(
                repository,
                "update-ref",
                "-d",
                "refs/heads/main",
                candidate_head["value"],
            )

    reconciliation = RepositoryReconciliationService(  # type: ignore[arg-type]
        store, fault_injector=fault
    )
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-c", "pass"],
    )
    candidate_head["value"] = candidate["candidate_head"]

    message = (
        "advanced before publication completion"
        if validator_succeeds
        else "rollback compare-and-swap failed"
    )
    with pytest.raises(InvalidTransition, match=message):
        reconciliation.publish_integration(
            candidate["id"],
            post_publish_validation=[
                sys.executable,
                "-c",
                "pass" if validator_succeeds else "raise SystemExit(9)",
            ],
        )
    stored = store.one("SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate["id"],))
    result = json.loads(stored["validation_result_json"])
    assert stored["status"] == "failed"
    assert result["observed_target_head"] is None
    assert result["phase"] == (
        "publication_completion_fence" if validator_succeeds else "post_publish_rollback"
    )
    assert git(repository, "show-ref", "--verify", "refs/heads/main", check=False) == ""
    assert store.one("SELECT status FROM cleanup_items_v2 WHERE id=?", (item["id"],)) == {
        "status": "failed"
    }


def test_later_target_successor_preserves_historical_publication(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("candidate\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "accepted feature")
    git(repository, "switch", "main")
    reconciliation = service()
    item, bundle = accepted_item(reconciliation, repository, "accepted-feature", tmp_path)
    candidate = reconciliation.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-c", "pass"],
    )
    first = reconciliation.publish_integration(candidate["id"])
    assert first["status"] == "published"
    (repository / "successor.txt").write_text("legitimate successor\n", encoding="utf-8")
    git(repository, "add", "--", "successor.txt")
    git(repository, "commit", "-m", "later target successor")
    successor_head = git(repository, "rev-parse", "main")

    replay = reconciliation.publish_integration(candidate["id"])
    assert replay == first
    assert successor_head != candidate["candidate_head"]
    assert reconciliation.store.one(
        "SELECT status FROM integration_candidates_v2 WHERE id=?", (candidate["id"],)
    ) == {"status": "published"}
    assert reconciliation.store.one(
        "SELECT status FROM cleanup_items_v2 WHERE id=?", (item["id"],)
    ) == {"status": "completed"}


def test_concurrent_publisher_cannot_resurrect_rolled_back_candidate(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    original = git(repository, "rev-parse", "main")
    git(repository, "switch", "-c", "accepted-feature")
    (repository / "feature.txt").write_text("candidate\n", encoding="utf-8")
    git(repository, "add", "--", "feature.txt")
    git(repository, "commit", "-m", "accepted feature")
    git(repository, "switch", "main")
    store = Database(tmp_path / "concurrent.sqlite3")
    first_holds_lock = threading.Event()
    second_loaded_stale_row = threading.Event()

    def first_fault(point: str) -> None:
        if point == "publish:after_ref_update":
            first_holds_lock.set()
            if not second_loaded_stale_row.wait(timeout=5):
                raise AssertionError("second publisher did not reach the pre-lock boundary")

    def second_fault(point: str) -> None:
        if point == "publish:before_repository_lock":
            second_loaded_stale_row.set()

    first_service = RepositoryReconciliationService(store, fault_injector=first_fault)
    second_service = RepositoryReconciliationService(store, fault_injector=second_fault)
    item, bundle = accepted_item(first_service, repository, "accepted-feature", tmp_path)
    candidate = first_service.prepare_integration(
        item["id"],
        preservation_bundle_id=bundle["id"],
        target_branch="main",
        worktree_root=tmp_path / "integration-worktrees",
        validation_command=[sys.executable, "-c", "pass"],
    )
    first_errors: list[BaseException] = []
    second_errors: list[BaseException] = []

    def publish_then_roll_back() -> None:
        try:
            first_service.publish_integration(
                candidate["id"],
                post_publish_validation=[sys.executable, "-c", "raise SystemExit(9)"],
            )
        except BaseException as exc:
            first_errors.append(exc)

    def publish_from_stale_read() -> None:
        try:
            second_service.publish_integration(candidate["id"])
        except BaseException as exc:
            second_errors.append(exc)

    first_thread = threading.Thread(target=publish_then_roll_back)
    first_thread.start()
    assert first_holds_lock.wait(timeout=5)
    second_thread = threading.Thread(target=publish_from_stale_read)
    second_thread.start()
    first_thread.join(timeout=10)
    second_thread.join(timeout=10)
    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert len(first_errors) == 1 and isinstance(first_errors[0], RuntimeError)
    assert len(second_errors) == 1 and isinstance(second_errors[0], InvalidTransition)
    assert "changed before publication" in str(second_errors[0])
    stored = store.one("SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate["id"],))
    result = json.loads(stored["validation_result_json"])
    assert stored["status"] == "rolled_back"
    assert result["phase"] == "post_publish"
    assert result["exit_code"] == 9
    assert git(repository, "rev-parse", "main") == original
    assert store.one("SELECT status FROM cleanup_items_v2 WHERE id=?", (item["id"],)) == {
        "status": "failed"
    }


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
    inventory = reconciliation._operations.inventory_repository(
        repository_root=repository, mission_id="mission-1"
    )
    bundle = reconciliation._operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = reconciliation._operations.plan_cleanup_item(
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


def test_unfinished_checked_out_branch_restores_dirty_and_untracked_bytes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "unfinished")
    (repository / "unfinished.txt").write_text("committed checkpoint\n", encoding="utf-8")
    git(repository, "add", "--", "unfinished.txt")
    git(repository, "commit", "-m", "unfinished checkpoint")
    (repository / "unfinished.txt").write_text("latest dirty bytes\n", encoding="utf-8")
    (repository / "research.txt").write_text("untracked research\n", encoding="utf-8")

    reconciliation = service()
    inventory = reconciliation._operations.inventory_repository(
        repository_root=repository, mission_id="mission-1"
    )
    bundle = reconciliation._operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = reconciliation._operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key="unfinished",
        classification="unfinished",
        disposition="restart",
        evidence={"remaining_obligation": "complete dirty work"},
    )
    arguments = {
        "preservation_bundle_id": bundle["id"],
        "baseline_branch": "main",
        "worktree_root": tmp_path / "restart-worktrees",
    }
    restarted = reconciliation.restart_unfinished_work(item["id"], **arguments)
    worktree = Path(restarted["restart_worktree"])
    assert (worktree / "unfinished.txt").read_text(encoding="utf-8") == "latest dirty bytes\n"
    assert (worktree / "research.txt").read_text(encoding="utf-8") == "untracked research\n"
    assert "A  unfinished.txt" in git(worktree, "status", "--porcelain=v1")
    assert "?? research.txt" in git(worktree, "status", "--porcelain=v1")

    receipt_path = worktree.parent / f".{restarted['id']}.restore.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["untracked_files"][0]["path"] == "research.txt"
    assert reconciliation.restart_unfinished_work(item["id"], **arguments)["id"] == restarted["id"]


def test_unfinished_restart_resumes_restored_workspace_without_duplication(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    make_repo(repository)
    git(repository, "switch", "-c", "unfinished")
    (repository / "unfinished.txt").write_text("partial\n", encoding="utf-8")
    git(repository, "add", "--", "unfinished.txt")
    git(repository, "commit", "-m", "unfinished")
    git(repository, "switch", "main")
    store = TestStore()
    armed = {"restart": True}

    def fault(point: str) -> None:
        if point == "restart:after_restore" and armed.pop("restart", False):
            raise SystemExit("injected restore/sql crash")

    reconciliation = RepositoryReconciliationService(  # type: ignore[arg-type]
        store, fault_injector=fault
    )
    inventory = reconciliation._operations.inventory_repository(repository_root=repository)
    bundle = reconciliation._operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "preserved"
    )
    item = reconciliation._operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key="unfinished",
        classification="unfinished",
        disposition="restart",
        evidence={"remaining_obligation": "finish"},
    )
    kwargs = {
        "preservation_bundle_id": bundle["id"],
        "baseline_branch": "main",
        "worktree_root": tmp_path / "restart-worktrees",
    }
    with pytest.raises(SystemExit, match="restore/sql"):
        reconciliation.restart_unfinished_work(item["id"], **kwargs)
    restarted = reconciliation.restart_unfinished_work(item["id"], **kwargs)
    assert restarted["status"] == "ready"
    assert store.one("SELECT count(*) AS count FROM restart_workspaces_v2") == {"count": 1}


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
