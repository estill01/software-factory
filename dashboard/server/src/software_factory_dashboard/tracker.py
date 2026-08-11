from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
import difflib
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from threading import RLock
from types import ModuleType
from typing import Any, Iterable, Mapping
import unicodedata

from .catalog import ProjectRecord


MAX_TRACKER_BYTES = 4 * 1024 * 1024
MAX_ANALYSIS_CACHE_ENTRIES = 128
MAX_MAP_ROWS = 500
MAX_SECTION_PREVIEW_CHARS = 12_000
MAX_DIFF_PREVIEW_CHARS = 32_000
VERIFIER_TIMEOUT_SECONDS = 15
GIT_TIMEOUT_SECONDS = 5
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")

DASHBOARD_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_VERIFIER_PATH = (
    DASHBOARD_REPOSITORY_ROOT
    / "author-implementation-trackers"
    / "scripts"
    / "verify_tracker.py"
)
DEFAULT_CORE_COMPATIBILITY: dict[str, dict[str, frozenset[str]]] = {
    str(DASHBOARD_REPOSITORY_ROOT): {
        "docs/software-factory-learning-and-capability-evolution-mvp-implementation-tracker.md": frozenset(
            {"ecc7b31ebd7bd7bc825746dded4059be2ddcc56377f4a702e1ab7781d09e07c6"}
        ),
        "docs/software-factory-tracker-authoring-supervision-implementation-tracker.md": frozenset(
            {"dc87fde4b7fe4017a82426ad0199dd2ef226eb8d9a658d348ec0aea6ea2dd424"}
        ),
    }
}


class TrackerProjectionError(ValueError):
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
class TrackerFile:
    path: Path
    relative_path: str
    content: bytes
    text: str
    content_sha256: str
    size: int
    mtime_ns: int
    device: int
    inode: int


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def tracker_identity(project_id: str, relative_path: str) -> str:
    return sha256(f"{project_id}\0{relative_path}".encode("utf-8")).hexdigest()


def _validate_relative_tracker_path(value: str) -> PurePosixPath:
    if not isinstance(value, str):
        raise TrackerProjectionError("invalid_tracker_path", "Tracker path must be a string.")
    pure = PurePosixPath(value)
    if (
        not value
        or len(value) > 500
        or any(unicodedata.category(character).startswith("C") for character in value)
        or "\\" in value
        or pure.is_absolute()
        or ".." in pure.parts
        or not value.endswith(".md")
    ):
        raise TrackerProjectionError(
            "invalid_tracker_path",
            "Tracker path must be a bounded relative Markdown path without traversal.",
        )
    return pure


def _read_tracker_file(root: Path, relative_path: str) -> TrackerFile:
    pure = _validate_relative_tracker_path(relative_path)
    try:
        canonical_root = root.resolve(strict=True)
        candidate = root.joinpath(*pure.parts)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(canonical_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise TrackerProjectionError(
            "tracker_unavailable",
            f"Tracker path is unavailable or escaped its registered root: {exc}",
            status=404,
        ) from exc
    if root != canonical_root or root.is_symlink():
        raise TrackerProjectionError(
            "project_root_changed",
            "Registered project root is no longer canonical.",
            status=409,
        )
    if candidate.is_symlink() or resolved != candidate:
        raise TrackerProjectionError(
            "tracker_path_escape",
            "Tracker path must not use symlinks or aliases.",
            status=400,
        )
    relative = resolved.relative_to(canonical_root)
    if any(
        canonical_root.joinpath(*relative.parts[:index]).is_symlink()
        for index in range(1, len(relative.parts))
    ):
        raise TrackerProjectionError(
            "tracker_path_escape",
            "Tracker path traversed a symlink inside the registered root.",
            status=400,
        )
    try:
        path_metadata = resolved.lstat()
        descriptor = os.open(
            resolved,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or (before.st_dev, before.st_ino) != (path_metadata.st_dev, path_metadata.st_ino)
            ):
                raise TrackerProjectionError(
                    "tracker_changed_during_read",
                    "Tracker identity changed while it was being opened.",
                    status=409,
                    retryable=True,
                )
            content = stream.read(MAX_TRACKER_BYTES + 1)
            after = os.fstat(stream.fileno())
        current_path_metadata = resolved.lstat()
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (after.st_dev, after.st_ino)
            != (current_path_metadata.st_dev, current_path_metadata.st_ino)
        ):
            raise TrackerProjectionError(
                "tracker_changed_during_read",
                "Tracker changed while it was being read; retry from a stable source revision.",
                status=409,
                retryable=True,
            )
        if len(content) > MAX_TRACKER_BYTES:
            raise TrackerProjectionError(
                "tracker_size_limit",
                f"Tracker exceeds the {MAX_TRACKER_BYTES}-byte read limit.",
                status=413,
            )
        text = content.decode("utf-8")
    except TrackerProjectionError:
        raise
    except (OSError, UnicodeError) as exc:
        raise TrackerProjectionError(
            "tracker_read_failed",
            f"Tracker could not be read as UTF-8: {exc}",
            status=422,
        ) from exc
    return TrackerFile(
        path=resolved,
        relative_path=relative.as_posix(),
        content=content,
        text=text,
        content_sha256=sha256(content).hexdigest(),
        size=after.st_size,
        mtime_ns=after.st_mtime_ns,
        device=after.st_dev,
        inode=after.st_ino,
    )


def _refresh_tracker_file(root: Path, tracker: TrackerFile) -> TrackerFile:
    try:
        metadata = tracker.path.lstat()
    except OSError as exc:
        raise TrackerProjectionError(
            "tracker_changed_during_projection",
            f"Tracker became unavailable during projection: {exc}",
            status=409,
            retryable=True,
        ) from exc
    current_identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
    )
    prior_identity = (tracker.device, tracker.inode, tracker.size, tracker.mtime_ns)
    if current_identity == prior_identity and not tracker.path.is_symlink():
        return tracker
    refreshed = _read_tracker_file(root, tracker.relative_path)
    if refreshed.content_sha256 != tracker.content_sha256:
        raise TrackerProjectionError(
            "tracker_changed_during_projection",
            "Tracker content changed during projection; retry from the new source revision.",
            status=409,
            retryable=True,
        )
    return refreshed


def _slug(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^\w\- ]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", "-", normalized)
    return normalized.strip("-") or "section"


def _heading_anchors(lines: list[str], verifier: ModuleType) -> dict[int, str]:
    anchors: dict[int, str] = {}
    counts: Counter[str] = Counter()
    for index, line in verifier.iter_unfenced_lines(lines):
        match = verifier.SECTION_HEADING.match(line.rstrip())
        if not match:
            continue
        base = _slug(match.group("title"))
        occurrence = counts[base]
        counts[base] += 1
        anchors[index + 1] = base if occurrence == 0 else f"{base}-{occurrence}"
    return anchors


def _section_ranges(
    lines: list[str],
    verifier: ModuleType,
    *,
    base_line: int = 0,
    minimum_level: int = 1,
) -> list[dict[str, Any]]:
    headings: list[tuple[int, int, str]] = []
    for index, line in verifier.iter_unfenced_lines(lines):
        match = verifier.SECTION_HEADING.match(line.rstrip())
        if not match:
            continue
        level = len(line) - len(line.lstrip("#"))
        if level >= minimum_level:
            headings.append((index, level, match.group("title").strip()))
    sections: list[dict[str, Any]] = []
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break
        sections.append(
            {
                "title": title,
                "normalized_title": verifier.normalize_heading(title),
                "level": level,
                "line": base_line + start + 1,
                "end_line": base_line + max(start + 1, end),
                "body_start": start + 1,
                "body_end": end,
            }
        )
    return sections


def _plain_preview(lines: Iterable[str], *, maximum: int = 700) -> str | None:
    parts: list[str] = []
    for raw in lines:
        value = raw.strip()
        if not value or value.startswith("|") or value.startswith("```") or value.startswith("~~~"):
            continue
        value = re.sub(r"^[-*+]\s+", "", value)
        value = re.sub(r"^\d+[.)]\s+", "", value)
        value = value.replace("`", "").replace("**", "")
        parts.append(value)
        if sum(len(part) for part in parts) >= maximum:
            break
    if not parts:
        return None
    joined = " ".join(parts)
    return joined if len(joined) <= maximum else joined[: maximum - 1].rstrip() + "…"


def _section_body(lines: list[str], section: dict[str, Any] | None) -> list[str]:
    if section is None:
        return []
    return lines[section["body_start"] : section["body_end"]]


def _section_projection(lines: list[str], section: dict[str, Any]) -> dict[str, Any]:
    markdown = "\n".join(_section_body(lines, section)).strip("\n")
    content = markdown.encode("utf-8")
    truncated = len(markdown) > MAX_SECTION_PREVIEW_CHARS
    preview = markdown[:MAX_SECTION_PREVIEW_CHARS]
    if truncated:
        preview = preview.rstrip() + "\n\n[Preview truncated; open the exact source range.]"
    return {
        "title": section["title"],
        "normalized_title": section["normalized_title"],
        "line": section["line"],
        "end_line": section["end_line"],
        "anchor": section["anchor"],
        "markdown_preview": preview,
        "preview_truncated": truncated,
        "content_sha256": sha256(content).hexdigest(),
    }


def _parse_dependencies(value: str) -> list[int]:
    if value.strip().strip("`") in {"", "—", "-", "none", "None"}:
        return []
    dependencies: set[int] = set()
    ranges: list[tuple[int, int]] = []
    for match in re.finditer(r"(?P<start>\d+)\s*[–-]\s*(?P<end>\d+)", value):
        start = int(match.group("start"))
        end = int(match.group("end"))
        ranges.append((match.start(), match.end()))
        if start <= end and end - start <= 500:
            dependencies.update(range(start, end + 1))
    remainder = value
    for start, end in reversed(ranges):
        remainder = remainder[:start] + " " * (end - start) + remainder[end:]
    dependencies.update(int(number) for number in re.findall(r"\d+", remainder))
    return sorted(dependencies)


def _parse_tables(
    lines: list[str],
    *,
    base_line: int,
    maximum_rows: int = MAX_MAP_ROWS,
) -> list[dict[str, Any]]:
    def split_row(value: str) -> list[str]:
        row = value.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|") and not row.endswith(r"\|"):
            row = row[:-1]
        cells: list[str] = []
        current: list[str] = []
        escaped = False
        for character in row:
            if escaped:
                current.append(character)
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "|":
                cells.append("".join(current).strip())
                current = []
            else:
                current.append(character)
        if escaped:
            current.append("\\")
        cells.append("".join(current).strip())
        return cells

    tables: list[dict[str, Any]] = []
    index = 0
    rows_seen = 0
    while index + 1 < len(lines) and rows_seen < maximum_rows:
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        separator_cells = split_row(separator)
        if (
            not header.startswith("|")
            or not separator.startswith("|")
            or not separator_cells
            or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells)
        ):
            index += 1
            continue
        headers = split_row(header)
        rows: list[list[str]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].strip().startswith("|"):
            rows.append(split_row(lines[cursor]))
            rows_seen += 1
            cursor += 1
            if rows_seen >= maximum_rows:
                break
        tables.append(
            {
                "line": base_line + index + 1,
                "headers": headers,
                "rows": rows,
                "truncated": rows_seen >= maximum_rows,
            }
        )
        index = cursor
    return tables


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TrackerProjectionError(
            "git_unavailable",
            f"Git currentness could not be inspected: {exc}",
            status=503,
            retryable=True,
        ) from exc


def _run_git_bytes(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TrackerProjectionError(
            "git_unavailable",
            f"Git currentness could not be inspected: {exc}",
            status=503,
            retryable=True,
        ) from exc


def _run_git_bytes_with_input(
    root: Path,
    arguments: list[str],
    input_bytes: bytes,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            input=input_bytes,
            check=False,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TrackerProjectionError(
            "git_unavailable",
            f"Git currentness could not be inspected: {exc}",
            status=503,
            retryable=True,
        ) from exc


def _git_value(root: Path, *arguments: str) -> str | None:
    result = _run_git(root, *arguments)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _git_blob_contents(root: Path, object_ids: Iterable[str]) -> dict[str, bytes]:
    requested = list(dict.fromkeys(object_ids))
    if not requested:
        return {}
    result = _run_git_bytes_with_input(
        root,
        ["cat-file", "--batch"],
        "".join(f"{object_id}\n" for object_id in requested).encode("ascii"),
    )
    if result.returncode != 0:
        raise TrackerProjectionError(
            "git_blob_read_failed",
            result.stderr.decode("utf-8", errors="replace").strip()
            or "Git could not read committed tracker blobs.",
        )
    contents: dict[str, bytes] = {}
    position = 0
    for requested_id in requested:
        header_end = result.stdout.find(b"\n", position)
        if header_end < 0:
            raise TrackerProjectionError(
                "git_blob_output_invalid",
                "Git returned a truncated batch blob header.",
            )
        header = result.stdout[position:header_end].split()
        position = header_end + 1
        if len(header) == 2 and header[1] == b"missing":
            continue
        if len(header) != 3 or not header[2].isdigit():
            raise TrackerProjectionError(
                "git_blob_output_invalid",
                "Git returned an invalid batch blob header.",
            )
        size = int(header[2])
        content_end = position + size
        if content_end > len(result.stdout):
            raise TrackerProjectionError(
                "git_blob_output_invalid",
                "Git returned a truncated committed tracker blob.",
            )
        contents[requested_id] = result.stdout[position:content_end]
        position = content_end
        if position < len(result.stdout) and result.stdout[position : position + 1] == b"\n":
            position += 1
    return contents


def _diff_projection(
    committed: bytes | None,
    current: bytes,
    *,
    tracked: bool,
    include_preview: bool = True,
) -> dict[str, Any]:
    if committed is None and tracked:
        return {
            "status": "unavailable",
            "changed": None,
            "base": None,
            "added_lines": None,
            "removed_lines": None,
            "preview": None,
            "truncated": False,
            "error": {
                "code": "committed_tracker_unavailable",
                "message": "The tracker HEAD blob is unavailable for comparison.",
            },
        }
    try:
        before = (committed or b"").decode("utf-8").splitlines()
        after = current.decode("utf-8").splitlines()
    except UnicodeError:
        return {
            "status": "unavailable",
            "changed": None,
            "base": None,
            "added_lines": None,
            "removed_lines": None,
            "preview": None,
            "truncated": False,
            "error": {
                "code": "tracker_diff_encoding",
                "message": "The tracker HEAD blob is not valid UTF-8.",
            },
        }
    lines = list(
        difflib.unified_diff(
            before,
            after,
            fromfile="HEAD" if tracked else "/dev/null",
            tofile="working-tree",
            lineterm="",
            n=3,
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    preview_length = sum(len(line) + 1 for line in lines)
    truncated = preview_length > MAX_DIFF_PREVIEW_CHARS
    preview = "\n".join(lines) if include_preview else None
    if preview is not None and truncated:
        preview = preview[:MAX_DIFF_PREVIEW_CHARS].rstrip() + "\n[Diff preview truncated.]"
    return {
        "status": "available",
        "changed": bool(lines),
        "base": "HEAD" if tracked else "empty",
        "added_lines": added,
        "removed_lines": removed,
        "preview": preview,
        "truncated": truncated,
        "error": None,
    }


def _git_last_commits(
    root: Path,
    relative_paths: set[str],
) -> dict[str, dict[str, str]]:
    if not relative_paths:
        return {}
    result = _run_git_bytes(
        root,
        "log",
        "--no-renames",
        "--format=%x1e%H%x00%cI%x00%s%x00",
        "--name-only",
        "-z",
        "--",
        *sorted(relative_paths),
    )
    if result.returncode != 0:
        raise TrackerProjectionError(
            "git_log_failed",
            result.stderr.decode("utf-8", errors="replace").strip()
            or "Git could not inspect tracker history.",
        )
    commits: dict[str, dict[str, str]] = {}
    for record in result.stdout.split(b"\x1e")[1:]:
        fields = record.split(b"\x00")
        if len(fields) < 5:
            continue
        try:
            revision = fields[0].decode("ascii")
            committed_at = fields[1].decode("utf-8")
            subject = fields[2].decode("utf-8", errors="replace")
        except UnicodeError as exc:
            raise TrackerProjectionError(
                "git_log_output_invalid",
                "Git returned invalid tracker-history metadata.",
            ) from exc
        for raw_path in fields[4:]:
            if not raw_path:
                continue
            if raw_path.startswith(b"\n"):
                raw_path = raw_path[1:]
            try:
                relative_path = raw_path.decode("utf-8")
            except UnicodeError as exc:
                raise TrackerProjectionError(
                    "git_log_output_invalid",
                    "Git returned a non-UTF-8 tracker path.",
                ) from exc
            if relative_path in relative_paths and relative_path not in commits:
                commits[relative_path] = {
                    "revision": revision,
                    "committed_at": committed_at,
                    "subject": subject,
                }
        if len(commits) == len(relative_paths):
            break
    return commits


def _git_unavailable(
    tracker: TrackerFile,
    bound_content_sha256: str | None,
    error: TrackerProjectionError,
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "repository_head": None,
        "branch": None,
        "tracked": None,
        "untracked": None,
        "worktree_changed": None,
        "porcelain": [],
        "git_blob": None,
        "index_blob": None,
        "committed_content_sha256": None,
        "content_matches_head": None,
        "last_commit": None,
        "upstream": None,
        "ahead": None,
        "behind": None,
        "durability": "unavailable",
        "bound_content_sha256": bound_content_sha256,
        "binding_status": "unknown",
        "diff": {
            "status": "unavailable",
            "changed": None,
            "base": None,
            "added_lines": None,
            "removed_lines": None,
            "preview": None,
            "truncated": False,
            "error": {"code": error.code, "message": str(error)},
        },
        "errors": [{"code": error.code, "message": str(error)}],
    }


def _git_currentness_batch(
    root: Path,
    trackers: Iterable[TrackerFile],
    *,
    bound_content_sha256: dict[str, str | None] | None = None,
    include_diff_preview: bool = True,
) -> dict[str, dict[str, Any]]:
    tracker_list = list(trackers)
    bound_hashes = bound_content_sha256 or {}
    for tracker in tracker_list:
        bound_hash = bound_hashes.get(tracker.relative_path)
        if bound_hash is not None and not FINGERPRINT_RE.fullmatch(bound_hash):
            raise TrackerProjectionError(
                "invalid_bound_tracker_hash",
                "Bound tracker hash must be a lowercase SHA-256 digest.",
            )
    if not tracker_list:
        return {}
    paths = sorted({tracker.relative_path for tracker in tracker_list})
    try:
        head = _git_value(root, "rev-parse", "HEAD")
        branch = _git_value(root, "symbolic-ref", "--short", "-q", "HEAD")
        tracked_result = _run_git_bytes(root, "ls-files", "--stage", "-z", "--", *paths)
        if tracked_result.returncode != 0:
            raise TrackerProjectionError(
                "git_index_failed",
                tracked_result.stderr.decode("utf-8", errors="replace").strip()
                or "Git could not inspect tracker index entries.",
            )
        index_blob_by_path: dict[str, str] = {}
        indexed_paths: set[str] = set()
        for raw_entry in tracked_result.stdout.split(b"\x00"):
            if not raw_entry:
                continue
            try:
                header, raw_path = raw_entry.split(b"\t", 1)
                mode, object_id, stage = header.decode("ascii").split()
                relative_path = raw_path.decode("utf-8")
            except (UnicodeError, ValueError) as exc:
                raise TrackerProjectionError(
                    "git_index_output_invalid",
                    "Git returned invalid tracker index metadata.",
                ) from exc
            if mode and relative_path in paths:
                indexed_paths.add(relative_path)
                if stage == "0":
                    index_blob_by_path[relative_path] = object_id

        head_blob_by_path: dict[str, str] = {}
        if head is not None:
            tree_result = _run_git_bytes(
                root,
                "ls-tree",
                "-r",
                "-z",
                head,
                "--",
                *paths,
            )
            if tree_result.returncode != 0:
                raise TrackerProjectionError(
                    "git_tree_failed",
                    tree_result.stderr.decode("utf-8", errors="replace").strip()
                    or "Git could not inspect committed tracker blobs.",
                )
            for raw_entry in tree_result.stdout.split(b"\x00"):
                if not raw_entry:
                    continue
                try:
                    header, raw_path = raw_entry.split(b"\t", 1)
                    _, object_type, object_id = header.decode("ascii").split()
                    relative_path = raw_path.decode("utf-8")
                except (UnicodeError, ValueError) as exc:
                    raise TrackerProjectionError(
                        "git_tree_output_invalid",
                        "Git returned invalid committed tracker metadata.",
                    ) from exc
                if object_type == "blob" and relative_path in paths:
                    head_blob_by_path[relative_path] = object_id

        status_result = _run_git_bytes(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            *paths,
        )
        if status_result.returncode != 0:
            raise TrackerProjectionError(
                "git_status_failed",
                status_result.stderr.decode("utf-8", errors="replace").strip()
                or "Git status failed.",
            )
        status_by_path: dict[str, list[str]] = {path: [] for path in paths}
        status_entries = status_result.stdout.split(b"\x00")
        index = 0
        while index < len(status_entries):
            raw_entry = status_entries[index]
            index += 1
            if not raw_entry:
                continue
            try:
                decoded = raw_entry.decode("utf-8")
            except UnicodeError as exc:
                raise TrackerProjectionError(
                    "git_status_output_invalid",
                    "Git returned a non-UTF-8 tracker status path.",
                ) from exc
            if len(decoded) < 4 or decoded[2] != " ":
                continue
            status_code = decoded[:2]
            relative_path = decoded[3:]
            if relative_path in status_by_path:
                status_by_path[relative_path].append(f"{status_code} {relative_path}")
            if any(character in "RC" for character in status_code) and index < len(status_entries):
                index += 1

        committed_contents = _git_blob_contents(root, head_blob_by_path.values())
        history_paths = set(head_blob_by_path) | indexed_paths
        last_commits = _git_last_commits(root, history_paths) if head is not None else {}
        upstream = _git_value(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        ahead = behind = None
        durability = "unavailable"
        if head is not None and upstream is not None:
            counts = _git_value(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
            if counts:
                pieces = counts.split()
                if len(pieces) == 2 and all(piece.isdigit() for piece in pieces):
                    ahead, behind = (int(piece) for piece in pieces)
                    durability = (
                        "matched"
                        if ahead == 0 and behind == 0
                        else "diverged"
                        if ahead and behind
                        else "ahead"
                        if ahead
                        else "behind"
                    )
        if _git_value(root, "rev-parse", "HEAD") != head:
            raise TrackerProjectionError(
                "git_changed_during_projection",
                "Repository HEAD changed during tracker projection; retry the repository snapshot.",
                status=409,
                retryable=True,
            )
        projected: dict[str, dict[str, Any]] = {}
        for tracker in tracker_list:
            bound_hash = bound_hashes.get(tracker.relative_path)
            status_lines = status_by_path[tracker.relative_path]
            untracked = tracker.relative_path not in indexed_paths
            committed_blob = head_blob_by_path.get(tracker.relative_path)
            index_blob = index_blob_by_path.get(tracker.relative_path)
            committed_content = (
                committed_contents.get(committed_blob) if committed_blob is not None else None
            )
            committed_content_sha256 = (
                sha256(committed_content).hexdigest()
                if committed_content is not None
                else None
            )
            binding_status = (
                "unavailable"
                if bound_hash is None
                else "current"
                if bound_hash == tracker.content_sha256
                else "stale"
            )
            projected[tracker.relative_path] = {
                "status": "available",
                "repository_head": head,
                "branch": branch,
                "tracked": tracker.relative_path in indexed_paths,
                "untracked": untracked,
                "worktree_changed": bool(status_lines),
                "porcelain": status_lines,
                "git_blob": committed_blob,
                "index_blob": index_blob,
                "committed_content_sha256": committed_content_sha256,
                "content_matches_head": (
                    committed_content_sha256 == tracker.content_sha256
                    if committed_content_sha256 is not None
                    else None
                ),
                "last_commit": last_commits.get(tracker.relative_path),
                "upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "durability": durability,
                "bound_content_sha256": bound_hash,
                "binding_status": binding_status,
                "diff": _diff_projection(
                    committed_content,
                    tracker.content,
                    tracked=tracker.relative_path in indexed_paths,
                    include_preview=include_diff_preview,
                ),
                "errors": [],
            }
        return projected
    except TrackerProjectionError as exc:
        return {
            tracker.relative_path: _git_unavailable(
                tracker,
                bound_hashes.get(tracker.relative_path),
                exc,
            )
            for tracker in tracker_list
        }


def _git_currentness(
    root: Path,
    tracker: TrackerFile,
    *,
    bound_content_sha256: str | None,
    include_diff_preview: bool = True,
) -> dict[str, Any]:
    return _git_currentness_batch(
        root,
        [tracker],
        bound_content_sha256={tracker.relative_path: bound_content_sha256},
        include_diff_preview=include_diff_preview,
    )[tracker.relative_path]


def _document_analysis(
    tracker: TrackerFile,
    verifier: ModuleType,
    verifier_result: dict[str, Any],
    *,
    profile: str,
    profile_reason: str,
) -> dict[str, Any]:
    lines = tracker.text.splitlines()
    anchors = _heading_anchors(lines, verifier)
    blocks = verifier.parse_blocks(lines)
    status_table, _ = verifier.parse_status_table(lines)
    first_block_line = blocks[0].line if blocks else len(lines) + 1
    preamble = lines[: first_block_line - 1]
    first_document_section = next(
        (
            index
            for index, line in verifier.iter_unfenced_lines(preamble)
            if verifier.SECTION_HEADING.match(line.rstrip())
            and len(line) - len(line.lstrip("#")) >= 2
        ),
        len(preamble),
    )
    metadata, metadata_duplicates = verifier.parse_labeled_bullets(
        preamble[:first_document_section]
    )
    title = next(
        (
            line[2:].strip()
            for line in lines
            if line.startswith("# ") and not line.startswith("## ")
        ),
        "Untitled implementation tracker",
    )

    all_sections = _section_ranges(lines, verifier)
    block_ranges = [
        (block.line, block.line + len(block.body))
        for block in blocks
    ]
    document_level_sections = [
        section
        for section in all_sections
        if not any(start <= section["line"] <= end for start, end in block_ranges)
    ]
    document_sections = [
        _section_projection(
            lines,
            {
                **section,
                "anchor": anchors.get(section["line"], _slug(section["title"])),
            },
        )
        for section in document_level_sections
    ]

    frames: list[dict[str, Any]] = []
    maps: list[dict[str, Any]] = []
    supplemental: list[dict[str, Any]] = []
    for section in document_level_sections:
        normalized = section["normalized_title"]
        body = _section_body(lines, section)
        section_record = {
            "title": section["title"],
            "line": section["line"],
            "end_line": section["end_line"],
            "anchor": anchors.get(section["line"], _slug(section["title"])),
        }
        if normalized in {"target-product capability frame", "mission frame"}:
            fields, duplicates = verifier.parse_labeled_bullets(body)
            frames.append({**section_record, "fields": fields, "duplicate_fields": sorted(duplicates)})
        if any(token in normalized for token in ("owner", "source", "authority", "adaptation map", "prior-work")):
            tables = _parse_tables(body, base_line=section["line"])
            if tables:
                maps.append({**section_record, "tables": tables})
        if (
            "verification matrix" in normalized
            or "definition of done" in normalized
            or "final integrated acceptance" in normalized
            or normalized == "final acceptance"
        ):
            supplemental.append(
                {
                    **section_record,
                    "preview": _plain_preview(body),
                    "tables": _parse_tables(body, base_line=section["line"]),
                }
            )

    statuses: dict[int, list[str | None]] = {}
    raw_blocks: list[dict[str, Any]] = []
    for block in blocks:
        status, status_line = verifier.parse_status(block)
        statuses.setdefault(block.number, []).append(status)
        block_lines_list = list(block.body)
        sections = _section_ranges(
            block_lines_list,
            verifier,
            base_line=block.line,
            minimum_level=block.level + 1,
        )
        by_name = {section["normalized_title"]: section for section in sections}
        dependencies_text = status_table.get(block.number, ("", "", 0))[1]
        dependencies = _parse_dependencies(dependencies_text)
        evidence_section = by_name.get("completion evidence")
        evidence_body = _section_body(block_lines_list, evidence_section)
        evidence_preview = _plain_preview(evidence_body)
        evidence_present = any(
            verifier.is_concrete_evidence(line)
            for _, line in verifier.iter_unfenced_lines(evidence_body)
            if line.strip()
        )
        evidence_posture = (
            "recorded"
            if status == "accepted" and evidence_present
            else "missing"
            if status == "accepted"
            else "open"
        )
        capability = by_name.get("target-product capability delta")
        capability_fields: dict[str, str] = {}
        if capability is not None:
            capability_fields, _ = verifier.parse_labeled_bullets(
                _section_body(block_lines_list, capability)
            )
        raw_blocks.append(
            {
                "number": block.number,
                "title": block.title,
                "line": block.line,
                "anchor": anchors.get(block.line, _slug(f"block-{block.number}-{block.title}")),
                "status": status,
                "status_line": status_line,
                "dependencies": dependencies,
                "dependency_expression": dependencies_text,
                "objective": _plain_preview(
                    _section_body(block_lines_list, by_name.get("objective"))
                ),
                "stop": _plain_preview(_section_body(block_lines_list, by_name.get("stop"))),
                "capability_delta": capability_fields,
                "completion_evidence": {
                    "present": evidence_present,
                    "posture": evidence_posture,
                    "line": evidence_section["line"] if evidence_section else None,
                    "preview": evidence_preview,
                },
                "sections": [
                    _section_projection(
                        block_lines_list,
                        {
                            **section,
                            "anchor": anchors.get(
                                section["line"],
                                _slug(section["title"]),
                            ),
                        },
                    )
                    for section in sections
                ],
            }
        )

    unique_blocks: dict[int, Mapping[str, Any] | None] = {}
    for block in raw_blocks:
        number = block["number"]
        unique_blocks[number] = block if number not in unique_blocks else None

    def blocked_ancestors(block: Mapping[str, Any]) -> list[int]:
        """Return exact transitive dependencies whose recorded status is blocked."""

        blocked: set[int] = set()
        visited: set[int] = set()
        pending = list(block["dependencies"])
        while pending:
            dependency = pending.pop()
            if dependency in visited:
                continue
            visited.add(dependency)
            dependency_block = unique_blocks.get(dependency)
            dependency_status = statuses.get(dependency, [])
            if len(dependency_status) == 1 and dependency_status[0] == "blocked":
                blocked.add(dependency)
            if dependency_block is not None:
                pending.extend(dependency_block["dependencies"])
        return sorted(blocked)

    for block in raw_blocks:
        dependency_statuses = [
            {
                "number": dependency,
                "status": statuses[dependency][0]
                if len(statuses.get(dependency, [])) == 1
                else None,
            }
            for dependency in block["dependencies"]
        ]
        block["dependency_statuses"] = dependency_statuses
        block["blocked_ancestors"] = blocked_ancestors(block)
        block["eligible"] = bool(
            verifier_result["valid"]
            and block["status"] == "not-started"
            and all(item["status"] == "accepted" for item in dependency_statuses)
        )

    exact_counts = dict(
        sorted(Counter(block["status"] or "unknown" for block in raw_blocks).items())
    )
    accepted_count = exact_counts.get("accepted", 0)
    all_accepted = bool(raw_blocks) and accepted_count == len(raw_blocks)
    tracker_status_value = metadata.get("tracker status")
    tracker_status = (
        verifier.normalized_value(tracker_status_value)
        if tracker_status_value is not None
        else None
    )
    return {
        "title": title,
        "tracker_status": tracker_status,
        "tracker_sequence": metadata.get("tracker sequence"),
        "metadata": metadata,
        "metadata_duplicate_fields": sorted(metadata_duplicates),
        "profile": profile,
        "profile_reason": profile_reason,
        "verifier": verifier_result,
        "counts": {
            "total": len(raw_blocks),
            "by_status": exact_counts,
            "accepted": accepted_count,
            "open": len(raw_blocks) - accepted_count,
            "with_completion_evidence": sum(
                1 for block in raw_blocks if block["completion_evidence"]["present"]
            ),
            "evidence_by_posture": dict(
                sorted(
                    Counter(
                        block["completion_evidence"]["posture"]
                        for block in raw_blocks
                    ).items()
                )
            ),
        },
        "current_blocks": [
            block["number"] for block in raw_blocks if block["status"] == "in-progress"
        ],
        "current_block_details": [
            {
                "number": block["number"],
                "title": block["title"],
                "status": block["status"],
                "line": block["line"],
                "status_line": block["status_line"],
            }
            for block in raw_blocks
            if block["status"] == "in-progress"
        ],
        "eligible_blocks": [block["number"] for block in raw_blocks if block["eligible"]],
        "header_block_status_conflict": bool(
            tracker_status
            and (
                (all_accepted and tracker_status not in {"accepted", "completed"})
                or (tracker_status in {"accepted", "completed"} and not all_accepted)
            )
        ),
        "frames": frames,
        "owner_source_maps": maps,
        "supplemental_sections": supplemental,
        "document_sections": document_sections,
        "blocks": raw_blocks,
        "parser_limitations": [
            "Markdown prose is previewed only; exact source ranges remain authoritative.",
            "Dependency ranges and explicit Block numbers are derived from the status table.",
            "Unknown sections are preserved as source-linked ranges rather than reinterpreted.",
        ],
    }


class TrackerProjectionService:
    def __init__(
        self,
        *,
        verifier_path: Path = DEFAULT_VERIFIER_PATH,
        core_compatibility: dict[str, dict[str, frozenset[str]]] | None = None,
        maximum_cache_entries: int = MAX_ANALYSIS_CACHE_ENTRIES,
    ) -> None:
        if maximum_cache_entries < 0:
            raise ValueError("maximum_cache_entries must be nonnegative")
        self.verifier_path = verifier_path
        self.core_compatibility = (
            DEFAULT_CORE_COMPATIBILITY
            if core_compatibility is None
            else core_compatibility
        )
        self.maximum_cache_entries = maximum_cache_entries
        self._cache: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()
        self._module: ModuleType | None = None
        self._module_sha256: str | None = None
        self._verifier_revision_cache: tuple[str, dict[str, Any]] | None = None
        self._lock = RLock()
        self.verifier_run_count = 0

    def _verifier_source(self) -> tuple[Path, bytes, str]:
        path = self.verifier_path
        try:
            resolved = path.resolve(strict=True)
            metadata = resolved.lstat()
        except (OSError, RuntimeError) as exc:
            raise TrackerProjectionError(
                "tracker_verifier_unavailable",
                f"Maintained tracker verifier is unavailable: {exc}",
                status=503,
                retryable=True,
            ) from exc
        if path.is_symlink() or resolved != path or not stat.S_ISREG(metadata.st_mode):
            raise TrackerProjectionError(
                "unsafe_tracker_verifier",
                "Maintained tracker verifier must be a canonical regular file.",
                status=503,
            )
        content = resolved.read_bytes()
        return resolved, content, sha256(content).hexdigest()

    def verifier_revision(self) -> dict[str, Any]:
        path, _, digest = self._verifier_source()
        with self._lock:
            if self._verifier_revision_cache is not None:
                cached_digest, cached_revision = self._verifier_revision_cache
                if cached_digest == digest:
                    return dict(cached_revision)
            try:
                relative = path.relative_to(DASHBOARD_REPOSITORY_ROOT).as_posix()
            except ValueError:
                owning_revision = None
            else:
                owning_revision = _git_value(
                    DASHBOARD_REPOSITORY_ROOT,
                    "log",
                    "-1",
                    "--format=%H",
                    "--",
                    relative,
                )
            revision = {
                "path": str(path),
                "sha256": digest,
                "owning_revision": owning_revision,
            }
            self._verifier_revision_cache = (digest, revision)
            return dict(revision)

    def _verifier_module(self, digest: str) -> ModuleType:
        if self._module is not None and self._module_sha256 == digest:
            return self._module
        module_name = f"_software_factory_tracker_verifier_{digest}"
        spec = importlib.util.spec_from_file_location(module_name, self.verifier_path)
        if spec is None or spec.loader is None:
            raise TrackerProjectionError(
                "tracker_verifier_unavailable",
                "Maintained tracker verifier could not be loaded for read-only parsing.",
                status=503,
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self._module = module
        self._module_sha256 = digest
        return module

    def _profile(self, root: Path, tracker: TrackerFile) -> tuple[str, str]:
        allowed_hashes = self.core_compatibility.get(str(root), {}).get(
            tracker.relative_path,
            frozenset(),
        )
        if tracker.content_sha256 in allowed_hashes:
            return "core", "inherited core path and content root frozen by the compatibility contract"
        if re.search(
            r"^#{2,6}\s+Target-product capability frame\s*$",
            tracker.text,
            re.IGNORECASE | re.MULTILINE,
        ):
            return "full", "current capability frame present"
        return "full", "full is the fail-closed default; no inherited core grant is recorded"

    def _invoke_verifier(
        self,
        tracker: TrackerFile,
        *,
        profile: str,
        verifier_source: dict[str, Any],
    ) -> dict[str, Any]:
        arguments = [
            sys.executable,
            str(self.verifier_path),
            str(tracker.path),
            "--profile",
            profile,
            "--json",
        ]
        try:
            result = subprocess.run(
                arguments,
                check=False,
                capture_output=True,
                text=True,
                timeout=VERIFIER_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TrackerProjectionError(
                "tracker_verifier_failed",
                f"Maintained tracker verifier could not run: {exc}",
                status=503,
                retryable=True,
            ) from exc
        self.verifier_run_count += 1
        if result.returncode not in {0, 1}:
            raise TrackerProjectionError(
                "tracker_verifier_failed",
                result.stderr.strip() or "Maintained tracker verifier did not return JSON diagnostics.",
                status=503,
                retryable=True,
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise TrackerProjectionError(
                "tracker_verifier_invalid_output",
                "Maintained tracker verifier returned invalid JSON.",
                status=503,
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("path") != str(tracker.path)
            or payload.get("profile") != profile
            or not isinstance(payload.get("blocks"), list)
            or any(
                not isinstance(number, int) or isinstance(number, bool)
                for number in payload.get("blocks", [])
            )
            or not isinstance(payload.get("errors"), list)
            or any(not isinstance(error, str) for error in payload.get("errors", []))
            or not isinstance(payload.get("warnings"), list)
            or any(not isinstance(warning, str) for warning in payload.get("warnings", []))
        ):
            raise TrackerProjectionError(
                "tracker_verifier_invalid_output",
                "Maintained tracker verifier returned an incompatible JSON contract.",
                status=503,
            )
        return {
            "profile": profile,
            "valid": result.returncode == 0 and not payload.get("errors"),
            "exit_status": result.returncode,
            "blocks": payload["blocks"],
            "errors": payload["errors"],
            "warnings": payload["warnings"],
            "command": arguments,
            "owner": {
                "identity": "author-implementation-trackers/verify_tracker.py",
                **verifier_source,
            },
        }

    def _project_loaded(
        self,
        project: ProjectRecord,
        tracker: TrackerFile,
        git: dict[str, Any],
        bound_content_sha256: str | None,
        refresh_analysis_cache: dict[
            tuple[str, str, str],
            dict[str, Any],
        ] | None = None,
    ) -> dict[str, Any]:
        root = Path(project.root)
        tracker = _refresh_tracker_file(root, tracker)
        with self._lock:
            _, _, verifier_digest = self._verifier_source()
            verifier_source = self.verifier_revision()
            profile, profile_reason = self._profile(root, tracker)
            cache_key = (tracker.content_sha256, verifier_digest, profile)
            cached = (
                refresh_analysis_cache.get(cache_key)
                if refresh_analysis_cache is not None
                else None
            )
            if cached is None:
                cached = self._cache.get(cache_key)
            cache_status = "hit" if cached is not None else "miss"
            if cached is None:
                verifier_module = self._verifier_module(verifier_digest)
                verifier_result = self._invoke_verifier(
                    tracker,
                    profile=profile,
                    verifier_source=verifier_source,
                )
                confirmed_tracker = _read_tracker_file(root, tracker.relative_path)
                if confirmed_tracker.content_sha256 != tracker.content_sha256:
                    raise TrackerProjectionError(
                        "tracker_changed_during_verification",
                        "Tracker content changed while the maintained verifier was running.",
                        status=409,
                        retryable=True,
                    )
                tracker = confirmed_tracker
                cached = _document_analysis(
                    tracker,
                    verifier_module,
                    verifier_result,
                    profile=profile,
                    profile_reason=profile_reason,
                )
                self._cache[cache_key] = cached
                while len(self._cache) > self.maximum_cache_entries:
                    self._cache.popitem(last=False)
            else:
                if cache_key in self._cache:
                    self._cache.move_to_end(cache_key)
            if refresh_analysis_cache is not None:
                refresh_analysis_cache[cache_key] = cached
        verifier_view = {
            **cached["verifier"],
            "command": [
                sys.executable,
                str(self.verifier_path),
                str(tracker.path),
                "--profile",
                profile,
                "--json",
            ],
            "owner": {
                "identity": "author-implementation-trackers/verify_tracker.py",
                **verifier_source,
            },
        }
        cached_view = {**cached, "verifier": verifier_view}
        observed_at = _timestamp()
        projection_material = {
            "project_id": project.id,
            "relative_path": tracker.relative_path,
            "content_sha256": tracker.content_sha256,
            "verifier_sha256": verifier_digest,
            "profile": cached_view["profile"],
            "git": git,
        }
        projection_fingerprint = sha256(_canonical_json(projection_material)).hexdigest()
        progress_posture = (
            "stale"
            if git["binding_status"] == "stale"
            else "untracked"
            if git["untracked"] is True
            else "dirty"
            if git["worktree_changed"] is True
            else "current"
            if git["status"] == "available"
            else "unavailable"
        )
        return {
            "id": tracker_identity(project.id, tracker.relative_path),
            "project_id": project.id,
            "project_label": project.label,
            "relative_path": tracker.relative_path,
            "status": "available",
            "observed_at": observed_at,
            "fingerprint": projection_fingerprint,
            "source": {
                "kind": "tracker-markdown",
                "identity": f"{project.id}:{tracker.relative_path}",
                "revision": tracker.content_sha256,
            },
            "raw_file": {
                "path": str(tracker.path),
                "line": 1,
                "read_only": True,
                "content_sha256": tracker.content_sha256,
                "size": tracker.size,
                "mtime_ns": str(tracker.mtime_ns),
            },
            "git": git,
            "progress_posture": progress_posture,
            "analysis_cache": {
                "status": cache_status,
                "key": sha256(_canonical_json(cache_key)).hexdigest(),
            },
            "coverage": {
                "status": "complete" if git["status"] == "available" else "partial",
                "observed": ["tracker-markdown", "maintained-verifier"]
                + (["git-currentness"] if git["status"] == "available" else []),
                "missing": [] if git["status"] == "available" else ["git-currentness"],
            },
            "limitations": list(cached_view["parser_limitations"])
            + (
                ["No canonical run-bound tracker hash is present in this tracker source."]
                if bound_content_sha256 is None
                else []
            ),
            **cached_view,
        }

    def project(
        self,
        project: ProjectRecord,
        relative_path: str,
        *,
        bound_content_sha256: str | None = None,
        include_diff_preview: bool = True,
    ) -> dict[str, Any]:
        root = Path(project.root)
        tracker = _read_tracker_file(root, relative_path)
        git = _git_currentness(
            root,
            tracker,
            bound_content_sha256=bound_content_sha256,
            include_diff_preview=include_diff_preview,
        )
        return self._project_loaded(project, tracker, git, bound_content_sha256)

    def source(self, project: ProjectRecord, relative_path: str) -> TrackerFile:
        return _read_tracker_file(Path(project.root), relative_path)

    def diff(self, project: ProjectRecord, relative_path: str) -> dict[str, Any]:
        root = Path(project.root)
        tracker = _read_tracker_file(root, relative_path)
        git = _git_currentness(
            root,
            tracker,
            bound_content_sha256=None,
            include_diff_preview=True,
        )
        return {
            "tracker_id": tracker_identity(project.id, tracker.relative_path),
            "content_sha256": tracker.content_sha256,
            "repository_head": git["repository_head"],
            "diff": git["diff"],
        }

    def project_many(
        self,
        project: ProjectRecord,
        relative_paths: Iterable[str],
        *,
        bound_content_sha256: dict[str, str | None] | None = None,
        include_diff_preview: bool = True,
        refresh_analysis_cache: dict[
            tuple[str, str, str],
            dict[str, Any],
        ] | None = None,
    ) -> dict[str, dict[str, Any] | TrackerProjectionError]:
        ordered_paths = list(dict.fromkeys(relative_paths))
        bound_hashes = bound_content_sha256 or {}
        root = Path(project.root)
        trackers: dict[str, TrackerFile] = {}
        outcomes: dict[str, dict[str, Any] | TrackerProjectionError] = {}
        request_cache = (
            refresh_analysis_cache
            if refresh_analysis_cache is not None
            else {}
        )
        for relative_path in ordered_paths:
            try:
                trackers[relative_path] = _read_tracker_file(root, relative_path)
            except TrackerProjectionError as error:
                outcomes[relative_path] = error
        git_by_path = _git_currentness_batch(
            root,
            trackers.values(),
            bound_content_sha256=bound_hashes,
            include_diff_preview=include_diff_preview,
        )
        for relative_path in ordered_paths:
            tracker = trackers.get(relative_path)
            if tracker is None:
                continue
            try:
                outcomes[relative_path] = self._project_loaded(
                    project,
                    tracker,
                    git_by_path[relative_path],
                    bound_hashes.get(relative_path),
                    request_cache,
                )
            except TrackerProjectionError as error:
                outcomes[relative_path] = error
        return outcomes

    @staticmethod
    def summary(detail: dict[str, Any]) -> dict[str, Any]:
        summary = {
            key: detail[key]
            for key in (
                "id",
                "project_id",
                "project_label",
                "relative_path",
                "status",
                "observed_at",
                "fingerprint",
                "source",
                "raw_file",
                "title",
                "tracker_status",
                "profile",
                "profile_reason",
                "verifier",
                "counts",
                "current_blocks",
                "current_block_details",
                "eligible_blocks",
                "header_block_status_conflict",
                "git",
                "progress_posture",
                "coverage",
                "limitations",
            )
        }
        git = summary.get("git")
        if isinstance(git, dict) and isinstance(git.get("diff"), dict):
            summary["git"] = {
                **git,
                "diff": {**git["diff"], "preview": None},
            }
        return summary


def unavailable_tracker(
    project: ProjectRecord,
    relative_path: str,
    error: TrackerProjectionError,
) -> dict[str, Any]:
    observed_at = _timestamp()
    return {
        "id": tracker_identity(project.id, relative_path),
        "project_id": project.id,
        "project_label": project.label,
        "relative_path": relative_path,
        "status": "unavailable",
        "observed_at": observed_at,
        "fingerprint": None,
        "source": {
            "kind": "tracker-markdown",
            "identity": f"{project.id}:{relative_path}",
            "revision": "unavailable",
        },
        "coverage": {"status": "unavailable", "observed": [], "missing": ["tracker"]},
        "limitations": ["This tracker could not be projected; other trackers remain independent."],
        "error": {
            "code": error.code,
            "message": str(error),
            "retryable": error.retryable,
        },
    }
