#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile
import tomllib
from contextlib import contextmanager
from email import policy as email_policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


DEFAULT_ROOT = Path.home() / ".codex" / "supervision" / "tracker-runs"
CODEX_AUTOMATIONS_ROOT = Path.home() / ".codex" / "automations"
MISSION_META_CHARTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "mission-meta-charter-v1.json"
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
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
    "successor-transition",
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
    "resolved",
}
NON_COMPLETION_CHECK_CATEGORIES = {"max-sample", "meta-sample"}
OUTCOME_COMPLETION_CATEGORY = "observable-outcome-completion"
OUTCOME_COMPLETION_STATUSES = {"verified", "failed"}
OUTCOME_COMPLETION_HASH_FIELDS = (
    "outcome_manifest_sha256",
    "artifact_currentness_sha256",
    "effect_reconciliation_sha256",
    "open_item_compatibility_sha256",
    "independent_challenge_sha256",
    "capability_reconciliation_sha256",
)
CAPABILITY_RECONCILIATION_FIELDS = (
    "requested_capability",
    "protected_capabilities",
    "selected_architecture_level",
    "accepted_tradeoffs",
    "current_behavior",
    "operator_visible_effects",
    "supported_gaps",
)
CAPABILITY_RECONCILIATION_KIND = (
    "software-factory-terminal-capability-reconciliation"
)
CAPABILITY_RECONCILIATION_POSTURES = {"verified", "reopen-narrow-owner"}
MAX_CAPABILITY_RECONCILIATION_BYTES = 64 * 1024
TERMINAL_REPORT_DELIVERY_CATEGORY = "gmail-terminal-completion"
WEEKLY_REPORT_DELIVERY_CATEGORY = "gmail-weekly-report"
TERMINAL_SHUTDOWN_CATEGORY = "terminal-supervision-shutdown"
SUPERVISION_PAUSE_CATEGORY = "supervision-pause"
SUPERVISION_RESUME_CATEGORY = "supervision-resume"
SUPERVISION_RESUME_CONTRACT_VERSION = 1
MAX_AUTOMATION_OWNER_BYTES = 256 * 1024
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
FACTORY_EVOLUTION_ARTIFACT_NAMES = {
    "learning-packet.json",
    "prepare-manifest.json",
    "review.json",
    "finalize-manifest.json",
    "evaluation.json",
    "machine-report.json",
    "manifest.json",
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
SUCCESSOR_TRANSITION_PHASES = (
    "required",
    "successor-created",
    "successor-bound",
    "handoff-sent",
    "target-acknowledged",
    "work-started",
)
SUCCESSOR_TRANSITION_IDENTITY_FIELDS = (
    "tracker_sha256",
    "tracker_source_record",
    "requested_block_range",
    "first_eligible_block",
    "source_mission_root",
    "governing_authority_source_class",
    "governing_authority_source_record",
)
MISSION_ACTIVATION_PHASES = ("pending", "work-started")
MISSION_ACTIVATION_START_ACTION = "start-current-mission-first-eligible-work"
FAILURE_MODE_LAYERS = {
    "authority",
    "control-plane",
    "evidence",
    "execution",
    "lifecycle",
    "reporting",
    "resource",
    "validation",
}
REUSABLE_LANE_REQUIRED_FAILURE_MODE_IDS = {
    "FM-INVOCATION-ENVELOPE-MAINTENANCE-OMISSION",
}
REUSABLE_LANE_DISPOSITIONS = (
    "candidate-opened",
    "existing-owner-sufficient",
    "repository-specific-not-applicable",
    "evidence-pending",
)
REUSABLE_LANE_EFFECTIVENESS_STATUSES = TERMINAL_INCIDENT_STATUSES | {
    "effective",
    "verified",
}
AUTHORITY_SOURCE_CLASSES = {
    "direct-user",
    "system",
    "repository",
    "tracker",
    "supervisor-steer",
    "codex_delegation",
    "derived-inference",
}
DIRECT_AUTHORITY_SOURCE_CLASSES = {
    "direct-user",
    "system",
    "repository",
    "tracker",
}
MISSION_IMPACT_CLASSES = {"local", "material", "goal-blocking", "goal-reversing"}
REVERSIBILITY_POSTURES = {"reversible", "conditional", "irreversible"}
MISSION_IMPACT_FIELDS = (
    "mission_root",
    "authority_source_class",
    "authority_source_record",
    "impact_class",
    "affected_width",
    "duration",
    "reversibility",
    "ordinary_means_disabled",
    "independent_mission_review",
)
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
        "effectiveness_or_closure_requires_reusable_lane_disposition": True,
        "reusable_lane_dispositions": list(REUSABLE_LANE_DISPOSITIONS),
    }


def legacy_execution_economy_contract_without_reusable_lane() -> dict[str, Any]:
    """Exact predecessor accepted only so `bind` can upgrade a live policy."""

    contract = execution_economy_contract()
    contract.pop("effectiveness_or_closure_requires_reusable_lane_disposition")
    contract.pop("reusable_lane_dispositions")
    return contract


def outcome_completion_contract() -> dict[str, Any]:
    return {
        "enabled": True,
        "terminal_state": "completed",
        "record_category": OUTCOME_COMPLETION_CATEGORY,
        "required_bindings": list(OUTCOME_COMPLETION_HASH_FIELDS),
        "capability_reconciliation_required_fields": list(
            CAPABILITY_RECONCILIATION_FIELDS
        ),
        "supported_gap_posture": "reject-completed-and-reopen-narrow-owner",
        "reviewer_model": "gpt-5.6-sol",
        "reviewer_reasoning": ["xhigh", "max"],
        "missing_or_failed_posture": "reject-completed-and-open-critical-review",
        "process_proxies_sufficient": False,
    }


def legacy_outcome_completion_contract_without_capability() -> dict[str, Any]:
    """Exact predecessor accepted only so `bind` can upgrade a live policy."""

    contract = outcome_completion_contract()
    contract["required_bindings"] = [
        field
        for field in contract["required_bindings"]
        if field != "capability_reconciliation_sha256"
    ]
    contract.pop("capability_reconciliation_required_fields")
    contract.pop("supported_gap_posture")
    return contract


def legacy_outcome_completion_contract_with_unvalidated_capability() -> dict[str, Any]:
    """Exact Block 6 predecessor accepted only so `bind` can upgrade it."""

    contract = outcome_completion_contract()
    contract["capability_reconciliation_required_fields"] = [
        *contract["capability_reconciliation_required_fields"][:-1],
        "supported_gaps_and_narrow_owner",
    ]
    return contract


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


def weekly_report_contract() -> dict[str, Any]:
    return {
        "enabled": False,
        "timezone": "America/Los_Angeles",
        "weekday": "MO",
        "local_time": "08:00",
        "coverage_days": 7,
        "automation_id": None,
        "writer_role": "roundup_writer",
        "email_lane": "gmail_roundup",
        "cognitive_review_required": True,
        "pdf_required": True,
        "attachment_delivery_required_when_configured": True,
        "gmail_raw_mime_readback_required": True,
        "gmail_attachment_owner_ids_required": True,
    }


def terminal_report_contract() -> dict[str, Any]:
    return {
        "enabled": True,
        "writer_role": "base_reviewer",
        "email_lane": "gmail",
        "report_types": [
            "work-since-last-report",
            "full-implementation-report-of-reports",
        ],
        "cognitive_review_required": True,
        "pdf_required": True,
        "attachment_delivery_required": True,
        "gmail_raw_mime_readback_required": True,
        "gmail_attachment_owner_ids_required": True,
        "delivery_required_before_pause": True,
        "shutdown_receipt_required": True,
        "automation_owner_state_required": True,
        "verified_prior_reports_required": True,
        "pdf_semantic_projection_required": True,
        "delta_anchor": "latest-roundup-or-report",
        "full_scope": "supervision-inception-through-completed-fingerprint",
    }


def alignment_operating_contract() -> dict[str, Any]:
    """Keep supervision aligned without requiring target-native alignment."""

    return {
        "mode": "independent-mission-charter",
        "governing_source": "bound-direct-mission-sources",
        "meta_charter": mission_meta_charter_binding(),
        "target_native_alignment_required": False,
        "target_native_alignment_role": "optional-read-only-corroboration",
        "missing_target_alignment_posture": "unavailable-open",
        "target_native_alignment_may_authorize_or_block": False,
        "target_native_alignment_writes_allowed": False,
    }


def legacy_alignment_operating_contract_v1() -> dict[str, Any]:
    """Exact predecessor from candidate d66ac96."""

    return {
        "mode": "independent-mission-charter",
        "governing_source": "bound-direct-mission-sources",
        "target_native_alignment_required": False,
        "target_native_alignment_role": "optional-read-only-corroboration",
        "missing_target_alignment_posture": "unavailable-open",
        "target_native_alignment_may_authorize_or_block": False,
        "target_native_alignment_writes_allowed": False,
    }


def legacy_mission_binding_contract(
    mission_root: str, mission_source_record: str
) -> dict[str, Any]:
    """Exact accepted predecessor retained for readable live policies."""

    return {
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "semantic_owner": "target-or-tracker",
        "frame_fields": [
            "primary-outcome",
            "ordinary-effect-classes",
            "hard-direct-authority-and-safety-boundaries",
            "acceptance-and-stop-boundary",
        ],
        "primary_mission_governs_subordinate_process": True,
        "aggregate_score": False,
    }


def legacy_mission_binding_contract_v2(
    mission_root: str, mission_source_record: str
) -> dict[str, Any]:
    return {
        "contract_version": 2,
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "alignment_operating_contract": legacy_alignment_operating_contract_v1(),
        "frame_fields": [
            "primary-outcome",
            "ordinary-effect-classes",
            "hard-direct-authority-and-safety-boundaries",
            "acceptance-and-stop-boundary",
        ],
        "primary_mission_governs_subordinate_process": True,
        "aggregate_score": False,
    }


def mission_binding_contract(
    mission_root: str,
    mission_source_record: str,
    *,
    derivation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    meta_charter = mission_meta_charter_binding()
    mission_derivation = (
        dict(derivation)
        if derivation is not None
        else {
            "kind": "supervision-mission-derivation",
            "mode": "explicit-exact-root",
            "meta_charter": meta_charter,
        }
    )
    return {
        "contract_version": 3,
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "mission_derivation": mission_derivation,
        "alignment_operating_contract": alignment_operating_contract(),
        "frame_fields": [
            "primary-outcome",
            "ordinary-effect-classes",
            "hard-direct-authority-and-safety-boundaries",
            "acceptance-and-stop-boundary",
        ],
        "primary_mission_governs_subordinate_process": True,
        "aggregate_score": False,
    }


def derive_mission_binding(
    *,
    target_thread: str,
    source_class: str,
    source_record: str,
    source_sha256: str,
) -> dict[str, Any]:
    if source_class not in DIRECT_AUTHORITY_SOURCE_CLASSES:
        raise SupervisionLogError(
            "Mission derivation requires a direct-user, system, repository, or tracker source"
        )
    target = safe_id(target_thread, label="target thread ID")
    record = safe_id(source_record, label="mission source record")
    source_hash = exact_sha256(source_sha256, label="mission source SHA-256")
    derivation = {
        "kind": "supervision-mission-derivation",
        "mode": "derived-from-versioned-meta-charter",
        "target_thread_id": target,
        "controlling_source": {
            "class": source_class,
            "record": record,
            "sha256": source_hash,
        },
        "meta_charter": mission_meta_charter_binding(),
    }
    return mission_binding_contract(
        digest(derivation), record, derivation=derivation
    )


def mission_binding_identity(binding: Mapping[str, Any]) -> tuple[str, str] | None:
    root = binding.get("mission_root")
    source = binding.get("mission_source_record")
    if (
        not isinstance(root, str)
        or not root
        or not isinstance(source, str)
        or not source
    ):
        return None
    return root, source


def mission_binding_is_supported(
    binding: Mapping[str, Any], *, target_thread: str
) -> bool:
    identity = mission_binding_identity(binding)
    if identity is None:
        return False
    mission_root, source_record = identity
    exact_predecessors = {
        canonical(legacy_mission_binding_contract(mission_root, source_record)),
        canonical(legacy_mission_binding_contract_v2(mission_root, source_record)),
        canonical(mission_binding_contract(mission_root, source_record)),
    }
    if canonical(binding) in exact_predecessors:
        return True
    derivation = binding.get("mission_derivation")
    if not isinstance(derivation, Mapping):
        return False
    if derivation.get("mode") != "derived-from-versioned-meta-charter":
        return False
    source = derivation.get("controlling_source")
    if not isinstance(source, Mapping):
        return False
    try:
        expected = derive_mission_binding(
            target_thread=target_thread,
            source_class=str(source.get("class", "")),
            source_record=str(source.get("record", "")),
            source_sha256=str(source.get("sha256", "")),
        )
    except SupervisionLogError:
        return False
    return binding == expected


def mission_binding_from_args(
    args: argparse.Namespace, *, required: bool
) -> dict[str, Any] | None:
    mission_root = clean(
        getattr(args, "mission_root", None), label="mission root", maximum=128
    )
    mission_source_record = clean(
        getattr(args, "mission_source_record", None),
        label="mission source record",
        maximum=128,
    )
    source_class = getattr(args, "mission_source_class", None)
    source_sha256 = clean(
        getattr(args, "mission_source_sha256", None),
        label="mission source SHA-256",
        maximum=64,
    )
    if bool(source_class) != bool(source_sha256):
        raise SupervisionLogError(
            "Mission derivation requires both source class and source SHA-256"
        )
    if source_class:
        if not mission_source_record:
            raise SupervisionLogError(
                "Mission derivation requires an exact source record"
            )
        derived = derive_mission_binding(
            target_thread=str(getattr(args, "target_thread", "")),
            source_class=str(source_class),
            source_record=mission_source_record,
            source_sha256=source_sha256,
        )
        if mission_root and mission_root != derived["mission_root"]:
            raise SupervisionLogError(
                "Supplied mission root differs from deterministic derivation"
            )
        return derived
    if bool(mission_root) != bool(mission_source_record):
        raise SupervisionLogError(
            "Mission binding requires both an exact mission root and source record"
        )
    if required and not mission_root:
        raise SupervisionLogError(
            "New supervision requires an exact mission root and source record"
        )
    if not mission_root:
        return None
    safe_id(mission_root, label="mission root")
    safe_id(mission_source_record, label="mission source record")
    return mission_binding_contract(mission_root, mission_source_record)


def bound_mission(policy: dict[str, Any]) -> dict[str, Any] | None:
    binding = policy.get("mission_binding")
    if not isinstance(binding, dict):
        return None
    if mission_binding_identity(binding) is None:
        return None
    return binding


def policy_mission_roots(directory: Path) -> dict[str, str]:
    """Resolve policy hashes to the mission that was active for that version."""

    roots: dict[str, str] = {}
    for record in events(directory / "policy-history.jsonl"):
        snapshot = record.get("policy")
        if not isinstance(snapshot, dict):
            continue
        policy_sha256 = snapshot.get("policy_sha256")
        binding = bound_mission(snapshot)
        if isinstance(policy_sha256, str) and binding is not None:
            roots[policy_sha256] = str(binding["mission_root"])
    return roots


def mission_scoped_events(
    directory: Path,
    policy: dict[str, Any],
    all_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    binding = bound_mission(policy)
    if binding is None:
        return all_events
    active_root = str(binding["mission_root"])
    roots = policy_mission_roots(directory)
    return [
        item
        for item in all_events
        if roots.get(str(item.get("policy_sha256", ""))) == active_root
    ]


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
    expected_completion = outcome_completion_contract()
    if policy.get("outcome_completion") != expected_completion:
        policy["outcome_completion"] = expected_completion
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
    reports = policy.setdefault("reports", {})
    expected_terminal = terminal_report_contract()
    if reports.get("terminal") != expected_terminal:
        reports["terminal"] = expected_terminal
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


def exact_sha256(value: str, *, label: str) -> str:
    text = str(value).strip()
    if not SHA256.fullmatch(text):
        raise SupervisionLogError(f"{label} must be an exact lowercase SHA-256")
    return text


def mission_meta_charter_profile() -> dict[str, Any]:
    try:
        value = json.loads(MISSION_META_CHARTER_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Cannot read mission meta-charter profile") from exc
    if not isinstance(value, dict):
        raise SupervisionLogError("Mission meta-charter profile must be an object")
    expected_keys = {
        "schema_version",
        "kind",
        "profile_id",
        "version",
        "primary_directive",
        "root_invariants",
        "valid_stop_conditions",
        "invalid_stop_bases",
        "unsupported_goal_preventing_stop",
        "target_native_alignment",
        "non_goals",
        "profile_sha256",
    }
    if set(value) != expected_keys:
        raise SupervisionLogError("Mission meta-charter profile shape differs")
    recorded_hash = exact_sha256(
        str(value["profile_sha256"]), label="mission meta-charter profile SHA-256"
    )
    material = {
        key: item for key, item in value.items() if key != "profile_sha256"
    }
    if digest(material) != recorded_hash:
        raise SupervisionLogError("Mission meta-charter profile hash is stale")
    if (
        value["schema_version"] != 1
        or value["kind"] != "supervision-mission-meta-charter"
        or value["profile_id"] != "tracker-outcome-completion"
        or value["version"] != 1
    ):
        raise SupervisionLogError("Unsupported mission meta-charter profile")
    if not isinstance(value["root_invariants"], list) or not all(
        isinstance(item, str) for item in value["root_invariants"]
    ):
        raise SupervisionLogError("Mission meta-charter invariants must be strings")
    if not isinstance(value["valid_stop_conditions"], list) or not all(
        isinstance(item, str) for item in value["valid_stop_conditions"]
    ):
        raise SupervisionLogError("Mission meta-charter stop conditions must be strings")
    if not isinstance(value["invalid_stop_bases"], list) or not all(
        isinstance(item, str) for item in value["invalid_stop_bases"]
    ):
        raise SupervisionLogError("Mission meta-charter invalid stop bases must be strings")
    required_invariants = {
        "direct-authority-over-derived-process-state",
        "observable-outcome-over-process-proxy",
        "ordinary-required-effects-expected-when-authorized",
        "preserve-valid-work-history-and-user-owned-state",
        "safe-in-scope-continuation-by-default",
        "stop-expansion-after-observable-completion",
    }
    if set(value["root_invariants"]) != required_invariants:
        raise SupervisionLogError("Mission meta-charter root invariants differ")
    if value["primary_directive"] != "complete-the-explicit-governing-outcome":
        raise SupervisionLogError("Mission meta-charter primary directive differs")
    if set(value["valid_stop_conditions"]) != {
        "current-direct-goal-change-or-stop",
        "hard-authority-or-safety-boundary",
        "independently-established-current-infeasibility",
        "observable-completion",
        "required-nondelegable-input-unavailable-and-empty-safe-frontier",
    }:
        raise SupervisionLogError("Mission meta-charter valid stop conditions differ")
    if set(value["invalid_stop_bases"]) != {
        "checkpoint-freeze-alone",
        "historical-or-operation-specific-hold",
        "monitoring-or-supervision-uncertainty-alone",
        "process-check-or-test-result-alone",
        "safe-frontier-still-nonempty",
    }:
        raise SupervisionLogError("Mission meta-charter invalid stop bases differ")
    stop = value["unsupported_goal_preventing_stop"]
    if stop != {
        "severity": "critical",
        "posture": "challenge-and-resume-or-establish-valid-stop",
        "user_action_required_by_default": False,
    }:
        raise SupervisionLogError(
            "Mission meta-charter weakens unsupported stop handling"
        )
    target_alignment = value["target_native_alignment"]
    if target_alignment != {
        "required": False,
        "role": "optional-read-only-corroboration",
        "missing_posture": "unavailable-open",
        "may_authorize_or_block": False,
        "writes_allowed": False,
    }:
        raise SupervisionLogError(
            "Mission meta-charter target-alignment boundary differs"
        )
    if set(value["non_goals"]) != {
        "general-objective-management-platform",
        "target-alignment-schema-or-service",
        "universal-quality-score",
    }:
        raise SupervisionLogError("Mission meta-charter non-goals differ")
    return value


def mission_meta_charter_binding() -> dict[str, Any]:
    profile = mission_meta_charter_profile()
    return {
        "profile_id": profile["profile_id"],
        "version": profile["version"],
        "sha256": profile["profile_sha256"],
    }


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
        "outcome_completion": outcome_completion_contract(),
        "decision_resolution": decision_resolution_contract(),
        "cross_thread_routing": cross_thread_routing_contract(),
        "skill_maintenance": skill_maintenance_contract(),
        "reports": {
            "weekly": weekly_report_contract(),
            "terminal": terminal_report_contract(),
        },
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
    mission_binding = mission_binding_from_args(args, required=False)
    if mission_binding is not None:
        policy["mission_binding"] = mission_binding
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
    mission_binding = policy.get("mission_binding")
    if mission_binding is not None:
        if not isinstance(mission_binding, dict):
            raise SupervisionLogError("Mission binding is not an object")
        mission_root = mission_binding.get("mission_root")
        mission_source_record = mission_binding.get("mission_source_record")
        if not isinstance(mission_root, str) or not mission_root:
            raise SupervisionLogError("Mission binding lacks an exact root")
        if not isinstance(mission_source_record, str) or not mission_source_record:
            raise SupervisionLogError("Mission binding lacks an exact source record")
        safe_id(mission_root, label="mission root")
        safe_id(mission_source_record, label="mission source record")
        if not mission_binding_is_supported(
            mission_binding,
            target_thread=str(policy.get("target_thread_id", "")),
        ):
            raise SupervisionLogError("Mission binding contract differs")
    maintenance = policy.get("skill_maintenance")
    if maintenance is not None:
        if maintenance.get("mode") not in SKILL_MAINTENANCE_MODES:
            raise SupervisionLogError("Unsupported skill-maintenance mode")
        if maintenance.get("allowlist") != ALLOWLISTED_MAINTENANCE_SKILLS:
            raise SupervisionLogError("Skill-maintenance allowlist differs")
    economy = policy.get("execution_economy")
    if economy is not None and canonical(economy) not in {
        canonical(execution_economy_contract()),
        canonical(legacy_execution_economy_contract_without_reusable_lane()),
    }:
        raise SupervisionLogError("Execution-economy contract differs")
    completion = policy.get("outcome_completion")
    if completion is not None and canonical(completion) not in {
        canonical(outcome_completion_contract()),
        canonical(legacy_outcome_completion_contract_without_capability()),
        canonical(legacy_outcome_completion_contract_with_unvalidated_capability()),
    }:
        raise SupervisionLogError("Outcome-completion contract differs")
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
    weekly = policy.get("reports", {}).get("weekly")
    if weekly is not None:
        expected_weekly = weekly_report_contract()
        for key in (
            "timezone",
            "writer_role",
            "email_lane",
            "cognitive_review_required",
            "pdf_required",
        ):
            if weekly.get(key) != expected_weekly[key]:
                raise SupervisionLogError("Weekly supervision report contract differs")
        if weekly.get("weekday") not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}:
            raise SupervisionLogError("Weekly report weekday is invalid")
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(weekly.get("local_time", ""))):
            raise SupervisionLogError("Weekly report local time is invalid")
        coverage_days = weekly.get("coverage_days")
        if not isinstance(coverage_days, int) or not 2 <= coverage_days <= 31:
            raise SupervisionLogError("Weekly report coverage days are invalid")
        if weekly.get("enabled"):
            if not weekly.get("automation_id"):
                raise SupervisionLogError("Enabled weekly report lacks an automation binding")
            roundup = policy.get("notifications", {}).get("gmail_roundup", {})
            if not roundup.get("enabled") or not all(
                roundup.get(key) for key in ("project_key", "reply_message_id", "subject")
            ):
                raise SupervisionLogError("Weekly report requires the bound roundup email lane")
    terminal = policy.get("reports", {}).get("terminal")
    if terminal is not None and terminal != terminal_report_contract():
        raise SupervisionLogError("Terminal implementation report contract differs")
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


def append_event_locked(
    args: argparse.Namespace, directory: Path, record: dict[str, Any]
) -> None:
    """Append only when the event still cites the current policy snapshot."""

    current_directory, current = load_policy(args)
    if current_directory.resolve() != directory.resolve():
        raise SupervisionLogError("Event append resolved a different supervision root")
    if record.get("policy_sha256") != current.get("policy_sha256"):
        raise SupervisionLogError(
            "Supervision policy changed concurrently; rebuild the event before appending"
        )
    append_raw_locked(directory / "events.jsonl", record)


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
    for envelope_name in ("failure_mode", "containment", "reusable_lane"):
        if record.get(envelope_name):
            rows.append(
                f"- {envelope_name.replace('_', ' ').title()}: "
                f"`{canonical(record[envelope_name]).decode('utf-8')}`\n"
            )
    with path.open(mode, encoding="utf-8") as handle:
        handle.writelines(rows)
    os.chmod(path, 0o600)


def cmd_mission_plan(args: argparse.Namespace) -> None:
    binding = derive_mission_binding(
        target_thread=args.target_thread,
        source_class=args.mission_source_class,
        source_record=args.mission_source_record,
        source_sha256=args.mission_source_sha256,
    )
    print(
        json.dumps(
            {
                "kind": "supervision-mission-plan",
                "mission_root": binding["mission_root"],
                "mission_source_record": binding["mission_source_record"],
                "mission_source_class": args.mission_source_class,
                "mission_source_sha256": args.mission_source_sha256,
                "mission_binding": binding,
                "init_arguments": [
                    "--mission-source-class",
                    args.mission_source_class,
                    "--mission-source-record",
                    args.mission_source_record,
                    "--mission-source-sha256",
                    args.mission_source_sha256,
                ],
            },
            sort_keys=True,
        )
    )


def cmd_init(args: argparse.Namespace) -> None:
    mission_binding_from_args(args, required=True)
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
        current_mission = policy.get("mission_binding")
        expected_mission = expected.get("mission_binding")
        if (
            not isinstance(current_mission, Mapping)
            or not isinstance(expected_mission, Mapping)
            or mission_binding_identity(current_mission)
            != mission_binding_identity(expected_mission)
        ):
            raise SupervisionLogError("Existing policy conflicts on mission binding")
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


def write_policy_version_locked(
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
    append_raw_locked(
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


def write_policy_version(
    directory: Path,
    policy: dict[str, Any],
    *,
    kind: str,
    reason: str,
    evidence_values: list[str],
) -> None:
    with append_lock(directory):
        current = read_json(directory / "policy.json")
        validate_policy(current)
        if current.get("policy_sha256") != policy.get("policy_sha256"):
            raise SupervisionLogError(
                "Supervision policy changed concurrently; reload before writing"
            )
        write_policy_version_locked(
            directory,
            policy,
            kind=kind,
            reason=reason,
            evidence_values=evidence_values,
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
    requested_mission = mission_binding_from_args(args, required=False)
    current_mission = bound_mission(policy)
    if requested_mission is not None:
        if (
            current_mission is not None
            and mission_binding_identity(current_mission)
            != mission_binding_identity(requested_mission)
        ):
            raise SupervisionLogError("Mission binding already differs")
        if current_mission != requested_mission:
            policy["mission_binding"] = requested_mission
            changed = True
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


def cmd_mission_successor(args: argparse.Namespace) -> None:
    """Replace a completed or superseded mission without rewriting its history."""

    directory, _ = load_policy(args)
    from_root = clean(
        args.from_mission_root, label="predecessor mission root", maximum=128
    )
    safe_id(from_root, label="predecessor mission root")
    evidence_values = [
        clean(value, label="mission succession evidence", maximum=256)
        for value in args.evidence
        if value.strip()
    ]
    if not evidence_values:
        raise SupervisionLogError("Mission succession requires exact evidence")
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many mission succession evidence references")
    requested = mission_binding_from_args(args, required=True)
    assert requested is not None
    disposition = str(args.predecessor_disposition)
    reason = clean(args.reason, label="mission succession reason", maximum=480)
    first_eligible_work = clean(
        args.first_eligible_work,
        label="successor first eligible work",
        maximum=160,
    )
    if not first_eligible_work:
        raise SupervisionLogError(
            "Mission succession requires exact first eligible work"
        )

    with append_lock(directory):
        policy = read_json(directory / "policy.json")
        validate_policy(policy)
        if policy.get("target_thread_id") != args.target_thread:
            raise SupervisionLogError("Policy belongs to a different target")
        current = bound_mission(policy)
        if current is None:
            raise SupervisionLogError(
                "Mission succession requires an existing exact mission binding"
            )
        if current["mission_root"] != from_root:
            raise SupervisionLogError("Predecessor mission root differs")
        if mission_binding_identity(current) == mission_binding_identity(requested):
            raise SupervisionLogError("Successor mission is unchanged")

        all_events = events(directory / "events.jsonl")
        incident_heads: dict[str, dict[str, Any]] = {}
        decision_heads: dict[str, dict[str, Any]] = {}
        for item in all_events:
            incident_id = item.get("incident_id")
            if incident_id and is_substantive_incident_record(
                item, str(incident_id)
            ):
                incident_heads[str(incident_id)] = item
            if item.get("kind") == "decision" and item.get("decision_id"):
                decision_heads[str(item["decision_id"])] = item
        open_incidents = [
            item
            for incident_id, item in incident_heads.items()
            if not is_terminal_incident_record(item, incident_id)
        ]
        open_decisions = [
            item
            for item in decision_heads.values()
            if item.get("phase") != "target-acknowledged"
        ]
        open_transitions = successor_transition_heads(all_events, open_only=True)
        open_activations = mission_activation_heads(
            mission_scoped_events(directory, policy, all_events), open_only=True
        )
        if open_incidents or open_decisions or open_transitions or open_activations:
            raise SupervisionLogError(
                "Mission succession requires closed incidents, decisions, successor "
                "transitions, and current mission activation"
            )
        if disposition == "completed":
            scoped = mission_scoped_events(directory, policy, all_events)
            lifecycle = [item for item in scoped if item.get("kind") == "lifecycle"]
            if not lifecycle or lifecycle[-1].get("status") != "completed":
                raise SupervisionLogError(
                    "Completed mission succession requires an exact predecessor lifecycle"
                )
            lifecycle_record = safe_id(
                str(lifecycle[-1].get("record_id", "")),
                label="completed lifecycle record ID",
            )
            evidence_values.append(lifecycle_record)
        if len(evidence_values) > 16:
            raise SupervisionLogError("Too many mission succession evidence references")

        previous = {
            "mission_root": current["mission_root"],
            "mission_source_record": current["mission_source_record"],
        }
        policy["mission_binding"] = requested
        write_policy_version_locked(
            directory,
            policy,
            kind="policy-mission-successor",
            reason=f"{disposition}: {reason}",
            evidence_values=evidence_values,
        )
        activation = mission_activation_pending_record(
            target_thread=args.target_thread,
            mission_binding=requested,
            activation_policy_sha256=str(policy["policy_sha256"]),
            first_eligible_work=first_eligible_work,
            evidence=evidence_values,
        )
        activation["record_id"] = f"EVT-{len(all_events) + 1:06d}"
        append_event_locked(args, directory, activation)
    print(
        json.dumps(
            {
                "changed": True,
                "predecessor_disposition": disposition,
                "predecessor": previous,
                "successor": {
                    "mission_root": requested["mission_root"],
                    "mission_source_record": requested["mission_source_record"],
                },
                "mission_activation": activation,
                "policy": policy,
            },
            sort_keys=True,
        )
    )


def yes_no_value(raw: str | None, *, label: str) -> bool:
    if raw not in {"yes", "no"}:
        raise SupervisionLogError(f"{label} requires yes or no")
    return raw == "yes"


def mission_impact_from_args(
    args: argparse.Namespace, policy: dict[str, Any]
) -> dict[str, Any]:
    binding = bound_mission(policy)
    if binding is None:
        raise SupervisionLogError(
            "Consequential action requires an exact bound mission; run bind with its source and root"
        )
    mission_root = clean(
        getattr(args, "mission_root", None), label="mission root", maximum=128
    )
    if not mission_root:
        raise SupervisionLogError("Mission impact requires an exact mission root")
    if mission_root != binding["mission_root"]:
        raise SupervisionLogError("Mission impact cites a stale mission root")
    authority_source_class = getattr(args, "authority_source_class", None)
    if authority_source_class not in AUTHORITY_SOURCE_CLASSES:
        raise SupervisionLogError("Mission impact requires an authority source class")
    authority_source_record = clean(
        getattr(args, "authority_source_record", None),
        label="authority source record",
        maximum=128,
    )
    if not authority_source_record:
        raise SupervisionLogError("Mission impact requires an exact authority source record")
    safe_id(authority_source_record, label="authority source record")
    impact_class = getattr(args, "impact_class", None)
    if impact_class not in MISSION_IMPACT_CLASSES:
        raise SupervisionLogError("Mission impact requires an impact class")
    affected_width = clean(
        getattr(args, "affected_width", None),
        label="affected width",
        maximum=160,
    )
    duration = clean(
        getattr(args, "duration", None), label="duration", maximum=160
    )
    reversibility = getattr(args, "reversibility", None)
    if not affected_width or not duration:
        raise SupervisionLogError("Mission impact requires affected width and duration")
    if reversibility not in REVERSIBILITY_POSTURES:
        raise SupervisionLogError("Mission impact requires a reversibility posture")
    return {
        "mission_root": mission_root,
        "authority_source_class": authority_source_class,
        "authority_source_record": authority_source_record,
        "impact_class": impact_class,
        "affected_width": affected_width,
        "duration": duration,
        "reversibility": reversibility,
        "ordinary_means_disabled": yes_no_value(
            getattr(args, "ordinary_means_disabled", None),
            label="ordinary means disabled",
        ),
        "independent_mission_review": yes_no_value(
            getattr(args, "independent_mission_review", None),
            label="independent mission review",
        ),
    }


def containment_envelope_from_args(
    args: argparse.Namespace, policy: dict[str, Any]
) -> dict[str, Any]:
    impact = mission_impact_from_args(args, policy)
    operation_scope = clean(
        getattr(args, "operation_scope", None),
        label="operation scope",
        maximum=160,
    )
    block_scope = clean(
        getattr(args, "block_scope", None), label="Block scope", maximum=80
    )
    scope_identity = clean(
        getattr(args, "scope_identity", None),
        label="scope identity",
        maximum=128,
    )
    expiry_event = clean(
        getattr(args, "expiry_event", None), label="expiry event", maximum=128
    )
    if not operation_scope and not block_scope:
        raise SupervisionLogError(
            "Containment requires an exact operation or Block scope"
        )
    if not scope_identity or not expiry_event:
        raise SupervisionLogError(
            "Containment requires a content-minimized scope identity and expiry event"
        )
    safe_id(scope_identity, label="containment scope identity")
    safe_id(expiry_event, label="containment expiry event")
    carry_forward = getattr(args, "carry_forward", None)
    successor_effects = getattr(args, "successor_effects", None)
    if carry_forward != "false":
        raise SupervisionLogError("Containment must set carry-forward=false")
    if successor_effects != "allowed":
        raise SupervisionLogError("Containment must allow successor effects")
    severity = getattr(args, "severity", "info")
    incident = getattr(args, "incident_id", None)
    if impact["impact_class"] == "goal-reversing":
        raise SupervisionLogError("A supervisor containment cannot reverse the mission goal")
    if (
        impact["ordinary_means_disabled"] is True
        and impact["independent_mission_review"] is not True
    ):
        raise SupervisionLogError(
            "Containment that disables an ordinary mission means requires independent review"
        )
    if impact["impact_class"] == "goal-blocking":
        if severity != "critical" or not incident:
            raise SupervisionLogError(
                "A goal-blocking hold requires one exact critical incident"
            )
        safe_id(incident, label="incident ID")
        if not operation_scope or block_scope:
            raise SupervisionLogError(
                "A goal-blocking hold is limited to one exact operation"
            )
        if impact["independent_mission_review"] is not True:
            raise SupervisionLogError(
                "A goal-blocking hold requires independent mission-level review"
            )
    return {
        **impact,
        "operation_scope": operation_scope,
        "block_scope": block_scope,
        "scope_identity": scope_identity,
        "expiry_event": expiry_event,
        "carry_forward": False,
        "successor_effects": "allowed",
        "incident_id": incident or "",
        "severity": severity,
    }


def failure_mode_envelope_from_args(args: argparse.Namespace) -> dict[str, Any]:
    failure_mode_id = safe_id(
        str(getattr(args, "failure_mode_id", "")), label="failure mode ID"
    )
    layer = getattr(args, "failure_layer", None)
    if layer not in FAILURE_MODE_LAYERS:
        raise SupervisionLogError("Failure mode requires a maintained layer")
    required_text = {
        "mechanism": ("failure mechanism", 240),
        "trigger": ("failure trigger", 300),
        "effect": ("failure effect", 300),
        "detection": ("failure detection", 300),
        "correction": ("failure correction", 300),
        "recurrence_invariant": ("failure recurrence invariant", 300),
    }
    result: dict[str, Any] = {
        "failure_mode_id": failure_mode_id,
        "layer": layer,
    }
    for field, (label, maximum) in required_text.items():
        value = clean(
            getattr(args, f"failure_{field}", None),
            label=label,
            maximum=maximum,
        )
        if not value:
            raise SupervisionLogError(f"{label.title()} is required")
        result[field] = value
    result["human_scheduling_leak"] = yes_no_value(
        getattr(args, "failure_human_scheduling_leak", None),
        label="failure human scheduling leak",
    )
    return result


def reusable_lane_envelope_from_args(args: argparse.Namespace) -> dict[str, Any]:
    disposition = str(getattr(args, "reusable_lane_disposition", ""))
    if disposition not in REUSABLE_LANE_DISPOSITIONS:
        raise SupervisionLogError(
            "Reusable lane requires one maintained bounded disposition"
        )
    owner = clean(
        getattr(args, "reusable_lane_owner", ""),
        label="reusable lane owner",
        maximum=128,
    )
    if owner:
        safe_id(owner, label="reusable lane owner")
    rationale = clean(
        getattr(args, "reusable_lane_rationale", ""),
        label="reusable lane rationale",
        maximum=300,
    )
    evidence = [
        clean(item, label="reusable lane evidence", maximum=160)
        for item in getattr(args, "reusable_lane_evidence", [])
    ]
    if len(evidence) > 8:
        raise SupervisionLogError("Too many reusable lane evidence references")
    if any(not item for item in evidence):
        raise SupervisionLogError("Reusable lane evidence references must be exact")
    if disposition in {"candidate-opened", "existing-owner-sufficient"}:
        if not owner or not evidence:
            raise SupervisionLogError(
                f"Reusable lane disposition {disposition} requires an owner and evidence"
            )
    elif disposition == "repository-specific-not-applicable":
        if not rationale:
            raise SupervisionLogError(
                "Repository-specific reusable lane disposition requires rationale"
            )
    elif disposition == "evidence-pending":
        if not rationale or not evidence:
            raise SupervisionLogError(
                "Pending reusable lane disposition requires rationale and a next evidence trigger"
            )
    return {
        "disposition": disposition,
        "owner": owner,
        "evidence": evidence,
        "rationale": rationale,
    }


def is_supported_execution_economy_incident_record(
    item: dict[str, Any], current_incident_id: str
) -> bool:
    if not is_substantive_incident_record(item, current_incident_id):
        return False
    category = item.get("category")
    category_marks_economy = isinstance(category, str) and (
        category == "execution-economy"
        or category.startswith("execution-economy-")
    )
    failure_mode = item.get("failure_mode")
    failure_mode_marks_economy = isinstance(failure_mode, Mapping) and (
        failure_mode.get("failure_mode_id")
        in REUSABLE_LANE_REQUIRED_FAILURE_MODE_IDS
    )
    return category_marks_economy or failure_mode_marks_economy


def requires_reusable_lane_disposition(
    current_events: list[dict[str, Any]], record: dict[str, Any]
) -> bool:
    incident_id_value = record.get("incident_id")
    if not isinstance(incident_id_value, str) or not incident_id_value:
        return False
    if record.get("kind") in {"resolution", "meta-review"}:
        effectiveness_or_closure = (
            record.get("status") in REUSABLE_LANE_EFFECTIVENESS_STATUSES
            or record.get("notice_disposition") == "terminal"
        )
    else:
        return False
    return effectiveness_or_closure and any(
        is_supported_execution_economy_incident_record(
            item, incident_id_value
        )
        for item in [*current_events, record]
    )


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

    containment = None
    if getattr(args, "containment", False):
        if args.purpose != "target-action" or recipient_role != "target":
            raise SupervisionLogError(
                "Containment is permitted only for an exact target action"
            )
        containment = containment_envelope_from_args(args, policy)

    result = {
        "send_allowed": True,
        "target_thread_id": policy["target_thread_id"],
        "recipient_thread_id": recipient,
        "recipient_role": recipient_role,
        "purpose": args.purpose,
        "source_record": source_record,
        "action_sha256": digest(action),
        "policy_sha256": policy["policy_sha256"],
    }
    if containment is not None:
        result["containment"] = containment
        result["containment_sha256"] = digest(containment)
    print(json.dumps(result, sort_keys=True))


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
    all_events = events(directory / "events.jsonl")
    prior = last_check(mission_scoped_events(directory, policy, all_events))
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


def assess_outcome_completion_record(
    item: Mapping[str, Any] | None,
    *,
    policy: dict[str, Any],
    state_fingerprint: str,
) -> tuple[bool, str]:
    if policy.get("outcome_completion") != outcome_completion_contract():
        return False, "The current outcome-completion contract is not bound."
    mission = bound_mission(policy)
    if mission is None:
        return False, "The current supervision mission is not bound."
    if item is None:
        return False, "No current observable-outcome completion record exists."
    if (
        item.get("kind") != "check"
        or item.get("category") != OUTCOME_COMPLETION_CATEGORY
    ):
        return False, "The cited completion record has the wrong kind or category."
    if item.get("state_fingerprint") != state_fingerprint:
        return False, "The observable-outcome completion record is stale."
    if item.get("mission_root") != mission["mission_root"]:
        return False, "The observable-outcome completion record cites a stale mission."
    if item.get("model") != outcome_completion_contract()["reviewer_model"]:
        return False, "The completion record lacks the required independent reviewer model."
    if item.get("reasoning") not in outcome_completion_contract()["reviewer_reasoning"]:
        return False, "The completion record lacks the required reviewer reasoning level."
    for field in OUTCOME_COMPLETION_HASH_FIELDS:
        value = item.get(field)
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            return False, f"The completion record lacks an exact {field} binding."
    reviewer_id = item.get("capability_reconciliation_reviewer_id")
    if not isinstance(reviewer_id, str) or not SAFE_ID.fullmatch(reviewer_id):
        return False, "The completion record lacks the independent capability reviewer."
    runtime = policy.get("runtime")
    if not isinstance(runtime, Mapping):
        return False, "The current policy lacks bound capability reviewer roles."
    eligible_reviewers = {
        value
        for value in (
            runtime.get("base_reviewer_thread_id"),
            runtime.get("reviewer_thread_id"),
        )
        if isinstance(value, str) and value
    }
    disallowed_reviewers = {
        value
        for value in (
            policy.get("target_thread_id"),
            runtime.get("watcher_thread_id"),
            runtime.get("fix_executor_thread_id"),
        )
        if isinstance(value, str) and value
    }
    if reviewer_id not in eligible_reviewers or reviewer_id in disallowed_reviewers:
        return False, "The capability reviewer is not a bound independent role."
    implementation_owner = item.get(
        "capability_reconciliation_implementation_owner_id"
    )
    if (
        not isinstance(implementation_owner, str)
        or not SAFE_ID.fullmatch(implementation_owner)
        or implementation_owner == reviewer_id
    ):
        return False, "The capability reconciliation is self-certified."
    revision = item.get("capability_reconciliation_revision")
    if not isinstance(revision, str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision
    ):
        return False, "The completion record lacks the reconciled current revision."
    if (
        item.get("capability_reconciliation_posture") != "verified"
        or item.get("capability_reconciliation_gap_count") != 0
    ):
        return False, "The capability reconciliation retains a supported outcome gap."
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(
        isinstance(value, str) and value for value in evidence
    ):
        return False, "The completion record lacks exact source evidence."
    if item.get("status") != "verified":
        return False, "The current observable-outcome review did not verify completion."
    return True, "The current observable outcome is independently verified."


def latest_outcome_completion_record(
    all_events: list[dict[str, Any]], *, state_fingerprint: str
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in reversed(all_events)
            if item.get("kind") == "check"
            and item.get("category") == OUTCOME_COMPLETION_CATEGORY
            and item.get("state_fingerprint") == state_fingerprint
        ),
        None,
    )


def load_capability_reconciliation(
    path_value: str,
    *,
    target_thread: str,
    mission_root: str,
    state_fingerprint: str,
    current_revision: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    source = Path(path_value).expanduser()
    try:
        if not source.is_file():
            raise SupervisionLogError(
                "Capability reconciliation source is not an explicit file"
            )
        if source.stat().st_size > MAX_CAPABILITY_RECONCILIATION_BYTES:
            raise SupervisionLogError(
                "Capability reconciliation exceeds its byte bound"
            )
        with source.open("rb") as handle:
            raw = handle.read(MAX_CAPABILITY_RECONCILIATION_BYTES + 1)
    except OSError as exc:
        raise SupervisionLogError(
            "Capability reconciliation source cannot be read"
        ) from exc
    if len(raw) > MAX_CAPABILITY_RECONCILIATION_BYTES:
        raise SupervisionLogError("Capability reconciliation exceeds its byte bound")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Capability reconciliation is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SupervisionLogError("Capability reconciliation must be an object")
    expected = {
        "schema_version",
        "kind",
        "target_thread_id",
        "mission_root",
        "state_fingerprint",
        "current_revision",
        "implementation_owner_id",
        "reviewer_id",
        "requested_capability",
        "protected_capabilities",
        "selected_architecture_level",
        "accepted_tradeoffs",
        "current_behavior",
        "operator_visible_effects",
        "supported_gaps",
        "completion_posture",
        "evidence",
    }
    if set(value) != expected:
        raise SupervisionLogError(
            "Capability reconciliation has unexpected or missing fields"
        )
    if value.get("schema_version") != 1 or value.get("kind") != CAPABILITY_RECONCILIATION_KIND:
        raise SupervisionLogError("Capability reconciliation kind or schema differs")
    if value.get("target_thread_id") != target_thread:
        raise SupervisionLogError("Capability reconciliation cites another target")
    if value.get("mission_root") != mission_root:
        raise SupervisionLogError("Capability reconciliation cites a stale mission")
    if value.get("state_fingerprint") != state_fingerprint:
        raise SupervisionLogError(
            "Capability reconciliation cites a stale state fingerprint"
        )
    revision = value.get("current_revision")
    if revision != current_revision:
        raise SupervisionLogError(
            "Capability reconciliation cites a stale current revision"
        )
    implementation_owner_value = value.get("implementation_owner_id")
    reviewer_value = value.get("reviewer_id")
    if not isinstance(implementation_owner_value, str) or not isinstance(
        reviewer_value, str
    ):
        raise SupervisionLogError(
            "Capability reconciliation owner identities must be strings"
        )
    implementation_owner = safe_id(
        implementation_owner_value, label="capability implementation owner"
    )
    reviewer = safe_id(reviewer_value, label="capability reviewer")
    if implementation_owner == reviewer:
        raise SupervisionLogError(
            "Capability reconciliation reviewer is not independent of implementation"
        )
    runtime = policy.get("runtime")
    if not isinstance(runtime, Mapping):
        raise SupervisionLogError("Capability reconciliation lacks bound reviewer roles")
    eligible_reviewers = {
        item
        for item in (
            runtime.get("base_reviewer_thread_id"),
            runtime.get("reviewer_thread_id"),
        )
        if isinstance(item, str) and item
    }
    disallowed_reviewers = {
        item
        for item in (
            policy.get("target_thread_id"),
            runtime.get("watcher_thread_id"),
            runtime.get("fix_executor_thread_id"),
        )
        if isinstance(item, str) and item
    }
    if reviewer not in eligible_reviewers or reviewer in disallowed_reviewers:
        raise SupervisionLogError(
            "Capability reconciliation reviewer is not an eligible bound independent role"
        )

    def exact_text(item: Any, *, label: str, maximum: int = 1200) -> str:
        if (
            not isinstance(item, str)
            or not item
            or item != item.strip()
            or len(item) > maximum
        ):
            raise SupervisionLogError(
                f"Capability reconciliation {label} is not exact and bounded"
            )
        return item

    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence or len(evidence) > 32:
        raise SupervisionLogError(
            "Capability reconciliation evidence is not a bounded array"
        )
    evidence_classes = {
        "direct-authority",
        "current-repository",
        "observed-outcome",
        "validation",
        "independent-review",
    }
    evidence_by_id: dict[str, str] = {}
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {
            "evidence_id",
            "evidence_class",
            "source_root",
        }:
            raise SupervisionLogError("Capability reconciliation evidence shape differs")
        evidence_id_value = item.get("evidence_id")
        if not isinstance(evidence_id_value, str):
            raise SupervisionLogError("Capability reconciliation evidence ID must be a string")
        evidence_id = safe_id(evidence_id_value, label="capability evidence ID")
        evidence_class = item.get("evidence_class")
        if evidence_class not in evidence_classes:
            raise SupervisionLogError(
                "Capability reconciliation evidence class is unsupported"
            )
        exact_sha256(item.get("source_root"), label="capability evidence source root")
        if evidence_id in evidence_by_id:
            raise SupervisionLogError("Capability reconciliation repeats evidence")
        evidence_by_id[evidence_id] = str(evidence_class)

    def evidence_ids(item: Any, *, label: str) -> list[str]:
        if not isinstance(item, list) or not item or len(item) > 16:
            raise SupervisionLogError(
                f"Capability reconciliation {label} evidence is not a bounded array"
            )
        result: list[str] = []
        for evidence_id_value in item:
            if not isinstance(evidence_id_value, str):
                raise SupervisionLogError(
                    f"Capability reconciliation {label} evidence ID must be a string"
                )
            evidence_id = safe_id(
                evidence_id_value, label=f"capability {label} evidence ID"
            )
            if evidence_id not in evidence_by_id:
                raise SupervisionLogError(
                    f"Capability reconciliation {label} has dangling evidence"
                )
            result.append(evidence_id)
        if len(result) != len(set(result)):
            raise SupervisionLogError(
                f"Capability reconciliation {label} repeats evidence"
            )
        return result

    def claim(
        item: Any,
        *,
        label: str,
        required_classes: set[str],
    ) -> None:
        if not isinstance(item, dict) or set(item) != {"statement", "evidence_ids"}:
            raise SupervisionLogError(f"Capability reconciliation {label} shape differs")
        exact_text(item.get("statement"), label=f"{label} statement")
        linked = evidence_ids(item.get("evidence_ids"), label=label)
        if not ({evidence_by_id[evidence_id] for evidence_id in linked} & required_classes):
            raise SupervisionLogError(
                f"Capability reconciliation {label} lacks required evidence class"
            )

    claim(
        value.get("requested_capability"),
        label="requested capability",
        required_classes={"direct-authority"},
    )
    for field, classes in (
        ("protected_capabilities", {"direct-authority", "current-repository"}),
        ("accepted_tradeoffs", {"direct-authority", "current-repository"}),
        ("operator_visible_effects", {"observed-outcome"}),
    ):
        items = value.get(field)
        if not isinstance(items, list) or not items or len(items) > 16:
            raise SupervisionLogError(
                f"Capability reconciliation {field} is not a bounded array"
            )
        for index, item in enumerate(items):
            claim(
                item,
                label=f"{field} {index}",
                required_classes=classes,
            )
    claim(
        value.get("current_behavior"),
        label="current behavior",
        required_classes={"observed-outcome"},
    )
    architecture = value.get("selected_architecture_level")
    if not isinstance(architecture, dict) or set(architecture) != {
        "level",
        "owner_ref",
        "evidence_ids",
    }:
        raise SupervisionLogError(
            "Capability reconciliation selected architecture level shape differs"
        )
    exact_text(architecture.get("level"), label="architecture level", maximum=160)
    exact_text(architecture.get("owner_ref"), label="architecture owner", maximum=300)
    architecture_evidence = evidence_ids(
        architecture.get("evidence_ids"), label="selected architecture level"
    )
    if "current-repository" not in {
        evidence_by_id[evidence_id] for evidence_id in architecture_evidence
    }:
        raise SupervisionLogError(
            "Capability reconciliation architecture lacks current repository evidence"
        )
    gaps = value.get("supported_gaps")
    if not isinstance(gaps, list) or len(gaps) > 16:
        raise SupervisionLogError(
            "Capability reconciliation supported_gaps is not a bounded array"
        )
    seen_gap_ids: set[str] = set()
    for gap in gaps:
        if not isinstance(gap, dict) or set(gap) != {
            "gap_id",
            "statement",
            "owner_class",
            "owner_ref",
            "evidence_ids",
        }:
            raise SupervisionLogError("Capability reconciliation gap shape differs")
        gap_id_value = gap.get("gap_id")
        if not isinstance(gap_id_value, str):
            raise SupervisionLogError("Capability reconciliation gap ID must be a string")
        gap_id = safe_id(gap_id_value, label="capability gap ID")
        if gap_id in seen_gap_ids:
            raise SupervisionLogError("Capability reconciliation repeats a gap ID")
        seen_gap_ids.add(gap_id)
        exact_text(gap.get("statement"), label="gap statement", maximum=500)
        if gap.get("owner_class") not in {
            "authoring",
            "implementation",
            "supervision",
            "target-repository",
        }:
            raise SupervisionLogError(
                "Capability reconciliation gap owner class is unsupported"
            )
        exact_text(gap.get("owner_ref"), label="gap owner reference", maximum=300)
        gap_evidence = evidence_ids(gap.get("evidence_ids"), label="supported gap")
        if "observed-outcome" not in {
            evidence_by_id[evidence_id] for evidence_id in gap_evidence
        }:
            raise SupervisionLogError(
                "Capability reconciliation gap lacks observed outcome evidence"
            )
    posture = value.get("completion_posture")
    if posture not in CAPABILITY_RECONCILIATION_POSTURES:
        raise SupervisionLogError("Capability reconciliation posture is unsupported")
    if (posture == "verified") != (not gaps):
        raise SupervisionLogError(
            "Capability reconciliation gap set contradicts its completion posture"
        )
    return value, digest(value)


def cmd_completion_record(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    if policy.get("outcome_completion") != outcome_completion_contract():
        raise SupervisionLogError(
            "Current outcome-completion contract is not bound; run bind first"
        )
    mission = bound_mission(policy)
    if mission is None:
        raise SupervisionLogError("Outcome completion requires an exact bound mission")
    mission_root = exact_sha256(args.mission_root, label="mission root")
    if mission_root != mission["mission_root"]:
        raise SupervisionLogError("Outcome completion cites a stale mission root")
    state_fingerprint = safe_id(
        args.state_fingerprint, label="state fingerprint"
    )
    current_revision = str(args.current_revision)
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", current_revision):
        raise SupervisionLogError("Outcome completion requires an exact current revision")
    if args.model != outcome_completion_contract()["reviewer_model"]:
        raise SupervisionLogError("Outcome completion requires the configured Sol reviewer")
    if args.reasoning not in outcome_completion_contract()["reviewer_reasoning"]:
        raise SupervisionLogError(
            "Outcome completion requires xhigh or max reviewer reasoning"
        )
    evidence_values = [clean(item, label="evidence", maximum=160) for item in args.evidence]
    if not evidence_values or not all(evidence_values):
        raise SupervisionLogError("Outcome completion requires exact source evidence")
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many outcome-completion evidence references")
    reconciliation, reconciliation_root = load_capability_reconciliation(
        args.capability_reconciliation_json,
        target_thread=args.target_thread,
        mission_root=mission_root,
        state_fingerprint=state_fingerprint,
        current_revision=current_revision,
        policy=policy,
    )
    if args.status == "verified" and reconciliation["completion_posture"] != "verified":
        raise SupervisionLogError(
            "Verified completion cannot retain a supported capability gap"
        )
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "",
        "timestamp": utc_now(),
        "target_thread_id": args.target_thread,
        "kind": "check",
        "model": args.model,
        "reasoning": args.reasoning,
        "state_fingerprint": state_fingerprint,
        "status": args.status,
        "severity": "info" if args.status == "verified" else "critical",
        "category": OUTCOME_COMPLETION_CATEGORY,
        "active_block": clean(args.active_block, label="active block", maximum=40),
        "checkpoint": clean(args.checkpoint, label="checkpoint", maximum=160),
        "summary": clean(args.summary, label="summary"),
        "evidence": evidence_values,
        "mission_root": mission_root,
        "policy_sha256": policy["policy_sha256"],
        "capability_reconciliation_reviewer_id": reconciliation["reviewer_id"],
        "capability_reconciliation_implementation_owner_id": reconciliation[
            "implementation_owner_id"
        ],
        "capability_reconciliation_revision": reconciliation["current_revision"],
        "capability_reconciliation_posture": reconciliation["completion_posture"],
        "capability_reconciliation_gap_count": len(reconciliation["supported_gaps"]),
    }
    for field in OUTCOME_COMPLETION_HASH_FIELDS:
        record[field] = (
            reconciliation_root
            if field == "capability_reconciliation_sha256"
            else exact_sha256(getattr(args, field), label=field)
        )
    with append_lock(directory):
        current_events = events(directory / "events.jsonl")
        prior = latest_outcome_completion_record(
            current_events, state_fingerprint=state_fingerprint
        )
        if prior is not None and all(
            prior.get(key) == record.get(key)
            for key in (
                "status",
                "model",
                "reasoning",
                "mission_root",
                "evidence",
                *OUTCOME_COMPLETION_HASH_FIELDS,
            )
        ):
            print(
                json.dumps(
                    {"duplicate": True, "record_id": prior["record_id"]},
                    sort_keys=True,
                )
            )
            return
        record["record_id"] = f"EVT-{len(current_events) + 1:06d}"
        append_event_locked(args, directory, record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def cmd_record(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    if args.kind not in KINDS:
        raise SupervisionLogError("Unsupported event kind")
    if args.status == "resumed" or args.category == SUPERVISION_RESUME_CATEGORY:
        raise SupervisionLogError(
            "Canonical supervision resume must use resume-gate and resume-finalize"
        )
    evidence_values = [
        clean(item, label="evidence", maximum=160) for item in args.evidence
    ]
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
    if getattr(args, "containment", False):
        if args.kind not in {"incident", "steer"}:
            raise SupervisionLogError(
                "Structured containment evidence requires an incident or steer record"
            )
        record["containment"] = containment_envelope_from_args(args, policy)
    if getattr(args, "failure_mode", False):
        if args.kind not in {"incident", "steer", "resolution", "meta-review"}:
            raise SupervisionLogError(
                "Structured failure-mode evidence requires an incident-owned record"
            )
        if args.kind != "incident" and not args.incident_id:
            raise SupervisionLogError(
                "A successor failure-mode record must reference its incident"
            )
        record["failure_mode"] = failure_mode_envelope_from_args(args)
    reusable_lane_inputs = any(
        (
            getattr(args, "reusable_lane_disposition", ""),
            getattr(args, "reusable_lane_owner", ""),
            getattr(args, "reusable_lane_rationale", ""),
            getattr(args, "reusable_lane_evidence", []),
        )
    )
    if reusable_lane_inputs:
        if args.kind not in {"resolution", "meta-review"} or not args.incident_id:
            raise SupervisionLogError(
                "Reusable lane disposition requires an incident-owned effectiveness or resolution record"
            )
        record["reusable_lane"] = reusable_lane_envelope_from_args(args)
    with append_lock(directory):
        current_events = events(directory / "events.jsonl")
        if args.kind == "lifecycle" and record["status"] == "completed":
            if successor_transition_heads(current_events, open_only=True):
                raise SupervisionLogError(
                    "Completed lifecycle rejected: an open successor transition "
                    "has not reached work-started"
                )
            active_events = mission_scoped_events(directory, policy, current_events)
            if mission_activation_heads(active_events, open_only=True):
                raise SupervisionLogError(
                    "Completed lifecycle rejected: current mission first work "
                    "has not started"
                )
            completion_record = latest_outcome_completion_record(
                current_events, state_fingerprint=record["state_fingerprint"]
            )
            completion_permitted, completion_reason = assess_outcome_completion_record(
                completion_record,
                policy=policy,
                state_fingerprint=record["state_fingerprint"],
            )
            if not completion_permitted:
                raise SupervisionLogError(
                    f"Completed lifecycle rejected: {completion_reason}"
                )
            record["outcome_completion_record_id"] = completion_record["record_id"]
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
        if (
            policy.get("execution_economy") == execution_economy_contract()
            and requires_reusable_lane_disposition(current_events, record)
            and "reusable_lane" not in record
        ):
            raise SupervisionLogError(
                "Supported execution-economy incident effectiveness or closure requires an explicit reusable lane disposition"
            )
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

        append_event_locked(args, directory, record)
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


def is_routing_only_incident_record(item: dict[str, Any]) -> bool:
    if item.get("kind") != "escalation":
        return False
    category = item.get("category")
    return (
        item.get("status") == "routed"
        or category == "incident-routing"
        or isinstance(category, str) and category.endswith("-routing")
    )


def is_substantive_incident_record(
    item: dict[str, Any], current_incident_id: str
) -> bool:
    return (
        item.get("incident_id") == current_incident_id
        and item.get("kind") != "notification"
        and not is_routing_only_incident_record(item)
        and not (
            item.get("kind") == "check"
            and item.get("category") == "target-read-availability"
        )
    )


def is_terminal_incident_record(
    item: dict[str, Any], current_incident_id: str
) -> bool:
    return is_substantive_incident_record(item, current_incident_id) and (
        item.get("status") in TERMINAL_INCIDENT_STATUSES
        or item.get("notice_disposition") == "terminal"
    )


def sent_gmail_notification_links_source(
    item: dict[str, Any], source_record: str
) -> bool:
    if (
        item.get("kind") != "notification"
        or item.get("status") != "sent"
        or item.get("category") != "gmail"
    ):
        return False
    evidence = item.get("evidence", [])
    if isinstance(evidence, list) and source_record in evidence:
        return True
    return item.get("dedup_key") == f"gmail:{source_record}"


def prior_correction_notice_remains_current(
    all_events: list[dict[str, Any]],
    current_incident_id: str,
    source_record: str,
    incident_source_record_ids: set[str],
) -> bool:
    source_position = next(
        (
            position
            for position, item in enumerate(all_events)
            if item.get("record_id") == source_record
        ),
        len(all_events),
    )
    if source_position == len(all_events):
        return False
    source = all_events[source_position]
    source_fingerprint = source.get("state_fingerprint")
    if (
        not is_substantive_incident_record(source, current_incident_id)
        or source.get("notice_disposition") != "correction-issued"
        or not isinstance(source_fingerprint, str)
        or not source_fingerprint
        or source.get("kind") == "steer"
    ):
        return False

    for prior_position in range(source_position - 1, -1, -1):
        prior_source = all_events[prior_position]
        if (
            not is_substantive_incident_record(
                prior_source, current_incident_id
            )
            or prior_source.get("notice_disposition") != "correction-issued"
            or prior_source.get("state_fingerprint") != source_fingerprint
            or not isinstance(prior_source.get("record_id"), str)
        ):
            continue
        prior_source_record = prior_source["record_id"]
        receipt_exists = any(
            notification_matches_incident(
                item, current_incident_id, incident_source_record_ids
            )
            and sent_gmail_notification_links_source(item, prior_source_record)
            for item in all_events[prior_position + 1 : source_position]
        )
        if not receipt_exists:
            continue
        materially_different_correction = any(
            is_substantive_incident_record(item, current_incident_id)
            and item.get("notice_disposition") == "correction-issued"
            and (
                item.get("kind") == "steer"
                or isinstance(item.get("state_fingerprint"), str)
                and item.get("state_fingerprint")
                and item.get("state_fingerprint") != source_fingerprint
            )
            for item in all_events[prior_position + 1 : source_position]
        )
        if not materially_different_correction:
            return True
    return False


def prior_terminal_outcome_remains_current(
    all_events: list[dict[str, Any]],
    current_incident_id: str,
    source_record: str,
    incident_source_record_ids: set[str],
) -> bool:
    source_position = next(
        (
            position
            for position, item in enumerate(all_events)
            if item.get("record_id") == source_record
        ),
        len(all_events),
    )
    terminal_source_positions = {
        item.get("record_id"): position
        for position, item in enumerate(all_events[:source_position])
        if is_terminal_incident_record(item, current_incident_id)
    }
    for receipt_position in range(source_position - 1, -1, -1):
        item = all_events[receipt_position]
        if (
            item.get("status") != "sent"
            or not notification_matches_incident(
                item, current_incident_id, incident_source_record_ids
            )
        ):
            continue
        evidence = item.get("evidence", [])
        source_references = {
            reference for reference in evidence if isinstance(reference, str)
        }
        dedup_key = item.get("dedup_key")
        if isinstance(dedup_key, str) and dedup_key.startswith("gmail:"):
            source_references.add(dedup_key.removeprefix("gmail:"))
        linked_terminal_positions = [
            terminal_source_positions[reference]
            for reference in source_references
            if reference in terminal_source_positions
            and terminal_source_positions[reference] < receipt_position
        ]
        if (
            not linked_terminal_positions
            and item.get("notice_disposition") != "terminal"
        ):
            continue
        terminal_position = (
            max(linked_terminal_positions)
            if linked_terminal_positions
            else max(
                (
                    position
                    for position in terminal_source_positions.values()
                    if position < receipt_position
                ),
                default=receipt_position,
            )
        )
        return not any(
            is_substantive_incident_record(candidate, current_incident_id)
            and not is_terminal_incident_record(candidate, current_incident_id)
            for candidate in all_events[terminal_position + 1 : source_position]
        )
    return False


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
    exact_source_duplicate = any(
        sent_gmail_notification_links_source(item, source_record)
        for item in incident_notifications
    )
    user_action_required = args.user_action_required == "yes"
    repeated_terminal = (
        args.notice_disposition == "terminal"
        and not exact_source_duplicate
        and prior_terminal_outcome_remains_current(
            all_events,
            current_incident_id,
            source_record,
            incident_source_record_ids,
        )
    )
    repeated_correction = (
        args.notice_disposition == "correction-issued"
        and not exact_source_duplicate
        and args.severity != "critical"
        and not user_action_required
        and prior_correction_notice_remains_current(
            all_events,
            current_incident_id,
            source_record,
            incident_source_record_ids,
        )
    )
    duplicate = exact_source_duplicate or repeated_terminal or repeated_correction
    previously_alerted = bool(incident_notifications)

    if exact_source_duplicate:
        send_now = False
        channel = "none"
        reason = "An outcome for this source record is already in the outbound ledger."
        banner = None
    elif repeated_terminal:
        send_now = False
        channel = "none"
        reason = (
            "A sent terminal outcome already covers this incident and no "
            "substantive nonterminal record reopened it."
        )
        banner = None
    elif repeated_correction:
        send_now = False
        channel = "none"
        reason = (
            "A sent correction-issued outcome already covers this incident "
            "and target fingerprint without an intervening new correction."
        )
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


def terminal_stop_head_snapshot(
    directory: Path,
    policy: Mapping[str, Any],
    all_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    current_policy = dict(policy)
    binding = bound_mission(current_policy)
    if binding is None:
        active_events = [dict(item) for item in all_events]
    else:
        roots = policy_mission_roots(directory)
        policy_sha256 = current_policy.get("policy_sha256")
        if isinstance(policy_sha256, str):
            roots[policy_sha256] = str(binding["mission_root"])
        active_events = [
            dict(item)
            for item in all_events
            if roots.get(str(item.get("policy_sha256", "")))
            == str(binding["mission_root"])
        ]
    incident_heads: dict[str, dict[str, Any]] = {}
    decision_heads: dict[str, dict[str, Any]] = {}
    for item in active_events:
        incident_id = item.get("incident_id")
        if incident_id and is_substantive_incident_record(item, str(incident_id)):
            incident_heads[str(incident_id)] = item
        if item.get("kind") == "decision" and item.get("decision_id"):
            decision_heads[str(item["decision_id"])] = item
    open_incident_ids = sorted(
        incident_id
        for incident_id, item in incident_heads.items()
        if not is_terminal_incident_record(item, incident_id)
    )
    open_decision_ids = sorted(
        decision_id
        for decision_id, item in decision_heads.items()
        if item.get("phase") != "target-acknowledged"
    )
    open_transitions = successor_transition_heads(
        [dict(item) for item in all_events], open_only=True
    )
    open_activations = mission_activation_heads(active_events, open_only=True)
    event_head = all_events[-1].get("record_sha256") if all_events else None
    if event_head is not None and (
        not isinstance(event_head, str) or not SHA256.fullmatch(event_head)
    ):
        raise SupervisionLogError("Terminal stop event head is invalid")
    return {
        "event_count": len(all_events),
        "event_head": event_head,
        "open_incident_ids": open_incident_ids,
        "open_decision_ids": open_decision_ids,
        "open_successor_transitions": list(open_transitions.values()),
        "open_mission_activations": list(open_activations.values()),
    }


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
        raise SupervisionLogError(
            "Lifecycle source record does not match requested state"
        )
    if state_fingerprint and source.get("state_fingerprint") != state_fingerprint:
        raise SupervisionLogError("Lifecycle source record fingerprint differs")

    stop_heads = terminal_stop_head_snapshot(directory, policy, all_events)
    open_transitions = stop_heads["open_successor_transitions"]
    transition_stop_conflict = bool(
        open_transitions and lifecycle_state in {"completed", "paused", "stopped"}
    )
    open_activations = stop_heads["open_mission_activations"]
    activation_stop_conflict = bool(
        open_activations and lifecycle_state in {"completed", "paused", "stopped"}
    )
    incident_stop_conflict = bool(
        stop_heads["open_incident_ids"] and lifecycle_state == "completed"
    )
    decision_stop_conflict = bool(
        stop_heads["open_decision_ids"] and lifecycle_state == "completed"
    )
    terminal_stop_conflict = bool(
        incident_stop_conflict
        or decision_stop_conflict
        or transition_stop_conflict
        or activation_stop_conflict
    )

    completion_permitted = True
    completion_record_id: str | None = None
    completion_reason = "The lifecycle state does not require outcome completion proof."
    if lifecycle_state == "completed":
        completion_record = latest_outcome_completion_record(
            all_events, state_fingerprint=source.get("state_fingerprint", "")
        )
        completion_permitted, completion_reason = assess_outcome_completion_record(
            completion_record,
            policy=policy,
            state_fingerprint=source.get("state_fingerprint", ""),
        )
        completion_record_id = (
            str(completion_record.get("record_id"))
            if completion_record is not None
            else None
        )
        if source.get("outcome_completion_record_id") != completion_record_id:
            completion_permitted = False
            completion_reason = (
                "The completed lifecycle is not bound to the current "
                "observable-outcome record."
            )
        if incident_stop_conflict:
            completion_permitted = False
            completion_reason = (
                "A current substantive incident remains open; terminal source stop is prohibited."
            )
        elif decision_stop_conflict:
            completion_permitted = False
            completion_reason = (
                "A current decision remains open; terminal source stop is prohibited."
            )
        elif transition_stop_conflict:
            completion_permitted = False
            completion_reason = (
                "An open successor transition has not reached work-started; "
                "handoff is not completion of the governing requested scope."
            )
        elif activation_stop_conflict:
            completion_permitted = False
            completion_reason = (
                "The current mission has not reached exact first-work-start "
                "evidence after its binding."
            )

    terminal_reporting = bool(
        lifecycle_state == "completed"
        and policy.get("reports", {}).get("terminal", {}).get("enabled")
    )
    terminal_delivery: Mapping[str, Any] | None = None
    terminal_reports_delivered = False
    terminal_report_reason = "The lifecycle state does not require terminal reports."
    terminal_report_set_id: str | None = None
    if terminal_reporting and completion_permitted:
        requested_terminal_report_set = getattr(args, "terminal_report_set_id", None)
        if requested_terminal_report_set:
            requested_terminal_report_set = safe_id(
                requested_terminal_report_set,
                label="terminal report set ID",
            )
        terminal_delivery = latest_terminal_delivery(
            all_events,
            lifecycle_record_id=source_record,
            report_set_id=requested_terminal_report_set,
        )
        if terminal_delivery is None:
            terminal_report_reason = "Generate, verify, and email both terminal PDF reports before pausing supervision."
        else:
            terminal_report_set_id = str(terminal_delivery.get("report_set_id", ""))
            try:
                verified_terminal = verify_terminal_report_set(
                    directory, terminal_report_set_id
                )
                terminal_reports_delivered = bool(
                    terminal_delivery_is_current(terminal_delivery, verified_terminal)
                    and terminal_delivery.get("state_fingerprint")
                    == source.get("state_fingerprint")
                )
            except (SupervisionLogError, OSError, json.JSONDecodeError) as exc:
                terminal_report_reason = f"Terminal report verification failed: {exc}"
            else:
                terminal_report_reason = (
                    "Both terminal PDF reports were verified and delivered on the bound Gmail thread."
                    if terminal_reports_delivered
                    else "Terminal report delivery no longer matches the verified attachment set."
                )

    priority_lifecycle = lifecycle_state in PRIORITY_LIFECYCLE_STATES
    category = (
        TERMINAL_REPORT_DELIVERY_CATEGORY
        if terminal_reporting
        else "gmail-priority-lifecycle"
        if priority_lifecycle
        else "gmail-lifecycle"
    )
    notification_key = f"{category}:{source_record}"
    duplicate = (
        terminal_reports_delivered
        if terminal_reporting
        else any(
            item.get("kind") == "notification"
            and item.get("category") == category
            and (
                source_record in item.get("evidence", [])
                or item.get("dedup_key") == notification_key
            )
            for item in all_events
        )
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
    send_now = (
        enabled and not duplicate and completion_permitted and not terminal_reporting
    )
    supervision_pause_permitted = bool(
        lifecycle_state == "completed"
        and completion_permitted
        and not terminal_stop_conflict
        and (not terminal_reporting or terminal_reports_delivered)
    )
    if not completion_permitted:
        reason = completion_reason
    elif terminal_reporting and not terminal_reports_delivered:
        reason = terminal_report_reason
    elif terminal_reporting:
        reason = terminal_report_reason
    elif duplicate:
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
                    else "primary-status"
                    if send_now
                    else "none"
                ),
                "completion_action": (
                    MISSION_ACTIVATION_START_ACTION
                    if activation_stop_conflict
                    else "resume-successor-transition"
                    if transition_stop_conflict
                    else "open-critical-false-completion-review"
                    if not completion_permitted
                    else "prepare-finalize-verify-email-and-record-terminal-reports"
                    if terminal_reporting and not terminal_reports_delivered
                    else "none"
                ),
                "completion_permitted": completion_permitted,
                "completion_record_id": completion_record_id,
                "duplicate": duplicate,
                "decision_context_required": decision_context_required,
                "required_decision_fields": (
                    notification_config.get("required_decision_fields", [])
                    if decision_context_required
                    else []
                ),
                "lifecycle_state": lifecycle_state,
                "event_count": stop_heads["event_count"],
                "event_head": stop_heads["event_head"],
                "notification_category": category,
                "notification_dedup_key": notification_key,
                "pause_automation_ids": (
                    expected_terminal_automation_ids(policy)
                    if supervision_pause_permitted
                    else []
                ),
                "policy_sha256": policy["policy_sha256"],
                "reason": reason,
                "reply_message_id": (
                    notification_config.get("reply_message_id")
                    if send_now or terminal_reporting
                    else None
                ),
                "send_now": send_now,
                "source_record": source_record,
                "source_stop_permitted": not terminal_stop_conflict,
                "state_fingerprint": source.get("state_fingerprint", ""),
                "open_incident_ids": stop_heads["open_incident_ids"],
                "open_decision_ids": stop_heads["open_decision_ids"],
                "open_mission_activations": open_activations,
                "open_successor_transitions": open_transitions,
                "supervision_pause_permitted": supervision_pause_permitted,
                "terminal_email_recipient": (
                    notification_config.get("recipient") if terminal_reporting else None
                ),
                "terminal_email_subject": (
                    notification_config.get("subject") if terminal_reporting else None
                ),
                "terminal_report_set_id": terminal_report_set_id,
                "terminal_reports_delivered": terminal_reports_delivered,
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


def mission_activation_identity(
    *,
    target_thread: str,
    mission_root: str,
    mission_source_record: str,
    activation_policy_sha256: str,
    first_eligible_work: str,
) -> str:
    material = {
        "kind": "same-target-mission-activation",
        "target_thread_id": target_thread,
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "activation_policy_sha256": activation_policy_sha256,
        "first_eligible_work": first_eligible_work,
    }
    return f"MACT-{digest(material)[:24].upper()}"


def mission_activation_pending_record(
    *,
    target_thread: str,
    mission_binding: Mapping[str, Any],
    activation_policy_sha256: str,
    first_eligible_work: str,
    evidence: list[str],
) -> dict[str, Any]:
    mission_root = exact_sha256(
        mission_binding.get("mission_root"), label="activation mission root"
    )
    mission_source_record = safe_id(
        str(mission_binding.get("mission_source_record", "")),
        label="activation mission source record",
    )
    policy_sha256 = exact_sha256(
        activation_policy_sha256, label="activation policy SHA-256"
    )
    work_identity = clean(
        first_eligible_work, label="first eligible work", maximum=160
    )
    if not work_identity:
        raise SupervisionLogError("Mission activation requires first eligible work")
    return {
        "schema_version": 1,
        "record_id": "",
        "timestamp": utc_now(),
        "target_thread_id": target_thread,
        "kind": "mission-activation",
        "activation_id": mission_activation_identity(
            target_thread=target_thread,
            mission_root=mission_root,
            mission_source_record=mission_source_record,
            activation_policy_sha256=policy_sha256,
            first_eligible_work=work_identity,
        ),
        "phase": "pending",
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "activation_policy_sha256": policy_sha256,
        "first_eligible_work": work_identity,
        "source_record": "",
        "evidence": evidence,
        "policy_sha256": policy_sha256,
    }


def mission_activation_events(
    all_events: list[dict[str, Any]], activation_id: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in all_events
        if item.get("kind") == "mission-activation"
        and item.get("activation_id") == activation_id
    ]


def mission_activation_heads(
    all_events: list[dict[str, Any]], *, open_only: bool = False
) -> dict[str, dict[str, Any]]:
    heads: dict[str, dict[str, Any]] = {}
    for item in all_events:
        activation_id = item.get("activation_id")
        if item.get("kind") == "mission-activation" and isinstance(
            activation_id, str
        ):
            heads[activation_id] = item
    if not open_only:
        return heads
    return {
        activation_id: item
        for activation_id, item in heads.items()
        if item.get("phase") != "work-started"
    }


def cmd_mission_activation_start(args: argparse.Namespace) -> None:
    directory, _ = load_policy(args)
    mission_root = exact_sha256(args.mission_root, label="activation mission root")
    activation_policy_sha256 = exact_sha256(
        args.activation_policy_sha256, label="activation policy SHA-256"
    )
    first_eligible_work = clean(
        args.first_eligible_work, label="first eligible work", maximum=160
    )
    if not first_eligible_work:
        raise SupervisionLogError("Mission activation requires first eligible work")
    source_record = safe_id(
        args.source_record, label="mission activation source record"
    )
    evidence_values = [
        clean(item, label="mission activation evidence", maximum=160)
        for item in args.evidence
    ]
    if not evidence_values or not all(evidence_values):
        raise SupervisionLogError(
            "Mission activation work-started requires exact nonempty evidence"
        )
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many mission activation evidence references")

    with append_lock(directory):
        policy = read_json(directory / "policy.json")
        validate_policy(policy)
        if policy.get("target_thread_id") != args.target_thread:
            raise SupervisionLogError("Policy belongs to a different target")
        mission = bound_mission(policy)
        if mission is None or mission.get("mission_root") != mission_root:
            raise SupervisionLogError(
                "Mission activation cites a stale or different mission root"
            )
        all_events = events(directory / "events.jsonl")
        active_events = mission_scoped_events(directory, policy, all_events)
        heads = mission_activation_heads(active_events)
        candidates = [
            item
            for item in heads.values()
            if item.get("mission_root") == mission_root
            and item.get("mission_source_record")
            == mission.get("mission_source_record")
        ]
        if len(candidates) != 1:
            raise SupervisionLogError(
                "Current mission has no unique activation obligation"
            )
        head = candidates[0]
        if head.get("phase") not in MISSION_ACTIVATION_PHASES:
            raise SupervisionLogError("Mission activation phase is invalid")
        if head.get("activation_policy_sha256") != activation_policy_sha256:
            raise SupervisionLogError("Mission activation policy identity differs")
        if head.get("first_eligible_work") != first_eligible_work:
            raise SupervisionLogError("Mission activation first work identity differs")

        source_index = next(
            (
                index
                for index, item in enumerate(all_events)
                if item.get("record_id") == source_record
            ),
            None,
        )
        if source_index is None:
            raise SupervisionLogError(
                "Mission activation source record does not exist"
            )
        source = all_events[source_index]
        records = mission_activation_events(
            all_events, str(head["activation_id"])
        )
        pending = records[0] if records else None
        if pending is None or pending.get("phase") != "pending":
            raise SupervisionLogError("Mission activation lacks its pending binding")
        pending_index = next(
            index
            for index, item in enumerate(all_events)
            if item.get("record_id") == pending.get("record_id")
        )
        if source_index <= pending_index:
            raise SupervisionLogError(
                "Mission activation cannot use pre-binding evidence"
            )
        if source.get("target_thread_id") != args.target_thread:
            raise SupervisionLogError(
                "Mission activation source belongs to another target"
            )
        source_root = policy_mission_roots(directory).get(
            str(source.get("policy_sha256", ""))
        )
        if source_root != mission_root:
            raise SupervisionLogError(
                "Mission activation source belongs to another mission"
            )
        source_evidence = source.get("evidence")
        if (
            not isinstance(source_evidence, list)
            or not all(isinstance(item, str) for item in source_evidence)
            or not set(evidence_values) <= set(source_evidence)
        ):
            raise SupervisionLogError(
                "Mission activation evidence is not bound to its source record"
            )

        record = {
            "schema_version": 1,
            "record_id": "",
            "timestamp": utc_now(),
            "target_thread_id": args.target_thread,
            "kind": "mission-activation",
            "activation_id": head["activation_id"],
            "phase": "work-started",
            "mission_root": mission_root,
            "mission_source_record": mission["mission_source_record"],
            "activation_policy_sha256": activation_policy_sha256,
            "first_eligible_work": first_eligible_work,
            "source_record": source_record,
            "evidence": evidence_values,
            "policy_sha256": policy["policy_sha256"],
        }
        if head.get("phase") == "work-started":
            if all(
                head.get(field) == record.get(field)
                for field in (
                    "activation_id",
                    "phase",
                    "mission_root",
                    "mission_source_record",
                    "activation_policy_sha256",
                    "first_eligible_work",
                    "source_record",
                    "evidence",
                )
            ):
                print(
                    json.dumps(
                        {"duplicate": True, "record_id": head["record_id"]},
                        sort_keys=True,
                    )
                )
                return
            raise SupervisionLogError(
                "Mission activation already closed with different evidence"
            )
        record["record_id"] = f"EVT-{len(all_events) + 1:06d}"
        append_event_locked(args, directory, record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def successor_transition_events(
    all_events: list[dict[str, Any]], transition_id: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in all_events
        if item.get("kind") == "successor-transition"
        and item.get("transition_id") == transition_id
    ]


def successor_transition_heads(
    all_events: list[dict[str, Any]], *, open_only: bool = False
) -> dict[str, dict[str, Any]]:
    heads: dict[str, dict[str, Any]] = {}
    for item in all_events:
        transition_id = item.get("transition_id")
        if item.get("kind") == "successor-transition" and isinstance(
            transition_id, str
        ):
            heads[transition_id] = item
    if not open_only:
        return heads
    return {
        transition_id: item
        for transition_id, item in heads.items()
        if item.get("phase") != "work-started"
    }


def validate_successor_transition(
    prior: dict[str, Any] | None,
    record: dict[str, Any],
) -> None:
    phase = str(record["phase"])
    phase_index = SUCCESSOR_TRANSITION_PHASES.index(phase)
    if prior is None:
        if phase != "required":
            raise SupervisionLogError("A successor transition must begin required")
    else:
        prior_phase = str(prior.get("phase", ""))
        if prior_phase not in SUCCESSOR_TRANSITION_PHASES:
            raise SupervisionLogError("Prior successor transition phase is invalid")
        prior_index = SUCCESSOR_TRANSITION_PHASES.index(prior_phase)
        if phase_index != prior_index + 1:
            raise SupervisionLogError(
                f"Successor transition {prior_phase} -> {phase} is not allowed"
            )
        for field in SUCCESSOR_TRANSITION_IDENTITY_FIELDS:
            if prior.get(field) != record.get(field):
                raise SupervisionLogError(
                    f"Successor transition must preserve {field.replace('_', ' ')}"
                )

    required_by_phase = {
        "successor-created": ("successor_thread_id",),
        "successor-bound": (
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
        ),
        "handoff-sent": (
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
            "handoff_record",
        ),
        "target-acknowledged": (
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
            "handoff_record",
            "acknowledgement_record",
        ),
        "work-started": (
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
            "handoff_record",
            "acknowledgement_record",
            "started_block",
        ),
    }
    expected_fields = required_by_phase.get(phase, ())
    for field in expected_fields:
        if not record.get(field):
            raise SupervisionLogError(
                f"{phase} requires {field.replace('_', ' ')}"
            )
    all_successor_fields = {
        field
        for fields in required_by_phase.values()
        for field in fields
    }
    allowed_successor_fields = set(expected_fields)
    for field in all_successor_fields - allowed_successor_fields:
        if record.get(field):
            raise SupervisionLogError(
                f"{phase} cannot claim later {field.replace('_', ' ')}"
            )
    if prior is not None:
        for field in all_successor_fields:
            prior_value = prior.get(field, "")
            if prior_value and record.get(field) != prior_value:
                raise SupervisionLogError(
                    f"Successor transition cannot change {field.replace('_', ' ')}"
                )
    if phase == "work-started" and record.get("started_block") != record.get(
        "first_eligible_block"
    ):
        raise SupervisionLogError(
            "Work must start at the transition's first eligible Block"
        )


def cmd_successor_transition_record(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    transition_id = safe_id(args.transition_id, label="successor transition ID")
    evidence_values = [
        clean(item, label="successor transition evidence", maximum=160)
        for item in args.evidence
    ]
    if not evidence_values or not all(evidence_values):
        raise SupervisionLogError(
            "Successor transition records require exact nonempty evidence"
        )
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many successor transition evidence references")
    authority_source_class = args.governing_authority_source_class
    if authority_source_class not in DIRECT_AUTHORITY_SOURCE_CLASSES:
        raise SupervisionLogError(
            "A successor implementation transition requires governing direct authority"
        )
    authority_source_record = safe_id(
        args.governing_authority_source_record,
        label="governing authority source record",
    )
    tracker_source_record = clean(
        args.tracker_source_record,
        label="tracker source record",
        maximum=160,
    )
    if not tracker_source_record:
        raise SupervisionLogError("Tracker source record is required")
    requested_block_range = clean(
        args.requested_block_range,
        label="requested Block range",
        maximum=80,
    )
    first_eligible_block = clean(
        args.first_eligible_block,
        label="first eligible Block",
        maximum=40,
    )
    if not requested_block_range or not first_eligible_block:
        raise SupervisionLogError(
            "Successor transition requires its Block range and first eligible Block"
        )

    successor_thread_id = clean(
        args.successor_thread, label="successor thread ID", maximum=128
    )
    successor_group_id = clean(
        args.successor_group_id, label="successor group ID", maximum=128
    )
    handoff_record = clean(
        args.handoff_record, label="handoff record", maximum=128
    )
    acknowledgement_record = clean(
        args.acknowledgement_record,
        label="acknowledgement record",
        maximum=128,
    )
    for label, value in (
        ("successor thread ID", successor_thread_id),
        ("successor group ID", successor_group_id),
        ("handoff record", handoff_record),
        ("acknowledgement record", acknowledgement_record),
    ):
        if value:
            safe_id(value, label=label)
    successor_mission_root = clean(
        args.successor_mission_root,
        label="successor mission root",
        maximum=64,
    )
    if successor_mission_root:
        successor_mission_root = exact_sha256(
            successor_mission_root, label="successor mission root"
        )
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "",
        "timestamp": parse_time(args.now).isoformat(),
        "target_thread_id": args.target_thread,
        "kind": "successor-transition",
        "transition_id": transition_id,
        "phase": args.phase,
        "tracker_sha256": exact_sha256(
            args.tracker_sha256, label="tracker SHA-256"
        ),
        "tracker_source_record": tracker_source_record,
        "requested_block_range": requested_block_range,
        "first_eligible_block": first_eligible_block,
        "source_mission_root": exact_sha256(
            args.source_mission_root, label="source mission root"
        ),
        "governing_authority_source_class": authority_source_class,
        "governing_authority_source_record": authority_source_record,
        "successor_thread_id": successor_thread_id,
        "successor_mission_root": successor_mission_root,
        "successor_group_id": successor_group_id,
        "handoff_record": handoff_record,
        "acknowledgement_record": acknowledgement_record,
        "started_block": clean(
            args.started_block, label="started Block", maximum=40
        ),
        "state_fingerprint": clean(
            args.state_fingerprint,
            label="state fingerprint",
            maximum=128,
        ),
        "evidence": evidence_values,
        "policy_sha256": policy["policy_sha256"],
    }
    with append_lock(directory):
        all_events = events(directory / "events.jsonl")
        records = successor_transition_events(all_events, transition_id)
        prior = records[-1] if records else None
        if prior is not None and all(
            prior.get(field) == record.get(field)
            for field in (
                "phase",
                *SUCCESSOR_TRANSITION_IDENTITY_FIELDS,
                "successor_thread_id",
                "successor_mission_root",
                "successor_group_id",
                "handoff_record",
                "acknowledgement_record",
                "started_block",
                "state_fingerprint",
                "evidence",
            )
        ):
            print(
                json.dumps(
                    {"duplicate": True, "record_id": prior["record_id"]},
                    sort_keys=True,
                )
            )
            return
        validate_successor_transition(prior, record)
        record["record_id"] = f"EVT-{len(all_events) + 1:06d}"
        append_event_locked(args, directory, record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def cmd_successor_transition_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    transition_id = safe_id(args.transition_id, label="successor transition ID")
    records = successor_transition_events(
        events(directory / "events.jsonl"), transition_id
    )
    if not records:
        raise SupervisionLogError("Successor transition does not exist")
    head = records[-1]
    phase = str(head["phase"])
    if phase == "required":
        if args.task_creation_authority == "available":
            next_action = "create-successor-task"
            authority_required = False
        else:
            next_action = "keep-open-await-direct-task-creation-authority"
            authority_required = True
    else:
        authority_required = False
        next_action = {
            "successor-created": "bind-successor-mission-and-isolated-supervision",
            "successor-bound": "send-exact-handoff",
            "handoff-sent": "obtain-target-acknowledgement",
            "target-acknowledged": "start-first-eligible-block",
            "work-started": "continue-successor-and-close-transition-incident",
        }[phase]
    source_stop_permitted = phase == "work-started"
    print(
        json.dumps(
            {
                "transition_id": transition_id,
                "phase": phase,
                "transition_open": not source_stop_permitted,
                "source_stop_permitted": source_stop_permitted,
                "required_source_posture": (
                    "transition-satisfied" if source_stop_permitted else "in-progress"
                ),
                "next_action": next_action,
                "direct_task_creation_authority_required": authority_required,
                "human_input_required": authority_required,
                "task_creation_authority": args.task_creation_authority,
                "failure_mode_if_stopped": "handoff-without-continuation",
                "tracker_sha256": head["tracker_sha256"],
                "tracker_source_record": head["tracker_source_record"],
                "successor_thread_id": head.get("successor_thread_id") or None,
                "successor_mission_root": head.get("successor_mission_root") or None,
                "successor_group_id": head.get("successor_group_id") or None,
                "first_eligible_block": head["first_eligible_block"],
                "policy_sha256": policy["policy_sha256"],
                "record_id": head["record_id"],
            },
            sort_keys=True,
        )
    )


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
    mission_impact = mission_impact_from_args(args, policy)
    if (
        classification == "reserved-authority"
        and mission_impact["authority_source_class"]
        not in DIRECT_AUTHORITY_SOURCE_CLASSES
    ):
        raise SupervisionLogError(
            "Reserved authority requires an exact direct-user, system, repository, or tracker source"
        )
    if (
        mission_impact["impact_class"] in {"goal-blocking", "goal-reversing"}
        or mission_impact["ordinary_means_disabled"] is True
    ):
        if (
            mission_impact["authority_source_class"]
            not in DIRECT_AUTHORITY_SOURCE_CLASSES
            or mission_impact["independent_mission_review"] is not True
        ):
            raise SupervisionLogError(
                "Consequential decisions require direct authority and independent mission-level review"
            )
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
        if prior is not None:
            prior_mission_fields = [
                field in prior for field in MISSION_IMPACT_FIELDS
            ]
            if any(prior_mission_fields) and not all(prior_mission_fields):
                raise SupervisionLogError(
                    "Legacy decision mission provenance is incomplete"
                )
            if all(prior_mission_fields):
                for field in MISSION_IMPACT_FIELDS:
                    if prior.get(field) != mission_impact[field]:
                        raise SupervisionLogError(
                            "Decision transitions must preserve mission impact and authority provenance"
                        )
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
            and all(
                prior.get(field) == mission_impact[field]
                for field in MISSION_IMPACT_FIELDS
            )
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
            **mission_impact,
        }
        append_event_locked(args, directory, record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def decision_notification(
    policy: dict[str, Any],
    all_events: list[dict[str, Any]],
    head: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    phase = ""
    if action == "challenge-mission-provenance":
        phase = ""
    elif head["classification"] == "delegable":
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
    alignment_contract = alignment_operating_contract()
    meta_charter = mission_meta_charter_profile()
    binding = bound_mission(policy)
    mission_binding_valid = bool(
        binding is not None and head.get("mission_root") == binding["mission_root"]
    )
    authority_source_class = str(head.get("authority_source_class", ""))
    authority_provenance_valid = bool(
        authority_source_class in AUTHORITY_SOURCE_CLASSES
        and head.get("authority_source_record")
        and (
            classification != "reserved-authority"
            or authority_source_class in DIRECT_AUTHORITY_SOURCE_CLASSES
        )
    )
    impact_class = str(head.get("impact_class", ""))
    mission_challenge_valid = bool(
        (
            impact_class not in {"goal-blocking", "goal-reversing"}
            and head.get("ordinary_means_disabled") is not True
        )
        or (
            authority_source_class in DIRECT_AUTHORITY_SOURCE_CLASSES
            and head.get("independent_mission_review") is True
        )
    )
    consequential = bool(
        classification in {"missing-fact", "reserved-authority"}
        or impact_class in {"goal-blocking", "goal-reversing"}
        or head.get("ordinary_means_disabled") is True
    )
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
    if consequential and not (
        mission_binding_valid
        and authority_provenance_valid
        and mission_challenge_valid
    ):
        action = "challenge-mission-provenance"
    next_attempt = attempt + 1 if action == "start-sol-max-attempt" else attempt
    blocking_permitted = bool(
        phase in {"handoff-sent", "target-acknowledged"}
        and head.get("outcome") == "safe-deferred"
        and not safe_work
        and classification in {"missing-fact", "reserved-authority"}
        and mission_binding_valid
        and authority_provenance_valid
        and mission_challenge_valid
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
        "mission_binding_valid": mission_binding_valid,
        "authority_provenance_valid": authority_provenance_valid,
        "mission_challenge_valid": mission_challenge_valid,
        "consequential": consequential,
        "alignment_operating_mode": alignment_contract["mode"],
        "mission_binding_mode": (
            binding.get("mission_derivation", {}).get(
                "mode", "legacy-explicit-exact-root"
            )
            if binding is not None
            else "unbound"
        ),
        "mission_meta_charter": alignment_contract["meta_charter"],
        "target_native_alignment_required": False,
        "target_native_alignment_role": alignment_contract[
            "target_native_alignment_role"
        ],
        "missing_target_alignment_posture": alignment_contract[
            "missing_target_alignment_posture"
        ],
        "valid_stop_conditions": meta_charter["valid_stop_conditions"],
        "unsupported_goal_preventing_stop": meta_charter[
            "unsupported_goal_preventing_stop"
        ],
    }
    for field in MISSION_IMPACT_FIELDS:
        result[field] = head.get(field)
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


def factory_evolution_module() -> Any:
    try:
        import factory_evolution
    except ImportError as exc:
        raise SupervisionLogError(
            "Factory evolution implementation is unavailable"
        ) from exc
    return factory_evolution


def factory_evolution_call(module: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    try:
        return getattr(module, name)(*args, **kwargs)
    except module.FactoryEvolutionError as exc:
        raise SupervisionLogError(str(exc)) from exc


def factory_evolution_directory(directory: Path, evolution_id: str) -> Path:
    safe_id(evolution_id, label="factory evolution ID")
    base = (directory / "learning" / "factory-evolution").resolve()
    if directory.resolve() not in base.parents:
        raise SupervisionLogError("Factory evolution owner escaped the target directory")
    result = (base / evolution_id).resolve()
    if result.parent != base:
        raise SupervisionLogError("Factory evolution directory escaped its owner")
    return result


def factory_evolution_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8") + b"\n"


def write_factory_evolution_set(
    directory: Path, artifacts: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    if not artifacts or not set(artifacts) <= FACTORY_EVOLUTION_ARTIFACT_NAMES:
        raise SupervisionLogError("Factory evolution artifact set is invalid")
    expected = {
        name: factory_evolution_json_bytes(value)
        for name, value in artifacts.items()
    }
    reused: list[str] = []
    missing: list[str] = []
    with factory_evolution_lock(directory):
        verify_factory_evolution_inventory(directory)
        for name in sorted(expected):
            path = directory / name
            if path.parent != directory:
                raise SupervisionLogError("Factory evolution artifact escaped its set")
            if path.exists():
                if path.read_bytes() != expected[name]:
                    raise SupervisionLogError(
                        f"Existing factory evolution artifact differs: {name}"
                    )
                reused.append(name)
            else:
                missing.append(name)
        for name in missing:
            atomic_json(directory / name, dict(artifacts[name]))
    return {"written": missing, "reused": reused}


@contextmanager
def factory_evolution_lock(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".append.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise SupervisionLogError("Cannot open Factory evolution lock safely") from exc
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def verify_factory_evolution_inventory(directory: Path) -> None:
    if not directory.exists():
        return
    allowed = FACTORY_EVOLUTION_ARTIFACT_NAMES | {".append.lock"}
    unexpected = sorted(item.name for item in directory.iterdir() if item.name not in allowed)
    if unexpected:
        raise SupervisionLogError(
            "Factory evolution set contains unexpected artifacts: "
            + ", ".join(unexpected)
        )


def require_factory_evolution_artifacts(
    directory: Path, names: tuple[str, ...]
) -> dict[str, dict[str, Any]]:
    missing = [name for name in names if not (directory / name).is_file()]
    if missing:
        raise SupervisionLogError(
            "Factory evolution action is out of order; missing " + ", ".join(missing)
        )
    return {name: read_json(directory / name) for name in names}


def verify_factory_evolution_prepare(
    module: Any, directory: Path
) -> dict[str, Any]:
    artifacts = require_factory_evolution_artifacts(
        directory, ("learning-packet.json", "prepare-manifest.json")
    )
    packet = factory_evolution_call(
        module, "verify_learning_packet", artifacts["learning-packet.json"]
    )
    factory_evolution_call(
        module,
        "verify_evolution_manifest",
        artifacts["prepare-manifest.json"],
        {"learning-packet.json": packet},
    )
    return packet


def verify_factory_evolution_finalize(
    module: Any, directory: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = verify_factory_evolution_prepare(module, directory)
    artifacts = require_factory_evolution_artifacts(
        directory, ("review.json", "finalize-manifest.json")
    )
    review = factory_evolution_call(
        module, "verify_evolution_review", packet, artifacts["review.json"]
    )
    factory_evolution_call(
        module,
        "verify_evolution_manifest",
        artifacts["finalize-manifest.json"],
        {"learning-packet.json": packet, "review.json": review},
    )
    return packet, review


def cmd_factory_evolution_prepare(args: argparse.Namespace) -> None:
    if not args.report_paths or not args.event_paths:
        raise SupervisionLogError(
            "Factory evolution prepare requires explicit report and event paths"
        )
    if args.review_json or args.evaluation_json:
        raise SupervisionLogError("Factory evolution prepare received a later-stage input")
    module = factory_evolution_module()
    directory = factory_evolution_directory(
        target_dir(args), safe_id(args.evolution_id, label="factory evolution ID")
    )
    packet = factory_evolution_call(
        module,
        "build_learning_packet",
        report_paths=args.report_paths,
        event_paths=args.event_paths,
    )
    prepare_manifest = factory_evolution_call(
        module,
        "build_evolution_manifest",
        {"learning-packet.json": packet},
    )
    write_result = write_factory_evolution_set(
        directory,
        {
            "learning-packet.json": packet,
            "prepare-manifest.json": prepare_manifest,
        },
    )
    print(
        json.dumps(
            {
                "action": "prepare",
                "evolution_id": args.evolution_id,
                "stage": "prepared",
                "packet_id": packet["packet_id"],
                "packet_root": packet["packet_root"],
                **write_result,
            },
            sort_keys=True,
        )
    )


def cmd_factory_evolution_finalize(args: argparse.Namespace) -> None:
    if not args.review_json or args.report_paths or args.event_paths or args.evaluation_json:
        raise SupervisionLogError(
            "Factory evolution finalize requires only an explicit review JSON"
        )
    module = factory_evolution_module()
    directory = factory_evolution_directory(
        target_dir(args), safe_id(args.evolution_id, label="factory evolution ID")
    )
    packet = verify_factory_evolution_prepare(module, directory)
    review_submission = read_json(Path(args.review_json).expanduser())
    review = factory_evolution_call(
        module, "build_evolution_review", packet, review_submission
    )
    finalize_manifest = factory_evolution_call(
        module,
        "build_evolution_manifest",
        {"learning-packet.json": packet, "review.json": review},
    )
    write_result = write_factory_evolution_set(
        directory,
        {
            "learning-packet.json": packet,
            "review.json": review,
            "finalize-manifest.json": finalize_manifest,
        },
    )
    print(
        json.dumps(
            {
                "action": "finalize",
                "evolution_id": args.evolution_id,
                "stage": "finalized",
                "review_id": review["review_id"],
                "review_root": review["review_root"],
                **write_result,
            },
            sort_keys=True,
        )
    )


def cmd_factory_evolution_evaluate(args: argparse.Namespace) -> None:
    if (
        not args.evaluation_json
        or args.report_paths
        or args.event_paths
        or args.review_json
    ):
        raise SupervisionLogError(
            "Factory evolution evaluate requires only an explicit evaluation JSON"
        )
    module = factory_evolution_module()
    directory = factory_evolution_directory(
        target_dir(args), safe_id(args.evolution_id, label="factory evolution ID")
    )
    packet, review = verify_factory_evolution_finalize(module, directory)
    evaluation_submission = read_json(Path(args.evaluation_json).expanduser())
    evaluation = factory_evolution_call(
        module,
        "build_candidate_evaluation",
        packet,
        review,
        evaluation_submission,
    )
    bundle = factory_evolution_call(
        module, "build_evolution_bundle", packet, review, evaluation
    )
    write_result = write_factory_evolution_set(directory, bundle)
    print(
        json.dumps(
            {
                "action": "evaluate",
                "evolution_id": args.evolution_id,
                "stage": "evaluated",
                "evaluation_id": evaluation["evaluation_id"],
                "evaluation_root": evaluation["evaluation_root"],
                "disposition": evaluation["disposition"],
                **write_result,
            },
            sort_keys=True,
        )
    )


def cmd_factory_evolution_verify(args: argparse.Namespace) -> None:
    if args.report_paths or args.event_paths or args.review_json or args.evaluation_json:
        raise SupervisionLogError("Factory evolution verify does not accept producer inputs")
    module = factory_evolution_module()
    directory = factory_evolution_directory(
        target_dir(args), safe_id(args.evolution_id, label="factory evolution ID")
    )
    verify_factory_evolution_inventory(directory)
    packet = verify_factory_evolution_prepare(module, directory)
    stage = "prepared"
    result: dict[str, Any] = {
        "packet_id": packet["packet_id"],
        "packet_root": packet["packet_root"],
    }
    if (directory / "review.json").exists() or (directory / "finalize-manifest.json").exists():
        packet, review = verify_factory_evolution_finalize(module, directory)
        stage = "finalized"
        result.update(
            {"review_id": review["review_id"], "review_root": review["review_root"]}
        )
    final_names = (
        "evaluation.json",
        "machine-report.json",
        "manifest.json",
    )
    if any((directory / name).exists() for name in final_names):
        require_factory_evolution_artifacts(directory, final_names)
        bundle = {
            name: read_json(directory / name)
            for name in (
                "learning-packet.json",
                "review.json",
                "evaluation.json",
                "machine-report.json",
                "manifest.json",
            )
        }
        factory_evolution_call(module, "verify_evolution_bundle", bundle)
        stage = "evaluated"
        result.update(
            {
                "evaluation_id": bundle["evaluation.json"]["evaluation_id"],
                "evaluation_root": bundle["evaluation.json"]["evaluation_root"],
                "disposition": bundle["evaluation.json"]["disposition"],
            }
        )
    print(
        json.dumps(
            {
                "action": "verify",
                "evolution_id": args.evolution_id,
                "stage": stage,
                **result,
            },
            sort_keys=True,
        )
    )


def cmd_factory_evolution(args: argparse.Namespace) -> None:
    if args.action == "prepare":
        cmd_factory_evolution_prepare(args)
        return
    if args.action == "finalize":
        cmd_factory_evolution_finalize(args)
        return
    if args.action == "evaluate":
        cmd_factory_evolution_evaluate(args)
        return
    if args.action == "verify":
        cmd_factory_evolution_verify(args)
        return
    raise SupervisionLogError("Unsupported factory evolution action")


def weekly_report_module() -> Any:
    try:
        import weekly_report
    except ImportError as exc:
        raise SupervisionLogError("Weekly report implementation is unavailable") from exc
    return weekly_report


def weekly_projection_inventory(directory: Path) -> dict[str, Any]:
    def inventory(folder: str) -> dict[str, Any]:
        path = directory / folder
        names = sorted(item.name for item in path.glob("*.md")) if path.exists() else []
        return {"count": len(names), "names_sha256": digest(names)}

    return {
        "incident_reports": inventory("incidents"),
        "review_reports": inventory("reviews"),
        "note": "Markdown files are derived projections; the hash-chained JSONL records remain the report source.",
    }


def weekly_report_directory(directory: Path, report_id: str) -> Path:
    safe_id(report_id, label="weekly report ID")
    base = (directory / "reports" / "weekly").resolve()
    result = (base / report_id).resolve()
    if result.parent != base:
        raise SupervisionLogError("Weekly report directory escaped its owner")
    return result


def write_exact_or_reuse(path: Path, value: Mapping[str, Any]) -> bool:
    module = weekly_report_module()
    expected = json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8") + b"\n"
    if path.exists():
        if path.read_bytes() != expected:
            raise SupervisionLogError(
                f"Existing weekly report artifact differs: {path.name}"
            )
        return True
    module.atomic_write(path, expected)
    return False


def cmd_weekly_report_prepare(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    module = weekly_report_module()
    all_events = events(directory / "events.jsonl")
    if not all_events:
        raise SupervisionLogError("Cannot report an empty supervision ledger")
    policy_history = events(directory / "policy-history.jsonl")
    end = parse_time(args.end) if args.end else parse_time(None)
    coverage_days = args.days or int(
        policy.get("reports", {}).get("weekly", {}).get("coverage_days", 7)
    )
    if not 2 <= coverage_days <= 31:
        raise SupervisionLogError("Weekly report coverage must be 2-31 days")
    if args.start:
        start = parse_time(args.start)
    elif args.since_inception:
        start = parse_time(str(all_events[0]["timestamp"]))
    else:
        start = end - dt.timedelta(days=coverage_days)
        first = parse_time(str(all_events[0]["timestamp"]))
        if first > start:
            start = first
    timezone_name = str(
        policy.get("reports", {}).get("weekly", {}).get(
            "timezone",
            policy.get("schedule", {}).get(
                "roundup_timezone", "America/Los_Angeles"
            ),
        )
    )
    canonical_resume_record_ids = frozenset(
        str(item["record_id"])
        for item in all_events
        if supervision_resume_record_is_canonical(item, all_events, policy_history)
    )
    try:
        metrics, packet = module.build_metrics(
            target_label=str(policy.get("target_label", args.target_thread[:12])),
            target_thread_id=args.target_thread,
            start=start,
            end=end,
            timezone_name=timezone_name,
            all_events=all_events,
            policy_history=policy_history,
            current_policy=policy,
            projection_inventory=weekly_projection_inventory(directory),
            canonical_resume_record_ids=canonical_resume_record_ids,
        )
    except module.WeeklyReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    report_directory = weekly_report_directory(directory, str(metrics["report_id"]))
    report_directory.mkdir(parents=True, exist_ok=True)
    os.chmod(report_directory, 0o700)
    metrics_path = report_directory / "metrics.json"
    packet_path = report_directory / "review-packet.json"
    reused_metrics = write_exact_or_reuse(metrics_path, metrics)
    reused_packet = write_exact_or_reuse(packet_path, packet)
    print(
        json.dumps(
            {
                "report_id": metrics["report_id"],
                "coverage": metrics["coverage"],
                "source_root": metrics["source"]["source_root"],
                "report_directory": str(report_directory),
                "metrics_path": str(metrics_path),
                "review_packet_path": str(packet_path),
                "reused": reused_metrics and reused_packet,
                "next": "Read every review-packet event, produce the exact cognitive-review contract, then finalize with --review-base64.",
            },
            sort_keys=True,
        )
    )


def load_weekly_artifacts(
    directory: Path, report_id: str
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    report_directory = weekly_report_directory(directory, report_id)
    metrics = read_json(report_directory / "metrics.json")
    packet = read_json(report_directory / "review-packet.json")
    if metrics.get("report_id") != report_id or packet.get("report_id") != report_id:
        raise SupervisionLogError("Weekly report identity differs")
    if packet.get("metrics") != metrics:
        raise SupervisionLogError(
            "Weekly review packet diverges from canonical metrics"
        )
    if packet.get("source_root") != metrics.get("source", {}).get("source_root"):
        raise SupervisionLogError("Weekly report source roots diverge")
    return report_directory, metrics, packet


def cmd_weekly_report_finalize(args: argparse.Namespace) -> None:
    directory, _policy = load_policy(args)
    module = weekly_report_module()
    report_directory, metrics, packet = load_weekly_artifacts(
        directory, args.report_id
    )
    try:
        review_bytes = base64.b64decode(args.review_base64, validate=True)
        raw_review = json.loads(review_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Weekly cognitive review encoding is invalid") from exc
    if not isinstance(raw_review, dict):
        raise SupervisionLogError("Weekly cognitive review must be an object")
    record_ids = {
        str(item.get("record_id"))
        for item in packet.get("event_records", [])
        if item.get("record_id")
    }
    try:
        review = module.validate_review(
            raw_review,
            report_id=args.report_id,
            source_root=str(metrics["source"]["source_root"]),
            record_ids=record_ids,
        )
    except module.WeeklyReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    review_path = report_directory / "review.json"
    report_json_path = report_directory / "report.json"
    markdown_path = report_directory / "report.md"
    pdf_path = report_directory / "report.pdf"
    manifest_path = report_directory / "manifest.json"
    review_reused = write_exact_or_reuse(review_path, review)
    machine_report = module.machine_report(metrics, review)
    report_json_reused = write_exact_or_reuse(report_json_path, machine_report)
    markdown_bytes = module.markdown_report(metrics, review).encode("utf-8")
    if markdown_path.exists():
        if markdown_path.read_bytes() != markdown_bytes:
            raise SupervisionLogError("Existing weekly Markdown report differs")
    else:
        module.atomic_write(markdown_path, markdown_bytes)
    if pdf_path.exists():
        pdf_reused = True
    else:
        temporary_pdf = report_directory / ".report.pdf.prepared"
        try:
            module.render_pdf(temporary_pdf, metrics, review)
            os.replace(temporary_pdf, pdf_path)
        finally:
            if temporary_pdf.exists():
                temporary_pdf.unlink()
        pdf_reused = False
    manifest = module.manifest_for(
        metrics_path=report_directory / "metrics.json",
        packet_path=report_directory / "review-packet.json",
        review_path=review_path,
        report_json_path=report_json_path,
        markdown_path=markdown_path,
        pdf_path=pdf_path,
    )
    manifest["report_id"] = args.report_id
    manifest["source_root"] = metrics["source"]["source_root"]
    write_exact_or_reuse(manifest_path, manifest)
    print(
        json.dumps(
            {
                "report_id": args.report_id,
                "source_root": metrics["source"]["source_root"],
                "review_reused": review_reused,
                "report_json_reused": report_json_reused,
                "pdf_reused": pdf_reused,
                "pdf_path": str(pdf_path),
                "report_json_path": str(report_json_path),
                "markdown_path": str(markdown_path),
                "manifest_path": str(manifest_path),
            },
            sort_keys=True,
        )
    )


def verify_weekly_report_set(directory: Path, report_id: str) -> dict[str, Any]:
    module = weekly_report_module()
    report_directory, metrics, packet = load_weekly_artifacts(
        directory, report_id
    )
    review = read_json(report_directory / "review.json")
    manifest = read_json(report_directory / "manifest.json")
    record_ids = {
        str(item.get("record_id"))
        for item in packet.get("event_records", [])
        if item.get("record_id")
    }
    try:
        review = module.validate_review(
            review,
            report_id=report_id,
            source_root=str(metrics["source"]["source_root"]),
            record_ids=record_ids,
        )
    except module.WeeklyReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    paths = {
        "metrics.json": report_directory / "metrics.json",
        "review-packet.json": report_directory / "review-packet.json",
        "review.json": report_directory / "review.json",
        "report.json": report_directory / "report.json",
        "report.md": report_directory / "report.md",
        "report.pdf": report_directory / "report.pdf",
    }
    try:
        report_members = {path.name for path in report_directory.iterdir()}
    except OSError as exc:
        raise SupervisionLogError("Weekly report directory is unavailable") from exc
    if report_members != {*paths, "manifest.json"}:
        raise SupervisionLogError("Weekly report directory member set differs")
    if set(manifest.get("files", {})) != set(paths):
        raise SupervisionLogError("Weekly report manifest file set differs")
    for name, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise SupervisionLogError(f"Weekly report is missing {name}")
        expected = manifest["files"][name]
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if (
            expected.get("sha256") != actual_hash
            or expected.get("bytes") != path.stat().st_size
        ):
            raise SupervisionLogError(f"Weekly report artifact differs: {name}")
    if digest(manifest["files"]) != manifest.get("manifest_root"):
        raise SupervisionLogError("Weekly report manifest root differs")
    expected_markdown = module.markdown_report(metrics, review).encode("utf-8")
    if paths["report.md"].read_bytes() != expected_markdown:
        raise SupervisionLogError("Weekly Markdown projection differs")
    expected_machine_report = module.machine_report(metrics, review)
    if read_json(paths["report.json"]) != expected_machine_report:
        raise SupervisionLogError("Weekly machine-readable report differs")
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(paths["report.pdf"]))
        page_count = len(reader.pages)
        text_sample = "".join(
            (page.extract_text() or "") for page in reader.pages[:2]
        )
    except Exception as exc:
        raise SupervisionLogError("Weekly PDF cannot be parsed") from exc
    if page_count < 4 or "SUPERVISION WEEKLY REVIEW" not in text_sample:
        raise SupervisionLogError(
            "Weekly PDF lacks the required rendered report"
        )
    return {
        "valid": True,
        "report_id": report_id,
        "source_root": metrics["source"]["source_root"],
        "manifest_root": manifest["manifest_root"],
        "page_count": page_count,
        "pdf_path": str(paths["report.pdf"]),
        "report_sha256": hashlib.sha256(paths["report.json"].read_bytes()).hexdigest(),
        "review_sha256": hashlib.sha256(paths["review.json"].read_bytes()).hexdigest(),
        "pdf_sha256": hashlib.sha256(paths["report.pdf"].read_bytes()).hexdigest(),
    }


def cmd_weekly_report_verify(args: argparse.Namespace) -> None:
    directory, _policy = load_policy(args)
    print(
        json.dumps(
            verify_weekly_report_set(directory, args.report_id), sort_keys=True
        )
    )


def decode_weekly_gmail_readback(value: str) -> dict[str, Any]:
    try:
        decoded = base64.b64decode(value, validate=True)
        readback = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Weekly Gmail read-back encoding is invalid") from exc
    if not isinstance(readback, dict):
        raise SupervisionLogError("Weekly Gmail read-back must be an object")
    return readback


def validate_weekly_gmail_readback(
    readback: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "seed_message",
        "sent_message",
        "attachments",
    }
    if set(readback) != required:
        raise SupervisionLogError("Weekly Gmail read-back shape differs")
    if (
        readback.get("schema_version") != 1
        or readback.get("kind") != "gmail-weekly-report-delivery-readback"
    ):
        raise SupervisionLogError("Weekly Gmail read-back version differs")
    roundup = policy.get("notifications", {}).get("gmail_roundup", {})
    if (
        not isinstance(roundup, Mapping)
        or roundup.get("enabled") is not True
        or not all(
            isinstance(roundup.get(key), str) and roundup[key]
            for key in ("project_key", "reply_message_id", "subject")
        )
        or policy.get("permissions", {}).get("gmail_roundup_notification") is not True
    ):
        raise SupervisionLogError(
            "Weekly report delivery requires the enabled roundup Gmail lane"
        )
    seed, _seed_message, _seed_mime = validate_gmail_message_owner(
        readback.get("seed_message"), label="Weekly Gmail seed"
    )
    sent, message, _raw_mime = validate_gmail_message_owner(
        readback.get("sent_message"), label="Weekly Gmail sent message"
    )
    if seed["message_id"] != roundup.get("reply_message_id"):
        raise SupervisionLogError("Weekly Gmail read-back used another thread seed")
    if sent["message_id"] == seed["message_id"] or sent["thread_id"] != seed["thread_id"]:
        raise SupervisionLogError(
            "Weekly Gmail sent message is not owned by the seed thread"
        )
    in_reply_to = str(message.get("In-Reply-To", ""))
    references = str(message.get("References", ""))
    if seed["rfc_message_id"] not in {in_reply_to, *references.split()}:
        raise SupervisionLogError(
            "Weekly Gmail sent message is not a reply to the seed"
        )
    expected_subject = str(roundup.get("subject", "")).strip()
    seed_subject = re.sub(r"^(?:re:\s*)+", "", seed["subject"], flags=re.I)
    sent_subject = re.sub(r"^(?:re:\s*)+", "", sent["subject"], flags=re.I)
    if not expected_subject or seed_subject != expected_subject or sent_subject != expected_subject:
        raise SupervisionLogError("Weekly Gmail subject differs from the bound lane")

    pdf_path = Path(str(verified["pdf_path"]))
    expected_attachment = {
        "sha256": verified["pdf_sha256"],
        "bytes": pdf_path.stat().st_size,
    }
    mime_attachments: dict[str, bytes] = {}
    for part in message.iter_attachments():
        filename = str(part.get_filename() or "")
        if not filename or filename in mime_attachments:
            raise SupervisionLogError("Weekly Gmail MIME attachment identity differs")
        mime_attachments[filename] = part.get_payload(decode=True) or b""
    if set(mime_attachments) != {"report.pdf"}:
        raise SupervisionLogError("Weekly Gmail attachment set differs")
    declared = readback.get("attachments")
    if not isinstance(declared, list) or len(declared) != 1:
        raise SupervisionLogError(
            "Weekly Gmail read-back requires the verified PDF attachment"
        )
    item = declared[0]
    if not isinstance(item, Mapping) or set(item) != {
        "filename",
        "attachment_id",
        "owner_message_id",
        "owner_thread_id",
        "read_tool_call_id",
        "sha256",
        "bytes",
    }:
        raise SupervisionLogError("Weekly Gmail attachment receipt shape differs")
    if item.get("filename") != "report.pdf":
        raise SupervisionLogError("Weekly Gmail attachment filename differs")
    attachment_id = safe_id(
        str(item.get("attachment_id", "")), label="Weekly Gmail attachment ID"
    )
    attachment_call = safe_id(
        str(item.get("read_tool_call_id", "")),
        label="Weekly Gmail attachment read tool call ID",
    )
    owner_message_id = safe_id(
        str(item.get("owner_message_id", "")),
        label="Weekly Gmail attachment owner message ID",
    )
    owner_thread_id = safe_id(
        str(item.get("owner_thread_id", "")),
        label="Weekly Gmail attachment owner thread ID",
    )
    if owner_message_id != sent["message_id"] or owner_thread_id != sent["thread_id"]:
        raise SupervisionLogError("Weekly Gmail attachment owner differs")
    payload = mime_attachments["report.pdf"]
    actual = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    if actual != expected_attachment:
        raise SupervisionLogError("Weekly Gmail MIME attachment bytes differ")
    if item.get("sha256") != actual["sha256"] or item.get("bytes") != actual["bytes"]:
        raise SupervisionLogError("Weekly Gmail attachment read-back differs")
    normalized = {
        "seed_message": seed,
        "sent_message": sent,
        "attachments": [
            {
                "filename": "report.pdf",
                "attachment_id": attachment_id,
                "owner_message_id": owner_message_id,
                "owner_thread_id": owner_thread_id,
                "read_tool_call_id": attachment_call,
                **actual,
            }
        ],
    }
    return {**normalized, "readback_root": digest(normalized)}


def latest_weekly_delivery(
    all_events: Sequence[Mapping[str, Any]], *, report_id: str
) -> Mapping[str, Any] | None:
    return next(
        (
            item
            for item in reversed(all_events)
            if item.get("kind") == "notification"
            and item.get("category") == WEEKLY_REPORT_DELIVERY_CATEGORY
            and item.get("status") == "sent"
            and item.get("report_id") == report_id
        ),
        None,
    )


def weekly_delivery_is_current(
    delivery: Mapping[str, Any],
    verified: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> bool:
    readback = delivery.get("gmail_readback")
    if not isinstance(readback, Mapping):
        return False
    material = {key: value for key, value in readback.items() if key != "readback_root"}
    sent_message = readback.get("sent_message")
    attachments = readback.get("attachments")
    attachment = (
        attachments[0]
        if isinstance(attachments, list)
        and len(attachments) == 1
        and isinstance(attachments[0], Mapping)
        else None
    )
    roundup = policy.get("notifications", {}).get("gmail_roundup", {})
    seed_message = readback.get("seed_message")
    return bool(
        readback.get("readback_root") == digest(material)
        and isinstance(sent_message, Mapping)
        and isinstance(seed_message, Mapping)
        and isinstance(attachment, Mapping)
        and delivery.get("report_id") == verified["report_id"]
        and delivery.get("source_root") == verified["source_root"]
        and delivery.get("manifest_root") == verified["manifest_root"]
        and delivery.get("pdf_sha256") == verified["pdf_sha256"]
        and delivery.get("gmail_readback_root") == readback.get("readback_root")
        and delivery.get("gmail_message_id") == sent_message.get("message_id")
        and delivery.get("gmail_thread_id") == sent_message.get("thread_id")
        and attachment.get("filename") == "report.pdf"
        and attachment.get("sha256") == verified["pdf_sha256"]
        and seed_message.get("message_id") == roundup.get("reply_message_id")
        and delivery.get("policy_sha256") == policy.get("policy_sha256")
    )


def weekly_delivery_status(
    directory: Path,
    policy: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    roundup = policy.get("notifications", {}).get("gmail_roundup", {})
    configured = bool(
        isinstance(roundup, Mapping)
        and roundup.get("enabled") is True
        and all(
            isinstance(roundup.get(key), str) and roundup[key]
            for key in ("project_key", "reply_message_id", "subject")
        )
        and policy.get("permissions", {}).get("gmail_roundup_notification") is True
    )
    if not configured:
        return {
            "status": "unavailable",
            "configured": False,
            "retryable": True,
            "record_id": None,
            "message_id": None,
            "thread_id": None,
            "reason": "The roundup Gmail lane is not fully configured.",
        }
    delivery = latest_weekly_delivery(
        events(directory / "events.jsonl"), report_id=str(verified["report_id"])
    )
    if delivery is None:
        return {
            "status": "pending",
            "configured": True,
            "retryable": True,
            "record_id": None,
            "message_id": None,
            "thread_id": None,
            "reason": "The verified report has not been delivered through the roundup Gmail owner.",
        }
    current = weekly_delivery_is_current(delivery, verified, policy)
    return {
        "status": "delivered" if current else "stale",
        "configured": True,
        "retryable": not current,
        "record_id": delivery.get("record_id"),
        "message_id": delivery.get("gmail_message_id"),
        "thread_id": delivery.get("gmail_thread_id"),
        "reason": (
            None
            if current
            else "The recorded delivery no longer matches the verified report and current roundup lane."
        ),
    }


def append_weekly_delivery(
    *,
    args: argparse.Namespace,
    directory: Path,
    policy: Mapping[str, Any],
    verified: Mapping[str, Any],
    readback: Mapping[str, Any],
) -> dict[str, Any]:
    sent_message = readback["sent_message"]
    message_id = str(sent_message["message_id"])
    with append_lock(directory):
        current_events = events(directory / "events.jsonl")
        prior = latest_weekly_delivery(
            current_events, report_id=str(verified["report_id"])
        )
        if prior is not None:
            if (
                prior.get("gmail_message_id") != message_id
                or prior.get("gmail_readback_root") != readback["readback_root"]
                or not weekly_delivery_is_current(prior, verified, policy)
            ):
                raise SupervisionLogError("Weekly report delivery already differs")
            return dict(prior)
        record = {
            "schema_version": 1,
            "record_id": f"EVT-{len(current_events) + 1:06d}",
            "timestamp": utc_now(),
            "target_thread_id": policy["target_thread_id"],
            "kind": "notification",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": verified["source_root"],
            "status": "sent",
            "severity": "info",
            "category": WEEKLY_REPORT_DELIVERY_CATEGORY,
            "summary": "Sent the verified weekly supervision PDF through the configured roundup Gmail lane.",
            "evidence": [
                verified["report_id"],
                verified["source_root"],
                verified["manifest_root"],
                message_id,
            ],
            "dedup_key": f"gmail-weekly:{verified['report_id']}",
            "report_id": verified["report_id"],
            "source_root": verified["source_root"],
            "manifest_root": verified["manifest_root"],
            "pdf_sha256": verified["pdf_sha256"],
            "gmail_message_id": message_id,
            "gmail_thread_id": sent_message["thread_id"],
            "gmail_rfc_message_id": sent_message["rfc_message_id"],
            "gmail_read_tool_call_id": sent_message["read_tool_call_id"],
            "gmail_readback_root": readback["readback_root"],
            "gmail_attachments": readback["attachments"],
            "gmail_readback": dict(readback),
            "policy_sha256": policy["policy_sha256"],
        }
        append_event_locked(args, directory, record)
    return record


def cmd_weekly_report_delivery(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    verified = verify_weekly_report_set(directory, args.report_id)
    readback = validate_weekly_gmail_readback(
        decode_weekly_gmail_readback(args.gmail_readback_base64),
        policy=policy,
        verified=verified,
    )
    record = append_weekly_delivery(
        args=args,
        directory=directory,
        policy=policy,
        verified=verified,
        readback=readback,
    )
    print(
        json.dumps(
            {
                "record": record,
                "verified": verified,
                "delivery": weekly_delivery_status(directory, policy, verified),
            },
            sort_keys=True,
        )
    )


def cmd_weekly_report_status(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    verified = verify_weekly_report_set(directory, args.report_id)
    print(
        json.dumps(
            {
                "verified": verified,
                "delivery": weekly_delivery_status(directory, policy, verified),
            },
            sort_keys=True,
        )
    )


def cmd_weekly_report_configure(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    roundup = policy.get("notifications", {}).get("gmail_roundup", {})
    if not roundup.get("enabled") or not all(
        roundup.get(key) for key in ("project_key", "reply_message_id", "subject")
    ):
        raise SupervisionLogError(
            "Weekly report requires the enabled roundup email lane"
        )
    automation_id = safe_id(
        args.automation_id, label="weekly report automation ID"
    )
    time_value = clean(
        args.local_time, label="weekly report local time", maximum=5
    )
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time_value):
        raise SupervisionLogError("Weekly report local time is invalid")
    if not 2 <= args.days <= 31:
        raise SupervisionLogError("Weekly report coverage must be 2-31 days")
    policy.setdefault("reports", {})["weekly"] = {
        **weekly_report_contract(),
        "enabled": True,
        "weekday": args.weekday,
        "local_time": time_value,
        "coverage_days": args.days,
        "automation_id": automation_id,
    }
    write_policy_version(
        directory,
        policy,
        kind="policy-weekly-report",
        reason="Enabled one derived weekly PDF review through the existing roundup writer and email lane.",
        evidence_values=[automation_id],
    )
    print(
        json.dumps(
            {
                "changed": True,
                "weekly": policy["reports"]["weekly"],
                "policy": policy,
            },
            sort_keys=True,
        )
    )


def cmd_weekly_report(args: argparse.Namespace) -> None:
    if args.action == "prepare":
        cmd_weekly_report_prepare(args)
        return
    if args.action == "finalize":
        if not args.report_id or not args.review_base64:
            raise SupervisionLogError(
                "Weekly report finalize requires --report-id and --review-base64"
            )
        cmd_weekly_report_finalize(args)
        return
    if args.action == "verify":
        if not args.report_id:
            raise SupervisionLogError("Weekly report verify requires --report-id")
        cmd_weekly_report_verify(args)
        return
    if args.action == "status":
        if not args.report_id:
            raise SupervisionLogError("Weekly report status requires --report-id")
        cmd_weekly_report_status(args)
        return
    if args.action == "record-delivery":
        if not args.report_id or not args.gmail_readback_base64:
            raise SupervisionLogError(
                "Weekly report delivery requires --report-id and --gmail-readback-base64"
            )
        cmd_weekly_report_delivery(args)
        return
    if args.action == "configure":
        if not args.automation_id:
            raise SupervisionLogError(
                "Weekly report configure requires --automation-id"
            )
        cmd_weekly_report_configure(args)
        return
    raise SupervisionLogError("Unsupported weekly report action")


def terminal_report_module() -> Any:
    try:
        import terminal_report
    except ImportError as exc:
        raise SupervisionLogError("Terminal report implementation is unavailable") from exc
    return terminal_report


def terminal_report_directory(directory: Path, report_set_id: str) -> Path:
    safe_id(report_set_id, label="terminal report set ID")
    base = (directory / "reports" / "terminal").resolve()
    result = (base / report_set_id).resolve()
    if result.parent != base:
        raise SupervisionLogError("Terminal report directory escaped its owner")
    return result


def terminal_prior_report_inventory(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    weekly_root = directory / "reports" / "weekly"
    if not weekly_root.exists():
        return rows
    for report_directory in sorted(item for item in weekly_root.iterdir() if item.is_dir()):
        manifest_path = report_directory / "manifest.json"
        report_path = report_directory / "report.json"
        if not manifest_path.is_file() or not report_path.is_file():
            raise SupervisionLogError(
                f"Prior weekly report is incomplete: {report_directory.name}"
            )
        manifest = read_json(manifest_path)
        report = read_json(report_path)
        report_id = str(manifest.get("report_id", report_directory.name))
        verified = verify_weekly_report_set(directory, report_id)
        rows.append(
            {
                "report_id": safe_id(report_id, label="prior report ID"),
                "kind": str(report.get("kind", "supervision-weekly-review-record")),
                "source_root": verified["source_root"],
                "manifest_root": verified["manifest_root"],
                "report_sha256": verified["report_sha256"],
                "review_sha256": verified["review_sha256"],
                "pdf_sha256": verified["pdf_sha256"],
                "coverage": report.get("metrics", {}).get("coverage", {}),
                "cognitive_review": report.get("cognitive_review", {}),
            }
        )
    return rows


def write_terminal_exact_or_reuse(path: Path, data: bytes) -> bool:
    module = terminal_report_module()
    if path.exists():
        if path.read_bytes() != data:
            raise SupervisionLogError(f"Existing terminal report artifact differs: {path.name}")
        return True
    module.atomic_write(path, data)
    return False


def terminal_pdf_projection(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        metadata = reader.metadata or {}
        pages = [
            re.sub(r"\s+", " ", page.extract_text() or "").strip()
            for page in reader.pages
        ]
    except Exception as exc:
        raise SupervisionLogError("Terminal report PDF cannot be parsed") from exc
    return {
        "pages": pages,
        "title": str(metadata.get("/Title", "")),
        "author": str(metadata.get("/Author", "")),
    }


def render_and_verify_terminal_pdf(
    *, path: Path, report: Mapping[str, Any], report_set_id: str
) -> bool:
    module = terminal_report_module()
    prepared = path.parent / f".{path.name}.prepared"
    try:
        module.render_pdf(prepared, report, report_set_id=report_set_id)
        expected = terminal_pdf_projection(prepared)
        if path.exists():
            if terminal_pdf_projection(path) != expected:
                raise SupervisionLogError(
                    f"Existing terminal report artifact differs: {path.name}"
                )
            return True
        os.replace(prepared, path)
        return False
    finally:
        if prepared.exists():
            prepared.unlink()


def terminal_packet(directory: Path, report_set_id: str) -> tuple[Path, dict[str, Any]]:
    module = terminal_report_module()
    report_directory = terminal_report_directory(directory, report_set_id)
    packet = read_json(report_directory / "review-packet.json")
    try:
        packet = module.validate_packet(packet)
    except module.TerminalReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    if packet["report_set_id"] != report_set_id:
        raise SupervisionLogError("Terminal report packet identity differs")
    return report_directory, packet


def cmd_terminal_report_prepare(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    if policy.get("reports", {}).get("terminal") != terminal_report_contract():
        raise SupervisionLogError("Terminal implementation reporting is not enabled")
    all_events = events(directory / "events.jsonl")
    lifecycle_record = next(
        (item for item in all_events if item.get("record_id") == args.lifecycle_record),
        None,
    )
    if lifecycle_record is None or lifecycle_record.get("kind") != "lifecycle" or lifecycle_record.get("status") != "completed":
        raise SupervisionLogError("Terminal report requires the exact completed lifecycle")
    state_fingerprint = str(lifecycle_record.get("state_fingerprint", ""))
    completion_record = latest_outcome_completion_record(
        all_events, state_fingerprint=state_fingerprint
    )
    permitted, reason = assess_outcome_completion_record(
        completion_record, policy=policy, state_fingerprint=state_fingerprint
    )
    if not permitted or completion_record is None:
        raise SupervisionLogError(f"Terminal report completion proof is invalid: {reason}")
    if lifecycle_record.get("outcome_completion_record_id") != completion_record.get("record_id"):
        raise SupervisionLogError("Completed lifecycle is not bound to current outcome proof")
    mission = bound_mission(policy)
    if mission is None:
        raise SupervisionLogError("Terminal report requires an exact mission binding")
    module = terminal_report_module()
    try:
        packet = module.build_packet(
            target_label=str(policy.get("target_label", args.target_thread[:12])),
            target_thread_id=args.target_thread,
            mission_root=str(mission["mission_root"]),
            state_fingerprint=state_fingerprint,
            completion_record=completion_record,
            lifecycle_record=lifecycle_record,
            all_events=all_events,
            prior_reports=terminal_prior_report_inventory(directory),
        )
    except module.TerminalReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    report_directory = terminal_report_directory(directory, packet["report_set_id"])
    report_directory.mkdir(parents=True, exist_ok=True)
    os.chmod(report_directory, 0o700)
    packet_bytes = json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    reused = write_terminal_exact_or_reuse(
        report_directory / "review-packet.json", packet_bytes
    )
    print(
        json.dumps(
            {
                "report_set_id": packet["report_set_id"],
                "source_root": packet["source_root"],
                "coverage": packet["coverage"],
                "review_packet_path": str(report_directory / "review-packet.json"),
                "report_directory": str(report_directory),
                "reused": reused,
                "next": "Read the complete packet, write both required cognitive reports, then finalize with --review-base64.",
            },
            sort_keys=True,
        )
    )


def cmd_terminal_report_finalize(args: argparse.Namespace) -> None:
    directory, _policy = load_policy(args)
    module = terminal_report_module()
    report_directory, packet = terminal_packet(directory, args.report_set_id)
    try:
        review_bytes = base64.b64decode(args.review_base64, validate=True)
        raw_review = json.loads(review_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Terminal cognitive review encoding is invalid") from exc
    try:
        review = module.validate_review(raw_review, packet)
    except module.TerminalReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    files: dict[str, Path] = {
        "review-packet.json": report_directory / "review-packet.json",
        "review.json": report_directory / "review.json",
        "delta-report.json": report_directory / "delta-report.json",
        "delta-report.md": report_directory / "delta-report.md",
        "delta-report.pdf": report_directory / "delta-report.pdf",
        "full-report.json": report_directory / "full-report.json",
        "full-report.md": report_directory / "full-report.md",
        "full-report.pdf": report_directory / "full-report.pdf",
    }
    review_bytes_out = json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    write_terminal_exact_or_reuse(files["review.json"], review_bytes_out)
    for report_type, key, prefix in (
        ("delta", "delta_report", "delta-report"),
        ("full", "full_report", "full-report"),
    ):
        report = review[key]
        machine = module.report_record(
            report,
            report_set_id=args.report_set_id,
            source_root=str(packet["source_root"]),
            report_type=report_type,
        )
        machine_bytes = json.dumps(machine, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        write_terminal_exact_or_reuse(files[f"{prefix}.json"], machine_bytes)
        markdown = module.markdown_report(
            report, report_set_id=args.report_set_id
        ).encode("utf-8")
        write_terminal_exact_or_reuse(files[f"{prefix}.md"], markdown)
        render_and_verify_terminal_pdf(
            path=files[f"{prefix}.pdf"],
            report=report,
            report_set_id=args.report_set_id,
        )
    manifest = module.manifest_for(
        files,
        report_set_id=args.report_set_id,
        source_root=str(packet["source_root"]),
    )
    manifest_path = report_directory / "manifest.json"
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    write_terminal_exact_or_reuse(manifest_path, manifest_bytes)
    print(
        json.dumps(
            {
                "report_set_id": args.report_set_id,
                "source_root": packet["source_root"],
                "manifest_root": manifest["manifest_root"],
                "delta_pdf_path": str(files["delta-report.pdf"]),
                "full_pdf_path": str(files["full-report.pdf"]),
                "manifest_path": str(manifest_path),
            },
            sort_keys=True,
        )
    )


def verify_terminal_report_set(
    directory: Path, report_set_id: str
) -> dict[str, Any]:
    module = terminal_report_module()
    report_directory, packet = terminal_packet(directory, report_set_id)
    all_events = events(directory / "events.jsonl")
    lifecycle_record = next(
        (
            item
            for item in all_events
            if item.get("record_id") == packet["lifecycle_record_id"]
        ),
        None,
    )
    completion_record = next(
        (
            item
            for item in all_events
            if item.get("record_id") == packet["completion_record_id"]
        ),
        None,
    )
    if lifecycle_record is None or completion_record is None:
        raise SupervisionLogError("Terminal report source records are missing")
    try:
        current_packet = module.build_packet(
            target_label=str(packet["target_label"]),
            target_thread_id=str(packet["target_thread_id"]),
            mission_root=str(packet["mission_root"]),
            state_fingerprint=str(packet["state_fingerprint"]),
            completion_record=completion_record,
            lifecycle_record=lifecycle_record,
            all_events=all_events,
            prior_reports=terminal_prior_report_inventory(directory),
        )
    except module.TerminalReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    if current_packet != packet:
        raise SupervisionLogError("Terminal report source packet is stale")
    review = read_json(report_directory / "review.json")
    manifest = read_json(report_directory / "manifest.json")
    try:
        review = module.validate_review(review, packet)
    except module.TerminalReportError as exc:
        raise SupervisionLogError(str(exc)) from exc
    paths = {
        "review-packet.json": report_directory / "review-packet.json",
        "review.json": report_directory / "review.json",
        "delta-report.json": report_directory / "delta-report.json",
        "delta-report.md": report_directory / "delta-report.md",
        "delta-report.pdf": report_directory / "delta-report.pdf",
        "full-report.json": report_directory / "full-report.json",
        "full-report.md": report_directory / "full-report.md",
        "full-report.pdf": report_directory / "full-report.pdf",
    }
    if set(manifest.get("files", {})) != set(paths):
        raise SupervisionLogError("Terminal report manifest file set differs")
    for name, path in paths.items():
        if not path.is_file():
            raise SupervisionLogError(f"Terminal report is missing {name}")
        expected = manifest["files"][name]
        actual = path.read_bytes()
        if expected.get("sha256") != hashlib.sha256(actual).hexdigest() or expected.get("bytes") != len(actual):
            raise SupervisionLogError(f"Terminal report artifact differs: {name}")
    if digest(manifest["files"]) != manifest.get("manifest_root"):
        raise SupervisionLogError("Terminal report manifest root differs")
    expected_manifest = module.manifest_for(
        paths,
        report_set_id=report_set_id,
        source_root=str(packet["source_root"]),
    )
    if manifest != expected_manifest:
        raise SupervisionLogError("Terminal report manifest identity differs")
    for report_type, key, prefix in (
        ("delta", "delta_report", "delta-report"),
        ("full", "full_report", "full-report"),
    ):
        expected_machine = module.report_record(
            review[key],
            report_set_id=report_set_id,
            source_root=str(packet["source_root"]),
            report_type=report_type,
        )
        if read_json(paths[f"{prefix}.json"]) != expected_machine:
            raise SupervisionLogError(f"Terminal {report_type} JSON projection differs")
        expected_markdown = module.markdown_report(
            review[key], report_set_id=report_set_id
        ).encode("utf-8")
        if paths[f"{prefix}.md"].read_bytes() != expected_markdown:
            raise SupervisionLogError(f"Terminal {report_type} Markdown projection differs")
        with tempfile.TemporaryDirectory(dir=report_directory) as temporary:
            expected_pdf = Path(temporary) / f"{prefix}.pdf"
            module.render_pdf(
                expected_pdf, review[key], report_set_id=report_set_id
            )
            if terminal_pdf_projection(paths[f"{prefix}.pdf"]) != terminal_pdf_projection(
                expected_pdf
            ):
                raise SupervisionLogError(
                    f"Terminal {report_type} PDF projection differs"
                )
    delta_projection = terminal_pdf_projection(paths["delta-report.pdf"])
    full_projection = terminal_pdf_projection(paths["full-report.pdf"])
    return {
        "valid": True,
        "report_set_id": report_set_id,
        "source_root": packet["source_root"],
        "state_fingerprint": packet["state_fingerprint"],
        "completion_record_id": packet["completion_record_id"],
        "lifecycle_record_id": packet["lifecycle_record_id"],
        "manifest_root": manifest["manifest_root"],
        "delta_pdf_path": str(paths["delta-report.pdf"]),
        "full_pdf_path": str(paths["full-report.pdf"]),
        "delta_pdf_sha256": manifest["files"]["delta-report.pdf"]["sha256"],
        "full_pdf_sha256": manifest["files"]["full-report.pdf"]["sha256"],
        "delta_page_count": len(delta_projection["pages"]),
        "full_page_count": len(full_projection["pages"]),
    }


def cmd_terminal_report_verify(args: argparse.Namespace) -> None:
    directory, _policy = load_policy(args)
    print(json.dumps(verify_terminal_report_set(directory, args.report_set_id), sort_keys=True))


def decode_terminal_gmail_readback(value: str) -> dict[str, Any]:
    try:
        decoded = base64.b64decode(value, validate=True)
        readback = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError("Terminal Gmail read-back encoding is invalid") from exc
    if not isinstance(readback, dict):
        raise SupervisionLogError("Terminal Gmail read-back must be an object")
    return readback


def decode_urlsafe_payload(value: Any, *, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise SupervisionLogError(f"{label} is missing")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise SupervisionLogError(f"{label} is invalid") from exc


def validate_gmail_message_owner(
    raw: Any, *, label: str
) -> tuple[dict[str, Any], Any, bytes]:
    required = {
        "provider",
        "message_id",
        "thread_id",
        "read_tool_call_id",
        "fetched_at",
        "raw_mime_base64",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise SupervisionLogError(f"{label} owner shape differs")
    if raw.get("provider") != "gmail.read_email":
        raise SupervisionLogError(f"{label} owner provider differs")
    message_id = safe_id(str(raw.get("message_id", "")), label=f"{label} message ID")
    thread_id = safe_id(str(raw.get("thread_id", "")), label=f"{label} thread ID")
    read_tool_call_id = safe_id(
        str(raw.get("read_tool_call_id", "")), label=f"{label} read tool call ID"
    )
    fetched_at = parse_time(str(raw.get("fetched_at", "")))
    raw_mime = decode_urlsafe_payload(
        raw.get("raw_mime_base64"), label=f"{label} raw MIME"
    )
    try:
        message = BytesParser(policy=email_policy.default).parsebytes(raw_mime)
    except Exception as exc:
        raise SupervisionLogError(f"{label} raw MIME cannot be parsed") from exc
    sent_header = message.get("Date")
    rfc_message_id = str(message.get("Message-ID", "")).strip()
    if not sent_header or not rfc_message_id:
        raise SupervisionLogError(f"{label} raw MIME lacks delivery headers")
    try:
        sent_at = parsedate_to_datetime(str(sent_header)).astimezone(dt.timezone.utc)
    except (TypeError, ValueError) as exc:
        raise SupervisionLogError(f"{label} sent time is invalid") from exc
    if fetched_at < sent_at - dt.timedelta(minutes=5):
        raise SupervisionLogError(f"{label} read-back predates the message")
    normalized = {
        "provider": "gmail.read_email",
        "message_id": message_id,
        "thread_id": thread_id,
        "rfc_message_id": rfc_message_id,
        "read_tool_call_id": read_tool_call_id,
        "fetched_at": fetched_at.isoformat(),
        "sent_at": sent_at.isoformat(),
        "subject": str(message.get("Subject", "")).strip(),
        "raw_mime_sha256": hashlib.sha256(raw_mime).hexdigest(),
    }
    return normalized, message, raw_mime


def validate_terminal_gmail_readback(
    readback: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "seed_message",
        "sent_message",
        "attachments",
    }
    if set(readback) != required:
        raise SupervisionLogError("Terminal Gmail read-back shape differs")
    if (
        readback.get("schema_version") != 1
        or readback.get("kind") != "gmail-terminal-delivery-readback"
    ):
        raise SupervisionLogError("Terminal Gmail read-back version differs")
    gmail = policy.get("notifications", {}).get("gmail", {})
    seed, _seed_message, _seed_mime = validate_gmail_message_owner(
        readback.get("seed_message"), label="Terminal Gmail seed"
    )
    sent, message, _raw_mime = validate_gmail_message_owner(
        readback.get("sent_message"), label="Terminal Gmail sent message"
    )
    if seed["message_id"] != gmail.get("reply_message_id"):
        raise SupervisionLogError("Terminal Gmail read-back used another thread seed")
    if sent["message_id"] == seed["message_id"] or sent["thread_id"] != seed["thread_id"]:
        raise SupervisionLogError("Terminal Gmail sent message is not owned by the seed thread")
    in_reply_to = str(message.get("In-Reply-To", ""))
    references = str(message.get("References", ""))
    if seed["rfc_message_id"] not in {in_reply_to, *references.split()}:
        raise SupervisionLogError("Terminal Gmail sent message is not a reply to the seed")
    expected_subject = str(gmail.get("subject", "")).strip()
    seed_subject = re.sub(r"^(?:re:\s*)+", "", seed["subject"], flags=re.I)
    sent_subject = re.sub(r"^(?:re:\s*)+", "", sent["subject"], flags=re.I)
    if not expected_subject or seed_subject != expected_subject or sent_subject != expected_subject:
        raise SupervisionLogError("Terminal Gmail subject differs from the bound lane")
    mime_attachments: dict[str, bytes] = {}
    for part in message.iter_attachments():
        filename = str(part.get_filename() or "")
        if not filename or filename in mime_attachments:
            raise SupervisionLogError("Terminal Gmail MIME attachment identity differs")
        mime_attachments[filename] = part.get_payload(decode=True) or b""
    expected_attachments = {
        "delta-report.pdf": {
            "sha256": verified["delta_pdf_sha256"],
            "bytes": Path(str(verified["delta_pdf_path"])).stat().st_size,
        },
        "full-report.pdf": {
            "sha256": verified["full_pdf_sha256"],
            "bytes": Path(str(verified["full_pdf_path"])).stat().st_size,
        },
    }
    if set(mime_attachments) != set(expected_attachments):
        raise SupervisionLogError("Terminal Gmail attachment set differs")
    declared = readback.get("attachments")
    if not isinstance(declared, list) or len(declared) != 2:
        raise SupervisionLogError("Terminal Gmail read-back requires both attachments")
    normalized_attachments: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    seen_ids: set[str] = set()
    for item in declared:
        if not isinstance(item, Mapping) or set(item) != {
            "filename",
            "attachment_id",
            "owner_message_id",
            "owner_thread_id",
            "read_tool_call_id",
            "sha256",
            "bytes",
        }:
            raise SupervisionLogError("Terminal Gmail attachment receipt shape differs")
        filename = str(item.get("filename", ""))
        if filename not in expected_attachments or filename in seen_names:
            raise SupervisionLogError("Terminal Gmail attachment filename differs")
        attachment_id = safe_id(
            str(item.get("attachment_id", "")), label="Gmail attachment ID"
        )
        if attachment_id in seen_ids:
            raise SupervisionLogError("Terminal Gmail repeats an attachment ID")
        attachment_call = safe_id(
            str(item.get("read_tool_call_id", "")),
            label="Gmail attachment read tool call ID",
        )
        owner_message_id = safe_id(
            str(item.get("owner_message_id", "")),
            label="Gmail attachment owner message ID",
        )
        owner_thread_id = safe_id(
            str(item.get("owner_thread_id", "")),
            label="Gmail attachment owner thread ID",
        )
        if owner_message_id != sent["message_id"] or owner_thread_id != sent["thread_id"]:
            raise SupervisionLogError("Terminal Gmail attachment owner differs")
        payload = mime_attachments[filename]
        actual = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        if actual != expected_attachments[filename]:
            raise SupervisionLogError("Terminal Gmail MIME attachment bytes differ")
        if item.get("sha256") != actual["sha256"] or item.get("bytes") != actual["bytes"]:
            raise SupervisionLogError("Terminal Gmail attachment read-back differs")
        seen_names.add(filename)
        seen_ids.add(attachment_id)
        normalized_attachments.append(
            {
                "filename": filename,
                "attachment_id": attachment_id,
                "owner_message_id": owner_message_id,
                "owner_thread_id": owner_thread_id,
                "read_tool_call_id": attachment_call,
                **actual,
            }
        )
    normalized_attachments.sort(key=lambda item: item["filename"])
    normalized = {
        "seed_message": seed,
        "sent_message": sent,
        "attachments": normalized_attachments,
    }
    return {**normalized, "readback_root": digest(normalized)}


def append_terminal_delivery(
    *,
    args: argparse.Namespace,
    directory: Path,
    policy: Mapping[str, Any],
    verified: Mapping[str, Any],
    readback: Mapping[str, Any],
) -> dict[str, Any]:
    gmail = policy.get("notifications", {}).get("gmail", {})
    if not gmail.get("enabled") or not gmail.get("reply_message_id"):
        raise SupervisionLogError("Terminal report delivery requires the bound primary Gmail lane")
    sent_message = readback["sent_message"]
    message_id = str(sent_message["message_id"])
    with append_lock(directory):
        current_events = events(directory / "events.jsonl")
        prior = next(
            (
                item
                for item in reversed(current_events)
                if item.get("kind") == "notification"
                and item.get("category") == TERMINAL_REPORT_DELIVERY_CATEGORY
                and item.get("report_set_id") == verified["report_set_id"]
                and item.get("status") == "sent"
            ),
            None,
        )
        if prior is not None:
            if (
                prior.get("gmail_message_id") != message_id
                or prior.get("gmail_readback_root") != readback["readback_root"]
            ):
                raise SupervisionLogError("Terminal report delivery already differs")
            return prior
        record = {
            "schema_version": 1,
            "record_id": f"EVT-{len(current_events) + 1:06d}",
            "timestamp": utc_now(),
            "target_thread_id": policy["target_thread_id"],
            "kind": "notification",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": verified["state_fingerprint"],
            "status": "sent",
            "severity": "info",
            "category": TERMINAL_REPORT_DELIVERY_CATEGORY,
            "summary": "Sent accepted completion notice with both verified terminal PDF reports attached.",
            "evidence": [
                verified["completion_record_id"],
                verified["lifecycle_record_id"],
                verified["report_set_id"],
                message_id,
            ],
            "dedup_key": f"gmail-terminal:{verified['report_set_id']}",
            "report_set_id": verified["report_set_id"],
            "manifest_root": verified["manifest_root"],
            "delta_pdf_sha256": verified["delta_pdf_sha256"],
            "full_pdf_sha256": verified["full_pdf_sha256"],
            "gmail_message_id": message_id,
            "gmail_thread_id": sent_message["thread_id"],
            "gmail_rfc_message_id": sent_message["rfc_message_id"],
            "gmail_read_tool_call_id": sent_message["read_tool_call_id"],
            "gmail_readback_root": readback["readback_root"],
            "gmail_attachments": readback["attachments"],
            "gmail_readback": dict(readback),
            "policy_sha256": policy["policy_sha256"],
        }
        append_event_locked(args, directory, record)
    return record


def cmd_terminal_report_delivery(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    verified = verify_terminal_report_set(directory, args.report_set_id)
    readback = validate_terminal_gmail_readback(
        decode_terminal_gmail_readback(args.gmail_readback_base64),
        policy=policy,
        verified=verified,
    )
    record = append_terminal_delivery(
        args=args,
        directory=directory,
        policy=policy,
        verified=verified,
        readback=readback,
    )
    print(json.dumps({"record": record, "verified": verified}, sort_keys=True))


def latest_terminal_delivery(
    all_events: Sequence[Mapping[str, Any]],
    *,
    lifecycle_record_id: str,
    report_set_id: str | None = None,
) -> Mapping[str, Any] | None:
    return next(
        (
            item
            for item in reversed(all_events)
            if item.get("kind") == "notification"
            and item.get("category") == TERMINAL_REPORT_DELIVERY_CATEGORY
            and item.get("status") == "sent"
            and lifecycle_record_id in item.get("evidence", [])
            and (report_set_id is None or item.get("report_set_id") == report_set_id)
        ),
        None,
    )


def terminal_delivery_is_current(
    delivery: Mapping[str, Any], verified: Mapping[str, Any]
) -> bool:
    readback = delivery.get("gmail_readback")
    if not isinstance(readback, Mapping):
        return False
    material = {key: value for key, value in readback.items() if key != "readback_root"}
    if readback.get("readback_root") != digest(material):
        return False
    attachments = {
        str(item.get("filename")): item
        for item in readback.get("attachments", [])
        if isinstance(item, Mapping)
    }
    sent_message = readback.get("sent_message")
    if not isinstance(sent_message, Mapping):
        return False
    return bool(
        delivery.get("manifest_root") == verified["manifest_root"]
        and delivery.get("delta_pdf_sha256") == verified["delta_pdf_sha256"]
        and delivery.get("full_pdf_sha256") == verified["full_pdf_sha256"]
        and delivery.get("gmail_readback_root") == readback.get("readback_root")
        and delivery.get("gmail_message_id") == sent_message.get("message_id")
        and delivery.get("gmail_thread_id") == sent_message.get("thread_id")
        and attachments.get("delta-report.pdf", {}).get("sha256")
        == verified["delta_pdf_sha256"]
        and attachments.get("full-report.pdf", {}).get("sha256")
        == verified["full_pdf_sha256"]
        and set(attachments) == {"delta-report.pdf", "full-report.pdf"}
    )


def validated_policy_history(
    directory: Path, policy: Mapping[str, Any]
) -> list[dict[str, Any]]:
    history = events(directory / "policy-history.jsonl")
    if not history:
        raise SupervisionLogError("Supervision policy history is unavailable")
    previous_version = 0
    for item in history:
        snapshot = item.get("policy")
        if not isinstance(snapshot, dict):
            raise SupervisionLogError("Supervision policy history lacks a snapshot")
        validate_policy(snapshot)
        version = snapshot.get("policy_version")
        if type(version) is not int or version != previous_version + 1:
            raise SupervisionLogError("Supervision policy history is not contiguous")
        if item.get("record_id") != f"POLICY-{version}":
            raise SupervisionLogError("Supervision policy history identity differs")
        if snapshot.get("target_thread_id") != policy.get("target_thread_id"):
            raise SupervisionLogError("Supervision policy history target differs")
        previous_version = version
    latest = history[-1].get("policy")
    if not isinstance(latest, Mapping) or canonical(latest) != canonical(policy):
        raise SupervisionLogError("Current supervision policy differs from its history")
    return history


def supervision_group_id(
    policy: Mapping[str, Any], policy_history: Sequence[Mapping[str, Any]]
) -> str:
    genesis = policy_history[0].get("record_sha256") if policy_history else None
    if not isinstance(genesis, str) or not SHA256.fullmatch(genesis):
        raise SupervisionLogError("Supervision group genesis is unavailable")
    return "group-" + digest(
        {
            "kind": "supervision-group-identity",
            "target_thread_id": policy.get("target_thread_id"),
            "policy_history_genesis_sha256": genesis,
        }
    )


def expected_resume_automation_specs(
    policy: Mapping[str, Any],
    all_events: Sequence[Mapping[str, Any]],
    *,
    now: dt.datetime,
) -> list[dict[str, str]]:
    runtime = policy.get("runtime")
    schedule = policy.get("schedule")
    notifications = policy.get("notifications")
    reports = policy.get("reports")
    if not all(
        isinstance(item, Mapping)
        for item in (runtime, schedule, notifications, reports)
    ):
        raise SupervisionLogError("Resume automation policy is incomplete")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    schedule = schedule if isinstance(schedule, Mapping) else {}
    notifications = notifications if isinstance(notifications, Mapping) else {}
    reports = reports if isinstance(reports, Mapping) else {}
    specs: list[dict[str, str]] = []

    def add(
        role: str,
        automation_id: Any,
        target_thread_id: Any,
        rrule: str | None,
    ) -> None:
        if not isinstance(automation_id, str) or not automation_id:
            raise SupervisionLogError(f"Resume requires the bound {role} automation")
        if not isinstance(target_thread_id, str) or not target_thread_id:
            raise SupervisionLogError(f"Resume requires the bound {role} task")
        if not isinstance(rrule, str) or not rrule:
            raise SupervisionLogError(f"Resume {role} schedule is unavailable")
        specs.append(
            {
                "role": role,
                "automation_id": safe_id(automation_id, label=f"{role} automation ID"),
                "target_thread_id": safe_id(
                    target_thread_id, label=f"{role} target thread ID"
                ),
                "rrule": rrule,
            }
        )

    routine_minutes = schedule.get("routine_minutes")
    if type(routine_minutes) is not int or routine_minutes <= 0:
        raise SupervisionLogError("Resume watcher schedule is invalid")
    add(
        "watcher",
        runtime.get("routine_automation_id"),
        runtime.get("watcher_thread_id"),
        f"RRULE:FREQ=MINUTELY;INTERVAL={routine_minutes}",
    )
    meta_hours = schedule.get("meta_review_hours")
    if type(meta_hours) is not int or meta_hours <= 0:
        raise SupervisionLogError("Resume reviewer schedule is invalid")
    add(
        "reviewer",
        runtime.get("meta_automation_id"),
        runtime.get("reviewer_thread_id"),
        f"RRULE:FREQ=HOURLY;INTERVAL={meta_hours}",
    )

    gmail = notifications.get("gmail")
    gmail = gmail if isinstance(gmail, Mapping) else {}
    gmail_bound = any(
        (
            gmail.get("inbound_enabled") is True,
            runtime.get("gmail_poll_automation_id"),
            runtime.get("gmail_gate_thread_id"),
        )
    )
    if gmail_bound:
        quiet_minutes = schedule.get(
            "gmail_quiet_poll_minutes", schedule.get("gmail_poll_minutes")
        )
        active_minutes = schedule.get("gmail_active_poll_minutes")
        window_minutes = schedule.get("gmail_active_window_minutes")
        if not (
            type(quiet_minutes) is int
            and type(active_minutes) is int
            and type(window_minutes) is int
            and 2 <= quiet_minutes <= 10
            and 1 <= active_minutes < quiet_minutes
            and 5 <= window_minutes <= 120
        ):
            raise SupervisionLogError("Resume Gmail cadence policy is invalid")
        activity = next(
            (
                item
                for item in reversed(all_events)
                if is_gmail_conversation_activity(dict(item))
            ),
            None,
        )
        active_until: dt.datetime | None = None
        if activity is not None:
            active_until = parse_event_time(
                activity.get("timestamp"), label="Gmail activity timestamp"
            ) + dt.timedelta(minutes=window_minutes)
        desired_minutes = (
            active_minutes
            if active_until is not None and now < active_until
            else quiet_minutes
        )
        add(
            "gmail-gate",
            runtime.get("gmail_poll_automation_id"),
            runtime.get("gmail_gate_thread_id"),
            f"RRULE:FREQ=MINUTELY;INTERVAL={desired_minutes}",
        )

    roundup = notifications.get("gmail_roundup")
    roundup = roundup if isinstance(roundup, Mapping) else {}
    weekly = reports.get("weekly")
    weekly = weekly if isinstance(weekly, Mapping) else {}
    roundup_bound = any(
        (
            roundup.get("enabled") is True,
            runtime.get("roundup_automation_id"),
        )
    )
    if roundup_bound:
        times = schedule.get("roundup_local_times")
        if not isinstance(times, list) or not times:
            raise SupervisionLogError("Resume roundup schedule is unavailable")
        parsed_times: list[tuple[int, int]] = []
        for value in times:
            if not isinstance(value, str) or not re.fullmatch(
                r"(?:[01]\d|2[0-3]):[0-5]\d", value
            ):
                raise SupervisionLogError("Resume roundup schedule is invalid")
            hour, minute = (int(part) for part in value.split(":"))
            parsed_times.append((hour, minute))
        minutes = {minute for _, minute in parsed_times}
        hours = {hour for hour, _ in parsed_times}
        if len(minutes) != 1 or len(hours) != len(parsed_times):
            raise SupervisionLogError("Resume roundup schedule is ambiguous")
        add(
            "roundup-writer",
            runtime.get("roundup_automation_id"),
            runtime.get("roundup_thread_id"),
            "RRULE:FREQ=DAILY;"
            + "BYHOUR="
            + ",".join(str(hour) for hour, _ in parsed_times)
            + f";BYMINUTE={parsed_times[0][1]};BYSECOND=0",
        )

    if weekly.get("enabled") is True:
        weekday = weekly.get("weekday")
        local_time = weekly.get("local_time")
        if weekday not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"} or not (
            isinstance(local_time, str)
            and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", local_time)
        ):
            raise SupervisionLogError("Resume weekly-report schedule is invalid")
        hour, minute = (int(part) for part in local_time.split(":"))
        add(
            "weekly-report",
            weekly.get("automation_id"),
            runtime.get("roundup_thread_id"),
            "RRULE:FREQ=WEEKLY;"
            f"BYDAY={weekday};BYHOUR={hour};BYMINUTE={minute};BYSECOND=0",
        )

    automation_ids = [item["automation_id"] for item in specs]
    if len(automation_ids) != len(set(automation_ids)):
        raise SupervisionLogError(
            "Resume automation bindings reuse one owner for multiple roles"
        )
    return specs


def resume_automation_owner_state(spec: Mapping[str, str]) -> dict[str, Any]:
    automation_id = safe_id(spec.get("automation_id"), label="automation ID")
    owner_root = CODEX_AUTOMATIONS_ROOT.expanduser().resolve(strict=True)
    automation_directory = owner_root / automation_id
    config_path = automation_directory / "automation.toml"
    if automation_directory.is_symlink() or config_path.is_symlink():
        raise SupervisionLogError("Resume automation owner path is symlinked")
    try:
        resolved = config_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SupervisionLogError(
            f"Resume automation owner is missing: {automation_id}"
        ) from exc
    if resolved.parent.parent != owner_root:
        raise SupervisionLogError("Resume automation owner path escaped")
    with resolved.open("rb") as handle:
        raw = handle.read(MAX_AUTOMATION_OWNER_BYTES + 1)
    if len(raw) > MAX_AUTOMATION_OWNER_BYTES:
        raise SupervisionLogError("Resume automation owner is oversized")
    try:
        config = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SupervisionLogError("Resume automation owner is invalid") from exc
    expected_fields = {
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
    if set(config) != expected_fields or config.get("version") != 1:
        raise SupervisionLogError("Resume automation owner shape differs")
    if config.get("id") != automation_id:
        raise SupervisionLogError("Resume automation owner identity differs")
    if config.get("kind") != "heartbeat":
        raise SupervisionLogError("Resume automation owner kind differs")
    if config.get("target_thread_id") != spec.get("target_thread_id"):
        raise SupervisionLogError("Resume automation target differs")
    if config.get("rrule") != spec.get("rrule"):
        raise SupervisionLogError("Resume automation schedule differs")
    if config.get("status") not in {"ACTIVE", "PAUSED"}:
        raise SupervisionLogError("Resume automation state is unsupported")
    if not isinstance(config.get("name"), str) or not isinstance(
        config.get("prompt"), str
    ):
        raise SupervisionLogError("Resume automation owner text is malformed")
    if any(
        type(config.get(field)) is not int for field in ("created_at", "updated_at")
    ):
        raise SupervisionLogError("Resume automation owner timestamps are malformed")
    configuration = {
        key: config[key]
        for key in (
            "version",
            "id",
            "kind",
            "name",
            "prompt",
            "rrule",
            "target_thread_id",
            "created_at",
        )
    }
    return {
        "automation_id": automation_id,
        "role": str(spec.get("role", "")),
        "status": config["status"],
        "rrule": config["rrule"],
        "target_thread_id": config["target_thread_id"],
        "updated_at": config["updated_at"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "configuration_sha256": digest(configuration),
    }


def stable_resume_automation_states(
    specs: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    first = {
        str(spec["automation_id"]): resume_automation_owner_state(spec)
        for spec in specs
    }
    second = {
        str(spec["automation_id"]): resume_automation_owner_state(spec)
        for spec in specs
    }
    if first != second:
        raise SupervisionLogError("Resume automation owners changed during validation")
    return first


def is_canonical_supervision_pause(item: Mapping[str, Any]) -> bool:
    return bool(
        item.get("kind") == "lifecycle"
        and item.get("status") == "paused"
        and item.get("category") == SUPERVISION_PAUSE_CATEGORY
        and isinstance(item.get("state_fingerprint"), str)
        and item.get("state_fingerprint")
    )


def is_eligible_resume_source(item: Mapping[str, Any]) -> bool:
    evidence = item.get("evidence")
    role = (item.get("model"), item.get("reasoning"))
    return bool(
        is_completion_check(dict(item))
        and item.get("status") == "no-intervention"
        and role
        in {
            ("gpt-5.6-terra", "max"),
            ("gpt-5.6-sol", "xhigh"),
        }
        and isinstance(evidence, list)
        and 1 <= len(evidence) <= 16
        and all(isinstance(value, str) and value for value in evidence)
    )


def resume_source_currentness_material(
    *,
    target_thread_id: str,
    group_id: str,
    mission_root: str,
    mission_source_record: str,
    policy_version: int,
    policy_sha256: str,
    policy_history_head: str,
    policy_history_count: int,
    event_head: str,
    event_count: int,
    pause_record: Mapping[str, Any],
    source_record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "target_thread_id": target_thread_id,
        "group_id": group_id,
        "mission_root": mission_root,
        "mission_source_record": mission_source_record,
        "policy_version": policy_version,
        "policy_sha256": policy_sha256,
        "policy_history_head": policy_history_head,
        "policy_history_count": policy_history_count,
        "event_head": event_head,
        "event_count": event_count,
        "pause_record_id": pause_record.get("record_id"),
        "pause_record_sha256": pause_record.get("record_sha256"),
        "source_record_id": source_record.get("record_id"),
        "source_record_sha256": source_record.get("record_sha256"),
        "state_fingerprint": source_record.get("state_fingerprint"),
    }


def supervision_resume_record_is_canonical(
    record: Mapping[str, Any],
    all_events: Sequence[Mapping[str, Any]],
    policy_history: Sequence[Mapping[str, Any]],
) -> bool:
    try:
        if not (
            record.get("resume_contract_version") == SUPERVISION_RESUME_CONTRACT_VERSION
            and record.get("kind") == "lifecycle"
            and record.get("category") == SUPERVISION_RESUME_CATEGORY
            and record.get("status") == "resumed"
        ):
            return False
        index = next(
            idx
            for idx, item in enumerate(all_events)
            if item.get("record_id") == record.get("record_id")
        )
        if record.get("record_id") != f"EVT-{index + 1:06d}":
            return False
        if record.get("event_count_before_resume") != index:
            return False
        expected_previous = (
            all_events[index - 1].get("record_sha256") if index else None
        )
        if record.get("previous_record_sha256") != expected_previous:
            return False
        by_id = {
            str(item.get("record_id")): item
            for item in all_events[:index]
            if isinstance(item.get("record_id"), str)
        }
        pause = by_id.get(str(record.get("pause_record_id", "")))
        source = by_id.get(str(record.get("source_record_id", "")))
        if pause is None or source is None or not is_canonical_supervision_pause(pause):
            return False
        if not is_eligible_resume_source(source):
            return False
        if any(
            item.get("target_thread_id") != record.get("target_thread_id")
            for item in (pause, source)
        ):
            return False
        if pause.get("record_sha256") != record.get("pause_record_sha256"):
            return False
        if source.get("record_sha256") != record.get("source_record_sha256"):
            return False
        if source.get("state_fingerprint") != record.get("state_fingerprint"):
            return False
        if source.get("policy_sha256") != record.get("policy_sha256"):
            return False
        pause_time = parse_event_time(
            pause.get("timestamp"), label="Pause lifecycle timestamp"
        )
        source_time = parse_event_time(
            source.get("timestamp"), label="Resume source timestamp"
        )
        resume_time = parse_event_time(
            record.get("timestamp"), label="Resume lifecycle timestamp"
        )
        if not pause_time < source_time <= resume_time:
            return False
        history_count = record.get("policy_history_count")
        if type(history_count) is not int or not 1 <= history_count <= len(
            policy_history
        ):
            return False
        history_head = policy_history[history_count - 1]
        if history_head.get("record_sha256") != record.get("policy_history_head"):
            return False
        snapshot = history_head.get("policy")
        if not isinstance(snapshot, Mapping):
            return False
        binding = bound_mission(dict(snapshot))
        if binding is None:
            return False
        group_id = supervision_group_id(snapshot, policy_history[:history_count])
        if group_id != record.get("group_id"):
            return False
        if (
            snapshot.get("policy_sha256") != record.get("policy_sha256")
            or snapshot.get("policy_version") != record.get("policy_version")
            or binding.get("mission_root") != record.get("mission_root")
            or binding.get("mission_source_record")
            != record.get("mission_source_record")
        ):
            return False
        source_material = resume_source_currentness_material(
            target_thread_id=str(record.get("target_thread_id", "")),
            group_id=group_id,
            mission_root=str(record.get("mission_root", "")),
            mission_source_record=str(record.get("mission_source_record", "")),
            policy_version=int(record.get("policy_version")),
            policy_sha256=str(record.get("policy_sha256", "")),
            policy_history_head=str(record.get("policy_history_head", "")),
            policy_history_count=history_count,
            event_head=str(record.get("previous_record_sha256", "")),
            event_count=index,
            pause_record=pause,
            source_record=source,
        )
        if digest(source_material) != record.get("source_currentness_root"):
            return False
        expectations = record.get("automation_expectations")
        states = record.get("automation_states")
        if not isinstance(expectations, list) or not isinstance(states, Mapping):
            return False
        schedule_evaluated_at = parse_event_time(
            record.get("schedule_evaluated_at"),
            label="Resume schedule evaluation timestamp",
        )
        if expectations != expected_resume_automation_specs(
            snapshot,
            all_events[:index],
            now=schedule_evaluated_at,
        ):
            return False
        expected_ids = {
            str(item.get("automation_id"))
            for item in expectations
            if isinstance(item, Mapping)
        }
        if not expected_ids or expected_ids != set(states):
            return False
        configuration_roots: dict[str, str] = {}
        for expectation in expectations:
            if not isinstance(expectation, Mapping):
                return False
            automation_id = str(expectation.get("automation_id", ""))
            state = states.get(automation_id)
            if not isinstance(state, Mapping):
                return False
            if any(
                state.get(key) != expectation.get(expected_key)
                for key, expected_key in (
                    ("automation_id", "automation_id"),
                    ("role", "role"),
                    ("rrule", "rrule"),
                    ("target_thread_id", "target_thread_id"),
                )
            ):
                return False
            if state.get("status") != "ACTIVE":
                return False
            updated_at = state.get("updated_at")
            if (
                type(updated_at) is not int
                or dt.datetime.fromtimestamp(updated_at / 1000, tz=dt.timezone.utc)
                <= pause_time
            ):
                return False
            configuration_sha256 = state.get("configuration_sha256")
            if not isinstance(configuration_sha256, str) or not SHA256.fullmatch(
                configuration_sha256
            ):
                return False
            configuration_roots[automation_id] = configuration_sha256
        if configuration_roots != record.get("automation_configuration_roots"):
            return False
        eligibility_material = {
            "kind": "supervision-resume-eligibility",
            "contract_version": SUPERVISION_RESUME_CONTRACT_VERSION,
            "source_currentness_root": record.get("source_currentness_root"),
            "automation_expectations": expectations,
            "automation_configuration_roots": configuration_roots,
        }
        if digest(eligibility_material) != record.get("eligibility_root"):
            return False
        if digest(states) != record.get("automation_evidence_root"):
            return False
        if record.get("evidence") != [
            record.get("pause_record_id"),
            record.get("source_record_id"),
            *sorted(states),
        ]:
            return False
        expected_resume_id = "resume-" + digest(
            {
                "target_thread_id": record.get("target_thread_id"),
                "pause_record_id": record.get("pause_record_id"),
                "eligibility_root": record.get("eligibility_root"),
            }
        )
        return record.get("resume_id") == expected_resume_id
    except (KeyError, StopIteration, TypeError, ValueError, SupervisionLogError):
        return False


def resume_context(
    directory: Path,
    policy: dict[str, Any],
    *,
    pause_record_id: str,
    source_record_id: str,
    state_fingerprint: str,
) -> dict[str, Any]:
    policy_history = validated_policy_history(directory, policy)
    all_events = events(directory / "events.jsonl")
    binding = bound_mission(policy)
    if binding is None:
        raise SupervisionLogError("Resume requires an active mission binding")
    active_events = mission_scoped_events(directory, policy, all_events)
    active_ids = {
        str(item.get("record_id")): item
        for item in active_events
        if isinstance(item.get("record_id"), str)
    }
    pause = active_ids.get(pause_record_id)
    source = active_ids.get(source_record_id)
    if pause is None or not is_canonical_supervision_pause(pause):
        raise SupervisionLogError("Resume requires the exact current paused lifecycle")
    if source is None:
        raise SupervisionLogError("Resume source record is outside the active mission")
    if not is_eligible_resume_source(source):
        raise SupervisionLogError(
            "Resume source must be the current eligible watcher or semantic check"
        )
    if source.get("target_thread_id") != policy.get("target_thread_id"):
        raise SupervisionLogError("Resume source target differs")
    if source.get("policy_sha256") != policy.get("policy_sha256"):
        raise SupervisionLogError("Resume source policy is stale")
    if source.get("state_fingerprint") != state_fingerprint or not state_fingerprint:
        raise SupervisionLogError("Resume source fingerprint differs")
    pause_time = parse_event_time(pause.get("timestamp"), label="Pause timestamp")
    source_time = parse_event_time(
        source.get("timestamp"), label="Resume source timestamp"
    )
    if source_record_id == pause_record_id or source_time <= pause_time:
        raise SupervisionLogError(
            "Resume requires a distinct current source after the paused lifecycle"
        )
    lifecycle_events = [
        item for item in active_events if item.get("kind") == "lifecycle"
    ]
    if not lifecycle_events:
        raise SupervisionLogError("Resume lifecycle history is unavailable")
    latest_lifecycle = lifecycle_events[-1]
    if latest_lifecycle.get("record_id") != pause_record_id:
        if latest_lifecycle.get(
            "pause_record_id"
        ) == pause_record_id and supervision_resume_record_is_canonical(
            latest_lifecycle, all_events, policy_history
        ):
            if latest_lifecycle.get("mission_root") != binding.get("mission_root"):
                raise SupervisionLogError(
                    "Existing resume lifecycle belongs to another mission"
                )
            if all_events[-1].get("record_id") != latest_lifecycle.get("record_id"):
                raise SupervisionLogError(
                    "Existing resume lifecycle is no longer the current event head"
                )
            return {
                "already_resumed": latest_lifecycle,
                "policy_history": policy_history,
                "all_events": all_events,
                "pause_time": pause_time,
            }
        raise SupervisionLogError("Paused lifecycle is no longer current")
    fingerprint_events = [
        item
        for item in active_events
        if isinstance(item.get("state_fingerprint"), str)
        and item.get("state_fingerprint")
        and parse_event_time(item.get("timestamp"), label="Source timestamp")
        >= pause_time
    ]
    if (
        not fingerprint_events
        or fingerprint_events[-1].get("record_id") != source_record_id
    ):
        raise SupervisionLogError("Resume source record is stale")
    group_id = supervision_group_id(policy, policy_history)
    history_head = policy_history[-1]
    event_head = all_events[-1].get("record_sha256") if all_events else None
    if not isinstance(event_head, str):
        raise SupervisionLogError("Resume event head is unavailable")
    source_material = resume_source_currentness_material(
        target_thread_id=str(policy["target_thread_id"]),
        group_id=group_id,
        mission_root=str(binding["mission_root"]),
        mission_source_record=str(binding["mission_source_record"]),
        policy_version=int(policy["policy_version"]),
        policy_sha256=str(policy["policy_sha256"]),
        policy_history_head=str(history_head["record_sha256"]),
        policy_history_count=len(policy_history),
        event_head=event_head,
        event_count=len(all_events),
        pause_record=pause,
        source_record=source,
    )
    return {
        "already_resumed": None,
        "policy_history": policy_history,
        "all_events": all_events,
        "pause": pause,
        "source": source,
        "pause_time": pause_time,
        "group_id": group_id,
        "binding": binding,
        "source_material": source_material,
        "source_currentness_root": digest(source_material),
    }


def resume_basis(
    directory: Path,
    policy: dict[str, Any],
    *,
    pause_record_id: str,
    source_record_id: str,
    state_fingerprint: str,
    now: dt.datetime,
) -> dict[str, Any]:
    context = resume_context(
        directory,
        policy,
        pause_record_id=pause_record_id,
        source_record_id=source_record_id,
        state_fingerprint=state_fingerprint,
    )
    specs = expected_resume_automation_specs(policy, context["all_events"], now=now)
    states = stable_resume_automation_states(specs)
    pause_time = context["pause_time"]
    for state in states.values():
        updated_at = dt.datetime.fromtimestamp(
            int(state["updated_at"]) / 1000, tz=dt.timezone.utc
        )
        if state["status"] == "ACTIVE" and updated_at <= pause_time:
            raise SupervisionLogError(
                "Active resume automation state does not postdate the paused lifecycle"
            )
    configuration_roots = {
        automation_id: str(state["configuration_sha256"])
        for automation_id, state in states.items()
    }
    if context.get("already_resumed") is not None:
        if not all(state["status"] == "ACTIVE" for state in states.values()):
            raise SupervisionLogError(
                "Existing resume lifecycle has incomplete current automation state"
            )
        context.update(
            {
                "automation_expectations": specs,
                "automation_states": states,
                "automation_configuration_roots": configuration_roots,
                "activate_automation_ids": [],
                "ready_to_finalize": True,
            }
        )
        return context
    eligibility_material = {
        "kind": "supervision-resume-eligibility",
        "contract_version": SUPERVISION_RESUME_CONTRACT_VERSION,
        "source_currentness_root": context["source_currentness_root"],
        "automation_expectations": specs,
        "automation_configuration_roots": configuration_roots,
    }
    context.update(
        {
            "automation_expectations": specs,
            "schedule_evaluated_at": now.astimezone(dt.timezone.utc).isoformat(),
            "automation_states": states,
            "automation_configuration_roots": configuration_roots,
            "eligibility_root": digest(eligibility_material),
            "activate_automation_ids": sorted(
                automation_id
                for automation_id, state in states.items()
                if state["status"] == "PAUSED"
            ),
            "ready_to_finalize": all(
                state["status"] == "ACTIVE" for state in states.values()
            ),
        }
    )
    return context


def cmd_resume_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    pause_record_id = safe_id(args.pause_record, label="pause record ID")
    source_record_id = safe_id(args.source_record, label="source record ID")
    state_fingerprint = clean(
        args.state_fingerprint, label="state fingerprint", maximum=128
    )
    basis = resume_basis(
        directory,
        policy,
        pause_record_id=pause_record_id,
        source_record_id=source_record_id,
        state_fingerprint=state_fingerprint,
        now=dt.datetime.now(dt.timezone.utc),
    )
    after_directory, after_policy = load_policy(args)
    after_history = validated_policy_history(after_directory, after_policy)
    after_events = events(after_directory / "events.jsonl")
    if (
        after_directory.resolve() != directory.resolve()
        or after_policy.get("policy_sha256") != policy.get("policy_sha256")
        or len(after_history) != len(basis["policy_history"])
        or after_history[-1].get("record_sha256")
        != basis["policy_history"][-1].get("record_sha256")
        or len(after_events) != len(basis["all_events"])
        or after_events[-1].get("record_sha256")
        != basis["all_events"][-1].get("record_sha256")
    ):
        raise SupervisionLogError("Resume source changed during eligibility validation")
    existing = basis.get("already_resumed")
    if isinstance(existing, Mapping):
        print(
            json.dumps(
                {
                    "status": "already-resumed",
                    "eligible": True,
                    "ready_to_finalize": True,
                    "duplicate": True,
                    "resume_record": existing,
                    "policy_sha256": policy["policy_sha256"],
                    "action": "none",
                },
                sort_keys=True,
            )
        )
        return
    print(
        json.dumps(
            {
                "status": (
                    "ready" if basis["ready_to_finalize"] else "pending-activation"
                ),
                "eligible": True,
                "ready_to_finalize": basis["ready_to_finalize"],
                "duplicate": False,
                "action": (
                    "resume-finalize"
                    if basis["ready_to_finalize"]
                    else "activate-exact-bound-automations"
                ),
                "activate_automation_ids": basis["activate_automation_ids"],
                "automation_states": basis["automation_states"],
                "eligibility_root": basis["eligibility_root"],
                "source_currentness_root": basis["source_currentness_root"],
                "pause_record_id": pause_record_id,
                "source_record_id": source_record_id,
                "state_fingerprint": state_fingerprint,
                "group_id": basis["group_id"],
                "mission_root": basis["binding"]["mission_root"],
                "policy_version": policy["policy_version"],
                "policy_sha256": policy["policy_sha256"],
            },
            sort_keys=True,
        )
    )


def cmd_resume_finalize(args: argparse.Namespace) -> None:
    directory, _ = load_policy(args)
    pause_record_id = safe_id(args.pause_record, label="pause record ID")
    source_record_id = safe_id(args.source_record, label="source record ID")
    state_fingerprint = clean(
        args.state_fingerprint, label="state fingerprint", maximum=128
    )
    eligibility_root = exact_sha256(
        args.eligibility_root, label="resume eligibility root"
    )
    with append_lock(directory):
        directory, policy = load_policy(args)
        basis = resume_basis(
            directory,
            policy,
            pause_record_id=pause_record_id,
            source_record_id=source_record_id,
            state_fingerprint=state_fingerprint,
            now=dt.datetime.now(dt.timezone.utc),
        )
        prior = basis.get("already_resumed")
        if isinstance(prior, Mapping):
            if any(
                prior.get(key) != value
                for key, value in (
                    ("source_record_id", source_record_id),
                    ("state_fingerprint", state_fingerprint),
                    ("eligibility_root", eligibility_root),
                )
            ):
                raise SupervisionLogError("Existing resume lifecycle record differs")
            print(
                json.dumps(
                    {"duplicate": True, "record": prior, "postcondition": "resumed"},
                    sort_keys=True,
                )
            )
            return
        policy_history = basis["policy_history"]
        current_events = basis["all_events"]
        if basis["eligibility_root"] != eligibility_root:
            raise SupervisionLogError("Resume eligibility is stale")
        if not basis["ready_to_finalize"]:
            raise SupervisionLogError(
                "Resume remains pending until every exact bound automation is active"
            )
        # Re-read only the named owners under the append boundary. This detects
        # an owner transition between validation and the canonical append.
        final_states = stable_resume_automation_states(basis["automation_expectations"])
        if final_states != basis["automation_states"]:
            raise SupervisionLogError(
                "Resume automation owners changed before finalization"
            )
        automation_evidence_root = digest(final_states)
        resume_id = "resume-" + digest(
            {
                "target_thread_id": args.target_thread,
                "pause_record_id": pause_record_id,
                "eligibility_root": eligibility_root,
            }
        )
        source_material = basis["source_material"]
        record = {
            "schema_version": 1,
            "resume_contract_version": SUPERVISION_RESUME_CONTRACT_VERSION,
            "record_id": f"EVT-{len(current_events) + 1:06d}",
            "timestamp": utc_now(),
            "target_thread_id": args.target_thread,
            "kind": "lifecycle",
            "model": "supervision_log.py",
            "reasoning": "deterministic",
            "state_fingerprint": state_fingerprint,
            "status": "resumed",
            "severity": "info",
            "category": SUPERVISION_RESUME_CATEGORY,
            "summary": "Every exact bound supervision automation is active at its maintained schedule; the paused lifecycle is canonically resumed.",
            "evidence": [
                pause_record_id,
                source_record_id,
                *sorted(final_states),
            ],
            "dedup_key": f"supervision-resume:{pause_record_id}",
            "resume_id": resume_id,
            "pause_record_id": pause_record_id,
            "pause_record_sha256": basis["pause"]["record_sha256"],
            "source_record_id": source_record_id,
            "source_record_sha256": basis["source"]["record_sha256"],
            "source_currentness_root": basis["source_currentness_root"],
            "eligibility_root": eligibility_root,
            "automation_expectations": basis["automation_expectations"],
            "schedule_evaluated_at": basis["schedule_evaluated_at"],
            "automation_configuration_roots": basis["automation_configuration_roots"],
            "automation_states": final_states,
            "automation_evidence_root": automation_evidence_root,
            "group_id": basis["group_id"],
            "mission_root": basis["binding"]["mission_root"],
            "mission_source_record": basis["binding"]["mission_source_record"],
            "policy_version": policy["policy_version"],
            "policy_sha256": policy["policy_sha256"],
            "policy_history_head": source_material["policy_history_head"],
            "policy_history_count": source_material["policy_history_count"],
            "event_count_before_resume": source_material["event_count"],
        }
        candidate = dict(record)
        candidate["previous_record_sha256"] = current_events[-1]["record_sha256"]
        candidate["record_sha256"] = digest(candidate)
        if not supervision_resume_record_is_canonical(
            candidate, [*current_events, candidate], policy_history
        ):
            raise SupervisionLogError(
                "Candidate resume lifecycle record failed verification"
            )
        append_event_locked(args, directory, record)
        persisted = events(directory / "events.jsonl")[-1]
        if not supervision_resume_record_is_canonical(
            persisted, events(directory / "events.jsonl"), policy_history
        ):
            raise SupervisionLogError(
                "Persisted resume lifecycle record failed verification"
            )
    print(
        json.dumps(
            {"duplicate": False, "record": persisted, "postcondition": "resumed"},
            sort_keys=True,
        )
    )


def expected_terminal_automation_ids(policy: Mapping[str, Any]) -> list[str]:
    runtime = policy.get("runtime", {})
    values = [
        runtime.get("routine_automation_id"),
        runtime.get("meta_automation_id"),
        runtime.get("gmail_poll_automation_id"),
        runtime.get("roundup_automation_id"),
        policy.get("reports", {}).get("weekly", {}).get("automation_id"),
    ]
    automation_ids = [
        safe_id(str(item), label="terminal automation ID") for item in values if item
    ]
    if len(automation_ids) != len(set(automation_ids)):
        raise SupervisionLogError(
            "Terminal supervision roles must bind distinct automations"
        )
    return sorted(automation_ids)


def terminal_automation_owner_states(
    automation_ids: list[str],
    *,
    not_before: dt.datetime,
    automation_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    owner_root = (automation_root or CODEX_AUTOMATIONS_ROOT).resolve()
    states: dict[str, dict[str, Any]] = {}
    for automation_id in automation_ids:
        safe_id(automation_id, label="automation ID")
        automation_directory = owner_root / automation_id
        config_path = automation_directory / "automation.toml"
        if automation_directory.is_symlink() or config_path.is_symlink():
            raise SupervisionLogError("Terminal automation owner path is symlinked")
        try:
            resolved = config_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise SupervisionLogError(
                f"Terminal automation owner is missing: {automation_id}"
            ) from exc
        if resolved.parent.parent != owner_root:
            raise SupervisionLogError("Terminal automation owner path escaped")
        raw = resolved.read_bytes()
        try:
            config = tomllib.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise SupervisionLogError("Terminal automation owner is invalid") from exc
        if config.get("id") != automation_id:
            raise SupervisionLogError("Terminal automation owner identity differs")
        if str(config.get("status", "")).upper() != "PAUSED":
            raise SupervisionLogError(
                "Every terminal supervision automation must be paused"
            )
        updated_at = config.get("updated_at")
        if not isinstance(updated_at, int):
            raise SupervisionLogError("Terminal automation owner lacks update time")
        updated = dt.datetime.fromtimestamp(updated_at / 1000, tz=dt.timezone.utc)
        if updated < not_before:
            raise SupervisionLogError(
                "Terminal automation pause predates report delivery"
            )
        states[automation_id] = {
            "status": "PAUSED",
            "updated_at": updated_at,
            "kind": str(config.get("kind", "")),
            "target_thread_id": str(config.get("target_thread_id", "")),
            "config_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return states


def terminal_shutdown_record_is_canonical(
    record: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    delivery: Mapping[str, Any],
    verified: Mapping[str, Any],
    automation_states: Mapping[str, Mapping[str, Any]],
) -> bool:
    try:
        record_id = record.get("record_id")
        timestamp = record.get("timestamp")
        record_sha256 = record.get("record_sha256")
        previous_record_sha256 = record.get("previous_record_sha256")
        recorded_at = dt.datetime.fromisoformat(
            str(timestamp).strip().replace("Z", "+00:00")
        )
        if recorded_at.tzinfo is None:
            return False
        recorded_at = recorded_at.astimezone(dt.timezone.utc)
        delivered_at = parse_time(str(delivery.get("timestamp", "")))
        owner_updates = [
            dt.datetime.fromtimestamp(
                int(state["updated_at"]) / 1000,
                tz=dt.timezone.utc,
            )
            for state in automation_states.values()
            if isinstance(state, Mapping) and type(state.get("updated_at")) is int
        ]
        material = {
            key: value for key, value in record.items() if key != "record_sha256"
        }
        return bool(
            record.get("schema_version") == 1
            and isinstance(record_id, str)
            and SAFE_ID.fullmatch(record_id)
            and isinstance(timestamp, str)
            and len(owner_updates) == len(automation_states)
            and recorded_at >= delivered_at
            and all(recorded_at >= updated for updated in owner_updates)
            and isinstance(record_sha256, str)
            and SHA256.fullmatch(record_sha256)
            and isinstance(previous_record_sha256, str)
            and SHA256.fullmatch(previous_record_sha256)
            and digest(material) == record_sha256
            and record.get("target_thread_id") == policy.get("target_thread_id")
            and record.get("kind") == "check"
            and record.get("model") == "gpt-5.6-sol"
            and record.get("reasoning") == "xhigh"
            and record.get("state_fingerprint") == lifecycle.get("state_fingerprint")
            and record.get("status") == "verified"
            and record.get("severity") == "info"
            and record.get("category") == TERMINAL_SHUTDOWN_CATEGORY
            and record.get("summary")
            == "Viewed every bound supervision automation in paused state after terminal report delivery."
            and record.get("evidence")
            == [
                lifecycle.get("record_id"),
                verified.get("report_set_id"),
                delivery.get("record_id"),
            ]
            and record.get("report_set_id") == verified.get("report_set_id")
            and record.get("manifest_root") == verified.get("manifest_root")
            and sorted(automation_states) == expected_terminal_automation_ids(policy)
            and record.get("automation_states") == automation_states
            and record.get("automation_state_root") == digest(automation_states)
            and record.get("policy_sha256") == policy.get("policy_sha256")
        )
    except (SupervisionLogError, TypeError, ValueError):
        return False

def cmd_terminal_shutdown(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    expected_event_head = clean(
        args.expected_event_head,
        label="expected terminal event head",
        maximum=64,
    )
    if not SHA256.fullmatch(expected_event_head):
        raise SupervisionLogError("Expected terminal event head is invalid")
    all_events = events(directory / "events.jsonl")
    lifecycle = next(
        (item for item in all_events if item.get("record_id") == args.lifecycle_record),
        None,
    )
    if lifecycle is None or lifecycle.get("status") != "completed":
        raise SupervisionLogError("Terminal shutdown requires the completed lifecycle")
    delivery = latest_terminal_delivery(
        all_events,
        lifecycle_record_id=args.lifecycle_record,
        report_set_id=args.report_set_id,
    )
    if delivery is None:
        raise SupervisionLogError(
            "Terminal shutdown requires delivered report attachments"
        )
    verified = verify_terminal_report_set(directory, args.report_set_id)
    if not terminal_delivery_is_current(delivery, verified):
        raise SupervisionLogError("Terminal shutdown report delivery is stale")
    expected = expected_terminal_automation_ids(policy)
    if not expected:
        raise SupervisionLogError("Terminal shutdown has no bound automations")
    states = terminal_automation_owner_states(
        expected, not_before=parse_time(str(delivery.get("timestamp", "")))
    )
    with append_lock(directory):
        current_directory, current_policy = load_policy(args)
        if (
            current_directory.resolve() != directory.resolve()
            or current_policy.get("target_thread_id") != args.target_thread
            or current_policy.get("policy_sha256") != policy.get("policy_sha256")
        ):
            raise SupervisionLogError(
                "Terminal shutdown policy changed before receipt append"
            )
        current_events = events(directory / "events.jsonl")
        stop_heads = terminal_stop_head_snapshot(
            directory, current_policy, current_events
        )
        prior = next(
            (
                item
                for item in reversed(current_events)
                if item.get("kind") == "check"
                and item.get("category") == TERMINAL_SHUTDOWN_CATEGORY
                and item.get("report_set_id") == args.report_set_id
                and item.get("status") == "verified"
            ),
            None,
        )
        if stop_heads["open_incident_ids"] or stop_heads["open_decision_ids"]:
            raise SupervisionLogError(
                "Terminal shutdown requires closed current incidents and decisions"
            )
        if (
            stop_heads["open_successor_transitions"]
            or stop_heads["open_mission_activations"]
        ):
            raise SupervisionLogError(
                "Terminal shutdown requires closed successor and activation heads"
            )
        if prior is not None:
            if not terminal_shutdown_record_is_canonical(
                prior,
                policy=policy,
                lifecycle=lifecycle,
                delivery=delivery,
                verified=verified,
                automation_states=states,
            ):
                raise SupervisionLogError("Terminal shutdown receipt already differs")
            if (
                prior.get("previous_record_sha256") != expected_event_head
                or stop_heads["event_head"] != prior.get("record_sha256")
            ):
                raise SupervisionLogError(
                    "Terminal shutdown receipt is not current for the expected event head"
                )
            print(json.dumps({"duplicate": True, "record": prior}, sort_keys=True))
            return
        if stop_heads["event_head"] != expected_event_head:
            raise SupervisionLogError(
                "Terminal shutdown event head changed before receipt append"
            )
        record = {
            "schema_version": 1,
            "record_id": f"EVT-{len(current_events) + 1:06d}",
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "target_thread_id": args.target_thread,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": str(lifecycle.get("state_fingerprint", "")),
            "status": "verified",
            "severity": "info",
            "category": TERMINAL_SHUTDOWN_CATEGORY,
            "summary": "Viewed every bound supervision automation in paused state after terminal report delivery.",
            "evidence": [
                args.lifecycle_record,
                args.report_set_id,
                str(delivery.get("record_id")),
            ],
            "report_set_id": args.report_set_id,
            "manifest_root": verified["manifest_root"],
            "automation_states": states,
            "automation_state_root": digest(states),
            "policy_sha256": policy["policy_sha256"],
        }
        append_event_locked(args, directory, record)
        persisted = events(directory / "events.jsonl")[-1]
        if not terminal_shutdown_record_is_canonical(
            persisted,
            policy=policy,
            lifecycle=lifecycle,
            delivery=delivery,
            verified=verified,
            automation_states=states,
        ):
            raise SupervisionLogError(
                "Persisted terminal shutdown receipt failed verification"
            )
    print(json.dumps({"duplicate": False, "record": persisted}, sort_keys=True))


def cmd_terminal_report(args: argparse.Namespace) -> None:
    if args.action == "prepare":
        if not args.lifecycle_record:
            raise SupervisionLogError("Terminal report prepare requires --lifecycle-record")
        cmd_terminal_report_prepare(args)
        return
    if args.action == "finalize":
        if not args.report_set_id or not args.review_base64:
            raise SupervisionLogError("Terminal report finalize requires --report-set-id and --review-base64")
        cmd_terminal_report_finalize(args)
        return
    if args.action == "verify":
        if not args.report_set_id:
            raise SupervisionLogError("Terminal report verify requires --report-set-id")
        cmd_terminal_report_verify(args)
        return
    if args.action == "record-delivery":
        if not args.report_set_id or not args.gmail_readback_base64:
            raise SupervisionLogError(
                "Terminal report delivery requires the report and exact Gmail read-back"
            )
        cmd_terminal_report_delivery(args)
        return
    raise SupervisionLogError("Unsupported terminal report action")


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
    active_events = mission_scoped_events(directory, policy, all_events)
    incident_events = [item for item in active_events if item.get("kind") == "incident"]
    incident_heads: dict[str, dict[str, Any]] = {}
    for item in active_events:
        current_incident_id = item.get("incident_id")
        # Delivery receipts are projections of an incident outcome, not a
        # lifecycle transition. Keep the latest substantive incident record as
        # the head so email status such as `sent` cannot hide `under-review`,
        # `awaiting-target-evidence`, or a terminal resolution.
        if current_incident_id and is_substantive_incident_record(
            item, str(current_incident_id)
        ):
            incident_heads[current_incident_id] = item
    open_incidents = [
        item
        for item in incident_heads.values()
        if not is_terminal_incident_record(item, str(item["incident_id"]))
    ]
    open_incident_ids = [item["incident_id"] for item in open_incidents]
    last = last_check(active_events)
    meta_reviews = [item for item in active_events if item.get("kind") == "meta-review"]
    notification_events = [
        item for item in active_events if item.get("kind") == "notification"
    ]
    inbound_events = [
        item for item in active_events if item.get("kind") == "inbound-message"
    ]
    roundup_events = [item for item in active_events if item.get("kind") == "roundup"]
    lifecycle_events = [
        item for item in active_events if item.get("kind") == "lifecycle"
    ]
    policy_history_path = directory / "policy-history.jsonl"
    resume_policy_history = (
        events(policy_history_path) if policy_history_path.exists() else []
    )
    supervision_resume_events = [
        item
        for item in lifecycle_events
        if supervision_resume_record_is_canonical(
            item, all_events, resume_policy_history
        )
    ]
    current_supervision_pause: Mapping[str, Any] | None = None
    valid_resume_ids = {
        str(item.get("record_id")) for item in supervision_resume_events
    }
    for item in lifecycle_events:
        if is_canonical_supervision_pause(item):
            current_supervision_pause = item
        elif (
            str(item.get("record_id")) in valid_resume_ids
            and current_supervision_pause is not None
            and item.get("pause_record_id")
            == current_supervision_pause.get("record_id")
        ):
            current_supervision_pause = None
    outcome_completion_events = [
        item
        for item in active_events
        if item.get("kind") == "check"
        and item.get("category") == OUTCOME_COMPLETION_CATEGORY
    ]
    terminal_report_deliveries = [
        item
        for item in active_events
        if item.get("kind") == "notification"
        and item.get("category") == TERMINAL_REPORT_DELIVERY_CATEGORY
    ]
    terminal_shutdown_events = [
        item
        for item in active_events
        if item.get("kind") == "check"
        and item.get("category") == TERMINAL_SHUTDOWN_CATEGORY
    ]
    decision_heads: dict[str, dict[str, Any]] = {}
    for item in active_events:
        if item.get("kind") == "decision" and item.get("decision_id"):
            decision_heads[str(item["decision_id"])] = item
    open_decisions = [
        item
        for item in decision_heads.values()
        if item.get("phase") != "target-acknowledged"
    ]
    activation_heads = mission_activation_heads(active_events)
    open_activations = mission_activation_heads(active_events, open_only=True)
    current_activation = (
        list(activation_heads.values())[-1] if activation_heads else None
    )
    transition_heads = successor_transition_heads(active_events)
    open_transitions = successor_transition_heads(active_events, open_only=True)
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
                "last_supervision_resume": (
                    supervision_resume_events[-1] if supervision_resume_events else None
                ),
                "current_supervision_pause": current_supervision_pause,
                "supervision_resume_supported": True,
                "last_outcome_completion": (
                    outcome_completion_events[-1]
                    if outcome_completion_events
                    else None
                ),
                "last_terminal_report_delivery": (
                    terminal_report_deliveries[-1]
                    if terminal_report_deliveries
                    else None
                ),
                "last_terminal_shutdown": (
                    terminal_shutdown_events[-1]
                    if terminal_shutdown_events
                    else None
                ),
                "decision_count": len(decision_heads),
                "open_decisions": open_decisions,
                "mission_activation_count": len(activation_heads),
                "current_mission_activation": current_activation,
                "open_mission_activations": list(open_activations.values()),
                "mission_activation_action": (
                    MISSION_ACTIVATION_START_ACTION
                    if open_activations
                    else "none"
                ),
                "mission_activation_required_target_posture": (
                    "in-progress" if open_activations else None
                ),
                "successor_transition_count": len(transition_heads),
                "open_successor_transitions": list(open_transitions.values()),
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Maintain bounded tracker supervision records"
    )
    result.add_argument("--root", help="Override the supervision root for testing")
    subparsers = result.add_subparsers(dest="command", required=True)

    mission_plan = subparsers.add_parser("mission-plan")
    mission_plan.add_argument("--target-thread", required=True)
    mission_plan.add_argument(
        "--mission-source-class",
        choices=sorted(DIRECT_AUTHORITY_SOURCE_CLASSES),
        required=True,
    )
    mission_plan.add_argument("--mission-source-record", required=True)
    mission_plan.add_argument("--mission-source-sha256", required=True)
    mission_plan.set_defaults(func=cmd_mission_plan)

    init = subparsers.add_parser("init")
    init.add_argument("--target-thread", required=True)
    init.add_argument("--target-label", required=True)
    init.add_argument("--watcher-thread", required=True)
    init.add_argument("--reviewer-thread", required=True)
    init.add_argument("--base-reviewer-thread")
    init.add_argument("--notice-reviewer-thread")
    init.add_argument("--fix-executor-thread")
    init.add_argument("--mission-root")
    init.add_argument("--mission-source-record")
    init.add_argument(
        "--mission-source-class", choices=sorted(DIRECT_AUTHORITY_SOURCE_CLASSES)
    )
    init.add_argument("--mission-source-sha256")
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
    bind.add_argument("--mission-root")
    bind.add_argument("--mission-source-record")
    bind.add_argument(
        "--mission-source-class", choices=sorted(DIRECT_AUTHORITY_SOURCE_CLASSES)
    )
    bind.add_argument("--mission-source-sha256")
    bind.set_defaults(func=cmd_bind)

    mission_successor = subparsers.add_parser("mission-successor")
    mission_successor.add_argument("--target-thread", required=True)
    mission_successor.add_argument("--from-mission-root", required=True)
    mission_successor.add_argument(
        "--mission-source-class",
        choices=sorted(DIRECT_AUTHORITY_SOURCE_CLASSES),
        required=True,
    )
    mission_successor.add_argument("--mission-source-record", required=True)
    mission_successor.add_argument("--mission-source-sha256", required=True)
    mission_successor.add_argument(
        "--predecessor-disposition",
        choices=("completed", "superseded"),
        required=True,
    )
    mission_successor.add_argument("--first-eligible-work", required=True)
    mission_successor.add_argument("--reason", required=True)
    mission_successor.add_argument("--evidence", action="append", default=[])
    mission_successor.set_defaults(func=cmd_mission_successor)

    mission_activation_start = subparsers.add_parser("mission-activation-start")
    mission_activation_start.add_argument("--target-thread", required=True)
    mission_activation_start.add_argument("--mission-root", required=True)
    mission_activation_start.add_argument("--activation-policy-sha256", required=True)
    mission_activation_start.add_argument("--first-eligible-work", required=True)
    mission_activation_start.add_argument("--source-record", required=True)
    mission_activation_start.add_argument("--evidence", action="append", required=True)
    mission_activation_start.set_defaults(func=cmd_mission_activation_start)

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
    thread_route_gate.add_argument("--containment", action="store_true")
    thread_route_gate.add_argument("--mission-root")
    thread_route_gate.add_argument(
        "--authority-source-class", choices=sorted(AUTHORITY_SOURCE_CLASSES)
    )
    thread_route_gate.add_argument("--authority-source-record")
    thread_route_gate.add_argument(
        "--impact-class", choices=sorted(MISSION_IMPACT_CLASSES)
    )
    thread_route_gate.add_argument("--affected-width")
    thread_route_gate.add_argument("--duration")
    thread_route_gate.add_argument(
        "--reversibility", choices=sorted(REVERSIBILITY_POSTURES)
    )
    thread_route_gate.add_argument("--ordinary-means-disabled", choices=["yes", "no"])
    thread_route_gate.add_argument(
        "--independent-mission-review", choices=["yes", "no"]
    )
    thread_route_gate.add_argument("--operation-scope")
    thread_route_gate.add_argument("--block-scope")
    thread_route_gate.add_argument("--scope-identity")
    thread_route_gate.add_argument("--expiry-event")
    thread_route_gate.add_argument("--carry-forward", choices=["true", "false"])
    thread_route_gate.add_argument(
        "--successor-effects", choices=["allowed", "blocked"]
    )
    thread_route_gate.add_argument(
        "--severity", choices=sorted(SEVERITIES), default="info"
    )
    thread_route_gate.add_argument("--incident-id")
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
    record.add_argument(
        "--notice-disposition", choices=["", *sorted(NOTICE_DISPOSITIONS)], default=""
    )
    record.add_argument(
        "--resolution-owner", choices=["", *sorted(RESOLUTION_OWNERS)], default=""
    )
    record.add_argument("--user-action-required", choices=["", "yes", "no"], default="")
    record.add_argument("--containment", action="store_true")
    record.add_argument("--mission-root")
    record.add_argument(
        "--authority-source-class", choices=sorted(AUTHORITY_SOURCE_CLASSES)
    )
    record.add_argument("--authority-source-record")
    record.add_argument("--impact-class", choices=sorted(MISSION_IMPACT_CLASSES))
    record.add_argument("--affected-width")
    record.add_argument("--duration")
    record.add_argument("--reversibility", choices=sorted(REVERSIBILITY_POSTURES))
    record.add_argument("--ordinary-means-disabled", choices=["yes", "no"])
    record.add_argument("--independent-mission-review", choices=["yes", "no"])
    record.add_argument("--operation-scope")
    record.add_argument("--block-scope")
    record.add_argument("--scope-identity")
    record.add_argument("--expiry-event")
    record.add_argument("--carry-forward", choices=["true", "false"])
    record.add_argument("--successor-effects", choices=["allowed", "blocked"])
    record.add_argument("--failure-mode", action="store_true")
    record.add_argument("--failure-mode-id")
    record.add_argument("--failure-layer", choices=sorted(FAILURE_MODE_LAYERS))
    record.add_argument("--failure-mechanism")
    record.add_argument("--failure-trigger")
    record.add_argument("--failure-effect")
    record.add_argument("--failure-detection")
    record.add_argument("--failure-correction")
    record.add_argument("--failure-recurrence-invariant")
    record.add_argument("--failure-human-scheduling-leak", choices=["yes", "no"])
    record.add_argument(
        "--reusable-lane-disposition",
        choices=list(REUSABLE_LANE_DISPOSITIONS),
    )
    record.add_argument("--reusable-lane-owner", default="")
    record.add_argument("--reusable-lane-evidence", action="append", default=[])
    record.add_argument("--reusable-lane-rationale", default="")
    record.set_defaults(func=cmd_record)

    completion_record = subparsers.add_parser("completion-record")
    completion_record.add_argument("--target-thread", required=True)
    completion_record.add_argument("--state-fingerprint", required=True)
    completion_record.add_argument("--current-revision", required=True)
    completion_record.add_argument("--mission-root", required=True)
    completion_record.add_argument(
        "--status", choices=sorted(OUTCOME_COMPLETION_STATUSES), required=True
    )
    completion_record.add_argument("--model", required=True)
    completion_record.add_argument(
        "--reasoning", choices=["xhigh", "max"], required=True
    )
    completion_record.add_argument("--outcome-manifest-sha256", required=True)
    completion_record.add_argument("--artifact-currentness-sha256", required=True)
    completion_record.add_argument("--effect-reconciliation-sha256", required=True)
    completion_record.add_argument("--open-item-compatibility-sha256", required=True)
    completion_record.add_argument("--independent-challenge-sha256", required=True)
    completion_record.add_argument("--capability-reconciliation-json", required=True)
    completion_record.add_argument("--active-block", default="")
    completion_record.add_argument("--checkpoint", default="")
    completion_record.add_argument("--summary", required=True)
    completion_record.add_argument("--evidence", action="append", required=True)
    completion_record.set_defaults(func=cmd_completion_record)

    notice_gate = subparsers.add_parser("notice-gate")
    notice_gate.add_argument("--target-thread", required=True)
    notice_gate.add_argument("--incident-id", required=True)
    notice_gate.add_argument("--source-record", required=True)
    notice_gate.add_argument(
        "--notice-disposition", choices=sorted(NOTICE_DISPOSITIONS), required=True
    )
    notice_gate.add_argument(
        "--resolution-owner", choices=sorted(RESOLUTION_OWNERS), required=True
    )
    notice_gate.add_argument(
        "--user-action-required", choices=["yes", "no"], required=True
    )
    notice_gate.add_argument(
        "--severity", choices=sorted(SEVERITIES), default="warning"
    )
    notice_gate.set_defaults(func=cmd_notice_gate)

    lifecycle_gate = subparsers.add_parser("lifecycle-gate")
    lifecycle_gate.add_argument("--target-thread", required=True)
    lifecycle_gate.add_argument(
        "--lifecycle-state", choices=sorted(LIFECYCLE_STATES), required=True
    )
    lifecycle_gate.add_argument("--source-record", required=True)
    lifecycle_gate.add_argument("--state-fingerprint", default="")
    lifecycle_gate.add_argument("--terminal-report-set-id")
    lifecycle_gate.set_defaults(func=cmd_lifecycle_gate)

    resume_gate = subparsers.add_parser("resume-gate")
    resume_gate.add_argument("--target-thread", required=True)
    resume_gate.add_argument("--pause-record", required=True)
    resume_gate.add_argument("--source-record", required=True)
    resume_gate.add_argument("--state-fingerprint", required=True)
    resume_gate.set_defaults(func=cmd_resume_gate)

    resume_finalize = subparsers.add_parser("resume-finalize")
    resume_finalize.add_argument("--target-thread", required=True)
    resume_finalize.add_argument("--pause-record", required=True)
    resume_finalize.add_argument("--source-record", required=True)
    resume_finalize.add_argument("--state-fingerprint", required=True)
    resume_finalize.add_argument("--eligibility-root", required=True)
    resume_finalize.set_defaults(func=cmd_resume_finalize)

    decision_record = subparsers.add_parser("decision-record")
    decision_record.add_argument("--target-thread", required=True)
    decision_record.add_argument("--decision-id", required=True)
    decision_record.add_argument(
        "--classification", choices=sorted(DECISION_CLASSIFICATIONS), required=True
    )
    decision_record.add_argument(
        "--phase", choices=sorted(DECISION_PHASES), required=True
    )
    decision_record.add_argument(
        "--safe-frontier", choices=sorted(SAFE_FRONTIER_POSTURES), required=True
    )
    decision_record.add_argument("--attempt", type=int, default=0)
    decision_record.add_argument(
        "--outcome", choices=sorted(DECISION_OUTCOMES), default=""
    )
    decision_record.add_argument("--decision-packet-hash", required=True)
    decision_record.add_argument("--blocked-scope-hash", required=True)
    decision_record.add_argument("--safe-frontier-hash", required=True)
    decision_record.add_argument("--state-fingerprint", default="")
    decision_record.add_argument("--evidence", action="append", required=True)
    decision_record.add_argument("--mission-root", required=True)
    decision_record.add_argument(
        "--authority-source-class",
        choices=sorted(AUTHORITY_SOURCE_CLASSES),
        required=True,
    )
    decision_record.add_argument("--authority-source-record", required=True)
    decision_record.add_argument(
        "--impact-class", choices=sorted(MISSION_IMPACT_CLASSES), required=True
    )
    decision_record.add_argument("--affected-width", required=True)
    decision_record.add_argument("--duration", required=True)
    decision_record.add_argument(
        "--reversibility", choices=sorted(REVERSIBILITY_POSTURES), required=True
    )
    decision_record.add_argument(
        "--ordinary-means-disabled", choices=["yes", "no"], required=True
    )
    decision_record.add_argument(
        "--independent-mission-review", choices=["yes", "no"], required=True
    )
    decision_record.add_argument("--now")
    decision_record.set_defaults(func=cmd_decision_record)

    decision_gate = subparsers.add_parser("decision-gate")
    decision_gate.add_argument("--target-thread", required=True)
    decision_gate.add_argument("--decision-id", required=True)
    decision_gate.add_argument("--now")
    decision_gate.set_defaults(func=cmd_decision_gate)

    successor_record = subparsers.add_parser("successor-transition-record")
    successor_record.add_argument("--target-thread", required=True)
    successor_record.add_argument("--transition-id", required=True)
    successor_record.add_argument(
        "--phase", choices=SUCCESSOR_TRANSITION_PHASES, required=True
    )
    successor_record.add_argument("--tracker-sha256", required=True)
    successor_record.add_argument("--tracker-source-record", required=True)
    successor_record.add_argument("--requested-block-range", required=True)
    successor_record.add_argument("--first-eligible-block", required=True)
    successor_record.add_argument("--source-mission-root", required=True)
    successor_record.add_argument(
        "--governing-authority-source-class",
        choices=sorted(AUTHORITY_SOURCE_CLASSES),
        required=True,
    )
    successor_record.add_argument("--governing-authority-source-record", required=True)
    successor_record.add_argument("--successor-thread", default="")
    successor_record.add_argument("--successor-mission-root", default="")
    successor_record.add_argument("--successor-group-id", default="")
    successor_record.add_argument("--handoff-record", default="")
    successor_record.add_argument("--acknowledgement-record", default="")
    successor_record.add_argument("--started-block", default="")
    successor_record.add_argument("--state-fingerprint", default="")
    successor_record.add_argument("--evidence", action="append", required=True)
    successor_record.add_argument("--now")
    successor_record.set_defaults(func=cmd_successor_transition_record)

    successor_gate = subparsers.add_parser("successor-transition-gate")
    successor_gate.add_argument("--target-thread", required=True)
    successor_gate.add_argument("--transition-id", required=True)
    successor_gate.add_argument(
        "--task-creation-authority",
        choices=("available", "unavailable"),
        default="unavailable",
    )
    successor_gate.set_defaults(func=cmd_successor_transition_gate)

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

    weekly_report = subparsers.add_parser("weekly-report")
    weekly_report.add_argument("--target-thread", required=True)
    weekly_report.add_argument(
        "--action",
        choices=(
            "prepare",
            "finalize",
            "verify",
            "status",
            "record-delivery",
            "configure",
        ),
        required=True,
    )
    weekly_report.add_argument("--start")
    weekly_report.add_argument("--end")
    weekly_report.add_argument("--days", type=int, default=7)
    weekly_report.add_argument("--since-inception", action="store_true")
    weekly_report.add_argument("--report-id")
    weekly_report.add_argument("--review-base64")
    weekly_report.add_argument("--gmail-readback-base64")
    weekly_report.add_argument("--automation-id")
    weekly_report.add_argument(
        "--weekday",
        choices=("MO", "TU", "WE", "TH", "FR", "SA", "SU"),
        default="MO",
    )
    weekly_report.add_argument("--local-time", default="08:00")
    weekly_report.set_defaults(func=cmd_weekly_report)

    factory_evolution = subparsers.add_parser("factory-evolution")
    factory_evolution.add_argument("--target-thread", required=True)
    factory_evolution.add_argument("--evolution-id", required=True)
    factory_evolution.add_argument(
        "--action",
        choices=("prepare", "finalize", "evaluate", "verify"),
        required=True,
    )
    factory_evolution.add_argument(
        "--report-json", dest="report_paths", action="append", default=[]
    )
    factory_evolution.add_argument(
        "--events-jsonl", dest="event_paths", action="append", default=[]
    )
    factory_evolution.add_argument("--review-json")
    factory_evolution.add_argument("--evaluation-json")
    factory_evolution.set_defaults(func=cmd_factory_evolution)

    terminal_report = subparsers.add_parser("terminal-report")
    terminal_report.add_argument("--target-thread", required=True)
    terminal_report.add_argument(
        "--action",
        choices=("prepare", "finalize", "verify", "record-delivery"),
        required=True,
    )
    terminal_report.add_argument("--lifecycle-record")
    terminal_report.add_argument("--report-set-id")
    terminal_report.add_argument("--review-base64")
    terminal_report.add_argument("--gmail-readback-base64")
    terminal_report.set_defaults(func=cmd_terminal_report)

    terminal_shutdown = subparsers.add_parser("terminal-shutdown")
    terminal_shutdown.add_argument("--target-thread", required=True)
    terminal_shutdown.add_argument("--lifecycle-record", required=True)
    terminal_shutdown.add_argument("--report-set-id", required=True)
    terminal_shutdown.add_argument("--expected-event-head", required=True)
    terminal_shutdown.set_defaults(func=cmd_terminal_shutdown)

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
