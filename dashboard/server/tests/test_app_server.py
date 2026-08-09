from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from dashboard.server.tests.fake_app_server import write_contract

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

        self.assertEqual(len(retained), MAX_EVENTS)
        self.assertEqual(retained[0]["sequence"], 10)
        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0]["sequence"], events.sequence)

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


if __name__ == "__main__":
    unittest.main()
