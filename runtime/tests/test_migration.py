from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from software_factory.database import Database
from software_factory.errors import InvalidTransition
from software_factory.learning import LearningService
from software_factory.migration import MigrationService


def services() -> tuple[MigrationService, LearningService]:
    temporary_directory = TemporaryDirectory()
    database = Database(Path(temporary_directory.name) / "factory.sqlite3")
    now = "2026-01-01T00:00:00Z"
    with database.transaction() as db:
        db.execute(
            """INSERT INTO missions(
                   id,title,objective,status,autonomy_mode,created_at,updated_at
               ) VALUES('mission-1','mission','migrate','active','full_autonomous',?,?)""",
            (now, now),
        )
    migration = MigrationService(database)
    learning = LearningService(database)
    migration._test_temporary_directory = temporary_directory  # type: ignore[attr-defined]
    learning._test_temporary_directory = temporary_directory  # type: ignore[attr-defined]
    return migration, learning


def make_source(root: Path) -> None:
    (root / "tests").mkdir(parents=True)
    (root / "state").mkdir()
    (root / "docs").mkdir()
    (root / "tests" / "test_supervision.py").write_text(
        "def test_incident_recovery():\n    assert True\n", encoding="utf-8"
    )
    (root / "state" / "events.jsonl").write_text(
        json.dumps(
            {
                "id": "legacy-event-1",
                "event_type": "legacy-failure",
                "classification": "failure",
                "created_at": "2026-01-01T00:00:00Z",
                "detail": "historical only",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "docs" / "tracker.md").write_text("# Tracker\n", encoding="utf-8")


def test_inventory_and_backup_preserve_exact_complete_source(tmp_path: Path) -> None:
    migration, _ = services()
    source = tmp_path / "v1"
    source.mkdir()
    make_source(source)
    run = migration.inventory_source(source)
    items = migration.store.all(
        "SELECT relative_path,sha256 FROM migration_items_v2 WHERE migration_id=? ORDER BY relative_path",
        (run["id"],),
    )
    assert [item["relative_path"] for item in items] == [
        "docs/tracker.md",
        "state/events.jsonl",
        "tests/test_supervision.py",
    ]
    backed_up = migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    assert backed_up["status"] == "backed_up"
    assert Path(backed_up["backup_path"]).is_file()
    assert backed_up["backup_root"]


def test_inventory_rejects_symlinked_source_bytes(tmp_path: Path) -> None:
    migration, _ = services()
    source = tmp_path / "v1"
    source.mkdir()
    make_source(source)
    (source / "linked-tracker").symlink_to(source / "docs" / "tracker.md")
    with pytest.raises(ValueError, match="symlink"):
        migration.inventory_source(source)


def test_historical_event_import_cannot_trigger_live_signal_route(tmp_path: Path) -> None:
    migration, learning = services()
    source = tmp_path / "v1"
    source.mkdir()
    make_source(source)
    run = migration.inventory_source(source)
    migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    imported = migration.import_historical(run["id"], target_mission_id="mission-1")
    assert imported["status"] == "imported"
    event = migration.store.one(
        "SELECT * FROM observed_stream_events WHERE source_id='legacy-event-1'"
    )
    assert event is not None
    assert event["historical_only"] == 1
    assert learning.route_event(event["id"]) == []


def test_unmapped_legacy_test_fails_closed_until_explicitly_adjudicated(
    tmp_path: Path,
) -> None:
    migration, _ = services()
    source = tmp_path / "v1"
    source.mkdir()
    make_source(source)
    run = migration.inventory_source(source)
    migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    migration.import_historical(run["id"])
    cases = migration.map_parity_cases(run["id"])
    assert len(cases) == 1
    assert cases[0]["disposition"] == "unmapped"
    with pytest.raises(InvalidTransition, match="remain unresolved"):
        migration.verify_parity(
            run["id"],
            repository_root=tmp_path,
            test_command=[sys.executable, "-c", "raise SystemExit(0)"],
        )
    migration.accept_parity_case(
        cases[0]["id"],
        disposition="stronger_replacement",
        native_test_ids=["runtime/tests/test_supervision.py::test_effective_correction"],
        evidence_ids=["native-test-run"],
        rationale={"covers": "incident recovery plus later effectiveness"},
    )
    evidence = migration.verify_parity(
        run["id"],
        repository_root=tmp_path,
        test_command=[sys.executable, "-c", "raise SystemExit(0)"],
    )
    assert evidence["status"] == "passed"
    assert evidence["parity_case_count"] == 1


def prepared_cutover(tmp_path: Path) -> tuple[MigrationService, dict[str, Any], Path]:
    migration, _ = services()
    repository = tmp_path / "repository"
    repository.mkdir()
    source = repository / "v1-source"
    source.mkdir()
    make_source(source)
    native = repository / "runtime"
    native.mkdir()
    (native / "native.txt").write_text("native\n", encoding="utf-8")
    run = migration.inventory_source(source)
    migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    migration.import_historical(run["id"])
    cases = migration.map_parity_cases(run["id"])
    for case in cases:
        migration.accept_parity_case(
            case["id"],
            disposition="equivalent",
            native_test_ids=["runtime/tests/test_migration.py"],
            evidence_ids=["passing-test-run"],
            rationale={"equivalent": True},
        )
    migration.verify_parity(
        run["id"],
        repository_root=repository,
        test_command=[sys.executable, "-c", "raise SystemExit(0)"],
    )
    cutover = migration.plan_cutover(
        run["id"],
        repository_root=repository,
        native_runtime_root="runtime",
        legacy_paths=["v1-source"],
        legacy_archive_root="legacy/v1",
        active_writer_probe={"legacy_writers": 0, "native_writers": 1},
    )
    return migration, cutover, repository


def test_cutover_refuses_legacy_or_multiple_native_writers(tmp_path: Path) -> None:
    migration, _ = services()
    repository = tmp_path / "repository"
    repository.mkdir()
    source = repository / "v1-source"
    source.mkdir()
    make_source(source)
    (repository / "runtime").mkdir()
    run = migration.inventory_source(source)
    migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    migration.import_historical(run["id"])
    cases = migration.map_parity_cases(run["id"])
    for case in cases:
        migration.accept_parity_case(
            case["id"],
            disposition="equivalent",
            native_test_ids=["native-test"],
            evidence_ids=["test-run"],
            rationale={"accepted": True},
        )
    migration.verify_parity(
        run["id"],
        repository_root=repository,
        test_command=[sys.executable, "-c", "raise SystemExit(0)"],
    )
    with pytest.raises(InvalidTransition, match="legacy writers"):
        migration.plan_cutover(
            run["id"],
            repository_root=repository,
            native_runtime_root="runtime",
            legacy_paths=["v1-source"],
            active_writer_probe={"legacy_writers": 1, "native_writers": 1},
        )
    with pytest.raises(InvalidTransition, match="exactly one native writer"):
        migration.plan_cutover(
            run["id"],
            repository_root=repository,
            native_runtime_root="runtime",
            legacy_paths=["v1-source"],
            active_writer_probe={"legacy_writers": 0, "native_writers": 2},
        )


def test_actual_cutover_moves_legacy_owner_and_rolls_back_exact_bytes(
    tmp_path: Path,
) -> None:
    migration, cutover, repository = prepared_cutover(tmp_path)
    before = (repository / "v1-source" / "docs" / "tracker.md").read_bytes()
    applied = migration.apply_cutover(cutover["id"])
    assert applied["status"] == "verified"
    replayed = migration.apply_cutover(cutover["id"])
    assert replayed["status"] == "verified"
    assert not (repository / "v1-source").exists()
    assert (
        repository / "legacy" / "v1" / "v1-source" / "docs" / "tracker.md"
    ).read_bytes() == before
    marker = json.loads((repository / ".software-factory-runtime.json").read_text(encoding="utf-8"))
    assert marker["active_runtime"] == "runtime"
    assert marker["one_writer"] is True
    rolled_back = migration.rollback_cutover(cutover["id"])
    assert rolled_back["status"] == "rolled_back"
    assert migration.rollback_cutover(cutover["id"])["status"] == "rolled_back"
    assert (repository / "v1-source" / "docs" / "tracker.md").read_bytes() == before
    assert not (repository / ".software-factory-runtime.json").exists()
    reapplied = migration.apply_cutover(cutover["id"])
    assert reapplied["status"] == "verified"
    assert (
        repository / "legacy" / "v1" / "v1-source" / "docs" / "tracker.md"
    ).read_bytes() == before


def test_verified_cutover_replay_rejects_physical_or_marker_drift(tmp_path: Path) -> None:
    migration, cutover, repository = prepared_cutover(tmp_path)
    migration.apply_cutover(cutover["id"])
    archived = repository / "legacy" / "v1" / "v1-source" / "docs" / "tracker.md"
    archived.write_text("changed after verification\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="archive differs"):
        migration.apply_cutover(cutover["id"])

    archived.write_text("# Tracker\n", encoding="utf-8")
    marker = repository / ".software-factory-runtime.json"
    marker_value = json.loads(marker.read_text(encoding="utf-8"))
    marker_value["active_runtime"] = "other-runtime"
    marker.write_text(json.dumps(marker_value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="marker differs"):
        migration.apply_cutover(cutover["id"])


def test_verified_cutover_rollback_rejects_changed_archive_before_mutation(
    tmp_path: Path,
) -> None:
    migration, cutover, repository = prepared_cutover(tmp_path)
    migration.apply_cutover(cutover["id"])
    archived = repository / "legacy" / "v1" / "v1-source" / "docs" / "tracker.md"
    archived.write_text("changed after verification\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="archive differs"):
        migration.rollback_cutover(cutover["id"])
    assert not (repository / "v1-source").exists()


def test_interrupted_cutover_reconciles_already_moved_path(tmp_path: Path) -> None:
    migration, cutover, repository = prepared_cutover(tmp_path)
    source = repository / "v1-source"
    destination = repository / "legacy" / "v1" / "v1-source"
    destination.parent.mkdir(parents=True)
    source.replace(destination)
    with migration.store.transaction() as db:
        db.execute("UPDATE cutover_effects_v2 SET status='failed' WHERE id=?", (cutover["id"],))
    recovered = migration.recover_interrupted_cutover(cutover["id"])
    assert recovered["status"] == "verified"
    assert destination.is_dir()
    assert not source.exists()


def test_cutover_path_escape_is_rejected(tmp_path: Path) -> None:
    migration, _ = services()
    repository = tmp_path / "repository"
    repository.mkdir()
    source = repository / "v1-source"
    source.mkdir()
    make_source(source)
    (repository / "runtime").mkdir()
    run = migration.inventory_source(source)
    migration.create_backup(run["id"], output_directory=tmp_path / "backups")
    migration.import_historical(run["id"])
    with migration.store.transaction() as db:
        db.execute("UPDATE migration_runs_v2 SET status='parity' WHERE id=?", (run["id"],))
    with pytest.raises(ValueError, match="escape"):
        migration.plan_cutover(
            run["id"],
            repository_root=repository,
            native_runtime_root="runtime",
            legacy_paths=["../outside"],
            active_writer_probe={"legacy_writers": 0, "native_writers": 1},
        )
