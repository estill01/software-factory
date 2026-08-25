from __future__ import annotations

import hashlib
import importlib
import json
import sys
import zipfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import ModuleType
from typing import Any

from .errors import StoreError

_QUALIFIED_UTILS_PIN = "provider_pins/qualified-utils.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_record(path: Path) -> tuple[str, int, int, dict[str, bytes]]:
    rows: list[dict[str, str | int]] = []
    members: dict[str, bytes] = {}
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            for info in sorted(
                (item for item in archive.infolist() if not item.is_dir()),
                key=lambda item: item.filename,
            ):
                data = archive.read(info)
                members[info.filename] = data
                total += len(data)
                rows.append(
                    {
                        "path": info.filename,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    }
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise StoreError("qualified utility wheel is unreadable or invalid") from exc
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(rows), total, members


@dataclass(frozen=True)
class QualifiedUtilityPin:
    record: dict[str, Any]

    @classmethod
    def load(cls) -> QualifiedUtilityPin:
        source = resources.files("software_factory").joinpath(_QUALIFIED_UTILS_PIN)
        try:
            record = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise StoreError("qualified utils pin is unavailable or invalid") from exc
        if not isinstance(record, dict) or record.get("schema_version") != 1:
            raise StoreError("qualified utils pin schema is unsupported")
        if record.get("release_posture") != "no-license-selected/unpublished":
            raise StoreError("qualified utils pin lost the unpublished/no-license boundary")
        packages = record.get("packages")
        if not isinstance(packages, dict) or set(packages) != {
            "embedded-service-contract",
            "runtime-manifest",
        }:
            raise StoreError("qualified utils pin package set is incomplete")
        return cls(record=record)

    def verify_wheel(self, distribution: str, wheel_path: str | Path) -> Path:
        package = self.record["packages"].get(distribution)
        if not isinstance(package, dict):
            raise StoreError("utility distribution is not qualified for this Factory lane")
        supplied = Path(wheel_path).expanduser()
        if supplied.is_symlink():
            raise StoreError("qualified utility wheel must be a regular non-symlink file")
        try:
            path = supplied.resolve(strict=True)
        except OSError as exc:
            raise StoreError("qualified utility wheel is unavailable") from exc
        if not path.is_file() or path.name != package["wheel"]:
            raise StoreError("qualified utility wheel filename differs from the accepted artifact")
        if _sha256(path) != package["wheel_sha256"]:
            raise StoreError("qualified utility wheel SHA-256 differs from the accepted artifact")
        content_root, member_count, total_bytes, members = _wheel_record(path)
        if content_root != package["wheel_content_root_sha256"]:
            raise StoreError(
                "qualified utility wheel content root differs from the accepted artifact"
            )
        if member_count != package["wheel_member_count"]:
            raise StoreError(
                "qualified utility wheel member count differs from the accepted artifact"
            )
        if total_bytes != package["wheel_uncompressed_bytes"]:
            raise StoreError(
                "qualified utility wheel byte count differs from the accepted artifact"
            )
        for member, expected in package["public_contracts"].items():
            content = members.get(member)
            if content is None or hashlib.sha256(content).hexdigest() != expected:
                raise StoreError("qualified utility public contract differs from the accepted root")
        return path

    def load_module(self, distribution: str, wheel_path: str | Path) -> ModuleType:
        path = self.verify_wheel(distribution, wheel_path)
        package = self.record["packages"][distribution]
        import_root = str(package["import_root"])
        existing = sys.modules.get(import_root)
        if existing is not None:
            self.verify_module(distribution, existing, path)
            return existing
        sys.path.insert(0, str(path))
        try:
            module = importlib.import_module(import_root)
            self.verify_module(distribution, module, path)
        except Exception:
            sys.path.remove(str(path))
            raise
        return module

    def verify_module(self, distribution: str, module: ModuleType, wheel_path: Path) -> None:
        package = self.record["packages"][distribution]
        module_path = str(getattr(module, "__file__", ""))
        if not module_path.startswith(f"{wheel_path}{Path('/').as_posix()}"):
            raise StoreError("qualified utility was not imported from its verified wheel")
        if getattr(module, "__version__", None) != package["version"]:
            raise StoreError("qualified utility version differs from the accepted pin")


def load_qualified_utility_modules(
    *,
    embedded_contract_wheel: str | Path,
    runtime_manifest_wheel: str | Path,
) -> tuple[ModuleType, ModuleType, QualifiedUtilityPin]:
    """Load only the two exact Block 9 utility artifacts from explicit paths."""

    pin = QualifiedUtilityPin.load()
    embedded = pin.load_module("embedded-service-contract", embedded_contract_wheel)
    manifest = pin.load_module("runtime-manifest", runtime_manifest_wheel)
    return embedded, manifest, pin
