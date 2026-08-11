#!/usr/bin/env python3
"""Read-only target-class composition for the accepted adaptive protocol."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


class TargetClassProtocolError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[2]
SUPERVISION_PATH = ROOT / "supervise-tracker-runs" / "scripts" / "supervision_log.py"
PROGRAM_REVISION_PATH = (
    ROOT / "author-implementation-trackers" / "scripts" / "program_revision.py"
)
FACTORY_EVOLUTION_PATH = (
    ROOT / "supervise-tracker-runs" / "scripts" / "factory_evolution.py"
)
DEFAULT_SKILLS_ROOT = Path.home() / ".codex" / "skills"
SKILL_IDS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
)
TARGET_CLASSES = {"target-repository", "software-factory"}
FACTORY_EVALUATED_DISPOSITIONS = {
    "correct-inline",
    "compare-candidate",
    "cutover-candidate",
}
MAX_SKILL_FILES = 256
MAX_SKILL_BYTES = 4 * 1024 * 1024


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TargetClassProtocolError(f"{name} owner is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


supervision = _load_module("target_class_supervision", SUPERVISION_PATH)
program_revision = _load_module("target_class_program_revision", PROGRAM_REVISION_PATH)
factory_evolution = _load_module("target_class_factory_evolution", FACTORY_EVOLUTION_PATH)


def digest(value: Any) -> str:
    return supervision.digest(value)


def _exact_fields(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise TargetClassProtocolError(f"{label} shape differs")
    return value


def _exact_sha(value: Any, label: str) -> str:
    try:
        return supervision.exact_sha256(value, label=label)
    except Exception as error:
        raise TargetClassProtocolError(f"{label} differs") from error


def _safe_id(value: Any, label: str) -> str:
    if type(value) is not str:
        raise TargetClassProtocolError(f"{label} must be a string")
    try:
        return supervision.safe_id(value, label=label)
    except Exception as error:
        raise TargetClassProtocolError(f"{label} differs") from error


def _manifest_root(source: Path) -> tuple[str, int, int]:
    records: list[dict[str, Any]] = []
    aggregate = 0
    paths = sorted(source.rglob("*"))
    names = [path.relative_to(source).as_posix() for path in paths]
    for path, relative in zip(paths, names):
        if path.is_symlink():
            raise TargetClassProtocolError("live skill source contains a nested symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise TargetClassProtocolError("live skill source contains a non-file entry")
        descriptor = -1
        try:
            descriptor = os.open(
                path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            )
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise TargetClassProtocolError(
                    "live skill source contains a non-file entry"
                )
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                raw = handle.read(MAX_SKILL_BYTES + 1)
                after = os.fstat(handle.fileno())
        except OSError as error:
            raise TargetClassProtocolError(
                "live skill source changed while reading"
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
        )
        try:
            current = os.lstat(path)
        except OSError as error:
            raise TargetClassProtocolError(
                "live skill source changed while reading"
            ) from error
        if (
            identity(before) != identity(after)
            or identity(after) != identity(current)
            or not stat.S_ISREG(current.st_mode)
        ):
            raise TargetClassProtocolError("live skill source changed while reading")
        aggregate += len(raw)
        if len(records) >= MAX_SKILL_FILES or aggregate > MAX_SKILL_BYTES:
            raise TargetClassProtocolError("live skill source exceeds its bounded manifest")
        records.append(
            {
                "path": relative,
                "mode": stat.S_IMODE(after.st_mode),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if names != [
        path.relative_to(source).as_posix() for path in sorted(source.rglob("*"))
    ]:
        raise TargetClassProtocolError("live skill source changed while reading")
    if not records or not any(item["path"] == "SKILL.md" for item in records):
        raise TargetClassProtocolError("live skill source lacks SKILL.md")
    return digest(records), len(records), aggregate


def resolve_live_skill_sources(
    skills_root: Path = DEFAULT_SKILLS_ROOT,
) -> list[dict[str, Any]]:
    """Resolve and content-bind each stable live skill discovery link once."""

    root = skills_root.resolve(strict=True)
    records: list[dict[str, Any]] = []
    release_roots: set[str] = set()
    for skill_id in SKILL_IDS:
        discovery = root / skill_id
        if not discovery.is_symlink():
            raise TargetClassProtocolError("live skill discovery entry is not a stable symlink")
        source = discovery.resolve(strict=True)
        if not source.is_dir() or source.name != skill_id:
            raise TargetClassProtocolError("live skill source identity differs")
        manifest_root, file_count, byte_count = _manifest_root(source)
        if discovery.resolve(strict=True) != source:
            raise TargetClassProtocolError("live skill source changed while reading")
        release_roots.add(str(source.parent))
        records.append(
            {
                "skill_id": skill_id,
                "discovery_path": str(discovery),
                "source_path": str(source),
                "source_manifest_root": manifest_root,
                "file_count": file_count,
                "byte_count": byte_count,
            }
        )
    if len(release_roots) != 1:
        raise TargetClassProtocolError("live skills do not resolve to one accepted release")
    return records


def _normalize_findings(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 16:
        raise TargetClassProtocolError(f"{label} findings differ")
    result: list[dict[str, str]] = []
    for item in value:
        _exact_fields(item, {"finding_id", "statement", "evidence_root"}, label)
        finding_id = _safe_id(item["finding_id"], f"{label} finding ID")
        statement = item["statement"]
        if (
            type(statement) is not str
            or not statement
            or statement != statement.strip()
            or len(statement) > 600
        ):
            raise TargetClassProtocolError(f"{label} finding statement differs")
        result.append(
            {
                "finding_id": finding_id,
                "statement": statement,
                "evidence_root": _exact_sha(
                    item["evidence_root"], f"{label} finding evidence root"
                ),
            }
        )
    if result != sorted(result, key=lambda item: item["finding_id"]) or len(
        {item["finding_id"] for item in result}
    ) != len(result):
        raise TargetClassProtocolError(f"{label} finding order differs")
    return result


def validate_target_class_protocol(
    policy: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    skills_root: Path = DEFAULT_SKILLS_ROOT,
) -> dict[str, Any]:
    """Compose existing owners without conferring release or promotion authority."""

    expected = {
        "schema_version",
        "kind",
        "target_class",
        "decision_packet",
        "program_revision_packet",
        "factory_skill_sources",
        "factory_evolution_bundle",
        "capability_context",
        "claimed_improvement",
        "factory_alignment_findings",
        "target_product_findings",
    }
    source = _exact_fields(packet, expected, "target-class packet")
    if source.get("schema_version") != 1 or source.get("kind") != "software-factory-target-class-protocol":
        raise TargetClassProtocolError("target-class packet kind differs")
    target_class = source.get("target_class")
    if target_class not in TARGET_CLASSES:
        raise TargetClassProtocolError("target class differs")
    control = policy.get("adaptive_decision_control")
    if not isinstance(control, Mapping) or control.get("target_class") != target_class:
        raise TargetClassProtocolError("target class differs from canonical policy")
    decision_packet = source["decision_packet"]
    try:
        result = supervision._adaptive_decision_posture(
            policy,
            decision_packet,
            active_candidate_fingerprints=[],
        )
    except Exception as error:
        raise TargetClassProtocolError("adaptive decision evidence is not current") from error
    decision = decision_packet["decision_evidence"]
    disposition = str(decision["disposition"])
    candidate = decision_packet["candidate_evidence"]
    program_packet = source["program_revision_packet"]
    if disposition == "amend-structure":
        try:
            program_packet = program_revision.validate_stored_packet(program_packet)
        except Exception as error:
            raise TargetClassProtocolError("program revision packet is not valid") from error
        if (
            program_packet["target_class"] != target_class
            or program_packet["target_thread_id"] != policy.get("target_thread_id")
            or program_packet["repository_root"] != decision["target_repository_root"]
            or program_packet["target_revision_root"] != decision["target_revision_root"]
            or program_packet["decision_fingerprint"] != result["decision_fingerprint"]
            or program_packet["decision_currentness_root"]
            != result["decision_currentness_root"]
        ):
            raise TargetClassProtocolError("program revision differs from the decision")
        if target_class == "software-factory" and (
            program_packet["author_id"] != decision.get("proposer_author_id")
            or program_packet["application_owner_id"]
            != decision["implementation_owner_id"]
        ):
            raise TargetClassProtocolError(
                "software-factory structural roles differ from the decision"
            )
    elif program_packet is not None:
        raise TargetClassProtocolError("program revision requires amend-structure")
    factory_findings = _normalize_findings(
        source["factory_alignment_findings"], "factory-alignment"
    )
    product_findings = _normalize_findings(
        source["target_product_findings"], "target-product"
    )
    evolution_disposition: Optional[str] = None
    adoption_eligible = False
    if target_class == "target-repository":
        if source["factory_skill_sources"] or source["factory_evolution_bundle"] is not None:
            raise TargetClassProtocolError("ordinary target work invoked Factory evolution")
        if factory_findings:
            raise TargetClassProtocolError("ordinary target work claimed Factory ownership")
        protected_roots = [
            skills_root.resolve(strict=True),
            (Path.home() / ".codex").resolve(),
            ROOT.resolve(strict=True),
        ]
        repository_root = Path(decision["target_repository_root"]).resolve(strict=True)
        if any(
            repository_root == root or root in repository_root.parents
            for root in protected_roots
        ):
            raise TargetClassProtocolError("ordinary target is a Software Factory owner")
        for affected in decision["affected_scope"]:
            path = Path(affected["path"]).resolve(strict=True)
            if any(path == root or root in path.parents for root in protected_roots):
                raise TargetClassProtocolError("ordinary target scope reaches a live Factory skill")
    else:
        live_sources = (
            []
            if disposition == "continue-unchanged"
            else resolve_live_skill_sources(skills_root)
        )
        if source["factory_skill_sources"] != live_sources:
            raise TargetClassProtocolError("software-factory skill sources are stale")
        if disposition != "continue-unchanged":
            review = decision_packet["independent_review"]
            if not isinstance(review, Mapping):
                raise TargetClassProtocolError("software-factory review is absent")
            proposer = decision.get("proposer_author_id")
            implementer = decision.get("implementation_owner_id")
            reviewer = review.get("reviewer_id")
            evaluator = review.get("evaluator_id")
            roles = [proposer, implementer, reviewer, evaluator]
            if any(type(item) is not str for item in roles) or len(set(roles)) != 4:
                raise TargetClassProtocolError("software-factory roles are not independent")
            evolution = source["factory_evolution_bundle"]
            if disposition in FACTORY_EVALUATED_DISPOSITIONS:
                try:
                    evolution = factory_evolution.verify_evolution_bundle(evolution)
                except Exception as error:
                    raise TargetClassProtocolError("Factory evolution bundle is not current") from error
                evolution_review = evolution["review.json"]
                evaluation = evolution["evaluation.json"]
                experiment = evolution_review["experiment"]
                if (
                    experiment["proposer_id"] != proposer
                    or experiment["implementer_id"] != implementer
                    or experiment["evaluator_id"] != evaluator
                    or evaluation["evaluator_id"] != evaluator
                ):
                    raise TargetClassProtocolError("Factory evolution roles differ from the decision")
                evolution_disposition = str(evaluation["disposition"])
                adoption_eligible = evolution_disposition == "promote"
            elif evolution is not None:
                raise TargetClassProtocolError("Factory evolution is not required for this path")
        elif source["factory_evolution_bundle"] is not None:
            raise TargetClassProtocolError("unchanged Factory work opened an evolution cycle")
    capability_root: Optional[str] = None
    improvement_established = False
    capability_context = source["capability_context"]
    if capability_context is not None:
        context = _exact_fields(
            capability_context,
            {
                "path",
                "target_thread_id",
                "mission_root",
                "state_fingerprint",
                "current_revision",
            },
            "capability context",
        )
        if context["target_thread_id"] != policy.get("target_thread_id"):
            raise TargetClassProtocolError("capability target differs")
        try:
            capability, capability_root = supervision.load_capability_reconciliation(
                context["path"],
                target_thread=context["target_thread_id"],
                mission_root=context["mission_root"],
                state_fingerprint=context["state_fingerprint"],
                current_revision=context["current_revision"],
                policy=policy,
            )
        except Exception as error:
            raise TargetClassProtocolError("current behavior is not reconciled") from error
        if context["current_revision"] != decision["target_revision"]:
            raise TargetClassProtocolError("capability revision differs from the decision")
        improvement_established = capability["completion_posture"] == "verified"
    claimed_improvement = source["claimed_improvement"]
    if type(claimed_improvement) is not bool:
        raise TargetClassProtocolError("claimed improvement must be boolean")
    if claimed_improvement and not improvement_established:
        raise TargetClassProtocolError(
            "process-only evidence cannot establish target improvement"
        )
    if improvement_established and not claimed_improvement:
        raise TargetClassProtocolError("current behavior claim is not explicit")
    application_action: Optional[str] = None
    if disposition == "correct-inline":
        application_action = "normal-owner-inline-correction"
    elif disposition == "compare-candidate":
        application_action = "retain-comparison-with-incumbent-authoritative"
    elif disposition == "amend-structure":
        application_action = "normal-authoring-owner-application"
    elif disposition == "cutover-candidate":
        application_action = (
            "normal-target-owner-cutover"
            if target_class == "target-repository"
            else "separately-governed-factory-adoption"
        )
    application_handoff = (
        {
            "target_class": target_class,
            "disposition": disposition,
            "decision_fingerprint": result["decision_fingerprint"],
            "decision_currentness_root": result["decision_currentness_root"],
            "candidate_evidence_root": result["candidate_evidence_root"],
            "program_revision_root": (
                program_packet.get("packet_root") if program_packet else None
            ),
            "application_action": application_action,
            "application_owner_id": (
                decision["implementation_owner_id"]
                if target_class == "target-repository"
                else None
            ),
            "application_authorized": False,
            "candidate_authoritative": False,
            "promotion_authorized": False,
        }
        if application_action is not None
        else None
    )
    material = {
        "schema_version": 1,
        "kind": "software-factory-target-class-result",
        "target_class": target_class,
        "target_repository_root": decision["target_repository_root"],
        "target_revision_root": decision["target_revision_root"],
        "disposition": disposition,
        "decision_fingerprint": result["decision_fingerprint"],
        "decision_currentness_root": result["decision_currentness_root"],
        "candidate_evidence_root": candidate.get("evidence_root") if candidate else None,
        "program_revision_root": program_packet.get("packet_root") if program_packet else None,
        "application_handoff_root": (
            digest(application_handoff) if application_handoff else None
        ),
        "application_handoff": application_handoff,
        "factory_skill_sources_root": digest(source["factory_skill_sources"]),
        "factory_evolution_disposition": evolution_disposition,
        "factory_alignment_findings_root": digest(factory_findings),
        "target_product_findings_root": digest(product_findings),
        "capability_reconciliation_root": capability_root,
        "application_authorized": bool(result.get("application_authorized")),
        "candidate_authoritative": False,
        "promotion_authorized": False,
        "adoption_eligible": adoption_eligible,
        "improvement_established": improvement_established,
        "next_owner": (
            decision["implementation_owner_id"]
            if application_action is not None and target_class == "target-repository"
            else None
        ),
        "resume_action": (
            "continue-current-block"
            if disposition == "continue-unchanged"
            else application_action
        ),
    }
    return {**material, "protocol_root": digest(material)}
