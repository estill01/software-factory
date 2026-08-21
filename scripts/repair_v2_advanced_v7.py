#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SOURCE = RUNTIME / "src" / "software_factory"
TESTS = RUNTIME / "tests"


def add_import(path: Path, marker: str, import_line: str) -> None:
    text = path.read_text(encoding="utf-8")
    if import_line in text:
        return
    if marker not in text:
        raise RuntimeError(f"import marker missing in {path}: {marker}")
    path.write_text(text.replace(marker, marker + import_line, 1), encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def wire_problem_solving() -> None:
    path = SOURCE / "advanced.py"
    add_import(path, "import json\n", "import hashlib\n")
    add_import(
        path,
        "from .operations import OperationsService\n",
        "from .problem_solving import ProblemSolvingService\n",
    )
    text = path.read_text(encoding="utf-8")
    assignment_marker = "        self.learning = LearningService(store)\n"
    assignment = "        self.problem_solving = ProblemSolvingService(store, self.learning)\n"
    if assignment not in text:
        if assignment_marker not in text:
            raise RuntimeError("advanced learning assignment marker missing")
        text = text.replace(assignment_marker, assignment_marker + assignment, 1)
    helper_marker = '''def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))
'''
    helper_addition = helper_marker + '''

def _root(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
'''
    if "def _root(value: Any)" not in text:
        if helper_marker not in text:
            raise RuntimeError("advanced helper insertion point missing")
        text = text.replace(helper_marker, helper_addition, 1)
    path.write_text(text, encoding="utf-8")


def route_failures_into_problem_cycles() -> None:
    path = SOURCE / "advanced.py"
    text = path.read_text(encoding="utf-8")
    marker = '''            actions.append({"kind": "incident", "incident_id": incident["id"]})
        elif classification == "success":
'''
    addition = '''            actions.append({"kind": "incident", "incident_id": incident["id"]})
            mission = self.store.one(
                "SELECT * FROM missions WHERE id=?", (mission_id,)
            )
            requested_range = (
                mission.get("requested_range_root")
                or mission.get("range_root")
                or _root(_loads(mission.get("requested_range_json"), {}))
            )
            cycle = self.problem_solving.begin_cycle(
                mission_id=mission_id,
                trigger_type="incident",
                trigger_id=incident["id"],
                objective={
                    "mission_goal": mission.get("goal"),
                    "required_outcome": "restore forward progress without closing the obligation",
                    "work_item_id": execution.get("work_item_id"),
                },
                governing_range_root=str(requested_range),
                state={
                    "execution_id": execution["id"],
                    "status": status,
                    "error": _loads(execution.get("error_json"), {}),
                    "incident_id": incident["id"],
                },
                causal_level=int(incident["causal_level"]),
            )
            actions.append(
                {
                    "kind": "problem-solving-cycle",
                    "cycle_id": cycle["id"],
                    "next_action": self.problem_solving.next_action(cycle["id"]),
                }
            )
        elif classification == "success":
'''
    if "\"kind\": \"problem-solving-cycle\"" not in text:
        if marker not in text:
            raise RuntimeError("failure problem-cycle insertion point missing")
        text = text.replace(marker, addition, 1)
    path.write_text(text, encoding="utf-8")


def route_successes_into_bounded_generalization() -> None:
    path = SOURCE / "advanced.py"
    text = path.read_text(encoding="utf-8")
    marker = '''            actions.append(
                {
                    "kind": "success-reflection",
                    "case_id": retained["case"]["id"],
                    "next_action": retained["next_action"],
                }
            )
        return {"material": True, "event_id": event["id"], "actions": actions}
'''
    addition = '''            actions.append(
                {
                    "kind": "success-reflection",
                    "case_id": retained["case"]["id"],
                    "next_action": retained["next_action"],
                }
            )
            mission = self.store.one(
                "SELECT * FROM missions WHERE id=?", (mission_id,)
            )
            requested_range = (
                mission.get("requested_range_root")
                or mission.get("range_root")
                or _root(_loads(mission.get("requested_range_json"), {}))
            )
            success_cycle = self.problem_solving.begin_cycle(
                mission_id=mission_id,
                trigger_type="unexpected_success",
                trigger_id=retained["case"]["id"],
                objective={
                    "mission_goal": mission.get("goal"),
                    "required_outcome": "test whether the successful method generalizes safely",
                },
                governing_range_root=str(requested_range),
                state={
                    "execution_id": execution["id"],
                    "case_id": retained["case"]["id"],
                    "provider_key": execution.get("provider_key"),
                },
            )
            generalization = self.problem_solving.record_unexpected_success(
                success_cycle["id"],
                source_id=str(execution["id"]),
                mechanism={
                    "prompt_root": execution.get("prompt_root"),
                    "provider_key": execution.get("provider_key"),
                    "attempt_number": execution.get("attempt_number"),
                },
                outcome={
                    "status": status,
                    "result_artifact_id": execution.get("result_artifact_id"),
                },
                evidence_ids=[event["id"]],
                proposer_session_id=execution.get("agent_session_id"),
            )
            actions.append(
                {
                    "kind": "bounded-success-generalization",
                    "cycle_id": success_cycle["id"],
                    "strategy_id": generalization["id"],
                }
            )
        return {"material": True, "event_id": event["id"], "actions": actions}
'''
    if "\"kind\": \"bounded-success-generalization\"" not in text:
        if marker not in text:
            raise RuntimeError("success generalization insertion point missing")
        text = text.replace(marker, addition, 1)
    path.write_text(text, encoding="utf-8")


def add_recurring_signal_discovery_and_cycle_status() -> None:
    path = SOURCE / "advanced.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        checkpoint = self.evolution.checkpoint(
            mission_id=mission_id,
'''
    addition = '''        discovered_signals = self.learning.discover_recurring_sequences(
            mission_id, min_support=3, sequence_length=2
        )
        problem_cycles = self.store.all(
            """SELECT * FROM problem_solving_cycles_v2
               WHERE mission_id=? AND status NOT IN ('resolved','superseded')
               ORDER BY created_at""",
            (mission_id,),
        )
        problem_next_actions = [
            {
                "cycle_id": cycle["id"],
                "next_action": self.problem_solving.next_action(cycle["id"]),
            }
            for cycle in problem_cycles
        ]
        checkpoint = self.evolution.checkpoint(
            mission_id=mission_id,
'''
    if "discovered_signals = self.learning.discover_recurring_sequences(" not in text:
        if marker not in text:
            raise RuntimeError("advanced recurring signal insertion point missing")
        text = text.replace(marker, addition, 1)
    return_marker = '''            "active_incidents": incidents,
            "evolution_checkpoint": checkpoint,
        }
'''
    return_addition = '''            "active_incidents": incidents,
            "discovered_signal_candidates": discovered_signals,
            "problem_cycles": problem_cycles,
            "problem_next_actions": problem_next_actions,
            "evolution_checkpoint": checkpoint,
        }
'''
    if '"problem_next_actions": problem_next_actions' not in text:
        if return_marker not in text:
            raise RuntimeError("advanced reconcile return marker missing")
        text = text.replace(return_marker, return_addition, 1)
    path.write_text(text, encoding="utf-8")


def wire_core_services() -> None:
    path = SOURCE / "core.py"
    add_import(
        path,
        "from .program import ProgramService\n",
        "from .problem_solving import ProblemSolvingService\n",
    )
    add_import(
        path,
        "from .qa import QAService\n",
        "from .recovery import FactoryRecoveryCoordinator, ReleaseRefreshCoordinator\n",
    )
    text = path.read_text(encoding="utf-8")
    marker = "        self.governance = GovernanceService(store)\n"
    assignments = (
        "        self.problem_solving = ProblemSolvingService(store, self.advanced.learning)\n"
        "        self.factory_recovery = FactoryRecoveryCoordinator(store)\n"
        "        self.release_refresh = ReleaseRefreshCoordinator(store)\n"
    )
    if assignments not in text:
        if marker not in text:
            raise RuntimeError("core governance assignment marker missing")
        text = text.replace(marker, marker + assignments, 1)
    path.write_text(text, encoding="utf-8")


def update_acceptance_matrix() -> None:
    path = RUNTIME / "acceptance-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["minimum_behavioral_cases"] = max(88, int(matrix["minimum_behavioral_cases"]))
    matrix["domains"]["self_directed_problem_solving"] = {
        "required": [
            "test_problem_solving.py::test_selects_maximal_nonconflicting_strategy_set_by_attributed_selector",
            "test_problem_solving.py::test_materially_identical_failed_strategy_cannot_be_reproposed_without_new_evidence",
            "test_problem_solving.py::test_failed_attempt_escalates_causal_level_and_changes_required_strategy_type",
            "test_problem_solving.py::test_real_discriminating_experiment_changes_available_evidence",
            "test_problem_solving.py::test_unexpected_success_becomes_bounded_candidate_not_global_policy",
            "test_problem_solving.py::test_cycle_resolves_only_after_effective_outcome_verification"
        ]
    }
    matrix["domains"]["closed_loop_factory_recovery"] = {
        "required": [
            "test_recovery_coordinator.py::test_factory_repair_closes_loop_and_wakes_target_once",
            "test_recovery_coordinator.py::test_release_refresh_waits_for_safe_boundary_and_is_idempotent"
        ]
    }
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_acceptance_domain_test() -> None:
    path = TESTS / "test_acceptance_matrix.py"
    text = path.read_text(encoding="utf-8")
    marker = '        "governance_effect_reconciliation",\n'
    additions = (
        '        "self_directed_problem_solving",\n'
        '        "closed_loop_factory_recovery",\n'
    )
    if additions not in text:
        if marker not in text:
            raise RuntimeError("acceptance governance domain marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def update_composition_test() -> None:
    path = TESTS / "test_v2_entrypoints.py"
    add_import(
        path,
        "from software_factory.migration import MigrationService\n",
        "from software_factory.problem_solving import ProblemSolvingService\n",
    )
    add_import(
        path,
        "from software_factory.reporting import ReportingService\n",
        "from software_factory.recovery import FactoryRecoveryCoordinator, ReleaseRefreshCoordinator\n",
    )
    text = path.read_text(encoding="utf-8")
    marker = "    assert isinstance(core.governance, GovernanceService)\n"
    additions = (
        "    assert isinstance(core.problem_solving, ProblemSolvingService)\n"
        "    assert isinstance(core.factory_recovery, FactoryRecoveryCoordinator)\n"
        "    assert isinstance(core.release_refresh, ReleaseRefreshCoordinator)\n"
    )
    if additions not in text:
        if marker not in text:
            raise RuntimeError("composition governance marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def bump_versions() -> None:
    schema = SOURCE / "schema.py"
    text = schema.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(SCHEMA_VERSION|LATEST_SCHEMA_VERSION)\s*=\s*\d+\s*$",
        lambda match: f"{match.group(1)} = 16",
        text,
    )
    schema.write_text(text, encoding="utf-8")
    pyproject = RUNTIME / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'(?m)^version = "2\.0\.0\.dev\d+"$', 'version = "2.0.0.dev8"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")
    init = SOURCE / "__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__ = "2\.0\.0\.dev\d+"', '__version__ = "2.0.0.dev8"', text, count=1)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    wire_problem_solving()
    route_failures_into_problem_cycles()
    route_successes_into_bounded_generalization()
    add_recurring_signal_discovery_and_cycle_status()
    wire_core_services()
    update_acceptance_matrix()
    update_acceptance_domain_test()
    update_composition_test()
    bump_versions()


if __name__ == "__main__":
    main()
