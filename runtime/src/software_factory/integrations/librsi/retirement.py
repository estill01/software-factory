from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib.resources import files
from typing import Any

from ...util import digest_json

EXPECTED_LIBRSI_SHADOW_RETIREMENT_ROOT = (
    "e61871f6e8c058b43183eaecf4a0cfa14f6e0234e024a40b1f0b64387e339677"
)


@dataclass(frozen=True, slots=True)
class LibRSIShadowRetirement:
    """Immutable acceptance basis for retiring the active legacy comparator."""

    accepted_factory_revision: str
    accepted_factory_tree: str
    contract: str
    focused_evidence_path: str
    focused_evidence_sha256: str
    legacy_comparator_path: str
    legacy_comparator_sha256: str
    parity_dimensions: tuple[str, ...]
    preserved_legacy_path: str
    retirement_disposition: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LibRSIShadowRetirement:
        payload = dict(value)
        dimensions = payload.get("parity_dimensions")
        if not isinstance(dimensions, list) or not all(
            isinstance(item, str) and item for item in dimensions
        ):
            raise RuntimeError("libRSI shadow retirement parity dimensions are invalid")
        payload["parity_dimensions"] = tuple(dimensions)
        retirement = cls(**payload)
        if retirement.contract != "software-factory.librsi-shadow-retirement/v1":
            raise RuntimeError("libRSI shadow retirement contract is unsupported")
        return retirement

    @property
    def root(self) -> str:
        return digest_json(asdict(self))


def _load_retirement() -> LibRSIShadowRetirement:
    payload = (
        files("software_factory.semantic_pins")
        .joinpath("librsi-shadow-retirement.json")
        .read_text(encoding="utf-8")
    )
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError("libRSI shadow retirement pin must be a JSON object")
    retirement = LibRSIShadowRetirement.from_dict(value)
    if retirement.root != EXPECTED_LIBRSI_SHADOW_RETIREMENT_ROOT:
        raise RuntimeError("libRSI shadow retirement pin does not match the accepted root")
    return retirement


LIBRSI_SHADOW_RETIREMENT = _load_retirement()
