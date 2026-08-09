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

from test_tracker import FULL_TRACKER

from software_factory_dashboard.server import (
    DashboardConfigurationError,
    NONCE_PLACEHOLDER,
    ServerConfig,
    create_server,
)
from software_factory_dashboard.operations import DEFAULT_SUPERVISION_OWNER


@contextmanager
def running_server(
    static_dir: Path,
    *,
    catalog_path: Path | None = None,
    supervision_root: Path | None = None,
    automations_root: Path | None = None,
) -> Iterator[str]:
    server = create_server(
        ServerConfig(
            host="127.0.0.1",
            port=0,
            static_dir=static_dir,
            catalog_path=catalog_path or static_dir / ".catalog" / "projects.json",
            supervision_root=supervision_root or static_dir / ".supervision",
            automations_root=automations_root or static_dir / ".automations",
            quiet=True,
        ),
        nonce="test-launch-nonce",
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
            self.assertEqual(healthy["progress_posture"], "current")

            detail_response = response(f"{origin}/api/v1/trackers/{healthy['id']}")
            detail_payload = json.loads(detail_response.body)
            self.assertEqual(detail_response.status, 200)
            detail = detail_payload["data"]["tracker"]
            self.assertEqual(detail["raw_file"]["path"], str(tracker_path))
            self.assertEqual(detail["counts"]["by_status"], {"accepted": 1, "not-started": 1})
            self.assertEqual(detail["eligible_blocks"], [1])
            self.assertIn("unrecognized operator note", {
                section["normalized_title"]
                for section in detail["blocks"][0]["sections"]
            })

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
        self.assertEqual(metrics["data"]["aggregate"]["headline"]["recorded_events"], 1)
        self.assertEqual(
            metrics["data"]["aggregate"]["api_equivalent_estimate"]["label"],
            "API-equivalent estimate",
        )
        self.assertEqual(metrics["data"]["per_run"][0]["status"], "available")
        self.assertEqual(
            metrics["data"]["per_run"][0]["cost_label"],
            "API-equivalent estimate",
        )
        self.assertEqual(missing.status, 404)
        self.assertEqual(json.loads(missing.body)["error"]["code"], "run_not_found")


if __name__ == "__main__":
    unittest.main()
