from __future__ import annotations

import stat
from pathlib import Path

import software_factory


def _installed_package_root() -> Path:
    paths = tuple(Path(value) for value in software_factory.__path__)
    if len(paths) != 1:
        raise RuntimeError(
            "software_factory must resolve to one installed package root"
        )
    root = paths[0]
    try:
        resolved = root.resolve(strict=True)
        metadata = resolved.lstat()
    except OSError as exc:
        raise RuntimeError("software_factory package root is unavailable") from exc
    if root.is_symlink() or resolved != root or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(
            "software_factory package root must be a canonical directory"
        )
    return resolved


SOFTWARE_FACTORY_PACKAGE_ROOT = _installed_package_root()
COMPATIBILITY_OWNER_ROOT = SOFTWARE_FACTORY_PACKAGE_ROOT / "compatibility_owners"
