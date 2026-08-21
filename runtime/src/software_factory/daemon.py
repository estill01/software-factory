from __future__ import annotations

import argparse
import signal
import threading
from collections.abc import Sequence
from pathlib import Path

from .bootstrap import RuntimeContext, open_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="software-factoryd")
    parser.add_argument("--home", type=Path)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    return parser


def _tick_all(context: RuntimeContext) -> list[dict[str, object]]:
    return context.core.tick_all()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = open_runtime(args.home)
    if args.once:
        _tick_all(context)
        return 0

    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not stop.is_set():
        _tick_all(context)
        stop.wait(max(args.interval, 0.05))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
