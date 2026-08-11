#!/usr/bin/env python3
"""Read-only target-class composition for the accepted adaptive protocol."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
from pathlib import Path
from types import SimpleNamespace
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
CANONICAL_CODEX_ROOT = Path("/Users/ethanstillman/.codex")
DEFAULT_SKILLS_ROOT = CANONICAL_CODEX_ROOT / "skills"
DEFAULT_SUPERVISION_ROOT = CANONICAL_CODEX_ROOT / "supervision" / "tracker-runs"
SKILL_IDS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
)
TARGET_CLASSES = {"target-repository", "software-factory"}
FACTORY_EVALUATED_DISPOSITIONS = {
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


def _live_skill_identity(skills_root: Path) -> str:
    """Capture bounded source identity without rereading skill file content."""

    root = skills_root.resolve(strict=True)
    records: list[dict[str, Any]] = []
    for skill_id in SKILL_IDS:
        discovery = root / skill_id
        try:
            link = discovery.lstat()
            source = discovery.resolve(strict=True)
        except OSError as error:
            raise TargetClassProtocolError(
                "live skill identity changed while reading"
            ) from error
        if not stat.S_ISLNK(link.st_mode) or not source.is_dir():
            raise TargetClassProtocolError("live skill identity differs")
        records.append(
            {
                "skill_id": skill_id,
                "entry": ".",
                "source_path": str(source),
                "mode": stat.S_IMODE(link.st_mode),
                "device": link.st_dev,
                "inode": link.st_ino,
                "size": link.st_size,
                "mtime_ns": link.st_mtime_ns,
            }
        )
        paths = sorted(source.rglob("*"))
        if len(paths) > MAX_SKILL_FILES * 2:
            raise TargetClassProtocolError(
                "live skill identity exceeds its bounded manifest"
            )
        for path in paths:
            try:
                current = path.lstat()
            except OSError as error:
                raise TargetClassProtocolError(
                    "live skill identity changed while reading"
                ) from error
            records.append(
                {
                    "skill_id": skill_id,
                    "entry": path.relative_to(source).as_posix(),
                    "source_path": str(source),
                    "mode": current.st_mode,
                    "device": current.st_dev,
                    "inode": current.st_ino,
                    "size": current.st_size,
                    "mtime_ns": current.st_mtime_ns,
                }
            )
    return digest(records)


def _normalize_findings(
    value: Any,
    label: str,
    *,
    allowed_roots: set[str],
    required_root: Optional[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 16:
        raise TargetClassProtocolError(f"{label} findings differ")
    if required_root is not None and not value:
        raise TargetClassProtocolError(f"{label} findings are required")
    result: list[dict[str, Any]] = []
    for item in value:
        _exact_fields(item, {"finding_id", "statement", "evidence_roots"}, label)
        finding_id = _safe_id(item["finding_id"], f"{label} finding ID")
        statement = item["statement"]
        if (
            type(statement) is not str
            or not statement
            or statement != statement.strip()
            or len(statement) > 600
        ):
            raise TargetClassProtocolError(f"{label} finding statement differs")
        roots = item["evidence_roots"]
        if (
            not isinstance(roots, list)
            or not roots
            or len(roots) > 8
            or any(type(root) is not str for root in roots)
            or roots != sorted(set(roots))
        ):
            raise TargetClassProtocolError(f"{label} finding evidence differs")
        normalized_roots = [
            _exact_sha(root, f"{label} finding evidence root") for root in roots
        ]
        if not set(normalized_roots).issubset(allowed_roots):
            raise TargetClassProtocolError(
                f"{label} finding evidence is not claim-bound"
            )
        result.append(
            {
                "finding_id": finding_id,
                "statement": statement,
                "evidence_roots": normalized_roots,
            }
        )
    if result != sorted(result, key=lambda item: item["finding_id"]) or len(
        {item["finding_id"] for item in result}
    ) != len(result):
        raise TargetClassProtocolError(f"{label} finding order differs")
    if required_root is not None and not any(
        required_root in item["evidence_roots"] for item in result
    ):
        raise TargetClassProtocolError(f"{label} findings omit current evidence")
    return result


def _control_snapshot(
    target_thread: str,
) -> tuple[Path, dict[str, Any], list[dict[str, Any]], Any, Any, Any]:
    target = _safe_id(target_thread, "target thread")
    args = SimpleNamespace(root=str(DEFAULT_SUPERVISION_ROOT), target_thread=target)
    try:
        (
            directory,
            policy,
            policy_snapshot,
            all_events,
            event_snapshot,
            directory_snapshot,
        ) = supervision.load_control_snapshot(args)
    except Exception as error:
        raise TargetClassProtocolError(
            "canonical supervision state is unavailable"
        ) from error
    active_events = supervision.mission_scoped_events(directory, policy, all_events)
    return (
        directory,
        policy,
        active_events,
        policy_snapshot,
        event_snapshot,
        directory_snapshot,
    )


def validate_target_class_protocol(
    target_thread: str,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose existing owners without conferring release or promotion authority."""

    (
        directory,
        policy,
        active_events,
        policy_snapshot,
        event_snapshot,
        directory_snapshot,
    ) = _control_snapshot(target_thread)

    expected = {
        "schema_version",
        "kind",
        "target_class",
        "decision_record_id",
        "decision_packet",
        "program_revision_packet",
        "program_revision_review",
        "factory_skill_sources",
        "factory_evolution_id",
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
    governing_events = [
        item
        for item in active_events
        if item.get("kind") not in {"adaptive-decision", "adaptive-decision-review"}
    ]
    governing_root = (
        governing_events[-1].get("record_sha256") if governing_events else None
    )
    if decision_packet.get("governing_event_head_root") != governing_root:
        raise TargetClassProtocolError("adaptive governing event head is not current")
    try:
        result = supervision._adaptive_decision_posture(
            policy,
            decision_packet,
            active_candidate_fingerprints=supervision.adaptive_active_candidate_fingerprints(
                active_events
            ),
        )
    except Exception as error:
        raise TargetClassProtocolError("adaptive decision evidence is not current") from error
    decision_record_id = _safe_id(source["decision_record_id"], "decision record")
    all_decision_events = [
        item for item in active_events if item.get("kind") == "adaptive-decision"
    ]
    decision_events = [
        item
        for item in all_decision_events
        if item.get("decision_id") == result["decision_id"]
    ]
    decision_event = next(
        (
            item
            for item in decision_events
            if item.get("record_id") == decision_record_id
        ),
        None,
    )
    if decision_event is not None and decision_event.get(
        "independent_review_record"
    ) is not None:
        result = {
            **result,
            "independent_review_record": decision_event[
                "independent_review_record"
            ],
        }
        result["result_sha256"] = digest(
            {key: value for key, value in result.items() if key != "result_sha256"}
        )
    event_bindings = {
        "decision_fingerprint": result["decision_fingerprint"],
        "decision_currentness_root": result["decision_currentness_root"],
        "decision_semantics_root": result["decision_semantics_root"],
        "decision_source_root": result["decision_source_root"],
        "target_class": result["target_class"],
        "disposition": result["disposition"],
        "candidate_evidence_root": result["candidate_evidence_root"],
        "candidate_currentness_root": result["candidate_currentness_root"],
        "proposer_author_id": result["proposer_author_id"],
        "implementation_owner_id": result["implementation_owner_id"],
        "policy_sha256": result["policy_sha256"],
        "result_sha256": result["result_sha256"],
    }
    if (
        decision_event is None
        or not decision_events
        or decision_events[-1] != decision_event
        or not all_decision_events
        or all_decision_events[-1] != decision_event
        or any(decision_event.get(key) != value for key, value in event_bindings.items())
    ):
        raise TargetClassProtocolError(
            "adaptive decision differs from its canonical owner event"
        )
    review_record_id = decision_event.get("independent_review_record")
    if review_record_id is None:
        if decision_packet.get("independent_review") is not None:
            raise TargetClassProtocolError("adaptive review lacks a canonical event")
    else:
        try:
            canonical_review = supervision.resolve_adaptive_review(
                active_events, str(review_record_id), policy=policy
            )
        except Exception as error:
            raise TargetClassProtocolError(
                "adaptive review is not canonically current"
            ) from error
        if decision_packet.get("independent_review") != canonical_review:
            raise TargetClassProtocolError(
                "adaptive review differs from its canonical event"
            )
    decision = decision_packet["decision_evidence"]
    disposition = str(decision["disposition"])
    candidate = decision_packet["candidate_evidence"]
    repository_root = Path(decision["target_repository_root"]).resolve(strict=True)
    canonical_repository_root = Path(
        control["target_repository_root"]
    ).resolve(strict=True)
    if repository_root != canonical_repository_root:
        raise TargetClassProtocolError(
            "target class differs from the canonical repository owner"
        )
    program_packet = source["program_revision_packet"]
    program_review = source["program_revision_review"]
    if disposition == "amend-structure":
        try:
            program_packet = program_revision.validate_stored_packet(program_packet)
        except Exception as error:
            raise TargetClassProtocolError("program revision packet is not valid") from error
        mission = supervision.bound_mission(policy)
        if mission is None:
            raise TargetClassProtocolError("program revision lacks a bound mission")
        if (
            program_packet["target_class"] != target_class
            or program_packet["target_thread_id"] != policy.get("target_thread_id")
            or program_packet["mission_root"] != mission["mission_root"]
            or program_packet["policy_sha256"] != policy["policy_sha256"]
            or program_packet["decision_record_id"] != decision_event["record_id"]
            or program_packet["decision_record_sha256"]
            != decision_event["record_sha256"]
            or program_packet["repository_root"] != decision["target_repository_root"]
            or program_packet["target_revision"] != decision["target_revision"]
            or program_packet["target_revision_root"] != decision["target_revision_root"]
            or program_packet["target_revision_root"]
            != digest({"target_revision": program_packet["target_revision"]})
            or program_packet["decision_fingerprint"] != result["decision_fingerprint"]
            or program_packet["decision_currentness_root"]
            != result["decision_currentness_root"]
            or program_packet["application_precondition_root"]
            != result["application_precondition_root"]
            or program_packet["candidate_evidence_root"]
            != result["candidate_evidence_root"]
            or program_packet["decision_target_state_root"]
            != decision["decision_target_state_root"]
            or program_packet["current_target_state_root"]
            != decision["current_target_state_root"]
            or program_packet["authority_mode"]
            != result["adaptive_decision_mode"]
        ):
            raise TargetClassProtocolError("program revision differs from the decision")
        previous_tracker = Path(program_packet["previous_tracker_path"])
        try:
            previous_tracker = previous_tracker.resolve(strict=True)
            previous_tracker.relative_to(repository_root)
        except (OSError, ValueError) as error:
            raise TargetClassProtocolError(
                "program revision tracker differs from the target repository"
            ) from error
        affected_by_path = {
            Path(item["path"]).resolve(): item for item in decision["affected_scope"]
        }
        previous_scope = affected_by_path.get(previous_tracker)
        if (
            previous_scope is None
            or hashlib.sha256(previous_tracker.read_bytes()).hexdigest()
            != program_packet["previous_tracker_sha256"]
            or previous_scope["content_root"]
            != program_packet["previous_tracker_sha256"]
        ):
            raise TargetClassProtocolError(
                "program revision tracker is not current decision scope"
            )
        if target_class == "software-factory" and (
            program_packet["author_id"] != decision.get("proposer_author_id")
            or program_packet["application_owner_id"]
            != decision["implementation_owner_id"]
        ):
            raise TargetClassProtocolError(
                "software-factory structural roles differ from the decision"
            )
        if (
            program_packet["application_owner_id"]
            != decision["implementation_owner_id"]
        ):
            raise TargetClassProtocolError(
                "program revision application owner differs from the decision"
            )
        try:
            program_review = supervision.validate_program_revision_review(
                program_review, packet=program_packet
            )
        except Exception as error:
            raise TargetClassProtocolError(
                "program revision independent review is not valid"
            ) from error
        adaptive_review = decision_packet["independent_review"]
        if (
            program_review["disposition"] != "accepted"
            or program_review["finding_refs"]
            or program_review["reviewer_id"] != program_packet["reviewer_id"]
            or not isinstance(adaptive_review, Mapping)
            or program_review["reviewer_id"] != adaptive_review.get("reviewer_id")
            or program_review["reviewer_id"]
            in {
                decision.get("proposer_author_id"),
                decision["implementation_owner_id"],
            }
        ):
            raise TargetClassProtocolError(
                "program revision review roles or disposition differ"
            )
    elif program_packet is not None or program_review is not None:
        raise TargetClassProtocolError("program revision requires amend-structure")
    evolution_disposition: Optional[str] = None
    adoption_eligible = False
    live_sources: list[dict[str, Any]] = []
    live_skill_identity: Optional[str] = None
    live_sources_root = digest(live_sources)
    evolution_root: Optional[str] = None
    evolution_id: Optional[str] = None
    evolution_review_root: Optional[str] = None
    evaluation_root: Optional[str] = None
    experiment_root: Optional[str] = None
    proposer: Optional[str] = None
    implementer: Optional[str] = None
    reviewer: Optional[str] = None
    evaluator: Optional[str] = None
    if target_class == "target-repository":
        if source["factory_skill_sources"] or source["factory_evolution_id"] is not None:
            raise TargetClassProtocolError("ordinary target work invoked Factory evolution")
        if source["factory_alignment_findings"]:
            raise TargetClassProtocolError("ordinary target work claimed Factory ownership")
        protected_roots = [
            DEFAULT_SKILLS_ROOT.resolve(strict=True),
            CANONICAL_CODEX_ROOT.resolve(strict=True),
            ROOT.resolve(strict=True),
        ]
        if any(
            repository_root == root or root in repository_root.parents
            for root in protected_roots
        ):
            raise TargetClassProtocolError("ordinary target is a Software Factory owner")
        for affected in decision["affected_scope"]:
            path = Path(affected["path"]).resolve()
            if any(path == root or root in path.parents for root in protected_roots):
                raise TargetClassProtocolError("ordinary target scope reaches a live Factory skill")
    else:
        if disposition == "continue-unchanged":
            live_sources = []
        else:
            identity_before = _live_skill_identity(DEFAULT_SKILLS_ROOT)
            live_sources = resolve_live_skill_sources(DEFAULT_SKILLS_ROOT)
            live_skill_identity = _live_skill_identity(DEFAULT_SKILLS_ROOT)
            if live_skill_identity != identity_before:
                raise TargetClassProtocolError(
                    "software-factory skill sources changed"
                )
        if source["factory_skill_sources"] != live_sources:
            raise TargetClassProtocolError("software-factory skill sources are stale")
        live_sources_root = digest(live_sources)
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
            evolution_id = source["factory_evolution_id"]
            if disposition in FACTORY_EVALUATED_DISPOSITIONS:
                expected_evolution_id = (
                    "target-class-" + result["decision_fingerprint"][:20]
                )
                if evolution_id != expected_evolution_id:
                    raise TargetClassProtocolError(
                        "Factory evolution identity differs from the decision"
                    )
                try:
                    evolution_directory = supervision.factory_evolution_directory(
                        directory,
                        _safe_id(evolution_id, "Factory evolution ID"),
                    )
                    supervision.verify_factory_evolution_inventory(
                        evolution_directory
                    )
                    evolution_packet, evolution_review = (
                        supervision.verify_factory_evolution_finalize(
                            factory_evolution, evolution_directory
                        )
                    )
                    artifacts = supervision.require_factory_evolution_artifacts(
                        evolution_directory,
                        (
                            "evaluation.json",
                            "machine-report.json",
                            "manifest.json",
                        ),
                    )
                    evolution = {
                        "learning-packet.json": evolution_packet,
                        "review.json": evolution_review,
                        **artifacts,
                    }
                    evolution = factory_evolution.verify_evolution_bundle(evolution)
                except Exception as error:
                    raise TargetClassProtocolError("Factory evolution bundle is not current") from error
                evolution_review = evolution["review.json"]
                evaluation = evolution["evaluation.json"]
                experiment = evolution_review["experiment"]
                selected_id = evolution_review["selection"]["candidate_id"]
                expected_candidate_id = (
                    "adaptive-candidate-" + result["decision_fingerprint"][:20]
                )
                if candidate is None:
                    raise TargetClassProtocolError(
                        "Factory evolution lacks retained candidate behavior"
                    )
                expected_candidate_revision = candidate["candidate_root"]
                evolution_binding = {
                    "decision_id": result["decision_id"],
                    "decision_fingerprint": result["decision_fingerprint"],
                    "decision_currentness_root": result[
                        "decision_currentness_root"
                    ],
                    "target_revision_root": decision["target_revision_root"],
                    "live_skill_sources_root": live_sources_root,
                    "adaptive_candidate_evidence_root": result[
                        "candidate_evidence_root"
                    ],
                    "evolution_candidate_revision": expected_candidate_revision,
                }
                if (
                    experiment["proposer_id"] != proposer
                    or experiment["implementer_id"] != implementer
                    or experiment["evaluator_id"] != evaluator
                    or evaluation["evaluator_id"] != evaluator
                    or experiment["experiment_id"]
                    != "adaptive-experiment-"
                    + result["decision_fingerprint"][:20]
                    or selected_id != expected_candidate_id
                    or experiment["candidate_id"] != expected_candidate_id
                    or experiment["baseline_revision"] != live_sources_root
                    or experiment["candidate_revision"]
                    != expected_candidate_revision
                    or experiment["evidence_capture"]
                    != "target-class-binding:" + digest(evolution_binding)
                ):
                    raise TargetClassProtocolError(
                        "Factory evolution evidence differs from the decision"
                    )
                evolution_root = digest(evolution)
                evolution_review_root = evolution_review["review_root"]
                evaluation_root = evaluation["evaluation_root"]
                experiment_root = digest(experiment)
                evolution_disposition = str(evaluation["disposition"])
                adoption_eligible = evolution_disposition == "promote"
            elif evolution_id is not None:
                raise TargetClassProtocolError("Factory evolution is not required for this path")
        elif source["factory_evolution_id"] is not None:
            raise TargetClassProtocolError("unchanged Factory work opened an evolution cycle")
    capability_root: Optional[str] = None
    capability_completion_record_id: Optional[str] = None
    capability_completion_record_sha256: Optional[str] = None
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
                "completion_record_id",
                "completion_record_sha256",
                "capability_reconciliation_sha256",
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
        completion_id = _safe_id(
            context["completion_record_id"], "capability completion record"
        )
        completion = next(
            (
                item
                for item in active_events
                if item.get("record_id") == completion_id
            ),
            None,
        )
        latest_completion = supervision.latest_outcome_completion_record(
            active_events,
            state_fingerprint=context["state_fingerprint"],
        )
        if (
            completion is None
            or latest_completion != completion
            or completion.get("kind") != "check"
            or completion.get("category")
            != supervision.OUTCOME_COMPLETION_CATEGORY
            or completion.get("status") != "verified"
            or completion.get("policy_sha256") != policy["policy_sha256"]
            or completion.get("mission_root") != context["mission_root"]
            or completion.get("state_fingerprint")
            != context["state_fingerprint"]
            or completion.get("capability_reconciliation_revision")
            != context["current_revision"]
            or completion.get("capability_reconciliation_posture") != "verified"
            or completion.get("capability_reconciliation_gap_count") != 0
            or completion.get("capability_reconciliation_sha256")
            != capability_root
            or completion.get("capability_reconciliation_sha256")
            != context["capability_reconciliation_sha256"]
            or completion.get("record_sha256")
            != context["completion_record_sha256"]
            or completion.get("capability_reconciliation_implementation_owner_id")
            != decision["implementation_owner_id"]
            or completion.get("capability_reconciliation_reviewer_id")
            != capability["reviewer_id"]
        ):
            raise TargetClassProtocolError(
                "capability reconciliation lacks its canonical completion event"
            )
        capability_completion_record_id = completion["record_id"]
        capability_completion_record_sha256 = completion["record_sha256"]
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

    decision_roots = {
        _exact_sha(item["root_sha256"], "decision evidence reference")
        for item in decision["adjudicating_evidence_refs"]
    }
    allowed_finding_roots = {
        *decision_roots,
        decision["target_revision_root"],
        decision["decision_target_state_root"],
        decision["current_target_state_root"],
        decision_event["record_sha256"],
        result["decision_fingerprint"],
        result["decision_currentness_root"],
    }
    if candidate is not None:
        allowed_finding_roots.update(
            {
                candidate["candidate_root"],
                candidate["evidence_root"],
                candidate["currentness_root"],
                candidate["validation_root"],
                candidate["comparison_root"],
            }
        )
    if program_packet is not None:
        allowed_finding_roots.update(
            {program_packet["packet_root"], program_review["review_root"]}
        )
    for optional_root in (
        live_sources_root if live_sources else None,
        evolution_root,
        evolution_review_root,
        evaluation_root,
        experiment_root,
        capability_root,
        context["completion_record_sha256"]
        if capability_context is not None
        else None,
    ):
        if optional_root is not None:
            allowed_finding_roots.add(optional_root)

    product_required_root: Optional[str] = None
    if disposition != "continue-unchanged" or claimed_improvement:
        if candidate is not None:
            product_required_root = candidate["evidence_root"]
        elif program_packet is not None:
            product_required_root = program_packet["packet_root"]
        elif capability_root is not None:
            product_required_root = capability_root
        else:
            product_required_root = decision["current_target_state_root"]
    product_findings = _normalize_findings(
        source["target_product_findings"],
        "target-product",
        allowed_roots=allowed_finding_roots,
        required_root=product_required_root,
    )
    factory_findings = _normalize_findings(
        source["factory_alignment_findings"],
        "Factory-alignment",
        allowed_roots=allowed_finding_roots,
        required_root=(
            live_sources_root
            if target_class == "software-factory"
            and disposition != "continue-unchanged"
            else None
        ),
    )

    # Rehydrate every owner after the last read-only evidence load. A result is
    # not current merely because each input was valid at a different instant.
    (
        final_directory,
        final_policy,
        final_events,
        final_policy_snapshot,
        final_event_snapshot,
        final_directory_snapshot,
    ) = _control_snapshot(target_thread)
    if (
        final_directory != directory
        or final_policy != policy
        or final_events != active_events
        or final_policy_snapshot != policy_snapshot
        or final_event_snapshot != event_snapshot
        or final_directory_snapshot != directory_snapshot
    ):
        raise TargetClassProtocolError("canonical supervision currentness changed")
    try:
        final_result = supervision._adaptive_decision_posture(
            final_policy,
            decision_packet,
            active_candidate_fingerprints=supervision.adaptive_active_candidate_fingerprints(
                final_events
            ),
        )
    except Exception as error:
        raise TargetClassProtocolError(
            "adaptive decision currentness changed"
        ) from error
    if review_record_id is not None:
        final_result = {
            **final_result,
            "independent_review_record": review_record_id,
        }
        final_result["result_sha256"] = digest(
            {
                key: value
                for key, value in final_result.items()
                if key != "result_sha256"
            }
        )
    if final_result != result:
        raise TargetClassProtocolError("adaptive decision currentness changed")
    if target_class == "software-factory" and disposition != "continue-unchanged":
        if _live_skill_identity(DEFAULT_SKILLS_ROOT) != live_skill_identity:
            raise TargetClassProtocolError("software-factory skill sources changed")
    if capability_context is not None:
        try:
            final_capability, final_capability_root = (
                supervision.load_capability_reconciliation(
                    context["path"],
                    target_thread=context["target_thread_id"],
                    mission_root=context["mission_root"],
                    state_fingerprint=context["state_fingerprint"],
                    current_revision=context["current_revision"],
                    policy=final_policy,
                )
            )
        except Exception as error:
            raise TargetClassProtocolError(
                "current behavior changed during reconciliation"
            ) from error
        if final_capability != capability or final_capability_root != capability_root:
            raise TargetClassProtocolError(
                "current behavior changed during reconciliation"
            )
    application_action: Optional[str] = None
    if disposition == "correct-inline":
        application_action = "normal-owner-inline-correction"
    elif disposition == "compare-candidate":
        application_action = "retain-comparison-with-incumbent-authoritative"
    elif disposition == "amend-structure":
        application_action = "normal-authoring-owner-application"
    elif disposition == "cutover-candidate":
        if target_class == "target-repository":
            application_action = "normal-target-owner-cutover"
        elif evolution_disposition == "promote":
            application_action = (
                "retain-adoption-eligible-evidence-with-normal-owner"
            )
        elif evolution_disposition == "revise":
            application_action = "normal-owner-factory-candidate-revision"
        elif evolution_disposition == "reject":
            application_action = "normal-owner-factory-candidate-retirement"
        else:
            application_action = "normal-owner-factory-candidate-advisory"
    application_handoff = (
        {
            "schema_version": 1,
            "kind": "software-factory-target-class-application-handoff",
            "target_class": target_class,
            "target_repository_root": decision["target_repository_root"],
            "target_revision": decision["target_revision"],
            "target_revision_root": decision["target_revision_root"],
            "disposition": disposition,
            "decision_record_id": decision_event["record_id"],
            "decision_record_sha256": decision_event["record_sha256"],
            "decision_fingerprint": result["decision_fingerprint"],
            "decision_currentness_root": result["decision_currentness_root"],
            "candidate_evidence_root": result["candidate_evidence_root"],
            "program_revision_root": (
                program_packet.get("packet_root") if program_packet else None
            ),
            "program_revision_review_root": (
                program_review.get("review_root") if program_review else None
            ),
            "factory_skill_sources_root": live_sources_root,
            "factory_evolution_id": evolution_id,
            "factory_evolution_root": evolution_root,
            "factory_evolution_review_root": evolution_review_root,
            "factory_evaluation_root": evaluation_root,
            "factory_experiment_root": experiment_root,
            "factory_evolution_disposition": evolution_disposition,
            "factory_role_map": {
                "proposer_id": proposer,
                "implementation_owner_id": implementer,
                "reviewer_id": reviewer,
                "evaluator_id": evaluator,
            },
            "capability_reconciliation_root": capability_root,
            "capability_completion_record_id": capability_completion_record_id,
            "capability_completion_record_sha256": (
                capability_completion_record_sha256
            ),
            "factory_alignment_findings_root": digest(factory_findings),
            "target_product_findings_root": digest(product_findings),
            "application_action": application_action,
            "application_owner_id": decision["implementation_owner_id"],
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
        "target_revision": decision["target_revision"],
        "target_revision_root": decision["target_revision_root"],
        "disposition": disposition,
        "decision_record_id": decision_event["record_id"],
        "decision_record_sha256": decision_event["record_sha256"],
        "decision_fingerprint": result["decision_fingerprint"],
        "decision_currentness_root": result["decision_currentness_root"],
        "candidate_evidence_root": candidate.get("evidence_root") if candidate else None,
        "program_revision_root": program_packet.get("packet_root") if program_packet else None,
        "program_revision_review_root": (
            program_review.get("review_root") if program_review else None
        ),
        "application_handoff_root": (
            digest(application_handoff) if application_handoff else None
        ),
        "application_handoff": application_handoff,
        "factory_skill_sources_root": live_sources_root,
        "factory_evolution_id": evolution_id,
        "factory_evolution_root": evolution_root,
        "factory_evolution_review_root": evolution_review_root,
        "factory_evaluation_root": evaluation_root,
        "factory_experiment_root": experiment_root,
        "factory_evolution_disposition": evolution_disposition,
        "factory_alignment_findings_root": digest(factory_findings),
        "target_product_findings_root": digest(product_findings),
        "capability_reconciliation_root": capability_root,
        "capability_completion_record_id": capability_completion_record_id,
        "capability_completion_record_sha256": (
            capability_completion_record_sha256
        ),
        "application_authorized": False,
        "candidate_authoritative": False,
        "promotion_authorized": False,
        "adoption_eligible": adoption_eligible,
        "improvement_established": improvement_established,
        "next_owner": (
            decision["implementation_owner_id"]
            if application_action is not None
            else None
        ),
        "resume_action": (
            "continue-current-block"
            if disposition == "continue-unchanged"
            else application_action
        ),
    }
    return {**material, "protocol_root": digest(material)}
