from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import tarfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import new_id, utc_now


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _tree_digest(path: Path) -> str:
    if path.is_file():
        return _file_digest(path)
    entries = []
    for child in sorted(path.rglob("*")):
        if child.is_file() and not child.is_symlink():
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "sha256": _file_digest(child),
                    "bytes": child.stat().st_size,
                }
            )
    return _digest(entries)


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _classify_path(relative: str) -> str:
    lower = relative.lower()
    name = Path(lower).name
    if "event" in lower and Path(lower).suffix in {".json", ".jsonl"}:
        return "event"
    if "tracker" in lower or name in {"implementation-plan.md", "implementation_tracker.md"}:
        return "tracker"
    if name.startswith("test_") or "/tests/" in f"/{lower}":
        return "test"
    if "fixture" in lower:
        return "fixture"
    if "failure" in lower or "incident" in lower:
        return "failure"
    if "success" in lower or "lesson" in lower:
        return "success"
    if "report" in lower:
        return "report"
    if name == "skill.md" or "/skills/" in f"/{lower}":
        return "skill"
    if "dashboard" in lower or "/web/" in f"/{lower}":
        return "dashboard"
    if "release" in lower:
        return "release"
    if Path(lower).suffix in {".json", ".jsonl", ".db", ".sqlite", ".sqlite3"}:
        return "state"
    return "other"


_DOMAIN_KEYWORDS = {
    "mission_continuation": ("mission", "continue", "terminal", "range", "obligation"),
    "multi_agent_execution": ("agent", "lease", "fence", "workspace", "dispatch", "callback"),
    "qa_acceptance": ("qa", "review", "candidate", "accept", "integration"),
    "supervision_adaptation": ("supervision", "incident", "contain", "strategy", "effectiveness"),
    "signals_learning": ("signal", "classif", "pattern", "failure_mode", "success_mode"),
    "reflection_experiments": ("reflection", "hypothesis", "experiment", "counterexample"),
    "program_evolution": ("evolution", "successor", "portfolio", "tracker_amend"),
    "selection_rsi": ("selection", "selector", "feature_choice", "design_choice"),
    "release_recovery": ("release", "rollback", "refresh", "recovery", "resume"),
    "cleanup_reconciliation": ("cleanup", "reconcile", "worktree", "branch", "preserve"),
    "reporting_ui": ("report", "notification", "dashboard", "api", "factory_floor"),
    "migration_parity": ("migration", "parity", "cutover", "legacy", "one_writer"),
}


class MigrationService:
    """No-loss v1 migration, executable parity, and one-writer cutover."""

    def __init__(self, store: Store):
        self.store = store

    def inventory_source(self, source_root: str | Path) -> dict[str, Any]:
        root = Path(source_root).resolve()
        if not root.is_dir():
            raise ValueError("migration source root does not exist")
        items: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if relative == ".git" or relative.startswith(".git/"):
                continue
            items.append(
                {
                    "relative_path": relative,
                    "item_kind": _classify_path(relative),
                    "sha256": _file_digest(path),
                    "bytes": path.stat().st_size,
                }
            )
        inventory_root = _digest(items)
        existing = self.store.one(
            """SELECT * FROM migration_runs_v2
               WHERE source_root=? AND source_inventory_root=?""",
            (str(root), inventory_root),
            required=False,
        )
        if existing is not None:
            return existing
        migration_id = new_id("migration")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO migration_runs_v2(
                       id,source_root,source_inventory_root,status,current_step,created_at,updated_at
                   ) VALUES(?,?,?,'inventoried','inventory',?,?)""",
                (migration_id, str(root), inventory_root, now, now),
            )
            db.executemany(
                """INSERT INTO migration_items_v2(
                       id,migration_id,relative_path,item_kind,sha256,bytes,
                       historical_only,import_status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,1,'pending',?,?)""",
                [
                    (
                        new_id("migration-item"),
                        migration_id,
                        item["relative_path"],
                        item["item_kind"],
                        item["sha256"],
                        item["bytes"],
                        now,
                        now,
                    )
                    for item in items
                ],
            )
        return self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))

    def create_backup(
        self,
        migration_id: str,
        *,
        output_directory: str | Path,
    ) -> dict[str, Any]:
        migration = self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))
        if migration["status"] not in {"inventoried", "failed"}:
            raise InvalidTransition("migration is not awaiting backup")
        root = Path(migration["source_root"]).resolve()
        output = Path(output_directory).resolve()
        output.mkdir(parents=True, exist_ok=True)
        backup_path = output / f"{migration_id}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as archive:
            for item in self.store.all(
                "SELECT * FROM migration_items_v2 WHERE migration_id=? ORDER BY relative_path",
                (migration_id,),
            ):
                path = root / item["relative_path"]
                if path.is_file() and not path.is_symlink():
                    archive.add(path, arcname=item["relative_path"], recursive=False)
        with tarfile.open(backup_path, "r:gz") as archive:
            archived = sorted(member.name for member in archive.getmembers() if member.isfile())
        expected = [
            row["relative_path"]
            for row in self.store.all(
                "SELECT relative_path FROM migration_items_v2 WHERE migration_id=? ORDER BY relative_path",
                (migration_id,),
            )
        ]
        if archived != expected:
            backup_path.unlink(missing_ok=True)
            raise RuntimeError("migration backup did not preserve the complete inventory")
        backup_root = _file_digest(backup_path)
        with self.store.transaction() as db:
            db.execute(
                """UPDATE migration_runs_v2
                   SET backup_path=?,backup_root=?,status='backed_up',current_step='backup',updated_at=?
                   WHERE id=?""",
                (str(backup_path), backup_root, utc_now(), migration_id),
            )
        return self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))

    def import_historical(
        self,
        migration_id: str,
        *,
        target_mission_id: str | None = None,
    ) -> dict[str, Any]:
        migration = self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))
        if migration["status"] not in {"backed_up", "importing", "failed"}:
            raise InvalidTransition("migration requires a verified backup before import")
        root = Path(migration["source_root"])
        with self.store.transaction() as db:
            db.execute(
                """UPDATE migration_runs_v2
                   SET status='importing',current_step='historical_import',updated_at=? WHERE id=?""",
                (utc_now(), migration_id),
            )
        imported = 0
        preserved = 0
        for item in self.store.all(
            "SELECT * FROM migration_items_v2 WHERE migration_id=? ORDER BY relative_path",
            (migration_id,),
        ):
            path = root / item["relative_path"]
            native_reference: dict[str, Any] = {
                "source_sha256": item["sha256"],
                "historical_only": True,
            }
            status = "preserved_only"
            try:
                if item["item_kind"] == "event" and target_mission_id is not None:
                    records: list[Any] = []
                    if path.suffix == ".jsonl":
                        records = [
                            json.loads(line)
                            for line in path.read_text(encoding="utf-8").splitlines()
                            if line.strip()
                        ]
                    else:
                        value = json.loads(path.read_text(encoding="utf-8"))
                        records = value if isinstance(value, list) else [value]
                    event_ids: list[str] = []
                    for record in records:
                        if not isinstance(record, Mapping):
                            continue
                        event_id = new_id("historical-event")
                        with self.store.transaction() as db:
                            db.execute(
                                """INSERT INTO observed_stream_events(
                                       id,mission_id,source_type,source_id,event_type,
                                       classification,attributes_json,evidence_ids_json,
                                       occurred_at,ingested_at,historical_only
                                   ) VALUES(?,?,?,?,?,?,?,'[]',?,?,1)""",
                                (
                                    event_id,
                                    target_mission_id,
                                    "legacy",
                                    str(record.get("id", item["relative_path"])),
                                    str(
                                        record.get("event_type", record.get("kind", "legacy-event"))
                                    ),
                                    str(record.get("classification", "neutral"))
                                    if str(record.get("classification", "neutral"))
                                    in {
                                        "neutral",
                                        "progress",
                                        "failure",
                                        "success",
                                        "mixed",
                                        "opportunity",
                                    }
                                    else "neutral",
                                    _canonical(dict(record)),
                                    str(record.get("created_at", utc_now())),
                                    utc_now(),
                                ),
                            )
                        event_ids.append(event_id)
                    native_reference["observed_stream_event_ids"] = event_ids
                    status = "imported"
                elif item["item_kind"] in {
                    "tracker",
                    "test",
                    "fixture",
                    "failure",
                    "success",
                    "report",
                    "skill",
                    "dashboard",
                    "release",
                    "state",
                }:
                    native_reference["preserved_path"] = item["relative_path"]
                    status = "imported"
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                native_reference["import_error"] = str(exc)
                status = "failed"
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE migration_items_v2
                       SET import_status=?,native_reference_json=?,updated_at=? WHERE id=?""",
                    (status, _canonical(native_reference), utc_now(), item["id"]),
                )
            if status == "imported":
                imported += 1
            else:
                preserved += 1
        failures = self.store.one(
            """SELECT id FROM migration_items_v2
               WHERE migration_id=? AND import_status='failed' LIMIT 1""",
            (migration_id,),
            required=False,
        )
        final_status = "failed" if failures else "imported"
        with self.store.transaction() as db:
            db.execute(
                """UPDATE migration_runs_v2
                   SET status=?,current_step='historical_import',updated_at=? WHERE id=?""",
                (final_status, utc_now(), migration_id),
            )
        return {
            "migration_id": migration_id,
            "status": final_status,
            "imported": imported,
            "preserved_only": preserved,
        }

    def map_parity_cases(
        self,
        migration_id: str,
        *,
        explicit_mapping: Mapping[str, Sequence[str]] | None = None,
    ) -> list[dict[str, Any]]:
        migration = self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))
        if migration["status"] not in {"imported", "parity", "failed"}:
            raise InvalidTransition("migration has not completed historical import")
        root = Path(migration["source_root"])
        overrides = dict(explicit_mapping or {})
        created: list[dict[str, Any]] = []
        tests = self.store.all(
            """SELECT * FROM migration_items_v2
               WHERE migration_id=? AND item_kind='test' ORDER BY relative_path""",
            (migration_id,),
        )
        for item in tests:
            path = root / item["relative_path"]
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                case_names = [path.stem]
            else:
                case_names = [
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name.startswith("test")
                ] or [path.stem]
            for case_name in case_names:
                mapping_key = f"{item['relative_path']}::{case_name}"
                native_ids = list(overrides.get(mapping_key, ()))
                domain = ""
                normalized = mapping_key.lower()
                for candidate_domain, keywords in _DOMAIN_KEYWORDS.items():
                    if any(keyword in normalized for keyword in keywords):
                        domain = candidate_domain
                        break
                disposition = "equivalent" if native_ids else "unmapped"
                if not domain:
                    domain = "unclassified"
                case_id = new_id("parity-case")
                with self.store.transaction() as db:
                    db.execute(
                        """INSERT OR IGNORE INTO parity_cases_v2(
                               id,migration_id,legacy_path,legacy_case_key,capability_domain,
                               native_test_ids_json,disposition,rationale_json,
                               evidence_ids_json,created_at,updated_at
                           ) VALUES(?,?,?,?,?,?,?,?,'[]',?,?)""",
                        (
                            case_id,
                            migration_id,
                            item["relative_path"],
                            case_name,
                            domain,
                            _canonical(native_ids),
                            disposition,
                            _canonical(
                                {
                                    "mapping_source": "explicit"
                                    if native_ids
                                    else "keyword_domain_only",
                                    "legacy_sha256": item["sha256"],
                                }
                            ),
                            utc_now(),
                            utc_now(),
                        ),
                    )
                created.append(
                    self.store.one(
                        """SELECT * FROM parity_cases_v2
                           WHERE migration_id=? AND legacy_path=? AND legacy_case_key=?""",
                        (migration_id, item["relative_path"], case_name),
                    )
                )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE migration_runs_v2
                   SET status='parity',current_step='parity_mapping',updated_at=? WHERE id=?""",
                (utc_now(), migration_id),
            )
        return created

    def accept_parity_case(
        self,
        parity_case_id: str,
        *,
        disposition: Literal["equivalent", "stronger_replacement", "deferred", "rejected"],
        native_test_ids: Sequence[str],
        evidence_ids: Sequence[str],
        rationale: Mapping[str, Any],
    ) -> dict[str, Any]:
        if disposition in {"equivalent", "stronger_replacement"} and (
            not native_test_ids or not evidence_ids
        ):
            raise ValueError("accepted parity requires executable native tests and evidence")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE parity_cases_v2
                   SET native_test_ids_json=?,disposition=?,rationale_json=?,
                       evidence_ids_json=?,updated_at=? WHERE id=?""",
                (
                    _canonical(sorted(set(native_test_ids))),
                    disposition,
                    _canonical(dict(rationale)),
                    _canonical(sorted(set(evidence_ids))),
                    utc_now(),
                    parity_case_id,
                ),
            )
            if db.execute("SELECT changes()").fetchone()[0] != 1:
                raise StoreError("parity case not found")
        return self.store.one("SELECT * FROM parity_cases_v2 WHERE id=?", (parity_case_id,))

    def verify_parity(
        self,
        migration_id: str,
        *,
        repository_root: str | Path,
        test_command: Sequence[str],
    ) -> dict[str, Any]:
        unresolved = self.store.all(
            """SELECT * FROM parity_cases_v2
               WHERE migration_id=? AND disposition NOT IN ('equivalent','stronger_replacement')""",
            (migration_id,),
        )
        if unresolved:
            raise InvalidTransition(f"{len(unresolved)} legacy parity cases remain unresolved")
        process = subprocess.run(
            [str(part) for part in test_command],
            cwd=Path(repository_root).resolve(),
            capture_output=True,
            text=True,
            check=False,
        )
        evidence = {
            "command": list(test_command),
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "parity_case_count": len(
                self.store.all(
                    "SELECT id FROM parity_cases_v2 WHERE migration_id=?", (migration_id,)
                )
            ),
        }
        if process.returncode != 0:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE migration_runs_v2
                       SET status='failed',error_json=?,updated_at=? WHERE id=?""",
                    (_canonical(evidence), utc_now(), migration_id),
                )
            raise RuntimeError("native parity suite failed")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE migration_runs_v2
                   SET status='parity',current_step='parity_verified',error_json=NULL,updated_at=?
                   WHERE id=?""",
                (utc_now(), migration_id),
            )
        return evidence | {"evidence_root": _digest(evidence), "status": "passed"}

    def plan_cutover(
        self,
        migration_id: str,
        *,
        repository_root: str | Path,
        native_runtime_root: str,
        legacy_paths: Sequence[str],
        legacy_archive_root: str = "legacy/v1",
        active_writer_probe: Mapping[str, Any],
    ) -> dict[str, Any]:
        migration = self.store.one("SELECT * FROM migration_runs_v2 WHERE id=?", (migration_id,))
        if migration["status"] != "parity" or not migration["backup_root"]:
            raise InvalidTransition("cutover requires backup and accepted parity")
        if int(active_writer_probe.get("legacy_writers", -1)) != 0:
            raise InvalidTransition("legacy writers are still active")
        if int(active_writer_probe.get("native_writers", -1)) != 1:
            raise InvalidTransition("exactly one native writer must be established")
        root = Path(repository_root).resolve()
        native = (root / native_runtime_root).resolve()
        if not native.exists():
            raise ValueError("native runtime root is missing")
        archive_root = (root / legacy_archive_root).resolve()
        try:
            native.relative_to(root)
            archive_root.relative_to(root)
        except ValueError as exc:
            raise ValueError("cutover paths escape repository root") from exc
        moves: list[dict[str, Any]] = []
        for relative in legacy_paths:
            source = (root / relative).resolve()
            try:
                source.relative_to(root)
            except ValueError as exc:
                raise ValueError("legacy path escapes repository root") from exc
            if not source.exists() or source == native or native in source.parents:
                continue
            destination = archive_root / relative
            moves.append(
                {
                    "source": str(source.relative_to(root)),
                    "destination": str(destination.relative_to(root)),
                    "source_sha256": _tree_digest(source),
                }
            )
        cutover_id = new_id("cutover")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO cutover_effects_v2(
                       id,migration_id,repository_root,native_runtime_root,
                       legacy_archive_root,move_manifest_json,active_writer_probe_json,
                       one_writer_verified,status,updated_at
                   ) VALUES(?,?,?,?,?,?,?,1,'planned',?)""",
                (
                    cutover_id,
                    migration_id,
                    str(root),
                    native_runtime_root,
                    legacy_archive_root,
                    _canonical(moves),
                    _canonical(dict(active_writer_probe)),
                    now,
                ),
            )
            db.executemany(
                """INSERT INTO cutover_path_effects_v2(
                       id,cutover_id,source_path,destination_path,source_sha256,
                       effect_status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,'planned',?,?)""",
                [
                    (
                        new_id("cutover-path"),
                        cutover_id,
                        move["source"],
                        move["destination"],
                        move["source_sha256"],
                        now,
                        now,
                    )
                    for move in moves
                ],
            )
        return self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))

    def apply_cutover(self, cutover_id: str) -> dict[str, Any]:
        cutover = self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))
        if cutover["status"] not in {"planned", "failed", "rolled_back"}:
            raise InvalidTransition("cutover is not awaiting application")
        if not cutover["one_writer_verified"]:
            raise InvalidTransition("cutover lacks one-writer verification")
        root = Path(cutover["repository_root"])
        effects = self.store.all(
            "SELECT * FROM cutover_path_effects_v2 WHERE cutover_id=? ORDER BY source_path",
            (cutover_id,),
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE cutover_effects_v2
                   SET status='running',started_at=?,updated_at=? WHERE id=?""",
                (utc_now(), utc_now(), cutover_id),
            )
        try:
            for effect in effects:
                source = root / effect["source_path"]
                destination = root / effect["destination_path"]
                if destination.exists() and not source.exists():
                    if _tree_digest(destination) != effect["source_sha256"]:
                        raise RuntimeError("interrupted cutover destination differs")
                elif source.exists():
                    if _tree_digest(source) != effect["source_sha256"]:
                        raise InvalidTransition("legacy path changed after cutover planning")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        raise RuntimeError("cutover destination already exists")
                    source.replace(destination)
                else:
                    raise RuntimeError("cutover source and destination are both absent")
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE cutover_path_effects_v2
                           SET effect_status='moved',updated_at=? WHERE id=?""",
                        (utc_now(), effect["id"]),
                    )
            marker = root / ".software-factory-runtime.json"
            marker.write_text(
                _canonical(
                    {
                        "active_runtime": cutover["native_runtime_root"],
                        "legacy_archive": cutover["legacy_archive_root"],
                        "cutover_id": cutover_id,
                        "one_writer": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        except BaseException as exc:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE cutover_effects_v2 SET status='failed',updated_at=? WHERE id=?""",
                    (utc_now(), cutover_id),
                )
                db.execute(
                    """UPDATE migration_runs_v2
                       SET status='failed',error_json=?,updated_at=? WHERE id=?""",
                    (_canonical({"cutover_error": str(exc)}), utc_now(), cutover["migration_id"]),
                )
            raise
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE cutover_effects_v2
                   SET status='verified',completed_at=?,updated_at=? WHERE id=?""",
                (now, now, cutover_id),
            )
            db.execute(
                """UPDATE cutover_path_effects_v2
                   SET effect_status='verified',updated_at=? WHERE cutover_id=?""",
                (now, cutover_id),
            )
            db.execute(
                """UPDATE migration_runs_v2
                   SET status='cutover',current_step='one_writer_cutover',completed_at=?,updated_at=?
                   WHERE id=?""",
                (now, now, cutover["migration_id"]),
            )
        return self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))

    def rollback_cutover(self, cutover_id: str) -> dict[str, Any]:
        cutover = self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))
        if cutover["status"] not in {"verified", "applied", "failed"}:
            raise InvalidTransition("cutover is not rollback-eligible")
        root = Path(cutover["repository_root"])
        effects = list(
            reversed(
                self.store.all(
                    "SELECT * FROM cutover_path_effects_v2 WHERE cutover_id=? ORDER BY source_path",
                    (cutover_id,),
                )
            )
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE cutover_effects_v2
                   SET status='rolling_back',updated_at=? WHERE id=?""",
                (utc_now(), cutover_id),
            )
        for effect in effects:
            source = root / effect["source_path"]
            destination = root / effect["destination_path"]
            if source.exists():
                if _tree_digest(source) != effect["source_sha256"]:
                    raise RuntimeError("restored legacy source differs")
            elif destination.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                destination.replace(source)
            else:
                raise RuntimeError("rollback source and archive are both absent")
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE cutover_path_effects_v2
                       SET effect_status='restored',updated_at=? WHERE id=?""",
                    (utc_now(), effect["id"]),
                )
        (root / ".software-factory-runtime.json").unlink(missing_ok=True)
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE cutover_effects_v2
                   SET status='rolled_back',completed_at=?,updated_at=? WHERE id=?""",
                (now, now, cutover_id),
            )
            db.execute(
                """UPDATE migration_runs_v2
                   SET status='rolled_back',current_step='rollback',updated_at=? WHERE id=?""",
                (now, cutover["migration_id"]),
            )
        return self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))

    def recover_interrupted_cutover(self, cutover_id: str) -> dict[str, Any]:
        cutover = self.store.one("SELECT * FROM cutover_effects_v2 WHERE id=?", (cutover_id,))
        if cutover["status"] not in {"running", "failed"}:
            return cutover
        root = Path(cutover["repository_root"])
        effects = self.store.all(
            "SELECT * FROM cutover_path_effects_v2 WHERE cutover_id=?",
            (cutover_id,),
        )
        for effect in effects:
            source = root / effect["source_path"]
            destination = root / effect["destination_path"]
            if destination.exists() and _tree_digest(destination) == effect["source_sha256"]:
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE cutover_path_effects_v2
                           SET effect_status='moved',updated_at=? WHERE id=?""",
                        (utc_now(), effect["id"]),
                    )
            elif not source.exists():
                return self.rollback_cutover(cutover_id)
        with self.store.transaction() as db:
            db.execute(
                "UPDATE cutover_effects_v2 SET status='planned',updated_at=? WHERE id=?",
                (utc_now(), cutover_id),
            )
        return self.apply_cutover(cutover_id)
