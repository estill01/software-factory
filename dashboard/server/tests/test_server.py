from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest

from software_factory_dashboard.server import (
    DashboardConfigurationError,
    NONCE_PLACEHOLDER,
    ServerConfig,
    create_server,
)


@contextmanager
def running_server(static_dir: Path) -> Iterator[str]:
    server = create_server(
        ServerConfig(host="127.0.0.1", port=0, static_dir=static_dir, quiet=True),
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


if __name__ == "__main__":
    unittest.main()
