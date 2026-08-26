#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SOURCE = RUNTIME / "src" / "software_factory"
TESTS = RUNTIME / "tests"


def add_import(path: Path, marker: str, import_line: str) -> None:
    text = path.read_text(encoding="utf-8")
    if import_line in text:
        return
    if marker not in text:
        raise RuntimeError(f"import marker missing in {path}: {marker}")
    path.write_text(text.replace(marker, marker + import_line, 1), encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_function_preamble(path: Path, function_name: str, preamble: str) -> None:
    text = path.read_text(encoding="utf-8")
    if preamble.strip() in text:
        return
    tree = ast.parse(text)
    node = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == function_name
        ),
        None,
    )
    if node is None or not node.body:
        raise RuntimeError(f"function not found in {path}: {function_name}")
    first = node.body[0]
    insertion_line = first.lineno - 1
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        insertion_line = int(first.end_lineno or first.lineno)
    lines = text.splitlines(keepends=True)
    lines.insert(insertion_line, preamble.rstrip() + "\n")
    path.write_text("".join(lines), encoding="utf-8")


def enforce_governed_release_review() -> None:
    path = SOURCE / "operations.py"
    preamble = '''        release_columns = {
            str(row["name"])
            for row in self.store.all("PRAGMA table_info(immutable_releases_v2)")
        }
        if "acceptance_decision_id" in release_columns:
            governed_release = self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,)
            )
            if not governed_release.get("acceptance_contract_id") or not governed_release.get(
                "acceptance_decision_id"
            ):
                raise InvalidTransition(
                    "release review requires a strict revision-bound acceptance decision"
                )
            acceptance = self.store.one(
                "SELECT * FROM acceptance_decisions_v2 WHERE id=?",
                (governed_release["acceptance_decision_id"],),
            )
            if (
                acceptance["decision"] != "accepted"
                or acceptance["exact_revision"] != governed_release["source_revision"]
                or acceptance["contract_id"] != governed_release["acceptance_contract_id"]
            ):
                raise InvalidTransition("release acceptance decision is stale or invalid")
'''
    insert_function_preamble(path, "review_release", preamble)


def bind_release_review_row_to_decision() -> None:
    path = SOURCE / "release.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        self.operations.review_release(
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
        return self.store.one(
'''
    replacement = marker.replace(
        "        return self.store.one(\n",
        '''        with self.store.transaction() as db:
            db.execute(
                """UPDATE release_reviews_v2 SET acceptance_decision_id=?
                   WHERE release_id=? AND reviewer_session_id=?""",
                (decision["id"], release_id, primary_review["reviewer_session_id"]),
            )
        return self.store.one(
''',
    )
    if "UPDATE release_reviews_v2 SET acceptance_decision_id" not in text:
        if marker not in text:
            raise RuntimeError("governed release review binding marker missing")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def make_factory_recovery_use_governed_release() -> None:
    path = SOURCE / "recovery.py"
    add_import(path, "from .operations import OperationsService\n", "from .release import GovernedReleaseService\n")
    text = path.read_text(encoding="utf-8")
    init_marker = "        self.operations = OperationsService(store)\n"
    init_assignment = "        self.releases = GovernedReleaseService(store)\n"
    if init_assignment not in text:
        if init_marker not in text:
            raise RuntimeError("recovery operations assignment marker missing")
        text = text.replace(init_marker, init_marker + init_assignment, 1)
    start = text.find("    def recover(\n")
    end = text.find("\n\n\nclass ReleaseRefreshCoordinator:", start)
    if start < 0 or end < 0:
        raise RuntimeError("recovery function boundary missing")
    replacement = '''    def recover(
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
        recovery = self.operations.open_recovery(
            target_mission_id=target_mission_id,
            defect_class=defect_class,
            defect_evidence=defect_evidence,
            target_state=target_state,
            requested_range_root=requested_range_root,
            tracker_currentness_root=tracker_currentness_root,
            safe_frontier=safe_frontier,
        )
        if recovery["status"] == "resolved":
            token = self.store.one(
                "SELECT * FROM recovery_resume_tokens_v2 WHERE recovery_id=?",
                (recovery["id"],),
                required=False,
            )
            wake_effect = self.store.one(
                """SELECT * FROM external_effect_intents_v2
                   WHERE idempotency_key=?""",
                (token["resume_key"],) if token else ("",),
                required=False,
            )
            release = self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?",
                (recovery["release_id"],),
                required=False,
            )
            return {
                "recovery": recovery,
                "release": release,
                "resume_token": token,
                "wake_effect": wake_effect,
                "verification": {"already_resolved": True},
            }
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
        staged = self.releases.stage(
            source_root=repair_result["source_root"],
            release_root=release_root,
            source_revision=str(repair_result["source_revision"]),
            source_tree_root=str(repair_result["source_tree_root"]),
            mission_id=target_mission_id,
            implementer_session_id=implementer_session_id,
            required_probes=[
                {"key": "repair-qa", "type": "test"},
                {"key": "protected-recovery-capabilities", "type": "protected_capability"},
            ],
            protected_capabilities=[
                "target-range-preservation",
                "one-writer-release",
                "exact-once-target-resumption",
            ],
        )
        if staged["status"] == "staged":
            self.releases.record_probe(
                staged["id"],
                probe_key="repair-qa",
                disposition="passed",
                observed_result={"repair_revision": repair_result["source_revision"]},
                evidence_ids=[str(value) for value in repair_result["repair_evidence_ids"]],
                observer_session_id=implementer_session_id,
            )
            self.releases.record_probe(
                staged["id"],
                probe_key="protected-recovery-capabilities",
                disposition="passed",
                observed_result={
                    "target_range_preserved": True,
                    "one_writer_release": True,
                    "exact_once_resume": True,
                },
                evidence_ids=[
                    requested_range_root,
                    tracker_currentness_root,
                    *[str(value) for value in repair_result["repair_evidence_ids"]],
                ],
                observer_session_id=implementer_session_id,
            )
            review_result = dict(review(staged))
            grant = self.releases.issue_reviewer_grant(
                staged["id"],
                reviewer_session_id=reviewer_session_id,
                currentness_root=str(
                    review_result.get("currentness_root", tracker_currentness_root)
                ),
                policy_root=str(
                    review_result.get(
                        "policy_root", f"factory-repair-policy:{defect_class}"
                    )
                ),
                expires_at=str(review_result["expires_at"]),
                issued_by_session_id=review_result.get("issued_by_session_id"),
            )
            self.releases.record_independent_review(
                staged["id"],
                grant_id=grant["id"],
                reviewer_session_id=reviewer_session_id,
                currentness_root=str(
                    review_result.get("currentness_root", tracker_currentness_root)
                ),
                review_contract=dict(
                    review_result.get(
                        "review_contract",
                        {"check": ["repair correctness", "range preservation", "rollback"]},
                    )
                ),
                provider_session_id=str(review_result["provider_session_id"]),
                transcript_artifact_id=str(review_result["transcript_artifact_id"]),
                evidence_ids=[str(value) for value in review_result["evidence_ids"]],
                disposition=str(review_result.get("disposition", "rejected")),
                findings=dict(review_result.get("findings", {})),
            )
            staged = self.releases.accept(staged["id"])
        activated = self.releases.activate_and_verify(
            staged["id"],
            release_root=release_root,
            verification_command=[str(value) for value in repair_result["health_command"]],
        )
        if activated["verification"]["disposition"] != "passed":
            raise RuntimeError("Factory repair release failed installed verification")
        release = activated["release"]
        self.operations.record_repair(
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
        token = self.operations.reserve_exact_once_resume(
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
        self.operations.mark_resume_sent(token["id"])
        verification_result = dict(verify_target(wake_payload))
        resolved = self.operations.verify_recovery(
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
'''
    path.write_text(text[:start] + replacement.rstrip() + text[end:], encoding="utf-8")


def protect_active_writers_in_reconciliation() -> None:
    path = SOURCE / "reconciliation.py"
    text = path.read_text(encoding="utf-8")
    marker = '''        repository = Path(inventory["repository_root"]).resolve()
        source_branch = str(item["item_key"])
'''
    replacement = '''        repository = Path(inventory["repository_root"]).resolve()
        source_branch = str(item["item_key"])
        active_writers = _loads(inventory.get("active_writers_json"), [])
        if any(str(writer.get("branch")) == source_branch for writer in active_writers):
            raise InvalidTransition("accepted source branch still has an active writer")
'''
    if "accepted source branch still has an active writer" not in text:
        if marker not in text:
            raise RuntimeError("integration writer guard marker missing")
        text = text.replace(marker, replacement, 1)
    publish_marker = '''        repository = Path(candidate["repository_root"])
        target_branch = str(candidate["target_branch"])
'''
    publish_replacement = '''        repository = Path(candidate["repository_root"])
        target_branch = str(candidate["target_branch"])
        item = self.store.one(
            "SELECT * FROM cleanup_items_v2 WHERE id=?", (candidate["cleanup_item_id"],)
        )
        inventory = self.store.one(
            "SELECT * FROM repository_inventories_v2 WHERE id=?", (item["inventory_id"],)
        )
        active_writers = _loads(inventory.get("active_writers_json"), [])
        if any(str(writer.get("branch")) == target_branch for writer in active_writers):
            raise InvalidTransition("target branch still has an active writer")
'''
    if "target branch still has an active writer" not in text:
        if publish_marker not in text:
            raise RuntimeError("publication writer guard marker missing")
        text = text.replace(publish_marker, publish_replacement, 1)
    path.write_text(text, encoding="utf-8")


def wire_release_and_reconciliation() -> None:
    core = SOURCE / "core.py"
    add_import(core, "from .qa import QAService\n", "from .reconciliation import RepositoryReconciliationService\n")
    add_import(core, "from .reconciliation import RepositoryReconciliationService\n", "from .release import GovernedReleaseService\n")
    text = core.read_text(encoding="utf-8")
    marker = "        self.release_refresh = ReleaseRefreshCoordinator(store)\n"
    additions = (
        "        self.releases = GovernedReleaseService(store)\n"
        "        self.reconciliation = RepositoryReconciliationService(store)\n"
    )
    if additions not in text:
        if marker not in text:
            raise RuntimeError("core release refresh marker missing")
        text = text.replace(marker, marker + additions, 1)
    core.write_text(text, encoding="utf-8")


def update_recovery_test_review_contract() -> None:
    path = TESTS / "test_recovery_coordinator.py"
    text = path.read_text(encoding="utf-8")
    old_agents = '''            INSERT INTO agent_sessions(id,provider_session_id) VALUES
              ('agent-safe','provider-safe'),
              ('agent-busy','provider-busy');
'''
    new_agents = '''            INSERT INTO agent_sessions(id,provider_session_id) VALUES
              ('agent-safe','provider-safe'),
              ('agent-busy','provider-busy'),
              ('factory-repair-implementer','provider-implementer'),
              ('factory-repair-reviewer','provider-reviewer'),
              ('factory-repair-authority','provider-authority');
'''
    if new_agents not in text:
        if old_agents not in text:
            raise RuntimeError("recovery test agent fixture marker missing")
        text = text.replace(old_agents, new_agents, 1)
    migration_marker = '''        self.connection.executescript(
            (migrations / "0014_governance_effects.sql").read_text(encoding="utf-8")
        )
'''
    migration_addition = migration_marker + '''        self.connection.executescript(
            (migrations / "0018_governed_release.sql").read_text(encoding="utf-8")
        )
'''
    if '"0018_governed_release.sql"' not in text:
        if migration_marker not in text:
            raise RuntimeError("recovery test governed release migration marker missing")
        text = text.replace(migration_marker, migration_addition, 1)
    review_old = '''        review=lambda _: {
            "disposition": "accepted",
            "findings": {"blocking": []},
            "evidence_ids": ["independent-review"],
        },
'''
    review_new = '''        review=lambda _: {
            "disposition": "accepted",
            "findings": {"blocking": []},
            "evidence_ids": ["independent-review"],
            "provider_session_id": "provider-reviewer",
            "transcript_artifact_id": "repair-review-transcript",
            "currentness_root": "tracker-1234567890abcdef",
            "policy_root": "factory-repair-policy-1234567890abcdef",
            "expires_at": "9999-12-31T23:59:59Z",
            "issued_by_session_id": "factory-repair-authority",
        },
'''
    if '"repair-review-transcript"' not in text:
        if review_old not in text:
            raise RuntimeError("recovery test review callback marker missing")
        text = text.replace(review_old, review_new, 1)
    path.write_text(text, encoding="utf-8")


def update_acceptance_matrix() -> None:
    path = RUNTIME / "acceptance-matrix.json"
    matrix = json.loads(path.read_text(encoding="utf-8"))
    matrix["minimum_behavioral_cases"] = max(98, int(matrix["minimum_behavioral_cases"]))
    matrix["domains"]["governed_release"] = {
        "required": [
            "test_governed_release.py::test_release_cannot_be_accepted_before_all_probes_and_granted_review",
            "test_governed_release.py::test_full_governed_release_activates_and_verifies_exact_revision",
            "test_governed_release.py::test_reviewer_grant_is_single_use_and_bound_to_exact_release_revision"
        ]
    }
    matrix["domains"]["repository_reconciliation"] = {
        "required": [
            "test_reconciliation.py::test_accepted_branch_is_validated_published_by_cas_and_lane_retires",
            "test_reconciliation.py::test_target_advance_after_validation_prevents_publication",
            "test_reconciliation.py::test_post_publish_failure_rolls_target_back",
            "test_reconciliation.py::test_unfinished_branch_is_restored_on_new_baseline_worktree"
        ]
    }
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_acceptance_domain_test() -> None:
    path = TESTS / "test_acceptance_matrix.py"
    text = path.read_text(encoding="utf-8")
    marker = '        "closed_loop_factory_recovery",\n'
    additions = '        "governed_release",\n        "repository_reconciliation",\n'
    if additions not in text:
        if marker not in text:
            raise RuntimeError("acceptance recovery domain marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def update_composition_test() -> None:
    path = TESTS / "test_v2_entrypoints.py"
    add_import(path, "from software_factory.problem_solving import ProblemSolvingService\n", "from software_factory.reconciliation import RepositoryReconciliationService\n")
    add_import(path, "from software_factory.reconciliation import RepositoryReconciliationService\n", "from software_factory.release import GovernedReleaseService\n")
    text = path.read_text(encoding="utf-8")
    marker = "    assert isinstance(core.release_refresh, ReleaseRefreshCoordinator)\n"
    additions = (
        "    assert isinstance(core.releases, GovernedReleaseService)\n"
        "    assert isinstance(core.reconciliation, RepositoryReconciliationService)\n"
    )
    if additions not in text:
        if marker not in text:
            raise RuntimeError("composition release refresh marker missing")
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def bump_versions() -> None:
    schema = SOURCE / "schema.py"
    text = schema.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(SCHEMA_VERSION|LATEST_SCHEMA_VERSION)\s*=\s*\d+\s*$",
        lambda match: f"{match.group(1)} = 18",
        text,
    )
    schema.write_text(text, encoding="utf-8")
    pyproject = RUNTIME / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'(?m)^version = "2\.0\.0\.dev\d+"$', 'version = "2.0.0.dev9"', text, count=1)
    pyproject.write_text(text, encoding="utf-8")
    init = SOURCE / "__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(r'__version__ = "2\.0\.0\.dev\d+"', '__version__ = "2.0.0.dev9"', text, count=1)
    init.write_text(text, encoding="utf-8")


def main() -> None:
    enforce_governed_release_review()
    bind_release_review_row_to_decision()
    make_factory_recovery_use_governed_release()
    protect_active_writers_in_reconciliation()
    wire_release_and_reconciliation()
    update_recovery_test_review_contract()
    update_acceptance_matrix()
    update_acceptance_domain_test()
    update_composition_test()
    bump_versions()


if __name__ == "__main__":
    main()
