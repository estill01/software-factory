from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import (
    canonical_json,
    digest_json,
    json_load,
    new_id,
    parse_time,
    scope_contains,
    unique_sorted,
    utc_now,
)


class MissionService:
    def __init__(self, store: Store):
        self.store = store

    def create_project(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        project_id = new_id("prj")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?)",
                (project_id, name, canonical_json(metadata or {}), now, now),
            )
            self.store.append_event(
                db,
                mission_id=None,
                project_id=project_id,
                stream_key="mission",
                event_type="project.created",
                subject_type="project",
                subject_id=project_id,
                payload={"name": name},
            )
        return project_id

    def register_repository(
        self,
        path: str | Path,
        *,
        project_id: str | None = None,
        remote_url: str | None = None,
        default_branch: str = "main",
        current_revision: str | None = None,
        workspace_policy: dict[str, Any] | None = None,
    ) -> str:
        repository_id = new_id("repo")
        now = utc_now()
        resolved = str(Path(path).resolve())
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO repositories(
                   id,project_id,path,remote_url,default_branch,current_revision,
                   workspace_policy_json,state_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    repository_id,
                    project_id,
                    resolved,
                    remote_url,
                    default_branch,
                    current_revision,
                    canonical_json(workspace_policy or {}),
                    1,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                project_id=project_id,
                mission_id=None,
                stream_key="repository",
                event_type="repository.registered",
                subject_type="repository",
                subject_id=repository_id,
                payload={
                    "path": resolved,
                    "remote_url": remote_url,
                    "default_branch": default_branch,
                    "current_revision": current_revision,
                },
            )
        return repository_id

    def create_mission(
        self,
        *,
        title: str,
        objective: str,
        project_id: str | None = None,
        autonomy_mode: str = "full_autonomous",
        resource_limits: dict[str, Any] | None = None,
    ) -> str:
        mission_id = new_id("mis")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO missions(
                    id,project_id,title,objective,status,autonomy_mode,
                    resource_limits_json,state_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    mission_id,
                    project_id,
                    title,
                    objective,
                    "active",
                    autonomy_mode,
                    canonical_json(resource_limits or {}),
                    1,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                project_id=project_id,
                mission_id=mission_id,
                stream_key="mission",
                event_type="mission.created",
                subject_type="mission",
                subject_id=mission_id,
                new_version=1,
                payload={
                    "title": title,
                    "objective": objective,
                    "autonomy_mode": autonomy_mode,
                },
            )
        return mission_id

    def cancel_mission(self, mission_id: str, *, reason: str) -> dict[str, Any]:
        """Cancel a mission when no provider-owned execution is still active."""

        if not reason.strip():
            raise ValueError("mission cancellation requires a reason")
        with self.store.transaction() as db:
            mission = db.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
            if mission is None:
                raise StoreError("mission does not exist")
            if mission["status"] == "cancelled_by_authority":
                return dict(mission)
            if mission["status"] == "completed":
                raise InvalidTransition("completed mission cannot be cancelled")
            active = db.execute(
                """SELECT id FROM executions WHERE mission_id=? AND status IN (
                       'queued','dispatching','leased','running','verifying'
                   ) LIMIT 1""",
                (mission_id,),
            ).fetchone()
            if active is not None:
                raise InvalidTransition(
                    "mission has active execution; provider cancellation must complete first"
                )
            prior_version = int(mission["state_version"])
            new_version = prior_version + 1
            now = utc_now()
            db.execute(
                """UPDATE missions SET status='cancelled_by_authority',state_version=?,
                   updated_at=?,completed_at=? WHERE id=?""",
                (new_version, now, now, mission_id),
            )
            self.store.append_event(
                db,
                project_id=mission["project_id"],
                mission_id=mission_id,
                stream_key="mission",
                event_type="mission.cancelled_by_authority",
                subject_type="mission",
                subject_id=mission_id,
                prior_version=prior_version,
                new_version=new_version,
                payload={"reason": reason},
            )
        return self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))

    @staticmethod
    def _authority_set_root(db: Any, mission_id: str) -> str | None:
        rows = db.execute(
            """SELECT id,source_type,source_ref,effect_classes_json,scope_json,
                      parent_id,status,expires_at,uses_remaining,root_sha256
               FROM authority_records
               WHERE mission_id=? AND status='active'
               ORDER BY id""",
            (mission_id,),
        ).fetchall()
        if not rows:
            return None
        return digest_json([dict(row) for row in rows])

    def add_authority(
        self,
        *,
        mission_id: str,
        source_type: str,
        source_ref: str,
        effect_classes: Iterable[str],
        scope: Mapping[str, Any],
        parent_id: str | None = None,
        expires_at: str | None = None,
        uses_remaining: int | None = None,
    ) -> str:
        authority_id = new_id("auth")
        classes = unique_sorted(effect_classes)
        if not classes:
            raise ValueError("authority must grant at least one effect class")
        if uses_remaining is not None and uses_remaining <= 0:
            raise ValueError("uses_remaining must be positive")
        now_dt = dt.datetime.now(dt.UTC)
        expiry = parse_time(expires_at)
        if expires_at is not None and (expiry is None or expiry <= now_dt):
            raise ValueError("authority cannot be created already expired")
        material = {
            "mission_id": mission_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "effect_classes": classes,
            "scope": dict(scope),
            "parent_id": parent_id,
            "expires_at": expires_at,
            "uses_remaining": uses_remaining,
        }
        record_root = digest_json(material)
        with self.store.transaction() as db:
            mission = db.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
            if mission is None:
                raise StoreError("mission does not exist")
            if parent_id:
                parent = db.execute(
                    "SELECT * FROM authority_records WHERE id=?", (parent_id,)
                ).fetchone()
                if parent is None or parent["status"] != "active":
                    raise StoreError("delegating authority is not active")
                if parent["mission_id"] != mission_id:
                    raise StoreError("delegation cannot cross mission boundaries")
                parent_expiry = parse_time(parent["expires_at"])
                if parent_expiry is not None and parent_expiry <= now_dt:
                    raise StoreError("delegating authority is expired")
                parent_classes = set(json_load(parent["effect_classes_json"], []))
                if not set(classes).issubset(parent_classes):
                    raise StoreError("delegation would widen effect classes")
                parent_scope = json_load(parent["scope_json"], {})
                if not scope_contains(parent_scope, scope):
                    raise StoreError("delegation would widen scope")
                if parent["uses_remaining"] is not None and (
                    uses_remaining is None or uses_remaining > parent["uses_remaining"]
                ):
                    raise StoreError("delegation would widen use count")
                child_expiry = parse_time(expires_at)
                if parent_expiry is not None and (
                    child_expiry is None or child_expiry > parent_expiry
                ):
                    raise StoreError("delegation would widen expiration")
            db.execute(
                """INSERT INTO authority_records(
                    id,mission_id,source_type,source_ref,effect_classes_json,scope_json,
                    parent_id,status,expires_at,root_sha256,created_at,uses_remaining
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    authority_id,
                    mission_id,
                    source_type,
                    source_ref,
                    canonical_json(classes),
                    canonical_json(dict(scope)),
                    parent_id,
                    "active",
                    expires_at,
                    record_root,
                    utc_now(),
                    uses_remaining,
                ),
            )
            authority_root = self._authority_set_root(db, mission_id)
            prior_version = int(mission["state_version"])
            new_version = prior_version + 1
            db.execute(
                """UPDATE missions SET authority_root=?,state_version=?,updated_at=?
                   WHERE id=?""",
                (authority_root, new_version, utc_now(), mission_id),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="authority",
                event_type="authority.recorded",
                subject_type="authority",
                subject_id=authority_id,
                prior_version=prior_version,
                new_version=new_version,
                payload=material
                | {"record_root": record_root, "authority_set_root": authority_root},
            )
        return authority_id

    def revoke_authority(
        self,
        authority_id: str,
        *,
        expected_mission_version: int,
        reason: str,
    ) -> None:
        with self.store.transaction() as db:
            authority = db.execute(
                "SELECT * FROM authority_records WHERE id=?", (authority_id,)
            ).fetchone()
            if authority is None or authority["status"] != "active":
                raise InvalidTransition("authority is not active")
            self.store.check_version(
                db,
                table="missions",
                row_id=authority["mission_id"],
                expected_version=expected_mission_version,
            )
            db.execute("UPDATE authority_records SET status='revoked' WHERE id=?", (authority_id,))
            authority_root = self._authority_set_root(db, authority["mission_id"])
            new_version = expected_mission_version + 1
            db.execute(
                """UPDATE missions SET authority_root=?,state_version=?,updated_at=?
                   WHERE id=?""",
                (authority_root, new_version, utc_now(), authority["mission_id"]),
            )
            self.store.append_event(
                db,
                mission_id=authority["mission_id"],
                stream_key="authority",
                event_type="authority.revoked",
                subject_type="authority",
                subject_id=authority_id,
                prior_version=expected_mission_version,
                new_version=new_version,
                payload={"reason": reason, "authority_set_root": authority_root},
            )
