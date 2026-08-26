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
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo


SCHEMA_VERSION = 1
REPORT_KIND = "supervision-weekly-review"
DEFAULT_PRICING_PROFILE = (
    Path(__file__).resolve().parent / "weekly-report-pricing-v1.json"
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
SUPERVISOR_SCOPE_TERMS = re.compile(
    r"\b(supervision|supervisor|monitor|monitoring|watcher|reviewer|review|"
    r"detection|routing|incident|correction|automation|report|reporting|alert|"
    r"intervention|escalation|validation|evidence|command|skill|policy|email|"
    r"gmail|runtime|availability|cost|token)\b",
    re.IGNORECASE,
)
TARGET_RECOMMENDATION_TERMS = re.compile(
    r"\b(block\s+\d+|panel|claim|filing|figure|renderer|route[- ]disposition|"
    r"route conflict|patent authority|maintained filing)\b",
    re.IGNORECASE,
)

REPORT_PALETTE = {
    "navy": "#14213D",
    "blue": "#145DA0",
    "cyan": "#167D9A",
    "teal": "#117864",
    "amber": "#8A4B00",
    "red": "#B3261E",
    "mist": "#F2F5F8",
    "ink": "#17212F",
    "muted": "#3F4A59",
    "white": "#FFFFFF",
}


class WeeklyReportError(RuntimeError):
    pass


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG relative-luminance contrast ratio for two hex colors."""

    def luminance(value: str) -> float:
        raw = value.removeprefix("#")
        if len(raw) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", raw):
            raise WeeklyReportError(f"Invalid report color: {value}")
        channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def validate_report_contrast() -> None:
    """Fail before rendering if maintained text/background pairs are illegible."""

    pairs = (
        ("white", "navy"),
        ("white", "blue"),
        ("white", "teal"),
        ("white", "amber"),
        ("white", "red"),
        ("white", "muted"),
        ("ink", "white"),
        ("muted", "white"),
        ("ink", "mist"),
        ("blue", "mist"),
    )
    failures = [
        f"{foreground} on {background}={contrast_ratio(REPORT_PALETTE[foreground], REPORT_PALETTE[background]):.2f}"
        for foreground, background in pairs
        if contrast_ratio(REPORT_PALETTE[foreground], REPORT_PALETTE[background]) < 4.5
    ]
    if failures:
        raise WeeklyReportError(
            "Weekly report palette fails the maintained 4.5:1 contrast floor: "
            + ", ".join(failures)
        )


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


def monitoring_roles(
    current_policy: Mapping[str, Any], window_events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Project configured supervision threads into operator-readable roles."""

    runtime = current_policy.get("runtime")
    if not isinstance(runtime, Mapping):
        runtime = {}

    role_definitions = (
        (
            "Routine watcher",
            "Mechanical change gate and scheduled target checks.",
            "watcher_thread_id",
            lambda item: item.get("kind") == "check"
            and item.get("model") == "gpt-5.6-terra",
            "watcher checks",
        ),
        (
            "Semantic reviewer",
            "Substantive review of each routed changed target state.",
            "base_reviewer_thread_id",
            lambda item: item.get("kind") == "check"
            and item.get("reasoning") == "xhigh",
            "semantic reviews",
        ),
        (
            "Max reviewer",
            "Sampled changed-state review plus scheduled effectiveness review.",
            "reviewer_thread_id",
            lambda item: (
                item.get("kind") == "check" and item.get("category") == "max-sample"
            )
            or item.get("kind") == "meta-review",
            "sample/effectiveness reviews",
        ),
        (
            "Incident outcome reviewer",
            "Material incident adjudication and correction-outcome review.",
            "notice_reviewer_thread_id",
            lambda item: "incident-review" in str(item.get("category", ""))
            or item.get("category") in {"notice-review", "notice-outcome-review"},
            "incident review actions",
        ),
        (
            "Fix executor",
            "Independently approved, bounded fixes to supervision machinery.",
            "fix_executor_thread_id",
            lambda item: item.get("category") == "fix-execution",
            "fix actions",
        ),
        (
            "Roundup/report writer",
            "Scheduled summaries and cognitive weekly supervision review.",
            "roundup_thread_id",
            lambda item: item.get("kind") == "roundup",
            "roundups",
        ),
        (
            "Gmail reply gate",
            "Validates whether an inbound roundup-thread reply may be processed.",
            "gmail_gate_thread_id",
            lambda item: item.get("kind") == "inbound-message"
            and item.get("category") == "gmail-reply-gate",
            "reply-gate records",
        ),
        (
            "Gmail reply processor",
            "Processes only replies admitted by the maintained Gmail gate.",
            "gmail_processor_thread_id",
            lambda item: item.get("kind") == "inbound-message"
            and item.get("category") == "gmail-reply-processor",
            "reply-processing records",
        ),
    )
    roles = []
    for role, purpose, thread_key, test, activity_label in role_definitions:
        roles.append(
            {
                "role": role,
                "purpose": purpose,
                "configured": isinstance(runtime.get(thread_key), str)
                and bool(runtime.get(thread_key)),
                "recorded_action_count": sum(1 for item in window_events if test(item)),
                "activity_label": activity_label,
            }
        )
    return {
        "configured_thread_count": sum(1 for item in roles if item["configured"]),
        "core_role_count": sum(
            1 for item in roles[:6] if item["configured"]
        ),
        "support_role_count": sum(
            1 for item in roles[6:] if item["configured"]
        ),
        "roles": roles,
        "interpretation": "Configured threads describe the maintained supervision roles. Recorded actions are ledger-visible lower bounds because unchanged scheduled wakes may intentionally emit no record.",
    }


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
    bounded_events: Sequence[Mapping[str, Any]],
    start: dt.datetime,
    end: dt.datetime,
    *,
    canonical_resume_record_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Compute explicit schedule posture without inferring silence as downtime."""

    window_events = [item for item in bounded_events if in_window(item, start, end)]
    if not window_events:
        raise WeeklyReportError("Weekly report window contains no supervision events")

    def pause_identity(item: Mapping[str, Any]) -> tuple[str, str] | None:
        record_id = item.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            return None
        if (
            item.get("kind") == "lifecycle"
            and item.get("category") == "supervision-pause"
            and item.get("status") == "paused"
            and isinstance(item.get("state_fingerprint"), str)
            and item.get("state_fingerprint")
        ):
            return record_id, "canonical-lifecycle"
        if (
            item.get("kind") == "policy-change"
            and item.get("category") == "stop-condition-pause"
            and item.get("status") == "paused"
        ):
            return record_id, "legacy-policy-change"
        return None

    def resumes_pause(
        item: Mapping[str, Any], pause_record_id: str, pause_kind: str
    ) -> bool:
        if pause_kind == "canonical-lifecycle":
            return bool(
                item.get("record_id") in canonical_resume_record_ids
                and item.get("resume_contract_version") == 1
                and item.get("kind") == "lifecycle"
                and item.get("category") == "supervision-resume"
                and item.get("status") == "resumed"
                and item.get("pause_record_id") == pause_record_id
                and isinstance(item.get("source_currentness_root"), str)
                and isinstance(item.get("eligibility_root"), str)
                and isinstance(item.get("automation_evidence_root"), str)
            )
        return bool(
            pause_kind == "legacy-policy-change"
            and item.get("kind") == "policy-change"
            and item.get("category") == "supervision-resume"
            and item.get("status") == "resumed"
        )

    active = True
    cursor = start
    active_seconds = 0.0
    paused_seconds = 0.0
    intervals: list[dict[str, Any]] = []
    pause_start: dt.datetime | None = None
    pause_record: str | None = None
    pause_kind: str | None = None
    ordered = sorted(
        (item for item in bounded_events if record_time(item) <= end),
        key=record_time,
    )

    # Establish exact posture at the report boundary from retained history.
    for item in (item for item in ordered if record_time(item) < start):
        identity = pause_identity(item)
        if identity is not None and active:
            active = False
            pause_start = record_time(item)
            pause_record, pause_kind = identity
        elif (
            not active
            and pause_record is not None
            and pause_kind is not None
            and resumes_pause(item, pause_record, pause_kind)
        ):
            active = True
            pause_start = None
            pause_record = None
            pause_kind = None

    for item in (item for item in ordered if start <= record_time(item) <= end):
        stamp = record_time(item)
        identity = pause_identity(item)
        is_resume = bool(
            not active
            and pause_record is not None
            and pause_kind is not None
            and resumes_pause(item, pause_record, pause_kind)
        )
        if identity is not None and active:
            active_seconds += max(0.0, (stamp - cursor).total_seconds())
            active = False
            cursor = stamp
            pause_start = stamp
            pause_record, pause_kind = identity
        elif is_resume and not active:
            paused_seconds += max(0.0, (stamp - cursor).total_seconds())
            intervals.append(
                {
                    "start": iso_time(max(pause_start or cursor, start)),
                    "end": iso_time(stamp),
                    "hours": round((stamp - cursor).total_seconds() / 3600, 2),
                    "pause_record_id": pause_record,
                    "resume_record_id": item.get("record_id"),
                    "evidence_posture": pause_kind,
                }
            )
            active = True
            cursor = stamp
            pause_start = None
            pause_record = None
            pause_kind = None
    if active:
        active_seconds += max(0.0, (end - cursor).total_seconds())
    else:
        paused_seconds += max(0.0, (end - cursor).total_seconds())
        intervals.append(
            {
                "start": iso_time(max(pause_start or cursor, start)),
                "end": iso_time(end),
                "hours": round((end - cursor).total_seconds() / 3600, 2),
                "pause_record_id": pause_record,
                "resume_record_id": None,
                "evidence_posture": pause_kind,
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
        "interpretation": "Scheduled-active time is derived only from exact canonical pause/resume lifecycle pairs or retained legacy policy-change pairs. A canonical resume closes only its named pause predecessor. Target-read availability uses recorded material read outcomes. Quiet gaps are not downtime because unchanged wakes may emit no event.",
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
    canonical_resume_record_ids: frozenset[str] = frozenset(),
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
        "current_policy_sha256": current_policy.get("policy_sha256"),
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
    open_heads = [incident_heads[incident] for incident in open_at_end]
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
            "incidents_open_high_or_critical": sum(
                1
                for item in open_heads
                if str(item.get("severity", "")).lower() in {"high", "critical"}
            ),
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
        "availability": availability_metrics(
            bounded_events,
            start,
            end,
            canonical_resume_record_ids=canonical_resume_record_ids,
        ),
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
        "monitoring_roles": monitoring_roles(current_policy, window_events),
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
            "reporting_scope": "Evaluate only the supervision and monitoring machinery. Monitored implementation facts may appear only as bounded evidence of detection or effectiveness.",
            "recommendation_scope": "Recommend changes only to supervisor watchers, reviewers, routing, incident handling, report generation, or operating policy. Never prescribe changes to the monitored target.",
            "presentation": "Lead with the executive dashboard, use at most three concise evidence-backed findings per review section, define every chart, and start every major review domain on a new page.",
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
        if not isinstance(entries, list) or not entries or len(entries) > 3:
            raise WeeklyReportError(f"Review section {section} requires 1-3 entries")
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
            combined = f"{clean_entries[-1]['title']} {clean_entries[-1]['assessment']}"
            if not SUPERVISOR_SCOPE_TERMS.search(combined):
                raise WeeklyReportError(
                    f"Review section {section} entry {index} lacks supervisor focus"
                )
            if (
                section == "recommended_bounded_improvements"
                and TARGET_RECOMMENDATION_TERMS.search(combined)
            ):
                raise WeeklyReportError(
                    "Weekly recommendations must improve supervision machinery, not the monitored target"
                )
        clean_sections[section] = clean_entries
    result["sections"] = clean_sections
    return result


def report_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Return the supervisor-only metrics projection used by durable reports."""

    included = (
        "schema_version",
        "kind",
        "report_id",
        "target_label",
        "coverage",
        "source",
        "headline",
        "rates",
        "availability",
        "resource_estimate",
        "counts",
        "daily_activity",
        "daily_incidents",
        "monitoring_roles",
        "task_activity",
        "incidents",
        "limitations",
    )
    return {key: metrics[key] for key in included}


def machine_report(
    metrics: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-record",
        "report_id": metrics["report_id"],
        "source_root": metrics["source"]["source_root"],
        "coverage": metrics["coverage"],
        "metrics": report_metrics(metrics),
        "cognitive_review": review,
    }


def executive_takeaways(review: Mapping[str, Any]) -> list[str]:
    section_labels = (
        ("Detection", "caught_and_prevented"),
        ("Effectiveness", "fixes_and_effectiveness"),
        ("Residual risk", "blind_spots_and_misses"),
        ("Efficiency", "resource_efficiency"),
        ("Next improvement", "recommended_bounded_improvements"),
    )
    return [
        f"{label}: {review['sections'][section][0]['title']}"
        for label, section in section_labels
    ]


def markdown_report(metrics: Mapping[str, Any], review: Mapping[str, Any]) -> str:
    headline = metrics["headline"]
    coverage = metrics["coverage"]
    availability = metrics["availability"]
    resources = metrics["resource_estimate"]
    resource_totals = resources["totals"]
    roles = metrics["monitoring_roles"]
    rows = [
        f"# Supervision weekly review - {metrics['target_label']}\n",
        f"**Coverage:** {coverage['start']} through {coverage['end']} ({coverage['timezone']})  \n",
        f"**Posture:** {review['overall_posture']}  \n",
        f"**Evidence root:** `{metrics['source']['source_root']}`\n\n",
        "## Executive metrics\n\n",
        f"- Scheduled monitoring time: {availability['core_heartbeats_scheduled_active_hours']} hours\n",
        f"- Projected API-equivalent cost: ${resource_totals['projected_cost_usd_base']:.2f}\n",
        f"- Incidents detected / resolved or closed / unresolved: {headline['incidents_opened']} / {headline['incidents_terminal']} / {headline['incidents_open_at_end']}\n",
        f"- High or critical unresolved incidents: {headline['incidents_open_high_or_critical']}\n",
        f"- Configured supervision role threads: {roles['configured_thread_count']}\n\n",
        "## What was running\n\n",
        *[
            f"- **{item['role']}**: {item['purpose']} "
            f"{item['recorded_action_count']} {item['activity_label']} "
            f"({'configured' if item['configured'] else 'not configured'}).\n"
            for item in roles["roles"]
        ],
        "\n## Monitoring time and recorded read reliability\n\n",
        f"- Total report period: {availability['report_period_hours']} hours\n",
        f"- Scheduled monitoring time: {availability['core_heartbeats_scheduled_active_hours']} hours ({availability['core_heartbeats_scheduled_active_percent']}%)\n",
        f"- Explicitly paused monitoring time: {availability['core_heartbeats_explicitly_paused_hours']} hours\n",
        f"- Recorded target-read reliability: {availability['recorded_target_read_availability_percent']}% ({availability['recorded_target_read_successes']} successful / {availability['recorded_target_read_failures']} failed)\n",
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
    rows.extend(
        [
            "## Supervisor assessment\n\n",
            f"**{review['headline']}**\n\n",
            *[f"- {item}\n" for item in executive_takeaways(review)],
            "\nThis report evaluates the supervisor and monitoring machinery. Target implementation details appear only as content-minimized evidence identifiers; they are not report recommendations.\n\n",
        ]
    )
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
    rows.append("## Supervisor incident posture\n\n")
    rows.append(
        f"- Opened: {headline['incidents_opened']}; terminal: {headline['incidents_terminal']}; open at cutoff: {headline['incidents_open_at_end']}.\n"
    )
    rows.append(
        "- Terminal status distribution: "
        + ", ".join(
            f"{key}={value}"
            for key, value in metrics["incidents"]["terminal_statuses"].items()
        )
        + "\n"
    )
    if metrics["incidents"]["open_at_end_ids"]:
        rows.append(
            "- Open incident evidence IDs: "
            + ", ".join(f"`{item}`" for item in metrics["incidents"]["open_at_end_ids"])
            + "\n"
        )
    rows.append("\n## Mechanical limitations\n\n")
    rows.extend(f"- {item}\n" for item in metrics["limitations"])
    return "".join(rows)


def render_pdf(
    output: Path,
    metrics: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    factory_evolution_eligibility: Mapping[str, Any] | None = None,
    factory_evolution_outcomes: Mapping[str, Any] | None = None,
) -> None:
    validate_report_contrast()
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

    navy = colors.HexColor(REPORT_PALETTE["navy"])
    blue = colors.HexColor(REPORT_PALETTE["blue"])
    cyan = colors.HexColor(REPORT_PALETTE["cyan"])
    teal = colors.HexColor(REPORT_PALETTE["teal"])
    amber = colors.HexColor(REPORT_PALETTE["amber"])
    red = colors.HexColor(REPORT_PALETTE["red"])
    mist = colors.HexColor(REPORT_PALETTE["mist"])
    ink = colors.HexColor(REPORT_PALETTE["ink"])
    muted = colors.HexColor(REPORT_PALETTE["muted"])
    palette = [blue, cyan, teal, amber, red, colors.HexColor("#6B4FA1"), colors.HexColor("#5E6875")]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=navy, alignment=TA_LEFT, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubTitle", parent=styles["Normal"], fontSize=11, leading=16, textColor=muted, spaceAfter=18))
    styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=navy, spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=blue, spaceBefore=7, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9.2, leading=13, textColor=ink, spaceAfter=7))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.8, leading=10.5, textColor=muted))
    styles.add(ParagraphStyle(name="CardNumber", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=navy, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CardLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.5, textColor=muted, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle(name="PostureLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="SectionKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=blue, spaceAfter=5))
    styles.add(ParagraphStyle(name="BulletCustom", parent=styles["BodyText"], fontSize=9.5, leading=13.5, textColor=ink, leftIndent=13, firstLineIndent=-8, bulletIndent=3, spaceAfter=7))
    styles.add(ParagraphStyle(name="LegendLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=ink))
    styles.add(ParagraphStyle(name="LegendBody", parent=styles["Normal"], fontSize=7.2, leading=9, textColor=muted))
    styles.add(ParagraphStyle(name="RoleTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.7, leading=9.2, textColor=navy, spaceAfter=2))
    styles.add(ParagraphStyle(name="RoleBody", parent=styles["Normal"], fontSize=7, leading=8.5, textColor=ink))

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

    coverage = metrics["coverage"]
    availability = metrics["availability"]
    resources = metrics["resource_estimate"]
    totals = resources["totals"]
    headline = metrics["headline"]
    role_projection = metrics["monitoring_roles"]

    def display_target(value: Any) -> str:
        return " ".join(
            token.upper() if token.lower() in {"rgda"} else token.capitalize()
            for token in str(value).replace("-", " ").split()
        )

    def local_timestamp(value: str) -> str:
        stamp = parse_time(value).astimezone(ZoneInfo(str(coverage["timezone"])))
        return (
            f"{stamp.strftime('%b')} {stamp.day}, {stamp.year} at "
            f"{stamp.strftime('%I:%M %p %Z').lstrip('0')}"
        )

    story.append(paragraph("SUPERVISION WEEKLY REVIEW", "Small"))
    story.append(paragraph("Executive summary", "TitleCustom"))
    duration_label = f"{coverage['elapsed_hours'] / 24:.1f} days"
    partial = " (inaugural partial week)" if coverage["partial_week"] else ""
    story.extend(
        [
            paragraph(f"Monitored target: {display_target(metrics['target_label'])}", "SubTitle"),
            paragraph(f"Coverage start: {local_timestamp(coverage['start'])}", "Small"),
            paragraph(f"Coverage end: {local_timestamp(coverage['end'])}", "Small"),
            paragraph(f"Report window: {duration_label}{partial}", "Small"),
            Spacer(1, 0.09 * inch),
        ]
    )

    posture_colors = {
        "effective": teal,
        "effective-with-findings": blue,
        "mixed": amber,
        "needs-attention": red,
        "insufficient-evidence": muted,
    }
    posture_box = Table(
        [[paragraph(review["overall_posture"].upper(), "PostureLabel"), paragraph(review["headline"], "H2Custom")]],
        colWidths=[1.85 * inch, 4.85 * inch],
    )
    posture_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), posture_colors[review["overall_posture"]]),
        ("BACKGROUND", (1, 0), (1, 0), mist),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    cards = [
        (f"{availability['core_heartbeats_scheduled_active_hours']:.1f} h", "Scheduled monitoring time"),
        (f"${totals['projected_cost_usd_base']:.2f}", "Projected API-equivalent cost"),
        (headline["incidents_opened"], "Incidents detected"),
        (headline["incidents_terminal"], "Incidents resolved / closed"),
        (headline["incidents_open_high_or_critical"], "High / critical unresolved"),
        (role_projection["configured_thread_count"], "Configured role threads"),
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
    story.extend([card_table, Spacer(1, 0.11 * inch), posture_box])
    if factory_evolution_eligibility is not None:
        story.append(paragraph("Factory evolution nomination", "H2Custom"))
        story.append(
            paragraph(factory_evolution_eligibility["summary"], "BodyCustom")
        )
    if factory_evolution_outcomes is not None:
        story.append(paragraph("Factory evolution outcomes", "H2Custom"))
        current_outcomes = factory_evolution_outcomes.get("current_outcomes", [])
        if current_outcomes:
            for item in current_outcomes:
                story.append(
                    paragraph(
                        f"{item['evolution_id']}: {item['outcome_posture']}; "
                        f"next {item['next_action']}.",
                        "BodyCustom",
                    )
                )
        else:
            story.append(
                paragraph("No current terminal Factory-evolution outcome.", "BodyCustom")
            )
    story.append(paragraph("Executive supervisor assessment", "H2Custom"))
    for takeaway in executive_takeaways(review)[:4]:
        story.append(Paragraph(f"• {takeaway}", styles["BulletCustom"]))

    story.append(paragraph("What was running", "H2Custom"))
    role_cells = []
    for item in role_projection["roles"]:
        state = "configured" if item["configured"] else "not configured"
        role_cells.append(
            [
                Paragraph(
                    f"{item['role']} — {item['recorded_action_count']} {item['activity_label']}",
                    styles["RoleTitle"],
                ),
                Paragraph(f"{item['purpose']} ({state})", styles["RoleBody"]),
            ]
        )
    role_rows = []
    for index in range(0, len(role_cells), 2):
        role_rows.append(
            [
                Table([[item] for item in role_cells[index]], colWidths=[3.18 * inch]),
                Table([[item] for item in role_cells[index + 1]], colWidths=[3.18 * inch]),
            ]
        )
    role_table = Table(role_rows, colWidths=[3.35 * inch, 3.35 * inch])
    role_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, mist]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([role_table, paragraph(role_projection["interpretation"], "Small")])

    story.append(paragraph("Inside this report", "H2Custom"))
    contents = [
        "Monitoring time, read reliability, and projected cost",
        "Activity, incidents, and response time",
        "Supervisor effectiveness",
        "Detection quality",
        "Coverage and operating efficiency",
        "Monitoring machinery evolution",
        "Methodology and evidence boundary",
    ]
    contents_table = Table(
        [
            [paragraph(contents[index], "Small"), paragraph(contents[index + 1], "Small")]
            for index in range(0, 6, 2)
        ]
        + [[paragraph(contents[6], "Small"), ""]],
        colWidths=[3.35 * inch, 3.35 * inch],
    )
    contents_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(contents_table)

    def axis_scale(maximum: float, target_ticks: int = 4) -> tuple[float, list[float]]:
        maximum = max(float(maximum), 0.0)
        if maximum == 0:
            return 1.0, [0.0, 0.25, 0.5, 0.75, 1.0]
        rough_step = maximum / target_ticks
        magnitude = 10 ** math.floor(math.log10(rough_step))
        normalized = rough_step / magnitude
        factor = next(item for item in (1, 2, 5, 10) if item >= normalized)
        step = factor * magnitude
        axis_maximum = math.ceil(maximum / step) * step
        ticks = [index * step for index in range(int(round(axis_maximum / step)) + 1)]
        return axis_maximum, ticks

    def format_tick(value: float) -> str:
        return f"{int(value):,}" if float(value).is_integer() else f"{value:,.1f}"

    def definition_legend(
        entries: Sequence[tuple[Any, str, str]], *, columns: int = 1
    ) -> Any:
        rows = []
        for index in range(0, len(entries), columns):
            row: list[Any] = []
            for _color, label, explanation in entries[index : index + columns]:
                row.extend(
                    [
                        "",
                        Paragraph(
                            f"<b>{label}</b> — {explanation}", styles["LegendBody"]
                        ),
                    ]
                )
            while len(row) < columns * 2:
                row.extend(["", ""])
            rows.append(row)
        text_width = (6.7 - 0.13 * columns) / columns
        table = Table(
            rows, colWidths=[value for _ in range(columns) for value in (0.13 * inch, text_width * inch)]
        )
        commands = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        for index, (color, _label, _explanation) in enumerate(entries):
            row_index = index // columns
            column_index = (index % columns) * 2
            commands.append(
                (
                    "BACKGROUND",
                    (column_index, row_index),
                    (column_index, row_index),
                    color,
                )
            )
        table.setStyle(TableStyle(commands))
        return table

    def stacked_chart(rows: Sequence[Mapping[str, Any]]) -> Any:
        width, height = 480, 150
        drawing = Drawing(width, height)
        categories = ("mechanical", "review", "routing", "intervention", "communication", "maintenance")
        totals = [sum(int(row.get(name, 0)) for name in categories) for row in rows]
        maximum, ticks = axis_scale(max(totals or [0]))
        plot_left, plot_bottom, plot_width, plot_height = 57, 35, 405, 93
        bar_width = max(12, min(46, plot_width / max(1, len(rows)) * 0.62))
        gap = plot_width / max(1, len(rows))
        drawing.add(Rect(plot_left, plot_bottom, plot_width, plot_height, fillColor=colors.white, strokeColor=colors.HexColor("#AEBAC7")))
        for tick in ticks:
            y = plot_bottom + plot_height * tick / maximum
            drawing.add(
                Rect(
                    plot_left,
                    y,
                    plot_width,
                    0.35,
                    fillColor=colors.HexColor("#D9E2EC"),
                    strokeColor=None,
                )
            )
            drawing.add(
                String(
                    plot_left - 7,
                    y - 2.5,
                    format_tick(tick),
                    fontName="Helvetica",
                    fontSize=6.7,
                    fillColor=muted,
                    textAnchor="end",
                )
            )
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
            drawing.add(String(x + bar_width / 2, 21, label, fontName="Helvetica", fontSize=7, fillColor=muted, textAnchor="middle"))
        drawing.add(String(plot_left, 137, "Y axis: recorded supervision records", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink))
        drawing.add(String(plot_left + plot_width / 2, 7, f"Local calendar day ({coverage['timezone']})", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink, textAnchor="middle"))
        return drawing

    def availability_chart(value: Mapping[str, Any]) -> Any:
        width, height = 480, 93
        drawing = Drawing(width, height)
        active = float(value["core_heartbeats_scheduled_active_hours"])
        paused = float(value["core_heartbeats_explicitly_paused_hours"])
        total = max(active + paused, 0.001)
        plot_left, plot_bottom, plot_width, plot_height = 25, 39, 430, 20
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
                72,
                f"Scheduled active {active:.2f} h",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=teal,
            )
        )
        drawing.add(
            String(
                plot_left + plot_width,
                72,
                f"Explicitly paused {paused:.2f} h",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=muted,
                textAnchor="end",
            )
        )
        for percent in (0, 25, 50, 75, 100):
            x = plot_left + plot_width * percent / 100
            drawing.add(String(x, 25, f"{percent}%", fontName="Helvetica", fontSize=6.7, fillColor=muted, textAnchor="middle"))
        drawing.add(String(plot_left + plot_width / 2, 8, "Share of the report window", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink, textAnchor="middle"))
        return drawing

    def incident_chart(rows: Sequence[Mapping[str, Any]]) -> Any:
        width, height = 480, 112
        drawing = Drawing(width, height)
        maximum = max(
            (max(int(row.get("opened", 0)), int(row.get("terminal", 0))) for row in rows),
            default=1,
        )
        maximum, ticks = axis_scale(maximum)
        plot_left, plot_bottom, plot_width, plot_height = 57, 35, 405, 52
        gap = plot_width / max(1, len(rows))
        bar_width = min(19, gap * 0.24)
        drawing.add(
            Rect(
                plot_left,
                plot_bottom,
                plot_width,
                plot_height,
                fillColor=colors.white,
                strokeColor=colors.HexColor("#C6CFD9"),
            )
        )
        for tick in ticks:
            y = plot_bottom + plot_height * tick / maximum
            drawing.add(Rect(plot_left, y, plot_width, 0.35, fillColor=colors.HexColor("#D9E2EC"), strokeColor=None))
            drawing.add(String(plot_left - 7, y - 2.5, format_tick(tick), fontName="Helvetica", fontSize=6.7, fillColor=muted, textAnchor="end"))
        for index, row in enumerate(rows):
            center = plot_left + gap * index + gap / 2
            for offset, key, color in (
                (-bar_width, "opened", red),
                (0, "terminal", teal),
            ):
                value = int(row.get(key, 0))
                bar_height = plot_height * value / maximum
                drawing.add(
                    Rect(
                        center + offset,
                        plot_bottom,
                        bar_width,
                        bar_height,
                        fillColor=color,
                        strokeColor=None,
                    )
                )
            drawing.add(
                String(
                    center,
                    20,
                    str(row["date"])[5:],
                    fontName="Helvetica",
                    fontSize=7,
                    fillColor=muted,
                    textAnchor="middle",
                )
            )
        drawing.add(String(plot_left, 99, "Y axis: incident count", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink))
        drawing.add(String(plot_left + plot_width / 2, 7, f"Local calendar day ({coverage['timezone']})", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink, textAnchor="middle"))
        return drawing

    def model_cost_chart(rows: Sequence[Mapping[str, Any]]) -> Any:
        width, height = 480, 158
        drawing = Drawing(width, height)
        maximum = max(
            (float(item["projected_cost_usd_high"]) for item in rows), default=1.0
        )
        maximum, ticks = axis_scale(max(maximum, 0.01))
        plot_left, plot_bottom, plot_width, plot_height = 78, 38, 360, 94
        row_height = plot_height / max(1, len(rows))
        for tick in ticks:
            x = plot_left + plot_width * tick / maximum
            drawing.add(Rect(x, plot_bottom, 0.35, plot_height, fillColor=colors.HexColor("#D9E2EC"), strokeColor=None))
            drawing.add(String(x, 24, f"${format_tick(tick)}", fontName="Helvetica", fontSize=6.5, fillColor=muted, textAnchor="middle"))
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
                143,
                "Projected API-equivalent cost by model",
                fontName="Helvetica-Bold",
                fontSize=8,
                fillColor=navy,
            )
        )
        drawing.add(String(plot_left + plot_width / 2, 7, "Projected API-equivalent cost (USD)", fontName="Helvetica-Bold", fontSize=7.2, fillColor=ink, textAnchor="middle"))
        return drawing

    story.append(PageBreak())

    story.append(paragraph("Monitoring time, read reliability, and projected cost", "H1Custom"))
    story.append(
        paragraph(
            "This page separates explicit schedule posture, recorded target-read reliability, and projected resource use. It does not infer continuous process uptime from quiet ledger gaps.",
            "SubTitle",
        )
    )
    availability_rows = [
        ["Total report period", f"{availability['report_period_hours']:.2f} h"],
        ["Scheduled monitoring time", f"{availability['core_heartbeats_scheduled_active_hours']:.2f} h ({availability['core_heartbeats_scheduled_active_percent']}%)"],
        ["Explicitly paused monitoring time", f"{availability['core_heartbeats_explicitly_paused_hours']:.2f} h"],
        ["Recorded target-read reliability", f"{availability['recorded_target_read_availability_percent']}% ({availability['recorded_target_read_successes']} successful / {availability['recorded_target_read_failures']} failed reads)"],
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

    story.append(paragraph("Estimated token use and projected API-equivalent cost", "H1Custom"))
    story.append(model_cost_chart(resources["models"]))
    story.append(
        definition_legend(
            (
                (navy, "Low estimate", "Lower token multiplier from the versioned estimation profile."),
                (blue, "Base estimate", "Central API-equivalent projection used in the executive summary."),
                (colors.HexColor("#DCE8F5"), "High estimate", "Upper token multiplier; still a projection, not billed usage."),
            ),
            columns=3,
        )
    )
    resource_rows = [[
        paragraph("Model", "TableHeader"),
        paragraph("Records", "TableHeader"),
        paragraph("Estimated tokens", "TableHeader"),
        paragraph("Projected cost", "TableHeader"),
        paragraph("API pricing assumption", "TableHeader"),
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
    ])
    story.append(PageBreak())

    story.append(paragraph("Activity, incidents, and response time", "H1Custom"))
    story.append(
        paragraph(
            "These charts show ledger-visible supervision activity by local day. Their units and categories describe the monitoring system, not implementation quality.",
            "SubTitle",
        )
    )
    story.extend(
        [
            paragraph("Recorded monitoring activity by day", "H2Custom"),
            stacked_chart(metrics["daily_activity"]),
            definition_legend(
                (
                    (blue, "Mechanical", "Scheduled watcher, check, and control records."),
                    (cyan, "Review", "Semantic, sampled, checkpoint, and effectiveness review records."),
                    (teal, "Routing", "Handoffs for changed target states and incident evidence."),
                    (amber, "Intervention", "Incident openings, corrective steers, and terminal resolutions."),
                    (red, "Communication", "Roundups, approved notifications, and lifecycle communication."),
                    (colors.HexColor("#6B4FA1"), "Maintenance", "Supervisor policy, skill, and reporting-maintenance records."),
                ),
                columns=2,
            ),
            paragraph("Incident detection and resolution by day", "H2Custom"),
            incident_chart(metrics["daily_incidents"]),
            definition_legend(
                (
                    (red, "Detected", "A new material supervision incident opened during the report window."),
                    (teal, "Resolved / closed", "The incident's first terminal outcome was recorded during the window; this does not mean an implementation Block completed."),
                ),
                columns=2,
            ),
        ]
    )

    rates = metrics["rates"]
    rate_rows = [
        ["Detection yield", f"{rates['incidents_per_100_changed_state_routes']} incidents per 100 routed changed states"],
        ["Resolved / closed share", f"{rates['terminal_share_of_opened_percent']}% of incidents detected in the period" if rates["terminal_share_of_opened_percent"] is not None else "n/a"],
        ["Median detection-to-resolution time", f"{rates['incident_detection_to_terminal_median_hours']} h" if rates["incident_detection_to_terminal_median_hours"] is not None else "n/a"],
        ["P90 detection-to-resolution time", f"{rates['incident_detection_to_terminal_p90_hours']} h" if rates["incident_detection_to_terminal_p90_hours"] is not None else "n/a"],
        ["Unresolved incidents at cutoff", f"{headline['incidents_open_at_end']} total; {headline['incidents_open_high_or_critical']} high/critical"],
    ]
    story.append(paragraph("Incident response posture", "H2Custom"))
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

    section_titles = {
        "caught_and_prevented": "What supervision caught or prevented",
        "fixes_and_effectiveness": "Whether supervisor corrections worked",
        "recurring_patterns": "Recurring supervision failure classes",
        "blind_spots_and_misses": "False positives, misses, and blind spots",
        "development_pace": "Coverage and monitored development pace",
        "monitoring_machinery_changes": "Monitoring machinery change log",
        "resource_efficiency": "Supervisor operating efficiency",
        "recommended_bounded_improvements": "Improvements to supervision machinery",
        "methodology_and_limits": "Methodology and limits",
    }

    def add_review_section(section: str) -> None:
        story.append(paragraph(section_titles[section], "H2Custom"))
        for entry in review["sections"][section]:
            evidence = ", ".join(entry["evidence"])
            story.append(
                KeepTogether(
                    [
                        paragraph(entry["title"], "SectionKicker"),
                        paragraph(entry["assessment"]),
                        paragraph(f"Evidence: {evidence}", "Small"),
                        Spacer(1, 0.06 * inch),
                    ]
                )
            )

    review_groups = (
        (
            "Supervisor effectiveness",
            "Detection value and correction effectiveness",
            ("caught_and_prevented", "fixes_and_effectiveness"),
        ),
        (
            "Detection quality",
            "Recurrence, false positives, misses, and blind spots",
            ("recurring_patterns", "blind_spots_and_misses"),
        ),
        (
            "Coverage and operating efficiency",
            "Pace, resource posture, and avoidable supervision cost",
            ("development_pace", "resource_efficiency"),
        ),
        (
            "Monitoring machinery evolution",
            "What changed in the supervisor and what should improve next",
            ("monitoring_machinery_changes", "recommended_bounded_improvements"),
        ),
        (
            "Methodology and evidence boundary",
            "How to interpret this supervisor-performance report",
            ("methodology_and_limits",),
        ),
    )
    for title, subtitle, sections in review_groups:
        story.append(PageBreak())
        story.append(paragraph(title, "H1Custom"))
        story.append(paragraph(subtitle, "SubTitle"))
        for section in sections:
            add_review_section(section)
        if sections == ("methodology_and_limits",):
            story.append(paragraph("Exact evidence binding", "H2Custom"))
            story.append(paragraph(f"Report ID: {metrics['report_id']}", "Small"))
            story.append(paragraph(f"Source root: {metrics['source']['source_root']}", "Small"))
            story.append(paragraph(f"Source records: {metrics['source']['first_record_id']} through {metrics['source']['last_record_id']} ({metrics['source']['event_count']} records)", "Small"))
            story.append(paragraph("The PDF is a deterministic supervisor-performance projection. It does not direct the monitored implementation, confer tracker completion, or establish patent or legal quality.", "Small"))
            story.append(paragraph("Resource projection boundary", "H2Custom"))
            story.append(paragraph(resources["method"], "Small"))
            story.append(paragraph(resources["disclaimer"], "Small"))
            for item in metrics["limitations"]:
                story.append(Paragraph(f"• {item}", styles["BulletCustom"]))

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
