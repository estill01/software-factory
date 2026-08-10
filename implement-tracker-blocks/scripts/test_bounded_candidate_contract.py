#!/usr/bin/env python3
"""Evidence-bound behavior for one selective bounded candidate lane."""

from __future__ import annotations

import copy
import ast
import base64
import difflib
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import tempfile
import unittest
import unicodedata
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from statistics import median
from time import process_time_ns


def reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_pairs)
    if type(value) is not dict:
        raise ValueError("fixture root must be an object")
    return value


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
TRACKER_PATH = REPO_ROOT / "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL_ROOT / "references/bounded-candidate-lane.md").read_text(encoding="utf-8")
ADAPTIVE = (SKILL_ROOT / "references/adaptive-decision-control.md").read_text(encoding="utf-8")
SPEC = json.loads(ADAPTIVE.split("<!-- contract-spec-v1 -->", 1)[1].split("```json", 1)[1].split("```", 1)[0])
EXERCISE = load_strict_json(SKILL_ROOT / "fixtures/bounded_candidate_v1.json")
REVIEW_FIXTURE = load_strict_json(SKILL_ROOT / "fixtures/bounded_candidate_reviews_v1.json")
PRE_RUN = load_strict_json(SKILL_ROOT / "fixtures/bounded_candidate_prerun_v1.json")
ACCEPTED_SNAPSHOT_PATH = SKILL_ROOT / "fixtures/bounded_candidate_accepted_v1.json"
ACCEPTED_SNAPSHOT = load_strict_json(ACCEPTED_SNAPSHOT_PATH)
EXACT_REVIEW_PATH = SKILL_ROOT / "fixtures/bounded_candidate_exact_review_v1.json"
EXACT_REVIEW_BYTES = EXACT_REVIEW_PATH.read_bytes()
EXACT_REVIEW = load_strict_json(EXACT_REVIEW_PATH)
REVIEWER_AUTHORITY_ROOT = Path("/Users/ethanstillman/.codex/software-factory-release-authority")
REVIEWER_AUTHORITY_DIRECTORY = REVIEWER_AUTHORITY_ROOT / "reviewers"
REVIEWER_PUBLIC_KEY_PATH = REVIEWER_AUTHORITY_DIRECTORY / "software-factory-release-reviewer-v1.pem"

EXPECTED_EXERCISE_ROOT = "a039c787cb15df11e7fd1c2dbfd904a4b908540f5aa2ffea4900f359df383337"
EXPECTED_REVIEW_FIXTURE_ROOT = "3bbf84c0823cecdd73110f60ff990f541bb20c14a9deeda868463a54811804e0"
EXPECTED_PRE_RUN_ROOT = "f3fc594b4eca93ff75db127234a18ed494377575df82373695ac8754a9231bbb"
EXPECTED_ACCEPTED_SNAPSHOT_ROOT = "c5af9febeae85773f106d3a761689e88e7756f75666e4f613de5c38615ea2252"
EXPECTED_EXACT_REVIEW_SHA256 = "83d8a3efc7c5492884499f2ebb5e124901ca85b5f7af59f79613c5f90f4cc811"
EXPECTED_REVIEWER_KEY_SHA256 = "e6ace9dfbbf97ec65800d1da146c4b59b20a2aef86ad706b174b9837bcb41a02"
TRUSTED_OPENSSL_PATH = Path("/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl")
TRUSTED_OPENSSL_SHA256 = "bf63843e6856e1994ca71092ff3b46834236eb2144dd9b6ceb85d511128b836e"
GIT_EXECUTABLE = "/usr/bin/git"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
DIMENSIONS = [
    "observable-outcome",
    "implementation-cost",
    "maintenance-cost",
    "reversibility",
    "compatibility",
    "protected-capability",
]
RELATIONS = {"candidate-better", "incumbent-better", "equivalent", "inconclusive"}
COMPARISON_DISPOSITIONS = {"candidate-better", "incumbent-better", "non-inferior-no-benefit", "inconclusive"}
BLOCK4_REVIEW = {
    "candidate-better": "accepted",
    "incumbent-better": "accepted",
    "non-inferior-no-benefit": "accepted",
    "inconclusive": "inconclusive",
}
RETIREMENT = {
    "candidate-better": "eligible-cutover",
    "incumbent-better": "retired-loser",
    "non-inferior-no-benefit": "retired-loser",
    "inconclusive": "retired-inconclusive",
}
ELIGIBILITY_FIELDS = {
    "material_better_path",
    "trigger_evidence_root",
    "outcome_uncertainty_supported",
    "outcome_uncertainty_evidence_root",
    "implementation_evidence_required",
    "implementation_evidence_root",
    "read_only_resolvable",
    "rework_avoided_minutes",
    "candidate_ceiling_minutes",
    "review_ceiling_minutes",
    "isolation_recovery_minutes",
    "reversibility_posture",
    "reversibility_evidence_root",
    "isolation_safe",
}


def validate_canonical_value(value: object) -> None:
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("JSON string is not NFC-normalized")
        return
    if type(value) is list:
        for item in value:
            validate_canonical_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or unicodedata.normalize("NFC", key) != key:
                raise ValueError("JSON object key is not canonical")
            validate_canonical_value(item)
        return
    raise ValueError("JSON value is outside the bounded RFC8785 profile")


def canonical(value: object) -> bytes:
    validate_canonical_value(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def root(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_root(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def exact_string(value: object, label: str, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value or (pattern is not None and pattern.fullmatch(value) is None):
        raise ValueError(f"{label} differs")
    return value


def exact_int(value: object, label: str, *, minimum: int = 0, maximum: int = 100000000) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ValueError(f"{label} differs")
    return value


def exact_path(value: object, label: str, *, contained_by: str | None = None) -> str:
    path = exact_string(value, label)
    pure = PurePosixPath(path)
    if not pure.is_absolute() or any(part in {".", ".."} for part in pure.parts) or str(pure) != path:
        raise ValueError(f"{label} is not canonical")
    if contained_by is not None:
        container = PurePosixPath(contained_by)
        try:
            pure.relative_to(container)
        except ValueError as error:
            raise ValueError(f"{label} escapes owner") from error
    return path


def validate_scope_refs(value: object, label: str, *, contained_by: str, min_items: int) -> list[dict[str, object]]:
    if type(value) is not list or len(value) < min_items:
        raise ValueError(f"{label} differs")
    if len({canonical(item) for item in value}) != len(value):
        raise ValueError(f"{label} contains duplicates")
    for item in value:
        if type(item) is not dict or set(item) != {"owner_id", "path", "content_root"}:
            raise ValueError(f"{label} shape differs")
        exact_string(item["owner_id"], f"{label} owner", ID_RE)
        exact_path(item["path"], f"{label} path", contained_by=contained_by)
        exact_string(item["content_root"], f"{label} root", SHA_RE)
    return value


def tracker_sha256() -> str:
    relative = TRACKER_PATH.relative_to(REPO_ROOT).as_posix()
    probe = subprocess.run([GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"], cwd=REPO_ROOT, capture_output=True, text=True)
    frozen = subprocess.run([GIT_EXECUTABLE, "show", f"{EXERCISE['tracker_source_revision']}:{relative}"], cwd=REPO_ROOT, capture_output=True)
    if frozen.returncode == 0:
        return hashlib.sha256(frozen.stdout).hexdigest()
    if probe.returncode == 0:
        raise ValueError("frozen tracker source cannot be resolved in live repository")
    return exact_string(EXERCISE["tracker_sha256"], "archive tracker root", SHA_RE)


def block_contract_root() -> str:
    relative = TRACKER_PATH.relative_to(REPO_ROOT).as_posix()
    probe = subprocess.run([GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"], cwd=REPO_ROOT, capture_output=True, text=True)
    frozen = subprocess.run([GIT_EXECUTABLE, "show", f"{EXERCISE['tracker_source_revision']}:{relative}"], cwd=REPO_ROOT, capture_output=True)
    if frozen.returncode == 0:
        marker = b"## Block 6 \xe2\x80\x94"
        start = frozen.stdout.find(marker)
        end = frozen.stdout.find(b"\n---\n", start)
        if start < 0 or end < 0:
            raise ValueError("frozen Block 6 contract cannot be isolated")
        return hashlib.sha256(frozen.stdout[start:end]).hexdigest()
    if probe.returncode == 0:
        raise ValueError("frozen Block 6 contract cannot be resolved in live repository")
    return exact_string(EXERCISE["block_contract_root"], "archive Block 6 root", SHA_RE)


def pre_run_contract_root() -> str:
    relative = "implement-tracker-blocks/fixtures/bounded_candidate_prerun_v1.json"
    source_revision = EXERCISE["pre_run_contract"]["source_revision"]
    probe = subprocess.run([GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"], cwd=REPO_ROOT, capture_output=True, text=True)
    frozen = subprocess.run([GIT_EXECUTABLE, "show", f"{source_revision}:{relative}"], cwd=REPO_ROOT, capture_output=True)
    if frozen.returncode == 0:
        value = json.loads(frozen.stdout, object_pairs_hook=reject_duplicate_pairs)
        if type(value) is not dict:
            raise ValueError("pre-run contract source differs")
        return root(value)
    if probe.returncode == 0:
        raise ValueError("pre-run contract source cannot be resolved in live repository")
    return exact_string(EXERCISE["pre_run_contract"]["contract_root"], "archive pre-run contract root", SHA_RE)


def file_manifest(files: object, *, contained_by: str) -> list[dict[str, str]]:
    if type(files) is not list or not files:
        raise ValueError("artifact files differ")
    result: list[dict[str, str]] = []
    for item in files:
        if type(item) is not dict or set(item) != {"path", "content_utf8"}:
            raise ValueError("artifact file shape differs")
        path = exact_path(item["path"], "artifact path", contained_by=contained_by)
        content = exact_string(item["content_utf8"], "artifact bytes")
        result.append({"path": path, "content_sha256": bytes_root(content)})
    result.sort(key=lambda item: item["path"])
    if len({item["path"] for item in result}) != len(result):
        raise ValueError("artifact path is duplicated")
    return result


def file_content_root(files: object, path: str, *, contained_by: str) -> str:
    manifest = file_manifest(files, contained_by=contained_by)
    matches = [item["content_sha256"] for item in manifest if item["path"] == path]
    if len(matches) != 1:
        raise ValueError("owned file content root is unavailable")
    return matches[0]


def artifact_root(artifact: dict[str, object]) -> str:
    revision = exact_string(artifact["revision"], "candidate revision", REV_RE)
    return root({"revision": revision, "files": file_manifest(artifact["files"], contained_by=EXERCISE["lane"]["root"])})


def incumbent_root() -> str:
    incumbent = EXERCISE["incumbent"]
    revision = exact_string(incumbent["revision"], "incumbent revision", REV_RE)
    return root({"revision": revision, "files": file_manifest(incumbent["files"], contained_by=EXERCISE["target_repository_root"])})


def target_revision_root() -> str:
    return root({"target_revision": EXERCISE["target_revision"]})


def representative_payload() -> tuple[list[bytes], bytes]:
    workload = EXERCISE["representative_workload"]
    exact_fields = {"schema_version", "kind", "row_count", "index_format", "repeated_utf8", "repeat_count", "suffix_alphabet", "suffix_repeat_count", "join_separator_hex"}
    if type(workload) is not dict or set(workload) != exact_fields or workload["schema_version"] != 1 or workload["kind"] != "deterministic-compression-corpus" or workload["index_format"] != "row-%04d-" or workload["join_separator_hex"] != "0a":
        raise ValueError("representative workload differs")
    row_count = exact_int(workload["row_count"], "workload rows", minimum=1, maximum=10000)
    repeat_count = exact_int(workload["repeat_count"], "workload repeat", minimum=1, maximum=1000)
    suffix_count = exact_int(workload["suffix_repeat_count"], "workload suffix", minimum=1, maximum=1000)
    repeated = exact_string(workload["repeated_utf8"], "workload repeated bytes").encode("utf-8")
    alphabet = exact_string(workload["suffix_alphabet"], "workload alphabet").encode("ascii")
    rows = [(b"row-%04d-" % index) + (repeated * repeat_count) + (bytes([alphabet[index % len(alphabet)]]) * suffix_count) for index in range(row_count)]
    return rows, bytes.fromhex(workload["join_separator_hex"]).join(rows)


def validation_runtime_root() -> str:
    runtime = EXERCISE["validation_runtime"]
    executable = Path(sys.executable).resolve()
    expected = {
        "schema_version": 1,
        "kind": "python-stdlib-zlib",
        "algorithm": "zlib.compress",
        "python_executable": str(executable),
        "python_executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "zlib_version": zlib.ZLIB_RUNTIME_VERSION,
        "system": platform.system(),
        "system_release": platform.release(),
        "machine": platform.machine(),
    }
    if type(runtime) is not dict or runtime != expected:
        raise ValueError("validation runtime differs")
    return root(runtime)


def stream_source(files: object, *, contained_by: str) -> str:
    path = f"{contained_by}/stream_export.py"
    if type(files) is not list:
        raise ValueError("stream source files differ")
    matches = [item for item in files if type(item) is dict and item.get("path") == path]
    if len(matches) != 1:
        raise ValueError("stream source is unavailable")
    return exact_string(matches[0].get("content_utf8"), "stream source bytes")


def load_export(files: object, *, contained_by: str):
    source = stream_source(files, contained_by=contained_by)
    namespace: dict[str, object] = {}
    code = compile(source, "<bounded-candidate-stream-export>", "exec")
    exec(code, {"__builtins__": {"bytes": bytes, "RuntimeError": RuntimeError}, "zlib": zlib}, namespace)
    export = namespace.get("export")
    if not callable(export):
        raise ValueError("stream source lacks export")
    return export


def benchmark_performance(files: object, *, contained_by: str) -> dict[str, object]:
    rows, _ = representative_payload()
    incumbent_export = load_export(EXERCISE["incumbent"]["files"], contained_by=EXERCISE["target_repository_root"])
    candidate_export = load_export(files, contained_by=contained_by)
    protocol = EXERCISE["performance_protocol"]
    for _ in range(protocol["warmup_pairs"]):
        incumbent_export(rows)
        candidate_export(rows)
    incumbent_samples: list[int] = []
    candidate_samples: list[int] = []
    for sample in range(protocol["sample_pairs"]):
        ordered = ((candidate_export, candidate_samples), (incumbent_export, incumbent_samples)) if sample % 2 else ((incumbent_export, incumbent_samples), (candidate_export, candidate_samples))
        for operation, samples in ordered:
            started = process_time_ns()
            for _ in range(protocol["calls_per_sample"]):
                operation(rows)
            samples.append(process_time_ns() - started)
    incumbent_median = int(median(incumbent_samples))
    candidate_median = int(median(candidate_samples))
    ratios = sorted((candidate * 10000) // incumbent for candidate, incumbent in zip(candidate_samples, incumbent_samples))
    ratio_basis_points = candidate_median * 10000 // incumbent_median
    spread = ratios[11] - ratios[3]
    maximum = EXERCISE["materiality_criterion"]["maximum_candidate_runtime_basis_points"]
    if spread > protocol["maximum_interquartile_spread_basis_points"]:
        posture = "inconclusive"
    else:
        posture = "candidate-not-materially-slower" if ratio_basis_points <= maximum else "candidate-materially-slower"
    return {
        "incumbent_samples_ns": incumbent_samples,
        "candidate_samples_ns": candidate_samples,
        "incumbent_median_ns": incumbent_median,
        "candidate_median_ns": candidate_median,
        "ratio_basis_points": ratio_basis_points,
        "interquartile_spread_basis_points": spread,
        "performance_posture": posture,
    }


def performance_evidence(artifact: dict[str, object], candidate_root: str) -> dict[str, object]:
    mapped = artifact["mapped"]
    if type(mapped) is not dict or type(mapped.get("performance_evidence")) is not dict:
        raise ValueError("mapped performance evidence is absent")
    value = copy.deepcopy(mapped["performance_evidence"])
    exact_fields = {
        "schema_version", "kind", "candidate_root", "representative_workload_root",
        "validation_runtime_root", "performance_protocol_root", "recorded_at",
        "incumbent_samples_ns", "candidate_samples_ns", "incumbent_median_ns",
        "candidate_median_ns", "ratio_basis_points", "interquartile_spread_basis_points",
        "performance_posture", "result_root",
    }
    if type(value) is not dict or set(value) != exact_fields or value["schema_version"] != 1 or value["kind"] != "software-factory-candidate-performance-result":
        raise ValueError("performance evidence shape differs")
    if value["candidate_root"] != candidate_root or value["representative_workload_root"] != root(EXERCISE["representative_workload"]) or value["validation_runtime_root"] != validation_runtime_root() or value["performance_protocol_root"] != root(EXERCISE["performance_protocol"]):
        raise ValueError("performance evidence basis differs")
    parse_time(value["recorded_at"], "performance evidence time")
    protocol = EXERCISE["performance_protocol"]
    for key in ("incumbent_samples_ns", "candidate_samples_ns"):
        samples = value[key]
        if type(samples) is not list or len(samples) != protocol["sample_pairs"]:
            raise ValueError("performance sample count differs")
        for sample in samples:
            exact_int(sample, "performance sample", minimum=1, maximum=10_000_000_000)
    incumbent_median = int(median(value["incumbent_samples_ns"]))
    candidate_median = int(median(value["candidate_samples_ns"]))
    ratios = sorted((candidate * 10000) // incumbent for candidate, incumbent in zip(value["candidate_samples_ns"], value["incumbent_samples_ns"]))
    spread = ratios[11] - ratios[3]
    ratio = candidate_median * 10000 // incumbent_median
    posture = "inconclusive" if spread > protocol["maximum_interquartile_spread_basis_points"] else "candidate-not-materially-slower" if ratio <= EXERCISE["materiality_criterion"]["maximum_candidate_runtime_basis_points"] else "candidate-materially-slower"
    if (value["incumbent_median_ns"], value["candidate_median_ns"], value["ratio_basis_points"], value["interquartile_spread_basis_points"], value["performance_posture"]) != (incumbent_median, candidate_median, ratio, spread, posture):
        raise ValueError("performance evidence calculation differs")
    raw = dict(value)
    recorded_root = raw.pop("result_root")
    if recorded_root != root(raw):
        raise ValueError("performance evidence root differs")
    # Timing evidence is an immutable observation, not an instruction to rerun
    # a noisy producer whenever a consumer validates its exact bytes. Runtime,
    # protocol, candidate, samples, derivation, and result root establish its
    # currentness; a later benchmark is new evidence for a successor decision.
    return value


def execute_stream(files: object, *, contained_by: str) -> dict[str, object]:
    try:
        export = load_export(files, contained_by=contained_by)
        rows, payload = representative_payload()
        result = export(rows)
        bytes_api = type(result) is bytes
        regressions: list[str] = []
        if not bytes_api:
            regressions.append("stable-bytes-api")
        try:
            restored = zlib.decompress(result) if bytes_api else b""
        except zlib.error:
            restored = b""
        if restored != payload:
            regressions.append("semantic-roundtrip")
        payload_root = hashlib.sha256(restored).hexdigest()
        artifact_bytes = len(result) if bytes_api else None
        focused_output = f"roundtrip={payload_root};bytes={artifact_bytes};api={'bytes' if bytes_api else type(result).__name__}"
        return {"exit_code": 0 if not regressions else 1, "output": focused_output, "protected_result": "preserved" if not regressions else "regressed", "decompressed_sha256": payload_root, "artifact_bytes": artifact_bytes, "api_type": "bytes" if bytes_api else type(result).__name__, "regression_ids": sorted(regressions)}
    except (RuntimeError, TypeError, ValueError) as error:
        return {"exit_code": 1, "output": f"execution={type(error).__name__}:{error}", "protected_result": "failed", "decompressed_sha256": None, "artifact_bytes": None, "api_type": None, "regression_ids": ["execution-failed"]}


def changed_lines(files: object) -> int:
    incumbent = stream_source(EXERCISE["incumbent"]["files"], contained_by=EXERCISE["target_repository_root"])
    candidate = stream_source(files, contained_by=EXERCISE["lane"]["root"])
    return sum(1 for line in difflib.ndiff(incumbent.splitlines(), candidate.splitlines()) if line.startswith(("+ ", "- ")))


def decision_points(files: object, *, contained_by: str) -> int:
    tree = ast.parse(stream_source(files, contained_by=contained_by))
    nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.BoolOp, ast.IfExp, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    return sum(isinstance(node, nodes) for node in ast.walk(tree))


def derived_candidate_metrics(artifact: dict[str, object]) -> dict[str, object]:
    observed = execute_stream(artifact["files"], contained_by=EXERCISE["lane"]["root"])
    performance = performance_evidence(artifact, artifact_root(artifact))
    compatibility: list[str] | None = []
    if artifact["mapped"]["output"] == "comparison=broader-compatibility-unavailable":
        compatibility = None
    return {
        "observable-outcome": {"decompressed_sha256": observed["decompressed_sha256"], "artifact_bytes": observed["artifact_bytes"], "performance_posture": performance["performance_posture"], "performance_result_root": performance["result_root"]},
        "implementation-cost": {"changed_lines": changed_lines(artifact["files"])},
        "maintenance-cost": {"decision_points": decision_points(artifact["files"], contained_by=EXERCISE["lane"]["root"])},
        "reversibility": {"restore_steps": 1},
        "compatibility": {"api_break_ids": compatibility},
        "protected-capability": {"regression_ids": observed["regression_ids"]},
    }


def derived_incumbent_metrics() -> dict[str, object]:
    observed = execute_stream(EXERCISE["incumbent"]["files"], contained_by=EXERCISE["target_repository_root"])
    return {
        "observable-outcome": {"decompressed_sha256": observed["decompressed_sha256"], "artifact_bytes": observed["artifact_bytes"], "performance_posture": "baseline", "performance_result_root": None},
        "implementation-cost": {"changed_lines": 0},
        "maintenance-cost": {"decision_points": decision_points(EXERCISE["incumbent"]["files"], contained_by=EXERCISE["target_repository_root"])},
        "reversibility": {"restore_steps": 0},
        "compatibility": {"api_break_ids": []},
        "protected-capability": {"regression_ids": observed["regression_ids"]},
    }


def parse_time(value: object, label: str) -> datetime:
    raw = exact_string(value, label)
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ValueError(f"{label} differs") from error
    return parsed


def result_id(prefix: str, candidate_root: str) -> str:
    return f"{prefix}-{candidate_root[:20]}"


def focused_result(artifact: dict[str, object], candidate_root: str) -> dict[str, object]:
    value = artifact["focused"]
    if type(value) is not dict or set(value) != {"recorded_at", "command", "exit_code", "output", "protected_result"}:
        raise ValueError("focused result shape differs")
    observed = execute_stream(artifact["files"], contained_by=EXERCISE["lane"]["root"])
    if value["command"] != "embedded:focused-compressed-export-v1" or any(value[key] != observed[key] for key in ("exit_code", "output", "protected_result")):
        raise ValueError("focused result differs from executable candidate bytes")
    result = {
        "schema_version": 1,
        "kind": "software-factory-candidate-focused-result",
        "result_id": result_id("focused", candidate_root),
        "candidate_root": candidate_root,
        "pre_run_contract_root": pre_run_contract_root(),
        "lane_execution_root": root(EXERCISE["lane_execution"]),
        "representative_workload_root": root(EXERCISE["representative_workload"]),
        "validation_runtime_root": validation_runtime_root(),
        "recorded_at": exact_string(value["recorded_at"], "focused time"),
        "command": exact_string(value["command"], "focused command"),
        "exit_code": exact_int(value["exit_code"], "focused exit", maximum=255),
        "output_sha256": bytes_root(exact_string(value["output"], "focused output")),
        "protected_result": exact_string(value["protected_result"], "protected result"),
    }
    parse_time(result["recorded_at"], "focused time")
    result["result_root"] = root(result)
    return result


def validate_metrics(metrics: object) -> dict[str, object]:
    if type(metrics) is not dict or list(metrics) != DIMENSIONS:
        raise ValueError("mapped metrics differ")
    outcome = metrics["observable-outcome"]
    if type(outcome) is not dict or set(outcome) != {"decompressed_sha256", "artifact_bytes", "performance_posture", "performance_result_root"}:
        raise ValueError("observable metric differs")
    exact_string(outcome["decompressed_sha256"], "observable output", SHA_RE)
    if outcome["artifact_bytes"] is not None:
        exact_int(outcome["artifact_bytes"], "artifact bytes")
    if outcome["performance_posture"] not in {"baseline", "candidate-not-materially-slower", "candidate-materially-slower", "inconclusive"}:
        raise ValueError("performance posture differs")
    if outcome["performance_result_root"] is not None:
        exact_string(outcome["performance_result_root"], "performance result root", SHA_RE)
    for dimension, field in (
        ("implementation-cost", "changed_lines"),
        ("maintenance-cost", "decision_points"),
        ("reversibility", "restore_steps"),
    ):
        value = metrics[dimension]
        if type(value) is not dict or set(value) != {field}:
            raise ValueError(f"{dimension} metric differs")
        exact_int(value[field], dimension)
    compatibility = metrics["compatibility"]
    if type(compatibility) is not dict or set(compatibility) != {"api_break_ids"} or (compatibility["api_break_ids"] is not None and type(compatibility["api_break_ids"]) is not list):
        raise ValueError("compatibility metric differs")
    if compatibility["api_break_ids"] is not None and (compatibility["api_break_ids"] != sorted(set(compatibility["api_break_ids"])) or any(type(item) is not str or not item for item in compatibility["api_break_ids"])):
        raise ValueError("compatibility break differs")
    protected = metrics["protected-capability"]
    if type(protected) is not dict or set(protected) != {"regression_ids"} or type(protected["regression_ids"]) is not list:
        raise ValueError("protected metric differs")
    if protected["regression_ids"] != sorted(set(protected["regression_ids"])) or any(type(item) is not str or not item for item in protected["regression_ids"]):
        raise ValueError("protected regression differs")
    return metrics


def mapped_result(artifact: dict[str, object], candidate_root: str, focused: dict[str, object]) -> dict[str, object] | None:
    value = artifact["mapped"]
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"recorded_at", "command", "exit_code", "output", "metrics", "performance_evidence"}:
        raise ValueError("mapped result shape differs")
    metrics = value["metrics"]
    if metrics is not None:
        validate_metrics(metrics)
        if value["command"] != "embedded:mapped-compressed-export-v1" or value["exit_code"] != 0 or metrics != derived_candidate_metrics(artifact):
            raise ValueError("mapped result differs from executable candidate bytes")
    elif value["command"] != "embedded:mapped-compressed-export-v1" or value["exit_code"] == 0 or value["performance_evidence"] is not None:
        raise ValueError("mapped failure differs")
    result = {
        "schema_version": 1,
        "kind": "software-factory-candidate-mapped-result",
        "result_id": result_id("mapped", candidate_root),
        "candidate_root": candidate_root,
        "incumbent_root": incumbent_root(),
        "focused_result_root": focused["result_root"],
        "recorded_at": exact_string(value["recorded_at"], "mapped time"),
        "command": exact_string(value["command"], "mapped command"),
        "exit_code": exact_int(value["exit_code"], "mapped exit", maximum=255),
        "output_sha256": bytes_root(exact_string(value["output"], "mapped output")),
        "performance_result_root": metrics["observable-outcome"]["performance_result_root"] if metrics is not None else None,
        "metrics": metrics,
    }
    if parse_time(result["recorded_at"], "mapped time") <= parse_time(focused["recorded_at"], "focused time"):
        raise ValueError("mapped result does not follow frozen focused proof")
    result["result_root"] = root(result)
    return result


def validate_exercise() -> None:
    if root(EXERCISE) != EXPECTED_EXERCISE_ROOT or root(REVIEW_FIXTURE) != EXPECTED_REVIEW_FIXTURE_ROOT:
        raise ValueError("bounded candidate source root differs")
    exact_exercise_fields = {"schema_version", "kind", "block_number", "tracker_source_revision", "tracker_sha256", "mission_root", "policy_root", "event_head_root", "block_contract_root", "pre_run_contract", "lane_execution", "representative_workload", "validation_runtime", "performance_protocol", "materiality_criterion", "candidate_trigger", "target_repository_root", "target_revision", "capability_contract", "incumbent", "lane", "hypothesis", "hypothesis_scope", "comparison_dimensions", "eligibility_evidence", "eligibility_default", "artifacts", "cases"}
    if set(EXERCISE) != exact_exercise_fields:
        raise ValueError("bounded candidate exercise shape differs")
    if type(EXERCISE["schema_version"]) is not int or EXERCISE["schema_version"] != 2 or EXERCISE["kind"] != "software-factory-bounded-candidate-exercise" or type(EXERCISE["block_number"]) is not int or EXERCISE["block_number"] != 6:
        raise ValueError("bounded candidate identity differs")
    exact_string(EXERCISE["tracker_source_revision"], "tracker source revision", REV_RE)
    if EXERCISE["tracker_sha256"] != tracker_sha256():
        raise ValueError("tracker source root is stale")
    trigger = EXERCISE["candidate_trigger"]
    if type(trigger) is not dict or set(trigger) != {"disposition", "reason", "source_class", "source_root"} or trigger != {"disposition": "compare-candidate", "reason": "material-better-path", "source_class": "tracker", "source_root": EXERCISE["tracker_sha256"]}:
        raise ValueError("candidate trigger differs")
    if EXERCISE["block_contract_root"] != block_contract_root():
        raise ValueError("Block 6 contract root is stale")
    pre_run = EXERCISE["pre_run_contract"]
    if type(pre_run) is not dict or set(pre_run) != {"source_revision", "contract_root"}:
        raise ValueError("pre-run contract identity differs")
    exact_string(pre_run["source_revision"], "pre-run source revision", REV_RE)
    if pre_run["contract_root"] != EXPECTED_PRE_RUN_ROOT or pre_run_contract_root() != EXPECTED_PRE_RUN_ROOT or root(PRE_RUN) != EXPECTED_PRE_RUN_ROOT:
        raise ValueError("pre-run contract root differs")
    lane_execution = EXERCISE["lane_execution"]
    if type(lane_execution) is not dict or set(lane_execution) != {"schema_version", "kind", "pre_run_source_revision", "pre_run_contract_root", "lane_started_at", "implementation_started_at", "start_basis"} or lane_execution["schema_version"] != 1 or lane_execution["kind"] != "software-factory-bounded-candidate-lane-execution" or lane_execution["pre_run_source_revision"] != pre_run["source_revision"] or lane_execution["pre_run_contract_root"] != pre_run["contract_root"] or lane_execution["start_basis"] != "conservative-pre-run-checkpoint-commit-time":
        raise ValueError("lane execution start differs")
    lane_started = parse_time(lane_execution["lane_started_at"], "lane start")
    implementation_started = parse_time(lane_execution["implementation_started_at"], "implementation start")
    if implementation_started < lane_started:
        raise ValueError("implementation predates lane start")
    representative_payload()
    runtime_root = validation_runtime_root()
    protocol = EXERCISE["performance_protocol"]
    if type(protocol) is not dict or set(protocol) != {"clock", "warmup_pairs", "sample_pairs", "calls_per_sample", "order", "summary", "maximum_interquartile_spread_basis_points"} or protocol["clock"] != "process_time_ns" or protocol["order"] != "alternating-incumbent-candidate" or protocol["summary"] != "median-ratio-basis-points":
        raise ValueError("performance protocol differs")
    exact_int(protocol["warmup_pairs"], "performance warmups", minimum=1, maximum=100)
    exact_int(protocol["sample_pairs"], "performance samples", minimum=15, maximum=101)
    exact_int(protocol["calls_per_sample"], "performance calls", minimum=1, maximum=1000)
    exact_int(protocol["maximum_interquartile_spread_basis_points"], "performance spread", minimum=1, maximum=10000)
    materiality = EXERCISE["materiality_criterion"]
    if type(materiality) is not dict or set(materiality) != {"minimum_artifact_byte_reduction", "minimum_reduction_basis_points", "maximum_candidate_runtime_basis_points", "maximum_changed_lines", "maximum_restore_steps", "rationale"}:
        raise ValueError("candidate materiality criterion differs")
    exact_int(materiality["minimum_artifact_byte_reduction"], "minimum artifact byte reduction", minimum=1)
    exact_int(materiality["minimum_reduction_basis_points"], "minimum reduction basis points", minimum=1, maximum=10000)
    exact_int(materiality["maximum_candidate_runtime_basis_points"], "maximum candidate runtime basis points", minimum=1, maximum=100000)
    exact_int(materiality["maximum_changed_lines"], "maximum changed lines", minimum=0, maximum=1000)
    exact_int(materiality["maximum_restore_steps"], "maximum restore steps", minimum=0, maximum=100)
    exact_string(materiality["rationale"], "materiality rationale")
    if any(EXERCISE[key] != PRE_RUN[key] for key in ("representative_workload", "validation_runtime", "performance_protocol", "materiality_criterion", "capability_contract", "hypothesis", "hypothesis_scope")):
        raise ValueError("candidate run differs from frozen pre-run contract")
    expected_mission = root({"source_class": "tracker", "tracker_sha256": EXERCISE["tracker_sha256"], "block_number": 6, "capability_contract": EXERCISE["capability_contract"]})
    expected_policy = root({"adaptive_decision_mode": "full-autonomous", "candidate_lane_limit": 1, "mission_root": expected_mission})
    expected_event = root({"event_id": "block6-exercise-genesis", "mission_root": expected_mission, "policy_root": expected_policy})
    if (EXERCISE["mission_root"], EXERCISE["policy_root"], EXERCISE["event_head_root"]) != (expected_mission, expected_policy, expected_event):
        raise ValueError("candidate control roots differ")
    target_root = exact_path(EXERCISE["target_repository_root"], "target repository root")
    exact_string(EXERCISE["target_revision"], "target revision", REV_RE)
    contract = EXERCISE["capability_contract"]
    if type(contract) is not dict or set(contract) != {"statement", "protected_capabilities", "expected_observable_effect", "success_criteria", "cleanup_retention_posture"}:
        raise ValueError("capability contract differs")
    for key in ("statement", "expected_observable_effect", "cleanup_retention_posture"):
        exact_string(contract[key], f"capability {key}")
    for key in ("protected_capabilities", "success_criteria"):
        values = contract[key]
        if type(values) is not list or not values or values != sorted(set(values)) or any(type(item) is not str or not item for item in values):
            raise ValueError(f"capability {key} differs")
    lane = EXERCISE["lane"]
    if set(lane) != {"isolation_kind", "root", "isolated_writable_scope", "shared_resource_exclusions", "implementation_owner_id", "independent_reviewer_id", "cutover_owner_id", "resource_ceiling", "time_ceiling_minutes", "stop_condition"}:
        raise ValueError("candidate lane shape differs")
    exact_path(lane["root"], "lane root")
    if lane["isolation_kind"] not in SPEC["enums"]["isolation-kind"]:
        raise ValueError("isolation kind differs")
    for key in ("implementation_owner_id", "independent_reviewer_id", "cutover_owner_id"):
        exact_string(lane[key], key, ID_RE)
    if lane["implementation_owner_id"] != EXERCISE["incumbent"]["production_authority_owner_id"] or lane["independent_reviewer_id"] in {lane["implementation_owner_id"], lane["cutover_owner_id"]}:
        raise ValueError("candidate roles differ")
    ceiling = lane["resource_ceiling"]
    if type(ceiling) is not dict or set(ceiling) != {"max_files", "max_changed_lines", "max_commands", "max_review_passes"}:
        raise ValueError("resource ceiling differs")
    for key, maximum in (("max_files", 100), ("max_changed_lines", 10000), ("max_commands", 100), ("max_review_passes", 10)):
        exact_int(ceiling[key], key, minimum=1, maximum=maximum)
    exact_int(lane["time_ceiling_minutes"], "time ceiling", minimum=1, maximum=120)
    exact_string(lane["stop_condition"], "stop condition")
    validate_scope_refs(EXERCISE["hypothesis_scope"], "hypothesis scope", contained_by=target_root, min_items=1)
    validate_scope_refs(lane["isolated_writable_scope"], "isolated scope", contained_by=lane["root"], min_items=1)
    validate_scope_refs(lane["shared_resource_exclusions"], "shared exclusions", contained_by=target_root, min_items=0)
    production = set(EXERCISE["incumbent"]["writable_scope"])
    excluded = {item["path"] for item in lane["shared_resource_exclusions"]}
    isolated = {item["path"] for item in lane["isolated_writable_scope"]}
    if production.intersection(isolated) or not production.issubset(excluded):
        raise ValueError("candidate isolation overlaps production authority")
    incumbent_path = f"{target_root}/stream_export.py"
    incumbent_content = file_content_root(EXERCISE["incumbent"]["files"], incumbent_path, contained_by=target_root)
    if production != {incumbent_path} or EXERCISE["hypothesis_scope"] != [{"owner_id": EXERCISE["incumbent"]["production_authority_owner_id"], "path": incumbent_path, "content_root": incumbent_content}]:
        raise ValueError("candidate hypothesis does not bind the canonical target owner")
    for scope in lane["shared_resource_exclusions"]:
        expected_root = incumbent_content if scope["path"] == incumbent_path else root({"owner_id": scope["owner_id"], "path": scope["path"], "posture": "excluded"})
        if scope["content_root"] != expected_root:
            raise ValueError("shared-resource exclusion root differs")
    for scope in lane["isolated_writable_scope"]:
        if scope["content_root"] != root({"owner_id": scope["owner_id"], "path": scope["path"], "posture": "unmaterialized"}):
            raise ValueError("isolated pre-creation root differs")
    exact_string(EXERCISE["hypothesis"], "hypothesis")
    if EXERCISE["comparison_dimensions"] != DIMENSIONS:
        raise ValueError("comparison dimension order differs")
    eligibility_records = EXERCISE["eligibility_evidence"]
    if type(eligibility_records) is not dict or set(eligibility_records) != {"outcome_uncertainty", "implementation_evidence", "reversibility"}:
        raise ValueError("eligibility evidence differs")
    for record in eligibility_records.values():
        if type(record) is not dict:
            raise ValueError("eligibility evidence record differs")
    defaults = EXERCISE["eligibility_default"]
    if (defaults["outcome_uncertainty_evidence_root"], defaults["implementation_evidence_root"], defaults["reversibility_evidence_root"]) != (root(eligibility_records["outcome_uncertainty"]), root(eligibility_records["implementation_evidence"]), root(eligibility_records["reversibility"])):
        raise ValueError("eligibility evidence roots differ")
    implementation_evidence = eligibility_records["implementation_evidence"]
    if implementation_evidence.get("pre_run_contract_root") != pre_run["contract_root"] or implementation_evidence.get("representative_workload_root") != root(EXERCISE["representative_workload"]) or implementation_evidence.get("validation_runtime_root") != runtime_root or implementation_evidence.get("performance_protocol_root") != root(protocol) or implementation_evidence.get("materiality_criterion") != materiality:
        raise ValueError("implementation-evidence basis differs")
    validate_metrics(EXERCISE["incumbent"]["metrics"])
    if EXERCISE["incumbent"]["metrics"] != derived_incumbent_metrics():
        raise ValueError("incumbent metrics differ from retained bytes")
    if set(EXERCISE["incumbent"]) != {"revision", "production_authority_owner_id", "files", "metrics", "writable_scope"}:
        raise ValueError("candidate incumbent shape differs")
    incumbent_root()
    artifacts = EXERCISE["artifacts"]
    if type(artifacts) is not dict or not artifacts:
        raise ValueError("candidate artifacts differ")
    for artifact in artifacts.values():
        if type(artifact) is not dict or set(artifact) != {"revision", "files", "focused", "mapped"}:
            raise ValueError("candidate artifact shape differs")
        candidate = artifact_root(artifact)
        focused = focused_result(artifact, candidate)
        if parse_time(focused["recorded_at"], "focused time") <= implementation_started:
            raise ValueError("focused proof predates implementation start")
        mapped_result(artifact, candidate, focused)
    if type(EXERCISE["cases"]) is not list or len({case["case_id"] for case in EXERCISE["cases"]}) != len(EXERCISE["cases"]):
        raise ValueError("case identity differs")
    allowed_stops = {None, "incumbent-basis-drift", "focused-failure", "mapped-failure", "protected-regression", "review-currentness-loss", "cancelled", "isolation-drift", "hypothesis-falsified"}
    base_case_fields = {"case_id", "artifact_id", "eligibility", "usage", "stop_reason", "expected_action", "expected_comparison_disposition"}
    for case in EXERCISE["cases"]:
        if type(case) is not dict or (set(case) != base_case_fields and set(case) != base_case_fields | {"stop_evidence"}) or type(case["case_id"]) is not str or case["stop_reason"] not in allowed_stops:
            raise ValueError("candidate case shape differs")
        if case["artifact_id"] is not None and (type(case["artifact_id"]) is not str or case["artifact_id"] not in artifacts):
            raise ValueError("candidate case artifact differs")
    if set(REVIEW_FIXTURE) != {"schema_version", "kind", "source_posture", "reviewer_id", "reviewer_authority", "results"} or REVIEW_FIXTURE["schema_version"] != 2 or REVIEW_FIXTURE["kind"] != "software-factory-bounded-candidate-independent-review-fixture":
        raise ValueError("candidate review source shape differs")
    authority = REVIEW_FIXTURE["reviewer_authority"]
    if type(authority) is not dict or set(authority) != {"schema_version", "kind", "record_id", "reviewer_id", "source_revision", "source_review_posture"} or authority["reviewer_id"] != REVIEW_FIXTURE["reviewer_id"]:
        raise ValueError("candidate reviewer authority differs")
    if type(REVIEW_FIXTURE["results"]) is not list or len({item["input_root"] for item in REVIEW_FIXTURE["results"]}) != len(REVIEW_FIXTURE["results"]):
        raise ValueError("candidate review result identity differs")


def case_index() -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in EXERCISE["cases"]}


def canonical_case(case_id: str) -> dict[str, object]:
    validate_exercise()
    try:
        return copy.deepcopy(case_index()[case_id])
    except KeyError as error:
        raise ValueError("candidate case is absent") from error


def eligibility(case: dict[str, object]) -> dict[str, object]:
    override = case["eligibility"]
    if type(override) is not dict or not set(override).issubset(ELIGIBILITY_FIELDS):
        raise ValueError("eligibility override differs")
    value = {**EXERCISE["eligibility_default"], **override}
    if set(value) != ELIGIBILITY_FIELDS:
        raise ValueError("eligibility fields differ")
    for key in ("material_better_path", "outcome_uncertainty_supported", "implementation_evidence_required", "read_only_resolvable", "isolation_safe"):
        if type(value[key]) is not bool:
            raise ValueError(f"eligibility {key} differs")
    for key in ("trigger_evidence_root", "outcome_uncertainty_evidence_root", "implementation_evidence_root", "reversibility_evidence_root"):
        exact_string(value[key], key, SHA_RE)
    for key in ("rework_avoided_minutes", "candidate_ceiling_minutes", "review_ceiling_minutes", "isolation_recovery_minutes"):
        exact_int(value[key], key, maximum=120)
    if value["candidate_ceiling_minutes"] != EXERCISE["lane"]["time_ceiling_minutes"]:
        raise ValueError("eligibility candidate ceiling differs")
    if value["reversibility_posture"] != "checkpoint-restore":
        raise ValueError("eligibility reversibility differs")
    value["bounded_cost_minutes"] = value["candidate_ceiling_minutes"] + value["review_ceiling_minutes"] + value["isolation_recovery_minutes"]
    value["net_avoidable_minutes"] = value["rework_avoided_minutes"] - value["bounded_cost_minutes"]
    value["eligibility_root"] = root(value)
    return value


def lane_eligible(value: dict[str, object]) -> bool:
    return bool(value["material_better_path"] and value["outcome_uncertainty_supported"] and value["implementation_evidence_required"] and not value["read_only_resolvable"] and value["isolation_safe"] and value["net_avoidable_minutes"] > 0)


def candidate_root_for(case: dict[str, object]) -> tuple[dict[str, object], str]:
    artifact_id = case["artifact_id"]
    if type(artifact_id) is not str or artifact_id not in EXERCISE["artifacts"]:
        raise ValueError("candidate artifact is absent")
    artifact = EXERCISE["artifacts"][artifact_id]
    return artifact, artifact_root(artifact)


def decision_basis(case: dict[str, object], eligible: dict[str, object]) -> dict[str, object]:
    contract = EXERCISE["capability_contract"]
    incumbent = EXERCISE["incumbent"]
    return {
        "candidate_trigger": EXERCISE["candidate_trigger"],
        "tracker_sha256": EXERCISE["tracker_sha256"],
        "block_contract_root": EXERCISE["block_contract_root"],
        "target_repository_root": EXERCISE["target_repository_root"],
        "target_revision": EXERCISE["target_revision"],
        "target_revision_root": target_revision_root(),
        "incumbent_revision": incumbent["revision"],
        "incumbent_root": incumbent_root(),
        "hypothesis": EXERCISE["hypothesis"],
        "hypothesis_scope": EXERCISE["hypothesis_scope"],
        "capability_contract": contract,
        "expected_observable_effect": contract["expected_observable_effect"],
        "pre_run_contract_root": pre_run_contract_root(),
        "representative_workload_root": root(EXERCISE["representative_workload"]),
        "validation_runtime_root": validation_runtime_root(),
        "performance_protocol_root": root(EXERCISE["performance_protocol"]),
        "materiality_criterion": EXERCISE["materiality_criterion"],
        "comparison_dimensions": DIMENSIONS,
        "eligibility_root": eligible["eligibility_root"],
        "isolation": EXERCISE["lane"],
    }


def source_evidence(case: dict[str, object], eligible: dict[str, object]) -> list[dict[str, object]]:
    refs = [
        {"ref_id": "evidence-capability", "source_class": "tracker", "adjudication_posture": "adjudicating", "root_sha256": root(EXERCISE["capability_contract"]), "claim_ids": sorted(["bounded-candidate", "capability-contract", "generalized-service", "protected-contract", "semantic-roundtrip", "stable-bytes-api"])},
        {"ref_id": "evidence-eligibility", "source_class": "repository", "adjudication_posture": "adjudicating", "root_sha256": eligible["eligibility_root"], "claim_ids": sorted(["bounded-candidate", "implementation-evidence-required", "material-better-path", "positive-decision-value", "reversibility-bound"])},
        {"ref_id": "evidence-incumbent", "source_class": "repository", "adjudication_posture": "adjudicating", "root_sha256": incumbent_root(), "claim_ids": sorted(["incumbent-authoritative", "incumbent-local", "incumbent-revision"])},
        {"ref_id": "evidence-reviewer-authority", "source_class": "independent-review", "adjudication_posture": "process", "root_sha256": root(REVIEW_FIXTURE["reviewer_authority"]), "claim_ids": [EXERCISE["lane"]["independent_reviewer_id"]]},
    ]
    return sorted(refs, key=lambda item: item["ref_id"])


def fingerprint_projection(case: dict[str, object], eligible: dict[str, object]) -> dict[str, object]:
    evidence = source_evidence(case, eligible)
    adjudicating = [item for item in evidence if item["adjudication_posture"] == "adjudicating"]
    scope = copy.deepcopy(EXERCISE["hypothesis_scope"])
    paths = [
        {"path_id": "incumbent-local", "kind": "local", "posture": "rejected", "rationale": "read-only evidence cannot decide", "evidence_ref_ids": ["evidence-incumbent"]},
        {"path_id": "bounded-candidate", "kind": "bounded-general", "posture": "selected", "rationale": "one isolated implementation supplies the missing evidence", "evidence_ref_ids": ["evidence-capability", "evidence-eligibility"]},
        {"path_id": "generalized-service", "kind": "architectural-owner", "posture": "rejected", "rationale": "unsupported generalized experiment infrastructure", "evidence_ref_ids": ["evidence-capability"]},
    ]
    basis = decision_basis(case, eligible)
    values = {
        "schema_version": 1,
        "mission_root": EXERCISE["mission_root"],
        "authority_effect": "none",
        "authority_claim_id": None,
        "authority_evidence_refs": [],
        "prior_mission_root": EXERCISE["mission_root"],
        "proposed_mission_root": None,
        "tracker_path": f"{EXERCISE['target_repository_root']}/BLOCK.md",
        "block_number": 6,
        "block_contract_root": EXERCISE["block_contract_root"],
        "target_class": "target-repository",
        "target_repository_root": EXERCISE["target_repository_root"],
        "decision_target_state_root": root(basis),
        "capability_statement": EXERCISE["capability_contract"]["statement"],
        "capability_frame_root": root(EXERCISE["capability_contract"]),
        "protected_capability_results": [{"capability_id": item, "result": "preserved", "evidence_ref_ids": ["evidence-capability"]} for item in EXERCISE["capability_contract"]["protected_capabilities"]],
        "adjudicating_evidence_ref_ids": [item["ref_id"] for item in adjudicating],
        "adjudicating_evidence_root": root(adjudicating),
        "compared_paths": paths,
        "affected_scope": scope,
        "proposer_author_id": None,
        "implementation_owner_id": EXERCISE["lane"]["implementation_owner_id"],
        "stop_boundary": "before Block 9 cutover, tracker amendment, policy change, publication, or external release",
    }
    if set(values) != set(SPEC["fingerprint_projection"]):
        raise ValueError("fingerprint projection differs from Block 4")
    return values


def decision_fingerprint(case: dict[str, object], eligible: dict[str, object]) -> str:
    common = fingerprint_projection(case, eligible)
    candidate = candidate_fields(None, None, None, None, "active-isolated")
    candidate_projection = {key: candidate[key] for key in SPEC["candidate_fingerprint_projection"]}
    return root({**common, "candidate": candidate_projection})


def metric_relation(dimension: str, incumbent: dict[str, object], candidate: dict[str, object]) -> tuple[str, str]:
    if dimension == "observable-outcome":
        if candidate["decompressed_sha256"] != incumbent["decompressed_sha256"]:
            return "incumbent-better", "roundtrip-sha256-artifact-bytes-and-runtime"
        if candidate["artifact_bytes"] is None:
            return "inconclusive", "roundtrip-sha256-artifact-bytes-and-runtime"
        if candidate["performance_posture"] == "candidate-materially-slower":
            return "incumbent-better", "roundtrip-sha256-artifact-bytes-and-runtime"
        if candidate["performance_posture"] != "candidate-not-materially-slower" or incumbent["performance_posture"] != "baseline":
            return "inconclusive", "roundtrip-sha256-artifact-bytes-and-runtime"
        reduction = incumbent["artifact_bytes"] - candidate["artifact_bytes"]
        basis_points = (reduction * 10000) // incumbent["artifact_bytes"]
        criterion = EXERCISE["materiality_criterion"]
        if reduction >= criterion["minimum_artifact_byte_reduction"] and basis_points >= criterion["minimum_reduction_basis_points"]:
            return "candidate-better", "roundtrip-sha256-artifact-bytes-and-runtime"
        if reduction < 0:
            return "incumbent-better", "roundtrip-sha256-artifact-bytes-and-runtime"
        return "equivalent", "roundtrip-sha256-artifact-bytes-and-runtime"
    field = {"implementation-cost": "changed_lines", "maintenance-cost": "decision_points", "reversibility": "restore_steps"}.get(dimension)
    if field is not None:
        left, right = incumbent[field], candidate[field]
        relation = "candidate-better" if right < left else "incumbent-better" if right > left else "equivalent"
        return relation, field
    field = "api_break_ids" if dimension == "compatibility" else "regression_ids"
    left = incumbent[field]
    right = candidate[field]
    if right is None:
        return "inconclusive", field
    if left is None:
        return "inconclusive", field
    left_set, right_set = set(left), set(right)
    if right_set - left_set:
        return "incumbent-better", field
    if left_set - right_set:
        return "candidate-better", field
    return "equivalent", field


def comparison_records(mapped: dict[str, object]) -> list[dict[str, object]]:
    if mapped["exit_code"] != 0 or mapped["metrics"] is None:
        raise ValueError("mapped comparison is not coherent")
    incumbent_metrics = EXERCISE["incumbent"]["metrics"]
    candidate_metrics = mapped["metrics"]
    records: list[dict[str, object]] = []
    for dimension in DIMENSIONS:
        relation, unit = metric_relation(dimension, incumbent_metrics[dimension], candidate_metrics[dimension])
        if relation not in RELATIONS:
            raise ValueError("comparison relation differs")
        records.append({
            "dimension": dimension,
            "unit": unit,
            "incumbent_evidence_root": root({"incumbent_root": incumbent_root(), "dimension": dimension, "value": incumbent_metrics[dimension]}),
            "candidate_evidence_root": root({"candidate_root": mapped["candidate_root"], "mapped_result_root": mapped["result_root"], "dimension": dimension, "value": candidate_metrics[dimension]}),
            "incumbent_value": copy.deepcopy(incumbent_metrics[dimension]),
            "candidate_value": copy.deepcopy(candidate_metrics[dimension]),
            "relation": relation,
        })
    validate_comparison(records, mapped)
    return records


def validate_comparison(records: object, mapped: dict[str, object] | None = None) -> None:
    if type(records) is not list or [item.get("dimension") for item in records if type(item) is dict] != DIMENSIONS:
        raise ValueError("comparison dimensions differ")
    exact = {"dimension", "unit", "incumbent_evidence_root", "candidate_evidence_root", "incumbent_value", "candidate_value", "relation"}
    for record in records:
        if type(record) is not dict or set(record) != exact:
            raise ValueError("comparison record shape differs")
        exact_string(record["unit"], "comparison unit")
        exact_string(record["incumbent_evidence_root"], "incumbent evidence", SHA_RE)
        exact_string(record["candidate_evidence_root"], "candidate evidence", SHA_RE)
        if record["relation"] not in RELATIONS:
            raise ValueError("comparison relation differs")
    if mapped is not None:
        if mapped["metrics"] is None:
            raise ValueError("comparison lacks mapped metrics")
        for record in records:
            dimension = record["dimension"]
            expected_relation, expected_unit = metric_relation(dimension, EXERCISE["incumbent"]["metrics"][dimension], mapped["metrics"][dimension])
            expected_incumbent_root = root({"incumbent_root": incumbent_root(), "dimension": dimension, "value": EXERCISE["incumbent"]["metrics"][dimension]})
            expected_candidate_root = root({"candidate_root": mapped["candidate_root"], "mapped_result_root": mapped["result_root"], "dimension": dimension, "value": mapped["metrics"][dimension]})
            if (record["unit"], record["relation"], record["incumbent_evidence_root"], record["candidate_evidence_root"], record["incumbent_value"], record["candidate_value"]) != (expected_unit, expected_relation, expected_incumbent_root, expected_candidate_root, EXERCISE["incumbent"]["metrics"][dimension], mapped["metrics"][dimension]):
                raise ValueError("comparison record does not bind retained evidence")


def blind_review_packet(candidate_root: str, mapped: dict[str, object], comparison: list[dict[str, object]]) -> dict[str, object]:
    packet = {
        "schema_version": 1,
        "kind": "software-factory-bounded-candidate-blind-review-input",
        "target_revision_root": target_revision_root(),
        "incumbent_root": incumbent_root(),
        "candidate_root": candidate_root,
        "pre_run_contract_root": pre_run_contract_root(),
        "lane_execution_root": root(EXERCISE["lane_execution"]),
        "representative_workload_root": root(EXERCISE["representative_workload"]),
        "validation_runtime_root": validation_runtime_root(),
        "materiality_criterion": EXERCISE["materiality_criterion"],
        "focused_result_root": mapped["focused_result_root"],
        "performance_result_root": mapped["performance_result_root"],
        "mapped_result_root": mapped["result_root"],
        "comparison_root": root(comparison),
        "comparison_dimensions": DIMENSIONS,
        "capability_frame_root": root(EXERCISE["capability_contract"]),
        "protected_capabilities": EXERCISE["capability_contract"]["protected_capabilities"],
    }
    if any(key in packet for key in ("expected_action", "expected_comparison_disposition", "implementer_preference", "case_id")):
        raise ValueError("blind review input leaks implementer preference")
    return packet


def review_fixture_result(packet: dict[str, object], comparison: list[dict[str, object]] | None) -> dict[str, object]:
    input_root = root(packet)
    entries = [item for item in REVIEW_FIXTURE["results"] if type(item) is dict and item.get("input_root") == input_root]
    if len(entries) != 1 or REVIEW_FIXTURE["reviewer_id"] != EXERCISE["lane"]["independent_reviewer_id"]:
        raise ValueError("independent review fixture differs")
    entry = copy.deepcopy(entries[0])
    expected_fields = {"schema_version", "kind", "review_id", "reviewer_id", "input_root", "recorded_at", "comparison_disposition", "review_disposition", "retirement_posture", "result_root"}
    if set(entry) != expected_fields or entry["schema_version"] != 1 or entry["kind"] != "software-factory-bounded-candidate-independent-review" or entry["reviewer_id"] != REVIEW_FIXTURE["reviewer_id"]:
        raise ValueError("independent review result shape differs")
    recorded_root = entry.pop("result_root")
    if recorded_root != root(entry):
        raise ValueError("independent review result root differs")
    entry["review_root"] = recorded_root
    parse_time(entry["recorded_at"], "review time")
    disposition = entry["comparison_disposition"]
    if comparison is not None:
        validate_comparison(comparison)
        if packet["comparison_root"] != root(comparison):
            raise ValueError("review input does not bind raw comparison")
        if disposition not in COMPARISON_DISPOSITIONS:
            raise ValueError("comparison disposition differs")
        relations = {item["dimension"]: item["relation"] for item in comparison}
        values = {item["dimension"]: item["candidate_value"] for item in comparison}
        criterion = packet["materiality_criterion"]
        candidate_within_bounded_cost = (
            values["implementation-cost"]["changed_lines"] <= criterion["maximum_changed_lines"]
            and values["reversibility"]["restore_steps"] <= criterion["maximum_restore_steps"]
        )
        if disposition == "candidate-better" and (
            relations["observable-outcome"] != "candidate-better"
            or relations["maintenance-cost"] in {"incumbent-better", "inconclusive"}
            or relations["compatibility"] in {"incumbent-better", "inconclusive"}
            or relations["protected-capability"] in {"incumbent-better", "inconclusive"}
            or not candidate_within_bounded_cost
        ):
            raise ValueError("candidate-better is unsupported by material raw comparison")
        if disposition == "incumbent-better" and "incumbent-better" not in relations.values():
            raise ValueError("incumbent-better is unsupported by raw comparison")
        if disposition == "non-inferior-no-benefit" and ("candidate-better" in relations.values() or "inconclusive" in relations.values()):
            raise ValueError("non-inferior disposition differs from raw comparison")
        if disposition == "inconclusive" and "inconclusive" not in relations.values():
            raise ValueError("inconclusive disposition differs from raw comparison")
        if entry["review_disposition"] != BLOCK4_REVIEW[disposition] or entry["retirement_posture"] != RETIREMENT[disposition]:
            raise ValueError("review disposition mapping differs")
    elif disposition is not None or entry["review_disposition"] not in {"rejected", "inconclusive"}:
        raise ValueError("Stop review disposition differs")
    return entry


def stop_review_packet(case: dict[str, object], candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, stop_reason: str, usage: dict[str, int], cause: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "software-factory-bounded-candidate-stop-review-input",
        "target_revision_root": target_revision_root(),
        "incumbent_root": incumbent_root(),
        "candidate_root": candidate_root,
        "focused_result_root": focused["result_root"],
        "mapped_result_root": mapped["result_root"] if mapped else None,
        "stop_reason": stop_reason,
        "cause_root": root(cause),
        "resource_usage": usage,
        "resource_ceiling": EXERCISE["lane"]["resource_ceiling"],
        "time_ceiling_minutes": EXERCISE["lane"]["time_ceiling_minutes"],
        "incumbent_authoritative": True,
        "candidate_authoritative": False,
    }


def control_stop_result(artifact: dict[str, object], candidate_root: str, reason: str, cause: dict[str, object]) -> dict[str, object]:
    value = {
        "schema_version": 1,
        "kind": "software-factory-candidate-focused-result",
        "result_id": result_id("focused", candidate_root),
        "candidate_root": candidate_root,
        "pre_run_contract_root": pre_run_contract_root(),
        "lane_execution_root": root(EXERCISE["lane_execution"]),
        "representative_workload_root": root(EXERCISE["representative_workload"]),
        "validation_runtime_root": validation_runtime_root(),
        "recorded_at": exact_string(artifact["focused"]["recorded_at"], "control Stop time"),
        "command": "control:pre-validation-stop",
        "exit_code": 1,
        "output_sha256": root({"reason": reason, "cause": cause}),
        "protected_result": "not-run",
    }
    parse_time(value["recorded_at"], "control Stop time")
    value["result_root"] = root(value)
    return value


def stop_cause(case: dict[str, object], artifact: dict[str, object], candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, usage: dict[str, int], reason: str) -> dict[str, object]:
    if reason == "ceiling-expired":
        ceiling = EXERCISE["lane"]["resource_ceiling"]
        exceeded = sorted(key for key in ("files", "changed_lines", "commands", "review_passes") if usage[key] > ceiling[f"max_{key}"])
        if usage["elapsed_minutes"] > EXERCISE["lane"]["time_ceiling_minutes"]:
            exceeded.append("elapsed_minutes")
        if not exceeded:
            raise ValueError("ceiling Stop lacks an exceeded resource")
        return {"reason": reason, "exceeded": exceeded, "usage": usage, "resource_ceiling": ceiling, "time_ceiling_minutes": EXERCISE["lane"]["time_ceiling_minutes"]}
    supplied = case.get("stop_evidence")
    if reason == "incumbent-basis-drift":
        if type(supplied) is not dict or set(supplied) != {"observed_incumbent"} or type(supplied["observed_incumbent"]) is not dict:
            raise ValueError("incumbent drift evidence differs")
        observed = supplied["observed_incumbent"]
        if set(observed) != {"schema_version", "kind", "revision", "files"} or observed["schema_version"] != 1 or observed["kind"] != "software-factory-candidate-incumbent-observation":
            raise ValueError("incumbent observation shape differs")
        revision = exact_string(observed["revision"], "observed incumbent revision", REV_RE)
        observed_root = root({"revision": revision, "files": file_manifest(observed["files"], contained_by=EXERCISE["target_repository_root"])})
        if observed_root == incumbent_root():
            raise ValueError("incumbent drift evidence is unchanged")
        return {"reason": reason, "expected_incumbent_root": incumbent_root(), "observed_incumbent": observed, "observed_incumbent_record_root": root(observed), "observed_incumbent_root": observed_root}
    if reason == "cancelled":
        if type(supplied) is not dict or set(supplied) != {"cancellation_authority"} or type(supplied["cancellation_authority"]) is not dict:
            raise ValueError("cancellation evidence differs")
        authority = supplied["cancellation_authority"]
        if set(authority) != {"schema_version", "kind", "record_id", "authority_class", "reason"} or authority["schema_version"] != 1 or authority["kind"] != "software-factory-candidate-cancellation" or authority["authority_class"] != "repository-policy":
            raise ValueError("cancellation authority shape differs")
        exact_string(authority["record_id"], "cancellation record", ID_RE)
        exact_string(authority["reason"], "cancellation reason")
        return {"reason": reason, "cancellation_authority": authority, "cancellation_authority_root": root(authority)}
    if reason == "isolation-drift":
        expected = root(EXERCISE["lane"]["isolated_writable_scope"])
        if type(supplied) is not dict or set(supplied) != {"observed_isolation_scope"}:
            raise ValueError("isolation drift evidence differs")
        observed = validate_scope_refs(supplied["observed_isolation_scope"], "observed isolation scope", contained_by=EXERCISE["lane"]["root"], min_items=1)
        observed_root = root(observed)
        if observed_root == expected:
            raise ValueError("isolation drift evidence is unchanged")
        return {"reason": reason, "expected_isolation_root": expected, "observed_isolation_scope": observed, "observed_isolation_root": observed_root}
    if reason == "focused-failure":
        if focused["exit_code"] == 0:
            raise ValueError("focused failure evidence differs")
        return {"reason": reason, "focused_result_root": focused["result_root"], "exit_code": focused["exit_code"]}
    if reason == "protected-regression":
        observed = execute_stream(artifact["files"], contained_by=EXERCISE["lane"]["root"])
        if not observed["regression_ids"]:
            raise ValueError("protected regression evidence differs")
        return {"reason": reason, "focused_result_root": focused["result_root"], "regression_ids": observed["regression_ids"]}
    if reason == "mapped-failure":
        if mapped is None or mapped["exit_code"] == 0:
            raise ValueError("mapped failure evidence differs")
        return {"reason": reason, "focused_result_root": focused["result_root"], "mapped_result_root": mapped["result_root"], "exit_code": mapped["exit_code"]}
    if reason in {"hypothesis-falsified", "review-currentness-loss"}:
        if mapped is None or mapped["metrics"] is None:
            raise ValueError("post-comparison Stop lacks mapped evidence")
        comparison = comparison_records(mapped)
        comparison_root = root(comparison)
        if reason == "hypothesis-falsified":
            if any(item["dimension"] == "observable-outcome" and item["relation"] == "candidate-better" for item in comparison):
                raise ValueError("hypothesis falsification is unsupported")
            return {"reason": reason, "comparison_root": comparison_root}
        expected_input = root(blind_review_packet(candidate_root, mapped, comparison))
        if type(supplied) is not dict or set(supplied) != {"observed_review_input"} or type(supplied["observed_review_input"]) is not dict:
            raise ValueError("review currentness evidence differs")
        observed = supplied["observed_review_input"]
        if set(observed) != {"schema_version", "kind", "target_revision", "posture"} or observed["schema_version"] != 1 or observed["kind"] != "software-factory-candidate-review-input-observation" or observed["posture"] != "stale-target-basis":
            raise ValueError("review input observation differs")
        exact_string(observed["target_revision"], "observed review target revision", REV_RE)
        observed_root = root(observed)
        if observed_root == expected_input:
            raise ValueError("review currentness evidence is unchanged")
        return {"reason": reason, "expected_review_input_root": expected_input, "observed_review_input": observed, "observed_review_input_root": observed_root}
    raise ValueError("unknown candidate Stop reason")


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def candidate_fields(candidate_root: str | None, focused: dict[str, object] | None, mapped: dict[str, object] | None, review: dict[str, object] | None, retirement: str) -> dict[str, object]:
    isolated = copy.deepcopy(EXERCISE["lane"]["isolated_writable_scope"])
    values = {
        "hypothesis": EXERCISE["hypothesis"],
        "hypothesis_scope": copy.deepcopy(EXERCISE["hypothesis_scope"]),
        "incumbent_root": incumbent_root(),
        "candidate_root": candidate_root,
        "isolation_kind": EXERCISE["lane"]["isolation_kind"],
        "isolated_writable_scope": isolated,
        "shared_resource_exclusions": copy.deepcopy(EXERCISE["lane"]["shared_resource_exclusions"]),
        "resource_ceiling": "files<=3;changed-lines<=120;commands<=6;review-passes<=1",
        "time_ceiling": "elapsed-minutes<=20",
        "stop_condition": EXERCISE["lane"]["stop_condition"],
        "production_authority_owner_id": EXERCISE["incumbent"]["production_authority_owner_id"],
        "focused_validation": ["focused-compressed-export-v1"],
        "mapped_validation": ["mapped-compressed-export-v1"],
        "validation_order": "focused-then-mapped",
        "comparison_dimensions": DIMENSIONS,
        "independent_reviewer_id": EXERCISE["lane"]["independent_reviewer_id"],
        "review_root": review["review_root"] if review else None,
        "review_disposition": review["review_disposition"] if review else None,
        "cutover_owner_id": EXERCISE["lane"]["cutover_owner_id"],
        "cutover_preconditions": ["block-9", "current-review", "current-target", "single-authority"],
        "retirement_posture": retirement,
    }
    validate_candidate_fields(values)
    return values


def validate_candidate_fields(values: dict[str, object]) -> None:
    if set(values) != set(SPEC["candidate_fields"]):
        raise ValueError("candidate field set differs from Block 4")
    for key in ("incumbent_root",):
        exact_string(values[key], key, SHA_RE)
    if values["candidate_root"] is not None:
        exact_string(values["candidate_root"], "candidate root", SHA_RE)
    for key in ("hypothesis", "resource_ceiling", "time_ceiling", "stop_condition"):
        exact_string(values[key], key)
    if values["isolation_kind"] not in SPEC["enums"]["isolation-kind"]:
        raise ValueError("candidate isolation kind differs")
    for key in ("production_authority_owner_id", "independent_reviewer_id", "cutover_owner_id"):
        exact_string(values[key], key, ID_RE)
    for key, minimum in (("focused_validation", 1), ("mapped_validation", 0), ("cutover_preconditions", 1)):
        refs = values[key]
        if type(refs) is not list or len(refs) < minimum or refs != sorted(set(refs)) or any(type(ref) is not str or ID_RE.fullmatch(ref) is None for ref in refs):
            raise ValueError(f"candidate {key} differs")
    if values["validation_order"] != "focused-then-mapped" or values["comparison_dimensions"] != DIMENSIONS:
        raise ValueError("candidate validation/comparison order differs")
    if values["review_root"] is not None:
        exact_string(values["review_root"], "review root", SHA_RE)
    if values["review_disposition"] is not None and values["review_disposition"] not in SPEC["enums"]["review-disposition"]:
        raise ValueError("candidate review disposition differs")
    if values["retirement_posture"] not in SPEC["enums"]["retirement-posture"]:
        raise ValueError("candidate retirement posture differs")
    validate_scope_refs(values["hypothesis_scope"], "hypothesis scope", contained_by=EXERCISE["target_repository_root"], min_items=1)
    validate_scope_refs(values["isolated_writable_scope"], "isolated scope", contained_by=EXERCISE["lane"]["root"], min_items=1)
    validate_scope_refs(values["shared_resource_exclusions"], "shared exclusions", contained_by=EXERCISE["target_repository_root"], min_items=0)


def resource_usage_root(usage: dict[str, int]) -> str:
    return root({
        "resource_usage": usage,
        "resource_ceiling": EXERCISE["lane"]["resource_ceiling"],
        "time_ceiling_minutes": EXERCISE["lane"]["time_ceiling_minutes"],
    })


def process_evidence(stage: str, decision_id: str, candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, review: dict[str, object], current_state_root: str, target_root: str, usage: dict[str, int]) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    if stage in {"validated", "reviewed", "cutover-eligible", "closed"}:
        validation_root = root({"focused_result_root": focused["result_root"], "mapped_result_root": mapped["result_root"] if mapped and stage != "validated" else None})
        evidence.append({"ref_id": f"validation-{stage}", "source_class": "validation", "adjudication_posture": "process", "root_sha256": validation_root, "claim_ids": sorted([decision_id, candidate_root])})
        evidence.append({"ref_id": f"resource-{stage}", "source_class": "validation", "adjudication_posture": "process", "root_sha256": resource_usage_root(usage), "claim_ids": sorted([decision_id, candidate_root, "resource-usage"])})
    if stage in {"reviewed", "cutover-eligible", "closed"}:
        evidence.append({"ref_id": f"review-{stage}", "source_class": "independent-review", "adjudication_posture": "process", "root_sha256": review["review_root"], "claim_ids": sorted([decision_id, candidate_root, review["reviewer_id"], review["review_disposition"]])})
    if stage in {"cutover-eligible", "closed"}:
        evidence.append({"ref_id": f"outcome-{stage}", "source_class": "observed-outcome", "adjudication_posture": "current-outcome", "root_sha256": root({"incumbent_authoritative": True, "candidate_authoritative": False, "candidate_root": candidate_root, "target_revision_root": target_root}), "claim_ids": sorted([decision_id, current_state_root, target_root, candidate_root])})
    return evidence


def currentness_projection(record: dict[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    for field in SPEC["currentness_projection"]:
        optional = field.endswith("?")
        key = field[:-1] if optional else field
        if optional and key not in {"candidate_root", "review_root", "review_disposition", "retirement_posture"}:
            continue
        values[key] = record[key]
    return values


def validate_stage_record(record: dict[str, object]) -> None:
    if set(record) != set(SPEC["common_fields"]) | set(SPEC["candidate_fields"]):
        raise ValueError("candidate stage record differs from Block 4")
    if record["target_revision_root"] != root({"target_revision": record["target_revision"]}):
        raise ValueError("candidate target revision root differs")
    evidence = record["evidence_refs"]
    if type(evidence) is not list or evidence != sorted(evidence, key=lambda item: item["ref_id"]):
        raise ValueError("candidate evidence order differs")
    index = {item["ref_id"]: item for item in evidence}
    if len(index) != len(evidence) or record["evidence_manifest_root"] != root(evidence):
        raise ValueError("candidate evidence manifest differs")
    for item in evidence:
        if type(item) is not dict or set(item) != {"ref_id", "source_class", "adjudication_posture", "root_sha256", "claim_ids"}:
            raise ValueError("candidate evidence shape differs")
        exact_string(item["ref_id"], "evidence id", ID_RE)
        exact_string(item["root_sha256"], "evidence root", SHA_RE)
        if type(item["claim_ids"]) is not list or item["claim_ids"] != sorted(set(item["claim_ids"])):
            raise ValueError("candidate evidence claims differ")
    for protected in record["protected_capability_results"]:
        for ref_id in protected["evidence_ref_ids"]:
            if ref_id not in index or protected["capability_id"] not in index[ref_id]["claim_ids"]:
                raise ValueError("protected capability evidence is unbound")
    for path in record["compared_paths"]:
        for ref_id in path["evidence_ref_ids"]:
            if ref_id not in index or path["path_id"] not in index[ref_id]["claim_ids"]:
                raise ValueError("compared path evidence is unbound")
    adjudicating = sorted(item["ref_id"] for item in evidence if item["adjudication_posture"] == "adjudicating")
    if record["adjudicating_evidence_ref_ids"] != adjudicating or record["adjudicating_evidence_root"] != root([index[item] for item in adjudicating]):
        raise ValueError("adjudicating evidence differs")
    reviewer_evidence = [item for item in evidence if item["source_class"] == "independent-review" and record["reviewer_id"] in item["claim_ids"]]
    if not reviewer_evidence:
        raise ValueError("candidate reviewer identity is unbound")
    stage = record["decision_stage"]
    classes = {item["source_class"] for item in evidence}
    required = set(SPEC["stage_rules"]["required_evidence_source_classes"][stage])
    if stage == "closed":
        required.update(SPEC["stage_rules"]["closed_required_by_disposition"]["compare-candidate"])
    if not required.issubset(classes):
        raise ValueError("candidate stage evidence is incomplete")
    if stage in {"reviewed", "cutover-eligible", "closed"}:
        bound = [item for item in evidence if item["source_class"] == "independent-review" and item["root_sha256"] == record["review_root"] and all(record[field] in item["claim_ids"] for field in ("decision_id", "candidate_root", "reviewer_id", "review_disposition"))]
        if not bound:
            raise ValueError("candidate review evidence is unbound")
    if record["currentness_root"] != root(currentness_projection(record)):
        raise ValueError("candidate currentness differs")


def stage_records(case: dict[str, object], eligible: dict[str, object], candidate_root: str, focused: dict[str, object], mapped: dict[str, object] | None, review: dict[str, object], terminal_stage: str, usage: dict[str, int]) -> list[dict[str, object]]:
    fingerprint_values = fingerprint_projection(case, eligible)
    fingerprint = decision_fingerprint(case, eligible)
    base_evidence = source_evidence(case, eligible)
    focused_time = parse_time(focused["recorded_at"], "focused time")
    review_time = parse_time(review["recorded_at"], "review time")
    stages = ["selected", "implementing"]
    if focused["exit_code"] == 0 and focused["protected_result"] == "preserved":
        stages.append("validated")
    if review["comparison_disposition"] is not None:
        stages.append("reviewed")
    stages.append(terminal_stage)
    stages = list(dict.fromkeys(stages))
    records: list[dict[str, object]] = []
    previous: str | None = None
    lane_started = parse_time(EXERCISE["lane_execution"]["lane_started_at"], "lane start")
    implementation_started = parse_time(EXERCISE["lane_execution"]["implementation_started_at"], "implementation start")
    times = {"selected": lane_started, "implementing": implementation_started, "validated": focused_time, "reviewed": review_time, terminal_stage: review_time + timedelta(seconds=1)}
    for stage in stages:
        decision_id = f"candidate-{case['case_id']}-{stage}"
        candidate_is_observed = stage in {"validated", "reviewed", "cutover-eligible", "closed"}
        if stage == "validated":
            stage_usage = {
                "files": usage["files"],
                "changed_lines": usage["changed_lines"],
                "commands": 1,
                "review_passes": 0,
                "elapsed_minutes": max(1, math.ceil((focused_time - lane_started).total_seconds() / 60)),
            }
        else:
            stage_usage = usage
        current_state = root({"target_revision_root": target_revision_root(), "incumbent_root": incumbent_root(), "candidate_root": candidate_root if candidate_is_observed else None, "stage": stage, "candidate_authoritative": False, "resource_usage_root": resource_usage_root(stage_usage) if candidate_is_observed else None})
        evidence = sorted([*copy.deepcopy(base_evidence), *process_evidence(stage, decision_id, candidate_root, focused, mapped, review, current_state, target_revision_root(), stage_usage)], key=lambda item: item["ref_id"])
        terminal = stage == terminal_stage
        retirement = review["retirement_posture"] if terminal else "active-isolated"
        fields = candidate_fields(candidate_root if candidate_is_observed else None, focused if candidate_is_observed else None, mapped if stage in {"reviewed", "cutover-eligible", "closed"} else None, review if stage in {"reviewed", "cutover-eligible", "closed"} else None, retirement)
        record = {
            **fingerprint_values,
            **fields,
            "decision_id": decision_id,
            "decision_stage": stage,
            "disposition": "compare-candidate",
            "recorded_at": format_time(times[stage]),
            "predecessor_decision_id": None,
            "currentness_refresh_of": previous,
            "tracker_sha256": EXERCISE["tracker_sha256"],
            "target_revision": EXERCISE["target_revision"],
            "target_revision_root": target_revision_root(),
            "current_target_state_root": current_state,
            "evidence_refs": evidence,
            "evidence_manifest_root": root(evidence),
            "decision_fingerprint": fingerprint,
            "selected_path": "bounded-candidate",
            "rejected_paths": ["incumbent-local", "generalized-service"],
            "valid_work_refs": ["evidence-incumbent"],
            "stale_proof_refs": [],
            "safe_frontier": [],
            "adaptive_decision_mode": "full-autonomous",
            "reviewer_id": EXERCISE["lane"]["independent_reviewer_id"],
            "evaluator_id": None,
            "policy_root": EXERCISE["policy_root"],
            "event_head_root": EXERCISE["event_head_root"],
            "accepted_decision_head": None,
            "accepted_revision_head": None,
            "revisit_trigger": None,
            "external_boundary": None,
        }
        record["currentness_root"] = root(currentness_projection(record))
        validate_stage_record(record)
        common_projection = {key: record[key] for key in SPEC["fingerprint_projection"]}
        candidate_projection = {key: record[key] for key in SPEC["candidate_fingerprint_projection"]}
        if root({**common_projection, "candidate": candidate_projection}) != fingerprint:
            raise ValueError("candidate stage changed decision fingerprint")
        records.append(record)
        previous = decision_id
    allowed = SPEC["stage_rules"]["allowed_transitions"]
    for left, right in zip(records, records[1:]):
        if right["decision_stage"] not in allowed[left["decision_stage"]]:
            raise ValueError("candidate stage transition differs")
    return records


def handoff_record(records: list[dict[str, object]], comparison: list[dict[str, object]], review: dict[str, object], usage: dict[str, int]) -> dict[str, object]:
    final = records[-1]
    if final["decision_stage"] != "cutover-eligible" or final["retirement_posture"] != "eligible-cutover":
        raise ValueError("candidate is not handoff eligible")
    value = {
        "schema_version": 1,
        "kind": "software-factory-block9-cutover-handoff",
        "source_block": 6,
        "destination_block": 9,
        "decision_fingerprint": final["decision_fingerprint"],
        "currentness_root": final["currentness_root"],
        "target_revision_root": final["target_revision_root"],
        "incumbent_root": final["incumbent_root"],
        "candidate_root": final["candidate_root"],
        "review_root": final["review_root"],
        "comparison_root": root(comparison),
        "resource_usage": usage,
        "resource_usage_root": resource_usage_root(usage),
        "target_owner_id": final["cutover_owner_id"],
        "protected_capability_results": final["protected_capability_results"],
        "cutover_preconditions": final["cutover_preconditions"],
        "non_mutating": True,
        "cutover_authority": False,
        "publish_authority": False,
        "tracker_authority": False,
        "policy_authority": False,
    }
    value["handoff_id"] = f"block9-handoff-{root(value)[:20]}"
    value["handoff_root"] = root(value)
    return value


def accepted_lane_head(result: dict[str, object]) -> dict[str, object]:
    records = result["stage_records"]
    final = records[-1]
    value = {
        "schema_version": 1,
        "kind": "software-factory-accepted-candidate-lane-head",
        "tracker_sha256": EXERCISE["tracker_sha256"],
        "target_revision_root": target_revision_root(),
        "decision_fingerprint": result["decision_fingerprint"],
        "candidate_root": final["candidate_root"],
        "review_root": final["review_root"],
        "currentness_root": final["currentness_root"],
        "handoff_root": result["handoff"]["handoff_root"] if result["handoff"] else None,
        "resource_usage_root": resource_usage_root(result["resource_usage"]),
    }
    value["head_root"] = root(value)
    return value


def validate_accepted_head(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != {"schema_version", "kind", "tracker_sha256", "target_revision_root", "decision_fingerprint", "candidate_root", "review_root", "currentness_root", "handoff_root", "resource_usage_root", "head_root"}:
        raise ValueError("accepted lane head differs")
    raw = dict(value)
    recorded = raw.pop("head_root")
    if recorded != root(raw):
        raise ValueError("accepted lane head is stale")
    for key in ("tracker_sha256", "target_revision_root", "decision_fingerprint", "candidate_root", "review_root", "currentness_root", "resource_usage_root"):
        exact_string(value[key], key, SHA_RE)
    if value["handoff_root"] is not None:
        exact_string(value["handoff_root"], "handoff root", SHA_RE)
    return value


def verify_exact_review_signature() -> None:
    if (
        ACCEPTED_SNAPSHOT_PATH.is_symlink()
        or EXACT_REVIEW_PATH.is_symlink()
        or REVIEWER_AUTHORITY_ROOT.is_symlink()
        or not REVIEWER_AUTHORITY_ROOT.is_dir()
        or REVIEWER_AUTHORITY_ROOT.stat().st_mode & 0o222
        or REVIEWER_AUTHORITY_DIRECTORY.is_symlink()
        or not REVIEWER_AUTHORITY_DIRECTORY.is_dir()
        or REVIEWER_AUTHORITY_DIRECTORY.stat().st_mode & 0o222
        or REVIEWER_PUBLIC_KEY_PATH.is_symlink()
        or not REVIEWER_PUBLIC_KEY_PATH.is_file()
        or REVIEWER_PUBLIC_KEY_PATH.stat().st_mode & 0o222
        or hashlib.sha256(EXACT_REVIEW_BYTES).hexdigest() != EXPECTED_EXACT_REVIEW_SHA256
        or EXACT_REVIEW_BYTES != canonical(EXACT_REVIEW) + b"\n"
        or hashlib.sha256(REVIEWER_PUBLIC_KEY_PATH.read_bytes()).hexdigest() != EXPECTED_REVIEWER_KEY_SHA256
    ):
        raise ValueError("exact independent review bytes differ")
    root_material = {
        key: value
        for key, value in EXACT_REVIEW.items()
        if key not in {"evidence_root_sha256", "signature_base64"}
    }
    signed_material = {
        key: value for key, value in EXACT_REVIEW.items() if key != "signature_base64"
    }
    if EXACT_REVIEW.get("evidence_root_sha256") != root(root_material):
        raise ValueError("exact independent review root differs")
    if (
        TRUSTED_OPENSSL_PATH.is_symlink()
        or not TRUSTED_OPENSSL_PATH.is_file()
        or hashlib.sha256(TRUSTED_OPENSSL_PATH.read_bytes()).hexdigest() != TRUSTED_OPENSSL_SHA256
    ):
        raise ValueError("trusted signature verifier differs")
    try:
        signature = base64.b64decode(
            exact_string(EXACT_REVIEW.get("signature_base64"), "review signature"),
            validate=True,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("exact independent review signature differs") from error
    with tempfile.TemporaryDirectory(prefix="software-factory-block6-review-") as raw:
        temporary = Path(raw)
        material_path = temporary / "material.json"
        signature_path = temporary / "signature.bin"
        material_path.write_bytes(canonical(signed_material))
        signature_path.write_bytes(signature)
        result = subprocess.run(
            [
                str(TRUSTED_OPENSSL_PATH),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(REVIEWER_PUBLIC_KEY_PATH),
                "-rawin",
                "-in",
                str(material_path),
                "-sigfile",
                str(signature_path),
            ],
            check=False,
            capture_output=True,
        )
    if result.returncode:
        raise ValueError("exact independent review signature differs")


def validate_accepted_source_manifest(repo_root: Path) -> None:
    source_revision = exact_string(
        ACCEPTED_SNAPSHOT["source_revision"], "accepted source revision", REV_RE
    )
    source_files = ACCEPTED_SNAPSHOT["source_files"]
    if type(source_files) is not list or not source_files or len(source_files) > 16:
        raise ValueError("accepted source manifest differs")
    git_probe = subprocess.run(
        [GIT_EXECUTABLE, "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    git_available = git_probe.returncode == 0
    tracker_relative = "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
    seen_paths: set[str] = set()
    for entry in source_files:
        if type(entry) is not dict or set(entry) != {"path", "sha256"}:
            raise ValueError("accepted source entry differs")
        relative = exact_string(entry["path"], "accepted source path")
        expected_sha256 = exact_string(entry["sha256"], "accepted source root", SHA_RE)
        pure_relative = PurePosixPath(relative)
        if pure_relative.is_absolute() or any(part in {".", ".."} for part in pure_relative.parts):
            raise ValueError("accepted source path escapes repository")
        if relative in seen_paths:
            raise ValueError("accepted source path differs")
        seen_paths.add(relative)
        path = repo_root / relative
        if not path.exists():
            if (
                not git_available
                and relative == tracker_relative
                and expected_sha256 == ACCEPTED_SNAPSHOT["tracker_sha256"]
            ):
                continue
            raise ValueError("accepted source path differs")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(repo_root.resolve(strict=True))
        except (FileNotFoundError, ValueError) as error:
            raise ValueError("accepted source path escapes repository") from error
        if path.is_symlink() or resolved != repo_root.resolve(strict=True) / relative or not path.is_file():
            raise ValueError("accepted source path differs")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError("accepted source content changed")
        frozen = subprocess.run(
            [GIT_EXECUTABLE, "show", f"{source_revision}:{relative}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if frozen.returncode == 0:
            if hashlib.sha256(frozen.stdout).hexdigest() != expected_sha256:
                raise ValueError("accepted source revision differs")
        elif git_available:
            raise ValueError("accepted source revision cannot be resolved")


def validate_accepted_snapshot() -> dict[str, object]:
    expected_fields = {
        "schema_version",
        "kind",
        "record_id",
        "source_revision",
        "source_files",
        "exact_review",
        "exercise_root",
        "review_fixture_root",
        "pre_run_contract_root",
        "tracker_sha256",
        "case_id",
        "resource_usage",
        "handoff",
        "lane_head",
    }
    if (
        set(ACCEPTED_SNAPSHOT) != expected_fields
        or type(ACCEPTED_SNAPSHOT.get("schema_version")) is not int
        or ACCEPTED_SNAPSHOT["schema_version"] != 1
        or ACCEPTED_SNAPSHOT["kind"] != "software-factory-accepted-candidate-lane"
        or root(ACCEPTED_SNAPSHOT) != EXPECTED_ACCEPTED_SNAPSHOT_ROOT
    ):
        raise ValueError("accepted candidate snapshot differs")
    source_revision = exact_string(
        ACCEPTED_SNAPSHOT["source_revision"], "accepted source revision", REV_RE
    )
    validate_accepted_source_manifest(REPO_ROOT)
    review = ACCEPTED_SNAPSHOT["exact_review"]
    if type(review) is not dict or set(review) != {
        "record_id",
        "file_sha256",
        "evidence_root",
        "authority_key_sha256",
        "review_disposition",
        "finding_count",
    }:
        raise ValueError("accepted exact review identity differs")
    if review != {
        "record_id": EXACT_REVIEW["record_id"],
        "file_sha256": EXPECTED_EXACT_REVIEW_SHA256,
        "evidence_root": EXACT_REVIEW["evidence_root_sha256"],
        "authority_key_sha256": EXPECTED_REVIEWER_KEY_SHA256,
        "review_disposition": "accepted",
        "finding_count": 0,
    }:
        raise ValueError("accepted exact review identity differs")
    verify_exact_review_signature()
    lane_head = validate_accepted_head(ACCEPTED_SNAPSHOT["lane_head"])
    handoff = ACCEPTED_SNAPSHOT["handoff"]
    if type(handoff) is not dict or handoff.get("handoff_root") != lane_head["handoff_root"]:
        raise ValueError("accepted Block 9 handoff differs")
    raw_handoff = dict(handoff)
    handoff_root = raw_handoff.pop("handoff_root")
    if handoff_root != root(raw_handoff):
        raise ValueError("accepted Block 9 handoff is stale")
    resource_usage = ACCEPTED_SNAPSHOT["resource_usage"]
    if type(resource_usage) is not dict or set(resource_usage) != {
        "files",
        "changed_lines",
        "commands",
        "review_passes",
        "elapsed_minutes",
    }:
        raise ValueError("accepted resource usage differs")
    for key, value in resource_usage.items():
        exact_int(value, f"accepted usage {key}")
    result_roots = [item["result_root"] for item in REVIEW_FIXTURE["results"]]
    candidate_projection = EXACT_REVIEW["candidate_projection"]
    lifecycle = EXACT_REVIEW["winning_lifecycle"]
    if (
        ACCEPTED_SNAPSHOT["case_id"] != "winning-candidate"
        or ACCEPTED_SNAPSHOT["exercise_root"] != root(EXERCISE)
        or ACCEPTED_SNAPSHOT["review_fixture_root"] != root(REVIEW_FIXTURE)
        or ACCEPTED_SNAPSHOT["pre_run_contract_root"] != root(PRE_RUN)
        or ACCEPTED_SNAPSHOT["tracker_sha256"] != tracker_sha256()
        or lane_head["tracker_sha256"] != tracker_sha256()
        or lane_head["resource_usage_root"] != resource_usage_root(resource_usage)
        or handoff["resource_usage"] != resource_usage
        or handoff["resource_usage_root"] != lane_head["resource_usage_root"]
        or handoff["decision_fingerprint"] != lane_head["decision_fingerprint"]
        or handoff["candidate_root"] != lane_head["candidate_root"]
        or handoff["review_root"] != lane_head["review_root"]
        or handoff["currentness_root"] != lane_head["currentness_root"]
        or handoff["target_revision_root"] != lane_head["target_revision_root"]
        or EXACT_REVIEW["source_revision"] != source_revision
        or EXACT_REVIEW["exercise_root"] != ACCEPTED_SNAPSHOT["exercise_root"]
        or EXACT_REVIEW["review_fixture_root"] != ACCEPTED_SNAPSHOT["review_fixture_root"]
        or EXACT_REVIEW["pre_run_contract_root"] != ACCEPTED_SNAPSHOT["pre_run_contract_root"]
        or EXACT_REVIEW["review_disposition"] != "accepted"
        or EXACT_REVIEW["finding_count"] != 0
        or EXACT_REVIEW["external_result_roots"] != result_roots
        or type(candidate_projection) is not dict
        or candidate_projection.get("source_commit") != source_revision
        or candidate_projection.get("candidate_root_sha256") != EXACT_REVIEW["candidate_root_sha256"]
        or EXACT_REVIEW["reviewer_id"] != "software-factory-release-reviewer-v1"
        or EXACT_REVIEW["winning_candidate_root"] != lane_head["candidate_root"]
        or EXACT_REVIEW["winning_decision_fingerprint"] != lane_head["decision_fingerprint"]
        or EXACT_REVIEW["winning_review_root"] != lane_head["review_root"]
        or EXACT_REVIEW["winning_final_currentness_root"] != lane_head["currentness_root"]
        or EXACT_REVIEW["winning_handoff_root"] != lane_head["handoff_root"]
        or EXACT_REVIEW["winning_comparison_root"] != handoff["comparison_root"]
        or EXACT_REVIEW["winning_lane_head_root"] != lane_head["head_root"]
        or EXACT_REVIEW["winning_resource_usage"] != resource_usage
        or EXACT_REVIEW["winning_resource_usage_root"] != lane_head["resource_usage_root"]
        or type(lifecycle) is not list
        or not lifecycle
        or lifecycle[-1].get("currentness_root") != lane_head["currentness_root"]
        or lifecycle[-1].get("candidate_root") != lane_head["candidate_root"]
        or lifecycle[-1].get("review_root") != lane_head["review_root"]
    ):
        raise ValueError("accepted candidate evidence is not current")
    return copy.deepcopy(ACCEPTED_SNAPSHOT)


def artifact_changed_lines(files: object) -> int:
    if type(files) is not list:
        raise ValueError("candidate files differ")
    stream_path = f"{EXERCISE['lane']['root']}/stream_export.py"
    extra = sum(len(exact_string(item["content_utf8"], "candidate bytes").splitlines()) for item in files if item["path"] != stream_path)
    return changed_lines(files) + extra


def derived_usage(
    case: dict[str, object],
    artifact: dict[str, object],
    *,
    focused: dict[str, object] | None = None,
    mapped: dict[str, object] | None = None,
    review: dict[str, object] | None = None,
    prior_reviews: list[dict[str, object]] | None = None,
    compare_expected: bool = True,
) -> dict[str, int]:
    reason = case.get("stop_reason")
    files = artifact["files"]
    file_count = len(files)
    ceiling_hit = file_count > EXERCISE["lane"]["resource_ceiling"]["max_files"] or artifact_changed_lines(files) > EXERCISE["lane"]["resource_ceiling"]["max_changed_lines"]
    if ceiling_hit or reason in {"incumbent-basis-drift", "cancelled", "isolation-drift"}:
        commands = 0
    elif reason in {"focused-failure", "protected-regression"}:
        commands = 1
    else:
        commands = 2
    started = parse_time(EXERCISE["lane_execution"]["lane_started_at"], "lane start")
    if focused is None:
        last = started
        elapsed_minutes = 0
    else:
        last = parse_time(focused["recorded_at"], "focused time")
        if mapped is not None:
            last = parse_time(mapped["recorded_at"], "mapped time")
        reviews = [*(prior_reviews or []), *([review] if review is not None else [])]
        for item in reviews:
            review_time = parse_time(item["recorded_at"], "review time")
            if review_time <= last:
                raise ValueError("independent review does not follow retained producer evidence")
            last = review_time
        elapsed_minutes = max(1, math.ceil((last - started).total_seconds() / 60))
    value = {
        "files": file_count,
        "changed_lines": artifact_changed_lines(files),
        "commands": commands,
        "review_passes": len(prior_reviews or []) + (1 if review is not None else 0),
        "elapsed_minutes": elapsed_minutes,
    }
    if review is not None and compare_expected and case["usage"] != value:
        raise ValueError("candidate usage differs from retained artifacts")
    return value


def review_exceeds_ceiling(review: dict[str, object], producer: dict[str, object]) -> bool:
    review_time = parse_time(review["recorded_at"], "review time")
    producer_time = parse_time(producer["recorded_at"], "producer time")
    if review_time <= producer_time:
        raise ValueError("independent review does not follow retained producer evidence")
    return review_time - producer_time > timedelta(minutes=EXERCISE["eligibility_default"]["review_ceiling_minutes"])


def ceiling_exceeded(usage: dict[str, int]) -> bool:
    for key in usage:
        exact_int(usage[key], f"usage {key}")
    ceiling = EXERCISE["lane"]["resource_ceiling"]
    return usage["files"] > ceiling["max_files"] or usage["changed_lines"] > ceiling["max_changed_lines"] or usage["commands"] > ceiling["max_commands"] or usage["review_passes"] > ceiling["max_review_passes"] or usage["elapsed_minutes"] > EXERCISE["lane"]["time_ceiling_minutes"]


def evaluate_unaccepted(case_id: str, *, accepted_head: dict[str, object] | None = None) -> dict[str, object]:
    case = canonical_case(case_id)
    eligible = eligibility(case)
    fingerprint = decision_fingerprint(case, eligible)
    if not lane_eligible(eligible):
        return {"action": "reject-before-lane", "lane_created": False, "review_cycle": False, "decision_fingerprint": fingerprint, "eligibility": eligible}
    artifact, candidate_root = candidate_root_for(case)
    usage = derived_usage(case, artifact)
    if accepted_head is not None:
        raise ValueError("caller-supplied accepted lane heads are not authority")
    stop_reason = case["stop_reason"]
    if ceiling_exceeded(usage):
        stop_reason = "ceiling-expired"
    early_stop = stop_reason in {"ceiling-expired", "incumbent-basis-drift", "cancelled", "isolation-drift"}
    if early_stop:
        provisional_cause = {"reason": stop_reason, "usage": usage, "case_evidence": case.get("stop_evidence")}
        focused = control_stop_result(artifact, candidate_root, stop_reason, provisional_cause)
        mapped = None
    else:
        focused = focused_result(artifact, candidate_root)
        mapped = mapped_result(artifact, candidate_root, focused)
    usage = derived_usage(case, artifact, focused=focused, mapped=mapped)
    if ceiling_exceeded(usage):
        stop_reason = "ceiling-expired"
    if focused["exit_code"] != 0:
        if not early_stop:
            stop_reason = "focused-failure"
    if focused["protected_result"] == "regressed":
        stop_reason = "protected-regression"
    if mapped is not None and mapped["exit_code"] != 0:
        stop_reason = "mapped-failure"
    if stop_reason is not None:
        stop_reason = exact_string(stop_reason, "stop reason")
        cause = stop_cause(case, artifact, candidate_root, focused, mapped, usage, stop_reason)
        packet = stop_review_packet(case, candidate_root, focused, mapped, stop_reason, usage, cause)
        review = review_fixture_result(packet, None)
        usage = derived_usage(case, artifact, focused=focused, mapped=mapped, review=review)
        records = stage_records(case, eligible, candidate_root, focused, mapped, review, "closed", usage)
        return {"action": "stop-retire", "lane_created": True, "review_cycle": True, "decision_fingerprint": fingerprint, "stop_reason": stop_reason, "stop_cause": cause, "stop_review_packet": packet, "resource_usage": usage, "stage_records": records, "candidate_root": candidate_root, "candidate_authoritative": False, "incumbent_authoritative": True, "isolation_cleanup": "retired-non-authoritative", "retained_evidence": [focused["result_root"], *( [mapped["result_root"]] if mapped else []), review["review_root"]], "handoff": None, "cutover_performed": False, "tracker_mutated": False, "policy_mutated": False}
    if mapped is None or mapped["exit_code"] != 0 or mapped["metrics"] is None:
        raise ValueError("mapped result is absent after focused success")
    comparison = comparison_records(mapped)
    packet = blind_review_packet(candidate_root, mapped, comparison)
    review = review_fixture_result(packet, comparison)
    if review_exceeds_ceiling(review, mapped):
        late_usage = derived_usage(case, artifact, focused=focused, mapped=mapped, review=review, compare_expected=False)
        cause = {
            "reason": "review-ceiling-expired",
            "review_ceiling_minutes": EXERCISE["eligibility_default"]["review_ceiling_minutes"],
            "mapped_result_root": mapped["result_root"],
            "late_review_root": review["review_root"],
            "late_review_recorded_at": review["recorded_at"],
            "usage_at_detection": late_usage,
        }
        stop_packet = stop_review_packet(case, candidate_root, focused, mapped, "review-ceiling-expired", late_usage, cause)
        stop_review = review_fixture_result(stop_packet, None)
        usage = derived_usage(case, artifact, focused=focused, mapped=mapped, review=stop_review, prior_reviews=[review])
        records = stage_records(case, eligible, candidate_root, focused, mapped, stop_review, "closed", usage)
        return {"action": "stop-retire", "lane_created": True, "review_cycle": True, "decision_fingerprint": fingerprint, "stop_reason": "review-ceiling-expired", "stop_cause": cause, "stop_review_packet": stop_packet, "resource_usage": usage, "stage_records": records, "candidate_root": candidate_root, "candidate_authoritative": False, "incumbent_authoritative": True, "isolation_cleanup": "retired-non-authoritative", "retained_evidence": [focused["result_root"], mapped["result_root"], review["review_root"], stop_review["review_root"]], "handoff": None, "cutover_performed": False, "tracker_mutated": False, "policy_mutated": False}
    usage = derived_usage(case, artifact, focused=focused, mapped=mapped, review=review)
    if ceiling_exceeded(usage):
        raise ValueError("candidate review completed outside the resource ceiling")
    terminal = "cutover-eligible" if review["comparison_disposition"] == "candidate-better" else "closed"
    records = stage_records(case, eligible, candidate_root, focused, mapped, review, terminal, usage)
    handoff = handoff_record(records, comparison, review, usage) if terminal == "cutover-eligible" else None
    action = "handoff-block-9" if handoff else "retire-candidate"
    result = {"action": action, "lane_created": True, "review_cycle": True, "decision_fingerprint": fingerprint, "candidate_root": candidate_root, "focused_result": focused, "mapped_result": mapped, "resource_usage": usage, "raw_comparison_records": comparison, "blind_review_packet": packet, "review_result": review, "stage_records": records, "candidate_authoritative": False, "incumbent_authoritative": True, "isolation_cleanup": "kept-isolated-for-block-9" if handoff else "retired-non-authoritative", "handoff": handoff, "cutover_performed": False, "tracker_mutated": False, "policy_mutated": False}
    result["lane_head"] = accepted_lane_head(result)
    return result


def evaluate(case_id: str, *, accepted_head: dict[str, object] | None = None) -> dict[str, object]:
    """Evaluate current work, deduplicating only against the canonical accepted lane."""
    if accepted_head is not None:
        raise ValueError("caller-supplied accepted lane heads are not authority")
    if case_id == ACCEPTED_SNAPSHOT.get("case_id"):
        accepted = validate_accepted_snapshot()
        head = accepted["lane_head"]
        return {
            "action": "deduplicate",
            "lane_created": False,
            "review_cycle": False,
            "decision_fingerprint": head["decision_fingerprint"],
            "candidate_root": head["candidate_root"],
            "resource_usage": accepted["resource_usage"],
            "lane_head": head,
            "handoff": None,
            "existing_handoff": accepted["handoff"],
            "existing_handoff_root": accepted["handoff"]["handoff_root"],
            "candidate_authoritative": False,
            "incumbent_authoritative": True,
            "cutover_performed": False,
            "tracker_mutated": False,
            "policy_mutated": False,
            "next_action": "continue-with-existing-block-9-handoff",
        }
    case = canonical_case(case_id)
    eligible = eligibility(case)
    fingerprint = decision_fingerprint(case, eligible)
    if not lane_eligible(eligible):
        return evaluate_unaccepted(case_id)
    return evaluate_unaccepted(case_id)


class BoundedCandidateContractTests(unittest.TestCase):
    def test_strict_json_rejects_duplicates_floats_and_non_nfc(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads('{"schema_version":1,"schema_version":1}', object_pairs_hook=reject_duplicate_pairs)
        with self.assertRaisesRegex(ValueError, "RFC8785"):
            canonical({"value": 1.0})
        with self.assertRaisesRegex(ValueError, "NFC"):
            canonical({"value": "e\u0301"})

    def test_source_preflight_and_nonopaque_eligibility_include_reversibility(self) -> None:
        validate_exercise()
        self.assertEqual(root(PRE_RUN), EXPECTED_PRE_RUN_ROOT)
        self.assertEqual(EXERCISE["pre_run_contract"]["source_revision"], "c8b92ac48920b86587a1e39f5f16702de8b65554")
        self.assertEqual(EXERCISE["pre_run_contract"]["contract_root"], EXPECTED_PRE_RUN_ROOT)
        self.assertGreater(parse_time(EXERCISE["lane_execution"]["lane_started_at"], "lane start"), parse_time(PRE_RUN["created_at"], "pre-run creation"))
        self.assertGreater(parse_time(EXERCISE["lane_execution"]["implementation_started_at"], "implementation start"), parse_time(EXERCISE["lane_execution"]["lane_started_at"], "lane start"))
        positive = eligibility(canonical_case("winning-candidate"))
        self.assertEqual(positive["bounded_cost_minutes"], 35)
        self.assertEqual(positive["net_avoidable_minutes"], 25)
        self.assertEqual(positive["reversibility_posture"], "checkpoint-restore")
        self.assertTrue(lane_eligible(positive))
        self.assertIn("compressed-size delta", EXERCISE["eligibility_evidence"]["outcome_uncertainty"]["claim"])
        self.assertEqual(EXERCISE["eligibility_default"]["implementation_evidence_root"], root(EXERCISE["eligibility_evidence"]["implementation_evidence"]))
        for case_id in ("read-only-decidable", "unsafe-isolation", "style-only", "speculative-reuse", "novelty-only"):
            result = evaluate_unaccepted(case_id)
            self.assertEqual(result["action"], "reject-before-lane")
            self.assertFalse(result["lane_created"])

    def test_coherent_cases_bind_bytes_validation_comparison_and_external_review(self) -> None:
        for case_id in ("winning-candidate", "losing-candidate", "novelty-bias", "inconclusive-comparison"):
            case = canonical_case(case_id)
            result = evaluate_unaccepted(case_id)
            self.assertEqual(result["action"], case["expected_action"])
            self.assertEqual(result["review_result"]["comparison_disposition"], case["expected_comparison_disposition"])
            self.assertEqual(result["candidate_root"], artifact_root(EXERCISE["artifacts"][case["artifact_id"]]))
            self.assertEqual(result["mapped_result"]["focused_result_root"], result["focused_result"]["result_root"])
            self.assertGreater(parse_time(result["mapped_result"]["recorded_at"], "mapped"), parse_time(result["focused_result"]["recorded_at"], "focused"))
            validate_comparison(result["raw_comparison_records"])
            self.assertEqual(result["review_result"]["input_root"], root(result["blind_review_packet"]))

    def test_block4_lifecycle_winner_and_inconclusive_are_valid(self) -> None:
        winner = evaluate_unaccepted("winning-candidate")
        self.assertEqual([item["decision_stage"] for item in winner["stage_records"]], ["selected", "implementing", "validated", "reviewed", "cutover-eligible"])
        self.assertEqual(winner["stage_records"][-1]["review_disposition"], "accepted")
        self.assertEqual(winner["stage_records"][-1]["retirement_posture"], "eligible-cutover")
        inconclusive = evaluate_unaccepted("inconclusive-comparison")
        self.assertEqual(inconclusive["stage_records"][-1]["decision_stage"], "closed")
        self.assertEqual(inconclusive["stage_records"][-1]["review_disposition"], "inconclusive")
        self.assertEqual(inconclusive["stage_records"][-1]["retirement_posture"], "retired-inconclusive")
        loser = evaluate_unaccepted("losing-candidate")
        for index in (0, 1):
            self.assertIsNone(winner["stage_records"][index]["candidate_root"])
            self.assertIsNone(loser["stage_records"][index]["candidate_root"])
            self.assertEqual(winner["stage_records"][index]["current_target_state_root"], loser["stage_records"][index]["current_target_state_root"])
        validated = winner["stage_records"][2]
        validated_index = {item["ref_id"]: item for item in validated["evidence_refs"]}
        as_of_focused = {"files": 1, "changed_lines": 2, "commands": 1, "review_passes": 0, "elapsed_minutes": 1}
        self.assertEqual(validated_index["resource-validated"]["root_sha256"], resource_usage_root(as_of_focused))
        self.assertEqual(validated_index["validation-validated"]["root_sha256"], root({"focused_result_root": winner["focused_result"]["result_root"], "mapped_result_root": None}))
        self.assertNotEqual(validated_index["resource-validated"]["root_sha256"], resource_usage_root(winner["resource_usage"]))
        reviewed = winner["stage_records"][3]
        reviewed_index = {item["ref_id"]: item for item in reviewed["evidence_refs"]}
        self.assertEqual(reviewed_index["resource-reviewed"]["root_sha256"], resource_usage_root(winner["resource_usage"]))
        self.assertEqual(reviewed_index["validation-reviewed"]["root_sha256"], root({"focused_result_root": winner["focused_result"]["result_root"], "mapped_result_root": winner["mapped_result"]["result_root"]}))
        for record in [*winner["stage_records"], *inconclusive["stage_records"]]:
            self.assertEqual(record["currentness_root"], root(currentness_projection(record)))
            self.assertEqual(set(record), set(SPEC["common_fields"]) | set(SPEC["candidate_fields"]))
            validate_stage_record(record)
            common = {key: record[key] for key in SPEC["fingerprint_projection"]}
            candidate = {key: record[key] for key in SPEC["candidate_fingerprint_projection"]}
            self.assertEqual(record["decision_fingerprint"], root({**common, "candidate": candidate}))
            self.assertEqual(record["target_revision_root"], root({"target_revision": record["target_revision"]}))

    def test_all_post_creation_stops_close_with_evidence_cleanup_and_no_authority(self) -> None:
        for case_id in ("ceiling-expired", "incumbent-conflict", "focused-failure", "mapped-failure", "protected-regression", "review-currentness-loss", "cancelled", "isolation-drift", "hypothesis-falsified", "review-timeout"):
            result = evaluate_unaccepted(case_id)
            self.assertEqual(result["action"], "stop-retire")
            self.assertEqual(result["stage_records"][-1]["decision_stage"], "closed")
            self.assertFalse(result["candidate_authoritative"])
            self.assertTrue(result["incumbent_authoritative"])
            self.assertEqual(result["isolation_cleanup"], "retired-non-authoritative")
            self.assertTrue(result["review_cycle"])
            self.assertEqual(result["stop_review_packet"]["cause_root"], root(result["stop_cause"]))
            self.assertIsNone(result["handoff"])
            self.assertFalse(result["cutover_performed"] or result["tracker_mutated"] or result["policy_mutated"])
            classes = {item["source_class"] for item in result["stage_records"][-1]["evidence_refs"]}
            self.assertTrue({"validation", "independent-review", "observed-outcome"}.issubset(classes))

    def test_caller_cannot_fabricate_an_accepted_head_to_suppress_work(self) -> None:
        first = evaluate_unaccepted("winning-candidate")
        with self.assertRaisesRegex(ValueError, "not authority"):
            evaluate("winning-candidate", accepted_head=first["lane_head"])
        forged = copy.deepcopy(first["lane_head"])
        for key in ("review_root", "currentness_root", "handoff_root"):
            forged[key] = "0" * 64
        raw = dict(forged)
        raw.pop("head_root")
        forged["head_root"] = root(raw)
        with self.assertRaisesRegex(ValueError, "not authority"):
            evaluate("winning-candidate", accepted_head=forged)

    def test_exact_accepted_lane_deduplicates_without_new_lane_review_or_handoff(self) -> None:
        historical = evaluate_unaccepted("winning-candidate")
        review_producer = globals()["review_fixture_result"]
        globals()["review_fixture_result"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("deduplication invoked the independent review producer")
        )
        try:
            first = evaluate("winning-candidate")
            second = evaluate("winning-candidate")
        finally:
            globals()["review_fixture_result"] = review_producer
        self.assertEqual(first, second)
        self.assertEqual(first["action"], "deduplicate")
        self.assertFalse(first["lane_created"] or first["review_cycle"])
        self.assertIsNone(first["handoff"])
        self.assertEqual(first["lane_head"], historical["lane_head"])
        self.assertEqual(first["existing_handoff"], historical["handoff"])
        self.assertEqual(first["existing_handoff_root"], historical["handoff"]["handoff_root"])
        self.assertEqual(first["next_action"], "continue-with-existing-block-9-handoff")
        self.assertFalse(first["candidate_authoritative"] or first["cutover_performed"])
        self.assertTrue(first["incumbent_authoritative"])
        first["lane_head"]["review_root"] = "0" * 64
        self.assertEqual(evaluate("winning-candidate")["lane_head"], historical["lane_head"])

    def test_accepted_snapshot_and_signed_review_fail_closed_on_replacement(self) -> None:
        validate_accepted_snapshot()
        original_head = ACCEPTED_SNAPSHOT["lane_head"]
        ACCEPTED_SNAPSHOT["lane_head"] = {**original_head, "review_root": "0" * 64}
        try:
            with self.assertRaisesRegex(ValueError, "snapshot differs"):
                validate_accepted_snapshot()
        finally:
            ACCEPTED_SNAPSHOT["lane_head"] = original_head
        original_disposition = EXACT_REVIEW["review_disposition"]
        EXACT_REVIEW["review_disposition"] = "rejected"
        try:
            with self.assertRaisesRegex(ValueError, "review bytes differ"):
                validate_accepted_snapshot()
        finally:
            EXACT_REVIEW["review_disposition"] = original_disposition

    def test_installed_release_may_omit_only_the_signed_tracker_blob(self) -> None:
        tracker_relative = "docs/software-factory-adaptive-implementation-decision-control-implementation-tracker.md"
        with tempfile.TemporaryDirectory(prefix="software-factory-block6-installed-") as raw:
            installed_root = Path(raw)
            copied: list[Path] = []
            for entry in ACCEPTED_SNAPSHOT["source_files"]:
                if entry["path"] == tracker_relative:
                    continue
                source = REPO_ROOT / entry["path"]
                destination = installed_root / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
                copied.append(destination)
            validate_accepted_source_manifest(installed_root)
            copied[0].unlink()
            with self.assertRaisesRegex(ValueError, "source path differs"):
                validate_accepted_source_manifest(installed_root)

    def test_winner_emits_one_frozen_nonmutating_block9_handoff(self) -> None:
        result = evaluate_unaccepted("winning-candidate")
        handoff = result["handoff"]
        self.assertEqual(handoff["source_block"], 6)
        self.assertEqual(handoff["destination_block"], 9)
        self.assertTrue(handoff["non_mutating"])
        for key in ("cutover_authority", "publish_authority", "tracker_authority", "policy_authority"):
            self.assertFalse(handoff[key])
        raw = dict(handoff)
        recorded_root = raw.pop("handoff_root")
        self.assertEqual(recorded_root, root(raw))

    def test_blind_review_input_excludes_preference_and_disposition_follows_raw_evidence(self) -> None:
        result = evaluate_unaccepted("winning-candidate")
        packet = result["blind_review_packet"]
        for key in ("case_id", "expected_action", "expected_comparison_disposition", "implementer_preference"):
            self.assertNotIn(key, packet)
        changed = copy.deepcopy(result["raw_comparison_records"])
        changed[0]["relation"] = "incumbent-better"
        with self.assertRaisesRegex(ValueError, "bind raw comparison"):
            review_fixture_result(packet, changed)
        forged = copy.deepcopy(result["raw_comparison_records"])
        forged[0]["candidate_value"]["artifact_bytes"] = 99999999
        forged[0]["candidate_evidence_root"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "retained evidence"):
            validate_comparison(forged, result["mapped_result"])

    def test_embedded_candidate_bytes_are_the_observable_source(self) -> None:
        incumbent = execute_stream(EXERCISE["incumbent"]["files"], contained_by=EXERCISE["target_repository_root"])
        winner = execute_stream(EXERCISE["artifacts"]["candidate-winning"]["files"], contained_by=EXERCISE["lane"]["root"])
        self.assertEqual(incumbent["decompressed_sha256"], winner["decompressed_sha256"])
        self.assertEqual((incumbent["artifact_bytes"], winner["artifact_bytes"]), (4619, 4531))
        self.assertEqual(winner["regression_ids"], [])
        self.assertEqual(metric_relation("observable-outcome", EXERCISE["incumbent"]["metrics"]["observable-outcome"], derived_candidate_metrics(EXERCISE["artifacts"]["candidate-winning"])["observable-outcome"])[0], "candidate-better")
        broken = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        broken["files"][0]["content_utf8"] = "def export(rows):\n    return b'BROKEN'\n"
        with self.assertRaisesRegex(ValueError, "executable candidate bytes"):
            focused_result(broken, artifact_root(broken))

    def test_resource_usage_is_derived_and_ceiling_is_factual(self) -> None:
        winning = canonical_case("winning-candidate")
        result = evaluate_unaccepted("winning-candidate")
        self.assertEqual(result["resource_usage"], winning["usage"])
        self.assertEqual(derived_usage(winning, EXERCISE["artifacts"][winning["artifact_id"]])["review_passes"], 0)
        ceiling = canonical_case("ceiling-expired")
        usage = derived_usage(ceiling, EXERCISE["artifacts"][ceiling["artifact_id"]])
        self.assertTrue(ceiling_exceeded(usage))
        changed = copy.deepcopy(winning)
        changed["usage"]["files"] = 3
        with self.assertRaisesRegex(ValueError, "retained artifacts"):
            derived_usage(changed, EXERCISE["artifacts"][changed["artifact_id"]], focused=result["focused_result"], mapped=result["mapped_result"], review=result["review_result"])

    def test_resource_usage_is_bound_to_currentness_handoff_and_accepted_head(self) -> None:
        result = evaluate_unaccepted("winning-candidate")
        baseline_currentness = result["stage_records"][-1]["currentness_root"]
        baseline_handoff = result["handoff"]["handoff_root"]
        baseline_head = result["lane_head"]["head_root"]
        expected_usage_root = resource_usage_root(result["resource_usage"])
        self.assertEqual(result["handoff"]["resource_usage_root"], expected_usage_root)
        self.assertEqual(result["lane_head"]["resource_usage_root"], expected_usage_root)
        resource_ref = next(item for item in result["stage_records"][-1]["evidence_refs"] if item["ref_id"] == "resource-cutover-eligible")
        self.assertEqual(resource_ref["root_sha256"], expected_usage_root)
        case = canonical_case("winning-candidate")
        eligible = eligibility(case)
        artifact, candidate = candidate_root_for(case)
        focused = focused_result(artifact, candidate)
        mapped = mapped_result(artifact, candidate, focused)
        comparison = comparison_records(mapped)
        review = review_fixture_result(blind_review_packet(candidate, mapped, comparison), comparison)
        for replacement in (
            {key: 0 for key in result["resource_usage"]},
            {key: 999 for key in result["resource_usage"]},
        ):
            records = stage_records(case, eligible, candidate, focused, mapped, review, "cutover-eligible", replacement)
            self.assertNotEqual(records[-1]["currentness_root"], baseline_currentness)
            mutated_handoff = handoff_record(records, comparison, review, replacement)
            self.assertNotEqual(mutated_handoff["handoff_root"], baseline_handoff)
            mutated = {**result, "resource_usage": replacement, "stage_records": records, "handoff": mutated_handoff}
            self.assertNotEqual(accepted_lane_head(mutated)["head_root"], baseline_head)

    def test_materiality_runtime_and_incumbent_metrics_are_factual(self) -> None:
        self.assertEqual(EXERCISE["incumbent"]["metrics"], derived_incumbent_metrics())
        incumbent = EXERCISE["incumbent"]["metrics"]["observable-outcome"]
        one_byte = {**incumbent, "artifact_bytes": incumbent["artifact_bytes"] - 1, "performance_posture": "candidate-not-materially-slower"}
        self.assertEqual(metric_relation("observable-outcome", incumbent, one_byte)[0], "equivalent")
        slow = copy.deepcopy(derived_candidate_metrics(EXERCISE["artifacts"]["candidate-winning"])["observable-outcome"])
        slow["performance_posture"] = "candidate-materially-slower"
        self.assertEqual(metric_relation("observable-outcome", incumbent, slow)[0], "incumbent-better")
        winning = evaluate_unaccepted("winning-candidate")
        self.assertEqual(winning["blind_review_packet"]["representative_workload_root"], root(EXERCISE["representative_workload"]))
        self.assertEqual(winning["blind_review_packet"]["validation_runtime_root"], validation_runtime_root())
        performance = EXERCISE["artifacts"]["candidate-winning"]["mapped"]["performance_evidence"]
        self.assertEqual(len(performance["incumbent_samples_ns"]), EXERCISE["performance_protocol"]["sample_pairs"])
        self.assertEqual(len(performance["candidate_samples_ns"]), EXERCISE["performance_protocol"]["sample_pairs"])
        self.assertEqual(performance["incumbent_median_ns"], int(median(performance["incumbent_samples_ns"])))
        self.assertEqual(performance["candidate_median_ns"], int(median(performance["candidate_samples_ns"])))
        self.assertEqual(winning["blind_review_packet"]["performance_result_root"], performance["result_root"])
        original_benchmark = globals()["benchmark_performance"]
        globals()["benchmark_performance"] = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("retained evidence reran producer"))
        try:
            self.assertEqual(performance_evidence(EXERCISE["artifacts"]["candidate-winning"], winning["candidate_root"])["result_root"], performance["result_root"])
        finally:
            globals()["benchmark_performance"] = original_benchmark
        stale = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        stale["mapped"]["performance_evidence"]["candidate_samples_ns"][0] += 1
        with self.assertRaisesRegex(ValueError, "performance (evidence|result) root"):
            performance_evidence(stale, artifact_root(stale))

    def test_review_chronology_and_usage_ceiling_are_derived(self) -> None:
        case = canonical_case("winning-candidate")
        artifact, candidate = candidate_root_for(case)
        focused = focused_result(artifact, candidate)
        mapped = mapped_result(artifact, candidate, focused)
        comparison = comparison_records(mapped)
        review = review_fixture_result(blind_review_packet(candidate, mapped, comparison), comparison)
        usage = derived_usage(case, artifact, focused=focused, mapped=mapped, review=review)
        self.assertEqual(usage, case["usage"])
        delayed = copy.deepcopy(review)
        delayed["recorded_at"] = format_time(parse_time(mapped["recorded_at"], "mapped") + timedelta(minutes=11))
        self.assertTrue(review_exceeds_ceiling(delayed, mapped))
        timeout = evaluate_unaccepted("review-timeout")
        self.assertEqual(timeout["action"], "stop-retire")
        self.assertEqual(timeout["stop_reason"], "review-ceiling-expired")
        self.assertEqual(timeout["resource_usage"]["review_passes"], 2)
        self.assertEqual(timeout["isolation_cleanup"], "retired-non-authoritative")
        self.assertIsNone(timeout["handoff"])

    def test_stop_observations_are_retained_objects_not_unresolved_roots(self) -> None:
        for case_id, retained_key, derived_key in (
            ("incumbent-conflict", "observed_incumbent", "observed_incumbent_record_root"),
            ("review-currentness-loss", "observed_review_input", "observed_review_input_root"),
            ("cancelled", "cancellation_authority", "cancellation_authority_root"),
            ("isolation-drift", "observed_isolation_scope", "observed_isolation_root"),
        ):
            result = evaluate_unaccepted(case_id)
            self.assertIn(retained_key, result["stop_cause"])
            self.assertEqual(result["stop_cause"][derived_key], root(result["stop_cause"][retained_key]))

    def test_evidence_claim_binding_rejects_protected_path_and_reviewer_forgery(self) -> None:
        record = copy.deepcopy(evaluate_unaccepted("winning-candidate")["stage_records"][-1])
        capability = next(item for item in record["evidence_refs"] if item["ref_id"] == "evidence-capability")
        capability["claim_ids"].remove("stable-bytes-api")
        record["evidence_manifest_root"] = root(record["evidence_refs"])
        record["currentness_root"] = root(currentness_projection(record))
        with self.assertRaisesRegex(ValueError, "protected capability"):
            validate_stage_record(record)
        record = copy.deepcopy(evaluate_unaccepted("winning-candidate")["stage_records"][0])
        record["evidence_refs"] = [item for item in record["evidence_refs"] if item["ref_id"] != "evidence-reviewer-authority"]
        record["evidence_manifest_root"] = root(record["evidence_refs"])
        record["currentness_root"] = root(currentness_projection(record))
        with self.assertRaisesRegex(ValueError, "reviewer identity"):
            validate_stage_record(record)

    def test_exact_regression_id_sets_are_not_lossy_counts(self) -> None:
        left = {"regression_ids": ["stable-bytes-api"]}
        right = {"regression_ids": ["semantic-roundtrip"]}
        relation, _ = metric_relation("protected-capability", left, right)
        self.assertEqual(relation, "incumbent-better")

    def test_fingerprint_binds_target_incumbent_outcome_dimensions_and_source_basis(self) -> None:
        case = canonical_case("winning-candidate")
        eligible = eligibility(case)
        baseline = decision_basis(case, eligible)
        baseline_root = root(baseline)
        for key, value in (
            ("target_repository_root", "/different-target"),
            ("target_revision", "f" * 40),
            ("incumbent_revision", "e" * 40),
            ("expected_observable_effect", "different effect"),
            ("representative_workload_root", "d" * 64),
            ("validation_runtime_root", "c" * 64),
            ("materiality_criterion", {**EXERCISE["materiality_criterion"], "minimum_artifact_byte_reduction": 51}),
            ("comparison_dimensions", list(reversed(DIMENSIONS))),
        ):
            changed = copy.deepcopy(baseline)
            changed[key] = value
            self.assertNotEqual(root(changed), baseline_root, key)

    def test_strict_schema_types_and_paths_reject_coercion_empty_scope_and_escape(self) -> None:
        fields = evaluate_unaccepted("winning-candidate")["stage_records"][-1]
        for key, value in (("isolation_kind", "invented"), ("hypothesis_scope", []), ("isolated_writable_scope", []), ("production_authority_owner_id", True), ("independent_reviewer_id", 123), ("focused_validation", [123])):
            invalid = {name: copy.deepcopy(fields[name]) for name in SPEC["candidate_fields"]}
            invalid[key] = value
            with self.assertRaises(ValueError, msg=key):
                validate_candidate_fields(invalid)
        invalid_scope = copy.deepcopy({name: fields[name] for name in SPEC["candidate_fields"]})
        invalid_scope["isolated_writable_scope"][0]["path"] = "/software-factory-candidate-lane/../production/owned.py"
        with self.assertRaisesRegex(ValueError, "canonical"):
            validate_candidate_fields(invalid_scope)
        invalid_owner = copy.deepcopy({name: fields[name] for name in SPEC["candidate_fields"]})
        invalid_owner["isolated_writable_scope"][0]["owner_id"] = True
        with self.assertRaises(ValueError):
            validate_candidate_fields(invalid_owner)

    def test_focused_mapped_order_and_content_currentness_fail_closed(self) -> None:
        artifact = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        candidate = artifact_root(artifact)
        focused = focused_result(artifact, candidate)
        artifact["mapped"]["recorded_at"] = artifact["focused"]["recorded_at"]
        with self.assertRaisesRegex(ValueError, "does not follow"):
            mapped_result(artifact, candidate, focused)
        changed = copy.deepcopy(EXERCISE["artifacts"]["candidate-winning"])
        original = artifact_root(changed)
        changed["files"][0]["content_utf8"] += "# changed\n"
        self.assertNotEqual(artifact_root(changed), original)

    def test_method_is_selective_bounded_and_stops_before_cutover(self) -> None:
        skill = " ".join(SKILL.split())
        reference = " ".join(REFERENCE.split())
        for phrase in ("Use `compare-candidate` only after the inline loop proves", "Open exactly one branch, worktree, temporary repository, or equivalent lane", "without a novelty bonus or opaque aggregate score", "do not cut over here", "Never retain two live implementations or force adoption"):
            self.assertIn(phrase, skill)
        for phrase in ("Failure of any condition returns to the incumbent without creating a lane", "The incumbent is the only production authority", "The Block Stop is before cutover, tracker amendment, policy change"):
            self.assertIn(phrase, reference)


if __name__ == "__main__":
    unittest.main()
