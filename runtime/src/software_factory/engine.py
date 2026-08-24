from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .core import CoreService
from .errors import StoreError
from .store import Store
from .util import digest_json, json_load, utc_now

ENGINE_CONTRACT_VERSION = "software-factory-engine/1"
MAX_EVENT_PAGE = 1000


@dataclass(frozen=True)
class MissionSubmission:
    idempotency_key: str
    title: str
    objective: str
    project_id: str | None = None
    autonomy_mode: str = "full_autonomous"
    resource_limits: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "objective": self.objective,
            "project_id": self.project_id,
            "autonomy_mode": self.autonomy_mode,
            "resource_limits": dict(self.resource_limits),
        }

    @property
    def request_root(self) -> str:
        return digest_json(self.normalized())


@dataclass(frozen=True)
class MissionRef:
    mission_id: str
    request_root: str
    duplicate: bool


@dataclass(frozen=True)
class MissionSnapshot:
    mission_id: str
    status: str
    state_version: int
    next_action: Mapping[str, Any]
    last_event_sequence: int


@dataclass(frozen=True)
class EventRecord:
    sequence: int
    event_id: str
    event_type: str
    stream_key: str
    subject_type: str | None
    subject_id: str | None
    payload: Mapping[str, Any]
    created_at: str


@dataclass(frozen=True)
class CancelResult:
    mission_id: str
    status: str
    state_version: int


@dataclass(frozen=True)
class MissionOutcome:
    mission_id: str
    terminal: bool
    disposition: str | None
    terminal_evidence_id: str | None
    completed_at: str | None


class EngineContract(Protocol):
    def start(self, submission: MissionSubmission) -> MissionRef: ...

    def status(self, mission_id: str) -> MissionSnapshot: ...

    def continue_mission(self, mission_id: str) -> MissionSnapshot: ...

    def cancel(self, mission_id: str, *, reason: str) -> CancelResult: ...

    def outcome(self, mission_id: str) -> MissionOutcome: ...

    def events(
        self, mission_id: str, *, after_sequence: int = 0, limit: int = 100
    ) -> tuple[EventRecord, ...]: ...


class FactoryEngine:
    """Typed mission engine shared unchanged by embedded and service hosts."""

    contract_version = ENGINE_CONTRACT_VERSION

    def __init__(self, store: Store, core: CoreService):
        self.store = store
        self.core = core

    def start(self, submission: MissionSubmission) -> MissionRef:
        key = submission.idempotency_key.strip()
        if not key or len(key) > 256:
            raise ValueError("idempotency key must contain 1 to 256 characters")
        if not submission.title.strip() or not submission.objective.strip():
            raise ValueError("mission title and objective are required")
        root = submission.request_root
        with self.store.transaction() as db:
            existing = db.execute(
                "SELECT * FROM engine_submissions_v2 WHERE idempotency_key=?", (key,)
            ).fetchone()
            if existing is not None:
                if existing["request_root"] != root:
                    raise StoreError("idempotency key was reused for a different mission request")
                return MissionRef(
                    mission_id=str(existing["mission_id"]),
                    request_root=root,
                    duplicate=True,
                )
            mission_id = self.core.create_mission(
                title=submission.title,
                objective=submission.objective,
                project_id=submission.project_id,
                autonomy_mode=submission.autonomy_mode,
                resource_limits=dict(submission.resource_limits),
            )
            db.execute(
                """INSERT INTO engine_submissions_v2(
                       idempotency_key,request_root,mission_id,created_at
                   ) VALUES(?,?,?,?)""",
                (key, root, mission_id, utc_now()),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="host",
                event_type="engine.mission_submitted",
                subject_type="mission",
                subject_id=mission_id,
                source_type="engine_contract",
                source_id=ENGINE_CONTRACT_VERSION,
                payload={"idempotency_key": key, "request_root": root},
            )
        return MissionRef(mission_id=mission_id, request_root=root, duplicate=False)

    def status(self, mission_id: str) -> MissionSnapshot:
        mission = self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
        last_sequence = int(
            self.store.scalar(
                "SELECT COALESCE(MAX(sequence),0) FROM events WHERE mission_id=?", (mission_id,)
            )
        )
        return MissionSnapshot(
            mission_id=mission_id,
            status=str(mission["status"]),
            state_version=int(mission["state_version"]),
            next_action=self.core.next_action(mission_id),
            last_event_sequence=last_sequence,
        )

    def continue_mission(self, mission_id: str) -> MissionSnapshot:
        """Reattach to the durable mission and expose its current safe frontier.

        Scheduling and provider effects remain owned by later Blocks. This
        operation intentionally performs no host-local or provider mutation.
        """

        return self.status(mission_id)

    def cancel(self, mission_id: str, *, reason: str) -> CancelResult:
        mission = self.core.missions.cancel_mission(mission_id, reason=reason)
        return CancelResult(
            mission_id=mission_id,
            status=str(mission["status"]),
            state_version=int(mission["state_version"]),
        )

    def outcome(self, mission_id: str) -> MissionOutcome:
        mission = self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
        status = str(mission["status"])
        disposition = None
        if status == "completed":
            disposition = "succeeded"
        elif status == "cancelled_by_authority":
            disposition = "cancelled"
        return MissionOutcome(
            mission_id=mission_id,
            terminal=disposition is not None,
            disposition=disposition,
            terminal_evidence_id=mission.get("terminal_evidence_id"),
            completed_at=mission.get("completed_at"),
        )

    def events(
        self,
        mission_id: str,
        *,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[EventRecord, ...]:
        self.store.one("SELECT id FROM missions WHERE id=?", (mission_id,))
        if after_sequence < 0:
            raise ValueError("after_sequence cannot be negative")
        if limit < 1 or limit > MAX_EVENT_PAGE:
            raise ValueError(f"event limit must be between 1 and {MAX_EVENT_PAGE}")
        rows = self.store.all(
            """SELECT sequence,id,event_type,stream_key,subject_type,subject_id,
                      payload_json,created_at
               FROM events WHERE mission_id=? AND sequence>?
               ORDER BY sequence LIMIT ?""",
            (mission_id, after_sequence, limit),
        )
        return tuple(
            EventRecord(
                sequence=int(row["sequence"]),
                event_id=str(row["id"]),
                event_type=str(row["event_type"]),
                stream_key=str(row["stream_key"]),
                subject_type=row.get("subject_type"),
                subject_id=row.get("subject_id"),
                payload=json_load(row["payload_json"], {}),
                created_at=str(row["created_at"]),
            )
            for row in rows
        )


ContractValue = MissionRef | MissionSnapshot | EventRecord | CancelResult | MissionOutcome


def contract_dict(value: ContractValue) -> dict[str, Any]:
    return asdict(value)
