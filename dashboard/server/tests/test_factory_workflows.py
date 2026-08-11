from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import RLock
from types import SimpleNamespace
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
    route_action_fingerprint,
)
from software_factory_dashboard.catalog import ProjectRecord
from software_factory_dashboard.factory_workflows import (
    FactoryWorkflowOwner,
    SupervisionRouteGate,
    _normalized_policy_root,
    _policy_after_changes,
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

    @staticmethod
    def supervision_owner_module():
        spec = importlib.util.spec_from_file_location(
            "test_factory_workflow_supervision_owner",
            DEFAULT_SUPERVISION_OWNER,
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        scripts = str(DEFAULT_SUPERVISION_OWNER.parent)
        sys.path.insert(0, scripts)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        return module

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
        self.assertEqual(len(supported), 17)
        self.assertIn("factory.blocks-implement", supported)
        self.assertIn("factory.supervision-check-now", supported)
        self.assertIn("factory.supervision-adjust", supported)
        self.assertIn("factory.supervision-repair-mission-binding", supported)
        self.assertIn("factory.supervision-repair-role-task-binding", supported)
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

    def test_http_role_binding_repair_uses_disposable_policy_and_existing_task(self) -> None:
        target_id = "target-role-repair-001"
        candidate_id = "task-fake-001"
        self.init_supervision(target_id)
        owner = self.supervision_owner_module()
        directory = self.supervision_root / target_id
        initial = owner.read_json(directory / "policy.json")
        prior = json.loads(json.dumps(initial))
        prior["project_root"] = str(self.repository)
        prior["runtime"]["notice_reviewer_thread_id"] = candidate_id
        prior["policy_version"] += 1
        prior["policy_sha256"] = owner.digest(owner.policy_material(prior))
        owner.atomic_json(directory / "policy.json", prior)
        owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-ROLE-PRIOR",
                "timestamp": "2026-08-11T04:10:00+00:00",
                "kind": "policy-bind",
                "policy": prior,
            },
        )
        missing = json.loads(json.dumps(prior))
        missing["runtime"]["notice_reviewer_thread_id"] = None
        missing["policy_version"] += 1
        missing["policy_sha256"] = owner.digest(owner.policy_material(missing))
        owner.atomic_json(directory / "policy.json", missing)
        owner.append_raw(
            directory / "policy-history.jsonl",
            {
                "schema_version": 1,
                "record_id": "POLICY-ROLE-MISSING",
                "timestamp": "2026-08-11T04:11:00+00:00",
                "kind": "policy-recovery",
                "policy": missing,
            },
        )
        request_payload = {
            "operation_type": "factory.supervision-repair-role-task-binding",
            "target": {
                "kind": "run",
                "id": target_id,
                "project_id": "workflow",
            },
            "input": {"role": "notice_reviewer"},
        }

        with self.server() as origin:
            self.register(origin)
            task_before = json.loads(
                response(f"{origin}/api/v1/tasks/{candidate_id}?include_turns=true").body
            )["data"]["task"]
            preview_status, previewed = preview(origin, request_payload)
            self.assertEqual(preview_status, 201, previewed)
            execute_status, executed = execute(origin, request_payload, previewed)
            task_after = json.loads(
                response(f"{origin}/api/v1/tasks/{candidate_id}?include_turns=true").body
            )["data"]["task"]

        self.assertEqual(execute_status, 200, executed)
        operation = executed["data"]["operation"]
        self.assertEqual(operation["state"], "applied", executed)
        self.assertEqual(
            operation["preview"]["source_evidence"]["expected_task_id"],
            candidate_id,
        )
        self.assertEqual(
            operation["preview"]["source_evidence"]["identity_source"],
            "canonical-policy-history-exact-task-id",
        )
        self.assertTrue(
            operation["verification_evidence"]["task_postcondition_current"]
        )
        self.assertTrue(
            operation["verification_evidence"]["policy_postcondition_current"]
        )
        self.assertTrue(operation["verification_evidence"]["route_gate_accepted"])
        self.assertEqual(task_before, task_after)
        current = owner.read_json(directory / "policy.json")
        self.assertEqual(
            current["runtime"]["notice_reviewer_thread_id"],
            candidate_id,
        )
        self.assertEqual(current["runtime"]["watcher_thread_id"], initial["runtime"]["watcher_thread_id"])
        self.assertEqual(current["runtime"]["reviewer_thread_id"], initial["runtime"]["reviewer_thread_id"])

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

    def test_policy_adjustment_binds_exact_diff_owner_history_and_automation(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        reviewer_workspace = self.root / "reviewer-workspace"
        fix_workspace = self.root / "fix-workspace"
        reviewer_workspace.mkdir()
        fix_workspace.mkdir()
        target_task = {
            "id": "task-fake-001",
            "status": {"type": "idle"},
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
        }
        reviewer_task = {
            "id": "reviewer-workflow-001",
            "status": {"type": "idle"},
            "cwd": str(reviewer_workspace),
            "turns": [],
        }
        fix_task = {
            "id": "fix-workflow-001",
            "status": {"type": "idle"},
            "cwd": str(fix_workspace),
            "turns": [],
        }
        tasks = {
            target_task["id"]: target_task,
            reviewer_task["id"]: reviewer_task,
            fix_task["id"]: fix_task,
        }
        policy = {
            "schema_version": 1,
            "policy_version": 5,
            "policy_sha256": "b" * 64,
            "target_thread_id": target_task["id"],
            "project_root": str(self.repository),
            "mission_binding": {
                "mission_root": "a" * 64,
                "mission_source_record": "direct-user-item-44",
            },
            "schedule": {
                "routine_minutes": 20,
                "meta_review_hours": 4,
                "gmail_poll_minutes": 2,
                "gmail_quiet_poll_minutes": 2,
                "gmail_active_poll_minutes": 1,
                "gmail_active_window_minutes": 30,
            },
            "routing": {
                "max_sample_denominator": 6,
                "escalation_cooldown_minutes": 60,
                "max_escalations_per_hour": 1,
            },
            "permissions": {"allowlisted_skill_maintenance": False},
            "skill_maintenance": {"mode": "propose-only"},
            "execution_economy": {"enabled": True},
            "runtime": {
                "watcher_thread_id": "watcher-workflow-001",
                "reviewer_thread_id": reviewer_task["id"],
                "fix_executor_thread_id": fix_task["id"],
                "gmail_gate_thread_id": None,
                "routine_automation_id": "watcher-automation-001",
                "meta_automation_id": "reviewer-automation-001",
                "gmail_poll_automation_id": None,
            },
        }
        contract = {
            "fields": [
                {
                    "field": field,
                    "kind": "enum" if field == "skill_maintenance_mode" else "integer",
                    "minimum": {
                        "routine_minutes": 15,
                        "meta_review_hours": 2,
                        "max_sample_denominator": 4,
                        "cooldown_minutes": 30,
                        "max_escalations_per_hour": 1,
                        "gmail_quiet_minutes": 2,
                        "gmail_active_minutes": 1,
                        "gmail_active_window_minutes": 5,
                    }.get(field),
                    "maximum": {
                        "routine_minutes": 60,
                        "meta_review_hours": 24,
                        "max_sample_denominator": 10,
                        "cooldown_minutes": 120,
                        "max_escalations_per_hour": 2,
                        "gmail_quiet_minutes": 10,
                        "gmail_active_minutes": 9,
                        "gmail_active_window_minutes": 120,
                    }.get(field),
                    "automation_role": None,
                }
                for field in (
                    "routine_minutes",
                    "meta_review_hours",
                    "max_sample_denominator",
                    "cooldown_minutes",
                    "max_escalations_per_hour",
                    "gmail_quiet_minutes",
                    "gmail_active_minutes",
                    "gmail_active_window_minutes",
                    "skill_maintenance_mode",
                )
            ],
            "skill_maintenance_modes": [
                "apply-allowlisted-skill-maintenance-with-review",
                "apply-supervision-maintenance",
                "propose-only",
            ],
            "skill_maintenance_contracts": {
                "propose-only": {"mode": "propose-only"},
                "apply-supervision-maintenance": {
                    "mode": "apply-supervision-maintenance"
                },
                "apply-allowlisted-skill-maintenance-with-review": {
                    "mode": "apply-allowlisted-skill-maintenance-with-review"
                },
            },
            "execution_economy_contract": {"enabled": True},
        }
        adjustable = {
            "routine_minutes": 20,
            "meta_review_hours": 4,
            "max_sample_denominator": 6,
            "cooldown_minutes": 60,
            "max_escalations_per_hour": 1,
            "gmail_quiet_minutes": 2,
            "gmail_active_minutes": 1,
            "gmail_active_window_minutes": 30,
            "skill_maintenance_mode": "propose-only",
        }
        control = {
            "fingerprint": "c" * 64,
            "owner_sha256": "d" * 64,
            "policy_sha256": policy["policy_sha256"],
            "policy_version": policy["policy_version"],
            "policy_history_head": "e" * 64,
            "policy_history_records": [],
            "source_record": "EVT-000004",
            "lifecycle_status": None,
            "policy": policy,
            "adjustment_contract": contract,
            "adjustable": adjustable,
            "runtime": policy["runtime"],
            "automations_by_role": {
                "watcher": {
                    "id": "watcher-automation-001",
                    "status": "available",
                    "owner_status": "ACTIVE",
                    "kind": "heartbeat",
                    "target_thread_id": "watcher-workflow-001",
                    "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                    "manifest_sha256": "f" * 64,
                },
                "reviewer": {
                    "id": "reviewer-automation-001",
                    "status": "available",
                    "owner_status": "ACTIVE",
                    "kind": "heartbeat",
                    "target_thread_id": reviewer_task["id"],
                    "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                    "manifest_sha256": "1" * 64,
                },
                "gmail_gate": None,
            },
        }

        class OperationsStub:
            @staticmethod
            def policy_control_snapshot(target_thread_id):
                if target_thread_id != target_task["id"]:
                    raise AssertionError("wrong target")
                return control

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
                if task_id not in tasks:
                    raise AssertionError("wrong task")
                if task_id == target_task["id"] and include_turns:
                    raise AssertionError("target task should use summary read")
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
                reviewer_stat = reviewer_workspace.stat()
                self.prompt = text
                if (
                    task_id != reviewer_task["id"]
                    or expected_cwd != str(reviewer_workspace)
                    or expected_cwd_identity
                    != (reviewer_stat.st_dev, reviewer_stat.st_ino)
                ):
                    raise AssertionError("wrong reviewer dispatch")
                reviewer_task["turns"] = [
                    {
                        "id": "turn-policy-adjust-001",
                        "status": "completed",
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-policy-adjust-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            "6" * 64,
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint="7" * 64,
            target_thread=request.target_thread,
        )
        owner._policy_adjust_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "2" * 64)
        definition = owner._adjust_supervision_definition()
        target = OperationTarget(
            kind="run",
            id=target_task["id"],
            project_id=project.id,
        )
        inputs = {
            "reason": "Increase routine observation cadence for the active run.",
            "routine_minutes": 25,
        }
        source = definition.resolve_source(target, inputs)
        self.assertEqual(source.evidence["before"], {"routine_minutes": 20})
        self.assertEqual(source.evidence["after"], {"routine_minutes": 25})
        self.assertEqual(len(source.evidence["affected_automations"]), 1)
        route = definition.route_gate_request(target, inputs, source)
        self.assertEqual(route.purpose, "semantic-escalation")
        self.assertEqual(route.recipient, reviewer_task["id"])
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("fix-execution", owner.app_server_client.prompt)
        self.assertIn("never write policy.json", owner.app_server_client.prompt)
        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["policy_applied"])

        next_policy = _policy_after_changes(policy, {"routine_minutes": 25}, contract)
        next_policy["updated_at"] = "2026-08-11T00:00:00+00:00"
        next_policy["policy_sha256"] = "3" * 64
        record = {
            "schema_version": 1,
            "record_id": "POLICY-6",
            "timestamp": "2026-08-11T00:00:01+00:00",
            "kind": "policy-adjust",
            "reason": inputs["reason"],
            "evidence": [
                "dashboard-route-purpose:semantic-escalation",
                f"dashboard-preview:{source.fingerprint}",
                f"dashboard-adjust-task:{reviewer_task['id']}",
                "dashboard-source-record:EVT-000004",
            ],
            "policy": next_policy,
            "record_sha256": "4" * 64,
        }
        control.update(
            {
                "policy": next_policy,
                "policy_sha256": next_policy["policy_sha256"],
                "policy_version": 6,
                "policy_history_head": record["record_sha256"],
                "policy_history_records": [record],
            }
        )
        control["automations_by_role"]["watcher"] = {
            **control["automations_by_role"]["watcher"],
            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=25",
            "manifest_sha256": "5" * 64,
        }
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied")
        self.assertTrue(applied.evidence["policy_applied"])
        self.assertTrue(applied.evidence["automation_reconciled"])
        self.assertTrue(applied.evidence["fully_reconciled"])
        self.assertFalse(applied.evidence["direct_policy_write"])

        control["automations_by_role"]["watcher"]["rrule"] = (
            "RRULE:FREQ=MINUTELY;INTERVAL=20"
        )
        partial = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(partial.state, "pending")
        self.assertTrue(partial.evidence["policy_applied"])
        self.assertFalse(partial.evidence["automation_reconciled"])
        self.assertTrue(partial.evidence["partial_reconciliation"])

        with self.assertRaises(OperationError) as unchanged:
            definition.resolve_source(
                target,
                {"reason": "No effective change.", "routine_minutes": 20},
            )
        self.assertEqual(unchanged.exception.code, "policy_adjust_no_change")
        with self.assertRaises(OperationError) as path_reason:
            definition.resolve_source(
                target,
                {
                    "reason": "Load a policy from /Users/example/policy.json",
                    "routine_minutes": 30,
                },
            )
        self.assertEqual(path_reason.exception.code, "policy_adjust_reason_invalid")

        drifted = {**next_policy, "unrelated": "changed"}
        record["policy"] = drifted
        control["policy"] = drifted
        control["automations_by_role"]["watcher"]["rrule"] = (
            "RRULE:FREQ=MINUTELY;INTERVAL=25"
        )
        drift = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(drift.state, "failed")
        self.assertFalse(drift.evidence["policy_applied"])

        current_policy = json.loads(json.dumps(next_policy))
        current_policy["runtime"]["gmail_gate_thread_id"] = "gmail-gate-workflow-001"
        current_policy["runtime"]["gmail_poll_automation_id"] = (
            "gmail-automation-workflow-001"
        )
        control.update(
            {
                "fingerprint": "8" * 64,
                "policy": current_policy,
                "policy_sha256": current_policy["policy_sha256"],
                "policy_version": current_policy["policy_version"],
                "runtime": current_policy["runtime"],
                "adjustable": {
                    **adjustable,
                    "routine_minutes": 25,
                },
                "gmail_cadence": {
                    "status": "available",
                    "mode": "active",
                    "desired_rrule": "RRULE:FREQ=MINUTELY;INTERVAL=1",
                },
            }
        )
        control["automations_by_role"]["gmail_gate"] = {
            "id": "gmail-automation-workflow-001",
            "status": "available",
            "owner_status": "ACTIVE",
            "kind": "heartbeat",
            "target_thread_id": "gmail-gate-workflow-001",
            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=1",
            "manifest_sha256": "9" * 64,
        }
        gmail_inputs = {
            "reason": "Adjust all bounded Gmail cadence fields together.",
            "gmail_quiet_minutes": 3,
            "gmail_active_minutes": 2,
            "gmail_active_window_minutes": 45,
        }
        gmail_source = definition.resolve_source(target, gmail_inputs)
        self.assertEqual(len(gmail_source.evidence["affected_automations"]), 1)
        gmail_automation = gmail_source.evidence["affected_automations"][0]
        self.assertEqual(gmail_automation["role"], "gmail_gate")
        self.assertEqual(
            gmail_automation["fields"],
            [
                "gmail_quiet_minutes",
                "gmail_active_minutes",
                "gmail_active_window_minutes",
            ],
        )
        self.assertEqual(
            gmail_automation["expected_rrule_owner"],
            "maintained-gmail-cadence",
        )
        self.assertIsNone(gmail_automation["expected_rrule"])
        gmail_dispatched = definition.dispatch(target, gmail_inputs, gmail_source)
        gmail_next_policy = _policy_after_changes(
            current_policy,
            {
                "gmail_quiet_minutes": 3,
                "gmail_active_minutes": 2,
                "gmail_active_window_minutes": 45,
            },
            contract,
        )
        gmail_next_policy["updated_at"] = "2026-08-11T00:10:00+00:00"
        gmail_next_policy["policy_sha256"] = "a" * 64
        gmail_record = {
            "schema_version": 1,
            "record_id": "POLICY-7",
            "timestamp": "2026-08-11T00:10:01+00:00",
            "kind": "policy-adjust",
            "reason": gmail_inputs["reason"],
            "evidence": [
                "dashboard-route-purpose:semantic-escalation",
                f"dashboard-preview:{gmail_source.fingerprint}",
                f"dashboard-adjust-task:{reviewer_task['id']}",
                "dashboard-source-record:EVT-000004",
            ],
            "policy": gmail_next_policy,
            "record_sha256": "b" * 64,
        }
        control.update(
            {
                "policy": gmail_next_policy,
                "policy_sha256": gmail_next_policy["policy_sha256"],
                "policy_version": 7,
                "policy_history_head": gmail_record["record_sha256"],
                "policy_history_records": [gmail_record],
                "gmail_cadence": {
                    "status": "available",
                    "mode": "active",
                    "desired_rrule": "RRULE:FREQ=MINUTELY;INTERVAL=2",
                },
            }
        )
        control["automations_by_role"]["gmail_gate"].update(
            {
                "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=2",
                "manifest_sha256": "c" * 64,
            }
        )
        gmail_applied = definition.verify(
            target,
            gmail_inputs,
            gmail_source,
            gmail_dispatched,
        )
        self.assertEqual(gmail_applied.state, "applied")
        self.assertTrue(gmail_applied.evidence["automation_reconciled"])
        self.assertEqual(
            gmail_applied.evidence["reconciliation"][0]["fields"],
            [
                "gmail_quiet_minutes",
                "gmail_active_minutes",
                "gmail_active_window_minutes",
            ],
        )
        self.assertEqual(
            gmail_applied.evidence["reconciliation"][0]["expected_rrule"],
            "RRULE:FREQ=MINUTELY;INTERVAL=2",
        )
        self.assertEqual(
            gmail_applied.evidence["reconciliation"][0]["cadence_mode"],
            "active",
        )

    def test_missing_mission_binding_repair_preserves_exact_task_tracker_and_history(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        reviewer_workspace = self.root / "binding-reviewer-workspace"
        fix_workspace = self.root / "binding-fix-workspace"
        reviewer_workspace.mkdir()
        fix_workspace.mkdir()
        target_id = "task-fake-001"
        source_turn_id = "turn-source-001"
        source_item_id = "item-source-001"
        source_record = (
            f"codex:{target_id}:{source_turn_id}:{source_item_id}"
        )
        source_text = "Implement the full exact tracker.\n"
        source_sha = sha256(source_text.encode("utf-8")).hexdigest()
        source_content = [{"type": "text", "text": source_text}]
        source_envelope_sha = sha256(
            json.dumps(
                source_content,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        mixed_source_content = [
            *source_content,
            {"type": "localImage", "path": "/private/tmp/source.png"},
        ]
        mixed_source_envelope_sha = sha256(
            json.dumps(
                mixed_source_content,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        tracker_id = "c" * 64
        tracker_content = "d" * 64
        expected_mission = {
            "contract_version": 3,
            "mission_root": "a" * 64,
            "mission_source_record": source_record,
            "mission_derivation": {
                "controlling_source": {
                    "class": "direct-user",
                    "record": source_record,
                    "sha256": source_sha,
                }
            },
        }
        implementation_marker = {
            "kind": "implement-blocks",
            "source_fingerprint": "b" * 64,
            "project_id": project.id,
            "tracker_id": tracker_id,
            "block_start": 0,
            "block_end": 25,
            "mission_root": expected_mission["mission_root"],
            "mission_source_record": source_record,
        }
        target_task = {
            "id": target_id,
            "status": {"type": "idle"},
            "project_binding": {
                "status": "bound",
                "project_id": project.id,
                "candidates": [project.id],
            },
            "turns": [
                {
                    "id": source_turn_id,
                    "status": "completed",
                    "items": [
                        {
                            "id": source_item_id,
                            "type": "userMessage",
                            "summary": source_text,
                            "client_id": "client-source-001",
                            "user_content_sha256": source_sha,
                            "user_content_truncated": False,
                            "user_content_envelope_sha256": source_envelope_sha,
                            "user_content_part_types": ["text"],
                            "user_input_classification": "ordinary-user-message",
                            "user_authority_status": "unverified",
                        }
                    ],
                },
                {
                    "id": "turn-implementation-001",
                    "status": "completed",
                    "items": [
                        {
                            "id": "item-implementation-001",
                            "type": "userMessage",
                            "summary": (
                                "SOFTWARE_FACTORY_DASHBOARD_MISSION "
                                + json.dumps(
                                    implementation_marker,
                                    separators=(",", ":"),
                                    sort_keys=True,
                                )
                                + "\n"
                            ),
                        }
                    ],
                },
            ],
        }
        reviewer_task = {
            "id": "reviewer-binding-001",
            "status": {"type": "idle"},
            "cwd": str(reviewer_workspace),
            "turns": [],
        }
        fix_task = {
            "id": "fix-binding-001",
            "status": {"type": "idle"},
            "cwd": str(fix_workspace),
            "turns": [],
        }
        tasks = {
            target_task["id"]: target_task,
            reviewer_task["id"]: reviewer_task,
            fix_task["id"]: fix_task,
        }
        policy = {
            "schema_version": 1,
            "policy_version": 5,
            "policy_sha256": "e" * 64,
            "target_thread_id": target_id,
            "runtime": {
                "reviewer_thread_id": reviewer_task["id"],
                "fix_executor_thread_id": fix_task["id"],
            },
        }
        next_policy = {
            **policy,
            "policy_version": 6,
            "policy_sha256": "f" * 64,
            "updated_at": "2026-08-11T02:00:00+00:00",
            "mission_binding": expected_mission,
        }
        prior_record = {
            "record_id": "POLICY-5",
            "record_sha256": "1" * 64,
            "policy": policy,
        }
        control = {
            "fingerprint": "2" * 64,
            "owner_sha256": "3" * 64,
            "policy_sha256": policy["policy_sha256"],
            "policy_version": policy["policy_version"],
            "policy_history_head": prior_record["record_sha256"],
            "policy_history_records": [prior_record],
            "source_record": "EVT-000004",
            "lifecycle_status": None,
            "policy": policy,
            "runtime": policy["runtime"],
        }
        plan = {
            "control": control,
            "owner_sha256": control["owner_sha256"],
            "source_record": source_record,
            "source_sha256": source_sha,
            "expected_mission_binding": expected_mission,
            "expected_policy_version": 6,
            "expected_normalized_policy_sha256": _normalized_policy_root(
                next_policy
            ),
            "expected_history_kind": "policy-bind",
            "expected_history_reason": "Bound live identifiers and current routing defaults.",
            "expected_history_evidence": [],
            "group_ids": [target_id],
        }
        run_project_binding = {
            "target_thread_id": target_id,
            "project_binding": {
                "status": "bound",
                "project_id": project.id,
                "evidence": [
                    {
                        "source_record": "policy",
                        "field": "project_root",
                        "value": str(self.repository),
                    }
                ],
                "limitations": [],
            },
            "fingerprint": "a" * 64,
            "cache_status": "fresh",
        }

        class OperationsStub:
            @staticmethod
            def preview_mission_bind(
                selected_target,
                *,
                source_record: str,
                source_sha256: str,
            ):
                if (
                    selected_target != target_id
                    or source_record != plan["source_record"]
                    or source_sha256 != plan["source_sha256"]
                ):
                    raise AssertionError("wrong bind preview source")
                return plan

            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong target")
                return control

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong target")
                return [target_id]

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong target")
                return run_project_binding

        class AppServerStub:
            prompt = None

            @staticmethod
            def integration_state():
                return {
                    "features": [
                        {"capability": name, "status": "supported"}
                        for name in ("task_read", "task_resume", "turn_start")
                    ]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id not in tasks or not include_turns:
                    raise AssertionError("wrong task read")
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
                reviewer_stat = reviewer_workspace.stat()
                if (
                    task_id != reviewer_task["id"]
                    or expected_cwd != str(reviewer_workspace)
                    or expected_cwd_identity
                    != (reviewer_stat.st_dev, reviewer_stat.st_ino)
                ):
                    raise AssertionError("wrong reviewer dispatch")
                self.prompt = text
                reviewer_task["turns"] = [
                    {
                        "id": "turn-binding-repair-001",
                        "status": "completed",
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-binding-repair-001"},
                    "task_resumed": False,
                }

        selection = SimpleNamespace(
            project=project,
            relative_path="docs/demo-implementation-tracker.md",
            catalog_fingerprint="4" * 64,
            detail={
                "profile": "full",
                "verifier": {"valid": True},
                "raw_file": {"content_sha256": tracker_content},
            },
        )
        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            "5" * 64,
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint="6" * 64,
            target_thread=request.target_thread,
        )
        owner._binding_repair_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), selection.catalog_fingerprint)
        owner._tracker_selection = lambda target: selection
        definition = owner._mission_binding_repair_definition()
        self.assertEqual(
            definition.confirmation.expected_value,
            "REQUEST BINDING REVIEW",
        )
        target = OperationTarget(
            kind="run",
            id=target_id,
            project_id=project.id,
        )
        source = definition.resolve_source(target, {})
        self.assertEqual(source.evidence["repair_scope"], "missing-mission-binding-only")
        self.assertEqual(source.evidence["tracker_content_sha256"], tracker_content)
        self.assertEqual(source.evidence["mission_source_sha256"], source_sha)
        self.assertEqual(
            source.evidence["mission_source_envelope_sha256"],
            source_envelope_sha,
        )
        self.assertEqual(
            source.evidence["mission_source_classification"],
            "ordinary-user-message",
        )
        self.assertEqual(
            source.evidence["mission_source_authority_status"],
            "unverified-reviewer-verification-required",
        )
        self.assertEqual(
            source.evidence["run_project_binding"]["project_id"],
            project.id,
        )
        for role_key in ("reviewer_thread_id", "fix_executor_thread_id"):
            distinct_task_id = policy["runtime"][role_key]
            policy["runtime"][role_key] = target_id
            with self.assertRaises(OperationError) as collapsed_role:
                definition.resolve_source(target, {})
            self.assertEqual(
                collapsed_role.exception.code,
                "binding_repair_owner_unavailable",
            )
            policy["runtime"][role_key] = distinct_task_id
        route = definition.route_gate_request(target, {}, source)
        self.assertEqual(route.purpose, "semantic-escalation")
        self.assertEqual(route.recipient, reviewer_task["id"])
        dispatched = definition.dispatch(target, {}, source)
        self.assertEqual(
            dispatched.evidence["source_authority_status"],
            "unverified-reviewer-verification-required",
        )
        self.assertNotIn("source_attestation", dispatched.evidence)
        self.assertIn(
            "The operator confirmation requested this review",
            owner.app_server_client.prompt,
        )
        self.assertIn(
            "It is not source attestation, provenance, direct-user proof",
            owner.app_server_client.prompt,
        )
        self.assertIn("--mission-source-sha256", owner.app_server_client.prompt)
        self.assertIn("Never write policy.json", owner.app_server_client.prompt)
        pending = definition.verify(target, {}, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["binding_repaired"])

        next_record = {
            "schema_version": 1,
            "record_id": "POLICY-6",
            "record_sha256": "7" * 64,
            "timestamp": "2026-08-11T02:00:01+00:00",
            "kind": "policy-bind",
            "reason": "Bound live identifiers and current routing defaults.",
            "evidence": [],
            "policy": next_policy,
        }
        control.update(
            {
                "policy": next_policy,
                "policy_sha256": next_policy["policy_sha256"],
                "policy_version": 6,
                "policy_history_head": next_record["record_sha256"],
                "policy_history_records": [prior_record, next_record],
            }
        )
        unverified_without_review = definition.verify(target, {}, source, dispatched)
        self.assertEqual(unverified_without_review.state, "unverified")
        self.assertFalse(unverified_without_review.evidence["binding_repaired"])
        self.assertTrue(
            unverified_without_review.evidence["policy_binding_observed"]
        )
        self.assertFalse(
            unverified_without_review.evidence["reviewer_authority_verified"]
        )

        authority_marker = owner._binding_authority_review_marker(target, source)
        authority_text = (
            "SOFTWARE_FACTORY_DASHBOARD_BINDING_AUTHORITY_REVIEW "
            + json.dumps(authority_marker, separators=(",", ":"), sort_keys=True)
        )
        reviewer_task["turns"][0]["items"].append(
            {
                "id": "item-binding-review-result-001",
                "type": "agentMessage",
                "summary": authority_text,
                "summary_sha256": sha256(authority_text.encode("utf-8")).hexdigest(),
                "summary_truncated": False,
            }
        )
        applied = definition.verify(target, {}, source, dispatched)
        self.assertEqual(applied.state, "applied")
        self.assertTrue(applied.evidence["binding_repaired"])
        self.assertTrue(applied.evidence["target_binding_current"])
        self.assertTrue(applied.evidence["tracker_binding_current"])
        self.assertTrue(applied.evidence["mission_source_current"])
        self.assertTrue(applied.evidence["run_project_binding_current"])
        self.assertTrue(applied.evidence["reviewer_authority_verified"])
        self.assertEqual(applied.evidence["source_authority_status"], "reviewer-verified")
        self.assertTrue(applied.evidence["prior_history_preserved"])
        self.assertTrue(applied.evidence["single_group_current"])
        self.assertTrue(applied.evidence["owner_current"])
        self.assertFalse(applied.evidence["direct_policy_write"])

        reviewer_task["turns"][0]["items"][-1]["summary_truncated"] = True
        incomplete_review = definition.verify(target, {}, source, dispatched)
        self.assertEqual(incomplete_review.state, "unverified")
        self.assertFalse(incomplete_review.evidence["reviewer_authority_verified"])
        self.assertFalse(incomplete_review.evidence["binding_repaired"])
        reviewer_task["turns"][0]["items"][-1]["summary_truncated"] = False

        control["owner_sha256"] = "9" * 64
        changed_owner = definition.verify(target, {}, source, dispatched)
        self.assertEqual(changed_owner.state, "unverified")
        self.assertFalse(changed_owner.evidence["owner_current"])
        control["owner_sha256"] = plan["owner_sha256"]

        target_task["status"] = {"type": "notLoaded"}
        non_live = definition.verify(target, {}, source, dispatched)
        self.assertEqual(non_live.state, "unverified")
        self.assertFalse(non_live.evidence["target_binding_current"])
        target_task["status"] = {"type": "idle"}

        source_turn = target_task["turns"][0]
        source_turn["items"] = []
        missing_source = definition.verify(target, {}, source, dispatched)
        self.assertEqual(missing_source.state, "unverified")
        self.assertFalse(missing_source.evidence["mission_source_current"])
        source_turn["items"] = [
            {
                "id": source_item_id,
                "type": "userMessage",
                "summary": source_text,
                "client_id": "client-source-001",
                "user_content_sha256": source_sha,
                "user_content_truncated": False,
                "user_content_envelope_sha256": source_envelope_sha,
                "user_content_part_types": ["text"],
                "user_input_classification": "ordinary-user-message",
                "user_authority_status": "unverified",
            }
        ]

        run_project_binding["project_binding"] = {
            "status": "bound",
            "project_id": "different-project",
            "evidence": [],
            "limitations": [],
        }
        changed_project = definition.verify(target, {}, source, dispatched)
        self.assertEqual(changed_project.state, "unverified")
        self.assertFalse(
            changed_project.evidence["run_project_binding_current"]
        )
        with self.assertRaises(OperationError) as project_mismatch:
            definition.resolve_source(target, {})
        self.assertEqual(
            project_mismatch.exception.code,
            "binding_repair_project_claim_mismatch",
        )
        run_project_binding["project_binding"] = source.evidence[
            "run_project_binding"
        ]

        routed_text = "<codex_delegation><input>steer</input></codex_delegation>"
        source_turn["items"][0].update(
            {
                "summary": routed_text,
                "user_content_sha256": sha256(routed_text.encode("utf-8")).hexdigest(),
                "user_input_classification": "routed-delegation",
                "user_authority_status": "ineligible",
            }
        )
        with self.assertRaises(OperationError) as routed_source:
            definition.resolve_source(target, {})
        self.assertEqual(
            routed_source.exception.code,
            "binding_repair_source_ineligible",
        )
        source_turn["items"][0].update(
            {
                "summary": source_text,
                "user_content_sha256": source_sha,
                "user_content_envelope_sha256": source_envelope_sha,
                "user_content_part_types": ["text"],
                "user_input_classification": "ordinary-user-message",
                "user_authority_status": "unverified",
            }
        )

        generated_text = "SOFTWARE_FACTORY_DASHBOARD_MISSION {}"
        source_turn["items"][0].update(
            {
                "summary": generated_text,
                "user_content_sha256": sha256(
                    generated_text.encode("utf-8")
                ).hexdigest(),
                "user_input_classification": "dashboard-generated-marker",
                "user_authority_status": "ineligible",
            }
        )
        with self.assertRaises(OperationError) as generated_source:
            definition.resolve_source(target, {})
        self.assertEqual(
            generated_source.exception.code,
            "binding_repair_source_ineligible",
        )
        source_turn["items"][0].update(
            {
                "summary": source_text,
                "user_content_sha256": source_sha,
                "user_content_envelope_sha256": source_envelope_sha,
                "user_content_part_types": ["text"],
                "user_input_classification": "ordinary-user-message",
                "user_authority_status": "unverified",
            }
        )

        source_turn["items"][0].update(
            {
                "user_content_envelope_sha256": mixed_source_envelope_sha,
                "user_content_part_types": ["text", "localImage"],
                "user_input_classification": "noncanonical-content-envelope",
                "user_authority_status": "ineligible",
            }
        )
        with self.assertRaises(OperationError) as mixed_source:
            definition.resolve_source(target, {})
        self.assertEqual(
            mixed_source.exception.code,
            "binding_repair_source_ineligible",
        )
        source_turn["items"][0].update(
            {
                "user_content_envelope_sha256": source_envelope_sha,
                "user_content_part_types": ["text"],
                "user_input_classification": "ordinary-user-message",
                "user_authority_status": "unverified",
            }
        )

        source_turn["items"][0]["user_content_truncated"] = True
        with self.assertRaises(OperationError) as truncated_source:
            definition.resolve_source(target, {})
        self.assertEqual(
            truncated_source.exception.code,
            "binding_repair_source_ineligible",
        )
        source_turn["items"][0]["user_content_truncated"] = False

        target_task["turns_truncated"] = True
        partial_verification = definition.verify(target, {}, source, dispatched)
        self.assertEqual(partial_verification.state, "unverified")
        self.assertFalse(partial_verification.evidence["target_binding_current"])
        with self.assertRaises(OperationError) as partial_source:
            definition.resolve_source(target, {})
        self.assertEqual(
            partial_source.exception.code,
            "binding_repair_task_history_partial",
        )
        target_task.pop("turns_truncated")

        policy["mission_binding"] = expected_mission
        with self.assertRaises(OperationError) as healthy:
            definition.resolve_source(target, {})
        self.assertEqual(healthy.exception.code, "binding_repair_not_missing")
        policy.pop("mission_binding")
        plan["expected_mission_binding"] = {
            **expected_mission,
            "mission_root": "8" * 64,
        }
        with self.assertRaises(OperationError) as different:
            definition.resolve_source(target, {})
        self.assertEqual(
            different.exception.code,
            "binding_repair_mission_semantics_differ",
        )

    def test_role_task_binding_repair_requires_task_policy_and_route_postconditions(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        target_id = "task-fake-001"
        candidate_id = "notice-reviewer-prior-001"
        candidate_workspace = self.root / "notice-role-workspace"
        candidate_workspace.mkdir()
        candidate_task = {
            "id": candidate_id,
            "session_id": "session-notice-001",
            "parent_task_id": None,
            "forked_from_id": None,
            "name": "A title that is never an identity source",
            "preview": "Unstructured prior prompt",
            "cwd": str(candidate_workspace),
            "project_binding": {
                "status": "unregistered",
                "project_id": None,
                "candidates": [],
            },
            "status": {"type": "idle"},
            "created_at": "2026-08-10T10:00:00Z",
            "updated_at": "2026-08-10T10:30:00Z",
            "source": "appServer",
            "model_provider": "openai",
            "cli_version": "0.145.0",
            "ephemeral": False,
            "git": {"revision": None, "branch": None, "origin": None},
            "turns": [],
            "turns_truncated": False,
        }
        mission_binding = {
            "contract_version": 3,
            "mission_root": "a" * 64,
            "mission_source_record": "direct-user-item-44",
        }
        runtime = {
            "watcher_thread_id": "watcher-workflow-001",
            "base_reviewer_thread_id": "base-reviewer-workflow-001",
            "reviewer_thread_id": "reviewer-workflow-001",
            "notice_reviewer_thread_id": None,
            "fix_executor_thread_id": "fix-workflow-001",
            "gmail_gate_thread_id": None,
            "gmail_processor_thread_id": None,
            "roundup_thread_id": None,
            "routine_automation_id": "watcher-automation-001",
            "meta_automation_id": "reviewer-automation-001",
            "gmail_poll_automation_id": None,
        }
        policy = {
            "schema_version": 1,
            "policy_version": 7,
            "policy_sha256": "b" * 64,
            "target_thread_id": target_id,
            "mission_binding": mission_binding,
            "runtime": runtime,
        }
        prior_record = {
            "record_id": "POLICY-ROLE-MISSING",
            "record_sha256": "c" * 64,
            "policy": policy,
        }
        control = {
            "policy": policy,
            "policy_sha256": policy["policy_sha256"],
            "policy_version": policy["policy_version"],
            "policy_history_head": prior_record["record_sha256"],
            "policy_history_records": [prior_record],
            "runtime": runtime,
            "automations_by_role": {
                "watcher": {"manifest_sha256": "d" * 64},
                "reviewer": {"manifest_sha256": "e" * 64},
                "gmail_gate": None,
            },
        }
        next_policy = json.loads(json.dumps(policy))
        next_policy["policy_version"] = 8
        next_policy["policy_sha256"] = "f" * 64
        next_policy["updated_at"] = "2026-08-11T04:00:00+00:00"
        next_policy["runtime"]["notice_reviewer_thread_id"] = candidate_id
        expected_root = _normalized_policy_root(next_policy)
        plan = {
            "control": control,
            "owner_sha256": "1" * 64,
            "role": "notice_reviewer",
            "runtime_field": "notice_reviewer_thread_id",
            "candidate_task_id": candidate_id,
            "candidate_source_records": ["POLICY-NOTICE-BOUND"],
            "expected_model": {"model": "gpt-5.6-sol", "reasoning": "xhigh"},
            "expected_policy_version": 8,
            "expected_normalized_policy_sha256": expected_root,
            "expected_history_kind": "policy-bind",
            "expected_history_reason": "Bound live identifiers and current routing defaults.",
            "expected_history_evidence": [],
            "preserved_runtime": {
                key: value
                for key, value in runtime.items()
                if key != "notice_reviewer_thread_id"
            },
            "group_ids": [target_id],
        }
        project_binding = {
            "fingerprint": "2" * 64,
            "project_binding": {
                "status": "bound",
                "project_id": project.id,
                "evidence": [],
                "limitations": [],
            },
        }

        class OperationsStub:
            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong target")
                return project_binding

            @staticmethod
            def preview_role_bind(selected_target, *, role):
                if selected_target != target_id or role != "notice_reviewer":
                    raise AssertionError("wrong role bind preview")
                return plan

            @staticmethod
            def apply_role_bind(
                selected_target,
                *,
                role,
                candidate_task_id,
                prior_policy_sha256,
                prior_policy_version,
                expected_normalized_policy_sha256,
            ):
                if (
                    selected_target != target_id
                    or role != "notice_reviewer"
                    or candidate_task_id != candidate_id
                    or prior_policy_sha256 != policy["policy_sha256"]
                    or prior_policy_version != 7
                    or expected_normalized_policy_sha256 != expected_root
                ):
                    raise AssertionError("wrong role bind apply")
                next_record = {
                    "record_id": "POLICY-8",
                    "record_sha256": "3" * 64,
                    "timestamp": "2026-08-11T04:00:01+00:00",
                    "kind": "policy-bind",
                    "reason": "Bound live identifiers and current routing defaults.",
                    "evidence": [],
                    "policy": next_policy,
                }
                control.update(
                    {
                        "policy": next_policy,
                        "policy_sha256": next_policy["policy_sha256"],
                        "policy_version": 8,
                        "policy_history_head": next_record["record_sha256"],
                        "policy_history_records": [prior_record, next_record],
                        "runtime": next_policy["runtime"],
                    }
                )
                return {
                    "owner_result": {"changed": True},
                    "control": control,
                    "plan": plan,
                }

            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong target")
                return control

        class AppServerStub:
            @staticmethod
            def integration_state():
                return {
                    "features": [{"capability": "task_read", "status": "supported"}]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id != candidate_id or not include_turns:
                    raise AssertionError("wrong role task read")
                return {"task": candidate_task}

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=control["policy_sha256"],
            target_thread=request.target_thread,
        )
        owner._role_binding_repair_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "4" * 64)
        definition = owner._role_binding_repair_definition()
        target = OperationTarget(
            kind="run",
            id=target_id,
            project_id=project.id,
        )
        inputs = {"role": "notice_reviewer"}

        source = definition.resolve_source(target, inputs)

        self.assertEqual(source.evidence["current_task_id"], None)
        self.assertEqual(source.evidence["expected_task_id"], candidate_id)
        self.assertEqual(source.evidence["identity_source"], "canonical-policy-history-exact-task-id")
        self.assertFalse(source.evidence["title_matching"])
        self.assertEqual(source.evidence["route_purpose"], "incident-review")
        self.assertEqual(source.evidence["task_creation_authority"], "unavailable-not-used")
        self.assertIsNone(definition.route_gate_request)

        before_task = json.loads(json.dumps(candidate_task))
        dispatched = definition.dispatch(target, inputs, source)
        self.assertTrue(dispatched.evidence["policy_owner_changed"])
        self.assertFalse(dispatched.evidence["task_created"])
        self.assertEqual(candidate_task, before_task)
        applied = definition.verify(target, inputs, source, dispatched)

        self.assertEqual(applied.state, "applied")
        self.assertTrue(applied.evidence["role_binding_applied"])
        self.assertTrue(applied.evidence["task_postcondition_current"])
        self.assertTrue(applied.evidence["policy_postcondition_current"])
        self.assertTrue(applied.evidence["route_gate_accepted"])
        self.assertTrue(applied.evidence["single_role_current"])
        self.assertTrue(applied.evidence["unrelated_roles_preserved"])
        self.assertTrue(applied.evidence["automations_preserved"])
        self.assertFalse(applied.evidence["direct_policy_write"])

        candidate_task["status"] = {"type": "active"}
        changed_task = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(changed_task.state, "unverified")
        self.assertFalse(changed_task.evidence["task_postcondition_current"])
        candidate_task["status"] = {"type": "idle"}

        owner.route_gate = lambda request: RouteGateResult(
            False,
            None,
            reason="purpose denied",
        )
        denied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(denied.state, "unverified")
        self.assertFalse(denied.evidence["route_gate_accepted"])

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
        self.assertIn(
            "Record status as exactly one supported semantic conclusion:",
            app_server.prompts[issue_route.recipient],
        )
        self.assertIn("resolved", app_server.prompts[issue_route.recipient])
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
        run["timeline"][-1]["status"] = "resolved"
        self.assertEqual(
            issue.verify(target, issue_input, issue_source, issue_dispatched).state,
            "applied",
        )

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
