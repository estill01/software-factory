from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import time
from typing import Any
import unittest
from unittest.mock import patch

import software_factory_dashboard.app_server as app_server_module
from software_factory_dashboard.app_server import (
    MAX_EVENTS,
    AppServerError,
    CodexAppServerClient,
    TaskEventBuffer,
)
from software_factory_dashboard.catalog import ProjectRecord

from fake_shared_client import fake_client_binding


class CodexAppServerClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        self.project = ProjectRecord(
            id="demo", label="Demo", root=str(self.project_root)
        )
        self.clients: list[CodexAppServerClient] = []

    def tearDown(self) -> None:
        for client in self.clients:
            client.close()
        self.temporary.cleanup()

    def client(
        self, mode: str = "normal", *, request_timeout: float = 1
    ) -> tuple[Any, Any]:
        wheel, codex_home, loader, module = fake_client_binding(
            self.root, self.project_root, mode=mode
        )
        with patch.object(app_server_module, "_qualified_client_loader", loader):
            client = CodexAppServerClient(
                wheel_path=wheel,
                codex_home=codex_home,
                request_timeout=request_timeout,
            )
        self.clients.append(client)
        return client, module

    @staticmethod
    def wait_for(predicate: Any, timeout: float = 2) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        raise AssertionError("condition was not reached")

    def test_exact_qualified_client_list_read_and_feature_matrix(self) -> None:
        client, _module = self.client()

        state = client.integration_state()
        listing = client.list_tasks((self.project,), limit=10)
        detail = client.read_task((self.project,), "task-fake-001")
        contracted = client.read_task_with_execution_contract(
            (self.project,), "task-fake-001"
        )

        self.assertEqual(state["status"], "available")
        self.assertEqual(state["protocol_status"], "compatible")
        self.assertEqual(state["client_package"]["version"], "0.1.0")
        self.assertEqual(
            state["client_package"]["release_posture"],
            "no-license-selected/unpublished",
        )
        self.assertEqual(state["cli"]["version"], "0.147.0")
        self.assertEqual(
            state["schema"]["schema_tree_root_sha256"],
            state["schema"]["expected_schema_tree_root_sha256"],
        )
        self.assertEqual(listing["tasks"][0]["id"], "task-fake-001")
        self.assertEqual(
            listing["tasks"][0]["project_binding"],
            {"status": "bound", "project_id": "demo", "candidates": ["demo"]},
        )
        self.assertEqual(detail["task"]["status"]["type"], "idle")
        self.assertEqual(
            contracted["task"]["execution_contract"]["model"], "gpt-5.6-sol"
        )
        self.assertEqual(
            contracted["task"]["execution_contract"]["reasoning_effort"], "xhigh"
        )
        raw = next(
            item for item in state["features"] if item["capability"] == "raw_protocol"
        )
        self.assertEqual(raw["status"], "unavailable")

    def test_task_and_turn_operations_remain_bound_to_registered_cwd(self) -> None:
        client, _module = self.client()

        started = client.start_task((self.project,), project_id="demo", ephemeral=False)
        task_id = started["task"]["id"]
        turn = client.start_turn(
            (self.project,), task_id, "Implement one bounded block."
        )
        turn_id = turn["turn"]["id"]
        steered = client.steer_turn(
            (self.project,), task_id, turn_id, "Keep scope exact."
        )
        interrupted = client.interrupt_turn((self.project,), task_id, turn_id)

        self.assertEqual(Path(started["task"]["cwd"]), self.project_root)
        self.assertEqual(steered["operation"], "turn_steered")
        self.assertEqual(interrupted["operation"], "turn_interrupted")
        outside = ProjectRecord(
            id="outside", label="Outside", root=str(self.root / "outside")
        )
        (self.root / "outside").mkdir()
        with self.assertRaisesRegex(AppServerError, "registered project"):
            client.start_task((self.project,), project_id=outside.id)

    def test_long_task_response_is_projected_to_bounded_items(self) -> None:
        client, _module = self.client("large-task-response")
        detail = client.read_task((self.project,), "task-fake-001")
        item = detail["task"]["turns"][0]["items"][0]
        self.assertTrue(item["summary_truncated"])
        self.assertLessEqual(len(item["summary"]), app_server_module.MAX_TEXT)
        self.assertEqual(client.integration_state()["status"], "available")

    def test_user_projection_hashes_content_without_inventing_authority(self) -> None:
        direct = app_server_module._item_projection(
            {
                "id": "item-user",
                "type": "userMessage",
                "clientId": "codex-desktop",
                "content": [{"type": "text", "text": "continue"}],
            }
        )
        routed = app_server_module._item_projection(
            {
                "id": "item-routed",
                "type": "userMessage",
                "content": [
                    {"type": "text", "text": "<codex_delegation>...</codex_delegation>"}
                ],
            }
        )
        self.assertEqual(direct["user_authority_status"], "unverified")
        self.assertEqual(routed["user_authority_status"], "ineligible")
        self.assertEqual(routed["user_input_classification"], "routed-delegation")

    def test_approval_callback_is_fingerprinted_typed_and_single_use(self) -> None:
        client, _module = self.client("approval")
        self.wait_for(lambda: len(client.pending_requests()) == 1)
        pending = client.pending_requests()[0]

        resolved = client.respond_to_server_request(
            pending["id"], pending["source_fingerprint"], {"decision": "decline"}
        )

        self.assertEqual(resolved["status"], "responded")
        with self.assertRaisesRegex(AppServerError, "already answered"):
            client.respond_to_server_request(
                pending["id"], pending["source_fingerprint"], {"decision": "decline"}
            )

    def test_user_input_requires_exact_current_questions(self) -> None:
        client, _module = self.client("user-input")
        self.wait_for(lambda: len(client.pending_requests()) == 1)
        pending = client.pending_requests()[0]
        with self.assertRaisesRegex(AppServerError, "each current question"):
            client.respond_to_server_request(
                pending["id"],
                pending["source_fingerprint"],
                {"answers": {"wrong": ["x"]}},
            )
        resolved = client.respond_to_server_request(
            pending["id"],
            pending["source_fingerprint"],
            {"answers": {"choice": ["First"]}},
        )
        self.assertEqual(resolved["status"], "responded")

    def test_task_not_found_and_timeout_fail_closed(self) -> None:
        missing, _module = self.client("task-not-found")
        with self.assertRaisesRegex(AppServerError, "not found") as caught:
            missing.read_task((self.project,), "task-missing")
        self.assertEqual(caught.exception.status, 404)

        timeout, _module = self.client("timeout", request_timeout=0.05)
        with self.assertRaisesRegex(AppServerError, "bound"):
            timeout.list_tasks((self.project,))
        self.assertEqual(timeout.integration_state()["status"], "unavailable")

    def test_typed_event_stream_is_narrowed_and_redacted(self) -> None:
        client, module = self.client()
        assert module.last_session is not None
        owner = client._owner
        assert owner is not None
        owner.call(
            module.last_session.event_queue.put(
                module.ErrorNotification.from_dict(
                    {
                        "threadId": "task-fake-001",
                        "turnId": "turn-active-001",
                        "error": {"message": f"failed at {Path.home()}/secret"},
                        "willRetry": False,
                    }
                )
            )
        )
        self.wait_for(
            lambda: any(item["type"] == "error" for item in client.events.after(0, 0))
        )
        event = next(
            item for item in client.events.after(0, 0) if item["type"] == "error"
        )
        self.assertIn("<home>", event["data"]["message"])
        self.assertNotIn(str(Path.home()), event["data"]["message"])

    def test_missing_exact_wheel_is_visible_and_event_replay_is_bounded(self) -> None:
        unavailable = CodexAppServerClient(auto_start=True)
        self.clients.append(unavailable)
        state = unavailable.integration_state()
        self.assertEqual(state["status"], "unavailable")
        self.assertEqual(state["last_error"]["code"], "app_server_artifact_required")

        events = TaskEventBuffer()
        for index in range(MAX_EVENTS + 2):
            events.publish("test", {"index": index})
        replay, rows = events.replay_after(0, timeout=0)
        self.assertTrue(replay["truncated"])
        self.assertEqual(len(rows), MAX_EVENTS)


if __name__ == "__main__":
    unittest.main()
