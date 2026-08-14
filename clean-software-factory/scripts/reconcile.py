#!/usr/bin/env python3
"""Deterministic inventory, planning, and local preservation for reconciliation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_OWNER_SNAPSHOT_BYTES = 1024 * 1024
MAX_COMMAND_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_PRESERVATION_FILE_BYTES = 8 * 1024 * 1024
MAX_PRESERVATION_PACKAGE_BYTES = 64 * 1024 * 1024
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


def run_command(
    argv: list[str],
    cwd: Path,
    *,
    timeout: int = 30,
    max_output_bytes: int = MAX_COMMAND_OUTPUT_BYTES,
) -> bytes:
    environment = os.environ.copy()
    environment.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"})
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                check=False,
                timeout=timeout,
            )
            if (
                os.fstat(stdout.fileno()).st_size > max_output_bytes
                or os.fstat(stderr.fileno()).st_size > max_output_bytes
            ):
                raise CleanupError(f"command output exceeds bound: {argv[0]}")
            stdout.seek(0)
            output = stdout.read(max_output_bytes + 1)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CleanupError(f"command unavailable: {argv[0]}") from exc
    if completed.returncode != 0:
        raise CleanupError(f"command failed ({completed.returncode}): {argv[0]}")
    return output


def git(repo: Path, *args: str, timeout: int = 30) -> bytes:
    return run_command(["git", *args], repo, timeout=timeout)


def normalized_absolute(raw: str, *, must_exist: bool = True) -> Path:
    lexical = Path(raw)
    if not lexical.is_absolute() or os.path.normpath(raw) != raw or raw == "/":
        raise CleanupError("path must be canonical and absolute")
    for candidate in (lexical, *lexical.parents):
        if candidate.is_symlink():
            raise CleanupError("symlink or substituted path is not allowed")
    try:
        resolved = lexical.resolve(strict=must_exist)
    except OSError as exc:
        raise CleanupError("path is unavailable") from exc
    if resolved != lexical:
        raise CleanupError("path is not canonical")
    return resolved


def resolve_repository(raw: str) -> tuple[Path, Path]:
    repo = normalized_absolute(raw)
    if not repo.is_dir():
        raise CleanupError("repository path is not a directory")
    top = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != repo:
        raise CleanupError("repository must be its canonical top level")
    common_raw = git(repo, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common_raw)
    if not common.is_absolute():
        common = repo / common
    common = common.resolve(strict=True)
    if not common.is_dir() or common == Path("/"):
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


def parse_status(worktree: Path) -> list[dict[str, str]]:
    raw = git(
        worktree,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=normal",
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
        if "R" in code or "C" in code:
            if index >= len(tokens) or not tokens[index]:
                raise CleanupError("malformed renamed Git status entry")
            path = f"{tokens[index]} -> {path}"
            index += 1
        entries.append({"code": code, "path": path})
    return sorted(entries, key=lambda item: (item["path"], item["code"]))


def dirt_for(code: str) -> str:
    if code == "??":
        return "untracked"
    if code == "!!":
        return "ignored"
    if code[0] not in {" ", "?", "!"}:
        return "staged"
    if code[1] != " ":
        return "unstaged"
    return "unknown"


def parse_refs(repo: Path) -> list[dict[str, str | None]]:
    raw = git(
        repo,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(upstream)%00",
        "refs/heads",
        "refs/remotes",
        "refs/tags",
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


def load_owner_snapshot(path: str | None, kind: str) -> dict[str, Any]:
    if path is None:
        return {"availability": "unavailable", "kind": kind}
    source = normalized_absolute(path)
    if not source.is_file() or source.stat().st_size > MAX_OWNER_SNAPSHOT_BYTES:
        raise CleanupError(f"{kind} snapshot is missing or oversized")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupError(f"{kind} snapshot is malformed") from exc
    if not isinstance(value, dict):
        raise CleanupError(f"{kind} snapshot must be an object")
    value = dict(value)
    value.setdefault("availability", "available")
    value.setdefault("kind", kind)
    if value["availability"] == "available":
        value["complete"] = False
    return value


def github_slug(remote_url: str) -> str | None:
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?", remote_url)
    if not match:
        match = re.fullmatch(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?", remote_url)
    return match.group(1) if match else None


def provider_snapshot(
    repo: Path, provider: str, remote_url: str, frozen_path: str | None
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
        "number,state,headRefName,headRefOid,baseRefName,isDraft,mergeStateStatus,updatedAt",
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
    return {
        "availability": "available",
        "argv": argv,
        "complete": False,
        "kind": "provider-snapshot",
        "owner": provider,
        "pull_requests": sorted(payload, key=lambda item: int(item["number"])),
    }


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
    remote_main = git_oid(
        repo, f"refs/remotes/{args.remote}/{args.main}", missing_ok=True
    )
    refs = parse_refs(repo)
    worktrees = parse_worktrees(repo)
    task_state = load_owner_snapshot(args.task_snapshot, "task-snapshot")
    release_state = load_owner_snapshot(args.release_snapshot, "release-snapshot")
    provider_state = provider_snapshot(
        repo, args.provider, remote_url, args.provider_snapshot
    )

    artifacts: list[dict[str, Any]] = []
    worktree_projection: list[dict[str, Any]] = []
    for worktree in worktrees:
        worktree_path = Path(str(worktree["worktree"]))
        statuses = parse_status(worktree_path)
        status_root = sha256(statuses)
        projection = dict(worktree)
        projection.update(
            {
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
                "origin": str(common),
                "owner_id": owner_id,
                "path": str(worktree_path),
            }
        )
        for status_entry in statuses:
            relative_path = status_entry["path"]
            artifacts.append(
                {
                    "artifact_id": artifact_id(
                        "worktree-path",
                        [str(worktree_path), status_entry["code"], relative_path],
                    ),
                    "artifact_kind": "worktree-path",
                    "dirt": dirt_for(status_entry["code"]),
                    "object_id": None,
                    "origin": str(worktree_path),
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

    stash_raw = git(repo, "stash", "list", "--format=%gd%x00%H%x00").decode(
        "utf-8", errors="surrogateescape"
    )
    stash_fields = stash_raw.replace("\n", "").split("\0")
    for offset in range(0, len(stash_fields) - 1, 2):
        name, oid = stash_fields[offset : offset + 2]
        if not name:
            continue
        artifacts.append(
            {
                "artifact_id": artifact_id("stash", [name, oid]),
                "artifact_kind": "stash",
                "dirt": "clean",
                "object_id": oid if GIT_OID.fullmatch(oid) else None,
                "origin": name,
                "owner_id": None,
                "path": None,
            }
        )

    submodule_state: dict[str, Any] = {"availability": "deferred-bounded-scan"}
    lfs_state: dict[str, Any] = {"availability": "deferred-bounded-scan"}

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
                    "origin": args.provider,
                    "owner_id": None,
                    "path": f"pr:{pull_request['number']}",
                }
            )

    semantic = {
        "common_dir": str(common),
        "invocation": {
            "main": args.main,
            "provider": args.provider,
            "remote": args.remote,
        },
        "lfs": lfs_state,
        "local_main": local_main,
        "provider": provider_state,
        "refs": refs,
        "release": release_state,
        "remote_main": remote_main,
        "remote_url": remote_url,
        "repository_root": str(repo),
        "submodules": submodule_state,
        "tasks": task_state,
        "worktrees": worktree_projection,
    }
    if git_oid(repo, f"refs/heads/{args.main}") != local_main:
        raise CleanupError("source changed during inventory")
    if (
        git_oid(repo, f"refs/remotes/{args.remote}/{args.main}", missing_ok=True)
        != remote_main
    ):
        raise CleanupError("source changed during inventory")
    if parse_refs(repo) != refs or parse_worktrees(repo) != worktrees:
        raise CleanupError("source changed during inventory")
    for projection in worktree_projection:
        worktree_path = Path(str(projection["worktree"]))
        if sha256(parse_status(worktree_path)) != projection["status_root"]:
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
    identity = sha256(
        {
            "common_dir": str(common),
            "main_ref": f"refs/heads/{args.main}",
            "remote": args.remote,
            "remote_url": remote_url,
            "repository_root": str(repo),
        }
    )
    source_root = sha256(semantic)
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
    source_record.update(
        {
            "common_dir": str(common),
            "main_ref": f"refs/heads/{args.main}@{local_main}",
            "provider_snapshot_root": sha256(provider_state),
            "ref_snapshot_root": sha256(refs),
            "release_snapshot_root": sha256(release_state),
            "remote_main": remote_main,
            "remote_name": args.remote,
            "remote_url": remote_url,
            "repository_root": str(repo),
            "task_snapshot_root": sha256(task_state),
            "worktree_snapshot_root": sha256(worktree_projection),
        }
    )
    finish_record(source_record)
    posture = "deferred proof: custom refs/reflogs; ignored/untracked bytes; worktree/stash/submodule/LFS detail; owner/remote completeness/currentness; overlap; canonical/proof-root closure; bounded fast path"
    artifacts.append(
        {
            "artifact_id": artifact_id("bounded-inventory-posture", posture),
            "artifact_kind": "bounded-inventory-posture",
            "dirt": "unknown",
            "object_id": None,
            "origin": posture,
            "owner_id": None,
            "path": None,
        }
    )
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
    }


def active_overlapping_tasks(state: dict[str, Any]) -> list[str]:
    if state["tasks"].get("complete") is not True:
        return []
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
    add_hold("remote-currentness-unproved")
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
    add_hold("task-overlap-unproved")
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


def safe_status_path(raw: str) -> PurePosixPath | None:
    path = PurePosixPath(raw)
    if (
        not raw
        or " -> " in raw
        or path.is_absolute()
        or ".." in path.parts
        or raw.endswith("/")
    ):
        return None
    return path


def read_regular_file(path: Path) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CleanupError("preservation source is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size > MAX_PRESERVATION_FILE_BYTES
        ):
            raise CleanupError("preservation source is nonregular or oversized")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise CleanupError("preservation source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if identity(before) != identity(after):
        raise CleanupError("preservation source changed while reading")
    return b"".join(chunks), f"{before.st_mode:06o}"[-6:]


def restore_drill(payload: bytes) -> str:
    with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
        restored = Path(temporary) / "restored.bin"
        restored.write_bytes(payload)
        if restored.read_bytes() != payload:
            raise CleanupError("local restore drill differs")
    return sha256(payload)


def write_local_package(
    directory: Path,
    package_id: str,
    files: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len({item["artifact_id"] for item in files}) != len(files):
        raise CleanupError("preservation package artifact identities differ")
    total = sum(len(item["payload"]) for item in files)
    if total > MAX_PRESERVATION_PACKAGE_BYTES:
        raise CleanupError("preservation package exceeds local byte bound")
    package_path = directory / "packages" / package_id
    package_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if package_path.is_symlink() or package_path.resolve(strict=True) != package_path:
        raise CleanupError("preservation package path is unsafe")
    rows: list[dict[str, Any]] = []
    byte_entries: list[dict[str, Any]] = []
    for item in sorted(files, key=lambda value: value["artifact_id"]):
        payload = item["payload"]
        name = f"{item['artifact_id']}.bin"
        write_immutable_bytes(package_path / name, payload, MAX_PRESERVATION_FILE_BYTES)
        digest = sha256(payload)
        rows.append(
            {
                "artifact_id": item["artifact_id"],
                "mode": item["mode"],
                "name": name,
                "path": item["path"],
                "sha256": digest,
                "size": len(payload),
            }
        )
        byte_entries.append(
            {
                "artifact_id": item["artifact_id"],
                "mode": item["mode"],
                "path": item["path"],
                "sha256": digest,
                "size": len(payload),
            }
        )
    artifact_ids = sorted({item["artifact_id"] for item in files})
    manifest = {
        "artifact_ids": artifact_ids,
        "files": rows,
        "kind": "local-preservation-package",
        "schema_version": SCHEMA_VERSION,
    }
    manifest_payload = canonical(manifest) + b"\n"
    write_immutable_bytes(
        package_path / "manifest.json", manifest_payload, MAX_RECORD_BYTES
    )
    return (
        {
            "artifact_ids": artifact_ids,
            "local_only": True,
            "package_id": package_id,
            "package_root": sha256(manifest_payload),
            "path": str(package_path),
        },
        byte_entries,
    )


def surface_kinds(path: str | None) -> list[str]:
    if not path:
        return []
    lowered = path.lower()
    name = PurePosixPath(path).name
    tokens = set(re.split(r"[^a-z0-9]+", lowered))
    kinds: list[str] = []
    rules: tuple[tuple[str, set[str]], ...] = (
        ("route", {"route", "routes", "router"}),
        ("api", {"api"}),
        ("migration", {"migration", "migrations", "migrate"}),
        ("configuration", {"config", "configuration"}),
        ("ui", {"component", "components", "frontend", "ui"}),
        ("test", {"test", "tests", "spec", "specs"}),
        ("fix", {"fix", "bug"}),
        ("tracker-evidence", {"tracker"}),
        ("review-evidence", {"review"}),
        ("deferred-option", {"defer", "deferred", "todo"}),
    )
    for kind, markers in rules:
        if tokens & markers:
            kinds.append(kind)
    if name.endswith((".tsx", ".jsx", ".css")) and "ui" not in kinds:
        kinds.append("ui")
    return kinds


def build_preservation(
    state: dict[str, Any], plan: dict[str, Any], directory: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact_ids = {item["artifact_id"] for item in state["artifacts"]}
    disposition_ids = {item["artifact_id"] for item in plan["dispositions"]}
    if artifact_ids != disposition_ids or any(
        item["disposition"] != "retain" for item in plan["dispositions"]
    ):
        raise CleanupError("preservation requires exhaustive retain-first plan")

    object_entries: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    byte_entries: list[dict[str, Any]] = []
    proof_roots: dict[str, list[str]] = {}
    object_cache: dict[str, tuple[str, str]] = {}
    for artifact in state["artifacts"]:
        oid = artifact["object_id"]
        if not isinstance(oid, str):
            continue
        cached = object_cache.get(oid)
        if cached is None:
            try:
                raw_type = git(state["repo"], "cat-file", "-t", oid).decode().strip()
                payload = git(state["repo"], "cat-file", "-p", oid)
            except CleanupError:
                continue
            if len(payload) > MAX_PRESERVATION_FILE_BYTES or raw_type not in {
                "commit",
                "tree",
                "blob",
                "tag",
            }:
                continue
            cached = (raw_type, restore_drill(payload))
            object_cache[oid] = cached
        object_type, payload_root = cached
        if artifact["artifact_kind"] == "stash":
            object_type = "stash"
        object_entries.append(
            {
                "artifact_id": artifact["artifact_id"],
                "object_id": oid,
                "object_type": object_type,
            }
        )
        proof_roots.setdefault(artifact["artifact_id"], []).append(payload_root)

    for worktree in (
        item for item in state["artifacts"] if item["artifact_kind"] == "worktree"
    ):
        worktree_path = Path(str(worktree["path"]))
        children = [
            item
            for item in state["artifacts"]
            if item["artifact_kind"] == "worktree-path"
            and item["origin"] == str(worktree_path)
        ]
        if not children:
            continue
        files: list[dict[str, Any]] = []
        try:
            staged = git(worktree_path, "diff", "--binary", "--cached", "--no-ext-diff")
            unstaged = git(worktree_path, "diff", "--binary", "--no-ext-diff")
            delta = (
                canonical(
                    {
                        "staged": base64.b64encode(staged).decode("ascii"),
                        "unstaged": base64.b64encode(unstaged).decode("ascii"),
                    }
                )
                + b"\n"
            )
            if len(delta) > MAX_PRESERVATION_FILE_BYTES:
                raise CleanupError("worktree delta package is oversized")
            files.append(
                {
                    "artifact_id": worktree["artifact_id"],
                    "mode": "100600",
                    "path": ".git-deltas.json",
                    "payload": delta,
                }
            )
        except CleanupError:
            pass
        for child in children:
            relative = safe_status_path(str(child["path"]))
            if relative is None:
                continue
            candidate = worktree_path.joinpath(*relative.parts)
            try:
                payload, mode = read_regular_file(candidate)
            except CleanupError:
                continue
            files.append(
                {
                    "artifact_id": child["artifact_id"],
                    "mode": mode,
                    "path": str(relative),
                    "payload": payload,
                }
            )
        if not files:
            continue
        package_id = artifact_id(
            "package", [state["source_root"], worktree["artifact_id"]]
        )
        package, entries = write_local_package(directory, package_id, files)
        packages.append(package)
        byte_entries.extend(entries)
        for item in files:
            proof_roots.setdefault(item["artifact_id"], []).append(
                restore_drill(item["payload"])
            )

    object_entries.sort(key=lambda item: item["artifact_id"])
    packages.sort(key=lambda item: item["package_id"])
    byte_entries.sort(key=lambda item: item["artifact_id"])
    restore_receipts = [
        {
            "artifact_id": key,
            "disposable_root": sha256(sorted(values)),
            "restored_root": sha256(sorted(values)),
            "status": "passed",
        }
        for key, values in sorted(proof_roots.items())
    ]
    preservation_root = sha256(
        {
            "byte_entries": byte_entries,
            "object_entries": object_entries,
            "packages": packages,
            "plan_root": plan["plan_root"],
            "restore_receipts": restore_receipts,
        }
    )
    preservation = base_record(
        "preservation",
        "preserve",
        "passed",
        state["identity"],
        state["run_id"],
        state["source_root"],
        state["created_at"],
    )
    preservation.update(
        {
            "byte_entries": byte_entries,
            "object_entries": object_entries,
            "packages": packages,
            "plan_root": plan["plan_root"],
            "preservation_root": preservation_root,
            "restore_receipts": restore_receipts,
        }
    )
    finish_record(preservation)

    candidates = [
        {
            "candidate_id": f"candidate-{item['artifact_id']}",
            "source_artifact_ids": [item["artifact_id"]],
            "status": "unknown",
        }
        for item in state["artifacts"]
    ]
    byte_roots = {item["artifact_id"]: item["sha256"] for item in byte_entries}
    object_roots = {item["artifact_id"]: item["object_id"] for item in object_entries}
    surfaces: list[dict[str, Any]] = []
    for artifact in state["artifacts"]:
        evidence_refs = []
        if artifact["artifact_id"] in byte_roots:
            evidence_refs.append(f"byte:{byte_roots[artifact['artifact_id']]}")
        if artifact["artifact_id"] in object_roots:
            evidence_refs.append(f"object:{object_roots[artifact['artifact_id']]}")
        if not evidence_refs:
            evidence_refs.append("retained:unknown")
        for kind in surface_kinds(artifact["path"]):
            surfaces.append(
                {
                    "candidate_id": f"candidate-{artifact['artifact_id']}",
                    "evidence_refs": evidence_refs,
                    "surface_id": artifact_id(
                        "surface", [artifact["artifact_id"], kind]
                    ),
                    "surface_kind": kind,
                }
            )
    surfaces.sort(key=lambda item: item["surface_id"])
    unknowns = [
        {
            "reason": "functional coverage requires independent semantic evidence",
            "revisit_trigger": "before any non-retain disposition",
            "subject_id": item["candidate_id"],
        }
        for item in candidates
    ]
    review_requirements = [
        {
            "candidate_id": item["candidate_id"],
            "reason": "required before integration or supersession",
            "review_kind": "semantic-supersession",
        }
        for item in candidates
    ]
    coverage_root = sha256(
        {
            "candidates": candidates,
            "plan_root": plan["plan_root"],
            "preservation_root": preservation_root,
            "review_requirements": review_requirements,
            "surfaces": surfaces,
            "unknowns": unknowns,
        }
    )
    coverage = base_record(
        "capability-coverage",
        "preserve",
        "passed",
        state["identity"],
        state["run_id"],
        state["source_root"],
        state["created_at"],
    )
    coverage.update(
        {
            "candidates": candidates,
            "coverage_root": coverage_root,
            "plan_root": plan["plan_root"],
            "preservation_root": preservation_root,
            "review_requirements": review_requirements,
            "surfaces": surfaces,
            "unknowns": unknowns,
        }
    )
    return preservation, finish_record(coverage)


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


def write_immutable_bytes(path: Path, payload: bytes, limit: int) -> None:
    if len(payload) > limit:
        raise CleanupError(f"immutable artifact exceeds {limit} bytes")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        existing, _ = read_regular_file(path)
        if len(existing) > limit or existing != payload:
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


def write_immutable(path: Path, value: dict[str, Any]) -> None:
    write_immutable_bytes(path, canonical(value) + b"\n", MAX_RECORD_BYTES)


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


def read_record(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > MAX_RECORD_BYTES
    ):
        raise CleanupError(f"record is missing or unsafe: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupError(f"record is malformed: {path.name}") from exc
    if not isinstance(value, dict):
        raise CleanupError(f"record is not an object: {path.name}")
    validate_record(value)
    projection = dict(value)
    record_root = projection.pop("record_root", None)
    if record_root != sha256(projection):
        raise CleanupError(f"record root differs: {path.name}")
    return value


def verify_local_packages(
    directory: Path,
    preservation: dict[str, Any],
) -> None:
    package_rows: dict[str, dict[str, Any]] = {}
    for package in preservation["packages"]:
        package_path = normalized_absolute(package["path"])
        if (
            package_path.parent != directory / "packages"
            or package_path.name != package["package_id"]
            or not package_path.is_dir()
        ):
            raise CleanupError("preservation package escaped run directory")
        manifest_payload, _ = read_regular_file(package_path / "manifest.json")
        if sha256(manifest_payload) != package["package_root"]:
            raise CleanupError("preservation package root differs")
        try:
            manifest = json.loads(manifest_payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CleanupError("preservation package manifest is malformed") from exc
        if canonical(manifest) + b"\n" != manifest_payload:
            raise CleanupError("preservation package manifest is noncanonical")
        if set(manifest) != {
            "artifact_ids",
            "files",
            "kind",
            "schema_version",
        } or not isinstance(manifest["files"], list):
            raise CleanupError("preservation package manifest fields differ")
        if (
            manifest["kind"] != "local-preservation-package"
            or manifest["schema_version"] != SCHEMA_VERSION
        ):
            raise CleanupError("preservation package manifest version differs")
        if manifest.get("artifact_ids") != package["artifact_ids"]:
            raise CleanupError("preservation package artifact set differs")
        expected_names = {"manifest.json"}
        for row in manifest.get("files", []):
            if not isinstance(row, dict) or set(row) != {
                "artifact_id",
                "mode",
                "name",
                "path",
                "sha256",
                "size",
            }:
                raise CleanupError("preservation package row is malformed")
            if row["artifact_id"] in package_rows:
                raise CleanupError("artifact appears in multiple package files")
            if row["name"] != f"{row['artifact_id']}.bin":
                raise CleanupError("preservation package filename differs")
            expected_names.add(row["name"])
            payload, _ = read_regular_file(package_path / row["name"])
            if len(payload) != row["size"] or sha256(payload) != row["sha256"]:
                raise CleanupError("preservation package bytes differ")
            package_rows[row["artifact_id"]] = row
        if {item.name for item in package_path.iterdir()} != expected_names:
            raise CleanupError("preservation package file set differs")
    for entry in preservation["byte_entries"]:
        row = package_rows.get(entry["artifact_id"])
        if row is None or any(
            entry[name] != row[name] for name in ("mode", "path", "sha256", "size")
        ):
            raise CleanupError("preservation byte entry differs from package")
    if set(package_rows) != {
        item["artifact_id"] for item in preservation["byte_entries"]
    }:
        raise CleanupError("preservation package contains unbound bytes")


def verify_preservation_records(
    directory: Path,
    inventory: dict[str, Any],
    plan: dict[str, Any],
    preservation: dict[str, Any],
    coverage: dict[str, Any],
) -> None:
    if preservation["plan_root"] != plan["plan_root"]:
        raise CleanupError("preservation plan binding differs")
    expected_preservation_root = sha256(
        {
            name: preservation[name]
            for name in (
                "byte_entries",
                "object_entries",
                "packages",
                "plan_root",
                "restore_receipts",
            )
        }
    )
    if preservation["preservation_root"] != expected_preservation_root:
        raise CleanupError("preservation semantic root differs")
    verify_local_packages(directory, preservation)
    inventory_by_id = {item["artifact_id"]: item for item in inventory["artifacts"]}
    for entry in preservation["object_entries"]:
        artifact = inventory_by_id.get(entry["artifact_id"])
        if artifact is None or artifact["object_id"] != entry["object_id"]:
            raise CleanupError("preserved object differs from inventory")
    if any(
        entry["artifact_id"] not in inventory_by_id
        for entry in preservation["byte_entries"]
    ):
        raise CleanupError("preserved bytes differ from inventory")
    if any(
        artifact_id not in inventory_by_id
        for package in preservation["packages"]
        for artifact_id in package["artifact_ids"]
    ):
        raise CleanupError("preservation package differs from inventory")
    if any(
        item["status"] != "passed" or item["disposable_root"] != item["restored_root"]
        for item in preservation["restore_receipts"]
    ):
        raise CleanupError("preservation restore receipt differs")
    if (
        coverage["plan_root"] != plan["plan_root"]
        or coverage["preservation_root"] != preservation["preservation_root"]
    ):
        raise CleanupError("capability coverage binding differs")
    expected_coverage_root = sha256(
        {
            name: coverage[name]
            for name in (
                "candidates",
                "plan_root",
                "preservation_root",
                "review_requirements",
                "surfaces",
                "unknowns",
            )
        }
    )
    if coverage["coverage_root"] != expected_coverage_root:
        raise CleanupError("capability coverage semantic root differs")
    inventory_ids = {item["artifact_id"] for item in inventory["artifacts"]}
    covered_list = [
        artifact_id
        for candidate in coverage["candidates"]
        for artifact_id in candidate["source_artifact_ids"]
    ]
    covered_ids = set(covered_list)
    unknown_ids = {item["subject_id"] for item in coverage["unknowns"]}
    candidate_ids = {item["candidate_id"] for item in coverage["candidates"]}
    if (
        inventory_ids != covered_ids
        or len(covered_list) != len(inventory_ids)
        or any(
            item["status"] != "unknown" or item["candidate_id"] not in unknown_ids
            for item in coverage["candidates"]
        )
        or unknown_ids != candidate_ids
        or {item["candidate_id"] for item in coverage["review_requirements"]}
        != candidate_ids
        or any(
            item["candidate_id"] not in candidate_ids for item in coverage["surfaces"]
        )
    ):
        raise CleanupError("capability coverage is not exhaustive and retained")


def restore_artifact(
    directory: Path, artifact_id_value: str, destination: str
) -> dict[str, Any]:
    verified = verify_directory(directory)
    if verified["status"] != "preservation-retained-unknown":
        raise CleanupError("verified preservation is unavailable")
    preservation = read_record(directory / "preservation.json")
    entry = next(
        (
            item
            for item in preservation["byte_entries"]
            if item["artifact_id"] == artifact_id_value
        ),
        None,
    )
    package = next(
        (
            item
            for item in preservation["packages"]
            if artifact_id_value in item["artifact_ids"]
        ),
        None,
    )
    if entry is None or package is None:
        raise CleanupError("artifact has no local byte package")
    package_path = normalized_absolute(package["path"])
    payload, _ = read_regular_file(package_path / f"{artifact_id_value}.bin")
    if len(payload) != entry["size"] or sha256(payload) != entry["sha256"]:
        raise CleanupError("artifact package bytes differ")
    restored = normalized_absolute(destination, must_exist=False)
    if restored.exists() or not restored.parent.is_dir():
        raise CleanupError("restore destination must be a new file")
    write_immutable_bytes(restored, payload, MAX_PRESERVATION_FILE_BYTES)
    try:
        os.chmod(restored, int(entry["mode"], 8) & 0o7777)
    except (OSError, ValueError) as exc:
        raise CleanupError("restored mode could not be applied") from exc
    restored_payload, restored_mode = read_regular_file(restored)
    if restored_payload != payload or restored_mode[-4:] != entry["mode"][-4:]:
        raise CleanupError("restored artifact differs")
    return {
        "artifact_id": artifact_id_value,
        "mode": entry["mode"],
        "path": str(restored),
        "sha256": entry["sha256"],
        "status": "restored",
    }


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


def verify_directory(
    directory: Path, *, allow_incomplete_preservation: bool = False
) -> dict[str, Any]:
    directory = normalized_absolute(str(directory))
    if not directory.is_dir() or not RUN_ID.fullmatch(directory.name):
        raise CleanupError("run directory is invalid")
    source = read_record(directory / "source-snapshot.json")
    inventory = read_record(directory / "inventory.json")
    for record in (inventory,):
        if any(
            record[name] != source[name]
            for name in (
                "created_at",
                "repository_identity",
                "run_id",
                "source_snapshot_root",
            )
        ):
            raise CleanupError("inventory run binding differs")
    if inventory["source_snapshot_root"] != source["source_snapshot_root"]:
        raise CleanupError("inventory source binding differs")
    if inventory["artifact_count"] != len(inventory["artifacts"]):
        raise CleanupError("inventory count differs")
    records = {"inventory": inventory, "source-snapshot": source}
    plan_path = directory / "plan.json"
    if plan_path.exists():
        plan = read_record(plan_path)
        if any(
            plan[name] != source[name]
            for name in (
                "created_at",
                "repository_identity",
                "run_id",
                "source_snapshot_root",
            )
        ):
            raise CleanupError("plan run binding differs")
        if plan["inventory_root"] != inventory["inventory_root"]:
            raise CleanupError("plan inventory binding differs")
        if plan["source_snapshot_root"] != source["source_snapshot_root"]:
            raise CleanupError("plan source binding differs")
        records["plan"] = plan
    preservation_path = directory / "preservation.json"
    coverage_path = directory / "capability-coverage.json"
    if (
        preservation_path.exists() != coverage_path.exists()
        and not allow_incomplete_preservation
    ):
        raise CleanupError("preservation record pair is incomplete")
    if preservation_path.exists() and coverage_path.exists():
        if "plan" not in records:
            raise CleanupError("preservation requires plan")
        preservation = read_record(preservation_path)
        coverage = read_record(coverage_path)
        for record in (preservation, coverage):
            if any(
                record[name] != source[name]
                for name in (
                    "created_at",
                    "repository_identity",
                    "run_id",
                    "source_snapshot_root",
                )
            ):
                raise CleanupError("preservation run binding differs")
        verify_preservation_records(
            directory, inventory, records["plan"], preservation, coverage
        )
        records["preservation"] = preservation
        records["capability-coverage"] = coverage
    status_path = directory / "status.json"
    if status_path.exists():
        status = read_record(status_path)
        if any(
            status[name] != source[name]
            for name in (
                "created_at",
                "repository_identity",
                "run_id",
                "source_snapshot_root",
            )
        ):
            raise CleanupError("status run binding differs")
        records["status"] = status
    return {
        "record_roots": {
            key: value["record_root"] for key, value in sorted(records.items())
        },
        "run_dir": str(directory),
        "run_id": source["run_id"],
        "source_snapshot_root": source["source_snapshot_root"],
        "status": (
            "preservation-retained-unknown"
            if preservation_path.exists() and coverage_path.exists()
            else "retained-deferred-proof"
        ),
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
    preserve = commands.add_parser("preserve")
    preserve.add_argument("--run-dir", required=True)
    common_parser(preserve)
    restore = commands.add_parser("restore")
    restore.add_argument("--run-dir", required=True)
    restore.add_argument("--artifact-id", required=True)
    restore.add_argument("--destination", required=True)
    status = commands.add_parser("status")
    status.add_argument("--run-dir", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--run-dir", required=True)
    common_parser(verify)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.command == "restore":
            result = restore_artifact(
                normalized_absolute(args.run_dir), args.artifact_id, args.destination
            )
            print(canonical(result).decode("utf-8"))
            return 0
        if args.command in {"status", "verify"}:
            result = verify_directory(Path(args.run_dir))
            if args.command == "verify":
                current = build_state(args)
                if current["source_root"] != result["source_snapshot_root"]:
                    raise CleanupError("source changed; successor plan required")
                result["current"] = "bounded-observations-only"
            else:
                directory = Path(result["run_dir"])
                status_path = directory / "status.json"
                if status_path.exists():
                    status = read_record(status_path)
                    preserved = result["status"] == "preservation-retained-unknown"
                    result.update(
                        {
                            "active_holds": status["active_holds"],
                            "current_phase": "preserve"
                            if preserved
                            else status["current_phase"],
                            "next_action": (
                                "obtain-independent-semantic-coverage-before-non-retain-disposition"
                                if preserved
                                else status["next_action"]
                            ),
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

        if args.command == "preserve":
            directory = normalized_absolute(args.run_dir)
            verified = verify_directory(directory, allow_incomplete_preservation=True)
            state = build_state(args)
            if state["source_root"] != verified["source_snapshot_root"]:
                raise CleanupError("source changed; successor plan required")
            if run_directory(args, state) != directory:
                raise CleanupError("run directory does not match current source")
            source = read_record(directory / "source-snapshot.json")
            plan = read_record(directory / "plan.json")
            state["created_at"] = source["created_at"]
            if build_plan(state)["plan_root"] != plan["plan_root"]:
                raise CleanupError("plan changed; successor plan required")
            preservation, coverage = build_preservation(state, plan, directory)
            closing = build_state(args)
            if closing["source_root"] != state["source_root"]:
                raise CleanupError(
                    "source changed while preserving; successor plan required"
                )
            write_immutable(directory / "preservation.json", preservation)
            write_immutable(directory / "capability-coverage.json", coverage)
            result = verify_directory(directory)
            result.update(
                {
                    "package_count": len(preservation["packages"]),
                    "preservation_root": preservation["preservation_root"],
                    "unknown_count": len(coverage["unknowns"]),
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
