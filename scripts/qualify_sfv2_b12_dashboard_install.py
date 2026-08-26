from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from contextlib import closing
from hashlib import sha1, sha256
from importlib.metadata import distribution
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from types import ModuleType
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

from software_factory_dashboard.operations import DEFAULT_SUPERVISION_OWNER
from software_factory_dashboard.runtime_owners import SOFTWARE_FACTORY_PACKAGE_ROOT
from software_factory_dashboard.server import DashboardHTTPServer, ServerConfig
from software_factory_dashboard.tracker import DEFAULT_VERIFIER_PATH


OFFLINE_QUALIFIER_RELATIVE_PATH = Path("scripts/qualify_sfv2_b11_install.py")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode()


def _content_projection(root: Path) -> tuple[int, int, str]:
    records: list[dict[str, Any]] = []
    total_bytes = 0
    for path in sorted(
        candidate for candidate in root.rglob("*") if candidate.is_file()
    ):
        content = path.read_bytes()
        total_bytes += len(content)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    return len(records), total_bytes, sha256(_canonical_json(records)).hexdigest()


def _get_json(origin: str, path: str) -> tuple[int, dict[str, Any]]:
    try:
        with closing(urlopen(f"{origin}{path}", timeout=15)) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def _distribution_root(name: str) -> Path:
    return Path(distribution(name).locate_file("")).resolve(strict=True)


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


def _read_stable_bytes(path: Path, *, label: str, maximum_bytes: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            raise RuntimeError(f"{label} is not a bounded regular file")
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
    value = b"".join(chunks)
    if (
        _file_identity(before) != _file_identity(after)
        or len(value) != before.st_size
        or len(value) > maximum_bytes
    ):
        raise RuntimeError(f"{label} changed while read")
    return value


def _git_blob_sha1(content: bytes) -> str:
    return sha1(
        f"blob {len(content)}\0".encode("ascii") + content, usedforsecurity=False
    ).hexdigest()


def _load_offline_qualifier(
    project_root: Path, source_revision: str
) -> tuple[ModuleType, dict[str, str]]:
    relative_path = OFFLINE_QUALIFIER_RELATIVE_PATH.as_posix()
    path = project_root / OFFLINE_QUALIFIER_RELATIVE_PATH
    if path.is_symlink():
        raise RuntimeError("offline qualifier must be a tracked regular file")
    content = _read_stable_bytes(
        path.resolve(strict=True),
        label="source-bound offline qualifier",
        maximum_bytes=1024 * 1024,
    )
    listing = _git_value(
        project_root,
        "ls-tree",
        source_revision,
        "--",
        relative_path,
    )
    try:
        metadata, listed_path = listing.split("\t", 1)
        mode, object_type, expected_blob = metadata.split()
    except ValueError as exc:
        raise RuntimeError("offline qualifier is absent from the exact source") from exc
    actual_blob = _git_blob_sha1(content)
    if (
        listed_path != relative_path
        or mode not in {"100644", "100755"}
        or object_type != "blob"
        or actual_blob != expected_blob
    ):
        raise RuntimeError("offline qualifier differs from the exact source")
    module = ModuleType("_sfv2_b12_source_bound_offline_qualifier")
    module.__file__ = str(path)
    exec(compile(content, str(path), "exec"), module.__dict__)
    return module, {
        "path": relative_path,
        "git_blob": expected_blob,
        "sha256": sha256(content).hexdigest(),
    }


def _git_value(project_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "exact Git source is unavailable")
    return result.stdout.strip()


def _bind_exact_install(
    *,
    project_root: Path,
    manifest_path: Path,
    offline_receipt_path: Path,
    artifact_directory: Path,
) -> dict[str, Any]:
    manifest_bytes = _read_stable_bytes(
        manifest_path.resolve(strict=True),
        label="dashboard qualification manifest",
        maximum_bytes=1024 * 1024,
    )
    try:
        manifest_identity = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("dashboard qualification manifest is unreadable") from exc
    if not isinstance(manifest_identity, dict):
        raise TypeError("dashboard qualification manifest must be an object")
    source_revision = _git_value(project_root, "rev-parse", "HEAD")
    source_tree = _git_value(project_root, "rev-parse", "HEAD^{tree}")
    source_status = _git_value(
        project_root, "status", "--porcelain=v1", "--untracked-files=all"
    )
    if (
        source_revision != manifest_identity.get("source_revision")
        or source_tree != manifest_identity.get("source_tree")
        or source_status
    ):
        raise RuntimeError("project checkout differs from the exact source candidate")
    qualifier, qualifier_identity = _load_offline_qualifier(
        project_root, source_revision
    )
    manifest = qualifier.load_manifest(manifest_bytes)
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    receipt_bytes = _read_stable_bytes(
        offline_receipt_path.resolve(strict=True),
        label="dashboard offline qualification receipt",
        maximum_bytes=4 * 1024 * 1024,
    )
    try:
        offline_receipt = json.loads(receipt_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("offline qualification receipt is unreadable") from exc
    if not isinstance(offline_receipt, dict):
        raise TypeError("offline qualification receipt must be an object")
    offline_material = dict(offline_receipt)
    offline_root = offline_material.pop("qualification_root_sha256", None)
    if (
        offline_receipt.get("kind") != "sfv2-b12-offline-install-qualification"
        or offline_receipt.get("result") != "passed"
        or offline_receipt.get("manifest_sha256") != manifest_sha256
        or offline_receipt.get("registry_resolution_allowed") is not False
        or sha256(qualifier.canonical(offline_material)).hexdigest() != offline_root
    ):
        raise RuntimeError("offline qualification receipt is not exact and current")

    artifact_directory = artifact_directory.resolve(strict=True)
    if artifact_directory.is_symlink() or not artifact_directory.is_dir():
        raise RuntimeError("artifact directory must be a real directory")
    source_archive = manifest.get("source_archive")
    if not isinstance(source_archive, dict) or set(source_archive) != {
        "filename",
        "sha256",
    }:
        raise RuntimeError("source archive contract is incomplete")
    expected_names = {
        *[artifact["filename"] for artifact in manifest["artifacts"]],
        source_archive["filename"],
    }
    actual_names = {
        path.name
        for path in artifact_directory.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if actual_names != expected_names:
        raise RuntimeError("artifact directory differs from the exact manifest")
    archive_path = artifact_directory / source_archive["filename"]
    if qualifier.sha256(archive_path) != source_archive["sha256"]:
        raise RuntimeError("source archive hash differs")

    expected_versions = {
        qualifier.normalize_distribution_name(name): version
        for name, version in manifest["distributions"].items()
    }
    receipt_by_filename = {
        item["filename"]: item for item in offline_receipt.get("artifacts", [])
    }
    artifact_paths: list[Path] = []
    projections: list[dict[str, Any]] = []
    for artifact in manifest["artifacts"]:
        artifact_path = artifact_directory / artifact["filename"]
        if qualifier.sha256(artifact_path) != artifact["sha256"]:
            raise RuntimeError(f"artifact hash differs: {artifact['filename']}")
        projection = qualifier.wheel_projection(artifact_path)
        if (
            expected_versions.get(projection["normalized_name"])
            != projection["version"]
        ):
            raise RuntimeError(f"artifact identity differs: {artifact['filename']}")
        artifact_paths.append(artifact_path)
        projections.append(projection)

    installed_roots = qualifier.verify_installed_projection(
        Path(sys.executable).absolute(), projections, artifact_paths
    )
    for artifact, projection in zip(manifest["artifacts"], projections, strict=True):
        receipt = receipt_by_filename.get(artifact["filename"])
        roots = installed_roots.get(projection["name"])
        if (
            not isinstance(receipt, dict)
            or receipt.get("sha256") != artifact["sha256"]
            or receipt.get("installed_content_root_sha256")
            != projection["content_root_sha256"]
            or not isinstance(roots, dict)
            or receipt.get("installed_inventory_root_sha256")
            != roots.get("inventory_root_sha256")
        ):
            raise RuntimeError(
                f"installed artifact root differs: {artifact['filename']}"
            )

    installed_distributions: dict[str, str] = {}
    for name, expected_version in manifest["distributions"].items():
        actual_version = distribution(name).version
        if actual_version != expected_version:
            raise RuntimeError(f"installed distribution differs: {name}")
        installed_distributions[name] = actual_version
    if len(installed_distributions) != len(manifest["artifacts"]):
        raise RuntimeError("installed distribution set is incomplete")

    final_source_revision = _git_value(project_root, "rev-parse", "HEAD")
    final_source_tree = _git_value(project_root, "rev-parse", "HEAD^{tree}")
    final_source_status = _git_value(
        project_root, "status", "--porcelain=v1", "--untracked-files=all"
    )
    if (
        final_source_revision != source_revision
        or final_source_tree != source_tree
        or final_source_status
    ):
        raise RuntimeError("project checkout changed during exact qualification")

    return {
        "source_revision": source_revision,
        "source_tree": source_tree,
        "offline_qualifier": qualifier_identity,
        "manifest_sha256": manifest_sha256,
        "offline_qualification_root_sha256": offline_root,
        "offline_receipt_material_sha256": sha256(
            qualifier.canonical(offline_receipt)
        ).hexdigest(),
        "installed_artifact_projection_root_sha256": sha256(
            qualifier.canonical(offline_receipt["artifacts"])
        ).hexdigest(),
        "source_archive": source_archive,
        "artifacts_verified": len(manifest["artifacts"]),
        "installed_distributions": installed_distributions,
        "installed_record_roots_verified": True,
        "registry_resolution_allowed": False,
    }


def qualify(
    *,
    project_root: Path,
    static_dir: Path,
    manifest_path: Path,
    offline_receipt_path: Path,
    artifact_directory: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    static_dir = static_dir.resolve(strict=True)
    tracker_path = (
        project_root / "docs" / "software-factory-v2-implementation-tracker.md"
    )
    if not tracker_path.is_file() or not (static_dir / "index.html").is_file():
        raise ValueError("exact project tracker and static index are required")
    exact_install = _bind_exact_install(
        project_root=project_root,
        manifest_path=manifest_path,
        offline_receipt_path=offline_receipt_path,
        artifact_directory=artifact_directory,
    )

    runtime_distribution_root = _distribution_root("software-factory")
    dashboard_distribution_root = _distribution_root("software-factory-dashboard")
    expected_runtime_package = runtime_distribution_root / "software_factory"
    if SOFTWARE_FACTORY_PACKAGE_ROOT != expected_runtime_package:
        raise RuntimeError(
            "runtime owners did not resolve from the installed distribution"
        )
    if not DEFAULT_VERIFIER_PATH.is_relative_to(expected_runtime_package):
        raise RuntimeError("tracker verifier escaped the installed runtime package")
    if not DEFAULT_SUPERVISION_OWNER.is_relative_to(expected_runtime_package):
        raise RuntimeError("supervision owner escaped the installed runtime package")

    with TemporaryDirectory(prefix="sfv2-b12-dashboard-smoke-") as temporary:
        root = Path(temporary)
        catalog_path = root / "projects.json"
        supervision_root = root / "supervision"
        automations_root = root / "automations"
        supervision_root.mkdir()
        automations_root.mkdir()
        catalog_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "projects": [
                        {
                            "id": "sfv2-smoke",
                            "label": "SFV2 installed-artifact smoke",
                            "root": str(project_root),
                            "tracker_patterns": [
                                "docs/software-factory-v2-implementation-tracker.md"
                            ],
                            "description": "read-only installed-artifact qualification",
                            "archived": False,
                        }
                    ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        catalog_path.chmod(0o600)
        server = DashboardHTTPServer(
            ServerConfig(
                host="127.0.0.1",
                port=0,
                static_dir=static_dir,
                catalog_path=catalog_path,
                supervision_root=supervision_root,
                automations_root=automations_root,
                codex_auto_start=False,
                quiet=True,
            )
        )
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            origin = f"http://{host}:{port}"
            tracker_status, trackers = _get_json(origin, "/api/v1/trackers")
            runs_status, runs = _get_json(origin, "/api/v1/runs")
            health_status, health = _get_json(origin, "/api/v1/health")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    if tracker_status != 200 or not trackers.get("data", {}).get("trackers"):
        raise RuntimeError(f"installed tracker projection failed: {trackers}")
    if runs_status != 200 or "owners" not in runs.get("data", {}):
        raise RuntimeError(f"installed supervision projection failed: {runs}")
    if health_status != 200:
        raise RuntimeError(f"installed health projection failed: {health}")

    static_files, static_bytes, static_root = _content_projection(static_dir)
    owner_revisions: dict[str, dict[str, Any]] = {}
    for key, raw_owner in runs["data"]["owners"].items():
        owner = dict(raw_owner)
        owner_path = Path(owner["path"]).resolve(strict=True)
        if not owner_path.is_relative_to(expected_runtime_package):
            raise RuntimeError(
                "supervision owner escaped the installed runtime package"
            )
        owner["path"] = owner_path.relative_to(expected_runtime_package).as_posix()
        owner_revisions[key] = owner
    return {
        "schema_version": 1,
        "kind": "sfv2-b12-installed-dashboard-qualification",
        "result": "passed",
        "python": sys.version.split()[0],
        "exact_install": exact_install,
        "installed_package_paths": {
            "software-factory": expected_runtime_package.relative_to(
                runtime_distribution_root
            ).as_posix(),
            "software-factory-dashboard": (
                dashboard_distribution_root / "software_factory_dashboard"
            )
            .relative_to(dashboard_distribution_root)
            .as_posix(),
        },
        "owners": {
            "tracker": {
                "path": DEFAULT_VERIFIER_PATH.relative_to(
                    expected_runtime_package
                ).as_posix(),
                "sha256": trackers["data"]["verifier_owner"]["sha256"],
            },
            "supervision": owner_revisions,
        },
        "http": {
            "trackers": tracker_status,
            "runs": runs_status,
            "health": health_status,
            "projected_trackers": len(trackers["data"]["trackers"]),
            "projected_runs": len(runs["data"].get("runs", [])),
        },
        "static_projection": {
            "files": static_files,
            "bytes": static_bytes,
            "root_sha256": static_root,
            "supplied_by": "--static-dir",
        },
        "posture": "isolated no-index/no-deps installed-wheel smoke; read-only loopback service",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify SFV2 dashboard projections from isolated installed wheels."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--static-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--offline-receipt", type=Path, required=True)
    parser.add_argument("--artifact-directory", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    print(
        json.dumps(
            qualify(
                project_root=args.project_root,
                static_dir=args.static_dir,
                manifest_path=args.manifest,
                offline_receipt_path=args.offline_receipt,
                artifact_directory=args.artifact_directory,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
