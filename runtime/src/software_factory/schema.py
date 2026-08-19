from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files


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
)
SCHEMA_VERSION = MIGRATIONS[-1].version


def migration_sql(migration: Migration) -> str:
    return files("software_factory.migrations").joinpath(migration.name).read_text(
        encoding="utf-8"
    )
