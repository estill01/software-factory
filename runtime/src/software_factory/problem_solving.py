from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from librsi import CandidateSnapshot, ImprovementResult, TargetSnapshot

from .errors import InvalidTransition, StoreError
from .integrations.librsi import LibRSIIntegration
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

    def __init__(
        self,
        store: Store,
        learning: LearningService | None = None,
        *,
        semantic: LibRSIIntegration | None = None,
    ):
        self.store = store
        if learning is not None and semantic is not None and learning.semantic is not semantic:
            raise ValueError("problem solving requires one shared libRSI semantic owner")
        self.learning = learning or LearningService(store, semantic=semantic)
        self.semantic = semantic or self.learning.semantic

    def _require_mission(self, mission_id: str) -> None:
        if (
            self.store.one("SELECT id FROM missions WHERE id=?", (mission_id,), required=False)
            is None
        ):
            raise StoreError(f"mission not found: {mission_id}")

    @staticmethod
    def _operational_projection(candidate: CandidateSnapshot) -> dict[str, Any]:
        projection = candidate.request.intervention.specification.get("software_factory_operation")
        if not isinstance(projection, Mapping):
            raise InvalidTransition(
                "selected libRSI candidate lacks an exact Factory operational projection"
            )
        strategy = projection.get("strategy")
        expected_effect = projection.get("expected_effect")
        writable_scope = projection.get("writable_scope")
        strategy_type = projection.get("strategy_type")
        if (
            not isinstance(strategy_type, str)
            or not isinstance(strategy, Mapping)
            or not isinstance(expected_effect, Mapping)
            or not isinstance(writable_scope, Sequence)
            or isinstance(writable_scope, (str, bytes))
            or "librsi_candidate_root" in strategy
        ):
            raise InvalidTransition("selected libRSI Factory projection is malformed")
        return {
            "strategy_type": strategy_type,
            "strategy": dict(strategy),
            "expected_effect": dict(expected_effect),
            "writable_scope": _normalize_scope([str(value) for value in writable_scope]),
        }

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
        return self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))

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
        with self.store.transaction(mode="IMMEDIATE"):
            return self._propose_strategy_locked(
                cycle_id,
                strategy_type=strategy_type,
                strategy=strategy,
                rationale=rationale,
                expected_effect=expected_effect,
                writable_scope=writable_scope,
                prerequisites=prerequisites,
                evidence_ids=evidence_ids,
                proposer_session_id=proposer_session_id,
                priority=priority,
                expected_value=expected_value,
                estimated_cost=estimated_cost,
                estimated_risk=estimated_risk,
            )

    def _propose_strategy_locked(
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
        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
        if cycle["status"] not in {"open", "experimenting", "executing", "verifying"}:
            raise InvalidTransition("problem-solving cycle is not accepting strategies")
        if not strategy or not rationale or not expected_effect:
            raise ValueError("strategy requires mechanism, rationale, and expected effect")
        scope = _normalize_scope(writable_scope)
        evidence = _ids(evidence_ids)
        prerequisite_ids = _ids(prerequisites)
        candidate_root = str(strategy.get("librsi_candidate_root") or "")
        if not candidate_root:
            raise InvalidTransition(
                "operational strategy requires an exact libRSI improvement candidate root"
            )
        semantic_candidate = self.semantic.load_record(candidate_root)
        if type(semantic_candidate) is not CandidateSnapshot:
            raise InvalidTransition("strategy root is not an exact libRSI CandidateSnapshot")
        binding = self.store.one(
            """SELECT candidate.currentness_root,
                      result.librsi_root AS improvement_result_root
               FROM librsi_record_bindings AS candidate
               JOIN librsi_record_bindings AS result
                 ON result.mission_id=candidate.mission_id
                AND result.operational_subject_type=candidate.operational_subject_type
                AND result.operational_subject_id=candidate.operational_subject_id
                AND result.semantic_role='improvement_result'
                AND result.currentness_root=candidate.currentness_root
               WHERE candidate.mission_id=?
                 AND candidate.operational_subject_type='problem_solving_cycle'
                 AND candidate.operational_subject_id=?
                 AND candidate.librsi_root=?
                 AND candidate.semantic_role='improvement_candidate'
               ORDER BY result.created_at DESC,candidate.created_at DESC LIMIT 1""",
            (cycle["mission_id"], cycle_id, candidate_root),
            required=False,
        )
        if (
            binding is None
            or semantic_candidate.snapshot.target.target_id
            != f"software-factory-mission:{cycle['mission_id']}"
        ):
            raise InvalidTransition("strategy candidate is not bound to this exact mission")
        currentness = self.semantic.load_record(str(binding["currentness_root"]))
        if type(currentness) is not TargetSnapshot:
            raise StoreError("strategy candidate lacks exact host currentness")
        self.semantic.require_live_currentness(
            mission_id=str(cycle["mission_id"]), snapshot=currentness
        )
        improvement_result = self.semantic.load_record(str(binding["improvement_result_root"]))
        if type(improvement_result) is not ImprovementResult or improvement_result.handoff is None:
            raise InvalidTransition("strategy candidate lacks an exact selected improvement result")
        selected_roots = {
            reference.root for reference in improvement_result.handoff.selection.selected
        }
        if (
            candidate_root not in selected_roots
            or improvement_result.request.baseline != currentness
        ):
            raise InvalidTransition(
                "strategy candidate was not selected by its exact improvement result"
            )
        projection = self._operational_projection(semantic_candidate)
        projected_strategy = {
            **projection["strategy"],
            "librsi_candidate_root": candidate_root,
        }
        if (
            strategy_type != projection["strategy_type"]
            or dict(strategy) != projected_strategy
            or dict(expected_effect) != projection["expected_effect"]
            or scope != projection["writable_scope"]
        ):
            raise InvalidTransition(
                "operational strategy differs from the exact selected libRSI candidate projection"
            )
        semantic_fingerprint = candidate_root
        prior = self.store.all(
            """SELECT * FROM strategy_candidates_v2
               WHERE cycle_id=? AND semantic_fingerprint=?
               ORDER BY created_at""",
            (cycle_id, semantic_fingerprint),
        )
        operational_material = {
            "strategy_type": strategy_type,
            "strategy": dict(strategy),
            "expected_effect": dict(expected_effect),
            "writable_scope": scope,
            "prerequisites": prerequisite_ids,
        }
        for candidate in prior:
            if candidate["status"] not in {"proposed", "selected", "running"}:
                continue
            prior_material = {
                "strategy_type": candidate["strategy_type"],
                "strategy": _loads(candidate["strategy_json"], {}),
                "expected_effect": _loads(candidate["expected_effect_json"], {}),
                "writable_scope": _loads(candidate["writable_scope_json"], []),
                "prerequisites": _loads(candidate["prerequisites_json"], []),
            }
            if prior_material == operational_material:
                return candidate
            raise InvalidTransition(
                "selected libRSI candidate already has a different active operational projection"
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
            candidate["status"] in {"failed", "ineffective", "rejected"} for candidate in prior
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
        self.semantic.require_live_currentness(
            mission_id=str(cycle["mission_id"]), snapshot=currentness
        )
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
        return self.store.one("SELECT * FROM strategy_candidates_v2 WHERE id=?", (candidate_id,))

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

    def record_improvement_result(
        self,
        cycle_id: str,
        *,
        result: ImprovementResult,
        currentness: TargetSnapshot,
    ) -> dict[str, Any]:
        with self.store.transaction(mode="IMMEDIATE"):
            return self._record_improvement_result_locked(
                cycle_id,
                result=result,
                currentness=currentness,
            )

    def _record_improvement_result_locked(
        self,
        cycle_id: str,
        *,
        result: ImprovementResult,
        currentness: TargetSnapshot,
    ) -> dict[str, Any]:
        """Admit the exact libRSI improvement outcome for one operational cycle."""

        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
        if cycle["status"] not in {"open", "experimenting", "executing", "verifying"}:
            raise InvalidTransition("problem-solving cycle cannot accept an improvement result")
        if type(result) is not ImprovementResult:
            raise TypeError("problem solving requires an exact ImprovementResult")
        self.semantic.record_workflow_result(
            mission_id=str(cycle["mission_id"]),
            subject_type="problem_solving_cycle",
            subject_id=cycle_id,
            result=result,
            currentness=currentness,
        )
        return {
            "cycle_id": cycle_id,
            "improvement_result_root": result.root,
            "currentness_root": currentness.root,
            "disposition": result.disposition,
            "candidate_roots": [
                reference.root
                for reference in (
                    result.handoff.selection.selected if result.handoff is not None else ()
                )
            ],
        }

    def select_next_actions(
        self,
        cycle_id: str,
        *,
        selected_by_session_id: str,
        rationale: Mapping[str, Any],
        authority: Mapping[str, Any],
        improvement_result_root: str,
        currentness_root: str,
        max_parallel: int = 4,
    ) -> dict[str, Any]:
        with self.store.transaction(mode="IMMEDIATE"):
            return self._select_next_actions_locked(
                cycle_id,
                selected_by_session_id=selected_by_session_id,
                rationale=rationale,
                authority=authority,
                improvement_result_root=improvement_result_root,
                currentness_root=currentness_root,
                max_parallel=max_parallel,
            )

    def _select_next_actions_locked(
        self,
        cycle_id: str,
        *,
        selected_by_session_id: str,
        rationale: Mapping[str, Any],
        authority: Mapping[str, Any],
        improvement_result_root: str,
        currentness_root: str,
        max_parallel: int = 4,
    ) -> dict[str, Any]:
        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
        if cycle["status"] not in {"open", "experimenting", "executing"}:
            raise InvalidTransition("problem-solving cycle is not selecting work")
        if max_parallel <= 0:
            raise ValueError("max_parallel must be positive")
        result = self.semantic.load_record(improvement_result_root)
        if type(result) is not ImprovementResult:
            raise InvalidTransition("next action requires an exact libRSI ImprovementResult")
        binding = self.store.one(
            """SELECT currentness_root FROM librsi_record_bindings
               WHERE mission_id=? AND operational_subject_type='problem_solving_cycle'
                 AND operational_subject_id=? AND semantic_role='improvement_result'
                 AND librsi_root=?""",
            (cycle["mission_id"], cycle_id, improvement_result_root),
            required=False,
        )
        if binding is None or str(binding["currentness_root"]) != currentness_root:
            raise InvalidTransition(
                "improvement result is not bound to this cycle and exact currentness"
            )
        currentness = self.semantic.load_record(currentness_root)
        if type(currentness) is not TargetSnapshot:
            raise InvalidTransition("improvement result lacks exact host currentness")
        self.semantic.require_live_currentness(
            mission_id=str(cycle["mission_id"]), snapshot=currentness
        )
        if result.request.baseline != currentness or result.handoff is None:
            raise InvalidTransition("improvement result has no current selected handoff")
        selected_roots = {reference.root for reference in result.handoff.selection.selected}
        candidates = self.store.all(
            """SELECT * FROM strategy_candidates_v2
               WHERE cycle_id=? AND status='proposed'
               ORDER BY created_at,id""",
            (cycle_id,),
        )
        chosen = [
            candidate
            for candidate in candidates
            if str(_loads(candidate["strategy_json"], {}).get("librsi_candidate_root") or "")
            in selected_roots
        ]
        matched_roots = {
            str(_loads(candidate["strategy_json"], {})["librsi_candidate_root"])
            for candidate in chosen
        }
        if matched_roots != selected_roots:
            raise InvalidTransition(
                "Factory lacks an operational projection for every selected libRSI candidate"
            )
        if len(chosen) != len(selected_roots):
            raise InvalidTransition(
                "each selected libRSI candidate requires exactly one operational projection"
            )
        if not chosen:
            raise InvalidTransition("libRSI selected no operationally mapped strategy")
        if len(chosen) > max_parallel:
            raise InvalidTransition("selected libRSI set exceeds current host parallel capacity")
        chosen_ids = {str(candidate["id"]) for candidate in chosen}
        if any(not self._prerequisites_satisfied(candidate, chosen_ids) for candidate in chosen):
            raise InvalidTransition("selected libRSI set has unsatisfied host prerequisites")
        scopes = [_loads(candidate["writable_scope_json"], []) for candidate in chosen]
        for index, scope in enumerate(scopes):
            if any(_scope_conflicts(scope, other) for other in scopes[index + 1 :]):
                raise InvalidTransition("selected libRSI set has conflicting host writable scopes")
        decision_material = {
            "cycle_id": cycle_id,
            "cycle_state_root": cycle["state_root"],
            "improvement_result_root": improvement_result_root,
            "currentness_root": currentness_root,
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
        self.semantic.require_live_currentness(
            mission_id=str(cycle["mission_id"]), snapshot=currentness
        )
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
                    _canonical(
                        {
                            **dict(authority),
                            "semantic_owner": "libRSI",
                            "improvement_result_root": improvement_result_root,
                            "currentness_root": currentness_root,
                        }
                    ),
                    now,
                    now,
                ),
            )
            db.execute(
                """UPDATE problem_solving_cycles_v2
                   SET status='executing',updated_at=? WHERE id=?""",
                (now, cycle_id),
            )
        return self.store.one("SELECT * FROM next_action_decisions_v2 WHERE id=?", (decision_id,))

    def start_strategy(
        self,
        strategy_id: str,
        *,
        agent_session_id: str,
        execution_id: str | None = None,
        basis_evidence_ids: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        strategy = self.store.one("SELECT * FROM strategy_candidates_v2 WHERE id=?", (strategy_id,))
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
        return self.store.one("SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,))

    def complete_strategy(
        self,
        attempt_id: str,
        *,
        disposition: Literal["succeeded", "failed", "ineffective", "cancelled", "invalid"],
        result: Mapping[str, Any],
        observed_evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        attempt = self.store.one("SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,))
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
        return self.store.one("SELECT * FROM strategy_attempts_v2 WHERE id=?", (attempt_id,))

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
        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
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
        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
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
                "action": "await_librsi_improvement_result",
                "strategy_ids": [row["id"] for row in proposed],
                "semantic_owner": "libRSI",
            }
        return {
            "action": "request_librsi_improvement_cycle",
            "semantic_owner": "libRSI",
            "objective": _loads(cycle["objective_json"], {}),
            "currentness_required": True,
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
        cycle = self.store.one("SELECT * FROM problem_solving_cycles_v2 WHERE id=?", (cycle_id,))
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
        improvement_candidate_root: str,
        proposer_session_id: str | None = None,
    ) -> dict[str, Any]:
        return self.propose_strategy(
            cycle_id,
            strategy_type="success_generalization",
            strategy={
                "source_id": source_id,
                "mechanism": dict(mechanism),
                "generalization_mode": "bounded_candidate",
                "librsi_candidate_root": improvement_candidate_root,
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
