from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SemanticProjection:
    """Factory projection covered by the accepted libRSI parity basis."""

    hypothesis_roles: tuple[str, str]
    statements: tuple[str, str]
    predictions: tuple[Mapping[str, Any], Mapping[str, Any]]
    recommended_next_action: str
    experiment_kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_roles": list(self.hypothesis_roles),
            "statements": list(self.statements),
            "predictions": [dict(item) for item in self.predictions],
            "recommended_next_action": self.recommended_next_action,
            "experiment_kind": self.experiment_kind,
        }
