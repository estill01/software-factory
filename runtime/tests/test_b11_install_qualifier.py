from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
import stat
import warnings
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
QUALIFIER = ROOT / "scripts" / "qualify_sfv2_b11_install.py"


def load_qualifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sfv2_b11_install_qualifier", QUALIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record_digest(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode("ascii")
    return f"sha256={encoded.rstrip('=')}"


def write_wheel(
    path: Path,
    *,
    unrecorded: bool = False,
    duplicate: bool = False,
    symlink: bool = False,
) -> None:
    metadata = b"Name: demo\nVersion: 1.0\n"
    module = b"VALUE = 1\n"
    record_path = "demo-1.0.dist-info/RECORD"
    rows = [
        f"demo/__init__.py,{record_digest(module)},{len(module)}",
        f"demo-1.0.dist-info/METADATA,{record_digest(metadata)},{len(metadata)}",
        f"{record_path},,",
    ]
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("demo/__init__.py", module)
        wheel.writestr("demo-1.0.dist-info/METADATA", metadata)
        wheel.writestr(record_path, "\n".join(rows) + "\n")
        if unrecorded:
            wheel.writestr("demo/unrecorded_effect.py", b"EFFECT = True\n")
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                wheel.writestr("demo/__init__.py", module)
        if symlink:
            link = zipfile.ZipInfo("demo/link.py")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            wheel.writestr(link, "__init__.py")


@pytest.mark.parametrize("mutation", ["unrecorded", "duplicate", "symlink"])
def test_wheel_projection_rejects_incomplete_or_unsafe_inventory(
    tmp_path: Path, mutation: str
) -> None:
    qualifier = load_qualifier()
    wheel = tmp_path / "demo-1.0-py3-none-any.whl"
    write_wheel(
        wheel,
        unrecorded=mutation == "unrecorded",
        duplicate=mutation == "duplicate",
        symlink=mutation == "symlink",
    )

    with pytest.raises(qualifier.QualificationError):
        qualifier.wheel_projection(wheel)


def test_wheel_projection_accepts_exact_record_coverage(tmp_path: Path) -> None:
    qualifier = load_qualifier()
    wheel = tmp_path / "demo-1.0-py3-none-any.whl"
    write_wheel(wheel)

    projection = qualifier.wheel_projection(wheel)

    assert projection["name"] == "demo"
    assert projection["version"] == "1.0"
    assert {entry["path"] for entry in projection["entries"]} == {
        "demo/__init__.py",
        "demo-1.0.dist-info/METADATA",
    }


def test_manifest_authority_is_one_stable_no_follow_read(tmp_path: Path) -> None:
    qualifier = load_qualifier()
    manifest = tmp_path / "manifest.json"
    original = b'{"authority":"original"}\n'
    replacement = b'{"authority":"replacement"}\n'
    manifest.write_bytes(original)

    authority = qualifier.read_stable_bytes(
        manifest,
        label="Qualification manifest",
        maximum_bytes=1024,
    )
    manifest.write_bytes(replacement)

    assert authority == original
    assert hashlib.sha256(authority).hexdigest() == hashlib.sha256(original).hexdigest()

    symlink = tmp_path / "manifest-link.json"
    os.symlink(manifest, symlink)
    with pytest.raises(OSError):
        qualifier.read_stable_bytes(
            symlink,
            label="Qualification manifest",
            maximum_bytes=1024,
        )
