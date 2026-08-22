from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from software_factory.acceptance import AcceptanceService
from software_factory.database import Database
from software_factory.errors import InvalidTransition


def git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return process.stdout.strip()


def make_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repository = tmp_path / "repository"
    tests = repository / "runtime" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_behavior.py").write_text(
        "def test_passes():\n    assert True\n\n"
        "def test_fails():\n    assert False\n",
        encoding="utf-8",
    )
    git(repository, "init")
    git(repository, "config", "user.email", "acceptance@example.test")
    git(repository, "config", "user.name", "Acceptance Test")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "initial")
    return repository, git(repository, "rev-parse", "HEAD"), git(
        repository, "rev-parse", "HEAD^{tree}"
    )


def database(tmp_path: Path) -> Database:
    value = Database(tmp_path / "factory.sqlite3")
    value.initialize()
    return value


def write_matrix(path: Path, test_id: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "domains": {
                    "end_to_end": {
                        "required": [test_id],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_acceptance_run_binds_and_executes_exact_revision(tmp_path: Path) -> None:
    repository, head, tree = make_repository(tmp_path)
    store = database(tmp_path)
    service = AcceptanceService(store)
    matrix = write_matrix(
        repository / "runtime" / "acceptance-matrix.json",
        "tests/test_behavior.py::test_passes",
    )
    run = service.create_run(
        source_revision=head,
        source_tree=tree,
        matrix_path=matrix,
        test_root="runtime",
    )
    completed = service.execute(run["id"], repository_root=repository)
    assert completed["status"] == "passed"
    assert len(completed["evidence_root"]) == 64
    assert service.require_passed_revision(head)["id"] == run["id"]
    assert service.case_results(run["id"])[0]["status"] == "passed"


def test_acceptance_failure_cannot_authorize_revision(tmp_path: Path) -> None:
    repository, head, tree = make_repository(tmp_path)
    store = database(tmp_path)
    service = AcceptanceService(store)
    matrix = write_matrix(
        repository / "runtime" / "acceptance-matrix.json",
        "tests/test_behavior.py::test_fails",
    )
    run = service.create_run(
        source_revision=head,
        source_tree=tree,
        matrix_path=matrix,
        test_root="runtime",
    )
    completed = service.execute(run["id"], repository_root=repository)
    assert completed["status"] == "failed"
    with pytest.raises(InvalidTransition, match="lacks a passed"):
        service.require_passed_revision(head)


def test_acceptance_rejects_stale_source_and_duplicate_claim(tmp_path: Path) -> None:
    repository, head, tree = make_repository(tmp_path)
    store = database(tmp_path)
    service = AcceptanceService(store)
    matrix = write_matrix(
        repository / "runtime" / "acceptance-matrix.json",
        "tests/test_behavior.py::test_passes",
    )
    run = service.create_run(
        source_revision=head,
        source_tree=tree,
        matrix_path=matrix,
        test_root="runtime",
    )
    (repository / "change.txt").write_text("change\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "advance")
    with pytest.raises(InvalidTransition, match="source revision is stale"):
        service.execute(run["id"], repository_root=repository)

    current_head = git(repository, "rev-parse", "HEAD")
    current_tree = git(repository, "rev-parse", "HEAD^{tree}")
    run = service.create_run(
        source_revision=current_head,
        source_tree=current_tree,
        matrix_path=matrix,
        test_root="runtime",
    )
    service.execute(run["id"], repository_root=repository)
    with pytest.raises(InvalidTransition, match="not queued"):
        service.execute(run["id"], repository_root=repository)


def test_acceptance_matrix_rejects_duplicate_case_ownership(tmp_path: Path) -> None:
    repository, head, tree = make_repository(tmp_path)
    store = database(tmp_path)
    service = AcceptanceService(store)
    matrix = repository / "runtime" / "acceptance-matrix.json"
    matrix.write_text(
        json.dumps(
            {
                "domains": {
                    "one": {"required": ["tests/test_behavior.py::test_passes"]},
                    "two": {"required": ["tests/test_behavior.py::test_passes"]},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicated"):
        service.create_run(
            source_revision=head,
            source_tree=tree,
            matrix_path=matrix,
            test_root="runtime",
        )
