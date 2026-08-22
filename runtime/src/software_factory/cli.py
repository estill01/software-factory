from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .bootstrap import open_runtime


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="software-factory",
        description="Operate the native Software Factory v2 runtime.",
    )
    parser.add_argument(
        "--home",
        type=Path,
        help="Runtime state directory (default: $SOFTWARE_FACTORY_HOME or ~/.software-factory).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the state database and runtime directories.")
    sub.add_parser("health", help="Run database and continuation health checks.")

    status = sub.add_parser("status", help="Show bounded runtime or mission status.")
    status.add_argument("--mission")

    tick = sub.add_parser("tick", help="Recover, poll, and dispatch one mission.")
    tick.add_argument("mission")
    tick.add_argument("--max-dispatch", type=int)
    tick.add_argument("--no-auto-spawn", action="store_true")

    callback = sub.add_parser(
        "provider-callback", help="Submit a fenced provider result to a durable execution."
    )
    callback.add_argument("execution")
    callback.add_argument("generation", type=int)
    callback.add_argument("token")
    callback.add_argument("status", choices=("succeeded", "failed"))
    callback.add_argument("--result", default="{}", help="JSON result/error payload.")

    verify = sub.add_parser("verify-events", help="Verify a hash-chained event stream.")
    verify.add_argument("--mission")

    create_project = sub.add_parser("create-project", help="Create a project.")
    create_project.add_argument("name")

    create_mission = sub.add_parser("create-mission", help="Create an autonomous mission.")
    create_mission.add_argument("title")
    create_mission.add_argument("objective")
    create_mission.add_argument("--project")
    create_mission.add_argument(
        "--autonomy-mode",
        default="full_autonomous",
        choices=("fixed", "recommend", "reviewed_autonomous", "full_autonomous"),
    )
    return parser


def _mission_status(context: Any, mission_id: str) -> dict[str, Any]:
    mission = context.store.one("SELECT * FROM missions WHERE id=?", (mission_id,))
    return {
        "mission": mission,
        "capabilities": context.store.all(
            "SELECT * FROM capabilities WHERE mission_id=? ORDER BY created_at", (mission_id,)
        ),
        "obligations": context.store.all(
            "SELECT * FROM obligations WHERE mission_id=? ORDER BY priority DESC,created_at",
            (mission_id,),
        ),
        "work": context.store.all(
            "SELECT * FROM work_items WHERE mission_id=? ORDER BY priority DESC,created_at",
            (mission_id,),
        ),
        "executions": context.store.all(
            "SELECT * FROM executions WHERE mission_id=? ORDER BY created_at DESC LIMIT 100",
            (mission_id,),
        ),
        "next_action": context.core.next_action(mission_id),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = open_runtime(args.home)

    if args.command == "init":
        _json(
            {
                "initialized": True,
                "home": str(context.paths.root),
                "database": str(context.paths.database),
                "schema_version": context.store.health()["schema_version"],
            }
        )
        return 0
    if args.command == "health":
        health = context.store.health()
        _json(health)
        return 0 if health["ok"] else 1
    if args.command == "status":
        if args.mission:
            _json(_mission_status(context, args.mission))
        else:
            _json(
                {
                    "health": context.store.health(),
                    "missions": context.store.all(
                        "SELECT * FROM missions ORDER BY created_at DESC LIMIT 100"
                    ),
                    "active_executions": context.store.all(
                        """SELECT * FROM executions
                           WHERE status IN ('queued','dispatching','leased','running','verifying')
                           ORDER BY created_at"""
                    ),
                }
            )
        return 0
    if args.command == "tick":
        _json(
            context.core.tick_mission(
                args.mission,
                max_dispatch=args.max_dispatch,
                auto_spawn=not args.no_auto_spawn,
            )
        )
        return 0
    if args.command == "provider-callback":
        payload = json.loads(args.result)
        if not isinstance(payload, dict):
            raise ValueError("provider callback result must be a JSON object")
        _json(
            context.core.accept_provider_callback(
                args.execution,
                token=args.token,
                generation=args.generation,
                succeeded=args.status == "succeeded",
                result=payload,
            )
        )
        return 0
    if args.command == "verify-events":
        _json(context.store.verify_event_chain(args.mission))
        return 0
    if args.command == "create-project":
        _json({"project_id": context.core.create_project(args.name)})
        return 0
    if args.command == "create-mission":
        mission_id = context.core.create_mission(
            project_id=args.project,
            title=args.title,
            objective=args.objective,
            autonomy_mode=args.autonomy_mode,
        )
        _json({"mission_id": mission_id})
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
