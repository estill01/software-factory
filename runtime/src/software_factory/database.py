from __future__ import annotations

import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterator, Mapping

from .errors import StaleState, StoreError
from .schema import DDL, SCHEMA_VERSION

class DatabaseStore:

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
            db = self.connect()
            try:
                db.executescript(DDL)
                row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
                if row is None:
                    db.execute(
                        "INSERT INTO meta(key,value) VALUES('schema_version',?)",
                        (str(SCHEMA_VERSION),),
                    )
                elif int(row["value"]) != SCHEMA_VERSION:
                    raise StoreError(
                        f"unsupported schema {row['value']}; expected {SCHEMA_VERSION}"
                    )
            finally:
                db.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
            current = getattr(self._local, "db", None)
            if current is not None:
                yield current
                return
            db = self.connect()
            self._local.db = db
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.execute("COMMIT")
            except Exception:
                with contextlib.suppress(sqlite3.Error):
                    db.execute("ROLLBACK")
                raise
            finally:
                self._local.db = None
                db.close()

    def one(
            self,
            sql: str,
            parameters: tuple[Any, ...] | Mapping[str, Any] = (),
            *,
            required: bool = True,
            db: sqlite3.Connection | None = None,
        ) -> dict[str, Any] | None:
            owns = db is None
            db = db or self.connect()
            try:
                row = db.execute(sql, parameters).fetchone()
                if row is None:
                    if required:
                        raise StoreError("required row was not found")
                    return None
                return dict(row)
            finally:
                if owns:
                    db.close()

    def all(
            self,
            sql: str,
            parameters: tuple[Any, ...] | Mapping[str, Any] = (),
            *,
            db: sqlite3.Connection | None = None,
        ) -> list[dict[str, Any]]:
            owns = db is None
            db = db or self.connect()
            try:
                return [dict(row) for row in db.execute(sql, parameters).fetchall()]
            finally:
                if owns:
                    db.close()

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
                "repositories","missions","capabilities","obligations","programs",
                "work_items","experiments","incidents","hypotheses","signal_candidates",
                "recovery_cases","cleanup_runs",
            }
            if table not in allowed:
                raise StoreError(f"versioned table is not allowlisted: {table}")
            row = db.execute(
                f"SELECT * FROM {table} WHERE id=?", (row_id,)
            ).fetchone()
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
                    db.execute(
                        "SELECT value FROM meta WHERE key='schema_version'"
                    ).fetchone()[0]
                )
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
                "ok": integrity == "ok" and schema == SCHEMA_VERSION,
                "integrity": integrity,
                "schema_version": schema,
                "orphaned_active_missions": orphaned,
            }
