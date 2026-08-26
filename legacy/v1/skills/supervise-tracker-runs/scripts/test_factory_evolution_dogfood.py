#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("factory_evolution_dogfood.py")
SPEC = importlib.util.spec_from_file_location("factory_evolution_dogfood", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
dogfood = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dogfood)


class FactoryEvolutionDogfoodUnitTests(unittest.TestCase):
    def test_frozen_integrated_projection_rebuilds_from_exact_raw_evidence(
        self,
    ) -> None:
        fixtures = SCRIPT.parent.parent / "fixtures"
        raw = dogfood.json.loads(
            (
                fixtures / "factory_evolution_integrated_dogfood_evidence_v1.json"
            ).read_text(encoding="utf-8")
        )
        projection = dogfood.json.loads(
            (
                fixtures / "factory_evolution_integrated_dogfood_projection_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(dogfood.reproducible_result_projection(raw), projection)
        self.assertEqual(raw["source_revision"], "69a00124c0223666e55a711198e3385a1019f613")
        self.assertEqual(
            projection["projection_root"],
            "ccd4c7ca8dbd99231911f9898240815c25859cb3088a932f18101e3690ebe114",
        )

    def test_candidate_proof_pass_and_failure_outputs_are_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="software-factory-block17-proof-output-"
        ) as temporary:
            root = Path(temporary)
            scripts = root / "implement-tracker-blocks" / "scripts"
            scripts.mkdir(parents=True)
            skill = scripts.parent / "SKILL.md"
            proof = scripts / "test_capability_255083e6fcd14f5d07bc.py"
            skill.write_text("Baseline guidance.\n", encoding="utf-8")
            proof.write_text(dogfood._candidate_proof_source(), encoding="utf-8")

            def run_proof() -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        str(scripts.relative_to(root)),
                        "-p",
                        proof.name,
                    ],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "LC_ALL": "C",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )

            baseline_first = run_proof()
            baseline_second = run_proof()
            self.assertEqual(baseline_first.returncode, 1)
            self.assertEqual(baseline_first.stderr, baseline_second.stderr)
            skill.write_text(
                "Retain one exact installed-outcome root before terminal acceptance.\n",
                encoding="utf-8",
            )
            candidate_first = run_proof()
            candidate_second = run_proof()
            self.assertEqual(candidate_first.returncode, 0)
            self.assertEqual(candidate_first.stderr, candidate_second.stderr)


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

    def test_semantic_projection_is_closed_rooted_and_nonauthorizing(self) -> None:
        projection = dogfood.reproducible_result_projection(self.result)
        material = {
            key: value for key, value in projection.items() if key != "projection_root"
        }
        self.assertEqual(projection["projection_root"], dogfood.digest(material))
        self.assertFalse(projection["authorizing"])
        self.assertTrue(projection["raw_roots_validated"])
        self.assertTrue(projection["projected_semantics_validated"])
        self.assertTrue(projection["target_clean"])
        self.assertEqual(
            projection["live_skill_identity"]["live_skill_root"],
            self.result["live_skill_invocation"]["live_skill_root"],
        )
        self.assertNotIn("cycle", projection["eligible_adopted"])
        self.assertNotIn("artifact_names", projection["eligible_adopted"])
        self.assertNotIn("baseline_revision", projection["losing_candidate"])
        self.assertNotIn(
            "discovery_target", projection["live_skill_identity"]["skills"][0]
        )
        changed = copy.deepcopy(self.result)
        changed["eligible_adopted"]["cycle_root"] = "0" * 64
        with self.assertRaisesRegex(dogfood.DogfoodError, "root differs"):
            dogfood.reproducible_result_projection(changed)

    def test_root_consistent_synthetic_semantics_do_not_validate(self) -> None:
        cases = (
            ("external-effect", lambda value: value.update(external_effects_performed=True)),
            (
                "missing-installed-effect",
                lambda value: value["eligible_adopted"].update(installed_effect=None),
            ),
            (
                "no-op-candidate",
                lambda value: value["unchanged_no_op"].update(candidate_created=True),
            ),
            (
                "lower-power-selected",
                lambda value: value["eligible_adopted"].update(
                    selected_path="lower-power-shortcut"
                ),
            ),
        )
        for case_id, mutate in cases:
            with self.subTest(case_id=case_id):
                changed = copy.deepcopy(self.result)
                mutate(changed)
                if case_id in {"missing-installed-effect", "lower-power-selected"}:
                    cycle = changed["eligible_adopted"]
                    cycle["cycle_root"] = dogfood.digest(
                        {key: value for key, value in cycle.items() if key != "cycle_root"}
                    )
                elif case_id == "no-op-candidate":
                    no_op = changed["unchanged_no_op"]
                    no_op["no_op_root"] = dogfood.digest(
                        {key: value for key, value in no_op.items() if key != "no_op_root"}
                    )
                changed["result_root"] = dogfood.digest(
                    {
                        key: value
                        for key, value in changed.items()
                        if key != "result_root"
                    }
                )
                with self.assertRaisesRegex(
                    dogfood.DogfoodError,
                    "integrated dogfood semantic evidence differs",
                ):
                    dogfood.reproducible_result_projection(changed)

    def test_every_retained_projection_boundary_rejects_synthetic_semantics(
        self,
    ) -> None:
        cases = (
            ("live-validator", lambda value: value["live_skill_invocation"]["skills"][0].update(validator_exit_code=1), "live"),
            ("live-release", lambda value: value["live_skill_invocation"].update(shared_release=None), "live"),
            ("tracker-verifier", lambda value: value["live_skill_invocation"].update(tracker_verifier_exit_code=1), "live"),
            ("authority", lambda value: value["within_run_compatibility"]["authority_cases"][0].update(authorized=True), "compatibility"),
            ("high-precision-root", lambda value: value["eligible_adopted"].update(admission_result_root="not-a-root"), "winner"),
            ("target-head", lambda value: value["operator_projection"].update(target_head="f" * 40), "operator"),
            ("event-counts", lambda value: value["operator_projection"].update(event_kind_counts={}), "operator"),
            ("report-authority", lambda value: value["human_report_projection"]["current_outcomes"][0].update(candidate_authoritative=False), "report"),
            ("raw-kind", lambda value: value.update(kind="synthetic-dogfood"), "raw"),
            (
                "candidate-revision",
                lambda value: (
                    value["eligible_adopted"].update(candidate_revision="not-a-revision"),
                    value["eligible_adopted"]["installed_effect"].update(
                        installed_source_revision="not-a-revision"
                    ),
                ),
                "winner-installed",
            ),
            (
                "live-discovery-target",
                lambda value: value["live_skill_invocation"]["skills"][0].update(
                    discovery_target=(
                        "/Users/ethanstillman/.codex/skills/"
                        "author-implementation-trackers"
                    )
                ),
                "live",
            ),
            (
                "live-release-shape",
                lambda value: (
                    value["live_skill_invocation"].update(shared_release="garbage"),
                    [
                        item.update(resolved_release="garbage")
                        for item in value["live_skill_invocation"]["skills"]
                    ],
                ),
                "live",
            ),
        )
        for case_id, mutate, boundary in cases:
            with self.subTest(case_id=case_id):
                changed = copy.deepcopy(self.result)
                mutate(changed)
                if boundary == "live":
                    live = changed["live_skill_invocation"]
                    live["live_skill_root"] = dogfood.digest(
                        {key: value for key, value in live.items() if key != "live_skill_root"}
                    )
                elif boundary == "compatibility":
                    compatibility = changed["within_run_compatibility"]
                    compatibility["compatibility_root"] = dogfood.digest(
                        {
                            key: value
                            for key, value in compatibility.items()
                            if key != "compatibility_root"
                        }
                    )
                elif boundary in {"winner", "winner-installed"}:
                    winner = changed["eligible_adopted"]
                    if boundary == "winner-installed":
                        installed = winner["installed_effect"]
                        installed["observed_effect_root"] = dogfood.digest(
                            {
                                key: value
                                for key, value in installed.items()
                                if key != "observed_effect_root"
                            }
                        )
                    winner["cycle_root"] = dogfood.digest(
                        {key: value for key, value in winner.items() if key != "cycle_root"}
                    )
                elif boundary == "operator":
                    operator = changed["operator_projection"]
                    operator["operator_projection_root"] = dogfood.digest(
                        {
                            key: value
                            for key, value in operator.items()
                            if key != "operator_projection_root"
                        }
                    )
                elif boundary == "report":
                    report = changed["human_report_projection"]
                    report["report_projection_root"] = dogfood.digest(
                        {
                            key: value
                            for key, value in report.items()
                            if key != "report_projection_root"
                        }
                    )
                changed["result_root"] = dogfood.digest(
                    {
                        key: value
                        for key, value in changed.items()
                        if key != "result_root"
                    }
                )
                with self.assertRaises(dogfood.DogfoodError):
                    dogfood.reproducible_result_projection(changed)

    def test_gitless_source_fallback_is_exact(self) -> None:
        completed = mock.Mock(returncode=128, stdout="", stderr="not a repository")
        with (
            mock.patch.object(dogfood.subprocess, "run", return_value=completed),
            mock.patch.object(dogfood, "ARCHIVE_SOURCE_REVISION", "a" * 40),
        ):
            self.assertEqual(dogfood.source_revision(), "a" * 40)

    def test_gitless_source_copy_uses_exact_archive_bytes_without_runtime_cache(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="software-factory-block17-gitless-copy-"
        ) as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "copied"
            (source / "package" / "__pycache__").mkdir(parents=True)
            (source / "package" / "current.py").write_text(
                "VALUE = 1\n", encoding="utf-8"
            )
            (source / "package" / "__pycache__" / "current.pyc").write_bytes(
                b"runtime-cache"
            )
            revision = "b" * 40
            with (
                mock.patch.object(dogfood, "REPOSITORY_ROOT", source),
                mock.patch.object(dogfood, "ARCHIVE_SOURCE_REVISION", revision),
            ):
                dogfood._copy_source_tree(revision, destination)
            self.assertEqual(
                (destination / "package" / "current.py").read_text(encoding="utf-8"),
                "VALUE = 1\n",
            )
            self.assertFalse((destination / "package" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
