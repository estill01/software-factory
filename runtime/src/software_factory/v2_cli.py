from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import cli as base_cli
from .advanced import AdvancedServices
from .api_main import main as api_main
from .doctor import RuntimeDoctor
from .entrypoints import context_core, context_store, open_context
from .migration import MigrationService
from .reporting import ReportingService

_ADVANCED_COMMANDS = {
    "advanced-tick",
    "api",
    "doctor",
    "migration-inventory",
    "migration-backup",
    "migration-import",
    "factory-floor",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Software Factory v2")
    parser.add_argument("--home")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tick = subparsers.add_parser("advanced-tick")
    tick.add_argument("--mission")
    tick.add_argument("--max-dispatch", type=int, default=4)

    api = subparsers.add_parser("api")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--root", default=".")
    doctor.add_argument("--stale-before")

    inventory = subparsers.add_parser("migration-inventory")
    inventory.add_argument("source_root")

    backup = subparsers.add_parser("migration-backup")
    backup.add_argument("migration_id")
    backup.add_argument("output_directory")

    import_command = subparsers.add_parser("migration-import")
    import_command.add_argument("migration_id")
    import_command.add_argument("--mission")

    floor = subparsers.add_parser("factory-floor")
    floor.add_argument("--mission")
    return parser


def _is_advanced(argv: Sequence[str]) -> bool:
    return any(value in _ADVANCED_COMMANDS for value in argv if not value.startswith("-"))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _is_advanced(arguments):
        return int(base_cli.main(arguments) or 0)
    args = build_parser().parse_args(arguments)
    if args.command == "api":
        api_arguments = ["--host", args.host, "--port", str(args.port)]
        if args.home:
            api_arguments = ["--home", args.home, *api_arguments]
        return api_main(api_arguments)

    context = open_context(args.home)
    store = context_store(context)
    core = context_core(context)
    advanced = AdvancedServices(store)
    migration = MigrationService(store)
    reporting = ReportingService(store)

    if args.command == "advanced-tick":
        result = (
            advanced.tick_mission(core, args.mission, max_dispatch=args.max_dispatch)
            if args.mission
            else advanced.tick_all(core, max_dispatch_per_mission=args.max_dispatch)
        )
    elif args.command == "doctor":
        doctor = RuntimeDoctor(store, root=Path(args.root))
        result = doctor.inspect()
        if args.stale_before:
            result["reconciled_commands"] = doctor.reconcile_stale_commands(
                stale_before=args.stale_before
            )
    elif args.command == "migration-inventory":
        result = migration.inventory_source(args.source_root)
    elif args.command == "migration-backup":
        result = migration.create_backup(
            args.migration_id, output_directory=args.output_directory
        )
    elif args.command == "migration-import":
        result = migration.import_historical(
            args.migration_id, target_mission_id=args.mission
        )
    elif args.command == "factory-floor":
        from .api import FactoryAPI

        result = FactoryAPI(store, advanced).factory_floor(args.mission)
    else:
        raise RuntimeError(f"unhandled command: {args.command}")
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
