#!/usr/bin/env python3
"""Build and verify one bounded active-program structural revision packet."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import argparse
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


MAX_TRACKER_BYTES = 2 * 1024 * 1024
MAX_LIST_ITEMS = 64
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,127}$")
BLOCK_HEADING = re.compile(r"^## Block (\d+)\b", re.MULTILINE)
TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")
ALLOWED_TARGET_CLASSES = {"target-repository", "software-factory"}
ALLOWED_AUTHORITY_MODES = {
    "fixed",
    "recommend",
    "reviewed-autonomous",
    "full-autonomous",
}
PACKET_FIELDS = {
    "schema_version",
    "kind",
    "revision_id",
    "target_thread_id",
    "target_class",
    "mission_root",
    "policy_sha256",
    "decision_record_id",
    "decision_record_sha256",
    "decision_fingerprint",
    "decision_currentness_root",
    "application_precondition_root",
    "candidate_evidence_root",
    "decision_target_state_root",
    "current_target_state_root",
    "repository_root",
    "target_revision",
    "target_revision_root",
    "previous_tracker_path",
    "previous_tracker_sha256",
    "previous_tracker_structure_sha256",
    "previous_blocks",
    "proposed_tracker_path",
    "proposed_tracker_sha256",
    "proposed_tracker_structure_sha256",
    "proposed_blocks",
    "block_number_map",
    "accepted_history_blocks",
    "accepted_history_root",
    "affected_previous_blocks",
    "affected_proposed_blocks",
    "safe_frontier_blocks",
    "resume_block",
    "learned_fact_refs",
    "capability_effects",
    "selected_path",
    "rejected_paths",
    "proposed_mutations",
    "preserved_work_refs",
    "invalidated_proof_refs",
    "authority_mode",
    "author_id",
    "reviewer_id",
    "stop",
    "full_verifier_result_root",
    "packet_root",
}


class ProgramRevisionError(ValueError):
    """Raised when structural revision evidence is incomplete or stale."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ProgramRevisionError(f"Duplicate JSON key is not allowed: {key}")
        value[key] = item
    return value


def validate_exact_json(value: Any) -> None:
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        if unicodedata.normalize("NFC", value) != value:
            raise ProgramRevisionError("Canonical JSON contains a non-NFC string")
        return
    if isinstance(value, list):
        for item in value:
            validate_exact_json(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str or unicodedata.normalize("NFC", key) != key:
                raise ProgramRevisionError("Canonical JSON contains a non-NFC key")
            validate_exact_json(item)
        return
    raise ProgramRevisionError(
        "Canonical JSON permits only null, booleans, integers, strings, arrays, and objects"
    )


def exact_sha256(value: Any, *, label: str) -> str:
    if type(value) is not str or SHA256.fullmatch(value) is None:
        raise ProgramRevisionError(f"{label} must be an exact SHA-256")
    return value


def safe_id(value: Any, *, label: str) -> str:
    if type(value) is not str or SAFE_ID.fullmatch(value) is None:
        raise ProgramRevisionError(f"{label} is invalid")
    return value


def exact_string_list(value: Any, *, label: str, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or len(value) > MAX_LIST_ITEMS
        or any(type(item) is not str or not item or len(item) > 240 for item in value)
        or len(set(value)) != len(value)
    ):
        raise ProgramRevisionError(f"{label} is invalid")
    return list(value)


def read_regular_file(path_value: str | Path) -> tuple[Path, bytes]:
    supplied = Path(path_value).expanduser()
    descriptor = -1
    try:
        resolved = supplied.resolve(strict=True)
        if supplied.is_symlink():
            raise ProgramRevisionError("Tracker must be one explicit non-symlink file")
        descriptor = os.open(
            resolved,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_TRACKER_BYTES:
            raise ProgramRevisionError("Tracker file type or byte bound is invalid")
        raw = os.read(descriptor, MAX_TRACKER_BYTES + 1)
        after = os.fstat(descriptor)
        if (
            len(raw) > MAX_TRACKER_BYTES
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise ProgramRevisionError("Tracker changed while reading")
    except OSError as exc:
        raise ProgramRevisionError("Tracker cannot be read safely") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return resolved, raw


def _normalized_block_lines(
    section: str, *, include_completion: bool, normalize_number: bool
) -> list[str]:
    lines = section.splitlines()
    normalized: list[str] = []
    in_completion = False
    for index, line in enumerate(lines):
        if index == 0 and normalize_number:
            line = re.sub(r"^(## Block) \d+", r"\1 <number>", line)
        if re.match(r"^Status:\s*", line):
            normalized.append("Status: <runtime-state>")
            continue
        if line.strip() == "### Completion evidence":
            in_completion = True
            normalized.append(line)
            continue
        if in_completion and re.match(r"^###\s+", line):
            in_completion = False
        if include_completion or not in_completion:
            normalized.append(line.rstrip())
    return normalized


def _load_full_verifier() -> Any:
    path = Path(__file__).with_name("verify_tracker.py")
    spec = importlib.util.spec_from_file_location("program_revision_verify_tracker", path)
    if spec is None or spec.loader is None:
        raise ProgramRevisionError("Full tracker verifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def tracker_snapshot(path_value: str | Path, *, require_full: bool = True) -> dict[str, Any]:
    path, raw = read_regular_file(path_value)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProgramRevisionError("Tracker must be UTF-8") from exc
    headings = list(BLOCK_HEADING.finditer(text))
    numbers = [int(item.group(1)) for item in headings]
    if not numbers or len(numbers) != len(set(numbers)):
        raise ProgramRevisionError("Tracker Block headings are absent or repeated")
    rows: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        match = TABLE_ROW.match(line)
        if match is None:
            continue
        number = int(match.group(1))
        cells = [item.strip().strip("`") for item in line.strip().strip("|").split("|")]
        if number not in numbers or len(cells) < 4:
            continue
        if number in rows:
            raise ProgramRevisionError("Tracker repeats a status row")
        rows[number] = {
            "scope": cells[1],
            "dependencies": [int(item) for item in re.findall(r"\d+", cells[2])],
            "status": cells[3],
        }
    if set(rows) != set(numbers):
        raise ProgramRevisionError("Tracker status table is incomplete")
    contracts: list[dict[str, Any]] = []
    for index, heading in enumerate(headings):
        number = int(heading.group(1))
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.start() : end]
        contract_sha256 = hashlib.sha256(
            "\n".join(
                _normalized_block_lines(
                    section, include_completion=False, normalize_number=False
                )
            )
            .strip()
            .encode("utf-8")
        ).hexdigest()
        mapped_contract_sha256 = hashlib.sha256(
            "\n".join(
                _normalized_block_lines(
                    section, include_completion=False, normalize_number=True
                )
            )
            .strip()
            .encode("utf-8")
        ).hexdigest()
        history_sha256 = hashlib.sha256(
            "\n".join(
                _normalized_block_lines(
                    section, include_completion=True, normalize_number=True
                )
            )
            .strip()
            .encode("utf-8")
        ).hexdigest()
        rows[number]["contract_sha256"] = contract_sha256
        rows[number]["mapped_contract_sha256"] = mapped_contract_sha256
        rows[number]["history_sha256"] = history_sha256
        contracts.append(
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
            "blocks": contracts,
        }
    )
    verifier_result: dict[str, Any] | None = None
    if require_full:
        verifier = _load_full_verifier()
        verifier_result = verifier.verify(path, "full")
        if verifier_result.get("errors"):
            raise ProgramRevisionError("Proposed tracker fails the full structural verifier")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "structure_sha256": structure_sha256,
        "blocks": rows,
        "verifier_result_root": digest(verifier_result) if verifier_result else None,
    }


def normalize_block_map(
    value: Any, *, old_blocks: set[int], new_blocks: set[int]
) -> dict[str, list[int]]:
    if not isinstance(value, Mapping) or set(value) != {str(item) for item in old_blocks}:
        raise ProgramRevisionError("Block-number map is incomplete")
    normalized: dict[str, list[int]] = {}
    for old in sorted(old_blocks):
        targets = value[str(old)]
        if (
            not isinstance(targets, list)
            or len(targets) > MAX_LIST_ITEMS
            or any(type(item) is not int for item in targets)
            or targets != sorted(set(targets))
            or not set(targets).issubset(new_blocks)
        ):
            raise ProgramRevisionError("Block-number map target set is invalid")
        normalized[str(old)] = list(targets)
    return normalized


def dependency_closure(blocks: Mapping[int, Mapping[str, Any]], seeds: set[int]) -> set[int]:
    closure = set(seeds)
    changed = True
    while changed:
        changed = False
        for number, block in blocks.items():
            if number not in closure and set(block["dependencies"]) & closure:
                closure.add(number)
                changed = True
    return closure


def _accepted_history(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "block": number,
            "history_sha256": block["history_sha256"],
            "contract_sha256": block["contract_sha256"],
        }
        for number, block in sorted(snapshot["blocks"].items())
        if block["status"] == "completed"
    ]


def build_revision_packet(
    *,
    previous_tracker: str | Path,
    proposed_tracker: str | Path,
    target_tracker_path: str | Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    required_metadata = {
        "revision_id",
        "target_thread_id",
        "target_class",
        "mission_root",
        "policy_sha256",
        "decision_record_id",
        "decision_record_sha256",
        "decision_fingerprint",
        "decision_currentness_root",
        "application_precondition_root",
        "candidate_evidence_root",
        "decision_target_state_root",
        "current_target_state_root",
        "repository_root",
        "target_revision",
        "target_revision_root",
        "author_id",
        "reviewer_id",
        "learned_fact_refs",
        "capability_effects",
        "selected_path",
        "rejected_paths",
        "proposed_mutations",
        "preserved_work_refs",
        "invalidated_proof_refs",
        "authority_mode",
        "stop",
        "block_number_map",
    }
    if set(metadata) != required_metadata:
        raise ProgramRevisionError("Program revision metadata shape differs")
    previous = tracker_snapshot(previous_tracker, require_full=True)
    proposed = tracker_snapshot(proposed_tracker, require_full=True)
    target_path = Path(target_tracker_path).expanduser().resolve(strict=False)
    if previous["path"] != str(target_path):
        raise ProgramRevisionError("Previous tracker is not the canonical target path")
    if previous["structure_sha256"] == proposed["structure_sha256"]:
        raise ProgramRevisionError("Local/status-only change is not a structural revision")
    old_blocks = set(previous["blocks"])
    new_blocks = set(proposed["blocks"])
    block_map = normalize_block_map(
        metadata["block_number_map"], old_blocks=old_blocks, new_blocks=new_blocks
    )
    changed_old: set[int] = set()
    changed_new: set[int] = set()
    for old, old_block in previous["blocks"].items():
        targets = block_map[str(old)]
        if len(targets) != 1:
            changed_old.add(old)
            changed_new.update(targets)
            continue
        new = targets[0]
        new_block = proposed["blocks"][new]
        mapped_dependencies = sorted(
            {
                mapped
                for dependency in old_block["dependencies"]
                for mapped in block_map[str(dependency)]
            }
        )
        if (
            old_block["scope"] != new_block["scope"]
            or old_block["mapped_contract_sha256"]
            != new_block["mapped_contract_sha256"]
            or mapped_dependencies != new_block["dependencies"]
        ):
            changed_old.add(old)
            changed_new.add(new)
    represented_once = {
        targets[0]
        for targets in block_map.values()
        if len(targets) == 1
    }
    changed_new.update(new_blocks - represented_once)
    affected_new = dependency_closure(proposed["blocks"], changed_new)
    affected_old = {
        old
        for old, targets in ((item, block_map[str(item)]) for item in old_blocks)
        if not targets or set(targets) & affected_new
    }
    accepted_history = _accepted_history(previous)
    for item in accepted_history:
        old = int(item["block"])
        targets = block_map[str(old)]
        if len(targets) != 1:
            raise ProgramRevisionError("Accepted Block cannot be removed, split, or merged")
        old_block = previous["blocks"][old]
        new_block = proposed["blocks"][targets[0]]
        mapped_dependencies = sorted(
            {
                mapped
                for dependency in old_block["dependencies"]
                for mapped in block_map[str(dependency)]
            }
        )
        if (
            new_block["status"] != "completed"
            or new_block["scope"] != old_block["scope"]
            or new_block["history_sha256"] != item["history_sha256"]
            or new_block["mapped_contract_sha256"]
            != old_block["mapped_contract_sha256"]
            or new_block["dependencies"] != mapped_dependencies
        ):
            raise ProgramRevisionError("Accepted Block history was rewritten")
    completed_new = {
        number
        for number, block in proposed["blocks"].items()
        if block["status"] == "completed"
    }
    safe_frontier = sorted(
        number
        for number, block in proposed["blocks"].items()
        if number not in affected_new
        and number not in completed_new
        and set(block["dependencies"]).issubset(completed_new)
    )
    resume_candidates = sorted(
        number
        for number in affected_new
        if number not in completed_new
        and set(proposed["blocks"][number]["dependencies"]).issubset(completed_new)
    )
    if not resume_candidates:
        raise ProgramRevisionError("Structural revision has no dependency-safe resume Block")
    capability_effects = metadata["capability_effects"]
    if not isinstance(capability_effects, Mapping) or set(capability_effects) != {
        "gains",
        "protected",
        "losses",
    }:
        raise ProgramRevisionError("Capability effects shape differs")
    normalized_effects = {
        key: exact_string_list(
            capability_effects[key], label=f"capability {key}", allow_empty=key == "losses"
        )
        for key in ("gains", "protected", "losses")
    }
    packet: dict[str, Any] = {
        "schema_version": 1,
        "kind": "implementation-program-revision-packet",
        "revision_id": safe_id(metadata["revision_id"], label="program revision ID"),
        "target_thread_id": safe_id(metadata["target_thread_id"], label="target thread ID"),
        "target_class": metadata["target_class"],
        "mission_root": exact_sha256(metadata["mission_root"], label="mission root"),
        "policy_sha256": exact_sha256(metadata["policy_sha256"], label="policy SHA-256"),
        "decision_record_id": safe_id(metadata["decision_record_id"], label="decision record"),
        "decision_record_sha256": exact_sha256(metadata["decision_record_sha256"], label="decision record SHA-256"),
        "decision_fingerprint": exact_sha256(metadata["decision_fingerprint"], label="decision fingerprint"),
        "decision_currentness_root": exact_sha256(metadata["decision_currentness_root"], label="decision currentness root"),
        "application_precondition_root": exact_sha256(metadata["application_precondition_root"], label="application precondition root"),
        "candidate_evidence_root": (
            exact_sha256(metadata["candidate_evidence_root"], label="candidate evidence root")
            if metadata["candidate_evidence_root"] is not None
            else None
        ),
        "decision_target_state_root": exact_sha256(metadata["decision_target_state_root"], label="decision target state root"),
        "current_target_state_root": exact_sha256(metadata["current_target_state_root"], label="current target state root"),
        "repository_root": str(Path(metadata["repository_root"]).expanduser().resolve(strict=True)),
        "target_revision": safe_id(metadata["target_revision"], label="target revision"),
        "target_revision_root": exact_sha256(metadata["target_revision_root"], label="target revision root"),
        "previous_tracker_path": str(target_path),
        "previous_tracker_sha256": previous["sha256"],
        "previous_tracker_structure_sha256": previous["structure_sha256"],
        "previous_blocks": sorted(old_blocks),
        "proposed_tracker_path": str(target_path),
        "proposed_tracker_sha256": proposed["sha256"],
        "proposed_tracker_structure_sha256": proposed["structure_sha256"],
        "proposed_blocks": sorted(new_blocks),
        "block_number_map": block_map,
        "accepted_history_blocks": [item["block"] for item in accepted_history],
        "accepted_history_root": digest(accepted_history),
        "affected_previous_blocks": sorted(affected_old),
        "affected_proposed_blocks": sorted(affected_new),
        "safe_frontier_blocks": safe_frontier,
        "resume_block": resume_candidates[0],
        "learned_fact_refs": exact_string_list(metadata["learned_fact_refs"], label="learned-fact references"),
        "capability_effects": normalized_effects,
        "selected_path": safe_id(metadata["selected_path"], label="selected path"),
        "rejected_paths": exact_string_list(metadata["rejected_paths"], label="rejected paths"),
        "proposed_mutations": exact_string_list(metadata["proposed_mutations"], label="proposed mutations"),
        "preserved_work_refs": exact_string_list(metadata["preserved_work_refs"], label="preserved-work references"),
        "invalidated_proof_refs": exact_string_list(metadata["invalidated_proof_refs"], label="invalidated-proof references"),
        "authority_mode": metadata["authority_mode"],
        "author_id": safe_id(metadata["author_id"], label="author ID"),
        "reviewer_id": safe_id(metadata["reviewer_id"], label="reviewer ID"),
        "stop": safe_id(metadata["stop"], label="revision Stop"),
        "full_verifier_result_root": proposed["verifier_result_root"],
    }
    if packet["target_class"] not in ALLOWED_TARGET_CLASSES:
        raise ProgramRevisionError("Program revision target class is invalid")
    if packet["authority_mode"] not in ALLOWED_AUTHORITY_MODES:
        raise ProgramRevisionError("Program revision authority mode is invalid")
    if packet["author_id"] == packet["reviewer_id"]:
        raise ProgramRevisionError("Program revision author and reviewer must differ")
    packet["packet_root"] = digest(packet)
    return packet


def validate_revision_packet(
    value: Any,
    *,
    previous_tracker: str | Path,
    proposed_tracker: str | Path,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProgramRevisionError("Program revision packet must be an object")
    metadata_fields = {
        "revision_id",
        "target_thread_id",
        "target_class",
        "mission_root",
        "policy_sha256",
        "decision_record_id",
        "decision_record_sha256",
        "decision_fingerprint",
        "decision_currentness_root",
        "application_precondition_root",
        "candidate_evidence_root",
        "decision_target_state_root",
        "current_target_state_root",
        "repository_root",
        "target_revision",
        "target_revision_root",
        "author_id",
        "reviewer_id",
        "learned_fact_refs",
        "capability_effects",
        "selected_path",
        "rejected_paths",
        "proposed_mutations",
        "preserved_work_refs",
        "invalidated_proof_refs",
        "authority_mode",
        "stop",
        "block_number_map",
    }
    metadata = {key: value.get(key) for key in metadata_fields}
    rebuilt = build_revision_packet(
        previous_tracker=previous_tracker,
        proposed_tracker=proposed_tracker,
        target_tracker_path=value.get("previous_tracker_path", ""),
        metadata=metadata,
    )
    if dict(value) != rebuilt:
        raise ProgramRevisionError("Program revision packet differs from current sources")
    return rebuilt


def validate_stored_packet(value: Any) -> dict[str, Any]:
    """Validate immutable packet shape after predecessor bytes are historical."""
    if not isinstance(value, Mapping) or set(value) != PACKET_FIELDS:
        raise ProgramRevisionError("Stored program revision packet shape differs")
    packet = dict(value)
    if type(packet.get("schema_version")) is not int or packet["schema_version"] != 1:
        raise ProgramRevisionError("Stored program revision packet version differs")
    if packet.get("kind") != "implementation-program-revision-packet":
        raise ProgramRevisionError("Stored program revision packet kind differs")
    if packet["packet_root"] != digest(
        {key: item for key, item in packet.items() if key != "packet_root"}
    ):
        raise ProgramRevisionError("Stored program revision packet root differs")
    for field in (
        "mission_root",
        "policy_sha256",
        "decision_record_sha256",
        "decision_fingerprint",
        "decision_currentness_root",
        "application_precondition_root",
        "decision_target_state_root",
        "current_target_state_root",
        "target_revision_root",
        "previous_tracker_sha256",
        "previous_tracker_structure_sha256",
        "proposed_tracker_sha256",
        "proposed_tracker_structure_sha256",
        "accepted_history_root",
        "full_verifier_result_root",
        "packet_root",
    ):
        exact_sha256(packet.get(field), label=field.replace("_", " "))
    if packet.get("candidate_evidence_root") is not None:
        exact_sha256(
            packet.get("candidate_evidence_root"), label="candidate evidence root"
        )
    for field in (
        "revision_id",
        "target_thread_id",
        "decision_record_id",
        "target_revision",
        "selected_path",
        "author_id",
        "reviewer_id",
        "stop",
    ):
        safe_id(packet.get(field), label=field.replace("_", " "))
    if packet["author_id"] == packet["reviewer_id"]:
        raise ProgramRevisionError("Stored program revision roles are not distinct")
    if packet.get("target_class") not in ALLOWED_TARGET_CLASSES:
        raise ProgramRevisionError("Stored program revision target class differs")
    if packet.get("authority_mode") not in ALLOWED_AUTHORITY_MODES:
        raise ProgramRevisionError("Stored program revision authority mode differs")
    for field in (
        "previous_blocks",
        "proposed_blocks",
        "accepted_history_blocks",
        "affected_previous_blocks",
        "affected_proposed_blocks",
        "safe_frontier_blocks",
    ):
        items = packet.get(field)
        if (
            not isinstance(items, list)
            or any(type(item) is not int for item in items)
            or items != sorted(set(items))
        ):
            raise ProgramRevisionError(f"Stored program revision {field} differs")
    if not packet["previous_blocks"] or not packet["proposed_blocks"]:
        raise ProgramRevisionError("Stored program revision Block sets are empty")
    block_map = normalize_block_map(
        packet.get("block_number_map"),
        old_blocks=set(packet["previous_blocks"]),
        new_blocks=set(packet["proposed_blocks"]),
    )
    if block_map != packet["block_number_map"]:
        raise ProgramRevisionError("Stored program revision map differs")
    if (
        not set(packet["accepted_history_blocks"]).issubset(packet["previous_blocks"])
        or not set(packet["affected_previous_blocks"]).issubset(packet["previous_blocks"])
        or not set(packet["affected_proposed_blocks"]).issubset(packet["proposed_blocks"])
        or not set(packet["safe_frontier_blocks"]).issubset(packet["proposed_blocks"])
        or type(packet.get("resume_block")) is not int
        or packet["resume_block"] not in packet["affected_proposed_blocks"]
    ):
        raise ProgramRevisionError("Stored program revision closure differs")
    return packet


def review_root_material(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in value if key not in {"review_root", "signature_base64"}}


def validate_review_shape(
    value: Any,
    *,
    packet: Mapping[str, Any],
    authority_key_sha256: str,
) -> dict[str, Any]:
    expected = {
        "schema_version",
        "kind",
        "record_id",
        "revision_id",
        "packet_root",
        "previous_tracker_sha256",
        "proposed_tracker_sha256",
        "proposed_tracker_structure_sha256",
        "accepted_history_root",
        "block_map_root",
        "affected_closure_root",
        "resume_block",
        "author_id",
        "reviewer_id",
        "disposition",
        "finding_refs",
        "evidence_root",
        "authority_key_sha256",
        "review_root",
        "signature_base64",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ProgramRevisionError("Program revision review shape differs")
    if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ProgramRevisionError("Program revision review version differs")
    if value.get("kind") != "software-factory-program-revision-independent-review":
        raise ProgramRevisionError("Program revision review kind differs")
    exact = {
        "revision_id": packet["revision_id"],
        "packet_root": packet["packet_root"],
        "previous_tracker_sha256": packet["previous_tracker_sha256"],
        "proposed_tracker_sha256": packet["proposed_tracker_sha256"],
        "proposed_tracker_structure_sha256": packet["proposed_tracker_structure_sha256"],
        "accepted_history_root": packet["accepted_history_root"],
        "block_map_root": digest(packet["block_number_map"]),
        "affected_closure_root": digest(packet["affected_proposed_blocks"]),
        "resume_block": packet["resume_block"],
        "author_id": packet["author_id"],
        "reviewer_id": packet["reviewer_id"],
        "authority_key_sha256": authority_key_sha256,
    }
    if any(value.get(key) != item for key, item in exact.items()):
        raise ProgramRevisionError("Program revision review does not bind the exact packet")
    safe_id(value.get("record_id"), label="program revision review record")
    if value.get("disposition") not in {"accepted", "revise", "rejected"}:
        raise ProgramRevisionError("Program revision review disposition is invalid")
    exact_string_list(value.get("finding_refs"), label="program revision findings", allow_empty=True)
    exact_sha256(value.get("evidence_root"), label="program revision review evidence root")
    exact_sha256(value.get("review_root"), label="program revision review root")
    if type(value.get("signature_base64")) is not str or not value["signature_base64"]:
        raise ProgramRevisionError("Program revision review signature is absent")
    if value["review_root"] != digest(review_root_material(value)):
        raise ProgramRevisionError("Program revision review root differs")
    return dict(value)


def load_json(path_value: str | Path) -> dict[str, Any]:
    path, raw = read_regular_file(path_value)
    if len(raw) > 256 * 1024:
        raise ProgramRevisionError(f"JSON input is too large: {path}")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProgramRevisionError(f"JSON input is invalid: {path}") from exc
    validate_exact_json(value)
    if not isinstance(value, dict) or raw != canonical(value) + b"\n":
        raise ProgramRevisionError(f"JSON input is not exact canonical JSON: {path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--previous-tracker", required=True)
    build.add_argument("--proposed-tracker", required=True)
    build.add_argument("--target-tracker-path", required=True)
    build.add_argument("--metadata-json", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--previous-tracker", required=True)
    verify.add_argument("--proposed-tracker", required=True)
    verify.add_argument("--packet-json", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "build":
            packet = build_revision_packet(
                previous_tracker=args.previous_tracker,
                proposed_tracker=args.proposed_tracker,
                target_tracker_path=args.target_tracker_path,
                metadata=load_json(args.metadata_json),
            )
        else:
            packet = validate_revision_packet(
                load_json(args.packet_json),
                previous_tracker=args.previous_tracker,
                proposed_tracker=args.proposed_tracker,
            )
    except ProgramRevisionError as exc:
        parser.error(str(exc))
    print(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
