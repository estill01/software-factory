#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from email import policy as email_policy
from email.message import EmailMessage
from email.parser import BytesParser
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


def sign_provider_review(
    receipt: dict[str, object],
    *,
    policy: dict[str, object],
    verified: dict[str, object],
    private_key: Path,
    authority_key_sha256: str,
    reviewed_at: str,
) -> None:
    receipt.pop("provider_review", None)
    seed, _seed_message, _seed_mime = supervision_log.validate_gmail_message_owner(
        receipt["seed_message"], label="Terminal Gmail seed"
    )
    sent, _sent_message, _sent_mime = supervision_log.validate_gmail_message_owner(
        receipt["sent_message"], label="Terminal Gmail sent message"
    )
    normalized_attachments = [
        {
            "filename": str(item["filename"]),
            "attachment_id": str(item["attachment_id"]),
            "owner_message_id": str(item["owner_message_id"]),
            "owner_thread_id": str(item["owner_thread_id"]),
            "read_tool_call_id": str(item["read_tool_call_id"]),
            "sha256": str(item["sha256"]),
            "bytes": int(item["bytes"]),
        }
        for item in receipt["attachments"]
    ]
    normalized_attachments.sort(key=lambda item: item["filename"])
    readback_core = supervision_log.terminal_gmail_readback_core(
        seed_message=seed,
        sent_message=sent,
        attachments=normalized_attachments,
    )
    provider_review = {
        "schema_version": 1,
        "kind": supervision_log.TERMINAL_GMAIL_PROVIDER_REVIEW_KIND,
        "record_id": "terminal-gmail-provider-review-1234",
        "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
        "disposition": "accepted",
        "target_thread_id": str(policy["target_thread_id"]),
        "report_set_id": str(verified["report_set_id"]),
        "readback_core_sha256": supervision_log.digest(readback_core),
        "reviewed_at": reviewed_at,
        "evidence": ["gmail-provider-output-observed"],
        "authority_key_sha256": authority_key_sha256,
        "review_root": "",
        "signature_base64": "",
    }
    provider_review["review_root"] = supervision_log.digest(
        supervision_log.terminal_gmail_provider_review_root_material(
            provider_review
        )
    )
    with tempfile.TemporaryDirectory() as temporary:
        content = Path(temporary) / "provider-review.json"
        signature = Path(temporary) / "provider-review.sig"
        content.write_bytes(
            supervision_log.canonical(
                supervision_log.adaptive_external_review_signed_material(
                    provider_review
                )
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(private_key),
                "-rawin",
                "-in",
                str(content),
                "-out",
                str(signature),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        provider_review["signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode()
    receipt["provider_review"] = provider_review


def gmail_readback(
    *,
    verified: dict[str, object],
    policy: dict[str, object],
    private_key: Path,
    authority_key_sha256: str,
) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    seed = EmailMessage()
    seed["Subject"] = policy["notifications"]["gmail"]["subject"]
    seed["From"] = "codex@example.test"
    seed["To"] = "operator@example.test"
    seed["Date"] = now - dt.timedelta(minutes=1)
    seed["Message-ID"] = "<supervision-seed@example.test>"
    seed.set_content("Supervision seed.")
    message = EmailMessage()
    message["Subject"] = policy["notifications"]["gmail"]["subject"]
    message["From"] = "codex@example.test"
    message["To"] = "operator@example.test"
    message["Date"] = now
    message["Message-ID"] = "<terminal-report@example.test>"
    message["In-Reply-To"] = "<supervision-seed@example.test>"
    message["References"] = "<supervision-seed@example.test>"
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
                "owner_message_id": "gmail-terminal-result",
                "owner_thread_id": "gmail-terminal-thread",
                "read_tool_call_id": f"exec-read-{filename.split('-')[0]}-attachment",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    receipt = {
        "schema_version": 1,
        "kind": "gmail-terminal-delivery-readback",
        "seed_message": {
            "provider": "gmail.read_email",
            "message_id": policy["notifications"]["gmail"]["reply_message_id"],
            "thread_id": "gmail-terminal-thread",
            "read_tool_call_id": "exec-read-terminal-seed",
            "fetched_at": now.isoformat(),
            "raw_mime_base64": base64.urlsafe_b64encode(seed.as_bytes()).decode(),
        },
        "sent_message": {
            "provider": "gmail.read_email",
            "message_id": "gmail-terminal-result",
            "thread_id": "gmail-terminal-thread",
            "read_tool_call_id": "exec-read-terminal-email",
            "fetched_at": now.isoformat(),
            "raw_mime_base64": base64.urlsafe_b64encode(message.as_bytes()).decode(),
        },
        "attachments": attachments,
    }
    sign_provider_review(
        receipt,
        policy=policy,
        verified=verified,
        private_key=private_key,
        authority_key_sha256=authority_key_sha256,
        reviewed_at=(now + dt.timedelta(seconds=1)).isoformat(),
    )
    return base64.b64encode(
        json.dumps(receipt, separators=(",", ":")).encode()
    ).decode()


def write_automation_owners(
    root: Path, automation_owners: dict[str, str]
) -> None:
    updated_at = int((dt.datetime.now(dt.timezone.utc).timestamp() + 60) * 1000)
    for automation_id, owner_thread_id in automation_owners.items():
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
                    f'target_thread_id = "{owner_thread_id}"',
                    "created_at = 1",
                    f"updated_at = {updated_at}",
                    "",
                )
            ),
            encoding="utf-8",
        )


class TerminalReportUnitTests(unittest.TestCase):
    def test_generic_shutdown_correction_cannot_retire_owner_evidence(self) -> None:
        generic = {
            "schema_version": 1,
            "record_id": "EVT-000099",
            "timestamp": "2026-08-13T00:00:00+00:00",
            "target_thread_id": TARGET,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": FINGERPRINT,
            "status": "rejected",
            "severity": "high",
            "category": supervision_log.TERMINAL_SHUTDOWN_REJECTED_CATEGORY,
            "summary": "Caller assertion.",
            "evidence": ["EVT-000098"],
            "policy_sha256": "1" * 64,
        }
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "shutdown rejection record is invalid",
        ):
            supervision_log.terminal_shutdown_rejected_record_ids([generic])

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

    def test_gmail_attachment_id_accepts_provider_owned_opaque_length(self) -> None:
        provider_id = "A" * 512
        self.assertEqual(
            supervision_log.gmail_attachment_id(provider_id), provider_id
        )
        for invalid in ("not a provider id", "A" * 2049):
            with self.subTest(invalid_length=len(invalid)):
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "Invalid Gmail attachment ID",
                ):
                    supervision_log.gmail_attachment_id(invalid)

    def test_automation_owner_root_is_codex_runtime_state(self) -> None:
        self.assertEqual(
            supervision_log.CODEX_AUTOMATIONS_ROOT,
            supervision_log.DEFAULT_ROOT.parents[1] / "automations",
        )


class TerminalReportIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority_temporary = tempfile.TemporaryDirectory()
        authority_root = Path(cls.authority_temporary.name) / "sealed" / "keys"
        authority_root.mkdir(parents=True)
        authority_root.parent.chmod(0o700)
        authority_root.chmod(0o700)
        cls.provider_private_key = authority_root / "review-private.pem"
        cls.provider_public_key = authority_root / "review-public.pem"
        openssl = str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH)
        subprocess.run(
            [
                openssl,
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(cls.provider_private_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                openssl,
                "pkey",
                "-in",
                str(cls.provider_private_key),
                "-pubout",
                "-out",
                str(cls.provider_public_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cls.provider_public_key.chmod(0o444)
        cls.provider_public_key_sha256 = hashlib.sha256(
            cls.provider_public_key.read_bytes()
        ).hexdigest()
        cls.authority_patches = [
            mock.patch.object(
                supervision_log,
                "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH",
                cls.provider_public_key,
            ),
            mock.patch.object(
                supervision_log,
                "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256",
                cls.provider_public_key_sha256,
            ),
        ]
        for patcher in cls.authority_patches:
            patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        for patcher in reversed(cls.authority_patches):
            patcher.stop()
        cls.authority_temporary.cleanup()

    def encoded_gmail_readback(
        self, *, verified: dict[str, object], policy: dict[str, object]
    ) -> str:
        return gmail_readback(
            verified=verified,
            policy=policy,
            private_key=self.provider_private_key,
            authority_key_sha256=self.provider_public_key_sha256,
        )

    def resign_provider_review(
        self,
        receipt: dict[str, object],
        *,
        policy: dict[str, object],
        verified: dict[str, object],
    ) -> None:
        sign_provider_review(
            receipt,
            policy=policy,
            verified=verified,
            private_key=self.provider_private_key,
            authority_key_sha256=self.provider_public_key_sha256,
            reviewed_at=(dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=1)).isoformat(),
        )

    def prepare_root(self, root: Path, *, bind_gmail: bool = True) -> Path:
        directory = root / TARGET
        directory.mkdir(parents=True)
        policy = supervision_log.default_policy(init_args())
        policy["mission_binding"] = supervision_log.mission_binding_contract(
            MISSION, "mission-source-terminal"
        )
        if bind_gmail:
            policy["notifications"]["gmail"].update(
                {
                    "enabled": False,
                    "reply_message_id": "gmail-seed-terminal",
                    "project_key": "Terminal",
                    "subject": "Codex Tracker Supervision - Terminal",
                }
            )
        policy["runtime"].update(
            {
                "routine_automation_id": "watcher-automation-terminal",
                "meta_automation_id": "reviewer-automation-terminal",
                "gmail_gate_thread_id": "gmail-gate-terminal-1234",
                "gmail_poll_automation_id": "gmail-automation-terminal",
                "roundup_thread_id": "roundup-terminal-1234",
                "roundup_automation_id": "roundup-automation-terminal",
            }
        )
        tracker = root / "terminal-tracker.md"
        tracker.write_text(
            "| Block | Scope | Depends on | Status |\n"
            "|---:|---|---:|---|\n"
            "| 0 | Terminal fixture | — | `completed` |\n\n"
            "## Block 0 — Terminal fixture\n\n"
            "Status: `completed`\n\n"
            "### Completion evidence\n\nAccepted.\n\n"
            "### Stop\n\nStop at this Block boundary.\n",
            encoding="utf-8",
        )
        (
            tracker_path,
            tracker_sha256,
            tracker_structure_sha256,
            tracker_blocks,
        ) = supervision_log.implementation_tracker_snapshot(str(tracker))
        authority = {
            "source_class": "direct-user",
            "source_record": "terminal-range-source-1234",
            "source_sha256": "d" * 64,
        }
        mission_identity = {
            "mission_root": MISSION,
            "mission_source_record": "mission-source-terminal",
        }
        entry = supervision_log.implementation_range_history_entry(
            sequence=1,
            prior_entry_sha256="",
            operation="bound",
            request_text="implement this tracker",
            tracker_sha256=tracker_sha256,
            tracker_structure_sha256=tracker_structure_sha256,
            tracker_path=str(tracker_path),
            tracker_blocks=sorted(tracker_blocks),
            range_intent="full-tracker",
            explicit_blocks=[],
            authority=authority,
            authority_policy_version=1,
            mission_identity=mission_identity,
        )
        genesis = supervision_log.digest(
            {
                "range_id": "terminal-range-1234",
                "authority": authority,
                "request_text_sha256": entry["request_text_sha256"],
                "initial_tracker_sha256": tracker_sha256,
                "initial_tracker_structure_sha256": tracker_structure_sha256,
                "initial_tracker_blocks": sorted(tracker_blocks),
                "initial_range_intent": "full-tracker",
                "initial_explicit_blocks": [],
                "mission_identity": mission_identity,
            }
        )
        policy["implementation_range"] = {
            "schema_version": 1,
            "kind": "implementation-range-binding",
            "range_id": "terminal-range-1234",
            "genesis_sha256": genesis,
            "authority": authority,
            "mission_identity": mission_identity,
            "range_intent": "full-tracker",
            "explicit_blocks": [],
            "tracker_path": str(tracker_path),
            "tracker_sha256": tracker_sha256,
            "tracker_structure_sha256": tracker_structure_sha256,
            "tracker_blocks": sorted(tracker_blocks),
            "history": [entry],
            "history_head_sha256": entry["entry_sha256"],
        }
        policy["owner_root_history_required"] = True
        policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(policy)
        )
        supervision_log.atomic_json(directory / "policy.json", policy)
        policy_record = {
            "schema_version": 1,
            "record_id": "POLICY-1",
            "timestamp": supervision_log.utc_now(),
            "kind": "policy-init",
            "policy": policy,
            "previous_record_sha256": None,
        }
        policy_record["record_sha256"] = supervision_log.digest(policy_record)
        (directory / "policy-history.jsonl").write_bytes(
            supervision_log.canonical(policy_record) + b"\n"
        )
        supervision_log.atomic_json(
            directory / supervision_log.EVENT_LEDGER_ANCHOR_NAME,
            supervision_log.event_ledger_anchor([]),
        )
        descriptor = os.open(
            directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            supervision_log.ensure_owner_root_history_at(descriptor)
        finally:
            os.close(descriptor)
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
            "capability_reconciliation_reviewer_id": "base-terminal-1234",
            "capability_reconciliation_implementation_owner_id": TARGET,
            "capability_reconciliation_revision": "c" * 40,
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
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

    def test_terminal_delivery_is_default_without_enabling_routine_email(self) -> None:
        policy = supervision_log.default_policy(init_args())
        self.assertTrue(policy["reports"]["terminal"]["enabled"])
        self.assertTrue(policy["permissions"]["gmail_self_notification"])
        self.assertTrue(
            policy["notifications"]["gmail"]["terminal_report_enabled"]
        )
        self.assertFalse(policy["notifications"]["gmail"]["enabled"])

        args = supervision_log.parser().parse_args(
            [
                "bind",
                "--target-thread",
                TARGET,
                "--gmail-terminal-reply-message-id",
                "gmail-seed-terminal",
                "--gmail-terminal-project-key",
                "Terminal",
                "--gmail-terminal-subject",
                "Codex Tracker Supervision - Terminal",
            ]
        )
        with (
            mock.patch.object(
                supervision_log,
                "load_policy",
                return_value=(Path("/tmp/terminal-default"), policy),
            ),
            mock.patch.object(supervision_log, "write_policy_version"),
            redirect_stdout(io.StringIO()),
        ):
            supervision_log.cmd_bind(args)
        gmail = policy["notifications"]["gmail"]
        self.assertTrue(gmail["terminal_report_enabled"])
        self.assertFalse(gmail["enabled"])
        self.assertEqual(gmail["reply_message_id"], "gmail-seed-terminal")

    def test_missing_terminal_email_binding_is_an_explicit_completion_action(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_root(root, bind_gmail=False)
            gate_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_state="completed",
                source_record="EVT-000002",
                state_fingerprint=FINGERPRINT,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_lifecycle_gate(gate_args)
            gate = json.loads(output.getvalue())
            self.assertTrue(gate["completion_permitted"])
            self.assertFalse(gate["supervision_pause_permitted"])
            self.assertEqual(
                gate["completion_action"], "bind-terminal-report-email-lane"
            )
            prepare_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "default bound primary Gmail lane",
            ):
                supervision_log.cmd_terminal_report_prepare(prepare_args)

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

    def append_in_progress_lifecycle(self, root: Path) -> None:
        directory = root / TARGET
        policy = supervision_log.read_json(directory / "policy.json")
        current = supervision_log.events(directory / "events.jsonl")
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": f"EVT-{len(current) + 1:06d}",
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": TARGET,
                "kind": "lifecycle",
                "model": "gpt-5.6-terra",
                "reasoning": "max",
                "state_fingerprint": "state-reopened-terminal-1234",
                "status": "in-progress",
                "severity": "info",
                "category": "implementation-lifecycle",
                "summary": "Later current work reopened the implementation.",
                "evidence": ["later-work-start"],
                "policy_sha256": policy["policy_sha256"],
            },
        )

    def deliver_reports(
        self, root: Path
    ) -> tuple[dict[str, object], dict[str, object]]:
        prepared, _review, verified = self.finalized_reports(root)
        policy = supervision_log.read_json(root / TARGET / "policy.json")
        args = argparse.Namespace(
            root=str(root),
            target_thread=TARGET,
            report_set_id=prepared["report_set_id"],
            gmail_readback_base64=self.encoded_gmail_readback(
                verified=verified, policy=policy
            ),
        )
        with redirect_stdout(io.StringIO()):
            supervision_log.cmd_terminal_report_delivery(args)
        return prepared, verified

    def test_terminal_prepare_requires_a_current_completed_range(self) -> None:
        policy = supervision_log.default_policy(init_args())
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "canonical implementation range",
        ):
            supervision_log.require_current_terminal_completion(
                directory=Path("/tmp/terminal-range-missing"),
                policy=policy,
                policy_snapshot=(1, 1, 1, 1),
                all_events=[],
                event_snapshot=None,
                directory_snapshot=(1, 1, 1, 1),
                lifecycle_record_id="EVT-000001",
            )

    def test_delivery_rejects_changed_bytes_without_provider_review_provenance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _review, verified = self.finalized_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            receipt = json.loads(
                base64.b64decode(
                    self.encoded_gmail_readback(
                        verified=verified, policy=policy
                    )
                )
            )
            receipt["attachments"][0]["attachment_id"] = "fake1"
            receipt["attachments"][1]["attachment_id"] = "fake2"
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
                "provider-output provenance",
            ):
                supervision_log.cmd_terminal_report_delivery(args)

    def test_delivery_rejects_when_current_lifecycle_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _review, verified = self.finalized_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            self.append_in_progress_lifecycle(root)
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id=prepared["report_set_id"],
                gmail_readback_base64=self.encoded_gmail_readback(
                    verified=verified, policy=policy
                ),
            )
            with self.assertRaises(supervision_log.SupervisionLogError):
                supervision_log.cmd_terminal_report_delivery(args)
            self.assertFalse(
                any(
                    item.get("category")
                    == supervision_log.TERMINAL_REPORT_DELIVERY_CATEGORY
                    for item in supervision_log.events(
                        root / TARGET / "events.jsonl"
                    )
                )
            )

    def test_shutdown_rejects_an_automation_owned_by_another_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _verified = self.deliver_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            expected = supervision_log.expected_terminal_automation_owners(policy)
            automation_root = root / "automations"
            write_automation_owners(automation_root, expected)
            automation_id = next(iter(expected))
            expected_owner = expected[automation_id]
            config = automation_root / automation_id / "automation.toml"
            config.write_text(
                config.read_text().replace(
                    f'target_thread_id = "{expected_owner}"',
                    'target_thread_id = "unrelated-target-1234"',
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
            )
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ), self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "owner target differs"
            ):
                supervision_log.cmd_terminal_shutdown(args)

    def test_shutdown_rejects_when_current_lifecycle_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _verified = self.deliver_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            expected = supervision_log.expected_terminal_automation_owners(policy)
            automation_root = root / "automations"
            write_automation_owners(automation_root, expected)
            self.append_in_progress_lifecycle(root)
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
            )
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ), self.assertRaises(supervision_log.SupervisionLogError):
                supervision_log.cmd_terminal_shutdown(args)
            self.assertFalse(
                any(
                    item.get("category")
                    == supervision_log.TERMINAL_SHUTDOWN_CATEGORY
                    for item in supervision_log.events(
                        root / TARGET / "events.jsonl"
                    )
                )
            )

    def test_shutdown_corrects_owner_drift_during_receipt_append(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _verified = self.deliver_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            expected = supervision_log.expected_terminal_automation_owners(policy)
            automation_root = root / "automations"
            write_automation_owners(automation_root, expected)
            changed_config = automation_root / next(iter(expected)) / "automation.toml"
            original = supervision_log.terminal_automation_owner_states
            calls = 0

            def change_after_locked_read(*arguments, **keywords):
                nonlocal calls
                calls += 1
                result = original(*arguments, **keywords)
                if calls == 2:
                    changed_config.write_text(
                        changed_config.read_text().replace(
                            'status = "PAUSED"', 'status = "ACTIVE"'
                        ),
                        encoding="utf-8",
                    )
                return result

            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                lifecycle_record="EVT-000002",
                report_set_id=prepared["report_set_id"],
            )
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ), mock.patch.object(
                supervision_log,
                "terminal_automation_owner_states",
                side_effect=change_after_locked_read,
            ), self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "changed during shutdown append",
            ):
                supervision_log.cmd_terminal_shutdown(args)
            recorded = supervision_log.events(root / TARGET / "events.jsonl")
            source = [
                item
                for item in recorded
                if item.get("category")
                == supervision_log.TERMINAL_SHUTDOWN_CATEGORY
            ]
            corrections = [
                item
                for item in recorded
                if item.get("category")
                == supervision_log.TERMINAL_SHUTDOWN_REJECTED_CATEGORY
            ]
            self.assertEqual(len(source), 1)
            self.assertEqual(len(corrections), 1)
            self.assertEqual(
                corrections[0]["supersedes_record_id"], source[0]["record_id"]
            )
            status_args = argparse.Namespace(root=str(root), target_thread=TARGET)
            status_output = io.StringIO()
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ), redirect_stdout(status_output):
                supervision_log.cmd_status(status_args)
            self.assertIsNone(
                json.loads(status_output.getvalue())["last_terminal_shutdown"]
            )

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
                gmail_readback_base64=self.encoded_gmail_readback(
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
                automation_root,
                supervision_log.expected_terminal_automation_owners(
                    supervision_log.read_json(root / TARGET / "policy.json")
                ),
            )
            shutdown_output = io.StringIO()
            with mock.patch.object(
                supervision_log, "CODEX_AUTOMATIONS_ROOT", automation_root
            ):
                with redirect_stdout(shutdown_output):
                    supervision_log.cmd_terminal_shutdown(shutdown)
            shutdown_result = json.loads(shutdown_output.getvalue())
            self.assertFalse(shutdown_result["duplicate"])
            expected_owners = supervision_log.expected_terminal_automation_owners(
                supervision_log.read_json(root / TARGET / "policy.json")
            )
            self.assertEqual(
                {
                    automation_id: state["target_thread_id"]
                    for automation_id, state in shutdown_result["record"][
                        "automation_states"
                    ].items()
                },
                expected_owners,
            )

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
            encoded = self.encoded_gmail_readback(
                verified=verified, policy=policy
            )
            receipt = json.loads(base64.b64decode(encoded))
            receipt["attachments"][0]["sha256"] = "0" * 64
            self.resign_provider_review(
                receipt, policy=policy, verified=verified
            )
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

    def test_delivery_rejects_duplicate_provider_attachment_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _review, verified = self.finalized_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            receipt = json.loads(
                base64.b64decode(
                    self.encoded_gmail_readback(
                        verified=verified, policy=policy
                    )
                )
            )
            receipt["attachments"][1]["attachment_id"] = receipt["attachments"][0][
                "attachment_id"
            ]
            self.resign_provider_review(
                receipt, policy=policy, verified=verified
            )
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
                "repeats an attachment ID",
            ):
                supervision_log.cmd_terminal_report_delivery(args)

    def test_delivery_rejects_unowned_message_or_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared, _review, verified = self.finalized_reports(root)
            policy = supervision_log.read_json(root / TARGET / "policy.json")
            encoded = self.encoded_gmail_readback(
                verified=verified, policy=policy
            )
            receipt = json.loads(base64.b64decode(encoded))
            sent = receipt["sent_message"]
            raw = base64.urlsafe_b64decode(sent["raw_mime_base64"])
            message = BytesParser(policy=email_policy.default).parsebytes(raw)
            del message["In-Reply-To"]
            del message["References"]
            sent["raw_mime_base64"] = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()
            self.resign_provider_review(
                receipt, policy=policy, verified=verified
            )
            args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_set_id=prepared["report_set_id"],
                gmail_readback_base64=base64.b64encode(
                    json.dumps(receipt, separators=(",", ":")).encode()
                ).decode(),
            )
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "not a reply to the seed"
            ):
                supervision_log.cmd_terminal_report_delivery(args)

            receipt = json.loads(base64.b64decode(encoded))
            receipt["attachments"][0]["owner_message_id"] = "another-gmail-message"
            self.resign_provider_review(
                receipt, policy=policy, verified=verified
            )
            args.gmail_readback_base64 = base64.b64encode(
                json.dumps(receipt, separators=(",", ":")).encode()
            ).decode()
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "attachment owner differs"
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
