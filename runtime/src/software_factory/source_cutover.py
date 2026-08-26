from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from .repository_lock import repository_effect_lock

SKILL_NAMES = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
    "evolve-product-program",
    "clean-software-factory",
)

_FORBIDDEN_ROOT_REFERENCES = (
    "supervision_log.py",
    "skill_release.py",
    "state.jsonl",
    "events.jsonl",
    ".codex/software-factory",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _file_hash(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def _root_hash(manifest: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(manifest).encode("utf-8")).hexdigest()


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _wrapper(skill: str) -> str:
    descriptions = {
        "author-implementation-trackers": "Author or revise the canonical implementation program through the native SQL-backed Software Factory v2 runtime.",
        "implement-tracker-blocks": "Execute eligible implementation work through the native multi-agent Software Factory v2 runtime.",
        "supervise-tracker-runs": "Supervise live Software Factory v2 work, incidents, adaptation, reflection, and acceptance.",
        "evolve-product-program": "Evolve product and implementation programs through the native Software Factory v2 selection and experimentation runtime.",
        "clean-software-factory": "Reconcile repository state through the native no-loss Software Factory v2 cleanup runtime.",
    }
    return f"""---
name: {skill}
description: {descriptions[skill]}
---

# Native Software Factory v2 interface

This skill is a thin invocation and role contract. The installed SQL-backed v2
runtime is the only active control-plane owner. Do not write or reactivate files
under `legacy/v1`.

Resolve the governing mission and invoke:

```bash
sf-skill {skill} --mission <mission-id> --payload '<json-object>'
```

Treat the returned record as an observed runtime result, not as authority to
invent completion. Continue through the native runtime until obligations are
accepted, terminal verification passes, or a genuinely reserved external effect
is recorded with its exact blocker. Do not create a parallel file ledger, event
log, scheduler, acceptance owner, or release owner in this skill directory.
"""


class SourceCutoverService:
    """Move v1 skill owners to immutable legacy storage and install thin v2 roots."""

    def __init__(self, repository_root: str | Path):
        self.root = Path(repository_root).resolve()
        self.legacy_root = self.root / "legacy" / "v1"
        self.skills_legacy_root = self.legacy_root / "skills"
        self.marker = self.root / ".software-factory-source-cutover.json"

    def plan(self) -> dict[str, Any]:
        if not (self.root / "runtime" / "src" / "software_factory").is_dir():
            raise ValueError("native runtime source is missing")
        skills: list[dict[str, Any]] = []
        for name in SKILL_NAMES:
            source = self.root / name
            if source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
                raise RuntimeError(f"skill owner contains a symlink: {name}")
            manifest = _tree_manifest(source)
            skills.append(
                {
                    "name": name,
                    "source_exists": source.is_dir(),
                    "legacy_destination": f"legacy/v1/skills/{name}",
                    "manifest": manifest,
                    "source_root": _root_hash(manifest),
                }
            )
        material = {
            "schema_version": 1,
            "runtime": "runtime/src/software_factory",
            "skills": skills,
        }
        return material | {"plan_root": hashlib.sha256(_canonical(material).encode()).hexdigest()}

    def apply(self) -> dict[str, Any]:
        with repository_effect_lock(self.root, "source-cutover"):
            return self._apply_locked()

    def _apply_locked(self) -> dict[str, Any]:
        if self.marker.exists() or self.marker.is_symlink():
            marker = self._read_marker()
            self._validate_plan_material(marker)
            if marker.get("status") == "applied":
                self.verify()
                return marker
            if marker.get("status") != "applying":
                raise RuntimeError("source cutover is not apply-eligible")
            plan = {
                key: marker[key] for key in ("schema_version", "runtime", "skills", "plan_root")
            }
        else:
            plan = self.plan()
            marker = plan | {
                "status": "applying",
                "active_runtime": "runtime/src/software_factory",
                "legacy_runtime": "legacy/v1",
                "one_writer": True,
            }
            _write_atomic(self.marker, _canonical(marker) + "\n")
        self.skills_legacy_root.mkdir(parents=True, exist_ok=True)
        for skill in plan["skills"]:
            self._apply_skill(skill)
        readme = self.legacy_root / "README.md"
        _write_atomic(
            readme,
            "# Software Factory v1 retained source\n\n"
            "These bytes are retained for migration, regression, lineage, and rollback.\n"
            "They are not active runtime owners. Root skill entrypoints invoke v2.\n",
        )
        marker = plan | {
            "status": "applied",
            "active_runtime": "runtime/src/software_factory",
            "legacy_runtime": "legacy/v1",
            "one_writer": True,
        }
        _write_atomic(self.marker, _canonical(marker) + "\n")
        self.verify()
        return marker

    def _apply_skill(self, skill: dict[str, Any]) -> None:
        name = str(skill["name"])
        source = self.root / name
        destination = self.skills_legacy_root / name
        expected = str(skill["source_root"])
        source_exists = bool(skill["source_exists"])
        wrapper_matches = (
            source.is_dir()
            and not source.is_symlink()
            and (source / "SKILL.md").is_file()
            and not (source / "SKILL.md").is_symlink()
            and [path for path in source.rglob("*") if path != source / "SKILL.md"] == []
            and (source / "SKILL.md").read_text(encoding="utf-8") == _wrapper(name)
        )
        destination_matches = (
            destination.is_dir()
            and not destination.is_symlink()
            and not any(path.is_symlink() for path in destination.rglob("*"))
            and _root_hash(_tree_manifest(destination)) == expected
        )
        if source_exists:
            if not destination_matches:
                if destination.exists() or destination.is_symlink():
                    raise RuntimeError(f"legacy destination differs: {name}")
                if not source.is_dir() or source.is_symlink():
                    raise RuntimeError(f"skill source is missing or unsafe: {name}")
                if any(path.is_symlink() for path in source.rglob("*")):
                    raise RuntimeError(f"skill source is unsafe: {name}")
                if _root_hash(_tree_manifest(source)) != expected:
                    raise RuntimeError(f"skill source differs from frozen intent: {name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
            elif source.exists() and not wrapper_matches:
                raise RuntimeError(f"active skill differs during replay: {name}")
        elif destination.exists() or destination.is_symlink():
            raise RuntimeError(f"unexpected legacy destination exists: {name}")
        if not wrapper_matches:
            if source.exists() or source.is_symlink():
                raise RuntimeError(f"active skill is unsafe during replay: {name}")
            source.mkdir(parents=True)
            _write_atomic(source / "SKILL.md", _wrapper(name))

    def verify(self) -> dict[str, Any]:
        if not self.marker.is_file():
            raise RuntimeError("source cutover marker is missing")
        marker = self._read_marker()
        skills = self._validate_plan_material(marker)
        failures: list[str] = []
        if marker.get("status") != "applied":
            failures.append("source cutover status differs")
        for skill in skills:
            name = skill["name"]
            wrapper_root = self.root / name
            wrapper = wrapper_root / "SKILL.md"
            if wrapper_root.is_symlink() or not wrapper.is_file() or wrapper.is_symlink():
                failures.append(f"missing native wrapper: {name}")
                continue
            extra = [
                path.relative_to(wrapper_root).as_posix()
                for path in wrapper_root.rglob("*")
                if path != wrapper
            ]
            if extra:
                failures.append(f"native wrapper contains competing files: {name}: {extra}")
            content = wrapper.read_text(encoding="utf-8")
            if content != _wrapper(name):
                failures.append(f"native wrapper differs from its exact v2 contract: {name}")
            if any(reference in content for reference in _FORBIDDEN_ROOT_REFERENCES):
                failures.append(f"native wrapper references a legacy writer: {name}")
            destination = self.skills_legacy_root / name
            expected = skill["source_root"]
            if skill["source_exists"]:
                if destination.is_symlink() or any(
                    path.is_symlink() for path in destination.rglob("*")
                ):
                    failures.append(f"legacy source is unsafe: {name}")
                elif _root_hash(_tree_manifest(destination)) != expected:
                    failures.append(f"legacy source hash differs: {name}")
            if not skill["source_exists"] and destination.exists():
                failures.append(f"unexpected legacy source exists: {name}")
        if marker.get("active_runtime") != "runtime/src/software_factory":
            failures.append("active runtime marker differs")
        if marker.get("legacy_runtime") != "legacy/v1":
            failures.append("legacy runtime marker differs")
        if marker.get("one_writer") is not True:
            failures.append("one-writer marker is absent")
        if failures:
            raise RuntimeError("; ".join(failures))
        return {
            "status": "verified",
            "active_runtime": marker["active_runtime"],
            "legacy_runtime": marker["legacy_runtime"],
            "one_writer": True,
            "skill_count": len(skills),
        }

    def _read_marker(self) -> dict[str, Any]:
        if self.marker.is_symlink():
            raise RuntimeError("source cutover marker is unsafe")
        try:
            value = json.loads(self.marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("source cutover marker is unreadable") from exc
        if not isinstance(value, dict):
            raise RuntimeError("source cutover marker is invalid")
        return value

    def _validate_plan_material(self, marker: dict[str, Any]) -> list[dict[str, Any]]:
        skills = marker.get("skills")
        if marker.get("schema_version") != 1 or marker.get("runtime") != (
            "runtime/src/software_factory"
        ):
            raise RuntimeError("source cutover schema or runtime differs")
        if (
            not isinstance(skills, list)
            or any(not isinstance(item, dict) for item in skills)
            or [item.get("name") for item in skills] != list(SKILL_NAMES)
        ):
            raise RuntimeError("source cutover skill set differs")
        for name, skill in zip(SKILL_NAMES, skills, strict=True):
            manifest = skill.get("manifest")
            if (
                type(skill.get("source_exists")) is not bool
                or skill.get("legacy_destination") != f"legacy/v1/skills/{name}"
                or not isinstance(manifest, list)
                or any(
                    not isinstance(item, dict)
                    or set(item) != {"path", "sha256", "bytes"}
                    or not isinstance(item["path"], str)
                    or not isinstance(item["sha256"], str)
                    or not isinstance(item["bytes"], int)
                    for item in manifest
                )
                or skill.get("source_root") != _root_hash(manifest)
            ):
                raise RuntimeError(f"source cutover frozen skill material differs: {name}")
        material = {
            "schema_version": marker["schema_version"],
            "runtime": marker["runtime"],
            "skills": skills,
        }
        expected = hashlib.sha256(_canonical(material).encode()).hexdigest()
        if marker.get("plan_root") != expected:
            raise RuntimeError(
                "incompatible source cutover plan root differs from its frozen material"
            )
        return skills

    def rollback(self) -> dict[str, Any]:
        with repository_effect_lock(self.root, "source-cutover"):
            return self._rollback_locked()

    def _rollback_locked(self) -> dict[str, Any]:
        if not self.marker.exists() and not self.marker.is_symlink():
            return {"status": "not_applied"}
        marker = self._read_marker()
        self._validate_plan_material(marker)
        if marker.get("status") == "applied":
            self.verify()
            marker = marker | {"status": "rolling_back"}
            _write_atomic(self.marker, _canonical(marker) + "\n")
        elif marker.get("status") not in {"applying", "rolling_back"}:
            raise RuntimeError("source cutover is not rollback-eligible")
        for skill in reversed(marker["skills"]):
            name = str(skill["name"])
            wrapper_root = self.root / name
            legacy = self.skills_legacy_root / name
            if skill["source_exists"]:
                expected = str(skill["source_root"])
                if wrapper_root.is_dir() and _root_hash(_tree_manifest(wrapper_root)) == expected:
                    if legacy.exists() or legacy.is_symlink():
                        raise RuntimeError(f"rollback has two legacy copies: {name}")
                    continue
                if not legacy.is_dir() or legacy.is_symlink():
                    raise RuntimeError(
                        f"legacy source is missing or unsafe during rollback: {name}"
                    )
                if any(path.is_symlink() for path in legacy.rglob("*")):
                    raise RuntimeError(f"legacy source is unsafe during rollback: {name}")
                if _root_hash(_tree_manifest(legacy)) != expected:
                    raise RuntimeError(f"legacy source differs during rollback: {name}")
                if wrapper_root.exists() or wrapper_root.is_symlink():
                    expected_wrapper = wrapper_root / "SKILL.md"
                    if (
                        wrapper_root.is_symlink()
                        or not expected_wrapper.is_file()
                        or expected_wrapper.is_symlink()
                        or [path for path in wrapper_root.rglob("*") if path != expected_wrapper]
                        or expected_wrapper.read_text(encoding="utf-8") != _wrapper(name)
                    ):
                        raise RuntimeError(f"active wrapper differs during rollback: {name}")
                    shutil.rmtree(wrapper_root)
                legacy.replace(wrapper_root)
                if _root_hash(_tree_manifest(wrapper_root)) != expected:
                    raise RuntimeError(f"restored source hash differs: {name}")
            else:
                if legacy.exists() or legacy.is_symlink():
                    raise RuntimeError(f"unexpected legacy source during rollback: {name}")
                if wrapper_root.exists() or wrapper_root.is_symlink():
                    expected_wrapper = wrapper_root / "SKILL.md"
                    if (
                        wrapper_root.is_symlink()
                        or not expected_wrapper.is_file()
                        or expected_wrapper.is_symlink()
                        or [path for path in wrapper_root.rglob("*") if path != expected_wrapper]
                        or expected_wrapper.read_text(encoding="utf-8") != _wrapper(name)
                    ):
                        raise RuntimeError(f"active wrapper differs during rollback: {name}")
                    shutil.rmtree(wrapper_root)
        self.marker.unlink()
        return {"status": "rolled_back", "restored_skills": len(marker["skills"])}
