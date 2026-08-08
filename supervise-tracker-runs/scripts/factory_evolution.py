#!/usr/bin/env python3
"""Pure, deterministic builders and validators for Factory evolution artifacts."""

from __future__ import annotations

import hashlib
import json
import re
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
                "evidence_refs": _evidence_refs(item.get("evidence", [])),
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
    report_id = _bounded_text(report.get("report_id"), limit=160)
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
        record_id = _bounded_text(value.get("record_id"), limit=160)
        if not record_id or record_id in record_ids:
            raise FactoryEvolutionError(
                f"{source.name} has a missing or duplicate record ID at line {line_number}"
            )
        record_ids.add(record_id)
        record_hashes.append(recorded_hash)
        previous = recorded_hash
        target_thread_id = _bounded_text(value.get("target_thread_id"), limit=160)
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
        "first_record_sha256": record_hashes[0],
        "last_record_sha256": record_hashes[-1],
        "target_thread_ids": sorted(target_thread_ids),
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

    reports_by_root: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for path in report_paths:
        reference, hypotheses = _load_report(path)
        source_root = reference["source_root"]
        candidate = (reference, hypotheses)
        current = reports_by_root.get(source_root)
        if current is None or canonical(candidate) < canonical(current):
            reports_by_root[source_root] = candidate

    ledgers_by_root: dict[str, dict[str, Any]] = {}
    events_by_hash: dict[str, dict[str, Any]] = {}
    unknown_by_ledger: dict[str, int] = {}
    for path in event_paths:
        manifest, source_events, unknown_count = _load_event_ledger(path)
        ledger_root = manifest["ledger_root"]
        current_manifest = ledgers_by_root.get(ledger_root)
        if current_manifest is not None and current_manifest != manifest:
            raise FactoryEvolutionError("One event ledger root has conflicting manifests")
        ledgers_by_root[ledger_root] = manifest
        unknown_by_ledger[ledger_root] = unknown_count
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

    reports = [reports_by_root[root][0] for root in sorted(reports_by_root)]
    hypotheses = [
        item
        for root in sorted(reports_by_root)
        for item in reports_by_root[root][1]
    ]
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
            "unsupported_event_kinds": sum(unknown_by_ledger.values()),
        },
    }
    packet_root = digest(material)
    packet = dict(material)
    packet["packet_id"] = "learning-" + packet_root[:20]
    packet["packet_root"] = packet_root
    return verify_learning_packet(packet)


def verify_learning_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Verify packet identity and that every retained claim resolves to a source."""

    value = dict(packet)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise FactoryEvolutionError("Learning packet schema_version is unsupported")
    if value.get("kind") != PACKET_KIND or value.get("authority") != PACKET_AUTHORITY:
        raise FactoryEvolutionError("Learning packet kind or authority is invalid")
    if value.get("transformation") != TRANSFORMATION:
        raise FactoryEvolutionError("Learning packet transformation is invalid")
    recorded_root = _exact_sha256(value.pop("packet_root", None), label="packet_root")
    packet_id = value.pop("packet_id", None)
    expected_root = digest(value)
    if recorded_root != expected_root or packet_id != "learning-" + expected_root[:20]:
        raise FactoryEvolutionError("Learning packet identity is stale")

    sources = value.get("sources")
    evidence = value.get("evidence")
    if not isinstance(sources, Mapping) or not isinstance(evidence, Mapping):
        raise FactoryEvolutionError("Learning packet sources and evidence must be objects")
    report_keys = {
        (item.get("report_id"), item.get("source_root"), item.get("report_sha256"))
        for item in sources.get("reports", [])
        if isinstance(item, Mapping)
    }
    ledger_roots = {
        item.get("ledger_root")
        for item in sources.get("event_ledgers", [])
        if isinstance(item, Mapping)
    }
    for hypothesis in evidence.get("report_hypotheses", []):
        if not isinstance(hypothesis, Mapping):
            raise FactoryEvolutionError("Packet hypothesis must be an object")
        key = (
            hypothesis.get("source_report_id"),
            hypothesis.get("source_root"),
            hypothesis.get("source_report_sha256"),
        )
        if key not in report_keys:
            raise FactoryEvolutionError("Packet hypothesis does not resolve to a report")
    for event in evidence.get("events", []):
        if not isinstance(event, Mapping):
            raise FactoryEvolutionError("Packet event must be an object")
        roots = event.get("source_ledger_roots")
        if not isinstance(roots, list) or not roots or not set(roots) <= ledger_roots:
            raise FactoryEvolutionError("Packet event does not resolve to an event ledger")
        _exact_sha256(event.get("record_sha256"), label="packet event record_sha256")
    result = dict(packet)
    return result
