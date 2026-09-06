#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest import mock


SUPPORT_PATH = Path(__file__).with_name("test_adaptive_decision_policy.py")
SUPPORT_SPEC = importlib.util.spec_from_file_location(
    "program_revision_adaptive_support", SUPPORT_PATH
)
assert SUPPORT_SPEC is not None and SUPPORT_SPEC.loader is not None
support = importlib.util.module_from_spec(SUPPORT_SPEC)
SUPPORT_SPEC.loader.exec_module(support)
supervision_log = support.supervision_log
program_revision = supervision_log.program_revision_module()
SOURCE_REPOSITORY_ROOT = supervision_log.software_factory_source_repository_root


class ProgramRevisionControlTests(unittest.TestCase):
    local_reviews = False
    local_review_stages = {"profile", "adaptive", "program"}

    def setUp(self) -> None:
        self.fixture = support.AdaptiveDecisionPolicyTests(
            methodName="test_modes_preserve_application_and_review_boundaries"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        if self.local_reviews:
            self.fixture.root = self.fixture.root / "supervision"
            self.fixture.root.mkdir()
        self.write_tracker(
            self.fixture.tracker_path,
            [
                ("Accepted 0", [], "completed"),
                ("Accepted 1", [0], "completed"),
                ("Accepted 2", [1], "completed"),
                ("Accepted 3", [2], "completed"),
                ("Accepted 4", [3], "completed"),
                ("Accepted 5", [4], "completed"),
                ("Accepted 6", [5], "completed"),
                ("Structural revision", [6], "in-progress"),
            ],
        )
        (
            self.software_factory_source_root,
            self.software_factory_source_revision,
            software_factory_source_sha256,
        ) = self.create_profile_source_repository(
            "maintained-software-factory-source",
            "# Maintained tracker-authoring supervision policy\n\n"
            "The author writes; the watcher routes; distinct semantic and "
            "adjudication roles remain read-only.\n",
        )
        source_root_patch = mock.patch.object(
            supervision_log,
            "software_factory_source_repository_root",
            return_value=self.software_factory_source_root,
        )
        source_root_patch.start()
        self.addCleanup(source_root_patch.stop)
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "add",
                "tracker.md",
            ],
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit",
                "-q",
                "-m",
                "full program revision fixture",
            ],
            check=True,
        )
        self.refresh_fixture_revision()
        self.policy = self.fixture.init()
        directory = self.fixture.root / self.fixture.target
        self.policy["permissions"]["repository_write"] = True
        supervision_log.write_policy_version(
            directory,
            self.policy,
            kind="test-repository-write-authority",
            reason="Exercise the already authorized target repository owner.",
            evidence_values=["test-direct-repository-write-authority"],
        )
        if self.local_reviews:
            self.install_native_review_fixture()
            for accessor in ("trusted_adaptive_reviewer_key", "trusted_adaptive_reviewer_private_key"):
                if accessor == "trusted_adaptive_reviewer_key" and self.local_review_stages != {"profile", "adaptive", "program"}:
                    continue  # Mixed fixtures retain their existing test public key.
                guard = mock.patch.object(supervision_log, accessor, side_effect=AssertionError("local tracker path touched signer"))
                guard.start()
                self.addCleanup(guard.stop)
            if "adaptive" in self.local_review_stages:
                self.fixture.sign_outer_review = lambda value: self.local_review(value, "adaptive")
        self.profile_review = self.signed_profile_review(
            source_revision=self.software_factory_source_revision,
            source_root=software_factory_source_sha256,
        )
        self.profile_review_path = self.fixture.write_json(
            "tracker-authoring-profile-review.json", self.profile_review
        )
        self.policy = self.fixture.adjust(
            "--program-revision-authoring-thread",
            self.fixture.target,
            "--program-revision-authoring-profile-review",
            str(self.profile_review_path),
        )
        if not self.local_reviews:
            self.policy = self.fixture.adjust("--adaptive-target-class", "software-factory")
        self.proposal = self.fixture.root / "proposal.md"
        self.write_tracker(
            self.proposal,
            [
                ("Accepted 0", [], "completed"),
                ("Accepted 1", [0], "completed"),
                ("Accepted 2", [1], "completed"),
                ("Accepted 3", [2], "completed"),
                ("Accepted 4", [3], "completed"),
                ("Accepted 5", [4], "completed"),
                ("Accepted 6", [5], "completed"),
                ("New structural prerequisite", [6], "in-progress"),
                ("Revised structural application", [7], "not-started"),
            ],
        )
        self.install_program_control(
            {**{str(number): [number] for number in range(7)}, "7": [7, 8]},
            affected=[7, 8],
            resume=7,
        )
        self.decision_evidence = self.structural_decision_evidence(
            target_class="target-repository" if self.local_reviews else "software-factory"
        )
        pending = self.fixture.run_gate(
            self.fixture.gate_args(self.decision_evidence)
        )["record"]
        adaptive_review = self.fixture.run_review(pending)["record"]
        self.mechanical_route = pending
        self.semantic_review = adaptive_review
        self.source = self.fixture.run_gate(
            self.fixture.gate_args(
                self.decision_evidence,
                review_record=str(adaptive_review["record_id"]),
            )
        )["record"]
        self.packet = self.build_packet()
        self.packet_path = self.fixture.write_json("program-revision.json", self.packet)

    def install_native_review_fixture(self):
        import gcp_supervision
        self.native_rows = {}
        self.native_config = self.fixture.root.parent / "config.json"
        self.native_cli = str(Path(gcp_supervision.__file__).resolve())
        self.native_config.write_text(json.dumps({
            "target_thread_id": self.fixture.target, "state_root": str(self.fixture.root.parent),
            "supervision_root": str(self.fixture.root),
            "socket_path": "/test-native-socket", "native_cli": self.native_cli,
            "roles": {role: {"thread_id": self.policy["runtime"][role + "_thread_id"]}
                      for role in ("base_reviewer", "reviewer")},
        }))
        with closing(sqlite3.connect(self.fixture.root.parent / "runtime.sqlite3", isolation_level=None)) as db:
            db.execute("CREATE TABLE deliveries (id TEXT PRIMARY KEY, recipient TEXT, message TEXT, message_sha256 TEXT, source TEXT, state TEXT, turn_id TEXT)")
        rows = self.native_rows

        class Client:
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def compact(self, task): return {"id": task}
            def call(self, method, params):
                if method != "thread/items/list": raise AssertionError(method)
                return copy.deepcopy(rows.get((params["threadId"], params["turnId"]), {"data": [], "nextCursor": None}))

        for patch in (
            mock.patch.object(gcp_supervision, "CodexClient", Client),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def local_review(self, value, stage, *, reviewer=None):
        value = copy.deepcopy(value)
        directory = self.fixture.root / self.fixture.target
        policy = supervision_log.read_json(directory / "policy.json")
        mission = supervision_log.bound_mission(policy)
        value.update(kind=supervision_log.LOCAL_TRACKER_REVIEW_KINDS[stage],
                     authority_key_sha256=None, signature_base64=None,
                     canonical_review={"record_id": "pending", "record_sha256": "0" * 64,
                                       "native_delivery_id": "pending", "native_turn_id": "pending"})
        value["reviewer_id"] = reviewer or policy["runtime"][
            "base_reviewer_thread_id" if stage == "program" else "reviewer_thread_id"]
        if stage == "profile":
            value.update(profile_source_repository_root=str(self.software_factory_source_root),
                         policy_sha256=policy["policy_sha256"],
                         mission_root=mission["mission_root"], target_thread_id=self.fixture.target)
        value["review_root"] = supervision_log.digest(
            supervision_log.tracker_authoring_profile_review_root_material(value))
        proof = value["canonical_review"]
        proof.update(native_delivery_id="delivery-" + value["review_root"], native_turn_id="turn-" + value["review_root"])
        evidence = supervision_log.local_tracker_review_evidence(value, stage, mission["mission_root"])
        retained = supervision_log.events(directory / "events.jsonl")
        found = next((item for item in reversed(retained) if item.get("category") == f"local-tracker-{stage}-review"
                      and item.get("evidence") == evidence), None)
        if found is None:
            if not retained or retained[-1].get("policy_sha256") != policy["policy_sha256"]:
                supervision_log.append_raw(directory / "events.jsonl", {
                    "schema_version": 1, "record_id": f"EVT-{len(retained) + 1:06d}",
                    "timestamp": supervision_log.utc_now(), "target_thread_id": self.fixture.target,
                    "kind": "check", "policy_sha256": policy["policy_sha256"], "evidence": ["review-request"],
                })
                retained = supervision_log.events(directory / "events.jsonl")
            source = retained[-1]
            is_base = value["reviewer_id"] == policy["runtime"]["base_reviewer_thread_id"]
            record_args = ["record", "--target-thread", self.fixture.target,
                "--kind", "checkpoint-review" if is_base else "meta-review",
                "--category", f"local-tracker-{stage}-review", "--model", "gpt-5.6-sol",
                "--reasoning", "xhigh" if is_base else "max", "--resolution-owner", "supervisor",
                "--user-action-required", "no", "--summary", "Independent exact local tracker review",
                "--status", value.get("review_disposition") if stage == "adaptive" else value["disposition"]]
            for token in evidence:
                record_args.extend(["--evidence", token])
            record_output = io.StringIO()
            with redirect_stdout(record_output):
                supervision_log.cmd_record(supervision_log.parser().parse_args([
                    "--root", str(self.fixture.root), *record_args]))
            self.assertFalse(json.loads(record_output.getvalue())["duplicate"])
            found = supervision_log.events(directory / "events.jsonl")[-1]
            message = "\n".join([evidence[1], evidence[2], "policy-sha256:" + policy["policy_sha256"]])
            with closing(sqlite3.connect(self.fixture.root.parent / "runtime.sqlite3", isolation_level=None)) as db:
                db.execute("INSERT INTO deliveries VALUES (?,?,?,?,?,?,?)", (
                    proof["native_delivery_id"], value["reviewer_id"], message,
                    hashlib.sha256(message.encode()).hexdigest(), source["record_id"], "acknowledged", proof["native_turn_id"],
                ))
            argv = [sys.executable, self.native_cli, "--config", str(self.native_config), "helper", "--", *record_args]
            self.native_rows[(value["reviewer_id"], proof["native_turn_id"])] = {"nextCursor": None, "data": [
                {"turnId": proof["native_turn_id"], "item": {"type": "userMessage", "id": "user-item", "clientId": proof["native_delivery_id"],
                    "content": [{"type": "text", "text": f"[gcp-supervision-delivery:{proof['native_delivery_id']}]\n{message}"}]}},
                {"turnId": proof["native_turn_id"], "item": {"type": "commandExecution", "id": "exec-review-record", "source": "unifiedExecStartup",
                    "status": "completed", "exitCode": 0, "command": shlex.join(["/usr/bin/bash", "-lc", shlex.join(argv)]),
                    "aggregatedOutput": record_output.getvalue()}},
            ]}
        value["canonical_review"].update({field: found[field] for field in ("record_id", "record_sha256")})
        return value

    def create_profile_source_repository(
        self, name: str, profile_text: str
    ) -> tuple[Path, str, str]:
        repository = (self.fixture.root / name).resolve()
        repository.mkdir()
        subprocess.run(["/usr/bin/git", "init", "-q"], cwd=repository, check=True)
        subprocess.run(
            ["/usr/bin/git", "config", "user.email", "test@example.com"],
            cwd=repository,
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "config", "user.name", "Test"],
            cwd=repository,
            check=True,
        )
        profile = repository / supervision_log.TRACKER_AUTHORING_PROFILE_SOURCE_PATH
        profile.parent.mkdir(parents=True)
        profile.write_text(profile_text, encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/git",
                "add",
                supervision_log.TRACKER_AUTHORING_PROFILE_SOURCE_PATH,
            ],
            cwd=repository,
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "commit", "-q", "-m", "profile source"],
            cwd=repository,
            check=True,
        )
        revision = subprocess.run(
            ["/usr/bin/git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        return repository, revision, hashlib.sha256(profile.read_bytes()).hexdigest()

    def install_program_control(
        self,
        mapping: dict[str, list[int]],
        *,
        affected: list[int],
        resume: int,
        revision_id: str = "PROGRAM-REVISION-1234",
    ) -> None:
        text = self.proposal.read_text(encoding="utf-8")
        text = re.sub(
            r"\n## Active-program revision control\n.*?(?=\n## Block 0\b)",
            "",
            text,
            flags=re.S,
        )
        self.proposal.write_text(text, encoding="utf-8")
        previous = program_revision.tracker_snapshot(self.fixture.tracker_path)
        proposed = program_revision.tracker_snapshot(self.proposal)
        blocks = sorted(proposed["blocks"])
        block_text = ",".join(str(item) for item in blocks)
        affected_text = ",".join(str(item) for item in affected)
        control = f"""## Active-program revision control

- Terminal Block: `{max(blocks)}`
- Required order: `{block_text}`
- Prose-reference Blocks: `{block_text}`
- Source-map Blocks: `{block_text}`
- Verification-matrix Blocks: `{block_text}`
- Handoff Block: `{resume}`

### Program revision history

| Revision ID | Predecessor tracker SHA-256 | Current structure SHA-256 | Block map SHA-256 | Affected Blocks | Resume Block |
|---|---|---|---|---|---:|
| `{revision_id}` | `{previous['sha256']}` | `{proposed['structure_sha256']}` | `{program_revision.digest(mapping)}` | `{affected_text}` | `{resume}` |
"""
        self.proposal.write_text(
            text.replace("## Block 0", control + "\n## Block 0", 1),
            encoding="utf-8",
        )
        current_structure = program_revision.tracker_snapshot(
            self.proposal, require_full=False
        )["structure_sha256"]
        self.proposal.write_text(
            self.proposal.read_text(encoding="utf-8").replace(
                f"| `{revision_id}` | `{previous['sha256']}` | "
                f"`{proposed['structure_sha256']}` |",
                f"| `{revision_id}` | `{previous['sha256']}` | "
                f"`{current_structure}` |",
                1,
            ),
            encoding="utf-8",
        )

    def refresh_fixture_revision(self) -> None:
        self.fixture.target_revision = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "rev-parse",
                "HEAD",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        (
            _path,
            self.fixture.tracker_sha,
            self.fixture.tracker_structure_sha,
            self.fixture.tracker_blocks,
        ) = supervision_log.implementation_tracker_snapshot(
            str(self.fixture.tracker_path)
        )

    def signed_profile_review(
        self, *, source_revision: str, source_root: str
    ) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-tracker-authoring-profile-review",
            "record_id": "tracker-authoring-profile-review-1234",
            "profile_source_path": supervision_log.TRACKER_AUTHORING_PROFILE_SOURCE_PATH,
            "profile_source_revision": source_revision,
            "profile_source_root": source_root,
            "disposition": "accepted",
            "acceptance_scope": "profile-design-contract-only",
            "implementation_claim": "not-claimed",
            "finding_count": 0,
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "authority_key_sha256": self.fixture.public_key_sha,
            "observed_at": "2026-08-10T00:00:00+00:00",
            "review_root": "",
            "signature_base64": "",
        }
        if self.local_reviews and "profile" in self.local_review_stages:
            return self.local_review(value, "profile")
        value["review_root"] = supervision_log.digest(
            supervision_log.tracker_authoring_profile_review_root_material(value)
        )
        signed = dict(value)
        signed.pop("signature_base64")
        content = self.fixture.root / "tracker-authoring-profile-review-to-sign.json"
        signature = self.fixture.root / "tracker-authoring-profile-review.sig"
        content.write_bytes(supervision_log.canonical(signed))
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.fixture.private_key),
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
        value["signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode("ascii")
        return value

    def write_tracker(
        self, path: Path, blocks: list[tuple[str, list[int], str]]
    ) -> None:
        rows: list[str] = []
        sections: list[str] = []
        for number, (title, dependencies, status) in enumerate(blocks):
            dependency_text = ", ".join(str(item) for item in dependencies) or "—"
            rows.append(
                f"| {number} | {title} | {dependency_text} | `{status}` |"
            )
            evidence = (
                f"Accepted evidence for {title}." if status == "completed" else "Pending."
            )
            sections.append(
                f"""## Block {number} — {title}

Status: `{status}`

### Objective

Make {title.lower()} true.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: improve {title.lower()}.
- Potential capability loss or regression: malformed structure could lose accepted work.
- Protected-capability effect: preserve accepted history and full-range continuation.
- Architecture and operating-model effect: reuse the existing author and supervision owners.
- Tradeoff and source evidence: the exact predecessor and proposal bound this delta.

### Inputs and dependencies

- Current canonical tracker evidence.

### Required work

- Implement only {title.lower()}.

### Scope and non-goals

- In scope: {title.lower()}.
- Not in scope: candidate implementation or release.

### Deliverables and recorded state

- Exact bounded evidence for {title.lower()}.

### Resource and economy contract

Reuse the current bounded tracker snapshot once.

### QA and independent review

Run focused verification and exact independent review.

### Acceptance

- {title} is current and evidence-bound.

### Negative tests

- Reject stale or rewritten accepted evidence.

### Completion evidence

{evidence}

### Stop

Stop before the next Block mutation.
"""
            )
        path.write_text(
            """# Active program revision fixture

- Tracker sequence: Blocks 0–{terminal}

## Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: the fixture changes an active program structure.
- Direct product sources: exact predecessor and proposed tracker bytes.
- Product thesis and intended effect: preserve accepted work while revising invalid structure.
- Protected capabilities: accepted Block history and standing full-tracker intent.
- Architecture strategy: reuse the tracker author, full verifier, and supervision range owner.
- Requested capability: one exact structural revision and automatic continuation.
- Proportionality: invalidate only the affected dependency closure.
- Tradeoffs: structural review costs one separate signed review.
- Uncertainty: later candidate and cutover work remains outside this Block.

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---|---|
{rows}

## Program source map

| Block | Current source basis |
|---:|---|
{source_rows}

## Program verification matrix

| Block | Current verification basis |
|---:|---|
{verification_rows}

{sections}
""".format(
                terminal=len(blocks) - 1,
                rows="\n".join(rows),
                source_rows="\n".join(
                    f"| {number} | source-block-{number} |"
                    for number in range(len(blocks))
                ),
                verification_rows="\n".join(
                    f"| {number} | verify-block-{number} |"
                    for number in range(len(blocks))
                ),
                sections="\n---\n\n".join(sections),
            ),
            encoding="utf-8",
        )

    def structural_decision_evidence(
        self,
        *,
        decision_id: str = "program-revision-decision-1234",
        target_class: str = "software-factory",
    ) -> dict[str, object]:
        value = self.fixture.decision_evidence(
            decision_id=decision_id,
            disposition="amend-structure",
            target_class=target_class,
        )
        tracker_root = hashlib.sha256(self.fixture.tracker_path.read_bytes()).hexdigest()
        value["affected_scope"] = [
            {
                "owner_id": self.fixture.target,
                "path": str(self.fixture.tracker_path),
                "content_root": tracker_root,
            }
        ]
        for item in value["adjudicating_evidence_refs"]:  # type: ignore[union-attr]
            if item["ref_id"] == "owned-file-1234":
                item["root_sha256"] = tracker_root
        value["adjudicating_evidence_refs"] = sorted(
            value["adjudicating_evidence_refs"],  # type: ignore[arg-type]
            key=lambda item: item["ref_id"],
        )
        value["evidence_manifest_root"] = supervision_log.digest(
            value["adjudicating_evidence_refs"]
        )
        state_root = supervision_log.digest(
            {
                "target_revision_root": value["target_revision_root"],
                "affected_scope": value["affected_scope"],
            }
        )
        value["decision_target_state_root"] = state_root
        value["current_target_state_root"] = state_root
        material = dict(value)
        material.pop("source_root")
        value["source_root"] = supervision_log.digest(material)
        return value

    def build_packet(
        self,
        *,
        last_block_successors: list[int] | None = None,
        revision_id: str = "PROGRAM-REVISION-1234",
        predecessor_revision_id: str | None = None,
        predecessor_review_root: str | None = None,
        resolved_finding_refs: list[str] | None = None,
    ) -> dict[str, object]:
        mission = supervision_log.bound_mission(self.policy)
        assert mission is not None
        authoring_profile = self.policy["program_revision_authoring_profile"]
        metadata = {
            "revision_id": revision_id,
            "predecessor_revision_id": predecessor_revision_id,
            "predecessor_review_root": predecessor_review_root,
            "resolved_finding_refs": resolved_finding_refs or [],
            "target_thread_id": self.fixture.target,
            "target_class": self.source["target_class"],
            "mission_root": mission["mission_root"],
            "policy_sha256": self.policy["policy_sha256"],
            "decision_record_id": self.source["record_id"],
            "decision_record_sha256": self.source["record_sha256"],
            "decision_fingerprint": self.source["decision_fingerprint"],
            "decision_currentness_root": self.source["decision_currentness_root"],
            "application_precondition_root": self.source[
                "application_precondition_root"
            ],
            "candidate_evidence_root": self.source["candidate_evidence_root"],
            "decision_target_state_root": self.decision_evidence[
                "decision_target_state_root"
            ],
            "current_target_state_root": self.decision_evidence[
                "current_target_state_root"
            ],
            "repository_root": self.fixture.repository_root,
            "target_revision": self.fixture.target_revision,
            "target_revision_root": self.decision_evidence["target_revision_root"],
            "author_id": authoring_profile["authoring_target_thread_id"],
            "application_owner_id": self.source["implementation_owner_id"],
            "reviewer_id": authoring_profile["semantic_reviewer_id"],
            "authoring_profile_revision": authoring_profile["profile_revision"],
            "authoring_profile_root": authoring_profile["profile_root"],
            "authoring_profile_source_revision": authoring_profile[
                "profile_source_revision"
            ],
            "authoring_profile_source_root": authoring_profile[
                "profile_source_root"
            ],
            "authoring_profile_binding_root": authoring_profile["binding_root"],
            "mechanical_watcher_id": authoring_profile["mechanical_watcher_id"],
            "mechanical_route_record_id": self.mechanical_route["record_id"],
            "semantic_review_record_id": self.semantic_review["record_id"],
            "semantic_review_root": self.semantic_review["review_root"],
            "adjudicator_id": authoring_profile["adjudicator_id"],
            "adjudication_root": (
                self.semantic_review["evaluation_root"]
                if self.semantic_review["evaluation_root"] is not None
                else self.semantic_review["review_root"]
            ),
            "fix_executor_id": authoring_profile["fix_executor_id"],
            "learned_fact_refs": ["FACT-STRUCTURE-1234"],
            "capability_effects": {
                "gains": ["dependency-safe revised program"],
                "protected": ["accepted Block history", "standing full range"],
                "losses": [],
            },
            "selected_path": "structural-authoring",
            "rejected_paths": ["continue-unchanged", "correct-inline"],
            "proposed_mutations": ["split-active-structural-block"],
            "preserved_work_refs": ["BLOCKS-0-6-ACCEPTED"],
            "invalidated_proof_refs": ["BLOCK-7-OLD-CONTRACT"],
            "authority_mode": self.source["adaptive_decision_mode"],
            "stop": "before-candidate-implementation",
            "block_number_map": {
                **{str(number): [number] for number in range(7)},
                "7": last_block_successors or [7, 8],
            },
        }
        return program_revision.build_revision_packet(
            previous_tracker=self.fixture.tracker_path,
            proposed_tracker=self.proposal,
            target_tracker_path=self.fixture.tracker_path,
            metadata=metadata,
        )

    def signed_program_review(
        self, *, disposition: str = "accepted"
    ) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-program-revision-independent-review",
            "record_id": f"program-review-{disposition}-1234",
            "revision_id": self.packet["revision_id"],
            "predecessor_revision_id": self.packet["predecessor_revision_id"],
            "predecessor_review_root": self.packet["predecessor_review_root"],
            "resolved_finding_refs": self.packet["resolved_finding_refs"],
            "packet_root": self.packet["packet_root"],
            "previous_tracker_sha256": self.packet["previous_tracker_sha256"],
            "proposed_tracker_sha256": self.packet["proposed_tracker_sha256"],
            "proposed_tracker_structure_sha256": self.packet[
                "proposed_tracker_structure_sha256"
            ],
            "accepted_history_root": self.packet["accepted_history_root"],
            "block_map_root": program_revision.digest(
                self.packet["block_number_map"]
            ),
            "affected_closure_root": program_revision.digest(
                self.packet["affected_proposed_blocks"]
            ),
            "resume_block": self.packet["resume_block"],
            "author_id": self.packet["author_id"],
            "application_owner_id": self.packet["application_owner_id"],
            "reviewer_id": self.packet["reviewer_id"],
            "mechanical_watcher_id": self.packet["mechanical_watcher_id"],
            "adjudicator_id": self.packet["adjudicator_id"],
            "fix_executor_id": self.packet["fix_executor_id"],
            "authoring_profile_source_revision": self.packet[
                "authoring_profile_source_revision"
            ],
            "authoring_profile_source_root": self.packet[
                "authoring_profile_source_root"
            ],
            "authoring_profile_binding_root": self.packet[
                "authoring_profile_binding_root"
            ],
            "mechanical_route_record_id": self.packet[
                "mechanical_route_record_id"
            ],
            "semantic_review_record_id": self.packet[
                "semantic_review_record_id"
            ],
            "adjudication_root": self.packet["adjudication_root"],
            "disposition": disposition,
            "finding_refs": [] if disposition == "accepted" else ["FINDING-1234"],
            "evidence_root": program_revision.digest(
                {"packet_root": self.packet["packet_root"], "disposition": disposition}
            ),
            "authority_key_sha256": self.fixture.public_key_sha,
            "review_root": "",
            "signature_base64": "",
        }
        if self.local_reviews and "program" in self.local_review_stages:
            return self.local_review(value, "program")
        value["review_root"] = program_revision.digest(
            program_revision.review_root_material(value)
        )
        content = self.fixture.root / "program-review-to-sign.json"
        signature = self.fixture.root / "program-review.sig"
        signed = dict(value)
        signed.pop("signature_base64")
        content.write_bytes(program_revision.canonical(signed))
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.fixture.private_key),
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
        value["signature_base64"] = base64.b64encode(signature.read_bytes()).decode()
        return value

    def record_program_revision(self, *, disposition: str = "accepted") -> dict[str, object]:
        review_path = self.fixture.write_json(
            f"program-review-{disposition}.json",
            self.signed_program_review(disposition=disposition),
        )
        decision_path = self.fixture.write_json(
            "program-decision.json", self.decision_evidence
        )
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.fixture.root),
                "implementation-program-revision",
                "--target-thread",
                self.fixture.target,
                "--previous-tracker",
                str(self.fixture.tracker_path),
                "--proposed-tracker",
                str(self.proposal),
                "--packet-json",
                str(self.packet_path),
                "--review-json",
                str(review_path),
                "--decision-evidence",
                str(decision_path),
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_implementation_program_revision(args)
        return json.loads(output.getvalue())

    def use_target_repository_review(self) -> None:
        self.policy = self.fixture.adjust(
            "--adaptive-target-class", "target-repository"
        )
        self.decision_evidence = self.structural_decision_evidence(
            decision_id="program-revision-target-repository-1234",
            target_class="target-repository",
        )
        pending = self.fixture.run_gate(
            self.fixture.gate_args(self.decision_evidence)
        )["record"]
        adaptive_review = self.fixture.run_review(pending)["record"]
        self.mechanical_route = pending
        self.semantic_review = adaptive_review
        self.source = self.fixture.run_gate(
            self.fixture.gate_args(
                self.decision_evidence,
                review_record=str(adaptive_review["record_id"]),
            )
        )["record"]
        self.packet = self.build_packet()
        self.packet_path.write_bytes(program_revision.canonical(self.packet) + b"\n")

    def apply_proposal(self) -> str:
        self.fixture.tracker_path.write_bytes(self.proposal.read_bytes())
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "add",
                "tracker.md",
            ],
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit",
                "-q",
                "-m",
                "apply accepted program revision",
            ],
            check=True,
        )
        return subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "rev-parse",
                "HEAD",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def range_amend(
        self, event_id: str, application_commit: str
    ) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.fixture.root),
                "implementation-range-amend",
                "--target-thread",
                self.fixture.target,
                "--tracker",
                str(self.fixture.tracker_path),
                "--amendment-event-record",
                event_id,
                "--application-commit",
                application_commit,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_implementation_range_amend(args)
        return json.loads(output.getvalue())

    def test_accepted_revision_maps_full_range_and_resumes_dependency_safe_block(self) -> None:
        accepted = self.record_program_revision()
        duplicate_record = self.record_program_revision()
        self.assertFalse(accepted["duplicate"])
        self.assertTrue(duplicate_record["duplicate"])
        self.assertEqual(
            duplicate_record["next_action"], accepted["next_action"]
        )
        self.assertEqual(accepted["record"]["review_disposition"], "accepted")
        self.fixture.tracker_path.write_bytes(self.proposal.read_bytes())
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "parent differs from the accepted target revision|"
            "does not contain the accepted tracker",
        ):
            self.range_amend(
                str(accepted["record"]["record_id"]),
                self.fixture.target_revision,
            )
        application_commit = self.apply_proposal()
        amended = self.range_amend(
            str(accepted["record"]["record_id"]), application_commit
        )
        duplicate_amend = self.range_amend(
            str(accepted["record"]["record_id"]), application_commit
        )
        self.assertFalse(amended["contraction"])
        self.assertFalse(amended["duplicate"])
        self.assertEqual(amended["binding"]["tracker_blocks"], list(range(9)))
        self.assertEqual(amended["program_revision"]["resume_block"], 7)
        self.assertEqual(
            amended["program_revision"]["next_action"],
            "resume-block-7-without-user-scheduling",
        )
        self.assertTrue(duplicate_amend["duplicate"])
        self.assertEqual(
            duplicate_amend["program_revision"], amended["program_revision"]
        )
        policy = supervision_log.read_json(
            self.fixture.root / self.fixture.target / "policy.json"
        )
        state = supervision_log.implementation_range_state(policy)
        assert state is not None
        self.assertEqual(state["requested_blocks"], list(range(9)))
        self.assertEqual(state["accepted_blocks"], list(range(7)))
        self.assertEqual(state["eligible_blocks"], [7])
        packet = accepted["record"]["packet"]
        self.assertEqual(packet["accepted_history_blocks"], list(range(7)))
        self.assertEqual(packet["affected_proposed_blocks"], [7, 8])
        self.assertEqual(packet["resume_block"], 7)

    def test_same_target_author_and_application_owner_reaches_canonical_event(self) -> None:
        profile = self.policy["program_revision_authoring_profile"]
        self.assertEqual(profile["authoring_target_thread_id"], self.fixture.target)
        self.assertEqual(self.packet["author_id"], self.fixture.target)
        self.assertEqual(
            self.packet["application_owner_id"], self.source["implementation_owner_id"]
        )
        self.assertEqual(self.packet["author_id"], self.packet["application_owner_id"])
        accepted = self.record_program_revision()
        self.assertEqual(accepted["record"]["review_disposition"], "accepted")
        self.assertEqual(
            accepted["record"]["packet"]["application_owner_id"],
            self.fixture.target,
        )

    def test_target_repository_review_root_is_adjudication_without_evaluator(self) -> None:
        self.use_target_repository_review()
        self.assertIsNone(self.semantic_review["evaluation_root"])
        self.assertEqual(
            self.packet["adjudication_root"], self.semantic_review["review_root"]
        )
        before = supervision_log.events(
            self.fixture.root / self.fixture.target / "events.jsonl"
        )
        accepted = self.record_program_revision()
        after = supervision_log.events(
            self.fixture.root / self.fixture.target / "events.jsonl"
        )
        self.assertEqual(accepted["record"]["packet"], self.packet)
        self.assertEqual(len(after), len(before) + 1)

    def test_target_repository_wrong_or_missing_adjudication_rejects_without_append(self) -> None:
        self.use_target_repository_review()
        original = copy.deepcopy(self.packet)
        directory = self.fixture.root / self.fixture.target
        before = supervision_log.events(directory / "events.jsonl")
        for root in (
            None,
            "f" * 64,
            self.semantic_review["external_review_root"],
        ):
            with self.subTest(adjudication_root=root):
                changed = copy.deepcopy(original)
                changed["adjudication_root"] = root
                changed["packet_root"] = program_revision.digest(
                    {
                        key: value
                        for key, value in changed.items()
                        if key != "packet_root"
                    }
                )
                self.packet = changed
                self.packet_path.write_bytes(
                    program_revision.canonical(changed) + b"\n"
                )
                with self.assertRaisesRegex(
                    supervision_log.SupervisionLogError,
                    "adjudication|SHA-256|tracker-authoring supervision binding",
                ):
                    self.record_program_revision()
                self.assertEqual(
                    supervision_log.events(directory / "events.jsonl"), before
                )

    def test_software_factory_requires_accepted_evaluator_before_append(self) -> None:
        self.assertEqual(self.semantic_review["evaluation_disposition"], "accepted")
        self.assertEqual(
            self.packet["adjudication_root"], self.semantic_review["evaluation_root"]
        )
        directory = self.fixture.root / self.fixture.target
        before = supervision_log.events(directory / "events.jsonl")
        for disposition in (None, "rejected"):
            with self.subTest(evaluation_disposition=disposition):
                review = copy.deepcopy(self.semantic_review)
                review["evaluation_disposition"] = disposition
                if disposition is None:
                    review["evaluation_root"] = None
                with (
                    mock.patch.object(
                        supervision_log,
                        "resolve_adaptive_review",
                        return_value=review,
                    ),
                    self.assertRaisesRegex(
                        supervision_log.SupervisionLogError,
                        "structural decision is not accepted",
                    ),
                ):
                    self.record_program_revision()
                self.assertEqual(
                    supervision_log.events(directory / "events.jsonl"), before
                )

    def test_spoofed_application_owner_rejects_before_event_append(self) -> None:
        changed_packet = copy.deepcopy(self.packet)
        changed_packet["application_owner_id"] = "spoofed-application-owner-1234"
        changed_packet["packet_root"] = program_revision.digest(
            {
                key: value
                for key, value in changed_packet.items()
                if key != "packet_root"
            }
        )
        self.packet = changed_packet
        self.packet_path.write_bytes(
            program_revision.canonical(changed_packet) + b"\n"
        )
        directory = self.fixture.root / self.fixture.target
        before = supervision_log.events(directory / "events.jsonl")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "differs from its decision owner",
        ):
            self.record_program_revision()
        self.assertEqual(supervision_log.events(directory / "events.jsonl"), before)

    def test_revise_disposition_is_retained_but_cannot_amend_range(self) -> None:
        retained = self.record_program_revision(disposition="revise")
        self.assertEqual(
            retained["next_action"],
            "return-exact-findings-to-author-and-continue-safe-frontier",
        )
        application_commit = self.apply_proposal()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "not independently accepted",
        ):
            self.range_amend(
                str(retained["record"]["record_id"]), application_commit
            )

    def test_revise_findings_require_exact_corrective_delta_lineage(self) -> None:
        retained = self.record_program_revision(disposition="revise")
        lineage = {
            "revision_id": "PROGRAM-REVISION-1235",
            "predecessor_revision_id": retained["record"]["revision_id"],
            "predecessor_review_root": retained["record"]["review_root"],
            "resolved_finding_refs": retained["record"]["review_payload"][
                "finding_refs"
            ],
        }
        self.install_program_control(
            {**{str(number): [number] for number in range(7)}, "7": [7, 8]},
            affected=[7, 8],
            resume=7,
            revision_id="PROGRAM-REVISION-1235",
        )
        self.packet = self.build_packet(**lineage)
        self.packet_path.write_bytes(program_revision.canonical(self.packet) + b"\n")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "lacks a corrective structural delta",
        ):
            self.record_program_revision()
        self.proposal.write_text(
            self.proposal.read_text(encoding="utf-8").replace(
                "| 8 | source-block-8 |",
                "| 8 | corrected-source-block-8 |",
            ),
            encoding="utf-8",
        )
        self.install_program_control(
            {**{str(number): [number] for number in range(7)}, "7": [7, 8]},
            affected=[7, 8],
            resume=7,
            revision_id="PROGRAM-REVISION-1235",
        )
        self.packet = self.build_packet(**lineage)
        self.packet_path.write_bytes(program_revision.canonical(self.packet) + b"\n")
        corrected = self.record_program_revision()
        self.assertEqual(corrected["record"]["review_disposition"], "accepted")
        self.assertEqual(
            corrected["record"]["packet"]["predecessor_review_root"],
            retained["record"]["review_root"],
        )

    def test_application_rejects_policy_change_after_revision_acceptance(self) -> None:
        accepted = self.record_program_revision()
        self.policy = self.fixture.adjust(
            "--adaptive-decision-mode", "reviewed-autonomous"
        )
        application_commit = self.apply_proposal()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "stale for the current policy",
        ):
            self.range_amend(
                str(accepted["record"]["record_id"]), application_commit
            )

    def test_application_commit_parent_must_equal_accepted_target_revision(self) -> None:
        accepted = self.record_program_revision()
        application_commit = self.apply_proposal()
        tree = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "rev-parse",
                f"{application_commit}^{{tree}}",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        unrelated_parent = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit-tree",
                tree,
            ],
            check=True,
            input="unrelated root\n",
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        detached = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit-tree",
                tree,
                "-p",
                unrelated_parent,
            ],
            check=True,
            input="detached accepted bytes\n",
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        merge = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit-tree",
                tree,
                "-p",
                application_commit,
                "-p",
                detached,
            ],
            check=True,
            input="merge detached witness\n",
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "update-ref",
                "HEAD",
                merge,
            ],
            check=True,
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "parent differs from the accepted target revision",
        ):
            self.range_amend(str(accepted["record"]["record_id"]), detached)

    def test_application_commit_rejects_unrelated_target_change(self) -> None:
        accepted = self.record_program_revision()
        self.fixture.tracker_path.write_bytes(self.proposal.read_bytes())
        owned = Path(self.fixture.owned_path)
        owned.write_text("unrelated target implementation\n", encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "add",
                "tracker.md",
                owned.name,
            ],
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "commit",
                "-q",
                "-m",
                "mix program revision with unrelated work",
            ],
            check=True,
        )
        mixed_commit = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                self.fixture.repository_root,
                "rev-parse",
                "HEAD",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "changes unrelated repository paths",
        ):
            self.range_amend(
                str(accepted["record"]["record_id"]), mixed_commit
            )

    def test_application_currentness_change_during_policy_update_is_rejected(self) -> None:
        accepted = self.record_program_revision()
        application_commit = self.apply_proposal()
        directory = self.fixture.root / self.fixture.target
        before = supervision_log.read_json(directory / "policy.json")[
            "implementation_range"
        ]
        original_write = supervision_log.write_policy_version

        def write_with_currentness_change(*args, **kwargs):
            if kwargs.get("kind") == "implementation-range-amend":
                self.fixture.tracker_path.write_text(
                    self.fixture.tracker_path.read_text(encoding="utf-8")
                    + "\nRepository-owned later tracker change.\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    [
                        "/usr/bin/git",
                        "-C",
                        self.fixture.repository_root,
                        "add",
                        "tracker.md",
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "/usr/bin/git",
                        "-C",
                        self.fixture.repository_root,
                        "commit",
                        "-q",
                        "-m",
                        "advance tracker after application validation",
                    ],
                    check=True,
                )
            return original_write(*args, **kwargs)

        with (
            mock.patch.object(
                supervision_log,
                "write_policy_version",
                side_effect=write_with_currentness_change,
            ),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "changed during the range update",
            ),
        ):
            self.range_amend(
                str(accepted["record"]["record_id"]), application_commit
            )
        after = supervision_log.read_json(directory / "policy.json")
        self.assertEqual(after["implementation_range"], before)

    def test_stale_packet_and_signature_fail_before_event_append(self) -> None:
        stale = copy.deepcopy(self.packet)
        stale["resume_block"] = 8
        stale["packet_root"] = program_revision.digest(
            {key: value for key, value in stale.items() if key != "packet_root"}
        )
        self.packet_path.write_bytes(program_revision.canonical(stale) + b"\n")
        before = supervision_log.events(
            self.fixture.root / self.fixture.target / "events.jsonl"
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "differs from current sources",
        ):
            self.record_program_revision()
        after = supervision_log.events(
            self.fixture.root / self.fixture.target / "events.jsonl"
        )
        self.assertEqual(after, before)

    def test_authoring_profile_and_canonical_route_are_not_caller_replaceable(self) -> None:
        changed_packet = copy.deepcopy(self.packet)
        changed_packet["authoring_profile_binding_root"] = "f" * 64
        changed_packet["mechanical_route_record_id"] = "EVT-UNVERIFIED-ROUTE-1234"
        changed_packet["packet_root"] = program_revision.digest(
            {
                key: value
                for key, value in changed_packet.items()
                if key != "packet_root"
            }
        )
        self.packet = changed_packet
        self.packet_path.write_bytes(
            program_revision.canonical(changed_packet) + b"\n"
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "tracker-authoring supervision binding",
        ):
            self.record_program_revision()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "roles are not distinct",
        ):
            supervision_log.tracker_authoring_profile_binding(
                authoring_thread_id=self.policy["runtime"]["watcher_thread_id"],
                runtime=self.policy["runtime"],
                profile_review=self.profile_review,
            )

    def test_external_target_uses_maintained_profile_without_a_copied_document(self) -> None:
        target_profile = (
            Path(self.fixture.repository_root)
            / supervision_log.TRACKER_AUTHORING_PROFILE_SOURCE_PATH
        )
        self.assertFalse(target_profile.exists())
        accepted = self.record_program_revision()
        self.assertEqual(accepted["record"]["review_disposition"], "accepted")
        self.assertEqual(
            accepted["record"]["packet"]["repository_root"],
            self.fixture.repository_root,
        )
        self.assertEqual(
            accepted["record"]["packet"]["authoring_profile_source_revision"],
            self.software_factory_source_revision,
        )

    def test_authoring_profile_resolves_exact_maintained_source_revision(self) -> None:
        profile = self.policy["program_revision_authoring_profile"]
        self.assertEqual(
            profile["profile_source_path"],
            "docs/software-factory-tracker-authoring-supervision-implementation-tracker.md",
        )
        self.assertEqual(
            profile["profile_revision"], self.software_factory_source_revision
        )
        self.assertEqual(profile["profile_root"], profile["profile_source_root"])
        self.assertEqual(
            profile["profile_acceptance_record_id"], self.profile_review["record_id"]
        )
        self.assertEqual(
            profile["profile_acceptance_root"], self.profile_review["review_root"]
        )
        self.assertEqual(
            profile["mechanical_watcher_id"], self.policy["runtime"]["watcher_thread_id"]
        )
        self.assertEqual(
            profile["semantic_reviewer_id"],
            self.policy["runtime"]["base_reviewer_thread_id"],
        )
        self.assertEqual(
            profile["adjudicator_id"], self.policy["runtime"]["reviewer_thread_id"]
        )
        self.assertEqual(
            profile["fix_executor_id"], self.policy["runtime"]["fix_executor_thread_id"]
        )
        source_bytes = subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(self.software_factory_source_root),
                "cat-file",
                "blob",
                f"{profile['profile_source_revision']}:"
                f"{supervision_log.TRACKER_AUTHORING_PROFILE_SOURCE_PATH}",
            ],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        self.assertEqual(
            profile["profile_source_root"], hashlib.sha256(source_bytes).hexdigest()
        )
        changed_policy = copy.deepcopy(self.policy)
        changed_profile = dict(profile)
        changed_profile["profile_source_root"] = "f" * 64
        changed_profile["binding_root"] = supervision_log.digest(
            {
                key: value
                for key, value in changed_profile.items()
                if key != "binding_root"
            }
        )
        changed_policy["program_revision_authoring_profile"] = changed_profile
        changed_policy["policy_sha256"] = supervision_log.digest(
            supervision_log.policy_material(changed_policy)
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "profile binding differs",
        ):
            supervision_log.validate_policy(changed_policy)
        changed_review = copy.deepcopy(self.profile_review)
        changed_review["signature_base64"] = base64.b64encode(b"x" * 64).decode()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "signature verification failed",
        ):
            supervision_log.validate_tracker_authoring_profile_review(
                changed_review
            )

    def test_stale_or_mismatched_maintained_profile_source_fails_closed(self) -> None:
        unrelated_source, _revision, _source_sha256 = (
            self.create_profile_source_repository(
                "unrelated-software-factory-source",
                "# Unrelated profile source\n",
            )
        )
        directory = self.fixture.root / self.fixture.target
        before = supervision_log.events(directory / "events.jsonl")
        with (
            mock.patch.object(
                supervision_log,
                "software_factory_source_repository_root",
                return_value=unrelated_source,
            ),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "source is not in current repository history",
            ),
        ):
            self.record_program_revision()
        self.assertEqual(
            supervision_log.events(directory / "events.jsonl"), before
        )

        mismatched_review = self.signed_profile_review(
            source_revision=self.software_factory_source_revision,
            source_root="f" * 64,
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "review differs from its exact source",
        ):
            supervision_log.tracker_authoring_profile_binding(
                authoring_thread_id="tracker-authoring-thread-1234",
                runtime=self.policy["runtime"],
                profile_review=mismatched_review,
            )
        self.assertEqual(
            supervision_log.events(directory / "events.jsonl"), before
        )

    def test_adaptive_target_root_and_revision_drift_remain_fail_closed(self) -> None:
        drifted_root = copy.deepcopy(self.decision_evidence)
        drifted_root["target_repository_root"] = str(
            self.software_factory_source_root
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Adaptive target repository root differs from canonical policy",
        ):
            supervision_log.validate_adaptive_decision_evidence(
                drifted_root, policy=self.policy
            )

        directory = self.fixture.root / self.fixture.target
        before = supervision_log.events(directory / "events.jsonl")
        drift_path = Path(self.fixture.repository_root) / "target-drift.txt"
        drift_path.write_text("later target state\n", encoding="utf-8")
        subprocess.run(
            ["/usr/bin/git", "add", "target-drift.txt"],
            cwd=self.fixture.repository_root,
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "commit", "-q", "-m", "advance target state"],
            cwd=self.fixture.repository_root,
            check=True,
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "Adaptive target revision is stale",
        ):
            self.record_program_revision()
        self.assertEqual(
            supervision_log.events(directory / "events.jsonl"), before
        )

    def test_exact_explicit_range_maps_to_successor_union_without_contraction(self) -> None:
        directory = self.fixture.root / self.fixture.target
        policy = supervision_log.read_json(directory / "policy.json")
        contract = policy["implementation_range"]
        contract["range_intent"] = "explicit-blocks"
        contract["explicit_blocks"] = [7]
        history = list(contract["history"])
        history[-1]["range_intent"] = "explicit-blocks"
        history[-1]["explicit_blocks"] = [7]
        history[-1]["entry_sha256"] = supervision_log.digest(
            {key: value for key, value in history[-1].items() if key != "entry_sha256"}
        )
        contract["history"] = history
        contract["history_head_sha256"] = history[-1]["entry_sha256"]
        contract["genesis_sha256"] = supervision_log.digest(
            {
                "range_id": contract["range_id"],
                "authority": contract["authority"],
                "request_text_sha256": history[0]["request_text_sha256"],
                "initial_tracker_sha256": history[0]["tracker_sha256"],
                "initial_tracker_structure_sha256": history[0][
                    "tracker_structure_sha256"
                ],
                "initial_tracker_blocks": history[0]["tracker_blocks"],
                "initial_range_intent": "explicit-blocks",
                "initial_explicit_blocks": [7],
                "mission_identity": history[0]["mission_identity"],
            }
        )
        policy["implementation_range"] = contract
        supervision_log.validate_implementation_range_contract(contract)
        supervision_log.write_policy_version(
            directory,
            policy,
            kind="test-explicit-range",
            reason="Exercise exact successor-union mapping.",
            evidence_values=[contract["history_head_sha256"]],
        )
        self.policy = supervision_log.read_json(directory / "policy.json")
        self.decision_evidence = self.structural_decision_evidence()
        pending = self.fixture.run_gate(
            self.fixture.gate_args(self.decision_evidence)
        )["record"]
        adaptive_review = self.fixture.run_review(pending)["record"]
        self.mechanical_route = pending
        self.semantic_review = adaptive_review
        self.source = self.fixture.run_gate(
            self.fixture.gate_args(
                self.decision_evidence,
                review_record=str(adaptive_review["record_id"]),
            )
        )["record"]
        explicit_map = {
            **{str(number): [number] for number in range(7)},
            "7": [8],
        }
        self.install_program_control(
            explicit_map,
            affected=[7, 8],
            resume=7,
        )
        self.packet = self.build_packet(last_block_successors=[8])
        self.packet_path.write_bytes(program_revision.canonical(self.packet) + b"\n")
        accepted = self.record_program_revision()
        application_commit = self.apply_proposal()
        amended = self.range_amend(
            str(accepted["record"]["record_id"]), application_commit
        )
        self.assertFalse(amended["contraction"])
        self.assertEqual(amended["binding"]["explicit_blocks"], [7, 8])


class LocalProgramRevisionControlTests(unittest.TestCase):
    def setUp(self):
        self.case = ProgramRevisionControlTests("test_accepted_revision_maps_full_range_and_resumes_dependency_safe_block")
        self.case.local_reviews = True
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_native_review_chain_preserves_full_range_without_signer(self):
        self.case.test_accepted_revision_maps_full_range_and_resumes_dependency_safe_block()
        case = self.case
        args = supervision_log.parser().parse_args([
            "--root", str(case.fixture.root), "implementation-range-gate",
            "--target-thread", case.fixture.target, "--response-kind", "block-boundary",
        ])
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_implementation_range_gate(args)
        gate = json.loads(output.getvalue())
        self.assertTrue(gate["range_binding_current"])
        self.assertFalse(gate["final_response_permitted"])

    def validate_review(self, review, *, policy=None, packet=None):
        case = self.case
        directory = case.fixture.root / case.fixture.target
        return supervision_log.validate_program_revision_review(
            review, packet=packet or case.packet, policy=policy or case.policy,
            all_events=supervision_log.events(directory / "events.jsonl"), owner_directory=directory,
        )

    def test_target_authored_qualifying_record_has_no_reviewer_origin(self):
        case = self.case
        review = case.signed_program_review()
        directory = case.fixture.root / case.fixture.target
        original = supervision_log.events(directory / "events.jsonl")[-1]
        forged = {key: value for key, value in original.items() if key not in {"record_id", "record_sha256", "previous_record_sha256"}}
        forged["record_id"] = f"EVT-{len(supervision_log.events(directory / 'events.jsonl')) + 1:06d}"
        # This is exactly the syntactically qualifying record the target can
        # write. Its native creation output belongs to no reviewer task.
        supervision_log.append_raw(directory / "events.jsonl", forged)
        retained = supervision_log.events(directory / "events.jsonl")[-1]
        review["canonical_review"].update({key: retained[key] for key in ("record_id", "record_sha256")})
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "native origin failed"):
            self.validate_review(review)
        # A later genuine review can recover without authenticating the older
        # target-written record or deleting it from the canonical history.
        successor = copy.deepcopy(review)
        successor["record_id"] = "program-review-genuine-successor-1234"
        successor = case.local_review(successor, "program")
        self.validate_review(successor)
        # Nor may an unverified later label become a semantic supersession.
        review["canonical_review"].update({key: original[key] for key in ("record_id", "record_sha256")})
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "native origin failed"):
            self.validate_review(review)

    def test_native_origin_rejects_wrong_turn_recipient_echo_and_shell_expansion(self):
        case = self.case
        review = case.signed_program_review()
        key = (review["reviewer_id"], review["canonical_review"]["native_turn_id"])
        original = copy.deepcopy(case.native_rows[key])
        mutations = {
            "wrong-turn": lambda rows: rows[1].update(turnId="other-turn"),
            "wrong-client": lambda rows: rows[0]["item"].update(clientId="other-delivery"),
            "wrong-message": lambda rows: rows[0]["item"].update(content=[{"type": "text", "text": "forged marker only"}]),
            "wrong-order": lambda rows: rows.reverse(),
            "echo": lambda rows: rows[1]["item"].update(command="/usr/bin/echo '{}'"),
            "duplicate": lambda rows: rows[1]["item"].update(aggregatedOutput=json.dumps({"duplicate": True, "record": json.loads(rows[1]["item"]["aggregatedOutput"])["record"]})),
            "incomplete-command": lambda rows: rows[1]["item"].update(status="inProgress"),
            "wrong-source": lambda rows: rows[1]["item"].update(source="userShell"),
            "wrong-output": lambda rows: rows[1]["item"].update(aggregatedOutput="{}"),
            "unwrapped-substitution": lambda rows: rows[1]["item"].update(command=shlex.split(rows[1]["item"]["command"])[2] + " $(echo forged)"),
            "unwrapped-operator": lambda rows: rows[1]["item"].update(command=shlex.split(rows[1]["item"]["command"])[2] + ";echo forged"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                case.native_rows[key] = copy.deepcopy(original)
                mutate(case.native_rows[key]["data"])
                with self.assertRaisesRegex(supervision_log.SupervisionLogError, "native origin failed"):
                    self.validate_review(review)
        case.native_rows[key] = original
        self.validate_review(review)
        with closing(sqlite3.connect(case.fixture.root.parent / "runtime.sqlite3", isolation_level=None)) as db:
            for field, value in (("recipient", case.fixture.target), ("turn_id", "other-turn"), ("state", "prepared"), ("message_sha256", "0" * 64), ("source", "missing-source")):
                with self.subTest(field=field):
                    old = db.execute(f"SELECT {field} FROM deliveries WHERE id=?", (review["canonical_review"]["native_delivery_id"],)).fetchone()[0]
                    db.execute(f"UPDATE deliveries SET {field}=? WHERE id=?", (value, review["canonical_review"]["native_delivery_id"]))
                    with self.assertRaisesRegex(supervision_log.SupervisionLogError, "native origin failed"):
                        self.validate_review(review)
                    db.execute(f"UPDATE deliveries SET {field}=? WHERE id=?", (old, review["canonical_review"]["native_delivery_id"]))

    def test_review_context_and_profile_location_fail_closed(self):
        case = self.case
        review = case.signed_program_review()
        for field, value in (("policy_sha256", "0" * 64), ("target_thread_id", "other-target")):
            policy = copy.deepcopy(case.policy)
            policy[field] = value
            with self.subTest(field=field), self.assertRaises(supervision_log.SupervisionLogError):
                self.validate_review(review, policy=policy)
        for field in ("mission_root", "packet_root", "accepted_history_root", "proposed_tracker_sha256"):
            packet = copy.deepcopy(case.packet)
            packet[field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(supervision_log.SupervisionLogError):
                self.validate_review(review, packet=packet)
        packet = {**case.packet, "target_class": "software-factory"}
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "release authority"):
            self.validate_review(review, packet=packet)
        with mock.patch.object(supervision_log, "software_factory_source_repository_root", SOURCE_REPOSITORY_ROOT):
            source = supervision_log.tracker_authoring_profile_source(repository_root=str(case.software_factory_source_root), source_revision=case.software_factory_source_revision)
            self.assertEqual(source["profile_source_root"], case.profile_review["profile_source_root"])
            self.assertEqual(source["profile_source_repository_root"], str(case.software_factory_source_root))
            link = case.fixture.root / "source-link"
            link.symlink_to(case.software_factory_source_root, target_is_directory=True)
            for path in (link, case.fixture.root / "unavailable", case.software_factory_source_root / "docs"):
                with self.subTest(path=path), self.assertRaises(supervision_log.SupervisionLogError):
                    supervision_log.tracker_authoring_profile_source(repository_root=str(path), source_revision=case.software_factory_source_revision)

    def test_historical_policy_can_load_during_native_outage_but_current_admission_cannot(self):
        import gcp_supervision
        case = self.case
        args = supervision_log.parser().parse_args(["--root", str(case.fixture.root), "status", "--target-thread", case.fixture.target])
        with mock.patch.object(gcp_supervision, "CodexClient", side_effect=RuntimeError("native owner unavailable")):
            directory, policy = supervision_log.load_policy(args)
            self.assertEqual(policy["policy_sha256"], case.policy["policy_sha256"])
            with self.assertRaisesRegex(supervision_log.SupervisionLogError, "not current:.*native owner unavailable"):
                supervision_log.require_current_local_tracker_reviews(directory, policy, supervision_log.events(directory / "events.jsonl"))

    def test_genuine_later_max_rejection_blocks_application_without_breaking_history(self):
        case = self.case
        accepted = case.record_program_revision()["record"]
        rejected = copy.deepcopy(accepted["review_payload"])
        rejected.update(disposition="rejected", finding_refs=["EXACT-NEW-FINDING"])
        case.local_review(rejected, "program", reviewer=case.policy["runtime"]["reviewer_thread_id"])
        application = case.apply_proposal()
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "superseded"):
            case.range_amend(accepted["record_id"], application)
        args = supervision_log.parser().parse_args(["--root", str(case.fixture.root), "status", "--target-thread", case.fixture.target])
        supervision_log.load_policy(args)


class MixedLocalProgramRevisionControlTests(unittest.TestCase):
    def check_currentness(self, *, stages, rejected_stage):
        case = ProgramRevisionControlTests("test_accepted_revision_maps_full_range_and_resumes_dependency_safe_block")
        case.local_reviews = True
        case.local_review_stages = stages
        case.setUp()
        self.addCleanup(case.doCleanups)
        accepted = case.record_program_revision()["record"]
        application = case.apply_proposal()
        case.range_amend(accepted["record_id"], application)
        args = supervision_log.parser().parse_args([
            "--root", str(case.fixture.root), "implementation-range-gate",
            "--target-thread", case.fixture.target, "--response-kind", "block-boundary",
        ])

        def gate():
            output = io.StringIO()
            with redirect_stdout(output):
                supervision_log.cmd_implementation_range_gate(args)
            return json.loads(output.getvalue())

        self.assertTrue(gate()["implementation_start_permitted"])
        review = copy.deepcopy(accepted["review_payload"] if rejected_stage == "program"
                               else case.semantic_review["external_review_payload"])
        review.update(record_id="later-genuine-rejection-1234", finding_refs=["CURRENTNESS-REGRESSION"])
        review["review_disposition" if rejected_stage == "adaptive" else "disposition"] = "rejected"
        case.local_review(review, rejected_stage, reviewer=case.policy["runtime"]["reviewer_thread_id"])
        result = gate()
        self.assertFalse(result["range_binding_current"])
        self.assertFalse(result["implementation_start_permitted"])
        self.assertFalse(result["final_response_permitted"])
        self.assertTrue(any("Local tracker review is not current" in str(issue)
                            for issue in result["control_posture"]["issues"]))
        directory, policy = supervision_log.load_policy(args)
        self.assertEqual(policy["implementation_range"]["range_intent"], "full-tracker")

    def test_signed_profile_local_program_rejection_blocks_range_and_control(self):
        self.check_currentness(stages={"adaptive", "program"}, rejected_stage="program")

    def test_signed_profile_and_program_local_adaptive_rejection_blocks_range_and_control(self):
        self.check_currentness(stages={"adaptive"}, rejected_stage="adaptive")


if __name__ == "__main__":
    unittest.main()
