from __future__ import annotations

from collections import Counter, OrderedDict
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import argparse
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import RLock
import tomllib
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
AUTOMATION_CALENDAR_TIMEZONE = "America/Los_Angeles"
AUTOMATION_TARGET_QUERY_VERSION = 1
AUTOMATION_TARGET_QUERY_UNAVAILABLE_REASON = (
    "No maintained versioned automation target-query provider is configured; "
    "the dashboard will not scan unrelated manifests to infer duplicate owners."
)
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
AUTOMATION_BINDING_CONTRACTS = {
    "watcher": {
        "label": "Routine watcher",
        "purpose": "watcher-action",
        "thread_key": "watcher_thread_id",
        "automation_key": "routine_automation_id",
        "policy_source": "runtime",
    },
    "reviewer": {
        "label": "Effectiveness reviewer",
        "purpose": "semantic-escalation",
        "thread_key": "reviewer_thread_id",
        "automation_key": "meta_automation_id",
        "policy_source": "runtime",
    },
    "gmail_gate": {
        "label": "Gmail reply gate",
        "purpose": "gmail-gate",
        "thread_key": "gmail_gate_thread_id",
        "automation_key": "gmail_poll_automation_id",
        "policy_source": "runtime",
    },
    "roundup_writer": {
        "label": "Roundup writer",
        "purpose": "roundup-action",
        "thread_key": "roundup_thread_id",
        "automation_key": "roundup_automation_id",
        "policy_source": "runtime",
    },
    "weekly_report": {
        "label": "Weekly report",
        "purpose": "weekly-report",
        "thread_key": "roundup_thread_id",
        "automation_key": "automation_id",
        "policy_source": "weekly_report",
    },
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
ROLE_BIND_FIELDS = {
    "base_reviewer": ("base_reviewer_thread_id", "base_reviewer_thread"),
    "notice_reviewer": ("notice_reviewer_thread_id", "notice_reviewer_thread"),
    "fix_executor": ("fix_executor_thread_id", "fix_executor_thread"),
    "gmail_processor": ("gmail_processor_thread_id", "gmail_processor_thread"),
    "roundup_writer": ("roundup_thread_id", "roundup_thread"),
}
ROLE_MODEL_CONTRACTS = {
    role: {"model": "gpt-5.6-sol", "reasoning": "xhigh"}
    for role in ROLE_BIND_FIELDS
}
SEMANTIC_KINDS = {
    "checkpoint-review",
    "meta-review",
    "resolution",
}
DECISION_CONCLUSION_PHASES = {"resolved", "safe-deferred"}
POLICY_ADJUSTABLE_FIELDS = (
    "routine_minutes",
    "meta_review_hours",
    "max_sample_denominator",
    "cooldown_minutes",
    "max_escalations_per_hour",
    "gmail_quiet_minutes",
    "gmail_active_minutes",
    "gmail_active_window_minutes",
    "skill_maintenance_mode",
)
POLICY_ADJUSTMENT_FIELD_CONTRACTS = (
    {
        "field": "routine_minutes",
        "kind": "integer",
        "minimum": 15,
        "maximum": 60,
        "automation_role": "watcher",
    },
    {
        "field": "meta_review_hours",
        "kind": "integer",
        "minimum": 2,
        "maximum": 24,
        "automation_role": "reviewer",
    },
    {
        "field": "max_sample_denominator",
        "kind": "integer",
        "minimum": 4,
        "maximum": 10,
        "automation_role": None,
    },
    {
        "field": "cooldown_minutes",
        "kind": "integer",
        "minimum": 30,
        "maximum": 120,
        "automation_role": None,
    },
    {
        "field": "max_escalations_per_hour",
        "kind": "integer",
        "minimum": 1,
        "maximum": 2,
        "automation_role": None,
    },
    {
        "field": "gmail_quiet_minutes",
        "kind": "integer",
        "minimum": 2,
        "maximum": 10,
        "automation_role": "gmail_gate",
    },
    {
        "field": "gmail_active_minutes",
        "kind": "integer",
        "minimum": 1,
        "maximum": 9,
        "automation_role": "gmail_gate",
    },
    {
        "field": "gmail_active_window_minutes",
        "kind": "integer",
        "minimum": 5,
        "maximum": 120,
        "automation_role": "gmail_gate",
    },
    {
        "field": "skill_maintenance_mode",
        "kind": "enum",
        "minimum": None,
        "maximum": None,
        "automation_role": None,
    },
)
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


@dataclass(frozen=True)
class AutomationTargetQueryResult:
    """One exact, expiring candidate set from a read-only automation owner."""

    version: int
    target_thread_id: str
    automation_ids: tuple[str, ...]
    source_identity: str
    source_revision: str
    observed_at: datetime
    expires_at: datetime
    currentness: str


AutomationTargetQuery = Callable[[str], AutomationTargetQueryResult]


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


def policy_adjustable_values(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Project only fields owned by the maintained bounded `adjust` command."""

    schedule = policy.get("schedule")
    schedule = schedule if isinstance(schedule, Mapping) else {}
    routing = policy.get("routing")
    routing = routing if isinstance(routing, Mapping) else {}
    maintenance = policy.get("skill_maintenance")
    maintenance = maintenance if isinstance(maintenance, Mapping) else {}
    return {
        "routine_minutes": schedule.get("routine_minutes"),
        "meta_review_hours": schedule.get("meta_review_hours"),
        "max_sample_denominator": routing.get("max_sample_denominator"),
        "cooldown_minutes": routing.get("escalation_cooldown_minutes"),
        "max_escalations_per_hour": routing.get("max_escalations_per_hour"),
        "gmail_quiet_minutes": schedule.get("gmail_quiet_poll_minutes"),
        "gmail_active_minutes": schedule.get("gmail_active_poll_minutes"),
        "gmail_active_window_minutes": schedule.get("gmail_active_window_minutes"),
        "skill_maintenance_mode": maintenance.get("mode"),
    }


def policy_adjustment_contract(owner: ModuleType) -> dict[str, Any]:
    """Freeze the maintained helper's exact bounded field and contract surface."""

    modes = sorted(str(mode) for mode in owner.SKILL_MAINTENANCE_MODES)
    return {
        "fields": [dict(item) for item in POLICY_ADJUSTMENT_FIELD_CONTRACTS],
        "skill_maintenance_modes": modes,
        "skill_maintenance_contracts": {
            mode: owner.skill_maintenance_contract(mode) for mode in modes
        },
        "execution_economy_contract": owner.execution_economy_contract(),
    }


def _policy_weekly_report(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    reports = policy.get("reports")
    reports = reports if isinstance(reports, Mapping) else {}
    weekly = reports.get("weekly")
    return weekly if isinstance(weekly, Mapping) else {}


def _expected_automation_rrule(
    policy: Mapping[str, Any],
    role: str,
    *,
    gmail_cadence: Mapping[str, Any] | None = None,
) -> str | None:
    schedule = policy.get("schedule")
    schedule = schedule if isinstance(schedule, Mapping) else {}
    if role == "watcher":
        interval = schedule.get("routine_minutes")
        return (
            f"RRULE:FREQ=MINUTELY;INTERVAL={interval}"
            if type(interval) is int and interval > 0
            else None
        )
    if role == "reviewer":
        interval = schedule.get("meta_review_hours")
        return (
            f"RRULE:FREQ=HOURLY;INTERVAL={interval}"
            if type(interval) is int and interval > 0
            else None
        )
    if role == "gmail_gate":
        return (
            str(gmail_cadence["desired_rrule"])
            if isinstance(gmail_cadence, Mapping)
            and gmail_cadence.get("status") == "available"
            and isinstance(gmail_cadence.get("desired_rrule"), str)
            else None
        )
    if role == "roundup_writer":
        times = schedule.get("roundup_local_times")
        if not isinstance(times, list) or not times:
            return None
        parsed: list[tuple[int, int]] = []
        for value in times:
            if not isinstance(value, str) or not re.fullmatch(
                r"(?:[01]\d|2[0-3]):[0-5]\d", value
            ):
                return None
            hour, minute = (int(item) for item in value.split(":"))
            parsed.append((hour, minute))
        minutes = {minute for _, minute in parsed}
        if len(minutes) != 1 or len({hour for hour, _ in parsed}) != len(parsed):
            return None
        hours = ",".join(str(hour) for hour, _ in parsed)
        return (
            f"RRULE:FREQ=DAILY;BYHOUR={hours};BYMINUTE={parsed[0][1]};BYSECOND=0"
        )
    if role == "weekly_report":
        weekly = _policy_weekly_report(policy)
        weekday = weekly.get("weekday")
        local_time = weekly.get("local_time")
        if (
            weekly.get("enabled") is not True
            or weekday not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
            or not isinstance(local_time, str)
            or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", local_time)
        ):
            return None
        hour, minute = (int(item) for item in local_time.split(":"))
        return (
            "RRULE:FREQ=WEEKLY;"
            f"BYDAY={weekday};BYHOUR={hour};BYMINUTE={minute};BYSECOND=0"
        )
    return None


def _expected_automation_timezone(policy: Mapping[str, Any], role: str) -> str:
    if role == "roundup_writer":
        schedule = policy.get("schedule")
        schedule = schedule if isinstance(schedule, Mapping) else {}
        value = schedule.get("roundup_timezone")
        return (
            AUTOMATION_CALENDAR_TIMEZONE
            if value == AUTOMATION_CALENDAR_TIMEZONE
            else "unavailable"
        )
    if role == "weekly_report":
        value = _policy_weekly_report(policy).get("timezone")
        return (
            AUTOMATION_CALENDAR_TIMEZONE
            if value == AUTOMATION_CALENDAR_TIMEZONE
            else "unavailable"
        )
    return "not-applicable-to-interval-schedule"


def _system_timezone_name() -> str | None:
    """Project the local timezone used by the desktop automation owner."""

    candidates: list[str] = []
    localtime = Path("/etc/localtime")
    try:
        resolved = localtime.resolve(strict=True)
    except (OSError, RuntimeError):
        resolved = None
    if resolved is not None:
        marker = "/zoneinfo/"
        value = str(resolved)
        if marker in value:
            candidates.append(value.split(marker, 1)[1])
    for candidate in candidates:
        if not candidate or candidate.startswith("/") or ".." in Path(candidate).parts:
            continue
        try:
            ZoneInfo(candidate)
        except (ValueError, ZoneInfoNotFoundError):
            continue
        return candidate
    return None


def policy_automation_reconciliation(
    policy: Mapping[str, Any],
    roles: Sequence[Mapping[str, Any]],
    gmail_cadence: Mapping[str, Any] | None = None,
    automations: Mapping[str, Mapping[str, Any]] | None = None,
    automation_timezone: str | None = None,
    automation_target_query_available: bool = False,
) -> list[dict[str, Any]]:
    """Compare cadence policy to the actual bound automation owner projection."""

    runtime = policy.get("runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    by_role = {
        str(role.get("role")): role
        for role in roles
        if isinstance(role.get("role"), str)
    }
    specs = (
        ("routine_minutes", "watcher"),
        ("meta_review_hours", "reviewer"),
        ("gmail_cadence", "gmail_gate"),
        ("roundup_schedule", "roundup_writer"),
        ("weekly_report_schedule", "weekly_report"),
    )
    rows: list[dict[str, Any]] = []
    for field, role_name in specs:
        contract = AUTOMATION_BINDING_CONTRACTS[role_name]
        weekly = _policy_weekly_report(policy)
        automation_id = (
            weekly.get("automation_id")
            if contract["policy_source"] == "weekly_report"
            else runtime.get(contract["automation_key"])
        )
        target_thread_id = runtime.get(contract["thread_key"])
        if role_name in {"gmail_gate", "roundup_writer"} and not (
            automation_id or target_thread_id
        ):
            continue
        if role_name == "weekly_report" and not (
            weekly.get("enabled") is True or automation_id
        ):
            continue
        role = by_role.get(role_name)
        if role_name == "weekly_report":
            role = by_role.get("roundup_writer")
        automation = (
            automations.get(str(automation_id))
            if automations is not None and isinstance(automation_id, str)
            else role.get("automation") if isinstance(role, Mapping) else None
        )
        cadence_available = (
            role_name != "gmail_gate"
            or (
                isinstance(gmail_cadence, Mapping)
                and gmail_cadence.get("status") == "available"
            )
        )
        expected_rrule = _expected_automation_rrule(
            policy,
            role_name,
            gmail_cadence=gmail_cadence,
        )
        expected_timezone = _expected_automation_timezone(policy, role_name)
        actual_timezone = (
            "not-applicable-to-interval-schedule"
            if expected_timezone == "not-applicable-to-interval-schedule"
            else automation_timezone
        )
        actual_rrule = automation.get("rrule") if isinstance(automation, Mapping) else None
        owner_status = (
            automation.get("owner_status") if isinstance(automation, Mapping) else None
        )
        actual_target = (
            automation.get("target_thread_id") if isinstance(automation, Mapping) else None
        )
        allowed_sibling_ids = {
            sibling_id
            for sibling_role, sibling_contract in AUTOMATION_BINDING_CONTRACTS.items()
            if sibling_role != role_name
            and runtime.get(sibling_contract["thread_key"]) == target_thread_id
            and isinstance(
                sibling_id := (
                    _policy_weekly_report(policy).get("automation_id")
                    if sibling_contract["policy_source"] == "weekly_report"
                    else runtime.get(sibling_contract["automation_key"])
                ),
                str,
            )
            and sibling_id
        }
        related_unavailable_ids = sorted(
            automation_owner_id
            for automation_owner_id, item in (automations or {}).items()
            if (
                not isinstance(item, Mapping)
                or item.get("status") != "available"
            )
            and (
                automation_owner_id == automation_id
                or (
                    isinstance(item, Mapping)
                    and item.get("target_thread_id") == target_thread_id
                )
            )
        )
        target_owner_coverage_exact = bool(
            automations is not None
            and "automation-inventory" not in automations
            and not related_unavailable_ids
        )
        active_target_owner_ids = sorted(
            str(item.get("id"))
            for item in automations.values()
            if isinstance(item, Mapping)
            and item.get("status") == "available"
            and item.get("owner_status") == "ACTIVE"
            and item.get("kind") == "heartbeat"
            and item.get("target_thread_id") == target_thread_id
            and isinstance(item.get("id"), str)
        ) if automations is not None else []
        conflicting_owner_ids = [
            item
            for item in active_target_owner_ids
            if item != automation_id and item not in allowed_sibling_ids
        ]
        if not cadence_available:
            state = "unavailable"
            reason = "The maintained Gmail cadence projection is unavailable."
        elif (
            not isinstance(automation_id, str)
            or not automation_id
            or not isinstance(target_thread_id, str)
            or not target_thread_id
            or expected_rrule is None
            or expected_timezone == "unavailable"
        ):
            state = "unavailable"
            reason = "The canonical automation binding or schedule expectation is unavailable."
        elif actual_timezone is None:
            state = "unavailable"
            reason = "The automation owner's local timezone is unavailable."
        elif not target_owner_coverage_exact:
            state = "unavailable"
            reason = "The target-specific automation owner lookup cannot prove duplicate-role absence."
        elif not isinstance(automation, Mapping) or automation.get("status") != "available":
            state = "unavailable"
            reason = "The named automation owner projection is unavailable."
        elif conflicting_owner_ids:
            state = "partial"
            reason = "Another active automation is not proven to be a distinct canonical role."
        elif (
            expected_rrule == actual_rrule
            and expected_timezone == actual_timezone
            and owner_status == "ACTIVE"
            and automation.get("kind") == "heartbeat"
            and actual_target == target_thread_id
            and automation.get("id") == automation_id
        ):
            state = "reconciled"
            reason = "Policy cadence and actual active automation agree."
        else:
            state = "partial"
            reason = (
                "Policy cadence and actual automation state do not fully agree."
                if automation_target_query_available
                else AUTOMATION_TARGET_QUERY_UNAVAILABLE_REASON
            )
        repairable = bool(
            state == "partial"
            and automation_target_query_available
            and isinstance(automation, Mapping)
            and automation.get("id") == automation_id
            and automation.get("kind") == "heartbeat"
            and expected_timezone == actual_timezone
            and not conflicting_owner_ids
            and (
                role_name == "weekly_report"
                or (
                    isinstance(role, Mapping)
                    and role.get("binding_status") != "duplicate-automation"
                )
            )
        )
        rows.append(
            {
                "field": field,
                "role": role_name,
                "automation_id": automation_id if isinstance(automation_id, str) else None,
                "actual_automation_id": (
                    automation.get("id") if isinstance(automation, Mapping) else None
                ),
                "expected_rrule": expected_rrule,
                "actual_rrule": actual_rrule,
                "owner_status": owner_status,
                "target_thread_id": target_thread_id,
                "actual_target_thread_id": actual_target,
                "purpose": contract["purpose"],
                "timezone": expected_timezone,
                "actual_timezone": actual_timezone,
                "duplicate_coverage": (
                    "exact" if target_owner_coverage_exact else "unavailable"
                ),
                "active_target_owner_ids": active_target_owner_ids,
                "mode": (
                    gmail_cadence.get("mode")
                    if role_name == "gmail_gate" and cadence_available
                    else None
                ),
                "state": state,
                "repairable": repairable,
                "reason": reason,
            }
        )
    return rows


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


def _automation_target_values(text: str) -> tuple[str, ...]:
    """Extract only exact target assignments without parsing an unrelated manifest."""

    values: set[str] = set()
    for match in re.finditer(
        r"^\s*target_thread_id\s*=\s*(.+?)\s*$",
        text,
        flags=re.MULTILINE,
    ):
        try:
            candidate = tomllib.loads(
                f"target_thread_id = {match.group(1)}\n"
            ).get("target_thread_id")
        except tomllib.TOMLDecodeError:
            continue
        if isinstance(candidate, str) and SAFE_ID.fullmatch(candidate):
            values.add(candidate)
    return tuple(sorted(values))


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
        automation_timezone: Callable[[], str | None] | None = None,
        automation_target_query: AutomationTargetQuery | None = None,
    ) -> None:
        self.supervision_root = supervision_root.expanduser().resolve()
        self.automations_root = automations_root.expanduser().resolve()
        self.supervision_owner = supervision_owner.resolve()
        self.weekly_owner = weekly_owner.resolve()
        self.terminal_owner = terminal_owner.resolve()
        self.evolution_owner = evolution_owner.resolve()
        self._now = now or (lambda: datetime.now(UTC))
        self._automation_timezone = automation_timezone or _system_timezone_name
        self._automation_target_query = automation_target_query
        self._lock = RLock()
        self._modules: dict[str, tuple[tuple[Any, ...], ModuleType]] = {}
        self._target_cache: OrderedDict[str, TargetEvidence] = OrderedDict()
        self._automation_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        self._report_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

    def automation_target_query_posture(self) -> dict[str, Any]:
        """Describe whether the read-only duplicate-owner dependency is configured."""

        available = self._automation_target_query is not None
        return {
            "status": "available" if available else "unavailable",
            "version": AUTOMATION_TARGET_QUERY_VERSION,
            "reason": None if available else AUTOMATION_TARGET_QUERY_UNAVAILABLE_REASON,
        }

    def _automation_target_candidates(
        self,
        target_thread_id: str,
    ) -> AutomationTargetQueryResult:
        provider = self._automation_target_query
        if provider is None:
            raise OperationsProjectionError(
                "automation_target_query_unavailable",
                AUTOMATION_TARGET_QUERY_UNAVAILABLE_REASON,
                status=503,
                retryable=True,
            )
        try:
            result = provider(target_thread_id)
        except OperationsProjectionError:
            raise
        except Exception as error:
            raise OperationsProjectionError(
                "automation_target_query_failed",
                "The maintained automation target-query provider failed closed.",
                status=503,
                retryable=True,
            ) from error
        if not isinstance(result, AutomationTargetQueryResult):
            raise OperationsProjectionError(
                "automation_target_query_invalid",
                "The automation target-query provider returned an invalid envelope.",
                status=503,
            )
        now = self._now()
        if now.tzinfo is None:
            raise OperationsProjectionError(
                "automation_target_query_clock_invalid",
                "The automation target-query currentness clock is invalid.",
                status=503,
            )
        now = now.astimezone(UTC)
        observed_at = result.observed_at
        expires_at = result.expires_at
        identities_valid = bool(
            isinstance(result.source_identity, str)
            and 1 <= len(result.source_identity) <= 240
            and SAFE_ID.fullmatch(result.source_identity)
            and isinstance(result.source_revision, str)
            and SHA256.fullmatch(result.source_revision)
            and isinstance(result.currentness, str)
            and SHA256.fullmatch(result.currentness)
        )
        automation_ids_valid = bool(
            isinstance(result.automation_ids, tuple)
            and len(result.automation_ids) <= MAX_AUTOMATIONS
            and result.automation_ids == tuple(sorted(set(result.automation_ids)))
            and all(
                isinstance(automation_id, str) and SAFE_ID.fullmatch(automation_id)
                for automation_id in result.automation_ids
            )
        )
        timestamps_valid = bool(
            isinstance(observed_at, datetime)
            and isinstance(expires_at, datetime)
            and observed_at.tzinfo is not None
            and expires_at.tzinfo is not None
        )
        if not (
            result.version == AUTOMATION_TARGET_QUERY_VERSION
            and result.target_thread_id == target_thread_id
            and identities_valid
            and automation_ids_valid
            and timestamps_valid
        ):
            raise OperationsProjectionError(
                "automation_target_query_invalid",
                "The automation target-query provider returned an ambiguous or incompatible result.",
                status=503,
            )
        observed_utc = observed_at.astimezone(UTC)
        expires_utc = expires_at.astimezone(UTC)
        if observed_utc > now + timedelta(seconds=5) or expires_utc <= observed_utc:
            raise OperationsProjectionError(
                "automation_target_query_invalid",
                "The automation target-query freshness interval is invalid.",
                status=503,
            )
        if expires_utc <= now:
            raise OperationsProjectionError(
                "automation_target_query_stale",
                "The automation target-query candidate set is stale.",
                status=409,
                retryable=True,
            )
        return result

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

    def _gmail_cadence_snapshot(
        self,
        target_thread_id: str,
        policy: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """Resolve the bound Gmail automation's current owner-derived cadence."""

        runtime = policy.get("runtime")
        runtime = runtime if isinstance(runtime, Mapping) else {}
        if not all(
            isinstance(runtime.get(key), str) and runtime[key]
            for key in ("gmail_gate_thread_id", "gmail_poll_automation_id")
        ):
            return None
        try:
            payload = self._owner_command(
                ["gmail-cadence", "--target-thread", target_thread_id]
            )
            mode = payload.get("mode")
            quiet = payload.get("quiet_interval_minutes")
            active = payload.get("active_interval_minutes")
            window = payload.get("active_window_minutes")
            desired_rrule = payload.get("desired_rrule")
            expected_interval = active if mode == "active" else quiet
            if (
                mode not in {"active", "quiet"}
                or type(quiet) is not int
                or type(active) is not int
                or type(window) is not int
                or not 2 <= quiet <= 10
                or not 1 <= active < quiet
                or not 5 <= window <= 120
                or desired_rrule
                != f"RRULE:FREQ=MINUTELY;INTERVAL={expected_interval}"
            ):
                raise OperationsProjectionError(
                    "gmail_cadence_invalid",
                    "The maintained Gmail cadence owner returned an invalid contract.",
                    status=422,
                )
            return {
                "status": "available",
                "mode": mode,
                "desired_rrule": desired_rrule,
                "quiet_interval_minutes": quiet,
                "active_interval_minutes": active,
                "active_window_minutes": window,
                "last_activity_record_id": _bounded(
                    payload.get("last_activity_record_id"), 160
                ),
                "last_activity_at": _bounded(payload.get("last_activity_at"), 80),
                "active_until": _bounded(payload.get("active_until"), 80),
                "seconds_until_quiet": payload.get("seconds_until_quiet"),
                "error": None,
            }
        except OperationsProjectionError as error:
            return {
                "status": "unavailable",
                "mode": None,
                "desired_rrule": None,
                "quiet_interval_minutes": None,
                "active_interval_minutes": None,
                "active_window_minutes": None,
                "last_activity_record_id": None,
                "last_activity_at": None,
                "active_until": None,
                "seconds_until_quiet": None,
                "error": {
                    "code": error.code,
                    "message": str(error),
                    "retryable": error.retryable,
                },
            }

    def policy_control_snapshot(
        self,
        target_thread_id: str,
        *,
        automation_roles: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Read one validated policy/history head and selected named automations."""

        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        unresolved = self.supervision_root / target_thread_id
        if unresolved.is_symlink():
            raise OperationsProjectionError(
                "supervision_target_symlink_rejected",
                "Supervision target must not be a symlink.",
                status=422,
            )
        try:
            directory = unresolved.resolve(strict=True)
        except OSError as error:
            raise OperationsProjectionError(
                "run_not_found",
                "Supervision target is not discoverable.",
                status=404,
            ) from error
        if directory.parent != self.supervision_root or not directory.is_dir():
            raise OperationsProjectionError(
                "supervision_target_invalid",
                "Supervision target escaped its canonical owner root.",
                status=422,
            )
        evidence, cache_status = self._load_target(directory)
        if not evidence.policy_history:
            raise OperationsProjectionError(
                "policy_history_unavailable",
                "The validated policy has no canonical history record.",
                status=422,
            )
        history_head = evidence.policy_history[-1]
        history_policy = history_head.get("policy")
        if (
            not isinstance(history_policy, Mapping)
            or history_policy.get("policy_version") != evidence.policy.get("policy_version")
            or history_policy.get("policy_sha256") != evidence.policy.get("policy_sha256")
        ):
            raise OperationsProjectionError(
                "policy_history_head_mismatch",
                "The current policy does not match the canonical policy-history head.",
                status=422,
            )
        runtime = evidence.policy.get("runtime")
        runtime = runtime if isinstance(runtime, Mapping) else {}
        automation_keys = {
            "watcher": "routine_automation_id",
            "reviewer": "meta_automation_id",
            "gmail_gate": "gmail_poll_automation_id",
            "roundup_writer": "roundup_automation_id",
        }
        selected_roles = (
            set(automation_keys) | {"weekly_report"}
            if automation_roles is None
            else set(automation_roles)
        )
        if not selected_roles.issubset(set(automation_keys) | {"weekly_report"}):
            raise OperationsProjectionError(
                "automation_role_unsupported",
                "The selected policy-control automation role is unsupported.",
                status=422,
            )
        automations: dict[str, dict[str, Any] | None] = {}
        for role, key in automation_keys.items():
            if role not in selected_roles:
                continue
            automation_id = runtime.get(key)
            automations[role] = (
                self._load_automation(automation_id)
                if isinstance(automation_id, str) and automation_id
                else None
            )
        weekly_automation_id = _policy_weekly_report(evidence.policy).get(
            "automation_id"
        )
        if "weekly_report" in selected_roles:
            automations["weekly_report"] = (
                self._load_automation(weekly_automation_id)
                if isinstance(weekly_automation_id, str) and weekly_automation_id
                else None
            )
        gmail_cadence = (
            self._gmail_cadence_snapshot(
                target_thread_id,
                evidence.policy,
            )
            if automation_roles is None or "gmail_gate" in selected_roles
            else None
        )
        calendar_role_selected = bool(
            selected_roles.intersection({"roundup_writer", "weekly_report"})
        )
        automation_timezone = (
            self._automation_timezone() if calendar_role_selected else None
        )
        if not isinstance(automation_timezone, str) or not automation_timezone:
            automation_timezone = None
        if self._target_key(directory) != evidence.cache_key:
            raise OperationsProjectionError(
                "supervision_changed_during_projection",
                "Supervision source changed during policy-control projection; retry.",
                status=409,
                retryable=True,
            )
        owner = self.owner_revisions()["supervision"]
        owner_module = self._module("supervision")
        source_record = next(
            (
                item.get("record_id")
                for item in reversed(evidence.active_events or evidence.events)
                if isinstance(item.get("record_id"), str)
            ),
            None,
        )
        current_state_source = next(
            (
                item
                for item in reversed(evidence.active_events)
                if isinstance(item.get("record_id"), str)
                and isinstance(item.get("record_sha256"), str)
                and SHA256.fullmatch(str(item["record_sha256"]))
                and isinstance(item.get("state_fingerprint"), str)
                and item["state_fingerprint"]
            ),
            None,
        )
        lifecycle_record = next(
            (
                item
                for item in reversed(evidence.active_events)
                if item.get("kind") == "lifecycle"
                and isinstance(item.get("status"), str)
            ),
            None,
        )
        lifecycle_status = (
            lifecycle_record.get("status")
            if isinstance(lifecycle_record, Mapping)
            else None
        )
        post_lifecycle_notifications: list[dict[str, Any]] = []
        if isinstance(lifecycle_record, Mapping):
            lifecycle_record_id = lifecycle_record.get("record_id")
            lifecycle_index = next(
                (
                    index
                    for index, item in enumerate(evidence.events)
                    if item.get("record_id") == lifecycle_record_id
                ),
                None,
            )
            if lifecycle_index is not None:
                post_lifecycle_notifications = [
                    json.loads(json.dumps(item))
                    for item in evidence.events[lifecycle_index + 1 :]
                    if item.get("kind") == "notification"
                    and item.get("status") == "sent"
                ]
        successor_transitions = owner_module.successor_transition_heads(
            list(evidence.events)
        )
        open_successor_transitions = owner_module.successor_transition_heads(
            list(evidence.events),
            open_only=True,
        )
        open_mission_activations = owner_module.mission_activation_heads(
            list(evidence.active_events),
            open_only=True,
        )
        event_head = (
            evidence.events[-1].get("record_sha256") if evidence.events else None
        )
        policy_copy = json.loads(json.dumps(evidence.policy))
        history_copy = json.loads(json.dumps(history_head))
        history_records = json.loads(json.dumps(evidence.policy_history))
        adjustment_contract = policy_adjustment_contract(self._module("supervision"))
        material = {
            "target_thread_id": target_thread_id,
            "owner_sha256": owner["sha256"],
            "policy_sha256": evidence.policy.get("policy_sha256"),
            "policy_version": evidence.policy.get("policy_version"),
            "policy_history_count": len(evidence.policy_history),
            "policy_history_head": history_head.get("record_sha256"),
            "source_record": source_record,
            "current_state_source_record": (
                current_state_source.get("record_id")
                if isinstance(current_state_source, Mapping)
                else None
            ),
            "current_state_source_sha256": (
                current_state_source.get("record_sha256")
                if isinstance(current_state_source, Mapping)
                else None
            ),
            "current_state_fingerprint": (
                current_state_source.get("state_fingerprint")
                if isinstance(current_state_source, Mapping)
                else None
            ),
            "event_head": event_head,
            "event_count": len(evidence.events),
            "active_event_count": len(evidence.active_events),
            "lifecycle_record_sha256": (
                lifecycle_record.get("record_sha256")
                if isinstance(lifecycle_record, Mapping)
                else None
            ),
            "post_lifecycle_notification_sha256s": [
                item.get("record_sha256")
                for item in post_lifecycle_notifications
            ],
            "lifecycle_status": lifecycle_status,
            "open_successor_transition_ids": sorted(open_successor_transitions),
            "successor_transition_ids": sorted(successor_transitions),
            "open_mission_activation_ids": sorted(open_mission_activations),
            "automations": {
                role: automation.get("manifest_sha256") if automation else None
                for role, automation in automations.items()
            },
            "gmail_cadence": (
                {
                    key: gmail_cadence.get(key)
                    for key in (
                        "status",
                        "mode",
                        "desired_rrule",
                        "quiet_interval_minutes",
                        "active_interval_minutes",
                        "active_window_minutes",
                        "last_activity_record_id",
                        "last_activity_at",
                        "active_until",
                    )
                }
                if isinstance(gmail_cadence, Mapping)
                else None
            ),
            "automation_timezone": automation_timezone,
        }
        return {
            **material,
            "fingerprint": _digest(material),
            "cache_status": cache_status,
            "lifecycle_status": lifecycle_status,
            "lifecycle_record": (
                json.loads(json.dumps(lifecycle_record))
                if isinstance(lifecycle_record, Mapping)
                else None
            ),
            "current_state_source": (
                json.loads(json.dumps(current_state_source))
                if isinstance(current_state_source, Mapping)
                else None
            ),
            "post_lifecycle_notifications": post_lifecycle_notifications,
            "open_successor_transitions": json.loads(
                json.dumps(open_successor_transitions)
            ),
            "successor_transitions": json.loads(json.dumps(successor_transitions)),
            "open_mission_activations": json.loads(
                json.dumps(open_mission_activations)
            ),
            "policy": policy_copy,
            "adjustable": policy_adjustable_values(policy_copy),
            "policy_history_head_record": history_copy,
            "policy_history_records": history_records,
            "adjustment_contract": adjustment_contract,
            "runtime": {
                key: runtime.get(key)
                for key in (
                    "watcher_thread_id",
                    "base_reviewer_thread_id",
                    "reviewer_thread_id",
                    "notice_reviewer_thread_id",
                    "fix_executor_thread_id",
                    "gmail_gate_thread_id",
                    "gmail_processor_thread_id",
                    "roundup_thread_id",
                    "roundup_automation_id",
                    *automation_keys.values(),
                )
            },
            "automations_by_role": automations,
            "gmail_cadence": gmail_cadence,
            "automation_timezone": automation_timezone,
        }

    def mission_history_snapshot(self, target_thread_id: str) -> dict[str, Any]:
        """Return exact mission segmentation without promoting historical state."""

        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        unresolved = self.supervision_root / target_thread_id
        if unresolved.is_symlink():
            raise OperationsProjectionError(
                "supervision_target_symlink_rejected",
                "Supervision target must not be a symlink.",
                status=422,
            )
        try:
            directory = unresolved.resolve(strict=True)
        except OSError as error:
            raise OperationsProjectionError(
                "run_not_found",
                "Supervision target is not discoverable.",
                status=404,
            ) from error
        if directory.parent != self.supervision_root or not directory.is_dir():
            raise OperationsProjectionError(
                "supervision_target_invalid",
                "Supervision target escaped its canonical owner root.",
                status=422,
            )
        evidence, cache_status = self._load_target(directory)
        owner = self._module("supervision")
        binding = owner.bound_mission(evidence.policy)
        active_root = (
            binding.get("mission_root") if isinstance(binding, Mapping) else None
        )
        segments = self._mission_segments(evidence)
        active_record_ids = [
            item.get("record_id")
            for item in evidence.active_events
            if isinstance(item.get("record_id"), str)
        ]
        active_record_sha256s = [
            item.get("record_sha256")
            for item in evidence.active_events
            if isinstance(item.get("record_sha256"), str)
            and SHA256.fullmatch(str(item["record_sha256"]))
        ]
        material = {
            "target_thread_id": target_thread_id,
            "active_mission_root": active_root,
            "policy_sha256": evidence.policy.get("policy_sha256"),
            "segments": segments,
            "active_record_ids": active_record_ids,
            "active_record_sha256s": active_record_sha256s,
        }
        return {
            **material,
            "fingerprint": _digest(material),
            "cache_status": cache_status,
        }

    def mission_successor_plan_snapshot(
        self,
        target_thread_id: str,
        *,
        source_record: str,
        source_sha256: str,
        predecessor_disposition: str,
        first_eligible_work: str,
        reason: str,
    ) -> dict[str, Any]:
        """Plan one same-target mission succession through the maintained owner."""

        if (
            not SAFE_ID.fullmatch(target_thread_id)
            or not SAFE_ID.fullmatch(source_record)
            or not SHA256.fullmatch(source_sha256)
            or predecessor_disposition not in {"completed", "superseded"}
            or not isinstance(first_eligible_work, str)
            or not first_eligible_work
            or len(first_eligible_work) > 160
            or "\n" in first_eligible_work
            or "\r" in first_eligible_work
            or not isinstance(reason, str)
            or not reason
            or len(reason) > 480
            or "\n" in reason
            or "\r" in reason
            or any(
                marker in value
                for value in (first_eligible_work, reason)
                for marker in ("/Users/", "file://", "\\Users\\")
            )
        ):
            raise OperationsProjectionError(
                "mission_successor_input_invalid",
                "Mission succession requires exact bounded source, disposition, first-work, and reason fields.",
                status=422,
            )
        before = self.policy_control_snapshot(target_thread_id)
        history_before = self.mission_history_snapshot(target_thread_id)
        policy = before.get("policy")
        if not isinstance(policy, Mapping):
            raise OperationsProjectionError(
                "mission_successor_policy_unavailable",
                "The current supervision policy is unavailable.",
                status=409,
            )
        owner = self._module("supervision")
        current = owner.bound_mission(dict(policy))
        if (
            not isinstance(current, Mapping)
            or not owner.mission_binding_is_supported(
                current,
                target_thread=target_thread_id,
            )
        ):
            raise OperationsProjectionError(
                "mission_successor_predecessor_unavailable",
                "Mission succession requires one supported current predecessor binding.",
                status=409,
            )
        try:
            successor = owner.derive_mission_binding(
                target_thread=target_thread_id,
                source_class="direct-user",
                source_record=source_record,
                source_sha256=source_sha256,
            )
        except Exception as error:
            raise OperationsProjectionError(
                "mission_successor_source_invalid",
                "The maintained owner rejected the exact direct-user successor source.",
                status=422,
            ) from error
        if (
            current.get("mission_source_record") == source_record
            or owner.mission_binding_identity(current)
            == owner.mission_binding_identity(successor)
        ):
            raise OperationsProjectionError(
                "mission_successor_unchanged",
                "The candidate source derives the already-current mission binding.",
                status=409,
            )

        directory = (self.supervision_root / target_thread_id).resolve(strict=True)
        evidence, _cache_status = self._load_target(directory)
        if evidence.policy.get("policy_sha256") != before.get("policy_sha256"):
            raise OperationsProjectionError(
                "mission_successor_source_changed",
                "The policy changed while the succession plan was being composed.",
                status=409,
                retryable=True,
            )
        all_events = list(evidence.events)
        incident_heads: dict[str, Mapping[str, Any]] = {}
        decision_heads: dict[str, Mapping[str, Any]] = {}
        for item in all_events:
            incident_id = item.get("incident_id")
            if incident_id and owner.is_substantive_incident_record(
                item,
                str(incident_id),
            ):
                incident_heads[str(incident_id)] = item
            if item.get("kind") == "decision" and item.get("decision_id"):
                decision_heads[str(item["decision_id"])] = item
        open_incidents = sorted(
            incident_id
            for incident_id, item in incident_heads.items()
            if not owner.is_terminal_incident_record(item, incident_id)
        )
        open_decisions = sorted(
            decision_id
            for decision_id, item in decision_heads.items()
            if item.get("phase") != "target-acknowledged"
        )
        open_transitions = owner.successor_transition_heads(
            all_events,
            open_only=True,
        )
        scoped_events = owner.mission_scoped_events(
            directory,
            dict(policy),
            all_events,
        )
        open_activations = owner.mission_activation_heads(
            scoped_events,
            open_only=True,
        )
        if open_incidents or open_decisions or open_transitions or open_activations:
            raise OperationsProjectionError(
                "mission_successor_open_heads",
                "Mission succession requires closed incidents, decisions, successor transitions, and current mission activation.",
                status=409,
            )
        lifecycle = [item for item in scoped_events if item.get("kind") == "lifecycle"]
        predecessor_terminal = lifecycle[-1] if lifecycle else None
        if predecessor_disposition == "completed" and (
            not isinstance(predecessor_terminal, Mapping)
            or predecessor_terminal.get("status") != "completed"
            or not isinstance(predecessor_terminal.get("record_id"), str)
        ):
            raise OperationsProjectionError(
                "mission_successor_completion_unavailable",
                "Completed succession requires one exact current predecessor completion lifecycle.",
                status=409,
            )
        expected_evidence = [source_record]
        if predecessor_disposition == "completed":
            expected_evidence.append(str(predecessor_terminal["record_id"]))
        expected_policy = json.loads(json.dumps(policy))
        expected_policy["mission_binding"] = successor
        expected_policy["policy_version"] = int(policy.get("policy_version", 0)) + 1
        expected_policy.pop("policy_sha256", None)
        expected_policy.pop("updated_at", None)
        expected_normalized_policy_sha256 = _digest(expected_policy)
        current_segment = next(
            (
                item
                for item in history_before["segments"]
                if item.get("posture") == "current"
            ),
            None,
        )
        if (
            not isinstance(current_segment, Mapping)
            or current_segment.get("mission_root") != current.get("mission_root")
        ):
            raise OperationsProjectionError(
                "mission_successor_history_unavailable",
                "The exact predecessor mission segment is unavailable.",
                status=409,
            )
        after = self.policy_control_snapshot(target_thread_id)
        history_after = self.mission_history_snapshot(target_thread_id)
        if (
            before.get("fingerprint") != after.get("fingerprint")
            or history_before.get("fingerprint") != history_after.get("fingerprint")
        ):
            raise OperationsProjectionError(
                "mission_successor_source_changed",
                "Mission, policy, history, or open-head evidence changed during planning.",
                status=409,
                retryable=True,
            )
        material = {
            "target_thread_id": target_thread_id,
            "control_fingerprint": before.get("fingerprint"),
            "history_fingerprint": history_before.get("fingerprint"),
            "predecessor": current,
            "successor": successor,
            "predecessor_disposition": predecessor_disposition,
            "predecessor_terminal_record": (
                predecessor_terminal.get("record_id")
                if isinstance(predecessor_terminal, Mapping)
                else None
            ),
            "source_record": source_record,
            "source_sha256": source_sha256,
            "first_eligible_work": first_eligible_work,
            "reason": reason,
            "expected_evidence": expected_evidence,
            "expected_policy_version": expected_policy["policy_version"],
            "expected_normalized_policy_sha256": expected_normalized_policy_sha256,
            "policy_history_head": before.get("policy_history_head"),
            "policy_history_count": len(before.get("policy_history_records", [])),
            "predecessor_segment": current_segment,
        }
        return {
            **material,
            "fingerprint": _digest(material),
            "owner_sha256": before.get("owner_sha256"),
            "policy_sha256": before.get("policy_sha256"),
            "policy_version": before.get("policy_version"),
            "expected_history_kind": "policy-mission-successor",
            "expected_history_reason": f"{predecessor_disposition}: {reason}",
            "open_incident_ids": open_incidents,
            "open_decision_ids": open_decisions,
            "open_successor_transition_ids": sorted(open_transitions),
            "open_mission_activation_ids": sorted(open_activations),
            "control": before,
            "history": history_before,
        }

    def lifecycle_gate_snapshot(
        self,
        target_thread_id: str,
        *,
        lifecycle_state: str,
        source_record: str,
        state_fingerprint: str,
    ) -> dict[str, Any]:
        """Run the maintained lifecycle gate read-only against one exact record."""

        if lifecycle_state not in {"completed", "paused", "blocked", "failed", "stopped"}:
            raise OperationsProjectionError(
                "lifecycle_state_invalid",
                "The requested lifecycle state is unsupported.",
                status=422,
            )
        if not SAFE_ID.fullmatch(target_thread_id) or not SAFE_ID.fullmatch(source_record):
            raise OperationsProjectionError(
                "lifecycle_source_invalid",
                "The lifecycle target or source record identity is invalid.",
                status=422,
            )
        if not isinstance(state_fingerprint, str) or not state_fingerprint:
            raise OperationsProjectionError(
                "lifecycle_source_invalid",
                "The lifecycle state fingerprint is required.",
                status=422,
            )
        before = self.policy_control_snapshot(target_thread_id)
        record = before.get("lifecycle_record")
        if (
            not isinstance(record, Mapping)
            or record.get("record_id") != source_record
            or record.get("kind") != "lifecycle"
            or record.get("status") != lifecycle_state
            or record.get("state_fingerprint") != state_fingerprint
        ):
            raise OperationsProjectionError(
                "lifecycle_source_mismatch",
                "The exact current lifecycle record does not match the requested gate source.",
                status=409,
            )
        payload = self._owner_command(
            [
                "lifecycle-gate",
                "--target-thread",
                target_thread_id,
                "--lifecycle-state",
                lifecycle_state,
                "--source-record",
                source_record,
                "--state-fingerprint",
                state_fingerprint,
            ]
        )
        after = self.policy_control_snapshot(target_thread_id)
        if before.get("fingerprint") != after.get("fingerprint"):
            raise OperationsProjectionError(
                "lifecycle_source_changed",
                "The lifecycle source changed while the maintained gate was evaluated.",
                status=409,
                retryable=True,
            )
        required = {
            "completion_permitted",
            "duplicate",
            "lifecycle_state",
            "notification_category",
            "notification_dedup_key",
            "open_mission_activations",
            "open_successor_transitions",
            "policy_sha256",
            "send_now",
            "source_record",
            "source_stop_permitted",
            "state_fingerprint",
            "supervision_pause_permitted",
        }
        if (
            not required.issubset(payload)
            or payload.get("lifecycle_state") != lifecycle_state
            or payload.get("source_record") != source_record
            or payload.get("state_fingerprint") != state_fingerprint
            or payload.get("policy_sha256") != before.get("policy_sha256")
            or not isinstance(payload.get("notification_category"), str)
            or not payload["notification_category"]
            or not isinstance(payload.get("notification_dedup_key"), str)
            or not payload["notification_dedup_key"]
            or not isinstance(payload.get("open_mission_activations"), list)
            or not isinstance(payload.get("open_successor_transitions"), list)
            or any(
                type(payload.get(key)) is not bool
                for key in (
                    "completion_permitted",
                    "duplicate",
                    "send_now",
                    "source_stop_permitted",
                    "supervision_pause_permitted",
                )
            )
        ):
            raise OperationsProjectionError(
                "lifecycle_gate_output_invalid",
                "The maintained lifecycle gate returned an invalid contract.",
                status=503,
            )
        notifications = before.get("post_lifecycle_notifications")
        notifications = notifications if isinstance(notifications, list) else []
        matching_notifications = [
            item
            for item in notifications
            if isinstance(item, Mapping)
            and item.get("category") == payload["notification_category"]
            and (
                item.get("dedup_key") == payload["notification_dedup_key"]
                or (
                    isinstance(item.get("evidence"), list)
                    and source_record in item["evidence"]
                )
            )
        ]
        notification_record: Mapping[str, Any] | None = None
        if payload.get("duplicate") is True:
            if (
                len(matching_notifications) != 1
                or not isinstance(matching_notifications[0].get("record_id"), str)
                or not SAFE_ID.fullmatch(str(matching_notifications[0]["record_id"]))
                or not isinstance(
                    matching_notifications[0].get("record_sha256"), str
                )
                or not SHA256.fullmatch(
                    str(matching_notifications[0]["record_sha256"])
                )
                or _event_time(matching_notifications[0]) is None
            ):
                raise OperationsProjectionError(
                    "lifecycle_notification_evidence_invalid",
                    "The maintained lifecycle notification is missing, duplicated, or malformed.",
                    status=409,
                )
            notification_record = matching_notifications[0]
        elif matching_notifications:
            raise OperationsProjectionError(
                "lifecycle_notification_evidence_inconsistent",
                "Canonical notification evidence disagrees with the maintained lifecycle gate.",
                status=409,
            )
        currentness = _digest(
            {
                "control": before.get("fingerprint"),
                "owner": before.get("owner_sha256"),
                "record": record.get("record_sha256"),
                "notification": (
                    notification_record.get("record_sha256")
                    if isinstance(notification_record, Mapping)
                    else None
                ),
                "gate": payload,
            }
        )
        return {
            "target_thread_id": target_thread_id,
            "owner_sha256": before.get("owner_sha256"),
            "source_record_sha256": record.get("record_sha256"),
            "notification_record": (
                json.loads(json.dumps(notification_record))
                if isinstance(notification_record, Mapping)
                else None
            ),
            "control_fingerprint": before.get("fingerprint"),
            "currentness": currentness,
            "gate": json.loads(json.dumps(payload)),
        }

    def supervision_resume_gate_snapshot(
        self,
        target_thread_id: str,
        *,
        pause_record: str,
        source_record: str,
        state_fingerprint: str,
    ) -> dict[str, Any]:
        """Run the maintained semantic-resume gate without mutating an owner."""

        if (
            not SAFE_ID.fullmatch(target_thread_id)
            or not SAFE_ID.fullmatch(pause_record)
            or not SAFE_ID.fullmatch(source_record)
            or not isinstance(state_fingerprint, str)
            or not state_fingerprint
            or len(state_fingerprint) > 128
        ):
            raise OperationsProjectionError(
                "supervision_resume_source_invalid",
                "The resume target, pause, source, or state identity is invalid.",
                status=422,
            )
        before = self.policy_control_snapshot(target_thread_id)
        payload = self._owner_command(
            [
                "resume-gate",
                "--target-thread",
                target_thread_id,
                "--pause-record",
                pause_record,
                "--source-record",
                source_record,
                "--state-fingerprint",
                state_fingerprint,
            ]
        )
        after = self.policy_control_snapshot(target_thread_id)
        if before.get("fingerprint") != after.get("fingerprint"):
            raise OperationsProjectionError(
                "supervision_resume_source_changed",
                "The resume lifecycle, policy, source, or named automation owners changed during validation.",
                status=409,
                retryable=True,
            )
        status = payload.get("status")
        if status == "already-resumed":
            record = payload.get("resume_record")
            current = after.get("lifecycle_record")
            if (
                payload.get("eligible") is not True
                or payload.get("ready_to_finalize") is not True
                or payload.get("duplicate") is not True
                or payload.get("action") != "none"
                or payload.get("policy_sha256") != after.get("policy_sha256")
                or not isinstance(record, Mapping)
                or record.get("kind") != "lifecycle"
                or record.get("category") != "supervision-resume"
                or record.get("status") != "resumed"
                or record.get("resume_contract_version") != 1
                or record.get("pause_record_id") != pause_record
                or record.get("source_record_id") != source_record
                or record.get("state_fingerprint") != state_fingerprint
                or not isinstance(record.get("record_id"), str)
                or not SAFE_ID.fullmatch(str(record["record_id"]))
                or not isinstance(record.get("record_sha256"), str)
                or not SHA256.fullmatch(str(record["record_sha256"]))
                or not isinstance(current, Mapping)
                or current.get("record_id") != record.get("record_id")
                or current.get("record_sha256") != record.get("record_sha256")
            ):
                raise OperationsProjectionError(
                    "supervision_resume_gate_output_invalid",
                    "The maintained resume gate returned an invalid canonical-resume result.",
                    status=503,
                )
        elif status in {"pending-activation", "ready"}:
            states = payload.get("automation_states")
            activate_ids = payload.get("activate_automation_ids")
            required = {
                "action",
                "automation_states",
                "activate_automation_ids",
                "duplicate",
                "eligibility_root",
                "eligible",
                "group_id",
                "mission_root",
                "pause_record_id",
                "policy_sha256",
                "policy_version",
                "ready_to_finalize",
                "source_currentness_root",
                "source_record_id",
                "state_fingerprint",
                "status",
            }
            states_valid = bool(
                isinstance(states, Mapping)
                and 2 <= len(states) <= MAX_AUTOMATIONS
                and all(
                    isinstance(automation_id, str)
                    and SAFE_ID.fullmatch(automation_id)
                    and isinstance(state, Mapping)
                    and set(state)
                    == {
                        "automation_id",
                        "configuration_sha256",
                        "manifest_sha256",
                        "role",
                        "rrule",
                        "status",
                        "target_thread_id",
                        "updated_at",
                    }
                    and state.get("automation_id") == automation_id
                    and isinstance(state.get("role"), str)
                    and bool(state["role"])
                    and state.get("status") in {"ACTIVE", "PAUSED"}
                    and isinstance(state.get("rrule"), str)
                    and bool(state["rrule"])
                    and isinstance(state.get("target_thread_id"), str)
                    and SAFE_ID.fullmatch(str(state["target_thread_id"]))
                    and type(state.get("updated_at")) is int
                    and state["updated_at"] > 0
                    and isinstance(state.get("manifest_sha256"), str)
                    and SHA256.fullmatch(str(state["manifest_sha256"]))
                    and isinstance(state.get("configuration_sha256"), str)
                    and SHA256.fullmatch(str(state["configuration_sha256"]))
                    for automation_id, state in states.items()
                )
            )
            paused_ids = (
                sorted(
                    str(automation_id)
                    for automation_id, state in states.items()
                    if isinstance(state, Mapping) and state.get("status") == "PAUSED"
                )
                if isinstance(states, Mapping)
                else []
            )
            if (
                not required.issubset(payload)
                or payload.get("eligible") is not True
                or payload.get("duplicate") is not False
                or payload.get("pause_record_id") != pause_record
                or payload.get("source_record_id") != source_record
                or payload.get("state_fingerprint") != state_fingerprint
                or payload.get("policy_sha256") != before.get("policy_sha256")
                or payload.get("policy_version") != before.get("policy_version")
                or not isinstance(payload.get("group_id"), str)
                or not payload["group_id"]
                or not isinstance(payload.get("mission_root"), str)
                or not SHA256.fullmatch(str(payload["mission_root"]))
                or not isinstance(payload.get("eligibility_root"), str)
                or not SHA256.fullmatch(str(payload["eligibility_root"]))
                or not isinstance(payload.get("source_currentness_root"), str)
                or not SHA256.fullmatch(str(payload["source_currentness_root"]))
                or not states_valid
                or not isinstance(activate_ids, list)
                or activate_ids != paused_ids
                or payload.get("ready_to_finalize") is not (not paused_ids)
                or status != ("ready" if not paused_ids else "pending-activation")
                or payload.get("action")
                != (
                    "resume-finalize"
                    if not paused_ids
                    else "activate-exact-bound-automations"
                )
            ):
                raise OperationsProjectionError(
                    "supervision_resume_gate_output_invalid",
                    "The maintained resume gate returned an invalid eligibility result.",
                    status=503,
                )
        else:
            raise OperationsProjectionError(
                "supervision_resume_gate_output_invalid",
                "The maintained resume gate returned an unsupported status.",
                status=503,
            )
        currentness = _digest(
            {
                "control": before.get("fingerprint"),
                "owner": before.get("owner_sha256"),
                "pause_record": pause_record,
                "source_record": source_record,
                "state_fingerprint": state_fingerprint,
                "gate": payload,
            }
        )
        return {
            "target_thread_id": target_thread_id,
            "owner_sha256": before.get("owner_sha256"),
            "control_fingerprint": before.get("fingerprint"),
            "currentness": currentness,
            "gate": json.loads(json.dumps(payload)),
        }

    def successor_transition_gate_snapshot(
        self,
        target_thread_id: str,
        *,
        transition_id: str,
        task_creation_authority: str,
    ) -> dict[str, Any]:
        """Run the maintained successor-transition gate against one exact head."""

        if (
            not SAFE_ID.fullmatch(target_thread_id)
            or not SAFE_ID.fullmatch(transition_id)
            or task_creation_authority not in {"available", "unavailable"}
        ):
            raise OperationsProjectionError(
                "successor_transition_source_invalid",
                "The successor-transition target, identity, or authority posture is invalid.",
                status=422,
            )
        before = self.policy_control_snapshot(target_thread_id)
        heads = before.get("successor_transitions")
        heads = heads if isinstance(heads, Mapping) else {}
        head = heads.get(transition_id)
        if not isinstance(head, Mapping):
            raise OperationsProjectionError(
                "successor_transition_not_open",
                "The exact successor transition is not a canonical head.",
                status=409,
            )
        record_id = head.get("record_id")
        record_sha256 = head.get("record_sha256")
        if (
            not isinstance(record_id, str)
            or not SAFE_ID.fullmatch(record_id)
            or not isinstance(record_sha256, str)
            or not SHA256.fullmatch(record_sha256)
        ):
            raise OperationsProjectionError(
                "successor_transition_head_invalid",
                "The canonical successor-transition head identity is incomplete.",
                status=422,
            )
        payload = self._owner_command(
            [
                "successor-transition-gate",
                "--target-thread",
                target_thread_id,
                "--transition-id",
                transition_id,
                "--task-creation-authority",
                task_creation_authority,
            ]
        )
        after = self.policy_control_snapshot(target_thread_id)
        if before.get("fingerprint") != after.get("fingerprint"):
            raise OperationsProjectionError(
                "successor_transition_source_changed",
                "The successor-transition source changed while its maintained gate was evaluated.",
                status=409,
                retryable=True,
            )
        required = {
            "transition_id",
            "phase",
            "transition_open",
            "source_stop_permitted",
            "required_source_posture",
            "next_action",
            "direct_task_creation_authority_required",
            "human_input_required",
            "task_creation_authority",
            "failure_mode_if_stopped",
            "tracker_sha256",
            "tracker_source_record",
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
            "first_eligible_block",
            "policy_sha256",
            "record_id",
        }
        if (
            not required.issubset(payload)
            or payload.get("transition_id") != transition_id
            or payload.get("phase") != head.get("phase")
            or payload.get("record_id") != record_id
            or payload.get("task_creation_authority") != task_creation_authority
            or payload.get("tracker_sha256") != head.get("tracker_sha256")
            or payload.get("tracker_source_record")
            != head.get("tracker_source_record")
            or payload.get("first_eligible_block") != head.get("first_eligible_block")
            or payload.get("successor_thread_id")
            != (head.get("successor_thread_id") or None)
            or payload.get("successor_mission_root")
            != (head.get("successor_mission_root") or None)
            or payload.get("successor_group_id")
            != (head.get("successor_group_id") or None)
            or payload.get("policy_sha256") != before.get("policy_sha256")
            or any(
                type(payload.get(field)) is not bool
                for field in (
                    "transition_open",
                    "source_stop_permitted",
                    "direct_task_creation_authority_required",
                    "human_input_required",
                )
            )
            or not isinstance(payload.get("next_action"), str)
            or not payload["next_action"]
        ):
            raise OperationsProjectionError(
                "successor_transition_gate_invalid",
                "The maintained successor-transition gate returned an inconsistent contract.",
                status=503,
            )
        return {
            "target_thread_id": target_thread_id,
            "transition_id": transition_id,
            "head": json.loads(json.dumps(head)),
            "head_record_sha256": record_sha256,
            "control_fingerprint": before.get("fingerprint"),
            "owner_sha256": before.get("owner_sha256"),
            "currentness": _digest(
                {
                    "control": before.get("fingerprint"),
                    "owner": before.get("owner_sha256"),
                    "head": record_sha256,
                    "gate": payload,
                }
            ),
            "gate": json.loads(json.dumps(payload)),
        }

    @staticmethod
    def _policy_automation_id(
        policy: Mapping[str, Any],
        role: str,
    ) -> str | None:
        contract = AUTOMATION_BINDING_CONTRACTS.get(role)
        if contract is None:
            return None
        if contract["policy_source"] == "weekly_report":
            value = _policy_weekly_report(policy).get("automation_id")
        else:
            runtime = policy.get("runtime")
            runtime = runtime if isinstance(runtime, Mapping) else {}
            value = runtime.get(contract["automation_key"])
        return value if isinstance(value, str) and value else None

    def automation_binding_claims(self, automation_id: str) -> list[dict[str, Any]]:
        """Return only canonical policy claims for one named automation ID."""

        if not SAFE_ID.fullmatch(automation_id):
            raise OperationsProjectionError(
                "automation_id_invalid",
                "Automation ID is invalid.",
                status=422,
            )
        claims: list[dict[str, Any]] = []
        observed: list[TargetEvidence] = []
        for directory in self._target_directories():
            evidence, _cache_status = self._load_target(directory)
            observed.append(evidence)
            policy = evidence.policy
            runtime = policy.get("runtime")
            runtime = runtime if isinstance(runtime, Mapping) else {}
            for role, contract in AUTOMATION_BINDING_CONTRACTS.items():
                if self._policy_automation_id(policy, role) != automation_id:
                    continue
                claims.append(
                    {
                        "target_thread_id": evidence.target_thread_id,
                        "role": role,
                        "label": contract["label"],
                        "purpose": contract["purpose"],
                        "role_thread_id": runtime.get(contract["thread_key"]),
                        "policy_version": policy.get("policy_version"),
                        "policy_sha256": policy.get("policy_sha256"),
                    }
                )
        if any(
            self._target_key(evidence.directory) != evidence.cache_key
            for evidence in observed
        ):
            raise OperationsProjectionError(
                "automation_binding_claims_changed",
                "A canonical automation binding changed during the duplicate-role check; retry.",
                status=409,
                retryable=True,
            )
        return sorted(
            claims,
            key=lambda item: (
                str(item["target_thread_id"]),
                str(item["role"]),
                str(item["purpose"]),
            ),
        )

    def active_automation_target_owners(
        self,
        *,
        target_thread_id: str,
        supervision_target_thread_id: str,
        role: str,
        selected_automation_id: str,
    ) -> dict[str, Any]:
        """Prove which active heartbeat owners currently target one exact role task."""

        if not all(
            SAFE_ID.fullmatch(value)
            for value in (
                target_thread_id,
                supervision_target_thread_id,
                selected_automation_id,
            )
        ) or role not in AUTOMATION_BINDING_CONTRACTS:
            raise OperationsProjectionError(
                "automation_target_owner_check_invalid",
                "The duplicate-role owner check received an invalid exact identity.",
                status=422,
            )
        def unavailable_result(error: OperationsProjectionError) -> dict[str, Any]:
            material = {
                "status": "unavailable",
                "target_thread_id": target_thread_id,
                "selected_automation_id": selected_automation_id,
                "unavailable_automation_ids": [],
                "owners": [],
                "conflicting_owner_ids": [],
                "target_query": {
                    "status": "unavailable",
                    "version": AUTOMATION_TARGET_QUERY_VERSION,
                    "error": {
                        "code": error.code,
                        "message": str(error),
                        "retryable": error.retryable,
                    },
                },
            }
            return {**material, "fingerprint": _digest(material)}

        try:
            target_query = self._automation_target_candidates(target_thread_id)
        except OperationsProjectionError as error:
            return unavailable_result(error)
        candidate_ids = set(target_query.automation_ids)
        candidate_ids.add(selected_automation_id)
        inventory = {
            automation_id: self._load_automation(automation_id)
            for automation_id in sorted(candidate_ids)
        }
        try:
            current_target_query = self._automation_target_candidates(target_thread_id)
        except OperationsProjectionError as error:
            return unavailable_result(error)
        if current_target_query != target_query:
            return unavailable_result(
                OperationsProjectionError(
                    "automation_target_query_changed",
                    "The exact automation target-query result changed during the read; retry.",
                    status=409,
                    retryable=True,
                )
            )
        unavailable = sorted(
            automation_id
            for automation_id, item in inventory.items()
            if not isinstance(item, Mapping) or item.get("status") != "available"
        )
        if selected_automation_id not in inventory:
            unavailable.append(selected_automation_id)
        if unavailable:
            material = {
                "status": "unavailable",
                "target_thread_id": target_thread_id,
                "selected_automation_id": selected_automation_id,
                "unavailable_automation_ids": sorted(set(unavailable)),
                "owners": [],
                "conflicting_owner_ids": [],
                "target_query": {
                    "status": "available",
                    "version": target_query.version,
                    "source_identity": target_query.source_identity,
                    "source_revision": target_query.source_revision,
                    "currentness": target_query.currentness,
                    "observed_at": target_query.observed_at.isoformat(),
                    "expires_at": target_query.expires_at.isoformat(),
                    "automation_ids": list(target_query.automation_ids),
                },
            }
            return {**material, "fingerprint": _digest(material)}

        inconsistent_candidates = sorted(
            automation_id
            for automation_id in target_query.automation_ids
            if inventory[automation_id].get("target_thread_id") != target_thread_id
        )
        if inconsistent_candidates:
            return unavailable_result(
                OperationsProjectionError(
                    "automation_target_query_inconsistent",
                    "A returned automation candidate does not target the exact queried task.",
                    status=409,
                    retryable=True,
                )
            )

        owners: list[dict[str, Any]] = []
        for automation_id, item in sorted(inventory.items()):
            if not (
                item.get("owner_status") == "ACTIVE"
                and item.get("kind") == "heartbeat"
                and item.get("target_thread_id") == target_thread_id
            ):
                continue
            claims = self.automation_binding_claims(automation_id)
            if automation_id == selected_automation_id:
                relation = "selected-role"
            elif (
                len(claims) == 1
                and claims[0].get("target_thread_id")
                == supervision_target_thread_id
                and claims[0].get("role") != role
                and claims[0].get("role_thread_id") == target_thread_id
            ):
                relation = "distinct-canonical-role"
            else:
                relation = "conflicting-or-unclaimed-role"
            owners.append(
                {
                    "automation_id": automation_id,
                    "manifest_sha256": item.get("manifest_sha256"),
                    "relation": relation,
                    "canonical_claims": claims,
                }
            )
        conflicting_owner_ids = sorted(
            str(item["automation_id"])
            for item in owners
            if item["relation"] == "conflicting-or-unclaimed-role"
        )
        material = {
            "status": "available",
            "target_thread_id": target_thread_id,
            "selected_automation_id": selected_automation_id,
            "unavailable_automation_ids": [],
            "owners": owners,
            "conflicting_owner_ids": conflicting_owner_ids,
            "target_query": {
                "status": "available",
                "version": target_query.version,
                "source_identity": target_query.source_identity,
                "source_revision": target_query.source_revision,
                "currentness": target_query.currentness,
                "observed_at": target_query.observed_at.isoformat(),
                "expires_at": target_query.expires_at.isoformat(),
                "automation_ids": list(target_query.automation_ids),
            },
        }
        return {**material, "fingerprint": _digest(material)}

    def automation_binding_snapshot(
        self,
        target_thread_id: str,
        role: str,
    ) -> dict[str, Any]:
        """Read one policy, its named automation, and exact duplicate policy claims."""

        contract = AUTOMATION_BINDING_CONTRACTS.get(role)
        if contract is None:
            raise OperationsProjectionError(
                "automation_role_unsupported",
                "The selected automation role is not supported.",
                status=422,
            )
        control = self.policy_control_snapshot(
            target_thread_id,
            automation_roles=(role,),
        )
        policy = control.get("policy")
        runtime = control.get("runtime")
        automations = control.get("automations_by_role")
        if not all(isinstance(value, Mapping) for value in (policy, runtime, automations)):
            raise OperationsProjectionError(
                "automation_binding_source_unavailable",
                "The canonical policy or named automation projection is unavailable.",
                status=422,
            )
        automation_id = self._policy_automation_id(policy, role)
        if automation_id is None:
            raise OperationsProjectionError(
                "automation_binding_missing",
                "The maintained bind owner has no exact existing automation ID for this role.",
                status=409,
            )
        expected_target = runtime.get(contract["thread_key"])
        expected_rrule = _expected_automation_rrule(
            policy,
            role,
            gmail_cadence=control.get("gmail_cadence"),
        )
        expected_timezone = _expected_automation_timezone(policy, role)
        actual_timezone = (
            "not-applicable-to-interval-schedule"
            if expected_timezone == "not-applicable-to-interval-schedule"
            else control.get("automation_timezone")
        )
        actual = automations.get(role)
        claims = self.automation_binding_claims(automation_id)
        target_owners = (
            self.active_automation_target_owners(
                target_thread_id=expected_target,
                supervision_target_thread_id=target_thread_id,
                role=role,
                selected_automation_id=automation_id,
            )
            if isinstance(expected_target, str) and expected_target
            else {
                "status": "unavailable",
                "target_thread_id": expected_target,
                "selected_automation_id": automation_id,
                "unavailable_automation_ids": [],
                "owners": [],
                "conflicting_owner_ids": [],
                "fingerprint": None,
            }
        )
        exact_claim = {
            "target_thread_id": target_thread_id,
            "role": role,
            "purpose": contract["purpose"],
        }
        claim_matches = [
            item
            for item in claims
            if all(item.get(key) == value for key, value in exact_claim.items())
        ]
        mismatches: list[str] = []
        source_available = True
        if not isinstance(expected_target, str) or not expected_target:
            mismatches.append("role target unavailable")
            source_available = False
        if expected_rrule is None:
            mismatches.append("canonical schedule unavailable")
            source_available = False
        if expected_timezone == "unavailable":
            mismatches.append("canonical timezone unavailable")
            source_available = False
        elif actual_timezone is None:
            mismatches.append("automation owner timezone unavailable")
            source_available = False
        elif actual_timezone != expected_timezone:
            mismatches.append("automation owner timezone differs")
        if target_owners.get("status") != "available":
            mismatches.append("duplicate-role owner coverage unavailable")
            source_available = False
        elif target_owners.get("conflicting_owner_ids"):
            mismatches.append("different automation already active on role target")
        if not isinstance(actual, Mapping) or actual.get("status") != "available":
            mismatches.append("named automation unavailable")
            source_available = False
        else:
            comparisons = {
                "automation ID differs": actual.get("id") == automation_id,
                "enabled state differs": actual.get("owner_status") == "ACTIVE",
                "automation kind differs": actual.get("kind") == "heartbeat",
                "role target differs": actual.get("target_thread_id") == expected_target,
                "schedule differs": actual.get("rrule") == expected_rrule,
                "protected automation fields unavailable": isinstance(
                    actual.get("protected_sha256"), str
                )
                and SHA256.fullmatch(str(actual["protected_sha256"])) is not None,
            }
            mismatches.extend(label for label, matched in comparisons.items() if not matched)
        if len(claims) != 1 or len(claim_matches) != 1:
            mismatches.append("duplicate or conflicting canonical role claim")
        repairable_mismatches = {
            "enabled state differs",
            "role target differs",
            "schedule differs",
        }
        repairable = bool(mismatches) and source_available and set(mismatches).issubset(
            repairable_mismatches
        )
        current = {
            key: actual.get(key) if isinstance(actual, Mapping) else None
            for key in (
                "id",
                "status",
                "owner_status",
                "kind",
                "rrule",
                "target_thread_id",
                "manifest_sha256",
                "protected_sha256",
                "source_path",
            )
        }
        current["timezone"] = actual_timezone
        expected = {
            "id": automation_id,
            "owner_status": "ACTIVE",
            "kind": "heartbeat",
            "target_thread_id": expected_target,
            "rrule": expected_rrule,
            "timezone": expected_timezone,
        }
        material = {
            "target_thread_id": target_thread_id,
            "role": role,
            "purpose": contract["purpose"],
            "control_fingerprint": control.get("fingerprint"),
            "current": current,
            "expected": expected,
            "claims": claims,
            "active_target_owners": target_owners,
            "mismatches": mismatches,
            "repairable": repairable,
        }
        return {
            **material,
            "fingerprint": _digest(material),
            "label": contract["label"],
            "policy_version": control.get("policy_version"),
            "policy_sha256": control.get("policy_sha256"),
            "policy_history_head": control.get("policy_history_head"),
            "source_record": control.get("source_record"),
            "mission_binding": policy.get("mission_binding"),
            "lifecycle_status": control.get("lifecycle_status"),
            "control": control,
        }

    def binding_group_ids(self, target_thread_id: str) -> list[str]:
        """Return the one validated canonical group keyed by an exact target."""

        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        control = self.policy_control_snapshot(target_thread_id)
        if control.get("target_thread_id") != target_thread_id:
            raise OperationsProjectionError(
                "binding_group_check_unavailable",
                "The canonical supervision group does not claim the exact target.",
                status=422,
            )
        # The maintained owner keys a group by target ID. Reading the one exact
        # canonical directory proves the claim without scanning or reconciling
        # unrelated groups.
        return [target_thread_id]

    def project_binding_snapshot(
        self,
        projects: Sequence[ProjectRecord],
        target_thread_id: str,
    ) -> dict[str, Any]:
        """Project the canonical path claim for one exact supervision target."""

        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        unresolved = self.supervision_root / target_thread_id
        if unresolved.is_symlink():
            raise OperationsProjectionError(
                "supervision_target_symlink_rejected",
                "Supervision target must not be a symlink.",
                status=422,
            )
        try:
            directory = unresolved.resolve(strict=True)
        except OSError as error:
            raise OperationsProjectionError(
                "run_not_found",
                "Supervision target is not discoverable.",
                status=404,
            ) from error
        if directory.parent != self.supervision_root or not directory.is_dir():
            raise OperationsProjectionError(
                "supervision_target_invalid",
                "Supervision target escaped its canonical owner root.",
                status=422,
            )
        evidence, cache_status = self._load_target(directory)
        binding = self._project_binding(evidence, projects)
        material = {
            "target_thread_id": target_thread_id,
            "project_binding": binding,
        }
        return {
            **material,
            "fingerprint": _digest(material),
            "cache_status": cache_status,
        }

    def preview_mission_bind(
        self,
        target_thread_id: str,
        *,
        source_record: str,
        source_sha256: str,
    ) -> dict[str, Any]:
        """Exercise the maintained bind owner against an ephemeral exact policy copy."""

        if not SAFE_ID.fullmatch(target_thread_id):
            raise OperationsProjectionError("invalid_run_id", "Run target ID is invalid.")
        if not isinstance(source_record, str) or not SAFE_ID.fullmatch(source_record):
            raise OperationsProjectionError(
                "binding_source_invalid",
                "Mission source record identity is invalid.",
                status=422,
            )
        if not isinstance(source_sha256, str) or not SHA256.fullmatch(source_sha256):
            raise OperationsProjectionError(
                "binding_source_invalid",
                "Mission source content root is invalid.",
                status=422,
            )
        control = self.policy_control_snapshot(target_thread_id)
        policy = control.get("policy")
        history = control.get("policy_history_records")
        if not isinstance(policy, Mapping) or not isinstance(history, list):
            raise OperationsProjectionError(
                "binding_source_unavailable",
                "The current policy or policy history is unavailable.",
                status=422,
            )
        if policy.get("mission_binding") is not None:
            raise OperationsProjectionError(
                "binding_repair_not_missing",
                "The canonical policy already has a mission binding; bind cannot repair a differing mission.",
                status=409,
            )
        group_ids = self.binding_group_ids(target_thread_id)
        if group_ids != [target_thread_id]:
            raise OperationsProjectionError(
                "binding_group_ambiguous",
                "The exact target does not resolve to one canonical supervision group.",
                status=409,
            )
        owner = self._module("supervision")
        try:
            planned_binding = owner.derive_mission_binding(
                target_thread=target_thread_id,
                source_class="direct-user",
                source_record=source_record,
                source_sha256=source_sha256,
            )
        except Exception as error:
            raise OperationsProjectionError(
                "binding_source_invalid",
                "The maintained owner rejected the exact direct-user mission source.",
                status=422,
            ) from error

        with TemporaryDirectory(prefix="sf-dashboard-bind-preview-") as temporary:
            preview_root = Path(temporary).resolve() / "tracker-runs"
            preview_directory = preview_root / target_thread_id
            preview_directory.mkdir(parents=True)
            os.chmod(preview_directory, 0o700)
            owner.atomic_json(
                preview_directory / "policy.json",
                json.loads(json.dumps(policy)),
            )
            for record in history:
                if not isinstance(record, Mapping):
                    raise OperationsProjectionError(
                        "binding_source_unavailable",
                        "The canonical policy history contains a non-record value.",
                        status=422,
                    )
                material = {
                    key: json.loads(json.dumps(value))
                    for key, value in record.items()
                    if key not in {"previous_record_sha256", "record_sha256"}
                }
                owner.append_raw(preview_directory / "policy-history.jsonl", material)
            arguments = argparse.Namespace(
                root=str(preview_root),
                target_thread=target_thread_id,
                base_reviewer_thread=None,
                notice_reviewer_thread=None,
                fix_executor_thread=None,
                routine_automation=None,
                meta_automation=None,
                gmail_gate_thread=None,
                gmail_processor_thread=None,
                gmail_poll_automation=None,
                roundup_thread=None,
                roundup_automation=None,
                gmail_reply_message_id=None,
                gmail_project_key=None,
                gmail_subject=None,
                gmail_priority_reply_message_id=None,
                gmail_priority_project_key=None,
                gmail_priority_subject=None,
                gmail_priority_decision_context=False,
                gmail_roundup_reply_message_id=None,
                gmail_roundup_project_key=None,
                gmail_roundup_subject=None,
                mission_root=None,
                mission_source_record=source_record,
                mission_source_class="direct-user",
                mission_source_sha256=source_sha256,
            )
            output = StringIO()
            try:
                with redirect_stdout(output):
                    owner.cmd_bind(arguments)
                result = json.loads(output.getvalue())
                expected_policy = owner.read_json(preview_directory / "policy.json")
                expected_history = owner.events(
                    preview_directory / "policy-history.jsonl"
                )
            except Exception as error:
                raise OperationsProjectionError(
                    "binding_owner_preview_failed",
                    "The maintained bind owner rejected the exact ephemeral repair preview.",
                    status=422,
                ) from error
        if result.get("changed") is not True or not expected_history:
            raise OperationsProjectionError(
                "binding_owner_preview_failed",
                "The maintained bind owner did not produce one changed preview.",
                status=422,
            )
        expected_record = expected_history[-1]
        if (
            expected_policy.get("mission_binding") != planned_binding
            or expected_policy.get("policy_version") != int(policy.get("policy_version", 0)) + 1
            or expected_record.get("kind") != "policy-bind"
            or expected_record.get("reason") != "Bound live identifiers and current routing defaults."
            or expected_record.get("evidence") != []
            or expected_record.get("policy") != expected_policy
        ):
            raise OperationsProjectionError(
                "binding_owner_preview_failed",
                "The maintained bind owner returned an incompatible repair postcondition.",
                status=422,
            )

        def preserved_material(value: Mapping[str, Any]) -> dict[str, Any]:
            result = json.loads(json.dumps(value))
            for key in (
                "mission_binding",
                "policy_version",
                "policy_sha256",
                "updated_at",
            ):
                result.pop(key, None)
            return result

        if preserved_material(policy) != preserved_material(expected_policy):
            raise OperationsProjectionError(
                "binding_repair_owner_would_expand_scope",
                "The maintained bind owner would change fields beyond the missing mission binding.",
                status=409,
            )
        normalized = json.loads(json.dumps(expected_policy))
        normalized.pop("policy_sha256", None)
        normalized.pop("updated_at", None)
        return {
            "control": control,
            "owner_sha256": self.owner_revisions()["supervision"]["sha256"],
            "source_record": source_record,
            "source_sha256": source_sha256,
            "expected_mission_binding": json.loads(json.dumps(planned_binding)),
            "expected_policy_version": expected_policy["policy_version"],
            "expected_normalized_policy_sha256": _digest(normalized),
            "expected_history_kind": "policy-bind",
            "expected_history_reason": "Bound live identifiers and current routing defaults.",
            "expected_history_evidence": [],
            "group_ids": group_ids,
        }

    @staticmethod
    def _role_bind_arguments(
        target_thread_id: str,
        *,
        role: str,
        candidate_task_id: str,
        root: Path,
    ) -> argparse.Namespace:
        binding = ROLE_BIND_FIELDS.get(role)
        if binding is None:
            raise OperationsProjectionError(
                "role_binding_owner_unavailable",
                "The maintained bind owner cannot assign the selected role.",
                status=409,
            )
        values: dict[str, Any] = {
            "root": str(root),
            "target_thread": target_thread_id,
            "base_reviewer_thread": None,
            "notice_reviewer_thread": None,
            "fix_executor_thread": None,
            "routine_automation": None,
            "meta_automation": None,
            "gmail_gate_thread": None,
            "gmail_processor_thread": None,
            "gmail_poll_automation": None,
            "roundup_thread": None,
            "roundup_automation": None,
            "gmail_reply_message_id": None,
            "gmail_project_key": None,
            "gmail_subject": None,
            "gmail_priority_reply_message_id": None,
            "gmail_priority_project_key": None,
            "gmail_priority_subject": None,
            "gmail_priority_decision_context": False,
            "gmail_roundup_reply_message_id": None,
            "gmail_roundup_project_key": None,
            "gmail_roundup_subject": None,
            "mission_root": None,
            "mission_source_record": None,
            "mission_source_class": None,
            "mission_source_sha256": None,
        }
        values[binding[1]] = candidate_task_id
        return argparse.Namespace(**values)

    def preview_role_bind(
        self,
        target_thread_id: str,
        *,
        role: str,
    ) -> dict[str, Any]:
        """Derive one prior exact role task and exercise bind on an ephemeral copy."""

        binding = ROLE_BIND_FIELDS.get(role)
        if binding is None:
            raise OperationsProjectionError(
                "role_binding_owner_unavailable",
                "The maintained bind owner cannot assign the selected role.",
                status=409,
            )
        field, _ = binding
        control = self.policy_control_snapshot(target_thread_id)
        policy = control.get("policy")
        history = control.get("policy_history_records")
        runtime = policy.get("runtime") if isinstance(policy, Mapping) else None
        if (
            not isinstance(policy, Mapping)
            or not isinstance(history, list)
            or not isinstance(runtime, Mapping)
        ):
            raise OperationsProjectionError(
                "role_binding_source_unavailable",
                "The current policy or policy history is unavailable.",
                status=422,
            )
        if control.get("lifecycle_status") in {"completed", "stopped"}:
            raise OperationsProjectionError(
                "role_binding_target_terminal",
                "Role binding repair is unavailable for a terminal supervision group.",
                status=409,
            )
        if runtime.get(field) is not None:
            raise OperationsProjectionError(
                "role_binding_owner_cannot_replace",
                "The maintained bind owner only fills a missing role and cannot replace a differing binding.",
                status=409,
            )
        expected_model = ROLE_MODEL_CONTRACTS[role]
        models = policy.get("models")
        if not isinstance(models, Mapping) or models.get(role) != expected_model:
            raise OperationsProjectionError(
                "role_binding_model_contract_mismatch",
                "The selected role's governed model and reasoning contract is unavailable or differs.",
                status=409,
            )
        current_mission_binding = policy.get("mission_binding")
        if not isinstance(current_mission_binding, Mapping):
            raise OperationsProjectionError(
                "role_binding_source_unavailable",
                "The current mission binding is unavailable.",
                status=422,
            )

        prior_candidates: list[tuple[str, str]] = []
        candidate_other_roles: dict[str, set[str]] = {}
        for record in history[:-1]:
            snapshot = record.get("policy") if isinstance(record, Mapping) else None
            if not isinstance(snapshot, Mapping):
                raise OperationsProjectionError(
                    "role_binding_source_unavailable",
                    "Canonical policy history contains an incomplete policy snapshot.",
                    status=422,
                )
            if snapshot.get("mission_binding") != current_mission_binding:
                continue
            historical_runtime = (
                snapshot.get("runtime")
            )
            if not isinstance(historical_runtime, Mapping):
                raise OperationsProjectionError(
                    "role_binding_source_unavailable",
                    "Canonical policy history contains an incomplete runtime snapshot.",
                    status=422,
                )
            candidate = historical_runtime.get(field)
            record_id = record.get("record_id") if isinstance(record, Mapping) else None
            if isinstance(candidate, str) and candidate and isinstance(record_id, str):
                prior_candidates.append((candidate, record_id))
            for other_role, (other_field, _) in ROLE_BIND_FIELDS.items():
                other_value = historical_runtime.get(other_field)
                if isinstance(other_value, str) and other_value:
                    candidate_other_roles.setdefault(other_value, set()).add(other_role)
            for other_role, other_field in (
                ("watcher", "watcher_thread_id"),
                ("reviewer", "reviewer_thread_id"),
                ("gmail_gate", "gmail_gate_thread_id"),
            ):
                other_value = historical_runtime.get(other_field)
                if isinstance(other_value, str) and other_value:
                    candidate_other_roles.setdefault(other_value, set()).add(other_role)
        unique_candidates = sorted({item[0] for item in prior_candidates})
        if len(unique_candidates) != 1:
            raise OperationsProjectionError(
                "role_binding_candidate_ambiguous"
                if unique_candidates
                else "role_binding_task_authority_unavailable",
                (
                    "Canonical policy history names more than one prior task for the selected role."
                    if unique_candidates
                    else "No exact prior role task exists and generic task creation is not authorized."
                ),
                status=409,
            )
        candidate_task_id = unique_candidates[0]
        source_records = [
            record_id
            for candidate, record_id in prior_candidates
            if candidate == candidate_task_id
        ]
        current_role_ids = {
            str(value): role_name
            for role_name, role_field in (
                ("watcher", "watcher_thread_id"),
                ("base_reviewer", "base_reviewer_thread_id"),
                ("reviewer", "reviewer_thread_id"),
                ("notice_reviewer", "notice_reviewer_thread_id"),
                ("fix_executor", "fix_executor_thread_id"),
                ("gmail_gate", "gmail_gate_thread_id"),
                ("gmail_processor", "gmail_processor_thread_id"),
                ("roundup_writer", "roundup_thread_id"),
            )
            if isinstance((value := runtime.get(role_field)), str) and value
        }
        if candidate_task_id == target_thread_id or candidate_task_id in current_role_ids:
            raise OperationsProjectionError(
                "role_binding_candidate_conflict",
                "The prior task is already the target or a currently configured role.",
                status=409,
            )
        historical_roles = candidate_other_roles.get(candidate_task_id, set())
        if historical_roles - {role}:
            raise OperationsProjectionError(
                "role_binding_candidate_ambiguous",
                "The prior task has canonical history under another role.",
                status=409,
            )

        owner = self._module("supervision")
        with TemporaryDirectory(prefix="sf-dashboard-role-bind-preview-") as temporary:
            preview_root = Path(temporary).resolve() / "tracker-runs"
            preview_directory = preview_root / target_thread_id
            preview_directory.mkdir(parents=True)
            os.chmod(preview_directory, 0o700)
            owner.atomic_json(
                preview_directory / "policy.json",
                json.loads(json.dumps(policy)),
            )
            for record in history:
                if not isinstance(record, Mapping):
                    raise OperationsProjectionError(
                        "role_binding_source_unavailable",
                        "Canonical policy history contains a non-record value.",
                        status=422,
                    )
                material = {
                    key: json.loads(json.dumps(value))
                    for key, value in record.items()
                    if key not in {"previous_record_sha256", "record_sha256"}
                }
                owner.append_raw(preview_directory / "policy-history.jsonl", material)
            output = StringIO()
            try:
                arguments = self._role_bind_arguments(
                    target_thread_id,
                    role=role,
                    candidate_task_id=candidate_task_id,
                    root=preview_root,
                )
                with redirect_stdout(output):
                    owner.cmd_bind(arguments)
                result = json.loads(output.getvalue())
                expected_policy = owner.read_json(preview_directory / "policy.json")
                expected_history = owner.events(
                    preview_directory / "policy-history.jsonl"
                )
            except Exception as error:
                raise OperationsProjectionError(
                    "role_binding_owner_preview_failed",
                    "The maintained bind owner rejected the ephemeral role repair preview.",
                    status=422,
                ) from error
        expected_record = expected_history[-1] if expected_history else None
        if (
            result.get("changed") is not True
            or not isinstance(expected_record, Mapping)
            or expected_policy.get("runtime", {}).get(field) != candidate_task_id
            or expected_policy.get("policy_version")
            != int(policy.get("policy_version", 0)) + 1
            or expected_record.get("kind") != "policy-bind"
            or expected_record.get("reason")
            != "Bound live identifiers and current routing defaults."
            or expected_record.get("evidence") != []
            or expected_record.get("policy") != expected_policy
        ):
            raise OperationsProjectionError(
                "role_binding_owner_preview_failed",
                "The maintained bind owner returned an incompatible role repair postcondition.",
                status=422,
            )

        def preserved_material(value: Mapping[str, Any]) -> dict[str, Any]:
            material = json.loads(json.dumps(value))
            for key in ("policy_version", "policy_sha256", "updated_at"):
                material.pop(key, None)
            selected_runtime = material.get("runtime")
            if isinstance(selected_runtime, dict):
                selected_runtime.pop(field, None)
            return material

        if preserved_material(policy) != preserved_material(expected_policy):
            raise OperationsProjectionError(
                "role_binding_owner_would_expand_scope",
                "The maintained bind owner would change fields beyond the selected missing role.",
                status=409,
            )
        normalized = json.loads(json.dumps(expected_policy))
        normalized.pop("policy_sha256", None)
        normalized.pop("updated_at", None)
        return {
            "control": control,
            "owner_sha256": self.owner_revisions()["supervision"]["sha256"],
            "role": role,
            "runtime_field": field,
            "candidate_task_id": candidate_task_id,
            "candidate_source_records": source_records,
            "expected_model": dict(expected_model),
            "expected_policy_version": expected_policy["policy_version"],
            "expected_normalized_policy_sha256": _digest(normalized),
            "expected_history_kind": "policy-bind",
            "expected_history_reason": "Bound live identifiers and current routing defaults.",
            "expected_history_evidence": [],
            "preserved_runtime": {
                key: value for key, value in runtime.items() if key != field
            },
            "group_ids": self.binding_group_ids(target_thread_id),
        }

    def apply_role_bind(
        self,
        target_thread_id: str,
        *,
        role: str,
        candidate_task_id: str,
        prior_policy_sha256: str,
        prior_policy_version: int,
        prior_policy_history_head: str,
        prior_policy_history_count: int,
        expected_owner_sha256: str,
        expected_normalized_policy_sha256: str,
    ) -> dict[str, Any]:
        """Invoke one exact maintained bind assignment after revalidating its plan."""

        with self._lock:
            binding = ROLE_BIND_FIELDS.get(role)
            if binding is None:
                raise OperationsProjectionError(
                    "role_binding_owner_unavailable",
                    "The maintained bind owner cannot assign the selected role.",
                    status=409,
                )
            field, _ = binding
            control = self.policy_control_snapshot(target_thread_id)
            policy = control.get("policy")
            runtime = control.get("runtime")
            history = control.get("policy_history_records")
            models = policy.get("models") if isinstance(policy, Mapping) else None
            current_role_ids = {
                value
                for role_field in ROLE_THREAD_KEYS
                if isinstance(runtime, Mapping)
                and isinstance((value := runtime.get(role_field)), str)
                and value
            }
            if (
                not isinstance(policy, Mapping)
                or not isinstance(runtime, Mapping)
                or not isinstance(history, list)
                or control.get("policy_sha256") != prior_policy_sha256
                or control.get("policy_version") != prior_policy_version
                or control.get("policy_history_head") != prior_policy_history_head
                or len(history) != prior_policy_history_count
                or control.get("owner_sha256") != expected_owner_sha256
                or control.get("lifecycle_status") in {"completed", "stopped"}
                or runtime.get(field) is not None
                or candidate_task_id == target_thread_id
                or candidate_task_id in current_role_ids
                or not isinstance(models, Mapping)
                or models.get(role) != ROLE_MODEL_CONTRACTS[role]
            ):
                raise OperationsProjectionError(
                    "role_binding_source_stale",
                    "The role, candidate task, or policy head changed before assignment.",
                    status=409,
                    retryable=True,
                )
            owner = self._module("supervision")
            output = StringIO()
            try:
                arguments = self._role_bind_arguments(
                    target_thread_id,
                    role=role,
                    candidate_task_id=candidate_task_id,
                    root=self.supervision_root,
                )
                with redirect_stdout(output):
                    owner.cmd_bind(arguments)
                result = json.loads(output.getvalue())
            except Exception as error:
                raise OperationsProjectionError(
                    "role_binding_owner_failed",
                    "The maintained bind owner rejected the exact role assignment.",
                    status=409,
                ) from error
            current = self.policy_control_snapshot(target_thread_id)
            current_policy = current.get("policy")
            normalized = (
                json.loads(json.dumps(current_policy))
                if isinstance(current_policy, Mapping)
                else None
            )
            if isinstance(normalized, dict):
                normalized.pop("policy_sha256", None)
                normalized.pop("updated_at", None)
            if (
                result.get("changed") is not True
                or current.get("policy_version") != prior_policy_version + 1
                or not isinstance(normalized, dict)
                or _digest(normalized) != expected_normalized_policy_sha256
                or current.get("runtime", {}).get(field) != candidate_task_id
            ):
                raise OperationsProjectionError(
                    "role_binding_owner_postcondition_unverified",
                    "The maintained owner returned without the exact expected role assignment.",
                    status=409,
                )
            return {
                "owner_result": result,
                "control": current,
                "plan": {
                    "runtime_field": field,
                    "expected_policy_version": prior_policy_version + 1,
                },
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
        target_hint: str | None = None
        try:
            raw = _read_bounded(path, MAX_AUTOMATION_BYTES)
            text = raw.decode("utf-8")
            target_values = _automation_target_values(text)
            if len(target_values) == 1:
                target_hint = target_values[0]
            value = tomllib.loads(text)
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
                "protected_sha256": _digest(
                    {
                        key: value[key]
                        for key in (
                            "version",
                            "id",
                            "kind",
                            "name",
                            "prompt",
                            "created_at",
                        )
                    }
                ),
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
                "target_thread_id": target_hint,
                "created_at": None,
                "updated_at": None,
                "next_scheduled_at": None,
                "manifest_sha256": None,
                "protected_sha256": None,
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
        automation_timezone: str | None,
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
        gmail_cadence = self._gmail_cadence_snapshot(
            evidence.target_thread_id,
            evidence.policy,
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
            {
                "transition_id": transition_id,
                "open": item.get("phase") != "work-started",
                "head": _record_ref(item),
                "phase": _bounded(item.get("phase")),
                "tracker_sha256": _bounded(item.get("tracker_sha256"), 64),
                "tracker_source_record": _bounded(
                    item.get("tracker_source_record"), 160
                ),
                "requested_block_range": _bounded(
                    item.get("requested_block_range"), 80
                ),
                "first_eligible_block": _bounded(
                    item.get("first_eligible_block"), 40
                ),
                "source_mission_root": _bounded(
                    item.get("source_mission_root"), 64
                ),
                "governing_authority_source_class": _bounded(
                    item.get("governing_authority_source_class"), 40
                ),
                "governing_authority_source_record": _bounded(
                    item.get("governing_authority_source_record"), 160
                ),
                "successor_thread_id": _bounded(
                    item.get("successor_thread_id"), 128
                ),
                "successor_mission_root": _bounded(
                    item.get("successor_mission_root"), 64
                ),
                "successor_group_id": _bounded(
                    item.get("successor_group_id"), 128
                ),
                "handoff_record": _bounded(item.get("handoff_record"), 128),
                "acknowledgement_record": _bounded(
                    item.get("acknowledgement_record"), 128
                ),
                "started_block": _bounded(item.get("started_block"), 40),
                "state_fingerprint": _bounded(
                    item.get("state_fingerprint"), 128
                ),
            }
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
                "adjustable": policy_adjustable_values(evidence.policy),
                "adjustment_contract": {
                    key: value
                    for key, value in policy_adjustment_contract(
                        self._module("supervision")
                    ).items()
                    if key in {"fields", "skill_maintenance_modes"}
                },
                "automation_reconciliation": policy_automation_reconciliation(
                    evidence.policy,
                    roles,
                    gmail_cadence,
                    automations,
                    automation_timezone,
                    self._automation_target_query is not None,
                ),
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
        automation_timezone = self._automation_timezone()
        if not isinstance(automation_timezone, str) or not automation_timezone:
            automation_timezone = None
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
                    automation_timezone=automation_timezone,
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
