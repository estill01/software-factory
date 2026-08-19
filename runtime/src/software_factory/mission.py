from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .store import InvalidTransition, Store, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now

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

    def add_authority(
            self,
            *,
            mission_id: str,
            source_type: str,
            source_ref: str,
            effect_classes: Iterable[str],
            scope: dict[str, Any],
            parent_id: str | None = None,
            expires_at: str | None = None,
        ) -> str:
            authority_id = new_id("auth")
            classes = sorted(set(effect_classes))
            if not classes:
                raise ValueError("authority must grant at least one effect class")
            material = {
                "mission_id": mission_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "effect_classes": classes,
                "scope": scope,
                "parent_id": parent_id,
                "expires_at": expires_at,
            }
            root = digest_json(material)
            with self.store.transaction() as db:
                if parent_id:
                    parent = db.execute(
                        "SELECT * FROM authority_records WHERE id=?", (parent_id,)
                    ).fetchone()
                    if parent is None or parent["status"] != "active":
                        raise StoreError("delegating authority is not active")
                    parent_classes = set(json_load(parent["effect_classes_json"], []))
                    if not set(classes).issubset(parent_classes):
                        raise StoreError("delegation would widen effect classes")
                db.execute(
                    """INSERT INTO authority_records(
                        id,mission_id,source_type,source_ref,effect_classes_json,scope_json,
                        parent_id,status,expires_at,root_sha256,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        authority_id,
                        mission_id,
                        source_type,
                        source_ref,
                        canonical_json(classes),
                        canonical_json(scope),
                        parent_id,
                        "active",
                        expires_at,
                        root,
                        utc_now(),
                    ),
                )
                mission = db.execute(
                    "SELECT state_version FROM missions WHERE id=?", (mission_id,)
                ).fetchone()
                if mission is None:
                    raise StoreError("mission does not exist")
                db.execute(
                    "UPDATE missions SET authority_root=?,updated_at=? WHERE id=?",
                    (root, utc_now(), mission_id),
                )
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="authority",
                    event_type="authority.recorded",
                    subject_type="authority",
                    subject_id=authority_id,
                    payload=material | {"root_sha256": root},
                )
            return authority_id
