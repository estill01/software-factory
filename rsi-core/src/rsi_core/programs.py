from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import RSITransitionError
from .identity import digest


class ProgramPolicy:
    """Stable identities and effect gates for recursive program changes."""

    @staticmethod
    def candidate_root(
        *,
        scope_id: str,
        program_id: str | None,
        change_kind: str,
        rationale: Mapping[str, Any],
        change_spec: Mapping[str, Any],
        requested_range_root: str,
        accepted_history_root: str,
        currentness_root: str,
    ) -> str:
        if not rationale or not change_spec:
            raise ValueError("program change requires rationale and an effect specification")
        roots = (requested_range_root, accepted_history_root, currentness_root)
        if any(len(root) < 16 for root in roots):
            raise ValueError("program change roots must be stable content identifiers")
        return digest(
            {
                "mission_id": scope_id,
                "program_id": program_id,
                "change_kind": change_kind,
                "rationale": dict(rationale),
                "change_spec": dict(change_spec),
                "requested_range_root": requested_range_root,
                "accepted_history_root": accepted_history_root,
                "currentness_root": currentness_root,
            }
        )

    @staticmethod
    def require_application(
        *,
        review_status: str,
        application_status: str,
        reviewed_currentness_root: str,
        currentness_root: str,
    ) -> None:
        if review_status != "accepted":
            raise RSITransitionError("only an accepted program change may be applied")
        if application_status not in {"pending", "failed", "rolled_back"}:
            raise RSITransitionError("program change is not awaiting application")
        if currentness_root != reviewed_currentness_root:
            raise RSITransitionError("program change currentness root is stale")
