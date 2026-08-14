#!/usr/bin/env python3
"""Deterministic read-only inventory and planning for repository reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_OWNER_SNAPSHOT_BYTES = 1024 * 1024
GIT_OID = re.compile(r"^[0-9a-f]{40,64}$")
RUN_ID = re.compile(r"^cleanup-[0-9a-f]{24}$")


class CleanupError(RuntimeError):
    """Fail-closed cleanup input or evidence error."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(argv: list[str], cwd: Path, *, timeout: int = 30) -> bytes:
    environment = os.environ.copy()
    environment.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"})
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CleanupError(f"command unavailable: {argv[0]}") from exc
    if completed.returncode != 0:
        raise CleanupError(f"command failed ({completed.returncode}): {argv[0]}")
    return completed.stdout


def git(repo: Path, *args: str, timeout: int = 30) -> bytes:
    return run_command(["git", *args], repo, timeout=timeout)


def normalized_absolute(raw: str, *, must_exist: bool = True) -> Path:
    lexical = Path(raw)
    if not lexical.is_absolute():
        raise CleanupError("path must be absolute")
    normalized = os.path.normpath(raw)
    if normalized != raw or raw == "/":
        raise CleanupError("path must be canonical and narrower than root")
    lexical = Path(raw)
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CleanupError("symlink or substituted path is not allowed")
    try:
        resolved = lexical.resolve(strict=must_exist)
    except OSError as exc:
        raise CleanupError("path is unavailable") from exc
    if resolved != lexical:
        raise CleanupError("symlink or substituted path is not allowed")
    return resolved


def resolve_repository(raw: str) -> tuple[Path, Path]:
    repo = normalized_absolute(raw)
    if repo == Path("/") or not repo.is_dir():
        raise CleanupError("repository path is not a directory")
    top = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != repo:
        raise CleanupError("repository must be its canonical top level")
    common_raw = git(repo, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common_raw)
    if not common.is_absolute():
        common = repo / common
    common_lexical = Path(os.path.normpath(str(common)))
    common = common_lexical.resolve(strict=True)
    if common != common_lexical or not common.is_dir() or common == Path("/"):
        raise CleanupError("unsafe Git common directory")
    return repo, common


def git_oid(repo: Path, ref: str, *, missing_ok: bool = False) -> str | None:
    try:
        oid = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    except CleanupError:
        if missing_ok:
            return None
        raise
    if not GIT_OID.fullmatch(oid):
        raise CleanupError("Git returned a malformed object ID")
    return oid


def parse_worktrees(repo: Path) -> list[dict[str, Any]]:
    output = git(repo, "worktree", "list", "--porcelain").decode(
        "utf-8", errors="surrogateescape"
    )
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in output.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"detached", "locked", "prunable", "bare"}:
            current[key] = value or True
        else:
            current[key] = value
    for record in records:
        path = normalized_absolute(str(record["worktree"]))
        record["worktree"] = str(path)
        head = str(record.get("HEAD", ""))
        if not GIT_OID.fullmatch(head):
            raise CleanupError("worktree has a malformed HEAD")
    return sorted(records, key=lambda item: str(item["worktree"]))


def safe_content_root(worktree: Path, relative: str) -> str:
    """Hash an untracked/ignored path without copying its bytes into evidence."""
    candidate = worktree / relative.rstrip("/")
    lexical = Path(os.path.normpath(str(candidate)))
    if lexical != candidate or worktree != lexical and worktree not in lexical.parents:
        raise CleanupError("status path escapes its worktree")
    if not candidate.exists() and not candidate.is_symlink():
        return sha256({"kind": "missing", "path": relative})
    entries: list[dict[str, Any]] = []
    paths = [candidate]
    if candidate.is_dir() and not candidate.is_symlink():
        paths.extend(sorted(candidate.rglob("*"), key=lambda item: str(item)))
    for path in paths:
        relative_path = str(path.relative_to(worktree))
        stat = path.lstat()
        if path.is_symlink():
            payload_root = sha256(os.readlink(path).encode("utf-8", "surrogateescape"))
            kind = "symlink"
        elif path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            payload_root = digest.hexdigest()
            kind = "file"
        elif path.is_dir():
            payload_root = sha256(b"")
            kind = "directory"
        else:
            payload_root = sha256(b"")
            kind = "special"
        entries.append(
            {
                "kind": kind,
                "mode": stat.st_mode & 0o777777,
                "path": relative_path,
                "payload_root": payload_root,
            }
        )
    return sha256(entries)


def parse_status(
    worktree: Path, *, include_ignored: bool = False
) -> list[dict[str, str]]:
    argv = [
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ]
    if include_ignored:
        argv.append("--ignored=matching")
    raw = git(
        worktree,
        *argv,
    )
    tokens = raw.decode("utf-8", errors="surrogateescape").split("\0")
    entries: list[dict[str, str]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4:
            raise CleanupError("malformed Git status entry")
        code = token[:2]
        path = token[3:]
        physical_path = path
        if "R" in code or "C" in code:
            if index >= len(tokens) or not tokens[index]:
                raise CleanupError("malformed renamed Git status entry")
            path = f"{tokens[index]} -> {path}"
            index += 1
        entry = {"code": code, "path": path}
        entry["content_root"] = safe_content_root(worktree, physical_path)
        entries.append(entry)
    return sorted(entries, key=lambda item: (item["path"], item["code"]))


def dirt_dimensions(code: str) -> list[str]:
    if code == "??":
        return ["untracked"]
    if code == "!!":
        return ["ignored"]
    dimensions: list[str] = []
    if code[0] not in {" ", "?", "!"}:
        dimensions.append("staged")
    if code[1] != " ":
        dimensions.append("unstaged")
    return dimensions or ["unknown"]


def parse_refs(repo: Path) -> list[dict[str, str | None]]:
    raw = git(
        repo,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(upstream)%00",
    ).decode("utf-8", errors="surrogateescape")
    fields = raw.replace("\n", "").split("\0")
    refs: list[dict[str, str | None]] = []
    for offset in range(0, len(fields) - 2, 3):
        name, oid, upstream = fields[offset : offset + 3]
        if not name:
            continue
        if not GIT_OID.fullmatch(oid):
            raise CleanupError("ref has a malformed object ID")
        refs.append({"name": name, "object_id": oid, "upstream": upstream or None})
    return sorted(refs, key=lambda item: str(item["name"]))


def parse_stashes(repo: Path) -> list[dict[str, str]]:
    raw = git(repo, "stash", "list", "--format=%gd%x00%H%x00").decode(
        "utf-8", errors="surrogateescape"
    )
    fields = raw.replace("\n", "").split("\0")
    stashes: list[dict[str, str]] = []
    for offset in range(0, len(fields) - 1, 2):
        name, oid = fields[offset : offset + 2]
        if not name:
            continue
        if not GIT_OID.fullmatch(oid):
            raise CleanupError("stash has a malformed object ID")
        stashes.append({"name": name, "object_id": oid})
    return sorted(stashes, key=lambda item: item["name"])


def parse_reflog_candidates(repo: Path) -> list[dict[str, str]]:
    try:
        raw = git(repo, "reflog", "show", "--all", "--format=%H%x00%gD%x00").decode(
            "utf-8", errors="surrogateescape"
        )
    except CleanupError:
        return []
    fields = raw.replace("\n", "").split("\0")
    candidates: dict[tuple[str, str], dict[str, str]] = {}
    for offset in range(0, len(fields) - 1, 2):
        oid, selector = fields[offset : offset + 2]
        if not oid:
            continue
        if not GIT_OID.fullmatch(oid) or not selector:
            raise CleanupError("reflog candidate is malformed")
        candidates[(selector, oid)] = {"object_id": oid, "selector": selector}
    return [candidates[key] for key in sorted(candidates)]


def remote_snapshot(repo: Path, remote: str, main: str) -> dict[str, Any]:
    try:
        raw = git(repo, "ls-remote", "--refs", remote, timeout=60).decode(
            "utf-8", errors="surrogateescape"
        )
    except CleanupError:
        return {
            "availability": "unavailable",
            "main": None,
            "refs": [],
            "remote": remote,
        }
    refs: list[dict[str, str]] = []
    for line in raw.splitlines():
        oid, separator, name = line.partition("\t")
        if not separator or not GIT_OID.fullmatch(oid) or not name.startswith("refs/"):
            raise CleanupError("remote returned a malformed ref")
        refs.append({"name": name, "object_id": oid})
    refs.sort(key=lambda item: item["name"])
    matches = [
        item["object_id"] for item in refs if item["name"] == f"refs/heads/{main}"
    ]
    if len(matches) > 1:
        raise CleanupError("remote main is ambiguous")
    return {
        "availability": "available",
        "main": matches[0] if matches else None,
        "refs": refs,
        "remote": remote,
    }


def strict_json_object(path: Path, subject: str, maximum: int) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise CleanupError(f"{subject} is missing or oversized")
    try:
        raw = path.read_text(encoding="utf-8")

        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise CleanupError(f"{subject} contains duplicate keys")
                result[key] = value
            return result

        value = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupError(f"{subject} is malformed") from exc
    if not isinstance(value, dict):
        raise CleanupError(f"{subject} must be an object")
    return value


def validate_owner_snapshot(value: dict[str, Any], kind: str) -> None:
    availability = value.get("availability")
    if availability not in {"available", "unavailable"}:
        raise CleanupError(f"{kind} snapshot availability is malformed")
    if value.get("kind") != kind:
        raise CleanupError(f"{kind} snapshot kind differs")
    if availability == "unavailable":
        return
    if value.get("complete") is not True:
        return
    if kind == "provider-snapshot":
        if not isinstance(value.get("owner"), str):
            raise CleanupError("provider snapshot owner is malformed")
        if not isinstance(value.get("pull_requests"), list):
            raise CleanupError("provider snapshot pull requests are malformed")
        if not isinstance(value.get("branch_protection"), dict):
            raise CleanupError("provider snapshot branch protection is malformed")
        required = {
            "baseRefName": str,
            "headRefName": str,
            "headRefOid": str,
            "isDraft": bool,
            "mergeStateStatus": str,
            "number": int,
            "reviewDecision": str,
            "state": str,
            "updatedAt": str,
        }
        for pull_request in value["pull_requests"]:
            if not isinstance(pull_request, dict) or any(
                not isinstance(pull_request.get(field), expected)
                or (
                    field == "headRefOid" and not GIT_OID.fullmatch(pull_request[field])
                )
                for field, expected in required.items()
            ):
                raise CleanupError("provider pull request is malformed")
    elif kind == "task-snapshot":
        if not isinstance(value.get("tasks"), list):
            raise CleanupError("task snapshot tasks are malformed")
        for task in value["tasks"]:
            if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
                raise CleanupError("task snapshot entry is malformed")
            if "changed_paths" in task and not isinstance(task["changed_paths"], list):
                raise CleanupError("task changed paths are malformed")
    elif kind == "release-snapshot" and not isinstance(value.get("release_id"), str):
        raise CleanupError("release snapshot identity is malformed")


def load_owner_snapshot(path: str | None, kind: str) -> dict[str, Any]:
    if path is None:
        return {"availability": "unavailable", "kind": kind}
    source = normalized_absolute(path)
    value = strict_json_object(source, f"{kind} snapshot", MAX_OWNER_SNAPSHOT_BYTES)
    value = dict(value)
    value.setdefault("availability", "available")
    value.setdefault("kind", kind)
    if value["availability"] == "available" and value.get("complete") is not True:
        value["complete"] = False
    validate_owner_snapshot(value, kind)
    return value


def github_slug(remote_url: str) -> str | None:
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?", remote_url)
    if not match:
        match = re.fullmatch(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?", remote_url)
    return match.group(1) if match else None


def provider_snapshot(
    repo: Path,
    provider: str,
    remote_url: str,
    main: str,
    frozen_path: str | None,
) -> dict[str, Any]:
    if frozen_path:
        value = load_owner_snapshot(frozen_path, "provider-snapshot")
        if value.get("owner") != provider:
            raise CleanupError("provider snapshot owner differs")
        return value
    if provider != "github":
        return {
            "availability": "unavailable",
            "kind": "provider-snapshot",
            "owner": provider,
            "reason": "unsupported-owner",
        }
    slug = github_slug(remote_url)
    if not slug or shutil.which("gh") is None:
        return {
            "availability": "unavailable",
            "kind": "provider-snapshot",
            "owner": provider,
            "reason": "owner-tool-unavailable",
        }
    argv = [
        "gh",
        "pr",
        "list",
        "--repo",
        slug,
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,state,headRefName,headRefOid,baseRefName,isDraft,mergeStateStatus,reviewDecision,updatedAt",
    ]
    try:
        payload = json.loads(run_command(argv, repo).decode("utf-8"))
    except (CleanupError, UnicodeError, json.JSONDecodeError):
        return {
            "availability": "unavailable",
            "kind": "provider-snapshot",
            "owner": provider,
            "reason": "owner-query-failed",
        }
    if not isinstance(payload, list):
        raise CleanupError("provider returned a malformed result")
    protection_argv = ["gh", "api", f"repos/{slug}/branches/{main}/protection"]
    try:
        branch_protection = json.loads(
            run_command(protection_argv, repo).decode("utf-8")
        )
    except (CleanupError, UnicodeError, json.JSONDecodeError):
        branch_protection = {
            "availability": "unavailable",
            "reason": "owner-query-failed",
        }
    if not isinstance(branch_protection, dict):
        raise CleanupError("provider returned malformed branch protection")
    value = {
        "availability": "available",
        "argv": argv,
        "branch_protection": branch_protection,
        "complete": len(payload) < 1000
        and branch_protection.get("availability") != "unavailable",
        "kind": "provider-snapshot",
        "owner": provider,
        "pull_requests": sorted(payload, key=lambda item: int(item["number"])),
    }
    validate_owner_snapshot(value, "provider-snapshot")
    return value


def artifact_id(kind: str, identity: Any) -> str:
    return f"{kind}-{sha256(identity)[:24]}"


def owner_for_path(
    path: str, worktree: str, repository_root: str, task_state: dict[str, Any]
) -> str | None:
    tasks = task_state.get("tasks", [])
    if not isinstance(tasks, list):
        return None
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_repo = task.get("repository_root")
        if (
            not isinstance(task_repo, str)
            or str(Path(task_repo).resolve()) != repository_root
        ):
            continue
        task_worktree = task.get("worktree")
        worktree_match = (
            isinstance(task_worktree, str)
            and str(Path(task_worktree).resolve()) == worktree
        )
        if worktree_match or path in task.get("changed_paths", []):
            return str(task.get("task_id")) if task.get("task_id") else None
    return None


def base_record(
    kind: str,
    phase: str,
    status: str,
    repository_identity: str,
    run_id: str,
    source_root: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "created_at": created_at,
        "kind": kind,
        "phase": phase,
        "previous_record_root": None,
        "record_root": "",
        "repository_identity": repository_identity,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "source_snapshot_root": source_root,
        "status": status,
    }


def finish_record(record: dict[str, Any]) -> dict[str, Any]:
    projection = dict(record)
    projection.pop("record_root", None)
    record["record_root"] = sha256(projection)
    return record


def submodule_snapshot(repo: Path) -> dict[str, Any]:
    if not (repo / ".gitmodules").exists():
        return {"availability": "not-present", "entries": []}
    try:
        output = git(repo, "submodule", "status", "--recursive", timeout=60).decode(
            "utf-8", errors="surrogateescape"
        )
    except CleanupError:
        return {"availability": "unavailable", "entries": []}
    entries = sorted(line for line in output.splitlines() if line)
    return {"availability": "available", "entries": entries, "root": sha256(entries)}


def lfs_snapshot(repo: Path) -> dict[str, Any]:
    attributes = git(
        repo, "ls-files", "--", "*.gitattributes", ".gitattributes"
    ).decode("utf-8", errors="surrogateescape")
    attribute_paths = sorted(set(filter(None, attributes.splitlines())))
    present = False
    for relative in attribute_paths:
        candidate = repo / relative
        if candidate.is_file() and "filter=lfs" in candidate.read_text(
            encoding="utf-8", errors="replace"
        ):
            present = True
            break
    if not present:
        return {"availability": "not-present", "entries": []}
    try:
        output = git(repo, "lfs", "ls-files", "--long", timeout=60).decode(
            "utf-8", errors="surrogateescape"
        )
    except CleanupError:
        return {"availability": "unavailable", "entries": []}
    entries = sorted(line for line in output.splitlines() if line)
    return {"availability": "available", "entries": entries, "root": sha256(entries)}


def index_snapshot_root(worktree: Path) -> str:
    raw = git(worktree, "rev-parse", "--git-path", "index").decode().strip()
    index = Path(raw)
    if not index.is_absolute():
        index = worktree / index
    index = index.resolve(strict=True)
    digest = hashlib.sha256()
    with index.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_state(args: argparse.Namespace) -> dict[str, Any]:
    repo, common = resolve_repository(args.repo)
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", args.main) or args.main.startswith("-"):
        raise CleanupError("invalid main branch name")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.remote) or args.remote.startswith("-"):
        raise CleanupError("invalid remote name")
    local_main = git_oid(repo, f"refs/heads/{args.main}")
    remote_url = git(repo, "remote", "get-url", args.remote).decode().strip()
    if not remote_url:
        raise CleanupError("configured remote has no URL")
    tracking_main = git_oid(
        repo, f"refs/remotes/{args.remote}/{args.main}", missing_ok=True
    )
    refs = parse_refs(repo)
    stashes = parse_stashes(repo)
    reflog_candidates = parse_reflog_candidates(repo)
    remote_state = remote_snapshot(repo, args.remote, args.main)
    remote_main = remote_state["main"]
    worktrees = parse_worktrees(repo)
    task_state = load_owner_snapshot(args.task_snapshot, "task-snapshot")
    release_state = load_owner_snapshot(args.release_snapshot, "release-snapshot")
    provider_state = provider_snapshot(
        repo, args.provider, remote_url, args.main, args.provider_snapshot
    )

    artifacts: list[dict[str, Any]] = []
    worktree_projection: list[dict[str, Any]] = []
    for worktree in worktrees:
        worktree_path = Path(str(worktree["worktree"]))
        branch = str(worktree.get("branch", ""))
        include_ignored = worktree_path != repo or branch != f"refs/heads/{args.main}"
        statuses = parse_status(worktree_path, include_ignored=include_ignored)
        status_root = sha256(statuses)
        projection = dict(worktree)
        projection.update(
            {
                "ignored_inventory": include_ignored,
                "index_snapshot_root": index_snapshot_root(worktree_path),
                "status_root": status_root,
            }
        )
        worktree_projection.append(projection)
        owner_id = owner_for_path("", str(worktree_path), str(repo), task_state)
        artifacts.append(
            {
                "artifact_id": artifact_id("worktree", projection),
                "artifact_kind": "worktree",
                "dirt": "clean" if not statuses else "unknown",
                "object_id": str(worktree["HEAD"]),
                "origin": canonical(projection).decode("utf-8"),
                "owner_id": owner_id,
                "path": str(worktree_path),
            }
        )
        for status_entry in statuses:
            relative_path = status_entry["path"]
            for dirt in dirt_dimensions(status_entry["code"]):
                artifacts.append(
                    {
                        "artifact_id": artifact_id(
                            "worktree-path",
                            [
                                str(worktree_path),
                                status_entry["code"],
                                relative_path,
                                dirt,
                                status_entry.get("content_root"),
                            ],
                        ),
                        "artifact_kind": "worktree-path",
                        "dirt": dirt,
                        "object_id": None,
                        "origin": canonical(
                            {
                                "content_root": status_entry.get("content_root"),
                                "status_code": status_entry["code"],
                                "worktree": str(worktree_path),
                            }
                        ).decode("utf-8"),
                        "owner_id": owner_for_path(
                            relative_path, str(worktree_path), str(repo), task_state
                        ),
                        "path": relative_path,
                    }
                )

    for ref in refs:
        artifacts.append(
            {
                "artifact_id": artifact_id("ref", ref["name"]),
                "artifact_kind": "ref",
                "dirt": "clean",
                "object_id": ref["object_id"],
                "origin": str(ref["name"]),
                "owner_id": None,
                "path": None,
            }
        )

    for stash in stashes:
        artifacts.append(
            {
                "artifact_id": artifact_id("stash", stash),
                "artifact_kind": "stash",
                "dirt": "clean",
                "object_id": stash["object_id"],
                "origin": stash["name"],
                "owner_id": None,
                "path": None,
            }
        )

    for candidate in reflog_candidates:
        artifacts.append(
            {
                "artifact_id": artifact_id("reflog-candidate", candidate),
                "artifact_kind": "reflog-candidate",
                "dirt": "clean",
                "object_id": candidate["object_id"],
                "origin": candidate["selector"],
                "owner_id": None,
                "path": None,
            }
        )

    for remote_ref in remote_state["refs"]:
        artifacts.append(
            {
                "artifact_id": artifact_id("remote-ref", remote_ref),
                "artifact_kind": "remote-ref",
                "dirt": "clean",
                "object_id": remote_ref["object_id"],
                "origin": f"{args.remote}:{remote_ref['name']}",
                "owner_id": args.remote,
                "path": None,
            }
        )

    submodule_state = submodule_snapshot(repo)
    lfs_state = lfs_snapshot(repo)
    for kind, posture in (
        ("submodule-posture", submodule_state),
        ("lfs-posture", lfs_state),
    ):
        artifacts.append(
            {
                "artifact_id": artifact_id(kind, posture),
                "artifact_kind": kind,
                "dirt": "unknown"
                if posture["availability"] == "unavailable"
                else "clean",
                "object_id": None,
                "origin": canonical(posture).decode("utf-8"),
                "owner_id": kind,
                "path": None,
            }
        )

    pull_requests = provider_state.get("pull_requests", [])
    if isinstance(pull_requests, list):
        for pull_request in pull_requests:
            if not isinstance(pull_request, dict) or "number" not in pull_request:
                raise CleanupError("provider pull request is malformed")
            oid = pull_request.get("headRefOid")
            artifacts.append(
                {
                    "artifact_id": artifact_id("pull-request", pull_request["number"]),
                    "artifact_kind": "pull-request",
                    "dirt": "clean",
                    "object_id": oid
                    if isinstance(oid, str) and GIT_OID.fullmatch(oid)
                    else None,
                    "origin": canonical(pull_request).decode("utf-8"),
                    "owner_id": None,
                    "path": f"pr:{pull_request['number']}",
                }
            )

    if git_oid(repo, f"refs/heads/{args.main}") != local_main:
        raise CleanupError("source changed during inventory")
    if (
        git_oid(repo, f"refs/remotes/{args.remote}/{args.main}", missing_ok=True)
        != tracking_main
    ):
        raise CleanupError("source changed during inventory")
    if (
        parse_refs(repo) != refs
        or parse_stashes(repo) != stashes
        or parse_reflog_candidates(repo) != reflog_candidates
        or parse_worktrees(repo) != worktrees
        or remote_snapshot(repo, args.remote, args.main) != remote_state
    ):
        raise CleanupError("source changed during inventory")
    for projection in worktree_projection:
        worktree_path = Path(str(projection["worktree"]))
        if (
            sha256(
                parse_status(
                    worktree_path, include_ignored=projection["ignored_inventory"]
                )
            )
            != projection["status_root"]
        ):
            raise CleanupError("source changed during inventory")
        if index_snapshot_root(worktree_path) != projection["index_snapshot_root"]:
            raise CleanupError("source changed during inventory")
    if args.task_snapshot and sha256(
        load_owner_snapshot(args.task_snapshot, "task-snapshot")
    ) != sha256(task_state):
        raise CleanupError("task owner changed during inventory")
    if args.release_snapshot and sha256(
        load_owner_snapshot(args.release_snapshot, "release-snapshot")
    ) != sha256(release_state):
        raise CleanupError("release owner changed during inventory")
    if args.provider_snapshot and sha256(
        load_owner_snapshot(args.provider_snapshot, "provider-snapshot")
    ) != sha256(provider_state):
        raise CleanupError("provider owner changed during inventory")
    if (
        not args.provider_snapshot
        and provider_snapshot(repo, args.provider, remote_url, args.main, None)
        != provider_state
    ):
        raise CleanupError("provider owner changed during inventory")
    if submodule_snapshot(repo) != submodule_state or lfs_snapshot(repo) != lfs_state:
        raise CleanupError("submodule or LFS owner changed during inventory")
    identity = sha256(
        {
            "common_dir": str(common),
            "main_ref": f"refs/heads/{args.main}",
            "remote": args.remote,
            "remote_url": remote_url,
            "repository_root": str(repo),
        }
    )
    ref_snapshot_root = sha256(
        {
            "local": refs,
            "reflog": reflog_candidates,
            "remote": remote_state,
            "stashes": stashes,
        }
    )
    worktree_snapshot_root = sha256(
        {
            "lfs": lfs_state,
            "submodules": submodule_state,
            "worktrees": worktree_projection,
        }
    )
    source_fields = {
        "common_dir": str(common),
        "main_ref": f"refs/heads/{args.main}@{local_main}",
        "provider_snapshot_root": sha256(provider_state),
        "ref_snapshot_root": ref_snapshot_root,
        "release_snapshot_root": sha256(release_state),
        "remote_main": remote_main,
        "remote_name": args.remote,
        "remote_url": remote_url,
        "repository_root": str(repo),
        "task_snapshot_root": sha256(task_state),
        "worktree_snapshot_root": worktree_snapshot_root,
    }
    source_root = sha256(source_fields)
    run_id = f"cleanup-{source_root[:24]}"
    created_at = utc_now()
    source_record = base_record(
        "source-snapshot",
        "inventory",
        "passed",
        identity,
        run_id,
        source_root,
        created_at,
    )
    source_record.update(source_fields)
    finish_record(source_record)
    artifacts = sorted(artifacts, key=lambda item: item["artifact_id"])
    if len({item["artifact_id"] for item in artifacts}) != len(artifacts):
        raise CleanupError("artifact identities are not unique")
    inventory_root = sha256({"artifact_count": len(artifacts), "artifacts": artifacts})
    inventory_record = base_record(
        "inventory", "inventory", "passed", identity, run_id, source_root, created_at
    )
    inventory_record.update(
        {
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "inventory_root": inventory_root,
        }
    )
    finish_record(inventory_record)
    return {
        "artifacts": artifacts,
        "common_dir": common,
        "created_at": created_at,
        "identity": identity,
        "inventory": inventory_record,
        "provider": provider_state,
        "release": release_state,
        "repo": repo,
        "remote_main": remote_main,
        "run_id": run_id,
        "source": source_record,
        "source_root": source_root,
        "tasks": task_state,
        "lfs": lfs_state,
        "remote": remote_state,
        "submodules": submodule_state,
    }


def active_overlapping_tasks(state: dict[str, Any]) -> list[str]:
    tasks = state["tasks"].get("tasks", [])
    if not isinstance(tasks, list):
        return []
    active: list[str] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_repo = task.get("repository_root")
        if not isinstance(task_repo, str) or Path(task_repo).resolve() != state["repo"]:
            continue
        if task.get("status") in {"active", "running", "in-progress"} and task.get(
            "writer", True
        ):
            active.append(str(task.get("task_id", "unknown-task")))
    return sorted(set(active))


def build_plan(state: dict[str, Any]) -> dict[str, Any]:
    holds: list[dict[str, Any]] = []

    def add_hold(subject: str) -> None:
        hold_id = f"hold-{sha256([state['source_root'], subject])[:24]}"
        holds.append(
            {
                "carry_forward": False,
                "effect_scope": [subject],
                "expiry_root": state["source_root"],
                "hold_id": hold_id,
                "successor_effects": "blocked",
            }
        )

    if state["remote_main"] is None:
        add_hold("remote-main-unavailable")
    if state["remote"].get("availability") != "available":
        add_hold("remote-owner-unavailable")
    if state["provider"].get("availability") != "available":
        add_hold("provider-owner-unavailable")
    elif state["provider"].get("complete") is not True:
        add_hold("provider-inventory-incomplete")
    if state["tasks"].get("availability") != "available":
        add_hold("task-owner-unavailable")
    elif state["tasks"].get("complete") is not True:
        add_hold("task-inventory-incomplete")
    if state["release"].get("availability") != "available":
        add_hold("release-owner-unavailable")
    elif state["release"].get("complete") is not True:
        add_hold("release-inventory-incomplete")
    if state["submodules"].get("availability") == "unavailable":
        add_hold("submodule-owner-unavailable")
    if state["lfs"].get("availability") == "unavailable":
        add_hold("lfs-owner-unavailable")
    dirty = [item for item in state["artifacts"] if item["dirt"] != "clean"]
    if dirty:
        add_hold("dirty-or-unknown-worktree-state")
    active_tasks = active_overlapping_tasks(state)
    for task_id in active_tasks:
        add_hold(f"active-writer:{task_id}")

    dispositions: list[dict[str, Any]] = []
    for artifact in state["artifacts"]:
        dispositions.append(
            {
                "artifact_id": artifact["artifact_id"],
                "disposition": "retain",
                "proof_refs": [],
            }
        )

    holds = sorted(holds, key=lambda item: item["hold_id"])
    if active_tasks:
        path = "coordinated-reconciliation"
        next_action = "obtain-owner-checkpoints-and-quiescence-gate"
    elif holds:
        path = "audit"
        next_action = f"resolve:{holds[0]['effect_scope'][0]}"
    else:
        path = "safe-cleanup"
        next_action = "build-preservation-and-capability-proof"
    plan_root = sha256(
        {
            "dispositions": dispositions,
            "holds": holds,
            "inventory_root": state["inventory"]["inventory_root"],
            "next_action": next_action,
            "path": path,
            "source_snapshot_root": state["source_root"],
        }
    )
    record = base_record(
        "plan",
        "plan",
        "passed",
        state["identity"],
        state["run_id"],
        state["source_root"],
        state["created_at"],
    )
    record.update(
        {
            "dispositions": dispositions,
            "holds": holds,
            "inventory_root": state["inventory"]["inventory_root"],
            "next_action": next_action,
            "path": path,
            "plan_root": plan_root,
        }
    )
    return finish_record(record)


def artifact_root(args: argparse.Namespace, state: dict[str, Any]) -> Path:
    raw = args.artifact_root or str(
        Path.home() / ".codex" / "software-factory-cleanup" / "runs"
    )
    root = normalized_absolute(raw, must_exist=False)
    repo = state["repo"]
    common = state["common_dir"]
    if root == repo or repo in root.parents or root == common or common in root.parents:
        raise CleanupError(
            "artifact root must be outside repository and Git common directory"
        )
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CleanupError("artifact root contains a symlink")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise CleanupError("artifact root is unsafe")
    return root


def run_directory(args: argparse.Namespace, state: dict[str, Any]) -> Path:
    root = artifact_root(args, state)
    directory = root / state["identity"] / state["run_id"]
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = directory.resolve(strict=True)
    if resolved != directory or resolved.is_symlink():
        raise CleanupError("run directory is unsafe")
    return directory


def write_immutable(path: Path, value: dict[str, Any]) -> None:
    payload = canonical(value) + b"\n"
    if len(payload) > MAX_RECORD_BYTES:
        raise CleanupError(f"record exceeds {MAX_RECORD_BYTES} bytes")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            existing = os.read(descriptor, MAX_RECORD_BYTES + 1)
        finally:
            os.close(descriptor)
        if existing != payload:
            raise CleanupError(f"immutable record differs: {path.name}")
        return
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise CleanupError(f"record write did not advance: {path.name}")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def schema_definition() -> dict[str, Any]:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "references"
        / "repository-reconciliation-schema-v1.json"
    )
    try:
        value = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupError("record schema is unavailable") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise CleanupError("record schema is incompatible")
    return value


def matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def validate_format(value: Any, format_name: str) -> bool:
    if format_name in {"sha256", "sha256-self-excluded"}:
        return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))
    if format_name == "sha256-or-null":
        return value is None or validate_format(value, "sha256")
    if format_name == "git-oid":
        return isinstance(value, str) and bool(GIT_OID.fullmatch(value))
    if format_name == "git-oid-or-null":
        return value is None or validate_format(value, "git-oid")
    if format_name == "cleanup-id":
        return isinstance(value, str) and bool(RUN_ID.fullmatch(value))
    if format_name == "canonical-absolute-path":
        return (
            isinstance(value, str)
            and Path(value).is_absolute()
            and os.path.normpath(value) == value
        )
    if format_name == "rfc3339":
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True
    if format_name == "git-mode":
        return isinstance(value, str) and bool(re.fullmatch(r"[0-7]{6}", value))
    if format_name in {"record-kind", "normalized-git-url"}:
        return isinstance(value, str) and bool(value)
    return False


def validate_field(
    value: Any, spec: dict[str, Any], schema: dict[str, Any], subject: str
) -> None:
    expected = spec.get("type")
    expected_types = expected if isinstance(expected, list) else [expected]
    if not expected_types or not any(
        matches_type(value, item) for item in expected_types
    ):
        raise CleanupError(f"schema type differs: {subject}")
    if "const" in spec and value != spec["const"]:
        raise CleanupError(f"schema constant differs: {subject}")
    if "enum" in spec and value not in spec["enum"]:
        raise CleanupError(f"schema enum differs: {subject}")
    if "enum_ref" in spec and value not in schema.get(spec["enum_ref"], []):
        raise CleanupError(f"schema referenced enum differs: {subject}")
    if "format" in spec and not validate_format(value, spec["format"]):
        raise CleanupError(f"schema format differs: {subject}")
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in spec:
        if value < spec["minimum"]:
            raise CleanupError(f"schema minimum differs: {subject}")
    if isinstance(value, str) and "max_length" in spec:
        if len(value) > spec["max_length"]:
            raise CleanupError(f"schema string bound differs: {subject}")
    if isinstance(value, list):
        if len(value) < int(spec.get("min_items", 0)):
            raise CleanupError(f"schema array bound differs: {subject}")
        item_name = spec.get("items")
        for index, item in enumerate(value):
            if item_name in {"string", "integer"}:
                if not matches_type(item, item_name):
                    raise CleanupError(f"schema item type differs: {subject}[{index}]")
            elif item_name:
                validate_item(item, item_name, schema, f"{subject}[{index}]")
        if spec.get("unique") and len({canonical(item) for item in value}) != len(
            value
        ):
            raise CleanupError(f"schema array is not unique: {subject}")
        unique_by = spec.get("unique_by")
        if unique_by:
            keys = [
                item.get(unique_by) if isinstance(item, dict) else None
                for item in value
            ]
            if None in keys or len(set(keys)) != len(keys):
                raise CleanupError(f"schema keyed array is not unique: {subject}")
    if isinstance(value, dict) and spec.get("item_ref"):
        validate_item(value, spec["item_ref"], schema, subject)


def validate_item(
    value: Any, item_name: str, schema: dict[str, Any], subject: str
) -> None:
    definition = schema.get("item_types", {}).get(item_name)
    if not isinstance(definition, dict) or not isinstance(value, dict):
        raise CleanupError(f"schema item differs: {subject}")
    fields = definition["fields"]
    required = set(definition["required"])
    if not required <= set(value):
        raise CleanupError(f"schema item field missing: {subject}")
    if definition.get("additional_fields") is False and set(value) != set(fields):
        raise CleanupError(f"schema item fields differ: {subject}")
    for name, field_spec in fields.items():
        validate_field(value[name], field_spec, schema, f"{subject}.{name}")


def validate_record(value: dict[str, Any]) -> None:
    schema = schema_definition()
    kind = value.get("kind")
    definition = schema.get("records", {}).get(kind)
    if not isinstance(definition, dict):
        raise CleanupError("record kind is unknown")
    fields = {**schema["base_fields"], **definition["fields"]}
    if schema["record_field_policy"].get("additional_fields") is False and set(
        value
    ) != set(fields):
        raise CleanupError("record fields differ")
    if schema["record_field_policy"].get("required") == "all-declared-fields" and set(
        fields
    ) - set(value):
        raise CleanupError("record field is missing")
    if value.get("phase") != definition["phase"]:
        raise CleanupError("record phase differs")
    for name, field_spec in fields.items():
        validate_field(value[name], field_spec, schema, name)
    if value["run_id"] != f"cleanup-{value['source_snapshot_root'][:24]}":
        raise CleanupError("run identity differs from source root")
    if kind == "inventory":
        artifacts = value["artifacts"]
        if artifacts != sorted(artifacts, key=lambda item: item["artifact_id"]):
            raise CleanupError("inventory artifacts are not canonically sorted")
        if value["artifact_count"] != len(artifacts):
            raise CleanupError("inventory count differs")
        expected = sha256({"artifact_count": len(artifacts), "artifacts": artifacts})
        if value["inventory_root"] != expected:
            raise CleanupError("inventory root differs")
    elif kind == "plan":
        dispositions = value["dispositions"]
        holds = value["holds"]
        if dispositions != sorted(dispositions, key=lambda item: item["artifact_id"]):
            raise CleanupError("plan dispositions are not canonically sorted")
        if holds != sorted(holds, key=lambda item: item["hold_id"]):
            raise CleanupError("plan holds are not canonically sorted")
        expected = sha256(
            {
                "dispositions": dispositions,
                "holds": holds,
                "inventory_root": value["inventory_root"],
                "next_action": value["next_action"],
                "path": value["path"],
                "source_snapshot_root": value["source_snapshot_root"],
            }
        )
        if value["plan_root"] != expected:
            raise CleanupError("plan root differs")
        if any(
            entry["disposition"] != "retain" or entry["proof_refs"]
            for entry in dispositions
        ):
            raise CleanupError("planning cannot manufacture acceptance")
        if any(hold["expiry_root"] != value["source_snapshot_root"] for hold in holds):
            raise CleanupError("plan hold expiry differs from source")
    elif kind == "source-snapshot":
        source_fields = {name: value[name] for name in definition["fields"]}
        if value["source_snapshot_root"] != sha256(source_fields):
            raise CleanupError("source snapshot root differs")
    elif kind == "status":
        entries = value["current_record_roots"]["entries"]
        if entries != sorted(entries, key=lambda item: item["kind"]):
            raise CleanupError("status roots are not canonically sorted")


def read_record(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > MAX_RECORD_BYTES
    ):
        raise CleanupError(f"record is missing or unsafe: {path.name}")
    try:
        raw = path.read_bytes()

        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, item in pairs:
                if key in result:
                    raise CleanupError(f"record contains duplicate keys: {path.name}")
                result[key] = item
            return result

        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupError(f"record is malformed: {path.name}") from exc
    if not isinstance(value, dict):
        raise CleanupError(f"record is not an object: {path.name}")
    if raw != canonical(value) + b"\n":
        raise CleanupError(f"record encoding is not canonical: {path.name}")
    validate_record(value)
    projection = dict(value)
    record_root = projection.pop("record_root", None)
    if record_root != sha256(projection):
        raise CleanupError(f"record root differs: {path.name}")
    return value


def status_record(state: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    record = base_record(
        "status",
        "outcome",
        "open",
        state["identity"],
        state["run_id"],
        state["source_root"],
        state["created_at"],
    )
    record.update(
        {
            "active_holds": plan["holds"],
            "current_phase": "plan",
            "current_record_roots": {
                "entries": [
                    {"kind": "inventory", "root": state["inventory"]["record_root"]},
                    {"kind": "plan", "root": plan["record_root"]},
                    {"kind": "source-snapshot", "root": state["source"]["record_root"]},
                ]
            },
            "gate_posture": {
                "deletion": "not-requested",
                "outcome": "not-requested",
                "plan": "permitted",
                "quiescence": "not-requested",
            },
            "next_action": plan["next_action"],
        }
    )
    return finish_record(record)


def write_inventory(args: argparse.Namespace, state: dict[str, Any]) -> Path:
    directory = run_directory(args, state)
    existing_source = directory / "source-snapshot.json"
    if existing_source.exists():
        previous = read_record(existing_source)
        state["created_at"] = str(previous["created_at"])
        for record in (state["source"], state["inventory"]):
            record["created_at"] = state["created_at"]
            finish_record(record)
    write_immutable(existing_source, state["source"])
    write_immutable(directory / "inventory.json", state["inventory"])
    return directory


def verify_directory(directory: Path) -> dict[str, Any]:
    directory = normalized_absolute(str(directory))
    if not directory.is_dir() or not RUN_ID.fullmatch(directory.name):
        raise CleanupError("run directory is invalid")
    source = read_record(directory / "source-snapshot.json")
    inventory = read_record(directory / "inventory.json")
    if inventory["source_snapshot_root"] != source["source_snapshot_root"]:
        raise CleanupError("inventory source binding differs")
    common_fields = ("repository_identity", "run_id", "source_snapshot_root")
    for field in common_fields:
        if inventory[field] != source[field]:
            raise CleanupError(f"inventory {field} binding differs")
    records = {"inventory": inventory, "source-snapshot": source}
    plan_path = directory / "plan.json"
    if plan_path.exists():
        plan = read_record(plan_path)
        if plan["inventory_root"] != inventory["inventory_root"]:
            raise CleanupError("plan inventory binding differs")
        if plan["source_snapshot_root"] != source["source_snapshot_root"]:
            raise CleanupError("plan source binding differs")
        for field in common_fields:
            if plan[field] != source[field]:
                raise CleanupError(f"plan {field} binding differs")
        inventory_ids = [item["artifact_id"] for item in inventory["artifacts"]]
        disposition_ids = [item["artifact_id"] for item in plan["dispositions"]]
        if disposition_ids != inventory_ids:
            raise CleanupError("plan dispositions do not exhaust the inventory")
        records["plan"] = plan
    status_path = directory / "status.json"
    if status_path.exists():
        status = read_record(status_path)
        for field in common_fields:
            if status[field] != source[field]:
                raise CleanupError(f"status {field} binding differs")
        expected_roots = [
            {"kind": kind, "root": record["record_root"]}
            for kind, record in sorted(records.items())
        ]
        if status["current_record_roots"]["entries"] != expected_roots:
            raise CleanupError("status record roots differ")
        if "plan" in records:
            if status["active_holds"] != records["plan"]["holds"]:
                raise CleanupError("status holds differ from plan")
            if status["next_action"] != records["plan"]["next_action"]:
                raise CleanupError("status action differs from plan")
        records["status"] = status
    return {
        "record_roots": {
            key: value["record_root"] for key, value in sorted(records.items())
        },
        "run_dir": str(directory),
        "run_id": source["run_id"],
        "source_snapshot_root": source["source_snapshot_root"],
        "status": "verified",
    }


def common_parser(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--repo", required=True)
    subparser.add_argument("--main", default="main")
    subparser.add_argument("--remote", default="origin")
    subparser.add_argument("--provider", default="github")
    subparser.add_argument("--provider-snapshot")
    subparser.add_argument("--task-snapshot")
    subparser.add_argument("--release-snapshot")
    subparser.add_argument("--artifact-root")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "plan"):
        common_parser(commands.add_parser(name))
    status = commands.add_parser("status")
    status.add_argument("--run-dir", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--run-dir", required=True)
    common_parser(verify)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.command in {"status", "verify"}:
            result = verify_directory(Path(args.run_dir))
            if args.command == "verify":
                current = build_state(args)
                if current["source_root"] != result["source_snapshot_root"]:
                    raise CleanupError("source changed; successor plan required")
                result["current"] = True
            else:
                directory = Path(result["run_dir"])
                status_path = directory / "status.json"
                if status_path.exists():
                    status = read_record(status_path)
                    result.update(
                        {
                            "active_holds": status["active_holds"],
                            "current_phase": status["current_phase"],
                            "next_action": status["next_action"],
                        }
                    )
                else:
                    result.update(
                        {
                            "active_holds": [],
                            "current_phase": "inventory",
                            "next_action": "produce-plan",
                        }
                    )
            print(canonical(result).decode("utf-8"))
            return 0

        state = build_state(args)
        directory = write_inventory(args, state)
        result: dict[str, Any] = {
            "inventory_root": state["inventory"]["inventory_root"],
            "run_dir": str(directory),
            "run_id": state["run_id"],
            "source_snapshot_root": state["source_root"],
            "status": "inventory-complete",
        }
        if args.command == "plan":
            plan = build_plan(state)
            write_immutable(directory / "plan.json", plan)
            status = status_record(state, plan)
            write_immutable(directory / "status.json", status)
            result.update(
                {
                    "hold_count": len(plan["holds"]),
                    "next_action": plan["next_action"],
                    "path": plan["path"],
                    "plan_root": plan["plan_root"],
                    "status": "plan-complete",
                }
            )
        print(canonical(result).decode("utf-8"))
        return 0
    except CleanupError as exc:
        print(canonical({"error": str(exc), "status": "rejected"}).decode("utf-8"))
        return 2


if __name__ == "__main__":
    sys.exit(main())
