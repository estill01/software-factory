from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .bootstrap import open_runtime

SKILLS = {
    "author-implementation-trackers": "program_author",
    "implement-tracker-blocks": "implementer",
    "supervise-tracker-runs": "supervisor",
    "evolve-product-program": "program_evolver",
    "clean-software-factory": "cleanup_owner",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sf-skill")
    parser.add_argument("skill", choices=sorted(SKILLS))
    parser.add_argument("--home", type=Path)
    parser.add_argument("--mission", required=True)
    parser.add_argument("--payload", default="{}", help="JSON command payload.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = open_runtime(args.home)
    mission = context.store.one("SELECT * FROM missions WHERE id=?", (args.mission,))
    payload = json.loads(args.payload)
    result = {
        "skill": args.skill,
        "role": SKILLS[args.skill],
        "mission_id": args.mission,
        "mission_version": mission["state_version"],
        "next_action": context.core.next_action(args.mission),
        "payload": payload,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
