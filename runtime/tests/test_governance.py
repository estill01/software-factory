from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.errors import InvalidTransition
from software_factory.governance import GovernanceService


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE missions(id TEXT PRIMARY KEY);
            CREATE TABLE agent_sessions(
                id TEXT PRIMARY KEY,
                provider_session_id TEXT
            );
            CREATE TABLE notifications_v2(
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL
            );
            CREATE TABLE reports_v2(
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT
            );
            INSERT INTO missions(id) VALUES('mission-1');
            INSERT INTO agent_sessions(id,provider_session_id) VALUES
              ('implementer','provider-implementer'),
              ('reviewer','provider-reviewer'),
              ('reviewer-2','provider-reviewer-2'),
              ('authority','provider-authority');
            """
        )
        migration = (
            Path(__file__).parents[1]
            / "src"
            / "software_factory"
            / "migrations"
            / "0014_governance_effects.sql"
        )
        self.connection.executescript(migration.read_text(encoding="utf-8"))

    @contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        self.connection.execute(f"BEGIN {mode}")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        if row is None:
            if required:
                raise LookupError(sql)
            return None
        return dict(row)

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, parameters).fetchall()]


def service() -> GovernanceService:
    return GovernanceService(TestStore())  # type: ignore[arg-type]


def future(hours: int = 1) -> str:
    return (dt.datetime.now(dt.UTC) + dt.timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def contract(governance: GovernanceService, revision: str = "revision-1") -> dict[str, Any]:
    return governance.create_acceptance_contract(
        mission_id="mission-1",
        target_type="candidate",
        target_id="candidate-1",
        target_revision=revision,
        required_probes=[
            {"key": "focused-tests", "type": "test"},
            {"key": "integration", "type": "integration"},
            {"key": "protected-capability", "type": "protected_capability"},
        ],
        protected_capabilities=["mission-continuation"],
    )


def grant(governance: GovernanceService, revision: str = "revision-1") -> dict[str, Any]:
    return governance.issue_role_grant(
        mission_id="mission-1",
        grantee_session_id="reviewer",
        role="independent_reviewer",
        target_type="candidate",
        target_id="candidate-1",
        target_revision=revision,
        policy_root="policy-1234567890abcdef",
        currentness_root="current-1234567890abcdef",
        scope={"paths": ["runtime"], "effects": ["review"]},
        issued_by_session_id="authority",
        expires_at=future(),
    )


def accepted_review(
    governance: GovernanceService,
    contract_id: str,
    grant_id: str,
    revision: str = "revision-1",
) -> dict[str, Any]:
    return governance.record_independent_review(
        contract_id,
        grant_id=grant_id,
        reviewer_session_id="reviewer",
        implementer_session_id="implementer",
        exact_revision=revision,
        currentness_root="current-1234567890abcdef",
        review_contract={"check": ["correctness", "scope", "regressions"]},
        provider_session_id="provider-reviewer",
        transcript_artifact_id="review-transcript",
        evidence_ids=["review-output", "candidate-diff"],
        disposition="accepted",
        findings={"blocking": []},
    )


def pass_probes(
    governance: GovernanceService, contract_id: str, revision: str = "revision-1"
) -> None:
    for key, probe_type in (
        ("focused-tests", "test"),
        ("integration", "integration"),
        ("protected-capability", "protected_capability"),
    ):
        governance.record_probe_result(
            contract_id,
            probe_key=key,
            exact_revision=revision,
            disposition="passed",
            observed_result={"probe_type": probe_type, "observed": True},
            evidence_ids=[f"{key}-evidence"],
            observer_session_id="reviewer-2",
        )


def test_caller_asserted_reviewer_role_without_grant_is_rejected() -> None:
    governance = service()
    acceptance = contract(governance)
    with pytest.raises(LookupError):
        accepted_review(governance, acceptance["id"], "nonexistent-grant")


def test_delegated_role_grant_cannot_widen_scope_or_outlive_parent() -> None:
    governance = service()
    parent = governance.issue_role_grant(
        mission_id="mission-1",
        grantee_session_id="reviewer",
        role="independent_reviewer",
        target_type="candidate",
        target_id="candidate-1",
        target_revision="revision-1",
        policy_root="policy-1234567890abcdef",
        currentness_root="current-1234567890abcdef",
        scope={"paths": ["runtime"], "effects": ["review"]},
        expires_at=future(2),
        max_uses=2,
    )
    with pytest.raises(InvalidTransition, match="widens scope"):
        governance.issue_role_grant(
            mission_id="mission-1",
            grantee_session_id="reviewer-2",
            role="independent_reviewer",
            target_type="candidate",
            target_id="candidate-1",
            target_revision="revision-1",
            policy_root="child-policy-1234567890",
            currentness_root="current-1234567890abcdef",
            scope={"paths": ["runtime", "scripts"], "effects": ["review"]},
            expires_at=future(),
            parent_grant_id=parent["id"],
        )


def test_acceptance_contract_fails_closed_without_behavioral_probe() -> None:
    governance = service()
    with pytest.raises(ValueError, match="behavioral probe"):
        governance.create_acceptance_contract(
            mission_id="mission-1",
            target_type="candidate",
            target_id="candidate-1",
            target_revision="revision-1",
            required_probes=[
                {"key": "git-clean", "type": "git_clean"},
                {"key": "semantic-review", "type": "semantic_review"},
            ],
        )


def test_acceptance_requires_all_observed_probes_and_independent_review() -> None:
    governance = service()
    acceptance = contract(governance)
    review_grant = grant(governance)
    accepted_review(governance, acceptance["id"], review_grant["id"])
    governance.record_probe_result(
        acceptance["id"],
        probe_key="focused-tests",
        exact_revision="revision-1",
        disposition="passed",
        observed_result={"exit_code": 0},
        evidence_ids=["test-log"],
    )
    with pytest.raises(InvalidTransition, match="incomplete"):
        governance.decide_acceptance(acceptance["id"], exact_revision="revision-1")
    pass_probes(governance, acceptance["id"])
    decision = governance.decide_acceptance(acceptance["id"], exact_revision="revision-1")
    assert decision["decision"] == "accepted"
    assert decision["evidence_root"]


def test_provider_identity_must_match_granted_reviewer_session() -> None:
    governance = service()
    acceptance = contract(governance)
    review_grant = grant(governance)
    with pytest.raises(InvalidTransition, match="provider identity"):
        governance.record_independent_review(
            acceptance["id"],
            grant_id=review_grant["id"],
            reviewer_session_id="reviewer",
            implementer_session_id="implementer",
            exact_revision="revision-1",
            currentness_root="current-1234567890abcdef",
            review_contract={"check": ["correctness"]},
            provider_session_id="different-provider",
            transcript_artifact_id="transcript",
            evidence_ids=["review"],
            disposition="accepted",
            findings={},
        )


def test_changed_revision_invalidates_prior_review_and_acceptance() -> None:
    governance = service()
    acceptance = contract(governance)
    review_grant = grant(governance)
    pass_probes(governance, acceptance["id"])
    accepted_review(governance, acceptance["id"], review_grant["id"])
    decision = governance.decide_acceptance(acceptance["id"], exact_revision="revision-1")
    governance.invalidate_target_revision(
        target_type="candidate", target_id="candidate-1", prior_revision="revision-1"
    )
    assert governance.store.one(
        "SELECT status FROM acceptance_contracts_v2 WHERE id=?", (acceptance["id"],)
    ) == {"status": "stale"}
    assert governance.store.one(
        "SELECT decision FROM acceptance_decisions_v2 WHERE id=?", (decision["id"],)
    ) == {"decision": "stale"}


def test_effect_idempotency_collision_and_stale_reconciliation() -> None:
    governance = service()
    effect = governance.claim_effect(
        mission_id="mission-1",
        effect_type="provider_start",
        target_type="execution",
        target_id="execution-1",
        idempotency_key="start-execution-1",
        request={"provider": "codex", "prompt_root": "prompt-1"},
        probe_spec={"kind": "provider_status"},
    )
    duplicate = governance.claim_effect(
        mission_id="mission-1",
        effect_type="provider_start",
        target_type="execution",
        target_id="execution-1",
        idempotency_key="start-execution-1",
        request={"provider": "codex", "prompt_root": "prompt-1"},
        probe_spec={"kind": "provider_status"},
    )
    assert duplicate["id"] == effect["id"]
    with pytest.raises(InvalidTransition, match="collides"):
        governance.claim_effect(
            effect_type="provider_cancel",
            target_type="execution",
            target_id="execution-1",
            idempotency_key="start-execution-1",
            request={"cancel": True},
        )
    governance.start_effect(
        effect["id"],
        lease_owner="controller-1",
        lease_expires_at="2026-01-01T00:00:00Z",
    )
    reconciled = governance.reconcile_stale_effects(
        now="2026-01-01T00:01:00Z",
        probe=lambda _: {
            "disposition": "succeeded",
            "provider_reference": "codex-task-1",
            "observed_status": "running",
        },
    )
    assert reconciled[0]["status"] == "succeeded"
    assert reconciled[0]["provider_reference"] == "codex-task-1"


def test_notification_delivery_propagates_to_linked_report() -> None:
    governance = service()
    with governance.store.transaction() as db:
        db.execute("INSERT INTO notifications_v2(id,status) VALUES('notification-1','delivered')")
        db.execute(
            "INSERT INTO reports_v2(id,status,updated_at) VALUES('report-1','queued','2026-01-01')"
        )
    governance.link_notification_report("notification-1", "report-1")
    governance.propagate_notification_status("notification-1")
    assert governance.store.one("SELECT status FROM reports_v2 WHERE id='report-1'") == {
        "status": "delivered"
    }
