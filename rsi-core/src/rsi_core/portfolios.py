from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import RSITransitionError
from .models import PortfolioMode, PortfolioStatus, PortfolioTransition


class PortfolioPolicy:
    """Pure sequential and parallel improvement-lane transitions."""

    @staticmethod
    def validate_lanes(lanes: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
        if not lanes:
            raise ValueError("program portfolio requires at least one lane")
        lane_ids = tuple(str(lane.get("id", "")) for lane in lanes)
        if any(not lane_id for lane_id in lane_ids) or len(set(lane_ids)) != len(lane_ids):
            raise ValueError("portfolio lanes require unique stable ids")
        return lane_ids

    def activate(
        self,
        *,
        mode: PortfolioMode,
        lanes: Sequence[Mapping[str, Any]],
        status: str,
        baseline_currentness_root: str,
        currentness_root: str,
    ) -> PortfolioTransition:
        lane_ids = self.validate_lanes(lanes)
        if status != "planned":
            raise RSITransitionError("portfolio is not awaiting activation")
        if baseline_currentness_root != currentness_root:
            raise RSITransitionError("portfolio baseline is stale")
        if mode == "sequential":
            active: tuple[str, ...] = (lane_ids[0],)
        elif mode == "parallel":
            active = tuple(
                lane_id
                for lane_id, lane in zip(lane_ids, lanes, strict=True)
                if not lane.get("blocked", False)
            )
        else:
            raise ValueError(f"unsupported portfolio mode: {mode}")
        return PortfolioTransition(active, (), "active")

    def complete_lane(
        self,
        *,
        mode: PortfolioMode,
        lanes: Sequence[Mapping[str, Any]],
        status: str,
        active_lane_ids: Sequence[str],
        completed_lane_ids: Sequence[str],
        lane_id: str,
        succeeded: bool,
    ) -> PortfolioTransition:
        lane_ids = self.validate_lanes(lanes)
        if status != "active":
            raise RSITransitionError("portfolio is not active")
        active = list(active_lane_ids)
        completed = list(completed_lane_ids)
        if lane_id not in active:
            raise RSITransitionError("lane is not active")
        active.remove(lane_id)
        if succeeded:
            completed.append(lane_id)
        if mode == "sequential" and succeeded:
            remaining = [item for item in lane_ids if item not in set(active + completed)]
            if remaining:
                active.append(remaining[0])
        next_status: PortfolioStatus = (
            "failed"
            if not succeeded
            else "completed"
            if not active and len(completed) == len(lane_ids)
            else "active"
        )
        return PortfolioTransition(tuple(active), tuple(completed), next_status)
