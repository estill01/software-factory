#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from email.message import EmailMessage
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import supervision_log  # noqa: E402
import terminal_report  # noqa: E402


TARGET = "target-terminal-1234"
FINGERPRINT = "state-terminal-1234"
MISSION = "a" * 64


def init_args() -> argparse.Namespace:
    return argparse.Namespace(
        target_thread=TARGET,
        target_label="terminal-test",
        watcher_thread="watcher-terminal-1234",
        reviewer_thread="reviewer-terminal-1234",
        base_reviewer_thread="base-terminal-1234",
        notice_reviewer_thread="notice-terminal-1234",
        fix_executor_thread="fix-terminal-1234",
    )


def fixture_review(packet: dict[str, object]) -> dict[str, object]:
    evidence = [packet["lifecycle_record_id"]]
    prior_report_ids = [
        item["report_id"] for item in packet.get("prior_report_records", [])
    ]

    def report(title: str, start: str, headings: list[str]) -> dict[str, object]:
        return {
            "title": title,
            "coverage_start": start,
            "coverage_end": packet["coverage"]["end"],
            "executive_summary": "The bounded implementation reached its verified observable outcome with preserved evidence and explicit limitations.",
            "sections": [
                {
                    "heading": heading,
                    "narrative": f"{heading} was reconstructed from the exact completion, lifecycle, review, and prior-report evidence.",
                    "evidence": (
                        evidence + prior_report_ids
                        if title == terminal_report.FULL_TITLE
                        and heading == "Report synthesis"
                        else evidence
                    ),
                }
                for heading in headings
            ],
            "limitations": [
                "This report is derived implementation evidence and does not confer patent, legal, filing, release, or substantive approval status."
            ],
        }

    return {
        "schema_version": 1,
        "kind": f"{terminal_report.REPORT_KIND}-cognitive-review",
        "report_set_id": packet["report_set_id"],
        "source_root": packet["source_root"],
        "mission_root": packet["mission_root"],
        "state_fingerprint": packet["state_fingerprint"],
        "completion_record_id": packet["completion_record_id"],
        "lifecycle_record_id": packet["lifecycle_record_id"],
        "delta_report": report(
            terminal_report.DELTA_TITLE,
            packet["coverage"]["delta_start"],
            list(terminal_report.DELTA_HEADINGS),
        ),
        "full_report": report(
            terminal_report.FULL_TITLE,
            packet["coverage"]["full_start"],
            list(terminal_report.FULL_HEADINGS),
        ),
    }


def gmail_readback(
    *, verified: dict[str, object], policy: dict[str, object]
) -> str:
    message = EmailMessage()
    message["Subject"] = policy["notifications"]["gmail"]["subject"]
    message["From"] = "codex@example.test"
    message["To"] = "operator@example.test"
    message["Date"] = dt.datetime.now(dt.timezone.utc)
    message["Message-ID"] = "<terminal-report@example.test>"
    message.set_content("Terminal implementation reports are attached.")
    attachments = []
    for filename, path_key in (
        ("delta-report.pdf", "delta_pdf_path"),
        ("full-report.pdf", "full_pdf_path"),
    ):
        payload = Path(str(verified[path_key])).read_bytes()
        message.add_attachment(
            payload,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )
        attachments.append(
            {
                "filename": filename,
                "attachment_id": f"gmail-attachment-{filename.split('-')[0]}",
                "read_tool_call_id": f"exec-read-{filename.split('-')[0]}-attachment",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    receipt = {
        "schema_version": 1,
        "kind": "gmail-terminal-delivery-readback",
        "message_id": "gmail-terminal-result",
        "thread_id": "gmail-terminal-thread",
        "reply_message_id": policy["notifications"]["gmail"]["reply_message_id"],
        "read_tool_call_id": "exec-read-terminal-email",
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "raw_mime_base64": base64.urlsafe_b64encode(message.as_bytes()).decode(),
        "attachments": attachments,
    }
    return base64.b64encode(
        json.dumps(receipt, separators=(",", ":")).encode()
    ).decode()


def write_automation_owners(root: Path, automation_ids: list[str]) -> None:
    updated_at = int((dt.datetime.now(dt.timezone.utc).timestamp() + 60) * 1000)
    for automation_id in automation_ids:
        directory = root / automation_id
        directory.mkdir(parents=True)
        (directory / "automation.toml").write_text(
            "\n".join(
                (
                    "version = 1",
                    f'id = "{automation_id}"',
                    'kind = "heartbeat"',
                    f'name = "{automation_id}"',
                    'prompt = "terminal test"',
                    'status = "PAUSED"',
                    'rrule = "RRULE:FREQ=MINUTELY;INTERVAL=20"',
                    f'target_thread_id = "{TARGET}"',
                    "created_at = 1",
                    f"updated_at = {updated_at}",
                    "",
                )
            ),
            encoding="utf-8",
        )


class TerminalReportUnitTests(unittest.TestCase):
    def packet(self) -> dict[str, object]:
        events = [
            {
                "record_id": "EVT-000001",
                "record_sha256": "1" * 64,
                "timestamp": "2026-08-01T00:00:00+00:00",
                "kind": "roundup",
            },
            {
                "record_id": "EVT-000002",
                "record_sha256": "2" * 64,
                "timestamp": "2026-08-01T01:00:00+00:00",
                "kind": "check",
            },
            {
                "record_id": "EVT-000003",
                "record_sha256": "3" * 64,
                "timestamp": "2026-08-01T02:00:00+00:00",
                "kind": "lifecycle",
            },
        ]
        return terminal_report.build_packet(
            target_label="target",
            target_thread_id=TARGET,
            mission_root=MISSION,
            state_fingerprint=FINGERPRINT,
            completion_record=events[1],
            lifecycle_record=events[2],
            all_events=events,
            prior_reports=[
                {
                    "report_id": "weekly-report-1234",
                    "source_root": "4" * 64,
                    "manifest_root": "5" * 64,
                }
            ],
        )

    def test_packet_uses_latest_report_marker_for_delta(self) -> None:
        packet = self.packet()
        self.assertEqual(packet["coverage"]["delta_anchor_record_id"], "EVT-000001")
        self.assertEqual(len(packet["delta_event_records"]), 2)
        self.assertEqual(len(packet["full_event_records"]), 3)

    def test_review_requires_exact_sections_and_known_evidence(self) -> None:
        packet = self.packet()
        review = fixture_review(packet)
        validated = terminal_report.validate_review(review, packet)
        self.assertEqual(validated["report_set_id"], packet["report_set_id"])

        review["delta_report"]["sections"][0]["evidence"] = ["EVT-unknown"]
        with self.assertRaisesRegex(
            terminal_report.TerminalReportError, "unknown evidence"
        ):
            terminal_report.validate_review(review, packet)

    def test_delta_and_report_of_reports_scope_are_enforced(self) -> None:
        packet = self.packet()
        review = fixture_review(packet)
        review["delta_report"]["sections"][0]["evidence"] = ["EVT-000001"]
        with self.assertRaisesRegex(
            terminal_report.TerminalReportError, "unknown evidence"
        ):
            terminal_report.validate_review(review, packet)

        review = fixture_review(packet)
        synthesis = next(
            section
            for section in review["full_report"]["sections"]
            if section["heading"] == "Report synthesis"
        )
        synthesis["evidence"] = [packet["lifecycle_record_id"]]
        with self.assertRaisesRegex(
            terminal_report.TerminalReportError, "synthesize every verified"
        ):
            terminal_report.validate_review(review, packet)

    def test_packet_rejects_forged_source_identity(self) -> None:
        packet = self.packet()
        packet["source_root"] = "f" * 64
        with self.assertRaisesRegex(
            terminal_report.TerminalReportError, "source root differs"
        ):
            terminal_report.validate_packet(packet)

    def test_pdf_outputs_are_parseable_and_titled(self) -> None:
        from pypdf import PdfReader

        packet = self.packet()
        review = terminal_report.validate_review(fixture_review(packet), packet)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for key, expected in (
                ("delta_report", "Terminal Work Since Last Report"),
                ("full_report", "Terminal Full Implementation Report"),
            ):
                path = root / f"{key}.pdf"
                terminal_report.render_pdf(
                    path, review[key], report_set_id=packet["report_set_id"]
                )
                reader = PdfReader(str(path))
                text = "".join((page.extract_text() or "") for page in reader.pages[:2])
                self.assertGreaterEqual(len(reader.pages), 3)
                self.assertIn(expected, text)


class TerminalReportIntegrationTests(unittest.TestCase):
    def prepare_root(self, root: Path) -> Path:
        directory = root / TARGET
        directory.mkdir(parents=True)
        policy = supervision_log.default_policy(init_args())
        policy["mission_binding"] = supervision_log.mission_binding_contract(
            MISSION, "mission-source-terminal"
        )
        policy["notifications"]["gmail"].update(
            {
                "enabled": True,
                "reply_message_id": "gmail-seed-terminal",
                "project_key": "Terminal",
                "subject": "Codex Tracker Supervision - Terminal",
            }
        )
        policy["runtime"].update(
            {
                "routine_automation_id": "watcher-automation-terminal",
                "meta_automation_id": "reviewer-automation-terminal",
                "gmail_poll_automation_id": "gmail-automation-terminal",
                "roundup_automation_id": "roundup-automation-terminal",
            }
        )
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.atomic_json(directory / "policy.json", policy)
        completion = {
            "schema_version": 1,
            "record_id": "EVT-000001",
            "timestamp": "2026-08-01T00:00:00+00:00",
            "target_thread_id": TARGET,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": FINGERPRINT,
            "status": "verified",
            "severity": "info",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "summary": "Observable outcome verified.",
            "evidence": ["evidence-terminal"],
            "mission_root": MISSION,
            "policy_sha256": policy["policy_sha256"],
            **{
                field: "b" * 64
                for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS
            },
        }
        lifecycle = {
            "schema_version": 1,
            "record_id": "EVT-000002",
            "timestamp": "2026-08-01T01:00:00+00:00",
            "target_thread_id": TARGET,
            "kind": "lifecycle",
            "model": "gpt-5.6-terra",
            "reasoning": "max",
            "state_fingerprint": FINGERPRINT,
            "status": "completed",
            "severity": "info",
            "category": "implementation-lifecycle",
            "summary": "Target completed.",
            "evidence": ["target-terminal"],
            "outcome_completion_record_id": "EVT-000001",
            "policy_sha256": policy["policy_sha256"],
        }
        supervision_log.append_raw(directory / "events.jsonl", completion)
        supervision_log.append_raw(directory / "events.jsonl", lifecycle)
        return directory

    def finalized_reports(
        self, root: Path
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        self.prepare_root(root)
        prepare_args = argparse.Namespace(
            root=str(root),
            target_thread=TARGET,
            lifecycle_record="EVT-000002",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_terminal_report_prepare(prepare_args)
        prepared = json.loads(output.getvalue())
        packet = json.loads(Path(prepared["review_packet_path"]).read_text())
        review = fixture_review(packet)
        finalize_args = argparse.Namespace(
            root=str(root),
            target_thread=TARGET,
            report_set_id=prepared["report_set_id"],
            review_base64=base64.b64encode(
                json.dumps(review, separators=(",", ":")).encode()
            ).decode(),
        )
        with redirect_stdout(io.StringIO()):
            supervision_log.cmd_terminal_report_finalize(finalize_args)
        verified = supervision_log.verify_terminal_report_set(
            root / TARGET, prepared["report_set_id"]
        )
        return prepared, review, verified

    def test_reports_delivery_gate_and_shutdown_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_root(root)
            prepare_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
            )
            prepared_output = io.StringIO()
            with redirect_stdout(prepared_output):
                supervision_log.cmd_terminal_report_prepare(prepare_args)
            prepared = json.loads(prepared_output.getvalue())
            packet = json.loads(Path(prepared["review_packet_path"]).read_text())
            review = fixture_review(packet)
            finalize_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id=prepared["report_set_id"],
                review_base64=base64.b64encode(
                    json.dumps(review, separators=(",", ":")).encode()
                ).decode(),
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_terminal_report_finalize(finalize_args)
            verify_output = io.StringIO()
            with redirect_stdout(verify_output):
                supervision_log.cmd_terminal_report_verify(finalize_args)
            verified = json.loads(verify_output.getvalue())
            self.assertTrue(verified["valid"])

            gate_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_state="completed",
                source_record="EVT-000002",
                state_fingerprint=FINGERPRINT,
            )
            before_output = io.StringIO()
            with redirect_stdout(before_output):
                supervision_log.cmd_lifecycle_gate(gate_args)
            before = json.loads(before_output.getvalue())
            self.assertTrue(before["completion_permitted"])
            self.assertFalse(before["terminal_reports_delivered"])
            self.assertFalse(before["supervision_pause_permitted"])
            self.assertEqual(
                before["completion_action"],
                "prepare-finalize-verify-email-and-record-terminal-reports",
            )

            delivery_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id=prepared["report_set_id"],
                gmail_readback_base64=gmail_readback(
                    verified=verified,
                    policy=supervision_log.read_json(root / TARGET / "policy.json"),
                ),
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_terminal_report_delivery(delivery_args)
            after_output = io.StringIO()
            with redirect_stdout(after_output):
                supervision_log.cmd_lifecycle_gate(gate_args)
            after = json.loads(after_output.getvalue())
            self.assertTrue(after["terminal_reports_delivered"])
            self.assertTrue(after["supervision_pause_permitted"])
            self.assertEqual(len(after["pause_automation_ids"]), 4)

            shutdown = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "automation owner is missing",
            ):
                supervision_log.cmd_terminal_shutdown(shutdown)

            automation_root = root / "automations"
            write_automation_owners(
                automation_root, after["pause_automation_ids"]
            )
            shutdown_output = io.StringIO()
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ):
                with redirect_stdout(shutdown_output):
                    supervision_log.cmd_terminal_shutdown(shutdown)
            self.assertFalse(json.loads(shutdown_output.getvalue())["duplicate"])

    def test_delivery_rejects_claim_without_gmail_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_root(root)
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id="terminal-missing-report",
                gmail_readback_base64=base64.b64encode(b"{}").decode(),
            )
            with self.assertRaises(supervision_log.SupervisionLogError):
                supervision_log.cmd_terminal_report_delivery(args)

    def test_delivery_rejects_divergent_attachment_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _review, verified = self.finalized_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            encoded = gmail_readback(verified=verified, policy=policy)
            receipt = json.loads(base64.b64decode(encoded))
            receipt["attachments"][0]["sha256"] = "0" * 64
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id=prepared["report_set_id"],
                gmail_readback_base64=base64.b64encode(
                    json.dumps(receipt, separators=(",", ":")).encode()
                ).decode(),
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "attachment read-back differs",
            ):
                supervision_log.cmd_terminal_report_delivery(args)

    def test_forged_pdf_and_manifest_identity_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, review, verified = self.finalized_reports(root)
            report_directory = Path(str(verified["delta_pdf_path"])).parent
            paths = {
                name: report_directory / name
                for name in (
                    "review-packet.json",
                    "review.json",
                    "delta-report.json",
                    "delta-report.md",
                    "delta-report.pdf",
                    "full-report.json",
                    "full-report.md",
                    "full-report.pdf",
                )
            }
            forged = json.loads(json.dumps(review["delta_report"]))
            forged["sections"][0]["narrative"] = (
                "Forged narrative that is absent from the canonical review."
            )
            terminal_report.render_pdf(
                paths["delta-report.pdf"],
                forged,
                report_set_id=prepared["report_set_id"],
            )
            manifest = terminal_report.manifest_for(
                paths,
                report_set_id=prepared["report_set_id"],
                source_root=prepared["source_root"],
            )
            supervision_log.atomic_json(report_directory / "manifest.json", manifest)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "PDF projection differs"
            ):
                supervision_log.verify_terminal_report_set(
                    root / TARGET, prepared["report_set_id"]
                )

            terminal_report.render_pdf(
                paths["delta-report.pdf"],
                review["delta_report"],
                report_set_id=prepared["report_set_id"],
            )
            manifest = terminal_report.manifest_for(
                paths,
                report_set_id=prepared["report_set_id"],
                source_root=prepared["source_root"],
            )
            manifest["report_set_id"] = "forged-terminal-report-set"
            supervision_log.atomic_json(report_directory / "manifest.json", manifest)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "manifest identity differs"
            ):
                supervision_log.verify_terminal_report_set(
                    root / TARGET, prepared["report_set_id"]
                )

    def test_prior_weekly_reports_are_verified_before_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / TARGET
            report_directory = (
                directory / "reports" / "weekly" / "weekly-report-verified"
            )
            report_directory.mkdir(parents=True)
            supervision_log.atomic_json(
                report_directory / "manifest.json",
                {
                    "report_id": "weekly-report-verified",
                    "source_root": "1" * 64,
                    "manifest_root": "2" * 64,
                },
            )
            supervision_log.atomic_json(
                report_directory / "report.json",
                {
                    "kind": "supervision-weekly-review-record",
                    "metrics": {"coverage": {"start": "a", "end": "b"}},
                    "cognitive_review": {"summary": "verified"},
                },
            )
            verified = {
                "source_root": "1" * 64,
                "manifest_root": "2" * 64,
                "report_sha256": "3" * 64,
                "review_sha256": "4" * 64,
                "pdf_sha256": "5" * 64,
            }
            with mock.patch.object(
                supervision_log,
                "verify_weekly_report_set",
                return_value=verified,
            ) as verifier:
                rows = supervision_log.terminal_prior_report_inventory(directory)
            verifier.assert_called_once_with(directory, "weekly-report-verified")
            self.assertEqual(rows[0]["report_sha256"], "3" * 64)


if __name__ == "__main__":
    unittest.main()
