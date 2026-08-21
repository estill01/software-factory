from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .evolution import EvolutionService
from .learning import LearningService
from .operations import OperationsService
from .store import Store
from .supervision import IncidentEnvelope, SupervisionService


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


class AdvancedServices:
    """Integrated adaptive services layered around the transactional controller.

    The controller continues to own dispatch and provider effects. This coordinator
    observes those effects and routes material changes into supervision, learning,
    reflection, and program-evolution checkpoints without making the controller a
    procedural monolith.
    """

    def __init__(self, store: Store):
        self.store = store
        self.supervision = SupervisionService(store)
        self.learning = LearningService(store)
        self.evolution = EvolutionService(store)
        self.operations = OperationsService(store)

    def _monitor_execution(self, mission_id: str, execution: Mapping[str, Any]) -> dict[str, Any]:
        monitor = self.supervision.assign_monitor(
            mission_id=mission_id,
            target_type="execution",
            target_id=str(execution["id"]),
            role="watcher",
            agent_session_id=execution.get("agent_session_id"),
            policy={
                "material_fields": [
                    "status",
                    "provider_key",
                    "lease_generation",
                    "result_artifact_id",
                    "error_json",
                ]
            },
        )
        state = {
            "status": execution.get("status"),
            "provider_key": execution.get("provider_key"),
            "lease_generation": execution.get("lease_generation"),
            "result_artifact_id": execution.get("result_artifact_id"),
            "error": _loads(execution.get("error_json"), {}),
        }
        status = str(execution.get("status"))
        classification = (
            "failure"
            if status in {"failed", "abandoned", "timed_out", "cancelled"}
            else "success"
            if status == "succeeded"
            else "progress"
            if status in {"queued", "dispatching", "leased", "running", "verifying"}
            else "neutral"
        )
        evidence_ids = [
            str(value)
            for value in (
                execution.get("result_artifact_id"),
                execution.get("stdout_artifact_id"),
                execution.get("stderr_artifact_id"),
            )
            if value
        ]
        return self.supervision.observe(
            monitor["id"],
            state=state,
            classification=classification,  # type: ignore[arg-type]
            evidence_ids=evidence_ids,
        )

    def _route_material_execution(
        self,
        mission_id: str,
        execution: Mapping[str, Any],
        observation: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not observation.get("material"):
            return {"material": False, "actions": []}
        status = str(execution.get("status"))
        classification = str(observation.get("classification", "neutral"))
        event = self.learning.record_event(
            mission_id=mission_id,
            source_type="execution",
            source_id=str(execution["id"]),
            event_type=f"execution-{status}",
            classification=classification,  # type: ignore[arg-type]
            attributes={
                "work_item_id": execution.get("work_item_id"),
                "provider_key": execution.get("provider_key"),
                "lease_generation": execution.get("lease_generation"),
                "attempt_number": execution.get("attempt_number"),
                "error": _loads(execution.get("error_json"), {}),
            },
            evidence_ids=_loads(observation.get("evidence_ids_json"), []),
        )
        occurrences = self.learning.route_event(event["id"])
        actions: list[dict[str, Any]] = [
            {"kind": "learned-route", "occurrence_id": row["id"]} for row in occurrences
        ]
        if classification == "failure":
            incident = self.supervision.open_incident(
                mission_id=mission_id,
                target_type="execution",
                target_id=str(execution["id"]),
                observation_id=str(observation["id"]),
                severity="high" if status in {"abandoned", "timed_out"} else "medium",
                envelope=IncidentEnvelope(
                    mechanism={
                        "execution_status": status,
                        "provider_key": execution.get("provider_key"),
                        "error": _loads(execution.get("error_json"), {}),
                    },
                    trigger={
                        "event_id": event["id"],
                        "attempt_number": execution.get("attempt_number"),
                    },
                    effect={
                        "work_item_id": execution.get("work_item_id"),
                        "obligation_remains_open": True,
                    },
                    detection={
                        "observation_id": observation["id"],
                        "source": "observed_execution_state",
                    },
                    containment={
                        "scope": "affected_work_item",
                        "preserve_unrelated_safe_frontier": True,
                    },
                    correction={
                        "initial": "diagnose_then_select_supported_strategy",
                        "repeat_without_new_evidence": False,
                    },
                    recurrence={
                        "attempt_number": execution.get("attempt_number"),
                        "strategy_fingerprint": execution.get("prompt_root"),
                    },
                    human_scheduling_leakage={
                        "detected": False,
                        "ordinary_recovery_is_automatic": True,
                    },
                    affected_scope=_loads(execution.get("writable_scope_json"), []),
                ),
            )
            actions.append({"kind": "incident", "incident_id": incident["id"]})
        elif classification == "success":
            retained = self.supervision.record_success(
                mission_id=mission_id,
                source_type="execution",
                source_id=str(execution["id"]),
                context={
                    "work_item_id": execution.get("work_item_id"),
                    "provider_key": execution.get("provider_key"),
                },
                mechanism={
                    "prompt_root": execution.get("prompt_root"),
                    "attempt_number": execution.get("attempt_number"),
                },
                trigger={"event_id": event["id"]},
                outcome={
                    "status": status,
                    "result_artifact_id": execution.get("result_artifact_id"),
                },
                response={"retain_for_bounded_generalization": True},
                applicability={"provider_key": execution.get("provider_key")},
            )
            actions.append(
                {
                    "kind": "success-reflection",
                    "case_id": retained["case"]["id"],
                    "next_action": retained["next_action"],
                }
            )
        return {"material": True, "event_id": event["id"], "actions": actions}

    def reconcile_mission(self, mission_id: str) -> dict[str, Any]:
        executions = self.store.all(
            """SELECT e.*, w.writable_scope_json
               FROM executions e
               LEFT JOIN work_items w ON w.id=e.work_item_id
               WHERE e.mission_id=?
               ORDER BY e.created_at,e.id""",
            (mission_id,),
        )
        material_routes: list[dict[str, Any]] = []
        for execution in executions:
            observation = self._monitor_execution(mission_id, execution)
            routed = self._route_material_execution(mission_id, execution, observation)
            if routed["material"]:
                material_routes.append(
                    {"execution_id": execution["id"], "route": routed}
                )
        incidents = self.store.all(
            """SELECT * FROM supervision_incidents
               WHERE mission_id=? AND status IN ('open','contained','correcting','verifying')
               ORDER BY opened_at""",
            (mission_id,),
        )
        checkpoint = self.evolution.checkpoint(
            mission_id=mission_id,
            boundary_type="checkpoint",
            source_type="mission",
            source_id=mission_id,
            state={
                "executions": [
                    {"id": row["id"], "status": row["status"]} for row in executions
                ],
                "incidents": [
                    {
                        "id": row["id"],
                        "status": row["status"],
                        "causal_level": row["causal_level"],
                    }
                    for row in incidents
                ],
            },
            observations={
                "material_routes": len(material_routes),
                "active_incidents": len(incidents),
            },
            evidence_ids=[
                str(route["route"]["event_id"])
                for route in material_routes
                if route["route"].get("event_id")
            ]
            or [f"mission-state:{mission_id}"],
        )
        return {
            "mission_id": mission_id,
            "material_routes": material_routes,
            "active_incidents": incidents,
            "evolution_checkpoint": checkpoint,
        }

    def tick_mission(
        self,
        core: Any,
        mission_id: str,
        *,
        max_dispatch: int = 4,
    ) -> dict[str, Any]:
        controller = getattr(core, "controller", core)
        controller_result = controller.tick_mission(
            mission_id, max_dispatch=max_dispatch
        )
        adaptive_result = self.reconcile_mission(mission_id)
        ready = []
        work_items = getattr(core, "work_items", None)
        if work_items is not None and hasattr(work_items, "ready_work"):
            ready = work_items.ready_work(mission_id)
        safe = self.supervision.safe_frontier(mission_id, ready)
        return {
            "mission_id": mission_id,
            "controller": controller_result,
            "adaptive": adaptive_result,
            "safe_frontier": safe,
        }

    def tick_all(self, core: Any, *, max_dispatch_per_mission: int = 4) -> list[dict[str, Any]]:
        missions = self.store.all(
            """SELECT id FROM missions
               WHERE status NOT IN ('completed','cancelled','failed')
               ORDER BY created_at,id"""
        )
        return [
            self.tick_mission(
                core,
                str(row["id"]),
                max_dispatch=max_dispatch_per_mission,
            )
            for row in missions
        ]
