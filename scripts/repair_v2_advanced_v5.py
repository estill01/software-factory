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


def wire_advanced_governance() -> None:
    path = SOURCE / "advanced.py"
    add_import(path, "from .evolution import EvolutionService\n", "from .governance import GovernanceService\n")
    text = path.read_text(encoding="utf-8")
    marker = "        self.evolution = EvolutionService(store)\n"
    assignment = "        self.governance = GovernanceService(store)\n"
    if assignment not in text:
        if marker not in text:
            raise RuntimeError("advanced governance assignment marker missing")
        text = text.replace(marker, marker + assignment, 1)
    path.write_text(text, encoding="utf-8")


def wire_core_governance() -> None:
    path = SOURCE / "core.py"
    add_import(path, "from .execution import ExecutionService\n", "from .governance import GovernanceService\n")
    text = path.read_text(encoding="utf-8")
    marker = "        self.advanced = AdvancedServices(store)\n"
    assignment = "        self.governance = GovernanceService(store)\n"
    if assignment not in text:
        if marker not in text:
            raise RuntimeError("core advanced assignment marker missing")
        text = text.replace(marker, marker + assignment, 1)
    path.write_text(text, encoding="utf-8")


def wire_report_delivery_propagation() -> None:
    path = SOURCE / "reporting.py"
    add_import(path, "from .errors import InvalidTransition, StoreError\n", "from .governance import GovernanceService\n")
    text = path.read_text(encoding="utf-8")
    init_old = '''    def __init__(self, store: Store):
        self.store = store
'''
    init_new = '''    def __init__(self, store: Store):
        self.store = store
        self.governance = GovernanceService(store)
'''
    if init_new not in text:
        if text.count(init_old) != 1:
            raise RuntimeError("reporting initializer marker missing")
        text = text.replace(init_old, init_new, 1)
    dispatch_marker = '''        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def record_readback(
'''
    dispatch_replacement = '''        self.governance.propagate_notification_status(notification_id)
        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def record_readback(
'''
    if dispatch_replacement not in text:
        if dispatch_marker not in text:
            raise RuntimeError("notification dispatch return marker missing")
        text = text.replace(dispatch_marker, dispatch_replacement, 1)
    readback_marker = '''        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def issue_operator_token(
'''
    readback_replacement = '''        self.governance.propagate_notification_status(notification_id)
        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def issue_operator_token(
'''
    if readback_replacement not in text:
        if readback_marker not in text:
            raise RuntimeError("notification readback return marker missing")
        text = text.replace(readback_marker, readback_replacement, 1)
    path.write_text(text, encoding="utf-8")


def update_acceptance_matrix() -> None:
    path = RUNTIME / "acceptance-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["minimum_behavioral_cases"] = max(78, int(matrix["minimum_behavioral_cases"]))
    matrix["domains"]["governance_effect_reconciliation"] = {
        "required": [
            "test_governance.py::test_caller_asserted_reviewer_role_without_grant_is_rejected",
            "test_governance.py::test_acceptance_contract_fails_closed_without_behavioral_probe",
            "test_governance.py::test_acceptance_requires_all_observed_probes_and_independent_review",
            "test_governance.py::test_changed_revision_invalidates_prior_review_and_acceptance",
            "test_governance.py::test_effect_idempotency_collision_and_stale_reconciliation"
        ]
    }
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_acceptance_domain_test() -> None:
    path = TESTS / "test_acceptance_matrix.py"
    text = path.read_text(encoding="utf-8")
    marker = '        "native_composition",\n'
    addition = '        "governance_effect_reconciliation",\n'
    if addition not in text:
        if marker not in text:
            raise RuntimeError("acceptance domain set marker missing")
        text = text.replace(marker, marker + addition, 1)
    path.write_text(text, encoding="utf-8")


def update_composition_test() -> None:
    path = TESTS / "test_v2_entrypoints.py"
    add_import(path, "from software_factory.evolution import EvolutionService\n", "from software_factory.governance import GovernanceService\n")
    text = path.read_text(encoding="utf-8")
    marker = "    assert isinstance(core.advanced.evolution, EvolutionService)\n"
    additions = (
        "    assert isinstance(core.advanced.governance, GovernanceService)\n"
        "    assert isinstance(core.governance, GovernanceService)\n"
    )
    if additions not in text:
        if marker not in text:
            raise RuntimeError("composition test marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def bump_schema_and_package_version() -> None:
    schema = SOURCE / "schema.py"
    text = schema.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(SCHEMA_VERSION|LATEST_SCHEMA_VERSION)\s*=\s*\d+\s*$",
        lambda match: f"{match.group(1)} = 14",
        text,
    )
    schema.write_text(text, encoding="utf-8")
    pyproject = RUNTIME / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'(?m)^version = "2\.0\.0\.dev\d+"$', 'version = "2.0.0.dev7"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")
    init = SOURCE / "__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__ = "2\.0\.0\.dev\d+"', '__version__ = "2.0.0.dev7"', text, count=1)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    wire_advanced_governance()
    wire_core_governance()
    wire_report_delivery_propagation()
    update_acceptance_matrix()
    update_acceptance_domain_test()
    update_composition_test()
    bump_schema_and_package_version()


if __name__ == "__main__":
    main()
