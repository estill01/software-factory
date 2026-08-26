from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from software_factory.source_cutover import SKILL_NAMES, SourceCutoverService


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def make_repository(root: Path, *, omit: str | None = None) -> dict[str, str]:
    (root / "runtime" / "src" / "software_factory").mkdir(parents=True)
    roots: dict[str, str] = {}
    for index, name in enumerate(SKILL_NAMES):
        if name == omit:
            continue
        directory = root / name
        (directory / "scripts").mkdir(parents=True)
        skill = directory / "SKILL.md"
        script = directory / "scripts" / "owner.py"
        skill.write_text(
            f"---\nname: {name}\n---\n\nRun scripts/owner.py for {name}.\n",
            encoding="utf-8",
        )
        script.write_text(f"OWNER = {index!r}\n", encoding="utf-8")
        roots[f"{name}/SKILL.md"] = digest(skill)
        roots[f"{name}/scripts/owner.py"] = digest(script)
    return roots


def test_cutover_moves_exact_legacy_bytes_and_installs_thin_native_wrappers(
    tmp_path: Path,
) -> None:
    expected = make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    plan = service.plan()
    marker = service.apply()
    assert service.apply() == marker
    assert service.plan() == plan
    assert marker["one_writer"] is True
    verified = service.verify()
    assert verified == {
        "status": "verified",
        "active_runtime": "runtime/src/software_factory",
        "legacy_runtime": "legacy/v1",
        "one_writer": True,
        "skill_count": 5,
    }
    for name in SKILL_NAMES:
        wrapper_root = tmp_path / name
        assert [path.name for path in wrapper_root.iterdir()] == ["SKILL.md"]
        content = (wrapper_root / "SKILL.md").read_text(encoding="utf-8")
        assert f"sf-skill {name}" in content
        legacy = tmp_path / "legacy" / "v1" / "skills" / name
        assert digest(legacy / "SKILL.md") == expected[f"{name}/SKILL.md"]
        assert digest(legacy / "scripts" / "owner.py") == expected[f"{name}/scripts/owner.py"]


def test_cutover_creates_native_wrapper_for_previously_missing_skill(tmp_path: Path) -> None:
    make_repository(tmp_path, omit="clean-software-factory")
    service = SourceCutoverService(tmp_path)
    marker = service.apply()
    missing = next(item for item in marker["skills"] if item["name"] == "clean-software-factory")
    assert missing["source_exists"] is False
    assert (tmp_path / "clean-software-factory" / "SKILL.md").is_file()
    assert not (tmp_path / "legacy" / "v1" / "skills" / "clean-software-factory").exists()


def test_rollback_restores_original_skill_bytes_exactly(tmp_path: Path) -> None:
    expected = make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    service.apply()
    rolled_back = service.rollback()
    assert rolled_back == {"status": "rolled_back", "restored_skills": 5}
    assert not (tmp_path / ".software-factory-source-cutover.json").exists()
    for relative, expected_hash in expected.items():
        assert digest(tmp_path / relative) == expected_hash
    for name in SKILL_NAMES:
        assert (tmp_path / name / "scripts" / "owner.py").is_file()
    reapplied = service.apply()
    assert reapplied["one_writer"] is True
    assert service.verify()["status"] == "verified"


def test_verification_rejects_competing_root_owner_file(tmp_path: Path) -> None:
    make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    service.apply()
    (tmp_path / "supervise-tracker-runs" / "scripts.py").write_text(
        "legacy_writer = True\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="competing files"):
        service.verify()


def test_verification_rejects_tampered_legacy_source(tmp_path: Path) -> None:
    make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    service.apply()
    legacy = (
        tmp_path / "legacy" / "v1" / "skills" / "implement-tracker-blocks" / "scripts" / "owner.py"
    )
    legacy.write_text("tampered = True\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="legacy source hash differs"):
        service.verify()


def test_incompatible_second_cutover_is_rejected(tmp_path: Path) -> None:
    make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    service.apply()
    marker = tmp_path / ".software-factory-source-cutover.json"
    content = marker.read_text(encoding="utf-8")
    marker.write_text(content.replace('"plan_root":"', '"plan_root":"different-'), encoding="utf-8")
    with pytest.raises(RuntimeError, match="incompatible"):
        service.apply()


def test_plan_rejects_symlinked_source_bytes(tmp_path: Path) -> None:
    make_repository(tmp_path)
    source = tmp_path / "implement-tracker-blocks"
    (source / "linked-owner.py").symlink_to(source / "scripts" / "owner.py")
    with pytest.raises(RuntimeError, match="symlink"):
        SourceCutoverService(tmp_path).plan()


def test_apply_resumes_from_frozen_pre_mutation_journal(tmp_path: Path) -> None:
    make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    plan = service.plan()
    marker = plan | {
        "status": "applying",
        "active_runtime": "runtime/src/software_factory",
        "legacy_runtime": "legacy/v1",
        "one_writer": True,
    }
    service.marker.write_text(json.dumps(marker), encoding="utf-8")
    first = SKILL_NAMES[0]
    destination = service.skills_legacy_root / first
    destination.parent.mkdir(parents=True)
    (tmp_path / first).replace(destination)

    applied = service.apply()

    assert applied["status"] == "applied"
    assert service.verify()["status"] == "verified"
    assert (tmp_path / first / "SKILL.md").is_file()
    assert (destination / "scripts" / "owner.py").is_file()


def test_rollback_rejects_changed_wrapper_before_deleting_it(tmp_path: Path) -> None:
    make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    service.apply()
    wrapper = tmp_path / "implement-tracker-blocks" / "SKILL.md"
    wrapper.write_text("changed\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="wrapper differs"):
        service.rollback()

    assert wrapper.read_text(encoding="utf-8") == "changed\n"
    assert (service.skills_legacy_root / "implement-tracker-blocks").is_dir()


def test_rollback_resumes_from_rolling_back_journal(tmp_path: Path) -> None:
    expected = make_repository(tmp_path)
    service = SourceCutoverService(tmp_path)
    marker = service.apply() | {"status": "rolling_back"}
    service.marker.write_text(json.dumps(marker), encoding="utf-8")
    first = SKILL_NAMES[-1]
    shutil.rmtree(tmp_path / first)
    (service.skills_legacy_root / first).replace(tmp_path / first)

    rolled_back = service.rollback()

    assert rolled_back == {"status": "rolled_back", "restored_skills": 5}
    for relative, expected_hash in expected.items():
        assert digest(tmp_path / relative) == expected_hash
