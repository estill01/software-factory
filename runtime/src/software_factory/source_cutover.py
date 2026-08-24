from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

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
        plan = self.plan()
        if self.marker.exists():
            current = json.loads(self.marker.read_text(encoding="utf-8"))
            if current.get("plan_root") == plan["plan_root"]:
                self.verify()
                return current
            raise RuntimeError("an incompatible source cutover marker already exists")
        self.skills_legacy_root.mkdir(parents=True, exist_ok=True)
        applied: list[str] = []
        try:
            for skill in plan["skills"]:
                name = skill["name"]
                source = self.root / name
                destination = self.skills_legacy_root / name
                if source.exists():
                    if source.is_symlink() or not source.is_dir():
                        raise RuntimeError(f"skill owner has unsafe file type: {name}")
                    if destination.exists():
                        if _root_hash(_tree_manifest(destination)) != skill["source_root"]:
                            raise RuntimeError(f"legacy destination differs: {name}")
                        shutil.rmtree(source)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        source.replace(destination)
                source.mkdir(parents=True, exist_ok=True)
                (source / "SKILL.md").write_text(_wrapper(name), encoding="utf-8")
                applied.append(name)
            readme = self.legacy_root / "README.md"
            readme.write_text(
                "# Software Factory v1 retained source\n\n"
                "These bytes are retained for migration, regression, lineage, and rollback.\n"
                "They are not active runtime owners. Root skill entrypoints invoke v2.\n",
                encoding="utf-8",
            )
            marker = plan | {
                "status": "applied",
                "active_runtime": "runtime/src/software_factory",
                "legacy_runtime": "legacy/v1",
                "one_writer": True,
            }
            self.marker.write_text(_canonical(marker) + "\n", encoding="utf-8")
            self.verify()
            return marker
        except BaseException:
            for name in reversed(applied):
                wrapper = self.root / name
                destination = self.skills_legacy_root / name
                shutil.rmtree(wrapper, ignore_errors=True)
                if destination.exists():
                    destination.replace(wrapper)
            self.marker.unlink(missing_ok=True)
            raise

    def verify(self) -> dict[str, Any]:
        if not self.marker.is_file():
            raise RuntimeError("source cutover marker is missing")
        marker = json.loads(self.marker.read_text(encoding="utf-8"))
        failures: list[str] = []
        for skill in marker["skills"]:
            name = skill["name"]
            wrapper_root = self.root / name
            wrapper = wrapper_root / "SKILL.md"
            if not wrapper.is_file():
                failures.append(f"missing native wrapper: {name}")
                continue
            extra = [
                path.relative_to(wrapper_root).as_posix()
                for path in wrapper_root.rglob("*")
                if path.is_file() and path != wrapper
            ]
            if extra:
                failures.append(f"native wrapper contains competing files: {name}: {extra}")
            content = wrapper.read_text(encoding="utf-8")
            if f"sf-skill {name}" not in content:
                failures.append(f"native wrapper does not invoke v2: {name}")
            if any(reference in content for reference in _FORBIDDEN_ROOT_REFERENCES):
                failures.append(f"native wrapper references a legacy writer: {name}")
            destination = self.skills_legacy_root / name
            expected = skill["source_root"]
            if skill["source_exists"] and _root_hash(_tree_manifest(destination)) != expected:
                failures.append(f"legacy source hash differs: {name}")
        if marker.get("active_runtime") != "runtime/src/software_factory":
            failures.append("active runtime marker differs")
        if marker.get("one_writer") is not True:
            failures.append("one-writer marker is absent")
        if failures:
            raise RuntimeError("; ".join(failures))
        return {
            "status": "verified",
            "active_runtime": marker["active_runtime"],
            "legacy_runtime": marker["legacy_runtime"],
            "one_writer": True,
            "skill_count": len(marker["skills"]),
        }

    def rollback(self) -> dict[str, Any]:
        if not self.marker.is_file():
            return {"status": "not_applied"}
        marker = json.loads(self.marker.read_text(encoding="utf-8"))
        for skill in reversed(marker["skills"]):
            name = skill["name"]
            wrapper_root = self.root / name
            legacy = self.skills_legacy_root / name
            shutil.rmtree(wrapper_root, ignore_errors=True)
            if skill["source_exists"]:
                if not legacy.exists():
                    raise RuntimeError(f"legacy source is missing during rollback: {name}")
                legacy.replace(wrapper_root)
                if _root_hash(_tree_manifest(wrapper_root)) != skill["source_root"]:
                    raise RuntimeError(f"restored source hash differs: {name}")
            else:
                legacy.unlink(missing_ok=True)
        self.marker.unlink()
        return {"status": "rolled_back", "restored_skills": len(marker["skills"])}
