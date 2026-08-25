from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from software_factory.api import APIServer, FactoryAPI
from software_factory.database import Database
from software_factory.learning import LearningService


def _store() -> Database:
    temporary_directory = TemporaryDirectory()
    store = Database(Path(temporary_directory.name) / "factory.sqlite3")
    now = "2026-01-01T00:00:00Z"
    with store.transaction() as db:
        db.execute(
            """INSERT INTO missions(
                   id,title,objective,status,autonomy_mode,created_at,updated_at
               ) VALUES(
                   'mission-1','Ship system','ship system','active',
                   'full_autonomous',?,?
               )""",
            (now, now),
        )
    store._test_temporary_directory = temporary_directory  # type: ignore[attr-defined]
    return store


def request_json(
    url: str, *, method: str = "GET", data: dict[str, Any] | None = None, token: str | None = None
) -> tuple[int, dict[str, Any]]:
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
    api = FactoryAPI(_store())
    with pytest.raises(ValueError, match="loopback"):
        APIServer(api, host="0.0.0.0")


def test_health_factory_floor_and_html_are_available() -> None:
    api = FactoryAPI(_store())
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
    store = _store()
    api = FactoryAPI(store)
    schedule = api.reporting.create_schedule(
        schedule_type="interval",
        specification={"seconds": 60},
        action={"kind": "tick"},
        next_run_at="2026-01-01T00:00:00Z",
        mission_id="mission-1",
    )
    expires = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
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


def test_mission_detail_returns_canonical_strategy_and_selection_records() -> None:
    store = _store()
    api = FactoryAPI(store)
    selection = api.advanced.evolution.consider_selection(
        mission_id="mission-1",
        selection_group="runtime",
        selection_type="strategy",
        candidate_key="strategy-a",
        candidate={"name": "strategy-a"},
        evidence={"source": "focused-test"},
        expected_value={"progress": True},
    )
    detail = api.mission_detail("mission-1")
    assert detail["mission"]["objective"] == "ship system"
    assert detail["strategy_outcomes"] == []
    assert detail["selection_records"][0]["id"] == selection["id"]


def test_factory_floor_projects_canonical_librsi_reflections() -> None:
    store = _store()
    learning = LearningService(store)
    reflection = learning.create_reflection(
        mission_id="mission-1",
        reflection_type="live",
        source_type="execution",
        source_id="execution-1",
        evidence_ids=["evidence-1"],
        observations={"status": "failed"},
        conclusions={"cause": "bounded"},
        confidence=0.7,
    )
    floor = FactoryAPI(store).factory_floor("mission-1")
    assert floor["reflections"][0]["id"] == reflection["id"]
    assert floor["reflections"][0]["semantic_owner"] == "libRSI"
    assert floor["reflections"][0]["canonical"]["record_type"] == "observation"
