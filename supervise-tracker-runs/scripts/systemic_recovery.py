#!/usr/bin/env python3
"""Derived Software Factory recovery and outcome-effectiveness projections.

This module has no owner side effects.  ``supervision_log.py`` supplies current,
canonical event and policy records, persists the derived records, and retains
all routing, release, range, tracker, and target-writer authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
OWNER_CLASSES = {
    "target-owned",
    "software-factory-owned",
    "mixed",
    "reserved-external",
}
NEXT_EFFECTIVENESS_TRIGGERS = (
    "materially-different-treatment",
    "attempted-hold-violation",
    "new-independent-outcome-evidence",
)
EFFECTIVENESS_CRITERIA = {
    "disposition-change",
    "material-finding-reduction",
    "disposition-and-finding-reduction",
}


class RecoveryError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_text(value: Any, *, label: str, maximum: int = 240) -> str:
    if not isinstance(value, str):
        raise RecoveryError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > maximum:
        raise RecoveryError(f"{label} is missing or too long")
    return cleaned


def safe_id(value: Any, *, label: str) -> str:
    text = exact_text(value, label=label, maximum=160)
    if SAFE_ID.fullmatch(text) is None:
        raise RecoveryError(f"{label} is not a bounded identifier")
    return text


def exact_sha256(value: Any, *, label: str) -> str:
    text = exact_text(value, label=label, maximum=64)
    if SHA256.fullmatch(text) is None:
        raise RecoveryError(f"{label} must be an exact SHA-256")
    return text


def _exact_keys(value: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    if set(value) != keys:
        raise RecoveryError(f"{label} shape differs")


def _string_list(
    value: Any,
    *,
    label: str,
    minimum: int = 1,
    maximum: int = 16,
) -> list[str]:
    if (
        not isinstance(value, list)
        or not minimum <= len(value) <= maximum
    ):
        raise RecoveryError(f"{label} must be a bounded array")
    items = [safe_id(item, label=label) for item in value]
    if len(items) != len(set(items)):
        raise RecoveryError(f"{label} repeats an identifier")
    return items


def owner_evidence_from_failure_mode(
    failure_mode: Mapping[str, Any],
) -> dict[str, Any]:
    owner_class = failure_mode.get("owner_class")
    if owner_class not in OWNER_CLASSES:
        raise RecoveryError(
            "Recovery classification requires canonical failure owner evidence"
        )
    failed_owner = safe_id(failure_mode.get("failed_owner"), label="failed owner")
    failed_contract = safe_id(
        failure_mode.get("failed_contract"), label="failed contract"
    )
    observed_revision = safe_id(
        failure_mode.get("observed_revision"), label="observed revision"
    )
    accepted_revision = safe_id(
        failure_mode.get("accepted_revision"), label="accepted revision"
    )
    recovery_trigger = safe_id(
        failure_mode.get("recovery_trigger"), label="recovery trigger"
    )
    safe_frontier = _string_list(
        failure_mode.get("safe_frontier"), label="safe frontier"
    )
    subjects_value = failure_mode.get("ownership_subjects")
    if not isinstance(subjects_value, list) or not subjects_value:
        raise RecoveryError("Recovery classification requires owner subjects")
    subjects: list[dict[str, str]] = []
    identities: set[str] = set()
    for item in subjects_value:
        if not isinstance(item, Mapping):
            raise RecoveryError("Recovery owner subject must be an object")
        _exact_keys(
            item,
            {"subject", "owner_class"},
            label="recovery owner subject",
        )
        subject = safe_id(item.get("subject"), label="recovery subject")
        subject_owner = item.get("owner_class")
        if subject_owner not in OWNER_CLASSES - {"mixed"}:
            raise RecoveryError("Recovery subject owner is unsupported")
        if subject in identities:
            raise RecoveryError("Recovery owner subject is duplicated")
        identities.add(subject)
        subjects.append({"subject": subject, "owner_class": str(subject_owner)})
    subject_owners = {item["owner_class"] for item in subjects}
    if owner_class == "mixed":
        if len(subject_owners) < 2:
            raise RecoveryError("Mixed recovery ownership was not split by subject")
    elif subject_owners != {owner_class}:
        raise RecoveryError("Recovery subject ownership contradicts its disposition")
    return {
        "owner_class": str(owner_class),
        "failed_owner": failed_owner,
        "failed_contract": failed_contract,
        "observed_revision": observed_revision,
        "accepted_revision": accepted_revision,
        "recovery_trigger": recovery_trigger,
        "safe_frontier": safe_frontier,
        "ownership_subjects": subjects,
    }


def classify_recovery(
    *,
    incident: Mapping[str, Any],
    incident_head: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    incident_id = safe_id(incident_head.get("incident_id"), label="incident ID")
    if incident.get("incident_id") != incident_id:
        raise RecoveryError("Recovery incident history differs from its current head")
    if incident_head.get("status") in {
        "corrected",
        "false-positive",
        "accepted-risk",
        "superseded",
        "closed",
        "resolved",
    }:
        raise RecoveryError("Recovery classification requires an open incident")
    failure_mode = incident.get("failure_mode")
    if not isinstance(failure_mode, Mapping):
        raise RecoveryError("Recovery incident lacks canonical failure-mode evidence")
    owner = owner_evidence_from_failure_mode(failure_mode)
    policy_root = exact_sha256(policy.get("policy_sha256"), label="policy SHA-256")
    mission = policy.get("mission_binding")
    if not isinstance(mission, Mapping):
        raise RecoveryError("Recovery classification requires a bound mission")
    mission_root = exact_sha256(mission.get("mission_root"), label="mission root")
    incident_head_root = exact_sha256(
        incident_head.get("record_sha256"), label="incident head SHA-256"
    )
    owner_class = owner["owner_class"]
    if owner_class == "software-factory-owned":
        next_action = "open-software-factory-recovery"
    elif owner_class == "target-owned":
        next_action = "route-target-owned-subjects"
    elif owner_class == "reserved-external":
        next_action = "route-reserved-subjects-to-decision-owner"
    else:
        next_action = "split-and-route-subjects-by-owner"
    factory_subjects = [
        item["subject"]
        for item in owner["ownership_subjects"]
        if item["owner_class"] == "software-factory-owned"
    ]
    material = {
        "schema_version": 1,
        "kind": "software-factory-recovery-classification",
        "incident_id": incident_id,
        "incident_head_record_id": safe_id(
            incident_head.get("record_id"), label="incident head record"
        ),
        "incident_head_record_sha256": incident_head_root,
        "failure_mode_id": safe_id(
            failure_mode.get("failure_mode_id"), label="failure mode ID"
        ),
        "mission_root": mission_root,
        "policy_sha256": policy_root,
        **owner,
        "factory_subjects": factory_subjects,
        "required_target_posture": "in-progress",
        "manual_resume_required": False,
        "human_input_required": False,
        "next_action": next_action,
    }
    material["recovery_id"] = "RECOVERY-" + digest(material)[:24]
    material["classification_root_sha256"] = digest(material)
    return material


def _validated_outcome(
    value: Any,
    *,
    label: str,
    allowed_reviewers: set[str],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{label} must be an object")
    _exact_keys(
        value,
        {
            "source_record",
            "source_sha256",
            "reviewer_id",
            "disposition",
            "material_findings",
        },
        label=label,
    )
    reviewer_id = safe_id(value.get("reviewer_id"), label=f"{label} reviewer")
    if reviewer_id not in allowed_reviewers:
        raise RecoveryError(f"{label} reviewer is not an independent bound owner")
    findings = _string_list(
        value.get("material_findings"), label=f"{label} material findings"
    )
    result = {
        "source_record": safe_id(
            value.get("source_record"), label=f"{label} source record"
        ),
        "source_sha256": exact_sha256(
            value.get("source_sha256"), label=f"{label} source root"
        ),
        "reviewer_id": reviewer_id,
        "disposition": safe_id(
            value.get("disposition"), label=f"{label} disposition"
        ),
        "material_findings": sorted(findings),
    }
    result["finding_set_fingerprint_sha256"] = digest(
        {
            "disposition": result["disposition"],
            "material_findings": result["material_findings"],
        }
    )
    return result


def _validated_hypothesis(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{label} must be an object")
    _exact_keys(
        value,
        {"causal_mechanism", "changed_levers", "expected_effect"},
        label=label,
    )
    result = {
        "causal_mechanism": safe_id(
            value.get("causal_mechanism"), label=f"{label} causal mechanism"
        ),
        "changed_levers": sorted(
            _string_list(
                value.get("changed_levers"), label=f"{label} changed levers"
            )
        ),
        "expected_effect": safe_id(
            value.get("expected_effect"), label=f"{label} expected effect"
        ),
    }
    result["identity_sha256"] = digest(result)
    return result


def _validated_criterion(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RecoveryError("Effectiveness criterion must be an object")
    _exact_keys(
        value,
        {
            "criterion",
            "target_disposition",
            "minimum_findings_removed",
        },
        label="effectiveness criterion",
    )
    criterion = value.get("criterion")
    if criterion not in EFFECTIVENESS_CRITERIA:
        raise RecoveryError("Effectiveness criterion is unsupported")
    minimum = value.get("minimum_findings_removed")
    if type(minimum) is not int or not 0 <= minimum <= 32:
        raise RecoveryError("Effectiveness finding threshold is invalid")
    target = safe_id(
        value.get("target_disposition"), label="target disposition"
    )
    result = {
        "criterion": criterion,
        "target_disposition": target,
        "minimum_findings_removed": minimum,
    }
    result["criterion_sha256"] = digest(result)
    return result


def evaluate_outcome_effectiveness(
    packet: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    _exact_keys(
        packet,
        {
            "schema_version",
            "kind",
            "implementation_owner_id",
            "primary_observable_outcome",
            "baseline_outcomes",
            "prior_treatment_hypothesis",
            "candidate_treatment_hypothesis",
            "effectiveness_criterion",
            "current_outcome",
        },
        label="outcome-effectiveness packet",
    )
    if (
        packet.get("schema_version") != 1
        or packet.get("kind") != "outcome-effectiveness-admission"
    ):
        raise RecoveryError("Outcome-effectiveness packet identity differs")
    target_id = safe_id(policy.get("target_thread_id"), label="target thread")
    owner_id = safe_id(
        packet.get("implementation_owner_id"), label="implementation owner"
    )
    if owner_id != target_id:
        raise RecoveryError("Outcome-effectiveness packet names another owner")
    runtime = policy.get("runtime")
    if not isinstance(runtime, Mapping):
        raise RecoveryError("Outcome-effectiveness policy lacks runtime owners")
    allowed_reviewers = {
        str(runtime.get("base_reviewer_thread_id", "")),
        str(runtime.get("reviewer_thread_id", "")),
    } - {""}
    disallowed = {
        target_id,
        str(runtime.get("watcher_thread_id", "")),
        str(runtime.get("fix_executor_thread_id", "")),
    }
    if not allowed_reviewers or allowed_reviewers & disallowed:
        raise RecoveryError("Outcome-effectiveness reviewer roles are not independent")
    outcomes_value = packet.get("baseline_outcomes")
    if not isinstance(outcomes_value, list) or not 2 <= len(outcomes_value) <= 8:
        raise RecoveryError("Outcome baseline requires consecutive accepted evidence")
    outcomes = [
        _validated_outcome(
            item,
            label=f"baseline outcome {index}",
            allowed_reviewers=allowed_reviewers,
        )
        for index, item in enumerate(outcomes_value, start=1)
    ]
    if len({item["source_record"] for item in outcomes}) != len(outcomes):
        raise RecoveryError("Outcome baseline repeats a source record")
    baseline_fingerprints = {
        item["finding_set_fingerprint_sha256"] for item in outcomes
    }
    outcome_unchanged = len(baseline_fingerprints) == 1
    prior = _validated_hypothesis(
        packet.get("prior_treatment_hypothesis"), label="prior treatment"
    )
    candidate = _validated_hypothesis(
        packet.get("candidate_treatment_hypothesis"), label="candidate treatment"
    )
    criterion = _validated_criterion(packet.get("effectiveness_criterion"))
    primary_outcome = safe_id(
        packet.get("primary_observable_outcome"),
        label="primary observable outcome",
    )
    same_hypothesis = prior["identity_sha256"] == candidate["identity_sha256"]
    current_value = packet.get("current_outcome")
    current = (
        None
        if current_value is None
        else _validated_outcome(
            current_value,
            label="current outcome",
            allowed_reviewers=allowed_reviewers,
        )
    )
    baseline = outcomes[-1]
    removed: list[str] = []
    added: list[str] = []
    criterion_met: bool | None = None
    if current is not None:
        removed = sorted(
            set(baseline["material_findings"])
            - set(current["material_findings"])
        )
        added = sorted(
            set(current["material_findings"])
            - set(baseline["material_findings"])
        )
        disposition_met = current["disposition"] == criterion["target_disposition"]
        finding_met = len(removed) >= criterion["minimum_findings_removed"]
        if criterion["criterion"] == "disposition-change":
            criterion_met = disposition_met
        elif criterion["criterion"] == "material-finding-reduction":
            criterion_met = finding_met
        else:
            criterion_met = disposition_met and finding_met
    hold = outcome_unchanged and same_hypothesis and current is None
    if hold:
        status = "outcome-unchanged"
        effectiveness = "ineffective"
        candidate_posture = "diagnostic"
        effect_allowed = False
    elif current is None:
        status = "treatment-admitted"
        effectiveness = "unresolved"
        candidate_posture = "eligible"
        effect_allowed = True
    else:
        status = "effectiveness-observed"
        effectiveness = "effective" if criterion_met else "ineffective"
        candidate_posture = "observed"
        effect_allowed = False
    material = {
        "schema_version": 1,
        "kind": "outcome-effectiveness-gate",
        "implementation_owner_id": owner_id,
        "primary_observable_outcome": primary_outcome,
        "baseline_outcome_records": [item["source_record"] for item in outcomes],
        "baseline_outcome_root_sha256": digest(outcomes),
        "baseline_disposition": baseline["disposition"],
        "baseline_finding_set_fingerprint_sha256": baseline[
            "finding_set_fingerprint_sha256"
        ],
        "outcome_unchanged": outcome_unchanged,
        "prior_treatment_hypothesis_sha256": prior["identity_sha256"],
        "candidate_treatment_hypothesis_sha256": candidate["identity_sha256"],
        "same_treatment_hypothesis": same_hypothesis,
        "effectiveness_criterion_sha256": criterion["criterion_sha256"],
        "current_outcome_record": current["source_record"] if current else None,
        "current_disposition": current["disposition"] if current else None,
        "current_finding_set_fingerprint_sha256": (
            current["finding_set_fingerprint_sha256"] if current else None
        ),
        "material_findings_removed": removed,
        "material_findings_added": added,
        "criterion_met": criterion_met,
        "status": status,
        "effectiveness": effectiveness,
        "candidate_posture": candidate_posture,
        "effect_allowed": effect_allowed,
        "next_wake_triggers": list(NEXT_EFFECTIVENESS_TRIGGERS),
        "carry_forward": False,
    }
    material["gate_root_sha256"] = digest(material)
    return material
