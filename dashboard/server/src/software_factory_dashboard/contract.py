from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any


API_VERSION = "v1"
PACKAGE_VERSION = "0.1.0"


def observed_at() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def envelope(
    *,
    data: Any,
    source: dict[str, str],
    coverage: dict[str, Any],
    limitations: list[str],
    error: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    material = {
        "data": data,
        "source": source,
        "coverage": coverage,
        "limitations": limitations,
        "error": error,
    }
    return {
        **material,
        "observed_at": timestamp or observed_at(),
        "fingerprint": sha256(_canonical(material)).hexdigest(),
    }
