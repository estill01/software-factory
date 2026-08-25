from __future__ import annotations

import ast
import datetime as dt
import re
import sqlite3
from pathlib import Path

import pytest

from software_factory.database import Database, DatabaseStore
from software_factory.errors import StoreError
from software_factory.ownership import LIFECYCLE_OWNERS, owner_for_table
from software_factory.reporting import ReportingService
from software_factory.schema import MIGRATIONS, SCHEMA_VERSION, migration_sql
from software_factory.store import Store
from software_factory.util import digest_bytes

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "software_factory"
WRITE_PATTERN = re.compile(
    r"(?:INSERT(?:\s+OR\s+[A-Z]+)?\s+INTO|UPDATE|DELETE\s+FROM)\s+"
    r"([a-z][a-z0-9_]*)",
    re.IGNORECASE,
)


def _applied_prefix(path: Path, through: int) -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(
        """CREATE TABLE schema_migrations(
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )
    try:
        for migration in MIGRATIONS[:through]:
            sql = migration_sql(migration)
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations VALUES(?,?,?,'2026-01-01T00:00:00Z')",
                (migration.version, migration.name, digest_bytes(sql.encode("utf-8"))),
            )
    finally:
        connection.close()


def test_store_compatibility_names_are_the_same_persistence_owner() -> None:
    assert Store is Database
    assert DatabaseStore is Database


def test_migration_catalog_is_complete_contiguous_and_file_exact() -> None:
    assert SCHEMA_VERSION == 25
    assert [migration.version for migration in MIGRATIONS] == list(range(1, 26))
    names = [migration.name for migration in MIGRATIONS]
    assert len(names) == len(set(names))
    discovered = sorted(path.name for path in (PACKAGE_ROOT / "migrations").glob("*.sql"))
    assert discovered == sorted(names)


def test_publication_intent_migration_preserves_historical_validator_identity() -> None:
    database = sqlite3.connect(":memory:", isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute(
        """CREATE TABLE integration_candidates_v2(
               id TEXT PRIMARY KEY,
               status TEXT NOT NULL,
               validation_result_json TEXT
           )"""
    )
    database.executemany(
        "INSERT INTO integration_candidates_v2 VALUES(?,?,?)",
        [
            (
                "validated",
                "published",
                '{"phase":"post_publish","command":["python","-c","pass"]}',
            ),
            ("unvalidated", "published", '{"command":["python","-c","prepare"]}'),
            ("unfinished", "accepted", None),
        ],
    )
    database.executescript(migration_sql(MIGRATIONS[-1]))
    rows = {
        row["id"]: row["post_validation_command_json"]
        for row in database.execute(
            "SELECT id,post_validation_command_json FROM integration_candidates_v2"
        )
    }
    assert rows == {
        "validated": '["python","-c","pass"]',
        "unvalidated": "[]",
        "unfinished": None,
    }


def test_database_upgrades_an_applied_v9_prefix_without_alternate_writers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "factory.sqlite3"
    _applied_prefix(path, 9)
    database = Database(path)
    assert database.health()["schema_version"] == 25
    tables = {
        row["name"] for row in database.all("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "incidents" in tables
    assert "observed_stream_events" in tables
    assert "supervision_incidents" not in tables
    assert "retained_adaptive_cases" not in tables


def test_applied_migration_checksum_or_unknown_history_fails_closed(
    tmp_path: Path,
) -> None:
    checksum_path = tmp_path / "checksum.sqlite3"
    checksum_database = Database(checksum_path)
    with checksum_database.transaction() as db:
        db.execute("UPDATE schema_migrations SET sha256='changed' WHERE version=1")
    with pytest.raises(StoreError, match="checksum/name changed"):
        Database(checksum_path)

    unknown_path = tmp_path / "unknown.sqlite3"
    unknown_database = Database(unknown_path)
    with unknown_database.transaction() as db:
        db.execute(
            """INSERT INTO schema_migrations(version,name,sha256,applied_at)
               VALUES(99,'0099_unknown.sql','unknown','2026-01-01T00:00:00Z')"""
        )
    with pytest.raises(StoreError, match="unknown, duplicated, or gapped"):
        Database(unknown_path)


def test_nested_transactions_use_savepoints_and_preserve_atomicity(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    with database.transaction() as outer:
        outer.execute("INSERT INTO projects VALUES('outer','outer','{}','now','now')")
        with pytest.raises(RuntimeError, match="inner failure"), database.transaction() as inner:
            inner.execute("INSERT INTO projects VALUES('inner','inner','{}','now','now')")
            raise RuntimeError("inner failure")
        outer.execute("INSERT INTO projects VALUES('after','after','{}','now','now')")
    assert database.all("SELECT id FROM projects ORDER BY id") == [
        {"id": "after"},
        {"id": "outer"},
    ]

    with pytest.raises(RuntimeError, match="outer failure"), database.transaction() as outer:
        with database.transaction() as inner:
            inner.execute("INSERT INTO projects VALUES('nested','nested','{}','now','now')")
        raise RuntimeError("outer failure")
    assert database.one("SELECT id FROM projects WHERE id='nested'", required=False) is None


def test_operator_decision_atomically_couples_owner_effect_event_and_state(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    reporting = ReportingService(database)
    schedule = reporting.create_schedule(
        schedule_type="interval",
        specification={"seconds": 60},
        action={"kind": "tick"},
        next_run_at="2026-01-01T00:00:00Z",
    )
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat()

    raw, _ = reporting.issue_operator_token(
        allowed_actions=["pause_schedule"],
        scope={"target_type": "schedule", "target_ids": [schedule["id"]]},
        expires_at=expires_at,
    )
    failed_decision = reporting.accept_operator_action(
        raw,
        action="pause_schedule",
        target_type="schedule",
        target_id=schedule["id"],
    )

    def fail_after_effect(decision: dict[str, object]) -> dict[str, object]:
        reporting.set_schedule_status(
            schedule["id"],
            status="paused",
            operator_decision_id=str(decision["id"]),
        )
        raise RuntimeError("injected failure after owned effect")

    with pytest.raises(RuntimeError, match="injected failure"):
        reporting.apply_operator_decision(failed_decision["id"], handler=fail_after_effect)
    assert database.one("SELECT status FROM schedules_v2 WHERE id=?", (schedule["id"],)) == {
        "status": "active"
    }
    assert (
        database.scalar(
            "SELECT COUNT(*) FROM events WHERE subject_type='schedule' AND subject_id=?",
            (schedule["id"],),
        )
        == 0
    )
    assert database.one(
        "SELECT status FROM operator_decisions_v2 WHERE id=?", (failed_decision["id"],)
    ) == {"status": "failed"}

    raw, _ = reporting.issue_operator_token(
        allowed_actions=["pause_schedule"],
        scope={"target_type": "schedule", "target_ids": [schedule["id"]]},
        expires_at=expires_at,
    )
    decision = reporting.accept_operator_action(
        raw,
        action="pause_schedule",
        target_type="schedule",
        target_id=schedule["id"],
    )

    def apply_effect(record: dict[str, object]) -> dict[str, object]:
        reporting.set_schedule_status(
            schedule["id"],
            status="paused",
            operator_decision_id=str(record["id"]),
        )
        return {"paused": schedule["id"]}

    applied = reporting.apply_operator_decision(decision["id"], handler=apply_effect)
    assert applied["status"] == "applied"
    assert database.one("SELECT status FROM schedules_v2 WHERE id=?", (schedule["id"],)) == {
        "status": "paused"
    }
    assert (
        database.scalar(
            "SELECT COUNT(*) FROM events WHERE subject_type='schedule' AND subject_id=?",
            (schedule["id"],),
        )
        == 1
    )

    def must_not_repeat(_record: dict[str, object]) -> dict[str, object]:
        raise AssertionError("applied decision repeated its effect")

    duplicate = reporting.apply_operator_decision(decision["id"], handler=must_not_repeat)
    assert duplicate["status"] == "applied"


def test_every_operational_table_has_one_primary_owner_and_only_declared_writers() -> None:
    tables = [table for owner in LIFECYCLE_OWNERS for table in owner.authoritative_tables]
    assert len(tables) == len(set(tables))
    assert len({owner.concern for owner in LIFECYCLE_OWNERS}) == len(LIFECYCLE_OWNERS)

    runtime_writes: set[str] = set()
    for source in PACKAGE_ROOT.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        module = source.relative_to(PACKAGE_ROOT).with_suffix("").as_posix().replace("/", ".")
        if module.endswith(".__init__"):
            module = module.removesuffix(".__init__")
        for table in WRITE_PATTERN.findall(text):
            runtime_writes.add(table)
            owner = owner_for_table(table)
            assert module in owner.writer_modules, (
                f"{source.name} writes {table}, owned by {owner.primary_module}; "
                f"allowed writers are {owner.writer_modules}"
            )
    assert runtime_writes == set(tables)


def test_dependency_direction_rejects_persistence_to_service_and_service_to_host() -> None:
    persistence = {"audit", "database", "schema", "store"}
    support = {"audit", "database", "errors", "schema", "store", "util"}
    hosts = {"api", "api_main", "native_skills", "runtime_daemon", "v2_cli"}

    for source in PACKAGE_ROOT.glob("*.py"):
        imports: set[str] = set()
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                imports.add(node.module.split(".", 1)[0])
        if source.stem in persistence:
            assert imports <= support, f"{source.stem} reverses into {sorted(imports - support)}"
        if source.stem not in hosts:
            assert imports.isdisjoint(hosts), (
                f"{source.stem} imports host modules {sorted(imports & hosts)}"
            )


def test_semantic_records_cannot_be_operational_foreign_key_authority(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    semantic_tables = {"librsi_records"}
    operational_tables = {
        table
        for owner in LIFECYCLE_OWNERS
        if owner.authority_class == "operational"
        for table in owner.authoritative_tables
    }
    for table in operational_tables:
        foreign_tables = {row["table"] for row in database.all(f"PRAGMA foreign_key_list({table})")}
        assert foreign_tables.isdisjoint(semantic_tables), (
            f"operational table {table} depends on semantic authority "
            f"{sorted(foreign_tables & semantic_tables)}"
        )


def test_librsi_is_the_only_current_semantic_lifecycle_owner() -> None:
    semantic_owners = [owner for owner in LIFECYCLE_OWNERS if owner.authority_class == "semantic"]
    assert [(owner.concern, owner.primary_module) for owner in semantic_owners] == [
        ("librsi_semantic_cache", "integrations.librsi.service")
    ]
    package_text = "\n".join(
        source.read_text(encoding="utf-8") for source in PACKAGE_ROOT.rglob("*.py")
    )
    assert "INSERT INTO hypotheses_v2" not in package_text
    assert "INSERT INTO hypothesis_evidence_v2" not in package_text
    assert "INSERT INTO reflections_v2" not in package_text
    assert "INSERT INTO selection_outcomes_v2" not in package_text
    assert "UPDATE hypotheses_v2" not in package_text
