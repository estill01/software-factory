from __future__ import annotations

from pathlib import Path

from software_factory.advanced import AdvancedServices
from software_factory.core import CoreService
from software_factory.database import Database
from software_factory.evolution import EvolutionService
from software_factory.learning import LearningService
from software_factory.migration import MigrationService
from software_factory.operations import OperationsService
from software_factory.reporting import ReportingService
from software_factory.supervision import SupervisionService

EXPECTED_TABLES = {
    "incidents",
    "supervision_assignments",
    "supervision_checks",
    "strategy_outcomes",
    "adaptive_actions",
    "acceptance_runs",
    "acceptance_case_results",
    "observed_stream_events",
    "learned_signal_candidates",
    "signal_evaluations_v2",
    "active_signal_bundles",
    "reflections_v2",
    "hypotheses_v2",
    "experiments_v2",
    "evolution_checkpoints_v2",
    "program_change_candidates_v2",
    "selection_records_v2",
    "selector_policy_candidates_v2",
    "immutable_releases_v2",
    "factory_recovery_cases_v2",
    "repository_inventories_v2",
    "schedules_v2",
    "reports_v2",
    "notifications_v2",
    "migration_runs_v2",
    "parity_cases_v2",
    "cutover_effects_v2",
}

RETIRED_ALTERNATE_TABLES = {
    "supervision_monitors",
    "supervision_incidents",
    "supervision_actions",
    "retained_adaptive_cases",
}


def _mission(database: Database) -> None:
    now = "2026-01-01T00:00:00Z"
    with database.transaction() as db:
        db.execute(
            """INSERT INTO projects(id,name,created_at,updated_at)
               VALUES('project-1','project',?,?)""",
            (now, now),
        )
        db.execute(
            """INSERT INTO missions(
                   id,project_id,title,objective,status,autonomy_mode,created_at,updated_at
               ) VALUES(
                   'mission-1','project-1','ship','ship safely','active',
                   'reviewed_autonomous',?,?
               )""",
            (now, now),
        )


def test_real_database_discovers_only_the_active_migration_lineage(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    health = database.health()
    assert health["schema_version"] == 24
    tables = {
        row["name"]
        for row in database.all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    }
    assert tables >= EXPECTED_TABLES
    assert RETIRED_ALTERNATE_TABLES.isdisjoint(tables)
    assert database.one("PRAGMA integrity_check") == {"integrity_check": "ok"}
    assert database.one("PRAGMA foreign_key_check", required=False) is None


def test_advanced_services_and_core_share_one_authoritative_graph(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    advanced = AdvancedServices(database)
    assert isinstance(advanced.supervision, SupervisionService)
    assert isinstance(advanced.learning, LearningService)
    assert isinstance(advanced.evolution, EvolutionService)
    assert isinstance(advanced._operations, OperationsService)
    assert advanced.supervision.store is database
    assert advanced.learning.store is database
    assert advanced.learning.semantic.work_items is advanced.work_items
    assert advanced.adaptive.semantic is advanced.learning.semantic
    assert advanced.evolution.store is database
    assert advanced._operations.store is database
    assert ReportingService(database).store is database
    assert MigrationService(database).store is database

    core = CoreService(database)
    assert core.advanced.store is database
    assert core.advanced.work_items is core.work_items
    assert core.advanced.continuation is core.continuation
    assert core.advanced.supervision is core.supervision
    assert core.advanced.adaptive is core.adaptive
    assert core.advanced.learning is core.learning
    assert core.advanced.learning.semantic is core.semantic
    assert core.advanced.adaptive.semantic is core.semantic
    assert core.advanced.evolution is core.evolution
    assert core.advanced._operations is core._operations


def test_supervision_learning_and_evolution_share_canonical_observed_state(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    _mission(database)
    advanced = AdvancedServices(database)
    incident_id = advanced.supervision.open_incident(
        mission_id="mission-1",
        target_type="mission",
        target_id="mission-1",
        severity="high",
        layer="execution",
        mechanism="observed repeated failure",
        trigger={"source": "focused-proof"},
        effect={"progress": "stopped"},
        detection={"kind": "runtime-observation"},
        failure_fingerprint="failure-fingerprint",
        strategy_key="strategy-a",
    )
    event = advanced.learning.record_event(
        mission_id="mission-1",
        source_type="incident",
        source_id=incident_id,
        event_type="incident-opened",
        classification="failure",
        attributes={"severity": "high"},
        evidence_ids=[incident_id],
    )
    checkpoint = advanced.evolution.checkpoint(
        mission_id="mission-1",
        boundary_type="structural",
        source_type="incident",
        source_id=incident_id,
        state={"layer": "execution", "event_id": event["id"]},
        observations={"program_may_need_revision": True},
        evidence_ids=[event["id"]],
    )
    assert checkpoint["material"] == 1
    assert database.one("SELECT COUNT(*) AS count FROM incidents WHERE mission_id='mission-1'") == {
        "count": 1
    }
    assert database.one(
        "SELECT COUNT(*) AS count FROM observed_stream_events WHERE mission_id='mission-1'"
    ) == {"count": 1}
    assert database.one(
        "SELECT COUNT(*) AS count FROM evolution_checkpoints_v2 WHERE mission_id='mission-1'"
    ) == {"count": 1}
