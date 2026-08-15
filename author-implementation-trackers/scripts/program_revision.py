#!/usr/bin/env python3
"""Build and verify one bounded active-program structural revision packet."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
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
PROGRAM_CONTROL_HEADING = re.compile(
    r"^## Active-program revision control\s*$", re.MULTILINE
)
PROGRAM_CONTROL_FIELD = re.compile(
    r"^- (?P<label>Terminal Block|Required order|Prose-reference Blocks|"
    r"Source-map Blocks|Verification-matrix Blocks|Handoff Block): "
    r"`(?P<value>[^`]+)`$"
)
PROGRAM_CONTROL_FIELD_ORDER = (
    "Terminal Block",
    "Required order",
    "Prose-reference Blocks",
    "Source-map Blocks",
    "Verification-matrix Blocks",
    "Handoff Block",
)
PROGRAM_HISTORY_HEADING = "### Program revision history"
PROGRAM_HISTORY_HEADER = (
    "| Revision ID | Predecessor tracker SHA-256 | Current structure SHA-256 "
    "| Block map SHA-256 | Affected Blocks | Resume Block |"
)
PROGRAM_HISTORY_SEPARATOR = "|---|---|---|---|---|---:|"
PROGRAM_HISTORY_ROW = re.compile(
    r"^\| `(?P<revision>[A-Za-z0-9][A-Za-z0-9._:-]{3,127})` "
    r"\| `(?P<previous>[0-9a-f]{64})` \| `(?P<current>[0-9a-f]{64})` "
    r"\| `(?P<map>[0-9a-f]{64})` \| `(?P<affected>\d+(?:,\d+)*)` "
    r"\| `(?P<resume>\d+)` \|$"
)
PROGRAM_INDEX_ROW = re.compile(
    r"^\|\s*(?P<block>\d+)\s*\|\s*(?P<value>[^|]+)\|$"
)
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
    "predecessor_revision_id",
    "predecessor_review_root",
    "resolved_finding_refs",
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
    "application_owner_id",
    "reviewer_id",
    "authoring_profile_revision",
    "authoring_profile_root",
    "authoring_profile_source_revision",
    "authoring_profile_source_root",
    "authoring_profile_binding_root",
    "mechanical_watcher_id",
    "mechanical_route_record_id",
    "semantic_review_record_id",
    "semantic_review_root",
    "adjudicator_id",
    "adjudication_root",
    "fix_executor_id",
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


def exact_git_revision(value: Any, *, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ProgramRevisionError(f"{label} must be an exact Git commit")
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


def exact_block_list_text(value: str, *, label: str) -> list[int]:
    if re.fullmatch(r"\d+(?:,\d+)*", value) is None:
        raise ProgramRevisionError(f"{label} is invalid")
    items = [int(item) for item in value.split(",")]
    if items != sorted(set(items)) or len(items) > MAX_LIST_ITEMS:
        raise ProgramRevisionError(f"{label} is invalid")
    return items


def parse_program_revision_control(text: str) -> dict[str, Any] | None:
    headings = list(PROGRAM_CONTROL_HEADING.finditer(text))
    if not headings:
        return None
    if len(headings) != 1:
        raise ProgramRevisionError("Tracker repeats active-program revision control")
    start = headings[0].end()
    following = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + following.start() if following is not None else len(text)
    lines = [line for line in text[start:end].strip().splitlines() if line]
    if (
        len(lines) < len(PROGRAM_CONTROL_FIELD_ORDER) + 4
        or lines[len(PROGRAM_CONTROL_FIELD_ORDER)] != PROGRAM_HISTORY_HEADING
        or lines[len(PROGRAM_CONTROL_FIELD_ORDER) + 1] != PROGRAM_HISTORY_HEADER
        or lines[len(PROGRAM_CONTROL_FIELD_ORDER) + 2] != PROGRAM_HISTORY_SEPARATOR
    ):
        raise ProgramRevisionError(
            "Active-program revision control layout is not canonical"
        )
    fields: dict[str, str] = {}
    history: list[dict[str, Any]] = []
    for position, label in enumerate(PROGRAM_CONTROL_FIELD_ORDER):
        line = lines[position]
        field = PROGRAM_CONTROL_FIELD.fullmatch(line)
        if field is None or field.group("label") != label:
            raise ProgramRevisionError(
                "Active-program revision control field order differs"
            )
        fields[label] = field.group("value")
    for line in lines[len(PROGRAM_CONTROL_FIELD_ORDER) + 3 :]:
        row = PROGRAM_HISTORY_ROW.fullmatch(line)
        if row is None:
            raise ProgramRevisionError(
                "Program revision history contains a noncanonical row"
            )
        history.append(
            {
                "revision_id": row.group("revision"),
                "previous_tracker_sha256": row.group("previous"),
                "current_tracker_structure_sha256": row.group("current"),
                "block_map_root": row.group("map"),
                "affected_blocks": exact_block_list_text(
                    row.group("affected"), label="program history affected Blocks"
                ),
                "resume_block": int(row.group("resume")),
            }
        )
    if set(fields) != set(PROGRAM_CONTROL_FIELD_ORDER) or not history:
        raise ProgramRevisionError("Active-program revision control is incomplete")
    for label in ("Terminal Block", "Handoff Block"):
        if re.fullmatch(r"\d+", fields[label]) is None:
            raise ProgramRevisionError(f"Active-program {label} is invalid")
    revision_ids = [item["revision_id"] for item in history]
    if len(revision_ids) != len(set(revision_ids)):
        raise ProgramRevisionError("Program revision history repeats a revision ID")
    return {
        "terminal_block": int(fields["Terminal Block"]),
        "required_order": exact_block_list_text(
            fields["Required order"], label="active-program required order"
        ),
        "prose_reference_blocks": exact_block_list_text(
            fields["Prose-reference Blocks"],
            label="active-program prose references",
        ),
        "source_map_blocks": exact_block_list_text(
            fields["Source-map Blocks"], label="active-program source map"
        ),
        "verification_matrix_blocks": exact_block_list_text(
            fields["Verification-matrix Blocks"],
            label="active-program verification matrix",
        ),
        "handoff_block": int(fields["Handoff Block"]),
        "history": history,
    }


def _program_index(text: str, heading: str) -> list[dict[str, Any]]:
    headings = list(re.finditer(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE))
    if len(headings) != 1:
        raise ProgramRevisionError(
            f"Active-program tracker requires one {heading} section"
        )
    start = headings[0].end()
    following = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + following.start() if following is not None else len(text)
    rows: list[dict[str, Any]] = []
    for line in text[start:end].splitlines():
        match = PROGRAM_INDEX_ROW.fullmatch(line)
        if match is not None:
            rows.append(
                {
                    "block": int(match.group("block")),
                    "basis": match.group("value").strip(),
                }
            )
    if not rows or [item["block"] for item in rows] != list(
        dict.fromkeys(item["block"] for item in rows)
    ):
        raise ProgramRevisionError(f"Active-program {heading} is malformed")
    return rows


def _tracker_wide_program_claims(text: str) -> list[str]:
    current = text
    for heading in (
        "Active-program revision control",
        "Program source map",
        "Program verification matrix",
    ):
        current = re.sub(
            rf"^## {re.escape(heading)}\s*$.*?(?=^##\s+|\Z)",
            "",
            current,
            flags=re.MULTILINE | re.DOTALL,
        )
    claims: list[str] = []
    in_block = False
    for line in current.splitlines():
        if BLOCK_HEADING.fullmatch(line) is not None:
            in_block = True
        elif re.fullmatch(r"##\s+.+", line) is not None:
            in_block = False
        if (
            not in_block
            and re.search(r"\bBlocks?\s+\d+", line, re.I)
            and re.search(
                r"\b(?:range|order|handoff|resume|terminal)\b", line, re.I
            )
        ):
            claims.append(line.strip())
    return claims


def active_program_surface_projection(text: str) -> dict[str, Any] | None:
    control = parse_program_revision_control(text)
    if control is None:
        return None
    return {
        "schema_version": 1,
        "kind": "active-program-structural-surface",
        "terminal_block": control["terminal_block"],
        "required_order": control["required_order"],
        "prose_reference_blocks": control["prose_reference_blocks"],
        "source_map_blocks": control["source_map_blocks"],
        "verification_matrix_blocks": control["verification_matrix_blocks"],
        "handoff_block": control["handoff_block"],
        "source_map": _program_index(text, "Program source map"),
        "verification_matrix": _program_index(text, "Program verification matrix"),
        "tracker_wide_claims": _tracker_wide_program_claims(text),
    }


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


def _legacy_predecessor_completed_mismatches(
    verifier: Any,
    text: str,
    rows: Mapping[int, Mapping[str, Any]],
) -> tuple[list[str], set[int]]:
    lines = text.splitlines()
    body_statuses: dict[int, list[str]] = {}
    for block in verifier.parse_blocks(lines):
        statuses: list[str] = []
        for _, line in verifier.iter_unfenced_lines(block.body):
            match = verifier.STATUS_LINE.match(line)
            if match is not None:
                statuses.append(match.group("status"))
        body_statuses[block.number] = statuses
    table, table_errors = verifier.parse_status_table(lines)
    if table_errors:
        return [], set()
    errors: list[str] = []
    legacy_blocks: set[int] = set()
    for number, (table_status, _, line) in table.items():
        if (
            rows.get(number, {}).get("status") == "complete"
            and table_status == "complete"
            and body_statuses.get(number) == ["completed"]
        ):
            errors.append(
                f"line {line}: Block {number} table status 'complete' "
                "does not match block status 'completed'"
            )
            legacy_blocks.add(number)
    return errors, legacy_blocks


def _tracker_snapshot(
    path_value: str | Path,
    *,
    require_full: bool,
    allow_legacy_predecessor_completed: bool,
) -> dict[str, Any]:
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
    program_surface = active_program_surface_projection(text)
    structure_material = {
        "schema_version": 1,
        "kind": "implementation-tracker-structure",
        "blocks": contracts,
    }
    if program_surface is not None:
        structure_material["active_program_surface"] = program_surface
    structure_sha256 = digest(structure_material)
    program_control = parse_program_revision_control(text)
    if program_control is not None:
        expected_blocks = sorted(numbers)
        if (
            program_control["terminal_block"] != max(numbers)
            or program_control["required_order"] != expected_blocks
            or program_control["prose_reference_blocks"] != expected_blocks
            or program_control["source_map_blocks"] != expected_blocks
            or program_control["verification_matrix_blocks"] != expected_blocks
            or program_control["handoff_block"] not in rows
        ):
            raise ProgramRevisionError(
                "Active-program structural indexes differ from current Blocks"
            )
    verifier_result: dict[str, Any] | None = None
    if require_full:
        verifier = _load_full_verifier()
        verifier_result = verifier.verify(path, "full")
        verifier_errors = verifier_result.get("errors")
        if verifier_errors:
            expected_errors, legacy_blocks = _legacy_predecessor_completed_mismatches(
                verifier, text, rows
            )
            if not (
                allow_legacy_predecessor_completed
                and legacy_blocks
                and verifier_errors == expected_errors
            ):
                raise ProgramRevisionError(
                    "Proposed tracker fails the full structural verifier"
                )
            for number in legacy_blocks:
                rows[number]["status"] = "completed"
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "structure_sha256": structure_sha256,
        "blocks": rows,
        "program_revision_control": program_control,
        "active_program_surface_root": (
            digest(program_surface) if program_surface is not None else None
        ),
        "verifier_result_root": digest(verifier_result) if verifier_result else None,
    }


def tracker_snapshot(path_value: str | Path, *, require_full: bool = True) -> dict[str, Any]:
    return _tracker_snapshot(
        path_value,
        require_full=require_full,
        allow_legacy_predecessor_completed=False,
    )


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
        "predecessor_revision_id",
        "predecessor_review_root",
        "resolved_finding_refs",
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
        "application_owner_id",
        "reviewer_id",
        "authoring_profile_revision",
        "authoring_profile_root",
        "authoring_profile_source_revision",
        "authoring_profile_source_root",
        "authoring_profile_binding_root",
        "mechanical_watcher_id",
        "mechanical_route_record_id",
        "semantic_review_record_id",
        "semantic_review_root",
        "adjudicator_id",
        "adjudication_root",
        "fix_executor_id",
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
    previous = _tracker_snapshot(
        previous_tracker,
        require_full=True,
        allow_legacy_predecessor_completed=True,
    )
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
    successor_predecessors: dict[int, set[int]] = {}
    for old, targets in ((item, block_map[str(item)]) for item in old_blocks):
        for target in targets:
            successor_predecessors.setdefault(target, set()).add(old)
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
            successor_predecessors.get(targets[0]) != {old}
            or
            new_block["status"] != "completed"
            or new_block["scope"] != old_block["scope"]
            or new_block["history_sha256"] != item["history_sha256"]
            or new_block["mapped_contract_sha256"]
            != old_block["mapped_contract_sha256"]
            or new_block["dependencies"] != mapped_dependencies
        ):
            raise ProgramRevisionError("Accepted Block history was rewritten")
    for old, old_block in previous["blocks"].items():
        if old_block["status"] == "completed":
            continue
        if any(
            proposed["blocks"][target]["status"] == "completed"
            for target in block_map[str(old)]
        ):
            raise ProgramRevisionError("Open Block cannot map to completed work")
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
    proposed_control = proposed["program_revision_control"]
    if proposed_control is None:
        raise ProgramRevisionError(
            "Structural proposal lacks active-program revision control"
        )
    previous_control = previous["program_revision_control"]
    previous_history = previous_control["history"] if previous_control else []
    proposed_history = proposed_control["history"]
    if (
        len(proposed_history) != len(previous_history) + 1
        or proposed_history[:-1] != previous_history
    ):
        raise ProgramRevisionError("Program revision history is not append-only")
    expected_history_entry = {
        "revision_id": metadata["revision_id"],
        "previous_tracker_sha256": previous["sha256"],
        "current_tracker_structure_sha256": proposed["structure_sha256"],
        "block_map_root": digest(block_map),
        "affected_blocks": sorted(affected_new),
        "resume_block": resume_candidates[0],
    }
    if (
        proposed_history[-1] != expected_history_entry
        or proposed_control["handoff_block"] != resume_candidates[0]
    ):
        raise ProgramRevisionError(
            "Program revision history or handoff differs from the exact delta"
        )
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
        "predecessor_revision_id": (
            safe_id(
                metadata["predecessor_revision_id"],
                label="predecessor program revision ID",
            )
            if metadata["predecessor_revision_id"] is not None
            else None
        ),
        "predecessor_review_root": (
            exact_sha256(
                metadata["predecessor_review_root"],
                label="predecessor program review root",
            )
            if metadata["predecessor_review_root"] is not None
            else None
        ),
        "resolved_finding_refs": exact_string_list(
            metadata["resolved_finding_refs"],
            label="resolved program revision findings",
            allow_empty=True,
        ),
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
        "application_owner_id": safe_id(
            metadata["application_owner_id"], label="application owner ID"
        ),
        "reviewer_id": safe_id(metadata["reviewer_id"], label="reviewer ID"),
        "authoring_profile_revision": safe_id(
            metadata["authoring_profile_revision"],
            label="tracker-authoring profile revision",
        ),
        "authoring_profile_root": exact_sha256(
            metadata["authoring_profile_root"],
            label="tracker-authoring profile root",
        ),
        "authoring_profile_source_revision": exact_git_revision(
            metadata["authoring_profile_source_revision"],
            label="tracker-authoring profile source revision",
        ),
        "authoring_profile_source_root": exact_sha256(
            metadata["authoring_profile_source_root"],
            label="tracker-authoring profile source root",
        ),
        "authoring_profile_binding_root": exact_sha256(
            metadata["authoring_profile_binding_root"],
            label="tracker-authoring binding root",
        ),
        "mechanical_watcher_id": safe_id(
            metadata["mechanical_watcher_id"], label="mechanical watcher ID"
        ),
        "mechanical_route_record_id": safe_id(
            metadata["mechanical_route_record_id"],
            label="mechanical route record ID",
        ),
        "semantic_review_record_id": safe_id(
            metadata["semantic_review_record_id"],
            label="semantic review record ID",
        ),
        "semantic_review_root": exact_sha256(
            metadata["semantic_review_root"], label="semantic review root"
        ),
        "adjudicator_id": safe_id(
            metadata["adjudicator_id"], label="program adjudicator ID"
        ),
        "adjudication_root": exact_sha256(
            metadata["adjudication_root"], label="program adjudication root"
        ),
        "fix_executor_id": (
            safe_id(metadata["fix_executor_id"], label="fix executor ID")
            if metadata["fix_executor_id"] is not None
            else None
        ),
        "stop": safe_id(metadata["stop"], label="revision Stop"),
        "full_verifier_result_root": proposed["verifier_result_root"],
    }
    if packet["target_class"] not in ALLOWED_TARGET_CLASSES:
        raise ProgramRevisionError("Program revision target class is invalid")
    if packet["authority_mode"] not in ALLOWED_AUTHORITY_MODES:
        raise ProgramRevisionError("Program revision authority mode is invalid")
    role_ids = {
        packet["author_id"],
        packet["reviewer_id"],
        packet["mechanical_watcher_id"],
        packet["adjudicator_id"],
    }
    if (
        len(role_ids) != 4
        or packet["application_owner_id"] == packet["author_id"]
        or packet["fix_executor_id"] in role_ids
    ):
        raise ProgramRevisionError("Program revision authoring roles must differ")
    if (
        (packet["predecessor_revision_id"] is None)
        != (packet["predecessor_review_root"] is None)
        or (
            packet["predecessor_revision_id"] is None
            and packet["resolved_finding_refs"]
        )
    ):
        raise ProgramRevisionError("Program revision finding lineage is incomplete")
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
        "predecessor_revision_id",
        "predecessor_review_root",
        "resolved_finding_refs",
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
        "application_owner_id",
        "reviewer_id",
        "authoring_profile_revision",
        "authoring_profile_root",
        "authoring_profile_source_revision",
        "authoring_profile_source_root",
        "authoring_profile_binding_root",
        "mechanical_watcher_id",
        "mechanical_route_record_id",
        "semantic_review_record_id",
        "semantic_review_root",
        "adjudicator_id",
        "adjudication_root",
        "fix_executor_id",
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
        "authoring_profile_root",
        "authoring_profile_source_root",
        "authoring_profile_binding_root",
        "semantic_review_root",
        "adjudication_root",
        "packet_root",
    ):
        exact_sha256(packet.get(field), label=field.replace("_", " "))
    if packet.get("predecessor_review_root") is not None:
        exact_sha256(
            packet.get("predecessor_review_root"),
            label="predecessor program review root",
        )
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
        "application_owner_id",
        "reviewer_id",
        "authoring_profile_revision",
        "mechanical_watcher_id",
        "mechanical_route_record_id",
        "semantic_review_record_id",
        "adjudicator_id",
        "stop",
    ):
        safe_id(packet.get(field), label=field.replace("_", " "))
    exact_git_revision(
        packet.get("authoring_profile_source_revision"),
        label="tracker-authoring profile source revision",
    )
    if packet.get("predecessor_revision_id") is not None:
        safe_id(
            packet.get("predecessor_revision_id"),
            label="predecessor program revision ID",
        )
    exact_string_list(
        packet.get("resolved_finding_refs"),
        label="resolved program revision findings",
        allow_empty=True,
    )
    if (
        (packet.get("predecessor_revision_id") is None)
        != (packet.get("predecessor_review_root") is None)
        or (
            packet.get("predecessor_revision_id") is None
            and packet.get("resolved_finding_refs")
        )
    ):
        raise ProgramRevisionError("Stored program revision finding lineage differs")
    if packet.get("fix_executor_id") is not None:
        safe_id(packet.get("fix_executor_id"), label="fix executor ID")
    role_ids = {
        packet["author_id"],
        packet["reviewer_id"],
        packet["mechanical_watcher_id"],
        packet["adjudicator_id"],
    }
    if (
        len(role_ids) != 4
        or packet["application_owner_id"] == packet["author_id"]
        or packet.get("fix_executor_id") in role_ids
    ):
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
        "predecessor_revision_id",
        "predecessor_review_root",
        "resolved_finding_refs",
        "packet_root",
        "previous_tracker_sha256",
        "proposed_tracker_sha256",
        "proposed_tracker_structure_sha256",
        "accepted_history_root",
        "block_map_root",
        "affected_closure_root",
        "resume_block",
        "author_id",
        "application_owner_id",
        "reviewer_id",
        "mechanical_watcher_id",
        "adjudicator_id",
        "fix_executor_id",
        "authoring_profile_source_revision",
        "authoring_profile_source_root",
        "authoring_profile_binding_root",
        "mechanical_route_record_id",
        "semantic_review_record_id",
        "adjudication_root",
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
        "predecessor_revision_id": packet["predecessor_revision_id"],
        "predecessor_review_root": packet["predecessor_review_root"],
        "resolved_finding_refs": packet["resolved_finding_refs"],
        "packet_root": packet["packet_root"],
        "previous_tracker_sha256": packet["previous_tracker_sha256"],
        "proposed_tracker_sha256": packet["proposed_tracker_sha256"],
        "proposed_tracker_structure_sha256": packet["proposed_tracker_structure_sha256"],
        "accepted_history_root": packet["accepted_history_root"],
        "block_map_root": digest(packet["block_number_map"]),
        "affected_closure_root": digest(packet["affected_proposed_blocks"]),
        "resume_block": packet["resume_block"],
        "author_id": packet["author_id"],
        "application_owner_id": packet["application_owner_id"],
        "reviewer_id": packet["reviewer_id"],
        "mechanical_watcher_id": packet["mechanical_watcher_id"],
        "adjudicator_id": packet["adjudicator_id"],
        "fix_executor_id": packet["fix_executor_id"],
        "authoring_profile_source_revision": packet[
            "authoring_profile_source_revision"
        ],
        "authoring_profile_source_root": packet[
            "authoring_profile_source_root"
        ],
        "authoring_profile_binding_root": packet[
            "authoring_profile_binding_root"
        ],
        "mechanical_route_record_id": packet["mechanical_route_record_id"],
        "semantic_review_record_id": packet["semantic_review_record_id"],
        "adjudication_root": packet["adjudication_root"],
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
