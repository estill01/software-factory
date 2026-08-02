#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DEFAULT_ROOT = Path.home() / ".codex" / "supervision" / "tracker-runs"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$")
KINDS = {
    "check",
    "lifecycle",
    "incident",
    "escalation",
    "steer",
    "resolution",
    "checkpoint-review",
    "meta-review",
    "policy-change",
    "notification",
    "inbound-message",
    "roundup",
    "decision",
}
STANDARD_LIFECYCLE_STATES = {"completed", "paused"}
PRIORITY_LIFECYCLE_STATES = {"blocked", "failed", "stopped"}
LIFECYCLE_STATES = STANDARD_LIFECYCLE_STATES | PRIORITY_LIFECYCLE_STATES
SEVERITIES = {"info", "warning", "high", "critical"}
TERMINAL_INCIDENT_STATUSES = {
    "corrected",
    "false-positive",
    "accepted-risk",
    "superseded",
    "closed",
}
NON_COMPLETION_CHECK_CATEGORIES = {"max-sample", "meta-sample"}
GMAIL_CONVERSATION_NOTIFICATION_CATEGORIES = {
    "gmail-user-ack",
    "gmail-user-outcome",
}
NOTICE_DISPOSITIONS = {
    "critical",
    "user-action",
    "blocked",
    "correction-issued",
    "intermediate",
    "terminal",
    "operational-warning",
}
RESOLUTION_OWNERS = {"target", "supervisor", "user", "none"}
IMMEDIATE_NOTICE_DISPOSITIONS = {
    "critical",
    "user-action",
    "blocked",
    "correction-issued",
}
SKILL_MAINTENANCE_MODES = {
    "propose-only",
    "apply-supervision-maintenance",
    "apply-allowlisted-skill-maintenance-with-review",
}
ALLOWLISTED_MAINTENANCE_SKILLS = [
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
]
EXECUTION_ECONOMY_DIMENSIONS = [
    "batching",
    "convergence",
    "ordering",
    "proportionality",
    "relevance",
    "resource-posture",
    "reuse",
    "scope",
    "stability",
    "stopping",
]
DECISION_CLASSIFICATIONS = {
    "delegable",
    "human-preference",
    "missing-fact",
    "reserved-authority",
}
DECISION_PHASES = {
    "decision-ready",
    "user-responded",
    "attempt-started",
    "attempt-unresolved",
    "resolved",
    "safe-deferred",
    "handoff-sent",
    "target-acknowledged",
}
SAFE_FRONTIER_POSTURES = {"empty", "nonempty"}
DECISION_OUTCOMES = {"", "selected", "safe-deferred", "user-supplied"}
THREAD_ROUTE_PURPOSE_ROLES = {
    "changed-state-review": ("base_reviewer",),
    "fix-execution": ("fix_executor",),
    "gmail-reply-processing": ("gmail_processor",),
    "incident-review": ("notice_reviewer",),
    "role-refresh": (
        "base_reviewer",
        "fix_executor",
        "gmail_processor",
        "notice_reviewer",
        "reviewer",
        "roundup_writer",
        "watcher",
    ),
    "roundup-action": ("roundup_writer",),
    "semantic-escalation": ("reviewer",),
    "target-action": ("target",),
    "watcher-action": ("watcher",),
}
THREAD_ROUTE_ROLE_FIELDS = {
    "watcher": "watcher_thread_id",
    "reviewer": "reviewer_thread_id",
    "base_reviewer": "base_reviewer_thread_id",
    "notice_reviewer": "notice_reviewer_thread_id",
    "fix_executor": "fix_executor_thread_id",
    "gmail_processor": "gmail_processor_thread_id",
    "roundup_writer": "roundup_thread_id",
}


class SupervisionLogError(RuntimeError):
    pass


def execution_economy_contract() -> dict[str, Any]:
    return {
        "enabled": True,
        "dimensions": EXECUTION_ECONOMY_DIMENSIONS,
        "semantic_review_required": True,
        "systemic_candidate_threshold": {
            "minimum_distinct_episodes": 2,
            "single_material_episode_allowed": True,
        },
    }


def skill_maintenance_contract(mode: str = "propose-only") -> dict[str, Any]:
    if mode not in SKILL_MAINTENANCE_MODES:
        raise SupervisionLogError("Unsupported skill-maintenance mode")
    return {
        "mode": mode,
        "allowlist": ALLOWLISTED_MAINTENANCE_SKILLS,
        "deprojectize_required": True,
        "independent_review_required": True,
        "refresh_active_roles_after_acceptance": True,
    }


def decision_resolution_contract() -> dict[str, Any]:
    return {
        "enabled": True,
        "continuation_first": True,
        "blocking_requires_empty_safe_frontier": True,
        "attempt_before_user_notification": True,
        "continue_attempts_during_user_window": True,
        "human_response_minutes": 20,
        "attempt_model": "gpt-5.6-sol",
        "attempt_reasoning": "max",
        "attempt_minutes": 20,
        "max_attempts": 3,
        "start_next_attempt_without_idle_wait": True,
        "final_disposition": {
            "delegable": "select-and-proceed",
            "human-preference": "select-and-proceed",
            "missing-fact": "safe-defer-with-open-fact",
            "reserved-authority": "safe-defer-with-open-authority",
        },
        "priority_phase_notifications": [
            "human-input-requested",
            "final-disposition",
            "target-resumed",
        ],
    }


def cross_thread_routing_contract() -> dict[str, Any]:
    return {
        "enabled": True,
        "ordinary_progress_owner": "target-thread",
        "gate_command": "thread-route-gate",
        "required_action_packet": True,
        "purpose_roles": {
            purpose: list(roles)
            for purpose, roles in THREAD_ROUTE_PURPOSE_ROLES.items()
        },
        "unrelated_thread_behavior": "fail-closed",
        "routine_status_behavior": "remain-in-target-thread",
        "email_behavior": "existing-notification-gates-only",
    }


def legacy_single_role_cross_thread_routing_contract() -> dict[str, Any]:
    """Exact predecessor accepted only so `bind` can add role refresh."""
    contract = cross_thread_routing_contract()
    contract["purpose_roles"] = {
        purpose: roles[0]
        for purpose, roles in THREAD_ROUTE_PURPOSE_ROLES.items()
        if purpose != "role-refresh"
    }
    return contract


def legacy_wait_first_decision_resolution_contract() -> dict[str, Any]:
    """Exact predecessor accepted only so `bind` can upgrade a live policy."""
    contract = decision_resolution_contract()
    contract.pop("attempt_before_user_notification")
    contract.pop("continue_attempts_during_user_window")
    contract["priority_phase_notifications"] = [
        "decision-ready",
        "automatic-resolution-started",
        "final-disposition",
        "target-resumed",
    ]
    return contract


def gmail_priority_contract() -> dict[str, Any]:
    return {
        "enabled": False,
        "recipient": "me",
        "thread_scope": "monitored-project-priority-lifecycle",
        "project_key": None,
        "reply_message_id": None,
        "subject": None,
        "delivery_policy": "immediate-genuine-decision-and-blocked-failed-stopped",
        "lifecycle_states": sorted(PRIORITY_LIFECYCLE_STATES),
        "banner": "🚨 IMPLEMENTATION BLOCKED / STOPPED 🚨",
        "decision_context_enabled": False,
        "decision_context_policy": "concise-decision-brief-when-user-action-required",
        "required_decision_fields": [
            "decision",
            "recommendation",
            "why-recommended",
            "material-alternatives",
            "tradeoffs-and-uncertainties",
            "consequence-of-no-action",
            "response-options",
            "authoritative-detail-link",
        ],
    }


def ensure_execution_economy_policy(policy: dict[str, Any]) -> bool:
    changed = False
    expected_economy = execution_economy_contract()
    if policy.get("execution_economy") != expected_economy:
        policy["execution_economy"] = expected_economy
        changed = True
    expected_decisions = decision_resolution_contract()
    if policy.get("decision_resolution") != expected_decisions:
        policy["decision_resolution"] = expected_decisions
        changed = True
    expected_thread_routing = cross_thread_routing_contract()
    if policy.get("cross_thread_routing") != expected_thread_routing:
        policy["cross_thread_routing"] = expected_thread_routing
        changed = True
    current_maintenance = policy.get("skill_maintenance")
    mode = (
        current_maintenance.get("mode", "propose-only")
        if isinstance(current_maintenance, dict)
        else "propose-only"
    )
    expected_maintenance = skill_maintenance_contract(mode)
    if current_maintenance != expected_maintenance:
        policy["skill_maintenance"] = expected_maintenance
        changed = True
    expected_permission = (
        mode == "apply-allowlisted-skill-maintenance-with-review"
    )
    permissions = policy.setdefault("permissions", {})
    if permissions.get("allowlisted_skill_maintenance") is not expected_permission:
        permissions["allowlisted_skill_maintenance"] = expected_permission
        changed = True
    if "gmail_priority_notification" not in permissions:
        permissions["gmail_priority_notification"] = False
        changed = True
    notifications = policy.setdefault("notifications", {})
    if "gmail_priority" not in notifications:
        notifications["gmail_priority"] = gmail_priority_contract()
        changed = True
    return changed


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        result = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SupervisionLogError("Time must be ISO-8601") from exc
    if result.tzinfo is None:
        raise SupervisionLogError("Time must include a timezone")
    return result.astimezone(dt.timezone.utc).replace(microsecond=0)


def iso_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def clean(value: str | None, *, label: str, maximum: int = 600) -> str:
    text = (value or "").strip()
    if len(text) > maximum:
        raise SupervisionLogError(f"{label} exceeds {maximum} characters")
    if "\n" in text or "\r" in text:
        raise SupervisionLogError(f"{label} must be one line")
    if "/Users/" in text or "file://" in text or "\\Users\\" in text:
        raise SupervisionLogError(f"{label} must not contain a local path")
    return text


def safe_id(value: str, *, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise SupervisionLogError(f"Invalid {label}")
    return value


def optional_safe_id(value: str | None, *, label: str) -> str | None:
    return safe_id(value, label=label) if value else None


def root_from(args: argparse.Namespace) -> Path:
    return Path(args.root).expanduser().resolve() if args.root else DEFAULT_ROOT.resolve()


def target_dir(args: argparse.Namespace) -> Path:
    target = safe_id(args.target_thread, label="target thread ID")
    root = root_from(args)
    result = (root / target).resolve()
    if result.parent != root:
        raise SupervisionLogError("Target log directory escaped the supervision root")
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupervisionLogError(f"Cannot read supervision state: {path.name}") from exc
    if not isinstance(value, dict):
        raise SupervisionLogError(f"Supervision state is not an object: {path.name}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def default_policy(args: argparse.Namespace) -> dict[str, Any]:
    target = safe_id(args.target_thread, label="target thread ID")
    policy: dict[str, Any] = {
        "schema_version": 1,
        "policy_version": 1,
        "target_thread_id": target,
        "target_label": clean(args.target_label, label="target label", maximum=80)
        or target[:12],
        "models": {
            "routine": {"model": "gpt-5.6-terra", "reasoning": "max"},
            "base_reviewer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
            "notice_reviewer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
            "reviewer": {"model": "gpt-5.6-sol", "reasoning": "max"},
            "fix_executor": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
            "gmail_gate": {"model": "gpt-5.6-luna", "reasoning": "low"},
            "gmail_processor": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
            "roundup_writer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        },
        "schedule": {
            "routine_minutes": 20,
            "high_risk_minutes": 15,
            "meta_review_hours": 4,
            "gmail_poll_minutes": 2,
            "gmail_quiet_poll_minutes": 2,
            "gmail_active_poll_minutes": 1,
            "gmail_active_window_minutes": 30,
            "roundup_timezone": "America/Los_Angeles",
            "roundup_local_times": ["07:00", "13:00", "17:00", "23:00"],
        },
        "routing": {
            "xhigh_every_changed_state": True,
            "max_sample_denominator": 6,
            "sample_records_complete_gate": False,
            "escalation_cooldown_minutes": 60,
            "max_escalations_per_hour": 1,
        },
        "read_bounds": {
            "newest_turns": 4,
            "summaries_first": True,
            "raw_output_only_after_trigger": True,
        },
        "permissions": {
            "repository_write": False,
            "command_or_test_execution": False,
            "supervision_log_write": True,
            "bounded_thread_steer": True,
            "bounded_supervision_maintenance": True,
            "allowlisted_skill_maintenance": False,
            "gmail_self_notification": False,
            "gmail_inbound_processing": False,
            "gmail_priority_notification": False,
            "gmail_roundup_notification": False,
        },
        "execution_economy": execution_economy_contract(),
        "decision_resolution": decision_resolution_contract(),
        "cross_thread_routing": cross_thread_routing_contract(),
        "skill_maintenance": skill_maintenance_contract(),
        "notifications": {
            "gmail": {
                "enabled": False,
                "recipient": "me",
                "thread_scope": "monitored-project",
                "project_key": None,
                "reply_message_id": None,
                "subject": None,
                "delivery_policy": "material-alerts-and-new-evidence-meta-digest",
                "inbound_enabled": False,
                "notice_gate_required": True,
                "immediate_dispositions": sorted(IMMEDIATE_NOTICE_DISPOSITIONS),
                "automatic_intermediate_delivery": "digest-only",
                "terminal_delivery": "primary-outcome-if-previously-alerted",
                "lifecycle_immediate_states": sorted(STANDARD_LIFECYCLE_STATES),
                "lifecycle_banner": "IMPLEMENTATION STATUS",
            },
            "gmail_priority": gmail_priority_contract(),
            "gmail_roundup": {
                "enabled": False,
                "recipient": "me",
                "thread_scope": "monitored-project-roundup",
                "project_key": None,
                "reply_message_id": None,
                "subject": None,
                "delivery_policy": "scheduled-pacific-operational-change-log",
            },
        },
        "runtime": {
            "watcher_thread_id": safe_id(args.watcher_thread, label="watcher thread ID"),
            "reviewer_thread_id": safe_id(args.reviewer_thread, label="reviewer thread ID"),
            "base_reviewer_thread_id": optional_safe_id(
                args.base_reviewer_thread, label="base reviewer thread ID"
            ),
            "notice_reviewer_thread_id": optional_safe_id(
                getattr(args, "notice_reviewer_thread", None),
                label="notice reviewer thread ID",
            ),
            "fix_executor_thread_id": optional_safe_id(
                args.fix_executor_thread, label="fix executor thread ID"
            ),
            "routine_automation_id": None,
            "meta_automation_id": None,
            "gmail_gate_thread_id": None,
            "gmail_processor_thread_id": None,
            "gmail_poll_automation_id": None,
            "roundup_thread_id": None,
            "roundup_automation_id": None,
        },
        "created_at": utc_now(),
    }
    policy["policy_sha256"] = digest(policy)
    return policy


def policy_material(policy: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in policy.items() if key != "policy_sha256"}


def validate_policy(policy: dict[str, Any]) -> None:
    expected = digest(policy_material(policy))
    if policy.get("policy_sha256") != expected:
        raise SupervisionLogError("Supervision policy hash is stale")
    if policy.get("schema_version") != 1:
        raise SupervisionLogError("Unsupported supervision policy schema")
    maintenance = policy.get("skill_maintenance")
    if maintenance is not None:
        if maintenance.get("mode") not in SKILL_MAINTENANCE_MODES:
            raise SupervisionLogError("Unsupported skill-maintenance mode")
        if maintenance.get("allowlist") != ALLOWLISTED_MAINTENANCE_SKILLS:
            raise SupervisionLogError("Skill-maintenance allowlist differs")
    economy = policy.get("execution_economy")
    if economy is not None and economy != execution_economy_contract():
        raise SupervisionLogError("Execution-economy contract differs")
    decisions = policy.get("decision_resolution")
    if decisions is not None and canonical(decisions) not in {
        canonical(decision_resolution_contract()),
        canonical(legacy_wait_first_decision_resolution_contract()),
    }:
        raise SupervisionLogError("Decision-resolution contract differs")
    thread_routing = policy.get("cross_thread_routing")
    if thread_routing is not None and canonical(thread_routing) not in {
        canonical(cross_thread_routing_contract()),
        canonical(legacy_single_role_cross_thread_routing_contract()),
    }:
        raise SupervisionLogError("Cross-thread routing contract differs")
    priority = policy.get("notifications", {}).get("gmail_priority")
    if priority is not None:
        expected_priority = gmail_priority_contract()
        for key in (
            "recipient",
            "thread_scope",
            "delivery_policy",
            "lifecycle_states",
            "banner",
            "decision_context_policy",
            "required_decision_fields",
        ):
            if key in {"decision_context_policy", "required_decision_fields"} and key not in priority:
                # Additive decision-context fields are backfilled by `bind` so
                # already-running supervisors can adopt the new contract in place.
                continue
            if (
                key == "delivery_policy"
                and priority.get(key) == "immediate-blocked-failed-stopped-only"
            ):
                # `bind` upgrades already-running supervisors in place.
                continue
            if priority.get(key) != expected_priority[key]:
                raise SupervisionLogError("Gmail priority lifecycle contract differs")
        if priority.get("decision_context_enabled") is True:
            if priority.get("enabled") is not True:
                raise SupervisionLogError(
                    "Decision context requires an enabled Gmail priority binding"
                )
            if (
                priority.get("required_decision_fields")
                != expected_priority["required_decision_fields"]
            ):
                raise SupervisionLogError(
                    "Enabled decision context requires every maintained decision field"
                )
        if priority.get("enabled"):
            if not all(
                priority.get(key)
                for key in ("project_key", "reply_message_id", "subject")
            ):
                raise SupervisionLogError("Enabled Gmail priority lifecycle binding is incomplete")
            if policy.get("permissions", {}).get("gmail_priority_notification") is not True:
                raise SupervisionLogError("Enabled Gmail priority lifecycle permission is absent")


@contextmanager
def append_lock(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".append.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_raw_locked(path: Path, value: dict[str, Any]) -> None:
    existing = events(path)
    previous = existing[-1].get("record_sha256") if existing else None
    material = dict(value)
    material["previous_record_sha256"] = previous
    material["record_sha256"] = digest(material)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, canonical(material) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def append_raw(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with append_lock(path.parent):
        append_raw_locked(path, value)


def events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    previous: str | None = None
    record_ids: set[str] = set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SupervisionLogError(
                f"Ledger {path.name} has malformed JSON at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise SupervisionLogError("Event ledger contains a non-object")
        recorded_hash = value.get("record_sha256")
        material = {key: item for key, item in value.items() if key != "record_sha256"}
        if material.get("previous_record_sha256") != previous:
            raise SupervisionLogError(
                f"Ledger {path.name} has a broken hash chain at line {line_number}"
            )
        if not isinstance(recorded_hash, str) or digest(material) != recorded_hash:
            raise SupervisionLogError(
                f"Ledger {path.name} has a stale record hash at line {line_number}"
            )
        record_id = value.get("record_id")
        if isinstance(record_id, str):
            if record_id in record_ids:
                raise SupervisionLogError(
                    f"Ledger {path.name} repeats record ID {record_id}"
                )
            record_ids.add(record_id)
        previous = recorded_hash
        result.append(value)
    return result


def append_markdown(path: Path, record: dict[str, Any], *, create: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if create and path.exists():
        raise SupervisionLogError(f"Material report already exists: {path.name}")
    mode = "x" if create else "a"
    heading = f"# {record['incident_id']}\n" if create else f"\n## {record['kind']} — {record['timestamp']}\n"
    rows = [heading]
    for key in (
        "timestamp",
        "kind",
        "status",
        "severity",
        "category",
        "model",
        "reasoning",
        "active_block",
        "checkpoint",
        "state_fingerprint",
        "summary",
        "estimated_risk",
        "action",
        "resolution",
        "notice_disposition",
        "resolution_owner",
        "user_action_required",
        "policy_sha256",
    ):
        value = record.get(key)
        if value not in (None, ""):
            rows.append(f"- {key.replace('_', ' ').title()}: `{value}`\n")
    if record.get("evidence"):
        rows.append("- Evidence: " + ", ".join(f"`{item}`" for item in record["evidence"]) + "\n")
    with path.open(mode, encoding="utf-8") as handle:
        handle.writelines(rows)
    os.chmod(path, 0o600)


def cmd_init(args: argparse.Namespace) -> None:
    directory = target_dir(args)
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    (directory / "incidents").mkdir(exist_ok=True)
    (directory / "reviews").mkdir(exist_ok=True)
    policy_path = directory / "policy.json"
    if policy_path.exists():
        policy = read_json(policy_path)
        validate_policy(policy)
        expected = default_policy(args)
        for key in ("target_thread_id", "target_label"):
            if policy.get(key) != expected.get(key):
                raise SupervisionLogError(f"Existing policy conflicts on {key}")
        for key in ("watcher_thread_id", "reviewer_thread_id"):
            if policy.get("runtime", {}).get(key) != expected["runtime"][key]:
                raise SupervisionLogError(f"Existing policy conflicts on runtime {key}")
        print(json.dumps({"created": False, "policy": policy}, sort_keys=True))
        return
    policy = default_policy(args)
    atomic_json(policy_path, policy)
    append_raw(
        directory / "policy-history.jsonl",
        {
            "schema_version": 1,
            "record_id": f"POLICY-{policy['policy_version']}",
            "timestamp": utc_now(),
            "kind": "policy-init",
            "policy": policy,
        },
    )
    print(json.dumps({"created": True, "policy": policy}, sort_keys=True))


def load_policy(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    directory = target_dir(args)
    policy = read_json(directory / "policy.json")
    validate_policy(policy)
    if policy.get("target_thread_id") != args.target_thread:
        raise SupervisionLogError("Policy belongs to a different target")
    return directory, policy


def write_policy_version(
    directory: Path,
    policy: dict[str, Any],
    *,
    kind: str,
    reason: str,
    evidence_values: list[str],
) -> None:
    policy["policy_version"] = int(policy["policy_version"]) + 1
    policy["updated_at"] = utc_now()
    policy["policy_sha256"] = digest(policy_material(policy))
    atomic_json(directory / "policy.json", policy)
    append_raw(
        directory / "policy-history.jsonl",
        {
            "schema_version": 1,
            "record_id": f"POLICY-{policy['policy_version']}",
            "timestamp": utc_now(),
            "kind": kind,
            "reason": reason,
            "evidence": evidence_values,
            "policy": policy,
        },
    )


def cmd_bind(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    runtime = policy["runtime"]
    updates = {
        "base_reviewer_thread_id": args.base_reviewer_thread,
        "notice_reviewer_thread_id": args.notice_reviewer_thread,
        "fix_executor_thread_id": args.fix_executor_thread,
        "routine_automation_id": args.routine_automation,
        "meta_automation_id": args.meta_automation,
        "gmail_gate_thread_id": args.gmail_gate_thread,
        "gmail_processor_thread_id": args.gmail_processor_thread,
        "gmail_poll_automation_id": args.gmail_poll_automation,
        "roundup_thread_id": args.roundup_thread,
        "roundup_automation_id": args.roundup_automation,
    }
    changed = ensure_execution_economy_policy(policy)
    for key, raw in updates.items():
        if not raw:
            continue
        value = safe_id(raw, label=key.replace("_", " "))
        if runtime.get(key) not in (None, value):
            raise SupervisionLogError(f"Runtime binding already differs for {key}")
        if runtime.get(key) != value:
            runtime[key] = value
            changed = True
    model_defaults = {
        "base_reviewer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        "notice_reviewer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        "fix_executor": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        "gmail_gate": {"model": "gpt-5.6-luna", "reasoning": "low"},
        "gmail_processor": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
        "roundup_writer": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
    }
    for key, value in model_defaults.items():
        if policy.setdefault("models", {}).get(key) != value:
            policy["models"][key] = value
            changed = True
    if not policy.setdefault("permissions", {}).get(
        "bounded_supervision_maintenance", False
    ):
        policy["permissions"]["bounded_supervision_maintenance"] = True
        changed = True
    gmail = policy.setdefault("notifications", {}).setdefault(
        "gmail",
        {
            "enabled": False,
            "recipient": "me",
            "thread_scope": "monitored-project",
            "project_key": None,
            "reply_message_id": None,
            "subject": None,
            "delivery_policy": "material-alerts-and-new-evidence-meta-digest",
            "inbound_enabled": False,
        },
    )
    gmail_notice_defaults = {
        "notice_gate_required": True,
        "immediate_dispositions": sorted(IMMEDIATE_NOTICE_DISPOSITIONS),
        "automatic_intermediate_delivery": "digest-only",
        "terminal_delivery": "primary-outcome-if-previously-alerted",
        "lifecycle_immediate_states": sorted(STANDARD_LIFECYCLE_STATES),
        "lifecycle_banner": "IMPLEMENTATION STATUS",
    }
    for key, value in gmail_notice_defaults.items():
        if gmail.get(key) != value:
            gmail[key] = value
            changed = True
    if args.gmail_reply_message_id:
        message_id = safe_id(
            args.gmail_reply_message_id, label="Gmail reply message ID"
        )
        project_key = safe_id(
            args.gmail_project_key or policy["target_label"],
            label="Gmail monitored project key",
        )
        subject = clean(
            args.gmail_subject or f"Codex Tracker Supervision - {project_key}",
            label="Gmail subject",
            maximum=160,
        )
        if gmail.get("reply_message_id") not in (None, message_id):
            raise SupervisionLogError("Gmail reply message binding already differs")
        if gmail.get("subject") not in (None, subject):
            raise SupervisionLogError("Gmail subject binding already differs")
        desired_gmail = {
            "enabled": True,
            "recipient": "me",
            "thread_scope": "monitored-project",
            "project_key": project_key,
            "reply_message_id": message_id,
            "subject": subject,
            "delivery_policy": "material-alerts-and-new-evidence-meta-digest",
        }
        for key, value in desired_gmail.items():
            if gmail.get(key) != value:
                gmail[key] = value
                changed = True
        if policy["permissions"].get("gmail_self_notification") is not True:
            policy["permissions"]["gmail_self_notification"] = True
            changed = True
    priority = policy.setdefault("notifications", {}).setdefault(
        "gmail_priority", gmail_priority_contract()
    )
    for key, value in gmail_priority_contract().items():
        if key in {
            "enabled",
            "project_key",
            "reply_message_id",
            "subject",
            "decision_context_enabled",
        }:
            continue
        if priority.get(key) != value:
            priority[key] = value
            changed = True
    if args.gmail_priority_reply_message_id:
        priority_message_id = safe_id(
            args.gmail_priority_reply_message_id,
            label="Gmail priority reply message ID",
        )
        priority_project_key = safe_id(
            args.gmail_priority_project_key
            or gmail.get("project_key")
            or policy["target_label"],
            label="Gmail priority monitored project key",
        )
        priority_subject = clean(
            args.gmail_priority_subject
            or f"PRIORITY - Codex Implementation Blocked or Stopped - {priority_project_key}",
            label="Gmail priority subject",
            maximum=160,
        )
        if priority.get("reply_message_id") not in (None, priority_message_id):
            raise SupervisionLogError("Gmail priority reply binding already differs")
        if priority.get("subject") not in (None, priority_subject):
            raise SupervisionLogError("Gmail priority subject binding already differs")
        desired_priority = {
            "enabled": True,
            "recipient": "me",
            "thread_scope": "monitored-project-priority-lifecycle",
            "project_key": priority_project_key,
            "reply_message_id": priority_message_id,
            "subject": priority_subject,
            "delivery_policy": gmail_priority_contract()["delivery_policy"],
            "lifecycle_states": sorted(PRIORITY_LIFECYCLE_STATES),
            "banner": "🚨 IMPLEMENTATION BLOCKED / STOPPED 🚨",
        }
        for key, value in desired_priority.items():
            if priority.get(key) != value:
                priority[key] = value
                changed = True
        if policy["permissions"].get("gmail_priority_notification") is not True:
            policy["permissions"]["gmail_priority_notification"] = True
            changed = True
    if args.gmail_priority_decision_context:
        if not priority.get("enabled") or not priority.get("reply_message_id"):
            raise SupervisionLogError(
                "Bind the Gmail priority seed before enabling decision context"
            )
        if priority.get("decision_context_enabled") is not True:
            priority["decision_context_enabled"] = True
            changed = True
    inbound_binding_requested = any(
        (
            args.gmail_gate_thread,
            args.gmail_processor_thread,
            args.gmail_poll_automation,
        )
    )
    if inbound_binding_requested:
        if not gmail.get("enabled") or not gmail.get("reply_message_id"):
            raise SupervisionLogError(
                "Bind the monitored project's Gmail seed before inbound processing"
            )
        if gmail.get("inbound_enabled") is not True:
            gmail["inbound_enabled"] = True
            changed = True
        if policy["permissions"].get("gmail_inbound_processing") is not True:
            policy["permissions"]["gmail_inbound_processing"] = True
            changed = True
        schedule = policy.setdefault("schedule", {})
        gmail_schedule_defaults = {
            "gmail_poll_minutes": 2,
            "gmail_quiet_poll_minutes": 2,
            "gmail_active_poll_minutes": 1,
            "gmail_active_window_minutes": 30,
        }
        for key, value in gmail_schedule_defaults.items():
            if schedule.get(key) != value:
                schedule[key] = value
                changed = True
    roundup = policy.setdefault("notifications", {}).setdefault(
        "gmail_roundup",
        {
            "enabled": False,
            "recipient": "me",
            "thread_scope": "monitored-project-roundup",
            "project_key": None,
            "reply_message_id": None,
            "subject": None,
            "delivery_policy": "scheduled-pacific-operational-change-log",
        },
    )
    if args.gmail_roundup_reply_message_id:
        roundup_message_id = safe_id(
            args.gmail_roundup_reply_message_id,
            label="Gmail roundup reply message ID",
        )
        roundup_project_key = safe_id(
            args.gmail_roundup_project_key
            or gmail.get("project_key")
            or policy["target_label"],
            label="Gmail roundup monitored project key",
        )
        roundup_subject = clean(
            args.gmail_roundup_subject
            or f"Codex Tracker Roundup - {roundup_project_key}",
            label="Gmail roundup subject",
            maximum=160,
        )
        if roundup.get("reply_message_id") not in (None, roundup_message_id):
            raise SupervisionLogError("Gmail roundup reply binding already differs")
        if roundup.get("subject") not in (None, roundup_subject):
            raise SupervisionLogError("Gmail roundup subject binding already differs")
        desired_roundup = {
            "enabled": True,
            "recipient": "me",
            "thread_scope": "monitored-project-roundup",
            "project_key": roundup_project_key,
            "reply_message_id": roundup_message_id,
            "subject": roundup_subject,
            "delivery_policy": "scheduled-pacific-operational-change-log",
        }
        for key, value in desired_roundup.items():
            if roundup.get(key) != value:
                roundup[key] = value
                changed = True
        if policy["permissions"].get("gmail_roundup_notification") is not True:
            policy["permissions"]["gmail_roundup_notification"] = True
            changed = True
    roundup_binding_requested = any((args.roundup_thread, args.roundup_automation))
    if roundup_binding_requested:
        if not roundup.get("enabled") or not roundup.get("reply_message_id"):
            raise SupervisionLogError(
                "Bind the monitored project's Gmail roundup seed before its runtime"
            )
        schedule = policy.setdefault("schedule", {})
        if "roundup_hours" in schedule:
            del schedule["roundup_hours"]
            changed = True
        roundup_schedule = {
            "roundup_timezone": "America/Los_Angeles",
            "roundup_local_times": ["07:00", "13:00", "17:00", "23:00"],
        }
        for key, value in roundup_schedule.items():
            if schedule.get(key) != value:
                schedule[key] = value
                changed = True
        if roundup.get("delivery_policy") != "scheduled-pacific-operational-change-log":
            roundup["delivery_policy"] = "scheduled-pacific-operational-change-log"
            changed = True
    routing = policy.setdefault("routing", {})
    legacy_denominator = routing.pop("sol_sample_denominator", None)
    if legacy_denominator is not None:
        routing.setdefault("max_sample_denominator", legacy_denominator)
        changed = True
    if "max_sample_denominator" not in routing:
        routing["max_sample_denominator"] = 6
        changed = True
    if routing.get("xhigh_every_changed_state") is not True:
        routing["xhigh_every_changed_state"] = True
        changed = True
    if routing.get("sample_records_complete_gate") is not False:
        routing["sample_records_complete_gate"] = False
        changed = True
    if changed:
        write_policy_version(
            directory,
            policy,
            kind="policy-bind",
            reason="Bound live identifiers and current routing defaults.",
            evidence_values=[],
        )
    print(json.dumps({"changed": changed, "policy": policy}, sort_keys=True))


def cmd_thread_route_gate(args: argparse.Namespace) -> None:
    _, policy = load_policy(args)
    routing = policy.get("cross_thread_routing")
    if routing != cross_thread_routing_contract():
        raise SupervisionLogError(
            "Current cross-thread routing contract is not bound; run bind first"
        )

    recipient = safe_id(args.recipient_thread, label="recipient thread ID")
    source_record = safe_id(args.source_record, label="source record ID")
    action = clean(args.action, label="required action", maximum=240)
    if not action:
        raise SupervisionLogError("Cross-thread routing requires an exact action")

    role_threads: dict[str, str] = {"target": policy["target_thread_id"]}
    runtime = policy.get("runtime", {})
    for role, field in THREAD_ROUTE_ROLE_FIELDS.items():
        value = runtime.get(field)
        if value:
            role_threads[role] = value

    matched_roles = sorted(
        role for role, thread_id in role_threads.items() if thread_id == recipient
    )
    if not matched_roles:
        raise SupervisionLogError(
            "Cross-thread recipient is not a configured action owner"
        )
    if len(matched_roles) != 1:
        raise SupervisionLogError(
            "Cross-thread recipient has ambiguous configured roles"
        )
    recipient_role = matched_roles[0]
    allowed_roles = THREAD_ROUTE_PURPOSE_ROLES.get(args.purpose)
    if allowed_roles is None:
        raise SupervisionLogError("Unsupported cross-thread routing purpose")
    if recipient_role not in allowed_roles:
        raise SupervisionLogError(
            "Cross-thread purpose does not match the configured recipient role"
        )

    print(
        json.dumps(
            {
                "send_allowed": True,
                "target_thread_id": policy["target_thread_id"],
                "recipient_thread_id": recipient,
                "recipient_role": recipient_role,
                "purpose": args.purpose,
                "source_record": source_record,
                "action_sha256": digest(action),
                "policy_sha256": policy["policy_sha256"],
            },
            sort_keys=True,
        )
    )


def is_completion_check(item: dict[str, Any]) -> bool:
    if item.get("kind") != "check":
        return False
    if item.get("category") in NON_COMPLETION_CHECK_CATEGORIES:
        return False
    # Older policy versions may already contain a Sol Max sample logged as a
    # generic check. Preserve that evidence while preventing a late review of
    # an older fingerprint from moving the live change-gate watermark backward.
    return not (
        item.get("model") == "gpt-5.6-sol" and item.get("reasoning") == "max"
    )


def last_check(all_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in reversed(all_events) if is_completion_check(item)), None)


def gate_fingerprint(args: argparse.Namespace) -> str:
    if args.state_fingerprint:
        return safe_id(args.state_fingerprint, label="state fingerprint")
    material = {
        "target_thread_id": args.target_thread,
        "thread_updated_at": clean(
            args.thread_updated_at, label="thread updated at", maximum=80
        ),
        "thread_status": clean(args.thread_status, label="thread status", maximum=40),
        "active_block": clean(args.active_block, label="active block", maximum=40),
        "latest_item": clean(args.latest_item, label="latest item", maximum=128),
        "checkpoint": clean(args.checkpoint, label="checkpoint", maximum=160),
    }
    if not any(value for key, value in material.items() if key != "target_thread_id"):
        raise SupervisionLogError(
            "Gate requires a state fingerprint or at least one bounded state marker"
        )
    return digest(material)


def cmd_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    fingerprint = gate_fingerprint(args)
    prior = last_check(events(directory / "events.jsonl"))
    changed = prior is None or prior.get("state_fingerprint") != fingerprint
    routing = policy["routing"]
    denominator = int(
        routing.get(
            "max_sample_denominator", routing.get("sol_sample_denominator", 6)
        )
    )
    bucket = int(hashlib.sha256(f"{args.target_thread}:{fingerprint}".encode()).hexdigest()[:16], 16) % denominator
    print(
        json.dumps(
            {
                "changed": changed,
                "state_fingerprint": fingerprint,
                "xhigh_review": changed,
                "max_sample": changed and bucket == 0,
                "sol_sample": changed,
                "sample_bucket": bucket,
                "sample_denominator": denominator,
                "prior_state_fingerprint": prior.get("state_fingerprint") if prior else None,
                "policy_sha256": policy["policy_sha256"],
            },
            sort_keys=True,
        )
    )


def incident_id(args: argparse.Namespace, record: dict[str, Any]) -> str:
    if args.incident_id:
        return safe_id(args.incident_id, label="incident ID")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = digest({"stamp": stamp, "record": record})[:6].upper()
    return f"INC-{stamp}-{suffix}"


def cmd_record(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    if args.kind not in KINDS:
        raise SupervisionLogError("Unsupported event kind")
    evidence_values = [clean(item, label="evidence", maximum=160) for item in args.evidence]
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many evidence references")
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "",
        "timestamp": utc_now(),
        "target_thread_id": args.target_thread,
        "kind": args.kind,
        "model": clean(args.model, label="model", maximum=80),
        "reasoning": clean(args.reasoning, label="reasoning", maximum=20),
        "state_fingerprint": clean(
            args.state_fingerprint, label="state fingerprint", maximum=128
        ),
        "status": clean(args.status, label="status", maximum=80),
        "severity": args.severity,
        "category": clean(args.category, label="category", maximum=80),
        "active_block": clean(args.active_block, label="active block", maximum=40),
        "checkpoint": clean(args.checkpoint, label="checkpoint", maximum=160),
        "summary": clean(args.summary, label="summary"),
        "evidence": evidence_values,
        "estimated_risk": clean(args.estimated_risk, label="estimated risk", maximum=300),
        "action": clean(args.action, label="action"),
        "resolution": clean(args.resolution, label="resolution"),
        "notice_disposition": args.notice_disposition,
        "resolution_owner": args.resolution_owner,
        "user_action_required": args.user_action_required,
        "dedup_key": clean(args.dedup_key, label="dedup key", maximum=160),
        "policy_sha256": policy["policy_sha256"],
    }
    if args.severity not in SEVERITIES:
        raise SupervisionLogError("Unsupported severity")
    with append_lock(directory):
        current_events = events(directory / "events.jsonl")
        if args.kind in {"lifecycle", "incident", "notification", "inbound-message"} and record["dedup_key"]:
            duplicate = next(
                (
                    item
                    for item in reversed(current_events)
                    if item.get("kind") == args.kind
                    and item.get("dedup_key") == record["dedup_key"]
                    and item.get("state_fingerprint") == record["state_fingerprint"]
                    and (
                        args.kind != "notification"
                        or (
                            item.get("status") == "sent"
                            and record["status"] == "sent"
                        )
                    )
                ),
                None,
            )
            if duplicate:
                print(
                    json.dumps(
                        {
                            "duplicate": True,
                            "incident_id": duplicate.get("incident_id"),
                            "record_id": duplicate.get("record_id"),
                        },
                        sort_keys=True,
                    )
                )
                return
        if args.kind == "incident" or args.incident_id:
            record["incident_id"] = incident_id(args, record)
        sequence = len(current_events) + 1
        record["record_id"] = f"EVT-{sequence:06d}"

        incident_path: Path | None = None
        if args.kind == "incident":
            incident_path = directory / "incidents" / f"{record['incident_id']}.md"
            if incident_path.exists():
                raise SupervisionLogError(
                    f"Material report already exists: {incident_path.name}"
                )
        elif args.incident_id:
            incident_path = directory / "incidents" / f"{record['incident_id']}.md"
            if not incident_path.exists():
                raise SupervisionLogError("Referenced incident report does not exist")

        review_path: Path | None = None
        review_record: dict[str, Any] | None = None
        if args.kind in {"checkpoint-review", "meta-review"}:
            review_id = (
                safe_id(args.review_id, label="review ID")
                if args.review_id
                else f"REVIEW-{record['record_id']}"
            )
            review_path = directory / "reviews" / f"{review_id}.md"
            if review_path.exists():
                raise SupervisionLogError(
                    f"Material report already exists: {review_path.name}"
                )
            review_record = dict(record)
            review_record["incident_id"] = review_id

        append_raw_locked(directory / "events.jsonl", record)
        if incident_path is not None:
            append_markdown(incident_path, record, create=args.kind == "incident")
        if review_path is not None and review_record is not None:
            append_markdown(review_path, review_record, create=True)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def notification_matches_incident(
    item: dict[str, Any],
    current_incident_id: str,
    incident_source_record_ids: set[str],
) -> bool:
    if item.get("kind") != "notification":
        return False
    if item.get("incident_id") == current_incident_id:
        return True
    if item.get("status") != "sent" or item.get("category") != "gmail":
        return False
    evidence = item.get("evidence", [])
    if not isinstance(evidence, list):
        return False
    return any(
        isinstance(reference, str) and reference in incident_source_record_ids
        for reference in evidence
    )


def cmd_notice_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    current_incident_id = safe_id(args.incident_id, label="incident ID")
    source_record = safe_id(args.source_record, label="source record ID")
    if not (directory / "incidents" / f"{current_incident_id}.md").exists():
        raise SupervisionLogError("Referenced incident report does not exist")

    all_events = events(directory / "events.jsonl")
    incident_source_record_ids = {
        item["record_id"]
        for item in all_events
        if item.get("incident_id") == current_incident_id
        and isinstance(item.get("record_id"), str)
    }
    incident_notifications = [
        item
        for item in all_events
        if notification_matches_incident(
            item, current_incident_id, incident_source_record_ids
        )
    ]
    duplicate = any(
        source_record in item.get("evidence", [])
        or item.get("dedup_key") == f"gmail:{source_record}"
        for item in incident_notifications
    )
    previously_alerted = bool(incident_notifications)
    user_action_required = args.user_action_required == "yes"

    if duplicate:
        send_now = False
        channel = "none"
        reason = "An outcome for this source record is already in the outbound ledger."
        banner = None
    elif args.notice_disposition == "terminal":
        send_now = previously_alerted
        channel = "primary-outcome" if send_now else "digest"
        reason = (
            "Send one nonurgent terminal outcome because this incident was previously alerted."
            if send_now
            else "No prior incident alert requires a standalone terminal email."
        )
        banner = "SUPERVISION OUTCOME" if send_now else None
    elif (
        args.severity == "critical"
        or user_action_required
        or args.notice_disposition in IMMEDIATE_NOTICE_DISPOSITIONS
    ):
        send_now = True
        channel = "primary-immediate"
        reason = "The incident requires immediate operator awareness or action."
        banner = (
            "🚨 CRITICAL SUPERVISION ALERT 🚨"
            if args.severity == "critical"
            or args.notice_disposition == "critical"
            else "⚠️ IMPORTANT SUPERVISION NOTICE"
        )
    else:
        send_now = False
        channel = "digest"
        reason = (
            "Automatic resolution or observation remains active without a user decision; "
            "keep intermediate progress out of the Important channel."
        )
        banner = None

    print(
        json.dumps(
            {
                "banner": banner,
                "channel": channel,
                "duplicate": duplicate,
                "follow_up_required": args.notice_disposition != "terminal",
                "incident_id": current_incident_id,
                "notice_disposition": args.notice_disposition,
                "policy_sha256": policy["policy_sha256"],
                "previously_alerted": previously_alerted,
                "reason": reason,
                "resolution_owner": args.resolution_owner,
                "send_now": send_now,
                "source_record": source_record,
                "user_action_required": user_action_required,
            },
            sort_keys=True,
        )
    )


def cmd_lifecycle_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    source_record = safe_id(args.source_record, label="source record ID")
    lifecycle_state = args.lifecycle_state
    state_fingerprint = clean(
        args.state_fingerprint, label="state fingerprint", maximum=128
    )
    all_events = events(directory / "events.jsonl")
    source = next(
        (item for item in all_events if item.get("record_id") == source_record),
        None,
    )
    if source is None:
        raise SupervisionLogError("Lifecycle source record does not exist")
    if source.get("kind") != "lifecycle" or source.get("status") != lifecycle_state:
        raise SupervisionLogError("Lifecycle source record does not match requested state")
    if state_fingerprint and source.get("state_fingerprint") != state_fingerprint:
        raise SupervisionLogError("Lifecycle source record fingerprint differs")

    priority_lifecycle = lifecycle_state in PRIORITY_LIFECYCLE_STATES
    category = "gmail-priority-lifecycle" if priority_lifecycle else "gmail-lifecycle"
    notification_key = f"{category}:{source_record}"
    duplicate = any(
        item.get("kind") == "notification"
        and item.get("category") == category
        and (
            source_record in item.get("evidence", [])
            or item.get("dedup_key") == notification_key
        )
        for item in all_events
    )
    notification_config = policy.get("notifications", {}).get(
        "gmail_priority" if priority_lifecycle else "gmail", {}
    )
    enabled = bool(notification_config.get("enabled"))
    user_action_required = source.get("user_action_required") == "yes"
    decision_context_required = bool(
        priority_lifecycle
        and user_action_required
        and notification_config.get("decision_context_enabled")
    )
    send_now = enabled and not duplicate
    if duplicate:
        reason = "This lifecycle transition is already in the outbound ledger."
    elif not enabled and priority_lifecycle:
        reason = (
            "Dedicated priority lifecycle delivery is not bound for this target; "
            "do not substitute the primary or roundup thread."
        )
    elif not enabled:
        reason = "Gmail lifecycle delivery is not enabled for this target."
    else:
        reason = "The implementation lifecycle changed and requires one status email."
    print(
        json.dumps(
            {
                "banner": notification_config.get("banner") if send_now else None,
                "channel": (
                    "priority-lifecycle"
                    if send_now and priority_lifecycle
                    else "primary-status" if send_now else "none"
                ),
                "duplicate": duplicate,
                "decision_context_required": decision_context_required,
                "required_decision_fields": (
                    notification_config.get("required_decision_fields", [])
                    if decision_context_required
                    else []
                ),
                "lifecycle_state": lifecycle_state,
                "notification_category": category,
                "notification_dedup_key": notification_key,
                "policy_sha256": policy["policy_sha256"],
                "reason": reason,
                "reply_message_id": (
                    notification_config.get("reply_message_id") if send_now else None
                ),
                "send_now": send_now,
                "source_record": source_record,
                "state_fingerprint": source.get("state_fingerprint", ""),
            },
            sort_keys=True,
        )
    )


def decision_events(
    all_events: list[dict[str, Any]], decision_id: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in all_events
        if item.get("kind") == "decision" and item.get("decision_id") == decision_id
    ]


def validate_decision_transition(
    prior: dict[str, Any] | None,
    *,
    classification: str,
    phase: str,
    attempt: int,
    outcome: str,
) -> None:
    if phase not in {"resolved", "safe-deferred", "handoff-sent", "target-acknowledged"} and outcome:
        raise SupervisionLogError("Only a disposition or handoff may carry an outcome")
    if prior is None:
        if phase != "decision-ready" or attempt != 0 or outcome:
            raise SupervisionLogError(
                "A decision must begin decision-ready with attempt zero and no outcome"
            )
        return
    if prior.get("classification") != classification:
        raise SupervisionLogError("Decision classification cannot change")
    prior_phase = prior.get("phase")
    prior_attempt = int(prior.get("attempt", 0))
    transitions = {
        "decision-ready": {
            "user-responded",
            "attempt-started",
            "resolved",
            "safe-deferred",
        },
        "user-responded": {"resolved", "safe-deferred"},
        "attempt-started": {
            "attempt-unresolved",
            "user-responded",
            "resolved",
            "safe-deferred",
        },
        "attempt-unresolved": {
            "attempt-started",
            "user-responded",
            "resolved",
            "safe-deferred",
        },
        "resolved": {"handoff-sent"},
        "safe-deferred": {"handoff-sent"},
        "handoff-sent": {"target-acknowledged"},
        "target-acknowledged": set(),
    }
    if phase not in transitions.get(str(prior_phase), set()):
        raise SupervisionLogError(
            f"Decision transition {prior_phase!s} -> {phase!s} is not allowed"
        )
    if phase == "attempt-started":
        if classification == "delegable":
            raise SupervisionLogError("A delegable decision must resolve immediately")
        if attempt != prior_attempt + 1:
            raise SupervisionLogError("Decision attempts must be continuous")
    elif attempt != prior_attempt:
        raise SupervisionLogError("Only attempt-started may increment the attempt")
    if phase == "attempt-unresolved" and prior_phase != "attempt-started":
        raise SupervisionLogError("Only an active attempt may become unresolved")
    if phase == "resolved" and outcome not in {"selected", "user-supplied"}:
        raise SupervisionLogError("Resolved decisions require a selected outcome")
    if phase == "safe-deferred" and outcome != "safe-deferred":
        raise SupervisionLogError("Safe deferral requires the safe-deferred outcome")
    if phase == "safe-deferred":
        if classification == "delegable":
            raise SupervisionLogError("A delegable decision cannot be safely deferred")
        if classification == "human-preference" and prior_phase != "user-responded":
            raise SupervisionLogError(
                "An unresolved human preference must be selected after bounded attempts"
            )
    if phase == "resolved":
        if classification in {"missing-fact", "reserved-authority"}:
            if prior_phase != "user-responded" or outcome != "user-supplied":
                raise SupervisionLogError(
                    "A missing fact or reserved authority can resolve only from user input"
                )
        elif prior_phase == "user-responded" and outcome != "user-supplied":
            raise SupervisionLogError("A user response requires the user-supplied outcome")
        elif prior_phase != "user-responded" and outcome != "selected":
            raise SupervisionLogError("Automatic resolution requires the selected outcome")
    if phase in {"handoff-sent", "target-acknowledged"}:
        if outcome != prior.get("outcome"):
            raise SupervisionLogError("Handoff must preserve the exact decision outcome")


def cmd_decision_record(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    decision_id = safe_id(args.decision_id, label="decision ID")
    classification = args.classification
    phase = args.phase
    safe_frontier = args.safe_frontier
    outcome = args.outcome
    attempt = int(args.attempt)
    contract = policy["decision_resolution"]
    if attempt < 0 or attempt > int(contract["max_attempts"]):
        raise SupervisionLogError("Decision attempt is outside the maintained bound")
    evidence_values = [
        clean(item, label="evidence", maximum=160) for item in args.evidence
    ]
    if not evidence_values or not all(evidence_values):
        raise SupervisionLogError("Decision records require nonempty exact evidence")
    if len(evidence_values) > 12:
        raise SupervisionLogError("Too many decision evidence references")
    exact_hashes = {
        "decision packet hash": args.decision_packet_hash,
        "blocked scope hash": args.blocked_scope_hash,
        "safe frontier hash": args.safe_frontier_hash,
    }
    for label, value in exact_hashes.items():
        if not clean(value, label=label, maximum=128):
            raise SupervisionLogError(f"{label.title()} is required")
    now = parse_time(args.now)
    with append_lock(directory):
        all_events = events(directory / "events.jsonl")
        prior_records = decision_events(all_events, decision_id)
        prior = prior_records[-1] if prior_records else None
        if (
            prior is not None
            and prior.get("classification") == classification
            and prior.get("phase") == phase
            and prior.get("safe_frontier") == safe_frontier
            and int(prior.get("attempt", 0)) == attempt
            and prior.get("outcome", "") == outcome
            and prior.get("state_fingerprint", "")
            == clean(
                args.state_fingerprint,
                label="state fingerprint",
                maximum=128,
            )
            and prior.get("decision_packet_hash") == args.decision_packet_hash
            and prior.get("blocked_scope_hash") == args.blocked_scope_hash
            and prior.get("safe_frontier_hash") == args.safe_frontier_hash
            and prior.get("evidence") == evidence_values
        ):
            print(
                json.dumps(
                    {"duplicate": True, "record_id": prior["record_id"]},
                    sort_keys=True,
                )
            )
            return
        validate_decision_transition(
            prior,
            classification=classification,
            phase=phase,
            attempt=attempt,
            outcome=outcome,
        )
        if prior is not None:
            prior_phase = str(prior.get("phase", ""))
            prior_attempt = int(prior.get("attempt", 0))
            automatic_resolution = phase == "resolved" and outcome == "selected"
            if (
                automatic_resolution
                and classification != "delegable"
                and prior_phase == "decision-ready"
            ):
                raise SupervisionLogError(
                    "A non-delegable decision must record its first resolution attempt"
                )
            if automatic_resolution and prior_phase == "attempt-started":
                if now > parse_time(str(prior.get("deadline_at", ""))):
                    raise SupervisionLogError(
                        "An expired resolution attempt must be recorded unresolved"
                    )
            if automatic_resolution and prior_phase == "attempt-unresolved":
                user_deadline_at = str(prior.get("user_deadline_at", ""))
                if (
                    prior_attempt < int(contract["max_attempts"])
                    or not user_deadline_at
                    or now < parse_time(user_deadline_at)
                ):
                    raise SupervisionLogError(
                        "Automatic final selection requires all attempts and the user window"
                    )
            if phase == "safe-deferred" and prior_phase != "user-responded":
                user_deadline_at = str(prior.get("user_deadline_at", ""))
                if (
                    prior_phase != "attempt-unresolved"
                    or prior_attempt < int(contract["max_attempts"])
                    or not user_deadline_at
                    or now < parse_time(user_deadline_at)
                ):
                    raise SupervisionLogError(
                        "Automatic safe deferral requires all attempts and the user window"
                    )
        if phase == "decision-ready":
            decision_ready_at = iso_time(now)
            deadline_at = ""
            human_input_requested_at = ""
            user_deadline_at = ""
        elif phase == "attempt-started":
            decision_ready_at = str(prior["decision_ready_at"])
            deadline_at = iso_time(
                now + dt.timedelta(minutes=int(contract["attempt_minutes"]))
            )
            human_input_requested_at = str(
                prior.get("human_input_requested_at", "")
            )
            user_deadline_at = str(prior.get("user_deadline_at", ""))
        else:
            decision_ready_at = str(prior["decision_ready_at"])
            deadline_at = ""
            human_input_requested_at = str(
                prior.get("human_input_requested_at", "")
            )
            user_deadline_at = str(prior.get("user_deadline_at", ""))
            if phase == "attempt-unresolved" and not user_deadline_at:
                human_input_requested_at = iso_time(now)
                user_deadline_at = iso_time(
                    now
                    + dt.timedelta(minutes=int(contract["human_response_minutes"]))
                )
        record: dict[str, Any] = {
            "schema_version": 1,
            "record_id": f"EVT-{len(all_events) + 1:06d}",
            "timestamp": iso_time(now),
            "target_thread_id": args.target_thread,
            "kind": "decision",
            "decision_id": decision_id,
            "classification": classification,
            "phase": phase,
            "safe_frontier": safe_frontier,
            "attempt": attempt,
            "outcome": outcome,
            "decision_ready_at": decision_ready_at,
            "deadline_at": deadline_at,
            "human_input_requested_at": human_input_requested_at,
            "user_deadline_at": user_deadline_at,
            "decision_packet_hash": clean(
                args.decision_packet_hash,
                label="decision packet hash",
                maximum=128,
            ),
            "blocked_scope_hash": clean(
                args.blocked_scope_hash,
                label="blocked scope hash",
                maximum=128,
            ),
            "safe_frontier_hash": clean(
                args.safe_frontier_hash,
                label="safe frontier hash",
                maximum=128,
            ),
            "state_fingerprint": clean(
                args.state_fingerprint,
                label="state fingerprint",
                maximum=128,
            ),
            "evidence": evidence_values,
            "policy_sha256": policy["policy_sha256"],
        }
        append_raw_locked(directory / "events.jsonl", record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def decision_notification(
    policy: dict[str, Any],
    all_events: list[dict[str, Any]],
    head: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    phase = ""
    if head["classification"] == "delegable":
        phase = ""
    elif head["phase"] == "attempt-unresolved" and int(head["attempt"]) == 1:
        phase = "human-input-requested"
    elif (
        head["phase"] in {"resolved", "safe-deferred"}
        and head.get("human_input_requested_at")
    ):
        phase = "final-disposition"
    elif head["phase"] == "target-acknowledged" and head.get(
        "human_input_requested_at"
    ):
        phase = "target-resumed"
    source_record = str(head["record_id"])
    category = "gmail-priority-decision"
    dedup_key = f"{category}:{source_record}:{phase}"
    duplicate = any(
        item.get("kind") == "notification"
        and item.get("category") == category
        and item.get("status") == "sent"
        and (
            item.get("dedup_key") == dedup_key
            or source_record in item.get("evidence", [])
        )
        for item in all_events
    )
    priority = policy.get("notifications", {}).get("gmail_priority", {})
    decision_context_enabled = priority.get("decision_context_enabled") is True
    send_now = bool(
        phase
        and priority.get("enabled")
        and decision_context_enabled
        and not duplicate
    )
    banners = {
        "human-input-requested": "🚨 HUMAN INPUT REQUESTED — RESOLUTION CONTINUES 🚨",
        "final-disposition": "SUPERVISION DECISION OUTCOME",
        "target-resumed": "IMPLEMENTATION RESUMED",
    }
    return {
        "notification_phase": phase,
        "notification_send_now": send_now,
        "notification_duplicate": duplicate,
        "notification_banner": banners.get(phase) if send_now else None,
        "notification_category": category if send_now else None,
        "notification_dedup_key": dedup_key if send_now else None,
        "notification_reply_message_id": (
            priority.get("reply_message_id") if send_now else None
        ),
        "notification_action": action,
        "required_decision_fields": (
            priority.get("required_decision_fields", [])
            if send_now and phase == "human-input-requested"
            else []
        ),
    }


def cmd_decision_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    decision_id = safe_id(args.decision_id, label="decision ID")
    all_events = events(directory / "events.jsonl")
    records = decision_events(all_events, decision_id)
    if not records:
        raise SupervisionLogError("Decision does not exist")
    head = records[-1]
    now = parse_time(args.now)
    phase = str(head["phase"])
    classification = str(head["classification"])
    attempt = int(head.get("attempt", 0))
    safe_work = head.get("safe_frontier") == "nonempty"
    contract = policy["decision_resolution"]
    if phase == "decision-ready":
        if classification == "delegable":
            action = "resolve-immediately-and-continue"
        else:
            action = "start-sol-max-attempt"
    elif phase == "attempt-started":
        deadline = parse_time(str(head["deadline_at"]))
        action = (
            "continue-sol-max-attempt-and-safe-frontier"
            if now < deadline
            else "record-attempt-unresolved"
        )
    elif phase == "attempt-unresolved":
        if attempt < int(contract["max_attempts"]):
            action = "start-sol-max-attempt"
        elif head.get("user_deadline_at") and now < parse_time(
            str(head["user_deadline_at"])
        ):
            action = "await-user-and-continue-safe-frontier"
        elif classification in {"delegable", "human-preference"}:
            action = "choose-and-handoff"
        else:
            action = "safe-defer-and-handoff"
    elif phase == "user-responded":
        action = "resolve-user-response-and-handoff"
    elif phase in {"resolved", "safe-deferred"}:
        action = "send-exact-handoff"
    elif phase == "handoff-sent":
        action = "await-target-evidence-and-continue-safe-frontier"
    else:
        action = "closed"
    next_attempt = attempt + 1 if action == "start-sol-max-attempt" else attempt
    blocking_permitted = bool(
        phase in {"handoff-sent", "target-acknowledged"}
        and head.get("outcome") == "safe-deferred"
        and not safe_work
        and classification in {"missing-fact", "reserved-authority"}
    )
    result = {
        "decision_id": decision_id,
        "source_record": head["record_id"],
        "classification": classification,
        "phase": phase,
        "attempt": attempt,
        "next_attempt": next_attempt,
        "action": action,
        "must_continue_safe_frontier": safe_work,
        "safe_frontier": head["safe_frontier"],
        "blocking_permitted": blocking_permitted,
        "required_target_posture": (
            "blocked" if blocking_permitted else "in-progress"
        ),
        "manual_resume_required": False,
        "attempt_model": contract["attempt_model"],
        "attempt_reasoning": contract["attempt_reasoning"],
        "attempt_minutes": contract["attempt_minutes"],
        "max_attempts": contract["max_attempts"],
        "deadline_at": head.get("deadline_at", ""),
        "human_input_requested_at": head.get("human_input_requested_at", ""),
        "user_deadline_at": head.get("user_deadline_at", ""),
        "policy_sha256": policy["policy_sha256"],
    }
    result.update(decision_notification(policy, all_events, head, action))
    print(json.dumps(result, sort_keys=True))


def cmd_adjust(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    reason = clean(args.reason, label="reason")
    if not reason:
        raise SupervisionLogError("A bounded policy adjustment requires a reason")
    evidence_values = [clean(item, label="evidence", maximum=160) for item in args.evidence]
    requested = {
        "routine_minutes": args.routine_minutes,
        "meta_review_hours": args.meta_review_hours,
        "max_sample_denominator": args.max_sample_denominator,
        "cooldown_minutes": args.cooldown_minutes,
        "max_escalations_per_hour": args.max_escalations_per_hour,
        "gmail_quiet_minutes": args.gmail_quiet_minutes,
        "gmail_active_minutes": args.gmail_active_minutes,
        "gmail_active_window_minutes": args.gmail_active_window_minutes,
        "skill_maintenance_mode": args.skill_maintenance_mode,
    }
    changed = False
    if requested["routine_minutes"] is not None:
        value = int(requested["routine_minutes"])
        if not 15 <= value <= 60:
            raise SupervisionLogError("Routine minutes must be between 15 and 60")
        policy["schedule"]["routine_minutes"] = value
        changed = True
    if requested["meta_review_hours"] is not None:
        value = int(requested["meta_review_hours"])
        if not 2 <= value <= 24:
            raise SupervisionLogError("Meta-review hours must be between 2 and 24")
        policy["schedule"]["meta_review_hours"] = value
        changed = True
    if requested["max_sample_denominator"] is not None:
        value = int(requested["max_sample_denominator"])
        if not 4 <= value <= 10:
            raise SupervisionLogError("Max sample denominator must be between 4 and 10")
        policy["routing"]["max_sample_denominator"] = value
        changed = True
    if requested["cooldown_minutes"] is not None:
        value = int(requested["cooldown_minutes"])
        if not 30 <= value <= 120:
            raise SupervisionLogError("Cooldown must be between 30 and 120 minutes")
        policy["routing"]["escalation_cooldown_minutes"] = value
        changed = True
    if requested["max_escalations_per_hour"] is not None:
        value = int(requested["max_escalations_per_hour"])
        if not 1 <= value <= 2:
            raise SupervisionLogError("Escalations per hour must be one or two")
        policy["routing"]["max_escalations_per_hour"] = value
        changed = True
    schedule = policy.setdefault("schedule", {})
    quiet_minutes = int(
        requested["gmail_quiet_minutes"]
        if requested["gmail_quiet_minutes"] is not None
        else schedule.get("gmail_quiet_poll_minutes", 2)
    )
    active_minutes = int(
        requested["gmail_active_minutes"]
        if requested["gmail_active_minutes"] is not None
        else schedule.get("gmail_active_poll_minutes", 1)
    )
    active_window_minutes = int(
        requested["gmail_active_window_minutes"]
        if requested["gmail_active_window_minutes"] is not None
        else schedule.get("gmail_active_window_minutes", 30)
    )
    if not 2 <= quiet_minutes <= 10:
        raise SupervisionLogError("Gmail quiet cadence must be between 2 and 10 minutes")
    if not 1 <= active_minutes < quiet_minutes:
        raise SupervisionLogError(
            "Gmail active cadence must be at least one minute and faster than quiet cadence"
        )
    if not 5 <= active_window_minutes <= 120:
        raise SupervisionLogError(
            "Gmail active window must be between 5 and 120 minutes"
        )
    if any(
        requested[key] is not None
        for key in (
            "gmail_quiet_minutes",
            "gmail_active_minutes",
            "gmail_active_window_minutes",
        )
    ):
        schedule["gmail_poll_minutes"] = quiet_minutes
        schedule["gmail_quiet_poll_minutes"] = quiet_minutes
        schedule["gmail_active_poll_minutes"] = active_minutes
        schedule["gmail_active_window_minutes"] = active_window_minutes
        changed = True
    if requested["skill_maintenance_mode"] is not None:
        if not any(evidence_values):
            raise SupervisionLogError(
                "A skill-maintenance mode change requires operator or review evidence"
            )
        mode = requested["skill_maintenance_mode"]
        policy["skill_maintenance"] = skill_maintenance_contract(mode)
        policy["execution_economy"] = execution_economy_contract()
        policy.setdefault("permissions", {})["allowlisted_skill_maintenance"] = (
            mode == "apply-allowlisted-skill-maintenance-with-review"
        )
        changed = True
    if not changed:
        raise SupervisionLogError("No bounded policy field was supplied")
    write_policy_version(
        directory,
        policy,
        kind="policy-adjust",
        reason=reason,
        evidence_values=evidence_values,
    )
    print(json.dumps({"changed": True, "policy": policy}, sort_keys=True))


def gmail_message_id(value: str) -> str:
    result = safe_id(value, label="Gmail message ID")
    if not re.fullmatch(r"[0-9A-Fa-f]{12,64}", result):
        raise SupervisionLogError("Gmail message ID must be hexadecimal")
    return result.lower()


def cmd_gmail_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    gmail = policy.get("notifications", {}).get("gmail", {})
    if gmail.get("enabled") is not True or gmail.get("inbound_enabled") is not True:
        raise SupervisionLogError("Gmail inbound processing is not enabled")
    supplied = [gmail_message_id(item) for item in args.message_id]
    known: set[str] = set()
    seed = gmail.get("reply_message_id")
    if isinstance(seed, str) and seed:
        known.add(gmail_message_id(seed))
    for item in events(directory / "events.jsonl"):
        if item.get("kind") not in {"notification", "inbound-message"}:
            continue
        for evidence in item.get("evidence", []):
            if not isinstance(evidence, str):
                continue
            known.update(
                match.lower()
                for match in re.findall(
                    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{12,64}(?![0-9A-Fa-f])",
                    evidence,
                )
            )
    print(
        json.dumps(
            {
                "pending_message_ids": [item for item in supplied if item not in known],
                "known_message_ids": [item for item in supplied if item in known],
            },
            sort_keys=True,
        )
    )


def parse_event_time(value: Any, *, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise SupervisionLogError(f"{label} is missing")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupervisionLogError(f"{label} is malformed") from exc
    if parsed.tzinfo is None:
        raise SupervisionLogError(f"{label} must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def is_gmail_conversation_activity(item: dict[str, Any]) -> bool:
    if item.get("kind") == "inbound-message" and item.get("category") == "gmail":
        return True
    return (
        item.get("kind") == "notification"
        and item.get("category") in GMAIL_CONVERSATION_NOTIFICATION_CATEGORIES
        and item.get("status") == "sent"
    )


def cmd_gmail_cadence(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    gmail = policy.get("notifications", {}).get("gmail", {})
    if gmail.get("enabled") is not True or gmail.get("inbound_enabled") is not True:
        raise SupervisionLogError("Gmail inbound processing is not enabled")
    schedule = policy.get("schedule", {})
    quiet_minutes = int(
        schedule.get("gmail_quiet_poll_minutes", schedule.get("gmail_poll_minutes", 2))
    )
    active_minutes = int(schedule.get("gmail_active_poll_minutes", 1))
    window_minutes = int(schedule.get("gmail_active_window_minutes", 30))
    if not 2 <= quiet_minutes <= 10 or not 1 <= active_minutes < quiet_minutes:
        raise SupervisionLogError("Gmail cadence policy is invalid")
    if not 5 <= window_minutes <= 120:
        raise SupervisionLogError("Gmail active-window policy is invalid")
    now = (
        parse_event_time(args.now, label="Current time")
        if args.now
        else dt.datetime.now(dt.timezone.utc)
    )
    activity = next(
        (
            item
            for item in reversed(events(directory / "events.jsonl"))
            if is_gmail_conversation_activity(item)
        ),
        None,
    )
    active_until: dt.datetime | None = None
    if activity is not None:
        active_until = parse_event_time(
            activity.get("timestamp"), label="Gmail activity timestamp"
        ) + dt.timedelta(minutes=window_minutes)
    active = active_until is not None and now < active_until
    desired_minutes = active_minutes if active else quiet_minutes
    print(
        json.dumps(
            {
                "mode": "active" if active else "quiet",
                "desired_interval_minutes": desired_minutes,
                "desired_rrule": f"RRULE:FREQ=MINUTELY;INTERVAL={desired_minutes}",
                "quiet_interval_minutes": quiet_minutes,
                "active_interval_minutes": active_minutes,
                "active_window_minutes": window_minutes,
                "last_activity_record_id": (
                    activity.get("record_id") if activity is not None else None
                ),
                "last_activity_at": (
                    activity.get("timestamp") if activity is not None else None
                ),
                "active_until": active_until.isoformat() if active_until else None,
                "seconds_until_quiet": (
                    max(0, int((active_until - now).total_seconds()))
                    if active_until is not None
                    else 0
                ),
            },
            sort_keys=True,
        )
    )


def cmd_status(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    all_events = events(directory / "events.jsonl")
    incident_events = [item for item in all_events if item.get("kind") == "incident"]
    incident_heads: dict[str, dict[str, Any]] = {}
    for item in all_events:
        current_incident_id = item.get("incident_id")
        # Delivery receipts are projections of an incident outcome, not a
        # lifecycle transition. Keep the latest substantive incident record as
        # the head so email status such as `sent` cannot hide `under-review`,
        # `awaiting-target-evidence`, or a terminal resolution.
        if current_incident_id and item.get("kind") != "notification":
            incident_heads[current_incident_id] = item
    open_incidents = [
        item
        for item in incident_heads.values()
        if item.get("status") not in TERMINAL_INCIDENT_STATUSES
    ]
    open_incident_ids = [item["incident_id"] for item in open_incidents]
    last = last_check(all_events)
    meta_reviews = [item for item in all_events if item.get("kind") == "meta-review"]
    notification_events = [
        item for item in all_events if item.get("kind") == "notification"
    ]
    inbound_events = [
        item for item in all_events if item.get("kind") == "inbound-message"
    ]
    roundup_events = [item for item in all_events if item.get("kind") == "roundup"]
    lifecycle_events = [
        item for item in all_events if item.get("kind") == "lifecycle"
    ]
    decision_heads: dict[str, dict[str, Any]] = {}
    for item in all_events:
        if item.get("kind") == "decision" and item.get("decision_id"):
            decision_heads[str(item["decision_id"])] = item
    open_decisions = [
        item
        for item in decision_heads.values()
        if item.get("phase") != "target-acknowledged"
    ]
    print(
        json.dumps(
            {
                "target_thread_id": args.target_thread,
                "root": str(directory),
                "policy": policy,
                "event_count": len(all_events),
                "incident_count": len(incident_events),
                "open_incident_ids": open_incident_ids,
                "open_incidents": open_incidents,
                "last_check": last,
                "last_meta_review": meta_reviews[-1] if meta_reviews else None,
                "notification_count": len(notification_events),
                "last_notification": (
                    notification_events[-1] if notification_events else None
                ),
                "inbound_message_count": len(inbound_events),
                "last_inbound_message": (
                    inbound_events[-1] if inbound_events else None
                ),
                "roundup_count": len(roundup_events),
                "last_roundup": roundup_events[-1] if roundup_events else None,
                "lifecycle_count": len(lifecycle_events),
                "last_lifecycle": (
                    lifecycle_events[-1] if lifecycle_events else None
                ),
                "decision_count": len(decision_heads),
                "open_decisions": open_decisions,
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Maintain bounded tracker supervision records")
    result.add_argument("--root", help="Override the supervision root for testing")
    subparsers = result.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--target-thread", required=True)
    init.add_argument("--target-label", required=True)
    init.add_argument("--watcher-thread", required=True)
    init.add_argument("--reviewer-thread", required=True)
    init.add_argument("--base-reviewer-thread")
    init.add_argument("--notice-reviewer-thread")
    init.add_argument("--fix-executor-thread")
    init.set_defaults(func=cmd_init)

    bind = subparsers.add_parser("bind")
    bind.add_argument("--target-thread", required=True)
    bind.add_argument("--base-reviewer-thread")
    bind.add_argument("--notice-reviewer-thread")
    bind.add_argument("--fix-executor-thread")
    bind.add_argument("--routine-automation")
    bind.add_argument("--meta-automation")
    bind.add_argument("--gmail-gate-thread")
    bind.add_argument("--gmail-processor-thread")
    bind.add_argument("--gmail-poll-automation")
    bind.add_argument("--roundup-thread")
    bind.add_argument("--roundup-automation")
    bind.add_argument("--gmail-reply-message-id")
    bind.add_argument("--gmail-project-key")
    bind.add_argument("--gmail-subject")
    bind.add_argument("--gmail-priority-reply-message-id")
    bind.add_argument("--gmail-priority-project-key")
    bind.add_argument("--gmail-priority-subject")
    bind.add_argument("--gmail-priority-decision-context", action="store_true")
    bind.add_argument("--gmail-roundup-reply-message-id")
    bind.add_argument("--gmail-roundup-project-key")
    bind.add_argument("--gmail-roundup-subject")
    bind.set_defaults(func=cmd_bind)

    gate = subparsers.add_parser("gate")
    gate.add_argument("--target-thread", required=True)
    gate.add_argument("--state-fingerprint")
    gate.add_argument("--thread-updated-at", default="")
    gate.add_argument("--thread-status", default="")
    gate.add_argument("--active-block", default="")
    gate.add_argument("--latest-item", default="")
    gate.add_argument("--checkpoint", default="")
    gate.set_defaults(func=cmd_gate)

    thread_route_gate = subparsers.add_parser("thread-route-gate")
    thread_route_gate.add_argument("--target-thread", required=True)
    thread_route_gate.add_argument("--recipient-thread", required=True)
    thread_route_gate.add_argument(
        "--purpose", choices=sorted(THREAD_ROUTE_PURPOSE_ROLES), required=True
    )
    thread_route_gate.add_argument("--source-record", required=True)
    thread_route_gate.add_argument("--action", required=True)
    thread_route_gate.set_defaults(func=cmd_thread_route_gate)

    record = subparsers.add_parser("record")
    record.add_argument("--target-thread", required=True)
    record.add_argument("--kind", required=True)
    record.add_argument("--model", default="")
    record.add_argument("--reasoning", default="")
    record.add_argument("--state-fingerprint", default="")
    record.add_argument("--status", default="")
    record.add_argument("--severity", default="info")
    record.add_argument("--category", default="")
    record.add_argument("--active-block", default="")
    record.add_argument("--checkpoint", default="")
    record.add_argument("--summary", required=True)
    record.add_argument("--evidence", action="append", default=[])
    record.add_argument("--estimated-risk", default="")
    record.add_argument("--action", default="")
    record.add_argument("--resolution", default="")
    record.add_argument("--dedup-key", default="")
    record.add_argument("--incident-id")
    record.add_argument("--review-id")
    record.add_argument("--notice-disposition", choices=["", *sorted(NOTICE_DISPOSITIONS)], default="")
    record.add_argument("--resolution-owner", choices=["", *sorted(RESOLUTION_OWNERS)], default="")
    record.add_argument("--user-action-required", choices=["", "yes", "no"], default="")
    record.set_defaults(func=cmd_record)

    notice_gate = subparsers.add_parser("notice-gate")
    notice_gate.add_argument("--target-thread", required=True)
    notice_gate.add_argument("--incident-id", required=True)
    notice_gate.add_argument("--source-record", required=True)
    notice_gate.add_argument("--notice-disposition", choices=sorted(NOTICE_DISPOSITIONS), required=True)
    notice_gate.add_argument("--resolution-owner", choices=sorted(RESOLUTION_OWNERS), required=True)
    notice_gate.add_argument("--user-action-required", choices=["yes", "no"], required=True)
    notice_gate.add_argument("--severity", choices=sorted(SEVERITIES), default="warning")
    notice_gate.set_defaults(func=cmd_notice_gate)

    lifecycle_gate = subparsers.add_parser("lifecycle-gate")
    lifecycle_gate.add_argument("--target-thread", required=True)
    lifecycle_gate.add_argument(
        "--lifecycle-state", choices=sorted(LIFECYCLE_STATES), required=True
    )
    lifecycle_gate.add_argument("--source-record", required=True)
    lifecycle_gate.add_argument("--state-fingerprint", default="")
    lifecycle_gate.set_defaults(func=cmd_lifecycle_gate)

    decision_record = subparsers.add_parser("decision-record")
    decision_record.add_argument("--target-thread", required=True)
    decision_record.add_argument("--decision-id", required=True)
    decision_record.add_argument(
        "--classification", choices=sorted(DECISION_CLASSIFICATIONS), required=True
    )
    decision_record.add_argument("--phase", choices=sorted(DECISION_PHASES), required=True)
    decision_record.add_argument(
        "--safe-frontier", choices=sorted(SAFE_FRONTIER_POSTURES), required=True
    )
    decision_record.add_argument("--attempt", type=int, default=0)
    decision_record.add_argument("--outcome", choices=sorted(DECISION_OUTCOMES), default="")
    decision_record.add_argument("--decision-packet-hash", required=True)
    decision_record.add_argument("--blocked-scope-hash", required=True)
    decision_record.add_argument("--safe-frontier-hash", required=True)
    decision_record.add_argument("--state-fingerprint", default="")
    decision_record.add_argument("--evidence", action="append", required=True)
    decision_record.add_argument("--now")
    decision_record.set_defaults(func=cmd_decision_record)

    decision_gate = subparsers.add_parser("decision-gate")
    decision_gate.add_argument("--target-thread", required=True)
    decision_gate.add_argument("--decision-id", required=True)
    decision_gate.add_argument("--now")
    decision_gate.set_defaults(func=cmd_decision_gate)

    gmail_gate = subparsers.add_parser("gmail-gate")
    gmail_gate.add_argument("--target-thread", required=True)
    gmail_gate.add_argument("--message-id", action="append", required=True)
    gmail_gate.set_defaults(func=cmd_gmail_gate)

    gmail_cadence = subparsers.add_parser("gmail-cadence")
    gmail_cadence.add_argument("--target-thread", required=True)
    gmail_cadence.add_argument(
        "--now", help="Override current ISO-8601 time for deterministic verification"
    )
    gmail_cadence.set_defaults(func=cmd_gmail_cadence)

    adjust = subparsers.add_parser("adjust")
    adjust.add_argument("--target-thread", required=True)
    adjust.add_argument("--routine-minutes", type=int)
    adjust.add_argument("--meta-review-hours", type=int)
    adjust.add_argument(
        "--max-sample-denominator",
        "--sol-sample-denominator",
        dest="max_sample_denominator",
        type=int,
    )
    adjust.add_argument("--cooldown-minutes", type=int)
    adjust.add_argument("--max-escalations-per-hour", type=int)
    adjust.add_argument("--gmail-quiet-minutes", type=int)
    adjust.add_argument("--gmail-active-minutes", type=int)
    adjust.add_argument("--gmail-active-window-minutes", type=int)
    adjust.add_argument(
        "--skill-maintenance-mode",
        choices=sorted(SKILL_MAINTENANCE_MODES),
    )
    adjust.add_argument("--reason", required=True)
    adjust.add_argument("--evidence", action="append", default=[])
    adjust.set_defaults(func=cmd_adjust)

    status = subparsers.add_parser("status")
    status.add_argument("--target-thread", required=True)
    status.set_defaults(func=cmd_status)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (SupervisionLogError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
