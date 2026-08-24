from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from software_factory.errors import InvalidTransition
from software_factory.learning import LearningService
from software_factory.problem_solving import ProblemSolvingService
from software_factory.store import Store
from software_factory.util import utc_now


class ProblemStore(Store):
    def __init__(self) -> None:
        self._temporary_directory = TemporaryDirectory()
        super().__init__(Path(self._temporary_directory.name) / "factory.sqlite3")
        now = utc_now()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO projects(id,name,created_at,updated_at)
                   VALUES('project-1','problem-solving',?,?)""",
                (now, now),
            )
            db.execute(
                """INSERT INTO missions(
                    id,project_id,title,objective,status,autonomy_mode,created_at,updated_at
                ) VALUES(
                    'mission-1','project-1','problem','restore progress','active',
                    'reviewed_autonomous',?,?
                )""",
                (now, now),
            )
            db.executemany(
                """INSERT INTO agent_sessions(
                    id,mission_id,provider,role,desired_status,observed_status,started_at
                ) VALUES(?,'mission-1','test',?,'idle','idle',?)""",
                [
                    (session_id, session_id, now)
                    for session_id in ("proposer", "selector", "worker-a", "worker-b", "verifier")
                ],
            )


def service() -> ProblemSolvingService:
    store = ProblemStore()
    learning = LearningService(store)
    return ProblemSolvingService(store, learning)


def cycle(problem: ProblemSolvingService, causal_level: int = 0) -> dict[str, Any]:
    return problem.begin_cycle(
        mission_id="mission-1",
        trigger_type="incident",
        trigger_id="incident-1",
        objective={"capability": "controller remains live", "outcome": "work progresses"},
        governing_range_root="range-1234567890abcdef",
        state={"controller": "stopped", "open_obligations": ["obligation-1"]},
        causal_level=causal_level,
    )


def propose(
    problem: ProblemSolvingService,
    cycle_id: str,
    *,
    name: str,
    scope: list[str],
    evidence: list[str] | None = None,
    priority: int = 0,
    expected_value: float = 1.0,
    prerequisites: list[str] | None = None,
) -> dict[str, Any]:
    return problem.propose_strategy(
        cycle_id,
        strategy_type="alternate_implementation",
        strategy={"name": name, "implementation": f"implement {name}"},
        rationale={"reason": f"{name} addresses observed cause"},
        expected_effect={"progress_restored": True},
        writable_scope=scope,
        prerequisites=prerequisites,
        evidence_ids=evidence or [f"evidence-{name}"],
        proposer_session_id="proposer",
        priority=priority,
        expected_value=expected_value,
        estimated_cost=0.1,
        estimated_risk=0.1,
    )


def test_cycle_is_idempotent_for_exact_trigger_and_state() -> None:
    problem = service()
    first = cycle(problem)
    second = cycle(problem)
    assert second["id"] == first["id"]
    assert problem.store.one("SELECT COUNT(*) AS count FROM problem_solving_cycles_v2") == {
        "count": 1
    }


def test_selects_maximal_nonconflicting_strategy_set_by_attributed_selector() -> None:
    problem = service()
    current = cycle(problem)
    api = propose(problem, current["id"], name="api", scope=["runtime/api"], priority=4)
    conflict = propose(
        problem,
        current["id"],
        name="api-child",
        scope=["runtime/api/routes"],
        priority=3,
    )
    docs = propose(problem, current["id"], name="docs", scope=["docs"], priority=2)
    decision = problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "highest-value safe parallel frontier"},
        authority={"kind": "mission", "range_root": "range-1234567890abcdef"},
        max_parallel=4,
    )
    selected = set(__import__("json").loads(decision["selected_strategy_ids_json"]))
    assert selected == {api["id"], docs["id"]}
    assert conflict["id"] not in selected
    rows = problem.store.all(
        "SELECT id,selected_by_session_id,status FROM strategy_candidates_v2 WHERE id IN (?,?)",
        (api["id"], docs["id"]),
    )
    assert all(row["selected_by_session_id"] == "selector" for row in rows)
    assert all(row["status"] == "selected" for row in rows)


def test_prerequisite_blocks_selection_until_prior_strategy_succeeds() -> None:
    problem = service()
    current = cycle(problem)
    foundation = propose(
        problem, current["id"], name="foundation", scope=["runtime/foundation"], priority=1
    )
    dependent = propose(
        problem,
        current["id"],
        name="dependent",
        scope=["runtime/dependent"],
        priority=10,
        prerequisites=[foundation["id"]],
    )
    first = problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "dependency order"},
        authority={"kind": "mission"},
    )
    assert __import__("json").loads(first["selected_strategy_ids_json"]) == [foundation["id"]]
    attempt = problem.start_strategy(
        foundation["id"], agent_session_id="worker-a", basis_evidence_ids=["foundation-basis"]
    )
    problem.complete_strategy(
        attempt["id"],
        disposition="succeeded",
        result={"foundation_ready": True},
        observed_evidence_ids=["foundation-result"],
    )
    problem.verify_cycle(
        current["id"],
        disposition="inconclusive",
        metrics={"dependent_work_remaining": True},
        evidence_ids=[],
        verifier_session_id="verifier",
    )
    second = problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "prerequisite now accepted"},
        authority={"kind": "mission"},
    )
    assert __import__("json").loads(second["selected_strategy_ids_json"]) == [dependent["id"]]


def test_materially_identical_failed_strategy_cannot_be_reproposed_without_new_evidence() -> None:
    problem = service()
    current = cycle(problem)
    candidate = propose(
        problem,
        current["id"],
        name="same",
        scope=["runtime"],
        evidence=["initial-evidence"],
    )
    problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "initial supported strategy"},
        authority={"kind": "mission"},
    )
    attempt = problem.start_strategy(
        candidate["id"],
        agent_session_id="worker-a",
        basis_evidence_ids=["initial-evidence"],
    )
    problem.complete_strategy(
        attempt["id"],
        disposition="ineffective",
        result={"progress": False},
        observed_evidence_ids=["ineffective-result"],
    )
    with pytest.raises(InvalidTransition, match="genuinely new evidence"):
        propose(
            problem,
            current["id"],
            name="same",
            scope=["runtime"],
            evidence=["initial-evidence"],
        )
    retry = propose(
        problem,
        current["id"],
        name="same",
        scope=["runtime"],
        evidence=["initial-evidence", "new-causal-trace"],
    )
    assert retry["semantic_fingerprint"] == candidate["semantic_fingerprint"]
    assert retry["strategy_fingerprint"] != candidate["strategy_fingerprint"]


def test_failed_attempt_escalates_causal_level_and_changes_required_strategy_type() -> None:
    problem = service()
    current = cycle(problem, causal_level=0)
    candidate = propose(problem, current["id"], name="local", scope=["runtime"])
    problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "try local fix"},
        authority={"kind": "mission"},
    )
    attempt = problem.start_strategy(
        candidate["id"], agent_session_id="worker-a", basis_evidence_ids=["trace"]
    )
    problem.complete_strategy(
        attempt["id"],
        disposition="failed",
        result={"error": "same defect"},
        observed_evidence_ids=["failure-log"],
    )
    updated = problem.store.one(
        "SELECT causal_level,status FROM problem_solving_cycles_v2 WHERE id=?",
        (current["id"],),
    )
    assert updated == {"causal_level": 1, "status": "open"}
    next_action = problem.next_action(current["id"])
    assert next_action["action"] == "generate_strategies"
    assert next_action["required_strategy_type"] == "alternate_implementation"


def test_real_discriminating_experiment_changes_available_evidence(tmp_path: Path) -> None:
    problem = service()
    current = cycle(problem)
    design = problem.design_discriminating_experiment(
        current["id"],
        question="Does the alternate adapter emit the required health marker?",
        experiment_type="command",
        experiment_spec={"adapter": "alternate", "isolation": "subprocess"},
        expected_discrimination={
            "marker_present": "select alternate adapter",
            "marker_absent": "escalate architecture",
        },
        success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["ADAPTER_OK"]},
        safety_constraints={"network": False, "shell": False},
    )
    next_action = problem.next_action(current["id"])
    assert next_action["action"] == "run_discriminating_experiment"
    run = problem.run_command_experiment(
        design["id"],
        command=[sys.executable, "-c", "print('ADAPTER_OK')"],
        cwd=tmp_path,
    )
    assert run["disposition"] == "passed"
    assert run["evidence_root"]
    assert problem.store.one(
        "SELECT status FROM problem_experiment_designs_v2 WHERE id=?", (design["id"],)
    ) == {"status": "succeeded"}


def test_unexpected_success_becomes_bounded_candidate_not_global_policy() -> None:
    problem = service()
    current = cycle(problem)
    candidate = problem.record_unexpected_success(
        current["id"],
        source_id="execution-success-1",
        mechanism={"batching": "smaller", "ordering": "dependency-first"},
        outcome={"latency_delta": -0.4, "regressions": 0},
        evidence_ids=["success-trace"],
        proposer_session_id="proposer",
    )
    assert candidate["strategy_type"] == "success_generalization"
    strategy = __import__("json").loads(candidate["strategy_json"])
    rationale = __import__("json").loads(candidate["rationale_json"])
    assert strategy["generalization_mode"] == "bounded_candidate"
    assert rationale["automatic_global_promotion"] is False
    assert candidate["status"] == "proposed"


def test_cycle_resolves_only_after_effective_outcome_verification() -> None:
    problem = service()
    current = cycle(problem)
    candidate = propose(problem, current["id"], name="repair", scope=["runtime"])
    problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "supported repair"},
        authority={"kind": "mission"},
    )
    attempt = problem.start_strategy(
        candidate["id"], agent_session_id="worker-a", basis_evidence_ids=["repair-basis"]
    )
    problem.complete_strategy(
        attempt["id"],
        disposition="succeeded",
        result={"tests_passed": True},
        observed_evidence_ids=["test-output"],
    )
    assert problem.store.one(
        "SELECT status FROM problem_solving_cycles_v2 WHERE id=?", (current["id"],)
    ) == {"status": "verifying"}
    with pytest.raises(ValueError, match="requires observed"):
        problem.verify_cycle(
            current["id"],
            disposition="effective",
            metrics={"target_progressed": True},
            evidence_ids=[],
            verifier_session_id="verifier",
        )
    verification = problem.verify_cycle(
        current["id"],
        disposition="effective",
        metrics={"target_progressed": True, "recurrence": 0},
        evidence_ids=["later-live-progress"],
        verifier_session_id="verifier",
    )
    assert verification["disposition"] == "effective"
    assert problem.store.one(
        "SELECT status FROM problem_solving_cycles_v2 WHERE id=?", (current["id"],)
    ) == {"status": "resolved"}


def test_same_strategy_attempt_requires_new_basis_after_failure() -> None:
    problem = service()
    current = cycle(problem)
    candidate = propose(problem, current["id"], name="retryable", scope=["runtime"])
    problem.select_next_actions(
        current["id"],
        selected_by_session_id="selector",
        rationale={"reason": "first attempt"},
        authority={"kind": "mission"},
    )
    first = problem.start_strategy(
        candidate["id"], agent_session_id="worker-a", basis_evidence_ids=["basis-1"]
    )
    problem.complete_strategy(
        first["id"],
        disposition="failed",
        result={"failure": "transient-looking"},
        observed_evidence_ids=["failure-1"],
    )
    with pytest.raises(InvalidTransition, match="materially new evidence"):
        problem.start_strategy(
            candidate["id"], agent_session_id="worker-b", basis_evidence_ids=["basis-1"]
        )
    second = problem.start_strategy(
        candidate["id"],
        agent_session_id="worker-b",
        basis_evidence_ids=["basis-1", "new-provider-trace"],
    )
    assert second["attempt_number"] == 2
    assert second["agent_session_id"] == "worker-b"
