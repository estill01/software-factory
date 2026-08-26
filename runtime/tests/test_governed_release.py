from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from software_factory.errors import InvalidTransition
from software_factory.release import GovernedReleaseService


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
            INSERT INTO missions(id) VALUES('mission-1');
            INSERT INTO agent_sessions(id,provider_session_id) VALUES
              ('implementer','provider-implementer'),
              ('reviewer','provider-reviewer'),
              ('observer','provider-observer'),
              ('authority','provider-authority');
            """
        )
        migrations = Path(__file__).parents[1] / "src" / "software_factory" / "migrations"
        for name in (
            "0011_release_recovery_cleanup.sql",
            "0012_operability_runtime.sql",
            "0014_governance_effects.sql",
            "0017_reconciliation_runtime.sql",
            "0018_governed_release.sql",
            "0024_delivery_reconciliation.sql",
        ):
            self.connection.executescript((migrations / name).read_text(encoding="utf-8"))

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


def future() -> str:
    return (dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")


def stage(service: GovernedReleaseService, tmp_path: Path) -> tuple[dict[str, Any], Path]:
    source = tmp_path / "source"
    source.mkdir()
    (source / "health.py").write_text("print('HEALTHY')\n", encoding="utf-8")
    release_root = tmp_path / "releases"
    release = service.stage(
        source_root=source,
        release_root=release_root,
        source_revision="revision-1",
        source_tree_root="tree-1234567890abcdef",
        mission_id="mission-1",
        implementer_session_id="implementer",
        required_probes=[
            {"key": "runtime-tests", "type": "test"},
            {"key": "protected-capabilities", "type": "protected_capability"},
            {"key": "clean-install", "type": "installed"},
        ],
        protected_capabilities=["mission-continuation", "release-rollback"],
    )
    return release, release_root


def test_release_cannot_be_accepted_before_all_probes_and_granted_review(
    tmp_path: Path,
) -> None:
    service = GovernedReleaseService(TestStore())  # type: ignore[arg-type]
    release, _ = stage(service, tmp_path)
    service.record_probe(
        release["id"],
        probe_key="runtime-tests",
        disposition="passed",
        observed_result={"exit_code": 0, "tests": 100},
        evidence_ids=["test-log"],
        observer_session_id="observer",
    )
    with pytest.raises(InvalidTransition, match="incomplete"):
        service.accept(release["id"])


def test_accepted_physical_review_without_governed_decision_cannot_activate(
    tmp_path: Path,
) -> None:
    service = GovernedReleaseService(TestStore())  # type: ignore[arg-type]
    release, release_root = stage(service, tmp_path)
    service._operations.review_release(
        release["id"],
        reviewer_session_id="arbitrary-reviewer-string",
        disposition="accepted",
        findings={"claimed": "accepted"},
        evidence_ids=["unbound-review-string"],
    )
    accepted_without_decision = service.store.one(
        "SELECT * FROM immutable_releases_v2 WHERE id=?", (release["id"],)
    )
    assert accepted_without_decision["status"] == "accepted"
    assert accepted_without_decision["acceptance_decision_id"] is None
    with pytest.raises(InvalidTransition, match="strict acceptance decision"):
        service.activate(release["id"], release_root=release_root)
    with pytest.raises(InvalidTransition, match="strict acceptance decision"):
        service.activate_and_verify(
            release["id"],
            release_root=release_root,
            verification_command=[sys.executable, "health.py"],
        )
    assert not (release_root / "active-release.json").exists()


def test_full_governed_release_activates_and_verifies_exact_revision(
    tmp_path: Path,
) -> None:
    service = GovernedReleaseService(TestStore())  # type: ignore[arg-type]
    release, release_root = stage(service, tmp_path)
    for key, observed in (
        ("runtime-tests", {"exit_code": 0, "tests": 100}),
        ("protected-capabilities", {"mission-continuation": True, "release-rollback": True}),
        ("clean-install", {"wheel_installed": True, "entrypoints": "healthy"}),
    ):
        service.record_probe(
            release["id"],
            probe_key=key,
            disposition="passed",
            observed_result=observed,
            evidence_ids=[f"{key}-evidence"],
            observer_session_id="observer",
        )
    grant = service.issue_reviewer_grant(
        release["id"],
        reviewer_session_id="reviewer",
        currentness_root="current-1234567890abcdef",
        policy_root="release-policy-1234567890abcdef",
        expires_at=future(),
        issued_by_session_id="authority",
    )
    review = service.record_independent_review(
        release["id"],
        grant_id=grant["id"],
        reviewer_session_id="reviewer",
        currentness_root="current-1234567890abcdef",
        review_contract={
            "check": [
                "manifest",
                "behavioral evidence",
                "protected capabilities",
                "rollback",
            ]
        },
        provider_session_id="provider-reviewer",
        transcript_artifact_id="review-transcript-artifact",
        evidence_ids=["review-transcript-artifact", "manifest-review"],
        disposition="accepted",
        findings={"blocking": [], "advisory": []},
    )
    assert review["disposition"] == "accepted"
    accepted = service.accept(release["id"])
    assert accepted["status"] == "accepted"
    assert accepted["acceptance_contract_id"]
    assert accepted["acceptance_decision_id"]
    activated = service.activate_and_verify(
        release["id"],
        release_root=release_root,
        verification_command=[sys.executable, "health.py"],
    )
    assert activated["release"]["status"] == "active"
    assert activated["release"]["verification_status"] == "passed"
    assert activated["verification"]["disposition"] == "passed"


def test_reviewer_grant_is_single_use_and_bound_to_exact_release_revision(
    tmp_path: Path,
) -> None:
    service = GovernedReleaseService(TestStore())  # type: ignore[arg-type]
    release, _ = stage(service, tmp_path)
    grant = service.issue_reviewer_grant(
        release["id"],
        reviewer_session_id="reviewer",
        currentness_root="current-1234567890abcdef",
        policy_root="release-policy-1234567890abcdef",
        expires_at=future(),
    )
    service.record_independent_review(
        release["id"],
        grant_id=grant["id"],
        reviewer_session_id="reviewer",
        currentness_root="current-1234567890abcdef",
        review_contract={"check": ["manifest"]},
        provider_session_id="provider-reviewer",
        transcript_artifact_id="review-1",
        evidence_ids=["review-1"],
        disposition="accepted",
        findings={},
    )
    with pytest.raises(InvalidTransition, match="not active"):
        service.record_independent_review(
            release["id"],
            grant_id=grant["id"],
            reviewer_session_id="reviewer",
            currentness_root="current-1234567890abcdef",
            review_contract={"check": ["manifest"]},
            provider_session_id="provider-reviewer",
            transcript_artifact_id="review-2",
            evidence_ids=["review-2"],
            disposition="accepted",
            findings={},
        )
