from __future__ import annotations

import ast
import copy
import fnmatch
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
BASELINE_PATH = REPOSITORY_ROOT / "docs" / "software-factory-v2-baseline.json"
EXPECTED_SOURCE = {
    "branch": "agent/software-factory-v2-native-refactor",
    "commit": "63bb9f3a69bcb5dba0e4b2fe652dce5af7169ae4",
    "tree": "79d758db7e36aa45a34d0af96b676344321e953b",
    "remote_ref": "origin/agent/software-factory-v2-native-refactor",
    "remote_commit_at_freeze": "63bb9f3a69bcb5dba0e4b2fe652dce5af7169ae4",
}
EXPECTED_MODULE_TREATMENTS = {
    "dashboard/server/src/software_factory_dashboard/app_server.py",
    "runtime/src/software_factory/evolution.py",
    "runtime/src/software_factory/governance.py",
    "runtime/src/software_factory/learning.py",
    "runtime/src/software_factory/problem_solving.py",
    "runtime/src/software_factory/providers.py",
    "runtime/src/software_factory/reflection.py",
    "runtime/src/software_factory/workspaces.py",
}
EXPECTED_AUTHORITY_DOMAINS = {
    "governance-and-acceptance-mutation",
    "mission-and-work-state",
    "provider-process-lifecycle",
    "reflection-hypothesis-and-experiment-semantics",
    "release-recovery-and-cleanup",
    "signal-execution-and-operational-effects",
}
EXPECTED_COMPATIBILITY_ROUTES = {
    "dashboard-codex-app-client",
    "embedded-and-service-runtime",
    "local-semantic-runtime",
    "python-entrypoints",
    "sqlite-migrations",
}
EXPECTED_EVIDENCE_IDS = {
    "pre-v2-runtime-and-skill-trackers",
    "source-plan-commit-b34cdd9",
}
EXPECTED_UTILS_HANDOFF = {
    "completion_commit": "a5659745a7cbcbb002b5f06051f6ed9826f721a7",
    "completion_tree": "f6b5cd45b6692c98c93bb3f19b2d4f2ddf361ec1",
    "remote_ref": "origin/main",
    "remote_commit_at_verification": "a5659745a7cbcbb002b5f06051f6ed9826f721a7",
    "remote_divergence_at_verification": {"ahead": 0, "behind": 0},
    "tracker_git_blob": "910ef685dfb95f9a6803dee31000072eb40af257",
    "tracker_sha256": "149202d90a6b389ca0204f9ecbe26c5799c4c86f8a18ab26e407cbe802bdfe7a",
    "completed_blocks": "0-16",
    "qualification_matrix_git_blob": "53414e20421716b207b2296b312ededbbb6d8782",
    "qualification_matrix_sha256": "0888bed363b63842c37baa8187c9883cdddff73d936596e497e4e013341cd849",
    "technical_candidate_commit": "2150966402474bb633c01d04eca0a1bc8309d941",
    "technical_qualification_root_sha256": "9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068",
    "release_posture": "no-license-selected/unpublished",
}
EXPECTED_UTILS_ARTIFACTS = {
    "codex-app-server-client": "1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9",
    "embedded-service-contract": "2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d",
    "runtime-manifest": "f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac",
}
ALLOWED_DISPOSITIONS = {"retain", "move", "adapt", "replace", "retire", "evidence-only"}
CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Za-z0-9_]+)",
    re.IGNORECASE,
)
SQL_TABLE_REFERENCE_PATTERN = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
EXPECTED_EFFECTIVE_OWNER_CONTRACT = {
    "schema_version": "software-factory-v2-effective-path-owner/v1",
    "base_rule_cardinality": "exactly-one",
    "override_selector": "exact-module-path",
    "override_cardinality": "zero-or-one",
    "precedence": "module-treatment-overrides-base-rule",
    "result_cardinality": "exactly-one-effective-owner-and-disposition",
}


class BaselineError(AssertionError):
    pass


def _git(*arguments: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout


def _git_bytes(*arguments: str) -> bytes:
    output = _git(*arguments, text=False)
    assert isinstance(output, bytes)
    return output


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _rule_matches(rule: dict[str, Any], path: str) -> bool:
    selectors = [key for key in ("exact", "prefix", "glob") if key in rule]
    if len(selectors) != 1:
        raise BaselineError(f"path rule {rule.get('id')} must have exactly one selector")
    selector = selectors[0]
    if selector == "exact":
        return path in rule[selector]
    if selector == "prefix":
        return path.startswith(rule[selector])
    return fnmatch.fnmatchcase(path, rule[selector])


def _validate_source(baseline: dict[str, Any]) -> None:
    source = baseline["source"]
    for field, expected in EXPECTED_SOURCE.items():
        if source.get(field) != expected:
            raise BaselineError(f"stale source binding: {field}")

    if source.get("worktree_at_freeze") != "clean":
        raise BaselineError("stale source binding: worktree_at_freeze")
    if source.get("remote_divergence_at_freeze") != {"ahead": 0, "behind": 0}:
        raise BaselineError("stale source binding: remote_divergence_at_freeze")
    if source.get("main_integration") != "deferred-until-complete-v2-acceptance":
        raise BaselineError("stale source binding: main_integration")

    commit = source["commit"]
    tree = str(_git("rev-parse", f"{commit}^{{tree}}")).strip()
    if tree != source["tree"]:
        raise BaselineError("stale source binding: tree")

    paths = str(_git("ls-tree", "-r", "--name-only", commit)).splitlines()
    if len(paths) != source["tracked_file_count"]:
        raise BaselineError("stale source binding: tracked file count")

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        raise BaselineError("frozen source is no longer an ancestor of the candidate")

    remote_ref = source["remote_ref"]
    try:
        remote_head = str(_git("rev-parse", remote_ref)).strip()
    except subprocess.CalledProcessError as exc:
        raise BaselineError("stale source binding: remote_ref") from exc
    remote_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source["remote_commit_at_freeze"], remote_head],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    if remote_ancestor.returncode != 0:
        raise BaselineError("stale source binding: remote history")


def _validate_product_frame(baseline: dict[str, Any]) -> None:
    commit = baseline["source"]["commit"]
    frame = baseline["product_frame"]
    for path_key, hash_key in (
        ("tracker", "tracker_sha256"),
        ("architecture_plan", "architecture_plan_sha256"),
        ("canonical_tracker", "canonical_tracker_sha256"),
    ):
        content = _git_bytes("show", f"{commit}:{frame[path_key]}")
        if _sha256(content) != frame[hash_key]:
            raise BaselineError(f"frozen product frame drifted: {frame[path_key]}")

    tracker = _git_bytes("show", f"{commit}:{frame['tracker']}").splitlines(keepends=True)
    for range_key, hash_key in (
        ("frame_line_range", "frame_sha256"),
        ("block_line_range", "block_sha256"),
    ):
        first, last = frame[range_key]
        if _sha256(b"".join(tracker[first - 1 : last])) != frame[hash_key]:
            raise BaselineError(f"frozen tracker slice drifted: {range_key}")


def _validate_path_inventory(baseline: dict[str, Any]) -> None:
    commit = baseline["source"]["commit"]
    paths = str(_git("ls-tree", "-r", "--name-only", commit)).splitlines()
    inventory = baseline["path_inventory"]
    if inventory.get("effective_owner_contract") != EXPECTED_EFFECTIVE_OWNER_CONTRACT:
        raise BaselineError("effective path-owner contract is missing or stale")
    rules = inventory["rules"]
    rule_ids = [rule["id"] for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise BaselineError("duplicate path rule id")

    for rule in rules:
        if rule.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise BaselineError(f"invalid disposition for path rule {rule['id']}")
        if not rule.get("target_owner"):
            raise BaselineError(f"missing target owner for path rule {rule['id']}")

    treatments = inventory["module_treatments"]
    treatment_paths = [item["path"] for item in treatments]
    if len(treatment_paths) != len(set(treatment_paths)):
        raise BaselineError("duplicate module treatment")
    if set(treatment_paths) != EXPECTED_MODULE_TREATMENTS:
        raise BaselineError("module-treatment inventory is incomplete")
    treatment_by_path = {item["path"]: item for item in treatments}
    for treatment in treatments:
        if treatment["path"] not in paths:
            raise BaselineError(f"module treatment path is not frozen: {treatment['path']}")
        if treatment["disposition"] not in ALLOWED_DISPOSITIONS:
            raise BaselineError(f"invalid module treatment: {treatment['path']}")
        if not treatment.get("target_owner") or not treatment.get("removal_condition"):
            raise BaselineError(f"incomplete module treatment: {treatment['path']}")

    for path in paths:
        base_matches = [rule for rule in rules if _rule_matches(rule, path)]
        if len(base_matches) != 1:
            match_ids = [rule["id"] for rule in base_matches]
            raise BaselineError(f"path {path} maps to {len(base_matches)} base owners: {match_ids}")
        effective = treatment_by_path.get(path, base_matches[0])
        if effective.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise BaselineError(f"invalid effective disposition for path {path}")
        if not effective.get("target_owner"):
            raise BaselineError(f"missing effective target owner for path {path}")


def _validate_surface_roots(baseline: dict[str, Any]) -> None:
    commit = baseline["source"]["commit"]
    for surface in baseline["production_surfaces"]:
        path = surface["path"]
        path_output = _git_bytes("ls-tree", "-r", "--name-only", commit, "--", path)
        paths = path_output.splitlines()
        if len(paths) != surface["tracked_files"]:
            raise BaselineError(f"surface file count drifted: {path}")
        if _sha256(path_output) != surface["path_set_sha256"]:
            raise BaselineError(f"surface path set drifted: {path}")
        tree = str(_git("rev-parse", f"{commit}:{path}")).strip()
        if tree != surface["tree"]:
            raise BaselineError(f"surface tree drifted: {path}")

    for root in baseline["configuration_roots"]:
        content = _git_bytes("show", f"{commit}:{root['path']}")
        if _sha256(content) != root["sha256"]:
            raise BaselineError(f"configuration root drifted: {root['path']}")


def _baseline_migration_text(commit: str, migration: str) -> str:
    return str(_git("show", f"{commit}:runtime/src/software_factory/migrations/{migration}"))


def _runtime_table_references(commit: str, python_paths: list[str]) -> set[str]:
    references: set[str] = set()
    for path in python_paths:
        source = str(_git("show", f"{commit}:{path}"))
        for node in ast.walk(ast.parse(source, filename=path)):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr not in {"execute", "executemany", "executescript"}
                or not node.args
            ):
                continue
            argument = node.args[0]
            literals: list[str] = []
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                literals.append(argument.value)
            elif isinstance(argument, ast.JoinedStr):
                literals.extend(
                    value.value
                    for value in argument.values
                    if isinstance(value, ast.Constant) and isinstance(value.value, str)
                )
            for literal in literals:
                references.update(SQL_TABLE_REFERENCE_PATTERN.findall(literal))
    return references


def _validate_table_inventory(baseline: dict[str, Any]) -> None:
    inventory = baseline["migration_inventory"]
    groups = inventory["table_groups"]
    group_ids = [group["id"] for group in groups]
    if len(group_ids) != len(set(group_ids)):
        raise BaselineError("duplicate table group id")

    table_to_group: dict[str, str] = {}
    for group in groups:
        if group["disposition"] not in ALLOWED_DISPOSITIONS or not group.get("target_owner"):
            raise BaselineError(f"incomplete table group: {group['id']}")
        for table in group["tables"]:
            if table in table_to_group:
                raise BaselineError(
                    f"duplicate table authority: {table} in {table_to_group[table]} and {group['id']}"
                )
            table_to_group[table] = group["id"]

    commit = baseline["source"]["commit"]
    migration_root = "runtime/src/software_factory/migrations"
    frozen_migrations = {
        path.rsplit("/", 1)[-1]
        for path in str(
            _git("ls-tree", "-r", "--name-only", commit, "--", migration_root)
        ).splitlines()
        if path.endswith(".sql")
    }
    declared_migrations = set(inventory["active_migration_files"]) | set(
        inventory["defined_not_applied_migration_files"]
    )
    if frozen_migrations != declared_migrations:
        raise BaselineError("migration-file inventory is incomplete")

    schema_source = str(_git("show", f"{commit}:runtime/src/software_factory/schema.py"))
    active_from_code = re.findall(r'Migration\(\d+,\s*"([^"]+\.sql)"\)', schema_source)
    if active_from_code != inventory["active_migration_files"]:
        raise BaselineError("active migration order does not match schema.py")

    defined_tables: set[str] = {"schema_migrations"}
    for migration in sorted(frozen_migrations):
        defined_tables.update(
            CREATE_TABLE_PATTERN.findall(_baseline_migration_text(commit, migration))
        )

    active_group = next(group for group in groups if group["state"] == "active")
    inactive_group = next(group for group in groups if group["state"] == "defined-not-applied")
    missing_group = next(group for group in groups if group["state"] == "referenced-no-definition")
    mapped_defined_tables = set(active_group["tables"]) | set(inactive_group["tables"])
    if defined_tables != mapped_defined_tables:
        raise BaselineError(
            f"defined table inventory mismatch: missing={sorted(defined_tables - mapped_defined_tables)}, "
            f"extra={sorted(mapped_defined_tables - defined_tables)}"
        )

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE schema_migrations("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
            "sha256 TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        for migration in inventory["active_migration_files"]:
            connection.executescript(_baseline_migration_text(commit, migration))
        active_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        connection.close()
    if active_tables != set(active_group["tables"]):
        raise BaselineError("fresh active schema does not match the frozen table map")

    python_paths = [
        path
        for path in str(
            _git(
                "ls-tree",
                "-r",
                "--name-only",
                commit,
                "--",
                "runtime/src/software_factory",
            )
        ).splitlines()
        if path.endswith(".py")
    ]
    referenced_without_definition = _runtime_table_references(commit, python_paths) - defined_tables
    declared_without_definition = set(missing_group["tables"])
    if referenced_without_definition != declared_without_definition:
        raise BaselineError(
            "referenced-without-definition inventory mismatch: "
            f"missing={sorted(referenced_without_definition - declared_without_definition)}, "
            f"extra={sorted(declared_without_definition - referenced_without_definition)}"
        )


def _validate_authorities_and_evidence(baseline: dict[str, Any]) -> None:
    domains = baseline["authority_domains"]
    domain_names = [domain["domain"] for domain in domains]
    if len(domain_names) != len(set(domain_names)):
        raise BaselineError("duplicate authority domain")
    if set(domain_names) != EXPECTED_AUTHORITY_DOMAINS:
        raise BaselineError("authority-domain inventory is incomplete")
    for domain in domains:
        if not isinstance(domain.get("current_authoritative_writer"), str):
            raise BaselineError(f"duplicate or missing current authority: {domain['domain']}")
        if (
            not domain["current_authoritative_writer"]
            or not domain.get("target_owner")
            or domain.get("disposition") not in ALLOWED_DISPOSITIONS
            or not isinstance(domain.get("block"), int)
        ):
            raise BaselineError(f"missing authority owner: {domain['domain']}")
        if domain["current_authoritative_writer"] in domain["duplicate_or_shadow_implementations"]:
            raise BaselineError(f"duplicate active authority: {domain['domain']}")

    route_ids = [route["id"] for route in baseline["compatibility_routes"]]
    if len(route_ids) != len(set(route_ids)):
        raise BaselineError("duplicate compatibility route")
    if set(route_ids) != EXPECTED_COMPATIBILITY_ROUTES:
        raise BaselineError("compatibility-route inventory is incomplete")
    for route in baseline["compatibility_routes"]:
        if (
            not route.get("target_owner")
            or not route.get("removal_condition")
            or route.get("disposition") not in ALLOWED_DISPOSITIONS
            or not isinstance(route.get("cutover_block"), int)
        ):
            raise BaselineError(f"incomplete compatibility route: {route['id']}")

    evidence_rows = baseline["accepted_evidence"]
    evidence_ids = [evidence["id"] for evidence in evidence_rows]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise BaselineError("duplicate accepted evidence")
    if set(evidence_ids) != EXPECTED_EVIDENCE_IDS:
        raise BaselineError("accepted-evidence inventory is incomplete")

    for evidence in evidence_rows:
        if evidence["classification"] != "accepted-input":
            raise BaselineError(f"unsupported evidence classification: {evidence['id']}")
        if evidence["currentness"] != "historical-evidence-not-current-implementation":
            raise BaselineError(f"accepted proof reclassified as current: {evidence['id']}")
        sources = evidence.get("sources")
        if not isinstance(sources, list) or not sources:
            raise BaselineError(f"accepted evidence lacks exact sources: {evidence['id']}")
        source_paths: set[tuple[str, str]] = set()
        for source in sources:
            identity = (source["commit"], source["path"])
            if identity in source_paths:
                raise BaselineError(f"duplicate accepted evidence source: {identity}")
            source_paths.add(identity)
            try:
                blob = str(_git("rev-parse", f"{source['commit']}:{source['path']}")).strip()
                content = _git_bytes("show", f"{source['commit']}:{source['path']}")
            except subprocess.CalledProcessError as exc:
                raise BaselineError(f"accepted evidence source is unavailable: {identity}") from exc
            if blob != source["git_blob"] or _sha256(content) != source["sha256"]:
                raise BaselineError(f"accepted evidence source drifted: {identity}")

    frozen_commit = baseline["source"]["commit"]
    frozen_historical_trackers = {
        path
        for path in str(
            _git("ls-tree", "-r", "--name-only", frozen_commit, "--", "docs")
        ).splitlines()
        if path.endswith("-implementation-tracker.md")
        and path != "docs/software-factory-v2-implementation-tracker.md"
    }
    historical_evidence = next(
        evidence
        for evidence in evidence_rows
        if evidence["id"] == "pre-v2-runtime-and-skill-trackers"
    )
    recorded_historical_trackers = {source["path"] for source in historical_evidence["sources"]}
    if recorded_historical_trackers != frozen_historical_trackers:
        raise BaselineError("historical tracker evidence is incomplete")

    planned_blocks = [item["block"] for item in baseline["changed_test_plan"]]
    if planned_blocks != list(range(1, 13)):
        raise BaselineError("changed-test plan must cover Blocks 1-12 in order")


def _validate_external_inputs(baseline: dict[str, Any]) -> None:
    inputs = {item["distribution"]: item for item in baseline["external_inputs"]}
    if set(inputs) != {"utils", "libRSI"}:
        raise BaselineError("external-input inventory is incomplete")
    utils = inputs["utils"]
    handoff = utils.get("accepted_handoff")
    if not isinstance(handoff, dict):
        raise BaselineError("utils accepted handoff is missing")
    for field, expected in EXPECTED_UTILS_HANDOFF.items():
        if handoff.get(field) != expected:
            raise BaselineError(f"utils accepted handoff is stale: {field}")
    artifacts = handoff.get("artifacts")
    if not isinstance(artifacts, list):
        raise BaselineError("utils accepted artifact inventory is missing")
    artifact_hashes = {item["distribution"]: item["artifact_sha256"] for item in artifacts}
    if artifact_hashes != EXPECTED_UTILS_ARTIFACTS:
        raise BaselineError("utils accepted artifact inventory is stale")
    if "bare registry name/version" not in utils.get("consumption_rule", ""):
        raise BaselineError("utils registry-name collision boundary is missing")

    repository = Path(utils["repository"])
    commit = handoff["completion_commit"]
    commands = {
        "completion_tree": ("rev-parse", f"{commit}^{{tree}}"),
        "tracker_git_blob": ("rev-parse", f"{commit}:docs/tracker.md"),
        "qualification_matrix_git_blob": (
            "rev-parse",
            f"{commit}:tools/qualification_matrix.json",
        ),
    }
    for field, arguments in commands.items():
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() != handoff[field]:
            raise BaselineError(f"utils accepted handoff source drifted: {field}")
    for field, path in (
        ("tracker_sha256", "docs/tracker.md"),
        ("qualification_matrix_sha256", "tools/qualification_matrix.json"),
    ):
        content = subprocess.run(
            ["git", "-C", str(repository), "show", f"{commit}:{path}"],
            check=True,
            capture_output=True,
        ).stdout
        if _sha256(content) != handoff[field]:
            raise BaselineError(f"utils accepted handoff source drifted: {field}")
    remote_head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", handoff["remote_ref"]],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", commit, remote_head],
        check=False,
    ).returncode:
        raise BaselineError("utils accepted handoff is not retained by its remote")


def validate_baseline(baseline: dict[str, Any]) -> None:
    if baseline.get("schema_version") != "software-factory-v2-baseline/v1":
        raise BaselineError("unknown baseline schema")
    _validate_source(baseline)
    _validate_product_frame(baseline)
    _validate_path_inventory(baseline)
    _validate_surface_roots(baseline)
    _validate_table_inventory(baseline)
    _validate_authorities_and_evidence(baseline)
    _validate_external_inputs(baseline)


def test_frozen_baseline_is_complete_and_current() -> None:
    validate_baseline(_load_baseline())


def test_rejects_unmapped_active_writer() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["path_inventory"]["rules"] = [
        rule for rule in baseline["path_inventory"]["rules"] if rule["id"] != "mission-runtime"
    ]
    with pytest.raises(BaselineError, match="maps to 0 base owners"):
        _validate_path_inventory(baseline)


def test_rejects_duplicate_table_authority() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["migration_inventory"]["table_groups"][1]["tables"].append("missions")
    with pytest.raises(BaselineError, match="duplicate table authority: missions"):
        _validate_table_inventory(baseline)


def test_rejects_missing_module_treatment() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["path_inventory"]["module_treatments"].pop()
    with pytest.raises(BaselineError, match="module-treatment inventory is incomplete"):
        _validate_path_inventory(baseline)


def test_rejects_missing_referenced_without_definition_table() -> None:
    baseline = copy.deepcopy(_load_baseline())
    missing_group = next(
        group
        for group in baseline["migration_inventory"]["table_groups"]
        if group["state"] == "referenced-no-definition"
    )
    missing_group["tables"].pop()
    with pytest.raises(BaselineError, match="referenced-without-definition inventory mismatch"):
        _validate_table_inventory(baseline)


def test_rejects_missing_authority_domain() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["authority_domains"].pop()
    with pytest.raises(BaselineError, match="authority-domain inventory is incomplete"):
        _validate_authorities_and_evidence(baseline)


def test_rejects_duplicate_active_authority() -> None:
    baseline = copy.deepcopy(_load_baseline())
    domain = baseline["authority_domains"][0]
    domain["duplicate_or_shadow_implementations"].append(domain["current_authoritative_writer"])
    with pytest.raises(BaselineError, match="duplicate active authority"):
        _validate_authorities_and_evidence(baseline)


def test_rejects_missing_compatibility_route() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["compatibility_routes"].pop()
    with pytest.raises(BaselineError, match="compatibility-route inventory is incomplete"):
        _validate_authorities_and_evidence(baseline)


def test_rejects_missing_historical_evidence_source() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["accepted_evidence"][0]["sources"].pop()
    with pytest.raises(BaselineError, match="historical tracker evidence is incomplete"):
        _validate_authorities_and_evidence(baseline)


def test_rejects_stale_branch_binding() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["source"]["branch"] = "main"
    with pytest.raises(BaselineError, match="stale source binding: branch"):
        _validate_source(baseline)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("remote_ref", "origin/main"),
        ("remote_commit_at_freeze", "d7568142396e77c8f6e2970e072f9406f64d60c5"),
        ("worktree_at_freeze", "dirty"),
        ("remote_divergence_at_freeze", {"ahead": 1, "behind": 0}),
    ),
)
def test_rejects_stale_remote_or_worktree_binding(field: str, value: Any) -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["source"][field] = value
    with pytest.raises(BaselineError, match=f"stale source binding: {field}"):
        _validate_source(baseline)


def test_rejects_accepted_proof_reclassified_as_current_implementation() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["accepted_evidence"][0]["currentness"] = "current-implementation"
    with pytest.raises(BaselineError, match="accepted proof reclassified as current"):
        _validate_authorities_and_evidence(baseline)


def test_rejects_utils_handoff_reclassified_as_public_release() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["external_inputs"][0]["accepted_handoff"]["release_posture"] = "publicly-installable"
    with pytest.raises(BaselineError, match="utils accepted handoff is stale"):
        _validate_external_inputs(baseline)


def test_rejects_missing_utils_artifact_identity() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["external_inputs"][0]["accepted_handoff"]["artifacts"].pop()
    with pytest.raises(BaselineError, match="artifact inventory is stale"):
        _validate_external_inputs(baseline)
