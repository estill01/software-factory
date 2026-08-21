#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"


def update_schema_version() -> None:
    path = SOURCE / "schema.py"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(SCHEMA_VERSION|LATEST_SCHEMA_VERSION)\s*=\s*\d+\s*$",
        lambda match: f"{match.group(1)} = 13",
        text,
    )
    path.write_text(text, encoding="utf-8")


def harden_signal_qa_inconclusive() -> None:
    path = SOURCE / "learning.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        column = {
            "historical_replay": "replay_status",
            "shadow": "shadow_status",
            "canary": "canary_status",
            "qa": "qa_status",
        }[phase]
'''
    replacement = marker + '''        stored_disposition = (
            "pending" if phase == "qa" and disposition == "inconclusive" else disposition
        )
'''
    if "stored_disposition = (" not in text:
        if marker not in text:
            raise RuntimeError("learning evaluation status marker is missing")
        text = text.replace(marker, replacement, 1)
        old = '''                (disposition, candidate_status, now, candidate_id),
'''
        new = '''                (stored_disposition, candidate_status, now, candidate_id),
'''
        if old not in text:
            raise RuntimeError("learning candidate status update is missing")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def reject_cutover_path_overlap() -> None:
    path = SOURCE / "migration.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        moves: list[dict[str, Any]] = []
        for relative in legacy_paths:
'''
    replacement = '''        normalized_paths = [Path(relative) for relative in legacy_paths]
        for index, left in enumerate(normalized_paths):
            for right in normalized_paths[index + 1 :]:
                if left == right or left in right.parents or right in left.parents:
                    raise ValueError("legacy cutover paths overlap")
        moves: list[dict[str, Any]] = []
        for relative in legacy_paths:
'''
    if "legacy cutover paths overlap" not in text:
        if marker not in text:
            raise RuntimeError("cutover path insertion point is missing")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def rewrite_doctor_for_schema_tolerance() -> None:
    path = SOURCE / "doctor.py"
    content = '''from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import Store


class RuntimeDoctor:
    def __init__(self, store: Store, *, root: str | Path):
        self.store = store
        self.root = Path(root).resolve()

    def _table_exists(self, name: str) -> bool:
        return (
            self.store.one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
                required=False,
            )
            is not None
        )

    def _rows(self, table: str, where: str = "", parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if not self._table_exists(table):
            return []
        return self.store.all(f"SELECT * FROM {table} {where}", parameters)

    def inspect(self) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        integrity = self.store.one("PRAGMA integrity_check")
        checks["sqlite_integrity"] = list(integrity.values())[0] if integrity else "missing"
        foreign_keys = self.store.all("PRAGMA foreign_key_check")
        checks["foreign_key_violations"] = foreign_keys
        migrations = self._rows("schema_migrations", "ORDER BY version")
        checks["schema_version"] = migrations[-1]["version"] if migrations else 0
        checks["migration_count"] = len(migrations)
        checks["active_leases"] = self._rows(
            "leases", "WHERE status='active' ORDER BY expires_at"
        )
        assignments = self._rows("work_assignments")
        work_ids = {str(row["id"]) for row in self._rows("work_items")}
        agent_ids = {str(row["id"]) for row in self._rows("agent_sessions")}
        checks["orphan_assignments"] = [
            row
            for row in assignments
            if str(row.get("work_item_id")) not in work_ids
            or str(row.get("agent_session_id")) not in agent_ids
        ]
        executions = self._rows("executions")
        checks["orphan_executions"] = [
            row
            for row in executions
            if str(row.get("work_item_id")) not in work_ids
            or (
                row.get("agent_session_id") is not None
                and str(row.get("agent_session_id")) not in agent_ids
            )
        ]
        unresolved = []
        for row in self._rows("commands"):
            if row.get("status") in {"claimed", "running"}:
                unresolved.append(row)
        checks["unresolved_commands"] = unresolved
        checks["active_incidents"] = [
            row
            for row in self._rows("supervision_incidents")
            if row.get("status") in {"open", "contained", "correcting", "verifying"}
        ]
        active_releases = [
            row for row in self._rows("immutable_releases_v2") if row.get("status") == "active"
        ]
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
            and not checks["orphan_assignments"]
            and not checks["orphan_executions"]
            and len(active_releases) <= 1
        )
        return checks

    def reconcile_stale_commands(self, *, stale_before: str) -> list[str]:
        if not self._table_exists("commands"):
            return []
        rows = [
            row
            for row in self._rows("commands")
            if row.get("status") in {"claimed", "running"}
            and str(row.get("started_at") or row.get("created_at") or "") < stale_before
        ]
        reconciled: list[str] = []
        columns = {str(row["name"]) for row in self.store.all("PRAGMA table_info(commands)")}
        assignments = ["status='failed'"]
        values: list[Any] = []
        if "error_json" in columns:
            assignments.append("error_json=?")
            values.append(
                json.dumps(
                    {
                        "kind": "stale_command_reconciled",
                        "retriable": True,
                        "stale_before": stale_before,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        for timestamp_column in ("completed_at", "updated_at"):
            if timestamp_column in columns:
                assignments.append(f"{timestamp_column}=?")
                values.append(stale_before)
        with self.store.transaction() as db:
            for row in rows:
                db.execute(
                    f"UPDATE commands SET {','.join(assignments)} WHERE id=? AND status IN ('claimed','running')",
                    (*values, row["id"]),
                )
                if db.execute("SELECT changes()").fetchone()[0] == 1:
                    reconciled.append(str(row["id"]))
        return reconciled
'''
    path.write_text(content, encoding="utf-8")


def main() -> None:
    update_schema_version()
    harden_signal_qa_inconclusive()
    reject_cutover_path_overlap()
    rewrite_doctor_for_schema_tolerance()


if __name__ == "__main__":
    main()
