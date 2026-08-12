#!/usr/bin/env python3
"""Run the bounded Block 17 integrated Factory-evolution dogfood.

The runner exercises production parser/functions against one disposable Git
target and one disposable release owner.  It never writes the live supervision,
skill, release, mission, lifecycle, Gmail, deployment, or external owners.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Mapping
from unittest import mock


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIRECTORY.parent
REPOSITORY_ROOT = SKILL_ROOT.parent
TRACKER_PATH = REPOSITORY_ROOT / "docs" / (
    "software-factory-adaptive-implementation-decision-control-"
    "implementation-tracker.md"
)
DEFAULT_WORKSPACE = Path("/tmp/software-factory-integrated-dogfood-v1")
DEFAULT_LIVE_SKILLS = Path("/Users/ethanstillman/.codex/skills")
ARCHIVE_SOURCE_REVISION = "$Format:%H$"

sys.path.insert(0, str(SCRIPT_DIRECTORY))
import factory_evolution  # noqa: E402
import supervision_log  # noqa: E402


class DogfoodError(RuntimeError):
    """Raised when an integrated dogfood invariant differs."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def source_revision() -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        revision = completed.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", revision):
            return revision
    if re.fullmatch(r"[0-9a-f]{40}", ARCHIVE_SOURCE_REVISION):
        return ARCHIVE_SOURCE_REVISION
    raise DogfoodError("exact source revision is unavailable")


class DeterministicClock:
    """Return a monotonic fixed chronology for reproducible temporary evidence."""

    def __init__(self) -> None:
        self.current = dt.datetime(2026, 8, 11, 20, 0, tzinfo=dt.timezone.utc)

    def __call__(self) -> str:
        value = self.current.isoformat()
        self.current += dt.timedelta(seconds=1)
        return value


class DeterministicBytes:
    """Supply reproducible owner-root material without touching a live key."""

    def __init__(self) -> None:
        self.counter = 0

    def __call__(self, count: int) -> bytes:
        value = b""
        while len(value) < count:
            self.counter += 1
            value += hashlib.sha256(
                f"block17-owner-material-{self.counter}".encode("ascii")
            ).digest()
        return value[:count]


def _git(repository: Path, *arguments: str, env: Mapping[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", str(repository), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(env) if env is not None else None,
    )
    return completed.stdout.strip()


def _commit(repository: Path, message: str, timestamp: str) -> str:
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_DATE": timestamp,
            "GIT_COMMITTER_DATE": timestamp,
            "LC_ALL": "C",
        }
    )
    _git(
        repository,
        "-c",
        "user.name=Factory Dogfood Owner",
        "-c",
        "user.email=factory-dogfood@example.test",
        "commit",
        "-q",
        "-m",
        message,
        env=environment,
    )
    return _git(repository, "rev-parse", "HEAD")


def _copy_git_archive(revision: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination.parent / "source.tar"
    with archive.open("wb") as handle:
        subprocess.run(
            ["/usr/bin/git", "archive", "--format=tar", revision],
            cwd=REPOSITORY_ROOT,
            check=True,
            stdout=handle,
            stderr=subprocess.PIPE,
        )
    with tarfile.open(archive, mode="r:") as source:
        source.extractall(destination)
    archive.unlink()


def _tree_manifest(root: Path) -> tuple[str, int]:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return digest(entries), len(entries)


class TemporaryReleaseOwner:
    """Small normal release-owner seam backed by real disposable installed bytes."""

    class ReleaseError(RuntimeError):
        pass

    def __init__(self, root: Path, repository: Path, baseline: str, candidate: str):
        self.root = root
        self.repository = repository
        self.baseline = baseline
        self.candidate = candidate
        self.active = baseline
        self.activation_count = 0
        self.rollback_count = 0
        self.rollback_active = False
        (self.root / "releases").mkdir(parents=True)
        self._install("baseline-release-1234", baseline)
        self._point("baseline-release-1234")

    def _install(self, release_id: str, revision: str) -> None:
        target = self.root / "releases" / release_id
        if target.exists():
            return
        target.mkdir()
        archive = self.root / f"{release_id}.tar"
        with archive.open("wb") as handle:
            subprocess.run(
                [
                    "/usr/bin/git",
                    "-C",
                    str(self.repository),
                    "archive",
                    "--format=tar",
                    revision,
                ],
                check=True,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
        with tarfile.open(archive, mode="r:") as source:
            source.extractall(target)
        archive.unlink()

    def _point(self, release_id: str) -> None:
        current = self.root / "current"
        temporary = self.root / ".current-next"
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        temporary.symlink_to(Path("releases") / release_id)
        os.replace(temporary, current)

    def _status(self) -> dict[str, object]:
        candidate_active = self.active == self.candidate and not self.rollback_active
        release_id = (
            "candidate-release-1234" if candidate_active else "baseline-release-1234"
        )
        installed = (self.root / "current").resolve(strict=True)
        manifest, file_count = _tree_manifest(installed)
        activation_id = (
            "ACTIVATION-3"
            if self.rollback_active
            else "ACTIVATION-2"
            if candidate_active
            else "ACTIVATION-1"
        )
        activation_hmac = (
            "9" * 64
            if self.rollback_active
            else "e" * 64
            if candidate_active
            else "f" * 64
        )
        result: dict[str, object] = {
            "active_release_id": release_id,
            "source_commit": self.active,
            "manifest_sha256": manifest,
            "candidate_root_sha256": digest(
                {"source_commit": self.active, "manifest_sha256": manifest}
            ),
            "independent_review": {
                "reviewer_id": (
                    "release-reviewer-1234"
                    if candidate_active
                    else "baseline-reviewer-1234"
                )
            },
            "installed_complete": True,
            "acceptance_record": {
                "record_id": (
                    "RELEASE-ACCEPTANCE-2"
                    if candidate_active
                    else "RELEASE-ACCEPTANCE-1"
                ),
                "review_record_id": "release-review-record-1234",
            },
            "activation_record": {
                "record_id": activation_id,
                "record_hmac_sha256": activation_hmac,
                "previous_release_id": (
                    "baseline-release-1234"
                    if candidate_active
                    else "candidate-release-1234"
                    if self.rollback_active
                    else None
                ),
                "previous_record_hmac_sha256": (
                    "f" * 64
                    if candidate_active
                    else "e" * 64
                    if self.rollback_active
                    else None
                ),
            },
            "current_verification": {
                "verification_root_sha256": digest(
                    {"manifest_sha256": manifest, "file_count": file_count}
                )
            },
        }
        result["release_owner_state_root_sha256"] = digest(result)
        return result

    def status(self, _args: object) -> dict[str, object]:
        return self._status()

    def load_bounded_json(self, path: Path, *, label: str) -> dict[str, object]:
        del label
        return json.loads(path.read_text(encoding="utf-8"))

    def adopt_release(self, args: object) -> dict[str, object]:
        if getattr(args, "baseline_source_commit") != self.baseline:
            raise self.ReleaseError("temporary release baseline differs")
        if getattr(args, "source_commit") != self.candidate:
            raise self.ReleaseError("temporary release candidate differs")
        duplicate = self.active == self.candidate and not self.rollback_active
        if not duplicate:
            self._install("candidate-release-1234", self.candidate)
            self.active = self.candidate
            self.rollback_active = False
            self.activation_count += 1
            self._point("candidate-release-1234")
        status = self._status()
        result: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-skill-adoption",
            "duplicate": duplicate,
            "baseline_source_commit": self.baseline,
            "candidate_source_commit": self.candidate,
            "previous_release_id": "baseline-release-1234",
            "active_release_id": status["active_release_id"],
            "manifest_sha256": status["manifest_sha256"],
            "candidate_root_sha256": status["candidate_root_sha256"],
            "review_record_id": "release-review-record-1234",
            "reviewer_id": "release-reviewer-1234",
            "review_root_sha256": "3" * 64,
            "acceptance_record_id": status["acceptance_record"]["record_id"],
            "activation_record_id": status["activation_record"]["record_id"],
            "activation_record_hmac_sha256": status["activation_record"][
                "record_hmac_sha256"
            ],
            "previous_activation_record_hmac_sha256": "f" * 64,
            "installed_verification_root_sha256": status["current_verification"][
                "verification_root_sha256"
            ],
        }
        result["adoption_root_sha256"] = digest(
            {key: value for key, value in result.items() if key != "duplicate"}
        )
        return result

    def history(self, _release_root: Path) -> list[dict[str, object]]:
        records: list[dict[str, object]] = [
            {
                "action": "bootstrap",
                "record_id": "ACTIVATION-1",
                "record_hmac_sha256": "f" * 64,
                "previous_record_hmac_sha256": None,
                "release_id": "baseline-release-1234",
                "previous_release_id": None,
            }
        ]
        if self.activation_count:
            records.append(
                {
                    "action": "activate",
                    "record_id": "ACTIVATION-2",
                    "record_hmac_sha256": "e" * 64,
                    "previous_record_hmac_sha256": "f" * 64,
                    "release_id": "candidate-release-1234",
                    "previous_release_id": "baseline-release-1234",
                }
            )
        if self.rollback_active:
            records.append(
                {
                    "action": "rollback",
                    "record_id": "ACTIVATION-3",
                    "record_hmac_sha256": "9" * 64,
                    "previous_record_hmac_sha256": "e" * 64,
                    "release_id": "baseline-release-1234",
                    "previous_release_id": "candidate-release-1234",
                }
            )
        return records

    def restore_adoption_release(self, args: object) -> dict[str, object]:
        if (
            getattr(args, "expected_candidate_release_id")
            != "candidate-release-1234"
        ):
            raise self.ReleaseError("temporary rollback candidate differs")
        duplicate = self.rollback_active
        if not duplicate:
            self.rollback_active = True
            self.active = self.baseline
            self.rollback_count += 1
            self._point("baseline-release-1234")
        status = self._status()
        return {
            "action": "rollback",
            "duplicate": duplicate,
            "active_release_id": "baseline-release-1234",
            "previous_release_id": "candidate-release-1234",
            "installed": status["current_verification"],
            "activation_record": status["activation_record"],
        }


class DogfoodWorkspace:
    def __init__(self, root: Path, clock: DeterministicClock) -> None:
        self.root = root
        self.clock = clock
        self.repository = root / "target"
        self.supervision_root = root / "supervision"
        self.target_thread = "software-factory-block17-dogfood"
        self.directory = self.supervision_root / self.target_thread
        self.base_revision = ""
        self.evaluator_private = root / "evaluator-private.der"
        self.evaluator_public = (
            root / "authority" / "evaluators" / "evaluator-public.pem"
        )
        self.evaluator_public_sha = ""
        self.release_owner: TemporaryReleaseOwner | None = None

    def git(self, *arguments: str, env: Mapping[str, str] | None = None) -> str:
        return _git(self.repository, *arguments, env=env)

    def command(self, *arguments: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            ["--root", str(self.supervision_root), *arguments]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            args.func(args)
        value = json.loads(output.getvalue())
        if type(value) is not dict:
            raise DogfoodError("operator command did not return an object")
        return value

    def setup(self, revision: str) -> None:
        _copy_git_archive(revision, self.repository)
        proof_path = (
            self.repository
            / "implement-tracker-blocks"
            / "scripts"
            / "test_capability_255083e6fcd14f5d07bc.py"
        )
        proof_path.write_text(
            "import unittest\n"
            "from pathlib import Path\n\n"
            "class TemporaryFactoryCapabilityTests(unittest.TestCase):\n"
            "    def test_installed_outcome_rule(self):\n"
            "        skill = Path(__file__).resolve().parents[1] / 'SKILL.md'\n"
            "        self.assertIn(\n"
            "            'Retain one exact installed-outcome root before terminal acceptance.',\n"
            "            skill.read_text(encoding='utf-8'),\n"
            "        )\n",
            encoding="utf-8",
        )
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.base_revision = _commit(
            self.repository,
            "Create bounded Software Factory dogfood baseline",
            "2026-08-11T19:55:00+00:00",
        )
        self.command(
            "init",
            "--target-thread",
            self.target_thread,
            "--target-label",
            "Software Factory Block 17 dogfood",
            "--watcher-thread",
            "watcher-1234",
            "--reviewer-thread",
            "reviewer-1234",
            "--base-reviewer-thread",
            "base-reviewer-1234",
            "--fix-executor-thread",
            "fix-executor-1234",
            "--mission-source-class",
            "direct-user",
            "--mission-source-record",
            "direct-user-block17-dogfood",
            "--mission-source-sha256",
            "a" * 64,
            "--adaptive-target-repository-root",
            str(self.repository),
        )
        self._bind_range_and_permissions()
        self._install_evaluator_key()

    def _bind_range_and_permissions(self) -> None:
        policy = supervision_log.read_json(self.directory / "policy.json")
        tracker = self.repository / "docs" / TRACKER_PATH.name
        tracker_path, tracker_sha, structure_sha, blocks = (
            supervision_log.implementation_tracker_snapshot(str(tracker))
        )
        authority = {
            "source_class": "direct-user",
            "source_record": "direct-user-block17-dogfood",
            "source_sha256": "a" * 64,
        }
        request = "Demonstrate the complete bounded Blocks 0-17 outcome."
        entry = supervision_log.implementation_range_history_entry(
            sequence=1,
            prior_entry_sha256="",
            operation="bound",
            request_text=request,
            request_bytes=request.encode("utf-8"),
            tracker_sha256=tracker_sha,
            tracker_structure_sha256=structure_sha,
            tracker_path=str(tracker_path),
            tracker_blocks=sorted(blocks),
            range_intent="full-tracker",
            explicit_blocks=[],
            authority=authority,
            authority_policy_version=int(policy["policy_version"]) + 1,
        )
        policy["implementation_range"] = {
            "schema_version": 1,
            "kind": "implementation-range-binding",
            "range_id": "full-tracker-block17-dogfood",
            "genesis_sha256": supervision_log.digest(
                {
                    "range_id": "full-tracker-block17-dogfood",
                    "authority": authority,
                    "request_text_sha256": entry["request_text_sha256"],
                    "initial_tracker_sha256": tracker_sha,
                    "initial_tracker_structure_sha256": structure_sha,
                    "initial_tracker_blocks": sorted(blocks),
                    "initial_range_intent": "full-tracker",
                    "initial_explicit_blocks": [],
                }
            ),
            "authority": authority,
            "range_intent": "full-tracker",
            "explicit_blocks": [],
            "tracker_path": str(tracker_path),
            "tracker_sha256": tracker_sha,
            "tracker_structure_sha256": structure_sha,
            "tracker_blocks": sorted(blocks),
            "history": [entry],
            "history_head_sha256": entry["entry_sha256"],
        }
        policy["adaptive_decision_control"] = (
            supervision_log.adaptive_decision_control_contract(
                "full-autonomous",
                target_class="software-factory",
                target_repository_root=str(self.repository),
            )
        )
        for permission in supervision_log.FACTORY_ADOPTION_REQUIRED_PERMISSIONS:
            policy["permissions"][permission] = True
        policy["permissions"]["command_or_test_execution"] = True
        supervision_log.write_policy_version(
            self.directory,
            policy,
            kind="block17-dogfood-policy",
            reason="Bind one disposable full-autonomous Factory dogfood owner.",
            evidence_values=[tracker_sha, entry["entry_sha256"]],
        )

    def _install_evaluator_key(self) -> None:
        self.evaluator_public.parent.mkdir(parents=True)
        seed = hashlib.sha256(b"software-factory-block17-temporary-evaluator").digest()
        prefix = bytes.fromhex("302e020100300506032b657004220420")
        self.evaluator_private.write_bytes(prefix + seed)
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkey",
                "-inform",
                "DER",
                "-in",
                str(self.evaluator_private),
                "-pubout",
                "-out",
                str(self.evaluator_public),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.evaluator_public.chmod(0o444)
        self.evaluator_public.parent.chmod(0o555)
        self.evaluator_public.parent.parent.chmod(0o555)
        self.evaluator_public_sha = hashlib.sha256(
            self.evaluator_public.read_bytes()
        ).hexdigest()

    def append_signal(self, cycle: str) -> tuple[list[str], Path]:
        policy = supervision_log.read_json(self.directory / "policy.json")
        mission = supervision_log.bound_mission(policy)
        if mission is None:
            raise DogfoodError("temporary mission is not bound")
        event_ids: list[str] = []
        for kind, status, category, summary in (
            (
                "incident",
                "failed",
                "factory-capability-gap",
                f"{cycle} observed a bounded reusable Factory capability gap.",
            ),
            (
                "resolution",
                "resolved",
                "owner-method-effect",
                f"{cycle} retained the existing bounded implementation owner.",
            ),
        ):
            existing = supervision_log.events(self.directory / "events.jsonl")
            record_id = f"EVT-{len(existing) + 1:06d}"
            record = {
                "schema_version": 1,
                "kind": kind,
                "record_id": record_id,
                "timestamp": self.clock(),
                "target_thread_id": self.target_thread,
                "status": status,
                "severity": "warning" if kind == "incident" else "info",
                "category": category,
                "active_block": "Block 17",
                "checkpoint": "integrated-factory-dogfood",
                "summary": summary,
                "resolution": "Proceed only through the bounded existing owner.",
                "evidence": [f"dogfood:{cycle}"],
                "policy_sha256": policy["policy_sha256"],
                "mission_root": mission["mission_root"],
            }
            supervision_log.append_raw(self.directory / "events.jsonl", record)
            event_ids.append(record_id)
        all_events = supervision_log.events(self.directory / "events.jsonl")
        source_root = supervision_log.digest(
            {"record_hashes": [item["record_sha256"] for item in all_events]}
        )
        report_id = f"weekly-{cycle}-{source_root[:12]}"
        report = {
            "schema_version": 1,
            "kind": "supervision-weekly-review-record",
            "report_id": report_id,
            "source_root": source_root,
            "coverage": {
                "start": "2026-08-11T20:00:00+00:00",
                "end": "2026-08-11T21:00:00+00:00",
            },
            "metrics": {"report_id": report_id, "source": {"source_root": source_root}},
            "cognitive_review": {
                "schema_version": 1,
                "kind": "supervision-weekly-review-cognitive-review",
                "report_id": report_id,
                "source_root": source_root,
                "headline": "Bounded Factory capability evidence.",
                "executive_assessment": (
                    "Canonical evidence nominates one bounded existing-owner improvement."
                ),
                "overall_posture": "bounded",
                "sections": {
                    "recommended_bounded_improvements": [
                        {
                            "title": "Retain current installed-outcome evidence",
                            "assessment": (
                                "Use the existing implementation owner and one paired comparison."
                            ),
                            "evidence": event_ids,
                        }
                    ]
                },
            },
        }
        report_directory = self.directory / "reports" / "weekly" / report_id
        report_directory.mkdir(parents=True)
        path = report_directory / "report.json"
        path.write_bytes(canonical(report) + b"\n")
        return event_ids, path

    def admit(self, report: Path) -> dict[str, object]:
        return self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "admit",
            "--report-json",
            str(report),
            "--events-jsonl",
            str(self.directory / "events.jsonl"),
        )

    def _candidate(
        self,
        candidate_id: str,
        candidate_type: str,
        event_ids: list[str],
        *,
        selected: bool,
    ) -> dict[str, object]:
        owner = factory_evolution.candidate_owner_route(candidate_type)
        dimensions = {
            name: {
                "rating": (
                    "high"
                    if name in {"effect", "product_gain", "reversibility"}
                    else "medium"
                ),
                "rationale": f"The bounded {name} evidence remains inspectable.",
                "evidence_ids": [event_ids[0]],
            }
            for name in factory_evolution.SELECTION_DIMENSIONS
        }
        return {
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "capability_gap": (
                "Terminal acceptance lacks one current installed-outcome reminder."
            ),
            "effect": (
                "Retain one exact installed-outcome root before terminal acceptance."
            ),
            "meta_pattern_ids": ["meta-current-outcome"],
            "evidence_ids": list(event_ids),
            "protected_capabilities": ["bounded owner execution"],
            "applicability": "Consequential Software Factory terminal evidence.",
            "tradeoffs": ["Adds one bounded guidance line and focused proof."],
            "uncertainty": "The dogfood covers one paired temporary target.",
            "counterexample_case_ids": [event_ids[1]],
            "counterexample_posture": "observed",
            "counterexample_search": "Compared the bounded owner resolution.",
            "implementation_owner": owner,
            "evaluation_owner": supervision_log.ADAPTIVE_EVALUATOR_ID,
            "smaller_change_insufficient": (
                "A local shortcut would not retain current installed behavior."
            ),
            "proportionality": (
                "Use the existing skill owner without a detector or control platform."
            ),
            "selection_dimensions": dimensions,
        }

    def review_submission(
        self, packet: Mapping[str, Any], event_ids: list[str]
    ) -> dict[str, object]:
        hypotheses = [
            item["hypothesis_id"]
            for item in packet["evidence"]["report_hypotheses"]
        ]
        candidates = [
            self._candidate(
                "candidate-existing-skill-owner",
                "skill-method",
                event_ids,
                selected=True,
            ),
            self._candidate(
                "candidate-lower-power-shortcut",
                "tracker-method",
                event_ids,
                selected=False,
            ),
            self._candidate(
                "candidate-generalized-detector",
                "detector",
                event_ids,
                selected=False,
            ),
        ]
        return {
            "schema_version": 1,
            "kind": factory_evolution.REVIEW_KIND,
            "packet_id": packet["packet_id"],
            "packet_root": packet["packet_root"],
            "reviewer_id": "base-reviewer-1234",
            "observations": [
                {
                    "observation_id": "observation-gap",
                    "summary": "The terminal evidence omitted one installed outcome reminder.",
                    "valence": "exception",
                    "event_ids": [event_ids[0]],
                },
                {
                    "observation_id": "observation-owner",
                    "summary": "The existing implementation owner remains sufficient.",
                    "valence": "productive",
                    "event_ids": [event_ids[1]],
                },
            ],
            "lessons": [
                {
                    "lesson_id": "lesson-current-outcome",
                    "statement": "Terminal evidence must retain current installed behavior.",
                    "observation_ids": ["observation-gap"],
                    "supporting_case_ids": [event_ids[0]],
                    "report_hypothesis_ids": hypotheses[:1],
                    "counterexample_case_ids": [event_ids[1]],
                    "counterexample_posture": "observed",
                    "counterexample_search": "Inspected the existing bounded owner path.",
                    "goals_advanced": [],
                    "goals_threatened": ["current operator-visible outcome"],
                    "causal_hypothesis": "The final evidence stopped at process records.",
                    "confidence": "medium",
                    "applicability": "Consequential terminal Factory evidence.",
                    "unresolved_questions": ["How broadly does the pattern recur?"],
                },
                {
                    "lesson_id": "lesson-existing-owner",
                    "statement": "A bounded skill-owner update can retain the missing evidence.",
                    "observation_ids": ["observation-owner"],
                    "supporting_case_ids": [event_ids[1]],
                    "report_hypothesis_ids": hypotheses[:1],
                    "counterexample_case_ids": [event_ids[0]],
                    "counterexample_posture": "observed",
                    "counterexample_search": "Compared the observed evidence gap.",
                    "goals_advanced": ["current operator-visible outcome"],
                    "goals_threatened": [],
                    "causal_hypothesis": "The existing owner can add the narrow guidance.",
                    "confidence": "medium",
                    "applicability": "The bounded integrated dogfood target.",
                    "unresolved_questions": ["Does the candidate preserve mapped behavior?"],
                },
            ],
            "meta_patterns": [
                {
                    "meta_pattern_id": "meta-current-outcome",
                    "statement": "Process evidence and current installed behavior remain distinct.",
                    "lesson_ids": ["lesson-current-outcome", "lesson-existing-owner"],
                    "supporting_case_ids": event_ids,
                    "counterexample_lesson_ids": ["lesson-existing-owner"],
                    "applicability": "Terminal Software Factory capability claims.",
                    "uncertainty": "One bounded run does not justify a general detector.",
                }
            ],
            "candidates": candidates,
            "selection": {
                "candidate_id": "candidate-existing-skill-owner",
                "compared_candidate_ids": [
                    "candidate-lower-power-shortcut",
                    "candidate-generalized-detector",
                ],
                "rationale": (
                    "The existing skill owner is sufficient; a tracker-only shortcut "
                    "underreaches and a generalized detector overreaches."
                ),
                "dimensions_considered": list(factory_evolution.SELECTION_DIMENSIONS),
            },
            "experiment": {
                "experiment_id": "experiment-installed-outcome-guidance",
                "candidate_id": "candidate-existing-skill-owner",
                "proposer_id": "base-reviewer-1234",
                "implementer_id": "implement-tracker-blocks",
                "evaluator_id": supervision_log.ADAPTIVE_EVALUATOR_ID,
                "baseline_revision": self.base_revision,
                "candidate_revision": "f" * 40,
                "positive_case_ids": ["case-current-outcome"],
                "exception_case_ids": ["case-lower-power", "case-generalized-layer"],
                "expected_effects": [
                    "Retain the installed outcome without adding another owner."
                ],
                "resource_bounds": ["Two changed files and one paired comparison."],
                "rollback_condition": "Keep the incumbent if the guidance regresses proof.",
                "success_measures": [
                    "The candidate proof observes the installed-outcome guidance.",
                    "The incumbent proof does not observe that guidance.",
                ],
                "regression_measures": ["No new owner, detector, or tracker rewrite."],
                "evidence_capture": "Retain revision-bound candidate and baseline outputs.",
                "stop_condition": "Stop after one exact independent disposition.",
                "comparison_mode": "improvement",
                "minimum_expected_delta": "Candidate passes while baseline fails.",
                "non_inferiority_justification": "",
            },
        }

    def finalize(self, evolution_id: str, event_ids: list[str]) -> dict[str, object]:
        packet_path = (
            self.directory
            / "learning"
            / "factory-evolution"
            / evolution_id
            / "learning-packet.json"
        )
        packet = supervision_log.read_json(packet_path)
        source = self.root / f"review-{evolution_id}.json"
        source.write_bytes(canonical(self.review_submission(packet, event_ids)) + b"\n")
        return self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "finalize",
            "--evolution-id",
            evolution_id,
            "--review-json",
            str(source),
        )

    def create_candidate(
        self, evolution_id: str, owner_record: Mapping[str, Any]
    ) -> tuple[str, dict[str, str]]:
        branch = f"candidate-{evolution_id[-12:]}"
        self.git("switch", "-q", "-c", branch, self.base_revision)
        skill = self.repository / "implement-tracker-blocks" / "SKILL.md"
        with skill.open("a", encoding="utf-8") as handle:
            handle.write(
                "\nRetain one exact installed-outcome root before terminal acceptance.\n"
            )
        test_path = Path(
            "implement-tracker-blocks/scripts/"
            "test_capability_255083e6fcd14f5d07bc.py"
        )
        test = self.repository / test_path
        with test.open("a", encoding="utf-8") as handle:
            handle.write("\n# Candidate-owned focused proof.\n")
        self.git("add", "implement-tracker-blocks/SKILL.md", test_path.as_posix())
        message = (
            f"Build isolated {evolution_id} candidate\n\n"
            f"Software-Factory-Handoff-Record: {owner_record['record_id']}\n"
            "Software-Factory-Handoff-Root: "
            f"{owner_record['orchestration_root']}\n"
            "Software-Factory-Handoff-Record-SHA256: "
            f"{owner_record['record_sha256']}"
        )
        revision = _commit(self.repository, message, self.clock())
        self.git("switch", "-q", "main")
        capability = "bounded owner execution"
        capability_id = "capability-" + hashlib.sha256(
            capability.encode("utf-8")
        ).hexdigest()[:20]
        return revision, {capability_id: test_path.as_posix()}

    def acknowledge(
        self,
        evolution_id: str,
        owner_record: Mapping[str, Any],
        candidate_revision: str,
        proof_paths: Mapping[str, str],
    ) -> dict[str, object]:
        handoff = owner_record["payload"]
        value = {
            "schema_version": 1,
            "kind": supervision_log.FACTORY_EVOLUTION_OWNER_ACK_INPUT_KIND,
            "owner_handoff_record_id": owner_record["record_id"],
            "owner_handoff_orchestration_root": owner_record["orchestration_root"],
            "owner_handoff_record_sha256": owner_record["record_sha256"],
            "handoff_root": handoff["handoff_root"],
            "target_revision": handoff["target_revision"],
            "candidate_revision": candidate_revision,
            "protected_capability_test_paths": dict(proof_paths),
        }
        source = self.root / f"owner-ack-{evolution_id}.json"
        source.write_bytes(canonical(value) + b"\n")
        return self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "acknowledge",
            "--evolution-id",
            evolution_id,
            "--owner-ack-json",
            str(source),
        )

    def sign_evaluation(self, value: Mapping[str, Any]) -> dict[str, object]:
        result = dict(value)
        result["evaluation_signature_base64"] = ""
        content = self.root / "evaluation-to-sign.json"
        signature = self.root / "evaluation.sig"
        content.write_bytes(
            canonical(
                {
                    key: item
                    for key, item in result.items()
                    if key != "evaluation_signature_base64"
                }
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.evaluator_private),
                "-keyform",
                "DER",
                "-rawin",
                "-in",
                str(content),
                "-out",
                str(signature),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result["evaluation_signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode("ascii")
        return result

    def evaluation_submission(
        self, handoff: Mapping[str, Any], disposition: str
    ) -> dict[str, object]:
        case_ids = sorted(
            set(handoff["positive_case_ids"] + handoff["exception_case_ids"])
        )

        def results(
            *, revision: str, source_root: str, outcome: str, label: str
        ) -> list[dict[str, object]]:
            values = []
            for case_id in case_ids:
                regressions = (
                    ["The candidate did not retain the required broader outcome."]
                    if disposition == "reject" and label == "Candidate"
                    else []
                )
                material = {
                    "case_id": case_id,
                    "outcome": outcome,
                    "observed_effect": f"{label} {outcome} observed for {case_id}.",
                    "resource_cost": "The one mapped comparison was reused.",
                    "regressions": regressions,
                    "condition_revision": revision,
                    "source_evidence_root": source_root,
                }
                values.append(
                    {
                        **material,
                        "evidence_root": supervision_log.digest(
                            {
                                "evaluation_handoff_root": handoff[
                                    "evaluation_handoff_root"
                                ],
                                "result": material,
                            }
                        ),
                    }
                )
            return values

        value = {
            "schema_version": 1,
            "kind": factory_evolution.ORCHESTRATED_EVALUATION_SUBMISSION_KIND,
            "evaluation_handoff_root": handoff["evaluation_handoff_root"],
            "evaluator_id": handoff["evaluator_id"],
            "evaluator_authority_key_sha256": self.evaluator_public_sha,
            "evaluation_signature_base64": "",
            "baseline_results": results(
                revision=str(handoff["baseline_revision"]),
                source_root=str(handoff["baseline_validation_root"]),
                outcome="fail",
                label="Incumbent",
            ),
            "candidate_results": results(
                revision=str(handoff["candidate_revision"]),
                source_root=str(handoff["candidate_validation_root"]),
                outcome="pass" if disposition == "promote" else "fail",
                label="Candidate",
            ),
            "contrary_evidence": [
                "The lower-power shortcut and generalized layer were inspected."
            ],
            "regression_findings": (
                []
                if disposition == "promote"
                else ["The losing candidate underreached the required outcome."]
            ),
            "disposition": disposition,
            "rationale": (
                "The candidate alone passed the current installed-outcome proof."
                if disposition == "promote"
                else "The retained evidence supports keeping the incumbent."
            ),
        }
        return self.sign_evaluation(value)

    def append_completion(
        self, evolution_id: str, observed_effect_root: str
    ) -> str:
        if self.release_owner is None:
            raise DogfoodError("temporary release owner is unavailable")
        policy = supervision_log.read_json(self.directory / "policy.json")
        all_events = supervision_log.events(self.directory / "events.jsonl")
        state = supervision_log.factory_evolution_cycle_state(
            self.directory, policy, all_events, evolution_id=evolution_id
        )
        fingerprint = supervision_log.factory_evolution_outcome_state_fingerprint(
            state
        )
        mission = supervision_log.bound_mission(policy)
        if mission is None:
            raise DogfoodError("temporary mission is unavailable")
        record_id = f"EVT-{len(all_events) + 1:06d}"
        record: dict[str, object] = {
            "schema_version": 1,
            "record_id": record_id,
            "timestamp": self.clock(),
            "target_thread_id": self.target_thread,
            "kind": "check",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "state_fingerprint": fingerprint,
            "status": "verified",
            "severity": "info",
            "category": supervision_log.OUTCOME_COMPLETION_CATEGORY,
            "active_block": "Block 17",
            "checkpoint": "Factory current observable outcome",
            "summary": "The disposable installed candidate produced the current effect.",
            "evidence": [f"factory-evolution:{evolution_id}"],
            "mission_root": mission["mission_root"],
            "policy_sha256": policy["policy_sha256"],
            "capability_reconciliation_reviewer_id": policy["runtime"][
                "base_reviewer_thread_id"
            ],
            "capability_reconciliation_implementation_owner_id": state[
                "acknowledgment_record"
            ]["payload"]["owner_id"],
            "capability_reconciliation_revision": state["evaluation"][
                "candidate_revision"
            ],
            "capability_reconciliation_posture": "verified",
            "capability_reconciliation_gap_count": 0,
        }
        for field in supervision_log.OUTCOME_COMPLETION_HASH_FIELDS:
            record[field] = (
                observed_effect_root
                if field == "effect_reconciliation_sha256"
                else supervision_log.digest(
                    {"field": field, "evolution_id": evolution_id}
                )
            )
        supervision_log.append_raw(self.directory / "events.jsonl", record)
        return record_id

    def installed_effect(self) -> dict[str, object]:
        if self.release_owner is None:
            raise DogfoodError("temporary release owner is unavailable")
        installed = (self.release_owner.root / "current").resolve(strict=True)
        skill = installed / "implement-tracker-blocks" / "SKILL.md"
        proof = (
            installed
            / "implement-tracker-blocks"
            / "scripts"
            / "test_capability_255083e6fcd14f5d07bc.py"
        )
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", proof.name],
            cwd=proof.parent,
            text=True,
            capture_output=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        result = {
            "installed_release_id": self.release_owner._status()["active_release_id"],
            "installed_source_revision": self.release_owner.active,
            "skill_sha256": hashlib.sha256(skill.read_bytes()).hexdigest(),
            "proof_exit_code": completed.returncode,
            "proof_stdout_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
            "proof_stderr_sha256": hashlib.sha256(
                completed.stderr.encode("utf-8")
            ).hexdigest(),
            "guidance_observed": (
                "Retain one exact installed-outcome root before terminal acceptance."
                in skill.read_text(encoding="utf-8")
            ),
        }
        result["observed_effect_root"] = digest(result)
        if completed.returncode != 0 or result["guidance_observed"] is not True:
            raise DogfoodError("temporary installed behavior differs")
        return result

    def run_cycle(
        self,
        cycle: str,
        *,
        disposition: str,
        adopt: bool,
    ) -> tuple[dict[str, object], Path]:
        event_ids, report = self.append_signal(cycle)
        admitted = self.admit(report)
        if admitted.get("disposition") != "admitted" or not admitted.get("eligible"):
            raise DogfoodError(f"{cycle} signal was not admitted")
        evolution_id = str(admitted["evolution_id"])
        routed = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            evolution_id,
        )
        if routed["action"]["stage"] != "review-required":
            raise DogfoodError("review handoff stage differs")
        finalized = self.finalize(evolution_id, event_ids)
        handed = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            evolution_id,
        )
        owner_record = handed["record"]
        candidate_revision, proof_paths = self.create_candidate(
            evolution_id, owner_record
        )
        acknowledgment = self.acknowledge(
            evolution_id, owner_record, candidate_revision, proof_paths
        )
        comparison = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "orchestrate",
            "--evolution-id",
            evolution_id,
        )
        handoff = comparison["record"]["payload"]
        evaluation_source = self.root / f"evaluation-{evolution_id}.json"
        evaluation_source.write_bytes(
            canonical(self.evaluation_submission(handoff, disposition)) + b"\n"
        )
        evaluated = self.command(
            "factory-evolution",
            "--target-thread",
            self.target_thread,
            "--action",
            "evaluate",
            "--evolution-id",
            evolution_id,
            "--evaluation-json",
            str(evaluation_source),
        )
        before_activation = (
            self.release_owner.activation_count if self.release_owner else 0
        )
        effect: dict[str, object] | None = None
        if adopt:
            self.release_owner = TemporaryReleaseOwner(
                self.root / "release-owner",
                self.repository,
                self.base_revision,
                candidate_revision,
            )
            review_path = self.root / "release-review.json"
            review_path.write_text("{}\n", encoding="utf-8")
            permit_path = self.root / "quiescent-evidence.json"
            permit_path.write_text(
                '{"operator_id":"temporary-release-operator-1234"}\n',
                encoding="utf-8",
            )
            with mock.patch.object(
                supervision_log,
                "factory_release_module",
                return_value=self.release_owner,
            ):
                adoption = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "orchestrate",
                    "--evolution-id",
                    evolution_id,
                    "--release-review-evidence",
                    str(review_path),
                    "--quiescent-evidence",
                    str(permit_path),
                )
                effect = self.installed_effect()
                completion_id = self.append_completion(
                    evolution_id, str(effect["observed_effect_root"])
                )
                outcome = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "outcome",
                    "--evolution-id",
                    evolution_id,
                    "--outcome-completion-record",
                    completion_id,
                )
                outcome_retry = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "outcome",
                    "--evolution-id",
                    evolution_id,
                    "--outcome-completion-record",
                    completion_id,
                )
        else:
            if self.release_owner is None:
                raise DogfoodError("winner must establish the temporary release owner first")
            with mock.patch.object(
                supervision_log,
                "factory_release_module",
                return_value=self.release_owner,
            ):
                adoption = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "orchestrate",
                    "--evolution-id",
                    evolution_id,
                )
                outcome = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "outcome",
                    "--evolution-id",
                    evolution_id,
                )
                outcome_retry = self.command(
                    "factory-evolution",
                    "--target-thread",
                    self.target_thread,
                    "--action",
                    "outcome",
                    "--evolution-id",
                    evolution_id,
                )
        with mock.patch.object(
            supervision_log,
            "factory_release_module",
            return_value=self.release_owner,
        ):
            status = self.command(
                "factory-evolution",
                "--target-thread",
                self.target_thread,
                "--action",
                "status",
                "--evolution-id",
                evolution_id,
            )
        evolution_directory = (
            self.directory / "learning" / "factory-evolution" / evolution_id
        )
        artifacts = sorted(
            path.name for path in evolution_directory.iterdir() if path.is_file()
        )
        result: dict[str, object] = {
            "cycle": cycle,
            "evolution_id": evolution_id,
            "admission_result_root": admitted["result_root"],
            "packet_root": admitted["packet_root"],
            "review_root": finalized["review_root"],
            "review_handoff_root": routed["record"]["payload"][
                "review_handoff_root"
            ],
            "owner_handoff_root": owner_record["payload"]["handoff_root"],
            "normal_owner": owner_record["payload"]["normal_owner"],
            "candidate_revision": candidate_revision,
            "baseline_revision": handoff["baseline_revision"],
            "candidate_currentness_root": acknowledgment["record"]["payload"][
                "currentness_root"
            ],
            "candidate_validation_root": acknowledgment["record"]["payload"][
                "validation_root"
            ],
            "baseline_validation_root": handoff["baseline_validation_root"],
            "evaluation_handoff_root": handoff["evaluation_handoff_root"],
            "evaluation_root": evaluated["record"]["payload"]["evaluation_root"],
            "evaluation_disposition": disposition,
            "adoption_stage": adoption["action"]["stage"],
            "outcome_posture": outcome["action"]["outcome_posture"],
            "outcome_root": outcome["action"]["outcome_root"],
            "outcome_retry_duplicate": outcome_retry["duplicate"],
            "candidate_authoritative": outcome["action"]["candidate_authoritative"],
            "incumbent_authoritative": outcome["action"]["incumbent_authoritative"],
            "human_request_count": adoption["action"].get("human_request_count", 0),
            "release_activation_delta": (
                self.release_owner.activation_count - before_activation
                if self.release_owner
                else 0
            ),
            "installed_effect": effect,
            "selected_path": "bounded-existing-skill-owner",
            "rejected_paths": ["lower-power-shortcut", "generalized-detector"],
            "structural_contract_changed": False,
            "tracker_authoring_invoked": False,
            "artifact_names": artifacts,
            "operator_status": status,
        }
        result["cycle_root"] = digest(result)
        return result, report


def live_skill_results(skills_root: Path) -> dict[str, object]:
    validator = (
        skills_root / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
    )
    if not validator.is_file():
        raise DogfoodError("installed skill validator is unavailable")
    results = []
    for skill_id in factory_evolution.FACTORY_SKILL_IDS:
        discovery = skills_root / skill_id
        if not discovery.is_symlink():
            raise DogfoodError(f"live skill entrypoint is not a symlink: {skill_id}")
        source = discovery.resolve(strict=True)
        skill_file = source / "SKILL.md"
        completed = subprocess.run(
            ["/usr/bin/python3", str(validator), str(discovery)],
            text=True,
            capture_output=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        if completed.returncode != 0:
            raise DogfoodError(f"live skill invocation failed: {skill_id}")
        tree_root, file_count = _tree_manifest(source)
        results.append(
            {
                "skill_id": skill_id,
                "discovery_target": os.readlink(discovery),
                "resolved_release": source.parent.name,
                "skill_sha256": hashlib.sha256(skill_file.read_bytes()).hexdigest(),
                "tree_root": tree_root,
                "file_count": file_count,
                "validator_exit_code": completed.returncode,
                "validator_stdout_sha256": hashlib.sha256(
                    completed.stdout.encode("utf-8")
                ).hexdigest(),
                "instruction_invocation": "current-stable-entrypoint-validated",
            }
        )
    tracker_verifier = (
        skills_root
        / "author-implementation-trackers"
        / "scripts"
        / "verify_tracker.py"
    )
    completed = subprocess.run(
        [
            "/usr/bin/python3",
            str(tracker_verifier),
            "--profile",
            "full",
            "--json",
            str(TRACKER_PATH),
        ],
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    if completed.returncode != 0:
        raise DogfoodError("live author skill rejected the current tracker")
    result: dict[str, object] = {
        "skills": results,
        "shared_release": (
            results[0]["resolved_release"]
            if len({item["resolved_release"] for item in results}) == 1
            else None
        ),
        "tracker_verifier_exit_code": completed.returncode,
        "tracker_verifier_output_root": hashlib.sha256(
            completed.stdout.encode("utf-8")
        ).hexdigest(),
    }
    result["live_skill_root"] = digest(result)
    return result


def within_run_compatibility() -> dict[str, object]:
    script = (
        REPOSITORY_ROOT
        / "implement-tracker-blocks"
        / "scripts"
        / "adaptive_protocol_dogfood.py"
    )
    completed = subprocess.run(
        ["/usr/bin/python3", str(script)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C"},
    )
    if completed.returncode != 0:
        raise DogfoodError("maintained within-run dogfood failed")
    value = json.loads(completed.stdout)
    authority = [
        {
            "case_id": item["case_id"],
            "mode": item["adaptive_decision_mode"],
            "posture": item["application_posture"],
            "authorized": item["application_authorized"],
            "human_request_count": item["human_request_count"],
            "blocked_subjects": item["blocked_subjects"],
        }
        for item in value["authority_cases"]
    ]
    result = {
        "source_revision": value["source_revision"],
        "result_root": value["result_root"],
        "authority_cases": authority,
        "authority_modes": sorted({item["mode"] for item in authority}),
        "human_request_count": sum(item["human_request_count"] for item in authority),
        "temporary_target_effects_performed": value[
            "temporary_target_effects_performed"
        ],
        "external_effects_performed": value["external_effects_performed"],
        "release_mutated": value["release_mutated"],
        "policy_mutated": value["policy_mutated"],
        "mission_mutated": value["mission_mutated"],
        "lifecycle_mutated": value["lifecycle_mutated"],
    }
    result["compatibility_root"] = digest(result)
    return result


@contextlib.contextmanager
def isolated_workspace(path: Path) -> Iterator[None]:
    resolved = path.resolve()
    if resolved == Path("/") or len(resolved.parts) < 3:
        raise DogfoodError("disposable dogfood workspace is too broad")
    lock_path = resolved.with_name(resolved.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    def remove_owned_workspace() -> None:
        if not resolved.exists():
            return
        for item in sorted(
            (entry for entry in resolved.rglob("*") if entry.is_dir()),
            key=lambda entry: len(entry.parts),
            reverse=True,
        ):
            item.chmod(0o700)
        resolved.chmod(0o700)
        shutil.rmtree(resolved)

    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        remove_owned_workspace()
        resolved.mkdir(mode=0o700)
        try:
            yield
        finally:
            remove_owned_workspace()


def run_dogfood(*, workspace: Path, live_skills: Path) -> dict[str, object]:
    revision = source_revision()
    clock = DeterministicClock()
    deterministic_bytes = DeterministicBytes()
    with isolated_workspace(workspace):
        dogfood = DogfoodWorkspace(workspace.resolve(), clock)
        with (
            mock.patch.object(supervision_log, "utc_now", side_effect=clock),
            mock.patch.object(
                supervision_log.secrets,
                "token_bytes",
                side_effect=deterministic_bytes,
            ),
        ):
            dogfood.setup(revision)
            with (
                mock.patch.object(
                    supervision_log,
                    "ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH",
                    dogfood.evaluator_public,
                ),
                mock.patch.object(
                    supervision_log,
                    "ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256",
                    dogfood.evaluator_public_sha,
                ),
            ):
                winner, winner_report = dogfood.run_cycle(
                    "eligible-winner", disposition="promote", adopt=True
                )
                before_noop_events = len(
                    supervision_log.events(dogfood.directory / "events.jsonl")
                )
                before_noop_inventory = sorted(
                    path.name
                    for path in (
                        dogfood.directory / "learning" / "factory-evolution"
                    ).iterdir()
                    if path.is_dir()
                )
                with mock.patch.object(
                    supervision_log,
                    "factory_release_module",
                    return_value=dogfood.release_owner,
                ):
                    no_op = dogfood.admit(winner_report)
                after_noop_events = len(
                    supervision_log.events(dogfood.directory / "events.jsonl")
                )
                after_noop_inventory = sorted(
                    path.name
                    for path in (
                        dogfood.directory / "learning" / "factory-evolution"
                    ).iterdir()
                    if path.is_dir()
                )
                no_op_result = {
                    "disposition": no_op["disposition"],
                    "eligible": no_op["eligible"],
                    "admission_authorized": no_op["admission_authorized"],
                    "reused": no_op["reused"],
                    "packet_builds": no_op["packet_builds"],
                    "model_calls": 0,
                    "reviewer_calls": 0,
                    "human_request_count": 0,
                    "event_delta": after_noop_events - before_noop_events,
                    "artifact_directory_delta": len(after_noop_inventory)
                    - len(before_noop_inventory),
                    "inventory_unchanged": before_noop_inventory
                    == after_noop_inventory,
                    "candidate_created": False,
                    "authoring_handoff_created": False,
                }
                no_op_result["no_op_root"] = digest(no_op_result)
                with mock.patch.object(
                    supervision_log,
                    "factory_release_module",
                    return_value=dogfood.release_owner,
                ):
                    losing, _losing_report = dogfood.run_cycle(
                        "losing-candidate", disposition="reject", adopt=False
                    )
                events = supervision_log.events(dogfood.directory / "events.jsonl")
                policy = supervision_log.read_json(dogfood.directory / "policy.json")
                with mock.patch.object(
                    supervision_log,
                    "factory_release_module",
                    return_value=dogfood.release_owner,
                ):
                    outcome_projection = supervision_log.factory_evolution_outcome_projection(
                        events, policy=policy
                    )
                    overall_status = dogfood.command(
                        "status", "--target-thread", dogfood.target_thread
                    )
                event_counts = Counter(str(item.get("kind")) for item in events)
                report_projection = {
                    "terminal_cycle_count": outcome_projection[
                        "terminal_cycle_count"
                    ],
                    "current_outcomes": [
                        {
                            "evolution_id": item["evolution_id"],
                            "outcome_posture": item["outcome_posture"],
                            "next_action": item["next_action"],
                            "candidate_authoritative": item["outcome_posture"]
                            == "adopted-effective",
                            "incumbent_authoritative": item["outcome_posture"]
                            != "adopted-effective",
                        }
                        for item in outcome_projection["current_outcomes"]
                    ],
                    "human_summary": [
                        "One bounded candidate was adopted and observed in the disposable release owner.",
                        "One independently rejected candidate retained the incumbent and history.",
                        "The identical consumed checkpoint created no new cycle or handoff.",
                    ],
                }
                report_projection["report_projection_root"] = digest(
                    report_projection
                )
                operator_projection = {
                    "factory_admission_state": overall_status[
                        "factory_evolution_admission"
                    ]["state"],
                    "factory_active_cycle_count": len(
                        overall_status["factory_evolution_admission"][
                            "active_cycles"
                        ]
                    ),
                    "event_kind_counts": dict(sorted(event_counts.items())),
                    "target_head": dogfood.git("rev-parse", "HEAD"),
                    "target_status": dogfood.git("status", "--short"),
                    "release_activation_count": dogfood.release_owner.activation_count,
                    "release_rollback_count": dogfood.release_owner.rollback_count,
                    "active_release_id": dogfood.release_owner._status()[
                        "active_release_id"
                    ],
                }
                operator_projection["operator_projection_root"] = digest(
                    operator_projection
                )
        live = live_skill_results(live_skills.resolve(strict=True))
        compatibility = within_run_compatibility()
    result: dict[str, object] = {
        "schema_version": 1,
        "kind": "software-factory-integrated-dogfood-result",
        "source_revision": revision,
        "eligible_adopted": winner,
        "unchanged_no_op": no_op_result,
        "losing_candidate": losing,
        "within_run_compatibility": compatibility,
        "live_skill_invocation": live,
        "operator_projection": operator_projection,
        "human_report_projection": report_projection,
        "external_effects_performed": False,
        "live_release_mutated": False,
        "live_policy_mutated": False,
        "live_mission_mutated": False,
        "live_lifecycle_mutated": False,
        "gmail_action_performed": False,
        "deployment_performed": False,
        "temporary_target_effects_performed": True,
        "temporary_release_effects_performed": True,
    }
    if (
        winner["outcome_posture"] != "adopted-effective"
        or winner["candidate_authoritative"] is not True
        or winner["human_request_count"] != 0
        or no_op_result["disposition"]
        != "already-consumed-canonical-coverage"
        or no_op_result["event_delta"] != 0
        or no_op_result["artifact_directory_delta"] != 0
        or losing["outcome_posture"] != "candidate-retired"
        or losing["incumbent_authoritative"] is not True
        or losing["release_activation_delta"] != 0
        or compatibility["authority_modes"]
        != ["fixed", "full-autonomous", "recommend", "reviewed-autonomous"]
        or compatibility["human_request_count"] != 0
        or operator_projection["target_head"] != winner["baseline_revision"]
        or operator_projection["target_status"] != ""
    ):
        raise DogfoodError("integrated dogfood acceptance projection differs")
    result["result_root"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded temporary-target and temporary-release integrated "
            "Factory-evolution dogfood."
        )
    )
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--live-skills-root", type=Path, default=DEFAULT_LIVE_SKILLS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = run_dogfood(
        workspace=args.workspace,
        live_skills=args.live_skills_root,
    )
    payload = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
    ) + "\n"
    if args.output is not None:
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
