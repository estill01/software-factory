from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .errors import InvalidTransition, StoreError
from .operations import OperationsService
from .store import Store
from .util import new_id, utc_now


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _git(
    root: Path,
    *args: str,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=input_text,
        capture_output=True,
        text=True,
        check=check,
    )


def _branch_head(root: Path, branch: str) -> str:
    result = _git(root, "rev-parse", "--verify", f"refs/heads/{branch}", check=False)
    if result.returncode != 0:
        raise StoreError(f"branch does not exist: {branch}")
    return result.stdout.strip()


def _worktrees(root: Path) -> list[dict[str, str]]:
    output = _git(root, "worktree", "list", "--porcelain").stdout
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return rows


@contextmanager
def _repository_lock(root: Path, name: str) -> Iterator[None]:
    common_dir = _git(root, "rev-parse", "--git-common-dir").stdout.strip()
    common_path = (root / common_dir).resolve() if not Path(common_dir).is_absolute() else Path(common_dir)
    lock_path = common_path / f"software-factory-{name}.lock"
    descriptor = -1
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        yield
    except FileExistsError as exc:
        raise InvalidTransition(f"repository effect is already locked: {name}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
            lock_path.unlink(missing_ok=True)


class RepositoryReconciliationService:
    """No-loss integration, publication, retirement, and unfinished-work restart."""

    def __init__(self, store: Store):
        self.store = store
        self.operations = OperationsService(store)

    def _item_and_bundle(
        self, cleanup_item_id: str, preservation_bundle_id: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        item = self.store.one(
            "SELECT * FROM cleanup_items_v2 WHERE id=?", (cleanup_item_id,)
        )
        bundle = self.store.one(
            "SELECT * FROM preservation_bundles_v2 WHERE id=?",
            (preservation_bundle_id,),
        )
        inventory = self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?",
            (item["inventory_id"],),
        )
        if bundle["inventory_id"] != item["inventory_id"] or not bundle["verified"]:
            raise InvalidTransition(
                "repository effect requires a verified bundle for the same inventory"
            )
        return item, bundle, inventory

    def prepare_integration(
        self,
        cleanup_item_id: str,
        *,
        preservation_bundle_id: str,
        target_branch: str,
        worktree_root: str | Path,
        validation_command: Sequence[str],
    ) -> dict[str, Any]:
        item, bundle, inventory = self._item_and_bundle(
            cleanup_item_id, preservation_bundle_id
        )
        if item["item_type"] != "branch":
            raise InvalidTransition("only a branch can be integrated")
        if item["classification"] != "accepted" or item["disposition"] != "integrate":
            raise InvalidTransition("branch is not accepted for integration")
        if not validation_command:
            raise ValueError("integration requires a validation command")
        repository = Path(inventory["repository_root"]).resolve()
        source_branch = str(item["item_key"])
        source_head = _branch_head(repository, source_branch)
        target_head = _branch_head(repository, target_branch)
        existing = self.store.one(
            """SELECT * FROM integration_candidates_v2
               WHERE cleanup_item_id=? AND source_head=? AND target_head_before=?""",
            (cleanup_item_id, source_head, target_head),
            required=False,
        )
        if existing is not None:
            return existing
        candidate_id = new_id("integration")
        integration_branch = f"sf/integration/{candidate_id}"
        root = Path(worktree_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        worktree = root / candidate_id
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO integration_candidates_v2(
                       id,cleanup_item_id,preservation_bundle_id,repository_root,
                       source_branch,source_head,target_branch,target_head_before,
                       integration_branch,integration_worktree,validation_command_json,
                       status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'planned',?,?)""",
                (
                    candidate_id,
                    cleanup_item_id,
                    bundle["id"],
                    str(repository),
                    source_branch,
                    source_head,
                    target_branch,
                    target_head,
                    integration_branch,
                    str(worktree),
                    _canonical(list(validation_command)),
                    now,
                    now,
                ),
            )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='running',updated_at=? WHERE id=?",
                (now, cleanup_item_id),
            )
        try:
            _git(
                repository,
                "worktree",
                "add",
                "-b",
                integration_branch,
                str(worktree),
                target_head,
            )
            _git(worktree, "config", "user.name", "software-factory-v2")
            _git(worktree, "config", "user.email", "software-factory-v2@invalid")
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE integration_candidates_v2
                       SET status='merging',updated_at=? WHERE id=?""",
                    (utc_now(), candidate_id),
                )
            merge = _git(
                worktree,
                "merge",
                "--no-ff",
                "--no-edit",
                source_head,
                check=False,
            )
            if merge.returncode != 0:
                _git(worktree, "merge", "--abort", check=False)
                raise RuntimeError(f"integration merge failed: {merge.stderr.strip()}")
            candidate_head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE integration_candidates_v2
                       SET candidate_head=?,status='validating',updated_at=? WHERE id=?""",
                    (candidate_head, utc_now(), candidate_id),
                )
            validation = subprocess.run(
                [str(value) for value in validation_command],
                cwd=worktree,
                capture_output=True,
                text=True,
                check=False,
            )
            validation_result = {
                "command": list(validation_command),
                "exit_code": validation.returncode,
                "stdout": validation.stdout,
                "stderr": validation.stderr,
            }
            if validation.returncode != 0:
                raise RuntimeError("integration validation failed")
        except BaseException as exc:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE integration_candidates_v2
                       SET status='failed',validation_result_json=?,updated_at=? WHERE id=?""",
                    (
                        _canonical(
                            locals().get(
                                "validation_result", {"error": str(exc)}
                            )
                        ),
                        utc_now(),
                        candidate_id,
                    ),
                )
                db.execute(
                    "UPDATE cleanup_items_v2 SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), cleanup_item_id),
                )
            _git(repository, "worktree", "remove", "--force", str(worktree), check=False)
            _git(repository, "branch", "-D", integration_branch, check=False)
            raise
        with self.store.transaction() as db:
            db.execute(
                """UPDATE integration_candidates_v2
                   SET status='accepted',validation_result_json=?,updated_at=? WHERE id=?""",
                (_canonical(validation_result), utc_now(), candidate_id),
            )
        return self.store.one(
            "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,)
        )

    def _target_worktree(
        self, repository: Path, target_branch: str
    ) -> Path | None:
        expected = f"refs/heads/{target_branch}"
        for row in _worktrees(repository):
            if row.get("branch") == expected and row.get("worktree"):
                return Path(row["worktree"]).resolve()
        return None

    def publish_integration(
        self,
        candidate_id: str,
        *,
        post_publish_validation: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        candidate = self.store.one(
            "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,)
        )
        if candidate["status"] == "published":
            return candidate
        if candidate["status"] != "accepted" or not candidate["candidate_head"]:
            raise InvalidTransition("integration candidate is not accepted")
        repository = Path(candidate["repository_root"])
        target_branch = str(candidate["target_branch"])
        target_before = str(candidate["target_head_before"])
        candidate_head = str(candidate["candidate_head"])
        with _repository_lock(repository, f"publish-{target_branch.replace('/', '-')}"):
            if _branch_head(repository, target_branch) != target_before:
                raise InvalidTransition(
                    "target branch advanced after integration validation"
                )
            target_worktree = self._target_worktree(repository, target_branch)
            if target_worktree is not None:
                if _git(
                    target_worktree, "status", "--porcelain=v1", check=False
                ).stdout.strip():
                    raise InvalidTransition(
                        "checked-out target branch has uncommitted work"
                    )
                _git(target_worktree, "merge", "--ff-only", candidate_head)
            else:
                result = _git(
                    repository,
                    "update-ref",
                    f"refs/heads/{target_branch}",
                    candidate_head,
                    target_before,
                    check=False,
                )
                if result.returncode != 0:
                    raise InvalidTransition(
                        "target compare-and-swap publication failed"
                    )
            if _branch_head(repository, target_branch) != candidate_head:
                raise RuntimeError("published target branch differs from accepted candidate")
            if post_publish_validation:
                validation_root = target_worktree or Path(candidate["integration_worktree"])
                validation = subprocess.run(
                    [str(value) for value in post_publish_validation],
                    cwd=validation_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if validation.returncode != 0:
                    if target_worktree is not None:
                        _git(target_worktree, "reset", "--hard", target_before)
                    else:
                        _git(
                            repository,
                            "update-ref",
                            f"refs/heads/{target_branch}",
                            target_before,
                            candidate_head,
                        )
                    with self.store.transaction() as db:
                        db.execute(
                            """UPDATE integration_candidates_v2
                               SET status='rolled_back',validation_result_json=?,
                                   completed_at=?,updated_at=? WHERE id=?""",
                            (
                                _canonical(
                                    {
                                        "phase": "post_publish",
                                        "exit_code": validation.returncode,
                                        "stdout": validation.stdout,
                                        "stderr": validation.stderr,
                                    }
                                ),
                                utc_now(),
                                utc_now(),
                                candidate_id,
                            ),
                        )
                    raise RuntimeError(
                        "post-publication validation failed and target was rolled back"
                    )
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE integration_candidates_v2
                   SET status='published',completed_at=?,updated_at=? WHERE id=?""",
                (now, now, candidate_id),
            )
            db.execute(
                """UPDATE cleanup_items_v2
                   SET status='completed',updated_at=? WHERE id=?""",
                (now, candidate["cleanup_item_id"]),
            )
        return self.store.one(
            "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,)
        )

    def retire_integration_lane(self, candidate_id: str) -> None:
        candidate = self.store.one(
            "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,)
        )
        if candidate["status"] not in {"published", "rolled_back", "failed"}:
            raise InvalidTransition(
                "integration lane cannot retire before publication or rollback"
            )
        repository = Path(candidate["repository_root"])
        worktree = Path(candidate["integration_worktree"])
        _git(repository, "worktree", "remove", "--force", str(worktree), check=False)
        _git(
            repository,
            "branch",
            "-D",
            candidate["integration_branch"],
            check=False,
        )

    def restart_unfinished_work(
        self,
        cleanup_item_id: str,
        *,
        preservation_bundle_id: str,
        baseline_branch: str,
        worktree_root: str | Path,
    ) -> dict[str, Any]:
        item, bundle, inventory = self._item_and_bundle(
            cleanup_item_id, preservation_bundle_id
        )
        if item["classification"] != "unfinished" or item["disposition"] != "restart":
            raise InvalidTransition("cleanup item is not classified for restart")
        if item["item_type"] not in {"branch", "stash", "detached_commit"}:
            raise InvalidTransition("cleanup item has no restart adapter")
        repository = Path(inventory["repository_root"])
        baseline_head = _branch_head(repository, baseline_branch)
        restart_id = new_id("restart")
        restart_branch = f"sf/restart/{restart_id}"
        root = Path(worktree_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        worktree = root / restart_id
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO restart_workspaces_v2(
                       id,cleanup_item_id,preservation_bundle_id,repository_root,
                       baseline_branch,baseline_head,restart_branch,restart_worktree,
                       restored_source_reference,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'creating',?,?)""",
                (
                    restart_id,
                    cleanup_item_id,
                    bundle["id"],
                    str(repository),
                    baseline_branch,
                    baseline_head,
                    restart_branch,
                    str(worktree),
                    item["item_key"],
                    now,
                    now,
                ),
            )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='running',updated_at=? WHERE id=?",
                (now, cleanup_item_id),
            )
        try:
            _git(
                repository,
                "worktree",
                "add",
                "-b",
                restart_branch,
                str(worktree),
                baseline_head,
            )
            if item["item_type"] in {"branch", "detached_commit"}:
                source_reference = (
                    _branch_head(repository, item["item_key"])
                    if item["item_type"] == "branch"
                    else str(item["item_key"])
                )
                patch = _git(
                    repository,
                    "diff",
                    "--binary",
                    f"{baseline_head}...{source_reference}",
                    check=False,
                ).stdout
                if patch.strip():
                    applied = _git(
                        worktree,
                        "apply",
                        "--3way",
                        "--index",
                        check=False,
                        input_text=patch,
                    )
                    if applied.returncode != 0:
                        raise RuntimeError(
                            f"unfinished branch could not be restored: {applied.stderr.strip()}"
                        )
            else:
                patch = _git(
                    repository,
                    "stash",
                    "show",
                    "-p",
                    "--binary",
                    item["item_key"],
                    check=False,
                ).stdout
                applied = _git(
                    worktree,
                    "apply",
                    "--3way",
                    "--index",
                    check=False,
                    input_text=patch,
                )
                if applied.returncode != 0:
                    raise RuntimeError(
                        f"stash could not be restored: {applied.stderr.strip()}"
                    )
        except BaseException:
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE restart_workspaces_v2 SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), restart_id),
                )
                db.execute(
                    "UPDATE cleanup_items_v2 SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), cleanup_item_id),
                )
            raise
        with self.store.transaction() as db:
            db.execute(
                "UPDATE restart_workspaces_v2 SET status='ready',updated_at=? WHERE id=?",
                (utc_now(), restart_id),
            )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='completed',updated_at=? WHERE id=?",
                (utc_now(), cleanup_item_id),
            )
        return self.store.one(
            "SELECT * FROM restart_workspaces_v2 WHERE id=?", (restart_id,)
        )

    def reconcile(
        self,
        *,
        repository_root: str | Path,
        mission_id: str | None,
        active_writers: Sequence[Mapping[str, Any]],
        classifications: Sequence[Mapping[str, Any]],
        preservation_directory: str | Path,
    ) -> dict[str, Any]:
        inventory = self.operations.inventory_repository(
            repository_root=repository_root,
            mission_id=mission_id,
            active_writers=active_writers,
        )
        bundle = self.operations.preserve_repository(
            inventory["id"], output_directory=preservation_directory
        )
        items: list[dict[str, Any]] = []
        for classification in classifications:
            item = self.operations.plan_cleanup_item(
                inventory["id"],
                item_type=str(classification["item_type"]),  # type: ignore[arg-type]
                item_key=str(classification["item_key"]),
                classification=str(classification.get("classification", "unknown")),  # type: ignore[arg-type]
                disposition=classification.get("disposition"),  # type: ignore[arg-type]
                evidence=classification.get("evidence")
                if isinstance(classification.get("evidence"), Mapping)
                else {},
            )
            items.append(item)
        return {
            "inventory": inventory,
            "preservation_bundle": bundle,
            "items": items,
            "unknown_defaults_to_retain": all(
                item["disposition"] == "retain"
                for item in items
                if item["classification"] == "unknown"
            ),
        }
