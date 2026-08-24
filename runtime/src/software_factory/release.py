from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .governance import GovernanceService
from .operations import OperationsService
from .store import Store
from .util import utc_now


class GovernedReleaseService:
    """Immutable release lifecycle with revision-bound probes and granted review."""

    def __init__(
        self,
        store: Store,
        *,
        governance: GovernanceService | None = None,
        operations: OperationsService | None = None,
    ):
        self.store = store
        self.governance = governance or GovernanceService(store)
        self.operations = operations or OperationsService(store)

    def stage(
        self,
        *,
        source_root: str | Path,
        release_root: str | Path,
        source_revision: str,
        source_tree_root: str,
        implementer_session_id: str,
        required_probes: Sequence[Mapping[str, Any]],
        protected_capabilities: Sequence[str],
        mission_id: str | None = None,
        minimum_independent_reviews: int = 1,
    ) -> dict[str, Any]:
        release = self.operations.stage_release(
            source_root=source_root,
            release_root=release_root,
            source_revision=source_revision,
            source_tree_root=source_tree_root,
            mission_id=mission_id,
            implementer_session_id=implementer_session_id,
        )
        if release.get("acceptance_contract_id"):
            return release
        contract = self.governance.create_acceptance_contract(
            mission_id=mission_id,
            target_type="release",
            target_id=release["id"],
            target_revision=source_revision,
            required_probes=required_probes,
            protected_capabilities=protected_capabilities,
            minimum_independent_reviews=minimum_independent_reviews,
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE immutable_releases_v2
                   SET acceptance_contract_id=?,updated_at=? WHERE id=?""",
                (contract["id"], utc_now(), release["id"]),
            )
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release["id"],))

    def record_probe(
        self,
        release_id: str,
        *,
        probe_key: str,
        disposition: str,
        observed_result: Mapping[str, Any],
        evidence_ids: Sequence[str],
        command: Sequence[str] | None = None,
        observer_session_id: str | None = None,
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        return self.governance.record_probe_result(
            release["acceptance_contract_id"],
            probe_key=probe_key,
            exact_revision=release["source_revision"],
            disposition=disposition,  # type: ignore[arg-type]
            observed_result=observed_result,
            evidence_ids=evidence_ids,
            command=command,
            observer_session_id=observer_session_id,
        )

    def issue_reviewer_grant(
        self,
        release_id: str,
        *,
        reviewer_session_id: str,
        currentness_root: str,
        policy_root: str,
        expires_at: str,
        issued_by_session_id: str | None = None,
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        return self.governance.issue_role_grant(
            mission_id=release["mission_id"],
            grantee_session_id=reviewer_session_id,
            role="independent_reviewer",
            target_type="release",
            target_id=release_id,
            target_revision=release["source_revision"],
            policy_root=policy_root,
            currentness_root=currentness_root,
            scope={
                "release_id": release_id,
                "manifest_root": release["manifest_root"],
                "effects": ["review"],
            },
            issued_by_session_id=issued_by_session_id,
            expires_at=expires_at,
        )

    def record_independent_review(
        self,
        release_id: str,
        *,
        grant_id: str,
        reviewer_session_id: str,
        currentness_root: str,
        review_contract: Mapping[str, Any],
        provider_session_id: str,
        transcript_artifact_id: str,
        evidence_ids: Sequence[str],
        disposition: str,
        findings: Mapping[str, Any],
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        return self.governance.record_independent_review(
            release["acceptance_contract_id"],
            grant_id=grant_id,
            reviewer_session_id=reviewer_session_id,
            implementer_session_id=release["implementer_session_id"],
            exact_revision=release["source_revision"],
            currentness_root=currentness_root,
            review_contract=review_contract,
            provider_session_id=provider_session_id,
            transcript_artifact_id=transcript_artifact_id,
            evidence_ids=evidence_ids,
            disposition=disposition,  # type: ignore[arg-type]
            findings=findings,
        )

    def accept(self, release_id: str) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        decision = self.governance.decide_acceptance(
            release["acceptance_contract_id"],
            exact_revision=release["source_revision"],
        )
        reviews = self.store.all(
            """SELECT * FROM independent_review_executions_v2
               WHERE contract_id=? AND exact_revision=? AND status='completed'
                 AND disposition='accepted' ORDER BY created_at""",
            (release["acceptance_contract_id"], release["source_revision"]),
        )
        if not reviews:
            raise RuntimeError("accepted release decision has no accepted review execution")
        primary_review = reviews[0]
        with self.store.transaction() as db:
            db.execute(
                """UPDATE immutable_releases_v2
                   SET acceptance_decision_id=?,updated_at=? WHERE id=?""",
                (decision["id"], utc_now(), release_id),
            )
        self.operations.review_release(
            release_id,
            reviewer_session_id=primary_review["reviewer_session_id"],
            disposition="accepted",
            findings={
                "strict_acceptance_decision_id": decision["id"],
                "review_execution_ids": [review["id"] for review in reviews],
            },
            evidence_ids=[
                decision["evidence_root"],
                *[
                    evidence
                    for review in reviews
                    for evidence in __import__("json").loads(review["evidence_ids_json"])
                ],
            ],
        )
        return self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))

    def activate_and_verify(
        self,
        release_id: str,
        *,
        release_root: str | Path,
        verification_command: Sequence[str],
    ) -> dict[str, Any]:
        self.operations.activate_release(release_id, release_root=release_root)
        verification = self.operations.verify_release(
            release_id,
            command=verification_command,
            release_root=release_root,
            verification_type="installed",
        )
        return {
            "release": self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
            ),
            "verification": verification,
        }
