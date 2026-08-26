#!/usr/bin/env python3
"""Install and smoke-test the exact SFV2 Block 11 wheel composition offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    environment: Path,
    *,
    uv: Path,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    if not artifact_directory.is_dir() or artifact_directory.is_symlink():
        raise QualificationError("Artifact directory must be a real directory")
    artifact_paths: list[Path] = []
    artifact_receipts: list[dict[str, str]] = []
    for artifact in manifest["artifacts"]:
        path = artifact_directory / artifact["filename"]
        if path.is_symlink() or not path.is_file():
            raise QualificationError(f"Artifact is missing: {artifact['filename']}")
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise QualificationError(f"Artifact hash differs: {artifact['filename']}")
        artifact_paths.append(path.resolve(strict=True))
        artifact_receipts.append({"filename": artifact["filename"], "sha256": actual})

    run(
        [
            str(uv),
            "venv",
            "--clear",
            "--python",
            manifest["python"],
            str(environment),
        ],
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
        [str(python), "-I", "-c", probe], label="isolated import and version probe"
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
    value.add_argument("--environment", type=Path, required=True)
    value.add_argument("--uv", type=Path, default=Path("/opt/homebrew/bin/uv"))
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        receipt = qualify(
            args.manifest.resolve(strict=True),
            args.artifact_directory.resolve(strict=True),
            args.environment,
            uv=args.uv.resolve(strict=True),
        )
    except (OSError, QualificationError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
