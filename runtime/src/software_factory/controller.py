from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets
import sqlite3
from collections.abc import Mapping
from typing import Any

from .errors import (
    InvalidTransition,
    LeaseConflict,
    ProviderError,
    StaleLease,
    StoreError,
)
from .execution import _leases_conflict, _resource_key
from .providers import ProviderObservation, ProviderRegistry, ProviderRequest
from .scheduling import (
    SchedulingPolicy,
    active_execution_count,
    implementation_attempt_counts,
)
from .util import canonical_json, digest_json, json_load, new_id, parse_time, utc_now

_MUTATING_WORK_TYPES = {
    "implementation",
    "inline_correction",
    "candidate_comparison",
    "integration",
    "program_revision",
    "release",
    "rollback",
    "cleanup",
}


class ControllerService:
    """Authoritative controller for recovery, atomic dispatch, and provider lifecycle."""

    def __init__(
        self,
        store: Any,
        *,
        work_items: Any,
        agents: Any,
        workspaces: Any,
        executions: Any,
        continuation: Any,
        supervision: Any | None,
        adaptive: Any | None,
        governance: Any,
        providers: ProviderRegistry,
        default_provider: str | None = None,
    ) -> None:
        self.store = store
        self.work_items = work_items
        self.agents = agents
        self.workspaces = workspaces
        self.executions = executions
        self.continuation = continuation
        self.supervision = supervision
        self.adaptive = adaptive
        self.governance = governance
        self.providers = providers
        self.default_provider = default_provider

    def _resolve_repository(self, work: Mapping[str, Any]) -> str | None:
        if work.get("repository_id"):
            return str(work["repository_id"])
        if work["work_type"] not in _MUTATING_WORK_TYPES:
            return None
        rows = self.store.all(
            """SELECT r.id FROM repositories r
               JOIN missions m ON m.project_id=r.project_id
               WHERE m.id=? AND r.project_id IS m.project_id ORDER BY r.created_at""",
            (work["mission_id"],),
        )
        if len(rows) != 1:
            raise InvalidTransition(
                "mutating work requires an explicit repository when the mission does not have exactly one"
            )
        repository_id = str(rows[0]["id"])
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT state_version FROM work_items WHERE id=?", (work["id"],)
            ).fetchone()
            if current is None:
                raise StoreError("work item not found")
            new_version = int(current["state_version"]) + 1
            db.execute(
                """UPDATE work_items SET repository_id=?,state_version=?,updated_at=?
                   WHERE id=?""",
                (repository_id, new_version, utc_now(), work["id"]),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="controller",
                event_type="work.repository_resolved",
                subject_type="work_item",
                subject_id=work["id"],
                prior_version=current["state_version"],
                new_version=new_version,
                payload={"repository_id": repository_id},
            )
        return repository_id

    def _ensure_workspace(self, work: Mapping[str, Any], repository_id: str | None) -> str | None:
        if repository_id is None:
            return None
        existing = self.store.one(
            """SELECT id FROM workspaces
               WHERE work_item_id=? AND status IN ('creating','ready','active','retained')
               ORDER BY created_at DESC LIMIT 1""",
            (work["id"],),
            required=False,
        )
        if existing is not None:
            return str(existing["id"])
        repository = self.store.one(
            "SELECT current_revision FROM repositories WHERE id=?", (repository_id,)
        )
        if not repository["current_revision"]:
            raise InvalidTransition("repository has no current revision")
        workspace_type = (
            "candidate_lane" if work["work_type"] == "candidate_comparison" else "cooperative_lane"
        )
        try:
            return self.workspaces.create_workspace(
                repository_id=repository_id,
                mission_id=work["mission_id"],
                work_item_id=work["id"],
                workspace_type=workspace_type,
                base_revision=repository["current_revision"],
                writable_scope=json_load(work["writable_scope_json"], []),
            )
        except sqlite3.IntegrityError:
            raced = self.store.one(
                """SELECT id FROM workspaces WHERE work_item_id=?
                   AND status IN ('creating','ready','active','retained')
                   ORDER BY created_at DESC LIMIT 1""",
                (work["id"],),
                required=False,
            )
            if raced is None:
                raise
            return str(raced["id"])

    def _choose_agent(
        self,
        *,
        mission_id: str,
        provider_key: str,
        role: str,
        auto_spawn: bool,
    ) -> str | None:
        row = self.store.one(
            """SELECT s.id FROM agent_sessions s
               WHERE s.mission_id=? AND s.provider=? AND s.role=?
                 AND s.desired_status='running'
                 AND s.observed_status IN ('starting','active','idle')
                 AND NOT EXISTS(
                     SELECT 1 FROM work_assignments a
                     WHERE a.agent_session_id=s.id
                       AND a.status IN ('offered','accepted','active')
                 )
               ORDER BY CASE s.observed_status
                   WHEN 'idle' THEN 0 WHEN 'active' THEN 1 ELSE 2 END,
                   s.started_at LIMIT 1""",
            (mission_id, provider_key, role),
            required=False,
        )
        if row is not None:
            return str(row["id"])
        if not auto_spawn:
            return None
        self.providers.get(provider_key)
        return self.agents.create_agent_session(
            mission_id=mission_id,
            provider=provider_key,
            role=role,
            metadata={"spawned_by": "controller"},
        )

    @staticmethod
    def _callback_expiry(ttl_seconds: int) -> str:
        return (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl_seconds)).isoformat(
            timespec="microseconds"
        )

    def _reserve_dispatch(
        self,
        *,
        work_id: str,
        agent_session_id: str,
        workspace_id: str | None,
        provider_key: str,
        callback_token: str,
        lease_ttl_seconds: int,
    ) -> dict[str, Any]:
        now = utc_now()
        callback_id = new_id("pcb")
        assignment_id = new_id("asn")
        execution_id = new_id("exe")
        with self.store.transaction() as db:
            work_row = db.execute("SELECT * FROM work_items WHERE id=?", (work_id,)).fetchone()
            if work_row is None:
                raise StoreError("work item not found")
            work = dict(work_row)
            mission = db.execute(
                "SELECT status,resource_limits_json FROM missions WHERE id=?",
                (work["mission_id"],),
            ).fetchone()
            if mission is None or mission["status"] != "active":
                raise InvalidTransition("work mission is not active")
            cancelling = db.execute(
                """SELECT id FROM external_effect_intents_v2
                   WHERE effect_type='provider_cancel' AND target_type='mission'
                     AND target_id=? AND status<>'cancelled' LIMIT 1""",
                (work["mission_id"],),
            ).fetchone()
            if cancelling is not None:
                raise InvalidTransition("mission provider cancellation is fenced")
            policy = SchedulingPolicy.from_resource_limits(mission["resource_limits_json"])
            if active_execution_count(self.store, work["mission_id"], db=db) >= policy.max_parallel:
                raise InvalidTransition("mission parallel execution limit is reached")
            prior_attempts = implementation_attempt_counts(self.store, [work_id], db=db).get(
                work_id, 0
            )
            if prior_attempts >= policy.max_attempts_per_work:
                raise InvalidTransition("work implementation attempt budget is exhausted")
            if self.adaptive is not None:
                self.adaptive.assert_strategy_allowed(work_id, db=db)
            if work["planning_status"] != "selected" or work["execution_status"] not in {
                "not_started",
                "abandoned",
            }:
                raise InvalidTransition("work is no longer dispatchable")
            active = db.execute(
                """SELECT id FROM executions WHERE work_item_id=?
                   AND status IN ('queued','dispatching','leased','running','verifying')""",
                (work_id,),
            ).fetchone()
            if active is not None:
                raise InvalidTransition("work already has an active execution")
            session = db.execute(
                "SELECT * FROM agent_sessions WHERE id=?", (agent_session_id,)
            ).fetchone()
            if session is None or session["mission_id"] != work["mission_id"]:
                raise InvalidTransition("agent session does not belong to the work mission")
            if session["provider"] != provider_key:
                raise InvalidTransition("agent provider does not match work provider")
            if session["role"] != work["required_role"]:
                raise InvalidTransition("agent role does not match required role")
            if session["observed_status"] in {"stopped", "lost", "unresponsive"}:
                raise InvalidTransition("agent is not available")
            competing_assignment = db.execute(
                """SELECT id FROM work_assignments WHERE agent_session_id=?
                   AND status IN ('offered','accepted','active')""",
                (agent_session_id,),
            ).fetchone()
            if competing_assignment is not None:
                raise InvalidTransition("agent already has an active assignment")
            workspace = None
            if workspace_id is not None:
                workspace = db.execute(
                    "SELECT * FROM workspaces WHERE id=?", (workspace_id,)
                ).fetchone()
                if workspace is None or workspace["work_item_id"] != work_id:
                    raise InvalidTransition("workspace does not belong to work")
                if workspace["status"] not in {"ready", "active", "retained"}:
                    raise InvalidTransition("workspace is not dispatchable")

            prompt = self._prompt_for_work(work)
            instructions_root = digest_json(
                {
                    "mission_id": work["mission_id"],
                    "work_item_id": work_id,
                    "program_revision_id": work["program_revision_id"],
                    "prompt": prompt,
                    "acceptance_spec": json_load(work["acceptance_spec_json"], {}),
                }
            )
            db.execute(
                """INSERT INTO work_assignments(
                    id,work_item_id,agent_session_id,workspace_id,role,status,
                    assignment_scope_json,instructions_root,lease_generation,
                    created_at,started_at,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    assignment_id,
                    work_id,
                    agent_session_id,
                    workspace_id,
                    work["required_role"],
                    "active",
                    canonical_json(
                        {
                            "paths": json_load(work["writable_scope_json"], []),
                            "repository_id": work["repository_id"],
                        }
                    ),
                    instructions_root,
                    0,
                    now,
                    now,
                    1,
                ),
            )
            if workspace_id is not None:
                db.execute(
                    """UPDATE workspaces SET owner_assignment_id=?,status='active',
                       updated_at=?,state_version=state_version+1 WHERE id=?""",
                    (assignment_id, now, workspace_id),
                )

            input_payload = {
                "prompt": prompt,
                "acceptance_spec": json_load(work["acceptance_spec_json"], {}),
                "expected_effect": json_load(work["expected_effect_json"], {}),
            }
            command_root = digest_json(
                {
                    "mission_id": work["mission_id"],
                    "work_item_id": work_id,
                    "assignment_id": assignment_id,
                    "workspace_id": workspace_id,
                    "provider_key": provider_key,
                    "input": input_payload,
                }
            )
            attempt_number = prior_attempts + 1
            db.execute(
                """INSERT INTO executions(
                    id,mission_id,obligation_id,work_item_id,agent_session_id,
                    assignment_id,execution_type,status,strategy_key,attempt_number,
                    idempotency_key,lease_generation,input_json,result_json,error_json,
                    limits_json,usage_json,created_at,workspace_id,command_root,
                    expected_effect_json,state_version,provider_key,provider_handle_json,
                    dispatch_attempts
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    execution_id,
                    work["mission_id"],
                    work["obligation_id"],
                    work_id,
                    agent_session_id,
                    assignment_id,
                    "implementation",
                    "dispatching",
                    work.get("strategy_key") or f"provider:{provider_key}",
                    attempt_number,
                    f"dispatch:{work_id}:{attempt_number}",
                    0,
                    canonical_json(input_payload),
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    now,
                    workspace_id,
                    command_root,
                    work["expected_effect_json"],
                    1,
                    provider_key,
                    "{}",
                    1,
                ),
            )

            resources = [{"kind": "work", "key": work_id, "mode": "exclusive"}]
            for path in json_load(work["writable_scope_json"], []):
                if path == "*":
                    resources.append(
                        {
                            "kind": "repository",
                            "key": work["repository_id"],
                            "repository_id": work["repository_id"],
                            "mode": "exclusive",
                        }
                    )
                elif work["repository_id"]:
                    resources.append(
                        {
                            "kind": "path",
                            "repository_id": work["repository_id"],
                            "path": path,
                            "mode": "exclusive",
                        }
                    )
            expired_rows = db.execute(
                """SELECT DISTINCT owner_execution_id FROM leases
                   WHERE status='active' AND julianday(expires_at)<=julianday(?)""",
                (now,),
            ).fetchall()
            if expired_rows:
                raise LeaseConflict("expired leases require controller recovery before dispatch")
            active_leases = [
                dict(row)
                for row in db.execute(
                    """SELECT * FROM leases WHERE status='active'
                       AND julianday(expires_at)>julianday(?)""",
                    (now,),
                )
            ]
            requested: list[dict[str, Any]] = []
            for resource in resources:
                key, repository_id, kind, path = _resource_key(resource)
                candidate = {
                    "resource_key": key,
                    "repository_id": repository_id,
                    "resource_kind": kind,
                    "resource_path": path,
                    "mode": resource["mode"],
                }
                conflict = next(
                    (lease for lease in active_leases if _leases_conflict(lease, candidate)),
                    None,
                )
                if conflict is not None:
                    raise LeaseConflict(
                        f"resource {key} conflicts with active lease {conflict['id']}"
                    )
                requested.append(candidate)
            resource_keys = [row["resource_key"] for row in requested]
            generation = 1
            if resource_keys:
                placeholders = ",".join("?" for _ in resource_keys)
                previous = db.execute(
                    f"SELECT MAX(generation) FROM leases WHERE resource_key IN ({placeholders})",
                    tuple(resource_keys),
                ).fetchone()[0]
                generation = int(previous or 0) + 1
            lease_expires_at = self._callback_expiry(lease_ttl_seconds)
            callback_expires_at = self._callback_expiry(max(lease_ttl_seconds * 4, 3600))
            for resource in requested:
                db.execute(
                    """INSERT INTO leases(
                        id,resource_key,mode,owner_execution_id,owner_assignment_id,
                        generation,status,expires_at,heartbeat_at,created_at,mission_id,
                        repository_id,resource_kind,resource_path
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        new_id("lea"),
                        resource["resource_key"],
                        resource["mode"],
                        execution_id,
                        assignment_id,
                        generation,
                        "active",
                        lease_expires_at,
                        now,
                        now,
                        work["mission_id"],
                        resource["repository_id"],
                        resource["resource_kind"],
                        resource["resource_path"],
                    ),
                )
            db.execute(
                """UPDATE executions SET status='leased',lease_generation=?,
                   state_version=state_version+1 WHERE id=?""",
                (generation, execution_id),
            )
            db.execute(
                """UPDATE work_assignments SET lease_generation=?,state_version=state_version+1
                   WHERE id=?""",
                (generation, assignment_id),
            )
            db.execute(
                """UPDATE work_items SET execution_status='queued',state_version=state_version+1,
                   updated_at=? WHERE id=?""",
                (now, work_id),
            )
            if work["obligation_id"]:
                db.execute(
                    """UPDATE obligations SET status='in_progress',updated_at=?,
                       state_version=state_version+1
                       WHERE id=? AND status IN ('open','ready','waiting_for_evidence')""",
                    (now, work["obligation_id"]),
                )
            db.execute(
                """INSERT INTO provider_callbacks(
                    id,execution_id,generation,token_sha256,status,expires_at,created_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    callback_id,
                    execution_id,
                    generation,
                    hashlib.sha256(callback_token.encode("utf-8")).hexdigest(),
                    "pending",
                    callback_expires_at,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="controller",
                event_type="controller.work_reserved",
                subject_type="execution",
                subject_id=execution_id,
                new_version=2,
                payload={
                    "work_item_id": work_id,
                    "assignment_id": assignment_id,
                    "workspace_id": workspace_id,
                    "agent_session_id": agent_session_id,
                    "provider_key": provider_key,
                    "generation": generation,
                    "resources": requested,
                },
            )
        return {
            "work_item_id": work_id,
            "execution_id": execution_id,
            "assignment_id": assignment_id,
            "workspace_id": workspace_id,
            "agent_session_id": agent_session_id,
            "provider_key": provider_key,
            "generation": generation,
            "callback_token": callback_token,
            "prompt": prompt,
            "instructions_root": instructions_root,
        }

    @staticmethod
    def _prompt_for_work(work: Mapping[str, Any]) -> str:
        acceptance = json_load(work["acceptance_spec_json"], {})
        expected = json_load(work["expected_effect_json"], {})
        scope = json_load(work["writable_scope_json"], [])
        return (
            f"Mission work item: {work['title']}\n\n"
            f"{work['description']}\n\n"
            f"Writable scope: {canonical_json(scope)}\n"
            f"Expected effect: {canonical_json(expected)}\n"
            f"Acceptance contract: {canonical_json(acceptance)}\n\n"
            "Implement the complete end-to-end effect. Preserve protected behavior, "
            "adapt when an approach is ineffective, run focused validation, commit the "
            "candidate in the assigned workspace, and report exact observed evidence."
        )

    def dispatch_work(
        self,
        work_id: str,
        *,
        auto_spawn: bool = True,
        lease_ttl_seconds: int = 900,
    ) -> dict[str, Any]:
        work = self.store.one("SELECT * FROM work_items WHERE id=?", (work_id,))
        mission = self.store.one(
            "SELECT status,resource_limits_json FROM missions WHERE id=?", (work["mission_id"],)
        )
        if mission["status"] != "active":
            raise InvalidTransition("work mission is not active")
        provider_key = str(work.get("provider_key") or self.default_provider or "")
        if not provider_key:
            raise InvalidTransition("work has no provider and no default provider is configured")
        provider = self.providers.get(provider_key)
        self.recover_expired_provider_executions()
        policy = SchedulingPolicy.from_resource_limits(mission["resource_limits_json"])
        if active_execution_count(self.store, work["mission_id"]) >= policy.max_parallel:
            raise InvalidTransition("mission parallel execution limit is reached")
        prior_attempts = implementation_attempt_counts(self.store, [work_id]).get(work_id, 0)
        if prior_attempts >= policy.max_attempts_per_work:
            raise InvalidTransition("work implementation attempt budget is exhausted")
        repository_id = self._resolve_repository(work)
        work = self.store.one("SELECT * FROM work_items WHERE id=?", (work_id,))
        workspace_id = self._ensure_workspace(work, repository_id)
        agent_session_id = self._choose_agent(
            mission_id=work["mission_id"],
            provider_key=provider_key,
            role=work["required_role"],
            auto_spawn=auto_spawn,
        )
        if agent_session_id is None:
            raise InvalidTransition("no compatible agent session is available")
        callback_token = secrets.token_urlsafe(32)
        reservation = self._reserve_dispatch(
            work_id=work_id,
            agent_session_id=agent_session_id,
            workspace_id=workspace_id,
            provider_key=provider_key,
            callback_token=callback_token,
            lease_ttl_seconds=lease_ttl_seconds,
        )
        execution_path = (
            self.workspaces.workspace_path(workspace_id)
            if workspace_id
            else (
                self.workspaces.repository_path(repository_id)
                if repository_id
                else self.store.path.parent.resolve()
            )
        )
        request = ProviderRequest(
            execution_id=reservation["execution_id"],
            mission_id=work["mission_id"],
            work_item_id=work_id,
            assignment_id=reservation["assignment_id"],
            workspace_id=workspace_id or "",
            workspace_path=execution_path,
            lease_generation=reservation["generation"],
            role=work["required_role"],
            prompt=reservation["prompt"],
            context={
                "workspace_path": str(execution_path),
                "instructions_root": reservation["instructions_root"],
            },
        )
        try:
            observation = provider.dispatch(request)
        except Exception as exc:
            self._abandon_dispatch(
                reservation["execution_id"],
                reservation["generation"],
                reason={"type": type(exc).__name__, "message": str(exc)},
                work_status="failed",
            )
            raise ProviderError(
                f"provider {provider_key} failed to dispatch {work_id}: {exc}"
            ) from exc
        self._apply_provider_observation(
            reservation["execution_id"],
            reservation["generation"],
            observation,
            callback_consumed=observation.status in {"succeeded", "failed"},
        )
        return {
            key: value
            for key, value in reservation.items()
            if key not in {"callback_token", "prompt"}
        } | {"provider_status": observation.status}

    def _apply_provider_observation(
        self,
        execution_id: str,
        generation: int,
        observation: ProviderObservation,
        *,
        callback_consumed: bool = False,
    ) -> None:
        handle = dict(observation.handle)
        handle.setdefault("execution_id", execution_id)
        if observation.status == "running":
            with self.store.transaction() as db:
                execution = db.execute(
                    "SELECT * FROM executions WHERE id=?", (execution_id,)
                ).fetchone()
                if execution is None:
                    raise StoreError("execution not found")
                self.executions._assert_generation(db, execution, generation)
                db.execute(
                    """UPDATE executions SET status='running',provider_handle_json=?,
                       last_provider_poll_at=?,started_at=COALESCE(started_at,?),
                       state_version=state_version+1 WHERE id=?""",
                    (canonical_json(handle), utc_now(), utc_now(), execution_id),
                )
                if execution["work_item_id"]:
                    db.execute(
                        """UPDATE work_items SET execution_status='running',updated_at=?,
                           state_version=state_version+1 WHERE id=?""",
                        (utc_now(), execution["work_item_id"]),
                    )
                db.execute(
                    """UPDATE agent_sessions SET observed_status='active',
                       external_thread_id=COALESCE(?,external_thread_id),
                       external_task_id=COALESCE(?,external_task_id),last_heartbeat_at=?,
                       state_version=state_version+1 WHERE id=?""",
                    (
                        observation.external_thread_id,
                        observation.external_task_id,
                        utc_now(),
                        execution["agent_session_id"],
                    ),
                )
            return
        if observation.status in {"succeeded", "failed"}:
            if callback_consumed:
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE provider_callbacks SET status='used',used_at=?
                           WHERE execution_id=? AND status='pending'""",
                        (utc_now(), execution_id),
                    )
            payload = dict(
                observation.result if observation.status == "succeeded" else observation.error
            )
            payload["provider_handle"] = handle
            payload["provider_usage"] = dict(observation.usage)
            self.executions.complete_external_execution(
                execution_id,
                generation=generation,
                result=payload,
                succeeded=observation.status == "succeeded",
                usage=observation.usage,
                stdout=observation.stdout,
                stderr=observation.stderr,
            )
            if self.adaptive is not None:
                self.adaptive.observe_execution(execution_id)
            return
        if observation.status in {"lost", "cancelled"}:
            self._abandon_dispatch(
                execution_id,
                generation,
                reason=dict(observation.error) | {"provider_status": observation.status},
                cancelled=observation.status == "cancelled",
            )

    def _abandon_dispatch(
        self,
        execution_id: str,
        generation: int,
        *,
        reason: Mapping[str, Any],
        cancelled: bool = False,
        work_status: str = "abandoned",
        allow_expired_lease: bool = False,
    ) -> None:
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None:
                raise StoreError("execution not found")
            if execution["status"] in {"succeeded", "failed", "cancelled", "invalidated"}:
                return
            if allow_expired_lease:
                if int(execution["lease_generation"] or 0) != generation:
                    raise StaleLease("execution lease generation is stale")
                active_lease = db.execute(
                    """SELECT id FROM leases WHERE owner_execution_id=?
                       AND status='active' AND generation=? LIMIT 1""",
                    (execution_id, generation),
                ).fetchone()
                if active_lease is None:
                    raise StaleLease("execution has no active owned lease")
            else:
                self.executions._assert_generation(db, execution, generation)
            status = "cancelled" if cancelled else "abandoned"
            now = utc_now()
            db.execute(
                """UPDATE executions SET status=?,error_json=?,finished_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (status, canonical_json(dict(reason)), now, execution_id),
            )
            db.execute(
                """UPDATE leases SET status=?,released_at=?
                   WHERE owner_execution_id=? AND status='active' AND generation=?""",
                ("revoked" if cancelled else "released", now, execution_id, generation),
            )
            if execution["assignment_id"]:
                db.execute(
                    """UPDATE work_assignments SET status='released',released_at=?,
                       state_version=state_version+1 WHERE id=?""",
                    (now, execution["assignment_id"]),
                )
            if execution["workspace_id"]:
                db.execute(
                    """UPDATE workspaces SET owner_assignment_id=NULL,status='retained',
                       updated_at=?,state_version=state_version+1 WHERE id=?""",
                    (now, execution["workspace_id"]),
                )
            if execution["agent_session_id"]:
                db.execute(
                    """UPDATE agent_sessions SET observed_status='idle',last_heartbeat_at=?,
                       state_version=state_version+1 WHERE id=?
                       AND observed_status NOT IN ('lost','stopped')""",
                    (now, execution["agent_session_id"]),
                )
            if work_status not in {"abandoned", "failed", "cancelled"}:
                raise ValueError("unsupported work status for abandoned dispatch")
            if execution["work_item_id"]:
                db.execute(
                    """UPDATE work_items SET execution_status=?,updated_at=?,
                       state_version=state_version+1 WHERE id=?""",
                    (work_status, now, execution["work_item_id"]),
                )
            db.execute(
                """UPDATE provider_callbacks SET status='revoked',used_at=?
                   WHERE execution_id=? AND status='pending'""",
                (now, execution_id),
            )
            self.store.append_event(
                db,
                mission_id=execution["mission_id"],
                stream_key="controller",
                event_type=f"provider.{status}",
                subject_type="execution",
                subject_id=execution_id,
                payload=dict(reason),
            )
        if self.adaptive is not None:
            self.adaptive.observe_execution(execution_id)

    def _cancel_recovered_provider(self, execution_id: str) -> dict[str, Any] | None:
        execution = self.store.one(
            "SELECT provider_key,provider_handle_json,mission_id FROM executions WHERE id=?",
            (execution_id,),
        )
        handle = json_load(execution["provider_handle_json"], {})
        provider_key = execution["provider_key"]
        if not provider_key or not handle:
            return None
        try:
            observation = self.providers.get(provider_key).cancel(handle)
        except Exception as exc:
            with self.store.transaction() as db:
                self.store.append_event(
                    db,
                    mission_id=execution["mission_id"],
                    stream_key="controller",
                    event_type="provider.cancel_failed_before_recovery",
                    subject_type="execution",
                    subject_id=execution_id,
                    payload={"type": type(exc).__name__, "message": str(exc)},
                )
            return {
                "execution_id": execution_id,
                "status": "cancel_failed",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        with self.store.transaction() as db:
            self.store.append_event(
                db,
                mission_id=execution["mission_id"],
                stream_key="controller",
                event_type="provider.cancelled_before_recovery",
                subject_type="execution",
                subject_id=execution_id,
                payload={"provider_status": observation.status},
            )
        return {"execution_id": execution_id, "status": observation.status}

    def recover_expired_provider_executions(
        self, *, mission_id: str | None = None
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Cancel provider work before releasing its expired Factory authority."""

        expired = self.executions.expired_execution_ids(mission_id=mission_id)
        authorized: list[str] = []
        cancellations: list[dict[str, Any]] = []
        for execution_id in expired:
            execution = self.store.one(
                "SELECT provider_key,provider_handle_json FROM executions WHERE id=?",
                (execution_id,),
            )
            handle = json_load(execution["provider_handle_json"], {})
            if execution["provider_key"] and handle:
                cancellation = self._cancel_recovered_provider(execution_id)
                if cancellation is None:
                    continue
                cancellations.append(cancellation)
                if cancellation["status"] != "cancelled":
                    continue
            authorized.append(execution_id)
        recovered = self.executions.recover_expired_leases(
            mission_id=mission_id,
            provider_cancelled_execution_ids=authorized,
        )
        return recovered, cancellations

    def _active_provider_executions(self, mission_id: str) -> list[dict[str, Any]]:
        return self.store.all(
            """SELECT * FROM executions WHERE mission_id=? AND status IN (
                   'queued','dispatching','leased','running','verifying'
               ) ORDER BY created_at,id""",
            (mission_id,),
        )

    def cancel_mission_provider_executions(self, mission_id: str, *, reason: str) -> str:
        """Fence new dispatch, cancel exact provider handles, then release authority."""

        if not reason.strip():
            raise ValueError("mission cancellation requires a reason")
        self.store.one("SELECT id FROM missions WHERE id=?", (mission_id,))
        effect = self.governance.claim_effect(
            effect_type="provider_cancel",
            target_type="mission",
            target_id=mission_id,
            idempotency_key=f"mission-provider-cancel:{mission_id}",
            request={"mission_id": mission_id},
            probe_spec={"terminal_provider_status": "cancelled"},
            mission_id=mission_id,
        )
        if effect["status"] == "succeeded":
            return str(effect["id"])
        if effect["status"] in {"claimed", "failed"}:
            effect = self.governance.start_effect(
                effect["id"],
                lease_owner="factory-engine",
                lease_expires_at=self._callback_expiry(60),
            )
        try:
            cancelled: list[dict[str, Any]] = []
            for execution in self._active_provider_executions(mission_id):
                handle = json_load(execution["provider_handle_json"], {})
                if not execution["provider_key"] or not handle:
                    raise ProviderError(
                        "active execution cannot be cancelled before its provider handle is durable"
                    )
                observation = self.providers.get(str(execution["provider_key"])).cancel(handle)
                if observation.status != "cancelled":
                    raise ProviderError("provider cancellation did not reach a terminal state")
                self._abandon_dispatch(
                    str(execution["id"]),
                    int(execution["lease_generation"]),
                    reason={"kind": "mission_cancelled_by_authority", "reason": reason},
                    cancelled=True,
                    work_status="cancelled",
                    allow_expired_lease=True,
                )
                cancelled.append(
                    {
                        "execution_id": str(execution["id"]),
                        "provider_status": observation.status,
                    }
                )
            self.governance.observe_effect(
                effect["id"],
                provider_reference="factory-provider-registry",
                observed_result={"cancelled_executions": cancelled},
            )
        except Exception as exc:
            self.governance.complete_effect(
                effect["id"],
                succeeded=False,
                error={"type": type(exc).__name__},
            )
            raise
        return str(effect["id"])

    def fail_mission_cancellation(self, effect_id: str, error: Exception) -> None:
        effect = self.store.one(
            "SELECT status FROM external_effect_intents_v2 WHERE id=?", (effect_id,)
        )
        if effect["status"] in {"observed", "started", "ambiguous"}:
            self.governance.complete_effect(
                effect_id,
                succeeded=False,
                error={"type": type(error).__name__},
            )

    def complete_mission_cancellation(self, effect_id: str) -> None:
        effect = self.store.one(
            "SELECT status FROM external_effect_intents_v2 WHERE id=?", (effect_id,)
        )
        if effect["status"] == "succeeded":
            return
        self.governance.complete_effect(effect_id, succeeded=True)

    def accept_provider_callback(
        self,
        execution_id: str,
        *,
        token: str,
        generation: int,
        succeeded: bool,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.store.transaction() as db:
            callback = db.execute(
                "SELECT * FROM provider_callbacks WHERE execution_id=?", (execution_id,)
            ).fetchone()
            if callback is None or callback["status"] != "pending":
                raise InvalidTransition("provider callback is not pending")
            expires = parse_time(callback["expires_at"])
            if expires is None or expires <= dt.datetime.now(dt.UTC):
                db.execute(
                    "UPDATE provider_callbacks SET status='expired' WHERE id=?",
                    (callback["id"],),
                )
                raise StaleLease("provider callback expired")
            if callback["generation"] != generation:
                raise StaleLease("provider callback generation is stale")
            if not hmac.compare_digest(callback["token_sha256"], token_hash):
                raise InvalidTransition("provider callback token is invalid")
            db.execute(
                "UPDATE provider_callbacks SET status='used',used_at=? WHERE id=?",
                (utc_now(), callback["id"]),
            )
            self.executions.complete_external_execution(
                execution_id,
                generation=generation,
                result=dict(result),
                succeeded=succeeded,
            )
        if self.adaptive is not None:
            self.adaptive.observe_execution(execution_id)
        return self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))

    def poll_provider_executions(self, mission_id: str | None = None) -> list[dict[str, Any]]:
        query = """SELECT * FROM executions
                   WHERE status IN ('leased','running','dispatching')
                     AND provider_key IS NOT NULL AND provider_handle_json<>'{}'"""
        parameters: tuple[Any, ...] = ()
        if mission_id is not None:
            query += " AND mission_id=?"
            parameters = (mission_id,)
        query += " ORDER BY created_at"
        updates: list[dict[str, Any]] = []
        for execution in self.store.all(query, parameters):
            try:
                provider = self.providers.get(execution["provider_key"])
                observation = provider.poll(json_load(execution["provider_handle_json"], {}))
            except Exception as exc:
                now = utc_now()
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE executions SET last_provider_poll_at=?,error_json=?,
                           state_version=state_version+1 WHERE id=?""",
                        (
                            now,
                            canonical_json(
                                {
                                    "type": type(exc).__name__,
                                    "message": str(exc),
                                    "phase": "provider_poll",
                                }
                            ),
                            execution["id"],
                        ),
                    )
                    self.store.append_event(
                        db,
                        mission_id=execution["mission_id"],
                        stream_key="controller",
                        event_type="provider.poll_failed",
                        subject_type="execution",
                        subject_id=execution["id"],
                        payload={"type": type(exc).__name__, "message": str(exc)},
                    )
                updates.append(
                    {
                        "execution_id": execution["id"],
                        "status": "poll_failed",
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
                continue
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE executions SET last_provider_poll_at=? WHERE id=?",
                    (utc_now(), execution["id"]),
                )
            if observation.status == "running":
                self.executions.heartbeat_execution(
                    execution["id"], generation=execution["lease_generation"], ttl_seconds=900
                )
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE provider_callbacks SET expires_at=?
                           WHERE execution_id=? AND status='pending'""",
                        (self._callback_expiry(3600), execution["id"]),
                    )
            else:
                self._apply_provider_observation(
                    execution["id"],
                    execution["lease_generation"],
                    observation,
                    callback_consumed=observation.status in {"succeeded", "failed"},
                )
            updates.append({"execution_id": execution["id"], "status": observation.status})
        return updates

    def tick_mission(
        self,
        mission_id: str,
        *,
        max_dispatch: int | None = None,
        auto_spawn: bool = True,
    ) -> dict[str, Any]:
        recovered, recovered_provider_cancellations = self.recover_expired_provider_executions(
            mission_id=mission_id
        )
        provider_updates = self.poll_provider_executions(mission_id)
        adaptive_updates = (
            self.adaptive.observe_new_execution_outcomes(mission_id)
            if self.adaptive is not None
            else []
        )
        supervision_updates = (
            self.supervision.run_due_checks(mission_id) if self.supervision is not None else []
        )
        mission = self.store.one(
            "SELECT resource_limits_json FROM missions WHERE id=?", (mission_id,)
        )
        policy = SchedulingPolicy.from_resource_limits(mission["resource_limits_json"])
        requested_limit = policy.tick_limit(max_dispatch)
        posture = self.continuation.next_action(mission_id)
        generated_problem_solving: list[str] = []
        if posture["action"] == "diagnose_reflect_or_replan" and self.adaptive is not None:
            generated_problem_solving = self.adaptive.ensure_problem_solving(mission_id)
            posture = self.continuation.next_action(mission_id)
        dispatches: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        if posture["action"] == "dispatch_ready_work":
            ready_ids = posture["work_item_ids"][:requested_limit]
            for work_id in ready_ids:
                try:
                    dispatches.append(self.dispatch_work(work_id, auto_spawn=auto_spawn))
                except (InvalidTransition, KeyError, LeaseConflict, ProviderError) as exc:
                    blocked.append(
                        {
                            "work_item_id": work_id,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    )
        if blocked and self.adaptive is not None:
            blocked_ids = [item["work_item_id"] for item in blocked]
            placeholders = ",".join("?" for _ in blocked_ids)
            rows = self.store.all(
                f"""SELECT DISTINCT id FROM work_items
                    WHERE mission_id=? AND parent_id IN ({placeholders})
                      AND work_type='semantic_experiment'
                      AND planning_status IN ('proposed','selected')
                      AND execution_status IN ('not_started','queued')""",
                (mission_id, *blocked_ids),
            )
            generated_problem_solving.extend(str(row["id"]) for row in rows)
            generated_problem_solving = sorted(set(generated_problem_solving))
        final_posture = self.continuation.next_action(mission_id)
        result = {
            "mission_id": mission_id,
            "recovered_execution_ids": recovered,
            "recovered_provider_cancellations": recovered_provider_cancellations,
            "provider_updates": provider_updates,
            "adaptive_updates": adaptive_updates,
            "supervision_updates": supervision_updates,
            "generated_problem_solving_work": generated_problem_solving,
            "scheduling_policy": policy.as_dict(),
            "requested_dispatch_limit": requested_limit,
            "initial_posture": posture,
            "dispatches": dispatches,
            "dispatch_blockers": blocked,
            "posture": final_posture,
        }
        with self.store.transaction() as db:
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="controller",
                event_type="controller.tick_completed",
                subject_type="mission",
                subject_id=mission_id,
                payload=result,
            )
        return result

    def tick_all(self, *, max_dispatch_per_mission: int | None = None) -> list[dict[str, Any]]:
        rows = self.store.all(
            """SELECT id FROM missions
               WHERE status IN ('active','terminal_verification') ORDER BY created_at"""
        )
        return [self.tick_mission(row["id"], max_dispatch=max_dispatch_per_mission) for row in rows]
