from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from .config import RuntimePaths
from .core import CoreService
from .providers import CodexCLIProvider, ProviderRegistry
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
    providers = ProviderRegistry()
    codex_executable = os.environ.get("SOFTWARE_FACTORY_CODEX_EXECUTABLE", "codex")
    codex_args = shlex.split(
        os.environ.get(
            "SOFTWARE_FACTORY_CODEX_ARGS",
            "exec --json --full-auto",
        )
    )
    providers.register(
        "codex_cli",
        CodexCLIProvider(
            paths.providers / "codex-cli",
            executable=codex_executable,
            argument_prefix=tuple(codex_args),
        ),
    )
    core = CoreService(store, providers=providers, default_provider="codex_cli")
    return RuntimeContext(paths=paths, store=store, core=core)
