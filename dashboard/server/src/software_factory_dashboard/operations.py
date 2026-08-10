from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import RLock
import tomllib
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence

from .catalog import ProjectRecord


DASHBOARD_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SUPERVISION_ROOT = Path.home() / ".codex" / "supervision" / "tracker-runs"
DEFAULT_AUTOMATIONS_ROOT = Path.home() / ".codex" / "automations"
DEFAULT_SUPERVISION_OWNER = (
    DASHBOARD_REPOSITORY_ROOT
    / "supervise-tracker-runs"
    / "scripts"
    / "supervision_log.py"
)
DEFAULT_WEEKLY_OWNER = DEFAULT_SUPERVISION_OWNER.with_name("weekly_report.py")
DEFAULT_TERMINAL_OWNER = DEFAULT_SUPERVISION_OWNER.with_name("terminal_report.py")
DEFAULT_EVOLUTION_OWNER = DEFAULT_SUPERVISION_OWNER.with_name("factory_evolution.py")

MAX_TARGETS = 250
MAX_AUTOMATIONS = 500
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_AUTOMATION_BYTES = 256 * 1024
MAX_REPORT_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_TIMELINE_RECORDS = 2_500
MAX_RECENT_RECORDS = 250
MAX_REPORT_SETS = 250
MAX_CACHE_ENTRIES = 256
MAX_METRIC_HISTORY_ROWS = 1_000
OWNER_TIMEOUT_SECONDS = 30
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

ROLE_THREAD_KEYS = (
    "watcher_thread_id",
    "base_reviewer_thread_id",
    "reviewer_thread_id",
    "notice_reviewer_thread_id",
    "fix_executor_thread_id",
    "gmail_gate_thread_id",
    "gmail_processor_thread_id",
    "roundup_thread_id",
)
ROLE_AUTOMATION_KEYS = {
    "watcher_thread_id": "routine_automation_id",
    "reviewer_thread_id": "meta_automation_id",
    "gmail_gate_thread_id": "gmail_poll_automation_id",
    "roundup_thread_id": "roundup_automation_id",
}
ROLE_LABELS = {
    "watcher_thread_id": "Routine watcher",
    "base_reviewer_thread_id": "Semantic reviewer",
    "reviewer_thread_id": "Effectiveness reviewer",
    "notice_reviewer_thread_id": "Incident outcome reviewer",
    "fix_executor_thread_id": "Fix executor",
    "gmail_gate_thread_id": "Gmail reply gate",
    "gmail_processor_thread_id": "Gmail reply processor",
    "roundup_thread_id": "Report writer",
}
SEMANTIC_KINDS = {
    "checkpoint-review",
    "meta-review",
    "resolution",
}
DECISION_CONCLUSION_PHASES = {"resolved", "safe-deferred"}
ACTIVITY_KINDS = {
    "check",
    "escalation",
    "steer",
    "incident",
    "resolution",
    "checkpoint-review",
    "meta-review",
    "policy-change",
    "notification",
    "inbound-message",
    "roundup",
    "decision",
    "successor-transition",
    "lifecycle",
}
PATH_BINDING_KEYS = {
    "cwd",
    "project_root",
    "repository_root",
    "tracker_path",
    "tracker_source_path",
}


class OperationsProjectionError(ValueError):
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
class TargetEvidence:
    target_thread_id: str
    directory: Path
    policy: dict[str, Any]
    policy_history: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    active_events: tuple[dict[str, Any], ...]
    roots_by_policy: dict[str, str]
    fingerprint: str
    cache_key: tuple[Any, ...]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _observed_at() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _bounded(value: Any, maximum: int = 2_400) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= maximum:
        return text
    return text[: maximum - 1].rstrip() + "…"


def _event_time(value: Mapping[str, Any]) -> datetime | None:
    raw = value.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _milliseconds_timestamp(value: Any) -> str | None:
    if not isinstance(value, int) or value < 0:
        return None
    try:
        stamp = datetime.fromtimestamp(value / 1_000, UTC)
    except (OverflowError, OSError, ValueError):
        return None
    return stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _stat_key(path: Path) -> tuple[Any, ...]:
    try:
        metadata = path.lstat()
    except OSError:
        return (str(path), None)
    return (
        str(path),
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        path.is_symlink(),
    )


def _read_bounded(path: Path, maximum: int) -> bytes:
    try:
        if path.is_symlink():
            raise OperationsProjectionError(
                "source_symlink_rejected",
                f"Source file must not be a symlink: {path.name}.",
            )
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
    except OperationsProjectionError:
        raise
    except OSError as exc:
        raise OperationsProjectionError(
            "source_read_failed",
            f"Source file could not be read: {path.name}: {exc}",
            status=503,
            retryable=True,
        ) from exc
    if len(data) > maximum:
        raise OperationsProjectionError(
            "source_size_limit",
            f"Source file exceeds its bounded read limit: {path.name}.",
            status=413,
        )
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise OperationsProjectionError(
            "source_changed_during_read",
            f"Source file changed while it was read: {path.name}.",
            status=409,
            retryable=True,
        )
    return data


def _git_owning_revision(path: Path) -> str | None:
    repository = DASHBOARD_REPOSITORY_ROOT
    try:
        relative = path.resolve(strict=True).relative_to(repository.resolve(strict=True))
    except (OSError, ValueError):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "log", "-1", "--format=%H", "--", relative.as_posix()],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", value) else None


def _owner_sha256(path: Path) -> str:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise OperationsProjectionError(
            "owner_unavailable",
            f"Maintained owner is unavailable: {path.name}: {exc}",
            status=503,
            retryable=True,
        ) from exc
    return sha256(_read_bounded(resolved, 4 * 1024 * 1024)).hexdigest()


def _owner_revision(path: Path, identity: str) -> dict[str, Any]:
    return {
        "identity": identity,
        "path": str(path.resolve()),
        "sha256": _owner_sha256(path),
        "owning_revision": _git_owning_revision(path),
    }


def _load_module(path: Path, name: str) -> ModuleType:
    resolved = path.resolve(strict=True)
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        raise OperationsProjectionError(
            "owner_unavailable", f"Maintained owner cannot be loaded: {resolved.name}.", status=503
        )
    module = importlib.util.module_from_spec(spec)
    scripts_path = str(resolved.parent)
    inserted = scripts_path not in sys.path
    if inserted:
        sys.path.insert(0, scripts_path)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise OperationsProjectionError(
            "owner_unavailable",
            f"Maintained owner failed to load: {resolved.name}: {exc}",
            status=503,
            retryable=True,
        ) from exc
    finally:
        if inserted and sys.path and sys.path[0] == scripts_path:
            sys.path.pop(0)
    return module


def _event_projection(
    item: Mapping[str, Any],
    *,
    mission_root: str,
    source_path: Path,
    line: int,
) -> dict[str, Any]:
    scalar_fields = (
        "record_id",
        "timestamp",
        "kind",
        "status",
        "severity",
        "category",
        "active_block",
        "checkpoint",
        "state_fingerprint",
        "incident_id",
        "decision_id",
        "transition_id",
        "phase",
        "classification",
        "safe_frontier",
        "outcome",
        "model",
        "reasoning",
        "summary",
        "action",
        "resolution",
        "notice_disposition",
        "resolution_owner",
        "user_action_required",
        "policy_sha256",
        "record_sha256",
    )
    projected = {field: _bounded(item.get(field)) for field in scalar_fields}
    evidence = item.get("evidence")
    projected["evidence"] = (
        [_bounded(entry, 800) or "" for entry in evidence[:30]]
        if isinstance(evidence, list)
        else []
    )
    projected["mission_root"] = mission_root
    projected["actor"] = {
        "status": "unavailable",
        "role": None,
        "thread_id": None,
        "reason": (
            "The canonical supervision record does not identify its emitting task or role; "
            "model and reasoning fields are not used as actor identity."
        ),
    }
    projected["source"] = {
        "path": str(source_path),
        "line": line,
        "read_only": True,
    }
    return projected


def _record_ref(item: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "record_id": _bounded(item.get("record_id")),
        "timestamp": _bounded(item.get("timestamp")),
        "kind": _bounded(item.get("kind")),
        "status": _bounded(item.get("status")),
        "severity": _bounded(item.get("severity")),
        "category": _bounded(item.get("category")),
        "summary": _bounded(item.get("summary"), 1_000),
    }


class OperationsProjectionService:
    """Read canonical supervision families without becoming an operational owner."""

    def __init__(
        self,
        *,
        supervision_root: Path = DEFAULT_SUPERVISION_ROOT,
        automations_root: Path = DEFAULT_AUTOMATIONS_ROOT,
        supervision_owner: Path = DEFAULT_SUPERVISION_OWNER,
        weekly_owner: Path = DEFAULT_WEEKLY_OWNER,
        terminal_owner: Path = DEFAULT_TERMINAL_OWNER,
        evolution_owner: Path = DEFAULT_EVOLUTION_OWNER,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.supervision_root = supervision_root.expanduser().resolve()
        self.automations_root = automations_root.expanduser().resolve()
        self.supervision_owner = supervision_owner.resolve()
        self.weekly_owner = weekly_owner.resolve()
        self.terminal_owner = terminal_owner.resolve()
        self.evolution_owner = evolution_owner.resolve()
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._modules: dict[str, tuple[tuple[Any, ...], ModuleType]] = {}
        self._target_cache: OrderedDict[str, TargetEvidence] = OrderedDict()
        self._automation_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        self._report_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

    def owner_revisions(self) -> dict[str, dict[str, Any]]:
        return {
            "supervision": _owner_revision(
                self.supervision_owner,
                "supervise-tracker-runs/scripts/supervision_log.py",
            ),
            "weekly_report": _owner_revision(
                self.weekly_owner,
                "supervise-tracker-runs/scripts/weekly_report.py",
            ),
            "terminal_report": _owner_revision(
                self.terminal_owner,
                "supervise-tracker-runs/scripts/terminal_report.py",
            ),
            "factory_evolution": _owner_revision(
                self.evolution_owner,
                "supervise-tracker-runs/scripts/factory_evolution.py",
            ),
        }

    def readiness(self) -> dict[str, Any]:
        owners = self.owner_revisions()
        targets = self._target_directories()
        automation_status = (
            "available"
            if self.automations_root.is_dir() and not self.automations_root.is_symlink()
            else "unavailable"
        )
        return {
            "status": "available",
            "target_count": len(targets),
            "automation_status": automation_status,
            "owners": owners,
            "revision": _digest(
                {
                    "owners": {key: value["sha256"] for key, value in owners.items()},
                    "targets": [directory.name for directory in targets],
                    "automation_status": automation_status,
                }
            ),
        }

    def _module(self, family: str) -> ModuleType:
        paths = {
            "supervision": self.supervision_owner,
            "weekly": self.weekly_owner,
        }
        path = paths[family]
        before = _stat_key(path)
        with self._lock:
            existing = self._modules.get(family)
            if existing is not None and existing[0] == before:
                return existing[1]
            module = _load_module(
                path,
                f"software_factory_dashboard_{family}_owner_{abs(hash(before))}",
            )
            after = _stat_key(path)
            if before != after:
                raise OperationsProjectionError(
                    "owner_changed_during_load",
                    f"Maintained {family} owner changed while it was loaded; retry from its new revision.",
                    status=409,
                    retryable=True,
                )
            self._modules[family] = (after, module)
            return module

    def _target_directories(self) -> list[Path]:
        if not self.supervision_root.exists():
            return []
        if not self.supervision_root.is_dir() or self.supervision_root.is_symlink():
            raise OperationsProjectionError(
                "supervision_root_invalid",
                "The configured supervision root is not a canonical directory.",
                status=503,
            )
        directories = [
            item
            for item in self.supervision_root.iterdir()
            if item.is_dir() and not item.is_symlink() and SAFE_ID.fullmatch(item.name)
        ]
        if len(directories) > MAX_TARGETS:
            raise OperationsProjectionError(
                "supervision_target_limit",
                f"The supervision root exceeds the {MAX_TARGETS}-target projection limit.",
                status=413,
            )
        return sorted(directories, key=lambda item: item.name)

    @staticmethod
    def _target_key(directory: Path) -> tuple[Any, ...]:
        return tuple(
            _stat_key(directory / name)
            for name in ("policy.json", "policy-history.jsonl", "events.jsonl")
        )

    def _load_target(self, directory: Path) -> tuple[TargetEvidence, str]:
        target = directory.name
        before = self._target_key(directory)
        with self._lock:
            cached = self._target_cache.get(target)
            if cached is not None and cached.cache_key == before:
                self._target_cache.move_to_end(target)
                return cached, "hit"
        if before[0][-1] is None:
            raise OperationsProjectionError(
                "supervision_policy_unavailable",
                "Supervision target lacks policy.json.",
                status=422,
            )
        for name in ("policy.json", "policy-history.jsonl", "events.jsonl"):
            path = directory / name
            if path.is_symlink():
                raise OperationsProjectionError(
                    "supervision_source_symlink_rejected",
                    f"Supervision source must not be a symlink: {name}.",
                    status=422,
                )
            if path.exists() and not path.is_file():
                raise OperationsProjectionError(
                    "supervision_source_invalid",
                    f"Supervision source is not a regular file: {name}.",
                    status=422,
                )
            if path.exists() and path.stat().st_size > MAX_LEDGER_BYTES:
                raise OperationsProjectionError(
                    "supervision_ledger_size_limit",
                    f"{name} exceeds the bounded projection limit.",
                    status=413,
                )
        owner = self._module("supervision")
        args = argparse.Namespace(root=str(self.supervision_root), target_thread=target)
        try:
            owner_directory, policy = owner.load_policy(args)
            policy_history = owner.events(owner_directory / "policy-history.jsonl")
            all_events = owner.events(owner_directory / "events.jsonl")
            roots_by_policy = owner.policy_mission_roots(owner_directory)
            active_events = owner.mission_scoped_events(owner_directory, policy, all_events)
        except Exception as exc:
            code = "supervision_integrity_failed"
            raise OperationsProjectionError(code, str(exc), status=422) from exc
        after = self._target_key(directory)
        if before != after:
            raise OperationsProjectionError(
                "supervision_changed_during_projection",
                "Supervision source changed during validation; retry from its new root.",
                status=409,
                retryable=True,
            )
        fingerprint = _digest(
            {
                "policy_sha256": policy.get("policy_sha256"),
                "policy_history_head": (
                    policy_history[-1].get("record_sha256") if policy_history else None
                ),
                "policy_history_count": len(policy_history),
                "event_head": all_events[-1].get("record_sha256") if all_events else None,
                "event_count": len(all_events),
            }
        )
        evidence = TargetEvidence(
            target_thread_id=target,
            directory=directory,
            policy=policy,
            policy_history=tuple(policy_history),
            events=tuple(all_events),
            active_events=tuple(active_events),
            roots_by_policy=roots_by_policy,
            fingerprint=fingerprint,
            cache_key=after,
        )
        with self._lock:
            self._target_cache[target] = evidence
            self._target_cache.move_to_end(target)
            while len(self._target_cache) > MAX_CACHE_ENTRIES:
                self._target_cache.popitem(last=False)
        return evidence, "miss"

    def _load_automation(self, automation_id: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(automation_id):
            return {
                "id": automation_id,
                "status": "unavailable",
                "error": {
                    "code": "automation_id_invalid",
                    "message": "Policy references an invalid automation ID.",
                    "retryable": False,
                },
            }
        path = self.automations_root / automation_id / "automation.toml"
        key = _stat_key(path)
        with self._lock:
            cached = self._automation_cache.get(key)
            if cached is not None:
                self._automation_cache.move_to_end(key)
                return dict(cached)
        try:
            raw = _read_bounded(path, MAX_AUTOMATION_BYTES)
            value = tomllib.loads(raw.decode("utf-8"))
            expected = {
                "version",
                "id",
                "kind",
                "name",
                "prompt",
                "status",
                "rrule",
                "target_thread_id",
                "created_at",
                "updated_at",
            }
            if set(value) != expected or value.get("id") != automation_id:
                raise OperationsProjectionError(
                    "automation_manifest_invalid",
                    "Automation manifest shape or identity differs from the frozen contract.",
                    status=422,
                )
            if not isinstance(value.get("prompt"), str):
                raise OperationsProjectionError(
                    "automation_manifest_invalid",
                    "Automation prompt field is malformed.",
                    status=422,
                )
            result = {
                "id": automation_id,
                "status": "available",
                "name": _bounded(value["name"], 160),
                "kind": _bounded(value["kind"], 80),
                "owner_status": _bounded(value["status"], 40),
                "rrule": _bounded(value["rrule"], 300),
                "target_thread_id": _bounded(value["target_thread_id"], 160),
                "created_at": _milliseconds_timestamp(value["created_at"]),
                "updated_at": _milliseconds_timestamp(value["updated_at"]),
                "next_scheduled_at": None,
                "manifest_sha256": sha256(raw).hexdigest(),
                "source_path": str(path),
                "limitations": [
                    "The automation owner exposes schedule and enabled state here, but no canonical next occurrence or wake receipt.",
                    "Automation prompt content is deliberately omitted.",
                ],
                "error": None,
            }
        except (OperationsProjectionError, OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            error = exc if isinstance(exc, OperationsProjectionError) else OperationsProjectionError(
                "automation_unavailable", str(exc), status=422
            )
            result = {
                "id": automation_id,
                "status": "unavailable",
                "name": None,
                "kind": None,
                "owner_status": None,
                "rrule": None,
                "target_thread_id": None,
                "created_at": None,
                "updated_at": None,
                "next_scheduled_at": None,
                "manifest_sha256": None,
                "source_path": str(path),
                "limitations": ["Automation source is unavailable; it is not treated as paused or inactive."],
                "error": {
                    "code": error.code,
                    "message": str(error),
                    "retryable": error.retryable,
                },
            }
        with self._lock:
            self._automation_cache[key] = dict(result)
            while len(self._automation_cache) > MAX_CACHE_ENTRIES:
                self._automation_cache.popitem(last=False)
        return result

    def _automation_inventory(self) -> dict[str, dict[str, Any]]:
        def unavailable(code: str, message: str) -> dict[str, dict[str, Any]]:
            return {
                "automation-inventory": {
                    "id": "automation-inventory",
                    "status": "unavailable",
                    "name": None,
                    "kind": None,
                    "owner_status": None,
                    "rrule": None,
                    "target_thread_id": None,
                    "created_at": None,
                    "updated_at": None,
                    "next_scheduled_at": None,
                    "manifest_sha256": None,
                    "source_path": str(self.automations_root),
                    "limitations": [
                        "Automation inventory is unavailable; independent supervision targets remain readable."
                    ],
                    "error": {"code": code, "message": message, "retryable": False},
                }
            }

        if not self.automations_root.exists():
            return {}
        if not self.automations_root.is_dir() or self.automations_root.is_symlink():
            return unavailable(
                "automation_root_invalid",
                "The automation projection root is not a canonical directory.",
            )
        try:
            ids = sorted(
                item.name
                for item in self.automations_root.iterdir()
                if item.is_dir() and not item.is_symlink() and SAFE_ID.fullmatch(item.name)
            )
        except OSError as exc:
            return unavailable("automation_inventory_unavailable", str(exc))
        if len(ids) > MAX_AUTOMATIONS:
            return unavailable(
                "automation_inventory_limit",
                f"Automation inventory exceeds the {MAX_AUTOMATIONS}-manifest projection limit.",
            )
        return {automation_id: self._load_automation(automation_id) for automation_id in ids}

    @staticmethod
    def _path_binding_values(value: Any) -> list[tuple[str, str]]:
        matches: list[tuple[str, str]] = []

        def visit(current: Any) -> None:
            if isinstance(current, Mapping):
                for key, item in current.items():
                    if key in PATH_BINDING_KEYS and isinstance(item, str) and item.startswith("/"):
                        matches.append((str(key), item))
                    elif isinstance(item, (Mapping, list, tuple)):
                        visit(item)
            elif isinstance(current, (list, tuple)):
                for item in current:
                    visit(item)

        visit(value)
        return matches

    def _project_binding(
        self, evidence: TargetEvidence, projects: Sequence[ProjectRecord]
    ) -> dict[str, Any]:
        candidates: dict[str, list[dict[str, str]]] = {}
        sources: list[tuple[str, str, str]] = []
        for key, value in self._path_binding_values(evidence.policy):
            sources.append(("policy", key, value))
        for event in evidence.active_events:
            record_id = str(event.get("record_id", "unknown"))
            for key, value in self._path_binding_values(event):
                sources.append((record_id, key, value))
        for source_record, key, raw_path in sources:
            path = Path(raw_path).expanduser()
            try:
                resolved = path.resolve(strict=False)
            except (OSError, RuntimeError):
                continue
            for project in projects:
                root = Path(project.root)
                try:
                    resolved.relative_to(root)
                except ValueError:
                    continue
                candidates.setdefault(project.id, []).append(
                    {"source_record": source_record, "field": key, "value": raw_path}
                )
        if len(candidates) == 1:
            project_id = next(iter(candidates))
            return {
                "status": "bound",
                "project_id": project_id,
                "evidence": candidates[project_id],
                "limitations": [],
            }
        if len(candidates) > 1:
            return {
                "status": "ambiguous",
                "project_id": None,
                "evidence": [entry for rows in candidates.values() for entry in rows],
                "limitations": [
                    "Canonical path-bearing records resolve to more than one registered project; no friendly-label join was used."
                ],
            }
        return {
            "status": "unassigned",
            "project_id": None,
            "evidence": [],
            "limitations": [
                "No canonical policy or active supervision record currently binds this target; task cwd remains independently available from /api/v1/tasks."
            ],
        }

    @staticmethod
    def _mission_root(evidence: TargetEvidence, item: Mapping[str, Any]) -> str:
        return evidence.roots_by_policy.get(str(item.get("policy_sha256", "")), "unbound")

    def _timeline(self, evidence: TargetEvidence) -> tuple[list[dict[str, Any]], bool]:
        selected = list(evidence.events[-MAX_TIMELINE_RECORDS:])
        offset = len(evidence.events) - len(selected)
        return (
            [
                _event_projection(
                    item,
                    mission_root=self._mission_root(evidence, item),
                    source_path=evidence.directory / "events.jsonl",
                    line=offset + index,
                )
                for index, item in enumerate(selected, start=1)
            ],
            offset > 0,
        )

    def _mission_segments(self, evidence: TargetEvidence) -> list[dict[str, Any]]:
        owner = self._module("supervision")
        active_binding = owner.bound_mission(evidence.policy)
        active_root = (
            str(active_binding["mission_root"])
            if isinstance(active_binding, Mapping)
            else "unbound"
        )
        groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        for item in evidence.events:
            groups.setdefault(self._mission_root(evidence, item), []).append(item)
        if active_root not in groups:
            groups[active_root] = []
        policy_sources: dict[str, tuple[str | None, list[str]]] = {}
        for record in evidence.policy_history:
            policy = record.get("policy")
            if not isinstance(policy, Mapping):
                continue
            binding = owner.bound_mission(dict(policy))
            root = str(binding["mission_root"]) if isinstance(binding, Mapping) else "unbound"
            source_record = (
                str(binding.get("mission_source_record"))
                if isinstance(binding, Mapping) and binding.get("mission_source_record")
                else None
            )
            current = policy_sources.setdefault(root, (source_record, []))
            policy_sha = policy.get("policy_sha256")
            if isinstance(policy_sha, str):
                current[1].append(policy_sha)
        segments: list[dict[str, Any]] = []
        for root, records in groups.items():
            incidents: dict[str, dict[str, Any]] = {}
            for item in records:
                incident_id = item.get("incident_id")
                if incident_id and owner.is_substantive_incident_record(item, str(incident_id)):
                    incidents[str(incident_id)] = item
            lifecycle = [item for item in records if item.get("kind") == "lifecycle"]
            conclusions = [item for item in records if self._is_conclusion(item, owner)]
            source_record, policy_shas = policy_sources.get(root, (None, []))
            first = _event_time(records[0]) if records else None
            last = _event_time(records[-1]) if records else None
            segments.append(
                {
                    "mission_root": root,
                    "mission_source_record": source_record,
                    "posture": "current" if root == active_root else (
                        "unbound-history" if root == "unbound" else "predecessor"
                    ),
                    "policy_sha256s": policy_shas,
                    "first_recorded_at": first.isoformat().replace("+00:00", "Z") if first else None,
                    "last_recorded_at": last.isoformat().replace("+00:00", "Z") if last else None,
                    "event_count": len(records),
                    "incident_count": len(incidents),
                    "open_incident_count": sum(
                        1
                        for incident_id, item in incidents.items()
                        if not owner.is_terminal_incident_record(item, incident_id)
                    ),
                    "conclusion_count": len(conclusions),
                    "terminal_record": _record_ref(lifecycle[-1] if lifecycle else None),
                    "superseded_by": active_root if root != active_root else None,
                }
            )
        return segments

    @staticmethod
    def _is_conclusion(item: Mapping[str, Any], owner: ModuleType) -> bool:
        kind = item.get("kind")
        if kind in SEMANTIC_KINDS:
            return True
        if kind == "decision":
            return item.get("phase") in DECISION_CONCLUSION_PHASES
        if kind == "incident" and item.get("incident_id"):
            return owner.is_terminal_incident_record(item, str(item["incident_id"]))
        if kind == "check" and item.get("category") == owner.OUTCOME_COMPLETION_CATEGORY:
            return True
        return False

    def _active_heads(self, evidence: TargetEvidence) -> dict[str, Any]:
        owner = self._module("supervision")
        incidents: dict[str, dict[str, Any]] = {}
        decisions: dict[str, dict[str, Any]] = {}
        transitions: dict[str, dict[str, Any]] = {}
        lifecycle: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        conclusions: list[dict[str, Any]] = []
        for item in evidence.active_events:
            incident_id = item.get("incident_id")
            if incident_id and owner.is_substantive_incident_record(item, str(incident_id)):
                incidents[str(incident_id)] = item
            if item.get("kind") == "decision" and item.get("decision_id"):
                decisions[str(item["decision_id"])] = item
            if item.get("kind") == "successor-transition" and item.get("transition_id"):
                transitions[str(item["transition_id"])] = item
            if item.get("kind") == "lifecycle":
                lifecycle.append(item)
            if item.get("kind") == "check":
                checks.append(item)
            if self._is_conclusion(item, owner):
                conclusions.append(item)
        return {
            "incidents": incidents,
            "decisions": decisions,
            "transitions": transitions,
            "lifecycle": lifecycle,
            "checks": checks,
            "conclusions": conclusions,
        }

    def _roles(
        self,
        evidence: TargetEvidence,
        automations: Mapping[str, dict[str, Any]],
        duplicate_threads: set[str],
        duplicate_automations: set[str],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        runtime = evidence.policy.get("runtime")
        if not isinstance(runtime, Mapping):
            runtime = {}
        anomalies: list[str] = []
        roles: list[dict[str, Any]] = []
        for thread_key in ROLE_THREAD_KEYS:
            thread_id = runtime.get(thread_key)
            automation_key = ROLE_AUTOMATION_KEYS.get(thread_key)
            automation_id = runtime.get(automation_key) if automation_key else None
            automation = automations.get(str(automation_id)) if automation_id else None
            if thread_id is None and automation_id is None:
                continue
            binding = "bound"
            if not isinstance(thread_id, str) or not thread_id:
                binding = "missing-thread"
                anomalies.append(f"{thread_key} has no task binding")
            elif thread_id in duplicate_threads:
                binding = "duplicate-thread"
                anomalies.append(f"{thread_key} reuses a task bound elsewhere")
            if automation_id in duplicate_automations:
                binding = "duplicate-automation"
                anomalies.append(f"automation {automation_id} is bound by more than one role")
            if automation_id and automation is None:
                binding = "missing-automation"
                anomalies.append(f"{thread_key} references missing automation {automation_id}")
            elif automation is not None:
                if automation["status"] != "available":
                    binding = "automation-unavailable"
                    anomalies.append(f"automation {automation_id} is unavailable")
                elif automation.get("target_thread_id") != thread_id:
                    binding = "automation-target-mismatch"
                    anomalies.append(f"automation {automation_id} targets a different task")
            roles.append(
                {
                    "role": thread_key.removesuffix("_thread_id"),
                    "label": ROLE_LABELS[thread_key],
                    "thread_id": thread_id if isinstance(thread_id, str) else None,
                    "binding_status": binding,
                    "task_state": {
                        "status": "unavailable",
                        "reason": "Live task state is not joined into this source-specific projection; use /api/v1/tasks.",
                    },
                    "automation": automation,
                    "last_activity": None,
                    "activity_attribution": {
                        "status": "unavailable",
                        "reason": (
                            "Canonical supervision events do not identify their emitting task; "
                            "model and reasoning fields are not treated as role identity."
                        ),
                    },
                }
            )
        return roles, anomalies

    def _light(
        self,
        evidence: TargetEvidence,
        heads: Mapping[str, Any],
        binding_anomalies: Sequence[str],
        *,
        include_integration_gap: bool,
    ) -> dict[str, Any]:
        owner = self._module("supervision")
        facts: list[dict[str, Any]] = []

        def add(rule: str, severity: str, item: Mapping[str, Any] | None, detail: str) -> None:
            source_line = None
            if item is not None:
                try:
                    source_line = evidence.events.index(item) + 1
                except ValueError:
                    source_line = None
            facts.append(
                {
                    "rule": rule,
                    "severity": severity,
                    "record_id": _bounded(item.get("record_id")) if item else None,
                    "observed_at": _bounded(item.get("timestamp")) if item else _observed_at(),
                    "detail": detail,
                    "source_identity": (
                        "supervise-tracker-runs/events.jsonl"
                        if item is not None
                        else "software-factory-dashboard/derived-attention"
                    ),
                    "source_path": (
                        str(evidence.directory / "events.jsonl") if item is not None else None
                    ),
                    "source_line": source_line,
                }
            )

        open_incidents = [
            item
            for incident_id, item in heads["incidents"].items()
            if not owner.is_terminal_incident_record(item, incident_id)
        ]
        lifecycle = heads["lifecycle"][-1] if heads["lifecycle"] else None
        lifecycle_status = str(lifecycle.get("status", "")) if lifecycle else ""
        for item in open_incidents:
            severity = str(item.get("severity", "info")).lower()
            if severity in {"high", "critical"}:
                add("open-high-or-critical-incident", "red", item, str(item.get("summary", "Open incident")))
        for item in heads["decisions"].values():
            if item.get("phase") != "target-acknowledged" and item.get("safe_frontier") == "empty":
                add("blocking-decision-empty-safe-frontier", "red", item, str(item.get("summary", "Blocking decision")))
        for item in heads["transitions"].values():
            if item.get("phase") != "work-started":
                add("incomplete-successor-transition", "red", item, str(item.get("summary", "Incomplete successor transition")))
        if lifecycle_status in {"blocked", "failed", "stopped"}:
            add(
                f"lifecycle-{lifecycle_status}",
                "red",
                lifecycle,
                str(lifecycle.get("summary") or f"Supervision lifecycle is {lifecycle_status}."),
            )
        elif lifecycle_status == "completed" and lifecycle is not None:
            state_fingerprint = str(lifecycle.get("state_fingerprint", ""))
            completion = owner.latest_outcome_completion_record(
                list(evidence.active_events),
                state_fingerprint=state_fingerprint,
            )
            permitted, reason = owner.assess_outcome_completion_record(
                completion,
                policy=evidence.policy,
                state_fingerprint=state_fingerprint,
            )
            if (
                not permitted
                or completion is None
                or lifecycle.get("outcome_completion_record_id") != completion.get("record_id")
            ):
                add(
                    "stale-or-unverified-completion",
                    "red",
                    lifecycle,
                    reason,
                )
        if not any(fact["severity"] == "red" for fact in facts):
            for item in open_incidents:
                if str(item.get("severity", "")).lower() == "warning":
                    add("open-warning-incident", "amber", item, str(item.get("summary", "Warning incident")))
            for item in heads["decisions"].values():
                if item.get("phase") != "target-acknowledged":
                    add("open-nonblocking-decision", "amber", item, str(item.get("summary", "Open decision")))
            for anomaly in binding_anomalies:
                add("degraded-supervisor-binding", "amber", None, anomaly)
            last_check = heads["checks"][-1] if heads["checks"] else None
            routine_minutes = evidence.policy.get("schedule", {}).get("routine_minutes")
            last_time = _event_time(last_check) if last_check else None
            if isinstance(routine_minutes, int) and routine_minutes > 0:
                threshold = timedelta(minutes=routine_minutes)
                if last_time is None or self._now().astimezone(UTC) - last_time > threshold:
                    add(
                        "recorded-check-later-than-configured-cadence",
                        "amber",
                        last_check,
                        f"No recorded check falls within the configured {routine_minutes}-minute cadence; no-op wake success remains unverified.",
                    )
            if include_integration_gap:
                add(
                    "codex-task-state-unavailable",
                    "amber",
                    None,
                    "Codex task/turn state is not joined into this source-specific projection; task terminality or activity is not inferred.",
                )
        red = any(fact["severity"] == "red" for fact in facts)
        amber = any(fact["severity"] == "amber" for fact in facts)
        if red:
            posture, label = "red", "Action required"
        elif lifecycle_status in {"paused", "completed", "stopped", "failed", "blocked"}:
            posture, label = "neutral", lifecycle_status.replace("-", " ").title()
        elif amber:
            posture, label = "amber", "Attention"
        else:
            posture, label = "green", "On track"
        return {
            "posture": posture,
            "label": label,
            "facts": facts,
            "derived": True,
            "completion_claim": False,
        }

    def _operating_history(self, evidence: TargetEvidence) -> list[dict[str, Any]]:
        owner = self._module("supervision")
        incident_heads: dict[str, Mapping[str, Any]] = {}
        decision_heads: dict[str, Mapping[str, Any]] = {}
        transition_heads: dict[str, Mapping[str, Any]] = {}
        lifecycle: Mapping[str, Any] | None = None
        prior = "neutral"
        transitions: list[dict[str, Any]] = []
        for index, item in enumerate(evidence.active_events):
            incident_id = item.get("incident_id")
            if incident_id and owner.is_substantive_incident_record(item, str(incident_id)):
                incident_heads[str(incident_id)] = item
            if item.get("kind") == "decision" and item.get("decision_id"):
                decision_heads[str(item["decision_id"])] = item
            if item.get("kind") == "successor-transition" and item.get("transition_id"):
                transition_heads[str(item["transition_id"])] = item
            if item.get("kind") == "lifecycle":
                lifecycle = item
            open_incidents = [
                value
                for key, value in incident_heads.items()
                if not owner.is_terminal_incident_record(value, key)
            ]
            if any(str(value.get("severity", "")).lower() in {"high", "critical"} for value in open_incidents):
                posture, trigger = "red", "open-high-or-critical-incident"
            elif any(value.get("safe_frontier") == "empty" and value.get("phase") != "target-acknowledged" for value in decision_heads.values()):
                posture, trigger = "red", "blocking-decision-empty-safe-frontier"
            elif any(value.get("phase") != "work-started" for value in transition_heads.values()):
                posture, trigger = "red", "incomplete-successor-transition"
            elif lifecycle and lifecycle.get("status") in {"blocked", "failed", "stopped"}:
                posture, trigger = "red", f"lifecycle-{lifecycle.get('status')}"
            elif lifecycle and lifecycle.get("status") == "completed":
                state_fingerprint = str(lifecycle.get("state_fingerprint", ""))
                completion = owner.latest_outcome_completion_record(
                    list(evidence.active_events[: index + 1]),
                    state_fingerprint=state_fingerprint,
                )
                permitted, _reason = owner.assess_outcome_completion_record(
                    completion,
                    policy=evidence.policy,
                    state_fingerprint=state_fingerprint,
                )
                if (
                    not permitted
                    or completion is None
                    or lifecycle.get("outcome_completion_record_id")
                    != completion.get("record_id")
                ):
                    posture, trigger = "red", "stale-or-unverified-completion"
                else:
                    posture, trigger = "neutral", "lifecycle-completed"
            elif open_incidents or any(value.get("phase") != "target-acknowledged" for value in decision_heads.values()):
                posture, trigger = "amber", "open-warning-or-decision"
            elif lifecycle and lifecycle.get("status") == "paused":
                posture, trigger = "neutral", f"lifecycle-{lifecycle.get('status')}"
            else:
                posture, trigger = "amber", "codex-task-state-unavailable"
            if posture != prior:
                transitions.append(
                    {
                        "from": prior,
                        "to": posture,
                        "trigger": trigger,
                        "record": _record_ref(item),
                    }
                )
                prior = posture
        return transitions

    def _owner_command(self, arguments: Sequence[str]) -> dict[str, Any]:
        command = [sys.executable, str(self.supervision_owner), "--root", str(self.supervision_root), *arguments]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=OWNER_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OperationsProjectionError(
                "report_owner_unavailable", str(exc), status=503, retryable=True
            ) from exc
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise OperationsProjectionError(
                "report_owner_output_invalid",
                "Maintained report owner returned non-JSON output.",
                status=503,
            ) from exc
        if result.returncode != 0:
            message = payload.get("error") if isinstance(payload, Mapping) else None
            raise OperationsProjectionError(
                "report_verification_failed",
                str(message or "Maintained report owner rejected the artifact set."),
                status=422,
            )
        if not isinstance(payload, dict):
            raise OperationsProjectionError(
                "report_owner_output_invalid", "Maintained report owner output is not an object.", status=503
            )
        return payload

    @staticmethod
    def _report_tree_key(directory: Path, owner_sha256: str) -> tuple[Any, ...]:
        if not directory.exists():
            return (str(directory), owner_sha256, None)
        entries = tuple(
            _stat_key(path)
            for path in sorted(directory.iterdir(), key=lambda item: item.name)
            if path.is_file()
        )
        return (str(directory), owner_sha256, entries)

    @staticmethod
    def _report_members(directory: Path) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            if not path.is_file() or path.is_symlink() or path.name == ".append.lock":
                continue
            raw = _read_bounded(path, MAX_REPORT_ARTIFACT_BYTES)
            members.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "media_type": (
                        "application/pdf"
                        if path.suffix == ".pdf"
                        else "application/json"
                        if path.suffix == ".json"
                        else "text/markdown"
                        if path.suffix == ".md"
                        else "application/octet-stream"
                    ),
                    "bytes": len(raw),
                    "sha256": sha256(raw).hexdigest(),
                    "read_only": True,
                }
            )
        return members

    def _verify_report(
        self,
        *,
        target: str,
        family: str,
        report_id: str,
        directory: Path,
        owner_sha256: str,
        source_fingerprint: str,
    ) -> dict[str, Any]:
        key = (*self._report_tree_key(directory, owner_sha256), source_fingerprint)
        with self._lock:
            cached = self._report_cache.get(key)
            if cached is not None:
                self._report_cache.move_to_end(key)
                return dict(cached)
        try:
            if family == "weekly":
                verification = self._owner_command(
                    ["weekly-report", "--target-thread", target, "--action", "verify", "--report-id", report_id]
                )
                report_path = directory / "report.json"
                report = json.loads(_read_bounded(report_path, MAX_REPORT_ARTIFACT_BYTES))
                review = report.get("cognitive_review") if isinstance(report, Mapping) else None
                metrics = report.get("metrics") if isinstance(report, Mapping) else None
                result = {
                    "id": report_id,
                    "target_thread_id": target,
                    "family": family,
                    "stage": "verified",
                    "status": "available",
                    "source_root": verification.get("source_root"),
                    "manifest_root": verification.get("manifest_root"),
                    "disposition": review.get("overall_posture") if isinstance(review, Mapping) else None,
                    "coverage": metrics.get("coverage") if isinstance(metrics, Mapping) else None,
                    "review_summary": {
                        "headline": _bounded(review.get("headline"), 500),
                        "assessment": _bounded(review.get("executive_assessment"), 1_500),
                    } if isinstance(review, Mapping) else None,
                    "verification": verification,
                    "members": self._report_members(directory),
                    "limitations": list(metrics.get("limitations", [])) if isinstance(metrics, Mapping) else [],
                    "error": None,
                }
            elif family == "terminal":
                verification = self._owner_command(
                    ["terminal-report", "--target-thread", target, "--action", "verify", "--report-set-id", report_id]
                )
                result = {
                    "id": report_id,
                    "target_thread_id": target,
                    "family": family,
                    "stage": "verified",
                    "status": "available",
                    "source_root": verification.get("source_root"),
                    "manifest_root": verification.get("manifest_root"),
                    "disposition": None,
                    "coverage": None,
                    "review_summary": None,
                    "verification": verification,
                    "members": self._report_members(directory),
                    "limitations": ["A verified terminal report is not lifecycle or observable-outcome authority."],
                    "error": None,
                }
            else:
                verification = self._owner_command(
                    ["factory-evolution", "--target-thread", target, "--evolution-id", report_id, "--action", "verify"]
                )
                result = {
                    "id": report_id,
                    "target_thread_id": target,
                    "family": family,
                    "stage": verification.get("stage"),
                    "status": "available",
                    "source_root": verification.get("packet_root"),
                    "manifest_root": verification.get("evaluation_root") or verification.get("review_root") or verification.get("packet_root"),
                    "disposition": verification.get("disposition"),
                    "coverage": None,
                    "review_summary": None,
                    "verification": verification,
                    "members": self._report_members(directory),
                    "limitations": ["Factory-evolution disposition grants no implementation, adoption, deployment, or outcome authority."],
                    "error": None,
                }
        except (OperationsProjectionError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            error = exc if isinstance(exc, OperationsProjectionError) else OperationsProjectionError(
                "report_projection_failed", str(exc), status=422
            )
            try:
                members = self._report_members(directory) if directory.is_dir() else []
            except OperationsProjectionError:
                members = []
            result = {
                "id": report_id,
                "target_thread_id": target,
                "family": family,
                "stage": "partial",
                "status": "unavailable",
                "source_root": None,
                "manifest_root": None,
                "disposition": None,
                "coverage": None,
                "review_summary": None,
                "verification": None,
                "members": members,
                "limitations": ["This source-local report failure does not suppress independent run or report families."],
                "error": {"code": error.code, "message": str(error), "retryable": error.retryable},
            }
        with self._lock:
            self._report_cache[key] = dict(result)
            while len(self._report_cache) > MAX_CACHE_ENTRIES:
                self._report_cache.popitem(last=False)
        return result

    def _reports(self, evidence: TargetEvidence, owners: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        families = (
            ("weekly", evidence.directory / "reports" / "weekly", owners["weekly_report"]["sha256"]),
            ("terminal", evidence.directory / "reports" / "terminal", owners["terminal_report"]["sha256"]),
            ("factory-evolution", evidence.directory / "learning" / "factory-evolution", owners["factory_evolution"]["sha256"]),
        )
        reports: list[dict[str, Any]] = []

        def unavailable_inventory(
            family: str,
            report_id: str,
            code: str,
            message: str,
        ) -> dict[str, Any]:
            return {
                "id": report_id,
                "target_thread_id": evidence.target_thread_id,
                "family": family,
                "stage": "partial",
                "status": "unavailable",
                "source_root": None,
                "manifest_root": None,
                "disposition": None,
                "coverage": None,
                "review_summary": None,
                "verification": None,
                "members": [],
                "limitations": [
                    "This source-local report inventory failure does not suppress independent run or report families."
                ],
                "error": {"code": code, "message": message, "retryable": False},
        }

        for family, root, owner_sha in families:
            if root.is_symlink():
                reports.append(
                    unavailable_inventory(
                        family,
                        f"{family}-inventory",
                        "report_root_invalid",
                        "Report family root must be a local, non-symlink directory.",
                    )
                )
                continue
            if not root.exists():
                continue
            if not root.is_dir():
                reports.append(
                    unavailable_inventory(
                        family,
                        f"{family}-inventory",
                        "report_root_invalid",
                        "Report family root must be a local, non-symlink directory.",
                    )
                )
                continue
            try:
                entries = sorted(root.iterdir(), key=lambda item: item.name)
            except OSError as exc:
                reports.append(
                    unavailable_inventory(
                        family,
                        f"{family}-inventory",
                        "report_inventory_unavailable",
                        f"Report inventory could not be read: {exc}",
                    )
                )
                continue
            directories: list[Path] = []
            for item in entries:
                if not SAFE_ID.fullmatch(item.name):
                    continue
                if item.is_symlink() or not item.is_dir():
                    reports.append(
                        unavailable_inventory(
                            family,
                            item.name,
                            "report_set_invalid",
                            "Report set must be a local, non-symlink directory.",
                        )
                    )
                    continue
                directories.append(item)
            if len(directories) > MAX_REPORT_SETS:
                reports.append(
                    unavailable_inventory(
                        family,
                        f"{family}-inventory",
                        "report_set_limit",
                        "Too many report sets.",
                    )
                )
                continue
            for directory in sorted(directories, key=lambda item: item.name):
                reports.append(
                    self._verify_report(
                        target=evidence.target_thread_id,
                        family=family,
                        report_id=directory.name,
                        directory=directory,
                        owner_sha256=str(owner_sha),
                        source_fingerprint=evidence.fingerprint,
                    )
                )
        return reports

    def _metrics(self, evidence: TargetEvidence) -> dict[str, Any]:
        if not evidence.active_events:
            return {
                "status": "unavailable",
                "definition_owner": "supervise-tracker-runs/scripts/weekly_report.py",
                "metrics": None,
                "error": {"code": "empty_active_mission", "message": "The active mission has no canonical events.", "retryable": False},
            }
        try:
            weekly = self._module("weekly")
            owner = self._module("supervision")
            first = _event_time(evidence.active_events[0])
            last = _event_time(evidence.active_events[-1])
            if first is None or last is None:
                raise OperationsProjectionError(
                    "metric_time_invalid",
                    "Active mission event timestamps are invalid.",
                    status=422,
                )
            if last <= first:
                last = first + timedelta(seconds=1)
            active_binding = owner.bound_mission(evidence.policy)
            active_root = (
                str(active_binding["mission_root"])
                if isinstance(active_binding, Mapping)
                else "unbound"
            )
            policy_history = [
                record
                for record in evidence.policy_history
                if isinstance(record.get("policy"), Mapping)
                and evidence.roots_by_policy.get(
                    str(record["policy"].get("policy_sha256", "")),
                    "unbound",
                )
                == active_root
            ]
            metrics, _packet = weekly.build_metrics(
                target_label=str(evidence.policy.get("target_label", evidence.target_thread_id[:12])),
                target_thread_id=evidence.target_thread_id,
                start=first,
                end=last,
                timezone_name=str(evidence.policy.get("reports", {}).get("weekly", {}).get("timezone", "America/Los_Angeles")),
                all_events=list(evidence.active_events),
                policy_history=policy_history,
                current_policy=evidence.policy,
                projection_inventory=owner.weekly_projection_inventory(evidence.directory),
            )
            projection = weekly.report_metrics(metrics)
            projection["blocks"] = metrics.get("blocks", [])
            return {
                "status": "available",
                "definition_owner": "supervise-tracker-runs/scripts/weekly_report.py",
                "metrics": projection,
                "error": None,
            }
        except Exception as exc:
            error = (
                exc
                if isinstance(exc, OperationsProjectionError)
                else OperationsProjectionError("metric_projection_failed", str(exc), status=422)
            )
            return {
                "status": "unavailable",
                "definition_owner": "supervise-tracker-runs/scripts/weekly_report.py",
                "metrics": None,
                "error": {
                    "code": error.code,
                    "message": str(error),
                    "retryable": error.retryable,
                },
            }

    def _attention(
        self,
        run: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        order = {
            "pending-approval-or-input": 0,
            "open-high-or-critical-incident": 1,
            "blocking-decision-empty-safe-frontier": 2,
            "incomplete-successor-transition": 3,
            "source-integrity-failure": 4,
            "lifecycle-blocked": 4,
            "lifecycle-failed": 4,
            "lifecycle-stopped": 4,
            "stale-or-unverified-completion": 5,
            "open-warning-incident": 6,
            "unavailable-required-integration": 7,
            "open-nonblocking-decision": 7,
            "degraded-supervisor-binding": 7,
            "recorded-check-later-than-configured-cadence": 7,
            "codex-task-state-unavailable": 7,
        }
        items = []
        for fact in run.get("light", {}).get("facts", []):
            rule = str(fact.get("rule", "unavailable-required-integration"))
            items.append(
                {
                    "rank": order.get(rule, 7),
                    "rule": rule,
                    "severity": fact.get("severity"),
                    "target_thread_id": run.get("target_thread_id"),
                    "source_record_id": fact.get("record_id"),
                    "source_identity": fact.get("source_identity"),
                    "source_path": fact.get("source_path"),
                    "source_line": fact.get("source_line"),
                    "observed_at": fact.get("observed_at"),
                    "detail": fact.get("detail"),
                    "detail_route": f"/runs/{run.get('target_thread_id')}",
                }
            )
        return items

    def _available_run(
        self,
        evidence: TargetEvidence,
        *,
        projects: Sequence[ProjectRecord],
        automations: Mapping[str, dict[str, Any]],
        duplicate_threads: set[str],
        duplicate_automations: set[str],
        owners: Mapping[str, Mapping[str, Any]],
        cache_status: str,
    ) -> dict[str, Any]:
        owner = self._module("supervision")
        binding = owner.bound_mission(evidence.policy)
        current_mission = {
            "root": str(binding["mission_root"]) if isinstance(binding, Mapping) else None,
            "source_record": str(binding["mission_source_record"]) if isinstance(binding, Mapping) else None,
            "policy_sha256": evidence.policy.get("policy_sha256"),
        }
        heads = self._active_heads(evidence)
        roles, anomalies = self._roles(
            evidence,
            automations,
            duplicate_threads,
            duplicate_automations,
        )
        project_binding = self._project_binding(evidence, projects)
        if project_binding["status"] != "bound":
            anomalies.append(f"project binding is {project_binding['status']}")
        light = self._light(evidence, heads, anomalies, include_integration_gap=True)
        timeline, timeline_truncated = self._timeline(evidence)
        reports = self._reports(evidence, owners)
        metrics = self._metrics(evidence)
        incidents = []
        for incident_id, head in sorted(heads["incidents"].items()):
            incidents.append(
                {
                    "incident_id": incident_id,
                    "open": not owner.is_terminal_incident_record(head, incident_id),
                    "head": _record_ref(head),
                }
            )
        decisions = [
            {"decision_id": decision_id, "open": item.get("phase") != "target-acknowledged", "head": _record_ref(item), "phase": _bounded(item.get("phase")), "safe_frontier": _bounded(item.get("safe_frontier"))}
            for decision_id, item in sorted(heads["decisions"].items())
        ]
        transitions = [
            {"transition_id": transition_id, "open": item.get("phase") != "work-started", "head": _record_ref(item), "phase": _bounded(item.get("phase"))}
            for transition_id, item in sorted(heads["transitions"].items())
        ]
        activity_records = [item for item in evidence.active_events if item.get("kind") in ACTIVITY_KINDS]
        conclusion_records = [item for item in evidence.active_events if self._is_conclusion(item, owner)]
        activities = [
            _event_projection(
                item,
                mission_root=self._mission_root(evidence, item),
                source_path=evidence.directory / "events.jsonl",
                line=evidence.events.index(item) + 1,
            )
            for item in activity_records[-MAX_RECENT_RECORDS:]
        ]
        conclusions = [
            _event_projection(
                item,
                mission_root=self._mission_root(evidence, item),
                source_path=evidence.directory / "events.jsonl",
                line=evidence.events.index(item) + 1,
            )
            for item in conclusion_records[-MAX_RECENT_RECORDS:]
        ]
        report_counts = Counter(
            f"{report['family']}:{report['status']}" for report in reports
        )
        lifecycle = heads["lifecycle"][-1] if heads["lifecycle"] else None
        topology = {
            "supervisor_group_id": _digest(
                {"target": evidence.target_thread_id, "mission": current_mission["root"]}
            ),
            "implementation": {
                "thread_id": evidence.target_thread_id,
                "status": "unavailable",
                "reason": "Use the version-gated task API; composed topology begins in the Factory Floor.",
            },
            "project_binding": project_binding,
            "tracker_binding": {
                "status": "unavailable",
                "tracker_path": None,
                "tracker_sha256": None,
                "reason": "No canonical tracker association field exists in the maintained supervision policy.",
            },
            "roles": roles,
            "binding_integrity": "valid" if not anomalies else "degraded",
            "anomalies": sorted(set(anomalies)),
        }
        return {
            "status": "available",
            "target_thread_id": evidence.target_thread_id,
            "target_label": str(evidence.policy.get("target_label", evidence.target_thread_id[:12])),
            "observed_at": _observed_at(),
            "fingerprint": evidence.fingerprint,
            "current_mission": current_mission,
            "project_binding": project_binding,
            "event_count": len(evidence.events),
            "current_event_count": len(evidence.active_events),
            "predecessor_count": sum(1 for segment in self._mission_segments(evidence) if segment["posture"] != "current"),
            "lifecycle": {"status": _bounded(lifecycle.get("status")) if lifecycle else None, "record": _record_ref(lifecycle)},
            "counts": {
                "open_incidents": sum(1 for item in incidents if item["open"]),
                "open_decisions": sum(1 for item in decisions if item["open"]),
                "open_successor_transitions": sum(1 for item in transitions if item["open"]),
                "activities": len(activity_records),
                "conclusions": len(conclusion_records),
                "reports": dict(sorted(report_counts.items())),
            },
            "last_check": _record_ref(heads["checks"][-1] if heads["checks"] else None),
            "latest_activity": _record_ref(activity_records[-1] if activity_records else None),
            "latest_conclusion": _record_ref(conclusion_records[-1] if conclusion_records else None),
            "light": light,
            "topology": topology,
            "policy": {
                "version": evidence.policy.get("policy_version"),
                "sha256": evidence.policy.get("policy_sha256"),
                "schedule": evidence.policy.get("schedule", {}),
                "reports": evidence.policy.get("reports", {}),
                "source_path": str(evidence.directory / "policy.json"),
                "read_only": True,
            },
            "policy_history": [
                {
                    "record_id": record.get("record_id"),
                    "timestamp": record.get("timestamp"),
                    "kind": record.get("kind"),
                    "policy_version": record.get("policy", {}).get("policy_version") if isinstance(record.get("policy"), Mapping) else None,
                    "policy_sha256": record.get("policy", {}).get("policy_sha256") if isinstance(record.get("policy"), Mapping) else None,
                    "mission_root": evidence.roots_by_policy.get(str(record.get("policy", {}).get("policy_sha256", "")), "unbound") if isinstance(record.get("policy"), Mapping) else "unbound",
                }
                for record in evidence.policy_history
            ],
            "mission_segments": self._mission_segments(evidence),
            "incidents": incidents,
            "decisions": decisions,
            "successor_transitions": transitions,
            "activities": activities,
            "activities_truncated": len(activity_records) > MAX_RECENT_RECORDS,
            "conclusions": conclusions,
            "conclusions_truncated": len(conclusion_records) > MAX_RECENT_RECORDS,
            "timeline": timeline,
            "timeline_truncated": timeline_truncated,
            "operating_history": self._operating_history(evidence),
            "reports": reports,
            "metrics": metrics,
            "source": {
                "identity": "supervise-tracker-runs/scripts/supervision_log.py",
                "root": str(evidence.directory),
                "revision": owners["supervision"]["sha256"],
                "event_head_sha256": evidence.events[-1].get("record_sha256") if evidence.events else None,
                "policy_head_sha256": evidence.policy.get("policy_sha256"),
                "cache_status": cache_status,
            },
            "coverage": {
                "status": "partial",
                "observed": ["policy", "policy-history", "event-ledger", "mission-scoped-state", "automations", "reports", "metrics"],
                "missing": ["codex-app-server-task-state", "canonical-tracker-association", "automation-wake-receipts"],
            },
            "limitations": [
                "Current state is scoped to the active mission root; predecessor records remain separate history.",
                "Unchanged automation wakes may have no event, so recorded activity is a lower bound.",
                "Canonical supervision events do not identify an emitting task or role; actor attribution is unavailable rather than inferred from model or reasoning.",
                "Traffic lights are transparent derived facts, never lifecycle or completion state.",
                "API-equivalent cost is an estimate from the maintained report owner, not billing telemetry.",
            ] + (["Timeline was bounded to its newest records; source line identities remain exact."] if timeline_truncated else []),
            "error": None,
        }

    @staticmethod
    def _unavailable_run(target: str, error: OperationsProjectionError) -> dict[str, Any]:
        observed = _observed_at()
        return {
            "status": "unavailable",
            "target_thread_id": target,
            "target_label": target[:12],
            "observed_at": observed,
            "fingerprint": None,
            "current_mission": None,
            "project_binding": {"status": "unassigned", "project_id": None, "evidence": [], "limitations": []},
            "event_count": None,
            "current_event_count": None,
            "predecessor_count": None,
            "lifecycle": {"status": None, "record": None},
            "counts": None,
            "last_check": None,
            "latest_activity": None,
            "latest_conclusion": None,
            "light": {
                "posture": "red",
                "label": "Action required",
                "facts": [{
                    "rule": "source-integrity-failure",
                    "severity": "red",
                    "record_id": None,
                    "observed_at": observed,
                    "detail": str(error),
                    "source_identity": "supervise-tracker-runs/source-validation",
                    "source_path": None,
                    "source_line": None,
                }],
                "derived": True,
                "completion_claim": False,
            },
            "topology": None,
            "policy": None,
            "policy_history": [],
            "mission_segments": [],
            "incidents": [],
            "decisions": [],
            "successor_transitions": [],
            "activities": [],
            "activities_truncated": False,
            "conclusions": [],
            "conclusions_truncated": False,
            "timeline": [],
            "timeline_truncated": False,
            "operating_history": [],
            "reports": [],
            "metrics": {"status": "unavailable", "definition_owner": "supervise-tracker-runs/scripts/weekly_report.py", "metrics": None, "error": {"code": error.code, "message": str(error), "retryable": error.retryable}},
            "source": None,
            "coverage": {"status": "unavailable", "observed": [], "missing": ["supervision-integrity"]},
            "limitations": ["This source-local failure does not suppress independent targets."],
            "error": {"code": error.code, "message": str(error), "retryable": error.retryable},
        }

    @staticmethod
    def _summary(run: Mapping[str, Any]) -> dict[str, Any]:
        keys = (
            "status",
            "target_thread_id",
            "target_label",
            "observed_at",
            "fingerprint",
            "current_mission",
            "project_binding",
            "event_count",
            "current_event_count",
            "predecessor_count",
            "lifecycle",
            "counts",
            "last_check",
            "latest_activity",
            "latest_conclusion",
            "light",
            "topology",
            "source",
            "coverage",
            "limitations",
            "error",
        )
        return {key: run[key] for key in keys}

    def snapshot(self, projects: Sequence[ProjectRecord]) -> dict[str, Any]:
        owners = self.owner_revisions()
        automations = self._automation_inventory()
        loaded: list[tuple[TargetEvidence, str]] = []
        unavailable: list[tuple[str, OperationsProjectionError]] = []
        for directory in self._target_directories():
            try:
                loaded.append(self._load_target(directory))
            except OperationsProjectionError as error:
                unavailable.append((directory.name, error))
        thread_counts: Counter[str] = Counter()
        automation_counts: Counter[str] = Counter()
        referenced_automations: set[str] = set()
        for evidence, _cache_status in loaded:
            runtime = evidence.policy.get("runtime")
            if not isinstance(runtime, Mapping):
                continue
            for key in ROLE_THREAD_KEYS:
                value = runtime.get(key)
                if isinstance(value, str) and value:
                    thread_counts[value] += 1
            for key in ROLE_AUTOMATION_KEYS.values():
                value = runtime.get(key)
                if isinstance(value, str) and value:
                    referenced_automations.add(value)
                    automation_counts[value] += 1
        duplicate_threads = {value for value, count in thread_counts.items() if count > 1}
        duplicate_automations = {
            value for value, count in automation_counts.items() if count > 1
        }
        runs: list[dict[str, Any]] = []
        for evidence, cache_status in loaded:
            try:
                projected = self._available_run(
                    evidence,
                    projects=projects,
                    automations=automations,
                    duplicate_threads=duplicate_threads,
                    duplicate_automations=duplicate_automations,
                    owners=owners,
                    cache_status=cache_status,
                )
                if self._target_key(evidence.directory) != evidence.cache_key:
                    raise OperationsProjectionError(
                        "supervision_changed_during_projection",
                        "Supervision source changed during projection; retry from its new root.",
                        status=409,
                        retryable=True,
                    )
            except OperationsProjectionError as error:
                projected = self._unavailable_run(evidence.target_thread_id, error)
            runs.append(projected)
        runs.extend(self._unavailable_run(target, error) for target, error in unavailable)
        runs.sort(key=lambda item: str(item["target_thread_id"]))
        attention = [item for run in runs for item in self._attention(run)]
        attention.sort(key=lambda item: (item["rank"], str(item["observed_at"]), str(item["target_thread_id"])))
        orphan_automations = [
            {**automation, "binding_status": "unreferenced"}
            for automation_id, automation in sorted(automations.items())
            if automation_id not in referenced_automations
        ]
        reports = [report for run in runs for report in run.get("reports", [])]
        bound_project_ids = {
            str(run["project_binding"]["project_id"])
            for run in runs
            if run.get("status") == "available"
            and run.get("project_binding", {}).get("status") == "bound"
            and run.get("project_binding", {}).get("project_id")
        }
        unmonitored_projects = [
            {
                "project_id": project.id,
                "project_label": project.label,
                "root": project.root,
                "status": "unmonitored",
                "reason": "No canonical supervision source currently binds this registered project; use the task API for independent cwd-bound work.",
            }
            for project in projects
            if project.id not in bound_project_ids
        ]
        available_metrics = [
            (run["target_thread_id"], run["metrics"]["metrics"])
            for run in runs
            if run.get("metrics", {}).get("status") == "available"
        ]
        metric_contracts: dict[tuple[Any, ...], dict[str, Any]] = {}
        for target_thread_id, metrics in available_metrics:
            coverage = metrics.get("coverage", {}) if isinstance(metrics, Mapping) else {}
            rates = metrics.get("rates", {}) if isinstance(metrics, Mapping) else {}
            calendar_days = tuple(coverage.get("calendar_days", []))
            contract_key = (
                metrics.get("schema_version"),
                metrics.get("kind"),
                coverage.get("start"),
                coverage.get("end"),
                coverage.get("timezone"),
                coverage.get("elapsed_hours"),
                coverage.get("partial_week"),
                calendar_days,
                rates.get("denominator_note"),
            )
            contract = metric_contracts.setdefault(
                contract_key,
                {
                    "schema_version": metrics.get("schema_version"),
                    "kind": metrics.get("kind"),
                    "coverage": {
                        "start": coverage.get("start"),
                        "end": coverage.get("end"),
                        "timezone": coverage.get("timezone"),
                        "elapsed_hours": coverage.get("elapsed_hours"),
                        "partial_week": coverage.get("partial_week"),
                        "calendar_days": list(calendar_days),
                    },
                    "denominator_note": rates.get("denominator_note"),
                    "target_thread_ids": [],
                },
            )
            contract["target_thread_ids"].append(target_thread_id)
        aggregate_status = (
            "unavailable"
            if not available_metrics
            else "available"
            if len(metric_contracts) == 1
            else "incompatible"
        )
        aggregate_inputs = available_metrics if aggregate_status == "available" else []
        aggregate_headline: Counter[str] = Counter()
        cost_totals: Counter[str] = Counter()
        per_run_metrics = []
        posture_transitions: list[dict[str, Any]] = []
        current_postures: Counter[str] = Counter()
        conclusion_kinds: Counter[str] = Counter()
        conclusion_categories: Counter[str] = Counter()
        scheduled_active_hours = 0.0
        explicitly_paused_hours = 0.0
        target_read_successes = 0
        target_read_failures = 0
        for run in runs:
            metrics_projection = run["metrics"]
            conclusions = run.get("conclusions", [])
            per_run_metrics.append(
                {
                    "target_thread_id": run["target_thread_id"],
                    "target_label": run["target_label"],
                    "supervisor_group_id": (
                        run.get("topology", {}).get("supervisor_group_id")
                        if isinstance(run.get("topology"), Mapping)
                        else None
                    ),
                    "project_binding": run["project_binding"],
                    "observed_at": run["observed_at"],
                    "current_mission_root": (
                        run.get("current_mission", {}).get("root")
                        if isinstance(run.get("current_mission"), Mapping)
                        else None
                    ),
                    "lifecycle": run["lifecycle"],
                    "light": run["light"],
                    "operating_history": run.get("operating_history", []),
                    "conclusion_counts": {
                        "by_kind": dict(
                            sorted(
                                Counter(
                                    str(item.get("kind") or "unavailable")
                                    for item in conclusions
                                ).items()
                            )
                        ),
                        "by_category": dict(
                            sorted(
                                Counter(
                                    str(item.get("category") or "unavailable")
                                    for item in conclusions
                                ).items()
                            )
                        ),
                    },
                    "report_counts": dict(run.get("counts", {}).get("reports", {}))
                    if isinstance(run.get("counts"), Mapping)
                    else {},
                    "status": metrics_projection["status"],
                    "cost_label": "API-equivalent estimate",
                    "metrics": metrics_projection["metrics"],
                    "error": metrics_projection["error"],
                }
            )
            current_postures[str(run.get("light", {}).get("posture", "unavailable"))] += 1
            for conclusion in conclusions:
                conclusion_kinds[str(conclusion.get("kind") or "unavailable")] += 1
                conclusion_categories[str(conclusion.get("category") or "unavailable")] += 1
            for transition in run.get("operating_history", []):
                posture_transitions.append(
                    {
                        "target_thread_id": run["target_thread_id"],
                        "target_label": run["target_label"],
                        "project_id": run.get("project_binding", {}).get("project_id"),
                        **transition,
                    }
                )
            if (
                metrics_projection.get("status") != "available"
                or aggregate_status != "available"
            ):
                continue
            metric_body = metrics_projection.get("metrics")
            availability = (
                metric_body.get("availability", {})
                if isinstance(metric_body, Mapping)
                else {}
            )
            scheduled_active_hours += float(
                availability.get("core_heartbeats_scheduled_active_hours", 0) or 0
            )
            explicitly_paused_hours += float(
                availability.get("core_heartbeats_explicitly_paused_hours", 0) or 0
            )
            target_read_successes += int(
                availability.get("recorded_target_read_successes", 0) or 0
            )
            target_read_failures += int(
                availability.get("recorded_target_read_failures", 0) or 0
            )
        posture_transitions.sort(
            key=lambda item: str(item.get("record", {}).get("timestamp") or "")
        )
        posture_transition_total = len(posture_transitions)
        posture_transitions = posture_transitions[-MAX_METRIC_HISTORY_ROWS:]
        for _target, metrics in aggregate_inputs:
            headline = metrics.get("headline", {}) if isinstance(metrics, Mapping) else {}
            for key, value in headline.items():
                if isinstance(value, int):
                    aggregate_headline[key] += value
            resource = metrics.get("resource_estimate", {}) if isinstance(metrics, Mapping) else {}
            totals = resource.get("totals", {}) if isinstance(resource, Mapping) else {}
            for key in (
                "recorded_model_attributed_events",
                "excluded_unpriced_or_unattributed_records",
                "estimated_input_tokens_base",
                "estimated_output_tokens_base",
                "estimated_tokens_base",
                "estimated_tokens_low",
                "estimated_tokens_high",
            ):
                value = totals.get(key)
                if isinstance(value, int):
                    cost_totals[key] += value
            for key in ("projected_cost_usd_low", "projected_cost_usd_base", "projected_cost_usd_high"):
                value = totals.get(key)
                if isinstance(value, (int, float)):
                    cost_totals[key] += float(value)
        aggregate = {
            "status": aggregate_status,
            "definition": "Exact sum only when every included current-mission metric projection shares one schema, definition, coverage interval, timezone, partial-window posture, calendar-day set, and denominator contract.",
            "run_count": len(runs),
            "available_run_count": len(available_metrics),
            "historical_segment_count": sum(int(run.get("predecessor_count") or 0) for run in runs),
            "contract_count": len(metric_contracts),
            "contracts": [
                {
                    **contract,
                    "target_thread_ids": sorted(contract["target_thread_ids"]),
                    "run_count": len(contract["target_thread_ids"]),
                }
                for _key, contract in sorted(
                    metric_contracts.items(), key=lambda item: repr(item[0])
                )
            ],
            "headline": (
                dict(sorted(aggregate_headline.items()))
                if aggregate_status == "available"
                else None
            ),
            "api_equivalent_estimate": {
                "label": "API-equivalent estimate",
                "actual_billing_data": False,
                "coverage_run_count": len(aggregate_inputs),
                "totals": (
                    dict(sorted(cost_totals.items()))
                    if aggregate_status == "available"
                    else None
                ),
            },
            "limitations": [
                "Incompatible or wholly unavailable contracts produce no aggregate numeric value; per-run projections remain available independently.",
                "Cross-run incident resolution percentiles are not synthesized because the maintained owner does not expose merge-safe sufficient statistics; exact median/P90 remain available per run.",
                "Counts exclude predecessor-only mission records and never imply implementation quality or completion.",
            ],
        }
        factory_history = {
            "definition": (
                "Bounded current-mission supervision history from maintained run "
                "projections; task concurrency and unrecorded no-op wakes are not inferred."
            ),
            "current_postures": dict(sorted(current_postures.items())),
            "supervisor_group_count": len(
                {
                    str(run["topology"]["supervisor_group_id"])
                    for run in runs
                    if isinstance(run.get("topology"), Mapping)
                    and run["topology"].get("supervisor_group_id")
                }
            ),
            "bound_project_count": len(bound_project_ids),
            "unmonitored_project_count": len(unmonitored_projects),
            "availability": {
                "status": aggregate_status,
                "scheduled_active_hours": (
                    round(scheduled_active_hours, 4)
                    if aggregate_status == "available"
                    else None
                ),
                "explicitly_paused_hours": (
                    round(explicitly_paused_hours, 4)
                    if aggregate_status == "available"
                    else None
                ),
                "recorded_target_read_successes": (
                    target_read_successes if aggregate_status == "available" else None
                ),
                "recorded_target_read_failures": (
                    target_read_failures if aggregate_status == "available" else None
                ),
                "continuous_uptime_measured": False,
            },
            "conclusions": {
                "by_kind": dict(sorted(conclusion_kinds.items())),
                "by_category": dict(sorted(conclusion_categories.items())),
            },
            "posture_transition_count": posture_transition_total,
            "posture_transitions": posture_transitions,
            "posture_transitions_truncated": (
                posture_transition_total > len(posture_transitions)
            ),
            "unsupported": [
                "Historical concurrent implementation count is unavailable because the canonical task owner exposes bounded current pages, not a retained task-state timeline.",
                "Unmonitored duration is unavailable; registered projects without a current exact run binding are a present-time count only.",
                "Traffic-light transition times do not establish time-in-posture without a complete interval boundary.",
                "Historical late or missed-check intervals are unavailable; current cadence warnings remain source-grounded light facts on each run.",
                "Generalized issue-recurrence rates are unavailable from merge-safe current metrics; exact incident and report evidence remains in source drill-downs.",
            ],
        }
        current_owner_hashes = {
            "supervision": _owner_sha256(self.supervision_owner),
            "weekly_report": _owner_sha256(self.weekly_owner),
            "terminal_report": _owner_sha256(self.terminal_owner),
            "factory_evolution": _owner_sha256(self.evolution_owner),
        }
        if {
            key: value["sha256"] for key, value in owners.items()
        } != current_owner_hashes:
            raise OperationsProjectionError(
                "owner_changed_during_projection",
                "A maintained supervision/report owner changed during projection; retry from its new revision.",
                status=409,
                retryable=True,
            )
        fingerprint = _digest(
            {
                "owners": {key: value["sha256"] for key, value in owners.items()},
                "runs": [run.get("fingerprint") or run.get("error") for run in runs],
                "automations": [automation.get("manifest_sha256") for automation in automations.values()],
                "reports": [report.get("manifest_root") or report.get("error") for report in reports],
            }
        )
        automation_inventory_available = not (
            automations.get("automation-inventory", {}).get("status") == "unavailable"
        )
        observed = ["supervision", "policy-history", "event-ledgers", "reports", "metrics"]
        missing = ["codex-app-server-task-state", "automation-wake-receipts", "billing-telemetry"]
        limitations = [
            "Every target and source family is isolated; unavailable input is never converted to zero, inactive, healthy, or complete.",
            "Task state and canonical cwd remain in the version-gated task API until the composed Factory Floor.",
        ]
        if automation_inventory_available:
            observed.append("automations")
        else:
            missing.append("automation-manifests")
            limitations.append(
                "Automation manifest inventory is unavailable; configured role IDs and independent supervision ledgers remain visible."
            )
        return {
            "fingerprint": fingerprint,
            "owners": owners,
            "runs": runs,
            "run_summaries": [self._summary(run) for run in runs],
            "attention": attention,
            "orphan_automations": orphan_automations,
            "unmonitored_projects": unmonitored_projects,
            "reports": reports,
            "metrics": {
                "aggregate": aggregate,
                "factory_history": factory_history,
                "per_run": per_run_metrics,
            },
            "coverage": {
                "status": "partial",
                "observed": observed,
                "missing": missing,
            },
            "limitations": limitations,
        }

    def run(self, projects: Sequence[ProjectRecord], target_thread_id: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        snapshot = self.snapshot(projects)
        selected = next(
            (run for run in snapshot["runs"] if run["target_thread_id"] == target_thread_id),
            None,
        )
        if selected is None:
            raise OperationsProjectionError(
                "run_not_found", "Supervision target is not discoverable.", status=404
            )
        return {**snapshot, "selected_run": selected}

    def _selected_report(
        self,
        projects: Sequence[ProjectRecord],
        target_thread_id: str,
        family: str,
        report_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        if family not in {"weekly", "terminal", "factory-evolution"}:
            raise OperationsProjectionError("invalid_report_family", "Report family is invalid.")
        if not SAFE_ID.fullmatch(report_id):
            raise OperationsProjectionError("invalid_report_id", "Report ID is invalid.")
        snapshot = self.snapshot(projects)
        selected = next(
            (
                report
                for report in snapshot["reports"]
                if report["target_thread_id"] == target_thread_id
                and report["family"] == family
                and report["id"] == report_id
            ),
            None,
        )
        if selected is None:
            raise OperationsProjectionError(
                "report_not_found", "Report artifact set is not discoverable.", status=404
            )
        return snapshot, selected

    def _read_selected_report_member(
        self,
        selected: Mapping[str, Any],
        *,
        member_name: str,
    ) -> tuple[bytes, dict[str, Any]]:
        if selected.get("status") != "available" or not isinstance(
            selected.get("verification"), Mapping
        ):
            raise OperationsProjectionError(
                "report_not_verified",
                "Artifacts are served only from a currently verified report set.",
                status=409,
            )
        if not SAFE_ID.fullmatch(member_name):
            raise OperationsProjectionError(
                "invalid_report_member", "Report member name is invalid."
            )
        member = next(
            (item for item in selected.get("members", []) if item.get("name") == member_name),
            None,
        )
        if member is None:
            raise OperationsProjectionError(
                "report_member_not_found", "Report member is not discoverable.", status=404
            )
        if member.get("media_type") not in {
            "application/json",
            "application/pdf",
            "text/markdown",
        }:
            raise OperationsProjectionError(
                "report_member_type_unsupported",
                "Only verified JSON, Markdown, and PDF report members are served.",
                status=415,
            )
        target = str(selected["target_thread_id"])
        family = str(selected["family"])
        report_id = str(selected["id"])
        relative_root = (
            Path("learning") / "factory-evolution"
            if family == "factory-evolution"
            else Path("reports") / family
        )
        expected_root = self.supervision_root / target / relative_root / report_id
        path = Path(str(member.get("path", "")))
        try:
            if expected_root.is_symlink() or path.is_symlink():
                raise OSError("symlinked report member")
            resolved_root = expected_root.resolve(strict=True)
            resolved_path = path.resolve(strict=True)
        except OSError as exc:
            raise OperationsProjectionError(
                "report_member_unavailable",
                "Verified report member is no longer available at its exact source.",
                status=409,
                retryable=True,
            ) from exc
        if resolved_path.parent != resolved_root or not resolved_path.is_file():
            raise OperationsProjectionError(
                "report_member_outside_bundle",
                "Report member is outside its verified bundle.",
                status=403,
            )
        raw = _read_bounded(resolved_path, MAX_REPORT_ARTIFACT_BYTES)
        if len(raw) != member.get("bytes") or sha256(raw).hexdigest() != member.get("sha256"):
            raise OperationsProjectionError(
                "report_member_changed",
                "Report member changed after verification; refresh the report projection.",
                status=409,
                retryable=True,
            )
        return raw, dict(member)

    def report(
        self,
        projects: Sequence[ProjectRecord],
        target_thread_id: str,
        family: str,
        report_id: str,
    ) -> dict[str, Any]:
        snapshot, selected = self._selected_report(
            projects, target_thread_id, family, report_id
        )
        metric_summary: dict[str, Any] | None = None
        if selected.get("status") == "available" and family == "weekly":
            raw, _member = self._read_selected_report_member(
                selected, member_name="metrics.json"
            )
            try:
                parsed = json.loads(raw)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise OperationsProjectionError(
                    "report_metric_summary_invalid",
                    "Verified weekly metric summary is not valid JSON.",
                    status=422,
                ) from exc
            if not isinstance(parsed, dict):
                raise OperationsProjectionError(
                    "report_metric_summary_invalid",
                    "Verified weekly metric summary is not an object.",
                    status=422,
                )
            metric_summary = parsed
        return {
            **snapshot,
            "selected_report": {**selected, "metric_summary": metric_summary},
        }

    def report_member(
        self,
        projects: Sequence[ProjectRecord],
        target_thread_id: str,
        family: str,
        report_id: str,
        member_name: str,
    ) -> tuple[bytes, dict[str, Any]]:
        _snapshot, selected = self._selected_report(
            projects, target_thread_id, family, report_id
        )
        return self._read_selected_report_member(
            selected, member_name=member_name
        )
