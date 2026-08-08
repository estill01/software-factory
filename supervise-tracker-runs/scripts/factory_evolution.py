#!/usr/bin/env python3
"""Pure, deterministic builders and validators for Factory evolution artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
PACKET_KIND = "software-factory-learning-packet"
PACKET_AUTHORITY = "derived-non-authoritative"
TRANSFORMATION = {
    "name": "factory-evolution-learning-packet",
    "version": 1,
}
SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_EVENT_RECORDS = 10_000
MAX_EXPLICIT_REPORT_INPUTS = 32
MAX_EXPLICIT_EVENT_INPUTS = 32
MAX_PACKET_REPORTS = 16
MAX_PACKET_LEDGERS = 16
MAX_PACKET_EVENTS = 5_000
MAX_PACKET_HYPOTHESES = 512
MAX_PACKET_CANONICAL_RECORDS = 10_000
MAX_REPORT_HYPOTHESES = 64
MAX_EVIDENCE_REFS = 8
MAX_EVENT_TEXT = 280
MAX_REPORT_TEXT = 360
MAX_REFERENCE_TEXT = 180

SUPPORTED_EVENT_KINDS = frozenset(
    {
        "check",
        "checkpoint-review",
        "decision",
        "escalation",
        "incident",
        "lifecycle",
        "meta-review",
        "notification",
        "policy-change",
        "resolution",
        "roundup",
        "steer",
    }
)
FORBIDDEN_SOURCE_KEYS = frozenset(
    {
        "file_contents",
        "full_text",
        "messages",
        "raw_messages",
        "raw_transcript",
        "target_content",
        "target_files",
        "transcript",
    }
)
REFERENCE_KEYS = frozenset(
    {
        "event_id",
        "incident_id",
        "kind",
        "path",
        "record_id",
        "sha256",
        "source",
        "status",
    }
)


class FactoryEvolutionError(ValueError):
    """Raised when an evolution input or derived artifact is invalid."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _exact_sha256(value: Any, *, label: str) -> str:
    text = str(value).strip()
    if not SHA256.fullmatch(text):
        raise FactoryEvolutionError(f"{label} must be an exact lowercase SHA-256")
    return text


def _exact_identifier(value: Any, *, label: str, limit: int = 160) -> str:
    if not isinstance(value, str):
        raise FactoryEvolutionError(f"{label} must be a string")
    if not value or len(value) > limit or value != value.strip():
        raise FactoryEvolutionError(f"{label} must be an exact bounded identifier")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value):
        raise FactoryEvolutionError(f"{label} contains unsafe identifier characters")
    return value


def _bounded_text(value: Any, *, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, (str, int, float, bool)):
        raise FactoryEvolutionError("Retained text must be a scalar")
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _read_once(path: str | Path) -> tuple[Path, bytes]:
    source = Path(path).expanduser()
    try:
        if not source.is_file():
            raise FactoryEvolutionError(f"Explicit source is not a file: {source}")
        size = source.stat().st_size
        if size > MAX_SOURCE_BYTES:
            raise FactoryEvolutionError(
                f"Explicit source exceeds {MAX_SOURCE_BYTES} bytes: {source.name}"
            )
        return source, source.read_bytes()
    except OSError as exc:
        raise FactoryEvolutionError(f"Cannot read explicit source: {source}") from exc


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FactoryEvolutionError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise FactoryEvolutionError(f"{label} must contain a JSON object")
    return value


def _reject_forbidden_source_keys(value: Any, *, label: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in FORBIDDEN_SOURCE_KEYS:
                raise FactoryEvolutionError(
                    f"{label} contains forbidden raw-content field {key!r}"
                )
            _reject_forbidden_source_keys(item, label=label)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_source_keys(item, label=label)


def _evidence_ref(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return _bounded_text(value, limit=MAX_REFERENCE_TEXT)
    if isinstance(value, Mapping):
        retained = {
            str(key): _bounded_text(item, limit=MAX_REFERENCE_TEXT)
            for key, item in value.items()
            if str(key) in REFERENCE_KEYS
            and isinstance(item, (str, int, float, bool))
        }
        return _bounded_text(
            canonical(retained).decode("utf-8") if retained else "[structured reference omitted]",
            limit=MAX_REFERENCE_TEXT,
        )
    return "[non-scalar reference omitted]"


def _evidence_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise FactoryEvolutionError("Evidence references must be an array")
    return [_evidence_ref(item) for item in value[:MAX_EVIDENCE_REFS]]


def _report_evidence_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise FactoryEvolutionError("Report evidence references must be an array")
    return [
        _exact_identifier(item, label="report evidence record ID")
        for item in value[:MAX_EVIDENCE_REFS]
    ]


def _report_hypotheses(
    report: Mapping[str, Any], *, report_id: str, source_root: str, report_sha256: str
) -> list[dict[str, Any]]:
    review = report.get("cognitive_review")
    if not isinstance(review, Mapping):
        raise FactoryEvolutionError("Report cognitive_review must be an object")
    if review.get("report_id") != report_id or review.get("source_root") != source_root:
        raise FactoryEvolutionError("Report cognitive review identity does not match report")
    sections = review.get("sections")
    if not isinstance(sections, Mapping):
        raise FactoryEvolutionError("Report cognitive_review.sections must be an object")

    hypotheses: list[dict[str, Any]] = []
    for section_name in sorted(str(key) for key in sections):
        items = sections.get(section_name)
        if not isinstance(items, list):
            raise FactoryEvolutionError(f"Report section {section_name!r} must be an array")
        for index, item in enumerate(items):
            if len(hypotheses) >= MAX_REPORT_HYPOTHESES:
                break
            if not isinstance(item, Mapping):
                raise FactoryEvolutionError("Report hypothesis must be an object")
            hypothesis = {
                "section": section_name,
                "position": index,
                "title": _bounded_text(item.get("title"), limit=MAX_REPORT_TEXT),
                "assessment": _bounded_text(
                    item.get("assessment"), limit=MAX_REPORT_TEXT
                ),
                "evidence_refs": _report_evidence_ids(item.get("evidence", [])),
                "source_report_id": report_id,
                "source_root": source_root,
                "source_report_sha256": report_sha256,
            }
            hypothesis["hypothesis_id"] = "hyp-" + digest(hypothesis)[:20]
            hypotheses.append(hypothesis)
    return hypotheses


def _load_report(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source, raw = _read_once(path)
    report = _json_object(raw, label=source.name)
    _reject_forbidden_source_keys(report, label=source.name)
    source_root = _exact_sha256(report.get("source_root"), label="report source_root")
    report_id = _exact_identifier(report.get("report_id"), label="report_id")
    if not report_id or not report_id.endswith(source_root[:12]):
        raise FactoryEvolutionError("Report ID is not bound to its source root")
    kind = _bounded_text(report.get("kind"), limit=120)
    if kind != "supervision-weekly-review-record":
        raise FactoryEvolutionError("Unsupported report kind")
    if not isinstance(report.get("schema_version"), int):
        raise FactoryEvolutionError("Report schema_version must be an integer")

    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping) or metrics.get("report_id") != report_id:
        raise FactoryEvolutionError("Report metrics identity does not match report")
    metrics_source = metrics.get("source")
    if not isinstance(metrics_source, Mapping) or metrics_source.get("source_root") != source_root:
        raise FactoryEvolutionError("Report metrics source root does not match report")

    coverage = report.get("coverage")
    if not isinstance(coverage, Mapping):
        raise FactoryEvolutionError("Report coverage must be an object")
    report_sha256 = hashlib.sha256(raw).hexdigest()
    review = report["cognitive_review"]
    assert isinstance(review, Mapping)
    reference = {
        "report_id": report_id,
        "source_root": source_root,
        "report_sha256": report_sha256,
        "kind": kind,
        "schema_version": report["schema_version"],
        "coverage": {
            "start": _bounded_text(coverage.get("start"), limit=64),
            "end": _bounded_text(coverage.get("end"), limit=64),
        },
        "review_summary": {
            "headline": _bounded_text(review.get("headline"), limit=MAX_REPORT_TEXT),
            "executive_assessment": _bounded_text(
                review.get("executive_assessment"), limit=MAX_REPORT_TEXT
            ),
            "overall_posture": _bounded_text(
                review.get("overall_posture"), limit=120
            ),
        },
    }
    return reference, _report_hypotheses(
        report,
        report_id=report_id,
        source_root=source_root,
        report_sha256=report_sha256,
    )


def _load_event_ledger(
    path: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    source, raw = _read_once(path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FactoryEvolutionError(f"{source.name} is not UTF-8 JSONL") from exc

    previous: str | None = None
    record_ids: set[str] = set()
    record_hashes: list[str] = []
    record_index: list[dict[str, str]] = []
    retained: list[dict[str, Any]] = []
    unknown_count = 0
    target_thread_ids: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        if len(record_hashes) >= MAX_EVENT_RECORDS:
            raise FactoryEvolutionError(
                f"{source.name} exceeds {MAX_EVENT_RECORDS} event records"
            )
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FactoryEvolutionError(
                f"{source.name} has malformed JSON at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise FactoryEvolutionError(
                f"{source.name} has a non-object at line {line_number}"
            )
        _reject_forbidden_source_keys(value, label=f"{source.name}:{line_number}")
        recorded_hash = _exact_sha256(
            value.get("record_sha256"), label="event record_sha256"
        )
        material = {key: item for key, item in value.items() if key != "record_sha256"}
        if material.get("previous_record_sha256") != previous:
            raise FactoryEvolutionError(
                f"{source.name} has a broken hash chain at line {line_number}"
            )
        if digest(material) != recorded_hash:
            raise FactoryEvolutionError(
                f"{source.name} has a stale record hash at line {line_number}"
            )
        record_id = _exact_identifier(value.get("record_id"), label="event record_id")
        if record_id in record_ids:
            raise FactoryEvolutionError(
                f"{source.name} has a duplicate record ID at line {line_number}"
            )
        record_ids.add(record_id)
        record_hashes.append(recorded_hash)
        record_index.append(
            {"record_id": record_id, "record_sha256": recorded_hash}
        )
        previous = recorded_hash
        target_thread_id = _exact_identifier(
            value.get("target_thread_id"), label="event target_thread_id"
        )
        if target_thread_id:
            target_thread_ids.add(target_thread_id)

        kind = _bounded_text(value.get("kind"), limit=80)
        if kind not in SUPPORTED_EVENT_KINDS:
            unknown_count += 1
            continue
        event = {
            "record_id": record_id,
            "record_sha256": recorded_hash,
            "kind": kind,
            "timestamp": _bounded_text(value.get("timestamp"), limit=64),
            "status": _bounded_text(value.get("status"), limit=80),
            "severity": _bounded_text(value.get("severity"), limit=40),
            "category": _bounded_text(value.get("category"), limit=100),
            "active_block": _bounded_text(value.get("active_block"), limit=100),
            "checkpoint": _bounded_text(value.get("checkpoint"), limit=100),
            "summary": _bounded_text(value.get("summary"), limit=MAX_EVENT_TEXT),
            "resolution": _bounded_text(
                value.get("resolution"), limit=MAX_EVENT_TEXT
            ),
            "evidence_refs": _evidence_refs(value.get("evidence", [])),
            "target_thread_id": target_thread_id,
        }
        retained.append(event)

    if not record_hashes:
        raise FactoryEvolutionError(f"{source.name} contains no event records")
    ledger_root = digest({"record_hashes": record_hashes})
    for event in retained:
        event["source_ledger_roots"] = [ledger_root]
    manifest = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "ledger_root": ledger_root,
        "record_count": len(record_hashes),
        "record_index": record_index,
        "first_record_sha256": record_hashes[0],
        "last_record_sha256": record_hashes[-1],
        "target_thread_ids": sorted(target_thread_ids),
        "unsupported_event_kinds": unknown_count,
    }
    return manifest, retained, unknown_count


def build_learning_packet(
    *, report_paths: Sequence[str | Path], event_paths: Sequence[str | Path]
) -> dict[str, Any]:
    """Build a deterministic, non-authoritative packet from explicit sources."""

    if not report_paths:
        raise FactoryEvolutionError("At least one explicit report path is required")
    if not event_paths:
        raise FactoryEvolutionError("At least one explicit event path is required")
    if len(report_paths) > MAX_EXPLICIT_REPORT_INPUTS:
        raise FactoryEvolutionError("Too many explicit report inputs")
    if len(event_paths) > MAX_EXPLICIT_EVENT_INPUTS:
        raise FactoryEvolutionError("Too many explicit event inputs")

    reports_by_root: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for path in report_paths:
        reference, hypotheses = _load_report(path)
        source_root = reference["source_root"]
        candidate = (reference, hypotheses)
        current = reports_by_root.get(source_root)
        if current is not None:
            if current[0]["report_sha256"] != reference["report_sha256"]:
                raise FactoryEvolutionError(
                    "One report source root has conflicting report content"
                )
            continue
        reports_by_root[source_root] = candidate
        if len(reports_by_root) > MAX_PACKET_REPORTS:
            raise FactoryEvolutionError("Learning packet has too many report roots")

    ledgers_by_root: dict[str, dict[str, Any]] = {}
    events_by_hash: dict[str, dict[str, Any]] = {}
    for path in event_paths:
        manifest, source_events, unknown_count = _load_event_ledger(path)
        ledger_root = manifest["ledger_root"]
        current_manifest = ledgers_by_root.get(ledger_root)
        if current_manifest is not None and current_manifest != manifest:
            raise FactoryEvolutionError("One event ledger root has conflicting manifests")
        ledgers_by_root[ledger_root] = manifest
        if len(ledgers_by_root) > MAX_PACKET_LEDGERS:
            raise FactoryEvolutionError("Learning packet has too many event ledger roots")
        if (
            sum(item["record_count"] for item in ledgers_by_root.values())
            > MAX_PACKET_CANONICAL_RECORDS
        ):
            raise FactoryEvolutionError(
                "Learning packet has too many canonical record index entries"
            )
        for event in source_events:
            record_hash = event["record_sha256"]
            current = events_by_hash.get(record_hash)
            if current is None:
                events_by_hash[record_hash] = event
                continue
            comparable = dict(current)
            comparable.pop("source_ledger_roots", None)
            incoming = dict(event)
            incoming.pop("source_ledger_roots", None)
            if comparable != incoming:
                raise FactoryEvolutionError("One event hash has conflicting retained data")
            current["source_ledger_roots"] = sorted(
                set(current["source_ledger_roots"] + event["source_ledger_roots"])
            )
        if len(events_by_hash) > MAX_PACKET_EVENTS:
            raise FactoryEvolutionError("Learning packet has too many retained events")

    reports = [reports_by_root[root][0] for root in sorted(reports_by_root)]
    hypotheses = [
        item
        for root in sorted(reports_by_root)
        for item in reports_by_root[root][1]
    ]
    if len(hypotheses) > MAX_PACKET_HYPOTHESES:
        raise FactoryEvolutionError("Learning packet has too many report hypotheses")
    events = sorted(
        events_by_hash.values(),
        key=lambda item: (
            item["timestamp"],
            item["record_id"],
            item["record_sha256"],
        ),
    )
    ledgers = [ledgers_by_root[root] for root in sorted(ledgers_by_root)]
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": PACKET_KIND,
        "authority": PACKET_AUTHORITY,
        "transformation": TRANSFORMATION,
        "sources": {"reports": reports, "event_ledgers": ledgers},
        "evidence": {
            "report_hypotheses": hypotheses,
            "events": events,
        },
        "coverage": {
            "report_roots": len(reports),
            "event_ledger_roots": len(ledgers),
            "canonical_event_records": sum(item["record_count"] for item in ledgers),
            "retained_event_records": len(events),
            "retained_report_hypotheses": len(hypotheses),
            "unsupported_event_kinds": sum(
                item["unsupported_event_kinds"] for item in ledgers
            ),
        },
    }
    packet_root = digest(material)
    packet = dict(material)
    packet["packet_id"] = "learning-" + packet_root[:20]
    packet["packet_root"] = packet_root
    return verify_learning_packet(packet)


def _exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    if set(value) != expected:
        raise FactoryEvolutionError(f"{label} has unexpected or missing fields")


def _bounded_packet_text(value: Any, *, label: str, limit: int) -> str:
    if not isinstance(value, str) or _bounded_text(value, limit=limit) != value:
        raise FactoryEvolutionError(f"{label} is not normalized and bounded")
    return value


def _bounded_integer(value: Any, *, label: str, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FactoryEvolutionError(f"{label} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise FactoryEvolutionError(f"{label} exceeds its aggregate bound")
    return value


def _string_array(
    value: Any, *, label: str, limit: int, item_limit: int
) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise FactoryEvolutionError(f"{label} is not a bounded array")
    result = [
        _bounded_packet_text(item, label=f"{label} item", limit=item_limit)
        for item in value
    ]
    if len(result) != len(set(result)):
        raise FactoryEvolutionError(f"{label} contains duplicate entries")
    return result


def verify_learning_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Fully verify packet schema, bounds, provenance, ordering, and identity."""

    if not isinstance(packet, Mapping):
        raise FactoryEvolutionError("Learning packet must be an object")
    _reject_forbidden_source_keys(packet, label="learning packet")
    value = dict(packet)
    _exact_keys(
        value,
        {
            "schema_version",
            "kind",
            "authority",
            "transformation",
            "sources",
            "evidence",
            "coverage",
            "packet_id",
            "packet_root",
        },
        label="Learning packet",
    )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise FactoryEvolutionError("Learning packet schema_version is unsupported")
    if value.get("kind") != PACKET_KIND or value.get("authority") != PACKET_AUTHORITY:
        raise FactoryEvolutionError("Learning packet kind or authority is invalid")
    if value.get("transformation") != TRANSFORMATION:
        raise FactoryEvolutionError("Learning packet transformation is invalid")

    sources = value.get("sources")
    evidence = value.get("evidence")
    coverage = value.get("coverage")
    if not isinstance(sources, Mapping) or not isinstance(evidence, Mapping):
        raise FactoryEvolutionError("Learning packet sources and evidence must be objects")
    if not isinstance(coverage, Mapping):
        raise FactoryEvolutionError("Learning packet coverage must be an object")
    _exact_keys(sources, {"reports", "event_ledgers"}, label="Packet sources")
    _exact_keys(evidence, {"report_hypotheses", "events"}, label="Packet evidence")
    _exact_keys(
        coverage,
        {
            "report_roots",
            "event_ledger_roots",
            "canonical_event_records",
            "retained_event_records",
            "retained_report_hypotheses",
            "unsupported_event_kinds",
        },
        label="Packet coverage",
    )

    reports = sources.get("reports")
    ledgers = sources.get("event_ledgers")
    events = evidence.get("events")
    hypotheses = evidence.get("report_hypotheses")
    if not isinstance(reports, list) or not reports or len(reports) > MAX_PACKET_REPORTS:
        raise FactoryEvolutionError("Packet reports are not a bounded array")
    if not isinstance(ledgers, list) or not ledgers or len(ledgers) > MAX_PACKET_LEDGERS:
        raise FactoryEvolutionError("Packet event ledgers are not a bounded array")
    if not isinstance(events, list) or len(events) > MAX_PACKET_EVENTS:
        raise FactoryEvolutionError("Packet events are not a bounded array")
    if (
        not isinstance(hypotheses, list)
        or not hypotheses
        or len(hypotheses) > MAX_PACKET_HYPOTHESES
    ):
        raise FactoryEvolutionError("Packet hypotheses are not a bounded array")

    report_keys: set[tuple[str, str, str]] = set()
    report_roots: list[str] = []
    for report in reports:
        if not isinstance(report, Mapping):
            raise FactoryEvolutionError("Packet report source must be an object")
        _exact_keys(
            report,
            {
                "report_id",
                "source_root",
                "report_sha256",
                "kind",
                "schema_version",
                "coverage",
                "review_summary",
            },
            label="Packet report source",
        )
        report_id = _exact_identifier(report.get("report_id"), label="packet report_id")
        source_root = _exact_sha256(report.get("source_root"), label="packet report source_root")
        report_sha256 = _exact_sha256(
            report.get("report_sha256"), label="packet report SHA-256"
        )
        if not report_id.endswith(source_root[:12]):
            raise FactoryEvolutionError("Packet report ID is not bound to its source root")
        if report.get("kind") != "supervision-weekly-review-record":
            raise FactoryEvolutionError("Packet report kind is unsupported")
        if report.get("schema_version") != 1:
            raise FactoryEvolutionError("Packet report schema_version is unsupported")
        report_coverage = report.get("coverage")
        summary = report.get("review_summary")
        if not isinstance(report_coverage, Mapping) or not isinstance(summary, Mapping):
            raise FactoryEvolutionError("Packet report coverage and summary must be objects")
        _exact_keys(report_coverage, {"start", "end"}, label="Packet report coverage")
        _exact_keys(
            summary,
            {"headline", "executive_assessment", "overall_posture"},
            label="Packet report review summary",
        )
        for key in ("start", "end"):
            _bounded_packet_text(
                report_coverage.get(key), label=f"report coverage {key}", limit=64
            )
        for key in ("headline", "executive_assessment"):
            _bounded_packet_text(
                summary.get(key), label=f"report summary {key}", limit=MAX_REPORT_TEXT
            )
        _bounded_packet_text(
            summary.get("overall_posture"),
            label="report summary overall_posture",
            limit=120,
        )
        key = (report_id, source_root, report_sha256)
        if key in report_keys or source_root in report_roots:
            raise FactoryEvolutionError("Packet report roots are not unique")
        report_keys.add(key)
        report_roots.append(source_root)
    if report_roots != sorted(report_roots):
        raise FactoryEvolutionError("Packet reports are not deterministically ordered")

    ledger_roots: list[str] = []
    canonical_record_ids: set[str] = set()
    canonical_record_hashes: dict[str, str] = {}
    ledger_record_keys: dict[str, set[tuple[str, str]]] = {}
    unsupported_total = 0
    canonical_total = 0
    for ledger in ledgers:
        if not isinstance(ledger, Mapping):
            raise FactoryEvolutionError("Packet event ledger must be an object")
        _exact_keys(
            ledger,
            {
                "source_sha256",
                "ledger_root",
                "record_count",
                "record_index",
                "first_record_sha256",
                "last_record_sha256",
                "target_thread_ids",
                "unsupported_event_kinds",
            },
            label="Packet event ledger",
        )
        _exact_sha256(ledger.get("source_sha256"), label="ledger source SHA-256")
        ledger_root = _exact_sha256(ledger.get("ledger_root"), label="ledger root")
        first_hash = _exact_sha256(
            ledger.get("first_record_sha256"), label="ledger first record SHA-256"
        )
        last_hash = _exact_sha256(
            ledger.get("last_record_sha256"), label="ledger last record SHA-256"
        )
        record_count = _bounded_integer(
            ledger.get("record_count"), label="ledger record count", maximum=MAX_EVENT_RECORDS
        )
        unsupported = _bounded_integer(
            ledger.get("unsupported_event_kinds"),
            label="ledger unsupported event count",
            maximum=record_count,
        )
        record_index = ledger.get("record_index")
        if not isinstance(record_index, list) or len(record_index) != record_count or not record_index:
            raise FactoryEvolutionError("Ledger record index does not match its count")
        record_hashes: list[str] = []
        ledger_ids: set[str] = set()
        for record in record_index:
            if not isinstance(record, Mapping):
                raise FactoryEvolutionError("Ledger record index entry must be an object")
            _exact_keys(
                record,
                {"record_id", "record_sha256"},
                label="Ledger record index entry",
            )
            record_id = _exact_identifier(
                record.get("record_id"), label="ledger record_id"
            )
            record_hash = _exact_sha256(
                record.get("record_sha256"), label="ledger record SHA-256"
            )
            if record_id in ledger_ids:
                raise FactoryEvolutionError("Ledger record index repeats a record ID")
            known_hash = canonical_record_hashes.get(record_id)
            if known_hash is not None and known_hash != record_hash:
                raise FactoryEvolutionError("One canonical record ID has conflicting hashes")
            ledger_ids.add(record_id)
            canonical_record_ids.add(record_id)
            canonical_record_hashes[record_id] = record_hash
            record_hashes.append(record_hash)
        if first_hash != record_hashes[0] or last_hash != record_hashes[-1]:
            raise FactoryEvolutionError("Ledger first or last record hash is stale")
        if ledger_root != digest({"record_hashes": record_hashes}):
            raise FactoryEvolutionError("Ledger root is stale")
        target_ids = ledger.get("target_thread_ids")
        if not isinstance(target_ids, list) or len(target_ids) > 32:
            raise FactoryEvolutionError("Ledger target thread IDs are not bounded")
        normalized_targets = [
            _exact_identifier(item, label="ledger target thread ID") for item in target_ids
        ]
        if normalized_targets != sorted(set(normalized_targets)):
            raise FactoryEvolutionError("Ledger target thread IDs are not sorted and unique")
        if ledger_root in ledger_roots:
            raise FactoryEvolutionError("Packet repeats an event ledger root")
        ledger_roots.append(ledger_root)
        ledger_record_keys[ledger_root] = {
            (str(item["record_id"]), str(item["record_sha256"]))
            for item in record_index
        }
        canonical_total += record_count
        if canonical_total > MAX_PACKET_CANONICAL_RECORDS:
            raise FactoryEvolutionError(
                "Packet canonical record indexes exceed their aggregate bound"
            )
        unsupported_total += unsupported
    if ledger_roots != sorted(ledger_roots):
        raise FactoryEvolutionError("Packet ledgers are not deterministically ordered")
    ledger_root_set = set(ledger_roots)

    event_keys: set[tuple[str, str]] = set()
    event_order: list[tuple[str, str, str]] = []
    for event in events:
        if not isinstance(event, Mapping):
            raise FactoryEvolutionError("Packet event must be an object")
        _exact_keys(
            event,
            {
                "record_id",
                "record_sha256",
                "kind",
                "timestamp",
                "status",
                "severity",
                "category",
                "active_block",
                "checkpoint",
                "summary",
                "resolution",
                "evidence_refs",
                "target_thread_id",
                "source_ledger_roots",
            },
            label="Packet event",
        )
        record_id = _exact_identifier(event.get("record_id"), label="packet event record_id")
        record_hash = _exact_sha256(
            event.get("record_sha256"), label="packet event record SHA-256"
        )
        if canonical_record_hashes.get(record_id) != record_hash:
            raise FactoryEvolutionError("Packet event does not resolve to a canonical record")
        if event.get("kind") not in SUPPORTED_EVENT_KINDS:
            raise FactoryEvolutionError("Packet event kind is unsupported")
        for key, limit in (
            ("timestamp", 64),
            ("status", 80),
            ("severity", 40),
            ("category", 100),
            ("active_block", 100),
            ("checkpoint", 100),
            ("summary", MAX_EVENT_TEXT),
            ("resolution", MAX_EVENT_TEXT),
        ):
            _bounded_packet_text(event.get(key), label=f"packet event {key}", limit=limit)
        _exact_identifier(
            event.get("target_thread_id"), label="packet event target_thread_id"
        )
        _string_array(
            event.get("evidence_refs"),
            label="packet event evidence refs",
            limit=MAX_EVIDENCE_REFS,
            item_limit=MAX_REFERENCE_TEXT,
        )
        roots = event.get("source_ledger_roots")
        if not isinstance(roots, list) or not roots:
            raise FactoryEvolutionError("Packet event has no source ledger roots")
        validated_roots = [
            _exact_sha256(item, label="packet event ledger root") for item in roots
        ]
        if validated_roots != sorted(set(validated_roots)) or not set(validated_roots) <= ledger_root_set:
            raise FactoryEvolutionError("Packet event ledger roots are invalid")
        event_key = (record_id, record_hash)
        if any(event_key not in ledger_record_keys[root] for root in validated_roots):
            raise FactoryEvolutionError(
                "Packet event does not belong to every claimed source ledger"
            )
        if event_key in event_keys:
            raise FactoryEvolutionError("Packet repeats an event identity")
        event_keys.add(event_key)
        event_order.append((event["timestamp"], record_id, record_hash))
    if event_order != sorted(event_order):
        raise FactoryEvolutionError("Packet events are not deterministically ordered")

    hypothesis_ids: set[str] = set()
    hypothesis_order: list[tuple[str, str, int, str]] = []
    section_positions: dict[tuple[str, str], list[int]] = {}
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, Mapping):
            raise FactoryEvolutionError("Packet hypothesis must be an object")
        _exact_keys(
            hypothesis,
            {
                "section",
                "position",
                "title",
                "assessment",
                "evidence_refs",
                "source_report_id",
                "source_root",
                "source_report_sha256",
                "hypothesis_id",
            },
            label="Packet hypothesis",
        )
        key = (
            _exact_identifier(
                hypothesis.get("source_report_id"), label="hypothesis report_id"
            ),
            _exact_sha256(hypothesis.get("source_root"), label="hypothesis source root"),
            _exact_sha256(
                hypothesis.get("source_report_sha256"), label="hypothesis report SHA-256"
            ),
        )
        if key not in report_keys:
            raise FactoryEvolutionError("Packet hypothesis does not resolve to a report")
        section = _bounded_packet_text(
            hypothesis.get("section"), label="hypothesis section", limit=160
        )
        position = _bounded_integer(
            hypothesis.get("position"), label="hypothesis position", maximum=10_000
        )
        _bounded_packet_text(
            hypothesis.get("title"), label="hypothesis title", limit=MAX_REPORT_TEXT
        )
        _bounded_packet_text(
            hypothesis.get("assessment"),
            label="hypothesis assessment",
            limit=MAX_REPORT_TEXT,
        )
        evidence_ids = hypothesis.get("evidence_refs")
        if not isinstance(evidence_ids, list) or len(evidence_ids) > MAX_EVIDENCE_REFS:
            raise FactoryEvolutionError("Hypothesis evidence references are not bounded")
        validated_evidence = [
            _exact_identifier(item, label="hypothesis evidence record ID")
            for item in evidence_ids
        ]
        if len(validated_evidence) != len(set(validated_evidence)):
            raise FactoryEvolutionError("Hypothesis evidence references contain duplicates")
        if not set(validated_evidence) <= canonical_record_ids:
            raise FactoryEvolutionError(
                "Hypothesis evidence does not resolve to a canonical event"
            )
        hypothesis_material = dict(hypothesis)
        hypothesis_id = _exact_identifier(
            hypothesis_material.pop("hypothesis_id"), label="hypothesis_id"
        )
        expected_id = "hyp-" + digest(hypothesis_material)[:20]
        if hypothesis_id != expected_id or hypothesis_id in hypothesis_ids:
            raise FactoryEvolutionError("Hypothesis identity is stale or duplicated")
        hypothesis_ids.add(hypothesis_id)
        hypothesis_order.append((key[1], section, position, hypothesis_id))
        section_positions.setdefault((key[1], section), []).append(position)

    if hypothesis_order != sorted(hypothesis_order):
        raise FactoryEvolutionError("Packet hypotheses are not deterministically ordered")
    for positions in section_positions.values():
        if positions != list(range(len(positions))):
            raise FactoryEvolutionError("Packet hypothesis section positions are incoherent")

    expected_coverage = {
        "report_roots": len(reports),
        "event_ledger_roots": len(ledgers),
        "canonical_event_records": canonical_total,
        "retained_event_records": len(events),
        "retained_report_hypotheses": len(hypotheses),
        "unsupported_event_kinds": unsupported_total,
    }
    for key, expected in expected_coverage.items():
        actual = _bounded_integer(coverage.get(key), label=f"coverage {key}")
        if actual != expected:
            raise FactoryEvolutionError(f"Packet coverage {key} is stale")

    recorded_root = _exact_sha256(value.pop("packet_root", None), label="packet_root")
    packet_id = _exact_identifier(value.pop("packet_id", None), label="packet_id")
    expected_root = digest(value)
    if recorded_root != expected_root or packet_id != "learning-" + expected_root[:20]:
        raise FactoryEvolutionError("Learning packet identity is stale")
    return dict(packet)


REVIEW_KIND = "software-factory-evolution-review"
EVALUATION_KIND = "software-factory-candidate-evaluation"
MACHINE_REPORT_KIND = "software-factory-evolution-machine-report"
MANIFEST_KIND = "software-factory-evolution-manifest"
MAX_SEMANTIC_RECORDS = 64
MAX_SEMANTIC_TEXT = 600
MAX_SEMANTIC_LIST = 16
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_ARTIFACT_BYTES = 4 * 1024 * 1024
CANDIDATE_TYPES = frozenset(
    {
        "detector",
        "correction",
        "exculpator",
        "skill-method",
        "tracker-method",
        "supervision",
        "execution",
        "evaluation",
        "resource-policy",
        "architecture",
        "removal",
        "experiment",
    }
)
SELECTION_DIMENSIONS = (
    "effect",
    "recurrence",
    "reach",
    "compounding_value",
    "reliability",
    "product_gain",
    "evidence_strength",
    "cost",
    "regression_risk",
    "complexity",
    "reversibility",
    "time_to_evidence",
)
DIMENSION_RATINGS = frozenset({"low", "medium", "high", "unknown"})
COUNTEREXAMPLE_POSTURES = frozenset(
    {"observed", "searched-none-found", "unknown-limits-applicability"}
)
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
RESULT_EVIDENCE_CLASSES = frozenset({"observed", "shadow", "synthetic"})
RESULT_OUTCOMES = frozenset({"pass", "fail", "mixed"})
DISPOSITIONS = frozenset({"promote", "advisory", "revise", "reject"})
RESULT_EVIDENCE_KIND = "software-factory-experiment-result-evidence"


def _semantic_text(value: Any, *, label: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise FactoryEvolutionError(f"{label} must be text")
    normalized = _bounded_text(value, limit=MAX_SEMANTIC_TEXT)
    if normalized != value or (not value and not allow_empty):
        raise FactoryEvolutionError(f"{label} must be nonempty, normalized, bounded text")
    return value


def _semantic_strings(
    value: Any, *, label: str, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_SEMANTIC_LIST:
        raise FactoryEvolutionError(f"{label} must be a bounded array")
    result = [_semantic_text(item, label=f"{label} item") for item in value]
    if not result and not allow_empty:
        raise FactoryEvolutionError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise FactoryEvolutionError(f"{label} contains duplicates")
    return sorted(result)


def _semantic_ids(
    value: Any,
    *,
    label: str,
    allowed: set[str] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_SEMANTIC_LIST:
        raise FactoryEvolutionError(f"{label} must be a bounded ID array")
    result = [_exact_identifier(item, label=f"{label} item") for item in value]
    if not result and not allow_empty:
        raise FactoryEvolutionError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise FactoryEvolutionError(f"{label} contains duplicate IDs")
    if allowed is not None and not set(result) <= allowed:
        raise FactoryEvolutionError(f"{label} contains a dangling reference")
    return sorted(result)


def _packet_reference_sets(packet: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    verified = verify_learning_packet(packet)
    event_ids = {
        str(item["record_id"])
        for ledger in verified["sources"]["event_ledgers"]
        for item in ledger["record_index"]
    }
    hypothesis_ids = {
        str(item["hypothesis_id"])
        for item in verified["evidence"]["report_hypotheses"]
    }
    return event_ids, hypothesis_ids


def _normalize_observations(value: Any, *, event_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_SEMANTIC_RECORDS:
        raise FactoryEvolutionError("Review observations must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError("Review observation must be an object")
        _exact_keys(
            item,
            {"observation_id", "summary", "valence", "event_ids"},
            label="Review observation",
        )
        observation_id = _exact_identifier(
            item.get("observation_id"), label="observation_id"
        )
        if observation_id in seen:
            raise FactoryEvolutionError("Review repeats an observation ID")
        seen.add(observation_id)
        valence = str(item.get("valence"))
        if valence not in {"productive", "harmful", "exception", "mixed"}:
            raise FactoryEvolutionError("Observation valence is unsupported")
        result.append(
            {
                "observation_id": observation_id,
                "summary": _semantic_text(item.get("summary"), label="observation summary"),
                "valence": valence,
                "event_ids": _semantic_ids(
                    item.get("event_ids"),
                    label="observation event IDs",
                    allowed=event_ids,
                ),
            }
        )
    return sorted(result, key=lambda item: item["observation_id"])


def _normalize_lessons(
    value: Any,
    *,
    observation_events: Mapping[str, set[str]],
    event_ids: set[str],
    hypothesis_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_SEMANTIC_RECORDS:
        raise FactoryEvolutionError("Review lessons must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected = {
        "lesson_id",
        "statement",
        "observation_ids",
        "supporting_case_ids",
        "report_hypothesis_ids",
        "counterexample_case_ids",
        "counterexample_posture",
        "counterexample_search",
        "goals_advanced",
        "goals_threatened",
        "causal_hypothesis",
        "confidence",
        "applicability",
        "unresolved_questions",
    }
    for item in value:
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError("Review lesson must be an object")
        _exact_keys(item, expected, label="Review lesson")
        lesson_id = _exact_identifier(item.get("lesson_id"), label="lesson_id")
        if lesson_id in seen:
            raise FactoryEvolutionError("Review repeats a lesson ID")
        seen.add(lesson_id)
        linked_observations = _semantic_ids(
            item.get("observation_ids"),
            label="lesson observation IDs",
            allowed=set(observation_events),
        )
        supporting = _semantic_ids(
            item.get("supporting_case_ids"),
            label="lesson supporting cases",
            allowed=event_ids,
        )
        linked_events = {
            event_id
            for observation_id in linked_observations
            for event_id in observation_events[observation_id]
        }
        if not set(supporting) <= linked_events:
            raise FactoryEvolutionError(
                "Lesson supporting cases contradict its linked observations"
            )
        counterexamples = _semantic_ids(
            item.get("counterexample_case_ids"),
            label="lesson counterexample cases",
            allowed=event_ids,
            allow_empty=True,
        )
        posture = str(item.get("counterexample_posture"))
        if posture not in COUNTEREXAMPLE_POSTURES:
            raise FactoryEvolutionError("Lesson counterexample posture is missing or unsupported")
        if posture == "observed" and not counterexamples:
            raise FactoryEvolutionError("Observed counterexample posture requires an exact case")
        if posture != "observed" and counterexamples:
            raise FactoryEvolutionError(
                "Non-observed counterexample posture cannot cite observed cases"
            )
        confidence = str(item.get("confidence"))
        if confidence not in CONFIDENCE_LEVELS:
            raise FactoryEvolutionError("Lesson confidence is unsupported")
        result.append(
            {
                "lesson_id": lesson_id,
                "statement": _semantic_text(item.get("statement"), label="lesson statement"),
                "observation_ids": linked_observations,
                "supporting_case_ids": supporting,
                "report_hypothesis_ids": _semantic_ids(
                    item.get("report_hypothesis_ids"),
                    label="lesson report hypothesis IDs",
                    allowed=hypothesis_ids,
                    allow_empty=True,
                ),
                "counterexample_case_ids": counterexamples,
                "counterexample_posture": posture,
                "counterexample_search": _semantic_text(
                    item.get("counterexample_search"), label="lesson counterexample search"
                ),
                "goals_advanced": _semantic_strings(
                    item.get("goals_advanced"), label="lesson goals advanced", allow_empty=True
                ),
                "goals_threatened": _semantic_strings(
                    item.get("goals_threatened"),
                    label="lesson goals threatened",
                    allow_empty=True,
                ),
                "causal_hypothesis": _semantic_text(
                    item.get("causal_hypothesis"), label="lesson causal hypothesis"
                ),
                "confidence": confidence,
                "applicability": _semantic_text(
                    item.get("applicability"), label="lesson applicability"
                ),
                "unresolved_questions": _semantic_strings(
                    item.get("unresolved_questions"),
                    label="lesson unresolved questions",
                    allow_empty=True,
                ),
            }
        )
    return sorted(result, key=lambda item: item["lesson_id"])


def _normalize_meta_patterns(
    value: Any, *, lesson_ids: set[str], event_ids: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_SEMANTIC_RECORDS:
        raise FactoryEvolutionError("Review meta-patterns must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError("Review meta-pattern must be an object")
        _exact_keys(
            item,
            {
                "meta_pattern_id",
                "statement",
                "lesson_ids",
                "supporting_case_ids",
                "counterexample_lesson_ids",
                "applicability",
                "uncertainty",
            },
            label="Review meta-pattern",
        )
        meta_id = _exact_identifier(item.get("meta_pattern_id"), label="meta_pattern_id")
        if meta_id in seen:
            raise FactoryEvolutionError("Review repeats a meta-pattern ID")
        seen.add(meta_id)
        linked_lessons = _semantic_ids(
            item.get("lesson_ids"), label="meta-pattern lesson IDs", allowed=lesson_ids
        )
        if len(linked_lessons) < 2:
            raise FactoryEvolutionError("Meta-pattern must relate at least two lessons")
        result.append(
            {
                "meta_pattern_id": meta_id,
                "statement": _semantic_text(
                    item.get("statement"), label="meta-pattern statement"
                ),
                "lesson_ids": linked_lessons,
                "supporting_case_ids": _semantic_ids(
                    item.get("supporting_case_ids"),
                    label="meta-pattern supporting cases",
                    allowed=event_ids,
                ),
                "counterexample_lesson_ids": _semantic_ids(
                    item.get("counterexample_lesson_ids"),
                    label="meta-pattern counterexample lessons",
                    allowed=lesson_ids,
                    allow_empty=True,
                ),
                "applicability": _semantic_text(
                    item.get("applicability"), label="meta-pattern applicability"
                ),
                "uncertainty": _semantic_text(
                    item.get("uncertainty"), label="meta-pattern uncertainty"
                ),
            }
        )
    return sorted(result, key=lambda item: item["meta_pattern_id"])


def _normalize_dimensions(value: Any, *, event_ids: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FactoryEvolutionError("Candidate selection dimensions must be an object")
    _exact_keys(value, set(SELECTION_DIMENSIONS), label="Candidate selection dimensions")
    result: dict[str, Any] = {}
    for name in SELECTION_DIMENSIONS:
        item = value.get(name)
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError(f"Candidate dimension {name} must be an object")
        _exact_keys(item, {"rating", "rationale", "evidence_ids"}, label=f"Dimension {name}")
        rating = str(item.get("rating"))
        if rating not in DIMENSION_RATINGS:
            raise FactoryEvolutionError(f"Candidate dimension {name} rating is unsupported")
        result[name] = {
            "rating": rating,
            "rationale": _semantic_text(
                item.get("rationale"), label=f"candidate dimension {name} rationale"
            ),
            "evidence_ids": _semantic_ids(
                item.get("evidence_ids"),
                label=f"candidate dimension {name} evidence IDs",
                allowed=event_ids,
                allow_empty=rating == "unknown",
            ),
        }
    return result


def _normalize_candidates(
    value: Any, *, meta_ids: set[str], event_ids: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > MAX_SEMANTIC_RECORDS:
        raise FactoryEvolutionError("Review candidates must be a nonempty bounded array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected = {
        "candidate_id",
        "candidate_type",
        "capability_gap",
        "effect",
        "meta_pattern_ids",
        "evidence_ids",
        "protected_capabilities",
        "applicability",
        "tradeoffs",
        "uncertainty",
        "implementation_owner",
        "evaluation_owner",
        "smaller_change_insufficient",
        "proportionality",
        "selection_dimensions",
        "counterexample_case_ids",
        "counterexample_posture",
        "counterexample_search",
    }
    for item in value:
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError("Review candidate must be an object")
        _exact_keys(item, expected, label="Review candidate")
        candidate_id = _exact_identifier(item.get("candidate_id"), label="candidate_id")
        if candidate_id in seen:
            raise FactoryEvolutionError("Review repeats a candidate ID")
        seen.add(candidate_id)
        candidate_type = str(item.get("candidate_type"))
        if candidate_type not in CANDIDATE_TYPES:
            raise FactoryEvolutionError("Candidate type is unsupported")
        implementation_owner = _exact_identifier(
            item.get("implementation_owner"), label="candidate implementation owner"
        )
        evaluation_owner = _exact_identifier(
            item.get("evaluation_owner"), label="candidate evaluation owner"
        )
        if implementation_owner == evaluation_owner:
            raise FactoryEvolutionError("Candidate implementation and evaluation owners collapse")
        counterexamples = _semantic_ids(
            item.get("counterexample_case_ids"),
            label="candidate counterexample cases",
            allowed=event_ids,
            allow_empty=True,
        )
        posture = str(item.get("counterexample_posture"))
        if posture not in COUNTEREXAMPLE_POSTURES:
            raise FactoryEvolutionError(
                "Candidate counterexample posture is missing or unsupported"
            )
        if posture == "observed" and not counterexamples:
            raise FactoryEvolutionError(
                "Observed candidate counterexample posture requires an exact case"
            )
        if posture != "observed" and counterexamples:
            raise FactoryEvolutionError(
                "Non-observed candidate counterexample posture cannot cite observed cases"
            )
        result.append(
            {
                "candidate_id": candidate_id,
                "candidate_type": candidate_type,
                "capability_gap": _semantic_text(
                    item.get("capability_gap"), label="candidate capability gap"
                ),
                "effect": _semantic_text(item.get("effect"), label="candidate effect"),
                "meta_pattern_ids": _semantic_ids(
                    item.get("meta_pattern_ids"),
                    label="candidate meta-pattern IDs",
                    allowed=meta_ids,
                ),
                "evidence_ids": _semantic_ids(
                    item.get("evidence_ids"),
                    label="candidate evidence IDs",
                    allowed=event_ids,
                ),
                "protected_capabilities": _semantic_strings(
                    item.get("protected_capabilities"),
                    label="candidate protected capabilities",
                ),
                "applicability": _semantic_text(
                    item.get("applicability"), label="candidate applicability"
                ),
                "tradeoffs": _semantic_strings(
                    item.get("tradeoffs"), label="candidate tradeoffs"
                ),
                "uncertainty": _semantic_text(
                    item.get("uncertainty"), label="candidate uncertainty"
                ),
                "counterexample_case_ids": counterexamples,
                "counterexample_posture": posture,
                "counterexample_search": _semantic_text(
                    item.get("counterexample_search"),
                    label="candidate counterexample search",
                ),
                "implementation_owner": implementation_owner,
                "evaluation_owner": evaluation_owner,
                "smaller_change_insufficient": _semantic_text(
                    item.get("smaller_change_insufficient"),
                    label="candidate smaller-change rationale",
                ),
                "proportionality": _semantic_text(
                    item.get("proportionality"), label="candidate proportionality"
                ),
                "selection_dimensions": _normalize_dimensions(
                    item.get("selection_dimensions"), event_ids=event_ids
                ),
            }
        )
    return sorted(result, key=lambda item: item["candidate_id"])


def _exact_revision(value: Any, *, label: str) -> str:
    text = str(value)
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", text):
        raise FactoryEvolutionError(f"{label} must be an exact 40- or 64-hex revision")
    return text


def _normalize_experiment(
    value: Any, *, selected: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FactoryEvolutionError("Selected candidate experiment must be an object")
    _exact_keys(
        value,
        {
            "experiment_id",
            "candidate_id",
            "proposer_id",
            "implementer_id",
            "evaluator_id",
            "baseline_revision",
            "candidate_revision",
            "positive_case_ids",
            "exception_case_ids",
            "expected_effects",
            "resource_bounds",
            "rollback_condition",
            "success_measures",
            "regression_measures",
            "evidence_capture",
            "stop_condition",
            "comparison_mode",
            "minimum_expected_delta",
            "non_inferiority_justification",
        },
        label="Selected candidate experiment",
    )
    candidate_id = _exact_identifier(value.get("candidate_id"), label="experiment candidate_id")
    if candidate_id != selected["candidate_id"]:
        raise FactoryEvolutionError("Experiment does not target the selected candidate")
    proposer = _exact_identifier(value.get("proposer_id"), label="experiment proposer_id")
    implementer = _exact_identifier(
        value.get("implementer_id"), label="experiment implementer_id"
    )
    evaluator = _exact_identifier(value.get("evaluator_id"), label="experiment evaluator_id")
    if len({proposer, implementer, evaluator}) != 3:
        raise FactoryEvolutionError("Proposer, implementer, and evaluator identities collapse")
    if implementer != selected["implementation_owner"] or evaluator != selected["evaluation_owner"]:
        raise FactoryEvolutionError("Experiment owners do not match the selected candidate")
    baseline = _exact_revision(value.get("baseline_revision"), label="baseline revision")
    candidate = _exact_revision(value.get("candidate_revision"), label="candidate revision")
    if baseline == candidate:
        raise FactoryEvolutionError("Baseline and candidate revisions must differ")
    positive_cases = _semantic_ids(
        value.get("positive_case_ids"), label="experiment positive cases"
    )
    exception_cases = _semantic_ids(
        value.get("exception_case_ids"), label="experiment exception cases"
    )
    if set(positive_cases) & set(exception_cases):
        raise FactoryEvolutionError("Experiment positive and exception cases overlap")
    comparison_mode = str(value.get("comparison_mode"))
    if comparison_mode not in {"improvement", "non-inferiority"}:
        raise FactoryEvolutionError("Experiment comparison mode is unsupported")
    non_inferiority = _semantic_text(
        value.get("non_inferiority_justification"),
        label="experiment non-inferiority justification",
        allow_empty=True,
    )
    if comparison_mode == "non-inferiority" and not non_inferiority:
        raise FactoryEvolutionError(
            "Non-inferiority experiments require an explicit justification"
        )
    if comparison_mode == "improvement" and non_inferiority:
        raise FactoryEvolutionError(
            "Improvement experiments cannot smuggle in a non-inferiority justification"
        )
    return {
        "experiment_id": _exact_identifier(
            value.get("experiment_id"), label="experiment_id"
        ),
        "candidate_id": candidate_id,
        "proposer_id": proposer,
        "implementer_id": implementer,
        "evaluator_id": evaluator,
        "baseline_revision": baseline,
        "candidate_revision": candidate,
        "positive_case_ids": positive_cases,
        "exception_case_ids": exception_cases,
        "expected_effects": _semantic_strings(
            value.get("expected_effects"), label="experiment expected effects"
        ),
        "resource_bounds": _semantic_strings(
            value.get("resource_bounds"), label="experiment resource bounds"
        ),
        "rollback_condition": _semantic_text(
            value.get("rollback_condition"), label="experiment rollback condition"
        ),
        "success_measures": _semantic_strings(
            value.get("success_measures"), label="experiment success measures"
        ),
        "regression_measures": _semantic_strings(
            value.get("regression_measures"), label="experiment regression measures"
        ),
        "evidence_capture": _semantic_text(
            value.get("evidence_capture"), label="experiment evidence capture"
        ),
        "stop_condition": _semantic_text(
            value.get("stop_condition"), label="experiment stop condition"
        ),
        "comparison_mode": comparison_mode,
        "minimum_expected_delta": _semantic_text(
            value.get("minimum_expected_delta"),
            label="experiment minimum expected delta",
        ),
        "non_inferiority_justification": non_inferiority,
    }


def _normalize_review_material(
    packet: Mapping[str, Any], submission: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(submission, Mapping):
        raise FactoryEvolutionError("Evolution review submission must be an object")
    _reject_forbidden_source_keys(submission, label="evolution review")
    _exact_keys(
        submission,
        {
            "schema_version",
            "kind",
            "packet_id",
            "packet_root",
            "reviewer_id",
            "observations",
            "lessons",
            "meta_patterns",
            "candidates",
            "selection",
            "experiment",
        },
        label="Evolution review submission",
    )
    if submission.get("schema_version") != SCHEMA_VERSION or submission.get("kind") != REVIEW_KIND:
        raise FactoryEvolutionError("Evolution review kind or schema is unsupported")
    if submission.get("packet_id") != packet.get("packet_id") or submission.get(
        "packet_root"
    ) != packet.get("packet_root"):
        raise FactoryEvolutionError("Evolution review is not bound to the packet")
    event_ids, hypothesis_ids = _packet_reference_sets(packet)
    observations = _normalize_observations(submission.get("observations"), event_ids=event_ids)
    observation_events = {
        item["observation_id"]: set(item["event_ids"]) for item in observations
    }
    lessons = _normalize_lessons(
        submission.get("lessons"),
        observation_events=observation_events,
        event_ids=event_ids,
        hypothesis_ids=hypothesis_ids,
    )
    lesson_ids = {item["lesson_id"] for item in lessons}
    meta_patterns = _normalize_meta_patterns(
        submission.get("meta_patterns"), lesson_ids=lesson_ids, event_ids=event_ids
    )
    meta_ids = {item["meta_pattern_id"] for item in meta_patterns}
    candidates = _normalize_candidates(
        submission.get("candidates"), meta_ids=meta_ids, event_ids=event_ids
    )
    candidate_map = {item["candidate_id"]: item for item in candidates}
    selection = submission.get("selection")
    if not isinstance(selection, Mapping):
        raise FactoryEvolutionError("Candidate selection must be an object")
    _exact_keys(
        selection,
        {"candidate_id", "compared_candidate_ids", "rationale", "dimensions_considered"},
        label="Candidate selection",
    )
    selected_id = _exact_identifier(selection.get("candidate_id"), label="selected candidate_id")
    if selected_id not in candidate_map:
        raise FactoryEvolutionError("Selected candidate is dangling")
    compared = _semantic_ids(
        selection.get("compared_candidate_ids"),
        label="compared candidate IDs",
        allowed=set(candidate_map),
        allow_empty=len(candidate_map) == 1,
    )
    if selected_id in compared:
        raise FactoryEvolutionError("Selected candidate cannot compare against itself")
    dimensions = selection.get("dimensions_considered")
    if dimensions != list(SELECTION_DIMENSIONS):
        raise FactoryEvolutionError("Selection must preserve every visible dimension in order")
    normalized_selection = {
        "candidate_id": selected_id,
        "compared_candidate_ids": compared,
        "rationale": _semantic_text(
            selection.get("rationale"), label="candidate selection rationale"
        ),
        "dimensions_considered": list(SELECTION_DIMENSIONS),
    }
    experiment = _normalize_experiment(
        submission.get("experiment"), selected=candidate_map[selected_id]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REVIEW_KIND,
        "packet_id": packet["packet_id"],
        "packet_root": packet["packet_root"],
        "reviewer_id": _exact_identifier(
            submission.get("reviewer_id"), label="reviewer_id"
        ),
        "observations": observations,
        "lessons": lessons,
        "meta_patterns": meta_patterns,
        "candidates": candidates,
        "selection": normalized_selection,
        "experiment": experiment,
    }


def build_evolution_review(
    packet: Mapping[str, Any], submission: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate submitted semantic judgment and bind it to one learning packet."""

    material = _normalize_review_material(packet, submission)
    review_root = digest(material)
    return {
        **material,
        "review_id": "evolution-review-" + review_root[:20],
        "review_root": review_root,
    }


def verify_evolution_review(
    packet: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(review, Mapping):
        raise FactoryEvolutionError("Evolution review must be an object")
    material = dict(review)
    recorded_root = _exact_sha256(material.pop("review_root", None), label="review_root")
    review_id = _exact_identifier(material.pop("review_id", None), label="review_id")
    rebuilt = build_evolution_review(packet, material)
    if rebuilt["review_root"] != recorded_root or rebuilt["review_id"] != review_id:
        raise FactoryEvolutionError("Evolution review identity is stale")
    return dict(review)


def _normalize_results(
    value: Any,
    *,
    label: str,
    case_ids: set[str],
    event_ids: set[str],
    expected_revision: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != len(case_ids):
        raise FactoryEvolutionError(f"{label} must cover every experiment case exactly once")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise FactoryEvolutionError(f"{label} result must be an object")
        _exact_keys(
            item,
            {
                "case_id",
                "evidence_class",
                "evidence_ids",
                "outcome",
                "observed_effect",
                "resource_cost",
                "regressions",
                "condition_revision",
                "evidence_root",
            },
            label=f"{label} result",
        )
        case_id = _exact_identifier(item.get("case_id"), label=f"{label} case_id")
        if case_id not in case_ids or case_id in seen:
            raise FactoryEvolutionError(f"{label} has a dangling or duplicate case")
        seen.add(case_id)
        evidence_class = str(item.get("evidence_class"))
        if evidence_class not in RESULT_EVIDENCE_CLASSES:
            raise FactoryEvolutionError(f"{label} evidence class is unsupported")
        outcome = str(item.get("outcome"))
        if outcome not in RESULT_OUTCOMES:
            raise FactoryEvolutionError(f"{label} outcome is unsupported")
        condition_revision = _exact_revision(
            item.get("condition_revision"), label=f"{label} condition revision"
        )
        if condition_revision != expected_revision:
            raise FactoryEvolutionError(f"{label} is not bound to its condition revision")
        normalized = {
            "case_id": case_id,
            "evidence_class": evidence_class,
            "evidence_ids": _semantic_ids(
                item.get("evidence_ids"),
                label=f"{label} evidence IDs",
                allowed=event_ids,
            ),
            "outcome": outcome,
            "observed_effect": _semantic_text(
                item.get("observed_effect"), label=f"{label} observed effect"
            ),
            "resource_cost": _semantic_text(
                item.get("resource_cost"), label=f"{label} resource cost"
            ),
            "regressions": _semantic_strings(
                item.get("regressions"),
                label=f"{label} regressions",
                allow_empty=True,
            ),
            "condition_revision": condition_revision,
        }
        recorded_evidence_root = _exact_sha256(
            item.get("evidence_root"), label=f"{label} evidence root"
        )
        if recorded_evidence_root != experiment_result_evidence_root(normalized):
            raise FactoryEvolutionError(f"{label} evidence root is stale")
        result.append({**normalized, "evidence_root": recorded_evidence_root})
    return sorted(result, key=lambda item: item["case_id"])


def experiment_result_evidence_root(result: Mapping[str, Any]) -> str:
    """Return the canonical root for one normalized condition-bound result."""

    return digest(
        {
            "schema_version": SCHEMA_VERSION,
            "kind": RESULT_EVIDENCE_KIND,
            "result": dict(result),
        }
    )


def _normalize_evaluation_material(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    submission: Mapping[str, Any],
) -> dict[str, Any]:
    verified_review = verify_evolution_review(packet, review)
    if not isinstance(submission, Mapping):
        raise FactoryEvolutionError("Candidate evaluation submission must be an object")
    _reject_forbidden_source_keys(submission, label="candidate evaluation")
    _exact_keys(
        submission,
        {
            "schema_version",
            "kind",
            "packet_id",
            "packet_root",
            "review_id",
            "review_root",
            "experiment_id",
            "candidate_id",
            "evaluator_id",
            "baseline_results",
            "candidate_results",
            "contrary_evidence_ids",
            "regression_findings",
            "disposition",
            "rationale",
        },
        label="Candidate evaluation submission",
    )
    if submission.get("schema_version") != SCHEMA_VERSION or submission.get("kind") != EVALUATION_KIND:
        raise FactoryEvolutionError("Candidate evaluation kind or schema is unsupported")
    for field in ("packet_id", "packet_root", "review_id", "review_root"):
        expected = packet[field] if field.startswith("packet") else verified_review[field]
        if submission.get(field) != expected:
            raise FactoryEvolutionError(f"Candidate evaluation {field} is stale")
    experiment = verified_review["experiment"]
    if submission.get("experiment_id") != experiment["experiment_id"]:
        raise FactoryEvolutionError("Candidate evaluation experiment is stale")
    if submission.get("candidate_id") != experiment["candidate_id"]:
        raise FactoryEvolutionError("Candidate evaluation candidate is stale")
    evaluator = _exact_identifier(
        submission.get("evaluator_id"), label="evaluation evaluator_id"
    )
    if evaluator != experiment["evaluator_id"] or evaluator in {
        experiment["proposer_id"],
        experiment["implementer_id"],
    }:
        raise FactoryEvolutionError("Candidate evaluation is not independent")
    case_ids = set(experiment["positive_case_ids"] + experiment["exception_case_ids"])
    event_ids, _ = _packet_reference_sets(packet)
    baseline = _normalize_results(
        submission.get("baseline_results"),
        label="baseline results",
        case_ids=case_ids,
        event_ids=event_ids,
        expected_revision=experiment["baseline_revision"],
    )
    candidate = _normalize_results(
        submission.get("candidate_results"),
        label="candidate results",
        case_ids=case_ids,
        event_ids=event_ids,
        expected_revision=experiment["candidate_revision"],
    )
    disposition = str(submission.get("disposition"))
    if disposition not in DISPOSITIONS:
        raise FactoryEvolutionError("Candidate disposition is unsupported")
    regression_findings = _semantic_strings(
        submission.get("regression_findings"),
        label="evaluation regression findings",
        allow_empty=True,
    )
    if disposition == "promote":
        if regression_findings or any(item["regressions"] for item in candidate):
            raise FactoryEvolutionError("Candidate with regression findings cannot be promoted")
        if any(item["outcome"] != "pass" for item in candidate):
            raise FactoryEvolutionError("Promoted candidate must pass every experiment case")
        if any(item["evidence_class"] != "observed" for item in baseline + candidate):
            raise FactoryEvolutionError(
                "Synthetic or shadow evidence alone cannot justify promotion"
            )
        baseline_by_case = {item["case_id"]: item for item in baseline}
        candidate_by_case = {item["case_id"]: item for item in candidate}
        if any(
            baseline_by_case[case_id]["evidence_root"]
            == candidate_by_case[case_id]["evidence_root"]
            for case_id in case_ids
        ):
            raise FactoryEvolutionError(
                "Promotion evidence must be independently bound to each condition"
            )
        if experiment["comparison_mode"] == "improvement" and not any(
            baseline_by_case[case_id]["outcome"] != "pass" for case_id in case_ids
        ):
            raise FactoryEvolutionError(
                "Improvement promotion requires a mechanically visible baseline delta"
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": EVALUATION_KIND,
        "packet_id": packet["packet_id"],
        "packet_root": packet["packet_root"],
        "review_id": verified_review["review_id"],
        "review_root": verified_review["review_root"],
        "experiment_id": experiment["experiment_id"],
        "candidate_id": experiment["candidate_id"],
        "evaluator_id": evaluator,
        "baseline_results": baseline,
        "candidate_results": candidate,
        "contrary_evidence_ids": _semantic_ids(
            submission.get("contrary_evidence_ids"),
            label="evaluation contrary evidence IDs",
            allowed=event_ids,
            allow_empty=True,
        ),
        "regression_findings": regression_findings,
        "disposition": disposition,
        "rationale": _semantic_text(
            submission.get("rationale"), label="evaluation rationale"
        ),
    }


def build_candidate_evaluation(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    submission: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate independent baseline/candidate results and record a disposition."""

    material = _normalize_evaluation_material(packet, review, submission)
    evaluation_root = digest(material)
    return {
        **material,
        "evaluation_id": "candidate-evaluation-" + evaluation_root[:20],
        "evaluation_root": evaluation_root,
    }


def verify_candidate_evaluation(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(evaluation, Mapping):
        raise FactoryEvolutionError("Candidate evaluation must be an object")
    material = dict(evaluation)
    recorded_root = _exact_sha256(
        material.pop("evaluation_root", None), label="evaluation_root"
    )
    evaluation_id = _exact_identifier(
        material.pop("evaluation_id", None), label="evaluation_id"
    )
    rebuilt = build_candidate_evaluation(packet, review, material)
    if rebuilt["evaluation_root"] != recorded_root or rebuilt["evaluation_id"] != evaluation_id:
        raise FactoryEvolutionError("Candidate evaluation identity is stale")
    return dict(evaluation)


def build_evolution_machine_report(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    verified_review = verify_evolution_review(packet, review)
    verified_evaluation = verify_candidate_evaluation(packet, review, evaluation)
    selected_id = verified_review["selection"]["candidate_id"]
    selected = next(
        item for item in verified_review["candidates"] if item["candidate_id"] == selected_id
    )
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": MACHINE_REPORT_KIND,
        "packet_id": packet["packet_id"],
        "packet_root": packet["packet_root"],
        "review_id": verified_review["review_id"],
        "review_root": verified_review["review_root"],
        "evaluation_id": verified_evaluation["evaluation_id"],
        "evaluation_root": verified_evaluation["evaluation_root"],
        "selected_candidate": {
            "candidate_id": selected_id,
            "candidate_type": selected["candidate_type"],
            "selection_dimensions": selected["selection_dimensions"],
            "disposition": verified_evaluation["disposition"],
        },
        "result_roots": {
            "baseline": digest(verified_evaluation["baseline_results"]),
            "candidate": digest(verified_evaluation["candidate_results"]),
            "contrary_evidence": digest(verified_evaluation["contrary_evidence_ids"]),
            "regression_findings": digest(verified_evaluation["regression_findings"]),
        },
        "counts": {
            "lessons": len(verified_review["lessons"]),
            "meta_patterns": len(verified_review["meta_patterns"]),
            "candidates": len(verified_review["candidates"]),
            "baseline_results": len(verified_evaluation["baseline_results"]),
            "candidate_results": len(verified_evaluation["candidate_results"]),
        },
    }
    report_root = digest(material)
    return {
        **material,
        "report_id": "evolution-report-" + report_root[:20],
        "report_root": report_root,
    }


def verify_evolution_machine_report(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    expected = build_evolution_machine_report(packet, review, evaluation)
    if canonical(expected) != canonical(report):
        raise FactoryEvolutionError("Evolution machine report does not exactly rebuild")
    return dict(report)


def build_evolution_manifest(artifacts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(artifacts, Mapping) or not artifacts or len(artifacts) > 8:
        raise FactoryEvolutionError("Evolution manifest requires bounded artifacts")
    entries: list[dict[str, Any]] = []
    aggregate_bytes = 0
    for name in sorted(artifacts):
        if not re.fullmatch(r"[a-z][a-z0-9-]*\.json", name):
            raise FactoryEvolutionError("Evolution artifact name is unsafe")
        artifact = artifacts[name]
        if not isinstance(artifact, Mapping):
            raise FactoryEvolutionError("Evolution artifact must be an object")
        raw = canonical(artifact)
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise FactoryEvolutionError("Evolution artifact exceeds its byte bound")
        aggregate_bytes += len(raw)
        if aggregate_bytes > MAX_MANIFEST_ARTIFACT_BYTES:
            raise FactoryEvolutionError("Evolution manifest artifacts exceed aggregate bytes")
        entries.append(
            {
                "name": name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "artifacts": entries,
    }
    manifest_root = digest(material)
    return {
        **material,
        "manifest_id": "evolution-manifest-" + manifest_root[:20],
        "manifest_root": manifest_root,
    }


def verify_evolution_manifest(
    manifest: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    expected = build_evolution_manifest(artifacts)
    if canonical(expected) != canonical(manifest):
        raise FactoryEvolutionError("Evolution manifest does not exactly rebuild")
    return dict(manifest)


def build_evolution_bundle(
    packet: Mapping[str, Any],
    review: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    verified_packet = verify_learning_packet(packet)
    verified_review = verify_evolution_review(packet, review)
    verified_evaluation = verify_candidate_evaluation(packet, review, evaluation)
    report = build_evolution_machine_report(packet, review, evaluation)
    artifacts = {
        "learning-packet.json": verified_packet,
        "review.json": verified_review,
        "evaluation.json": verified_evaluation,
        "machine-report.json": report,
    }
    return {**artifacts, "manifest.json": build_evolution_manifest(artifacts)}


def verify_evolution_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise FactoryEvolutionError("Evolution bundle must be an object")
    _exact_keys(
        bundle,
        {
            "learning-packet.json",
            "review.json",
            "evaluation.json",
            "machine-report.json",
            "manifest.json",
        },
        label="Evolution bundle",
    )
    packet = bundle["learning-packet.json"]
    review = bundle["review.json"]
    evaluation = bundle["evaluation.json"]
    report = bundle["machine-report.json"]
    manifest = bundle["manifest.json"]
    verify_learning_packet(packet)
    verify_evolution_review(packet, review)
    verify_candidate_evaluation(packet, review, evaluation)
    verify_evolution_machine_report(packet, review, evaluation, report)
    verify_evolution_manifest(
        manifest,
        {
            "learning-packet.json": packet,
            "review.json": review,
            "evaluation.json": evaluation,
            "machine-report.json": report,
        },
    )
    return deepcopy(dict(bundle))
