from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from librsi import (
    CommandObservation,
    Evidence,
    ExperimentPolicy,
    ExperimentSpec,
    Hypothesis,
    HypothesisPolicy,
    Observation,
    TargetSnapshot,
)

from .errors import InvalidTransition, StoreError
from .integrations.librsi import LibRSIIntegration
from .store import Store
from .util import new_id, utc_now

SignalKind = Literal["failure", "success", "mixed", "opportunity"]
EvaluationPhase = Literal["historical_replay", "shadow", "canary", "qa"]


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


def _path_value(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _condition_matches(condition: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    actual = _path_value(event, str(condition.get("path", "")))
    expected = condition.get("value")
    operator = condition.get("op", "eq")
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "in":
        return actual in expected if isinstance(expected, list) else False
    if operator == "contains":
        return expected in actual if isinstance(actual, (str, list, tuple, set)) else False
    if operator == "exists":
        return (actual is not None) is bool(expected)
    if operator in {"gt", "gte", "lt", "lte"}:
        try:
            if operator == "gt":
                return actual > expected
            if operator == "gte":
                return actual >= expected
            if operator == "lt":
                return actual < expected
            return actual <= expected
        except TypeError:
            return False
    raise ValueError(f"unsupported detector operator: {operator}")


class LearningService:
    """Observed-stream learning, signal promotion, reflection, and experiments.

    Signal candidates are inert until replay, shadow, canary, and independent QA
    evidence all pass. Promotion atomically activates a detector and its governed
    response route. Historical imports can contribute evidence but can never route
    live effects.
    """

    def __init__(self, store: Store, *, semantic: LibRSIIntegration | None = None) -> None:
        self.store = store
        self.semantic = semantic or LibRSIIntegration(store)

    def _require_mission(self, mission_id: str) -> None:
        if (
            self.store.one("SELECT id FROM missions WHERE id=?", (mission_id,), required=False)
            is None
        ):
            raise StoreError(f"mission not found: {mission_id}")

    def record_event(
        self,
        *,
        mission_id: str,
        source_type: str,
        source_id: str,
        event_type: str,
        classification: Literal[
            "neutral", "progress", "failure", "success", "mixed", "opportunity"
        ] = "neutral",
        attributes: Mapping[str, Any] | None = None,
        evidence_ids: Sequence[str] | None = None,
        occurred_at: str | None = None,
        historical_only: bool = False,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        event_id = new_id("stream-event")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO observed_stream_events(
                       id,mission_id,source_type,source_id,event_type,classification,
                       attributes_json,evidence_ids_json,occurred_at,ingested_at,historical_only
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id,
                    mission_id,
                    source_type,
                    source_id,
                    event_type,
                    classification,
                    _canonical(dict(attributes or {})),
                    _canonical(_ids(evidence_ids)),
                    occurred_at or now,
                    now,
                    1 if historical_only else 0,
                ),
            )
        return self.store.one("SELECT * FROM observed_stream_events WHERE id=?", (event_id,))

    def _normalized_event(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "mission_id": row["mission_id"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "event_type": row["event_type"],
            "classification": row["classification"],
            "attributes": _loads(row["attributes_json"], {}),
            "occurred_at": row["occurred_at"],
            "historical_only": bool(row["historical_only"]),
        }

    def create_candidate(
        self,
        *,
        mission_id: str,
        signal_kind: SignalKind,
        name: str,
        detector_spec: Mapping[str, Any],
        response_spec: Mapping[str, Any],
        discovery_evidence: Mapping[str, Any],
        counterexamples: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if response_spec.get("action") not in {
            "reflect",
            "remediate",
            "replan",
            "rollback",
            "generalize",
            "experiment",
            "notify",
            "contain",
        }:
            raise ValueError("response route has an unsupported action")
        material = {
            "signal_kind": signal_kind,
            "detector_spec": dict(detector_spec),
            "response_spec": dict(response_spec),
        }
        fingerprint = _digest(material)
        existing = self.store.one(
            """SELECT * FROM learned_signal_candidates
               WHERE mission_id=? AND candidate_fingerprint=?""",
            (mission_id, fingerprint),
            required=False,
        )
        if existing is not None:
            return existing
        candidate_id = new_id("signal-candidate")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO learned_signal_candidates(
                       id,mission_id,signal_kind,name,candidate_fingerprint,
                       detector_spec_json,response_spec_json,discovery_evidence_json,
                       counterexamples_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'candidate',?,?)""",
                (
                    candidate_id,
                    mission_id,
                    signal_kind,
                    name,
                    fingerprint,
                    _canonical(dict(detector_spec)),
                    _canonical(dict(response_spec)),
                    _canonical(dict(discovery_evidence)),
                    _canonical([dict(item) for item in (counterexamples or ())]),
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM learned_signal_candidates WHERE id=?", (candidate_id,))

    def discover_recurring_sequences(
        self,
        mission_id: str,
        *,
        window: int = 500,
        min_support: int = 3,
        sequence_length: int = 2,
    ) -> list[dict[str, Any]]:
        if not 2 <= sequence_length <= 5:
            raise ValueError("sequence_length must be between 2 and 5")
        if min_support < 2:
            raise ValueError("min_support must be at least 2")
        rows = list(
            reversed(
                self.store.all(
                    """SELECT * FROM observed_stream_events WHERE mission_id=?
                       ORDER BY occurred_at DESC,id DESC LIMIT ?""",
                    (mission_id, window),
                )
            )
        )
        normalized = [self._normalized_event(row) for row in rows]
        sequences: Counter[tuple[tuple[str, str], ...]] = Counter()
        examples: dict[tuple[tuple[str, str], ...], list[str]] = defaultdict(list)
        for index in range(0, len(normalized) - sequence_length + 1):
            segment = normalized[index : index + sequence_length]
            key = tuple((str(item["event_type"]), str(item["classification"])) for item in segment)
            sequences[key] += 1
            examples[key].extend(str(item["id"]) for item in segment)

        candidates: list[dict[str, Any]] = []
        for sequence, support in sequences.most_common():
            if support < min_support:
                continue
            classifications = {classification for _, classification in sequence}
            if "failure" in classifications:
                kind: SignalKind = "failure"
                action = "remediate"
            elif "success" in classifications:
                kind = "success"
                action = "generalize"
            elif "opportunity" in classifications:
                kind = "opportunity"
                action = "experiment"
            elif "mixed" in classifications or len(classifications - {"neutral", "progress"}) > 1:
                kind = "mixed"
                action = "reflect"
            else:
                continue
            candidate = self.create_candidate(
                mission_id=mission_id,
                signal_kind=kind,
                name=" -> ".join(event_type for event_type, _ in sequence),
                detector_spec={
                    "sequence": [
                        {"event_type": event_type, "classification": classification}
                        for event_type, classification in sequence
                    ]
                },
                response_spec={"action": action, "mode": "governed"},
                discovery_evidence={
                    "support": support,
                    "event_ids": sorted(set(examples[sequence])),
                    "window": window,
                },
            )
            candidates.append(candidate)
        return candidates

    def record_evaluation(
        self,
        candidate_id: str,
        *,
        phase: EvaluationPhase,
        disposition: Literal["passed", "failed", "inconclusive"],
        metrics: Mapping[str, Any],
        evidence_ids: Sequence[str],
        evaluator_session_id: str | None = None,
    ) -> dict[str, Any]:
        candidate = self.store.one(
            "SELECT * FROM learned_signal_candidates WHERE id=?", (candidate_id,)
        )
        if candidate["status"] in {"promoted", "rejected", "superseded"}:
            raise InvalidTransition("terminal signal candidate cannot be evaluated")
        if not evidence_ids:
            raise ValueError("signal evaluation requires observed evidence")
        column = {
            "historical_replay": "replay_status",
            "shadow": "shadow_status",
            "canary": "canary_status",
            "qa": "qa_status",
        }[phase]
        evaluation_id = new_id("signal-evaluation")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO signal_evaluations_v2(
                       id,candidate_id,phase,disposition,metrics_json,evidence_ids_json,
                       evaluator_session_id,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    evaluation_id,
                    candidate_id,
                    phase,
                    disposition,
                    _canonical(dict(metrics)),
                    _canonical(_ids(evidence_ids)),
                    evaluator_session_id,
                    now,
                ),
            )
            candidate_status = "rejected" if disposition == "failed" else "evaluating"
            db.execute(
                f"""UPDATE learned_signal_candidates
                    SET {column}=?, status=?, updated_at=? WHERE id=?""",
                (disposition, candidate_status, now, candidate_id),
            )
        return self.store.one("SELECT * FROM signal_evaluations_v2 WHERE id=?", (evaluation_id,))

    def promote_candidate(
        self,
        candidate_id: str,
        *,
        activated_by_session_id: str | None = None,
    ) -> dict[str, Any]:
        candidate = self.store.one(
            "SELECT * FROM learned_signal_candidates WHERE id=?", (candidate_id,)
        )
        required = {
            "replay_status": "passed",
            "shadow_status": "passed",
            "canary_status": "passed",
            "qa_status": "passed",
        }
        missing = [key for key, expected in required.items() if candidate[key] != expected]
        if missing:
            raise InvalidTransition(
                "signal promotion requires passing replay, shadow, canary, and QA"
            )
        detector = _loads(candidate["detector_spec_json"], {})
        response = _loads(candidate["response_spec_json"], {})
        bundle_root = _digest(
            {
                "candidate_id": candidate_id,
                "detector": detector,
                "response": response,
            }
        )
        bundle_id = new_id("signal-bundle")
        now = utc_now()
        with self.store.transaction() as db:
            latest = db.execute(
                """SELECT COALESCE(MAX(version),0) AS version FROM active_signal_bundles
                   WHERE mission_id=? AND bundle_root=?""",
                (candidate["mission_id"], bundle_root),
            ).fetchone()
            version = int(latest["version"]) + 1
            db.execute(
                """INSERT INTO active_signal_bundles(
                       id,mission_id,candidate_id,signal_kind,detector_spec_json,
                       response_spec_json,bundle_root,version,status,
                       activated_by_session_id,activated_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?, 'active',?,?,?)""",
                (
                    bundle_id,
                    candidate["mission_id"],
                    candidate_id,
                    candidate["signal_kind"],
                    candidate["detector_spec_json"],
                    candidate["response_spec_json"],
                    bundle_root,
                    version,
                    activated_by_session_id,
                    now,
                    now,
                ),
            )
            db.execute(
                """UPDATE learned_signal_candidates
                   SET status='promoted', updated_at=? WHERE id=?""",
                (now, candidate_id),
            )
        return self.store.one("SELECT * FROM active_signal_bundles WHERE id=?", (bundle_id,))

    def _bundle_matches(
        self,
        bundle: Mapping[str, Any],
        event: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        detector = _loads(bundle["detector_spec_json"], {})
        normalized = self._normalized_event(event)
        event_types = detector.get("event_types")
        if isinstance(event_types, list) and normalized["event_type"] not in event_types:
            return None
        classifications = detector.get("classifications")
        if (
            isinstance(classifications, list)
            and normalized["classification"] not in classifications
        ):
            return None
        conditions = detector.get("where", [])
        if not isinstance(conditions, list) or not all(
            isinstance(item, Mapping) for item in conditions
        ):
            return None
        if not all(_condition_matches(item, normalized) for item in conditions):
            return None
        sequence = detector.get("sequence")
        matched_ids = [normalized["id"]]
        if isinstance(sequence, list) and sequence:
            history = list(
                reversed(
                    self.store.all(
                        """SELECT * FROM observed_stream_events
                           WHERE mission_id=? AND occurred_at<=?
                           ORDER BY occurred_at DESC,id DESC LIMIT ?""",
                        (event["mission_id"], event["occurred_at"], len(sequence)),
                    )
                )
            )
            if len(history) != len(sequence):
                return None
            for expected, actual_row in zip(sequence, history, strict=True):
                actual = self._normalized_event(actual_row)
                if expected.get("event_type") != actual["event_type"]:
                    return None
                expected_classification = expected.get("classification")
                if expected_classification and expected_classification != actual["classification"]:
                    return None
            matched_ids = [str(row["id"]) for row in history]
        return {"event_ids": matched_ids, "detector": detector}

    def route_event(self, event_id: str) -> list[dict[str, Any]]:
        event = self.store.one("SELECT * FROM observed_stream_events WHERE id=?", (event_id,))
        if event["historical_only"]:
            return []
        bundles = self.store.all(
            """SELECT * FROM active_signal_bundles
               WHERE mission_id=? AND status IN ('active','narrowed')
               ORDER BY activated_at""",
            (event["mission_id"],),
        )
        occurrences: list[dict[str, Any]] = []
        for bundle in bundles:
            match = self._bundle_matches(bundle, event)
            if match is None:
                continue
            occurrence_id = new_id("signal-occurrence")
            response = _loads(bundle["response_spec_json"], {})
            with self.store.transaction() as db:
                db.execute(
                    """INSERT OR IGNORE INTO signal_occurrences(
                           id,mission_id,bundle_id,event_id,match_json,
                           routed_action_json,status,created_at
                       ) VALUES(?,?,?,?,?,?,'routed',?)""",
                    (
                        occurrence_id,
                        event["mission_id"],
                        bundle["id"],
                        event_id,
                        _canonical(match),
                        _canonical(response),
                        utc_now(),
                    ),
                )
            occurrence = self.store.one(
                """SELECT * FROM signal_occurrences
                   WHERE bundle_id=? AND event_id=?""",
                (bundle["id"], event_id),
            )
            occurrences.append(occurrence)
        return occurrences

    def record_occurrence_effectiveness(
        self,
        occurrence_id: str,
        *,
        disposition: Literal[
            "effective",
            "ineffective",
            "false_positive",
            "false_negative",
            "harmful",
            "inconclusive",
        ],
        metrics: Mapping[str, Any],
        evidence_ids: Sequence[str],
        recurrence_detected: bool = False,
    ) -> dict[str, Any]:
        occurrence = self.store.one("SELECT * FROM signal_occurrences WHERE id=?", (occurrence_id,))
        if not evidence_ids:
            raise ValueError("signal effectiveness review requires evidence")
        review_id = new_id("signal-effectiveness")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO signal_effectiveness_reviews(
                       id,occurrence_id,bundle_id,disposition,recurrence_detected,
                       metrics_json,evidence_ids_json,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    review_id,
                    occurrence_id,
                    occurrence["bundle_id"],
                    disposition,
                    1 if recurrence_detected else 0,
                    _canonical(dict(metrics)),
                    _canonical(_ids(evidence_ids)),
                    now,
                ),
            )
            occurrence_status = "succeeded" if disposition == "effective" else "failed"
            db.execute(
                """UPDATE signal_occurrences
                   SET status=?, completed_at=? WHERE id=?""",
                (occurrence_status, now, occurrence_id),
            )
            if disposition in {"harmful", "false_positive"}:
                db.execute(
                    """UPDATE active_signal_bundles
                       SET status='rolled_back', updated_at=? WHERE id=?""",
                    (now, occurrence["bundle_id"]),
                )
            elif disposition in {"ineffective", "false_negative"} or recurrence_detected:
                db.execute(
                    """UPDATE active_signal_bundles
                       SET status='revising', updated_at=? WHERE id=?""",
                    (now, occurrence["bundle_id"]),
                )
        return self.store.one("SELECT * FROM signal_effectiveness_reviews WHERE id=?", (review_id,))

    def create_reflection(
        self,
        *,
        mission_id: str,
        reflection_type: Literal["live", "checkpoint", "terminal", "cross_run", "meta"],
        source_type: str,
        source_id: str,
        evidence_ids: Sequence[str],
        observations: Mapping[str, Any],
        conclusions: Mapping[str, Any],
        proposed_actions: Sequence[Mapping[str, Any]] | None = None,
        confidence: float,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("reflection confidence must be between zero and one")
        evidence = _ids(evidence_ids)
        if not evidence:
            raise ValueError("reflection requires exact evidence references")
        prompt_root = _digest(
            {
                "reflection_type": reflection_type,
                "source_type": source_type,
                "source_id": source_id,
                "evidence_ids": evidence,
                "observations": dict(observations),
            }
        )
        target, snapshot = self.semantic.mission_snapshot(
            mission_id=mission_id,
            revision=f"learning-reflection:{prompt_root}",
            state={
                "reflection_type": reflection_type,
                "source_type": source_type,
                "source_id": source_id,
            },
        )
        reflection = Observation(
            kind=f"software-factory.learning.reflection.{reflection_type}",
            value={
                "source_type": source_type,
                "source_id": source_id,
                "evidence_ids": evidence,
                "observations": dict(observations),
                "conclusions": dict(conclusions),
                "proposed_actions": [dict(item) for item in (proposed_actions or ())],
                "confidence": confidence,
                "prompt_root": prompt_root,
            },
            target_snapshot=snapshot,
            metadata={"factory_projection": "learning/v2"},
        )
        self.semantic.cache_and_bind(
            mission_id=mission_id,
            subject_type="learning_reflection",
            subject_id=reflection.root,
            records=(target, snapshot, reflection),
            roles=(
                ("target", target),
                ("target_snapshot", snapshot),
                ("reflection_observation", reflection),
            ),
            currentness_root=snapshot.root,
        )
        return {
            "id": reflection.root,
            "mission_id": mission_id,
            "reflection_type": reflection_type,
            "source_type": source_type,
            "source_id": source_id,
            "prompt_root": prompt_root,
            "evidence_ids_json": _canonical(evidence),
            "observations_json": _canonical(dict(observations)),
            "conclusions_json": _canonical(dict(conclusions)),
            "proposed_actions_json": _canonical([dict(item) for item in (proposed_actions or ())]),
            "confidence": confidence,
            "status": "advisory",
            "canonical": True,
        }

    def create_hypothesis(
        self,
        *,
        mission_id: str,
        statement: str,
        causal_model: Mapping[str, Any],
        prediction: Mapping[str, Any],
        reflection_id: str | None = None,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if not statement.strip():
            raise ValueError("hypothesis statement is required")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("hypothesis confidence must be between zero and one")
        target, snapshot = self.semantic.mission_snapshot(
            mission_id=mission_id,
            revision=f"learning-hypothesis:{_digest({'statement': statement, 'causal_model': dict(causal_model), 'prediction': dict(prediction)})}",
            state={"reflection_id": reflection_id, "semantic_operation": "hypothesis_proposal"},
        )
        observation = Observation(
            kind="software-factory.learning.hypothesis-proposal",
            value={"mission_id": mission_id, "reflection_id": reflection_id},
            target_snapshot=snapshot,
        )
        hypothesis = HypothesisPolicy().create(
            target=target,
            statement=statement.strip(),
            causal_model=dict(causal_model),
            predictions=(dict(prediction),),
            source_refs=(observation.ref,),
            confidence=confidence,
            lineage=(observation.ref,),
            metadata={"factory_projection": "learning/v2", "reflection_id": reflection_id},
        )
        self.semantic.cache_and_bind(
            mission_id=mission_id,
            subject_type="learning_hypothesis",
            subject_id=hypothesis.root,
            records=(target, snapshot, observation, hypothesis),
            roles=(
                ("target", target),
                ("target_snapshot", snapshot),
                ("observation", observation),
                ("hypothesis", hypothesis),
            ),
            currentness_root=snapshot.root,
        )
        return {
            "id": hypothesis.root,
            "mission_id": mission_id,
            "statement": hypothesis.statement,
            "causal_model_json": _canonical(dict(hypothesis.causal_model)),
            "prediction_json": _canonical(dict(hypothesis.predictions[0])),
            "status": hypothesis.status,
            "confidence": hypothesis.confidence,
            "created_from_reflection_id": reflection_id,
            "canonical": True,
        }

    def add_hypothesis_evidence(
        self,
        hypothesis_id: str,
        *,
        evidence_type: Literal["support", "counterexample", "boundary", "confounder", "null"],
        evidence_id: str,
        weight: float,
        rationale: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not 0.0 <= weight <= 1.0:
            raise ValueError("evidence weight must be between zero and one")
        hypothesis = self.semantic.load_record(hypothesis_id)
        if not isinstance(hypothesis, Hypothesis):
            raise ValueError("hypothesis evidence requires a canonical libRSI hypothesis root")
        binding = self.store.one(
            """SELECT mission_id,currentness_root FROM librsi_record_bindings
               WHERE librsi_root=? AND semantic_role IN ('hypothesis','hypothesis_update')
               ORDER BY created_at DESC LIMIT 1""",
            (hypothesis_id,),
        )
        snapshot = self.semantic.load_record(str(binding["currentness_root"]))
        if not isinstance(snapshot, TargetSnapshot):
            raise StoreError("canonical hypothesis binding lacks its exact target snapshot")
        observation = Observation(
            kind="software-factory.learning.hypothesis-evidence",
            value={"evidence_id": evidence_id, "rationale": dict(rationale or {})},
            target_snapshot=snapshot,
            source_refs=(hypothesis.ref,),
        )
        evidence = Evidence(
            evidence_type=evidence_type,
            data={"evidence_id": evidence_id, "rationale": dict(rationale or {})},
            subject_refs=(hypothesis.ref,),
            source_refs=(observation.ref,),
            target_snapshot=snapshot,
            weight=weight,
            lineage=(hypothesis.ref, observation.ref),
        )
        updated = HypothesisPolicy().apply(hypothesis=hypothesis, evidence=evidence)
        mission_id = str(binding["mission_id"])
        self.semantic.cache_and_bind(
            mission_id=mission_id,
            subject_type="learning_hypothesis",
            subject_id=updated.root,
            records=(observation, evidence, updated),
            roles=(
                ("evidence_observation", observation),
                ("hypothesis_evidence", evidence),
                ("hypothesis_update", updated),
            ),
            currentness_root=snapshot.root,
        )
        return {
            "id": evidence.root,
            "hypothesis_id": hypothesis_id,
            "hypothesis_root": updated.root,
            "evidence_type": evidence.evidence_type,
            "evidence_id": evidence_id,
            "weight": evidence.weight,
            "status": updated.status,
            "confidence": updated.confidence,
            "canonical": True,
        }

    def design_experiment(
        self,
        *,
        mission_id: str,
        experiment_type: Literal[
            "command", "historical_replay", "shadow", "canary", "simulation", "comparison"
        ],
        design: Mapping[str, Any],
        success_criteria: Mapping[str, Any],
        safety_constraints: Mapping[str, Any] | None = None,
        hypothesis_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if not design or not success_criteria:
            raise ValueError("experiment design and success criteria are required")
        experiment_id = new_id("experiment")
        target, snapshot = self.semantic.mission_snapshot(
            mission_id=mission_id,
            revision=f"learning-experiment:{_digest({'experiment_id': experiment_id, 'design': dict(design), 'criteria': dict(success_criteria)})}",
            state={"experiment_type": experiment_type, "semantic_operation": "experiment_design"},
        )
        if hypothesis_id is None:
            hypothesis = HypothesisPolicy().create(
                target=target,
                statement=f"The {experiment_type} experiment can satisfy its exact criteria.",
                causal_model={"experiment_type": experiment_type},
                predictions=({"success_criteria": dict(success_criteria)},),
                confidence=0.5,
                metadata={"factory_projection": "learning/v2", "generated_for_experiment": True},
            )
        else:
            loaded = self.semantic.load_record(hypothesis_id)
            if type(loaded) is not Hypothesis:
                raise ValueError("experiment hypothesis must be a canonical libRSI root")
            hypothesis = loaded
            binding = self.store.one(
                """SELECT currentness_root FROM librsi_record_bindings
                   WHERE mission_id=? AND librsi_root=?
                     AND semantic_role IN ('hypothesis','hypothesis_update',
                                           'experiment_hypothesis')
                   ORDER BY created_at DESC LIMIT 1""",
                (mission_id, hypothesis_id),
                required=False,
            )
            if binding is None or hypothesis.target != target:
                raise InvalidTransition(
                    "experiment hypothesis is not bound to this exact Factory mission"
                )
            bound_snapshot = self.semantic.load_record(str(binding["currentness_root"]))
            if type(bound_snapshot) is not TargetSnapshot:
                raise StoreError("experiment hypothesis lacks exact host currentness")
            self.semantic.require_live_currentness(mission_id=mission_id, snapshot=bound_snapshot)
        spec = ExperimentSpec(
            experiment_id=experiment_id,
            kind=experiment_type,
            target_snapshot=snapshot,
            design=dict(design),
            criteria=dict(success_criteria),
            inputs={"hypothesis_root": hypothesis.root},
            environment={"safety_constraints": dict(safety_constraints or {})},
            requested_measurements=("command.passed",) if experiment_type == "command" else (),
            lineage=(hypothesis.ref,),
            metadata={"factory_projection": "learning/v2", "phase": "designed"},
        )
        self.semantic.cache_and_bind(
            mission_id=mission_id,
            subject_type="learning_experiment",
            subject_id=experiment_id,
            records=(target, snapshot, hypothesis, spec),
            roles=(
                ("target", target),
                ("target_snapshot", snapshot),
                ("experiment_hypothesis", hypothesis),
                ("experiment_spec", spec),
            ),
            currentness_root=snapshot.root,
        )
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO experiments_v2(
                       id,mission_id,hypothesis_id,experiment_type,design_json,
                       success_criteria_json,safety_constraints_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,'designed',?,?)""",
                (
                    experiment_id,
                    mission_id,
                    None,
                    experiment_type,
                    _canonical(dict(design)),
                    _canonical(dict(success_criteria)),
                    _canonical(dict(safety_constraints or {})),
                    now,
                    now,
                ),
            )
        row = self.store.one("SELECT * FROM experiments_v2 WHERE id=?", (experiment_id,))
        return {**row, "hypothesis_root": hypothesis.root, "librsi_root": spec.root}

    def run_command_experiment(
        self,
        experiment_id: str,
        *,
        command: Sequence[str],
        cwd: str | Path,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        experiment = self.store.one("SELECT * FROM experiments_v2 WHERE id=?", (experiment_id,))
        if experiment["experiment_type"] != "command":
            raise InvalidTransition("experiment is not a command experiment")
        if experiment["status"] != "designed":
            raise InvalidTransition("experiment is not awaiting execution")
        if not command or any(not str(part) for part in command):
            raise ValueError("command experiment requires a nonempty argv")
        resolved_cwd = str(Path(cwd).resolve())
        design = _loads(experiment["design_json"], {})
        criteria = _loads(experiment["success_criteria_json"], {})
        binding_rows = self.store.all(
            """SELECT semantic_role,librsi_root,currentness_root
               FROM librsi_record_bindings
               WHERE mission_id=? AND operational_subject_type='learning_experiment'
                 AND operational_subject_id=?""",
            (experiment["mission_id"], experiment_id),
        )
        roots_by_role = {str(row["semantic_role"]): str(row["librsi_root"]) for row in binding_rows}
        hypothesis = self.semantic.load_record(roots_by_role["experiment_hypothesis"])
        snapshot = self.semantic.load_record(str(binding_rows[0]["currentness_root"]))
        if not isinstance(hypothesis, Hypothesis) or not isinstance(snapshot, TargetSnapshot):
            raise StoreError("command experiment lacks canonical hypothesis/currentness")
        semantic_spec = ExperimentPolicy().design_command(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            target_snapshot=snapshot,
            design=design,
            success_criteria=criteria,
            command=command,
            cwd=resolved_cwd,
            environment={"safety_constraints": _loads(experiment["safety_constraints_json"], {})},
        )
        prepared = ExperimentPolicy.prepare_command(semantic_spec)
        self.semantic.cache_and_bind(
            mission_id=str(experiment["mission_id"]),
            subject_type="learning_experiment",
            subject_id=experiment_id,
            records=(semantic_spec,),
            roles=(("execution_experiment_spec", semantic_spec),),
            currentness_root=snapshot.root,
        )
        exact_input_root = semantic_spec.root
        run_id = new_id("experiment-run")
        started = utc_now()
        with self.store.transaction() as db:
            db.execute(
                "UPDATE experiments_v2 SET status='running',updated_at=? WHERE id=?",
                (started, experiment_id),
            )
            db.execute(
                """INSERT INTO experiment_runs_v2(
                       id,experiment_id,exact_input_root,command_json,cwd,
                       disposition,started_at
                   ) VALUES(?,?,?,?,?,'running',?)""",
                (
                    run_id,
                    experiment_id,
                    exact_input_root,
                    _canonical(list(command)),
                    resolved_cwd,
                    started,
                ),
            )
        try:
            completed = subprocess.run(
                list(prepared.command),
                cwd=prepared.cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            invalid = False
        except (OSError, subprocess.TimeoutExpired) as exc:
            exit_code = None
            stdout = ""
            stderr = str(exc)
            invalid = True

        semantic_evidence = ExperimentPolicy().evaluate_command(
            spec=semantic_spec,
            observation=CommandObservation(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                invalid=invalid,
                exact_input_root=exact_input_root,
            ),
        )
        disposition = str(semantic_evidence.data["disposition"])
        passed = bool(semantic_evidence.data["passed"])
        evidence_root = semantic_evidence.root
        updated_hypothesis = HypothesisPolicy().apply(
            hypothesis=hypothesis, evidence=semantic_evidence
        )
        self.semantic.cache_and_bind(
            mission_id=str(experiment["mission_id"]),
            subject_type="learning_experiment",
            subject_id=experiment_id,
            records=(semantic_evidence, updated_hypothesis),
            roles=(
                ("experiment_evidence", semantic_evidence),
                ("hypothesis_update", updated_hypothesis),
            ),
            currentness_root=snapshot.root,
        )
        completed_at = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE experiment_runs_v2
                   SET exit_code=?,stdout_text=?,stderr_text=?,measurement_json=?,
                       evidence_root=?,disposition=?,completed_at=? WHERE id=?""",
                (
                    exit_code,
                    stdout,
                    stderr,
                    _canonical({"passed": passed, "criteria": criteria}),
                    evidence_root,
                    disposition,
                    completed_at,
                    run_id,
                ),
            )
            db.execute(
                "UPDATE experiments_v2 SET status=?,updated_at=? WHERE id=?",
                ("succeeded" if passed else disposition, completed_at, experiment_id),
            )
        return self.store.one("SELECT * FROM experiment_runs_v2 WHERE id=?", (run_id,))

    def browse_signals(self, mission_id: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "candidates": self.store.all(
                """SELECT * FROM learned_signal_candidates
                   WHERE mission_id=? ORDER BY created_at DESC""",
                (mission_id,),
            ),
            "bundles": self.store.all(
                """SELECT * FROM active_signal_bundles
                   WHERE mission_id=? ORDER BY activated_at DESC""",
                (mission_id,),
            ),
            "occurrences": self.store.all(
                """SELECT * FROM signal_occurrences
                   WHERE mission_id=? ORDER BY created_at DESC""",
                (mission_id,),
            ),
        }
