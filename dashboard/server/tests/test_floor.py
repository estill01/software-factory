from __future__ import annotations

import unittest

from software_factory_dashboard.floor import compose_factory_floor


OBSERVED = "2026-08-09T18:00:00.000Z"


def task(task_id: str, project_id: str, status: str = "active") -> dict[str, object]:
    return {
        "id": task_id,
        "name": f"Task {task_id}",
        "status": {"type": status, "active_flags": []},
        "project_binding": {
            "status": "bound",
            "project_id": project_id,
            "candidates": [project_id],
        },
        "updated_at": "2026-08-09T17:59:00.000Z",
        "recency_at": "2026-08-09T17:59:00.000Z",
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
        "current_mission": {"root": "m" * 64},
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
    return {
        "id": tracker_id,
        "project_id": project_id,
        "project_label": project_id.title(),
        "relative_path": path,
        "status": "available",
        "observed_at": "2026-08-09T17:54:00.000Z",
        "fingerprint": tracker_id[0] * 64,
        "title": f"{project_id.title()} tracker",
        "blocks": blocks,
        "counts": {
            "accepted": sum(1 for block in blocks if block["status"] == "accepted"),
            "open": sum(1 for block in blocks if block["status"] != "accepted"),
        },
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
                task("target-alpha", "alpha"),
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
        self.assertEqual(alpha["light"]["posture"], "green")
        self.assertFalse(alpha["light"]["completion_claim"])

        beta = rows["run:target-beta"]
        self.assertEqual(beta["project"]["status"], "ambiguous")
        self.assertEqual(beta["light"]["posture"], "amber")
        self.assertIn("task cwd binds project beta", beta["disagreements"][0])

        gamma = rows["task:task-gamma"]
        self.assertEqual(gamma["supervision"]["status"], "unmonitored")
        self.assertEqual(gamma["light"]["posture"], "neutral")

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


if __name__ == "__main__":
    unittest.main()
