from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Filesystem locations used by one Software Factory runtime instance."""

    root: Path
    database: Path
    artifacts: Path
    workspaces: Path
    releases: Path
    providers: Path

    @classmethod
    def from_root(cls, root: str | Path) -> RuntimePaths:
        resolved = Path(root).expanduser().resolve()
        return cls(
            root=resolved,
            database=resolved / "factory.sqlite3",
            artifacts=resolved / "artifacts",
            workspaces=resolved / "workspaces",
            releases=resolved / "releases",
            providers=resolved / "providers",
        )

    @classmethod
    def from_environment(cls) -> RuntimePaths:
        configured = os.environ.get("SOFTWARE_FACTORY_HOME")
        root = Path(configured).expanduser() if configured else Path.home() / ".software-factory"
        return cls.from_root(root)

    def ensure(self) -> RuntimePaths:
        for directory in (
            self.root,
            self.artifacts,
            self.workspaces,
            self.releases,
            self.providers,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self
