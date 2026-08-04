#!/usr/bin/env python3
"""Terminal implementation reports derived from bounded supervision evidence.

The reports are human-readable projections over the existing supervision ledger,
completion record, lifecycle record, and prior derived reports.  They are not a
second status authority and cannot make an incomplete outcome complete.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape


SCHEMA_VERSION = 1
REPORT_KIND = "supervision-terminal-implementation-report"
DELTA_TITLE = "Terminal Work Since Last Report"
FULL_TITLE = "Terminal Full Implementation Report (Report of Reports)"
LOCAL_PATH = re.compile(r"(?:/Users/|file://|\\\\Users\\\\)")
DELTA_HEADINGS = (
    "Work completed",
    "Decisions and corrections",
    "Validation and acceptance",
    "Current outcome and open items",
)
FULL_HEADINGS = (
    "Primary objective and observable result",
    "Implementation arc",
    "Capabilities and artifacts",
    "Validation and independent review",
    "Report synthesis",
    "Incidents and corrections",
    "Open items and limitations",
    "Terminal assessment",
)


class TerminalReportError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_time(value: str) -> dt.datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        result = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TerminalReportError("Terminal report time must be ISO-8601") from exc
    if result.tzinfo is None:
        raise TerminalReportError("Terminal report time must include a timezone")
    return result.astimezone(dt.timezone.utc).replace(microsecond=0)


def iso_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_text(value: Any, *, label: str, maximum: int = 3200) -> str:
    if not isinstance(value, str):
        raise TerminalReportError(f"{label} must be text")
    text = value.strip()
    if not text:
        raise TerminalReportError(f"{label} must not be empty")
    if len(text) > maximum:
        raise TerminalReportError(f"{label} exceeds {maximum} characters")
    if LOCAL_PATH.search(text):
        raise TerminalReportError(f"{label} must not contain a local path")
    return text


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def event_time(record: Mapping[str, Any]) -> dt.datetime:
    return parse_time(str(record.get("timestamp", "")))


def build_packet(
    *,
    target_label: str,
    target_thread_id: str,
    mission_root: str,
    state_fingerprint: str,
    completion_record: Mapping[str, Any],
    lifecycle_record: Mapping[str, Any],
    all_events: Sequence[Mapping[str, Any]],
    prior_reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not all_events:
        raise TerminalReportError("Terminal report requires supervision evidence")
    ordered = sorted(all_events, key=event_time)
    end = event_time(lifecycle_record)
    bounded = [item for item in ordered if event_time(item) <= end]
    if not bounded:
        raise TerminalReportError("Terminal report completion precedes all evidence")
    report_markers = [
        item
        for item in bounded
        if item.get("kind") == "roundup"
        and item.get("record_id") != lifecycle_record.get("record_id")
    ]
    delta_anchor = report_markers[-1] if report_markers else bounded[0]
    delta_start = event_time(delta_anchor)
    delta_events = (
        [item for item in bounded if event_time(item) > delta_start]
        if report_markers
        else list(bounded)
    )
    event_roots = [str(item.get("record_sha256", "")) for item in bounded]
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in event_roots):
        raise TerminalReportError("Terminal report source event lacks an exact hash")
    prior_report_rows = [dict(item) for item in prior_reports]
    source = {
        "event_record_ids": [str(item.get("record_id", "")) for item in bounded],
        "event_record_roots": event_roots,
        "prior_reports": prior_report_rows,
        "completion_record_id": str(completion_record.get("record_id", "")),
        "completion_record_sha256": str(completion_record.get("record_sha256", "")),
        "lifecycle_record_id": str(lifecycle_record.get("record_id", "")),
        "lifecycle_record_sha256": str(lifecycle_record.get("record_sha256", "")),
        "mission_root": mission_root,
        "state_fingerprint": state_fingerprint,
    }
    source_root = digest(source)
    report_set_id = f"terminal-{target_thread_id[:12]}-{source_root[:16]}"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-review-packet",
        "report_set_id": report_set_id,
        "target_label": target_label,
        "target_thread_id": target_thread_id,
        "mission_root": mission_root,
        "state_fingerprint": state_fingerprint,
        "completion_record_id": source["completion_record_id"],
        "lifecycle_record_id": source["lifecycle_record_id"],
        "source_root": source_root,
        "coverage": {
            "delta_start": iso_time(delta_start),
            "full_start": iso_time(event_time(bounded[0])),
            "end": iso_time(end),
            "delta_anchor_record_id": str(delta_anchor.get("record_id", "")),
        },
        "required_reports": {
            "delta": {"title": DELTA_TITLE, "required_headings": list(DELTA_HEADINGS)},
            "full": {"title": FULL_TITLE, "required_headings": list(FULL_HEADINGS)},
        },
        "source": source,
        "delta_event_records": [dict(item) for item in delta_events],
        "full_event_records": [dict(item) for item in bounded],
        "prior_report_records": prior_report_rows,
        "content_boundary": (
            "Derived implementation reporting only; no patent prose, credentials, local "
            "paths, legal conclusions, or new completion authority."
        ),
    }


def _validate_section(
    raw: Any, *, expected_heading: str, known_evidence: set[str]
) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {"heading", "narrative", "evidence"}:
        raise TerminalReportError("Terminal report section shape differs")
    heading = safe_text(raw["heading"], label="section heading", maximum=120)
    if heading != expected_heading:
        raise TerminalReportError("Terminal report section ordering or heading differs")
    narrative = safe_text(raw["narrative"], label=f"{heading} narrative")
    evidence = raw["evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 16:
        raise TerminalReportError(f"{heading} must cite 1-16 evidence records")
    normalized: list[str] = []
    for item in evidence:
        value = safe_text(item, label=f"{heading} evidence", maximum=160)
        if value not in known_evidence:
            raise TerminalReportError(f"{heading} cites unknown evidence")
        if value in normalized:
            raise TerminalReportError(f"{heading} repeats evidence")
        normalized.append(value)
    return {"heading": heading, "narrative": narrative, "evidence": normalized}


def _validate_report(
    raw: Any,
    *,
    title: str,
    headings: Sequence[str],
    known_evidence: set[str],
    coverage: Mapping[str, str],
) -> dict[str, Any]:
    required = {
        "title",
        "coverage_start",
        "coverage_end",
        "executive_summary",
        "sections",
        "limitations",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise TerminalReportError("Terminal implementation report shape differs")
    if raw.get("title") != title:
        raise TerminalReportError("Terminal implementation report title differs")
    start = safe_text(raw["coverage_start"], label="coverage start", maximum=40)
    end = safe_text(raw["coverage_end"], label="coverage end", maximum=40)
    if start != coverage["start"] or end != coverage["end"]:
        raise TerminalReportError("Terminal implementation report coverage differs")
    summary = safe_text(raw["executive_summary"], label="executive summary")
    sections = raw["sections"]
    if not isinstance(sections, list) or len(sections) != len(headings):
        raise TerminalReportError("Terminal implementation report section count differs")
    normalized_sections = [
        _validate_section(item, expected_heading=heading, known_evidence=known_evidence)
        for item, heading in zip(sections, headings, strict=True)
    ]
    limitations = raw["limitations"]
    if not isinstance(limitations, list) or not 1 <= len(limitations) <= 8:
        raise TerminalReportError("Terminal report must state 1-8 limitations")
    normalized_limits = [
        safe_text(item, label="terminal report limitation", maximum=500)
        for item in limitations
    ]
    return {
        "title": title,
        "coverage_start": start,
        "coverage_end": end,
        "executive_summary": summary,
        "sections": normalized_sections,
        "limitations": normalized_limits,
    }


def validate_review(review: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "kind",
        "report_set_id",
        "source_root",
        "mission_root",
        "state_fingerprint",
        "completion_record_id",
        "lifecycle_record_id",
        "delta_report",
        "full_report",
    }
    if not isinstance(review, Mapping) or set(review) != required:
        raise TerminalReportError("Terminal cognitive review shape differs")
    if review.get("schema_version") != SCHEMA_VERSION or review.get("kind") != f"{REPORT_KIND}-cognitive-review":
        raise TerminalReportError("Terminal cognitive review version differs")
    for field in (
        "report_set_id",
        "source_root",
        "mission_root",
        "state_fingerprint",
        "completion_record_id",
        "lifecycle_record_id",
    ):
        if review.get(field) != packet.get(field):
            raise TerminalReportError(f"Terminal cognitive review {field} differs")
    known_evidence = {
        str(item.get("record_id"))
        for item in packet.get("full_event_records", [])
        if item.get("record_id")
    }
    known_evidence.update(
        str(item.get("report_id"))
        for item in packet.get("prior_report_records", [])
        if item.get("report_id")
    )
    coverage = packet["coverage"]
    delta = _validate_report(
        review["delta_report"],
        title=DELTA_TITLE,
        headings=DELTA_HEADINGS,
        known_evidence=known_evidence,
        coverage={"start": coverage["delta_start"], "end": coverage["end"]},
    )
    full = _validate_report(
        review["full_report"],
        title=FULL_TITLE,
        headings=FULL_HEADINGS,
        known_evidence=known_evidence,
        coverage={"start": coverage["full_start"], "end": coverage["end"]},
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-cognitive-review",
        "report_set_id": packet["report_set_id"],
        "source_root": packet["source_root"],
        "mission_root": packet["mission_root"],
        "state_fingerprint": packet["state_fingerprint"],
        "completion_record_id": packet["completion_record_id"],
        "lifecycle_record_id": packet["lifecycle_record_id"],
        "delta_report": delta,
        "full_report": full,
    }


def report_record(
    report: Mapping[str, Any], *, report_set_id: str, source_root: str, report_type: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-{report_type}",
        "report_set_id": report_set_id,
        "source_root": source_root,
        **dict(report),
    }


def markdown_report(report: Mapping[str, Any], *, report_set_id: str) -> str:
    rows = [
        f"# {report['title']}\n\n",
        f"- Report set: `{report_set_id}`\n",
        f"- Coverage: `{report['coverage_start']}` through `{report['coverage_end']}`\n\n",
        "## Executive summary\n\n",
        f"{report['executive_summary']}\n\n",
    ]
    for section in report["sections"]:
        rows.extend(
            [
                f"## {section['heading']}\n\n",
                f"{section['narrative']}\n\n",
                "Evidence: " + ", ".join(f"`{item}`" for item in section["evidence"]) + "\n\n",
            ]
        )
    rows.append("## Limitations\n\n")
    rows.extend(f"- {item}\n" for item in report["limitations"])
    rows.append(
        "\nThis is a derived implementation report. It does not confer patent, legal, filing, release, or substantive approval status.\n"
    )
    return "".join(rows)


def render_pdf(path: Path, report: Mapping[str, Any], *, report_set_id: str) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            ListFlowable,
            ListItem,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except Exception as exc:
        raise TerminalReportError("Terminal PDF dependencies are unavailable") from exc

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TerminalTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#14213D"),
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TerminalHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#145DA0"),
            spaceBefore=8,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TerminalBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#17212F"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TerminalSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#3F4A59"),
        )
    )

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#3F4A59"))
        canvas.drawString(0.65 * inch, 0.36 * inch, report_set_id)
        canvas.drawRightString(7.85 * inch, 0.36 * inch, f"Page {document.page}")
        canvas.restoreState()

    story: list[Any] = [
        Spacer(1, 0.45 * inch),
        Paragraph(escape(str(report["title"])), styles["TerminalTitle"]),
        Paragraph(
            escape(
                f"Coverage: {report['coverage_start']} through {report['coverage_end']}"
            ),
            styles["TerminalSmall"],
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("Executive summary", styles["TerminalHeading"]),
        Paragraph(escape(str(report["executive_summary"])), styles["TerminalBody"]),
        PageBreak(),
    ]
    for index, section in enumerate(report["sections"]):
        if index and index % 3 == 0:
            story.append(PageBreak())
        story.append(
            Paragraph(escape(str(section["heading"])), styles["TerminalHeading"])
        )
        story.append(
            Paragraph(escape(str(section["narrative"])), styles["TerminalBody"])
        )
        story.append(
            Paragraph(
                escape(
                    "Evidence: "
                    + ", ".join(str(item) for item in section["evidence"])
                ),
                styles["TerminalSmall"],
            )
        )
        story.append(Spacer(1, 0.14 * inch))
    story.extend(
        [
            PageBreak(),
            Paragraph("Limitations", styles["TerminalHeading"]),
            ListFlowable(
                [
                    ListItem(Paragraph(escape(item), styles["TerminalBody"]))
                    for item in report["limitations"]
                ],
                bulletType="bullet",
                leftIndent=18,
            ),
            Spacer(1, 0.2 * inch),
            Paragraph(
                "Derived implementation report only. It does not confer patent, legal, filing, release, or substantive approval status.",
                styles["TerminalSmall"],
            ),
        ]
    )
    document = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.62 * inch,
        title=str(report["title"]),
        author="Codex Tracker Supervision",
    )
    try:
        document.build(story, onFirstPage=footer, onLaterPages=footer)
    except Exception as exc:
        raise TerminalReportError("Terminal PDF rendering failed") from exc


def manifest_for(paths: Mapping[str, Path], *, report_set_id: str, source_root: str) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name, path in sorted(paths.items()):
        data = path.read_bytes()
        files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": f"{REPORT_KIND}-manifest",
        "report_set_id": report_set_id,
        "source_root": source_root,
        "files": files,
        "manifest_root": digest(files),
    }
