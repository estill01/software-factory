from __future__ import annotations

import hashlib
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from software_factory.errors import InvalidTransition
from software_factory.evolution import EvolutionService


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE missions(id TEXT PRIMARY KEY);
            CREATE TABLE agent_sessions(id TEXT PRIMARY KEY);
            """
        )
        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0010_evolution_runtime.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))
        self.connection.execute("INSERT INTO missions(id) VALUES('mission-1')")
        self.connection.executemany(
            "INSERT INTO agent_sessions(id) VALUES(?)",
            [("author",), ("reviewer",), ("selector",), ("evaluator",)],
        )

    @contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        self.connection.execute(f"BEGIN {mode}")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        if row is None:
            if required:
                raise LookupError(sql)
            return None
        return dict(row)

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, parameters).fetchall()]


def service() -> EvolutionService:
    return EvolutionService(TestStore())  # type: ignore[arg-type]


def roots() -> dict[str, str]:
    return {
        "requested_range_root": "range-1234567890abcdef",
        "accepted_history_root": "history-1234567890abcdef",
        "currentness_root": "current-1234567890abcdef",
    }


def test_checkpoint_is_material_only_when_exact_state_changes() -> None:
    evolution = service()
    first = evolution.checkpoint(
        mission_id="mission-1",
        boundary_type="checkpoint",
        source_type="work_item",
        source_id="work-1",
        state={"status": "running", "revision": "a"},
        observations={"progress": 0.4},
        evidence_ids=["event-1"],
    )
    second = evolution.checkpoint(
        mission_id="mission-1",
        boundary_type="checkpoint",
        source_type="work_item",
        source_id="work-1",
        state={"status": "running", "revision": "a"},
        observations={"progress": 0.4},
        evidence_ids=["event-1"],
    )
    assert first["material"] == 1
    assert second["material"] is False
    assert second["action"] == "no_change"


def test_program_change_requires_independent_review_and_currentness() -> None:
    evolution = service()
    change = evolution.propose_program_change(
        mission_id="mission-1",
        change_kind="amend_current",
        rationale={"reason": "current strategy invalidated"},
        change_spec={"tracker_path": "docs/tracker.md", "new_content": "new"},
        author_session_id="author",
        **roots(),
    )
    with pytest.raises(InvalidTransition, match="author"):
        evolution.review_program_change(
            change["id"],
            reviewer_session_id="author",
            disposition="accepted",
            evidence_ids=["review"],
        )
    reviewed = evolution.review_program_change(
        change["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        evidence_ids=["review"],
    )
    assert reviewed["review_status"] == "accepted"
    with pytest.raises(InvalidTransition, match="stale"):
        evolution.apply_tracker_change(
            change["id"],
            repository_root=Path.cwd(),
            currentness_root="different-currentness-root",
        )


def test_tracker_change_is_exact_byte_bound_and_rolls_back_failed_validation(
    tmp_path: Path,
) -> None:
    evolution = service()
    tracker = tmp_path / "docs" / "tracker.md"
    tracker.parent.mkdir()
    tracker.write_text("old\n", encoding="utf-8")
    old_hash = hashlib.sha256(tracker.read_bytes()).hexdigest()
    change = evolution.propose_program_change(
        mission_id="mission-1",
        change_kind="amend_current",
        rationale={"reason": "repair invalid dependency"},
        change_spec={
            "tracker_path": "docs/tracker.md",
            "expected_sha256": old_hash,
            "new_content": "new\n",
        },
        author_session_id="author",
        **roots(),
    )
    evolution.review_program_change(
        change["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        evidence_ids=["review"],
    )
    with pytest.raises(RuntimeError, match="validation"):
        evolution.apply_tracker_change(
            change["id"],
            repository_root=tmp_path,
            currentness_root=roots()["currentness_root"],
            validation_command=[sys.executable, "-c", "raise SystemExit(2)"],
        )
    assert tracker.read_text(encoding="utf-8") == "old\n"
    status = evolution.store.one(
        "SELECT application_status FROM program_change_candidates_v2 WHERE id=?",
        (change["id"],),
    )
    assert status == {"application_status": "failed"}


def test_tracker_change_applies_after_validation(tmp_path: Path) -> None:
    evolution = service()
    tracker = tmp_path / "docs" / "tracker.md"
    tracker.parent.mkdir()
    tracker.write_text("old\n", encoding="utf-8")
    change = evolution.propose_program_change(
        mission_id="mission-1",
        change_kind="replace",
        rationale={"reason": "accepted successor"},
        change_spec={
            "tracker_path": "docs/tracker.md",
            "expected_sha256": hashlib.sha256(tracker.read_bytes()).hexdigest(),
            "new_content": "new\n",
        },
        author_session_id="author",
        **roots(),
    )
    evolution.review_program_change(
        change["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        evidence_ids=["review"],
    )
    applied = evolution.apply_tracker_change(
        change["id"],
        repository_root=tmp_path,
        currentness_root=roots()["currentness_root"],
        validation_command=[sys.executable, "-c", "raise SystemExit(0)"],
    )
    assert applied["application_status"] == "applied"
    assert tracker.read_text(encoding="utf-8") == "new\n"


def test_sequential_and_parallel_portfolios_have_distinct_lane_semantics() -> None:
    evolution = service()
    sequential = evolution.create_portfolio(
        mission_id="mission-1",
        mode="sequential",
        lanes=[{"id": "a"}, {"id": "b"}],
        baseline_currentness_root="current-1234567890abcdef",
    )
    active = evolution.activate_portfolio(
        sequential["id"], currentness_root="current-1234567890abcdef"
    )
    assert active["active_lane_ids_json"] == '["a"]'
    advanced = evolution.complete_portfolio_lane(
        sequential["id"], lane_id="a", succeeded=True
    )
    assert advanced["active_lane_ids_json"] == '["b"]'

    parallel = evolution.create_portfolio(
        mission_id="mission-1",
        mode="parallel",
        lanes=[{"id": "p1"}, {"id": "p2"}, {"id": "blocked", "blocked": True}],
        baseline_currentness_root="current-1234567890abcdef",
    )
    parallel_active = evolution.activate_portfolio(
        parallel["id"], currentness_root="current-1234567890abcdef"
    )
    assert parallel_active["active_lane_ids_json"] == '["p1","p2"]'


def test_selection_is_selected_by_an_attributed_selector_after_independent_challenge() -> None:
    evolution = service()
    selection = evolution.consider_selection(
        mission_id="mission-1",
        selection_group="feature-queue-1",
        selection_type="feature",
        candidate_key="durable-callbacks",
        candidate={"feature": "durable callbacks"},
        evidence={"incidents": 4},
        expected_value={"stalled_runs_prevented": 4},
        proposer_session_id="author",
    )
    evolution.review_selection(
        selection["id"],
        reviewer_session_id="reviewer",
        disposition="accept",
        findings={"highest leverage": True},
        evidence_ids=["case-1", "case-2"],
    )
    selected = evolution.select_candidate(
        selection["id"],
        selector_session_id="selector",
        rationale={"reason": "largest supported bottleneck"},
    )
    assert selected["status"] == "selected"
    assert selected["selector_session_id"] == "selector"
    outcome = evolution.record_selection_outcome(
        selection["id"],
        outcome_type="mixed",
        metrics={"stalls_before": 4, "stalls_after": 1},
        evidence_ids=["forward-cycle"],
        causal_confidence=0.7,
        limitations={"counterfactual": "no randomized control"},
    )
    assert outcome["outcome_type"] == "mixed"
    assert outcome["causal_confidence"] == pytest.approx(0.7)


def test_selector_policy_requires_frozen_history_forward_shadow_and_review() -> None:
    evolution = service()
    policy = evolution.propose_selector_policy(
        mission_id="mission-1",
        name="outcome-first selector",
        policy={"weights": {"expected_outcome": 0.6, "cost": -0.2, "risk": -0.2}},
        author_session_id="author",
    )
    with pytest.raises(InvalidTransition, match="historical"):
        evolution.activate_selector_policy(policy["id"])
    evolution.evaluate_selector_policy(
        policy["id"],
        evaluation_type="historical",
        disposition="passed",
        metrics={"regret_delta": -0.3},
        evidence_ids=["frozen-cases"],
        case_ids=["case-a", "case-b"],
        evaluator_session_id="evaluator",
    )
    evolution.evaluate_selector_policy(
        policy["id"],
        evaluation_type="forward_shadow",
        disposition="passed",
        metrics={"quality_delta": 0.2},
        evidence_ids=["forward-cycle"],
        evaluator_session_id="evaluator",
    )
    evolution.evaluate_selector_policy(
        policy["id"],
        evaluation_type="independent_review",
        disposition="accepted",
        metrics={"safe": True},
        evidence_ids=["review"],
        evaluator_session_id="reviewer",
    )
    active = evolution.activate_selector_policy(policy["id"])
    assert active["status"] == "active"
    rolled_back = evolution.rollback_selector_policy(
        active["id"], evidence_ids=["live-regression"]
    )
    assert rolled_back["status"] == "rolled_back"
