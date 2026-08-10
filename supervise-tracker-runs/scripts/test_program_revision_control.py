#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SUPPORT_PATH = Path(__file__).with_name("test_adaptive_decision_policy.py")
SUPPORT_SPEC = importlib.util.spec_from_file_location(
    "program_revision_adaptive_support", SUPPORT_PATH
)
assert SUPPORT_SPEC is not None and SUPPORT_SPEC.loader is not None
support = importlib.util.module_from_spec(SUPPORT_SPEC)
SUPPORT_SPEC.loader.exec_module(support)
supervision_log = support.supervision_log
program_revision = supervision_log.program_revision_module()


class ProgramRevisionControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = support.AdaptiveDecisionPolicyTests(
            methodName="test_modes_preserve_application_and_review_boundaries"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
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
        self.policy = self.fixture.adjust(
            "--adaptive-target-class", "software-factory"
        )
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
        self.decision_evidence = self.structural_decision_evidence()
        pending = self.fixture.run_gate(
            self.fixture.gate_args(self.decision_evidence)
        )["record"]
        adaptive_review = self.fixture.run_review(pending)["record"]
        self.source = self.fixture.run_gate(
            self.fixture.gate_args(
                self.decision_evidence,
                review_record=str(adaptive_review["record_id"]),
            )
        )["record"]
        self.packet = self.build_packet()
        self.packet_path = self.fixture.write_json("program-revision.json", self.packet)

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

{sections}
""".format(
                terminal=len(blocks) - 1,
                rows="\n".join(rows),
                sections="\n---\n\n".join(sections),
            ),
            encoding="utf-8",
        )

    def structural_decision_evidence(self) -> dict[str, object]:
        value = self.fixture.decision_evidence(
            decision_id="program-revision-decision-1234",
            disposition="amend-structure",
            target_class="software-factory",
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

    def build_packet(self) -> dict[str, object]:
        mission = supervision_log.bound_mission(self.policy)
        assert mission is not None
        metadata = {
            "revision_id": "PROGRAM-REVISION-1234",
            "target_thread_id": self.fixture.target,
            "target_class": "software-factory",
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
            "author_id": self.fixture.target,
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
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
                "7": [7, 8],
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
            "reviewer_id": supervision_log.ADAPTIVE_REVIEWER_ID,
            "disposition": disposition,
            "finding_refs": [] if disposition == "accepted" else ["FINDING-1234"],
            "evidence_root": program_revision.digest(
                {"packet_root": self.packet["packet_root"], "disposition": disposition}
            ),
            "authority_key_sha256": self.fixture.public_key_sha,
            "review_root": "",
            "signature_base64": "",
        }
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
        self.assertEqual(accepted["record"]["review_disposition"], "accepted")
        self.fixture.tracker_path.write_bytes(self.proposal.read_bytes())
        with self.assertRaisesRegex(
            supervision_log.SupervisionLogError,
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
        self.source = self.fixture.run_gate(
            self.fixture.gate_args(
                self.decision_evidence,
                review_record=str(adaptive_review["record_id"]),
            )
        )["record"]
        self.packet = self.build_packet()
        self.packet_path.write_bytes(program_revision.canonical(self.packet) + b"\n")
        accepted = self.record_program_revision()
        application_commit = self.apply_proposal()
        amended = self.range_amend(
            str(accepted["record"]["record_id"]), application_commit
        )
        self.assertFalse(amended["contraction"])
        self.assertEqual(amended["binding"]["explicit_blocks"], [7, 8])


if __name__ == "__main__":
    unittest.main()
