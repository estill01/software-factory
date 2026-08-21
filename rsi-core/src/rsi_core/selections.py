from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import RSITransitionError
from .identity import digest, normalize_ids


class SelectionPolicy:
    """Reviewed candidate selection and outcome-quality invariants."""

    @staticmethod
    def review_root(
        *,
        selection_id: str,
        disposition: str,
        findings: Mapping[str, Any],
        evidence_ids: Sequence[str],
    ) -> str:
        evidence = normalize_ids(evidence_ids)
        if not evidence:
            raise ValueError("selection review requires evidence")
        return digest(
            {
                "selection_id": selection_id,
                "disposition": disposition,
                "findings": dict(findings),
                "evidence_ids": list(evidence),
            }
        )

    @staticmethod
    def require_selectable(*, status: str, has_accepting_review: bool) -> None:
        if not has_accepting_review:
            raise RSITransitionError("selection requires an independent accepting review")
        if status in {"rejected", "deferred", "superseded"}:
            raise RSITransitionError("selection candidate is not eligible")

    @staticmethod
    def validate_causal_confidence(value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("causal confidence must be between zero and one")
