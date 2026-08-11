#!/usr/bin/env python3
"""Atomic, evidence-bound cutover for one accepted bounded candidate.

The operation is deliberately target-owner scoped.  It consumes the frozen
Block 6 handoff, resolves current context through a separate owner callback,
commits only the affected implementation and cutover records, proves the live
effect, and returns one idempotent Block 9 resume token.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import unicodedata
import zlib
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple


class CutoverError(RuntimeError):
    """The candidate cannot be cut over at the current exact state."""


SKILL_ROOT = Path(__file__).resolve().parents[1]
TRACKER_RELATIVE = (
    "docs/software-factory-adaptive-implementation-decision-control-"
    "implementation-tracker.md"
)
ACCEPTED_SNAPSHOT_PATH = SKILL_ROOT / "fixtures/bounded_candidate_accepted_v1.json"
EXACT_REVIEW_PATH = SKILL_ROOT / "fixtures/bounded_candidate_exact_review_v1.json"
EXERCISE_PATH = SKILL_ROOT / "fixtures/bounded_candidate_v1.json"
CUTOVER_FIXTURE_PATH = SKILL_ROOT / "fixtures/candidate_cutover_v1.json"
REVIEWER_PUBLIC_KEY_PATH = Path(
    "/Users/ethanstillman/.codex/software-factory-release-authority/reviewers/"
    "software-factory-release-reviewer-v1.pem"
)
REVIEWER_AUTHORITY_ROOT = REVIEWER_PUBLIC_KEY_PATH.parents[1]
REVIEWER_AUTHORITY_DIRECTORY = REVIEWER_PUBLIC_KEY_PATH.parent
TRUSTED_OPENSSL_PATH = Path("/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl")
GIT = "/usr/bin/git"

EXPECTED_ACCEPTED_SNAPSHOT_ROOT = (
    "c5af9febeae85773f106d3a761689e88e7756f75666e4f613de5c38615ea2252"
)
EXPECTED_EXACT_REVIEW_SHA256 = (
    "83d8a3efc7c5492884499f2ebb5e124901ca85b5f7af59f79613c5f90f4cc811"
)
EXPECTED_REVIEWER_KEY_SHA256 = (
    "e6ace9dfbbf97ec65800d1da146c4b59b20a2aef86ad706b174b9837bcb41a02"
)
TRUSTED_OPENSSL_SHA256 = (
    "bf63843e6856e1994ca71092ff3b46834236eb2144dd9b6ceb85d511128b836e"
)
EXPECTED_BLOCK9_CONTRACT_ROOT = (
    "8ffdc33952d48f60afb14f6c54e4d15e54aebef939191f20a54cd854b481604e"
)
EXPECTED_HANDOFF_ROOT = (
    "eee651909f87a4e0c50cca8956b6805d641e09c6f97ff6a0831818984b958844"
)
EXPECTED_LANE_HEAD_ROOT = (
    "3493d8048ac4dc4f35cf0ac236bb05588a786a90cfa8c6885d56e9d361a3e93c"
)
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
STATE_RELATIVE = ".software-factory/candidate-cutover-v1.json"
OUTCOME_RELATIVE = ".software-factory/candidate-cutover-outcome-v1.json"
RESUME_RELATIVE = ".software-factory/candidate-cutover-resume-v1.json"


def _reject_duplicate_pairs(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CutoverError("duplicate JSON key")
        result[key] = value
    return result


def _validate_canonical(value: object) -> None:
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        if unicodedata.normalize("NFC", value) != value:
            raise CutoverError("JSON string is not NFC-normalized")
        return
    if type(value) is list:
        for item in value:
            _validate_canonical(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or unicodedata.normalize("NFC", key) != key:
                raise CutoverError("JSON object key is not canonical")
            _validate_canonical(item)
        return
    raise CutoverError("JSON value is outside the bounded canonical profile")


def canonical(value: object) -> bytes:
    _validate_canonical(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def object_root(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_root(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_string(
    value: object, name: str, pattern: Optional[re.Pattern] = ID_RE
) -> str:
    if type(value) is not str or (pattern is not None and pattern.fullmatch(value) is None):
        raise CutoverError("%s differs" % name)
    return value


def _load_json(path: Path) -> Dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise CutoverError("evidence path differs")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise CutoverError("evidence exceeds the bounded size")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CutoverError("evidence JSON differs") from error
    if type(value) is not dict:
        raise CutoverError("evidence root must be an object")
    _validate_canonical(value)
    return value


def _canonical_line(path: Path, value: Mapping[str, object]) -> bool:
    return path.read_bytes() == canonical(dict(value)) + b"\n"


def _verify_signature(review: Mapping[str, object]) -> None:
    review_bytes = EXACT_REVIEW_PATH.read_bytes()
    if (
        bytes_root(review_bytes) != EXPECTED_EXACT_REVIEW_SHA256
        or not _canonical_line(EXACT_REVIEW_PATH, review)
        or REVIEWER_AUTHORITY_ROOT.is_symlink()
        or not REVIEWER_AUTHORITY_ROOT.is_dir()
        or REVIEWER_AUTHORITY_ROOT.stat().st_mode & 0o222
        or REVIEWER_AUTHORITY_DIRECTORY.is_symlink()
        or not REVIEWER_AUTHORITY_DIRECTORY.is_dir()
        or REVIEWER_AUTHORITY_DIRECTORY.stat().st_mode & 0o222
        or REVIEWER_PUBLIC_KEY_PATH.is_symlink()
        or not REVIEWER_PUBLIC_KEY_PATH.is_file()
        or REVIEWER_PUBLIC_KEY_PATH.stat().st_mode & 0o222
        or bytes_root(REVIEWER_PUBLIC_KEY_PATH.read_bytes())
        != EXPECTED_REVIEWER_KEY_SHA256
        or TRUSTED_OPENSSL_PATH.is_symlink()
        or not TRUSTED_OPENSSL_PATH.is_file()
        or bytes_root(TRUSTED_OPENSSL_PATH.read_bytes()) != TRUSTED_OPENSSL_SHA256
    ):
        raise CutoverError("independent review identity differs")
    root_material = {
        key: value
        for key, value in review.items()
        if key not in {"evidence_root_sha256", "signature_base64"}
    }
    if review.get("evidence_root_sha256") != object_root(root_material):
        raise CutoverError("independent review root differs")
    signed_material = {
        key: value for key, value in review.items() if key != "signature_base64"
    }
    try:
        signature = base64.b64decode(
            _exact_string(review.get("signature_base64"), "review signature", None),
            validate=True,
        )
    except (TypeError, ValueError) as error:
        raise CutoverError("independent review signature differs") from error
    with tempfile.TemporaryDirectory(prefix="candidate-cutover-review-") as raw:
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
        raise CutoverError("independent review signature differs")


def _validate_rooted_record(value: object, root_field: str, name: str) -> Dict[str, object]:
    if type(value) is not dict:
        raise CutoverError("%s differs" % name)
    record = dict(value)
    recorded = record.pop(root_field, None)
    if _exact_string(recorded, "%s root" % name, SHA_RE) != object_root(record):
        raise CutoverError("%s root differs" % name)
    return dict(value)


def load_accepted_bundle() -> Dict[str, object]:
    snapshot = _load_json(ACCEPTED_SNAPSHOT_PATH)
    review = _load_json(EXACT_REVIEW_PATH)
    exercise = _load_json(EXERCISE_PATH)
    if object_root(snapshot) != EXPECTED_ACCEPTED_SNAPSHOT_ROOT:
        raise CutoverError("accepted candidate snapshot differs")
    _verify_signature(review)
    handoff = _validate_rooted_record(snapshot.get("handoff"), "handoff_root", "handoff")
    lane_head = _validate_rooted_record(snapshot.get("lane_head"), "head_root", "lane head")
    artifacts = exercise.get("artifacts")
    incumbent = exercise.get("incumbent")
    if type(artifacts) is not dict or type(incumbent) is not dict:
        raise CutoverError("accepted candidate source differs")
    winner = artifacts.get("candidate-winning")
    if type(winner) is not dict:
        raise CutoverError("accepted winning candidate differs")
    bundle = {
        "snapshot": snapshot,
        "review": review,
        "exercise": exercise,
        "handoff": handoff,
        "lane_head": lane_head,
        "incumbent": incumbent,
        "winner": winner,
    }
    validate_cutover_bundle(bundle)
    return bundle


def validate_cutover_bundle(bundle: Mapping[str, object]) -> None:
    handoff = bundle.get("handoff")
    lane_head = bundle.get("lane_head")
    review = bundle.get("review")
    if type(handoff) is not dict or type(lane_head) is not dict or type(review) is not dict:
        raise CutoverError("accepted candidate bundle differs")
    if (
        handoff.get("handoff_root") != EXPECTED_HANDOFF_ROOT
        or lane_head.get("head_root") != EXPECTED_LANE_HEAD_ROOT
        or handoff.get("handoff_root") != lane_head.get("handoff_root")
        or handoff.get("decision_fingerprint") != lane_head.get("decision_fingerprint")
        or handoff.get("candidate_root") != lane_head.get("candidate_root")
        or handoff.get("review_root") != lane_head.get("review_root")
        or handoff.get("currentness_root") != lane_head.get("currentness_root")
        or handoff.get("target_revision_root") != lane_head.get("target_revision_root")
        or handoff.get("destination_block") != 9
        or handoff.get("non_mutating") is not True
        or handoff.get("cutover_authority") is not False
        or review.get("review_disposition") != "accepted"
        or review.get("finding_count") != 0
        or review.get("authority_key_sha256") != EXPECTED_REVIEWER_KEY_SHA256
        or review.get("winning_handoff_root") != handoff.get("handoff_root")
        or review.get("winning_lane_head_root") != lane_head.get("head_root")
        or review.get("winning_candidate_root") != handoff.get("candidate_root")
        or review.get("winning_review_root") != handoff.get("review_root")
        or review.get("winning_comparison_root") != handoff.get("comparison_root")
        or review.get("winning_decision_fingerprint")
        != handoff.get("decision_fingerprint")
        or review.get("winning_final_currentness_root")
        != handoff.get("currentness_root")
        or review.get("exercise_root") != object_root(bundle.get("exercise"))
        or handoff.get("cutover_preconditions")
        != ["block-9", "current-review", "current-target", "single-authority"]
        or {
            item.get("capability_id")
            for item in handoff.get("protected_capability_results", [])
            if type(item) is dict
        }
        != {"semantic-roundtrip", "stable-bytes-api"}
        or any(
            type(item) is not dict or item.get("result") != "preserved"
            for item in handoff.get("protected_capability_results", [])
        )
    ):
        raise CutoverError("accepted candidate handoff differs")
    lifecycle = review.get("winning_lifecycle")
    if (
        type(lifecycle) is not list
        or not lifecycle
        or type(lifecycle[-1]) is not dict
        or lifecycle[-1].get("decision_stage") != "cutover-eligible"
        or lifecycle[-1].get("candidate_root") != handoff.get("candidate_root")
        or lifecycle[-1].get("review_root") != handoff.get("review_root")
        or lifecycle[-1].get("currentness_root") != handoff.get("currentness_root")
    ):
        raise CutoverError("accepted candidate lifecycle differs")


def _block9_contract_root(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CutoverError("tracker must be UTF-8") from error
    match = re.search(r"^## Block 9 .*?(?=^## Block 10 )", text, re.M | re.S)
    if match is None:
        raise CutoverError("Block 9 contract is absent")
    normalized: List[str] = []
    in_completion = False
    for line in match.group(0).splitlines():
        if re.match(r"^Status:\s*", line):
            normalized.append("Status: <runtime-state>")
            continue
        if line.strip() == "### Completion evidence":
            in_completion = True
            normalized.append(line)
            continue
        if in_completion and re.match(r"^###\s+", line):
            in_completion = False
        if not in_completion:
            normalized.append(line.rstrip())
    return bytes_root("\n".join(normalized).strip().encode("utf-8"))


def _git(repo: Path, args: Sequence[str], *, env: Optional[Mapping[str, str]] = None) -> bytes:
    result = subprocess.run(
        [GIT, "-C", str(repo), *args],
        check=False,
        capture_output=True,
        env=dict(env) if env is not None else None,
    )
    if result.returncode:
        raise CutoverError("Git target-owner operation failed")
    return result.stdout.strip()


def _repo_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise CutoverError("target repository root differs")
    resolved = path.resolve(strict=True)
    top = Path(_git(resolved, ["rev-parse", "--show-toplevel"]).decode("utf-8"))
    if top != resolved or top == Path("/"):
        raise CutoverError("target repository root differs")
    return resolved


def _safe_file(repo: Path, relative: str, *, required: bool = True) -> Optional[bytes]:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in {".", ".."} for part in pure.parts):
        raise CutoverError("affected path escapes target repository")
    path = repo.joinpath(*pure.parts)
    if not path.exists() and not path.is_symlink():
        if required:
            raise CutoverError("affected path is absent")
        return None
    if path.is_symlink() or not path.is_file():
        raise CutoverError("affected path is not a regular file")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(repo)
    except ValueError as error:
        raise CutoverError("affected path escapes target repository") from error
    before = path.stat()
    if before.st_size > MAX_SOURCE_BYTES:
        raise CutoverError("affected file exceeds the bounded size")
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(after):
        raise CutoverError("affected file changed while reading")
    return raw


def _write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return canonical(dict(value)) + b"\n"


def _head(repo: Path) -> str:
    return _exact_string(_git(repo, ["rev-parse", "HEAD"]).decode("ascii"), "target HEAD", REV_RE)


def _target_state_root(head: str, relative: str, content: bytes) -> str:
    return object_root(
        {
            "schema_version": 1,
            "kind": "candidate-cutover-target-state",
            "target_head": head,
            "affected_path": relative,
            "affected_content_root": bytes_root(content),
        }
    )


def resolve_current_context(
    repo: Path,
    tracker_path: Path,
    context_owner: Callable[[], Mapping[str, object]],
    relative: str,
) -> Dict[str, object]:
    owner_identity = getattr(context_owner, "cutover_owner_id", None)
    if owner_identity is None and getattr(context_owner, "__self__", None) is not None:
        owner_identity = getattr(context_owner.__self__, "cutover_owner_id", None)
    if owner_identity != "owner-target-production":
        raise CutoverError("context resolver is not the normal target owner")
    tracker_raw = _safe_external_tracker(tracker_path)
    target_raw = _safe_file(repo, relative)
    assert target_raw is not None
    head = _head(repo)
    computed = {
        "target_repository_root": str(repo),
        "target_head": head,
        "target_state_root": _target_state_root(head, relative, target_raw),
        "affected_path": relative,
        "affected_content_root": bytes_root(target_raw),
        "tracker_path": str(tracker_path.resolve(strict=True)),
        "tracker_sha256": bytes_root(tracker_raw),
        "block9_contract_root": _block9_contract_root(tracker_raw),
    }
    value = context_owner()
    if type(value) is not dict:
        raise CutoverError("context owner did not return canonical state")
    required = {
        "schema_version",
        "kind",
        "mission_root",
        "policy_root",
        "event_head_root",
        "cutover_owner_id",
        "structural_change",
        *computed.keys(),
    }
    if set(value) != required:
        raise CutoverError("current context fields differ")
    for key in ("mission_root", "policy_root", "event_head_root"):
        _exact_string(value.get(key), "context %s" % key, SHA_RE)
    _exact_string(value.get("cutover_owner_id"), "cutover owner")
    if type(value.get("structural_change")) is not bool:
        raise CutoverError("structural-change posture differs")
    if value.get("schema_version") != 1 or value.get("kind") != "candidate-cutover-current-context":
        raise CutoverError("current context identity differs")
    for key, expected in computed.items():
        if value.get(key) != expected:
            raise CutoverError("current context %s is stale" % key)
    if computed["block9_contract_root"] != EXPECTED_BLOCK9_CONTRACT_ROOT:
        raise CutoverError("Block 9 contract requires structural amendment")
    return dict(value)


def _safe_external_tracker(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CutoverError("tracker path differs")
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if len(raw) > MAX_JSON_BYTES:
        raise CutoverError("tracker exceeds the bounded size")
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise CutoverError("tracker changed while reading")
    return raw


def _control_directory(repo: Path) -> Path:
    path = repo / ".software-factory"
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
            raise CutoverError("target control directory differs")
    else:
        path.mkdir(mode=0o755)
    return path


def _artifact_file(bundle: Mapping[str, object], which: str) -> Tuple[str, bytes]:
    source = bundle[which]
    files = source.get("files") if type(source) is dict else None
    if type(files) is not list or len(files) != 1 or type(files[0]) is not dict:
        raise CutoverError("candidate artifact scope differs")
    path = _exact_string(files[0].get("path"), "candidate artifact path", None)
    pure = PurePosixPath(path)
    if not pure.is_absolute() or any(part in {".", ".."} for part in pure.parts):
        raise CutoverError("candidate artifact path differs")
    content = files[0].get("content_utf8")
    if type(content) is not str or unicodedata.normalize("NFC", content) != content:
        raise CutoverError("candidate artifact bytes differ")
    return pure.name, content.encode("utf-8")


def reconcile_proof(fixture: Mapping[str, object], handoff: Mapping[str, object]) -> Dict[str, object]:
    records = fixture.get("proof_records")
    if type(records) is not list or not records or len(records) > 32:
        raise CutoverError("proof graph differs")
    by_id: Dict[str, Mapping[str, object]] = {}
    for record in records:
        if type(record) is not dict or set(record) != {"proof_id", "subject_root", "depends_on"}:
            raise CutoverError("proof record differs")
        proof_id = _exact_string(record["proof_id"], "proof ID")
        _exact_string(record["subject_root"], "proof subject", SHA_RE)
        dependencies = record["depends_on"]
        if type(dependencies) is not list or any(type(item) is not str for item in dependencies):
            raise CutoverError("proof dependencies differ")
        if proof_id in by_id:
            raise CutoverError("proof ID repeats")
        by_id[proof_id] = record
    for record in records:
        for dependency in record["depends_on"]:
            if dependency not in by_id or dependency == record["proof_id"]:
                raise CutoverError("proof dependency differs")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(proof_id: str) -> None:
        if proof_id in visiting:
            raise CutoverError("proof dependency cycle differs")
        if proof_id in visited:
            return
        visiting.add(proof_id)
        for dependency in by_id[proof_id]["depends_on"]:
            visit(dependency)
        visiting.remove(proof_id)
        visited.add(proof_id)

    for proof_id in by_id:
        visit(proof_id)
    invalidated = {
        proof_id
        for proof_id, record in by_id.items()
        if record["subject_root"] == handoff["incumbent_root"]
    }
    changed = True
    while changed:
        changed = False
        for proof_id, record in by_id.items():
            if proof_id not in invalidated and any(
                dependency in invalidated for dependency in record["depends_on"]
            ):
                invalidated.add(proof_id)
                changed = True
    if not invalidated:
        raise CutoverError("affected proof closure is empty")
    preserved = sorted(set(by_id) - invalidated)
    return {
        "invalidated_proof_ids": sorted(invalidated),
        "preserved_proof_ids": preserved,
        "proof_graph_root": object_root(records),
    }


def _commit_paths(
    repo: Path,
    expected_head: str,
    paths: Sequence[str],
    message: str,
    *,
    failpoint: Optional[str] = None,
) -> str:
    ref = _git(repo, ["symbolic-ref", "-q", "HEAD"]).decode("utf-8")
    with tempfile.TemporaryDirectory(prefix="candidate-cutover-index-") as raw:
        index = Path(raw) / "index"
        env = dict(os.environ)
        env.update(
            {
                "GIT_INDEX_FILE": str(index),
                "GIT_AUTHOR_NAME": "Software Factory Target Owner",
                "GIT_AUTHOR_EMAIL": "software-factory@local.invalid",
                "GIT_COMMITTER_NAME": "Software Factory Target Owner",
                "GIT_COMMITTER_EMAIL": "software-factory@local.invalid",
            }
        )
        _git(repo, ["read-tree", expected_head], env=env)
        _git(repo, ["add", "--", *paths], env=env)
        tree = _git(repo, ["write-tree"], env=env).decode("ascii")
        commit = _git(
            repo,
            ["commit-tree", tree, "-p", expected_head, "-m", message],
            env=env,
        ).decode("ascii")
        if failpoint == "before-ref-update":
            raise CutoverError("injected interruption before target-owner commit")
        _git(repo, ["update-ref", ref, commit, expected_head])
    if failpoint == "after-ref-update":
        raise CutoverError("injected interruption after target-owner commit")
    _git(repo, ["reset", "-q", commit, "--", *paths])
    return _exact_string(commit, "cutover commit", REV_RE)


def _restore(path: Path, previous: Optional[bytes]) -> None:
    if previous is None:
        if path.exists() and not path.is_symlink():
            path.unlink()
        return
    _write_atomic(path, previous)


def _run_observable_effect(source: bytes, exercise: Mapping[str, object]) -> Dict[str, object]:
    workload = exercise.get("representative_workload")
    if type(workload) is not dict:
        raise CutoverError("representative workload differs")
    alphabet = workload["suffix_alphabet"].encode("ascii")
    repeated = workload["repeated_utf8"].encode("utf-8")
    rows = [
        (workload["index_format"] % index).encode("ascii")
        + repeated * workload["repeat_count"]
        + bytes([alphabet[index % len(alphabet)]]) * workload["suffix_repeat_count"]
        for index in range(workload["row_count"])
    ]
    namespace = {"zlib": zlib}
    try:
        exec(compile(source.decode("utf-8"), "<candidate-cutover>", "exec"), namespace)
        artifact = namespace["export"](rows)
        decompressed = zlib.decompress(artifact)
    except Exception as error:
        raise CutoverError("current target effect does not execute") from error
    if type(artifact) is not bytes:
        raise CutoverError("current target effect changed the bytes API")
    expected_payload = b"\n".join(rows)
    winner = exercise["artifacts"]["candidate-winning"]
    metrics = winner["mapped"]["metrics"]["observable-outcome"]
    if (
        decompressed != expected_payload
        or bytes_root(decompressed) != metrics["decompressed_sha256"]
        or len(artifact) != metrics["artifact_bytes"]
    ):
        raise CutoverError("current target effect differs from the accepted winner")
    return {
        "artifact_bytes": len(artifact),
        "decompressed_sha256": bytes_root(decompressed),
        "api_kind": "bytes",
        "protected_capability_results": [
            {"capability_id": "semantic-roundtrip", "result": "preserved"},
            {"capability_id": "stable-bytes-api", "result": "preserved"},
        ],
    }


def _resume_token(
    handoff_root: str, integration_commit: str, effect_root: str
) -> str:
    return object_root(
        {
            "schema_version": 1,
            "kind": "candidate-cutover-resume",
            "handoff_root": handoff_root,
            "integration_commit": integration_commit,
            "effect_root": effect_root,
            "destination_block": 9,
            "next_action": "continue-block-9-from-current-effect",
            "manual_resume_required": False,
        }
    )


def _result_from_current(repo: Path, state: Mapping[str, object], duplicate: bool) -> Dict[str, object]:
    outcome_path = repo / OUTCOME_RELATIVE
    outcome = _load_json(outcome_path)
    _validate_rooted_record(outcome, "effect_root", "cutover outcome")
    if (
        state.get("status") != "effect-accepted"
        or state.get("effect_root") != outcome.get("effect_root")
        or state.get("integration_commit") != outcome.get("integration_commit")
    ):
        raise CutoverError("cutover outcome currentness differs")
    integration_commit = _exact_string(
        state.get("integration_commit"), "integration commit", REV_RE
    )
    if subprocess.run(
        [GIT, "-C", str(repo), "merge-base", "--is-ancestor", integration_commit, "HEAD"],
        check=False,
        capture_output=True,
    ).returncode:
        raise CutoverError("cutover integration is no longer target history")
    expected_resume = _resume_token(
        state["handoff_root"], integration_commit, state["effect_root"]
    )
    if state.get("resume_token") != expected_resume:
        raise CutoverError("cutover resume currentness differs")
    return {
        "action": "cutover-current" if duplicate else "cutover-applied",
        "duplicate": duplicate,
        "integration_commit": integration_commit,
        "effect_root": state["effect_root"],
        "resume_token": state["resume_token"],
        "next_action": "continue-block-9-from-current-effect",
        "manual_resume_required": False,
        "candidate_authoritative": True,
        "incumbent_authoritative": False,
        "single_authority": True,
        "proof_reconciliation": state["proof_reconciliation"],
    }


def _apply_cutover_locked(
    target_repository: Path,
    tracker_path: Path,
    context_owner: Callable[[], Mapping[str, object]],
    *,
    failpoint: Optional[str] = None,
) -> Dict[str, object]:
    """Apply or resume one accepted candidate cutover through the target owner."""

    repo = _repo_root(target_repository)
    bundle = load_accepted_bundle()
    handoff = bundle["handoff"]
    incumbent_name, incumbent_bytes = _artifact_file(bundle, "incumbent")
    candidate_name, candidate_bytes = _artifact_file(bundle, "winner")
    if incumbent_name != candidate_name:
        raise CutoverError("candidate affected scope differs")
    relative = incumbent_name
    context = resolve_current_context(repo, tracker_path, context_owner, relative)
    refreshed_context = resolve_current_context(
        repo, tracker_path, context_owner, relative
    )
    if object_root(refreshed_context) != object_root(context):
        raise CutoverError("cutover context changed before target-owner write")
    if context["cutover_owner_id"] != handoff["target_owner_id"]:
        raise CutoverError("normal target owner differs")
    if context["structural_change"] is True:
        return {
            "action": "route-block-8",
            "structural_change": True,
            "application_authorized": False,
            "manual_resume_required": False,
        }
    state_path = repo / STATE_RELATIVE
    _control_directory(repo)
    existing = _safe_file(repo, STATE_RELATIVE, required=False)
    if existing is not None:
        state = _load_json(state_path)
        _validate_rooted_record(state, "state_root", "cutover state")
        if state.get("handoff_root") != handoff["handoff_root"]:
            raise CutoverError("another candidate cutover is already authoritative")
        for key in (
            "mission_root",
            "policy_root",
            "event_head_root",
            "tracker_sha256",
            "block9_contract_root",
            "target_owner_id",
        ):
            expected = context["cutover_owner_id"] if key == "target_owner_id" else context[key]
            if state.get(key) != expected:
                raise CutoverError("cutover currentness %s changed" % key)
        current_target = _safe_file(repo, relative)
        if current_target != candidate_bytes:
            raise CutoverError("authoritative candidate bytes changed")
        if state.get("integration_commit") is None and state.get("status") == "effect-pending":
            current_head = _head(repo)
            parent = _git(repo, ["rev-parse", "%s^" % current_head]).decode("ascii")
            if parent != state.get("pre_cutover_head"):
                raise CutoverError("interrupted integration ancestry differs")
            state["integration_commit"] = current_head
            state_without_root = dict(state)
            state_without_root.pop("state_root")
            state["state_root"] = object_root(state_without_root)
            _write_atomic(state_path, _json_bytes(state))
        integration_commit = _exact_string(
            state.get("integration_commit"), "integration commit", REV_RE
        )
        _git(repo, ["reset", "-q", "HEAD", "--", relative, STATE_RELATIVE])
        if state.get("status") == "effect-accepted":
            return _result_from_current(repo, state, True)
        if state.get("status") != "effect-pending":
            raise CutoverError("cutover state differs")
    else:
        current_target = _safe_file(repo, relative)
        if current_target != incumbent_bytes:
            raise CutoverError("incumbent target bytes are stale")
        proof_reconciliation = reconcile_proof(
            _load_json(CUTOVER_FIXTURE_PATH), handoff
        )
        before_head = _head(repo)
        state = {
            "schema_version": 1,
            "kind": "software-factory-candidate-cutover-state",
            "operation_id": "block9-cutover-%s" % handoff["handoff_root"][:20],
            "handoff_root": handoff["handoff_root"],
            "lane_head_root": bundle["lane_head"]["head_root"],
            "decision_fingerprint": handoff["decision_fingerprint"],
            "review_root": handoff["review_root"],
            "candidate_root": handoff["candidate_root"],
            "incumbent_root": handoff["incumbent_root"],
            "target_owner_id": handoff["target_owner_id"],
            "pre_cutover_head": before_head,
            "pre_cutover_target_state_root": context["target_state_root"],
            "tracker_sha256": context["tracker_sha256"],
            "block9_contract_root": context["block9_contract_root"],
            "mission_root": context["mission_root"],
            "policy_root": context["policy_root"],
            "event_head_root": context["event_head_root"],
            "affected_path": relative,
            "candidate_content_root": bytes_root(candidate_bytes),
            "incumbent_content_root": bytes_root(incumbent_bytes),
            "proof_reconciliation": proof_reconciliation,
            "incumbent_posture": "superseded-non-authoritative-history",
            "candidate_posture": "sole-authoritative-implementation",
            "status": "effect-pending",
            "integration_commit": None,
            "effect_root": None,
            "resume_token": None,
        }
        state["state_root"] = object_root(state)
        target_path = repo / relative
        prior_state = None
        try:
            _write_atomic(target_path, candidate_bytes)
            _write_atomic(state_path, _json_bytes(state))
            if failpoint == "after-write":
                raise CutoverError("injected interruption after cutover write")
            integration_commit = _commit_paths(
                repo,
                before_head,
                [relative, STATE_RELATIVE],
                "Cut over accepted bounded candidate",
                failpoint=(
                    failpoint
                    if failpoint in {"before-ref-update", "after-ref-update"}
                    else None
                ),
            )
        except CutoverError:
            if _head(repo) == before_head:
                _restore(target_path, incumbent_bytes)
                _restore(state_path, prior_state)
                _git(repo, ["reset", "-q", before_head, "--", relative, STATE_RELATIVE])
            raise
        state["integration_commit"] = integration_commit
        state_without_root = dict(state)
        state_without_root.pop("state_root")
        state["state_root"] = object_root(state_without_root)
        _write_atomic(state_path, _json_bytes(state))
        _git(repo, ["reset", "-q", "HEAD", "--", relative, STATE_RELATIVE])
        if failpoint == "after-integration":
            raise CutoverError("injected interruption after integration")
    effect = _run_observable_effect(candidate_bytes, bundle["exercise"])
    integration_commit = _exact_string(
        state.get("integration_commit"), "integration commit", REV_RE
    )
    outcome = {
        "schema_version": 1,
        "kind": "software-factory-candidate-cutover-outcome",
        "handoff_root": handoff["handoff_root"],
        "integration_commit": integration_commit,
        "target_head_observed": _head(repo),
        "candidate_content_root": bytes_root(candidate_bytes),
        "observable_effect": effect,
        "decision_posture": "accepted-current-effect",
    }
    outcome["effect_root"] = object_root(outcome)
    resume_token = _resume_token(
        handoff["handoff_root"], integration_commit, outcome["effect_root"]
    )
    pending_state_bytes = state_path.read_bytes()
    state["status"] = "effect-accepted"
    state["effect_root"] = outcome["effect_root"]
    state["resume_token"] = resume_token
    state_without_root = dict(state)
    state_without_root.pop("state_root")
    state["state_root"] = object_root(state_without_root)
    outcome_path = repo / OUTCOME_RELATIVE
    prior_outcome = _safe_file(repo, OUTCOME_RELATIVE, required=False)
    _write_atomic(state_path, _json_bytes(state))
    _write_atomic(outcome_path, _json_bytes(outcome))
    if failpoint == "before-outcome-commit":
        _write_atomic(state_path, pending_state_bytes)
        _restore(outcome_path, prior_outcome)
        raise CutoverError("injected interruption before outcome commit")
    current_head = _head(repo)
    _commit_paths(
        repo,
        current_head,
        [STATE_RELATIVE, OUTCOME_RELATIVE],
        "Record accepted candidate effect",
    )
    return _result_from_current(repo, state, False)


def claim_resume(
    target_repository: Path,
    resume_token: str,
    *,
    failpoint: Optional[str] = None,
) -> Dict[str, object]:
    """Claim the accepted continuation once; replays become a cheap no-op."""

    repo = _repo_root(target_repository)
    _exact_string(resume_token, "resume token", SHA_RE)
    git_dir_raw = _git(repo, ["rev-parse", "--git-dir"]).decode("utf-8")
    git_dir = Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    lock_path = git_dir.resolve(strict=True) / "software-factory-candidate-cutover.lock"
    descriptor = os.open(str(lock_path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        _control_directory(repo)
        state = _load_json(repo / STATE_RELATIVE)
        _validate_rooted_record(state, "state_root", "cutover state")
        if state.get("status") != "effect-accepted" or state.get("resume_token") != resume_token:
            raise CutoverError("resume token is not current")
        resume_path = repo / RESUME_RELATIVE
        existing = _safe_file(repo, RESUME_RELATIVE, required=False)
        if existing is not None:
            record = _load_json(resume_path)
            _validate_rooted_record(record, "claim_root", "resume claim")
            if record.get("resume_token") != resume_token:
                raise CutoverError("another resume token is already claimed")
            return {
                "action": "resume-already-claimed",
                "duplicate": True,
                "execute": False,
                "resume_token": resume_token,
            }
        record = {
            "schema_version": 1,
            "kind": "software-factory-candidate-cutover-resume-claim",
            "resume_token": resume_token,
            "handoff_root": state["handoff_root"],
            "integration_commit": state["integration_commit"],
            "effect_root": state["effect_root"],
            "destination_block": 9,
            "next_action": "continue-block-9-from-current-effect",
            "manual_resume_required": False,
        }
        record["claim_root"] = object_root(record)
        before_head = _head(repo)
        _write_atomic(resume_path, _json_bytes(record))
        try:
            _commit_paths(
                repo,
                before_head,
                [RESUME_RELATIVE],
                "Claim candidate cutover continuation",
                failpoint=failpoint,
            )
        except CutoverError:
            if _head(repo) == before_head:
                _restore(resume_path, None)
            raise
        return {
            "action": "resume-claimed",
            "duplicate": False,
            "execute": True,
            "resume_token": resume_token,
            "next_action": record["next_action"],
            "manual_resume_required": False,
        }
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def apply_cutover(
    target_repository: Path,
    tracker_path: Path,
    context_owner: Callable[[], Mapping[str, object]],
    *,
    failpoint: Optional[str] = None,
) -> Dict[str, object]:
    """Serialize the full target-owner cutover and its recovery phases."""

    repo = _repo_root(target_repository)
    git_dir_raw = _git(repo, ["rev-parse", "--git-dir"]).decode("utf-8")
    git_dir = Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    lock_path = git_dir.resolve(strict=True) / "software-factory-candidate-cutover.lock"
    descriptor = os.open(str(lock_path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return _apply_cutover_locked(
            repo, tracker_path, context_owner, failpoint=failpoint
        )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
