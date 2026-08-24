from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .util import json_load

ACTIVE_EXECUTION_STATUSES = (
    "queued",
    "dispatching",
    "leased",
    "running",
    "verifying",
)


def _positive_integer(limits: Mapping[str, Any], key: str, default: int) -> int:
    value = limits.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"resource limit {key} must be a positive integer")
    return value


@dataclass(frozen=True)
class SchedulingPolicy:
    """The bounded scheduling portion of a mission's durable resource policy."""

    max_parallel: int = 4
    max_dispatch_per_tick: int = 4
    max_attempts_per_work: int = 3

    @classmethod
    def from_resource_limits(
        cls, resource_limits: Mapping[str, Any] | str | bytes | None
    ) -> SchedulingPolicy:
        if isinstance(resource_limits, (str, bytes)) or resource_limits is None:
            resource_limits = json_load(resource_limits, {})
        if not isinstance(resource_limits, Mapping):
            raise ValueError("mission resource limits must be an object")
        return cls(
            max_parallel=_positive_integer(resource_limits, "max_parallel", 4),
            max_dispatch_per_tick=_positive_integer(resource_limits, "max_dispatch_per_tick", 4),
            max_attempts_per_work=_positive_integer(resource_limits, "max_attempts_per_work", 3),
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "max_parallel": self.max_parallel,
            "max_dispatch_per_tick": self.max_dispatch_per_tick,
            "max_attempts_per_work": self.max_attempts_per_work,
        }

    def tick_limit(self, requested: int | None) -> int:
        if requested is None:
            return self.max_dispatch_per_tick
        if isinstance(requested, bool) or not isinstance(requested, int) or requested < 0:
            raise ValueError("max_dispatch must be a non-negative integer")
        return min(requested, self.max_dispatch_per_tick)


def active_execution_count(
    store: Any,
    mission_id: str,
    *,
    db: Any | None = None,
) -> int:
    placeholders = ",".join("?" for _ in ACTIVE_EXECUTION_STATUSES)
    return int(
        store.scalar(
            f"""SELECT COUNT(*) FROM executions
                WHERE mission_id=? AND status IN ({placeholders})""",
            (mission_id, *ACTIVE_EXECUTION_STATUSES),
            db=db,
        )
        or 0
    )


def implementation_attempt_counts(
    store: Any,
    work_item_ids: Sequence[str],
    *,
    db: Any | None = None,
) -> dict[str, int]:
    if not work_item_ids:
        return {}
    placeholders = ",".join("?" for _ in work_item_ids)
    rows = store.all(
        f"""SELECT work_item_id,COUNT(*) AS attempts FROM executions
            WHERE execution_type='implementation'
              AND work_item_id IN ({placeholders})
            GROUP BY work_item_id""",
        tuple(work_item_ids),
        db=db,
    )
    return {str(row["work_item_id"]): int(row["attempts"]) for row in rows}


def budget_exhausted_work_item_ids(
    store: Any,
    mission_id: str,
    policy: SchedulingPolicy,
    *,
    db: Any | None = None,
) -> list[str]:
    rows = store.all(
        """SELECT w.id,COUNT(e.id) AS attempts
           FROM work_items w
           LEFT JOIN executions e
             ON e.work_item_id=w.id AND e.execution_type='implementation'
           WHERE w.mission_id=? AND w.planning_status='selected'
             AND w.execution_status IN ('not_started','queued','abandoned')
           GROUP BY w.id,w.priority,w.created_at
           HAVING COUNT(e.id)>=?
           ORDER BY w.priority DESC,w.created_at,w.id""",
        (mission_id, policy.max_attempts_per_work),
        db=db,
    )
    return [str(row["id"]) for row in rows]
