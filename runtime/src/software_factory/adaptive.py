from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import InvalidTransition
from .util import canonical_json, digest_json, json_load, new_id, utc_now


class AdaptiveExecutionService:
    """Outcome-driven strategy adaptation and no-null-next-action control."""

    def __init__(
        self,
        store: Any,
        *,
        work_items: Any,
        continuation: Any,
        supervision: Any,
    ) -> None:
        self.store = store
        self.work_items = work_items
        self.continuation = continuation
        self.supervision = supervision

    def observe_new_execution_outcomes(self, mission_id: str) -> list[dict[str, Any]]:
        """Project newly terminal executions into adaptive state exactly once."""

        rows = self.store.all(
            """SELECT e.id FROM executions e
               LEFT JOIN strategy_outcomes o ON o.execution_id=e.id
               WHERE e.mission_id=?
                 AND e.status IN ('succeeded','failed','abandoned','cancelled')
                 AND o.id IS NULL
               ORDER BY e.created_at,e.id""",
            (mission_id,),
        )
        return [self.observe_execution(str(row["id"])) for row in rows]

    @staticmethod
    def _problem_key(execution: Mapping[str, Any]) -> str:
        return str(
            execution.get("obligation_id")
            or execution.get("work_item_id")
            or execution.get("mission_id")
        )

    @staticmethod
    def _strategy_key(execution: Mapping[str, Any], work: Mapping[str, Any] | None) -> str:
        if execution.get("strategy_key"):
            return str(execution["strategy_key"])
        if work is not None:
            basis = json_load(work["selection_basis_json"], {})
            if basis.get("strategy_key"):
                return str(basis["strategy_key"])
            return f"{work['work_type']}:{work['title']}"
        return "unknown"

    @staticmethod
    def _unexpected_success(execution: Mapping[str, Any]) -> bool:
        result = json_load(execution["result_json"], {})
        observed = json_load(execution["observed_effect_json"], {})
        return bool(
            result.get("unexpected_success")
            or observed.get("unexpected_success")
            or observed.get("outperformed_expectation")
        )

    def observe_execution(self, execution_id: str) -> dict[str, Any]:
        prior = self.store.one(
            "SELECT * FROM strategy_outcomes WHERE execution_id=?",
            (execution_id,),
            required=False,
        )
        if prior is not None:
            return {"strategy_outcome_id": prior["id"], "duplicate": True}
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if execution["status"] not in {"succeeded", "failed", "abandoned", "cancelled"}:
            raise InvalidTransition("execution outcome is not observable yet")
        work = None
        if execution.get("work_item_id"):
            work = self.store.one(
                "SELECT * FROM work_items WHERE id=?", (execution["work_item_id"],)
            )
        problem_key = self._problem_key(execution)
        strategy_key = self._strategy_key(execution, work)
        unexpected = execution["status"] == "succeeded" and self._unexpected_success(execution)
        outcome = "unexpected_success" if unexpected else str(execution["status"])
        fingerprint = execution.get("failure_fingerprint")
        if outcome in {"failed", "abandoned", "cancelled"} and not fingerprint:
            fingerprint = digest_json(json_load(execution["error_json"], {}))
        outcome_id = new_id("out")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO strategy_outcomes(
                    id,mission_id,work_item_id,execution_id,obligation_id,problem_key,
                    strategy_key,outcome,failure_fingerprint,evidence_root,
                    capability_delta_json,resource_use_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    outcome_id,
                    execution["mission_id"],
                    execution.get("work_item_id"),
                    execution_id,
                    execution.get("obligation_id"),
                    problem_key,
                    strategy_key,
                    outcome,
                    fingerprint,
                    execution.get("command_root"),
                    execution["observed_effect_json"],
                    execution["usage_json"],
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=execution["mission_id"],
                stream_key="supervision",
                event_type=f"strategy.{outcome}",
                subject_type="execution",
                subject_id=execution_id,
                payload={
                    "problem_key": problem_key,
                    "strategy_key": strategy_key,
                    "failure_fingerprint": fingerprint,
                },
            )
        if (
            outcome == "abandoned"
            and not json_load(execution["error_json"], {})
            and execution.get("work_item_id")
        ):
            # A lease-expired/lost worker is a resumable ownership failure, not evidence
            # that the implementation strategy itself is bad. The original selected work
            # remains dispatchable and is fenced by the next lease generation.
            with self.store.transaction() as db:
                self.store.append_event(
                    db,
                    mission_id=execution["mission_id"],
                    stream_key="recovery",
                    event_type="strategy.attempt_abandoned_resumable",
                    subject_type="execution",
                    subject_id=execution_id,
                    payload={
                        "work_item_id": execution.get("work_item_id"),
                        "problem_key": problem_key,
                        "strategy_key": strategy_key,
                    },
                )
            return {
                "strategy_outcome_id": outcome_id,
                "resumable": True,
                "duplicate": False,
            }
        if outcome in {"failed", "abandoned", "cancelled"}:
            incident_id = self.supervision.open_incident(
                mission_id=str(execution["mission_id"]),
                target_type="execution",
                target_id=execution_id,
                severity="high" if outcome == "failed" else "medium",
                layer="implementation",
                mechanism="observed execution did not produce the required effect",
                trigger={
                    "execution_status": outcome,
                    "error": json_load(execution["error_json"], {}),
                },
                effect={"work_item_id": execution.get("work_item_id"), "obligation_open": True},
                detection={"source": "execution_outcome"},
                failure_fingerprint=None if fingerprint is None else str(fingerprint),
                strategy_key=strategy_key,
                source_execution_id=execution_id,
            )
            action = self._route_failed_strategy(
                execution=execution,
                work=work,
                incident_id=incident_id,
                problem_key=problem_key,
                strategy_key=strategy_key,
                failure_fingerprint=None if fingerprint is None else str(fingerprint),
            )
            return {
                "strategy_outcome_id": outcome_id,
                "incident_id": incident_id,
                "adaptive_action": action,
                "duplicate": False,
            }
        if unexpected:
            action = self.create_action(
                mission_id=str(execution["mission_id"]),
                incident_id=None,
                source_execution_id=execution_id,
                action_kind="success_generalization",
                causal_level="strategy",
                problem_key=problem_key,
                prior_strategy_key=strategy_key,
                rationale={
                    "reason": "observed outcome materially outperformed expectation",
                    "generalization_posture": "bounded_hypothesis_and_counterexample_test",
                },
                work_type="reflection",
                title="Explain and test unexpected implementation success",
                description=(
                    "Preserve the current-run benefit, identify a causal hypothesis, search for "
                    "counterexamples, and test bounded applicability before any policy promotion."
                ),
                required_role="reflection_owner",
                parent_work_id=None if work is None else str(work["id"]),
                obligation_id=execution.get("obligation_id"),
            )
            return {
                "strategy_outcome_id": outcome_id,
                "adaptive_action": action,
                "duplicate": False,
            }
        return {"strategy_outcome_id": outcome_id, "duplicate": False}

    def _route_failed_strategy(
        self,
        *,
        execution: Mapping[str, Any],
        work: Mapping[str, Any] | None,
        incident_id: str,
        problem_key: str,
        strategy_key: str,
        failure_fingerprint: str | None,
    ) -> dict[str, Any]:
        similar = self.store.all(
            """SELECT id FROM strategy_outcomes
               WHERE mission_id=? AND problem_key=? AND strategy_key=?
                 AND outcome IN ('failed','abandoned','cancelled')
                 AND failure_fingerprint IS ? ORDER BY created_at""",
            (
                execution["mission_id"],
                problem_key,
                strategy_key,
                failure_fingerprint,
            ),
        )
        count = len(similar)
        if count <= 1:
            action_kind = "diagnose"
            causal_level = "local"
            work_type = "diagnosis"
            title = "Diagnose failed implementation effect"
            description = (
                "Compare expected and observed effects, preserve valid work, identify the causal "
                "failure level, and propose the cheapest discriminating next action."
            )
            required_role = "reflection_owner"
        elif count == 2:
            action_kind = "alternative_strategy"
            causal_level = "implementation"
            work_type = "implementation"
            title = "Implement a materially different strategy"
            description = (
                "The prior strategy and failure fingerprint repeated without capability progress. "
                "Do not retry it. Select and implement a materially different supported approach."
            )
            required_role = "implementer"
        else:
            action_kind = "architecture_review"
            causal_level = "architecture"
            work_type = "reflection"
            title = "Reframe architecture or active program after repeated failure"
            description = (
                "Multiple materially similar failures require an independent architecture/problem "
                "framing review and, if needed, a program revision rather than another local retry."
            )
            required_role = "escalation_reviewer"
        return self.create_action(
            mission_id=str(execution["mission_id"]),
            incident_id=incident_id,
            source_execution_id=str(execution["id"]),
            action_kind=action_kind,
            causal_level=causal_level,
            problem_key=problem_key,
            prior_strategy_key=strategy_key,
            rationale={
                "similar_failure_count": count,
                "failure_fingerprint": failure_fingerprint,
                "identical_retry_prohibited": count >= 2,
            },
            work_type=work_type,
            title=title,
            description=description,
            required_role=required_role,
            parent_work_id=None if work is None else str(work["id"]),
            obligation_id=execution.get("obligation_id"),
        )

    def create_action(
        self,
        *,
        mission_id: str,
        incident_id: str | None,
        source_execution_id: str | None,
        action_kind: str,
        causal_level: str,
        problem_key: str,
        prior_strategy_key: str | None,
        rationale: Mapping[str, Any],
        work_type: str,
        title: str,
        description: str,
        required_role: str,
        parent_work_id: str | None,
        obligation_id: str | None,
    ) -> dict[str, Any]:
        existing = self.store.one(
            """SELECT * FROM adaptive_actions WHERE mission_id=? AND problem_key=?
               AND action_kind=? AND status IN ('proposed','selected','running')""",
            (mission_id, problem_key, action_kind),
            required=False,
        )
        if existing is not None:
            return dict(existing) | {"duplicate": True}
        parent = (
            self.store.one("SELECT * FROM work_items WHERE id=?", (parent_work_id,))
            if parent_work_id
            else None
        )
        strategy_revision = 1 if parent is None else int(parent.get("strategy_revision") or 1) + 1
        strategy_key = f"{action_kind}:{problem_key}:r{strategy_revision}"
        work_id = self.work_items.create_work_item(
            mission_id=mission_id,
            work_type=work_type,
            title=title,
            description=description,
            obligation_id=obligation_id,
            program_id=None if parent is None else parent.get("program_id"),
            parent_id=parent_work_id,
            priority=100,
            proposed_by="supervision",
            expected_effect={
                "problem_key": problem_key,
                "causal_level": causal_level,
                "must_differ_from_strategy": prior_strategy_key
                if action_kind in {"alternative_strategy", "architecture_review"}
                else None,
                "strategy_key": strategy_key,
            },
            acceptance_spec={
                "candidate": [
                    {"type": "semantic_effect_review", "required": True},
                    {"type": "focused_validation", "required": True},
                ]
            },
            writable_scope=[] if parent is None else json_load(parent["writable_scope_json"], []),
            lane_key=f"adaptive:{problem_key}",
            repository_id=None if parent is None else parent.get("repository_id"),
            provider_key=None if parent is None else parent.get("provider_key"),
            required_role=required_role,
            strategy_key=strategy_key,
            strategy_revision=strategy_revision,
        )
        work = self.work_items.select_work(
            work_id,
            expected_version=1,
            selected_by="supervision",
            basis={
                "adaptive_action": action_kind,
                "problem_key": problem_key,
                "strategy_key": strategy_key,
                "prior_strategy_key": prior_strategy_key,
                "rationale": dict(rationale),
            },
        )
        action_id = new_id("ada")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO adaptive_actions(
                    id,mission_id,incident_id,source_execution_id,action_kind,causal_level,
                    problem_key,prior_strategy_key,selected_work_item_id,status,
                    rationale_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,'selected',?,?,?)""",
                (
                    action_id,
                    mission_id,
                    incident_id,
                    source_execution_id,
                    action_kind,
                    causal_level,
                    problem_key,
                    prior_strategy_key,
                    work_id,
                    canonical_json(rationale),
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="supervision",
                event_type="adaptive_action.selected",
                subject_type="adaptive_action",
                subject_id=action_id,
                payload={
                    "action_kind": action_kind,
                    "causal_level": causal_level,
                    "problem_key": problem_key,
                    "selected_work_item_id": work_id,
                    "rationale": dict(rationale),
                },
            )
        return {
            "id": action_id,
            "selected_work_item_id": work_id,
            "work": work,
            "action_kind": action_kind,
            "duplicate": False,
        }

    def ensure_strategy_allowed(
        self,
        *,
        mission_id: str,
        work_item_id: str,
        strategy_key: str | None = None,
    ) -> None:
        work = self.store.one(
            "SELECT mission_id,strategy_key FROM work_items WHERE id=?",
            (work_item_id,),
        )
        if work["mission_id"] != mission_id:
            raise InvalidTransition("strategy check crosses mission boundary")
        if strategy_key is not None and work.get("strategy_key") not in {None, strategy_key}:
            raise InvalidTransition("strategy key differs from selected work")
        self.assert_strategy_allowed(work_item_id)

    def assert_strategy_allowed(self, work_item_id: str, *, db: Any | None = None) -> None:
        work = self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,), db=db)
        basis = json_load(work["selection_basis_json"], {})
        problem_key = str(
            basis.get("problem_key")
            or work.get("obligation_id")
            or work.get("parent_id")
            or work["id"]
        )
        strategy_key = str(
            basis.get("strategy_key")
            or json_load(work["expected_effect_json"], {}).get("strategy_key")
            or f"{work['work_type']}:{work['title']}"
        )
        failures = self.store.all(
            """SELECT failure_fingerprint,evidence_root FROM strategy_outcomes
               WHERE mission_id=? AND problem_key=? AND strategy_key=?
                 AND outcome IN ('failed','abandoned','cancelled')
               ORDER BY created_at DESC LIMIT 2""",
            (work["mission_id"], problem_key, strategy_key),
            db=db,
        )
        if len(failures) < 2:
            return
        new_evidence = basis.get("new_evidence_ids") or []
        if not new_evidence:
            raise InvalidTransition(
                "materially identical strategy retry is prohibited after repeated failure without new evidence"
            )

    def ensure_problem_solving(self, mission_id: str) -> list[str]:
        open_obligations = self.store.all(
            """SELECT * FROM obligations WHERE mission_id=?
               AND status IN ('open','ready','in_progress','waiting_for_evidence')
               ORDER BY priority DESC,created_at""",
            (mission_id,),
        )
        created: list[str] = []
        for obligation in open_obligations:
            active = self.store.one(
                """SELECT id FROM work_items WHERE obligation_id=?
                   AND planning_status='selected'
                   AND execution_status IN ('not_started','queued','running','submitted','abandoned')
                   ORDER BY created_at DESC LIMIT 1""",
                (obligation["id"],),
                required=False,
            )
            if active is not None:
                continue
            action = self.create_action(
                mission_id=mission_id,
                incident_id=None,
                source_execution_id=None,
                action_kind="reflect",
                causal_level="problem_framing",
                problem_key=str(obligation["id"]),
                prior_strategy_key=None,
                rationale={
                    "reason": "open obligation has no selected executable path",
                    "no_null_next_action": True,
                },
                work_type="diagnosis",
                title=f"Determine next effective action: {obligation['description']}",
                description=(
                    "Reconstruct the obligation, current evidence, attempted strategies, and safe "
                    "frontier; select an implementation, experiment, recovery, or program-revision path."
                ),
                required_role="reflection_owner",
                parent_work_id=None,
                obligation_id=str(obligation["id"]),
            )
            if not action.get("duplicate"):
                created.append(str(action["selected_work_item_id"]))
        return created
