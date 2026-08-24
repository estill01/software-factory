from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import new_id, utc_now


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


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _scope_contains(parent: Mapping[str, Any], child: Mapping[str, Any]) -> bool:
    for key, child_value in child.items():
        if key not in parent:
            return False
        parent_value = parent[key]
        if isinstance(child_value, Mapping):
            if not isinstance(parent_value, Mapping) or not _scope_contains(
                parent_value, child_value
            ):
                return False
        elif isinstance(child_value, list):
            if not isinstance(parent_value, list) or not set(child_value) <= set(parent_value):
                return False
        elif parent_value != child_value:
            return False
    return True


_BEHAVIORAL_PROBE_TYPES = {
    "command",
    "test",
    "integration",
    "installed",
    "operator_visible",
    "protected_capability",
    "migration",
    "release_health",
    "historical_replay",
    "shadow",
    "canary",
}


class GovernanceService:
    """Independent role grants, fail-closed acceptance, and effect reconciliation."""

    def __init__(self, store: Store):
        self.store = store

    def issue_role_grant(
        self,
        *,
        grantee_session_id: str,
        role: str,
        target_type: str,
        target_id: str,
        policy_root: str,
        currentness_root: str,
        expires_at: str,
        scope: Mapping[str, Any] | None = None,
        target_revision: str | None = None,
        mission_id: str | None = None,
        issued_by_session_id: str | None = None,
        parent_grant_id: str | None = None,
        max_uses: int = 1,
    ) -> dict[str, Any]:
        if (
            self.store.one(
                "SELECT id FROM agent_sessions WHERE id=?",
                (grantee_session_id,),
                required=False,
            )
            is None
        ):
            raise StoreError("grantee agent session does not exist")
        if _parse_time(expires_at) <= dt.datetime.now(dt.UTC):
            raise ValueError("role grant cannot be created expired")
        if max_uses <= 0:
            raise ValueError("role grant max_uses must be positive")
        child_scope = dict(scope or {})
        if parent_grant_id is not None:
            parent = self.store.one("SELECT * FROM role_grants_v2 WHERE id=?", (parent_grant_id,))
            if parent["status"] != "active" or _parse_time(parent["expires_at"]) <= dt.datetime.now(
                dt.UTC
            ):
                raise InvalidTransition("parent role grant is inactive")
            if parent["role"] != role:
                raise InvalidTransition("delegated role grant widens the role")
            if (parent["target_type"], parent["target_id"]) != (target_type, target_id):
                raise InvalidTransition("delegated role grant widens the target")
            if parent["target_revision"] not in (None, target_revision):
                raise InvalidTransition("delegated role grant widens the target revision")
            if parent["currentness_root"] != currentness_root:
                raise InvalidTransition("delegated role grant currentness differs")
            if not _scope_contains(_loads(parent["scope_json"], {}), child_scope):
                raise InvalidTransition("delegated role grant widens scope")
            if _parse_time(expires_at) > _parse_time(parent["expires_at"]):
                raise InvalidTransition("delegated role grant outlives its parent")
            if max_uses > int(parent["max_uses"]) - int(parent["use_count"]):
                raise InvalidTransition("delegated role grant exceeds parent use budget")
        grant_id = new_id("role-grant")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO role_grants_v2(
                       id,mission_id,grantee_session_id,role,target_type,target_id,
                       target_revision,policy_root,currentness_root,scope_json,
                       issued_by_session_id,parent_grant_id,max_uses,use_count,
                       expires_at,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,'active',?,?)""",
                (
                    grant_id,
                    mission_id,
                    grantee_session_id,
                    role,
                    target_type,
                    target_id,
                    target_revision,
                    policy_root,
                    currentness_root,
                    _canonical(child_scope),
                    issued_by_session_id,
                    parent_grant_id,
                    max_uses,
                    expires_at,
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM role_grants_v2 WHERE id=?", (grant_id,))

    def _validate_grant(
        self,
        grant_id: str,
        *,
        grantee_session_id: str,
        role: str,
        target_type: str,
        target_id: str,
        target_revision: str | None,
        currentness_root: str,
    ) -> dict[str, Any]:
        grant = self.store.one("SELECT * FROM role_grants_v2 WHERE id=?", (grant_id,))
        if grant["status"] != "active":
            raise InvalidTransition("role grant is not active")
        if _parse_time(grant["expires_at"]) <= dt.datetime.now(dt.UTC):
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE role_grants_v2 SET status='expired',updated_at=? WHERE id=?",
                    (utc_now(), grant_id),
                )
            raise InvalidTransition("role grant is expired")
        expected = (
            grantee_session_id,
            role,
            target_type,
            target_id,
            target_revision,
            currentness_root,
        )
        observed = (
            grant["grantee_session_id"],
            grant["role"],
            grant["target_type"],
            grant["target_id"],
            grant["target_revision"],
            grant["currentness_root"],
        )
        if observed != expected:
            raise InvalidTransition("role grant does not cover the requested review")
        if int(grant["use_count"]) >= int(grant["max_uses"]):
            raise InvalidTransition("role grant exhausted its use budget")
        return grant

    def create_acceptance_contract(
        self,
        *,
        target_type: str,
        target_id: str,
        target_revision: str,
        required_probes: Sequence[Mapping[str, Any]],
        protected_capabilities: Sequence[str] | None = None,
        minimum_independent_reviews: int = 1,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        probes = [dict(probe) for probe in required_probes]
        if not probes:
            raise ValueError("acceptance contract cannot be empty")
        keys = [str(probe.get("key", "")) for probe in probes]
        if any(not key for key in keys) or len(set(keys)) != len(keys):
            raise ValueError("acceptance probes require unique stable keys")
        if not any(str(probe.get("type")) in _BEHAVIORAL_PROBE_TYPES for probe in probes):
            raise ValueError("acceptance requires at least one observed behavioral probe")
        if minimum_independent_reviews <= 0:
            raise ValueError("acceptance requires an independent review")
        material = {
            "target_type": target_type,
            "target_id": target_id,
            "target_revision": target_revision,
            "required_probes": probes,
            "protected_capabilities": _ids(protected_capabilities),
            "minimum_independent_reviews": minimum_independent_reviews,
        }
        spec_root = _digest(material)
        existing = self.store.one(
            """SELECT * FROM acceptance_contracts_v2
               WHERE target_type=? AND target_id=? AND target_revision=?
                 AND acceptance_spec_root=?""",
            (target_type, target_id, target_revision, spec_root),
            required=False,
        )
        if existing is not None:
            return existing
        contract_id = new_id("acceptance-contract")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """UPDATE acceptance_contracts_v2 SET status='superseded',updated_at=?
                   WHERE target_type=? AND target_id=? AND status='active'""",
                (now, target_type, target_id),
            )
            db.execute(
                """INSERT INTO acceptance_contracts_v2(
                       id,mission_id,target_type,target_id,target_revision,
                       acceptance_spec_root,required_probes_json,
                       protected_capabilities_json,minimum_independent_reviews,
                       status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'active',?,?)""",
                (
                    contract_id,
                    mission_id,
                    target_type,
                    target_id,
                    target_revision,
                    spec_root,
                    _canonical(probes),
                    _canonical(_ids(protected_capabilities)),
                    minimum_independent_reviews,
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,))

    def record_probe_result(
        self,
        contract_id: str,
        *,
        probe_key: str,
        exact_revision: str,
        disposition: Literal["passed", "failed", "inconclusive", "invalid"],
        observed_result: Mapping[str, Any],
        evidence_ids: Sequence[str],
        command: Sequence[str] | None = None,
        observer_session_id: str | None = None,
    ) -> dict[str, Any]:
        contract = self.store.one(
            "SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,)
        )
        if contract["status"] != "active" or contract["target_revision"] != exact_revision:
            raise InvalidTransition("acceptance contract is stale for this revision")
        probes = {
            str(probe["key"]): probe for probe in _loads(contract["required_probes_json"], [])
        }
        if probe_key not in probes:
            raise InvalidTransition("probe is not part of the acceptance contract")
        evidence = _ids(evidence_ids)
        if not evidence:
            raise ValueError("probe result requires observed evidence")
        result_id = new_id("probe-result")
        with self.store.transaction() as db:
            db.execute(
                """INSERT OR REPLACE INTO acceptance_probe_results_v2(
                       id,contract_id,probe_key,probe_type,exact_revision,command_json,
                       observed_result_json,evidence_ids_json,disposition,
                       observer_session_id,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result_id,
                    contract_id,
                    probe_key,
                    str(probes[probe_key]["type"]),
                    exact_revision,
                    _canonical(list(command)) if command else None,
                    _canonical(dict(observed_result)),
                    _canonical(evidence),
                    disposition,
                    observer_session_id,
                    utc_now(),
                ),
            )
        return self.store.one(
            """SELECT * FROM acceptance_probe_results_v2
               WHERE contract_id=? AND probe_key=? AND exact_revision=?""",
            (contract_id, probe_key, exact_revision),
        )

    def record_independent_review(
        self,
        contract_id: str,
        *,
        grant_id: str,
        reviewer_session_id: str,
        implementer_session_id: str | None,
        exact_revision: str,
        currentness_root: str,
        review_contract: Mapping[str, Any],
        provider_session_id: str,
        transcript_artifact_id: str,
        evidence_ids: Sequence[str],
        disposition: Literal["accepted", "rejected", "revise", "inconclusive"],
        findings: Mapping[str, Any],
    ) -> dict[str, Any]:
        contract = self.store.one(
            "SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,)
        )
        if contract["status"] != "active" or contract["target_revision"] != exact_revision:
            raise InvalidTransition("review target revision is stale")
        if reviewer_session_id == implementer_session_id:
            raise InvalidTransition("implementer cannot independently review the revision")
        reviewer = self.store.one("SELECT * FROM agent_sessions WHERE id=?", (reviewer_session_id,))
        if str(reviewer.get("provider_session_id") or "") != provider_session_id:
            raise InvalidTransition("review provider identity does not match the granted session")
        self._validate_grant(
            grant_id,
            grantee_session_id=reviewer_session_id,
            role="independent_reviewer",
            target_type=contract["target_type"],
            target_id=contract["target_id"],
            target_revision=exact_revision,
            currentness_root=currentness_root,
        )
        evidence = _ids(evidence_ids)
        if not transcript_artifact_id or not evidence:
            raise ValueError("independent review requires transcript and evidence artifacts")
        review_root = _digest(
            {
                "contract_id": contract_id,
                "exact_revision": exact_revision,
                "review_contract": dict(review_contract),
                "provider_session_id": provider_session_id,
                "transcript_artifact_id": transcript_artifact_id,
                "evidence_ids": evidence,
                "disposition": disposition,
                "findings": dict(findings),
            }
        )
        review_id = new_id("independent-review")
        with self.store.transaction() as db:
            current = db.execute("SELECT * FROM role_grants_v2 WHERE id=?", (grant_id,)).fetchone()
            if current is None or current["status"] != "active":
                raise InvalidTransition("role grant was consumed concurrently")
            use_count = int(current["use_count"]) + 1
            if use_count > int(current["max_uses"]):
                raise InvalidTransition("role grant use budget was consumed concurrently")
            db.execute(
                """UPDATE role_grants_v2
                   SET use_count=?,status=?,updated_at=? WHERE id=?""",
                (
                    use_count,
                    "consumed" if use_count >= int(current["max_uses"]) else "active",
                    utc_now(),
                    grant_id,
                ),
            )
            db.execute(
                """INSERT INTO independent_review_executions_v2(
                       id,contract_id,grant_id,reviewer_session_id,implementer_session_id,
                       exact_revision,review_contract_root,provider_session_id,
                       transcript_artifact_id,evidence_ids_json,disposition,
                       findings_json,status,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'completed',?)""",
                (
                    review_id,
                    contract_id,
                    grant_id,
                    reviewer_session_id,
                    implementer_session_id,
                    exact_revision,
                    review_root,
                    provider_session_id,
                    transcript_artifact_id,
                    _canonical(evidence),
                    disposition,
                    _canonical(dict(findings)),
                    utc_now(),
                ),
            )
        return self.store.one(
            "SELECT * FROM independent_review_executions_v2 WHERE id=?", (review_id,)
        )

    def decide_acceptance(self, contract_id: str, *, exact_revision: str) -> dict[str, Any]:
        contract = self.store.one(
            "SELECT * FROM acceptance_contracts_v2 WHERE id=?", (contract_id,)
        )
        if contract["status"] != "active" or contract["target_revision"] != exact_revision:
            raise InvalidTransition("acceptance contract is stale")
        probes = _loads(contract["required_probes_json"], [])
        results = self.store.all(
            """SELECT * FROM acceptance_probe_results_v2
               WHERE contract_id=? AND exact_revision=?""",
            (contract_id, exact_revision),
        )
        latest_by_key = {str(result["probe_key"]): result for result in results}
        missing_or_failed = [
            str(probe["key"])
            for probe in probes
            if latest_by_key.get(str(probe["key"]), {}).get("disposition") != "passed"
        ]
        if missing_or_failed:
            raise InvalidTransition(
                f"acceptance probes are incomplete or failing: {missing_or_failed}"
            )
        reviews = self.store.all(
            """SELECT * FROM independent_review_executions_v2
               WHERE contract_id=? AND exact_revision=? AND status='completed'""",
            (contract_id, exact_revision),
        )
        accepted_reviews = [review for review in reviews if review["disposition"] == "accepted"]
        distinct_reviewers = {str(review["reviewer_session_id"]) for review in accepted_reviews}
        if len(distinct_reviewers) < int(contract["minimum_independent_reviews"]):
            raise InvalidTransition("insufficient independent accepted reviews")
        if any(review["disposition"] in {"rejected", "revise"} for review in reviews):
            raise InvalidTransition("an independent review still rejects or revises the candidate")
        probe_ids = sorted(str(result["id"]) for result in latest_by_key.values())
        review_ids = sorted(str(review["id"]) for review in accepted_reviews)
        evidence_root = _digest(
            {
                "contract_id": contract_id,
                "revision": exact_revision,
                "probe_result_ids": probe_ids,
                "review_execution_ids": review_ids,
            }
        )
        decision_id = new_id("acceptance-decision")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO acceptance_decisions_v2(
                       id,contract_id,exact_revision,decision,probe_result_ids_json,
                       review_execution_ids_json,evidence_root,decided_at
                   ) VALUES(?,?,?,'accepted',?,?,?,?)""",
                (
                    decision_id,
                    contract_id,
                    exact_revision,
                    _canonical(probe_ids),
                    _canonical(review_ids),
                    evidence_root,
                    utc_now(),
                ),
            )
            db.execute(
                """UPDATE acceptance_contracts_v2
                   SET status='satisfied',updated_at=? WHERE id=?""",
                (utc_now(), contract_id),
            )
        return self.store.one("SELECT * FROM acceptance_decisions_v2 WHERE id=?", (decision_id,))

    def invalidate_target_revision(
        self,
        *,
        target_type: str,
        target_id: str,
        prior_revision: str,
    ) -> None:
        with self.store.transaction() as db:
            contracts = db.execute(
                """SELECT id FROM acceptance_contracts_v2
                   WHERE target_type=? AND target_id=? AND target_revision=?
                     AND status IN ('active','satisfied')""",
                (target_type, target_id, prior_revision),
            ).fetchall()
            for contract in contracts:
                db.execute(
                    "UPDATE acceptance_contracts_v2 SET status='stale',updated_at=? WHERE id=?",
                    (utc_now(), contract["id"]),
                )
                db.execute(
                    """UPDATE independent_review_executions_v2
                       SET status='invalidated' WHERE contract_id=?""",
                    (contract["id"],),
                )
                db.execute(
                    """UPDATE acceptance_decisions_v2 SET decision='stale'
                       WHERE contract_id=?""",
                    (contract["id"],),
                )

    def claim_effect(
        self,
        *,
        effect_type: str,
        target_type: str,
        target_id: str,
        idempotency_key: str,
        request: Mapping[str, Any],
        probe_spec: Mapping[str, Any] | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        command_root = _digest(
            {
                "effect_type": effect_type,
                "target_type": target_type,
                "target_id": target_id,
                "request": dict(request),
                "probe_spec": dict(probe_spec or {}),
            }
        )
        existing = self.store.one(
            "SELECT * FROM external_effect_intents_v2 WHERE idempotency_key=?",
            (idempotency_key,),
            required=False,
        )
        if existing is not None:
            if existing["command_root"] != command_root:
                raise InvalidTransition("effect idempotency key collides with a different command")
            return existing
        effect_id = new_id("external-effect")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO external_effect_intents_v2(
                       id,mission_id,effect_type,target_type,target_id,idempotency_key,
                       command_root,request_json,probe_spec_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'claimed',?,?)""",
                (
                    effect_id,
                    mission_id,
                    effect_type,
                    target_type,
                    target_id,
                    idempotency_key,
                    command_root,
                    _canonical(dict(request)),
                    _canonical(dict(probe_spec or {})),
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))

    def start_effect(
        self,
        effect_id: str,
        *,
        lease_owner: str,
        lease_expires_at: str,
    ) -> dict[str, Any]:
        effect = self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))
        if effect["status"] not in {"claimed", "ambiguous", "failed"}:
            raise InvalidTransition("effect is not startable")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE external_effect_intents_v2
                   SET status='started',lease_owner=?,lease_expires_at=?,started_at=?,updated_at=?
                   WHERE id=?""",
                (lease_owner, lease_expires_at, utc_now(), utc_now(), effect_id),
            )
        return self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))

    def observe_effect(
        self,
        effect_id: str,
        *,
        provider_reference: str,
        observed_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        effect = self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))
        if effect["status"] not in {"started", "ambiguous", "observed"}:
            raise InvalidTransition("effect is not awaiting observation")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE external_effect_intents_v2
                   SET status='observed',provider_reference=?,observed_result_json=?,
                       observed_at=?,updated_at=? WHERE id=?""",
                (
                    provider_reference,
                    _canonical(dict(observed_result)),
                    utc_now(),
                    utc_now(),
                    effect_id,
                ),
            )
        return self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))

    def complete_effect(
        self,
        effect_id: str,
        *,
        succeeded: bool,
        error: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        effect = self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))
        if effect["status"] not in {"observed", "started", "ambiguous"}:
            raise InvalidTransition("effect is not completable")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE external_effect_intents_v2
                   SET status=?,error_json=?,completed_at=?,lease_owner=NULL,
                       lease_expires_at=NULL,updated_at=? WHERE id=?""",
                (
                    "succeeded" if succeeded else "failed",
                    _canonical(dict(error or {})) if error else None,
                    utc_now(),
                    utc_now(),
                    effect_id,
                ),
            )
        return self.store.one("SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect_id,))

    def reconcile_stale_effects(
        self,
        *,
        now: str,
        probe: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = self.store.all(
            """SELECT * FROM external_effect_intents_v2
               WHERE status IN ('started','ambiguous')
                 AND lease_expires_at IS NOT NULL AND lease_expires_at<=?
               ORDER BY created_at""",
            (now,),
        )
        reconciled: list[dict[str, Any]] = []
        for row in rows:
            result = dict(probe(row))
            disposition = result.get("disposition")
            if disposition == "succeeded":
                self.observe_effect(
                    row["id"],
                    provider_reference=str(result.get("provider_reference", "reconciled")),
                    observed_result=result,
                )
                reconciled.append(self.complete_effect(row["id"], succeeded=True))
            elif disposition == "failed":
                reconciled.append(
                    self.complete_effect(
                        row["id"],
                        succeeded=False,
                        error={"kind": "reconciled_provider_failure", "probe": result},
                    )
                )
            else:
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE external_effect_intents_v2
                           SET status='ambiguous',observed_result_json=?,updated_at=? WHERE id=?""",
                        (_canonical(result), utc_now(), row["id"]),
                    )
                reconciled.append(
                    self.store.one(
                        "SELECT * FROM external_effect_intents_v2 WHERE id=?", (row["id"],)
                    )
                )
        return reconciled

    def link_notification_report(self, notification_id: str, report_id: str) -> None:
        with self.store.transaction() as db:
            db.execute(
                """INSERT OR IGNORE INTO notification_report_links_v2(notification_id,report_id)
                   VALUES(?,?)""",
                (notification_id, report_id),
            )

    def propagate_notification_status(self, notification_id: str) -> None:
        notification = self.store.one(
            "SELECT * FROM notifications_v2 WHERE id=?", (notification_id,)
        )
        report_status = {
            "delivered": "delivered",
            "read": "read",
            "failed": "failed",
        }.get(notification["status"])
        if report_status is None:
            return
        with self.store.transaction() as db:
            db.execute(
                """UPDATE reports_v2 SET status=?,updated_at=?
                   WHERE id IN (
                       SELECT report_id FROM notification_report_links_v2
                       WHERE notification_id=?
                   )""",
                (report_status, utc_now(), notification_id),
            )
