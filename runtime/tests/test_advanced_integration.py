from __future__ import annotations

from pathlib import Path

from software_factory.advanced import AdvancedServices
from software_factory.database import Database
from software_factory.evolution import EvolutionService
from software_factory.learning import LearningService
from software_factory.migration import MigrationService
from software_factory.operations import OperationsService
from software_factory.reporting import ReportingService
from software_factory.supervision import IncidentEnvelope, SupervisionService


EXPECTED_TABLES = {
    "supervision_monitors",
    "supervision_incidents",
    "supervision_actions",
    "retained_adaptive_cases",
    "observed_stream_events",
    "learned_signal_candidates",
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


def test_real_database_discovers_all_advanced_migrations(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    database.initialize()
    health = database.health()
    assert health["schema_version"] >= 13
    tables = {
        row["name"]
        for row in database.all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    }
    assert EXPECTED_TABLES <= tables
    assert database.one("PRAGMA integrity_check") == {"integrity_check": "ok"}
    assert database.one("PRAGMA foreign_key_check", required=False) is None


def test_advanced_services_share_one_authoritative_store(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    database.initialize()
    advanced = AdvancedServices(database)
    assert isinstance(advanced.supervision, SupervisionService)
    assert isinstance(advanced.learning, LearningService)
    assert isinstance(advanced.evolution, EvolutionService)
    assert isinstance(advanced.operations, OperationsService)
    assert advanced.supervision.store is database
    assert advanced.learning.store is database
    assert advanced.evolution.store is database
    assert advanced.operations.store is database
    reporting = ReportingService(database)
    migration = MigrationService(database)
    assert reporting.store is database
    assert migration.store is database


def test_supervision_learning_and_evolution_share_observed_state(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    database.initialize()
    advanced = AdvancedServices(database)
    now = "2026-01-01T00:00:00Z"
    with database.transaction() as db:
        db.execute(
            """INSERT INTO projects(id,name,root_path,created_at,updated_at)
               VALUES('project-1','project','/tmp/project',?,?)""",
            (now, now),
        )
        db.execute(
            """INSERT INTO missions(
                   id,project_id,goal,status,requested_range_json,created_at,updated_at
               ) VALUES('mission-1','project-1','ship','active','{}',?,?)""",
            (now, now),
        )
    monitor = advanced.supervision.assign_monitor(
        mission_id="mission-1",
        target_type="mission",
        target_id="mission-1",
        role="watcher",
    )
    observation = advanced.supervision.observe(
        monitor["id"],
        state={"status": "blocked", "reason": "same strategy failed"},
        classification="failure",
        evidence_ids=["observed-state"],
    )
    incident = advanced.supervision.open_incident(
        mission_id="mission-1",
        target_type="mission",
        target_id="mission-1",
        observation_id=observation["id"],
        severity="high",
        envelope=IncidentEnvelope(
            mechanism={"strategy": "same"},
            trigger={"observation_id": observation["id"]},
            effect={"progress": "blocked"},
            detection={"source": "monitor"},
            containment={"safe_frontier": True},
            correction={"different_strategy": True},
            recurrence={"count": 2},
            human_scheduling_leakage={"detected": False},
        ),
    )
    event = advanced.learning.record_event(
        mission_id="mission-1",
        source_type="incident",
        source_id=incident["id"],
        event_type="incident-opened",
        classification="failure",
        attributes={"severity": "high"},
        evidence_ids=[observation["id"]],
    )
    checkpoint = advanced.evolution.checkpoint(
        mission_id="mission-1",
        boundary_type="structural",
        source_type="incident",
        source_id=incident["id"],
        state={"causal_level": incident["causal_level"], "event_id": event["id"]},
        observations={"program_may_need_revision": True},
        evidence_ids=[event["id"]],
    )
    assert checkpoint["material"] == 1
    assert database.one(
        "SELECT COUNT(*) AS count FROM supervision_incidents WHERE mission_id='mission-1'"
    ) == {"count": 1}
    assert database.one(
        "SELECT COUNT(*) AS count FROM observed_stream_events WHERE mission_id='mission-1'"
    ) == {"count": 1}
    assert database.one(
        "SELECT COUNT(*) AS count FROM evolution_checkpoints_v2 WHERE mission_id='mission-1'"
    ) == {"count": 1}
