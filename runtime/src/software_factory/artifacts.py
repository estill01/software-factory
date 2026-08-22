from __future__ import annotations

import mimetypes
import sqlite3
from pathlib import Path
from typing import Any

from .util import atomic_write, canonical_json, digest_bytes, new_id, utc_now


class ArtifactService:
    """Content-addressed evidence storage backed by the canonical artifacts table."""

    def __init__(self, store: Any, artifact_root: str | Path | None = None):
        self.store = store
        self.artifact_root = Path(artifact_root or self.store.path.parent / "artifacts").resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def store_bytes(
        self,
        payload: bytes,
        *,
        mission_id: str | None = None,
        producer_execution_id: str | None = None,
        media_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        db: sqlite3.Connection | None = None,
    ) -> str:
        sha256 = digest_bytes(payload)
        existing_row = (
            db.execute(
                "SELECT id FROM artifacts WHERE sha256=? AND byte_count=?",
                (sha256, len(payload)),
            ).fetchone()
            if db is not None
            else self.store.one(
                "SELECT id FROM artifacts WHERE sha256=? AND byte_count=?",
                (sha256, len(payload)),
                required=False,
            )
        )
        existing = dict(existing_row) if existing_row is not None else None
        if existing is not None:
            return str(existing["id"])
        artifact_id = new_id("art")
        extension = mimetypes.guess_extension(media_type or "") or ".bin"
        path = self.artifact_root / sha256[:2] / f"{sha256}{extension}"
        if not path.exists():
            atomic_write(path, payload, mode=0o600)
        values = (
            artifact_id,
            producer_execution_id,
            sha256,
            len(payload),
            media_type or "application/octet-stream",
            path.as_uri(),
            canonical_json(metadata or {}),
            utc_now(),
            mission_id,
            subject_type,
            subject_id,
        )
        statement = """INSERT INTO artifacts(
            id,producer_execution_id,sha256,byte_count,media_type,storage_uri,
            metadata_json,created_at,mission_id,subject_type,subject_id
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)"""
        if db is not None:
            db.execute(statement, values)
        else:
            with self.store.transaction() as connection:
                connection.execute(statement, values)
        return artifact_id

    def store_text(self, text: str, **kwargs: Any) -> str:
        kwargs.setdefault("media_type", "text/plain")
        return self.store_bytes(text.encode("utf-8"), **kwargs)

    def read(self, artifact_id: str) -> bytes:
        row = self.store.one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
        path = Path(row["storage_uri"].removeprefix("file://"))
        payload = path.read_bytes()
        if digest_bytes(payload) != row["sha256"] or len(payload) != row["byte_count"]:
            raise ValueError(f"artifact integrity check failed: {artifact_id}")
        return payload
