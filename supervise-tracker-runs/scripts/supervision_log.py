#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import difflib
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import unicodedata
from contextlib import contextmanager
from email import policy as email_policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterator, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 maintained host runtime.
    import tomli as tomllib


DEFAULT_ROOT = Path.home() / ".codex" / "supervision" / "tracker-runs"
CODEX_AUTOMATIONS_ROOT = Path(__file__).resolve().parents[3] / "automations"
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
    "implementation-range",
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
MAX_ADAPTIVE_CANDIDATE_EVIDENCE_BYTES = 64 * 1024
MAX_ADAPTIVE_DECISION_EVIDENCE_BYTES = 64 * 1024
MAX_ADAPTIVE_REVIEW_EVIDENCE_BYTES = 64 * 1024
ADAPTIVE_REVIEWER_ID = "software-factory-release-reviewer-v1"
ADAPTIVE_EVALUATOR_ID = "software-factory-adaptive-evaluator-v1"
ADAPTIVE_REVIEW_PUBLIC_KEY_PATH = Path(
    "/Users/ethanstillman/.codex/software-factory-release-authority/"
    "reviewers/software-factory-release-reviewer-v1.pem"
)
ADAPTIVE_REVIEW_OPENSSL_PATH = Path(
    "/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl"
)
ADAPTIVE_REVIEW_OPENSSL_SHA256 = (
    "bf63843e6856e1994ca71092ff3b46834236eb2144dd9b6ceb85d511128b836e"
)
ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256 = (
    "e6ace9dfbbf97ec65800d1da146c4b59b20a2aef86ad706b174b9837bcb41a02"
)
ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH = Path(
    "/Users/ethanstillman/.codex/software-factory-release-authority/"
    "evaluators/software-factory-adaptive-evaluator-v1.pem"
)
ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256 = (
    "179f04afb14b47ed7d48560e21fcaa91979974ad2e39de41e4d35ea8e70c898c"
)
TERMINAL_REPORT_DELIVERY_CATEGORY = "gmail-terminal-completion"
TERMINAL_SHUTDOWN_CATEGORY = "terminal-supervision-shutdown"
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
ADAPTIVE_DECISION_MODES = {
    "fixed",
    "recommend",
    "reviewed-autonomous",
    "full-autonomous",
}
ADAPTIVE_DISPOSITIONS = {
    "continue-unchanged",
    "correct-inline",
    "compare-candidate",
    "cutover-candidate",
    "amend-structure",
}
ADAPTIVE_JUDGMENT_CLASSES = {
    "ordinary-engineering",
    "consequential-product-tradeoff",
    "reserved-external",
    "material-goal-change",
}
ADAPTIVE_CONSEQUENCE_CLASSES = {"routine", "low-moderate", "consequential"}
ADAPTIVE_REVIEWED_DISPOSITIONS = {
    "compare-candidate",
    "cutover-candidate",
    "amend-structure",
}
ADAPTIVE_PERMISSION_FIELDS = {
    "repository_write",
    "command_or_test_execution",
    "bounded_thread_steer",
    "bounded_supervision_maintenance",
    "allowlisted_skill_maintenance",
    "gmail_self_notification",
    "gmail_inbound_processing",
    "gmail_priority_notification",
    "gmail_roundup_notification",
    "production_promotion",
    "release",
    "deployment",
    "destructive_action",
    "spend",
    "credential_access",
    "external_action",
}
ADAPTIVE_TARGET_CLASSES = {"target-repository", "software-factory"}
ADAPTIVE_EFFECT_CLASSES = {
    "no-mutation",
    "implementation-write",
    "candidate-isolated-write",
    "production-cutover",
    "tracker-amendment",
    "skill-maintenance",
    "skill-release-cutover",
    "deployment",
    "destructive-action",
    "spend",
    "credential-access",
    "external-action",
}
ADAPTIVE_DISPOSITION_EFFECTS = {
    "continue-unchanged": {"no-mutation"},
    "correct-inline": {"implementation-write", "skill-maintenance"},
    "compare-candidate": {"candidate-isolated-write"},
    "cutover-candidate": {"production-cutover", "skill-release-cutover"},
    "amend-structure": {"tracker-amendment"},
}
ADAPTIVE_EFFECT_PERMISSIONS = {
    "no-mutation": [],
    "implementation-write": ["repository_write"],
    "candidate-isolated-write": [
        "repository_write",
        "command_or_test_execution",
    ],
    "production-cutover": ["repository_write", "production_promotion"],
    "tracker-amendment": ["repository_write"],
    "skill-maintenance": ["repository_write", "allowlisted_skill_maintenance"],
    "skill-release-cutover": [
        "repository_write",
        "allowlisted_skill_maintenance",
        "release",
        "production_promotion",
    ],
    "deployment": ["repository_write", "deployment"],
    "destructive-action": ["destructive_action"],
    "spend": ["spend"],
    "credential-access": ["credential_access"],
    "external-action": ["external_action"],
}


def adaptive_effect_class(target_class: str, disposition: str) -> str:
    if target_class not in ADAPTIVE_TARGET_CLASSES or disposition not in ADAPTIVE_DISPOSITIONS:
        raise SupervisionLogError("Adaptive target or disposition is unsupported")
    if disposition == "continue-unchanged":
        return "no-mutation"
    if disposition == "compare-candidate":
        return "candidate-isolated-write"
    if disposition == "amend-structure":
        return "tracker-amendment"
    if disposition == "correct-inline":
        return "skill-maintenance" if target_class == "software-factory" else "implementation-write"
    return "skill-release-cutover" if target_class == "software-factory" else "production-cutover"
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
    "corrected",
}
SAFE_FRONTIER_POSTURES = {"empty", "nonempty"}
DECISION_OUTCOMES = {"", "selected", "safe-deferred", "user-supplied"}
DECISION_CORRECTION_PHASES = {"corrected"}
DECISION_GOVERNING_OUTCOME_EFFECTS = {"continue-governing-outcome"}
DECISION_IMMUTABLE_FIELDS = (
    "state_fingerprint",
    "decision_packet_hash",
    "blocked_scope_hash",
    "safe_frontier_hash",
)
SUCCESSOR_TRANSITION_PHASES = (
    "required",
    "successor-created",
    "successor-bound",
    "handoff-sent",
    "target-acknowledged",
    "work-started",
)
SUCCESSOR_TRANSITION_TERMINAL_PHASES = (
    "corrected",
    "superseded",
    "cancelled",
    "expired",
)
SUCCESSOR_TRANSITION_ALL_PHASES = (
    *SUCCESSOR_TRANSITION_PHASES,
    *SUCCESSOR_TRANSITION_TERMINAL_PHASES,
)
SUCCESSOR_TRANSITION_CLOSED_PHASES = {
    "work-started",
    *SUCCESSOR_TRANSITION_TERMINAL_PHASES,
}
SUCCESSOR_TOPOLOGY_POSTURES = {"same-task-new-run", "distinct-task"}
SUCCESSOR_TOPOLOGY_BASES = {
    "same-task-default",
    "direct-request",
    "technical-isolation",
    "legacy-linear",
}
SUCCESSOR_GOVERNING_OUTCOME_EFFECTS = {
    "continue-same-task",
    "continue-replacement-transition",
}
MAX_SUCCESSOR_TRANSITION_HOURS = 24
IMPLEMENTATION_RANGE_INTENTS = {"full-tracker", "explicit-blocks"}
IMPLEMENTATION_RANGE_RESPONSE_KINDS = (
    "block-boundary",
    "commit-boundary",
    "review-boundary",
    "handoff-boundary",
    "push-boundary",
    "final-response",
    "outcome-terminal",
)
SKILL_RELEASE_PUBLICATION_STATUSES = (
    "published",
    "unavailable",
    "failed",
)
DIRECT_AUTHORITY_EVENT_KIND = "direct-user-authority-source"
LEGACY_DIRECT_AUTHORITY_PROVENANCE_KIND = (
    "legacy-direct-user-authority-provenance"
)
LEGACY_DIRECT_AUTHORITY_REVIEW_CATEGORY = (
    "legacy-direct-authority-ingestion"
)
LEGACY_DIRECT_AUTHORITY_CLASSIFICATION = (
    "author-then-implement-full-tracker"
)
TRACKER_AMENDMENT_EVENT_KIND = "implementation-tracker-amendment"
SUCCESSOR_TOPOLOGY_EVENT_KIND = "successor-topology-decision"
EVENT_LEDGER_ANCHOR_NAME = "events-head.json"
OWNER_ROOT_HISTORY_NAME = "owner-root-history.jsonl"
OWNER_ROOT_KEY_DIRECTORY = ".owner-root-keys"
MAX_IMPLEMENTATION_TRACKER_BYTES = 2 * 1024 * 1024
MAX_LEGACY_DIRECT_AUTHORITY_PROVENANCE_BYTES = 4096
IMPLEMENTATION_BLOCK_HEADING = re.compile(r"^## Block (\d+)\b", re.MULTILINE)
IMPLEMENTATION_TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")
SUCCESSOR_TRANSITION_IDENTITY_FIELDS = (
    "tracker_sha256",
    "tracker_source_record",
    "requested_block_range",
    "first_eligible_block",
    "source_mission_root",
    "governing_authority_source_class",
    "governing_authority_source_record",
    "governing_authority_source_sha256",
    "topology_posture",
    "topology_basis",
    "topology_rationale",
    "topology_request_sha256",
    "topology_decision_event_record_id",
    "topology_decision_event_sha256",
    "transition_expires_at",
    "replaces_transition_id",
)
MAX_GOVERNING_OUTCOME_MEMBERS = 8
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


def adaptive_candidate_budget_contract() -> dict[str, Any]:
    return {
        "max_active_lanes_per_decision": 1,
        "max_active_lanes_per_target": 1,
        "max_files": 3,
        "max_changed_lines": 120,
        "max_commands": 6,
        "max_elapsed_minutes": 20,
        "max_mapped_comparisons": 1,
        "max_review_passes": 1,
        "independent_review_required": True,
        "stop_on_resource_exhaustion": True,
        "stop_on_protected_regression": True,
    }


def adaptive_decision_control_contract(
    mode: str = "full-autonomous",
    *,
    candidate_budget: Mapping[str, Any] | None = None,
    target_class: str = "target-repository",
    target_repository_root: str | None = None,
) -> dict[str, Any]:
    if mode not in ADAPTIVE_DECISION_MODES:
        raise SupervisionLogError("Unsupported adaptive-decision mode")
    if target_class not in ADAPTIVE_TARGET_CLASSES:
        raise SupervisionLogError("Unsupported adaptive target class")
    budget = dict(candidate_budget or adaptive_candidate_budget_contract())
    return {
        "schema_version": 1,
        "adaptive_decision_mode": mode,
        "target_class": target_class,
        "target_repository_root": target_repository_root,
        "candidate_budget": budget,
        "unchanged_fast_path": "fingerprint-currentness-only",
        "permission_posture": "never-expand-non-adaptive-permissions",
        "required_independent_review": sorted(ADAPTIVE_REVIEWED_DISPOSITIONS),
        "software_factory_mutation_independent_review": True,
        "input_avoidance": {
            "enabled": mode == "full-autonomous",
            "ordinary_human_request_limit": 0 if mode == "full-autonomous" else 1,
            "automated_review_pass_limit": 1,
            "reversible_default": "safest-source-backed-option",
            "assumption_posture": "bounded-assumption-with-revisit-trigger",
            "unavailable_act_posture": "reserved-external-no-request",
            "continue_safe_frontier": True,
        },
    }


def validate_adaptive_decision_control(value: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "adaptive_decision_mode",
        "target_class",
        "target_repository_root",
        "candidate_budget",
        "unchanged_fast_path",
        "permission_posture",
        "required_independent_review",
        "software_factory_mutation_independent_review",
        "input_avoidance",
    }
    mode = value.get("adaptive_decision_mode")
    if (
        frozenset(value) not in {
            frozenset(expected_keys),
            frozenset(expected_keys - {"target_repository_root"}),
        }
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != 1
        or mode not in ADAPTIVE_DECISION_MODES
        or value.get("target_class") not in ADAPTIVE_TARGET_CLASSES
        or value.get("unchanged_fast_path") != "fingerprint-currentness-only"
        or value.get("permission_posture")
        != "never-expand-non-adaptive-permissions"
        or value.get("required_independent_review")
        != sorted(ADAPTIVE_REVIEWED_DISPOSITIONS)
        or value.get("software_factory_mutation_independent_review") is not True
    ):
        raise SupervisionLogError("Adaptive-decision control contract differs")
    repository_root = value.get("target_repository_root")
    if repository_root is not None:
        if type(repository_root) is not str or not repository_root.startswith("/"):
            raise SupervisionLogError("Adaptive target repository root must be absolute")
        root_path = Path(repository_root)
        if "." in root_path.parts or ".." in root_path.parts:
            raise SupervisionLogError("Adaptive target repository root must be normalized")
        try:
            resolved_root = root_path.resolve(strict=True)
        except OSError as exc:
            raise SupervisionLogError("Adaptive target repository root is unavailable") from exc
        if resolved_root != root_path or root_path == Path("/") or not root_path.is_dir():
            raise SupervisionLogError("Adaptive target repository root is not canonical")
        git_result = subprocess.run(
            ["/usr/bin/git", "-C", str(root_path), "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        if (
            git_result.returncode != 0
            or Path(git_result.stdout.strip()).resolve(strict=True) != root_path
        ):
            raise SupervisionLogError(
                "Adaptive target repository root is not the exact Git top level"
            )
    budget = value.get("candidate_budget")
    expected_budget_keys = set(adaptive_candidate_budget_contract())
    if not isinstance(budget, Mapping) or set(budget) != expected_budget_keys:
        raise SupervisionLogError("Adaptive candidate budget shape differs")
    exact_limits = {
        "max_active_lanes_per_decision": (1, 1),
        "max_active_lanes_per_target": (1, 1),
        "max_files": (1, 3),
        "max_changed_lines": (1, 5000),
        "max_commands": (1, 6),
        "max_elapsed_minutes": (1, 240),
        "max_mapped_comparisons": (1, 1),
        "max_review_passes": (1, 1),
    }
    for field, (minimum, maximum) in exact_limits.items():
        item = budget.get(field)
        if type(item) is not int or not minimum <= item <= maximum:
            raise SupervisionLogError(f"Adaptive candidate budget {field} is invalid")
    for field in (
        "independent_review_required",
        "stop_on_resource_exhaustion",
        "stop_on_protected_regression",
    ):
        if budget.get(field) is not True:
            raise SupervisionLogError(f"Adaptive candidate budget {field} must remain enabled")
    input_avoidance = value.get("input_avoidance")
    expected_input = adaptive_decision_control_contract(str(mode))["input_avoidance"]
    if input_avoidance != expected_input:
        raise SupervisionLogError("Adaptive input-avoidance contract differs")


def ensure_adaptive_decision_policy(
    policy: dict[str, Any], *, mode: str = "full-autonomous"
) -> bool:
    changed = False
    current = policy.get("adaptive_decision_control")
    if current is None:
        policy["adaptive_decision_control"] = adaptive_decision_control_contract(mode)
        changed = True
    elif not isinstance(current, Mapping):
        raise SupervisionLogError("Adaptive-decision policy is malformed")
    else:
        if "target_repository_root" not in current:
            current = dict(current)
            current["target_repository_root"] = None
            policy["adaptive_decision_control"] = current
            changed = True
        validate_adaptive_decision_control(current)
    permissions = policy.setdefault("permissions", {})
    for field in ADAPTIVE_PERMISSION_FIELDS:
        if field not in permissions:
            permissions[field] = False
            changed = True
    return changed


def effective_adaptive_decision_mode(policy: Mapping[str, Any]) -> str:
    value = policy.get("adaptive_decision_control")
    if value is None:
        return "fixed"
    if not isinstance(value, Mapping):
        raise SupervisionLogError("Adaptive-decision policy is malformed")
    validate_adaptive_decision_control(value)
    return str(value["adaptive_decision_mode"])


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


def file_snapshot(stat: os.stat_result) -> tuple[int, int, int, int]:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def path_snapshot(path: Path) -> tuple[int, int, int, int] | None:
    try:
        return file_snapshot(path.lstat())
    except OSError:
        return None


def read_text_snapshot(
    path: Path,
    *,
    missing_ok: bool = False,
    directory_fd: int | None = None,
) -> tuple[str, tuple[int, int, int, int] | None]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        if missing_ok:
            return "", None
        raise
    try:
        before = file_snapshot(os.fstat(descriptor))
        handle = os.fdopen(descriptor, "r", encoding="utf-8")
        descriptor = -1
        with handle:
            text = handle.read()
            after = file_snapshot(os.fstat(handle.fileno()))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if before != after:
        raise SupervisionLogError(f"Supervision state changed while reading: {path.name}")
    return text, after


def read_json_snapshot(
    path: Path, *, directory_fd: int | None = None
) -> tuple[dict[str, Any], tuple[int, int, int, int]]:
    try:
        raw, snapshot = read_text_snapshot(path, directory_fd=directory_fd)
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise SupervisionLogError(f"Cannot read supervision state: {path.name}") from exc
    if not isinstance(value, dict):
        raise SupervisionLogError(f"Supervision state is not an object: {path.name}")
    assert snapshot is not None
    return value, snapshot


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


def atomic_json_at(directory_fd: int, name: str, value: dict[str, Any]) -> None:
    temporary_name = f".{name}.{secrets.token_hex(12)}"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
    try:
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8") + b"\n"
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.rename(
            temporary_name,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        os.fsync(directory_fd)
    finally:
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def default_policy(args: argparse.Namespace) -> dict[str, Any]:
    target = safe_id(args.target_thread, label="target thread ID")
    created_at = utc_now()
    policy: dict[str, Any] = {
        "schema_version": 1,
        "policy_version": 1,
        "target_thread_id": target,
        "supervision_group_id": "supervision-group-"
        + digest(
            {
                "kind": "supervision-group",
                "target_thread_id": target,
                "created_at": created_at,
            }
        )[:24],
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
            "production_promotion": False,
            "release": False,
            "deployment": False,
            "destructive_action": False,
            "spend": False,
            "credential_access": False,
            "external_action": False,
        },
        "execution_economy": execution_economy_contract(),
        "outcome_completion": outcome_completion_contract(),
        "decision_resolution": decision_resolution_contract(),
        "cross_thread_routing": cross_thread_routing_contract(),
        "skill_maintenance": skill_maintenance_contract(),
        "adaptive_decision_control": adaptive_decision_control_contract(
            target_repository_root=getattr(
                args, "adaptive_target_repository_root", None
            )
        ),
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
        "created_at": created_at,
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
    owner_root_required = policy.get("owner_root_history_required")
    if owner_root_required is not None and owner_root_required is not True:
        raise SupervisionLogError("Canonical owner-root history posture is invalid")
    if (
        policy.get("implementation_range") is not None
        or policy.get("direct_authority_receipts")
    ) and owner_root_required is not True:
        raise SupervisionLogError(
            "Canonical range or authority state requires owner-root history"
        )
    group_id = policy.get("supervision_group_id")
    if group_id is not None:
        if not isinstance(group_id, str):
            raise SupervisionLogError("Supervision group ID is not a string")
        safe_id(group_id, label="supervision group ID")
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
    implementation_range = policy.get("implementation_range")
    if implementation_range is not None:
        if not isinstance(implementation_range, Mapping):
            raise SupervisionLogError("Implementation range binding is not an object")
        validate_implementation_range_contract(implementation_range)
    authority_receipts = policy.get("direct_authority_receipts", [])
    if not isinstance(authority_receipts, list):
        raise SupervisionLogError("Direct-authority receipts are malformed")
    seen_authority_receipts: set[tuple[str, str]] = set()
    for receipt in authority_receipts:
        if not isinstance(receipt, Mapping) or receipt.get("source_class") != "direct-user":
            raise SupervisionLogError("Direct-authority receipt provenance differs")
        source_record = safe_id(
            str(receipt.get("source_record", "")),
            label="direct-authority source record",
        )
        source_sha256 = exact_sha256(
            str(receipt.get("source_sha256", "")),
            label="direct-authority source SHA-256",
        )
        reviewer_id = safe_id(
            str(receipt.get("reviewer_id", "")),
            label="direct-authority receipt reviewer",
        )
        safe_id(
            str(receipt.get("source_event_record_id", "")),
            label="direct-authority canonical event record",
        )
        exact_sha256(
            str(receipt.get("source_event_sha256", "")),
            label="direct-authority canonical event SHA-256",
        )
        safe_id(
            str(receipt.get("source_task_id", "")),
            label="direct-authority source task",
        )
        safe_id(
            str(receipt.get("source_item_id", "")),
            label="direct-authority source item",
        )
        exact_sha256(
            str(receipt.get("source_policy_sha256", "")),
            label="direct-authority source policy SHA-256",
        )
        if receipt.get("accepted") is not True or not receipt.get("evidence"):
            raise SupervisionLogError("Direct-authority receipt is not accepted evidence")
        if not isinstance(receipt.get("accepted_policy_version"), int) or receipt[
            "accepted_policy_version"
        ] <= 0:
            raise SupervisionLogError("Direct-authority receipt version is invalid")
        if (source_record, source_sha256) in seen_authority_receipts:
            raise SupervisionLogError("Direct-authority receipt is duplicated")
        seen_authority_receipts.add((source_record, source_sha256))
        runtime = policy.get("runtime", {})
        if reviewer_id not in {
            runtime.get("base_reviewer_thread_id"),
            runtime.get("reviewer_thread_id"),
        }:
            raise SupervisionLogError("Direct-authority receipt reviewer is not bound")
    maintenance = policy.get("skill_maintenance")
    if maintenance is not None:
        if maintenance.get("mode") not in SKILL_MAINTENANCE_MODES:
            raise SupervisionLogError("Unsupported skill-maintenance mode")
        if maintenance.get("allowlist") != ALLOWLISTED_MAINTENANCE_SKILLS:
            raise SupervisionLogError("Skill-maintenance allowlist differs")
    adaptive = policy.get("adaptive_decision_control")
    if adaptive is not None:
        if not isinstance(adaptive, Mapping):
            raise SupervisionLogError("Adaptive-decision policy is malformed")
        validate_adaptive_decision_control(adaptive)
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


@contextmanager
def append_lock_at(directory_fd: int) -> Iterator[None]:
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(".append.lock", flags, 0o600, dir_fd=directory_fd)
    except OSError as exc:
        raise SupervisionLogError("Cannot open supervision append lock safely") from exc
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def owner_append_lock(
    root: Path,
    target_thread_id: str,
    expected_directory_snapshot: tuple[int, int, int, int],
) -> Iterator[int]:
    _directory, directory_fd, directory_snapshot = open_member_directory(
        root, target_thread_id
    )
    try:
        if directory_snapshot != expected_directory_snapshot:
            raise SupervisionLogError(
                "Completed lifecycle rejected by governing-outcome control: "
                "retry-control-currentness"
            )
        with append_lock_at(directory_fd):
            yield directory_fd
    finally:
        os.close(directory_fd)


def append_raw_locked(path: Path, value: dict[str, Any]) -> None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path.parent, flags)
    try:
        existing, snapshot = events_snapshot(
            Path(path.name), directory_fd=descriptor
        )
        previous = existing[-1].get("record_sha256") if existing else None
        append_raw_locked_at(
            descriptor,
            path.name,
            value,
            previous_record_sha256=(
                str(previous) if previous is not None else None
            ),
            expected_file_snapshot=snapshot,
        )
    finally:
        os.close(descriptor)


def append_raw_locked_at(
    directory_fd: int,
    name: str,
    value: dict[str, Any],
    *,
    previous_record_sha256: str | None,
    expected_file_snapshot: tuple[int, int, int, int] | None,
    require_event_anchor: bool = False,
) -> str:
    owner_policy_history: list[dict[str, Any]] = []
    owner_events: list[dict[str, Any]] = []
    owner_root_enabled = bool(
        name in {"events.jsonl", "policy-history.jsonl"}
        and owner_root_enabled_at(directory_fd)
    )
    if owner_root_enabled:
        owner_policy_history, _owner_policy_history_snapshot = events_snapshot(
            Path("policy-history.jsonl"), directory_fd=directory_fd
        )
        owner_events, _owner_events_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        validate_owner_root_history_at(
            directory_fd,
            owner_policy_history,
            owner_events,
            allow_missing=owner_root_bootstrap_allowed_at(
                directory_fd,
                owner_policy_history,
                owner_events,
            ),
        )
    if name == "events.jsonl":
        prior_events, _prior_snapshot = events_snapshot(
            Path(name), directory_fd=directory_fd
        )
        validate_event_ledger_anchor_at(
            directory_fd,
            prior_events,
            allow_missing=not require_event_anchor and not prior_events,
        )
        actual_prior = (
            str(prior_events[-1].get("record_sha256")) if prior_events else None
        )
        if actual_prior != previous_record_sha256:
            raise SupervisionLogError(
                "Supervision event ledger head changed before append"
            )
    material = dict(value)
    material["previous_record_sha256"] = previous_record_sha256
    record_sha256 = digest(material)
    material["record_sha256"] = record_sha256
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    flags |= os.O_EXCL | os.O_CREAT if expected_file_snapshot is None else 0
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    try:
        if (
            expected_file_snapshot is not None
            and file_snapshot(os.fstat(descriptor)) != expected_file_snapshot
        ):
            raise SupervisionLogError(
                "Supervision event ledger changed before append"
            )
        os.write(descriptor, canonical(material) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if name == "events.jsonl":
        current_events, _current_snapshot = events_snapshot(
            Path(name), directory_fd=directory_fd
        )
        atomic_json_at(
            directory_fd,
            EVENT_LEDGER_ANCHOR_NAME,
            event_ledger_anchor(current_events),
        )
    if (
        name in {"events.jsonl", "policy-history.jsonl"}
        and (owner_root_enabled or owner_root_enabled_at(directory_fd))
    ):
        current_policy_history, _current_policy_history_snapshot = events_snapshot(
            Path("policy-history.jsonl"), directory_fd=directory_fd
        )
        current_owner_events, _current_owner_event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        append_owner_root_history_at(
            directory_fd,
            current_policy_history,
            current_owner_events,
        )
    return record_sha256


def append_raw(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with append_lock(path.parent):
        append_raw_locked(path, value)


def append_event_locked(
    args: argparse.Namespace, directory: Path, record: dict[str, Any]
) -> None:
    """Append under the caller's owner lock against the current policy."""

    current_directory, current = load_policy(args)
    if current_directory.resolve() != directory.resolve():
        raise SupervisionLogError("Event append resolved a different supervision root")
    if record.get("policy_sha256") != current.get("policy_sha256"):
        raise SupervisionLogError(
            "Supervision policy changed concurrently; rebuild the event before appending"
        )
    append_raw_locked(directory / "events.jsonl", record)


def parse_events(text: str, *, ledger_name: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    previous: str | None = None
    record_ids: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SupervisionLogError(
                f"Ledger {ledger_name} has malformed JSON at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise SupervisionLogError("Event ledger contains a non-object")
        recorded_hash = value.get("record_sha256")
        material = {key: item for key, item in value.items() if key != "record_sha256"}
        if material.get("previous_record_sha256") != previous:
            raise SupervisionLogError(
                f"Ledger {ledger_name} has a broken hash chain at line {line_number}"
            )
        if not isinstance(recorded_hash, str) or digest(material) != recorded_hash:
            raise SupervisionLogError(
                f"Ledger {ledger_name} has a stale record hash at line {line_number}"
            )
        record_id = value.get("record_id")
        if isinstance(record_id, str):
            if record_id in record_ids:
                raise SupervisionLogError(
                    f"Ledger {ledger_name} repeats record ID {record_id}"
                )
            record_ids.add(record_id)
        previous = recorded_hash
        result.append(value)
    return result


def events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return parse_events(path.read_text(encoding="utf-8"), ledger_name=path.name)


def event_ledger_anchor(all_events: list[dict[str, Any]]) -> dict[str, Any]:
    material: dict[str, Any] = {
        "schema_version": 1,
        "kind": "supervision-event-ledger-head",
        "event_count": len(all_events),
        "genesis_record_sha256": (
            all_events[0].get("record_sha256") if all_events else None
        ),
        "event_head_sha256": (
            all_events[-1].get("record_sha256") if all_events else None
        ),
    }
    material["anchor_sha256"] = digest(material)
    return material


def validate_event_ledger_anchor_value(
    value: Mapping[str, Any], all_events: list[dict[str, Any]]
) -> None:
    expected = event_ledger_anchor(all_events)
    if dict(value) != expected:
        raise SupervisionLogError(
            "Canonical supervision event-ledger head is stale or replaced"
        )


def validate_event_ledger_anchor(
    directory: Path,
    all_events: list[dict[str, Any]],
    *,
    allow_missing: bool,
) -> None:
    path = directory / EVENT_LEDGER_ANCHOR_NAME
    if not path.exists():
        if allow_missing:
            return
        raise SupervisionLogError(
            "Canonical supervision event-ledger head is missing"
        )
    validate_event_ledger_anchor_value(read_json(path), all_events)


def validate_event_ledger_anchor_at(
    directory_fd: int,
    all_events: list[dict[str, Any]],
    *,
    allow_missing: bool,
) -> None:
    if path_snapshot_at(directory_fd, EVENT_LEDGER_ANCHOR_NAME) is None:
        if allow_missing:
            return
        raise SupervisionLogError(
            "Canonical supervision event-ledger head is missing"
        )
    value, _snapshot = read_json_snapshot(
        Path(EVENT_LEDGER_ANCHOR_NAME), directory_fd=directory_fd
    )
    validate_event_ledger_anchor_value(value, all_events)


def ensure_event_ledger_anchor_at(directory_fd: int) -> None:
    all_events, _snapshot = events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    if path_snapshot_at(directory_fd, EVENT_LEDGER_ANCHOR_NAME) is None:
        atomic_json_at(
            directory_fd,
            EVENT_LEDGER_ANCHOR_NAME,
            event_ledger_anchor(all_events),
        )
        return
    validate_event_ledger_anchor_at(
        directory_fd,
        all_events,
        allow_missing=False,
    )


def owner_root_material(
    policy_history: list[dict[str, Any]], all_events: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "policy_history_count": len(policy_history),
        "policy_history_genesis_sha256": (
            policy_history[0].get("record_sha256") if policy_history else None
        ),
        "policy_history_head_sha256": (
            policy_history[-1].get("record_sha256") if policy_history else None
        ),
        "event_count": len(all_events),
        "event_genesis_sha256": (
            all_events[0].get("record_sha256") if all_events else None
        ),
        "event_head_sha256": (
            all_events[-1].get("record_sha256") if all_events else None
        ),
    }


def directory_path_from_fd(directory_fd: int) -> Path:
    if sys.platform != "darwin":
        proc_path = Path(f"/proc/self/fd/{directory_fd}")
        try:
            return proc_path.resolve(strict=True)
        except OSError as exc:
            raise SupervisionLogError(
                "Cannot resolve canonical owner directory for root authority"
            ) from exc
    try:
        raw = fcntl.fcntl(directory_fd, 50, b"\0" * 1024)
    except OSError as exc:
        raise SupervisionLogError(
            "Cannot resolve canonical owner directory for root authority"
        ) from exc
    value = raw.split(b"\0", 1)[0].decode("utf-8")
    return Path(value).resolve(strict=True)


def owner_root_key_path_at(directory_fd: int) -> Path:
    directory = directory_path_from_fd(directory_fd)
    key_directory = directory.parent / OWNER_ROOT_KEY_DIRECTORY
    key_name = hashlib.sha256(directory.name.encode("utf-8")).hexdigest() + ".key"
    return key_directory / key_name


def owner_root_state_path_at(directory_fd: int) -> Path:
    key_path = owner_root_key_path_at(directory_fd)
    return key_path.with_suffix(".state.json")


def owner_root_external_state(
    key: bytes, roots: list[dict[str, Any]]
) -> dict[str, Any]:
    material: dict[str, Any] = {
        "schema_version": 1,
        "kind": "supervision-owner-root-external-head",
        "sequence": len(roots),
        "owner_root_head_sha256": (
            roots[-1].get("record_sha256") if roots else None
        ),
    }
    material["state_hmac_sha256"] = hmac.new(
        key,
        canonical(material),
        hashlib.sha256,
    ).hexdigest()
    return material


def validate_owner_root_external_state_at(
    directory_fd: int,
    key: bytes,
    roots: list[dict[str, Any]],
) -> None:
    path = owner_root_state_path_at(directory_fd)
    if not path.exists() or path.is_symlink():
        raise SupervisionLogError(
            "Canonical external owner-root head is missing or symlinked"
        )
    value = read_json(path)
    expected = owner_root_external_state(key, roots)
    if value != expected:
        raise SupervisionLogError(
            "Canonical external owner-root head rejects rollback or replacement"
        )


def owner_root_key_exists_at(directory_fd: int) -> bool:
    path = owner_root_key_path_at(directory_fd)
    return path.exists() and not path.is_symlink()


def owner_root_external_state_exists_at(directory_fd: int) -> bool:
    path = owner_root_state_path_at(directory_fd)
    return path.exists() or path.is_symlink()


def owner_root_key_at(directory_fd: int, *, allow_create: bool) -> bytes:
    path = owner_root_key_path_at(directory_fd)
    if not path.exists():
        if owner_root_external_state_exists_at(directory_fd):
            raise SupervisionLogError(
                "Canonical external owner-root head survives without its key"
            )
        if not allow_create:
            raise SupervisionLogError("Canonical external owner-root key is missing")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise SupervisionLogError("Canonical owner-root key directory is symlinked")
        os.chmod(path.parent, 0o700)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o400)
        try:
            os.write(descriptor, secrets.token_bytes(32))
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o400)
        finally:
            os.close(descriptor)
    if path.is_symlink():
        raise SupervisionLogError("Canonical external owner-root key is symlinked")
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
        raise SupervisionLogError("Canonical external owner-root key is invalid")
    return key


def owner_root_enabled_at(directory_fd: int) -> bool:
    if path_snapshot_at(directory_fd, OWNER_ROOT_HISTORY_NAME) is not None:
        return True
    if (
        owner_root_key_exists_at(directory_fd)
        or owner_root_external_state_exists_at(directory_fd)
    ):
        return True
    try:
        policy, _snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(policy)
    except (OSError, SupervisionLogError):
        return False
    return policy.get("owner_root_history_required") is True


def owner_root_bootstrap_allowed_at(
    directory_fd: int,
    policy_history: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
) -> bool:
    if path_snapshot_at(directory_fd, OWNER_ROOT_HISTORY_NAME) is not None:
        return False
    if (
        owner_root_key_exists_at(directory_fd)
        or owner_root_external_state_exists_at(directory_fd)
    ):
        return False
    try:
        policy, _snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(policy)
    except (OSError, SupervisionLogError):
        return not policy_history and not all_events
    return (
        policy.get("owner_root_history_required") is not True
        or (not policy_history and not all_events)
    )


def validate_owner_root_history_at(
    directory_fd: int,
    policy_history: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
    *,
    allow_missing: bool,
) -> None:
    if path_snapshot_at(directory_fd, OWNER_ROOT_HISTORY_NAME) is None:
        if allow_missing:
            return
        raise SupervisionLogError("Canonical owner-root history is missing")
    roots, _snapshot = events_snapshot(
        Path(OWNER_ROOT_HISTORY_NAME), directory_fd=directory_fd
    )
    if not roots:
        raise SupervisionLogError("Canonical owner-root history is empty")
    key = owner_root_key_at(directory_fd, allow_create=False)
    for index, record in enumerate(roots, start=1):
        expected_fields = {
            "schema_version",
            "record_id",
            "timestamp",
            "kind",
            "sequence",
            *owner_root_material([], []).keys(),
            "owner_hmac_sha256",
            "previous_record_sha256",
            "record_sha256",
        }
        if (
            set(record) != expected_fields
            or record.get("schema_version") != 1
            or record.get("kind") != "supervision-owner-root"
            or record.get("sequence") != index
            or record.get("record_id") != f"OWNER-ROOT-{index:06d}"
        ):
            raise SupervisionLogError("Canonical owner-root history shape differs")
        signed = {
            field: value
            for field, value in record.items()
            if field not in {"owner_hmac_sha256", "record_sha256"}
        }
        expected_hmac = hmac.new(
            key,
            canonical(signed),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            str(record.get("owner_hmac_sha256", "")), expected_hmac
        ):
            raise SupervisionLogError(
                "Canonical owner-root history lacks external authority"
            )
    validate_owner_root_external_state_at(directory_fd, key, roots)
    expected = owner_root_material(policy_history, all_events)
    if any(roots[-1].get(field) != value for field, value in expected.items()):
        raise SupervisionLogError(
            "Canonical owner-root history differs from policy or event state"
        )


def append_owner_root_history_at(
    directory_fd: int,
    policy_history: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
) -> None:
    roots, snapshot = events_snapshot(
        Path(OWNER_ROOT_HISTORY_NAME), directory_fd=directory_fd
    )
    key = owner_root_key_at(directory_fd, allow_create=True)
    material: dict[str, Any] = {
        "schema_version": 1,
        "record_id": f"OWNER-ROOT-{len(roots) + 1:06d}",
        "timestamp": utc_now(),
        "kind": "supervision-owner-root",
        "sequence": len(roots) + 1,
        **owner_root_material(policy_history, all_events),
        "previous_record_sha256": (
            roots[-1].get("record_sha256") if roots else None
        ),
    }
    material["owner_hmac_sha256"] = hmac.new(
        key,
        canonical(material),
        hashlib.sha256,
    ).hexdigest()
    material["record_sha256"] = digest(material)
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    flags |= os.O_EXCL | os.O_CREAT if snapshot is None else 0
    descriptor = os.open(
        OWNER_ROOT_HISTORY_NAME,
        flags,
        0o600,
        dir_fd=directory_fd,
    )
    try:
        if snapshot is not None and file_snapshot(os.fstat(descriptor)) != snapshot:
            raise SupervisionLogError(
                "Canonical owner-root history changed before append"
            )
        os.write(descriptor, canonical(material) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    atomic_json(
        owner_root_state_path_at(directory_fd),
        owner_root_external_state(key, [*roots, material]),
    )


def ensure_owner_root_history_at(directory_fd: int) -> None:
    policy_history, _history_snapshot = events_snapshot(
        Path("policy-history.jsonl"), directory_fd=directory_fd
    )
    all_events, _event_snapshot = events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    if path_snapshot_at(directory_fd, OWNER_ROOT_HISTORY_NAME) is None:
        append_owner_root_history_at(directory_fd, policy_history, all_events)
        return
    validate_owner_root_history_at(
        directory_fd,
        policy_history,
        all_events,
        allow_missing=False,
    )


def canonical_direct_authority_event(
    all_events: list[dict[str, Any]],
    *,
    event_record_id: str,
    policy: Mapping[str, Any],
    policy_history: list[dict[str, Any]],
) -> dict[str, Any]:
    event = next(
        (item for item in all_events if item.get("record_id") == event_record_id),
        None,
    )
    if event is None:
        raise SupervisionLogError(
            "Direct-authority source is not in the canonical owner event ledger"
        )
    required = {
        "schema_version",
        "record_id",
        "timestamp",
        "target_thread_id",
        "kind",
        "source_class",
        "source_record",
        "source_sha256",
        "source_task_id",
        "source_item_id",
        "verifier_id",
        "provenance_status",
        "policy_sha256",
        "evidence",
        "previous_record_sha256",
        "record_sha256",
    }
    if set(event) != required:
        raise SupervisionLogError(
            "Canonical direct-authority source event shape differs"
        )
    if (
        event.get("schema_version") != 1
        or event.get("kind") != DIRECT_AUTHORITY_EVENT_KIND
        or event.get("source_class") != "direct-user"
        or event.get("provenance_status") != "verified-before-entry"
        or event.get("target_thread_id") != policy.get("target_thread_id")
    ):
        raise SupervisionLogError(
            "Canonical direct-authority source provenance differs"
        )
    safe_id(str(event["record_id"]), label="direct-authority event record")
    source_record = safe_id(
        str(event["source_record"]), label="direct-authority source record"
    )
    source_item_id = safe_id(
        str(event["source_item_id"]), label="direct-authority source item"
    )
    if source_record != source_item_id:
        raise SupervisionLogError(
            "Canonical direct-authority source record and item differ"
        )
    safe_id(str(event["source_task_id"]), label="direct-authority source task")
    exact_sha256(str(event["source_sha256"]), label="direct-authority source SHA-256")
    exact_sha256(str(event["record_sha256"]), label="direct-authority event SHA-256")
    source_policy_sha256 = exact_sha256(
        str(event["policy_sha256"]), label="direct-authority source policy SHA-256"
    )
    if not any(
        isinstance(item.get("policy"), Mapping)
        and item["policy"].get("policy_sha256") == source_policy_sha256
        for item in policy_history
    ):
        raise SupervisionLogError(
            "Canonical direct-authority event is not anchored to owner policy history"
        )
    verifier_id = safe_id(
        str(event["verifier_id"]), label="direct-authority provenance verifier"
    )
    runtime = policy.get("runtime", {})
    eligible = {
        runtime.get("base_reviewer_thread_id"),
        runtime.get("reviewer_thread_id"),
    }
    disallowed = {
        policy.get("target_thread_id"),
        runtime.get("watcher_thread_id"),
        runtime.get("fix_executor_thread_id"),
    }
    evidence = event.get("evidence")
    if (
        verifier_id not in eligible
        or verifier_id in disallowed
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or not all(isinstance(item, str) and item for item in evidence)
    ):
        raise SupervisionLogError(
            "Canonical direct-authority event lacks independent provenance evidence"
        )
    return event


def validate_direct_authority_receipts(
    policy: Mapping[str, Any],
    *,
    all_events: list[dict[str, Any]],
    policy_history: list[dict[str, Any]],
) -> None:
    for receipt in policy.get("direct_authority_receipts", []):
        event = canonical_direct_authority_event(
            all_events,
            event_record_id=str(receipt["source_event_record_id"]),
            policy=policy,
            policy_history=policy_history,
        )
        comparisons = {
            "source_record": "source_record",
            "source_sha256": "source_sha256",
            "reviewer_id": "verifier_id",
            "source_event_sha256": "record_sha256",
            "source_task_id": "source_task_id",
            "source_item_id": "source_item_id",
            "source_policy_sha256": "policy_sha256",
            "evidence": "evidence",
        }
        if any(
            receipt.get(receipt_field) != event.get(event_field)
            for receipt_field, event_field in comparisons.items()
        ):
            raise SupervisionLogError(
                "Direct-authority receipt differs from its canonical owner event"
            )


def canonical_tracker_amendment_event(
    all_events: list[dict[str, Any]],
    *,
    event_record_id: str,
    policy: Mapping[str, Any],
    policy_history: list[dict[str, Any]],
) -> dict[str, Any]:
    event = next(
        (item for item in all_events if item.get("record_id") == event_record_id),
        None,
    )
    if event is None:
        raise SupervisionLogError(
            "Tracker amendment is not in the canonical owner event ledger"
        )
    required = {
        "schema_version",
        "record_id",
        "timestamp",
        "target_thread_id",
        "kind",
        "old_tracker_path",
        "old_tracker_sha256",
        "old_tracker_structure_sha256",
        "old_blocks",
        "new_tracker_path",
        "new_tracker_sha256",
        "new_tracker_structure_sha256",
        "new_blocks",
        "block_number_map",
        "verifier_id",
        "provenance_status",
        "policy_sha256",
        "evidence",
        "previous_record_sha256",
        "record_sha256",
    }
    if set(event) != required:
        raise SupervisionLogError("Canonical tracker-amendment event shape differs")
    if (
        event.get("schema_version") != 1
        or event.get("kind") != TRACKER_AMENDMENT_EVENT_KIND
        or event.get("provenance_status") != "accepted-before-entry"
        or event.get("target_thread_id") != policy.get("target_thread_id")
    ):
        raise SupervisionLogError("Canonical tracker-amendment provenance differs")
    for field in ("old_tracker_path", "new_tracker_path"):
        value = event.get(field)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise SupervisionLogError("Canonical tracker-amendment path is not exact")
    for field in (
        "old_tracker_sha256",
        "old_tracker_structure_sha256",
        "new_tracker_sha256",
        "new_tracker_structure_sha256",
        "record_sha256",
    ):
        exact_sha256(str(event.get(field, "")), label=field.replace("_", " "))
    old_blocks = event.get("old_blocks")
    new_blocks = event.get("new_blocks")
    if (
        not isinstance(old_blocks, list)
        or not isinstance(new_blocks, list)
        or not old_blocks
        or not new_blocks
        or not all(isinstance(item, int) for item in [*old_blocks, *new_blocks])
        or old_blocks != sorted(set(old_blocks))
        or new_blocks != sorted(set(new_blocks))
    ):
        raise SupervisionLogError("Canonical tracker-amendment Block sets differ")
    block_map = event.get("block_number_map")
    if (
        not isinstance(block_map, Mapping)
        or set(block_map) != {str(item) for item in old_blocks}
        or not all(isinstance(item, int) for item in block_map.values())
        or len(set(block_map.values())) != len(block_map)
        or not set(block_map.values()).issubset(set(new_blocks))
    ):
        raise SupervisionLogError(
            "Canonical tracker-amendment renumbering map is incomplete"
        )
    source_policy_sha256 = exact_sha256(
        str(event.get("policy_sha256", "")),
        label="tracker-amendment source policy SHA-256",
    )
    if not any(
        isinstance(item.get("policy"), Mapping)
        and item["policy"].get("policy_sha256") == source_policy_sha256
        for item in policy_history
    ):
        raise SupervisionLogError(
            "Canonical tracker amendment is not anchored to owner policy history"
        )
    verifier_id = safe_id(
        str(event.get("verifier_id", "")),
        label="tracker-amendment verifier",
    )
    runtime = policy.get("runtime", {})
    eligible = {
        runtime.get("base_reviewer_thread_id"),
        runtime.get("reviewer_thread_id"),
    }
    disallowed = {
        policy.get("target_thread_id"),
        runtime.get("watcher_thread_id"),
        runtime.get("fix_executor_thread_id"),
    }
    evidence = event.get("evidence")
    if (
        verifier_id not in eligible
        or verifier_id in disallowed
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or not all(isinstance(item, str) and item for item in evidence)
    ):
        raise SupervisionLogError(
            "Canonical tracker amendment lacks independent acceptance evidence"
        )
    return event


def validate_tracker_amendment_events(
    policy: Mapping[str, Any],
    *,
    all_events: list[dict[str, Any]],
    policy_history: list[dict[str, Any]],
) -> None:
    contract = implementation_range_contract(policy)
    if contract is None:
        return
    for entry in contract.get("history", []):
        event_record_id = entry.get("amendment_event_record_id", "")
        if not event_record_id:
            if entry.get("amendment_event_sha256", ""):
                raise SupervisionLogError(
                    "Range history has an unbound tracker-amendment event hash"
                )
            continue
        event = canonical_tracker_amendment_event(
            all_events,
            event_record_id=str(event_record_id),
            policy=policy,
            policy_history=policy_history,
        )
        if (
            entry.get("amendment_event_sha256") != event.get("record_sha256")
            or entry.get("amendment_map_sha256")
            != digest(event.get("block_number_map"))
            or entry.get("tracker_path") != event.get("new_tracker_path")
            or entry.get("tracker_sha256") != event.get("new_tracker_sha256")
            or entry.get("tracker_blocks") != event.get("new_blocks")
        ):
            raise SupervisionLogError(
                "Range history differs from its canonical tracker-amendment event"
            )


def canonical_successor_topology_event(
    all_events: list[dict[str, Any]],
    *,
    event_record_id: str,
    policy: Mapping[str, Any],
    policy_history: list[dict[str, Any]],
) -> dict[str, Any]:
    event = next(
        (item for item in all_events if item.get("record_id") == event_record_id),
        None,
    )
    if event is None:
        raise SupervisionLogError(
            "Technical-isolation decision is not in the canonical owner event ledger"
        )
    required = {
        "schema_version",
        "record_id",
        "timestamp",
        "target_thread_id",
        "kind",
        "transition_id",
        "topology_posture",
        "topology_basis",
        "topology_rationale",
        "governing_authority_source_class",
        "governing_authority_source_record",
        "governing_authority_source_sha256",
        "verifier_id",
        "provenance_status",
        "policy_sha256",
        "evidence",
        "previous_record_sha256",
        "record_sha256",
    }
    if set(event) != required:
        raise SupervisionLogError("Canonical topology-decision event shape differs")
    if (
        event.get("schema_version") != 1
        or event.get("kind") != SUCCESSOR_TOPOLOGY_EVENT_KIND
        or event.get("target_thread_id") != policy.get("target_thread_id")
        or event.get("topology_posture") != "distinct-task"
        or event.get("topology_basis") != "technical-isolation"
        or event.get("provenance_status") != "accepted-before-entry"
    ):
        raise SupervisionLogError("Canonical topology-decision provenance differs")
    for field in ("record_id", "transition_id", "governing_authority_source_record"):
        safe_id(str(event.get(field, "")), label=field.replace("_", " "))
    for field in ("record_sha256", "governing_authority_source_sha256", "policy_sha256"):
        exact_sha256(str(event.get(field, "")), label=field.replace("_", " "))
    rationale = event.get("topology_rationale")
    if not isinstance(rationale, str) or not rationale or len(rationale) > 300:
        raise SupervisionLogError("Canonical topology rationale is not exact")
    if not canonical_authority_source(
        policy,
        source_class=str(event.get("governing_authority_source_class", "")),
        source_record=str(event.get("governing_authority_source_record", "")),
        source_sha256=str(event.get("governing_authority_source_sha256", "")),
    ):
        raise SupervisionLogError(
            "Canonical topology decision lacks governing authority"
        )
    if not any(
        isinstance(item.get("policy"), Mapping)
        and item["policy"].get("policy_sha256") == event.get("policy_sha256")
        for item in policy_history
    ):
        raise SupervisionLogError(
            "Canonical topology decision is not anchored to policy history"
        )
    verifier_id = safe_id(
        str(event.get("verifier_id", "")), label="topology-decision verifier"
    )
    runtime = policy.get("runtime", {})
    evidence = event.get("evidence")
    if (
        verifier_id
        not in {
            runtime.get("base_reviewer_thread_id"),
            runtime.get("reviewer_thread_id"),
        }
        or verifier_id
        in {
            policy.get("target_thread_id"),
            runtime.get("watcher_thread_id"),
            runtime.get("fix_executor_thread_id"),
        }
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or not all(isinstance(item, str) and item for item in evidence)
    ):
        raise SupervisionLogError(
            "Canonical topology decision lacks independent evidence"
        )
    return event


def events_snapshot(
    path: Path, *, directory_fd: int | None = None
) -> tuple[list[dict[str, Any]], tuple[int, int, int, int] | None]:
    try:
        text, snapshot = read_text_snapshot(
            path, missing_ok=True, directory_fd=directory_fd
        )
    except OSError as exc:
        raise SupervisionLogError(f"Cannot read supervision state: {path.name}") from exc
    return parse_events(text, ledger_name=path.name), snapshot


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
    validate_adaptive_decision_control(policy["adaptive_decision_control"])
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
    atomic_json(
        directory / EVENT_LEDGER_ANCHOR_NAME,
        event_ledger_anchor([]),
    )
    print(json.dumps({"created": True, "policy": policy}, sort_keys=True))


def range_policy_requires_history(policy: Mapping[str, Any]) -> bool:
    return bool(
        policy.get("implementation_range") is not None
        or policy.get("direct_authority_receipts")
    )


def validate_policy_history_sequence(
    history: list[dict[str, Any]], policy: Mapping[str, Any]
) -> None:
    policy_version = policy.get("policy_version")
    if not isinstance(policy_version, int) or policy_version < 1:
        raise SupervisionLogError("Canonical policy version is invalid")
    if len(history) != policy_version:
        raise SupervisionLogError(
            "Canonical policy history was truncated or re-rooted"
        )
    for index, record in enumerate(history, start=1):
        embedded = record.get("policy")
        if (
            record.get("record_id") != f"POLICY-{index}"
            or not isinstance(embedded, Mapping)
            or embedded.get("policy_version") != index
            or embedded.get("target_thread_id") != policy.get("target_thread_id")
        ):
            raise SupervisionLogError(
                "Canonical policy history sequence or owner differs"
            )
        try:
            validate_policy(dict(embedded))
        except SupervisionLogError as exc:
            raise SupervisionLogError(
                "Canonical policy history contains an invalid embedded policy"
            ) from exc
        if (
            embedded.get("created_at") != policy.get("created_at")
            or embedded.get("target_label") != policy.get("target_label")
        ):
            raise SupervisionLogError(
                "Canonical policy history immutable owner identity differs"
            )


def validate_range_policy_history_at(
    directory_fd: int, policy: Mapping[str, Any]
) -> None:
    external_owner_root = (
        owner_root_key_exists_at(directory_fd)
        or owner_root_external_state_exists_at(directory_fd)
    )
    owner_root_required = (
        policy.get("owner_root_history_required") is True
        or external_owner_root
    )
    if (
        external_owner_root
        or range_policy_requires_history(policy)
    ) and policy.get("owner_root_history_required") is not True:
        raise SupervisionLogError(
            "Canonical owner-root history enforcement cannot be downgraded"
        )
    if not range_policy_requires_history(policy) and not owner_root_required:
        return
    history, _snapshot = events_snapshot(
        Path("policy-history.jsonl"), directory_fd=directory_fd
    )
    validate_policy_history_sequence(history, policy)
    if not history or history[-1].get("policy") != policy:
        raise SupervisionLogError(
            "Canonical implementation-range policy history is stale or replaced"
        )
    all_events, _event_snapshot = events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    if owner_root_required:
        validate_owner_root_history_at(
            directory_fd,
            history,
            all_events,
            allow_missing=False,
        )
    if policy.get("direct_authority_receipts") or policy.get("implementation_range"):
        validate_event_ledger_anchor_at(
            directory_fd,
            all_events,
            allow_missing=not all_events,
        )
        if policy.get("direct_authority_receipts"):
            validate_direct_authority_receipts(
                policy,
                all_events=all_events,
                policy_history=history,
            )
        validate_tracker_amendment_events(
            policy,
            all_events=all_events,
            policy_history=history,
        )


def validate_range_policy_history(directory: Path, policy: Mapping[str, Any]) -> None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(directory, flags)
    try:
        validate_range_policy_history_at(descriptor, policy)
    finally:
        os.close(descriptor)


def load_policy(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    directory, policy, _policy_snapshot, _directory_snapshot = (
        load_policy_directory_snapshot(args)
    )
    return directory, policy


def load_policy_snapshot(
    args: argparse.Namespace,
) -> tuple[Path, dict[str, Any], tuple[int, int, int, int]]:
    directory, policy, snapshot, _directory_snapshot = (
        load_policy_directory_snapshot(args)
    )
    return directory, policy, snapshot


def load_policy_directory_snapshot(
    args: argparse.Namespace,
) -> tuple[
    Path,
    dict[str, Any],
    tuple[int, int, int, int],
    tuple[int, int, int, int],
]:
    root = root_from(args)
    directory, directory_fd, directory_snapshot = open_member_directory(
        root, args.target_thread
    )
    try:
        policy, snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(policy)
        validate_range_policy_history_at(directory_fd, policy)
    finally:
        os.close(directory_fd)
    if policy.get("target_thread_id") != args.target_thread:
        raise SupervisionLogError("Policy belongs to a different target")
    return directory, policy, snapshot, directory_snapshot


def load_control_snapshot(
    args: argparse.Namespace,
) -> tuple[
    Path,
    dict[str, Any],
    tuple[int, int, int, int],
    list[dict[str, Any]],
    tuple[int, int, int, int] | None,
    tuple[int, int, int, int],
]:
    root = root_from(args)
    directory, directory_fd, directory_snapshot = open_member_directory(
        root, args.target_thread
    )
    try:
        policy, policy_snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(policy)
        validate_range_policy_history_at(directory_fd, policy)
        all_events, event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
    finally:
        os.close(directory_fd)
    if policy.get("target_thread_id") != args.target_thread:
        raise SupervisionLogError("Policy belongs to a different target")
    return (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    )


def require_bound_policy_at(
    directory_fd: int,
    *,
    expected_policy: dict[str, Any],
    expected_snapshot: tuple[int, int, int, int],
) -> dict[str, Any]:
    try:
        current_policy, current_snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(current_policy)
        validate_range_policy_history_at(directory_fd, current_policy)
    except (OSError, SupervisionLogError) as exc:
        raise SupervisionLogError(
            "Completed lifecycle rejected by governing-outcome control: "
            "retry-control-currentness"
        ) from exc
    if (
        current_snapshot != expected_snapshot
        or current_policy.get("policy_sha256")
        != expected_policy.get("policy_sha256")
        or current_policy.get("target_thread_id")
        != expected_policy.get("target_thread_id")
    ):
        raise SupervisionLogError(
            "Completed lifecycle rejected by governing-outcome control: "
            "retry-control-currentness"
        )
    return current_policy


@contextmanager
def policy_owner_lock(
    directory: Path,
) -> Iterator[tuple[int, tuple[int, int, int, int]]]:
    """Lock the exact opened owner directory against path substitution."""

    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        directory_fd = os.open(directory, flags)
        directory_snapshot = file_snapshot(os.fstat(directory_fd))
    except OSError as exc:
        raise SupervisionLogError(
            "Cannot open policy owner directory safely"
        ) from exc
    try:
        if path_snapshot(directory) != directory_snapshot:
            raise SupervisionLogError(
                "Policy owner directory changed before mutation"
            )
        with append_lock_at(directory_fd):
            yield directory_fd, directory_snapshot
    finally:
        os.close(directory_fd)


def write_policy_version_locked_at(
    directory: Path,
    directory_fd: int,
    directory_snapshot: tuple[int, int, int, int],
    policy: dict[str, Any],
    *,
    kind: str,
    reason: str,
    evidence_values: list[str],
    pre_mutation_validator: Any = None,
) -> None:
    expected_policy_sha256 = str(policy.get("policy_sha256", ""))
    expected_policy_version = int(policy["policy_version"])
    current_policy, _current_snapshot = read_json_snapshot(
        Path("policy.json"), directory_fd=directory_fd
    )
    validate_policy(current_policy)
    validate_range_policy_history_at(directory_fd, current_policy)
    legacy_history, legacy_history_snapshot = events_snapshot(
        Path("policy-history.jsonl"), directory_fd=directory_fd
    )
    if (
        current_policy.get("policy_sha256") != expected_policy_sha256
        or int(current_policy.get("policy_version", -1))
        != expected_policy_version
        or current_policy.get("target_thread_id")
        != policy.get("target_thread_id")
    ):
        raise SupervisionLogError(
            "Policy changed concurrently after it was loaded; reload before mutation"
        )
    if pre_mutation_validator is not None:
        pre_mutation_validator(directory_fd, current_policy)
    ensure_event_ledger_anchor_at(directory_fd)
    if (
        kind == "owner-root-history-migration"
        and not legacy_history
        and current_policy.get("policy_version") == 1
    ):
        append_raw_locked_at(
            directory_fd,
            "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-1",
                "timestamp": utc_now(),
                "kind": "legacy-policy-genesis-migration",
                "policy": current_policy,
            },
            previous_record_sha256=None,
            expected_file_snapshot=legacy_history_snapshot,
        )
    if (
        policy.get("owner_root_history_required") is True
        or policy.get("implementation_range") is not None
        or policy.get("direct_authority_receipts")
        or kind == "owner-root-history-migration"
    ):
        ensure_owner_root_history_at(directory_fd)
        policy["owner_root_history_required"] = True
    policy["policy_version"] = expected_policy_version + 1
    policy["updated_at"] = utc_now()
    policy["policy_sha256"] = digest(policy_material(policy))
    validate_policy(policy)
    policy_history, history_snapshot = events_snapshot(
        Path("policy-history.jsonl"), directory_fd=directory_fd
    )
    history_record = {
        "schema_version": 1,
        "record_id": f"POLICY-{policy['policy_version']}",
        "timestamp": utc_now(),
        "kind": kind,
        "reason": reason,
        "evidence": evidence_values,
        "policy": policy,
    }
    atomic_json_at(directory_fd, "policy.json", policy)
    prior_hash = (
        policy_history[-1].get("record_sha256")
        if policy_history
        else None
    )
    history_head = append_raw_locked_at(
        directory_fd,
        "policy-history.jsonl",
        history_record,
        previous_record_sha256=(
            str(prior_hash) if prior_hash is not None else None
        ),
        expected_file_snapshot=history_snapshot,
    )
    installed_policy, _installed_snapshot = read_json_snapshot(
        Path("policy.json"), directory_fd=directory_fd
    )
    validate_policy(installed_policy)
    validate_range_policy_history_at(directory_fd, installed_policy)
    current_directory_snapshot = path_snapshot(directory)
    if (
        installed_policy.get("policy_sha256")
        != policy.get("policy_sha256")
        or current_directory_snapshot is None
        or current_directory_snapshot[:2] != directory_snapshot[:2]
        or event_head_hash(
            Path("policy-history.jsonl"), directory_fd=directory_fd
        )
        != history_head
    ):
        raise SupervisionLogError(
            "Policy mutation lost canonical currentness"
        )


def write_policy_version(
    directory: Path,
    policy: dict[str, Any],
    *,
    kind: str,
    reason: str,
    evidence_values: list[str],
    pre_mutation_validator: Any = None,
) -> None:
    with policy_owner_lock(directory) as (directory_fd, directory_snapshot):
        write_policy_version_locked_at(
            directory,
            directory_fd,
            directory_snapshot,
            policy,
            kind=kind,
            reason=reason,
            evidence_values=evidence_values,
            pre_mutation_validator=pre_mutation_validator,
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
    if ensure_adaptive_decision_policy(policy):
        changed = True
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

    with policy_owner_lock(directory) as (directory_fd, directory_snapshot):
        policy, _policy_snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(policy)
        validate_range_policy_history_at(directory_fd, policy)
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

        all_events, event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        validate_event_ledger_anchor_at(
            directory_fd,
            all_events,
            allow_missing=not all_events,
        )
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
            if decision_head_is_open(item, all_events, policy)
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
        write_policy_version_locked_at(
            directory,
            directory_fd,
            directory_snapshot,
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
        prior_hash = (
            str(all_events[-1].get("record_sha256")) if all_events else None
        )
        activation_head = append_raw_locked_at(
            directory_fd,
            "events.jsonl",
            activation,
            previous_record_sha256=prior_hash,
            expected_file_snapshot=event_snapshot,
            require_event_anchor=True,
        )
        current_directory_snapshot = path_snapshot(directory)
        if (
            current_directory_snapshot is None
            or current_directory_snapshot[:2] != directory_snapshot[:2]
            or event_head_hash(
                Path("events.jsonl"), directory_fd=directory_fd
            )
            != activation_head
        ):
            raise SupervisionLogError(
                "Mission activation append lost canonical owner currentness"
            )
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


def canonical_record_first_incident(
    *,
    directory: Path,
    policy: dict[str, Any],
    source_record: str,
    incident_id_value: str,
    failure_mode_id: str,
) -> dict[str, str]:
    """Resolve one exact open incident head before a critical route."""

    current_incident_id = safe_id(
        incident_id_value, label="critical-route incident ID"
    )
    expected_failure_mode_id = safe_id(
        failure_mode_id, label="critical-route failure mode ID"
    )
    all_events = events(directory / "events.jsonl")
    validate_event_ledger_anchor(
        directory,
        all_events,
        allow_missing=not all_events,
    )
    incident_records = [
        item
        for item in all_events
        if is_substantive_incident_record(item, current_incident_id)
    ]
    if not incident_records:
        raise SupervisionLogError(
            "Critical route requires a pre-existing canonical incident head"
        )
    head = incident_records[-1]
    if head.get("record_id") != source_record:
        raise SupervisionLogError(
            "Critical route source is not the current canonical incident head"
        )
    if is_terminal_incident_record(head, current_incident_id):
        raise SupervisionLogError(
            "Critical route incident head is terminal or closed"
        )
    if head.get("severity") != "critical":
        raise SupervisionLogError(
            "Critical route incident head is not critical"
        )
    failure_mode = head.get("failure_mode")
    required_failure_fields = {
        "failure_mode_id",
        "layer",
        "mechanism",
        "trigger",
        "effect",
        "detection",
        "correction",
        "recurrence_invariant",
        "human_scheduling_leak",
    }
    if not isinstance(failure_mode, Mapping) or any(
        field not in failure_mode for field in required_failure_fields
    ):
        raise SupervisionLogError(
            "Critical route incident head lacks its complete failure-mode envelope"
        )
    if failure_mode.get("failure_mode_id") != expected_failure_mode_id:
        raise SupervisionLogError(
            "Critical route failure mode does not match the incident head"
        )
    if not str(failure_mode.get("correction", "")).strip():
        raise SupervisionLogError(
            "Critical route incident head lacks the exact correction"
        )
    resolution_owner = head.get("resolution_owner")
    if resolution_owner not in {"target", "supervisor"}:
        raise SupervisionLogError(
            "Critical route incident head lacks an autonomous resolution owner"
        )
    if head.get("user_action_required") != "no":
        raise SupervisionLogError(
            "Critical route incident head lacks a no-user-action posture"
        )
    next_trigger = str(head.get("action", "")).strip()
    if not next_trigger:
        raise SupervisionLogError(
            "Critical route incident head lacks an autonomous next effectiveness trigger"
        )
    record_sha256 = exact_sha256(
        str(head.get("record_sha256", "")),
        label="critical-route incident head SHA-256",
    )
    anchor = event_ledger_anchor(all_events)
    currentness_root = digest(
        {
            "incident_id": current_incident_id,
            "incident_head_record_id": source_record,
            "incident_head_record_sha256": record_sha256,
            "failure_mode_id": expected_failure_mode_id,
            "next_effectiveness_trigger_sha256": digest(next_trigger),
            "event_anchor_sha256": anchor["anchor_sha256"],
            "policy_sha256": policy["policy_sha256"],
        }
    )
    return {
        "incident_id": current_incident_id,
        "incident_head_record_id": source_record,
        "incident_head_record_sha256": record_sha256,
        "failure_mode_id": expected_failure_mode_id,
        "resolution_owner": str(resolution_owner),
        "user_action_required": "no",
        "next_effectiveness_trigger_sha256": digest(next_trigger),
        "incident_currentness_root_sha256": currentness_root,
    }


def cmd_thread_route_gate(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
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

    incident_head = None
    if (
        getattr(args, "severity", "info") == "critical"
        and containment is None
    ):
        if not getattr(args, "incident_id", None):
            raise SupervisionLogError(
                "Critical route requires an exact canonical incident ID"
            )
        if not getattr(args, "failure_mode_id", None):
            raise SupervisionLogError(
                "Critical route requires an exact failure mode ID"
            )
        incident_head = canonical_record_first_incident(
            directory=directory,
            policy=policy,
            source_record=source_record,
            incident_id_value=args.incident_id,
            failure_mode_id=args.failure_mode_id,
        )

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
    if incident_head is not None:
        result["critical_incident_head"] = incident_head
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
    return validate_capability_reconciliation(
        raw,
        target_thread=target_thread,
        mission_root=mission_root,
        state_fingerprint=state_fingerprint,
        current_revision=current_revision,
        policy=policy,
    )


def load_capability_reconciliation_base64(
    encoded_value: str,
    *,
    target_thread: str,
    mission_root: str,
    state_fingerprint: str,
    current_revision: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if not isinstance(encoded_value, str) or not encoded_value:
        raise SupervisionLogError(
            "Capability reconciliation base64 must be nonempty canonical text"
        )
    try:
        encoded = encoded_value.encode("ascii")
        raw = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise SupervisionLogError(
            "Capability reconciliation base64 is not valid canonical base64"
        ) from exc
    if base64.b64encode(raw) != encoded:
        raise SupervisionLogError(
            "Capability reconciliation base64 is not valid canonical base64"
        )
    if len(raw) > MAX_CAPABILITY_RECONCILIATION_BYTES:
        raise SupervisionLogError("Capability reconciliation exceeds its byte bound")
    return validate_capability_reconciliation(
        raw,
        target_thread=target_thread,
        mission_root=mission_root,
        state_fingerprint=state_fingerprint,
        current_revision=current_revision,
        policy=policy,
    )


def load_capability_reconciliation_input(
    path_value: str | None,
    base64_value: str | None,
    *,
    target_thread: str,
    mission_root: str,
    state_fingerprint: str,
    current_revision: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if (path_value is None) == (base64_value is None):
        raise SupervisionLogError(
            "Completion record requires exactly one capability reconciliation input"
        )
    if path_value is not None:
        return load_capability_reconciliation(
            path_value,
            target_thread=target_thread,
            mission_root=mission_root,
            state_fingerprint=state_fingerprint,
            current_revision=current_revision,
            policy=policy,
        )
    assert base64_value is not None
    return load_capability_reconciliation_base64(
        base64_value,
        target_thread=target_thread,
        mission_root=mission_root,
        state_fingerprint=state_fingerprint,
        current_revision=current_revision,
        policy=policy,
    )


def validate_capability_reconciliation(
    raw: bytes,
    *,
    target_thread: str,
    mission_root: str,
    state_fingerprint: str,
    current_revision: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
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
    evidence_values = [
        clean(item, label="evidence", maximum=160) for item in args.evidence
    ]
    if not evidence_values or not all(evidence_values):
        raise SupervisionLogError("Outcome completion requires exact source evidence")
    if len(evidence_values) > 16:
        raise SupervisionLogError("Too many outcome-completion evidence references")
    reconciliation, reconciliation_root = load_capability_reconciliation_input(
        getattr(args, "capability_reconciliation_json", None),
        getattr(args, "capability_reconciliation_base64", None),
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
    policy_snapshot: tuple[int, int, int, int] | None = None
    directory_snapshot: tuple[int, int, int, int] | None = None
    if args.kind == "lifecycle" and args.status == "completed":
        (
            directory,
            policy,
            policy_snapshot,
            directory_snapshot,
        ) = load_policy_directory_snapshot(args)
    else:
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
    terminal_record = args.kind == "lifecycle" and record["status"] == "completed"
    lock_context = (
        owner_append_lock(
            root_from(args), args.target_thread, directory_snapshot
        )
        if terminal_record and directory_snapshot is not None
        else append_lock(directory)
    )
    with lock_context as terminal_directory_fd:
        if args.kind == "lifecycle" and record["status"] == "completed":
            if terminal_directory_fd is None:
                current_events, event_snapshot = events_snapshot(
                    directory / "events.jsonl"
                )
            else:
                current_events, event_snapshot = events_snapshot(
                    Path("events.jsonl"), directory_fd=terminal_directory_fd
                )
        else:
            current_events = events(directory / "events.jsonl")
            event_snapshot = None
        if args.kind == "lifecycle" and record["status"] == "completed":
            range_state = implementation_range_state(policy)
            if range_state is not None and range_state["remaining_blocks"]:
                next_range_action = (
                    "continue-next-eligible-block"
                    if range_state["eligible_blocks"]
                    else "reconcile-unmet-dependencies-without-final-response"
                )
                raise SupervisionLogError(
                    "Completed lifecycle rejected by critical implementation-range "
                    f"gate: {next_range_action}"
                )
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
            control_posture = reduce_control_posture(
                directory=directory,
                policy=policy,
                owner_events=current_events,
                owner_policy_snapshot=policy_snapshot,
                owner_event_snapshot=event_snapshot,
                owner_directory_snapshot=directory_snapshot,
            )
            if (
                control_posture["issues"]
                or control_posture["open_transition_records"]
                or control_posture["open_decision_records"]
            ):
                raise SupervisionLogError(
                    "Completed lifecycle rejected by governing-outcome control: "
                    f"{control_posture['next_action']}"
                )
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

        if (
            args.kind == "lifecycle"
            and record["status"] == "completed"
            and directory_snapshot is not None
        ):
            assert terminal_directory_fd is not None
            try:
                (
                    _write_directory,
                    write_directory_fd,
                    write_directory_snapshot,
                ) = open_member_directory(root_from(args), args.target_thread)
            except SupervisionLogError as exc:
                raise SupervisionLogError(
                    "Completed lifecycle rejected by governing-outcome control: "
                    "retry-control-currentness"
                ) from exc
            try:
                if write_directory_snapshot != directory_snapshot:
                    raise SupervisionLogError(
                        "Completed lifecycle rejected by governing-outcome control: "
                        "retry-control-currentness"
                    )
                if (
                    path_snapshot_at(terminal_directory_fd, "events.jsonl")
                    != event_snapshot
                ):
                    raise SupervisionLogError(
                        "Completed lifecycle rejected by governing-outcome control: "
                        "retry-control-currentness"
                    )
                assert policy_snapshot is not None
                require_bound_policy_at(
                    terminal_directory_fd,
                    expected_policy=policy,
                    expected_snapshot=policy_snapshot,
                )
                prior_hash = (
                    current_events[-1].get("record_sha256")
                    if current_events
                    else None
                )
                appended_hash = append_raw_locked_at(
                    terminal_directory_fd,
                    "events.jsonl",
                    record,
                    previous_record_sha256=(
                        str(prior_hash) if prior_hash is not None else None
                    ),
                    expected_file_snapshot=event_snapshot,
                )
            finally:
                os.close(write_directory_fd)
            try:
                (
                    _verified_directory,
                    verified_directory_fd,
                    verified_directory_snapshot,
                ) = open_member_directory(root_from(args), args.target_thread)
            except SupervisionLogError as exc:
                raise SupervisionLogError(
                    "Completed lifecycle append lost canonical currentness"
                ) from exc
            try:
                assert policy_snapshot is not None
                require_bound_policy_at(
                    verified_directory_fd,
                    expected_policy=policy,
                    expected_snapshot=policy_snapshot,
                )
                if (
                    verified_directory_snapshot[:2] != directory_snapshot[:2]
                    or event_head_hash(
                        Path("events.jsonl"), directory_fd=verified_directory_fd
                    )
                    != appended_hash
                ):
                    raise SupervisionLogError(
                        "Completed lifecycle append lost canonical currentness"
                    )
            finally:
                os.close(verified_directory_fd)
        else:
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


def cmd_lifecycle_gate(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    source_record = safe_id(args.source_record, label="source record ID")
    lifecycle_state = args.lifecycle_state
    state_fingerprint = clean(
        args.state_fingerprint, label="state fingerprint", maximum=128
    )
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

    open_transitions = successor_transition_heads(all_events, open_only=True)
    transition_stop_conflict = bool(
        open_transitions
        and lifecycle_state in {"completed", "paused", "stopped"}
    )
    active_events = mission_scoped_events(directory, policy, all_events)
    open_activations = mission_activation_heads(active_events, open_only=True)
    activation_stop_conflict = bool(
        open_activations
        and lifecycle_state in {"completed", "paused", "stopped"}
    )
    range_state = implementation_range_state(policy)
    range_completion_conflict = bool(
        range_state is not None
        and range_state["remaining_blocks"]
        and lifecycle_state == "completed"
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
        if transition_stop_conflict:
            completion_permitted = False
            completion_reason = (
                "An open successor transition has not reached work-started; "
                "handoff is not completion of the governing requested scope."
            )
        if range_completion_conflict:
            completion_permitted = False
            completion_reason = (
                "Critical implementation-range gate retains requested Blocks; "
                "continue the dependency-safe frontier before terminalization."
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
        terminal_delivery = latest_terminal_delivery(
            all_events, lifecycle_record_id=source_record
        )
        if terminal_delivery is None:
            terminal_report_reason = (
                "Generate, verify, and email both terminal PDF reports before pausing supervision."
            )
        else:
            terminal_report_set_id = str(terminal_delivery.get("report_set_id", ""))
            try:
                verified_terminal = verify_terminal_report_set(
                    directory, terminal_report_set_id
                )
                terminal_reports_delivered = bool(
                    terminal_delivery_is_current(
                        terminal_delivery, verified_terminal
                    )
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
        enabled
        and not duplicate
        and completion_permitted
        and not terminal_reporting
    )
    supervision_pause_permitted = bool(
        lifecycle_state == "completed"
        and completion_permitted
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
    control_posture = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=all_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
    supervision_pause_permitted = bool(
        supervision_pause_permitted
        and control_posture["required_target_posture"] == "completed"
    )
    print(
        json.dumps(
            {
                "banner": notification_config.get("banner") if send_now else None,
                "channel": (
                    "priority-lifecycle"
                    if send_now and priority_lifecycle
                    else "primary-status" if send_now else "none"
                ),
                "completion_action": (
                    "continue-next-eligible-block"
                    if range_completion_conflict
                    and range_state is not None
                    and range_state["eligible_blocks"]
                    else "reconcile-unmet-dependencies-without-final-response"
                    if range_completion_conflict
                    else MISSION_ACTIVATION_START_ACTION
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
                "source_stop_permitted": bool(
                    control_posture["required_target_posture"]
                    in {"blocked", "completed", "stopped"}
                    and not transition_stop_conflict
                    and not activation_stop_conflict
                ),
                "required_target_posture": control_posture[
                    "required_target_posture"
                ],
                "control_posture": control_posture,
                "state_fingerprint": source.get("state_fingerprint", ""),
                "open_mission_activations": list(open_activations.values()),
                "open_successor_transitions": list(open_transitions.values()),
                "implementation_range": range_state,
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
        if item.get("phase") not in SUCCESSOR_TRANSITION_CLOSED_PHASES
        and successor_transition_is_activated(heads, transition_id, item)
    }


def successor_transition_is_activated(
    heads: Mapping[str, Mapping[str, Any]],
    transition_id: str,
    head: Mapping[str, Any],
) -> bool:
    predecessor_id = head.get("replaces_transition_id")
    if not predecessor_id:
        return True
    predecessor = heads.get(str(predecessor_id))
    return bool(
        predecessor is not None
        and predecessor.get("phase") == "superseded"
        and predecessor.get("replacement_transition_id") == transition_id
    )


def decode_legacy_direct_authority_provenance(
    encoded_value: str,
) -> dict[str, Any]:
    if not isinstance(encoded_value, str) or not encoded_value:
        raise SupervisionLogError(
            "Legacy direct-authority provenance must be nonempty canonical base64"
        )
    try:
        encoded = encoded_value.encode("ascii")
        raw = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise SupervisionLogError(
            "Legacy direct-authority provenance is not valid canonical base64"
        ) from exc
    if base64.b64encode(raw) != encoded:
        raise SupervisionLogError(
            "Legacy direct-authority provenance is not valid canonical base64"
        )
    if len(raw) > MAX_LEGACY_DIRECT_AUTHORITY_PROVENANCE_BYTES:
        raise SupervisionLogError(
            "Legacy direct-authority provenance exceeds its byte bound"
        )
    try:
        value = json.loads(raw, object_pairs_hook=reject_duplicate_json_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError(
            "Legacy direct-authority provenance is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise SupervisionLogError(
            "Legacy direct-authority provenance must be a JSON object"
        )
    validate_exact_json_value(value)
    if raw != canonical(value):
        raise SupervisionLogError(
            "Legacy direct-authority provenance is not exact canonical JSON"
        )
    return value


def legacy_full_tracker_request_projection(
    request_text: str,
) -> dict[str, str]:
    pattern = re.compile(
        r"^\[\$author-implementation-trackers\]"
        r"\((?P<author>/Users/[^)\r\n]+/author-implementation-trackers/SKILL\.md)\)"
        r" for this all / make sure the tracker is up to date with what we've discussed\. "
        r"then \[\$implement-tracker-blocks\]"
        r"\((?P<implement>/Users/[^)\r\n]+/implement-tracker-blocks/SKILL\.md)\)"
        r" for that tracker\n$"
    )
    match = pattern.fullmatch(request_text)
    if match is None:
        raise SupervisionLogError(
            "Legacy implementation request does not match the allowlisted skill-link form"
        )
    author = Path(match.group("author"))
    implement = Path(match.group("implement"))
    if (
        not author.is_absolute()
        or not implement.is_absolute()
        or author.name != "SKILL.md"
        or implement.name != "SKILL.md"
        or author.parent.name != "author-implementation-trackers"
        or implement.parent.name != "implement-tracker-blocks"
        or author.parent.parent != implement.parent.parent
        or author.parent.parent.name != "software_factory"
    ):
        raise SupervisionLogError(
            "Legacy implementation request skill-link destinations differ"
        )
    return {
        "classification": LEGACY_DIRECT_AUTHORITY_CLASSIFICATION,
        "range_intent": "full-tracker",
    }


def legacy_direct_authority_review_evidence(
    provenance: Mapping[str, Any],
) -> list[str]:
    return [
        f"source-task:{provenance['source_task_id']}",
        f"source-turn:{provenance['source_turn_id']}",
        f"source-item:{provenance['source_item_id']}",
        f"source-byte-count:{provenance['source_byte_count']}",
        f"source-sha256:{provenance['source_sha256']}",
        f"verifier:{provenance['verifier_id']}",
        f"legacy-transition-record:{provenance['legacy_transition_record_id']}",
        f"legacy-transition-id:{provenance['legacy_transition_id']}",
    ]


def legacy_direct_authority_event_evidence(
    provenance: Mapping[str, Any], authorization: Mapping[str, Any]
) -> list[str]:
    return [
        *legacy_direct_authority_review_evidence(provenance),
        "authorization-record:"
        + ":".join(
            (
                str(authorization["record_id"]),
                str(authorization["record_sha256"]),
            )
        ),
        f"classification:{LEGACY_DIRECT_AUTHORITY_CLASSIFICATION}",
    ]


def canonical_legacy_direct_authority_review(
    all_events: list[dict[str, Any]],
    *,
    provenance: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    record_id = safe_id(
        str(provenance["authorization_record_id"]),
        label="legacy authority review record",
    )
    event = next(
        (item for item in all_events if item.get("record_id") == record_id),
        None,
    )
    if event is None:
        raise SupervisionLogError(
            "Legacy direct-authority review is not in the canonical event ledger"
        )
    verifier_id = safe_id(
        str(provenance["verifier_id"]),
        label="legacy authority independent verifier",
    )
    runtime = policy.get("runtime", {})
    eligible = {
        runtime.get("base_reviewer_thread_id"),
        runtime.get("reviewer_thread_id"),
    }
    disallowed = {
        policy.get("target_thread_id"),
        runtime.get("watcher_thread_id"),
        runtime.get("fix_executor_thread_id"),
    }
    evidence = event.get("evidence")
    expected_review_kind = (
        "checkpoint-review"
        if verifier_id == runtime.get("base_reviewer_thread_id")
        else "meta-review"
    )
    if (
        verifier_id not in eligible
        or verifier_id in disallowed
        or event.get("schema_version") != 1
        or event.get("target_thread_id") != policy.get("target_thread_id")
        or event.get("kind") != expected_review_kind
        or event.get("category") != LEGACY_DIRECT_AUTHORITY_REVIEW_CATEGORY
        or event.get("status") != "accepted"
        or event.get("model") != "gpt-5.6-sol"
        or event.get("reasoning") not in {"xhigh", "max"}
        or event.get("resolution_owner") != "supervisor"
        or event.get("user_action_required") != "no"
        or event.get("policy_sha256") != provenance.get("policy_sha256")
        or not isinstance(evidence, list)
        or not all(
            item in evidence
            for item in legacy_direct_authority_review_evidence(provenance)
        )
    ):
        raise SupervisionLogError(
            "Legacy direct-authority review does not bind independent exact provenance"
        )
    exact_sha256(
        str(event.get("record_sha256", "")),
        label="legacy authority review record SHA-256",
    )
    return event


def canonical_legacy_successor_transition(
    all_events: list[dict[str, Any]],
    *,
    provenance: Mapping[str, Any],
    policy: Mapping[str, Any],
    policy_history: list[dict[str, Any]],
    require_open: bool,
) -> dict[str, Any]:
    transition_id = safe_id(
        str(provenance["legacy_transition_id"]),
        label="legacy successor transition ID",
    )
    transition_record_id = safe_id(
        str(provenance["legacy_transition_record_id"]),
        label="legacy successor transition record",
    )
    records = successor_transition_events(all_events, transition_id)
    event = next(
        (item for item in records if item.get("record_id") == transition_record_id),
        None,
    )
    if event is None:
        raise SupervisionLogError(
            "Legacy successor transition is not in the canonical event ledger"
        )
    source_policy_sha256 = exact_sha256(
        str(event.get("policy_sha256", "")),
        label="legacy successor transition policy SHA-256",
    )
    if not any(
        isinstance(item.get("policy"), Mapping)
        and item["policy"].get("policy_sha256") == source_policy_sha256
        for item in policy_history
    ):
        raise SupervisionLogError(
            "Legacy successor transition is not anchored to policy history"
        )
    if (
        (require_open and len(records) != 1)
        or event.get("schema_version") != 1
        or event.get("target_thread_id") != policy.get("target_thread_id")
        or event.get("phase") != "required"
        or event.get("governing_authority_source_class") != "direct-user"
        or event.get("governing_authority_source_record")
        != provenance.get("source_item_id")
        or event.get("governing_authority_source_sha256")
        or event.get("topology_posture")
        or event.get("topology_basis")
        or event.get("topology_decision_event_record_id")
        or event.get("topology_decision_event_sha256")
    ):
        raise SupervisionLogError(
            "Successor transition is not the exact unbound legacy authority transition"
        )
    if require_open:
        open_head = successor_transition_heads(all_events, open_only=True).get(
            transition_id
        )
        if open_head is None or open_head.get("record_id") != transition_record_id:
            raise SupervisionLogError(
                "Legacy successor transition is no longer the open canonical head"
            )
    return event


def validate_legacy_direct_authority_provenance(
    provenance: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    policy_history: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
    require_current_policy: bool,
    require_open_transition: bool,
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    expected = {
        "schema_version",
        "kind",
        "target_thread_id",
        "source_task_id",
        "source_turn_id",
        "source_item_id",
        "source_text",
        "source_byte_count",
        "source_sha256",
        "policy_version",
        "policy_sha256",
        "verifier_id",
        "authorization_record_id",
        "legacy_transition_record_id",
        "legacy_transition_id",
    }
    if set(provenance) != expected:
        raise SupervisionLogError(
            "Legacy direct-authority provenance shape differs"
        )
    if (
        provenance.get("schema_version") != 1
        or provenance.get("kind") != LEGACY_DIRECT_AUTHORITY_PROVENANCE_KIND
        or provenance.get("target_thread_id") != policy.get("target_thread_id")
        or provenance.get("source_task_id") != policy.get("target_thread_id")
    ):
        raise SupervisionLogError(
            "Legacy direct-authority target or provenance kind differs"
        )
    for field, label in (
        ("source_task_id", "legacy authority source task"),
        ("source_turn_id", "legacy authority source turn"),
        ("source_item_id", "legacy authority source item"),
    ):
        safe_id(str(provenance[field]), label=label)
    source_text = provenance.get("source_text")
    if not isinstance(source_text, str):
        raise SupervisionLogError("Legacy direct-authority source text is not exact")
    source_bytes = source_text.encode("utf-8")
    source_byte_count = provenance.get("source_byte_count")
    if (
        type(source_byte_count) is not int
        or source_byte_count <= 0
        or source_byte_count > 1200
        or len(source_bytes) != source_byte_count
    ):
        raise SupervisionLogError(
            "Legacy direct-authority source byte count differs"
        )
    source_sha256 = exact_sha256(
        str(provenance["source_sha256"]),
        label="legacy authority source SHA-256",
    )
    if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
        raise SupervisionLogError(
            "Legacy direct-authority source bytes differ from their SHA-256"
        )
    source_policy_sha256 = exact_sha256(
        str(provenance["policy_sha256"]),
        label="legacy authority policy SHA-256",
    )
    policy_version = provenance.get("policy_version")
    if type(policy_version) is not int or policy_version <= 0:
        raise SupervisionLogError(
            "Legacy direct-authority policy version is invalid"
        )
    historical_policy = next(
        (
            item.get("policy")
            for item in policy_history
            if isinstance(item.get("policy"), Mapping)
            and item["policy"].get("policy_version") == policy_version
            and item["policy"].get("policy_sha256") == source_policy_sha256
        ),
        None,
    )
    if historical_policy is None:
        raise SupervisionLogError(
            "Legacy direct-authority provenance is not anchored to policy history"
        )
    if require_current_policy and (
        policy_version != policy.get("policy_version")
        or source_policy_sha256 != policy.get("policy_sha256")
    ):
        raise SupervisionLogError(
            "Legacy direct-authority provenance policy is stale"
        )
    authorization = canonical_legacy_direct_authority_review(
        all_events,
        provenance=provenance,
        policy=policy,
    )
    transition = canonical_legacy_successor_transition(
        all_events,
        provenance=provenance,
        policy=policy,
        policy_history=policy_history,
        require_open=require_open_transition,
    )
    event_order = {
        str(item.get("record_id")): index
        for index, item in enumerate(all_events)
    }
    if event_order[str(transition["record_id"])] >= event_order[
        str(authorization["record_id"])
    ]:
        raise SupervisionLogError(
            "Legacy successor transition must precede its independent authorization"
        )
    projection = legacy_full_tracker_request_projection(source_text)
    return projection, authorization, transition


def transition_first_record(
    all_events: list[dict[str, Any]], transition_id: str
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in all_events
            if item.get("kind") == "successor-transition"
            and item.get("transition_id") == transition_id
        ),
        None,
    )


def implementation_tracker_snapshot(
    path_value: str,
) -> tuple[Path, str, str, dict[int, dict[str, Any]]]:
    supplied = Path(path_value).expanduser()
    descriptor = -1
    try:
        resolved = supplied.resolve(strict=True)
        if supplied.is_symlink():
            raise SupervisionLogError(
                "Implementation tracker must be one explicit non-symlink file"
            )
        descriptor = os.open(
            resolved,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SupervisionLogError("Implementation tracker is not a regular file")
        if before.st_size > MAX_IMPLEMENTATION_TRACKER_BYTES:
            raise SupervisionLogError("Implementation tracker exceeds its byte bound")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_IMPLEMENTATION_TRACKER_BYTES + 1)
            after = os.fstat(handle.fileno())
        if file_snapshot(before) != file_snapshot(after) or path_snapshot(resolved) != file_snapshot(after):
            raise SupervisionLogError("Implementation tracker changed while reading")
    except OSError as exc:
        raise SupervisionLogError("Implementation tracker cannot be read") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_IMPLEMENTATION_TRACKER_BYTES:
        raise SupervisionLogError("Implementation tracker exceeds its byte bound")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SupervisionLogError("Implementation tracker is not UTF-8") from exc
    heading_values = [int(value) for value in IMPLEMENTATION_BLOCK_HEADING.findall(text)]
    headings = set(heading_values)
    if len(heading_values) != len(headings):
        raise SupervisionLogError("Implementation tracker repeats a Block heading")
    rows: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        match = IMPLEMENTATION_TABLE_ROW.match(line)
        if match is None:
            continue
        number = int(match.group(1))
        cells = [item.strip().strip("`") for item in line.strip().strip("|").split("|")]
        if len(cells) < 4 or number not in headings:
            continue
        if number in rows:
            raise SupervisionLogError("Implementation tracker repeats a status row")
        rows[number] = {
            "scope": cells[1],
            "dependencies": [int(item) for item in re.findall(r"\d+", cells[2])],
            "status": cells[3],
        }
    missing = sorted(headings - set(rows))
    if missing or not rows:
        raise SupervisionLogError(
            "Implementation tracker status table is incomplete"
        )
    block_matches = list(IMPLEMENTATION_BLOCK_HEADING.finditer(text))
    block_contract_roots: list[dict[str, Any]] = []
    for index, match in enumerate(block_matches):
        number = int(match.group(1))
        end = block_matches[index + 1].start() if index + 1 < len(block_matches) else len(text)
        section_text = text[match.start():end]
        section_lines = section_text.splitlines()
        normalized_lines: list[str] = []
        in_completion_evidence = False
        for line in section_lines:
            if re.match(r"^Status:\s*", line):
                normalized_lines.append("Status: <runtime-state>")
                continue
            if line.strip() == "### Completion evidence":
                in_completion_evidence = True
                normalized_lines.append(line)
                continue
            if in_completion_evidence and re.match(r"^###\s+", line):
                in_completion_evidence = False
            if not in_completion_evidence:
                normalized_lines.append(line.rstrip())
        contract_sha256 = hashlib.sha256(
            "\n".join(normalized_lines).strip().encode("utf-8")
        ).hexdigest()
        capability_match = re.search(
            r"^### Target-product capability delta\s*$\n(.*?)(?=^###\s+)",
            section_text,
            re.M | re.S,
        )
        capability_frame_sha256 = (
            hashlib.sha256(
                capability_match.group(1).strip().encode("utf-8")
            ).hexdigest()
            if capability_match is not None
            else ""
        )
        rows[number]["contract_sha256"] = contract_sha256
        rows[number]["capability_frame_sha256"] = capability_frame_sha256
        block_contract_roots.append(
            {
                "number": number,
                "scope": rows[number]["scope"],
                "dependencies": rows[number]["dependencies"],
                "contract_sha256": contract_sha256,
            }
        )
    structure_sha256 = digest(
        {
            "schema_version": 1,
            "kind": "implementation-tracker-structure",
            "blocks": block_contract_roots,
        }
    )
    return resolved, hashlib.sha256(raw).hexdigest(), structure_sha256, rows


def classify_implementation_request(
    request_text: str, blocks: set[int]
) -> tuple[str, list[int]]:
    value = clean(
        request_text,
        label="implementation range request text",
        maximum=1200,
    )
    def exact_blocks(expression: str) -> list[int]:
        normalized = expression.strip().lower().rstrip(".!")
        range_match = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", normalized)
        if range_match is not None:
            start, end = map(int, range_match.groups())
            if end < start:
                raise SupervisionLogError("Implementation range is reversed")
            requested = list(range(start, end + 1))
        else:
            parts = re.split(r"\s*(?:,|\band\b)\s*", normalized)
            if not parts or not all(part.isdigit() for part in parts):
                raise SupervisionLogError("Explicit implementation Block list is invalid")
            requested = [int(part) for part in parts]
            if len(requested) != len(set(requested)):
                raise SupervisionLogError("Explicit implementation Block list repeats a Block")
        if set(requested) - blocks:
            raise SupervisionLogError("Implementation range cites absent Blocks")
        return sorted(requested)

    block_expression = r"(\d+(?:\s*[-–]\s*\d+|(?:\s*(?:,|\band\b)\s*\d+)*))"
    positive_explicit: list[list[int]] = []
    positive_full = False
    clauses = re.split(r"\s*;\s*|\s*,\s*but\s+", value)
    for raw_clause in clauses:
        clause = raw_clause.strip()
        invocation_present = bool(
            re.search(r"\$?implement-tracker-blocks\b", clause, re.I)
        )
        clause = re.sub(
            r"\[\$?implement-tracker-blocks\]\([^)]*\)",
            "",
            clause,
            flags=re.I,
        )
        clause = re.sub(
            r"\$?implement-tracker-blocks\b\s*:?s*",
            "",
            clause,
            count=1,
            flags=re.I,
        ).strip()
        clause = re.sub(r"^use\s+", "", clause, flags=re.I)
        clause = re.sub(r"^for\s+", "", clause, flags=re.I)
        if not clause and invocation_present:
            positive_full = True
            continue
        normalized_clause = re.sub(r"^(?:please\s+)", "", clause, flags=re.I)
        if re.match(r"^(?:do\s+not|don't|never)\b", normalized_clause, re.I):
            continue
        explicit_match = None
        for pattern in (
            rf"(?:implement|execute|continue|do)\s+only\s+blocks?\s+{block_expression}",
            rf"(?:implement|execute|continue|do)\s+blocks?\s+{block_expression}\s+only",
            rf"only\s+blocks?\s+{block_expression}",
            rf"blocks?\s+{block_expression}\s+only",
            rf"(?:implement|execute|continue|do)\s+blocks?\s+{block_expression}",
            rf"blocks?\s+{block_expression}",
        ):
            explicit_match = re.fullmatch(
                rf"\s*{pattern}\s*[.!]?\s*", normalized_clause, re.I
            )
            if explicit_match is not None:
                break
        if explicit_match is not None:
            positive_explicit.append(exact_blocks(explicit_match.group(1)))
            continue
        lowered_clause = normalized_clause.lower().strip(" .!")
        if (
            lowered_clause in {"all", "full"}
            or re.fullmatch(
                r"(?:implement|execute|continue|do)\s+all(?:\s+(?:blocks?|of\s+the\s+blocks?))?",
                lowered_clause,
            )
            or re.fullmatch(
                r"(?:implement|execute|continue|do)(?:\s+and\s+finish)?\s+"
                r"(?:this|the|entire|complete|full)\s+tracker",
                lowered_clause,
            )
            or lowered_clause in {
                "this tracker",
                "the tracker",
                "entire tracker",
                "complete tracker",
                "full tracker",
            }
        ):
            positive_full = True
    if len({tuple(item) for item in positive_explicit}) > 1:
        raise SupervisionLogError(
            "Implementation request has contradictory explicit Block ranges"
        )
    if positive_explicit and positive_full:
        if re.search(r",\s*but\s+only\s+blocks?\b", value, re.I):
            return "explicit-blocks", positive_explicit[-1]
        raise SupervisionLogError(
            "Implementation request has contradictory full and bounded commands"
        )
    if positive_explicit:
        return "explicit-blocks", positive_explicit[-1]
    if positive_full:
        return "full-tracker", sorted(blocks)
    if re.fullmatch(r"\d+(?:\s*[-–]\s*\d+)?", value.lower()):
        return "explicit-blocks", exact_blocks(value)
    raise SupervisionLogError(
        "Implementation request does not establish full-tracker or exact Block intent"
    )


def direct_request_requires_distinct_task(request_text: str) -> bool:
    value = clean(
        request_text,
        label="distinct-task direct request text",
        maximum=1200,
    )
    task_phrase = (
        r"(?:distinct|separate|new)(?:\s+successor)?\s+"
        r"(?:codex\s+)?(?:task|thread|chat|conversation)"
        r"|successor\s+(?:codex\s+)?(?:task|thread|chat|conversation)"
    )
    if re.search(
        r"\b(?:do\s+not|don't|never|without|avoid|instead\s+of|"
        r"current\s+(?:task|thread|chat|conversation)|"
        r"same\s+(?:task|thread|chat|conversation)|"
        r"if|unless|only\s+if|when(?:ever)?|where|as\s+needed|"
        r"necessary|needed|provided|depending|feasible|feasibility|"
        r"subject\s+to|assuming|otherwise|or|may|might|could|"
        r"optional(?:ly)?)\b",
        value,
        re.I,
    ):
        return False
    clauses = [item.strip() for item in re.split(r"[.;]", value) if item.strip()]
    if len(clauses) != 1:
        return False
    clause = clauses[0]
    return bool(
        re.fullmatch(
            rf"(?:please\s+)?(?:create|start|use)\s+(?:a|one|the)\s+"
            rf"(?:{task_phrase})(?:\s+for\s+"
            rf"(?:this(?:\s+(?:work|implementation|tracker))?|"
            rf"the\s+(?:work|implementation|tracker)))?",
            clause,
            re.I,
        )
        or re.fullmatch(
            rf"(?:please\s+)?(?:move|continue|implement|execute|run)\b"
            rf".{{0,140}}\b(?:in|within|through|to)\s+"
            rf"(?:a|one|the)\s+(?:{task_phrase})",
            clause,
            re.I,
        )
    )


def implementation_range_contract(policy: Mapping[str, Any]) -> dict[str, Any] | None:
    value = policy.get("implementation_range")
    return dict(value) if isinstance(value, Mapping) else None


def validate_implementation_range_contract(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != 1 or value.get("kind") != "implementation-range-binding":
        raise SupervisionLogError("Implementation range binding schema differs")
    safe_id(str(value.get("range_id", "")), label="implementation range ID")
    if value.get("range_intent") not in IMPLEMENTATION_RANGE_INTENTS:
        raise SupervisionLogError("Implementation range intent is invalid")
    exact_sha256(str(value.get("genesis_sha256", "")), label="range genesis SHA-256")
    exact_sha256(str(value.get("tracker_sha256", "")), label="range tracker SHA-256")
    exact_sha256(
        str(value.get("tracker_structure_sha256", "")),
        label="range tracker structure SHA-256",
    )
    tracker_path = value.get("tracker_path")
    if not isinstance(tracker_path, str) or not Path(tracker_path).is_absolute():
        raise SupervisionLogError("Implementation range tracker path is not exact")
    source = value.get("authority")
    if not isinstance(source, Mapping) or source.get("source_class") != "direct-user":
        raise SupervisionLogError("Implementation range lacks direct-user authority")
    safe_id(str(source.get("source_record", "")), label="range authority source record")
    exact_sha256(str(source.get("source_sha256", "")), label="range authority source SHA-256")
    explicit = value.get("explicit_blocks")
    if not isinstance(explicit, list) or not all(isinstance(item, int) for item in explicit):
        raise SupervisionLogError("Implementation range explicit Block set is invalid")
    if value.get("range_intent") == "full-tracker" and explicit:
        raise SupervisionLogError("Full-tracker binding cannot carry an explicit subset")
    tracker_blocks = value.get("tracker_blocks")
    if (
        not isinstance(tracker_blocks, list)
        or not tracker_blocks
        or not all(isinstance(item, int) for item in tracker_blocks)
        or tracker_blocks != sorted(set(tracker_blocks))
    ):
        raise SupervisionLogError("Implementation range tracker Block set is invalid")
    history = value.get("history")
    if not isinstance(history, list) or not history:
        raise SupervisionLogError("Implementation range lacks append-only history")
    prior_hash = ""
    prior_authority_version = 0
    for index, item in enumerate(history):
        if not isinstance(item, Mapping):
            raise SupervisionLogError("Implementation range history is malformed")
        if item.get("sequence") != index + 1 or item.get("prior_entry_sha256", "") != prior_hash:
            raise SupervisionLogError("Implementation range history chain differs")
        material = {key: item[key] for key in item if key != "entry_sha256"}
        expected = digest(material)
        if item.get("entry_sha256") != expected:
            raise SupervisionLogError("Implementation range history entry hash is stale")
        exact_sha256(
            str(item.get("tracker_structure_sha256", "")),
            label="range-history tracker structure SHA-256",
        )
        authority_version = item.get("authority_policy_version")
        if not isinstance(authority_version, int) or authority_version <= 0:
            raise SupervisionLogError(
                "Implementation range authority version is invalid"
            )
        if item.get("operation") == "contracted" and authority_version <= prior_authority_version:
            raise SupervisionLogError(
                "Implementation range contraction authority is not newer"
            )
        prior_authority_version = max(prior_authority_version, authority_version)
        prior_hash = expected
    if value.get("history_head_sha256") != prior_hash:
        raise SupervisionLogError("Implementation range history head is stale")
    head = history[-1]
    for contract_field, history_field in (
        ("tracker_sha256", "tracker_sha256"),
        ("tracker_structure_sha256", "tracker_structure_sha256"),
        ("tracker_path", "tracker_path"),
        ("range_intent", "range_intent"),
        ("explicit_blocks", "explicit_blocks"),
        ("tracker_blocks", "tracker_blocks"),
        ("authority", "authority"),
    ):
        if value.get(contract_field) != head.get(history_field):
            raise SupervisionLogError(
                f"Implementation range current {contract_field.replace('_', ' ')} "
                "differs from its append-only head"
            )
    genesis_material = {
        "range_id": value["range_id"],
        "authority": history[0].get("authority"),
        "request_text_sha256": history[0].get("request_text_sha256"),
        "initial_tracker_sha256": history[0].get("tracker_sha256"),
        "initial_tracker_structure_sha256": history[0].get(
            "tracker_structure_sha256"
        ),
        "initial_tracker_blocks": history[0].get("tracker_blocks"),
        "initial_range_intent": history[0].get("range_intent"),
        "initial_explicit_blocks": history[0].get("explicit_blocks"),
    }
    if value.get("genesis_sha256") != digest(genesis_material):
        raise SupervisionLogError("Implementation range immutable genesis differs")


def eligible_direct_authority(
    policy: Mapping[str, Any], source_record: str, source_sha256: str
) -> bool:
    mission = bound_mission(dict(policy))
    if mission is not None:
        controlling = mission.get("mission_derivation", {}).get("controlling_source", {})
        if (
            controlling.get("class") == "direct-user"
            and controlling.get("record") == source_record
            and controlling.get("sha256") == source_sha256
        ):
            return True
    receipts = policy.get("direct_authority_receipts", [])
    return any(
        isinstance(item, Mapping)
        and item.get("source_class") == "direct-user"
        and item.get("source_record") == source_record
        and item.get("source_sha256") == source_sha256
        and item.get("accepted") is True
        for item in receipts
    )


def canonical_authority_source(
    policy: Mapping[str, Any],
    *,
    source_class: str,
    source_record: str,
    source_sha256: str,
) -> bool:
    mission = bound_mission(dict(policy))
    controlling = (
        mission.get("mission_derivation", {}).get("controlling_source", {})
        if mission is not None
        else {}
    )
    if (
        controlling.get("class") == source_class
        and controlling.get("record") == source_record
        and controlling.get("sha256") == source_sha256
    ):
        return True
    if (
        mission is not None
        and mission.get("mission_derivation", {}).get("mode")
        == "explicit-exact-root"
        and source_class in DIRECT_AUTHORITY_SOURCE_CLASSES
        and mission.get("mission_source_record") == source_record
        and mission.get("mission_root") == source_sha256
    ):
        return True
    return bool(
        source_class == "direct-user"
        and eligible_direct_authority(policy, source_record, source_sha256)
    )


def implementation_range_requested_blocks(
    contract: Mapping[str, Any], blocks: set[int]
) -> list[int]:
    if contract.get("range_intent") == "full-tracker":
        return sorted(blocks)
    requested = contract.get("explicit_blocks", [])
    if set(requested) - blocks:
        raise SupervisionLogError(
            "Bound explicit Blocks require an exact accepted renumbering map"
        )
    return sorted(set(requested))


def format_implementation_block_set(blocks: list[int]) -> str:
    if not blocks:
        raise SupervisionLogError("Implementation range has no requested Blocks")
    if len(blocks) == 1:
        return f"Block {blocks[0]}"
    if blocks == list(range(blocks[0], blocks[-1] + 1)):
        return f"Blocks {blocks[0]}-{blocks[-1]}"
    return "Blocks " + ",".join(str(item) for item in blocks)


def implementation_range_state(
    policy: Mapping[str, Any], *, require_tracker_hash: bool = True
) -> dict[str, Any] | None:
    contract = implementation_range_contract(policy)
    if contract is None:
        return None
    validate_implementation_range_contract(contract)
    path, tracker_sha256, tracker_structure_sha256, blocks = implementation_tracker_snapshot(
        str(contract["tracker_path"])
    )
    if str(path) != contract["tracker_path"]:
        raise SupervisionLogError("Implementation tracker path identity changed")
    if require_tracker_hash and tracker_sha256 != contract["tracker_sha256"]:
        raise SupervisionLogError(
            "Implementation tracker changed without an accepted range amendment"
        )
    if tracker_structure_sha256 != contract["tracker_structure_sha256"]:
        raise SupervisionLogError(
            "Implementation tracker structure changed without an accepted amendment"
        )
    requested = implementation_range_requested_blocks(contract, set(blocks))
    completed_tracker_blocks = {
        number for number in blocks if blocks[number]["status"] == "completed"
    }
    accepted = [
        number for number in requested if blocks[number]["status"] == "completed"
    ]
    remaining = [number for number in requested if number not in accepted]
    eligible = [
        number
        for number in remaining
        if all(
            dependency in completed_tracker_blocks
            for dependency in blocks[number]["dependencies"]
        )
    ]
    return {
        "range_id": contract["range_id"],
        "range_intent": contract["range_intent"],
        "tracker_path": str(path),
        "tracker_sha256": tracker_sha256,
        "tracker_structure_sha256": tracker_structure_sha256,
        "requested_blocks": requested,
        "accepted_blocks": accepted,
        "completed_prerequisite_blocks": sorted(
            completed_tracker_blocks - set(requested)
        ),
        "remaining_blocks": remaining,
        "eligible_blocks": eligible,
        "range_history_head_sha256": contract["history_head_sha256"],
    }


def legacy_direct_authority_event_material(
    provenance: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target_thread_id": provenance["target_thread_id"],
        "kind": DIRECT_AUTHORITY_EVENT_KIND,
        "source_class": "direct-user",
        "source_record": provenance["source_item_id"],
        "source_sha256": provenance["source_sha256"],
        "source_task_id": provenance["source_task_id"],
        "source_item_id": provenance["source_item_id"],
        "verifier_id": provenance["verifier_id"],
        "provenance_status": "verified-before-entry",
        "policy_sha256": provenance["policy_sha256"],
        "evidence": legacy_direct_authority_event_evidence(
            provenance, authorization
        ),
    }


def matching_legacy_direct_authority_event(
    all_events: list[dict[str, Any]],
    *,
    provenance: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> dict[str, Any] | None:
    expected = legacy_direct_authority_event_material(provenance, authorization)
    authorization_token = (
        "authorization-record:"
        + str(authorization["record_id"])
        + ":"
        + str(authorization["record_sha256"])
    )
    related = [
        item
        for item in all_events
        if item.get("kind") == DIRECT_AUTHORITY_EVENT_KIND
        and (
            item.get("source_record") == provenance.get("source_item_id")
            or (
                isinstance(item.get("evidence"), list)
                and authorization_token in item["evidence"]
            )
        )
    ]
    for item in related:
        comparable = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "record_id",
                "timestamp",
                "previous_record_sha256",
                "record_sha256",
            }
        }
        if comparable == expected:
            return item
    if related:
        raise SupervisionLogError(
            "Legacy direct-authority source or review was already used with different provenance"
        )
    return None


def cmd_legacy_direct_authority_ingest(args: argparse.Namespace) -> None:
    provenance = decode_legacy_direct_authority_provenance(args.provenance_base64)
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    validate_event_ledger_anchor(
        directory, all_events, allow_missing=not all_events
    )
    policy_history = events(directory / "policy-history.jsonl")
    projection, authorization, _transition = (
        validate_legacy_direct_authority_provenance(
            provenance,
            policy=policy,
            policy_history=policy_history,
            all_events=all_events,
            require_current_policy=False,
            require_open_transition=False,
        )
    )
    duplicate = matching_legacy_direct_authority_event(
        all_events,
        provenance=provenance,
        authorization=authorization,
    )
    if duplicate is not None:
        print(
            json.dumps(
                {
                    "duplicate": True,
                    "record_id": duplicate["record_id"],
                    "record_sha256": duplicate["record_sha256"],
                    "source_record": duplicate["source_record"],
                    "source_sha256": duplicate["source_sha256"],
                    "classification": projection["classification"],
                },
                sort_keys=True,
            )
        )
        return
    validate_legacy_direct_authority_provenance(
        provenance,
        policy=policy,
        policy_history=policy_history,
        all_events=all_events,
        require_current_policy=True,
        require_open_transition=True,
    )
    record = {
        "record_id": "",
        "timestamp": utc_now(),
        **legacy_direct_authority_event_material(provenance, authorization),
    }
    with owner_append_lock(
        root_from(args), args.target_thread, directory_snapshot
    ) as directory_fd:
        require_bound_policy_at(
            directory_fd,
            expected_policy=policy,
            expected_snapshot=policy_snapshot,
        )
        current_events, current_event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        current_policy_history, _history_snapshot = events_snapshot(
            Path("policy-history.jsonl"), directory_fd=directory_fd
        )
        validate_event_ledger_anchor_at(
            directory_fd,
            current_events,
            allow_missing=not current_events,
        )
        if current_event_snapshot != event_snapshot or current_events != all_events:
            raise SupervisionLogError(
                "Legacy direct-authority event state changed before append"
            )
        current_projection, current_authorization, _current_transition = (
            validate_legacy_direct_authority_provenance(
                provenance,
                policy=policy,
                policy_history=current_policy_history,
                all_events=current_events,
                require_current_policy=True,
                require_open_transition=True,
            )
        )
        if current_projection != projection or current_authorization != authorization:
            raise SupervisionLogError(
                "Legacy direct-authority provenance changed before append"
            )
        duplicate = matching_legacy_direct_authority_event(
            current_events,
            provenance=provenance,
            authorization=current_authorization,
        )
        if duplicate is not None:
            print(
                json.dumps(
                    {
                        "duplicate": True,
                        "record_id": duplicate["record_id"],
                        "record_sha256": duplicate["record_sha256"],
                        "source_record": duplicate["source_record"],
                        "source_sha256": duplicate["source_sha256"],
                        "classification": projection["classification"],
                    },
                    sort_keys=True,
                )
            )
            return
        record["record_id"] = f"EVT-{len(current_events) + 1:06d}"
        previous = (
            str(current_events[-1]["record_sha256"])
            if current_events
            else None
        )
        appended_hash = append_raw_locked_at(
            directory_fd,
            "events.jsonl",
            record,
            previous_record_sha256=previous,
            expected_file_snapshot=current_event_snapshot,
            require_event_anchor=bool(current_events),
        )
        record["record_sha256"] = appended_hash
    print(
        json.dumps(
            {
                "duplicate": False,
                "record_id": record["record_id"],
                "record_sha256": record["record_sha256"],
                "source_record": provenance["source_item_id"],
                "source_sha256": provenance["source_sha256"],
                "classification": projection["classification"],
            },
            sort_keys=True,
        )
    )


def evidence_value(evidence: Any, prefix: str) -> str:
    matches = [
        item[len(prefix):]
        for item in evidence
        if isinstance(item, str) and item.startswith(prefix)
    ] if isinstance(evidence, list) else []
    if len(matches) != 1 or not matches[0]:
        raise SupervisionLogError(
            "Legacy direct-authority event evidence is incomplete"
        )
    return matches[0]


def legacy_terminal_range_compatibility_eligible(
    policy: Mapping[str, Any],
    *,
    all_events: list[dict[str, Any]],
    policy_history: list[dict[str, Any]],
    prior: Mapping[str, Any],
    record: Mapping[str, Any],
    contract: Mapping[str, Any],
    range_state: Mapping[str, Any],
) -> bool:
    """Admit only an exact canonical legacy transition's terminal retirement."""
    mission = bound_mission(dict(policy))
    authority = contract.get("authority")
    history = contract.get("history")
    if (
        record.get("phase") not in SUCCESSOR_TRANSITION_TERMINAL_PHASES
        or prior.get("phase") != "required"
        or record.get("transition_id") != prior.get("transition_id")
        or record.get("prior_record_id") != prior.get("record_id")
        or prior.get("governing_authority_source_class") != "direct-user"
        or prior.get("governing_authority_source_sha256")
        or prior.get("topology_posture")
        or prior.get("topology_basis")
        or prior.get("topology_decision_event_record_id")
        or prior.get("topology_decision_event_sha256")
        or not isinstance(mission, Mapping)
        or prior.get("source_mission_root") != mission.get("mission_root")
        or not isinstance(authority, Mapping)
        or not isinstance(history, list)
        or not history
        or contract.get("range_intent") != "full-tracker"
        or contract.get("explicit_blocks") != []
        or range_state.get("range_intent") != "full-tracker"
        or range_state.get("requested_blocks") != contract.get("tracker_blocks")
    ):
        return False
    source_record = str(authority.get("source_record", ""))
    source_sha256 = str(authority.get("source_sha256", ""))
    expected_authority = {
        "source_class": "direct-user",
        "source_record": source_record,
        "source_sha256": source_sha256,
    }
    expected_effect = (
        "continue-replacement-transition"
        if record.get("phase") == "superseded"
        else "continue-same-task"
    )
    genesis = history[0]
    if (
        dict(authority) != expected_authority
        or not isinstance(genesis, Mapping)
        or genesis.get("operation") != "bound"
        or genesis.get("authority") != expected_authority
        or genesis.get("range_intent") != "full-tracker"
        or genesis.get("request_text_sha256") != source_sha256
        or prior.get("governing_authority_source_record") != source_record
        or record.get("governing_authority_source_class") != "direct-user"
        or record.get("governing_authority_source_record") != source_record
        or record.get("governing_authority_source_sha256") != source_sha256
        or record.get("correction_authority_source_class") != "direct-user"
        or record.get("correction_authority_source_record") != source_record
        or record.get("correction_authority_source_sha256") != source_sha256
        or record.get("governing_outcome_effect") != expected_effect
    ):
        return False
    receipts = [
        item
        for item in policy.get("direct_authority_receipts", [])
        if isinstance(item, Mapping)
        and item.get("accepted") is True
        and item.get("source_class") == "direct-user"
        and item.get("source_record") == source_record
        and item.get("source_sha256") == source_sha256
    ]
    if len(receipts) != 1:
        return False
    receipt = receipts[0]
    accepted_version = receipt.get("accepted_policy_version")
    authority_version = genesis.get("authority_policy_version")
    if (
        type(accepted_version) is not int
        or type(authority_version) is not int
        or accepted_version >= authority_version
        or authority_version > policy.get("policy_version", 0)
    ):
        return False
    try:
        source_event = canonical_direct_authority_event(
            all_events,
            event_record_id=str(receipt["source_event_record_id"]),
            policy=policy,
            policy_history=policy_history,
        )
        evidence = source_event["evidence"]
        authorization_value = evidence_value(evidence, "authorization-record:")
        authorization_record_id, separator, authorization_sha256 = (
            authorization_value.partition(":")
        )
        if not separator:
            return False
        provenance = {
            "source_task_id": evidence_value(evidence, "source-task:"),
            "source_turn_id": evidence_value(evidence, "source-turn:"),
            "source_item_id": evidence_value(evidence, "source-item:"),
            "source_byte_count": int(evidence_value(evidence, "source-byte-count:")),
            "source_sha256": evidence_value(evidence, "source-sha256:"),
            "policy_sha256": source_event["policy_sha256"],
            "verifier_id": source_event["verifier_id"],
            "authorization_record_id": authorization_record_id,
            "legacy_transition_record_id": evidence_value(
                evidence, "legacy-transition-record:"
            ),
            "legacy_transition_id": evidence_value(
                evidence, "legacy-transition-id:"
            ),
        }
        authorization = canonical_legacy_direct_authority_review(
            all_events, provenance=provenance, policy=policy
        )
        transition = canonical_legacy_successor_transition(
            all_events,
            provenance=provenance,
            policy=policy,
            policy_history=policy_history,
            require_open=True,
        )
        event_order = {
            str(item.get("record_id")): index
            for index, item in enumerate(all_events)
        }
        classification = evidence_value(evidence, "classification:")
    except (KeyError, StopIteration, SupervisionLogError, TypeError, ValueError):
        return False
    return bool(
        classification == LEGACY_DIRECT_AUTHORITY_CLASSIFICATION
        and source_event.get("source_record") == source_record
        and source_event.get("source_item_id") == source_record
        and source_event.get("source_task_id") == policy.get("target_thread_id")
        and source_event.get("source_sha256") == source_sha256
        and source_event.get("record_sha256") == receipt.get("source_event_sha256")
        and source_event.get("verifier_id") == receipt.get("reviewer_id")
        and authorization.get("record_sha256") == authorization_sha256
        and transition.get("record_id") == prior.get("record_id")
        and event_order[str(transition["record_id"])]
        < event_order[str(authorization["record_id"])]
        < event_order[str(source_event["record_id"])]
    )


def legacy_implementation_request_classification_from_state(
    policy: Mapping[str, Any],
    *,
    all_events: list[dict[str, Any]],
    policy_history: list[dict[str, Any]],
    source_record: str,
    source_sha256: str,
    request_text: str,
    blocks: set[int],
) -> tuple[str, list[int]]:
    receipt = next(
        (
            item
            for item in policy.get("direct_authority_receipts", [])
            if item.get("source_record") == source_record
            and item.get("source_sha256") == source_sha256
            and item.get("accepted") is True
        ),
        None,
    )
    if receipt is None or receipt.get("accepted_policy_version") != policy.get(
        "policy_version"
    ):
        raise SupervisionLogError(
            "Legacy implementation request lacks a current accepted authority receipt"
        )
    source_event = canonical_direct_authority_event(
        all_events,
        event_record_id=str(receipt["source_event_record_id"]),
        policy=policy,
        policy_history=policy_history,
    )
    evidence = source_event["evidence"]
    if evidence_value(evidence, "classification:") != (
        LEGACY_DIRECT_AUTHORITY_CLASSIFICATION
    ):
        raise SupervisionLogError(
            "Direct-authority event is not eligible for legacy request classification"
        )
    source_turn_id = safe_id(
        evidence_value(evidence, "source-turn:"),
        label="legacy authority source turn",
    )
    source_byte_count_value = evidence_value(evidence, "source-byte-count:")
    if not source_byte_count_value.isdigit():
        raise SupervisionLogError(
            "Legacy direct-authority source byte count is invalid"
        )
    authorization_value = evidence_value(evidence, "authorization-record:")
    authorization_record_id, separator, authorization_sha256 = (
        authorization_value.partition(":")
    )
    if not separator:
        raise SupervisionLogError(
            "Legacy direct-authority authorization evidence differs"
        )
    exact_sha256(
        authorization_sha256,
        label="legacy authority review record SHA-256",
    )
    provenance = {
        "schema_version": 1,
        "kind": LEGACY_DIRECT_AUTHORITY_PROVENANCE_KIND,
        "target_thread_id": policy["target_thread_id"],
        "source_task_id": evidence_value(evidence, "source-task:"),
        "source_turn_id": source_turn_id,
        "source_item_id": evidence_value(evidence, "source-item:"),
        "source_text": request_text,
        "source_byte_count": int(source_byte_count_value),
        "source_sha256": source_sha256,
        "policy_version": next(
            int(item["policy"]["policy_version"])
            for item in policy_history
            if isinstance(item.get("policy"), Mapping)
            and item["policy"].get("policy_sha256")
            == source_event["policy_sha256"]
        ),
        "policy_sha256": source_event["policy_sha256"],
        "verifier_id": source_event["verifier_id"],
        "authorization_record_id": authorization_record_id,
        "legacy_transition_record_id": evidence_value(
            evidence, "legacy-transition-record:"
        ),
        "legacy_transition_id": evidence_value(
            evidence, "legacy-transition-id:"
        ),
    }
    projection, authorization, _transition = (
        validate_legacy_direct_authority_provenance(
            provenance,
            policy=policy,
            policy_history=policy_history,
            all_events=all_events,
            require_current_policy=False,
            require_open_transition=True,
        )
    )
    if (
        authorization.get("record_sha256") != authorization_sha256
        or source_event.get("source_task_id") != provenance["source_task_id"]
        or source_event.get("source_item_id") != provenance["source_item_id"]
        or source_event.get("source_record") != provenance["source_item_id"]
        or hashlib.sha256(request_text.encode("utf-8")).hexdigest()
        != source_sha256
        or projection.get("range_intent") != "full-tracker"
    ):
        raise SupervisionLogError(
            "Legacy implementation request differs from canonical authority"
        )
    return "full-tracker", sorted(blocks)


def legacy_implementation_request_classification(
    directory: Path,
    policy: Mapping[str, Any],
    *,
    source_record: str,
    source_sha256: str,
    request_text: str,
    blocks: set[int],
) -> tuple[str, list[int], str]:
    all_events = events(directory / "events.jsonl")
    policy_history = events(directory / "policy-history.jsonl")
    intent, requested = legacy_implementation_request_classification_from_state(
        policy,
        all_events=all_events,
        policy_history=policy_history,
        source_record=source_record,
        source_sha256=source_sha256,
        request_text=request_text,
        blocks=blocks,
    )
    if not all_events:
        raise SupervisionLogError(
            "Legacy implementation authority event ledger is empty"
        )
    return intent, requested, str(all_events[-1]["record_sha256"])


def cmd_implementation_authority_receipt(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    policy_history = events(directory / "policy-history.jsonl")
    source_event = canonical_direct_authority_event(
        events(directory / "events.jsonl"),
        event_record_id=safe_id(
            args.authority_event_record,
            label="canonical direct-authority event record",
        ),
        policy=policy,
        policy_history=policy_history,
    )
    source_record = str(source_event["source_record"])
    source_sha256 = str(source_event["source_sha256"])
    receipts = policy.setdefault("direct_authority_receipts", [])
    if any(
        item.get("source_record") == source_record
        and item.get("source_sha256") == source_sha256
        for item in receipts
    ):
        print(json.dumps({"duplicate": True, "source_record": source_record}, sort_keys=True))
        return
    receipt = {
        "source_class": "direct-user",
        "source_record": source_record,
        "source_sha256": source_sha256,
        "reviewer_id": source_event["verifier_id"],
        "source_event_record_id": source_event["record_id"],
        "source_event_sha256": source_event["record_sha256"],
        "source_task_id": source_event["source_task_id"],
        "source_item_id": source_event["source_item_id"],
        "source_policy_sha256": source_event["policy_sha256"],
        "accepted": True,
        "accepted_policy_version": int(policy["policy_version"]) + 1,
        "evidence": source_event["evidence"],
    }
    receipts.append(receipt)
    write_policy_version(
        directory,
        policy,
        kind="implementation-range-authority-receipt",
        reason="Resolved a separately ingested canonical direct-user authority event.",
        evidence_values=[
            str(source_event["record_id"]),
            str(source_event["record_sha256"]),
        ],
    )
    print(json.dumps({"duplicate": False, "receipt": receipt}, sort_keys=True))


def implementation_range_history_entry(
    *,
    sequence: int,
    prior_entry_sha256: str,
    operation: str,
    request_text: str,
    tracker_sha256: str,
    tracker_structure_sha256: str,
    tracker_path: str,
    tracker_blocks: list[int],
    range_intent: str,
    explicit_blocks: list[int],
    authority: Mapping[str, Any],
    authority_policy_version: int,
    amendment_map_sha256: str = "",
    amendment_event_record_id: str = "",
    amendment_event_sha256: str = "",
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "sequence": sequence,
        "prior_entry_sha256": prior_entry_sha256,
        "operation": operation,
        "request_text_sha256": hashlib.sha256(request_text.encode("utf-8")).hexdigest(),
        "tracker_sha256": tracker_sha256,
        "tracker_structure_sha256": tracker_structure_sha256,
        "tracker_path": tracker_path,
        "tracker_blocks": tracker_blocks,
        "range_intent": range_intent,
        "explicit_blocks": explicit_blocks,
        "authority": dict(authority),
        "authority_policy_version": authority_policy_version,
        "amendment_map_sha256": amendment_map_sha256,
        "amendment_event_record_id": amendment_event_record_id,
        "amendment_event_sha256": amendment_event_sha256,
    }
    entry["entry_sha256"] = digest(entry)
    return entry


def cmd_implementation_range_bind(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    if implementation_range_contract(policy) is not None:
        raise SupervisionLogError("Implementation range is already bound")
    source_record = safe_id(
        args.authority_source_record, label="range authority source record"
    )
    source_sha256 = exact_sha256(
        args.authority_source_sha256, label="range authority source SHA-256"
    )
    if hashlib.sha256(args.request_text.encode("utf-8")).hexdigest() != source_sha256:
        raise SupervisionLogError(
            "Implementation request text does not match its canonical direct source"
        )
    if not eligible_direct_authority(policy, source_record, source_sha256):
        raise SupervisionLogError(
            "Implementation range source is not canonical eligible direct authority"
        )
    (
        tracker_path,
        tracker_sha256,
        tracker_structure_sha256,
        blocks,
    ) = implementation_tracker_snapshot(args.tracker)
    legacy_event_head_sha256 = ""
    if (
        "/Users/" in args.request_text
        or "file://" in args.request_text
        or "\\Users\\" in args.request_text
    ):
        (
            intent,
            requested,
            legacy_event_head_sha256,
        ) = legacy_implementation_request_classification(
            directory,
            policy,
            source_record=source_record,
            source_sha256=source_sha256,
            request_text=args.request_text,
            blocks=set(blocks),
        )
    else:
        intent, requested = classify_implementation_request(
            args.request_text, set(blocks)
        )
    authority = {
        "source_class": "direct-user",
        "source_record": source_record,
        "source_sha256": source_sha256,
    }
    range_id = safe_id(args.range_id, label="implementation range ID")
    explicit = requested if intent == "explicit-blocks" else []
    entry = implementation_range_history_entry(
        sequence=1,
        prior_entry_sha256="",
        operation="bound",
        request_text=args.request_text,
        tracker_sha256=tracker_sha256,
        tracker_structure_sha256=tracker_structure_sha256,
        tracker_path=str(tracker_path),
        tracker_blocks=sorted(blocks),
        range_intent=intent,
        explicit_blocks=explicit,
        authority=authority,
        authority_policy_version=int(policy["policy_version"]) + 1,
    )
    genesis = digest(
        {
            "range_id": range_id,
            "authority": authority,
            "request_text_sha256": entry["request_text_sha256"],
            "initial_tracker_sha256": tracker_sha256,
            "initial_tracker_structure_sha256": tracker_structure_sha256,
            "initial_tracker_blocks": sorted(blocks),
            "initial_range_intent": intent,
            "initial_explicit_blocks": explicit,
        }
    )
    policy["implementation_range"] = {
        "schema_version": 1,
        "kind": "implementation-range-binding",
        "range_id": range_id,
        "genesis_sha256": genesis,
        "authority": authority,
        "range_intent": intent,
        "explicit_blocks": explicit,
        "tracker_path": str(tracker_path),
        "tracker_sha256": tracker_sha256,
        "tracker_structure_sha256": tracker_structure_sha256,
        "tracker_blocks": sorted(blocks),
        "history": [entry],
        "history_head_sha256": entry["entry_sha256"],
    }
    validate_implementation_range_contract(policy["implementation_range"])

    def revalidate_legacy_binding_before_mutation(
        directory_fd: int, current_policy: Mapping[str, Any]
    ) -> None:
        current_events, _event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        current_policy_history, _history_snapshot = events_snapshot(
            Path("policy-history.jsonl"), directory_fd=directory_fd
        )
        validate_event_ledger_anchor_at(
            directory_fd,
            current_events,
            allow_missing=False,
        )
        current_event_head = (
            str(current_events[-1].get("record_sha256", ""))
            if current_events
            else ""
        )
        if current_event_head != legacy_event_head_sha256:
            raise SupervisionLogError(
                "Legacy implementation authority event state changed before range bind"
            )
        locked_intent, locked_requested = (
            legacy_implementation_request_classification_from_state(
                current_policy,
                all_events=current_events,
                policy_history=current_policy_history,
                source_record=source_record,
                source_sha256=source_sha256,
                request_text=args.request_text,
                blocks=set(blocks),
            )
        )
        if locked_intent != intent or locked_requested != requested:
            raise SupervisionLogError(
                "Legacy implementation authority changed before range bind"
            )

    write_policy_version(
        directory,
        policy,
        kind="implementation-range-bind",
        reason="Freeze the direct requested implementation range.",
        evidence_values=[source_record, tracker_sha256, genesis],
        pre_mutation_validator=(
            revalidate_legacy_binding_before_mutation
            if legacy_event_head_sha256
            else None
        ),
    )
    print(json.dumps({"binding": policy["implementation_range"]}, sort_keys=True))


def cmd_implementation_range_amend(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    contract = implementation_range_contract(policy)
    if contract is None:
        raise SupervisionLogError("Implementation range is not bound")
    validate_implementation_range_contract(contract)
    (
        tracker_path,
        tracker_sha256,
        tracker_structure_sha256,
        blocks,
    ) = implementation_tracker_snapshot(args.tracker)
    old_intent = str(contract["range_intent"])
    old_explicit = list(contract["explicit_blocks"])
    old_blocks = list(contract["tracker_blocks"])
    new_blocks = sorted(blocks)
    structural_change = bool(
        str(tracker_path) != contract["tracker_path"]
        or new_blocks != old_blocks
        or tracker_structure_sha256 != contract["tracker_structure_sha256"]
    )
    amendment_event: dict[str, Any] | None = None
    block_number_map = {str(item): item for item in old_blocks}
    if structural_change:
        event_record_id = safe_id(
            args.amendment_event_record,
            label="canonical tracker-amendment event record",
        )
        _owner_directory, owner_fd, _owner_snapshot = open_member_directory(
            root_from(args), args.target_thread
        )
        try:
            all_events, _events_snapshot = events_snapshot(
                Path("events.jsonl"), directory_fd=owner_fd
            )
            policy_history, _history_snapshot = events_snapshot(
                Path("policy-history.jsonl"), directory_fd=owner_fd
            )
        finally:
            os.close(owner_fd)
        amendment_event = canonical_tracker_amendment_event(
            all_events,
            event_record_id=event_record_id,
            policy=policy,
            policy_history=policy_history,
        )
        comparisons = {
            "old_tracker_path": contract["tracker_path"],
            "old_tracker_sha256": contract["tracker_sha256"],
            "old_tracker_structure_sha256": contract[
                "tracker_structure_sha256"
            ],
            "old_blocks": old_blocks,
            "new_tracker_path": str(tracker_path),
            "new_tracker_sha256": tracker_sha256,
            "new_tracker_structure_sha256": tracker_structure_sha256,
            "new_blocks": new_blocks,
        }
        if any(amendment_event.get(field) != expected for field, expected in comparisons.items()):
            raise SupervisionLogError(
                "Canonical tracker-amendment event does not match the exact transition"
            )
        block_number_map = dict(amendment_event["block_number_map"])
    elif args.amendment_event_record:
        raise SupervisionLogError(
            "A status-only tracker update must not invent a structural amendment"
        )
    if args.request_text:
        new_intent, requested = classify_implementation_request(
            args.request_text, set(blocks)
        )
        new_explicit = requested if new_intent == "explicit-blocks" else []
    else:
        new_intent = old_intent
        new_explicit = (
            [block_number_map[str(item)] for item in old_explicit]
            if structural_change
            else old_explicit
        )
    contraction = bool(
        old_intent == "full-tracker" and new_intent != "full-tracker"
        or old_intent == "explicit-blocks"
        and new_intent == "explicit-blocks"
        and not set(old_explicit).issubset(new_explicit)
    )
    history = list(contract["history"])
    authority = dict(contract["authority"])
    if contraction:
        source_record = safe_id(
            args.authority_source_record,
            label="range-change authority source record",
        )
        source_sha256 = exact_sha256(
            args.authority_source_sha256,
            label="range-change authority source SHA-256",
        )
        if (
            source_record == contract["authority"]["source_record"]
            or not eligible_direct_authority(policy, source_record, source_sha256)
        ):
            raise SupervisionLogError(
                "Range contraction lacks a newer canonical direct-user authority event"
            )
        if hashlib.sha256(args.request_text.encode("utf-8")).hexdigest() != source_sha256:
            raise SupervisionLogError(
                "Range contraction text does not match its canonical direct source"
            )
        matching_receipt = next(
            (
                item
                for item in policy.get("direct_authority_receipts", [])
                if item.get("source_record") == source_record
                and item.get("source_sha256") == source_sha256
                and item.get("accepted") is True
            ),
            None,
        )
        minimum_authority_version = max(
            int(item.get("authority_policy_version", 0)) for item in history
        )
        if (
            matching_receipt is None
            or int(matching_receipt.get("accepted_policy_version", 0))
            <= minimum_authority_version
        ):
            raise SupervisionLogError(
                "Range contraction authority is not newer than the frozen range"
            )
        authority = {
            "source_class": "direct-user",
            "source_record": source_record,
            "source_sha256": source_sha256,
        }
        authority_policy_version = int(matching_receipt["accepted_policy_version"])
    else:
        authority_policy_version = int(
            contract["history"][-1].get("authority_policy_version", 0)
        )
    amendment_map = (
        digest(block_number_map) if amendment_event is not None else ""
    )
    entry = implementation_range_history_entry(
        sequence=len(history) + 1,
        prior_entry_sha256=str(contract["history_head_sha256"]),
        operation="contracted" if contraction else "tracker-amended",
        request_text=args.request_text or "preserve-frozen-range-intent",
        tracker_sha256=tracker_sha256,
        tracker_structure_sha256=tracker_structure_sha256,
        tracker_path=str(tracker_path),
        tracker_blocks=new_blocks,
        range_intent=new_intent,
        explicit_blocks=new_explicit,
        authority=authority,
        authority_policy_version=authority_policy_version,
        amendment_map_sha256=amendment_map,
        amendment_event_record_id=(
            str(amendment_event["record_id"]) if amendment_event is not None else ""
        ),
        amendment_event_sha256=(
            str(amendment_event["record_sha256"]) if amendment_event is not None else ""
        ),
    )
    history.append(entry)
    contract.update(
        {
            "authority": authority,
            "range_intent": new_intent,
            "explicit_blocks": new_explicit,
            "tracker_path": str(tracker_path),
            "tracker_sha256": tracker_sha256,
            "tracker_structure_sha256": tracker_structure_sha256,
            "tracker_blocks": new_blocks,
            "history": history,
            "history_head_sha256": entry["entry_sha256"],
        }
    )
    validate_implementation_range_contract(contract)
    policy["implementation_range"] = contract
    write_policy_version(
        directory,
        policy,
        kind="implementation-range-amend",
        reason="Advance the canonical tracker identity without losing direct range intent.",
        evidence_values=[tracker_sha256, entry["entry_sha256"], *( [amendment_map] if amendment_map else [])],
    )
    print(json.dumps({"binding": contract, "contraction": contraction}, sort_keys=True))


def implementation_range_repair_result(
    *,
    response_kind: str,
    policy: Mapping[str, Any],
    control: Mapping[str, Any],
    posture: str,
    cause: str,
) -> dict[str, Any]:
    effective_control = dict(control)
    effective_control["required_target_posture"] = "in-progress"
    effective_control["next_action"] = (
        "continue-local-safe-frontier-and-repair-binding"
    )
    return {
        "range_binding_current": False,
        "range_binding_posture": posture,
        "response_kind": response_kind,
        "final_response_permitted": False,
        "required_target_posture": "in-progress",
        "next_action": "continue-local-safe-frontier-and-repair-binding",
        "failure_mode_if_returned": "FM-UNAUTHORIZED-EARLY-RETURN",
        "severity_if_returned": "critical",
        "process_boundary_implies_completion": False,
        "manual_resume_required": False,
        "human_input_required": False,
        "suppression_cause": cause,
        "control_posture": effective_control,
        "governing_outcome_currentness_sha256": control[
            "governing_outcome_currentness_sha256"
        ],
        "policy_sha256": policy["policy_sha256"],
    }


def skill_release_publication_projection(
    *, publication_status: str, publication_retry_trigger: str = ""
) -> dict[str, Any]:
    """Separate remote durability from the independently owned local release lane."""

    if publication_status not in SKILL_RELEASE_PUBLICATION_STATUSES:
        raise SupervisionLogError("Skill release publication status is invalid")
    retry_trigger = clean(
        publication_retry_trigger,
        label="publication retry trigger",
        maximum=240,
    )
    durability_pending = publication_status != "published"
    if durability_pending and not retry_trigger:
        raise SupervisionLogError(
            "Durability-pending release requires an autonomous publication retry trigger"
        )
    if not durability_pending and retry_trigger:
        raise SupervisionLogError(
            "Published release must not carry a pending publication retry trigger"
        )
    return {
        "publication_status": publication_status,
        "durability_state": (
            "durability-pending" if durability_pending else "remote-durable"
        ),
        "durability_pending": durability_pending,
        "remote_durability_claim_permitted": not durability_pending,
        "publication_retry_required": durability_pending,
        "publication_retry_trigger_sha256": (
            digest(retry_trigger) if durability_pending else None
        ),
        "signed_local_release_owner_required": True,
        "signed_local_stage_publication_eligible": True,
        "signed_local_activation_publication_eligible": True,
        "post_activation_role_refresh_publication_eligible": True,
        "local_effectiveness_publication_eligible": True,
        "final_response_effect": "none",
        "required_target_posture_effect": "none",
        "publication_blocks_only": "remote-durability-claim",
        "manual_resume_required": False,
        "human_input_required": False,
    }


def cmd_skill_release_publication_gate(args: argparse.Namespace) -> None:
    _directory, policy = load_policy(args)
    projection = skill_release_publication_projection(
        publication_status=args.publication_status,
        publication_retry_trigger=args.publication_retry_trigger,
    )
    print(
        json.dumps(
            {
                "target_thread_id": policy["target_thread_id"],
                **projection,
                "policy_sha256": policy["policy_sha256"],
            },
            sort_keys=True,
        )
    )


def cmd_implementation_range_gate(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        owner_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    control = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=owner_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
    try:
        state = implementation_range_state(policy)
    except SupervisionLogError as exc:
        repairable_noncurrent_messages = (
            "Implementation tracker changed without an accepted range amendment",
            "Implementation tracker structure changed without an accepted amendment",
            "Bound explicit Blocks require an exact accepted renumbering map",
        )
        if not str(exc).startswith(repairable_noncurrent_messages):
            raise
        result = implementation_range_repair_result(
            response_kind=args.response_kind,
            policy=policy,
            control=control,
            posture="noncurrent",
            cause=str(exc),
        )
        print(json.dumps(result, sort_keys=True))
        return
    if state is None:
        result = implementation_range_repair_result(
            response_kind=args.response_kind,
            policy=policy,
            control=control,
            posture="absent",
            cause="Implementation range is not canonically bound",
        )
        print(json.dumps(result, sort_keys=True))
        return
    remaining = state["remaining_blocks"]
    if remaining:
        next_action = (
            "continue-next-eligible-block"
            if state["eligible_blocks"]
            else "reconcile-unmet-dependencies-without-final-response"
        )
        final_permitted = False
    elif (
        state["range_intent"] == "explicit-blocks"
        and len(state["requested_blocks"]) == 1
        and args.response_kind in {"block-boundary", "final-response"}
    ):
        next_action = (
            "requested-block-boundary-satisfied"
            if args.response_kind == "block-boundary"
            else "requested-range-final-response-satisfied"
        )
        final_permitted = True
    elif control["required_target_posture"] in {"completed", "stopped"}:
        next_action = "governing-outcome-terminal-current"
        final_permitted = True
    else:
        next_action = control["next_action"]
        final_permitted = False
    effective_control = dict(control)
    if not final_permitted:
        effective_control["required_target_posture"] = "in-progress"
        effective_control["next_action"] = next_action
    result = {
        **state,
        "range_binding_current": True,
        "range_binding_posture": "current",
        "response_kind": args.response_kind,
        "final_response_permitted": final_permitted,
        "required_target_posture": effective_control[
            "required_target_posture"
        ],
        "next_action": next_action,
        "failure_mode_if_returned": (
            None if final_permitted else "FM-UNAUTHORIZED-EARLY-RETURN"
        ),
        "severity_if_returned": None if final_permitted else "critical",
        "process_boundary_implies_completion": False,
        "manual_resume_required": False,
        "human_input_required": False,
        "control_posture": effective_control,
        "governing_outcome_currentness_sha256": control[
            "governing_outcome_currentness_sha256"
        ],
        "policy_sha256": policy["policy_sha256"],
    }
    print(json.dumps(result, sort_keys=True))


def validate_successor_transition(
    prior: dict[str, Any] | None,
    record: dict[str, Any],
    all_events: list[dict[str, Any]],
) -> None:
    phase = str(record["phase"])
    topology_posture = str(record.get("topology_posture", ""))
    topology_basis = str(record.get("topology_basis", ""))
    topology_rationale = str(record.get("topology_rationale", ""))
    topology_event_record = str(
        record.get("topology_decision_event_record_id", "")
    )
    topology_event_sha256 = str(
        record.get("topology_decision_event_sha256", "")
    )
    topology_request_sha256 = str(record.get("topology_request_sha256", ""))
    if topology_posture not in SUCCESSOR_TOPOLOGY_POSTURES:
        raise SupervisionLogError("Successor transition topology is invalid")
    if topology_posture == "same-task-new-run":
        if (
            topology_basis != "same-task-default"
            or topology_request_sha256
            or topology_event_record
            or topology_event_sha256
        ):
            raise SupervisionLogError(
                "Same-task continuation requires the same-task default basis"
            )
    elif topology_basis == "direct-request":
        if (
            record.get("governing_authority_source_class") != "direct-user"
            or not topology_rationale
            or topology_request_sha256
            != record.get("governing_authority_source_sha256")
            or topology_event_record
            or topology_event_sha256
        ):
            raise SupervisionLogError(
                "Distinct-task direct-request topology requires canonical direct-user authority"
            )
    elif topology_basis == "technical-isolation":
        if (
            not topology_rationale
            or topology_request_sha256
            or not topology_event_record
            or not topology_event_sha256
        ):
            raise SupervisionLogError(
                "Technical-isolation topology requires a canonical decision event"
            )
    elif topology_basis == "legacy-linear":
        if prior is None:
            raise SupervisionLogError(
                "Legacy-linear topology is migration-only"
            )
    else:
        raise SupervisionLogError(
            "Distinct-task topology requires canonical direct request or technical isolation"
        )
    if record.get("successor_thread_id") == record.get("target_thread_id"):
        raise SupervisionLogError("A task cannot be its own successor")

    if prior is None:
        if phase != "required":
            raise SupervisionLogError("A successor transition must begin required")
        if any(
            record.get(field)
            for field in (
                "prior_record_id",
                "disposition_reason",
                "correction_authority_source_class",
                "correction_authority_source_record",
                "correction_authority_source_sha256",
                "replacement_transition_id",
                "governing_outcome_effect",
            )
        ):
            raise SupervisionLogError(
                "An initial transition cannot claim a correction disposition"
            )
        if any(
            record.get(field)
            for field in (
                "successor_thread_id",
                "successor_mission_root",
                "successor_group_id",
                "handoff_record",
                "acknowledgement_record",
                "started_block",
            )
        ):
            raise SupervisionLogError(
                "required cannot claim later successor evidence"
            )
        expires_at = str(record.get("transition_expires_at", ""))
        if expires_at:
            created = parse_time(str(record["timestamp"]))
            expiry = parse_time(expires_at)
            if expiry <= created or expiry - created > dt.timedelta(
                hours=MAX_SUCCESSOR_TRANSITION_HOURS
            ):
                raise SupervisionLogError(
                    "Transition expiry must be future and bounded to 24 hours"
                )
        replaced_id = str(record.get("replaces_transition_id", ""))
        if replaced_id:
            if replaced_id == record["transition_id"]:
                raise SupervisionLogError("A transition cannot replace itself")
            replaced = transition_first_record(all_events, replaced_id)
            if replaced is None:
                raise SupervisionLogError(
                    "A replacement transition requires its exact predecessor"
                )
            replaced_records = successor_transition_events(all_events, replaced_id)
            if replaced_records[-1].get("phase") in SUCCESSOR_TRANSITION_CLOSED_PHASES:
                raise SupervisionLogError(
                    "A replacement transition requires an open predecessor"
                )
            if any(
                item.get("kind") == "successor-transition"
                and item.get("replaces_transition_id") == replaced_id
                for item in all_events
            ):
                raise SupervisionLogError(
                    "A transition already has a declared replacement"
                )
            cursor = replaced
            seen = {str(record["transition_id"])}
            while cursor.get("replaces_transition_id"):
                cursor_id = str(cursor["replaces_transition_id"])
                if cursor_id in seen:
                    raise SupervisionLogError(
                        "Replacement transition chain is cyclic"
                    )
                seen.add(cursor_id)
                predecessor = transition_first_record(all_events, cursor_id)
                if predecessor is None:
                    raise SupervisionLogError(
                        "Replacement transition chain is incomplete"
                    )
                cursor = predecessor
        return

    prior_phase = str(prior.get("phase", ""))
    if prior_phase not in SUCCESSOR_TRANSITION_ALL_PHASES:
        raise SupervisionLogError("Prior successor transition phase is invalid")
    if prior_phase in SUCCESSOR_TRANSITION_CLOSED_PHASES:
        raise SupervisionLogError("A closed successor transition cannot advance")
    for field in SUCCESSOR_TRANSITION_IDENTITY_FIELDS:
        if prior.get(field, "") != record.get(field, ""):
            raise SupervisionLogError(
                f"Successor transition must preserve {field.replace('_', ' ')}"
            )

    if phase in SUCCESSOR_TRANSITION_TERMINAL_PHASES:
        if record.get("prior_record_id") != prior.get("record_id"):
            raise SupervisionLogError(
                "A transition disposition requires the exact current prior record"
            )
        if not record.get("disposition_reason"):
            raise SupervisionLogError("A transition disposition requires a reason")
        if (
            record.get("correction_authority_source_class")
            not in DIRECT_AUTHORITY_SOURCE_CLASSES
            or not record.get("correction_authority_source_record")
            or SHA256.fullmatch(
                str(record.get("correction_authority_source_sha256", ""))
            )
            is None
        ):
            raise SupervisionLogError(
                "A transition disposition requires current direct authority"
            )
        effect = record.get("governing_outcome_effect")
        if effect not in SUCCESSOR_GOVERNING_OUTCOME_EFFECTS:
            raise SupervisionLogError(
                "A transition disposition requires its governing-outcome effect"
            )
        replacement_id = str(record.get("replacement_transition_id", ""))
        if phase == "superseded":
            if effect != "continue-replacement-transition" or not replacement_id:
                raise SupervisionLogError(
                    "Supersession requires one replacement transition"
                )
            if replacement_id == record["transition_id"]:
                raise SupervisionLogError("A transition cannot supersede itself")
            replacement_records = successor_transition_events(
                all_events, replacement_id
            )
            if not replacement_records:
                raise SupervisionLogError(
                    "Supersession replacement transition does not exist"
                )
            replacement = replacement_records[-1]
            if replacement.get("replaces_transition_id") != record["transition_id"]:
                raise SupervisionLogError(
                    "Replacement transition lacks the exact supersession link"
                )
            if replacement.get("phase") in SUCCESSOR_TRANSITION_CLOSED_PHASES:
                raise SupervisionLogError(
                    "A closed transition cannot become the replacement"
                )
            old_first = transition_first_record(
                all_events, str(record["transition_id"])
            )
            replacement_first = replacement_records[0]
            if old_first is None or all_events.index(replacement_first) <= all_events.index(
                old_first
            ):
                raise SupervisionLogError(
                    "Replacement transition cannot point backward"
                )
        elif replacement_id:
            raise SupervisionLogError(
                "Only a supersession may name a replacement transition"
            )
        elif effect != "continue-same-task":
            raise SupervisionLogError(
                "Correction, cancellation, and expiry continue in the source task"
            )
        if phase == "expired":
            expires_at = str(record.get("transition_expires_at", ""))
            if not expires_at or parse_time(str(record["timestamp"])) < parse_time(
                expires_at
            ):
                raise SupervisionLogError(
                    "A transition cannot expire before its declared bounded event"
                )
        return

    if phase not in SUCCESSOR_TRANSITION_PHASES:
        raise SupervisionLogError("Successor transition phase is invalid")
    if any(
        record.get(field)
        for field in (
            "prior_record_id",
            "disposition_reason",
            "correction_authority_source_class",
            "correction_authority_source_record",
            "correction_authority_source_sha256",
            "replacement_transition_id",
            "governing_outcome_effect",
        )
    ):
        raise SupervisionLogError(
            "Correction disposition fields are valid only on terminal dispositions"
        )
    phase_index = SUCCESSOR_TRANSITION_PHASES.index(phase)
    prior_index = SUCCESSOR_TRANSITION_PHASES.index(prior_phase)
    if topology_posture == "same-task-new-run":
        if not (prior_phase == "required" and phase == "work-started"):
            raise SupervisionLogError(
                "Same-task continuation must move directly from required to work-started"
            )
    else:
        if phase_index != prior_index + 1:
            raise SupervisionLogError(
                f"Successor transition {prior_phase} -> {phase} is not allowed"
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
            "started_block",
        ),
    }
    if topology_posture == "distinct-task":
        required_by_phase["work-started"] = (
            "successor_thread_id",
            "successor_mission_root",
            "successor_group_id",
            "handoff_record",
            "acknowledgement_record",
            "started_block",
        )
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
    (
        directory,
        policy,
        policy_snapshot,
        loaded_events,
        loaded_event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    if policy.get("owner_root_history_required") is not True:
        policy["owner_root_history_required"] = True
        write_policy_version(
            directory,
            policy,
            kind="owner-root-history-migration",
            reason=(
                "Lazily bind a legacy supervision owner to canonical policy/event roots."
            ),
            evidence_values=[
                "legacy-owner-root-migration",
                str(policy["policy_sha256"]),
            ],
        )
        (
            directory,
            policy,
            policy_snapshot,
            loaded_events,
            loaded_event_snapshot,
            directory_snapshot,
        ) = load_control_snapshot(args)
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
    authority_source_sha256 = exact_sha256(
        args.governing_authority_source_sha256,
        label="governing authority source SHA-256",
    )
    if not canonical_authority_source(
        policy,
        source_class=authority_source_class,
        source_record=authority_source_record,
        source_sha256=authority_source_sha256,
    ):
        raise SupervisionLogError(
            "Successor transition governing authority is not canonical"
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
    topology_posture = clean(
        args.topology_posture, label="topology posture", maximum=40
    )
    topology_basis = clean(
        args.topology_basis, label="topology basis", maximum=40
    )
    topology_rationale = clean(
        args.topology_rationale, label="topology rationale", maximum=300
    )
    topology_decision_event_record_id = clean(
        args.topology_decision_event_record,
        label="topology decision event record",
        maximum=128,
    )
    if topology_decision_event_record_id:
        safe_id(
            topology_decision_event_record_id,
            label="topology decision event record",
        )
    topology_request_text = clean(
        args.topology_request_text,
        label="topology direct request text",
        maximum=1200,
    )
    transition_expires_at = (
        parse_time(args.expires_at).isoformat() if args.expires_at else ""
    )
    replaces_transition_id = clean(
        args.replaces_transition,
        label="replaced transition ID",
        maximum=128,
    )
    prior_record_id = clean(
        args.prior_record, label="prior transition record", maximum=128
    )
    disposition_reason = clean(
        args.disposition_reason,
        label="transition disposition reason",
        maximum=500,
    )
    correction_authority_source_record = clean(
        args.correction_authority_source_record,
        label="correction authority source record",
        maximum=128,
    )
    correction_authority_source_sha256 = clean(
        args.correction_authority_source_sha256,
        label="correction authority source SHA-256",
        maximum=64,
    )
    if correction_authority_source_sha256:
        correction_authority_source_sha256 = exact_sha256(
            correction_authority_source_sha256,
            label="correction authority source SHA-256",
        )
    replacement_transition_id = clean(
        args.replacement_transition,
        label="replacement transition ID",
        maximum=128,
    )
    for label, value in (
        ("replaced transition ID", replaces_transition_id),
        ("prior transition record", prior_record_id),
        ("correction authority source record", correction_authority_source_record),
        ("replacement transition ID", replacement_transition_id),
    ):
        if value:
            safe_id(value, label=label)
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
        "governing_authority_source_sha256": authority_source_sha256,
        "topology_posture": topology_posture,
        "topology_basis": topology_basis,
        "topology_rationale": topology_rationale,
        "topology_request_sha256": "",
        "topology_decision_event_record_id": topology_decision_event_record_id,
        "topology_decision_event_sha256": "",
        "transition_expires_at": transition_expires_at,
        "replaces_transition_id": replaces_transition_id,
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
        "prior_record_id": prior_record_id,
        "disposition_reason": disposition_reason,
        "correction_authority_source_class": (
            args.correction_authority_source_class or ""
        ),
        "correction_authority_source_record": (
            correction_authority_source_record
        ),
        "correction_authority_source_sha256": (
            correction_authority_source_sha256
        ),
        "replacement_transition_id": replacement_transition_id,
        "governing_outcome_effect": args.governing_outcome_effect or "",
        "evidence": evidence_values,
        "policy_sha256": policy["policy_sha256"],
    }
    range_state = implementation_range_state(policy)
    if record["phase"] in SUCCESSOR_TRANSITION_TERMINAL_PHASES and not canonical_authority_source(
        policy,
        source_class=str(record["correction_authority_source_class"]),
        source_record=str(record["correction_authority_source_record"]),
        source_sha256=str(record["correction_authority_source_sha256"]),
    ):
        raise SupervisionLogError(
            "Successor transition correction authority is not canonical"
        )
    if topology_basis == "direct-request":
        request_sha256 = hashlib.sha256(
            topology_request_text.encode("utf-8")
        ).hexdigest()
        if request_sha256 != authority_source_sha256:
            raise SupervisionLogError(
                "Distinct-task request text does not match its canonical direct source"
            )
        if not direct_request_requires_distinct_task(topology_request_text):
            raise SupervisionLogError(
                "Canonical direct request does not explicitly require a distinct task"
            )
        record["topology_request_sha256"] = request_sha256
    elif topology_request_text:
        raise SupervisionLogError(
            "Topology request text is valid only for a direct-request basis"
        )
    with owner_append_lock(
        root_from(args), args.target_thread, directory_snapshot
    ) as directory_fd:
        current_policy, current_policy_snapshot = read_json_snapshot(
            Path("policy.json"), directory_fd=directory_fd
        )
        validate_policy(current_policy)
        validate_range_policy_history_at(directory_fd, current_policy)
        if (
            current_policy_snapshot != policy_snapshot
            or current_policy.get("policy_sha256") != policy.get("policy_sha256")
        ):
            raise SupervisionLogError(
                "Successor transition policy changed before append"
            )
        all_events, current_event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        validate_event_ledger_anchor_at(
            directory_fd,
            all_events,
            allow_missing=not all_events,
        )
        if (
            current_event_snapshot != loaded_event_snapshot
            or all_events != loaded_events
        ):
            raise SupervisionLogError(
                "Successor transition event state changed before append"
            )
        records = successor_transition_events(all_events, transition_id)
        prior = dict(records[-1]) if records else None
        if range_state is not None:
            current_range_state = implementation_range_state(current_policy)
            if current_range_state != range_state:
                raise SupervisionLogError(
                    "Successor transition implementation range changed before append"
                )
            range_state = current_range_state
            mission = bound_mission(current_policy)
            contract = implementation_range_contract(current_policy)
            if mission is None or contract is None:
                raise SupervisionLogError(
                    "Canonical implementation range lacks a bound mission"
                )
            if prior is None:
                eligible_blocks = list(range_state["eligible_blocks"])
                if not eligible_blocks:
                    raise SupervisionLogError(
                        "Successor transition has no dependency-safe first Block"
                    )
                canonical_identity = {
                    "tracker_sha256": range_state["tracker_sha256"],
                    "tracker_source_record": (
                        "implementation-range-history:"
                        + str(range_state["range_history_head_sha256"])
                    ),
                    "requested_block_range": format_implementation_block_set(
                        list(range_state["requested_blocks"])
                    ),
                    "first_eligible_block": f"Block {eligible_blocks[0]}",
                    "source_mission_root": mission["mission_root"],
                }
                for field, expected in canonical_identity.items():
                    if record.get(field) != expected:
                        raise SupervisionLogError(
                            "Successor transition identity differs from the canonical "
                            f"implementation range: {field.replace('_', ' ')}"
                        )
            else:
                source_prefix = "implementation-range-history:"
                source_record = str(prior.get("tracker_source_record", ""))
                source_head = (
                    source_record[len(source_prefix):]
                    if source_record.startswith(source_prefix)
                    else ""
                )
                source_entry = next(
                    (
                        item
                        for item in contract["history"]
                        if item.get("entry_sha256") == source_head
                    ),
                    None,
                )
                compatible = bool(
                    source_entry is not None
                    and source_entry.get("tracker_sha256")
                    == prior.get("tracker_sha256")
                    and source_entry.get("tracker_structure_sha256")
                    == contract.get("tracker_structure_sha256")
                    and prior.get("requested_block_range")
                    == format_implementation_block_set(
                        list(range_state["requested_blocks"])
                    )
                    and prior.get("source_mission_root")
                    == mission.get("mission_root")
                )
                legacy_terminal = False
                if (
                    not compatible
                    and record["phase"] in SUCCESSOR_TRANSITION_TERMINAL_PHASES
                ):
                    policy_history, _history_snapshot = events_snapshot(
                        Path("policy-history.jsonl"), directory_fd=directory_fd
                    )
                    legacy_terminal = legacy_terminal_range_compatibility_eligible(
                        current_policy,
                        all_events=all_events,
                        policy_history=policy_history,
                        prior=prior,
                        record=record,
                        contract=contract,
                        range_state=range_state,
                    )
                if not compatible and not legacy_terminal:
                    raise SupervisionLogError(
                        "Current implementation range is not structurally compatible "
                        "with the frozen successor genesis"
                    )
        if prior is None:
            if not record["topology_posture"]:
                record["topology_posture"] = "same-task-new-run"
            if not record["topology_basis"]:
                record["topology_basis"] = (
                    "same-task-default"
                    if record["topology_posture"] == "same-task-new-run"
                    else ""
                )
            if record["topology_basis"] == "technical-isolation":
                policy_history, _history_snapshot = events_snapshot(
                    Path("policy-history.jsonl"), directory_fd=directory_fd
                )
                topology_event = canonical_successor_topology_event(
                    all_events,
                    event_record_id=str(
                        record["topology_decision_event_record_id"]
                    ),
                    policy=policy,
                    policy_history=policy_history,
                )
                expected_topology = {
                    "transition_id": record["transition_id"],
                    "topology_rationale": record["topology_rationale"],
                    "governing_authority_source_class": record[
                        "governing_authority_source_class"
                    ],
                    "governing_authority_source_record": record[
                        "governing_authority_source_record"
                    ],
                    "governing_authority_source_sha256": record[
                        "governing_authority_source_sha256"
                    ],
                }
                if any(
                    topology_event.get(field) != expected
                    for field, expected in expected_topology.items()
                ):
                    raise SupervisionLogError(
                        "Technical-isolation decision does not match the transition"
                    )
                record["topology_decision_event_sha256"] = topology_event[
                    "record_sha256"
                ]
        else:
            prior.setdefault(
                "governing_authority_source_sha256",
                record["governing_authority_source_sha256"],
            )
            prior.setdefault("topology_posture", "distinct-task")
            prior.setdefault("topology_basis", "legacy-linear")
            prior.setdefault(
                "topology_rationale", "Legacy linear successor transition."
            )
            prior.setdefault("transition_expires_at", "")
            prior.setdefault("replaces_transition_id", "")
            prior.setdefault("topology_decision_event_record_id", "")
            prior.setdefault("topology_decision_event_sha256", "")
            prior.setdefault("topology_request_sha256", "")
            for field in (
                "topology_posture",
                "topology_basis",
                "topology_rationale",
                "topology_request_sha256",
                "transition_expires_at",
                "replaces_transition_id",
                "topology_decision_event_record_id",
                "topology_decision_event_sha256",
            ):
                if not record[field]:
                    record[field] = prior[field]
            if record["phase"] in SUCCESSOR_TRANSITION_TERMINAL_PHASES:
                for field in (
                    "successor_thread_id",
                    "successor_mission_root",
                    "successor_group_id",
                    "handoff_record",
                    "acknowledgement_record",
                    "started_block",
                ):
                    if not record[field]:
                        record[field] = prior.get(field, "")
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
                "prior_record_id",
                "disposition_reason",
                "correction_authority_source_class",
                "correction_authority_source_record",
                "correction_authority_source_sha256",
                "replacement_transition_id",
                "governing_outcome_effect",
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
        validate_successor_transition(prior, record, all_events)
        record["record_id"] = f"EVT-{len(all_events) + 1:06d}"
        prior_hash = (
            str(all_events[-1].get("record_sha256")) if all_events else None
        )
        appended_hash = append_raw_locked_at(
            directory_fd,
            "events.jsonl",
            record,
            previous_record_sha256=prior_hash,
            expected_file_snapshot=current_event_snapshot,
            require_event_anchor=True,
        )
        _current_directory, recheck_fd, recheck_snapshot = open_member_directory(
            root_from(args), args.target_thread
        )
        try:
            if (
                recheck_snapshot[:2] != directory_snapshot[:2]
                or event_head_hash(
                    Path("events.jsonl"), directory_fd=recheck_fd
                )
                != appended_hash
            ):
                raise SupervisionLogError(
                    "Successor transition append lost canonical owner currentness"
                )
        finally:
            os.close(recheck_fd)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def cmd_successor_transition_gate(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    transition_id = safe_id(args.transition_id, label="successor transition ID")
    records = successor_transition_events(all_events, transition_id)
    if not records:
        raise SupervisionLogError("Successor transition does not exist")
    head = records[-1]
    phase = str(head["phase"])
    heads = successor_transition_heads(all_events)
    activated = successor_transition_is_activated(heads, transition_id, head)
    topology = str(head.get("topology_posture") or "distinct-task")
    if not activated:
        next_action = "await-exact-supersession-link"
        authority_required = False
    elif phase == "required" and topology == "same-task-new-run":
        next_action = "start-same-task-new-run"
        authority_required = False
    elif phase == "required":
        if args.task_creation_authority == "available":
            next_action = "create-successor-task"
            authority_required = False
        else:
            next_action = "keep-open-await-direct-task-creation-authority"
            authority_required = True
    elif phase in SUCCESSOR_TRANSITION_TERMINAL_PHASES:
        authority_required = False
        next_action = {
            "corrected": "continue-governing-outcome-in-source-task",
            "cancelled": "continue-governing-outcome-in-source-task",
            "expired": "continue-governing-outcome-in-source-task",
            "superseded": "continue-replacement-transition",
        }[phase]
    else:
        authority_required = False
        next_action = {
            "successor-created": "bind-successor-mission-and-isolated-supervision",
            "successor-bound": "send-exact-handoff",
            "handoff-sent": "obtain-target-acknowledgement",
            "target-acknowledged": "start-first-eligible-block",
            "work-started": (
                "continue-same-task-run"
                if topology == "same-task-new-run"
                else "continue-successor-and-close-transition-incident"
            ),
        }[phase]
    source_stop_permitted = bool(
        activated and phase == "work-started" and topology == "distinct-task"
    )
    transition_open = bool(
        activated and phase not in SUCCESSOR_TRANSITION_CLOSED_PHASES
    )
    control_posture = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=all_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
    print(
        json.dumps(
            {
                "transition_id": transition_id,
                "phase": phase,
                "transition_open": transition_open,
                "source_stop_permitted": source_stop_permitted,
                "required_source_posture": (
                    "transition-satisfied" if source_stop_permitted else "in-progress"
                ),
                "next_action": next_action,
                "direct_task_creation_authority_required": authority_required,
                "human_input_required": False,
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
                "topology_posture": topology,
                "topology_basis": head.get("topology_basis") or "legacy-linear",
                "disposition_reason": head.get("disposition_reason") or None,
                "governing_outcome_effect": (
                    head.get("governing_outcome_effect") or None
                ),
                "replacement_transition_id": (
                    head.get("replacement_transition_id") or None
                ),
                "transition_history_record_ids": [
                    item["record_id"] for item in records
                ],
                "control_posture": control_posture,
                "required_target_posture": control_posture["required_target_posture"],
            },
            sort_keys=True,
        )
    )


def supervision_group_identity(
    policy: Mapping[str, Any], *, legacy_claim: str | None = None
) -> tuple[str, str]:
    persisted = policy.get("supervision_group_id")
    if isinstance(persisted, str) and SAFE_ID.fullmatch(persisted):
        return persisted, "policy"
    if legacy_claim and SAFE_ID.fullmatch(legacy_claim):
        return legacy_claim, "legacy-transition"
    return (
        "legacy-supervision-group-"
        + digest(
            {
                "kind": "legacy-supervision-group-projection",
                "target_thread_id": policy.get("target_thread_id"),
                "created_at": policy.get("created_at"),
            }
        )[:24],
        "legacy-policy-projection",
    )


def execution_run_identity(
    policy: Mapping[str, Any], *, supervision_group_id: str | None = None
) -> str | None:
    mission = bound_mission(dict(policy))
    if mission is None:
        return None
    return digest(
        {
            "kind": "execution-run",
            "governing_outcome_root": mission["mission_root"],
            "task_id": policy.get("target_thread_id"),
            "supervision_group_id": (
                supervision_group_id or supervision_group_identity(policy)[0]
            ),
        }
    )


def latest_active_block(all_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(all_events):
        for field in ("active_block", "started_block", "first_eligible_block"):
            value = item.get(field)
            if isinstance(value, str) and value:
                return {"value": value, "source_record": item.get("record_id")}
    return None


def event_head_hash(path: Path, *, directory_fd: int | None = None) -> str | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            return None
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        buffer = bytearray()
        while position > 0:
            step = min(4096, position)
            position -= step
            handle.seek(position)
            buffer[:0] = handle.read(step)
            lines = bytes(buffer).splitlines()
            if len(lines) > 1 or position == 0:
                for raw in reversed(lines):
                    if raw.strip():
                        try:
                            value = json.loads(raw)
                        except json.JSONDecodeError as exc:
                            raise SupervisionLogError(
                                "Event ledger tail is malformed"
                            ) from exc
                        head = value.get("record_sha256")
                        if not isinstance(head, str) or not SHA256.fullmatch(head):
                            raise SupervisionLogError(
                                "Event ledger tail lacks an exact record hash"
                            )
                        return head
        return None


def member_directory(root: Path, target_thread_id: str) -> Path:
    target = safe_id(target_thread_id, label="governing outcome member target")
    directory = root / target
    if directory.parent != root:
        raise SupervisionLogError(
            "Governing outcome member escaped the supervision root"
        )
    return directory


def open_member_directory(
    root: Path, target_thread_id: str
) -> tuple[Path, int, tuple[int, int, int, int]]:
    directory = member_directory(root, target_thread_id)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(directory, flags)
        snapshot = file_snapshot(os.fstat(descriptor))
    except OSError as exc:
        raise SupervisionLogError(
            "Governing outcome member directory is unavailable or unsafe"
        ) from exc
    if path_snapshot(directory) != snapshot:
        os.close(descriptor)
        raise SupervisionLogError(
            "Governing outcome member directory changed during open"
        )
    return directory, descriptor, snapshot


def path_snapshot_at(
    directory_fd: int, name: str
) -> tuple[int, int, int, int] | None:
    try:
        return file_snapshot(
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        )
    except OSError:
        return None


def active_successor_edges(
    all_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    heads = successor_transition_heads(all_events)
    return [
        item
        for transition_id, item in heads.items()
        if isinstance(item.get("successor_thread_id"), str)
        and item.get("successor_thread_id")
        and item.get("phase") not in SUCCESSOR_TRANSITION_TERMINAL_PHASES
        and successor_transition_is_activated(heads, transition_id, item)
    ]


def load_governing_outcome_members(
    *,
    owner_directory: Path,
    owner_policy: dict[str, Any],
    owner_events: list[dict[str, Any]],
    owner_policy_snapshot: tuple[int, int, int, int] | None = None,
    owner_event_snapshot: tuple[int, int, int, int] | None = None,
    owner_directory_snapshot: tuple[int, int, int, int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str, bool]:
    root = owner_directory.parent.resolve()
    owner_target = str(
        owner_policy.get("target_thread_id") or owner_directory.name
    )
    queue: list[
        tuple[
            str,
            Path,
            dict[str, Any],
            list[dict[str, Any]],
            dict[str, Any] | None,
            tuple[int, int, int, int] | None,
            tuple[int, int, int, int] | None,
            tuple[int, int, int, int] | None,
        ]
    ] = [
        (
            owner_target,
            owner_directory,
            owner_policy,
            owner_events,
            None,
            owner_policy_snapshot,
            owner_event_snapshot,
            owner_directory_snapshot,
        )
    ]
    queued = {owner_target}
    members: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    snapshots: dict[
        str,
        tuple[
            Path,
            tuple[int, int, int, int] | None,
            Path,
            str | None,
            tuple[int, int, int, int] | None,
            Path,
            tuple[int, int, int, int] | None,
        ],
    ] = {}

    while queue:
        (
            target,
            directory,
            policy,
            member_events,
            edge,
            policy_snapshot,
            event_snapshot,
            directory_snapshot,
        ) = queue.pop(0)
        event_path = directory / "events.jsonl"
        policy_path = directory / "policy.json"
        event_head = (
            member_events[-1].get("record_sha256") if member_events else None
        )
        if event_snapshot is None:
            event_snapshot = path_snapshot(event_path)
        if policy_snapshot is None:
            policy_snapshot = path_snapshot(policy_path)
        snapshots[target] = (
            directory,
            directory_snapshot,
            event_path,
            event_head if isinstance(event_head, str) else None,
            event_snapshot,
            policy_path,
            policy_snapshot,
        )
        mission = bound_mission(policy)
        if mission is None:
            issues.append(
                {
                    "kind": "member-mission-unbound",
                    "target_thread_id": target,
                }
            )
        if edge is not None and mission is not None:
            expected_mission = edge.get("successor_mission_root")
            if not expected_mission or mission.get("mission_root") != expected_mission:
                issues.append(
                    {
                        "kind": "member-mission-mismatch",
                        "target_thread_id": target,
                    }
                )
        claimed_group_id = (
            str(edge.get("successor_group_id", "")) if edge is not None else None
        )
        group_id, group_binding_mode = supervision_group_identity(
            policy, legacy_claim=claimed_group_id
        )
        if (
            edge is not None
            and group_binding_mode == "policy"
            and claimed_group_id != group_id
        ):
            issues.append(
                {
                    "kind": "member-group-mismatch",
                    "target_thread_id": target,
                }
            )
        members.append(
            {
                "target_thread_id": target,
                "policy": policy,
                "events": member_events,
                "policy_sha256": policy.get("policy_sha256"),
                "event_head_sha256": event_head,
                "mission_root": mission.get("mission_root") if mission else None,
                "task_id": target,
                "supervision_group_id": group_id,
                "supervision_group_binding": group_binding_mode,
                "membership_claimed_group_id": (
                    edge.get("successor_group_id") if edge is not None else None
                ),
                "execution_run_id": execution_run_identity(
                    policy, supervision_group_id=group_id
                ),
                "active_block": latest_active_block(member_events),
                "membership_source_record": edge.get("record_id") if edge else None,
            }
        )
        for successor in active_successor_edges(member_events):
            successor_target = str(successor.get("successor_thread_id", ""))
            if not successor_target:
                continue
            if successor_target == target or successor_target in queued:
                issues.append(
                    {
                        "kind": "successor-membership-cycle-or-duplicate",
                        "target_thread_id": successor_target,
                    }
                )
                continue
            if len(queued) >= MAX_GOVERNING_OUTCOME_MEMBERS:
                issues.append(
                    {
                        "kind": "member-bound-exceeded",
                        "target_thread_id": successor_target,
                    }
                )
                continue
            queued.add(successor_target)
            try:
                (
                    successor_directory,
                    successor_directory_fd,
                    successor_directory_snapshot,
                ) = open_member_directory(root, successor_target)
                try:
                    successor_policy, successor_policy_snapshot = read_json_snapshot(
                        Path("policy.json"), directory_fd=successor_directory_fd
                    )
                    validate_policy(successor_policy)
                    if successor_policy.get("target_thread_id") != successor_target:
                        raise SupervisionLogError(
                            "Member policy belongs to a different target"
                        )
                    successor_events, successor_event_snapshot = events_snapshot(
                        Path("events.jsonl"),
                        directory_fd=successor_directory_fd,
                    )
                finally:
                    os.close(successor_directory_fd)
            except SupervisionLogError:
                issues.append(
                    {
                        "kind": "member-state-unavailable-or-invalid",
                        "target_thread_id": successor_target,
                    }
                )
                continue
            queue.append(
                (
                    successor_target,
                    successor_directory,
                    successor_policy,
                    successor_events,
                    successor,
                    successor_policy_snapshot,
                    successor_event_snapshot,
                    successor_directory_snapshot,
                )
            )

    currentness_material = [
        {
            "target_thread_id": member["target_thread_id"],
            "policy_sha256": member["policy_sha256"],
            "event_head_sha256": member["event_head_sha256"],
        }
        for member in sorted(members, key=lambda value: value["target_thread_id"])
    ]
    stable = True
    for target, (
        directory_path,
        recorded_directory_snapshot,
        path,
        recorded_head,
        recorded_event_snapshot,
        policy_path,
        recorded_policy_snapshot,
    ) in snapshots.items():
        recheck_directory_fd: int | None = None
        if recorded_directory_snapshot is not None:
            try:
                (
                    _recheck_directory,
                    recheck_directory_fd,
                    current_directory_snapshot,
                ) = open_member_directory(root, target)
            except SupervisionLogError:
                current_directory_snapshot = None
            if current_directory_snapshot != recorded_directory_snapshot:
                stable = False
                issues.append(
                    {
                        "kind": "member-directory-changed-during-read",
                        "target_thread_id": target,
                    }
                )
                if recheck_directory_fd is not None:
                    os.close(recheck_directory_fd)
                continue
        try:
            current_head = event_head_hash(
                Path("events.jsonl") if recheck_directory_fd is not None else path,
                directory_fd=recheck_directory_fd,
            )
        except (OSError, SupervisionLogError):
            current_head = None
            stable = False
            issues.append(
                {
                    "kind": "member-head-unavailable-during-recheck",
                    "target_thread_id": target,
                }
            )
        if current_head != recorded_head:
            stable = False
            issues.append(
                {
                    "kind": "member-head-changed-during-read",
                    "target_thread_id": target,
                }
            )
        current_event_snapshot = (
            path_snapshot_at(recheck_directory_fd, "events.jsonl")
            if recheck_directory_fd is not None
            else path_snapshot(path)
        )
        if current_event_snapshot != recorded_event_snapshot:
            stable = False
            issues.append(
                {
                    "kind": "member-event-file-changed-during-read",
                    "target_thread_id": target,
                }
            )
        current_policy_snapshot = (
            path_snapshot_at(recheck_directory_fd, "policy.json")
            if recheck_directory_fd is not None
            else path_snapshot(policy_path)
        )
        if current_policy_snapshot != recorded_policy_snapshot:
            stable = False
            issues.append(
                {
                    "kind": "member-policy-changed-during-read",
                    "target_thread_id": target,
                }
            )
        if recheck_directory_fd is not None:
            os.close(recheck_directory_fd)
    return members, issues, digest(currentness_material), stable


def decision_can_block(head: Mapping[str, Any], policy: dict[str, Any]) -> bool:
    mission = bound_mission(policy)
    if mission is None or head.get("mission_root") != mission.get("mission_root"):
        return False
    authority_source_class = str(head.get("authority_source_class", ""))
    classification = str(head.get("classification", ""))
    impact_class = str(head.get("impact_class", ""))
    provenance_valid = bool(
        authority_source_class in AUTHORITY_SOURCE_CLASSES
        and head.get("authority_source_record")
        and (
            classification != "reserved-authority"
            or authority_source_class in DIRECT_AUTHORITY_SOURCE_CLASSES
        )
    )
    challenge_valid = bool(
        (
            impact_class not in {"goal-blocking", "goal-reversing"}
            and head.get("ordinary_means_disabled") is not True
        )
        or (
            authority_source_class in DIRECT_AUTHORITY_SOURCE_CLASSES
            and head.get("independent_mission_review") is True
        )
    )
    return bool(
        head.get("phase") in {"handoff-sent", "target-acknowledged"}
        and head.get("outcome") == "safe-deferred"
        and head.get("safe_frontier") == "empty"
        and classification in {"missing-fact", "reserved-authority"}
        and provenance_valid
        and challenge_valid
    )


def decision_successor_reconciliation(
    head: Mapping[str, Any],
    all_events: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve a stale topology deferral from a later canonical correction.

    A successor-transition correction is sufficient only when it closes the
    exact transition premise that produced the decision: the transition genesis
    predates and is cited by the decision-ready record, has the same mission,
    source, and frozen state fingerprint, and is followed later in the canonical
    ledger by a current direct-authority correction that resumes the governing
    outcome in the same task.  This lets the reducer converge immediately while
    preserving both histories; the watcher can then append the explicit decision
    correction without leaving the target blocked in the interim.
    """
    if not decision_can_block(head, policy):
        return None
    try:
        decision_position = all_events.index(head)
    except ValueError:
        return None
    decision_id = head.get("decision_id")
    if not isinstance(decision_id, str):
        return None
    decision_lineage = decision_events(all_events, decision_id)
    decision_ready = next(
        (item for item in decision_lineage if item.get("phase") == "decision-ready"),
        None,
    )
    if decision_ready is None:
        return None
    try:
        decision_ready_position = all_events.index(decision_ready)
    except ValueError:
        return None
    if decision_ready_position >= decision_position:
        return None
    decision_ready_evidence = decision_ready.get("evidence")
    if not isinstance(decision_ready_evidence, list):
        return None
    premise_fingerprint = decision_ready.get("state_fingerprint")
    if not isinstance(premise_fingerprint, str) or not premise_fingerprint:
        return None
    if any(
        decision_ready.get(field) != head.get(field)
        for field in (
            "mission_root",
            "authority_source_class",
            "authority_source_record",
            *DECISION_IMMUTABLE_FIELDS,
        )
    ):
        return None
    transition_ids = {
        str(item.get("transition_id"))
        for item in all_events
        if item.get("kind") == "successor-transition"
        and isinstance(item.get("transition_id"), str)
    }
    matches: list[dict[str, Any]] = []
    for transition_id in sorted(transition_ids):
        records = successor_transition_events(all_events, transition_id)
        if len(records) < 2:
            continue
        first = records[0]
        correction = records[-1]
        try:
            first_position = all_events.index(first)
            correction_position = all_events.index(correction)
        except ValueError:
            continue
        if (
            first_position >= decision_ready_position
            or first.get("record_id") not in decision_ready_evidence
            or correction_position <= decision_position
        ):
            continue
        if (
            first.get("phase") != "required"
            or correction.get("phase") not in {"corrected", "cancelled", "expired"}
            or correction.get("governing_outcome_effect") != "continue-same-task"
            or correction.get("prior_record_id") != records[-2].get("record_id")
            or first.get("source_mission_root")
            != decision_ready.get("mission_root")
            or first.get("state_fingerprint") != premise_fingerprint
            or first.get("governing_authority_source_class")
            != decision_ready.get("authority_source_class")
            or first.get("governing_authority_source_record")
            != decision_ready.get("authority_source_record")
            or correction.get("correction_authority_source_class")
            != head.get("authority_source_class")
            or correction.get("correction_authority_source_record")
            != head.get("authority_source_record")
        ):
            continue
        correction_sha256 = str(
            correction.get("correction_authority_source_sha256", "")
        )
        if SHA256.fullmatch(correction_sha256) is None or not canonical_authority_source(
            policy,
            source_class=str(correction["correction_authority_source_class"]),
            source_record=str(correction["correction_authority_source_record"]),
            source_sha256=correction_sha256,
        ):
            continue
        evidence = correction.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            continue
        matches.append(
            {
                "decision_record_id": head.get("record_id"),
                "transition_id": transition_id,
                "transition_genesis_record_id": first.get("record_id"),
                "correction_record_id": correction.get("record_id"),
                "correction_phase": correction.get("phase"),
                "governing_outcome_effect": "continue-governing-outcome",
            }
        )
    return matches[0] if len(matches) == 1 else None


def decision_head_is_open(
    head: Mapping[str, Any],
    all_events: list[dict[str, Any]],
    policy: dict[str, Any],
) -> bool:
    if head.get("phase") in DECISION_CORRECTION_PHASES:
        return False
    if decision_successor_reconciliation(head, all_events, policy) is not None:
        return False
    return bool(
        head.get("phase") != "target-acknowledged"
        or head.get("outcome") == "safe-deferred"
    )


def decision_authorizes_direct_stop(
    head: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    policy: dict[str, Any],
) -> bool:
    mission = bound_mission(policy)
    evidence = lifecycle.get("evidence", [])
    if not isinstance(evidence, list):
        return False
    decision_fingerprint = str(head.get("state_fingerprint", ""))
    lifecycle_fingerprint = str(lifecycle.get("state_fingerprint", ""))
    return bool(
        mission is not None
        and lifecycle.get("status") == "stopped"
        and head.get("record_id") in evidence
        and head.get("phase") == "target-acknowledged"
        and head.get("classification") == "reserved-authority"
        and head.get("outcome") == "user-supplied"
        and head.get("safe_frontier") == "empty"
        and head.get("mission_root") == mission.get("mission_root")
        and head.get("authority_source_class") in DIRECT_AUTHORITY_SOURCE_CLASSES
        and bool(head.get("authority_source_record"))
        and head.get("independent_mission_review") is True
        and head.get("impact_class") in {"goal-blocking", "goal-reversing"}
        and head.get("ordinary_means_disabled") is True
        and bool(decision_fingerprint)
        and decision_fingerprint == lifecycle_fingerprint
    )


def tracker_program_roots(members: list[dict[str, Any]]) -> list[str]:
    roots = {
        str(item["tracker_sha256"])
        for member in members
        for item in active_successor_edges(member["events"])
        if item.get("tracker_sha256")
    }
    for member in members:
        source = (
            member["policy"]
            .get("mission_binding", {})
            .get("mission_derivation", {})
            .get("controlling_source", {})
        )
        if source.get("class") == "tracker" and source.get("sha256"):
            roots.add(str(source["sha256"]))
    return sorted(roots)


def reduce_control_posture(
    *,
    directory: Path,
    policy: dict[str, Any],
    owner_events: list[dict[str, Any]],
    owner_policy_snapshot: tuple[int, int, int, int] | None = None,
    owner_event_snapshot: tuple[int, int, int, int] | None = None,
    owner_directory_snapshot: tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    members, issues, currentness_root, stable = load_governing_outcome_members(
        owner_directory=directory,
        owner_policy=policy,
        owner_events=owner_events,
        owner_policy_snapshot=owner_policy_snapshot,
        owner_event_snapshot=owner_event_snapshot,
        owner_directory_snapshot=owner_directory_snapshot,
    )
    mission = bound_mission(policy)
    owner_target = str(policy.get("target_thread_id") or directory.name)
    identities = {
        "governing_outcome": {
            "root": mission.get("mission_root") if mission else None,
            "source_record": mission.get("mission_source_record") if mission else None,
            "owner_target_thread_id": owner_target,
        },
        "tracker_program_roots": tracker_program_roots(members),
        "members": [
            {
                key: member[key]
                for key in (
                    "task_id",
                    "supervision_group_id",
                    "execution_run_id",
                    "active_block",
                    "mission_root",
                    "membership_source_record",
                    "membership_claimed_group_id",
                    "supervision_group_binding",
                )
            }
            for member in members
        ],
    }
    if mission is None:
        issues.append(
            {"kind": "governing-outcome-mission-unbound", "target_thread_id": owner_target}
        )

    open_transitions: list[dict[str, Any]] = []
    open_decisions: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    reconciled_decisions: list[dict[str, Any]] = []
    completion_candidates: list[dict[str, Any]] = []
    subordinate_completion_candidates: list[dict[str, Any]] = []
    direct_stop_candidates: list[dict[str, Any]] = []
    subordinate_stop_records: list[str] = []
    for member in members:
        member_events = member["events"]
        member_policy = member["policy"]
        open_transitions.extend(
            item
            for item in successor_transition_heads(
                member_events, open_only=True
            ).values()
        )
        heads: dict[str, dict[str, Any]] = {}
        for item in member_events:
            if item.get("kind") == "decision" and item.get("decision_id"):
                heads[str(item["decision_id"])] = item
        for head in heads.values():
            reconciliation = decision_successor_reconciliation(
                head, member_events, member_policy
            )
            if reconciliation is not None:
                reconciled_decisions.append(
                    {
                        **reconciliation,
                        "target_thread_id": str(member["target_thread_id"]),
                        "reconciliation_posture": (
                            "append-explicit-decision-correction"
                        ),
                    }
                )
                continue
            if head.get("phase") in DECISION_CORRECTION_PHASES:
                reconciled_decisions.append(
                    {
                        "decision_record_id": head.get("record_id"),
                        "target_thread_id": str(member["target_thread_id"]),
                        "correction_record_id": head.get("record_id"),
                        "correction_phase": head.get("phase"),
                        "governing_outcome_effect": head.get(
                            "governing_outcome_effect"
                        ),
                        "reconciliation_posture": "recorded",
                    }
                )
                continue
            if decision_head_is_open(head, member_events, member_policy):
                open_decisions.append(
                    (head, member_policy, str(member["target_thread_id"]))
                )
        lifecycle = next(
            (
                item
                for item in reversed(member_events)
                if item.get("kind") == "lifecycle"
            ),
            None,
        )
        if lifecycle is not None and lifecycle.get("status") == "completed":
            state_fingerprint = str(lifecycle.get("state_fingerprint", ""))
            completion = latest_outcome_completion_record(
                member_events, state_fingerprint=state_fingerprint
            )
            permitted, reason = assess_outcome_completion_record(
                completion,
                policy=member_policy,
                state_fingerprint=state_fingerprint,
            )
            candidate = {
                "lifecycle_record_id": lifecycle.get("record_id"),
                "completion_record_id": (
                    completion.get("record_id") if completion is not None else None
                ),
                "target_thread_id": member["target_thread_id"],
            }
            if (
                permitted
                and completion is not None
                and lifecycle.get("outcome_completion_record_id")
                == completion.get("record_id")
            ):
                if member["target_thread_id"] == owner_target:
                    completion_candidates.append(candidate)
                else:
                    subordinate_completion_candidates.append(candidate)
            elif permitted:
                issues.append(
                    {
                        "kind": "completion-lifecycle-binding-mismatch",
                        "target_thread_id": member["target_thread_id"],
                    }
                )
            else:
                issues.append(
                    {
                        "kind": "completion-not-current",
                        "target_thread_id": member["target_thread_id"],
                        "reason": reason,
                    }
                )
        if lifecycle is not None and lifecycle.get("status") == "stopped":
            stop_decision = next(
                (
                    head
                    for head in heads.values()
                    if decision_authorizes_direct_stop(
                        head, lifecycle, member_policy
                    )
                ),
                None,
            )
            if member["target_thread_id"] != owner_target:
                subordinate_stop_records.append(str(lifecycle.get("record_id")))
            elif stop_decision is not None:
                direct_stop_candidates.append(
                    {
                        "lifecycle_record_id": lifecycle.get("record_id"),
                        "decision_record_id": stop_decision.get("record_id"),
                        "authority_source_record": stop_decision.get(
                            "authority_source_record"
                        ),
                        "target_thread_id": owner_target,
                    }
                )
            else:
                issues.append(
                    {
                        "kind": "direct-stop-authority-missing-or-invalid",
                        "target_thread_id": owner_target,
                    }
                )

    safe_work = any(
        head.get("safe_frontier") == "nonempty"
        for head, _policy, _target in open_decisions
    )
    blocking_decisions = [
        head
        for head, member_policy, target in open_decisions
        if target == owner_target and decision_can_block(head, member_policy)
    ]
    owner_nonblocking_decisions = [
        head
        for head, member_policy, target in open_decisions
        if target == owner_target and not decision_can_block(head, member_policy)
    ]
    subordinate_decisions = [
        head
        for head, _member_policy, target in open_decisions
        if target != owner_target
    ]
    if not stable:
        required_posture = "in-progress"
        next_action = "retry-control-currentness"
    elif issues:
        required_posture = "in-progress"
        next_action = "reconcile-control-membership-or-evidence"
    elif direct_stop_candidates:
        required_posture = "stopped"
        next_action = "close-governing-outcome-at-direct-stop"
    elif open_transitions:
        required_posture = "in-progress"
        next_action = "continue-open-successor-transition"
    elif safe_work or owner_nonblocking_decisions:
        required_posture = "in-progress"
        next_action = "continue-safe-frontier-or-resolve-decision"
    elif blocking_decisions:
        required_posture = "blocked"
        next_action = "preserve-safe-deferral-and-revisit-on-authority-change"
    elif subordinate_decisions:
        required_posture = "in-progress"
        next_action = "continue-safe-frontier-or-resolve-decision"
    elif completion_candidates:
        required_posture = "completed"
        next_action = "close-governing-outcome"
    else:
        required_posture = "in-progress"
        next_action = "continue-governing-outcome"

    return {
        "required_target_posture": required_posture,
        "next_action": next_action,
        "manual_resume_required": False,
        "human_input_required": False,
        "governing_outcome_currentness_sha256": currentness_root,
        "member_count": len(members),
        "member_bound": MAX_GOVERNING_OUTCOME_MEMBERS,
        "snapshot_stable": stable,
        "identities": identities,
        "issues": issues,
        "open_transition_records": [
            item.get("record_id") for item in open_transitions
        ],
        "open_decision_records": [
            item.get("record_id") for item, _policy, _target in open_decisions
        ],
        "blocking_decision_records": [
            item.get("record_id") for item in blocking_decisions
        ],
        "reconciled_decisions": reconciled_decisions,
        "completion_candidates": completion_candidates,
        "subordinate_completion_candidates": subordinate_completion_candidates,
        "direct_stop_candidates": direct_stop_candidates,
        "subordinate_stop_records": subordinate_stop_records,
    }


def cmd_control_posture_gate(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        owner_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    result = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=owner_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
    print(json.dumps(result, sort_keys=True))


def validate_decision_transition(
    prior: dict[str, Any] | None,
    *,
    classification: str,
    phase: str,
    attempt: int,
    outcome: str,
) -> None:
    if phase not in {
        "resolved",
        "safe-deferred",
        "handoff-sent",
        "target-acknowledged",
        *DECISION_CORRECTION_PHASES,
    } and outcome:
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
    if phase in DECISION_CORRECTION_PHASES:
        if prior_phase not in {"handoff-sent", "target-acknowledged"}:
            raise SupervisionLogError(
                "Only a handed-off decision may receive a correction"
            )
        if prior.get("outcome") != "safe-deferred" or outcome != "safe-deferred":
            raise SupervisionLogError(
                "A decision correction must retire an exact safe deferral"
            )
        if attempt != prior_attempt:
            raise SupervisionLogError(
                "A decision correction must preserve the attempt count"
            )
        return
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
        "target-acknowledged": set(DECISION_CORRECTION_PHASES),
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
    adaptive_mode = effective_adaptive_decision_mode(policy)
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
    state_fingerprint = clean(
        args.state_fingerprint,
        label="state fingerprint",
        maximum=128,
    )
    exact_hashes = {
        "decision packet hash": args.decision_packet_hash,
        "blocked scope hash": args.blocked_scope_hash,
        "safe frontier hash": args.safe_frontier_hash,
    }
    for label, value in exact_hashes.items():
        if not clean(value, label=label, maximum=128):
            raise SupervisionLogError(f"{label.title()} is required")
    prior_record_id = clean(
        getattr(args, "prior_record", ""),
        label="prior decision record",
        maximum=128,
    )
    disposition_reason = clean(
        getattr(args, "disposition_reason", ""),
        label="decision correction reason",
        maximum=500,
    )
    correction_authority_source_class = (
        getattr(args, "correction_authority_source_class", "") or ""
    )
    correction_authority_source_record = clean(
        getattr(args, "correction_authority_source_record", ""),
        label="decision correction authority source record",
        maximum=128,
    )
    correction_authority_source_sha256 = clean(
        getattr(args, "correction_authority_source_sha256", ""),
        label="decision correction authority source SHA-256",
        maximum=64,
    )
    governing_outcome_effect = (
        getattr(args, "governing_outcome_effect", "") or ""
    )
    correction_values = (
        prior_record_id,
        disposition_reason,
        correction_authority_source_class,
        correction_authority_source_record,
        correction_authority_source_sha256,
        governing_outcome_effect,
    )
    if phase in DECISION_CORRECTION_PHASES:
        if prior_record_id:
            safe_id(prior_record_id, label="prior decision record")
        if correction_authority_source_record:
            safe_id(
                correction_authority_source_record,
                label="decision correction authority source record",
            )
        if not prior_record_id or not disposition_reason:
            raise SupervisionLogError(
                "A decision correction requires the exact prior record and reason"
            )
        if (
            correction_authority_source_class
            not in DIRECT_AUTHORITY_SOURCE_CLASSES
            or not correction_authority_source_record
            or not correction_authority_source_sha256
        ):
            raise SupervisionLogError(
                "A decision correction requires current direct authority"
            )
        correction_authority_source_sha256 = exact_sha256(
            correction_authority_source_sha256,
            label="decision correction authority source SHA-256",
        )
        if not canonical_authority_source(
            policy,
            source_class=correction_authority_source_class,
            source_record=correction_authority_source_record,
            source_sha256=correction_authority_source_sha256,
        ):
            raise SupervisionLogError(
                "Decision correction authority is not canonical"
            )
        if governing_outcome_effect not in DECISION_GOVERNING_OUTCOME_EFFECTS:
            raise SupervisionLogError(
                "A decision correction must continue the governing outcome"
            )
    elif any(correction_values):
        raise SupervisionLogError(
            "Decision correction fields are valid only on a corrected decision"
        )
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
            immutable_values = {
                "state_fingerprint": state_fingerprint,
                "decision_packet_hash": args.decision_packet_hash,
                "blocked_scope_hash": args.blocked_scope_hash,
                "safe_frontier_hash": args.safe_frontier_hash,
            }
            if any(
                prior.get(field) != value
                for field, value in immutable_values.items()
            ):
                raise SupervisionLogError(
                    "Decision transitions must preserve the frozen decision identity"
                )
        if (
            prior is not None
            and prior.get("classification") == classification
            and prior.get("phase") == phase
            and prior.get("safe_frontier") == safe_frontier
            and int(prior.get("attempt", 0)) == attempt
            and prior.get("outcome", "") == outcome
            and prior.get("state_fingerprint", "") == state_fingerprint
            and prior.get("decision_packet_hash") == args.decision_packet_hash
            and prior.get("blocked_scope_hash") == args.blocked_scope_hash
            and prior.get("safe_frontier_hash") == args.safe_frontier_hash
            and prior.get("evidence") == evidence_values
            and prior.get("prior_record_id", "") == prior_record_id
            and prior.get("disposition_reason", "") == disposition_reason
            and prior.get("correction_authority_source_class", "")
            == correction_authority_source_class
            and prior.get("correction_authority_source_record", "")
            == correction_authority_source_record
            and prior.get("correction_authority_source_sha256", "")
            == correction_authority_source_sha256
            and prior.get("governing_outcome_effect", "")
            == governing_outcome_effect
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
        if phase in DECISION_CORRECTION_PHASES:
            if prior is None or prior_record_id != prior.get("record_id"):
                raise SupervisionLogError(
                    "A decision correction requires the exact current prior record"
                )
            for field, expected in (
                ("safe_frontier", safe_frontier),
                ("decision_packet_hash", args.decision_packet_hash),
                ("blocked_scope_hash", args.blocked_scope_hash),
                ("safe_frontier_hash", args.safe_frontier_hash),
            ):
                if prior.get(field) != expected:
                    raise SupervisionLogError(
                        "A decision correction must preserve the exact deferred decision"
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
                    or (
                        adaptive_mode != "full-autonomous"
                        and (
                            not user_deadline_at
                            or now < parse_time(user_deadline_at)
                        )
                    )
                ):
                    raise SupervisionLogError(
                        "Automatic final selection requires all maintained attempts"
                    )
            if phase == "safe-deferred" and prior_phase != "user-responded":
                user_deadline_at = str(prior.get("user_deadline_at", ""))
                if (
                    prior_phase != "attempt-unresolved"
                    or prior_attempt < int(contract["max_attempts"])
                    or (
                        adaptive_mode != "full-autonomous"
                        and (
                            not user_deadline_at
                            or now < parse_time(user_deadline_at)
                        )
                    )
                ):
                    raise SupervisionLogError(
                        "Automatic safe deferral requires all maintained attempts"
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
            if (
                phase == "attempt-unresolved"
                and not user_deadline_at
                and adaptive_mode != "full-autonomous"
            ):
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
            "state_fingerprint": state_fingerprint,
            "evidence": evidence_values,
            "policy_sha256": policy["policy_sha256"],
            "prior_record_id": prior_record_id,
            "disposition_reason": disposition_reason,
            "correction_authority_source_class": (
                correction_authority_source_class
            ),
            "correction_authority_source_record": (
                correction_authority_source_record
            ),
            "correction_authority_source_sha256": (
                correction_authority_source_sha256
            ),
            "governing_outcome_effect": governing_outcome_effect,
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
    if effective_adaptive_decision_mode(policy) == "full-autonomous":
        phase = ""
    elif action == "challenge-mission-provenance":
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
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    decision_id = safe_id(args.decision_id, label="decision ID")
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
    adaptive_mode = effective_adaptive_decision_mode(policy)
    alignment_contract = alignment_operating_contract()
    meta_charter = mission_meta_charter_profile()
    binding = bound_mission(policy)
    successor_reconciliation = decision_successor_reconciliation(
        head, all_events, policy
    )
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
    if phase in DECISION_CORRECTION_PHASES:
        action = "continue-governing-outcome-after-decision-correction"
    elif successor_reconciliation is not None:
        action = "record-decision-correction-and-continue-governing-outcome"
    elif phase == "decision-ready":
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
        elif adaptive_mode != "full-autonomous" and head.get("user_deadline_at") and now < parse_time(
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
    local_blocking_permitted = bool(
        phase not in DECISION_CORRECTION_PHASES
        and successor_reconciliation is None
        and phase in {"handoff-sent", "target-acknowledged"}
        and head.get("outcome") == "safe-deferred"
        and not safe_work
        and classification in {"missing-fact", "reserved-authority"}
        and mission_binding_valid
        and authority_provenance_valid
        and mission_challenge_valid
    )
    control_posture = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=all_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
    blocking_permitted = (
        control_posture["required_target_posture"] == "blocked"
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
        "required_target_posture": control_posture["required_target_posture"],
        "local_blocking_permitted": local_blocking_permitted,
        "control_posture": control_posture,
        "manual_resume_required": False,
        "attempt_model": contract["attempt_model"],
        "attempt_reasoning": contract["attempt_reasoning"],
        "attempt_minutes": contract["attempt_minutes"],
        "max_attempts": contract["max_attempts"],
        "adaptive_decision_mode": adaptive_mode,
        "human_input_eligible": adaptive_mode != "full-autonomous",
        "decision_reconciliation": (
            successor_reconciliation
            if successor_reconciliation is not None
            else (
                {
                    "decision_record_id": head.get("record_id"),
                    "correction_record_id": head.get("record_id"),
                    "correction_phase": phase,
                    "governing_outcome_effect": head.get(
                        "governing_outcome_effect"
                    ),
                    "reconciliation_posture": "recorded",
                }
                if phase in DECISION_CORRECTION_PHASES
                else None
            )
        ),
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
        "adaptive_decision_mode": getattr(args, "adaptive_decision_mode", None),
        "adaptive_target_class": getattr(args, "adaptive_target_class", None),
        "adaptive_target_repository_root": getattr(
            args, "adaptive_target_repository_root", None
        ),
        "candidate_max_active_lanes": getattr(args, "candidate_max_active_lanes", None),
        "candidate_max_files": getattr(args, "candidate_max_files", None),
        "candidate_max_changed_lines": getattr(args, "candidate_max_changed_lines", None),
        "candidate_max_commands": getattr(args, "candidate_max_commands", None),
        "candidate_max_elapsed_minutes": getattr(args, "candidate_max_elapsed_minutes", None),
        "candidate_max_mapped_comparisons": getattr(args, "candidate_max_mapped_comparisons", None),
        "candidate_max_review_passes": getattr(args, "candidate_max_review_passes", None),
    }
    changed = ensure_adaptive_decision_policy(policy)
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
    adaptive_requested = any(
        requested[key] is not None
        for key in (
            "adaptive_decision_mode",
            "adaptive_target_class",
            "adaptive_target_repository_root",
            "candidate_max_active_lanes",
            "candidate_max_files",
            "candidate_max_changed_lines",
            "candidate_max_commands",
            "candidate_max_elapsed_minutes",
            "candidate_max_mapped_comparisons",
            "candidate_max_review_passes",
        )
    )
    if adaptive_requested:
        adaptive = dict(policy["adaptive_decision_control"])
        budget = dict(adaptive["candidate_budget"])
        mode = requested["adaptive_decision_mode"] or adaptive["adaptive_decision_mode"]
        target_class = requested["adaptive_target_class"] or adaptive["target_class"]
        target_repository_root = (
            requested["adaptive_target_repository_root"]
            if requested["adaptive_target_repository_root"] is not None
            else adaptive.get("target_repository_root")
        )
        if (
            requested["adaptive_target_repository_root"] is not None
            and adaptive.get("target_repository_root") is not None
            and requested["adaptive_target_repository_root"]
            != adaptive.get("target_repository_root")
        ):
            raise SupervisionLogError(
                "Canonical adaptive target repository root is immutable"
            )
        if (
            requested["adaptive_target_class"] is not None
            or requested["adaptive_target_repository_root"] is not None
        ) and not evidence_values:
            raise SupervisionLogError(
                "An adaptive target or repository-root change requires exact operator or review evidence"
            )
        if (
            requested["adaptive_target_repository_root"] is not None
            and adaptive.get("target_repository_root") is None
        ):
            contract = implementation_range_contract(policy)
            if contract is None:
                raise SupervisionLogError(
                    "Adaptive repository-root migration requires a canonical implementation range"
                )
            validate_implementation_range_contract(contract)
            candidate_root = adaptive_git_top_level(
                str(Path(requested["adaptive_target_repository_root"]).resolve(strict=True))
            )
            tracker_path, tracker_sha, tracker_structure, _blocks = (
                implementation_tracker_snapshot(str(contract["tracker_path"]))
            )
            try:
                tracker_path.relative_to(candidate_root)
            except ValueError as exc:
                raise SupervisionLogError(
                    "Adaptive repository-root migration does not own the canonical tracker"
                ) from exc
            if (
                tracker_sha != contract["tracker_sha256"]
                or tracker_structure != contract["tracker_structure_sha256"]
            ):
                raise SupervisionLogError(
                    "Adaptive repository-root migration tracker is stale"
                )
        budget_updates = {
            "max_active_lanes_per_decision": requested["candidate_max_active_lanes"],
            "max_active_lanes_per_target": requested["candidate_max_active_lanes"],
            "max_files": requested["candidate_max_files"],
            "max_changed_lines": requested["candidate_max_changed_lines"],
            "max_commands": requested["candidate_max_commands"],
            "max_elapsed_minutes": requested["candidate_max_elapsed_minutes"],
            "max_mapped_comparisons": requested["candidate_max_mapped_comparisons"],
            "max_review_passes": requested["candidate_max_review_passes"],
        }
        for key, value in budget_updates.items():
            if value is not None:
                budget[key] = int(value)
        replacement = adaptive_decision_control_contract(
            str(mode),
            candidate_budget=budget,
            target_class=str(target_class),
            target_repository_root=(
                str(Path(str(target_repository_root)).resolve(strict=True))
                if target_repository_root is not None
                else None
            ),
        )
        validate_adaptive_decision_control(replacement)
        if replacement != policy["adaptive_decision_control"]:
            policy["adaptive_decision_control"] = replacement
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


ADAPTIVE_CANDIDATE_USAGE_FIELDS = {
    "active_lanes_for_decision",
    "active_lanes_for_target",
    "files",
    "changed_lines",
    "commands",
    "elapsed_minutes",
    "mapped_comparisons",
    "review_passes",
}


def validate_adaptive_candidate_usage(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != ADAPTIVE_CANDIDATE_USAGE_FIELDS:
        raise SupervisionLogError("Adaptive candidate usage shape differs")
    result: dict[str, int] = {}
    for field, item in value.items():
        if type(item) is not int or item < 0:
            raise SupervisionLogError(f"Adaptive candidate usage {field} is invalid")
        result[field] = item
    return result


def adaptive_candidate_decision_basis(
    decision_evidence: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "block_number": decision_evidence["block_number"],
        "block_contract_root": decision_evidence["block_contract_root"],
        "capability_frame_root": decision_evidence["capability_frame_root"],
        "target_repository_root": decision_evidence["target_repository_root"],
        "target_revision_root": decision_evidence["target_revision_root"],
        "decision_target_state_root": decision_evidence["decision_target_state_root"],
        "affected_scope": decision_evidence["affected_scope"],
        "protected_capability_root": decision_evidence["protected_capability_root"],
    }


def reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SupervisionLogError(f"Duplicate JSON key is not allowed: {key}")
        result[key] = value
    return result


def validate_exact_json_value(value: Any) -> None:
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        if unicodedata.normalize("NFC", value) != value:
            raise SupervisionLogError("Canonical JSON contains a non-NFC string")
        return
    if isinstance(value, list):
        for item in value:
            validate_exact_json_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str or unicodedata.normalize("NFC", key) != key:
                raise SupervisionLogError("Canonical JSON contains a non-NFC key")
            validate_exact_json_value(item)
        return
    raise SupervisionLogError("Canonical JSON permits only null, booleans, integers, strings, arrays, and objects")


def load_bounded_canonical_json(
    path_value: str, *, label: str, maximum_bytes: int
) -> dict[str, Any]:
    source = Path(path_value).expanduser()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        before_path = source.lstat()
        if not stat.S_ISREG(before_path.st_mode):
            raise SupervisionLogError(f"{label.title()} must be a regular file")
        if before_path.st_size > maximum_bytes:
            raise SupervisionLogError(f"{label.title()} exceeds its byte bound")
        descriptor = os.open(source, flags)
        before = file_snapshot(os.fstat(descriptor))
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(maximum_bytes + 1)
            after = file_snapshot(os.fstat(handle.fileno()))
        if before != after or path_snapshot(source) != before:
            raise SupervisionLogError(f"{label.title()} changed while reading")
    except OSError as exc:
        raise SupervisionLogError(f"{label.title()} cannot be read safely") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > maximum_bytes:
        raise SupervisionLogError(f"{label.title()} exceeds its byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=reject_duplicate_json_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisionLogError(f"{label.title()} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SupervisionLogError(f"{label.title()} must be a JSON object")
    validate_exact_json_value(value)
    if raw != canonical(value) + b"\n":
        raise SupervisionLogError(f"{label.title()} is not exact canonical JSON")
    return value


ADAPTIVE_DECISION_SOURCE_CLASSES = {
    "direct-user",
    "system",
    "repository",
    "tracker",
    "observed-outcome",
    "validation",
    "independent-review",
    "independent-evaluation",
}


def adaptive_scope_entry(value: Any, *, label: str) -> dict[str, str]:
    expected = {"owner_id", "path", "content_root"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SupervisionLogError(f"{label.title()} shape differs")
    if type(value.get("owner_id")) is not str:
        raise SupervisionLogError(f"{label.title()} owner must be a string")
    owner_id = safe_id(str(value["owner_id"]), label=f"{label} owner")
    path_value = value.get("path")
    if type(path_value) is not str or not path_value.startswith("/"):
        raise SupervisionLogError(f"{label.title()} path must be absolute")
    path_parts = Path(path_value).parts
    if "." in path_parts or ".." in path_parts:
        raise SupervisionLogError(f"{label.title()} path must be normalized")
    content_root = value.get("content_root")
    if type(content_root) is not str:
        raise SupervisionLogError(f"{label.title()} content root must be a string")
    exact_sha256(content_root, label=f"{label} content root")
    return {"owner_id": owner_id, "path": path_value, "content_root": content_root}


def adaptive_git_top_level(repository_root: str) -> Path:
    root = Path(repository_root)
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise SupervisionLogError("Adaptive target repository is unavailable") from exc
    if resolved != root or root == Path("/") or not root.is_dir():
        raise SupervisionLogError("Adaptive target repository root is not canonical")
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    if result.returncode != 0:
        raise SupervisionLogError("Adaptive target repository is not a Git worktree")
    try:
        top = Path(result.stdout.strip()).resolve(strict=True)
    except OSError as exc:
        raise SupervisionLogError("Adaptive Git top level is unavailable") from exc
    if top != root:
        raise SupervisionLogError("Adaptive target repository is not the exact Git top level")
    return root


def adaptive_git_revision(repository_root: str) -> str:
    root = adaptive_git_top_level(repository_root)
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise SupervisionLogError("Adaptive target revision is not a current Git commit")
    return revision


def adaptive_git_commit_time(
    repository_root: str, revision: str
) -> dt.datetime:
    root = adaptive_git_top_level(repository_root)
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise SupervisionLogError("Adaptive target revision is not an exact Git commit")
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "show", "-s", "--format=%ct", revision],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    timestamp = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9]+", timestamp) is None:
        raise SupervisionLogError("Adaptive target revision time is unavailable")
    try:
        return dt.datetime.fromtimestamp(int(timestamp), tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise SupervisionLogError("Adaptive target revision time is invalid") from exc


def adaptive_path_has_symlink(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except FileNotFoundError:
            break
    return False


def adaptive_scope_content_snapshot(
    repository_root: str, path_value: str, *, target_revision_root: str
) -> tuple[str, bytes]:
    root = adaptive_git_top_level(repository_root)
    path = Path(path_value)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SupervisionLogError("Adaptive affected scope escapes the target repository") from exc
    if adaptive_path_has_symlink(root, path):
        raise SupervisionLogError("Adaptive affected scope traverses a symlink")
    if path.exists():
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            descriptor = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ADAPTIVE_CANDIDATE_EVIDENCE_BYTES:
                    raise SupervisionLogError("Adaptive affected scope is not a bounded regular file")
                with os.fdopen(descriptor, "rb") as handle:
                    descriptor = -1
                    content = handle.read(MAX_ADAPTIVE_CANDIDATE_EVIDENCE_BYTES + 1)
                    after = os.fstat(handle.fileno())
                if file_snapshot(before) != file_snapshot(after) or path_snapshot(resolved) != file_snapshot(after):
                    raise SupervisionLogError("Adaptive affected file changed while reading")
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        except OSError as exc:
            raise SupervisionLogError("Adaptive affected file cannot be read safely") from exc
        if len(content) > MAX_ADAPTIVE_CANDIDATE_EVIDENCE_BYTES:
            raise SupervisionLogError("Adaptive affected file exceeds its byte bound")
        return hashlib.sha256(content).hexdigest(), content
    parent = path.parent
    try:
        resolved_parent = parent.resolve(strict=True)
        resolved_parent.relative_to(root)
    except (OSError, ValueError) as exc:
        raise SupervisionLogError("Adaptive planned file parent is not current") from exc
    if adaptive_path_has_symlink(root, parent):
        raise SupervisionLogError("Adaptive planned file parent traverses a symlink")
    return (
        digest(
            {
                "path": str(path),
                "posture": "planned-new-file",
                "target_revision_root": target_revision_root,
            }
        ),
        b"",
    )


def adaptive_scope_content_root(
    repository_root: str, path_value: str, *, target_revision_root: str
) -> str:
    return adaptive_scope_content_snapshot(
        repository_root,
        path_value,
        target_revision_root=target_revision_root,
    )[0]


def adaptive_tracker_block_context(
    policy: Mapping[str, Any], block_number: int
) -> tuple[dict[str, Any], Path, str, dict[str, Any]]:
    contract = implementation_range_contract(policy)
    if contract is None:
        raise SupervisionLogError("Adaptive decision requires a canonical implementation range")
    validate_implementation_range_contract(contract)
    tracker_path, tracker_sha, tracker_structure, blocks = implementation_tracker_snapshot(
        str(contract["tracker_path"])
    )
    if (
        tracker_sha != contract["tracker_sha256"]
        or tracker_structure != contract["tracker_structure_sha256"]
        or sorted(blocks) != contract["tracker_blocks"]
    ):
        raise SupervisionLogError("Adaptive decision tracker is stale for the canonical range")
    block = blocks.get(block_number)
    if block is None:
        raise SupervisionLogError("Adaptive decision Block is outside the canonical tracker")
    if SHA256.fullmatch(str(block.get("capability_frame_sha256", ""))) is None:
        raise SupervisionLogError("Adaptive decision Block lacks a canonical capability frame")
    requested = (
        set(contract["tracker_blocks"])
        if contract["range_intent"] == "full-tracker"
        else set(contract["explicit_blocks"])
    )
    if block_number not in requested:
        raise SupervisionLogError("Adaptive decision Block is outside the requested range")
    repository_root = adaptive_git_top_level(
        str(policy["adaptive_decision_control"]["target_repository_root"])
    )
    try:
        tracker_path.relative_to(repository_root)
    except ValueError as exc:
        raise SupervisionLogError(
            "Adaptive canonical tracker is outside the target repository"
        ) from exc
    return contract, tracker_path, tracker_sha, block


def adaptive_changed_line_count(before: bytes, after: bytes) -> int:
    try:
        before_lines = before.decode("utf-8").splitlines()
        after_lines = after.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SupervisionLogError("Adaptive candidate artifacts must be UTF-8") from exc
    changes = 0
    for line in difflib.ndiff(before_lines, after_lines):
        if line.startswith("- ") or line.startswith("+ "):
            changes += 1
    return changes


ADAPTIVE_COMPARISON_DIMENSIONS = (
    "correctness",
    "protected-capability",
    "maintainability",
    "performance",
    "compatibility",
    "reversibility",
)
ADAPTIVE_COMPARISON_RELATIONS = {
    "candidate-better",
    "incumbent-better",
    "equivalent",
    "inconclusive",
}


def adaptive_candidate_acceptance_material(value: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {
        "decision_id",
        "acceptance_root",
        "acceptance_signature_base64",
        "currentness_root",
        "evidence_root",
    }
    return {key: item for key, item in value.items() if key not in excluded}


def verify_adaptive_candidate_acceptance(value: Mapping[str, Any]) -> None:
    if value.get("acceptance_authority_id") != ADAPTIVE_EVALUATOR_ID:
        raise SupervisionLogError("Adaptive candidate acceptance authority differs")
    if value.get("acceptance_authority_key_sha256") != ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256:
        raise SupervisionLogError("Adaptive candidate acceptance key differs")
    material = adaptive_candidate_acceptance_material(value)
    if value.get("acceptance_root") != digest(material):
        raise SupervisionLogError("Adaptive candidate acceptance root differs")
    signature_value = value.get("acceptance_signature_base64")
    if type(signature_value) is not str:
        raise SupervisionLogError("Adaptive candidate acceptance signature is required")
    try:
        signature = base64.b64decode(signature_value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SupervisionLogError("Adaptive candidate acceptance signature is invalid") from exc
    if len(signature) != 64:
        raise SupervisionLogError("Adaptive candidate acceptance signature length differs")
    key_bytes = trusted_adaptive_evaluator_key()
    openssl = trusted_adaptive_review_openssl()
    signed = {**material, "acceptance_root": value["acceptance_root"]}
    with tempfile.TemporaryDirectory(prefix="adaptive-candidate-verify-") as temp_value:
        temp = Path(temp_value)
        content = temp / "candidate.json"
        signature_path = temp / "candidate.sig"
        key_path = temp / "evaluator.pem"
        content.write_bytes(canonical(signed))
        signature_path.write_bytes(signature)
        key_path.write_bytes(key_bytes)
        result = subprocess.run(
            [
                str(openssl),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(key_path),
                "-rawin",
                "-in",
                str(content),
                "-sigfile",
                str(signature_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    if result.returncode != 0:
        raise SupervisionLogError("Adaptive candidate acceptance signature is invalid")


def adaptive_candidate_retained_evidence(
    value: Mapping[str, Any], *, decision_evidence: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    repository_root = str(decision_evidence["target_repository_root"])
    target_revision_root = str(decision_evidence["target_revision_root"])
    source_scope = {
        str(item["path"]): item for item in decision_evidence["affected_scope"]
    }
    artifacts = value.get("artifact_manifest")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 3:
        raise SupervisionLogError("Adaptive candidate artifact manifest differs")
    normalized_artifacts: list[dict[str, Any]] = []
    total_changed = 0
    for item in artifacts:
        if not isinstance(item, Mapping) or set(item) != {
            "path",
            "before_root",
            "after_root",
            "after_content_base64",
            "changed_lines",
        }:
            raise SupervisionLogError("Adaptive candidate artifact shape differs")
        path_value = item.get("path")
        if type(path_value) is not str or path_value not in source_scope:
            raise SupervisionLogError("Adaptive candidate artifact is outside the decision scope")
        before_root, before = adaptive_scope_content_snapshot(
            repository_root, path_value, target_revision_root=target_revision_root
        )
        if item.get("before_root") != before_root:
            raise SupervisionLogError("Adaptive candidate artifact source is stale")
        content_value = item.get("after_content_base64")
        if type(content_value) is not str:
            raise SupervisionLogError("Adaptive candidate artifact content is required")
        try:
            after = base64.b64decode(content_value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise SupervisionLogError("Adaptive candidate artifact content is invalid") from exc
        if len(after) > 32768 or item.get("after_root") != hashlib.sha256(after).hexdigest():
            raise SupervisionLogError("Adaptive candidate artifact root differs")
        changed_lines = adaptive_changed_line_count(before, after)
        if type(item.get("changed_lines")) is not int or item["changed_lines"] != changed_lines:
            raise SupervisionLogError("Adaptive candidate changed-line count differs")
        total_changed += changed_lines
        normalized_artifacts.append(dict(item))
    if [item["path"] for item in normalized_artifacts] != sorted(source_scope):
        raise SupervisionLogError("Adaptive candidate artifacts must cover the exact affected scope")

    commands = value.get("command_results")
    if not isinstance(commands, list) or not 1 <= len(commands) <= 6:
        raise SupervisionLogError("Adaptive candidate command results differ")
    normalized_commands: list[dict[str, Any]] = []
    prior_finish: dt.datetime | None = None
    mapped_count = 0
    for item in commands:
        if not isinstance(item, Mapping) or set(item) != {
            "command_id",
            "kind",
            "started_at",
            "finished_at",
            "exit_code",
            "result_payload",
            "result_root",
        }:
            raise SupervisionLogError("Adaptive candidate command-result shape differs")
        if type(item.get("command_id")) is not str:
            raise SupervisionLogError("Adaptive candidate command ID must be a string")
        safe_id(item["command_id"], label="adaptive candidate command ID")
        if item.get("kind") not in {"focused", "mapped", "validation"}:
            raise SupervisionLogError("Adaptive candidate command kind differs")
        started = parse_event_time(item.get("started_at"), label="candidate command start")
        finished = parse_event_time(item.get("finished_at"), label="candidate command finish")
        if finished < started or (prior_finish is not None and started < prior_finish):
            raise SupervisionLogError("Adaptive candidate command chronology differs")
        prior_finish = finished
        if type(item.get("exit_code")) is not int or item["exit_code"] != 0:
            raise SupervisionLogError("Adaptive candidate command did not pass")
        payload = item.get("result_payload")
        validate_exact_json_value(payload)
        if item.get("result_root") != digest(payload):
            raise SupervisionLogError("Adaptive candidate command result root differs")
        if item["kind"] == "mapped":
            mapped_count += 1
        normalized_commands.append(dict(item))
    if normalized_commands[0]["kind"] != "focused" or mapped_count < 1:
        raise SupervisionLogError("Adaptive candidate requires focused proof before mapped proof")

    comparisons = value.get("comparison_results")
    if not isinstance(comparisons, list) or len(comparisons) != len(ADAPTIVE_COMPARISON_DIMENSIONS):
        raise SupervisionLogError("Adaptive candidate comparison results differ")
    normalized_comparisons: list[dict[str, Any]] = []
    command_roots = {str(item["result_root"]) for item in normalized_commands}
    for expected_dimension, item in zip(ADAPTIVE_COMPARISON_DIMENSIONS, comparisons):
        if not isinstance(item, Mapping) or set(item) != {"dimension", "relation", "evidence_root"}:
            raise SupervisionLogError("Adaptive candidate comparison shape differs")
        if (
            item.get("dimension") != expected_dimension
            or item.get("relation") not in ADAPTIVE_COMPARISON_RELATIONS
            or item.get("evidence_root") not in command_roots
        ):
            raise SupervisionLogError("Adaptive candidate comparison result differs")
        normalized_comparisons.append(dict(item))

    started_at = parse_event_time(value.get("lane_started_at"), label="candidate lane start")
    observed_at = parse_event_time(value.get("observed_at"), label="candidate observation")
    source_committed_at = adaptive_git_commit_time(
        repository_root, str(decision_evidence["target_revision"])
    )
    current_time = dt.datetime.now(tz=dt.timezone.utc)
    first_command = parse_event_time(
        normalized_commands[0]["started_at"], label="candidate first command"
    )
    last_command = parse_event_time(
        normalized_commands[-1]["finished_at"], label="candidate last command"
    )
    if (
        started_at < source_committed_at
        or started_at > first_command
        or observed_at < last_command
        or observed_at > current_time
    ):
        raise SupervisionLogError("Adaptive candidate lane chronology differs")
    elapsed_seconds = max(0.0, (observed_at - started_at).total_seconds())
    usage = {
        "active_lanes_for_decision": 1,
        "active_lanes_for_target": 1,
        "files": len(normalized_artifacts),
        "changed_lines": total_changed,
        "commands": len(normalized_commands),
        "elapsed_minutes": int((elapsed_seconds + 59) // 60),
        "mapped_comparisons": mapped_count,
        "review_passes": 0,
    }
    return normalized_artifacts, normalized_commands, normalized_comparisons, usage


def validate_adaptive_decision_evidence(
    value: Any, *, policy: Mapping[str, Any]
) -> dict[str, Any]:
    expected = {
        "schema_version",
        "kind",
        "decision_id",
        "disposition",
        "judgment_class",
        "consequence_class",
        "reversible",
        "mission_preserving",
        "block_number",
        "block_contract_root",
        "tracker_sha256",
        "target_repository_root",
        "target_revision",
        "target_revision_root",
        "decision_target_state_root",
        "current_target_state_root",
        "capability_frame_root",
        "protected_capability_results",
        "protected_capability_root",
        "adjudicating_evidence_refs",
        "affected_scope",
        "implementation_owner_id",
        "proposer_author_id",
        "stop_boundary",
        "safe_frontier",
        "blocked_subjects",
        "revisit_trigger",
        "candidate_evidence_root",
        "evidence_manifest_root",
        "accepted_decision_head",
        "accepted_revision_head",
        "source_root",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SupervisionLogError("Adaptive decision evidence shape differs")
    if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise SupervisionLogError("Adaptive decision evidence version differs")
    if value.get("kind") != "software-factory-adaptive-decision-source":
        raise SupervisionLogError("Adaptive decision evidence kind differs")
    for field, allowed in (
        ("disposition", ADAPTIVE_DISPOSITIONS),
        ("judgment_class", ADAPTIVE_JUDGMENT_CLASSES),
        ("consequence_class", ADAPTIVE_CONSEQUENCE_CLASSES),
    ):
        if value.get(field) not in allowed:
            raise SupervisionLogError(f"Adaptive decision {field} differs")
    if type(value.get("decision_id")) is not str:
        raise SupervisionLogError("Adaptive decision ID must be a string")
    decision_id = safe_id(str(value["decision_id"]), label="adaptive decision ID")
    for field in ("reversible", "mission_preserving"):
        if type(value.get(field)) is not bool:
            raise SupervisionLogError(f"Adaptive decision {field} must be boolean")
    if type(value.get("block_number")) is not int or value["block_number"] < 0:
        raise SupervisionLogError("Adaptive decision Block number is invalid")
    for field in (
        "block_contract_root",
        "tracker_sha256",
        "target_revision_root",
        "decision_target_state_root",
        "current_target_state_root",
        "capability_frame_root",
        "protected_capability_root",
        "evidence_manifest_root",
        "source_root",
    ):
        if type(value.get(field)) is not str:
            raise SupervisionLogError(f"Adaptive decision {field} must be a string")
        exact_sha256(str(value[field]), label=f"adaptive decision {field}")
    target_revision = value.get("target_revision")
    if type(target_revision) is not str or re.fullmatch(r"[0-9a-f]{40}", target_revision) is None:
        raise SupervisionLogError("Adaptive target revision must be an exact Git commit")
    if value["target_revision_root"] != digest({"target_revision": target_revision}):
        raise SupervisionLogError("Adaptive target revision root differs")
    repository_root = value.get("target_repository_root")
    if type(repository_root) is not str or not repository_root.startswith("/"):
        raise SupervisionLogError("Adaptive target repository root must be absolute")
    root_parts = Path(repository_root).parts
    if "." in root_parts or ".." in root_parts:
        raise SupervisionLogError("Adaptive target repository root must be normalized")
    if type(value.get("implementation_owner_id")) is not str:
        raise SupervisionLogError("Adaptive implementation owner must be a string")
    implementation_owner = safe_id(
        str(value["implementation_owner_id"]), label="adaptive implementation owner"
    )
    if implementation_owner != policy.get("target_thread_id"):
        raise SupervisionLogError("Adaptive implementation owner differs from target owner")
    proposer = value.get("proposer_author_id")
    if proposer is not None:
        if type(proposer) is not str:
            raise SupervisionLogError("Adaptive proposer must be a string or null")
        proposer = safe_id(proposer, label="adaptive proposer")
    control = policy.get("adaptive_decision_control")
    legacy_control = control is None
    if not isinstance(control, Mapping):
        control = adaptive_decision_control_contract("fixed")
    validate_adaptive_decision_control(control)
    target_class = str(control["target_class"])
    bound_repository_root = control.get("target_repository_root")
    if bound_repository_root is None and not legacy_control:
        raise SupervisionLogError(
            "Adaptive target repository root is not bound in canonical policy"
        )
    if bound_repository_root is not None and repository_root != bound_repository_root:
        raise SupervisionLogError(
            "Adaptive target repository root differs from canonical policy"
        )
    if bound_repository_root is not None:
        _contract, _tracker_path, tracker_sha, block = adaptive_tracker_block_context(
            policy, int(value["block_number"])
        )
        if value["tracker_sha256"] != tracker_sha:
            raise SupervisionLogError("Adaptive tracker root differs from canonical tracker")
        if value["block_contract_root"] != block["contract_sha256"]:
            raise SupervisionLogError("Adaptive Block contract root differs from canonical tracker")
        if value["capability_frame_root"] != block["capability_frame_sha256"]:
            raise SupervisionLogError("Adaptive capability frame differs from canonical tracker")
        current_revision = adaptive_git_revision(repository_root)
        if target_revision != current_revision:
            raise SupervisionLogError("Adaptive target revision is stale")
    if value["disposition"] == "continue-unchanged" and proposer is not None:
        raise SupervisionLogError("Unchanged decision cannot claim a proposer")
    if target_class == "software-factory" and value["disposition"] != "continue-unchanged":
        canonical_proposer = policy.get("runtime", {}).get("base_reviewer_thread_id")
        if proposer is None or proposer != canonical_proposer or proposer == implementation_owner:
            raise SupervisionLogError(
                "Software Factory mutation requires its canonical distinct proposer"
            )
    elif target_class == "target-repository" and proposer is not None:
        raise SupervisionLogError("Target-repository decision cannot claim a Factory proposer")
    evidence_refs = value.get("adjudicating_evidence_refs")
    if not isinstance(evidence_refs, list) or not 1 <= len(evidence_refs) <= 32:
        raise SupervisionLogError("Adaptive adjudicating evidence differs")
    evidence_ids: list[str] = []
    for item in evidence_refs:
        if not isinstance(item, Mapping) or set(item) != {
            "ref_id",
            "source_class",
            "root_sha256",
        }:
            raise SupervisionLogError("Adaptive adjudicating evidence shape differs")
        if type(item.get("ref_id")) is not str:
            raise SupervisionLogError("Adaptive evidence ref ID must be a string")
        ref_id = safe_id(str(item["ref_id"]), label="adaptive evidence ref ID")
        if ref_id in evidence_ids or item.get("source_class") not in ADAPTIVE_DECISION_SOURCE_CLASSES:
            raise SupervisionLogError("Adaptive adjudicating evidence differs")
        if type(item.get("root_sha256")) is not str:
            raise SupervisionLogError("Adaptive evidence root must be a string")
        exact_sha256(str(item["root_sha256"]), label="adaptive evidence root")
        evidence_ids.append(ref_id)
    if evidence_ids != sorted(evidence_ids):
        raise SupervisionLogError("Adaptive adjudicating evidence must be ID-sorted")
    protected_results = value.get("protected_capability_results")
    if not isinstance(protected_results, list) or not 1 <= len(protected_results) <= 32:
        raise SupervisionLogError("Adaptive protected capability results differ")
    capability_ids: list[str] = []
    for item in protected_results:
        if not isinstance(item, Mapping) or set(item) != {
            "capability_id",
            "result",
            "evidence_ref_ids",
        }:
            raise SupervisionLogError("Adaptive protected capability result shape differs")
        if type(item.get("capability_id")) is not str:
            raise SupervisionLogError("Adaptive protected capability ID must be a string")
        capability_id = safe_id(
            str(item["capability_id"]), label="adaptive protected capability ID"
        )
        refs = item.get("evidence_ref_ids")
        if (
            capability_id in capability_ids
            or item.get("result") not in {"preserved", "regressed", "unverified"}
            or not isinstance(refs, list)
            or not refs
            or refs != sorted(set(refs))
            or any(type(ref) is not str or ref not in evidence_ids for ref in refs)
        ):
            raise SupervisionLogError("Adaptive protected capability result differs")
        capability_ids.append(capability_id)
    if capability_ids != sorted(capability_ids):
        raise SupervisionLogError("Adaptive protected capabilities must be ID-sorted")
    if value["protected_capability_root"] != digest(protected_results):
        raise SupervisionLogError("Adaptive protected capability root differs")
    if value["evidence_manifest_root"] != digest(evidence_refs):
        raise SupervisionLogError("Adaptive evidence manifest root differs")
    affected = value.get("affected_scope")
    if not isinstance(affected, list) or not 1 <= len(affected) <= 32:
        raise SupervisionLogError("Adaptive affected scope differs")
    normalized_scope = [
        adaptive_scope_entry(item, label="adaptive affected scope") for item in affected
    ]
    if any(item["owner_id"] != implementation_owner for item in normalized_scope):
        raise SupervisionLogError("Adaptive affected scope has a different owner")
    actual_scope_roots: list[str] = []
    for item in normalized_scope:
        actual_root = adaptive_scope_content_root(
            repository_root,
            item["path"],
            target_revision_root=str(value["target_revision_root"]),
        )
        if item["content_root"] != actual_root:
            raise SupervisionLogError("Adaptive affected scope content is stale")
        actual_scope_roots.append(actual_root)
    expected_scope_order = sorted(
        normalized_scope, key=lambda item: (item["owner_id"], item["path"], item["content_root"])
    )
    if normalized_scope != expected_scope_order:
        raise SupervisionLogError("Adaptive affected scope must be canonically sorted")
    current_target_state_root = digest(
        {
            "target_revision_root": value["target_revision_root"],
            "affected_scope": normalized_scope,
        }
    )
    if (
        value["decision_target_state_root"] != current_target_state_root
        or value["current_target_state_root"] != current_target_state_root
    ):
        raise SupervisionLogError("Adaptive target state root is stale")
    evidence_roots = {str(item["root_sha256"]) for item in evidence_refs}
    required_evidence_roots = {
        value["tracker_sha256"],
        value["block_contract_root"],
        value["capability_frame_root"],
        value["target_revision_root"],
        *actual_scope_roots,
    }
    if not required_evidence_roots.issubset(evidence_roots):
        raise SupervisionLogError("Adaptive evidence does not cover the canonical source state")
    capability_id = f"block-{value['block_number']}-capability-frame"
    capability_frame_refs = {
        str(item["ref_id"])
        for item in evidence_refs
        if item["root_sha256"] == value["capability_frame_root"]
    }
    canonical_capability = next(
        (item for item in protected_results if item["capability_id"] == capability_id),
        None,
    )
    if (
        canonical_capability is None
        or canonical_capability["result"] != "preserved"
        or not capability_frame_refs.intersection(canonical_capability["evidence_ref_ids"])
    ):
        raise SupervisionLogError(
            "Adaptive protected results omit the canonical Block capability frame"
        )
    for field in ("stop_boundary", "revisit_trigger"):
        if type(value.get(field)) is not str:
            raise SupervisionLogError(f"Adaptive decision {field} must be a string")
        clean(str(value[field]), label=f"adaptive decision {field}", maximum=240)
    for field in ("safe_frontier", "blocked_subjects"):
        items = value.get(field)
        if (
            not isinstance(items, list)
            or len(items) > 16
            or any(type(item) is not str or not clean(item, label=field, maximum=160) for item in items)
            or items != sorted(set(items))
        ):
            raise SupervisionLogError(f"Adaptive decision {field} differs")
    candidate_root = value.get("candidate_evidence_root")
    candidate_disposition = value["disposition"] in {"compare-candidate", "cutover-candidate"}
    if candidate_disposition != (candidate_root is not None):
        raise SupervisionLogError("Adaptive candidate root does not match disposition")
    if candidate_root is not None:
        if type(candidate_root) is not str:
            raise SupervisionLogError("Adaptive candidate evidence root must be a string")
        exact_sha256(candidate_root, label="adaptive candidate evidence root")
    if (
        value.get("accepted_decision_head") is not None
        or value.get("accepted_revision_head") is not None
    ):
        raise SupervisionLogError(
            "Adaptive accepted heads must be derived by the canonical owner"
        )
    material = dict(value)
    material.pop("source_root")
    if value["source_root"] != digest(material):
        raise SupervisionLogError("Adaptive decision source root differs")
    return dict(value)


def load_adaptive_decision_evidence(
    path_value: str, *, policy: Mapping[str, Any]
) -> dict[str, Any]:
    return validate_adaptive_decision_evidence(
        load_bounded_canonical_json(
            path_value,
            label="adaptive decision evidence",
            maximum_bytes=MAX_ADAPTIVE_DECISION_EVIDENCE_BYTES,
        ),
        policy=policy,
    )


def validate_adaptive_candidate_evidence(
    value: Any,
    *,
    decision_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    decision_id = str(decision_evidence["decision_id"])
    implementation_owner_id = str(decision_evidence["implementation_owner_id"])
    expected = {
        "schema_version",
        "kind",
        "decision_id",
        "owner_id",
        "source_revision_root",
        "decision_basis_root",
        "lane_started_at",
        "observed_at",
        "artifact_manifest",
        "command_results",
        "comparison_results",
        "candidate_root",
        "candidate_budget_use",
        "candidate_budget_use_root",
        "protected_capability_results",
        "protected_capability_root",
        "validation_root",
        "comparison_root",
        "acceptance_authority_id",
        "acceptance_authority_key_sha256",
        "acceptance_root",
        "acceptance_signature_base64",
        "currentness_root",
        "evidence_root",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SupervisionLogError("Adaptive candidate evidence shape differs")
    if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise SupervisionLogError("Adaptive candidate evidence version differs")
    if value.get("kind") != "software-factory-adaptive-candidate-evidence":
        raise SupervisionLogError("Adaptive candidate evidence kind differs")
    if value.get("decision_id") != decision_id:
        raise SupervisionLogError("Adaptive candidate evidence identity differs")
    if type(value.get("owner_id")) is not str:
        raise SupervisionLogError("Adaptive candidate owner ID must be a string")
    safe_id(str(value["owner_id"]), label="adaptive candidate owner ID")
    if value["owner_id"] != implementation_owner_id:
        raise SupervisionLogError("Adaptive candidate owner differs from implementation owner")
    if type(value.get("source_revision_root")) is not str:
        raise SupervisionLogError("Adaptive candidate source revision root is required")
    exact_sha256(
        str(value["source_revision_root"]), label="adaptive candidate source revision root"
    )
    if value["source_revision_root"] != decision_evidence["target_revision_root"]:
        raise SupervisionLogError(
            "Adaptive candidate source revision differs from the decision target"
        )
    if type(value.get("decision_basis_root")) is not str:
        raise SupervisionLogError("Adaptive candidate decision basis root is required")
    exact_sha256(value["decision_basis_root"], label="adaptive candidate decision basis root")
    if value["decision_basis_root"] != digest(
        adaptive_candidate_decision_basis(decision_evidence)
    ):
        raise SupervisionLogError(
            "Adaptive candidate decision basis differs from the canonical decision"
        )
    for field in (
        "candidate_root",
        "candidate_budget_use_root",
        "protected_capability_root",
        "validation_root",
        "comparison_root",
        "acceptance_authority_key_sha256",
        "acceptance_root",
        "currentness_root",
        "evidence_root",
    ):
        if type(value.get(field)) is not str:
            raise SupervisionLogError(f"Adaptive candidate {field} must be a string")
        exact_sha256(str(value[field]), label=f"adaptive candidate {field}")
    artifacts, commands, comparisons, derived_usage = adaptive_candidate_retained_evidence(
        value, decision_evidence=decision_evidence
    )
    usage = validate_adaptive_candidate_usage(value["candidate_budget_use"])
    if usage != derived_usage:
        raise SupervisionLogError("Adaptive candidate usage is not derived from retained evidence")
    if usage["review_passes"] != 0:
        raise SupervisionLogError(
            "Candidate evidence cannot self-assert an independent review pass"
        )
    if value["candidate_budget_use_root"] != digest(usage):
        raise SupervisionLogError("Adaptive candidate usage root differs")
    if value["candidate_root"] != digest(artifacts):
        raise SupervisionLogError("Adaptive candidate artifact root differs")
    if value["validation_root"] != digest(commands):
        raise SupervisionLogError("Adaptive candidate validation root differs")
    if value["comparison_root"] != digest(comparisons):
        raise SupervisionLogError("Adaptive candidate comparison root differs")
    protected = value["protected_capability_results"]
    if not isinstance(protected, list) or not 1 <= len(protected) <= 32:
        raise SupervisionLogError("Adaptive protected-capability evidence differs")
    source_protected = {
        str(item["capability_id"]): item
        for item in decision_evidence["protected_capability_results"]
    }
    seen: set[str] = set()
    for item in protected:
        if not isinstance(item, Mapping) or set(item) != {
            "capability_id",
            "result",
            "evidence_root",
        }:
            raise SupervisionLogError("Adaptive protected-capability result differs")
        if type(item.get("capability_id")) is not str:
            raise SupervisionLogError("Protected capability ID must be a string")
        capability_id = safe_id(
            str(item["capability_id"]), label="protected capability ID"
        )
        if capability_id in seen or item.get("result") not in {
            "preserved",
            "regressed",
            "unverified",
        }:
            raise SupervisionLogError("Adaptive protected-capability result differs")
        seen.add(capability_id)
        if type(item.get("evidence_root")) is not str:
            raise SupervisionLogError("Protected-capability evidence root must be a string")
        exact_sha256(
            str(item["evidence_root"]), label="protected-capability evidence root"
        )
        source_item = source_protected.get(capability_id)
        if source_item is None or item["evidence_root"] != digest(
            {
                "capability_id": capability_id,
                "result": item["result"],
                "source_contract_root": digest(source_item),
                "candidate_root": value["candidate_root"],
                "validation_root": value["validation_root"],
            }
        ):
            raise SupervisionLogError(
                "Adaptive protected-capability evidence does not bind the decision contract"
            )
    candidate_capability_ids = [str(item["capability_id"]) for item in protected]
    if candidate_capability_ids != sorted(candidate_capability_ids) or seen != set(source_protected):
        raise SupervisionLogError(
            "Adaptive candidate protected capabilities differ from the decision contract"
        )
    if value["protected_capability_root"] != digest(protected):
        raise SupervisionLogError("Adaptive protected-capability root differs")
    currentness_material = {
        "owner_id": value["owner_id"],
        "source_revision_root": value["source_revision_root"],
        "decision_basis_root": value["decision_basis_root"],
        "candidate_root": value["candidate_root"],
        "candidate_budget_use_root": value["candidate_budget_use_root"],
        "protected_capability_root": value["protected_capability_root"],
        "validation_root": value["validation_root"],
        "comparison_root": value["comparison_root"],
        "acceptance_root": value["acceptance_root"],
    }
    if value["currentness_root"] != digest(currentness_material):
        raise SupervisionLogError("Adaptive candidate currentness root differs")
    evidence_material = dict(value)
    evidence_material.pop("evidence_root")
    evidence_material.pop("decision_id")
    evidence_material.pop("acceptance_signature_base64")
    if value["evidence_root"] != digest(evidence_material):
        raise SupervisionLogError("Adaptive candidate evidence root differs")
    verify_adaptive_candidate_acceptance(value)
    return dict(value)


def load_adaptive_candidate_evidence(
    path_value: str,
    *,
    decision_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    value = load_bounded_canonical_json(
        path_value,
        label="adaptive candidate evidence",
        maximum_bytes=MAX_ADAPTIVE_CANDIDATE_EVIDENCE_BYTES,
    )
    return validate_adaptive_candidate_evidence(
        value,
        decision_evidence=decision_evidence,
    )


def _adaptive_decision_posture(
    policy: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    active_candidate_fingerprints: Sequence[str],
) -> dict[str, Any]:
    expected_packet_fields = {
        "decision_evidence",
        "candidate_evidence",
        "independent_review",
        "request_human_input",
        "governing_event_head_root",
    }
    if set(packet) != expected_packet_fields:
        raise SupervisionLogError("Adaptive decision packet shape differs")
    if type(packet["request_human_input"]) is not bool:
        raise SupervisionLogError("Adaptive decision human-request posture must be boolean")
    if (
        any(
            type(item) is not str or SHA256.fullmatch(item) is None
            for item in active_candidate_fingerprints
        )
        or list(active_candidate_fingerprints)
        != sorted(set(active_candidate_fingerprints))
    ):
        raise SupervisionLogError("Adaptive active-candidate frontier differs")
    evidence = validate_adaptive_decision_evidence(
        packet["decision_evidence"], policy=policy
    )
    decision_id = str(evidence["decision_id"])
    disposition = str(evidence["disposition"])
    judgment_class = str(evidence["judgment_class"])
    consequence_class = str(evidence["consequence_class"])
    revisit_trigger = str(evidence["revisit_trigger"])
    control = policy.get("adaptive_decision_control")
    legacy = control is None
    if legacy:
        control = adaptive_decision_control_contract("fixed")
    if not isinstance(control, Mapping):
        raise SupervisionLogError("Adaptive-decision policy is malformed")
    validate_adaptive_decision_control(control)
    mode = str(control["adaptive_decision_mode"])
    target_class = str(control["target_class"])
    effect_class = adaptive_effect_class(target_class, str(disposition))
    mission = bound_mission(dict(policy))
    mission_root = (
        str(mission["mission_root"])
        if mission is not None
        else str(policy.get("policy_sha256", ""))
    )
    fingerprint_material = {
        "schema_version": 1,
        "mission_root": mission_root,
        "authority_effect": "mission-preserving" if evidence["mission_preserving"] else "goal-change",
        "block_number": evidence["block_number"],
        "block_contract_root": evidence["block_contract_root"],
        "tracker_sha256": evidence["tracker_sha256"],
        "target_class": target_class,
        "target_repository_root": evidence["target_repository_root"],
        "decision_target_state_root": evidence["decision_target_state_root"],
        "capability_frame_root": evidence["capability_frame_root"],
        "protected_capability_root": evidence["protected_capability_root"],
        "adjudicating_evidence_refs": evidence["adjudicating_evidence_refs"],
        "affected_scope": evidence["affected_scope"],
        "proposer_author_id": evidence["proposer_author_id"],
        "implementation_owner_id": evidence["implementation_owner_id"],
        "stop_boundary": evidence["stop_boundary"],
        "disposition": disposition,
        "candidate_evidence_root": evidence["candidate_evidence_root"],
    }
    decision_fingerprint = digest(fingerprint_material)
    budget = control["candidate_budget"]
    source_protected_regression = any(
        item["result"] != "preserved"
        for item in evidence["protected_capability_results"]
    )
    candidate_disposition = disposition in {"compare-candidate", "cutover-candidate"}
    candidate = packet["candidate_evidence"]
    if candidate_disposition:
        candidate = validate_adaptive_candidate_evidence(
            candidate,
            decision_evidence=evidence,
        )
        if candidate["evidence_root"] != evidence["candidate_evidence_root"]:
            raise SupervisionLogError("Adaptive candidate differs from decision evidence")
        usage = validate_adaptive_candidate_usage(candidate["candidate_budget_use"])
        protected_regression = source_protected_regression or any(
            item["result"] != "preserved"
            for item in candidate["protected_capability_results"]
        )
        other_active = set(active_candidate_fingerprints) - {decision_fingerprint}
        if other_active:
            raise SupervisionLogError(
                "Adaptive target already has a different active candidate lane"
            )
        usage["active_lanes_for_decision"] = 1
        usage["active_lanes_for_target"] = 1
    else:
        if candidate is not None:
            raise SupervisionLogError("Candidate evidence requires a candidate disposition")
        usage = {field: 0 for field in ADAPTIVE_CANDIDATE_USAGE_FIELDS}
        protected_regression = source_protected_regression
    review = packet["independent_review"]
    event_head_root = packet["governing_event_head_root"]
    if event_head_root is not None:
        if type(event_head_root) is not str:
            raise SupervisionLogError("Adaptive governing event head must be a string or null")
        exact_sha256(event_head_root, label="adaptive governing event head")
    pre_review_currentness = digest(
        {
            "decision_fingerprint": decision_fingerprint,
            "evidence_manifest_root": evidence["evidence_manifest_root"],
            "tracker_sha256": evidence["tracker_sha256"],
            "policy_root": policy.get("policy_sha256"),
            "event_head_root": event_head_root,
            "target_revision": evidence["target_revision"],
            "target_revision_root": evidence["target_revision_root"],
            "current_target_state_root": evidence["current_target_state_root"],
            "safe_frontier": evidence["safe_frontier"],
            "adaptive_decision_mode": mode,
            "accepted_decision_head": evidence["accepted_decision_head"],
            "accepted_revision_head": evidence["accepted_revision_head"],
            "revisit_trigger": revisit_trigger,
            "candidate_currentness_root": candidate.get("currentness_root") if candidate else None,
            "review_root": None,
            "review_disposition": None,
            "evaluator_id": None,
            "evaluation_evidence_root": None,
            "evaluator_authority_key_sha256": None,
            "evaluation_root": None,
            "evaluation_disposition": None,
        }
    )
    semantics_material = {
        "decision_fingerprint": decision_fingerprint,
        "decision_currentness_root": pre_review_currentness,
        "disposition": disposition,
        "judgment_class": judgment_class,
        "consequence_class": consequence_class,
        "reversible": evidence["reversible"],
        "mission_preserving": evidence["mission_preserving"],
        "target_class": target_class,
        "effect_class": effect_class,
        "candidate_evidence_root": candidate.get("evidence_root") if candidate else None,
        "candidate_owner_id": candidate.get("owner_id") if candidate else None,
        "blocked_subjects": evidence["blocked_subjects"],
        "safe_frontier": evidence["safe_frontier"],
        "revisit_trigger": revisit_trigger,
        "policy_sha256": policy.get("policy_sha256"),
    }
    decision_semantics_root = digest(semantics_material)
    if review is not None:
        expected_candidate_root = candidate.get("evidence_root") if candidate else None
        review_source = {
            "record_id": review.get("source_decision_record"),
            "record_sha256": review.get("source_decision_sha256"),
            "decision_id": decision_id,
            "decision_fingerprint": decision_fingerprint,
            "decision_currentness_root": pre_review_currentness,
            "decision_semantics_root": decision_semantics_root,
            "disposition": disposition,
            "target_class": target_class,
            "effect_class": effect_class,
            "candidate_evidence_root": expected_candidate_root,
            "candidate_owner_id": candidate.get("owner_id") if candidate else None,
            "proposer_author_id": evidence["proposer_author_id"],
            "implementation_owner_id": evidence["implementation_owner_id"],
        }
        review = validate_external_adaptive_review(
            review, source=review_source, policy=policy
        )
        if (
            review["decision_id"] != decision_id
            or review["decision_fingerprint"] != decision_fingerprint
            or review["decision_currentness_root"] != pre_review_currentness
            or review["decision_semantics_root"] != decision_semantics_root
            or review["disposition"] != disposition
            or review["target_class"] != target_class
            or review["effect_class"] != effect_class
            or review["candidate_evidence_root"] != expected_candidate_root
            or review["candidate_owner_id"]
            != (candidate.get("owner_id") if candidate else None)
            or review["proposer_author_id"] != evidence["proposer_author_id"]
            or review["implementation_owner_id"] != evidence["implementation_owner_id"]
        ):
            raise SupervisionLogError(
                "Adaptive review does not bind the current decision and candidate"
            )
        if review["reviewer_id"] in {
            evidence["implementation_owner_id"],
            evidence["proposer_author_id"],
            candidate.get("owner_id") if candidate else None,
        }:
            raise SupervisionLogError("Adaptive review is not independently owned")
        usage["review_passes"] += 1
    budget_exceeded = any(
        (
            usage["active_lanes_for_decision"] > budget["max_active_lanes_per_decision"],
            usage["active_lanes_for_target"] > budget["max_active_lanes_per_target"],
            usage["files"] > budget["max_files"],
            usage["changed_lines"] > budget["max_changed_lines"],
            usage["commands"] > budget["max_commands"],
            usage["elapsed_minutes"] > budget["max_elapsed_minutes"],
            usage["mapped_comparisons"] > budget["max_mapped_comparisons"],
            usage["review_passes"] > budget["max_review_passes"],
        )
    )
    required_permissions = ADAPTIVE_EFFECT_PERMISSIONS[effect_class]
    permission_results = {
        field: policy.get("permissions", {}).get(field) is True
        for field in required_permissions
    }
    permission_granted = all(permission_results.values())
    review_required = bool(
        disposition in ADAPTIVE_REVIEWED_DISPOSITIONS
        or (target_class == "software-factory" and disposition != "continue-unchanged")
        or (mode == "recommend" and disposition != "continue-unchanged")
    )
    if review is not None and not review_required:
        raise SupervisionLogError("Adaptive review is not eligible for this disposition")
    review_disposition = review.get("review_disposition") if review else None
    evaluation_disposition = review.get("evaluation_disposition") if review else None
    if target_class == "software-factory" and review is not None:
        identities = {
            evidence["proposer_author_id"],
            evidence["implementation_owner_id"],
            review["reviewer_id"],
            review["evaluator_id"],
        }
        if None in identities or len(identities) != 4:
            raise SupervisionLogError(
                "Software Factory review/evaluation roles are not distinct"
            )
    review_complete = review_disposition == "accepted" and (
        target_class != "software-factory" or evaluation_disposition == "accepted"
    )
    reserved = (
        judgment_class in {"reserved-external", "material-goal-change"}
        or evidence["mission_preserving"] is not True
        or evidence["reversible"] is not True
        or (
            mode in {"reviewed-autonomous", "full-autonomous"}
            and disposition != "continue-unchanged"
            and not permission_granted
        )
    )
    if mode == "full-autonomous" and packet["request_human_input"] is True:
        raise SupervisionLogError(
            "Full-autonomous mode forbids a human request; resolve or reserve externally"
        )
    if budget_exceeded or protected_regression:
        application_posture = (
            "stop-and-retire-candidate"
            if candidate_disposition
            else "stop-protected-regression"
        )
        next_action = "continue-unaffected-safe-frontier"
        application_authorized = False
        application_ready = False
        reserved = False
    elif reserved:
        if not evidence["blocked_subjects"] or not revisit_trigger:
            raise SupervisionLogError(
                "Reserved-external posture requires blocked subjects and a revisit trigger"
            )
        application_posture = "reserved-external"
        next_action = "continue-safe-frontier-without-human-request"
        application_authorized = False
        application_ready = False
    elif review_required and review is None:
        application_posture = "automated-independent-review-required"
        next_action = "obtain-one-bounded-automated-review"
        application_authorized = False
        application_ready = False
    elif review_required and not review_complete:
        application_posture = f"independent-review-{review_disposition}"
        next_action = "retire-or-hold-rejected-path-and-continue-safe-frontier"
        application_authorized = False
        application_ready = False
    elif disposition == "continue-unchanged":
        application_posture = "continue-unchanged"
        next_action = "continue-current-block"
        application_authorized = False
        application_ready = False
    elif mode == "fixed":
        application_posture = "record-only"
        next_action = "continue-safe-frontier-without-application"
        application_authorized = False
        application_ready = False
    elif mode == "recommend":
        application_posture = "recommendation-only"
        next_action = "continue-safe-frontier-pending-external-application"
        application_authorized = False
        application_ready = False
    elif mode == "reviewed-autonomous" and consequence_class == "consequential":
        application_posture = "external-application-authority-required"
        next_action = "continue-safe-frontier-pending-external-application"
        application_authorized = False
        application_ready = False
    else:
        application_posture = "owner-application-ready"
        next_action = "apply-through-existing-owner-after-atomic-currentness-recheck"
        application_authorized = False
        application_ready = True
    request_allowed = mode != "full-autonomous" and application_posture in {
        "recommendation-only",
        "external-application-authority-required",
        "reserved-external",
    }
    if packet["request_human_input"] is True and not request_allowed:
        raise SupervisionLogError("Adaptive human request is not eligible")
    human_request_count = 1 if packet["request_human_input"] is True else 0
    if human_request_count:
        next_action = "continue-safe-frontier-pending-external-response"
    result = {
        "schema_version": 1,
        "decision_id": decision_id,
        "state_fingerprint": decision_fingerprint,
        "decision_fingerprint": decision_fingerprint,
        "decision_currentness_root": digest(
            {
                **{
                    "decision_fingerprint": decision_fingerprint,
                    "evidence_manifest_root": evidence["evidence_manifest_root"],
                    "tracker_sha256": evidence["tracker_sha256"],
                    "policy_root": policy.get("policy_sha256"),
                    "event_head_root": event_head_root,
                    "target_revision": evidence["target_revision"],
                    "target_revision_root": evidence["target_revision_root"],
                    "current_target_state_root": evidence["current_target_state_root"],
                    "safe_frontier": evidence["safe_frontier"],
                    "adaptive_decision_mode": mode,
                    "accepted_decision_head": evidence["accepted_decision_head"],
                    "accepted_revision_head": evidence["accepted_revision_head"],
                    "revisit_trigger": revisit_trigger,
                    "candidate_currentness_root": candidate.get("currentness_root") if candidate else None,
                },
                "review_root": review.get("review_root") if review else None,
                "review_disposition": review_disposition,
                "evaluator_id": review.get("evaluator_id") if review else None,
                "evaluation_evidence_root": (
                    review.get("evaluation_evidence_root") if review else None
                ),
                "evaluator_authority_key_sha256": (
                    review.get("evaluator_authority_key_sha256") if review else None
                ),
                "evaluation_root": review.get("evaluation_root") if review else None,
                "evaluation_disposition": evaluation_disposition,
            }
        ),
        "decision_semantics_root": decision_semantics_root,
        "decision_source_root": evidence["source_root"],
        "governing_event_head_root": event_head_root,
        "adaptive_decision_mode": mode,
        "legacy_policy_posture": legacy,
        "disposition": disposition,
        "judgment_class": judgment_class,
        "consequence_class": consequence_class,
        "target_class": target_class,
        "effect_class": effect_class,
        "required_permissions": list(required_permissions),
        "permission_results": permission_results,
        "permission_granted": permission_granted,
        "reversible": evidence["reversible"],
        "mission_preserving": evidence["mission_preserving"],
        "independent_review_required": review_required,
        "independent_review_record": review.get("record_id") if review else None,
        "independent_reviewer_id": review.get("reviewer_id") if review else None,
        "independent_review_disposition": review_disposition,
        "independent_evaluator_id": review.get("evaluator_id") if review else None,
        "independent_evaluation_disposition": evaluation_disposition,
        "independent_evaluation_root": review.get("evaluation_root") if review else None,
        "independent_review_root": review.get("review_root") if review else None,
        "candidate_evidence_root": candidate.get("evidence_root") if candidate else None,
        "candidate_source_revision": candidate.get("source_revision_root") if candidate else None,
        "candidate_owner_id": candidate.get("owner_id") if candidate else None,
        "proposer_author_id": evidence["proposer_author_id"],
        "implementation_owner_id": evidence["implementation_owner_id"],
        "candidate_currentness_root": candidate.get("currentness_root") if candidate else None,
        "candidate_budget": dict(budget),
        "candidate_budget_use": dict(usage),
        "budget_exceeded": budget_exceeded,
        "protected_regression": protected_regression,
        "application_posture": application_posture,
        "application_authorized": application_authorized,
        "application_ready": application_ready,
        "human_request_count": human_request_count,
        "reserved_external": application_posture == "reserved-external",
        "blocked_subjects": list(evidence["blocked_subjects"]),
        "safe_frontier": list(evidence["safe_frontier"]),
        "revisit_trigger": revisit_trigger,
        "next_action": next_action,
        "policy_sha256": policy.get("policy_sha256"),
    }
    result["application_precondition_root"] = (
        digest(
            {
                "decision_source_root": result["decision_source_root"],
                "decision_fingerprint": result["decision_fingerprint"],
                "decision_currentness_root": result["decision_currentness_root"],
                "policy_sha256": result["policy_sha256"],
                "target_revision_root": evidence["target_revision_root"],
                "current_target_state_root": evidence["current_target_state_root"],
                "affected_scope": evidence["affected_scope"],
                "candidate_currentness_root": result["candidate_currentness_root"],
                "implementation_owner_id": result["implementation_owner_id"],
            }
        )
        if application_ready
        else None
    )
    result["result_sha256"] = digest(result)
    return result


def adaptive_decision_posture(
    policy: Mapping[str, Any], packet: Mapping[str, Any]
) -> dict[str, Any]:
    evidence = packet.get("decision_evidence")
    if (
        isinstance(evidence, Mapping)
        and evidence.get("disposition") in {"compare-candidate", "cutover-candidate"}
    ):
        raise SupervisionLogError(
            "Candidate posture requires the canonical owner-bound decision gate"
        )
    result = _adaptive_decision_posture(
        policy, packet, active_candidate_fingerprints=[]
    )
    if result["application_authorized"] is True or result["application_ready"] is True:
        raise SupervisionLogError(
            "Adaptive application authorization requires the canonical owner-bound decision gate"
        )
    return result


def adaptive_status_projection(
    policy: Mapping[str, Any], all_events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    configured = policy.get("adaptive_decision_control")
    legacy = configured is None
    control = (
        adaptive_decision_control_contract("fixed")
        if configured is None
        else configured
    )
    if not isinstance(control, Mapping):
        raise SupervisionLogError("Adaptive-decision policy is malformed")
    validate_adaptive_decision_control(control)
    decision_events: list[dict[str, Any]] = []
    event_only_fields = {
        "record_id",
        "timestamp",
        "target_thread_id",
        "kind",
        "previous_record_sha256",
        "record_sha256",
    }
    for item in all_events:
        if item.get("kind") != "adaptive-decision":
            continue
        normalized = dict(item)
        result_material = {
            key: value
            for key, value in normalized.items()
            if key not in event_only_fields | {"result_sha256"}
        }
        if (
            normalized.get("result_sha256") != digest(result_material)
            or type(normalized.get("human_request_count")) is not int
            or normalized.get("human_request_count") not in {0, 1}
            or normalized.get("adaptive_decision_mode") not in ADAPTIVE_DECISION_MODES
            or normalized.get("disposition") not in ADAPTIVE_DISPOSITIONS
            or not isinstance(normalized.get("candidate_budget"), Mapping)
        ):
            raise SupervisionLogError("Canonical adaptive decision event is invalid")
        validate_adaptive_decision_control(
            adaptive_decision_control_contract(
                str(normalized["adaptive_decision_mode"]),
                candidate_budget=normalized["candidate_budget"],
                target_class=str(normalized["target_class"]),
            )
        )
        decision_events.append(normalized)
    review_events = [
        dict(item) for item in all_events if item.get("kind") == "adaptive-decision-review"
    ]
    for item in review_events:
        resolve_adaptive_review(
            all_events,
            str(item.get("record_id", "")),
            policy=policy,
            require_current_policy=False,
        )
    adaptive_human_request_count = sum(
        int(item.get("human_request_count", 0)) for item in decision_events
    )
    legacy_human_decisions = {
        str(item.get("decision_id"))
        for item in all_events
        if item.get("kind") == "decision" and item.get("human_input_requested_at")
    }
    human_request_count = adaptive_human_request_count + len(legacy_human_decisions)
    current_policy_sha = policy.get("policy_sha256")
    current_full_autonomous_human_request_count = sum(
        int(item.get("human_request_count", 0))
        for item in decision_events
        if item.get("adaptive_decision_mode") == "full-autonomous"
        and item.get("policy_sha256") == current_policy_sha
    ) + len(
        {
            str(item.get("decision_id"))
            for item in all_events
            if item.get("kind") == "decision"
            and item.get("human_input_requested_at")
            and item.get("policy_sha256") == current_policy_sha
            and control["adaptive_decision_mode"] == "full-autonomous"
        }
    )
    reserved = [item for item in decision_events if item.get("reserved_external") is True]
    last = decision_events[-1] if decision_events else None
    return {
        "schema_version": 1,
        "adaptive_decision_mode": control["adaptive_decision_mode"],
        "legacy_policy_posture": legacy,
        "candidate_budget": dict(control["candidate_budget"]),
        "decision_count": len(decision_events),
        "independent_review_count": len(review_events),
        "human_request_count": human_request_count,
        "adaptive_human_request_count": adaptive_human_request_count,
        "legacy_decision_human_request_count": len(legacy_human_decisions),
        "current_full_autonomous_human_request_count": current_full_autonomous_human_request_count,
        "reserved_external_count": len(reserved),
        "last_decision": last,
        "last_candidate_budget_use": (
            last.get("candidate_budget_use") if last is not None else None
        ),
        "last_safe_frontier": last.get("safe_frontier") if last is not None else [],
        "last_application_posture": (
            last.get("application_posture") if last is not None else None
        ),
    }


def adaptive_external_review_root_material(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"review_root", "signature_base64"}
    }


def adaptive_external_review_signed_material(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "signature_base64"}


def adaptive_external_evaluation_root_material(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        key: value[key]
        for key in (
            "source_decision_record",
            "source_decision_sha256",
            "decision_id",
            "decision_fingerprint",
            "decision_currentness_root",
            "decision_semantics_root",
            "disposition",
            "target_class",
            "effect_class",
            "candidate_evidence_root",
            "candidate_owner_id",
            "proposer_author_id",
            "implementation_owner_id",
            "evaluator_id",
            "evaluation_evidence_root",
            "evaluation_disposition",
            "policy_sha256",
            "evaluator_authority_key_sha256",
        )
    }


def adaptive_external_evaluation_signed_material(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    material = adaptive_external_evaluation_root_material(value)
    material["evaluation_root"] = value["evaluation_root"]
    return material


def trusted_adaptive_authority_key(
    path: Path, *, expected_sha256: str, label: str
) -> bytes:
    descriptor = -1
    try:
        key_stat = path.lstat()
        if (
            not stat.S_ISREG(key_stat.st_mode)
            or stat.S_ISLNK(key_stat.st_mode)
            or key_stat.st_size > 8192
            or key_stat.st_mode & 0o022
        ):
            raise SupervisionLogError(f"Sealed adaptive {label} key posture differs")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        before = file_snapshot(os.fstat(descriptor))
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            key_bytes = handle.read(8193)
            after = file_snapshot(os.fstat(handle.fileno()))
        if before != after or path_snapshot(path) != before or len(key_bytes) > 8192:
            raise SupervisionLogError(f"Sealed adaptive {label} key changed while reading")
    except OSError as exc:
        raise SupervisionLogError(f"Sealed adaptive {label} key is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if hashlib.sha256(key_bytes).hexdigest() != expected_sha256:
        raise SupervisionLogError(f"Sealed adaptive {label} key identity differs")
    for parent in (path.parent, path.parent.parent):
        parent_stat = parent.lstat()
        if not stat.S_ISDIR(parent_stat.st_mode) or parent_stat.st_mode & 0o022:
            raise SupervisionLogError(f"Adaptive {label} authority owner is writable")
    return key_bytes


def trusted_adaptive_reviewer_key() -> bytes:
    return trusted_adaptive_authority_key(
        ADAPTIVE_REVIEW_PUBLIC_KEY_PATH,
        expected_sha256=ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256,
        label="reviewer",
    )


def trusted_adaptive_evaluator_key() -> bytes:
    return trusted_adaptive_authority_key(
        ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH,
        expected_sha256=ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256,
        label="evaluator",
    )


def trusted_adaptive_review_openssl() -> Path:
    path = ADAPTIVE_REVIEW_OPENSSL_PATH
    try:
        value = path.read_bytes()
        mode = path.lstat().st_mode
    except OSError as exc:
        raise SupervisionLogError("Pinned adaptive review verifier is unavailable") from exc
    if (
        not stat.S_ISREG(mode)
        or stat.S_ISLNK(mode)
        or not mode & 0o111
        or hashlib.sha256(value).hexdigest() != ADAPTIVE_REVIEW_OPENSSL_SHA256
    ):
        raise SupervisionLogError("Pinned adaptive review verifier identity differs")
    return path


def verify_adaptive_review_signature(value: Mapping[str, Any]) -> None:
    signature_value = value.get("signature_base64")
    if type(signature_value) is not str:
        raise SupervisionLogError("Adaptive review signature must be base64 text")
    try:
        signature = base64.b64decode(signature_value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SupervisionLogError("Adaptive review signature is not valid base64") from exc
    if len(signature) != 64:
        raise SupervisionLogError("Adaptive review signature length differs")
    key_bytes = trusted_adaptive_reviewer_key()
    openssl = trusted_adaptive_review_openssl()
    with tempfile.TemporaryDirectory(prefix="adaptive-review-verify-") as temp_value:
        temp = Path(temp_value)
        content = temp / "review.json"
        signature_path = temp / "review.sig"
        key_path = temp / "reviewer.pem"
        content.write_bytes(canonical(adaptive_external_review_signed_material(value)))
        signature_path.write_bytes(signature)
        key_path.write_bytes(key_bytes)
        result = subprocess.run(
            [
                str(openssl),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(key_path),
                "-rawin",
                "-in",
                str(content),
                "-sigfile",
                str(signature_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    if result.returncode != 0:
        raise SupervisionLogError("Adaptive review signature verification failed")


def verify_adaptive_evaluation_signature(value: Mapping[str, Any]) -> None:
    signature_value = value.get("evaluation_signature_base64")
    if type(signature_value) is not str:
        raise SupervisionLogError("Adaptive evaluation signature must be base64 text")
    try:
        signature = base64.b64decode(signature_value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SupervisionLogError("Adaptive evaluation signature is not valid base64") from exc
    if len(signature) != 64:
        raise SupervisionLogError("Adaptive evaluation signature length differs")
    key_bytes = trusted_adaptive_evaluator_key()
    openssl = trusted_adaptive_review_openssl()
    with tempfile.TemporaryDirectory(prefix="adaptive-evaluation-verify-") as temp_value:
        temp = Path(temp_value)
        content = temp / "evaluation.json"
        signature_path = temp / "evaluation.sig"
        key_path = temp / "evaluator.pem"
        content.write_bytes(canonical(adaptive_external_evaluation_signed_material(value)))
        signature_path.write_bytes(signature)
        key_path.write_bytes(key_bytes)
        result = subprocess.run(
            [
                str(openssl),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(key_path),
                "-rawin",
                "-in",
                str(content),
                "-sigfile",
                str(signature_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    if result.returncode != 0:
        raise SupervisionLogError("Adaptive evaluation signature verification failed")


def validate_external_adaptive_review(
    value: Any, *, source: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    expected = {
        "schema_version",
        "kind",
        "record_id",
        "source_decision_record",
        "source_decision_sha256",
        "decision_id",
        "decision_fingerprint",
        "decision_currentness_root",
        "decision_semantics_root",
        "disposition",
        "target_class",
        "effect_class",
        "candidate_evidence_root",
        "candidate_owner_id",
        "proposer_author_id",
        "implementation_owner_id",
        "reviewer_id",
        "evaluator_id",
        "evaluation_evidence_root",
        "evaluator_authority_key_sha256",
        "evaluation_root",
        "evaluation_signature_base64",
        "review_disposition",
        "evaluation_disposition",
        "evidence_root",
        "policy_sha256",
        "authority_key_sha256",
        "review_root",
        "signature_base64",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SupervisionLogError("External adaptive review shape differs")
    if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise SupervisionLogError("External adaptive review version differs")
    if value.get("kind") != "software-factory-adaptive-independent-review":
        raise SupervisionLogError("External adaptive review kind differs")
    for field in ("record_id", "source_decision_record", "decision_id"):
        if type(value.get(field)) is not str:
            raise SupervisionLogError(f"External adaptive review {field} must be a string")
        safe_id(str(value[field]), label=f"external adaptive review {field}")
    for field in (
        "source_decision_sha256",
        "decision_fingerprint",
        "decision_currentness_root",
        "decision_semantics_root",
        "evidence_root",
        "policy_sha256",
        "authority_key_sha256",
        "review_root",
    ):
        if type(value.get(field)) is not str:
            raise SupervisionLogError(f"External adaptive review {field} must be a string")
        exact_sha256(str(value[field]), label=f"external adaptive review {field}")
    for field in ("candidate_evidence_root",):
        item = value.get(field)
        if item is not None:
            if type(item) is not str:
                raise SupervisionLogError(f"External adaptive review {field} must be a string")
            exact_sha256(item, label=f"external adaptive review {field}")
    evaluation_evidence_root = value.get("evaluation_evidence_root")
    if evaluation_evidence_root is not None:
        if type(evaluation_evidence_root) is not str:
            raise SupervisionLogError("External adaptive evaluation evidence root must be a string")
        exact_sha256(
            evaluation_evidence_root,
            label="external adaptive evaluation evidence root",
        )
    for field in ("evaluator_authority_key_sha256", "evaluation_root"):
        item = value.get(field)
        if item is not None:
            if type(item) is not str:
                raise SupervisionLogError(
                    f"External adaptive review {field} must be a string"
                )
            exact_sha256(item, label=f"external adaptive review {field}")
    for field in (
        "candidate_owner_id",
        "proposer_author_id",
        "implementation_owner_id",
        "evaluator_id",
    ):
        item = value.get(field)
        if item is not None:
            if type(item) is not str:
                raise SupervisionLogError(f"External adaptive review {field} must be a string")
            safe_id(item, label=f"external adaptive review {field}")
    if value.get("reviewer_id") != ADAPTIVE_REVIEWER_ID:
        raise SupervisionLogError("External adaptive review authority differs")
    if value.get("review_disposition") not in {"accepted", "rejected", "inconclusive"}:
        raise SupervisionLogError("External adaptive review disposition differs")
    if value.get("evaluation_disposition") not in {None, "accepted", "rejected", "inconclusive"}:
        raise SupervisionLogError("External adaptive evaluation disposition differs")
    exact_identity = {
        "source_decision_record": source.get("record_id"),
        "source_decision_sha256": source.get("record_sha256"),
        "decision_id": source.get("decision_id"),
        "decision_fingerprint": source.get("decision_fingerprint"),
        "decision_currentness_root": source.get("decision_currentness_root"),
        "decision_semantics_root": source.get("decision_semantics_root"),
        "disposition": source.get("disposition"),
        "target_class": source.get("target_class"),
        "effect_class": source.get("effect_class"),
        "candidate_evidence_root": source.get("candidate_evidence_root"),
        "candidate_owner_id": source.get("candidate_owner_id"),
        "proposer_author_id": source.get("proposer_author_id"),
        "implementation_owner_id": source.get("implementation_owner_id"),
        "policy_sha256": policy.get("policy_sha256"),
        "authority_key_sha256": ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256,
    }
    if any(value.get(key) != item for key, item in exact_identity.items()):
        raise SupervisionLogError("External adaptive review does not bind the source decision")
    if value["target_class"] == "software-factory":
        if (
            value.get("evaluator_id") != ADAPTIVE_EVALUATOR_ID
            or value.get("evaluation_disposition") is None
            or value.get("evaluation_evidence_root") is None
            or value.get("evaluator_authority_key_sha256")
            != ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256
            or value.get("evaluation_root") is None
            or value.get("evaluation_signature_base64") is None
        ):
            raise SupervisionLogError(
                "Software Factory review requires an independent evaluator result"
            )
    elif any(
        value.get(field) is not None
        for field in (
            "evaluator_id",
            "evaluation_disposition",
            "evaluation_evidence_root",
            "evaluator_authority_key_sha256",
            "evaluation_root",
            "evaluation_signature_base64",
        )
    ):
        raise SupervisionLogError("Target-repository review cannot claim a Factory evaluator")
    if value["target_class"] == "software-factory":
        if value["evaluator_authority_key_sha256"] == value["authority_key_sha256"]:
            raise SupervisionLogError("Adaptive reviewer and evaluator authorities are not distinct")
        if value["evaluation_root"] != digest(
            adaptive_external_evaluation_root_material(value)
        ):
            raise SupervisionLogError("External adaptive evaluation root differs")
        verify_adaptive_evaluation_signature(value)
    if value["review_root"] != digest(adaptive_external_review_root_material(value)):
        raise SupervisionLogError("External adaptive review root differs")
    verify_adaptive_review_signature(value)
    return dict(value)


def load_external_adaptive_review(
    path_value: str, *, source: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    return validate_external_adaptive_review(
        load_bounded_canonical_json(
            path_value,
            label="external adaptive review",
            maximum_bytes=MAX_ADAPTIVE_REVIEW_EVIDENCE_BYTES,
        ),
        source=source,
        policy=policy,
    )


def adaptive_review_root_material(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: event[key]
        for key in (
            "external_review_payload",
            "external_review_record",
            "source_decision_record",
            "source_decision_sha256",
            "decision_id",
            "decision_fingerprint",
            "decision_currentness_root",
            "decision_semantics_root",
            "disposition",
            "target_class",
            "effect_class",
            "candidate_evidence_root",
            "candidate_owner_id",
            "proposer_author_id",
            "implementation_owner_id",
            "reviewer_id",
            "evaluator_id",
            "evaluation_evidence_root",
            "evaluator_authority_key_sha256",
            "evaluation_root",
            "evaluation_signature_sha256",
            "review_disposition",
            "evaluation_disposition",
            "evidence_root",
            "policy_sha256",
            "authority_key_sha256",
            "external_review_root",
            "external_signature_sha256",
        )
    }


def resolve_adaptive_review(
    all_events: Sequence[Mapping[str, Any]],
    record_id: str,
    *,
    policy: Mapping[str, Any],
    require_current_policy: bool = True,
) -> dict[str, Any]:
    safe_id(record_id, label="adaptive review record")
    event = next(
        (dict(item) for item in all_events if item.get("record_id") == record_id),
        None,
    )
    expected = {
        "schema_version", "record_id", "timestamp", "target_thread_id", "kind",
        "external_review_payload",
        "external_review_record", "source_decision_record", "source_decision_sha256",
        "decision_id", "decision_fingerprint", "decision_currentness_root",
        "decision_semantics_root", "disposition", "target_class", "effect_class",
        "candidate_evidence_root", "candidate_owner_id", "proposer_author_id",
        "implementation_owner_id", "reviewer_id", "evaluator_id",
        "evaluation_evidence_root", "evaluator_authority_key_sha256",
        "evaluation_root", "evaluation_signature_sha256",
        "review_disposition", "evaluation_disposition", "evidence_root", "policy_sha256",
        "authority_key_sha256", "external_review_root", "external_signature_sha256",
        "review_root", "previous_record_sha256", "record_sha256",
    }
    if event is None or set(event) != expected:
        raise SupervisionLogError("Canonical adaptive review record differs")
    if event.get("schema_version") != 1 or event.get("kind") != "adaptive-decision-review":
        raise SupervisionLogError("Canonical adaptive review kind differs")
    source = next(
        (
            dict(item)
            for item in all_events
            if item.get("record_id") == event["source_decision_record"]
        ),
        None,
    )
    if (
        source is None
        or source.get("kind") != "adaptive-decision"
        or source.get("record_sha256") != event["source_decision_sha256"]
        or source.get("decision_id") != event["decision_id"]
        or source.get("decision_fingerprint") != event["decision_fingerprint"]
        or source.get("decision_currentness_root") != event["decision_currentness_root"]
        or source.get("decision_semantics_root") != event["decision_semantics_root"]
        or source.get("disposition") != event["disposition"]
        or source.get("target_class") != event["target_class"]
        or source.get("effect_class") != event["effect_class"]
        or source.get("candidate_evidence_root") != event["candidate_evidence_root"]
        or source.get("candidate_owner_id") != event["candidate_owner_id"]
        or source.get("proposer_author_id") != event["proposer_author_id"]
        or source.get("implementation_owner_id") != event["implementation_owner_id"]
        or source.get("independent_review_required") is not True
        or source.get("application_posture") != "automated-independent-review-required"
    ):
        raise SupervisionLogError("Adaptive review source decision differs")
    earlier_adaptive = [
        item
        for item in all_events[: all_events.index(event)]
        if item.get("kind") == "adaptive-decision"
        and item.get("decision_id") == event["decision_id"]
    ]
    if not earlier_adaptive or earlier_adaptive[-1].get("record_id") != source.get("record_id"):
        raise SupervisionLogError("Adaptive review source decision is stale")
    reviewer_id = event.get("reviewer_id")
    disallowed = {
        source.get("implementation_owner_id"),
        source.get("proposer_author_id"),
        source.get("candidate_owner_id"),
    }
    if reviewer_id != ADAPTIVE_REVIEWER_ID or reviewer_id in disallowed:
        raise SupervisionLogError("Adaptive review is not independently owned")
    if event.get("review_disposition") not in {"accepted", "rejected", "inconclusive"}:
        raise SupervisionLogError("Adaptive review disposition differs")
    for field in (
        "source_decision_sha256",
        "decision_fingerprint",
        "decision_currentness_root",
        "decision_semantics_root",
        "evidence_root",
        "policy_sha256",
        "authority_key_sha256",
        "external_review_root",
        "external_signature_sha256",
        "review_root",
        "record_sha256",
    ):
        if type(event.get(field)) is not str:
            raise SupervisionLogError(f"Adaptive review {field} must be a string")
        exact_sha256(str(event[field]), label=f"adaptive review {field}")
    candidate_root = event.get("candidate_evidence_root")
    if candidate_root is not None:
        if type(candidate_root) is not str:
            raise SupervisionLogError("Adaptive candidate evidence root must be a string")
        exact_sha256(candidate_root, label="adaptive candidate evidence root")
    if require_current_policy and event["policy_sha256"] != policy.get("policy_sha256"):
        raise SupervisionLogError("Adaptive review is stale for the current policy")
    if event["review_root"] != digest(adaptive_review_root_material(event)):
        raise SupervisionLogError("Adaptive review root differs")
    external_review = validate_external_adaptive_review(
        event["external_review_payload"], source=source, policy=policy
    )
    exact_payload_fields = {
        "record_id": "external_review_record",
        "reviewer_id": "reviewer_id",
        "evaluator_id": "evaluator_id",
        "evaluation_evidence_root": "evaluation_evidence_root",
        "evaluator_authority_key_sha256": "evaluator_authority_key_sha256",
        "evaluation_root": "evaluation_root",
        "review_disposition": "review_disposition",
        "evaluation_disposition": "evaluation_disposition",
        "evidence_root": "evidence_root",
        "authority_key_sha256": "authority_key_sha256",
        "review_root": "external_review_root",
    }
    if any(
        external_review[payload_field] != event[event_field]
        for payload_field, event_field in exact_payload_fields.items()
    ):
        raise SupervisionLogError("Canonical adaptive review payload differs")
    if event["evaluation_signature_sha256"] != (
        hashlib.sha256(
            base64.b64decode(
                external_review["evaluation_signature_base64"], validate=True
            )
        ).hexdigest()
        if external_review["evaluation_signature_base64"] is not None
        else None
    ):
        raise SupervisionLogError("Canonical adaptive evaluation signature differs")
    return external_review


def adaptive_active_candidate_fingerprints(
    all_events: Sequence[Mapping[str, Any]],
) -> list[str]:
    latest_by_decision: dict[str, Mapping[str, Any]] = {}
    for item in all_events:
        if item.get("kind") == "adaptive-decision" and item.get("candidate_evidence_root"):
            latest_by_decision[str(item.get("decision_id"))] = item
    inactive = {
        "stop-and-retire-candidate",
        "independent-review-rejected",
        "independent-review-inconclusive",
    }
    roots = {
        str(item["decision_fingerprint"])
        for item in latest_by_decision.values()
        if item.get("application_posture") not in inactive
        and type(item.get("decision_fingerprint")) is str
        and SHA256.fullmatch(str(item["decision_fingerprint"])) is not None
    }
    return sorted(roots)


def cmd_adaptive_decision_gate(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    active_events = mission_scoped_events(directory, policy, all_events)
    decision_evidence = load_adaptive_decision_evidence(
        args.decision_evidence, policy=policy
    )
    decision_id = str(decision_evidence["decision_id"])
    control = policy.get("adaptive_decision_control")
    if control is None:
        control = adaptive_decision_control_contract("fixed")
    if not isinstance(control, Mapping):
        raise SupervisionLogError("Adaptive-decision policy is malformed")
    validate_adaptive_decision_control(control)
    candidate = None
    if args.candidate_evidence:
        candidate = load_adaptive_candidate_evidence(
            args.candidate_evidence,
            decision_evidence=decision_evidence,
        )
    review = None
    if args.independent_review_record:
        review = resolve_adaptive_review(
            active_events,
            args.independent_review_record,
            policy=policy,
        )
    governing_events = [
        item
        for item in active_events
        if item.get("kind") not in {"adaptive-decision", "adaptive-decision-review"}
    ]
    packet = {
        "decision_evidence": decision_evidence,
        "candidate_evidence": candidate,
        "independent_review": review,
        "request_human_input": args.request_human_input,
        "governing_event_head_root": (
            governing_events[-1].get("record_sha256") if governing_events else None
        ),
    }
    result = _adaptive_decision_posture(
        policy,
        packet,
        active_candidate_fingerprints=adaptive_active_candidate_fingerprints(
            active_events
        ),
    )
    if review is not None:
        result["independent_review_record"] = args.independent_review_record
        result["result_sha256"] = digest(
            {key: value for key, value in result.items() if key != "result_sha256"}
        )
    record = {
        "schema_version": 1,
        "record_id": "",
        "timestamp": utc_now(),
        "target_thread_id": args.target_thread,
        "kind": "adaptive-decision",
        **result,
    }
    with owner_append_lock(
        root_from(args), args.target_thread, directory_snapshot
    ) as directory_fd:
        require_bound_policy_at(
            directory_fd,
            expected_policy=policy,
            expected_snapshot=policy_snapshot,
        )
        current_events, current_event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        if current_event_snapshot != event_snapshot or current_events != all_events:
            raise SupervisionLogError(
                "Adaptive decision event head changed; retry current decision state"
            )
        current_active_events = mission_scoped_events(directory, policy, current_events)
        rechecked_decision = validate_adaptive_decision_evidence(
            decision_evidence, policy=policy
        )
        if rechecked_decision != decision_evidence:
            raise SupervisionLogError(
                "Adaptive target state changed; retry current decision state"
            )
        if candidate is not None:
            rechecked_candidate = validate_adaptive_candidate_evidence(
                candidate, decision_evidence=rechecked_decision
            )
            if rechecked_candidate != candidate:
                raise SupervisionLogError(
                    "Adaptive candidate state changed; retry current decision state"
                )
        same_fingerprint = [
            item
            for item in current_active_events
            if item.get("kind") == "adaptive-decision"
            and item.get("decision_fingerprint") == result["decision_fingerprint"]
        ]
        if same_fingerprint and same_fingerprint[-1].get("decision_id") != result["decision_id"]:
            if (
                review is None
                and same_fingerprint[-1].get("decision_currentness_root")
                == result["decision_currentness_root"]
                and same_fingerprint[-1].get("decision_semantics_root")
                == result["decision_semantics_root"]
            ):
                print(
                    json.dumps(
                        {"duplicate": True, "record": same_fingerprint[-1]},
                        sort_keys=True,
                    )
                )
                return
            raise SupervisionLogError(
                "Adaptive fingerprint already has a canonical decision ID; refresh that decision"
            )
        prior = [
            item
            for item in current_active_events
            if item.get("kind") == "adaptive-decision"
            and item.get("decision_id") == result["decision_id"]
        ]
        if prior:
            comparable = {
                key: value
                for key, value in prior[-1].items()
                if key
                not in {
                    "record_id",
                    "timestamp",
                    "previous_record_sha256",
                    "record_sha256",
                }
            }
            current = {
                key: value
                for key, value in record.items()
                if key not in {"record_id", "timestamp"}
            }
            if comparable == current:
                print(
                    json.dumps(
                        {"duplicate": True, "record": prior[-1]}, sort_keys=True
                    )
                )
                return
        if record["human_request_count"] == 1 and any(
            item.get("kind") == "adaptive-decision"
            and item.get("state_fingerprint") == result["state_fingerprint"]
            and item.get("human_request_count") == 1
            for item in current_active_events
        ):
            raise SupervisionLogError(
                "Adaptive state already emitted its bounded human request"
            )
        record["record_id"] = f"EVT-{len(current_events) + 1:06d}"
        previous = (
            str(current_events[-1]["record_sha256"]) if current_events else None
        )
        append_raw_locked_at(
            directory_fd,
            "events.jsonl",
            record,
            previous_record_sha256=previous,
            expected_file_snapshot=current_event_snapshot,
            require_event_anchor=bool(current_events),
        )
        current_directory_snapshot = path_snapshot(directory)
        if (
            current_directory_snapshot is None
            or current_directory_snapshot[:2] != directory_snapshot[:2]
        ):
            raise SupervisionLogError(
                "Adaptive decision owner changed during append; retry current decision state"
            )
        written_events, _written_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        record = written_events[-1]
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


def cmd_adaptive_decision_review(args: argparse.Namespace) -> None:
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
    active_events = mission_scoped_events(directory, policy, all_events)
    external_value = load_bounded_canonical_json(
        args.review_json,
        label="external adaptive review",
        maximum_bytes=MAX_ADAPTIVE_REVIEW_EVIDENCE_BYTES,
    )
    source_record_value = external_value.get("source_decision_record")
    if type(source_record_value) is not str:
        raise SupervisionLogError("External adaptive review source must be a string")
    source_record = safe_id(
        source_record_value, label="adaptive review source decision"
    )
    source = next(
        (dict(item) for item in active_events if item.get("record_id") == source_record),
        None,
    )
    if (
        source is None
        or source.get("kind") != "adaptive-decision"
        or source.get("independent_review_required") is not True
        or source.get("application_posture") != "automated-independent-review-required"
        or source.get("policy_sha256") != policy.get("policy_sha256")
    ):
        raise SupervisionLogError("Adaptive review source is not current and review-required")
    governing_events = [
        item
        for item in active_events
        if item.get("kind") not in {"adaptive-decision", "adaptive-decision-review"}
    ]
    current_governing_head = (
        governing_events[-1].get("record_sha256") if governing_events else None
    )
    if source.get("governing_event_head_root") != current_governing_head:
        raise SupervisionLogError(
            "Adaptive review source is stale for the governing event head"
        )
    latest = [
        item
        for item in active_events
        if item.get("kind") == "adaptive-decision"
        and item.get("decision_id") == source.get("decision_id")
    ]
    if not latest or latest[-1].get("record_id") != source_record:
        raise SupervisionLogError("Adaptive review source decision is stale")
    external_review = validate_external_adaptive_review(
        external_value, source=source, policy=policy
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "",
        "timestamp": utc_now(),
        "target_thread_id": args.target_thread,
        "kind": "adaptive-decision-review",
        "external_review_payload": external_review,
        "external_review_record": external_review["record_id"],
        "source_decision_record": source_record,
        "source_decision_sha256": source["record_sha256"],
        "decision_id": source["decision_id"],
        "decision_fingerprint": source["decision_fingerprint"],
        "decision_currentness_root": source["decision_currentness_root"],
        "decision_semantics_root": source["decision_semantics_root"],
        "disposition": source["disposition"],
        "target_class": source["target_class"],
        "effect_class": source["effect_class"],
        "candidate_evidence_root": source.get("candidate_evidence_root"),
        "candidate_owner_id": source.get("candidate_owner_id"),
        "proposer_author_id": source.get("proposer_author_id"),
        "implementation_owner_id": source.get("implementation_owner_id"),
        "reviewer_id": external_review["reviewer_id"],
        "evaluator_id": external_review["evaluator_id"],
        "evaluation_evidence_root": external_review["evaluation_evidence_root"],
        "evaluator_authority_key_sha256": external_review[
            "evaluator_authority_key_sha256"
        ],
        "evaluation_root": external_review["evaluation_root"],
        "evaluation_signature_sha256": (
            hashlib.sha256(
                base64.b64decode(
                    external_review["evaluation_signature_base64"], validate=True
                )
            ).hexdigest()
            if external_review["evaluation_signature_base64"] is not None
            else None
        ),
        "review_disposition": external_review["review_disposition"],
        "evaluation_disposition": external_review["evaluation_disposition"],
        "evidence_root": external_review["evidence_root"],
        "policy_sha256": policy["policy_sha256"],
        "authority_key_sha256": external_review["authority_key_sha256"],
        "external_review_root": external_review["review_root"],
        "external_signature_sha256": hashlib.sha256(
            base64.b64decode(external_review["signature_base64"], validate=True)
        ).hexdigest(),
    }
    record["review_root"] = digest(adaptive_review_root_material(record))
    with owner_append_lock(
        root_from(args), args.target_thread, directory_snapshot
    ) as directory_fd:
        require_bound_policy_at(
            directory_fd,
            expected_policy=policy,
            expected_snapshot=policy_snapshot,
        )
        current_events, current_event_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        if current_event_snapshot != event_snapshot or current_events != all_events:
            raise SupervisionLogError(
                "Adaptive review event head changed; retry current review state"
            )
        current_active_events = mission_scoped_events(directory, policy, current_events)
        prior = [
            item
            for item in current_active_events
            if item.get("kind") == "adaptive-decision-review"
            and item.get("source_decision_record") == source_record
        ]
        if prior:
            comparable = {
                key: value
                for key, value in prior[-1].items()
                if key not in {
                    "record_id",
                    "timestamp",
                    "previous_record_sha256",
                    "record_sha256",
                }
            }
            current = {
                key: value
                for key, value in record.items()
                if key not in {"record_id", "timestamp"}
            }
            if comparable == current:
                print(json.dumps({"duplicate": True, "record": prior[-1]}, sort_keys=True))
                return
            raise SupervisionLogError("Adaptive decision already has a review disposition")
        record["record_id"] = f"EVT-{len(current_events) + 1:06d}"
        previous = str(current_events[-1]["record_sha256"]) if current_events else None
        append_raw_locked_at(
            directory_fd,
            "events.jsonl",
            record,
            previous_record_sha256=previous,
            expected_file_snapshot=current_event_snapshot,
            require_event_anchor=bool(current_events),
        )
        current_directory_snapshot = path_snapshot(directory)
        if (
            current_directory_snapshot is None
            or current_directory_snapshot[:2] != directory_snapshot[:2]
        ):
            raise SupervisionLogError(
                "Adaptive review owner changed during append; retry current review state"
            )
        written_events, _written_snapshot = events_snapshot(
            Path("events.jsonl"), directory_fd=directory_fd
        )
        record = written_events[-1]
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


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
    all_events, event_snapshot = events_snapshot(directory / "events.jsonl")
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
    if set(manifest.get("files", {})) != set(paths):
        raise SupervisionLogError("Weekly report manifest file set differs")
    for name, path in paths.items():
        if not path.is_file():
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
    all_events: Sequence[Mapping[str, Any]], *, lifecycle_record_id: str
) -> Mapping[str, Any] | None:
    return next(
        (
            item
            for item in reversed(all_events)
            if item.get("kind") == "notification"
            and item.get("category") == TERMINAL_REPORT_DELIVERY_CATEGORY
            and item.get("status") == "sent"
            and lifecycle_record_id in item.get("evidence", [])
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


def expected_terminal_automation_ids(policy: Mapping[str, Any]) -> list[str]:
    runtime = policy.get("runtime", {})
    values = [
        runtime.get("routine_automation_id"),
        runtime.get("meta_automation_id"),
        runtime.get("gmail_poll_automation_id"),
        runtime.get("roundup_automation_id"),
        policy.get("reports", {}).get("weekly", {}).get("automation_id"),
    ]
    return sorted({str(item) for item in values if item})


def terminal_automation_owner_states(
    automation_ids: list[str], *, not_before: dt.datetime
) -> dict[str, dict[str, Any]]:
    owner_root = CODEX_AUTOMATIONS_ROOT.resolve()
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
        updated = dt.datetime.fromtimestamp(
            updated_at / 1000, tz=dt.timezone.utc
        )
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


def cmd_terminal_shutdown(args: argparse.Namespace) -> None:
    directory, policy = load_policy(args)
    all_events = events(directory / "events.jsonl")
    lifecycle = next(
        (item for item in all_events if item.get("record_id") == args.lifecycle_record),
        None,
    )
    if lifecycle is None or lifecycle.get("status") != "completed":
        raise SupervisionLogError("Terminal shutdown requires the completed lifecycle")
    delivery = latest_terminal_delivery(
        all_events, lifecycle_record_id=args.lifecycle_record
    )
    if delivery is None or delivery.get("report_set_id") != args.report_set_id:
        raise SupervisionLogError("Terminal shutdown requires delivered report attachments")
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
        current_events = events(directory / "events.jsonl")
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
        if prior is not None:
            if prior.get("automation_states") != states:
                raise SupervisionLogError("Terminal shutdown receipt already differs")
            print(json.dumps({"duplicate": True, "record": prior}, sort_keys=True))
            return
        record = {
            "schema_version": 1,
            "record_id": f"EVT-{len(current_events) + 1:06d}",
            "timestamp": utc_now(),
            "target_thread_id": args.target_thread,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": str(lifecycle.get("state_fingerprint", "")),
            "status": "verified",
            "severity": "info",
            "category": TERMINAL_SHUTDOWN_CATEGORY,
            "summary": "Viewed every bound supervision automation in paused state after terminal report delivery.",
            "evidence": [args.lifecycle_record, args.report_set_id, str(delivery.get("record_id"))],
            "report_set_id": args.report_set_id,
            "manifest_root": verified["manifest_root"],
            "automation_states": states,
            "automation_state_root": digest(states),
            "policy_sha256": policy["policy_sha256"],
        }
        append_event_locked(args, directory, record)
    print(json.dumps({"duplicate": False, "record": record}, sort_keys=True))


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
    (
        directory,
        policy,
        policy_snapshot,
        all_events,
        event_snapshot,
        directory_snapshot,
    ) = load_control_snapshot(args)
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
        if decision_head_is_open(item, active_events, policy)
    ]
    activation_heads = mission_activation_heads(active_events)
    open_activations = mission_activation_heads(active_events, open_only=True)
    current_activation = (
        list(activation_heads.values())[-1] if activation_heads else None
    )
    transition_heads = successor_transition_heads(all_events)
    open_transitions = successor_transition_heads(all_events, open_only=True)
    adaptive_control = adaptive_status_projection(policy, active_events)
    control_posture = reduce_control_posture(
        directory=directory,
        policy=policy,
        owner_events=all_events,
        owner_policy_snapshot=policy_snapshot,
        owner_event_snapshot=event_snapshot,
        owner_directory_snapshot=directory_snapshot,
    )
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
                "adaptive_decision_control": adaptive_control,
                "control_posture": control_posture,
                "required_target_posture": control_posture[
                    "required_target_posture"
                ],
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Maintain bounded tracker supervision records")
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
    init.add_argument("--adaptive-target-repository-root")
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
    mission_activation_start.add_argument(
        "--activation-policy-sha256", required=True
    )
    mission_activation_start.add_argument("--first-eligible-work", required=True)
    mission_activation_start.add_argument("--source-record", required=True)
    mission_activation_start.add_argument(
        "--evidence", action="append", required=True
    )
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
    thread_route_gate.add_argument(
        "--ordinary-means-disabled", choices=["yes", "no"]
    )
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
    thread_route_gate.add_argument("--failure-mode-id")
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
    record.add_argument(
        "--failure-layer", choices=sorted(FAILURE_MODE_LAYERS)
    )
    record.add_argument("--failure-mechanism")
    record.add_argument("--failure-trigger")
    record.add_argument("--failure-effect")
    record.add_argument("--failure-detection")
    record.add_argument("--failure-correction")
    record.add_argument("--failure-recurrence-invariant")
    record.add_argument(
        "--failure-human-scheduling-leak", choices=["yes", "no"]
    )
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
    completion_record.add_argument(
        "--open-item-compatibility-sha256", required=True
    )
    completion_record.add_argument("--independent-challenge-sha256", required=True)
    capability_reconciliation_input = completion_record.add_mutually_exclusive_group(
        required=True
    )
    capability_reconciliation_input.add_argument("--capability-reconciliation-json")
    capability_reconciliation_input.add_argument("--capability-reconciliation-base64")
    completion_record.add_argument("--active-block", default="")
    completion_record.add_argument("--checkpoint", default="")
    completion_record.add_argument("--summary", required=True)
    completion_record.add_argument("--evidence", action="append", required=True)
    completion_record.set_defaults(func=cmd_completion_record)

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
    decision_record.add_argument("--prior-record")
    decision_record.add_argument("--disposition-reason")
    decision_record.add_argument(
        "--correction-authority-source-class",
        choices=sorted(DIRECT_AUTHORITY_SOURCE_CLASSES),
    )
    decision_record.add_argument("--correction-authority-source-record")
    decision_record.add_argument("--correction-authority-source-sha256")
    decision_record.add_argument(
        "--governing-outcome-effect",
        choices=sorted(DECISION_GOVERNING_OUTCOME_EFFECTS),
    )
    decision_record.add_argument("--now")
    decision_record.set_defaults(func=cmd_decision_record)

    decision_gate = subparsers.add_parser("decision-gate")
    decision_gate.add_argument("--target-thread", required=True)
    decision_gate.add_argument("--decision-id", required=True)
    decision_gate.add_argument("--now")
    decision_gate.set_defaults(func=cmd_decision_gate)

    control_posture_gate = subparsers.add_parser("control-posture-gate")
    control_posture_gate.add_argument("--target-thread", required=True)
    control_posture_gate.set_defaults(func=cmd_control_posture_gate)

    legacy_authority_ingest = subparsers.add_parser(
        "legacy-direct-authority-ingest"
    )
    legacy_authority_ingest.add_argument("--target-thread", required=True)
    legacy_authority_ingest.add_argument("--provenance-base64", required=True)
    legacy_authority_ingest.set_defaults(
        func=cmd_legacy_direct_authority_ingest
    )

    range_authority = subparsers.add_parser(
        "implementation-range-authority-receipt"
    )
    range_authority.add_argument("--target-thread", required=True)
    range_authority.add_argument("--authority-event-record", required=True)
    range_authority.set_defaults(func=cmd_implementation_authority_receipt)

    range_bind = subparsers.add_parser("implementation-range-bind")
    range_bind.add_argument("--target-thread", required=True)
    range_bind.add_argument("--range-id", required=True)
    range_bind.add_argument("--tracker", required=True)
    range_bind.add_argument("--request-text", required=True)
    range_bind.add_argument("--authority-source-record", required=True)
    range_bind.add_argument("--authority-source-sha256", required=True)
    range_bind.set_defaults(func=cmd_implementation_range_bind)

    range_amend = subparsers.add_parser("implementation-range-amend")
    range_amend.add_argument("--target-thread", required=True)
    range_amend.add_argument("--tracker", required=True)
    range_amend.add_argument("--request-text", default="")
    range_amend.add_argument("--authority-source-record", default="")
    range_amend.add_argument("--authority-source-sha256", default="")
    range_amend.add_argument("--amendment-event-record", default="")
    range_amend.set_defaults(func=cmd_implementation_range_amend)

    range_gate = subparsers.add_parser("implementation-range-gate")
    range_gate.add_argument("--target-thread", required=True)
    range_gate.add_argument(
        "--response-kind",
        choices=IMPLEMENTATION_RANGE_RESPONSE_KINDS,
        default="outcome-terminal",
    )
    range_gate.set_defaults(func=cmd_implementation_range_gate)

    publication_gate = subparsers.add_parser("skill-release-publication-gate")
    publication_gate.add_argument("--target-thread", required=True)
    publication_gate.add_argument(
        "--publication-status",
        choices=SKILL_RELEASE_PUBLICATION_STATUSES,
        required=True,
    )
    publication_gate.add_argument("--publication-retry-trigger", default="")
    publication_gate.set_defaults(func=cmd_skill_release_publication_gate)

    successor_record = subparsers.add_parser("successor-transition-record")
    successor_record.add_argument("--target-thread", required=True)
    successor_record.add_argument("--transition-id", required=True)
    successor_record.add_argument(
        "--phase", choices=SUCCESSOR_TRANSITION_ALL_PHASES, required=True
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
    successor_record.add_argument(
        "--governing-authority-source-record", required=True
    )
    successor_record.add_argument(
        "--governing-authority-source-sha256", required=True
    )
    successor_record.add_argument(
        "--topology-posture", choices=sorted(SUCCESSOR_TOPOLOGY_POSTURES), default=""
    )
    successor_record.add_argument(
        "--topology-basis", choices=sorted(SUCCESSOR_TOPOLOGY_BASES), default=""
    )
    successor_record.add_argument("--topology-rationale", default="")
    successor_record.add_argument("--topology-request-text", default="")
    successor_record.add_argument("--topology-decision-event-record", default="")
    successor_record.add_argument("--expires-at", default="")
    successor_record.add_argument("--replaces-transition", default="")
    successor_record.add_argument("--successor-thread", default="")
    successor_record.add_argument("--successor-mission-root", default="")
    successor_record.add_argument("--successor-group-id", default="")
    successor_record.add_argument("--handoff-record", default="")
    successor_record.add_argument("--acknowledgement-record", default="")
    successor_record.add_argument("--started-block", default="")
    successor_record.add_argument("--prior-record", default="")
    successor_record.add_argument("--disposition-reason", default="")
    successor_record.add_argument(
        "--correction-authority-source-class",
        choices=sorted(AUTHORITY_SOURCE_CLASSES),
    )
    successor_record.add_argument(
        "--correction-authority-source-record", default=""
    )
    successor_record.add_argument(
        "--correction-authority-source-sha256", default=""
    )
    successor_record.add_argument("--replacement-transition", default="")
    successor_record.add_argument(
        "--governing-outcome-effect",
        choices=sorted(SUCCESSOR_GOVERNING_OUTCOME_EFFECTS),
    )
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
    adjust.add_argument(
        "--adaptive-decision-mode",
        choices=sorted(ADAPTIVE_DECISION_MODES),
    )
    adjust.add_argument(
        "--adaptive-target-class",
        choices=sorted(ADAPTIVE_TARGET_CLASSES),
    )
    adjust.add_argument("--adaptive-target-repository-root")
    adjust.add_argument("--candidate-max-active-lanes", type=int)
    adjust.add_argument("--candidate-max-files", type=int)
    adjust.add_argument("--candidate-max-changed-lines", type=int)
    adjust.add_argument("--candidate-max-commands", type=int)
    adjust.add_argument("--candidate-max-elapsed-minutes", type=int)
    adjust.add_argument("--candidate-max-mapped-comparisons", type=int)
    adjust.add_argument("--candidate-max-review-passes", type=int)
    adjust.add_argument("--reason", required=True)
    adjust.add_argument("--evidence", action="append", default=[])
    adjust.set_defaults(func=cmd_adjust)

    adaptive_gate = subparsers.add_parser("adaptive-decision-gate")
    adaptive_gate.add_argument("--target-thread", required=True)
    adaptive_gate.add_argument("--decision-evidence", required=True)
    adaptive_gate.add_argument("--candidate-evidence")
    adaptive_gate.add_argument("--independent-review-record")
    adaptive_gate.add_argument("--request-human-input", action="store_true")
    adaptive_gate.set_defaults(func=cmd_adaptive_decision_gate)

    adaptive_review = subparsers.add_parser("adaptive-decision-review")
    adaptive_review.add_argument("--target-thread", required=True)
    adaptive_review.add_argument("--review-json", required=True)
    adaptive_review.set_defaults(func=cmd_adaptive_decision_review)

    weekly_report = subparsers.add_parser("weekly-report")
    weekly_report.add_argument("--target-thread", required=True)
    weekly_report.add_argument(
        "--action",
        choices=("prepare", "finalize", "verify", "configure"),
        required=True,
    )
    weekly_report.add_argument("--start")
    weekly_report.add_argument("--end")
    weekly_report.add_argument("--days", type=int, default=7)
    weekly_report.add_argument("--since-inception", action="store_true")
    weekly_report.add_argument("--report-id")
    weekly_report.add_argument("--review-base64")
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
