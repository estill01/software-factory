from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.errors import InvalidTransition, StoreError
from software_factory.reporting import FileNotificationAdapter, ReportingService


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0012_operability_runtime.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))

    @contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        self.connection.execute(f"BEGIN {mode}")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        if row is None:
            if required:
                raise LookupError(sql)
            return None
        return dict(row)

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, parameters).fetchall()]


def service() -> ReportingService:
    return ReportingService(TestStore())  # type: ignore[arg-type]


class FailingAdapter:
    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]:
        raise OSError("provider unavailable")


def future(seconds: int = 3600) -> str:
    return (
        (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
    )


def test_interval_schedule_advances_without_manual_resume() -> None:
    reporting = service()
    schedule = reporting.create_schedule(
        schedule_type="interval",
        specification={"seconds": 60},
        action={"kind": "controller_tick"},
        next_run_at="2026-01-01T00:00:00Z",
    )
    assert reporting.due_schedules(now="2026-01-01T00:01:00Z")[0]["id"] == schedule["id"]
    advanced = reporting.mark_schedule_run(
        schedule["id"], succeeded=True, completed_at="2026-01-01T00:01:00Z"
    )
    assert advanced["status"] == "active"
    assert advanced["next_run_at"] == "2026-01-01T00:02:00Z"


def test_report_generation_is_content_addressed_and_writes_pdf(tmp_path: Path) -> None:
    reporting = service()
    report = reporting.generate_report(
        report_type="checkpoint",
        source_type="mission",
        source_id="mission-1",
        content={
            "status": "executing",
            "progress": {"accepted": 4, "remaining": 2},
            "incidents": [],
        },
        output_directory=tmp_path,
        title="Factory checkpoint",
    )
    duplicate = reporting.generate_report(
        report_type="checkpoint",
        source_type="mission",
        source_id="mission-1",
        content={
            "status": "executing",
            "progress": {"accepted": 4, "remaining": 2},
            "incidents": [],
        },
        output_directory=tmp_path,
        title="Factory checkpoint",
    )
    assert duplicate["id"] == report["id"]
    pdf = Path(report["pdf_path"])
    assert pdf.read_bytes().startswith(b"%PDF-1.4")
    assert "# Factory checkpoint" in report["markdown_content"]


def test_notification_outbox_deduplicates_delivers_and_records_readback(
    tmp_path: Path,
) -> None:
    reporting = service()
    destination = tmp_path / "delivered.json"
    queued = reporting.queue_notification(
        channel="file",
        destination=str(destination),
        subject="Mission checkpoint",
        body_text="Work continues.",
        dedupe_material={"mission": "mission-1", "checkpoint": 3},
    )
    duplicate = reporting.queue_notification(
        channel="file",
        destination=str(destination),
        subject="Mission checkpoint",
        body_text="Work continues.",
        dedupe_material={"mission": "mission-1", "checkpoint": 3},
    )
    assert duplicate["id"] == queued["id"]
    delivered = reporting.dispatch_notification(queued["id"], adapter=FileNotificationAdapter())
    assert delivered["status"] == "delivered"
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["notification_id"] == queued["id"]
    read = reporting.record_readback(queued["id"], readback={"provider": "file", "opened": True})
    assert read["status"] == "read"


def test_failed_notification_retries_with_bounded_budget(tmp_path: Path) -> None:
    reporting = service()
    notification = reporting.queue_notification(
        channel="webhook",
        destination="https://invalid.example.test",
        subject="Incident",
        body_text="A correction is required.",
        max_attempts=2,
    )
    first = reporting.dispatch_notification(notification["id"], adapter=FailingAdapter())
    assert first["status"] == "retry"
    second = reporting.dispatch_notification(notification["id"], adapter=FailingAdapter())
    assert second["status"] == "failed"
    assert second["attempt_count"] == 2
    with pytest.raises(InvalidTransition, match="exhausted"):
        reporting.dispatch_notification(notification["id"], adapter=FailingAdapter())


def test_operator_token_is_scoped_single_use_and_idempotent() -> None:
    reporting = service()
    raw, token = reporting.issue_operator_token(
        allowed_actions=["approve_release"],
        scope={"target_type": "release", "target_ids": ["release-1"]},
        expires_at=future(),
    )
    decision = reporting.accept_operator_action(
        raw,
        action="approve_release",
        target_type="release",
        target_id="release-1",
        payload={"note": "reviewed"},
    )
    duplicate = reporting.store.one(
        "SELECT * FROM operator_decisions_v2 WHERE id=?", (decision["id"],)
    )
    assert duplicate is not None
    assert reporting.store.one(
        "SELECT status,use_count FROM operator_action_tokens_v2 WHERE id=?", (token["id"],)
    ) == {"status": "consumed", "use_count": 1}
    with pytest.raises(StoreError, match="invalid"):
        reporting.accept_operator_action(
            raw,
            action="approve_release",
            target_type="release",
            target_id="release-1",
        )


def test_operator_action_rejects_scope_widening() -> None:
    reporting = service()
    raw, _ = reporting.issue_operator_token(
        allowed_actions=["cancel_work"],
        scope={"target_type": "work_item", "target_ids": ["work-1"]},
        expires_at=future(),
        max_uses=2,
    )
    with pytest.raises(StoreError, match="outside token scope"):
        reporting.accept_operator_action(
            raw,
            action="cancel_work",
            target_type="work_item",
            target_id="work-2",
        )


def test_terminal_shutdown_gate_requires_report_delivery_and_empty_outbox(tmp_path: Path) -> None:
    reporting = service()
    report = reporting.generate_report(
        report_type="terminal",
        source_type="mission",
        source_id="mission-1",
        mission_id="mission-1",
        content={"outcome": "complete"},
        output_directory=tmp_path,
    )
    assert reporting.terminal_delivery_ready("mission-1") is False
    with reporting.store.transaction() as db:
        db.execute("UPDATE reports_v2 SET status='delivered' WHERE id=?", (report["id"],))
    assert reporting.terminal_delivery_ready("mission-1") is True
