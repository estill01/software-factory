from __future__ import annotations

from importlib.resources import files

SCHEMA_VERSION = 1
MIGRATIONS = (
    "0001_core.sql",
    "0002_execution.sql",
    "0003_learning.sql",
    "0004_operations.sql",
)


def ddl() -> str:
    root = files("software_factory.migrations")
    return "\n".join(root.joinpath(name).read_text(encoding="utf-8") for name in MIGRATIONS)


DDL = ddl()
