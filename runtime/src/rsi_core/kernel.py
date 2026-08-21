from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

PortfolioMode = Literal["sequential", "parallel"]
PortfolioStatus = Literal["planned", "active", "completed", "failed", "cancelled"]


class RSITransitionError(RuntimeError):
    """A requested improvement transition violates a safety invariant."""


@dataclass(frozen=True)
class CheckpointDecision:
    """Materiality decision for one exact observed state."""

    state_fingerprint: str
    material: bool
    action: Literal["record", "no_change"]


@dataclass(frozen=True)
class PortfolioTransition:
    """Pure result of activating or advancing an improvement portfolio."""

    active_lane_ids: tuple[str, ...]
    completed_lane_ids: tuple[str, ...]
    status: PortfolioStatus


@dataclass(frozen=True)
class PolicyEvaluationUpdate:
    """Host update implied by one selector-policy evaluation."""

    status_field: Literal["historical_status", "forward_status", "review_status"] | None
    normalized_disposition: str


class RSIKernel:
    """Pure decision kernel for bounded recursive self-improvement.

    The kernel computes stable identities and enforces the transitions that make an
    improvement loop safe: exact materiality, currentness, independent challenge,
    attributed selection, measured outcomes, staged policy evaluation, and rollback.
    It does not prescribe a storage engine or execute proposed effects.
    """

    @staticmethod
    def canonical_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def digest(cls, value: Any) -> str:
        return hashlib.sha256(cls.canonical_json(value).encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_ids(values: Sequence[str] | None) -> tuple[str, ...]:
        return tuple(sorted({str(value) for value in (values or ()) if str(value)}))

    def checkpoint(
        self,
        *,
        state: Mapping[str, Any],
        evidence_ids: Sequence[str],
        previous_fingerprint: str | None = None,
    ) -> CheckpointDecision:
        fingerprint = self.digest(
            {
                "state": dict(state),
                "evidence_ids": list(self.normalize_ids(evidence_ids)),
            }
        )
        material = fingerprint != previous_fingerprint
        return CheckpointDecision(
            state_fingerprint=fingerprint,
            material=material,
            action="record" if material else "no_change",
        )

    def program_change_root(
        self,
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
        return self.digest(
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
    def require_independent_actor(
        *, author_id: str | None, reviewer_id: str | None, subject: str
    ) -> None:
        if author_id is not None and reviewer_id == author_id:
            raise RSITransitionError(f"{subject} cannot independently review it")

    @staticmethod
    def require_program_change_application(
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

    @staticmethod
    def validate_portfolio_lanes(lanes: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
        if not lanes:
            raise ValueError("program portfolio requires at least one lane")
        lane_ids = tuple(str(lane.get("id", "")) for lane in lanes)
        if any(not lane_id for lane_id in lane_ids) or len(set(lane_ids)) != len(lane_ids):
            raise ValueError("portfolio lanes require unique stable ids")
        return lane_ids

    def activate_portfolio(
        self,
        *,
        mode: PortfolioMode,
        lanes: Sequence[Mapping[str, Any]],
        status: str,
        baseline_currentness_root: str,
        currentness_root: str,
    ) -> PortfolioTransition:
        lane_ids = self.validate_portfolio_lanes(lanes)
        if status != "planned":
            raise RSITransitionError("portfolio is not awaiting activation")
        if baseline_currentness_root != currentness_root:
            raise RSITransitionError("portfolio baseline is stale")
        if mode == "sequential":
            active: tuple[str, ...] = (lane_ids[0],)
        elif mode == "parallel":
            active = tuple(
                lane_id
                for lane_id, lane in zip(lane_ids, lanes, strict=True)
                if not lane.get("blocked", False)
            )
        else:
            raise ValueError(f"unsupported portfolio mode: {mode}")
        return PortfolioTransition(
            active_lane_ids=active,
            completed_lane_ids=(),
            status="active",
        )

    def complete_portfolio_lane(
        self,
        *,
        mode: PortfolioMode,
        lanes: Sequence[Mapping[str, Any]],
        status: str,
        active_lane_ids: Sequence[str],
        completed_lane_ids: Sequence[str],
        lane_id: str,
        succeeded: bool,
    ) -> PortfolioTransition:
        lane_ids = self.validate_portfolio_lanes(lanes)
        if status != "active":
            raise RSITransitionError("portfolio is not active")
        active = list(active_lane_ids)
        completed = list(completed_lane_ids)
        if lane_id not in active:
            raise RSITransitionError("lane is not active")
        active.remove(lane_id)
        if succeeded:
            completed.append(lane_id)
        if mode == "sequential" and succeeded:
            remaining = [
                candidate
                for candidate in lane_ids
                if candidate not in set(active + completed)
            ]
            if remaining:
                active.append(remaining[0])
        next_status: PortfolioStatus = (
            "failed"
            if not succeeded
            else "completed"
            if not active and len(completed) == len(lane_ids)
            else "active"
        )
        return PortfolioTransition(tuple(active), tuple(completed), next_status)

    def selection_review_root(
        self,
        *,
        selection_id: str,
        disposition: str,
        findings: Mapping[str, Any],
        evidence_ids: Sequence[str],
    ) -> str:
        evidence = self.normalize_ids(evidence_ids)
        if not evidence:
            raise ValueError("selection review requires evidence")
        return self.digest(
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

    def selector_policy_root(self, policy: Mapping[str, Any]) -> str:
        return self.digest(dict(policy))

    @staticmethod
    def policy_evaluation_update(
        *, evaluation_type: str, disposition: str
    ) -> PolicyEvaluationUpdate:
        field: Literal["historical_status", "forward_status", "review_status"] | None = None
        normalized = disposition
        if evaluation_type == "historical":
            field = "historical_status"
        elif evaluation_type == "forward_shadow":
            field = "forward_status"
        elif evaluation_type == "independent_review":
            field = "review_status"
            normalized = {"passed": "accepted", "failed": "rejected"}.get(
                disposition, disposition
            )
        return PolicyEvaluationUpdate(field, normalized)

    @staticmethod
    def require_selector_policy_activation(
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

    @classmethod
    def require_selector_policy_rollback(
        cls, *, status: str, evidence_ids: Sequence[str]
    ) -> None:
        if not cls.normalize_ids(evidence_ids):
            raise ValueError("selector-policy rollback requires evidence")
        if status != "active":
            raise RSITransitionError("selector policy is not active")
