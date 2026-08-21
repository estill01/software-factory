from __future__ import annotations

import pytest

from rsi_core import RSIKernel, RSITransitionError


def test_checkpoint_identity_is_exact_stable_and_order_independent() -> None:
    kernel = RSIKernel()
    first = kernel.checkpoint(
        state={"revision": "a", "quality": 0.8},
        evidence_ids=["evaluation-2", "evaluation-1", "evaluation-2"],
    )
    repeated = kernel.checkpoint(
        state={"quality": 0.8, "revision": "a"},
        evidence_ids=["evaluation-1", "evaluation-2"],
        previous_fingerprint=first.state_fingerprint,
    )
    changed = kernel.checkpoint(
        state={"quality": 0.9, "revision": "a"},
        evidence_ids=["evaluation-1", "evaluation-2"],
        previous_fingerprint=first.state_fingerprint,
    )

    assert first.material is True
    assert repeated.material is False
    assert repeated.action == "no_change"
    assert changed.material is True
    assert changed.state_fingerprint != first.state_fingerprint


def test_program_change_identity_and_application_guards_are_host_neutral() -> None:
    kernel = RSIKernel()
    arguments = {
        "scope_id": "product-a",
        "program_id": "program-1",
        "change_kind": "replace",
        "rationale": {"reason": "measured regression"},
        "change_spec": {"adapter": "host-owned-effect", "candidate": "v2"},
        "requested_range_root": "range-1234567890abcdef",
        "accepted_history_root": "history-1234567890abcdef",
        "currentness_root": "current-1234567890abcdef",
    }
    assert kernel.program_change_root(**arguments) == kernel.program_change_root(**arguments)

    kernel.require_program_change_application(
        review_status="accepted",
        application_status="pending",
        reviewed_currentness_root=arguments["currentness_root"],
        currentness_root=arguments["currentness_root"],
    )
    with pytest.raises(RSITransitionError, match="stale"):
        kernel.require_program_change_application(
            review_status="accepted",
            application_status="pending",
            reviewed_currentness_root=arguments["currentness_root"],
            currentness_root="current-abcdef1234567890",
        )


def test_portfolio_transitions_are_pure_and_preserve_lane_semantics() -> None:
    kernel = RSIKernel()
    lanes = [{"id": "diagnose"}, {"id": "repair"}]
    activated = kernel.activate_portfolio(
        mode="sequential",
        lanes=lanes,
        status="planned",
        baseline_currentness_root="root-a",
        currentness_root="root-a",
    )
    advanced = kernel.complete_portfolio_lane(
        mode="sequential",
        lanes=lanes,
        status=activated.status,
        active_lane_ids=activated.active_lane_ids,
        completed_lane_ids=activated.completed_lane_ids,
        lane_id="diagnose",
        succeeded=True,
    )
    completed = kernel.complete_portfolio_lane(
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
    assert completed.completed_lane_ids == ("diagnose", "repair")


def test_selection_and_selector_self_change_require_independent_evidence() -> None:
    kernel = RSIKernel()
    with pytest.raises(RSITransitionError, match="independently"):
        kernel.require_independent_actor(
            author_id="author", reviewer_id="author", subject="candidate author"
        )
    with pytest.raises(RSITransitionError, match="accepting review"):
        kernel.require_selectable(status="considered", has_accepting_review=False)

    historical = kernel.policy_evaluation_update(
        evaluation_type="historical", disposition="passed"
    )
    review = kernel.policy_evaluation_update(
        evaluation_type="independent_review", disposition="passed"
    )
    assert historical.status_field == "historical_status"
    assert review.status_field == "review_status"
    assert review.normalized_disposition == "accepted"

    kernel.require_selector_policy_activation(
        historical_status="passed",
        forward_status="passed",
        review_status="accepted",
    )
    with pytest.raises(RSITransitionError, match="forward-shadow"):
        kernel.require_selector_policy_activation(
            historical_status="passed",
            forward_status="failed",
            review_status="accepted",
        )
    with pytest.raises(ValueError, match="requires evidence"):
        kernel.require_selector_policy_rollback(status="active", evidence_ids=[])
    with pytest.raises(RSITransitionError, match="not active"):
        kernel.require_selector_policy_rollback(
            status="superseded", evidence_ids=["live-regression"]
        )
