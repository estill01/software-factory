from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import RLock
import unittest
from unittest.mock import patch

from test_server import FAKE_APP_SERVER, NONCE_PLACEHOLDER, response, running_server
from test_tracker import FULL_TRACKER

from dashboard.server.tests.fake_app_server import write_contract
from software_factory_dashboard.admin_operations import (
    OperationError,
    OperationOwnerError,
    OperationTarget,
    RouteGateRequest,
    RouteGateResult,
)
from software_factory_dashboard.catalog import ProjectRecord
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
        self.assertEqual(len(supported), 14)
        self.assertIn("factory.blocks-implement", supported)
        self.assertIn("factory.supervision-check-now", supported)
        self.assertIn("factory.supervision-review-checkpoint", supported)
        self.assertIn("factory.supervision-review-meta", supported)
        self.assertIn("factory.supervision-review-issue", supported)
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
                    "mission_root": "a" * 64,
                    "mission_source_record": "direct-user-item-1",
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

    def test_writer_gate_rejects_unbound_active_task_and_nonoverlapping_second_owner(self) -> None:
        tracker_path = self.add_tracker()
        with self.server("active") as origin:
            self.register(origin)
            tracker = json.loads(response(f"{origin}/api/v1/trackers").body)["data"][
                "trackers"
            ][0]
            detail = json.loads(response(f"{origin}/api/v1/trackers/{tracker['id']}").body)[
                "data"
            ]["tracker"]
            block = next(item for item in detail["blocks"] if item["number"] == 1)
            status, result = preview(
                origin,
                {
                    "operation_type": "factory.blocks-implement",
                    "target": {
                        "kind": "tracker",
                        "id": tracker["id"],
                        "project_id": "workflow",
                    },
                    "input": {
                        "content_sha256": sha256(tracker_path.read_bytes()).hexdigest(),
                        "repository_head": self.head(),
                        "verifier_profile": detail["profile"],
                        "block_start": 1,
                        "block_end": 1,
                        "supervision": "none",
                        "expected_stop": block["stop"],
                        "mission_root": "a" * 64,
                        "mission_source_record": "direct-user-item-1",
                    },
                },
            )
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "tracker_writer_identity_unavailable")

        owner = object.__new__(FactoryWorkflowOwner)
        owner._task_listing = lambda _project: (  # type: ignore[method-assign]
            {
                "status": {"type": "active"},
                "preview": "SOFTWARE_FACTORY_DASHBOARD_MISSION "
                + json.dumps(
                    {
                        "kind": "implement-blocks",
                        "tracker_id": tracker["id"],
                        "block_start": 2,
                        "block_end": 2,
                    },
                    separators=(",", ":"),
                ),
                "turns": [],
            },
        )
        with self.assertRaises(OperationError) as context:
            owner._assert_no_conflicting_tracker_writer(
                project=ProjectRecord(id="workflow", label="Workflow", root=str(self.repository)),
                tracker_id=tracker["id"],
                purpose="implement",
            )
        self.assertEqual(context.exception.code, "implementation_owner_conflict")

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
                "mission_root": "a" * 64,
                "mission_source_record": "direct-user-item-1",
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

        with self.server() as origin:
            self.register(origin)
            tracker = json.loads(response(f"{origin}/api/v1/trackers").body)["data"][
                "trackers"
            ][0]
            detail = json.loads(response(f"{origin}/api/v1/trackers/{tracker['id']}").body)[
                "data"
            ]["tracker"]
            block = next(item for item in detail["blocks"] if item["number"] == 1)
            implementation_request = {
                "operation_type": "factory.blocks-implement",
                "target": {
                    "kind": "tracker",
                    "id": tracker["id"],
                    "project_id": "workflow",
                },
                "input": {
                    "content_sha256": sha256(tracker_path.read_bytes()).hexdigest(),
                    "repository_head": self.head(),
                    "verifier_profile": detail["profile"],
                    "block_start": 1,
                    "block_end": 1,
                    "supervision": "none",
                    "expected_stop": block["stop"],
                    "mission_root": "a" * 64,
                    "mission_source_record": "direct-user-item-1",
                },
            }
            _, implementation_preview = preview(origin, implementation_request)
            execute(origin, implementation_request, implementation_preview)
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
                    "block_start": 1,
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

        newer_marker = {**marker, "tracker_id": "b" * 64}
        task["turns"] = [
            {
                "items": [
                    {
                        "type": "userMessage",
                        "summary": "SOFTWARE_FACTORY_DASHBOARD_MISSION "
                        + json.dumps(newer_marker, separators=(",", ":")),
                    }
                ]
            }
        ]
        self.assertEqual(FactoryWorkflowOwner._task_marker(task), newer_marker)

        helper = self.root / "helper.py"
        helper.write_text("raise SystemExit(0)\n", encoding="utf-8")
        link = self.root / "helper-link.py"
        link.symlink_to(helper)
        gate = SupervisionRouteGate(
            supervision_root=self.supervision_root,
            helper_path=link,
        )
        route_request = RouteGateRequest(
            recipient="task-1",
            purpose="target-action",
            source_record="EVT-1",
            required_action="Do one exact action.",
        )
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            gate(route_request)

        regular = self.root / "regular-helper.py"
        regular.write_text("raise SystemExit(1)\n", encoding="utf-8")
        replacement_gate = SupervisionRouteGate(
            supervision_root=self.supervision_root,
            helper_path=regular,
        )
        forged = self.root / "forged-helper.py"
        forged.write_text("print('{}')\n", encoding="utf-8")
        regular.unlink()
        regular.symlink_to(forged)
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            replacement_gate(route_request)

        immutable = self.root / "immutable-helper.py"
        immutable.write_text(
            "import json\n"
            "print(json.dumps({'send_allowed': True, 'action_sha256': 'a' * 64, "
            "'recipient_thread_id': 'task-1', 'purpose': 'target-action', "
            "'source_record': 'EVT-1', 'policy_sha256': 'b' * 64}))\n",
            encoding="utf-8",
        )
        immutable_gate = SupervisionRouteGate(
            supervision_root=self.supervision_root,
            helper_path=immutable,
        )
        real_run = subprocess.run

        def replace_before_execution(*args, **kwargs):
            immutable.write_text(
                "import json\n"
                "print(json.dumps({'send_allowed': True, 'action_sha256': 'f' * 64, "
                "'recipient_thread_id': 'forged-task', 'purpose': 'target-action', "
                "'source_record': 'EVT-1', 'policy_sha256': 'f' * 64}))\n",
                encoding="utf-8",
            )
            return real_run(*args, **kwargs)

        with patch(
            "software_factory_dashboard.factory_workflows.subprocess.run",
            side_effect=replace_before_execution,
        ):
            immutable_result = immutable_gate(route_request)
        self.assertEqual(immutable_result.recipient, "task-1")
        self.assertEqual(immutable_result.action_hash, "a" * 64)

    def test_attachment_requires_exact_role_tasks_active_automations_and_cadence(self) -> None:
        target = OperationTarget(
            kind="task",
            id="implementation-task-1",
            project_id="workflow",
        )
        inputs = {
            "tracker_id": "b" * 64,
            "block_start": 1,
            "block_end": 2,
            "mission_root": "a" * 64,
            "mission_source_record": "direct-user-item-1",
        }
        marker = {
            "kind": "implement-blocks",
            "source_fingerprint": "c" * 64,
            "project_id": "workflow",
            "tracker_id": inputs["tracker_id"],
            "block_start": 1,
            "block_end": 2,
            "mission_root": inputs["mission_root"],
            "mission_source_record": inputs["mission_source_record"],
        }
        tasks = {
            target.id: {
                "id": target.id,
                "status": {"type": "idle"},
                "project_binding": {
                    "status": "bound",
                    "project_id": "workflow",
                    "candidates": ["workflow"],
                },
                "preview": "SOFTWARE_FACTORY_DASHBOARD_MISSION "
                + json.dumps(marker, separators=(",", ":")),
                "turns": [],
            },
        }

        class AppServerStub:
            def read_task(self, _projects, task_id, *, include_turns):
                del include_turns
                return {"task": tasks[task_id]}

        owner = object.__new__(FactoryWorkflowOwner)
        owner.app_server_client = AppServerStub()
        policy_sha = "d" * 64
        base_run = {
            "status": "available",
            "fingerprint": "e" * 64,
            "current_mission": {
                "root": inputs["mission_root"],
                "source_record": inputs["mission_source_record"],
            },
            "lifecycle": {"status": None},
            "policy": {
                "version": 1,
                "sha256": policy_sha,
                "schedule": {"routine_minutes": 20, "meta_review_hours": 4},
            },
            "policy_history": [{"policy_sha256": policy_sha}],
            "source": {"policy_head_sha256": policy_sha},
            "topology": {
                "project_binding": {"status": "bound", "project_id": "workflow"},
                "binding_integrity": "valid",
                "roles": [
                    {
                        "role": "watcher",
                        "thread_id": "watcher-task-1",
                        "binding_status": "bound",
                        "automation": {
                            "id": "watcher-automation-1",
                            "status": "available",
                            "owner_status": "ACTIVE",
                            "kind": "heartbeat",
                            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                            "target_thread_id": "watcher-task-1",
                        },
                    }
                ],
            },
        }
        project = ProjectRecord(id="workflow", label="Workflow", root=str(self.repository))
        partial = owner._supervision_attachment_evidence(
            projects=(project,),
            target=target,
            inputs=inputs,
            run=base_run,
        )
        self.assertFalse(partial["supervision_attached"])
        self.assertFalse(partial["required_role_family_current"])

        roles = []
        role_ids = {
            "watcher": "watcher-task-1",
            "base_reviewer": "base-reviewer-task-1",
            "reviewer": "reviewer-task-1",
            "fix_executor": "fix-executor-task-1",
        }
        for role_name, task_id in role_ids.items():
            tasks[task_id] = {
                "id": task_id,
                "status": {"type": "idle"},
                "project_binding": {
                    "status": "unregistered",
                    "project_id": None,
                    "candidates": [],
                },
                "preview": "Supervisor role",
                "turns": [],
            }
            automation = None
            if role_name == "watcher":
                automation = {
                    "id": "watcher-automation-1",
                    "status": "available",
                    "owner_status": "ACTIVE",
                    "kind": "heartbeat",
                    "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                    "target_thread_id": task_id,
                }
            elif role_name == "reviewer":
                automation = {
                    "id": "reviewer-automation-1",
                    "status": "available",
                    "owner_status": "ACTIVE",
                    "kind": "heartbeat",
                    "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                    "target_thread_id": task_id,
                }
            roles.append(
                {
                    "role": role_name,
                    "thread_id": task_id,
                    "binding_status": "bound",
                    "automation": automation,
                }
            )
        exact_run = {
            **base_run,
            "topology": {**base_run["topology"], "roles": roles},
        }
        exact = owner._supervision_attachment_evidence(
            projects=(project,),
            target=target,
            inputs=inputs,
            run=exact_run,
        )
        self.assertTrue(exact["supervision_attached"])
        self.assertTrue(exact["role_tasks_current"])
        self.assertTrue(exact["automation_current"])

    def test_check_now_wakes_one_exact_watcher_and_requires_matching_new_record(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        role_workspace = self.root / "watcher-workspace"
        role_workspace.mkdir()
        target_task = {
            "id": "task-fake-001",
            "status": {"type": "idle"},
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
        }
        watcher_task = {
            "id": "watcher-workflow-001",
            "status": {"type": "idle"},
            "cwd": str(role_workspace),
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
            "preview": "Watcher",
            "turns": [],
        }
        run = {
            "status": "available",
            "target_thread_id": "task-fake-001",
            "fingerprint": "c" * 64,
            "event_count": 4,
            "current_mission": {"root": "a" * 64},
            "project_binding": {"status": "bound", "project_id": "workflow"},
            "lifecycle": {"status": None},
            "last_check": {"record_id": "EVT-000004", "timestamp": "2026-08-10T00:00:00Z"},
            "latest_activity": {"record_id": "EVT-000004", "timestamp": "2026-08-10T00:00:00Z"},
            "policy": {"schedule": {"routine_minutes": 20}},
            "source": {
                "policy_head_sha256": "b" * 64,
                "event_head_sha256": "d" * 64,
            },
            "topology": {
                "binding_integrity": "valid",
                "roles": [
                    {
                        "role": "watcher",
                        "thread_id": "watcher-workflow-001",
                        "binding_status": "bound",
                        "automation": {
                            "id": "watcher-automation-001",
                            "status": "available",
                            "owner_status": "ACTIVE",
                            "kind": "heartbeat",
                            "target_thread_id": "watcher-workflow-001",
                            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                            "manifest_sha256": "e" * 64,
                        },
                    }
                ]
            },
            "timeline": [],
        }

        class OperationsStub:
            def run(self, _projects, target_thread_id):
                if target_thread_id != run["target_thread_id"]:
                    raise AssertionError("wrong target")
                return {"selected_run": run}

        class AppServerStub:
            prompt = None

            @staticmethod
            def integration_state():
                return {
                    "features": [
                        {"capability": "task_read", "status": "supported"},
                        {"capability": "task_resume", "status": "supported"},
                        {"capability": "turn_start", "status": "supported"},
                    ]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id == target_task["id"] and not include_turns:
                    return {"task": target_task}
                if not include_turns or task_id != watcher_task["id"]:
                    raise AssertionError("wrong watcher read")
                return {"task": watcher_task}

            def start_configured_role_turn(
                self,
                _projects,
                task_id,
                text,
                *,
                expected_cwd,
                expected_cwd_identity,
            ):
                role_stat = role_workspace.stat()
                if (
                    task_id != watcher_task["id"]
                    or expected_cwd != str(role_workspace)
                    or expected_cwd_identity != (role_stat.st_dev, role_stat.st_ino)
                ):
                    raise AssertionError("wrong watcher wake")
                self.prompt = text
                return {"turn": {"id": "turn-check-001"}, "task_resumed": False}

        app_server = AppServerStub()
        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = app_server
        owner.route_gate = lambda request: RouteGateResult(
            allowed=True,
            action_hash="f" * 64,
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint="b" * 64,
            target_thread=request.target_thread,
        )
        owner._check_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "9" * 64)  # type: ignore[method-assign]
        target = OperationTarget(
            kind="run",
            id="task-fake-001",
            project_id="workflow",
        )
        definition = owner._check_now_definition()
        source = definition.resolve_source(target, {})
        route = definition.route_gate_request(target, {}, source)
        self.assertEqual(route.target_thread, target.id)
        self.assertEqual(route.recipient, watcher_task["id"])
        self.assertEqual(route.purpose, "watcher-action")
        dispatched = definition.dispatch(target, {}, source)
        self.assertTrue(dispatched.evidence["watcher_awakened"])
        self.assertIn(f"dashboard-preview:{source.fingerprint}", app_server.prompt)

        unrelated = definition.verify(target, {}, source, dispatched)
        self.assertEqual(unrelated.state, "pending")
        run["event_count"] = 5
        run["timeline"] = [
            {
                "record_id": "EVT-000005",
                "timestamp": "2026-08-10T00:00:30Z",
                "kind": "check",
                "status": "no-intervention",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:target-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 5},
            },
        ]
        unrelated = definition.verify(target, {}, source, dispatched)
        self.assertEqual(unrelated.state, "pending")
        self.assertTrue(unrelated.evidence["unrelated_newer_event"])
        run["event_count"] = 6
        run["timeline"].append(
            {
                "record_id": "EVT-000006",
                "timestamp": "2026-08-10T00:00:45Z",
                "kind": "check",
                "status": "verified",
                "category": "observable-outcome-completion",
                "severity": "info",
                "action": "Accept implementation.",
                "resolution": "Outcome complete.",
                "resolution_owner": "reviewer",
                "notice_disposition": "terminal",
                "user_action_required": "no",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:watcher-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 6},
            }
        )
        semantic = definition.verify(target, {}, source, dispatched)
        self.assertEqual(semantic.state, "pending")
        self.assertFalse(semantic.evidence["check_recorded"])

        run["event_count"] = 7
        run["timeline"].append(
            {
                "record_id": "EVT-000007",
                "timestamp": "2026-08-10T00:01:00Z",
                "kind": "check",
                "status": "no-intervention",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:watcher-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 7},
            }
        )
        partial = definition.verify(target, {}, source, dispatched)
        self.assertEqual(partial.state, "pending")
        self.assertFalse(partial.evidence["check_recorded"])

        run["event_count"] = 8
        run["timeline"].append(
            {
                "kind": "check",
                "status": "no-intervention",
                "category": "",
                "severity": "info",
                "action": "",
                "resolution": "",
                "resolution_owner": "",
                "notice_disposition": "",
                "user_action_required": "",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:watcher-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 8},
            }
        )
        identityless = definition.verify(target, {}, source, dispatched)
        self.assertEqual(identityless.state, "pending")
        self.assertFalse(identityless.evidence["check_recorded"])

        run["event_count"] = 9
        run["timeline"].append(
            {
                "record_id": "EVT-000009",
                "timestamp": "2026-08-10T00:01:00Z",
                "kind": "check",
                "status": "no-intervention",
                "category": "",
                "severity": "info",
                "action": "",
                "resolution": "",
                "resolution_owner": "",
                "notice_disposition": "",
                "user_action_required": "",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:watcher-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 9},
            }
        )
        verified = definition.verify(target, {}, source, dispatched)
        self.assertEqual(verified.state, "applied")
        self.assertTrue(verified.evidence["check_recorded"])
        self.assertEqual(verified.evidence["check_record_kind"], "check")
        self.assertFalse(verified.evidence["changed_state_routed"])
        self.assertFalse(verified.evidence["semantic_conclusion"])

        run["event_count"] = 10
        run["timeline"] = [
            {
                "record_id": "EVT-000010",
                "timestamp": "2026-08-10T00:01:15Z",
                "kind": "escalation",
                "status": "routed",
                "category": "changed-state-review",
                "severity": "info",
                "action": "Read the exact changed target delta and perform independent semantic review.",
                "resolution": "",
                "resolution_owner": "supervisor",
                "notice_disposition": "",
                "user_action_required": "no",
                "state_fingerprint": source.fingerprint,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:watcher-action",
                    f"dashboard-preview:{source.fingerprint}",
                ],
                "source": {"line": 10},
            }
        ]
        routed = definition.verify(target, {}, source, dispatched)
        self.assertEqual(routed.state, "applied")
        self.assertEqual(routed.evidence["check_record_kind"], "escalation")
        self.assertTrue(routed.evidence["changed_state_routed"])
        self.assertFalse(routed.evidence["semantic_conclusion"])

        run["event_count"] = 5
        run["timeline"] = []
        watcher_task["turns"] = [
            {
                "id": "turn-check-001",
                "status": "completed",
                "items": [
                    {
                        "type": "userMessage",
                        "summary": app_server.prompt,
                    }
                ],
            }
        ]
        with self.assertRaises(OperationError) as duplicate:
            definition.resolve_source(target, {})
        self.assertEqual(duplicate.exception.code, "check_unverified_active")

        watcher_task["status"] = {"type": "active"}
        with self.assertRaises(OperationError) as active:
            definition.resolve_source(target, {})
        self.assertEqual(active.exception.code, "check_active")

        watcher_task["status"] = {"type": "idle"}
        watcher_role = run["topology"]["roles"][0]
        run["topology"]["roles"] = []
        with self.assertRaises(OperationError) as missing_watcher:
            definition.resolve_source(target, {})
        self.assertEqual(missing_watcher.exception.code, "watcher_binding_unavailable")

        run["topology"]["roles"] = [{**watcher_role, "automation": None}]
        with self.assertRaises(OperationError) as missing_automation:
            definition.resolve_source(target, {})
        self.assertEqual(missing_automation.exception.code, "watcher_binding_unavailable")

    def test_semantic_review_requests_bind_role_source_conclusion_and_supersession(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        role_workspace = self.root / "reviewer-workspace"
        role_workspace.mkdir()
        target_task = {
            "id": "task-fake-001",
            "status": {"type": "idle"},
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
        }
        tasks = {
            "reviewer-workflow-001": {
                "id": "reviewer-workflow-001",
                "status": {"type": "idle"},
                "cwd": str(role_workspace),
                "project_binding": {
                    "status": "unregistered",
                    "project_id": None,
                    "candidates": [],
                },
                "preview": "Semantic reviewer",
                "turns": [],
            },
            "notice-workflow-001": {
                "id": "notice-workflow-001",
                "status": {"type": "idle"},
                "cwd": str(role_workspace),
                "project_binding": {
                    "status": "unregistered",
                    "project_id": None,
                    "candidates": [],
                },
                "preview": "Notice reviewer",
                "turns": [],
            },
        }
        run = {
            "status": "available",
            "target_thread_id": "task-fake-001",
            "fingerprint": "c" * 64,
            "event_count": 4,
            "current_mission": {"root": "a" * 64},
            "project_binding": {"status": "bound", "project_id": "workflow"},
            "lifecycle": {"status": None},
            "last_check": {"record_id": "EVT-000003"},
            "latest_activity": {"record_id": "EVT-000004"},
            "latest_conclusion": None,
            "source": {
                "policy_head_sha256": "b" * 64,
                "event_head_sha256": "d" * 64,
            },
            "topology": {
                "binding_integrity": "valid",
                "roles": [
                    {
                        "role": "reviewer",
                        "thread_id": "reviewer-workflow-001",
                        "binding_status": "bound",
                        "automation": None,
                    },
                    {
                        "role": "notice_reviewer",
                        "thread_id": "notice-workflow-001",
                        "binding_status": "bound",
                        "automation": None,
                    },
                ],
            },
            "incidents": [
                {
                    "incident_id": "INC-20260810-TEST",
                    "open": True,
                    "head": {
                        "record_id": "EVT-000004",
                        "status": "open",
                        "summary": "Exact open test incident.",
                    },
                }
            ],
            "timeline": [],
        }

        class OperationsStub:
            def run(self, _projects, target_thread_id):
                if target_thread_id != run["target_thread_id"]:
                    raise AssertionError("wrong target")
                return {"selected_run": run}

        class AppServerStub:
            prompts: dict[str, str] = {}

            @staticmethod
            def integration_state():
                return {
                    "features": [
                        {"capability": "task_read", "status": "supported"},
                        {"capability": "task_resume", "status": "supported"},
                        {"capability": "turn_start", "status": "supported"},
                    ]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id == target_task["id"] and not include_turns:
                    return {"task": target_task}
                if task_id not in tasks or not include_turns:
                    raise AssertionError("wrong reviewer read")
                return {"task": tasks[task_id]}

            def start_configured_role_turn(
                self,
                _projects,
                task_id,
                text,
                *,
                expected_cwd,
                expected_cwd_identity,
            ):
                role_stat = role_workspace.stat()
                if (
                    task_id not in tasks
                    or expected_cwd != str(role_workspace)
                    or expected_cwd_identity != (role_stat.st_dev, role_stat.st_ino)
                ):
                    raise AssertionError("wrong reviewer dispatch")
                self.prompts[task_id] = text
                tasks[task_id]["turns"] = [
                    {
                        "id": f"turn-{task_id}",
                        "status": "completed",
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": f"turn-{task_id}"},
                    "task_resumed": False,
                }

        app_server = AppServerStub()
        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = app_server
        owner.route_gate = lambda request: RouteGateResult(
            allowed=True,
            action_hash="f" * 64,
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint="b" * 64,
            target_thread=request.target_thread,
        )
        owner._review_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "9" * 64)  # type: ignore[method-assign]
        target = OperationTarget(kind="run", id="task-fake-001", project_id="workflow")

        checkpoint = owner._semantic_review_definition("checkpoint")
        source = checkpoint.resolve_source(target, {})
        route = checkpoint.route_gate_request(target, {}, source)
        self.assertEqual(route.recipient, "reviewer-workflow-001")
        self.assertEqual(route.purpose, "semantic-escalation")
        dispatched = checkpoint.dispatch(target, {}, source)
        self.assertTrue(dispatched.evidence["review_task_started"])
        self.assertIn(f"dashboard-preview:{source.fingerprint}", app_server.prompts[route.recipient])
        pending = checkpoint.verify(target, {}, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["request_delivery_is_conclusion"])
        tasks["reviewer-workflow-001"]["turns"].append(
            {
                "id": "turn-unrelated-later",
                "status": "completed",
                "items": [{"type": "userMessage", "summary": "Unrelated role message."}],
            }
        )
        with self.assertRaises(OperationError) as duplicate:
            checkpoint.resolve_source(target, {})
        self.assertEqual(duplicate.exception.code, "review_unverified_active")

        run["event_count"] = 5
        run["timeline"] = [
            {
                "record_id": "EVT-000005",
                "timestamp": "2026-08-10T00:02:00Z",
                "kind": "checkpoint-review",
                "status": "accepted",
                "category": "checkpoint-retrospective",
                "state_fingerprint": "c" * 64,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:semantic-escalation",
                    f"dashboard-preview:{source.fingerprint}",
                    "dashboard-review-task:reviewer-workflow-001",
                    "dashboard-source-record:EVT-000004",
                ],
                "source": {"line": 5},
            }
        ]
        run["timeline"][0]["mission_root"] = "e" * 64
        self.assertEqual(checkpoint.verify(target, {}, source, dispatched).state, "pending")
        run["timeline"][0]["mission_root"] = "a" * 64
        run["timeline"][0]["evidence"][0] = "dashboard-route-purpose:watcher-action"
        self.assertEqual(checkpoint.verify(target, {}, source, dispatched).state, "pending")
        run["timeline"][0]["evidence"][0] = "dashboard-route-purpose:semantic-escalation"
        run["timeline"][0]["evidence"].extend(
            [
                "dashboard-route-purpose:incident-review",
                f"dashboard-preview:{'e' * 64}",
                "dashboard-review-task:unrelated-reviewer",
                "dashboard-source-record:EVT-000003",
            ]
        )
        self.assertEqual(checkpoint.verify(target, {}, source, dispatched).state, "pending")
        del run["timeline"][0]["evidence"][-4:]
        for non_conclusion_status in ("routed", "request", "awaiting", "unverified"):
            run["timeline"][0]["status"] = non_conclusion_status
            self.assertEqual(
                checkpoint.verify(target, {}, source, dispatched).state,
                "pending",
            )
        run["timeline"][0]["status"] = "accepted"
        tasks["reviewer-workflow-001"]["turns"][0]["id"] = "turn-unrelated"
        uncorrelated = checkpoint.verify(target, {}, source, dispatched)
        self.assertEqual(uncorrelated.state, "pending")
        self.assertFalse(uncorrelated.evidence["reviewer_request_current"])
        self.assertEqual(uncorrelated.evidence["matching_record_id"], "EVT-000005")
        tasks["reviewer-workflow-001"]["turns"][0]["id"] = "turn-reviewer-workflow-001"
        concluded = checkpoint.verify(target, {}, source, dispatched)
        self.assertEqual(concluded.state, "applied")
        self.assertTrue(concluded.evidence["conclusion_recorded"])
        self.assertTrue(concluded.evidence["conclusion_current"])
        self.assertEqual(concluded.evidence["conclusion_record_id"], "EVT-000005")
        self.assertEqual(concluded.evidence["conclusion_actor_attribution"], "unavailable")
        self.assertTrue(concluded.evidence["reviewer_turn_correlated"])
        self.assertFalse(concluded.evidence["implementation_accepted_by_dashboard"])

        run["event_count"] = 6
        run["timeline"].append(
            {
                "record_id": "EVT-000006",
                "timestamp": "2026-08-10T00:03:00Z",
                "kind": "checkpoint-review",
                "status": "superseding-review",
                "category": "checkpoint-retrospective",
                "state_fingerprint": "e" * 64,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": ["independent-later-review"],
                "source": {"line": 6},
            }
        )
        run["timeline"][-1]["timestamp"] = None
        malformed_later = checkpoint.verify(target, {}, source, dispatched)
        self.assertTrue(malformed_later.evidence["conclusion_current"])
        run["timeline"][-1]["timestamp"] = "2026-08-10T00:03:00Z"
        for non_conclusion_status in ("routed", "request", "awaiting", "unverified"):
            run["timeline"][-1]["status"] = non_conclusion_status
            routed_later = checkpoint.verify(target, {}, source, dispatched)
            self.assertTrue(routed_later.evidence["conclusion_current"])
        run["timeline"][-1]["status"] = "rejected"
        superseded = checkpoint.verify(target, {}, source, dispatched)
        self.assertFalse(superseded.evidence["conclusion_current"])
        self.assertEqual(superseded.evidence["conclusion_superseded_by"], "EVT-000006")

        meta = owner._semantic_review_definition("meta")
        meta_source = meta.resolve_source(target, {})
        meta_route = meta.route_gate_request(target, {}, meta_source)
        self.assertEqual(meta_route.recipient, "reviewer-workflow-001")
        self.assertEqual(meta_route.purpose, "semantic-escalation")
        run["fingerprint"] = "f" * 64
        with self.assertRaises(OperationOwnerError) as stale_meta:
            meta.dispatch(target, {}, meta_source)
        self.assertEqual(stale_meta.exception.code, "review_source_changed")
        run["fingerprint"] = "c" * 64

        issue = owner._semantic_review_definition("issue")
        issue_input = {"incident_id": "INC-20260810-TEST"}
        issue_source = issue.resolve_source(target, issue_input)
        issue_route = issue.route_gate_request(target, issue_input, issue_source)
        self.assertEqual(issue_route.recipient, "notice-workflow-001")
        self.assertEqual(issue_route.purpose, "incident-review")
        self.assertEqual(issue_route.source_record, "EVT-000004")
        issue_dispatched = issue.dispatch(target, issue_input, issue_source)
        issue_pending = issue.verify(target, issue_input, issue_source, issue_dispatched)
        self.assertEqual(issue_pending.state, "pending")
        self.assertFalse(issue_pending.evidence["conclusion_recorded"])

        run["event_count"] = 7
        run["timeline"].append(
            {
                "record_id": "EVT-000007",
                "timestamp": "2026-08-10T00:04:00+00:00",
                "kind": "resolution",
                "status": "awaiting-target-evidence",
                "category": "source-disagreement",
                "incident_id": "INC-20260810-TEST",
                "state_fingerprint": "c" * 64,
                "mission_root": "a" * 64,
                "policy_sha256": "b" * 64,
                "evidence": [
                    "dashboard-route-purpose:incident-review",
                    f"dashboard-preview:{issue_source.fingerprint}",
                    "dashboard-review-task:notice-workflow-001",
                    "dashboard-source-record:EVT-000004",
                ],
                "source": {"line": 7},
            }
        )
        issue_concluded = issue.verify(target, issue_input, issue_source, issue_dispatched)
        self.assertEqual(issue_concluded.state, "applied")
        self.assertEqual(issue_concluded.evidence["conclusion_kind"], "resolution")

        latest_activity = run.pop("latest_activity")
        last_check = run.pop("last_check")
        with self.assertRaises(OperationError) as missing_source:
            meta.resolve_source(target, {})
        self.assertEqual(missing_source.exception.code, "review_source_record_unavailable")
        run["latest_activity"] = latest_activity
        run["last_check"] = last_check

        with self.assertRaises(OperationError) as missing_issue:
            issue.resolve_source(target, {"incident_id": "INC-20260810-MISSING"})
        self.assertEqual(missing_issue.exception.code, "review_issue_unavailable")

        notice_role = run["topology"]["roles"].pop()
        with self.assertRaises(OperationError) as wrong_role:
            issue.resolve_source(target, issue_input)
        self.assertEqual(wrong_role.exception.code, "reviewer_binding_unavailable")
        run["topology"]["roles"].append(notice_role)

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
