#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("program_revision.py")
SPEC = importlib.util.spec_from_file_location("program_revision", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
program_revision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(program_revision)


class ProgramRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.previous = self.root / "tracker.md"
        self.proposed = self.root / "proposal.md"
        self.write_tracker(
            self.previous,
            [
                ("Foundation", [], "completed"),
                ("Accepted owner", [0], "completed"),
                ("Active work", [1], "in-progress"),
                ("Independent later work", [1], "not-started"),
            ],
        )
        self.write_tracker(
            self.proposed,
            [
                ("Foundation", [], "completed"),
                ("Accepted owner", [0], "completed"),
                ("New prerequisite", [1], "not-started"),
                ("Revised active work", [2], "in-progress"),
                ("Independent later work", [1], "not-started"),
            ],
        )

    def write_tracker(
        self, path: Path, blocks: list[tuple[str, list[int], str]]
    ) -> None:
        rows = []
        sections = []
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
- Potential capability loss or regression: a malformed change could lose current behavior.
- Protected-capability effect: preserve accepted evidence and current owners.
- Architecture and operating-model effect: reuse the existing tracker owner.
- Tradeoff and source evidence: the bounded fixture supplies the exact changed structure.

### Inputs and dependencies

- Current tracker evidence.

### Required work

- Implement only {title.lower()}.

### Scope and non-goals

- In scope: {title.lower()}.
- Not in scope: unrelated work.

### Deliverables and recorded state

- Exact {title.lower()} evidence.

### Resource and economy contract

Reuse the current tracker snapshot once.

### QA and independent review

Run focused verification and exact review.

### Acceptance

- {title} is current.

### Negative tests

- Reject stale evidence.

### Completion evidence

{evidence}

### Stop

Stop before the next Block.
"""
            )
        path.write_text(
            """# Program revision fixture

- Tracker sequence: Blocks 0–{terminal}

## Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: the fixture changes an active tracker contract.
- Direct product sources: exact predecessor and proposed tracker bytes.
- Product thesis and intended effect: preserve history while revising open work.
- Protected capabilities: accepted Blocks and dependency-safe continuation.
- Architecture strategy: reuse the tracker author and structural verifier.
- Requested capability: one exact structural revision.
- Proportionality: inspect only changed Blocks and descendants.
- Tradeoffs: structural review is reserved for invalidated program contracts.
- Uncertainty: semantic review remains independent.

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

    def metadata(self, mapping: dict[str, list[int]] | None = None) -> dict[str, object]:
        return {
            "revision_id": "REV-STRUCTURAL-0001",
            "target_thread_id": "target-thread-1234",
            "target_class": "software-factory",
            "mission_root": "1" * 64,
            "policy_sha256": "2" * 64,
            "decision_record_id": "EVT-000101",
            "decision_record_sha256": "3" * 64,
            "decision_fingerprint": "4" * 64,
            "decision_currentness_root": "5" * 64,
            "application_precondition_root": "6" * 64,
            "candidate_evidence_root": None,
            "decision_target_state_root": "a" * 64,
            "current_target_state_root": "a" * 64,
            "repository_root": str(self.root),
            "target_revision": "source-commit-1234",
            "target_revision_root": "7" * 64,
            "author_id": "tracker-author-1234",
            "reviewer_id": "tracker-reviewer-1234",
            "learned_fact_refs": ["FACT-STRUCTURE-0001"],
            "capability_effects": {
                "gains": ["dependency-safe active contract"],
                "protected": ["accepted Block history"],
                "losses": [],
            },
            "selected_path": "structural-authoring",
            "rejected_paths": ["inline-insufficient", "candidate-insufficient"],
            "proposed_mutations": ["split-active-block"],
            "preserved_work_refs": ["WORK-ACCEPTED-0001"],
            "invalidated_proof_refs": ["PROOF-OLD-ACTIVE-0001"],
            "authority_mode": "full-autonomous",
            "stop": "before-candidate-cutover",
            "block_number_map": mapping
            or {"0": [0], "1": [1], "2": [2, 3], "3": [4]},
        }

    def build(self) -> dict[str, object]:
        return program_revision.build_revision_packet(
            previous_tracker=self.previous,
            proposed_tracker=self.proposed,
            target_tracker_path=self.previous,
            metadata=self.metadata(),
        )

    def test_split_revision_preserves_history_and_derives_resume(self) -> None:
        packet = self.build()
        self.assertEqual(packet["accepted_history_blocks"], [0, 1])
        self.assertEqual(packet["affected_previous_blocks"], [2])
        self.assertEqual(packet["affected_proposed_blocks"], [2, 3])
        self.assertEqual(packet["safe_frontier_blocks"], [4])
        self.assertEqual(packet["resume_block"], 2)
        rebuilt = program_revision.validate_revision_packet(
            packet,
            previous_tracker=self.previous,
            proposed_tracker=self.proposed,
        )
        self.assertEqual(rebuilt, packet)

    def test_local_or_status_only_change_cannot_escalate(self) -> None:
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "not a structural revision"
        ):
            program_revision.build_revision_packet(
                previous_tracker=self.previous,
                proposed_tracker=self.previous,
                target_tracker_path=self.previous,
                metadata=self.metadata(
                    {"0": [0], "1": [1], "2": [2], "3": [3]}
                ),
            )

    def test_accepted_history_rewrite_rejects(self) -> None:
        changed = self.proposed.read_text(encoding="utf-8").replace(
            "Accepted evidence for Accepted owner.",
            "Rewritten accepted evidence.",
        )
        self.proposed.write_text(changed, encoding="utf-8")
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "Accepted Block history was rewritten"
        ):
            self.build()

    def test_accepted_dependency_rewrite_rejects(self) -> None:
        self.write_tracker(
            self.proposed,
            [
                ("Foundation", [], "completed"),
                ("Accepted owner", [], "completed"),
                ("New prerequisite", [1], "not-started"),
                ("Revised active work", [2], "in-progress"),
                ("Independent later work", [1], "not-started"),
            ],
        )
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "Accepted Block history was rewritten"
        ):
            self.build()

    def test_accepted_scope_rewrite_rejects(self) -> None:
        changed = self.proposed.read_text(encoding="utf-8").replace(
            "| 1 | Accepted owner | 0 | `completed` |",
            "| 1 | Renamed accepted owner | 0 | `completed` |",
        )
        self.proposed.write_text(changed, encoding="utf-8")
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "Accepted Block history was rewritten"
        ):
            self.build()

    def test_merge_remove_and_reorder_open_blocks_are_mappable(self) -> None:
        self.write_tracker(
            self.proposed,
            [
                ("Foundation", [], "completed"),
                ("Accepted owner", [0], "completed"),
                ("Merged open work", [1], "in-progress"),
            ],
        )
        packet = program_revision.build_revision_packet(
            previous_tracker=self.previous,
            proposed_tracker=self.proposed,
            target_tracker_path=self.previous,
            metadata=self.metadata(
                {"0": [0], "1": [1], "2": [2], "3": [2]}
            ),
        )
        self.assertEqual(packet["affected_previous_blocks"], [2, 3])
        self.assertEqual(packet["affected_proposed_blocks"], [2])
        self.assertEqual(packet["resume_block"], 2)

    def test_missing_or_conflicting_mapping_rejects(self) -> None:
        for mapping in (
            {"0": [0], "1": [1], "2": [2, 3]},
            {"0": [0], "1": [1], "2": [9], "3": [4]},
        ):
            with self.subTest(mapping=mapping):
                with self.assertRaises(program_revision.ProgramRevisionError):
                    program_revision.build_revision_packet(
                        previous_tracker=self.previous,
                        proposed_tracker=self.proposed,
                        target_tracker_path=self.previous,
                        metadata=self.metadata(mapping),
                    )

    def test_packet_tamper_and_self_review_reject(self) -> None:
        packet = self.build()
        tampered = copy.deepcopy(packet)
        tampered["resume_block"] = 4
        tampered["packet_root"] = program_revision.digest(
            {key: value for key, value in tampered.items() if key != "packet_root"}
        )
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "differs from current sources"
        ):
            program_revision.validate_revision_packet(
                tampered,
                previous_tracker=self.previous,
                proposed_tracker=self.proposed,
            )
        metadata = self.metadata()
        metadata["reviewer_id"] = metadata["author_id"]
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "must differ"
        ):
            program_revision.build_revision_packet(
                previous_tracker=self.previous,
                proposed_tracker=self.proposed,
                target_tracker_path=self.previous,
                metadata=metadata,
            )

    def test_full_verifier_accepts_exact_packet_and_rejects_stale(self) -> None:
        packet = self.build()
        packet_path = self.root / "packet.json"
        packet_path.write_bytes(program_revision.canonical(packet) + b"\n")
        command = [
            "/usr/bin/python3",
            str(Path(__file__).with_name("verify_tracker.py")),
            str(self.proposed),
            "--profile",
            "full",
            "--revision-packet",
            str(packet_path),
            "--previous-tracker",
            str(self.previous),
        ]
        accepted = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr + accepted.stdout)
        stale = copy.deepcopy(packet)
        stale["previous_tracker_sha256"] = "f" * 64
        stale["packet_root"] = program_revision.digest(
            {key: value for key, value in stale.items() if key != "packet_root"}
        )
        packet_path.write_bytes(program_revision.canonical(stale) + b"\n")
        rejected = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("differs from current sources", rejected.stdout)

    def test_review_shape_binds_delta_and_disposition(self) -> None:
        packet = self.build()
        review = {
            "schema_version": 1,
            "kind": "software-factory-program-revision-independent-review",
            "record_id": "REVIEW-STRUCTURAL-0001",
            "revision_id": packet["revision_id"],
            "packet_root": packet["packet_root"],
            "previous_tracker_sha256": packet["previous_tracker_sha256"],
            "proposed_tracker_sha256": packet["proposed_tracker_sha256"],
            "proposed_tracker_structure_sha256": packet[
                "proposed_tracker_structure_sha256"
            ],
            "accepted_history_root": packet["accepted_history_root"],
            "block_map_root": program_revision.digest(packet["block_number_map"]),
            "affected_closure_root": program_revision.digest(
                packet["affected_proposed_blocks"]
            ),
            "resume_block": packet["resume_block"],
            "author_id": packet["author_id"],
            "reviewer_id": packet["reviewer_id"],
            "disposition": "accepted",
            "finding_refs": [],
            "evidence_root": "8" * 64,
            "authority_key_sha256": "9" * 64,
            "review_root": "",
            "signature_base64": "signed-outside-author-owner",
        }
        review["review_root"] = program_revision.digest(
            program_revision.review_root_material(review)
        )
        accepted = program_revision.validate_review_shape(
            review, packet=packet, authority_key_sha256="9" * 64
        )
        self.assertEqual(accepted["disposition"], "accepted")
        review["packet_root"] = "0" * 64
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "does not bind"
        ):
            program_revision.validate_review_shape(
                review, packet=packet, authority_key_sha256="9" * 64
            )


if __name__ == "__main__":
    unittest.main()
