from __future__ import annotations

import json
import unittest

from software_factory_dashboard.floor import compose_factory_floor


OBSERVED = "2026-08-09T18:00:00.000Z"


def task(
    task_id: str,
    project_id: str,
    status: str = "active",
    *,
    block_start: int | None = None,
    block_end: int | None = None,
    tracker_id: str = "1" * 64,
    mission_root: str = "a" * 64,
) -> dict[str, object]:
    marker = None
    if block_start is not None:
        marker = "SOFTWARE_FACTORY_DASHBOARD_MISSION " + json.dumps(
            {
                "kind": "implement-blocks",
                "source_fingerprint": "f" * 64,
                "project_id": project_id,
                "tracker_id": tracker_id,
                "block_start": block_start,
                "block_end": block_start if block_end is None else block_end,
                "mission_root": mission_root,
                "mission_source_record": "direct-user:item-44",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    turns = [] if marker is None else [{
        "id": f"turn-{task_id}",
        "status": "inProgress" if status == "active" else "completed",
        "items_truncated": False,
        "items": [{"type": "userMessage", "summary": marker}],
    }]
    return {
        "id": task_id,
        "name": f"Task {task_id}",
        "preview": marker,
        "status": {"type": status, "active_flags": []},
        "project_binding": {
            "status": "bound",
            "project_id": project_id,
            "candidates": [project_id],
        },
        "updated_at": "2026-08-09T17:59:00.000Z",
        "recency_at": "2026-08-09T17:59:00.000Z",
        "turns": turns,
        "turns_truncated": False,
    }


def run(
    target: str,
    project_id: str,
    *,
    lifecycle: str | None = None,
    tracker_path: str | None = None,
) -> dict[str, object]:
    return {
        "status": "available",
        "target_thread_id": target,
        "target_label": f"Run {target}",
        "observed_at": "2026-08-09T17:58:00.000Z",
        "fingerprint": target.rjust(64, "a")[-64:],
        "current_mission": {"root": "a" * 64},
        "project_binding": {
            "status": "bound",
            "project_id": project_id,
        },
        "lifecycle": {"status": lifecycle, "record": None},
        "counts": {
            "open_incidents": 1,
            "open_decisions": 2,
            "open_successor_transitions": 0,
        },
        "last_check": {
            "record_id": "EVT-CHECK",
            "timestamp": "2026-08-09T17:56:00.000Z",
            "kind": "check",
            "status": "ok",
            "summary": "Watcher check completed.",
        },
        "light": {
            "posture": "green",
            "label": "On track",
            "facts": [
                {
                    "detail": "No current issue rule is active.",
                    "observed_at": "2026-08-09T17:56:00.000Z",
                    "source_identity": "supervise-tracker-runs/operating-light",
                }
            ],
        },
        "topology": {
            "supervisor_group_id": f"group-{target}",
            "binding_integrity": "valid",
            "tracker_binding": {
                "status": "bound" if tracker_path else "unavailable",
                "tracker_path": tracker_path,
            },
            "roles": [
                {
                    "role": "routine_watcher",
                    "label": "Watcher",
                    "thread_id": f"watcher-{target}",
                    "binding_status": "bound",
                    "automation": {"owner_status": "available"},
                }
            ],
        },
        "activities": [
            {
                "record_id": "EVT-WAKE",
                "timestamp": "2026-08-09T17:57:00.000Z",
                "kind": "check",
                "mission_root": "a" * 64,
                "active_block": 6,
                "checkpoint": "Implementing",
                "action": "Continue bounded work.",
            }
        ],
        "conclusions": [
            {
                "record_id": "EVT-CONCLUSION",
                "timestamp": "2026-08-09T17:55:00.000Z",
                "kind": "meta-review",
                "status": "accepted",
                "summary": "Current semantic review accepted the predecessor.",
                "action": "Continue to the next Block.",
                "record_sha256": "c" * 64,
                "source": {"path": "events.jsonl", "line": 8},
            }
        ],
        "source": {"root": "/source/run"},
    }


def tracker(
    project_id: str,
    tracker_id: str,
    path: str,
    blocks: list[dict[str, object]],
) -> dict[str, object]:
    all_accepted = bool(blocks) and all(block["status"] == "accepted" for block in blocks)
    return {
        "id": tracker_id,
        "project_id": project_id,
        "project_label": project_id.title(),
        "relative_path": path,
        "status": "available",
        "observed_at": "2026-08-09T17:54:00.000Z",
        "fingerprint": tracker_id[0] * 64,
        "title": f"{project_id.title()} tracker",
        "tracker_status": "accepted" if all_accepted else "in-progress",
        "header_block_status_conflict": False,
        "blocks": blocks,
        "verifier": {
            "valid": bool(blocks),
            "blocks": [block["number"] for block in blocks],
        },
        "counts": {
            "total": len(blocks),
            "accepted": sum(1 for block in blocks if block["status"] == "accepted"),
            "open": sum(1 for block in blocks if block["status"] != "accepted"),
        },
        "current_blocks": [
            block["number"] for block in blocks if block["status"] == "in-progress"
        ],
        "coverage": {"status": "complete", "observed": ["tracker"], "missing": []},
        "git": {
            "status": "available",
            "content_matches_head": True,
            "worktree_changed": False,
        },
        "source": {"identity": f"tracker/{tracker_id}"},
        "raw_file": {"path": path},
    }


class FactoryFloorCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projects = [
            {"id": "alpha", "label": "Alpha"},
            {"id": "beta", "label": "Beta"},
            {"id": "gamma", "label": "Gamma"},
        ]
        alpha_path = "docs/alpha-implementation-tracker.md"
        self.trackers = [
            tracker(
                "alpha",
                "1" * 64,
                alpha_path,
                [
                    {
                        "number": 5,
                        "title": "Accepted owner adapter",
                        "status": "accepted",
                        "line": 50,
                        "completion_evidence": {"line": 80},
                    },
                    {
                        "number": 6,
                        "title": "Factory floor",
                        "status": "in-progress",
                        "line": 90,
                        "completion_evidence": None,
                    },
                ],
            ),
            tracker(
                "beta",
                "2" * 64,
                "docs/beta-implementation-tracker.md",
                [{"number": 0, "title": "Plan", "status": "not-started", "line": 12}],
            ),
        ]
        first = run("target-alpha", "alpha", tracker_path=alpha_path)
        second = run("target-beta", "alpha")
        second["topology"]["binding_integrity"] = "degraded"  # type: ignore[index]
        self.operations = {
            "fingerprint": "f" * 64,
            "runs": [first, second],
            "attention": [
                {
                    "rank": 1,
                    "rule": "open-incident",
                    "severity": "red",
                    "target_thread_id": "target-alpha",
                    "detail": "A current incident remains open.",
                    "source_identity": "supervise-tracker-runs/incidents",
                    "source_record_id": "INC-1",
                    "source_path": "events.jsonl",
                    "source_line": 7,
                    "observed_at": "2026-08-09T17:55:00.000Z",
                }
            ],
            "orphan_automations": [
                {"id": "orphan-1", "target_thread_id": "missing-target"}
            ],
            "unmonitored_projects": [
                {
                    "project_id": "gamma",
                    "reason": "No canonical supervision source binds Gamma.",
                }
            ],
            "metrics": {
                "aggregate": {
                    "available_run_count": 2,
                    "api_equivalent_estimate": {
                        "coverage_run_count": 1,
                        "totals": {"projected_cost_usd_base": 3.25},
                    },
                },
                "per_run": [
                    {"metrics": {"counts": {"by_kind": {"check": 4}}}}
                ],
            },
        }
        self.tasks = {
            "tasks": [
                task("target-alpha", "alpha", block_start=6),
                task("target-beta", "beta", "idle"),
                task("task-gamma", "gamma", "active"),
            ]
        }
        self.sources = [
            {
                "family": "catalog",
                "label": "Project catalog",
                "status": "available",
                "identity": "catalog",
                "revision": "a" * 64,
                "observed_at": OBSERVED,
                "reason": "Available",
                "coverage": {"status": "complete", "observed": [], "missing": []},
            },
            {
                "family": "tasks",
                "label": "Codex tasks",
                "status": "partial",
                "identity": "tasks",
                "revision": "b" * 64,
                "observed_at": OBSERVED,
                "reason": "Later task pages are not loaded.",
                "coverage": {
                    "status": "partial",
                    "observed": ["first-page"],
                    "missing": ["later-pages"],
                },
            },
        ]

    def compose(self) -> dict[str, object]:
        return compose_factory_floor(
            projects=self.projects,
            operations=self.operations,
            trackers=self.trackers,
            task_data=self.tasks,
            source_health=self.sources,
            observed_at=OBSERVED,
        )

    def test_pairs_exact_targets_and_keeps_disagreements_visible(self) -> None:
        floor = self.compose()
        rows = {row["id"]: row for row in floor["rows"]}  # type: ignore[index]

        alpha = rows["run:target-alpha"]
        self.assertEqual(alpha["project"]["status"], "bound")
        self.assertEqual(alpha["work"]["tracker"]["status"], "exact")
        self.assertEqual(alpha["work"]["active_block"], "6")
        self.assertEqual(alpha["work"]["block_claims"]["posture"], "exact")
        self.assertEqual(
            alpha["work"]["block_claims"]["tracker_total"],
            {
                "value": 2,
                "posture": "exact",
                "reason": "Maintained verifier Block set for the exact canonical tracker binding.",
            },
        )
        self.assertEqual(
            alpha["work"]["block_claims"]["tracker_progress"],
            {
                "accepted": 1,
                "remaining": 1,
                "posture": "exact",
                "is_complete": False,
                "reason": "Maintained tracker counts for the exact canonical tracker binding.",
            },
        )
        claims = {
            claim["source"]: claim for claim in alpha["work"]["block_claims"]["claims"]
        }
        self.assertEqual(
            {source: claim["status"] for source, claim in claims.items()},
            {"tracker": "exact", "task": "exact", "supervision": "exact"},
        )
        self.assertEqual(claims["tracker"]["blocks"][0]["title"], "Factory floor")
        self.assertEqual(alpha["light"]["posture"], "green")
        self.assertFalse(alpha["light"]["completion_claim"])
        self.assertEqual(alpha["supervision"]["group_id"], "group-target-alpha")
        self.assertEqual(alpha["supervision"]["roles"][0]["label"], "Watcher")
        self.assertEqual(
            alpha["supervision"]["roles"][0]["thread_id"],
            "watcher-target-alpha",
        )

        beta = rows["run:target-beta"]
        self.assertEqual(beta["project"]["status"], "ambiguous")
        self.assertEqual(beta["light"]["posture"], "amber")
        self.assertIn("task cwd binds project beta", beta["disagreements"][0])

        gamma = rows["task:task-gamma"]
        self.assertEqual(gamma["supervision"]["status"], "unmonitored")
        self.assertEqual(gamma["light"]["posture"], "neutral")

    def test_block_claims_preserve_multiple_conflicting_and_predecessor_sources(self) -> None:
        alpha_tracker = self.trackers[0]
        alpha_tracker["blocks"][0]["status"] = "in-progress"  # type: ignore[index]
        alpha_tracker["current_blocks"] = [5, 6]
        self.tasks["tasks"][0] = task(
            "target-alpha",
            "alpha",
            block_start=7,
        )

        row = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        claims = {claim["source"]: claim for claim in row["work"]["block_claims"]["claims"]}

        self.assertEqual(row["work"]["block_claims"]["posture"], "conflict")
        self.assertEqual(
            [block["number"] for block in claims["tracker"]["blocks"]],
            [5, 6],
        )
        self.assertEqual([block["number"] for block in claims["task"]["blocks"]], [7])
        self.assertEqual(
            [block["number"] for block in claims["supervision"]["blocks"]],
            [6],
        )
        self.assertIn("Active Block disagreement", row["disagreements"][-1])
        self.assertEqual(row["light"]["posture"], "amber")

        self.tasks["tasks"][0] = task(
            "target-alpha",
            "alpha",
            block_start=6,
            mission_root="b" * 64,
        )
        predecessor = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        task_claim = next(
            claim
            for claim in predecessor["work"]["block_claims"]["claims"]
            if claim["source"] == "task"
        )
        self.assertEqual(task_claim["status"], "conflict")
        self.assertEqual(task_claim["blocks"], [])
        self.assertIn("mission binding", task_claim["reason"])

        self.operations["runs"][0]["activities"][-1]["mission_root"] = "b" * 64  # type: ignore[index]
        predecessor_activity = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        supervision_claim = next(
            claim
            for claim in predecessor_activity["work"]["block_claims"]["claims"]
            if claim["source"] == "supervision"
        )
        self.assertEqual(supervision_claim["status"], "conflict")
        self.assertEqual(supervision_claim["blocks"], [])
        self.assertIn("predecessor mission", supervision_claim["reason"])

    def test_block_claims_treat_current_task_none_as_a_source_disagreement(self) -> None:
        self.tasks["tasks"][0] = task("target-alpha", "alpha", "idle")

        row = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        claims = {claim["source"]: claim for claim in row["work"]["block_claims"]["claims"]}

        self.assertEqual(claims["tracker"]["status"], "exact")
        self.assertEqual(claims["task"]["status"], "none")
        self.assertEqual(claims["supervision"]["status"], "exact")
        self.assertEqual(row["work"]["block_claims"]["posture"], "conflict")
        self.assertIn("Implementation task reports None active", row["disagreements"][-1])
        self.assertEqual(row["light"]["posture"], "amber")

        self.tasks["tasks"][0]["status"] = {"type": "notLoaded", "active_flags": []}  # type: ignore[index]
        unavailable = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        task_claim = next(
            claim
            for claim in unavailable["work"]["block_claims"]["claims"]
            if claim["source"] == "task"
        )
        self.assertEqual(task_claim["status"], "unavailable")
        self.assertNotIn("Implementation task reports None active", unavailable["disagreements"])

    def test_block_claims_fail_closed_for_zero_partial_and_none_active(self) -> None:
        alpha_tracker = self.trackers[0]
        alpha_tracker["blocks"] = []
        alpha_tracker["verifier"] = {"valid": False, "blocks": []}
        alpha_tracker["counts"] = {"total": 0, "accepted": 0, "open": 0}
        alpha_tracker["current_blocks"] = []
        self.operations["runs"][0]["activities"] = []  # type: ignore[index]
        self.tasks["tasks"][0] = task("target-alpha", "alpha", "idle")

        row = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )

        self.assertEqual(
            row["work"]["block_claims"]["tracker_total"]["posture"],
            "unavailable",
        )
        self.assertIsNone(row["work"]["block_claims"]["tracker_total"]["value"])
        self.assertEqual(
            row["work"]["block_claims"]["tracker_progress"],
            {
                "accepted": None,
                "remaining": None,
                "posture": "unavailable",
                "is_complete": None,
                "reason": "Maintained tracker counts cannot establish accepted and remaining Blocks.",
            },
        )
        self.assertNotEqual(row["work"]["block_claims"]["posture"], "exact")

        alpha_tracker["blocks"] = [{
            "number": 0,
            "title": "Long exact tracker-owned heading",
            "status": "accepted",
            "line": 12,
        }]
        alpha_tracker["verifier"] = {"valid": True, "blocks": [0]}
        alpha_tracker["counts"] = {"total": 1, "accepted": 1, "open": 0}
        alpha_tracker["current_blocks"] = []
        alpha_tracker["tracker_status"] = "accepted"
        none_active = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        self.assertEqual(none_active["work"]["block_claims"]["posture"], "none")
        self.assertEqual(
            none_active["work"]["block_claims"]["tracker_progress"],
            {
                "accepted": 1,
                "remaining": 0,
                "posture": "exact",
                "is_complete": True,
                "reason": "Maintained tracker counts for the exact canonical tracker binding.",
            },
        )

        alpha_tracker["tracker_status"] = "in-progress"
        alpha_tracker["header_block_status_conflict"] = True
        conflicting_header = next(
            item for item in self.compose()["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )
        self.assertEqual(
            conflicting_header["work"]["block_claims"]["tracker_progress"],
            {
                "accepted": 1,
                "remaining": 0,
                "posture": "conflict",
                "is_complete": None,
                "reason": "The tracker header status conflicts with its exact Block statuses; completion is withheld.",
            },
        )
        self.assertIn(
            "tracker header status conflicts",
            conflicting_header["disagreements"][-1].lower(),
        )
        self.assertEqual(conflicting_header["light"]["posture"], "amber")

    def test_preserves_attention_precedence_and_partial_sources(self) -> None:
        floor = self.compose()
        attention = floor["attention"]  # type: ignore[index]

        self.assertEqual(attention[0]["rule"], "open-incident")
        self.assertIn("orphan-supervisor-automation", [item["rule"] for item in attention])
        self.assertIn("unmonitored-implementation", [item["rule"] for item in attention])
        self.assertIn("source-partial-or-unavailable", [item["rule"] for item in attention])
        source_item = next(item for item in attention if item["rule"] == "source-partial-or-unavailable")
        self.assertEqual(source_item["owner"], "tasks")

    def test_conclusions_and_acceptance_come_only_from_their_owners(self) -> None:
        self.trackers[0]["blocks"][0]["status"] = "completed"  # type: ignore[index]
        floor = self.compose()
        conclusions = floor["conclusions"]  # type: ignore[index]
        outcomes = floor["accepted_outcomes"]  # type: ignore[index]

        self.assertEqual([item["id"] for item in conclusions], ["conclusion:target-alpha:EVT-CONCLUSION", "conclusion:target-beta:EVT-CONCLUSION"])
        self.assertTrue(all("EVT-WAKE" not in item["id"] for item in conclusions))
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["block"], 5)
        self.assertIsNone(outcomes[0]["accepted_at"])
        self.assertEqual(outcomes[0]["currentness"], "current")

    def test_metrics_state_period_coverage_and_estimate_truth(self) -> None:
        floor = self.compose()
        metrics = {item["key"]: item for item in floor["metrics"]}  # type: ignore[index]

        self.assertEqual(metrics["active-projects"]["value"], 2)
        self.assertEqual(metrics["unmonitored-implementations"]["value"], 1)
        self.assertEqual(metrics["orphaned-supervisors"]["value"], 1)
        self.assertEqual(metrics["blocks-in-progress"]["value"], 1)
        self.assertTrue(metrics["api-equivalent"]["estimate"])
        self.assertEqual(metrics["api-equivalent"]["unit"], "USD estimate")
        for metric in metrics.values():
            self.assertTrue(metric["period"])
            self.assertTrue(metric["coverage"])

    def test_paused_lifecycle_is_neutral_not_green_or_complete(self) -> None:
        self.operations["runs"] = [
            run(
                "target-paused",
                "alpha",
                lifecycle="paused",
                tracker_path="docs/alpha-implementation-tracker.md",
            )
        ]
        self.tasks["tasks"] = [task("target-paused", "alpha", "idle")]

        floor = self.compose()
        row = floor["rows"][0]  # type: ignore[index]

        self.assertEqual(row["light"]["posture"], "neutral")
        self.assertEqual(row["light"]["label"], "Paused")
        self.assertFalse(row["light"]["completion_claim"])

    def test_attention_bound_reports_every_omitted_critical_item(self) -> None:
        self.operations["attention"] = [
            {
                "rank": index + 1,
                "rule": "open-incident",
                "severity": "red",
                "target_thread_id": "target-alpha",
                "detail": f"Critical item {index + 1}.",
                "source_identity": "supervise-tracker-runs/incidents",
                "source_record_id": f"INC-{index + 1:03d}",
                "source_path": "events.jsonl",
                "source_line": index + 1,
                "observed_at": OBSERVED,
            }
            for index in range(81)
        ]

        floor = self.compose()

        self.assertEqual(len(floor["attention"]), 80)
        self.assertEqual(
            floor["attention_summary"],
            {
                "total": 85,
                "returned": 80,
                "truncated": True,
                "critical_total": 82,
                "critical_returned": 80,
                "critical_omitted": 2,
            },
        )
        self.assertEqual(floor["summary"]["action_required"], 82)

    def test_semantic_fingerprint_tracks_task_state_not_read_time(self) -> None:
        initial = self.compose()
        first_task = self.tasks["tasks"][0]
        first_task["status"] = {"type": "idle", "active_flags": []}

        changed = self.compose()
        later_read = compose_factory_floor(
            projects=self.projects,
            operations=self.operations,
            trackers=self.trackers,
            task_data=self.tasks,
            source_health=self.sources,
            observed_at="2026-08-09T18:05:00.000Z",
        )

        self.assertNotEqual(initial["fingerprint"], changed["fingerprint"])
        self.assertEqual(changed["fingerprint"], later_read["fingerprint"])

    def test_semantic_fingerprint_tracks_consumed_task_workflow_marker(self) -> None:
        initial = self.compose()
        self.tasks["tasks"][0] = task("target-alpha", "alpha", block_start=5)

        changed = self.compose()
        row = next(
            item for item in changed["rows"] if item["id"] == "run:target-alpha"  # type: ignore[index]
        )

        self.assertNotEqual(initial["fingerprint"], changed["fingerprint"])
        self.assertEqual(row["work"]["block_claims"]["posture"], "conflict")


if __name__ == "__main__":
    unittest.main()
