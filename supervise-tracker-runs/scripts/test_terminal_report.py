#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


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
                    "evidence": evidence,
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
                gmail_message_id="gmail-terminal-result",
                delta_pdf_sha256=verified["delta_pdf_sha256"],
                full_pdf_sha256=verified["full_pdf_sha256"],
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

            bad_shutdown = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
                automation_state=["watcher-automation-terminal=ACTIVE"],
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "automation set differs|must be paused",
            ):
                supervision_log.cmd_terminal_shutdown(bad_shutdown)

            shutdown = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
                automation_state=[f"{item}=PAUSED" for item in after["pause_automation_ids"]],
            )
            shutdown_output = io.StringIO()
            with redirect_stdout(shutdown_output):
                supervision_log.cmd_terminal_shutdown(shutdown)
            self.assertFalse(json.loads(shutdown_output.getvalue())["duplicate"])

    def test_delivery_rejects_wrong_attachment_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_root(root)
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id="terminal-missing-report",
                gmail_message_id="gmail-terminal-result",
                delta_pdf_sha256="0" * 64,
                full_pdf_sha256="0" * 64,
            )
            with self.assertRaises(supervision_log.SupervisionLogError):
                supervision_log.cmd_terminal_report_delivery(args)


if __name__ == "__main__":
    unittest.main()
