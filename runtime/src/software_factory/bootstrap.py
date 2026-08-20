from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import RuntimePaths
from .core import CoreService
from .store import Store


@dataclass(frozen=True)
class RuntimeContext:
    """Constructed local runtime dependencies.

    This bootstrap object intentionally keeps filesystem and persistence wiring out of
    command handlers. Domain services remain testable with temporary stores.
    """

    paths: RuntimePaths
    store: Store
    core: CoreService


def open_runtime(home: str | Path | None = None) -> RuntimeContext:
    paths = RuntimePaths.from_root(home) if home is not None else RuntimePaths.from_environment()
    paths.ensure()
    store = Store(paths.database)
    core = CoreService(store)
    return RuntimeContext(paths=paths, store=store, core=core)
