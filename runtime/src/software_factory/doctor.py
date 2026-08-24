from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import Store


class RuntimeDoctor:
    def __init__(self, store: Store, *, root: str | Path):
        self.store = store
        self.root = Path(root).resolve()

    def inspect(self) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        integrity = self.store.one("PRAGMA integrity_check")
        checks["sqlite_integrity"] = list(integrity.values())[0] if integrity else "missing"
        foreign_keys = self.store.all("PRAGMA foreign_key_check")
        checks["foreign_key_violations"] = foreign_keys
        migrations = self.store.all(
            "SELECT version,name,sha256 FROM schema_migrations ORDER BY version"
        )
        checks["schema_version"] = migrations[-1]["version"] if migrations else 0
        checks["migration_count"] = len(migrations)
        active_leases = self.store.all(
            """SELECT id,mission_id,owner_session_id,resource_key,expires_at
               FROM leases WHERE status='active' ORDER BY expires_at"""
        )
        checks["active_leases"] = active_leases
        orphan_assignments = self.store.all(
            """SELECT wa.id,wa.work_item_id,wa.agent_session_id
               FROM work_assignments wa
               LEFT JOIN work_items w ON w.id=wa.work_item_id
               LEFT JOIN agent_sessions a ON a.id=wa.agent_session_id
               WHERE w.id IS NULL OR a.id IS NULL"""
        )
        checks["orphan_assignments"] = orphan_assignments
        orphan_executions = self.store.all(
            """SELECT e.id,e.work_item_id,e.agent_session_id
               FROM executions e
               LEFT JOIN work_items w ON w.id=e.work_item_id
               LEFT JOIN agent_sessions a ON a.id=e.agent_session_id
               WHERE w.id IS NULL OR (e.agent_session_id IS NOT NULL AND a.id IS NULL)"""
        )
        checks["orphan_executions"] = orphan_executions
        unresolved_commands = self.store.all(
            """SELECT id,command_type,target_type,target_id,status,started_at
               FROM commands WHERE status IN ('claimed','running') ORDER BY started_at"""
        )
        checks["unresolved_commands"] = unresolved_commands
        active_incidents = self.store.all(
            """SELECT id,mission_id,severity,status,layer,updated_at
               FROM incidents
               WHERE status IN ('open','contained','correcting','verifying')
               ORDER BY severity DESC,updated_at"""
        )
        checks["active_incidents"] = active_incidents
        active_releases = self.store.all(
            "SELECT id,source_revision,manifest_root,status FROM immutable_releases_v2 WHERE status='active'"
        )
        checks["active_release_count"] = len(active_releases)
        checks["active_releases"] = active_releases
        cutover_marker = self.root / ".software-factory-runtime.json"
        checks["cutover_marker"] = (
            json.loads(cutover_marker.read_text(encoding="utf-8"))
            if cutover_marker.is_file()
            else None
        )
        checks["one_writer"] = len(active_releases) <= 1
        checks["ok"] = (
            checks["sqlite_integrity"] == "ok"
            and not foreign_keys
            and not orphan_assignments
            and not orphan_executions
            and len(active_releases) <= 1
        )
        return checks

    def reconcile_stale_commands(self, *, stale_before: str) -> list[str]:
        rows = self.store.all(
            """SELECT id FROM commands
               WHERE status IN ('claimed','running') AND started_at<?""",
            (stale_before,),
        )
        reconciled: list[str] = []
        with self.store.transaction() as db:
            for row in rows:
                db.execute(
                    """UPDATE commands SET status='failed',error_json=?,completed_at=?,updated_at=?
                       WHERE id=? AND status IN ('claimed','running')""",
                    (
                        json.dumps(
                            {
                                "kind": "stale_command_reconciled",
                                "retriable": True,
                                "stale_before": stale_before,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        stale_before,
                        stale_before,
                        row["id"],
                    ),
                )
                if db.execute("SELECT changes()").fetchone()[0] == 1:
                    reconciled.append(str(row["id"]))
        return reconciled
