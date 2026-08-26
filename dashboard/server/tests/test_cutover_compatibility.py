from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from software_factory_dashboard.operations import DEFAULT_SUPERVISION_OWNER
from software_factory_dashboard.tracker import DEFAULT_VERIFIER_PATH


REPOSITORY = Path(__file__).resolve().parents[3]
SKILLS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
    "evolve-product-program",
    "clean-software-factory",
)


def test_cutover_has_one_active_compatibility_owner_and_inert_legacy_sources() -> None:
    source_marker = json.loads(
        (REPOSITORY / ".software-factory-source-cutover.json").read_text(encoding="utf-8")
    )
    runtime_marker = json.loads(
        (REPOSITORY / ".software-factory-runtime.json").read_text(encoding="utf-8")
    )
    assert source_marker["status"] == "applied"
    assert source_marker["one_writer"] is True
    assert runtime_marker["one_writer"] is True

    for skill in SKILLS:
        assert [path.name for path in (REPOSITORY / skill).iterdir()] == ["SKILL.md"]
    assert (REPOSITORY / "legacy" / "v1" / "skills" / "supervise-tracker-runs").is_dir()

    compatibility_root = (
        REPOSITORY / "runtime" / "src" / "software_factory" / "compatibility_owners"
    )
    assert DEFAULT_SUPERVISION_OWNER.is_relative_to(compatibility_root)
    assert DEFAULT_VERIFIER_PATH.is_relative_to(compatibility_root)
    assert "legacy/v1" not in DEFAULT_SUPERVISION_OWNER.read_text(encoding="utf-8")
    assert "legacy/v1" not in DEFAULT_VERIFIER_PATH.read_text(encoding="utf-8")

    for owner in (DEFAULT_SUPERVISION_OWNER, DEFAULT_VERIFIER_PATH):
        completed = subprocess.run(
            [sys.executable, str(owner), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout

    assert not list(REPOSITORY.glob(".v2-*-pending"))
    assert not (REPOSITORY / ".sf-upload").exists()
    assert len(list((REPOSITORY / "legacy" / "v1").glob(".v2-*-pending"))) == 12
    assert len(list((REPOSITORY / "legacy" / "v1" / ".sf-upload").rglob("part-*"))) == 4
