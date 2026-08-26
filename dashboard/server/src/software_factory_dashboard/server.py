from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from threading import Lock
from time import monotonic
from typing import Any, Sequence
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .admin_operations import OperationCoordinator, OperationError, OperationRegistry
from .app_server import AppServerError, CodexAppServerClient
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
from .factory_workflows import build_factory_operation_registry
from .floor import compose_factory_floor
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
FLOOR_CACHE_SECONDS = 2.0
MAX_TRACKER_SOURCE_LINES = 5_000
MAX_INLINE_REPORT_BYTES = 2 * 1024 * 1024


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
    codex_client_wheel: Path | None = None
    codex_executable: Path | None = None
    codex_home: Path | None = None
    codex_auto_start: bool = True
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
            codex_client_wheel=(
                self.codex_client_wheel.expanduser() if self.codex_client_wheel else None
            ),
            codex_executable=(self.codex_executable.expanduser() if self.codex_executable else None),
            codex_home=(self.codex_home.expanduser() if self.codex_home else None),
            codex_auto_start=self.codex_auto_start,
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

    def __init__(
        self,
        config: ServerConfig,
        nonce: str | None = None,
        operation_registry: OperationRegistry | None = None,
    ):
        self.config = config.validated()
        self.mutation_nonce = nonce or secrets.token_urlsafe(32)
        self.catalog_store = CatalogStore(self.config.catalog_path)
        self.tracker_service = TrackerProjectionService()
        self.operations_service = OperationsProjectionService(
            supervision_root=self.config.supervision_root,
            automations_root=self.config.automations_root,
        )
        self.floor_cache_lock = Lock()
        self.floor_cache: tuple[float, dict[str, Any]] | None = None
        super().__init__((self.config.host, self.config.port), DashboardRequestHandler)
        self.app_server_client = CodexAppServerClient(
            wheel_path=self.config.codex_client_wheel,
            codex_executable=self.config.codex_executable,
            codex_home=self.config.codex_home,
            auto_start=self.config.codex_auto_start,
        )
        registry = operation_registry or build_factory_operation_registry(
            catalog_store=self.catalog_store,
            tracker_service=self.tracker_service,
            operations_service=self.operations_service,
            app_server_client=self.app_server_client,
            supervision_root=self.config.supervision_root,
        )
        self.operation_coordinator = OperationCoordinator(registry)

    def server_close(self) -> None:
        self.app_server_client.close()
        super().server_close()

    def handle_error(self, request: Any, client_address: Any) -> None:
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


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
        content_disposition: str | None = None,
    ) -> None:
        try:
            self.send_response(status.value)
            self._send_security_headers()
            self.send_header("Cache-Control", cache_control)
            self.send_header("Content-Type", content_type)
            if content_disposition is not None:
                self.send_header("Content-Disposition", content_disposition)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.close_connection = True

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

    def _event_stream_source_is_valid(self) -> bool:
        if self._origin_matches_request():
            return True
        return (
            not self.headers.get("Origin")
            and self._request_host_is_valid()
            and self.headers.get("Sec-Fetch-Site") == "same-origin"
            and self.headers.get("Sec-Fetch-Mode") == "cors"
            and self.headers.get("Sec-Fetch-Dest") == "empty"
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
        app_server_state = self.server.app_server_client.integration_state()
        app_server_available = app_server_state["status"] == "available"
        app_server_reason = (
            None
            if app_server_available
            else (
                app_server_state["last_error"]["message"]
                if app_server_state["last_error"] is not None
                else "Codex App Server is not connected."
            )
        )
        missing = [] if app_server_available else ["codex-app-server"]
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
                    "status": "available" if app_server_available else "unavailable",
                    "reason": app_server_reason,
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
                        + (["codex-app-server"] if app_server_available else [])
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
                    (
                        "Qualified shared-client schema root: "
                        f"{app_server_state['schema']['schema_tree_root_sha256']}."
                        if app_server_available
                        else "Codex App Server task controls are unavailable and file-backed monitoring remains independent."
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
            "Use /api/v1/runs for supervision truth and /api/v1/tasks for Codex task state.",
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
                include_diff_preview=False,
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
            "Run binding remains in the run API; this tracker projection does not infer it.",
            "Tracker reads are immutable; workspace controls are not exposed by this endpoint.",
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

    def _tracker_selection(
        self,
        tracker_id: str,
        candidates: Sequence[tuple[ProjectRecord, str]] | None = None,
    ) -> tuple[ProjectRecord, str]:
        if not re.fullmatch(r"[0-9a-f]{64}", tracker_id):
            raise TrackerProjectionError(
                "invalid_tracker_id",
                "Tracker ID is invalid.",
                status=400,
            )
        if candidates is None:
            candidates, _, _, _ = self._tracker_candidates()
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
        return selected

    def _write_tracker(self, tracker_id: str) -> None:
        try:
            candidates, _, catalog_fingerprint, recovered = self._tracker_candidates()
            selected = self._tracker_selection(tracker_id, candidates)
            detail = self.server.tracker_service.project(
                *selected,
                include_diff_preview=False,
            )
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

    def _write_tracker_source(self, tracker_id: str, query: str) -> None:
        try:
            selected = self._tracker_selection(tracker_id)
            parsed: dict[str, list[str]] = {}
            if query:
                parsed = parse_qs(query, keep_blank_values=True, strict_parsing=True)
                allowed = {"line", "end_line", "revision", "content_sha256"}
                if not set(parsed).issubset(allowed) or any(
                    len(values) != 1 for values in parsed.values()
                ):
                    raise TrackerProjectionError(
                        "invalid_source_range",
                        "Tracker source accepts bounded line fields and at most one exact source identity.",
                    )
                if ({"line", "end_line"} & set(parsed)) not in (set(), {"line", "end_line"}):
                    raise TrackerProjectionError(
                        "invalid_source_range",
                        "Tracker source line and end_line must be provided together.",
                    )
                if "revision" in parsed and "content_sha256" in parsed:
                    raise TrackerProjectionError(
                        "invalid_source_identity",
                        "Tracker source accepts either a Git revision or a working-content hash, not both.",
                    )
            if "revision" in parsed:
                tracker = self.server.tracker_service.source_at_revision(
                    *selected,
                    parsed["revision"][0],
                )
            else:
                tracker = self.server.tracker_service.source(*selected)
                expected_content = parsed.get("content_sha256", [None])[0]
                if expected_content is not None:
                    if not re.fullmatch(r"[0-9a-f]{64}", expected_content):
                        raise TrackerProjectionError(
                            "invalid_source_identity",
                            "Working tracker source identity must be a lowercase SHA-256 digest.",
                        )
                    if tracker.content_sha256 != expected_content:
                        raise TrackerProjectionError(
                            "tracker_source_changed",
                            "Working tracker source changed after the semantic comparison; refresh before review.",
                            status=409,
                            retryable=True,
                        )
            if "line" not in parsed:
                body = tracker.content
            else:
                try:
                    line = int(parsed["line"][0])
                    end_line = int(parsed["end_line"][0])
                except ValueError as exc:
                    raise TrackerProjectionError(
                        "invalid_source_range",
                        "Tracker source line bounds must be integers.",
                    ) from exc
                source_lines = tracker.text.splitlines(keepends=True)
                if (
                    line < 1
                    or end_line < line
                    or end_line > len(source_lines)
                    or end_line - line + 1 > MAX_TRACKER_SOURCE_LINES
                ):
                    raise TrackerProjectionError(
                        "invalid_source_range",
                        f"Tracker source range must be within the file and at most {MAX_TRACKER_SOURCE_LINES} lines.",
                    )
                body = "".join(source_lines[line - 1 : end_line]).encode("utf-8")
        except (CatalogError, TrackerProjectionError, ValueError) as error:
            status = getattr(error, "status", 400)
            code = getattr(error, "code", "invalid_source_range")
            retryable = getattr(error, "retryable", False)
            self._error(HTTPStatus(status), code, str(error), retryable=retryable)
            return
        self._write(
            HTTPStatus.OK,
            body,
            content_type="text/markdown; charset=utf-8",
            cache_control="no-store",
        )

    def _write_tracker_diff(self, tracker_id: str) -> None:
        try:
            selected = self._tracker_selection(tracker_id)
            projected = self.server.tracker_service.diff(*selected)
            diff = projected["diff"]
            semantic = diff["semantic"]
            complete = bool(
                diff["status"] == "available"
                and not diff["truncated"]
                and semantic
                and semantic["status"] == "available"
                and semantic["complete"]
            )
            payload = envelope(
                data=projected,
                source={
                    "kind": "tracker-git-diff",
                    "identity": f"software-factory-dashboard/trackers/{tracker_id}/diff",
                    "revision": projected["content_sha256"],
                },
                coverage={
                    "status": "complete" if complete else "partial",
                    "observed": ["tracker-working-content"]
                    + (["git-head-diff"] if diff["status"] == "available" else [])
                    + (["tracker-semantic-diff"] if semantic and semantic["status"] == "available" else []),
                    "missing": [] if complete else ["complete-untruncated-semantic-diff"],
                },
                limitations=[
                    "The response is a bounded read-only comparison; tracker and Git identities must match the detail snapshot.",
                    *(semantic["limitations"] if semantic else []),
                ],
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
                    "terminal_workflows": snapshot["terminal_workflows"],
                    "evolution_workflows": snapshot["evolution_workflows"],
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

    @staticmethod
    def _report_artifact_url(
        target_thread_id: str,
        family: str,
        report_id: str,
        member_name: str,
        *,
        download: bool = False,
    ) -> str:
        segments = (
            target_thread_id,
            family,
            report_id,
            "artifacts",
            member_name,
        )
        path = f"/api/{API_VERSION}/reports/" + "/".join(
            quote(segment, safe="") for segment in segments
        )
        return f"{path}?download=true" if download else path

    def _write_report(
        self,
        target_thread_id: str,
        family: str,
        report_id: str,
    ) -> None:
        try:
            snapshot = self.server.operations_service.report(
                self._active_projects(), target_thread_id, family, report_id
            )
            report = snapshot["selected_report"]
            verified = report["status"] == "available" and isinstance(
                report.get("verification"), dict
            )
            artifacts = []
            for member in report["members"]:
                supported = member["media_type"] in {
                    "application/json",
                    "application/pdf",
                    "text/markdown",
                }
                previewable = verified and supported and member["bytes"] <= MAX_INLINE_REPORT_BYTES
                downloadable = verified and supported
                artifacts.append(
                    {
                        **member,
                        "previewable": previewable,
                        "preview_url": self._report_artifact_url(
                            target_thread_id,
                            family,
                            report_id,
                            member["name"],
                        )
                        if previewable
                        else None,
                        "download_url": self._report_artifact_url(
                            target_thread_id,
                            family,
                            report_id,
                            member["name"],
                            download=True,
                        )
                        if downloadable
                        else None,
                    }
                )
            payload = self._operations_envelope(
                identity=(
                    "software-factory-dashboard/reports/"
                    f"{target_thread_id}/{family}/{report_id}"
                ),
                revision=report["manifest_root"] or snapshot["fingerprint"],
                data={
                    "owners": snapshot["owners"],
                    "report": {**report, "artifacts": artifacts},
                },
                coverage=snapshot["coverage"],
                limitations=snapshot["limitations"]
                + [
                    "Artifact URLs are exact same-origin reads from the currently verified bundle; no report is generated or adopted.",
                    "Unavailable or partial report sets remain inspectable as metadata but their members are not served.",
                ],
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

    def _write_report_artifact(
        self,
        target_thread_id: str,
        family: str,
        report_id: str,
        member_name: str,
        query: str,
    ) -> None:
        if query not in {"", "download=true"}:
            self._error(
                HTTPStatus.BAD_REQUEST,
                "invalid_query",
                "Report artifacts accept only download=true.",
            )
            return
        try:
            raw, member = self.server.operations_service.report_member(
                self._active_projects(),
                target_thread_id,
                family,
                report_id,
                member_name,
            )
        except (CatalogError, OperationsProjectionError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        disposition = "attachment" if query == "download=true" else "inline"
        self._write(
            HTTPStatus.OK,
            raw,
            content_type=f"{member['media_type']}; charset=utf-8"
            if member["media_type"] != "application/pdf"
            else "application/pdf",
            cache_control="no-store",
            content_disposition=f'{disposition}; filename="{member_name}"',
        )

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
                    "factory_history": snapshot["metrics"]["factory_history"],
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

    @staticmethod
    def _floor_source(
        *,
        family: str,
        label: str,
        status: str,
        identity: str,
        revision: str | None,
        observed_at: str,
        reason: str,
        coverage: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "family": family,
            "label": label,
            "status": status,
            "identity": identity,
            "revision": revision,
            "observed_at": observed_at,
            "reason": reason,
            "coverage": coverage,
        }

    def _build_factory_floor_payload(self) -> dict[str, Any]:
        observed_at = datetime.now(UTC).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )
        source_health: list[dict[str, Any]] = []
        active_projects: tuple[ProjectRecord, ...] = ()
        project_views: list[dict[str, Any]] = []
        discoveries: dict[str, dict[str, Any]] = {}
        catalog_fingerprint: str | None = None
        recovered = False

        try:
            loaded = self.server.catalog_store.load()
            active_projects = tuple(
                project for project in loaded.state.projects if not project.archived
            )
            catalog_fingerprint = loaded.fingerprint
            recovered = loaded.recovered_from_previous
            discovered = [discover_project(project) for project in active_projects]
            discoveries = {str(project["id"]): project for project in discovered}
            unavailable_projects = [
                project for project in discovered if project["discovery"]["status"] != "available"
            ]
            project_views = [
                {
                    "id": project["id"],
                    "label": project["label"],
                    "status": project["discovery"]["status"],
                    "observed_at": project["observed_at"],
                }
                for project in discovered
            ]
            catalog_status = "partial" if unavailable_projects else "available"
            catalog_reason = (
                f"{len(unavailable_projects)} registered project root(s) are unavailable."
                if unavailable_projects
                else "Active registered project roots were read successfully."
            )
            source_health.append(
                self._floor_source(
                    family="catalog",
                    label="Project catalog",
                    status=catalog_status,
                    identity="software-factory-dashboard/project-catalog",
                    revision=loaded.fingerprint,
                    observed_at=observed_at,
                    reason=catalog_reason,
                    coverage={
                        "status": "partial" if unavailable_projects else "complete",
                        "observed": [project["id"] for project in discovered if project["discovery"]["status"] == "available"],
                        "missing": [project["id"] for project in unavailable_projects],
                    },
                )
            )
        except CatalogError as error:
            source_health.append(
                self._floor_source(
                    family="catalog",
                    label="Project catalog",
                    status="unavailable",
                    identity="software-factory-dashboard/project-catalog",
                    revision=None,
                    observed_at=observed_at,
                    reason=str(error),
                    coverage={"status": "partial", "observed": [], "missing": ["catalog"]},
                )
            )

        operations: dict[str, Any] | None = None
        try:
            operations = self.server.operations_service.snapshot(active_projects)
            source_health.append(
                self._floor_source(
                    family="operations",
                    label="Supervision",
                    status="available",
                    identity="supervise-tracker-runs/operations",
                    revision=operations["fingerprint"],
                    observed_at=observed_at,
                    reason="Current mission-scoped supervision owners were projected.",
                    coverage=operations["coverage"],
                )
            )
        except OperationsProjectionError as error:
            source_health.append(
                self._floor_source(
                    family="operations",
                    label="Supervision",
                    status="unavailable",
                    identity="supervise-tracker-runs/operations",
                    revision=None,
                    observed_at=observed_at,
                    reason=str(error),
                    coverage={
                        "status": "partial",
                        "observed": [],
                        "missing": ["supervision"],
                    },
                )
            )

        trackers: list[dict[str, Any]] = []
        tracker_failures = 0
        if catalog_fingerprint is None:
            source_health.append(
                self._floor_source(
                    family="trackers",
                    label="Trackers",
                    status="unavailable",
                    identity="software-factory-dashboard/trackers",
                    revision=None,
                    observed_at=observed_at,
                    reason="Tracker candidates require the unavailable project catalog.",
                    coverage={
                        "status": "partial",
                        "observed": [],
                        "missing": ["tracker-candidates", "tracker-content"],
                    },
                )
            )
        else:
            refresh_analysis_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
            for project in active_projects:
                discovery = discoveries[project.id]
                if discovery["discovery"]["status"] != "available":
                    tracker_failures += 1
                    continue
                paths = discovery["discovery"]["trackers"]["candidates"]
                outcomes = self.server.tracker_service.project_many(
                    project,
                    paths,
                    include_diff_preview=False,
                    refresh_analysis_cache=refresh_analysis_cache,
                )
                for path in paths:
                    outcome = outcomes[path]
                    if isinstance(outcome, TrackerProjectionError):
                        tracker_failures += 1
                        trackers.append(unavailable_tracker(project, path, outcome))
                    else:
                        trackers.append(outcome)
            trackers.sort(key=lambda item: (str(item["project_id"]), str(item["relative_path"])))
            try:
                verifier = self.server.tracker_service.verifier_revision()
                tracker_revision = verifier["sha256"]
            except TrackerProjectionError as error:
                tracker_failures += 1
                tracker_revision = None
                tracker_reason = str(error)
            else:
                tracker_reason = (
                    f"{tracker_failures} tracker or project source(s) are unavailable."
                    if tracker_failures
                    else "Discovered tracker candidates were projected by the maintained verifier."
                )
            source_health.append(
                self._floor_source(
                    family="trackers",
                    label="Trackers",
                    status="partial" if tracker_failures else "available",
                    identity="software-factory-dashboard/trackers",
                    revision=tracker_revision,
                    observed_at=observed_at,
                    reason=tracker_reason,
                    coverage={
                        "status": "partial" if tracker_failures else "complete",
                        "observed": [tracker["id"] for tracker in trackers if tracker["status"] == "available"],
                        "missing": [tracker["id"] for tracker in trackers if tracker["status"] != "available"],
                    },
                )
            )

        task_data: dict[str, Any] | None = None
        try:
            task_data = self.server.app_server_client.list_tasks(active_projects, limit=100)
            integration = task_data["integration"]
            source_health.append(
                self._floor_source(
                    family="tasks",
                    label="Codex tasks",
                    status="available",
                    identity="codex-app-server/task-list",
                    revision=integration["revision"],
                    observed_at=integration["observed_at"],
                    reason="The version-gated task page was read successfully.",
                    coverage={
                        "status": "partial" if task_data.get("next_cursor") else "complete",
                        "observed": ["task-list-page"],
                        "missing": ["later-task-pages"] if task_data.get("next_cursor") else [],
                    },
                )
            )
        except AppServerError as error:
            state = self.server.app_server_client.integration_state()
            source_health.append(
                self._floor_source(
                    family="tasks",
                    label="Codex tasks",
                    status="unavailable",
                    identity="codex-app-server/task-list",
                    revision=state["revision"],
                    observed_at=state["observed_at"],
                    reason=str(error),
                    coverage={
                        "status": "partial",
                        "observed": [],
                        "missing": ["codex-task-state"],
                    },
                )
            )

        floor = compose_factory_floor(
            projects=project_views,
            operations=operations,
            trackers=trackers,
            task_data=task_data,
            source_health=source_health,
            observed_at=observed_at,
        )
        observed_families = [
            source["family"] for source in source_health if source["status"] != "unavailable"
        ]
        missing_families = [
            source["family"]
            for source in source_health
            if source["status"] != "available"
            or source["coverage"]["status"] != "complete"
        ]
        return envelope(
            data={
                "catalog_fingerprint": catalog_fingerprint,
                "recovered_from_previous": recovered,
                **floor,
            },
            source={
                "kind": "factory-floor-composition",
                "identity": "software-factory-dashboard/factory-floor",
                "revision": floor["fingerprint"],
            },
            coverage={
                "status": "partial" if missing_families else "complete",
                "observed": observed_families,
                "missing": missing_families,
            },
            limitations=[
                "The Factory Floor composes existing read owners and stores no operational state.",
                "Tracker association remains candidate or ambiguous unless a canonical run binding exists.",
                "Task pages and recent records are bounded; truncation is explicit.",
                "Operating lights are transparent derived posture and never completion state.",
                "API-equivalent cost is an estimate, not actual spend.",
            ],
        )

    def _factory_floor_payload(self) -> dict[str, Any]:
        with self.server.floor_cache_lock:
            now = monotonic()
            cached = self.server.floor_cache
            if cached is not None and now - cached[0] <= FLOOR_CACHE_SECONDS:
                return cached[1]
            payload = self._build_factory_floor_payload()
            self.server.floor_cache = (monotonic(), payload)
            return payload

    def _write_factory_floor(self) -> None:
        self._write_json(HTTPStatus.OK, self._factory_floor_payload())

    def _active_projects(self) -> tuple[ProjectRecord, ...]:
        loaded = self.server.catalog_store.load()
        return tuple(project for project in loaded.state.projects if not project.archived)

    def _task_envelope(
        self,
        *,
        identity: str,
        data: dict[str, Any],
        limitations: list[str] | None = None,
    ) -> dict[str, Any]:
        state = self.server.app_server_client.integration_state()
        available = state["status"] == "available"
        return envelope(
            data=data,
            source={
                "kind": "codex-app-server",
                "identity": identity,
                "revision": state["revision"],
            },
            coverage={
                "status": "complete" if available else "partial",
                "observed": ["codex-app-server"] if available else [],
                "missing": [] if available else ["codex-app-server"],
            },
            limitations=(limitations or [])
            + [
                "Task state comes from the exact version-gated Codex App Server and is not a dashboard ledger.",
                "Project binding uses canonical task cwd only; absent or ambiguous bindings are never guessed.",
            ],
        )

    def _write_task_integration(self) -> None:
        state = self.server.app_server_client.integration_state()
        self._write_json(
            HTTPStatus.OK,
            self._task_envelope(
                identity="software-factory-dashboard/task-integration",
                data={"integration": state},
                limitations=[
                    "Restart affects only the dashboard-owned App Server child process.",
                    "Unavailable mutation features do not disable file-backed project, tracker, or supervision reads.",
                ],
            ),
        )

    def _write_tasks(self, query: str) -> None:
        try:
            parsed = parse_qs(query, keep_blank_values=True, strict_parsing=True) if query else {}
            if set(parsed) - {"cursor", "limit"} or any(len(values) != 1 for values in parsed.values()):
                raise AppServerError(
                    "invalid_task_query",
                    "Tasks accepts at most one cursor and one limit.",
                    status=400,
                )
            cursor = parsed.get("cursor", [None])[0]
            raw_limit = parsed.get("limit", ["50"])[0]
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError) as exc:
                raise AppServerError(
                    "invalid_task_page_limit",
                    "Task page limit must be an integer.",
                    status=400,
                ) from exc
            data = self.server.app_server_client.list_tasks(
                self._active_projects(), cursor=cursor, limit=limit
            )
            payload = self._task_envelope(
                identity="software-factory-dashboard/tasks",
                data=data,
                limitations=["Task list pages are bounded to 100 records and use opaque owner cursors."],
            )
        except (CatalogError, AppServerError, ValueError) as error:
            if isinstance(error, (CatalogError, AppServerError)):
                self._error(
                    HTTPStatus(error.status),
                    error.code,
                    str(error),
                    retryable=error.retryable,
                )
            else:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_task_query", "Task query is invalid.")
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_task(self, task_id: str, query: str) -> None:
        try:
            if query not in {"", "include_turns=true", "include_turns=false"}:
                raise AppServerError(
                    "invalid_task_query",
                    "Task detail accepts only include_turns=true or false.",
                    status=400,
                )
            data = self.server.app_server_client.read_task(
                self._active_projects(),
                task_id,
                include_turns=query != "include_turns=false",
            )
            payload = self._task_envelope(
                identity=f"software-factory-dashboard/tasks/{task_id}",
                data=data,
                limitations=[
                    "Turns and items are bounded; truncation is reported on the affected task or turn."
                ],
            )
        except (CatalogError, AppServerError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(HTTPStatus.OK, payload)

    def _write_task_events(self, query: str) -> None:
        if self.command != "GET":
            self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", "Task events require GET.")
            return
        if not self._event_stream_source_is_valid():
            self._error(HTTPStatus.FORBIDDEN, "origin_rejected", "Event-stream origin did not match.")
            return
        supplied_nonce = self.headers.get("X-Software-Factory-Nonce", "")
        if not secrets.compare_digest(supplied_nonce, self.server.mutation_nonce):
            self._error(HTTPStatus.FORBIDDEN, "nonce_rejected", "Event-stream nonce did not match.")
            return
        try:
            parsed = parse_qs(query, keep_blank_values=True, strict_parsing=True) if query else {}
            if set(parsed) - {"after"} or any(len(values) != 1 for values in parsed.values()):
                raise ValueError
            sequence = int(parsed.get("after", ["0"])[0])
            if sequence < 0:
                raise ValueError
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_event_cursor", "Event cursor is invalid.")
            return
        self.send_response(HTTPStatus.OK.value)
        self._send_security_headers()
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            replay = self.server.app_server_client.events.replay_state(sequence)
            ready = json.dumps(
                {
                    "sequence": sequence,
                    "type": "ready",
                    "observed_at": datetime.now(UTC)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                    "replay": replay,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
            self.wfile.write(f"event: ready\ndata: {ready}\n\n".encode("utf-8"))
            self.wfile.flush()
            reported_gap = (
                (replay["oldest_available"], replay["latest_available"])
                if replay["truncated"]
                else None
            )
            while True:
                replay, events = self.server.app_server_client.events.replay_after(
                    sequence, timeout=15.0
                )
                if not events:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue
                gap = (replay["oldest_available"], replay["latest_available"])
                if replay["truncated"] and gap != reported_gap:
                    replay_gap = json.dumps(
                        {
                            "sequence": sequence,
                            "type": "replay_gap",
                            "observed_at": datetime.now(UTC)
                            .isoformat(timespec="milliseconds")
                            .replace("+00:00", "Z"),
                            "replay": replay,
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    self.wfile.write(
                        f"event: replay_gap\ndata: {replay_gap}\n\n".encode("utf-8")
                    )
                reported_gap = gap if replay["truncated"] else None
                for event in events:
                    sequence = int(event["sequence"])
                    body = json.dumps(event, separators=(",", ":"), sort_keys=True)
                    self.wfile.write(
                        f"id: {sequence}\nevent: {event['type']}\ndata: {body}\n\n".encode(
                            "utf-8"
                        )
                    )
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _write_task_operation(
        self,
        identity: str,
        data: dict[str, Any],
        *,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self._write_json(
            status,
            self._task_envelope(
                identity=identity,
                data=data,
                limitations=[
                    "An applied task operation is not tracker acceptance, supervision lifecycle, or implementation completion."
                ],
            ),
        )

    def _operation_envelope(
        self,
        *,
        identity: str,
        data: dict[str, Any],
        limitations: list[str] | None = None,
    ) -> dict[str, Any]:
        framework = self.server.operation_coordinator.framework()
        revision = sha256(
            json.dumps(
                {
                    "registered_operations": framework["registered_operations"],
                    "activity": framework["activity"],
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return envelope(
            data=data,
            source={
                "kind": "administrative-operation",
                "identity": identity,
                "revision": revision,
            },
            coverage={
                "status": "partial",
                "observed": ["ephemeral-operation-state", "closed-operation-registry"],
                "missing": ["prior-server-session-operation-state"],
            },
            limitations=(
                limitations
                or [
                    "Operation activity is process-local and is not a second durable ledger.",
                    "An applied operation postcondition is not eventual workflow or implementation completion.",
                ]
            ),
        )

    def _write_operation_framework(self) -> None:
        framework = self.server.operation_coordinator.framework()
        self._write_json(
            HTTPStatus.OK,
            self._operation_envelope(
                identity="software-factory-dashboard/operations",
                data={"framework": framework},
            ),
        )

    def _write_operation(self, operation_id: str) -> None:
        try:
            operation = self.server.operation_coordinator.get(operation_id)
        except OperationError as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return
        self._write_json(
            HTTPStatus.OK,
            self._operation_envelope(
                identity=f"software-factory-dashboard/operations/{operation_id}",
                data=operation,
            ),
        )

    def _handle_admin_operation_mutation(self, decoded_path: str) -> bool:
        preview_path = f"/api/{API_VERSION}/operations/preview"
        execute_path = f"/api/{API_VERSION}/operations/execute"
        operation_prefix = f"/api/{API_VERSION}/operations/"
        try:
            if self.command == "POST" and decoded_path == preview_path:
                payload = self._read_json_body()
                if payload is None:
                    return True
                data = self.server.operation_coordinator.preview(payload)
                self._write_json(
                    HTTPStatus.CREATED,
                    self._operation_envelope(
                        identity="software-factory-dashboard/operations/preview",
                        data=data,
                        limitations=[
                            "Preview resolves current sources and route gates but performs no owner mutation.",
                            "The token expires and is bound to the exact operation, target, input, source fingerprint, and route-gate result.",
                        ],
                    ),
                )
                return True
            if self.command == "POST" and decoded_path == execute_path:
                payload = self._read_json_body()
                if payload is None:
                    return True
                data = self.server.operation_coordinator.execute(payload)
                self._write_json(
                    HTTPStatus.OK,
                    self._operation_envelope(
                        identity="software-factory-dashboard/operations/execute",
                        data=data,
                    ),
                )
                return True
            if (
                self.command == "POST"
                and decoded_path.startswith(operation_prefix)
                and decoded_path.endswith("/cancel")
            ):
                operation_id = decoded_path[len(operation_prefix) : -len("/cancel")]
                if not operation_id or "/" in operation_id:
                    raise OperationError("invalid_operation_id", "Operation ID is invalid.")
                payload = self._read_json_body()
                if payload is None:
                    return True
                data = self.server.operation_coordinator.cancel(operation_id, payload)
                self._write_json(
                    HTTPStatus.OK,
                    self._operation_envelope(
                        identity=f"software-factory-dashboard/operations/{operation_id}/cancel",
                        data=data,
                    ),
                )
                return True
            return False
        except OperationError as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return True

    def _handle_task_mutation(self, decoded_path: str) -> bool:
        try:
            if self.command == "POST" and decoded_path == f"/api/{API_VERSION}/task-integration/restart":
                payload = self._read_json_body()
                if payload is None:
                    return True
                if payload != {"confirmation": "restart-codex-adapter"}:
                    raise AppServerError(
                        "restart_confirmation_required",
                        "Restart requires the exact adapter confirmation.",
                        status=400,
                    )
                state = self.server.app_server_client.restart()
                self._write_task_operation(
                    "software-factory-dashboard/task-integration/restart",
                    {"integration": state, "operation": "adapter_restarted"},
                )
                return True
            return False
        except (CatalogError, AppServerError) as error:
            self._error(
                HTTPStatus(error.status),
                error.code,
                str(error),
                retryable=error.retryable,
            )
            return True

    def _read_json_body(self) -> dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "json_required",
                "Dashboard mutations require application/json.",
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
        if decoded_path == f"/api/{API_VERSION}/factory-floor":
            if urlsplit(self.path).query:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_query",
                    "Factory Floor does not accept query parameters.",
                )
            else:
                self._write_factory_floor()
            return
        if decoded_path == f"/api/{API_VERSION}/task-integration":
            if urlsplit(self.path).query:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_query",
                    "Task integration does not accept query parameters.",
                )
            else:
                self._write_task_integration()
            return
        if decoded_path == f"/api/{API_VERSION}/task-events":
            self._write_task_events(urlsplit(self.path).query)
            return
        if decoded_path == f"/api/{API_VERSION}/tasks":
            self._write_tasks(urlsplit(self.path).query)
            return
        task_prefix = f"/api/{API_VERSION}/tasks/"
        if decoded_path.startswith(task_prefix):
            task_id = decoded_path[len(task_prefix) :]
            if not task_id or "/" in task_id:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_task_id", "Task ID is invalid.")
            else:
                self._write_task(task_id, urlsplit(self.path).query)
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
        report_prefix = f"/api/{API_VERSION}/reports/"
        if decoded_path.startswith(report_prefix):
            suffix = decoded_path[len(report_prefix) :]
            parts = suffix.split("/")
            if len(parts) == 3 and all(parts):
                if urlsplit(self.path).query:
                    self._error(
                        HTTPStatus.BAD_REQUEST,
                        "invalid_query",
                        "Report detail does not accept query parameters.",
                    )
                else:
                    self._write_report(parts[0], parts[1], parts[2])
                return
            if len(parts) == 5 and parts[3] == "artifacts" and all(parts):
                self._write_report_artifact(
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[4],
                    urlsplit(self.path).query,
                )
                return
            self._error(
                HTTPStatus.BAD_REQUEST,
                "invalid_report_path",
                "Report path is invalid.",
            )
            return
        if decoded_path == f"/api/{API_VERSION}/metrics":
            if urlsplit(self.path).query:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_query", "Metrics does not accept query parameters.")
            else:
                self._write_metrics()
            return
        if decoded_path == f"/api/{API_VERSION}/operations":
            if urlsplit(self.path).query:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_query",
                    "Operations does not accept query parameters.",
                )
            else:
                self._write_operation_framework()
            return
        operation_prefix = f"/api/{API_VERSION}/operations/"
        if decoded_path.startswith(operation_prefix):
            operation_id = decoded_path[len(operation_prefix) :]
            if (
                not operation_id
                or "/" in operation_id
                or operation_id in {"preview", "execute"}
                or urlsplit(self.path).query
            ):
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_operation_id",
                    "Operation ID is invalid.",
                )
            else:
                self._write_operation(operation_id)
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
            tracker_suffix = decoded_path[len(tracker_prefix) :]
            if tracker_suffix.endswith("/source"):
                tracker_id = tracker_suffix[: -len("/source")]
                if not tracker_id or "/" in tracker_id:
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_tracker_id", "Tracker ID is invalid.")
                else:
                    self._write_tracker_source(tracker_id, urlsplit(self.path).query)
                return
            if tracker_suffix.endswith("/diff"):
                tracker_id = tracker_suffix[: -len("/diff")]
                if not tracker_id or "/" in tracker_id or urlsplit(self.path).query:
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_tracker_id", "Tracker ID is invalid.")
                else:
                    self._write_tracker_diff(tracker_id)
                return
            tracker_id = tracker_suffix
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
        if self._handle_admin_operation_mutation(decoded_path):
            return
        if self._handle_task_mutation(decoded_path):
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


def create_server(
    config: ServerConfig,
    *,
    nonce: str | None = None,
    operation_registry: OperationRegistry | None = None,
) -> DashboardHTTPServer:
    return DashboardHTTPServer(
        config,
        nonce=nonce,
        operation_registry=operation_registry,
    )


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
    command.add_argument("--codex-binary", type=Path)
    command.add_argument(
        "--codex-client-wheel",
        type=Path,
        default=(
            Path(os.environ["SOFTWARE_FACTORY_CODEX_CLIENT_WHEEL"])
            if os.environ.get("SOFTWARE_FACTORY_CODEX_CLIENT_WHEEL")
            else None
        ),
        help="Exact internal codex-app-server-client wheel accepted by the Factory pin.",
    )
    command.add_argument("--codex-home", type=Path)
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
                codex_client_wheel=args.codex_client_wheel,
                codex_executable=args.codex_binary,
                codex_home=args.codex_home,
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
