from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from .errors import InvalidTransition, RoleConflict
from .util import canonical_json, digest_json, json_load, new_id, parse_time, utc_now

_TARGET_TABLES = {
    "mission": ("missions", "id"),
    "capability": ("capabilities", "id"),
    "program": ("programs", "id"),
    "work_item": ("work_items", "id"),
    "execution": ("executions", "id"),
    "agent_session": ("agent_sessions", "id"),
    "selection": ("selections", "id"),
    "release": ("releases", "id"),
    "cleanup_run": ("cleanup_runs", "id"),
    "recovery_case": ("recovery_cases", "id"),
}

_SUPERVISOR_ROLES = {
    "mechanical_watcher",
    "semantic_reviewer",
    "escalation_reviewer",
    "supervisor",
    "effectiveness_reviewer",
    "terminal_reviewer",
    "independent_reviewer",
    "evaluator",
}

_EFFECTIVENESS = {
    "effective",
    "partially_effective",
    "ineffective",
    "counterproductive",
    "inconclusive",
    "not_yet_observable",
}


class SupervisionService:
    """Independent monitoring, incident containment, and correction review."""

    def __init__(
        self,
        store: Any,
        *,
        work_items: Any,
        continuation: Any,
    ) -> None:
        self.store = store
        self.work_items = work_items
        self.continuation = continuation
        self.adaptive: Any | None = None

    def bind_adaptive(self, adaptive: Any) -> None:
        self.adaptive = adaptive

    def _adaptive(self) -> Any:
        if self.adaptive is None:
            raise InvalidTransition("adaptive execution service is not bound")
        return self.adaptive

    def _target(self, target_type: str, target_id: str) -> dict[str, Any]:
        try:
            table, key = _TARGET_TABLES[target_type]
        except KeyError as exc:
            raise ValueError(f"unsupported supervision target: {target_type}") from exc
        row = self.store.one(f"SELECT * FROM {table} WHERE {key}=?", (target_id,))
        assert row is not None
        return row

    def _target_mission(self, target_type: str, row: Mapping[str, Any]) -> str | None:
        if target_type == "mission":
            return str(row["id"])
        if row.get("mission_id"):
            return str(row["mission_id"])
        if target_type == "program":
            return str(row["mission_id"])
        if target_type == "selection":
            return str(row["mission_id"])
        if target_type == "release":
            return None
        if target_type == "cleanup_run":
            repository = self.store.one(
                "SELECT project_id FROM repositories WHERE id=?", (row["repository_id"],)
            )
            mission = self.store.one(
                "SELECT id FROM missions WHERE project_id=? ORDER BY created_at DESC LIMIT 1",
                (repository["project_id"],),
                required=False,
            )
            return None if mission is None else str(mission["id"])
        return None

    def target_fingerprint(self, target_type: str, target_id: str) -> str:
        row = self._target(target_type, target_id)
        mission_id = self._target_mission(target_type, row)
        snapshot: dict[str, Any] = {
            "target_type": target_type,
            "target": dict(row),
        }
        if mission_id:
            snapshot["capabilities"] = self.store.all(
                """SELECT id,status,current_evidence_id,state_version FROM capabilities
                   WHERE mission_id=? ORDER BY id""",
                (mission_id,),
            )
            snapshot["obligations"] = self.store.all(
                """SELECT id,status,priority,state_version FROM obligations
                   WHERE mission_id=? ORDER BY id""",
                (mission_id,),
            )
            snapshot["active_executions"] = self.store.all(
                """SELECT id,work_item_id,status,lease_generation,state_version,
                          failure_fingerprint,source_revision_after
                   FROM executions WHERE mission_id=?
                     AND status IN ('dispatching','leased','running','verifying','failed','abandoned')
                   ORDER BY id""",
                (mission_id,),
            )
        return digest_json(snapshot)

    def create_assignment(
        self,
        *,
        mission_id: str | None,
        role: str,
        target_type: str,
        target_id: str,
        trigger_mode: str = "material_change",
        supervisor_session_id: str | None = None,
        trigger_spec: Mapping[str, Any] | None = None,
        policy: Mapping[str, Any] | None = None,
        next_due_at: str | None = None,
    ) -> str:
        if role not in _SUPERVISOR_ROLES:
            raise ValueError(f"unsupported supervision role: {role}")
        target = self._target(target_type, target_id)
        target_mission = self._target_mission(target_type, target)
        if mission_id is not None and target_mission not in {None, mission_id}:
            raise InvalidTransition("supervision target belongs to a different mission")
        if mission_id is None:
            mission_id = target_mission
        if supervisor_session_id:
            session = self.store.one(
                "SELECT mission_id,role FROM agent_sessions WHERE id=?",
                (supervisor_session_id,),
            )
            if session["role"] not in _SUPERVISOR_ROLES:
                raise RoleConflict("supervision assignment requires a supervisor role")
            if mission_id is not None and session["mission_id"] != mission_id:
                raise RoleConflict("supervisor belongs to a different mission")
        assignment_id = new_id("sup")
        now = utc_now()
        fingerprint = self.target_fingerprint(target_type, target_id)
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO supervision_assignments(
                    id,mission_id,role,supervisor_session_id,target_type,target_id,
                    trigger_mode,trigger_spec_json,policy_json,status,last_checked_at,
                    next_due_at,replacement_history_json,created_at,updated_at,
                    material_fingerprint,last_result_json,state_version
                ) VALUES(?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?,?,?,1)""",
                (
                    assignment_id,
                    mission_id,
                    role,
                    supervisor_session_id,
                    target_type,
                    target_id,
                    trigger_mode,
                    canonical_json(trigger_spec or {}),
                    canonical_json(policy or {}),
                    None,
                    next_due_at,
                    "[]",
                    now,
                    now,
                    fingerprint,
                    "{}",
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="supervision",
                event_type="supervision.assignment_created",
                subject_type="supervision_assignment",
                subject_id=assignment_id,
                source_type="session" if supervisor_session_id else "runtime",
                source_id=supervisor_session_id,
                new_version=1,
                payload={
                    "role": role,
                    "target_type": target_type,
                    "target_id": target_id,
                    "trigger_mode": trigger_mode,
                    "material_fingerprint": fingerprint,
                },
            )
        return assignment_id

    @staticmethod
    def _next_due(trigger_spec: Mapping[str, Any]) -> str | None:
        seconds = trigger_spec.get("cadence_seconds")
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            return None
        return (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=float(seconds))).isoformat(
            timespec="microseconds"
        )

    def _findings(self, assignment: Mapping[str, Any]) -> list[dict[str, Any]]:
        target_type = str(assignment["target_type"])
        target = self._target(target_type, str(assignment["target_id"]))
        findings: list[dict[str, Any]] = []
        if target_type == "execution":
            if target["status"] in {"failed", "abandoned", "cancelled"}:
                findings.append(
                    {
                        "kind": "execution_failure",
                        "severity": "high" if target["status"] == "failed" else "medium",
                        "execution_id": target["id"],
                        "failure_fingerprint": target.get("failure_fingerprint"),
                    }
                )
            if target["status"] == "running" and target.get("agent_session_id"):
                session = self.store.one(
                    "SELECT last_heartbeat_at,observed_status FROM agent_sessions WHERE id=?",
                    (target["agent_session_id"],),
                )
                heartbeat = parse_time(session["last_heartbeat_at"])
                stale_after = json_load(assignment["policy_json"], {}).get(
                    "heartbeat_stale_seconds", 900
                )
                stale_at = (
                    None if heartbeat is None else heartbeat + dt.timedelta(seconds=stale_after)
                )
                if stale_at is None or stale_at <= dt.datetime.now(dt.UTC):
                    findings.append(
                        {
                            "kind": "agent_unresponsive",
                            "severity": "high",
                            "execution_id": target["id"],
                            "agent_session_id": target["agent_session_id"],
                        }
                    )
        elif target_type == "work_item":
            if target["execution_status"] in {"failed", "abandoned"}:
                findings.append(
                    {
                        "kind": "work_attempt_failed",
                        "severity": "high",
                        "work_item_id": target["id"],
                    }
                )
            if (
                target["acceptance_status"] in {"candidate_accepted", "integrated_accepted"}
                and target["qa_status"] != "passed"
            ):
                findings.append(
                    {
                        "kind": "acceptance_without_current_qa",
                        "severity": "critical",
                        "work_item_id": target["id"],
                    }
                )
        elif target_type == "mission":
            regressed = self.store.all(
                "SELECT id FROM capabilities WHERE mission_id=? AND status='regressed'",
                (target["id"],),
            )
            if regressed:
                findings.append(
                    {
                        "kind": "protected_or_required_capability_regressed",
                        "severity": "critical",
                        "capability_ids": [row["id"] for row in regressed],
                    }
                )
            posture = self.continuation.next_action(str(target["id"]))
            if posture["action"] == "diagnose_reflect_or_replan":
                findings.append(
                    {
                        "kind": "mission_has_no_selected_supported_path",
                        "severity": "high",
                        "obligation_ids": posture.get("obligation_ids", []),
                    }
                )
        return findings

    def run_check(
        self,
        assignment_id: str,
        *,
        force: bool = False,
        reviewer_session_id: str | None = None,
    ) -> dict[str, Any]:
        assignment = self.store.one(
            "SELECT * FROM supervision_assignments WHERE id=?", (assignment_id,)
        )
        if assignment["status"] != "active":
            raise InvalidTransition("supervision assignment is not active")
        if reviewer_session_id:
            reviewer = self.store.one(
                "SELECT mission_id,role FROM agent_sessions WHERE id=?", (reviewer_session_id,)
            )
            if reviewer["role"] not in _SUPERVISOR_ROLES:
                raise RoleConflict("supervision check requires a reviewer role")
            if assignment["mission_id"] and reviewer["mission_id"] != assignment["mission_id"]:
                raise RoleConflict("reviewer belongs to a different mission")
        fingerprint = self.target_fingerprint(
            str(assignment["target_type"]), str(assignment["target_id"])
        )
        changed = fingerprint != assignment.get("material_fingerprint")
        findings = self._findings(assignment) if force or changed else []
        status = "finding" if findings else ("clear" if changed or force else "no_change")
        check_id = new_id("supchk")
        now = utc_now()
        trigger_spec = json_load(assignment["trigger_spec_json"], {})
        next_due = self._next_due(trigger_spec)
        result = {
            "assignment_id": assignment_id,
            "target_fingerprint": fingerprint,
            "material_changed": changed,
            "status": status,
            "findings": findings,
        }
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO supervision_checks(
                    id,assignment_id,mission_id,target_fingerprint,material_changed,
                    status,findings_json,reviewer_session_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    check_id,
                    assignment_id,
                    assignment["mission_id"],
                    fingerprint,
                    int(changed),
                    status,
                    canonical_json(findings),
                    reviewer_session_id,
                    now,
                ),
            )
            db.execute(
                """UPDATE supervision_assignments SET material_fingerprint=?,
                   last_result_json=?,last_checked_at=?,next_due_at=?,updated_at=?,
                   check_count=check_count+1,state_version=state_version+1 WHERE id=?""",
                (fingerprint, canonical_json(result), now, next_due, now, assignment_id),
            )
            self.store.append_event(
                db,
                mission_id=assignment["mission_id"],
                stream_key="supervision",
                event_type=f"supervision.check_{status}",
                subject_type="supervision_assignment",
                subject_id=assignment_id,
                source_type="session" if reviewer_session_id else "runtime",
                source_id=reviewer_session_id,
                payload=result,
            )
        for finding in findings:
            self._route_finding(assignment, finding)
        return result | {"check_id": check_id}

    def run_due_checks(self, mission_id: str) -> list[dict[str, Any]]:
        rows = self.store.all(
            """SELECT id FROM supervision_assignments
               WHERE mission_id=? AND status='active'
                 AND (next_due_at IS NULL OR julianday(next_due_at)<=julianday('now'))
               ORDER BY created_at""",
            (mission_id,),
        )
        return [self.run_check(row["id"]) for row in rows]

    def check_due(self, mission_id: str) -> list[dict[str, Any]]:
        """Run eligible supervision assignments and converge unchanged targets cheaply."""

        return self.run_due_checks(mission_id)

    def _route_finding(self, assignment: Mapping[str, Any], finding: Mapping[str, Any]) -> None:
        target_type = str(assignment["target_type"])
        target_id = str(assignment["target_id"])
        if finding["kind"] in {"execution_failure", "work_attempt_failed"}:
            execution_id: str | None = None
            if target_type == "execution":
                execution_id = target_id
            elif target_type == "work_item":
                row = self.store.one(
                    """SELECT id FROM executions WHERE work_item_id=?
                       AND status IN ('failed','abandoned','cancelled')
                       ORDER BY created_at DESC LIMIT 1""",
                    (target_id,),
                    required=False,
                )
                execution_id = None if row is None else str(row["id"])
            if execution_id:
                self._adaptive().observe_execution(execution_id)
            return
        if finding["kind"] == "mission_has_no_selected_supported_path":
            self._adaptive().ensure_problem_solving(str(assignment["mission_id"]))
            return
        if finding["kind"] == "protected_or_required_capability_regressed":
            self.open_incident(
                mission_id=str(assignment["mission_id"]),
                target_type="mission",
                target_id=str(assignment["mission_id"]),
                severity="critical",
                layer="capability",
                mechanism="capability regression detected by supervision",
                trigger={"finding": dict(finding)},
                effect={"capability_ids": finding.get("capability_ids", [])},
                detection={"assignment_id": assignment["id"]},
                failure_fingerprint=digest_json(finding),
                strategy_key=None,
            )

    def open_incident(
        self,
        *,
        mission_id: str,
        target_type: str,
        target_id: str,
        severity: str,
        layer: str,
        mechanism: str,
        trigger: Mapping[str, Any],
        effect: Mapping[str, Any],
        detection: Mapping[str, Any],
        failure_fingerprint: str | None,
        strategy_key: str | None,
        parent_incident_id: str | None = None,
        source_execution_id: str | None = None,
    ) -> str:
        dedup_key = digest_json(
            {
                "mission_id": mission_id,
                "target_type": target_type,
                "target_id": target_id,
                "layer": layer,
                "failure_fingerprint": failure_fingerprint,
                "strategy_key": strategy_key,
            }
        )
        existing = self.store.one(
            """SELECT * FROM incidents WHERE dedup_key=?
               AND status NOT IN ('resolved','superseded')""",
            (dedup_key,),
            required=False,
        )
        now = utc_now()
        if existing is not None:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE incidents SET occurrence_count=occurrence_count+1,
                       trigger_json=?,effect_json=?,detection_json=?,updated_at=?,
                       state_version=state_version+1 WHERE id=?""",
                    (
                        canonical_json(trigger),
                        canonical_json(effect),
                        canonical_json(detection),
                        now,
                        existing["id"],
                    ),
                )
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="supervision",
                    event_type="incident.recurred",
                    subject_type="incident",
                    subject_id=existing["id"],
                    payload={
                        "failure_fingerprint": failure_fingerprint,
                        "strategy_key": strategy_key,
                    },
                )
            return str(existing["id"])

        incident_id = new_id("inc")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO incidents(
                    id,mission_id,target_type,target_id,severity,status,layer,mechanism,
                    trigger_json,effect_json,detection_json,containment_json,
                    correction_json,recurrence_invariant_json,human_scheduling_leak,
                    effectiveness,reusable_disposition,state_version,created_at,updated_at,
                    failure_fingerprint,strategy_key,occurrence_count,parent_incident_id,
                    dedup_key,source_execution_id
                ) VALUES(
                    :id,:mission_id,:target_type,:target_id,:severity,'open',:layer,:mechanism,
                    :trigger_json,:effect_json,:detection_json,'{}','{}','{}',0,NULL,NULL,1,
                    :created_at,:updated_at,:failure_fingerprint,:strategy_key,1,
                    :parent_incident_id,:dedup_key,:source_execution_id
                )""",
                {
                    "id": incident_id,
                    "mission_id": mission_id,
                    "target_type": target_type,
                    "target_id": target_id,
                    "severity": severity,
                    "layer": layer,
                    "mechanism": mechanism,
                    "trigger_json": canonical_json(trigger),
                    "effect_json": canonical_json(effect),
                    "detection_json": canonical_json(detection),
                    "created_at": now,
                    "updated_at": now,
                    "failure_fingerprint": failure_fingerprint,
                    "strategy_key": strategy_key,
                    "parent_incident_id": parent_incident_id,
                    "dedup_key": dedup_key,
                    "source_execution_id": source_execution_id,
                },
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="supervision",
                event_type="incident.opened",
                subject_type="incident",
                subject_id=incident_id,
                new_version=1,
                payload={
                    "target_type": target_type,
                    "target_id": target_id,
                    "severity": severity,
                    "layer": layer,
                    "mechanism": mechanism,
                    "failure_fingerprint": failure_fingerprint,
                    "strategy_key": strategy_key,
                },
            )
        return incident_id

    def contain_incident(
        self,
        incident_id: str,
        *,
        actor_session_id: str,
        containment: Mapping[str, Any],
    ) -> dict[str, Any]:
        incident = self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
        actor = self.store.one(
            "SELECT mission_id,role FROM agent_sessions WHERE id=?", (actor_session_id,)
        )
        if actor["role"] not in _SUPERVISOR_ROLES:
            raise RoleConflict("containment requires a supervisor role")
        if actor["mission_id"] != incident["mission_id"]:
            raise RoleConflict("containment actor belongs to a different mission")
        now = utc_now()
        with self.store.transaction() as db:
            if incident["target_type"] == "execution":
                execution = db.execute(
                    "SELECT * FROM executions WHERE id=?", (incident["target_id"],)
                ).fetchone()
                if execution is not None and execution["status"] in {
                    "queued",
                    "dispatching",
                    "leased",
                    "running",
                    "verifying",
                }:
                    db.execute(
                        """UPDATE executions SET status='cancelled',finished_at=?,error_json=?,
                           state_version=state_version+1 WHERE id=?""",
                        (
                            now,
                            canonical_json(
                                {"reason": "incident_containment", "incident_id": incident_id}
                            ),
                            incident["target_id"],
                        ),
                    )
                    db.execute(
                        """UPDATE leases SET status='revoked',released_at=?
                           WHERE owner_execution_id=? AND status='active'""",
                        (now, incident["target_id"]),
                    )
                    db.execute(
                        """UPDATE provider_callbacks SET status='revoked',used_at=?
                           WHERE execution_id=? AND status='pending'""",
                        (now, incident["target_id"]),
                    )
            db.execute(
                """UPDATE incidents SET status='contained',containment_json=?,updated_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (canonical_json(containment), now, incident_id),
            )
            self.store.append_event(
                db,
                mission_id=incident["mission_id"],
                stream_key="supervision",
                event_type="incident.contained",
                subject_type="incident",
                subject_id=incident_id,
                source_type="session",
                source_id=actor_session_id,
                payload=dict(containment),
            )
        return self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))

    def acknowledge_incident(
        self,
        incident_id: str,
        *,
        operator_decision_id: str,
    ) -> dict[str, Any]:
        """Record an operator acknowledgement without creating a second writer."""

        incident = self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
        if incident["status"] not in {"open", "contained"}:
            raise InvalidTransition("incident is not awaiting acknowledgement")
        prior_version = int(incident["state_version"])
        new_version = prior_version + 1
        containment = json_load(incident["containment_json"], {})
        containment["operator_acknowledged"] = True
        containment["operator_decision_id"] = operator_decision_id
        with self.store.transaction() as db:
            db.execute(
                """UPDATE incidents
                   SET status='contained',containment_json=?,updated_at=?,state_version=?
                   WHERE id=?""",
                (canonical_json(containment), utc_now(), new_version, incident_id),
            )
            self.store.append_event(
                db,
                mission_id=incident["mission_id"],
                stream_key="supervision",
                event_type="incident.operator_acknowledged",
                subject_type="incident",
                subject_id=incident_id,
                source_type="operator_decision",
                source_id=operator_decision_id,
                prior_version=prior_version,
                new_version=new_version,
                payload={"operator_decision_id": operator_decision_id},
            )
        return self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))

    def record_correction(
        self,
        incident_id: str,
        *,
        work_item_id: str,
        expected_effect: Mapping[str, Any],
        verification_due_at: str | None = None,
    ) -> dict[str, Any]:
        incident = self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
        work = self.store.one("SELECT mission_id FROM work_items WHERE id=?", (work_item_id,))
        if work["mission_id"] != incident["mission_id"]:
            raise InvalidTransition("correction work belongs to a different mission")
        now = utc_now()
        correction = {
            "work_item_id": work_item_id,
            "expected_effect": dict(expected_effect),
            "recorded_at": now,
        }
        with self.store.transaction() as db:
            db.execute(
                """UPDATE incidents SET status='correcting',correction_json=?,
                   correction_work_item_id=?,verification_due_at=?,updated_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (
                    canonical_json(correction),
                    work_item_id,
                    verification_due_at,
                    now,
                    incident_id,
                ),
            )
            self.store.append_event(
                db,
                mission_id=incident["mission_id"],
                stream_key="supervision",
                event_type="incident.correction_recorded",
                subject_type="incident",
                subject_id=incident_id,
                payload=correction,
            )
        return self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))

    def record_effectiveness(
        self,
        incident_id: str,
        *,
        outcome: str,
        reviewer_session_id: str,
        evidence_ids: list[str] | None = None,
        observations: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if outcome not in _EFFECTIVENESS:
            raise ValueError(f"unsupported effectiveness outcome: {outcome}")
        incident = self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
        reviewer = self.store.one(
            "SELECT mission_id,role FROM agent_sessions WHERE id=?", (reviewer_session_id,)
        )
        if reviewer["role"] not in {"effectiveness_reviewer", "evaluator", "independent_reviewer"}:
            raise RoleConflict("effectiveness review requires an independent reviewer")
        if reviewer["mission_id"] != incident["mission_id"]:
            raise RoleConflict("effectiveness reviewer belongs to a different mission")
        evidence_ids = evidence_ids or []
        now = utc_now()
        status = "resolved" if outcome in {"effective", "partially_effective"} else "open"
        payload = {
            "outcome": outcome,
            "evidence_ids": evidence_ids,
            "observations": dict(observations or {}),
        }
        with self.store.transaction() as db:
            if evidence_ids:
                self.store.require_evidence(
                    db,
                    evidence_ids,
                    mission_id=incident["mission_id"],
                )
            db.execute(
                """UPDATE incidents SET status=?,effectiveness=?,updated_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (status, outcome, now, incident_id),
            )
            self.store.append_event(
                db,
                mission_id=incident["mission_id"],
                stream_key="supervision",
                event_type="incident.effectiveness_reviewed",
                subject_type="incident",
                subject_id=incident_id,
                source_type="session",
                source_id=reviewer_session_id,
                payload=payload,
            )
        if outcome in {"ineffective", "counterproductive"}:
            self._adaptive().create_action(
                mission_id=str(incident["mission_id"]),
                incident_id=incident_id,
                source_execution_id=None,
                action_kind="architecture_review",
                causal_level="architecture",
                problem_key=str(incident["target_id"]),
                prior_strategy_key=incident.get("strategy_key"),
                rationale={
                    "reason": "applied correction did not produce the predicted effect",
                    "effectiveness": outcome,
                    "causal_hypothesis_reopened": True,
                },
                work_type="reflection",
                title="Reopen causal hypothesis after ineffective correction",
                description=(
                    "The predicted effect was absent or counterproductive. Reassess the causal "
                    "model and choose a materially different architecture or program route."
                ),
                required_role="escalation_reviewer",
                parent_work_id=None,
                obligation_id=None,
            )
        return self.store.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
