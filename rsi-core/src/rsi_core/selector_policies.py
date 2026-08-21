from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .errors import RSITransitionError
from .identity import digest, normalize_ids
from .models import PolicyEvaluationUpdate

LiteralStatusField = Literal["historical_status", "forward_status", "review_status"] | None


class SelectorPolicy:
    """Staged evaluation and rollback rules for changing the selector itself."""

    @staticmethod
    def candidate_root(policy: Mapping[str, Any]) -> str:
        return digest(dict(policy))

    @staticmethod
    def evaluation_update(*, evaluation_type: str, disposition: str) -> PolicyEvaluationUpdate:
        field: LiteralStatusField = None
        normalized = disposition
        if evaluation_type == "historical":
            field = "historical_status"
        elif evaluation_type == "forward_shadow":
            field = "forward_status"
        elif evaluation_type == "independent_review":
            field = "review_status"
            normalized = {"passed": "accepted", "failed": "rejected"}.get(disposition, disposition)
        return PolicyEvaluationUpdate(field, normalized)

    @staticmethod
    def require_activation(
        *, historical_status: str, forward_status: str, review_status: str
    ) -> None:
        if not (
            historical_status == "passed"
            and forward_status == "passed"
            and review_status == "accepted"
        ):
            raise RSITransitionError(
                "selector policy requires historical, forward-shadow, and independent-review acceptance"
            )

    @staticmethod
    def require_rollback(*, status: str, evidence_ids: Sequence[str]) -> None:
        if not normalize_ids(evidence_ids):
            raise ValueError("selector-policy rollback requires evidence")
        if status != "active":
            raise RSITransitionError("selector policy is not active")
