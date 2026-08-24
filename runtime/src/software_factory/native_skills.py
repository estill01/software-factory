from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .entrypoints import context_core, open_context

SKILLS = {
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
    "evolve-product-program",
    "clean-software-factory",
}


def _payload(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    if not isinstance(loaded, Mapping):
        raise ValueError("skill payload must be a JSON object")
    return dict(loaded)


def invoke(
    *,
    skill: str,
    mission_id: str,
    payload: Mapping[str, Any],
    context: Any,
) -> Mapping[str, Any]:
    if skill not in SKILLS:
        raise ValueError(f"unsupported Software Factory skill: {skill}")
    core = context_core(context)
    advanced = core.advanced
    reporting = core.reporting
    migration = core.migration

    if skill == "implement-tracker-blocks":
        return advanced.tick_mission(
            core,
            mission_id,
            max_dispatch=int(payload.get("max_dispatch", 4)),
        )

    if skill == "supervise-tracker-runs":
        result = advanced.reconcile_mission(mission_id)
        if payload.get("generate_report"):
            report = reporting.generate_report(
                report_type="checkpoint",
                source_type="mission",
                source_id=mission_id,
                mission_id=mission_id,
                content=result,
                output_directory=payload.get("output_directory", ".software-factory/reports"),
                title=f"Software Factory mission {mission_id}",
            )
            result = dict(result) | {"report_id": report["id"], "pdf_path": report["pdf_path"]}
        return result

    if skill == "author-implementation-trackers":
        action = str(payload.get("action", "checkpoint"))
        if action == "propose_program_change":
            roots = payload.get("roots", {})
            if not isinstance(roots, Mapping):
                raise ValueError("program-change roots must be an object")
            return advanced.evolution.propose_program_change(
                mission_id=mission_id,
                program_id=payload.get("program_id"),
                checkpoint_id=payload.get("checkpoint_id"),
                change_kind=str(payload["change_kind"]),
                rationale=dict(payload.get("rationale", {})),
                change_spec=dict(payload.get("change_spec", {})),
                requested_range_root=str(roots["requested_range_root"]),
                accepted_history_root=str(roots["accepted_history_root"]),
                currentness_root=str(roots["currentness_root"]),
                author_session_id=payload.get("author_session_id"),
            )
        return advanced.evolution.checkpoint(
            mission_id=mission_id,
            program_id=payload.get("program_id"),
            boundary_type=str(payload.get("boundary_type", "checkpoint")),
            source_type=str(payload.get("source_type", "mission")),
            source_id=str(payload.get("source_id", mission_id)),
            state=dict(payload.get("state", {})),
            observations=dict(payload.get("observations", {})),
            evidence_ids=[str(value) for value in payload.get("evidence_ids", [])],
        )

    if skill == "evolve-product-program":
        action = str(payload.get("action", "checkpoint"))
        if action == "create_portfolio":
            lanes = payload.get("lanes", [])
            if not isinstance(lanes, list) or not all(isinstance(item, Mapping) for item in lanes):
                raise ValueError("portfolio lanes must be a list of objects")
            return advanced.evolution.create_portfolio(
                mission_id=mission_id,
                mode=str(payload.get("mode", "parallel")),
                lanes=[dict(item) for item in lanes],
                baseline_currentness_root=str(payload["baseline_currentness_root"]),
                parent_program_id=payload.get("parent_program_id"),
            )
        if action == "consider_selection":
            return advanced.evolution.consider_selection(
                mission_id=mission_id,
                selection_group=str(payload["selection_group"]),
                selection_type=str(payload["selection_type"]),
                candidate_key=str(payload["candidate_key"]),
                candidate=dict(payload.get("candidate", {})),
                evidence=dict(payload.get("evidence", {})),
                expected_value=dict(payload.get("expected_value", {})),
                proposer_session_id=payload.get("proposer_session_id"),
            )
        if action == "propose_selector_policy":
            return advanced.evolution.propose_selector_policy(
                mission_id=mission_id,
                name=str(payload["name"]),
                policy=dict(payload.get("policy", {})),
                author_session_id=payload.get("author_session_id"),
            )
        return advanced.reconcile_mission(mission_id)

    repository_root = Path(str(payload.get("repository_root", "."))).resolve()
    action = str(payload.get("action", "inventory"))
    if action == "inventory":
        return advanced._operations.inventory_repository(
            repository_root=repository_root,
            mission_id=mission_id,
            active_writers=[dict(item) for item in payload.get("active_writers", [])],
        )
    if action == "preserve":
        inventory_id = str(payload["inventory_id"])
        return advanced._operations.preserve_repository(
            inventory_id,
            output_directory=payload.get("output_directory", ".software-factory/preservation"),
        )
    if action == "migration_inventory":
        return migration.inventory_source(payload.get("source_root", repository_root))
    raise ValueError(f"unsupported cleanup skill action: {action}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native Software Factory v2 skill bridge")
    parser.add_argument("skill", choices=sorted(SKILLS))
    parser.add_argument("--mission", required=True)
    parser.add_argument("--payload", default="{}")
    parser.add_argument("--home")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = invoke(
        skill=args.skill,
        mission_id=args.mission,
        payload=_payload(args.payload),
        context=open_context(args.home),
    )
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
