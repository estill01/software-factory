#!/usr/bin/env python3
"""Stage and atomically select accepted Software Factory skill releases."""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Iterator, Mapping, Sequence


SKILLS = (
    "author-implementation-trackers",
    "implement-tracker-blocks",
    "supervise-tracker-runs",
)
MANIFEST_NAME = "release-manifest.json"
HISTORY_NAME = "activation-history.jsonl"
ACCEPTANCE_NAME = "accepted-releases.jsonl"
RECOVERY_NAME = "installed-link-recoveries.jsonl"
RECOVERY_PENDING_NAME = "installed-link-recovery-pending.json"
LOCK_NAME = ".release.lock"
KEY_DIRECTORY = ".software-factory-release-keys"
SCHEMA_VERSION = 1
CANONICAL_RELEASE_ROOT = Path.home() / ".codex/software-factory-releases"
CANONICAL_INSTALL_ROOT = Path.home() / ".codex/skills"
CANONICAL_DEV_OVERRIDES_ROOT = Path.home() / ".codex/software-factory-dev-overrides"
AUTHORITY_ROOT = Path(
    "/Users/ethanstillman/.codex/software-factory-release-authority"
)
TRUSTED_OPENSSL_PATH = Path("/opt/homebrew/Cellar/openssl@3/3.6.2/bin/openssl")
TRUSTED_OPENSSL_SHA256 = "bf63843e6856e1994ca71092ff3b46834236eb2144dd9b6ceb85d511128b836e"
TRUSTED_PYTHON_PATH = Path("/usr/bin/python3")
TRUSTED_PYTHON_SHA256 = "179301dcb41ea78accc3fa0048a7e6f6710d891945a751a34addd622020c1818"
TRUSTED_YAML_PATH = Path(
    "/Users/ethanstillman/Library/Python/3.9/lib/python/site-packages/yaml"
)
TRUSTED_YAML_ROOT_SHA256 = (
    "a641f6774e48216cd3e2e8be89b0313f464e5b070e41d222da7f5022b08cf7e7"
)
TRUSTED_VALIDATOR_PATH = Path(
    "/Users/ethanstillman/.codex/skills/.system/skill-creator/scripts/quick_validate.py"
)
TRUSTED_VALIDATOR_SHA256 = (
    "1fd66498c219616fd9249eacdf16c458412ea9065a9d887fd716aeef03907762"
)
TRUSTED_HISTORICAL_VALIDATOR_SHA256S = (
    "6cc9dc3199c935916cf6f73fcbbbb0e3bb1b58c8f5109fefa499978908164f51",
)
TRUSTED_AUTHORITY_IDS = {
    "reviewers": ("software-factory-release-reviewer-v1",),
    "operators": ("software-factory-release-operator-v1",),
}
AUTOMATED_ASSURANCE_KIND = "software-factory-skill-release-automated-assurance"
AUTOMATED_CHECK_RUNNER = Path("/opt/homebrew/bin/uv")
AUTOMATED_CHECK_TIMEOUT_SECONDS = 1800
AUTOMATED_CHECK_SUITES = (
    ("release-owner", "scripts", "test_skill_release.py", "system"),
    ("tracker-authoring", "author-implementation-trackers/scripts", "test_*.py", "system"),
    ("tracker-execution", "implement-tracker-blocks/scripts", "test_*.py", "system"),
    ("tracker-supervision", "supervise-tracker-runs/scripts", "test_*.py", "uv-reportlab"),
)


class ReleaseError(RuntimeError):
    """A release contract or currentness check failed."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_sha256(value: str, *, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
        raise ReleaseError(f"{label} must be an exact lowercase SHA-256")
    return value


def exact_git_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise ReleaseError("Source commit must be an exact lowercase Git SHA-1")
    return value


def bounded_id(value: str, *, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,159}", value or ""):
        raise ReleaseError(f"{label} is invalid")
    return value


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_git(repo: Path, *arguments: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseError(f"Git command failed: {detail or arguments[0]}")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def ensure_directory(path: Path, *, label: str, create: bool = True) -> Path:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"{label} must be a real directory")
    return path.resolve(strict=True)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_tree_directories(path: Path) -> None:
    directories = [Path(base) for base, _names, _files in os.walk(path)]
    for directory in reversed(directories):
        fsync_directory(directory)


def seal_release_tree(path: Path) -> None:
    directories: list[Path] = []
    for base, directory_names, file_names in os.walk(path):
        base_path = Path(base)
        directories.append(base_path)
        for name in directory_names:
            child = base_path / name
            if child.is_symlink():
                raise ReleaseError("Release tree contains a directory symlink")
        for name in file_names:
            child = base_path / name
            metadata = child.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ReleaseError("Release tree contains a non-regular file")
            child.chmod(0o555 if metadata.st_mode & stat.S_IXUSR else 0o444)
    for directory in reversed(directories):
        directory.chmod(0o555)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        payload = canonical(value) + b"\n"
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_directory(path.parent)


@contextlib.contextmanager
def release_lock(release_root: Path) -> Iterator[None]:
    lock_path = release_root / LOCK_NAME
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def release_key_path(release_root: Path) -> Path:
    key_directory = release_root.parent / KEY_DIRECTORY
    key_name = hashlib.sha256(str(release_root).encode("utf-8")).hexdigest() + ".key"
    return key_directory / key_name


def release_key(release_root: Path, *, allow_create: bool) -> bytes:
    path = release_key_path(release_root)
    protected_state_exists = any(
        (release_root / name).exists() for name in (ACCEPTANCE_NAME, HISTORY_NAME)
    )
    if not path.exists():
        if protected_state_exists or not allow_create:
            raise ReleaseError("External release authority key is missing")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ReleaseError("External release authority directory is symlinked")
        path.parent.chmod(0o700)
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o400,
        )
        try:
            os.write(descriptor, secrets.token_bytes(32))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        fsync_directory(path.parent)
    if path.is_symlink():
        raise ReleaseError("External release authority key is symlinked")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        key = os.read(descriptor, 33)
    finally:
        os.close(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size != 32
        or len(key) != 32
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ReleaseError("External release authority key is invalid")
    return key


def record_hmac(key: bytes, material: Mapping[str, Any]) -> str:
    return hmac.new(key, canonical(material), hashlib.sha256).hexdigest()


def load_bounded_json(path: Path, *, label: str, maximum: int = 65536) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"{label} must be a real regular file")
    metadata = path.stat()
    if metadata.st_size > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    with path.open("rb") as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} must be a JSON object")
    if raw != canonical(value) + b"\n":
        raise ReleaseError(f"{label} is not exact canonical JSON")
    return value


def trusted_executable(path: Path, expected_sha256: str, *, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"Canonical {label} is missing or symlinked")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not metadata.st_mode & stat.S_IXUSR
            or metadata.st_size > 16 * 1024 * 1024
        ):
            raise ReleaseError(f"Canonical {label} has an invalid file shape")
        payload = bytearray()
        while len(payload) <= 16 * 1024 * 1024:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            payload.extend(chunk)
    finally:
        os.close(descriptor)
    if len(payload) != metadata.st_size or len(payload) > 16 * 1024 * 1024:
        raise ReleaseError(f"Canonical {label} changed or exceeds its size limit")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ReleaseError(f"Canonical {label} content identity differs")
    return path


def trusted_directory_root(path: Path, *, label: str, expected_sha256: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"Canonical {label} is missing or symlinked")
    entries: list[dict[str, str]] = []
    total = 0
    for base, directory_names, file_names in os.walk(path, followlinks=False):
        directory_names.sort()
        file_names.sort()
        base_path = Path(base)
        for name in directory_names:
            if (base_path / name).is_symlink():
                raise ReleaseError(f"Canonical {label} contains a directory symlink")
        for name in file_names:
            child = base_path / name
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ReleaseError(f"Canonical {label} contains a non-regular file")
            total += metadata.st_size
            if len(entries) >= 128 or total > 4 * 1024 * 1024:
                raise ReleaseError(f"Canonical {label} exceeds its bounded tree")
            payload = child.read_bytes()
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "mode": "100755" if metadata.st_mode & stat.S_IXUSR else "100644",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    if not entries or digest(entries) != expected_sha256:
        raise ReleaseError(f"Canonical {label} content identity differs")
    return path


def trusted_openssl() -> Path:
    return trusted_executable(
        TRUSTED_OPENSSL_PATH,
        TRUSTED_OPENSSL_SHA256,
        label="OpenSSL verifier",
    )


def trusted_validator_python() -> tuple[Path, Path]:
    interpreter = trusted_executable(
        TRUSTED_PYTHON_PATH,
        TRUSTED_PYTHON_SHA256,
        label="Skill Creator Python interpreter",
    )
    yaml_path = trusted_directory_root(
        TRUSTED_YAML_PATH,
        label="Skill Creator YAML runtime",
        expected_sha256=TRUSTED_YAML_ROOT_SHA256,
    )
    return interpreter, yaml_path.parent


def authority_id(value: str, *, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", value or ""):
        raise ReleaseError(f"{label} is invalid")
    return value


def trusted_public_key(role: str, principal_id: str) -> tuple[Path, str]:
    if role not in {"reviewers", "operators"}:
        raise ReleaseError("Release authority role is invalid")
    principal = authority_id(principal_id, label="release authority ID")
    if principal not in TRUSTED_AUTHORITY_IDS[role]:
        raise ReleaseError("Release authority ID is not the pinned trusted role")
    root = AUTHORITY_ROOT
    role_root = root / role
    key_path = role_root / f"{principal}.pem"
    for path, label in (
        (root, "release authority root"),
        (role_root, "release authority role directory"),
    ):
        if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o222:
            raise ReleaseError(f"Canonical {label} is missing, symlinked, or writable")
    if (
        key_path.is_symlink()
        or not key_path.is_file()
        or key_path.stat().st_mode & 0o222
        or key_path.stat().st_size > 8192
    ):
        raise ReleaseError("Trusted release authority public key is invalid")
    payload = key_path.read_bytes()
    return key_path, hashlib.sha256(payload).hexdigest()


def verify_trusted_signature(
    *,
    role: str,
    principal_id: str,
    expected_key_sha256: str,
    signed_material: Mapping[str, Any],
    signature_base64: str,
) -> None:
    key_path, key_sha256 = trusted_public_key(role, principal_id)
    if key_sha256 != exact_sha256(
        expected_key_sha256, label="release authority public-key root"
    ):
        raise ReleaseError("Release authority public key differs from signed evidence")
    try:
        signature = base64.b64decode(signature_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ReleaseError("Release authority signature is invalid base64") from exc
    if not signature or len(signature) > 8192:
        raise ReleaseError("Release authority signature has an invalid size")
    openssl = trusted_openssl()
    with tempfile.TemporaryDirectory(prefix="software-factory-signature-") as raw:
        temporary = Path(raw)
        material_path = temporary / "material.json"
        signature_path = temporary / "signature.bin"
        material_path.write_bytes(canonical(signed_material))
        signature_path.write_bytes(signature)
        result = subprocess.run(
            [
                str(openssl),
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
            capture_output=True,
        )
    if result.returncode:
        raise ReleaseError("Release authority signature verification failed")


def operator_authority_ledger_path(operator_id: str) -> Path:
    principal = authority_id(operator_id, label="quiescent-boundary operator")
    if principal not in TRUSTED_AUTHORITY_IDS["operators"]:
        raise ReleaseError("Release authority ID is not the pinned trusted role")
    return AUTHORITY_ROOT / "operators" / f"{principal}.ledger.jsonl"


def validate_operator_authority_ledger(evidence: Mapping[str, Any]) -> None:
    operator_id = str(evidence.get("operator_id", ""))
    path = operator_authority_ledger_path(operator_id)
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_mode & 0o222
        or path.stat().st_size > 1024 * 1024
    ):
        raise ReleaseError(
            "Canonical operator authority ledger is missing, mutable, or oversized"
        )
    with path.open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ReleaseError("Canonical operator authority ledger is oversized")
    records: list[dict[str, Any]] = []
    previous: str | None = None
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "operator_id",
        "authority_sequence",
        "previous_authority_record_sha256",
        "operation",
        "release_id",
        "previous_active_release_id",
        "observed_at",
        "no_concurrent_skill_resolutions",
        "evidence",
        "authority_key_sha256",
        "evidence_root_sha256",
        "signature_base64",
    }
    for line in raw.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError("Canonical operator authority ledger is invalid JSON") from exc
        if not isinstance(record, dict) or line != canonical(record):
            raise ReleaseError("Canonical operator authority ledger is noncanonical")
        root_material = {
            item: member
            for item, member in record.items()
            if item not in {"evidence_root_sha256", "signature_base64"}
        }
        if (
            set(record) != exact_keys
            or type(record.get("schema_version")) is not int
            or record.get("schema_version") != SCHEMA_VERSION
            or record.get("kind") != "software-factory-quiescent-boundary"
            or record.get("operator_id") != operator_id
            or type(record.get("authority_sequence")) is not int
            or record.get("authority_sequence") != len(records) + 1
            or record.get("previous_authority_record_sha256") != previous
            or record.get("evidence_root_sha256") != digest(root_material)
        ):
            raise ReleaseError("Canonical operator authority ledger chain is invalid")
        previous = str(record["evidence_root_sha256"])
        records.append(record)
        if len(records) > 4096:
            raise ReleaseError("Canonical operator authority ledger has too many records")
    if not records or raw != b"".join(canonical(item) + b"\n" for item in records):
        raise ReleaseError("Canonical operator authority ledger is empty or noncanonical")
    if records[-1] != dict(evidence):
        raise ReleaseError(
            "Quiescent-boundary evidence is not the current external authority head"
        )


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, canonical(record) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)


def append_history(release_root: Path, record: Mapping[str, Any]) -> None:
    require_no_pending_recovery(release_root, operation="activation-history append")
    append_jsonl(release_root / HISTORY_NAME, record)


def jsonl_records(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"{label} is not a canonical regular file")
    maximum = 1024 * 1024
    metadata = path.stat()
    if metadata.st_size > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    with path.open("rb") as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ReleaseError(f"{label} exceeds its size limit")
    records: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"{label} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ReleaseError(f"{label} record must be an object")
        if line != canonical(value):
            raise ReleaseError(f"{label} contains noncanonical record bytes")
        records.append(value)
        if len(records) > 4096:
            raise ReleaseError(f"{label} contains too many records")
    return records


def acceptance_records(release_root: Path) -> list[dict[str, Any]]:
    values = jsonl_records(
        release_root / ACCEPTANCE_NAME, label="Release acceptance history"
    )
    if not values:
        return []
    key = release_key(release_root, allow_create=False)
    previous: str | None = None
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "release_id",
        "source_commit",
        "manifest_sha256",
        "candidate_root_sha256",
        "review_record_id",
        "review_root_sha256",
        "previous_record_hmac_sha256",
        "record_hmac_sha256",
    }
    for index, value in enumerate(values, start=1):
        material = {
            item: member for item, member in value.items() if item != "record_hmac_sha256"
        }
        if (
            set(value) != exact_keys
            or type(value.get("schema_version")) is not int
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("kind") != "software-factory-release-acceptance"
            or value.get("record_id") != f"RELEASE-ACCEPTANCE-{index}"
            or value.get("previous_record_hmac_sha256") != previous
            or value.get("record_hmac_sha256") != record_hmac(key, material)
        ):
            raise ReleaseError("Release acceptance history was forged or reordered")
        bounded_id(str(value["release_id"]), label="accepted release ID")
        exact_git_commit(str(value["source_commit"]))
        for label, field in (
            ("accepted manifest", "manifest_sha256"),
            ("accepted candidate", "candidate_root_sha256"),
            ("accepted review", "review_root_sha256"),
        ):
            exact_sha256(str(value[field]), label=label)
        bounded_id(str(value["review_record_id"]), label="accepted review record")
        previous = str(value["record_hmac_sha256"])
    return values


def accepted_release_record(
    release_root: Path, release_id: str
) -> dict[str, Any] | None:
    matches = [
        item for item in acceptance_records(release_root) if item["release_id"] == release_id
    ]
    if len(matches) > 1:
        raise ReleaseError("Release acceptance identity is duplicated")
    return matches[0] if matches else None


def accepted_automated_stage(
    release_root: Path, candidate: Mapping[str, Any]
) -> dict[str, Any] | None:
    source_commit = str(candidate["source_commit"])
    candidate_root = digest(candidate)
    matches = [
        item
        for item in acceptance_records(release_root)
        if item["source_commit"] == source_commit
    ]
    if not matches:
        return None
    if len(matches) != 1 or matches[0]["candidate_root_sha256"] != candidate_root:
        raise ReleaseError("Accepted release source is ambiguous or divergent")
    manifest = read_manifest(release_root, str(matches[0]["release_id"]))
    review = manifest["independent_review"]
    if (
        manifest["source_commit"] != source_commit
        or manifest["candidate_root_sha256"] != candidate_root
        or review.get("kind") != AUTOMATED_ASSURANCE_KIND
        or review.get("outcome") != "passed"
    ):
        raise ReleaseError("Accepted automated stage differs")
    return {"stage": "existing", **manifest}


def append_acceptance(
    release_root: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    require_no_pending_recovery(release_root, operation="release-acceptance append")
    records = acceptance_records(release_root)
    candidate = candidate_material(
        str(manifest["source_commit"]),
        manifest["skills"],
        manifest["validation"],
    )
    _assurance, assurance_record_id, assurance_root = release_assurance(
        manifest, candidate=candidate
    )
    existing = [
        item for item in records if item["release_id"] == manifest["release_id"]
    ]
    if existing:
        if len(existing) != 1:
            raise ReleaseError("Release acceptance identity is duplicated")
        if any(
            existing[0].get(field) != expected
            for field, expected in (
                ("source_commit", manifest["source_commit"]),
                ("manifest_sha256", manifest["manifest_sha256"]),
                ("candidate_root_sha256", manifest["candidate_root_sha256"]),
                ("review_record_id", assurance_record_id),
                ("review_root_sha256", assurance_root),
            )
        ):
            raise ReleaseError("Existing release acceptance differs from its manifest")
        return existing[0]
    key = release_key(release_root, allow_create=True)
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-release-acceptance",
        "record_id": f"RELEASE-ACCEPTANCE-{len(records) + 1}",
        "release_id": manifest["release_id"],
        "source_commit": manifest["source_commit"],
        "manifest_sha256": manifest["manifest_sha256"],
        "candidate_root_sha256": manifest["candidate_root_sha256"],
        "review_record_id": assurance_record_id,
        "review_root_sha256": assurance_root,
        "previous_record_hmac_sha256": (
            records[-1]["record_hmac_sha256"] if records else None
        ),
    }
    material["record_hmac_sha256"] = record_hmac(key, material)
    append_jsonl(release_root / ACCEPTANCE_NAME, material)
    return material


def history(release_root: Path) -> list[dict[str, Any]]:
    records = jsonl_records(release_root / HISTORY_NAME, label="Activation history")
    acceptances = acceptance_records(release_root)
    if not records:
        return []
    key = release_key(release_root, allow_create=False)
    previous: str | None = None
    active: str | None = None
    seen_active: set[str] = set()
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "timestamp",
        "action",
        "release_id",
        "previous_release_id",
        "quiescent_boundary_record",
        "quiescent_boundary_root_sha256",
        "post_swap_reload_root_sha256",
        "previous_record_hmac_sha256",
        "record_hmac_sha256",
    }
    for index, value in enumerate(records, start=1):
        material = {
            item: member for item, member in value.items() if item != "record_hmac_sha256"
        }
        action = value.get("action")
        release_id = str(value.get("release_id", ""))
        if (
            set(value) != exact_keys
            or type(value.get("schema_version")) is not int
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("kind") != "software-factory-release-activation"
            or value.get("record_id") != f"ACTIVATION-{index}"
            or value.get("previous_record_hmac_sha256") != previous
            or value.get("record_hmac_sha256") != record_hmac(key, material)
            or action not in {"bootstrap", "activate", "rollback"}
            or value.get("previous_release_id") != active
            or (index == 1 and action != "bootstrap")
            or (index > 1 and action == "bootstrap")
            or (action == "rollback" and release_id not in seen_active)
            or release_id == active
        ):
            raise ReleaseError("Activation history was forged or is semantically invalid")
        bounded_id(release_id, label="activation release ID")
        bounded_id(
            str(value["quiescent_boundary_record"]),
            label="activation quiescent record",
        )
        exact_sha256(
            str(value["quiescent_boundary_root_sha256"]),
            label="activation quiescent root",
        )
        exact_sha256(
            str(value["post_swap_reload_root_sha256"]),
            label="activation reload root",
        )
        if not any(item["release_id"] == release_id for item in acceptances):
            raise ReleaseError("Activation history names an unaccepted release")
        if active:
            seen_active.add(active)
        active = release_id
        previous = str(value["record_hmac_sha256"])
    return records


def archive_projection_summary(
    projection: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "content_root_sha256": projection[name]["content_root_sha256"],
            "file_count": projection[name]["file_count"],
        }
        for name in SKILLS
    }


def validate_installed_link_recovery_records(
    release_root: Path, records: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not records:
        return []
    key = release_key(release_root, allow_create=False)
    previous: str | None = None
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "timestamp",
        "current_release_id",
        "current_source_commit",
        "activation_record_id",
        "activation_record_hmac_sha256",
        "activation_history_count",
        "override_source_commit",
        "override_archive_projection",
        "candidate_source_commit",
        "candidate_parent_commit",
        "post_recovery_links",
        "installed_verification_root_sha256",
        "previous_record_hmac_sha256",
        "record_hmac_sha256",
    }
    for index, value in enumerate(records, start=1):
        material = {
            field: member
            for field, member in value.items()
            if field != "record_hmac_sha256"
        }
        projection = value.get("override_archive_projection")
        links = value.get("post_recovery_links")
        if (
            set(value) != exact_keys
            or type(value.get("schema_version")) is not int
            or value.get("schema_version") != SCHEMA_VERSION
            or value.get("kind") != "software-factory-installed-link-recovery"
            or value.get("record_id") != f"INSTALLED-LINK-RECOVERY-{index}"
            or not isinstance(value.get("timestamp"), str)
            or not value["timestamp"]
            or value.get("previous_record_hmac_sha256") != previous
            or value.get("record_hmac_sha256") != record_hmac(key, material)
            or type(value.get("activation_history_count")) is not int
            or value["activation_history_count"] < 1
            or not isinstance(projection, dict)
            or set(projection) != set(SKILLS)
            or not isinstance(links, dict)
            or set(links) != set(SKILLS)
        ):
            raise ReleaseError("Installed-link recovery history was forged or reordered")
        bounded_id(str(value["current_release_id"]), label="recovery release ID")
        bounded_id(str(value["activation_record_id"]), label="recovery activation record")
        for field in (
            "current_source_commit",
            "override_source_commit",
            "candidate_source_commit",
            "candidate_parent_commit",
        ):
            exact_git_commit(str(value[field]))
        for label, field in (
            ("recovery activation HMAC", "activation_record_hmac_sha256"),
            ("recovery installed verification", "installed_verification_root_sha256"),
        ):
            exact_sha256(str(value[field]), label=label)
        for name in SKILLS:
            member = projection[name]
            if (
                not isinstance(member, dict)
                or set(member) != {"content_root_sha256", "file_count"}
                or type(member.get("file_count")) is not int
                or member["file_count"] < 1
            ):
                raise ReleaseError("Installed-link recovery projection is invalid")
            exact_sha256(
                str(member.get("content_root_sha256", "")),
                label="recovery archive content root",
            )
            if links[name] != desired_link(release_root, name):
                raise ReleaseError("Installed-link recovery stable-link binding differs")
        previous = str(value["record_hmac_sha256"])
    return [dict(item) for item in records]


def installed_link_recovery_records(release_root: Path) -> list[dict[str, Any]]:
    return validate_installed_link_recovery_records(
        release_root,
        jsonl_records(
            release_root / RECOVERY_NAME, label="Installed-link recovery history"
        ),
    )


def recovery_records_from_bytes(
    release_root: Path, raw: bytes
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReleaseError("Installed-link recovery history is invalid JSON") from exc
        if not isinstance(value, dict) or line != canonical(value):
            raise ReleaseError("Installed-link recovery history is noncanonical")
        records.append(value)
    if raw != b"".join(canonical(item) + b"\n" for item in records):
        raise ReleaseError("Installed-link recovery history has an incomplete record")
    return validate_installed_link_recovery_records(release_root, records)


def recovery_ledger_bytes(release_root: Path) -> bytes:
    path = release_root / RECOVERY_NAME
    if not path.exists():
        return b""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ReleaseError("Installed-link recovery history is not a bounded regular file")
    with path.open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ReleaseError("Installed-link recovery history exceeds its size limit")
    return raw


def recovery_pending_path(release_root: Path) -> Path:
    return release_root / RECOVERY_PENDING_NAME


def recovery_pending_record(
    release_root: Path,
    state: Mapping[str, Any],
    recovery_records: Sequence[Mapping[str, Any]],
    ledger_raw: bytes,
) -> dict[str, Any]:
    identity = {
        "current_release_id": state["current_release_id"],
        "current_source_commit": state["current_source_commit"],
        "activation_record_id": state["activation_record"]["record_id"],
        "activation_record_hmac_sha256": state["activation_record"][
            "record_hmac_sha256"
        ],
        "activation_history_count": state["activation_history_count"],
        "override_source_commit": state["override_source_commit"],
        "override_archive_projection": state["override_archive_projection"],
        "candidate_source_commit": state["candidate_source_commit"],
        "candidate_parent_commit": state["candidate_parent_commit"],
        "original_links": state["override_link_targets"],
        "desired_links": state["stable_link_targets"],
        "prior_recovery_ledger_size": len(ledger_raw),
        "prior_recovery_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
        "prior_recovery_record_count": len(recovery_records),
        "prior_recovery_record_hmac_sha256": (
            recovery_records[-1]["record_hmac_sha256"]
            if recovery_records
            else None
        ),
    }
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-installed-link-recovery-intent",
        "intent_id": f"RECOVERY-{digest(identity)[:24]}",
        "phase": "prepared",
        "created_at": utc_now(),
        **identity,
        "installed_verification_root_sha256": None,
        "receipt": None,
    }
    material["intent_hmac_sha256"] = record_hmac(
        release_key(release_root, allow_create=False), material
    )
    return material


def validate_recovery_pending_record(
    release_root: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    exact_keys = {
        "schema_version",
        "kind",
        "intent_id",
        "phase",
        "created_at",
        "current_release_id",
        "current_source_commit",
        "activation_record_id",
        "activation_record_hmac_sha256",
        "activation_history_count",
        "override_source_commit",
        "override_archive_projection",
        "candidate_source_commit",
        "candidate_parent_commit",
        "original_links",
        "desired_links",
        "prior_recovery_ledger_size",
        "prior_recovery_ledger_sha256",
        "prior_recovery_record_count",
        "prior_recovery_record_hmac_sha256",
        "installed_verification_root_sha256",
        "receipt",
        "intent_hmac_sha256",
    }
    material = {
        field: member
        for field, member in value.items()
        if field != "intent_hmac_sha256"
    }
    projection = value.get("override_archive_projection")
    if (
        set(value) != exact_keys
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind")
        != "software-factory-installed-link-recovery-intent"
        or value.get("phase") not in {"prepared", "verified"}
        or not isinstance(value.get("created_at"), str)
        or not value["created_at"]
        or type(value.get("activation_history_count")) is not int
        or value["activation_history_count"] < 1
        or type(value.get("prior_recovery_ledger_size")) is not int
        or value["prior_recovery_ledger_size"] < 0
        or type(value.get("prior_recovery_record_count")) is not int
        or value["prior_recovery_record_count"] < 0
        or not isinstance(projection, dict)
        or set(projection) != set(SKILLS)
        or not isinstance(value.get("original_links"), dict)
        or set(value["original_links"]) != set(SKILLS)
        or not isinstance(value.get("desired_links"), dict)
        or set(value["desired_links"]) != set(SKILLS)
        or value.get("intent_hmac_sha256")
        != record_hmac(release_key(release_root, allow_create=False), material)
    ):
        raise ReleaseError("Installed-link recovery intent is invalid or unauthenticated")
    bounded_id(str(value["intent_id"]), label="recovery intent ID")
    bounded_id(str(value["current_release_id"]), label="recovery release ID")
    bounded_id(str(value["activation_record_id"]), label="recovery activation record")
    for field in (
        "current_source_commit",
        "override_source_commit",
        "candidate_source_commit",
        "candidate_parent_commit",
    ):
        exact_git_commit(str(value[field]))
    for label, field in (
        ("recovery activation HMAC", "activation_record_hmac_sha256"),
        ("recovery prior ledger", "prior_recovery_ledger_sha256"),
    ):
        exact_sha256(str(value[field]), label=label)
    prior_hmac = value.get("prior_recovery_record_hmac_sha256")
    if value["prior_recovery_record_count"] == 0:
        if prior_hmac is not None:
            raise ReleaseError("Empty recovery prefix has a prior record HMAC")
    else:
        exact_sha256(str(prior_hmac), label="recovery prior record HMAC")
    for name in SKILLS:
        member = projection[name]
        if (
            not isinstance(member, dict)
            or set(member) != {"content_root_sha256", "file_count"}
            or type(member.get("file_count")) is not int
            or member["file_count"] < 1
        ):
            raise ReleaseError("Installed-link recovery intent projection is invalid")
        exact_sha256(
            str(member.get("content_root_sha256", "")),
            label="recovery intent archive root",
        )
        if not isinstance(value["original_links"][name], str) or not isinstance(
            value["desired_links"][name], str
        ):
            raise ReleaseError("Installed-link recovery intent link set is invalid")
    receipt = value.get("receipt")
    if value["phase"] == "prepared":
        if receipt is not None or value.get("installed_verification_root_sha256") is not None:
            raise ReleaseError("Prepared recovery intent contains final evidence")
    else:
        if not isinstance(receipt, dict):
            raise ReleaseError("Verified recovery intent lacks its exact receipt")
        exact_sha256(
            str(value.get("installed_verification_root_sha256", "")),
            label="recovery intent installed verification",
        )
        if receipt.get("installed_verification_root_sha256") != value[
            "installed_verification_root_sha256"
        ]:
            raise ReleaseError("Recovery intent and receipt verification roots differ")
    return dict(value)


def load_recovery_pending(release_root: Path) -> dict[str, Any] | None:
    path = recovery_pending_path(release_root)
    if not path.exists() and not path.is_symlink():
        return None
    return validate_recovery_pending_record(
        release_root,
        load_bounded_json(path, label="Installed-link recovery intent"),
    )


def write_recovery_pending(release_root: Path, value: Mapping[str, Any]) -> None:
    validated = validate_recovery_pending_record(release_root, value)
    atomic_json(recovery_pending_path(release_root), validated)
    if load_recovery_pending(release_root) != validated:
        raise ReleaseError("Installed-link recovery intent durability check failed")


def remove_recovery_pending(release_root: Path) -> None:
    path = recovery_pending_path(release_root)
    if path.exists() or path.is_symlink():
        path.unlink()
        fsync_directory(release_root)


def recovery_pending_matches_state(
    pending: Mapping[str, Any], state: Mapping[str, Any]
) -> bool:
    activation = state["activation_record"]
    return all(
        pending.get(field) == expected
        for field, expected in (
            ("current_release_id", state["current_release_id"]),
            ("current_source_commit", state["current_source_commit"]),
            ("activation_record_id", activation["record_id"]),
            ("activation_record_hmac_sha256", activation["record_hmac_sha256"]),
            ("activation_history_count", state["activation_history_count"]),
            ("override_source_commit", state["override_source_commit"]),
            ("override_archive_projection", state["override_archive_projection"]),
            ("candidate_source_commit", state["candidate_source_commit"]),
            ("candidate_parent_commit", state["candidate_parent_commit"]),
            ("original_links", state["override_link_targets"]),
            ("desired_links", state["stable_link_targets"]),
        )
    )


def recovery_pending_ledger_posture(
    release_root: Path, pending: Mapping[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    raw = recovery_ledger_bytes(release_root)
    prior_size = int(pending["prior_recovery_ledger_size"])
    if len(raw) < prior_size:
        raise ReleaseError("Installed-link recovery ledger lost its retained prefix")
    prefix = raw[:prior_size]
    if hashlib.sha256(prefix).hexdigest() != pending[
        "prior_recovery_ledger_sha256"
    ]:
        raise ReleaseError("Installed-link recovery ledger prefix changed")
    prior_records = recovery_records_from_bytes(release_root, prefix)
    if (
        len(prior_records) != pending["prior_recovery_record_count"]
        or (
            prior_records[-1]["record_hmac_sha256"] if prior_records else None
        )
        != pending["prior_recovery_record_hmac_sha256"]
    ):
        raise ReleaseError("Installed-link recovery ledger prefix identity differs")
    suffix = raw[prior_size:]
    receipt = pending.get("receipt")
    if receipt is None:
        if suffix:
            raise ReleaseError("Prepared recovery intent has an unexpected ledger suffix")
        return "absent", prior_records
    receipt_bytes = canonical(receipt) + b"\n"
    validate_installed_link_recovery_records(
        release_root, [*prior_records, dict(receipt)]
    )
    if suffix == receipt_bytes:
        return "complete", prior_records
    if not suffix:
        return "absent", prior_records
    if receipt_bytes.startswith(suffix):
        return "partial", prior_records
    raise ReleaseError("Installed-link recovery ledger suffix is divergent")


def require_no_pending_recovery(release_root: Path, *, operation: str) -> None:
    """Fail closed while the recovery owner has authenticated unfinished work."""
    pending = load_recovery_pending(release_root)
    if pending is None:
        return
    ledger_posture, _records = recovery_pending_ledger_posture(
        release_root, pending
    )
    raise ReleaseError(
        f"Release-owner mutation {operation} is blocked by authenticated pending "
        f"recovery {pending['intent_id']} ({pending['phase']}/{ledger_posture}); "
        "recover-installed-links is the sole reconciliation owner"
    )


def make_recovery_receipt(
    release_root: Path,
    pending: Mapping[str, Any],
    prior_records: Sequence[Mapping[str, Any]],
    installed: Mapping[str, Any],
) -> dict[str, Any]:
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-installed-link-recovery",
        "record_id": f"INSTALLED-LINK-RECOVERY-{len(prior_records) + 1}",
        "timestamp": utc_now(),
        "current_release_id": pending["current_release_id"],
        "current_source_commit": pending["current_source_commit"],
        "activation_record_id": pending["activation_record_id"],
        "activation_record_hmac_sha256": pending[
            "activation_record_hmac_sha256"
        ],
        "activation_history_count": pending["activation_history_count"],
        "override_source_commit": pending["override_source_commit"],
        "override_archive_projection": pending["override_archive_projection"],
        "candidate_source_commit": pending["candidate_source_commit"],
        "candidate_parent_commit": pending["candidate_parent_commit"],
        "post_recovery_links": pending["desired_links"],
        "installed_verification_root_sha256": installed[
            "verification_root_sha256"
        ],
        "previous_record_hmac_sha256": (
            prior_records[-1]["record_hmac_sha256"] if prior_records else None
        ),
    }
    material["record_hmac_sha256"] = record_hmac(
        release_key(release_root, allow_create=False), material
    )
    validate_installed_link_recovery_records(
        release_root, [*prior_records, material]
    )
    return material


def verified_recovery_pending(
    release_root: Path,
    pending: Mapping[str, Any],
    prior_records: Sequence[Mapping[str, Any]],
    installed: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = make_recovery_receipt(
        release_root, pending, prior_records, installed
    )
    material = {
        field: member
        for field, member in pending.items()
        if field != "intent_hmac_sha256"
    }
    material["phase"] = "verified"
    material["installed_verification_root_sha256"] = installed[
        "verification_root_sha256"
    ]
    material["receipt"] = receipt
    material["intent_hmac_sha256"] = record_hmac(
        release_key(release_root, allow_create=False), material
    )
    return validate_recovery_pending_record(release_root, material)


def persist_recovery_receipt(
    release_root: Path,
    pending: Mapping[str, Any],
    *,
    crash_hook: Any | None = None,
) -> dict[str, Any]:
    if pending.get("phase") != "verified" or not isinstance(
        pending.get("receipt"), dict
    ):
        raise ReleaseError("Recovery receipt persistence requires verified intent")
    posture, _records = recovery_pending_ledger_posture(release_root, pending)
    if posture == "complete":
        fsync_directory(release_root)
        return dict(pending["receipt"])
    if crash_hook is not None:
        crash_hook("before-receipt-persistence")
    receipt_bytes = canonical(pending["receipt"]) + b"\n"
    raw = recovery_ledger_bytes(release_root)
    prior_size = int(pending["prior_recovery_ledger_size"])
    suffix = raw[prior_size:]
    remaining = receipt_bytes[len(suffix):]
    path = release_root / RECOVERY_NAME
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        offset = 0
        while offset < len(remaining):
            written = os.write(descriptor, remaining[offset:])
            if written <= 0:
                raise ReleaseError("Recovery receipt append made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(release_root)
    if crash_hook is not None:
        crash_hook("after-receipt-persistence")
    if recovery_pending_ledger_posture(release_root, pending)[0] != "complete":
        raise ReleaseError("Recovery receipt persistence did not become canonical")
    return dict(pending["receipt"])


def make_history_record(
    release_root: Path,
    *,
    action: str,
    release_id: str,
    previous_release_id: str | None,
    quiescent_record: str,
    quiescent_root: str,
    reload_root: str,
) -> dict[str, Any]:
    records = history(release_root)
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-release-activation",
        "record_id": f"ACTIVATION-{len(records) + 1}",
        "timestamp": utc_now(),
        "action": action,
        "release_id": release_id,
        "previous_release_id": previous_release_id,
        "quiescent_boundary_record": quiescent_record,
        "quiescent_boundary_root_sha256": quiescent_root,
        "post_swap_reload_root_sha256": reload_root,
        "previous_record_hmac_sha256": (
            records[-1]["record_hmac_sha256"] if records else None
        ),
    }
    material["record_hmac_sha256"] = record_hmac(
        release_key(release_root, allow_create=False), material
    )
    return material


def tree_projection(path: Path) -> tuple[str, int]:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"Skill tree is missing or symlinked: {path.name}")
    entries: list[dict[str, str]] = []
    for base, directory_names, file_names in os.walk(path, followlinks=False):
        directory_names.sort()
        file_names.sort()
        base_path = Path(base)
        for name in directory_names:
            child = base_path / name
            if child.is_symlink():
                raise ReleaseError(f"Skill tree contains a directory symlink: {child}")
        for name in file_names:
            child = base_path / name
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ReleaseError(f"Skill tree contains a non-regular file: {child}")
            payload = child.read_bytes()
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "mode": "100755" if metadata.st_mode & stat.S_IXUSR else "100644",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    if not entries or not any(item["path"] == "SKILL.md" for item in entries):
        raise ReleaseError(f"Skill tree is incomplete: {path.name}")
    return digest(entries), len(entries)


def git_archive_projection(repo: Path, commit: str) -> dict[str, dict[str, Any]]:
    """Project the exported skill bytes, including declared export-subst filters."""
    source = exact_git_commit(commit)
    result = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", source, "--", *SKILLS],
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseError(f"Git archive projection failed: {detail or 'git archive'}")
    if not result.stdout or len(result.stdout) > 64 * 1024 * 1024:
        raise ReleaseError("Git archive projection is empty or exceeds its size limit")
    entries: dict[str, list[dict[str, str]]] = {name: [] for name in SKILLS}
    try:
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                relative = member.name.rstrip("/")
                if not relative:
                    continue
                parts = relative.split("/")
                if (
                    parts[0] not in SKILLS
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise ReleaseError("Git archive entry escaped the exact skill set")
                if member.isdir():
                    continue
                if not member.isfile() or len(parts) < 2:
                    raise ReleaseError("Git archive contains a non-regular skill entry")
                source_file = archive.extractfile(member)
                if source_file is None:
                    raise ReleaseError("Git archive regular entry has no content")
                payload = source_file.read()
                if len(payload) != member.size:
                    raise ReleaseError("Git archive entry changed during projection")
                entries[parts[0]].append(
                    {
                        "path": "/".join(parts[1:]),
                        "mode": "100755" if member.mode & 0o100 else "100644",
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
    except (tarfile.TarError, OSError) as exc:
        raise ReleaseError("Git archive projection is invalid") from exc
    projection: dict[str, dict[str, Any]] = {}
    for name in SKILLS:
        ordered = sorted(entries[name], key=lambda item: item["path"])
        if not ordered or not any(item["path"] == "SKILL.md" for item in ordered):
            raise ReleaseError("Git archive lacks the complete three-skill set")
        projection[name] = {
            "content_root_sha256": digest(ordered),
            "file_count": len(ordered),
            "entries": ordered,
        }
    return projection


def sealed_override_projection(
    override_root: Path,
    expected: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if override_root.is_symlink() or not override_root.is_dir():
        raise ReleaseError("Development override root must be one real directory")
    if override_root.stat().st_mode & 0o222:
        raise ReleaseError("Development override root is writable")
    if {item.name for item in override_root.iterdir()} != set(SKILLS):
        raise ReleaseError("Development override does not contain exactly three skills")
    actual: dict[str, dict[str, Any]] = {}
    for name in SKILLS:
        root = override_root / name
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o222:
            raise ReleaseError("Development override skill root is invalid or writable")
        entries: list[dict[str, str]] = []
        for base, directory_names, file_names in os.walk(root, followlinks=False):
            directory_names.sort()
            file_names.sort()
            base_path = Path(base)
            if base_path.is_symlink() or base_path.stat().st_mode & 0o222:
                raise ReleaseError("Development override contains a symlink or writable directory")
            for directory_name in directory_names:
                child = base_path / directory_name
                if child.is_symlink() or child.stat().st_mode & 0o222:
                    raise ReleaseError("Development override contains a symlink or writable directory")
            for file_name in file_names:
                child = base_path / file_name
                metadata = child.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_mode & 0o222
                ):
                    raise ReleaseError("Development override contains an invalid or writable file")
                entries.append(
                    {
                        "path": child.relative_to(root).as_posix(),
                        "mode": "100755" if metadata.st_mode & stat.S_IXUSR else "100644",
                        "sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
                    }
                )
        entries.sort(key=lambda item: item["path"])
        projected = {
            "content_root_sha256": digest(entries),
            "file_count": len(entries),
            "entries": entries,
        }
        if projected != expected.get(name):
            raise ReleaseError("Development override differs from the exact Git archive projection")
        actual[name] = projected
    return actual


def git_tree_entries(repo: Path, commit: str) -> list[tuple[str, str, str]]:
    raw = run_git(repo, "ls-tree", "-r", "-z", commit, "--", *SKILLS, binary=True)
    assert isinstance(raw, bytes)
    entries: list[tuple[str, str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            header, raw_path = item.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split(" ")
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ReleaseError("Git skill tree entry is invalid") from exc
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ReleaseError(f"Git skill tree contains a symlink or unsupported entry: {relative}")
        root_name = relative.split("/", 1)[0]
        if root_name not in SKILLS or "/" not in relative:
            raise ReleaseError(f"Git skill entry is outside the exact release set: {relative}")
        entries.append((mode, object_id, relative))
    roots = {path.split("/", 1)[0] for _mode, _object, path in entries}
    if roots != set(SKILLS):
        raise ReleaseError("Git commit does not contain the complete three-skill set")
    return entries


def materialize_commit(repo: Path, commit: str, destination: Path) -> None:
    for mode, object_id, relative in git_tree_entries(repo, commit):
        output = destination / relative
        if destination not in output.parents:
            raise ReleaseError("Git entry escaped the release staging directory")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = run_git(repo, "cat-file", "blob", object_id, binary=True)
        assert isinstance(payload, bytes)
        descriptor = os.open(
            output,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o755 if mode == "100755" else 0o644,
        )
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def canonical_validator() -> tuple[Path, dict[str, str]]:
    validator = TRUSTED_VALIDATOR_PATH
    if validator.is_symlink() or not validator.is_file():
        raise ReleaseError("Canonical Skill Creator validator is missing or symlinked")
    payload = validator.read_bytes()
    validator_sha256 = hashlib.sha256(payload).hexdigest()
    if validator_sha256 != TRUSTED_VALIDATOR_SHA256:
        raise ReleaseError("Canonical Skill Creator validator content identity differs")
    return validator, {"path": str(validator), "sha256": validator_sha256}


def run_validator(
    validator: Path,
    validator_identity: Mapping[str, str],
    validator_runtime: tuple[Path, Path],
    skill: Path,
) -> dict[str, Any]:
    python, yaml_parent = validator_runtime
    wrapper = (
        "import runpy,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "validator,skill=sys.argv[2:4];"
        "sys.argv=[validator,skill];"
        "runpy.run_path(validator,run_name='__main__')"
    )
    command = [
        str(python),
        "-I",
        "-c",
        wrapper,
        str(yaml_parent),
        str(validator),
        str(skill),
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        env={"HOME": "/var/empty", "LANG": "C", "PATH": "/usr/bin:/bin"},
    )
    output = result.stdout + result.stderr
    if result.returncode:
        raise ReleaseError(f"Skill validation failed for {skill.name}")
    return {
        "status": "passed",
        "validator_path": validator_identity["path"],
        "validator_sha256": validator_identity["sha256"],
        "interpreter_path": str(python),
        "interpreter_sha256": TRUSTED_PYTHON_SHA256,
        "yaml_root_sha256": TRUSTED_YAML_ROOT_SHA256,
        "output_sha256": hashlib.sha256(output).hexdigest(),
    }


def candidate_material(
    source_commit: str,
    skills: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-skill-release-candidate",
        "source_commit": source_commit,
        "skill_names": list(SKILLS),
        "skills": dict(skills),
        "validation": dict(validation),
    }


def validate_review_object(
    value: Mapping[str, Any],
    *,
    implementer_id: str,
    candidate: Mapping[str, Any],
    verify_authority: bool = True,
) -> dict[str, Any]:
    implementer_id = bounded_id(implementer_id, label="implementer ID")
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "reviewer_id",
        "implementer_id",
        "disposition",
        "source_commit",
        "candidate_root_sha256",
        "reviewed_at",
        "evidence",
        "authority_key_sha256",
        "review_root_sha256",
        "signature_base64",
    }
    root_material = {
        item: member
        for item, member in value.items()
        if item not in {"review_root_sha256", "signature_base64"}
    }
    signed_material = {
        item: member for item, member in value.items() if item != "signature_base64"
    }
    reviewer_id = authority_id(
        str(value.get("reviewer_id", "")), label="reviewer ID"
    )
    if (
        set(value) != exact_keys
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind") != "software-factory-skill-release-review"
        or value.get("disposition") != "accepted"
        or value.get("source_commit") != candidate["source_commit"]
        or value.get("candidate_root_sha256") != digest(candidate)
        or value.get("implementer_id") != implementer_id
        or reviewer_id == implementer_id
        or value.get("review_root_sha256") != digest(root_material)
    ):
        raise ReleaseError("Independent review does not bind the exact release candidate")
    bounded_id(str(value.get("record_id", "")), label="review record ID")
    exact_sha256(
        str(value.get("candidate_root_sha256", "")), label="review candidate root"
    )
    evidence = value.get("evidence")
    if (
        not isinstance(value.get("reviewed_at"), str)
        or not value["reviewed_at"]
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 16
        or not all(isinstance(item, str) and 0 < len(item) <= 200 for item in evidence)
    ):
        raise ReleaseError("Independent review evidence is incomplete")
    if verify_authority:
        verify_trusted_signature(
            role="reviewers",
            principal_id=reviewer_id,
            expected_key_sha256=str(value.get("authority_key_sha256", "")),
            signed_material=signed_material,
            signature_base64=str(value.get("signature_base64", "")),
        )
    return dict(value)


def validate_review_evidence(
    path: Path,
    *,
    implementer_id: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    value = load_bounded_json(path, label="Independent review evidence")
    return validate_review_object(
        value, implementer_id=implementer_id, candidate=candidate
    )


def validate_automated_assurance(
    value: Mapping[str, Any], *, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "source_commit",
        "candidate_root_sha256",
        "checks",
        "outcome",
        "assurance_root_sha256",
    }
    root_material = {
        item: member
        for item, member in value.items()
        if item != "assurance_root_sha256"
    }
    checks = value.get("checks")
    expected_ids = [
        name for name, _directory, _pattern, _runtime in AUTOMATED_CHECK_SUITES
    ]
    if (
        set(value) != exact_keys
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind") != AUTOMATED_ASSURANCE_KIND
        or value.get("source_commit") != candidate["source_commit"]
        or value.get("candidate_root_sha256") != digest(candidate)
        or value.get("outcome") != "passed"
        or value.get("assurance_root_sha256") != digest(root_material)
        or not isinstance(checks, list)
        or [item.get("id") for item in checks if isinstance(item, dict)]
        != expected_ids
    ):
        raise ReleaseError("Automated assurance does not bind the exact release candidate")
    bounded_id(str(value.get("record_id", "")), label="automated assurance record")
    for check in checks:
        if (
            not isinstance(check, dict)
            or set(check)
            != {
                "id",
                "status",
                "test_count",
                "failure_count",
                "baseline_failure_count",
                "result_sha256",
            }
            or check.get("status") not in {"passed", "passed-with-baseline"}
            or type(check.get("test_count")) is not int
            or check["test_count"] < 1
            or type(check.get("failure_count")) is not int
            or check["failure_count"] < 0
            or type(check.get("baseline_failure_count")) is not int
            or check["baseline_failure_count"] < check["failure_count"]
            or (
                check["status"] == "passed" and check["failure_count"] != 0
            )
            or (
                check["status"] == "passed-with-baseline"
                and check["failure_count"] == 0
            )
            or check.get("result_sha256")
            != digest(
                {
                    "id": check.get("id"),
                    "status": check.get("status"),
                    "test_count": check.get("test_count"),
                    "failure_count": check.get("failure_count"),
                    "baseline_failure_count": check.get(
                        "baseline_failure_count"
                    ),
                }
            )
        ):
            raise ReleaseError("Automated assurance contains an invalid check result")
        exact_sha256(
            str(check.get("result_sha256", "")),
            label="automated check result",
        )
    return dict(value)


def release_assurance(
    manifest: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    verify_review_authority: bool = True,
) -> tuple[dict[str, Any], str, str]:
    value = manifest.get("independent_review")
    if not isinstance(value, dict):
        raise ReleaseError("Release has no review or automated assurance evidence")
    if value.get("kind") == AUTOMATED_ASSURANCE_KIND:
        assurance = validate_automated_assurance(value, candidate=candidate)
        return (
            assurance,
            str(assurance["record_id"]),
            str(assurance["assurance_root_sha256"]),
        )
    review = validate_review_object(
        value,
        implementer_id=str(value.get("implementer_id", "")),
        candidate=candidate,
        verify_authority=verify_review_authority,
    )
    return review, str(review["record_id"]), str(review["review_root_sha256"])


def automated_test_count(output: bytes) -> int:
    text = output.decode("utf-8", errors="replace")
    matches = re.findall(r"Ran\s+(\d+)\s+tests?", text)
    if not matches:
        raise ReleaseError("Automated candidate check did not report a test count")
    return sum(int(item) for item in matches)


def automated_test_failures(output: bytes) -> set[str]:
    text = output.decode("utf-8", errors="replace")
    return set(re.findall(r"^(?:FAIL|ERROR):\s+(.+)$", text, re.MULTILINE))


def run_automated_suite(
    checkout: Path,
    *,
    runner: Path,
    check_id: str,
    directory: str,
    pattern: str,
    runtime: str,
) -> tuple[int, set[str], bytes]:
    command = (
        [
            str(runner),
            "run",
            "--python",
            "3.14",
            "--with",
            "reportlab",
            "--with",
            "pypdf",
            "python",
        ]
        if runtime == "uv-reportlab"
        else [sys.executable]
    )
    command.extend(
        ["-m", "unittest", "discover", "-s", directory, "-p", pattern]
    )
    result = subprocess.run(
        command,
        cwd=checkout,
        check=False,
        capture_output=True,
        timeout=AUTOMATED_CHECK_TIMEOUT_SECONDS,
    )
    output = result.stdout + result.stderr
    count = automated_test_count(output)
    failures = automated_test_failures(output)
    if result.returncode and not failures:
        detail = output.decode("utf-8", errors="replace")[-1200:].strip()
        raise ReleaseError(
            f"Automated candidate check could not be evaluated: {check_id}: {detail}"
        )
    return count, failures, output


def run_automated_checks(
    repo: Path,
    source_commit: str,
    baseline_commit: str | None = None,
) -> list[dict[str, Any]]:
    try:
        runner = AUTOMATED_CHECK_RUNNER.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ReleaseError("Automated candidate check runner is unavailable") from exc
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise ReleaseError("Automated candidate check runner is unavailable")
    with tempfile.TemporaryDirectory(prefix="software-factory-candidate-checks-") as raw:
        checkout = Path(raw) / "candidate"
        run_git(repo, "worktree", "add", "--detach", str(checkout), source_commit)
        baseline_checkout = Path(raw) / "baseline"
        baseline_added = False
        try:
            checks: list[dict[str, Any]] = []
            for check_id, directory, pattern, runtime in AUTOMATED_CHECK_SUITES:
                test_count, failures, output = run_automated_suite(
                    checkout,
                    runner=runner,
                    check_id=check_id,
                    directory=directory,
                    pattern=pattern,
                    runtime=runtime,
                )
                baseline_failures: set[str] = set()
                if failures and baseline_commit:
                    if not baseline_added:
                        run_git(
                            repo,
                            "worktree",
                            "add",
                            "--detach",
                            str(baseline_checkout),
                            baseline_commit,
                        )
                        baseline_added = True
                    _baseline_count, baseline_failures, _baseline_output = (
                        run_automated_suite(
                            baseline_checkout,
                            runner=runner,
                            check_id=f"{check_id}-baseline",
                            directory=directory,
                            pattern=pattern,
                            runtime=runtime,
                        )
                    )
                new_failures = failures - baseline_failures
                if new_failures:
                    detail = output.decode("utf-8", errors="replace")[-1200:].strip()
                    raise ReleaseError(
                        f"Automated candidate check added failures: {check_id}: "
                        f"{', '.join(sorted(new_failures))}: {detail}"
                    )
                status = "passed-with-baseline" if failures else "passed"
                result_material = {
                    "id": check_id,
                    "status": status,
                    "test_count": test_count,
                    "failure_count": len(failures),
                    "baseline_failure_count": len(baseline_failures),
                }
                checks.append(
                    {**result_material, "result_sha256": digest(result_material)}
                )
            return checks
        finally:
            run_git(repo, "worktree", "remove", "--force", str(checkout))
            if baseline_added:
                run_git(
                    repo,
                    "worktree",
                    "remove",
                    "--force",
                    str(baseline_checkout),
                )


def automated_assurance(
    candidate: Mapping[str, Any], checks: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    material: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": AUTOMATED_ASSURANCE_KIND,
        "record_id": (
            f"AUTOMATED-{str(candidate['source_commit'])[:12]}-"
            f"{digest(candidate)[:12]}"
        ),
        "source_commit": candidate["source_commit"],
        "candidate_root_sha256": digest(candidate),
        "checks": [dict(item) for item in checks],
        "outcome": "passed",
    }
    material["assurance_root_sha256"] = digest(material)
    return validate_automated_assurance(material, candidate=candidate)


def current_release_id(release_root: Path) -> str | None:
    pointer = release_root / "current"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    if not pointer.is_symlink():
        raise ReleaseError("Current release pointer is not a symlink")
    target = os.readlink(pointer)
    expected_prefix = "releases/"
    if not target.startswith(expected_prefix) or "/" in target[len(expected_prefix) :]:
        raise ReleaseError("Current release pointer has an invalid target")
    release_id = target[len(expected_prefix) :]
    resolved = pointer.resolve(strict=True)
    expected = (release_root / "releases" / release_id).resolve(strict=True)
    if resolved != expected or expected.parent != (release_root / "releases").resolve():
        raise ReleaseError("Current release pointer escapes the release root")
    return release_id


def release_tree_is_sealed(release: Path) -> bool:
    for base, directory_names, file_names in os.walk(release, followlinks=False):
        base_path = Path(base)
        if base_path.stat().st_mode & 0o222:
            return False
        for name in directory_names:
            child = base_path / name
            if child.is_symlink() or child.stat().st_mode & 0o222:
                return False
        for name in file_names:
            child = base_path / name
            if child.is_symlink() or child.stat().st_mode & 0o222:
                return False
    return True


def read_manifest(
    release_root: Path,
    release_id: str,
    *,
    require_acceptance: bool = True,
    verify_review_authority: bool = True,
) -> dict[str, Any]:
    bounded_id(release_id, label="release ID")
    releases = release_root / "releases"
    if releases.is_symlink() or not releases.is_dir():
        raise ReleaseError("Canonical releases directory is missing or symlinked")
    release = releases / release_id
    if release.is_symlink() or not release.is_dir() or release.resolve().parent != releases.resolve():
        raise ReleaseError("Release directory is missing or escapes the release root")
    expected_names = set(SKILLS) | {MANIFEST_NAME}
    if {item.name for item in release.iterdir()} != expected_names:
        raise ReleaseError("Release set is partial or contains unexpected members")
    manifest_path = release / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ReleaseError("Release manifest is missing or symlinked")
    manifest = load_bounded_json(
        manifest_path, label="Release manifest", maximum=65536
    )
    exact_keys = {
        "schema_version",
        "kind",
        "release_id",
        "created_at",
        "source_commit",
        "candidate_root_sha256",
        "skill_names",
        "skills",
        "validation",
        "independent_review",
        "previous_active_release_id",
        "manifest_sha256",
    }
    material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (
        set(manifest) != exact_keys
        or type(manifest.get("schema_version")) is not int
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("kind") != "software-factory-skill-release"
        or manifest.get("release_id") != release_id
        or manifest.get("manifest_sha256") != digest(material)
        or list(manifest.get("skill_names", [])) != list(SKILLS)
        or not release_tree_is_sealed(release)
    ):
        raise ReleaseError("Release manifest identity or digest is invalid")
    source_commit = exact_git_commit(str(manifest.get("source_commit", "")))
    skills = manifest.get("skills")
    if not isinstance(skills, dict) or set(skills) != set(SKILLS):
        raise ReleaseError("Release manifest does not describe exactly three skills")
    validation = manifest.get("validation")
    if not isinstance(validation, dict) or set(validation) != set(SKILLS):
        raise ReleaseError("Release manifest has no exact validator evidence")
    for name in SKILLS:
        root, count = tree_projection(release / name)
        if skills[name] != {"content_root_sha256": root, "file_count": count}:
            raise ReleaseError(f"Release skill content drifted: {name}")
        validator_record = validation[name]
        if (
            not isinstance(validator_record, dict)
            or set(validator_record)
            != {
                "status",
                "validator_path",
                "validator_sha256",
                "interpreter_path",
                "interpreter_sha256",
                "yaml_root_sha256",
                "output_sha256",
            }
            or validator_record.get("status") != "passed"
            or validator_record.get("validator_path") != str(TRUSTED_VALIDATOR_PATH)
            or validator_record.get("validator_sha256")
            not in {
                TRUSTED_VALIDATOR_SHA256,
                *TRUSTED_HISTORICAL_VALIDATOR_SHA256S,
            }
            or validator_record.get("interpreter_path") != str(TRUSTED_PYTHON_PATH)
            or validator_record.get("interpreter_sha256") != TRUSTED_PYTHON_SHA256
            or validator_record.get("yaml_root_sha256")
            != TRUSTED_YAML_ROOT_SHA256
        ):
            raise ReleaseError("Release validator evidence is invalid")
        exact_sha256(
            str(validator_record.get("validator_sha256", "")),
            label="validator content root",
        )
        exact_sha256(
            str(validator_record.get("output_sha256", "")),
            label="validator output root",
        )
    candidate = candidate_material(source_commit, skills, validation)
    candidate_root = digest(candidate)
    assurance, assurance_record_id, assurance_root = release_assurance(
        manifest,
        candidate=candidate,
        verify_review_authority=verify_review_authority,
    )
    if (
        manifest.get("candidate_root_sha256") != candidate_root
        or assurance.get("source_commit") != source_commit
        or assurance.get("candidate_root_sha256") != candidate_root
    ):
        raise ReleaseError("Release candidate and assurance binding differ")
    identity_field = (
        "assurance_root_sha256"
        if assurance.get("kind") == AUTOMATED_ASSURANCE_KIND
        else "review_root_sha256"
    )
    expected_release_id = f"{source_commit[:12]}-{digest({'candidate_root_sha256': candidate_root, identity_field: assurance_root})[:12]}"
    if release_id != expected_release_id:
        raise ReleaseError("Release ID does not match its accepted content projection")
    if require_acceptance:
        accepted = accepted_release_record(release_root, release_id)
        if (
            accepted is None
            or accepted["source_commit"] != source_commit
            or accepted["manifest_sha256"] != manifest["manifest_sha256"]
            or accepted["candidate_root_sha256"] != candidate_root
            or accepted["review_record_id"] != assurance_record_id
            or accepted["review_root_sha256"] != assurance_root
        ):
            raise ReleaseError("Release is not bound to canonical acceptance")
    return manifest


def verified_source(repo: Path, source_commit: str) -> None:
    resolved = run_git(repo, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if resolved != source_commit:
        raise ReleaseError("Source commit does not resolve exactly")
    if run_git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseError("Source repository is dirty")


def build_candidate(repo: Path, source_commit: str, destination: Path) -> dict[str, Any]:
    validator, validator_identity = canonical_validator()
    validator_runtime = trusted_validator_python()
    materialize_commit(repo, source_commit, destination)
    skills: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    for name in SKILLS:
        validation[name] = run_validator(
            validator, validator_identity, validator_runtime, destination / name
        )
        root, count = tree_projection(destination / name)
        skills[name] = {"content_root_sha256": root, "file_count": count}
    return candidate_material(source_commit, skills, validation)


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def review_request(args: argparse.Namespace) -> dict[str, Any]:
    repo = ensure_directory(Path(args.repo), label="source repository", create=False)
    source_commit = exact_git_commit(args.source_commit)
    verified_source(repo, source_commit)
    with tempfile.TemporaryDirectory(prefix="software-factory-review-request-") as raw:
        candidate = build_candidate(repo, source_commit, Path(raw))
    return {**candidate, "candidate_root_sha256": digest(candidate)}


def stage_release(args: argparse.Namespace) -> dict[str, Any]:
    repo = ensure_directory(Path(args.repo), label="source repository", create=False)
    release_root = ensure_directory(Path(args.release_root), label="release root")
    require_no_pending_recovery(release_root, operation="stage")
    releases = ensure_directory(release_root / "releases", label="release directory")
    source_commit = exact_git_commit(args.source_commit)
    verified_source(repo, source_commit)
    review_argument = getattr(args, "review_evidence", None)
    review_path: Path | None = None
    implementer_id = ""
    checks: list[dict[str, Any]] | None = None
    candidate_projection: dict[str, Any] | None = None
    if review_argument:
        implementer_id = bounded_id(
            str(getattr(args, "implementer_id", "") or ""),
            label="implementer ID",
        )
        review_path = Path(review_argument).resolve(strict=True)
        if path_is_within(review_path, repo) or path_is_within(review_path, release_root):
            raise ReleaseError("Independent review evidence must remain externally owned")
    else:
        with tempfile.TemporaryDirectory(
            prefix="software-factory-stage-projection-"
        ) as raw:
            candidate_projection = build_candidate(repo, source_commit, Path(raw))
        existing = accepted_automated_stage(release_root, candidate_projection)
        if existing is not None:
            return existing
        active_release = current_release_id(release_root)
        baseline_commit = (
            str(read_manifest(release_root, active_release)["source_commit"])
            if active_release
            else None
        )
        checks = run_automated_checks(repo, source_commit, baseline_commit)
    temporary = releases / f".stage-{os.getpid()}-{secrets.token_hex(6)}"
    with release_lock(release_root):
        require_no_pending_recovery(release_root, operation="stage")
        try:
            temporary.mkdir(mode=0o700)
            candidate = build_candidate(repo, source_commit, temporary)
            if candidate_projection is not None:
                if candidate != candidate_projection:
                    raise ReleaseError("Candidate projection changed before staging")
                existing = accepted_automated_stage(release_root, candidate)
                if existing is not None:
                    shutil.rmtree(temporary)
                    return existing
            assurance = (
                validate_review_evidence(
                    review_path,
                    implementer_id=implementer_id,
                    candidate=candidate,
                )
                if review_path is not None
                else automated_assurance(candidate, checks or [])
            )
            candidate_root = digest(candidate)
            identity_field = (
                "assurance_root_sha256"
                if assurance.get("kind") == AUTOMATED_ASSURANCE_KIND
                else "review_root_sha256"
            )
            assurance_root = str(assurance[identity_field])
            release_id = (
                f"{source_commit[:12]}-"
                f"{digest({'candidate_root_sha256': candidate_root, identity_field: assurance_root})[:12]}"
            )
            destination = releases / release_id
            manifest: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "kind": "software-factory-skill-release",
                "release_id": release_id,
                "created_at": utc_now(),
                "source_commit": source_commit,
                "candidate_root_sha256": candidate_root,
                "skill_names": list(SKILLS),
                "skills": candidate["skills"],
                "validation": candidate["validation"],
                "independent_review": assurance,
                "previous_active_release_id": current_release_id(release_root),
            }
            manifest["manifest_sha256"] = digest(manifest)
            atomic_json(temporary / MANIFEST_NAME, manifest)
            fsync_tree_directories(temporary)
            if destination.exists():
                existing = read_manifest(
                    release_root, release_id, require_acceptance=False
                )
                if any(
                    existing.get(key) != manifest.get(key)
                    for key in (
                        "source_commit",
                        "skill_names",
                        "skills",
                        "independent_review",
                    )
                ):
                    raise ReleaseError("Existing release ID has different content")
                shutil.rmtree(temporary)
                append_acceptance(release_root, existing)
                return {"stage": "existing", **existing}
            seal_release_tree(temporary)
            fsync_tree_directories(temporary)
            os.replace(temporary, destination)
            fsync_directory(releases)
            read_manifest(release_root, release_id, require_acceptance=False)
            append_acceptance(release_root, manifest)
            return {"stage": "created", **manifest}
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise


def desired_link(release_root: Path, name: str) -> str:
    return str(release_root / "current" / name)


def installed_link_state(install_root: Path, release_root: Path) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name in SKILLS:
        path = install_root / name
        target = os.readlink(path) if path.is_symlink() else None
        state[name] = {
            "path": str(path),
            "target": target,
            "stable": target == desired_link(release_root, name),
            "exists": path.exists() or path.is_symlink(),
        }
    return state


def pending_recovery_status(
    release_root: Path,
    installed: Mapping[str, Mapping[str, Any]],
    active_release_id: str | None,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Return authenticated, content-minimized recovery identity and posture."""
    pending = load_recovery_pending(release_root)
    if pending is None:
        return None
    ledger_posture, _prior_records = recovery_pending_ledger_posture(
        release_root, pending
    )
    targets = {name: installed[name]["target"] for name in SKILLS}
    original = dict(pending["original_links"])
    desired = dict(pending["desired_links"])
    if targets == original:
        link_posture = "override"
    elif targets == desired:
        link_posture = "stable"
    elif all(targets[name] in {original[name], desired[name]} for name in SKILLS):
        link_posture = "partial"
    else:
        link_posture = "divergent"
    activation = records[-1] if records else None
    owner_current = bool(activation) and all(
        (
            active_release_id == pending["current_release_id"],
            len(records) == pending["activation_history_count"],
            activation.get("record_id") == pending["activation_record_id"],
            activation.get("record_hmac_sha256")
            == pending["activation_record_hmac_sha256"],
        )
    )
    return {
        "kind": pending["kind"],
        "intent_id": pending["intent_id"],
        "phase": pending["phase"],
        "current_release_id": pending["current_release_id"],
        "activation_record_id": pending["activation_record_id"],
        "activation_record_hmac_sha256": pending[
            "activation_record_hmac_sha256"
        ],
        "override_source_commit": pending["override_source_commit"],
        "candidate_source_commit": pending["candidate_source_commit"],
        "link_posture": link_posture,
        "recovery_ledger_posture": ledger_posture,
        "owner_current": owner_current,
        "reconciliation_owner": "recover-installed-links",
    }


def swap_pointer(release_root: Path, release_id: str | None) -> None:
    require_no_pending_recovery(release_root, operation="current-pointer swap")
    pointer = release_root / "current"
    if release_id is None:
        if pointer.exists() or pointer.is_symlink():
            pointer.unlink()
            fsync_directory(release_root)
        return
    read_manifest(release_root, release_id)
    temporary = release_root / f".current-{os.getpid()}-{secrets.token_hex(6)}"
    try:
        os.symlink(f"releases/{release_id}", temporary)
        fsync_directory(release_root)
        os.replace(temporary, pointer)
        fsync_directory(release_root)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def restore_pointer(release_root: Path, release_id: str | None) -> None:
    failures: list[str] = []
    for _attempt in range(3):
        try:
            swap_pointer(release_root, release_id)
            if current_release_id(release_root) == release_id:
                return
            failures.append("restored pointer did not resolve to the prior release")
        except Exception as exc:
            failures.append(str(exc))
    raise ReleaseError(
        "Current-pointer recovery failed after three attempts: "
        + "; ".join(failures)
    )


def verify_bootstrap_source(
    install_root: Path,
    bootstrap_source_root: Path | None,
    manifest: Mapping[str, Any],
) -> list[str | None]:
    originals: list[str | None] = []
    states = []
    for name in SKILLS:
        path = install_root / name
        states.append("absent" if not (path.exists() or path.is_symlink()) else "present")
        if path.exists() or path.is_symlink():
            if not path.is_symlink():
                raise ReleaseError("Existing skill discovery path is not a symlink")
            originals.append(os.readlink(path))
        else:
            originals.append(None)
    if len(set(states)) != 1:
        raise ReleaseError("Partial installed skill set cannot be bootstrapped")
    if states[0] == "absent":
        if bootstrap_source_root is not None:
            raise ReleaseError("Bootstrap source root is invalid for an empty install")
        return originals
    if bootstrap_source_root is None:
        raise ReleaseError("Existing installation requires an exact bootstrap source root")
    source = ensure_directory(
        bootstrap_source_root, label="bootstrap source root", create=False
    )
    for name in SKILLS:
        path = install_root / name
        if path.resolve(strict=True) != (source / name).resolve(strict=True):
            raise ReleaseError("Installed skill target differs from bootstrap source root")
        root, count = tree_projection(path.resolve(strict=True))
        if manifest["skills"][name] != {
            "content_root_sha256": root,
            "file_count": count,
        }:
            raise ReleaseError("Bootstrap source content differs from staged baseline")
    return originals


def replace_link(path: Path, target: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}")
    try:
        os.symlink(target, temporary)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def restore_links(install_root: Path, originals: Sequence[str | None]) -> None:
    failures: list[str] = []
    for name, target in zip(SKILLS, originals):
        path = install_root / name
        restored = False
        for _attempt in range(3):
            try:
                if target is None:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                        fsync_directory(install_root)
                else:
                    replace_link(path, target)
                restored = (
                    (target is None and not (path.exists() or path.is_symlink()))
                    or (target is not None and path.is_symlink() and os.readlink(path) == target)
                )
                if restored:
                    break
            except OSError:
                continue
        if not restored:
            failures.append(name)
    if failures:
        raise ReleaseError(
            "Bootstrap recovery could not restore discovery links: "
            + ", ".join(failures)
        )


def bootstrap_links(
    install_root: Path,
    release_root: Path,
    originals: Sequence[str | None],
    *,
    fail_after: int | None = None,
) -> None:
    for index, name in enumerate(SKILLS, start=1):
        replace_link(install_root / name, desired_link(release_root, name))
        if fail_after == index:
            raise ReleaseError("Injected bootstrap interruption")


def verify_installed(
    release_root: Path,
    install_root: Path,
    expected_release: str,
    *,
    verify_review_authority: bool = True,
) -> dict[str, Any]:
    manifest = read_manifest(
        release_root,
        expected_release,
        verify_review_authority=verify_review_authority,
    )
    if current_release_id(release_root) != expected_release:
        raise ReleaseError("Current pointer differs from expected release")
    resolved_roots: dict[str, str] = {}
    for name in SKILLS:
        link = install_root / name
        if not link.is_symlink() or os.readlink(link) != desired_link(release_root, name):
            raise ReleaseError("Installed discovery links are not the stable release links")
        resolved = link.resolve(strict=True)
        expected = (release_root / "releases" / expected_release / name).resolve()
        if resolved != expected:
            raise ReleaseError("Installed skill resolves outside the active release")
        root, _count = tree_projection(resolved)
        if root != manifest["skills"][name]["content_root_sha256"]:
            raise ReleaseError("Installed skill root differs from the release manifest")
        resolved_roots[name] = root
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-post-swap-resolution",
        "release_id": expected_release,
        "installed_roots": resolved_roots,
    }
    return {**material, "verification_root_sha256": digest(material)}


def child_reload_verify(
    release_root: Path, install_root: Path, expected_release: str
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--release-root",
            str(release_root),
            "--install-root",
            str(install_root),
            "verify-installed",
            "--expected-release",
            expected_release,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ReleaseError("Fresh-process post-swap resolution verification failed")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError("Post-swap verifier returned invalid evidence") from exc
    if value.get("release_id") != expected_release:
        raise ReleaseError("Post-swap verifier returned stale release evidence")
    exact_sha256(
        str(value.get("verification_root_sha256", "")),
        label="post-swap verification root",
    )
    return value


def canonical_recovery_roots(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    release_root = ensure_directory(
        Path(args.release_root), label="release root", create=False
    )
    install_root = ensure_directory(
        Path(args.install_root), label="skill install root", create=False
    )
    canonical_release = ensure_directory(
        CANONICAL_RELEASE_ROOT, label="canonical release root", create=False
    )
    canonical_install = ensure_directory(
        CANONICAL_INSTALL_ROOT, label="canonical skill install root", create=False
    )
    override_parent = ensure_directory(
        CANONICAL_DEV_OVERRIDES_ROOT,
        label="canonical development-override root",
        create=False,
    )
    if release_root != canonical_release or install_root != canonical_install:
        raise ReleaseError("Installed-link recovery requires canonical owner roots")
    return release_root, install_root, override_parent


def recovery_state(
    *,
    repo: Path,
    release_root: Path,
    install_root: Path,
    override_parent: Path,
    override_source_commit: str,
    candidate_source_commit: str,
    expected_current_release: str,
    expected_activation_hmac: str,
) -> dict[str, Any]:
    if run_git(repo, "rev-parse", "--show-toplevel") != str(repo):
        raise ReleaseError("Recovery repository is not the exact Git worktree root")
    verified_source(repo, candidate_source_commit)
    if run_git(repo, "rev-parse", "HEAD") != candidate_source_commit:
        raise ReleaseError("Recovery candidate is not the exact repository HEAD")
    candidate_parent = run_git(repo, "rev-parse", f"{candidate_source_commit}^")
    if candidate_parent != override_source_commit:
        raise ReleaseError("Recovery candidate does not have the exact override parent")

    active = current_release_id(release_root)
    if active != expected_current_release:
        raise ReleaseError("Current release differs from the recovery expectation")
    manifest = read_manifest(release_root, expected_current_release)
    active_source = exact_git_commit(str(manifest["source_commit"]))
    run_git(repo, "merge-base", "--is-ancestor", active_source, override_source_commit)
    records = history(release_root)
    if not records or records[-1]["release_id"] != expected_current_release:
        raise ReleaseError("Activation head differs from the current release")
    if records[-1]["record_hmac_sha256"] != expected_activation_hmac:
        raise ReleaseError("Activation head HMAC differs from the recovery expectation")

    override_root = override_parent / override_source_commit
    if (
        override_root.is_symlink()
        or not override_root.is_dir()
        or override_root.resolve(strict=True).parent != override_parent
        or override_root.resolve(strict=True).name != override_source_commit
    ):
        raise ReleaseError("Development override is outside its canonical commit root")
    archive = git_archive_projection(repo, override_source_commit)
    sealed_override_projection(override_root, archive)

    targets: dict[str, str | None] = {}
    for name in SKILLS:
        link = install_root / name
        targets[name] = os.readlink(link) if link.is_symlink() else None
    override_targets = {name: str(override_root / name) for name in SKILLS}
    stable_targets = {name: desired_link(release_root, name) for name in SKILLS}
    if targets == override_targets:
        link_mode = "override"
    elif targets == stable_targets:
        link_mode = "stable"
    elif all(
        targets[name] in {override_targets[name], stable_targets[name]}
        for name in SKILLS
    ):
        link_mode = "partial"
    else:
        raise ReleaseError("Installed skill links are foreign or invalid")
    return {
        "current_release_id": active,
        "current_source_commit": active_source,
        "activation_record": records[-1],
        "activation_history_count": len(records),
        "override_source_commit": override_source_commit,
        "override_root": str(override_root),
        "override_archive_projection": archive_projection_summary(archive),
        "candidate_source_commit": candidate_source_commit,
        "candidate_parent_commit": candidate_parent,
        "link_mode": link_mode,
        "link_targets": targets,
        "override_link_targets": override_targets,
        "stable_link_targets": stable_targets,
    }


def recovery_record_matches(
    record: Mapping[str, Any], state: Mapping[str, Any]
) -> bool:
    activation = state["activation_record"]
    return all(
        record.get(field) == expected
        for field, expected in (
            ("current_release_id", state["current_release_id"]),
            ("current_source_commit", state["current_source_commit"]),
            ("activation_record_id", activation["record_id"]),
            ("activation_record_hmac_sha256", activation["record_hmac_sha256"]),
            ("activation_history_count", state["activation_history_count"]),
            ("override_source_commit", state["override_source_commit"]),
            ("override_archive_projection", state["override_archive_projection"]),
            ("candidate_source_commit", state["candidate_source_commit"]),
            ("candidate_parent_commit", state["candidate_parent_commit"]),
        )
    )


def recover_installed_links(
    args: argparse.Namespace,
    *,
    fail_after_links: int | None = None,
    after_lock_acquired: Any | None = None,
    crash_hook: Any | None = None,
) -> dict[str, Any]:
    release_root, install_root, override_parent = canonical_recovery_roots(args)
    repo = ensure_directory(Path(args.repo), label="recovery repository", create=False)
    override_source_commit = exact_git_commit(args.override_source_commit)
    candidate_source_commit = exact_git_commit(args.expected_candidate_source_commit)
    expected_current_release = bounded_id(
        args.expected_current_release, label="expected current release"
    )
    expected_activation_hmac = exact_sha256(
        args.expected_activation_record_hmac_sha256,
        label="expected activation-record HMAC",
    )
    preflight = recovery_state(
        repo=repo,
        release_root=release_root,
        install_root=install_root,
        override_parent=override_parent,
        override_source_commit=override_source_commit,
        candidate_source_commit=candidate_source_commit,
        expected_current_release=expected_current_release,
        expected_activation_hmac=expected_activation_hmac,
    )
    preflight_pending = load_recovery_pending(release_root)
    if preflight_pending is not None:
        if not recovery_pending_matches_state(preflight_pending, preflight):
            raise ReleaseError("Pending recovery intent differs from current owner state")
        recovery_pending_ledger_posture(release_root, preflight_pending)
    elif preflight["link_mode"] == "partial":
        raise ReleaseError("Partial installed links have no durable recovery intent")
    with release_lock(release_root):
        if after_lock_acquired is not None:
            after_lock_acquired()
        locked = recovery_state(
            repo=repo,
            release_root=release_root,
            install_root=install_root,
            override_parent=override_parent,
            override_source_commit=override_source_commit,
            candidate_source_commit=candidate_source_commit,
            expected_current_release=expected_current_release,
            expected_activation_hmac=expected_activation_hmac,
        )
        pending = load_recovery_pending(release_root)
        if locked != preflight or pending != preflight_pending:
            raise ReleaseError("Installed-link recovery state changed under the owner lock")
        recovered_intent = pending is not None
        if pending is None:
            recovery_records = installed_link_recovery_records(release_root)
            matching = [
                item
                for item in recovery_records
                if recovery_record_matches(item, locked)
            ]
            if locked["link_mode"] == "stable":
                if len(matching) != 1 or matching[0] != recovery_records[-1]:
                    raise ReleaseError(
                        "Stable installed links lack one current recovery receipt"
                    )
                child = child_reload_verify(
                    release_root, install_root, expected_current_release
                )
                installed = verify_installed(
                    release_root, install_root, expected_current_release
                )
                if (
                    child != installed
                    or matching[0]["installed_verification_root_sha256"]
                    != installed["verification_root_sha256"]
                ):
                    raise ReleaseError("Idempotent recovery verification differs")
                return {
                    "recovery": "already-complete",
                    "duplicate": True,
                    "receipt": matching[0],
                    "installed": installed,
                }
            if locked["link_mode"] == "partial":
                raise ReleaseError("Partial installed links have no durable recovery intent")
            if matching:
                raise ReleaseError("Recovery receipt replayed after installed-link drift")
            ledger_raw = recovery_ledger_bytes(release_root)
            if recovery_records_from_bytes(release_root, ledger_raw) != recovery_records:
                raise ReleaseError("Recovery ledger changed during intent preparation")
            pending = recovery_pending_record(
                release_root, locked, recovery_records, ledger_raw
            )
            write_recovery_pending(release_root, pending)
            if crash_hook is not None:
                crash_hook("after-intent-persistence")
        else:
            if not recovery_pending_matches_state(pending, locked):
                raise ReleaseError("Pending recovery intent differs under owner lock")

        ledger_posture, prior_records = recovery_pending_ledger_posture(
            release_root, pending
        )
        if locked["link_mode"] == "override" and ledger_posture == "complete":
            raise ReleaseError("Completed recovery receipt conflicts with override links")
        if locked["link_mode"] == "partial":
            restore_links(
                install_root, [pending["original_links"][name] for name in SKILLS]
            )
            locked = recovery_state(
                repo=repo,
                release_root=release_root,
                install_root=install_root,
                override_parent=override_parent,
                override_source_commit=override_source_commit,
                candidate_source_commit=candidate_source_commit,
                expected_current_release=expected_current_release,
                expected_activation_hmac=expected_activation_hmac,
            )
            if locked["link_mode"] != "override" or not recovery_pending_matches_state(
                pending, locked
            ):
                raise ReleaseError("Partial-link recovery did not restore the exact override")

        archive = git_archive_projection(repo, override_source_commit)
        override_root = Path(str(locked["override_root"]))

        def verify_stable() -> dict[str, Any]:
            child = child_reload_verify(
                release_root, install_root, expected_current_release
            )
            installed_value = verify_installed(
                release_root, install_root, expected_current_release
            )
            if child != installed_value:
                raise ReleaseError(
                    "Fresh-process and in-process recovery evidence differ"
                )
            if current_release_id(release_root) != expected_current_release:
                raise ReleaseError("Current pointer changed during installed-link recovery")
            current_history = history(release_root)
            if (
                len(current_history) != pending["activation_history_count"]
                or current_history[-1]["record_id"] != pending["activation_record_id"]
                or current_history[-1]["record_hmac_sha256"]
                != pending["activation_record_hmac_sha256"]
            ):
                raise ReleaseError(
                    "Activation history changed during installed-link recovery"
                )
            return installed_value

        def finalize_stable(
            current_pending: Mapping[str, Any], *, recovered: bool
        ) -> dict[str, Any]:
            installed_value = verify_stable()
            if crash_hook is not None:
                crash_hook("after-installed-verification")
            if current_pending["phase"] == "prepared":
                current_pending = verified_recovery_pending(
                    release_root, current_pending, prior_records, installed_value
                )
                write_recovery_pending(release_root, current_pending)
            elif current_pending["installed_verification_root_sha256"] != installed_value[
                "verification_root_sha256"
            ]:
                raise ReleaseError("Retained recovery verification root differs")
            try:
                receipt = persist_recovery_receipt(
                    release_root, current_pending, crash_hook=crash_hook
                )
            except Exception:
                reopened = load_recovery_pending(release_root)
                if (
                    reopened is None
                    or reopened != current_pending
                    or not recovery_pending_matches_state(reopened, locked)
                ):
                    raise
                verify_stable()
                receipt = persist_recovery_receipt(release_root, reopened)
            if recovery_pending_ledger_posture(release_root, current_pending)[0] != "complete":
                raise ReleaseError("Recovery receipt is not durably complete")
            remove_recovery_pending(release_root)
            return {
                "recovery": "completed-after-retry" if recovered else "completed",
                "duplicate": False,
                "receipt": receipt,
                "installed": installed_value,
            }

        if locked["link_mode"] == "stable":
            return finalize_stable(pending, recovered=True)

        try:
            for index, name in enumerate(SKILLS, start=1):
                replace_link(install_root / name, pending["desired_links"][name])
                if crash_hook is not None:
                    crash_hook(f"after-link-{index}")
                if fail_after_links == index:
                    raise ReleaseError("Injected installed-link recovery interruption")
            return finalize_stable(pending, recovered=recovered_intent)
        except Exception:
            reopened = load_recovery_pending(release_root)
            ledger_pending = (
                reopened
                if reopened is not None and reopened.get("phase") == "verified"
                else pending
            )
            ledger_posture, _ledger_prior = recovery_pending_ledger_posture(
                release_root, ledger_pending
            )
            if ledger_posture == "complete":
                if ledger_pending.get("phase") != "verified":
                    raise ReleaseError(
                        "Completed recovery receipt lacks verified owner state"
                    )
                committed = recovery_state(
                    repo=repo,
                    release_root=release_root,
                    install_root=install_root,
                    override_parent=override_parent,
                    override_source_commit=override_source_commit,
                    candidate_source_commit=candidate_source_commit,
                    expected_current_release=expected_current_release,
                    expected_activation_hmac=expected_activation_hmac,
                )
                if committed["link_mode"] != "stable":
                    raise ReleaseError(
                        "Completed recovery receipt conflicts with installed links"
                    )
                installed_value = verify_stable()
                receipt = dict(ledger_pending["receipt"])
                if receipt["installed_verification_root_sha256"] != installed_value[
                    "verification_root_sha256"
                ]:
                    raise ReleaseError(
                        "Committed recovery receipt verification root differs"
                    )
                if reopened is not None:
                    remove_recovery_pending(release_root)
                return {
                    "recovery": "completed-after-retry",
                    "duplicate": False,
                    "receipt": receipt,
                    "installed": installed_value,
                }
            if reopened is not None and reopened.get("phase") == "verified":
                try:
                    current = recovery_state(
                        repo=repo,
                        release_root=release_root,
                        install_root=install_root,
                        override_parent=override_parent,
                        override_source_commit=override_source_commit,
                        candidate_source_commit=candidate_source_commit,
                        expected_current_release=expected_current_release,
                        expected_activation_hmac=expected_activation_hmac,
                    )
                    if current["link_mode"] == "stable":
                        return finalize_stable(reopened, recovered=True)
                except Exception:
                    if recovery_pending_ledger_posture(release_root, reopened)[0] == "complete":
                        raise ReleaseError(
                            "Recovery receipt is committed; stable cleanup remains retryable"
                        )
            restore_links(
                install_root, [pending["original_links"][name] for name in SKILLS]
            )
            sealed_override_projection(override_root, archive)
            restored = recovery_state(
                repo=repo,
                release_root=release_root,
                install_root=install_root,
                override_parent=override_parent,
                override_source_commit=override_source_commit,
                candidate_source_commit=candidate_source_commit,
                expected_current_release=expected_current_release,
                expected_activation_hmac=expected_activation_hmac,
            )
            if restored["link_mode"] != "override":
                raise ReleaseError(
                    "Installed-link recovery could not restore all original links"
                )
            posture, _prior = recovery_pending_ledger_posture(release_root, pending)
            if posture == "absent":
                remove_recovery_pending(release_root)
            raise


def validate_quiescent_evidence(
    path: Path,
    *,
    release_root: Path,
    operation: str,
    release_id: str,
    previous_release_id: str | None,
) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if path_is_within(resolved, release_root):
        raise ReleaseError("Quiescent-boundary evidence must remain externally owned")
    value = load_bounded_json(resolved, label="Quiescent-boundary evidence", maximum=16384)
    exact_keys = {
        "schema_version",
        "kind",
        "record_id",
        "operator_id",
        "authority_sequence",
        "previous_authority_record_sha256",
        "operation",
        "release_id",
        "previous_active_release_id",
        "observed_at",
        "no_concurrent_skill_resolutions",
        "evidence",
        "authority_key_sha256",
        "evidence_root_sha256",
        "signature_base64",
    }
    root_material = {
        item: member
        for item, member in value.items()
        if item not in {"evidence_root_sha256", "signature_base64"}
    }
    signed_material = {
        item: member for item, member in value.items() if item != "signature_base64"
    }
    if (
        set(value) != exact_keys
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("kind") != "software-factory-quiescent-boundary"
        or value.get("operation") != operation
        or value.get("release_id") != release_id
        or value.get("previous_active_release_id") != previous_release_id
        or value.get("no_concurrent_skill_resolutions") is not True
        or value.get("evidence_root_sha256") != digest(root_material)
    ):
        raise ReleaseError("Quiescent-boundary evidence is stale or does not bind cutover")
    bounded_id(str(value.get("record_id", "")), label="quiescent-boundary record")
    operator_id = authority_id(
        str(value.get("operator_id", "")), label="quiescent-boundary operator"
    )
    if type(value.get("authority_sequence")) is not int or value[
        "authority_sequence"
    ] < 1:
        raise ReleaseError("Quiescent-boundary authority sequence is invalid")
    previous_authority = value.get("previous_authority_record_sha256")
    if previous_authority is not None:
        exact_sha256(
            str(previous_authority), label="previous quiescent authority record"
        )
    evidence = value.get("evidence")
    try:
        observed_at = dt.datetime.fromisoformat(str(value.get("observed_at", "")))
    except ValueError as exc:
        raise ReleaseError("Quiescent-boundary observation time is invalid") from exc
    now = dt.datetime.now(dt.timezone.utc)
    if (
        observed_at.tzinfo is None
        or observed_at < now - dt.timedelta(minutes=10)
        or observed_at > now + dt.timedelta(minutes=1)
        or not isinstance(evidence, list)
        or not evidence
        or len(evidence) > 12
        or not all(isinstance(item, str) and 0 < len(item) <= 200 for item in evidence)
    ):
        raise ReleaseError("Quiescent-boundary evidence is incomplete")
    verify_trusted_signature(
        role="operators",
        principal_id=operator_id,
        expected_key_sha256=str(value.get("authority_key_sha256", "")),
        signed_material=signed_material,
        signature_base64=str(value.get("signature_base64", "")),
    )
    validate_operator_authority_ledger(value)
    for record in history(release_root):
        if (
            record["quiescent_boundary_record"] == value["record_id"]
            or record["quiescent_boundary_root_sha256"]
            == value["evidence_root_sha256"]
        ):
            raise ReleaseError("Quiescent-boundary evidence was already consumed")
    return value


def automated_cutover_guard(
    *, action: str, release_id: str, previous_release_id: str | None
) -> dict[str, str]:
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-atomic-cutover-guard",
        "action": action,
        "release_id": release_id,
        "previous_release_id": previous_release_id,
        "release_lock": "held",
        "pointer_update": "atomic",
        "fresh_process_verification": "required",
        "failure_recovery": "restore-prior-pointer",
    }
    root = digest(material)
    return {
        "record_id": f"AUTO-CUTOVER-{action.upper()}-{root[:20]}",
        "evidence_root_sha256": root,
    }


def activate_release(
    args: argparse.Namespace,
    *,
    action: str = "activate",
    expected_previous_release_id: str | None = None,
    expected_previous_activation_record_hmac_sha256: str | None = None,
) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    release_id = bounded_id(args.release_id, label="release ID")
    with release_lock(release_root):
        require_no_pending_recovery(release_root, operation=action)
        read_manifest(release_root, release_id)
        prior = current_release_id(release_root)
        prior_history = history(release_root)
        history_active = (
            str(prior_history[-1]["release_id"]) if prior_history else None
        )
        if history_active != prior:
            raise ReleaseError("Current pointer and activation history differ")
        if expected_previous_release_id is not None:
            if (
                prior != expected_previous_release_id
                or not prior_history
                or prior_history[-1]["record_hmac_sha256"]
                != expected_previous_activation_record_hmac_sha256
            ):
                raise ReleaseError(
                    "Release owner baseline changed before activation"
                )
        quiescent_argument = getattr(args, "quiescent_evidence", None)
        quiescent = (
            validate_quiescent_evidence(
                Path(quiescent_argument),
                release_root=release_root,
                operation=action,
                release_id=release_id,
                previous_release_id=prior,
            )
            if quiescent_argument
            else automated_cutover_guard(
                action=action,
                release_id=release_id,
                previous_release_id=prior,
            )
        )
        if prior == release_id:
            raise ReleaseError("Requested release is already active")
        prior_links = installed_link_state(install_root, release_root)
        stable_count = sum(bool(item["stable"]) for item in prior_links.values())
        if stable_count == 0:
            raise ReleaseError("Stable discovery links are not bootstrapped")
        if stable_count != len(SKILLS):
            raise ReleaseError("Installed stable discovery link set is partial")
        pointer_swapped = False
        try:
            swap_pointer(release_root, release_id)
            pointer_swapped = True
            reload_evidence = child_reload_verify(
                release_root, install_root, release_id
            )
            installed = verify_installed(release_root, install_root, release_id)
            record = make_history_record(
                release_root,
                action=action,
                release_id=release_id,
                previous_release_id=prior,
                quiescent_record=quiescent["record_id"],
                quiescent_root=quiescent["evidence_root_sha256"],
                reload_root=reload_evidence["verification_root_sha256"],
            )
            append_history(release_root, record)
            return {
                "action": action,
                "active_release_id": release_id,
                "previous_release_id": prior,
                "installed": installed,
                "activation_record": record,
            }
        except Exception:
            if pointer_swapped:
                try:
                    restore_pointer(release_root, prior)
                except Exception as exc:
                    raise ReleaseError(
                        f"{action.capitalize()} recovery was incomplete: {exc}"
                    )
            raise


def bootstrap_release(
    args: argparse.Namespace,
    *,
    fail_after_bootstrap_links: int | None = None,
) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    release_id = bounded_id(args.release_id, label="release ID")
    source_root = Path(args.legacy_source_root) if args.legacy_source_root else None
    with release_lock(release_root):
        require_no_pending_recovery(release_root, operation="bootstrap")
        manifest = read_manifest(release_root, release_id)
        if current_release_id(release_root) is not None:
            raise ReleaseError("Release owner is already bootstrapped")
        if history(release_root):
            raise ReleaseError("Activation history exists without a current release")
        quiescent_argument = getattr(args, "quiescent_evidence", None)
        quiescent = (
            validate_quiescent_evidence(
                Path(quiescent_argument),
                release_root=release_root,
                operation="bootstrap",
                release_id=release_id,
                previous_release_id=None,
            )
            if quiescent_argument
            else automated_cutover_guard(
                action="bootstrap",
                release_id=release_id,
                previous_release_id=None,
            )
        )
        links = installed_link_state(install_root, release_root)
        if any(item["stable"] for item in links.values()):
            raise ReleaseError("Installed stable discovery link set is partial")
        originals = verify_bootstrap_source(install_root, source_root, manifest)
        pointer_swapped = False
        try:
            swap_pointer(release_root, release_id)
            pointer_swapped = True
            bootstrap_links(
                install_root,
                release_root,
                originals,
                fail_after=fail_after_bootstrap_links,
            )
            reload_evidence = child_reload_verify(
                release_root, install_root, release_id
            )
            installed = verify_installed(release_root, install_root, release_id)
            record = make_history_record(
                release_root,
                action="bootstrap",
                release_id=release_id,
                previous_release_id=None,
                quiescent_record=quiescent["record_id"],
                quiescent_root=quiescent["evidence_root_sha256"],
                reload_root=reload_evidence["verification_root_sha256"],
            )
            append_history(release_root, record)
            return {
                "action": "bootstrap",
                "active_release_id": release_id,
                "previous_release_id": None,
                "installed": installed,
                "activation_record": record,
            }
        except Exception:
            recovery_errors: list[str] = []
            if pointer_swapped:
                try:
                    restore_pointer(release_root, None)
                except Exception as exc:
                    recovery_errors.append(f"pointer: {exc}")
            try:
                restore_links(install_root, originals)
            except Exception as exc:
                recovery_errors.append(f"links: {exc}")
            if recovery_errors:
                raise ReleaseError(
                    "Bootstrap recovery was incomplete: " + "; ".join(recovery_errors)
                )
            raise


def rollback_release(args: argparse.Namespace) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    require_no_pending_recovery(release_root, operation="rollback")
    expected_current_release = getattr(args, "expected_current_release", None)
    expected_current_activation = getattr(
        args, "expected_current_activation_record", None
    )
    if bool(expected_current_release) != bool(expected_current_activation):
        raise ReleaseError(
            "Expected-current rollback guard requires both release and activation identities"
        )
    if expected_current_release is not None:
        expected_current_release = bounded_id(
            str(expected_current_release), label="expected current release ID"
        )
        expected_current_activation = exact_sha256(
            str(expected_current_activation),
            label="expected current activation record",
        )
    records = history(release_root)
    current = current_release_id(release_root)
    prior_ids = [
        str(record["release_id"])
        for record in records
        if record.get("release_id") != current
    ]
    if args.release_id:
        selected = bounded_id(args.release_id, label="rollback release ID")
        if selected not in prior_ids:
            raise ReleaseError("Rollback target is not a prior accepted active release")
    else:
        selected = prior_ids[-1] if prior_ids else ""
        if not selected:
            raise ReleaseError("No prior accepted active release is available")
    args.release_id = selected
    return activate_release(
        args,
        action="rollback",
        expected_previous_release_id=expected_current_release,
        expected_previous_activation_record_hmac_sha256=(
            expected_current_activation
        ),
    )


def promote_release(args: argparse.Namespace) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    require_no_pending_recovery(release_root, operation="promote")
    staged = stage_release(args)
    release_id = str(staged["release_id"])
    args.release_id = release_id
    args.quiescent_evidence = None
    current = current_release_id(release_root)
    if current == release_id:
        activated = {
            "action": "already-active",
            "active_release_id": release_id,
            "previous_release_id": release_id,
            "installed": verify_installed(
                release_root,
                ensure_directory(Path(args.install_root), label="skill install root"),
                release_id,
            ),
        }
    elif current is None:
        args.legacy_source_root = args.legacy_source_root or args.repo
        activated = bootstrap_release(args)
    else:
        activated = activate_release(args)
    return {
        "promotion": "completed",
        "stage": staged["stage"],
        "release_id": release_id,
        "source_commit": staged["source_commit"],
        "automated_assurance": staged["independent_review"],
        "activation": activated,
    }


def restore_adoption_release(args: argparse.Namespace) -> dict[str, Any]:
    """Restore one frozen adopted release through the normal release owner.

    A retry after the rollback rehydrates the unique rollback transition and
    does not consume another operator record.
    """
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    require_no_pending_recovery(release_root, operation="adoption rollback")
    target_release_id = bounded_id(args.release_id, label="rollback release ID")
    expected_candidate_release_id = bounded_id(
        args.expected_candidate_release_id, label="adopted release ID"
    )
    expected_candidate_activation_hmac = exact_sha256(
        args.expected_candidate_activation_hmac_sha256,
        label="adopted activation HMAC",
    )
    before = status(
        argparse.Namespace(
            release_root=str(release_root),
            install_root=str(install_root),
        )
    )
    activation = before.get("activation_record")
    if not isinstance(activation, Mapping):
        raise ReleaseError("Adoption rollback history is unavailable")
    if before["active_release_id"] == target_release_id:
        matches = [
            item
            for item in history(release_root)
            if item["action"] == "rollback"
            and item["release_id"] == target_release_id
            and item["previous_release_id"] == expected_candidate_release_id
            and item["previous_record_hmac_sha256"]
            == expected_candidate_activation_hmac
        ]
        if len(matches) != 1 or matches[0] != activation:
            raise ReleaseError("Adoption rollback history is ambiguous")
        installed = verify_installed(release_root, install_root, target_release_id)
        return {
            "action": "rollback",
            "duplicate": True,
            "active_release_id": target_release_id,
            "previous_release_id": expected_candidate_release_id,
            "installed": installed,
            "activation_record": matches[0],
        }
    if (
        before["active_release_id"] != expected_candidate_release_id
        or activation.get("record_hmac_sha256")
        != expected_candidate_activation_hmac
    ):
        raise ReleaseError("Adoption rollback baseline changed")
    result = activate_release(
        argparse.Namespace(
            release_root=str(release_root),
            install_root=str(install_root),
            release_id=target_release_id,
            quiescent_evidence=args.quiescent_evidence,
        ),
        action="rollback",
        expected_previous_release_id=expected_candidate_release_id,
        expected_previous_activation_record_hmac_sha256=(
            expected_candidate_activation_hmac
        ),
    )
    return {**result, "duplicate": False}


def adopt_release(args: argparse.Namespace) -> dict[str, Any]:
    """Stage and activate one reviewed candidate through the existing owner.

    This is deliberately a composition of the existing immutable staging and
    one-pointer activation boundaries.  A retry after activation rehydrates
    the exact installed result without consuming a second operator record.
    """
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    require_no_pending_recovery(release_root, operation="adopt")
    baseline_source_commit = exact_git_commit(args.baseline_source_commit)
    before = status(
        argparse.Namespace(
            release_root=str(release_root),
            install_root=str(install_root),
        )
    )
    if (
        before["active_release_id"] is None
        or before["installed_complete"] is not True
        or before["source_commit"] not in {baseline_source_commit, args.source_commit}
    ):
        raise ReleaseError("Adoption baseline is not the exact current installation")
    staged = stage_release(args)
    release_id = str(staged["release_id"])
    if before["active_release_id"] == release_id:
        installed = verify_installed(release_root, install_root, release_id)
        records = history(release_root)
        if not records or records[-1]["release_id"] != release_id:
            raise ReleaseError("Adoption activation history is not current")
        candidate_activations = [
            record for record in records if record["release_id"] == release_id
        ]
        if len(candidate_activations) != 1:
            raise ReleaseError("Adoption activation history is ambiguous")
        activation_record = candidate_activations[0]
        previous_release_id = activation_record["previous_release_id"]
        if previous_release_id is None:
            raise ReleaseError("Adoption activation baseline is unavailable")
        previous_manifest = read_manifest(release_root, str(previous_release_id))
        if previous_manifest["source_commit"] != baseline_source_commit:
            raise ReleaseError("Adoption activation baseline differs")
        result = {
            "schema_version": SCHEMA_VERSION,
            "kind": "software-factory-skill-adoption",
            "duplicate": True,
            "baseline_source_commit": baseline_source_commit,
            "candidate_source_commit": staged["source_commit"],
            "previous_release_id": activation_record["previous_release_id"],
            "active_release_id": release_id,
            "manifest_sha256": staged["manifest_sha256"],
            "candidate_root_sha256": staged["candidate_root_sha256"],
            "review_record_id": staged["independent_review"]["record_id"],
            "reviewer_id": staged["independent_review"]["reviewer_id"],
            "review_root_sha256": staged["independent_review"][
                "review_root_sha256"
            ],
            "acceptance_record_id": accepted_release_record(
                release_root, release_id
            )["record_id"],
            "activation_record_id": activation_record["record_id"],
            "activation_record_hmac_sha256": activation_record[
                "record_hmac_sha256"
            ],
            "previous_activation_record_hmac_sha256": activation_record[
                "previous_record_hmac_sha256"
            ],
            "installed_verification_root_sha256": installed[
                "verification_root_sha256"
            ],
        }
        return {
            **result,
            "adoption_root_sha256": digest(
                {key: value for key, value in result.items() if key != "duplicate"}
            ),
        }
    if before["source_commit"] != baseline_source_commit:
        raise ReleaseError("Adoption candidate does not descend from the active baseline")
    activation = activate_release(
        argparse.Namespace(
            release_root=str(release_root),
            install_root=str(install_root),
            release_id=release_id,
            quiescent_evidence=args.quiescent_evidence,
        ),
        expected_previous_release_id=str(before["active_release_id"]),
        expected_previous_activation_record_hmac_sha256=str(
            before["activation_record"]["record_hmac_sha256"]
        ),
    )
    acceptance = accepted_release_record(release_root, release_id)
    if acceptance is None:
        raise ReleaseError("Adoption release acceptance is unavailable")
    record = activation["activation_record"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": "software-factory-skill-adoption",
        "duplicate": False,
        "baseline_source_commit": baseline_source_commit,
        "candidate_source_commit": staged["source_commit"],
        "previous_release_id": activation["previous_release_id"],
        "active_release_id": activation["active_release_id"],
        "manifest_sha256": staged["manifest_sha256"],
        "candidate_root_sha256": staged["candidate_root_sha256"],
        "review_record_id": staged["independent_review"]["record_id"],
        "reviewer_id": staged["independent_review"]["reviewer_id"],
        "review_root_sha256": staged["independent_review"]["review_root_sha256"],
        "acceptance_record_id": acceptance["record_id"],
        "activation_record_id": record["record_id"],
        "activation_record_hmac_sha256": record["record_hmac_sha256"],
        "previous_activation_record_hmac_sha256": record[
            "previous_record_hmac_sha256"
        ],
        "installed_verification_root_sha256": activation["installed"][
            "verification_root_sha256"
        ],
    }
    return {
        **result,
        "adoption_root_sha256": digest(
            {key: value for key, value in result.items() if key != "duplicate"}
        ),
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    release_root = ensure_directory(Path(args.release_root), label="release root")
    install_root = ensure_directory(Path(args.install_root), label="skill install root")
    with release_lock(release_root):
        active = current_release_id(release_root)
        manifest = read_manifest(release_root, active) if active else None
        records = history(release_root)
        history_active = str(records[-1]["release_id"]) if records else None
        if history_active != active:
            raise ReleaseError("Current pointer and activation history differ")
        installed = installed_link_state(install_root, release_root)
        result: dict[str, Any] = {
            "active_release_id": active,
            "source_commit": manifest.get("source_commit") if manifest else None,
            "manifest_sha256": manifest.get("manifest_sha256") if manifest else None,
            "candidate_root_sha256": (
                manifest.get("candidate_root_sha256") if manifest else None
            ),
            "independent_review": (
                manifest.get("independent_review") if manifest else None
            ),
            "skills": manifest.get("skills") if manifest else None,
            "installed_links": installed,
            "installed_complete": bool(active)
            and all(item["stable"] for item in installed.values()),
            "activation_history_records": len(records),
            "activation_record": records[-1] if records else None,
        }
        result["pending_installed_link_recovery"] = pending_recovery_status(
            release_root, installed, active, records
        )
        acceptance = accepted_release_record(release_root, active) if active else None
        result["acceptance_record"] = acceptance
        if active and result["installed_complete"]:
            result["current_verification"] = verify_installed(
                release_root, install_root, active
            )
        result["release_owner_state_root_sha256"] = digest(result)
        return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--release-root",
        default=str(CANONICAL_RELEASE_ROOT),
    )
    value.add_argument(
        "--install-root", default=str(CANONICAL_INSTALL_ROOT)
    )
    subcommands = value.add_subparsers(dest="command", required=True)

    request = subcommands.add_parser(
        "review-request", help="build the exact read-only release review projection"
    )
    request.add_argument("--repo", required=True)
    request.add_argument("--source-commit", required=True)
    request.set_defaults(func=review_request)

    stage = subcommands.add_parser(
        "stage", help="stage one exact automatically checked or reviewed commit"
    )
    stage.add_argument("--repo", required=True)
    stage.add_argument("--source-commit", required=True)
    stage.add_argument("--implementer-id")
    stage.add_argument("--review-evidence")
    stage.set_defaults(func=stage_release)

    activate = subcommands.add_parser("activate", help="activate one staged release")
    activate.add_argument("release_id")
    activate.add_argument("--quiescent-evidence")
    activate.set_defaults(func=activate_release)

    adopt = subcommands.add_parser(
        "adopt", help="stage and activate one current independently reviewed candidate"
    )
    adopt.add_argument("--repo", required=True)
    adopt.add_argument("--source-commit", required=True)
    adopt.add_argument("--baseline-source-commit", required=True)
    adopt.add_argument("--implementer-id", required=True)
    adopt.add_argument("--review-evidence", required=True)
    adopt.add_argument("--quiescent-evidence", required=True)
    adopt.set_defaults(func=adopt_release)

    bootstrap = subcommands.add_parser(
        "bootstrap", help="install stable links for one content-identical baseline"
    )
    bootstrap.add_argument("release_id")
    bootstrap.add_argument("--quiescent-evidence")
    bootstrap.add_argument("--legacy-source-root")
    bootstrap.set_defaults(func=bootstrap_release)

    rollback = subcommands.add_parser("rollback", help="restore a prior accepted release")
    rollback.add_argument("release_id", nargs="?")
    rollback.add_argument("--quiescent-evidence")
    rollback.add_argument("--expected-current-release", help=argparse.SUPPRESS)
    rollback.add_argument(
        "--expected-current-activation-record", help=argparse.SUPPRESS
    )
    rollback.set_defaults(func=rollback_release)

    recover = subcommands.add_parser(
        "recover-installed-links",
        help="restore the stable discovery links from one verified development override",
    )
    recover.add_argument("--repo", required=True)
    recover.add_argument("--override-source-commit", required=True)
    recover.add_argument("--expected-candidate-source-commit", required=True)
    recover.add_argument("--expected-current-release", required=True)
    recover.add_argument(
        "--expected-activation-record-hmac-sha256", required=True
    )
    recover.set_defaults(func=recover_installed_links)

    promote = subcommands.add_parser(
        "promote",
        help="check, stage, activate, verify, and recover one exact clean commit",
    )
    promote.add_argument("--repo", required=True)
    promote.add_argument("--source-commit", required=True)
    promote.add_argument("--legacy-source-root")
    promote.set_defaults(func=promote_release)

    inspect = subcommands.add_parser("status", help="report exact active roots")
    inspect.set_defaults(func=status)

    verify = subcommands.add_parser(
        "verify-installed", help=argparse.SUPPRESS
    )
    verify.add_argument("--expected-release", required=True)
    verify.set_defaults(
        func=lambda args: verify_installed(
            ensure_directory(Path(args.release_root), label="release root"),
            ensure_directory(Path(args.install_root), label="skill install root"),
            args.expected_release,
            verify_review_authority=False,
        )
    )
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.func(args)
    except (OSError, ReleaseError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
