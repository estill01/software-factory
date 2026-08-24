from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .errors import EvidenceInvalid, InvalidTransition, RoleConflict
from .util import canonical_json, digest_json, json_load, new_id, utc_now

AcceptanceStage = Literal["candidate", "integrated", "installed", "terminal"]

_STAGE_ORDER: tuple[AcceptanceStage, ...] = (
    "candidate",
    "integrated",
    "installed",
    "terminal",
)
_INDEPENDENT_ROLES = {"independent_reviewer", "evaluator", "terminal_reviewer"}
_SEMANTIC_PROBE_TYPES = {
    "independent_review",
    "review",
    "semantic_review",
    "architecture_review",
}


def _outcome_mismatches(expected: Any, observed: Any, path: str = "$") -> list[dict[str, Any]]:
    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping):
            return [{"path": path, "expected": expected, "observed": observed}]
        findings: list[dict[str, Any]] = []
        for key in sorted(expected):
            child = f"{path}.{key}"
            if key not in observed:
                findings.append(
                    {"path": child, "expected": expected[key], "observed_present": False}
                )
            else:
                findings.extend(_outcome_mismatches(expected[key], observed[key], child))
        return findings
    if isinstance(expected, list):
        if not isinstance(observed, list) or expected != observed:
            return [{"path": path, "expected": expected, "observed": observed}]
        return []
    if expected != observed:
        return [{"path": path, "expected": expected, "observed": observed}]
    return []


class AcceptanceLifecycleService:
    """Coordinate governance decisions with staged, observed outcome acceptance.

    Governance remains the sole review/decision authority. This service records the
    operational stage projection, requires an independent actual-outcome observation,
    and routes disagreement back to the narrow operational owners.
    """

    def __init__(
        self,
        store: Any,
        *,
        governance: Any,
        work_items: Any,
        capabilities: Any,
        supervision: Any,
    ) -> None:
        self.store = store
        self.governance = governance
        self.work_items = work_items
        self.capabilities = capabilities
        self.supervision = supervision
        self._work_acceptance_authority = object()
        self.work_items._bind_acceptance_lifecycle_authority(  # noqa: SLF001
            self._work_acceptance_authority
        )

    @staticmethod
    def _stage_index(stage: str) -> int:
        try:
            return _STAGE_ORDER.index(stage)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ValueError(f"unsupported acceptance stage: {stage}") from exc

    def prepare_stage(
        self,
        *,
        mission_id: str,
        stage: AcceptanceStage,
        target_revision: str,
        currentness_root: str,
        implementer_session_id: str,
        required_probes: Sequence[Mapping[str, Any]],
        expected_outcome: Mapping[str, Any],
        remaining_scope: Sequence[str],
        protected_capabilities: Sequence[str] | None = None,
        minimum_independent_reviews: int = 1,
        work_item_id: str | None = None,
        prior_stage_id: str | None = None,
    ) -> dict[str, Any]:
        index = self._stage_index(stage)
        if not target_revision or not currentness_root:
            raise ValueError("acceptance stage requires revision and currentness roots")
        expected = dict(expected_outcome)
        if not expected or not ({"operator_visible", "protected_capabilities"} & expected.keys()):
            raise ValueError(
                "outcome contract requires operator-visible or protected-capability state"
            )
        probes = [dict(probe) for probe in required_probes]
        if any(str(probe.get("type")) in _SEMANTIC_PROBE_TYPES for probe in probes):
            raise ValueError("semantic review cannot be represented as a mechanical probe")
        remaining_values = {str(item) for item in remaining_scope if str(item)}
        active_program_ids: list[str] = []
        if stage == "terminal":
            active_program_ids = [
                str(row["id"])
                for row in self.store.all(
                    "SELECT id FROM programs WHERE mission_id=? AND status='active' ORDER BY id",
                    (mission_id,),
                )
            ]
            remaining_values.update(
                f"program:{program_id}:active" for program_id in active_program_ids
            )
        remaining = sorted(remaining_values)
        scope_key = f"work:{work_item_id}" if work_item_id else f"mission:{mission_id}"
        material_root = digest_json(
            {
                "mission_id": mission_id,
                "scope_key": scope_key,
                "stage": stage,
                "target_revision": target_revision,
                "currentness_root": currentness_root,
                "expected_outcome": expected,
                "remaining_scope": remaining,
                "required_probes": probes,
                "protected_capabilities": sorted(set(protected_capabilities or ())),
                "minimum_independent_reviews": minimum_independent_reviews,
            }
        )
        existing = self.store.one(
            """SELECT * FROM acceptance_stage_records_v2
               WHERE scope_key=? AND stage=? AND target_revision=? AND currentness_root=?""",
            (scope_key, stage, target_revision, currentness_root),
            required=False,
        )
        if existing is not None:
            if existing["outcome_contract_root"] != material_root:
                raise InvalidTransition("acceptance stage revision was rebound to new material")
            return existing

        stage_id = new_id("acceptance-stage")
        now = utc_now()
        with self.store.transaction() as db:
            mission = db.execute("SELECT id FROM missions WHERE id=?", (mission_id,)).fetchone()
            implementer = db.execute(
                "SELECT mission_id FROM agent_sessions WHERE id=?", (implementer_session_id,)
            ).fetchone()
            if mission is None or implementer is None or implementer["mission_id"] != mission_id:
                raise InvalidTransition("acceptance implementer must belong to the mission")
            if stage == "terminal":
                current_active_program_ids = [
                    str(row["id"])
                    for row in db.execute(
                        """SELECT id FROM programs
                           WHERE mission_id=? AND status='active' ORDER BY id""",
                        (mission_id,),
                    ).fetchall()
                ]
                if current_active_program_ids != active_program_ids:
                    raise InvalidTransition(
                        "canonical program range changed during terminal stage preparation"
                    )
            if work_item_id:
                work = db.execute(
                    "SELECT mission_id FROM work_items WHERE id=?", (work_item_id,)
                ).fetchone()
                if work is None or work["mission_id"] != mission_id:
                    raise InvalidTransition("acceptance work item belongs to another mission")
            if index == 0 and prior_stage_id is not None:
                raise InvalidTransition("candidate acceptance cannot have a prior stage")
            prior: Any | None = None
            if index > 0:
                if prior_stage_id is None:
                    raise InvalidTransition(
                        "later acceptance stage requires its accepted predecessor"
                    )
                prior = db.execute(
                    "SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (prior_stage_id,)
                ).fetchone()
                expected_prior = _STAGE_ORDER[index - 1]
                if (
                    prior is None
                    or prior["status"] != "accepted"
                    or prior["stage"] != expected_prior
                    or prior["mission_id"] != mission_id
                    or prior["scope_key"] != scope_key
                    or prior["target_revision"] != target_revision
                    or prior["currentness_root"] != currentness_root
                ):
                    raise InvalidTransition(
                        f"{stage} acceptance requires accepted {expected_prior} at exact revision"
                    )

            older = db.execute(
                """SELECT id,target_revision FROM acceptance_stage_records_v2
                   WHERE scope_key=? AND (
                     target_revision<>? OR currentness_root<>?
                   )
                     AND status IN ('prepared','accepted','reopened')""",
                (scope_key, target_revision, currentness_root),
            ).fetchall()
            for row in older:
                self.governance.invalidate_target_revision(
                    target_type="acceptance_stage",
                    target_id=row["id"],
                    prior_revision=row["target_revision"],
                )
                db.execute(
                    """UPDATE acceptance_stage_records_v2
                       SET status='stale',updated_at=? WHERE id=?""",
                    (now, row["id"]),
                )

            contract = self.governance.create_acceptance_contract(
                mission_id=mission_id,
                target_type="acceptance_stage",
                target_id=stage_id,
                target_revision=target_revision,
                required_probes=probes,
                protected_capabilities=protected_capabilities,
                minimum_independent_reviews=minimum_independent_reviews,
            )
            db.execute(
                """INSERT INTO acceptance_stage_records_v2(
                       id,mission_id,work_item_id,scope_key,stage,target_revision,
                       currentness_root,expected_outcome_json,outcome_contract_root,
                       remaining_scope_json,contract_id,prior_stage_id,
                       implementer_session_id,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'prepared',?,?)""",
                (
                    stage_id,
                    mission_id,
                    work_item_id,
                    scope_key,
                    stage,
                    target_revision,
                    currentness_root,
                    canonical_json(expected),
                    material_root,
                    canonical_json(remaining),
                    contract["id"],
                    prior_stage_id,
                    implementer_session_id,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="acceptance",
                event_type="acceptance.stage_prepared",
                subject_type="acceptance_stage",
                subject_id=stage_id,
                source_type="session",
                source_id=implementer_session_id,
                payload={
                    "stage": stage,
                    "target_revision": target_revision,
                    "currentness_root": currentness_root,
                    "contract_id": contract["id"],
                    "prior_stage_id": prior_stage_id,
                    "remaining_scope": remaining,
                },
            )
        return self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))

    def record_probe_result(
        self,
        stage_id: str,
        *,
        probe_key: str,
        exact_revision: str,
        disposition: Literal["passed", "failed", "inconclusive", "invalid"],
        observed_result: Mapping[str, Any],
        evidence_ids: Sequence[str],
        command: Sequence[str] | None = None,
        observer_session_id: str | None = None,
    ) -> dict[str, Any]:
        stage = self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))
        if stage["status"] not in {"prepared", "reopened"}:
            raise InvalidTransition("acceptance stage is not awaiting probes")
        with self.store.transaction() as db:
            self.store.require_evidence(
                db,
                list(evidence_ids),
                mission_id=stage["mission_id"],
                revision=exact_revision,
            )
            return self.governance.record_probe_result(
                stage["contract_id"],
                probe_key=probe_key,
                exact_revision=exact_revision,
                disposition=disposition,
                observed_result=observed_result,
                evidence_ids=evidence_ids,
                command=command,
                observer_session_id=observer_session_id,
            )

    def record_stage_independent_review(
        self,
        stage_id: str,
        *,
        grant_id: str,
        reviewer_session_id: str,
        exact_revision: str,
        currentness_root: str,
        review_contract: Mapping[str, Any],
        provider_session_id: str,
        transcript_artifact_id: str,
        evidence_ids: Sequence[str],
        disposition: Literal["accepted", "rejected", "revise", "inconclusive"],
        findings: Mapping[str, Any],
    ) -> dict[str, Any]:
        stage = self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))
        if currentness_root != stage["currentness_root"]:
            raise InvalidTransition("review currentness does not match the prepared stage")
        with self.store.transaction() as db:
            self.store.require_evidence(
                db,
                list(evidence_ids),
                mission_id=stage["mission_id"],
                revision=exact_revision,
            )
            return self.governance.record_independent_review(
                stage["contract_id"],
                grant_id=grant_id,
                reviewer_session_id=reviewer_session_id,
                implementer_session_id=stage["implementer_session_id"],
                exact_revision=exact_revision,
                currentness_root=currentness_root,
                review_contract=review_contract,
                provider_session_id=provider_session_id,
                transcript_artifact_id=transcript_artifact_id,
                evidence_ids=evidence_ids,
                disposition=disposition,
                findings=findings,
            )

    def decide_stage(self, stage_id: str, *, exact_revision: str) -> dict[str, Any]:
        stage = self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))
        existing = self.store.one(
            """SELECT * FROM acceptance_decisions_v2
               WHERE contract_id=? AND exact_revision=? AND decision='accepted'
               ORDER BY decided_at DESC LIMIT 1""",
            (stage["contract_id"], exact_revision),
            required=False,
        )
        decision = existing or self.governance.decide_acceptance(
            stage["contract_id"], exact_revision=exact_revision
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE acceptance_stage_records_v2
                   SET decision_id=?,updated_at=? WHERE id=?""",
                (decision["id"], utc_now(), stage_id),
            )
        return decision

    def issue_outcome_reviewer_grant(
        self,
        stage_id: str,
        *,
        reviewer_session_id: str,
        policy_root: str,
        expires_at: str,
        issued_by_session_id: str | None = None,
        max_uses: int = 1,
    ) -> dict[str, Any]:
        stage = self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))
        return self.governance.issue_role_grant(
            mission_id=stage["mission_id"],
            grantee_session_id=reviewer_session_id,
            role="outcome_reviewer",
            target_type="acceptance_outcome",
            target_id=stage_id,
            target_revision=stage["target_revision"],
            policy_root=policy_root,
            currentness_root=stage["currentness_root"],
            scope={
                "effects": ["observe_actual_outcome"],
                "stage": stage["stage"],
                "outcome_contract_root": stage["outcome_contract_root"],
            },
            issued_by_session_id=issued_by_session_id,
            expires_at=expires_at,
            max_uses=max_uses,
        )

    def _validate_narrow_owner(
        self,
        *,
        stage: Mapping[str, Any],
        owner_type: str,
        owner_id: str,
    ) -> tuple[str | None, str | None]:
        if owner_type == "work_item":
            work = self.store.one("SELECT mission_id FROM work_items WHERE id=?", (owner_id,))
            if work["mission_id"] != stage["mission_id"] or stage.get("work_item_id") != owner_id:
                raise InvalidTransition("outcome disagreement must reopen its narrow work owner")
            return None, owner_id
        if owner_type == "capability":
            capability = self.store.one(
                "SELECT mission_id FROM capabilities WHERE id=?", (owner_id,)
            )
            if capability["mission_id"] != stage["mission_id"]:
                raise InvalidTransition("outcome capability belongs to another mission")
            return owner_id, None
        if owner_type == "mission" and owner_id == stage["mission_id"]:
            return None, None
        raise ValueError("narrow owner must be this stage's work item, capability, or mission")

    def reconcile_outcome(
        self,
        stage_id: str,
        *,
        grant_id: str,
        reviewer_session_id: str,
        provider_session_id: str,
        exact_revision: str,
        currentness_root: str,
        observed_outcome: Mapping[str, Any],
        evidence_ids: Sequence[str],
        observation_complete: bool = True,
        narrow_owner_type: str | None = None,
        narrow_owner_id: str | None = None,
    ) -> dict[str, Any]:
        stage = self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))
        if (
            stage["target_revision"] != exact_revision
            or stage["currentness_root"] != currentness_root
        ):
            raise InvalidTransition("outcome observation is stale for the prepared stage")
        if not stage.get("decision_id"):
            raise InvalidTransition("actual outcome cannot precede the governance decision")
        decision = self.store.one(
            "SELECT decision,exact_revision FROM acceptance_decisions_v2 WHERE id=?",
            (stage["decision_id"],),
        )
        if decision != {"decision": "accepted", "exact_revision": exact_revision}:
            raise InvalidTransition("actual outcome requires a current accepted decision")
        reviewer = self.store.one(
            """SELECT mission_id,role,external_task_id,external_thread_id
               FROM agent_sessions WHERE id=?""",
            (reviewer_session_id,),
        )
        if (
            reviewer["mission_id"] != stage["mission_id"]
            or reviewer["role"] not in _INDEPENDENT_ROLES
        ):
            raise RoleConflict("outcome reconciliation requires an independent reviewer")
        if reviewer_session_id == stage["implementer_session_id"]:
            raise RoleConflict("implementer cannot reconcile its own actual outcome")
        recorded_provider_identity = str(
            reviewer.get("external_task_id") or reviewer.get("external_thread_id") or ""
        )
        if recorded_provider_identity != provider_session_id:
            raise InvalidTransition(
                "outcome reviewer provider identity does not match the granted session"
            )

        expected = json_load(stage["expected_outcome_json"], {})
        observed = dict(observed_outcome)
        mismatches = (
            _outcome_mismatches(expected, observed)
            if observation_complete
            else [{"path": "$", "reason": "observation_incomplete"}]
        )
        disposition = (
            "aligned"
            if not mismatches
            else ("disagreed" if observation_complete else "inconclusive")
        )
        evidence = sorted({str(item) for item in evidence_ids if str(item)})
        outcome_root = digest_json(
            {
                "stage_record_id": stage_id,
                "exact_revision": exact_revision,
                "currentness_root": currentness_root,
                "expected_outcome": expected,
                "observed_outcome": observed,
                "mismatches": mismatches,
                "evidence_ids": evidence,
                "disposition": disposition,
            }
        )
        existing = self.store.one(
            """SELECT * FROM outcome_reconciliations_v2
               WHERE stage_record_id=? AND outcome_root=?""",
            (stage_id, outcome_root),
            required=False,
        )
        if existing is not None:
            return existing
        if disposition == "disagreed" and (not narrow_owner_type or not narrow_owner_id):
            raise InvalidTransition("outcome disagreement requires one narrow operational owner")
        capability_id: str | None = None
        work_id: str | None = None
        if disposition == "disagreed":
            assert narrow_owner_type is not None and narrow_owner_id is not None
            capability_id, work_id = self._validate_narrow_owner(
                stage=stage,
                owner_type=narrow_owner_type,
                owner_id=narrow_owner_id,
            )

        reconciliation_id = new_id("outcome-reconciliation")
        now = utc_now()
        with self.store.transaction() as db:
            self.store.require_evidence(
                db,
                evidence,
                mission_id=stage["mission_id"],
                revision=exact_revision,
            )
            self.governance.consume_role_grant(
                grant_id,
                grantee_session_id=reviewer_session_id,
                role="outcome_reviewer",
                target_type="acceptance_outcome",
                target_id=stage_id,
                target_revision=exact_revision,
                currentness_root=currentness_root,
            )
            db.execute(
                """INSERT INTO outcome_reconciliations_v2(
                       id,stage_record_id,reviewer_session_id,exact_revision,
                       currentness_root,expected_outcome_json,observed_outcome_json,
                       mismatches_json,evidence_ids_json,disposition,outcome_root,
                       narrow_owner_type,narrow_owner_id,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    reconciliation_id,
                    stage_id,
                    reviewer_session_id,
                    exact_revision,
                    currentness_root,
                    canonical_json(expected),
                    canonical_json(observed),
                    canonical_json(mismatches),
                    canonical_json(evidence),
                    disposition,
                    outcome_root,
                    narrow_owner_type,
                    narrow_owner_id,
                    now,
                ),
            )
            obligation_id: str | None = None
            incident_id: str | None = None
            if disposition == "disagreed":
                obligation_id = self.capabilities.add_obligation(
                    mission_id=stage["mission_id"],
                    obligation_type="outcome_reconciliation",
                    description=(
                        f"Reconcile actual {stage['stage']} outcome disagreement for "
                        f"{narrow_owner_type}/{narrow_owner_id}"
                    ),
                    capability_id=capability_id,
                    priority=100,
                    status="open",
                )
                if work_id is not None:
                    self.work_items.reopen_acceptance(
                        work_id,
                        reason="actual outcome disagrees with the accepted process record",
                        evidence_ids=evidence,
                        authority=self._work_acceptance_authority,
                    )
                if capability_id is not None:
                    self.capabilities.reopen_capability(
                        capability_id,
                        evidence_id=evidence[0],
                        exact_revision=exact_revision,
                        reason="actual outcome disagrees with the accepted process record",
                        actor_id=reviewer_session_id,
                    )
                incident_id = self.supervision.open_incident(
                    mission_id=stage["mission_id"],
                    target_type=narrow_owner_type,
                    target_id=narrow_owner_id,
                    severity="critical" if stage["stage"] == "terminal" else "high",
                    layer="outcome",
                    mechanism="accepted process record disagrees with observed actual outcome",
                    trigger={
                        "stage_record_id": stage_id,
                        "decision_id": stage["decision_id"],
                    },
                    effect={"mismatches": mismatches, "obligation_id": obligation_id},
                    detection={
                        "reviewer_session_id": reviewer_session_id,
                        "evidence_ids": evidence,
                    },
                    failure_fingerprint=digest_json(
                        {"stage_record_id": stage_id, "mismatches": mismatches}
                    ),
                    strategy_key=None,
                )
                db.execute(
                    """UPDATE outcome_reconciliations_v2
                       SET obligation_id=?,incident_id=? WHERE id=?""",
                    (obligation_id, incident_id, reconciliation_id),
                )
                db.execute(
                    """UPDATE acceptance_stage_records_v2
                       SET status='reopened',updated_at=? WHERE id=?""",
                    (now, stage_id),
                )
            self.store.append_event(
                db,
                mission_id=stage["mission_id"],
                stream_key="acceptance",
                event_type=f"acceptance.outcome_{disposition}",
                subject_type="acceptance_stage",
                subject_id=stage_id,
                source_type="session",
                source_id=reviewer_session_id,
                payload={
                    "reconciliation_id": reconciliation_id,
                    "outcome_root": outcome_root,
                    "mismatches": mismatches,
                    "obligation_id": obligation_id,
                    "incident_id": incident_id,
                },
            )
        return self.store.one(
            "SELECT * FROM outcome_reconciliations_v2 WHERE id=?", (reconciliation_id,)
        )

    def accept_stage(
        self,
        stage_id: str,
        *,
        acceptor_session_id: str,
        exact_revision: str,
        currentness_root: str,
    ) -> dict[str, Any]:
        with self.store.transaction() as db:
            stage = self.store.one(
                "SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,), db=db
            )
            if stage["status"] not in {"prepared", "reopened"}:
                raise InvalidTransition("acceptance stage is not promotable")
            if (
                stage["target_revision"] != exact_revision
                or stage["currentness_root"] != currentness_root
            ):
                raise InvalidTransition("acceptance stage promotion is stale")
            acceptor = self.store.one(
                "SELECT mission_id,role FROM agent_sessions WHERE id=?",
                (acceptor_session_id,),
                db=db,
            )
            if (
                acceptor["mission_id"] != stage["mission_id"]
                or acceptor["role"] not in _INDEPENDENT_ROLES
            ):
                raise RoleConflict("stage promotion requires an independent acceptance role")
            if acceptor_session_id == stage["implementer_session_id"]:
                raise RoleConflict("implementer cannot promote its own acceptance stage")
            latest = self.store.one(
                """SELECT * FROM outcome_reconciliations_v2
                   WHERE stage_record_id=? ORDER BY created_at DESC,id DESC LIMIT 1""",
                (stage_id,),
                required=False,
                db=db,
            )
            if latest is None or latest["disposition"] != "aligned":
                raise EvidenceInvalid("accepted process evidence has no aligned actual outcome")
            unresolved = self.store.one(
                """SELECT r.id FROM outcome_reconciliations_v2 r
                   LEFT JOIN obligations o ON o.id=r.obligation_id
                   LEFT JOIN incidents i ON i.id=r.incident_id
                   WHERE r.stage_record_id=? AND r.disposition='disagreed'
                     AND (
                       o.status NOT IN ('satisfied','superseded','waived_by_authority')
                       OR i.status NOT IN ('resolved','superseded')
                     ) LIMIT 1""",
                (stage_id,),
                required=False,
                db=db,
            )
            if unresolved is not None:
                raise InvalidTransition("outcome disagreement remains unresolved")
            if stage["stage"] == "terminal":
                remaining = json_load(stage["remaining_scope_json"], [])
                counts = db.execute(
                    """SELECT
                         (SELECT COUNT(*) FROM capabilities
                          WHERE mission_id=? AND required=1
                            AND status<>'end_to_end_verified') AS gaps,
                         (SELECT COUNT(*) FROM obligations WHERE mission_id=?
                          AND status NOT IN
                            ('satisfied','superseded','waived_by_authority')) AS obligations,
                         (SELECT COUNT(*) FROM work_items
                          WHERE mission_id=? AND planning_status='selected'
                            AND execution_status<>'cancelled'
                            AND acceptance_status<>'installed_accepted') AS unfinished_work,
                         (SELECT COUNT(*) FROM programs
                          WHERE mission_id=? AND status='active') AS active_programs""",
                    (stage["mission_id"],) * 4,
                ).fetchone()
                if (
                    remaining
                    or counts["gaps"]
                    or counts["obligations"]
                    or counts["unfinished_work"]
                    or counts["active_programs"]
                ):
                    raise InvalidTransition(
                        "terminal acceptance cannot leave requested range, capability gaps, "
                        "obligations, unfinished selected work, or active programs"
                    )
            if stage.get("work_item_id") and stage["stage"] != "terminal":
                self.work_items.promote_acceptance(
                    stage["work_item_id"],
                    stage=stage["stage"],
                    exact_revision=exact_revision,
                    evidence_ids=json_load(latest["evidence_ids_json"], []),
                    authority=self._work_acceptance_authority,
                )
            db.execute(
                """UPDATE acceptance_stage_records_v2
                   SET status='accepted',updated_at=? WHERE id=?""",
                (utc_now(), stage_id),
            )
            self.store.append_event(
                db,
                mission_id=stage["mission_id"],
                stream_key="acceptance",
                event_type=f"acceptance.{stage['stage']}_accepted",
                subject_type="acceptance_stage",
                subject_id=stage_id,
                source_type="session",
                source_id=acceptor_session_id,
                payload={
                    "decision_id": stage["decision_id"],
                    "outcome_reconciliation_id": latest["id"],
                    "target_revision": exact_revision,
                },
            )
        return self.store.one("SELECT * FROM acceptance_stage_records_v2 WHERE id=?", (stage_id,))

    def current_terminal_stage(self, mission_id: str) -> dict[str, Any] | None:
        return self.store.one(
            """SELECT s.*,r.id AS outcome_reconciliation_id,
                      r.exact_revision AS outcome_revision,r.disposition AS outcome_disposition
               FROM acceptance_stage_records_v2 s
               JOIN outcome_reconciliations_v2 r ON r.stage_record_id=s.id
               WHERE s.mission_id=? AND s.stage='terminal' AND s.status='accepted'
                 AND r.disposition='aligned'
               ORDER BY s.updated_at DESC,r.created_at DESC LIMIT 1""",
            (mission_id,),
            required=False,
        )
