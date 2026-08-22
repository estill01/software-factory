from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="microseconds")


def parse_time(value: str | None) -> dt.datetime | None:
    if value is None:
        return None
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def json_load(value: str | bytes | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)


def ensure_within(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    root = parent.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {path}") from exc
    return resolved


def normalize_relative_path(value: str) -> str:
    if value == "*":
        return value
    raw = value.replace("\\", "/").strip()
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"invalid repository-relative path: {value!r}")
    return path.as_posix().rstrip("/")


def scope_contains(parent: Mapping[str, Any], child: Mapping[str, Any]) -> bool:
    """Return whether a delegated scope is no broader than its parent scope.

    Scope keys are intentionally explicit. Unknown keys must match exactly rather
    than being silently widened.
    """

    for key, child_value in child.items():
        if key not in parent:
            return False
        parent_value = parent[key]
        if key in {"repository", "mission", "project", "target_type", "target_id"}:
            if parent_value != "*" and parent_value != child_value:
                return False
        elif key in {"paths", "resources"}:
            parent_items = [normalize_relative_path(v) for v in parent_value]
            child_items = [normalize_relative_path(v) for v in child_value]
            if "*" in parent_items:
                continue
            for item in child_items:
                if not any(
                    item == allowed or item.startswith(f"{allowed}/") for allowed in parent_items
                ):
                    return False
        elif isinstance(parent_value, list):
            if not set(child_value).issubset(set(parent_value)):
                return False
        elif isinstance(parent_value, Mapping) and isinstance(child_value, Mapping):
            if not scope_contains(parent_value, child_value):
                return False
        elif parent_value != child_value:
            return False
    return True


def scope_allows(scope: Mapping[str, Any], requested: Mapping[str, Any]) -> bool:
    return scope_contains(scope, requested)


def atomic_write(path: Path, payload: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp.exists():
            temp.unlink()


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted(set(values))
