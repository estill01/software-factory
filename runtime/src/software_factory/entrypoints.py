from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from .bootstrap import open_runtime


def open_context(home: str | Path | None = None) -> Any:
    """Open the installed runtime across the retained bootstrap call shapes."""

    signature = inspect.signature(open_runtime)
    parameters = signature.parameters
    root = Path(home).expanduser().resolve() if home is not None else None
    if "root" in parameters:
        return open_runtime(root=root) if root is not None else open_runtime()
    if "home" in parameters:
        return open_runtime(home=root) if root is not None else open_runtime()
    if root is not None:
        return open_runtime(root)
    return open_runtime()


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
