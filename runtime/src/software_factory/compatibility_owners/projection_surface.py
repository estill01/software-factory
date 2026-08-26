"""Fail-closed projection surfaces for installed v1 compatibility modules."""

from __future__ import annotations

from collections.abc import Mapping
from types import CodeType, FunctionType
from typing import Any


def _code_global_names(code: CodeType) -> set[str]:
    names = set(code.co_names)
    for value in code.co_consts:
        if isinstance(value, CodeType):
            names.update(_code_global_names(value))
    return names


def retain_projection_functions(
    namespace: dict[str, Any],
    *,
    roots: set[str],
    reject: FunctionType,
    opaque_roots: set[str] | None = None,
) -> tuple[str, ...]:
    """Replace every module function outside the projection dependency closure.

    ``opaque_roots`` retain their function objects without traversing referenced
    globals.  This is used for argparse builders: they may mention retired
    handlers, but those handler globals must resolve to ``reject`` when the
    parser is constructed.
    """

    module_name = str(namespace["__name__"])
    functions = {
        name: value
        for name, value in namespace.items()
        if isinstance(value, FunctionType) and value.__module__ == module_name
    }
    missing = sorted(name for name in roots if name not in functions)
    if missing:
        raise RuntimeError("Compatibility projection roots are missing: " + ", ".join(missing))

    opaque = opaque_roots or set()
    retained_ids: set[int] = {id(reject)}
    pending = list(roots)
    while pending:
        name = pending.pop()
        function = functions[name]
        identity = id(function)
        if identity in retained_ids:
            continue
        retained_ids.add(identity)
        if name in opaque:
            continue
        for dependency in _code_global_names(function.__code__):
            candidate = functions.get(dependency)
            if candidate is not None and id(candidate) not in retained_ids:
                pending.append(dependency)

    for name, function in functions.items():
        if id(function) not in retained_ids:
            namespace[name] = reject

    return tuple(
        sorted(
            name
            for name, value in namespace.items()
            if isinstance(value, FunctionType)
            and value.__module__ == module_name
            and value is not reject
        )
    )


def projection_surface_is_closed(
    namespace: Mapping[str, Any],
    *,
    exposed: tuple[str, ...],
    reject: FunctionType,
) -> bool:
    """Return whether the recorded active projection surface still matches."""

    module_name = str(namespace["__name__"])
    active = tuple(
        sorted(
            name
            for name, value in namespace.items()
            if isinstance(value, FunctionType)
            and value.__module__ == module_name
            and value is not reject
        )
    )
    return active == exposed
