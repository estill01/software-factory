#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "runtime" / "tests"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def govern_release_refresh_fixture() -> None:
    path = TESTS / "test_recovery_coordinator.py"
    text = path.read_text(encoding="utf-8")
    old = '''    staged = recovery.operations.stage_release(
        source_root=source,
        release_root=tmp_path / "releases",
        source_revision="revision-1",
        source_tree_root="tree-1",
        implementer_session_id="implementer",
    )
    recovery.operations.review_release(
        staged["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        findings={"blocking": []},
        evidence_ids=["review"],
    )
    recovery.operations.activate_release(staged["id"], release_root=tmp_path / "releases")
    recovery.operations.verify_release(
        staged["id"],
        command=[sys.executable, "health.py"],
        release_root=tmp_path / "releases",
    )
'''
    new = '''    staged = recovery.releases.stage(
        source_root=source,
        release_root=tmp_path / "releases",
        source_revision="revision-1",
        source_tree_root="tree-1",
        implementer_session_id="factory-repair-implementer",
        required_probes=[
            {"key": "tests", "type": "test"},
            {"key": "protected", "type": "protected_capability"},
        ],
        protected_capabilities=["refresh", "rollback"],
    )
    for key in ("tests", "protected"):
        recovery.releases.record_probe(
            staged["id"],
            probe_key=key,
            disposition="passed",
            observed_result={"passed": True, "key": key},
            evidence_ids=[f"{key}-evidence"],
            observer_session_id="factory-repair-implementer",
        )
    grant = recovery.releases.issue_reviewer_grant(
        staged["id"],
        reviewer_session_id="factory-repair-reviewer",
        currentness_root="refresh-currentness-1234567890",
        policy_root="refresh-policy-1234567890",
        expires_at="9999-12-31T23:59:59Z",
        issued_by_session_id="factory-repair-authority",
    )
    recovery.releases.record_independent_review(
        staged["id"],
        grant_id=grant["id"],
        reviewer_session_id="factory-repair-reviewer",
        currentness_root="refresh-currentness-1234567890",
        review_contract={"check": ["refresh", "rollback"]},
        provider_session_id="provider-reviewer",
        transcript_artifact_id="refresh-review-transcript",
        evidence_ids=["refresh-review-transcript"],
        disposition="accepted",
        findings={"blocking": []},
    )
    recovery.releases.accept(staged["id"])
    recovery.releases.activate_and_verify(
        staged["id"],
        release_root=tmp_path / "releases",
        verification_command=[sys.executable, "health.py"],
    )
'''
    if "refresh-review-transcript" not in text:
        replace_once(path, old, new)


def add_low_level_release_bypass_regression() -> None:
    path = TESTS / "test_governed_release.py"
    text = path.read_text(encoding="utf-8")
    if "test_low_level_release_review_fails_closed" in text:
        return
    addition = '''

def test_low_level_release_review_fails_closed_when_governance_schema_is_installed(
    tmp_path: Path,
) -> None:
    service = GovernedReleaseService(TestStore())  # type: ignore[arg-type]
    source = tmp_path / "source-low-level"
    source.mkdir()
    (source / "health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    release = service.operations.stage_release(
        source_root=source,
        release_root=tmp_path / "releases-low-level",
        source_revision="revision-low-level",
        source_tree_root="tree-low-level-1234567890",
        implementer_session_id="implementer",
    )
    with pytest.raises(InvalidTransition, match="strict revision-bound"):
        service.operations.review_release(
            release["id"],
            reviewer_session_id="reviewer",
            disposition="accepted",
            findings={"blocking": []},
            evidence_ids=["review-label-only"],
        )
'''
    path.write_text(text.rstrip() + addition + "\n", encoding="utf-8")


def expand_real_database_expected_tables() -> None:
    path = TESTS / "test_advanced_integration.py"
    text = path.read_text(encoding="utf-8")
    marker = '    "cutover_effects_v2",\n'
    additions = '''    "role_grants_v2",
    "acceptance_contracts_v2",
    "external_effect_intents_v2",
    "problem_solving_cycles_v2",
    "strategy_candidates_v2",
    "strategy_attempts_v2",
    "integration_candidates_v2",
    "restart_workspaces_v2",
    "acceptance_decisions_v2",
'''
    if '    "problem_solving_cycles_v2",' not in text:
        if marker not in text:
            raise RuntimeError("advanced expected table marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    govern_release_refresh_fixture()
    add_low_level_release_bypass_regression()
    expand_real_database_expected_tables()


if __name__ == "__main__":
    main()
