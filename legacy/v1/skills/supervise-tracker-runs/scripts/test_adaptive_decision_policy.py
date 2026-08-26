#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("supervision_log.py")
SPEC = importlib.util.spec_from_file_location("supervision_log", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
supervision_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervision_log)


class AdaptiveDecisionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = "adaptive-target-1234"
        repository = self.root / "target-repository"
        repository.mkdir()
        subprocess.run(
            ["/usr/bin/git", "-C", str(repository), "init", "-q"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.repository_root = str(repository.resolve())
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "config", "user.name", "Adaptive Test"],
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "config", "user.email", "adaptive@example.invalid"],
            check=True,
        )
        self.owned_path = (repository / "owned.py").resolve()
        self.owned_path.write_text("VALUE = 1\n", encoding="utf-8")
        self.tracker_path = (repository / "tracker.md").resolve()
        self.tracker_path.write_text(
            """# Adaptive test tracker

| Block | Scope | Depends on | Status |
|---|---|---|---|
| 7 | Adaptive decision policy | None | in-progress |

## Block 7 — Adaptive decision policy

Status: in-progress

### Target-product capability delta

- Protected-capability effect: preserve the canonical Block capability frame.

### Inputs

- The canonical repository state.

### Required work

- Apply the bounded adaptive decision.

### Acceptance criteria

- Current evidence is mechanically bound.

### Completion evidence

- Pending.

### Stop

Stop after exact review.
""",
            encoding="utf-8",
        )
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "add", "owned.py", "tracker.md"],
            check=True,
        )
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "commit", "-q", "-m", "fixture"],
            check=True,
        )
        self.target_revision = subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        self.target_committed_at = dt.datetime.fromtimestamp(
            int(
                subprocess.run(
                    [
                        "/usr/bin/git",
                        "-C",
                        self.repository_root,
                        "show",
                        "-s",
                        "--format=%ct",
                        self.target_revision,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout.strip()
            ),
            tz=dt.timezone.utc,
        )
        self.candidate_observed_at = dt.datetime.now(tz=dt.timezone.utc)
        (
            _tracker_path,
            self.tracker_sha,
            self.tracker_structure_sha,
            self.tracker_blocks,
        ) = supervision_log.implementation_tracker_snapshot(str(self.tracker_path))
        self.authority_root = self.root / "sealed-authorities"
        self.authority_root.mkdir(mode=0o700)
        self.private_key = self.authority_root / "review-private.pem"
        self.public_key = self.authority_root / "review-public.pem"
        self.evaluator_private_key = self.authority_root / "evaluator-private.pem"
        self.evaluator_public_key = self.authority_root / "evaluator-public.pem"
        openssl = str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH)
        subprocess.run(
            [openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [openssl, "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.public_key.chmod(0o444)
        self.public_key_sha = hashlib.sha256(self.public_key.read_bytes()).hexdigest()
        subprocess.run(
            [
                openssl,
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(self.evaluator_private_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                openssl,
                "pkey",
                "-in",
                str(self.evaluator_private_key),
                "-pubout",
                "-out",
                str(self.evaluator_public_key),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.evaluator_public_key.chmod(0o444)
        self.evaluator_public_key_sha = hashlib.sha256(
            self.evaluator_public_key.read_bytes()
        ).hexdigest()
        for name, value in (
            ("ADAPTIVE_REVIEW_PUBLIC_KEY_PATH", self.public_key),
            ("ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256", self.public_key_sha),
            ("ADAPTIVE_REVIEW_PRIVATE_KEY_PATH", self.private_key),
            ("ADAPTIVE_EVALUATOR_PUBLIC_KEY_PATH", self.evaluator_public_key),
            ("ADAPTIVE_EVALUATOR_PUBLIC_KEY_SHA256", self.evaluator_public_key_sha),
        ):
            patcher = mock.patch.object(supervision_log, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def policy(
        self,
        mode: str = "full-autonomous",
        *,
        target_class: str = "target-repository",
        repository_write: bool = True,
    ) -> dict[str, object]:
        permissions = {
            field: False for field in supervision_log.ADAPTIVE_PERMISSION_FIELDS
        }
        permissions["repository_write"] = repository_write
        permissions["command_or_test_execution"] = repository_write
        return {
            "target_thread_id": self.target,
            "policy_sha256": "a" * 64,
            "runtime": {
                "watcher_thread_id": "watcher-1234",
                "reviewer_thread_id": "reviewer-1234",
                "base_reviewer_thread_id": "base-reviewer-1234",
                "fix_executor_thread_id": "fix-executor-1234",
            },
            "permissions": permissions,
            "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(
                mode,
                target_class=target_class,
                target_repository_root=self.repository_root,
            ),
            "implementation_range": self.range_contract(),
        }

    def range_contract(self) -> dict[str, object]:
        request = "Implement this tracker!"
        authority = {
            "source_class": "direct-user",
            "source_record": "direct-range-item-1235",
            "source_sha256": hashlib.sha256(request.encode()).hexdigest(),
        }
        entry = supervision_log.implementation_range_history_entry(
            sequence=1,
            prior_entry_sha256="",
            operation="bound",
            request_text=request,
            tracker_sha256=self.tracker_sha,
            tracker_structure_sha256=self.tracker_structure_sha,
            tracker_path=str(self.tracker_path),
            tracker_blocks=[7],
            range_intent="full-tracker",
            explicit_blocks=[],
            authority=authority,
            authority_policy_version=1,
        )
        genesis = supervision_log.digest(
            {
                "range_id": "adaptive-range-1234",
                "authority": authority,
                "request_text_sha256": entry["request_text_sha256"],
                "initial_tracker_sha256": self.tracker_sha,
                "initial_tracker_structure_sha256": self.tracker_structure_sha,
                "initial_tracker_blocks": [7],
                "initial_range_intent": "full-tracker",
                "initial_explicit_blocks": [],
            }
        )
        return {
            "schema_version": 1,
            "kind": "implementation-range-binding",
            "range_id": "adaptive-range-1234",
            "genesis_sha256": genesis,
            "authority": authority,
            "range_intent": "full-tracker",
            "explicit_blocks": [],
            "tracker_path": str(self.tracker_path),
            "tracker_sha256": self.tracker_sha,
            "tracker_structure_sha256": self.tracker_structure_sha,
            "tracker_blocks": [7],
            "history": [entry],
            "history_head_sha256": entry["entry_sha256"],
        }

    def decision_evidence(
        self,
        *,
        decision_id: str = "adaptive-decision-1234",
        disposition: str = "correct-inline",
        target_class: str = "target-repository",
        candidate_evidence_root: str | None = None,
        evidence_root: str = "1" * 64,
        consequence_class: str = "routine",
        judgment_class: str = "ordinary-engineering",
        reversible: bool = True,
        mission_preserving: bool = True,
        blocked_subjects: list[str] | None = None,
        revisit_trigger: str = "",
    ) -> dict[str, object]:
        block = self.tracker_blocks[7]
        target_revision_root = supervision_log.digest(
            {"target_revision": self.target_revision}
        )
        file_root = hashlib.sha256(self.owned_path.read_bytes()).hexdigest()
        evidence_refs = sorted(
            [
                {"ref_id": "block-contract-1234", "source_class": "tracker", "root_sha256": block["contract_sha256"]},
                {"ref_id": "capability-frame-1234", "source_class": "tracker", "root_sha256": block["capability_frame_sha256"]},
                {"ref_id": "owned-file-1234", "source_class": "repository", "root_sha256": file_root},
                {"ref_id": "target-revision-1234", "source_class": "repository", "root_sha256": target_revision_root},
                {"ref_id": "tracker-content-1234", "source_class": "tracker", "root_sha256": self.tracker_sha},
                {"ref_id": "supplemental-evidence-1234", "source_class": "repository", "root_sha256": evidence_root},
            ],
            key=lambda item: item["ref_id"],
        )
        protected_results = [
            {
                "capability_id": "block-7-capability-frame",
                "result": "preserved",
                "evidence_ref_ids": ["capability-frame-1234"],
            }
        ]
        affected_scope = [
            {
                "owner_id": self.target,
                "path": str(self.owned_path),
                "content_root": file_root,
            }
        ]
        target_state_root = supervision_log.digest(
            {"target_revision_root": target_revision_root, "affected_scope": affected_scope}
        )
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-decision-source",
            "decision_id": decision_id,
            "disposition": disposition,
            "judgment_class": judgment_class,
            "consequence_class": consequence_class,
            "reversible": reversible,
            "mission_preserving": mission_preserving,
            "block_number": 7,
            "block_contract_root": block["contract_sha256"],
            "tracker_sha256": self.tracker_sha,
            "target_repository_root": self.repository_root,
            "target_revision": self.target_revision,
            "target_revision_root": target_revision_root,
            "decision_target_state_root": target_state_root,
            "current_target_state_root": target_state_root,
            "capability_frame_root": block["capability_frame_sha256"],
            "protected_capability_results": protected_results,
            "protected_capability_root": supervision_log.digest(protected_results),
            "adjudicating_evidence_refs": evidence_refs,
            "affected_scope": affected_scope,
            "implementation_owner_id": self.target,
            "proposer_author_id": (
                "base-reviewer-1234" if target_class == "software-factory" else None
            ),
            "stop_boundary": "Stop after the bounded owner action and validation.",
            "safe_frontier": ["block-7-unaffected-work"],
            "blocked_subjects": sorted(blocked_subjects or []),
            "revisit_trigger": revisit_trigger,
            "candidate_evidence_root": candidate_evidence_root,
            "evidence_manifest_root": supervision_log.digest(evidence_refs),
            "accepted_decision_head": None,
            "accepted_revision_head": None,
            "source_root": "",
        }
        material = dict(value)
        material.pop("source_root")
        value["source_root"] = supervision_log.digest(material)
        return value

    def candidate(
        self,
        *,
        decision_id: str = "adaptive-decision-1234",
        usage_updates: dict[str, int] | None = None,
        protected_result: str = "preserved",
        owner_id: str | None = None,
        after_text: str = "VALUE = 2\n",
        event_time: dt.datetime | None = None,
    ) -> dict[str, object]:
        lane_time = event_time or self.target_committed_at
        observed_time = event_time or self.candidate_observed_at
        lane_time_value = lane_time.isoformat().replace("+00:00", "Z")
        observed_time_value = observed_time.isoformat().replace("+00:00", "Z")
        after = after_text.encode("utf-8")
        artifact_manifest = [
            {
                "path": str(self.owned_path),
                "before_root": hashlib.sha256(self.owned_path.read_bytes()).hexdigest(),
                "after_root": hashlib.sha256(after).hexdigest(),
                "after_content_base64": base64.b64encode(after).decode(),
                "changed_lines": 2,
            }
        ]
        command_results = [
            {
                "command_id": "focused-command-1234",
                "kind": "focused",
                "started_at": lane_time_value,
                "finished_at": lane_time_value,
                "exit_code": 0,
                "result_payload": {"status": "passed", "tests": 1},
                "result_root": supervision_log.digest({"status": "passed", "tests": 1}),
            },
            {
                "command_id": "mapped-command-1234",
                "kind": "mapped",
                "started_at": lane_time_value,
                "finished_at": lane_time_value,
                "exit_code": 0,
                "result_payload": {"status": "passed", "tests": 7},
                "result_root": supervision_log.digest({"status": "passed", "tests": 7}),
            },
        ]
        comparison_results = [
            {
                "dimension": dimension,
                "relation": "candidate-better" if dimension == "correctness" else "equivalent",
                "evidence_root": command_results[-1]["result_root"],
            }
            for dimension in supervision_log.ADAPTIVE_COMPARISON_DIMENSIONS
        ]
        usage = {
            "active_lanes_for_decision": 1,
            "active_lanes_for_target": 1,
            "files": 1,
            "changed_lines": 2,
            "commands": 2,
            "elapsed_minutes": int(
                (
                    max(0.0, (observed_time - lane_time).total_seconds())
                    + 59
                )
                // 60
            ),
            "mapped_comparisons": 1,
            "review_passes": 0,
        }
        if usage_updates:
            usage.update(usage_updates)
        candidate_root = supervision_log.digest(artifact_manifest)
        validation_root = supervision_log.digest(command_results)
        source_protected = {
            "capability_id": "block-7-capability-frame",
            "result": "preserved",
            "evidence_ref_ids": ["capability-frame-1234"],
        }
        decision_basis_source = self.decision_evidence(
            decision_id=decision_id,
            disposition="compare-candidate",
            candidate_evidence_root="0" * 64,
        )
        protected = [
            {
                "capability_id": "block-7-capability-frame",
                "result": protected_result,
                "evidence_root": supervision_log.digest(
                    {
                        "capability_id": "block-7-capability-frame",
                        "result": protected_result,
                        "source_contract_root": supervision_log.digest(source_protected),
                        "candidate_root": candidate_root,
                        "validation_root": validation_root,
                    }
                ),
            }
        ]
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-candidate-evidence",
            "decision_id": decision_id,
            "owner_id": owner_id or self.target,
            "source_revision_root": supervision_log.digest({"target_revision": self.target_revision}),
            "decision_basis_root": supervision_log.digest(
                supervision_log.adaptive_candidate_decision_basis(
                    decision_basis_source
                )
            ),
            "lane_started_at": lane_time_value,
            "observed_at": observed_time_value,
            "artifact_manifest": artifact_manifest,
            "command_results": command_results,
            "comparison_results": comparison_results,
            "candidate_root": candidate_root,
            "candidate_budget_use": usage,
            "candidate_budget_use_root": supervision_log.digest(usage),
            "protected_capability_results": protected,
            "protected_capability_root": supervision_log.digest(protected),
            "validation_root": validation_root,
            "comparison_root": supervision_log.digest(comparison_results),
            "acceptance_authority_id": supervision_log.ADAPTIVE_EVALUATOR_ID,
            "acceptance_authority_key_sha256": self.evaluator_public_key_sha,
            "acceptance_root": "",
            "acceptance_signature_base64": "",
            "currentness_root": "",
            "evidence_root": "",
        }
        value["acceptance_root"] = supervision_log.digest(
            supervision_log.adaptive_candidate_acceptance_material(value)
        )
        content = self.root / "candidate-to-sign.json"
        signature = self.root / "candidate.sig"
        content.write_bytes(
            supervision_log.canonical(
                {
                    **supervision_log.adaptive_candidate_acceptance_material(value),
                    "acceptance_root": value["acceptance_root"],
                }
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.evaluator_private_key),
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
        value["acceptance_signature_base64"] = base64.b64encode(
            signature.read_bytes()
        ).decode()
        currentness = {
            "owner_id": value["owner_id"],
            "source_revision_root": value["source_revision_root"],
            "decision_basis_root": value["decision_basis_root"],
            "candidate_root": value["candidate_root"],
            "candidate_budget_use_root": value["candidate_budget_use_root"],
            "protected_capability_root": value["protected_capability_root"],
            "validation_root": value["validation_root"],
            "comparison_root": value["comparison_root"],
            "acceptance_root": value["acceptance_root"],
        }
        value["currentness_root"] = supervision_log.digest(currentness)
        material = dict(value)
        material.pop("evidence_root")
        material.pop("decision_id")
        material.pop("acceptance_signature_base64")
        value["evidence_root"] = supervision_log.digest(material)
        return value

    def packet(
        self,
        policy: dict[str, object],
        *,
        evidence: dict[str, object] | None = None,
        candidate: dict[str, object] | None = None,
        review: dict[str, object] | None = None,
        request_human_input: bool = False,
    ) -> dict[str, object]:
        source = evidence or self.decision_evidence(
            target_class=str(
                policy.get("adaptive_decision_control", {}).get(  # type: ignore[union-attr]
                    "target_class", "target-repository"
                )
            )
        )
        return {
            "decision_evidence": source,
            "candidate_evidence": candidate,
            "independent_review": review,
            "request_human_input": request_human_input,
            "governing_event_head_root": "f" * 64,
        }

    def posture(
        self, policy: dict[str, object], packet: dict[str, object]
    ) -> dict[str, object]:
        return supervision_log._adaptive_decision_posture(
            policy, packet, active_candidate_fingerprints=[]
        )

    def normalized_review(
        self,
        policy: dict[str, object],
        evidence: dict[str, object],
        *,
        candidate: dict[str, object] | None = None,
        disposition: str = "accepted",
    ) -> dict[str, object]:
        pending = self.posture(
            policy, self.packet(policy, evidence=evidence, candidate=candidate)
        )
        source = {
            **pending,
            "record_id": "source-decision-1234",
            "record_sha256": "1" * 64,
        }
        return self.signed_review_json(
            source, review_disposition=disposition
        )

    def write_json(self, name: str, value: dict[str, object]) -> Path:
        path = self.root / name
        path.write_bytes(supervision_log.canonical(value) + b"\n")
        return path

    def init(self) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "init", "--target-thread", self.target,
                "--target-label", "Adaptive policy fixture",
                "--watcher-thread", "watcher-1234",
                "--reviewer-thread", "reviewer-1234",
                "--base-reviewer-thread", "base-reviewer-1234",
                "--fix-executor-thread", "fix-executor-1234",
                "--mission-source-class", "direct-user",
                "--mission-source-record", "direct-item-1234",
                "--mission-source-sha256", hashlib.sha256(
                    b"Implement this tracker."
                ).hexdigest(),
                "--adaptive-target-repository-root", self.repository_root,
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_init(args)
        directory = self.root / self.target
        policy = supervision_log.read_json(directory / "policy.json")
        request_text = "Implement this tracker!"
        request_bytes = request_text.encode("utf-8")
        provenance: dict[str, object] = {
            "schema_version": 1,
            "kind": supervision_log.DIRECT_AUTHORITY_PROVENANCE_KIND,
            "target_thread_id": self.target,
            "source_task_id": self.target,
            "source_turn_id": "direct-range-turn-1235",
            "source_item_id": "direct-range-item-1235",
            "source_kind": supervision_log.DIRECT_AUTHORITY_SOURCE_KIND,
            "source_text": request_text,
            "source_byte_count": len(request_bytes),
            "source_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "policy_version": policy["policy_version"],
            "policy_sha256": policy["policy_sha256"],
            "verifier_id": "reviewer-1234",
            "authorization_record_id": "EVT-000001",
        }
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": provenance["authorization_record_id"],
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "meta-review",
                "category": supervision_log.DIRECT_AUTHORITY_REVIEW_CATEGORY,
                "status": "accepted",
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": policy["policy_sha256"],
                "evidence": supervision_log.direct_authority_review_evidence(
                    provenance
                ),
            },
        )
        ingest_args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "direct-authority-ingest",
                "--target-thread", self.target,
                "--provenance-base64", base64.b64encode(
                    supervision_log.canonical(provenance)
                ).decode("ascii"),
            ]
        )
        ingest_output = io.StringIO()
        with redirect_stdout(ingest_output):
            supervision_log.cmd_direct_authority_ingest(ingest_args)
        ingested = json.loads(ingest_output.getvalue())
        receipt_args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root),
                "implementation-range-authority-receipt",
                "--target-thread", self.target,
                "--authority-event-record", str(ingested["record_id"]),
            ]
        )
        with redirect_stdout(io.StringIO()):
            supervision_log.cmd_implementation_authority_receipt(receipt_args)
        bind_args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "implementation-range-bind",
                "--target-thread", self.target,
                "--range-id", "adaptive-range-1234",
                "--tracker", str(self.tracker_path),
                "--request-text", request_text,
                "--authority-source-record", "direct-range-item-1235",
                "--authority-source-sha256", hashlib.sha256(
                    request_bytes
                ).hexdigest(),
            ]
        )
        with redirect_stdout(io.StringIO()):
            supervision_log.cmd_implementation_range_bind(bind_args)
        return json.loads(
            (self.root / self.target / "policy.json").read_text(encoding="utf-8")
        )

    def adjust(self, *extra: str) -> dict[str, object]:
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "adjust", "--target-thread", self.target,
                *extra, "--reason", "Exercise bounded adaptive policy adjustment.",
                "--evidence", "block-7-focused-test",
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adjust(args)
        return json.loads(output.getvalue())["policy"]

    def gate_args(
        self,
        evidence: dict[str, object],
        *,
        candidate: dict[str, object] | None = None,
        review_record: str | None = None,
        request_human: bool = False,
    ):
        evidence_path = self.write_json(
            f"{evidence['decision_id']}-decision.json", evidence
        )
        values = [
            "--root", str(self.root), "adaptive-decision-gate",
            "--target-thread", self.target,
            "--decision-evidence", str(evidence_path),
        ]
        if candidate is not None:
            candidate_path = self.write_json(
                f"{candidate['decision_id']}-candidate.json", candidate
            )
            values.extend(["--candidate-evidence", str(candidate_path)])
        if review_record:
            values.extend(["--independent-review-record", review_record])
        if request_human:
            values.append("--request-human-input")
        return supervision_log.parser().parse_args(values)

    def run_gate(self, args) -> dict[str, object]:
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adaptive_decision_gate(args)
        return json.loads(output.getvalue())

    def signed_review_json(
        self,
        source: dict[str, object],
        *,
        review_disposition: str = "accepted",
        mutate: dict[str, object] | None = None,
    ) -> dict[str, object]:
        software_factory = source["target_class"] == "software-factory"
        value: dict[str, object] = {
            "schema_version": 1,
            "kind": "software-factory-adaptive-independent-review",
            "record_id": f"signed-{source['decision_id']}",
            "source_decision_record": source["record_id"],
            "source_decision_sha256": source["record_sha256"],
            "decision_id": source["decision_id"],
            "decision_fingerprint": source["decision_fingerprint"],
            "decision_currentness_root": source["decision_currentness_root"],
            "decision_semantics_root": source["decision_semantics_root"],
            "disposition": source["disposition"],
            "target_class": source["target_class"],
            "effect_class": source["effect_class"],
            "candidate_evidence_root": source["candidate_evidence_root"],
            "candidate_owner_id": source["candidate_owner_id"],
            "proposer_author_id": source["proposer_author_id"],
            "implementation_owner_id": source["implementation_owner_id"],
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "evaluator_id": (
                supervision_log.ADAPTIVE_EVALUATOR_ID if software_factory else None
            ),
            "evaluation_evidence_root": "4" * 64 if software_factory else None,
            "evaluator_authority_key_sha256": (
                self.evaluator_public_key_sha if software_factory else None
            ),
            "evaluation_root": None,
            "evaluation_signature_base64": None,
            "review_disposition": review_disposition,
            "evaluation_disposition": "accepted" if software_factory else None,
            "evidence_root": supervision_log.digest(
                {"source_decision_sha256": source["record_sha256"]}
            ),
            "policy_sha256": source["policy_sha256"],
            "authority_key_sha256": self.public_key_sha,
            "review_root": "",
            "signature_base64": "",
        }
        if mutate:
            value.update(mutate)
        if software_factory:
            value["evaluation_root"] = supervision_log.digest(
                supervision_log.adaptive_external_evaluation_root_material(value)
            )
            evaluation_content = self.root / "evaluation-to-sign.json"
            evaluation_signature = self.root / "evaluation.sig"
            evaluation_content.write_bytes(
                supervision_log.canonical(
                    supervision_log.adaptive_external_evaluation_signed_material(value)
                )
            )
            subprocess.run(
                [
                    str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                    "pkeyutl",
                    "-sign",
                    "-inkey",
                    str(self.evaluator_private_key),
                    "-rawin",
                    "-in",
                    str(evaluation_content),
                    "-out",
                    str(evaluation_signature),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            value["evaluation_signature_base64"] = base64.b64encode(
                evaluation_signature.read_bytes()
            ).decode()
        return self.sign_outer_review(value)

    def sign_outer_review(self, value: dict[str, object]) -> dict[str, object]:
        value["review_root"] = supervision_log.digest(
            supervision_log.adaptive_external_review_root_material(value)
        )
        content = self.root / "review-to-sign.json"
        signature = self.root / "review.sig"
        content.write_bytes(
            supervision_log.canonical(
                supervision_log.adaptive_external_review_signed_material(value)
            )
        )
        subprocess.run(
            [
                str(supervision_log.ADAPTIVE_REVIEW_OPENSSL_PATH),
                "pkeyutl", "-sign", "-inkey", str(self.private_key), "-rawin",
                "-in", str(content), "-out", str(signature),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        value["signature_base64"] = base64.b64encode(signature.read_bytes()).decode()
        return value

    def run_review(
        self,
        source: dict[str, object],
        *,
        mutate: dict[str, object] | None = None,
    ) -> dict[str, object]:
        review = self.signed_review_json(source, mutate=mutate)
        path = self.write_json(f"{review['record_id']}.json", review)
        args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "adaptive-decision-review",
                "--target-thread", self.target, "--review-json", str(path),
            ]
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH", self.public_key
            ),
            mock.patch.object(
                supervision_log,
                "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256",
                self.public_key_sha,
            ),
            redirect_stdout(output),
        ):
            supervision_log.cmd_adaptive_decision_review(args)
        return json.loads(output.getvalue())

    def test_new_policy_defaults_to_full_autonomous_with_sealed_effect_ceilings(self) -> None:
        policy = self.init()
        self.assertEqual(
            policy["adaptive_decision_control"]["adaptive_decision_mode"],
            "full-autonomous",
        )
        self.assertEqual(policy["adaptive_decision_control"]["target_class"], "target-repository")
        for field in (
            "production_promotion", "release", "deployment", "destructive_action",
            "spend", "credential_access", "external_action",
        ):
            self.assertIs(policy["permissions"][field], False)
        supervision_log.validate_policy(policy)
        invalid_args = supervision_log.parser().parse_args(
            [
                "--root", str(self.root), "init",
                "--target-thread", "invalid-root-target-1234",
                "--target-label", "Invalid root fixture",
                "--watcher-thread", "watcher-invalid-1234",
                "--reviewer-thread", "reviewer-invalid-1234",
                "--mission-source-class", "direct-user",
                "--mission-source-record", "direct-invalid-1234",
                "--mission-source-sha256", "d" * 64,
                "--adaptive-target-repository-root", "/",
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "not canonical"
        ):
            supervision_log.cmd_init(invalid_args)
        for field, value in (
            ("--candidate-max-files", "4"),
            ("--candidate-max-commands", "7"),
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "Adaptive candidate budget .* is invalid",
            ):
                self.adjust(field, value)

    def test_legacy_policy_stays_fixed_until_explicit_migration(self) -> None:
        policy = self.policy()
        del policy["adaptive_decision_control"]
        result = self.posture(policy, self.packet(policy))
        self.assertEqual(result["adaptive_decision_mode"], "fixed")
        self.assertEqual(result["application_posture"], "record-only")
        self.assertTrue(result["legacy_policy_posture"])

    def test_modes_preserve_application_and_review_boundaries(self) -> None:
        fixed_policy = self.policy("fixed")
        source = self.decision_evidence()
        fixed = self.posture(
            fixed_policy, self.packet(fixed_policy, evidence=source)
        )
        self.assertEqual(fixed["application_posture"], "record-only")
        recommend = self.policy("recommend")
        pending = self.posture(
            recommend, self.packet(recommend, evidence=source)
        )
        self.assertEqual(pending["application_posture"], "automated-independent-review-required")
        reviewed = self.posture(
            recommend,
            self.packet(
                recommend,
                evidence=source,
                review=self.normalized_review(recommend, source),
            ),
        )
        self.assertEqual(reviewed["application_posture"], "recommendation-only")
        full = self.policy()
        applied = self.posture(
            full, self.packet(full, evidence=source)
        )
        self.assertFalse(applied["application_authorized"])
        self.assertTrue(applied["application_ready"])
        self.assertEqual(applied["application_posture"], "owner-application-ready")
        self.assertRegex(str(applied["application_precondition_root"]), r"^[0-9a-f]{64}$")
        reviewed_policy = self.policy("reviewed-autonomous")
        consequential = self.decision_evidence(consequence_class="consequential")
        held = self.posture(
            reviewed_policy,
            self.packet(reviewed_policy, evidence=consequential),
        )
        self.assertEqual(held["application_posture"], "external-application-authority-required")

    def test_full_autonomy_never_routes_ordinary_judgment_to_a_human(self) -> None:
        policy = self.policy()
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "forbids a human"):
            self.posture(
                policy, self.packet(policy, request_human_input=True)
            )
        notification = supervision_log.decision_notification(
            {
                "adaptive_decision_control": supervision_log.adaptive_decision_control_contract(),
                "notifications": {"gmail_priority": {"enabled": True}},
            },
            [],
            {"record_id": "EVT-000001", "classification": "human-preference", "phase": "attempt-unresolved", "attempt": 1},
            "start-sol-max-attempt",
        )
        self.assertFalse(notification["notification_send_now"])
        reserved = self.decision_evidence(
            judgment_class="reserved-external",
            blocked_subjects=["credential-boundary"],
            revisit_trigger="Credential authority becomes current.",
        )
        posture = self.posture(
            policy, self.packet(policy, evidence=reserved)
        )
        self.assertEqual(posture["application_posture"], "reserved-external")
        self.assertEqual(posture["human_request_count"], 0)

    def test_effect_class_is_policy_derived_and_permission_specific(self) -> None:
        policy = self.policy()
        candidate = self.candidate()
        source = self.decision_evidence(
            disposition="cutover-candidate",
            candidate_evidence_root=str(candidate["evidence_root"]),
            blocked_subjects=["production-promotion"],
            revisit_trigger="Production promotion authority becomes current.",
        )
        review = self.normalized_review(policy, source, candidate=candidate)
        result = self.posture(
            policy, self.packet(policy, evidence=source, candidate=candidate, review=review)
        )
        self.assertEqual(result["effect_class"], "production-cutover")
        self.assertFalse(result["permission_results"]["production_promotion"])
        self.assertEqual(result["application_posture"], "reserved-external")
        parser = supervision_log.parser()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "adaptive-decision-gate", "--target-thread", self.target,
                    "--decision-evidence", "decision.json", "--effect-class", "implementation-write",
                ]
            )

    def test_candidate_evidence_is_canonical_owner_current_and_budget_bound(self) -> None:
        candidate = self.candidate()
        path = self.write_json("candidate.json", candidate)
        loaded = supervision_log.load_adaptive_candidate_evidence(
            str(path),
            decision_evidence=self.decision_evidence(
                disposition="compare-candidate",
                candidate_evidence_root=str(candidate["evidence_root"]),
            ),
        )
        self.assertEqual(loaded["evidence_root"], candidate["evidence_root"])
        retained_decision = self.decision_evidence(
            disposition="compare-candidate",
            candidate_evidence_root=str(candidate["evidence_root"]),
        )
        with mock.patch.object(
            Path,
            "read_bytes",
            side_effect=AssertionError("unfenced candidate source reopen"),
        ):
            artifacts, _commands, _comparisons, _usage = (
                supervision_log.adaptive_candidate_retained_evidence(
                    candidate,
                    decision_evidence=retained_decision,
                )
            )
        self.assertEqual(artifacts[0]["before_root"], candidate["artifact_manifest"][0]["before_root"])
        path.write_bytes(supervision_log.canonical(candidate) + b" \n")
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "exact canonical"):
            supervision_log.load_adaptive_candidate_evidence(
                str(path),
                decision_evidence=self.decision_evidence(
                    disposition="compare-candidate",
                    candidate_evidence_root=str(candidate["evidence_root"]),
                ),
            )
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "owner differs"):
            supervision_log.validate_adaptive_candidate_evidence(
                self.candidate(owner_id="invented-owner-1234"),
                decision_evidence=self.decision_evidence(
                    disposition="compare-candidate",
                    candidate_evidence_root=str(candidate["evidence_root"]),
                ),
            )
        stale_source = self.candidate()
        stale_source["source_revision_root"] = "0" * 64
        stale_currentness = {
            "owner_id": stale_source["owner_id"],
            "source_revision_root": stale_source["source_revision_root"],
            "decision_basis_root": stale_source["decision_basis_root"],
            "candidate_root": stale_source["candidate_root"],
            "candidate_budget_use_root": stale_source["candidate_budget_use_root"],
            "protected_capability_root": stale_source["protected_capability_root"],
            "validation_root": stale_source["validation_root"],
            "comparison_root": stale_source["comparison_root"],
            "acceptance_root": stale_source["acceptance_root"],
        }
        stale_source["currentness_root"] = supervision_log.digest(stale_currentness)
        stale_material = dict(stale_source)
        stale_material.pop("evidence_root")
        stale_material.pop("decision_id")
        stale_material.pop("acceptance_signature_base64")
        stale_source["evidence_root"] = supervision_log.digest(stale_material)
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "source revision"):
            supervision_log.validate_adaptive_candidate_evidence(
                stale_source,
                decision_evidence=self.decision_evidence(
                    disposition="compare-candidate",
                    candidate_evidence_root=str(stale_source["evidence_root"]),
                ),
            )
        renamed = self.candidate()
        renamed["protected_capability_results"][0]["capability_id"] = "renamed-contract"  # type: ignore[index]
        renamed["protected_capability_root"] = supervision_log.digest(
            renamed["protected_capability_results"]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "decision contract"
        ):
            supervision_log.validate_adaptive_candidate_evidence(
                renamed,
                decision_evidence=self.decision_evidence(
                    disposition="compare-candidate",
                    candidate_evidence_root=str(renamed["evidence_root"]),
                ),
            )
        basis_candidate = self.candidate()
        changed_basis_source = self.decision_evidence(
            disposition="compare-candidate",
            candidate_evidence_root=str(basis_candidate["evidence_root"]),
        )
        changed_basis_source["capability_frame_root"] = "0" * 64
        changed_basis_source["block_contract_root"] = "1" * 64
        changed_basis_source["decision_target_state_root"] = "2" * 64
        changed_basis_source["affected_scope"][0]["content_root"] = "3" * 64  # type: ignore[index]
        changed_basis_material = dict(changed_basis_source)
        changed_basis_material.pop("source_root")
        changed_basis_source["source_root"] = supervision_log.digest(
            changed_basis_material
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "decision basis|canonical tracker|Block contract"
        ):
            self.posture(
                self.policy(),
                self.packet(
                    self.policy(),
                    evidence=changed_basis_source,
                    candidate=basis_candidate,
                ),
            )
        over = self.candidate()
        source = self.decision_evidence(
            disposition="compare-candidate", candidate_evidence_root=str(over["evidence_root"])
        )
        over_policy = self.policy()
        over_budget = dict(over_policy["adaptive_decision_control"]["candidate_budget"])  # type: ignore[index]
        over_budget["max_changed_lines"] = 1
        over_policy["adaptive_decision_control"] = supervision_log.adaptive_decision_control_contract(
            "full-autonomous",
            candidate_budget=over_budget,
            target_repository_root=self.repository_root,
        )
        result = self.posture(
            over_policy, self.packet(over_policy, evidence=source, candidate=over)
        )
        self.assertTrue(result["budget_exceeded"])
        self.assertEqual(result["application_posture"], "stop-and-retire-candidate")

    def test_candidate_chronology_is_bound_to_source_commit_and_current_time(self) -> None:
        for event_time in (
            self.target_committed_at - dt.timedelta(seconds=1),
            dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(minutes=5),
        ):
            candidate = self.candidate(event_time=event_time)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "lane chronology"
            ):
                supervision_log.validate_adaptive_candidate_evidence(
                    candidate,
                    decision_evidence=self.decision_evidence(
                        disposition="compare-candidate",
                        candidate_evidence_root=str(candidate["evidence_root"]),
                    ),
                )

    def test_protected_regression_stops_candidate_before_review(self) -> None:
        candidate = self.candidate(protected_result="regressed")
        source = self.decision_evidence(
            disposition="compare-candidate", candidate_evidence_root=str(candidate["evidence_root"])
        )
        result = self.posture(
            self.policy(), self.packet(self.policy(), evidence=source, candidate=candidate)
        )
        self.assertTrue(result["protected_regression"])
        self.assertEqual(result["application_posture"], "stop-and-retire-candidate")

    def test_source_protected_regression_stops_non_candidate_authorization(self) -> None:
        source = self.decision_evidence(disposition="correct-inline")
        source["protected_capability_results"].append(  # type: ignore[union-attr]
            {
                "capability_id": "supplemental-protected-1234",
                "result": "regressed",
                "evidence_ref_ids": ["supplemental-evidence-1234"],
            }
        )
        source["protected_capability_root"] = supervision_log.digest(
            source["protected_capability_results"]
        )
        material = dict(source)
        material.pop("source_root")
        source["source_root"] = supervision_log.digest(material)
        result = self.posture(
            self.policy(), self.packet(self.policy(), evidence=source)
        )
        self.assertTrue(result["protected_regression"])
        self.assertFalse(result["application_authorized"])
        self.assertEqual(result["application_posture"], "stop-protected-regression")

    def test_signed_review_is_source_bound_current_and_one_use(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source_evidence = self.decision_evidence(decision_id="signed-decision-1234")
        source = self.run_gate(self.gate_args(source_evidence))["record"]
        self.assertEqual(source["application_posture"], "automated-independent-review-required")
        review = self.run_review(source)["record"]
        self.assertEqual(review["decision_semantics_root"], source["decision_semantics_root"])
        applied = self.run_gate(
            self.gate_args(source_evidence, review_record=str(review["record_id"]), request_human=True)
        )["record"]
        self.assertEqual(applied["independent_review_record"], review["record_id"])
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "stale|already has"):
            self.run_review(source)

    def test_public_signer_reuses_clean_semantic_review_for_currentness_refresh(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        evidence = self.decision_evidence(decision_id="signer-owner-decision-1234")
        reviewed_source = self.run_gate(self.gate_args(evidence))["record"]
        directory = self.root / self.target
        existing = supervision_log.events(directory / "events.jsonl")
        semantic_review_record = f"EVT-{len(existing) + 1:06d}"
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": semantic_review_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "meta-review",
                "category": "implementation-range-owner",
                "status": "independent-review-clean-signature-unavailable",
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": reviewed_source["policy_sha256"],
                "evidence": [
                    reviewed_source["record_id"],
                    reviewed_source["record_sha256"],
                    "reviewer:base-reviewer-1234:turn-1234:item-1234",
                ],
            },
        )
        refreshed_source = self.run_gate(self.gate_args(evidence))["record"]
        self.assertNotEqual(
            refreshed_source["record_id"], reviewed_source["record_id"]
        )
        self.assertEqual(
            refreshed_source["decision_fingerprint"],
            reviewed_source["decision_fingerprint"],
        )
        self.assertNotEqual(
            refreshed_source["decision_semantics_root"],
            reviewed_source["decision_semantics_root"],
        )
        self.assertEqual(
            refreshed_source["decision_source_root"],
            reviewed_source["decision_source_root"],
        )
        output_path = self.root / "sealed-adaptive-review.json"
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-review-sign",
                "--target-thread",
                self.target,
                "--source-record",
                refreshed_source["record_id"],
                "--review-evidence-record",
                semantic_review_record,
                "--output-json",
                str(output_path),
            ]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            supervision_log.cmd_adaptive_decision_review_sign(args)
        signed = json.loads(output_path.read_bytes())
        signing_result = json.loads(output.getvalue())
        self.assertFalse(signing_result["duplicate"])
        self.assertEqual(
            signed["source_decision_record"], refreshed_source["record_id"]
        )
        self.assertEqual(
            signed["evidence_root"],
            supervision_log.events(directory / "events.jsonl")[-2]["record_sha256"],
        )
        supervision_log.validate_external_adaptive_review(
            signed,
            source=refreshed_source,
            policy=supervision_log.read_json(directory / "policy.json"),
        )
        import_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-review",
                "--target-thread",
                self.target,
                "--review-json",
                str(output_path),
            ]
        )
        imported_output = io.StringIO()
        with redirect_stdout(imported_output):
            supervision_log.cmd_adaptive_decision_review(import_args)
        imported = json.loads(imported_output.getvalue())["record"]
        self.assertEqual(
            imported["source_decision_record"], refreshed_source["record_id"]
        )
        self.assertEqual(imported["review_disposition"], "accepted")

    def test_public_signer_rejects_unreviewed_or_wrong_authority_material(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        evidence = self.decision_evidence(decision_id="signer-attack-decision-1234")
        source = self.run_gate(self.gate_args(evidence))["record"]
        directory = self.root / self.target
        existing = supervision_log.events(directory / "events.jsonl")
        evidence_record = f"EVT-{len(existing) + 1:06d}"
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "schema_version": 1,
                "record_id": evidence_record,
                "timestamp": supervision_log.utc_now(),
                "target_thread_id": self.target,
                "kind": "meta-review",
                "category": "implementation-range-owner",
                "status": "independent-review-rejected",
                "model": "gpt-5.6-sol",
                "reasoning": "max",
                "resolution_owner": "supervisor",
                "user_action_required": "no",
                "policy_sha256": source["policy_sha256"],
                "evidence": [
                    source["record_id"],
                    source["record_sha256"],
                    "reviewer:base-reviewer-1234:turn-1234:item-1234",
                ],
            },
        )
        refreshed = self.run_gate(self.gate_args(evidence))["record"]
        args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "adaptive-decision-review-sign",
                "--target-thread",
                self.target,
                "--source-record",
                refreshed["record_id"],
                "--review-evidence-record",
                evidence_record,
                "--output-json",
                str(self.root / "must-not-exist.json"),
            ]
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "accepted independent semantic review"
        ):
            supervision_log.cmd_adaptive_decision_review_sign(args)

    def test_fabricated_or_replayed_review_rejects(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        source_evidence = self.decision_evidence(decision_id="review-attack-decision")
        source = self.run_gate(self.gate_args(source_evidence))["record"]
        for mutation in (
            {"decision_id": "other-decision-1234"},
            {"decision_semantics_root": "0" * 64},
            {"candidate_owner_id": "invented-owner-1234"},
            {"reviewer_id": "invented-reviewer-1234"},
        ):
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError,
                "bind|authority|source|signature|shape",
            ):
                self.run_review(source, mutate=mutation)
        unsigned = self.signed_review_json(source)
        unsigned["signature_base64"] = base64.b64encode(b"x" * 64).decode()
        path = self.write_json("forged-review.json", unsigned)
        args = supervision_log.parser().parse_args(
            ["--root", str(self.root), "adaptive-decision-review", "--target-thread", self.target, "--review-json", str(path)]
        )
        with (
            mock.patch.object(supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_PATH", self.public_key),
            mock.patch.object(supervision_log, "ADAPTIVE_REVIEW_PUBLIC_KEY_SHA256", self.public_key_sha),
            self.assertRaisesRegex(supervision_log.SupervisionLogError, "signature"),
        ):
            supervision_log.cmd_adaptive_decision_review(args)

    def test_software_factory_public_review_persists_two_verified_authorities(self) -> None:
        self.init()
        self.adjust(
            "--adaptive-target-class",
            "software-factory",
            "--adaptive-decision-mode",
            "recommend",
        )
        evidence = self.decision_evidence(
            decision_id="factory-signed-decision-1234",
            target_class="software-factory",
        )
        source = self.run_gate(self.gate_args(evidence))["record"]
        review = self.run_review(source)["record"]
        self.assertEqual(review["reviewer_id"], supervision_log.ADAPTIVE_REVIEWER_ID)
        self.assertEqual(review["evaluator_id"], supervision_log.ADAPTIVE_EVALUATOR_ID)
        self.assertNotEqual(
            review["authority_key_sha256"],
            review["evaluator_authority_key_sha256"],
        )
        reviewed = self.run_gate(
            self.gate_args(evidence, review_record=str(review["record_id"]))
        )["record"]
        self.assertEqual(reviewed["independent_review_record"], review["record_id"])
        self.assertEqual(
            reviewed["independent_evaluation_root"], review["evaluation_root"]
        )
        self.assertEqual(reviewed["application_posture"], "recommendation-only")

    def test_post_review_candidate_or_decision_currentness_change_rejects(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        candidate = self.candidate(decision_id="candidate-review-1234")
        evidence = self.decision_evidence(
            decision_id="candidate-review-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(candidate["evidence_root"]),
        )
        source = self.run_gate(self.gate_args(evidence, candidate=candidate))["record"]
        review = self.run_review(source)["record"]
        changed_candidate = copy.deepcopy(candidate)
        changed_candidate["source_revision_root"] = "0" * 64
        changed_currentness = {
            "owner_id": changed_candidate["owner_id"],
            "source_revision_root": changed_candidate["source_revision_root"],
            "decision_basis_root": changed_candidate["decision_basis_root"],
            "candidate_root": changed_candidate["candidate_root"],
            "candidate_budget_use_root": changed_candidate["candidate_budget_use_root"],
            "protected_capability_root": changed_candidate["protected_capability_root"],
            "validation_root": changed_candidate["validation_root"],
            "comparison_root": changed_candidate["comparison_root"],
            "acceptance_root": changed_candidate["acceptance_root"],
        }
        changed_candidate["currentness_root"] = supervision_log.digest(changed_currentness)
        candidate_material = dict(changed_candidate)
        candidate_material.pop("evidence_root")
        candidate_material.pop("decision_id")
        candidate_material.pop("acceptance_signature_base64")
        changed_candidate["evidence_root"] = supervision_log.digest(candidate_material)
        changed_evidence = copy.deepcopy(evidence)
        changed_evidence["candidate_evidence_root"] = changed_candidate["evidence_root"]
        source_material = dict(changed_evidence)
        source_material.pop("source_root")
        changed_evidence["source_root"] = supervision_log.digest(source_material)
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
            "bind the current decision|canonical decision|source revision",
        ):
            self.run_gate(
                self.gate_args(
                    changed_evidence,
                    candidate=changed_candidate,
                    review_record=str(review["record_id"]),
                )
            )

    def test_cross_id_same_fingerprint_deduplicates_before_review_cycle(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        first = self.decision_evidence(decision_id="decision-one-1234")
        second = self.decision_evidence(decision_id="decision-two-1234")
        first_result = self.run_gate(self.gate_args(first))
        second_result = self.run_gate(self.gate_args(second))
        self.assertFalse(first_result["duplicate"])
        self.assertTrue(second_result["duplicate"])
        self.assertEqual(second_result["record"]["decision_id"], "decision-one-1234")
        events = [
            json.loads(line)
            for line in (self.root / self.target / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        self.assertEqual(sum(item.get("kind") == "adaptive-decision" for item in events), 1)
        self.assertEqual(sum(item.get("kind") == "adaptive-decision-review" for item in events), 0)
        changed_semantics = self.decision_evidence(
            decision_id="decision-three-1234", consequence_class="consequential"
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "canonical decision ID"
        ):
            self.run_gate(self.gate_args(changed_semantics))
        candidate_one = self.candidate(decision_id="candidate-one-1234")
        candidate_two = self.candidate(decision_id="candidate-two-1234")
        self.assertEqual(candidate_one["evidence_root"], candidate_two["evidence_root"])
        candidate_source_one = self.decision_evidence(
            decision_id="candidate-one-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(candidate_one["evidence_root"]),
        )
        candidate_source_two = self.decision_evidence(
            decision_id="candidate-two-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(candidate_two["evidence_root"]),
        )
        first_candidate = self.run_gate(
            self.gate_args(candidate_source_one, candidate=candidate_one)
        )
        second_candidate = self.run_gate(
            self.gate_args(candidate_source_two, candidate=candidate_two)
        )
        self.assertFalse(first_candidate["duplicate"])
        self.assertTrue(second_candidate["duplicate"])
        self.assertEqual(
            second_candidate["record"]["decision_id"], "candidate-one-1234"
        )

    def test_fingerprint_is_recomputed_from_exact_evidence_not_caller_sha(self) -> None:
        policy = self.policy()
        for field in ("accepted_decision_head", "accepted_revision_head"):
            invented_head = self.decision_evidence()
            invented_head[field] = "9" * 64
            material = dict(invented_head)
            material.pop("source_root")
            invented_head["source_root"] = supervision_log.digest(material)
            with self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "canonical owner"
            ):
                supervision_log.validate_adaptive_decision_evidence(
                    invented_head, policy=policy
                )
        first = self.posture(
            policy, self.packet(policy, evidence=self.decision_evidence(decision_id="decision-one-1234"))
        )
        same = self.posture(
            policy, self.packet(policy, evidence=self.decision_evidence(decision_id="decision-two-1234"))
        )
        changed = self.posture(
            policy,
            self.packet(
                policy,
                evidence=self.decision_evidence(decision_id="decision-three-1234", evidence_root="0" * 64),
            ),
        )
        self.assertEqual(first["decision_fingerprint"], same["decision_fingerprint"])
        self.assertNotEqual(first["decision_fingerprint"], changed["decision_fingerprint"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            supervision_log.parser().parse_args(
                [
                    "adaptive-decision-gate", "--target-thread", self.target,
                    "--decision-evidence", "decision.json", "--state-fingerprint", "f" * 64,
                ]
            )

    def test_software_factory_inline_change_requires_review_and_evaluation(self) -> None:
        policy = self.policy(target_class="software-factory")
        policy["permissions"]["allowlisted_skill_maintenance"] = True
        evidence = self.decision_evidence(target_class="software-factory")
        pending = self.posture(
            policy, self.packet(policy, evidence=evidence)
        )
        self.assertTrue(pending["independent_review_required"])
        self.assertEqual(pending["application_posture"], "automated-independent-review-required")
        review = self.normalized_review(policy, evidence)
        applied = self.posture(
            policy, self.packet(policy, evidence=evidence, review=review)
        )
        self.assertFalse(applied["application_authorized"])
        self.assertTrue(applied["application_ready"])
        self.assertEqual(applied["application_posture"], "owner-application-ready")
        reviewer_rewrites_evaluator = copy.deepcopy(review)
        reviewer_rewrites_evaluator["evaluation_disposition"] = "rejected"
        reviewer_rewrites_evaluator["evaluation_root"] = supervision_log.digest(
            supervision_log.adaptive_external_evaluation_root_material(
                reviewer_rewrites_evaluator
            )
        )
        reviewer_rewrites_evaluator = self.sign_outer_review(
            reviewer_rewrites_evaluator
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "evaluation signature"
        ):
            self.posture(
                policy,
                self.packet(
                    policy,
                    evidence=evidence,
                    review=reviewer_rewrites_evaluator,
                ),
            )
        bad = copy.deepcopy(review)
        bad["evaluator_id"] = bad["reviewer_id"]
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "evaluator|roles are not distinct"
        ):
            self.posture(
                policy, self.packet(policy, evidence=evidence, review=bad)
            )
        unsigned = {
            "record_id": "unsigned-review-1234",
            "source_decision_record": "source-decision-1234",
            "source_decision_sha256": "1" * 64,
            "decision_id": pending["decision_id"],
            "decision_fingerprint": pending["decision_fingerprint"],
            "decision_currentness_root": pending["decision_currentness_root"],
            "decision_semantics_root": pending["decision_semantics_root"],
            "disposition": pending["disposition"],
            "target_class": pending["target_class"],
            "effect_class": pending["effect_class"],
            "candidate_evidence_root": None,
            "candidate_owner_id": None,
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "evaluator_id": supervision_log.ADAPTIVE_EVALUATOR_ID,
            "evaluation_evidence_root": "4" * 64,
            "review_disposition": "accepted",
            "evaluation_disposition": "accepted",
            "evidence_root": "2" * 64,
            "review_root": "3" * 64,
            "authority_key_sha256": self.public_key_sha,
            "policy_sha256": policy["policy_sha256"],
        }
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "shape"):
            self.posture(
                policy, self.packet(policy, evidence=evidence, review=unsigned)
            )

    def test_structural_target_class_change_requires_evidence_and_is_append_only(self) -> None:
        initial = self.init()
        initial_permissions = copy.deepcopy(initial["permissions"])
        first_history = (self.root / self.target / "policy-history.jsonl").read_bytes()
        adjusted = self.adjust(
            "--adaptive-target-class", "software-factory",
            "--adaptive-decision-mode", "reviewed-autonomous",
        )
        self.assertEqual(adjusted["permissions"], initial_permissions)
        self.assertEqual(adjusted["adaptive_decision_control"]["target_class"], "software-factory")
        self.assertTrue((self.root / self.target / "policy-history.jsonl").read_bytes().startswith(first_history))
        other_repository = self.root / "other-repository"
        other_repository.mkdir()
        subprocess.run(
            ["/usr/bin/git", "-C", str(other_repository), "init", "-q"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "repository root is immutable"
        ):
            self.adjust(
                "--adaptive-target-repository-root",
                str(other_repository.resolve()),
            )

    def test_status_reports_adaptive_and_legacy_human_requests_truthfully(self) -> None:
        policy = self.policy("recommend")
        evidence = self.decision_evidence()
        review = self.normalized_review(policy, evidence)
        result = self.posture(
            policy,
            self.packet(policy, evidence=evidence, review=review, request_human_input=True),
        )
        events = [
            {"kind": "adaptive-decision", **result},
            {"kind": "decision", "decision_id": "legacy-decision-1234", "human_input_requested_at": "2026-08-09T00:00:00+00:00", "policy_sha256": "0" * 64},
        ]
        status = supervision_log.adaptive_status_projection(policy, events)
        self.assertEqual(status["human_request_count"], 2)
        self.assertEqual(status["adaptive_human_request_count"], 1)
        self.assertEqual(status["legacy_decision_human_request_count"], 1)

    def test_exact_decision_source_rejects_tamper_duplicate_keys_and_scope_escape(self) -> None:
        policy = self.policy()
        value = self.decision_evidence()
        value["source_root"] = "0" * 64
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "source root"):
            supervision_log.validate_adaptive_decision_evidence(value, policy=policy)
        escaped = self.decision_evidence()
        escaped["affected_scope"][0]["path"] = f"{self.repository_root}/../outside.py"  # type: ignore[index]
        material = dict(escaped)
        material.pop("source_root")
        escaped["source_root"] = supervision_log.digest(material)
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "normalized"):
            supervision_log.validate_adaptive_decision_evidence(escaped, policy=policy)
        widened = self.decision_evidence()
        widened["target_repository_root"] = "/"
        widened_material = dict(widened)
        widened_material.pop("source_root")
        widened["source_root"] = supervision_log.digest(widened_material)
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "canonical policy"):
            supervision_log.validate_adaptive_decision_evidence(widened, policy=policy)
        outside = self.root / "outside"
        outside.mkdir()
        link = Path(self.repository_root) / "linked-outside"
        link.symlink_to(outside, target_is_directory=True)
        linked = self.decision_evidence()
        linked["affected_scope"][0]["path"] = str(link / "owned.py")  # type: ignore[index]
        linked_material = dict(linked)
        linked_material.pop("source_root")
        linked["source_root"] = supervision_log.digest(linked_material)
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "escapes|symlink"):
            supervision_log.validate_adaptive_decision_evidence(linked, policy=policy)
        duplicate_path = self.root / "duplicate.json"
        duplicate_path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
        with self.assertRaisesRegex(supervision_log.SupervisionLogError, "Duplicate"):
            supervision_log.load_bounded_canonical_json(
                str(duplicate_path), label="adaptive decision evidence", maximum_bytes=1024
            )

    def test_live_git_tracker_file_and_candidate_acceptance_currentness_fail_closed(self) -> None:
        policy = self.policy()
        current = self.decision_evidence()
        self.owned_path.write_text("VALUE = 9\n", encoding="utf-8")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "content is stale"
        ):
            supervision_log.validate_adaptive_decision_evidence(current, policy=policy)
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "checkout", "--", "owned.py"],
            check=True,
        )
        tracker_current = self.decision_evidence()
        self.tracker_path.write_text(
            self.tracker_path.read_text(encoding="utf-8") + "\nUnaccepted mutation.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "tracker is stale"
        ):
            supervision_log.validate_adaptive_decision_evidence(
                tracker_current, policy=policy
            )
        subprocess.run(
            ["/usr/bin/git", "-C", self.repository_root, "checkout", "--", "tracker.md"],
            check=True,
        )
        candidate = self.candidate()
        candidate["acceptance_signature_base64"] = base64.b64encode(b"x" * 64).decode()
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "acceptance signature"
        ):
            supervision_log.validate_adaptive_candidate_evidence(
                candidate,
                decision_evidence=self.decision_evidence(
                    disposition="compare-candidate",
                    candidate_evidence_root=str(candidate["evidence_root"]),
                ),
            )

    def test_public_gate_rechecks_live_target_inside_append_boundary(self) -> None:
        self.init()
        directory = self.root / self.target
        policy = json.loads((directory / "policy.json").read_text(encoding="utf-8"))
        policy["permissions"]["repository_write"] = True
        supervision_log.write_policy_version(
            directory,
            policy,
            kind="policy-change",
            reason="Enable the append-currentness fixture.",
            evidence_values=["append-currentness-regression"],
        )
        evidence = self.decision_evidence(decision_id="append-currentness-1234")
        original = supervision_log.validate_adaptive_decision_evidence
        calls = 0

        def validate_with_drift(value, *, policy):
            nonlocal calls
            calls += 1
            if calls == 3:
                self.owned_path.write_text("VALUE = 99\n", encoding="utf-8")
            return original(value, policy=policy)

        with (
            mock.patch.object(
                supervision_log,
                "validate_adaptive_decision_evidence",
                side_effect=validate_with_drift,
            ),
            self.assertRaisesRegex(
                supervision_log.SupervisionLogError, "content is stale|retry current"
            ),
        ):
            self.run_gate(self.gate_args(evidence))
        event_path = directory / "events.jsonl"
        events = (
            [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
            if event_path.exists()
            else []
        )
        self.assertEqual(
            sum(item.get("kind") == "adaptive-decision" for item in events), 0
        )

    def test_post_recheck_target_drift_never_appends_write_authority(self) -> None:
        self.init()
        directory = self.root / self.target
        policy = json.loads((directory / "policy.json").read_text(encoding="utf-8"))
        policy["permissions"]["repository_write"] = True
        supervision_log.write_policy_version(
            directory,
            policy,
            kind="policy-change",
            reason="Enable the post-recheck currentness fixture.",
            evidence_values=["post-recheck-currentness-regression"],
        )
        evidence = self.decision_evidence(decision_id="post-recheck-drift-1234")
        original = supervision_log.validate_adaptive_decision_evidence
        calls = 0

        def validate_then_drift(value, *, policy):
            nonlocal calls
            calls += 1
            result = original(value, policy=policy)
            if calls == 3:
                self.owned_path.write_text("VALUE = 99\n", encoding="utf-8")
            return result

        with mock.patch.object(
            supervision_log,
            "validate_adaptive_decision_evidence",
            side_effect=validate_then_drift,
        ):
            record = self.run_gate(self.gate_args(evidence))["record"]
        self.assertEqual(calls, 3)
        self.assertFalse(record["application_authorized"])
        self.assertTrue(record["application_ready"])
        self.assertEqual(record["application_posture"], "owner-application-ready")
        self.assertRegex(str(record["application_precondition_root"]), r"^[0-9a-f]{64}$")
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "content is stale|target state"
        ):
            supervision_log.validate_adaptive_decision_evidence(
                evidence,
                policy=json.loads(
                    (directory / "policy.json").read_text(encoding="utf-8")
                ),
            )

    def test_canonical_event_frontier_rejects_two_distinct_active_candidate_lanes(self) -> None:
        direct_candidate = self.candidate(decision_id="direct-lane-bypass-1234")
        direct_source = self.decision_evidence(
            decision_id="direct-lane-bypass-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(direct_candidate["evidence_root"]),
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "canonical owner-bound"
        ):
            supervision_log.adaptive_decision_posture(
                self.policy(),
                self.packet(
                    self.policy(), evidence=direct_source, candidate=direct_candidate
                ),
            )
        forged_policy = self.policy()
        forged_policy["permissions"]["repository_write"] = True
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "canonical owner-bound"
        ):
            supervision_log.adaptive_decision_posture(
                forged_policy,
                self.packet(
                    forged_policy,
                    evidence=self.decision_evidence(
                        decision_id="direct-policy-bypass-1234"
                    ),
                ),
            )
        self.init()
        directory = self.root / self.target
        bound_policy = json.loads(
            (directory / "policy.json").read_text(encoding="utf-8")
        )
        bound_policy["permissions"]["repository_write"] = True
        bound_policy["permissions"]["command_or_test_execution"] = True
        supervision_log.write_policy_version(
            directory,
            bound_policy,
            kind="policy-change",
            reason="Enable the bounded candidate fixture.",
            evidence_values=["active-lane-regression"],
        )
        first = self.candidate(decision_id="active-lane-one-1234")
        first_source = self.decision_evidence(
            decision_id="active-lane-one-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(first["evidence_root"]),
        )
        self.assertFalse(
            self.run_gate(self.gate_args(first_source, candidate=first))["duplicate"]
        )
        second = self.candidate(
            decision_id="active-lane-two-1234", after_text="VALUE = 3\n"
        )
        second_source = self.decision_evidence(
            decision_id="active-lane-two-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(second["evidence_root"]),
        )
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "different active candidate lane"
        ):
            self.run_gate(self.gate_args(second_source, candidate=second))
        events = [
            json.loads(line)
            for line in (self.root / self.target / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        self.assertEqual(
            sum(
                item.get("kind") == "adaptive-decision"
                and item.get("candidate_evidence_root") is not None
                for item in events
            ),
            1,
        )

    def test_mission_successor_scopes_adaptive_history_and_keeps_activation_gate(self) -> None:
        self.init()
        self.adjust("--adaptive-decision-mode", "recommend")
        directory = self.root / self.target
        old_candidate = self.candidate(decision_id="old-mission-candidate-1234")
        old_source = self.decision_evidence(
            decision_id="old-mission-candidate-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(old_candidate["evidence_root"]),
        )
        pending = self.run_gate(
            self.gate_args(old_source, candidate=old_candidate)
        )["record"]
        old_review = self.run_review(pending)["record"]
        reviewed = self.run_gate(
            self.gate_args(
                old_source,
                candidate=old_candidate,
                review_record=str(old_review["record_id"]),
            )
        )["record"]
        self.assertEqual(reviewed["application_posture"], "recommendation-only")
        old_policy = json.loads((directory / "policy.json").read_text(encoding="utf-8"))
        old_mission_root = old_policy["mission_binding"]["mission_root"]
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "record_id": "EVT-OLD-MISSION-COMPLETED",
                "target_thread_id": self.target,
                "kind": "lifecycle",
                "status": "completed",
                "policy_sha256": old_policy["policy_sha256"],
            },
        )
        successor_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "mission-successor",
                "--target-thread",
                self.target,
                "--from-mission-root",
                str(old_mission_root),
                "--mission-source-class",
                "direct-user",
                "--mission-source-record",
                "item-new-mission-1234",
                "--mission-source-sha256",
                "b" * 64,
                "--predecessor-disposition",
                "completed",
                "--first-eligible-work",
                "Block 7 current work",
                "--reason",
                "The completed predecessor is replaced by current direct authority.",
                "--evidence",
                "item-new-mission-1234",
            ]
        )
        successor_output = io.StringIO()
        with redirect_stdout(successor_output):
            supervision_log.cmd_mission_successor(successor_args)
        successor = json.loads(successor_output.getvalue())
        self.assertEqual(successor["mission_activation"]["phase"], "pending")
        self.assertEqual(
            successor["policy"]["adaptive_decision_control"],
            old_policy["adaptive_decision_control"],
        )

        new_candidate = self.candidate(
            decision_id="new-mission-candidate-1234", after_text="VALUE = 3\n"
        )
        new_source = self.decision_evidence(
            decision_id="new-mission-candidate-1234",
            disposition="compare-candidate",
            candidate_evidence_root=str(new_candidate["evidence_root"]),
        )
        new_pending = self.run_gate(
            self.gate_args(new_source, candidate=new_candidate)
        )
        self.assertFalse(new_pending["duplicate"])

        status_args = supervision_log.parser().parse_args(
            ["--root", str(self.root), "status", "--target-thread", self.target]
        )
        status_output = io.StringIO()
        with redirect_stdout(status_output):
            supervision_log.cmd_status(status_args)
        status = json.loads(status_output.getvalue())
        adaptive = status["adaptive_decision_control"]
        self.assertEqual(adaptive["decision_count"], 1)
        self.assertEqual(adaptive["independent_review_count"], 0)
        self.assertEqual(
            adaptive["last_decision"]["decision_id"], "new-mission-candidate-1234"
        )
        self.assertEqual(len(status["open_mission_activations"]), 1)
        all_events = supervision_log.events(directory / "events.jsonl")
        self.assertGreater(
            sum(item.get("kind") == "adaptive-decision" for item in all_events),
            adaptive["decision_count"],
        )
        self.assertIn(old_review, all_events)

        new_policy = json.loads((directory / "policy.json").read_text(encoding="utf-8"))
        supervision_log.append_raw(
            directory / "events.jsonl",
            {
                "record_id": "EVT-NEW-MISSION-PREMATURE-COMPLETION",
                "target_thread_id": self.target,
                "kind": "lifecycle",
                "status": "completed",
                "policy_sha256": new_policy["policy_sha256"],
            },
        )
        lifecycle_args = supervision_log.parser().parse_args(
            [
                "--root",
                str(self.root),
                "lifecycle-gate",
                "--target-thread",
                self.target,
                "--lifecycle-state",
                "completed",
                "--source-record",
                "EVT-NEW-MISSION-PREMATURE-COMPLETION",
            ]
        )
        lifecycle_output = io.StringIO()
        with redirect_stdout(lifecycle_output):
            supervision_log.cmd_lifecycle_gate(lifecycle_args)
        lifecycle = json.loads(lifecycle_output.getvalue())
        self.assertFalse(lifecycle["source_stop_permitted"])
        self.assertNotEqual(lifecycle["completion_action"], "record-completed-lifecycle")
        self.assertEqual(len(lifecycle["open_mission_activations"]), 1)

    def test_software_factory_role_identities_are_event_and_signature_bound(self) -> None:
        policy = self.policy(target_class="software-factory")
        policy["permissions"]["allowlisted_skill_maintenance"] = True
        evidence = self.decision_evidence(target_class="software-factory")
        pending = self.posture(
            policy, self.packet(policy, evidence=evidence)
        )
        self.assertEqual(pending["proposer_author_id"], "base-reviewer-1234")
        self.assertEqual(pending["implementation_owner_id"], self.target)
        source = {**pending, "record_id": "role-source-1234", "record_sha256": "1" * 64}
        review = self.signed_review_json(source)
        self.assertEqual(review["proposer_author_id"], "base-reviewer-1234")
        self.assertEqual(review["implementation_owner_id"], self.target)
        changed = copy.deepcopy(review)
        changed["proposer_author_id"] = "fabricated-proposer-1234"
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError, "bind the source decision|signature"
        ):
            supervision_log.validate_external_adaptive_review(
                changed, source=source, policy=policy
            )

    def test_cli_and_docs_expose_decision_evidence_signed_review_and_input_avoidance(self) -> None:
        parsed = supervision_log.parser().parse_args(
            [
                "adaptive-decision-gate", "--target-thread", self.target,
                "--decision-evidence", "decision.json",
            ]
        )
        self.assertEqual(parsed.command, "adaptive-decision-gate")
        signer = supervision_log.parser().parse_args(
            [
                "adaptive-decision-review-sign",
                "--target-thread",
                self.target,
                "--source-record",
                "EVT-000123",
                "--review-evidence-record",
                "EVT-000124",
                "--output-json",
                "/tmp/adaptive-review.json",
            ]
        )
        self.assertEqual(signer.command, "adaptive-decision-review-sign")
        text = MODULE_PATH.parent.parent.joinpath("SKILL.md").read_text(encoding="utf-8")
        text += MODULE_PATH.parent.parent.joinpath("references", "supervision-policy.md").read_text(encoding="utf-8")
        for token in (
            "adaptive-decision-review", "adaptive-decision-review-sign",
            "--decision-evidence", "--review-json", "--review-evidence-record",
            "adaptive-target-class", "adaptive-target-repository-root",
            "separately signed", "full-autonomous",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
