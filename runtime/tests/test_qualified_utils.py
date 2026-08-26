from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from software_factory.api import FactoryAPI
from software_factory.bootstrap import open_runtime
from software_factory.engine import (
    CancelResult,
    EventRecord,
    MissionOutcome,
    MissionRef,
    MissionSnapshot,
    MissionSubmission,
)
from software_factory.errors import StoreError
from software_factory.hosts import EmbeddedFactoryHost, StandaloneFactoryService
from software_factory.utility_contracts import (
    QualifiedUtilityRuntime,
    RuntimeIdentity,
    installed_component_root,
    service_api_protocol_root,
)
from software_factory.utility_provenance import QualifiedUtilityPin


@pytest.fixture(scope="module")
def qualified_utilities() -> QualifiedUtilityRuntime:
    embedded = os.environ.get("SFV2_EMBEDDED_CONTRACT_WHEEL")
    manifest = os.environ.get("SFV2_RUNTIME_MANIFEST_WHEEL")
    if not embedded or not manifest:
        pytest.skip("exact qualified utils wheels were not supplied")
    return QualifiedUtilityRuntime.from_wheels(
        embedded_contract_wheel=embedded,
        runtime_manifest_wheel=manifest,
    )


@dataclass
class _ProbeRecord:
    disposition: str | None
    events: list[EventRecord]


class _ContractProbeEngine:
    """Factory-owned deterministic state used only by the shared structural probe."""

    def __init__(self, instance: str):
        self.instance = instance
        self.sequence = 0
        self.records: dict[str, _ProbeRecord] = {}

    def _record(self, mission_id: str) -> _ProbeRecord:
        try:
            return self.records[mission_id]
        except KeyError as exc:
            raise StoreError("unknown probe mission") from exc

    def start(self, submission: MissionSubmission) -> MissionRef:
        self.sequence += 1
        mission_id = f"{self.instance}-{self.sequence}-{submission.idempotency_key}"
        if submission.title == "successful":
            disposition = "succeeded"
        elif submission.title == "failed":
            disposition = "failed"
        else:
            disposition = None
        event = EventRecord(
            sequence=1,
            event_id=f"event-{mission_id}-1",
            event_type="probe.started",
            stream_key="probe",
            subject_type="mission",
            subject_id=mission_id,
            payload={},
            created_at="2026-01-01T00:00:00Z",
        )
        self.records[mission_id] = _ProbeRecord(disposition, [event])
        return MissionRef(mission_id, submission.request_root, False)

    def status(self, mission_id: str) -> MissionSnapshot:
        record = self._record(mission_id)
        status = {
            None: "active",
            "succeeded": "completed",
            "failed": "failed",
            "cancelled": "cancelled_by_authority",
        }[record.disposition]
        return MissionSnapshot(mission_id, status, 1, {}, len(record.events))

    def continue_mission(self, mission_id: str) -> MissionSnapshot:
        return self.status(mission_id)

    def cancel(self, mission_id: str, *, reason: str) -> CancelResult:
        record = self._record(mission_id)
        if record.disposition is None:
            record.disposition = "cancelled"
            record.events.append(
                EventRecord(
                    sequence=2,
                    event_id=f"event-{mission_id}-2",
                    event_type="probe.cancelled",
                    stream_key="probe",
                    subject_type="mission",
                    subject_id=mission_id,
                    payload={"reason": reason},
                    created_at="2026-01-01T00:00:01Z",
                )
            )
        return CancelResult(mission_id, self.status(mission_id).status, 1)

    def outcome(self, mission_id: str) -> MissionOutcome:
        record = self._record(mission_id)
        return MissionOutcome(
            mission_id,
            record.disposition is not None,
            record.disposition,
            None,
            "2026-01-01T00:00:01Z" if record.disposition is not None else None,
        )

    def events(
        self, mission_id: str, *, after_sequence: int = 0, limit: int = 100
    ) -> tuple[EventRecord, ...]:
        record = self._record(mission_id)
        return tuple(record.events[after_sequence : after_sequence + limit])


def _request(key: str, title: str) -> MissionSubmission:
    return MissionSubmission(key, title, "shared structural conformance")


@pytest.mark.parametrize("mode", ["embedded", "service"])
def test_both_factory_host_shapes_pass_exact_shared_structural_contract(
    qualified_utilities: QualifiedUtilityRuntime,
    mode: str,
) -> None:
    shared = qualified_utilities.embedded_contract

    def host_factory(instance: str) -> Any:
        engine = _ContractProbeEngine(f"{mode}-{instance}")
        if mode == "embedded":
            host = EmbeddedFactoryHost(engine)
        else:
            host = StandaloneFactoryService(engine)
        adapter = qualified_utilities.lifecycle_adapter(host, mode=mode)
        assert set(adapter.__dict__) == {"_host", "_contract_module", "contract"}
        return adapter

    fixture = shared.ConformanceFixture(
        host_factory=host_factory,
        successful_request=_request(f"{mode}-success", "successful"),
        failing_request=_request(f"{mode}-failure", "failed"),
        cancellable_request=_request(f"{mode}-cancel", "cancellable"),
    )
    report = shared.assert_lifecycle_conformance(fixture)
    assert report.shape.value == mode
    assert report.scenarios == 3
    assert report.observed_events >= 4


def test_runtime_manifest_is_descriptive_exact_and_non_authoritative(
    qualified_utilities: QualifiedUtilityRuntime,
) -> None:
    component_root = installed_component_root()
    document = qualified_utilities.manifest_document(RuntimeIdentity(component_root))
    parsed = qualified_utilities.runtime_manifest.parse_manifest(document)
    assert parsed.component.name == "software-factory"
    assert parsed.component.content_root.value == component_root
    dependencies = {item.name: item for item in parsed.dependencies}
    protocols = {item.name: item for item in parsed.protocols}
    pin = qualified_utilities.pin.record["packages"]
    assert (
        dependencies["embedded-service-contract"].content_root.value
        == (pin["embedded-service-contract"]["wheel_content_root_sha256"])
    )
    assert (
        dependencies["runtime-manifest"].content_root.value
        == (pin["runtime-manifest"]["wheel_content_root_sha256"])
    )
    assert (
        protocols["software-factory-loopback-service"].schema_root.value
        == service_api_protocol_root()
    )
    lowered = document.lower()
    for forbidden in ("authorization", "authority", "acceptance", "accepted"):
        assert f'"{forbidden}"' not in lowered


def test_runtime_identity_rejects_a_caller_supplied_root_not_bound_to_installed_bytes() -> None:
    with pytest.raises(ValueError, match="installed Factory package bytes"):
        RuntimeIdentity("a" * 64)


def test_qualified_runtime_makes_real_service_ready_and_preserves_shared_state(
    qualified_utilities: QualifiedUtilityRuntime,
    tmp_path: Path,
) -> None:
    runtime = open_runtime(tmp_path / "factory")
    embedded = EmbeddedFactoryHost(runtime.engine)
    service = StandaloneFactoryService(runtime.engine)
    first = embedded.start(_request("real-shared-state-first", "active"))
    mission = embedded.start(_request("real-shared-state", "active"))
    embedded_adapter = qualified_utilities.lifecycle_adapter(embedded, mode="embedded")
    service_adapter = qualified_utilities.lifecycle_adapter(service, mode="service")
    shared = qualified_utilities.embedded_contract
    ref = shared.RunRef(mission.mission_id)
    assert embedded_adapter.status(ref) == service_adapter.status(ref)
    assert embedded_adapter.events(ref) == service_adapter.events(ref)
    assert [event.sequence for event in embedded_adapter.events(ref)] == [1, 2]
    first_ref = shared.RunRef(first.mission_id)
    service.cancel(first.mission_id, reason="prove run-local continuation")
    first_events = service_adapter.events(first_ref)
    assert [event.sequence for event in first_events] == list(range(1, len(first_events) + 1))
    assert service_adapter.events(first_ref, after_sequence=2) == first_events[2:]
    api = FactoryAPI(
        runtime.store,
        runtime.core.advanced,
        reporting=runtime.core.reporting,
        engine_service=service,
        utility_runtime=qualified_utilities,
        runtime_identity=RuntimeIdentity(installed_component_root()),
    )
    assert api.readiness() == {"ok": True}
    assert api.runtime_manifest_record()["component"]["name"] == "software-factory"


def test_exact_artifact_verification_rejects_modified_and_renamed_wheels(
    qualified_utilities: QualifiedUtilityRuntime,
    tmp_path: Path,
) -> None:
    pin = QualifiedUtilityPin.load()
    package = pin.record["packages"]["embedded-service-contract"]
    source = Path(os.environ["SFV2_EMBEDDED_CONTRACT_WHEEL"])
    renamed = tmp_path / "renamed.whl"
    renamed.write_bytes(source.read_bytes())
    with pytest.raises(StoreError, match="filename"):
        pin.verify_wheel("embedded-service-contract", renamed)
    modified = tmp_path / package["wheel"]
    modified.write_bytes(source.read_bytes() + b"modified")
    with pytest.raises(StoreError, match="SHA-256"):
        pin.verify_wheel("embedded-service-contract", modified)


def test_qualified_pin_preserves_producer_and_rights_boundary() -> None:
    record = QualifiedUtilityPin.load().record
    assert record["qualified_producer_revision"] == ("a5659745a7cbcbb002b5f06051f6ed9826f721a7")
    assert record["qualified_producer_tree"] == ("f6b5cd45b6692c98c93bb3f19b2d4f2ddf361ec1")
    assert record["qualification_matrix_sha256"] == (
        "0888bed363b63842c37baa8187c9883cdddff73d936596e497e4e013341cd849"
    )
    assert record["technical_qualification_root_sha256"] == (
        "9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068"
    )
    packages = record["packages"]
    assert {
        name: {
            key: package[key]
            for key in (
                "accepted_source_commit",
                "accepted_source_tree",
                "package_tree_object",
                "version",
                "wheel_sha256",
                "wheel_content_root_sha256",
            )
        }
        for name, package in packages.items()
    } == {
        "embedded-service-contract": {
            "accepted_source_commit": "401f87a64349c636a66be2da656498e7d9cb58e3",
            "accepted_source_tree": "3f208324277bcd51b29dde8c394ccca3fb64a017",
            "package_tree_object": "203c809f3d1ab2588df5ed83c08affde99f8010c",
            "version": "0.1.0",
            "wheel_sha256": "2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d",
            "wheel_content_root_sha256": (
                "c53432ff83c6b80483a95384af3c9058a3cd82c56ac774126f123a93dbff7113"
            ),
        },
        "runtime-manifest": {
            "accepted_source_commit": "6f7a7ea3c105c7461e6cb4c83944dd094883f187",
            "accepted_source_tree": "13aad3d7299095b02893e55356b1959929b525ca",
            "package_tree_object": "42cb7171d3de021a99f75ac741ea0a0cf97c84ae",
            "version": "0.1.0",
            "wheel_sha256": "f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac",
            "wheel_content_root_sha256": (
                "db8f7f7d0b0105361f9b1380ff1d1cc432e720be02def65880a9ef484ad112a2"
            ),
        },
    }
    assert record["release_posture"] == "no-license-selected/unpublished"
    assert record["resolution"] == {
        "registry_allowed": False,
        "copied_source_allowed": False,
        "required_identity": (
            "qualified producer revision plus package source/tree and exact wheel SHA-256"
        ),
    }
