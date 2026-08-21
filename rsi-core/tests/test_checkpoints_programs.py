from __future__ import annotations

import pytest

from rsi_core import RSIKernel, RSITransitionError


def test_checkpoint_identity_is_exact_stable_and_order_independent() -> None:
    policy = RSIKernel().checkpoints
    first = policy.evaluate(
        state={"revision": "a", "quality": 0.8},
        evidence_ids=["evaluation-2", "evaluation-1", "evaluation-2"],
    )
    repeated = policy.evaluate(
        state={"quality": 0.8, "revision": "a"},
        evidence_ids=["evaluation-1", "evaluation-2"],
        previous_fingerprint=first.state_fingerprint,
    )
    changed = policy.evaluate(
        state={"quality": 0.9, "revision": "a"},
        evidence_ids=["evaluation-1", "evaluation-2"],
        previous_fingerprint=first.state_fingerprint,
    )

    assert repeated.material is False
    assert repeated.action == "no_change"
    assert changed.material is True
    assert changed.state_fingerprint != first.state_fingerprint


def test_program_change_identity_and_application_guards_are_host_neutral() -> None:
    policy = RSIKernel().programs
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
    assert policy.candidate_root(**arguments) == policy.candidate_root(**arguments)

    policy.require_application(
        review_status="accepted",
        application_status="pending",
        reviewed_currentness_root=arguments["currentness_root"],
        currentness_root=arguments["currentness_root"],
    )
    with pytest.raises(RSITransitionError, match="stale"):
        policy.require_application(
            review_status="accepted",
            application_status="pending",
            reviewed_currentness_root=arguments["currentness_root"],
            currentness_root="current-abcdef1234567890",
        )
    with pytest.raises(RSITransitionError, match="accepted"):
        policy.require_application(
            review_status="pending",
            application_status="pending",
            reviewed_currentness_root=arguments["currentness_root"],
            currentness_root=arguments["currentness_root"],
        )
    with pytest.raises(RSITransitionError, match="awaiting application"):
        policy.require_application(
            review_status="accepted",
            application_status="applied",
            reviewed_currentness_root=arguments["currentness_root"],
            currentness_root=arguments["currentness_root"],
        )


def test_program_change_requires_an_effect_and_stable_roots() -> None:
    policy = RSIKernel().programs
    with pytest.raises(ValueError, match="effect specification"):
        policy.candidate_root(
            scope_id="scope",
            program_id=None,
            change_kind="replace",
            rationale={},
            change_spec={},
            requested_range_root="range-1234567890abcdef",
            accepted_history_root="history-1234567890abcdef",
            currentness_root="current-1234567890abcdef",
        )
    with pytest.raises(ValueError, match="stable content"):
        policy.candidate_root(
            scope_id="scope",
            program_id=None,
            change_kind="replace",
            rationale={"reason": "change"},
            change_spec={"effect": "host"},
            requested_range_root="short",
            accepted_history_root="history-1234567890abcdef",
            currentness_root="current-1234567890abcdef",
        )
