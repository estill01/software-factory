from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar, cast

from .errors import AuthorityDenied, EvidenceInvalid, StoreError
from .util import (
    canonical_json,
    digest_json,
    json_load,
    new_id,
    parse_time,
    scope_allows,
    utc_now,
)

T = TypeVar("T")


@dataclass(frozen=True)
class CommandEnvelope:
    command_id: str
    idempotency_key: str
    actor_id: str | None
    authority_record_id: str | None
    mission_id: str | None
    target_type: str
    target_id: str
    expected_version: int | None
    effect_class: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[str, ...] = ()
    requested_scope: Mapping[str, Any] = field(default_factory=dict)

    @property
    def root(self) -> str:
        return digest_json(
            {
                "actor_id": self.actor_id,
                "authority_record_id": self.authority_record_id,
                "mission_id": self.mission_id,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "expected_version": self.expected_version,
                "effect_class": self.effect_class,
                "payload": dict(self.payload),
                "evidence": list(self.evidence),
                "requested_scope": dict(self.requested_scope),
            }
        )


_VERSIONED_TARGETS = {
    "repository": "repositories",
    "mission": "missions",
    "capability": "capabilities",
    "obligation": "obligations",
    "program": "programs",
    "work_item": "work_items",
    "experiment": "experiments",
    "incident": "incidents",
    "hypothesis": "hypotheses",
    "signal_candidate": "signal_candidates",
    "recovery_case": "recovery_cases",
    "cleanup_run": "cleanup_runs",
}


class _AuditPersistence(Protocol):
    """Persistence surface required by the audit/application command layer."""

    def transaction(
        self, *, mode: str = "IMMEDIATE"
    ) -> AbstractContextManager[sqlite3.Connection]: ...

    def all(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        db: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]: ...

    def check_version(
        self,
        db: sqlite3.Connection,
        *,
        table: str,
        row_id: str,
        expected_version: int,
    ) -> dict[str, Any]: ...


class AuditMixin:
    def _persistence(self) -> _AuditPersistence:
        """Return the concrete database owner without competing base methods."""

        return cast(_AuditPersistence, self)

    def append_event(
        self,
        db: sqlite3.Connection,
        *,
        mission_id: str | None,
        stream_key: str,
        event_type: str,
        subject_type: str | None = None,
        subject_id: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        causation_id: str | None = None,
        correlation_id: str | None = None,
        prior_version: int | None = None,
        new_version: int | None = None,
        payload: Any = None,
        project_id: str | None = None,
    ) -> str:
        previous = db.execute(
            """SELECT event_hash FROM events
               WHERE mission_id IS ? ORDER BY sequence DESC LIMIT 1""",
            (mission_id,),
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else None
        event_id = new_id("evt")
        created_at = utc_now()
        material = {
            "id": event_id,
            "project_id": project_id,
            "mission_id": mission_id,
            "stream_key": stream_key,
            "event_type": event_type,
            "source_type": source_type,
            "source_id": source_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "causation_id": causation_id,
            "correlation_id": correlation_id,
            "prior_version": prior_version,
            "new_version": new_version,
            "payload": payload or {},
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        event_hash = digest_json(material)
        db.execute(
            """INSERT INTO events(
                id,project_id,mission_id,stream_key,event_type,source_type,source_id,
                subject_type,subject_id,causation_id,correlation_id,prior_version,
                new_version,payload_json,previous_hash,event_hash,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                project_id,
                mission_id,
                stream_key,
                event_type,
                source_type,
                source_id,
                subject_type,
                subject_id,
                causation_id,
                correlation_id,
                prior_version,
                new_version,
                canonical_json(payload or {}),
                previous_hash,
                event_hash,
                created_at,
            ),
        )
        return event_id

    def verify_event_chain(self, mission_id: str | None = None) -> dict[str, Any]:
        rows = self._persistence().all(
            "SELECT * FROM events WHERE mission_id IS ? ORDER BY sequence", (mission_id,)
        )
        previous_hash = None
        for row in rows:
            material = {
                "id": row["id"],
                "project_id": row["project_id"],
                "mission_id": row["mission_id"],
                "stream_key": row["stream_key"],
                "event_type": row["event_type"],
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "subject_type": row["subject_type"],
                "subject_id": row["subject_id"],
                "causation_id": row["causation_id"],
                "correlation_id": row["correlation_id"],
                "prior_version": row["prior_version"],
                "new_version": row["new_version"],
                "payload": json_load(row["payload_json"], {}),
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if row["previous_hash"] != previous_hash:
                raise StoreError(f"event chain predecessor differs at {row['id']}")
            expected = digest_json(material)
            if expected != row["event_hash"]:
                raise StoreError(f"event hash differs at {row['id']}")
            previous_hash = expected
        return {
            "mission_id": mission_id,
            "records": len(rows),
            "head": previous_hash,
            "valid": True,
        }

    def record_evidence(
        self,
        *,
        mission_id: str | None,
        evidence_type: str,
        subject_type: str,
        subject_id: str,
        status: str = "current",
        revision: str | None = None,
        artifact_id: str | None = None,
        execution_id: str | None = None,
        producer_session_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> str:
        evidence_id = new_id("evd")
        material = {
            "mission_id": mission_id,
            "evidence_type": evidence_type,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "revision": revision,
            "status": status,
            "artifact_id": artifact_id,
            "execution_id": execution_id,
            "producer_session_id": producer_session_id,
            "payload": dict(payload or {}),
        }
        with self._persistence().transaction() as db:
            if execution_id:
                execution = db.execute(
                    "SELECT mission_id,status FROM executions WHERE id=?", (execution_id,)
                ).fetchone()
                if execution is None or execution["status"] != "succeeded":
                    raise EvidenceInvalid("execution evidence must reference a succeeded execution")
                if mission_id is not None and execution["mission_id"] != mission_id:
                    raise EvidenceInvalid("execution evidence belongs to a different mission")
            db.execute(
                """INSERT INTO evidence_records(
                    id,mission_id,evidence_type,subject_type,subject_id,revision,status,
                    artifact_id,execution_id,producer_session_id,payload_json,root_sha256,
                    created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id,
                    mission_id,
                    evidence_type,
                    subject_type,
                    subject_id,
                    revision,
                    status,
                    artifact_id,
                    execution_id,
                    producer_session_id,
                    canonical_json(payload or {}),
                    digest_json(material),
                    utc_now(),
                ),
            )
            self.append_event(
                db,
                mission_id=mission_id,
                stream_key="evidence",
                event_type="evidence.recorded",
                subject_type=subject_type,
                subject_id=subject_id,
                source_type="session" if producer_session_id else "runtime",
                source_id=producer_session_id,
                payload={"evidence_id": evidence_id, **material},
            )
        return evidence_id

    def require_evidence(
        self,
        db: sqlite3.Connection,
        evidence_ids: list[str] | tuple[str, ...],
        *,
        mission_id: str | None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        revision: str | None = None,
        evidence_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not evidence_ids:
            raise EvidenceInvalid("at least one current evidence record is required")
        rows: list[dict[str, Any]] = []
        for evidence_id in evidence_ids:
            row = db.execute("SELECT * FROM evidence_records WHERE id=?", (evidence_id,)).fetchone()
            if row is None:
                raise EvidenceInvalid(f"evidence not found: {evidence_id}")
            value = dict(row)
            if value["status"] != "current":
                raise EvidenceInvalid(f"evidence is not current: {evidence_id}")
            if mission_id is not None and value["mission_id"] != mission_id:
                raise EvidenceInvalid(f"evidence belongs to another mission: {evidence_id}")
            if subject_type is not None and value["subject_type"] != subject_type:
                raise EvidenceInvalid(f"evidence has wrong subject type: {evidence_id}")
            if subject_id is not None and value["subject_id"] != subject_id:
                raise EvidenceInvalid(f"evidence has wrong subject: {evidence_id}")
            if revision is not None and value["revision"] != revision:
                raise EvidenceInvalid(f"evidence has wrong revision: {evidence_id}")
            if evidence_types and value["evidence_type"] not in evidence_types:
                raise EvidenceInvalid(f"evidence has wrong type: {evidence_id}")
            rows.append(value)
        return rows

    def invalidate_evidence(
        self,
        *,
        subject_type: str,
        subject_id: str,
        except_revision: str | None = None,
    ) -> int:
        with self._persistence().transaction() as db:
            if except_revision is None:
                result = db.execute(
                    """UPDATE evidence_records SET status='stale',invalidated_at=?
                       WHERE subject_type=? AND subject_id=? AND status='current'""",
                    (utc_now(), subject_type, subject_id),
                )
            else:
                result = db.execute(
                    """UPDATE evidence_records SET status='stale',invalidated_at=?
                       WHERE subject_type=? AND subject_id=? AND status='current'
                         AND COALESCE(revision,'')<>?""",
                    (utc_now(), subject_type, subject_id, except_revision),
                )
            return int(result.rowcount)

    def _validate_authority(self, db: sqlite3.Connection, envelope: CommandEnvelope) -> None:
        if envelope.authority_record_id is None:
            if envelope.effect_class not in {"read/observe", "internal_state"}:
                raise AuthorityDenied("consequential effect requires explicit authority")
            return
        authority = db.execute(
            "SELECT * FROM authority_records WHERE id=?", (envelope.authority_record_id,)
        ).fetchone()
        if authority is None or authority["status"] != "active":
            raise AuthorityDenied("authority record is missing or inactive")
        expiry = parse_time(authority["expires_at"])
        if expiry is not None and expiry <= dt.datetime.now(dt.UTC):
            raise AuthorityDenied("authority record is expired")
        if envelope.mission_id is not None and authority["mission_id"] != envelope.mission_id:
            raise AuthorityDenied("authority belongs to another mission")
        classes = set(json_load(authority["effect_classes_json"], []))
        if envelope.effect_class not in classes:
            raise AuthorityDenied(f"authority does not grant effect class {envelope.effect_class}")
        authority_scope = json_load(authority["scope_json"], {})
        if not scope_allows(authority_scope, envelope.requested_scope):
            raise AuthorityDenied("requested scope exceeds authority scope")
        if authority["uses_remaining"] is not None and authority["uses_remaining"] <= 0:
            raise AuthorityDenied("authority record has no remaining uses")

    def _validate_expected_version(self, db: sqlite3.Connection, envelope: CommandEnvelope) -> None:
        if envelope.expected_version is None:
            return
        table = _VERSIONED_TARGETS.get(envelope.target_type)
        if table is None:
            raise StoreError(
                f"expected_version cannot be enforced for target type {envelope.target_type}"
            )
        self._persistence().check_version(
            db,
            table=table,
            row_id=envelope.target_id,
            expected_version=envelope.expected_version,
        )

    def command(self, envelope: CommandEnvelope, apply: Callable[[sqlite3.Connection], T]) -> T:
        """Execute an idempotent command with durable failure recording.

        The command claim is committed before the effect transaction. If the effect
        rolls back, a second transaction records the failure, so retries cannot lose
        the prior attempt or silently duplicate an external effect.
        """

        with self._persistence().transaction() as db:
            existing = db.execute(
                "SELECT * FROM commands WHERE idempotency_key=?",
                (envelope.idempotency_key,),
            ).fetchone()
            if existing is not None:
                record = dict(existing)
                if record["command_root"] != envelope.root:
                    raise StoreError("idempotency key was reused for a different command")
                if record["status"] == "succeeded":
                    return json_load(record["result_json"])
                if record["status"] == "failed":
                    raise StoreError(
                        f"idempotent command previously failed: {json_load(record['error_json'])}"
                    )
                raise StoreError("idempotent command is already running")

            self._validate_authority(db, envelope)
            self._validate_expected_version(db, envelope)
            db.execute(
                """INSERT INTO commands(
                    id,idempotency_key,actor_id,authority_record_id,target_type,
                    target_id,expected_version,effect_class,payload_json,evidence_json,
                    status,created_at,command_root,requested_scope_json,mission_id
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    envelope.command_id,
                    envelope.idempotency_key,
                    envelope.actor_id,
                    envelope.authority_record_id,
                    envelope.target_type,
                    envelope.target_id,
                    envelope.expected_version,
                    envelope.effect_class,
                    canonical_json(dict(envelope.payload)),
                    canonical_json(list(envelope.evidence)),
                    "running",
                    utc_now(),
                    envelope.root,
                    canonical_json(dict(envelope.requested_scope)),
                    envelope.mission_id,
                ),
            )

        try:
            with self._persistence().transaction() as db:
                self._validate_authority(db, envelope)
                self._validate_expected_version(db, envelope)
                result = apply(db)
                if envelope.authority_record_id is not None:
                    db.execute(
                        """UPDATE authority_records
                           SET uses_remaining=CASE
                               WHEN uses_remaining IS NULL THEN NULL
                               ELSE uses_remaining-1 END,
                               consumed_at=CASE
                               WHEN uses_remaining=1 THEN ? ELSE consumed_at END
                           WHERE id=?""",
                        (utc_now(), envelope.authority_record_id),
                    )
                db.execute(
                    """UPDATE commands SET status='succeeded',result_json=?,completed_at=?
                       WHERE id=?""",
                    (canonical_json(result), utc_now(), envelope.command_id),
                )
            return result
        except Exception as exc:
            with self._persistence().transaction() as db:
                db.execute(
                    """UPDATE commands SET status='failed',error_json=?,completed_at=?
                       WHERE id=? AND status='running'""",
                    (
                        canonical_json({"type": type(exc).__name__, "message": str(exc)}),
                        utc_now(),
                        envelope.command_id,
                    ),
                )
            raise
