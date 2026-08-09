from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path, PurePosixPath
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Sequence
from urllib.parse import unquote, urlsplit

from .catalog import (
    CatalogError,
    CatalogStore,
    default_catalog_path,
    discover_catalog,
    discover_project,
    validate_catalog_fingerprint,
    validate_project_id,
)
from .contract import API_VERSION, PACKAGE_VERSION, envelope


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
        missing = ["codex-app-server"]
        if not frontend_available:
            missing.insert(0, "frontend-build")
        if not catalog_available:
            missing.insert(0, "project-catalog")
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
                    ),
                    "missing": missing,
                },
                limitations=[
                    "Project catalog readiness does not include tracker, supervision, or task truth."
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
            "Tracker paths are candidates only; content parsing begins in Block 3.",
            "Supervision and Codex task sources remain unavailable until Blocks 4 and 5.",
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
                "missing": ["tracker-content", "supervision", "codex-app-server"],
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
                    "missing": ["tracker-content", "supervision", "codex-app-server"],
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
