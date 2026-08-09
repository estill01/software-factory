from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from tempfile import mkstemp
from threading import RLock
from typing import Any, Callable, Iterable


CATALOG_VERSION = 1
DEFAULT_TRACKER_PATTERNS = (
    "docs/**/*implementation-tracker.md",
    "*implementation-tracker.md",
)
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
PROJECT_KEYS = {
    "id",
    "label",
    "root",
    "tracker_patterns",
    "description",
    "archived",
}
PRESENTATION_KEYS = {"label", "tracker_patterns", "description"}
MAX_TRACKER_CANDIDATES = 250
MAX_CATALOG_BYTES = 1024 * 1024
MAX_PROJECTS = 200


class CatalogError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    label: str
    root: str
    tracker_patterns: tuple[str, ...] = ()
    description: str | None = None
    archived: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "root": self.root,
            "tracker_patterns": list(self.tracker_patterns),
            "description": self.description,
            "archived": self.archived,
        }


@dataclass(frozen=True)
class CatalogState:
    projects: tuple[ProjectRecord, ...] = ()
    version: int = CATALOG_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "projects": [project.as_dict() for project in self.projects],
        }


@dataclass(frozen=True)
class LoadedCatalog:
    state: CatalogState
    fingerprint: str
    recovered_from_previous: bool = False


def default_catalog_path() -> Path:
    return Path.home() / ".codex" / "software-factory" / "dashboard" / "projects.json"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def catalog_fingerprint(state: CatalogState) -> str:
    return sha256(_canonical_json(state.as_dict())).hexdigest()


def _clean_text(value: Any, *, field: str, maximum: int, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise CatalogError("invalid_catalog_field", f"{field} must be a string.")
    cleaned = value.strip()
    if not cleaned and optional:
        return None
    if not cleaned:
        raise CatalogError("invalid_catalog_field", f"{field} must not be empty.")
    if len(cleaned) > maximum:
        raise CatalogError(
            "invalid_catalog_field",
            f"{field} must be at most {maximum} characters.",
        )
    return cleaned


def validate_project_id(value: Any) -> str:
    if not isinstance(value, str) or not PROJECT_ID_RE.fullmatch(value):
        raise CatalogError(
            "invalid_project_id",
            "Project ID must be 2-64 lowercase letters, numbers, dots, dashes, or underscores.",
        )
    return value


def validate_catalog_fingerprint(value: Any) -> str:
    if not isinstance(value, str) or not FINGERPRINT_RE.fullmatch(value):
        raise CatalogError(
            "invalid_catalog_fingerprint",
            "source_fingerprint must be a 64-character lowercase hexadecimal digest.",
        )
    return value


def validate_tracker_patterns(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > 16:
        raise CatalogError(
            "invalid_tracker_patterns",
            "tracker_patterns must be a list of at most 16 relative Markdown globs.",
        )
    patterns: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise CatalogError("invalid_tracker_pattern", "Tracker patterns must be strings.")
        pattern = raw.strip()
        path = PurePosixPath(pattern)
        if (
            not pattern
            or len(pattern) > 240
            or "\x00" in pattern
            or "\\" in pattern
            or path.is_absolute()
            or ".." in path.parts
            or not pattern.endswith(".md")
        ):
            raise CatalogError(
                "invalid_tracker_pattern",
                "Tracker patterns must be bounded relative .md globs that do not traverse.",
            )
        patterns.append(pattern)
    return tuple(sorted(set(patterns)))


def _run_git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CatalogError(
            "git_unavailable",
            f"Git could not inspect the registered root: {exc}",
            status=503,
            retryable=True,
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        reason = detail[-1] if detail else "Git rejected the repository root."
        raise CatalogError("invalid_git_root", reason)
    return result.stdout.strip()


def canonical_git_root(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise CatalogError("invalid_project_root", "Project root must be an absolute path.")
    submitted = Path(value)
    if not submitted.is_absolute() or ".." in submitted.parts:
        raise CatalogError(
            "invalid_project_root",
            "Project root must be an absolute canonical path without traversal.",
        )
    try:
        resolved = submitted.resolve(strict=True)
    except OSError as exc:
        raise CatalogError("missing_project_root", f"Project root is unavailable: {exc}") from exc
    if str(submitted) != str(resolved):
        raise CatalogError(
            "noncanonical_project_root",
            "Project root must not use symlinks, aliases, or noncanonical segments.",
        )
    if not resolved.is_dir():
        raise CatalogError("invalid_project_root", "Project root must be a directory.")
    git_root = Path(_run_git(resolved, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if git_root != resolved:
        raise CatalogError(
            "invalid_git_root",
            "Register the canonical Git top-level directory, not one of its descendants.",
        )
    return resolved


def project_from_input(value: Any) -> ProjectRecord:
    if not isinstance(value, dict):
        raise CatalogError("invalid_project", "project must be an object.")
    extra = set(value) - PROJECT_KEYS
    missing = {"id", "label", "root"} - set(value)
    if extra:
        raise CatalogError(
            "unsupported_catalog_field",
            f"Catalog records cannot store: {', '.join(sorted(extra))}.",
        )
    if missing:
        raise CatalogError(
            "missing_catalog_field",
            f"Project is missing: {', '.join(sorted(missing))}.",
        )
    if "archived" in value and value["archived"] is not False:
        raise CatalogError(
            "invalid_catalog_field",
            "New projects enter the visible catalog; archive them with the explicit archive action.",
        )
    return ProjectRecord(
        id=validate_project_id(value["id"]),
        label=_clean_text(value["label"], field="label", maximum=80) or "",
        root=str(canonical_git_root(value["root"])),
        tracker_patterns=validate_tracker_patterns(value.get("tracker_patterns", [])),
        description=_clean_text(
            value.get("description"),
            field="description",
            maximum=500,
            optional=True,
        ),
        archived=False,
    )


def _project_from_stored(value: Any) -> ProjectRecord:
    if not isinstance(value, dict) or set(value) != PROJECT_KEYS:
        extra = sorted(set(value) - PROJECT_KEYS) if isinstance(value, dict) else []
        suffix = f" Unsupported fields: {', '.join(extra)}." if extra else ""
        raise CatalogError(
            "invalid_catalog_schema",
            f"Stored project records must contain only the versioned discovery schema.{suffix}",
        )
    root = value["root"]
    if not isinstance(root, str) or not Path(root).is_absolute() or ".." in Path(root).parts:
        raise CatalogError("invalid_catalog_schema", "Stored project root is not canonical.")
    if not isinstance(value["archived"], bool):
        raise CatalogError("invalid_catalog_schema", "Stored archived posture must be boolean.")
    return ProjectRecord(
        id=validate_project_id(value["id"]),
        label=_clean_text(value["label"], field="label", maximum=80) or "",
        root=root,
        tracker_patterns=validate_tracker_patterns(value["tracker_patterns"]),
        description=_clean_text(
            value["description"],
            field="description",
            maximum=500,
            optional=True,
        ),
        archived=value["archived"],
    )


def _roots_overlap(first: str, second: str) -> bool:
    first_path = Path(first)
    second_path = Path(second)
    return (
        first_path == second_path
        or first_path.is_relative_to(second_path)
        or second_path.is_relative_to(first_path)
    )


def _validate_project_set(projects: Iterable[ProjectRecord]) -> tuple[ProjectRecord, ...]:
    ordered = tuple(sorted(projects, key=lambda project: project.id))
    ids: set[str] = set()
    for index, project in enumerate(ordered):
        if project.id in ids:
            raise CatalogError("duplicate_project_id", f"Duplicate project ID: {project.id}.")
        ids.add(project.id)
        for other in ordered[index + 1 :]:
            if _roots_overlap(project.root, other.root):
                raise CatalogError(
                    "overlapping_project_roots",
                    f"Project roots overlap: {project.id} and {other.id}.",
                )
    return ordered


class CatalogStore:
    def __init__(self, path: Path | None = None) -> None:
        selected = path or default_catalog_path()
        if not selected.is_absolute() or ".." in selected.parts:
            raise CatalogError(
                "invalid_catalog_path",
                "Catalog state path must be absolute and must not traverse.",
                status=500,
            )
        # Preserve the lexical leaf so lstat checks can detect and reject symlinks.
        self.path = selected
        self.previous_path = self.path.with_suffix(self.path.suffix + ".previous")
        self._lock = RLock()

    def _check_file(self, path: Path) -> None:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise CatalogError(
                "unsafe_catalog_file",
                "Catalog state must be a regular non-symlink file.",
                status=500,
            )
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise CatalogError(
                "unsafe_catalog_owner",
                "Catalog state must be owned by the dashboard operator.",
                status=500,
            )
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise CatalogError(
                "unsafe_catalog_permissions",
                "Catalog state must not be readable or writable by group or others.",
                status=500,
            )
        if metadata.st_size > MAX_CATALOG_BYTES:
            raise CatalogError(
                "catalog_size_limit",
                f"Catalog state exceeds the {MAX_CATALOG_BYTES}-byte limit.",
                status=500,
            )

    def _read_state(self, path: Path) -> CatalogState:
        self._check_file(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CatalogError(
                "invalid_catalog_json",
                f"Catalog JSON is invalid: {exc}",
                status=500,
            ) from exc
        if not isinstance(payload, dict) or set(payload) != {"version", "projects"}:
            raise CatalogError(
                "invalid_catalog_schema",
                "Catalog root must contain exactly version and projects.",
                status=500,
            )
        if payload["version"] != CATALOG_VERSION:
            raise CatalogError(
                "unsupported_catalog_version",
                f"Catalog version {payload['version']!r} is not supported.",
                status=500,
            )
        if not isinstance(payload["projects"], list):
            raise CatalogError("invalid_catalog_schema", "projects must be a list.", status=500)
        if len(payload["projects"]) > MAX_PROJECTS:
            raise CatalogError(
                "catalog_project_limit",
                f"Catalog state exceeds the {MAX_PROJECTS}-project limit.",
                status=500,
            )
        projects = tuple(_project_from_stored(item) for item in payload["projects"])
        ordered = _validate_project_set(projects)
        if projects != ordered:
            raise CatalogError(
                "nondeterministic_catalog_order",
                "Stored projects must be ordered by stable project ID.",
                status=500,
            )
        return CatalogState(projects=ordered)

    def load(self) -> LoadedCatalog:
        with self._lock:
            if not self.path.exists():
                if self.path.is_symlink():
                    self._check_file(self.path)
                if self.previous_path.exists():
                    previous = self._read_state(self.previous_path)
                    return LoadedCatalog(previous, catalog_fingerprint(previous), True)
                if self.previous_path.is_symlink():
                    self._check_file(self.previous_path)
                empty = CatalogState()
                return LoadedCatalog(empty, catalog_fingerprint(empty))
            try:
                current = self._read_state(self.path)
                return LoadedCatalog(current, catalog_fingerprint(current))
            except CatalogError as current_error:
                if current_error.code.startswith("unsafe_catalog_"):
                    raise
                if not self.previous_path.exists():
                    raise
                previous = self._read_state(self.previous_path)
                return LoadedCatalog(previous, catalog_fingerprint(previous), True)

    def _ensure_parent(self) -> None:
        parent = self.path.parent
        if parent.is_symlink():
            raise CatalogError(
                "unsafe_catalog_directory",
                "Catalog directory must be a regular directory, not a symlink.",
                status=500,
            )
        if parent.exists():
            metadata = parent.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or parent.is_symlink():
                raise CatalogError(
                    "unsafe_catalog_directory",
                    "Catalog directory must be a regular directory, not a symlink.",
                    status=500,
                )
            if stat.S_IMODE(metadata.st_mode) & 0o077:
                raise CatalogError(
                    "unsafe_catalog_permissions",
                    "Catalog directory must use owner-only permissions.",
                    status=500,
                )
            if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
                raise CatalogError(
                    "unsafe_catalog_owner",
                    "Catalog directory must be owned by the dashboard operator.",
                    status=500,
                )
            return
        parent.mkdir(parents=True, mode=0o700)
        parent.chmod(0o700)

    def _write_bytes(self, target: Path, content: bytes) -> None:
        descriptor, temporary_name = mkstemp(prefix=f".{target.name}.", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            target.chmod(0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()

    def _write(self, state: CatalogState) -> LoadedCatalog:
        self._ensure_parent()
        encoded = (json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")
        if self.path.exists():
            try:
                self._read_state(self.path)
            except CatalogError:
                pass
            else:
                self._write_bytes(self.previous_path, self.path.read_bytes())
        self._write_bytes(self.path, encoded)
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return LoadedCatalog(state, catalog_fingerprint(state))

    def _mutate(
        self,
        expected_fingerprint: str,
        transform: Callable[[CatalogState], CatalogState],
    ) -> LoadedCatalog:
        with self._lock:
            loaded = self.load()
            validate_catalog_fingerprint(expected_fingerprint)
            if loaded.recovered_from_previous:
                raise CatalogError(
                    "catalog_recovery_read_only",
                    "The current catalog is invalid; repair it before mutating recovered prior state.",
                    status=409,
                )
            if expected_fingerprint != loaded.fingerprint:
                raise CatalogError(
                    "stale_catalog_fingerprint",
                    "Catalog changed after it was observed; refresh before retrying.",
                    status=409,
                    retryable=True,
                )
            next_state = transform(loaded.state)
            next_state = CatalogState(projects=_validate_project_set(next_state.projects))
            return self._write(next_state)

    def register(self, expected_fingerprint: str, value: Any) -> LoadedCatalog:
        project = project_from_input(value)

        def add(state: CatalogState) -> CatalogState:
            if len(state.projects) >= MAX_PROJECTS:
                raise CatalogError(
                    "catalog_project_limit",
                    f"Catalog state supports at most {MAX_PROJECTS} projects.",
                )
            if any(existing.id == project.id for existing in state.projects):
                raise CatalogError("duplicate_project_id", f"Project ID {project.id} already exists.")
            if any(_roots_overlap(existing.root, project.root) for existing in state.projects):
                raise CatalogError(
                    "overlapping_project_roots",
                    "Registered project roots must be distinct and non-nested.",
                )
            return CatalogState(projects=state.projects + (project,))

        return self._mutate(expected_fingerprint, add)

    def update_presentation(
        self,
        expected_fingerprint: str,
        project_id: str,
        changes: Any,
    ) -> LoadedCatalog:
        validate_project_id(project_id)
        if not isinstance(changes, dict) or not changes or set(changes) - PRESENTATION_KEYS:
            raise CatalogError(
                "invalid_presentation_update",
                "Presentation updates may change only label, description, or tracker_patterns.",
            )

        def update(state: CatalogState) -> CatalogState:
            found = False
            projects: list[ProjectRecord] = []
            for project in state.projects:
                if project.id != project_id:
                    projects.append(project)
                    continue
                found = True
                projects.append(
                    replace(
                        project,
                        label=(
                            _clean_text(changes["label"], field="label", maximum=80) or ""
                            if "label" in changes
                            else project.label
                        ),
                        description=(
                            _clean_text(
                                changes["description"],
                                field="description",
                                maximum=500,
                                optional=True,
                            )
                            if "description" in changes
                            else project.description
                        ),
                        tracker_patterns=(
                            validate_tracker_patterns(changes["tracker_patterns"])
                            if "tracker_patterns" in changes
                            else project.tracker_patterns
                        ),
                    )
                )
            if not found:
                raise CatalogError(
                    "project_not_found",
                    f"Project {project_id} is not registered.",
                    status=404,
                )
            return CatalogState(projects=tuple(projects))

        return self._mutate(expected_fingerprint, update)

    def set_archived(
        self,
        expected_fingerprint: str,
        project_id: str,
        archived: bool,
        *,
        confirmation: str | None = None,
    ) -> LoadedCatalog:
        validate_project_id(project_id)
        if archived and confirmation != f"archive:{project_id}":
            raise CatalogError(
                "archive_confirmation_required",
                "Archiving requires the exact project-scoped confirmation.",
            )

        def update(state: CatalogState) -> CatalogState:
            found = False
            projects: list[ProjectRecord] = []
            for project in state.projects:
                if project.id == project_id:
                    found = True
                    projects.append(replace(project, archived=archived))
                else:
                    projects.append(project)
            if not found:
                raise CatalogError(
                    "project_not_found",
                    f"Project {project_id} is not registered.",
                    status=404,
                )
            return CatalogState(projects=tuple(projects))

        return self._mutate(expected_fingerprint, update)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_tracker_candidates(root: Path, patterns: Iterable[str]) -> list[str]:
    candidates: set[str] = set()
    for pattern in sorted(set(DEFAULT_TRACKER_PATTERNS).union(patterns)):
        validate_tracker_patterns([pattern])
        try:
            matches = root.glob(pattern)
        except (OSError, ValueError) as exc:
            raise CatalogError("tracker_discovery_failed", f"Tracker pattern failed: {exc}") from exc
        for match in matches:
            if len(candidates) >= MAX_TRACKER_CANDIDATES:
                raise CatalogError(
                    "tracker_candidate_limit",
                    f"Tracker discovery exceeded {MAX_TRACKER_CANDIDATES} candidates.",
                )
            try:
                resolved = match.resolve(strict=True)
                relative = resolved.relative_to(root)
            except (OSError, ValueError) as exc:
                raise CatalogError(
                    "tracker_path_escape",
                    f"Tracker candidate escaped its registered root: {match}.",
                ) from exc
            if match.is_symlink() or not resolved.is_file():
                continue
            if any(
                (root / Path(*relative.parts[:index])).is_symlink()
                for index in range(1, len(relative.parts))
            ):
                raise CatalogError(
                    "tracker_path_escape",
                    f"Tracker candidate traversed a symlink: {relative.as_posix()}.",
                )
            candidates.add(relative.as_posix())
    return sorted(candidates)


def discover_project(project: ProjectRecord) -> dict[str, Any]:
    observed = _timestamp()
    base = {
        **project.as_dict(),
        "observed_at": observed,
    }
    root = Path(project.root)
    try:
        if not root.exists():
            raise CatalogError("missing_project_root", "Registered project root is missing.")
        resolved = root.resolve(strict=True)
        if resolved != root or root.is_symlink():
            raise CatalogError(
                "project_root_changed",
                "Registered project root is no longer canonical.",
            )
        git_root = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if git_root != root:
            raise CatalogError("project_root_changed", "Git top-level no longer matches the catalog root.")
        revision = _run_git(root, "rev-parse", "HEAD")
        branch_result = subprocess.run(
            ["git", "-C", str(root), "symbolic-ref", "--short", "-q", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = branch_result.stdout.strip() or None
        trackers = _safe_tracker_candidates(root, project.tracker_patterns)
        discovery_material = {
            "project_id": project.id,
            "root": project.root,
            "revision": revision,
            "branch": branch,
            "tracker_candidates": trackers,
        }
        return {
            **base,
            "discovery": {
                "status": "available",
                "fingerprint": sha256(_canonical_json(discovery_material)).hexdigest(),
                "git": {"status": "available", "revision": revision, "branch": branch},
                "trackers": {"status": "available", "candidates": trackers},
                "source_families": {
                    "supervision": {"status": "unavailable", "reason": "Available after Block 4."},
                    "codex_tasks": {"status": "unavailable", "reason": "Available after Block 5."},
                },
                "coverage": "partial",
                "limitations": [
                    "Project discovery returns tracker paths only; read-only content projection is available from /api/v1/trackers.",
                    "Supervision and Codex task sources are not connected yet.",
                ],
                "errors": [],
            },
        }
    except (CatalogError, OSError, subprocess.TimeoutExpired) as exc:
        code = exc.code if isinstance(exc, CatalogError) else "project_discovery_failed"
        return {
            **base,
            "discovery": {
                "status": "unavailable",
                "fingerprint": None,
                "git": {"status": "unavailable", "revision": None, "branch": None},
                "trackers": {"status": "unavailable", "candidates": []},
                "source_families": {
                    "supervision": {"status": "unavailable", "reason": "Available after Block 4."},
                    "codex_tasks": {"status": "unavailable", "reason": "Available after Block 5."},
                },
                "coverage": "unavailable",
                "limitations": ["This project could not be refreshed; other projects remain independent."],
                "errors": [{"code": code, "message": str(exc)}],
            },
        }


def discover_catalog(loaded: LoadedCatalog, *, include_archived: bool) -> list[dict[str, Any]]:
    return [
        discover_project(project)
        for project in loaded.state.projects
        if include_archived or not project.archived
    ]
