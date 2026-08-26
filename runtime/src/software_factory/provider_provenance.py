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

from .errors import ProviderError

_CLIENT_PIN = "provider_pins/codex-app-server-client.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_content_record(path: Path) -> tuple[str, int, int]:
    rows: list[dict[str, str | int]] = []
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            for info in sorted(
                (item for item in archive.infolist() if not item.is_dir()),
                key=lambda item: item.filename,
            ):
                data = archive.read(info)
                total += len(data)
                rows.append(
                    {
                        "path": info.filename,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    }
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ProviderError("shared client wheel is unreadable or invalid") from exc
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(rows), total


@dataclass(frozen=True)
class QualifiedClientPin:
    record: dict[str, Any]

    @classmethod
    def load(cls) -> QualifiedClientPin:
        source = resources.files("software_factory").joinpath(_CLIENT_PIN)
        try:
            record = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProviderError("shared client pin is unavailable or invalid") from exc
        if not isinstance(record, dict) or record.get("schema_version") != 1:
            raise ProviderError("shared client pin schema is unsupported")
        return cls(record=record)

    def verify_wheel(self, wheel_path: str | Path) -> Path:
        supplied = Path(wheel_path).expanduser()
        if supplied.is_symlink():
            raise ProviderError("shared client wheel must be a regular non-symlink file")
        try:
            path = supplied.resolve(strict=True)
        except OSError as exc:
            raise ProviderError("shared client wheel is unavailable") from exc
        if not path.is_file():
            raise ProviderError("shared client wheel must be a regular non-symlink file")
        if path.name != self.record["wheel"]:
            raise ProviderError("shared client wheel filename differs from the accepted artifact")
        if _sha256(path) != self.record["wheel_sha256"]:
            raise ProviderError("shared client wheel SHA-256 differs from the accepted artifact")
        content_root, member_count, total_bytes = _wheel_content_record(path)
        if content_root != self.record["wheel_content_root_sha256"]:
            raise ProviderError(
                "shared client wheel content root differs from the accepted artifact"
            )
        if member_count != self.record["wheel_member_count"]:
            raise ProviderError(
                "shared client wheel member count differs from the accepted artifact"
            )
        if total_bytes != self.record["wheel_uncompressed_bytes"]:
            raise ProviderError("shared client wheel byte count differs from the accepted artifact")
        return path

    def verify_module(self, module: ModuleType, wheel_path: Path) -> None:
        module_path = str(getattr(module, "__file__", ""))
        if not module_path.startswith(f"{wheel_path}{Path('/').as_posix()}"):
            raise ProviderError("shared client was not imported from the verified wheel")
        if getattr(module, "__version__", None) != self.record["version"]:
            raise ProviderError("shared client version differs from the accepted pin")
        target = getattr(module, "PINNED_PROTOCOL", None)
        protocol = self.record["protocol"]
        for attribute, field in (
            ("codex_version", "codex_version"),
            ("source_commit", "source_commit"),
            ("schema_tree_root_sha256", "schema_tree_root_sha256"),
            ("selected_surface_root_sha256", "selected_surface_root_sha256"),
        ):
            if getattr(target, attribute, None) != protocol[field]:
                raise ProviderError(f"shared client protocol {attribute} differs from the pin")


def load_qualified_client(wheel_path: str | Path) -> tuple[ModuleType, QualifiedClientPin]:
    """Load the client only from its exact accepted wheel, never a registry resolution."""

    pin = QualifiedClientPin.load()
    accepted_wheel = pin.verify_wheel(wheel_path)
    existing = sys.modules.get(str(pin.record["import_root"]))
    if existing is not None:
        pin.verify_module(existing, accepted_wheel)
        return existing, pin
    sys.path.insert(0, str(accepted_wheel))
    try:
        module = importlib.import_module(str(pin.record["import_root"]))
        pin.verify_module(module, accepted_wheel)
    except Exception:
        sys.path.remove(str(accepted_wheel))
        raise
    return module, pin
