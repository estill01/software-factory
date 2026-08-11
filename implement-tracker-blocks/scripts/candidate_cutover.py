#!/usr/bin/env python3
"""Prepare, independently review, and atomically apply one Block 9 cutover."""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import hmac
import importlib.util
import json
import os
import re
import stat
import subprocess
import tempfile
import unicodedata
import zlib
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


class CutoverError(RuntimeError):
    """The candidate cannot be cut over at the current exact state."""


SKILL_ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_SNAPSHOT_PATH = SKILL_ROOT / "fixtures/bounded_candidate_accepted_v1.json"
EXACT_REVIEW_PATH = SKILL_ROOT / "fixtures/bounded_candidate_exact_review_v1.json"
EXERCISE_PATH = SKILL_ROOT / "fixtures/bounded_candidate_v1.json"
REVIEWER_PUBLIC_KEY_PATH = Path(
    "/Users/ethanstillman/.codex/software-factory-release-authority/reviewers/"
    "software-factory-release-reviewer-v1.pem"
)
REVIEWER_AUTHORITY_ROOT = REVIEWER_PUBLIC_KEY_PATH.parents[1]
REVIEWER_AUTHORITY_DIRECTORY = REVIEWER_PUBLIC_KEY_PATH.parent
TRUSTED_OPENSSL_PATH = Path("/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl")
SUPERVISION_ROOT = Path("/Users/ethanstillman/.codex/supervision/tracker-runs")
SUPERVISION_HELPER_PATH = (
    SKILL_ROOT.parent / "supervise-tracker-runs/scripts/supervision_log.py"
)
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
ACCEPTED_REVIEWER_PUBLIC_KEY_PATH = REVIEWER_PUBLIC_KEY_PATH
ACCEPTED_REVIEWER_AUTHORITY_ROOT = REVIEWER_AUTHORITY_ROOT
ACCEPTED_REVIEWER_AUTHORITY_DIRECTORY = REVIEWER_AUTHORITY_DIRECTORY
ACCEPTED_REVIEWER_KEY_SHA256 = EXPECTED_REVIEWER_KEY_SHA256
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
CONTINUATION_TRANSITION_ID = f"block9-cutover-{EXPECTED_HANDOFF_ROOT[:20]}"

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
MAX_INDEX_BYTES = 32 * 1024 * 1024
PROOF_RELATIVE = ".software-factory/proof-graph-v1.json"
OPERATION_DIRECTORY = "software-factory-candidate-cutover"


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
    value: object, name: str, pattern: Optional[re.Pattern[str]] = ID_RE
) -> str:
    if type(value) is not str or (pattern is not None and pattern.fullmatch(value) is None):
        raise CutoverError(f"{name} differs")
    return value


def _load_json(path: Path) -> Dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise CutoverError("evidence path differs")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise CutoverError("evidence exceeds the bounded size")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CutoverError("evidence JSON differs") from error
    if type(value) is not dict:
        raise CutoverError("evidence root must be an object")
    _validate_canonical(value)
    return value


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return canonical(dict(value)) + b"\n"


def _write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(
            path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_atomic_if_unchanged(path: Path, expected: bytes, raw: bytes) -> None:
    """Replace one owned file without overwriting bytes that arrived after snapshot."""

    if path.is_symlink() or not path.is_file():
        raise CutoverError("affected target path changed before reviewed write")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode)
    backup_descriptor, backup_name = tempfile.mkstemp(
        prefix=f".{path.name}.previous.", dir=str(path.parent)
    )
    os.close(backup_descriptor)
    os.unlink(backup_name)
    backup = Path(backup_name)
    temporary_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.replacement.", dir=str(path.parent)
    )
    installed = False
    try:
        os.fchmod(temporary_descriptor, mode)
        with os.fdopen(temporary_descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(path, backup)
        if backup.is_symlink() or not backup.is_file() or backup.read_bytes() != expected:
            if not path.exists() and not path.is_symlink():
                os.rename(backup, path)
            raise CutoverError("affected target bytes changed before reviewed write")
        try:
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise CutoverError("affected target bytes changed during reviewed write") from error
        installed = True
        backup.unlink()
    finally:
        if backup.exists() and not backup.is_symlink():
            if not path.exists() and not path.is_symlink():
                os.rename(backup, path)
            elif backup.read_bytes() == expected:
                backup.unlink()
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        if not installed and path.exists() and path.is_symlink():
            raise CutoverError("affected target path changed during reviewed write")


def _rooted(value: Mapping[str, object], field: str, name: str) -> Dict[str, object]:
    material = dict(value)
    recorded = material.pop(field, None)
    if _exact_string(recorded, f"{name} root", SHA_RE) != object_root(material):
        raise CutoverError(f"{name} root differs")
    return dict(value)


def _trusted_reviewer_identity(*, accepted_source: bool) -> Tuple[Path, str]:
    key_path = (
        ACCEPTED_REVIEWER_PUBLIC_KEY_PATH
        if accepted_source
        else REVIEWER_PUBLIC_KEY_PATH
    )
    authority_root = (
        ACCEPTED_REVIEWER_AUTHORITY_ROOT
        if accepted_source
        else REVIEWER_AUTHORITY_ROOT
    )
    authority_directory = (
        ACCEPTED_REVIEWER_AUTHORITY_DIRECTORY
        if accepted_source
        else REVIEWER_AUTHORITY_DIRECTORY
    )
    expected_key = (
        ACCEPTED_REVIEWER_KEY_SHA256
        if accepted_source
        else EXPECTED_REVIEWER_KEY_SHA256
    )
    if (
        authority_root.is_symlink()
        or not authority_root.is_dir()
        or authority_root.stat().st_mode & 0o222
        or authority_directory.is_symlink()
        or not authority_directory.is_dir()
        or authority_directory.stat().st_mode & 0o222
        or key_path.is_symlink()
        or not key_path.is_file()
        or key_path.stat().st_mode & 0o222
        or bytes_root(key_path.read_bytes()) != expected_key
        or TRUSTED_OPENSSL_PATH.is_symlink()
        or not TRUSTED_OPENSSL_PATH.is_file()
        or bytes_root(TRUSTED_OPENSSL_PATH.read_bytes()) != TRUSTED_OPENSSL_SHA256
    ):
        raise CutoverError("independent review identity differs")
    return key_path, expected_key


def _verify_reviewer_record(
    value: Mapping[str, object], *, root_field: str, signature_field: str,
    accepted_source: bool = False,
) -> None:
    key_path, _expected_key = _trusted_reviewer_identity(
        accepted_source=accepted_source
    )
    material = {
        key: item
        for key, item in value.items()
        if key not in {root_field, signature_field}
    }
    if value.get(root_field) != object_root(material):
        raise CutoverError("independent review root differs")
    signed = {key: item for key, item in value.items() if key != signature_field}
    try:
        signature = base64.b64decode(
            _exact_string(value.get(signature_field), "review signature", None),
            validate=True,
        )
    except (TypeError, ValueError) as error:
        raise CutoverError("independent review signature differs") from error
    if len(signature) != 64:
        raise CutoverError("independent review signature differs")
    with tempfile.TemporaryDirectory(prefix="candidate-cutover-review-") as raw:
        temporary = Path(raw)
        material_path = temporary / "material.json"
        signature_path = temporary / "signature.bin"
        material_path.write_bytes(canonical(signed))
        signature_path.write_bytes(signature)
        result = subprocess.run(
            [
                str(TRUSTED_OPENSSL_PATH),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(key_path),
                "-rawin",
                "-in",
                str(material_path),
                "-sigfile",
                str(signature_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
    if result.returncode:
        raise CutoverError("independent review signature differs")


def load_accepted_bundle() -> Dict[str, object]:
    snapshot = _load_json(ACCEPTED_SNAPSHOT_PATH)
    review = _load_json(EXACT_REVIEW_PATH)
    exercise = _load_json(EXERCISE_PATH)
    if object_root(snapshot) != EXPECTED_ACCEPTED_SNAPSHOT_ROOT:
        raise CutoverError("accepted candidate snapshot differs")
    if bytes_root(EXACT_REVIEW_PATH.read_bytes()) != EXPECTED_EXACT_REVIEW_SHA256:
        raise CutoverError("accepted candidate review bytes differ")
    _verify_reviewer_record(
        review,
        root_field="evidence_root_sha256",
        signature_field="signature_base64",
        accepted_source=True,
    )
    handoff = _rooted(snapshot.get("handoff", {}), "handoff_root", "handoff")
    lane_head = _rooted(snapshot.get("lane_head", {}), "head_root", "lane head")
    artifacts = exercise.get("artifacts")
    incumbent = exercise.get("incumbent")
    winner = artifacts.get("candidate-winning") if type(artifacts) is dict else None
    if type(incumbent) is not dict or type(winner) is not dict:
        raise CutoverError("accepted candidate source differs")
    if (
        handoff.get("handoff_root") != EXPECTED_HANDOFF_ROOT
        or lane_head.get("head_root") != EXPECTED_LANE_HEAD_ROOT
        or handoff.get("handoff_root") != lane_head.get("handoff_root")
        or handoff.get("candidate_root") != lane_head.get("candidate_root")
        or handoff.get("review_root") != lane_head.get("review_root")
        or handoff.get("currentness_root") != lane_head.get("currentness_root")
        or handoff.get("target_revision_root") != lane_head.get("target_revision_root")
        or handoff.get("destination_block") != 9
        or handoff.get("non_mutating") is not True
        or handoff.get("cutover_authority") is not False
        or review.get("review_disposition") != "accepted"
        or review.get("finding_count") != 0
        or review.get("winning_handoff_root") != handoff.get("handoff_root")
        or review.get("winning_lane_head_root") != lane_head.get("head_root")
        or review.get("winning_candidate_root") != handoff.get("candidate_root")
        or review.get("winning_final_currentness_root") != handoff.get("currentness_root")
        or review.get("exercise_root") != object_root(exercise)
    ):
        raise CutoverError("accepted candidate handoff differs")
    return {
        "snapshot": snapshot,
        "review": review,
        "exercise": exercise,
        "handoff": handoff,
        "lane_head": lane_head,
        "incumbent": incumbent,
        "winner": winner,
    }


def _git_raw(
    repo: Path,
    args: Sequence[str],
    *,
    env: Optional[Mapping[str, str]] = None,
    input_bytes: Optional[bytes] = None,
) -> bytes:
    run_env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    if env is not None:
        run_env.update(env)
    result = subprocess.run(
        [GIT, "-C", str(repo), *args],
        input=input_bytes,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=run_env,
    )
    if result.returncode:
        raise CutoverError("Git target-owner operation failed")
    return result.stdout


def _git(
    repo: Path,
    args: Sequence[str],
    *,
    env: Optional[Mapping[str, str]] = None,
    input_bytes: Optional[bytes] = None,
) -> bytes:
    return _git_raw(repo, args, env=env, input_bytes=input_bytes).strip()


def _repo_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise CutoverError("target repository root differs")
    resolved = path.resolve(strict=True)
    top = Path(_git(resolved, ["rev-parse", "--show-toplevel"]).decode())
    if top != resolved or top == Path("/"):
        raise CutoverError("target repository root differs")
    return resolved


def _head(repo: Path) -> str:
    return _exact_string(_git(repo, ["rev-parse", "HEAD"]).decode(), "target HEAD", REV_RE)


def _safe_file(repo: Path, relative: str, *, required: bool = True) -> Optional[bytes]:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in {".", ".."} for part in pure.parts):
        raise CutoverError("target path escapes repository")
    path = repo.joinpath(*pure.parts)
    if not path.exists() and not path.is_symlink():
        if required:
            raise CutoverError("target path is absent")
        return None
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True).parent == Path("/"):
        raise CutoverError("target path is not a contained regular file")
    try:
        path.resolve(strict=True).relative_to(repo)
    except ValueError as error:
        raise CutoverError("target path escapes repository") from error
    before = path.stat()
    if before.st_size > MAX_SOURCE_BYTES:
        raise CutoverError("target file exceeds the bounded size")
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(after):
        raise CutoverError("target file changed while reading")
    return raw


def _safe_tracker(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CutoverError("tracker path differs")
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if len(raw) > MAX_JSON_BYTES or (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise CutoverError("tracker changed while reading")
    return raw


def _normalized_block_root(raw: bytes, number: int) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CutoverError("tracker must be UTF-8") from error
    match = re.search(
        rf"^## Block {number} .*?(?=^## Block {number + 1} |\Z)", text, re.M | re.S
    )
    if match is None:
        raise CutoverError(f"Block {number} contract is absent")
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
    return bytes_root("\n".join(normalized).strip().encode())


def _tracker_program_root(raw: bytes) -> str:
    blocks = [
        {"block_number": number, "contract_root": _normalized_block_root(raw, number)}
        for number in range(18)
    ]
    return object_root({"schema_version": 1, "kind": "tracker-program-contracts", "blocks": blocks})


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


def _artifact_file(
    bundle: Mapping[str, object], which: str
) -> Tuple[str, str, bytes]:
    source = bundle[which]
    files = source.get("files") if type(source) is dict else None
    exercise = bundle["exercise"]
    if type(exercise) is not dict:
        raise CutoverError("accepted target source differs")
    if which == "incumbent":
        accepted_root = exercise.get("target_repository_root")
    else:
        lane = exercise.get("lane")
        accepted_root = lane.get("root") if type(lane) is dict else None
    if type(files) is not list or len(files) != 1 or type(files[0]) is not dict:
        raise CutoverError("candidate artifact scope differs")
    full = _exact_string(files[0].get("path"), "candidate artifact path", None)
    root = _exact_string(accepted_root, "accepted target repository root", None)
    pure = PurePosixPath(full)
    root_pure = PurePosixPath(root)
    if not pure.is_absolute() or not root_pure.is_absolute():
        raise CutoverError("accepted target path differs")
    try:
        relative = pure.relative_to(root_pure)
    except ValueError as error:
        raise CutoverError("accepted target path differs") from error
    if not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise CutoverError("accepted target path differs")
    content = files[0].get("content_utf8")
    if type(content) is not str or unicodedata.normalize("NFC", content) != content:
        raise CutoverError("candidate artifact bytes differ")
    return full, relative.as_posix(), content.encode()


def _supervision_module() -> ModuleType:
    path = SUPERVISION_HELPER_PATH.resolve(strict=True)
    spec = importlib.util.spec_from_file_location("candidate_cutover_supervision", path)
    if spec is None or spec.loader is None:
        raise CutoverError("canonical supervision owner is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _supervision_snapshot(
    module: ModuleType, *, owner_id: str, repo: Path, tracker_path: Path
) -> Tuple[Dict[str, object], Path, tuple[int, int, int, int]]:
    args = argparse.Namespace(root=str(SUPERVISION_ROOT), target_thread=owner_id)
    try:
        directory, policy, _policy_snapshot, all_events, _event_snapshot, directory_snapshot = (
            module.load_control_snapshot(args)
        )
        active = module.mission_scoped_events(directory, policy, all_events)
        mission = module.bound_mission(policy)
        anchor = module.read_json(directory / module.EVENT_LEDGER_ANCHOR_NAME)
        module.validate_event_ledger_anchor(directory, all_events, allow_missing=False)
        owner_roots = module.events(directory / module.OWNER_ROOT_HISTORY_NAME)
        range_state = module.implementation_range_state(policy)
        transition_records = module.successor_transition_events(
            active, CONTINUATION_TRANSITION_ID
        )
    except Exception as error:
        raise CutoverError("canonical supervision context is unavailable") from error
    control = policy.get("adaptive_decision_control")
    if (
        policy.get("target_thread_id") != owner_id
        or not isinstance(mission, dict)
        or not isinstance(control, dict)
        or control.get("target_class") != "target-repository"
        or control.get("target_repository_root") != str(repo)
        or not owner_roots
        or not isinstance(range_state, dict)
        or not transition_records
    ):
        raise CutoverError("canonical supervision target owner differs")
    if (
        Path(str(range_state.get("tracker_path", ""))).resolve(strict=True)
        != tracker_path.resolve(strict=True)
        or 9 not in range_state.get("requested_blocks", [])
        or range_state.get("eligible_blocks") != [9]
        or 9 not in range_state.get("remaining_blocks", [])
    ):
        raise CutoverError("canonical implementation range does not own Block 9")
    required_transition = transition_records[0]
    transition_head = transition_records[-1]
    if (
        required_transition.get("phase") != "required"
        or required_transition.get("topology_posture") != "same-task-new-run"
        or required_transition.get("topology_basis") != "same-task-default"
        or required_transition.get("first_eligible_block") != "Block 9"
        or required_transition.get("tracker_sha256") != range_state["tracker_sha256"]
        or transition_head.get("phase") not in {"required", "work-started"}
    ):
        raise CutoverError("canonical Block 9 continuation transition differs")
    stable_owner_event_head = (
        transition_head.get("previous_record_sha256")
        if transition_head.get("phase") == "work-started"
        else all_events[-1].get("record_sha256")
    )
    stable_owner_roots = [
        item
        for item in owner_roots
        if item.get("event_head_sha256") == stable_owner_event_head
    ]
    if not stable_owner_roots:
        raise CutoverError("canonical Block 9 continuation owner root differs")
    non_transition_roots = [
        item["record_sha256"]
        for item in active
        if not (
            item.get("kind") == "successor-transition"
            and item.get("transition_id") == CONTINUATION_TRANSITION_ID
        )
    ]
    range_root = object_root(range_state)
    context: Dict[str, object] = {
        "target_owner_id": owner_id,
        "mission_root": mission["mission_root"],
        "policy_root": policy["policy_sha256"],
        "event_head_root": object_root({"record_roots": non_transition_roots}),
        "owner_root_head": stable_owner_roots[-1]["record_sha256"],
        "active_event_count": len(non_transition_roots),
        "implementation_range": range_state,
        "implementation_range_root": range_root,
        "continuation_transition_required_root": required_transition[
            "record_sha256"
        ],
    }
    for field in (
        "mission_root",
        "policy_root",
        "event_head_root",
        "owner_root_head",
        "implementation_range_root",
        "continuation_transition_required_root",
    ):
        _exact_string(context[field], f"supervision {field}", SHA_RE)
    return context, directory, directory_snapshot


def _operation_directory(repo: Path) -> Path:
    raw = _git(repo, ["rev-parse", "--git-dir"]).decode()
    git_dir = Path(raw)
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    git_dir = git_dir.resolve(strict=True)
    path = git_dir / OPERATION_DIRECTORY
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
            raise CutoverError("cutover evidence directory differs")
    else:
        path.mkdir(mode=0o700)
    return path


def _operation_lock(repo: Path) -> int:
    lock = _operation_directory(repo) / "operation.lock"
    return os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)


def _proposal_path(repo: Path) -> Path:
    return _operation_directory(repo) / f"{EXPECTED_HANDOFF_ROOT}.proposal.json"


def _outcome_path(repo: Path) -> Path:
    return _operation_directory(repo) / f"{EXPECTED_HANDOFF_ROOT}.outcome.json"


def _review_copy_path(repo: Path) -> Path:
    return _operation_directory(repo) / f"{EXPECTED_HANDOFF_ROOT}.review.json"


def _effect_path(repo: Path) -> Path:
    return _operation_directory(repo) / f"{EXPECTED_HANDOFF_ROOT}.effect.json"


def _effect_pending_path(repo: Path) -> Path:
    return _operation_directory(repo) / f"{EXPECTED_HANDOFF_ROOT}.effect.pending.json"


def _validate_proof_graph(value: Mapping[str, object]) -> Dict[str, object]:
    graph = _rooted(value, "graph_root", "target proof graph")
    if set(graph) != {
        "schema_version",
        "kind",
        "records",
        "graph_root",
    } or graph.get("schema_version") != 1 or graph.get("kind") != "target-proof-graph":
        raise CutoverError("target proof graph differs")
    records = graph.get("records")
    if type(records) is not list or not records or len(records) > 64:
        raise CutoverError("target proof records differ")
    identifiers: set[str] = set()
    for record in records:
        if type(record) is not dict or set(record) != {
            "proof_id",
            "subject_root",
            "depends_on",
            "currentness",
        }:
            raise CutoverError("target proof record differs")
        proof_id = _exact_string(record["proof_id"], "proof ID")
        _exact_string(record["subject_root"], "proof subject", SHA_RE)
        dependencies = record["depends_on"]
        if (
            proof_id in identifiers
            or type(dependencies) is not list
            or dependencies != sorted(set(dependencies))
            or any(type(item) is not str for item in dependencies)
            or record["currentness"] not in {"current", "stale"}
        ):
            raise CutoverError("target proof record differs")
        identifiers.add(proof_id)
    if any(
        dependency not in identifiers or dependency == record["proof_id"]
        for record in records
        for dependency in record["depends_on"]
    ):
        raise CutoverError("target proof dependency differs")
    by_id = {record["proof_id"]: record for record in records}
    if any(
        record["currentness"] == "current"
        and any(by_id[dependency]["currentness"] != "current" for dependency in record["depends_on"])
        for record in records
    ):
        raise CutoverError("current target proof depends on stale proof")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(proof_id: str) -> None:
        if proof_id in visiting:
            raise CutoverError("target proof dependency cycle differs")
        if proof_id in visited:
            return
        visiting.add(proof_id)
        for dependency in by_id[proof_id]["depends_on"]:
            visit(dependency)
        visiting.remove(proof_id)
        visited.add(proof_id)

    for proof_id in sorted(by_id):
        visit(proof_id)
    return graph


def reconcile_proof(
    graph: Mapping[str, object], *, incumbent_root: str
) -> Tuple[Dict[str, object], Dict[str, object]]:
    before = _validate_proof_graph(graph)
    records = before["records"]
    invalidated = {
        record["proof_id"]
        for record in records
        if record["currentness"] == "current" and record["subject_root"] == incumbent_root
    }
    changed = True
    while changed:
        changed = False
        for record in records:
            if (
                record["proof_id"] not in invalidated
                and record["currentness"] == "current"
                and any(dependency in invalidated for dependency in record["depends_on"])
            ):
                invalidated.add(record["proof_id"])
                changed = True
    if not invalidated:
        raise CutoverError("current target proof has no affected incumbent closure")
    after_records = [
        {
            **record,
            "currentness": (
                "stale" if record["proof_id"] in invalidated else record["currentness"]
            ),
        }
        for record in records
    ]
    after: Dict[str, object] = {
        "schema_version": 1,
        "kind": "target-proof-graph",
        "records": after_records,
    }
    after["graph_root"] = object_root(after)
    reconciliation = {
        "before_graph_root": before["graph_root"],
        "after_graph_root": after["graph_root"],
        "invalidated_proof_ids": sorted(invalidated),
        "preserved_proof_ids": sorted(
            record["proof_id"]
            for record in records
            if record["proof_id"] not in invalidated
            and record["currentness"] == "current"
        ),
    }
    return after, reconciliation


def _paths_clean(repo: Path, head: str, paths: Sequence[str]) -> None:
    for staged in (False, True):
        args = ["diff", "--quiet"]
        if staged:
            args.append("--cached")
        args.extend([head, "--", *paths])
        result = subprocess.run(
            [GIT, "-C", str(repo), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        if result.returncode != 0:
            raise CutoverError("affected target or index contains user changes")


def _prepare_commit(
    repo: Path,
    head: str,
    replacements: Mapping[str, bytes],
) -> str:
    with tempfile.TemporaryDirectory(prefix="candidate-cutover-preparation-") as raw:
        temporary = Path(raw)
        index = temporary / "index"
        env = {
            "GIT_INDEX_FILE": str(index),
            "GIT_AUTHOR_NAME": "Software Factory Target Owner",
            "GIT_AUTHOR_EMAIL": "software-factory@local.invalid",
            "GIT_COMMITTER_NAME": "Software Factory Target Owner",
            "GIT_COMMITTER_EMAIL": "software-factory@local.invalid",
        }
        _git(repo, ["read-tree", head], env=env)
        for offset, (relative, content) in enumerate(sorted(replacements.items())):
            source = temporary / f"content-{offset}"
            source.write_bytes(content)
            blob = _git(repo, ["hash-object", "-w", str(source)]).decode()
            _git(
                repo,
                ["update-index", "--add", "--cacheinfo", f"100644,{blob},{relative}"],
                env=env,
            )
        tree = _git(repo, ["write-tree"], env=env).decode()
        commit = _git(
            repo,
            ["commit-tree", tree, "-p", head, "-m", "Cut over reviewed bounded candidate"],
            env=env,
        ).decode()
    return _exact_string(commit, "prepared integration commit", REV_RE)


def _diff_root(repo: Path, parent: str, commit: str, paths: Sequence[str]) -> str:
    return bytes_root(
        _git(repo, ["diff", "--binary", parent, commit, "--", *paths])
    )


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
        exec(compile(source.decode(), "<candidate-cutover-current-target>", "exec"), namespace)
        artifact = namespace["export"](rows)
        decompressed = zlib.decompress(artifact)
    except Exception as error:
        raise CutoverError("current target effect does not execute") from error
    metrics = exercise["artifacts"]["candidate-winning"]["mapped"]["metrics"]["observable-outcome"]
    if (
        type(artifact) is not bytes
        or decompressed != b"\n".join(rows)
        or bytes_root(decompressed) != metrics["decompressed_sha256"]
        or len(artifact) != metrics["artifact_bytes"]
    ):
        raise CutoverError("current target effect differs from accepted winner")
    return {
        "artifact_bytes": len(artifact),
        "decompressed_sha256": bytes_root(decompressed),
        "api_kind": "bytes",
        "protected_capability_results": [
            {"capability_id": "semantic-roundtrip", "result": "preserved"},
            {"capability_id": "stable-bytes-api", "result": "preserved"},
        ],
    }


def _validate_prepared_commit(
    repo: Path,
    proposal: Mapping[str, object],
    replacements: Mapping[str, bytes],
) -> None:
    parent = _git(repo, ["rev-parse", f"{proposal['prepared_commit']}^"]).decode()
    if parent != proposal["target_head"]:
        raise CutoverError("prepared integration ancestry differs")
    changed = _git(
        repo,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", proposal["prepared_commit"]],
    ).decode().splitlines()
    if changed != sorted(replacements):
        raise CutoverError("prepared integration scope differs")
    for relative, content in replacements.items():
        committed = _git(repo, ["show", f"{proposal['prepared_commit']}:{relative}"])
        if committed != content.rstrip(b"\n") and committed + b"\n" != content:
            raise CutoverError("prepared integration bytes differ")
    if _diff_root(
        repo,
        str(proposal["target_head"]),
        str(proposal["prepared_commit"]),
        sorted(replacements),
    ) != proposal["integration_diff_root"]:
        raise CutoverError("prepared integration diff differs")


def prepare_cutover(target_repository: Path, tracker_path: Path) -> Dict[str, object]:
    """Create one detached, non-authoritative commit for exact independent review."""

    repo = _repo_root(target_repository)
    bundle = load_accepted_bundle()
    handoff = bundle["handoff"]
    owner_id = _exact_string(handoff["target_owner_id"], "target owner")
    descriptor = _operation_lock(repo)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        module = _supervision_module()
        _initial, _directory, directory_snapshot = _supervision_snapshot(
            module, owner_id=owner_id, repo=repo, tracker_path=tracker_path
        )
        try:
            owner_lock = module.owner_append_lock(
                SUPERVISION_ROOT, owner_id, directory_snapshot
            )
            with owner_lock:
                supervision, _directory, _snapshot = _supervision_snapshot(
                    module, owner_id=owner_id, repo=repo, tracker_path=tracker_path
                )
                tracker_raw = _safe_tracker(tracker_path)
                if _normalized_block_root(tracker_raw, 9) != EXPECTED_BLOCK9_CONTRACT_ROOT:
                    raise CutoverError("Block 9 contract requires structural amendment")
                accepted_incumbent_path, relative, incumbent_bytes = _artifact_file(
                    bundle, "incumbent"
                )
                accepted_candidate_path, candidate_relative, candidate_bytes = _artifact_file(
                    bundle, "winner"
                )
                if relative != candidate_relative:
                    raise CutoverError("candidate affected scope differs")
                head = _head(repo)
                current = _safe_file(repo, relative)
                if current != incumbent_bytes:
                    raise CutoverError("current target is not the accepted incumbent")
                committed = _git(repo, ["show", f"{head}:{relative}"])
                if committed != incumbent_bytes.rstrip(b"\n") and committed + b"\n" != incumbent_bytes:
                    raise CutoverError("current target revision is not the accepted incumbent")
                proof_bytes = _safe_file(repo, PROOF_RELATIVE)
                assert proof_bytes is not None
                proof = _validate_proof_graph(
                    json.loads(proof_bytes.decode(), object_pairs_hook=_reject_duplicate_pairs)
                )
                proof_after, reconciliation = reconcile_proof(
                    proof, incumbent_root=str(handoff["incumbent_root"])
                )
                paths = sorted([relative, PROOF_RELATIVE])
                _paths_clean(repo, head, paths)
                replacements = {
                    relative: candidate_bytes,
                    PROOF_RELATIVE: _json_bytes(proof_after),
                }
                prepared = _prepare_commit(repo, head, replacements)
                proposal: Dict[str, object] = {
                    "schema_version": 1,
                    "kind": "software-factory-candidate-cutover-proposal",
                    "handoff_root": handoff["handoff_root"],
                    "lane_head_root": bundle["lane_head"]["head_root"],
                    "decision_fingerprint": handoff["decision_fingerprint"],
                    "review_root": handoff["review_root"],
                    "candidate_root": handoff["candidate_root"],
                    "incumbent_root": handoff["incumbent_root"],
                    "accepted_target_revision_root": handoff["target_revision_root"],
                    "accepted_target_repository_root": bundle["exercise"]["target_repository_root"],
                    "accepted_incumbent_path": accepted_incumbent_path,
                    "accepted_candidate_path": accepted_candidate_path,
                    "target_repository_root": str(repo),
                    "target_head": head,
                    "target_state_root": _target_state_root(head, relative, incumbent_bytes),
                    "affected_path": relative,
                    "incumbent_content_root": bytes_root(incumbent_bytes),
                    "candidate_content_root": bytes_root(candidate_bytes),
                    "tracker_path": str(tracker_path.resolve(strict=True)),
                    "tracker_sha256": bytes_root(tracker_raw),
                    "tracker_program_root": _tracker_program_root(tracker_raw),
                    "block9_contract_root": EXPECTED_BLOCK9_CONTRACT_ROOT,
                    "implementation_range_root": supervision[
                        "implementation_range_root"
                    ],
                    "supervision_context": supervision,
                    "proof_reconciliation": reconciliation,
                    "prepared_commit": prepared,
                    "integration_diff_root": _diff_root(repo, head, prepared, paths),
                    "changed_paths": paths,
                }
                proposal["proposal_root"] = object_root(proposal)
                existing_path = _proposal_path(repo)
                if existing_path.exists():
                    existing = _rooted(_load_json(existing_path), "proposal_root", "cutover proposal")
                    if existing != proposal:
                        raise CutoverError("another cutover proposal is already current")
                else:
                    _write_atomic(existing_path, _json_bytes(proposal))
        except CutoverError:
            raise
        except Exception as error:
            raise CutoverError("canonical target-owner preparation failed") from error
        return {
            "action": "independent-integration-review-required",
            "application_authorized": False,
            "proposal_root": proposal["proposal_root"],
            "prepared_commit": proposal["prepared_commit"],
            "integration_diff_root": proposal["integration_diff_root"],
            "proposal_path": str(_proposal_path(repo)),
        }
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


REVIEW_FIELDS = {
    "schema_version",
    "kind",
    "record_id",
    "proposal_root",
    "prepared_commit",
    "integration_diff_root",
    "handoff_root",
    "target_repository_root",
    "target_head",
    "target_state_root",
    "tracker_program_root",
    "implementation_range_root",
    "proof_before_root",
    "proof_after_root",
    "reviewer_id",
    "review_disposition",
    "finding_count",
    "authority_key_sha256",
    "observed_at",
    "review_root",
    "signature_base64",
}


def load_integration_review(path: Path, proposal: Mapping[str, object]) -> Dict[str, object]:
    review = _load_json(path)
    if set(review) != REVIEW_FIELDS:
        raise CutoverError("integration review fields differ")
    _verify_reviewer_record(review, root_field="review_root", signature_field="signature_base64")
    comparisons = {
        "proposal_root": proposal["proposal_root"],
        "prepared_commit": proposal["prepared_commit"],
        "integration_diff_root": proposal["integration_diff_root"],
        "handoff_root": proposal["handoff_root"],
        "target_repository_root": proposal["target_repository_root"],
        "target_head": proposal["target_head"],
        "target_state_root": proposal["target_state_root"],
        "tracker_program_root": proposal["tracker_program_root"],
        "implementation_range_root": proposal["implementation_range_root"],
        "proof_before_root": proposal["proof_reconciliation"]["before_graph_root"],
        "proof_after_root": proposal["proof_reconciliation"]["after_graph_root"],
    }
    if (
        review.get("schema_version") != 1
        or review.get("kind") != "software-factory-candidate-cutover-integration-review"
        or review.get("reviewer_id") != "software-factory-release-reviewer-v1"
        or review.get("review_disposition") != "accepted"
        or type(review.get("finding_count")) is not int
        or review.get("finding_count") != 0
        or review.get("authority_key_sha256") != EXPECTED_REVIEWER_KEY_SHA256
        or any(review.get(field) != expected for field, expected in comparisons.items())
    ):
        raise CutoverError("integration review is not accepted for the current proposal")
    _exact_string(review.get("record_id"), "integration review ID")
    _exact_string(review.get("observed_at"), "integration review timestamp", None)
    return review


def _proposal_replacements(
    bundle: Mapping[str, object], proposal: Mapping[str, object], proof_after: Mapping[str, object]
) -> Dict[str, bytes]:
    _full, relative, candidate = _artifact_file(bundle, "winner")
    if relative != proposal["affected_path"]:
        raise CutoverError("proposal affected path differs")
    return {relative: candidate, PROOF_RELATIVE: _json_bytes(proof_after)}


def _restore_paths(repo: Path, head: str, paths: Sequence[str]) -> None:
    for relative in paths:
        try:
            content = _git(repo, ["show", f"{head}:{relative}"])
        except CutoverError:
            path = repo / relative
            if path.exists() and not path.is_symlink():
                path.unlink()
            continue
        path = repo / relative
        _write_atomic(path, content + b"\n" if content and not content.endswith(b"\n") else content)
    _git(repo, ["reset", "-q", head, "--", *paths])


def _restore_owned_replacements(
    repo: Path,
    head: str,
    previous: Mapping[str, Optional[bytes]],
    replacements: Mapping[str, bytes],
    expected_index: bytes,
) -> None:
    """Restore only bytes still owned by this operation; preserve later caller work."""

    failures: List[str] = []
    for relative, prior in previous.items():
        path = repo / relative
        try:
            current = _safe_file(repo, relative, required=False)
            replacement = replacements[relative]
            if current != replacement:
                continue
            if prior is None:
                if path.exists() and not path.is_symlink():
                    path.unlink()
            else:
                _write_atomic_if_unchanged(path, replacement, prior)
        except Exception:
            failures.append(relative)
            continue
    _restore_index_paths_if_unchanged(
        repo,
        expected_index,
        head,
        sorted(previous),
    )
    if failures:
        raise CutoverError(
            "concurrent affected paths were preserved while owned writes were restored: "
            + ", ".join(sorted(failures))
        )


def _tree_path_bytes(repo: Path, head: str, relative: str) -> Optional[bytes]:
    entry = _git_raw(repo, ["ls-tree", "-z", head, "--", relative])
    if not entry:
        return None
    expected_suffix = b"\t" + relative.encode("utf-8") + b"\0"
    if entry.count(b"\0") != 1 or not entry.endswith(expected_suffix) or b" blob " not in entry:
        raise CutoverError("surviving target tree path differs during recovery")
    return _git_raw(repo, ["show", f"{head}:{relative}"])


def _index_path(repo: Path) -> Path:
    path = _operation_directory(repo).parent / "index"
    if path.is_symlink() or not path.is_file():
        raise CutoverError("target index differs")
    return path


def _index_bytes(repo: Path) -> bytes:
    path = _index_path(repo)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    if len(raw) > MAX_INDEX_BYTES or identity(before) != identity(after):
        raise CutoverError("target index changed while reading")
    return raw


def _updated_index_bytes(
    repo: Path,
    source: bytes,
    target_head: str,
    paths: Sequence[str],
) -> bytes:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="candidate-cutover-index.", dir=str(_operation_directory(repo))
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
        _git(
            repo,
            ["reset", "-q", target_head, "--", *paths],
            env={"GIT_INDEX_FILE": str(temporary)},
        )
        raw = temporary.read_bytes()
        if len(raw) > MAX_INDEX_BYTES:
            raise CutoverError("updated target index exceeds the bounded size")
        return raw
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()


def _index_lock(repo: Path) -> Tuple[int, Path]:
    lock = _index_path(repo).with_name("index.lock")
    try:
        descriptor = os.open(
            lock,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as error:
        raise CutoverError("target index owner is busy") from error
    return descriptor, lock


def _replace_index_if_unchanged(
    repo: Path,
    expected: bytes,
    replacement: bytes,
) -> None:
    descriptor, lock = _index_lock(repo)
    try:
        if _index_bytes(repo) != expected:
            raise CutoverError("affected target index changed")
        _write_atomic_if_unchanged(_index_path(repo), expected, replacement)
    finally:
        os.close(descriptor)
        if lock.exists() and not lock.is_symlink():
            lock.unlink()


def _restore_index_paths_if_unchanged(
    repo: Path,
    expected: bytes,
    target_head: str,
    paths: Sequence[str],
) -> None:
    if _index_bytes(repo) != expected:
        return
    replacement = _updated_index_bytes(repo, expected, target_head, paths)
    _replace_index_if_unchanged(repo, expected, replacement)


def _promote_ref_and_index(
    repo: Path,
    ref: str,
    target_head: str,
    expected_head: str,
    expected_index: bytes,
    paths: Sequence[str],
) -> bytes:
    replacement = _updated_index_bytes(repo, expected_index, target_head, paths)
    descriptor, lock = _index_lock(repo)
    promoted = False
    try:
        if _index_bytes(repo) != expected_index:
            raise CutoverError("affected target index changed before promotion")
        _git(repo, ["update-ref", ref, target_head, expected_head])
        promoted = True
        if _head(repo) != target_head or _index_bytes(repo) != expected_index:
            raise CutoverError("target ref or index changed during promotion")
        _write_atomic_if_unchanged(_index_path(repo), expected_index, replacement)
        return replacement
    except Exception:
        if promoted and _head(repo) == target_head:
            try:
                _git(repo, ["update-ref", ref, expected_head, target_head])
            except CutoverError:
                pass
        raise
    finally:
        os.close(descriptor)
        if lock.exists() and not lock.is_symlink():
            lock.unlink()


def _restore_owned_replacements_to_current_head(
    repo: Path,
    original_head: str,
    previous: Mapping[str, Optional[bytes]],
    replacements: Mapping[str, bytes],
    expected_index: bytes,
) -> None:
    surviving_head = _head(repo)
    desired = (
        dict(previous)
        if surviving_head == original_head
        else {
            relative: _tree_path_bytes(repo, surviving_head, relative)
            for relative in previous
        }
    )
    _restore_owned_replacements(
        repo,
        surviving_head,
        desired,
        replacements,
        expected_index,
    )


def _expected_effect(exercise: Mapping[str, object]) -> Dict[str, object]:
    metrics = exercise["artifacts"]["candidate-winning"]["mapped"]["metrics"][
        "observable-outcome"
    ]
    return {
        "artifact_bytes": metrics["artifact_bytes"],
        "decompressed_sha256": metrics["decompressed_sha256"],
        "api_kind": "bytes",
        "protected_capability_results": [
            {"capability_id": "semantic-roundtrip", "result": "preserved"},
            {"capability_id": "stable-bytes-api", "result": "preserved"},
        ],
    }


def _retain_review_copy(repo: Path, review: Mapping[str, object]) -> None:
    path = _review_copy_path(repo)
    raw = _json_bytes(review)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise CutoverError("retained integration review differs")
        return
    _write_atomic(path, raw)


def _validate_effect_record(
    value: Mapping[str, object],
    identity: Mapping[str, object],
    expected_effect: Mapping[str, object],
    owner_key: bytes,
) -> Dict[str, object]:
    retained = _rooted(value, "effect_validation_root", "cutover effect validation")
    if set(retained) != {
        *identity,
        "producer_recorded_at",
        "observable_effect",
        "owner_hmac_sha256",
        "effect_validation_root",
    }:
        raise CutoverError("retained cutover effect validation shape differs")
    signed = {
        key: retained[key]
        for key in retained
        if key not in {"owner_hmac_sha256", "effect_validation_root"}
    }
    expected_hmac = hmac.new(owner_key, canonical(signed), hashlib.sha256).hexdigest()
    if (
        {key: retained.get(key) for key in identity} != dict(identity)
        or retained.get("observable_effect") != dict(expected_effect)
        or type(retained.get("producer_recorded_at")) is not str
        or not hmac.compare_digest(
            str(retained.get("owner_hmac_sha256", "")), expected_hmac
        )
    ):
        raise CutoverError("retained cutover effect validation provenance differs")
    return retained


def _produce_durable_effect(
    repo: Path,
    proposal: Mapping[str, object],
    review: Mapping[str, object],
    bundle: Mapping[str, object],
    committed: bytes,
    module: ModuleType,
    directory_fd: int,
) -> Dict[str, object]:
    identity = {
        "schema_version": 1,
        "kind": "software-factory-candidate-cutover-effect-validation",
        "proposal_root": proposal["proposal_root"],
        "integration_commit": proposal["prepared_commit"],
        "integration_review_root": review["review_root"],
        "candidate_content_root": proposal["candidate_content_root"],
    }
    effect = _run_observable_effect(committed, bundle["exercise"])
    record: Dict[str, object] = {
        **identity,
        "producer_recorded_at": module.utc_now(),
        "observable_effect": effect,
    }
    owner_key = module.owner_root_key_at(directory_fd, allow_create=False)
    record["owner_hmac_sha256"] = hmac.new(
        owner_key, canonical(record), hashlib.sha256
    ).hexdigest()
    record["effect_validation_root"] = object_root(record)
    pending_path = _effect_pending_path(repo)
    _write_atomic(pending_path, _json_bytes(record))
    return _validate_effect_record(
        _load_json(pending_path),
        identity,
        _expected_effect(bundle["exercise"]),
        owner_key,
    )


def _load_or_produce_effect(
    repo: Path,
    proposal: Mapping[str, object],
    review: Mapping[str, object],
    bundle: Mapping[str, object],
    committed: bytes,
    module: ModuleType,
    directory_fd: int,
) -> Dict[str, object]:
    path = _effect_path(repo)
    pending_path = _effect_pending_path(repo)
    identity = {
        "schema_version": 1,
        "kind": "software-factory-candidate-cutover-effect-validation",
        "proposal_root": proposal["proposal_root"],
        "integration_commit": proposal["prepared_commit"],
        "integration_review_root": review["review_root"],
        "candidate_content_root": proposal["candidate_content_root"],
    }
    owner_key = module.owner_root_key_at(directory_fd, allow_create=False)
    expected_effect = _expected_effect(bundle["exercise"])
    if path.exists():
        return _validate_effect_record(
            _load_json(path), identity, expected_effect, owner_key
        )
    if pending_path.exists():
        retained = _validate_effect_record(
            _load_json(pending_path), identity, expected_effect, owner_key
        )
    else:
        retained = _produce_durable_effect(
            repo,
            proposal,
            review,
            bundle,
            committed,
            module,
            directory_fd,
        )
    _write_atomic(path, _json_bytes(retained))
    validated = _validate_effect_record(
        _load_json(path), identity, expected_effect, owner_key
    )
    if pending_path.exists() and not pending_path.is_symlink():
        pending_path.unlink()
        directory_descriptor = os.open(
            pending_path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    return validated


def _assert_current_cutover(
    repo: Path,
    tracker_path: Path,
    proposal: Mapping[str, object],
    bundle: Mapping[str, object],
    module: ModuleType,
    owner_id: str,
    supervision: Mapping[str, object],
) -> Dict[str, object]:
    if _head(repo) != proposal["prepared_commit"]:
        raise CutoverError("reviewed integration is not the current target revision")
    _full, relative, candidate = _artifact_file(bundle, "winner")
    committed = _git(repo, ["show", f"HEAD:{relative}"])
    live = _safe_file(repo, relative)
    if live != candidate or (
        committed != candidate.rstrip(b"\n") and committed + b"\n" != candidate
    ):
        raise CutoverError("current target differs from the reviewed candidate")
    proof = _validate_proof_graph(_load_json(repo / PROOF_RELATIVE))
    if proof["graph_root"] != proposal["proof_reconciliation"]["after_graph_root"]:
        raise CutoverError("current target proof reconciliation differs")
    tracker_raw = _safe_tracker(tracker_path)
    if (
        _normalized_block_root(tracker_raw, 9) != EXPECTED_BLOCK9_CONTRACT_ROOT
        or _tracker_program_root(tracker_raw) != proposal["tracker_program_root"]
    ):
        raise CutoverError("cutover tracker program currentness differs")
    refreshed, _directory, _snapshot = _supervision_snapshot(
        module, owner_id=owner_id, repo=repo, tracker_path=tracker_path
    )
    if refreshed != supervision:
        changed = sorted(
            key
            for key in set(refreshed) | set(supervision)
            if refreshed.get(key) != supervision.get(key)
        )
        raise CutoverError(
            "cutover supervision currentness changed: " + ", ".join(changed)
        )
    return proof


def _start_executor_transition(
    module: ModuleType,
    directory_fd: int,
    proposal: Mapping[str, object],
    review: Mapping[str, object],
    outcome: Mapping[str, object],
    *,
    failpoint: Optional[str],
) -> Dict[str, object]:
    next_action = "continue-block-9-from-current-effect"
    execution_key = object_root(
        {
            "handoff_root": proposal["handoff_root"],
            "integration_commit": proposal["prepared_commit"],
            "effect_root": outcome["effect_root"],
            "next_action": next_action,
        }
    )
    evidence = sorted(
        [
            f"current-effect:{outcome['effect_root']}",
            f"execution-key:{execution_key}",
            f"integration-review:{review['review_root']}",
        ]
    )
    all_events, event_snapshot = module.events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    records = module.successor_transition_events(
        all_events, CONTINUATION_TRANSITION_ID
    )
    if not records or records[0].get("record_sha256") != proposal[
        "supervision_context"
    ]["continuation_transition_required_root"]:
        raise CutoverError("canonical continuation transition changed")
    prior = dict(records[-1])
    if prior.get("phase") == "work-started":
        if (
            prior.get("started_block") != "Block 9"
            or prior.get("state_fingerprint") != execution_key
            or prior.get("evidence") != evidence
        ):
            raise CutoverError("canonical continuation start differs")
        return {
            "execution_key": execution_key,
            "next_action": next_action,
            "continuation_root": prior["record_sha256"],
            "state": "work-started",
            "start_count": 1,
        }
    if prior.get("phase") != "required":
        raise CutoverError("canonical continuation is not ready to start")
    if failpoint == "before-continuation-start":
        raise CutoverError("injected interruption before continuation start")
    record = {
        key: value
        for key, value in prior.items()
        if key not in {"record_id", "timestamp", "previous_record_sha256", "record_sha256"}
    }
    record.update(
        {
            "record_id": f"EVT-{len(all_events) + 1:06d}",
            "timestamp": module.utc_now(),
            "phase": "work-started",
            "started_block": "Block 9",
            "state_fingerprint": execution_key,
            "evidence": evidence,
        }
    )
    module.validate_successor_transition(prior, record, all_events)
    module.append_raw_locked_at(
        directory_fd,
        "events.jsonl",
        record,
        previous_record_sha256=str(all_events[-1]["record_sha256"]),
        expected_file_snapshot=event_snapshot,
        require_event_anchor=True,
    )
    written, _snapshot = module.events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    appended = written[-1]
    if (
        appended.get("transition_id") != CONTINUATION_TRANSITION_ID
        or appended.get("phase") != "work-started"
        or appended.get("state_fingerprint") != execution_key
        or appended.get("evidence") != evidence
    ):
        raise CutoverError("canonical continuation start was not retained")
    if failpoint == "after-continuation-start":
        raise CutoverError("injected interruption after continuation start")
    return {
        "execution_key": execution_key,
        "next_action": next_action,
        "continuation_root": appended["record_sha256"],
        "state": "work-started",
        "start_count": 1,
    }


def _correct_started_transition(
    module: ModuleType,
    directory_fd: int,
    *,
    reason: str,
) -> Optional[Dict[str, object]]:
    """Close a retained start whose target currentness failed after append."""

    all_events, event_snapshot = module.events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    records = module.successor_transition_events(
        all_events, CONTINUATION_TRANSITION_ID
    )
    if not records or records[-1].get("phase") != "work-started":
        return None
    prior = dict(records[-1])
    policy, _policy_snapshot = module.read_json_snapshot(
        Path("policy.json"), directory_fd=directory_fd
    )
    source = {
        "source_class": str(prior["governing_authority_source_class"]),
        "source_record": str(prior["governing_authority_source_record"]),
        "source_sha256": str(prior["governing_authority_source_sha256"]),
    }
    if not module.canonical_authority_source(policy, **source):
        raise CutoverError("canonical continuation correction provenance differs")
    record = {
        key: value
        for key, value in prior.items()
        if key not in {"record_id", "timestamp", "previous_record_sha256", "record_sha256"}
    }
    correction_evidence = sorted(
        [
            *list(prior.get("evidence", [])),
            "currentness-rejected:"
            + object_root(
                {
                    "transition_root": prior["record_sha256"],
                    "reason": reason,
                }
            ),
        ]
    )
    record.update(
        {
            "record_id": f"EVT-{len(all_events) + 1:06d}",
            "timestamp": module.utc_now(),
            "phase": "corrected",
            "prior_record_id": prior["record_id"],
            "disposition_reason": reason,
            "correction_authority_source_class": source["source_class"],
            "correction_authority_source_record": source["source_record"],
            "correction_authority_source_sha256": source["source_sha256"],
            "replacement_transition_id": "",
            "governing_outcome_effect": "continue-same-task",
            "evidence": correction_evidence,
        }
    )
    module.validate_successor_transition(prior, record, all_events)
    appended_root = module.append_raw_locked_at(
        directory_fd,
        "events.jsonl",
        record,
        previous_record_sha256=str(all_events[-1]["record_sha256"]),
        expected_file_snapshot=event_snapshot,
        require_event_anchor=True,
    )
    written, _snapshot = module.events_snapshot(
        Path("events.jsonl"), directory_fd=directory_fd
    )
    appended = written[-1]
    if (
        appended.get("phase") != "corrected"
        or appended.get("transition_id") != CONTINUATION_TRANSITION_ID
        or appended.get("record_sha256") != appended_root
        or appended.get("prior_record_id") != prior["record_id"]
    ):
        raise CutoverError("canonical continuation correction was not retained")
    return appended


def _current_result(
    repo: Path,
    tracker_path: Path,
    proposal: Mapping[str, object],
    review: Mapping[str, object],
    bundle: Mapping[str, object],
    module: ModuleType,
    owner_id: str,
    supervision: Mapping[str, object],
    directory_fd: int,
    *,
    duplicate: bool,
    failpoint: Optional[str] = None,
) -> Dict[str, object]:
    try:
        proof = _assert_current_cutover(
            repo,
            tracker_path,
            proposal,
            bundle,
            module,
            owner_id,
            supervision,
        )
    except CutoverError:
        _correct_started_transition(
            module,
            directory_fd,
            reason="Block 9 target currentness changed before continuation acceptance.",
        )
        raise
    _full, relative, _candidate = _artifact_file(bundle, "winner")
    committed = _git(repo, ["show", f"HEAD:{relative}"])
    if not _effect_path(repo).exists():
        raise CutoverError("retained cutover effect validation is missing")
    retained_effect = _load_or_produce_effect(
        repo, proposal, review, bundle, committed, module, directory_fd
    )
    outcome = _rooted(_load_json(_outcome_path(repo)), "effect_root", "cutover outcome")
    expected = {
        "schema_version": 1,
        "kind": "software-factory-candidate-cutover-outcome",
        "proposal_root": proposal["proposal_root"],
        "integration_review_root": review["review_root"],
        "integration_commit": proposal["prepared_commit"],
        "candidate_content_root": proposal["candidate_content_root"],
        "proof_graph_root": proof["graph_root"],
        "observable_effect": retained_effect["observable_effect"],
        "decision_posture": "accepted-current-effect",
    }
    if {key: value for key, value in outcome.items() if key != "effect_root"} != expected:
        raise CutoverError("cutover outcome currentness differs")
    _retain_review_copy(repo, review)
    _assert_current_cutover(
        repo,
        tracker_path,
        proposal,
        bundle,
        module,
        owner_id,
        supervision,
    )
    try:
        continuation = _start_executor_transition(
            module,
            directory_fd,
            proposal,
            review,
            outcome,
            failpoint=failpoint,
        )
    except CutoverError:
        try:
            _assert_current_cutover(
                repo,
                tracker_path,
                proposal,
                bundle,
                module,
                owner_id,
                supervision,
            )
        except CutoverError:
            _correct_started_transition(
                module,
                directory_fd,
                reason="Block 9 target currentness changed during continuation append.",
            )
        raise
    try:
        _assert_current_cutover(
            repo,
            tracker_path,
            proposal,
            bundle,
            module,
            owner_id,
            supervision,
        )
    except CutoverError:
        _correct_started_transition(
            module,
            directory_fd,
            reason="Block 9 target currentness changed during continuation append.",
        )
        raise
    return {
        "action": "cutover-current" if duplicate else "cutover-applied",
        "duplicate": duplicate,
        "application_authorized": True,
        "integration_commit": proposal["prepared_commit"],
        "integration_review_root": review["review_root"],
        "effect_root": outcome["effect_root"],
        "execution_key": continuation["execution_key"],
        "next_action": continuation["next_action"],
        "continuation_root": continuation["continuation_root"],
        "continuation_state": continuation["state"],
        "continuation_start_count": continuation["start_count"],
        "manual_resume_required": False,
        "candidate_authoritative": True,
        "incumbent_authoritative": False,
        "single_authority": True,
        "proof_reconciliation": proposal["proof_reconciliation"],
    }


def apply_cutover(
    target_repository: Path,
    tracker_path: Path,
    integration_review_path: Path,
    *,
    failpoint: Optional[str] = None,
) -> Dict[str, object]:
    """Promote only the current independently reviewed detached integration."""

    repo = _repo_root(target_repository)
    descriptor = _operation_lock(repo)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        bundle = load_accepted_bundle()
        handoff = bundle["handoff"]
        owner_id = _exact_string(handoff["target_owner_id"], "target owner")
        proposal = _rooted(_load_json(_proposal_path(repo)), "proposal_root", "cutover proposal")
        review = load_integration_review(integration_review_path, proposal)
        module = _supervision_module()
        _initial, _directory, directory_snapshot = _supervision_snapshot(
            module, owner_id=owner_id, repo=repo, tracker_path=tracker_path
        )
        try:
            with module.owner_append_lock(
                SUPERVISION_ROOT, owner_id, directory_snapshot
            ) as directory_fd:
                supervision, _directory, _snapshot = _supervision_snapshot(
                    module, owner_id=owner_id, repo=repo, tracker_path=tracker_path
                )
                if supervision != proposal["supervision_context"]:
                    raise CutoverError("cutover supervision currentness changed")
                tracker_raw = _safe_tracker(tracker_path)
                if (
                    _normalized_block_root(tracker_raw, 9) != EXPECTED_BLOCK9_CONTRACT_ROOT
                    or _tracker_program_root(tracker_raw) != proposal["tracker_program_root"]
                ):
                    return {
                        "action": "route-block-8",
                        "structural_change": True,
                        "application_authorized": False,
                        "manual_resume_required": False,
                    }
                head = _head(repo)
                if head == proposal["prepared_commit"]:
                    proof_after = _validate_proof_graph(
                        _load_json(repo / PROOF_RELATIVE)
                    )
                    if (
                        proof_after["graph_root"]
                        != proposal["proof_reconciliation"]["after_graph_root"]
                    ):
                        raise CutoverError("reviewed target proof is not current")
                    replacements = _proposal_replacements(
                        bundle, proposal, proof_after
                    )
                    _validate_prepared_commit(repo, proposal, replacements)
                    if not _outcome_path(repo).exists():
                        committed = _git(repo, ["show", f"HEAD:{proposal['affected_path']}"])
                        retained_effect = _load_or_produce_effect(
                            repo,
                            proposal,
                            review,
                            bundle,
                            committed,
                            module,
                            directory_fd,
                        )
                        refreshed, _directory, _snapshot = _supervision_snapshot(
                            module,
                            owner_id=owner_id,
                            repo=repo,
                            tracker_path=tracker_path,
                        )
                        if (
                            refreshed != supervision
                            or _head(repo) != proposal["prepared_commit"]
                        ):
                            raise CutoverError(
                                "current context changed during effect validation"
                            )
                        outcome: Dict[str, object] = {
                            "schema_version": 1,
                            "kind": "software-factory-candidate-cutover-outcome",
                            "proposal_root": proposal["proposal_root"],
                            "integration_review_root": review["review_root"],
                            "integration_commit": proposal["prepared_commit"],
                            "candidate_content_root": proposal["candidate_content_root"],
                            "proof_graph_root": proposal["proof_reconciliation"]["after_graph_root"],
                            "observable_effect": retained_effect["observable_effect"],
                            "decision_posture": "accepted-current-effect",
                        }
                        outcome["effect_root"] = object_root(outcome)
                        _write_atomic(_outcome_path(repo), _json_bytes(outcome))
                    _retain_review_copy(repo, review)
                    return _current_result(
                        repo,
                        tracker_path,
                        proposal,
                        review,
                        bundle,
                        module,
                        owner_id,
                        supervision,
                        directory_fd,
                        duplicate=True,
                        failpoint=failpoint,
                    )
                if head != proposal["target_head"]:
                    raise CutoverError("target revision changed after integration review")
                proof_before = _validate_proof_graph(
                    _load_json(repo / PROOF_RELATIVE)
                )
                proof_after, reconciliation = reconcile_proof(
                    proof_before, incumbent_root=str(handoff["incumbent_root"])
                )
                if reconciliation != proposal["proof_reconciliation"]:
                    raise CutoverError("current target proof basis changed")
                replacements = _proposal_replacements(bundle, proposal, proof_after)
                _validate_prepared_commit(repo, proposal, replacements)
                _full, relative, incumbent = _artifact_file(bundle, "incumbent")
                if _safe_file(repo, relative) != incumbent:
                    raise CutoverError("target bytes changed after integration review")
                paths = sorted(replacements)
                _paths_clean(repo, head, paths)
                index_before = _index_bytes(repo)
                previous = {path: _safe_file(repo, path, required=False) for path in paths}
                promoted = False
                promoted_index = index_before
                try:
                    for relative_path, content in replacements.items():
                        prior = previous[relative_path]
                        if prior is None:
                            raise CutoverError("reviewed target path unexpectedly absent")
                        _write_atomic_if_unchanged(repo / relative_path, prior, content)
                    if failpoint == "after-write":
                        raise CutoverError("injected interruption after reviewed write")
                    if _head(repo) != head or any(
                        _safe_file(repo, relative_path) != content
                        for relative_path, content in replacements.items()
                    ):
                        raise CutoverError("target state changed before atomic promotion")
                    ref = _git(repo, ["symbolic-ref", "-q", "HEAD"]).decode()
                    if failpoint == "before-ref-update":
                        raise CutoverError("injected interruption before atomic promotion")
                    promoted_index = _promote_ref_and_index(
                        repo,
                        ref,
                        str(proposal["prepared_commit"]),
                        head,
                        index_before,
                        paths,
                    )
                    promoted = True
                    if failpoint == "after-ref-update":
                        raise CutoverError("injected interruption after atomic promotion")
                except Exception as error:
                    if not promoted:
                        _restore_owned_replacements_to_current_head(
                            repo,
                            head,
                            previous,
                            replacements,
                            index_before,
                        )
                    if isinstance(error, CutoverError):
                        raise
                    raise CutoverError("reviewed target write failed before promotion") from error
                try:
                    if _head(repo) != proposal["prepared_commit"]:
                        raise CutoverError("reviewed integration lost target authority")
                    committed = _git(repo, ["show", f"HEAD:{relative}"])
                    if _safe_file(repo, relative) != replacements[relative]:
                        raise CutoverError("reviewed candidate is not current in the worktree")
                    retained_effect = _load_or_produce_effect(
                        repo,
                        proposal,
                        review,
                        bundle,
                        committed,
                        module,
                        directory_fd,
                    )
                    refreshed, _directory, _snapshot = _supervision_snapshot(
                        module,
                        owner_id=owner_id,
                        repo=repo,
                        tracker_path=tracker_path,
                    )
                    refreshed_tracker = _safe_tracker(tracker_path)
                    if (
                        refreshed != supervision
                        or _head(repo) != proposal["prepared_commit"]
                        or _tracker_program_root(refreshed_tracker)
                        != proposal["tracker_program_root"]
                    ):
                        raise CutoverError("current context changed during effect validation")
                except Exception as error:
                    if _head(repo) == proposal["prepared_commit"]:
                        ref = _git(repo, ["symbolic-ref", "-q", "HEAD"]).decode()
                        try:
                            _git(
                                repo,
                                [
                                    "update-ref",
                                    ref,
                                    head,
                                    str(proposal["prepared_commit"]),
                                ],
                            )
                        except CutoverError:
                            pass
                    _restore_owned_replacements_to_current_head(
                        repo,
                        head,
                        previous,
                        replacements,
                        promoted_index,
                    )
                    if isinstance(error, CutoverError):
                        raise
                    raise CutoverError(
                        "current effect validation failed after promotion"
                    ) from error
                outcome = {
                    "schema_version": 1,
                    "kind": "software-factory-candidate-cutover-outcome",
                    "proposal_root": proposal["proposal_root"],
                    "integration_review_root": review["review_root"],
                    "integration_commit": proposal["prepared_commit"],
                    "candidate_content_root": proposal["candidate_content_root"],
                    "proof_graph_root": proposal["proof_reconciliation"]["after_graph_root"],
                    "observable_effect": retained_effect["observable_effect"],
                    "decision_posture": "accepted-current-effect",
                }
                outcome["effect_root"] = object_root(outcome)
                if failpoint == "before-outcome-write":
                    raise CutoverError("injected interruption before current outcome")
                _write_atomic(_outcome_path(repo), _json_bytes(outcome))
                _retain_review_copy(repo, review)
                return _current_result(
                    repo,
                    tracker_path,
                    proposal,
                    review,
                    bundle,
                    module,
                    owner_id,
                    supervision,
                    directory_fd,
                    duplicate=False,
                    failpoint=failpoint,
                )
        except CutoverError:
            raise
        except Exception as error:
            raise CutoverError("canonical target-owner cutover failed") from error
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
