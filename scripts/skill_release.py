#!/usr/bin/env python3
"""Stage and atomically select accepted Software Factory skill releases."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence


SKILLS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
)
MANIFEST_NAME = "release-manifest.json"
HISTORY_NAME = "activation-history.jsonl"
ACCEPTANCE_NAME = "accepted-releases.jsonl"
LOCK_NAME = ".release.lock"
KEY_DIRECTORY = ".software-factory-release-keys"
SCHEMA_VERSION = 1


class ReleaseError(RuntimeError):
    """A release contract or currentness check failed."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_sha256(value: str, *, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
        raise ReleaseError(f"{label} must be an exact lowercase SHA-256")
    return value


def exact_git_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise ReleaseError("Source commit must be an exact lowercase Git SHA-1")
    return value


def bounded_id(value: str, *, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,159}", value or ""):
        raise ReleaseError(f"{label} is invalid")
    return value


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_git(repo: Path, *arguments: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseError(f"Git command failed: {detail or arguments[0]}")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def ensure_directory(path: Path, *, label: str, create: bool = True) -> Path:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"{label} must be a real directory")
    return path.resolve(strict=True)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_tree_directories(path: Path) -> None:
    directories = [Path(base) for base, _names, _files in os.walk(path)]
    for directory in reversed(directories):
        fsync_directory(directory)


def seal_release_tree(path: Path) -> None:
    directories: list[Path] = []
    for base, directory_names, file_names in os.walk(path):
        base_path = Path(base)
        directories.append(base_path)
        for name in directory_names:
            child = base_path / name
            if child.is_symlink():
                raise ReleaseError("Release tree contains a directory symlink")
        for name in file_names:
            child = base_path / name
            metadata = child.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ReleaseError("Release tree contains a non-regular file")
            child.chmod(0o555 if metadata.st_mode & stat.S_IXUSR else 0o444)
    for directory in reversed(directories):
        directory.chmod(0o555)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        payload = canonical(value) + b"\n"
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_directory(path.parent)


@contextlib.contextmanager
def release_lock(release_root: Path) -> Iterator[None]:
    lock_path = release_root / LOCK_NAME
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def release_key_path(release_root: Path) -> Path:
    key_directory = release_root.parent / KEY_DIRECTORY
    key_name = hashlib.sha256(str(release_root).encode("utf-8")).hexdigest() + ".key"
    return key_directory / key_name


def release_key(release_root: Path, *, allow_create: bool) -> bytes:
    path = release_key_path(release_root)
    protected_state_exists = any(
        (release_root / name).exists() for name in (ACCEPTANCE_NAME, HISTORY_NAME)
    )
    if not path.exists():
        if protected_state_exists or not allow_create:
            raise ReleaseError("External release authority key is missing")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ReleaseError("External release authority directory is symlinked")
        path.parent.chmod(0o700)
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o400,
        )
        try:
            os.write(descriptor, secrets.token_bytes(32))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        fsync_directory(path.parent)
    if path.is_symlink():
        raise ReleaseError("External release authority key is symlinked")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        key = os.read(descriptor, 33)
    finally:
        os.close(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size != 32
        or len(key) != 32
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ReleaseError("External release authority key is invalid")
    return key


def record_hmac(key: bytes, material: Mapping[str, Any]) -> str:
    return hmac.new(key, canonical(material), hashlib.sha256).hexdigest()


def load_bounded_json(path: Path, *, label: str, maximum: int = 65536) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"{label} must be a real regular file")
    metadata = path.stat()
    if metadata.st_size > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    with path.open("rb") as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} must be a JSON object")
    return value


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, canonical(record) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)


def append_history(release_root: Path, record: Mapping[str, Any]) -> None:
    append_jsonl(release_root / HISTORY_NAME, record)


def jsonl_records(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"{label} is not a canonical regular file")
    records: list[dict[str, Any]] = []
    for line in path.read_bytes().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"{label} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ReleaseError(f"{label} record must be an object")
        records.append(value)
    return records


def acceptance_records(release_root: Path) -> list[dict[str, Any]]:
    values = jsonl_records(
        release_root / ACCEPTANCE_NAME, label="Release acceptance history"
    )
    if not values:
        return []
    key = release_key(release_root, allow_create=False)
    previous: str | None = None
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "release_id",
        "source_commit",
        "manifest_sha256",
        "candidate_root_sha256",
        "review_record_id",
        "review_root_sha256",
        "previous_record_hmac_sha256",
        "record_hmac_sha256",
    }
    for index, value in enumerate(values, start=1):
        material = {
            item: member for item, member in value.items() if item != "record_hmac_sha256"
        }
        if (
            set(value) != exact_keys
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("kind") != "software-factory-release-acceptance"
            or value.get("record_id") != f"RELEASE-ACCEPTANCE-{index}"
            or value.get("previous_record_hmac_sha256") != previous
            or value.get("record_hmac_sha256") != record_hmac(key, material)
        ):
            raise ReleaseError("Release acceptance history was forged or reordered")
        bounded_id(str(value["release_id"]), label="accepted release ID")
        exact_git_commit(str(value["source_commit"]))
        for label, field in (
            ("accepted manifest", "manifest_sha256"),
            ("accepted candidate", "candidate_root_sha256"),
            ("accepted review", "review_root_sha256"),
        ):
            exact_sha256(str(value[field]), label=label)
        bounded_id(str(value["review_record_id"]), label="accepted review record")
        previous = str(value["record_hmac_sha256"])
    return values


def accepted_release_record(
    release_root: Path, release_id: str
) -> dict[str, Any] | None:
    matches = [
        item for item in acceptance_records(release_root) if item["release_id"] == release_id
    ]
    if len(matches) > 1:
        raise ReleaseError("Release acceptance identity is duplicated")
    return matches[0] if matches else None


def append_acceptance(
    release_root: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    records = acceptance_records(release_root)
    existing = [
        item for item in records if item["release_id"] == manifest["release_id"]
    ]
    if existing:
        if len(existing) != 1:
            raise ReleaseError("Release acceptance identity is duplicated")
        review = manifest["independent_review"]
        if any(
            existing[0].get(field) != expected
            for field, expected in (
                ("source_commit", manifest["source_commit"]),
                ("manifest_sha256", manifest["manifest_sha256"]),
                ("candidate_root_sha256", manifest["candidate_root_sha256"]),
                ("review_record_id", review["record_id"]),
                ("review_root_sha256", review["review_root_sha256"]),
            )
        ):
            raise ReleaseError("Existing release acceptance differs from its manifest")
        return existing[0]
    key = release_key(release_root, allow_create=True)
    review = manifest["independent_review"]
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-release-acceptance",
        "record_id": f"RELEASE-ACCEPTANCE-{len(records) + 1}",
        "release_id": manifest["release_id"],
        "source_commit": manifest["source_commit"],
        "manifest_sha256": manifest["manifest_sha256"],
        "candidate_root_sha256": manifest["candidate_root_sha256"],
        "review_record_id": review["record_id"],
        "review_root_sha256": review["review_root_sha256"],
        "previous_record_hmac_sha256": (
            records[-1]["record_hmac_sha256"] if records else None
        ),
    }
    material["record_hmac_sha256"] = record_hmac(key, material)
    append_jsonl(release_root / ACCEPTANCE_NAME, material)
    return material


def history(release_root: Path) -> list[dict[str, Any]]:
    records = jsonl_records(release_root / HISTORY_NAME, label="Activation history")
    if not records:
        return []
    key = release_key(release_root, allow_create=False)
    previous: str | None = None
    active: str | None = None
    seen_active: set[str] = set()
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "timestamp",
        "action",
        "release_id",
        "previous_release_id",
        "quiescent_boundary_record",
        "quiescent_boundary_root_sha256",
        "post_swap_reload_root_sha256",
        "previous_record_hmac_sha256",
        "record_hmac_sha256",
    }
    for index, value in enumerate(records, start=1):
        material = {
            item: member for item, member in value.items() if item != "record_hmac_sha256"
        }
        action = value.get("action")
        release_id = str(value.get("release_id", ""))
        if (
            set(value) != exact_keys
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("kind") != "software-factory-release-activation"
            or value.get("record_id") != f"ACTIVATION-{index}"
            or value.get("previous_record_hmac_sha256") != previous
            or value.get("record_hmac_sha256") != record_hmac(key, material)
            or action not in {"bootstrap", "activate", "rollback"}
            or value.get("previous_release_id") != active
            or (index == 1 and action != "bootstrap")
            or (index > 1 and action == "bootstrap")
            or (action == "rollback" and release_id not in seen_active)
            or release_id == active
        ):
            raise ReleaseError("Activation history was forged or is semantically invalid")
        bounded_id(release_id, label="activation release ID")
        bounded_id(
            str(value["quiescent_boundary_record"]),
            label="activation quiescent record",
        )
        exact_sha256(
            str(value["quiescent_boundary_root_sha256"]),
            label="activation quiescent root",
        )
        exact_sha256(
            str(value["post_swap_reload_root_sha256"]),
            label="activation reload root",
        )
        if accepted_release_record(release_root, release_id) is None:
            raise ReleaseError("Activation history names an unaccepted release")
        if active:
            seen_active.add(active)
        active = release_id
        previous = str(value["record_hmac_sha256"])
    return records


def make_history_record(
    release_root: Path,
    *,
    action: str,
    release_id: str,
    previous_release_id: str | None,
    quiescent_record: str,
    quiescent_root: str,
    reload_root: str,
) -> dict[str, Any]:
    records = history(release_root)
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-release-activation",
        "record_id": f"ACTIVATION-{len(records) + 1}",
        "timestamp": utc_now(),
        "action": action,
        "release_id": release_id,
        "previous_release_id": previous_release_id,
        "quiescent_boundary_record": quiescent_record,
        "quiescent_boundary_root_sha256": quiescent_root,
        "post_swap_reload_root_sha256": reload_root,
        "previous_record_hmac_sha256": (
            records[-1]["record_hmac_sha256"] if records else None
        ),
    }
    material["record_hmac_sha256"] = record_hmac(
        release_key(release_root, allow_create=False), material
    )
    return material


def tree_projection(path: Path) -> tuple[str, int]:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"Skill tree is missing or symlinked: {path.name}")
    entries: list[dict[str, str]] = []
    for base, directory_names, file_names in os.walk(path, followlinks=False):
        directory_names.sort()
        file_names.sort()
        base_path = Path(base)
        for name in directory_names:
            child = base_path / name
            if child.is_symlink():
                raise ReleaseError(f"Skill tree contains a directory symlink: {child}")
        for name in file_names:
            child = base_path / name
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ReleaseError(f"Skill tree contains a non-regular file: {child}")
            payload = child.read_bytes()
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "mode": "100755" if metadata.st_mode & stat.S_IXUSR else "100644",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    if not entries or not any(item["path"] == "SKILL.md" for item in entries):
        raise ReleaseError(f"Skill tree is incomplete: {path.name}")
    return digest(entries), len(entries)


def git_tree_entries(repo: Path, commit: str) -> list[tuple[str, str, str]]:
    raw = run_git(repo, "ls-tree", "-r", "-z", commit, "--", *SKILLS, binary=True)
    assert isinstance(raw, bytes)
    entries: list[tuple[str, str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            header, raw_path = item.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split(" ")
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ReleaseError("Git skill tree entry is invalid") from exc
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ReleaseError(f"Git skill tree contains a symlink or unsupported entry: {relative}")
        root_name = relative.split("/", 1)[0]
        if root_name not in SKILLS or "/" not in relative:
            raise ReleaseError(f"Git skill entry is outside the exact release set: {relative}")
        entries.append((mode, object_id, relative))
    roots = {path.split("/", 1)[0] for _mode, _object, path in entries}
    if roots != set(SKILLS):
        raise ReleaseError("Git commit does not contain the complete three-skill set")
    return entries


def materialize_commit(repo: Path, commit: str, destination: Path) -> None:
    for mode, object_id, relative in git_tree_entries(repo, commit):
        output = destination / relative
        if destination not in output.parents:
            raise ReleaseError("Git entry escaped the release staging directory")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = run_git(repo, "cat-file", "blob", object_id, binary=True)
        assert isinstance(payload, bytes)
        descriptor = os.open(
            output,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o755 if mode == "100755" else 0o644,
        )
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def canonical_validator() -> tuple[Path, dict[str, str]]:
    validator = (
        Path.home()
        / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
    )
    if validator.is_symlink() or not validator.is_file():
        raise ReleaseError("Canonical Skill Creator validator is missing or symlinked")
    payload = validator.read_bytes()
    return validator.resolve(strict=True), {
        "path": str(validator.resolve(strict=True)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def run_validator(
    validator: Path, validator_identity: Mapping[str, str], skill: Path
) -> dict[str, Any]:
    command = [str(validator), str(skill)]
    if not os.access(validator, os.X_OK):
        python = shutil.which("python3")
        if not python:
            raise ReleaseError("No Python runtime is available for the skill validator")
        command.insert(0, python)
    result = subprocess.run(command, check=False, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode:
        raise ReleaseError(f"Skill validation failed for {skill.name}")
    return {
        "status": "passed",
        "validator_path": validator_identity["path"],
        "validator_sha256": validator_identity["sha256"],
        "output_sha256": hashlib.sha256(output).hexdigest(),
    }


def candidate_material(
    source_commit: str,
    skills: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-skill-release-candidate",
        "source_commit": source_commit,
        "skill_names": list(SKILLS),
        "skills": dict(skills),
        "validation": dict(validation),
    }


def validate_review_evidence(
    path: Path,
    *,
    implementer_id: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    value = load_bounded_json(path, label="Independent review evidence")
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "reviewer_id",
        "implementer_id",
        "disposition",
        "source_commit",
        "candidate_root_sha256",
        "reviewed_at",
        "evidence",
        "review_root_sha256",
    }
    material = {
        item: member for item, member in value.items() if item != "review_root_sha256"
    }
    reviewer_id = bounded_id(str(value.get("reviewer_id", "")), label="reviewer ID")
    if (
        set(value) != exact_keys
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind") != "software-factory-skill-release-review"
        or value.get("disposition") != "accepted"
        or value.get("source_commit") != candidate["source_commit"]
        or value.get("candidate_root_sha256") != digest(candidate)
        or value.get("implementer_id") != implementer_id
        or reviewer_id == implementer_id
        or value.get("review_root_sha256") != digest(material)
    ):
        raise ReleaseError("Independent review does not bind the exact release candidate")
    bounded_id(str(value.get("record_id", "")), label="review record ID")
    exact_sha256(
        str(value.get("candidate_root_sha256", "")), label="review candidate root"
    )
    evidence = value.get("evidence")
    if (
        not isinstance(value.get("reviewed_at"), str)
        or not value["reviewed_at"]
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or not all(isinstance(item, str) and 0 < len(item) <= 200 for item in evidence)
    ):
        raise ReleaseError("Independent review evidence is incomplete")
    return value


def current_release_id(release_root: Path) -> str | None:
    pointer = release_root / "current"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    if not pointer.is_symlink():
        raise ReleaseError("Current release pointer is not a symlink")
    target = os.readlink(pointer)
    expected_prefix = "releases/"
    if not target.startswith(expected_prefix) or "/" in target[len(expected_prefix) :]:
        raise ReleaseError("Current release pointer has an invalid target")
    release_id = target[len(expected_prefix) :]
    resolved = pointer.resolve(strict=True)
    expected = (release_root / "releases" / release_id).resolve(strict=True)
    if resolved != expected or expected.parent != (release_root / "releases").resolve():
        raise ReleaseError("Current release pointer escapes the release root")
    return release_id


def release_tree_is_sealed(release: Path) -> bool:
    for base, directory_names, file_names in os.walk(release, followlinks=False):
        base_path = Path(base)
        if base_path.stat().st_mode & 0o222:
            return False
        for name in directory_names:
            child = base_path / name
            if child.is_symlink() or child.stat().st_mode & 0o222:
                return False
        for name in file_names:
            child = base_path / name
            if child.is_symlink() or child.stat().st_mode & 0o222:
                return False
    return True


def read_manifest(
    release_root: Path, release_id: str, *, require_acceptance: bool = True
) -> dict[str, Any]:
    bounded_id(release_id, label="release ID")
    releases = release_root / "releases"
    if releases.is_symlink() or not releases.is_dir():
        raise ReleaseError("Canonical releases directory is missing or symlinked")
    release = releases / release_id
    if release.is_symlink() or not release.is_dir() or release.resolve().parent != releases.resolve():
        raise ReleaseError("Release directory is missing or escapes the release root")
    expected_names = set(SKILLS) | {MANIFEST_NAME}
    if {item.name for item in release.iterdir()} != expected_names:
        raise ReleaseError("Release set is partial or contains unexpected members")
    manifest_path = release / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ReleaseError("Release manifest is missing or symlinked")
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except json.JSONDecodeError as exc:
        raise ReleaseError("Release manifest is invalid JSON") from exc
    if not isinstance(manifest, dict):
        raise ReleaseError("Release manifest must be an object")
    exact_keys = {
        "schema_version",
        "kind",
        "release_id",
        "created_at",
        "source_commit",
        "candidate_root_sha256",
        "skill_names",
        "skills",
        "validation",
        "independent_review",
        "previous_active_release_id",
        "manifest_sha256",
    }
    material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (
        set(manifest) != exact_keys
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("kind") != "software-factory-skill-release"
        or manifest.get("release_id") != release_id
        or manifest.get("manifest_sha256") != digest(material)
        or list(manifest.get("skill_names", [])) != list(SKILLS)
        or not release_tree_is_sealed(release)
    ):
        raise ReleaseError("Release manifest identity or digest is invalid")
    source_commit = exact_git_commit(str(manifest.get("source_commit", "")))
    review = manifest.get("independent_review")
    if not isinstance(review, dict):
        raise ReleaseError("Release has no independent review evidence")
    review_material = {
        item: member for item, member in review.items() if item != "review_root_sha256"
    }
    if review.get("review_root_sha256") != digest(review_material):
        raise ReleaseError("Release review evidence root is invalid")
    bounded_id(str(review.get("reviewer_id", "")), label="reviewer ID")
    bounded_id(str(review.get("implementer_id", "")), label="implementer ID")
    bounded_id(str(review.get("record_id", "")), label="review record ID")
    exact_sha256(str(review.get("review_root_sha256", "")), label="review root")
    skills = manifest.get("skills")
    if not isinstance(skills, dict) or set(skills) != set(SKILLS):
        raise ReleaseError("Release manifest does not describe exactly three skills")
    validation = manifest.get("validation")
    if not isinstance(validation, dict) or set(validation) != set(SKILLS):
        raise ReleaseError("Release manifest has no exact validator evidence")
    for name in SKILLS:
        root, count = tree_projection(release / name)
        if skills[name] != {"content_root_sha256": root, "file_count": count}:
            raise ReleaseError(f"Release skill content drifted: {name}")
        validator_record = validation[name]
        if (
            not isinstance(validator_record, dict)
            or set(validator_record)
            != {"status", "validator_path", "validator_sha256", "output_sha256"}
            or validator_record.get("status") != "passed"
        ):
            raise ReleaseError("Release validator evidence is invalid")
        exact_sha256(
            str(validator_record.get("validator_sha256", "")),
            label="validator content root",
        )
        exact_sha256(
            str(validator_record.get("output_sha256", "")),
            label="validator output root",
        )
    candidate = candidate_material(source_commit, skills, validation)
    candidate_root = digest(candidate)
    if (
        manifest.get("candidate_root_sha256") != candidate_root
        or review.get("source_commit") != source_commit
        or review.get("candidate_root_sha256") != candidate_root
    ):
        raise ReleaseError("Release candidate and review binding differ")
    expected_release_id = (
        f"{source_commit[:12]}-"
        f"{digest({'candidate_root_sha256': candidate_root, 'review_root_sha256': review['review_root_sha256']})[:12]}"
    )
    if release_id != expected_release_id:
        raise ReleaseError("Release ID does not match its accepted content projection")
    if require_acceptance:
        accepted = accepted_release_record(release_root, release_id)
        if (
            accepted is None
            or accepted["source_commit"] != source_commit
            or accepted["manifest_sha256"] != manifest["manifest_sha256"]
            or accepted["candidate_root_sha256"] != candidate_root
            or accepted["review_record_id"] != review["record_id"]
            or accepted["review_root_sha256"] != review["review_root_sha256"]
        ):
            raise ReleaseError("Release is not bound to canonical external acceptance")
    return manifest


def verified_source(repo: Path, source_commit: str) -> None:
    resolved = run_git(repo, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if resolved != source_commit:
        raise ReleaseError("Source commit does not resolve exactly")
    if run_git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseError("Source repository is dirty")


def build_candidate(repo: Path, source_commit: str, destination: Path) -> dict[str, Any]:
    validator, validator_identity = canonical_validator()
    materialize_commit(repo, source_commit, destination)
    skills: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    for name in SKILLS:
        validation[name] = run_validator(
            validator, validator_identity, destination / name
        )
        root, count = tree_projection(destination / name)
        skills[name] = {"content_root_sha256": root, "file_count": count}
    return candidate_material(source_commit, skills, validation)


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def review_request(args: argparse.Namespace) -> dict[str, Any]:
    repo = ensure_directory(Path(args.repo), label="source repository", create=False)
    source_commit = exact_git_commit(args.source_commit)
    verified_source(repo, source_commit)
    with tempfile.TemporaryDirectory(prefix="software-factory-review-request-") as raw:
        candidate = build_candidate(repo, source_commit, Path(raw))
    return {**candidate, "candidate_root_sha256": digest(candidate)}


def stage_release(args: argparse.Namespace) -> dict[str, Any]:
    repo = ensure_directory(Path(args.repo), label="source repository", create=False)
    release_root = ensure_directory(Path(args.release_root), label="release root")
    releases = ensure_directory(release_root / "releases", label="release directory")
    source_commit = exact_git_commit(args.source_commit)
    verified_source(repo, source_commit)
    implementer_id = bounded_id(args.implementer_id, label="implementer ID")
    review_path = Path(args.review_evidence).resolve(strict=True)
    if path_is_within(review_path, repo) or path_is_within(review_path, release_root):
        raise ReleaseError("Independent review evidence must remain externally owned")
    temporary = releases / f".stage-{os.getpid()}-{secrets.token_hex(6)}"
    with release_lock(release_root):
        try:
            temporary.mkdir(mode=0o700)
            candidate = build_candidate(repo, source_commit, temporary)
            review = validate_review_evidence(
                review_path,
                implementer_id=implementer_id,
                candidate=candidate,
            )
            candidate_root = digest(candidate)
            release_id = (
                f"{source_commit[:12]}-"
                f"{digest({'candidate_root_sha256': candidate_root, 'review_root_sha256': review['review_root_sha256']})[:12]}"
            )
            destination = releases / release_id
            manifest: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "kind": "software-factory-skill-release",
                "release_id": release_id,
                "created_at": utc_now(),
                "source_commit": source_commit,
                "candidate_root_sha256": candidate_root,
                "skill_names": list(SKILLS),
                "skills": candidate["skills"],
                "validation": candidate["validation"],
                "independent_review": review,
                "previous_active_release_id": current_release_id(release_root),
            }
            manifest["manifest_sha256"] = digest(manifest)
            atomic_json(temporary / MANIFEST_NAME, manifest)
            fsync_tree_directories(temporary)
            if destination.exists():
                existing = read_manifest(
                    release_root, release_id, require_acceptance=False
                )
                if any(
                    existing.get(key) != manifest.get(key)
                    for key in (
                        "source_commit",
                        "skill_names",
                        "skills",
                        "independent_review",
                    )
                ):
                    raise ReleaseError("Existing release ID has different content")
                shutil.rmtree(temporary)
                append_acceptance(release_root, existing)
                return {"stage": "existing", **existing}
            seal_release_tree(temporary)
            fsync_tree_directories(temporary)
            os.replace(temporary, destination)
            fsync_directory(releases)
            read_manifest(release_root, release_id, require_acceptance=False)
            append_acceptance(release_root, manifest)
            return {"stage": "created", **manifest}
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise


def desired_link(release_root: Path, name: str) -> str:
    return str(release_root / "current" / name)


def installed_link_state(install_root: Path, release_root: Path) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name in SKILLS:
        path = install_root / name
        target = os.readlink(path) if path.is_symlink() else None
        state[name] = {
            "path": str(path),
            "target": target,
            "stable": target == desired_link(release_root, name),
            "exists": path.exists() or path.is_symlink(),
        }
    return state


def swap_pointer(release_root: Path, release_id: str | None) -> None:
    pointer = release_root / "current"
    if release_id is None:
        if pointer.exists() or pointer.is_symlink():
            pointer.unlink()
            fsync_directory(release_root)
        return
    read_manifest(release_root, release_id)
    temporary = release_root / f".current-{os.getpid()}-{secrets.token_hex(6)}"
    try:
        os.symlink(f"releases/{release_id}", temporary)
        fsync_directory(release_root)
        os.replace(temporary, pointer)
        fsync_directory(release_root)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def verify_bootstrap_source(
    install_root: Path,
    bootstrap_source_root: Path | None,
    manifest: Mapping[str, Any],
) -> list[str | None]:
    originals: list[str | None] = []
    states = []
    for name in SKILLS:
        path = install_root / name
        states.append("absent" if not (path.exists() or path.is_symlink()) else "present")
        if path.exists() or path.is_symlink():
            if not path.is_symlink():
                raise ReleaseError("Existing skill discovery path is not a symlink")
            originals.append(os.readlink(path))
        else:
            originals.append(None)
    if len(set(states)) != 1:
        raise ReleaseError("Partial installed skill set cannot be bootstrapped")
    if states[0] == "absent":
        if bootstrap_source_root is not None:
            raise ReleaseError("Bootstrap source root is invalid for an empty install")
        return originals
    if bootstrap_source_root is None:
        raise ReleaseError("Existing installation requires an exact bootstrap source root")
    source = ensure_directory(
        bootstrap_source_root, label="bootstrap source root", create=False
    )
    for name in SKILLS:
        path = install_root / name
        if path.resolve(strict=True) != (source / name).resolve(strict=True):
            raise ReleaseError("Installed skill target differs from bootstrap source root")
        root, count = tree_projection(path.resolve(strict=True))
        if manifest["skills"][name] != {
            "content_root_sha256": root,
            "file_count": count,
        }:
            raise ReleaseError("Bootstrap source content differs from staged baseline")
    return originals


def replace_link(path: Path, target: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}")
    try:
        os.symlink(target, temporary)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def restore_links(install_root: Path, originals: Sequence[str | None]) -> None:
    failures: list[str] = []
    for name, target in zip(SKILLS, originals):
        path = install_root / name
        restored = False
        for _attempt in range(3):
            try:
                if target is None:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                        fsync_directory(install_root)
                else:
                    replace_link(path, target)
                restored = (
                    (target is None and not (path.exists() or path.is_symlink()))
                    or (target is not None and path.is_symlink() and os.readlink(path) == target)
                )
                if restored:
                    break
            except OSError:
                continue
        if not restored:
            failures.append(name)
    if failures:
        raise ReleaseError(
            "Bootstrap recovery could not restore discovery links: "
            + ", ".join(failures)
        )


def bootstrap_links(
    install_root: Path,
    release_root: Path,
    originals: Sequence[str | None],
    *,
    fail_after: int | None = None,
) -> None:
    for index, name in enumerate(SKILLS, start=1):
        replace_link(install_root / name, desired_link(release_root, name))
        if fail_after == index:
            raise ReleaseError("Injected bootstrap interruption")


def verify_installed(
    release_root: Path, install_root: Path, expected_release: str
) -> dict[str, Any]:
    manifest = read_manifest(release_root, expected_release)
    if current_release_id(release_root) != expected_release:
        raise ReleaseError("Current pointer differs from expected release")
    resolved_roots: dict[str, str] = {}
    for name in SKILLS:
        link = install_root / name
        if not link.is_symlink() or os.readlink(link) != desired_link(release_root, name):
            raise ReleaseError("Installed discovery links are not the stable release links")
        resolved = link.resolve(strict=True)
        expected = (release_root / "releases" / expected_release / name).resolve()
        if resolved != expected:
            raise ReleaseError("Installed skill resolves outside the active release")
        root, _count = tree_projection(resolved)
        if root != manifest["skills"][name]["content_root_sha256"]:
            raise ReleaseError("Installed skill root differs from the release manifest")
        resolved_roots[name] = root
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-post-swap-resolution",
        "release_id": expected_release,
        "installed_roots": resolved_roots,
    }
    return {**material, "verification_root_sha256": digest(material)}


def child_reload_verify(
    release_root: Path, install_root: Path, expected_release: str
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--release-root",
            str(release_root),
            "--install-root",
            str(install_root),
            "verify-installed",
            "--expected-release",
            expected_release,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ReleaseError("Fresh-process post-swap resolution verification failed")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError("Post-swap verifier returned invalid evidence") from exc
    if value.get("release_id") != expected_release:
        raise ReleaseError("Post-swap verifier returned stale release evidence")
    exact_sha256(
        str(value.get("verification_root_sha256", "")),
        label="post-swap verification root",
    )
    return value


def validate_quiescent_evidence(
    path: Path,
    *,
    release_root: Path,
    operation: str,
    release_id: str,
    previous_release_id: str | None,
) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if path_is_within(resolved, release_root):
        raise ReleaseError("Quiescent-boundary evidence must remain externally owned")
    value = load_bounded_json(resolved, label="Quiescent-boundary evidence", maximum=16384)
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "operator_id",
        "operation",
        "release_id",
        "previous_active_release_id",
        "observed_at",
        "no_concurrent_skill_resolutions",
        "evidence",
        "evidence_root_sha256",
    }
    material = {
        item: member for item, member in value.items() if item != "evidence_root_sha256"
    }
    if (
        set(value) != exact_keys
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind") != "software-factory-quiescent-boundary"
        or value.get("operation") != operation
        or value.get("release_id") != release_id
        or value.get("previous_active_release_id") != previous_release_id
        or value.get("no_concurrent_skill_resolutions") is not True
        or value.get("evidence_root_sha256") != digest(material)
    ):
        raise ReleaseError("Quiescent-boundary evidence is stale or does not bind cutover")
    bounded_id(str(value.get("record_id", "")), label="quiescent-boundary record")
    bounded_id(str(value.get("operator_id", "")), label="quiescent-boundary operator")
    evidence = value.get("evidence")
    if (
        not isinstance(value.get("observed_at"), str)
        or not value["observed_at"]
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 12
        or not all(isinstance(item, str) and 0 < len(item) <= 200 for item in evidence)
    ):
        raise ReleaseError("Quiescent-boundary evidence is incomplete")
    return value


def activate_release(
    args: argparse.Namespace,
    *,
    action: str = "activate",
) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    release_id = bounded_id(args.release_id, label="release ID")
    with release_lock(release_root):
        read_manifest(release_root, release_id)
        prior = current_release_id(release_root)
        prior_history = history(release_root)
        history_active = (
            str(prior_history[-1]["release_id"]) if prior_history else None
        )
        if history_active != prior:
            raise ReleaseError("Current pointer and activation history differ")
        quiescent = validate_quiescent_evidence(
            Path(args.quiescent_evidence),
            release_root=release_root,
            operation=action,
            release_id=release_id,
            previous_release_id=prior,
        )
        if prior == release_id:
            raise ReleaseError("Requested release is already active")
        prior_links = installed_link_state(install_root, release_root)
        stable_count = sum(bool(item["stable"]) for item in prior_links.values())
        if stable_count == 0:
            raise ReleaseError("Stable discovery links are not bootstrapped")
        if stable_count != len(SKILLS):
            raise ReleaseError("Installed stable discovery link set is partial")
        pointer_swapped = False
        try:
            swap_pointer(release_root, release_id)
            pointer_swapped = True
            reload_evidence = child_reload_verify(
                release_root, install_root, release_id
            )
            installed = verify_installed(release_root, install_root, release_id)
            record = make_history_record(
                release_root,
                action=action,
                release_id=release_id,
                previous_release_id=prior,
                quiescent_record=quiescent["record_id"],
                quiescent_root=quiescent["evidence_root_sha256"],
                reload_root=reload_evidence["verification_root_sha256"],
            )
            append_history(release_root, record)
            return {
                "action": action,
                "active_release_id": release_id,
                "previous_release_id": prior,
                "installed": installed,
                "activation_record": record,
            }
        except Exception:
            if pointer_swapped:
                swap_pointer(release_root, prior)
            raise


def bootstrap_release(
    args: argparse.Namespace,
    *,
    fail_after_bootstrap_links: int | None = None,
) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    release_id = bounded_id(args.release_id, label="release ID")
    source_root = Path(args.legacy_source_root) if args.legacy_source_root else None
    with release_lock(release_root):
        manifest = read_manifest(release_root, release_id)
        if current_release_id(release_root) is not None:
            raise ReleaseError("Release owner is already bootstrapped")
        if history(release_root):
            raise ReleaseError("Activation history exists without a current release")
        quiescent = validate_quiescent_evidence(
            Path(args.quiescent_evidence),
            release_root=release_root,
            operation="bootstrap",
            release_id=release_id,
            previous_release_id=None,
        )
        links = installed_link_state(install_root, release_root)
        if any(item["stable"] for item in links.values()):
            raise ReleaseError("Installed stable discovery link set is partial")
        originals = verify_bootstrap_source(install_root, source_root, manifest)
        pointer_swapped = False
        try:
            swap_pointer(release_root, release_id)
            pointer_swapped = True
            bootstrap_links(
                install_root,
                release_root,
                originals,
                fail_after=fail_after_bootstrap_links,
            )
            reload_evidence = child_reload_verify(
                release_root, install_root, release_id
            )
            installed = verify_installed(release_root, install_root, release_id)
            record = make_history_record(
                release_root,
                action="bootstrap",
                release_id=release_id,
                previous_release_id=None,
                quiescent_record=quiescent["record_id"],
                quiescent_root=quiescent["evidence_root_sha256"],
                reload_root=reload_evidence["verification_root_sha256"],
            )
            append_history(release_root, record)
            return {
                "action": "bootstrap",
                "active_release_id": release_id,
                "previous_release_id": None,
                "installed": installed,
                "activation_record": record,
            }
        except Exception:
            recovery_errors: list[str] = []
            if pointer_swapped:
                try:
                    swap_pointer(release_root, None)
                except Exception as exc:
                    recovery_errors.append(f"pointer: {exc}")
            try:
                restore_links(install_root, originals)
            except Exception as exc:
                recovery_errors.append(f"links: {exc}")
            if recovery_errors:
                raise ReleaseError(
                    "Bootstrap recovery was incomplete: " + "; ".join(recovery_errors)
                )
            raise


def rollback_release(args: argparse.Namespace) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    records = history(release_root)
    current = current_release_id(release_root)
    prior_ids = [
        str(record["release_id"])
        for record in records
        if record.get("release_id") != current
    ]
    if args.release_id:
        selected = bounded_id(args.release_id, label="rollback release ID")
        if selected not in prior_ids:
            raise ReleaseError("Rollback target is not a prior accepted active release")
    else:
        selected = prior_ids[-1] if prior_ids else ""
        if not selected:
            raise ReleaseError("No prior accepted active release is available")
    args.release_id = selected
    return activate_release(args, action="rollback")


def status(args: argparse.Namespace) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    with release_lock(release_root):
        active = current_release_id(release_root)
        manifest = read_manifest(release_root, active) if active else None
        records = history(release_root)
        history_active = str(records[-1]["release_id"]) if records else None
        if history_active != active:
            raise ReleaseError("Current pointer and activation history differ")
        installed = installed_link_state(install_root, release_root)
        result: dict[str, Any] = {
            "active_release_id": active,
            "source_commit": manifest.get("source_commit") if manifest else None,
            "skills": manifest.get("skills") if manifest else None,
            "installed_links": installed,
            "installed_complete": bool(active)
            and all(item["stable"] for item in installed.values()),
            "activation_history_records": len(records),
        }
        if active and result["installed_complete"]:
            result["current_verification"] = verify_installed(
                release_root, install_root, active
            )
        return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--release-root",
        default=str(Path.home() / ".codex/software-factory-releases"),
    )
    value.add_argument(
        "--install-root", default=str(Path.home() / ".codex/skills")
    )
    subcommands = value.add_subparsers(dest="command", required=True)

    request = subcommands.add_parser(
        "review-request", help="build the exact read-only release review projection"
    )
    request.add_argument("--repo", required=True)
    request.add_argument("--source-commit", required=True)
    request.set_defaults(func=review_request)

    stage = subcommands.add_parser("stage", help="stage one exact reviewed commit")
    stage.add_argument("--repo", required=True)
    stage.add_argument("--source-commit", required=True)
    stage.add_argument("--implementer-id", required=True)
    stage.add_argument("--review-evidence", required=True)
    stage.set_defaults(func=stage_release)

    activate = subcommands.add_parser("activate", help="activate one staged release")
    activate.add_argument("release_id")
    activate.add_argument("--quiescent-evidence", required=True)
    activate.set_defaults(func=activate_release)

    bootstrap = subcommands.add_parser(
        "bootstrap", help="install stable links for one content-identical baseline"
    )
    bootstrap.add_argument("release_id")
    bootstrap.add_argument("--quiescent-evidence", required=True)
    bootstrap.add_argument("--legacy-source-root")
    bootstrap.set_defaults(func=bootstrap_release)

    rollback = subcommands.add_parser("rollback", help="restore a prior accepted release")
    rollback.add_argument("release_id", nargs="?")
    rollback.add_argument("--quiescent-evidence", required=True)
    rollback.set_defaults(func=rollback_release)

    inspect = subcommands.add_parser("status", help="report exact active roots")
    inspect.set_defaults(func=status)

    verify = subcommands.add_parser(
        "verify-installed", help=argparse.SUPPRESS
    )
    verify.add_argument("--expected-release", required=True)
    verify.set_defaults(
        func=lambda args: verify_installed(
            ensure_directory(Path(args.release_root), label="release root"),
            ensure_directory(Path(args.install_root), label="skill install root"),
            args.expected_release,
        )
    )
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.func(args)
    except (OSError, ReleaseError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
