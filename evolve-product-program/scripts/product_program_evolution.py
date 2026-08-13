#!/usr/bin/env python3
"""Deterministic product-program evidence and derived evolution artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
TRANSFORMATION_VERSION = "product-program-evidence-v1"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_SOURCE_RECORDS = 64
MAX_BLOCKS = 512
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
RESOURCE_EVIDENCE_CLASSES = {
    "observed",
    "provider-reported",
    "estimated",
    "inferred",
    "unavailable",
}
SOURCE_EVIDENCE_CLASSES = RESOURCE_EVIDENCE_CLASSES | {
    "direct-authority",
    "current-repository",
    "canonical-owner",
    "observed-outcome",
    "independent-review",
    "validation",
}
FORBIDDEN_RETAINED_KEYS = {
    "body",
    "content",
    "credential",
    "credentials",
    "hidden_reasoning",
    "prompt",
    "raw_content",
    "raw_output",
    "raw_transcript",
    "reasoning",
    "secret",
    "secrets",
    "transcript",
}


class ProductProgramError(ValueError):
    """Raised when an evidence packet is invalid or stale."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ProductProgramError(f"{label} keys differ")
    return value


def exact_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX_64.fullmatch(value) is None:
        raise ProductProgramError(f"{label} must be a lowercase SHA-256")
    return value


def exact_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise ProductProgramError(f"{label} is not a bounded identifier")
    return value


def exact_string_list(value: Any, label: str, *, maximum: int = MAX_SOURCE_RECORDS) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum or not all(isinstance(item, str) and item for item in value):
        raise ProductProgramError(f"{label} must be a bounded string array")
    if value != sorted(set(value)):
        raise ProductProgramError(f"{label} must be sorted and unique")
    return list(value)


def exact_block_list(value: Any, label: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) > MAX_BLOCKS
        or not all(isinstance(item, int) and item >= 0 for item in value)
        or value != sorted(set(value))
    ):
        raise ProductProgramError(f"{label} must be a sorted unique Block array")
    return list(value)


def load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductProgramError(f"{label} is not valid JSON") from exc


def _literal_absolute_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or value.startswith("~") or "$HOME" in value:
        raise ProductProgramError(f"{label} must be a literal absolute path")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ProductProgramError(f"{label} must be a literal absolute path")
    return path


def read_bounded_regular(path_value: Any, owner_value: Any, label: str) -> tuple[bytes, str]:
    path = _literal_absolute_path(path_value, f"{label} path")
    owner_root = _literal_absolute_path(owner_value, f"{label} owner root")
    if owner_root in {Path("/"), Path.home().resolve()}:
        raise ProductProgramError(f"{label} owner root is too broad")
    if not owner_root.is_dir() or owner_root.resolve() != owner_root:
        raise ProductProgramError(f"{label} owner root is not an exact directory")
    try:
        relative = path.relative_to(owner_root)
    except ValueError as exc:
        raise ProductProgramError(f"{label} escapes its owner root") from exc
    if not relative.parts:
        raise ProductProgramError(f"{label} is not a regular file")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | nofollow
    open_directories: list[int] = []
    descriptor: int | None = None
    try:
        directory = os.open(owner_root, directory_flags)
        open_directories.append(directory)
        for part in relative.parts[:-1]:
            directory = os.open(part, directory_flags, dir_fd=directory)
            open_directories.append(directory)
        descriptor = os.open(relative.parts[-1], os.O_RDONLY | nofollow, dir_fd=directory)
    except OSError as exc:
        for directory in reversed(open_directories):
            os.close(directory)
        raise ProductProgramError(f"{label} cannot be opened without following symlinks") from exc
    try:
        assert descriptor is not None
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ProductProgramError(f"{label} is not a regular file")
        if before.st_size > MAX_SOURCE_BYTES:
            raise ProductProgramError(f"{label} exceeds the byte ceiling")
        chunks: list[bytes] = []
        remaining = MAX_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or len(raw) != before.st_size:
            raise ProductProgramError(f"{label} changed during its bounded read")
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory in reversed(open_directories):
            os.close(directory)
    return raw, str(path)


def source_descriptor(value: Any, label: str, *, resource_only: bool = False) -> tuple[dict[str, Any], bytes]:
    item = exact_keys(
        value,
        {"evidence_class", "owner_root", "path", "sha256", "source_id"},
        label,
    )
    source_id = exact_id(item["source_id"], f"{label} source ID")
    evidence_class = item["evidence_class"]
    allowed = RESOURCE_EVIDENCE_CLASSES if resource_only else SOURCE_EVIDENCE_CLASSES
    if evidence_class not in allowed:
        raise ProductProgramError(f"{label} evidence class is invalid")
    expected = exact_sha(item["sha256"], f"{label} SHA-256")
    raw, exact_path = read_bounded_regular(item["path"], item["owner_root"], label)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ProductProgramError(f"{label} is stale")
    retained = {
        "byte_length": len(raw),
        "evidence_class": evidence_class,
        "path_sha256": hashlib.sha256(exact_path.encode("utf-8")).hexdigest(),
        "sha256": actual,
        "source_id": source_id,
    }
    return retained, raw


def source_array(value: Any, label: str, *, resource_only: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_SOURCE_RECORDS:
        raise ProductProgramError(f"{label} must be a bounded source array")
    retained = [source_descriptor(item, f"{label} item", resource_only=resource_only)[0] for item in value]
    retained.sort(key=lambda item: item["source_id"])
    if len({item["source_id"] for item in retained}) != len(retained):
        raise ProductProgramError(f"{label} repeats a source ID")
    return retained


def event_record_sources(raw: bytes, event_source: Mapping[str, Any], kind: str) -> list[dict[str, Any]]:
    retained: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        value = load_json_bytes(line, f"supervision event line {index}")
        if not isinstance(value, Mapping) or value.get("kind") != kind:
            continue
        record_id = exact_id(value.get("record_id"), f"{kind} event record ID")
        retained.append(
            {
                "byte_length": len(line),
                "evidence_class": "canonical-owner",
                "path_sha256": event_source["path_sha256"],
                "sha256": hashlib.sha256(line).hexdigest(),
                "source_id": record_id,
            }
        )
    retained.sort(key=lambda item: item["source_id"])
    if len({item["source_id"] for item in retained}) != len(retained):
        raise ProductProgramError(f"supervision {kind} records repeat an ID")
    return retained


def run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ProductProgramError(f"Git currentness command failed: {' '.join(arguments)}")
    return result.stdout.strip()


BLOCK_HEADING = re.compile(r"^## Block (\d+)\s+[-—]", re.M)
STATUS_LINE = re.compile(r"^Status:\s*`([^`]+)`\s*$", re.M)
TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|.*?\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*$", re.M)


def tracker_snapshot(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProductProgramError("tracker is not UTF-8") from exc
    matches = list(BLOCK_HEADING.finditer(text))
    if not matches:
        raise ProductProgramError("tracker has no Blocks")
    rows: dict[int, dict[str, Any]] = {}
    table_values = {int(number): (dependencies.strip(), status) for number, dependencies, status in TABLE_ROW.findall(text)}
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if number in rows:
            raise ProductProgramError("tracker repeats a Block")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start():end]
        status_match = STATUS_LINE.search(section)
        if status_match is None or number not in table_values:
            raise ProductProgramError("tracker Block status is incomplete")
        dependency_text, table_status = table_values[number]
        status_value = status_match.group(1)
        if table_status != status_value:
            raise ProductProgramError("tracker Block status sources differ")
        dependencies = [] if dependency_text in {"—", "-", "none"} else [int(item) for item in re.findall(r"\d+", dependency_text)]
        evidence_start = section.find("### Completion evidence")
        stop_start = section.find("### Stop")
        if evidence_start < 0 or stop_start < evidence_start:
            raise ProductProgramError("tracker Block contract is incomplete")
        structural = section[:evidence_start] + section[stop_start:]
        structural = STATUS_LINE.sub("Status: `<runtime-status>`", structural)
        rows[number] = {
            "contract_root": hashlib.sha256(structural.encode("utf-8")).hexdigest(),
            "dependencies": sorted(set(dependencies)),
            "status": status_value,
        }
    numbers = sorted(rows)
    if numbers != list(range(numbers[0], numbers[-1] + 1)) or len(numbers) > MAX_BLOCKS:
        raise ProductProgramError("tracker Block sequence differs")
    structure_root = digest(
        {
            "blocks": [
                {"contract_root": rows[number]["contract_root"], "dependencies": rows[number]["dependencies"], "number": number}
                for number in numbers
            ],
            "kind": "product-program-tracker-structure",
            "schema_version": 1,
        }
    )
    return {"blocks": rows, "structure_root": structure_root}


def _normalize_outcome(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"evidence_ids", "root", "status"}, "current outcome")
    if item["status"] not in {"in-progress", "completed", "failed", "open"}:
        raise ProductProgramError("current outcome status is invalid")
    return {
        "evidence_ids": exact_string_list(item["evidence_ids"], "outcome evidence IDs"),
        "root": exact_sha(item["root"], "outcome root"),
        "status": item["status"],
    }


def _normalize_protected(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_SOURCE_RECORDS:
        raise ProductProgramError("protected capabilities must be a bounded nonempty array")
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(raw, {"capability_id", "result", "source_root"}, "protected capability")
        if item["result"] not in {"preserved", "changed", "open"}:
            raise ProductProgramError("protected capability result is invalid")
        result.append(
            {
                "capability_id": exact_id(item["capability_id"], "protected capability ID"),
                "result": item["result"],
                "source_root": exact_sha(item["source_root"], "protected capability source root"),
            }
        )
    result.sort(key=lambda item: item["capability_id"])
    if len({item["capability_id"] for item in result}) != len(result):
        raise ProductProgramError("protected capabilities repeat an ID")
    return result


def _packet_fields() -> set[str]:
    contract_path = Path(__file__).resolve().parents[1] / "fixtures" / "product_program_contract_v1.json"
    contract = load_json_bytes(contract_path.read_bytes(), "contract fixture")
    fields = contract["artifact_schemas"]["product-program-evidence-packet"]
    return set(fields)


def _reject_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_RETAINED_KEYS:
                raise ProductProgramError("packet contains forbidden raw-content field")
            _reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item)


def _validate_retained_sources(value: Any, label: str, *, resource_only: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_SOURCE_RECORDS:
        raise ProductProgramError(f"{label} retained sources are unbounded")
    allowed = RESOURCE_EVIDENCE_CLASSES if resource_only else SOURCE_EVIDENCE_CLASSES
    result: list[dict[str, Any]] = []
    for raw in value:
        item = exact_keys(raw, {"byte_length", "evidence_class", "path_sha256", "sha256", "source_id"}, f"{label} retained source")
        if not isinstance(item["byte_length"], int) or not 0 <= item["byte_length"] <= MAX_SOURCE_BYTES:
            raise ProductProgramError(f"{label} retained byte length is invalid")
        if item["evidence_class"] not in allowed:
            raise ProductProgramError(f"{label} retained evidence class is invalid")
        exact_sha(item["path_sha256"], f"{label} retained path hash")
        exact_sha(item["sha256"], f"{label} retained content hash")
        exact_id(item["source_id"], f"{label} retained source ID")
        result.append(dict(item))
    if result != sorted(result, key=lambda item: item["source_id"]) or len({item["source_id"] for item in result}) != len(result):
        raise ProductProgramError(f"{label} retained sources must be sorted and unique")
    return result


def _semantic_material_from_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    def semantic_sources(sources: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "byte_length": source["byte_length"],
                "evidence_class": source["evidence_class"],
                "sha256": source["sha256"],
                "source_id": source["source_id"],
            }
            for source in sources
        ]

    return {
        "decisions": semantic_sources(packet["decisions"]),
        "incidents": semantic_sources(packet["incidents"]),
        "mission": packet["mission"],
        "outcome": packet["outcome"],
        "product_sources": semantic_sources(packet["product_sources"]),
        "profile": packet["profile"],
        "protected_capabilities": packet["protected_capabilities"],
        "range": {
            "accepted_blocks": packet["range"]["accepted_blocks"],
            "next_eligible_blocks": packet["range"]["next_eligible_blocks"],
            "remaining_blocks": packet["range"]["remaining_blocks"],
            "requested_blocks": packet["range"]["requested_blocks"],
        },
        "repository": {
            "revision": packet["repository"]["revision"],
            "tree": packet["repository"]["tree"],
        },
        "resource_sources": semantic_sources(packet["resource_sources"]),
        "tracker_structure_root": packet["tracker"]["structural_root"],
    }


def prepare_packet(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    expected_checkpoint = {
        "current_outcome",
        "mission",
        "prior_checkpoint_identity",
        "product_sources",
        "profile",
        "protected_capabilities",
        "range",
        "reports",
        "repository",
        "resource_sources",
        "schema_version",
        "supervision",
        "tracker",
    }
    exact_keys(checkpoint, expected_checkpoint, "checkpoint")
    if checkpoint["schema_version"] != SCHEMA_VERSION or checkpoint["profile"] != "target-product-program":
        raise ProductProgramError("checkpoint identity differs")
    prior_identity = checkpoint["prior_checkpoint_identity"]
    if prior_identity is not None:
        prior = exact_keys(
            prior_identity,
            {"currentness_root", "material_change_fingerprint"},
            "prior checkpoint identity",
        )
        exact_sha(prior["currentness_root"], "prior checkpoint currentness root")
        exact_sha(prior["material_change_fingerprint"], "prior checkpoint material fingerprint")
    mission_input = exact_keys(checkpoint["mission"], {"mission_root", "source_record", "source_sha256"}, "mission")
    mission = {
        "mission_root": exact_sha(mission_input["mission_root"], "mission root"),
        "source_record": exact_id(mission_input["source_record"], "mission source record"),
        "source_sha256": exact_sha(mission_input["source_sha256"], "mission source SHA-256"),
    }
    repository_input = exact_keys(checkpoint["repository"], {"revision", "root", "tree"}, "repository")
    root = _literal_absolute_path(repository_input["root"], "repository root")
    if root == Path("/") or not root.is_dir() or root.resolve() != root or stat.S_ISLNK(os.lstat(root).st_mode):
        raise ProductProgramError("repository root is substituted or symlinked")
    top_level = run_git(root, "rev-parse", "--show-toplevel")
    if top_level != str(root):
        raise ProductProgramError("repository root is not the exact Git top level")
    revision = run_git(root, "rev-parse", "HEAD")
    tree = run_git(root, "rev-parse", "HEAD^{tree}")
    if repository_input["revision"] != revision or repository_input["tree"] != tree:
        raise ProductProgramError("repository revision or tree is stale")
    repository = {
        "revision": revision,
        "root_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "tree": tree,
    }
    tracker_input = exact_keys(checkpoint["tracker"], {"path", "sha256", "structural_root"}, "tracker")
    tracker_raw, tracker_path = read_bounded_regular(tracker_input["path"], str(root), "tracker")
    tracker_sha = hashlib.sha256(tracker_raw).hexdigest()
    if tracker_sha != exact_sha(tracker_input["sha256"], "tracker SHA-256"):
        raise ProductProgramError("tracker is stale")
    parsed_tracker = tracker_snapshot(tracker_raw)
    if parsed_tracker["structure_root"] != exact_sha(tracker_input["structural_root"], "tracker structural root"):
        raise ProductProgramError("tracker structure is stale")
    tracker_blocks: dict[int, dict[str, Any]] = parsed_tracker["blocks"]
    tracker = {
        "blocks": [
            {"dependencies": tracker_blocks[number]["dependencies"], "number": number, "status": tracker_blocks[number]["status"]}
            for number in sorted(tracker_blocks)
        ],
        "path_sha256": hashlib.sha256(tracker_path.encode("utf-8")).hexdigest(),
        "sha256": tracker_sha,
        "structural_root": parsed_tracker["structure_root"],
    }
    range_input = exact_keys(checkpoint["range"], {"accepted_blocks", "range_head_source", "requested_blocks"}, "range")
    requested = exact_block_list(range_input["requested_blocks"], "requested Blocks")
    accepted = exact_block_list(range_input["accepted_blocks"], "accepted Blocks")
    if not requested or set(requested) - set(tracker_blocks) or set(accepted) - set(requested):
        raise ProductProgramError("range Blocks differ from the tracker")
    derived_accepted = sorted(number for number in requested if tracker_blocks[number]["status"] == "accepted")
    if accepted != derived_accepted:
        raise ProductProgramError("range accepted Blocks are stale")
    range_source, range_raw = source_descriptor(range_input["range_head_source"], "range head")
    range_value = load_json_bytes(range_raw, "range head")
    range_record = exact_keys(range_value, {"range_head", "requested_blocks", "target_thread_id"}, "range head record")
    if exact_block_list(range_record["requested_blocks"], "range-head requested Blocks") != requested:
        raise ProductProgramError("range head requested Blocks mismatch")
    range_head = exact_sha(range_record["range_head"], "range head root")
    target_thread_id = exact_id(range_record["target_thread_id"], "range target thread ID")
    remaining = sorted(set(requested) - set(accepted))
    eligible = [
        number
        for number in remaining
        if set(tracker_blocks[number]["dependencies"]) <= set(accepted)
    ]
    range_value_retained = {
        "accepted_blocks": accepted,
        "next_eligible_blocks": eligible,
        "range_head": range_head,
        "range_source": range_source,
        "remaining_blocks": remaining,
        "requested_blocks": requested,
    }
    supervision_input = exact_keys(checkpoint["supervision"], {"event_source", "policy_source", "target_thread_id"}, "supervision")
    if exact_id(supervision_input["target_thread_id"], "supervision target thread ID") != target_thread_id:
        raise ProductProgramError("supervision target mismatches the range target")
    policy_source, _ = source_descriptor(supervision_input["policy_source"], "supervision policy")
    event_source, event_raw = source_descriptor(supervision_input["event_source"], "supervision events")
    supervision = {
        "event_source": event_source,
        "policy_source": policy_source,
        "target_thread_id": target_thread_id,
    }
    product_sources = source_array(checkpoint["product_sources"], "product sources")
    if not product_sources:
        raise ProductProgramError("at least one exact product source is required")
    reports = source_array(checkpoint["reports"], "reports")
    decisions = event_record_sources(event_raw, event_source, "decision")
    incidents = event_record_sources(event_raw, event_source, "incident")
    resource_sources = source_array(checkpoint["resource_sources"], "resource sources", resource_only=True)
    if not resource_sources:
        raise ProductProgramError("at least one typed resource source is required")
    outcome = _normalize_outcome(checkpoint["current_outcome"])
    protected = _normalize_protected(checkpoint["protected_capabilities"])

    # Re-open every mutable owner source and re-check Git immediately before
    # deriving identity. A file that changes after its first bounded read must
    # never be represented by a packet rooted in that obsolete snapshot.
    if source_descriptor(range_input["range_head_source"], "range head")[0] != range_source:
        raise ProductProgramError("range head changed during packet preparation")
    if source_descriptor(supervision_input["policy_source"], "supervision policy")[0] != policy_source:
        raise ProductProgramError("supervision policy changed during packet preparation")
    if source_descriptor(supervision_input["event_source"], "supervision events")[0] != event_source:
        raise ProductProgramError("supervision events changed during packet preparation")
    if source_array(checkpoint["product_sources"], "product sources") != product_sources:
        raise ProductProgramError("product sources changed during packet preparation")
    if source_array(checkpoint["reports"], "reports") != reports:
        raise ProductProgramError("reports changed during packet preparation")
    if source_array(checkpoint["resource_sources"], "resource sources", resource_only=True) != resource_sources:
        raise ProductProgramError("resource sources changed during packet preparation")
    tracker_recheck, _ = read_bounded_regular(tracker_input["path"], str(root), "tracker")
    if hashlib.sha256(tracker_recheck).hexdigest() != tracker_sha or tracker_snapshot(tracker_recheck) != parsed_tracker:
        raise ProductProgramError("tracker changed during packet preparation")
    if run_git(root, "rev-parse", "HEAD") != revision or run_git(root, "rev-parse", "HEAD^{tree}") != tree:
        raise ProductProgramError("repository changed during packet preparation")

    packet_material = {
        "decisions": decisions,
        "incidents": incidents,
        "mission": mission,
        "outcome": outcome,
        "product_sources": product_sources,
        "profile": checkpoint["profile"],
        "protected_capabilities": protected,
        "range": range_value_retained,
        "reports": reports,
        "repository": repository,
        "resource_sources": resource_sources,
        "tracker": tracker,
    }
    semantic_material = _semantic_material_from_packet(packet_material)
    material_fingerprint = digest({"kind": "product-program-material-change", "value": semantic_material})
    currentness = digest(
        {
            "kind": "product-program-currentness",
            "material_change_fingerprint": material_fingerprint,
            "range_head": range_head,
            "repository": repository,
            "source_currentness": {
                "product_sources": product_sources,
                "reports": reports,
                "resource_sources": resource_sources,
            },
            "supervision": supervision,
            "tracker_sha256": tracker_sha,
        }
    )
    packet: dict[str, Any] = {
        "artifact_root": "",
        "authority": {
            "direct_effects_allowed": False,
            "posture": "derived-nonauthorizing",
            "source_record": mission["source_record"],
        },
        "currentness_root": currentness,
        "decisions": decisions,
        "incidents": incidents,
        "kind": "product-program-evidence-packet",
        "material_change_fingerprint": material_fingerprint,
        "mission": mission,
        "outcome": outcome,
        "packet_id": f"program-packet-{material_fingerprint[:20]}",
        "product_sources": product_sources,
        "profile": checkpoint["profile"],
        "protected_capabilities": protected,
        "range": range_value_retained,
        "reports": reports,
        "repository": repository,
        "resource_sources": resource_sources,
        "schema_version": SCHEMA_VERSION,
        "supervision": supervision,
        "tracker": tracker,
        "transformation_version": TRANSFORMATION_VERSION,
    }
    if set(packet) != _packet_fields():
        raise ProductProgramError("packet implementation differs from the frozen schema")
    packet["artifact_root"] = digest({key: packet[key] for key in packet if key != "artifact_root"})
    verify_packet(packet)
    return packet


def verify_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    exact_keys(packet, _packet_fields(), "packet")
    _reject_forbidden(packet)
    if packet["schema_version"] != SCHEMA_VERSION or packet["kind"] != "product-program-evidence-packet":
        raise ProductProgramError("packet identity differs")
    if packet["transformation_version"] != TRANSFORMATION_VERSION or packet["profile"] != "target-product-program":
        raise ProductProgramError("packet transformation or profile differs")
    exact_sha(packet["material_change_fingerprint"], "packet material fingerprint")
    exact_sha(packet["currentness_root"], "packet currentness root")
    exact_id(packet["packet_id"], "packet ID")
    if packet["packet_id"] != f"program-packet-{packet['material_change_fingerprint'][:20]}":
        raise ProductProgramError("packet ID does not bind its material fingerprint")
    authority = exact_keys(packet["authority"], {"direct_effects_allowed", "posture", "source_record"}, "packet authority")
    if authority["direct_effects_allowed"] is not False or authority["posture"] != "derived-nonauthorizing":
        raise ProductProgramError("packet asserts downstream authority")
    mission = exact_keys(packet["mission"], {"mission_root", "source_record", "source_sha256"}, "packet mission")
    exact_sha(mission["mission_root"], "packet mission root")
    exact_sha(mission["source_sha256"], "packet mission source hash")
    exact_id(mission["source_record"], "packet mission source record")
    if authority["source_record"] != mission["source_record"]:
        raise ProductProgramError("packet authority provenance differs")
    repository = exact_keys(packet["repository"], {"revision", "root_sha256", "tree"}, "packet repository")
    if not isinstance(repository["revision"], str) or HEX_40.fullmatch(repository["revision"]) is None:
        raise ProductProgramError("packet repository revision is invalid")
    if not isinstance(repository["tree"], str) or HEX_40.fullmatch(repository["tree"]) is None:
        raise ProductProgramError("packet repository tree is invalid")
    exact_sha(repository["root_sha256"], "packet repository root hash")
    product_sources = _validate_retained_sources(packet["product_sources"], "product sources")
    if not product_sources:
        raise ProductProgramError("packet requires at least one exact product source")
    _validate_retained_sources(packet["reports"], "reports")
    _validate_retained_sources(packet["decisions"], "decisions")
    _validate_retained_sources(packet["incidents"], "incidents")
    resource_sources = _validate_retained_sources(packet["resource_sources"], "resource sources", resource_only=True)
    if not resource_sources:
        raise ProductProgramError("packet requires at least one typed resource source")
    outcome = _normalize_outcome(packet["outcome"])
    if outcome != packet["outcome"]:
        raise ProductProgramError("packet outcome is not normalized")
    protected = _normalize_protected(packet["protected_capabilities"])
    if protected != packet["protected_capabilities"]:
        raise ProductProgramError("packet protected capabilities are not normalized")
    tracker = exact_keys(packet["tracker"], {"blocks", "path_sha256", "sha256", "structural_root"}, "packet tracker")
    exact_sha(tracker["path_sha256"], "packet tracker path hash")
    exact_sha(tracker["sha256"], "packet tracker hash")
    exact_sha(tracker["structural_root"], "packet tracker structural root")
    if not isinstance(tracker["blocks"], list) or not tracker["blocks"] or len(tracker["blocks"]) > MAX_BLOCKS:
        raise ProductProgramError("packet tracker Blocks are invalid")
    tracker_numbers: list[int] = []
    tracker_by_number: dict[int, Mapping[str, Any]] = {}
    for raw_block in tracker["blocks"]:
        block = exact_keys(raw_block, {"dependencies", "number", "status"}, "packet tracker Block")
        if not isinstance(block["number"], int) or block["number"] < 0 or not isinstance(block["status"], str) or not block["status"]:
            raise ProductProgramError("packet tracker Block identity is invalid")
        exact_block_list(block["dependencies"], "packet tracker Block dependencies")
        tracker_numbers.append(block["number"])
        tracker_by_number[block["number"]] = block
    if tracker_numbers != sorted(set(tracker_numbers)):
        raise ProductProgramError("packet tracker Blocks must be sorted and unique")
    if any(set(block["dependencies"]) - set(tracker_numbers) or block["number"] in block["dependencies"] for block in tracker_by_number.values()):
        raise ProductProgramError("packet tracker Block dependencies are invalid")
    range_value = exact_keys(
        packet["range"],
        {"accepted_blocks", "next_eligible_blocks", "range_head", "range_source", "remaining_blocks", "requested_blocks"},
        "packet range",
    )
    requested = exact_block_list(range_value["requested_blocks"], "packet requested Blocks")
    accepted = exact_block_list(range_value["accepted_blocks"], "packet accepted Blocks")
    remaining = exact_block_list(range_value["remaining_blocks"], "packet remaining Blocks")
    eligible = exact_block_list(range_value["next_eligible_blocks"], "packet eligible Blocks")
    if set(requested) - set(tracker_numbers):
        raise ProductProgramError("packet range references an absent tracker Block")
    derived_accepted = sorted(number for number in requested if tracker_by_number[number]["status"] == "accepted")
    derived_remaining = sorted(set(requested) - set(derived_accepted))
    derived_eligible = [
        number
        for number in derived_remaining
        if set(tracker_by_number[number]["dependencies"]) <= set(derived_accepted)
    ]
    if accepted != derived_accepted or remaining != derived_remaining or eligible != derived_eligible:
        raise ProductProgramError("packet range partition differs")
    exact_sha(range_value["range_head"], "packet range head")
    _validate_retained_sources([range_value["range_source"]], "range source")
    supervision = exact_keys(packet["supervision"], {"event_source", "policy_source", "target_thread_id"}, "packet supervision")
    exact_id(supervision["target_thread_id"], "packet supervision target")
    _validate_retained_sources([supervision["event_source"]], "supervision event source")
    _validate_retained_sources([supervision["policy_source"]], "supervision policy source")
    expected_material = digest({"kind": "product-program-material-change", "value": _semantic_material_from_packet(packet)})
    if packet["material_change_fingerprint"] != expected_material:
        raise ProductProgramError("packet material fingerprint is stale")
    expected_currentness = digest(
        {
            "kind": "product-program-currentness",
            "material_change_fingerprint": expected_material,
            "range_head": range_value["range_head"],
            "repository": repository,
            "source_currentness": {
                "product_sources": packet["product_sources"],
                "reports": packet["reports"],
                "resource_sources": packet["resource_sources"],
            },
            "supervision": supervision,
            "tracker_sha256": tracker["sha256"],
        }
    )
    if packet["currentness_root"] != expected_currentness:
        raise ProductProgramError("packet currentness root is stale")
    expected_root = digest({key: packet[key] for key in packet if key != "artifact_root"})
    if packet["artifact_root"] != expected_root:
        raise ProductProgramError("packet artifact root is stale")
    return {
        "artifact_root": expected_root,
        "currentness_root": packet["currentness_root"],
        "material_change_fingerprint": packet["material_change_fingerprint"],
        "packet_id": packet["packet_id"],
        "verified": True,
    }


def prepare_result(checkpoint: Mapping[str, Any], prior_packet: Mapping[str, Any] | None = None) -> dict[str, Any]:
    packet = prepare_packet(checkpoint)
    unchanged = False
    if prior_packet is not None:
        verify_packet(prior_packet)
        unchanged = (
            prior_packet["material_change_fingerprint"] == packet["material_change_fingerprint"]
            and prior_packet["currentness_root"] == packet["currentness_root"]
        )
    return {
        "action": "continue-program-unchanged" if unchanged else "packet-prepared",
        "changed": not unchanged,
        "cognitive_work_started": False,
        "model_calls": 0,
        "packet": packet,
        "schema_version": SCHEMA_VERSION,
    }


def read_json_file(path_value: str, label: str) -> Mapping[str, Any]:
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    raw, _ = read_bounded_regular(str(path), str(path.parent), label)
    value = load_json_bytes(raw, label)
    if not isinstance(value, Mapping):
        raise ProductProgramError(f"{label} must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Prepare or rehydrate a deterministic packet")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--prior-packet")
    verify = subparsers.add_parser("verify", help="Verify a retained packet")
    verify.add_argument("--packet", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            checkpoint = read_json_file(args.input, "checkpoint input")
            prior = read_json_file(args.prior_packet, "prior packet") if args.prior_packet else None
            result = prepare_result(checkpoint, prior)
        else:
            packet = read_json_file(args.packet, "packet")
            result = verify_packet(packet)
    except ProductProgramError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
