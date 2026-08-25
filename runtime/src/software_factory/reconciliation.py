from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import stat
import subprocess
import tarfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import InvalidTransition, StoreError
from .operations import OperationsService
from .store import Store
from .util import atomic_write, new_id, utc_now


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
    common_path = (
        (root / common_dir).resolve() if not Path(common_dir).is_absolute() else Path(common_dir)
    )
    lock_path = common_path / f"software-factory-{name}.lock"
    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class RepositoryReconciliationService:
    """No-loss integration, publication, retirement, and unfinished-work restart."""

    def __init__(
        self,
        store: Store,
        *,
        operations: OperationsService | None = None,
        fault_injector: Callable[[str], None] | None = None,
    ):
        self.store = store
        self._operations = operations or OperationsService(store)
        self._fault_injector = fault_injector

    def _fault(self, point: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    @staticmethod
    def _restart_receipt_path(worktree: Path, restart_id: str) -> Path:
        return worktree.parent / f".{restart_id}.restore.json"

    def _restart_state(
        self,
        *,
        worktree: Path,
        restart_id: str,
        cleanup_item_id: str,
        baseline_head: str,
        source_identity: str,
    ) -> dict[str, Any]:
        if _git(worktree, "diff", "--quiet", check=False).returncode != 0:
            raise InvalidTransition("restart workspace has unstaged changes")
        staged_patch = _git(worktree, "diff", "--cached", "--binary", check=False).stdout
        untracked_names = [
            value
            for value in _git(
                worktree,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                check=False,
            ).stdout.split("\0")
            if value
        ]
        untracked: list[dict[str, Any]] = []
        for relative in sorted(untracked_names):
            pure = PurePosixPath(relative)
            if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                raise InvalidTransition("restart workspace has an unsafe untracked path")
            path = worktree.joinpath(*pure.parts)
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise InvalidTransition("restart workspace has a non-file untracked entry")
            untracked.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": metadata.st_size,
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
        return {
            "restart_id": restart_id,
            "cleanup_item_id": cleanup_item_id,
            "baseline_head": baseline_head,
            "source_identity": source_identity,
            "staged_patch_root": hashlib.sha256(staged_patch.encode()).hexdigest(),
            "untracked_files": untracked,
            "status": _git(worktree, "status", "--porcelain=v1", check=False).stdout.splitlines(),
        }

    @staticmethod
    def _write_restart_receipt(path: Path, payload: Mapping[str, Any]) -> None:
        atomic_write(
            path,
            (_canonical(dict(payload)) + "\n").encode("utf-8"),
            mode=0o600,
        )

    @staticmethod
    def _inventory_source_identity(item: Mapping[str, Any], inventory: Mapping[str, Any]) -> str:
        if item["item_type"] == "branch":
            matches = [
                value.split("|", 2)[1]
                for value in _loads(inventory["branches_json"], [])
                if isinstance(value, str)
                and value.split("|", 1)[0] == item["item_key"]
                and len(value.split("|", 2)) >= 2
            ]
        elif item["item_type"] == "stash":
            matches = [
                value.split("|", 2)[1]
                for value in _loads(inventory["stashes_json"], [])
                if isinstance(value, str)
                and value.split("|", 1)[0] == item["item_key"]
                and len(value.split("|", 2)) >= 2
            ]
        else:
            matches = [
                str(item["item_key"])
                for value in _loads(inventory["detached_commits_json"], [])
                if isinstance(value, str) and str(item["item_key"]) in value.split()
            ]
        if len(matches) != 1 or not matches[0]:
            raise InvalidTransition("restart source was not exact in the inventory")
        return matches[0]

    @staticmethod
    def _bundle_restore_members(
        bundle: Mapping[str, Any],
    ) -> tuple[str, bytes, list[str]]:
        manifest = _loads(bundle["manifest_json"], {})
        if not isinstance(manifest, dict):
            raise InvalidTransition("preservation bundle manifest is invalid")
        try:
            with tarfile.open(Path(str(bundle["bundle_path"])), "r:gz") as archive:
                patch_member = archive.getmember("working-tree.patch")
                untracked_member = archive.getmember("untracked.tar")
                patch_handle = archive.extractfile(patch_member)
                untracked_handle = archive.extractfile(untracked_member)
                if patch_handle is None or untracked_handle is None:
                    raise InvalidTransition("preservation bundle restore members are unreadable")
                patch = patch_handle.read().decode("utf-8")
                untracked = untracked_handle.read()
        except (KeyError, OSError, UnicodeDecodeError, tarfile.TarError) as exc:
            raise InvalidTransition("preservation bundle restore members are invalid") from exc
        paths = manifest.get("untracked_paths", [])
        if not isinstance(paths, list) or any(not isinstance(value, str) for value in paths):
            raise InvalidTransition("preservation bundle untracked path manifest is invalid")
        return patch, untracked, sorted(paths)

    @staticmethod
    def _item_owns_inventory_worktree(
        item: Mapping[str, Any], inventory: Mapping[str, Any], source_identity: str
    ) -> bool:
        if item["item_type"] != "branch":
            return False
        repository = str(Path(str(inventory["repository_root"])).resolve())
        return any(
            isinstance(value, dict)
            and str(Path(str(value.get("worktree", ""))).resolve()) == repository
            and value.get("HEAD") == source_identity
            and value.get("branch") == f"refs/heads/{item['item_key']}"
            for value in _loads(inventory["worktrees_json"], [])
        )

    @staticmethod
    def _restore_untracked(worktree: Path, archive_bytes: bytes, expected_paths: list[str]) -> None:
        try:
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
                members = archive.getmembers()
                names = [member.name for member in members]
                if sorted(names) != expected_paths or len(set(names)) != len(names):
                    raise InvalidTransition("preserved untracked member set differs")
                for member in members:
                    pure = PurePosixPath(member.name)
                    if (
                        not member.isfile()
                        or member.issym()
                        or member.islnk()
                        or pure.is_absolute()
                        or any(part in {"", ".", ".."} for part in pure.parts)
                    ):
                        raise InvalidTransition("preserved untracked member is unsafe")
                    target = worktree.joinpath(*pure.parts)
                    try:
                        target.resolve().relative_to(worktree)
                    except ValueError as exc:
                        raise InvalidTransition(
                            "preserved untracked member escapes worktree"
                        ) from exc
                    if target.exists() or target.is_symlink():
                        raise InvalidTransition("preserved untracked member collides in worktree")
                    if (
                        _git(
                            worktree,
                            "ls-files",
                            "--error-unmatch",
                            "--",
                            member.name,
                            check=False,
                        ).returncode
                        == 0
                    ):
                        raise InvalidTransition(
                            "preserved untracked member collides with tracked data"
                        )
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise InvalidTransition("preserved untracked member is unreadable")
                    atomic_write(target, handle.read(), mode=stat.S_IMODE(member.mode))
        except (OSError, tarfile.TarError) as exc:
            raise InvalidTransition("preserved untracked archive is invalid") from exc

    def _require_restart_receipt(self, path: Path, expected: Mapping[str, Any]) -> None:
        if not path.is_file() or path.is_symlink():
            raise InvalidTransition("restart workspace lacks an exact restoration receipt")
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidTransition("restart restoration receipt is invalid") from exc
        if actual != dict(expected):
            raise InvalidTransition("restart restoration receipt differs from workspace state")

    def _item_and_bundle(
        self, cleanup_item_id: str, preservation_bundle_id: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        item = self.store.one("SELECT * FROM cleanup_items_v2 WHERE id=?", (cleanup_item_id,))
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
        self._operations._require_verified_bundle(bundle)
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
        item, bundle, inventory = self._item_and_bundle(cleanup_item_id, preservation_bundle_id)
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
        if existing is not None and existing["status"] in {"accepted", "published"}:
            return existing
        root = Path(worktree_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        if existing is not None:
            if existing["status"] in {"failed", "rolled_back"}:
                raise InvalidTransition("integration candidate is terminal and cannot resume")
            if _loads(existing["validation_command_json"], []) != list(validation_command):
                raise InvalidTransition("integration retry validation command differs")
            candidate_id = str(existing["id"])
            integration_branch = str(existing["integration_branch"])
            worktree = Path(existing["integration_worktree"])
        else:
            candidate_id = new_id("integration")
            integration_branch = f"sf/integration/{candidate_id}"
            worktree = root / candidate_id
        now = utc_now()
        if existing is None:
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
            if not worktree.is_dir():
                branch_exists = (
                    _git(
                        repository,
                        "show-ref",
                        "--verify",
                        "--quiet",
                        f"refs/heads/{integration_branch}",
                        check=False,
                    ).returncode
                    == 0
                )
                if branch_exists:
                    _git(repository, "worktree", "add", str(worktree), integration_branch)
                else:
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
            current_head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
            if current_head == target_head:
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
            else:
                source_in_candidate = (
                    _git(
                        worktree,
                        "merge-base",
                        "--is-ancestor",
                        source_head,
                        current_head,
                        check=False,
                    ).returncode
                    == 0
                )
                target_in_candidate = (
                    _git(
                        worktree,
                        "merge-base",
                        "--is-ancestor",
                        target_head,
                        current_head,
                        check=False,
                    ).returncode
                    == 0
                )
                if not source_in_candidate or not target_in_candidate:
                    raise InvalidTransition("integration worktree head differs from planned merge")
                candidate_head = current_head
            self._fault("prepare:after_merge")
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
            self._fault("prepare:after_validation")
        except Exception as exc:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE integration_candidates_v2
                       SET status='failed',validation_result_json=?,updated_at=? WHERE id=?""",
                    (
                        _canonical(locals().get("validation_result", {"error": str(exc)})),
                        utc_now(),
                        candidate_id,
                    ),
                )
                db.execute(
                    "UPDATE cleanup_items_v2 SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), cleanup_item_id),
                )
            raise
        with self.store.transaction() as db:
            db.execute(
                """UPDATE integration_candidates_v2
                   SET status='accepted',validation_result_json=?,updated_at=? WHERE id=?""",
                (_canonical(validation_result), utc_now(), candidate_id),
            )
        return self.store.one("SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,))

    def _target_worktree(self, repository: Path, target_branch: str) -> Path | None:
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
            current_head = _branch_head(repository, target_branch)
            if current_head not in {target_before, candidate_head}:
                raise InvalidTransition("target branch advanced after integration validation")
            target_worktree = self._target_worktree(repository, target_branch)
            if (
                target_worktree is not None
                and _git(target_worktree, "status", "--porcelain=v1", check=False).stdout.strip()
            ):
                raise InvalidTransition("checked-out target branch has uncommitted work")
            if current_head == target_before and target_worktree is not None:
                _git(target_worktree, "merge", "--ff-only", candidate_head)
            elif current_head == target_before:
                result = _git(
                    repository,
                    "update-ref",
                    f"refs/heads/{target_branch}",
                    candidate_head,
                    target_before,
                    check=False,
                )
                if result.returncode != 0:
                    raise InvalidTransition("target compare-and-swap publication failed")
            if _branch_head(repository, target_branch) != candidate_head:
                raise RuntimeError("published target branch differs from accepted candidate")
            self._fault("publish:after_ref_update")
            if post_publish_validation:
                validation_root = Path(candidate["integration_worktree"])
                validation = subprocess.run(
                    [str(value) for value in post_publish_validation],
                    cwd=validation_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if validation.returncode != 0:
                    rollback = _git(
                        repository,
                        "update-ref",
                        f"refs/heads/{target_branch}",
                        target_before,
                        candidate_head,
                        check=False,
                    )
                    if rollback.returncode != 0:
                        raise InvalidTransition("post-publication rollback compare-and-swap failed")
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
            self._fault("publish:after_validation")
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
        return self.store.one("SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,))

    def retire_integration_lane(self, candidate_id: str) -> None:
        candidate = self.store.one(
            "SELECT * FROM integration_candidates_v2 WHERE id=?", (candidate_id,)
        )
        if candidate["status"] not in {"published", "rolled_back", "failed"}:
            raise InvalidTransition("integration lane cannot retire before publication or rollback")
        raise InvalidTransition(
            "integration lane must be preserved or deferred because Git has no deletion "
            "adapter that atomically fences tracked, untracked, ref, and worktree currentness"
        )

    def restart_unfinished_work(
        self,
        cleanup_item_id: str,
        *,
        preservation_bundle_id: str,
        baseline_branch: str,
        worktree_root: str | Path,
    ) -> dict[str, Any]:
        item, bundle, inventory = self._item_and_bundle(cleanup_item_id, preservation_bundle_id)
        if item["classification"] != "unfinished" or item["disposition"] != "restart":
            raise InvalidTransition("cleanup item is not classified for restart")
        if item["item_type"] not in {"branch", "stash", "detached_commit"}:
            raise InvalidTransition("cleanup item has no restart adapter")
        repository = Path(inventory["repository_root"])
        baseline_head = _branch_head(repository, baseline_branch)
        source_identity = self._inventory_source_identity(item, inventory)
        if (
            _git(
                repository,
                "cat-file",
                "-e",
                f"{source_identity}^{{commit}}",
                check=False,
            ).returncode
            != 0
        ):
            raise InvalidTransition("restart preserved source object is unavailable")
        owns_inventory_worktree = self._item_owns_inventory_worktree(
            item, inventory, source_identity
        )
        working_patch, untracked_archive, untracked_paths = self._bundle_restore_members(bundle)
        if not owns_inventory_worktree and (working_patch.strip() or untracked_paths):
            working_patch = ""
            untracked_archive = b""
            untracked_paths = []
        root = Path(worktree_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        existing = self.store.one(
            """SELECT * FROM restart_workspaces_v2
               WHERE cleanup_item_id=? AND baseline_head=?""",
            (cleanup_item_id, baseline_head),
            required=False,
        )
        if existing is not None and existing["status"] == "ready":
            worktree = Path(existing["restart_worktree"])
            if (
                not worktree.is_dir()
                or _git(worktree, "rev-parse", "HEAD", check=False).stdout.strip() != baseline_head
            ):
                raise InvalidTransition("ready restart workspace physical state differs")
            state = self._restart_state(
                worktree=worktree,
                restart_id=str(existing["id"]),
                cleanup_item_id=cleanup_item_id,
                baseline_head=baseline_head,
                source_identity=source_identity,
            )
            self._require_restart_receipt(
                self._restart_receipt_path(worktree, str(existing["id"])), state
            )
            return existing
        restart_id = existing["id"] if existing else new_id("restart")
        restart_branch = str(existing["restart_branch"]) if existing else f"sf/restart/{restart_id}"
        worktree = Path(existing["restart_worktree"]) if existing else root / restart_id
        now = utc_now()
        if existing is None:
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
            if not worktree.is_dir():
                branch_exists = (
                    _git(
                        repository,
                        "show-ref",
                        "--verify",
                        "--quiet",
                        f"refs/heads/{restart_branch}",
                        check=False,
                    ).returncode
                    == 0
                )
                if branch_exists:
                    _git(repository, "worktree", "add", str(worktree), restart_branch)
                else:
                    _git(
                        repository,
                        "worktree",
                        "add",
                        "-b",
                        restart_branch,
                        str(worktree),
                        baseline_head,
                    )
            elif _git(worktree, "rev-parse", "HEAD", check=False).stdout.strip() != baseline_head:
                raise InvalidTransition("restart workspace baseline differs")
            receipt_path = self._restart_receipt_path(worktree, restart_id)
            already_restored = receipt_path.exists()
            if already_restored:
                state = self._restart_state(
                    worktree=worktree,
                    restart_id=restart_id,
                    cleanup_item_id=cleanup_item_id,
                    baseline_head=baseline_head,
                    source_identity=source_identity,
                )
                self._require_restart_receipt(receipt_path, state)
            elif _git(worktree, "status", "--porcelain=v1", check=False).stdout.strip():
                raise InvalidTransition(
                    "restart workspace changed without an exact restoration receipt"
                )
            if not already_restored and item["item_type"] in {"branch", "detached_commit"}:
                patch = _git(
                    repository,
                    "diff",
                    "--binary",
                    f"{baseline_head}...{source_identity}",
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
            elif not already_restored:
                patch = _git(
                    repository,
                    "stash",
                    "show",
                    "-p",
                    "--binary",
                    source_identity,
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
                    raise RuntimeError(f"stash could not be restored: {applied.stderr.strip()}")
            if not already_restored:
                if working_patch.strip():
                    restored_working = _git(
                        worktree,
                        "apply",
                        "--3way",
                        "--index",
                        check=False,
                        input_text=working_patch,
                    )
                    if restored_working.returncode != 0:
                        raise RuntimeError(
                            "unfinished working tree could not be restored: "
                            f"{restored_working.stderr.strip()}"
                        )
                if untracked_paths:
                    self._restore_untracked(worktree, untracked_archive, untracked_paths)
                state = self._restart_state(
                    worktree=worktree,
                    restart_id=restart_id,
                    cleanup_item_id=cleanup_item_id,
                    baseline_head=baseline_head,
                    source_identity=source_identity,
                )
                self._write_restart_receipt(receipt_path, state)
            self._fault("restart:after_restore")
        except Exception:
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
        return self.store.one("SELECT * FROM restart_workspaces_v2 WHERE id=?", (restart_id,))

    def reconcile(
        self,
        *,
        repository_root: str | Path,
        mission_id: str | None,
        active_writers: Sequence[Mapping[str, Any]],
        classifications: Sequence[Mapping[str, Any]],
        preservation_directory: str | Path,
    ) -> dict[str, Any]:
        inventory = self._operations.inventory_repository(
            repository_root=repository_root,
            mission_id=mission_id,
            active_writers=active_writers,
        )
        bundle = self._operations.preserve_repository(
            inventory["id"], output_directory=preservation_directory
        )
        items: list[dict[str, Any]] = []
        for classification in classifications:
            item = self._operations.plan_cleanup_item(
                inventory["id"],
                item_type=str(classification["item_type"]),  # type: ignore[arg-type]
                item_key=str(classification["item_key"]),
                classification=str(classification.get("classification", "unknown")),  # type: ignore[arg-type]
                disposition=classification.get("disposition"),
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
