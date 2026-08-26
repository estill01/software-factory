from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from types import SimpleNamespace

import librsi
import pytest

from software_factory import StoreError
from software_factory.integrations.librsi import LIBRSI_PIN, verify_installed_librsi

RUNTIME_ROOT = Path(__file__).parents[1]


def test_librsi_dependency_is_exact_internal_and_not_a_bare_registry_resolution() -> None:
    project = tomllib.loads((RUNTIME_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    assert dependencies == [
        "libRSI @ git+https://github.com/estill01/libRSI.git@"
        "1d81f6180b40435e10145756a2d99e6f334d31bc"
    ]
    assert LIBRSI_PIN.version == "0.2.0"
    assert LIBRSI_PIN.producer_acceptance_revision == ("dbcb60edfbcab53ff7e5cc25403bfbc33b458329")
    assert LIBRSI_PIN.package_tree == "2653cb551e69bf2f45c95216982f70b50258c92e"
    assert LIBRSI_PIN.package_content_root == LIBRSI_PIN.package_tree
    assert LIBRSI_PIN.wheel_sha256 == (
        "6b06612150d2f3a11b23de14870738ea9cd6b704574c8cea2c8e811392454659"
    )
    assert LIBRSI_PIN.sdist_sha256 == (
        "e3ca4a817b80043ea59ba153e4d3ba105c86ad74183cb28816d66dd6d0f813c0"
    )
    assert "unpublished" in LIBRSI_PIN.artifact_boundary
    assert "no-license" in LIBRSI_PIN.artifact_boundary


def test_loaded_librsi_is_the_exact_vcs_revision_and_schema_contract() -> None:
    verified = verify_installed_librsi()
    assert verified["source_commit"] == LIBRSI_PIN.source_commit
    assert verified["version"] == LIBRSI_PIN.version
    direct_url = verified["direct_url"]
    assert direct_url is not None
    assert direct_url["vcs_info"]["commit_id"] == LIBRSI_PIN.source_commit
    assert LIBRSI_PIN.semantic_record_schema_version == 1
    assert LIBRSI_PIN.outcome_projection_schema_version == 1
    assert LIBRSI_PIN.event_projection_schema_version == 1
    assert LIBRSI_PIN.adapter_contract == "software-factory.librsi/v1"


def test_librsi_pin_fails_closed_without_exact_pep610_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = SimpleNamespace(version=LIBRSI_PIN.version, read_text=lambda _name: None)
    monkeypatch.setattr(
        "software_factory.integrations.librsi.pin.metadata.distribution",
        lambda _name: distribution,
    )
    with pytest.raises(StoreError, match="PEP 610"):
        verify_installed_librsi()


def test_dependency_direction_is_one_way_and_factory_does_not_copy_librsi_source() -> None:
    package_root = Path(librsi.__file__).resolve().parent
    reverse_imports: list[str] = []
    for source in package_root.rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".", 1)[0] == "software_factory" for alias in node.names):
                    reverse_imports.append(str(source))
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".", 1)[0] == "software_factory"
            ):
                reverse_imports.append(str(source))
    assert reverse_imports == []
    assert not (RUNTIME_ROOT / "src" / "librsi").exists()
