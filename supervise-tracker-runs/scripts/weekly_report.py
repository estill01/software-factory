#!/usr/bin/env python3
"""Derived weekly supervision metrics and PDF rendering.

This module is deliberately not a second supervision authority.  It computes a
bounded view over the existing hash-chained supervision records.  Public writes
are invoked only through ``supervision_log.py weekly-report``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo


SCHEMA_VERSION = 1
REPORT_KIND = "supervision-weekly-review"
DEFAULT_PRICING_PROFILE = (
    Path(__file__).resolve().parent.parent
    / "references"
    / "weekly-report-pricing-v1.json"
)
REVIEW_SECTIONS = (
    "caught_and_prevented",
    "fixes_and_effectiveness",
    "recurring_patterns",
    "blind_spots_and_misses",
    "development_pace",
    "monitoring_machinery_changes",
    "resource_efficiency",
    "recommended_bounded_improvements",
    "methodology_and_limits",
)
POSTURES = {
    "effective",
    "effective-with-findings",
    "mixed",
    "needs-attention",
    "insufficient-evidence",
}
TERMINAL_INCIDENT_STATUSES = {
    "corrected",
    "false-positive",
    "accepted-risk",
    "superseded",
    "closed",
    "resolved",
}
LOCAL_PATH = re.compile(r"(?:/Users/|file://|\\\\Users\\\\)")


class WeeklyReportError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_time(value: str) -> dt.datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        result = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WeeklyReportError("Weekly report time must be ISO-8601") from exc
    if result.tzinfo is None:
        raise WeeklyReportError("Weekly report time must include a timezone")
    return result.astimezone(dt.timezone.utc).replace(microsecond=0)


def iso_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_text(value: Any, *, label: str, maximum: int = 2400) -> str:
    if not isinstance(value, str):
        raise WeeklyReportError(f"{label} must be text")
    text = value.strip()
    if not text:
        raise WeeklyReportError(f"{label} must not be empty")
    if len(text) > maximum:
        raise WeeklyReportError(f"{label} exceeds {maximum} characters")
    if LOCAL_PATH.search(text):
        raise WeeklyReportError(f"{label} must not contain a local path")
    return text


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n",
    )


def record_time(record: Mapping[str, Any]) -> dt.datetime:
    value = record.get("timestamp")
    if not isinstance(value, str):
        raise WeeklyReportError("Supervision record lacks a timestamp")
    return parse_time(value)


def in_window(
    record: Mapping[str, Any], start: dt.datetime, end: dt.datetime
) -> bool:
    stamp = record_time(record)
    return start <= stamp <= end


def is_substantive_incident_record(record: Mapping[str, Any]) -> bool:
    if not record.get("incident_id"):
        return False
    if record.get("kind") in {"notification", "escalation"}:
        return False
    return True


def is_terminal_incident_record(record: Mapping[str, Any]) -> bool:
    return str(record.get("status", "")) in TERMINAL_INCIDENT_STATUSES


def percentile(values: Sequence[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentage
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def rounded(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def day_key(stamp: dt.datetime, timezone: ZoneInfo) -> str:
    return stamp.astimezone(timezone).date().isoformat()


def day_range(start: dt.datetime, end: dt.datetime, timezone: ZoneInfo) -> list[str]:
    current = start.astimezone(timezone).date()
    final = end.astimezone(timezone).date()
    result: list[str] = []
    while current <= final:
        result.append(current.isoformat())
        current += dt.timedelta(days=1)
    return result


def activity_class(record: Mapping[str, Any]) -> str:
    kind = str(record.get("kind", ""))
    if kind == "escalation":
        return "routing"
    if kind in {"incident", "steer", "resolution"}:
        return "intervention"
    if kind in {"notification", "roundup", "inbound-message", "lifecycle"}:
        return "communication"
    if kind in {"checkpoint-review", "meta-review", "decision"}:
        return "review"
    if kind == "check":
        return "review" if record.get("model") == "gpt-5.6-sol" else "mechanical"
    if kind == "policy-change":
        return "maintenance"
    return "other"


def task_activity(window_events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    definitions = (
        (
            "Watcher checks",
            lambda item: item.get("kind") == "check"
            and item.get("model") == "gpt-5.6-terra",
            "Every 20 minutes while active; unchanged no-op wakes may not be logged.",
        ),
        (
            "Changed-state routes",
            lambda item: item.get("category") == "changed-state-review",
            "One route for each distinct changed target state.",
        ),
        (
            "XHigh semantic reviews",
            lambda item: item.get("kind") == "check"
            and item.get("reasoning") == "xhigh",
            "Every changed state routed for substantive classification.",
        ),
        (
            "Max sampled reviews",
            lambda item: item.get("kind") == "check"
            and item.get("category") == "max-sample",
            "Deterministic one-in-six changed-state sample.",
        ),
        (
            "Max effectiveness reviews",
            lambda item: item.get("kind") == "meta-review",
            "Every four hours when review evidence changed.",
        ),
        (
            "Incident review actions",
            lambda item: "incident-review" in str(item.get("category", ""))
            or item.get("category") in {"notice-review", "notice-outcome-review"},
            "Event-driven for material incident evidence.",
        ),
        (
            "Fix-executor actions",
            lambda item: item.get("category") == "fix-execution",
            "Event-driven for an independently approved bounded fix.",
        ),
        (
            "Roundups",
            lambda item: item.get("kind") == "roundup",
            "Four Pacific-time change logs per day while enabled.",
        ),
        (
            "Email delivery receipts",
            lambda item: item.get("kind") == "notification",
            "Event-driven for approved notices and scheduled roundups.",
        ),
    )
    return [
        {"task": name, "recorded_count": sum(1 for item in window_events if test(item)), "cadence": cadence}
        for name, test, cadence in definitions
    ]


def load_pricing_profile(path: Path = DEFAULT_PRICING_PROFILE) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WeeklyReportError("Weekly report pricing profile cannot be read") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "profile_id",
        "currency",
        "estimation",
        "models",
        "disclaimer",
    }:
        raise WeeklyReportError("Weekly report pricing profile shape differs")
    if value.get("schema_version") != 1 or value.get("currency") != "USD":
        raise WeeklyReportError("Weekly report pricing profile version differs")
    estimation = value.get("estimation")
    models = value.get("models")
    if not isinstance(estimation, dict) or not isinstance(models, dict) or not models:
        raise WeeklyReportError("Weekly report pricing assumptions are incomplete")
    if set(estimation) != {
        "characters_per_token",
        "low_multiplier",
        "high_multiplier",
        "reasoning_output_multipliers",
    }:
        raise WeeklyReportError("Weekly report token-estimation shape differs")
    characters_per_token = estimation.get("characters_per_token")
    low = estimation.get("low_multiplier")
    high = estimation.get("high_multiplier")
    reasoning = estimation.get("reasoning_output_multipliers")
    if (
        not isinstance(characters_per_token, int)
        or characters_per_token < 1
        or not isinstance(low, (int, float))
        or not isinstance(high, (int, float))
        or not 0 < float(low) <= 1 <= float(high)
        or not isinstance(reasoning, dict)
        or "unspecified" not in reasoning
    ):
        raise WeeklyReportError("Weekly report token-estimation values are invalid")
    required_model_fields = {
        "api_price_assumption",
        "input_usd_per_million_tokens",
        "output_usd_per_million_tokens",
        "per_record_input_overhead_tokens",
        "per_record_output_floor_tokens",
        "source_url",
    }
    for model, assumption in models.items():
        if not isinstance(model, str) or not isinstance(assumption, dict):
            raise WeeklyReportError("Weekly report model assumption is invalid")
        if set(assumption) != required_model_fields:
            raise WeeklyReportError(
                f"Weekly report pricing assumption differs for {model}"
            )
        numeric = (
            assumption["input_usd_per_million_tokens"],
            assumption["output_usd_per_million_tokens"],
            assumption["per_record_input_overhead_tokens"],
            assumption["per_record_output_floor_tokens"],
        )
        if any(not isinstance(item, (int, float)) or item < 0 for item in numeric):
            raise WeeklyReportError(
                f"Weekly report pricing assumption is invalid for {model}"
            )
    value["profile_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def estimated_visible_tokens(value: Any, characters_per_token: int) -> int:
    return math.ceil(len(canonical(value).decode("utf-8")) / characters_per_token)


def resource_estimate(
    window_events: Sequence[Mapping[str, Any]],
    timezone: ZoneInfo,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Project token and API-equivalent cost from model-attributed log records."""

    estimation = profile["estimation"]
    characters_per_token = int(estimation["characters_per_token"])
    low_multiplier = float(estimation["low_multiplier"])
    high_multiplier = float(estimation["high_multiplier"])
    reasoning_multipliers = estimation["reasoning_output_multipliers"]
    models = profile["models"]
    rows: dict[str, dict[str, Any]] = {}
    daily: dict[str, dict[str, float | int | str]] = {}
    excluded_records = 0
    for item in window_events:
        model = item.get("model")
        if not isinstance(model, str) or model not in models:
            excluded_records += 1
            continue
        assumption = models[model]
        reasoning = str(item.get("reasoning") or "unspecified")
        reasoning_multiplier = float(
            reasoning_multipliers.get(reasoning, reasoning_multipliers["unspecified"])
        )
        observed_input = estimated_visible_tokens(item, characters_per_token)
        output_material = {
            key: item.get(key)
            for key in ("summary", "action", "resolution", "evidence")
            if item.get(key)
        }
        observed_output = estimated_visible_tokens(
            output_material or {"record_id": item.get("record_id")},
            characters_per_token,
        )
        input_tokens = int(assumption["per_record_input_overhead_tokens"]) + observed_input
        output_tokens = math.ceil(
            max(int(assumption["per_record_output_floor_tokens"]), observed_output)
            * reasoning_multiplier
        )
        input_cost = (
            input_tokens * float(assumption["input_usd_per_million_tokens"]) / 1_000_000
        )
        output_cost = (
            output_tokens * float(assumption["output_usd_per_million_tokens"]) / 1_000_000
        )
        row = rows.setdefault(
            model,
            {
                "model": model,
                "recorded_model_attributed_events": 0,
                "reasoning_event_counts": Counter(),
                "estimated_input_tokens_base": 0,
                "estimated_output_tokens_base": 0,
                "projected_cost_usd_base": 0.0,
                "api_price_assumption": assumption["api_price_assumption"],
                "input_usd_per_million_tokens": assumption[
                    "input_usd_per_million_tokens"
                ],
                "output_usd_per_million_tokens": assumption[
                    "output_usd_per_million_tokens"
                ],
                "source_url": assumption["source_url"],
            },
        )
        row["recorded_model_attributed_events"] += 1
        row["reasoning_event_counts"][reasoning] += 1
        row["estimated_input_tokens_base"] += input_tokens
        row["estimated_output_tokens_base"] += output_tokens
        row["projected_cost_usd_base"] += input_cost + output_cost
        day = day_key(record_time(item), timezone)
        day_row = daily.setdefault(
            day,
            {"date": day, "estimated_tokens_base": 0, "projected_cost_usd_base": 0.0},
        )
        day_row["estimated_tokens_base"] += input_tokens + output_tokens
        day_row["projected_cost_usd_base"] += input_cost + output_cost

    total_input = 0
    total_output = 0
    total_cost = 0.0
    model_rows: list[dict[str, Any]] = []
    for model in sorted(rows):
        row = rows[model]
        row["reasoning_event_counts"] = dict(row["reasoning_event_counts"].most_common())
        input_tokens = int(row["estimated_input_tokens_base"])
        output_tokens = int(row["estimated_output_tokens_base"])
        cost = float(row["projected_cost_usd_base"])
        row["estimated_tokens_base"] = input_tokens + output_tokens
        row["estimated_tokens_low"] = round((input_tokens + output_tokens) * low_multiplier)
        row["estimated_tokens_high"] = round((input_tokens + output_tokens) * high_multiplier)
        row["projected_cost_usd_low"] = round(cost * low_multiplier, 2)
        row["projected_cost_usd_base"] = round(cost, 2)
        row["projected_cost_usd_high"] = round(cost * high_multiplier, 2)
        total_input += input_tokens
        total_output += output_tokens
        total_cost += cost
        model_rows.append(row)
    daily_rows = []
    for day in sorted(daily):
        row = daily[day]
        row["projected_cost_usd_base"] = round(
            float(row["projected_cost_usd_base"]), 2
        )
        daily_rows.append(row)
    return {
        "measurement_posture": "estimated-from-content-minimized-records",
        "actual_provider_tokens_available": False,
        "actual_provider_cost_available": False,
        "pricing_profile_id": profile["profile_id"],
        "pricing_profile_sha256": profile["profile_sha256"],
        "currency": profile["currency"],
        "method": "For each model-attributed supervision record: canonical visible record characters divided by the configured character-per-token ratio, plus a model-specific input-context allowance; visible output fields or a model-specific output floor, multiplied by the recorded reasoning-effort factor. Low/high bounds multiply the base estimate. Costs apply the stated public API-equivalent price assumptions.",
        "models": model_rows,
        "totals": {
            "recorded_model_attributed_events": sum(
                int(row["recorded_model_attributed_events"]) for row in model_rows
            ),
            "excluded_unpriced_or_unattributed_records": excluded_records,
            "estimated_input_tokens_base": total_input,
            "estimated_output_tokens_base": total_output,
            "estimated_tokens_base": total_input + total_output,
            "estimated_tokens_low": round((total_input + total_output) * low_multiplier),
            "estimated_tokens_high": round((total_input + total_output) * high_multiplier),
            "projected_cost_usd_low": round(total_cost * low_multiplier, 2),
            "projected_cost_usd_base": round(total_cost, 2),
            "projected_cost_usd_high": round(total_cost * high_multiplier, 2),
        },
        "daily": daily_rows,
        "assumptions": {
            "characters_per_token": characters_per_token,
            "low_multiplier": low_multiplier,
            "high_multiplier": high_multiplier,
            "reasoning_output_multipliers": reasoning_multipliers,
            "models": models,
        },
        "disclaimer": profile["disclaimer"],
    }


def availability_metrics(
    window_events: Sequence[Mapping[str, Any]],
    start: dt.datetime,
    end: dt.datetime,
) -> dict[str, Any]:
    """Compute explicit schedule posture without inferring silence as downtime."""

    active = True
    cursor = start
    active_seconds = 0.0
    paused_seconds = 0.0
    intervals: list[dict[str, Any]] = []
    pause_start: dt.datetime | None = None
    pause_record: str | None = None
    for item in sorted(window_events, key=record_time):
        stamp = record_time(item)
        is_pause = (
            item.get("kind") == "policy-change"
            and item.get("category") == "stop-condition-pause"
            and item.get("status") == "paused"
        )
        is_resume = (
            item.get("kind") == "policy-change"
            and item.get("category") == "supervision-resume"
            and item.get("status") == "resumed"
        )
        if is_pause and active:
            active_seconds += max(0.0, (stamp - cursor).total_seconds())
            active = False
            cursor = stamp
            pause_start = stamp
            pause_record = str(item.get("record_id"))
        elif is_resume and not active:
            paused_seconds += max(0.0, (stamp - cursor).total_seconds())
            intervals.append(
                {
                    "start": iso_time(pause_start or cursor),
                    "end": iso_time(stamp),
                    "hours": round((stamp - (pause_start or cursor)).total_seconds() / 3600, 2),
                    "pause_record_id": pause_record,
                    "resume_record_id": item.get("record_id"),
                }
            )
            active = True
            cursor = stamp
            pause_start = None
            pause_record = None
    if active:
        active_seconds += max(0.0, (end - cursor).total_seconds())
    else:
        paused_seconds += max(0.0, (end - cursor).total_seconds())
        intervals.append(
            {
                "start": iso_time(pause_start or cursor),
                "end": iso_time(end),
                "hours": round((end - (pause_start or cursor)).total_seconds() / 3600, 2),
                "pause_record_id": pause_record,
                "resume_record_id": None,
            }
        )

    total_seconds = max(0.0, (end - start).total_seconds())
    successful_reads = sum(
        1 for item in window_events if item.get("category") == "changed-state-review"
    )
    failed_reads = sum(
        1
        for item in window_events
        if item.get("kind") == "check"
        and item.get("category")
        in {"watcher-failure", "watcher-unavailable", "target-read-deferred"}
        and item.get("status") in {"deferred", "blocked", "unavailable"}
    )
    read_total = successful_reads + failed_reads
    first_event = record_time(window_events[0])
    last_event = record_time(window_events[-1])
    return {
        "report_period_hours": round(total_seconds / 3600, 2),
        "observed_event_span_hours": round((last_event - first_event).total_seconds() / 3600, 2),
        "core_heartbeats_scheduled_active_hours": round(active_seconds / 3600, 2),
        "core_heartbeats_explicitly_paused_hours": round(paused_seconds / 3600, 2),
        "core_heartbeats_scheduled_active_percent": rounded(
            100.0 * active_seconds / total_seconds if total_seconds else None
        ),
        "explicit_pause_intervals": intervals,
        "recorded_target_read_successes": successful_reads,
        "recorded_target_read_failures": failed_reads,
        "recorded_target_read_availability_percent": rounded(
            100.0 * successful_reads / read_total if read_total else None
        ),
        "continuous_process_uptime_measured": False,
        "interpretation": "Scheduled-active time is derived only from explicit pause/resume policy records. Target-read availability uses recorded material read outcomes. Quiet gaps are not downtime because unchanged wakes may emit no event.",
    }


def build_metrics(
    *,
    target_label: str,
    target_thread_id: str,
    start: dt.datetime,
    end: dt.datetime,
    timezone_name: str,
    all_events: Sequence[Mapping[str, Any]],
    policy_history: Sequence[Mapping[str, Any]],
    current_policy: Mapping[str, Any],
    projection_inventory: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if end <= start:
        raise WeeklyReportError("Weekly report end must be after start")
    timezone = ZoneInfo(timezone_name)
    pricing_profile = load_pricing_profile()
    bounded_events = [item for item in all_events if record_time(item) <= end]
    window_events = [item for item in bounded_events if in_window(item, start, end)]
    bounded_policy = [item for item in policy_history if record_time(item) <= end]
    window_policy = [item for item in bounded_policy if in_window(item, start, end)]
    if not window_events:
        raise WeeklyReportError("Weekly report window contains no supervision events")

    source_material = {
        "schema_version": SCHEMA_VERSION,
        "target_thread_id": target_thread_id,
        "coverage_start": iso_time(start),
        "coverage_end": iso_time(end),
        "event_records": window_events,
        "policy_records": window_policy,
        "projection_inventory": projection_inventory,
        "pricing_profile_id": pricing_profile["profile_id"],
        "pricing_profile_sha256": pricing_profile["profile_sha256"],
    }
    source_root = digest(source_material)
    report_id = (
        "weekly-"
        + start.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + end.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + source_root[:12]
    )

    days = day_range(start, end, timezone)
    daily: dict[str, Counter[str]] = {day: Counter() for day in days}
    for item in window_events:
        daily[day_key(record_time(item), timezone)][activity_class(item)] += 1

    incident_openings = [item for item in window_events if item.get("kind") == "incident"]
    incident_heads: dict[str, Mapping[str, Any]] = {}
    incident_first: dict[str, Mapping[str, Any]] = {}
    incident_first_terminal: dict[str, Mapping[str, Any]] = {}
    for item in bounded_events:
        incident = item.get("incident_id")
        if not isinstance(incident, str) or not is_substantive_incident_record(item):
            continue
        incident_first.setdefault(incident, item)
        incident_heads[incident] = item
        if is_terminal_incident_record(item):
            incident_first_terminal.setdefault(incident, item)
    opened_ids = [str(item["incident_id"]) for item in incident_openings]
    terminal_in_window = [
        item
        for incident, item in incident_first_terminal.items()
        if incident in incident_first and in_window(item, start, end)
    ]
    open_at_end = [
        incident
        for incident, head in incident_heads.items()
        if not is_terminal_incident_record(head)
    ]
    durations_hours: list[float] = []
    for incident, terminal in incident_first_terminal.items():
        opening = incident_first.get(incident)
        if opening is None:
            continue
        if incident not in opened_ids and not in_window(terminal, start, end):
            continue
        duration = (record_time(terminal) - record_time(opening)).total_seconds() / 3600
        if duration >= 0:
            durations_hours.append(duration)

    daily_incidents: dict[str, dict[str, int]] = {
        day: {"opened": 0, "terminal": 0} for day in days
    }
    for item in incident_openings:
        daily_incidents[day_key(record_time(item), timezone)]["opened"] += 1
    for item in terminal_in_window:
        daily_incidents[day_key(record_time(item), timezone)]["terminal"] += 1

    changed_state_routes = sum(
        1 for item in window_events if item.get("category") == "changed-state-review"
    )
    incident_rate = (
        100.0 * len(incident_openings) / changed_state_routes
        if changed_state_routes
        else None
    )
    effectiveness_records = [
        item
        for item in window_events
        if "effectiveness" in str(item.get("category", ""))
        or (
            item.get("kind") in {"check", "resolution"}
            and item.get("status") in {"effective", "ineffective", "partial-effectiveness"}
        )
    ]
    effectiveness_counts = Counter(str(item.get("status", "")) for item in effectiveness_records)

    blocks: dict[str, dict[str, Any]] = {}
    for item in window_events:
        block = str(item.get("active_block", ""))
        if not block.isdigit():
            continue
        current = blocks.setdefault(
            block,
            {
                "block": int(block),
                "first_seen": item["timestamp"],
                "last_seen": item["timestamp"],
                "event_count": 0,
                "checkpoint_count": 0,
            },
        )
        current["last_seen"] = item["timestamp"]
        current["event_count"] += 1
        if item.get("kind") == "checkpoint-review" or "checkpoint" in str(item.get("status", "")):
            current["checkpoint_count"] += 1
    block_rows = sorted(blocks.values(), key=lambda row: row["first_seen"])

    tooling_events = [
        item
        for item in window_events
        if item.get("kind") == "policy-change"
        or "skill-maintenance" in str(item.get("category", ""))
        or "policy" in str(item.get("category", ""))
    ]
    line_items = [
        {
            "record_id": item.get("record_id"),
            "timestamp": item.get("timestamp"),
            "kind": item.get("kind"),
            "status": item.get("status"),
            "severity": item.get("severity"),
            "category": item.get("category"),
            "active_block": item.get("active_block"),
            "summary": item.get("summary"),
        }
        for item in window_events
        if item.get("kind") in {"incident", "steer", "policy-change", "lifecycle"}
        or (
            item.get("kind") == "resolution"
            and str(item.get("status", "")) in TERMINAL_INCIDENT_STATUSES
        )
        or item.get("category") == "block-transition"
    ]

    metrics: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "report_id": report_id,
        "target_label": target_label,
        "coverage": {
            "start": iso_time(start),
            "end": iso_time(end),
            "timezone": timezone_name,
            "calendar_days": days,
            "elapsed_hours": round((end - start).total_seconds() / 3600, 2),
            "partial_week": (end - start) < dt.timedelta(days=6, hours=23),
        },
        "source": {
            "source_root": source_root,
            "event_count": len(window_events),
            "first_record_id": window_events[0].get("record_id"),
            "last_record_id": window_events[-1].get("record_id"),
            "policy_record_count": len(window_policy),
            "policy_sha256_at_generation": current_policy.get("policy_sha256"),
            "projection_inventory": projection_inventory,
        },
        "headline": {
            "recorded_events": len(window_events),
            "changed_state_routes": changed_state_routes,
            "incidents_opened": len(incident_openings),
            "incidents_terminal": len(terminal_in_window),
            "incidents_open_at_end": len(open_at_end),
            "corrections_issued": sum(
                1
                for item in window_events
                if item.get("notice_disposition") == "correction-issued"
                and item.get("kind") == "steer"
            ),
            "max_samples": sum(
                1
                for item in window_events
                if item.get("kind") == "check" and item.get("category") == "max-sample"
            ),
            "roundups": sum(1 for item in window_events if item.get("kind") == "roundup"),
            "blocks_observed": len(block_rows),
            "tooling_change_records": len(tooling_events),
        },
        "rates": {
            "incidents_per_100_changed_state_routes": rounded(incident_rate),
            "terminal_share_of_opened_percent": rounded(
                100.0 * len(terminal_in_window) / len(incident_openings)
                if incident_openings
                else None
            ),
            "incident_detection_to_terminal_median_hours": rounded(
                median(durations_hours) if durations_hours else None
            ),
            "incident_detection_to_terminal_p90_hours": rounded(
                percentile(durations_hours, 0.9)
            ),
            "denominator_note": "Incident rate uses incident openings divided by exact changed-state routing records. It measures supervision yield, not implementation quality.",
        },
        "availability": availability_metrics(window_events, start, end),
        "resource_estimate": resource_estimate(
            window_events, timezone, pricing_profile
        ),
        "counts": {
            "by_kind": dict(Counter(str(item.get("kind", "")) for item in window_events).most_common()),
            "by_status": dict(Counter(str(item.get("status", "")) for item in window_events).most_common()),
            "by_severity": dict(Counter(str(item.get("severity", "")) for item in window_events).most_common()),
            "by_category": dict(Counter(str(item.get("category", "")) for item in window_events).most_common()),
            "by_model_reasoning": dict(
                Counter(
                    f"{item.get('model') or 'unspecified'} / {item.get('reasoning') or 'unspecified'}"
                    for item in window_events
                ).most_common()
            ),
        },
        "daily_activity": [
            {"date": day, **{name: daily[day].get(name, 0) for name in ("mechanical", "review", "routing", "intervention", "communication", "maintenance", "other")}}
            for day in days
        ],
        "daily_incidents": [
            {"date": day, **daily_incidents[day]} for day in days
        ],
        "task_activity": task_activity(window_events),
        "incidents": {
            "opened_ids": opened_ids,
            "terminal_ids": sorted(
                str(item.get("incident_id")) for item in terminal_in_window
            ),
            "open_at_end_ids": sorted(open_at_end),
            "terminal_statuses": dict(
                Counter(str(item.get("status", "")) for item in terminal_in_window)
            ),
            "effectiveness_statuses": dict(effectiveness_counts),
            "false_positive_terminal_count": sum(
                1 for item in terminal_in_window if item.get("status") == "false-positive"
            ),
            "sampled_false_negative_mentions": sum(
                1
                for item in window_events
                if item.get("kind") == "meta-review"
                and "false negative" in str(item.get("summary", "")).lower()
            ),
        },
        "blocks": block_rows,
        "tooling_changes": [
            {
                "record_id": item.get("record_id"),
                "timestamp": item.get("timestamp"),
                "status": item.get("status"),
                "category": item.get("category"),
                "summary": item.get("summary"),
            }
            for item in tooling_events
        ],
        "line_items": line_items,
        "limitations": [
            "Recorded task activity is a lower bound when scheduled no-op wakes intentionally emit no event.",
            "Counts and hashes establish operational completeness, not patent quality or legal sufficiency.",
            "A higher incident rate may reflect better detection or a riskier implementation phase; cognitive review is required before interpretation.",
            "The first report may cover less than seven days when supervision history is newer than one week.",
            "Token counts and costs are projection ranges from a versioned estimation profile, not provider telemetry, actual usage, billed cost, or the prices of internal model aliases.",
            "Continuous process uptime is not available from the content-minimized event ledger; only explicit scheduled-active/paused intervals and recorded target-read outcomes are reported.",
        ],
    }
    packet = {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-cognitive-review-packet",
        "report_id": report_id,
        "source_root": source_root,
        "coverage": metrics["coverage"],
        "review_contract": {
            "method": "Read every bounded record in this packet, reconcile the deterministic metrics, and explain patterns, effectiveness, misses, pace, and limitations. Do not merely restate counts.",
            "required_sections": list(REVIEW_SECTIONS),
            "content_boundary": "Use only content-minimized supervision records. Do not introduce patent content, raw tool output, prompts, local paths, credentials, or personal names.",
            "causality_boundary": "Distinguish observed association from causation and do not treat process activity as patent quality.",
        },
        "metrics": metrics,
        "event_records": window_events,
        "policy_records": window_policy,
    }
    return metrics, packet


def validate_review(
    review: Mapping[str, Any], *, report_id: str, source_root: str, record_ids: set[str]
) -> dict[str, Any]:
    expected = {
        "schema_version",
        "kind",
        "report_id",
        "source_root",
        "reviewer_method",
        "overall_posture",
        "headline",
        "executive_assessment",
        "sections",
    }
    if set(review) != expected:
        raise WeeklyReportError("Cognitive review shape differs")
    if review.get("schema_version") != SCHEMA_VERSION or review.get("kind") != f"{REPORT_KIND}-cognitive-review":
        raise WeeklyReportError("Unsupported cognitive review contract")
    if review.get("report_id") != report_id or review.get("source_root") != source_root:
        raise WeeklyReportError("Cognitive review is bound to different source evidence")
    if review.get("reviewer_method") != "bounded-full-window-cognitive-review":
        raise WeeklyReportError("Cognitive review method is not declared")
    posture = review.get("overall_posture")
    if posture not in POSTURES:
        raise WeeklyReportError("Unsupported weekly review posture")
    result = dict(review)
    result["headline"] = safe_text(review.get("headline"), label="review headline", maximum=180)
    result["executive_assessment"] = safe_text(
        review.get("executive_assessment"), label="executive assessment", maximum=3600
    )
    sections = review.get("sections")
    if not isinstance(sections, dict) or set(sections) != set(REVIEW_SECTIONS):
        raise WeeklyReportError("Cognitive review sections differ")
    clean_sections: dict[str, list[dict[str, Any]]] = {}
    for section in REVIEW_SECTIONS:
        entries = sections.get(section)
        if not isinstance(entries, list) or not entries or len(entries) > 12:
            raise WeeklyReportError(f"Review section {section} requires 1-12 entries")
        clean_entries: list[dict[str, Any]] = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or set(entry) != {"title", "assessment", "evidence"}:
                raise WeeklyReportError(f"Review section {section} entry {index} differs")
            evidence = entry.get("evidence")
            if not isinstance(evidence, list) or not evidence or len(evidence) > 20:
                raise WeeklyReportError(f"Review section {section} entry {index} lacks bounded evidence")
            unknown = [item for item in evidence if item not in record_ids]
            if unknown:
                raise WeeklyReportError(
                    f"Review section {section} cites unknown records: {', '.join(unknown)}"
                )
            clean_entries.append(
                {
                    "title": safe_text(entry.get("title"), label=f"{section} title", maximum=160),
                    "assessment": safe_text(entry.get("assessment"), label=f"{section} assessment", maximum=2400),
                    "evidence": evidence,
                }
            )
        clean_sections[section] = clean_entries
    result["sections"] = clean_sections
    return result


def machine_report(
    metrics: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-record",
        "report_id": metrics["report_id"],
        "source_root": metrics["source"]["source_root"],
        "coverage": metrics["coverage"],
        "metrics": metrics,
        "cognitive_review": review,
    }


def markdown_report(metrics: Mapping[str, Any], review: Mapping[str, Any]) -> str:
    headline = metrics["headline"]
    coverage = metrics["coverage"]
    availability = metrics["availability"]
    resources = metrics["resource_estimate"]
    resource_totals = resources["totals"]
    rows = [
        f"# Supervision weekly review - {metrics['target_label']}\n",
        f"**Coverage:** {coverage['start']} through {coverage['end']} ({coverage['timezone']})  \n",
        f"**Posture:** {review['overall_posture']}  \n",
        f"**Evidence root:** `{metrics['source']['source_root']}`\n\n",
        f"## {review['headline']}\n\n",
        review["executive_assessment"] + "\n\n",
        "## Headline metrics\n\n",
        f"- Recorded events: {headline['recorded_events']}\n",
        f"- Changed-state routes: {headline['changed_state_routes']}\n",
        f"- Incidents opened / terminal / open: {headline['incidents_opened']} / {headline['incidents_terminal']} / {headline['incidents_open_at_end']}\n",
        f"- Corrections issued: {headline['corrections_issued']}\n",
        f"- Max samples: {headline['max_samples']}\n",
        f"- Blocks observed: {headline['blocks_observed']}\n",
        f"- Tooling change records: {headline['tooling_change_records']}\n\n",
        "## Availability and runtime\n\n",
        f"- Total report period: {availability['report_period_hours']} hours\n",
        f"- Core heartbeat scheduled-active time: {availability['core_heartbeats_scheduled_active_hours']} hours ({availability['core_heartbeats_scheduled_active_percent']}%)\n",
        f"- Core heartbeat explicitly paused time: {availability['core_heartbeats_explicitly_paused_hours']} hours\n",
        f"- Recorded target-read availability: {availability['recorded_target_read_availability_percent']}% ({availability['recorded_target_read_successes']} successful / {availability['recorded_target_read_failures']} failed)\n",
        f"- Continuous process uptime directly measured: {availability['continuous_process_uptime_measured']}\n\n",
        availability["interpretation"] + "\n\n",
        "## Estimated model tokens and API-equivalent cost\n\n",
        f"- Estimated tokens: {resource_totals['estimated_tokens_base']:,} base ({resource_totals['estimated_tokens_low']:,}-{resource_totals['estimated_tokens_high']:,})\n",
        f"- Projected API-equivalent cost: ${resource_totals['projected_cost_usd_base']:.2f} base (${resource_totals['projected_cost_usd_low']:.2f}-${resource_totals['projected_cost_usd_high']:.2f})\n",
        f"- Pricing profile: `{resources['pricing_profile_id']}` / `{resources['pricing_profile_sha256']}`\n\n",
    ]
    for item in resources["models"]:
        rows.append(
            f"- **{item['model']}**: {item['recorded_model_attributed_events']} attributed records; "
            f"{item['estimated_tokens_base']:,} estimated tokens; "
            f"${item['projected_cost_usd_base']:.2f} projected ({item['api_price_assumption']}).\n"
        )
    rows.extend(["\n", resources["disclaimer"] + "\n\n"])
    titles = {
        "caught_and_prevented": "What supervision caught and prevented",
        "fixes_and_effectiveness": "Fixes and effectiveness",
        "recurring_patterns": "Recurring patterns",
        "blind_spots_and_misses": "Blind spots and misses",
        "development_pace": "Development pace",
        "monitoring_machinery_changes": "Monitoring machinery changes",
        "resource_efficiency": "Resource efficiency",
        "recommended_bounded_improvements": "Recommended bounded improvements",
        "methodology_and_limits": "Methodology and limits",
    }
    for section in REVIEW_SECTIONS:
        rows.append(f"## {titles[section]}\n\n")
        for entry in review["sections"][section]:
            rows.append(f"### {entry['title']}\n\n{entry['assessment']}  \n")
            rows.append("Evidence: " + ", ".join(f"`{item}`" for item in entry["evidence"]) + "\n\n")
    rows.append("## Material line items\n\n")
    for item in metrics["line_items"]:
        block = f" Block {item['active_block']}." if str(item.get("active_block", "")).isdigit() else ""
        rows.append(
            f"- **{item['timestamp']} - {item['record_id']}** ({item['kind']}/{item['status']}).{block} {item['summary']}\n"
        )
    rows.append("\n## Mechanical limitations\n\n")
    rows.extend(f"- {item}\n" for item in metrics["limitations"])
    return "".join(rows)


def render_pdf(
    output: Path, metrics: Mapping[str, Any], review: Mapping[str, Any]
) -> None:
    try:
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise WeeklyReportError("ReportLab is unavailable") from exc

    navy = colors.HexColor("#14213D")
    blue = colors.HexColor("#276FBF")
    cyan = colors.HexColor("#3FA7D6")
    teal = colors.HexColor("#2A9D8F")
    amber = colors.HexColor("#F4A261")
    red = colors.HexColor("#D1495B")
    mist = colors.HexColor("#EEF3F8")
    ink = colors.HexColor("#1F2937")
    muted = colors.HexColor("#5B6675")
    palette = [blue, cyan, teal, amber, red, colors.HexColor("#7D5BA6"), colors.HexColor("#9CA3AF")]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=navy, alignment=TA_LEFT, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubTitle", parent=styles["Normal"], fontSize=11, leading=16, textColor=muted, spaceAfter=18))
    styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=navy, spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=blue, spaceBefore=7, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.2, leading=13, textColor=ink, spaceAfter=7))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.4, leading=10, textColor=muted))
    styles.add(ParagraphStyle(name="CardNumber", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=navy, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CardLabel", parent=styles["Normal"], fontSize=7, leading=8, textColor=muted, alignment=TA_CENTER))

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.55 * inch,
        title=f"Supervision weekly review - {metrics['target_label']}",
        author="Codex Supervision",
        subject="Content-minimized supervision performance and effectiveness review",
    )
    story: list[Any] = []

    def paragraph(text: Any, style: str = "BodyCustom") -> Any:
        escaped = (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return Paragraph(escaped, styles[style])

    def header_footer(canvas: Any, current_doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.line(current_doc.leftMargin, 0.42 * inch, letter[0] - current_doc.rightMargin, 0.42 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(muted)
        canvas.drawString(current_doc.leftMargin, 0.25 * inch, metrics["report_id"])
        canvas.drawRightString(letter[0] - current_doc.rightMargin, 0.25 * inch, f"Page {current_doc.page}")
        canvas.restoreState()

    story.append(paragraph("SUPERVISION WEEKLY REVIEW", "Small"))
    story.append(paragraph(metrics["target_label"], "TitleCustom"))
    coverage = metrics["coverage"]
    duration_label = f"{coverage['elapsed_hours'] / 24:.1f} days"
    partial = " - inaugural partial week" if coverage["partial_week"] else ""
    story.append(paragraph(f"{coverage['start']} through {coverage['end']} | {duration_label}{partial} | {coverage['timezone']}", "SubTitle"))

    posture_colors = {
        "effective": teal,
        "effective-with-findings": blue,
        "mixed": amber,
        "needs-attention": red,
        "insufficient-evidence": muted,
    }
    posture_box = Table(
        [[paragraph(review["overall_posture"].upper(), "CardLabel"), paragraph(review["headline"], "H2Custom")]],
        colWidths=[1.55 * inch, 5.15 * inch],
    )
    posture_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), posture_colors[review["overall_posture"]]),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), mist),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([posture_box, Spacer(1, 0.14 * inch), paragraph(review["executive_assessment"]), Spacer(1, 0.10 * inch)])

    headline = metrics["headline"]
    cards = [
        (headline["recorded_events"], "Recorded events"),
        (headline["changed_state_routes"], "Changed states"),
        (headline["incidents_opened"], "Incidents opened"),
        (headline["incidents_terminal"], "Terminal outcomes"),
        (headline["blocks_observed"], "Blocks observed"),
        (headline["tooling_change_records"], "Tool changes"),
    ]
    card_cells = [[Paragraph(str(value), styles["CardNumber"]), Paragraph(label, styles["CardLabel"])] for value, label in cards]
    card_table = Table([card_cells], colWidths=[1.12 * inch] * 6)
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([card_table, Spacer(1, 0.15 * inch)])

    def stacked_chart(rows: Sequence[Mapping[str, Any]]) -> Any:
        width, height = 480, 155
        drawing = Drawing(width, height)
        categories = ("mechanical", "review", "routing", "intervention", "communication", "maintenance")
        totals = [sum(int(row.get(name, 0)) for name in categories) for row in rows]
        maximum = max(totals or [1])
        plot_left, plot_bottom, plot_width, plot_height = 35, 28, 430, 105
        bar_width = max(12, min(46, plot_width / max(1, len(rows)) * 0.62))
        gap = plot_width / max(1, len(rows))
        drawing.add(Rect(plot_left, plot_bottom, plot_width, plot_height, fillColor=colors.white, strokeColor=colors.HexColor("#D9E2EC")))
        for index, row in enumerate(rows):
            x = plot_left + gap * index + (gap - bar_width) / 2
            y = plot_bottom
            for color, category in zip(palette, categories):
                value = int(row.get(category, 0))
                segment = plot_height * value / maximum if maximum else 0
                if segment:
                    drawing.add(Rect(x, y, bar_width, segment, fillColor=color, strokeColor=None))
                y += segment
            label = str(row["date"])[5:]
            drawing.add(String(x + bar_width / 2, 12, label, fontName="Helvetica", fontSize=7, fillColor=muted, textAnchor="middle"))
        drawing.add(String(4, 137, f"max {maximum}", fontName="Helvetica", fontSize=6.5, fillColor=muted))
        legend_x = 38
        for color, category in zip(palette, categories):
            drawing.add(Rect(legend_x, 142, 7, 7, fillColor=color, strokeColor=None))
            drawing.add(String(legend_x + 10, 142, category, fontName="Helvetica", fontSize=6.5, fillColor=muted))
            legend_x += 69
        return drawing

    def availability_chart(value: Mapping[str, Any]) -> Any:
        width, height = 480, 78
        drawing = Drawing(width, height)
        active = float(value["core_heartbeats_scheduled_active_hours"])
        paused = float(value["core_heartbeats_explicitly_paused_hours"])
        total = max(active + paused, 0.001)
        plot_left, plot_bottom, plot_width, plot_height = 20, 30, 440, 20
        active_width = plot_width * active / total
        drawing.add(
            Rect(
                plot_left,
                plot_bottom,
                active_width,
                plot_height,
                fillColor=teal,
                strokeColor=None,
            )
        )
        drawing.add(
            Rect(
                plot_left + active_width,
                plot_bottom,
                plot_width - active_width,
                plot_height,
                fillColor=colors.HexColor("#CBD5E1"),
                strokeColor=None,
            )
        )
        drawing.add(
            String(
                plot_left,
                57,
                f"Scheduled active {active:.2f} h",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=teal,
            )
        )
        drawing.add(
            String(
                plot_left + plot_width,
                57,
                f"Explicitly paused {paused:.2f} h",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=muted,
                textAnchor="end",
            )
        )
        drawing.add(
            String(
                plot_left,
                14,
                "Explicit schedule posture only; quiet event gaps are not inferred downtime.",
                fontName="Helvetica",
                fontSize=7,
                fillColor=muted,
            )
        )
        return drawing

    def model_cost_chart(rows: Sequence[Mapping[str, Any]]) -> Any:
        width, height = 480, 142
        drawing = Drawing(width, height)
        maximum = max(
            (float(item["projected_cost_usd_high"]) for item in rows), default=1.0
        )
        maximum = max(maximum, 0.01)
        plot_left, plot_bottom, plot_width, plot_height = 70, 23, 385, 98
        row_height = plot_height / max(1, len(rows))
        for index, item in enumerate(rows):
            y = plot_bottom + plot_height - (index + 1) * row_height + 5
            low = plot_width * float(item["projected_cost_usd_low"]) / maximum
            base = plot_width * float(item["projected_cost_usd_base"]) / maximum
            high = plot_width * float(item["projected_cost_usd_high"]) / maximum
            drawing.add(
                String(
                    plot_left - 7,
                    y + 4,
                    str(item["model"]).replace("gpt-5.6-", ""),
                    fontName="Helvetica-Bold",
                    fontSize=7.5,
                    fillColor=ink,
                    textAnchor="end",
                )
            )
            drawing.add(
                Rect(
                    plot_left,
                    y,
                    high,
                    11,
                    fillColor=colors.HexColor("#DCE8F5"),
                    strokeColor=None,
                )
            )
            drawing.add(
                Rect(
                    plot_left,
                    y,
                    base,
                    11,
                    fillColor=blue,
                    strokeColor=None,
                )
            )
            drawing.add(
                Rect(
                    plot_left,
                    y,
                    low,
                    11,
                    fillColor=navy,
                    strokeColor=None,
                )
            )
            drawing.add(
                String(
                    min(plot_left + high + 5, width - 30),
                    y + 3,
                    f"${float(item['projected_cost_usd_base']):.2f}",
                    fontName="Helvetica",
                    fontSize=7,
                    fillColor=muted,
                )
            )
        drawing.add(
            String(
                plot_left,
                127,
                "Projected API-equivalent cost by model (low / base / high)",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=navy,
            )
        )
        return drawing

    story.extend([paragraph("Recorded monitoring activity by day", "H1Custom"), stacked_chart(metrics["daily_activity"]), paragraph("Each bar shows content-minimized records, not all scheduled wakes. Routing and communication are separated from substantive reviews and interventions.", "Small")])
    story.append(PageBreak())

    availability = metrics["availability"]
    story.append(paragraph("Availability and total monitored time", "H1Custom"))
    availability_rows = [
        ["Total report period", f"{availability['report_period_hours']:.2f} h"],
        ["Scheduled-active core heartbeat", f"{availability['core_heartbeats_scheduled_active_hours']:.2f} h ({availability['core_heartbeats_scheduled_active_percent']}%)"],
        ["Explicit core-heartbeat pause", f"{availability['core_heartbeats_explicitly_paused_hours']:.2f} h"],
        ["Recorded target-read availability", f"{availability['recorded_target_read_availability_percent']}% ({availability['recorded_target_read_successes']} success / {availability['recorded_target_read_failures']} failure)"],
        ["Continuous process uptime measured", "No"],
    ]
    availability_table = Table(
        [[paragraph(label, "BodyCustom"), paragraph(value, "BodyCustom")] for label, value in availability_rows],
        colWidths=[3.8 * inch, 2.9 * inch],
    )
    availability_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, mist]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([
        availability_table,
        availability_chart(availability),
        paragraph(availability["interpretation"], "Small"),
        Spacer(1, 0.12 * inch),
    ])

    resources = metrics["resource_estimate"]
    totals = resources["totals"]
    story.append(paragraph("Estimated token use and projected API-equivalent cost", "H1Custom"))
    story.append(model_cost_chart(resources["models"]))
    resource_rows = [[
        paragraph("Model", "Small"),
        paragraph("Records", "Small"),
        paragraph("Estimated tokens", "Small"),
        paragraph("Projected cost", "Small"),
        paragraph("API pricing assumption", "Small"),
    ]]
    for item in resources["models"]:
        resource_rows.append([
            paragraph(item["model"], "Small"),
            paragraph(item["recorded_model_attributed_events"], "Small"),
            paragraph(f"{item['estimated_tokens_base']:,} / {item['estimated_tokens_low']:,}-{item['estimated_tokens_high']:,}", "Small"),
            paragraph(f"${item['projected_cost_usd_base']:.2f} / ${item['projected_cost_usd_low']:.2f}-${item['projected_cost_usd_high']:.2f}", "Small"),
            paragraph(item["api_price_assumption"], "Small"),
        ])
    resource_rows.append([
        paragraph("TOTAL", "Small"),
        paragraph(totals["recorded_model_attributed_events"], "Small"),
        paragraph(f"{totals['estimated_tokens_base']:,} / {totals['estimated_tokens_low']:,}-{totals['estimated_tokens_high']:,}", "Small"),
        paragraph(f"${totals['projected_cost_usd_base']:.2f} / ${totals['projected_cost_usd_low']:.2f}-${totals['projected_cost_usd_high']:.2f}", "Small"),
        paragraph(resources["pricing_profile_id"], "Small"),
    ])
    resource_table = Table(
        resource_rows,
        colWidths=[1.05 * inch, 0.62 * inch, 1.35 * inch, 1.2 * inch, 2.48 * inch],
        repeatRows=1,
    )
    resource_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, mist]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([
        resource_table,
        paragraph(resources["method"], "Small"),
        paragraph(resources["disclaimer"], "Small"),
    ])
    for item in resources["models"]:
        story.append(
            paragraph(
                f"{item['model']}: {item['api_price_assumption']}; "
                f"${float(item['input_usd_per_million_tokens']):.2f}/M input, "
                f"${float(item['output_usd_per_million_tokens']):.2f}/M output; "
                f"source {item['source_url']}",
                "Small",
            )
        )
    story.append(PageBreak())

    section_titles = {
        "caught_and_prevented": "What supervision caught and prevented",
        "fixes_and_effectiveness": "What was fixed - and whether it worked",
        "recurring_patterns": "Recurring patterns and emerging risks",
        "blind_spots_and_misses": "False positives, misses, and blind spots",
        "development_pace": "Development pace and implementation flow",
        "monitoring_machinery_changes": "Monitoring machinery change log",
        "resource_efficiency": "Operational efficiency",
        "recommended_bounded_improvements": "Recommended bounded improvements",
        "methodology_and_limits": "Methodology and limits",
    }
    for section in REVIEW_SECTIONS:
        story.append(paragraph(section_titles[section], "H1Custom"))
        for entry in review["sections"][section]:
            evidence = ", ".join(entry["evidence"])
            story.append(KeepTogether([
                paragraph(entry["title"], "H2Custom"),
                paragraph(entry["assessment"]),
                paragraph(f"Evidence: {evidence}", "Small"),
                Spacer(1, 0.05 * inch),
            ]))

    story.append(PageBreak())
    story.append(paragraph("Monitoring tasks and recorded activity", "H1Custom"))
    task_rows = [[paragraph("Task", "Small"), paragraph("Recorded", "Small"), paragraph("Expected cadence / trigger", "Small")]]
    for item in metrics["task_activity"]:
        task_rows.append([paragraph(item["task"], "BodyCustom"), paragraph(item["recorded_count"], "BodyCustom"), paragraph(item["cadence"], "Small")])
    task_table = Table(task_rows, colWidths=[1.7 * inch, 0.75 * inch, 4.25 * inch], repeatRows=1)
    task_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, mist]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([task_table, Spacer(1, 0.16 * inch)])

    rates = metrics["rates"]
    rate_rows = [
        ["Incidents / 100 changed-state routes", rates["incidents_per_100_changed_state_routes"]],
        ["Terminal share of opened incidents", f"{rates['terminal_share_of_opened_percent']}%" if rates["terminal_share_of_opened_percent"] is not None else "n/a"],
        ["Median detection-to-terminal", f"{rates['incident_detection_to_terminal_median_hours']} h" if rates["incident_detection_to_terminal_median_hours"] is not None else "n/a"],
        ["P90 detection-to-terminal", f"{rates['incident_detection_to_terminal_p90_hours']} h" if rates["incident_detection_to_terminal_p90_hours"] is not None else "n/a"],
        ["Open incidents at end", headline["incidents_open_at_end"]],
    ]
    story.append(paragraph("Incident and correction posture", "H1Custom"))
    rate_table = Table([[paragraph(a, "BodyCustom"), paragraph(b, "BodyCustom")] for a, b in rate_rows], colWidths=[4.9 * inch, 1.8 * inch])
    rate_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, mist]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([rate_table, paragraph(rates["denominator_note"], "Small")])

    story.append(PageBreak())
    story.append(paragraph("Observed implementation flow", "H1Custom"))
    block_rows = [[paragraph("Block", "Small"), paragraph("First observed", "Small"), paragraph("Last observed", "Small"), paragraph("Records", "Small"), paragraph("Checkpoints", "Small")]]
    for item in metrics["blocks"]:
        block_rows.append([
            paragraph(item["block"], "BodyCustom"),
            paragraph(item["first_seen"], "Small"),
            paragraph(item["last_seen"], "Small"),
            paragraph(item["event_count"], "BodyCustom"),
            paragraph(item["checkpoint_count"], "BodyCustom"),
        ])
    block_table = Table(block_rows, colWidths=[0.55 * inch, 2.2 * inch, 2.2 * inch, 0.8 * inch, 0.85 * inch], repeatRows=1)
    block_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, mist]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([block_table, paragraph("Observed activity is not equivalent to accepted Block completion. Acceptance remains owned by the tracker and exact audit evidence.", "Small")])

    story.append(PageBreak())
    story.append(paragraph("Material line items", "H1Custom"))
    line_rows = [[paragraph("Time / record", "Small"), paragraph("Posture", "Small"), paragraph("Summary", "Small")]]
    for item in metrics["line_items"]:
        block = f"B{item['active_block']} " if str(item.get("active_block", "")).isdigit() else ""
        line_rows.append([
            paragraph(f"{item['timestamp']} / {item['record_id']}", "Small"),
            paragraph(f"{block}{item['kind']} / {item['status']}", "Small"),
            paragraph(item["summary"], "Small"),
        ])
    line_table = Table(line_rows, colWidths=[1.42 * inch, 1.24 * inch, 4.04 * inch], repeatRows=1)
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(line_table)

    story.append(PageBreak())
    story.append(paragraph("Evidence and interpretation boundary", "H1Custom"))
    story.append(paragraph(f"Report ID: {metrics['report_id']}"))
    story.append(paragraph(f"Source root: {metrics['source']['source_root']}"))
    story.append(paragraph(f"Source records: {metrics['source']['first_record_id']} through {metrics['source']['last_record_id']} ({metrics['source']['event_count']} records)"))
    story.append(paragraph("The PDF is a deterministic rendering of canonical metrics plus a validated full-window cognitive review. It is operational evidence only. It is not patent authority, a legal conclusion, a quality score, or proof that the monitored implementation is complete."))
    for item in metrics["limitations"]:
        story.append(paragraph(f"- {item}"))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    os.chmod(output, 0o600)


def manifest_for(
    *,
    metrics_path: Path,
    packet_path: Path,
    review_path: Path,
    report_json_path: Path,
    markdown_path: Path,
    pdf_path: Path,
) -> dict[str, Any]:
    files = {}
    for path in (
        metrics_path,
        packet_path,
        review_path,
        report_json_path,
        markdown_path,
        pdf_path,
    ):
        files[path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-manifest",
        "files": files,
        "manifest_root": digest(files),
    }
