#!/usr/bin/env python3
"""Install and smoke-test an exact SFV2 Block 11 or Block 12 wheel set offline."""

from __future__ import annotations

import argparse
import base64
import configparser
import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

SHA256 = re.compile(r"^[0-9a-f]{64}$")
QUALIFICATION_KINDS = (
    "sfv2-b11-offline-install-qualification",
    "sfv2-b12-offline-install-qualification",
)


class QualificationError(RuntimeError):
    """The exact offline installation contract was not satisfied."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def normalize_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_stable_bytes(path: Path, *, label: str, maximum_bytes: int) -> bytes:
    """Read one regular no-follow file from a stable descriptor exactly once."""

    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            raise QualificationError(f"{label} is not a bounded regular file")
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _file_identity(before) != _file_identity(after):
        raise QualificationError(f"{label} changed while read")
    value = b"".join(chunks)
    if len(value) != before.st_size or len(value) > maximum_bytes:
        raise QualificationError(f"{label} size differs")
    return value


def stage_artifact(source: Path, destination: Path, expected_sha256: str) -> str:
    """Copy one stable regular file into private qualification-owned storage."""

    source_descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(source_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise QualificationError(f"Artifact is not a regular file: {source.name}")
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o400,
        )
        digest = hashlib.sha256()
        try:
            while True:
                chunk = os.read(source_descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_descriptor, view)
                    view = view[written:]
            os.fsync(destination_descriptor)
        finally:
            os.close(destination_descriptor)
        after = os.fstat(source_descriptor)
    finally:
        os.close(source_descriptor)
    if _file_identity(before) != _file_identity(after):
        destination.unlink(missing_ok=True)
        raise QualificationError(f"Artifact changed while staged: {source.name}")
    actual = digest.hexdigest()
    if actual != expected_sha256 or sha256(destination) != expected_sha256:
        destination.unlink(missing_ok=True)
        raise QualificationError(f"Artifact hash differs: {source.name}")
    return actual


def _record_sha256(value: str) -> str:
    if not value.startswith("sha256="):
        raise QualificationError("Wheel RECORD uses a non-SHA-256 digest")
    encoded = value.removeprefix("sha256=")
    try:
        decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, TypeError) as exc:
        raise QualificationError("Wheel RECORD digest is invalid") from exc
    if len(decoded) != 32:
        raise QualificationError("Wheel RECORD digest is not an exact SHA-256")
    return decoded.hex()


def _validate_wheel_path(value: str, *, wheel: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value.rstrip("/")
    ):
        raise QualificationError(f"Wheel path escapes: {wheel}")


def _entrypoints(
    wheel: zipfile.ZipFile, names: set[str], *, label: str
) -> dict[str, str]:
    candidates = [
        name for name in names if name.endswith(".dist-info/entry_points.txt")
    ]
    if len(candidates) > 1:
        raise QualificationError(f"Wheel entry points are ambiguous: {label}")
    if not candidates:
        return {}
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        parser.read_string(wheel.read(candidates[0]).decode("utf-8"))
    except (configparser.Error, UnicodeDecodeError) as exc:
        raise QualificationError(f"Wheel entry points differ: {label}") from exc
    projected: dict[str, str] = {}
    for group in ("console_scripts", "gui_scripts"):
        if not parser.has_section(group):
            continue
        for name, target in parser.items(group):
            if (
                not name
                or Path(name).name != name
                or "\\" in name
                or name in projected
                or not target.strip()
            ):
                raise QualificationError(f"Wheel entry point differs: {label}")
            projected[name] = target.strip()
    return projected


def wheel_projection(path: Path) -> dict[str, Any]:
    """Validate one wheel and project its complete non-directory inventory."""

    try:
        with zipfile.ZipFile(path) as wheel:
            infos = wheel.infolist()
            names: set[str] = set()
            members: set[str] = set()
            for info in infos:
                _validate_wheel_path(info.filename, wheel=path.name)
                if info.filename in names:
                    raise QualificationError(f"Wheel member is duplicated: {path.name}")
                names.add(info.filename)
                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise QualificationError(f"Wheel member is symlinked: {path.name}")
                if not info.is_dir():
                    members.add(info.filename)
            metadata_names = [
                name for name in members if name.endswith(".dist-info/METADATA")
            ]
            record_names = [
                name for name in members if name.endswith(".dist-info/RECORD")
            ]
            if len(metadata_names) != 1 or len(record_names) != 1:
                raise QualificationError(f"Wheel metadata is ambiguous: {path.name}")
            metadata: dict[str, str] = {}
            for line in wheel.read(metadata_names[0]).decode("utf-8").splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    if key in {"Name", "Version"}:
                        metadata[key] = value
            if set(metadata) != {"Name", "Version"}:
                raise QualificationError(f"Wheel identity is incomplete: {path.name}")
            entries: list[dict[str, Any]] = []
            rows = csv.reader(io.StringIO(wheel.read(record_names[0]).decode("utf-8")))
            seen: set[str] = set()
            for row in rows:
                if len(row) != 3 or row[0] in seen:
                    raise QualificationError(f"Wheel RECORD differs: {path.name}")
                relative, encoded_hash, raw_size = row
                seen.add(relative)
                _validate_wheel_path(relative, wheel=path.name)
                if relative == record_names[0]:
                    if encoded_hash or raw_size:
                        raise QualificationError(
                            f"Wheel RECORD self-entry differs: {path.name}"
                        )
                    continue
                if relative not in names:
                    raise QualificationError(
                        f"Wheel RECORD member is missing: {path.name}"
                    )
                try:
                    size = int(raw_size)
                except ValueError as exc:
                    raise QualificationError(
                        f"Wheel RECORD size differs: {path.name}"
                    ) from exc
                payload = wheel.read(relative)
                digest = hashlib.sha256(payload).hexdigest()
                if len(payload) != size or digest != _record_sha256(encoded_hash):
                    raise QualificationError(
                        f"Wheel RECORD content differs: {path.name}"
                    )
                entries.append({"path": relative, "sha256": digest, "bytes": size})
            if seen != members:
                raise QualificationError(
                    f"Wheel RECORD does not cover every member: {path.name}"
                )
            entrypoints = _entrypoints(wheel, names, label=path.name)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise QualificationError(f"Wheel is unreadable: {path.name}") from exc
    entries.sort(key=lambda item: item["path"])
    return {
        "name": metadata["Name"],
        "normalized_name": normalize_distribution_name(metadata["Name"]),
        "version": metadata["Version"],
        "record_path": record_names[0],
        "dist_info_directory": record_names[0].removesuffix("/RECORD"),
        "entrypoints": entrypoints,
        "entries": entries,
        "content_root_sha256": hashlib.sha256(canonical(entries)).hexdigest(),
    }


def verify_installed_projection(
    python: Path,
    wheel_projections: Sequence[dict[str, Any]],
    staged_artifacts: Sequence[Path],
) -> dict[str, dict[str, str]]:
    result = run(
        [
            str(python),
            "-I",
            "-c",
            "import json,sysconfig;print(json.dumps(sysconfig.get_paths(),sort_keys=True))",
        ],
        label="isolated installation path projection",
    )
    paths = json.loads(result.stdout)
    roots = {
        Path(paths[name]).resolve(strict=True)
        for name in ("purelib", "platlib")
        if isinstance(paths.get(name), str)
    }
    if not roots:
        raise QualificationError("Installed package roots are unavailable")
    environment_root = Path(paths["data"]).resolve(strict=True)
    scripts_root = Path(paths["scripts"]).resolve(strict=True)
    installed_roots: dict[str, dict[str, str]] = {}
    fixed_installer_names = {
        "INSTALLER",
        "REQUESTED",
        "direct_url.json",
        "uv_cache.json",
    }
    for wheel, staged_artifact in zip(wheel_projections, staged_artifacts, strict=True):
        record_candidates = [root / wheel["record_path"] for root in roots]
        records = [candidate for candidate in record_candidates if candidate.is_file()]
        if len(records) != 1 or records[0].is_symlink():
            raise QualificationError(f"Installed RECORD is ambiguous: {wheel['name']}")
        root = next(root for root in roots if records[0] == root / wheel["record_path"])
        installed_record = read_stable_bytes(
            records[0],
            label=f"Installed RECORD for {wheel['name']}",
            maximum_bytes=16 * 1024 * 1024,
        )
        try:
            rows = csv.reader(io.StringIO(installed_record.decode("utf-8")))
            installed_entries: list[dict[str, Any]] = []
            installed_paths: set[str] = set()
            for row in rows:
                if len(row) != 3 or row[0] in installed_paths:
                    raise QualificationError(
                        f"Installed RECORD differs: {wheel['name']}"
                    )
                relative, encoded_hash, raw_size = row
                installed_paths.add(relative)
                relative_path = PurePosixPath(relative)
                if (
                    not relative
                    or "\\" in relative
                    or relative_path.is_absolute()
                    or relative_path.as_posix() != relative
                ):
                    raise QualificationError(
                        f"Installed RECORD path differs: {wheel['name']}"
                    )
                target = Path(os.path.abspath(root / relative))
                if not target.is_relative_to(environment_root):
                    raise QualificationError(
                        f"Installed RECORD escapes: {wheel['name']}"
                    )
                if relative == wheel["record_path"]:
                    if encoded_hash or raw_size or target != records[0]:
                        raise QualificationError(
                            f"Installed RECORD self-entry differs: {wheel['name']}"
                        )
                    installed_entries.append(
                        {"path": relative, "kind": "installed-record-self"}
                    )
                    continue
                if target.is_symlink() or not target.is_file():
                    raise QualificationError(f"Installed member differs: {relative}")
                if any(
                    parent.is_symlink()
                    for parent in target.parents
                    if parent == environment_root
                    or parent.is_relative_to(environment_root)
                ):
                    raise QualificationError(
                        f"Installed member is symlinked: {relative}"
                    )
                try:
                    expected_size = int(raw_size)
                except ValueError as exc:
                    raise QualificationError(
                        f"Installed RECORD size differs: {wheel['name']}"
                    ) from exc
                actual_hash = sha256(target)
                if (
                    target.stat().st_size != expected_size
                    or actual_hash != _record_sha256(encoded_hash)
                ):
                    raise QualificationError(
                        f"Installed member content differs: {relative}"
                    )
                installed_entries.append(
                    {"path": relative, "sha256": actual_hash, "bytes": expected_size}
                )
        except UnicodeDecodeError as exc:
            raise QualificationError(
                f"Installed RECORD is unreadable: {wheel['name']}"
            ) from exc

        expected_wheel_paths = {entry["path"] for entry in wheel["entries"]}
        generated_metadata_paths = {
            f"{wheel['dist_info_directory']}/{name}" for name in fixed_installer_names
        }
        generated_script_paths = {
            Path(os.path.relpath(scripts_root / name, root)).as_posix()
            for name in wheel["entrypoints"]
        }
        expected_installed_paths = (
            expected_wheel_paths
            | generated_metadata_paths
            | generated_script_paths
            | {wheel["record_path"]}
        )
        if installed_paths != expected_installed_paths:
            raise QualificationError(
                f"Installed RECORD inventory differs: {wheel['name']}"
            )

        by_path = {entry["path"]: entry for entry in installed_entries}
        projected_wheel_entries = [
            by_path[path] for path in sorted(expected_wheel_paths)
        ]
        if (
            hashlib.sha256(canonical(projected_wheel_entries)).hexdigest()
            != wheel["content_root_sha256"]
        ):
            raise QualificationError(f"Installed wheel root differs: {wheel['name']}")

        installer_dir = root / wheel["dist_info_directory"]
        if (installer_dir / "INSTALLER").read_bytes() != b"uv" or (
            installer_dir / "REQUESTED"
        ).read_bytes() != b"":
            raise QualificationError(f"Installer metadata differs: {wheel['name']}")
        try:
            direct_url = json.loads(
                (installer_dir / "direct_url.json").read_text(encoding="utf-8")
            )
            parsed_url = urlparse(direct_url["url"])
            direct_path = Path(unquote(parsed_url.path)).resolve(strict=True)
            uv_cache = json.loads(
                (installer_dir / "uv_cache.json").read_text(encoding="utf-8")
            )
        except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise QualificationError(
                f"Installer metadata is unreadable: {wheel['name']}"
            ) from exc
        if (
            set(direct_url) != {"url", "archive_info"}
            or parsed_url.scheme != "file"
            or parsed_url.netloc not in {"", "localhost"}
            or direct_path != staged_artifact.resolve(strict=True)
            or direct_url["archive_info"] != {}
            or set(uv_cache) != {"timestamp", "commit", "tags", "env", "directories"}
            or uv_cache["commit"] is not None
            or uv_cache["tags"] is not None
            or uv_cache["env"] != {}
            or uv_cache["directories"] != {}
            or not isinstance(uv_cache["timestamp"], dict)
            or set(uv_cache["timestamp"]) != {"secs_since_epoch", "nanos_since_epoch"}
            or not all(
                isinstance(value, int) and value >= 0
                for value in uv_cache["timestamp"].values()
            )
        ):
            raise QualificationError(
                f"Installer metadata contract differs: {wheel['name']}"
            )

        normalized_inventory = [
            *[{**entry, "kind": "wheel-member"} for entry in projected_wheel_entries],
            *[
                {"path": path, "kind": "installer-metadata"}
                for path in sorted(generated_metadata_paths)
            ],
            *[
                {
                    "path": Path(os.path.relpath(scripts_root / name, root)).as_posix(),
                    "kind": "generated-entrypoint",
                    "target": wheel["entrypoints"][name],
                }
                for name in sorted(wheel["entrypoints"])
            ],
            {"path": wheel["record_path"], "kind": "installed-record-self"},
        ]
        installed_roots[wheel["name"]] = {
            "content_root_sha256": wheel["content_root_sha256"],
            "inventory_root_sha256": hashlib.sha256(
                canonical(normalized_inventory)
            ).hexdigest(),
        }
    return installed_roots


def load_manifest(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("Qualification manifest is unreadable") from exc
    if not isinstance(value, dict):
        raise QualificationError("Qualification manifest must be an object")
    artifacts = value.get("artifacts")
    distributions = value.get("distributions")
    imports = value.get("imports")
    entrypoints = value.get("entrypoints")
    if (
        value.get("schema_version") != 1
        or not isinstance(value.get("python"), str)
        or not isinstance(artifacts, list)
        or not artifacts
        or not isinstance(distributions, dict)
        or not distributions
        or not isinstance(imports, list)
        or not imports
        or not isinstance(entrypoints, list)
        or not entrypoints
    ):
        raise QualificationError("Qualification manifest shape differs")
    names: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "filename",
            "sha256",
            "source",
        }:
            raise QualificationError("Artifact contract differs")
        filename = artifact.get("filename")
        expected = artifact.get("sha256")
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or not filename.endswith(".whl")
            or filename in names
            or not isinstance(expected, str)
            or not SHA256.fullmatch(expected)
            or not isinstance(artifact.get("source"), str)
        ):
            raise QualificationError("Artifact identity is invalid")
        names.add(filename)
    if not all(
        isinstance(name, str) and isinstance(version, str) and name and version
        for name, version in distributions.items()
    ):
        raise QualificationError("Distribution contract differs")
    if not all(isinstance(name, str) and name for name in imports + entrypoints):
        raise QualificationError("Smoke contract differs")
    return value


def run(command: Sequence[str], *, label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command), check=False, capture_output=True, text=True, timeout=300
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise QualificationError(f"{label} failed: {detail}")
    return result


def qualify(
    manifest_path: Path,
    artifact_directory: Path,
    *,
    uv: Path,
    qualification_kind: str = QUALIFICATION_KINDS[0],
) -> dict[str, Any]:
    if qualification_kind not in QUALIFICATION_KINDS:
        raise QualificationError("Qualification kind is unsupported")
    manifest_bytes = read_stable_bytes(
        manifest_path,
        label="Qualification manifest",
        maximum_bytes=1024 * 1024,
    )
    manifest = load_manifest(manifest_bytes)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if not artifact_directory.is_dir() or artifact_directory.is_symlink():
        raise QualificationError("Artifact directory must be a real directory")
    with tempfile.TemporaryDirectory(prefix="sfv2-b11-qualification-") as raw:
        qualification_root = Path(raw)
        if (
            qualification_root.is_symlink()
            or stat.S_IMODE(qualification_root.stat().st_mode) & 0o077
        ):
            raise QualificationError("Qualification root is not private")
        staging = qualification_root / "artifacts"
        staging.mkdir(mode=0o700)
        environment = qualification_root / "environment"
        if environment.exists() or environment.is_symlink():
            raise QualificationError("Qualification environment already exists")

        artifact_paths: list[Path] = []
        artifact_receipts: list[dict[str, str]] = []
        wheel_projections: list[dict[str, Any]] = []
        expected_versions = {
            normalize_distribution_name(name): version
            for name, version in manifest["distributions"].items()
        }
        observed_names: set[str] = set()
        for artifact in manifest["artifacts"]:
            source = artifact_directory / artifact["filename"]
            destination = staging / artifact["filename"]
            actual = stage_artifact(source, destination, artifact["sha256"])
            projection = wheel_projection(destination)
            expected_version = expected_versions.get(projection["normalized_name"])
            if (
                projection["normalized_name"] in observed_names
                or projection["version"] != expected_version
            ):
                raise QualificationError(
                    f"Wheel identity differs: {artifact['filename']}"
                )
            observed_names.add(projection["normalized_name"])
            artifact_paths.append(destination)
            wheel_projections.append(projection)
            artifact_receipts.append(
                {
                    "filename": artifact["filename"],
                    "sha256": actual,
                    "installed_content_root_sha256": projection["content_root_sha256"],
                }
            )
        if observed_names != set(expected_versions):
            raise QualificationError("Wheel set differs from the distribution contract")
        staging_descriptor = os.open(
            staging, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(staging_descriptor)
        finally:
            os.close(staging_descriptor)

        run(
            [str(uv), "venv", "--python", manifest["python"], str(environment)],
            label="isolated environment creation",
        )
        python = environment / "bin" / "python"
        install_command = [
            str(uv),
            "pip",
            "install",
            "--python",
            str(python),
            "--no-index",
            "--no-deps",
            *[str(path) for path in artifact_paths],
        ]
        run(install_command, label="offline exact-artifact installation")
        for artifact, path in zip(manifest["artifacts"], artifact_paths, strict=True):
            if sha256(path) != artifact["sha256"]:
                raise QualificationError(
                    f"Staged artifact changed after installation: {artifact['filename']}"
                )
        installed_roots = verify_installed_projection(
            python, wheel_projections, artifact_paths
        )
        for receipt, projection in zip(
            artifact_receipts, wheel_projections, strict=True
        ):
            if (
                installed_roots.get(projection["name"], {}).get("content_root_sha256")
                != receipt["installed_content_root_sha256"]
            ):
                raise QualificationError(
                    f"Installed artifact root differs: {receipt['filename']}"
                )
            receipt["installed_inventory_root_sha256"] = installed_roots[
                projection["name"]
            ]["inventory_root_sha256"]

        probe = (
            "import importlib,importlib.metadata,json,sys;"
            f"expected={json.dumps(manifest['distributions'], sort_keys=True)!r};"
            "expected=json.loads(expected);"
            f"imports={json.dumps(manifest['imports'])!r};imports=json.loads(imports);"
            "[importlib.import_module(name) for name in imports];"
            "actual={name:importlib.metadata.version(name) for name in expected};"
            "assert actual==expected,(actual,expected);"
            "print(json.dumps({'python':sys.version.split()[0],'distributions':actual},sort_keys=True))"
        )
        probe_result = run(
            [str(python), "-I", "-c", probe],
            label="isolated import and version probe",
        )
        installed = json.loads(probe_result.stdout)
        for entrypoint in manifest["entrypoints"]:
            run(
                [str(environment / "bin" / entrypoint), "--help"],
                label=f"{entrypoint} entrypoint probe",
            )

    material: dict[str, Any] = {
        "schema_version": 1,
        "kind": qualification_kind,
        "manifest_sha256": manifest_sha256,
        "python": installed["python"],
        "artifacts": artifact_receipts,
        "distributions": installed["distributions"],
        "imports": list(manifest["imports"]),
        "entrypoints": list(manifest["entrypoints"]),
        "install_flags": ["--no-index", "--no-deps"],
        "artifact_staging": "qualification-owned-private-copy",
        "environment_posture": "qualification-owned-temporary",
        "installed_record_roots_verified": True,
        "installed_record_complete_inventory_verified": True,
        "registry_resolution_allowed": False,
        "result": "passed",
    }
    material["qualification_root_sha256"] = hashlib.sha256(
        canonical(material)
    ).hexdigest()
    return material


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--artifact-directory", type=Path, required=True)
    value.add_argument("--uv", type=Path, default=Path("/opt/homebrew/bin/uv"))
    value.add_argument(
        "--qualification-kind",
        choices=QUALIFICATION_KINDS,
        default=QUALIFICATION_KINDS[0],
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        receipt = qualify(
            args.manifest.absolute(),
            args.artifact_directory.absolute(),
            uv=args.uv.resolve(strict=True),
            qualification_kind=args.qualification_kind,
        )
    except (OSError, QualificationError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
