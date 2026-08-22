from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import new_id, utc_now


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _ids(values: Sequence[str] | None) -> list[str]:
    return sorted({str(value) for value in (values or ()) if str(value)})


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=check,
    )


class OperationsService:
    """Physical owners for immutable release, systemic recovery, and cleanup."""

    def __init__(self, store: Store):
        self.store = store

    def _manifest(self, source_root: Path) -> tuple[list[dict[str, Any]], str]:
        entries: list[dict[str, Any]] = []
        for path in sorted(source_root.rglob("*")):
            relative = path.relative_to(source_root).as_posix()
            if not relative or relative == ".git" or relative.startswith(".git/"):
                continue
            if path.is_symlink():
                raise ValueError(f"release source contains a symlink: {relative}")
            if path.is_file():
                mode = stat.S_IMODE(path.stat().st_mode)
                entries.append(
                    {
                        "path": relative,
                        "sha256": _file_digest(path),
                        "bytes": path.stat().st_size,
                        "executable": bool(mode & stat.S_IXUSR),
                    }
                )
        return entries, _digest(entries)

    def stage_release(
        self,
        *,
        source_root: str | Path,
        release_root: str | Path,
        source_revision: str,
        source_tree_root: str,
        mission_id: str | None = None,
        implementer_session_id: str | None = None,
    ) -> dict[str, Any]:
        source = Path(source_root).resolve()
        releases = Path(release_root).resolve()
        if not source.is_dir():
            raise ValueError("release source root does not exist")
        manifest, manifest_root = self._manifest(source)
        existing = self.store.one(
            """SELECT * FROM immutable_releases_v2
               WHERE source_revision=? AND manifest_root=?""",
            (source_revision, manifest_root),
            required=False,
        )
        if existing is not None:
            return existing
        release_id = new_id("release")
        releases.mkdir(parents=True, exist_ok=True)
        destination = releases / release_id
        temporary = Path(tempfile.mkdtemp(prefix=f".{release_id}.", dir=releases))
        try:
            for entry in manifest:
                source_path = source / entry["path"]
                target = temporary / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target, follow_symlinks=False)
                target.chmod(0o555 if entry["executable"] else 0o444)
            manifest_payload = {
                "release_id": release_id,
                "source_revision": source_revision,
                "source_tree_root": source_tree_root,
                "manifest_root": manifest_root,
                "files": manifest,
            }
            manifest_path = temporary / "release-manifest.json"
            manifest_path.write_text(_canonical(manifest_payload) + "\n", encoding="utf-8")
            manifest_path.chmod(0o444)
            temporary.replace(destination)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        now = utc_now()
        try:
            with self.store.transaction() as db:
                db.execute(
                    """INSERT INTO immutable_releases_v2(
                           id,mission_id,source_revision,source_tree_root,manifest_root,
                           release_path,manifest_json,implementer_session_id,
                           status,staged_at,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?,'staged',?,?)""",
                    (
                        release_id,
                        mission_id,
                        source_revision,
                        source_tree_root,
                        manifest_root,
                        str(destination),
                        _canonical(manifest_payload),
                        implementer_session_id,
                        now,
                        now,
                    ),
                )
        except BaseException:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))

    def review_release(
        self,
        release_id: str,
        *,
        reviewer_session_id: str,
        disposition: Literal["accepted", "rejected", "revise"],
        findings: Mapping[str, Any],
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if release["status"] != "staged":
            raise InvalidTransition("only a staged release may be reviewed")
        if reviewer_session_id == release["implementer_session_id"]:
            raise InvalidTransition("release implementer cannot independently review it")
        evidence = _ids(evidence_ids)
        if not evidence:
            raise ValueError("release review requires evidence")
        review_root = _digest(
            {
                "release_id": release_id,
                "manifest_root": release["manifest_root"],
                "disposition": disposition,
                "findings": dict(findings),
                "evidence_ids": evidence,
            }
        )
        review_id = new_id("release-review")
        status = "accepted" if disposition == "accepted" else (
            "rejected" if disposition == "rejected" else "staged"
        )
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO release_reviews_v2(
                       id,release_id,reviewer_session_id,disposition,findings_json,
                       evidence_ids_json,review_root,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    review_id,
                    release_id,
                    reviewer_session_id,
                    disposition,
                    _canonical(dict(findings)),
                    _canonical(evidence),
                    review_root,
                    utc_now(),
                ),
            )
            db.execute(
                """UPDATE immutable_releases_v2
                   SET reviewer_session_id=?,review_status=?,status=?,updated_at=? WHERE id=?""",
                (reviewer_session_id, disposition, status, utc_now(), release_id),
            )
        return self.store.one("SELECT * FROM release_reviews_v2 WHERE id=?", (review_id,))

    def _write_active_pointer(self, release_root: Path, payload: Mapping[str, Any]) -> None:
        release_root.mkdir(parents=True, exist_ok=True)
        pointer = release_root / "active-release.json"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".active-release.", suffix=".tmp", dir=release_root
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(_canonical(dict(payload)) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(temporary_name).replace(pointer)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def activate_release(
        self,
        release_id: str,
        *,
        release_root: str | Path,
    ) -> dict[str, Any]:
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if release["review_status"] != "accepted" or release["status"] != "accepted":
            raise InvalidTransition("release must pass independent review before activation")
        previous = self.store.one(
            """SELECT * FROM immutable_releases_v2 WHERE status='active'
               ORDER BY activated_at DESC LIMIT 1""",
            required=False,
        )
        payload = {
            "release_id": release_id,
            "release_path": release["release_path"],
            "manifest_root": release["manifest_root"],
            "source_revision": release["source_revision"],
            "previous_release_id": previous["id"] if previous else None,
        }
        self._write_active_pointer(Path(release_root).resolve(), payload)
        now = utc_now()
        with self.store.transaction() as db:
            if previous is not None:
                db.execute(
                    """UPDATE immutable_releases_v2
                       SET status='superseded',deactivated_at=?,updated_at=? WHERE id=?""",
                    (now, now, previous["id"]),
                )
            db.execute(
                """UPDATE immutable_releases_v2
                   SET status='active',previous_release_id=?,activated_at=?,updated_at=?
                   WHERE id=?""",
                (previous["id"] if previous else None, now, now, release_id),
            )
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))

    def verify_release(
        self,
        release_id: str,
        *,
        command: Sequence[str],
        release_root: str | Path,
        verification_type: Literal["fresh_process", "installed", "health"] = "fresh_process",
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if release["status"] != "active":
            raise InvalidTransition("only the active release may be installed-verified")
        process = subprocess.run(
            [str(part) for part in command],
            cwd=release["release_path"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        disposition = "passed" if process.returncode == 0 else "failed"
        evidence_root = _digest(
            {
                "release_id": release_id,
                "manifest_root": release["manifest_root"],
                "command": list(command),
                "exit_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
            }
        )
        verification_id = new_id("release-verification")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO release_verifications_v2(
                       id,release_id,verification_type,command_json,exit_code,
                       stdout_text,stderr_text,evidence_root,disposition,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    verification_id,
                    release_id,
                    verification_type,
                    _canonical(list(command)),
                    process.returncode,
                    process.stdout,
                    process.stderr,
                    evidence_root,
                    disposition,
                    utc_now(),
                ),
            )
            db.execute(
                """UPDATE immutable_releases_v2
                   SET verification_status=?,updated_at=? WHERE id=?""",
                (disposition, utc_now(), release_id),
            )
        if disposition == "failed":
            self.rollback_release(
                release_id,
                release_root=release_root,
                evidence_ids=[evidence_root],
            )
        return self.store.one(
            "SELECT * FROM release_verifications_v2 WHERE id=?", (verification_id,)
        )

    def rollback_release(
        self,
        release_id: str,
        *,
        release_root: str | Path,
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if not evidence_ids:
            raise ValueError("release rollback requires evidence")
        previous = None
        if release["previous_release_id"]:
            previous = self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?",
                (release["previous_release_id"],),
            )
        payload = (
            {
                "release_id": previous["id"],
                "release_path": previous["release_path"],
                "manifest_root": previous["manifest_root"],
                "source_revision": previous["source_revision"],
                "rolled_back_from": release_id,
            }
            if previous is not None
            else {"release_id": None, "rolled_back_from": release_id}
        )
        self._write_active_pointer(Path(release_root).resolve(), payload)
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE immutable_releases_v2
                   SET status='rolled_back',deactivated_at=?,updated_at=? WHERE id=?""",
                (now, now, release_id),
            )
            if previous is not None:
                db.execute(
                    """UPDATE immutable_releases_v2
                       SET status='active',deactivated_at=NULL,updated_at=? WHERE id=?""",
                    (now, previous["id"]),
                )
            db.execute(
                """INSERT INTO release_verifications_v2(
                       id,release_id,verification_type,evidence_root,disposition,created_at
                   ) VALUES(?,?,'rollback',?,'passed',?)""",
                (new_id("release-verification"), release_id, _digest(_ids(evidence_ids)), now),
            )
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))

    def plan_agent_refresh(
        self,
        release_id: str,
        agents: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if release["status"] != "active" or release["verification_status"] != "passed":
            raise InvalidTransition("agents refresh only after installed release verification")
        refreshes: list[dict[str, Any]] = []
        for agent in agents:
            refresh_id = new_id("agent-refresh")
            boundary = str(agent.get("safe_boundary", "after_current_effect"))
            with self.store.transaction() as db:
                db.execute(
                    """INSERT OR IGNORE INTO release_agent_refreshes_v2(
                           id,release_id,agent_session_id,boundary_type,prior_revision,
                           target_revision,status,evidence_ids_json,created_at,updated_at
                       ) VALUES(?,?,?,?,?,?,'pending','[]',?,?)""",
                    (
                        refresh_id,
                        release_id,
                        agent["id"],
                        boundary,
                        agent.get("runtime_revision"),
                        release["source_revision"],
                        utc_now(),
                        utc_now(),
                    ),
                )
            refreshes.append(
                self.store.one(
                    """SELECT * FROM release_agent_refreshes_v2
                       WHERE release_id=? AND agent_session_id=?""",
                    (release_id, agent["id"]),
                )
            )
        return refreshes

    def open_recovery(
        self,
        *,
        target_mission_id: str,
        defect_class: str,
        defect_evidence: Mapping[str, Any],
        target_state: Mapping[str, Any],
        requested_range_root: str,
        tracker_currentness_root: str,
        safe_frontier: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if self.store.one(
            "SELECT id FROM missions WHERE id=?", (target_mission_id,), required=False
        ) is None:
            raise StoreError(f"mission not found: {target_mission_id}")
        defect_fingerprint = _digest(
            {"defect_class": defect_class, "defect_evidence": dict(defect_evidence)}
        )
        placeholders = ",".join("?" for _ in range(8))
        active_statuses = (
            "detected",
            "repairing",
            "qa",
            "releasing",
            "restoring",
            "resuming",
            "verifying",
            "failed",
        )
        existing = self.store.one(
            f"""SELECT * FROM factory_recovery_cases_v2
                WHERE target_mission_id=? AND defect_fingerprint=?
                  AND status IN ({placeholders}) ORDER BY opened_at DESC LIMIT 1""",
            (target_mission_id, defect_fingerprint, *active_statuses),
            required=False,
        )
        if existing is not None:
            return existing
        recovery_id = new_id("factory-recovery")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO factory_recovery_cases_v2(
                       id,target_mission_id,defect_class,defect_fingerprint,target_state_json,
                       requested_range_root,tracker_currentness_root,safe_frontier_json,
                       status,opened_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,'detected',?,?)""",
                (
                    recovery_id,
                    target_mission_id,
                    defect_class,
                    defect_fingerprint,
                    _canonical(dict(target_state)),
                    requested_range_root,
                    tracker_currentness_root,
                    _canonical([dict(item) for item in safe_frontier]),
                    now,
                    now,
                ),
            )
        return self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )

    def record_repair(
        self,
        recovery_id: str,
        *,
        repair_revision: str,
        evidence_ids: Sequence[str],
        release_id: str,
    ) -> dict[str, Any]:
        recovery = self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )
        if recovery["status"] not in {"detected", "repairing", "qa", "releasing", "failed"}:
            raise InvalidTransition("recovery is not awaiting a repaired release")
        release = self.store.one(
            "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
        )
        if release["source_revision"] != repair_revision:
            raise InvalidTransition("recovery repair revision differs from release revision")
        if release["verification_status"] != "passed":
            raise InvalidTransition("recovery release is not installed-verified")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE factory_recovery_cases_v2
                   SET repair_revision=?,repair_evidence_ids_json=?,release_id=?,
                       status='restoring',updated_at=? WHERE id=?""",
                (repair_revision, _canonical(_ids(evidence_ids)), release_id, utc_now(), recovery_id),
            )
        return self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )

    def reserve_exact_once_resume(
        self,
        recovery_id: str,
        *,
        requested_range_root: str,
        tracker_currentness_root: str,
        wake_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        recovery = self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )
        if recovery["status"] not in {"restoring", "resuming"}:
            raise InvalidTransition("recovery has not reached target restoration")
        if recovery["requested_range_root"] != requested_range_root:
            raise InvalidTransition("recovery requested range was not restored")
        if recovery["tracker_currentness_root"] != tracker_currentness_root:
            raise InvalidTransition("recovery tracker currentness was not restored")
        resume_key = _digest(
            {
                "recovery_id": recovery_id,
                "target_mission_id": recovery["target_mission_id"],
                "repair_revision": recovery["repair_revision"],
                "wake_payload": dict(wake_payload),
            }
        )
        existing = self.store.one(
            "SELECT * FROM recovery_resume_tokens_v2 WHERE recovery_id=?",
            (recovery_id,),
            required=False,
        )
        if existing is not None:
            return existing
        token_id = new_id("resume-token")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO recovery_resume_tokens_v2(
                       id,recovery_id,target_mission_id,resume_key,wake_payload_json,
                       status,reserved_at
                   ) VALUES(?,?,?,?,?,'reserved',?)""",
                (
                    token_id,
                    recovery_id,
                    recovery["target_mission_id"],
                    resume_key,
                    _canonical(dict(wake_payload)),
                    now,
                ),
            )
            db.execute(
                """UPDATE factory_recovery_cases_v2
                   SET status='resuming',updated_at=? WHERE id=?""",
                (now, recovery_id),
            )
        return self.store.one("SELECT * FROM recovery_resume_tokens_v2 WHERE id=?", (token_id,))

    def mark_resume_sent(self, token_id: str) -> dict[str, Any]:
        token = self.store.one(
            "SELECT * FROM recovery_resume_tokens_v2 WHERE id=?", (token_id,)
        )
        if token["status"] == "sent":
            return token
        if token["status"] != "reserved":
            raise InvalidTransition("resume token is not sendable")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE recovery_resume_tokens_v2
                   SET status='sent',sent_at=? WHERE id=? AND status='reserved'""",
                (now, token_id),
            )
            changed = db.execute("SELECT changes() AS count").fetchone()["count"]
            if changed != 1:
                raise InvalidTransition("resume token was consumed concurrently")
            db.execute(
                """UPDATE factory_recovery_cases_v2
                   SET resume_count=resume_count+1,status='verifying',updated_at=?
                   WHERE id=?""",
                (now, token["recovery_id"]),
            )
        return self.store.one("SELECT * FROM recovery_resume_tokens_v2 WHERE id=?", (token_id,))

    def verify_recovery(
        self,
        recovery_id: str,
        *,
        target_resumed: bool,
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        recovery = self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )
        if recovery["status"] != "verifying":
            raise InvalidTransition("recovery is not awaiting effectiveness verification")
        if recovery["resume_count"] != 1:
            raise InvalidTransition("target was not resumed exactly once")
        status = "resolved" if target_resumed and evidence_ids else "failed"
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE factory_recovery_cases_v2
                   SET status=?,resolved_at=?,updated_at=? WHERE id=?""",
                (status, now if status == "resolved" else None, now, recovery_id),
            )
        return self.store.one(
            "SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,)
        )

    def inventory_repository(
        self,
        *,
        repository_root: str | Path,
        mission_id: str | None = None,
        active_writers: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        root = Path(repository_root).resolve()
        head = _run_git(root, "rev-parse", "HEAD", check=False).stdout.strip() or None
        branches = [
            line for line in _run_git(root, "for-each-ref", "--format=%(refname:short)|%(objectname)|%(upstream:short)", "refs/heads", check=False).stdout.splitlines() if line
        ]
        worktrees_raw = _run_git(root, "worktree", "list", "--porcelain", check=False).stdout
        worktrees: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in worktrees_raw.splitlines() + [""]:
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue
            key, _, value = line.partition(" ")
            current[key] = value
        stashes = [
            line for line in _run_git(root, "stash", "list", "--format=%gd|%H|%gs", check=False).stdout.splitlines() if line
        ]
        status_lines = _run_git(root, "status", "--porcelain=v2", "--untracked-files=all", check=False).stdout.splitlines()
        detached = [
            line
            for line in _run_git(root, "fsck", "--unreachable", "--no-reflogs", check=False).stdout.splitlines()
            if "commit" in line
        ]
        payload = {
            "repository_root": str(root),
            "head": head,
            "branches": branches,
            "worktrees": worktrees,
            "stashes": stashes,
            "status": status_lines,
            "detached_commits": detached,
            "active_writers": [dict(item) for item in (active_writers or ())],
        }
        inventory_root = _digest(payload)
        inventory_id = new_id("repository-inventory")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO repository_inventories_v2(
                       id,mission_id,repository_root,repository_head,inventory_root,
                       branches_json,worktrees_json,stashes_json,status_json,
                       detached_commits_json,active_writers_json,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    inventory_id,
                    mission_id,
                    str(root),
                    head,
                    inventory_root,
                    _canonical(branches),
                    _canonical(worktrees),
                    _canonical(stashes),
                    _canonical(status_lines),
                    _canonical(detached),
                    _canonical(payload["active_writers"]),
                    utc_now(),
                ),
            )
        return self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?", (inventory_id,)
        )

    def preserve_repository(
        self,
        inventory_id: str,
        *,
        output_directory: str | Path,
    ) -> dict[str, Any]:
        inventory = self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?", (inventory_id,)
        )
        root = Path(inventory["repository_root"]).resolve()
        output = Path(output_directory).resolve()
        output.mkdir(parents=True, exist_ok=True)
        bundle_id = new_id("preservation-bundle")
        temporary = Path(tempfile.mkdtemp(prefix=f".{bundle_id}.", dir=output))
        archive_path = output / f"{bundle_id}.tar.gz"
        try:
            git_bundle = temporary / "repository.bundle"
            _run_git(root, "bundle", "create", str(git_bundle), "--all")
            (temporary / "working-tree.patch").write_text(
                _run_git(root, "diff", "--binary", "HEAD", check=False).stdout,
                encoding="utf-8",
            )
            untracked = _run_git(
                root, "ls-files", "--others", "--exclude-standard", "-z", check=False
            ).stdout.split("\0")
            untracked = [value for value in untracked if value]
            untracked_archive = temporary / "untracked.tar"
            with tarfile.open(untracked_archive, "w") as tar:
                for relative in untracked:
                    path = (root / relative).resolve()
                    try:
                        path.relative_to(root)
                    except ValueError:
                        continue
                    if path.exists() and not path.is_symlink():
                        tar.add(path, arcname=relative, recursive=True)
            manifest = {
                "inventory_id": inventory_id,
                "inventory_root": inventory["inventory_root"],
                "repository_head": inventory["repository_head"],
                "git_bundle_sha256": _file_digest(git_bundle),
                "working_tree_patch_sha256": _file_digest(temporary / "working-tree.patch"),
                "untracked_archive_sha256": _file_digest(untracked_archive),
                "untracked_paths": sorted(untracked),
            }
            (temporary / "manifest.json").write_text(
                _canonical(manifest) + "\n", encoding="utf-8"
            )
            with tarfile.open(archive_path, "w:gz") as tar:
                for path in sorted(temporary.iterdir()):
                    tar.add(path, arcname=path.name)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
        bundle_root = _file_digest(archive_path)
        with tarfile.open(archive_path, "r:gz") as tar:
            names = set(tar.getnames())
        verified = {"repository.bundle", "working-tree.patch", "untracked.tar", "manifest.json"} <= names
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO preservation_bundles_v2(
                       id,inventory_id,bundle_path,bundle_root,manifest_json,verified,
                       created_at,verified_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    bundle_id,
                    inventory_id,
                    str(archive_path),
                    bundle_root,
                    _canonical(manifest),
                    1 if verified else 0,
                    utc_now(),
                    utc_now() if verified else None,
                ),
            )
        return self.store.one("SELECT * FROM preservation_bundles_v2 WHERE id=?", (bundle_id,))

    def plan_cleanup_item(
        self,
        inventory_id: str,
        *,
        item_type: Literal[
            "branch", "worktree", "stash", "dirty_file", "untracked_file", "detached_commit", "task_owner"
        ],
        item_key: str,
        classification: Literal[
            "active", "accepted", "unfinished", "redundant", "historical", "unknown", "protected"
        ] = "unknown",
        disposition: Literal["retain", "preserve", "integrate", "retire", "restart", "defer"] | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if disposition is None:
            disposition = "retain" if classification in {"active", "unknown", "protected"} else "preserve"
        if disposition == "retire" and classification not in {"redundant", "historical"}:
            raise InvalidTransition("only proven redundant or historical items may retire")
        item_id = new_id("cleanup-item")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO cleanup_items_v2(
                       id,inventory_id,item_type,item_key,classification,disposition,
                       evidence_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,'planned',?,?)""",
                (
                    item_id,
                    inventory_id,
                    item_type,
                    item_key,
                    classification,
                    disposition,
                    _canonical(dict(evidence or {})),
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM cleanup_items_v2 WHERE id=?", (item_id,))

    def execute_retirement(
        self,
        cleanup_item_id: str,
        *,
        preservation_bundle_id: str,
    ) -> dict[str, Any]:
        item = self.store.one("SELECT * FROM cleanup_items_v2 WHERE id=?", (cleanup_item_id,))
        if item["disposition"] != "retire" or item["classification"] not in {"redundant", "historical"}:
            raise InvalidTransition("cleanup item is not proven safe to retire")
        bundle = self.store.one(
            "SELECT * FROM preservation_bundles_v2 WHERE id=?", (preservation_bundle_id,)
        )
        if not bundle["verified"] or bundle["inventory_id"] != item["inventory_id"]:
            raise InvalidTransition("cleanup retirement lacks a verified matching preservation bundle")
        inventory = self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?", (item["inventory_id"],)
        )
        active_writers = _loads(inventory["active_writers_json"], [])
        if any(
            item["item_key"] in {writer.get("branch"), writer.get("worktree"), writer.get("task_owner")}
            for writer in active_writers
        ):
            raise InvalidTransition("cleanup item still has an active writer")
        root = Path(inventory["repository_root"])
        effect_id = new_id("cleanup-effect")
        precondition = {
            "inventory_root": inventory["inventory_root"],
            "bundle_root": bundle["bundle_root"],
            "classification": item["classification"],
        }
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO cleanup_effects_v2(
                       id,cleanup_item_id,effect_type,precondition_json,status,updated_at
                   ) VALUES(?,?,?,?,'running',?)""",
                (effect_id, cleanup_item_id, f"retire_{item['item_type']}", _canonical(precondition), utc_now()),
            )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='running',updated_at=? WHERE id=?",
                (utc_now(), cleanup_item_id),
            )
        try:
            if item["item_type"] == "branch":
                _run_git(root, "branch", "-D", item["item_key"])
            elif item["item_type"] == "worktree":
                _run_git(root, "worktree", "remove", "--force", item["item_key"])
            elif item["item_type"] == "stash":
                _run_git(root, "stash", "drop", item["item_key"])
            else:
                raise InvalidTransition("item type has no destructive retirement owner")
            result = {"retired": item["item_key"], "item_type": item["item_type"]}
        except BaseException as exc:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE cleanup_effects_v2
                       SET status='failed',result_json=?,completed_at=?,updated_at=? WHERE id=?""",
                    (_canonical({"error": str(exc)}), utc_now(), utc_now(), effect_id),
                )
                db.execute(
                    "UPDATE cleanup_items_v2 SET status='failed',updated_at=? WHERE id=?",
                    (utc_now(), cleanup_item_id),
                )
            raise
        with self.store.transaction() as db:
            db.execute(
                """UPDATE cleanup_effects_v2
                   SET status='succeeded',result_json=?,completed_at=?,updated_at=? WHERE id=?""",
                (_canonical(result), utc_now(), utc_now(), effect_id),
            )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='completed',updated_at=? WHERE id=?",
                (utc_now(), cleanup_item_id),
            )
        return self.store.one("SELECT * FROM cleanup_effects_v2 WHERE id=?", (effect_id,))
