from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import InvalidTransition
from .integrations.librsi import LibRSIIntegration
from .util import digest_json, json_load, new_id, utc_now


class AdaptiveExecutionService:
    """Outcome-driven strategy adaptation and no-null-next-action control."""

    def __init__(
        self,
        store: Any,
        *,
        work_items: Any,
        continuation: Any,
        supervision: Any,
        semantic_integration: LibRSIIntegration | None = None,
    ) -> None:
        self.store = store
        self.work_items = work_items
        self.continuation = continuation
        self.supervision = supervision
        self.semantic = semantic_integration or LibRSIIntegration(store, work_items=work_items)

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
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if execution["status"] not in {"succeeded", "failed", "abandoned", "cancelled"}:
            raise InvalidTransition("execution outcome is not observable yet")
        unexpected = execution["status"] == "succeeded" and self._unexpected_success(execution)
        prior = self.store.one(
            "SELECT * FROM strategy_outcomes WHERE execution_id=?",
            (execution_id,),
            required=False,
        )
        if prior is not None:
            abandoned_with_error = execution["status"] == "abandoned" and bool(
                json_load(execution["error_json"], {})
            )
            semantic = (
                self.semantic.reflect_execution(execution_id)
                if execution["status"] in {"failed", "cancelled"}
                or abandoned_with_error
                or unexpected
                else None
            )
            return {
                "strategy_outcome_id": prior["id"],
                "semantic_reflection": semantic,
                "duplicate": True,
            }
        work = None
        if execution.get("work_item_id"):
            work = self.store.one(
                "SELECT * FROM work_items WHERE id=?", (execution["work_item_id"],)
            )
        problem_key = self._problem_key(execution)
        strategy_key = self._strategy_key(execution, work)
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
            semantic = self.semantic.reflect_execution(execution_id)
            return {
                "strategy_outcome_id": outcome_id,
                "incident_id": incident_id,
                "semantic_reflection": semantic,
                "experiment_work_item_id": semantic.experiment_work_item_id,
                "duplicate": False,
            }
        if unexpected:
            semantic = self.semantic.reflect_execution(execution_id)
            return {
                "strategy_outcome_id": outcome_id,
                "semantic_reflection": semantic,
                "experiment_work_item_id": semantic.experiment_work_item_id,
                "duplicate": False,
            }
        return {"strategy_outcome_id": outcome_id, "duplicate": False}

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
            work_id = self.work_items.create_work_item(
                mission_id=mission_id,
                work_type="diagnosis",
                title=f"Request libRSI improvement result: {obligation['description']}",
                description=(
                    "Collect the exact obligation/currentness/evidence projection and run the "
                    "canonical libRSI improvement workflow before proposing operational work."
                ),
                obligation_id=str(obligation["id"]),
                priority=100,
                proposed_by="adaptive_projection",
                expected_effect={
                    "semantic_owner": "libRSI",
                    "required_result_type": "improvement_result",
                    "obligation_id": obligation["id"],
                },
                acceptance_spec={
                    "candidate": [
                        {"type": "canonical_improvement_result", "required": True},
                        {"type": "exact_currentness", "required": True},
                    ]
                },
                writable_scope=[],
                lane_key=f"librsi-improvement-request:{obligation['id']}",
                required_role="reflection_owner",
                strategy_key=f"librsi-improvement-request:{obligation['id']}",
            )
            selected = self.work_items.select_work(
                work_id,
                expected_version=1,
                selected_by="adaptive_projection",
                basis={
                    "semantic_owner": "libRSI",
                    "requested_result": "improvement_result",
                    "obligation_id": obligation["id"],
                },
            )
            created.append(str(selected["id"]))
        return created
