from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from software_factory import CoreService, Store
from software_factory.store import InvalidTransition, StaleState


class CoreRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "factory.db")
        self.core = CoreService(self.store)
        self.project = self.core.create_project("test")
        self.mission = self.core.create_mission(
            project_id=self.project,
            title="Implement capability",
            objective="Produce a verified operator-visible capability",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_event_chain_and_authority_non_widening(self) -> None:
        parent = self.core.add_authority(
            mission_id=self.mission,
            source_type="direct_user",
            source_ref="request-1",
            effect_classes=["read/observe", "repository_write"],
            scope={"repository": "repo"},
        )
        child = self.core.add_authority(
            mission_id=self.mission,
            source_type="delegation",
            source_ref="delegate-1",
            effect_classes=["read/observe"],
            scope={"repository": "repo"},
            parent_id=parent,
        )
        self.assertTrue(child.startswith("auth_"))
        with self.assertRaises(Exception):
            self.core.add_authority(
                mission_id=self.mission,
                source_type="delegation",
                source_ref="delegate-bad",
                effect_classes=["release"],
                scope={"repository": "repo"},
                parent_id=parent,
            )
        result = self.store.verify_event_chain(self.mission)
        self.assertTrue(result["valid"])
        self.assertGreaterEqual(result["records"], 3)

    def test_attempt_failure_does_not_close_obligation(self) -> None:
        cap = self.core.add_capability(
            mission_id=self.mission,
            name="Feature",
            description="Feature works end to end",
        )
        obligation = self.core.add_obligation(
            mission_id=self.mission,
            capability_id=cap,
            obligation_type="implement",
            description="Implement feature",
        )
        row = self.store.one("SELECT * FROM obligations WHERE id=?", (obligation,))
        self.assertEqual("open", row["status"])
        action = self.core.next_action(self.mission)
        self.assertEqual("diagnose_reflect_or_replan", action["action"])
        self.assertIn(obligation, action["obligation_ids"])

    def test_scheduler_returns_maximal_nonconflicting_set(self) -> None:
        obligation = self.core.add_obligation(
            mission_id=self.mission,
            obligation_type="implement",
            description="Build",
        )
        ids = []
        for title, scope, priority in [
            ("backend", ["server/"], 10),
            ("frontend", ["web/"], 9),
            ("conflict", ["server/api/"], 8),
        ]:
            work = self.core.create_work_item(
                mission_id=self.mission,
                obligation_id=obligation,
                work_type="implementation",
                title=title,
                description=title,
                writable_scope=scope,
                priority=priority,
            )
            self.core.select_work(
                work, expected_version=1, selected_by="selector", basis={"why": title}
            )
            ids.append(work)
        ready = self.core.ready_work(self.mission)
        self.assertEqual(ids[:2], [row["id"] for row in ready])

    def test_dependency_and_program_revision_preserve_range(self) -> None:
        program = self.core.create_program(
            mission_id=self.mission,
            name="Program",
            requested_range={"kind": "full_program"},
            terminal_criteria={"probe": "e2e"},
        )
        first = self.core.create_work_item(
            mission_id=self.mission,
            program_id=program,
            work_type="implementation",
            title="first",
            description="first",
        )
        second = self.core.create_work_item(
            mission_id=self.mission,
            program_id=program,
            work_type="implementation",
            title="second",
            description="second",
        )
        self.core.add_work_dependency(second, first)
        self.core.select_work(
            second, expected_version=1, selected_by="selector", basis={}
        )
        self.assertEqual([], self.core.ready_work(self.mission))
        revision = self.core.revise_program(
            program,
            expected_version=1,
            mapping={first: [first], second: [second]},
            graph={"work": [first, second]},
            accepted_history={"accepted": []},
            resume_frontier={"first": first},
            source_ref="revision-1",
            author_execution_id="author",
            review_execution_id="reviewer",
            accepted=True,
        )
        program_row = self.store.one("SELECT * FROM programs WHERE id=?", (program,))
        self.assertEqual(revision, program_row["current_revision_id"])
        self.assertEqual('{"kind":"full_program"}', program_row["requested_range_json"])

    def test_stale_capability_update_rejected(self) -> None:
        cap = self.core.add_capability(
            mission_id=self.mission,
            name="Capability",
            description="works",
        )
        self.core.set_capability_status(
            cap, expected_version=1, status="partial", evidence_id="e1"
        )
        with self.assertRaises(StaleState):
            self.core.set_capability_status(
                cap, expected_version=1, status="locally_verified", evidence_id="e2"
            )

    def test_terminal_completion_requires_real_capability_and_terminal_execution(self) -> None:
        cap = self.core.add_capability(
            mission_id=self.mission,
            name="Capability",
            description="works",
        )
        with self.assertRaises(InvalidTransition):
            self.core.complete_mission(
                self.mission,
                expected_version=1,
                terminal_evidence_id="evidence",
                verifier_session_id="reviewer",
            )


if __name__ == "__main__":
    unittest.main()
