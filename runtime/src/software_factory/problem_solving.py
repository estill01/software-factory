from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from .errors import InvalidTransition, StoreError
from .learning import LearningService
from .store import Store
from .util import new_id, utc_now

StrategyType = Literal[
    "local_repair",
    "alternate_implementation",
    "candidate_comparison",
    "architecture_change",
    "program_revision",
    "selection_reconsideration",
    "factory_evolution",
    "experiment",
    "success_generalization",
]

_CAUSAL_LEVEL_STRATEGIES: tuple[StrategyType, ...] = (
    "local_repair",
    "alternate_implementation",
    "candidate_comparison",
    "architecture_change",
    "program_revision",
    "selection_reconsideration",
    "factory_evolution",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _ids(values: Sequence[str] | None) -> list[str]:
    return sorted({str(value) for value in (values or ()) if str(value)})


def _normalize_scope(values: Sequence[str] | None) -> list[str]:
    normalized: set[str] = set()
    for raw in values or ():
        value = str(raw).strip().replace("\\", "/").strip("/")
        if not value or value == "." or value.startswith("../") or "/../" in f"/{value}/":
            raise ValueError(f"invalid writable scope: {raw!r}")
        normalized.add(value)
    return sorted(normalized)


def _scope_conflicts(left: Sequence[str], right: Sequence[str]) -> bool:
    for left_value in left:
        left_parts = tuple(part for part in left_value.split("/") if part)
        for right_value in right:
            right_parts = tuple(part for part in right_value.split("/") if part)
            common = min(len(left_parts), len(right_parts))
            if left_parts[:common] == right_parts[:common]:
                return True
    return False


class ProblemSolvingService:
    """Durable, self-directed strategy generation, experimentation, and next actions.

    A cycle remains open until later outcome verification establishes that the
    governing objective was reached. Failed or ineffective semantic strategies may
    not be repeated without materially new evidence. Several nonconflicting
    strategies can be selected concurrently, and every selection is attributable.
    """

    def __init__(self, store: Store, learning: LearningService | None = None):
        self.store = store
        self.learning = learning or LearningService(store)

    def _require_mission(self, mission_id: str) -> None:
        if self.store.one(
            "SELECT id FROM missions WHERE id=?", (mission_id,), required=False
        ) is None:
            raise StoreError(f"mission not found: {mission_id}")

    def begin_cycle(
        self,
        *,
        mission_id: str,
        trigger_type: str,
        trigger_id: str,
        objective: Mapping[str, Any],
        governing_range_root: str,
        state: Mapping[str, Any],
        causal_level: int = 0,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if not trigger_type or not trigger_id or not objective:
            raise ValueError("problem-solving cycle requires trigger and objective")
        if not 0 <= causal_level <= 6:
            raise ValueError("causal level must be between zero and six")
        if len(governing_range_root) < 16:
            raise ValueError("governing range root must be a stable content identifier")
        state_root = _digest(dict(state))
        existing = self.store.one(
            """SELECT * FROM problem_solving_cycles_v2
               WHERE mission_id=? AND trigger_type=? AND trigger_id=? AND state_root=?""",
            (mission_id, trigger_type, trigger_id, state_root),
            required=False,
        )
        if existing is not None:
            return existing
        cycle_id = new_id("problem-cycle")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO problem_solving_cycles_v2(
                       id,mission_id,trigger_type,trigger_id,objective_json,
                       governing_range_root,state_root,causal_level,status,
                       created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?, 'open',?,?)""",
                (
                    cycle_id,
                    mission_id,
                    trigger_type,
                    trigger_id,
                    _canonical(dict(objective)),
                    governing_range_root,
                    state_root,
                    causal_level,
                    now,
                    now,
                ),
            )
        return self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )

    def propose_strategy(
        self,
        cycle_id: str,
        *,
        strategy_type: StrategyType,
        strategy: Mapping[str, Any],
        rationale: Mapping[str, Any],
        expected_effect: Mapping[str, Any],
        writable_scope: Sequence[str] | None = None,
        prerequisites: Sequence[str] | None = None,
        evidence_ids: Sequence[str] | None = None,
        proposer_session_id: str | None = None,
        priority: int = 0,
        expected_value: float = 0.0,
        estimated_cost: float = 0.0,
        estimated_risk: float = 0.0,
    ) -> dict[str, Any]:
        cycle = self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )
        if cycle["status"] not in {"open", "experimenting", "executing", "verifying"}:
            raise InvalidTransition("problem-solving cycle is not accepting strategies")
        if not strategy or not rationale or not expected_effect:
            raise ValueError("strategy requires mechanism, rationale, and expected effect")
        scope = _normalize_scope(writable_scope)
        evidence = _ids(evidence_ids)
        prerequisite_ids = _ids(prerequisites)
        semantic_material = {
            "strategy_type": strategy_type,
            "strategy": dict(strategy),
            "expected_effect": dict(expected_effect),
            "writable_scope": scope,
            "prerequisites": prerequisite_ids,
        }
        semantic_fingerprint = _digest(semantic_material)
        prior = self.store.all(
            """SELECT * FROM strategy_candidates_v2
               WHERE cycle_id=? AND semantic_fingerprint=?
               ORDER BY created_at""",
            (cycle_id, semantic_fingerprint),
        )
        prior_evidence: set[str] = set()
        for candidate in prior:
            prior_evidence.update(_loads(candidate["evidence_ids_json"], []))
            attempts = self.store.all(
                "SELECT basis_evidence_ids_json FROM strategy_attempts_v2 WHERE strategy_id=?",
                (candidate["id"],),
            )
            for attempt in attempts:
                prior_evidence.update(_loads(attempt["basis_evidence_ids_json"], []))
        prior_terminal = any(
            candidate["status"] in {"failed", "ineffective", "rejected"}
            for candidate in prior
        )
        if prior_terminal and not (set(evidence) - prior_evidence):
            raise InvalidTransition(
                "materially identical failed strategy requires genuinely new evidence"
            )
        candidate_fingerprint = _digest(
            {
                "semantic_fingerprint": semantic_fingerprint,
                "basis_evidence_ids": evidence,
            }
        )
        existing = self.store.one(
            """SELECT * FROM strategy_candidates_v2
               WHERE cycle_id=? AND strategy_fingerprint=?""",
            (cycle_id, candidate_fingerprint),
            required=False,
        )
        if existing is not None:
            return existing
        for prerequisite_id in prerequisite_ids:
            prerequisite = self.store.one(
                "SELECT status FROM strategy_candidates_v2 WHERE id=? AND cycle_id=?",
                (prerequisite_id, cycle_id),
                required=False,
            )
            if prerequisite is None:
                raise ValueError(f"strategy prerequisite is not in the cycle: {prerequisite_id}")
        candidate_id = new_id("strategy")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO strategy_candidates_v2(
                       id,cycle_id,strategy_type,strategy_fingerprint,rationale_json,
                       expected_effect_json,writable_scope_json,prerequisites_json,
                       evidence_ids_json,proposer_session_id,status,created_at,updated_at,
                       strategy_json,semantic_fingerprint,priority,expected_value,
                       estimated_cost,estimated_risk
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,'proposed',?,?,?,?,?,?,?,?)""",
                (
                    candidate_id,
                    cycle_id,
                    strategy_type,
                    candidate_fingerprint,
                    _canonical(dict(rationale)),
                    _canonical(dict(expected_effect)),
                    _canonical(scope),
                    _canonical(prerequisite_ids),
                    _canonical(evidence),
                    proposer_session_id,
                    now,
                    now,
                    _canonical(dict(strategy)),
                    semantic_fingerprint,
                    priority,
                    expected_value,
                    estimated_cost,
                    estimated_risk,
                ),
            )
        return self.store.one(
            "SELECT * FROM strategy_candidates_v2 WHERE id=?", (candidate_id,)
        )

    def _prerequisites_satisfied(
        self, candidate: Mapping[str, Any], selected_ids: set[str] | None = None
    ) -> bool:
        selected = selected_ids or set()
        for prerequisite_id in _loads(candidate["prerequisites_json"], []):
            if prerequisite_id in selected:
                continue
            prerequisite = self.store.one(
                "SELECT status FROM strategy_candidates_v2 WHERE id=?",
                (prerequisite_id,),
                required=False,
            )
            if prerequisite is None or prerequisite["status"] != "succeeded":
                return False
        return True

    def select_next_actions(
        self,
        cycle_id: str,
        *,
        selected_by_session_id: str,
        rationale: Mapping[str, Any],
        authority: Mapping[str, Any],
        max_parallel: int = 4,
    ) -> dict[str, Any]:
        cycle = self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )
        if cycle["status"] not in {"open", "experimenting", "executing"}:
            raise InvalidTransition("problem-solving cycle is not selecting work")
        if max_parallel <= 0:
            raise ValueError("max_parallel must be positive")
        candidates = self.store.all(
            """SELECT * FROM strategy_candidates_v2
               WHERE cycle_id=? AND status='proposed'
               ORDER BY priority DESC,
                        (expected_value-estimated_cost-estimated_risk) DESC,
                        created_at,id""",
            (cycle_id,),
        )
        chosen: list[dict[str, Any]] = []
        chosen_ids: set[str] = set()
        scopes: list[list[str]] = []
        for candidate in candidates:
            if len(chosen) >= max_parallel:
                break
            if not self._prerequisites_satisfied(candidate, chosen_ids):
                continue
            candidate_scope = _loads(candidate["writable_scope_json"], [])
            if any(_scope_conflicts(candidate_scope, existing_scope) for existing_scope in scopes):
                continue
            chosen.append(candidate)
            chosen_ids.add(str(candidate["id"]))
            scopes.append(candidate_scope)
        if not chosen:
            raise InvalidTransition("no safe eligible strategy is selectable")
        decision_material = {
            "cycle_id": cycle_id,
            "cycle_state_root": cycle["state_root"],
            "causal_level": cycle["causal_level"],
            "selected_strategy_ids": sorted(chosen_ids),
            "selected_by_session_id": selected_by_session_id,
            "rationale": dict(rationale),
            "authority": dict(authority),
        }
        decision_root = _digest(decision_material)
        existing = self.store.one(
            """SELECT * FROM next_action_decisions_v2
               WHERE cycle_id=? AND decision_root=?""",
            (cycle_id, decision_root),
            required=False,
        )
        if existing is not None:
            return existing
        decision_id = new_id("next-action")
        now = utc_now()
        with self.store.transaction() as db:
            db.executemany(
                """UPDATE strategy_candidates_v2
                   SET status='selected',selected_by_session_id=?,updated_at=? WHERE id=?""",
                [(selected_by_session_id, now, candidate["id"]) for candidate in chosen],
            )
            db.execute(
                """INSERT INTO next_action_decisions_v2(
                       id,cycle_id,decision_root,selected_strategy_ids_json,
                       selected_by_session_id,rationale_json,authority_json,
                       status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,'selected',?,?)""",
                (
                    decision_id,
                    cycle_id,
                    decision_root,
                    _canonical(sorted(chosen_ids)),
                    selected_by_session_id,
                    _canonical(dict(rationale)),
                    _canonical(dict(authority)),
                    now,
                    now,
                ),
            )
            db.execute(
                """UPDATE problem_solving_cycles_v2
                   SET status='executing',updated_at=? WHERE id=?""",
                (now, cycle_id),
            )
        return self.store.one(
            "SELECT * FROM next_action_decisions_v2 WHERE id=?", (decision_id,)
        )

    def start_strategy(
        self,
        strategy_id: str,
        *,
        agent_session_id: str,
        execution_id: str | None = None,
        basis_evidence_ids: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        strategy = self.store.one(
            "SELECT * FROM strategy_candidates_v2 WHERE id=?", (strategy_id,)
        )
        if strategy["status"] not in {"selected", "failed", "ineffective"}:
            raise InvalidTransition("strategy is not ready to run")
        basis = _ids(basis_evidence_ids)
        if strategy["status"] in {"failed", "ineffective"}:
            previous_evidence: set[str] = set()
            for attempt in self.store.all(
                "SELECT basis_evidence_ids_json FROM strategy_attempts_v2 WHERE strategy_id=?",
                (strategy_id,),
            ):
                previous_evidence.update(_loads(attempt["basis_evidence_ids_json"], []))
            if not (set(basis) - previous_evidence):
                raise InvalidTransition(
                    "failed strategy cannot run again without materially new evidence"
                )
        attempts = self.store.one(
            "SELECT COUNT(*) AS count FROM strategy_attempts_v2 WHERE strategy_id=?",
            (strategy_id,),
        )
        attempt_number = int(attempts["count"]) + 1
        exact_input_root = _digest(
            {
                "strategy_id": strategy_id,
                "semantic_fingerprint": strategy["semantic_fingerprint"],
                "attempt_number": attempt_number,
                "basis_evidence_ids": basis,
                "agent_session_id": agent_session_id,
                "execution_id": execution_id,
            }
        )
        attempt_id = new_id("strategy-attempt")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO strategy_attempts_v2(
                       id,strategy_id,cycle_id,attempt_number,agent_session_id,
                       execution_id,basis_evidence_ids_json,exact_input_root,
                       disposition,started_at
                   ) VALUES(?,?,?,?,?,?,?,?, 'running',?)""",
                (
                    attempt_id,
                    strategy_id,
                    strategy["cycle_id"],
                    attempt_number,
                    agent_session_id,
                    execution_id,
                    _canonical(basis),
                    exact_input_root,
                    now,
                ),
            )
            db.execute(
                """UPDATE strategy_candidates_v2
                   SET status='running',updated_at=? WHERE id=?""",
                (now, strategy_id),
            )
        return self.store.one(
            "SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,)
        )

    def complete_strategy(
        self,
        attempt_id: str,
        *,
        disposition: Literal["succeeded", "failed", "ineffective", "cancelled", "invalid"],
        result: Mapping[str, Any],
        observed_evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        attempt = self.store.one(
            "SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,)
        )
        if attempt["disposition"] != "running":
            raise InvalidTransition("strategy attempt is already terminal")
        evidence = _ids(observed_evidence_ids)
        if disposition in {"succeeded", "failed", "ineffective"} and not evidence:
            raise ValueError("strategy outcome requires observed evidence")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE strategy_attempts_v2
                   SET result_json=?,observed_evidence_ids_json=?,disposition=?,
                       completed_at=? WHERE id=?""",
                (_canonical(dict(result)), _canonical(evidence), disposition, now, attempt_id),
            )
            db.execute(
                """UPDATE strategy_candidates_v2 SET status=?,result_json=?,updated_at=?
                   WHERE id=?""",
                (disposition, _canonical(dict(result)), now, attempt["strategy_id"]),
            )
            if disposition == "succeeded":
                db.execute(
                    """UPDATE problem_solving_cycles_v2
                       SET status='verifying',updated_at=? WHERE id=?""",
                    (now, attempt["cycle_id"]),
                )
            elif disposition in {"failed", "ineffective", "invalid"}:
                db.execute(
                    """UPDATE problem_solving_cycles_v2
                       SET status='open',causal_level=MIN(6,causal_level+1),updated_at=?
                       WHERE id=?""",
                    (now, attempt["cycle_id"]),
                )
        return self.store.one(
            "SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,)
        )

    def design_discriminating_experiment(
        self,
        cycle_id: str,
        *,
        question: str,
        experiment_type: Literal[
            "command", "historical_replay", "shadow", "canary", "simulation", "comparison"
        ],
        experiment_spec: Mapping[str, Any],
        expected_discrimination: Mapping[str, Any],
        success_criteria: Mapping[str, Any],
        safety_constraints: Mapping[str, Any] | None = None,
        strategy_id: str | None = None,
        hypothesis_id: str | None = None,
    ) -> dict[str, Any]:
        cycle = self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )
        if cycle["status"] not in {"open", "experimenting"}:
            raise InvalidTransition("cycle is not accepting experiments")
        if not question or not expected_discrimination:
            raise ValueError("experiment must discriminate between possible actions")
        design_root = _digest(
            {
                "cycle_id": cycle_id,
                "strategy_id": strategy_id,
                "hypothesis_id": hypothesis_id,
                "question": question,
                "experiment_type": experiment_type,
                "experiment_spec": dict(experiment_spec),
                "expected_discrimination": dict(expected_discrimination),
                "success_criteria": dict(success_criteria),
                "safety_constraints": dict(safety_constraints or {}),
            }
        )
        existing = self.store.one(
            """SELECT * FROM problem_experiment_designs_v2
               WHERE cycle_id=? AND design_root=?""",
            (cycle_id, design_root),
            required=False,
        )
        if existing is not None:
            return existing
        experiment = self.learning.design_experiment(
            mission_id=cycle["mission_id"],
            experiment_type=experiment_type,
            design=dict(experiment_spec),
            success_criteria=dict(success_criteria),
            safety_constraints=dict(safety_constraints or {}),
            hypothesis_id=hypothesis_id,
        )
        design_id = new_id("problem-experiment")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO problem_experiment_designs_v2(
                       id,cycle_id,strategy_id,hypothesis_id,design_root,question,
                       experiment_spec_json,expected_discrimination_json,status,
                       experiment_id,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,'designed',?,?,?)""",
                (
                    design_id,
                    cycle_id,
                    strategy_id,
                    hypothesis_id,
                    design_root,
                    question,
                    _canonical(dict(experiment_spec)),
                    _canonical(dict(expected_discrimination)),
                    experiment["id"],
                    now,
                    now,
                ),
            )
            db.execute(
                """UPDATE problem_solving_cycles_v2
                   SET status='experimenting',updated_at=? WHERE id=?""",
                (now, cycle_id),
            )
        return self.store.one(
            "SELECT * FROM problem_experiment_designs_v2 WHERE id=?", (design_id,)
        )

    def run_command_experiment(
        self,
        design_id: str,
        *,
        command: Sequence[str],
        cwd: str | Path,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        design = self.store.one(
            "SELECT * FROM problem_experiment_designs_v2 WHERE id=?", (design_id,)
        )
        if design["status"] != "designed":
            raise InvalidTransition("problem experiment is not awaiting execution")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE problem_experiment_designs_v2
                   SET status='running',updated_at=? WHERE id=?""",
                (utc_now(), design_id),
            )
        try:
            result = self.learning.run_command_experiment(
                design["experiment_id"],
                command=command,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
            )
        except BaseException:
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE problem_experiment_designs_v2
                       SET status='failed',updated_at=? WHERE id=?""",
                    (utc_now(), design_id),
                )
            raise
        status = "succeeded" if result["disposition"] == "passed" else result["disposition"]
        with self.store.transaction() as db:
            db.execute(
                """UPDATE problem_experiment_designs_v2
                   SET status=?,updated_at=? WHERE id=?""",
                (status, utc_now(), design_id),
            )
            db.execute(
                """UPDATE problem_solving_cycles_v2
                   SET status='open',updated_at=? WHERE id=?""",
                (utc_now(), design["cycle_id"]),
            )
        return result

    def next_action(self, cycle_id: str) -> dict[str, Any]:
        cycle = self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )
        if cycle["status"] == "resolved":
            return {"action": "none", "reason": "objective_verified"}
        running = self.store.all(
            """SELECT id,strategy_type FROM strategy_candidates_v2
               WHERE cycle_id=? AND status IN ('selected','running')""",
            (cycle_id,),
        )
        if running:
            return {
                "action": "continue_selected_strategies",
                "strategy_ids": [row["id"] for row in running],
            }
        experiments = self.store.all(
            """SELECT id,status FROM problem_experiment_designs_v2
               WHERE cycle_id=? AND status IN ('designed','running')""",
            (cycle_id,),
        )
        if experiments:
            return {
                "action": "run_discriminating_experiment",
                "experiment_design_ids": [row["id"] for row in experiments],
            }
        proposed = self.store.all(
            """SELECT id FROM strategy_candidates_v2
               WHERE cycle_id=? AND status='proposed'""",
            (cycle_id,),
        )
        if proposed:
            return {
                "action": "select_maximal_safe_strategy_set",
                "strategy_ids": [row["id"] for row in proposed],
            }
        level = int(cycle["causal_level"])
        return {
            "action": "generate_strategies",
            "required_strategy_type": _CAUSAL_LEVEL_STRATEGIES[level],
            "causal_level": level,
            "objective": _loads(cycle["objective_json"], {}),
        }

    def verify_cycle(
        self,
        cycle_id: str,
        *,
        disposition: Literal["effective", "ineffective", "inconclusive", "regressed"],
        metrics: Mapping[str, Any],
        evidence_ids: Sequence[str],
        verifier_session_id: str | None = None,
    ) -> dict[str, Any]:
        cycle = self.store.one(
            "SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,)
        )
        if cycle["status"] not in {"verifying", "executing", "open"}:
            raise InvalidTransition("cycle is not awaiting outcome verification")
        evidence = _ids(evidence_ids)
        if disposition != "inconclusive" and not evidence:
            raise ValueError("cycle verification requires observed outcome evidence")
        verification_root = _digest(
            {
                "cycle_id": cycle_id,
                "state_root": cycle["state_root"],
                "disposition": disposition,
                "metrics": dict(metrics),
                "evidence_ids": evidence,
                "verifier_session_id": verifier_session_id,
            }
        )
        existing = self.store.one(
            """SELECT * FROM problem_cycle_verifications_v2
               WHERE cycle_id=? AND verification_root=?""",
            (cycle_id, verification_root),
            required=False,
        )
        if existing is not None:
            return existing
        verification_id = new_id("cycle-verification")
        now = utc_now()
        status = "resolved" if disposition == "effective" else "open"
        causal_increment = 1 if disposition in {"ineffective", "regressed"} else 0
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO problem_cycle_verifications_v2(
                       id,cycle_id,disposition,metrics_json,evidence_ids_json,
                       verifier_session_id,verification_root,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    verification_id,
                    cycle_id,
                    disposition,
                    _canonical(dict(metrics)),
                    _canonical(evidence),
                    verifier_session_id,
                    verification_root,
                    now,
                ),
            )
            db.execute(
                """UPDATE problem_solving_cycles_v2
                   SET status=?,causal_level=MIN(6,causal_level+?),updated_at=? WHERE id=?""",
                (status, causal_increment, now, cycle_id),
            )
            if disposition in {"ineffective", "regressed"}:
                db.execute(
                    """UPDATE strategy_candidates_v2
                       SET status='ineffective',updated_at=?
                       WHERE cycle_id=? AND status='succeeded'""",
                    (now, cycle_id),
                )
        return self.store.one(
            "SELECT * FROM problem_cycle_verifications_v2 WHERE id=?",
            (verification_id,),
        )

    def record_unexpected_success(
        self,
        cycle_id: str,
        *,
        source_id: str,
        mechanism: Mapping[str, Any],
        outcome: Mapping[str, Any],
        evidence_ids: Sequence[str],
        proposer_session_id: str | None = None,
    ) -> dict[str, Any]:
        return self.propose_strategy(
            cycle_id,
            strategy_type="success_generalization",
            strategy={
                "source_id": source_id,
                "mechanism": dict(mechanism),
                "generalization_mode": "bounded_candidate",
            },
            rationale={
                "reason": "unexpected success may encode a reusable method",
                "automatic_global_promotion": False,
            },
            expected_effect={
                "test_bounded_reuse": True,
                "preserve_counterexamples": True,
            },
            evidence_ids=evidence_ids,
            proposer_session_id=proposer_session_id,
            priority=1,
            expected_value=0.5,
            estimated_cost=0.1,
            estimated_risk=0.2,
        )
