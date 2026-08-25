from __future__ import annotations

import datetime as dt
import http.client
import json
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from software_factory.api import APIServer, FactoryAPI
from software_factory.api_main import read_service_token
from software_factory.bootstrap import open_runtime
from software_factory.database import Database
from software_factory.engine import MissionSubmission
from software_factory.hosts import StandaloneFactoryService
from software_factory.learning import LearningService
from software_factory.utility_contracts import service_api_protocol_root

SERVICE_TOKEN = "sfv2-test-service-token-00000000000000000000000000000000"
WORKFLOW_ROOT = service_api_protocol_root()


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
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    token: str | None = None,
    operator_token: str | None = None,
    workflow_root: str | None = None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if operator_token:
        headers["X-Software-Factory-Operator-Token"] = operator_token
    if workflow_root:
        headers["X-Software-Factory-Workflow-Root"] = workflow_root
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_api_binds_only_to_loopback() -> None:
    api = FactoryAPI(_store())
    with pytest.raises(ValueError, match="loopback"):
        APIServer(api, service_token=SERVICE_TOKEN, host="0.0.0.0")

    with pytest.raises(ValueError, match="32 to 512"):
        APIServer(api, service_token="short")


def test_health_factory_floor_and_html_are_available() -> None:
    api = FactoryAPI(_store())
    server = APIServer(api, service_token=SERVICE_TOKEN)
    server.start()
    try:
        host, port = server.address
        base = f"http://{host}:{port}"
        status, health = request_json(base + "/health")
        assert status == 200
        assert health["ok"] is True
        status, readiness = request_json(base + "/ready")
        assert status == 503
        assert readiness == {"ok": False}
        status, floor = request_json(base + "/api/factory-floor")
        assert status == 401
        assert "token" in floor["error"]
        status, floor = request_json(base + "/api/factory-floor", token="agent-session-1")
        assert status == 401
        status, floor = request_json(base + "/api/factory-floor", token=SERVICE_TOKEN)
        assert status == 200
        assert floor["missions"][0]["id"] == "mission-1"
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            html = response.read().decode()
        assert "Software Factory v2" in html
        assert "/api/factory-floor" in html
        assert "innerHTML" not in html
        assert "textContent" in html
    finally:
        server.close()


def test_operator_post_separates_service_and_one_time_authority_tokens() -> None:
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
    server = APIServer(api, service_token=SERVICE_TOKEN)
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
        status, error = request_json(
            url,
            method="POST",
            data=payload,
            token=SERVICE_TOKEN,
            workflow_root=WORKFLOW_ROOT,
        )
        assert status == 401
        assert "operator" in error["error"]
        status, result = request_json(
            url,
            method="POST",
            data=payload,
            token=SERVICE_TOKEN,
            operator_token=token,
            workflow_root=WORKFLOW_ROOT,
        )
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
    assert detail["mission"]["title"] == "Ship system"
    assert "objective" not in detail["mission"]
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
    assert "canonical" not in floor["reflections"][0]
    assert floor["reflections"][0]["currentness_root"]


def test_factory_floor_omits_authority_secrets_and_unbounded_content() -> None:
    store = _store()
    secret = "operator-secret-that-must-not-leak"
    with store.transaction() as db:
        db.execute(
            """UPDATE missions SET objective=?,authority_root=?,resource_limits_json=?
               WHERE id=?""",
            (secret, secret, json.dumps({"credential": secret}), "mission-1"),
        )
    wire = json.dumps(FactoryAPI(store).factory_floor("mission-1"), sort_keys=True)
    assert secret not in wire
    assert "authority_root" not in wire
    assert "resource_limits_json" not in wire


def test_api_rejects_oversized_requests_and_unregistered_engine_effects(
    tmp_path: Path,
) -> None:
    runtime = open_runtime(tmp_path / "factory")
    api = FactoryAPI(
        runtime.store,
        runtime.core.advanced,
        reporting=runtime.core.reporting,
        engine_service=StandaloneFactoryService(runtime.engine),
    )
    server = APIServer(api, service_token=SERVICE_TOKEN)
    server.start()
    try:
        host, port = server.address
        base = f"http://{host}:{port}"
        status, error = request_json(
            base + "/api/engine/start",
            method="POST",
            data={"idempotency_key": "stale-client"},
            token=SERVICE_TOKEN,
            workflow_root="0" * 64,
        )
        assert status == 409
        assert "workflow root" in error["error"]
        status, error = request_json(
            base + "/api/engine/cancel",
            method="POST",
            data={"mission_id": "mission-1"},
            token=SERVICE_TOKEN,
            workflow_root=WORKFLOW_ROOT,
        )
        assert status == 400
        assert "not exposed" in error["error"]
        status, error = request_json(
            base + "/api/engine/complete",
            method="POST",
            data={"mission_id": "mission-1"},
            token=SERVICE_TOKEN,
            workflow_root=WORKFLOW_ROOT,
        )
        assert status == 400
        assert "not exposed" in error["error"]
        status, error = request_json(
            base + "/api/engine/start",
            method="POST",
            data={"command": ["sh", "-c", "arbitrary"]},
            token=SERVICE_TOKEN,
            workflow_root=WORKFLOW_ROOT,
        )
        assert status == 400
        assert "fields are invalid" in error["error"]
        connection = http.client.HTTPConnection(host, port, timeout=5)
        connection.putrequest("POST", "/api/engine/start")
        connection.putheader("Authorization", f"Bearer {SERVICE_TOKEN}")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("X-Software-Factory-Workflow-Root", WORKFLOW_ROOT)
        connection.putheader("Content-Length", str(1024 * 1024 + 1))
        connection.endheaders()
        response = connection.getresponse()
        error = json.loads(response.read())
        connection.close()
        assert response.status == 400
        assert "one megabyte" in error["error"]
    finally:
        server.close()


def test_server_shutdown_is_idempotent_and_restart_is_rejected() -> None:
    server = APIServer(FactoryAPI(_store()), service_token=SERVICE_TOKEN)
    server.start()
    server.start()
    server.close()
    server.close()
    with pytest.raises(RuntimeError, match="closed"):
        server.start()


def test_service_token_file_must_be_private_regular_and_not_a_symlink(tmp_path: Path) -> None:
    token_file = tmp_path / "service-token"
    token_file.write_text(SERVICE_TOKEN + "\n", encoding="utf-8")
    token_file.chmod(0o600)
    assert read_service_token(str(token_file)) == SERVICE_TOKEN
    token_file.chmod(0o640)
    with pytest.raises(ValueError, match="group or world"):
        read_service_token(str(token_file))
    token_file.chmod(0o600)
    link = tmp_path / "token-link"
    link.symlink_to(token_file)
    with pytest.raises(ValueError, match="non-symlink"):
        read_service_token(str(link))


def test_mission_cancellation_requires_distinct_governed_operator_authority(
    tmp_path: Path,
) -> None:
    runtime = open_runtime(tmp_path / "factory")
    service = StandaloneFactoryService(runtime.engine)
    mission_id = service.start(
        MissionSubmission("operator-cancel", "Operator cancellation", "Prove separate authority")
    ).mission_id
    expires = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    operator_token, _ = runtime.core.reporting.issue_operator_token(
        allowed_actions=["cancel_mission"],
        scope={"target_type": "mission", "target_ids": [mission_id]},
        expires_at=expires,
        mission_id=mission_id,
    )
    server = APIServer(
        FactoryAPI(
            runtime.store,
            runtime.core.advanced,
            reporting=runtime.core.reporting,
            engine_service=service,
        ),
        service_token=SERVICE_TOKEN,
    )
    server.start()
    try:
        host, port = server.address
        status, result = request_json(
            f"http://{host}:{port}/api/operator-actions",
            method="POST",
            data={
                "action": "cancel_mission",
                "target_type": "mission",
                "target_id": mission_id,
                "payload": {"reason": "bounded operator cancellation"},
            },
            token=SERVICE_TOKEN,
            operator_token=operator_token,
            workflow_root=WORKFLOW_ROOT,
        )
        assert status == 200
        assert result["status"] == "applied"
        assert service.status(mission_id).status == "cancelled_by_authority"
    finally:
        server.close()
