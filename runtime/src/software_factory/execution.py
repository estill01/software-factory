from __future__ import annotations

import datetime as dt
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .artifacts import ArtifactService
from .errors import InvalidTransition, LeaseConflict, StaleLease, StoreError
from .util import (
    canonical_json,
    digest_json,
    json_load,
    new_id,
    normalize_relative_path,
    parse_time,
    utc_now,
)

_TERMINAL_EXECUTION_STATES = {"succeeded", "failed", "abandoned", "cancelled", "invalidated"}


def _resource_key(resource: Mapping[str, Any]) -> tuple[str, str | None, str, str | None]:
    kind = str(resource.get("kind") or "generic")
    repository_id = resource.get("repository_id")
    path = resource.get("path")
    key = resource.get("key")
    if kind == "path":
        if not repository_id or path is None:
            raise ValueError("path lease requires repository_id and path")
        normalized = normalize_relative_path(str(path))
        return f"repo:{repository_id}:path:{normalized}", str(repository_id), kind, normalized
    if not key:
        raise ValueError(f"{kind} lease requires key")
    return f"{kind}:{key}", str(repository_id) if repository_id else None, kind, None


def _leases_conflict(existing: Mapping[str, Any], requested: Mapping[str, Any]) -> bool:
    if existing["mode"] == "read" and requested["mode"] == "read":
        return False
    if existing["resource_kind"] == "path" and requested["resource_kind"] == "path":
        if existing["repository_id"] != requested["repository_id"]:
            return False
        left = existing["resource_path"]
        right = requested["resource_path"]
        return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")
    return existing["resource_key"] == requested["resource_key"]


class ExecutionService:
    """Durable execution, fenced resource ownership, observed commands, and recovery."""

    def __init__(self, store: Any, artifacts: ArtifactService | None = None):
        self.store = store
        self.artifacts = artifacts or ArtifactService(store)

    def queue_execution(
        self,
        *,
        mission_id: str,
        execution_type: str,
        idempotency_key: str,
        work_item_id: str | None = None,
        obligation_id: str | None = None,
        experiment_id: str | None = None,
        agent_session_id: str | None = None,
        assignment_id: str | None = None,
        workspace_id: str | None = None,
        strategy_key: str | None = None,
        input_payload: dict[str, Any] | None = None,
        limits: dict[str, Any] | None = None,
        expected_effect: dict[str, Any] | None = None,
    ) -> str:
        existing = self.store.one(
            "SELECT id FROM executions WHERE idempotency_key=?",
            (idempotency_key,),
            required=False,
        )
        if existing is not None:
            return str(existing["id"])
        execution_id = new_id("exe")
        now = utc_now()
        with self.store.transaction() as db:
            if work_item_id:
                work = db.execute("SELECT * FROM work_items WHERE id=?", (work_item_id,)).fetchone()
                if work is None or work["mission_id"] != mission_id:
                    raise InvalidTransition(
                        "execution work item is missing or belongs to another mission"
                    )
            if agent_session_id:
                session = db.execute(
                    "SELECT * FROM agent_sessions WHERE id=?", (agent_session_id,)
                ).fetchone()
                if session is None or session["mission_id"] != mission_id:
                    raise InvalidTransition("execution agent belongs to another mission")
            if assignment_id:
                assignment = db.execute(
                    "SELECT * FROM work_assignments WHERE id=?", (assignment_id,)
                ).fetchone()
                if assignment is None or assignment["work_item_id"] != work_item_id:
                    raise InvalidTransition("execution assignment does not own the work item")
                if agent_session_id and assignment["agent_session_id"] != agent_session_id:
                    raise InvalidTransition("execution session does not own the assignment")
                if workspace_id and assignment["workspace_id"] != workspace_id:
                    raise InvalidTransition("execution workspace does not match assignment")
            command_root = digest_json(
                {
                    "mission_id": mission_id,
                    "work_item_id": work_item_id,
                    "execution_type": execution_type,
                    "agent_session_id": agent_session_id,
                    "assignment_id": assignment_id,
                    "workspace_id": workspace_id,
                    "strategy_key": strategy_key,
                    "input": input_payload or {},
                    "limits": limits or {},
                    "expected_effect": expected_effect or {},
                }
            )
            db.execute(
                """INSERT INTO executions(
                    id,mission_id,obligation_id,work_item_id,experiment_id,agent_session_id,
                    assignment_id,execution_type,status,strategy_key,attempt_number,
                    idempotency_key,input_json,result_json,error_json,limits_json,usage_json,
                    created_at,workspace_id,command_root,expected_effect_json,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    execution_id,
                    mission_id,
                    obligation_id,
                    work_item_id,
                    experiment_id,
                    agent_session_id,
                    assignment_id,
                    execution_type,
                    "queued",
                    strategy_key,
                    1,
                    idempotency_key,
                    canonical_json(input_payload or {}),
                    "{}",
                    "{}",
                    canonical_json(limits or {}),
                    "{}",
                    now,
                    workspace_id,
                    command_root,
                    canonical_json(expected_effect or {}),
                    1,
                ),
            )
            if work_item_id:
                db.execute(
                    """UPDATE work_items SET execution_status='queued',updated_at=?
                       WHERE id=? AND execution_status IN ('not_started','abandoned','failed')""",
                    (now, work_item_id),
                )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="execution",
                event_type="execution.queued",
                subject_type="execution",
                subject_id=execution_id,
                new_version=1,
                payload={
                    "execution_type": execution_type,
                    "work_item_id": work_item_id,
                    "assignment_id": assignment_id,
                    "workspace_id": workspace_id,
                    "command_root": command_root,
                },
            )
        return execution_id

    def acquire_leases(
        self,
        execution_id: str,
        resources: list[dict[str, Any]],
        *,
        ttl_seconds: int = 300,
    ) -> int:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None or execution["status"] not in {"queued", "dispatching"}:
                raise InvalidTransition("only queued/dispatching execution can acquire leases")
            assignment = None
            if execution["assignment_id"]:
                assignment = db.execute(
                    "SELECT * FROM work_assignments WHERE id=?", (execution["assignment_id"],)
                ).fetchone()
                if assignment is None or assignment["status"] not in {"accepted", "active"}:
                    raise InvalidTransition("execution assignment is not active")
            active = [dict(row) for row in db.execute("SELECT * FROM leases WHERE status='active'")]
            requested_rows: list[dict[str, Any]] = []
            for resource in resources:
                mode = str(resource.get("mode") or "exclusive")
                if mode not in {"read", "write", "exclusive"}:
                    raise ValueError(f"unsupported lease mode: {mode}")
                key, repository_id, kind, path = _resource_key(resource)
                requested = {
                    "resource_key": key,
                    "repository_id": repository_id,
                    "resource_kind": kind,
                    "resource_path": path,
                    "mode": mode,
                }
                conflict = next(
                    (
                        lease
                        for lease in active
                        if lease["owner_execution_id"] != execution_id
                        and _leases_conflict(lease, requested)
                    ),
                    None,
                )
                if conflict is not None:
                    raise LeaseConflict(
                        f"resource {key} conflicts with active lease {conflict['id']}"
                    )
                requested_rows.append(requested)
            generation = int(execution["lease_generation"] or 0) + 1
            if assignment is not None:
                generation = max(generation, int(assignment["lease_generation"] or 0) + 1)
            now = dt.datetime.now(dt.UTC)
            expires = (now + dt.timedelta(seconds=ttl_seconds)).isoformat(timespec="microseconds")
            for requested in requested_rows:
                db.execute(
                    """INSERT INTO leases(
                        id,resource_key,mode,owner_execution_id,owner_assignment_id,generation,
                        status,expires_at,heartbeat_at,created_at,mission_id,repository_id,
                        resource_kind,resource_path
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        new_id("lea"),
                        requested["resource_key"],
                        requested["mode"],
                        execution_id,
                        execution["assignment_id"],
                        generation,
                        "active",
                        expires,
                        now.isoformat(timespec="microseconds"),
                        now.isoformat(timespec="microseconds"),
                        execution["mission_id"],
                        requested["repository_id"],
                        requested["resource_kind"],
                        requested["resource_path"],
                    ),
                )
            db.execute(
                """UPDATE executions SET status='leased',lease_generation=?,state_version=state_version+1
                   WHERE id=?""",
                (generation, execution_id),
            )
            if assignment is not None:
                db.execute(
                    """UPDATE work_assignments SET status='active',lease_generation=?,
                       started_at=COALESCE(started_at,?),state_version=state_version+1 WHERE id=?""",
                    (generation, utc_now(), assignment["id"]),
                )
            if execution["work_item_id"]:
                db.execute(
                    "UPDATE work_items SET execution_status='running',updated_at=? WHERE id=?",
                    (utc_now(), execution["work_item_id"]),
                )
            self.store.append_event(
                db,
                mission_id=execution["mission_id"],
                stream_key="lease",
                event_type="execution.leased",
                subject_type="execution",
                subject_id=execution_id,
                payload={
                    "generation": generation,
                    "resources": requested_rows,
                    "expires_at": expires,
                },
            )
        return generation

    def _assert_generation(self, db: Any, execution: Mapping[str, Any], generation: int) -> None:
        if int(execution["lease_generation"] or 0) != generation:
            raise StaleLease("execution lease generation is stale")
        rows = db.execute(
            "SELECT generation,status,expires_at FROM leases WHERE owner_execution_id=?",
            (execution["id"],),
        ).fetchall()
        if not rows:
            raise StaleLease("execution has no active leases")
        now = dt.datetime.now(dt.UTC)
        for row in rows:
            if row["status"] != "active" or row["generation"] != generation:
                raise StaleLease("execution lease is no longer active")
            expires_at = parse_time(row["expires_at"])
            if expires_at is None or expires_at <= now:
                raise StaleLease("execution lease expired")

    def heartbeat_execution(
        self,
        execution_id: str,
        *,
        generation: int,
        ttl_seconds: int = 300,
    ) -> None:
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None:
                raise StoreError("execution not found")
            self._assert_generation(db, execution, generation)
            now = dt.datetime.now(dt.UTC)
            expires = (now + dt.timedelta(seconds=ttl_seconds)).isoformat(timespec="microseconds")
            db.execute(
                """UPDATE leases SET heartbeat_at=?,expires_at=?
                   WHERE owner_execution_id=? AND status='active' AND generation=?""",
                (now.isoformat(timespec="microseconds"), expires, execution_id, generation),
            )
            if execution["agent_session_id"]:
                db.execute(
                    """UPDATE agent_sessions SET last_heartbeat_at=?,observed_status='active'
                       WHERE id=?""",
                    (utc_now(), execution["agent_session_id"]),
                )

    def start_execution(self, execution_id: str, *, generation: int) -> None:
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None or execution["status"] not in {"leased", "running"}:
                raise InvalidTransition("execution must be leased before start")
            self._assert_generation(db, execution, generation)
            db.execute(
                """UPDATE executions SET status='running',started_at=COALESCE(started_at,?),
                   state_version=state_version+1 WHERE id=?""",
                (utc_now(), execution_id),
            )

    def release_execution_leases(self, execution_id: str, *, generation: int) -> None:
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None:
                raise StoreError("execution not found")
            if int(execution["lease_generation"] or 0) != generation:
                raise StaleLease("cannot release stale generation")
            db.execute(
                """UPDATE leases SET status='released',released_at=?
                   WHERE owner_execution_id=? AND status='active' AND generation=?""",
                (utc_now(), execution_id, generation),
            )

    def run_command(
        self,
        execution_id: str,
        command: Sequence[str],
        *,
        generation: int,
        timeout_seconds: int = 300,
        env_overrides: Mapping[str, str] | None = None,
        allowed_exit_codes: set[int] | None = None,
    ) -> dict[str, Any]:
        if not command or any(not isinstance(part, str) for part in command):
            raise ValueError("command must be a nonempty argument vector")
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if not execution["workspace_id"]:
            raise InvalidTransition("observed command execution requires a workspace")
        workspace = self.store.one(
            "SELECT * FROM workspaces WHERE id=?", (execution["workspace_id"],)
        )
        work = (
            self.store.one("SELECT * FROM work_items WHERE id=?", (execution["work_item_id"],))
            if execution["work_item_id"]
            else None
        )
        self.start_execution(execution_id, generation=generation)
        path = Path(workspace["path"])
        before = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=True
        ).stdout.strip()
        env = os.environ.copy()
        env.update({str(key): str(value) for key, value in (env_overrides or {}).items()})
        started = dt.datetime.now(dt.UTC)
        try:
            process = subprocess.run(
                list(command),
                cwd=path,
                env=env,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            process = subprocess.CompletedProcess(
                args=list(command),
                returncode=124,
                stdout=exc.stdout or b"",
                stderr=(exc.stderr or b"") + b"\nsoftware-factory: timeout",
            )
            timed_out = True
        finished = dt.datetime.now(dt.UTC)
        stdout = process.stdout if isinstance(process.stdout, bytes) else process.stdout.encode()
        stderr = process.stderr if isinstance(process.stderr, bytes) else process.stderr.encode()
        stdout_id = self.artifacts.store_bytes(
            stdout,
            mission_id=execution["mission_id"],
            producer_execution_id=execution_id,
            media_type="text/plain",
            subject_type="execution",
            subject_id=execution_id,
            metadata={"stream": "stdout"},
        )
        stderr_id = self.artifacts.store_bytes(
            stderr,
            mission_id=execution["mission_id"],
            producer_execution_id=execution_id,
            media_type="text/plain",
            subject_type="execution",
            subject_id=execution_id,
            metadata={"stream": "stderr"},
        )
        after = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=True
        ).stdout.strip()
        changed_output = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=path,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        dirty_files = sorted(
            {
                normalize_relative_path(line[3:].split(" -> ")[-1])
                for line in changed_output.splitlines()
                if len(line) >= 4
            }
        )
        committed_output = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACDMRTUXB",
                workspace["base_revision"],
                after,
            ],
            cwd=path,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        committed_files = sorted(
            {
                normalize_relative_path(line)
                for line in committed_output.splitlines()
                if line.strip()
            }
        )
        changed_files = sorted(set(dirty_files) | set(committed_files))
        allowed_scope = json_load(work["writable_scope_json"], []) if work else []
        scope_violations = [
            name
            for name in changed_files
            if allowed_scope
            and "*" not in allowed_scope
            and not any(name == scope or name.startswith(f"{scope}/") for scope in allowed_scope)
        ]
        accepted_codes = allowed_exit_codes or {0}
        success = process.returncode in accepted_codes and not scope_violations
        failure_fingerprint = None
        if not success:
            failure_fingerprint = digest_json(
                {
                    "command": list(command),
                    "exit_code": process.returncode,
                    "stderr_tail": stderr.decode("utf-8", errors="replace")[-2000:],
                    "scope_violations": scope_violations,
                    "timed_out": timed_out,
                }
            )
        observed = {
            "command": list(command),
            "exit_code": process.returncode,
            "timed_out": timed_out,
            "duration_seconds": (finished - started).total_seconds(),
            "dirty_files": dirty_files,
            "committed_files": committed_files,
            "changed_files": changed_files,
            "scope_violations": scope_violations,
            "source_revision_before": before,
            "source_revision_after": after,
        }
        with self.store.transaction() as db:
            current = db.execute("SELECT * FROM executions WHERE id=?", (execution_id,)).fetchone()
            self._assert_generation(db, current, generation)
            status = "succeeded" if success else "failed"
            db.execute(
                """UPDATE executions SET status=?,result_json=?,error_json=?,usage_json=?,
                   observed_effect_json=?,source_revision_before=?,source_revision_after=?,
                   exit_code=?,stdout_artifact_id=?,stderr_artifact_id=?,failure_fingerprint=?,
                   finished_at=?,state_version=state_version+1 WHERE id=?""",
                (
                    status,
                    canonical_json(observed if success else {}),
                    canonical_json({} if success else observed),
                    canonical_json({"duration_seconds": observed["duration_seconds"]}),
                    canonical_json(observed),
                    before,
                    after,
                    process.returncode,
                    stdout_id,
                    stderr_id,
                    failure_fingerprint,
                    utc_now(),
                    execution_id,
                ),
            )
            db.execute(
                """UPDATE leases SET status='released',released_at=?
                   WHERE owner_execution_id=? AND status='active' AND generation=?""",
                (utc_now(), execution_id, generation),
            )
            if current["assignment_id"]:
                db.execute(
                    """UPDATE work_assignments SET status=?,completed_at=?,state_version=state_version+1
                       WHERE id=?""",
                    ("completed" if success else "released", utc_now(), current["assignment_id"]),
                )
            if current["work_item_id"]:
                db.execute(
                    """UPDATE work_items SET execution_status=?,updated_at=? WHERE id=?""",
                    ("submitted" if success else "failed", utc_now(), current["work_item_id"]),
                )
            self.store.append_event(
                db,
                mission_id=current["mission_id"],
                stream_key="execution",
                event_type=f"execution.{status}",
                subject_type="execution",
                subject_id=execution_id,
                payload=observed
                | {
                    "stdout_artifact_id": stdout_id,
                    "stderr_artifact_id": stderr_id,
                    "failure_fingerprint": failure_fingerprint,
                },
            )
        return observed | {
            "status": "succeeded" if success else "failed",
            "stdout_artifact_id": stdout_id,
            "stderr_artifact_id": stderr_id,
        }

    def complete_external_execution(
        self,
        execution_id: str,
        *,
        generation: int,
        result: Mapping[str, Any],
        succeeded: bool,
    ) -> dict[str, Any]:
        with self.store.transaction() as db:
            execution = db.execute(
                "SELECT * FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
            if execution is None:
                raise StoreError("execution not found")
            if execution["status"] == "abandoned":
                raise StaleLease("abandoned execution cannot submit a late result")
            if execution["status"] in _TERMINAL_EXECUTION_STATES:
                raise InvalidTransition("execution is already terminal")
            self._assert_generation(db, execution, generation)
            status = "succeeded" if succeeded else "failed"
            db.execute(
                """UPDATE executions SET status=?,result_json=?,error_json=?,finished_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (
                    status,
                    canonical_json(dict(result) if succeeded else {}),
                    canonical_json({} if succeeded else dict(result)),
                    utc_now(),
                    execution_id,
                ),
            )
            db.execute(
                """UPDATE leases SET status='released',released_at=?
                   WHERE owner_execution_id=? AND status='active' AND generation=?""",
                (utc_now(), execution_id, generation),
            )
            if execution["work_item_id"]:
                db.execute(
                    "UPDATE work_items SET execution_status=?,updated_at=? WHERE id=?",
                    ("submitted" if succeeded else "failed", utc_now(), execution["work_item_id"]),
                )
        return self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))

    def recover_expired_leases(self, *, mission_id: str | None = None) -> list[str]:
        now = dt.datetime.now(dt.UTC)
        query = """SELECT DISTINCT e.* FROM leases l
                   JOIN executions e ON e.id=l.owner_execution_id
                   WHERE l.status='active' AND julianday(l.expires_at)<=julianday(?)"""
        params: list[Any] = [now.isoformat(timespec="microseconds")]
        if mission_id:
            query += " AND e.mission_id=?"
            params.append(mission_id)
        recovered: list[str] = []
        with self.store.transaction() as db:
            executions = db.execute(query, tuple(params)).fetchall()
            for execution in executions:
                db.execute(
                    "UPDATE leases SET status='expired',released_at=? WHERE owner_execution_id=? AND status='active'",
                    (utc_now(), execution["id"]),
                )
                db.execute(
                    """UPDATE executions SET status='abandoned',finished_at=?,state_version=state_version+1
                       WHERE id=? AND status NOT IN ('succeeded','failed','cancelled','invalidated')""",
                    (utc_now(), execution["id"]),
                )
                if execution["assignment_id"]:
                    db.execute(
                        """UPDATE work_assignments SET status='expired',released_at=?,
                           state_version=state_version+1 WHERE id=?""",
                        (utc_now(), execution["assignment_id"]),
                    )
                if execution["agent_session_id"]:
                    db.execute(
                        """UPDATE agent_sessions SET observed_status='lost',stopped_at=?,
                           state_version=state_version+1 WHERE id=?""",
                        (utc_now(), execution["agent_session_id"]),
                    )
                if execution["work_item_id"]:
                    db.execute(
                        """UPDATE work_items SET execution_status='abandoned',updated_at=?
                           WHERE id=?""",
                        (utc_now(), execution["work_item_id"]),
                    )
                self.store.append_event(
                    db,
                    mission_id=execution["mission_id"],
                    stream_key="recovery",
                    event_type="execution.abandoned_after_lease_expiry",
                    subject_type="execution",
                    subject_id=execution["id"],
                    payload={
                        "work_item_id": execution["work_item_id"],
                        "assignment_id": execution["assignment_id"],
                    },
                )
                recovered.append(execution["id"])
        return recovered
