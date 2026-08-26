from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from ...util import digest_json, json_load


@dataclass(frozen=True, slots=True)
class LegacyShadowProjection:
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


def project_legacy_reflection(execution: Mapping[str, Any]) -> LegacyShadowProjection:
    """Pure preserved pre-cutover behavior used only as an independent comparator."""

    strategy = str(execution.get("strategy_key") or "unknown")
    if execution["status"] != "succeeded":
        fingerprint = str(
            execution.get("failure_fingerprint")
            or digest_json(json_load(cast(str, execution["error_json"]), {}))
        )
        return LegacyShadowProjection(
            hypothesis_roles=("causal", "problem_framing"),
            statements=(
                (
                    f"Strategy {strategy} is causally associated with failure "
                    f"fingerprint {fingerprint} in the current work context."
                ),
                (
                    f"The failure fingerprint {fingerprint} may be caused by environment, "
                    "currentness, or acceptance setup rather than the implementation strategy."
                ),
            ),
            predictions=(
                {"discriminator": "materially different strategy avoids the fingerprint"},
                {
                    "discriminator": (
                        "same strategy succeeds under corrected invocation/currentness"
                    )
                },
            ),
            recommended_next_action="run_discriminating_experiment",
            experiment_kind="bounded-strategy-context-discriminator",
        )
    return LegacyShadowProjection(
        hypothesis_roles=("strategy", "predictive"),
        statements=(
            (
                f"Strategy {strategy} produced an unusually strong capability effect in "
                "the observed context."
            ),
            (
                "The observed improvement may be contextual noise or an unrelated concurrent "
                "change rather than a reusable strategy effect."
            ),
        ),
        predictions=(
            {"discriminator": "benefit recurs in a bounded similar context"},
            {"discriminator": "benefit disappears under matched replay"},
        ),
        recommended_next_action="bounded_replay_and_counterexample_search",
        experiment_kind="bounded-matched-replay",
    )
