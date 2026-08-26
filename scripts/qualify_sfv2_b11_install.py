#!/usr/bin/env python3
"""Install and smoke-test the exact SFV2 Block 11 wheel composition offline."""

from __future__ import annotations

import argparse
import base64
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
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def wheel_projection(path: Path) -> dict[str, Any]:
    """Validate one wheel internally and project every installed payload file."""

    try:
        with zipfile.ZipFile(path) as wheel:
            names = set(wheel.namelist())
            metadata_names = [
                name for name in names if name.endswith(".dist-info/METADATA")
            ]
            record_names = [
                name for name in names if name.endswith(".dist-info/RECORD")
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
                relative_path = Path(relative)
                if (
                    relative_path.is_absolute()
                    or ".." in relative_path.parts
                    or relative_path.as_posix() != relative
                ):
                    raise QualificationError(f"Wheel path escapes: {path.name}")
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
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise QualificationError(f"Wheel is unreadable: {path.name}") from exc
    entries.sort(key=lambda item: item["path"])
    return {
        "name": metadata["Name"],
        "normalized_name": normalize_distribution_name(metadata["Name"]),
        "version": metadata["Version"],
        "entries": entries,
        "content_root_sha256": hashlib.sha256(canonical(entries)).hexdigest(),
    }


def verify_installed_projection(
    python: Path,
    wheel_projections: Sequence[dict[str, Any]],
) -> dict[str, str]:
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
    installed_roots: dict[str, str] = {}
    for wheel in wheel_projections:
        installed_entries: list[dict[str, Any]] = []
        for entry in wheel["entries"]:
            candidates = [root / entry["path"] for root in roots]
            existing = [path for path in candidates if path.exists()]
            if (
                len(existing) != 1
                or existing[0].is_symlink()
                or not existing[0].is_file()
            ):
                raise QualificationError(
                    f"Installed wheel member is missing or ambiguous: {entry['path']}"
                )
            installed = existing[0]
            if any(
                parent.is_symlink()
                for parent in installed.parents
                if parent in roots or any(parent.is_relative_to(root) for root in roots)
            ):
                raise QualificationError(
                    f"Installed wheel member is symlinked: {entry['path']}"
                )
            actual = sha256(installed)
            if actual != entry["sha256"] or installed.stat().st_size != entry["bytes"]:
                raise QualificationError(
                    f"Installed wheel content differs: {entry['path']}"
                )
            installed_entries.append(dict(entry))
        root = hashlib.sha256(canonical(installed_entries)).hexdigest()
        if root != wheel["content_root_sha256"]:
            raise QualificationError(f"Installed wheel root differs: {wheel['name']}")
        installed_roots[wheel["name"]] = root
    return installed_roots


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
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
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
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
        installed_roots = verify_installed_projection(python, wheel_projections)
        for receipt, projection in zip(
            artifact_receipts, wheel_projections, strict=True
        ):
            if (
                installed_roots.get(projection["name"])
                != receipt["installed_content_root_sha256"]
            ):
                raise QualificationError(
                    f"Installed artifact root differs: {receipt['filename']}"
                )

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
        "kind": "sfv2-b11-offline-install-qualification",
        "manifest_sha256": sha256(manifest_path),
        "python": installed["python"],
        "artifacts": artifact_receipts,
        "distributions": installed["distributions"],
        "imports": list(manifest["imports"]),
        "entrypoints": list(manifest["entrypoints"]),
        "install_flags": ["--no-index", "--no-deps"],
        "artifact_staging": "qualification-owned-private-copy",
        "environment_posture": "qualification-owned-temporary",
        "installed_record_roots_verified": True,
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
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        receipt = qualify(
            args.manifest.resolve(strict=True),
            args.artifact_directory.resolve(strict=True),
            uv=args.uv.resolve(strict=True),
        )
    except (OSError, QualificationError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
