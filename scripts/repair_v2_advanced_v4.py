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


def broaden_effectiveness_assignment_to_governed_target() -> None:
    path = SOURCE / "supervision.py"
    old = '''        reviewer_assignment = self.store.one(
            """SELECT * FROM supervision_monitors
               WHERE mission_id=? AND target_type='incident' AND target_id=?
                 AND role='effectiveness_reviewer' AND agent_session_id=?
                 AND status='active'""",
            (incident["mission_id"], incident["id"], reviewer_session_id),
            required=False,
        )
'''
    new = '''        reviewer_assignment = self.store.one(
            """SELECT * FROM supervision_monitors
               WHERE mission_id=? AND role='effectiveness_reviewer'
                 AND agent_session_id=? AND status='active'
                 AND (
                    (target_type='incident' AND target_id=?)
                    OR (target_type=? AND target_id=?)
                 )""",
            (
                incident["mission_id"],
                reviewer_session_id,
                incident["id"],
                incident["target_type"],
                incident["target_id"],
            ),
            required=False,
        )
'''
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    replace_once(path, old, new)


def filter_schema_fixture_overrides() -> None:
    path = TESTS / "test_advanced_integration.py"
    old = '''        columns = database.all(f"PRAGMA table_info({table})")
        values: dict[str, object] = dict(overrides)
        for column in columns:
'''
    new = '''        columns = database.all(f"PRAGMA table_info({table})")
        available = {str(column["name"]) for column in columns}
        values: dict[str, object] = {
            key: value for key, value in overrides.items() if key in available
        }
        for column in columns:
'''
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    replace_once(path, old, new)


def main() -> None:
    broaden_effectiveness_assignment_to_governed_target()
    filter_schema_fixture_overrides()


if __name__ == "__main__":
    main()
