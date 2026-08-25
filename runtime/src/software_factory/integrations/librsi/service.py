from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from librsi import (
    CandidateSnapshot,
    CandidateTrialBatch,
    ComparativeSelectionPolicy,
    EvaluationContract,
    Evidence,
    ExperimentSpec,
    Hypothesis,
    HypothesisPolicy,
    ImprovementResult,
    Observation,
    RiskPolicy,
    RSIResult,
    SelectionDecision,
    SelfChangePolicy,
    SemanticRecord,
    TargetRef,
    TargetSnapshot,
    deserialize_record,
)
from librsi.conformance import ComponentState, map_composite_snapshot

from ...errors import InvalidTransition, StoreError
from ...util import canonical_json, digest_json, json_load, utc_now
from .legacy_shadow import LegacyShadowProjection, project_legacy_reflection
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

    def __init__(
        self, store: Any, *, work_items: Any | None = None, verify_pin: bool = True
    ) -> None:
        self.store = store
        self.work_items = work_items
        if verify_pin:
            verify_installed_librsi()

    def mission_snapshot(
        self,
        *,
        mission_id: str,
        state: Mapping[str, Any],
        revision: str,
    ) -> tuple[TargetRef, TargetSnapshot]:
        """Create a canonical currentness pair for a Factory operational projection."""

        mission = self.store.one("SELECT state_version FROM missions WHERE id=?", (mission_id,))
        target = TargetRef(
            target_id=f"software-factory-mission:{mission_id}",
            kind="software-factory-operational-context",
            locator={"mission_id": mission_id},
        )
        snapshot = TargetSnapshot(
            target=target,
            revision=revision,
            state={**dict(state), "mission_state_version": mission["state_version"]},
        )
        return target, snapshot

    def require_live_currentness(self, *, mission_id: str, snapshot: TargetSnapshot) -> None:
        """Reject semantic input that no longer names the live host projection."""

        if type(snapshot) is not TargetSnapshot:
            raise TypeError("libRSI currentness must be an exact TargetSnapshot")
        expected_target_id = f"software-factory-mission:{mission_id}"
        if snapshot.target.target_id != expected_target_id:
            raise InvalidTransition("libRSI currentness crosses the Factory mission boundary")
        mission = self.store.one("SELECT state_version FROM missions WHERE id=?", (mission_id,))
        expected_mission_version = str(mission["state_version"])
        observed_mission_version = snapshot.state.get("mission_state_version")
        mission_component_seen = False
        for component in snapshot.components:
            operational_id = str(component.target.locator.get("operational_id") or "")
            if component.target.kind == "software-factory-mission":
                mission_component_seen = True
                if (
                    operational_id != mission_id
                    or str(component.revision) != expected_mission_version
                ):
                    raise InvalidTransition("libRSI mission currentness is stale")
                observed_mission_version = component.state.get("state_version", component.revision)
            elif component.target.kind == "software-factory-work-item":
                work = self.store.one(
                    "SELECT mission_id,state_version FROM work_items WHERE id=?",
                    (operational_id,),
                )
                if work["mission_id"] != mission_id or str(component.revision) != str(
                    work["state_version"]
                ):
                    raise InvalidTransition("libRSI work currentness is stale")
            elif component.target.kind == "software-factory-execution":
                execution = self.store.one(
                    "SELECT mission_id,state_version FROM executions WHERE id=?",
                    (operational_id,),
                )
                if execution["mission_id"] != mission_id or str(component.revision) != str(
                    execution["state_version"]
                ):
                    raise InvalidTransition("libRSI execution currentness is stale")
        if observed_mission_version is None and not mission_component_seen:
            raise InvalidTransition("libRSI currentness omits the host mission version")
        if str(observed_mission_version) != expected_mission_version:
            raise InvalidTransition("libRSI mission currentness is stale")

    def cache_and_bind(
        self,
        *,
        mission_id: str,
        subject_type: str,
        subject_id: str,
        records: Sequence[SemanticRecord],
        roles: Sequence[tuple[str, SemanticRecord]],
        currentness_root: str,
    ) -> None:
        """Admit canonical records and bind their exact roots to one host subject."""

        incoming = {record.root: record for record in records}
        currentness = incoming.get(currentness_root)
        if currentness is None:
            row = self.store.one(
                "SELECT canonical_json FROM librsi_records WHERE root=?",
                (currentness_root,),
                required=False,
            )
            if row is None:
                raise StoreError("libRSI binding currentness must name a cached canonical record")
            currentness = deserialize_record(str(row["canonical_json"]))
        if type(currentness) is not TargetSnapshot:
            raise StoreError("libRSI binding currentness is not an exact TargetSnapshot")
        self.require_live_currentness(mission_id=mission_id, snapshot=currentness)
        self._persist_records(records)
        for role, record in roles:
            self._bind(
                mission_id=mission_id,
                subject_type=subject_type,
                subject_id=subject_id,
                role=role,
                record=record,
                currentness_root=currentness_root,
            )

    def load_record(self, root: str) -> SemanticRecord:
        row = self.store.one("SELECT canonical_json FROM librsi_records WHERE root=?", (root,))
        return deserialize_record(str(row["canonical_json"]))

    def record_comparison(
        self,
        *,
        mission_id: str,
        subject_type: str,
        subject_id: str,
        selection_id: str,
        contract: EvaluationContract,
        batches: Sequence[CandidateTrialBatch],
        risk_policy: RiskPolicy,
        currentness: TargetSnapshot,
    ) -> SelectionDecision:
        """Run the accepted evidence-bound comparison policy without selecting host work."""

        if type(currentness) is not TargetSnapshot:
            raise TypeError("comparison currentness must be an exact TargetSnapshot")
        self.require_live_currentness(mission_id=mission_id, snapshot=currentness)
        decision = ComparativeSelectionPolicy.select(
            selection_id=selection_id,
            contract=contract,
            batches=batches,
            risk_policy=risk_policy,
        )
        if contract.baseline.snapshot != currentness:
            raise InvalidTransition("comparison contract is stale against host currentness")
        self.cache_and_bind(
            mission_id=mission_id,
            subject_type=subject_type,
            subject_id=subject_id,
            records=(currentness, *batches, risk_policy, decision),
            roles=(
                *(("candidate_trial_batch", batch) for batch in batches),
                ("comparison_risk_policy", risk_policy),
                ("selection_decision", decision),
            ),
            currentness_root=currentness.root,
        )
        return decision

    def record_workflow_result(
        self,
        *,
        mission_id: str,
        subject_type: str,
        subject_id: str,
        result: ImprovementResult | RSIResult,
        currentness: TargetSnapshot,
    ) -> None:
        """Bind a complete accepted improvement or governed-self-change result."""

        if type(currentness) is not TargetSnapshot:
            raise TypeError("workflow currentness must be an exact TargetSnapshot")
        self.require_live_currentness(mission_id=mission_id, snapshot=currentness)
        if type(result) not in {ImprovementResult, RSIResult}:
            raise TypeError("workflow result must be an exact libRSI result record")
        if type(result) is RSIResult:
            SelfChangePolicy.validate_request(result.request)
        if type(result) is ImprovementResult and result.request.baseline != currentness:
            raise InvalidTransition("improvement result is stale against host currentness")
        role = "improvement_result" if type(result) is ImprovementResult else "rsi_result"
        candidates: tuple[CandidateSnapshot, ...] = ()
        if type(result) is ImprovementResult:
            by_root = {
                batch.candidate.root: batch.candidate
                for iteration in result.iterations
                for batch in iteration.proposal.batches
            }
            candidates = tuple(by_root[root] for root in sorted(by_root))
        self.cache_and_bind(
            mission_id=mission_id,
            subject_type=subject_type,
            subject_id=subject_id,
            records=(currentness, result, *candidates),
            roles=(
                (role, result),
                *(("improvement_candidate", candidate) for candidate in candidates),
            ),
            currentness_root=currentness.root,
        )

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
                        role="causal",
                        statement=(
                            f"Strategy {strategy} is causally associated with failure "
                            f"fingerprint {fingerprint} in the current work context."
                        ),
                        causal_model={
                            "candidate_cause": "implementation_strategy",
                            "strategy_key": strategy,
                            "failure_fingerprint": fingerprint,
                        },
                        prediction={
                            "discriminator": "materially different strategy avoids the fingerprint"
                        },
                    ),
                    _HypothesisInput(
                        role="problem_framing",
                        statement=(
                            f"The failure fingerprint {fingerprint} may be caused by environment, "
                            "currentness, or acceptance setup rather than the implementation strategy."
                        ),
                        causal_model={
                            "candidate_cause": "operational_context",
                            "strategy_key": strategy,
                            "failure_fingerprint": fingerprint,
                        },
                        prediction={
                            "discriminator": (
                                "same strategy succeeds under corrected invocation/currentness"
                            )
                        },
                    ),
                ),
            )
        return (
            "bounded_replay_and_counterexample_search",
            (
                _HypothesisInput(
                    role="strategy",
                    statement=(
                        f"Strategy {strategy} produced an unusually strong capability effect in "
                        "the observed context."
                    ),
                    causal_model={
                        "candidate_cause": "implementation_strategy",
                        "strategy_key": strategy,
                    },
                    prediction={"discriminator": "benefit recurs in a bounded similar context"},
                ),
                _HypothesisInput(
                    role="predictive",
                    statement=(
                        "The observed improvement may be contextual noise or an unrelated concurrent "
                        "change rather than a reusable strategy effect."
                    ),
                    causal_model={
                        "candidate_cause": "context_or_concurrent_change",
                        "strategy_key": strategy,
                    },
                    prediction={"discriminator": "benefit disappears under matched replay"},
                ),
            ),
        )

    @staticmethod
    def _semantic_projection(
        hypotheses: Sequence[Hypothesis],
        experiment: ExperimentSpec,
        recommended: str,
    ) -> LegacyShadowProjection:
        if len(hypotheses) != 2 or any(len(item.predictions) != 1 for item in hypotheses):
            raise InvalidTransition("libRSI result does not preserve the two-way legacy comparison")
        roles = tuple(str(item.metadata.get("factory_semantic_role") or "") for item in hypotheses)
        if len(roles) != 2 or any(not role for role in roles):
            raise InvalidTransition("libRSI result omitted an expected semantic role")
        return LegacyShadowProjection(
            hypothesis_roles=cast(tuple[str, str], roles),
            statements=cast(tuple[str, str], tuple(item.statement for item in hypotheses)),
            predictions=cast(
                tuple[Mapping[str, Any], Mapping[str, Any]],
                tuple(item.predictions[0] for item in hypotheses),
            ),
            recommended_next_action=recommended,
            experiment_kind=experiment.kind,
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
        if self.work_items is None:
            raise StoreError("libRSI reflection work requires the Factory work owner")
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
        legacy_projection = project_legacy_reflection(execution)
        canonical_projection = self._semantic_projection(hypotheses, experiment, recommended)
        if canonical_projection != legacy_projection:
            raise InvalidTransition("libRSI shadow comparison did not reach parity")
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

        shadow_projection_root = digest_json(legacy_projection.to_dict())
        semantic_result_root = digest_json(
            {
                "observation_root": observation.root,
                "hypothesis_roots": [item.root for item in hypotheses],
                "evidence_roots": [item.root for item in evidence],
                "experiment_root": experiment.root,
                "recommended_next_action": recommended,
            }
        )
        parity = canonical_projection == legacy_projection
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
        work_item_id = execution.get("work_item_id")
        if not work_item_id:
            raise InvalidTransition("experiment evidence requires assigned experiment work")
        experiment_bindings = self.store.all(
            """SELECT bindings.mission_id,bindings.currentness_root,records.canonical_json
               FROM librsi_record_bindings AS bindings
               JOIN librsi_records AS records ON records.root=bindings.librsi_root
               WHERE bindings.mission_id=?
                 AND bindings.operational_subject_type='work_item'
                 AND bindings.operational_subject_id=?
                 AND bindings.semantic_role='experiment_spec'""",
            (execution["mission_id"], work_item_id),
        )
        if len(experiment_bindings) != 1:
            raise InvalidTransition(
                "experiment evidence requires one exact same-mission experiment binding"
            )
        experiment_binding = experiment_bindings[0]
        experiment = deserialize_record(str(experiment_binding["canonical_json"]))
        if not isinstance(experiment, ExperimentSpec):
            raise StoreError("experiment work binding does not resolve an ExperimentSpec")
        expected_roots = tuple(str(root) for root in experiment.inputs.get("hypothesis_roots", ()))
        if not expected_roots:
            raise StoreError("bound ExperimentSpec omits exact hypothesis roots")
        record = self.store.one(
            "SELECT canonical_json FROM librsi_records WHERE root=?", (hypothesis_root,)
        )
        hypothesis = deserialize_record(str(record["canonical_json"]))
        if not isinstance(hypothesis, Hypothesis):
            raise ValueError("experiment evidence must target a canonical libRSI hypothesis")
        lineage_roots = {reference.root for reference in hypothesis.lineage}
        if hypothesis_root not in expected_roots:
            admitted_descendant = self.store.one(
                """SELECT 1 AS admitted FROM librsi_record_bindings
                   WHERE mission_id=?
                     AND operational_subject_type='work_item'
                     AND operational_subject_id=?
                     AND semantic_role='hypothesis_update'
                     AND librsi_root=? AND currentness_root=?""",
                (
                    execution["mission_id"],
                    work_item_id,
                    hypothesis_root,
                    experiment_binding["currentness_root"],
                ),
                required=False,
            )
            if admitted_descendant is None or not lineage_roots.intersection(expected_roots):
                raise InvalidTransition(
                    "hypothesis is not the bound experiment root or an admitted immutable descendant"
                )
        snapshot_record = self.store.one(
            "SELECT canonical_json FROM librsi_records WHERE root=?",
            (experiment_binding["currentness_root"],),
        )
        target_snapshot = deserialize_record(str(snapshot_record["canonical_json"]))
        if not isinstance(target_snapshot, TargetSnapshot):
            raise StoreError("experiment binding does not resolve an exact target snapshot")
        if experiment.target_snapshot != target_snapshot:
            raise InvalidTransition("experiment evidence is stale against its bound currentness")
        self.require_live_currentness(
            mission_id=str(execution["mission_id"]), snapshot=target_snapshot
        )
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
            subject_type="work_item",
            subject_id=str(work_item_id),
            role="hypothesis_update",
            record=updated,
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
            if self.work_items is None:
                raise StoreError("supported hypothesis follow-up requires the Factory work owner")
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
