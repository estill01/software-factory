from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Condition, Event, Lock, RLock, Thread
import time
from typing import Any, Mapping, Sequence

from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import validator_for

from .catalog import ProjectRecord


COMPATIBILITY_PATH = Path(__file__).with_name("app_server_compatibility.json")
MAX_PROTOCOL_LINE_BYTES = 4 * 1024 * 1024
MAX_DIAGNOSTIC_LINE = 2_000
MAX_DIAGNOSTICS = 40
MAX_EVENTS = 512
MAX_PENDING_SERVER_REQUESTS = 100
MAX_COMPLETED_REQUEST_IDS = 256
MAX_TURNS = 80
MAX_ITEMS_PER_TURN = 250
MAX_TEXT = 16_000
REQUEST_TIMEOUT_SECONDS = 20.0
START_TIMEOUT_SECONDS = 40.0
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$")

CLIENT_METHODS = {
    "task_list": "thread/list",
    "task_read": "thread/read",
    "task_start": "thread/start",
    "task_resume": "thread/resume",
    "turn_start": "turn/start",
    "turn_steer": "turn/steer",
    "turn_interrupt": "turn/interrupt",
}
NOTIFICATION_METHODS = {
    "thread/started": ("task_started", "task_started"),
    "thread/status/changed": ("task_status", "task_status_changed"),
    "turn/started": ("turn_started", "turn_started"),
    "turn/completed": ("turn_completed", "turn_completed"),
    "item/started": ("item_started", "item_started"),
    "item/completed": ("item_completed", "item_completed"),
    "error": ("error", "error"),
}
SERVER_REQUEST_METHODS = {
    "item/commandExecution/requestApproval": "command_approval",
    "item/fileChange/requestApproval": "file_approval",
    "item/tool/requestUserInput": "user_input",
}
FEATURE_SCHEMA_KEYS = {
    **{
        family: (f"client:{family}:params", f"client:{family}:response")
        for family in CLIENT_METHODS
    },
    **{
        family: (f"server:{family}:params", f"server:{family}:response")
        for family in SERVER_REQUEST_METHODS.values()
    },
    "event_stream": tuple(
        f"notification:{schema_family}"
        for _, schema_family in NOTIFICATION_METHODS.values()
    ),
}
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


def _canonical(value: Any, *, newline: bool = False) -> bytes:
    suffix = "\n" if newline else ""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + suffix
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _observed_at() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value, UTC).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
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


def _resolved_command(command: Sequence[str] | None) -> tuple[str, ...]:
    requested = tuple(command) if command is not None else ("codex",)
    if not requested:
        raise AppServerError(
            "codex_cli_disabled",
            "Codex App Server is disabled for this runtime.",
            status=503,
        )
    executable = requested[0]
    located = shutil.which(executable) if not Path(executable).is_absolute() else executable
    if not located:
        raise AppServerError(
            "codex_cli_unavailable",
            "The configured Codex CLI executable is unavailable.",
            status=503,
        )
    resolved = Path(located).expanduser().resolve()
    if not resolved.is_file():
        raise AppServerError(
            "codex_cli_unavailable",
            "The configured Codex CLI path is not a regular file.",
            status=503,
        )
    return (str(resolved), *requested[1:])


def _manifest_root(root: Path) -> tuple[int, str]:
    lines: list[str] = []
    for source in sorted(root.rglob("*.json"), key=lambda item: item.relative_to(root).as_posix()):
        if source.is_symlink() or not source.is_file():
            raise AppServerError(
                "app_server_schema_invalid",
                "Generated schema bundle contains a non-regular JSON source.",
            )
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AppServerError(
                "app_server_schema_invalid",
                "Generated schema bundle contains invalid JSON.",
            ) from exc
        content_root = sha256(_canonical(value, newline=True)).hexdigest()
        lines.append(f"{content_root}  {source.relative_to(root).as_posix()}\n")
    return len(lines), sha256("".join(lines).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GeneratedCompatibility:
    command: tuple[str, ...]
    cli_version: str
    schema_root: str
    schema_count: int
    validators: Mapping[str, Any]
    config: Mapping[str, Any]

    @classmethod
    def generate(
        cls,
        command: Sequence[str] | None,
        *,
        compatibility_path: Path = COMPATIBILITY_PATH,
    ) -> "GeneratedCompatibility":
        try:
            config = json.loads(compatibility_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AppServerError(
                "app_server_contract_unavailable",
                "The frozen App Server compatibility contract is unavailable.",
            ) from exc
        resolved = _resolved_command(command)
        try:
            version = subprocess.run(
                [*resolved, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise AppServerError(
                "codex_cli_unavailable",
                "The configured Codex CLI version probe failed.",
                retryable=True,
            ) from exc
        if version != config.get("cli_version"):
            raise AppServerError(
                "app_server_version_incompatible",
                f"Codex CLI {version or 'unknown'} does not match the frozen {config.get('cli_version')} contract.",
            )
        with TemporaryDirectory(prefix="software-factory-app-server-schema-") as temporary:
            schema_root = Path(temporary)
            try:
                subprocess.run(
                    [*resolved, "app-server", "generate-json-schema", "--out", str(schema_root)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=START_TIMEOUT_SECONDS,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise AppServerError(
                    "app_server_schema_generation_failed",
                    "Codex App Server schema generation failed.",
                    retryable=True,
                ) from exc
            count, semantic_root = _manifest_root(schema_root)
            if count != config.get("generated_file_count") or semantic_root != config.get(
                "semantic_manifest_sha256"
            ):
                raise AppServerError(
                    "app_server_schema_incompatible",
                    "Generated App Server schemas do not match the frozen semantic root.",
                )
            validators: dict[str, Any] = {}
            schema_paths: dict[str, str] = {}
            for family, record in config["client_requests"].items():
                schema_paths[f"client:{family}:params"] = record["params_schema"]
                schema_paths[f"client:{family}:response"] = record["response_schema"]
            for family, relative in config["server_notifications"].items():
                schema_paths[f"notification:{family}"] = relative
            for family, record in config["server_requests"].items():
                schema_paths[f"server:{family}:params"] = record["params_schema"]
                schema_paths[f"server:{family}:response"] = record["response_schema"]
            schema_paths["protocol:error"] = config["protocol_error_schema"]
            try:
                for key, relative in schema_paths.items():
                    source = schema_root / relative
                    source.resolve(strict=True).relative_to(schema_root.resolve(strict=True))
                    schema = json.loads(source.read_text(encoding="utf-8"))
                    validator_type = validator_for(schema)
                    validator_type.check_schema(schema)
                    validators[key] = validator_type(schema)
            except (OSError, ValueError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
                raise AppServerError(
                    "app_server_schema_invalid",
                    "A selected generated App Server schema is unavailable or invalid.",
                ) from exc
        return cls(
            command=resolved,
            cli_version=version,
            schema_root=semantic_root,
            schema_count=count,
            validators=validators,
            config=config,
        )

    def validate(self, key: str, value: Any) -> None:
        validator = self.validators.get(key)
        if validator is None:
            raise AppServerError(
                "app_server_feature_unavailable",
                "The requested capability has no selected compatibility schema.",
                status=409,
            )
        try:
            validator.validate(value)
        except ValidationError as exc:
            raise AppServerError(
                "app_server_message_invalid",
                f"App Server message failed the frozen {key} schema at {list(exc.absolute_path)}.",
            ) from exc


@dataclass
class PendingCall:
    family: str
    generation: int
    event: Event = field(default_factory=Event)
    result: Any = None
    error: AppServerError | None = None


@dataclass
class PendingServerRequest:
    request_id: str
    source_fingerprint: str
    raw_id: str | int
    family: str
    params: dict[str, Any]
    received_at: str
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
            int(self._events[0]["sequence"])
            if self._events
            else self._sequence + 1
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


class CodexAppServerClient:
    def __init__(
        self,
        *,
        command: Sequence[str] | None = None,
        compatibility_path: Path = COMPATIBILITY_PATH,
        request_timeout: float = REQUEST_TIMEOUT_SECONDS,
        auto_start: bool = True,
    ) -> None:
        self.requested_command = None if command is None else tuple(command)
        self.compatibility_path = compatibility_path
        self.request_timeout = request_timeout
        self.events = TaskEventBuffer()
        self._lifecycle_lock = Lock()
        self._state_lock = RLock()
        self._write_lock = Lock()
        self._process: subprocess.Popen[str] | None = None
        self._compatibility: GeneratedCompatibility | None = None
        self._pending: dict[int, PendingCall] = {}
        self._completed_ids: deque[int] = deque(maxlen=MAX_COMPLETED_REQUEST_IDS)
        self._server_requests: OrderedDict[str, PendingServerRequest] = OrderedDict()
        self._next_id = 1
        self._status = "not-started"
        self._protocol_status = "not-started"
        self._last_error: dict[str, Any] | None = None
        self._diagnostics: deque[str] = deque(maxlen=MAX_DIAGNOSTICS)
        self._generation = 0
        self._restart_count = 0
        self._ignored_notifications = 0
        self._closing = False
        self._backoff_until = 0.0
        self._failure_count = 0
        if auto_start:
            self.start()

    def _set_failure(
        self,
        error: AppServerError,
        *,
        terminate: bool = True,
        expected_generation: int | None = None,
    ) -> None:
        with self._state_lock:
            if self._closing or (
                expected_generation is not None
                and expected_generation != self._generation
            ):
                return
            self._last_error = {
                "code": error.code,
                "message": str(error),
                "retryable": error.retryable,
                "observed_at": _observed_at(),
            }
            self._status = "unavailable"
            self._protocol_status = (
                "incompatible" if "incompatible" in error.code else "disconnected"
            )
            self._failure_count += 1
            self._backoff_until = time.monotonic() + min(30.0, 2 ** min(self._failure_count, 4))
            pending = list(self._pending.values())
            self._pending.clear()
            process = self._process
        for call in pending:
            call.error = error
            call.event.set()
        self.events.publish(
            "connection",
            {"status": "unavailable", "reason": str(error), "generation": self._generation},
        )
        if terminate and process is not None and process.poll() is None:
            process.terminate()

    def start(self, *, force: bool = False) -> None:
        with self._lifecycle_lock:
            with self._state_lock:
                process = self._process
                if (
                    not force
                    and self._status == "available"
                    and process is not None
                    and process.poll() is None
                ):
                    return
                if not force and time.monotonic() < self._backoff_until:
                    raise AppServerError(
                        "app_server_backoff",
                        "Codex App Server restart is backing off after a failure.",
                        retryable=True,
                    )
                self._status = "starting"
                self._protocol_status = "checking"
                self._closing = False
            self.events.publish("connection", {"status": "starting", "generation": self._generation})
            self._terminate_process()
            try:
                compatibility = GeneratedCompatibility.generate(
                    self.requested_command,
                    compatibility_path=self.compatibility_path,
                )
                process = subprocess.Popen(
                    [*compatibility.command, "app-server", "--stdio"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                if process.stdin is None or process.stdout is None or process.stderr is None:
                    raise AppServerError(
                        "app_server_transport_unavailable",
                        "Codex App Server stdio pipes were not created.",
                    )
                with self._state_lock:
                    self._compatibility = compatibility
                    self._process = process
                    self._generation += 1
                    generation = self._generation
                Thread(
                    target=self._read_stdout,
                    args=(process, generation),
                    daemon=True,
                    name="software-factory-codex-stdout",
                ).start()
                Thread(
                    target=self._read_stderr,
                    args=(process, generation),
                    daemon=True,
                    name="software-factory-codex-stderr",
                ).start()
                initialized = self._request(
                    "initialize",
                    {
                        "clientInfo": {
                            "name": "software-factory-dashboard",
                            "title": "Software Factory Dashboard",
                            "version": "0.1.0",
                        },
                        "capabilities": {"experimentalApi": False},
                    },
                    require_ready=False,
                )
                if not isinstance(initialized, Mapping):
                    raise AppServerError(
                        "app_server_initialize_invalid",
                        "Codex App Server returned an invalid initialize result.",
                    )
                self._write_message({"method": "initialized", "params": {}})
            except AppServerError as error:
                self._set_failure(error)
                return
            except (OSError, subprocess.SubprocessError):
                error = AppServerError(
                    "app_server_start_failed",
                    "Codex App Server could not be started.",
                    retryable=True,
                )
                self._set_failure(error)
                return
            with self._state_lock:
                self._status = "available"
                self._protocol_status = "compatible"
                self._last_error = None
                self._failure_count = 0
                self._backoff_until = 0.0
            self.events.publish(
                "connection",
                {"status": "available", "generation": self._generation},
            )

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
            self._terminate_process()
            self.events.publish("connection", {"status": "stopped", "generation": self._generation})

    def _terminate_process(self) -> None:
        with self._state_lock:
            process = self._process
            self._process = None
            pending = list(self._pending.values())
            self._pending.clear()
            for request in self._server_requests.values():
                if request.status == "pending":
                    request.status = "stale"
        closed = AppServerError(
            "app_server_restarted",
            "Codex App Server connection was restarted.",
            status=409,
            retryable=True,
        )
        for call in pending:
            call.error = closed
            call.event.set()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    def _ensure_available(self) -> None:
        with self._state_lock:
            available = (
                self._status == "available"
                and self._process is not None
                and self._process.poll() is None
            )
            error = self._last_error
        if available:
            return
        try:
            self.start()
        except AppServerError:
            pass
        with self._state_lock:
            if (
                self._status == "available"
                and self._process is not None
                and self._process.poll() is None
            ):
                return
            error = self._last_error or error
        raise AppServerError(
            error["code"] if error else "app_server_unavailable",
            error["message"] if error else "Codex App Server is unavailable.",
            retryable=bool(error and error["retryable"]),
        )

    def _write_message(self, message: Mapping[str, Any]) -> None:
        encoded = _canonical(message).decode("utf-8")
        if len(encoded.encode("utf-8")) > MAX_PROTOCOL_LINE_BYTES:
            raise AppServerError(
                "app_server_message_too_large",
                "App Server message exceeds the bounded transport limit.",
                status=413,
            )
        with self._state_lock:
            process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise AppServerError(
                "app_server_disconnected",
                "Codex App Server transport is disconnected.",
                retryable=True,
            )
        try:
            with self._write_lock:
                process.stdin.write(encoded + "\n")
                process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise AppServerError(
                "app_server_disconnected",
                "Codex App Server transport disconnected during a write.",
                retryable=True,
            ) from exc

    def _request(
        self,
        family: str,
        params: Mapping[str, Any],
        *,
        require_ready: bool = True,
    ) -> Any:
        if require_ready:
            self._ensure_available()
        compatibility = self._compatibility
        if compatibility is None:
            raise AppServerError(
                "app_server_contract_unavailable",
                "App Server compatibility schemas are unavailable.",
            )
        method = "initialize" if family == "initialize" else CLIENT_METHODS.get(family)
        if method is None:
            raise AppServerError(
                "app_server_method_rejected",
                "The requested operation is outside the narrowed App Server capability set.",
                status=404,
            )
        compatibility.validate(f"client:{family}:params", dict(params))
        with self._state_lock:
            generation = self._generation
            request_id = self._next_id
            self._next_id += 1
            pending = PendingCall(family=family, generation=generation)
            self._pending[request_id] = pending
        try:
            self._write_message({"id": request_id, "method": method, "params": dict(params)})
        except AppServerError:
            with self._state_lock:
                self._pending.pop(request_id, None)
            raise
        if not pending.event.wait(self.request_timeout):
            with self._state_lock:
                self._pending.pop(request_id, None)
            error = AppServerError(
                "app_server_timeout",
                "Codex App Server did not answer within the bounded timeout.",
                retryable=True,
            )
            self._set_failure(error, expected_generation=pending.generation)
            raise error
        if pending.error is not None:
            if pending.error.code not in {"app_server_remote_error", "task_not_found"}:
                self._set_failure(
                    pending.error,
                    expected_generation=pending.generation,
                )
            raise pending.error
        try:
            compatibility.validate(f"client:{family}:response", pending.result)
        except AppServerError as error:
            self._set_failure(error, expected_generation=pending.generation)
            raise
        return pending.result

    def _read_stdout(self, process: subprocess.Popen[str], generation: int) -> None:
        assert process.stdout is not None
        try:
            for raw_line in process.stdout:
                if len(raw_line.encode("utf-8", errors="replace")) > MAX_PROTOCOL_LINE_BYTES:
                    raise AppServerError(
                        "app_server_message_too_large",
                        "Codex App Server emitted an oversized protocol line.",
                    )
                try:
                    message = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise AppServerError(
                        "app_server_malformed_json",
                        "Codex App Server emitted malformed JSON.",
                    ) from exc
                if not isinstance(message, dict):
                    raise AppServerError(
                        "app_server_message_invalid",
                        "Codex App Server emitted a non-object message.",
                    )
                self._receive(message)
        except AppServerError as error:
            with self._state_lock:
                current = generation == self._generation and not self._closing
            if current:
                self._set_failure(error, expected_generation=generation)
            return
        finally:
            with self._state_lock:
                current = generation == self._generation and not self._closing
                active = self._process is process
                report_disconnect = self._status not in {"unavailable", "stopped"}
            if current and active and report_disconnect:
                self._set_failure(
                    AppServerError(
                        "app_server_disconnected",
                        "Codex App Server closed its output stream.",
                        retryable=True,
                    ),
                    terminate=False,
                    expected_generation=generation,
                )

    def _read_stderr(self, process: subprocess.Popen[str], generation: int) -> None:
        assert process.stderr is not None
        for raw_line in process.stderr:
            line = raw_line.strip()
            if not line:
                continue
            redacted = _redacted(line, MAX_DIAGNOSTIC_LINE) or ""
            with self._state_lock:
                if generation != self._generation:
                    return
                self._diagnostics.append(redacted)

    def _receive(self, message: dict[str, Any]) -> None:
        if "id" in message and ("result" in message or "error" in message) and "method" not in message:
            self._receive_response(message)
            return
        method = message.get("method")
        if not isinstance(method, str):
            raise AppServerError(
                "app_server_message_invalid",
                "Codex App Server message has no valid method or response identifier.",
            )
        if "id" in message:
            self._receive_server_request(message)
        else:
            self._receive_notification(method, message.get("params"))

    def _receive_response(self, message: dict[str, Any]) -> None:
        response_id = message.get("id")
        if not isinstance(response_id, int):
            raise AppServerError(
                "app_server_response_id_mismatch",
                "Codex App Server returned a non-integer response identifier.",
            )
        with self._state_lock:
            pending = self._pending.pop(response_id, None)
            duplicate = response_id in self._completed_ids
            if pending is not None:
                self._completed_ids.append(response_id)
        if pending is None:
            raise AppServerError(
                "app_server_duplicate_response" if duplicate else "app_server_response_id_mismatch",
                "Codex App Server returned a duplicate or unmatched response identifier.",
            )
        if "error" in message:
            compatibility = self._compatibility
            if compatibility is None:
                pending.error = AppServerError(
                    "app_server_contract_unavailable",
                    "App Server returned an error without a compatibility contract.",
                )
            else:
                try:
                    compatibility.validate("protocol:error", message)
                except AppServerError as validation_error:
                    pending.error = validation_error
                else:
                    error = message["error"]
                    remote_code = error.get("code")
                    remote_message = (
                        _bounded(error.get("message"), 500)
                        or "Codex App Server rejected the request."
                    )
                    if (
                        pending.family == "task_read"
                        and remote_code == -32600
                        and remote_message.startswith("thread not loaded:")
                    ):
                        pending.error = AppServerError(
                            "task_not_found",
                            "The requested Codex task is not loaded.",
                            status=404,
                        )
                    else:
                        pending.error = AppServerError(
                            "app_server_remote_error",
                            remote_message,
                            status=409,
                        )
        else:
            pending.result = message.get("result")
        pending.event.set()

    def _receive_notification(self, method: str, params: Any) -> None:
        mapped = NOTIFICATION_METHODS.get(method)
        if mapped is None:
            with self._state_lock:
                self._ignored_notifications += 1
            return
        event_type, schema_family = mapped
        compatibility = self._compatibility
        if compatibility is None:
            raise AppServerError(
                "app_server_contract_unavailable",
                "Notification arrived without a compatibility contract.",
            )
        compatibility.validate(f"notification:{schema_family}", params)
        if not isinstance(params, Mapping):
            raise AppServerError(
                "app_server_message_invalid",
                "App Server notification parameters are invalid.",
            )
        projected = self._notification_projection(event_type, params)
        self.events.publish(event_type, projected)
        if event_type == "turn_completed":
            self._stale_requests_for_turn(
                str(params.get("threadId", "")),
                str(params.get("turn", {}).get("id", ""))
                if isinstance(params.get("turn"), Mapping)
                else "",
            )

    def _receive_server_request(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        raw_id = message.get("id")
        if not isinstance(raw_id, (str, int)):
            raise AppServerError(
                "app_server_message_invalid",
                "App Server callback has an invalid identifier.",
            )
        family = SERVER_REQUEST_METHODS.get(str(method))
        if family is None:
            self._write_message(
                {
                    "id": raw_id,
                    "error": {
                        "code": -32601,
                        "message": "Client callback is outside the dashboard capability set.",
                    },
                }
            )
            with self._state_lock:
                self._ignored_notifications += 1
            return
        params = message.get("params")
        compatibility = self._compatibility
        if compatibility is None:
            raise AppServerError(
                "app_server_contract_unavailable",
                "Server request arrived without a compatibility contract.",
            )
        compatibility.validate(f"server:{family}:params", params)
        if not isinstance(params, dict):
            raise AppServerError(
                "app_server_message_invalid",
                "App Server callback parameters are invalid.",
            )
        source_fingerprint = _digest(
            {"generation": self._generation, "id": raw_id, "family": family, "params": params}
        )
        request_id = source_fingerprint[:32]
        record = PendingServerRequest(
            request_id=request_id,
            source_fingerprint=source_fingerprint,
            raw_id=raw_id,
            family=family,
            params=params,
            received_at=_observed_at(),
        )
        with self._state_lock:
            if len(self._server_requests) >= MAX_PENDING_SERVER_REQUESTS:
                evictable = next(
                    (
                        key
                        for key, candidate in self._server_requests.items()
                        if candidate.status != "pending"
                    ),
                    None,
                )
                if evictable is not None:
                    self._server_requests.pop(evictable)
                else:
                    self._write_message(
                        {
                            "id": raw_id,
                            "error": {
                                "code": -32000,
                                "message": "Dashboard callback buffer is full.",
                            },
                        }
                    )
                    return
            self._server_requests[request_id] = record
        self.events.publish("request", self._server_request_projection(record))

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
                "turn_id": _bounded(turn.get("id"), 256) if isinstance(turn, Mapping) else None,
                "status": _bounded(turn.get("status"), 80) if isinstance(turn, Mapping) else None,
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

    def _server_request_projection(self, request: PendingServerRequest) -> dict[str, Any]:
        params = request.params
        details: dict[str, Any]
        if request.family == "command_approval":
            details = {
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
            generation = self._generation
        if request is None:
            raise AppServerError(
                "task_request_not_found",
                "The task request is no longer available.",
                status=404,
            )
        if request.status != "pending" or request.source_fingerprint != source_fingerprint:
            raise AppServerError(
                "task_request_stale",
                "The task request changed, completed, or was already answered.",
                status=409,
            )
        if request.family in {"command_approval", "file_approval"}:
            if set(response) != {"decision"} or response.get("decision") not in APPROVAL_DECISIONS:
                raise AppServerError(
                    "invalid_approval_response",
                    "Approval response requires one supported decision.",
                    status=400,
                )
            result: dict[str, Any] = {"decision": response["decision"]}
        else:
            if set(response) != {"answers"} or not isinstance(response.get("answers"), Mapping):
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
                    or any(not isinstance(item, str) or not item or len(item) > 2_000 for item in value)
                ):
                    raise AppServerError(
                        "invalid_input_response",
                        "Each current question requires one to five bounded text answers.",
                        status=400,
                    )
                answers[str(key)] = {"answers": list(value)}
            result = {"answers": answers}
        compatibility = self._compatibility
        if compatibility is None:
            raise AppServerError(
                "app_server_contract_unavailable",
                "App Server compatibility schemas are unavailable.",
            )
        compatibility.validate(f"server:{request.family}:response", result)
        with self._state_lock:
            if generation != self._generation or request.status != "pending":
                raise AppServerError(
                    "task_request_stale",
                    "The task request became stale before the response was sent.",
                    status=409,
                )
            request.status = "responded"
        try:
            self._write_message({"id": request.raw_id, "result": result})
        except AppServerError:
            with self._state_lock:
                request.status = "stale"
            raise
        projection = self._server_request_projection(request)
        self.events.publish("request_resolved", projection)
        return projection

    def pending_requests(self) -> list[dict[str, Any]]:
        with self._state_lock:
            records = [record for record in self._server_requests.values() if record.status == "pending"]
        return [self._server_request_projection(record) for record in records]

    def feature_matrix(self) -> list[dict[str, Any]]:
        with self._state_lock:
            available = self._status == "available" and self._protocol_status == "compatible"
            compatibility = self._compatibility
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
        rows: list[dict[str, Any]] = []
        for capability, required_schemas in FEATURE_SCHEMA_KEYS.items():
            schema_ready = compatibility is not None and all(
                key in compatibility.validators for key in required_schemas
            )
            capability_available = available and schema_ready
            rows.append(
                {
                    "capability": capability,
                    "status": "supported" if capability_available else "unavailable",
                    "exposure": "owner-gated" if capability in owner_gated else "read",
                    "reason": (
                        "The adapter supports this method; dashboard controls require a registered owner workflow."
                        if capability_available and capability in owner_gated
                        else None
                        if capability_available
                        else "The exact capability schema is unavailable."
                        if available
                        else "The exact App Server compatibility gate is not available."
                    ),
                }
            )
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
                    "reason": "Raw App Server methods and payloads are never exposed.",
                },
            ]
        )
        return rows

    def integration_state(self) -> dict[str, Any]:
        with self._state_lock:
            compatibility = self._compatibility
            process = self._process
            state = {
                "status": self._status,
                "protocol_status": self._protocol_status,
                "cli": {
                    "command": list(compatibility.command) if compatibility else None,
                    "version": compatibility.cli_version if compatibility else None,
                    "expected_version": self._expected("cli_version"),
                },
                "schema": {
                    "semantic_manifest_sha256": compatibility.schema_root if compatibility else None,
                    "expected_semantic_manifest_sha256": self._expected(
                        "semantic_manifest_sha256"
                    ),
                    "file_count": compatibility.schema_count if compatibility else None,
                    "expected_file_count": self._expected("generated_file_count"),
                },
                "transport": {
                    "kind": "stdio",
                    "child_running": bool(process is not None and process.poll() is None),
                },
                "reconnect": {
                    "failure_count": self._failure_count,
                    "retry_after_ms": max(
                        0,
                        min(30_000, round((self._backoff_until - time.monotonic()) * 1_000)),
                    ),
                    "maximum_delay_ms": 30_000,
                },
                "features": self.feature_matrix(),
                "pending_requests": len(
                    [item for item in self._server_requests.values() if item.status == "pending"]
                ),
                "last_error": dict(self._last_error) if self._last_error else None,
                "restart_count": self._restart_count,
                "connection_generation": self._generation,
                "ignored_protocol_messages": self._ignored_notifications,
                "observed_at": _observed_at(),
            }
        state["revision"] = _digest(state)
        return state

    def _expected(self, field: str) -> Any:
        try:
            config = json.loads(self.compatibility_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return config.get(field)

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

    @staticmethod
    def _project(projects: Sequence[ProjectRecord], project_id: str) -> ProjectRecord:
        matches = [project for project in projects if project.id == project_id and not project.archived]
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
        projected = self.read_task(projects, task_id, include_turns=include_turns)["task"]
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
            (turn for turn in task["turns"] if turn["id"] == turn_id and turn["status"] == "inProgress"),
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
            (turn for turn in task["turns"] if turn["id"] == turn_id and turn["status"] == "inProgress"),
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
            _bounded(item, 80) for item in value.get("activeFlags", []) if isinstance(item, str)
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
        return {"status": "bound", "project_id": candidates[0], "candidates": candidates}
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
    status: str | None = None
    if item_type in {"agentMessage", "plan"}:
        summary = _bounded(item.get("text"))
    elif item_type == "userMessage":
        texts = [
            value.get("text")
            for value in item.get("content", [])
            if isinstance(value, Mapping)
            and value.get("type") == "text"
            and isinstance(value.get("text"), str)
        ]
        summary = _bounded("\n".join(texts))
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
        summary_values = item.get("summary") if isinstance(item.get("summary"), list) else []
        summary = _bounded(" ".join(str(value) for value in summary_values), 2_000)
    return {
        "id": _bounded(item.get("id"), 256) or "unknown",
        "type": item_type,
        "status": status,
        "summary": summary,
    }


def _turn_projection(turn: Mapping[str, Any]) -> dict[str, Any]:
    items = turn.get("items") if isinstance(turn.get("items"), list) else []
    selected = items[-MAX_ITEMS_PER_TURN:]
    return {
        "id": _bounded(turn.get("id"), 256) or "unknown",
        "status": _bounded(turn.get("status"), 100) or "unknown",
        "started_at": _timestamp(turn.get("startedAt")),
        "completed_at": _timestamp(turn.get("completedAt")),
        "duration_ms": turn.get("durationMs") if isinstance(turn.get("durationMs"), int) else None,
        "items_view": _bounded(turn.get("itemsView"), 100) or "full",
        "items": [_item_projection(item) for item in selected if isinstance(item, Mapping)],
        "items_truncated": len(items) > len(selected),
        "error": _bounded(turn.get("error"), 1_000) if turn.get("error") else None,
    }


def _task_projection(thread: Mapping[str, Any], projects: Sequence[ProjectRecord]) -> dict[str, Any]:
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
        "turns": [_turn_projection(turn) for turn in selected if isinstance(turn, Mapping)],
        "turns_truncated": len(turns) > len(selected),
    }
