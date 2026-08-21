from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .errors import InvalidTransition
from .util import (
    canonical_json,
    ensure_within,
    json_load,
    new_id,
    normalize_relative_path,
    utc_now,
)


class GitCommandError(RuntimeError):
    def __init__(self, command: Sequence[str], returncode: int, stdout: str, stderr: str):
        super().__init__(f"git command failed ({returncode}): {' '.join(command)}\n{stderr}")
        self.command = tuple(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run(
    command: Sequence[str], *, cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and process.returncode != 0:
        raise GitCommandError(command, process.returncode, process.stdout, process.stderr)
    return process


def _safe_branch(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._/-]+", "-", value.strip()).strip("-./")
    if not normalized or normalized.startswith("-") or ".." in normalized:
        raise ValueError(f"unsafe branch name: {value!r}")
    return normalized


class WorkspaceService:
    """Real Git branch/worktree lifecycle owner for implementation and candidate lanes."""

    def __init__(self, store: Any):
        self.store = store

    def workspace_path(self, workspace_id: str) -> Path:
        row = self.store.one("SELECT path FROM workspaces WHERE id=?", (workspace_id,))
        return Path(row["path"]).resolve()

    def repository_path(self, repository_id: str | None) -> Path:
        if repository_id is None:
            raise InvalidTransition("repository is required")
        row = self.store.one("SELECT path FROM repositories WHERE id=?", (repository_id,))
        return Path(row["path"]).resolve()

    def git_revision(self, path: str | Path) -> str:
        return _run(["git", "rev-parse", "HEAD"], cwd=Path(path)).stdout.strip()

    def git_tree(self, path: str | Path, revision: str = "HEAD") -> str:
        return _run(["git", "rev-parse", f"{revision}^{{tree}}"], cwd=Path(path)).stdout.strip()

    def git_is_clean(self, path: str | Path) -> bool:
        return not _run(["git", "status", "--porcelain=v1"], cwd=Path(path)).stdout.strip()

    def changed_files(
        self, path: str | Path, base_revision: str, revision: str = "HEAD"
    ) -> list[str]:
        output = _run(
            ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", base_revision, revision],
            cwd=Path(path),
        ).stdout
        return sorted(
            {normalize_relative_path(line) for line in output.splitlines() if line.strip()}
        )

    def create_workspace(
        self,
        *,
        repository_id: str,
        mission_id: str,
        work_item_id: str | None,
        workspace_type: str,
        branch: str | None = None,
        base_revision: str | None = None,
        workspace_root: str | Path | None = None,
        writable_scope: list[str] | None = None,
        exclusions: list[str] | None = None,
        created_by_execution_id: str | None = None,
    ) -> str:
        workspace_id = new_id("wsp")
        repository = self.store.one("SELECT * FROM repositories WHERE id=?", (repository_id,))
        if work_item_id:
            work = self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))
            if work["mission_id"] != mission_id:
                raise InvalidTransition("workspace work item belongs to another mission")
        repo_path = Path(repository["path"]).resolve()
        top = Path(_run(["git", "rev-parse", "--show-toplevel"], cwd=repo_path).stdout.strip())
        if top != repo_path:
            raise InvalidTransition("registered repository path is not its Git top level")
        base = base_revision or repository["current_revision"] or self.git_revision(repo_path)
        _run(["git", "rev-parse", "--verify", f"{base}^{{commit}}"], cwd=repo_path)
        policy = json_load(repository["workspace_policy_json"], {})
        root = Path(
            workspace_root
            or policy.get("workspace_root")
            or repo_path.parent / ".software-factory-worktrees"
        )
        root.mkdir(parents=True, exist_ok=True)
        branch_name = _safe_branch(branch or f"sf/{mission_id[:12]}/{workspace_id}")
        path = ensure_within(root / workspace_id, root)
        scope = sorted({normalize_relative_path(value) for value in (writable_scope or [])})
        excluded = sorted({normalize_relative_path(value) for value in (exclusions or [])})
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO workspaces(
                    id,repository_id,workspace_type,path,branch,base_revision,current_revision,
                    writable_scope_json,exclusions_json,status,created_at,updated_at,
                    mission_id,work_item_id,created_by_execution_id,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    workspace_id,
                    repository_id,
                    workspace_type,
                    str(path),
                    branch_name,
                    base,
                    None,
                    canonical_json(scope),
                    canonical_json(excluded),
                    "creating",
                    now,
                    now,
                    mission_id,
                    work_item_id,
                    created_by_execution_id,
                    1,
                ),
            )
        try:
            _run(["git", "worktree", "add", "-b", branch_name, str(path), base], cwd=repo_path)
            revision = self.git_revision(path)
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE workspaces SET status='ready',current_revision=?,updated_at=?,
                       state_version=2 WHERE id=?""",
                    (revision, utc_now(), workspace_id),
                )
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="workspace",
                    event_type="workspace.created",
                    subject_type="workspace",
                    subject_id=workspace_id,
                    new_version=2,
                    payload={
                        "repository_id": repository_id,
                        "work_item_id": work_item_id,
                        "type": workspace_type,
                        "path": str(path),
                        "branch": branch_name,
                        "base_revision": base,
                        "current_revision": revision,
                        "writable_scope": scope,
                    },
                )
        except Exception as exc:
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE workspaces SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), workspace_id),
                )
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="workspace",
                    event_type="workspace.create_failed",
                    subject_type="workspace",
                    subject_id=workspace_id,
                    payload={"error": {"type": type(exc).__name__, "message": str(exc)}},
                )
            raise
        return workspace_id

    def freeze_workspace(self, workspace_id: str, *, require_clean: bool = True) -> dict[str, Any]:
        workspace = self.store.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        path = Path(workspace["path"])
        if require_clean and not self.git_is_clean(path):
            raise InvalidTransition("candidate workspace must be committed and clean before freeze")
        revision = self.git_revision(path)
        tree = self.git_tree(path)
        changed = self.changed_files(path, workspace["base_revision"], revision)
        allowed = json_load(workspace["writable_scope_json"], [])
        for changed_path in changed:
            if (
                allowed
                and "*" not in allowed
                and not any(
                    changed_path == scope or changed_path.startswith(f"{scope}/")
                    for scope in allowed
                )
            ):
                raise InvalidTransition(
                    f"candidate changed path outside writable scope: {changed_path}"
                )
        with self.store.transaction() as db:
            current = db.execute("SELECT * FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
            version = int(current["state_version"]) + 1
            db.execute(
                """UPDATE workspaces SET status='frozen',current_revision=?,updated_at=?,
                   state_version=? WHERE id=?""",
                (revision, utc_now(), version, workspace_id),
            )
            self.store.append_event(
                db,
                mission_id=workspace["mission_id"],
                stream_key="workspace",
                event_type="workspace.frozen",
                subject_type="workspace",
                subject_id=workspace_id,
                prior_version=current["state_version"],
                new_version=version,
                payload={"revision": revision, "tree": tree, "changed_files": changed},
            )
        return {
            "workspace_id": workspace_id,
            "revision": revision,
            "tree": tree,
            "changed_files": changed,
        }

    def refresh_workspace_revision(self, workspace_id: str) -> str:
        workspace = self.store.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        revision = self.git_revision(workspace["path"])
        with self.store.transaction() as db:
            db.execute(
                "UPDATE workspaces SET current_revision=?,updated_at=? WHERE id=?",
                (revision, utc_now(), workspace_id),
            )
        return revision

    def retire_workspace(self, workspace_id: str, *, force: bool = False) -> None:
        workspace = self.store.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        if workspace["status"] == "retired":
            return
        if not force and not self.git_is_clean(workspace["path"]):
            raise InvalidTransition(
                "dirty workspace must be retained or preserved before retirement"
            )
        repository = self.store.one(
            "SELECT * FROM repositories WHERE id=?", (workspace["repository_id"],)
        )
        command = ["git", "worktree", "remove"]
        if force:
            command.append("--force")
        command.append(str(workspace["path"]))
        _run(command, cwd=Path(repository["path"]))
        with self.store.transaction() as db:
            db.execute(
                "UPDATE workspaces SET status='retired',updated_at=? WHERE id=?",
                (utc_now(), workspace_id),
            )
