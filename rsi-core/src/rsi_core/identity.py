from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_ids(values: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in (values or ()) if str(value)}))
