from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import supervision_log
import weekly_report


TARGET = "target-1234"


def event(
    sequence: int,
    timestamp: str,
    *,
    kind: str = "check",
    category: str = "",
    status: str = "no-intervention",
    model: str = "gpt-5.6-terra",
    reasoning: str = "max",
    block: str = "1",
    incident_id: str | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "record_id": f"EVT-{sequence:06d}",
        "timestamp": timestamp,
        "target_thread_id": TARGET,
        "kind": kind,
        "category": category,
        "status": status,
        "severity": "info",
        "model": model,
        "reasoning": reasoning,
        "active_block": block,
        "summary": f"Synthetic {kind} record {sequence}.",
        "action": "",
        "resolution": "",
        "notice_disposition": "",
        "evidence": [],
    }
    if incident_id:
        value["incident_id"] = incident_id
    return value


def fixture_events() -> list[dict[str, object]]:
    return [
        event(1, "2026-08-01T00:00:00+00:00"),
        event(
            2,
            "2026-08-01T01:00:00+00:00",
            kind="escalation",
            category="changed-state-review",
            status="escalated",
            model="gpt-5.6-terra",
        ),
        event(
            3,
            "2026-08-01T02:00:00+00:00",
            kind="check",
            category="semantic-base-review",
            model="gpt-5.6-sol",
            reasoning="xhigh",
        ),
        event(
            4,
            "2026-08-01T03:00:00+00:00",
            kind="incident",
            category="execution-economy",
            status="detected",
            model="gpt-5.6-sol",
            reasoning="max",
            incident_id="INC-20260801-TEST01",
        ),
        event(
            5,
            "2026-08-01T05:00:00+00:00",
            kind="resolution",
            category="correction-effectiveness",
            status="corrected",
            model="gpt-5.6-sol",
            reasoning="max",
            incident_id="INC-20260801-TEST01",
        ),
        event(
            6,
            "2026-08-02T00:00:00+00:00",
            kind="meta-review",
            category="supervisor-effectiveness",
            status="no-intervention",
            model="gpt-5.6-sol",
            reasoning="max",
            block="2",
        ),
        event(
            7,
            "2026-08-02T02:00:00+00:00",
            kind="roundup",
            category="scheduled-pacific",
            status="sent",
            model="gpt-5.6-sol",
            reasoning="xhigh",
            block="2",
        ),
    ]


def fixture_review(report_id: str, source_root: str) -> dict[str, object]:
    sections = {}
    for section in weekly_report.REVIEW_SECTIONS:
        sections[section] = [
            {
                "title": section.replace("_", " ").title(),
                "assessment": "The bounded records support one evidence-linked operational observation without claiming patent quality.",
                "evidence": ["EVT-000001"],
            }
        ]
    return {
        "schema_version": 1,
        "kind": "supervision-weekly-review-cognitive-review",
        "report_id": report_id,
        "source_root": source_root,
        "reviewer_method": "bounded-full-window-cognitive-review",
        "overall_posture": "effective-with-findings",
        "headline": "Supervision found one bounded issue and verified correction",
        "executive_assessment": "The week shows active monitoring, one detected issue, and a terminal correction. The sample is too small for a causal trend claim.",
        "sections": sections,
    }


class WeeklyMetricsTests(unittest.TestCase):
    def build(self) -> tuple[dict[str, object], dict[str, object]]:
        return weekly_report.build_metrics(
            target_label="Main",
            target_thread_id=TARGET,
            start=dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc),
            end=dt.datetime(2026, 8, 3, tzinfo=dt.timezone.utc),
            timezone_name="America/Los_Angeles",
            all_events=fixture_events(),
            policy_history=[],
            current_policy={"policy_sha256": "a" * 64},
            projection_inventory={"incident_reports": {"count": 1}},
        )

    def test_metrics_use_explicit_denominators_and_terminal_heads(self) -> None:
        metrics, packet = self.build()

        self.assertEqual(metrics["headline"]["recorded_events"], 7)
        self.assertEqual(metrics["headline"]["incidents_opened"], 1)
        self.assertEqual(metrics["headline"]["incidents_terminal"], 1)
        self.assertEqual(metrics["headline"]["incidents_open_at_end"], 0)
        self.assertEqual(
            metrics["rates"]["incidents_per_100_changed_state_routes"], 100.0
        )
        self.assertEqual(packet["metrics"], metrics)
        self.assertEqual(packet["source_root"], metrics["source"]["source_root"])
        self.assertEqual(
            metrics["availability"]["core_heartbeats_scheduled_active_hours"],
            48.0,
        )
        self.assertFalse(
            metrics["availability"]["continuous_process_uptime_measured"]
        )
        resources = metrics["resource_estimate"]
        self.assertEqual(
            resources["totals"]["recorded_model_attributed_events"], 7
        )
        self.assertGreater(resources["totals"]["estimated_tokens_base"], 0)
        self.assertGreater(resources["totals"]["projected_cost_usd_base"], 0)
        self.assertFalse(resources["actual_provider_tokens_available"])
        self.assertIn("not provider token telemetry", resources["disclaimer"])

    def test_availability_uses_explicit_pause_resume_only(self) -> None:
        events = fixture_events()
        events.extend(
            [
                event(
                    8,
                    "2026-08-01T12:00:00+00:00",
                    kind="policy-change",
                    category="stop-condition-pause",
                    status="paused",
                ),
                event(
                    9,
                    "2026-08-02T00:00:00+00:00",
                    kind="policy-change",
                    category="supervision-resume",
                    status="resumed",
                ),
            ]
        )
        value = weekly_report.availability_metrics(
            sorted(events, key=weekly_report.record_time),
            dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc),
            dt.datetime(2026, 8, 3, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(value["core_heartbeats_scheduled_active_hours"], 36.0)
        self.assertEqual(value["core_heartbeats_explicitly_paused_hours"], 12.0)
        self.assertEqual(len(value["explicit_pause_intervals"]), 1)

    def test_pricing_profile_and_estimate_are_deterministic(self) -> None:
        profile = weekly_report.load_pricing_profile()
        first = weekly_report.resource_estimate(
            fixture_events(),
            weekly_report.ZoneInfo("America/Los_Angeles"),
            profile,
        )
        second = weekly_report.resource_estimate(
            fixture_events(),
            weekly_report.ZoneInfo("America/Los_Angeles"),
            profile,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["pricing_profile_sha256"], profile["profile_sha256"])
        self.assertNotEqual(
            first["totals"]["estimated_tokens_low"],
            first["totals"]["estimated_tokens_high"],
        )

    def test_review_rejects_unknown_evidence_and_local_paths(self) -> None:
        metrics, _packet = self.build()
        review = fixture_review(metrics["report_id"], metrics["source"]["source_root"])
        review["sections"]["caught_and_prevented"][0]["evidence"] = ["EVT-999999"]
        with self.assertRaisesRegex(weekly_report.WeeklyReportError, "unknown records"):
            weekly_report.validate_review(
                review,
                report_id=metrics["report_id"],
                source_root=metrics["source"]["source_root"],
                record_ids={item["record_id"] for item in fixture_events()},
            )

        review = fixture_review(metrics["report_id"], metrics["source"]["source_root"])
        review["executive_assessment"] = "Read /Users/example/private output."
        with self.assertRaisesRegex(weekly_report.WeeklyReportError, "local path"):
            weekly_report.validate_review(
                review,
                report_id=metrics["report_id"],
                source_root=metrics["source"]["source_root"],
                record_ids={item["record_id"] for item in fixture_events()},
            )

    def test_pdf_renders_with_charts_and_line_items(self) -> None:
        metrics, _packet = self.build()
        review = weekly_report.validate_review(
            fixture_review(metrics["report_id"], metrics["source"]["source_root"]),
            report_id=metrics["report_id"],
            source_root=metrics["source"]["source_root"],
            record_ids={item["record_id"] for item in fixture_events()},
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.pdf"
            weekly_report.render_pdf(output, metrics, review)
            from pypdf import PdfReader

            reader = PdfReader(str(output))
            self.assertGreaterEqual(len(reader.pages), 4)
            self.assertIn(
                "SUPERVISION WEEKLY REVIEW", reader.pages[0].extract_text()
            )


class WeeklyCommandTests(unittest.TestCase):
    def init_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            target_thread=TARGET,
            target_label="Main",
            watcher_thread="watcher-1234",
            reviewer_thread="reviewer-1234",
            base_reviewer_thread="base-1234",
            notice_reviewer_thread="notice-1234",
            fix_executor_thread="fixer-1234",
            mission_root=None,
            mission_source_record=None,
            mission_source_class=None,
            mission_source_sha256=None,
        )

    def prepare_root(self, root: Path) -> None:
        directory = root / TARGET
        directory.mkdir(parents=True)
        (directory / "incidents").mkdir()
        (directory / "reviews").mkdir()
        policy = supervision_log.default_policy(self.init_args())
        supervision_log.atomic_json(directory / "policy.json", policy)
        supervision_log.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-1",
                "timestamp": "2026-08-01T00:00:00+00:00",
                "kind": "policy-init",
                "policy": policy,
            },
        )
        for item in fixture_events():
            supervision_log.append_raw(directory / "events.jsonl", item)

    def test_prepare_finalize_and_verify_are_replay_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_root(root)
            prepare_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                start="2026-08-01T00:00:00+00:00",
                end="2026-08-03T00:00:00+00:00",
                days=7,
                since_inception=False,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_weekly_report_prepare(prepare_args)
            prepared = json.loads(output.getvalue())
            metrics = json.loads(Path(prepared["metrics_path"]).read_text())
            review = fixture_review(
                prepared["report_id"], prepared["source_root"]
            )
            encoded = base64.b64encode(
                json.dumps(review, separators=(",", ":")).encode()
            ).decode()
            finalize_args = argparse.Namespace(
                root=str(root),
                target_thread=TARGET,
                report_id=prepared["report_id"],
                review_base64=encoded,
            )
            with redirect_stdout(io.StringIO()):
                supervision_log.cmd_weekly_report_finalize(finalize_args)
            verify_output = io.StringIO()
            with redirect_stdout(verify_output):
                supervision_log.cmd_weekly_report_verify(finalize_args)
            verified = json.loads(verify_output.getvalue())
            self.assertTrue(verified["valid"])
            self.assertGreaterEqual(verified["page_count"], 4)
            self.assertEqual(metrics["source"]["source_root"], prepared["source_root"])
            report_directory = Path(prepared["report_directory"])
            machine = json.loads((report_directory / "report.json").read_text())
            self.assertEqual(machine["metrics"], metrics)
            self.assertEqual(machine["cognitive_review"]["report_id"], prepared["report_id"])
            manifest = json.loads((report_directory / "manifest.json").read_text())
            self.assertIn("report.json", manifest["files"])


if __name__ == "__main__":
    unittest.main()
