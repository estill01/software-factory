from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Sequence
from urllib.parse import unquote, urlsplit

from .catalog import (
    CatalogError,
    CatalogStore,
    ProjectRecord,
    default_catalog_path,
    discover_catalog,
    discover_project,
    validate_catalog_fingerprint,
    validate_project_id,
)
from .contract import API_VERSION, PACKAGE_VERSION, envelope
from .operations import (
    DEFAULT_AUTOMATIONS_ROOT,
    DEFAULT_SUPERVISION_ROOT,
    OperationsProjectionError,
    OperationsProjectionService,
)
from .tracker import (
    TrackerProjectionError,
    TrackerProjectionService,
    tracker_identity,
    unavailable_tracker,
)


MAX_BODY_BYTES = 64 * 1024
NONCE_PLACEHOLDER = "__SOFTWARE_FACTORY_MUTATION_NONCE__"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}


class DashboardConfigurationError(ValueError):
    """Raised when the local runtime would exceed its authority boundary."""


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    static_dir: Path | None = None
    catalog_path: Path | None = None
    supervision_root: Path = DEFAULT_SUPERVISION_ROOT
    automations_root: Path = DEFAULT_AUTOMATIONS_ROOT
    quiet: bool = False

    def validated(self) -> "ServerConfig":
        normalized_host = self.host.strip().lower()
        if normalized_host not in LOOPBACK_HOSTS:
            raise DashboardConfigurationError(
                "Dashboard host must be 127.0.0.1 or localhost"
            )
        if not 0 <= self.port <= 65535:
            raise DashboardConfigurationError("Dashboard port must be between 0 and 65535")
        static_dir = self.static_dir.resolve() if self.static_dir else default_static_dir()
        catalog_path = self.catalog_path or default_catalog_path()
        if not catalog_path.is_absolute() or ".." in catalog_path.parts:
            raise DashboardConfigurationError("Dashboard catalog path must be absolute and canonical")
        return ServerConfig(
            host=normalized_host,
            port=self.port,
            static_dir=static_dir,
            catalog_path=catalog_path,
            supervision_root=self.supervision_root.expanduser().resolve(),
            automations_root=self.automations_root.expanduser().resolve(),
            quiet=self.quiet,
        )


def default_static_dir() -> Path:
    dashboard_dir = Path(__file__).resolve().parents[3]
    return dashboard_dir / "web" / "dist"


def _is_loopback_hostname(hostname: str | None) -> bool:
    return bool(hostname and hostname.lower() in LOOPBACK_HOSTS)


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, config: ServerConfig, nonce: str | None = None):
        self.config = config.validated()
        self.mutation_nonce = nonce or secrets.token_urlsafe(32)
        self.catalog_store = CatalogStore(self.config.catalog_path)
        self.tracker_service = TrackerProjectionService()
        self.operations_service = OperationsProjectionService(
            supervision_root=self.config.supervision_root,
            automations_root=self.config.automations_root,
        )
        super().__init__((self.config.host, self.config.port), DashboardRequestHandler)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: DashboardHTTPServer
    server_version = "SoftwareFactoryDashboard/0.1"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        if not self.server.config.quiet:
            super().log_message(format, *args)

    def _send_security_headers(self) -> None:
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def _write(
        self,
        status: HTTPStatus,
        body: bytes,
        *,
        content_type: str,
        cache_control: str = "no-store",
    ) -> None:
        self.send_response(status.value)
        self._send_security_headers()
        self.send_header("Cache-Control", cache_control)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._write(
            status,
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            content_type="application/json; charset=utf-8",
        )

    def _error(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        self._write_json(
            status,
            envelope(
                data=None,
                source={
                    "kind": "runtime",
                    "identity": "software-factory-dashboard/http",
                    "revision": PACKAGE_VERSION,
                },
                coverage={"status": "partial", "observed": ["runtime"], "missing": []},
                limitations=[],
                error={"code": code, "message": message, "retryable": retryable},
            ),
        )

    def _request_host_is_valid(self) -> bool:
        host_header = self.headers.get("Host", "")
        try:
            parsed = urlsplit(f"//{host_header}")
            request_port = parsed.port
        except ValueError:
            return False
        if not _is_loopback_hostname(parsed.hostname):
            return False
        server_port = int(self.server.server_address[1])
        return request_port == server_port

    def _origin_matches_request(self) -> bool:
        origin = self.headers.get("Origin", "")
        host_header = self.headers.get("Host", "")
        try:
            parsed = urlsplit(origin)
        except ValueError:
            return False
        return (
            parsed.scheme == "http"
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and parsed.path in {"", "/"}
            and _is_loopback_hostname(parsed.hostname)
            and parsed.netloc.lower() == host_header.lower()
        )

    def _health(self) -> None:
        static_dir = self.server.config.static_dir
        frontend_available = bool(static_dir and (static_dir / "index.html").is_file())
        try:
            self.server.catalog_store.load()
        except CatalogError as error:
            catalog_available = False
            catalog_reason = str(error)
        else:
            catalog_available = True
            catalog_reason = None
        tracker_owner: dict[str, Any] | None = None
        try:
            tracker_owner = self.server.tracker_service.verifier_revision()
        except TrackerProjectionError as error:
            tracker_available = False
            tracker_reason = str(error)
        else:
            tracker_available = catalog_available
            tracker_reason = catalog_reason
        supervision_owner: dict[str, Any] | None = None
        try:
            supervision_owner = self.server.operations_service.readiness()
        except OperationsProjectionError as error:
            supervision_available = False
            supervision_reason = str(error)
        else:
            supervision_available = catalog_available
            supervision_reason = catalog_reason
        missing = ["codex-app-server"]
        if not frontend_available:
            missing.insert(0, "frontend-build")
        if not catalog_available:
            missing.insert(0, "project-catalog")
        if not tracker_available:
            missing.insert(0, "tracker-projection")
        if not supervision_available:
            missing.insert(0, "supervision-projection")
        data = {
            "status": "ok",
            "service": {"name": "software-factory-dashboard", "version": PACKAGE_VERSION},
            "integrations": {
                "frontend": {
                    "status": "available" if frontend_available else "unavailable",
                    "reason": None
                    if frontend_available
                    else "Build the dashboard frontend production assets.",
                },
                "project_sources": {
                    "status": "available" if catalog_available else "unavailable",
                    "reason": catalog_reason,
                },
                "tracker_sources": {
                    "status": "available" if tracker_available else "unavailable",
                    "reason": tracker_reason,
                },
                "supervision_sources": {
                    "status": "available" if supervision_available else "unavailable",
                    "reason": supervision_reason,
                },
                "codex_app_server": {
                    "status": "unavailable",
                    "reason": "Codex task integration begins in tracker Block 5.",
                },
            },
        }
        self._write_json(
            HTTPStatus.OK,
            envelope(
                data=data,
                source={
                    "kind": "runtime",
                    "identity": "software-factory-dashboard/health",
                    "revision": PACKAGE_VERSION,
                },
                coverage={
                    "status": "partial" if missing else "complete",
                    "observed": (
                        ["runtime"]
                        + (["frontend-build"] if frontend_available else [])
                        + (["project-catalog"] if catalog_available else [])
                        + (["maintained-tracker-verifier"] if tracker_available else [])
                        + (["maintained-supervision-owners"] if supervision_available else [])
                    ),
                    "missing": missing,
                },
                limitations=[
                    "Tracker adapter readiness does not establish per-tracker validity or connect supervision and task truth.",
                    f"Maintained tracker verifier revision: {tracker_owner['sha256']}."
                    if tracker_available and tracker_owner is not None
                    else "Maintained tracker verifier is unavailable.",
                    (
                        "Maintained supervision/report owner bundle: "
                        f"{supervision_owner['revision']}."
                        if supervision_available and supervision_owner is not None
                        else "Maintained supervision/report owners are unavailable."
                    ),
                ],
            ),
        )

    def _catalog_payload(self, *, include_archived: bool) -> dict[str, Any]:
        loaded = self.server.catalog_store.load()
        projects = discover_catalog(loaded, include_archived=include_archived)
        unavailable = [
            project["id"]
            for project in projects
            if project["discovery"]["status"] == "unavailable"
        ]
        limitations = [
            "This project endpoint returns tracker candidates only; use /api/v1/trackers for read-only content projection.",
            "Use /api/v1/runs for supervision truth; Codex task state remains unavailable until Block 5.",
        ]
        if loaded.recovered_from_previous:
            limitations.append("The current catalog was invalid; a valid prior file was projected read-only.")
        if unavailable:
            limitations.append(
                f"Discovery is unavailable for {len(unavailable)} project(s): {', '.join(unavailable)}."
            )
        return envelope(
            data={
                "catalog_fingerprint": loaded.fingerprint,
                "recovered_from_previous": loaded.recovered_from_previous,
                "projects": projects,
            },
            source={
                "kind": "dashboard-catalog",
                "identity": "software-factory-dashboard/project-catalog",
                "revision": loaded.fingerprint,
            },
            coverage={
                "status": "partial",
                "observed": ["catalog", "registered-git-roots", "tracker-candidate-paths"],
                "missing": ["composed-supervision-project-binding", "codex-app-server"],
            },
            limitations=limitations,
        )

    def _write_catalog(self, *, include_archived: bool, status: HTTPStatus = HTTPStatus.OK) -> None:
        try:
            payload = self._catalog_payload(include_archived=include_archived)
        except CatalogError as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(status, payload)

    def _write_project(self, project_id: str) -> None:
        try:
            validate_project_id(project_id)
            loaded = self.server.catalog_store.load()
            project = next(
                (candidate for candidate in loaded.state.projects if candidate.id == project_id),
                None,
            )
            if project is None:
                raise CatalogError(
                    "project_not_found",
                    f"Project {project_id} is not registered.",
                    status=404,
                )
            projection = discover_project(project)
            payload = envelope(
                data={
                    "catalog_fingerprint": loaded.fingerprint,
                    "recovered_from_previous": loaded.recovered_from_previous,
                    "project": projection,
                },
                source={
                    "kind": "dashboard-catalog",
                    "identity": f"software-factory-dashboard/project-catalog/{project.id}",
                    "revision": loaded.fingerprint,
                },
                coverage={
                    "status": "partial",
                    "observed": ["catalog", "registered-git-root", "tracker-candidate-paths"],
                    "missing": ["tracker-content", "composed-supervision-project-binding", "codex-app-server"],
                },
                limitations=projection["discovery"]["limitations"],
            )
        except CatalogError as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _tracker_candidates(
        self,
    ) -> tuple[list[tuple[ProjectRecord, str]], list[dict[str, Any]], str, bool]:
        loaded = self.server.catalog_store.load()
        candidates: list[tuple[ProjectRecord, str]] = []
        projects: list[dict[str, Any]] = []
        for project in loaded.state.projects:
            if project.archived:
                continue
            projection = discover_project(project)
            discovery = projection["discovery"]
            project_state = {
                "project_id": project.id,
                "status": discovery["status"],
                "observed_at": projection["observed_at"],
                "errors": discovery["errors"],
                "tracker_candidates": len(discovery["trackers"]["candidates"]),
            }
            projects.append(project_state)
            if discovery["status"] != "available":
                continue
            for relative_path in discovery["trackers"]["candidates"]:
                candidates.append((project, relative_path))
        return candidates, projects, loaded.fingerprint, loaded.recovered_from_previous

    def _tracker_list_payload(self) -> dict[str, Any]:
        candidates, projects, catalog_fingerprint, recovered = self._tracker_candidates()
        trackers: list[dict[str, Any]] = []
        paths_by_project: dict[str, tuple[ProjectRecord, list[str]]] = {}
        for project, relative_path in candidates:
            entry = paths_by_project.setdefault(project.id, (project, []))
            entry[1].append(relative_path)
        refresh_analysis_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
        for project, relative_paths in paths_by_project.values():
            outcomes = self.server.tracker_service.project_many(
                project,
                relative_paths,
                refresh_analysis_cache=refresh_analysis_cache,
            )
            for relative_path in relative_paths:
                outcome = outcomes[relative_path]
                if isinstance(outcome, TrackerProjectionError):
                    trackers.append(unavailable_tracker(project, relative_path, outcome))
                else:
                    trackers.append(self.server.tracker_service.summary(outcome))
        trackers.sort(key=lambda tracker: (tracker["project_id"], tracker["relative_path"]))
        unavailable_projects = [project["project_id"] for project in projects if project["status"] != "available"]
        unavailable_trackers = [tracker["id"] for tracker in trackers if tracker["status"] != "available"]
        git_observed = any(
            tracker["status"] == "available" and tracker["git"]["status"] == "available"
            for tracker in trackers
        )
        git_partial = any(
            tracker["status"] != "available" or tracker["git"]["status"] != "available"
            for tracker in trackers
        )
        limitations = [
            "Tracker Markdown, maintained verifier output, and Git remain authoritative.",
            "Run-bound tracker hash comparison remains unavailable until Block 4 composition.",
            "This Block exposes read APIs only; tracker workspace UI begins in Block 8.",
        ]
        if recovered:
            limitations.append("The valid prior catalog is projected read-only.")
        if unavailable_projects:
            limitations.append(
                f"Project discovery is unavailable for: {', '.join(unavailable_projects)}."
            )
        if unavailable_trackers:
            limitations.append(
                f"Tracker projection is unavailable for {len(unavailable_trackers)} candidate(s)."
            )
        try:
            verifier_revision = self.server.tracker_service.verifier_revision()
            source_revision = verifier_revision["sha256"]
        except TrackerProjectionError as error:
            verifier_revision = {
                "path": None,
                "sha256": None,
                "owning_revision": None,
                "error": {"code": error.code, "message": str(error)},
            }
            source_revision = "unavailable"
        missing = ["run-bound-tracker-hash"]
        if not candidates:
            missing.append("registered-tracker-candidates")
        if unavailable_projects:
            missing.append("project-discovery")
        if unavailable_trackers or verifier_revision["sha256"] is None:
            missing.append("tracker-projection")
        if candidates and (git_partial or not git_observed):
            missing.append("git-currentness")
        observed = ["project-catalog", "tracker-candidate-paths"]
        if verifier_revision["sha256"]:
            observed.append("maintained-verifier")
        if git_observed:
            observed.append("git-currentness")
        return envelope(
            data={
                "catalog_fingerprint": catalog_fingerprint,
                "recovered_from_previous": recovered,
                "verifier_owner": verifier_revision,
                "projects": projects,
                "trackers": trackers,
            },
            source={
                "kind": "tracker-projection",
                "identity": "software-factory-dashboard/trackers",
                "revision": source_revision,
            },
            coverage={
                "status": "partial",
                "observed": observed,
                "missing": sorted(set(missing)),
            },
            limitations=limitations,
        )

    def _write_trackers(self) -> None:
        try:
            payload = self._tracker_list_payload()
        except (CatalogError, TrackerProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_tracker(self, tracker_id: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", tracker_id):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_tracker_id", "Tracker ID is invalid.")
            return
        try:
            candidates, _, catalog_fingerprint, recovered = self._tracker_candidates()
            selected = next(
                (
                    (project, relative_path)
                    for project, relative_path in candidates
                    if tracker_identity(project.id, relative_path) == tracker_id
                ),
                None,
            )
            if selected is None:
                raise TrackerProjectionError(
                    "tracker_not_found",
                    "Tracker is not discoverable in an active registered project.",
                    status=404,
                )
            detail = self.server.tracker_service.project(*selected)
            payload = envelope(
                data={
                    "catalog_fingerprint": catalog_fingerprint,
                    "recovered_from_previous": recovered,
                    "tracker": detail,
                },
                source={
                    "kind": "tracker-projection",
                    "identity": f"software-factory-dashboard/trackers/{tracker_id}",
                    "revision": detail["fingerprint"],
                },
                coverage={
                    "status": "partial",
                    "observed": detail["coverage"]["observed"],
                    "missing": sorted(
                        set(detail["coverage"]["missing"] + ["run-bound-tracker-hash"])
                    ),
                },
                limitations=detail["limitations"],
            )
        except (CatalogError, TrackerProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _operations_snapshot(self) -> tuple[dict[str, Any], str, bool]:
        loaded = self.server.catalog_store.load()
        projects = tuple(project for project in loaded.state.projects if not project.archived)
        snapshot = self.server.operations_service.snapshot(projects)
        return snapshot, loaded.fingerprint, loaded.recovered_from_previous

    def _operations_envelope(
        self,
        *,
        identity: str,
        revision: str,
        data: dict[str, Any],
        coverage: dict[str, Any],
        limitations: list[str],
    ) -> dict[str, Any]:
        return envelope(
            data=data,
            source={
                "kind": "operations-projection",
                "identity": identity,
                "revision": revision,
            },
            coverage=coverage,
            limitations=limitations,
        )

    def _write_runs(self) -> None:
        try:
            snapshot, catalog_fingerprint, recovered = self._operations_snapshot()
            payload = self._operations_envelope(
                identity="software-factory-dashboard/runs",
                revision=snapshot["fingerprint"],
                data={
                    "catalog_fingerprint": catalog_fingerprint,
                    "recovered_from_previous": recovered,
                    "owners": snapshot["owners"],
                    "runs": snapshot["run_summaries"],
                    "attention": snapshot["attention"],
                    "orphan_automations": snapshot["orphan_automations"],
                    "unmonitored_projects": snapshot["unmonitored_projects"],
                },
                coverage=snapshot["coverage"],
                limitations=snapshot["limitations"],
            )
        except (CatalogError, OperationsProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_run(self, target_thread_id: str) -> None:
        try:
            loaded = self.server.catalog_store.load()
            projects = tuple(project for project in loaded.state.projects if not project.archived)
            snapshot = self.server.operations_service.run(projects, target_thread_id)
            payload = self._operations_envelope(
                identity=f"software-factory-dashboard/runs/{target_thread_id}",
                revision=snapshot["fingerprint"],
                data={
                    "catalog_fingerprint": loaded.fingerprint,
                    "recovered_from_previous": loaded.recovered_from_previous,
                    "owners": snapshot["owners"],
                    "run": snapshot["selected_run"],
                },
                coverage=snapshot["selected_run"]["coverage"],
                limitations=snapshot["selected_run"]["limitations"],
            )
        except (CatalogError, OperationsProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_reports(self) -> None:
        try:
            snapshot, catalog_fingerprint, recovered = self._operations_snapshot()
            payload = self._operations_envelope(
                identity="software-factory-dashboard/reports",
                revision=snapshot["fingerprint"],
                data={
                    "catalog_fingerprint": catalog_fingerprint,
                    "recovered_from_previous": recovered,
                    "owners": snapshot["owners"],
                    "reports": snapshot["reports"],
                },
                coverage=snapshot["coverage"],
                limitations=snapshot["limitations"]
                + ["Report availability or verification never establishes implementation completion."],
            )
        except (CatalogError, OperationsProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_metrics(self) -> None:
        try:
            snapshot, catalog_fingerprint, recovered = self._operations_snapshot()
            payload = self._operations_envelope(
                identity="software-factory-dashboard/metrics",
                revision=snapshot["fingerprint"],
                data={
                    "catalog_fingerprint": catalog_fingerprint,
                    "recovered_from_previous": recovered,
                    "owners": snapshot["owners"],
                    "aggregate": snapshot["metrics"]["aggregate"],
                    "per_run": snapshot["metrics"]["per_run"],
                },
                coverage=snapshot["coverage"],
                limitations=snapshot["limitations"]
                + ["Cost fields are API-equivalent estimates, not actual spend."],
            )
        except (CatalogError, OperationsProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _read_json_body(self) -> dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "json_required",
                "Catalog mutations require application/json.",
            )
            return None
        body = self._read_bounded_body()
        if body is None:
            return None
        try:
            payload = json.loads(body)
        except (UnicodeError, json.JSONDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body is not valid JSON.")
            return None
        if not isinstance(payload, dict):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request", "Request body must be an object.")
            return None
        return payload

    def _project_id_from_path(self, decoded_path: str) -> str | None:
        prefix = f"/api/{API_VERSION}/projects/"
        if not decoded_path.startswith(prefix):
            return None
        remainder = decoded_path[len(prefix) :]
        return remainder if remainder and "/" not in remainder else None

    def _handle_catalog_mutation(self, decoded_path: str) -> bool:
        collection_path = f"/api/{API_VERSION}/projects"
        project_id = self._project_id_from_path(decoded_path)
        if self.command == "POST" and decoded_path == collection_path:
            payload = self._read_json_body()
            if payload is None:
                return True
            if set(payload) != {"source_fingerprint", "project"}:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_request",
                    "Register requires exactly source_fingerprint and project.",
                )
                return True
            try:
                validate_catalog_fingerprint(payload["source_fingerprint"])
                self.server.catalog_store.register(payload["source_fingerprint"], payload["project"])
            except CatalogError as error:
                self._error(
                    HTTPStatus(error.status),
                    error.code,
                    str(error),
                    retryable=error.retryable,
                )
                return True
            self._write_catalog(include_archived=True, status=HTTPStatus.CREATED)
            return True
        if self.command == "PATCH" and project_id is not None:
            payload = self._read_json_body()
            if payload is None:
                return True
            if set(payload) - {"source_fingerprint", "action", "changes", "confirmation"}:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_request", "Unknown catalog mutation field.")
                return True
            if set(payload) < {"source_fingerprint", "action"}:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_request",
                    "Catalog mutation requires source_fingerprint and action.",
                )
                return True
            try:
                validate_catalog_fingerprint(payload["source_fingerprint"])
                action = payload["action"]
                if action == "update_presentation" and set(payload) == {
                    "source_fingerprint",
                    "action",
                    "changes",
                }:
                    self.server.catalog_store.update_presentation(
                        payload["source_fingerprint"], project_id, payload["changes"]
                    )
                elif action == "archive" and set(payload) == {
                    "source_fingerprint",
                    "action",
                    "confirmation",
                }:
                    self.server.catalog_store.set_archived(
                        payload["source_fingerprint"],
                        project_id,
                        True,
                        confirmation=payload["confirmation"],
                    )
                elif action == "unarchive" and set(payload) == {
                    "source_fingerprint",
                    "action",
                }:
                    self.server.catalog_store.set_archived(
                        payload["source_fingerprint"], project_id, False
                    )
                else:
                    raise CatalogError(
                        "unsupported_catalog_action",
                        "Catalog action or its exact fields are not supported.",
                    )
            except CatalogError as error:
                self._error(
                    HTTPStatus(error.status),
                    error.code,
                    str(error),
                    retryable=error.retryable,
                )
                return True
            self._write_catalog(include_archived=True)
            return True
        return False

    def _decoded_path(self) -> str | None:
        raw_path = urlsplit(self.path).path
        try:
            decoded = unquote(raw_path, errors="strict")
        except UnicodeError:
            return None
        if "\x00" in decoded or "\\" in decoded:
            return None
        if ".." in PurePosixPath(decoded).parts:
            return None
        return decoded

    def _serve_static(self, decoded_path: str) -> None:
        static_root = self.server.config.static_dir
        if not static_root or not static_root.is_dir():
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "frontend_unavailable",
                "The frontend production build is unavailable.",
                retryable=True,
            )
            return

        relative = decoded_path.lstrip("/")
        requested = (static_root / relative).resolve()
        try:
            requested.relative_to(static_root)
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_path", "Static path escaped its root.")
            return

        index_path = static_root / "index.html"
        if relative in {"", "app", "app/"}:
            requested = index_path
        elif not requested.is_file():
            if decoded_path.startswith("/assets/") or PurePosixPath(decoded_path).suffix:
                self._error(HTTPStatus.NOT_FOUND, "not_found", "Static asset was not found.")
                return
            requested = index_path

        if not requested.is_file():
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "frontend_unavailable",
                "The frontend entry point is unavailable.",
                retryable=True,
            )
            return

        body = requested.read_bytes()
        if requested == index_path:
            body = body.replace(NONCE_PLACEHOLDER.encode(), self.server.mutation_nonce.encode())
            content_type = "text/html; charset=utf-8"
            cache_control = "no-store"
        else:
            guessed, _ = mimetypes.guess_type(requested.name)
            content_type = guessed or "application/octet-stream"
            cache_control = (
                "public, max-age=31536000, immutable"
                if requested.parent.name == "assets"
                else "no-cache"
            )
        self._write(
            HTTPStatus.OK,
            body,
            content_type=content_type,
            cache_control=cache_control,
        )

    def _read_bounded_body(self) -> bytes | None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_content_length", "Invalid body length.")
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "body_too_large",
                f"Request bodies are limited to {MAX_BODY_BYTES} bytes.",
            )
            return None
        return self.rfile.read(length) if length else b""

    def _handle_read(self) -> None:
        if not self._request_host_is_valid():
            self._error(HTTPStatus.BAD_REQUEST, "invalid_host", "Use the bound loopback origin.")
            return
        decoded_path = self._decoded_path()
        if decoded_path is None:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_path", "Request path is invalid.")
            return
        if decoded_path == f"/api/{API_VERSION}/health":
            self._health()
            return
        if decoded_path == f"/api/{API_VERSION}/runs":
            if urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_query", "Runs does not accept query parameters.")
            else:
                self._write_runs()
            return
        run_prefix = f"/api/{API_VERSION}/runs/"
        if decoded_path.startswith(run_prefix):
            target_thread_id = decoded_path[len(run_prefix) :]
            if not target_thread_id or "/" in target_thread_id or urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_run_id", "Run target ID is invalid.")
            else:
                self._write_run(target_thread_id)
            return
        if decoded_path == f"/api/{API_VERSION}/reports":
            if urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_query", "Reports does not accept query parameters.")
            else:
                self._write_reports()
            return
        if decoded_path == f"/api/{API_VERSION}/metrics":
            if urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_query", "Metrics does not accept query parameters.")
            else:
                self._write_metrics()
            return
        if decoded_path == f"/api/{API_VERSION}/trackers":
            if urlsplit(self.path).query:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_query",
                    "Trackers does not accept query parameters in this Block.",
                )
            else:
                self._write_trackers()
            return
        tracker_prefix = f"/api/{API_VERSION}/trackers/"
        if decoded_path.startswith(tracker_prefix):
            tracker_id = decoded_path[len(tracker_prefix) :]
            if not tracker_id or "/" in tracker_id or urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_tracker_id", "Tracker ID is invalid.")
            else:
                self._write_tracker(tracker_id)
            return
        if decoded_path == f"/api/{API_VERSION}/projects":
            query = urlsplit(self.path).query
            if query in {"", "include_archived=false"}:
                self._write_catalog(include_archived=False)
            elif query == "include_archived=true":
                self._write_catalog(include_archived=True)
            else:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_query",
                    "Projects accepts only include_archived=true or false.",
                )
            return
        project_id = self._project_id_from_path(decoded_path)
        if project_id is not None:
            self._write_project(project_id)
            return
        if decoded_path.startswith("/api/"):
            self._error(HTTPStatus.NOT_FOUND, "not_found", "API route was not found.")
            return
        self._serve_static(decoded_path)

    def _handle_mutation(self) -> None:
        if not self._request_host_is_valid():
            self._error(HTTPStatus.BAD_REQUEST, "invalid_host", "Use the bound loopback origin.")
            return
        if not self._origin_matches_request():
            self._error(HTTPStatus.FORBIDDEN, "origin_rejected", "Mutation origin did not match.")
            return
        supplied_nonce = self.headers.get("X-Software-Factory-Nonce", "")
        if not secrets.compare_digest(supplied_nonce, self.server.mutation_nonce):
            self._error(HTTPStatus.FORBIDDEN, "nonce_rejected", "Mutation nonce did not match.")
            return
        decoded_path = self._decoded_path()
        if decoded_path is None:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_path", "Request path is invalid.")
            return
        if self._handle_catalog_mutation(decoded_path):
            return
        if self._read_bounded_body() is None:
            return
        self._error(
            HTTPStatus.NOT_FOUND,
            "mutation_unavailable",
            "No mutation endpoint is available for this route.",
        )

    def do_GET(self) -> None:  # noqa: N802
        self._handle_read()

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle_read()

    def do_POST(self) -> None:  # noqa: N802
        self._handle_mutation()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle_mutation()

    def do_PATCH(self) -> None:  # noqa: N802
        self._handle_mutation()

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle_mutation()


def create_server(config: ServerConfig, *, nonce: str | None = None) -> DashboardHTTPServer:
    return DashboardHTTPServer(config, nonce=nonce)


def _port(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return parsed


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--host", default="127.0.0.1")
    command.add_argument("--port", type=_port, default=8787)
    command.add_argument("--static-dir", type=Path, default=default_static_dir())
    command.add_argument("--catalog-path", type=Path, default=default_catalog_path())
    command.add_argument("--supervision-root", type=Path, default=DEFAULT_SUPERVISION_ROOT)
    command.add_argument("--automations-root", type=Path, default=DEFAULT_AUTOMATIONS_ROOT)
    command.add_argument("--quiet", action="store_true")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        server = create_server(
            ServerConfig(
                host=args.host,
                port=args.port,
                static_dir=args.static_dir,
                catalog_path=args.catalog_path,
                supervision_root=args.supervision_root,
                automations_root=args.automations_root,
                quiet=args.quiet,
            )
        )
    except DashboardConfigurationError as exc:
        parser().error(str(exc))
    address = f"http://{server.server_address[0]}:{server.server_address[1]}"
    print(f"Software Factory dashboard listening at {address}", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
