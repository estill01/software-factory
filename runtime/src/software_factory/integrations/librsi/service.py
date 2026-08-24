from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from librsi import (
    Evidence,
    ExperimentSpec,
    Hypothesis,
    HypothesisPolicy,
    Observation,
    SemanticRecord,
    TargetSnapshot,
    deserialize_record,
)
from librsi.conformance import ComponentState, map_composite_snapshot

from ...errors import InvalidTransition, StoreError
from ...util import canonical_json, digest_json, json_load, utc_now
from .pin import LIBRSI_PIN, verify_installed_librsi


@dataclass(frozen=True, slots=True)
class SemanticReflection:
    currentness_root: str
    observation_root: str
    hypothesis_roots: tuple[str, ...]
    evidence_roots: tuple[str, ...]
    experiment_root: str
    experiment_work_item_id: str
    cutover_receipt_root: str
    recommended_next_action: str


@dataclass(frozen=True, slots=True)
class _HypothesisInput:
    role: str
    statement: str
    causal_model: Mapping[str, Any]
    prediction: Mapping[str, Any]


class LibRSIIntegration:
    """Host libRSI semantics without transferring Factory operational authority."""

    def __init__(self, store: Any, *, work_items: Any, verify_pin: bool = True) -> None:
        self.store = store
        self.work_items = work_items
        if verify_pin:
            verify_installed_librsi()

    @staticmethod
    def _inputs(execution: Mapping[str, Any]) -> tuple[str, tuple[_HypothesisInput, ...]]:
        strategy = str(execution.get("strategy_key") or "unknown")
        if execution["status"] != "succeeded":
            fingerprint = str(
                execution.get("failure_fingerprint")
                or digest_json(json_load(cast(str, execution["error_json"]), {}))
            )
            return (
                "run_discriminating_experiment",
                (
                    _HypothesisInput(
                        role="strategy_cause",
                        statement=(
                            f"Strategy {strategy} is causally associated with failure "
                            f"fingerprint {fingerprint} in this exact target state."
                        ),
                        causal_model={
                            "candidate_cause": "implementation_strategy",
                            "strategy_key": strategy,
                            "failure_fingerprint": fingerprint,
                        },
                        prediction={
                            "discriminator": (
                                "a materially different strategy avoids the fingerprint "
                                "under matched currentness"
                            )
                        },
                    ),
                    _HypothesisInput(
                        role="context_cause",
                        statement=(
                            f"Failure fingerprint {fingerprint} is caused by invocation, "
                            "environment, or currentness rather than the implementation strategy."
                        ),
                        causal_model={
                            "candidate_cause": "operational_context",
                            "strategy_key": strategy,
                            "failure_fingerprint": fingerprint,
                        },
                        prediction={
                            "discriminator": (
                                "the same strategy succeeds after one bounded context correction"
                            )
                        },
                    ),
                ),
            )
        return (
            "bounded_replay_and_counterexample_search",
            (
                _HypothesisInput(
                    role="reusable_effect",
                    statement=(
                        f"Strategy {strategy} produced a reusable capability effect in this exact "
                        "target state."
                    ),
                    causal_model={
                        "candidate_cause": "implementation_strategy",
                        "strategy_key": strategy,
                    },
                    prediction={"discriminator": "the benefit recurs in a bounded matched replay"},
                ),
                _HypothesisInput(
                    role="contextual_effect",
                    statement=(
                        "The observed improvement is contextual noise or an unrelated concurrent "
                        "change rather than a reusable strategy effect."
                    ),
                    causal_model={
                        "candidate_cause": "context_or_concurrent_change",
                        "strategy_key": strategy,
                    },
                    prediction={"discriminator": "the benefit disappears under matched replay"},
                ),
            ),
        )

    def _map_execution(self, execution: Mapping[str, Any]) -> Any:
        mission = self.store.one("SELECT * FROM missions WHERE id=?", (execution["mission_id"],))
        components = [
            ComponentState(
                component_id="mission",
                kind="software-factory-mission",
                revision=str(mission["state_version"]),
                state={
                    "status": mission["status"],
                    "objective": mission["objective"],
                    "state_version": mission["state_version"],
                },
                locator={"operational_id": mission["id"]},
            ),
            ComponentState(
                component_id="execution",
                kind="software-factory-execution",
                revision=str(execution["state_version"]),
                state={
                    "status": execution["status"],
                    "strategy_key": execution.get("strategy_key"),
                    "result": json_load(cast(str, execution["result_json"]), {}),
                    "error": json_load(cast(str, execution["error_json"]), {}),
                    "observed_effect": json_load(cast(str, execution["observed_effect_json"]), {}),
                },
                locator={"operational_id": execution["id"]},
            ),
        ]
        if execution.get("work_item_id"):
            work = self.store.one(
                "SELECT * FROM work_items WHERE id=?", (execution["work_item_id"],)
            )
            components.append(
                ComponentState(
                    component_id="work",
                    kind="software-factory-work-item",
                    revision=str(work["state_version"]),
                    state={
                        "planning_status": work["planning_status"],
                        "execution_status": work["execution_status"],
                        "acceptance_status": work["acceptance_status"],
                        "strategy_key": work["strategy_key"],
                    },
                    locator={"operational_id": work["id"]},
                )
            )
        return map_composite_snapshot(
            target_id=f"software-factory-mission:{mission['id']}",
            kind="software-factory-operational-context",
            components=components,
        )

    @staticmethod
    def _serialized(record: SemanticRecord) -> str:
        return canonical_json(record.to_dict())

    def _persist_records(self, records: Sequence[SemanticRecord]) -> None:
        now = utc_now()
        with self.store.transaction() as db:
            for record in records:
                serialized = self._serialized(record)
                db.execute(
                    """INSERT OR IGNORE INTO librsi_records(
                        root,record_type,schema_version,canonical_json,created_at
                    ) VALUES(?,?,?,?,?)""",
                    (
                        record.root,
                        record.record_type,
                        record.schema_version,
                        serialized,
                        now,
                    ),
                )
                persisted = db.execute(
                    "SELECT record_type,schema_version,canonical_json FROM librsi_records WHERE root=?",
                    (record.root,),
                ).fetchone()
                if (
                    persisted is None
                    or persisted["record_type"] != record.record_type
                    or persisted["schema_version"] != record.schema_version
                    or persisted["canonical_json"] != serialized
                ):
                    raise StoreError("immutable libRSI record root has conflicting content")

    def _bind(
        self,
        *,
        mission_id: str,
        subject_type: str,
        subject_id: str,
        role: str,
        record: SemanticRecord,
        currentness_root: str,
    ) -> None:
        with self.store.transaction() as db:
            db.execute(
                """INSERT OR IGNORE INTO librsi_record_bindings(
                    mission_id,operational_subject_type,operational_subject_id,
                    semantic_role,librsi_root,currentness_root,created_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    mission_id,
                    subject_type,
                    subject_id,
                    role,
                    record.root,
                    currentness_root,
                    utc_now(),
                ),
            )
            stale = db.execute(
                """SELECT currentness_root FROM librsi_record_bindings
                   WHERE mission_id=? AND operational_subject_type=?
                   AND operational_subject_id=? AND semantic_role=? AND librsi_root=?""",
                (mission_id, subject_type, subject_id, role, record.root),
            ).fetchone()
            if stale is None or stale["currentness_root"] != currentness_root:
                raise InvalidTransition("libRSI operational binding is stale or conflicting")

    def _ensure_experiment_work(
        self,
        *,
        execution: Mapping[str, Any],
        experiment: ExperimentSpec,
        hypothesis_roots: Sequence[str],
        recommended: str,
    ) -> str:
        lane_key = f"librsi-experiment:{execution['id']}"
        existing = self.store.one(
            "SELECT id FROM work_items WHERE mission_id=? AND lane_key=?",
            (execution["mission_id"], lane_key),
            required=False,
        )
        if existing is not None:
            return str(existing["id"])
        return self.work_items.create_work_item(
            mission_id=str(execution["mission_id"]),
            obligation_id=cast(str | None, execution.get("obligation_id")),
            parent_id=cast(str | None, execution.get("work_item_id")),
            work_type="semantic_experiment",
            title="Run libRSI discriminating experiment",
            description=(
                "Execute the Factory-hosted experiment bound to canonical libRSI records; "
                "the semantic recommendation itself grants no execution authority."
            ),
            priority=90,
            proposed_by="software-factory.librsi/v1",
            expected_effect={
                "recommended_next_action": recommended,
                "experiment_root": experiment.root,
                "hypothesis_roots": list(hypothesis_roots),
            },
            acceptance_spec={
                "candidate": [
                    {"type": "exact_experiment_observation", "required": True},
                    {"type": "librsi_evidence_update", "required": True},
                ]
            },
            lane_key=lane_key,
            strategy_key=f"librsi:{recommended}",
        )

    def reflect_execution(self, execution_id: str) -> SemanticReflection:
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        unexpected = bool(
            json_load(cast(str, execution["observed_effect_json"]), {}).get("unexpected_success")
            or json_load(cast(str, execution["result_json"]), {}).get("unexpected_success")
        )
        if execution["status"] == "succeeded" and not unexpected:
            raise InvalidTransition("ordinary success has no authoritative libRSI reflection slice")
        if execution["status"] not in {"succeeded", "failed", "abandoned", "cancelled"}:
            raise InvalidTransition("libRSI reflection requires a terminal execution")

        mapped = self._map_execution(execution)
        recommended, inputs = self._inputs(execution)
        observation = Observation(
            kind=(
                "software-factory.execution.unexpected-success"
                if unexpected
                else "software-factory.execution.failure"
            ),
            value={
                "execution_id": execution_id,
                "status": execution["status"],
                "strategy_key": execution.get("strategy_key"),
                "failure_fingerprint": execution.get("failure_fingerprint"),
                "observed_effect": json_load(cast(str, execution["observed_effect_json"]), {}),
            },
            target_snapshot=mapped.snapshot,
        )
        policy = HypothesisPolicy()
        initial_hypotheses = tuple(
            policy.create(
                target=mapped.target,
                statement=item.statement,
                causal_model=item.causal_model,
                predictions=(item.prediction,),
                source_refs=(observation.ref,),
                confidence=0.5,
                lineage=(observation.ref,),
                metadata={"factory_semantic_role": item.role},
            )
            for item in inputs
        )
        evidence = tuple(
            Evidence(
                evidence_type="boundary",
                data={
                    "disposition": "observed-but-not-yet-discriminated",
                    "execution_id": execution_id,
                    "hypothesis_role": inputs[index].role,
                },
                subject_refs=(hypothesis.ref,),
                source_refs=(observation.ref,),
                target_snapshot=mapped.snapshot,
                weight=0.25,
                lineage=(observation.ref, hypothesis.ref),
            )
            for index, hypothesis in enumerate(initial_hypotheses)
        )
        hypotheses = tuple(
            policy.apply(hypothesis=hypothesis, evidence=evidence[index])
            for index, hypothesis in enumerate(initial_hypotheses)
        )
        experiment = ExperimentSpec(
            experiment_id=f"factory-discriminator:{execution_id}",
            kind=(
                "bounded-matched-replay" if unexpected else "bounded-strategy-context-discriminator"
            ),
            target_snapshot=mapped.snapshot,
            design={
                "alternatives": [item.role for item in inputs],
                "authority": "software-factory-hosted",
                "selection_is_not_authorization": True,
            },
            criteria={
                "require_exact_currentness": True,
                "failed_run_disposition": "inconclusive-not-falsified",
                "compare_all_hypotheses": True,
            },
            inputs={
                "source_execution_id": execution_id,
                "hypothesis_roots": [item.root for item in hypotheses],
            },
            environment={"currentness_root": mapped.snapshot.root},
            requested_measurements=("failure_fingerprint", "capability_effect"),
            repetitions=1,
            lineage=(observation.ref, *(item.ref for item in hypotheses)),
        )
        records: tuple[SemanticRecord, ...] = (
            mapped.target,
            mapped.snapshot,
            observation,
            *initial_hypotheses,
            *evidence,
            *hypotheses,
            experiment,
        )
        self._persist_records(records)
        currentness_root = mapped.snapshot.root
        mission_id = str(execution["mission_id"])
        for role, record in (
            ("target", mapped.target),
            ("target_snapshot", mapped.snapshot),
            ("observation", observation),
            *(("hypothesis_initial", item) for item in initial_hypotheses),
            *(("hypothesis_evidence", item) for item in evidence),
            *(("hypothesis", item) for item in hypotheses),
            ("experiment_spec", experiment),
        ):
            self._bind(
                mission_id=mission_id,
                subject_type="execution",
                subject_id=execution_id,
                role=role,
                record=record,
                currentness_root=currentness_root,
            )

        work_id = self._ensure_experiment_work(
            execution=execution,
            experiment=experiment,
            hypothesis_roots=[item.root for item in hypotheses],
            recommended=recommended,
        )
        self._bind(
            mission_id=mission_id,
            subject_type="work_item",
            subject_id=work_id,
            role="experiment_spec",
            record=experiment,
            currentness_root=currentness_root,
        )

        shadow_projection_root = digest_json(
            {
                "hypothesis_roles": [item.role for item in inputs],
                "hypothesis_count": 2,
                "recommended_next_action": recommended,
            }
        )
        semantic_result_root = digest_json(
            {
                "observation_root": observation.root,
                "hypothesis_roots": [item.root for item in hypotheses],
                "evidence_roots": [item.root for item in evidence],
                "experiment_root": experiment.root,
                "recommended_next_action": recommended,
            }
        )
        parity = len(hypotheses) == 2 and all(item.predictions for item in hypotheses)
        receipt_root = digest_json(
            {
                "adapter_contract": LIBRSI_PIN.adapter_contract,
                "source_execution_id": execution_id,
                "source_commit": LIBRSI_PIN.source_commit,
                "package_content_root": LIBRSI_PIN.package_content_root,
                "currentness_root": currentness_root,
                "shadow_projection_root": shadow_projection_root,
                "semantic_result_root": semantic_result_root,
                "parity": parity,
            }
        )
        with self.store.transaction() as db:
            inserted = db.execute(
                """INSERT OR IGNORE INTO librsi_cutover_receipts_v2(
                    receipt_root,mission_id,source_execution_id,adapter_contract,
                    producer_acceptance_revision,source_commit,package_content_root,
                    currentness_root,shadow_projection_root,semantic_result_root,
                    parity_disposition,authority_posture,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'authoritative',?)""",
                (
                    receipt_root,
                    mission_id,
                    execution_id,
                    LIBRSI_PIN.adapter_contract,
                    LIBRSI_PIN.producer_acceptance_revision,
                    LIBRSI_PIN.source_commit,
                    LIBRSI_PIN.package_content_root,
                    currentness_root,
                    shadow_projection_root,
                    semantic_result_root,
                    "matched" if parity else "mismatched",
                    utc_now(),
                ),
            )
            receipt = db.execute(
                "SELECT * FROM librsi_cutover_receipts_v2 WHERE source_execution_id=?",
                (execution_id,),
            ).fetchone()
            if receipt is None or receipt["receipt_root"] != receipt_root:
                raise InvalidTransition("libRSI cutover receipt conflicts with exact currentness")
            if not parity:
                raise InvalidTransition("libRSI shadow comparison did not reach parity")
            if inserted.rowcount == 1:
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="librsi",
                    event_type="librsi.semantic_slice_cut_over",
                    subject_type="execution",
                    subject_id=execution_id,
                    payload={
                        "receipt_root": receipt_root,
                        "experiment_work_item_id": work_id,
                        "semantic_result_root": semantic_result_root,
                    },
                )

        return SemanticReflection(
            currentness_root=currentness_root,
            observation_root=observation.root,
            hypothesis_roots=tuple(item.root for item in hypotheses),
            evidence_roots=tuple(item.root for item in evidence),
            experiment_root=experiment.root,
            experiment_work_item_id=work_id,
            cutover_receipt_root=receipt_root,
            recommended_next_action=recommended,
        )

    def record_experiment_outcome(
        self,
        *,
        experiment_execution_id: str,
        hypothesis_root: str,
        disposition: str,
        data: Mapping[str, Any],
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Apply observed experiment evidence without granting an operational transition."""

        execution = self.store.one(
            "SELECT * FROM executions WHERE id=?", (experiment_execution_id,)
        )
        if execution["status"] not in {"succeeded", "failed", "abandoned", "cancelled"}:
            raise InvalidTransition("experiment evidence requires a terminal execution")
        record = self.store.one(
            "SELECT canonical_json FROM librsi_records WHERE root=?", (hypothesis_root,)
        )
        hypothesis = deserialize_record(str(record["canonical_json"]))
        if not isinstance(hypothesis, Hypothesis):
            raise ValueError("experiment evidence must target a canonical libRSI hypothesis")
        snapshot_record = self.store.one(
            """SELECT records.canonical_json
               FROM librsi_record_bindings AS bindings
               JOIN librsi_records AS records ON records.root=bindings.currentness_root
               WHERE bindings.librsi_root=?
               ORDER BY bindings.created_at LIMIT 1""",
            (hypothesis_root,),
        )
        target_snapshot = deserialize_record(str(snapshot_record["canonical_json"]))
        if not isinstance(target_snapshot, TargetSnapshot):
            raise StoreError("libRSI hypothesis binding does not resolve an exact target snapshot")
        relationships = {
            "supported": "support",
            "counterexample": "counterexample",
            "boundary": "boundary",
            "confounder": "confounder",
            "inconclusive": "null",
            "execution_failed": "null",
        }
        relationship = relationships.get(disposition)
        if relationship is None:
            raise ValueError("unsupported experiment evidence disposition")
        if execution["status"] != "succeeded":
            relationship = "null"
        evidence_weight = 0.0 if relationship == "null" else weight
        execution_observation_root = digest_json(
            {
                "execution_id": experiment_execution_id,
                "state_version": execution["state_version"],
                "status": execution["status"],
                "observed_effect": json_load(cast(str, execution["observed_effect_json"]), {}),
            }
        )
        observation = Observation(
            kind="software-factory.semantic-experiment.outcome",
            value={
                **dict(data),
                "operational_disposition": disposition,
                "execution_id": experiment_execution_id,
                "execution_status": execution["status"],
                "execution_observation_root": execution_observation_root,
            },
            source_refs=(hypothesis.ref,),
        )
        evidence = Evidence(
            evidence_type=relationship,
            data={
                **dict(data),
                "operational_disposition": disposition,
                "execution_status": execution["status"],
            },
            subject_refs=(hypothesis.ref,),
            source_refs=(observation.ref,),
            target_snapshot=target_snapshot,
            weight=evidence_weight,
            lineage=(hypothesis.ref, observation.ref),
        )
        updated = HypothesisPolicy().apply(hypothesis=hypothesis, evidence=evidence)
        self._persist_records((observation, evidence, updated))
        mission_id = str(execution["mission_id"])
        currentness_root = target_snapshot.root
        self._bind(
            mission_id=mission_id,
            subject_type="execution",
            subject_id=experiment_execution_id,
            role="experiment_observation",
            record=observation,
            currentness_root=currentness_root,
        )
        self._bind(
            mission_id=mission_id,
            subject_type="execution",
            subject_id=experiment_execution_id,
            role="experiment_evidence",
            record=evidence,
            currentness_root=currentness_root,
        )
        self._bind(
            mission_id=mission_id,
            subject_type="execution",
            subject_id=experiment_execution_id,
            role="hypothesis_update",
            record=updated,
            currentness_root=currentness_root,
        )
        followup_work_item_id: str | None = None
        if updated.status == "supported":
            lane_key = f"librsi-followup:{updated.root}"
            existing = self.store.one(
                "SELECT id FROM work_items WHERE mission_id=? AND lane_key=?",
                (mission_id, lane_key),
                required=False,
            )
            if existing is not None:
                followup_work_item_id = str(existing["id"])
            else:
                followup_work_item_id = self.work_items.create_work_item(
                    mission_id=mission_id,
                    obligation_id=cast(str | None, execution.get("obligation_id")),
                    parent_id=cast(str | None, execution.get("work_item_id")),
                    work_type="semantic_followup",
                    title="Evaluate bounded use of supported libRSI hypothesis",
                    description=(
                        "Operationally evaluate the evidence-supported semantic candidate; "
                        "the libRSI status remains non-authoritative for execution and acceptance."
                    ),
                    priority=70,
                    proposed_by=LIBRSI_PIN.adapter_contract,
                    expected_effect={
                        "hypothesis_root": updated.root,
                        "bounded_generalization_only": True,
                    },
                    acceptance_spec={
                        "candidate": [
                            {"type": "bounded_applicability_evidence", "required": True},
                            {"type": "independent_review", "required": True},
                        ]
                    },
                    lane_key=lane_key,
                    strategy_key="librsi:supported-hypothesis-followup",
                )
            self._bind(
                mission_id=mission_id,
                subject_type="work_item",
                subject_id=followup_work_item_id,
                role="supported_hypothesis",
                record=updated,
                currentness_root=currentness_root,
            )
        return {
            "evidence_root": evidence.root,
            "hypothesis_root": updated.root,
            "status": updated.status,
            "confidence": updated.confidence,
            "followup_work_item_id": followup_work_item_id,
            "operational_transition_authorized": False,
        }
