#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"
TESTS = ROOT / "runtime" / "tests"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def harden_problem_strategy_status_and_dependencies() -> None:
    path = SOURCE / "problem_solving.py"
    text = path.read_text(encoding="utf-8")
    old = '''    def _prerequisites_satisfied(
        self, candidate: Mapping[str, Any], selected_ids: set[str] | None = None
    ) -> bool:
        selected = selected_ids or set()
        for prerequisite_id in _loads(candidate["prerequisites_json"], []):
            if prerequisite_id in selected:
                continue
            prerequisite = self.store.one(
'''
    new = '''    def _prerequisites_satisfied(
        self, candidate: Mapping[str, Any]
    ) -> bool:
        for prerequisite_id in _loads(candidate["prerequisites_json"], []):
            prerequisite = self.store.one(
'''
    if new not in text:
        if old not in text:
            raise RuntimeError("problem prerequisite function marker missing")
        text = text.replace(old, new, 1)
    text = text.replace(
        "if not self._prerequisites_satisfied(candidate, chosen_ids):",
        "if not self._prerequisites_satisfied(candidate):",
    )
    old_update = '''            db.execute(
                """UPDATE strategy_candidates_v2 SET status=?,result_json=?,updated_at=?
                   WHERE id=?""",
                (disposition, _canonical(dict(result)), now, attempt["strategy_id"]),
            )
'''
    new_update = '''            candidate_status = (
                disposition if disposition in {"succeeded", "failed", "ineffective"} else "failed"
            )
            db.execute(
                """UPDATE strategy_candidates_v2 SET status=?,result_json=?,updated_at=?
                   WHERE id=?""",
                (candidate_status, _canonical(dict(result)), now, attempt["strategy_id"]),
            )
'''
    if "candidate_status = (" not in text:
        if old_update not in text:
            raise RuntimeError("problem candidate terminal update marker missing")
        text = text.replace(old_update, new_update, 1)
    path.write_text(text, encoding="utf-8")


def fix_recovery_placeholders() -> None:
    path = SOURCE / "operations.py"
    text = path.read_text(encoding="utf-8")
    old = '''        placeholders = ",".join("?" for _ in range(8))
        active_statuses = (
'''
    new = '''        active_statuses = (
'''
    if old in text:
        text = text.replace(old, new, 1)
    marker = '''            "resolved",
            "failed",
        )
        existing = self.store.one(
'''
    replacement = '''            "resolved",
            "failed",
        )
        placeholders = ",".join("?" for _ in active_statuses)
        existing = self.store.one(
'''
    if 'placeholders = ",".join("?" for _ in active_statuses)' not in text:
        if marker not in text:
            raise RuntimeError("recovery active-status marker missing")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def make_acceptance_decision_idempotent() -> None:
    path = SOURCE / "governance.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        contract = self.store.one(
            "SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,)
        )
        if contract["status"] != "active" or contract["target_revision"] != exact_revision:
            raise InvalidTransition("acceptance contract is stale")
'''
    replacement = '''        contract = self.store.one(
            "SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,)
        )
        existing = self.store.one(
            """SELECT * FROM acceptance_decisions_v2
               WHERE contract_id=? AND exact_revision=? AND decision='accepted'
               ORDER BY decided_at DESC LIMIT 1""",
            (contract_id, exact_revision),
            required=False,
        )
        if existing is not None and contract["status"] == "satisfied":
            return existing
        if contract["status"] != "active" or contract["target_revision"] != exact_revision:
            raise InvalidTransition("acceptance contract is stale")
'''
    if "existing is not None and contract[\"status\"] == \"satisfied\"" not in text:
        if marker not in text:
            raise RuntimeError("acceptance decision marker missing")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def harden_cutover_native_path_separation() -> None:
    path = SOURCE / "migration.py"
    text = path.read_text(encoding="utf-8")
    marker = '''            if not source.exists() or source == native or native in source.parents:
                continue
            destination = archive_root / relative
'''
    replacement = '''            if not source.exists():
                continue
            if source == root:
                raise ValueError("repository root cannot be a legacy cutover path")
            if source == native or source in native.parents or native in source.parents:
                raise ValueError("legacy cutover path overlaps the native runtime")
            destination = archive_root / relative
'''
    if "legacy cutover path overlaps the native runtime" not in text:
        if marker not in text:
            raise RuntimeError("cutover native separation marker missing")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def load_governance_schema_in_reporting_tests() -> None:
    path = TESTS / "test_reporting.py"
    text = path.read_text(encoding="utf-8")
    if '"0014_governance_effects.sql"' in text:
        return
    marker = '''        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0012_operability_runtime.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))
'''
    replacement = '''        migrations = (
            Path(__file__).parents[1] / "src" / "software_factory" / "migrations"
        )
        self.connection.executescript(
            """
            CREATE TABLE missions(id TEXT PRIMARY KEY);
            CREATE TABLE agent_sessions(id TEXT PRIMARY KEY);
            """
        )
        self.connection.executescript(
            (migrations / "0012_operability_runtime.sql").read_text(encoding="utf-8")
        )
        self.connection.executescript(
            (migrations / "0014_governance_effects.sql").read_text(encoding="utf-8")
        )
'''
    if marker not in text:
        raise RuntimeError("reporting test migration marker missing")
    path.write_text(text.replace(marker, replacement, 1), encoding="utf-8")


def strengthen_recovery_retry_test() -> None:
    path = TESTS / "test_recovery_coordinator.py"
    text = path.read_text(encoding="utf-8")
    marker = '''    assert result["wake_effect"]["status"] == "succeeded"
    assert len(wake_calls) == 1
'''
    addition = '''    assert result["wake_effect"]["status"] == "succeeded"
    assert len(wake_calls) == 1
    duplicate = coordinator.recover(
        target_mission_id="mission-1",
        defect_class="factory-controller",
        defect_evidence={"occurrence_id": "failure-1", "error": "dispatcher stopped"},
        target_state={"obligation": "open", "work": "stranded"},
        requested_range_root="range-1234567890abcdef",
        tracker_currentness_root="tracker-1234567890abcdef",
        safe_frontier=[{"work_id": "safe-work"}],
        release_root=tmp_path / "releases",
        repair=lambda _: (_ for _ in ()).throw(AssertionError("repair reran")),
        review=lambda _: (_ for _ in ()).throw(AssertionError("review reran")),
        wake_target=lambda payload: (
            wake_calls.append(dict(payload))
            or {"provider_reference": "target-thread-1", "sent": True}
        ),
        verify_target=lambda _: (_ for _ in ()).throw(AssertionError("verification reran")),
    )
    assert duplicate["verification"] == {"already_resolved": True}
    assert len(wake_calls) == 1
'''
    if "repair reran" not in text:
        if marker not in text:
            raise RuntimeError("recovery retry test marker missing")
        text = text.replace(marker, addition, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    harden_problem_strategy_status_and_dependencies()
    fix_recovery_placeholders()
    make_acceptance_decision_idempotent()
    harden_cutover_native_path_separation()
    load_governance_schema_in_reporting_tests()
    strengthen_recovery_retry_test()


if __name__ == "__main__":
    main()
