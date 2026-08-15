#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
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
        self.install_program_control(
            {"0": [0], "1": [1], "2": [2, 3], "3": [4]},
            affected=[2, 3],
            resume=2,
        )

    def install_program_control(
        self,
        mapping: dict[str, list[int]],
        *,
        affected: list[int],
        resume: int,
        revision_id: str = "REV-STRUCTURAL-0001",
        require_full_previous: bool = True,
    ) -> None:
        text = self.proposed.read_text(encoding="utf-8")
        text = re.sub(
            r"\n## Active-program revision control\n.*?(?=\n## Block 0\b)",
            "",
            text,
            flags=re.S,
        )
        self.proposed.write_text(text, encoding="utf-8")
        previous = program_revision.tracker_snapshot(
            self.previous, require_full=require_full_previous
        )
        proposed = program_revision.tracker_snapshot(self.proposed)
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
        self.proposed.write_text(
            text.replace("## Block 0", control + "\n## Block 0", 1),
            encoding="utf-8",
        )
        current_structure = program_revision.tracker_snapshot(
            self.proposed, require_full=False
        )["structure_sha256"]
        self.proposed.write_text(
            self.proposed.read_text(encoding="utf-8").replace(
                f"| `{revision_id}` | `{previous['sha256']}` | "
                f"`{proposed['structure_sha256']}` |",
                f"| `{revision_id}` | `{previous['sha256']}` | "
                f"`{current_structure}` |",
                1,
            ),
            encoding="utf-8",
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

    def metadata(self, mapping: dict[str, list[int]] | None = None) -> dict[str, object]:
        return {
            "revision_id": "REV-STRUCTURAL-0001",
            "predecessor_revision_id": None,
            "predecessor_review_root": None,
            "resolved_finding_refs": [],
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
            "application_owner_id": "target-application-owner-1234",
            "authoring_profile_revision": "tracker-authoring-profile-v1",
            "authoring_profile_root": "b" * 64,
            "authoring_profile_source_revision": "f" * 40,
            "authoring_profile_source_root": "a" * 64,
            "authoring_profile_binding_root": "c" * 64,
            "mechanical_watcher_id": "tracker-watcher-1234",
            "mechanical_route_record_id": "EVT-ROUTE-1234",
            "semantic_review_record_id": "EVT-REVIEW-1234",
            "semantic_review_root": "d" * 64,
            "adjudicator_id": "tracker-adjudicator-1234",
            "adjudication_root": "e" * 64,
            "fix_executor_id": "tracker-fix-executor-1234",
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

    def set_table_status(self, path: Path, block: int, status: str) -> None:
        pattern = re.compile(
            rf"^(\|\s*{block}\s*\|[^|\n]*\|[^|\n]*\|\s*)`[^`]+`(\s*\|)$",
            re.MULTILINE,
        )
        changed, count = pattern.subn(rf"\g<1>`{status}`\g<2>", path.read_text())
        self.assertEqual(count, 1)
        path.write_text(changed, encoding="utf-8")

    def reinstall_program_control_for_legacy_predecessor(self) -> None:
        self.install_program_control(
            {"0": [0], "1": [1], "2": [2, 3], "3": [4]},
            affected=[2, 3],
            resume=2,
            require_full_previous=False,
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

    def test_legacy_predecessor_complete_table_preserves_accepted_history(self) -> None:
        canonical = self.build()
        self.set_table_status(self.previous, 0, "complete")
        self.set_table_status(self.previous, 1, "complete")
        strict_result = program_revision._load_full_verifier().verify(
            self.previous, "full"
        )
        self.assertEqual(len(strict_result["errors"]), 2)
        self.assertTrue(
            all("table status 'complete'" in error for error in strict_result["errors"])
        )
        self.reinstall_program_control_for_legacy_predecessor()

        packet = self.build()

        self.assertEqual(packet["accepted_history_blocks"], [0, 1])
        self.assertEqual(
            packet["accepted_history_root"], canonical["accepted_history_root"]
        )
        self.assertEqual(
            program_revision.validate_revision_packet(
                packet,
                previous_tracker=self.previous,
                proposed_tracker=self.proposed,
            ),
            packet,
        )

    def test_proposal_legacy_complete_table_remains_strict(self) -> None:
        self.set_table_status(self.proposed, 0, "complete")
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError,
            "fails the full structural verifier",
        ):
            self.build()

    def test_legacy_predecessor_rejects_unmatched_or_unknown_statuses(self) -> None:
        original_previous = self.previous.read_text(encoding="utf-8")
        cases = (
            ("complete", "in-progress"),
            ("done", "completed"),
            ("done", "done"),
        )
        for table_status, body_status in cases:
            with self.subTest(table_status=table_status, body_status=body_status):
                self.previous.write_text(original_previous, encoding="utf-8")
                self.set_table_status(self.previous, 0, "complete")
                self.set_table_status(self.previous, 1, table_status)
                self.previous.write_text(
                    self.previous.read_text(encoding="utf-8").replace(
                        "## Block 1 — Accepted owner\n\nStatus: `completed`",
                        f"## Block 1 — Accepted owner\n\nStatus: `{body_status}`",
                        1,
                    ),
                    encoding="utf-8",
                )
                self.reinstall_program_control_for_legacy_predecessor()
                with self.assertRaises(program_revision.ProgramRevisionError):
                    self.build()

    def test_legacy_predecessor_rejects_any_extra_verifier_error(self) -> None:
        self.set_table_status(self.previous, 0, "complete")
        self.previous.write_text(
            self.previous.read_text(encoding="utf-8").replace(
                "### Negative tests", "### Failure examples", 1
            ),
            encoding="utf-8",
        )
        self.reinstall_program_control_for_legacy_predecessor()
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError,
            "fails the full structural verifier",
        ):
            self.build()

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

    def test_open_block_cannot_collide_with_accepted_successor(self) -> None:
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError,
            "Accepted Block history was rewritten|Open Block cannot map to completed work",
        ):
            program_revision.build_revision_packet(
                previous_tracker=self.previous,
                proposed_tracker=self.proposed,
                target_tracker_path=self.previous,
                metadata=self.metadata(
                    {"0": [0], "1": [1], "2": [1], "3": [4]}
                ),
            )

    def test_structural_proposal_requires_complete_program_control(self) -> None:
        original = self.proposed.read_text(encoding="utf-8")
        mutations = (
            re.sub(
                r"\n## Active-program revision control\n.*?(?=\n## Block 0\b)",
                "",
                original,
                flags=re.S,
            ),
            original.replace("- Terminal Block: `4`", "- Terminal Block: `3`"),
            original.replace(
                "- Source-map Blocks: `0,1,2,3,4`",
                "- Source-map Blocks: `0,1,2,3`",
            ),
            original.replace("- Handoff Block: `2`", "- Handoff Block: `4`"),
            original.replace(
                "| 4 | source-block-4 |",
                "| 3 | source-block-4 |",
            ),
            original.replace(
                "| Revision ID | Predecessor tracker SHA-256 |",
                "| Revision | Previous tracker SHA-256 |",
            ),
            original.replace(
                "## Block 0",
                "Retained implementation range: Blocks 2–3 only; "
                "handoff to obsolete Block 3.\n\n## Block 0",
                1,
            ),
            original
            + "\n## Retained program handoff\n\n"
            + "Resume at obsolete Block 3.\n",
        )
        for changed in mutations:
            with self.subTest(root=hashlib.sha256(changed.encode()).hexdigest()):
                self.proposed.write_text(changed, encoding="utf-8")
                with self.assertRaises(program_revision.ProgramRevisionError):
                    self.build()
        self.proposed.write_text(original, encoding="utf-8")

    def test_merge_remove_and_reorder_open_blocks_are_mappable(self) -> None:
        self.write_tracker(
            self.proposed,
            [
                ("Foundation", [], "completed"),
                ("Accepted owner", [0], "completed"),
                ("Merged open work", [1], "in-progress"),
            ],
        )
        self.install_program_control(
            {"0": [0], "1": [1], "2": [2], "3": [2]},
            affected=[2],
            resume=2,
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

    def test_packet_integrity_mismatch_and_self_review_reject(self) -> None:
        packet = self.build()
        changed_packet = copy.deepcopy(packet)
        changed_packet["resume_block"] = 4
        changed_packet["packet_root"] = program_revision.digest(
            {
                key: value
                for key, value in changed_packet.items()
                if key != "packet_root"
            }
        )
        with self.assertRaisesRegex(
            program_revision.ProgramRevisionError, "differs from current sources"
        ):
            program_revision.validate_revision_packet(
                changed_packet,
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
            "predecessor_revision_id": packet["predecessor_revision_id"],
            "predecessor_review_root": packet["predecessor_review_root"],
            "resolved_finding_refs": packet["resolved_finding_refs"],
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
            "application_owner_id": packet["application_owner_id"],
            "reviewer_id": packet["reviewer_id"],
            "mechanical_watcher_id": packet["mechanical_watcher_id"],
            "adjudicator_id": packet["adjudicator_id"],
            "fix_executor_id": packet["fix_executor_id"],
            "authoring_profile_source_revision": packet[
                "authoring_profile_source_revision"
            ],
            "authoring_profile_source_root": packet[
                "authoring_profile_source_root"
            ],
            "authoring_profile_binding_root": packet[
                "authoring_profile_binding_root"
            ],
            "mechanical_route_record_id": packet[
                "mechanical_route_record_id"
            ],
            "semantic_review_record_id": packet[
                "semantic_review_record_id"
            ],
            "adjudication_root": packet["adjudication_root"],
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
