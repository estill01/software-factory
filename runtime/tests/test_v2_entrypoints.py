from __future__ import annotations

import tomllib
from pathlib import Path

from software_factory.advanced import AdvancedServices
from software_factory.core import CoreService
from software_factory.database import Database
from software_factory.evolution import EvolutionService
from software_factory.migration import MigrationService
from software_factory.reporting import ReportingService
from software_factory.supervision import SupervisionService


def test_core_exposes_advanced_services_without_multiple_inheritance(tmp_path: Path) -> None:
    database = Database(tmp_path / "factory.sqlite3")
    database.initialize()
    core = CoreService(database)
    assert type(core).__bases__ == (object,)
    assert isinstance(core.advanced, AdvancedServices)
    assert isinstance(core.advanced.supervision, SupervisionService)
    assert isinstance(core.advanced.evolution, EvolutionService)
    assert isinstance(core.reporting, ReportingService)
    assert isinstance(core.migration, MigrationService)
    assert core.advanced.store is database
    assert core.reporting.store is database
    assert core.migration.store is database


def test_block2_entrypoints_preserve_effect_boundaries_and_add_service_host() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    scripts = pyproject["project"]["scripts"]
    assert scripts["software-factory"] == "software_factory.cli:main"
    assert scripts["software-factoryd"] == "software_factory.daemon:main"
    assert scripts["software-factory-api"] == "software_factory.api_main:main"
    assert scripts["sf-skill"] == "software_factory.skill_bridge:main"
