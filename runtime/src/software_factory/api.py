from __future__ import annotations

import json
import secrets
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .advanced import AdvancedServices
from .errors import InvalidTransition, StoreError
from .hosts.service import StandaloneFactoryService
from .reporting import ReportingService
from .store import Store
from .util import utc_now
from .utility_contracts import (
    SERVICE_ENGINE_OPERATIONS,
    SERVICE_MAX_REQUEST_BYTES,
    SERVICE_MAX_REQUEST_TARGET_BYTES,
    SERVICE_MAX_RESPONSE_BYTES,
    QualifiedUtilityRuntime,
    RuntimeIdentity,
    service_api_protocol_root,
)

_FACTORY_FLOOR_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Software Factory v2</title>
<style>
:root{font-family:ui-sans-serif,system-ui,sans-serif;color-scheme:dark;background:#101214;color:#edf1f5}
body{margin:0;padding:24px}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.card{background:#181c20;border:1px solid #30363d;border-radius:10px;padding:14px}
h1,h2{margin:0 0 10px}h1{font-size:22px}h2{font-size:15px;color:#a9c7ff}pre{white-space:pre-wrap;word-break:break-word;font-size:12px;margin:0}
.badge{padding:4px 8px;border-radius:999px;background:#263445;font-size:12px}.controls{display:flex;gap:8px}input{background:#101214;color:#edf1f5;border:1px solid #30363d;border-radius:7px;padding:8px}button{background:#2f81f7;color:white;border:0;border-radius:7px;padding:8px 12px;cursor:pointer}
</style></head><body><header><div><h1>Software Factory v2</h1><div id="status" class="badge">disconnected</div></div><div class="controls"><input id="token" type="password" autocomplete="off" placeholder="Service token"><button id="connect">Connect</button><button id="refresh">Refresh</button></div></header>
<div class="grid" id="grid"></div><script>
let serviceToken='';
function setText(node,value){node.textContent=value}
async function refresh(){const status=document.getElementById('status');const health=await fetch('/health',{cache:'no-store'}).then(r=>r.json());if(!health.ok){setText(status,'degraded');return}if(!serviceToken){setText(status,'token required');return}
const response=await fetch('/api/factory-floor',{headers:{Authorization:`Bearer ${serviceToken}`},cache:'no-store'});if(!response.ok){setText(status,response.status===401?'unauthorized':'degraded');return}setText(status,'ready');const data=await response.json();const grid=document.getElementById('grid');grid.replaceChildren();
for(const [name,value] of Object.entries(data)){const card=document.createElement('section');card.className='card';const heading=document.createElement('h2');setText(heading,name.replaceAll('_',' '));const body=document.createElement('pre');setText(body,JSON.stringify(value,null,2));card.append(heading,body);grid.appendChild(card)}}
document.getElementById('connect').addEventListener('click',()=>{const input=document.getElementById('token');serviceToken=input.value;input.value='';refresh()});document.getElementById('refresh').addEventListener('click',refresh);setInterval(refresh,15000);
</script></body></html>"""


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


class FactoryAPI:
    def __init__(
        self,
        store: Store,
        advanced: AdvancedServices | None = None,
        *,
        reporting: ReportingService | None = None,
        engine_service: StandaloneFactoryService | None = None,
        utility_runtime: QualifiedUtilityRuntime | None = None,
        runtime_identity: RuntimeIdentity | None = None,
    ):
        self.store = store
        self.advanced = advanced or AdvancedServices(store)
        self.reporting = reporting or ReportingService(store)
        self.engine_service = engine_service
        self.utility_runtime = utility_runtime
        self.runtime_identity = runtime_identity

    def apply_engine_operation(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if operation not in SERVICE_ENGINE_OPERATIONS:
            raise InvalidTransition("engine operation is not exposed by the service boundary")
        if self.engine_service is None:
            raise InvalidTransition("engine service is not configured for this host")
        try:
            return self.engine_service.invoke(operation, payload)
        except TypeError as exc:
            raise ValueError("engine request fields are invalid") from exc

    @staticmethod
    def liveness() -> dict[str, bool]:
        return {"ok": True}

    def health(self) -> dict[str, Any]:
        database_ok = False
        schema_version = 0
        try:
            integrity = self.store.one("PRAGMA integrity_check")
            schema = self.store.all("SELECT version,name FROM schema_migrations ORDER BY version")
            database_ok = bool(integrity) and list(integrity.values())[0] == "ok"
            schema_version = int(schema[-1]["version"]) if schema else 0
        except Exception:
            pass
        utilities_ok = self.utility_runtime is not None and self.runtime_identity is not None
        manifest_ok = False
        if utilities_ok:
            try:
                self.runtime_manifest_record()
                manifest_ok = True
            except Exception:
                pass
        ready = database_ok and self.engine_service is not None and utilities_ok and manifest_ok
        return {
            "ok": ready,
            "database": database_ok,
            "engine_service": self.engine_service is not None,
            "qualified_utilities": utilities_ok,
            "runtime_manifest": manifest_ok,
            "schema_version": schema_version,
            "checked_at": utc_now(),
        }

    def readiness(self) -> dict[str, bool]:
        return {"ok": bool(self.health()["ok"])}

    def runtime_manifest_record(self) -> dict[str, Any]:
        if self.utility_runtime is None or self.runtime_identity is None:
            raise InvalidTransition("qualified utility runtime is not configured")
        record = json.loads(self.utility_runtime.manifest_document(self.runtime_identity))
        if not isinstance(record, dict):
            raise StoreError("runtime manifest did not produce an object")
        return record

    def factory_floor(self, mission_id: str | None = None) -> dict[str, Any]:
        mission_filter = " WHERE mission_id=?" if mission_id else ""
        parameters = (mission_id,) if mission_id else ()
        missions = self.store.all(
            """SELECT id,status,title,created_at,updated_at
               FROM missions"""
            + (" WHERE id=?" if mission_id else "")
            + " ORDER BY created_at DESC LIMIT 100",
            parameters,
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
            """SELECT id,mission_id,provider,role,desired_status,observed_status,
                      last_heartbeat_at,started_at,stopped_at
               FROM agent_sessions"""
            + mission_filter
            + " ORDER BY started_at DESC LIMIT 250",
            parameters,
        )
        executions = self.store.all(
            """SELECT id,mission_id,work_item_id,agent_session_id,status,provider_key,
                      attempt_number,lease_generation,started_at,finished_at
               FROM executions"""
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 250",
            parameters,
        )
        incidents = self.store.all(
            """SELECT id,mission_id,target_type,target_id,severity,status,layer,mechanism,
                      failure_fingerprint,occurrence_count,created_at,updated_at
               FROM incidents"""
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 250",
            parameters,
        )
        signals = self.store.all(
            """SELECT id,mission_id,candidate_id,signal_kind,bundle_root,version,status,
                      activated_at,updated_at FROM active_signal_bundles"""
            + mission_filter
            + " ORDER BY activated_at DESC LIMIT 100",
            parameters,
        )
        legacy_reflections = self.store.all(
            """SELECT id,mission_id,reflection_type,source_type,source_id,prompt_root,
                      confidence,status,created_at FROM reflections_v2"""
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 100",
            parameters,
        )
        canonical_rows = self.store.all(
            """SELECT r.root AS id,b.mission_id,b.operational_subject_type AS source_type,
                      b.operational_subject_id AS source_id,b.currentness_root,b.created_at
               FROM librsi_record_bindings AS b
               JOIN librsi_records AS r ON r.root=b.librsi_root
               WHERE b.semantic_role='reflection_observation'"""
            + (" AND b.mission_id=?" if mission_id else "")
            + " ORDER BY b.created_at DESC LIMIT 100",
            parameters,
        )
        canonical_reflections = [
            {
                **row,
                "reflection_type": "canonical",
                "status": "advisory",
                "semantic_owner": "libRSI",
            }
            for row in canonical_rows
        ]
        reflections = sorted(
            [*canonical_reflections, *legacy_reflections],
            key=lambda row: str(row["created_at"]),
            reverse=True,
        )[:100]
        experiments = self.store.all(
            """SELECT id,mission_id,hypothesis_id,experiment_type,status,created_at,updated_at
               FROM experiments_v2"""
            + mission_filter
            + " ORDER BY created_at DESC LIMIT 100",
            parameters,
        )
        releases = self.store.all(
            """SELECT id,mission_id,source_revision,source_tree_root,manifest_root,
                      review_status,verification_status,status,previous_release_id,
                      staged_at,activated_at,deactivated_at,updated_at
               FROM immutable_releases_v2"""
            + mission_filter
            + " ORDER BY staged_at DESC LIMIT 50",
            parameters,
        )
        recoveries = self.store.all(
            """SELECT id,target_mission_id,defect_class,defect_fingerprint,
                      requested_range_root,tracker_currentness_root,repair_revision,
                      release_id,status,resume_count,opened_at,updated_at,resolved_at
               FROM factory_recovery_cases_v2"""
            + (" WHERE target_mission_id=?" if mission_id else "")
            + " ORDER BY opened_at DESC LIMIT 50",
            parameters,
        )
        cleanups = self.store.all(
            """SELECT ci.id,ci.inventory_id,ci.item_type,ci.classification,ci.disposition,
                      ci.status,ci.created_at,ci.updated_at
               FROM cleanup_items_v2 ci
               JOIN repository_inventories_v2 ri ON ri.id=ci.inventory_id
            """
            + (" WHERE ri.mission_id=?" if mission_id else "")
            + " ORDER BY ci.created_at DESC LIMIT 100",
            parameters,
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
            """SELECT id,project_id,title,status,autonomy_mode,state_version,
                      created_at,updated_at,completed_at
               FROM missions WHERE id=?""",
            (mission_id,),
            required=False,
        )
        if mission is None:
            raise StoreError("mission not found")
        floor = self.factory_floor(mission_id)
        floor["mission"] = mission
        floor["strategy_outcomes"] = self.store.all(
            """SELECT id,mission_id,work_item_id,execution_id,obligation_id,problem_key,
                      strategy_key,outcome,failure_fingerprint,evidence_root,created_at
               FROM strategy_outcomes
               WHERE mission_id=? ORDER BY created_at DESC LIMIT 250""",
            (mission_id,),
        )
        floor["selection_records"] = self.store.all(
            """SELECT id,mission_id,selection_group,selection_type,candidate_key,status,
                      selected_at,created_at,updated_at FROM selection_records_v2
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
            decision_payload = _loads(record.get("payload_json"), {})
            if not isinstance(decision_payload, Mapping):
                raise StoreError("operator decision payload is invalid")
            if action_name == "pause_schedule":
                self.reporting.set_schedule_status(
                    target,
                    status="paused",
                    operator_decision_id=str(record["id"]),
                )
                return {"paused": target}
            if action_name == "resume_schedule":
                self.reporting.set_schedule_status(
                    target,
                    status="active",
                    operator_decision_id=str(record["id"]),
                )
                return {"resumed": target}
            if action_name == "cancel_work":
                self.advanced.work_items.cancel_work(
                    target,
                    operator_decision_id=str(record["id"]),
                )
                return {"cancelled": target}
            if action_name == "cancel_mission":
                if self.engine_service is None:
                    raise InvalidTransition("engine service is not configured for this host")
                reason = str(decision_payload.get("reason", "operator cancellation")).strip()
                if not reason or len(reason) > 500:
                    raise ValueError("cancellation reason must contain at most 500 characters")
                return self.engine_service.invoke(
                    "cancel", {"mission_id": target, "reason": reason}
                )
            if action_name == "acknowledge_incident":
                self.advanced.supervision.acknowledge_incident(
                    target,
                    operator_decision_id=str(record["id"]),
                )
                return {"acknowledged": target}
            raise InvalidTransition(f"operator action has no governed owner: {action_name}")

        return self.reporting.apply_operator_decision(decision["id"], handler=handler)


def make_handler(api: FactoryAPI, service_token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "SoftwareFactoryV2/2"

        def _json(self, status: int, payload: Mapping[str, Any]) -> None:
            content = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            if len(content) > SERVICE_MAX_RESPONSE_BYTES:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                content = b'{"error":"response exceeds service limit"}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _body(self) -> Mapping[str, Any]:
            if self.headers.get("Transfer-Encoding") is not None:
                raise ValueError("transfer encoding is not supported")
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("content length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("content length must be an integer") from exc
            if length < 0 or length > SERVICE_MAX_REQUEST_BYTES:
                raise ValueError("request body exceeds one megabyte")
            if length and self.headers.get_content_type() != "application/json":
                raise ValueError("request body must use application/json")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("request body ended before content length")
            try:
                value = json.loads(raw or b"{}")
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("request body must be valid JSON") from exc
            if not isinstance(value, Mapping):
                raise ValueError("request body must be a JSON object")
            return value

        def _service_authorized(self) -> bool:
            authorization = self.headers.get("Authorization", "")
            if len(authorization) > 1024 or not authorization.startswith("Bearer "):
                return False
            return secrets.compare_digest(authorization[7:], service_token)

        def _require_service_auth(self) -> bool:
            if self._service_authorized():
                return True
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "service bearer token required"})
            return False

        def _require_current_workflow(self) -> bool:
            supplied = self.headers.get("X-Software-Factory-Workflow-Root", "")
            if len(supplied) == 64 and secrets.compare_digest(
                supplied, service_api_protocol_root()
            ):
                return True
            self._json(
                HTTPStatus.CONFLICT,
                {"error": "current workflow root required"},
            )
            return False

        @staticmethod
        def _known_error(exc: Exception) -> str:
            message = str(exc)
            return message[:500] if message else "request rejected"

        def do_GET(self) -> None:  # noqa: N802
            if len(self.path.encode("utf-8")) > SERVICE_MAX_REQUEST_TARGET_BYTES:
                self._json(HTTPStatus.REQUEST_URI_TOO_LONG, {"error": "request target too long"})
                return
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    content = _FACTORY_FLOOR_HTML.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if parsed.path == "/health":
                    self._json(HTTPStatus.OK, api.liveness())
                    return
                if parsed.path == "/ready":
                    readiness = api.readiness()
                    status = HTTPStatus.OK if readiness["ok"] else HTTPStatus.SERVICE_UNAVAILABLE
                    self._json(status, readiness)
                    return
                if not parsed.path.startswith("/api/"):
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                if not self._require_service_auth():
                    return
                query = parse_qs(parsed.query, max_num_fields=20)
                if parsed.path == "/api/health":
                    self._json(HTTPStatus.OK, api.health())
                    return
                if parsed.path == "/api/runtime-manifest":
                    self._json(HTTPStatus.OK, api.runtime_manifest_record())
                    return
                if parsed.path == "/api/factory-floor":
                    mission_id = query.get("mission_id", [None])[0]
                    if mission_id is not None and len(mission_id) > 256:
                        raise ValueError("mission id exceeds service limit")
                    self._json(HTTPStatus.OK, api.factory_floor(mission_id))
                    return
                if parsed.path.startswith("/api/missions/"):
                    mission_id = parsed.path.removeprefix("/api/missions/")
                    if not mission_id or "/" in mission_id or len(mission_id) > 256:
                        raise ValueError("mission id is invalid")
                    self._json(HTTPStatus.OK, api.mission_detail(mission_id))
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            except StoreError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": self._known_error(exc)})
            except (InvalidTransition, ValueError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": self._known_error(exc)})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal server error"})

        def do_POST(self) -> None:  # noqa: N802
            if len(self.path.encode("utf-8")) > SERVICE_MAX_REQUEST_TARGET_BYTES:
                self._json(HTTPStatus.REQUEST_URI_TOO_LONG, {"error": "request target too long"})
                return
            try:
                parsed = urlparse(self.path)
                if not parsed.path.startswith("/api/"):
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                if not self._require_service_auth():
                    return
                if not self._require_current_workflow():
                    return
                if parsed.path.startswith("/api/engine/"):
                    operation = parsed.path.removeprefix("/api/engine/")
                    self._json(HTTPStatus.OK, api.apply_engine_operation(operation, self._body()))
                    return
                if parsed.path != "/api/operator-actions":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                operator_token = self.headers.get("X-Software-Factory-Operator-Token", "")
                if not operator_token or len(operator_token) > 1024:
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "operator token required"})
                    return
                result = api.apply_operator_action(operator_token, self._body())
                self._json(HTTPStatus.OK, result)
            except (StoreError, InvalidTransition, ValueError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": self._known_error(exc)})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal server error"})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


class APIServer:
    def __init__(
        self,
        api: FactoryAPI,
        *,
        service_token: str,
        host: str = "127.0.0.1",
        port: int = 0,
    ):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("reference API binds only to loopback")
        if not 32 <= len(service_token) <= 512 or not service_token.isprintable():
            raise ValueError("service token must contain 32 to 512 printable characters")
        self.httpd = ThreadingHTTPServer((host, port), make_handler(api, service_token))
        self.thread: threading.Thread | None = None
        self._closed = threading.Event()

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.httpd.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        if self._closed.is_set():
            raise RuntimeError("API server is closed")
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def serve_forever(self) -> None:
        if self._closed.is_set():
            raise RuntimeError("API server is closed")
        self.httpd.serve_forever()

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        if self.thread is not None:
            self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
            self.thread = None
