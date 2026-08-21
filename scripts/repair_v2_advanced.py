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


def add_missing_subprocess_import() -> None:
    path = SOURCE / "migration.py"
    text = path.read_text(encoding="utf-8")
    if "import subprocess\n" not in text:
        marker = "import shutil\n"
        if marker not in text:
            raise RuntimeError("migration import insertion point is missing")
        path.write_text(text.replace(marker, marker + "import subprocess\n", 1), encoding="utf-8")


def harden_operator_idempotency() -> None:
    path = SOURCE / "reporting.py"
    old = '''        candidates = self.store.all(
            "SELECT * FROM operator_action_tokens_v2 WHERE status='active'"
        )
        token = next(
            (
                row
                for row in candidates
                if hmac.compare_digest(str(row["token_hash"]), token_hash)
            ),
            None,
        )
        if token is None:
            raise StoreError("operator token is invalid")
        if _parse_time(token["expires_at"]) <= dt.datetime.now(dt.UTC):
'''
    new = '''        candidates = self.store.all("SELECT * FROM operator_action_tokens_v2")
        token = next(
            (
                row
                for row in candidates
                if hmac.compare_digest(str(row["token_hash"]), token_hash)
            ),
            None,
        )
        if token is None:
            raise StoreError("operator token is invalid")
        request = {
            "token_id": token["id"],
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "payload": dict(payload or {}),
        }
        request_root = _digest(request)
        existing = self.store.one(
            """SELECT * FROM operator_decisions_v2
               WHERE token_id=? AND request_root=?""",
            (token["id"], request_root),
            required=False,
        )
        if existing is not None:
            return existing
        if token["status"] != "active":
            raise StoreError("operator token is invalid")
        if _parse_time(token["expires_at"]) <= dt.datetime.now(dt.UTC):
'''
    replace_once(path, old, new)
    duplicate = '''        request = {
            "token_id": token["id"],
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "payload": dict(payload or {}),
        }
        request_root = _digest(request)
        existing = self.store.one(
            """SELECT * FROM operator_decisions_v2
               WHERE token_id=? AND request_root=?""",
            (token["id"], request_root),
            required=False,
        )
        if existing is not None:
            return existing
'''
    text = path.read_text(encoding="utf-8")
    if text.count(duplicate) != 1:
        raise RuntimeError("expected one remaining duplicate operator request block")
    path.write_text(text.replace(duplicate, "", 1), encoding="utf-8")


def harden_execution_monitor_attribution() -> None:
    path = SOURCE / "advanced.py"
    old = '''        monitor = self.supervision.assign_monitor(
            mission_id=mission_id,
            target_type="execution",
            target_id=str(execution["id"]),
            role="watcher",
            agent_session_id=execution.get("agent_session_id"),
            policy={
'''
    new = '''        session_id = execution.get("agent_session_id")
        if session_id and self.store.one(
            "SELECT id FROM agent_sessions WHERE id=?", (session_id,), required=False
        ) is None:
            session_id = None
        monitor = self.supervision.assign_monitor(
            mission_id=mission_id,
            target_type="execution",
            target_id=str(execution["id"]),
            role="watcher",
            agent_session_id=session_id,
            policy={
'''
    replace_once(path, old, new)


def make_advanced_integration_schema_aware() -> None:
    path = TESTS / "test_advanced_integration.py"
    old = '''    now = "2026-01-01T00:00:00Z"
    with database.transaction() as db:
        db.execute(
            """INSERT INTO projects(id,name,root_path,created_at,updated_at)
               VALUES('project-1','project','/tmp/project',?,?)""",
            (now, now),
        )
        db.execute(
            """INSERT INTO missions(
                   id,project_id,goal,status,requested_range_json,created_at,updated_at
               ) VALUES('mission-1','project-1','ship','active','{}',?,?)""",
            (now, now),
        )
'''
    new = '''    now = "2026-01-01T00:00:00Z"

    def insert_required(table: str, overrides: dict[str, object]) -> None:
        columns = database.all(f"PRAGMA table_info({table})")
        values: dict[str, object] = dict(overrides)
        for column in columns:
            name = str(column["name"])
            if name in values or column["pk"] or not column["notnull"] or column["dflt_value"] is not None:
                continue
            declared = str(column["type"]).upper()
            if name.endswith("_json"):
                values[name] = "{}" if "range" in name or "spec" in name else "[]"
            elif name.endswith("_at"):
                values[name] = now
            elif "INT" in declared:
                values[name] = 0
            else:
                values[name] = name
        names = list(values)
        placeholders = ",".join("?" for _ in names)
        with database.transaction() as db:
            db.execute(
                f"INSERT INTO {table}({','.join(names)}) VALUES({placeholders})",
                tuple(values[name] for name in names),
            )

    insert_required(
        "projects",
        {"id": "project-1", "name": "project", "root_path": "/tmp/project", "created_at": now, "updated_at": now},
    )
    insert_required(
        "missions",
        {"id": "mission-1", "project_id": "project-1", "goal": "ship", "status": "active", "requested_range_json": "{}", "created_at": now, "updated_at": now},
    )
'''
    replace_once(path, old, new)


def strengthen_operator_idempotency_test() -> None:
    path = TESTS / "test_reporting.py"
    old = '''    duplicate = reporting.store.one(
        "SELECT * FROM operator_decisions_v2 WHERE id=?", (decision["id"],)
    )
    assert duplicate is not None
'''
    new = '''    duplicate = reporting.accept_operator_action(
        raw,
        action="approve_release",
        target_type="release",
        target_id="release-1",
        payload={"note": "reviewed"},
    )
    assert duplicate["id"] == decision["id"]
'''
    replace_once(path, old, new)


def main() -> None:
    add_missing_subprocess_import()
    harden_operator_idempotency()
    harden_execution_monitor_attribution()
    make_advanced_integration_schema_aware()
    strengthen_operator_idempotency_test()


if __name__ == "__main__":
    main()
