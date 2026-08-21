from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, TypeVar

from rsi_core import RSIKernel, RSITransitionError

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import new_id, utc_now


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _ids(values: Sequence[str] | None) -> list[str]:
    return sorted({str(value) for value in (values or ()) if str(value)})


T = TypeVar("T")


class EvolutionService:
    """Recursive program evolution and selection-quality RSI.

    Program changes preserve requested-range and accepted-history roots and are
    independently reviewed before any effect. Tracker effects are exact-byte,
    currentness-bound filesystem transitions with rollback on failed validation.
    Considered choices share one selection table; adoption is a status and outcome
    transition, not a separate decision-option ontology.
    """

    def __init__(self, store: Store, *, rsi: RSIKernel | None = None):
        self.store = store
        self.rsi = rsi or RSIKernel()

    @staticmethod
    def _transition(operation: Callable[[], T]) -> T:
        try:
            return operation()
        except RSITransitionError as exc:
            raise InvalidTransition(str(exc)) from exc

    def _require_mission(self, mission_id: str) -> None:
        if self.store.one(
            "SELECT id FROM missions WHERE id=?", (mission_id,), required=False
        ) is None:
            raise StoreError(f"mission not found: {mission_id}")

    def checkpoint(
        self,
        *,
        mission_id: str,
        boundary_type: Literal[
            "work", "block", "checkpoint", "terminal", "cross_run", "structural"
        ],
        source_type: str,
        source_id: str,
        state: Mapping[str, Any],
        observations: Mapping[str, Any],
        evidence_ids: Sequence[str],
        program_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        evidence = _ids(evidence_ids)
        previous = self.store.one(
            """SELECT * FROM evolution_checkpoints_v2
               WHERE mission_id=? AND boundary_type=? AND source_type=? AND source_id=?
               ORDER BY created_at DESC LIMIT 1""",
            (mission_id, boundary_type, source_type, source_id),
            required=False,
        )
        decision = self.rsi.checkpoint(
            state=state,
            evidence_ids=evidence,
            previous_fingerprint=(
                str(previous["state_fingerprint"]) if previous is not None else None
            ),
        )
        if not decision.material:
            return {
                "id": previous["id"],
                "mission_id": mission_id,
                "state_fingerprint": decision.state_fingerprint,
                "material": False,
                "action": decision.action,
            }
        checkpoint_id = new_id("evolution-checkpoint")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO evolution_checkpoints_v2(
                       id,mission_id,program_id,boundary_type,source_type,source_id,
                       state_fingerprint,material,observations_json,evidence_ids_json,created_at
                   ) VALUES(?,?,?,?,?,?,?,1,?,?,?)""",
                (
                    checkpoint_id,
                    mission_id,
                    program_id,
                    boundary_type,
                    source_type,
                    source_id,
                    decision.state_fingerprint,
                    _canonical(dict(observations)),
                    _canonical(evidence),
                    utc_now(),
                ),
            )
        return self.store.one(
            "SELECT * FROM evolution_checkpoints_v2 WHERE id=?", (checkpoint_id,)
        )

    def propose_program_change(
        self,
        *,
        mission_id: str,
        change_kind: Literal[
            "amend_current", "successor", "parallel_portfolio", "split", "merge", "retire", "replace"
        ],
        rationale: Mapping[str, Any],
        change_spec: Mapping[str, Any],
        requested_range_root: str,
        accepted_history_root: str,
        currentness_root: str,
        program_id: str | None = None,
        checkpoint_id: str | None = None,
        author_session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        candidate_root = self.rsi.program_change_root(
            scope_id=mission_id,
            program_id=program_id,
            change_kind=change_kind,
            rationale=rationale,
            change_spec=change_spec,
            requested_range_root=requested_range_root,
            accepted_history_root=accepted_history_root,
            currentness_root=currentness_root,
        )
        existing = self.store.one(
            """SELECT * FROM program_change_candidates_v2
               WHERE mission_id=? AND candidate_root=?""",
            (mission_id, candidate_root),
            required=False,
        )
        if existing is not None:
            return existing
        change_id = new_id("program-change")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO program_change_candidates_v2(
                       id,mission_id,program_id,checkpoint_id,change_kind,author_session_id,
                       rationale_json,change_spec_json,requested_range_root,
                       accepted_history_root,currentness_root,candidate_root,
                       review_status,application_status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'pending','pending',?,?)""",
                (
                    change_id,
                    mission_id,
                    program_id,
                    checkpoint_id,
                    change_kind,
                    author_session_id,
                    _canonical(dict(rationale)),
                    _canonical(dict(change_spec)),
                    requested_range_root,
                    accepted_history_root,
                    currentness_root,
                    candidate_root,
                    now,
                    now,
                ),
            )
        return self.store.one(
            "SELECT * FROM program_change_candidates_v2 WHERE id=?", (change_id,)
        )

    def review_program_change(
        self,
        change_id: str,
        *,
        reviewer_session_id: str,
        disposition: Literal["accepted", "revise", "rejected"],
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        change = self.store.one(
            "SELECT * FROM program_change_candidates_v2 WHERE id=?", (change_id,)
        )
        if change["review_status"] != "pending":
            raise InvalidTransition("program change was already reviewed")
        self._transition(
            lambda: self.rsi.require_independent_actor(
                author_id=change["author_session_id"],
                reviewer_id=reviewer_session_id,
                subject="program change author",
            )
        )
        evidence = _ids(evidence_ids)
        if not evidence:
            raise ValueError("program change review requires evidence")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE program_change_candidates_v2
                   SET review_status=?,reviewer_session_id=?,review_evidence_ids_json=?,
                       updated_at=? WHERE id=?""",
                (disposition, reviewer_session_id, _canonical(evidence), utc_now(), change_id),
            )
        return self.store.one(
            "SELECT * FROM program_change_candidates_v2 WHERE id=?", (change_id,)
        )

    def apply_tracker_change(
        self,
        change_id: str,
        *,
        repository_root: str | Path,
        currentness_root: str,
        validation_command: Sequence[str] | None = None,
        commit: bool = False,
    ) -> dict[str, Any]:
        change = self.store.one(
            "SELECT * FROM program_change_candidates_v2 WHERE id=?", (change_id,)
        )
        self._transition(
            lambda: self.rsi.require_program_change_application(
                review_status=change["review_status"],
                application_status=change["application_status"],
                reviewed_currentness_root=change["currentness_root"],
                currentness_root=currentness_root,
            )
        )
        spec = _loads(change["change_spec_json"], {})
        relative_path = spec.get("tracker_path")
        new_content = spec.get("new_content")
        expected_sha256 = spec.get("expected_sha256")
        if not isinstance(relative_path, str) or not isinstance(new_content, str):
            raise ValueError("tracker change requires tracker_path and new_content")
        root = Path(repository_root).resolve()
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("tracker path escapes repository root") from exc
        if target.is_symlink():
            raise ValueError("tracker path may not be a symlink")
        old_bytes = target.read_bytes() if target.exists() else b""
        old_sha256 = _bytes_digest(old_bytes)
        if expected_sha256 is not None and expected_sha256 != old_sha256:
            raise InvalidTransition("tracker bytes changed after change review")
        new_bytes = new_content.encode("utf-8")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE program_change_candidates_v2
                   SET application_status='applying',updated_at=? WHERE id=?""",
                (now, change_id),
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(new_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            Path(temporary_name).replace(target)
            validation: dict[str, Any] = {"command": None, "exit_code": 0}
            if validation_command:
                process = subprocess.run(
                    [str(part) for part in validation_command],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                validation = {
                    "command": list(validation_command),
                    "exit_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }
                if process.returncode != 0:
                    raise RuntimeError("tracker validation failed")
            commit_sha: str | None = None
            if commit:
                subprocess.run(["git", "add", "--", relative_path], cwd=root, check=True)
                subprocess.run(
                    ["git", "commit", "-m", f"evolve: apply {change['change_kind']}"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                commit_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            result = {
                "tracker_path": relative_path,
                "before_sha256": old_sha256,
                "after_sha256": _bytes_digest(new_bytes),
                "validation": validation,
                "commit_sha": commit_sha,
            }
        except BaseException as exc:
            if old_bytes:
                target.write_bytes(old_bytes)
            else:
                target.unlink(missing_ok=True)
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE program_change_candidates_v2
                       SET application_status='failed',application_result_json=?,updated_at=?
                       WHERE id=?""",
                    (_canonical({"error": str(exc), "rolled_back": True}), utc_now(), change_id),
                )
            raise
        finally:
            Path(temporary_name).unlink(missing_ok=True)
        with self.store.transaction() as db:
            db.execute(
                """UPDATE program_change_candidates_v2
                   SET application_status='applied',application_result_json=?,updated_at=?
                   WHERE id=?""",
                (_canonical(result), utc_now(), change_id),
            )
        return self.store.one(
            "SELECT * FROM program_change_candidates_v2 WHERE id=?", (change_id,)
        )

    def create_portfolio(
        self,
        *,
        mission_id: str,
        mode: Literal["sequential", "parallel"],
        lanes: Sequence[Mapping[str, Any]],
        baseline_currentness_root: str,
        parent_program_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        self.rsi.validate_portfolio_lanes(lanes)
        portfolio_id = new_id("program-portfolio")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO program_portfolios_v2(
                       id,mission_id,parent_program_id,mode,baseline_currentness_root,
                       lanes_json,active_lane_ids_json,completed_lane_ids_json,
                       status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,'[]','[]','planned',?,?)""",
                (
                    portfolio_id,
                    mission_id,
                    parent_program_id,
                    mode,
                    baseline_currentness_root,
                    _canonical([dict(lane) for lane in lanes]),
                    utc_now(),
                    utc_now(),
                ),
            )
        return self.store.one(
            "SELECT * FROM program_portfolios_v2 WHERE id=?", (portfolio_id,)
        )

    def activate_portfolio(
        self, portfolio_id: str, *, currentness_root: str
    ) -> dict[str, Any]:
        portfolio = self.store.one(
            "SELECT * FROM program_portfolios_v2 WHERE id=?", (portfolio_id,)
        )
        lanes = _loads(portfolio["lanes_json"], [])
        transition = self._transition(
            lambda: self.rsi.activate_portfolio(
                mode=portfolio["mode"],
                lanes=lanes,
                status=portfolio["status"],
                baseline_currentness_root=portfolio["baseline_currentness_root"],
                currentness_root=currentness_root,
            )
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE program_portfolios_v2
                   SET status='active',active_lane_ids_json=?,updated_at=? WHERE id=?""",
                (_canonical(list(transition.active_lane_ids)), utc_now(), portfolio_id),
            )
        return self.store.one(
            "SELECT * FROM program_portfolios_v2 WHERE id=?", (portfolio_id,)
        )

    def complete_portfolio_lane(
        self,
        portfolio_id: str,
        *,
        lane_id: str,
        succeeded: bool,
    ) -> dict[str, Any]:
        portfolio = self.store.one(
            "SELECT * FROM program_portfolios_v2 WHERE id=?", (portfolio_id,)
        )
        lanes = _loads(portfolio["lanes_json"], [])
        transition = self._transition(
            lambda: self.rsi.complete_portfolio_lane(
                mode=portfolio["mode"],
                lanes=lanes,
                status=portfolio["status"],
                active_lane_ids=_loads(portfolio["active_lane_ids_json"], []),
                completed_lane_ids=_loads(portfolio["completed_lane_ids_json"], []),
                lane_id=lane_id,
                succeeded=succeeded,
            )
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE program_portfolios_v2
                   SET active_lane_ids_json=?,completed_lane_ids_json=?,status=?,updated_at=?
                   WHERE id=?""",
                (
                    _canonical(list(transition.active_lane_ids)),
                    _canonical(list(transition.completed_lane_ids)),
                    transition.status,
                    utc_now(),
                    portfolio_id,
                ),
            )
        return self.store.one(
            "SELECT * FROM program_portfolios_v2 WHERE id=?", (portfolio_id,)
        )

    def consider_selection(
        self,
        *,
        mission_id: str,
        selection_group: str,
        selection_type: Literal[
            "feature", "problem", "design", "architecture", "strategy", "program", "experiment", "policy"
        ],
        candidate_key: str,
        candidate: Mapping[str, Any],
        evidence: Mapping[str, Any],
        expected_value: Mapping[str, Any],
        proposer_session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        if not selection_group or not candidate_key:
            raise ValueError("selection group and candidate key are required")
        selection_id = new_id("selection")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO selection_records_v2(
                       id,mission_id,selection_group,selection_type,candidate_key,
                       proposer_session_id,candidate_json,evidence_json,
                       expected_value_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'considered',?,?)""",
                (
                    selection_id,
                    mission_id,
                    selection_group,
                    selection_type,
                    candidate_key,
                    proposer_session_id,
                    _canonical(dict(candidate)),
                    _canonical(dict(evidence)),
                    _canonical(dict(expected_value)),
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM selection_records_v2 WHERE id=?", (selection_id,))

    def review_selection(
        self,
        selection_id: str,
        *,
        reviewer_session_id: str,
        disposition: Literal["accept", "challenge", "reject", "defer"],
        findings: Mapping[str, Any],
        evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        selection = self.store.one(
            "SELECT * FROM selection_records_v2 WHERE id=?", (selection_id,)
        )
        self._transition(
            lambda: self.rsi.require_independent_actor(
                author_id=selection["proposer_session_id"],
                reviewer_id=reviewer_session_id,
                subject="selection proposer",
            )
        )
        evidence = _ids(evidence_ids)
        review_root = self.rsi.selection_review_root(
            selection_id=selection_id,
            disposition=disposition,
            findings=findings,
            evidence_ids=evidence,
        )
        review_id = new_id("selection-review")
        status = {
            "accept": "considered",
            "challenge": "challenged",
            "reject": "rejected",
            "defer": "deferred",
        }[disposition]
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO selection_reviews_v2(
                       id,selection_id,reviewer_session_id,disposition,findings_json,
                       evidence_ids_json,review_root,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    review_id,
                    selection_id,
                    reviewer_session_id,
                    disposition,
                    _canonical(dict(findings)),
                    _canonical(evidence),
                    review_root,
                    utc_now(),
                ),
            )
            db.execute(
                "UPDATE selection_records_v2 SET status=?,updated_at=? WHERE id=?",
                (status, utc_now(), selection_id),
            )
        return self.store.one("SELECT * FROM selection_reviews_v2 WHERE id=?", (review_id,))

    def select_candidate(
        self,
        selection_id: str,
        *,
        selector_session_id: str,
        rationale: Mapping[str, Any],
    ) -> dict[str, Any]:
        selection = self.store.one(
            "SELECT * FROM selection_records_v2 WHERE id=?", (selection_id,)
        )
        accepted_review = self.store.one(
            """SELECT id FROM selection_reviews_v2
               WHERE selection_id=? AND disposition='accept'
               ORDER BY created_at DESC LIMIT 1""",
            (selection_id,),
            required=False,
        )
        self._transition(
            lambda: self.rsi.require_selectable(
                status=selection["status"],
                has_accepting_review=accepted_review is not None,
            )
        )
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE selection_records_v2
                   SET status='selected',selector_session_id=?,rationale_json=?,
                       selected_at=?,updated_at=? WHERE id=?""",
                (selector_session_id, _canonical(dict(rationale)), now, now, selection_id),
            )
        return self.store.one("SELECT * FROM selection_records_v2 WHERE id=?", (selection_id,))

    def record_selection_outcome(
        self,
        selection_id: str,
        *,
        outcome_type: Literal["success", "failure", "mixed", "unknown", "counterfactual_limit"],
        metrics: Mapping[str, Any],
        evidence_ids: Sequence[str],
        causal_confidence: float,
        limitations: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selection = self.store.one(
            "SELECT * FROM selection_records_v2 WHERE id=?", (selection_id,)
        )
        if selection["status"] != "selected":
            raise InvalidTransition("only a selected candidate can receive an outcome")
        self.rsi.validate_causal_confidence(causal_confidence)
        outcome_id = new_id("selection-outcome")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO selection_outcomes_v2(
                       id,selection_id,outcome_type,metrics_json,evidence_ids_json,
                       causal_confidence,limitations_json,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    outcome_id,
                    selection_id,
                    outcome_type,
                    _canonical(dict(metrics)),
                    _canonical(_ids(evidence_ids)),
                    causal_confidence,
                    _canonical(dict(limitations or {})),
                    utc_now(),
                ),
            )
        return self.store.one("SELECT * FROM selection_outcomes_v2 WHERE id=?", (outcome_id,))

    def propose_selector_policy(
        self,
        *,
        mission_id: str,
        name: str,
        policy: Mapping[str, Any],
        author_session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_mission(mission_id)
        policy_root = self.rsi.selector_policy_root(policy)
        existing = self.store.one(
            """SELECT * FROM selector_policy_candidates_v2
               WHERE mission_id=? AND policy_root=?""",
            (mission_id, policy_root),
            required=False,
        )
        if existing is not None:
            return existing
        candidate_id = new_id("selector-policy")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO selector_policy_candidates_v2(
                       id,mission_id,name,policy_json,policy_root,author_session_id,
                       status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,'candidate',?,?)""",
                (candidate_id, mission_id, name, _canonical(dict(policy)), policy_root, author_session_id, now, now),
            )
        return self.store.one(
            "SELECT * FROM selector_policy_candidates_v2 WHERE id=?", (candidate_id,)
        )

    def evaluate_selector_policy(
        self,
        candidate_id: str,
        *,
        evaluation_type: Literal["historical", "forward_shadow", "independent_review", "live_effectiveness"],
        disposition: Literal[
            "passed", "failed", "inconclusive", "accepted", "rejected", "revise", "effective", "ineffective"
        ],
        metrics: Mapping[str, Any],
        evidence_ids: Sequence[str],
        case_ids: Sequence[str] | None = None,
        evaluator_session_id: str | None = None,
    ) -> dict[str, Any]:
        candidate = self.store.one(
            "SELECT * FROM selector_policy_candidates_v2 WHERE id=?", (candidate_id,)
        )
        try:
            self.rsi.require_independent_actor(
                author_id=candidate["author_session_id"],
                reviewer_id=evaluator_session_id,
                subject="selector-policy",
            )
        except RSITransitionError as exc:
            raise InvalidTransition(
                "selector-policy author cannot independently evaluate it"
            ) from exc
        if not evidence_ids:
            raise ValueError("selector-policy evaluation requires evidence")
        evaluation_id = new_id("selector-policy-evaluation")
        update = self.rsi.policy_evaluation_update(
            evaluation_type=evaluation_type,
            disposition=disposition,
        )
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO selector_policy_evaluations_v2(
                       id,policy_candidate_id,evaluation_type,disposition,case_ids_json,
                       metrics_json,evidence_ids_json,evaluator_session_id,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    evaluation_id,
                    candidate_id,
                    evaluation_type,
                    disposition,
                    _canonical(_ids(case_ids)),
                    _canonical(dict(metrics)),
                    _canonical(_ids(evidence_ids)),
                    evaluator_session_id,
                    utc_now(),
                ),
            )
            if update.status_field is not None:
                db.execute(
                    f"""UPDATE selector_policy_candidates_v2
                        SET {update.status_field}=?,status='evaluating',updated_at=? WHERE id=?""",
                    (update.normalized_disposition, utc_now(), candidate_id),
                )
        return self.store.one(
            "SELECT * FROM selector_policy_evaluations_v2 WHERE id=?", (evaluation_id,)
        )

    def activate_selector_policy(self, candidate_id: str) -> dict[str, Any]:
        candidate = self.store.one(
            "SELECT * FROM selector_policy_candidates_v2 WHERE id=?", (candidate_id,)
        )
        self._transition(
            lambda: self.rsi.require_selector_policy_activation(
                historical_status=candidate["historical_status"],
                forward_status=candidate["forward_status"],
                review_status=candidate["review_status"],
            )
        )
        policy_id = new_id("active-selector-policy")
        now = utc_now()
        with self.store.transaction() as db:
            latest = db.execute(
                """SELECT COALESCE(MAX(version),0) AS version FROM active_selector_policies_v2
                   WHERE mission_id=?""",
                (candidate["mission_id"],),
            ).fetchone()
            version = int(latest["version"]) + 1
            db.execute(
                """UPDATE active_selector_policies_v2
                   SET status='superseded',deactivated_at=?
                   WHERE mission_id=? AND status='active'""",
                (now, candidate["mission_id"]),
            )
            db.execute(
                """INSERT INTO active_selector_policies_v2(
                       id,mission_id,policy_candidate_id,policy_root,version,status,activated_at
                   ) VALUES(?,?,?,?,?,'active',?)""",
                (policy_id, candidate["mission_id"], candidate_id, candidate["policy_root"], version, now),
            )
            db.execute(
                """UPDATE selector_policy_candidates_v2
                   SET status='active',updated_at=? WHERE id=?""",
                (now, candidate_id),
            )
        return self.store.one("SELECT * FROM active_selector_policies_v2 WHERE id=?", (policy_id,))

    def rollback_selector_policy(
        self, policy_id: str, *, evidence_ids: Sequence[str]
    ) -> dict[str, Any]:
        policy = self.store.one(
            "SELECT * FROM active_selector_policies_v2 WHERE id=?", (policy_id,)
        )
        self._transition(
            lambda: self.rsi.require_selector_policy_rollback(
                status=policy["status"], evidence_ids=evidence_ids
            )
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE active_selector_policies_v2
                   SET status='rolled_back',deactivated_at=? WHERE id=?""",
                (utc_now(), policy_id),
            )
            db.execute(
                """UPDATE selector_policy_candidates_v2
                   SET status='rolled_back',updated_at=? WHERE id=?""",
                (utc_now(), policy["policy_candidate_id"]),
            )
        return self.store.one(
            "SELECT * FROM active_selector_policies_v2 WHERE id=?", (policy_id,)
        )
