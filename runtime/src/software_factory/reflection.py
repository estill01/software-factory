from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from .errors import InvalidTransition, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now

_HYPOTHESIS_STATES = {
    "proposed",
    "challenged",
    "selected_for_test",
    "testing",
    "supported",
    "refuted",
    "inconclusive",
    "superseded",
    "retired",
}


class ReflectionService:
    """Structured live/checkpoint/terminal/cross-run reflection.

    Reflection is recorded as an execution. Narrative or model output may be attached as
    an artifact by an adapter, but canonical outputs are hypotheses and explicit next
    actions derived from exact observed state.
    """

    def __init__(self, store: Any, *, work_items: Any) -> None:
        self.store = store
        self.work_items = work_items

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

    def _create_hypothesis(
        self,
        *,
        mission_id: str,
        obligation_id: str | None,
        origin_execution_id: str,
        hypothesis_type: str,
        statement: str,
        scope: Mapping[str, Any],
        expected_evidence: Mapping[str, Any],
        supporting_evidence: Sequence[str] = (),
        contrary_evidence: Sequence[str] = (),
        uncertainty: Mapping[str, Any] | None = None,
        parent_hypothesis_id: str | None = None,
    ) -> str:
        existing = self.store.one(
            """SELECT id FROM hypotheses WHERE mission_id=? AND statement=?
               AND status NOT IN ('superseded','retired') ORDER BY created_at DESC LIMIT 1""",
            (mission_id, statement),
            required=False,
        )
        if existing is not None:
            return str(existing["id"])
        hypothesis_id = new_id("hyp")
        now = utc_now()
        evidence_root = digest_json(
            {
                "supporting": list(supporting_evidence),
                "contrary": list(contrary_evidence),
            }
        )
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO hypotheses(
                    id,mission_id,obligation_id,origin_execution_id,parent_hypothesis_id,
                    hypothesis_type,statement,status,scope_json,expected_evidence_json,
                    supporting_evidence_json,contrary_evidence_json,uncertainty_json,
                    state_version,created_at,updated_at,current_evidence_root
                ) VALUES(?,?,?,?,?,?,?,'proposed',?,?,?,?,?,1,?,?,?)""",
                (
                    hypothesis_id,
                    mission_id,
                    obligation_id,
                    origin_execution_id,
                    parent_hypothesis_id,
                    hypothesis_type,
                    statement,
                    canonical_json(dict(scope)),
                    canonical_json(dict(expected_evidence)),
                    canonical_json(list(supporting_evidence)),
                    canonical_json(list(contrary_evidence)),
                    canonical_json(dict(uncertainty or {})),
                    now,
                    now,
                    evidence_root,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="reflection",
                event_type="hypothesis.proposed",
                subject_type="hypothesis",
                subject_id=hypothesis_id,
                causation_id=origin_execution_id,
                new_version=1,
                payload={
                    "hypothesis_type": hypothesis_type,
                    "statement": statement,
                    "scope": dict(scope),
                    "expected_evidence": dict(expected_evidence),
                },
            )
        return hypothesis_id

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
        if failure:
            fingerprint = str(
                execution.get("failure_fingerprint")
                or digest_json(json_load(execution["error_json"], {}))
            )
            hypotheses = [
                {
                    "type": "causal",
                    "statement": (
                        f"Strategy {strategy} is causally associated with failure "
                        f"fingerprint {fingerprint} in the current work context."
                    ),
                    "expected": {
                        "discriminator": "materially different strategy avoids the fingerprint"
                    },
                },
                {
                    "type": "problem_framing",
                    "statement": (
                        f"The failure fingerprint {fingerprint} may be caused by environment, "
                        "currentness, or acceptance setup rather than the implementation strategy."
                    ),
                    "expected": {
                        "discriminator": "same strategy succeeds under corrected invocation/currentness"
                    },
                },
            ]
            recommended = "run_discriminating_experiment"
        elif unexpected:
            hypotheses = [
                {
                    "type": "strategy",
                    "statement": (
                        f"Strategy {strategy} produced an unusually strong capability effect in "
                        "the observed context."
                    ),
                    "expected": {"discriminator": "benefit recurs in a bounded similar context"},
                },
                {
                    "type": "predictive",
                    "statement": (
                        "The observed improvement may be contextual noise or an unrelated concurrent "
                        "change rather than a reusable strategy effect."
                    ),
                    "expected": {"discriminator": "benefit disappears under matched replay"},
                },
            ]
            recommended = "bounded_replay_and_counterexample_search"
        else:
            hypotheses = []
            recommended = "retain_current_strategy"

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
            "problem_reframing": "strategy_effect" if hypotheses else "no_material_reframe",
            "hypotheses": hypotheses,
            "recommended_next_action": recommended,
        }
        reflection_id = self._create_execution(
            mission_id=mission_id,
            timescale=timescale,
            source=source,
            result=result,
            origin_execution_id=execution_id,
        )
        hypothesis_ids = [
            self._create_hypothesis(
                mission_id=mission_id,
                obligation_id=execution.get("obligation_id"),
                origin_execution_id=reflection_id,
                hypothesis_type=cast(str, item["type"]),
                statement=cast(str, item["statement"]),
                scope={
                    "work_item_id": execution.get("work_item_id"),
                    "strategy_key": strategy,
                },
                expected_evidence=cast(Mapping[str, Any], item["expected"]),
                supporting_evidence=[execution_id],
                uncertainty={"posture": "requires_discrimination"},
            )
            for item in hypotheses
        ]
        return {
            "reflection_execution_id": reflection_id,
            "hypothesis_ids": hypothesis_ids,
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

    def update_hypothesis(
        self,
        hypothesis_id: str,
        *,
        expected_version: int,
        status: str,
        supporting_evidence: Sequence[str] = (),
        contrary_evidence: Sequence[str] = (),
    ) -> dict[str, Any]:
        if status not in _HYPOTHESIS_STATES:
            raise ValueError("unsupported hypothesis status")
        now = utc_now()
        with self.store.transaction() as db:
            current = self.store.check_version(
                db,
                table="hypotheses",
                row_id=hypothesis_id,
                expected_version=expected_version,
            )
            support = list(json_load(current["supporting_evidence_json"], []))
            contrary = list(json_load(current["contrary_evidence_json"], []))
            support.extend(item for item in supporting_evidence if item not in support)
            contrary.extend(item for item in contrary_evidence if item not in contrary)
            root = digest_json({"supporting": support, "contrary": contrary})
            db.execute(
                """UPDATE hypotheses SET status=?,supporting_evidence_json=?,
                   contrary_evidence_json=?,current_evidence_root=?,last_tested_at=?,
                   state_version=?,updated_at=? WHERE id=?""",
                (
                    status,
                    canonical_json(support),
                    canonical_json(contrary),
                    root,
                    now,
                    expected_version + 1,
                    now,
                    hypothesis_id,
                ),
            )
            self.store.append_event(
                db,
                mission_id=current["mission_id"],
                stream_key="reflection",
                event_type=f"hypothesis.{status}",
                subject_type="hypothesis",
                subject_id=hypothesis_id,
                prior_version=expected_version,
                new_version=expected_version + 1,
                payload={
                    "supporting_evidence": support,
                    "contrary_evidence": contrary,
                    "evidence_root": root,
                },
            )
        result = self.store.one("SELECT * FROM hypotheses WHERE id=?", (hypothesis_id,))
        if result is None:
            raise StoreError("hypothesis disappeared after update")
        return result
