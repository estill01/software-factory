from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..engine import (
    ENGINE_CONTRACT_VERSION,
    CancelResult,
    EngineContract,
    EventRecord,
    MissionOutcome,
    MissionRef,
    MissionSnapshot,
    MissionSubmission,
    contract_dict,
)


@dataclass(frozen=True)
class ServiceHostShape:
    mode: str = "service"
    provider_process_owner: bool = True


class StandaloneFactoryService:
    """Standalone service facade with no host-local mission state."""

    shape = ServiceHostShape()

    def __init__(self, engine: EngineContract):
        self.engine = engine

    def start(self, submission: MissionSubmission) -> MissionRef:
        return self.engine.start(submission)

    def status(self, mission_id: str) -> MissionSnapshot:
        return self.engine.status(mission_id)

    def continue_mission(self, mission_id: str) -> MissionSnapshot:
        return self.engine.continue_mission(mission_id)

    def cancel(self, mission_id: str, *, reason: str) -> CancelResult:
        return self.engine.cancel(mission_id, reason=reason)

    def outcome(self, mission_id: str) -> MissionOutcome:
        return self.engine.outcome(mission_id)

    def events(
        self, mission_id: str, *, after_sequence: int = 0, limit: int = 100
    ) -> tuple[EventRecord, ...]:
        return self.engine.events(mission_id, after_sequence=after_sequence, limit=limit)

    def invoke(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """JSON-ready service boundary over the exact typed engine operations."""

        if operation == "start":
            return self._wire(contract_dict(self.start(MissionSubmission(**dict(payload)))))
        mission_id = str(payload.get("mission_id", ""))
        if not mission_id:
            raise ValueError("service operation requires mission_id")
        if operation == "status":
            return self._wire(contract_dict(self.status(mission_id)))
        if operation == "continue":
            return self._wire(contract_dict(self.continue_mission(mission_id)))
        if operation == "cancel":
            return self._wire(
                contract_dict(self.cancel(mission_id, reason=str(payload.get("reason", ""))))
            )
        if operation == "outcome":
            return self._wire(contract_dict(self.outcome(mission_id)))
        if operation == "events":
            records = self.events(
                mission_id,
                after_sequence=int(payload.get("after_sequence", 0)),
                limit=int(payload.get("limit", 100)),
            )
            return self._wire({"events": [contract_dict(record) for record in records]})
        raise ValueError(f"unsupported engine operation: {operation}")

    @staticmethod
    def _wire(payload: Mapping[str, Any]) -> dict[str, Any]:
        return {"contract_version": ENGINE_CONTRACT_VERSION, **dict(payload)}
