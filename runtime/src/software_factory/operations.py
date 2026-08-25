from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import atomic_write, new_id, utc_now


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


@contextmanager
def _path_lock(root: Path, name: str) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f".software-factory-{name}.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def _repository_lock(root: Path, name: str) -> Iterator[None]:
    common_dir = _run_git(root, "rev-parse", "--git-common-dir").stdout.strip()
    common_path = (
        (root / common_dir).resolve() if not Path(common_dir).is_absolute() else Path(common_dir)
    )
    with _path_lock(common_path, name):
        yield


def _fsync_tree(root: Path) -> None:
    """Make staged file bytes and directory entries durable before publication."""

    directories = [root]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise InvalidTransition(f"staged release contains a symlink: {path}")
        if path.is_dir():
            directories.append(path)
            continue
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    for directory in sorted(directories, key=lambda value: len(value.parts), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class OperationsService:
    """Physical owners for immutable release, systemic recovery, and cleanup."""

    def __init__(
        self,
        store: Store,
        *,
        fault_injector: Callable[[str], None] | None = None,
    ):
        self.store = store
        self._fault_injector = fault_injector

    def _fault(self, point: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    @staticmethod
    def _release_belongs_to_root(release: Mapping[str, Any], release_root: Path) -> bool:
        return Path(str(release["release_path"])).resolve().parent == release_root

    def _require_release_root(self, release: Mapping[str, Any], release_root: str | Path) -> Path:
        root = Path(release_root).resolve()
        if not self._release_belongs_to_root(release, root):
            raise InvalidTransition("release belongs to a different target root")
        return root

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

    def _installed_equivalence(self, release: Mapping[str, Any]) -> str:
        """Return the installed content root or reject any byte/path drift."""

        release_path = Path(str(release["release_path"])).resolve()
        if not release_path.is_dir() or release_path.is_symlink():
            raise InvalidTransition("installed release path is missing or unsafe")
        manifest = _loads(release["manifest_json"], {})
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
            raise InvalidTransition("stored release manifest is invalid")
        if (
            manifest.get("release_id") != release["id"]
            or manifest.get("source_revision") != release["source_revision"]
            or manifest.get("source_tree_root") != release["source_tree_root"]
            or manifest.get("manifest_root") != release["manifest_root"]
        ):
            raise InvalidTransition("stored release manifest identity is stale")
        manifest_path = release_path / "release-manifest.json"
        expected_manifest = (_canonical(manifest) + "\n").encode("utf-8")
        if (
            not manifest_path.is_file()
            or manifest_path.is_symlink()
            or manifest_path.read_bytes() != expected_manifest
        ):
            raise InvalidTransition("installed release manifest bytes differ")

        expected: dict[str, Mapping[str, Any]] = {}
        for raw_entry in manifest["files"]:
            if not isinstance(raw_entry, dict) or not isinstance(raw_entry.get("path"), str):
                raise InvalidTransition("stored release manifest entry is invalid")
            relative = str(raw_entry["path"])
            candidate = (release_path / relative).resolve()
            try:
                candidate.relative_to(release_path)
            except ValueError as exc:
                raise InvalidTransition("release manifest path escapes install root") from exc
            if relative in expected or relative in {"", "release-manifest.json"}:
                raise InvalidTransition("release manifest contains a duplicate or reserved path")
            expected[relative] = raw_entry

        observed: list[dict[str, Any]] = []
        observed_paths: set[str] = set()
        for path in sorted(release_path.rglob("*")):
            relative = path.relative_to(release_path).as_posix()
            if path.is_symlink():
                raise InvalidTransition(f"installed release contains a symlink: {relative}")
            if not path.is_file() or relative == "release-manifest.json":
                continue
            entry = expected.get(relative)
            if entry is None:
                raise InvalidTransition(
                    f"installed release contains an undeclared file: {relative}"
                )
            mode = stat.S_IMODE(path.stat().st_mode)
            actual = {
                "path": relative,
                "sha256": _file_digest(path),
                "bytes": path.stat().st_size,
                "executable": bool(mode & stat.S_IXUSR),
            }
            if actual != dict(entry):
                raise InvalidTransition(f"installed release file differs: {relative}")
            observed.append(actual)
            observed_paths.add(relative)
        missing = sorted(set(expected) - observed_paths)
        if missing:
            raise InvalidTransition(f"installed release is missing files: {missing}")
        installed_root = _digest(observed)
        if installed_root != release["manifest_root"]:
            raise InvalidTransition("installed release content root differs")
        return installed_root

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
        releases.mkdir(parents=True, exist_ok=True)
        stage_root = _digest(
            {
                "source_revision": source_revision,
                "source_tree_root": source_tree_root,
                "manifest_root": manifest_root,
                "release_root": str(releases),
            }
        )
        receipt_path = releases / f".stage-{stage_root}.json"
        existing_rows = self.store.all(
            """SELECT * FROM immutable_releases_v2
               WHERE source_revision=? AND manifest_root=?""",
            (source_revision, manifest_root),
        )
        for existing in existing_rows:
            if self._release_belongs_to_root(existing, releases):
                self._installed_equivalence(existing)
                receipt_path.unlink(missing_ok=True)
                return existing
        if receipt_path.exists():
            if not receipt_path.is_file() or receipt_path.is_symlink():
                raise InvalidTransition("release staging receipt is unsafe")
            receipt = _loads(receipt_path.read_text(encoding="utf-8"), {})
            if not isinstance(receipt, dict) or receipt.get("stage_root") != stage_root:
                raise InvalidTransition("release staging receipt differs")
            release_id = str(receipt.get("release_id", ""))
            if not release_id:
                raise InvalidTransition("release staging receipt lacks a release id")
        else:
            release_id = new_id("release")
            receipt = {"stage_root": stage_root, "release_id": release_id}
            atomic_write(receipt_path, (_canonical(receipt) + "\n").encode("utf-8"))
        destination = releases / release_id
        manifest_payload = {
            "release_id": release_id,
            "source_revision": source_revision,
            "source_tree_root": source_tree_root,
            "manifest_root": manifest_root,
            "files": manifest,
        }
        if destination.exists():
            self._installed_equivalence(
                {
                    "id": release_id,
                    "source_revision": source_revision,
                    "source_tree_root": source_tree_root,
                    "manifest_root": manifest_root,
                    "manifest_json": _canonical(manifest_payload),
                    "release_path": str(destination),
                }
            )
        else:
            temporary = Path(tempfile.mkdtemp(prefix=f".{release_id}.", dir=releases))
            try:
                for entry in manifest:
                    source_path = source / entry["path"]
                    target = temporary / entry["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target, follow_symlinks=False)
                    target.chmod(0o555 if entry["executable"] else 0o444)
                manifest_path = temporary / "release-manifest.json"
                manifest_path.write_text(_canonical(manifest_payload) + "\n", encoding="utf-8")
                manifest_path.chmod(0o444)
                _fsync_tree(temporary)
                os.replace(temporary, destination)
                directory = os.open(releases, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except Exception:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        self._installed_equivalence(
            {
                "id": release_id,
                "source_revision": source_revision,
                "source_tree_root": source_tree_root,
                "manifest_root": manifest_root,
                "manifest_json": _canonical(manifest_payload),
                "release_path": str(destination),
            }
        )
        self._fault("stage:after_physical_effect")
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
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        receipt_path.unlink(missing_ok=True)
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
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
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
        status = (
            "accepted"
            if disposition == "accepted"
            else ("rejected" if disposition == "rejected" else "staged")
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
            directory = os.open(release_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    @staticmethod
    def _read_active_pointer(release_root: Path) -> dict[str, Any] | None:
        pointer = release_root / "active-release.json"
        if not pointer.exists():
            return None
        if not pointer.is_file() or pointer.is_symlink():
            raise InvalidTransition("active release pointer is unsafe")
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidTransition("active release pointer is invalid") from exc
        if not isinstance(payload, dict):
            raise InvalidTransition("active release pointer is invalid")
        return payload

    def _require_active_pointer(
        self, release: Mapping[str, Any], release_root: Path
    ) -> dict[str, Any]:
        payload = self._read_active_pointer(release_root)
        if (
            payload is None
            or payload.get("release_id") != release["id"]
            or payload.get("release_path") != release["release_path"]
            or payload.get("manifest_root") != release["manifest_root"]
            or payload.get("source_revision") != release["source_revision"]
            or not isinstance(payload.get("transition_root"), str)
        ):
            raise InvalidTransition("active release pointer differs from database state")
        transition = self.store.one(
            """SELECT * FROM release_transitions_v2
               WHERE transition_root=? AND status='committed'""",
            (payload["transition_root"],),
            required=False,
        )
        if transition is None or _loads(transition["pointer_payload_json"], {}) != payload:
            raise InvalidTransition("active release pointer lacks a committed transition")
        return payload

    def _prepare_release_transition(
        self,
        *,
        transition_type: Literal["activate", "rollback"],
        release: Mapping[str, Any],
        target_release: Mapping[str, Any] | None,
        previous_release: Mapping[str, Any] | None,
        release_root: Path,
        pointer_payload: Mapping[str, Any],
        evidence_ids: Sequence[str] = (),
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        transition_core = {
            "transition_type": transition_type,
            "release_id": release["id"],
            "target_release_id": target_release["id"] if target_release else None,
            "previous_release_id": previous_release["id"] if previous_release else None,
            "release_root": str(release_root),
            "pointer_payload": dict(pointer_payload),
            "evidence_ids": _ids(evidence_ids),
        }
        transition_root = _digest(transition_core)
        payload = {**dict(pointer_payload), "transition_root": transition_root}
        existing = self.store.one(
            "SELECT * FROM release_transitions_v2 WHERE transition_root=?",
            (transition_root,),
            required=False,
        )
        if existing is None:
            transition_id = new_id("release-transition")
            now = utc_now()
            with self.store.transaction() as db:
                db.execute(
                    """INSERT INTO release_transitions_v2(
                           id,transition_root,transition_type,release_id,target_release_id,
                           previous_release_id,release_root,pointer_payload_json,status,
                           created_at,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?,'prepared',?,?)""",
                    (
                        transition_id,
                        transition_root,
                        transition_type,
                        release["id"],
                        target_release["id"] if target_release else None,
                        previous_release["id"] if previous_release else None,
                        str(release_root),
                        _canonical(payload),
                        now,
                        now,
                    ),
                )
            existing = self.store.one(
                "SELECT * FROM release_transitions_v2 WHERE id=?", (transition_id,)
            )
        elif _loads(existing["pointer_payload_json"], {}) != payload:
            raise InvalidTransition("release transition payload differs from prepared state")
        return existing, payload

    def _ensure_transition_pointer(
        self,
        transition: Mapping[str, Any],
        *,
        release_root: Path,
        payload: Mapping[str, Any],
    ) -> None:
        current = self._read_active_pointer(release_root)
        if current != dict(payload):
            self._write_active_pointer(release_root, payload)
        self._fault(f"{transition['transition_type']}:after_pointer_write")
        if transition["status"] == "prepared":
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE release_transitions_v2
                       SET status='pointer_written',updated_at=?
                       WHERE id=? AND status='prepared'""",
                    (utc_now(), transition["id"]),
                )
        self._fault(f"{transition['transition_type']}:after_pointer_record")

    def _unfinished_transition(
        self,
        *,
        release_id: str,
        transition_type: Literal["activate", "rollback"],
        release_root: Path,
    ) -> dict[str, Any] | None:
        rows = self.store.all(
            """SELECT * FROM release_transitions_v2
               WHERE release_id=? AND transition_type=? AND release_root=?
                 AND status IN ('prepared','pointer_written')
               ORDER BY created_at,id""",
            (release_id, transition_type, str(release_root)),
        )
        if len(rows) > 1:
            raise InvalidTransition("release has multiple unfinished transitions")
        return rows[0] if rows else None

    def _require_no_other_root_transition(
        self, release_root: Path, *, excluding_id: str | None = None
    ) -> None:
        rows = self.store.all(
            """SELECT * FROM release_transitions_v2
               WHERE release_root=? AND status IN ('prepared','pointer_written')
               ORDER BY created_at,id""",
            (str(release_root),),
        )
        if any(row["id"] != excluding_id for row in rows):
            raise InvalidTransition("release root has an unfinished transition")

    def _active_release_for_root(self, release_root: Path) -> dict[str, Any] | None:
        candidates = [
            candidate
            for candidate in self.store.all(
                """SELECT * FROM immutable_releases_v2 WHERE status='active'
                   ORDER BY activated_at DESC,id"""
            )
            if self._release_belongs_to_root(candidate, release_root)
        ]
        if len(candidates) > 1:
            raise InvalidTransition("release root has multiple active releases")
        return candidates[0] if candidates else None

    def _require_current_pointer(
        self, release_root: Path, release: Mapping[str, Any] | None
    ) -> dict[str, Any] | None:
        if release is not None:
            return self._require_active_pointer(release, release_root)
        payload = self._read_active_pointer(release_root)
        if payload is None:
            return None
        if payload.get("release_id") is not None or not isinstance(
            payload.get("transition_root"), str
        ):
            raise InvalidTransition("release pointer differs from the current database state")
        transition = self.store.one(
            """SELECT * FROM release_transitions_v2
               WHERE transition_root=? AND status='committed'""",
            (payload["transition_root"],),
            required=False,
        )
        if transition is None or _loads(transition["pointer_payload_json"], {}) != payload:
            raise InvalidTransition("inactive release pointer lacks a committed transition")
        return payload

    def activate_release(
        self,
        release_id: str,
        *,
        release_root: str | Path,
    ) -> dict[str, Any]:
        initial = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        root = self._require_release_root(initial, release_root)
        with _path_lock(root, "release-transition"):
            return self._activate_release_locked(release_id, release_root=root)

    def _activate_release_locked(
        self,
        release_id: str,
        *,
        release_root: str | Path,
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        root = self._require_release_root(release, release_root)
        if release["status"] == "active":
            self._installed_equivalence(release)
            self._require_active_pointer(release, root)
            return release
        if release["review_status"] != "accepted" or release["status"] != "accepted":
            raise InvalidTransition("release must pass independent review before activation")
        self._installed_equivalence(release)
        transition = self._unfinished_transition(
            release_id=release_id,
            transition_type="activate",
            release_root=root,
        )
        self._require_no_other_root_transition(
            root, excluding_id=str(transition["id"]) if transition else None
        )
        active = self._active_release_for_root(root)
        if transition is not None:
            previous_id = transition["previous_release_id"]
            if (active["id"] if active else None) != previous_id:
                raise InvalidTransition("activation transition currentness changed")
            previous = (
                self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (previous_id,))
                if previous_id
                else None
            )
            if previous is not None and not self._release_belongs_to_root(previous, root):
                raise InvalidTransition("activation predecessor belongs to another root")
            pointer_payload = {
                "release_id": release_id,
                "release_path": release["release_path"],
                "manifest_root": release["manifest_root"],
                "source_revision": release["source_revision"],
                "previous_release_id": previous_id,
            }
            transition_core = {
                "transition_type": "activate",
                "release_id": release_id,
                "target_release_id": release_id,
                "previous_release_id": previous_id,
                "release_root": str(root),
                "pointer_payload": pointer_payload,
                "evidence_ids": [],
            }
            if _digest(transition_core) != transition["transition_root"]:
                raise InvalidTransition("activation transition root differs")
            payload = _loads(transition["pointer_payload_json"], {})
            expected_identity = {
                **pointer_payload,
                "transition_root": transition["transition_root"],
            }
            if payload != expected_identity:
                raise InvalidTransition("activation transition payload differs")
            current_pointer = self._read_active_pointer(root)
            if current_pointer != payload:
                if transition["status"] != "prepared":
                    raise InvalidTransition("activation transition pointer changed")
                self._require_current_pointer(root, previous)
        else:
            previous = active
            self._require_current_pointer(root, previous)
            pointer_payload = {
                "release_id": release_id,
                "release_path": release["release_path"],
                "manifest_root": release["manifest_root"],
                "source_revision": release["source_revision"],
                "previous_release_id": previous["id"] if previous else None,
            }
            transition, payload = self._prepare_release_transition(
                transition_type="activate",
                release=release,
                target_release=release,
                previous_release=previous,
                release_root=root,
                pointer_payload=pointer_payload,
            )
        if transition["status"] == "committed":
            return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        self._ensure_transition_pointer(transition, release_root=root, payload=payload)
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
            db.execute(
                """UPDATE release_transitions_v2
                   SET status='committed',completed_at=?,updated_at=? WHERE id=?""",
                (now, now, transition["id"]),
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
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        root = self._require_release_root(release, release_root)
        if release["status"] != "active":
            raise InvalidTransition("only the active release may be installed-verified")
        self._require_active_pointer(release, root)
        installed_root: str | None = None
        install_error: str | None = None
        try:
            installed_root = self._installed_equivalence(release)
        except InvalidTransition as exc:
            install_error = str(exc)
        if install_error is None:
            process = subprocess.run(
                [str(part) for part in command],
                cwd=release["release_path"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            try:
                post_probe_root = self._installed_equivalence(release)
            except InvalidTransition as exc:
                post_probe_root = None
                install_error = str(exc)
            disposition = (
                "passed"
                if process.returncode == 0
                and install_error is None
                and installed_root == post_probe_root
                else "failed"
            )
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        else:
            post_probe_root = None
            disposition = "failed"
            exit_code = -1
            stdout = ""
            stderr = install_error
        evidence_root = _digest(
            {
                "release_id": release_id,
                "manifest_root": release["manifest_root"],
                "installed_root": installed_root,
                "post_probe_root": post_probe_root,
                "install_error": install_error,
                "command": list(command),
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
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
                    exit_code,
                    stdout,
                    stderr,
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
                release_root=root,
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
        initial = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        root = self._require_release_root(initial, release_root)
        with _path_lock(root, "release-transition"):
            return self._rollback_release_locked(
                release_id, release_root=root, evidence_ids=evidence_ids
            )

    def _rollback_release_locked(
        self,
        release_id: str,
        *,
        release_root: str | Path,
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        root = self._require_release_root(release, release_root)
        if not evidence_ids:
            raise ValueError("release rollback requires evidence")
        if release["status"] == "rolled_back":
            return release
        if release["status"] != "active":
            raise InvalidTransition("only an active release may be rolled back")
        previous = None
        if release["previous_release_id"]:
            previous = self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?",
                (release["previous_release_id"],),
            )
            if not self._release_belongs_to_root(previous, root):
                raise InvalidTransition("previous release belongs to a different target root")
            if previous["verification_status"] != "passed":
                raise InvalidTransition("rollback target lacks installed verification")
            self._installed_equivalence(previous)
        pointer_payload = (
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
        transition = self._unfinished_transition(
            release_id=release_id,
            transition_type="rollback",
            release_root=root,
        )
        self._require_no_other_root_transition(
            root, excluding_id=str(transition["id"]) if transition else None
        )
        active = self._active_release_for_root(root)
        if active is None or active["id"] != release_id:
            raise InvalidTransition("rollback transition currentness changed")
        if transition is not None:
            transition_core = {
                "transition_type": "rollback",
                "release_id": release_id,
                "target_release_id": previous["id"] if previous else None,
                "previous_release_id": previous["id"] if previous else None,
                "release_root": str(root),
                "pointer_payload": pointer_payload,
                "evidence_ids": _ids(evidence_ids),
            }
            if _digest(transition_core) != transition["transition_root"]:
                raise InvalidTransition("rollback transition retry evidence differs")
            payload = {**pointer_payload, "transition_root": transition["transition_root"]}
            if _loads(transition["pointer_payload_json"], {}) != payload:
                raise InvalidTransition("rollback transition payload differs")
            current_pointer = self._read_active_pointer(root)
            if current_pointer != payload:
                if transition["status"] != "prepared":
                    raise InvalidTransition("rollback transition pointer changed")
                self._require_current_pointer(root, release)
        else:
            self._require_current_pointer(root, release)
            transition, payload = self._prepare_release_transition(
                transition_type="rollback",
                release=release,
                target_release=previous,
                previous_release=previous,
                release_root=root,
                pointer_payload=pointer_payload,
                evidence_ids=evidence_ids,
            )
        if transition["status"] == "committed":
            return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        self._ensure_transition_pointer(transition, release_root=root, payload=payload)
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
            db.execute(
                """UPDATE release_transitions_v2
                   SET status='committed',completed_at=?,updated_at=? WHERE id=?""",
                (now, now, transition["id"]),
            )
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))

    def plan_agent_refresh(
        self,
        release_id: str,
        agents: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
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
        if (
            self.store.one(
                "SELECT id FROM missions WHERE id=?", (target_mission_id,), required=False
            )
            is None
        ):
            raise StoreError(f"mission not found: {target_mission_id}")
        defect_fingerprint = _digest(
            {"defect_class": defect_class, "defect_evidence": dict(defect_evidence)}
        )
        existing = self.store.one(
            """SELECT * FROM factory_recovery_cases_v2
               WHERE target_mission_id=? AND defect_fingerprint=?
               ORDER BY opened_at DESC LIMIT 1""",
            (target_mission_id, defect_fingerprint),
            required=False,
        )
        if existing is not None:
            if (
                _loads(existing["target_state_json"], {}) != dict(target_state)
                or existing["requested_range_root"] != requested_range_root
                or existing["tracker_currentness_root"] != tracker_currentness_root
                or _loads(existing["safe_frontier_json"], [])
                != [dict(item) for item in safe_frontier]
            ):
                raise InvalidTransition("recovery fingerprint collides with different target state")
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
        return self.store.one("SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,))

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
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        if release["source_revision"] != repair_revision:
            raise InvalidTransition("recovery repair revision differs from release revision")
        if release["verification_status"] != "passed":
            raise InvalidTransition("recovery release is not installed-verified")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE factory_recovery_cases_v2
                   SET repair_revision=?,repair_evidence_ids_json=?,release_id=?,
                       status='restoring',updated_at=? WHERE id=?""",
                (
                    repair_revision,
                    _canonical(_ids(evidence_ids)),
                    release_id,
                    utc_now(),
                    recovery_id,
                ),
            )
        return self.store.one("SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,))

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
        token = self.store.one("SELECT * FROM recovery_resume_tokens_v2 WHERE id=?", (token_id,))
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
        return self.store.one("SELECT * FROM factory_recovery_cases_v2 WHERE id=?", (recovery_id,))

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
            line
            for line in _run_git(
                root,
                "for-each-ref",
                "--format=%(refname:short)|%(objectname)|%(upstream:short)",
                "refs/heads",
                check=False,
            ).stdout.splitlines()
            if line
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
            line
            for line in _run_git(
                root, "stash", "list", "--format=%gd|%H|%gs", check=False
            ).stdout.splitlines()
            if line
        ]
        status_lines = _run_git(
            root, "status", "--porcelain=v2", "--untracked-files=all", check=False
        ).stdout.splitlines()
        detached = [
            line
            for line in _run_git(
                root, "fsck", "--unreachable", "--no-reflogs", check=False
            ).stdout.splitlines()
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
        return self.store.one("SELECT * FROM repository_inventories_v2 WHERE id=?", (inventory_id,))

    @staticmethod
    def _verify_bundle_archive(archive_path: Path, manifest: Mapping[str, Any]) -> None:
        expected_names = {
            "repository.bundle",
            "working-tree.patch",
            "untracked.tar",
            "manifest.json",
        }
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                members = archive.getmembers()
                if {member.name for member in members} != expected_names:
                    raise InvalidTransition("preservation bundle member set differs")
                if any(
                    not member.isfile()
                    or member.issym()
                    or member.islnk()
                    or Path(member.name).is_absolute()
                    or ".." in Path(member.name).parts
                    for member in members
                ):
                    raise InvalidTransition("preservation bundle contains unsafe members")
                content: dict[str, bytes] = {}
                for member in members:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise InvalidTransition("preservation bundle member is unreadable")
                    content[member.name] = extracted.read()
        except (OSError, tarfile.TarError) as exc:
            raise InvalidTransition("preservation bundle is unreadable") from exc
        if content["manifest.json"] != (_canonical(dict(manifest)) + "\n").encode("utf-8"):
            raise InvalidTransition("preservation bundle manifest bytes differ")
        for name, key in (
            ("repository.bundle", "git_bundle_sha256"),
            ("working-tree.patch", "working_tree_patch_sha256"),
            ("untracked.tar", "untracked_archive_sha256"),
        ):
            actual = hashlib.sha256(content[name]).hexdigest()
            if actual != manifest.get(key):
                raise InvalidTransition(f"preservation bundle member differs: {name}")
        expected_untracked = manifest.get("untracked_paths", [])
        if not isinstance(expected_untracked, list) or any(
            not isinstance(value, str) for value in expected_untracked
        ):
            raise InvalidTransition("preservation untracked path manifest is invalid")
        try:
            with tarfile.open(fileobj=io.BytesIO(content["untracked.tar"]), mode="r:") as archive:
                members = archive.getmembers()
        except (OSError, tarfile.TarError) as exc:
            raise InvalidTransition("preservation untracked archive is unreadable") from exc
        names = [member.name for member in members]
        if sorted(names) != sorted(expected_untracked) or len(set(names)) != len(names):
            raise InvalidTransition("preservation untracked member set differs")
        if any(
            not member.isfile()
            or member.issym()
            or member.islnk()
            or Path(member.name).is_absolute()
            or ".." in Path(member.name).parts
            for member in members
        ):
            raise InvalidTransition("preservation untracked archive contains unsafe members")

    def _require_verified_bundle(self, bundle: Mapping[str, Any]) -> None:
        if not bundle["verified"]:
            raise InvalidTransition("preservation bundle was not verified")
        archive_path = Path(str(bundle["bundle_path"])).resolve()
        if not archive_path.is_file() or archive_path.is_symlink():
            raise InvalidTransition("preservation bundle path is missing or unsafe")
        if _file_digest(archive_path) != bundle["bundle_root"]:
            raise InvalidTransition("preservation bundle root differs")
        manifest = _loads(bundle["manifest_json"], {})
        if not isinstance(manifest, dict):
            raise InvalidTransition("preservation bundle stored manifest is invalid")
        self._verify_bundle_archive(archive_path, manifest)

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
                    path = root / relative
                    try:
                        path.resolve().relative_to(root)
                    except ValueError as exc:
                        raise InvalidTransition("untracked path escapes repository") from exc
                    if not path.is_file() or path.is_symlink():
                        raise InvalidTransition("untracked path cannot be preserved safely")
                    tar.add(path, arcname=relative, recursive=False)
            manifest = {
                "inventory_id": inventory_id,
                "inventory_root": inventory["inventory_root"],
                "repository_head": inventory["repository_head"],
                "git_bundle_sha256": _file_digest(git_bundle),
                "working_tree_patch_sha256": _file_digest(temporary / "working-tree.patch"),
                "untracked_archive_sha256": _file_digest(untracked_archive),
                "untracked_paths": sorted(untracked),
            }
            (temporary / "manifest.json").write_text(_canonical(manifest) + "\n", encoding="utf-8")
            with tarfile.open(archive_path, "w:gz") as tar:
                for path in sorted(temporary.iterdir()):
                    tar.add(path, arcname=path.name)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
        bundle_root = _file_digest(archive_path)
        verified = True
        try:
            self._verify_bundle_archive(archive_path, manifest)
        except InvalidTransition:
            verified = False
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
            "branch",
            "worktree",
            "stash",
            "dirty_file",
            "untracked_file",
            "detached_commit",
            "task_owner",
        ],
        item_key: str,
        classification: Literal[
            "active", "accepted", "unfinished", "redundant", "historical", "unknown", "protected"
        ] = "unknown",
        disposition: Literal["retain", "preserve", "integrate", "retire", "restart", "defer"]
        | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if disposition is None:
            disposition = (
                "retain" if classification in {"active", "unknown", "protected"} else "preserve"
            )
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

    @staticmethod
    def _recorded_cleanup_identity(
        item: Mapping[str, Any], inventory: Mapping[str, Any]
    ) -> dict[str, Any]:
        if item["item_type"] == "branch":
            branch_matches = [
                value.split("|", 2)
                for value in _loads(inventory["branches_json"], [])
                if isinstance(value, str) and value.split("|", 1)[0] == item["item_key"]
            ]
            if len(branch_matches) != 1 or len(branch_matches[0]) < 2:
                raise InvalidTransition("cleanup branch was not exact in the inventory")
            return {"branch": item["item_key"], "object_id": branch_matches[0][1]}
        if item["item_type"] == "worktree":
            target = str(Path(str(item["item_key"])).resolve())
            worktree_matches = [
                value
                for value in _loads(inventory["worktrees_json"], [])
                if isinstance(value, dict)
                and str(Path(str(value.get("worktree", ""))).resolve()) == target
            ]
            if len(worktree_matches) != 1:
                raise InvalidTransition("cleanup worktree was not exact in the inventory")
            return {
                "worktree": target,
                "head": worktree_matches[0].get("HEAD"),
                "branch": worktree_matches[0].get("branch"),
            }
        if item["item_type"] == "stash":
            stash_matches = [
                value.split("|", 2)
                for value in _loads(inventory["stashes_json"], [])
                if isinstance(value, str) and value.split("|", 1)[0] == item["item_key"]
            ]
            if len(stash_matches) != 1 or len(stash_matches[0]) < 2:
                raise InvalidTransition("cleanup stash was not exact in the inventory")
            return {"stash": item["item_key"], "object_id": stash_matches[0][1]}
        raise InvalidTransition("item type has no destructive retirement owner")

    @staticmethod
    def _require_cleanup_identity(
        root: Path, item: Mapping[str, Any], expected: Mapping[str, Any]
    ) -> None:
        if item["item_type"] == "branch":
            actual = _run_git(
                root,
                "rev-parse",
                "--verify",
                f"refs/heads/{item['item_key']}",
                check=False,
            ).stdout.strip()
            if actual != expected["object_id"]:
                raise InvalidTransition("cleanup branch advanced after preservation")
            worktrees = _run_git(root, "worktree", "list", "--porcelain", check=False).stdout
            if f"branch refs/heads/{item['item_key']}\n" in f"{worktrees}\n":
                raise InvalidTransition("cleanup branch is checked out in a worktree")
            return
        if item["item_type"] == "worktree":
            target = Path(str(expected["worktree"]))
            listed = _run_git(root, "worktree", "list", "--porcelain", check=False).stdout
            entries: list[dict[str, str]] = []
            current: dict[str, str] = {}
            for line in listed.splitlines() + [""]:
                if not line:
                    if current:
                        entries.append(current)
                        current = {}
                    continue
                key, _, value = line.partition(" ")
                current[key] = value
            match = next(
                (
                    value
                    for value in entries
                    if str(Path(value.get("worktree", "")).resolve()) == str(target)
                ),
                None,
            )
            if (
                match is None
                or match.get("HEAD") != expected["head"]
                or match.get("branch") != expected["branch"]
            ):
                raise InvalidTransition("cleanup worktree identity changed after preservation")
            if _run_git(
                target, "status", "--porcelain=v2", "--untracked-files=all", check=False
            ).stdout.strip():
                raise InvalidTransition("cleanup worktree changed after preservation")
            return
        if item["item_type"] == "stash":
            actual = _run_git(
                root, "rev-parse", "--verify", str(item["item_key"]), check=False
            ).stdout.strip()
            if actual != expected["object_id"]:
                raise InvalidTransition("cleanup stash changed after preservation")
            return
        raise InvalidTransition("item type has no destructive retirement owner")

    def execute_retirement(
        self,
        cleanup_item_id: str,
        *,
        preservation_bundle_id: str,
    ) -> dict[str, Any]:
        item = self.store.one("SELECT * FROM cleanup_items_v2 WHERE id=?", (cleanup_item_id,))
        if item["disposition"] != "retire" or item["classification"] not in {
            "redundant",
            "historical",
        }:
            raise InvalidTransition("cleanup item is not proven safe to retire")
        bundle = self.store.one(
            "SELECT * FROM preservation_bundles_v2 WHERE id=?", (preservation_bundle_id,)
        )
        if not bundle["verified"] or bundle["inventory_id"] != item["inventory_id"]:
            raise InvalidTransition(
                "cleanup retirement lacks a verified matching preservation bundle"
            )
        self._require_verified_bundle(bundle)
        inventory = self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?", (item["inventory_id"],)
        )
        active_writers = _loads(inventory["active_writers_json"], [])
        if any(
            item["item_key"]
            in {writer.get("branch"), writer.get("worktree"), writer.get("task_owner")}
            for writer in active_writers
        ):
            raise InvalidTransition("cleanup item still has an active writer")
        root = Path(inventory["repository_root"])
        recorded_identity = self._recorded_cleanup_identity(item, inventory)

        def retired_postcondition() -> bool:
            if item["item_type"] == "branch":
                return (
                    _run_git(
                        root,
                        "show-ref",
                        "--verify",
                        "--quiet",
                        f"refs/heads/{item['item_key']}",
                        check=False,
                    ).returncode
                    != 0
                )
            if item["item_type"] == "worktree":
                target = str(Path(item["item_key"]).resolve())
                listed = _run_git(root, "worktree", "list", "--porcelain", check=False).stdout
                return f"worktree {target}\n" not in f"{listed}\n" and not Path(target).exists()
            if item["item_type"] == "stash":
                return (
                    _run_git(
                        root, "rev-parse", "--verify", item["item_key"], check=False
                    ).returncode
                    != 0
                )
            raise InvalidTransition("item type has no destructive retirement owner")

        existing_effect = self.store.one(
            """SELECT * FROM cleanup_effects_v2
               WHERE cleanup_item_id=? ORDER BY updated_at DESC LIMIT 1""",
            (cleanup_item_id,),
            required=False,
        )
        if existing_effect is not None and existing_effect["status"] == "succeeded":
            if not retired_postcondition():
                raise InvalidTransition("completed cleanup effect no longer matches physical state")
            return existing_effect
        effect_id = existing_effect["id"] if existing_effect else new_id("cleanup-effect")
        precondition = {
            "inventory_root": inventory["inventory_root"],
            "bundle_root": bundle["bundle_root"],
            "classification": item["classification"],
            "physical_identity": recorded_identity,
        }
        with self.store.transaction() as db:
            if existing_effect is None:
                db.execute(
                    """INSERT INTO cleanup_effects_v2(
                           id,cleanup_item_id,effect_type,precondition_json,status,updated_at
                       ) VALUES(?,?,?,?,'running',?)""",
                    (
                        effect_id,
                        cleanup_item_id,
                        f"retire_{item['item_type']}",
                        _canonical(precondition),
                        utc_now(),
                    ),
                )
            else:
                if _loads(existing_effect["precondition_json"], {}) != precondition:
                    raise InvalidTransition("cleanup retry precondition differs")
                db.execute(
                    """UPDATE cleanup_effects_v2
                       SET status='running',result_json=NULL,completed_at=NULL,updated_at=?
                       WHERE id=?""",
                    (utc_now(), effect_id),
                )
            db.execute(
                "UPDATE cleanup_items_v2 SET status='running',updated_at=? WHERE id=?",
                (utc_now(), cleanup_item_id),
            )
        try:
            with _repository_lock(root, "cleanup-retirement"):
                already_absent = retired_postcondition()
                if already_absent and existing_effect is None:
                    raise InvalidTransition("cleanup item disappeared after preservation")
                if not already_absent:
                    self._require_cleanup_identity(root, item, recorded_identity)
                    if item["item_type"] == "branch":
                        _run_git(root, "branch", "-D", item["item_key"])
                    elif item["item_type"] == "worktree":
                        _run_git(root, "worktree", "remove", "--force", item["item_key"])
                    elif item["item_type"] == "stash":
                        _run_git(root, "stash", "drop", item["item_key"])
                    else:
                        raise InvalidTransition("item type has no destructive retirement owner")
                if not retired_postcondition():
                    raise RuntimeError("cleanup physical postcondition was not achieved")
                self._fault("retirement:after_physical_effect")
                result = {
                    "retired": item["item_key"],
                    "item_type": item["item_type"],
                    "already_absent": already_absent,
                    "physical_identity": recorded_identity,
                }
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
