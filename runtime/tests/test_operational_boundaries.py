from __future__ import annotations

import ast
import re
import sqlite3
from pathlib import Path

import pytest

from software_factory.database import Database, DatabaseStore
from software_factory.errors import StoreError
from software_factory.ownership import LIFECYCLE_OWNERS, owner_for_table
from software_factory.schema import MIGRATIONS, SCHEMA_VERSION, migration_sql
from software_factory.store import Store
from software_factory.util import digest_bytes

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "software_factory"
WRITE_PATTERN = re.compile(
    r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([a-z][a-z0-9_]*)",
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
    assert SCHEMA_VERSION == 20
    assert [migration.version for migration in MIGRATIONS] == list(range(1, 21))
    names = [migration.name for migration in MIGRATIONS]
    assert len(names) == len(set(names))
    discovered = sorted(path.name for path in (PACKAGE_ROOT / "migrations").glob("*.sql"))
    assert discovered == sorted(names)


def test_database_upgrades_an_applied_v9_prefix_without_alternate_writers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "factory.sqlite3"
    _applied_prefix(path, 9)
    database = Database(path)
    assert database.health()["schema_version"] == 20
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


def test_every_operational_table_has_one_primary_owner_and_only_declared_writers() -> None:
    tables = [table for owner in LIFECYCLE_OWNERS for table in owner.authoritative_tables]
    assert len(tables) == len(set(tables))
    assert len({owner.concern for owner in LIFECYCLE_OWNERS}) == len(LIFECYCLE_OWNERS)

    for source in PACKAGE_ROOT.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for table in WRITE_PATTERN.findall(text):
            if table not in tables:
                continue
            owner = owner_for_table(table)
            assert source.stem in owner.writer_modules, (
                f"{source.name} writes {table}, owned by {owner.primary_module}; "
                f"allowed writers are {owner.writer_modules}"
            )


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
    semantic_tables = {
        "active_signal_bundles",
        "evolution_checkpoints_v2",
        "experiments_v2",
        "hypotheses_v2",
        "learned_signal_candidates",
        "reflections_v2",
        "selection_records_v2",
    }
    operational_tables = {
        table for owner in LIFECYCLE_OWNERS for table in owner.authoritative_tables
    }
    for table in operational_tables:
        foreign_tables = {row["table"] for row in database.all(f"PRAGMA foreign_key_list({table})")}
        assert foreign_tables.isdisjoint(semantic_tables), (
            f"operational table {table} depends on semantic authority "
            f"{sorted(foreign_tables & semantic_tables)}"
        )
