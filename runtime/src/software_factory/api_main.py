from __future__ import annotations

import argparse
import os
import signal
import stat
from collections.abc import Sequence
from pathlib import Path

from .api import APIServer, FactoryAPI
from .entrypoints import context_core, context_store, open_context
from .hosts import StandaloneFactoryService
from .utility_contracts import QualifiedUtilityRuntime, RuntimeIdentity


def read_service_token(path_value: str) -> str:
    path = Path(path_value).expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError("service token file must be an available non-symlink file") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("service token file must be regular")
        if metadata.st_mode & 0o077:
            raise ValueError("service token file cannot grant group or world access")
        if metadata.st_size > 4096:
            raise ValueError("service token file exceeds the supported size")
        raw = os.read(descriptor, 4097)
    finally:
        os.close(descriptor)
    try:
        token = raw.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise ValueError("service token file must contain UTF-8 text") from exc
    if "\n" in token or "\r" in token:
        raise ValueError("service token file must contain exactly one token")
    if not 32 <= len(token) <= 512 or not token.isprintable():
        raise ValueError("service token must contain 32 to 512 printable characters")
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Software Factory v2 factory-floor API")
    parser.add_argument("--home")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--service-token-file", required=True)
    parser.add_argument("--embedded-contract-wheel", required=True)
    parser.add_argument("--runtime-manifest-wheel", required=True)
    parser.add_argument("--component-root", required=True)
    parser.add_argument("--runtime-version", default="2.0.0.dev6")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = open_context(args.home)
    store = context_store(context)
    core = context_core(context)
    service_token = read_service_token(args.service_token_file)
    utilities = QualifiedUtilityRuntime.from_wheels(
        embedded_contract_wheel=args.embedded_contract_wheel,
        runtime_manifest_wheel=args.runtime_manifest_wheel,
    )
    identity = RuntimeIdentity(component_root=args.component_root, version=args.runtime_version)
    server = APIServer(
        FactoryAPI(
            store,
            core.advanced,
            reporting=core.reporting,
            engine_service=StandaloneFactoryService(context.engine),
            utility_runtime=utilities,
            runtime_identity=identity,
        ),
        service_token=service_token,
        host=args.host,
        port=args.port,
    )
    host, port = server.address
    print(f"Software Factory v2 API listening on http://{host}:{port}")

    def stop_service(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    previous_sigterm = signal.signal(signal.SIGTERM, stop_service)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
