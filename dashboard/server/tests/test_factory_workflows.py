from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from test_server import FAKE_APP_SERVER, NONCE_PLACEHOLDER, response, running_server
from test_tracker import FULL_TRACKER

from dashboard.server.tests.fake_app_server import write_contract
from software_factory_dashboard.admin_operations import RouteGateRequest
from software_factory_dashboard.factory_workflows import (
    FactoryWorkflowOwner,
    SupervisionRouteGate,
)
from software_factory_dashboard.operations import DEFAULT_SUPERVISION_OWNER


def post(origin: str, path: str, payload: dict[str, object]):
    from urllib.request import Request

    return response(
        Request(
            f"{origin}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": origin,
                "X-Software-Factory-Nonce": "test-launch-nonce",
            },
        )
    )


def preview(origin: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    result = post(origin, "/api/v1/operations/preview", payload)
    return result.status, json.loads(result.body)


def execute(
    origin: str,
    request_payload: dict[str, object],
    preview_payload: dict[str, object],
) -> tuple[int, dict[str, object]]:
    operation = preview_payload["data"]["operation"]
    confirmation = operation["preview"]["confirmation"]
    result = post(
        origin,
        "/api/v1/operations/execute",
        {
            **request_payload,
            "preview_token": preview_payload["data"]["preview_token"],
            "confirmation": {
                "class": confirmation["class"],
                "value": confirmation["expected_value"],
            },
        },
    )
    return result.status, json.loads(result.body)


class FactoryWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.static_dir = self.root / "static"
        (self.static_dir / "assets").mkdir(parents=True)
        (self.static_dir / "index.html").write_text(
            f'<meta name="software-factory-mutation-nonce" content="{NONCE_PLACEHOLDER}">'
            '<main id="root"></main>',
            encoding="utf-8",
        )
        (self.static_dir / "assets" / "app.js").write_text("// fixture\n", encoding="utf-8")
        self.repository = self.root / "repository"
        self.repository.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repository)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repository), "config", "user.email", "workflow@test.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "config", "user.name", "Workflow Test"],
            check=True,
        )
        (self.repository / "README.md").write_text("# Workflow fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repository), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repository), "commit", "-qm", "initial"], check=True)
        self.compatibility = self.root / "compatibility.json"
        write_contract(self.compatibility)
        self.catalog_path = self.root / "catalog" / "projects.json"
        self.supervision_root = self.root / "supervision"
        self.automations_root = self.root / "automations"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, mode: str = "normal") -> tuple[str, ...]:
        return (
            sys.executable,
            str(FAKE_APP_SERVER),
            "--mode",
            mode,
            "--cwd",
            str(self.repository),
        )

    def register(self, origin: str) -> None:
        current = json.loads(response(f"{origin}/api/v1/projects?include_archived=true").body)
        if any(
            project["id"] == "workflow"
            for project in current["data"]["projects"]
        ):
            return
        created = post(
            origin,
            "/api/v1/projects",
            {
                "source_fingerprint": current["data"]["catalog_fingerprint"],
                "project": {
                    "id": "workflow",
                    "label": "Workflow",
                    "root": str(self.repository),
                    "tracker_patterns": [],
                    "description": None,
                },
            },
        )
        self.assertEqual(created.status, 201, created.body)

    def server(self, mode: str = "normal", *, cwd: Path | None = None):
        return running_server(
            self.static_dir,
            catalog_path=self.catalog_path,
            supervision_root=self.supervision_root,
            automations_root=self.automations_root,
            codex_command=(
                self.command(mode)
                if cwd is None
                else (
                    sys.executable,
                    str(FAKE_APP_SERVER),
                    "--mode",
                    mode,
                    "--cwd",
                    str(cwd),
                )
            ),
            codex_compatibility_path=self.compatibility,
        )

    def head(self) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def add_tracker(self) -> Path:
        tracker = self.repository / "docs" / "demo-implementation-tracker.md"
        tracker.parent.mkdir()
        tracker.write_text(FULL_TRACKER, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repository), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(self.repository), "commit", "-qm", "tracker"], check=True)
        return tracker

    def init_supervision(self, target: str = "task-fake-001") -> None:
        commands = [
            [
                "init",
                "--target-thread",
                target,
                "--target-label",
                "Workflow task",
                "--watcher-thread",
                "watcher-workflow-001",
                "--reviewer-thread",
                "reviewer-workflow-001",
                "--mission-root",
                "a" * 64,
                "--mission-source-record",
                "direct-user-item-1",
            ],
            [
                "record",
                "--target-thread",
                target,
                "--kind",
                "check",
                "--status",
                "no-intervention",
                "--state-fingerprint",
                "state-workflow-1",
                "--summary",
                "Current exact task state is available for a routed operator action.",
                "--evidence",
                "direct-user-item-1",
            ],
        ]
        for arguments in commands:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(DEFAULT_SUPERVISION_OWNER),
                    "--root",
                    str(self.supervision_root),
                    *arguments,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_closed_registry_and_author_prompt_preserve_exact_scope(self) -> None:
        with self.server() as origin:
            self.register(origin)
            framework = json.loads(response(f"{origin}/api/v1/operations").body)
            descriptors = framework["data"]["framework"]["registered_operations"]
            supported = [item["type"] for item in descriptors if item["status"] == "supported"]
            unavailable = [item for item in descriptors if item["status"] == "unavailable"]
            request_payload = {
                "operation_type": "factory.tracker-author",
                "target": {"kind": "project", "id": "workflow", "project_id": "workflow"},
                "input": {
                    "repository_head": self.head(),
                    "objective": "Build the smallest exact demo tracker; preserve this wording.",
                    "sources": ["README.md", "direct-user-item-1"],
                    "non_goals": ["Do not implement code", "Do not add a second task system"],
                },
            }
            status, previewed = preview(origin, request_payload)
            executed_status, executed = execute(origin, request_payload, previewed)
            duplicate_status, duplicate = preview(origin, request_payload)
            task = json.loads(
                response(f"{origin}/api/v1/tasks/task-fake-001?include_turns=true").body
            )["data"]["task"]

        self.assertEqual(status, 201)
        self.assertEqual(executed_status, 200)
        self.assertEqual(duplicate_status, 409)
        self.assertEqual(duplicate["error"]["code"], "authoring_owner_conflict")
        self.assertEqual(executed["data"]["operation"]["state"], "applied")
        self.assertEqual(len(supported), 10)
        self.assertIn("factory.blocks-implement", supported)
        self.assertIn("task.input-respond", supported)
        self.assertEqual(unavailable[0]["type"], "factory.tracker-authoring-supervision")
        prompt = task["turns"][0]["items"][0]["summary"]
        self.assertTrue(prompt.startswith("SOFTWARE_FACTORY_DASHBOARD_MISSION "))
        self.assertIn("$author-implementation-trackers", prompt)
        self.assertIn("Build the smallest exact demo tracker; preserve this wording.", prompt)
        self.assertIn("Do not implement it.", prompt)
        self.assertFalse(executed["data"]["operation"]["verification_evidence"]["block_accepted"])
        self.assertNotIn("smallest exact demo", json.dumps(executed["data"]["operation"]))

    def test_review_is_read_only_and_implement_enforces_range_conflict_and_tracker_truth(self) -> None:
        tracker_path = self.add_tracker()
        with self.server() as origin:
            self.register(origin)
            listed = json.loads(response(f"{origin}/api/v1/trackers").body)
            tracker = next(
                item
                for item in listed["data"]["trackers"]
                if item["relative_path"] == "docs/demo-implementation-tracker.md"
            )
            detail = json.loads(response(f"{origin}/api/v1/trackers/{tracker['id']}").body)[
                "data"
            ]["tracker"]
            base = {
                "content_sha256": sha256(tracker_path.read_bytes()).hexdigest(),
                "repository_head": self.head(),
                "verifier_profile": detail["profile"],
            }
            review_request = {
                "operation_type": "factory.tracker-review",
                "target": {
                    "kind": "tracker",
                    "id": tracker["id"],
                    "project_id": "workflow",
                },
                "input": {**base, "review_scope": "Review the full exact tracker contract."},
            }
            review_status, review_preview = preview(origin, review_request)
            _, reviewed = execute(origin, review_request, review_preview)
            review_task = json.loads(
                response(f"{origin}/api/v1/tasks/task-fake-001?include_turns=true").body
            )["data"]["task"]
            review_prompt = review_task["turns"][0]["items"][0]["summary"]

            block = next(item for item in detail["blocks"] if item["number"] == 1)
            implement_request = {
                "operation_type": "factory.blocks-implement",
                "target": review_request["target"],
                "input": {
                    **base,
                    "block_start": 1,
                    "block_end": 1,
                    "supervision": "none",
                    "expected_stop": block["stop"],
                },
            }
            implement_status, implement_preview = preview(origin, implement_request)
            _, implemented = execute(origin, implement_request, implement_preview)
            duplicate_status, duplicate = preview(origin, implement_request)
            revise_status, revise = preview(
                origin,
                {
                    "operation_type": "factory.tracker-revise",
                    "target": review_request["target"],
                    "input": {**base, "revision_scope": "Correct only one future Block."},
                },
            )
            tracker_after = json.loads(
                response(f"{origin}/api/v1/trackers/{tracker['id']}").body
            )["data"]["tracker"]

        self.assertEqual(review_status, 201)
        self.assertEqual(reviewed["data"]["operation"]["state"], "applied")
        self.assertIn("Quality-check this tracker read-only.", review_prompt)
        self.assertIn("Do not edit files", review_prompt)
        self.assertEqual(implement_status, 201)
        self.assertEqual(implemented["data"]["operation"]["state"], "applied")
        self.assertEqual(duplicate_status, 409)
        self.assertEqual(duplicate["error"]["code"], "implementation_owner_conflict")
        self.assertEqual(revise_status, 409)
        self.assertEqual(revise["error"]["code"], "tracker_writer_conflict")
        self.assertEqual(tracker_after["blocks"][1]["status"], "not-started")
        self.assertFalse(implemented["data"]["operation"]["verification_evidence"]["block_accepted"])

    def test_stale_or_dirty_implementation_and_partial_turn_start_fail_closed(self) -> None:
        tracker_path = self.add_tracker()
        with self.server() as origin:
            self.register(origin)
            tracker = json.loads(response(f"{origin}/api/v1/trackers").body)["data"][
                "trackers"
            ][0]
            detail = json.loads(response(f"{origin}/api/v1/trackers/{tracker['id']}").body)[
                "data"
            ]["tracker"]
            block = detail["blocks"][1]
            clean_input = {
                "content_sha256": detail["raw_file"]["content_sha256"],
                "repository_head": detail["git"]["repository_head"],
                "verifier_profile": detail["profile"],
                "block_start": 1,
                "block_end": 1,
                "supervision": "none",
                "expected_stop": block["stop"],
            }
            tracker_path.write_text(FULL_TRACKER + "\n<!-- dirty -->\n", encoding="utf-8")
            dirty_status, dirty = preview(
                origin,
                {
                    "operation_type": "factory.blocks-implement",
                    "target": {
                        "kind": "tracker",
                        "id": tracker["id"],
                        "project_id": "workflow",
                    },
                    "input": clean_input,
                },
            )
        self.assertEqual(dirty_status, 409)
        self.assertEqual(dirty["error"]["code"], "tracker_content_stale")

        subprocess.run(["git", "-C", str(self.repository), "restore", str(tracker_path)], check=True)
        with self.server("turn-start-fails") as origin:
            self.register(origin)
            author_request = {
                "operation_type": "factory.tracker-author",
                "target": {"kind": "project", "id": "workflow", "project_id": "workflow"},
                "input": {
                    "repository_head": self.head(),
                    "objective": "Author a bounded tracker.",
                    "sources": ["README.md"],
                    "non_goals": ["Do not implement"],
                },
            }
            _, author_preview = preview(origin, author_request)
            _, partial = execute(origin, author_request, author_preview)
        operation = partial["data"]["operation"]
        self.assertEqual(operation["state"], "failed")
        self.assertEqual(operation["request_evidence"]["task_started"], True)
        self.assertEqual(operation["request_evidence"]["turn_started"], False)
        self.assertEqual(operation["links"][0]["href"], "/tasks/task-fake-001")

    def test_continue_is_distinct_from_steer_and_lifecycle(self) -> None:
        with self.server() as origin:
            self.register(origin)
            request_payload = {
                "operation_type": "task.continue",
                "target": {
                    "kind": "task",
                    "id": "task-fake-001",
                    "project_id": "workflow",
                },
                "input": {"text": "Continue only the exact bounded work."},
            }
            status, previewed = preview(origin, request_payload)
            _, continued = execute(origin, request_payload, previewed)
            second_status, second = preview(origin, request_payload)
            steer_without_route_status, steer_without_route = preview(
                origin,
                {
                    "operation_type": "task.steer",
                    "target": request_payload["target"],
                    "input": {
                        "turn_id": "turn-active-001",
                        "text": "Narrow the active turn.",
                    },
                },
            )
        self.assertEqual(status, 201)
        self.assertEqual(continued["data"]["operation"]["state"], "applied")
        evidence = continued["data"]["operation"]["verification_evidence"]
        self.assertTrue(evidence["task_turn_started"])
        self.assertFalse(evidence["lifecycle_changed"])
        self.assertFalse(evidence["block_accepted"])
        self.assertFalse(evidence["outcome_verified"])
        self.assertEqual(second_status, 409)
        self.assertEqual(second["error"]["code"], "task_state_mismatch")
        self.assertEqual(steer_without_route_status, 409)
        self.assertEqual(steer_without_route["error"]["code"], "route_gate_unavailable")

    def test_wrong_cwd_and_partial_supervision_setup_never_claim_owner_state(self) -> None:
        tracker_path = self.add_tracker()
        wrong_cwd = self.root / "unregistered"
        wrong_cwd.mkdir()
        with self.server(cwd=wrong_cwd) as origin:
            self.register(origin)
            author_request = {
                "operation_type": "factory.tracker-author",
                "target": {"kind": "project", "id": "workflow", "project_id": "workflow"},
                "input": {
                    "repository_head": self.head(),
                    "objective": "Author one exact tracker.",
                    "sources": ["README.md"],
                    "non_goals": ["Do not implement"],
                },
            }
            _, author_preview = preview(origin, author_request)
            _, wrong_cwd_result = execute(origin, author_request, author_preview)
        self.assertEqual(wrong_cwd_result["data"]["operation"]["state"], "failed")
        self.assertFalse(
            wrong_cwd_result["data"]["operation"]["verification_evidence"].get(
                "turn_started", True
            )
        )

        with self.server("active") as origin:
            self.register(origin)
            tracker = json.loads(response(f"{origin}/api/v1/trackers").body)["data"][
                "trackers"
            ][0]
            detail = json.loads(response(f"{origin}/api/v1/trackers/{tracker['id']}").body)[
                "data"
            ]["tracker"]
            attach_request = {
                "operation_type": "factory.supervision-attach",
                "target": {
                    "kind": "task",
                    "id": "task-fake-001",
                    "project_id": "workflow",
                },
                "input": {
                    "tracker_id": tracker["id"],
                    "content_sha256": sha256(tracker_path.read_bytes()).hexdigest(),
                    "repository_head": self.head(),
                    "verifier_profile": detail["profile"],
                    "block_start": 0,
                    "block_end": 1,
                    "mission_root": "a" * 64,
                    "mission_source_record": "direct-user-item-1",
                },
            }
            attach_status, attach_preview = preview(origin, attach_request)
            _, attached = execute(origin, attach_request, attach_preview)
        self.assertEqual(attach_status, 201)
        self.assertNotEqual(attached["data"]["operation"]["state"], "applied")
        self.assertFalse(
            attached["data"]["operation"]["verification_evidence"][
                "supervision_attached"
            ]
        )

    def test_markers_accept_list_preview_and_route_helper_rejects_symlink(self) -> None:
        marker = {
            "kind": "implement-blocks",
            "tracker_id": "a" * 64,
            "block_start": 2,
            "block_end": 3,
        }
        task = {
            "preview": "SOFTWARE_FACTORY_DASHBOARD_MISSION "
            + json.dumps(marker, separators=(",", ":")),
            "turns": [],
        }
        self.assertEqual(FactoryWorkflowOwner._task_marker(task), marker)

        helper = self.root / "helper.py"
        helper.write_text("raise SystemExit(0)\n", encoding="utf-8")
        link = self.root / "helper-link.py"
        link.symlink_to(helper)
        gate = SupervisionRouteGate(
            supervision_root=self.supervision_root,
            helper_path=link,
        )
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            gate(
                RouteGateRequest(
                    recipient="task-1",
                    purpose="target-action",
                    source_record="EVT-1",
                    required_action="Do one exact action.",
                )
            )

    def test_routed_steer_interrupt_approval_and_input_use_exact_owner_records(self) -> None:
        self.init_supervision()
        with self.server("active") as origin:
            self.register(origin)
            target = {"kind": "task", "id": "task-fake-001", "project_id": "workflow"}
            steer_request = {
                "operation_type": "task.steer",
                "target": target,
                "input": {"turn_id": "turn-active-001", "text": "Keep only the selected scope."},
            }
            steer_status, steer_preview = preview(origin, steer_request)
            _, steered = execute(origin, steer_request, steer_preview)
            interrupt_request = {
                "operation_type": "task.interrupt",
                "target": target,
                "input": {"turn_id": "turn-active-001"},
            }
            interrupt_status, interrupt_preview = preview(origin, interrupt_request)
            _, interrupted = execute(origin, interrupt_request, interrupt_preview)

        self.assertEqual(steer_status, 201)
        self.assertEqual(
            steer_preview["data"]["operation"]["preview"]["route_gate"]["status"],
            "allowed",
        )
        self.assertEqual(steered["data"]["operation"]["state"], "applied")
        self.assertEqual(interrupt_status, 201)
        self.assertEqual(interrupted["data"]["operation"]["state"], "applied")
        interrupt_evidence = interrupted["data"]["operation"]["verification_evidence"]
        self.assertFalse(interrupt_evidence["supervision_paused"])
        self.assertFalse(interrupt_evidence["mission_stopped"])
        self.assertFalse(interrupt_evidence["work_accepted"])

        for mode, operation_type, response_field in (
            ("approval", "task.approval-respond", "decision"),
            ("user-input", "task.input-respond", "answers"),
        ):
            with self.server(mode) as origin:
                self.register(origin)
                listing = json.loads(response(f"{origin}/api/v1/tasks?limit=10").body)
                request = listing["data"]["pending_requests"][0]
                inputs: dict[str, object] = {
                    "source_fingerprint": request["source_fingerprint"],
                    "task_id": request["task_id"],
                    "turn_id": request["turn_id"],
                    "item_id": request["item_id"],
                }
                inputs[response_field] = (
                    "decline" if response_field == "decision" else {"choice": ["First"]}
                )
                request_payload = {
                    "operation_type": operation_type,
                    "target": {
                        "kind": "task-request",
                        "id": request["id"],
                        "project_id": "workflow",
                    },
                    "input": inputs,
                }
                response_status, response_preview = preview(origin, request_payload)
                _, responded = execute(origin, request_payload, response_preview)
                pending_after = json.loads(response(f"{origin}/api/v1/tasks?limit=10").body)[
                    "data"
                ]["pending_requests"]
            self.assertEqual(response_status, 201)
            self.assertEqual(responded["data"]["operation"]["state"], "applied")
            self.assertEqual(pending_after, [])


if __name__ == "__main__":
    unittest.main()
