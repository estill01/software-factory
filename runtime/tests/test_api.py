from __future__ import annotations

import datetime as dt
import json
import sqlite3
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from software_factory.api import APIServer, FactoryAPI


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT);
            INSERT INTO schema_migrations VALUES(12,'operability');
            CREATE TABLE missions(id TEXT PRIMARY KEY,status TEXT,goal TEXT,created_at TEXT,updated_at TEXT);
            CREATE TABLE work_items(id TEXT PRIMARY KEY,mission_id TEXT,title TEXT,work_type TEXT,planning_status TEXT,execution_status TEXT,qa_status TEXT,acceptance_status TEXT,priority INTEGER,updated_at TEXT);
            CREATE TABLE agent_sessions(id TEXT PRIMARY KEY,provider TEXT,provider_session_id TEXT,intended_role TEXT,observed_status TEXT,current_assignment_id TEXT,last_heartbeat_at TEXT,updated_at TEXT);
            CREATE TABLE executions(id TEXT PRIMARY KEY,mission_id TEXT,work_item_id TEXT,agent_session_id TEXT,status TEXT,provider_key TEXT,attempt_number INTEGER,lease_generation INTEGER,started_at TEXT,completed_at TEXT,created_at TEXT);
            CREATE TABLE supervision_incidents(id TEXT PRIMARY KEY,mission_id TEXT,status TEXT,opened_at TEXT,updated_at TEXT);
            CREATE TABLE active_signal_bundles(id TEXT PRIMARY KEY,mission_id TEXT,activated_at TEXT);
            CREATE TABLE reflections_v2(id TEXT PRIMARY KEY,mission_id TEXT,created_at TEXT);
            CREATE TABLE experiments_v2(id TEXT PRIMARY KEY,mission_id TEXT,created_at TEXT);
            CREATE TABLE immutable_releases_v2(id TEXT PRIMARY KEY,staged_at TEXT);
            CREATE TABLE factory_recovery_cases_v2(id TEXT PRIMARY KEY,opened_at TEXT);
            CREATE TABLE repository_inventories_v2(id TEXT PRIMARY KEY,repository_root TEXT);
            CREATE TABLE cleanup_items_v2(id TEXT PRIMARY KEY,inventory_id TEXT,created_at TEXT);
            CREATE TABLE retained_adaptive_cases(id TEXT PRIMARY KEY,mission_id TEXT,created_at TEXT);
            CREATE TABLE selection_records_v2(id TEXT PRIMARY KEY,mission_id TEXT,created_at TEXT);
            """
        )
        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0012_operability_runtime.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))
        self.connection.execute(
            "INSERT INTO missions VALUES('mission-1','active','ship system','2026-01-01','2026-01-01')"
        )

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


def request_json(url: str, *, method: str = "GET", data: dict[str, Any] | None = None, token: str | None = None) -> tuple[int, dict[str, Any]]:
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_api_binds_only_to_loopback() -> None:
    api = FactoryAPI(TestStore())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="loopback"):
        APIServer(api, host="0.0.0.0")


def test_health_factory_floor_and_html_are_available() -> None:
    api = FactoryAPI(TestStore())  # type: ignore[arg-type]
    server = APIServer(api)
    server.start()
    try:
        host, port = server.address
        base = f"http://{host}:{port}"
        status, health = request_json(base + "/health")
        assert status == 200
        assert health["ok"] is True
        status, floor = request_json(base + "/api/factory-floor")
        assert status == 200
        assert floor["missions"][0]["id"] == "mission-1"
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            html = response.read().decode()
        assert "Software Factory v2" in html
        assert "/api/factory-floor" in html
    finally:
        server.close()


def test_operator_post_requires_bearer_token_and_applies_governed_owner() -> None:
    store = TestStore()
    api = FactoryAPI(store)  # type: ignore[arg-type]
    schedule = api.reporting.create_schedule(
        schedule_type="interval",
        specification={"seconds": 60},
        action={"kind": "tick"},
        next_run_at="2026-01-01T00:00:00Z",
        mission_id="mission-1",
    )
    expires = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat().replace(
        "+00:00", "Z"
    )
    token, _ = api.reporting.issue_operator_token(
        allowed_actions=["pause_schedule"],
        scope={"target_type": "schedule", "target_ids": [schedule["id"]]},
        expires_at=expires,
        mission_id="mission-1",
    )
    server = APIServer(api)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/api/operator-actions"
        payload = {
            "action": "pause_schedule",
            "target_type": "schedule",
            "target_id": schedule["id"],
            "payload": {},
        }
        status, error = request_json(url, method="POST", data=payload)
        assert status == 401
        assert "token" in error["error"]
        status, result = request_json(url, method="POST", data=payload, token=token)
        assert status == 200
        assert result["status"] == "applied"
        assert store.one("SELECT status FROM schedules_v2 WHERE id=?", (schedule["id"],)) == {
            "status": "paused"
        }
    finally:
        server.close()


def test_mission_detail_returns_historical_adaptive_and_selection_records() -> None:
    store = TestStore()
    store.connection.execute(
        "INSERT INTO retained_adaptive_cases VALUES('case-1','mission-1','2026-01-01')"
    )
    store.connection.execute(
        "INSERT INTO selection_records_v2 VALUES('selection-1','mission-1','2026-01-01')"
    )
    api = FactoryAPI(store)  # type: ignore[arg-type]
    detail = api.mission_detail("mission-1")
    assert detail["mission"]["goal"] == "ship system"
    assert detail["adaptive_cases"][0]["id"] == "case-1"
    assert detail["selection_records"][0]["id"] == "selection-1"
