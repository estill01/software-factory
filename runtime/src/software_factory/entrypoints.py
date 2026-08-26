from __future__ import annotations

from pathlib import Path
from typing import Any

from .bootstrap import open_runtime


def open_context(home: str | Path | None = None) -> Any:
    """Open the one installed runtime composition root."""

    resolved = Path(home).expanduser().resolve() if home is not None else None
    return open_runtime(resolved)


def context_store(context: Any) -> Any:
    store = getattr(context, "store", None) or getattr(context, "database", None)
    if store is None:
        raise RuntimeError("runtime context does not expose its authoritative store")
    return store


def context_core(context: Any) -> Any:
    core = getattr(context, "core", None) or getattr(context, "runtime", None)
    if core is None:
        raise RuntimeError("runtime context does not expose its core services")
    return core
