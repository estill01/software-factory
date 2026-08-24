from __future__ import annotations

import json
from pathlib import Path

from software_factory.merge_readiness import MergeReadinessService


def make_repository(root: Path) -> None:
    tests = root / "runtime" / "tests"
    migrations = root / "runtime" / "src" / "software_factory" / "migrations"
    tests.mkdir(parents=True)
    migrations.mkdir(parents=True)
    (tests / "test_example.py").write_text(
        "def test_required_behavior():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "runtime" / "acceptance-matrix.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "domains": {"example": {"required": ["test_example.py::test_required_behavior"]}},
            }
        ),
        encoding="utf-8",
    )
    (migrations / "0001_core.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (migrations / "0002_next.sql").write_text("SELECT 1;\n", encoding="utf-8")


def test_merge_readiness_accepts_exact_clean_tree(tmp_path: Path) -> None:
    make_repository(tmp_path)
    report = MergeReadinessService(tmp_path).audit()
    assert report["status"] == "ready"
    assert report["acceptance"]["required"] == 1
    assert report["migrations"]["versions"] == [1, 2]
    assert report["findings"] == []


def test_merge_readiness_fails_closed_on_missing_behavior_and_transport(
    tmp_path: Path,
) -> None:
    make_repository(tmp_path)
    matrix = tmp_path / "runtime" / "acceptance-matrix.json"
    matrix.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "domains": {"example": {"required": ["test_example.py::test_missing_behavior"]}},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".v2-work-pending").write_text("pending\n", encoding="utf-8")
    upload = tmp_path / ".sf-upload" / "slice"
    upload.mkdir(parents=True)
    (upload / "part-000").write_text("opaque\n", encoding="utf-8")
    report = MergeReadinessService(tmp_path).audit()
    assert report["status"] == "blocked"
    checks = {finding["check"] for finding in report["findings"]}
    assert checks >= {"acceptance-matrix", "source-hygiene"}


def test_merge_readiness_rejects_duplicate_and_gapped_migrations(
    tmp_path: Path,
) -> None:
    make_repository(tmp_path)
    migrations = tmp_path / "runtime" / "src" / "software_factory" / "migrations"
    (migrations / "0002_duplicate.sql").write_text("SELECT 2;\n", encoding="utf-8")
    (migrations / "0004_gap.sql").write_text("SELECT 4;\n", encoding="utf-8")
    report = MergeReadinessService(tmp_path).audit()
    assert report["status"] == "blocked"
    messages = {finding["message"] for finding in report["findings"]}
    assert "multiple migrations claim the same version" in messages
    assert "migration sequence contains gaps" in messages


def test_merge_readiness_binds_command_results_and_currentness(
    tmp_path: Path,
) -> None:
    make_repository(tmp_path)
    report = MergeReadinessService(tmp_path).audit(
        commands=[["python", "-c", "raise SystemExit(3)"]],
        expected_head="not-this-head",
    )
    assert report["status"] == "blocked"
    checks = {finding["check"] for finding in report["findings"]}
    assert checks >= {"mechanical-gate", "currentness"}
    assert len(report["evidence_root"]) == 64
