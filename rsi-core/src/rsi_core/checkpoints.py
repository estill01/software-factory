from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import digest, normalize_ids
from .models import CheckpointDecision


class CheckpointPolicy:
    """Detect exact material changes without owning checkpoint persistence."""

    @staticmethod
    def evaluate(
        *,
        state: Mapping[str, Any],
        evidence_ids: Sequence[str],
        previous_fingerprint: str | None = None,
    ) -> CheckpointDecision:
        fingerprint = digest(
            {"state": dict(state), "evidence_ids": list(normalize_ids(evidence_ids))}
        )
        material = fingerprint != previous_fingerprint
        return CheckpointDecision(
            state_fingerprint=fingerprint,
            material=material,
            action="record" if material else "no_change",
        )
