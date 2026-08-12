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
            supported = [
                item["type"] for item in descriptors if item["status"] == "supported"
            ]
            unavailable = [
                item for item in descriptors if item["status"] == "unavailable"
            ]
            request_payload = {
                "operation_type": "factory.tracker-author",
                "target": {
                    "kind": "project",
                    "id": "workflow",
                    "project_id": "workflow",
                },
                "input": {
                    "repository_head": self.head(),
                    "objective": "Build the smallest exact demo tracker; preserve this wording.",
                    "sources": ["README.md", "direct-user-item-1"],
                    "non_goals": [
                        "Do not implement code",
                        "Do not add a second task system",
                    ],
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
        self.assertEqual(len(supported), 25)
        self.assertIn("factory.blocks-implement", supported)
        self.assertIn("factory.supervision-check-now", supported)
        self.assertIn("factory.supervision-adjust", supported)
        self.assertIn("factory.supervision-repair-mission-binding", supported)
        self.assertIn("factory.supervision-repair-role-task-binding", supported)
        self.assertIn("factory.supervision-pause", supported)
        self.assertIn("factory.supervision-resume", supported)
        self.assertIn("factory.supervision-mission-successor", supported)
        self.assertIn("factory.successor-task-transition", supported)
        self.assertIn("factory.weekly-supervision-report", supported)
        self.assertIn("factory.terminal-supervision-report", supported)
        self.assertIn("factory.terminal-supervision-shutdown", supported)
        self.assertIn("factory.evolution-evaluate", supported)
        automation_repair = next(
            item
            for item in unavailable
            if item["type"] == "factory.supervision-repair-automation-binding"
        )
        self.assertIn("target-query provider", automation_repair["reason"])
        self.assertIn("factory.supervision-review-checkpoint", supported)
        self.assertIn("factory.supervision-review-meta", supported)
        self.assertIn("factory.supervision-review-issue", supported)
        self.assertIn("task.input-respond", supported)
        self.assertEqual(
            {item["type"] for item in unavailable},
            {
                "factory.supervision-repair-automation-binding",
                "factory.tracker-authoring-supervision",
            },
        )
        prompt = task["turns"][0]["items"][0]["summary"]
        self.assertTrue(prompt.startswith("SOFTWARE_FACTORY_DASHBOARD_MISSION "))
        self.assertIn("$author-implementation-trackers", prompt)
        self.assertIn(
            "Build the smallest exact demo tracker; preserve this wording.", prompt
        )
        self.assertIn("Do not implement it.", prompt)
        self.assertFalse(
            executed["data"]["operation"]["verification_evidence"]["block_accepted"]
        )
        self.assertNotIn(
            "smallest exact demo", json.dumps(executed["data"]["operation"])
        )

    def test_weekly_report_advances_one_exact_owner_stage_and_rechecks_writer(self) -> None:
        project_root = self.root / "weekly-project"
        writer_root = self.root / "weekly-writer"
        project_root.mkdir()
        writer_root.mkdir()
        project = ProjectRecord(
            id="weekly-project",
            label="Weekly project",
            root=str(project_root),
        )
        target_id = "weekly-target-001"
        writer_id = "weekly-writer-001"
        policy_sha = "a" * 64
        execution_sha = "b" * 64
        catalog_fingerprint = "c" * 64
        binding_fingerprint = "d" * 64
        workflow_fingerprint = "e" * 64
        source_root = "f" * 64
        tasks = {
            writer_id: {
                "id": writer_id,
                "cwd": str(writer_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
                "model_provider": "openai",
                "execution_contract": {
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "xhigh",
                    "source_record_sha256": execution_sha,
                },
            }
        }
        project_claim = {
            "fingerprint": binding_fingerprint,
            "project_binding": {
                "status": "bound",
                "project_id": project.id,
            },
        }
        control = {
            "fingerprint": "1" * 64,
            "policy_sha256": policy_sha,
            "policy_version": 4,
            "source_record": "EVT-WEEKLY-SOURCE-001",
            "policy": {"policy_sha256": policy_sha},
            "runtime": {"roundup_thread_id": writer_id},
        }
        workflow = {
            "status": "available",
            "stage": "prepare",
            "next_action": "prepare",
            "actionable": True,
            "report_id": "weekly-20260801-20260808-test",
            "coverage": {
                "start": "2026-08-01T00:00:00+00:00",
                "end": "2026-08-08T00:00:00+00:00",
                "timezone": "America/Los_Angeles",
                "calendar_days": ["2026-08-01"],
                "elapsed_hours": 168.0,
                "partial_week": False,
            },
            "coverage_days": 7,
            "timezone": "America/Los_Angeles",
            "source_root": source_root,
            "manifest_root": None,
            "fingerprint": workflow_fingerprint,
            "writer_role": "roundup_writer",
            "writer_task_id": writer_id,
            "expected_members": ["metrics.json", "review-packet.json"],
            "members": [],
            "stages": [
                {
                    "id": "prepare",
                    "label": "Deterministic prepare",
                    "status": "current",
                    "owner": "weekly owner",
                },
                {
                    "id": "source-currentness",
                    "label": "Source currentness",
                    "status": "pending",
                    "owner": "source owner",
                },
            ],
            "delivery": {
                "status": "not-ready",
                "configured": False,
                "retryable": False,
                "record_id": None,
                "message_id": None,
                "thread_id": None,
                "reason": "Artifact verification has not completed.",
            },
            "limitations": [],
            "error": None,
        }
        group = {"ids": [target_id]}

        class OperationsStub:
            supervision_root = self.supervision_root

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong weekly project target")
                return project_claim

            @staticmethod
            def policy_control_snapshot(selected_target, *, automation_roles=()):
                if selected_target != target_id or automation_roles != ():
                    raise AssertionError("wrong weekly policy source")
                return control

            @staticmethod
            def weekly_report_workflow_snapshot(selected_target, *, coverage_days):
                if selected_target != target_id or coverage_days != 7:
                    raise AssertionError("wrong weekly report source")
                return workflow

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong weekly group target")
                return list(group["ids"])

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
            def read_task_with_execution_contract(_projects, task_id):
                if task_id != writer_id:
                    raise AssertionError("wrong weekly writer read")
                return {"task": tasks[writer_id]}

            def start_configured_role_turn(
                self,
                _projects,
                task_id,
                text,
                *,
                expected_cwd,
                expected_cwd_identity,
            ):
                metadata = writer_root.stat()
                if (
                    task_id != writer_id
                    or expected_cwd != str(writer_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong weekly writer dispatch")
                self.prompt = text
                tasks[writer_id]["status"] = {"type": "active"}
                tasks[writer_id]["turns"] = [
                    {
                        "id": "turn-weekly-001",
                        "status": "inProgress",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-weekly-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._weekly_report_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), catalog_fingerprint)
        definition = owner._weekly_report_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        inputs = {"coverage_days": 7}

        source = definition.resolve_source(target, inputs)
        self.assertEqual(source.evidence["action"], "prepare")
        changes = {
            item.id: item for item in definition.describe_effect(
                target, inputs, source
            ).semantic_changes
        }
        self.assertEqual(changes["weekly-report-stage"].kind, "changed")
        self.assertEqual(changes["weekly-report-source"].kind, "preserved")
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("Advance exactly one weekly supervision-report stage", owner.app_server_client.prompt)
        self.assertIn("Do not perform cognitive review", owner.app_server_client.prompt)
        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["direct_report_write"])
        self.assertFalse(pending.evidence["direct_gmail_action"])

        workflow["stage"] = "review-finalize"
        workflow["next_action"] = "review-finalize"
        workflow["stages"][0]["status"] = "complete"
        workflow["stages"][1]["status"] = "complete"
        tasks[writer_id]["status"] = {"type": "idle"}
        tasks[writer_id]["turns"][0]["status"] = "completed"

        tasks[writer_id]["execution_contract"]["source_record_sha256"] = "9" * 64
        changed_writer = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(changed_writer.state, "pending")
        self.assertFalse(changed_writer.evidence["writer_contract_current"])
        tasks[writer_id]["execution_contract"]["source_record_sha256"] = execution_sha

        group["ids"] = [target_id, "unrelated-target"]
        changed_group = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(changed_group.state, "pending")
        self.assertFalse(changed_group.evidence["supervision_group_current"])
        group["ids"] = [target_id]

        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["weekly_report_applied"])
        self.assertTrue(applied.evidence["writer_turn_completed"])
        self.assertTrue(applied.evidence["writer_contract_current"])
        self.assertTrue(applied.evidence["prior_stages_preserved"])
        self.assertFalse(applied.evidence["automatic_retry"])

        workflow.update(
            {
                "stage": "finalize-verify",
                "next_action": "finalize-verify",
                "fingerprint": "2" * 64,
            }
        )
        workflow["stages"] = [
            {"id": "prepare", "label": "Prepare", "status": "complete", "owner": "weekly owner"},
            {"id": "source-currentness", "label": "Source", "status": "complete", "owner": "source owner"},
            {"id": "cognitive-review", "label": "Review", "status": "complete", "owner": "roundup writer"},
            {"id": "finalize", "label": "Finalize", "status": "current", "owner": "weekly owner"},
            {"id": "verify", "label": "Verify", "status": "pending", "owner": "weekly owner"},
            {"id": "display", "label": "Display", "status": "pending", "owner": "dashboard"},
            {"id": "delivery", "label": "Delivery", "status": "pending", "owner": "delivery owner"},
        ]
        tasks[writer_id]["status"] = {"type": "idle"}
        recovery_source = definition.resolve_source(target, inputs)
        self.assertEqual(recovery_source.evidence["action"], "finalize-verify")
        recovery_dispatched = definition.dispatch(target, inputs, recovery_source)
        self.assertEqual(
            recovery_dispatched.evidence["requested_action"], "finalize-verify"
        )
        self.assertIn(
            "Do not produce, regenerate, edit, or reinterpret that review",
            owner.app_server_client.prompt,
        )
        self.assertIn(
            "base64-encode that exact JSON",
            owner.app_server_client.prompt,
        )
        self.assertNotIn(
            "Produce one evidence-bound Sol XHigh synthesis",
            owner.app_server_client.prompt,
        )

    def test_terminal_report_advances_one_stage_without_stop_pause_or_shutdown(self) -> None:
        project_root = self.root / "terminal-project"
        writer_root = self.root / "terminal-writer"
        project_root.mkdir()
        writer_root.mkdir()
        project = ProjectRecord(
            id="terminal-project",
            label="Terminal project",
            root=str(project_root),
        )
        target_id = "terminal-target-001"
        writer_id = "terminal-writer-001"
        policy_sha = "a" * 64
        execution_sha = "b" * 64
        catalog_fingerprint = "c" * 64
        binding_fingerprint = "d" * 64
        source_root = "e" * 64
        state_fingerprint = "terminal-state-001"
        tasks = {
            writer_id: {
                "id": writer_id,
                "cwd": str(writer_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
                "model_provider": "openai",
                "execution_contract": {
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "xhigh",
                    "source_record_sha256": execution_sha,
                },
            }
        }
        project_claim = {
            "fingerprint": binding_fingerprint,
            "project_binding": {"status": "bound", "project_id": project.id},
        }
        control = {
            "fingerprint": "1" * 64,
            "policy_sha256": policy_sha,
            "policy_version": 8,
            "source_record": "EVT-TERMINAL-SOURCE-001",
            "policy": {"policy_sha256": policy_sha},
            "runtime": {"base_reviewer_thread_id": writer_id},
        }
        coverage = {
            "delta_start": "2026-08-08T00:00:00+00:00",
            "full_start": "2026-08-01T00:00:00+00:00",
            "end": "2026-08-09T00:00:00+00:00",
            "delta_anchor_record_id": "weekly-report-001",
            "delta_anchor_kind": "verified-prior-report",
        }
        prior_reports = [
            {
                "report_id": "weekly-report-001",
                "source_root": "2" * 64,
                "manifest_root": "3" * 64,
                "coverage": None,
            }
        ]
        workflow = {
            "status": "available",
            "stage": "prepare",
            "next_action": "prepare",
            "actionable": True,
            "report_set_id": "terminal-target-001-source001",
            "source_root": source_root,
            "manifest_root": None,
            "fingerprint": "f" * 64,
            "state_fingerprint": state_fingerprint,
            "mission_root": "4" * 64,
            "completion": {
                "status": "reconciled",
                "record_id": "EVT-TERMINAL-COMPLETION",
                "lifecycle_record_id": "EVT-TERMINAL-LIFECYCLE",
                "reconciled": True,
            },
            "coverage": coverage,
            "prior_reports": prior_reports,
            "writer_role": "base_reviewer",
            "writer_task_id": writer_id,
            "expected_members": [
                "review-packet.json",
                "review.json",
                "delta-report.pdf",
                "full-report.pdf",
                "manifest.json",
            ],
            "members": [],
            "stages": [
                {"id": "prepare", "label": "Prepare", "status": "current", "owner": "terminal owner"},
                {"id": "source-currentness", "label": "Source", "status": "pending", "owner": "source owner"},
            ],
            "delivery": {
                "status": "not-ready",
                "configured": True,
                "required": True,
                "retryable": False,
                "record_id": None,
                "message_id": None,
                "thread_id": None,
                "readback_root": None,
                "reason": "Artifacts are not verified.",
            },
            "shutdown": {
                "status": "separate-owner",
                "permitted": False,
                "reason": "Terminal reporting is not shutdown authority.",
            },
            "limitations": ["Derived evidence only."],
            "error": None,
        }
        group = {"ids": [target_id]}

        class OperationsStub:
            supervision_root = self.supervision_root

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong terminal project target")
                return project_claim

            @staticmethod
            def policy_control_snapshot(selected_target, *, automation_roles=()):
                if selected_target != target_id or automation_roles != ():
                    raise AssertionError("wrong terminal policy source")
                return control

            @staticmethod
            def terminal_report_workflow_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong terminal report source")
                return workflow

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong terminal group target")
                return list(group["ids"])

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
            def read_task_with_execution_contract(_projects, task_id):
                if task_id != writer_id:
                    raise AssertionError("wrong terminal writer read")
                return {"task": tasks[writer_id]}

            def start_configured_role_turn(
                self,
                _projects,
                task_id,
                text,
                *,
                expected_cwd,
                expected_cwd_identity,
            ):
                metadata = writer_root.stat()
                if (
                    task_id != writer_id
                    or expected_cwd != str(writer_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong terminal writer dispatch")
                self.prompt = text
                tasks[writer_id]["status"] = {"type": "active"}
                tasks[writer_id]["turns"] = [
                    {
                        "id": "turn-terminal-001",
                        "status": "inProgress",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {"turn": {"id": "turn-terminal-001"}, "task_resumed": False}

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._terminal_report_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), catalog_fingerprint)
        definition = owner._terminal_report_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        inputs: dict[str, object] = {}

        control["runtime"] = {"roundup_thread_id": writer_id}
        with self.assertRaisesRegex(OperationError, "base reviewer"):
            definition.resolve_source(target, inputs)
        control["runtime"] = {"base_reviewer_thread_id": writer_id}
        workflow["writer_role"] = "roundup_writer"
        with self.assertRaisesRegex(OperationError, "base reviewer"):
            definition.resolve_source(target, inputs)
        workflow["writer_role"] = "base_reviewer"

        source = definition.resolve_source(target, inputs)
        route_request = definition.route_gate_request(target, inputs, source)
        self.assertEqual(route_request.purpose, "changed-state-review")
        self.assertEqual(route_request.recipient, writer_id)
        changes = {
            item.id: item
            for item in definition.describe_effect(target, inputs, source).semantic_changes
        }
        self.assertEqual(changes["terminal-report-stage"].kind, "changed")
        self.assertEqual(changes["terminal-report-outcome"].kind, "preserved")
        self.assertEqual(changes["terminal-report-shutdown"].after.value, "not performed")
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("Advance exactly one terminal supervision-report stage", owner.app_server_client.prompt)
        self.assertIn("Do not review, finalize, deliver, request-stop, pause", owner.app_server_client.prompt)
        self.assertFalse(dispatched.evidence["direct_gmail_action"])
        self.assertFalse(dispatched.evidence["direct_lifecycle_action"])
        self.assertFalse(dispatched.evidence["request_stop"])
        self.assertFalse(dispatched.evidence["automation_pause"])
        self.assertFalse(dispatched.evidence["terminal_shutdown"])

        workflow["stage"] = "review-finalize"
        workflow["next_action"] = "review-finalize"
        workflow["stages"][0]["status"] = "complete"
        workflow["stages"][1]["status"] = "complete"
        tasks[writer_id]["status"] = {"type": "idle"}
        tasks[writer_id]["turns"][0]["status"] = "completed"
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["terminal_report_applied"])
        self.assertFalse(applied.evidence["shutdown_permitted"])
        self.assertFalse(applied.evidence["direct_gmail_action"])
        self.assertFalse(applied.evidence["automatic_retry"])

        workflow["shutdown"]["permitted"] = True
        with self.assertRaisesRegex(OperationError, "shutdown-separation"):
            definition.resolve_source(target, inputs)
        workflow["shutdown"]["permitted"] = False
        workflow.update(
            {
                "stage": "finalize-verify",
                "next_action": "finalize-verify",
                "fingerprint": "5" * 64,
            }
        )
        workflow["stages"] = [
            {"id": "prepare", "label": "Prepare", "status": "complete", "owner": "terminal owner"},
            {"id": "source-currentness", "label": "Source", "status": "complete", "owner": "source owner"},
            {"id": "cognitive-review", "label": "Review", "status": "complete", "owner": "base reviewer"},
            {"id": "finalize", "label": "Finalize", "status": "current", "owner": "terminal owner"},
            {"id": "verify", "label": "Verify", "status": "pending", "owner": "terminal owner"},
            {"id": "display", "label": "Display", "status": "pending", "owner": "dashboard"},
            {"id": "delivery", "label": "Delivery", "status": "pending", "owner": "Gmail owner"},
        ]
        recovery_source = definition.resolve_source(target, inputs)
        recovery_dispatched = definition.dispatch(target, inputs, recovery_source)
        self.assertEqual(recovery_dispatched.evidence["requested_action"], "finalize-verify")
        self.assertIn("Do not produce, regenerate, edit, or reinterpret it", owner.app_server_client.prompt)
        self.assertNotIn("Produce one bounded Sol XHigh cognitive review", owner.app_server_client.prompt)

    def test_terminal_shutdown_requires_every_gate_and_preserves_target_task(
        self,
    ) -> None:
        project_root = self.root / "shutdown-project"
        fix_root = self.root / "shutdown-fix"
        project_root.mkdir()
        fix_root.mkdir()
        project = ProjectRecord(
            id="shutdown-project",
            label="Shutdown project",
            root=str(project_root),
        )
        target_id = "shutdown-target-001"
        fix_id = "shutdown-fix-001"
        policy_sha = "a" * 64
        catalog_fingerprint = "b" * 64
        binding_fingerprint = "c" * 64
        mission_root = "d" * 64
        lifecycle_sha = "e" * 64
        gate_currentness = "f" * 64
        manifest_root = "1" * 64
        tasks = {
            target_id: {
                "id": target_id,
                "cwd": str(project_root),
                "status": {"type": "idle"},
                "project_binding": {"status": "bound", "project_id": project.id},
                "turns_truncated": False,
                "turns": [
                    {
                        "id": "turn-target-complete",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [],
                    }
                ],
            },
            fix_id: {
                "id": fix_id,
                "cwd": str(fix_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
            },
        }
        project_claim = {
            "fingerprint": binding_fingerprint,
            "project_binding": {"status": "bound", "project_id": project.id},
        }
        lifecycle = {
            "record_id": "EVT-SHUTDOWN-LIFECYCLE",
            "record_sha256": lifecycle_sha,
            "status": "completed",
            "state_fingerprint": "shutdown-state-001",
        }
        control = {
            "policy_sha256": policy_sha,
            "event_head": "2" * 64,
            "policy": {
                "policy_sha256": policy_sha,
                "mission_binding": {"mission_root": mission_root},
            },
            "runtime": {"fix_executor_thread_id": fix_id},
            "lifecycle_record": lifecycle,
        }
        workflow = {
            "status": "available",
            "stage": "request-stop",
            "next_action": "shutdown",
            "actionable": True,
            "fingerprint": "3" * 64,
            "mission_root": mission_root,
            "state_fingerprint": lifecycle["state_fingerprint"],
            "completion_record_id": "EVT-SHUTDOWN-COMPLETION",
            "lifecycle_record_id": lifecycle["record_id"],
            "report_set_id": "terminal-shutdown-report-001",
            "manifest_root": manifest_root,
            "delivery_record_id": "EVT-SHUTDOWN-DELIVERY",
            "delivery_timestamp": "2026-08-12T08:00:00Z",
            "source_record": "EVT-SHUTDOWN-DELIVERY",
            "gate": {
                "status": "ready",
                "completion_permitted": True,
                "source_stop_permitted": True,
                "supervision_pause_permitted": True,
                "terminal_reports_delivered": True,
                "reason": "Every exact terminal gate is satisfied.",
                "currentness": gate_currentness,
            },
            "open_heads": {
                "incident_ids": [],
                "decision_ids": [],
                "successor_transition_ids": [],
                "mission_activation_ids": [],
            },
            "automations": [
                {
                    "role": "reviewer",
                    "label": "Reviewer",
                    "automation_id": "shutdown-reviewer-automation",
                    "target_thread_id": "shutdown-reviewer-task",
                    "owner_status": "PAUSED",
                    "updated_at": "2026-08-12T08:01:00.000Z",
                    "manifest_sha256": "4" * 64,
                    "protected_sha256": "5" * 64,
                    "post_delivery": True,
                    "action": "preserve",
                },
                {
                    "role": "watcher",
                    "label": "Watcher",
                    "automation_id": "shutdown-watcher-automation",
                    "target_thread_id": "shutdown-watcher-task",
                    "owner_status": "ACTIVE",
                    "updated_at": "2026-08-12T07:59:00.000Z",
                    "manifest_sha256": "6" * 64,
                    "protected_sha256": "7" * 64,
                    "post_delivery": False,
                    "action": "pause-after-delivery",
                },
            ],
            "receipt": {
                "status": "missing",
                "record_id": None,
                "record_sha256": None,
                "previous_record_sha256": None,
                "automation_state_root": None,
                "reason": "No shutdown receipt exists.",
            },
            "recovery": {
                "posture": "ready",
                "guidance": "Pause the named watcher and record the exact receipt.",
            },
            "limitations": [],
            "error": None,
        }
        group = {"ids": [target_id]}

        class OperationsStub:
            supervision_root = self.supervision_root
            supervision_owner = (
                Path(__file__).resolve().parents[3]
                / "supervise-tracker-runs"
                / "scripts"
                / "supervision_log.py"
            )

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong shutdown project target")
                return project_claim

            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong shutdown control target")
                return control

            @staticmethod
            def terminal_shutdown_workflow_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong shutdown workflow target")
                return workflow

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong shutdown group target")
                return list(group["ids"])

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
                if not include_turns or task_id not in tasks:
                    raise AssertionError("wrong shutdown task read")
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
                metadata = fix_root.stat()
                if (
                    task_id != fix_id
                    or expected_cwd != str(fix_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong shutdown dispatch")
                self.prompt = text
                tasks[fix_id]["status"] = {"type": "active"}
                tasks[fix_id]["turns"] = [
                    {
                        "id": "turn-shutdown-001",
                        "status": "inProgress",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-shutdown-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._terminal_shutdown_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), catalog_fingerprint)
        definition = owner._terminal_shutdown_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        inputs: dict[str, object] = {}

        workflow["open_heads"]["incident_ids"] = ["INC-SHUTDOWN-OPEN"]
        with self.assertRaisesRegex(OperationError, "gates deny shutdown"):
            definition.resolve_source(target, inputs)
        workflow["open_heads"]["incident_ids"] = []

        source = definition.resolve_source(target, inputs)
        route_request = definition.route_gate_request(target, inputs, source)
        self.assertEqual(route_request.purpose, "fix-execution")
        self.assertEqual(route_request.source_record, "EVT-SHUTDOWN-DELIVERY")
        changes = {
            item.id: item
            for item in definition.describe_effect(
                target, inputs, source
            ).semantic_changes
        }
        self.assertEqual(changes["terminal-shutdown-receipt"].kind, "added")
        self.assertEqual(
            changes["terminal-shutdown-automation-watcher"].after.value,
            "PAUSED after terminal delivery",
        )
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("--terminal-report-set-id", owner.app_server_client.prompt)
        self.assertIn(
            "uv run --python 3.14 python",
            owner.app_server_client.prompt,
        )
        self.assertNotIn("invoke python3", owner.app_server_client.prompt)
        self.assertIn("--expected-event-head", owner.app_server_client.prompt)
        self.assertIn("open_incident_ids", owner.app_server_client.prompt)
        self.assertIn("open_decision_ids", owner.app_server_client.prompt)
        self.assertIn(
            "Immediately before any automation pause",
            owner.app_server_client.prompt,
        )
        self.assertIn(
            "Do not stop, interrupt, continue, resume, archive",
            owner.app_server_client.prompt,
        )
        self.assertFalse(dispatched.evidence["target_task_stopped"])
        self.assertFalse(dispatched.evidence["target_turn_interrupted"])

        tasks[fix_id]["status"] = {"type": "idle"}
        tasks[fix_id]["turns"][0]["status"] = "completed"
        workflow["stage"] = "shutdown"
        workflow["next_action"] = None
        workflow["actionable"] = False
        workflow["automations"][1].update(
            {
                "owner_status": "PAUSED",
                "updated_at": "2026-08-12T08:02:00.000Z",
                "manifest_sha256": "8" * 64,
                "post_delivery": True,
                "action": "preserve",
            }
        )
        workflow["receipt"] = {
            "status": "verified",
            "record_id": "EVT-SHUTDOWN-RECEIPT",
            "record_sha256": "9" * 64,
            "previous_record_sha256": control["event_head"],
            "automation_state_root": "0" * 64,
            "reason": "Every exact terminal owner is current.",
        }
        workflow["recovery"] = {
            "posture": "complete",
            "guidance": "No further shutdown action is supported.",
        }
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["terminal_shutdown_applied"])
        self.assertTrue(applied.evidence["target_task_preserved"])
        self.assertTrue(applied.evidence["automation_postcondition_current"])
        self.assertTrue(applied.evidence["shutdown_receipt_postcondition_current"])
        self.assertFalse(applied.evidence["automatic_retry"])

        workflow["receipt"]["previous_record_sha256"] = "1" * 64
        intervening_event = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(intervening_event.state, "pending")
        self.assertFalse(intervening_event.evidence["terminal_shutdown_applied"])
        workflow["receipt"]["previous_record_sha256"] = control["event_head"]

        workflow["automations"][1]["owner_status"] = "ACTIVE"
        workflow["automations"][1]["post_delivery"] = False
        workflow["automations"][1]["action"] = "pause-after-delivery"
        partial = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(partial.state, "pending")
        self.assertFalse(partial.evidence["automation_postcondition_current"])
        self.assertFalse(partial.evidence["terminal_shutdown_applied"])
    def test_factory_evolution_advances_one_maintained_stage_without_candidate_or_adoption(self) -> None:
        project_root = self.root / "evolution-project"
        proposer_root = self.root / "evolution-proposer"
        evaluator_root = self.root / "evolution-evaluator"
        project_root.mkdir()
        proposer_root.mkdir()
        evaluator_root.mkdir()
        project = ProjectRecord(
            id="evolution-project",
            label="Evolution project",
            root=str(project_root),
        )
        target_id = "evolution-target-001"
        proposer_id = "evolution-proposer-001"
        evaluator_id = "evolution-evaluator-001"
        policy_sha = "a" * 64
        tasks = {
            proposer_id: {
                "id": proposer_id,
                "cwd": str(proposer_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
                "model_provider": "openai",
                "execution_contract": {
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "xhigh",
                    "source_record_sha256": "b" * 64,
                },
            },
            evaluator_id: {
                "id": evaluator_id,
                "cwd": str(evaluator_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
                "model_provider": "openai",
                "execution_contract": {
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "max",
                    "source_record_sha256": "c" * 64,
                },
            },
        }
        project_claim = {
            "fingerprint": "d" * 64,
            "project_binding": {"status": "bound", "project_id": project.id},
        }
        control = {
            "fingerprint": "e" * 64,
            "policy_sha256": policy_sha,
            "source_record": "EVT-EVOLUTION-SOURCE-001",
        }
        workflow = {
            "status": "available",
            "stage": "prepare",
            "next_action": "prepare",
            "actionable": True,
            "evolution_id": "evolution-test-001",
            "packet_id": "packet-test-001",
            "packet_root": "f" * 64,
            "review_id": None,
            "review_root": None,
            "evaluation_id": None,
            "evaluation_root": None,
            "disposition": None,
            "source_report_id": "weekly-test-001",
            "source_report_root": "1" * 64,
            "event_head_sha256": "2" * 64,
            "manifest_root": None,
            "fingerprint": "3" * 64,
            "proposer": {"role": "base_reviewer", "task_id": proposer_id},
            "implementer": {
                "status": "not-selected",
                "task_id": None,
                "baseline_revision": None,
                "candidate_revision": None,
            },
            "evaluator": {"role": "reviewer", "task_id": evaluator_id},
            "expected_members": ["learning-packet.json", "prepare-manifest.json"],
            "members": [],
            "stages": [
                {"id": "prepare", "label": "Prepare", "status": "current", "owner": "factory owner"},
                {"id": "finalize", "label": "Finalize", "status": "pending", "owner": "proposer"},
                {"id": "external-implementation", "label": "External", "status": "pending", "owner": "Block 11"},
                {"id": "evaluate", "label": "Evaluate", "status": "pending", "owner": "evaluator"},
                {"id": "verify", "label": "Verify", "status": "pending", "owner": "factory owner"},
            ],
            "limitations": ["Adoption is not performed by evolution."],
            "error": None,
        }

        class OperationsStub:
            supervision_root = self.supervision_root

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong evolution project target")
                return project_claim

            @staticmethod
            def policy_control_snapshot(selected_target, *, automation_roles=()):
                if selected_target != target_id or automation_roles != ():
                    raise AssertionError("wrong evolution policy source")
                return control

            @staticmethod
            def factory_evolution_workflow_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong evolution workflow target")
                return workflow

            @staticmethod
            def binding_group_ids(selected_target):
                return [selected_target]

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
            def read_task_with_execution_contract(_projects, task_id):
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
                if task_id != proposer_id or expected_cwd != str(proposer_root):
                    raise AssertionError("wrong evolution role dispatch")
                metadata = proposer_root.stat()
                if expected_cwd_identity != (metadata.st_dev, metadata.st_ino):
                    raise AssertionError("wrong evolution cwd identity")
                self.prompt = text
                tasks[proposer_id]["status"] = {"type": "active"}
                tasks[proposer_id]["turns"] = [{
                    "id": "turn-evolution-001",
                    "status": "inProgress",
                    "items_truncated": False,
                    "items": [{"type": "userMessage", "summary": text}],
                }]
                return {"turn": {"id": "turn-evolution-001"}, "task_resumed": False}

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._factory_evolution_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "4" * 64)
        definition = owner._factory_evolution_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        inputs: dict[str, object] = {}

        source = definition.resolve_source(target, inputs)
        self.assertEqual(source.evidence["action"], "prepare")
        semantic = {row.id: row for row in definition.describe_effect(target, inputs, source).semantic_changes}
        self.assertEqual(semantic["factory-evolution-stage"].kind, "changed")
        dispatched = definition.dispatch(target, inputs, source)
        prompt = owner.app_server_client.prompt
        self.assertIn("Run only deterministic prepare", prompt)
        self.assertIn("Do not synthesize review", prompt)
        self.assertNotIn("implement a candidate", prompt.lower().split("do not synthesize review")[0])
        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")

        tasks[proposer_id]["status"] = {"type": "idle"}
        tasks[proposer_id]["turns"][0]["status"] = "completed"
        workflow["stage"] = "finalize"
        workflow["next_action"] = "finalize"
        workflow["stages"][0]["status"] = "complete"
        workflow["stages"][1]["status"] = "current"
        tasks[evaluator_id]["execution_contract"]["source_record_sha256"] = "9" * 64
        changed_evaluator = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(changed_evaluator.state, "pending")
        self.assertFalse(changed_evaluator.evidence["role_contracts_current"])
        tasks[evaluator_id]["execution_contract"]["source_record_sha256"] = "c" * 64
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["factory_evolution_applied"])
        self.assertFalse(applied.evidence["external_implementation_started"])
        self.assertFalse(applied.evidence["candidate_adopted"])
        self.assertFalse(applied.evidence["deployment_changed"])
        self.assertFalse(applied.evidence["outcome_claimed"])

        workflow["proposer"] = {"role": "base_reviewer", "task_id": target_id}
        with self.assertRaisesRegex(OperationError, "not distinct"):
            definition.resolve_source(target, inputs)

    def test_supervision_pause_requires_both_owners_and_preserves_target_state(self) -> None:
        project_root = self.root / "pause-project"
        target_root = project_root / "target"
        fix_root = self.root / "pause-fix-role"
        target_root.mkdir(parents=True)
        fix_root.mkdir(parents=True)
        project = ProjectRecord(
            id="pause-project",
            label="Pause project",
            root=str(project_root),
        )
        target_id = "target-pause-0001"
        fix_id = "fix-pause-0001"
        policy_sha = "b" * 64
        mission_root = "c" * 64
        tasks = {
            target_id: {
                "id": target_id,
                "cwd": str(target_root),
                "status": {"type": "active"},
                "project_binding": {
                    "status": "bound",
                    "project_id": project.id,
                },
                "turns_truncated": False,
                "turns": [
                    {
                        "id": "target-turn-001",
                        "status": "inProgress",
                        "items": [],
                    }
                ],
            },
            fix_id: {
                "id": fix_id,
                "cwd": str(fix_root),
                "status": {"type": "idle"},
                "project_binding": {
                    "status": "unassigned",
                    "project_id": None,
                },
                "turns_truncated": False,
                "turns": [],
            },
        }
        policy = {
            "project_root": str(project_root),
            "policy_version": 7,
            "policy_sha256": policy_sha,
            "mission_binding": {"mission_root": mission_root},
            "runtime": {
                "watcher_thread_id": "watcher-pause-0001",
                "reviewer_thread_id": "reviewer-pause-0001",
                "fix_executor_thread_id": fix_id,
                "routine_automation_id": "watcher-automation-pause",
                "meta_automation_id": "reviewer-automation-pause",
                "gmail_gate_thread_id": None,
                "gmail_poll_automation_id": None,
                "roundup_thread_id": None,
                "roundup_automation_id": None,
            },
            "reports": {"weekly": {"enabled": False}},
            "notifications": {
                "gmail": {
                    "enabled": True,
                    "reply_message_id": "gmail-message-pause-0001",
                }
            },
        }
        control = {
            "fingerprint": "1" * 64,
            "target_thread_id": target_id,
            "policy": policy,
            "runtime": policy["runtime"],
            "policy_sha256": policy_sha,
            "policy_version": 7,
            "policy_history_head": "2" * 64,
            "source_record": "EVT-000004",
            "event_head": "3" * 64,
            "lifecycle_status": None,
            "lifecycle_record": None,
            "open_successor_transitions": {},
            "open_mission_activations": {},
            "automations_by_role": {
                "watcher": {
                    "status": "available",
                    "id": "watcher-automation-pause",
                    "name": "Pause watcher",
                    "kind": "heartbeat",
                    "owner_status": "ACTIVE",
                    "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                    "target_thread_id": "watcher-pause-0001",
                    "manifest_sha256": "4" * 64,
                    "protected_sha256": "5" * 64,
                    "updated_at": "2026-08-11T09:00:00Z",
                },
                "reviewer": {
                    "status": "available",
                    "id": "reviewer-automation-pause",
                    "name": "Pause reviewer",
                    "kind": "heartbeat",
                    "owner_status": "ACTIVE",
                    "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                    "target_thread_id": "reviewer-pause-0001",
                    "manifest_sha256": "6" * 64,
                    "protected_sha256": "7" * 64,
                    "updated_at": "2026-08-11T09:00:00Z",
                },
                "gmail_gate": None,
                "roundup_writer": None,
                "weekly_report": None,
            },
        }

        class OperationsStub:
            group_ids = [target_id]
            notification_record = {
                "record_id": "EVT-NOTIFY-001",
                "record_sha256": "d" * 64,
                "timestamp": "2026-08-11T09:05:00Z",
                "kind": "notification",
                "status": "sent",
                "category": "gmail-lifecycle",
            }
            notification_required = False

            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong pause target")
                return control

            @classmethod
            def binding_group_ids(cls, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong pause group target")
                return list(cls.group_ids)

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong project-binding target")
                return {
                    "fingerprint": "8" * 64,
                    "project_binding": {
                        "status": "bound",
                        "project_id": project.id,
                    },
                }

            @classmethod
            def lifecycle_gate_snapshot(
                cls,
                selected_target,
                *,
                lifecycle_state,
                source_record,
                state_fingerprint,
            ):
                lifecycle = control["lifecycle_record"]
                if (
                    selected_target != target_id
                    or lifecycle_state != "paused"
                    or lifecycle["record_id"] != source_record
                    or lifecycle["state_fingerprint"] != state_fingerprint
                ):
                    raise AssertionError("wrong lifecycle gate source")
                return {
                    "notification_record": cls.notification_record,
                    "gate": {
                        "completion_permitted": True,
                        "duplicate": not cls.notification_required,
                        "source_stop_permitted": True,
                        "send_now": cls.notification_required,
                        "open_mission_activations": [],
                        "open_successor_transitions": [],
                        "supervision_pause_permitted": False,
                    }
                }

        class AppServerStub:
            prompt = None

            @staticmethod
            def integration_state():
                return {
                    "features": [
                        {"capability": capability, "status": "supported"}
                        for capability in ("task_read", "task_resume", "turn_start")
                    ]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id not in tasks or not include_turns:
                    raise AssertionError("wrong pause task read")
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
                metadata = fix_root.stat()
                if (
                    task_id != fix_id
                    or expected_cwd != str(fix_root)
                    or expected_cwd_identity
                    != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong pause owner dispatch")
                self.prompt = text
                tasks[fix_id]["turns"] = [
                    {
                        "id": "turn-pause-001",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                marker = json.loads(
                    text.splitlines()[0].removeprefix(
                        "SOFTWARE_FACTORY_DASHBOARD_SUPERVISION_PAUSE "
                    )
                )
                control["lifecycle_status"] = "paused"
                control["lifecycle_record"] = {
                    "record_id": "EVT-PAUSE-001",
                    "record_sha256": "9" * 64,
                    "timestamp": "2026-08-11T09:04:00Z",
                    "kind": "lifecycle",
                    "status": "paused",
                    "severity": "info",
                    "category": "supervision-pause",
                    "policy_sha256": policy_sha,
                    "state_fingerprint": marker["preview_fingerprint"],
                    "dedup_key": (
                        "dashboard-supervision-pause:"
                        + marker["preview_fingerprint"]
                    ),
                    "evidence": [
                        "dashboard-preview:" + marker["preview_fingerprint"]
                    ],
                }
                return {
                    "turn": {"id": "turn-pause-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._supervision_pause_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "a" * 64)
        definition = owner._supervision_pause_definition()
        target = OperationTarget(
            kind="run",
            id=target_id,
            project_id=project.id,
        )

        OperationsStub.group_ids = ["wrong-group"]
        with self.assertRaises(OperationError) as wrong_group:
            definition.resolve_source(target, {})
        self.assertEqual(wrong_group.exception.code, "supervision_pause_group_unavailable")
        OperationsStub.group_ids = [target_id]

        policy["notifications"]["gmail"]["enabled"] = False
        with self.assertRaises(OperationError) as notification_unavailable:
            definition.resolve_source(target, {})
        self.assertEqual(
            notification_unavailable.exception.code,
            "supervision_pause_notification_unavailable",
        )
        policy["notifications"]["gmail"]["enabled"] = True

        control["open_successor_transitions"] = {"transition-001": {"phase": "required"}}
        with self.assertRaises(OperationError) as transition_open:
            definition.resolve_source(target, {})
        self.assertEqual(
            transition_open.exception.code,
            "supervision_pause_transition_open",
        )
        control["open_successor_transitions"] = {}

        reviewer_automation = control["automations_by_role"]["reviewer"]
        control["automations_by_role"]["reviewer"] = {
            **reviewer_automation,
            "status": "unavailable",
        }
        with self.assertRaises(OperationError) as missing_automation:
            definition.resolve_source(target, {})
        self.assertEqual(
            missing_automation.exception.code,
            "supervision_pause_automation_unavailable",
        )
        control["automations_by_role"]["reviewer"] = reviewer_automation

        source = definition.resolve_source(target, {})
        changes = {
            item.id: item
            for item in definition.describe_effect(target, {}, source).semantic_changes
        }
        self.assertEqual(changes["supervision-lifecycle"].kind, "added")
        self.assertEqual(
            changes["supervision-automation-watcher"].after.value,
            "PAUSED",
        )
        self.assertEqual(changes["supervision-target-task-state"].kind, "preserved")
        request = definition.route_gate_request(target, {}, source)
        self.assertEqual(request.recipient, fix_id)
        self.assertEqual(request.purpose, "fix-execution")
        self.assertEqual(request.source_record, "EVT-000004")

        dispatched = definition.dispatch(target, {}, source)
        self.assertIn("$supervise-tracker-runs", owner.app_server_client.prompt)
        self.assertIn(
            "Do not interrupt, continue, stop, or resume",
            owner.app_server_client.prompt,
        )
        self.assertIn("Do not edit policy JSON", owner.app_server_client.prompt)

        OperationsStub.notification_record = None
        OperationsStub.notification_required = True
        notification_pending = definition.verify(target, {}, source, dispatched)
        self.assertEqual(notification_pending.state, "pending")
        self.assertEqual(
            notification_pending.evidence["partial_posture"],
            "notification-pending",
        )
        self.assertFalse(
            notification_pending.evidence["lifecycle_postcondition_current"]
        )

        OperationsStub.notification_record = {
            "record_id": "EVT-NOTIFY-001",
            "record_sha256": "d" * 64,
            "timestamp": "2026-08-11T09:05:00Z",
            "kind": "notification",
            "status": "sent",
            "category": "gmail-lifecycle",
        }
        OperationsStub.notification_required = False
        lifecycle_only = definition.verify(target, {}, source, dispatched)
        self.assertEqual(lifecycle_only.state, "pending")
        self.assertEqual(
            lifecycle_only.evidence["partial_posture"],
            "lifecycle-paused-automations-pending",
        )
        self.assertTrue(lifecycle_only.evidence["lifecycle_postcondition_current"])
        self.assertFalse(lifecycle_only.evidence["automation_postcondition_current"])
        self.assertTrue(lifecycle_only.evidence["terminal_only_pause_gate_ignored"])

        recovery_source = definition.resolve_source(target, {})
        recovery_changes = {
            item.id: item
            for item in definition.describe_effect(
                target,
                {},
                recovery_source,
            ).semantic_changes
        }
        self.assertEqual(recovery_changes["supervision-lifecycle"].kind, "preserved")
        self.assertEqual(
            recovery_changes["supervision-automation-watcher"].kind,
            "changed",
        )

        for index, role in enumerate(("watcher", "reviewer")):
            control["automations_by_role"][role]["owner_status"] = "PAUSED"
            control["automations_by_role"][role]["manifest_sha256"] = (
                f"{index + 10:x}" * 64
            )[:64]
            control["automations_by_role"][role]["updated_at"] = (
                f"2026-08-11T09:06:0{index}Z"
            )
        control["automations_by_role"]["watcher"]["updated_at"] = (
            "2026-08-11T09:04:59Z"
        )
        wrong_order = definition.verify(target, {}, source, dispatched)
        self.assertEqual(wrong_order.state, "pending")
        watcher_result = next(
            item
            for item in wrong_order.evidence["automation_results"]
            if item["role"] == "watcher"
        )
        self.assertFalse(
            watcher_result["owner_transition_current"]
        )
        control["automations_by_role"]["watcher"]["updated_at"] = (
            "2026-08-11T09:06:00Z"
        )
        applied = definition.verify(target, {}, source, dispatched)
        self.assertEqual(applied.state, "applied")
        self.assertTrue(applied.evidence["supervision_pause_applied"])
        self.assertTrue(applied.evidence["target_task_preserved"])
        self.assertFalse(applied.evidence["turn_interrupted"])
        self.assertFalse(applied.evidence["semantic_resume_enabled"])
        self.assertEqual(
            applied.evidence["lifecycle_notification_record_id"],
            "EVT-NOTIFY-001",
        )

        tasks[target_id]["turns"][0]["status"] = "interrupted"
        interrupted = definition.verify(target, {}, source, dispatched)
        self.assertEqual(interrupted.state, "pending")
        self.assertFalse(interrupted.evidence["target_task_preserved"])

        tasks[target_id]["turns"][0]["status"] = "inProgress"
        with self.assertRaises(OperationError) as already:
            definition.resolve_source(target, {})
        self.assertEqual(already.exception.code, "supervision_already_paused")

    def test_supervision_resume_requires_both_owners_and_never_resumes_target_task(self) -> None:
        project_root = self.root / "resume-project"
        target_root = project_root / "target"
        fix_root = self.root / "resume-fix-role"
        target_root.mkdir(parents=True)
        fix_root.mkdir(parents=True)
        project = ProjectRecord(
            id="resume-project",
            label="Resume project",
            root=str(project_root),
        )
        target_id = "target-resume-0001"
        fix_id = "fix-resume-0001"
        policy_sha = "b" * 64
        mission_root = "c" * 64
        pause_record_id = "EVT-PAUSE-RESUME-001"
        source_record_id = "EVT-RESUME-SOURCE-001"
        state_fingerprint = "resume-source-state-001"
        eligibility_root = "d" * 64
        source_currentness_root = "e" * 64
        group_id = "group-" + "f" * 64
        tasks = {
            target_id: {
                "id": target_id,
                "cwd": str(target_root),
                "status": {"type": "active"},
                "project_binding": {
                    "status": "bound",
                    "project_id": project.id,
                },
                "turns_truncated": False,
                "turns": [
                    {
                        "id": "target-resume-turn-001",
                        "status": "inProgress",
                        "items": [],
                    }
                ],
            },
            fix_id: {
                "id": fix_id,
                "cwd": str(fix_root),
                "status": {"type": "idle"},
                "project_binding": {"status": "unassigned", "project_id": None},
                "turns_truncated": False,
                "turns": [],
            },
        }
        policy = {
            "project_root": str(project_root),
            "policy_version": 8,
            "policy_sha256": policy_sha,
            "mission_binding": {"mission_root": mission_root},
            "runtime": {
                "watcher_thread_id": "watcher-resume-0001",
                "reviewer_thread_id": "reviewer-resume-0001",
                "fix_executor_thread_id": fix_id,
                "routine_automation_id": "watcher-automation-resume",
                "meta_automation_id": "reviewer-automation-resume",
                "gmail_gate_thread_id": None,
                "gmail_poll_automation_id": None,
                "roundup_thread_id": None,
                "roundup_automation_id": None,
            },
            "reports": {"weekly": {"enabled": False}},
            "notifications": {"gmail": {"enabled": True}},
        }
        pause_record = {
            "record_id": pause_record_id,
            "record_sha256": "1" * 64,
            "timestamp": "2026-08-11T09:00:00Z",
            "kind": "lifecycle",
            "status": "paused",
            "category": "supervision-pause",
            "policy_sha256": policy_sha,
            "state_fingerprint": "paused-state-001",
        }
        state_source = {
            "record_id": source_record_id,
            "record_sha256": "2" * 64,
            "timestamp": "2026-08-11T09:02:30Z",
            "kind": "check",
            "status": "no-intervention",
            "category": "changed-state-review",
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "policy_sha256": policy_sha,
            "state_fingerprint": state_fingerprint,
            "evidence": ["exact-target-read"],
        }
        control = {
            "fingerprint": "3" * 64,
            "target_thread_id": target_id,
            "owner_sha256": "4" * 64,
            "policy": policy,
            "runtime": policy["runtime"],
            "policy_sha256": policy_sha,
            "policy_version": 8,
            "policy_history_head": "5" * 64,
            "source_record": source_record_id,
            "current_state_source": state_source,
            "event_head": state_source["record_sha256"],
            "lifecycle_status": "paused",
            "lifecycle_record": pause_record,
            "open_successor_transitions": {},
            "open_mission_activations": {},
            "automations_by_role": {
                "watcher": {
                    "status": "available",
                    "id": "watcher-automation-resume",
                    "name": "Resume watcher",
                    "kind": "heartbeat",
                    "owner_status": "PAUSED",
                    "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                    "target_thread_id": "watcher-resume-0001",
                    "manifest_sha256": "6" * 64,
                    "protected_sha256": "7" * 64,
                    "updated_at": "2026-08-11T09:01:00Z",
                },
                "reviewer": {
                    "status": "available",
                    "id": "reviewer-automation-resume",
                    "name": "Resume reviewer",
                    "kind": "heartbeat",
                    "owner_status": "ACTIVE",
                    "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                    "target_thread_id": "reviewer-resume-0001",
                    "manifest_sha256": "8" * 64,
                    "protected_sha256": "9" * 64,
                    "updated_at": "2026-08-11T09:02:00Z",
                },
                "gmail_gate": None,
                "roundup_writer": None,
                "weekly_report": None,
            },
        }
        configuration_roots = {
            "watcher-automation-resume": "a" * 64,
            "reviewer-automation-resume": "0" * 64,
        }

        class OperationsStub:
            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong resume target")
                return control

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong resume group target")
                return [target_id]

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong resume project target")
                return {
                    "fingerprint": "a" * 64,
                    "project_binding": {
                        "status": "bound",
                        "project_id": project.id,
                    },
                }

            @staticmethod
            def supervision_resume_gate_snapshot(
                selected_target,
                *,
                pause_record,
                source_record,
                state_fingerprint,
            ):
                if (
                    selected_target != target_id
                    or pause_record != pause_record_id
                    or source_record != source_record_id
                    or state_fingerprint != "resume-source-state-001"
                ):
                    raise AssertionError("wrong resume-gate source")
                if control["lifecycle_status"] == "resumed":
                    return {
                        "currentness": "b" * 64,
                        "gate": {
                            "status": "already-resumed",
                            "eligible": True,
                            "ready_to_finalize": True,
                            "duplicate": True,
                            "action": "none",
                            "policy_sha256": policy_sha,
                            "resume_record": control["lifecycle_record"],
                        },
                    }
                states = {}
                for role, owner_role, configuration_root in (
                    ("watcher", "watcher", configuration_roots["watcher-automation-resume"]),
                    ("reviewer", "reviewer", configuration_roots["reviewer-automation-resume"]),
                ):
                    automation = control["automations_by_role"][role]
                    states[automation["id"]] = {
                        "automation_id": automation["id"],
                        "configuration_sha256": configuration_root,
                        "manifest_sha256": automation["manifest_sha256"],
                        "role": owner_role,
                        "rrule": automation["rrule"],
                        "status": automation["owner_status"],
                        "target_thread_id": automation["target_thread_id"],
                        "updated_at": {
                            "2026-08-11T09:01:00Z": 1_786_438_860_000,
                            "2026-08-11T09:02:00Z": 1_786_438_920_000,
                            "2026-08-11T09:03:00Z": 1_786_438_980_000,
                        }[automation["updated_at"]],
                    }
                paused_ids = sorted(
                    automation_id
                    for automation_id, state in states.items()
                    if state["status"] == "PAUSED"
                )
                return {
                    "currentness": "b" * 64,
                    "gate": {
                        "status": "pending-activation" if paused_ids else "ready",
                        "eligible": True,
                        "ready_to_finalize": not paused_ids,
                        "duplicate": False,
                        "action": (
                            "activate-exact-bound-automations"
                            if paused_ids
                            else "resume-finalize"
                        ),
                        "activate_automation_ids": paused_ids,
                        "automation_states": states,
                        "eligibility_root": eligibility_root,
                        "source_currentness_root": source_currentness_root,
                        "pause_record_id": pause_record_id,
                        "source_record_id": source_record_id,
                        "state_fingerprint": state_fingerprint,
                        "group_id": group_id,
                        "mission_root": mission_root,
                        "policy_version": 8,
                        "policy_sha256": policy_sha,
                    },
                }

        class AppServerStub:
            prompt = None

            @staticmethod
            def integration_state():
                return {
                    "features": [
                        {"capability": capability, "status": "supported"}
                        for capability in ("task_read", "task_resume", "turn_start")
                    ]
                }

            @staticmethod
            def read_task(_projects, task_id, *, include_turns):
                if task_id not in tasks or not include_turns:
                    raise AssertionError("wrong resume task read")
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
                metadata = fix_root.stat()
                if (
                    task_id != fix_id
                    or expected_cwd != str(fix_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong resume owner dispatch")
                self.prompt = text
                tasks[fix_id]["turns"] = [
                    {
                        "id": "turn-resume-001",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {"turn": {"id": "turn-resume-001"}, "task_resumed": False}

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy_sha,
            target_thread=request.target_thread,
        )
        owner._supervision_resume_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "c" * 64)
        definition = owner._supervision_resume_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)

        source = definition.resolve_source(target, {})
        self.assertEqual(
            source.evidence["activate_automation_ids"],
            ["watcher-automation-resume"],
        )
        changes = {
            item.id: item
            for item in definition.describe_effect(target, {}, source).semantic_changes
        }
        self.assertEqual(changes["supervision-resume-lifecycle"].before.value, "paused")
        self.assertEqual(changes["supervision-resume-lifecycle"].after.value, "resumed")
        self.assertEqual(
            changes["supervision-resume-automation-watcher"].kind,
            "changed",
        )
        self.assertEqual(
            changes["supervision-resume-automation-reviewer"].kind,
            "preserved",
        )
        route_request = definition.route_gate_request(target, {}, source)
        route_result = owner.route_gate(route_request)
        self.assertTrue(route_result.allowed)
        self.assertEqual(route_result.recipient, route_request.recipient)
        self.assertEqual(route_result.purpose, route_request.purpose)
        self.assertEqual(route_result.source_record, route_request.source_record)
        self.assertEqual(route_result.target_thread, route_request.target_thread)
        self.assertEqual(
            route_result.action_hash,
            route_action_fingerprint(route_request.required_action),
        )
        self.assertEqual(route_result.policy_fingerprint, policy_sha)
        dispatched = definition.dispatch(target, {}, source)
        self.assertIn("$supervise-tracker-runs", owner.app_server_client.prompt)
        self.assertIn("Do not continue, interrupt, stop, or resume", owner.app_server_client.prompt)
        self.assertIn("Do not edit policy JSON", owner.app_server_client.prompt)
        self.assertIn("resume-finalize once", owner.app_server_client.prompt)

        partial = definition.verify(target, {}, source, dispatched)
        self.assertEqual(partial.state, "pending")
        self.assertEqual(partial.evidence["partial_posture"], "activation-partial")
        self.assertFalse(partial.evidence["target_task_or_turn_resumed"])

        watcher = control["automations_by_role"]["watcher"]
        watcher["owner_status"] = "ACTIVE"
        watcher["manifest_sha256"] = "d" * 64
        watcher["updated_at"] = "2026-08-11T09:03:00Z"
        owner_only = definition.verify(target, {}, source, dispatched)
        self.assertEqual(owner_only.state, "pending")
        self.assertEqual(
            owner_only.evidence["partial_posture"],
            "automations-active-lifecycle-pending",
        )
        self.assertFalse(owner_only.evidence["lifecycle_postcondition_current"])

        final_states = {}
        for role, owner_role in (("watcher", "watcher"), ("reviewer", "reviewer")):
            automation = control["automations_by_role"][role]
            final_states[automation["id"]] = {
                "automation_id": automation["id"],
                "configuration_sha256": configuration_roots[automation["id"]],
                "manifest_sha256": automation["manifest_sha256"],
                "role": owner_role,
                "rrule": automation["rrule"],
                "status": "ACTIVE",
                "target_thread_id": automation["target_thread_id"],
                "updated_at": {
                    "2026-08-11T09:02:00Z": 1_786_438_920_000,
                    "2026-08-11T09:03:00Z": 1_786_438_980_000,
                }[automation["updated_at"]],
            }
        resume_record = {
            "record_id": "EVT-RESUME-001",
            "record_sha256": "e" * 64,
            "timestamp": "2026-08-11T09:04:00Z",
            "kind": "lifecycle",
            "category": "supervision-resume",
            "status": "resumed",
            "resume_contract_version": 1,
            "pause_record_id": pause_record_id,
            "pause_record_sha256": pause_record["record_sha256"],
            "source_record_id": source_record_id,
            "source_record_sha256": state_source["record_sha256"],
            "state_fingerprint": state_fingerprint,
            "source_currentness_root": source_currentness_root,
            "eligibility_root": eligibility_root,
            "group_id": group_id,
            "mission_root": mission_root,
            "policy_sha256": policy_sha,
            "policy_version": 8,
            "policy_history_head": control["policy_history_head"],
            "automation_configuration_roots": configuration_roots,
            "automation_states": final_states,
        }
        control["lifecycle_status"] = "resumed"
        control["lifecycle_record"] = resume_record
        applied = definition.verify(target, {}, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["supervision_resume_applied"])
        self.assertTrue(applied.evidence["automation_postcondition_current"])
        self.assertTrue(applied.evidence["lifecycle_postcondition_current"])
        self.assertTrue(applied.evidence["target_task_preserved"])
        self.assertFalse(applied.evidence["target_task_or_turn_resumed"])
        self.assertEqual(applied.evidence["pause_record_id"], pause_record_id)
        self.assertEqual(applied.evidence["resume_record_id"], "EVT-RESUME-001")

        accepted_route_gate = owner.route_gate
        owner.route_gate = lambda request: RouteGateResult(
            False,
            None,
            reason="The exact route is no longer permitted.",
        )
        denied = definition.verify(target, {}, source, dispatched)
        self.assertEqual(denied.state, "pending")
        self.assertTrue(denied.evidence["lifecycle_postcondition_current"])
        self.assertTrue(denied.evidence["automation_postcondition_current"])
        self.assertFalse(denied.evidence["route_gate_accepted"])
        self.assertEqual(
            denied.evidence["partial_posture"],
            "owners-resumed-operation-unverified",
        )
        owner.route_gate = accepted_route_gate

        tasks[target_id]["turns"][0]["status"] = "interrupted"
        interrupted = definition.verify(target, {}, source, dispatched)
        self.assertEqual(interrupted.state, "pending")
        self.assertFalse(interrupted.evidence["target_task_preserved"])
        tasks[target_id]["turns"][0]["status"] = "inProgress"

        with self.assertRaises(OperationError) as already:
            definition.resolve_source(target, {})
        self.assertEqual(already.exception.code, "supervision_already_running")

    def test_mission_successor_preserves_history_and_ends_at_pending_activation(self) -> None:
        project_root = self.root / "successor-project"
        target_root = project_root / "target"
        reviewer_root = self.root / "successor-reviewer"
        fix_root = self.root / "successor-fix"
        for path in (target_root, reviewer_root, fix_root):
            path.mkdir(parents=True)
        project = ProjectRecord(
            id="successor-project",
            label="Successor project",
            root=str(project_root),
        )
        target_id = "target-successor-001"
        reviewer_id = "reviewer-successor-001"
        fix_id = "fix-successor-001"
        source_turn_id = "turn-successor-source-001"
        source_item_id = "item-successor-source-001"
        source_record = f"codex:{target_id}:{source_turn_id}:{source_item_id}"
        source_text = "Begin the materially different dashboard reliability mission."
        source_sha = sha256(source_text.encode("utf-8")).hexdigest()
        source_envelope_sha = sha256(
            json.dumps(
                [{"type": "text", "text": source_text}],
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        source_item = {
            "id": source_item_id,
            "type": "userMessage",
            "summary": source_text,
            "client_id": "client-successor-001",
            "user_content_sha256": source_sha,
            "user_content_truncated": False,
            "user_content_envelope_sha256": source_envelope_sha,
            "user_content_part_types": ["text"],
            "user_input_classification": "ordinary-user-message",
            "user_authority_status": "unverified",
        }
        tasks = {
            target_id: {
                "id": target_id,
                "cwd": str(target_root),
                "status": {"type": "idle"},
                "project_binding": {
                    "status": "bound",
                    "project_id": project.id,
                },
                "turns_truncated": False,
                "turns": [
                    {
                        "id": source_turn_id,
                        "status": "completed",
                        "items_truncated": False,
                        "items": [source_item],
                    }
                ],
            },
            reviewer_id: {
                "id": reviewer_id,
                "cwd": str(reviewer_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
            },
            fix_id: {
                "id": fix_id,
                "cwd": str(fix_root),
                "status": {"type": "idle"},
                "turns_truncated": False,
                "turns": [],
            },
        }
        predecessor_root = "a" * 64
        older_root = "b" * 64
        successor_root = "c" * 64
        predecessor_binding = {
            "contract_version": 3,
            "mission_root": predecessor_root,
            "mission_source_record": "direct-user-predecessor",
        }
        successor_binding = {
            "contract_version": 3,
            "mission_root": successor_root,
            "mission_source_record": source_record,
            "mission_derivation": {
                "controlling_source": {
                    "class": "direct-user",
                    "record": source_record,
                    "sha256": source_sha,
                }
            },
        }
        runtime = {
            "watcher_thread_id": "watcher-successor-001",
            "base_reviewer_thread_id": None,
            "reviewer_thread_id": reviewer_id,
            "notice_reviewer_thread_id": None,
            "fix_executor_thread_id": fix_id,
            "gmail_gate_thread_id": None,
            "gmail_processor_thread_id": None,
            "roundup_thread_id": "roundup-successor-001",
            "routine_automation_id": "watcher-automation-successor",
            "meta_automation_id": "reviewer-automation-successor",
            "gmail_poll_automation_id": None,
            "roundup_automation_id": None,
            "automation_id": None,
        }
        policy = {
            "schema_version": 1,
            "policy_version": 4,
            "policy_sha256": "d" * 64,
            "target_thread_id": target_id,
            "project_root": str(project_root),
            "mission_binding": predecessor_binding,
            "runtime": runtime,
            "reports": {
                "weekly": {
                    "enabled": True,
                    "automation_id": "weekly-automation-successor",
                }
            },
        }
        next_policy = {
            **json.loads(json.dumps(policy)),
            "policy_version": 5,
            "policy_sha256": "e" * 64,
            "updated_at": "2026-08-12T01:00:00+00:00",
            "mission_binding": successor_binding,
        }
        prior_policy_record = {
            "record_id": "POLICY-4",
            "record_sha256": "f" * 64,
            "timestamp": "2026-08-11T23:00:00+00:00",
            "kind": "policy-bind",
            "reason": "Existing mission binding.",
            "evidence": [],
            "policy": policy,
        }
        automations = {
            "watcher": {
                "status": "available",
                "id": "watcher-automation-successor",
                "name": "Successor watcher",
                "kind": "heartbeat",
                "owner_status": "ACTIVE",
                "target_thread_id": runtime["watcher_thread_id"],
                "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
                "manifest_sha256": "1" * 64,
                "protected_sha256": "2" * 64,
                "updated_at": "2026-08-11T23:30:00Z",
            },
            "reviewer": {
                "status": "available",
                "id": "reviewer-automation-successor",
                "name": "Successor reviewer",
                "kind": "heartbeat",
                "owner_status": "ACTIVE",
                "target_thread_id": reviewer_id,
                "rrule": "RRULE:FREQ=HOURLY;INTERVAL=4",
                "manifest_sha256": "3" * 64,
                "protected_sha256": "4" * 64,
                "updated_at": "2026-08-11T23:31:00Z",
            },
            "weekly_report": {
                "status": "available",
                "id": "weekly-automation-successor",
                "name": "Successor weekly report",
                "kind": "heartbeat",
                "owner_status": "ACTIVE",
                "target_thread_id": runtime["roundup_thread_id"],
                "rrule": "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0",
                "manifest_sha256": "5" * 64,
                "protected_sha256": "6" * 64,
                "updated_at": "2026-08-11T23:32:00Z",
            },
            "gmail_gate": None,
            "roundup_writer": None,
        }
        control = {
            "fingerprint": "5" * 64,
            "target_thread_id": target_id,
            "owner_sha256": "6" * 64,
            "policy": policy,
            "runtime": runtime,
            "policy_sha256": policy["policy_sha256"],
            "policy_version": policy["policy_version"],
            "policy_history_head": prior_policy_record["record_sha256"],
            "policy_history_records": [prior_policy_record],
            "source_record": "EVT-SUCCESSOR-SOURCE-001",
            "open_mission_activations": {},
            "automations_by_role": automations,
        }
        older_segment = {
            "mission_root": older_root,
            "mission_source_record": "direct-user-older",
            "posture": "predecessor",
            "superseded_by": predecessor_root,
            "event_count": 2,
            "incident_count": 0,
            "open_incident_count": 0,
            "conclusion_count": 1,
            "terminal_record": "EVT-OLDER-COMPLETE",
        }
        predecessor_segment = {
            "mission_root": predecessor_root,
            "mission_source_record": "direct-user-predecessor",
            "posture": "current",
            "superseded_by": None,
            "event_count": 3,
            "incident_count": 0,
            "open_incident_count": 0,
            "conclusion_count": 0,
            "terminal_record": None,
        }
        history = {
            "target_thread_id": target_id,
            "active_mission_root": predecessor_root,
            "policy_sha256": policy["policy_sha256"],
            "segments": [older_segment, predecessor_segment],
            "active_record_ids": ["EVT-PREDECESSOR-001"],
            "active_record_sha256s": ["7" * 64],
            "fingerprint": "8" * 64,
        }
        plan = {
            "fingerprint": "9" * 64,
            "owner_sha256": control["owner_sha256"],
            "policy_sha256": policy["policy_sha256"],
            "policy_version": 4,
            "policy_history_head": prior_policy_record["record_sha256"],
            "policy_history_count": 1,
            "predecessor": predecessor_binding,
            "successor": successor_binding,
            "predecessor_disposition": "superseded",
            "predecessor_terminal_record": None,
            "source_record": source_record,
            "source_sha256": source_sha,
            "first_eligible_work": "Block 0 capability review",
            "reason": "The direct user requested a materially different mission.",
            "expected_evidence": [source_record],
            "expected_policy_version": 5,
            "expected_normalized_policy_sha256": _normalized_policy_root(next_policy),
            "expected_history_kind": "policy-mission-successor",
            "expected_history_reason": (
                "superseded: The direct user requested a materially different mission."
            ),
            "open_incident_ids": [],
            "open_decision_ids": [],
            "open_successor_transition_ids": [],
            "open_mission_activation_ids": [],
            "control": control,
            "history": history,
            "history_fingerprint": history["fingerprint"],
            "predecessor_segment": predecessor_segment,
        }
        run_project = {
            "fingerprint": "0" * 64,
            "project_binding": {
                "status": "bound",
                "project_id": project.id,
            },
        }

        class OperationsStub:
            @staticmethod
            def mission_successor_plan_snapshot(
                selected_target,
                *,
                source_record,
                source_sha256,
                predecessor_disposition,
                first_eligible_work,
                reason,
            ):
                if (
                    selected_target != target_id
                    or source_record != plan["source_record"]
                    or source_sha256 != plan["source_sha256"]
                    or predecessor_disposition != plan["predecessor_disposition"]
                    or first_eligible_work != plan["first_eligible_work"]
                    or reason != plan["reason"]
                ):
                    raise AssertionError("wrong mission-successor plan source")
                return plan

            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong mission-successor target")
                return control

            @staticmethod
            def mission_history_snapshot(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong mission-history target")
                return history

            @staticmethod
            def project_binding_snapshot(_projects, selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong mission-project target")
                return run_project

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target != target_id:
                    raise AssertionError("wrong mission-group target")
                return [target_id]

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
                    raise AssertionError("wrong mission-successor task read")
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
                metadata = reviewer_root.stat()
                if (
                    task_id != reviewer_id
                    or expected_cwd != str(reviewer_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong mission reviewer dispatch")
                self.prompt = text
                tasks[reviewer_id]["turns"] = [
                    {
                        "id": "turn-successor-review-001",
                        "status": "inProgress",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-successor-review-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy["policy_sha256"],
            target_thread=request.target_thread,
        )
        owner._mission_successor_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "a" * 64)
        definition = owner._mission_successor_definition()
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        inputs = {
            "mission_source_record": source_record,
            "predecessor_disposition": "superseded",
            "first_eligible_work": plan["first_eligible_work"],
            "reason": plan["reason"],
        }

        source = definition.resolve_source(target, inputs)
        self.assertEqual(
            source.evidence["source_authority_status"],
            "unverified-reviewer-verification-required",
        )
        self.assertEqual(
            source.evidence["prior_policy_history_roots"],
            [prior_policy_record["record_sha256"]],
        )
        self.assertEqual(
            [item["role"] for item in source.evidence["automations"]],
            ["watcher", "reviewer", "weekly_report"],
        )
        semantic = {
            item.id: item
            for item in definition.describe_effect(
                target, inputs, source
            ).semantic_changes
        }
        self.assertEqual(semantic["mission-successor-binding"].kind, "changed")
        self.assertEqual(
            semantic["mission-successor-target-task"].kind,
            "preserved",
        )
        original_summary = source_item["summary"]
        original_sha = source_item["user_content_sha256"]
        original_envelope = source_item["user_content_envelope_sha256"]
        source_item["summary"] = "<codex_delegation>routed</codex_delegation>"
        source_item["user_content_sha256"] = sha256(
            source_item["summary"].encode("utf-8")
        ).hexdigest()
        source_item["user_content_envelope_sha256"] = sha256(
            json.dumps(
                [{"type": "text", "text": source_item["summary"]}],
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaises(OperationError) as routed:
            definition.resolve_source(target, inputs)
        self.assertEqual(routed.exception.code, "mission_successor_source_unavailable")
        source_item["summary"] = original_summary
        source_item["user_content_sha256"] = original_sha
        source_item["user_content_envelope_sha256"] = original_envelope

        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("$supervise-tracker-runs", owner.app_server_client.prompt)
        self.assertIn("must not use bind", owner.app_server_client.prompt)
        self.assertIn("Do not create a successor task", owner.app_server_client.prompt)
        self.assertIn("mission-activation-start", owner.app_server_client.prompt)
        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["mission_successor_applied"])

        authority_summary = (
            "SOFTWARE_FACTORY_DASHBOARD_MISSION_SUCCESSOR_AUTHORITY_REVIEW "
            + json.dumps(
                owner._mission_successor_authority_marker(target, source),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\nIndependent direct-source and material-difference review passed."
        )
        reviewer_turn = tasks[reviewer_id]["turns"][0]
        reviewer_turn["status"] = "completed"
        reviewer_turn["items"].append(
            {
                "type": "agentMessage",
                "summary": authority_summary,
                "summary_truncated": False,
                "summary_sha256": sha256(
                    authority_summary.encode("utf-8")
                ).hexdigest(),
            }
        )
        successor_record = {
            "record_id": "POLICY-5",
            "record_sha256": "a" * 64,
            "timestamp": "2026-08-12T01:00:01+00:00",
            "kind": plan["expected_history_kind"],
            "reason": plan["expected_history_reason"],
            "evidence": plan["expected_evidence"],
            "policy": next_policy,
        }
        activation = {
            "activation_id": "ACTIVATION-SUCCESSOR-001",
            "record_id": "EVT-SUCCESSOR-ACTIVATION-001",
            "phase": "pending",
            "target_thread_id": target_id,
            "mission_root": successor_root,
            "mission_source_record": source_record,
            "activation_policy_sha256": next_policy["policy_sha256"],
            "policy_sha256": next_policy["policy_sha256"],
            "first_eligible_work": plan["first_eligible_work"],
            "evidence": plan["expected_evidence"],
        }
        control.update(
            {
                "policy": next_policy,
                "runtime": next_policy["runtime"],
                "policy_sha256": next_policy["policy_sha256"],
                "policy_version": 5,
                "policy_history_head": successor_record["record_sha256"],
                "policy_history_records": [prior_policy_record, successor_record],
                "open_mission_activations": {
                    activation["activation_id"]: activation
                },
            }
        )
        history.update(
            {
                "active_mission_root": successor_root,
                "policy_sha256": next_policy["policy_sha256"],
                "segments": [
                    dict(older_segment),
                    {
                        **predecessor_segment,
                        "posture": "predecessor",
                        "superseded_by": successor_root,
                    },
                    {
                        "mission_root": successor_root,
                        "mission_source_record": source_record,
                        "posture": "current",
                        "superseded_by": None,
                        "policy_sha256s": [next_policy["policy_sha256"]],
                        "event_count": 1,
                        "incident_count": 0,
                        "open_incident_count": 0,
                        "conclusion_count": 0,
                        "terminal_record": None,
                    },
                ],
                "active_record_ids": [activation["record_id"]],
                "active_record_sha256s": ["b" * 64],
                "fingerprint": "c" * 64,
            }
        )
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["mission_successor_applied"])
        self.assertTrue(applied.evidence["predecessor_history_preserved"])
        self.assertTrue(applied.evidence["successor_current_state_isolated"])
        self.assertTrue(applied.evidence["mission_activation_pending"])
        self.assertFalse(applied.evidence["successor_task_created"])
        self.assertFalse(applied.evidence["mission_activation_started"])
        self.assertEqual(len(tasks), 3)
        self.assertEqual(
            history["segments"][0]["superseded_by"],
            predecessor_root,
        )

        weekly = control["automations_by_role"]["weekly_report"]
        weekly_manifest = weekly["manifest_sha256"]
        weekly_updated_at = weekly["updated_at"]
        weekly["manifest_sha256"] = "d" * 64
        weekly["updated_at"] = "2026-08-12T01:01:00Z"
        changed_weekly = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(changed_weekly.state, "unverified")
        self.assertFalse(changed_weekly.evidence["automations_preserved"])
        weekly_result = next(
            item
            for item in changed_weekly.evidence["automation_results"]
            if item["role"] == "weekly_report"
        )
        self.assertFalse(weekly_result["preserved"])
        weekly["manifest_sha256"] = weekly_manifest
        weekly["updated_at"] = weekly_updated_at

        history["segments"][-1]["conclusion_count"] = 1
        leaked = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(leaked.state, "unverified")
        self.assertFalse(leaked.evidence["successor_current_state_isolated"])

    def test_successor_transition_requires_acknowledgement_and_concrete_first_work(self) -> None:
        self.assertTrue(
            FactoryWorkflowOwner._successor_transition_range_contains(
                "Blocks 0-25, 27–31", 27
            )
        )
        self.assertFalse(
            FactoryWorkflowOwner._successor_transition_range_contains(
                "Blocks 0-25, 27–31", 26
            )
        )
        self.assertFalse(
            FactoryWorkflowOwner._successor_transition_range_contains(
                "0-25 plus 27-31", 27
            )
        )
        project_root = self.root / "continuity-project"
        source_root = project_root / "source"
        successor_root = project_root / "successor"
        fix_root = self.root / "continuity-fix"
        for path in (source_root, successor_root, fix_root):
            path.mkdir(parents=True)
        project = ProjectRecord(
            id="continuity-project",
            label="Continuity project",
            root=str(project_root),
        )
        target_id = "continuity-source-001"
        successor_id = "continuity-successor-001"
        fix_id = "continuity-fix-001"
        transition_id = "TRANSITION-CONTINUITY-001"
        source_mission = "a" * 64
        successor_mission = "b" * 64
        tracker_sha = "c" * 64
        bootstrap_fingerprint = "d" * 64
        work_fingerprint = "e" * 64
        authority_text = (
            "Continue the full implementation tracker in a distinct successor task "
            "when that owner boundary is required."
        )
        authority_record = (
            f"codex:{target_id}:turn-authority-001:item-authority-001"
        )
        authority_item = {
            "id": "item-authority-001",
            "type": "userMessage",
            "summary": authority_text,
            "user_content_sha256": sha256(authority_text.encode("utf-8")).hexdigest(),
            "user_content_envelope_sha256": sha256(
                json.dumps(
                    [{"text": authority_text, "type": "text"}],
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
            "user_content_part_types": ["text"],
            "user_content_truncated": False,
            "user_input_classification": "ordinary-user-message",
            "user_authority_status": "unverified",
            "client_id": "codex-desktop",
        }
        tracker = {
            "tracker_id": "f" * 64,
            "tracker_path": "docs/continuity-implementation-tracker.md",
            "tracker_sha256": tracker_sha,
            "tracker_fingerprint": "1" * 64,
            "repository_head": "2" * 40,
            "first_block_number": 26,
            "first_block_title": "Successor-task continuity",
            "first_block_status": "in-progress",
            "profile": "full",
        }
        bootstrap_marker = {
            "kind": "successor-continuity",
            "source_fingerprint": bootstrap_fingerprint,
            "project_id": project.id,
            "tracker_id": tracker["tracker_id"],
            "tracker_sha256": tracker_sha,
            "transition_id": transition_id,
            "requested_block_range": "26-31",
            "first_eligible_block": "Block 26",
            "source_mission_root": source_mission,
            "governing_authority_source_record": authority_record,
        }
        bootstrap_text = "SOFTWARE_FACTORY_DASHBOARD_MISSION " + json.dumps(
            bootstrap_marker,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        handoff_id = "HANDOFF-CONTINUITY-001"
        ack_id = "ACK-CONTINUITY-001"
        handoff_text = (
            "SOFTWARE_FACTORY_DASHBOARD_SUCCESSOR_TRANSITION "
            + json.dumps(
                {
                    "kind": "handoff",
                    "transition_id": transition_id,
                    "record_id": handoff_id,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        acknowledgement_text = (
            "SOFTWARE_FACTORY_DASHBOARD_SUCCESSOR_TRANSITION "
            + json.dumps(
                {
                    "kind": "acknowledgement",
                    "transition_id": transition_id,
                    "record_id": ack_id,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        tasks = {
            target_id: {
                "id": target_id,
                "cwd": str(source_root),
                "status": {"type": "idle"},
                "project_binding": {"status": "bound", "project_id": project.id},
                "turns_truncated": False,
                "turns": [{
                    "id": "turn-authority-001",
                    "status": "completed",
                    "items_truncated": False,
                    "items": [authority_item],
                }],
            },
            successor_id: {
                "id": successor_id,
                "cwd": str(successor_root),
                "status": {"type": "idle"},
                "project_binding": {"status": "bound", "project_id": project.id},
                "turns_truncated": False,
                "turns": [
                    {
                        "id": "turn-bootstrap-001",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [
                            {"type": "userMessage", "summary": bootstrap_text},
                            {
                                "type": "userMessage",
                                "summary": handoff_text,
                                "summary_truncated": False,
                            },
                            {
                                "type": "agentMessage",
                                "summary": acknowledgement_text,
                                "summary_truncated": False,
                            },
                        ],
                    }
                ],
            },
            fix_id: {
                "id": fix_id,
                "cwd": str(fix_root),
                "status": {"type": "idle"},
                "project_binding": {"status": "unassigned", "project_id": None},
                "turns_truncated": False,
                "turns": [],
            },
        }
        head = {
            "record_id": "EVT-CONTINUITY-005",
            "record_sha256": "3" * 64,
            "transition_id": transition_id,
            "phase": "target-acknowledged",
            "tracker_sha256": tracker_sha,
            "tracker_source_record": "commit:continuity-tracker",
            "requested_block_range": "26-31",
            "first_eligible_block": "Block 26",
            "source_mission_root": source_mission,
            "governing_authority_source_class": "direct-user",
            "governing_authority_source_record": authority_record,
            "successor_thread_id": successor_id,
            "successor_mission_root": successor_mission,
            "successor_group_id": successor_id,
            "handoff_record": handoff_id,
            "acknowledgement_record": ack_id,
            "started_block": "",
            "state_fingerprint": "state-before-work",
        }
        source_policy_sha = "4" * 64
        source_control = {
            "fingerprint": "5" * 64,
            "owner_sha256": "6" * 64,
            "policy_sha256": source_policy_sha,
            "policy": {
                "policy_sha256": source_policy_sha,
                "mission_binding": {"mission_root": source_mission},
            },
            "runtime": {"fix_executor_thread_id": fix_id},
            "open_successor_transitions": {transition_id: head},
            "successor_transitions": {transition_id: head},
            "successor_transition_records": {
                transition_id: [{
                    **head,
                    "record_id": "EVT-CONTINUITY-002",
                    "phase": "successor-created",
                    "state_fingerprint": bootstrap_fingerprint,
                }],
            },
        }
        successor_control = {
            "fingerprint": "7" * 64,
            "policy_sha256": "8" * 64,
            "policy": {
                "policy_sha256": "8" * 64,
                "mission_binding": {"mission_root": successor_mission},
            },
            "runtime": {},
            "open_successor_transitions": {},
            "successor_transitions": {},
        }

        expected_transition_id = transition_id

        class OperationsStub:
            @staticmethod
            def policy_control_snapshot(selected_target):
                if selected_target == target_id:
                    return source_control
                if selected_target == successor_id:
                    return successor_control
                raise AssertionError("wrong continuity control target")

            @staticmethod
            def binding_group_ids(selected_target):
                if selected_target == target_id:
                    return [target_id]
                if selected_target == successor_id:
                    return [successor_id]
                raise AssertionError("wrong continuity group target")

            @staticmethod
            def successor_transition_gate_snapshot(
                selected_target,
                *,
                transition_id,
                task_creation_authority,
            ):
                if (
                    selected_target != target_id
                    or transition_id != expected_transition_id
                    or task_creation_authority != "available"
                ):
                    raise AssertionError("wrong continuity gate source")
                stopped = head["phase"] == "work-started"
                next_action = {
                    "target-acknowledged": "start-first-eligible-block",
                    "work-started": "continue-successor-and-close-transition-incident",
                }[head["phase"]]
                return {
                    "currentness": "9" * 64,
                    "owner_sha256": "6" * 64,
                    "gate": {
                        "transition_id": expected_transition_id,
                        "phase": head["phase"],
                        "transition_open": not stopped,
                        "source_stop_permitted": stopped,
                        "required_source_posture": (
                            "transition-satisfied" if stopped else "in-progress"
                        ),
                        "next_action": next_action,
                    },
                }

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
                if task_id not in tasks:
                    raise AssertionError("wrong continuity task read")
                if include_turns is False:
                    return {"task": tasks[task_id]}
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
                metadata = fix_root.stat()
                if (
                    task_id != fix_id
                    or expected_cwd != str(fix_root)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong continuity owner dispatch")
                self.prompt = text
                tasks[fix_id]["turns"] = [
                    {
                        "id": "turn-continuity-fix-001",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                implementation_marker = {
                    "kind": "implement-blocks",
                    "source_fingerprint": work_fingerprint,
                    "project_id": project.id,
                    "tracker_id": tracker["tracker_id"],
                    "block_start": 26,
                    "block_end": 31,
                    "mission_root": successor_mission,
                    "mission_source_record": authority_record,
                }
                implementation_text = (
                    "SOFTWARE_FACTORY_DASHBOARD_MISSION "
                    + json.dumps(
                        implementation_marker,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                tasks[successor_id]["turns"].append(
                    {
                        "id": "turn-first-work-001",
                        "status": "inProgress",
                        "items_truncated": False,
                        "items": [
                            {"type": "userMessage", "summary": implementation_text},
                            {
                                "type": "fileChange",
                                "summary": "1 file change",
                                "status": "completed",
                            },
                        ],
                    }
                )
                head.update(
                    {
                        "record_id": "EVT-CONTINUITY-006",
                        "record_sha256": "a" * 64,
                        "phase": "work-started",
                        "started_block": "Block 26",
                        "state_fingerprint": work_fingerprint,
                    }
                )
                source_control["open_successor_transitions"] = {}
                return {
                    "turn": {"id": "turn-continuity-fix-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=source_policy_sha,
            target_thread=request.target_thread,
        )
        owner._successor_transition_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "b" * 64)
        owner._successor_transition_tracker = lambda selected, selected_head: tracker
        target = OperationTarget(kind="run", id=target_id, project_id=project.id)
        definition = owner._successor_transition_definition()
        inputs = {"transition_id": transition_id}

        head["governing_authority_source_record"] = "invented-direct-source"
        with self.assertRaises(OperationError) as invented_authority:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            invented_authority.exception.code,
            "successor_transition_authority_unavailable",
        )
        head["governing_authority_source_record"] = authority_record

        creation_record = source_control["successor_transition_records"][
            transition_id
        ][0]
        creation_record["state_fingerprint"] = "f" * 64
        with self.assertRaises(OperationError) as wrong_bootstrap_currentness:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            wrong_bootstrap_currentness.exception.code,
            "successor_transition_phase_evidence_missing",
        )
        creation_record["state_fingerprint"] = bootstrap_fingerprint

        handoff_item = tasks[successor_id]["turns"][0]["items"][1]
        handoff_item["type"] = "agentMessage"
        with self.assertRaises(OperationError) as spoofed_handoff:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            spoofed_handoff.exception.code,
            "successor_transition_phase_evidence_missing",
        )
        handoff_item["type"] = "userMessage"

        acknowledgement_item = tasks[successor_id]["turns"][0]["items"].pop()
        with self.assertRaises(OperationError) as missing_ack:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            missing_ack.exception.code,
            "successor_transition_phase_evidence_missing",
        )
        tasks[successor_id]["turns"][0]["items"].append(acknowledgement_item)

        acknowledgement_item["type"] = "userMessage"
        with self.assertRaises(OperationError) as spoofed_ack:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            spoofed_ack.exception.code,
            "successor_transition_phase_evidence_missing",
        )
        acknowledgement_item["type"] = "agentMessage"

        source = definition.resolve_source(target, inputs)
        self.assertEqual(source.evidence["phase"], "target-acknowledged")
        self.assertEqual(source.evidence["next_phase"], "work-started")
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("start the exact first eligible Block", owner.app_server_client.prompt)

        concrete_item = tasks[successor_id]["turns"][-1]["items"].pop()
        tasks[successor_id]["turns"][-1]["items"].append(
            {"type": "agentMessage", "summary": "Starting the requested work."}
        )
        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertFalse(pending.evidence["source_stop_permitted"])
        self.assertTrue(pending.evidence["maintained_gate_source_stop_claim"])
        self.assertFalse(pending.evidence["work_started_current"])
        self.assertFalse(pending.evidence["successor_transition_applied"])

        tasks[successor_id]["turns"][-1]["items"].pop()
        tasks[successor_id]["turns"][-1]["items"].append(concrete_item)
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied", applied.evidence)
        self.assertTrue(applied.evidence["work_started_current"])
        self.assertTrue(applied.evidence["source_stop_permitted"])
        self.assertTrue(applied.evidence["source_task_active"])
        self.assertFalse(applied.evidence["source_completed"])

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
        semantic = {
            row.id: row
            for row in definition.describe_effect(target, inputs, source).semantic_changes
        }
        self.assertEqual(semantic["policy-routine_minutes"].kind, "changed")
        self.assertEqual(semantic["policy-routine_minutes"].before.value, "20")
        self.assertEqual(semantic["policy-routine_minutes"].after.value, "25")
        self.assertEqual(
            semantic["automation-watcher-schedule"].after.value,
            "RRULE:FREQ=MINUTELY;INTERVAL=25",
        )
        self.assertEqual(
            semantic["policy-preserved-meta_review_hours"].kind,
            "preserved",
        )
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
        gmail_semantic = {
            row.id: row
            for row in definition.describe_effect(
                target,
                gmail_inputs,
                gmail_source,
            ).semantic_changes
        }
        self.assertEqual(
            gmail_semantic["automation-gmail_gate-schedule"].after.posture,
            "unavailable",
        )
        self.assertIn(
            "Gmail cadence owner",
            gmail_semantic["automation-gmail_gate-schedule"].owner,
        )
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

    def test_automation_binding_repair_keeps_policy_and_protected_fields_separate(self) -> None:
        project = ProjectRecord(
            id="workflow",
            label="Workflow",
            root=str(self.repository),
        )
        fix_workspace = self.repository / "automation-fix-workspace"
        role_workspace = self.repository / "automation-role-workspace"
        fix_workspace.mkdir()
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
        fix_task = {
            "id": "fix-automation-workflow-001",
            "status": {"type": "idle"},
            "cwd": str(fix_workspace),
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
            "turns": [],
            "turns_truncated": False,
        }
        role_task = {
            "id": "watcher-workflow-001",
            "status": {"type": "idle"},
            "cwd": str(role_workspace),
            "project_binding": {
                "status": "bound",
                "project_id": "workflow",
                "candidates": ["workflow"],
            },
        }
        policy = {
            "schema_version": 1,
            "policy_version": 9,
            "policy_sha256": "1" * 64,
            "target_thread_id": target_task["id"],
            "project_root": str(self.repository),
            "mission_binding": {
                "mission_root": "2" * 64,
                "mission_source_record": "direct-user-item-44",
            },
            "runtime": {
                "watcher_thread_id": "watcher-workflow-001",
                "routine_automation_id": "watcher-automation-001",
                "fix_executor_thread_id": fix_task["id"],
            },
        }
        current_automation = {
            "id": "watcher-automation-001",
            "status": "available",
            "owner_status": "PAUSED",
            "kind": "heartbeat",
            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=45",
            "target_thread_id": "wrong-watcher-task",
            "manifest_sha256": "3" * 64,
            "protected_sha256": "4" * 64,
            "source_path": str(
                self.automations_root
                / "watcher-automation-001"
                / "automation.toml"
            ),
        }
        expected_automation = {
            "id": "watcher-automation-001",
            "owner_status": "ACTIVE",
            "kind": "heartbeat",
            "target_thread_id": "watcher-workflow-001",
            "rrule": "RRULE:FREQ=MINUTELY;INTERVAL=20",
            "timezone": "not-applicable-to-interval-schedule",
        }
        claims = [
            {
                "target_thread_id": target_task["id"],
                "role": "watcher",
                "purpose": "watcher-action",
                "role_thread_id": "watcher-workflow-001",
                "policy_version": 9,
                "policy_sha256": policy["policy_sha256"],
            }
        ]
        control = {
            "policy": policy,
            "runtime": policy["runtime"],
        }
        binding = {
            "fingerprint": "5" * 64,
            "label": "Routine watcher",
            "purpose": "watcher-action",
            "lifecycle_status": None,
            "mismatches": [
                "enabled state differs",
                "role target differs",
                "schedule differs",
            ],
            "repairable": True,
            "current": current_automation,
            "expected": expected_automation,
            "claims": claims,
            "active_target_owners": {
                "status": "available",
                "target_thread_id": role_task["id"],
                "selected_automation_id": expected_automation["id"],
                "unavailable_automation_ids": [],
                "owners": [],
                "conflicting_owner_ids": [],
                "fingerprint": "a" * 64,
            },
            "source_record": "EVT-000020",
            "policy_sha256": policy["policy_sha256"],
            "policy_version": policy["policy_version"],
            "policy_history_head": "6" * 64,
            "mission_binding": policy["mission_binding"],
            "control": control,
        }

        class OperationsStub:
            @staticmethod
            def automation_target_query_posture():
                return {
                    "status": "available",
                    "version": 1,
                    "reason": None,
                }

            @staticmethod
            def automation_binding_snapshot(target_thread_id, role):
                if target_thread_id != target_task["id"] or role != "watcher":
                    raise AssertionError("wrong automation binding source")
                return binding

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
                if task_id == expected_automation["target_thread_id"] and not include_turns:
                    return {"task": role_task}
                if task_id == fix_task["id"] and include_turns:
                    return {"task": fix_task}
                raise AssertionError("wrong task read")

            def start_configured_role_turn(
                self,
                _projects,
                task_id,
                text,
                *,
                expected_cwd,
                expected_cwd_identity,
            ):
                metadata = fix_workspace.stat()
                if (
                    task_id != fix_task["id"]
                    or expected_cwd != str(fix_workspace)
                    or expected_cwd_identity != (metadata.st_dev, metadata.st_ino)
                ):
                    raise AssertionError("wrong fix-executor dispatch")
                self.prompt = text
                fix_task["turns"] = [
                    {
                        "id": "turn-automation-repair-001",
                        "status": "completed",
                        "items_truncated": False,
                        "items": [{"type": "userMessage", "summary": text}],
                    }
                ]
                return {
                    "turn": {"id": "turn-automation-repair-001"},
                    "task_resumed": False,
                }

        owner = object.__new__(FactoryWorkflowOwner)
        owner.operations_service = OperationsStub()
        owner.app_server_client = AppServerStub()
        owner.route_gate = lambda request: RouteGateResult(
            True,
            route_action_fingerprint(request.required_action),
            recipient=request.recipient,
            purpose=request.purpose,
            source_record=request.source_record,
            policy_fingerprint=policy["policy_sha256"],
            target_thread=request.target_thread,
        )
        owner._automation_binding_repair_dispatch_lock = RLock()
        owner._active_projects = lambda: ((project,), "7" * 64)
        definition = owner._automation_binding_repair_definition()
        target = OperationTarget(
            kind="run",
            id=target_task["id"],
            project_id=project.id,
        )
        inputs = {"role": "watcher"}

        role_task["project_binding"]["project_id"] = "other"
        with self.assertRaises(OperationError) as wrong_role_project:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            wrong_role_project.exception.code,
            "automation_binding_project_mismatch",
        )
        role_task["project_binding"]["project_id"] = project.id
        role_task["id"] = "different-role-task"
        with self.assertRaises(OperationError) as missing_role_target:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            missing_role_target.exception.code,
            "automation_binding_project_mismatch",
        )
        role_task["id"] = expected_automation["target_thread_id"]
        fix_task["project_binding"]["project_id"] = "other"
        with self.assertRaises(OperationError) as wrong_fix_project:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            wrong_fix_project.exception.code,
            "automation_binding_project_mismatch",
        )
        fix_task["project_binding"]["project_id"] = project.id
        outside_workspace = self.root / "outside-automation-project"
        outside_workspace.mkdir()
        fix_task["cwd"] = str(outside_workspace)
        with self.assertRaises(OperationError) as wrong_fix_cwd:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            wrong_fix_cwd.exception.code,
            "automation_binding_project_mismatch",
        )
        fix_task["cwd"] = str(fix_workspace)

        source = definition.resolve_source(target, inputs)
        self.assertEqual(source.evidence["mismatches"], binding["mismatches"])
        self.assertEqual(
            source.evidence["expected_automation"]["timezone"],
            "not-applicable-to-interval-schedule",
        )
        semantic = {
            row.id: row
            for row in definition.describe_effect(target, inputs, source).semantic_changes
        }
        self.assertEqual(semantic["automation-owner-status"].kind, "changed")
        self.assertEqual(semantic["automation-owner-status"].before.value, "PAUSED")
        self.assertEqual(semantic["automation-owner-status"].after.value, "ACTIVE")
        self.assertEqual(semantic["automation-protected-fields"].kind, "preserved")
        self.assertEqual(semantic["automation-policy-binding"].kind, "preserved")
        self.assertNotEqual(
            semantic["automation-policy-binding"].owner,
            semantic["automation-owner-status"].owner,
        )
        route = definition.route_gate_request(target, inputs, source)
        self.assertEqual(route.purpose, "fix-execution")
        self.assertEqual(route.recipient, fix_task["id"])
        dispatched = definition.dispatch(target, inputs, source)
        self.assertIn("exact existing automation ID", owner.app_server_client.prompt)
        self.assertIn("Never write automation.toml", owner.app_server_client.prompt)
        self.assertIn("must remain at the supplied version", owner.app_server_client.prompt)

        pending = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(pending.state, "pending")
        self.assertTrue(pending.evidence["policy_postcondition_current"])
        self.assertFalse(pending.evidence["automation_postcondition_current"])
        self.assertEqual(
            pending.evidence["partial_posture"],
            "policy-current-automation-pending",
        )

        binding["current"] = {
            **current_automation,
            **expected_automation,
            "status": "available",
            "manifest_sha256": "8" * 64,
            "protected_sha256": current_automation["protected_sha256"],
        }
        binding["mismatches"] = []
        binding["repairable"] = False
        binding["active_target_owners"] = {
            "status": "available",
            "target_thread_id": role_task["id"],
            "selected_automation_id": expected_automation["id"],
            "unavailable_automation_ids": [],
            "owners": [
                {
                    "automation_id": expected_automation["id"],
                    "manifest_sha256": "8" * 64,
                    "relation": "selected-role",
                    "canonical_claims": claims,
                }
            ],
            "conflicting_owner_ids": [],
            "fingerprint": "b" * 64,
        }
        applied = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(applied.state, "applied")
        self.assertTrue(applied.evidence["automation_binding_applied"])
        self.assertTrue(applied.evidence["duplicate_role_absent"])
        self.assertTrue(applied.evidence["protected_automation_fields_preserved"])
        self.assertTrue(applied.evidence["role_target_postcondition_current"])
        self.assertTrue(applied.evidence["fix_executor_postcondition_current"])
        self.assertTrue(applied.evidence["automation_timezone_current"])
        self.assertFalse(applied.evidence["direct_policy_write"])
        self.assertFalse(applied.evidence["direct_automation_write"])

        binding["current"]["protected_sha256"] = "9" * 64
        protected_drift = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(protected_drift.state, "pending")
        self.assertFalse(
            protected_drift.evidence["protected_automation_fields_preserved"]
        )

        role_task["project_binding"]["project_id"] = "other"
        role_drift = definition.verify(target, inputs, source, dispatched)
        self.assertEqual(role_drift.state, "pending")
        self.assertFalse(role_drift.evidence["role_target_postcondition_current"])
        role_task["project_binding"]["project_id"] = project.id

        binding["current"] = current_automation
        binding["mismatches"] = []
        binding["repairable"] = False
        with self.assertRaises(OperationError) as already_current:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            already_current.exception.code,
            "automation_binding_already_reconciled",
        )

        binding["mismatches"] = ["automation kind differs"]
        with self.assertRaises(OperationError) as unsupported:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            unsupported.exception.code,
            "automation_binding_repair_unsupported",
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
        semantic = {
            row.id: row
            for row in definition.describe_effect(target, {}, source).semantic_changes
        }
        self.assertEqual(semantic["mission-binding"].kind, "added")
        self.assertEqual(semantic["mission-binding"].before.posture, "unavailable")
        self.assertEqual(
            semantic["mission-binding"].after.value,
            expected_mission["mission_root"],
        )
        self.assertEqual(semantic["mission-target-task"].kind, "preserved")
        self.assertEqual(semantic["mission-tracker-content"].kind, "preserved")
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
            "execution_contract": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "xhigh",
                "source_record_sha256": "6" * 64,
                "source_size": 1_024,
                "source_mtime_ns": 1_786_279_000_000_000_000,
                "source_device": 1,
                "source_inode": 2,
                "scan_complete": True,
                "scan_bytes": 1_024,
            },
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
                prior_policy_history_head,
                prior_policy_history_count,
                expected_owner_sha256,
                expected_normalized_policy_sha256,
            ):
                if (
                    selected_target != target_id
                    or role != "notice_reviewer"
                    or candidate_task_id != candidate_id
                    or prior_policy_sha256 != policy["policy_sha256"]
                    or prior_policy_version != 7
                    or prior_policy_history_head != prior_record["record_sha256"]
                    or prior_policy_history_count != 1
                    or expected_owner_sha256 != "1" * 64
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
            def read_task_with_execution_contract(_projects, task_id):
                if task_id != candidate_id:
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
        self.assertEqual(
            source.evidence["observed_model_and_effort"]["model"],
            "gpt-5.6-sol",
        )
        self.assertEqual(
            source.evidence["observed_model_and_effort"]["reasoning"],
            "xhigh",
        )
        semantic = {
            row.id: row
            for row in definition.describe_effect(target, inputs, source).semantic_changes
        }
        self.assertEqual(semantic["role-task-binding"].kind, "added")
        self.assertEqual(semantic["role-task-binding"].before.posture, "unavailable")
        self.assertEqual(semantic["role-task-binding"].after.value, candidate_id)
        self.assertEqual(semantic["role-candidate-task"].kind, "preserved")
        self.assertEqual(semantic["role-automation-set"].kind, "preserved")
        self.assertIsNone(definition.route_gate_request)

        candidate_task["turns"] = [
            {
                "id": "turn-partial-001",
                "status": "completed",
                "items": [],
                "items_truncated": True,
            }
        ]
        with self.assertRaises(OperationError) as partial_items:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            partial_items.exception.code,
            "role_binding_task_history_partial",
        )
        candidate_task["turns"] = []

        candidate_task["execution_contract"]["reasoning_effort"] = "max"
        with self.assertRaises(OperationError) as wrong_effort:
            definition.resolve_source(target, inputs)
        self.assertEqual(
            wrong_effort.exception.code,
            "role_binding_task_model_contract_mismatch",
        )
        candidate_task["execution_contract"]["reasoning_effort"] = "xhigh"

        project_binding["fingerprint"] = "9" * 64
        with self.assertRaises(OperationOwnerError) as changed_project:
            definition.dispatch(target, inputs, source)
        self.assertEqual(
            changed_project.exception.code,
            "role_binding_project_changed",
        )
        project_binding["fingerprint"] = "2" * 64

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
        self.assertTrue(applied.evidence["run_project_binding_current"])
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

        project_binding["fingerprint"] = "9" * 64
        changed_project_verification = definition.verify(
            target,
            inputs,
            source,
            dispatched,
        )
        self.assertEqual(changed_project_verification.state, "unverified")
        self.assertFalse(
            changed_project_verification.evidence["run_project_binding_current"]
        )
        self.assertFalse(changed_project_verification.evidence["route_gate_accepted"])
        project_binding["fingerprint"] = "2" * 64

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
