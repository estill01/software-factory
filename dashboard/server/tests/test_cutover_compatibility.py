from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path

import tomllib
from software_factory_dashboard.factory_workflows import FactoryWorkflowOwner
from software_factory_dashboard.operations import (
    DEFAULT_SUPERVISION_OWNER,
    OperationsProjectionService,
)
from software_factory_dashboard.tracker import DEFAULT_VERIFIER_PATH

REPOSITORY = Path(__file__).resolve().parents[3]
SKILLS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
    "evolve-product-program",
    "clean-software-factory",
)


def compatibility_owner_module():
    spec = importlib.util.spec_from_file_location(
        "cutover_compatibility_owner", DEFAULT_SUPERVISION_OWNER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(DEFAULT_SUPERVISION_OWNER.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_cutover_has_one_active_compatibility_owner_and_inert_legacy_sources() -> None:
    source_marker = json.loads(
        (REPOSITORY / ".software-factory-source-cutover.json").read_text(
            encoding="utf-8"
        )
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

    rejected = subprocess.run(
        [
            sys.executable,
            str(DEFAULT_SUPERVISION_OWNER),
            "--root",
            str(REPOSITORY / "not-a-canonical-supervision-root"),
            "init",
            "--target-thread",
            "target-thread-retired-writer",
            "--target-label",
            "Retired writer probe",
            "--watcher-thread",
            "watcher-thread-retired-writer",
            "--reviewer-thread",
            "reviewer-thread-retired-writer",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2
    assert "projection-only" in rejected.stdout
    assert not (REPOSITORY / "not-a-canonical-supervision-root").exists()

    assert not list(REPOSITORY.glob(".v2-*-pending"))
    assert not (REPOSITORY / ".sf-upload").exists()
    assert len(list((REPOSITORY / "legacy" / "v1").glob(".v2-*-pending"))) == 12
    assert len(list((REPOSITORY / "legacy" / "v1" / ".sf-upload").rglob("part-*"))) == 4


def test_legacy_dashboard_supervision_effects_are_unavailable_not_hidden() -> None:
    owner = object.__new__(FactoryWorkflowOwner)
    definitions = owner._retired_legacy_supervision_definitions()
    assert len(definitions) == 12
    assert all(not definition.supported for definition in definitions)
    assert all(
        definition.owner == "software_factory.native_skills"
        for definition in definitions
    )
    assert all(
        "sf-skill supervise-tracker-runs" in definition.unavailable_reason
        for definition in definitions
    )

    apply_source = inspect.getsource(OperationsProjectionService.apply_role_bind)
    assert "owner.cmd_bind" not in apply_source
    assert "legacy_supervision_writer_retired" in apply_source


def test_installed_compatibility_owner_has_no_direct_second_writer_bypass(
    tmp_path: Path,
) -> None:
    owner = compatibility_owner_module()
    target = tmp_path / "forbidden.json"

    for effect in (
        lambda: owner.cmd_bind(object()),
        lambda: owner.atomic_json(target, {"forbidden": True}),
        lambda: owner.append_raw(target, {"forbidden": True}),
    ):
        try:
            effect()
        except owner.SupervisionLogError as exc:
            assert "projection-only" in str(exc)
        else:
            raise AssertionError(
                "installed compatibility effect unexpectedly succeeded"
            )
        assert not target.exists()

    parsed = owner.parser().parse_args(
        [
            "--root",
            str(tmp_path / "supervision"),
            "init",
            "--target-thread",
            "target-thread-retired-writer",
            "--target-label",
            "Retired writer probe",
            "--watcher-thread",
            "watcher-thread-retired-writer",
            "--reviewer-thread",
            "reviewer-thread-retired-writer",
        ]
    )
    try:
        parsed.func(parsed)
    except owner.SupervisionLogError as exc:
        assert "projection-only" in str(exc)
    else:
        raise AssertionError(
            "parsed compatibility command bypassed the read-only boundary"
        )
    assert not (tmp_path / "supervision").exists()

    sys.path.insert(0, str(DEFAULT_SUPERVISION_OWNER.parent))
    try:
        weekly = owner.weekly_report_module()
        terminal = owner.terminal_report_module()
    finally:
        sys.path.pop(0)
    for effect in (
        lambda: weekly.atomic_write(target, b"forbidden"),
        lambda: weekly.render_pdf(target, {}, {}),
        lambda: terminal.atomic_write(target, b"forbidden"),
        lambda: terminal.render_pdf(target, {}, report_set_id="forbidden"),
    ):
        try:
            effect()
        except (weekly.WeeklyReportError, terminal.TerminalReportError) as exc:
            assert "projection-only" in str(exc)
        else:
            raise AssertionError(
                "installed report companion retained a producer effect"
            )
        assert not target.exists()

    fixture_driver = Path(__file__).with_name("supervision_fixture_owner.py")
    assert "legacy/v1/skills/supervise-tracker-runs" in fixture_driver.read_text(
        encoding="utf-8"
    )


def test_dashboard_composes_the_exact_local_factory_runtime() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY / "dashboard/server/pyproject.toml").read_text()
    )
    assert "software-factory==2.0.0.dev6" in pyproject["project"]["dependencies"]
    assert pyproject["tool"]["uv"]["sources"]["software-factory"] == {
        "path": "../../runtime",
        "editable": True,
    }
