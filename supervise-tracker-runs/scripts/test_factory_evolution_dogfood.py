#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("factory_evolution_dogfood.py")
SPEC = importlib.util.spec_from_file_location("factory_evolution_dogfood", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
dogfood = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dogfood)


class IntegratedFactoryEvolutionDogfoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="software-factory-block17-test-"
        )
        cls.result = dogfood.run_dogfood(
            workspace=Path(cls.temporary.name) / "workspace",
            live_skills=dogfood.DEFAULT_LIVE_SKILLS,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_winner_noop_and_losing_candidate_are_current(self) -> None:
        winner = self.result["eligible_adopted"]
        no_op = self.result["unchanged_no_op"]
        losing = self.result["losing_candidate"]
        self.assertEqual(winner["outcome_posture"], "adopted-effective")
        self.assertTrue(winner["candidate_authoritative"])
        self.assertEqual(winner["human_request_count"], 0)
        self.assertEqual(winner["release_activation_delta"], 1)
        self.assertEqual(
            no_op["disposition"], "already-consumed-canonical-coverage"
        )
        self.assertEqual(no_op["event_delta"], 0)
        self.assertEqual(no_op["artifact_directory_delta"], 0)
        self.assertFalse(no_op["candidate_created"])
        self.assertEqual(losing["outcome_posture"], "candidate-retired")
        self.assertTrue(losing["incumbent_authoritative"])
        self.assertEqual(losing["release_activation_delta"], 0)

    def test_live_skills_authority_modes_and_effect_boundaries_are_visible(self) -> None:
        live = self.result["live_skill_invocation"]
        compatibility = self.result["within_run_compatibility"]
        self.assertEqual(len(live["skills"]), 3)
        self.assertTrue(
            all(item["validator_exit_code"] == 0 for item in live["skills"])
        )
        self.assertEqual(
            compatibility["authority_modes"],
            ["fixed", "full-autonomous", "recommend", "reviewed-autonomous"],
        )
        self.assertEqual(compatibility["human_request_count"], 0)
        for field in (
            "external_effects_performed",
            "live_release_mutated",
            "live_policy_mutated",
            "live_mission_mutated",
            "live_lifecycle_mutated",
            "gmail_action_performed",
            "deployment_performed",
        ):
            self.assertFalse(self.result[field])

    def test_result_and_nested_evidence_roots_are_exact(self) -> None:
        material = {
            key: value for key, value in self.result.items() if key != "result_root"
        }
        self.assertEqual(self.result["result_root"], dogfood.digest(material))
        for field, root_field in (
            ("eligible_adopted", "cycle_root"),
            ("losing_candidate", "cycle_root"),
            ("unchanged_no_op", "no_op_root"),
        ):
            value = self.result[field]
            nested = {key: item for key, item in value.items() if key != root_field}
            self.assertEqual(value[root_field], dogfood.digest(nested))

    def test_gitless_source_fallback_is_exact(self) -> None:
        completed = mock.Mock(returncode=128, stdout="", stderr="not a repository")
        with (
            mock.patch.object(dogfood.subprocess, "run", return_value=completed),
            mock.patch.object(dogfood, "ARCHIVE_SOURCE_REVISION", "a" * 40),
        ):
            self.assertEqual(dogfood.source_revision(), "a" * 40)


if __name__ == "__main__":
    unittest.main()
