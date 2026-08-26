"""Test-only driver for constructing historical v1 supervision fixtures.

Production entrypoints intentionally reject mutation after the SFV2 cutover. Tests
that exercise read-only projection still need representative historical ledgers, so
this driver calls the preserved compatibility command functions directly against a
temporary test root.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

OWNER = (
    Path(__file__).resolve().parents[3]
    / "runtime/src/software_factory/compatibility_owners/supervision/supervision_log.py"
)


def main() -> int:
    spec = importlib.util.spec_from_file_location("fixture_supervision_owner", OWNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(OWNER.parent))
    try:
        spec.loader.exec_module(module)
        args = module.parser().parse_args()
        args.func(args)
    finally:
        sys.path.pop(0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
