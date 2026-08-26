from __future__ import annotations

import ast
import json
from pathlib import Path


def collected_test_ids(test_root: Path) -> set[str]:
    identifiers: set[str] = set()
    for path in sorted(test_root.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                identifiers.add(f"{path.name}::{node.name}")
    return identifiers


def test_behavioral_acceptance_matrix_has_complete_executable_coverage() -> None:
    runtime = Path(__file__).parents[1]
    matrix = json.loads((runtime / "acceptance-matrix.json").read_text(encoding="utf-8"))
    identifiers = collected_test_ids(runtime / "tests")
    assert len(identifiers) >= matrix["minimum_behavioral_cases"]
    missing: list[str] = []
    for domain, specification in matrix["domains"].items():
        required = specification.get("required", [])
        assert required, f"acceptance domain has no executable anchors: {domain}"
        for identifier in required:
            if identifier in identifiers:
                continue
            module = identifier.split("::", 1)[0]
            if not any(candidate.startswith(f"{module}::") for candidate in identifiers):
                missing.append(identifier)
    assert not missing, f"acceptance anchors are missing: {missing}"


def test_acceptance_matrix_covers_every_required_capability_family() -> None:
    runtime = Path(__file__).parents[1]
    matrix = json.loads((runtime / "acceptance-matrix.json").read_text(encoding="utf-8"))
    required_domains = {
        "mission_continuation",
        "multi_agent_execution",
        "qa_acceptance",
        "supervision_adaptation",
        "signals_learning",
        "reflection_experiments",
        "program_evolution",
        "selection_quality_rsi",
        "release_refresh_rollback",
        "systemic_recovery",
        "cleanup_reconciliation",
        "reporting_notifications",
        "operator_api_ui",
        "migration_parity_cutover",
        "native_composition",
    }
    assert required_domains == set(matrix["domains"])
