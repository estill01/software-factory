from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
import concurrent.futures
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import Condition, Event, Lock, RLock, Thread
import time
from typing import Any, Mapping, Sequence

from .catalog import ProjectRecord


# Long-lived supervised tasks can legitimately carry dozens of bounded turns in
# one thread/read response. Keep the transport bounded while leaving room for
# the accepted 80-turn/250-item projection to perform its own tighter shaping.
MAX_PROTOCOL_LINE_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 512
MAX_PENDING_SERVER_REQUESTS = 100
MAX_TURNS = 80
MAX_ITEMS_PER_TURN = 250
MAX_TEXT = 16_000
MAX_TASK_CONTEXT_SCAN_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 20.0
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$")

CLIENT_MODELS = {
    "task_list": ("ThreadListParams", "list_threads"),
    "task_read": ("ThreadReadParams", "read_thread"),
    "task_start": ("ThreadStartParams", "start_thread"),
    "task_resume": ("ThreadResumeParams", "resume_thread"),
    "turn_start": ("TurnStartParams", "start_turn"),
    "turn_steer": ("TurnSteerParams", "steer_turn"),
    "turn_interrupt": ("TurnInterruptParams", "interrupt_turn"),
}
NOTIFICATION_METHODS = {
    "ThreadStartedNotification": "task_started",
    "ThreadStatusChangedNotification": "task_status",
    "TurnStartedNotification": "turn_started",
    "TurnCompletedNotification": "turn_completed",
    "ItemStartedNotification": "item_started",
    "ItemCompletedNotification": "item_completed",
    "ErrorNotification": "error",
}
SERVER_REQUEST_METHODS = {
    "CommandExecutionApprovalCallback": "command_approval",
    "FileChangeApprovalCallback": "file_approval",
    "UserInputCallback": "user_input",
}
FEATURES = (*CLIENT_MODELS, *SERVER_REQUEST_METHODS.values(), "event_stream")
APPROVAL_DECISIONS = {"accept", "acceptForSession", "decline", "cancel"}


class AppServerError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 503,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _observed_at() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return (
            datetime.fromtimestamp(value, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
    except (OverflowError, OSError, ValueError):
        return None


def _bounded(value: Any, maximum: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= maximum else f"{text[: maximum - 1]}…"


def _redacted(value: Any, maximum: int) -> str | None:
    text = _bounded(value, maximum)
    if text is None:
        return None
    text = text.replace(str(Path.home()), "<home>")
    return re.sub(r"https?://[^\s\"']+", "<url>", text)


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SAFE_IDENTIFIER.fullmatch(value):
        raise AppServerError("invalid_identifier", f"{label} is invalid.", status=400)
    return value


@dataclass
class PendingServerRequest:
    request_id: str
    source_fingerprint: str
    generation: int
    family: str
    params: dict[str, Any]
    received_at: str
    callback: Any = field(repr=False)
    status: str = "pending"


class TaskEventBuffer:
    def __init__(self) -> None:
        self._condition = Condition()
        self._events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)
        self._sequence = 0

    def publish(self, event_type: str, data: Mapping[str, Any]) -> dict[str, Any]:
        with self._condition:
            self._sequence += 1
            event = {
                "sequence": self._sequence,
                "type": event_type,
                "observed_at": _observed_at(),
                "data": dict(data),
            }
            self._events.append(event)
            self._condition.notify_all()
            return event

    def after(self, sequence: int, timeout: float = 15.0) -> list[dict[str, Any]]:
        _, events = self.replay_after(sequence, timeout)
        return events

    def replay_state(self, requested_after: int) -> dict[str, int | bool]:
        with self._condition:
            return self._replay_state_locked(requested_after)

    def replay_after(
        self, requested_after: int, timeout: float = 15.0
    ) -> tuple[dict[str, int | bool], list[dict[str, Any]]]:
        with self._condition:
            if self._sequence <= requested_after:
                self._condition.wait(timeout)
            replay = self._replay_state_locked(requested_after)
            events = [
                dict(item)
                for item in self._events
                if item["sequence"] > requested_after
            ]
            return replay, events

    def _replay_state_locked(self, requested_after: int) -> dict[str, int | bool]:
        oldest_available = (
            int(self._events[0]["sequence"]) if self._events else self._sequence + 1
        )
        return {
            "requested_after": requested_after,
            "oldest_available": oldest_available,
            "latest_available": self._sequence,
            "truncated": requested_after < oldest_available - 1,
        }

    @property
    def sequence(self) -> int:
        with self._condition:
            return self._sequence


class _LoopOwner:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self._ready = Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed = False
        self._thread = Thread(
            target=self._run,
            daemon=True,
            name="software-factory-dashboard-shared-client",
        )
        self._thread.start()
        if not self._ready.wait(5):
            raise AppServerError(
                "app_server_owner_unavailable",
                "The shared App Server event-loop owner did not start.",
                retryable=True,
            )

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()
        loop.close()

    def call(self, awaitable: Any) -> Any:
        if self._closed or self._loop is None:
            if asyncio.iscoroutine(awaitable):
                awaitable.close()
            raise AppServerError(
                "app_server_disconnected",
                "The shared App Server owner is closed.",
                retryable=True,
            )
        future = asyncio.run_coroutine_threadsafe(awaitable, self._loop)
        try:
            return future.result(timeout=self.timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise AppServerError(
                "app_server_timeout",
                "The shared App Server operation exceeded its bound.",
                retryable=True,
            ) from exc

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise AppServerError(
                "app_server_cleanup_failed",
                "The shared App Server event-loop owner did not stop.",
            )


def _qualified_client_loader(wheel_path: Path) -> tuple[Any, Any]:
    try:
        from software_factory.provider_provenance import load_qualified_client
    except ImportError as exc:
        raise AppServerError(
            "app_server_verifier_unavailable",
            "The Factory qualified-client verifier is unavailable.",
        ) from exc
    try:
        return load_qualified_client(wheel_path)
    except Exception as exc:
        raise AppServerError(
            "app_server_artifact_rejected",
            "The configured shared-client wheel did not match the accepted Factory pin.",
        ) from exc


class CodexAppServerClient:
    def __init__(
        self,
        *,
        wheel_path: str | Path | None = None,
        codex_executable: str | Path | None = None,
        codex_home: str | Path | None = None,
        request_timeout: float = REQUEST_TIMEOUT_SECONDS,
        auto_start: bool = True,
    ) -> None:
        self.wheel_path = (
            Path(wheel_path).expanduser() if wheel_path is not None else None
        )
        self.codex_executable = codex_executable
        self.configured_codex_home = Path(
            codex_home or Path.home() / ".codex"
        ).expanduser()
        self.request_timeout = request_timeout
        self.events = TaskEventBuffer()
        self._lifecycle_lock = Lock()
        self._state_lock = RLock()
        self._owner: _LoopOwner | None = None
        self._client_module: Any = None
        self._pin: Any = None
        self._compatibility: Any = None
        self._client: Any = None
        self._session: Any = None
        self._event_task: asyncio.Task[None] | None = None
        self._callback_task: asyncio.Task[None] | None = None
        self._codex_home: Path | None = None
        self._server_requests: OrderedDict[str, PendingServerRequest] = OrderedDict()
        self._callback_sequence = 0
        self._status = "not-started"
        self._protocol_status = "not-started"
        self._last_error: dict[str, Any] | None = None
        self._generation = 0
        self._restart_count = 0
        self._ignored_notifications = 0
        self._failure_count = 0
        self._backoff_until = 0.0
        self._closing = False
        if auto_start:
            self.start()

    @staticmethod
    def _error(exc: BaseException) -> AppServerError:
        if isinstance(exc, AppServerError):
            return exc
        name = type(exc).__name__
        retryable = name in {
            "CallTimeoutError",
            "DisconnectedError",
            "RestartError",
            "StaleGenerationError",
            "TransportClosedError",
            "TransportStartError",
        }
        if name == "RemoteRpcError" and "not found" in str(exc).casefold():
            return AppServerError(
                "task_not_found", "The task was not found.", status=404
            )
        return AppServerError(
            "app_server_shared_client_error",
            f"The shared App Server client rejected the operation ({name}).",
            retryable=retryable,
        )

    def _set_failure(self, error: AppServerError) -> None:
        with self._state_lock:
            if self._closing:
                return
            self._status = "unavailable"
            self._protocol_status = (
                "incompatible" if "incompatible" in error.code else "disconnected"
            )
            self._failure_count += 1
            self._backoff_until = time.monotonic() + min(
                30.0, 2 ** min(self._failure_count, 4)
            )
            self._last_error = {
                "code": error.code,
                "message": str(error),
                "retryable": error.retryable,
                "observed_at": _observed_at(),
            }
            for request in self._server_requests.values():
                if request.status == "pending":
                    request.status = "stale"
        self.events.publish(
            "connection",
            {
                "status": "unavailable",
                "reason": str(error),
                "generation": self._generation,
            },
        )

    def _exact_codex_home(self) -> Path:
        unresolved = self.configured_codex_home
        try:
            resolved = unresolved.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise AppServerError(
                "app_server_codex_home_invalid",
                "The configured Codex owner root is unavailable.",
            ) from exc
        if (
            not unresolved.is_absolute()
            or unresolved.is_symlink()
            or resolved != unresolved
            or not resolved.is_dir()
            or resolved.stat().st_uid != os.getuid()
        ):
            raise AppServerError(
                "app_server_codex_home_invalid",
                "The configured Codex owner root is invalid.",
            )
        return resolved

    async def _connect(self, module: Any, compatibility: Any) -> tuple[Any, Any]:
        limits = module.ClientLimits(
            max_message_bytes=MAX_PROTOCOL_LINE_BYTES,
            max_pending_calls=256,
            max_events=MAX_EVENTS,
            max_callbacks=MAX_PENDING_SERVER_REQUESTS,
            max_backoff_seconds=30.0,
        )
        client = await module.AppServerClient.connect(
            module.StdioTransport(compatibility.binary),
            compatibility,
            limits=limits,
        )
        try:
            session = await client.initialize(
                module.ClientIdentity("software-factory-dashboard", "2.0")
            )
        except Exception:
            await client.close()
            raise
        return client, session

    async def _start_drainers(self, generation: int) -> None:
        self._event_task = asyncio.create_task(self._drain_events(generation))
        self._callback_task = asyncio.create_task(self._drain_callbacks(generation))

    def start(self, *, force: bool = False) -> None:
        with self._lifecycle_lock:
            with self._state_lock:
                if (
                    not force
                    and self._status == "available"
                    and self._session is not None
                ):
                    return
                if not force and time.monotonic() < self._backoff_until:
                    raise AppServerError(
                        "app_server_backoff",
                        "Shared App Server restart is backing off after a failure.",
                        retryable=True,
                    )
                self._closing = False
                self._status = "starting"
                self._protocol_status = "checking"
            self.events.publish(
                "connection", {"status": "starting", "generation": self._generation}
            )
            self._terminate_owner()
            owner: _LoopOwner | None = None
            try:
                if self.wheel_path is None:
                    raise AppServerError(
                        "app_server_artifact_required",
                        "An exact qualified shared-client wheel path is required.",
                    )
                module, pin = _qualified_client_loader(self.wheel_path)
                binary = module.resolve_codex_binary(self.codex_executable)
                compatibility = module.inspect_compatibility(binary)
                codex_home = self._exact_codex_home()
                owner = _LoopOwner(self.request_timeout)
                client, session = owner.call(self._connect(module, compatibility))
                with self._state_lock:
                    self._owner = owner
                    self._client_module = module
                    self._pin = pin
                    self._compatibility = compatibility
                    self._client = client
                    self._session = session
                    self._codex_home = codex_home
                    self._generation += 1
                    generation = self._generation
                    self._status = "available"
                    self._protocol_status = "compatible"
                    self._last_error = None
                    self._failure_count = 0
                    self._backoff_until = 0.0
                owner.call(self._start_drainers(generation))
            except Exception as exc:
                with self._state_lock:
                    assigned = owner is not None and self._owner is owner
                if assigned:
                    self._terminate_owner()
                elif owner is not None:
                    owner.stop()
                self._set_failure(self._error(exc))
                return
            self.events.publish(
                "connection", {"status": "available", "generation": self._generation}
            )

    async def _shutdown(self) -> None:
        tasks = [
            task
            for task in (self._event_task, self._callback_task)
            if task is not None and task is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()
        try:
            if self._client is not None:
                await self._client.close()
        finally:
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _terminate_owner(self) -> None:
        with self._state_lock:
            owner = self._owner
            self._owner = None
            self._session = None
            self._codex_home = None
            for request in self._server_requests.values():
                if request.status == "pending":
                    request.status = "stale"
        if owner is not None:
            try:
                owner.call(self._shutdown())
            finally:
                owner.stop()
        with self._state_lock:
            self._client = None
            self._event_task = None
            self._callback_task = None

    def restart(self) -> dict[str, Any]:
        with self._state_lock:
            self._restart_count += 1
            self._backoff_until = 0.0
        self.start(force=True)
        return self.integration_state()

    def close(self) -> None:
        with self._lifecycle_lock:
            with self._state_lock:
                self._closing = True
                self._status = "stopped"
                self._protocol_status = "stopped"
            self._terminate_owner()
            self.events.publish(
                "connection", {"status": "stopped", "generation": self._generation}
            )

    def _ensure_available(self) -> None:
        with self._state_lock:
            available = self._status == "available" and self._session is not None
            error = self._last_error
        if not available:
            try:
                self.start()
            except AppServerError:
                pass
        with self._state_lock:
            if self._status == "available" and self._session is not None:
                return
            error = self._last_error or error
        raise AppServerError(
            error["code"] if error else "app_server_unavailable",
            error["message"]
            if error
            else "The shared App Server client is unavailable.",
            retryable=bool(error and error["retryable"]),
        )

    async def _request_async(
        self, module: Any, session: Any, family: str, params: Mapping[str, Any]
    ) -> dict[str, Any]:
        spec = CLIENT_MODELS.get(family)
        if spec is None:
            raise AppServerError(
                "app_server_method_rejected",
                "The requested operation is outside the narrowed shared-client surface.",
                status=404,
            )
        model_name, method_name = spec
        model = getattr(module, model_name).from_dict(dict(params))
        response = await getattr(session, method_name)(
            model, timeout=self.request_timeout
        )
        result = response.to_dict()
        if not isinstance(result, dict):
            raise AppServerError(
                "app_server_message_invalid",
                "The shared client returned a non-object typed response.",
            )
        return result

    def _request(self, family: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_available()
        with self._state_lock:
            owner = self._owner
            module = self._client_module
            session = self._session
            generation = self._generation
        if owner is None or module is None or session is None:
            raise AppServerError(
                "app_server_disconnected",
                "The shared App Server session is unavailable.",
                retryable=True,
            )
        try:
            result = owner.call(self._request_async(module, session, family, params))
        except Exception as exc:
            error = self._error(exc)
            if error.retryable:
                self._set_failure(error)
            raise error
        with self._state_lock:
            if generation != self._generation:
                raise AppServerError(
                    "app_server_restarted",
                    "The shared App Server generation changed during the operation.",
                    status=409,
                    retryable=True,
                )
        return result

    async def _drain_events(self, generation: int) -> None:
        try:
            async for event in self._session.events():
                name = type(event).__name__
                event_type = NOTIFICATION_METHODS.get(name)
                if event_type is None:
                    with self._state_lock:
                        self._ignored_notifications += 1
                    continue
                params = event.to_dict()
                with self._state_lock:
                    if generation != self._generation:
                        return
                projection = self._notification_projection(event_type, params)
                self.events.publish(event_type, projection)
                if event_type == "turn_completed":
                    task_id = projection.get("task_id")
                    turn_id = projection.get("turn_id")
                    if isinstance(task_id, str) and isinstance(turn_id, str):
                        self._stale_requests_for_turn(task_id, turn_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._set_failure(self._error(exc))

    async def _drain_callbacks(self, generation: int) -> None:
        try:
            async for callback in self._session.callbacks():
                family = SERVER_REQUEST_METHODS.get(type(callback).__name__)
                if family is None:
                    raise AppServerError(
                        "app_server_callback_rejected",
                        "The shared client returned an unsupported callback type.",
                    )
                params = callback.params.to_dict()
                source_fingerprint = _digest(
                    {"family": family, "generation": generation, "params": params}
                )
                with self._state_lock:
                    if generation != self._generation:
                        return
                    self._callback_sequence += 1
                    request_id = _digest(
                        {
                            "source_fingerprint": source_fingerprint,
                            "sequence": self._callback_sequence,
                        }
                    )
                    pending = [
                        item
                        for item in self._server_requests.values()
                        if item.status == "pending"
                    ]
                    if len(pending) >= MAX_PENDING_SERVER_REQUESTS:
                        raise AppServerError(
                            "app_server_callback_capacity",
                            "The dashboard callback buffer reached its exact bound.",
                        )
                    evictable = next(
                        (
                            key
                            for key, item in self._server_requests.items()
                            if item.status != "pending"
                        ),
                        None,
                    )
                    if (
                        len(self._server_requests) >= MAX_PENDING_SERVER_REQUESTS
                        and evictable
                    ):
                        self._server_requests.pop(evictable)
                    record = PendingServerRequest(
                        request_id=request_id,
                        source_fingerprint=source_fingerprint,
                        generation=generation,
                        family=family,
                        params=params,
                        received_at=_observed_at(),
                        callback=callback,
                    )
                    self._server_requests[request_id] = record
                self.events.publish("request", self._server_request_projection(record))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._set_failure(self._error(exc))

    def _notification_projection(
        self, event_type: str, params: Mapping[str, Any]
    ) -> dict[str, Any]:
        if event_type == "task_started":
            thread = params.get("thread")
            return {
                "task_id": thread.get("id") if isinstance(thread, Mapping) else None,
                "status": _status_projection(thread.get("status"))
                if isinstance(thread, Mapping)
                else {"type": "unknown", "active_flags": []},
            }
        if event_type == "task_status":
            return {
                "task_id": _bounded(params.get("threadId"), 256),
                "status": _status_projection(params.get("status")),
            }
        if event_type in {"turn_started", "turn_completed"}:
            turn = params.get("turn")
            return {
                "task_id": _bounded(params.get("threadId"), 256),
                "turn_id": _bounded(turn.get("id"), 256)
                if isinstance(turn, Mapping)
                else None,
                "status": _bounded(turn.get("status"), 80)
                if isinstance(turn, Mapping)
                else None,
            }
        if event_type in {"item_started", "item_completed"}:
            item = params.get("item")
            return {
                "task_id": _bounded(params.get("threadId"), 256),
                "turn_id": _bounded(params.get("turnId"), 256),
                "item": _item_projection(item) if isinstance(item, Mapping) else None,
            }
        raw_error = params.get("error")
        error = raw_error if isinstance(raw_error, Mapping) else {}
        error_info = error.get("codexErrorInfo")
        if isinstance(error_info, str):
            error_code = error_info
        elif isinstance(error_info, Mapping) and len(error_info) == 1:
            error_code = _bounded(next(iter(error_info)), 100)
        else:
            error_code = None
        return {
            "task_id": _bounded(params.get("threadId"), 256),
            "turn_id": _bounded(params.get("turnId"), 256),
            "message": _redacted(error.get("message"), 500)
            or "Codex reported a task error.",
            "code": error_code,
            "will_retry": bool(params.get("willRetry")),
        }

    def _server_request_projection(
        self, request: PendingServerRequest
    ) -> dict[str, Any]:
        params = request.params
        if request.family == "command_approval":
            details: dict[str, Any] = {
                "command": _bounded(params.get("command"), 2_000),
                "cwd": _bounded(params.get("cwd"), 1_000),
                "reason": _bounded(params.get("reason"), 1_000),
            }
        elif request.family == "file_approval":
            details = {
                "grant_root": _bounded(params.get("grantRoot"), 1_000),
                "reason": _bounded(params.get("reason"), 1_000),
            }
        else:
            details = {
                "questions": [
                    {
                        "id": _bounded(question.get("id"), 160),
                        "header": _bounded(question.get("header"), 160),
                        "question": _bounded(question.get("question"), 1_000),
                        "options": [
                            {
                                "label": _bounded(option.get("label"), 160),
                                "description": _bounded(option.get("description"), 500),
                            }
                            for option in question.get("options", [])
                            if isinstance(option, Mapping)
                        ],
                    }
                    for question in params.get("questions", [])
                    if isinstance(question, Mapping)
                ]
            }
        return {
            "id": request.request_id,
            "source_fingerprint": request.source_fingerprint,
            "family": request.family,
            "task_id": _bounded(params.get("threadId"), 256),
            "turn_id": _bounded(params.get("turnId"), 256),
            "item_id": _bounded(params.get("itemId"), 256),
            "received_at": request.received_at,
            "status": request.status,
            "details": details,
        }

    def _stale_requests_for_turn(self, task_id: str, turn_id: str) -> None:
        with self._state_lock:
            for request in self._server_requests.values():
                if (
                    request.status == "pending"
                    and request.params.get("threadId") == task_id
                    and request.params.get("turnId") == turn_id
                ):
                    request.status = "stale"

    def respond_to_server_request(
        self,
        request_id: str,
        source_fingerprint: str,
        response: Mapping[str, Any],
    ) -> dict[str, Any]:
        _identifier(request_id, "Request ID")
        if not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint):
            raise AppServerError(
                "invalid_source_fingerprint",
                "Request source fingerprint is invalid.",
                status=400,
            )
        with self._state_lock:
            request = self._server_requests.get(request_id)
            module = self._client_module
            owner = self._owner
            generation = self._generation
        if request is None:
            raise AppServerError(
                "task_request_not_found",
                "The task request is no longer available.",
                status=404,
            )
        if (
            request.status != "pending"
            or request.source_fingerprint != source_fingerprint
            or request.generation != generation
        ):
            raise AppServerError(
                "task_request_stale",
                "The task request changed, completed, or was already answered.",
                status=409,
            )
        if request.family in {"command_approval", "file_approval"}:
            if (
                set(response) != {"decision"}
                or response.get("decision") not in APPROVAL_DECISIONS
            ):
                raise AppServerError(
                    "invalid_approval_response",
                    "Approval response requires one supported decision.",
                    status=400,
                )
            result: dict[str, Any] = {"decision": response["decision"]}
            response_name = (
                "CommandExecutionRequestApprovalResponse"
                if request.family == "command_approval"
                else "FileChangeRequestApprovalResponse"
            )
        else:
            if set(response) != {"answers"} or not isinstance(
                response.get("answers"), Mapping
            ):
                raise AppServerError(
                    "invalid_input_response",
                    "Input response requires the exact answers object.",
                    status=400,
                )
            question_ids = {
                item.get("id")
                for item in request.params.get("questions", [])
                if isinstance(item, Mapping) and isinstance(item.get("id"), str)
            }
            if set(response["answers"]) != question_ids:
                raise AppServerError(
                    "invalid_input_response",
                    "Input response must answer each current question exactly once.",
                    status=400,
                )
            answers: dict[str, dict[str, list[str]]] = {}
            for key, value in response["answers"].items():
                if (
                    not isinstance(value, list)
                    or not value
                    or len(value) > 5
                    or any(
                        not isinstance(item, str) or not item or len(item) > 2_000
                        for item in value
                    )
                ):
                    raise AppServerError(
                        "invalid_input_response",
                        "Each current question requires one to five bounded text answers.",
                        status=400,
                    )
                answers[str(key)] = {"answers": list(value)}
            result = {"answers": answers}
            response_name = "ToolRequestUserInputResponse"
        if module is None or owner is None:
            raise AppServerError(
                "app_server_disconnected",
                "The shared App Server callback owner is unavailable.",
                retryable=True,
            )
        try:
            typed = getattr(module, response_name).from_dict(result)
            with self._state_lock:
                if (
                    request.status != "pending"
                    or request.generation != self._generation
                ):
                    raise AppServerError(
                        "task_request_stale",
                        "The task request became stale before response.",
                        status=409,
                    )
                request.status = "responding"
            owner.call(request.callback.respond(typed))
        except Exception as exc:
            with self._state_lock:
                request.status = "stale"
            raise self._error(exc)
        with self._state_lock:
            request.status = "responded"
        projection = self._server_request_projection(request)
        self.events.publish("request_resolved", projection)
        return projection

    def pending_requests(self) -> list[dict[str, Any]]:
        with self._state_lock:
            records = [
                record
                for record in self._server_requests.values()
                if record.status == "pending"
            ]
        return [self._server_request_projection(record) for record in records]

    def feature_matrix(self) -> list[dict[str, Any]]:
        with self._state_lock:
            available = (
                self._status == "available" and self._protocol_status == "compatible"
            )
        owner_gated = {
            "task_start",
            "task_resume",
            "turn_start",
            "turn_steer",
            "turn_interrupt",
            "command_approval",
            "file_approval",
            "user_input",
        }
        rows = [
            {
                "capability": capability,
                "status": "supported" if available else "unavailable",
                "exposure": "owner-gated" if capability in owner_gated else "read",
                "reason": (
                    "The exact qualified shared client supports this capability; dashboard controls remain owner-gated."
                    if available and capability in owner_gated
                    else None
                    if available
                    else "The exact qualified shared-client session is unavailable."
                ),
            }
            for capability in FEATURES
        ]
        rows.extend(
            [
                {
                    "capability": "task_fork",
                    "status": "unavailable",
                    "exposure": "unavailable",
                    "reason": "No registered owner workflow requires task forking.",
                },
                {
                    "capability": "permission_profile_response",
                    "status": "unavailable",
                    "exposure": "unavailable",
                    "reason": "Permission-profile grants are outside the narrowed response contract.",
                },
                {
                    "capability": "raw_protocol",
                    "status": "unavailable",
                    "exposure": "unavailable",
                    "reason": "Raw App Server methods and payloads are owned only by the shared client.",
                },
            ]
        )
        return rows

    def integration_state(self) -> dict[str, Any]:
        with self._state_lock:
            compatibility = self._compatibility
            pin_record = dict(self._pin.record) if self._pin is not None else {}
            binary = compatibility.binary if compatibility is not None else None
            target = compatibility.target if compatibility is not None else None
            state = {
                "status": self._status,
                "protocol_status": self._protocol_status,
                "client_package": {
                    "distribution": pin_record.get("distribution"),
                    "version": pin_record.get("version"),
                    "producer_revision": pin_record.get("qualified_producer_revision"),
                    "accepted_source_commit": pin_record.get("accepted_source_commit"),
                    "package_tree_object": pin_record.get("package_tree_object"),
                    "wheel_sha256": pin_record.get("wheel_sha256"),
                    "release_posture": pin_record.get("release_posture"),
                    "rights_boundary": pin_record.get("rights_boundary"),
                },
                "cli": {
                    "command": [str(binary.path)] if binary is not None else None,
                    "version": str(binary.reported_version)
                    if binary is not None
                    else None,
                    "expected_version": pin_record.get("protocol", {}).get(
                        "codex_version"
                    ),
                    "binary_sha256": str(binary.sha256) if binary is not None else None,
                },
                "schema": {
                    "schema_tree_root_sha256": str(target.schema_tree_root_sha256)
                    if target is not None
                    else None,
                    "expected_schema_tree_root_sha256": pin_record.get(
                        "protocol", {}
                    ).get("schema_tree_root_sha256"),
                    "selected_surface_root_sha256": str(
                        target.selected_surface_root_sha256
                    )
                    if target is not None
                    else None,
                    "expected_selected_surface_root_sha256": pin_record.get(
                        "protocol", {}
                    ).get("selected_surface_root_sha256"),
                },
                "transport": {
                    "kind": "shared-client-owned-stdio",
                    "owner_active": self._owner is not None
                    and self._session is not None,
                },
                "reconnect": {
                    "failure_count": self._failure_count,
                    "retry_after_ms": max(
                        0,
                        min(
                            30_000,
                            round((self._backoff_until - time.monotonic()) * 1_000),
                        ),
                    ),
                    "maximum_delay_ms": 30_000,
                },
                "features": self.feature_matrix(),
                "pending_requests": len(
                    [
                        item
                        for item in self._server_requests.values()
                        if item.status == "pending"
                    ]
                ),
                "last_error": dict(self._last_error) if self._last_error else None,
                "restart_count": self._restart_count,
                "connection_generation": self._generation,
                "ignored_protocol_messages": self._ignored_notifications,
                "observed_at": _observed_at(),
            }
        state["revision"] = _digest(state)
        return state

    def list_tasks(
        self,
        projects: Sequence[ProjectRecord],
        *,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise AppServerError(
                "invalid_task_page_limit",
                "Task page limit must be between 1 and 100.",
                status=400,
            )
        params: dict[str, Any] = {
            "limit": limit,
            "sortKey": "updated_at",
            "sortDirection": "desc",
        }
        if cursor is not None:
            if not cursor or len(cursor) > 1_000:
                raise AppServerError(
                    "invalid_task_cursor",
                    "Task cursor is invalid.",
                    status=400,
                )
            params["cursor"] = cursor
        result = self._request("task_list", params)
        return {
            "tasks": [_task_projection(item, projects) for item in result["data"]],
            "next_cursor": result.get("nextCursor"),
            "backwards_cursor": result.get("backwardsCursor"),
            "pending_requests": self.pending_requests(),
            "integration": self.integration_state(),
        }

    def read_task(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        *,
        include_turns: bool = True,
    ) -> dict[str, Any]:
        task_id = _identifier(task_id, "Task ID")
        result = self._request(
            "task_read",
            {"threadId": task_id, "includeTurns": bool(include_turns)},
        )
        return {
            "task": _task_projection(result["thread"], projects),
            "pending_requests": [
                item for item in self.pending_requests() if item["task_id"] == task_id
            ],
            "integration": self.integration_state(),
        }

    def read_task_with_execution_contract(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
    ) -> dict[str, Any]:
        """Read a task plus its exact latest persisted model/effort contract."""

        task_id = _identifier(task_id, "Task ID")
        result = self._request(
            "task_read",
            {"threadId": task_id, "includeTurns": True},
        )
        thread = result["thread"]
        task = _task_projection(thread, projects)
        with self._state_lock:
            codex_home = self._codex_home
        if codex_home is None:
            raise AppServerError(
                "task_execution_contract_unavailable",
                "The exact Codex owner root is unavailable.",
                status=409,
            )
        task["execution_contract"] = _task_execution_contract(
            thread,
            task_id,
            codex_home,
        )
        return {
            "task": task,
            "pending_requests": [
                item for item in self.pending_requests() if item["task_id"] == task_id
            ],
            "integration": self.integration_state(),
        }

    @staticmethod
    def _project(projects: Sequence[ProjectRecord], project_id: str) -> ProjectRecord:
        matches = [
            project
            for project in projects
            if project.id == project_id and not project.archived
        ]
        if len(matches) != 1:
            raise AppServerError(
                "project_not_available",
                "Task operation requires one active registered project.",
                status=409,
            )
        return matches[0]

    def _task_for_mutation(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        *,
        include_turns: bool,
    ) -> dict[str, Any]:
        projected = self.read_task(projects, task_id, include_turns=include_turns)[
            "task"
        ]
        if projected["project_binding"]["status"] != "bound":
            raise AppServerError(
                "task_project_unregistered",
                "Task operation requires an exact registered cwd binding.",
                status=409,
            )
        return projected

    def start_task(
        self,
        projects: Sequence[ProjectRecord],
        *,
        project_id: str,
        ephemeral: bool = False,
    ) -> dict[str, Any]:
        project = self._project(projects, project_id)
        result = self._request(
            "task_start",
            {"cwd": project.root, "ephemeral": bool(ephemeral)},
        )
        return {
            "task": _task_projection(result["thread"], projects),
            "operation": "task_started",
        }

    def resume_task(
        self, projects: Sequence[ProjectRecord], task_id: str
    ) -> dict[str, Any]:
        self._task_for_mutation(projects, task_id, include_turns=False)
        result = self._request("task_resume", {"threadId": task_id})
        return {
            "task": _task_projection(result["thread"], projects),
            "operation": "task_resumed",
        }

    def start_turn(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        text: str,
    ) -> dict[str, Any]:
        self._task_for_mutation(projects, task_id, include_turns=False)
        text = _validated_text(text)
        result = self._request(
            "turn_start",
            {"threadId": task_id, "input": [{"type": "text", "text": text}]},
        )
        return {"turn": _turn_projection(result["turn"]), "operation": "turn_started"}

    def start_configured_role_turn(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        text: str,
        *,
        expected_cwd: str,
        expected_cwd_identity: tuple[int, int],
    ) -> dict[str, Any]:
        """Start one turn on an exact route-gated role task.

        Supervision role tasks may live in Codex-owned task workspaces rather
        than a registered product repository. This method is intentionally not
        exposed as a generic HTTP task control: its caller must have already
        resolved the configured role and route gate, and it binds the task to
        the exact canonical cwd observed in that preview.
        """

        task_id = _identifier(task_id, "Role task ID")
        text = _validated_text(text)

        def current_cwd() -> str:
            try:
                canonical = str(Path(expected_cwd).expanduser().resolve(strict=True))
                cwd_path = Path(canonical)
                cwd_stat = cwd_path.stat()
            except (OSError, RuntimeError) as error:
                raise AppServerError(
                    "role_task_cwd_unavailable",
                    "The configured role task cwd is unavailable.",
                    status=409,
                ) from error
            if not cwd_path.is_dir():
                raise AppServerError(
                    "role_task_cwd_unavailable",
                    "The configured role task cwd is not a directory.",
                    status=409,
                )
            if (cwd_stat.st_dev, cwd_stat.st_ino) != expected_cwd_identity:
                raise AppServerError(
                    "role_task_cwd_changed",
                    "The configured role task cwd changed after preview.",
                    status=409,
                )
            return canonical

        canonical_cwd = current_cwd()
        task = self.read_task(projects, task_id, include_turns=False)["task"]
        try:
            observed_cwd = str(Path(task["cwd"]).expanduser().resolve(strict=True))
        except (OSError, RuntimeError) as error:
            raise AppServerError(
                "role_task_cwd_unavailable",
                "The configured role task cwd is unavailable.",
                status=409,
            ) from error
        if task["id"] != task_id or observed_cwd != canonical_cwd:
            raise AppServerError(
                "role_task_identity_changed",
                "The configured role task identity or cwd changed after preview.",
                status=409,
            )
        status = task["status"]["type"]
        resumed = False
        if status == "notLoaded":
            result = self._request("task_resume", {"threadId": task_id})
            resumed_task = _task_projection(result["thread"], projects)
            try:
                resumed_cwd = str(
                    Path(resumed_task["cwd"]).expanduser().resolve(strict=True)
                )
            except (OSError, RuntimeError) as error:
                raise AppServerError(
                    "role_task_cwd_unavailable",
                    "The resumed role task cwd is unavailable.",
                    status=409,
                ) from error
            if resumed_task["id"] != task_id or resumed_cwd != canonical_cwd:
                raise AppServerError(
                    "role_task_identity_changed",
                    "The resumed role task identity or cwd did not match the preview.",
                    status=409,
                )
            status = resumed_task["status"]["type"]
            resumed = True
        if status != "idle":
            raise AppServerError(
                "role_task_not_idle",
                "The configured role task is not idle for an immediate turn.",
                status=409,
            )
        # Bind the owner call to the same directory object as the preview even
        # if the path was replaced while task state was being re-read/resumed.
        current_cwd()
        result = self._request(
            "turn_start",
            {"threadId": task_id, "input": [{"type": "text", "text": text}]},
        )
        return {
            "turn": _turn_projection(result["turn"]),
            "operation": "role_turn_started",
            "task_resumed": resumed,
        }

    def steer_turn(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        turn_id: str,
        text: str,
    ) -> dict[str, Any]:
        task = self._task_for_mutation(projects, task_id, include_turns=True)
        turn_id = _identifier(turn_id, "Turn ID")
        active = next(
            (
                turn
                for turn in task["turns"]
                if turn["id"] == turn_id and turn["status"] == "inProgress"
            ),
            None,
        )
        if active is None:
            raise AppServerError(
                "turn_not_active",
                "The exact turn is not active and cannot accept steering.",
                status=409,
            )
        result = self._request(
            "turn_steer",
            {
                "threadId": task_id,
                "expectedTurnId": turn_id,
                "input": [{"type": "text", "text": _validated_text(text)}],
            },
        )
        return {"turn_id": result["turnId"], "operation": "turn_steered"}

    def interrupt_turn(
        self,
        projects: Sequence[ProjectRecord],
        task_id: str,
        turn_id: str,
    ) -> dict[str, Any]:
        task = self._task_for_mutation(projects, task_id, include_turns=True)
        turn_id = _identifier(turn_id, "Turn ID")
        active = next(
            (
                turn
                for turn in task["turns"]
                if turn["id"] == turn_id and turn["status"] == "inProgress"
            ),
            None,
        )
        if active is None:
            raise AppServerError(
                "turn_not_active",
                "The exact turn is not active and cannot be interrupted.",
                status=409,
            )
        self._request(
            "turn_interrupt",
            {"threadId": task_id, "turnId": turn_id},
        )
        return {"turn_id": turn_id, "operation": "turn_interrupted"}


def _validated_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 32_000:
        raise AppServerError(
            "invalid_task_input",
            "Task input must be 1 to 32,000 characters.",
            status=400,
        )
    return value


def _status_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not isinstance(value.get("type"), str):
        return {"type": "unknown", "active_flags": []}
    return {
        "type": value["type"],
        "active_flags": [
            _bounded(item, 80)
            for item in value.get("activeFlags", [])
            if isinstance(item, str)
        ],
    }


def _project_binding(cwd: str, projects: Sequence[ProjectRecord]) -> dict[str, Any]:
    try:
        resolved = Path(cwd).expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return {"status": "unregistered", "project_id": None, "candidates": []}
    candidates: list[str] = []
    for project in projects:
        if project.archived:
            continue
        try:
            resolved.relative_to(Path(project.root).expanduser().resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            continue
        candidates.append(project.id)
    if len(candidates) == 1:
        return {
            "status": "bound",
            "project_id": candidates[0],
            "candidates": candidates,
        }
    if len(candidates) > 1:
        return {"status": "ambiguous", "project_id": None, "candidates": candidates}
    return {"status": "unregistered", "project_id": None, "candidates": []}


def _source_label(value: Any) -> str:
    if isinstance(value, str):
        return _bounded(value, 100) or "unknown"
    if isinstance(value, Mapping) and len(value) == 1:
        return _bounded(next(iter(value)), 100) or "unknown"
    return "unknown"


def _item_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    item_type = _bounded(item.get("type"), 100) or "unknown"
    summary: str | None = None
    summary_content: str | None = None
    status: str | None = None
    user_content: str | None = None
    user_content_parts: list[Any] | None = None
    user_content_part_types: list[str] | None = None
    user_input_classification: str | None = None
    user_authority_status: str | None = None
    if item_type in {"agentMessage", "plan"}:
        summary_content = (
            item.get("text") if isinstance(item.get("text"), str) else None
        )
        summary = _bounded(summary_content)
    elif item_type == "userMessage":
        raw_parts = item.get("content")
        user_content_parts = raw_parts if isinstance(raw_parts, list) else None
        user_content_part_types = (
            [
                str(value.get("type"))
                if isinstance(value, Mapping) and isinstance(value.get("type"), str)
                else "unknown"
                for value in user_content_parts
            ]
            if user_content_parts is not None
            else None
        )
        texts = [
            value.get("text")
            for value in user_content_parts or []
            if isinstance(value, Mapping)
            and value.get("type") == "text"
            and isinstance(value.get("text"), str)
        ]
        user_content = "\n".join(texts)
        summary_content = user_content
        summary = _bounded(user_content)
        normalized = user_content.lstrip().casefold()
        if user_content_part_types != ["text"]:
            user_input_classification = "noncanonical-content-envelope"
            user_authority_status = "ineligible"
        elif "<codex_delegation" in normalized or "&lt;codex_delegation" in normalized:
            user_input_classification = "routed-delegation"
            user_authority_status = "ineligible"
        elif normalized.startswith("software_factory_dashboard_"):
            user_input_classification = "dashboard-generated-marker"
            user_authority_status = "ineligible"
        else:
            # The transport exposes a user message and client ID, but not an
            # authority class. Consequential consumers must keep authority
            # unverified until its maintained reviewer independently proves it.
            user_input_classification = "ordinary-user-message"
            user_authority_status = "unverified"
    elif item_type == "commandExecution":
        summary = _bounded(item.get("command"), 2_000)
        status = _bounded(item.get("status"), 100)
    elif item_type == "fileChange":
        changes = item.get("changes") if isinstance(item.get("changes"), list) else []
        summary = f"{len(changes)} file change{'s' if len(changes) != 1 else ''}"
        status = _bounded(item.get("status"), 100)
    elif item_type in {"mcpToolCall", "dynamicToolCall"}:
        summary = _bounded(item.get("tool"), 300)
        status = _bounded(item.get("status"), 100)
    elif item_type == "collabAgentToolCall":
        summary = _bounded(item.get("tool"), 300)
        status = _bounded(item.get("status"), 100)
    elif item_type == "reasoning":
        summary_values = (
            item.get("summary") if isinstance(item.get("summary"), list) else []
        )
        summary = _bounded(" ".join(str(value) for value in summary_values), 2_000)
    return {
        "id": _bounded(item.get("id"), 256) or "unknown",
        "type": item_type,
        "status": status,
        "summary": summary,
        "summary_sha256": (
            sha256(summary_content.encode("utf-8")).hexdigest()
            if summary_content is not None
            else None
        ),
        "summary_truncated": (
            len(summary_content) > MAX_TEXT if summary_content is not None else None
        ),
        "client_id": (
            item.get("clientId") if isinstance(item.get("clientId"), str) else None
        ),
        "user_content_sha256": (
            sha256(user_content.encode("utf-8")).hexdigest()
            if user_content is not None
            else None
        ),
        "user_content_truncated": (
            len(user_content) > MAX_TEXT if user_content is not None else None
        ),
        "user_content_envelope_sha256": (
            _digest(user_content_parts) if user_content_parts is not None else None
        ),
        "user_content_part_types": user_content_part_types,
        "user_input_classification": user_input_classification,
        "user_authority_status": user_authority_status,
    }


def _turn_projection(turn: Mapping[str, Any]) -> dict[str, Any]:
    items = turn.get("items") if isinstance(turn.get("items"), list) else []
    selected = items[-MAX_ITEMS_PER_TURN:]
    return {
        "id": _bounded(turn.get("id"), 256) or "unknown",
        "status": _bounded(turn.get("status"), 100) or "unknown",
        "started_at": _timestamp(turn.get("startedAt")),
        "completed_at": _timestamp(turn.get("completedAt")),
        "duration_ms": turn.get("durationMs")
        if isinstance(turn.get("durationMs"), int)
        else None,
        "items_view": _bounded(turn.get("itemsView"), 100) or "full",
        "items": [
            _item_projection(item) for item in selected if isinstance(item, Mapping)
        ],
        "items_truncated": len(items) > len(selected),
        "error": _bounded(turn.get("error"), 1_000) if turn.get("error") else None,
    }


def _task_execution_contract(
    thread: Mapping[str, Any],
    task_id: str,
    codex_home: Path,
) -> dict[str, Any]:
    """Resolve the latest exact turn contract from the App Server-owned task path."""

    raw_path = thread.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise AppServerError(
            "task_execution_contract_unavailable",
            "The App Server did not expose an exact persisted path for this task.",
            status=409,
        )
    unresolved = Path(raw_path)
    if not unresolved.is_absolute() or unresolved.is_symlink():
        raise AppServerError(
            "task_execution_contract_path_invalid",
            "The App Server task path is not a direct absolute regular file.",
            status=409,
        )
    try:
        resolved = unresolved.resolve(strict=True)
        metadata_before = resolved.stat()
    except (OSError, RuntimeError) as error:
        raise AppServerError(
            "task_execution_contract_unavailable",
            "The exact persisted task source is unavailable.",
            status=409,
        ) from error
    try:
        session_root = (codex_home / "sessions").resolve(strict=True)
        relative = resolved.relative_to(session_root)
    except (OSError, RuntimeError, ValueError) as error:
        raise AppServerError(
            "task_execution_contract_path_invalid",
            "The persisted task source escaped the exact Codex sessions root.",
            status=409,
        ) from error
    if (
        session_root != codex_home / "sessions"
        or resolved != unresolved
        or not resolved.is_file()
        or len(relative.parts) != 4
        or not re.fullmatch(r"\d{4}", relative.parts[0])
        or not re.fullmatch(r"\d{2}", relative.parts[1])
        or not re.fullmatch(r"\d{2}", relative.parts[2])
        or not relative.name.startswith("rollout-")
        or not relative.name.endswith(f"-{task_id}.jsonl")
        or metadata_before.st_uid != os.getuid()
        or metadata_before.st_mode & 0o022
    ):
        raise AppServerError(
            "task_execution_contract_path_invalid",
            "The persisted task source does not match the exact owner-controlled session path.",
            status=409,
        )
    start = max(0, metadata_before.st_size - MAX_TASK_CONTEXT_SCAN_BYTES)
    try:
        with resolved.open("rb") as source:
            source.seek(start)
            payload = source.read(MAX_TASK_CONTEXT_SCAN_BYTES + 1)
        metadata_after = resolved.stat()
    except OSError as error:
        raise AppServerError(
            "task_execution_contract_unavailable",
            "The exact persisted task source could not be read.",
            status=409,
        ) from error
    if len(payload) > MAX_TASK_CONTEXT_SCAN_BYTES or (
        metadata_before.st_dev,
        metadata_before.st_ino,
        metadata_before.st_size,
        metadata_before.st_mtime_ns,
    ) != (
        metadata_after.st_dev,
        metadata_after.st_ino,
        metadata_after.st_size,
        metadata_after.st_mtime_ns,
    ):
        raise AppServerError(
            "task_execution_contract_changed",
            "The persisted task source changed during the exact read.",
            status=409,
            retryable=True,
        )
    if start:
        separator = payload.find(b"\n")
        payload = payload[separator + 1 :] if separator >= 0 else b""
    for raw_line in reversed(payload.splitlines()):
        if not raw_line:
            continue
        if len(raw_line) > MAX_PROTOCOL_LINE_BYTES:
            raise AppServerError(
                "task_execution_contract_invalid",
                "A persisted task record exceeds the frozen record bound.",
                status=409,
            )
        try:
            record = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AppServerError(
                "task_execution_contract_invalid",
                "The persisted task source contains an invalid record.",
                status=409,
            ) from error
        if not isinstance(record, Mapping) or record.get("type") != "turn_context":
            continue
        context = record.get("payload")
        model = context.get("model") if isinstance(context, Mapping) else None
        effort = context.get("effort") if isinstance(context, Mapping) else None
        if (
            not isinstance(model, str)
            or not model
            or len(model) > 160
            or not isinstance(effort, str)
            or not effort
            or len(effort) > 80
        ):
            raise AppServerError(
                "task_execution_contract_invalid",
                "The latest persisted task contract omits exact model or effort.",
                status=409,
            )
        return {
            "model": model,
            "reasoning_effort": effort,
            "source_record_sha256": sha256(raw_line).hexdigest(),
            "source_size": metadata_after.st_size,
            "source_mtime_ns": metadata_after.st_mtime_ns,
            "source_device": metadata_after.st_dev,
            "source_inode": metadata_after.st_ino,
            "scan_complete": start == 0,
            "scan_bytes": len(payload),
        }
    raise AppServerError(
        "task_execution_contract_unavailable",
        "No exact recent model and effort contract exists in the bounded task source window.",
        status=409,
    )


def _task_projection(
    thread: Mapping[str, Any], projects: Sequence[ProjectRecord]
) -> dict[str, Any]:
    turns = thread.get("turns") if isinstance(thread.get("turns"), list) else []
    selected = turns[-MAX_TURNS:]
    cwd = str(thread.get("cwd", ""))
    git = thread.get("gitInfo") if isinstance(thread.get("gitInfo"), Mapping) else {}
    return {
        "id": _bounded(thread.get("id"), 256) or "unknown",
        "session_id": _bounded(thread.get("sessionId"), 256),
        "parent_task_id": _bounded(thread.get("parentThreadId"), 256),
        "forked_from_id": _bounded(thread.get("forkedFromId"), 256),
        "name": _bounded(thread.get("name"), 300),
        "preview": _bounded(thread.get("preview"), 2_000),
        "cwd": cwd,
        "project_binding": _project_binding(cwd, projects),
        "status": _status_projection(thread.get("status")),
        "created_at": _timestamp(thread.get("createdAt")),
        "updated_at": _timestamp(thread.get("updatedAt")),
        "recency_at": _timestamp(thread.get("recencyAt")),
        "source": _source_label(thread.get("source")),
        "model_provider": _bounded(thread.get("modelProvider"), 100) or "unknown",
        "cli_version": _bounded(thread.get("cliVersion"), 100) or "unknown",
        "ephemeral": bool(thread.get("ephemeral")),
        "git": {
            "revision": _bounded(git.get("sha"), 160),
            "branch": _bounded(git.get("branch"), 300),
            "origin": _bounded(git.get("originUrl"), 1_000),
        },
        "turns": [
            _turn_projection(turn) for turn in selected if isinstance(turn, Mapping)
        ],
        "turns_truncated": len(turns) > len(selected),
    }
