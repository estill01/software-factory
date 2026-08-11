from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest
from unittest.mock import patch

from test_tracker import FULL_TRACKER
from dashboard.server.tests.fake_app_server import write_contract
from test_admin_operations import (
    DeterministicOwner,
    execute_payload,
    preview_payload,
    test_definition,
)

from software_factory_dashboard.server import (
    DashboardConfigurationError,
    NONCE_PLACEHOLDER,
    ServerConfig,
    create_server,
)
from software_factory_dashboard.admin_operations import OperationRegistry
from software_factory_dashboard.operations import (
    DEFAULT_SUPERVISION_OWNER,
    OperationsProjectionService,
)
from software_factory_dashboard.app_server import COMPATIBILITY_PATH


FAKE_APP_SERVER = Path(__file__).with_name("fake_app_server.py")


@contextmanager
def running_server(
    static_dir: Path,
    *,
    catalog_path: Path | None = None,
    supervision_root: Path | None = None,
    automations_root: Path | None = None,
    codex_command: tuple[str, ...] = (),
    codex_compatibility_path: Path | None = None,
    operation_registry: OperationRegistry | None = None,
) -> Iterator[str]:
    server = create_server(
        ServerConfig(
            host="127.0.0.1",
            port=0,
            static_dir=static_dir,
            catalog_path=catalog_path or static_dir / ".catalog" / "projects.json",
            supervision_root=supervision_root or static_dir / ".supervision",
            automations_root=automations_root or static_dir / ".automations",
            codex_command=codex_command,
            codex_compatibility_path=(
                codex_compatibility_path
                if codex_compatibility_path is not None
                else COMPATIBILITY_PATH
            ),
            quiet=True,
        ),
        nonce="test-launch-nonce",
        operation_registry=operation_registry,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@dataclass(frozen=True)
class TestResponse:
    status: int
    headers: dict[str, str]
    body: bytes


def response(request: Request | str) -> TestResponse:
    try:
        opened = urlopen(request, timeout=3)
    except HTTPError as error:
        opened = error

    try:
        return TestResponse(
            status=opened.status,
            headers=dict(opened.headers.items()),
            body=opened.read(),
        )
    finally:
        opened.close()


class DashboardServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.static_dir = Path(self.temporary.name)
        (self.static_dir / "assets").mkdir()
        (self.static_dir / "index.html").write_text(
            f'<meta name="software-factory-mutation-nonce" content="{NONCE_PLACEHOLDER}">'
            '<main id="root"></main>',
            encoding="utf-8",
        )
        (self.static_dir / "assets" / "app-a1b2c3.js").write_text(
            "console.log('ready')", encoding="utf-8"
        )

    def make_repo(self, name: str) -> Path:
        root = (self.static_dir / "repositories" / name).resolve()
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "api@test.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "API Test"], check=True)
        (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
        return root

    @staticmethod
    def catalog_request(
        origin: str,
        path: str,
        payload: dict[str, object],
        method: str = "POST",
    ) -> TestResponse:
        return response(
            Request(
                f"{origin}{path}",
                data=json.dumps(payload).encode("utf-8"),
                method=method,
                headers={
                    "Content-Type": "application/json",
                    "Origin": origin,
                    "X-Software-Factory-Nonce": "test-launch-nonce",
                },
            )
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_non_loopback_bind_is_rejected(self) -> None:
        with self.assertRaisesRegex(DashboardConfigurationError, "127.0.0.1"):
            create_server(ServerConfig(host="0.0.0.0", port=8787))

    def test_health_uses_versioned_envelope_without_paths(self) -> None:
        with running_server(self.static_dir) as origin:
            result = response(f"{origin}/api/v1/health")
            payload = json.loads(result.body)

        self.assertEqual(result.status, 200)
        self.assertEqual(payload["data"]["status"], "ok")
        self.assertEqual(payload["data"]["integrations"]["frontend"]["status"], "available")
        self.assertEqual(payload["data"]["integrations"]["project_sources"]["status"], "available")
        self.assertEqual(payload["data"]["integrations"]["tracker_sources"]["status"], "available")
        self.assertEqual(payload["data"]["integrations"]["supervision_sources"]["status"], "available")
        self.assertIn("project-catalog", payload["coverage"]["observed"])
        self.assertEqual(payload["coverage"]["status"], "partial")
        self.assertRegex(payload["fingerprint"], r"^[0-9a-f]{64}$")
        self.assertNotIn(self.temporary.name, json.dumps(payload))

    def test_task_api_uses_exact_fake_protocol_and_registered_cwd(self) -> None:
        root = self.make_repo("task-api")
        compatibility = self.static_dir / "fake-app-server-compatibility.json"
        write_contract(compatibility)
        command = (
            sys.executable,
            str(FAKE_APP_SERVER),
            "--cwd",
            str(root),
        )
        with running_server(
            self.static_dir,
            codex_command=command,
            codex_compatibility_path=compatibility,
        ) as origin:
            initial_catalog = json.loads(
                response(f"{origin}/api/v1/projects?include_archived=true").body
            )
            created = self.catalog_request(
                origin,
                "/api/v1/projects",
                {
                    "source_fingerprint": initial_catalog["data"]["catalog_fingerprint"],
                    "project": {
                        "id": "task-api",
                        "label": "Task API",
                        "root": str(root),
                        "tracker_patterns": [],
                        "description": None,
                    },
                },
            )
            health = json.loads(response(f"{origin}/api/v1/health").body)
            integration = json.loads(response(f"{origin}/api/v1/task-integration").body)
            tasks = json.loads(response(f"{origin}/api/v1/tasks?limit=10").body)
            detail = json.loads(
                response(f"{origin}/api/v1/tasks/task-fake-001?include_turns=true").body
            )
            unavailable_start = self.catalog_request(
                origin,
                "/api/v1/tasks",
                {"project_id": "task-api", "ephemeral": False},
            )
            restarted = self.catalog_request(
                origin,
                "/api/v1/task-integration/restart",
                {"confirmation": "restart-codex-adapter"},
            )

        self.assertEqual(created.status, 201)
        self.assertEqual(health["data"]["integrations"]["codex_app_server"]["status"], "available")
        self.assertIn("codex-app-server", health["coverage"]["observed"])
        self.assertEqual(integration["data"]["integration"]["protocol_status"], "compatible")
        self.assertEqual(tasks["data"]["tasks"][0]["project_binding"]["project_id"], "task-api")
        self.assertEqual(detail["data"]["task"]["id"], "task-fake-001")
        self.assertEqual(unavailable_start.status, 404)
        self.assertEqual(
            json.loads(unavailable_start.body)["error"]["code"],
            "mutation_unavailable",
        )
        self.assertEqual(
            json.loads(restarted.body)["data"]["integration"]["restart_count"],
            1,
        )

    def test_factory_floor_composes_live_owners_and_preserves_query_boundary(self) -> None:
        root = self.make_repo("factory-floor")
        compatibility = self.static_dir / "factory-floor-compatibility.json"
        write_contract(compatibility)
        command = (
            sys.executable,
            str(FAKE_APP_SERVER),
            "--mode",
            "active",
            "--cwd",
            str(root),
        )
        with running_server(
            self.static_dir,
            codex_command=command,
            codex_compatibility_path=compatibility,
        ) as origin:
            initial_catalog = json.loads(
                response(f"{origin}/api/v1/projects?include_archived=true").body
            )
            created = self.catalog_request(
                origin,
                "/api/v1/projects",
                {
                    "source_fingerprint": initial_catalog["data"]["catalog_fingerprint"],
                    "project": {
                        "id": "factory-floor",
                        "label": "Factory Floor",
                        "root": str(root),
                        "tracker_patterns": [],
                        "description": None,
                    },
                },
            )
            floor_result = response(f"{origin}/api/v1/factory-floor")
            cached_floor_result = response(f"{origin}/api/v1/factory-floor")
            invalid_query = response(f"{origin}/api/v1/factory-floor?project=factory-floor")

        payload = json.loads(floor_result.body)
        self.assertEqual(created.status, 201)
        self.assertEqual(floor_result.status, 200)
        self.assertEqual(cached_floor_result.status, 200)
        self.assertEqual(
            json.loads(cached_floor_result.body)["observed_at"],
            payload["observed_at"],
        )
        self.assertEqual(payload["source"]["kind"], "factory-floor-composition")
        self.assertEqual(payload["data"]["summary"]["registered_projects"], 1)
        self.assertEqual(payload["data"]["rows"][0]["implementation"]["task_id"], "task-fake-001")
        self.assertEqual(payload["data"]["rows"][0]["supervision"]["status"], "unmonitored")
        self.assertEqual(
            {source["family"] for source in payload["data"]["source_health"]},
            {"catalog", "operations", "trackers", "tasks"},
        )
        self.assertTrue(all(metric["period"] for metric in payload["data"]["metrics"]))
        self.assertTrue(all(metric["coverage"] for metric in payload["data"]["metrics"]))
        self.assertEqual(invalid_query.status, 400)
        self.assertEqual(json.loads(invalid_query.body)["error"]["code"], "invalid_query")

    def test_task_events_and_mutations_require_same_origin_launch_nonce(self) -> None:
        with running_server(self.static_dir) as origin:
            event_without_origin = response(f"{origin}/api/v1/task-events")
            event_with_nonce_only = response(
                Request(
                    f"{origin}/api/v1/task-events",
                    headers={"X-Software-Factory-Nonce": "test-launch-nonce"},
                )
            )
            cross_site_event = response(
                Request(
                    f"{origin}/api/v1/task-events",
                    headers={
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "cross-site",
                        "X-Software-Factory-Nonce": "test-launch-nonce",
                    },
                )
            )
            event_stream = urlopen(
                Request(
                    f"{origin}/api/v1/task-events",
                    headers={
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                        "X-Software-Factory-Nonce": "test-launch-nonce",
                    },
                ),
                timeout=3,
            )
            try:
                event_stream_status = event_stream.status
                event_stream_type = event_stream.headers["Content-Type"]
                ready_event = event_stream.readline()
                ready_data = event_stream.readline()
            finally:
                event_stream.close()
            restart_without_nonce = response(
                Request(
                    f"{origin}/api/v1/task-integration/restart",
                    data=b'{"confirmation":"restart-codex-adapter"}',
                    method="POST",
                    headers={"Content-Type": "application/json", "Origin": origin},
                )
            )

        self.assertEqual(event_without_origin.status, 403)
        self.assertEqual(json.loads(event_without_origin.body)["error"]["code"], "origin_rejected")
        self.assertEqual(event_with_nonce_only.status, 403)
        self.assertEqual(cross_site_event.status, 403)
        self.assertEqual(event_stream_status, 200)
        self.assertEqual(event_stream_type, "text/event-stream; charset=utf-8")
        self.assertEqual(ready_event, b"event: ready\n")
        ready_payload = json.loads(ready_data.removeprefix(b"data: "))
        self.assertEqual(ready_payload["type"], "ready")
        self.assertEqual(
            ready_payload["replay"],
            {
                "latest_available": ready_payload["replay"]["latest_available"],
                "oldest_available": 1,
                "requested_after": 0,
                "truncated": False,
            },
        )
        self.assertEqual(restart_without_nonce.status, 403)
        self.assertEqual(json.loads(restart_without_nonce.body)["error"]["code"], "nonce_rejected")

    def test_operation_api_binds_preview_origin_nonce_request_and_postcondition(self) -> None:
        owner = DeterministicOwner()
        registry = OperationRegistry((test_definition(owner),))
        request_payload = preview_payload()
        with running_server(self.static_dir, operation_registry=registry) as origin:
            framework = json.loads(response(f"{origin}/api/v1/operations").body)
            missing_nonce = response(
                Request(
                    f"{origin}/api/v1/operations/preview",
                    data=json.dumps(request_payload).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json", "Origin": origin},
                )
            )
            preview_response = self.catalog_request(
                origin,
                "/api/v1/operations/preview",
                request_payload,
            )
            preview_data = json.loads(preview_response.body)["data"]
            operation_id = preview_data["operation"]["id"]
            status_before = json.loads(
                response(f"{origin}/api/v1/operations/{operation_id}").body
            )

            changed_request = execute_payload(preview_data, request_payload)
            changed_request["target"] = {
                "kind": "test-fixture",
                "id": "fixture-2",
                "project_id": "test",
            }
            changed = self.catalog_request(
                origin,
                "/api/v1/operations/execute",
                changed_request,
            )
            executed = self.catalog_request(
                origin,
                "/api/v1/operations/execute",
                execute_payload(preview_data, request_payload),
            )
            replayed = self.catalog_request(
                origin,
                "/api/v1/operations/execute",
                execute_payload(preview_data, request_payload),
            )
            cancel_after_request = self.catalog_request(
                origin,
                f"/api/v1/operations/{operation_id}/cancel",
                {"confirmation": "cancel-before-request"},
            )

        self.assertEqual(
            framework["data"]["framework"]["registered_operations"][0]["type"],
            "test.fixture-set",
        )
        self.assertTrue(framework["data"]["framework"]["ephemeral"])
        self.assertEqual(missing_nonce.status, 403)
        self.assertEqual(preview_response.status, 201)
        self.assertEqual(status_before["data"]["operation"]["state"], "previewed")
        self.assertEqual(owner.dispatches, 1)
        self.assertEqual(changed.status, 409)
        self.assertEqual(json.loads(changed.body)["error"]["code"], "preview_request_changed")
        self.assertEqual(executed.status, 200)
        self.assertEqual(json.loads(executed.body)["data"]["operation"]["state"], "applied")
        self.assertEqual(replayed.status, 409)
        self.assertEqual(json.loads(replayed.body)["error"]["code"], "preview_token_replayed")
        self.assertEqual(cancel_after_request.status, 409)
        self.assertEqual(
            json.loads(cancel_after_request.body)["error"]["code"],
            "cancel_boundary_crossed",
        )

    def test_task_request_is_visible_without_premature_response_control(self) -> None:
        root = self.make_repo("approval-api")
        compatibility = self.static_dir / "fake-approval-compatibility.json"
        write_contract(compatibility)
        command = (
            sys.executable,
            str(FAKE_APP_SERVER),
            "--mode",
            "approval",
            "--cwd",
            str(root),
        )
        with running_server(
            self.static_dir,
            codex_command=command,
            codex_compatibility_path=compatibility,
        ) as origin:
            tasks = json.loads(response(f"{origin}/api/v1/tasks").body)
            request_record = tasks["data"]["pending_requests"][0]
            payload = {
                "source_fingerprint": request_record["source_fingerprint"],
                "response": {"decision": "decline"},
            }
            unavailable_response = self.catalog_request(
                origin,
                f"/api/v1/task-requests/{request_record['id']}/response",
                payload,
            )

        self.assertEqual(unavailable_response.status, 404)
        self.assertEqual(
            json.loads(unavailable_response.body)["error"]["code"],
            "mutation_unavailable",
        )

    def test_app_server_failure_does_not_suppress_file_backed_health(self) -> None:
        compatibility = self.static_dir / "fake-malformed-compatibility.json"
        write_contract(compatibility)
        command = (
            sys.executable,
            str(FAKE_APP_SERVER),
            "--mode",
            "malformed",
        )
        with running_server(
            self.static_dir,
            codex_command=command,
            codex_compatibility_path=compatibility,
        ) as origin:
            health = json.loads(response(f"{origin}/api/v1/health").body)
            projects = response(f"{origin}/api/v1/projects")

        self.assertEqual(health["data"]["integrations"]["codex_app_server"]["status"], "unavailable")
        self.assertEqual(health["data"]["integrations"]["project_sources"]["status"], "available")
        self.assertEqual(projects.status, 200)

    def test_index_injects_nonce_and_spa_fallback(self) -> None:
        with running_server(self.static_dir) as origin:
            root = response(f"{origin}/")
            root_body = root.body.decode()
            nested = response(f"{origin}/trackers/example")
            nested_body = nested.body.decode()

        self.assertEqual(root.status, 200)
        self.assertIn('content="test-launch-nonce"', root_body)
        self.assertEqual(root_body, nested_body)
        self.assertEqual(root.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", root.headers["Content-Security-Policy"])

    def test_asset_cache_and_traversal_rejection(self) -> None:
        with running_server(self.static_dir) as origin:
            asset = response(f"{origin}/assets/app-a1b2c3.js")
            traversal = response(f"{origin}/%2e%2e/secret.txt")

        self.assertEqual(asset.status, 200)
        self.assertIn("immutable", asset.headers["Cache-Control"])
        self.assertEqual(traversal.status, 400)

    def test_mutations_require_same_origin_and_launch_nonce(self) -> None:
        with running_server(self.static_dir) as origin:
            wrong_origin = response(
                Request(
                    f"{origin}/api/v1/future",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Origin": "https://example.com",
                        "X-Software-Factory-Nonce": "test-launch-nonce",
                    },
                )
            )
            wrong_nonce = response(
                Request(
                    f"{origin}/api/v1/future",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Origin": origin,
                        "X-Software-Factory-Nonce": "wrong",
                    },
                )
            )
            valid_guard = response(
                Request(
                    f"{origin}/api/v1/future",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Origin": origin,
                        "X-Software-Factory-Nonce": "test-launch-nonce",
                    },
                )
            )

        self.assertEqual(wrong_origin.status, 403)
        self.assertEqual(json.loads(wrong_origin.body)["error"]["code"], "origin_rejected")
        self.assertEqual(wrong_nonce.status, 403)
        self.assertEqual(json.loads(wrong_nonce.body)["error"]["code"], "nonce_rejected")
        self.assertEqual(valid_guard.status, 404)
        self.assertEqual(json.loads(valid_guard.body)["error"]["code"], "mutation_unavailable")

    def test_api_unknown_is_json_not_spa(self) -> None:
        with running_server(self.static_dir) as origin:
            missing = response(f"{origin}/api/v1/missing")
            payload = json.loads(missing.body)

        self.assertEqual(missing.status, 404)
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", payload["fingerprint"]))

    def test_catalog_api_registers_three_archives_restores_and_rejects_stale_truth(self) -> None:
        roots = [self.make_repo(name) for name in ("alpha", "beta", "gamma")]
        with running_server(self.static_dir) as origin:
            initial = response(f"{origin}/api/v1/projects?include_archived=true")
            initial_payload = json.loads(initial.body)
            fingerprint = initial_payload["data"]["catalog_fingerprint"]

            for name, root in zip(("alpha", "beta", "gamma"), roots, strict=True):
                created = self.catalog_request(
                    origin,
                    "/api/v1/projects",
                    {
                        "source_fingerprint": fingerprint,
                        "project": {
                            "id": name,
                            "label": name.title(),
                            "root": str(root),
                            "tracker_patterns": [],
                            "description": None,
                        },
                    },
                )
                self.assertEqual(created.status, 201)
                created_payload = json.loads(created.body)
                fingerprint = created_payload["data"]["catalog_fingerprint"]

            detail = json.loads(response(f"{origin}/api/v1/projects/alpha").body)
            self.assertEqual(detail["data"]["project"]["id"], "alpha")
            self.assertEqual(detail["data"]["project"]["discovery"]["git"]["status"], "available")

            archived = self.catalog_request(
                origin,
                "/api/v1/projects/beta",
                {
                    "source_fingerprint": fingerprint,
                    "action": "archive",
                    "confirmation": "archive:beta",
                },
                method="PATCH",
            )
            self.assertEqual(archived.status, 200)
            fingerprint = json.loads(archived.body)["data"]["catalog_fingerprint"]
            visible = json.loads(response(f"{origin}/api/v1/projects").body)
            self.assertEqual([project["id"] for project in visible["data"]["projects"]], ["alpha", "gamma"])

            restored = self.catalog_request(
                origin,
                "/api/v1/projects/beta",
                {"source_fingerprint": fingerprint, "action": "unarchive"},
                method="PATCH",
            )
            self.assertEqual(restored.status, 200)
            restored_payload = json.loads(restored.body)
            all_projects = restored_payload["data"]["projects"]
            self.assertEqual([project["id"] for project in all_projects], ["alpha", "beta", "gamma"])

            updated = self.catalog_request(
                origin,
                "/api/v1/projects/alpha",
                {
                    "source_fingerprint": restored_payload["data"]["catalog_fingerprint"],
                    "action": "update_presentation",
                    "changes": {"label": "Alpha Project", "description": "Display metadata."},
                },
                method="PATCH",
            )
            self.assertEqual(updated.status, 200)
            updated_payload = json.loads(updated.body)
            self.assertEqual(updated_payload["data"]["projects"][0]["label"], "Alpha Project")

            stale = self.catalog_request(
                origin,
                "/api/v1/projects/alpha",
                {
                    "source_fingerprint": initial_payload["data"]["catalog_fingerprint"],
                    "action": "update_presentation",
                    "changes": {"label": "Stale"},
                },
                method="PATCH",
            )
            self.assertEqual(stale.status, 409)
            self.assertEqual(json.loads(stale.body)["error"]["code"], "stale_catalog_fingerprint")

            copied_truth = self.catalog_request(
                origin,
                "/api/v1/projects",
                {
                    "source_fingerprint": updated_payload["data"]["catalog_fingerprint"],
                    "project": {
                        "id": "truth-copy",
                        "label": "Truth copy",
                        "root": str(roots[0]),
                        "tracker_patterns": [],
                        "description": None,
                        "status": "running",
                    },
                },
            )
            self.assertEqual(copied_truth.status, 400)
            self.assertEqual(json.loads(copied_truth.body)["error"]["code"], "unsupported_catalog_field")

            invalid_fingerprint = self.catalog_request(
                origin,
                "/api/v1/projects/alpha",
                {
                    "source_fingerprint": 42,
                    "action": "update_presentation",
                    "changes": {"label": "Invalid fingerprint"},
                },
                method="PATCH",
            )
            self.assertEqual(invalid_fingerprint.status, 400)
            self.assertEqual(
                json.loads(invalid_fingerprint.body)["error"]["code"],
                "invalid_catalog_fingerprint",
            )

    def test_tracker_list_and_detail_match_registered_file_git_and_maintained_verifier(self) -> None:
        root = self.make_repo("tracker-api")
        tracker_path = root / "docs" / "demo-implementation-tracker.md"
        tracker_path.parent.mkdir()
        tracker_path.write_text(FULL_TRACKER, encoding="utf-8")
        malformed_path = root / "docs" / "malformed-implementation-tracker.md"
        malformed_path.write_text("# Malformed tracker\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "trackers"], check=True)
        expected_head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        expected_content_sha = sha256(tracker_path.read_bytes()).hexdigest()

        with running_server(self.static_dir) as origin:
            initial = json.loads(response(f"{origin}/api/v1/projects?include_archived=true").body)
            created = self.catalog_request(
                origin,
                "/api/v1/projects",
                {
                    "source_fingerprint": initial["data"]["catalog_fingerprint"],
                    "project": {
                        "id": "tracker-api",
                        "label": "Tracker API",
                        "root": str(root),
                        "tracker_patterns": [],
                        "description": None,
                    },
                },
            )
            self.assertEqual(created.status, 201)

            listed_response = response(f"{origin}/api/v1/trackers")
            listed = json.loads(listed_response.body)
            self.assertEqual(listed_response.status, 200)
            self.assertEqual(len(listed["data"]["trackers"]), 2)
            summaries = {
                tracker["relative_path"]: tracker for tracker in listed["data"]["trackers"]
            }
            healthy = summaries["docs/demo-implementation-tracker.md"]
            malformed = summaries["docs/malformed-implementation-tracker.md"]
            self.assertTrue(healthy["verifier"]["valid"])
            self.assertFalse(malformed["verifier"]["valid"])
            self.assertTrue(malformed["verifier"]["errors"])
            self.assertEqual(healthy["raw_file"]["content_sha256"], expected_content_sha)
            self.assertEqual(healthy["git"]["repository_head"], expected_head)
            self.assertTrue(healthy["git"]["content_matches_head"])
            self.assertIsNone(healthy["git"]["diff"]["preview"])
            self.assertEqual(healthy["progress_posture"], "current")

            detail_response = response(f"{origin}/api/v1/trackers/{healthy['id']}")
            detail_payload = json.loads(detail_response.body)
            self.assertEqual(detail_response.status, 200)
            detail = detail_payload["data"]["tracker"]
            self.assertEqual(detail["raw_file"]["path"], str(tracker_path))
            self.assertEqual(detail["counts"]["by_status"], {"accepted": 1, "not-started": 1})
            self.assertEqual(detail["eligible_blocks"], [1])
            self.assertFalse(detail["git"]["diff"]["changed"])
            self.assertIsNone(detail["git"]["diff"]["preview"])
            self.assertIn("unrecognized operator note", {
                section["normalized_title"]
                for section in detail["blocks"][0]["sections"]
            })
            objective = next(
                section
                for section in detail["blocks"][0]["sections"]
                if section["normalized_title"] == "objective"
            )
            self.assertIn("Project exact tracker state", objective["markdown_preview"])

            raw_source = response(f"{origin}/api/v1/trackers/{healthy['id']}/source")
            self.assertEqual(raw_source.status, 200)
            self.assertEqual(raw_source.body, tracker_path.read_bytes())
            self.assertEqual(raw_source.headers["Content-Type"], "text/markdown; charset=utf-8")
            ranged_source = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source"
                f"?line={objective['line']}&end_line={objective['end_line']}"
            )
            self.assertEqual(ranged_source.status, 200)
            self.assertIn(b"### Objective", ranged_source.body)
            self.assertIn(b"Project exact tracker state", ranged_source.body)
            exact_head_source = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source"
                f"?line={objective['line']}&end_line={objective['end_line']}"
                f"&revision={expected_head}"
            )
            self.assertEqual(exact_head_source.status, 200)
            self.assertEqual(exact_head_source.body, ranged_source.body)
            exact_working_source = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source"
                f"?line={objective['line']}&end_line={objective['end_line']}"
                f"&content_sha256={expected_content_sha}"
            )
            self.assertEqual(exact_working_source.status, 200)
            stale_working_source = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source"
                f"?line={objective['line']}&end_line={objective['end_line']}"
                f"&content_sha256={'0' * 64}"
            )
            self.assertEqual(stale_working_source.status, 409)
            self.assertEqual(json.loads(stale_working_source.body)["error"]["code"], "tracker_source_changed")
            diff_response = response(f"{origin}/api/v1/trackers/{healthy['id']}/diff")
            self.assertEqual(diff_response.status, 200)
            diff_payload = json.loads(diff_response.body)
            self.assertEqual(diff_payload["data"]["tracker_id"], healthy["id"])
            self.assertEqual(diff_payload["data"]["content_sha256"], expected_content_sha)
            self.assertEqual(diff_payload["data"]["repository_head"], expected_head)
            self.assertFalse(diff_payload["data"]["diff"]["changed"])
            self.assertEqual(diff_payload["data"]["diff"]["preview"], "")
            self.assertEqual(diff_payload["data"]["relative_path"], "docs/demo-implementation-tracker.md")
            self.assertEqual(diff_payload["data"]["diff"]["semantic"]["rows"], [])
            self.assertTrue(diff_payload["data"]["diff"]["semantic"]["complete"])
            self.assertFalse(diff_payload["data"]["diff"]["semantic"]["changed"])
            invalid_range = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source?line=0&end_line=2"
            )
            self.assertEqual(invalid_range.status, 400)
            self.assertEqual(json.loads(invalid_range.body)["error"]["code"], "invalid_source_range")
            invalid_identity = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source"
                f"?revision={expected_head}&content_sha256={expected_content_sha}"
            )
            self.assertEqual(invalid_identity.status, 400)
            self.assertEqual(json.loads(invalid_identity.body)["error"]["code"], "invalid_source_identity")
            unavailable_revision = response(
                f"{origin}/api/v1/trackers/{healthy['id']}/source?revision={'0' * 40}"
            )
            self.assertEqual(unavailable_revision.status, 404)
            self.assertEqual(
                json.loads(unavailable_revision.body)["error"]["code"],
                "tracker_source_revision_unavailable",
            )

            verifier = detail["verifier"]
            direct = subprocess.run(
                verifier["command"],
                check=False,
                capture_output=True,
                text=True,
            )
            direct_payload = json.loads(direct.stdout)
            self.assertEqual(direct.returncode, verifier["exit_status"])
            self.assertEqual(direct_payload["blocks"], verifier["blocks"])
            self.assertEqual(direct_payload["errors"], verifier["errors"])
            self.assertEqual(direct_payload["warnings"], verifier["warnings"])
            self.assertRegex(verifier["owner"]["owning_revision"], r"^[0-9a-f]{40}$")

            invalid_id = response(f"{origin}/api/v1/trackers/not-a-tracker")
            self.assertEqual(invalid_id.status, 400)
            self.assertEqual(json.loads(invalid_id.body)["error"]["code"], "invalid_tracker_id")
            invalid_source_id = response(f"{origin}/api/v1/trackers/not-a-tracker/source")
            self.assertEqual(invalid_source_id.status, 400)
            self.assertEqual(json.loads(invalid_source_id.body)["error"]["code"], "invalid_tracker_id")
            invalid_diff_id = response(f"{origin}/api/v1/trackers/not-a-tracker/diff")
            self.assertEqual(invalid_diff_id.status, 400)
            self.assertEqual(json.loads(invalid_diff_id.body)["error"]["code"], "invalid_tracker_id")

    def test_run_report_and_metric_apis_use_live_supervision_owner(self) -> None:
        root = self.make_repo("operations-api")
        supervision_root = self.static_dir / "supervision"
        automations_root = self.static_dir / "automations"
        target = "operations-target-0001"
        init = subprocess.run(
            [
                sys.executable,
                str(DEFAULT_SUPERVISION_OWNER),
                "--root",
                str(supervision_root),
                "init",
                "--target-thread",
                target,
                "--target-label",
                "Operations target",
                "--watcher-thread",
                "operations-watcher-01",
                "--reviewer-thread",
                "operations-reviewer-1",
                "--mission-root",
                "c" * 64,
                "--mission-source-record",
                "direct-item-44",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout)
        recorded = subprocess.run(
            [
                sys.executable,
                str(DEFAULT_SUPERVISION_OWNER),
                "--root",
                str(supervision_root),
                "record",
                "--target-thread",
                target,
                "--kind",
                "check",
                "--model",
                "gpt-5.6-terra",
                "--reasoning",
                "max",
                "--status",
                "no-intervention",
                "--category",
                "changed-state-review",
                "--summary",
                "Exact live owner check.",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(recorded.returncode, 0, recorded.stdout)

        with running_server(
            self.static_dir,
            supervision_root=supervision_root,
            automations_root=automations_root,
        ) as origin:
            initial = json.loads(response(f"{origin}/api/v1/projects?include_archived=true").body)
            created = self.catalog_request(
                origin,
                "/api/v1/projects",
                {
                    "source_fingerprint": initial["data"]["catalog_fingerprint"],
                    "project": {
                        "id": "operations-api",
                        "label": "Operations API",
                        "root": str(root),
                        "tracker_patterns": [],
                        "description": None,
                    },
                },
            )
            self.assertEqual(created.status, 201)

            listed = json.loads(response(f"{origin}/api/v1/runs").body)
            detail = json.loads(response(f"{origin}/api/v1/runs/{target}").body)
            reports = json.loads(response(f"{origin}/api/v1/reports").body)
            metrics = json.loads(response(f"{origin}/api/v1/metrics").body)
            missing = response(f"{origin}/api/v1/runs/missing-target-0000")

        self.assertEqual(len(listed["data"]["runs"]), 1)
        self.assertEqual(listed["data"]["runs"][0]["current_event_count"], 1)
        self.assertEqual(detail["data"]["run"]["target_thread_id"], target)
        self.assertEqual(detail["data"]["run"]["metrics"]["status"], "available")
        self.assertEqual(reports["data"]["reports"], [])
        self.assertEqual(metrics["data"]["aggregate"]["status"], "available")
        self.assertEqual(metrics["data"]["aggregate"]["contract_count"], 1)
        self.assertEqual(metrics["data"]["aggregate"]["headline"]["recorded_events"], 1)
        self.assertEqual(
            metrics["data"]["aggregate"]["api_equivalent_estimate"]["label"],
            "API-equivalent estimate",
        )
        self.assertEqual(metrics["data"]["per_run"][0]["status"], "available")
        self.assertEqual(
            metrics["data"]["per_run"][0]["target_label"],
            "Operations target",
        )
        self.assertFalse(
            metrics["data"]["factory_history"]["availability"][
                "continuous_uptime_measured"
            ]
        )
        self.assertEqual(
            metrics["data"]["per_run"][0]["cost_label"],
            "API-equivalent estimate",
        )
        self.assertEqual(missing.status, 404)
        self.assertEqual(json.loads(missing.body)["error"]["code"], "run_not_found")

    def test_report_detail_and_artifact_routes_remain_verified_and_same_origin(self) -> None:
        target = "report-target-0001"
        family = "weekly"
        report_id = "weekly-report-0001"
        member_name = "report.md"
        member_body = b"# Verified report\n"
        member = {
            "name": member_name,
            "path": "/source/report.md",
            "media_type": "text/markdown",
            "bytes": len(member_body),
            "sha256": sha256(member_body).hexdigest(),
            "read_only": True,
        }
        report = {
            "id": report_id,
            "target_thread_id": target,
            "family": family,
            "stage": "verified",
            "status": "available",
            "source_root": "1" * 64,
            "manifest_root": "2" * 64,
            "disposition": "effective-with-findings",
            "coverage": None,
            "review_summary": None,
            "verification": {"valid": True},
            "members": [member],
            "limitations": [],
            "error": None,
            "metric_summary": None,
        }
        owners = OperationsProjectionService().owner_revisions()
        projected = {
            "fingerprint": "3" * 64,
            "owners": owners,
            "selected_report": report,
            "coverage": {"status": "partial", "observed": ["reports"], "missing": []},
            "limitations": [],
        }

        with (
            patch.object(OperationsProjectionService, "report", return_value=projected),
            patch.object(
                OperationsProjectionService,
                "report_member",
                return_value=(member_body, member),
            ),
            running_server(self.static_dir) as origin,
        ):
            detail_response = response(
                f"{origin}/api/v1/reports/{target}/{family}/{report_id}"
            )
            detail = json.loads(detail_response.body)
            inline = response(
                f"{origin}/api/v1/reports/{target}/{family}/{report_id}/artifacts/{member_name}"
            )
            download = response(
                f"{origin}/api/v1/reports/{target}/{family}/{report_id}/artifacts/{member_name}?download=true"
            )
            invalid = response(
                f"{origin}/api/v1/reports/{target}/{family}/{report_id}/artifacts/{member_name}?raw=true"
            )

        self.assertEqual(detail_response.status, 200)
        artifact = detail["data"]["report"]["artifacts"][0]
        self.assertTrue(artifact["previewable"])
        self.assertTrue(artifact["preview_url"].startswith("/api/v1/reports/"))
        self.assertTrue(artifact["download_url"].endswith("?download=true"))
        self.assertEqual(inline.body, member_body)
        self.assertEqual(inline.headers["Content-Disposition"], 'inline; filename="report.md"')
        self.assertEqual(download.headers["Content-Disposition"], 'attachment; filename="report.md"')
        self.assertEqual(json.loads(invalid.body)["error"]["code"], "invalid_query")

    def test_each_verified_report_family_uses_the_same_bounded_artifact_route(self) -> None:
        target = "report-target-0002"
        owners = OperationsProjectionService().owner_revisions()
        cases = (
            ("weekly", "verified", "report.md", "text/markdown", b"# Weekly\n"),
            ("terminal", "verified", "full.pdf", "application/pdf", b"%PDF-test"),
            (
                "factory-evolution",
                "evaluated",
                "evaluation.json",
                "application/json",
                b'{"disposition":"retain"}',
            ),
        )
        for family, stage, member_name, media_type, member_body in cases:
            with self.subTest(family=family):
                report_id = f"{family}-report-0001"
                member = {
                    "name": member_name,
                    "path": f"/source/{member_name}",
                    "media_type": media_type,
                    "bytes": len(member_body),
                    "sha256": sha256(member_body).hexdigest(),
                    "read_only": True,
                }
                report = {
                    "id": report_id,
                    "target_thread_id": target,
                    "family": family,
                    "stage": stage,
                    "status": "available",
                    "source_root": "1" * 64,
                    "manifest_root": "2" * 64,
                    "disposition": "retain",
                    "coverage": None,
                    "review_summary": None,
                    "verification": {"valid": True},
                    "members": [member],
                    "limitations": [],
                    "error": None,
                    "metric_summary": None,
                }
                projected = {
                    "fingerprint": "3" * 64,
                    "owners": owners,
                    "selected_report": report,
                    "coverage": {
                        "status": "partial",
                        "observed": ["reports"],
                        "missing": [],
                    },
                    "limitations": [],
                }
                with (
                    patch.object(
                        OperationsProjectionService,
                        "report",
                        return_value=projected,
                    ),
                    patch.object(
                        OperationsProjectionService,
                        "report_member",
                        return_value=(member_body, member),
                    ),
                    running_server(self.static_dir) as origin,
                ):
                    detail = json.loads(
                        response(
                            f"{origin}/api/v1/reports/{target}/{family}/{report_id}"
                        ).body
                    )
                    artifact = response(
                        f"{origin}/api/v1/reports/{target}/{family}/{report_id}"
                        f"/artifacts/{member_name}"
                    )

                self.assertEqual(
                    detail["data"]["report"]["artifacts"][0]["preview_url"],
                    f"/api/v1/reports/{target}/{family}/{report_id}"
                    f"/artifacts/{member_name}",
                )
                self.assertEqual(artifact.body, member_body)


if __name__ == "__main__":
    unittest.main()
