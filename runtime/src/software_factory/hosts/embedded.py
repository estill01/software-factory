from __future__ import annotations

from dataclasses import dataclass

from ..engine import (
    CancelResult,
    EngineContract,
    EventRecord,
    MissionOutcome,
    MissionRef,
    MissionSnapshot,
    MissionSubmission,
)


@dataclass(frozen=True)
class EmbeddedHostShape:
    mode: str = "embedded"
    provider_process_owner: bool = False


class EmbeddedFactoryHost:
    """Typed in-process facade; the embedding product remains the outer host."""

    shape = EmbeddedHostShape()

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
