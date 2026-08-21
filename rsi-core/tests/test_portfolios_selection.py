from __future__ import annotations

import pytest

from rsi_core import RSIKernel, RSITransitionError


def test_portfolio_transitions_preserve_sequential_lane_semantics() -> None:
    policy = RSIKernel().portfolios
    lanes = [{"id": "diagnose"}, {"id": "repair"}]
    activated = policy.activate(
        mode="sequential",
        lanes=lanes,
        status="planned",
        baseline_currentness_root="root-a",
        currentness_root="root-a",
    )
    advanced = policy.complete_lane(
        mode="sequential",
        lanes=lanes,
        status=activated.status,
        active_lane_ids=activated.active_lane_ids,
        completed_lane_ids=activated.completed_lane_ids,
        lane_id="diagnose",
        succeeded=True,
    )
    completed = policy.complete_lane(
        mode="sequential",
        lanes=lanes,
        status=advanced.status,
        active_lane_ids=advanced.active_lane_ids,
        completed_lane_ids=advanced.completed_lane_ids,
        lane_id="repair",
        succeeded=True,
    )

    assert activated.active_lane_ids == ("diagnose",)
    assert advanced.active_lane_ids == ("repair",)
    assert completed.status == "completed"


def test_parallel_portfolios_filter_blocked_lanes_and_fail_closed() -> None:
    policy = RSIKernel().portfolios
    lanes = [{"id": "a"}, {"id": "b", "blocked": True}, {"id": "c"}]
    activated = policy.activate(
        mode="parallel",
        lanes=lanes,
        status="planned",
        baseline_currentness_root="root-a",
        currentness_root="root-a",
    )
    failed = policy.complete_lane(
        mode="parallel",
        lanes=lanes,
        status="active",
        active_lane_ids=activated.active_lane_ids,
        completed_lane_ids=(),
        lane_id="a",
        succeeded=False,
    )
    assert activated.active_lane_ids == ("a", "c")
    assert failed.status == "failed"

    with pytest.raises(ValueError, match="unique stable ids"):
        policy.validate_lanes([{"id": "a"}, {"id": "a"}])
    with pytest.raises(RSITransitionError, match="baseline is stale"):
        policy.activate(
            mode="parallel",
            lanes=lanes,
            status="planned",
            baseline_currentness_root="old",
            currentness_root="new",
        )
    with pytest.raises(RSITransitionError, match="lane is not active"):
        policy.complete_lane(
            mode="parallel",
            lanes=lanes,
            status="active",
            active_lane_ids=("a",),
            completed_lane_ids=(),
            lane_id="c",
            succeeded=True,
        )


def test_selection_and_selector_self_change_require_independent_evidence() -> None:
    kernel = RSIKernel()
    with pytest.raises(RSITransitionError, match="independently"):
        kernel.reviews.require_independent_actor(
            author_id="author", reviewer_id="author", subject="candidate author"
        )
    with pytest.raises(RSITransitionError, match="accepting review"):
        kernel.selections.require_selectable(status="considered", has_accepting_review=False)

    review = kernel.selector_policies.evaluation_update(
        evaluation_type="independent_review", disposition="passed"
    )
    assert review.status_field == "review_status"
    assert review.normalized_disposition == "accepted"

    kernel.selector_policies.require_activation(
        historical_status="passed",
        forward_status="passed",
        review_status="accepted",
    )
    with pytest.raises(ValueError, match="requires evidence"):
        kernel.selector_policies.require_rollback(status="active", evidence_ids=[])
    with pytest.raises(RSITransitionError, match="not active"):
        kernel.selector_policies.require_rollback(status="superseded", evidence_ids=["regression"])


def test_selection_review_identity_and_outcome_confidence_are_evidence_bound() -> None:
    policy = RSIKernel().selections
    first = policy.review_root(
        selection_id="selection-1",
        disposition="accept",
        findings={"quality": "highest"},
        evidence_ids=["case-b", "case-a"],
    )
    repeated = policy.review_root(
        selection_id="selection-1",
        disposition="accept",
        findings={"quality": "highest"},
        evidence_ids=["case-a", "case-b"],
    )
    assert first == repeated
    with pytest.raises(ValueError, match="requires evidence"):
        policy.review_root(
            selection_id="selection-1",
            disposition="accept",
            findings={},
            evidence_ids=[],
        )
    with pytest.raises(RSITransitionError, match="not eligible"):
        policy.require_selectable(status="rejected", has_accepting_review=True)
    with pytest.raises(ValueError, match="between zero and one"):
        policy.validate_causal_confidence(1.1)


def test_selector_policy_evaluation_maps_stages_and_rejects_incomplete_activation() -> None:
    policy = RSIKernel().selector_policies
    assert policy.candidate_root({"weight": 1}) == policy.candidate_root({"weight": 1})
    assert (
        policy.evaluation_update(evaluation_type="historical", disposition="passed").status_field
        == "historical_status"
    )
    assert (
        policy.evaluation_update(
            evaluation_type="forward_shadow", disposition="passed"
        ).status_field
        == "forward_status"
    )
    assert (
        policy.evaluation_update(
            evaluation_type="live_effectiveness", disposition="effective"
        ).status_field
        is None
    )
    with pytest.raises(RSITransitionError, match="forward-shadow"):
        policy.require_activation(
            historical_status="passed",
            forward_status="failed",
            review_status="accepted",
        )
