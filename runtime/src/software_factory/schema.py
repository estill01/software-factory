from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files

from .errors import StoreError


@dataclass(frozen=True)
class Migration:
    version: int
    name: str


MIGRATIONS = (
    Migration(1, "0001_core.sql"),
    Migration(2, "0002_execution.sql"),
    Migration(3, "0003_learning.sql"),
    Migration(4, "0004_operations.sql"),
    Migration(5, "0005_foundation_hardening.sql"),
    Migration(6, "0006_execution_runtime.sql"),
    Migration(7, "0007_controller_runtime.sql"),
    Migration(8, "0008_supervision_runtime.sql"),
    Migration(9, "0009_learning_runtime.sql"),
    Migration(10, "0010_evolution_runtime.sql"),
    Migration(11, "0011_release_recovery_cleanup.sql"),
    Migration(12, "0012_operability_runtime.sql"),
    Migration(13, "0013_migration_cutover.sql"),
    Migration(14, "0014_governance_effects.sql"),
    Migration(15, "0015_problem_solving.sql"),
    Migration(16, "0016_problem_solving_hardening.sql"),
    Migration(17, "0017_reconciliation_runtime.sql"),
    Migration(18, "0018_governed_release.sql"),
    Migration(19, "0019_operational_reconciliation.sql"),
    Migration(20, "0020_acceptance_fencing.sql"),
    Migration(21, "0021_engine_host_contract.sql"),
    Migration(22, "0022_acceptance_lifecycle.sql"),
    Migration(23, "0023_librsi_integration.sql"),
    Migration(24, "0024_delivery_reconciliation.sql"),
    Migration(25, "0025_publication_validation_intent.sql"),
    Migration(26, "0026_librsi_shadow_retirement.sql"),
)
SCHEMA_VERSION = MIGRATIONS[-1].version

_MIGRATION_NAME = re.compile(r"(?P<version>[0-9]{4})_[a-z0-9_]+\.sql")


def validate_migration_catalog() -> None:
    """Reject gaps, duplicate versions, and inert SQL migration files."""

    versions = [migration.version for migration in MIGRATIONS]
    if versions != list(range(1, SCHEMA_VERSION + 1)):
        raise StoreError("migration versions must be unique and contiguous from one")
    names = [migration.name for migration in MIGRATIONS]
    if len(names) != len(set(names)):
        raise StoreError("migration names must be unique")
    for migration in MIGRATIONS:
        match = _MIGRATION_NAME.fullmatch(migration.name)
        if match is None or int(match.group("version")) != migration.version:
            raise StoreError(f"migration filename/version mismatch: {migration.name}")
    resource = files("software_factory.migrations")
    discovered = sorted(child.name for child in resource.iterdir() if child.name.endswith(".sql"))
    if discovered != sorted(names):
        missing = sorted(set(names) - set(discovered))
        inert = sorted(set(discovered) - set(names))
        raise StoreError(f"migration catalog mismatch: missing={missing}, inert={inert}")


def migration_sql(migration: Migration) -> str:
    return files("software_factory.migrations").joinpath(migration.name).read_text(encoding="utf-8")
