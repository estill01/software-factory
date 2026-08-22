#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"
TESTS = ROOT / "runtime" / "tests"


def replace_function(path: Path, name: str, replacement: str, next_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_marker = f"    def {name}("
    end_marker = f"    def {next_name}("
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise RuntimeError(f"cannot locate {name}..{next_name} in {path}")
    path.write_text(text[:start] + replacement.rstrip() + "\n\n" + text[end:], encoding="utf-8")


def add_missing_subprocess_import() -> None:
    path = SOURCE / "migration.py"
    text = path.read_text(encoding="utf-8")
    if "import subprocess\n" not in text:
        marker = "import shutil\n"
        if marker not in text:
            raise RuntimeError("migration import insertion point is missing")
        path.write_text(text.replace(marker, marker + "import subprocess\n", 1), encoding="utf-8")


def replace_operator_action_function() -> None:
    path = SOURCE / "reporting.py"
    replacement = '''    def accept_operator_action(
        self,
        raw_token: str,
        *,
        action: str,
        target_type: str,
        target_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        candidates = self.store.all("SELECT * FROM operator_action_tokens_v2")
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
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE operator_action_tokens_v2 SET status='expired',updated_at=? WHERE id=?",
                    (utc_now(), token["id"]),
                )
            raise StoreError("operator token is expired")
        if action not in _loads(token["allowed_actions_json"], []):
            raise StoreError("operator token does not authorize this action")
        scope = _loads(token["scope_json"], {})
        if scope.get("target_type") not in (None, target_type):
            raise StoreError("operator action target type is outside token scope")
        allowed_ids = scope.get("target_ids")
        if isinstance(allowed_ids, list) and target_id not in allowed_ids:
            raise StoreError("operator action target is outside token scope")
        decision_id = new_id("operator-decision")
        now = utc_now()
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM operator_action_tokens_v2 WHERE id=?", (token["id"],)
            ).fetchone()
            if current is None or current["status"] != "active":
                raced = db.execute(
                    """SELECT * FROM operator_decisions_v2
                       WHERE token_id=? AND request_root=?""",
                    (token["id"], request_root),
                ).fetchone()
                if raced is not None:
                    return dict(raced)
                raise InvalidTransition("operator token was consumed concurrently")
            if int(current["use_count"]) >= int(current["max_uses"]):
                raise InvalidTransition("operator token has exhausted its uses")
            db.execute(
                """INSERT INTO operator_decisions_v2(
                       id,mission_id,token_id,action,target_type,target_id,payload_json,
                       request_root,status,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,'accepted',?)""",
                (
                    decision_id,
                    token["mission_id"],
                    token["id"],
                    action,
                    target_type,
                    target_id,
                    _canonical(dict(payload or {})),
                    request_root,
                    now,
                ),
            )
            use_count = int(current["use_count"]) + 1
            db.execute(
                """UPDATE operator_action_tokens_v2
                   SET use_count=?,status=?,updated_at=? WHERE id=?""",
                (
                    use_count,
                    "consumed" if use_count >= int(current["max_uses"]) else "active",
                    now,
                    token["id"],
                ),
            )
        return self.store.one(
            "SELECT * FROM operator_decisions_v2 WHERE id=?", (decision_id,)
        )'''
    replace_function(path, "accept_operator_action", replacement, "apply_operator_decision")


def harden_execution_monitor_attribution() -> None:
    path = SOURCE / "advanced.py"
    text = path.read_text(encoding="utf-8")
    if "session_id = execution.get(\"agent_session_id\")" in text:
        return
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
    if old not in text:
        raise RuntimeError("advanced monitor insertion point is missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def make_advanced_integration_schema_aware() -> None:
    path = TESTS / "test_advanced_integration.py"
    text = path.read_text(encoding="utf-8")
    if "def insert_required(table: str" in text:
        return
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
            if (
                name in values
                or column["pk"]
                or not column["notnull"]
                or column["dflt_value"] is not None
            ):
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
        {
            "id": "project-1",
            "name": "project",
            "root_path": "/tmp/project",
            "created_at": now,
            "updated_at": now,
        },
    )
    insert_required(
        "missions",
        {
            "id": "mission-1",
            "project_id": "project-1",
            "goal": "ship",
            "status": "active",
            "requested_range_json": "{}",
            "created_at": now,
            "updated_at": now,
        },
    )
'''
    if old not in text:
        raise RuntimeError("advanced integration fixture insertion point is missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def strengthen_operator_idempotency_test() -> None:
    path = TESTS / "test_reporting.py"
    text = path.read_text(encoding="utf-8")
    if "duplicate = reporting.accept_operator_action(" in text:
        return
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
    if old not in text:
        raise RuntimeError("operator idempotency test insertion point is missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    add_missing_subprocess_import()
    replace_operator_action_function()
    harden_execution_monitor_attribution()
    make_advanced_integration_schema_aware()
    strengthen_operator_idempotency_test()


if __name__ == "__main__":
    main()
