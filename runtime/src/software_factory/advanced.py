from __future__ import annotations

from typing import Any

from .adaptive import AdaptiveExecutionService
from .continuation import ContinuationService
from .evolution import EvolutionService
from .integrations.librsi import LibRSIIntegration
from .learning import LearningService
from .operations import OperationsService
from .store import Store
from .supervision import SupervisionService
from .work_items import WorkItemService


class AdvancedServices:
    """Coordinator over the canonical operational services.

    This object owns no alternate schema or lifecycle. It can assemble a coherent
    compatibility graph when used directly, while ``CoreService`` injects its one
    shared work, continuation, supervision, and adaptive service graph.
    """

    def __init__(
        self,
        store: Store,
        *,
        work_items: WorkItemService | None = None,
        continuation: ContinuationService | None = None,
        supervision: SupervisionService | None = None,
        adaptive: AdaptiveExecutionService | None = None,
        learning: LearningService | None = None,
        evolution: EvolutionService | None = None,
        operations: OperationsService | None = None,
    ) -> None:
        self.store = store
        self.work_items = work_items or WorkItemService(store)
        self.continuation = continuation or ContinuationService(store, self.work_items)
        self.supervision = supervision or SupervisionService(
            store,
            work_items=self.work_items,
            continuation=self.continuation,
        )
        if learning is None:
            semantic = LibRSIIntegration(store, work_items=self.work_items)
            self.learning = LearningService(store, semantic=semantic)
        else:
            self.learning = learning
            if self.learning.semantic.work_items is None:
                self.learning.semantic.work_items = self.work_items
        self.adaptive = adaptive or AdaptiveExecutionService(
            store,
            work_items=self.work_items,
            continuation=self.continuation,
            supervision=self.supervision,
            semantic_integration=self.learning.semantic,
        )
        if self.adaptive.semantic is not self.learning.semantic:
            raise ValueError("advanced services require one shared libRSI semantic owner")
        if self.supervision.adaptive is None:
            self.supervision.bind_adaptive(self.adaptive)
        elif self.supervision.adaptive is not self.adaptive:
            raise ValueError("supervision is already bound to a different adaptive owner")
        self.evolution = evolution or EvolutionService(store, semantic=self.learning.semantic)
        if self.evolution.semantic is not self.learning.semantic:
            raise ValueError("advanced services require one shared libRSI semantic owner")
        self._operations = operations or OperationsService(store)

    def reconcile_mission(self, mission_id: str) -> dict[str, Any]:
        """Observe canonical outcomes, run due checks, and record one checkpoint."""

        observed = self.adaptive.observe_new_execution_outcomes(mission_id)
        checks = self.supervision.run_due_checks(mission_id)
        incidents = self.store.all(
            """SELECT id,status,layer,severity,failure_fingerprint,strategy_key
               FROM incidents
               WHERE mission_id=? AND status IN ('open','contained','correcting','verifying')
               ORDER BY created_at,id""",
            (mission_id,),
        )
        strategy_outcomes = self.store.all(
            """SELECT id,execution_id,outcome,evidence_root,failure_fingerprint,strategy_key
               FROM strategy_outcomes WHERE mission_id=? ORDER BY created_at,id""",
            (mission_id,),
        )
        checkpoint = self.evolution.checkpoint(
            mission_id=mission_id,
            boundary_type="checkpoint",
            source_type="mission",
            source_id=mission_id,
            state={
                "incidents": incidents,
                "strategy_outcomes": strategy_outcomes,
            },
            observations={
                "new_execution_outcomes": len(observed),
                "supervision_checks": len(checks),
                "active_incidents": len(incidents),
            },
            evidence_ids=[
                str(row["evidence_root"]) for row in strategy_outcomes if row.get("evidence_root")
            ]
            or [f"mission-state:{mission_id}"],
        )
        return {
            "mission_id": mission_id,
            "execution_outcomes": observed,
            "supervision_checks": checks,
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
            mission_id,
            max_dispatch=max_dispatch,
        )
        adaptive_result = self.reconcile_mission(mission_id)
        return {
            "mission_id": mission_id,
            "controller": controller_result,
            "adaptive": adaptive_result,
            "safe_frontier": self.work_items.ready_work(mission_id),
            "continuation": self.continuation.next_action(mission_id),
        }

    def tick_all(
        self,
        core: Any,
        *,
        max_dispatch_per_mission: int = 4,
    ) -> list[dict[str, Any]]:
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
