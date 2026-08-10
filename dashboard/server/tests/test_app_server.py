from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
import time
from typing import Any, Mapping
import unittest
from unittest.mock import patch

from dashboard.server.tests.fake_app_server import fake_thread, write_contract

import software_factory_dashboard.app_server as app_server_module
from software_factory_dashboard.app_server import (
    MAX_EVENTS,
    AppServerError,
    CodexAppServerClient,
    TaskEventBuffer,
)
from software_factory_dashboard.catalog import ProjectRecord


FAKE_SERVER = Path(__file__).with_name("fake_app_server.py")


class CodexAppServerClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        self.contract = self.root / "compatibility.json"
        write_contract(self.contract)
        self.project = ProjectRecord(
            id="demo",
            label="Demo",
            root=str(self.project_root),
        )
        self.clients: list[CodexAppServerClient] = []

    def tearDown(self) -> None:
        for client in self.clients:
            client.close()
        self.temporary.cleanup()

    def client(
        self, mode: str = "normal", *, request_timeout: float = 1
    ) -> CodexAppServerClient:
        client = CodexAppServerClient(
            command=(
                sys.executable,
                str(FAKE_SERVER),
                "--mode",
                mode,
                "--cwd",
                str(self.project_root),
            ),
            compatibility_path=self.contract,
            request_timeout=request_timeout,
        )
        self.clients.append(client)
        return client

    @staticmethod
    def wait_for(predicate, timeout: float = 2) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        raise AssertionError("condition was not reached")

    def test_exact_bundle_handshake_list_read_and_feature_matrix(self) -> None:
        client = self.client()

        state = client.integration_state()
        listing = client.list_tasks((self.project,), limit=10)
        detail = client.read_task((self.project,), "task-fake-001")

        self.assertEqual(state["status"], "available")
        self.assertEqual(state["protocol_status"], "compatible")
        self.assertEqual(state["cli"]["version"], "codex-cli 0.145.0")
        self.assertEqual(
            state["schema"]["semantic_manifest_sha256"],
            state["schema"]["expected_semantic_manifest_sha256"],
        )
        self.assertEqual(listing["tasks"][0]["id"], "task-fake-001")
        self.assertEqual(
            listing["tasks"][0]["project_binding"],
            {"status": "bound", "project_id": "demo", "candidates": ["demo"]},
        )
        self.assertEqual(detail["task"]["status"]["type"], "idle")
        self.assertEqual(
            next(item for item in state["features"] if item["capability"] == "raw_protocol")[
                "status"
            ],
            "unavailable",
        )
        self.assertEqual(
            next(item for item in state["features"] if item["capability"] == "task_list")[
                "exposure"
            ],
            "read",
        )
        self.assertEqual(
            next(item for item in state["features"] if item["capability"] == "task_start")[
                "exposure"
            ],
            "owner-gated",
        )

    def test_task_and_turn_operations_are_bound_to_registered_cwd(self) -> None:
        client = self.client()

        started = client.start_task((self.project,), project_id="demo")
        resumed = client.resume_task((self.project,), "task-fake-001")
        turn = client.start_turn((self.project,), "task-fake-001", "Continue safely.")
        steered = client.steer_turn(
            (self.project,), "task-fake-001", "turn-active-001", "Narrow the work."
        )
        interrupted = client.interrupt_turn(
            (self.project,), "task-fake-001", "turn-active-001"
        )
        ephemeral = client.start_task((self.project,), project_id="demo", ephemeral=True)
        ephemeral_turn = client.start_turn(
            (self.project,), "task-fake-001", "No-write smoke."
        )

        self.assertEqual(started["operation"], "task_started")
        self.assertEqual(resumed["operation"], "task_resumed")
        self.assertEqual(turn["turn"]["status"], "inProgress")
        self.assertEqual(steered["turn_id"], "turn-active-001")
        self.assertEqual(interrupted["operation"], "turn_interrupted")
        self.assertTrue(ephemeral["task"]["ephemeral"])
        self.assertEqual(ephemeral_turn["operation"], "turn_started")

        outside = ProjectRecord(id="outside", label="Outside", root=str(self.root / "outside"))
        with self.assertRaisesRegex(AppServerError, "registered cwd"):
            client.resume_task((outside,), "task-fake-001")

    def test_long_lived_task_response_remains_bounded_and_does_not_drop_adapter(self) -> None:
        client = self.client("large-task-response")
        detail = client.read_task((self.project,), "task-fake-001", include_turns=True)

        self.assertEqual(detail["task"]["id"], "task-fake-001")
        self.assertEqual(detail["task"]["status"]["type"], "active")
        self.assertLessEqual(
            len(detail["task"]["turns"][0]["items"][0]["summary"]),
            app_server_module.MAX_TEXT,
        )
        self.assertEqual(client.integration_state()["status"], "available")

    def test_configured_role_turn_binds_exact_unregistered_cwd_and_resume(self) -> None:
        client = self.client()
        role_cwd = self.root / "codex-role-workspace"
        role_cwd.mkdir()
        role_id = "watcher-task-001"
        role_stat = role_cwd.stat()
        role_identity = (role_stat.st_dev, role_stat.st_ino)
        projected = {
            "id": role_id,
            "cwd": str(role_cwd),
            "status": {"type": "notLoaded"},
        }
        resumed_thread = fake_thread(str(role_cwd))
        resumed_thread["id"] = role_id
        resumed_thread["sessionId"] = role_id
        active_turn = fake_thread(
            str(role_cwd),
            active_turn=True,
            turn_text="Immediate check.",
        )["turns"][0]

        def request(capability, params):
            self.assertEqual(params["threadId"], role_id)
            if capability == "task_resume":
                return {"thread": resumed_thread}
            if capability == "turn_start":
                return {"turn": active_turn}
            raise AssertionError(f"unexpected capability {capability}")

        with (
            patch.object(
                client,
                "read_task",
                return_value={"task": projected},
            ),
            patch.object(client, "_request", side_effect=request) as owner_request,
        ):
            result = client.start_configured_role_turn(
                (self.project,),
                role_id,
                "Immediate check.",
                expected_cwd=str(role_cwd),
                expected_cwd_identity=role_identity,
            )
        self.assertTrue(result["task_resumed"])
        self.assertEqual(result["operation"], "role_turn_started")
        self.assertEqual(owner_request.call_count, 2)

        with patch.object(
            client,
            "read_task",
            return_value={"task": {**projected, "cwd": str(self.project_root)}},
        ):
            with self.assertRaisesRegex(AppServerError, "changed after preview"):
                client.start_configured_role_turn(
                    (self.project,),
                    role_id,
                    "Immediate check.",
                    expected_cwd=str(role_cwd),
                    expected_cwd_identity=role_identity,
                )

        def replace_role_cwd(*_args, **_kwargs):
            role_cwd.rmdir()
            role_cwd.mkdir()
            return {"task": {**projected, "status": {"type": "idle"}}}

        with (
            patch.object(client, "read_task", side_effect=replace_role_cwd),
            patch.object(client, "_request") as owner_request,
        ):
            with self.assertRaisesRegex(AppServerError, "changed after preview"):
                client.start_configured_role_turn(
                    (self.project,),
                    role_id,
                    "Immediate check.",
                    expected_cwd=str(role_cwd),
                    expected_cwd_identity=role_identity,
                )
        owner_request.assert_not_called()

    def test_approval_response_is_fingerprinted_and_single_use(self) -> None:
        client = self.client("approval")
        self.wait_for(lambda: len(client.pending_requests()) == 1)
        request = client.pending_requests()[0]

        resolved = client.respond_to_server_request(
            request["id"], request["source_fingerprint"], {"decision": "decline"}
        )

        self.assertEqual(resolved["status"], "responded")
        self.assertEqual(client.pending_requests(), [])
        with self.assertRaisesRegex(AppServerError, "already answered"):
            client.respond_to_server_request(
                request["id"], request["source_fingerprint"], {"decision": "accept"}
            )

    def test_user_input_requires_exact_current_questions(self) -> None:
        client = self.client("user-input")
        self.wait_for(lambda: len(client.pending_requests()) == 1)
        request = client.pending_requests()[0]

        with self.assertRaisesRegex(AppServerError, "each current question"):
            client.respond_to_server_request(
                request["id"], request["source_fingerprint"], {"answers": {}}
            )
        resolved = client.respond_to_server_request(
            request["id"],
            request["source_fingerprint"],
            {"answers": {"choice": ["First"]}},
        )

        self.assertEqual(resolved["status"], "responded")

    def test_unknown_notification_is_not_exposed_and_malformed_json_fails_closed(self) -> None:
        unknown = self.client("unknown-notification")
        listing = unknown.list_tasks((self.project,))
        state = unknown.integration_state()

        self.assertEqual(len(listing["tasks"]), 1)
        self.assertEqual(state["ignored_protocol_messages"], 1)
        self.assertNotIn("secret", json.dumps(unknown.events.after(0, timeout=0)))

        malformed = self.client("malformed")
        malformed_state = malformed.integration_state()
        self.assertEqual(malformed_state["status"], "unavailable")
        self.assertEqual(malformed_state["last_error"]["code"], "app_server_malformed_json")

    def test_duplicate_response_and_schema_drift_disable_all_mutations(self) -> None:
        invalid_response = self.client("invalid-list-schema")
        with self.assertRaises(AppServerError) as invalid_error:
            invalid_response.list_tasks((self.project,))
        self.assertEqual(invalid_error.exception.code, "app_server_message_invalid")
        invalid_state = invalid_response.integration_state()
        self.assertEqual(invalid_state["status"], "unavailable")
        self.assertTrue(
            all(item["status"] == "unavailable" for item in invalid_state["features"])
        )

        invalid_error_response = self.client("invalid-error-schema")
        with self.assertRaises(AppServerError) as protocol_error:
            invalid_error_response.list_tasks((self.project,))
        self.assertEqual(protocol_error.exception.code, "app_server_message_invalid")
        self.assertEqual(invalid_error_response.integration_state()["status"], "unavailable")

        duplicate = self.client("duplicate-response")
        duplicate.list_tasks((self.project,))
        self.wait_for(lambda: duplicate.integration_state()["status"] == "unavailable")
        self.assertEqual(
            duplicate.integration_state()["last_error"]["code"],
            "app_server_duplicate_response",
        )

        contract = json.loads(self.contract.read_text(encoding="utf-8"))
        contract["semantic_manifest_sha256"] = "0" * 64
        self.contract.write_text(json.dumps(contract), encoding="utf-8")
        incompatible = self.client()
        state = incompatible.integration_state()

        self.assertEqual(state["protocol_status"], "incompatible")
        self.assertTrue(all(item["status"] == "unavailable" for item in state["features"]))

    def test_capability_schema_gates_are_independent_after_handshake(self) -> None:
        client = self.client()
        compatibility = client._compatibility
        self.assertIsNotNone(compatibility)
        assert compatibility is not None
        validators = dict(compatibility.validators)
        validators.pop("client:task_start:response")
        client._compatibility = replace(compatibility, validators=validators)

        features = {
            item["capability"]: item for item in client.integration_state()["features"]
        }
        self.assertEqual(features["task_list"]["status"], "supported")
        self.assertEqual(features["task_start"]["status"], "unavailable")
        self.assertEqual(
            features["task_start"]["reason"],
            "The exact capability schema is unavailable.",
        )

    def test_child_death_does_not_require_or_mutate_file_backed_sources(self) -> None:
        client = self.client()
        process = client._process
        assert process is not None

        process.kill()
        process.wait(timeout=2)
        self.wait_for(lambda: client.integration_state()["status"] == "unavailable")

        state = client.integration_state()
        self.assertEqual(state["last_error"]["code"], "app_server_disconnected")
        self.assertFalse(self.contract.stat().st_size == 0)

    def test_timeout_and_mismatched_response_fail_closed_with_bounded_backoff(self) -> None:
        timeout = self.client("timeout", request_timeout=0.1)
        with self.assertRaises(AppServerError) as timeout_error:
            timeout.list_tasks((self.project,))

        self.assertEqual(timeout_error.exception.code, "app_server_timeout")
        timeout_state = timeout.integration_state()
        self.assertEqual(timeout_state["status"], "unavailable")
        self.assertGreater(timeout_state["reconnect"]["retry_after_ms"], 0)
        self.assertLessEqual(timeout_state["reconnect"]["retry_after_ms"], 30_000)

        mismatched = self.client("mismatched-response")
        with self.assertRaises(AppServerError) as mismatched_error:
            mismatched.list_tasks((self.project,))
        self.assertEqual(
            mismatched_error.exception.code,
            "app_server_response_id_mismatch",
        )
        self.assertEqual(mismatched.integration_state()["status"], "unavailable")

    def test_restart_cancellation_cannot_poison_the_successor_generation(self) -> None:
        client = self.client("timeout", request_timeout=2)
        stale_failure_entered = Event()
        release_stale_failure = Event()
        original_set_failure = client._set_failure
        request_errors: list[AppServerError] = []

        def delay_stale_failure(
            error: AppServerError,
            *,
            terminate: bool = True,
            expected_generation: int | None = None,
        ) -> None:
            if error.code == "app_server_restarted":
                stale_failure_entered.set()
                release_stale_failure.wait(2)
            original_set_failure(
                error,
                terminate=terminate,
                expected_generation=expected_generation,
            )

        client._set_failure = delay_stale_failure  # type: ignore[method-assign]

        def list_during_restart() -> None:
            try:
                client.list_tasks((self.project,))
            except AppServerError as error:
                request_errors.append(error)

        worker = Thread(target=list_during_restart)
        worker.start()
        self.wait_for(lambda: len(client._pending) == 1)
        try:
            restarted = client.restart()
            self.assertTrue(stale_failure_entered.wait(2))
        finally:
            release_stale_failure.set()
            worker.join(timeout=2)

        state = client.integration_state()
        process = client._process
        self.assertEqual(restarted["status"], "available")
        self.assertEqual([error.code for error in request_errors], ["app_server_restarted"])
        self.assertEqual(state["status"], "available")
        self.assertIsNone(state["last_error"])
        self.assertIsNotNone(process)
        assert process is not None
        self.assertIsNone(process.poll())

    def test_prior_generation_request_cannot_write_to_the_successor_child(self) -> None:
        client = self.client("timeout", request_timeout=2)
        prior_write_entered = Event()
        release_prior_write = Event()
        original_write_message = client._write_message
        request_errors: list[AppServerError] = []

        def delay_prior_write(
            message: Mapping[str, Any],
            *,
            expected_generation: int | None = None,
        ) -> None:
            if message.get("method") == "thread/list" and expected_generation == 1:
                prior_write_entered.set()
                release_prior_write.wait(2)
            original_write_message(
                message,
                expected_generation=expected_generation,
            )

        client._write_message = delay_prior_write  # type: ignore[method-assign]

        def list_during_restart() -> None:
            try:
                client.list_tasks((self.project,))
            except AppServerError as error:
                request_errors.append(error)

        worker = Thread(target=list_during_restart)
        worker.start()
        self.assertTrue(prior_write_entered.wait(2))
        try:
            restarted = client.restart()
        finally:
            release_prior_write.set()
            worker.join(timeout=2)

        state = client.integration_state()
        process = client._process
        self.assertEqual(restarted["status"], "available")
        self.assertEqual([error.code for error in request_errors], ["app_server_restarted"])
        self.assertEqual(state["status"], "available")
        self.assertIsNone(state["last_error"])
        self.assertIsNotNone(process)
        assert process is not None
        self.assertIsNone(process.poll())

    def test_prior_generation_notifications_and_callbacks_are_not_published(self) -> None:
        notification_client = self.client()
        notification_entered = Event()
        release_notification = Event()
        original_projection = notification_client._notification_projection
        notification_sequence = notification_client.events.sequence

        def delay_notification(event_type: str, params: Mapping[str, Any]) -> dict[str, Any]:
            if event_type == "error":
                notification_entered.set()
                release_notification.wait(2)
            return original_projection(event_type, params)

        notification_client._notification_projection = (  # type: ignore[method-assign]
            delay_notification
        )
        notification = {
            "threadId": "task-prior",
            "turnId": "turn-prior",
            "willRetry": False,
            "error": {"message": "Prior generation failure", "codexErrorInfo": None},
        }
        notification_worker = Thread(
            target=lambda: notification_client._receive_notification(
                "error",
                notification,
                generation=1,
            )
        )
        notification_worker.start()
        self.assertTrue(notification_entered.wait(2))
        try:
            self.assertEqual(notification_client.restart()["status"], "available")
        finally:
            release_notification.set()
            notification_worker.join(timeout=2)
        self.assertNotIn(
            "error",
            [
                event["type"]
                for event in notification_client.events.after(notification_sequence, timeout=0)
            ],
        )

        callback_client = self.client()
        callback_entered = Event()
        release_callback = Event()
        original_digest = app_server_module._digest
        callback_sequence = callback_client.events.sequence
        callback = {
            "id": "callback-prior",
            "method": "item/commandExecution/requestApproval",
            "params": {
                "threadId": "task-fake-001",
                "turnId": "turn-active-001",
                "itemId": "item-command-prior",
                "startedAtMs": 1786279000000,
                "command": "printf safe",
                "cwd": str(self.project_root),
                "reason": "Prior generation callback",
            },
        }

        def delay_callback(value: Any) -> str:
            if isinstance(value, dict) and value.get("id") == "callback-prior":
                callback_entered.set()
                release_callback.wait(2)
            return original_digest(value)

        with patch.object(app_server_module, "_digest", delay_callback):
            callback_worker = Thread(
                target=lambda: callback_client._receive_server_request(
                    callback,
                    generation=1,
                )
            )
            callback_worker.start()
            self.assertTrue(callback_entered.wait(2))
            try:
                self.assertEqual(callback_client.restart()["status"], "available")
            finally:
                release_callback.set()
                callback_worker.join(timeout=2)

        self.assertEqual(callback_client.pending_requests(), [])
        self.assertNotIn(
            "request",
            [
                event["type"]
                for event in callback_client.events.after(callback_sequence, timeout=0)
            ],
        )

    def test_task_not_found_terminal_state_and_unknown_method_are_explicit(self) -> None:
        missing = self.client("task-not-found")
        with self.assertRaises(AppServerError) as missing_error:
            missing.read_task((self.project,), "00000000-0000-0000-0000-000000000000")
        self.assertEqual(missing_error.exception.code, "task_not_found")
        self.assertEqual(missing_error.exception.status, 404)

        terminal = self.client("terminal")
        task = terminal.list_tasks((self.project,))["tasks"][0]
        self.assertEqual(task["status"]["type"], "idle")
        self.assertEqual(task["turns"][0]["status"], "completed")
        self.assertEqual(task["turns"][0]["items"][0]["summary"], "Done.")

        with self.assertRaises(AppServerError) as unknown_error:
            terminal._request("task_fork", {})
        self.assertEqual(unknown_error.exception.code, "app_server_method_rejected")

    def test_missing_cli_and_event_replay_bounds_are_visible(self) -> None:
        unavailable = CodexAppServerClient(
            command=(str(self.root / "missing-codex"),),
            compatibility_path=self.contract,
            request_timeout=0.1,
        )
        self.clients.append(unavailable)
        state = unavailable.integration_state()
        self.assertEqual(state["status"], "unavailable")
        self.assertEqual(state["last_error"]["code"], "codex_cli_unavailable")

        events = TaskEventBuffer()
        for index in range(MAX_EVENTS + 9):
            events.publish("task_status", {"index": index})
        retained = events.after(0, timeout=0)
        resumed = events.after(events.sequence - 1, timeout=0)
        truncated_replay = events.replay_state(0)
        current_replay = events.replay_state(events.sequence - 1)

        self.assertEqual(len(retained), MAX_EVENTS)
        self.assertEqual(retained[0]["sequence"], 10)
        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0]["sequence"], events.sequence)
        self.assertEqual(
            truncated_replay,
            {
                "requested_after": 0,
                "oldest_available": 10,
                "latest_available": MAX_EVENTS + 9,
                "truncated": True,
            },
        )
        self.assertFalse(current_replay["truncated"])

    def test_task_error_event_is_narrowed_and_redacted(self) -> None:
        client = self.client()
        sequence = client.events.sequence

        client._receive_notification(
            "error",
            {
                "threadId": "task-fake-001",
                "turnId": "turn-active-001",
                "willRetry": False,
                "error": {
                    "message": f"Failure in {Path.home()} from https://example.invalid/private",
                    "codexErrorInfo": "usageLimitExceeded",
                },
            },
        )

        event = client.events.after(sequence, timeout=0)[0]
        self.assertEqual(event["type"], "error")
        self.assertEqual(event["data"]["code"], "usageLimitExceeded")
        self.assertFalse(event["data"]["will_retry"])
        self.assertIn("<home>", event["data"]["message"])
        self.assertIn("<url>", event["data"]["message"])
        self.assertNotIn(str(Path.home()), event["data"]["message"])

    def test_answered_callback_records_are_evicted_before_new_requests(self) -> None:
        client = self.client()

        for index in range(105):
            client._receive_server_request(
                {
                    "id": f"callback-{index:03d}",
                    "method": "item/commandExecution/requestApproval",
                    "params": {
                        "threadId": "task-fake-001",
                        "turnId": "turn-active-001",
                        "itemId": f"item-command-{index:03d}",
                        "startedAtMs": 1786279000000 + index,
                        "command": "printf safe",
                        "cwd": str(self.project_root),
                        "reason": "Capacity proof",
                    },
                }
            )
            pending = client.pending_requests()
            self.assertEqual(len(pending), 1)
            client.respond_to_server_request(
                pending[0]["id"],
                pending[0]["source_fingerprint"],
                {"decision": "decline"},
            )

        self.assertEqual(client.pending_requests(), [])
        self.assertEqual(len(client._server_requests), 100)
        self.assertTrue(
            any(
                record.raw_id == "callback-104"
                for record in client._server_requests.values()
            )
        )


if __name__ == "__main__":
    unittest.main()
