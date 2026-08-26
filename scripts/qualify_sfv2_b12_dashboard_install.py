from __future__ import annotations

import argparse
import json
import sys
from contextlib import closing
from hashlib import sha256
from importlib.metadata import distribution
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

from software_factory_dashboard.operations import DEFAULT_SUPERVISION_OWNER
from software_factory_dashboard.runtime_owners import SOFTWARE_FACTORY_PACKAGE_ROOT
from software_factory_dashboard.server import DashboardHTTPServer, ServerConfig
from software_factory_dashboard.tracker import DEFAULT_VERIFIER_PATH


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


def qualify(*, project_root: Path, static_dir: Path) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    static_dir = static_dir.resolve(strict=True)
    tracker_path = (
        project_root / "docs" / "software-factory-v2-implementation-tracker.md"
    )
    if not tracker_path.is_file() or not (static_dir / "index.html").is_file():
        raise ValueError("exact project tracker and static index are required")

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
        "installed_distributions": {
            "software-factory": distribution("software-factory").version,
            "software-factory-dashboard": distribution(
                "software-factory-dashboard"
            ).version,
        },
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
    return parser


def main() -> int:
    args = _parser().parse_args()
    print(
        json.dumps(
            qualify(project_root=args.project_root, static_dir=args.static_dir),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
