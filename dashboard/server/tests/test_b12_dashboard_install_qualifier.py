from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[3]
QUALIFIER = ROOT / "scripts" / "qualify_sfv2_b12_dashboard_install.py"
OFFLINE_QUALIFIER = ROOT / "scripts" / "qualify_sfv2_b11_install.py"


def load_qualifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sfv2_b12_dashboard_install_qualifier", QUALIFIER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(project: Path, *arguments: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "SFV2 Test",
        "GIT_AUTHOR_EMAIL": "sfv2@example.invalid",
        "GIT_COMMITTER_NAME": "SFV2 Test",
        "GIT_COMMITTER_EMAIL": "sfv2@example.invalid",
    }
    return subprocess.run(
        ["git", "-C", str(project), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def test_cli_rejects_caller_supplied_offline_qualifier() -> None:
    qualifier = load_qualifier()
    parser = qualifier._parser()

    assert "--offline-qualifier" not in parser._option_string_actions
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--project-root",
                "/project",
                "--static-dir",
                "/static",
                "--manifest",
                "/manifest.json",
                "--offline-receipt",
                "/receipt.json",
                "--artifact-directory",
                "/artifacts",
                "--offline-qualifier",
                "/forged.py",
            ]
        )


def test_offline_qualifier_is_bound_to_exact_project_blob(tmp_path: Path) -> None:
    qualifier = load_qualifier()
    project = tmp_path / "project"
    helper = project / qualifier.OFFLINE_QUALIFIER_RELATIVE_PATH
    helper.parent.mkdir(parents=True)
    helper.write_bytes(OFFLINE_QUALIFIER.read_bytes())
    git(project, "init", "-q")
    git(project, "add", helper.relative_to(project).as_posix())
    git(project, "commit", "-qm", "exact qualifier")
    revision = git(project, "rev-parse", "HEAD")

    _, identity = qualifier._load_offline_qualifier(project, revision)

    assert identity["path"] == "scripts/qualify_sfv2_b11_install.py"
    assert identity["git_blob"] == git(
        project,
        "rev-parse",
        f"{revision}:scripts/qualify_sfv2_b11_install.py",
    )
    helper.write_text("FORGED = True\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="differs from the exact source"):
        qualifier._load_offline_qualifier(project, revision)
