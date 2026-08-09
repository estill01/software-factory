#!/usr/bin/env python3
"""Stage and atomically select accepted Software Factory skill releases."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
from typing import Any, Iterator, Mapping, Sequence


SKILLS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
)
MANIFEST_NAME = "release-manifest.json"
HISTORY_NAME = "activation-history.jsonl"
LOCK_NAME = ".release.lock"
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


def append_history(release_root: Path, record: Mapping[str, Any]) -> None:
    path = release_root / HISTORY_NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, canonical(record) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(release_root)


def history(release_root: Path) -> list[dict[str, Any]]:
    path = release_root / HISTORY_NAME
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ReleaseError("Activation history is not a canonical regular file")
    records: list[dict[str, Any]] = []
    previous: str | None = None
    for index, line in enumerate(path.read_bytes().splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError("Activation history is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ReleaseError("Activation history record must be an object")
        material = {key: item for key, item in value.items() if key != "record_sha256"}
        if (
            value.get("record_id") != f"ACTIVATION-{index}"
            or value.get("previous_record_sha256") != previous
            or value.get("record_sha256") != digest(material)
        ):
            raise ReleaseError("Activation history was rewritten or reordered")
        previous = value["record_sha256"]
        records.append(value)
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
        "record_id": f"ACTIVATION-{len(records) + 1}",
        "timestamp": utc_now(),
        "action": action,
        "release_id": release_id,
        "previous_release_id": previous_release_id,
        "quiescent_boundary_record": quiescent_record,
        "quiescent_boundary_root_sha256": quiescent_root,
        "post_swap_reload_root_sha256": reload_root,
        "previous_record_sha256": (
            records[-1]["record_sha256"] if records else None
        ),
    }
    material["record_sha256"] = digest(material)
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


def run_validator(validator: Path, skill: Path) -> dict[str, Any]:
    if validator.is_symlink() or not validator.is_file():
        raise ReleaseError("Skill validator must be a real regular file")
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
        "validator": validator.name,
        "output_sha256": hashlib.sha256(output).hexdigest(),
    }


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


def read_manifest(release_root: Path, release_id: str) -> dict[str, Any]:
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
    material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("kind") != "software-factory-skill-release"
        or manifest.get("release_id") != release_id
        or manifest.get("manifest_sha256") != digest(material)
        or list(manifest.get("skill_names", [])) != list(SKILLS)
    ):
        raise ReleaseError("Release manifest identity or digest is invalid")
    review = manifest.get("independent_review")
    if not isinstance(review, dict):
        raise ReleaseError("Release has no independent review evidence")
    bounded_id(str(review.get("reviewer_id", "")), label="reviewer ID")
    bounded_id(str(review.get("record_id", "")), label="review record ID")
    exact_sha256(str(review.get("root_sha256", "")), label="review root")
    skills = manifest.get("skills")
    if not isinstance(skills, dict) or set(skills) != set(SKILLS):
        raise ReleaseError("Release manifest does not describe exactly three skills")
    for name in SKILLS:
        root, count = tree_projection(release / name)
        if skills[name] != {"content_root_sha256": root, "file_count": count}:
            raise ReleaseError(f"Release skill content drifted: {name}")
    return manifest


def default_validator() -> Path:
    return Path(
        os.environ.get(
            "SOFTWARE_FACTORY_SKILL_VALIDATOR",
            str(
                Path.home()
                / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
            ),
        )
    )


def stage_release(args: argparse.Namespace) -> dict[str, Any]:
    repo = ensure_directory(Path(args.repo), label="source repository", create=False)
    release_root = ensure_directory(Path(args.release_root), label="release root")
    releases = ensure_directory(release_root / "releases", label="release directory")
    source_commit = exact_git_commit(args.source_commit)
    resolved = run_git(repo, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if resolved != source_commit:
        raise ReleaseError("Source commit does not resolve exactly")
    if run_git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseError("Source repository is dirty")
    reviewer_id = bounded_id(args.reviewer_id, label="reviewer ID")
    review_record = bounded_id(args.review_record, label="review record ID")
    review_root = exact_sha256(args.review_root, label="review root")
    validator = Path(args.validator).resolve(strict=True)
    temporary = releases / f".stage-{os.getpid()}-{secrets.token_hex(6)}"
    with release_lock(release_root):
        try:
            temporary.mkdir(mode=0o700)
            materialize_commit(repo, source_commit, temporary)
            skills: dict[str, Any] = {}
            validation: dict[str, Any] = {}
            for name in SKILLS:
                validation[name] = run_validator(validator, temporary / name)
                root, count = tree_projection(temporary / name)
                skills[name] = {"content_root_sha256": root, "file_count": count}
            release_material = {
                "source_commit": source_commit,
                "skills": skills,
                "independent_review": {
                    "reviewer_id": reviewer_id,
                    "record_id": review_record,
                    "root_sha256": review_root,
                },
            }
            release_id = f"{source_commit[:12]}-{digest(release_material)[:12]}"
            destination = releases / release_id
            manifest: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "kind": "software-factory-skill-release",
                "release_id": release_id,
                "created_at": utc_now(),
                "source_commit": source_commit,
                "skill_names": list(SKILLS),
                "skills": skills,
                "validation": validation,
                "independent_review": release_material["independent_review"],
                "previous_active_release_id": current_release_id(release_root),
            }
            manifest["manifest_sha256"] = digest(manifest)
            atomic_json(temporary / MANIFEST_NAME, manifest)
            fsync_tree_directories(temporary)
            if destination.exists():
                existing = read_manifest(release_root, release_id)
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
                return {"stage": "existing", **existing}
            seal_release_tree(temporary)
            fsync_tree_directories(temporary)
            os.replace(temporary, destination)
            fsync_directory(releases)
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
    for name, target in zip(SKILLS, originals):
        path = install_root / name
        if target is None:
            if path.exists() or path.is_symlink():
                path.unlink()
                fsync_directory(install_root)
        else:
            replace_link(path, target)


def bootstrap_links(
    install_root: Path,
    release_root: Path,
    originals: Sequence[str | None],
    *,
    fail_after: int | None = None,
) -> None:
    try:
        for index, name in enumerate(SKILLS, start=1):
            replace_link(install_root / name, desired_link(release_root, name))
            if fail_after == index:
                raise ReleaseError("Injected bootstrap interruption")
    except Exception:
        restore_links(install_root, originals)
        raise


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


def activate_release(
    args: argparse.Namespace,
    *,
    action: str = "activate",
) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    release_id = bounded_id(args.release_id, label="release ID")
    quiescent_record = bounded_id(
        args.quiescent_boundary_record, label="quiescent-boundary record"
    )
    quiescent_root = exact_sha256(
        args.quiescent_boundary_root, label="quiescent-boundary root"
    )
    with release_lock(release_root):
        read_manifest(release_root, release_id)
        prior = current_release_id(release_root)
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
                quiescent_record=quiescent_record,
                quiescent_root=quiescent_root,
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
    quiescent_record = bounded_id(
        args.quiescent_boundary_record, label="quiescent-boundary record"
    )
    quiescent_root = exact_sha256(
        args.quiescent_boundary_root, label="quiescent-boundary root"
    )
    source_root = Path(args.legacy_source_root) if args.legacy_source_root else None
    with release_lock(release_root):
        manifest = read_manifest(release_root, release_id)
        if current_release_id(release_root) is not None:
            raise ReleaseError("Release owner is already bootstrapped")
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
                quiescent_record=quiescent_record,
                quiescent_root=quiescent_root,
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
            restore_links(install_root, originals)
            if pointer_swapped:
                swap_pointer(release_root, None)
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
        installed = installed_link_state(install_root, release_root)
        result: dict[str, Any] = {
            "active_release_id": active,
            "source_commit": manifest.get("source_commit") if manifest else None,
            "skills": manifest.get("skills") if manifest else None,
            "installed_links": installed,
            "installed_complete": bool(active)
            and all(item["stable"] for item in installed.values()),
            "activation_history_records": len(history(release_root)),
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

    stage = subcommands.add_parser("stage", help="stage one exact reviewed commit")
    stage.add_argument("--repo", required=True)
    stage.add_argument("--source-commit", required=True)
    stage.add_argument("--reviewer-id", required=True)
    stage.add_argument("--review-record", required=True)
    stage.add_argument("--review-root", required=True)
    stage.add_argument("--validator", default=str(default_validator()))
    stage.set_defaults(func=stage_release)

    activate = subcommands.add_parser("activate", help="activate one staged release")
    activate.add_argument("release_id")
    activate.add_argument("--quiescent-boundary-record", required=True)
    activate.add_argument("--quiescent-boundary-root", required=True)
    activate.set_defaults(func=activate_release)

    bootstrap = subcommands.add_parser(
        "bootstrap", help="install stable links for one content-identical baseline"
    )
    bootstrap.add_argument("release_id")
    bootstrap.add_argument("--quiescent-boundary-record", required=True)
    bootstrap.add_argument("--quiescent-boundary-root", required=True)
    bootstrap.add_argument("--legacy-source-root")
    bootstrap.set_defaults(func=bootstrap_release)

    rollback = subcommands.add_parser("rollback", help="restore a prior accepted release")
    rollback.add_argument("release_id", nargs="?")
    rollback.add_argument("--quiescent-boundary-record", required=True)
    rollback.add_argument("--quiescent-boundary-root", required=True)
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
