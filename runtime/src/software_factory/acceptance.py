from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Literal, Protocol, overload

from .errors import InvalidTransition, StoreError
from .util import new_id, utc_now


class AcceptanceStore(Protocol):
    def transaction(
        self, *, mode: str = "IMMEDIATE"
    ) -> AbstractContextManager[sqlite3.Connection]: ...

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

    def all(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        db: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]: ...


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AcceptanceService:
    """Execute and persist the capability acceptance matrix at an exact revision."""

    def __init__(self, store: AcceptanceStore):
        self.store = store

    @staticmethod
    def _load_matrix(path: str | Path) -> tuple[dict[str, Any], str]:
        matrix_path = Path(path)
        try:
            raw = matrix_path.read_bytes()
            value = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("acceptance matrix is unreadable") from exc
        domains = value.get("domains")
        if not isinstance(domains, Mapping) or not domains:
            raise ValueError("acceptance matrix has no domains")
        seen: set[str] = set()
        normalized: dict[str, Any] = {
            "schema_version": int(value.get("schema_version", 1)),
            "domains": {},
        }
        for domain, record in sorted(domains.items()):
            if not isinstance(domain, str) or not domain:
                raise ValueError("acceptance matrix domain is invalid")
            if not isinstance(record, Mapping):
                raise ValueError(f"acceptance domain is invalid: {domain}")
            required = record.get("required")
            if not isinstance(required, list) or not required:
                raise ValueError(f"acceptance domain has no required cases: {domain}")
            tests: list[str] = []
            for test_id in required:
                if not isinstance(test_id, str) or not test_id.strip():
                    raise ValueError(f"acceptance test id is invalid: {domain}")
                normalized_id = test_id.strip()
                if normalized_id in seen:
                    raise ValueError(f"acceptance test id is duplicated: {normalized_id}")
                seen.add(normalized_id)
                tests.append(normalized_id)
            normalized["domains"][domain] = {"required": tests}
        return normalized, hashlib.sha256(raw).hexdigest()

    def create_run(
        self,
        *,
        source_revision: str,
        matrix_path: str | Path,
        test_root: str | Path,
        mission_id: str | None = None,
        source_tree: str | None = None,
    ) -> dict[str, Any]:
        if not source_revision.strip():
            raise ValueError("source revision is required")
        matrix, matrix_sha256 = self._load_matrix(matrix_path)
        now = utc_now()
        run_id = new_id("acceptance-run")
        with self.store.transaction() as db:
            if mission_id is not None:
                mission = db.execute("SELECT id FROM missions WHERE id=?", (mission_id,)).fetchone()
                if mission is None:
                    raise StoreError("mission not found")
            db.execute(
                """INSERT INTO acceptance_runs(
                    id,mission_id,source_revision,source_tree,matrix_sha256,
                    matrix_json,test_root,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    mission_id,
                    source_revision,
                    source_tree,
                    matrix_sha256,
                    _canonical(matrix),
                    str(Path(test_root)),
                    "queued",
                    now,
                    now,
                ),
            )
            for domain, record in matrix["domains"].items():
                for test_id in record["required"]:
                    db.execute(
                        """INSERT INTO acceptance_case_results(
                            id,run_id,domain,test_id,status,result_json,created_at
                        ) VALUES(?,?,?,?,?,?,?)""",
                        (
                            new_id("acceptance-case"),
                            run_id,
                            domain,
                            test_id,
                            "pending",
                            "{}",
                            now,
                        ),
                    )
        result = self.store.one(
            "SELECT * FROM acceptance_runs WHERE id=?",
            (run_id,),
        )
        assert result is not None
        return result

    @staticmethod
    def _git_revision(repository_root: Path) -> tuple[str | None, str | None]:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return (
            head.stdout.strip() if head.returncode == 0 else None,
            tree.stdout.strip() if tree.returncode == 0 else None,
        )

    def execute(
        self,
        run_id: str,
        *,
        repository_root: str | Path,
        python_executable: str | Path = sys.executable,
        timeout_seconds: int = 1800,
        extra_environment: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise ValueError("repository root does not exist")
        run = self.store.one(
            "SELECT * FROM acceptance_runs WHERE id=?",
            (run_id,),
        )
        if run is None:
            raise StoreError("acceptance run not found")
        if run["status"] != "queued":
            raise InvalidTransition("acceptance run is not queued")

        observed_head, observed_tree = self._git_revision(root)
        if observed_head is not None and observed_head != run["source_revision"]:
            raise InvalidTransition("acceptance source revision is stale")
        if run["source_tree"] and observed_tree != run["source_tree"]:
            raise InvalidTransition("acceptance source tree is stale")

        started = utc_now()
        with self.store.transaction() as db:
            changed = db.execute(
                """UPDATE acceptance_runs
                   SET status='running',started_at=?,updated_at=?
                   WHERE id=? AND status='queued'""",
                (started, started, run_id),
            ).rowcount
            if changed != 1:
                raise InvalidTransition("acceptance run was claimed concurrently")

        rows = self.store.all(
            """SELECT * FROM acceptance_case_results
               WHERE run_id=? ORDER BY domain,test_id""",
            (run_id,),
        )
        environment = {
            **os.environ,
            **dict(extra_environment or {}),
        }
        src = root / "runtime" / "src"
        environment["PYTHONPATH"] = (
            str(src)
            if not environment.get("PYTHONPATH")
            else f"{src}{os.pathsep}{environment['PYTHONPATH']}"
        )

        failed = False
        completed_results: list[dict[str, Any]] = []
        for row in rows:
            command = [
                str(python_executable),
                "-m",
                "pytest",
                row["test_id"],
                "-q",
            ]
            start = time.monotonic()
            try:
                process = subprocess.run(
                    command,
                    cwd=root / run["test_root"],
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout_seconds,
                )
                status = "passed" if process.returncode == 0 else "failed"
                result = {
                    "command": command,
                    "exit_code": process.returncode,
                    "stdout_sha256": _sha256_text(process.stdout),
                    "stderr_sha256": _sha256_text(process.stderr),
                }
            except subprocess.TimeoutExpired as exc:
                status = "error"
                stdout = exc.stdout if isinstance(exc.stdout, str) else ""
                stderr = exc.stderr if isinstance(exc.stderr, str) else ""
                result = {
                    "command": command,
                    "error": "timeout",
                    "stdout_sha256": _sha256_text(stdout),
                    "stderr_sha256": _sha256_text(stderr),
                }
                process = None
            duration_ms = max(0, int((time.monotonic() - start) * 1000))
            failed = failed or status != "passed"
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE acceptance_case_results
                       SET status=?,exit_code=?,stdout_sha256=?,stderr_sha256=?,
                           duration_ms=?,result_json=?
                       WHERE id=? AND status='pending'""",
                    (
                        status,
                        process.returncode if process is not None else None,
                        result["stdout_sha256"],
                        result["stderr_sha256"],
                        duration_ms,
                        _canonical(result),
                        row["id"],
                    ),
                )
            completed_results.append(
                {
                    "domain": row["domain"],
                    "test_id": row["test_id"],
                    "status": status,
                    "duration_ms": duration_ms,
                    **result,
                }
            )

        final_status = "failed" if failed else "passed"
        completed = utc_now()
        evidence = {
            "run_id": run_id,
            "source_revision": run["source_revision"],
            "source_tree": run["source_tree"],
            "matrix_sha256": run["matrix_sha256"],
            "status": final_status,
            "cases": completed_results,
        }
        evidence_root = _digest(evidence)
        with self.store.transaction() as db:
            db.execute(
                """UPDATE acceptance_runs
                   SET status=?,completed_at=?,evidence_root=?,updated_at=?
                   WHERE id=? AND status='running'""",
                (final_status, completed, evidence_root, completed, run_id),
            )
        result = self.store.one(
            "SELECT * FROM acceptance_runs WHERE id=?",
            (run_id,),
        )
        assert result is not None
        return result | {"evidence": evidence}

    def require_passed_revision(self, source_revision: str) -> dict[str, Any]:
        result = self.store.one(
            """SELECT * FROM acceptance_runs
               WHERE source_revision=? AND status='passed'
               ORDER BY completed_at DESC,created_at DESC LIMIT 1""",
            (source_revision,),
            required=False,
        )
        if result is None or not result.get("evidence_root"):
            raise InvalidTransition("source revision lacks a passed executable acceptance run")
        return result

    def case_results(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.all(
            """SELECT * FROM acceptance_case_results
               WHERE run_id=? ORDER BY domain,test_id""",
            (run_id,),
        )
