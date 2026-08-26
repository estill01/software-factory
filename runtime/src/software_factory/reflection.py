from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import InvalidTransition
from .integrations.librsi import LibRSIIntegration
from .util import canonical_json, digest_json, json_load, new_id, utc_now


class ReflectionService:
    """Structured live/checkpoint/terminal/cross-run reflection.

    Reflection is recorded as an execution. Narrative or model output may be attached as
    an artifact by an adapter, but canonical outputs are hypotheses and explicit next
    actions derived from exact observed state.
    """

    def __init__(
        self,
        store: Any,
        *,
        work_items: Any,
        semantic_integration: LibRSIIntegration | None = None,
    ) -> None:
        self.store = store
        self.work_items = work_items
        self.semantic_integration = semantic_integration or LibRSIIntegration(
            store, work_items=work_items
        )

    def _create_execution(
        self,
        *,
        mission_id: str,
        timescale: str,
        source: Mapping[str, Any],
        result: Mapping[str, Any],
        origin_execution_id: str | None = None,
    ) -> str:
        key = digest_json(
            {
                "mission_id": mission_id,
                "timescale": timescale,
                "source": dict(source),
            }
        )
        existing = self.store.one(
            "SELECT id FROM executions WHERE idempotency_key=?",
            (f"reflection:{key}",),
            required=False,
        )
        if existing is not None:
            return str(existing["id"])
        execution_id = new_id("exe")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO executions(
                    id,mission_id,execution_type,status,strategy_key,attempt_number,
                    idempotency_key,input_json,result_json,error_json,limits_json,
                    usage_json,observed_effect_json,created_at,started_at,finished_at,
                    state_version
                ) VALUES(?,?,?,'succeeded',?,1,?,?,?,'{}','{}','{}',?,?,?, ?,1)""",
                (
                    execution_id,
                    mission_id,
                    "reflection",
                    f"reflection:{timescale}",
                    f"reflection:{key}",
                    canonical_json(dict(source)),
                    canonical_json(dict(result)),
                    canonical_json(
                        {
                            "timescale": timescale,
                            "hypothesis_count": len(result.get("hypotheses", [])),
                            "origin_execution_id": origin_execution_id,
                        }
                    ),
                    now,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="reflection",
                event_type=f"reflection.{timescale}_completed",
                subject_type="execution",
                subject_id=execution_id,
                causation_id=origin_execution_id,
                payload=dict(result),
            )
        return execution_id

    def reflect_execution(self, execution_id: str, *, timescale: str = "live") -> dict[str, Any]:
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if execution["status"] not in {"succeeded", "failed", "abandoned", "cancelled"}:
            raise InvalidTransition("reflection requires a terminal observed execution")
        mission_id = str(execution["mission_id"])
        (
            self.store.one("SELECT * FROM work_items WHERE id=?", (execution["work_item_id"],))
            if execution.get("work_item_id")
            else None
        )
        strategy = str(execution.get("strategy_key") or "unknown")
        failure = execution["status"] != "succeeded"
        unexpected = bool(
            json_load(execution["observed_effect_json"], {}).get("unexpected_success")
            or json_load(execution["result_json"], {}).get("unexpected_success")
        )
        semantic = (
            self.semantic_integration.reflect_execution(execution_id)
            if failure or unexpected
            else None
        )
        recommended = (
            semantic.recommended_next_action if semantic is not None else "retain_current_strategy"
        )

        source = {
            "execution_id": execution_id,
            "status": execution["status"],
            "strategy_key": strategy,
            "work_item_id": execution.get("work_item_id"),
            "failure_fingerprint": execution.get("failure_fingerprint"),
            "observed_effect": json_load(execution["observed_effect_json"], {}),
            "usage": json_load(execution["usage_json"], {}),
        }
        result = {
            "timescale": timescale,
            "problem_reframing": (
                "strategy_effect" if semantic is not None else "no_material_reframe"
            ),
            "semantic_owner": "libRSI" if semantic is not None else None,
            "hypotheses": list(semantic.hypothesis_roots) if semantic is not None else [],
            "evidence_roots": list(semantic.evidence_roots) if semantic is not None else [],
            "experiment_root": semantic.experiment_root if semantic is not None else None,
            "cutover_receipt_root": (
                semantic.cutover_receipt_root if semantic is not None else None
            ),
            "recommended_next_action": recommended,
        }
        reflection_id = self._create_execution(
            mission_id=mission_id,
            timescale=timescale,
            source=source,
            result=result,
            origin_execution_id=execution_id,
        )
        return {
            "reflection_execution_id": reflection_id,
            "hypothesis_roots": (list(semantic.hypothesis_roots) if semantic is not None else []),
            "evidence_roots": list(semantic.evidence_roots) if semantic is not None else [],
            "experiment_root": semantic.experiment_root if semantic is not None else None,
            "experiment_work_item_id": (
                semantic.experiment_work_item_id if semantic is not None else None
            ),
            "cutover_receipt_root": (
                semantic.cutover_receipt_root if semantic is not None else None
            ),
            "recommended_next_action": recommended,
        }

    def reflect_mission(self, mission_id: str, *, timescale: str) -> dict[str, Any]:
        if timescale not in {"checkpoint", "terminal", "cross_run", "meta"}:
            raise ValueError("unsupported reflection timescale")
        mission = self.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
        outcomes = self.store.all(
            """SELECT * FROM strategy_outcomes WHERE mission_id=?
               ORDER BY created_at,id""",
            (mission_id,),
        )
        incidents = self.store.all(
            """SELECT id,status,layer,mechanism,effectiveness FROM incidents
               WHERE mission_id=? ORDER BY created_at,id""",
            (mission_id,),
        )
        source = {
            "mission_id": mission_id,
            "mission_version": mission["state_version"],
            "outcome_ids": [row["id"] for row in outcomes],
            "incident_ids": [row["id"] for row in incidents],
        }
        recurring: dict[str, int] = {}
        for row in outcomes:
            key = (row["strategy_key"], row["outcome"], row["failure_fingerprint"])
            recurring[str(key)] = recurring.get(str(key), 0) + 1
        result = {
            "timescale": timescale,
            "outcome_count": len(outcomes),
            "incident_count": len(incidents),
            "recurring_sequences": [
                {"key": key, "count": count} for key, count in recurring.items() if count >= 2
            ],
            "recommended_next_action": (
                "terminal_verify_open_items"
                if timescale == "terminal"
                else "evaluate_reusable_candidates"
            ),
        }
        execution_id = self._create_execution(
            mission_id=mission_id,
            timescale=timescale,
            source=source,
            result=result,
        )
        return {"reflection_execution_id": execution_id, **result}
