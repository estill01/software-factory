from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .governance import GovernanceService
from .operations import OperationsService
from .store import Store


class FactoryRecoveryCoordinator:
    """Closed-loop Software Factory repair and exact-once target resumption."""

    def __init__(
        self,
        store: Store,
        *,
        operations: OperationsService | None = None,
        governance: GovernanceService | None = None,
    ):
        self.store = store
        self._operations = operations or OperationsService(store)
        self.governance = governance or GovernanceService(store)

    def recover(
        self,
        *,
        target_mission_id: str,
        defect_class: str,
        defect_evidence: Mapping[str, Any],
        target_state: Mapping[str, Any],
        requested_range_root: str,
        tracker_currentness_root: str,
        safe_frontier: Sequence[Mapping[str, Any]],
        release_root: str | Path,
        repair: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        review: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        wake_target: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        verify_target: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        implementer_session_id: str = "factory-repair-implementer",
        reviewer_session_id: str = "factory-repair-reviewer",
    ) -> dict[str, Any]:
        recovery = self._operations.open_recovery(
            target_mission_id=target_mission_id,
            defect_class=defect_class,
            defect_evidence=defect_evidence,
            target_state=target_state,
            requested_range_root=requested_range_root,
            tracker_currentness_root=tracker_currentness_root,
            safe_frontier=safe_frontier,
        )
        repair_result = dict(repair(recovery))
        required = {
            "source_root",
            "source_revision",
            "source_tree_root",
            "repair_evidence_ids",
            "health_command",
        }
        missing = sorted(required - set(repair_result))
        if missing:
            raise ValueError(f"Factory repair result is incomplete: {missing}")
        staged = self._operations.stage_release(
            source_root=repair_result["source_root"],
            release_root=release_root,
            source_revision=str(repair_result["source_revision"]),
            source_tree_root=str(repair_result["source_tree_root"]),
            mission_id=target_mission_id,
            implementer_session_id=implementer_session_id,
        )
        if staged["status"] == "staged":
            review_result = dict(review(staged))
            self._operations.review_release(
                staged["id"],
                reviewer_session_id=reviewer_session_id,
                disposition=str(review_result.get("disposition", "rejected")),  # type: ignore[arg-type]
                findings=dict(review_result.get("findings", {})),
                evidence_ids=[str(value) for value in review_result.get("evidence_ids", [])],
            )
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (staged["id"],))
        if release["status"] == "accepted":
            release = self._operations.activate_release(release["id"], release_root=release_root)
        if release["verification_status"] != "passed":
            verification = self._operations.verify_release(
                release["id"],
                command=[str(value) for value in repair_result["health_command"]],
                release_root=release_root,
                verification_type="fresh_process",
            )
            if verification["disposition"] != "passed":
                raise RuntimeError("Factory repair release failed installed verification")
        self._operations.record_repair(
            recovery["id"],
            repair_revision=str(repair_result["source_revision"]),
            evidence_ids=[str(value) for value in repair_result["repair_evidence_ids"]],
            release_id=release["id"],
        )
        wake_payload = {
            "mission_id": target_mission_id,
            "recovery_id": recovery["id"],
            "repair_revision": repair_result["source_revision"],
            "requested_range_root": requested_range_root,
            "tracker_currentness_root": tracker_currentness_root,
        }
        token = self._operations.reserve_exact_once_resume(
            recovery["id"],
            requested_range_root=requested_range_root,
            tracker_currentness_root=tracker_currentness_root,
            wake_payload=wake_payload,
        )
        wake_effect = self.governance.claim_effect(
            mission_id=target_mission_id,
            effect_type="resume_target_mission",
            target_type="mission",
            target_id=target_mission_id,
            idempotency_key=token["resume_key"],
            request=wake_payload,
            probe_spec={"kind": "mission_resumption", "recovery_id": recovery["id"]},
        )
        if wake_effect["status"] not in {"succeeded", "observed"}:
            self.governance.start_effect(
                wake_effect["id"],
                lease_owner=recovery["id"],
                lease_expires_at="9999-12-31T23:59:59Z",
            )
            wake_result = dict(wake_target(wake_payload))
            self.governance.observe_effect(
                wake_effect["id"],
                provider_reference=str(wake_result.get("provider_reference", token["id"])),
                observed_result=wake_result,
            )
            self.governance.complete_effect(wake_effect["id"], succeeded=True)
        self._operations.mark_resume_sent(token["id"])
        verification_result = dict(verify_target(wake_payload))
        resolved = self._operations.verify_recovery(
            recovery["id"],
            target_resumed=bool(verification_result.get("target_resumed")),
            evidence_ids=[str(value) for value in verification_result.get("evidence_ids", [])],
        )
        return {
            "recovery": resolved,
            "release": self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?", (release["id"],)
            ),
            "resume_token": self.store.one(
                "SELECT * FROM recovery_resume_tokens_v2 WHERE id=?", (token["id"],)
            ),
            "wake_effect": self.store.one(
                "SELECT * FROM external_effect_intents_v2 WHERE id=?", (wake_effect["id"],)
            ),
            "verification": verification_result,
        }


class ReleaseRefreshCoordinator:
    """Refresh compatible active agents at explicit safe boundaries."""

    def __init__(
        self,
        store: Store,
        *,
        operations: OperationsService | None = None,
        governance: GovernanceService | None = None,
    ):
        self.store = store
        self._operations = operations or OperationsService(store)
        self.governance = governance or GovernanceService(store)

    def refresh(
        self,
        release_id: str,
        *,
        agents: Sequence[Mapping[str, Any]],
        refresh_agent: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        plans = self._operations.plan_agent_refresh(release_id, agents)
        results: list[dict[str, Any]] = []
        for plan in plans:
            if plan["status"] == "refreshed":
                results.append(plan)
                continue
            agent = next(item for item in agents if str(item["id"]) == plan["agent_session_id"])
            if not bool(agent.get("at_safe_boundary", False)):
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE release_agent_refreshes_v2
                           SET status='deferred',updated_at=? WHERE id=?""",
                        (plan["updated_at"], plan["id"]),
                    )
                results.append(
                    self.store.one(
                        "SELECT * FROM release_agent_refreshes_v2 WHERE id=?", (plan["id"],)
                    )
                )
                continue
            effect = self.governance.claim_effect(
                effect_type="refresh_agent_runtime",
                target_type="agent_session",
                target_id=plan["agent_session_id"],
                idempotency_key=f"refresh:{release_id}:{plan['agent_session_id']}",
                request={
                    "release_id": release_id,
                    "target_revision": plan["target_revision"],
                    "boundary": plan["boundary_type"],
                },
                probe_spec={"kind": "agent_runtime_revision"},
            )
            if effect["status"] != "succeeded":
                self.governance.start_effect(
                    effect["id"],
                    lease_owner=release_id,
                    lease_expires_at="9999-12-31T23:59:59Z",
                )
                observed = dict(refresh_agent(plan))
                self.governance.observe_effect(
                    effect["id"],
                    provider_reference=str(
                        observed.get("provider_reference", plan["agent_session_id"])
                    ),
                    observed_result=observed,
                )
                self.governance.complete_effect(
                    effect["id"], succeeded=bool(observed.get("refreshed"))
                )
            effect = self.store.one(
                "SELECT * FROM external_effect_intents_v2 WHERE id=?", (effect["id"],)
            )
            status = "refreshed" if effect["status"] == "succeeded" else "failed"
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE release_agent_refreshes_v2
                       SET status=?,evidence_ids_json=?,updated_at=? WHERE id=?""",
                    (
                        status,
                        json.dumps([effect["id"]], separators=(",", ":")),
                        plan["updated_at"],
                        plan["id"],
                    ),
                )
            results.append(
                self.store.one("SELECT * FROM release_agent_refreshes_v2 WHERE id=?", (plan["id"],))
            )
        return results
