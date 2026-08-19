from __future__ import annotations

import sqlite3
from typing import Any, Callable, TypeVar

from .errors import AuthorityDenied, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now

T = TypeVar("T")

class AuditMixin:

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
            rows = self.all(
                """SELECT * FROM events WHERE mission_id IS ?
                   ORDER BY sequence""",
                (mission_id,),
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

    def command(
            self,
            *,
            command_id: str,
            idempotency_key: str,
            actor_id: str | None,
            authority_record_id: str | None,
            target_type: str,
            target_id: str,
            expected_version: int | None,
            effect_class: str,
            payload: Any,
            evidence: list[str] | None,
            apply: Callable[[sqlite3.Connection], T],
        ) -> T:
            with self.transaction() as db:
                existing = db.execute(
                    "SELECT * FROM commands WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    record = dict(existing)
                    if record["status"] == "succeeded":
                        return json_load(record["result_json"])  # type: ignore[return-value]
                    if record["status"] == "failed":
                        raise StoreError(
                            f"idempotent command previously failed: "
                            f"{json_load(record['error_json'])}"
                        )
                    raise StoreError("idempotent command is already running")

                if authority_record_id is not None:
                    authority = db.execute(
                        "SELECT * FROM authority_records WHERE id=?",
                        (authority_record_id,),
                    ).fetchone()
                    if authority is None or authority["status"] != "active":
                        raise AuthorityDenied("authority record is missing or inactive")
                    classes = set(json_load(authority["effect_classes_json"], []))
                    if effect_class not in classes:
                        raise AuthorityDenied(
                            f"authority does not grant effect class {effect_class}"
                        )

                now = utc_now()
                db.execute(
                    """INSERT INTO commands(
                        id,idempotency_key,actor_id,authority_record_id,target_type,
                        target_id,expected_version,effect_class,payload_json,evidence_json,
                        status,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        command_id,
                        idempotency_key,
                        actor_id,
                        authority_record_id,
                        target_type,
                        target_id,
                        expected_version,
                        effect_class,
                        canonical_json(payload),
                        canonical_json(evidence or []),
                        "running",
                        now,
                    ),
                )
                try:
                    result = apply(db)
                except Exception as exc:
                    db.execute(
                        """UPDATE commands SET status='failed',error_json=?,completed_at=?
                           WHERE id=?""",
                        (
                            canonical_json({"type": type(exc).__name__, "message": str(exc)}),
                            utc_now(),
                            command_id,
                        ),
                    )
                    raise
                db.execute(
                    """UPDATE commands SET status='succeeded',result_json=?,completed_at=?
                       WHERE id=?""",
                    (canonical_json(result), utc_now(), command_id),
                )
                return result
