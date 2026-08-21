from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Sequence
from typing import Any

from .advanced import AdvancedServices
from .entrypoints import context_core, context_store, open_context
from .reporting import ReportingService
from .util import utc_now


class AdaptiveDaemon:
    def __init__(self, context: Any):
        self.context = context
        self.store = context_store(context)
        self.core = context_core(context)
        self.advanced = AdvancedServices(self.store)
        self.reporting = ReportingService(self.store)
        self.stop_requested = False

    def request_stop(self, *_: Any) -> None:
        self.stop_requested = True

    def tick(self, *, max_dispatch_per_mission: int = 4) -> dict[str, Any]:
        schedules = self.reporting.due_schedules(limit=100)
        schedule_results: list[dict[str, Any]] = []
        for schedule in schedules:
            action = json.loads(schedule["action_json"])
            try:
                if action.get("kind") == "controller_tick":
                    mission_id = action.get("mission_id") or schedule.get("mission_id")
                    result = (
                        self.advanced.tick_mission(
                            self.core,
                            str(mission_id),
                            max_dispatch=max_dispatch_per_mission,
                        )
                        if mission_id
                        else self.advanced.tick_all(
                            self.core,
                            max_dispatch_per_mission=max_dispatch_per_mission,
                        )
                    )
                elif action.get("kind") == "reconcile_mission":
                    mission_id = action.get("mission_id") or schedule.get("mission_id")
                    if not mission_id:
                        raise ValueError("reconcile_mission schedule lacks mission_id")
                    result = self.advanced.reconcile_mission(str(mission_id))
                else:
                    raise ValueError(f"unsupported scheduled action: {action.get('kind')}")
            except BaseException as exc:
                self.reporting.mark_schedule_run(schedule["id"], succeeded=False)
                schedule_results.append(
                    {"schedule_id": schedule["id"], "status": "failed", "error": str(exc)}
                )
            else:
                self.reporting.mark_schedule_run(schedule["id"], succeeded=True)
                schedule_results.append(
                    {"schedule_id": schedule["id"], "status": "succeeded", "result": result}
                )
        missions = self.advanced.tick_all(
            self.core, max_dispatch_per_mission=max_dispatch_per_mission
        )
        return {
            "ticked_at": utc_now(),
            "missions": missions,
            "schedules": schedule_results,
        }

    def run(
        self,
        *,
        interval_seconds: float = 5.0,
        once: bool = False,
        max_dispatch_per_mission: int = 4,
    ) -> int:
        while not self.stop_requested:
            result = self.tick(max_dispatch_per_mission=max_dispatch_per_mission)
            print(json.dumps(result, sort_keys=True, default=str))
            if once:
                return 0
            time.sleep(max(0.1, interval_seconds))
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Software Factory v2 adaptive daemon")
    parser.add_argument("--home")
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--max-dispatch-per-mission", type=int, default=4)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    daemon = AdaptiveDaemon(open_context(args.home))
    signal.signal(signal.SIGTERM, daemon.request_stop)
    signal.signal(signal.SIGINT, daemon.request_stop)
    return daemon.run(
        interval_seconds=args.interval_seconds,
        once=args.once,
        max_dispatch_per_mission=args.max_dispatch_per_mission,
    )


if __name__ == "__main__":
    raise SystemExit(main())
