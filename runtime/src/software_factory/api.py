from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .advanced import AdvancedServices
from .errors import InvalidTransition, StoreError
from .reporting import ReportingService
from .store import Store
from .util import utc_now

_FACTORY_FLOOR_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Software Factory v2</title>
<style>
:root{font-family:ui-sans-serif,system-ui,sans-serif;color-scheme:dark;background:#101214;color:#edf1f5}
body{margin:0;padding:24px}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.card{background:#181c20;border:1px solid #30363d;border-radius:10px;padding:14px}
h1,h2{margin:0 0 10px}h1{font-size:22px}h2{font-size:15px;color:#a9c7ff}pre{white-space:pre-wrap;word-break:break-word;font-size:12px;margin:0}
.badge{padding:4px 8px;border-radius:999px;background:#263445;font-size:12px}button{background:#2f81f7;color:white;border:0;border-radius:7px;padding:8px 12px;cursor:pointer}
</style></head><body><header><div><h1>Software Factory v2</h1><div id="status" class="badge">loading</div></div><button onclick="refresh()">Refresh</button></header>
<div class="grid" id="grid"></div><script>
async function refresh(){const health=await fetch('/health').then(r=>r.json());document.getElementById('status').textContent=health.ok?'healthy':'degraded';
const data=await fetch('/api/factory-floor').then(r=>r.json());const grid=document.getElementById('grid');grid.innerHTML='';
for(const [name,value] of Object.entries(data)){const card=document.createElement('section');card.className='card';card.innerHTML=`<h2>${name.replaceAll('_',' ')}</h2><pre>${JSON.stringify(value,null,2)}</pre>`;grid.appendChild(card)}}refresh();setInterval(refresh,15000);
</script></body></html>"""


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


class FactoryAPI:
    def __init__(self, store: Store, advanced: AdvancedServices | None = None):
        self.store = store
        self.advanced = advanced or AdvancedServices(store)
        self.reporting = ReportingService(store)

    def health(self) -> dict[str, Any]:
        try:
            integrity = self.store.one("PRAGMA integrity_check")
            schema = self.store.all(
                "SELECT version,name FROM schema_migrations ORDER BY version"
            )
            ok = bool(integrity) and list(integrity.values())[0] == "ok"
        except BaseException as exc:
            return {"ok": False, "error": str(exc), "checked_at": utc_now()}
        return {
            "ok": ok,
            "integrity": list(integrity.values())[0],
            "schema_version": schema[-1]["version"] if schema else 0,
            "checked_at": utc_now(),
        }

    def factory_floor(self, mission_id: str | None = None) -> dict[str, Any]:
        mission_filter = " WHERE mission_id=?" if mission_id else ""
        parameters = (mission_id,) if mission_id else ()
        missions = self.store.all(
            "SELECT id,status,goal,created_at,updated_at FROM missions ORDER BY created_at DESC LIMIT 100"
        )
        work = self.store.all(
            """SELECT id,mission_id,title,work_type,planning_status,execution_status,
                      qa_status,acceptance_status,priority,updated_at
               FROM work_items"""
            + mission_filter
            + " ORDER BY priority DESC,updated_at DESC LIMIT 250",
            parameters,
        )
        agents = self.store.all(
            """SELECT id,provider,provider_session_id,intended_role,observed_status,
                      current_assignment_id,last_heartbeat_at,updated_at
               FROM agent_sessions ORDER BY updated_at DESC LIMIT 250"""
        )
        executions = self.store.all(
            """SELECT id,mission_id,work_item_id,agent_session_id,status,provider_key,
                      attempt_number,lease_generation,started_at,completed_at
               FROM executions"""
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 250",
            parameters,
        )
        incidents = self.store.all(
            "SELECT * FROM supervision_incidents"
            + mission_filter
            + " ORDER BY opened_at DESC LIMIT 250",
            parameters,
        )
        signals = self.store.all(
            "SELECT * FROM active_signal_bundles"
            + mission_filter
            + " ORDER BY activated_at DESC LIMIT 100",
            parameters,
        )
        reflections = self.store.all(
            "SELECT * FROM reflections_v2"
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 100",
            parameters,
        )
        experiments = self.store.all(
            "SELECT * FROM experiments_v2"
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 100",
            parameters,
        )
        releases = self.store.all(
            "SELECT * FROM immutable_releases_v2 ORDER BY staged_at DESC LIMIT 50"
        )
        recoveries = self.store.all(
            "SELECT * FROM factory_recovery_cases_v2 ORDER BY opened_at DESC LIMIT 50"
        )
        cleanups = self.store.all(
            """SELECT ci.*,ri.repository_root FROM cleanup_items_v2 ci
               JOIN repository_inventories_v2 ri ON ri.id=ci.inventory_id
               ORDER BY ci.created_at DESC LIMIT 100"""
        )
        return {
            "missions": missions,
            "work": work,
            "agents": agents,
            "executions": executions,
            "incidents": incidents,
            "signals": signals,
            "reflections": reflections,
            "experiments": experiments,
            "releases": releases,
            "recoveries": recoveries,
            "cleanup": cleanups,
        }

    def mission_detail(self, mission_id: str) -> dict[str, Any]:
        mission = self.store.one(
            "SELECT * FROM missions WHERE id=?", (mission_id,), required=False
        )
        if mission is None:
            raise StoreError("mission not found")
        floor = self.factory_floor(mission_id)
        floor["mission"] = mission
        floor["adaptive_cases"] = self.store.all(
            """SELECT * FROM retained_adaptive_cases
               WHERE mission_id=? ORDER BY created_at DESC LIMIT 250""",
            (mission_id,),
        )
        floor["selection_records"] = self.store.all(
            """SELECT * FROM selection_records_v2
               WHERE mission_id=? ORDER BY created_at DESC LIMIT 250""",
            (mission_id,),
        )
        return floor

    def apply_operator_action(
        self,
        raw_token: str,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        action = str(request.get("action", ""))
        target_type = str(request.get("target_type", ""))
        target_id = str(request.get("target_id", ""))
        payload = request.get("payload", {})
        if not isinstance(payload, Mapping):
            raise ValueError("operator payload must be an object")
        decision = self.reporting.accept_operator_action(
            raw_token,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
        )

        def handler(record: Mapping[str, Any]) -> Mapping[str, Any]:
            action_name = str(record["action"])
            target = str(record["target_id"])
            if action_name == "pause_schedule":
                with self.store.transaction() as db:
                    db.execute(
                        "UPDATE schedules_v2 SET status='paused',updated_at=? WHERE id=?",
                        (utc_now(), target),
                    )
                    if db.execute("SELECT changes()").fetchone()[0] != 1:
                        raise StoreError("schedule not found")
                return {"paused": target}
            if action_name == "resume_schedule":
                with self.store.transaction() as db:
                    db.execute(
                        "UPDATE schedules_v2 SET status='active',updated_at=? WHERE id=?",
                        (utc_now(), target),
                    )
                    if db.execute("SELECT changes()").fetchone()[0] != 1:
                        raise StoreError("schedule not found")
                return {"resumed": target}
            if action_name == "cancel_work":
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE work_items
                           SET execution_status='cancelled',updated_at=? WHERE id=?""",
                        (utc_now(), target),
                    )
                    if db.execute("SELECT changes()").fetchone()[0] != 1:
                        raise StoreError("work item not found")
                return {"cancelled": target}
            if action_name == "acknowledge_incident":
                with self.store.transaction() as db:
                    db.execute(
                        """UPDATE supervision_incidents
                           SET status='accepted_risk',updated_at=? WHERE id=?""",
                        (utc_now(), target),
                    )
                    if db.execute("SELECT changes()").fetchone()[0] != 1:
                        raise StoreError("incident not found")
                return {"acknowledged": target}
            raise InvalidTransition(f"operator action has no governed owner: {action_name}")

        return self.reporting.apply_operator_decision(decision["id"], handler=handler)


def make_handler(api: FactoryAPI) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "SoftwareFactoryV2/2"

        def _json(self, status: int, payload: Mapping[str, Any]) -> None:
            content = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _body(self) -> Mapping[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1024 * 1024:
                raise ValueError("request body exceeds one megabyte")
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, Mapping):
                raise ValueError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    content = _FACTORY_FLOOR_HTML.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if parsed.path == "/health":
                    self._json(HTTPStatus.OK, api.health())
                    return
                if parsed.path == "/api/factory-floor":
                    mission_id = query.get("mission_id", [None])[0]
                    self._json(HTTPStatus.OK, api.factory_floor(mission_id))
                    return
                if parsed.path.startswith("/api/missions/"):
                    mission_id = parsed.path.removeprefix("/api/missions/")
                    self._json(HTTPStatus.OK, api.mission_detail(mission_id))
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            except StoreError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except BaseException as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                if self.path != "/api/operator-actions":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                authorization = self.headers.get("Authorization", "")
                if not authorization.startswith("Bearer "):
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "bearer token required"})
                    return
                result = api.apply_operator_action(
                    authorization.removeprefix("Bearer ").strip(), self._body()
                )
                self._json(HTTPStatus.OK, result)
            except (StoreError, InvalidTransition, ValueError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except BaseException as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


class APIServer:
    def __init__(
        self,
        api: FactoryAPI,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
    ):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("reference API binds only to loopback")
        self.httpd = ThreadingHTTPServer((host, port), make_handler(api))
        self.thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.httpd.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
            self.thread = None
