from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: Path, old: str, new: str, *, required: bool = True) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if required and count == 0:
        raise RuntimeError(f"expected a match in {path}\n{old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def harden_audit_boundary() -> None:
    path = SOURCE / "audit.py"
    replace_once(
        path,
        "import sqlite3\nfrom collections.abc import Callable, Mapping\nfrom dataclasses import dataclass, field\nfrom typing import Any, TypeVar\n",
        "import datetime as dt\nimport sqlite3\nfrom collections.abc import Callable, Mapping\nfrom contextlib import AbstractContextManager\nfrom dataclasses import dataclass, field\nfrom typing import Any, Protocol, TypeVar, cast\n",
    )
    protocol = '''\n\nclass _AuditPersistence(Protocol):
    """Persistence surface required by the audit/application command layer."""

    def transaction(
        self, *, mode: str = "IMMEDIATE"
    ) -> AbstractContextManager[sqlite3.Connection]: ...

    def all(
        self,
        sql: str,
        parameters: tuple[Any, ...] | Mapping[str, Any] = (),
        *,
        db: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]: ...

    def check_version(
        self,
        db: sqlite3.Connection,
        *,
        table: str,
        row_id: str,
        expected_version: int,
    ) -> dict[str, Any]: ...


class AuditMixin:
    def _persistence(self) -> _AuditPersistence:
        """Return the concrete database owner without competing base methods."""

        return cast(_AuditPersistence, self)
'''
    replace_once(path, "\n\nclass AuditMixin:\n", protocol)
    replace_all(path, "self.all(", "self._persistence().all(")
    replace_all(path, "self.transaction(", "self._persistence().transaction(")
    replace_all(path, "self.check_version(", "self._persistence().check_version(")
    replace_once(
        path,
        '''        expiry = parse_time(authority["expires_at"])
        if expiry is not None and expiry <= parse_time(utc_now()):
            raise AuthorityDenied("authority record is expired")
''',
        '''        expiry = parse_time(authority["expires_at"])
        if expiry is not None and expiry <= dt.datetime.now(dt.UTC):
            raise AuthorityDenied("authority record is expired")
''',
    )


def harden_authority_time_checks() -> None:
    path = SOURCE / "mission.py"
    text = path.read_text(encoding="utf-8")
    if "import datetime as dt\n" not in text:
        text = text.replace(
            "from __future__ import annotations\n\n",
            "from __future__ import annotations\n\nimport datetime as dt\n",
            1,
        )
        path.write_text(text, encoding="utf-8")
    replace_once(
        path,
        '''        if expires_at is not None and parse_time(expires_at) <= parse_time(utc_now()):
            raise ValueError("authority cannot be created already expired")
''',
        '''        now_dt = dt.datetime.now(dt.UTC)
        expiry = parse_time(expires_at)
        if expires_at is not None and (expiry is None or expiry <= now_dt):
            raise ValueError("authority cannot be created already expired")
''',
    )
    replace_once(
        path,
        '''                if parent_expiry is not None and parent_expiry <= parse_time(utc_now()):
''',
        '''                if parent_expiry is not None and parent_expiry <= now_dt:
''',
    )
    replace_once(
        path,
        '''                if parent_expiry is not None and (
                    expires_at is None or parse_time(expires_at) > parent_expiry
                ):
''',
        '''                child_expiry = parse_time(expires_at)
                if parent_expiry is not None and (
                    child_expiry is None or child_expiry > parent_expiry
                ):
''',
    )


def harden_lease_time_checks() -> None:
    path = SOURCE / "execution.py"
    replace_all(
        path,
        "dt.datetime.now(dt.timezone.utc)",
        "dt.datetime.now(dt.UTC)",
        required=False,
    )
    replace_once(
        path,
        '''            if parse_time(row["expires_at"]) <= now:
                raise StaleLease("execution lease expired")
''',
        '''            expires_at = parse_time(row["expires_at"])
            if expires_at is None or expires_at <= now:
                raise StaleLease("execution lease expired")
''',
    )


def harden_skill_lookup() -> None:
    path = SOURCE / "skill_bridge.py"
    replace_once(
        path,
        '''    mission = context.store.one("SELECT * FROM missions WHERE id=?", (args.mission,))
    payload = json.loads(args.payload)
''',
        '''    mission = context.store.one(
        "SELECT * FROM missions WHERE id=?", (args.mission,), required=False
    )
    if mission is None:
        raise RuntimeError(f"mission not found: {args.mission}")
    payload = json.loads(args.payload)
''',
    )


def align_package_version() -> None:
    path = SOURCE / "__init__.py"
    replace_once(path, '__version__ = "2.0.0.dev3"', '__version__ = "2.0.0.dev4"')


def main() -> None:
    harden_audit_boundary()
    harden_authority_time_checks()
    harden_lease_time_checks()
    harden_skill_lookup()
    align_package_version()


if __name__ == "__main__":
    main()
