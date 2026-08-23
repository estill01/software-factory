from __future__ import annotations

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
}
ALLOWED_DISPOSITIONS = {"retain", "move", "adapt", "replace", "retire", "evidence-only"}
CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Za-z0-9_]+)",
    re.IGNORECASE,
)


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
    rules = baseline["path_inventory"]["rules"]
    rule_ids = [rule["id"] for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise BaselineError("duplicate path rule id")

    for rule in rules:
        if rule.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise BaselineError(f"invalid disposition for path rule {rule['id']}")
        if not rule.get("target_owner"):
            raise BaselineError(f"missing target owner for path rule {rule['id']}")

    for path in paths:
        matches = [rule["id"] for rule in rules if _rule_matches(rule, path)]
        if len(matches) != 1:
            raise BaselineError(f"path {path} maps to {len(matches)} owners: {matches}")

    treatments = baseline["path_inventory"]["module_treatments"]
    treatment_paths = [item["path"] for item in treatments]
    if len(treatment_paths) != len(set(treatment_paths)):
        raise BaselineError("duplicate module treatment")
    for treatment in treatments:
        if treatment["path"] not in paths:
            raise BaselineError(f"module treatment path is not frozen: {treatment['path']}")
        if treatment["disposition"] not in ALLOWED_DISPOSITIONS:
            raise BaselineError(f"invalid module treatment: {treatment['path']}")
        if not treatment.get("target_owner") or not treatment.get("removal_condition"):
            raise BaselineError(f"incomplete module treatment: {treatment['path']}")


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
    runtime_source = "\n".join(str(_git("show", f"{commit}:{path}")) for path in python_paths)
    for table in missing_group["tables"]:
        if table in defined_tables:
            raise BaselineError(f"table is mislabeled as undefined: {table}")
        if not re.search(rf"\b{re.escape(table)}\b", runtime_source):
            raise BaselineError(f"undefined table is not referenced by runtime source: {table}")


def _validate_authorities_and_evidence(baseline: dict[str, Any]) -> None:
    domains = baseline["authority_domains"]
    domain_names = [domain["domain"] for domain in domains]
    if len(domain_names) != len(set(domain_names)):
        raise BaselineError("duplicate authority domain")
    for domain in domains:
        if not isinstance(domain.get("current_authoritative_writer"), str):
            raise BaselineError(f"duplicate or missing current authority: {domain['domain']}")
        if not domain["current_authoritative_writer"] or not domain.get("target_owner"):
            raise BaselineError(f"missing authority owner: {domain['domain']}")

    route_ids = [route["id"] for route in baseline["compatibility_routes"]]
    if len(route_ids) != len(set(route_ids)):
        raise BaselineError("duplicate compatibility route")
    for route in baseline["compatibility_routes"]:
        if not route.get("target_owner") or not route.get("removal_condition"):
            raise BaselineError(f"incomplete compatibility route: {route['id']}")

    for evidence in baseline["accepted_evidence"]:
        if evidence["classification"] != "accepted-input":
            raise BaselineError(f"unsupported evidence classification: {evidence['id']}")
        if evidence["currentness"] != "historical-evidence-not-current-implementation":
            raise BaselineError(f"accepted proof reclassified as current: {evidence['id']}")

    planned_blocks = [item["block"] for item in baseline["changed_test_plan"]]
    if planned_blocks != list(range(1, 13)):
        raise BaselineError("changed-test plan must cover Blocks 1-12 in order")


def validate_baseline(baseline: dict[str, Any]) -> None:
    if baseline.get("schema_version") != "software-factory-v2-baseline/v1":
        raise BaselineError("unknown baseline schema")
    _validate_source(baseline)
    _validate_product_frame(baseline)
    _validate_path_inventory(baseline)
    _validate_surface_roots(baseline)
    _validate_table_inventory(baseline)
    _validate_authorities_and_evidence(baseline)


def test_frozen_baseline_is_complete_and_current() -> None:
    validate_baseline(_load_baseline())


def test_rejects_unmapped_active_writer() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["path_inventory"]["rules"] = [
        rule for rule in baseline["path_inventory"]["rules"] if rule["id"] != "mission-runtime"
    ]
    with pytest.raises(BaselineError, match="maps to 0 owners"):
        _validate_path_inventory(baseline)


def test_rejects_duplicate_table_authority() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["migration_inventory"]["table_groups"][1]["tables"].append("missions")
    with pytest.raises(BaselineError, match="duplicate table authority: missions"):
        _validate_table_inventory(baseline)


def test_rejects_stale_branch_binding() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["source"]["branch"] = "main"
    with pytest.raises(BaselineError, match="stale source binding: branch"):
        _validate_source(baseline)


def test_rejects_accepted_proof_reclassified_as_current_implementation() -> None:
    baseline = copy.deepcopy(_load_baseline())
    baseline["accepted_evidence"][0]["currentness"] = "current-implementation"
    with pytest.raises(BaselineError, match="accepted proof reclassified as current"):
        _validate_authorities_and_evidence(baseline)
