from __future__ import annotations

import contextlib
import sqlite3
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Literal, overload

from .audit import AuditMixin
from .errors import StaleState, StoreError
from .schema import MIGRATIONS, SCHEMA_VERSION, migration_sql, validate_migration_catalog
from .util import digest_bytes, utc_now

_TRANSACTION_MODES = {"DEFERRED", "IMMEDIATE", "EXCLUSIVE"}


class _DatabaseStore:
    """SQLite persistence owner with transactional migrations and WAL semantics."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def initialize(self) -> None:
        validate_migration_catalog()
        db = self.connect()
        try:
            db.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations(
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )"""
            )
            applied_rows = [
                dict(row)
                for row in db.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
            ]
            applied_versions = [int(row["version"]) for row in applied_rows]
            expected_prefix = [
                migration.version for migration in MIGRATIONS[: len(applied_versions)]
            ]
            if applied_versions != expected_prefix:
                raise StoreError("applied migration history is unknown, duplicated, or gapped")
            applied = {int(row["version"]): row for row in applied_rows}
            for migration in MIGRATIONS:
                sql = migration_sql(migration)
                checksum = digest_bytes(sql.encode("utf-8"))
                previous = applied.get(migration.version)
                if previous is not None:
                    if previous["name"] != migration.name or previous["sha256"] != checksum:
                        raise StoreError(
                            f"migration {migration.version} checksum/name changed after application"
                        )
                    continue
                script = (
                    "BEGIN IMMEDIATE;\n"
                    + sql
                    + "\nINSERT INTO schema_migrations(version,name,sha256,applied_at) "
                    + f"VALUES({migration.version},'{migration.name}','{checksum}','{utc_now()}');\n"
                    + "COMMIT;"
                )
                try:
                    db.executescript(script)
                except Exception:
                    with contextlib.suppress(sqlite3.Error):
                        db.execute("ROLLBACK")
                    raise
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
        finally:
            db.close()

    @contextlib.contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        normalized_mode = mode.upper()
        if normalized_mode not in _TRANSACTION_MODES:
            raise ValueError(f"unsupported transaction mode: {mode}")
        current = getattr(self._local, "db", None)
        if current is not None:
            sequence = int(getattr(self._local, "savepoint_sequence", 0)) + 1
            self._local.savepoint_sequence = sequence
            savepoint = f"software_factory_nested_{sequence}"
            current.execute(f"SAVEPOINT {savepoint}")
            try:
                yield current
                current.execute(f"RELEASE SAVEPOINT {savepoint}")
            except Exception:
                with contextlib.suppress(sqlite3.Error):
                    current.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    current.execute(f"RELEASE SAVEPOINT {savepoint}")
                raise
            return
        db = self.connect()
        self._local.db = db
        self._local.savepoint_sequence = 0
        try:
            db.execute(f"BEGIN {normalized_mode}")
            yield db
            db.execute("COMMIT")
        except Exception:
            with contextlib.suppress(sqlite3.Error):
                db.execute("ROLLBACK")
            raise
        finally:
            self._local.db = None
            self._local.savepoint_sequence = 0
            db.close()

    @overload
    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        required: Literal[True] = True,
        db: sqlite3.Connection | None = None,
    ) -> dict[str, Any]: ...

    @overload
    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        required: Literal[False],
        db: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None: ...

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        required: bool = True,
        db: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        current = getattr(self._local, "db", None)
        owns = db is None and current is None
        connection = db or current or self.connect()
        try:
            row = connection.execute(sql, parameters).fetchone()
            if row is None:
                if required:
                    raise StoreError("required row was not found")
                return None
            return dict(row)
        finally:
            if owns:
                connection.close()

    def all(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        db: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        current = getattr(self._local, "db", None)
        owns = db is None and current is None
        connection = db or current or self.connect()
        try:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
        finally:
            if owns:
                connection.close()

    def scalar(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        db: sqlite3.Connection | None = None,
    ) -> Any:
        row = self.one(sql, parameters, db=db, required=False)
        return None if row is None else next(iter(row.values()))

    def check_version(
        self,
        db: sqlite3.Connection,
        *,
        table: str,
        row_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        allowed = {
            "repositories",
            "missions",
            "capabilities",
            "obligations",
            "programs",
            "work_items",
            "experiments",
            "incidents",
            "hypotheses",
            "signal_candidates",
            "recovery_cases",
            "cleanup_runs",
        }
        if table not in allowed:
            raise StoreError(f"versioned table is not allowlisted: {table}")
        row = db.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
        if row is None:
            raise StoreError(f"{table} row not found: {row_id}")
        value = dict(row)
        if value["state_version"] != expected_version:
            raise StaleState(
                f"{table}/{row_id} is version {value['state_version']}, "
                f"not expected {expected_version}"
            )
        return value

    def health(self) -> dict[str, Any]:
        db = self.connect()
        try:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            schema = int(
                db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            )
            event_chains = db.execute(
                "SELECT COUNT(DISTINCT COALESCE(mission_id,'__global__')) FROM events"
            ).fetchone()[0]
            orphaned = db.execute(
                """SELECT COUNT(*) FROM missions m
                   WHERE m.status='active'
                   AND EXISTS(
                       SELECT 1 FROM capabilities c
                       WHERE c.mission_id=m.id AND c.required=1
                         AND c.status<>'end_to_end_verified'
                   )
                   AND NOT EXISTS(
                       SELECT 1 FROM executions e
                       WHERE e.mission_id=m.id
                         AND e.status IN ('queued','dispatching','leased','running','verifying')
                   )
                   AND NOT EXISTS(
                       SELECT 1 FROM obligations o
                       WHERE o.mission_id=m.id AND o.status='blocked_reserved'
                   )"""
            ).fetchone()[0]
        finally:
            db.close()
        return {
            "ok": integrity == "ok" and schema == SCHEMA_VERSION and orphaned == 0,
            "integrity": integrity,
            "schema_version": schema,
            "event_chains": event_chains,
            "orphaned_active_missions": orphaned,
        }


class Database(AuditMixin, _DatabaseStore):
    """Canonical transactional SQL state and hash-chained audit owner."""


# Retained import compatibility without retaining a second persistence class.
DatabaseStore = Database
