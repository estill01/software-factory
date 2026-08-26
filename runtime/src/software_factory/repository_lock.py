from __future__ import annotations

import fcntl
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _lock_root(repository: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return repository
    common = Path(result.stdout.strip())
    return common if common.is_absolute() else (repository / common).resolve()


@contextmanager
def repository_effect_lock(repository: str | Path, name: str) -> Iterator[None]:
    """Serialize physical repository effects across worktrees and processes."""

    root = Path(repository).resolve()
    lock_root = _lock_root(root)
    lock_root.mkdir(parents=True, exist_ok=True)
    path = lock_root / f"software-factory-{name}.lock"
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
