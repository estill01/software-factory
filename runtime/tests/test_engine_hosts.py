from __future__ import annotations

import concurrent.futures
import json
import urllib.request
from pathlib import Path

import pytest

from software_factory.api import APIServer, FactoryAPI
from software_factory.bootstrap import open_runtime
from software_factory.engine import MAX_EVENT_PAGE, MissionSubmission
from software_factory.errors import StoreError
from software_factory.hosts import EmbeddedFactoryHost, StandaloneFactoryService


def submission(*, objective: str = "Produce one verified capability") -> MissionSubmission:
    return MissionSubmission(
        idempotency_key="submission-1",
        title="Bounded mission",
        objective=objective,
        resource_limits={"max_parallel": 2},
    )


def test_embedded_and_service_hosts_share_identity_state_events_and_outcome(
    tmp_path: Path,
) -> None:
    first_runtime = open_runtime(tmp_path / "factory")
    embedded = EmbeddedFactoryHost(first_runtime.engine)
    started = embedded.start(submission())
    assert started.duplicate is False
    assert embedded.shape.provider_process_owner is False

    restarted_runtime = open_runtime(tmp_path / "factory")
    service = StandaloneFactoryService(restarted_runtime.engine)
    assert service.shape.provider_process_owner is True
    assert service.status(started.mission_id) == embedded.status(started.mission_id)
    assert service.continue_mission(started.mission_id) == embedded.continue_mission(
        started.mission_id
    )
    assert service.outcome(started.mission_id) == embedded.outcome(started.mission_id)
    assert service.outcome(started.mission_id).terminal is False

    events = service.events(started.mission_id, limit=10)
    assert [event.event_type for event in events] == [
        "mission.created",
        "engine.mission_submitted",
    ]
    assert embedded.events(started.mission_id, after_sequence=events[0].sequence) == events[1:]

    cancelled = service.cancel(started.mission_id, reason="bounded caller cancellation")
    assert cancelled.status == "cancelled_by_authority"
    transferred_runtime = open_runtime(tmp_path / "factory")
    transferred = EmbeddedFactoryHost(transferred_runtime.engine)
    assert transferred.status(started.mission_id).next_action == {
        "posture": "cancelled",
        "action": "none",
        "reason": "mission_cancelled_by_authority",
    }
    assert transferred.outcome(started.mission_id).disposition == "cancelled"
    assert transferred.outcome(started.mission_id).terminal is True


def test_submission_is_durable_concurrent_idempotent_and_collision_safe(
    tmp_path: Path,
) -> None:
    runtime = open_runtime(tmp_path / "factory")

    def start() -> str:
        return runtime.engine.start(submission()).mission_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        mission_ids = list(pool.map(lambda _index: start(), range(2)))
    assert len(set(mission_ids)) == 1
    assert runtime.store.scalar("SELECT COUNT(*) FROM missions") == 1
    assert runtime.store.scalar("SELECT COUNT(*) FROM engine_submissions_v2") == 1

    restarted = open_runtime(tmp_path / "factory")
    duplicate = restarted.engine.start(submission())
    assert duplicate.mission_id == mission_ids[0]
    assert duplicate.duplicate is True
    with pytest.raises(StoreError, match="different mission request"):
        restarted.engine.start(submission(objective="A different mission"))
    assert restarted.store.scalar("SELECT COUNT(*) FROM missions") == 1


def test_service_json_boundary_is_thin_typed_and_bounded(tmp_path: Path) -> None:
    runtime = open_runtime(tmp_path / "factory")
    service = StandaloneFactoryService(runtime.engine)
    started = service.invoke(
        "start",
        {
            "idempotency_key": "service-submission",
            "title": "Service mission",
            "objective": "Prove the service boundary",
        },
    )
    mission_id = str(started["mission_id"])
    status = service.invoke("status", {"mission_id": mission_id})
    assert status["mission_id"] == mission_id
    assert service.invoke("continue", {"mission_id": mission_id}) == status
    event_page = service.invoke("events", {"mission_id": mission_id, "limit": 1})
    assert len(event_page["events"]) == 1
    with pytest.raises(ValueError, match="between 1"):
        service.events(mission_id, limit=MAX_EVENT_PAGE + 1)
    with pytest.raises(ValueError, match="unsupported"):
        service.invoke("launch_provider", {"mission_id": mission_id})


def test_loopback_service_api_exposes_the_same_engine_contract(tmp_path: Path) -> None:
    runtime = open_runtime(tmp_path / "factory")
    service = StandaloneFactoryService(runtime.engine)
    server = APIServer(
        FactoryAPI(
            runtime.store,
            runtime.core.advanced,
            reporting=runtime.core.reporting,
            engine_service=service,
        )
    )
    server.start()
    try:
        host, port = server.address
        start_request = urllib.request.Request(
            f"http://{host}:{port}/api/engine/start",
            data=json.dumps(
                {
                    "idempotency_key": "http-submission",
                    "title": "HTTP mission",
                    "objective": "Prove the loopback service facade",
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(start_request, timeout=5) as response:
            started = json.loads(response.read())
        status_request = urllib.request.Request(
            f"http://{host}:{port}/api/engine/status",
            data=json.dumps({"mission_id": started["mission_id"]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(status_request, timeout=5) as response:
            wire_status = json.loads(response.read())
        assert wire_status == service.invoke("status", {"mission_id": started["mission_id"]})
    finally:
        server.close()
