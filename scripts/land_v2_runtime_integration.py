#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SOURCE = RUNTIME / "src" / "software_factory"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_pyproject() -> None:
    path = RUNTIME / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    replacements = {
        'software-factory = "software_factory.cli:main"': 'software-factory = "software_factory.v2_cli:main"',
        'software-factoryd = "software_factory.daemon:main"': 'software-factoryd = "software_factory.runtime_daemon:main"',
        'sf-skill = "software_factory.skill_bridge:main"': 'sf-skill = "software_factory.native_skills:main"',
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new, 1)
        elif new not in text:
            raise RuntimeError(f"entrypoint not found in {path}: {old}")
    if 'software-factory-api = "software_factory.api_main:main"' not in text:
        marker = 'sf-skill = "software_factory.native_skills:main"\n'
        if marker not in text:
            raise RuntimeError("sf-skill entrypoint marker is missing")
        text = text.replace(
            marker,
            marker + 'software-factory-api = "software_factory.api_main:main"\n',
            1,
        )
    for old, new in (
        ('version = "2.0.0.dev5"', 'version = "2.0.0.dev6"'),
        ('version = "2.0.0.dev4"', 'version = "2.0.0.dev6"'),
        ('version = "2.0.0.dev3"', 'version = "2.0.0.dev6"'),
    ):
        if old in text:
            text = text.replace(old, new, 1)
            break
    path.write_text(text, encoding="utf-8")


def update_version() -> None:
    path = SOURCE / "__init__.py"
    text = path.read_text(encoding="utf-8")
    for version in ("2.0.0.dev5", "2.0.0.dev4", "2.0.0.dev3", "2.0.0.dev2"):
        marker = f'__version__ = "{version}"'
        if marker in text:
            text = text.replace(marker, '__version__ = "2.0.0.dev6"', 1)
            break
    path.write_text(text, encoding="utf-8")


def update_core() -> None:
    path = SOURCE / "core.py"
    text = path.read_text(encoding="utf-8")
    imports = [
        "from .advanced import AdvancedServices\n",
        "from .migration import MigrationService\n",
        "from .reporting import ReportingService\n",
    ]
    insertion_point = "from .agents import AgentService\n"
    if insertion_point not in text:
        raise RuntimeError("core import insertion point is missing")
    for import_line in reversed(imports):
        if import_line not in text:
            text = text.replace(insertion_point, insertion_point + import_line, 1)
    assignment_marker = "        self.store = store\n"
    assignments = (
        "        self.advanced = AdvancedServices(store)\n"
        "        self.reporting = ReportingService(store)\n"
        "        self.migration = MigrationService(store)\n"
    )
    if assignments not in text:
        if assignment_marker not in text:
            raise RuntimeError("core store assignment is missing")
        text = text.replace(assignment_marker, assignment_marker + assignments, 1)
    path.write_text(text, encoding="utf-8")


def update_readme() -> None:
    path = RUNTIME / "README.md"
    text = path.read_text(encoding="utf-8")
    section = """

## Native v2 capability owners

The installed runtime composes one authoritative SQL store with explicit owners for
controller/provider execution, supervision and adaptive correction, signal learning,
reflection and experiments, recursive program evolution and selector-quality RSI,
immutable release and systemic recovery, no-loss cleanup, reporting and notifications,
factory-floor API/UI, and v1 migration/parity/cutover.

Installed entrypoints:

```text
software-factory       CLI, doctor, migration, factory floor, and existing commands
software-factoryd      persistent adaptive controller daemon
software-factory-api   loopback factory-floor API/UI
sf-skill               five native Software Factory skill interfaces
```
"""
    if "## Native v2 capability owners" not in text:
        path.write_text(text.rstrip() + section + "\n", encoding="utf-8")


def main() -> None:
    update_pyproject()
    update_version()
    update_core()
    update_readme()


if __name__ == "__main__":
    main()
