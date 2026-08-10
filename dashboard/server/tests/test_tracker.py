from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import software_factory_dashboard.tracker as tracker_module
from software_factory_dashboard.catalog import ProjectRecord
from software_factory_dashboard.tracker import (
    TrackerProjectionError,
    TrackerProjectionService,
    tracker_identity,
)


def full_block(number: int, status: str, *, dependency: str, evidence: str) -> str:
    return f"""## Block {number} — Demo block {number}

Status: `{status}`

### Objective

Project exact tracker state for Block {number}.

### Target-product capability delta

- Posture: `consequential`
- Intended capability gain: expose exact source truth for Block {number}.
- Potential capability loss or regression: a lossy projection could hide open work.
- Protected-capability effect: preserve Markdown and Git ownership.
- Architecture and operating-model effect: add one read-only adapter boundary.
- Tradeoff and source evidence: structured parsing costs maintenance but exact source links preserve review.

### Inputs and dependencies

- Declared dependency expression: {dependency}.

### Required work

- Parse exact fields without editing the tracker.

### Scope and non-goals

- Read-only projection only.

### Deliverables and recorded state

- Typed projection and tests.

### Resource and economy contract

Cache only an unchanged content and verifier fingerprint.

### QA and independent review

- Compare with the maintained verifier.

### Acceptance

- Exact status and source identity remain visible.

### Negative tests

- Reject mismatched structure without rewriting it.

### Completion evidence

{evidence}

### Unrecognized operator note

This source section must remain linked even when it has no structured field.

### Stop

Stop before tracker mutation.

"""


FULL_TRACKER = (
    """# Full Demo Implementation Tracker

- Tracker status: `in-progress`
- Tracker sequence: Blocks 0–1
- Governing objective: `Project exact tracker and Git truth.`

## Target-product capability frame

- Applicability: `consequential`
- Applicability rationale: tracker truth affects operator decisions.
- Direct product sources: current tracker Markdown, Git, and maintained verifier.
- Product thesis and intended effect: exact projection makes review trustworthy.
- Protected capabilities: source ownership, status, evidence, and Stops.
- Architecture strategy: one read-only adapter behind the loopback API.
- Requested capability: tracker truth and Git currentness.
- Proportionality: parse only supported tracker fields and link the rest.
- Tradeoffs: structured projection requires parser maintenance.
- Uncertainty: inherited trackers may require an explicit core grant.

## Source owner map

| Concern | Owner | Treatment |
|---|---|---|
| Structure | Tracker \\| Markdown | read-only |
| Diagnostics | verify_tracker.py | invoke |

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Accepted base | — | `accepted` |
| 1 | Eligible successor | 0 | `not-started` |

"""
    + full_block(0, "accepted", dependency="none", evidence="- Commit `abc123` accepted.")
    + full_block(1, "not-started", dependency="Block 0", evidence="Pending.")
    + """## Verification matrix

| Capability | Proof |
|---|---|
| Tracker truth | maintained verifier JSON |

## Final integrated acceptance

The exact source and verifier result agree.
"""
)


CORE_TRACKER = """# Inherited Core Tracker

- Tracker status: `planning`
- Tracker sequence: Blocks 0–0

## Target-product capability frame

- Applicability: `consequential`

## Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Legacy work | — | `not-started` |

## Block 0 — Legacy work

Status: `not-started`

### Objective

Preserve the inherited tracker.

### Required work

- Read it through the documented compatibility path.

### Acceptance

- Core verification remains explicit.

### Stop

Stop before mutation.
"""


class TrackerProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = (Path(self.temporary.name) / "repository").resolve()
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "tracker@test.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Tracker Test"],
            check=True,
        )
        (self.root / "docs").mkdir()
        (self.root / "docs" / "full-implementation-tracker.md").write_text(
            FULL_TRACKER,
            encoding="utf-8",
        )
        (self.root / "docs" / "legacy-implementation-tracker.md").write_text(
            CORE_TRACKER,
            encoding="utf-8",
        )
        (self.root / "docs" / "unapproved-legacy-implementation-tracker.md").write_text(
            CORE_TRACKER,
            encoding="utf-8",
        )
        (self.root / "docs" / "full-copy-implementation-tracker.md").write_text(
            FULL_TRACKER,
            encoding="utf-8",
        )
        (self.root / "docs" / "crlf-implementation-tracker.md").write_bytes(
            FULL_TRACKER.replace("\n", "\r\n").encode("utf-8")
        )
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "fixtures"], check=True)
        self.project = ProjectRecord(
            id="demo",
            label="Demo",
            root=str(self.root),
        )
        self.service = TrackerProjectionService(
            core_compatibility={
                str(self.root): {
                    "docs/legacy-implementation-tracker.md": frozenset(
                        {sha256(CORE_TRACKER.encode("utf-8")).hexdigest()}
                    )
                }
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_full_projection_preserves_structure_verifier_and_source_ranges(self) -> None:
        detail = self.service.project(
            self.project,
            "docs/full-implementation-tracker.md",
        )

        self.assertEqual(detail["id"], tracker_identity("demo", "docs/full-implementation-tracker.md"))
        self.assertEqual(detail["profile"], "full")
        self.assertEqual(detail["tracker_status"], "in-progress")
        self.assertTrue(detail["verifier"]["valid"])
        self.assertEqual(detail["verifier"]["exit_status"], 0)
        self.assertEqual(detail["counts"]["by_status"], {"accepted": 1, "not-started": 1})
        self.assertEqual(detail["eligible_blocks"], [1])
        self.assertTrue(detail["blocks"][0]["completion_evidence"]["present"])
        self.assertEqual(detail["blocks"][0]["completion_evidence"]["posture"], "recorded")
        self.assertFalse(detail["blocks"][1]["completion_evidence"]["present"])
        self.assertEqual(detail["blocks"][1]["completion_evidence"]["posture"], "open")
        self.assertEqual(detail["blocks"][1]["dependency_statuses"], [{"number": 0, "status": "accepted"}])
        self.assertEqual(detail["blocks"][1]["blocked_ancestors"], [])
        self.assertIn(
            "unrecognized operator note",
            [section["normalized_title"] for section in detail["blocks"][0]["sections"]],
        )
        self.assertEqual(detail["frames"][0]["fields"]["applicability"], "`consequential`")
        owner_table = detail["owner_source_maps"][0]["tables"][0]
        self.assertEqual(owner_table["headers"], ["Concern", "Owner", "Treatment"])
        self.assertEqual(owner_table["rows"][0][1], "Tracker | Markdown")
        self.assertEqual(
            {section["title"] for section in detail["supplemental_sections"]},
            {"Verification matrix", "Final integrated acceptance"},
        )
        self.assertEqual(detail["git"]["status"], "available")
        self.assertTrue(detail["git"]["tracked"])
        self.assertFalse(detail["git"]["worktree_changed"])
        self.assertTrue(detail["git"]["content_matches_head"])
        self.assertEqual(detail["git"]["binding_status"], "unavailable")
        self.assertTrue(detail["raw_file"]["read_only"])
        self.assertEqual(detail["git"]["diff"]["status"], "available")
        self.assertFalse(detail["git"]["diff"]["changed"])
        objective_section = next(
            section
            for section in detail["blocks"][0]["sections"]
            if section["normalized_title"] == "objective"
        )
        self.assertIn("Project exact tracker state", objective_section["markdown_preview"])
        self.assertRegex(objective_section["content_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(objective_section["preview_truncated"])
        self.assertNotIn(
            "objective",
            [section["normalized_title"] for section in detail["document_sections"]],
        )

        all_accepted_path = self.root / "docs" / "all-accepted-implementation-tracker.md"
        all_accepted_path.write_text(
            FULL_TRACKER.replace("not-started", "accepted").replace(
                "Pending.", "- Commit `def456` accepted."
            ),
            encoding="utf-8",
        )
        all_accepted = self.service.project(
            self.project,
            "docs/all-accepted-implementation-tracker.md",
        )
        self.assertTrue(all_accepted["verifier"]["valid"])
        self.assertTrue(all_accepted["header_block_status_conflict"])

        open_items_path = self.root / "docs" / "open-items-implementation-tracker.md"
        open_items_path.write_text(
            FULL_TRACKER.replace("not-started", "completed-with-open-items"),
            encoding="utf-8",
        )
        open_items = self.service.project(
            self.project,
            "docs/open-items-implementation-tracker.md",
        )
        self.assertTrue(open_items["verifier"]["valid"])
        self.assertEqual(open_items["counts"]["accepted"], 1)
        self.assertEqual(open_items["counts"]["open"], 1)
        self.assertEqual(open_items["eligible_blocks"], [])

    def test_blocked_ancestry_is_derived_across_the_dependency_graph(self) -> None:
        blocked_tracker = FULL_TRACKER.replace("Blocks 0–1", "Blocks 0–2").replace(
            "| 0 | Accepted base | — | `accepted` |",
            "| 0 | Accepted base | — | `blocked` |",
        ).replace(
            "| 1 | Eligible successor | 0 | `not-started` |",
            "| 1 | Eligible successor | 0 | `not-started` |\n"
            "| 2 | Descendant successor | 1 | `not-started` |",
        ).replace(
            "Status: `accepted`",
            "Status: `blocked`",
            1,
        ).replace(
            "## Verification matrix",
            full_block(
                2,
                "not-started",
                dependency="Block 1",
                evidence="Pending.",
            )
            + "## Verification matrix",
        )
        path = self.root / "docs" / "blocked-chain-implementation-tracker.md"
        path.write_text(blocked_tracker, encoding="utf-8")

        detail = self.service.project(
            self.project,
            "docs/blocked-chain-implementation-tracker.md",
        )

        self.assertTrue(detail["verifier"]["valid"])
        self.assertEqual(detail["eligible_blocks"], [])
        self.assertEqual(detail["blocks"][0]["blocked_ancestors"], [])
        self.assertEqual(detail["blocks"][1]["blocked_ancestors"], [0])
        self.assertEqual(detail["blocks"][2]["blocked_ancestors"], [0])

    def test_cache_core_policy_invalid_default_dirty_untracked_and_stale_binding(self) -> None:
        full_path = self.root / "docs" / "full-implementation-tracker.md"
        original_sha = sha256(full_path.read_bytes()).hexdigest()
        first = self.service.project(self.project, "docs/full-implementation-tracker.md")
        second = self.service.project(self.project, "docs/full-implementation-tracker.md")
        self.assertEqual(self.service.verifier_run_count, 1)
        self.assertEqual(first["analysis_cache"]["status"], "miss")
        self.assertEqual(second["analysis_cache"]["status"], "hit")

        core = self.service.project(self.project, "docs/legacy-implementation-tracker.md")
        self.assertEqual(core["profile"], "core")
        self.assertTrue(core["verifier"]["valid"])
        legacy_path = self.root / "docs" / "legacy-implementation-tracker.md"
        legacy_path.write_text(CORE_TRACKER + "\n<!-- changed core root -->\n", encoding="utf-8")
        changed_core = self.service.project(
            self.project,
            "docs/legacy-implementation-tracker.md",
        )
        self.assertEqual(changed_core["profile"], "full")
        self.assertFalse(changed_core["verifier"]["valid"])
        unapproved = self.service.project(
            self.project,
            "docs/unapproved-legacy-implementation-tracker.md",
        )
        self.assertEqual(unapproved["profile"], "full")
        self.assertFalse(unapproved["verifier"]["valid"])
        self.assertTrue(any("capability frame" in error for error in unapproved["verifier"]["errors"]))

        full_path.write_text(FULL_TRACKER + "\n<!-- changed after binding -->\n", encoding="utf-8")
        changed = self.service.project(
            self.project,
            "docs/full-implementation-tracker.md",
            bound_content_sha256=original_sha,
        )
        self.assertEqual(changed["git"]["binding_status"], "stale")
        self.assertTrue(changed["git"]["worktree_changed"])
        self.assertFalse(changed["git"]["content_matches_head"])
        self.assertTrue(changed["git"]["diff"]["changed"])
        self.assertGreater(changed["git"]["diff"]["added_lines"], 0)
        self.assertIn("changed after binding", changed["git"]["diff"]["preview"])
        summary = self.service.summary(changed)
        self.assertIsNone(summary["git"]["diff"]["preview"])
        self.assertIn("changed after binding", changed["git"]["diff"]["preview"])
        deferred = self.service.project(
            self.project,
            "docs/full-implementation-tracker.md",
            include_diff_preview=False,
        )
        self.assertTrue(deferred["git"]["diff"]["changed"])
        self.assertIsNone(deferred["git"]["diff"]["preview"])
        loaded_diff = self.service.diff(
            self.project,
            "docs/full-implementation-tracker.md",
        )
        self.assertEqual(loaded_diff["content_sha256"], changed["raw_file"]["content_sha256"])
        self.assertIn("changed after binding", loaded_diff["diff"]["preview"])
        subprocess.run(["git", "-C", str(self.root), "add", str(full_path)], check=True)
        staged = self.service.project(self.project, "docs/full-implementation-tracker.md")
        self.assertTrue(staged["git"]["worktree_changed"])
        self.assertFalse(staged["git"]["content_matches_head"])
        self.assertNotEqual(staged["git"]["index_blob"], staged["git"]["git_blob"])

        untracked_path = self.root / "docs" / "untracked-implementation-tracker.md"
        untracked_path.write_text(FULL_TRACKER, encoding="utf-8")
        untracked = self.service.project(
            self.project,
            "docs/untracked-implementation-tracker.md",
        )
        self.assertFalse(untracked["git"]["tracked"])
        self.assertTrue(untracked["git"]["untracked"])
        self.assertTrue(untracked["git"]["worktree_changed"])
        self.assertEqual(untracked["git"]["diff"]["base"], "empty")
        self.assertTrue(untracked["git"]["diff"]["changed"])

        with self.assertRaisesRegex(TrackerProjectionError, "Bound tracker hash"):
            self.service.project(
                self.project,
                "docs/full-implementation-tracker.md",
                bound_content_sha256="not-a-sha256",
            )

    def test_maintained_verifier_diagnostics_gate_all_derived_eligibility(self) -> None:
        cases = {
            "status-mismatch": (
                FULL_TRACKER.replace(
                    "| 1 | Eligible successor | 0 | `not-started` |",
                    "| 1 | Eligible successor | 0 | `accepted` |",
                ),
                "does not match block status",
            ),
            "duplicate": (
                FULL_TRACKER.replace("## Block 1 — Demo block 1", "## Block 0 — Demo block 1"),
                "duplicate Block headings",
            ),
            "impossible-dependency": (
                FULL_TRACKER.replace(
                    "| 1 | Eligible successor | 0 | `not-started` |",
                    "| 1 | Eligible successor | 9 | `not-started` |",
                ),
                "depends on unknown Block 9",
            ),
            "missing-delta": (
                FULL_TRACKER.replace(
                    "### Target-product capability delta",
                    "### Capability change",
                    1,
                ),
                "missing section 'target-product capability delta'",
            ),
            "missing-evidence": (
                FULL_TRACKER.replace("### Completion evidence", "### Evidence omitted", 1),
                "missing section 'completion evidence'",
            ),
        }
        for name, (content, expected_error) in cases.items():
            with self.subTest(name=name):
                relative_path = f"docs/{name}-implementation-tracker.md"
                (self.root / relative_path).write_text(content, encoding="utf-8")
                detail = self.service.project(self.project, relative_path)
                self.assertFalse(detail["verifier"]["valid"])
                self.assertTrue(
                    any(expected_error in error for error in detail["verifier"]["errors"]),
                    detail["verifier"]["errors"],
                )
                self.assertEqual(detail["eligible_blocks"], [])
                if name == "duplicate":
                    self.assertEqual(detail["counts"]["total"], 2)

    def test_repository_batch_reuses_git_snapshot_and_exact_content_cache(self) -> None:
        service = TrackerProjectionService()
        paths = [
            "docs/full-implementation-tracker.md",
            "docs/full-copy-implementation-tracker.md",
            "docs/crlf-implementation-tracker.md",
        ]
        with patch(
            "software_factory_dashboard.tracker._run_git_bytes",
            wraps=tracker_module._run_git_bytes,
        ) as run_git_bytes:
            outcomes = service.project_many(self.project, paths)

        status_calls = [
            call for call in run_git_bytes.call_args_list if "status" in call.args
        ]
        index_calls = [
            call for call in run_git_bytes.call_args_list if "ls-files" in call.args
        ]
        log_calls = [call for call in run_git_bytes.call_args_list if "log" in call.args]
        self.assertEqual(len(status_calls), 1)
        self.assertEqual(len(index_calls), 1)
        self.assertEqual(len(log_calls), 1)
        self.assertEqual(service.verifier_run_count, 2)

        full = outcomes[paths[0]]
        copied = outcomes[paths[1]]
        crlf = outcomes[paths[2]]
        self.assertIsInstance(full, dict)
        self.assertIsInstance(copied, dict)
        self.assertIsInstance(crlf, dict)
        assert isinstance(full, dict) and isinstance(copied, dict) and isinstance(crlf, dict)
        self.assertEqual(full["analysis_cache"]["status"], "miss")
        self.assertEqual(copied["analysis_cache"]["status"], "hit")
        self.assertNotEqual(full["verifier"]["command"][2], copied["verifier"]["command"][2])
        self.assertTrue(crlf["git"]["content_matches_head"])
        self.assertEqual(
            crlf["git"]["committed_content_sha256"],
            sha256((self.root / paths[2]).read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
