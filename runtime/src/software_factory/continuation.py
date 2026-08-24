from __future__ import annotations

from typing import Any

from .errors import EvidenceInvalid, InvalidTransition, RoleConflict
from .scheduling import (
    SchedulingPolicy,
    active_execution_count,
    budget_exhausted_work_item_ids,
)
from .util import canonical_json, utc_now


class ContinuationService:
    def __init__(self, store: Any, work_items: Any):
        self.store = store
        self.work_items = work_items

    def satisfy_obligation(
        self,
        obligation_id: str,
        *,
        expected_version: int,
        resolution: dict[str, Any],
        evidence_ids: list[str],
        actor_session_id: str | None = None,
    ) -> dict[str, Any]:
        with self.store.transaction() as db:
            row = self.store.check_version(
                db,
                table="obligations",
                row_id=obligation_id,
                expected_version=expected_version,
            )
            if row["status"] in {"satisfied", "superseded", "waived_by_authority"}:
                raise InvalidTransition("obligation is already terminal")
            self.store.require_evidence(
                db,
                evidence_ids,
                mission_id=row["mission_id"],
                subject_type="obligation",
                subject_id=obligation_id,
            )
            new_version = expected_version + 1
            db.execute(
                """UPDATE obligations SET status='satisfied',resolution_json=?,
                   state_version=?,updated_at=? WHERE id=?""",
                (canonical_json(resolution), new_version, utc_now(), obligation_id),
            )
            self.store.append_event(
                db,
                mission_id=row["mission_id"],
                stream_key="work",
                event_type="obligation.satisfied",
                subject_type="obligation",
                subject_id=obligation_id,
                source_type="session" if actor_session_id else "runtime",
                source_id=actor_session_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={"resolution": resolution, "evidence_ids": evidence_ids},
            )
        return self.store.one("SELECT * FROM obligations WHERE id=?", (obligation_id,))

    def next_action(self, mission_id: str) -> dict[str, Any]:
        mission = self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
        if mission["status"] == "completed":
            return {"posture": "complete", "action": "none", "reason": "mission_completed"}
        if mission["status"] == "cancelled_by_authority":
            return {
                "posture": "cancelled",
                "action": "none",
                "reason": "mission_cancelled_by_authority",
            }

        expired = self.store.all(
            """SELECT l.*,e.work_item_id FROM leases l
               JOIN executions e ON e.id=l.owner_execution_id
               WHERE e.mission_id=? AND l.status='active'
                 AND julianday(l.expires_at) <= julianday('now')""",
            (mission_id,),
        )
        if expired:
            return {
                "posture": "recovering",
                "action": "recover_expired_work",
                "lease_ids": [row["id"] for row in expired],
            }

        active = self.store.all(
            """SELECT id,status,work_item_id FROM executions
               WHERE mission_id=? AND status IN (
                 'queued','dispatching','leased','running','verifying'
               ) ORDER BY created_at""",
            (mission_id,),
        )
        policy = SchedulingPolicy.from_resource_limits(mission["resource_limits_json"])
        exhausted_ids = budget_exhausted_work_item_ids(self.store, mission_id, policy)
        dispatchable = self.work_items.ready_work(mission_id)
        active_count = active_execution_count(self.store, mission_id)
        capacity = max(0, policy.max_parallel - active_count)
        if dispatchable and capacity:
            frontier = dispatchable[: min(capacity, policy.max_dispatch_per_tick)]
            return {
                "posture": "executing",
                "action": "dispatch_ready_work",
                "work_item_ids": [row["id"] for row in frontier],
                "capacity_remaining": capacity,
                "scheduling_policy": policy.as_dict(),
                "budget_exhausted_work_item_ids": exhausted_ids,
            }
        if active:
            return {
                "posture": "executing",
                "action": "wait_for_active_work",
                "execution_ids": [row["id"] for row in active],
                "capacity_remaining": capacity,
                "scheduling_policy": policy.as_dict(),
                "budget_exhausted_work_item_ids": exhausted_ids,
            }

        required_gaps = self.store.all(
            """SELECT * FROM capabilities
               WHERE mission_id=? AND required=1
                 AND status<>'end_to_end_verified'""",
            (mission_id,),
        )
        open_obligations = self.store.all(
            """SELECT * FROM obligations
               WHERE mission_id=? AND status NOT IN (
                 'satisfied','superseded','waived_by_authority'
               ) ORDER BY priority DESC,created_at""",
            (mission_id,),
        )
        reserved = [row for row in open_obligations if row["status"] == "blocked_reserved"]
        nonreserved = [row for row in open_obligations if row["status"] != "blocked_reserved"]

        if required_gaps or nonreserved:
            if nonreserved:
                return {
                    "posture": "problem_solving",
                    "action": "diagnose_reflect_or_replan",
                    "obligation_ids": [row["id"] for row in nonreserved],
                    "capability_ids": [row["id"] for row in required_gaps],
                    "budget_exhausted_work_item_ids": exhausted_ids,
                }
            return {
                "posture": "waiting_reserved_input",
                "action": "preserve_reserved_boundary",
                "obligation_ids": [row["id"] for row in reserved],
            }
        if exhausted_ids:
            return {
                "posture": "problem_solving",
                "action": "diagnose_reflect_or_replan",
                "obligation_ids": [],
                "capability_ids": [],
                "budget_exhausted_work_item_ids": exhausted_ids,
            }

        terminal = self.store.one(
            """SELECT id,status,agent_session_id,result_json FROM executions
               WHERE mission_id=? AND execution_type='terminal_verification'
               ORDER BY created_at DESC LIMIT 1""",
            (mission_id,),
            required=False,
        )
        if terminal is None or terminal["status"] != "succeeded":
            return {
                "posture": "terminal_verification",
                "action": "run_terminal_verification",
            }
        return {
            "posture": "terminal_verification",
            "action": "complete_mission",
            "terminal_execution_id": terminal["id"],
        }

    def complete_mission(
        self,
        mission_id: str,
        *,
        expected_version: int,
        terminal_evidence_id: str,
        verifier_session_id: str,
    ) -> dict[str, Any]:
        with self.store.transaction() as db:
            self.store.check_version(
                db, table="missions", row_id=mission_id, expected_version=expected_version
            )
            gaps = db.execute(
                """SELECT COUNT(*) AS n FROM capabilities
                   WHERE mission_id=? AND required=1
                     AND status<>'end_to_end_verified'""",
                (mission_id,),
            ).fetchone()["n"]
            open_obligations = db.execute(
                """SELECT COUNT(*) AS n FROM obligations
                   WHERE mission_id=? AND status NOT IN (
                     'satisfied','superseded','waived_by_authority'
                   )""",
                (mission_id,),
            ).fetchone()["n"]
            terminal = db.execute(
                """SELECT * FROM executions WHERE mission_id=?
                   AND execution_type='terminal_verification'
                   AND status='succeeded'
                   ORDER BY finished_at DESC LIMIT 1""",
                (mission_id,),
            ).fetchone()
            verifier = db.execute(
                "SELECT * FROM agent_sessions WHERE id=?", (verifier_session_id,)
            ).fetchone()
            if verifier is None or verifier["role"] not in {
                "terminal_reviewer",
                "evaluator",
                "independent_reviewer",
            }:
                raise RoleConflict("terminal completion requires an independent verifier")
            if terminal is None or terminal["agent_session_id"] != verifier_session_id:
                raise EvidenceInvalid(
                    "terminal verification was not produced by the declared verifier"
                )
            self.store.require_evidence(
                db,
                [terminal_evidence_id],
                mission_id=mission_id,
                subject_type="mission",
                subject_id=mission_id,
                evidence_types={"terminal_probe", "installed_probe"},
            )
            if gaps or open_obligations:
                raise InvalidTransition(
                    "mission cannot complete with capability gaps or open obligations"
                )
            new_version = expected_version + 1
            now = utc_now()
            db.execute(
                """UPDATE missions SET status='completed',terminal_evidence_id=?,
                   state_version=?,updated_at=?,completed_at=? WHERE id=?""",
                (terminal_evidence_id, new_version, now, now, mission_id),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="mission",
                event_type="mission.completed",
                subject_type="mission",
                subject_id=mission_id,
                source_type="terminal_reviewer",
                source_id=verifier_session_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={
                    "terminal_evidence_id": terminal_evidence_id,
                    "terminal_execution_id": terminal["id"],
                },
            )
        return self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
