from __future__ import annotations

from typing import Any

from .errors import InvalidTransition, RoleConflict, StoreError
from .util import canonical_json, new_id, utc_now


class AgentService:
    def __init__(self, store: Any):
        self.store = store

    """Durable Codex/worker sessions and attributable work-role assignments."""

    def create_agent_session(
        self,
        *,
        mission_id: str | None,
        provider: str,
        role: str,
        model: str | None = None,
        reasoning_level: str | None = None,
        external_thread_id: str | None = None,
        external_task_id: str | None = None,
        parent_session_id: str | None = None,
        loaded_release_id: str | None = None,
        loaded_instruction_root: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        session_id = new_id("ses")
        now = utc_now()
        with self.store.transaction() as db:
            if (
                mission_id
                and db.execute("SELECT 1 FROM missions WHERE id=?", (mission_id,)).fetchone()
                is None
            ):
                raise StoreError("mission not found")
            if parent_session_id:
                parent = db.execute(
                    "SELECT mission_id FROM agent_sessions WHERE id=?", (parent_session_id,)
                ).fetchone()
                if parent is None or parent["mission_id"] != mission_id:
                    raise InvalidTransition("parent session must belong to the same mission")
            db.execute(
                """INSERT INTO agent_sessions(
                    id,mission_id,provider,external_thread_id,external_task_id,role,model,
                    reasoning_level,parent_session_id,loaded_release_id,
                    loaded_instruction_root,desired_status,observed_status,last_heartbeat_at,
                    metadata_json,started_at,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id,
                    mission_id,
                    provider,
                    external_thread_id,
                    external_task_id,
                    role,
                    model,
                    reasoning_level,
                    parent_session_id,
                    loaded_release_id,
                    loaded_instruction_root,
                    "running",
                    "starting",
                    now,
                    canonical_json(metadata or {}),
                    now,
                    1,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="agent",
                event_type="agent.session_created",
                subject_type="agent_session",
                subject_id=session_id,
                new_version=1,
                payload={"provider": provider, "role": role, "model": model},
            )
        return session_id

    def heartbeat_agent(
        self,
        session_id: str,
        *,
        expected_version: int,
        observed_status: str = "active",
        metadata_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if observed_status not in {"active", "idle", "unresponsive", "stopped", "lost"}:
            raise ValueError(f"unsupported observed status: {observed_status}")
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise StoreError("agent session not found")
            if row["state_version"] != expected_version:
                raise InvalidTransition("agent session version changed")
            metadata = self._json_patch(row["metadata_json"], metadata_patch or {})
            new_version = expected_version + 1
            stopped_at = utc_now() if observed_status in {"stopped", "lost"} else None
            db.execute(
                """UPDATE agent_sessions SET observed_status=?,last_heartbeat_at=?,
                   metadata_json=?,state_version=?,stopped_at=COALESCE(?,stopped_at)
                   WHERE id=?""",
                (
                    observed_status,
                    utc_now(),
                    metadata,
                    new_version,
                    stopped_at,
                    session_id,
                ),
            )
            self.store.append_event(
                db,
                mission_id=row["mission_id"],
                stream_key="agent",
                event_type="agent.heartbeat",
                subject_type="agent_session",
                subject_id=session_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={"observed_status": observed_status},
            )
        return self.store.one("SELECT * FROM agent_sessions WHERE id=?", (session_id,))

    def request_agent_status(
        self,
        session_id: str,
        *,
        expected_version: int,
        desired_status: str,
    ) -> dict[str, Any]:
        if desired_status not in {"running", "idle", "stopping", "stopped"}:
            raise ValueError(f"unsupported desired status: {desired_status}")
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
            if row is None or row["state_version"] != expected_version:
                raise InvalidTransition("agent session missing or stale")
            new_version = expected_version + 1
            db.execute(
                "UPDATE agent_sessions SET desired_status=?,state_version=? WHERE id=?",
                (desired_status, new_version, session_id),
            )
            self.store.append_event(
                db,
                mission_id=row["mission_id"],
                stream_key="agent",
                event_type="agent.desired_status_changed",
                subject_type="agent_session",
                subject_id=session_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={"desired_status": desired_status},
            )
        return self.store.one("SELECT * FROM agent_sessions WHERE id=?", (session_id,))

    @staticmethod
    def _json_patch(current: str, patch: dict[str, Any]) -> str:
        import json

        value = json.loads(current or "{}")
        value.update(patch)
        return canonical_json(value)

    def assign_work(
        self,
        *,
        work_item_id: str,
        agent_session_id: str,
        role: str,
        workspace_id: str | None = None,
        assigned_by_execution_id: str | None = None,
        assignment_scope: dict[str, Any] | None = None,
        instructions_root: str | None = None,
    ) -> str:
        assignment_id = new_id("asn")
        now = utc_now()
        with self.store.transaction() as db:
            work = db.execute("SELECT * FROM work_items WHERE id=?", (work_item_id,)).fetchone()
            session = db.execute(
                "SELECT * FROM agent_sessions WHERE id=?", (agent_session_id,)
            ).fetchone()
            if work is None or session is None:
                raise StoreError("work item or agent session not found")
            if session["mission_id"] != work["mission_id"]:
                raise InvalidTransition("assignment cannot cross mission boundaries")
            if session["observed_status"] in {"stopped", "lost"}:
                raise InvalidTransition("stopped/lost agent cannot accept work")
            if workspace_id:
                workspace = db.execute(
                    "SELECT * FROM workspaces WHERE id=?", (workspace_id,)
                ).fetchone()
                if workspace is None or workspace["mission_id"] != work["mission_id"]:
                    raise InvalidTransition("workspace does not belong to work mission")
                if workspace["work_item_id"] not in {None, work_item_id}:
                    raise InvalidTransition("workspace belongs to another work item")
            if role in {"reviewer", "evaluator", "acceptance_owner"}:
                implementers = db.execute(
                    """SELECT agent_session_id FROM work_assignments
                       WHERE work_item_id=? AND role='implementer'
                         AND status IN ('accepted','active','completed')""",
                    (work_item_id,),
                ).fetchall()
                if agent_session_id in {row["agent_session_id"] for row in implementers}:
                    raise RoleConflict("implementer cannot independently review/evaluate itself")
            db.execute(
                """INSERT INTO work_assignments(
                    id,work_item_id,agent_session_id,workspace_id,role,status,
                    assigned_by_execution_id,assignment_scope_json,instructions_root,
                    lease_generation,created_at,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    assignment_id,
                    work_item_id,
                    agent_session_id,
                    workspace_id,
                    role,
                    "accepted",
                    assigned_by_execution_id,
                    canonical_json(assignment_scope or {}),
                    instructions_root,
                    0,
                    now,
                    1,
                ),
            )
            if workspace_id:
                db.execute(
                    "UPDATE workspaces SET owner_assignment_id=?,updated_at=? WHERE id=?",
                    (assignment_id, now, workspace_id),
                )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="agent",
                event_type="work.assigned",
                subject_type="work_assignment",
                subject_id=assignment_id,
                source_type="execution" if assigned_by_execution_id else "runtime",
                source_id=assigned_by_execution_id,
                new_version=1,
                payload={
                    "work_item_id": work_item_id,
                    "agent_session_id": agent_session_id,
                    "role": role,
                    "workspace_id": workspace_id,
                },
            )
        return assignment_id

    def activate_assignment(self, assignment_id: str, *, expected_version: int = 1) -> None:
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM work_assignments WHERE id=?", (assignment_id,)
            ).fetchone()
            if row is None or row["state_version"] != expected_version:
                raise InvalidTransition("assignment missing or stale")
            if row["status"] not in {"offered", "accepted"}:
                raise InvalidTransition("assignment cannot be activated")
            db.execute(
                """UPDATE work_assignments SET status='active',started_at=?,state_version=?
                   WHERE id=?""",
                (utc_now(), expected_version + 1, assignment_id),
            )
