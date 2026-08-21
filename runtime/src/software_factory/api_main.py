from __future__ import annotations

import argparse
from collections.abc import Sequence

from .advanced import AdvancedServices
from .api import APIServer, FactoryAPI
from .entrypoints import context_store, open_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Software Factory v2 factory-floor API")
    parser.add_argument("--home")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = open_context(args.home)
    store = context_store(context)
    server = APIServer(
        FactoryAPI(store, AdvancedServices(store)), host=args.host, port=args.port
    )
    host, port = server.address
    print(f"Software Factory v2 API listening on http://{host}:{port}")
    try:
        server.httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
