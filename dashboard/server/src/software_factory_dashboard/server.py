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

from .contract import API_VERSION, PACKAGE_VERSION, envelope


MAX_BODY_BYTES = 64 * 1024
NONCE_PLACEHOLDER = "__SOFTWARE_FACTORY_MUTATION_NONCE__"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}
MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class DashboardConfigurationError(ValueError):
    """Raised when the local runtime would exceed its authority boundary."""


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    static_dir: Path | None = None
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
        return ServerConfig(
            host=normalized_host,
            port=self.port,
            static_dir=static_dir,
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
        missing = ["project-sources", "codex-app-server"]
        if not frontend_available:
            missing.insert(0, "frontend-build")
        data = {
            "status": "ok",
            "service": {"name": "software-factory-dashboard", "version": PACKAGE_VERSION},
            "integrations": {
                "frontend": {
                    "status": "available" if frontend_available else "unavailable",
                    "reason": None
                    if frontend_available
                    else "Run the Block 1 frontend production build.",
                },
                "project_sources": {
                    "status": "unavailable",
                    "reason": "Project discovery begins in tracker Block 2.",
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
                    "observed": ["runtime"] + (["frontend-build"] if frontend_available else []),
                    "missing": missing,
                },
                limitations=[
                    "Block 1 exposes runtime readiness only; no project or task sources are read."
                ],
            ),
        )

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
        if self._read_bounded_body() is None:
            return
        self._error(
            HTTPStatus.NOT_FOUND,
            "mutation_unavailable",
            "Block 1 defines no mutation endpoint.",
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
