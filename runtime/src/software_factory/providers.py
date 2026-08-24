from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .util import atomic_write, canonical_json, ensure_within, utc_now


@dataclass(frozen=True)
class ProviderRequest:
    execution_id: str
    mission_id: str
    work_item_id: str
    assignment_id: str
    workspace_id: str
    workspace_path: Path
    lease_generation: int
    role: str
    prompt: str
    callback_token: str
    limits: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderObservation:
    status: str
    external_thread_id: str | None = None
    external_task_id: str | None = None
    handle: Mapping[str, Any] = field(default_factory=dict)
    result: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] = field(default_factory=dict)
    usage: Mapping[str, Any] = field(default_factory=dict)
    stdout: bytes | None = None
    stderr: bytes | None = None

    def __post_init__(self) -> None:
        if self.status not in {"running", "succeeded", "failed", "lost", "cancelled"}:
            raise ValueError(f"unsupported provider status: {self.status}")


class ProviderAdapter(Protocol):
    def dispatch(self, request: ProviderRequest) -> ProviderObservation: ...

    def poll(self, handle: Mapping[str, Any]) -> ProviderObservation: ...

    def cancel(self, handle: Mapping[str, Any]) -> ProviderObservation: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderAdapter] = {}

    def register(self, key: str, provider: ProviderAdapter) -> None:
        normalized = key.strip()
        if not normalized:
            raise ValueError("provider key is required")
        if normalized in self._providers:
            raise ValueError(f"provider is already registered: {normalized}")
        self._assert_process_owner_available(provider)
        self._providers[normalized] = provider

    def replace(self, key: str, provider: ProviderAdapter) -> None:
        normalized = key.strip()
        if not normalized:
            raise ValueError("provider key is required")
        self._assert_process_owner_available(provider, replacing=normalized)
        previous = self._providers.get(normalized)
        if previous is not None and previous is not provider:
            close = getattr(previous, "close", None)
            if callable(close):
                close()
        self._providers[normalized] = provider

    def get(self, key: str) -> ProviderAdapter:
        try:
            return self._providers[key]
        except KeyError as exc:
            raise KeyError(f"provider is not registered: {key}") from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def _assert_process_owner_available(
        self, provider: ProviderAdapter, *, replacing: str | None = None
    ) -> None:
        owner_key = getattr(provider, "process_owner_key", None)
        if owner_key is None:
            return
        if not isinstance(owner_key, str) or not owner_key.strip():
            raise ValueError("provider process_owner_key must be a nonempty string")
        for key, registered in self._providers.items():
            if key == replacing or registered is provider:
                continue
            if getattr(registered, "process_owner_key", None) == owner_key:
                raise ValueError(f"provider process owner is already registered: {owner_key}")

    def close(self) -> None:
        closed: set[int] = set()
        failures: list[str] = []
        providers = tuple(self._providers.values())
        self._providers.clear()
        for provider in providers:
            if id(provider) in closed:
                continue
            closed.add(id(provider))
            close = getattr(provider, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception as exc:
                failures.append(type(exc).__name__)
        if failures:
            raise RuntimeError(f"provider cleanup failed: {','.join(failures)}")


class DeterministicProvider:
    """Controlled provider used by integration tests and local dogfood.

    The handler receives the exact durable request and returns an observed provider
    result. It is intentionally explicit rather than pretending a model assertion is
    independent evidence.
    """

    def __init__(
        self,
        handler: Callable[[ProviderRequest], ProviderObservation] | None = None,
        *,
        max_prompt_bytes: int = 256 * 1024,
    ) -> None:
        if max_prompt_bytes <= 0:
            raise ValueError("max_prompt_bytes must be positive")
        self.handler = handler or (lambda request: ProviderObservation(status="running"))
        self.max_prompt_bytes = max_prompt_bytes
        self.requests: list[ProviderRequest] = []
        self._observations: dict[str, ProviderObservation] = {}

    def dispatch(self, request: ProviderRequest) -> ProviderObservation:
        _require_bounded_prompt(request, self.max_prompt_bytes)
        self.requests.append(request)
        observation = self.handler(request)
        self._observations[request.execution_id] = observation
        return observation

    def set_observation(self, execution_id: str, observation: ProviderObservation) -> None:
        self._observations[execution_id] = observation

    def poll(self, handle: Mapping[str, Any]) -> ProviderObservation:
        execution_id = str(handle.get("execution_id") or "")
        return self._observations.get(execution_id, ProviderObservation(status="lost"))

    def cancel(self, handle: Mapping[str, Any]) -> ProviderObservation:
        execution_id = str(handle.get("execution_id") or "")
        observation = ProviderObservation(status="cancelled")
        if execution_id:
            self._observations[execution_id] = observation
        return observation


_RUNNER = r"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

status_path = Path(sys.argv[1])
stdout_path = Path(sys.argv[2])
stderr_path = Path(sys.argv[3])
command_path = Path(sys.argv[4])
prompt_path = Path(sys.argv[5])
workspace = Path(sys.argv[6])
command = json.loads(command_path.read_text(encoding="utf-8"))
with prompt_path.open("rb") as prompt, stdout_path.open("wb") as out, stderr_path.open("wb") as err:
    process = subprocess.run(command, cwd=workspace, stdin=prompt, stdout=out, stderr=err, check=False)
value = {
    "status": "succeeded" if process.returncode == 0 else "failed",
    "exit_code": process.returncode,
    "finished_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
}
temporary = status_path.with_suffix(".tmp")
temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
temporary.replace(status_path)
"""


class ProcessProvider:
    """Restart-observable process provider with durable status/output files."""

    def __init__(
        self,
        state_root: str | Path,
        command_builder: Callable[[ProviderRequest], Sequence[str]],
        *,
        output_limit_bytes: int = 8 * 1024 * 1024,
        max_prompt_bytes: int = 256 * 1024,
    ) -> None:
        self.state_root = Path(state_root).expanduser().resolve()
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.command_builder = command_builder
        if output_limit_bytes <= 0:
            raise ValueError("output_limit_bytes must be positive")
        if max_prompt_bytes <= 0:
            raise ValueError("max_prompt_bytes must be positive")
        self.output_limit_bytes = output_limit_bytes
        self.max_prompt_bytes = max_prompt_bytes
        self.process_owner_key = f"process-provider:{self.state_root}"

    def _directory(self, execution_id: str) -> Path:
        directory = self.state_root / execution_id
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        return directory

    def dispatch(self, request: ProviderRequest) -> ProviderObservation:
        _require_bounded_prompt(request, self.max_prompt_bytes)
        directory = self._directory(request.execution_id)
        command = [str(value) for value in self.command_builder(request)]
        if not command or not command[0]:
            raise ValueError("provider command is empty")
        command_path = directory / "command.json"
        prompt_path = directory / "prompt.txt"
        status_path = directory / "status.json"
        stdout_path = directory / "stdout.log"
        stderr_path = directory / "stderr.log"
        atomic_write(command_path, (canonical_json(command) + "\n").encode("utf-8"))
        atomic_write(prompt_path, request.prompt.encode("utf-8"))
        status_path.unlink(missing_ok=True)
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                _RUNNER,
                str(status_path),
                str(stdout_path),
                str(stderr_path),
                str(command_path),
                str(prompt_path),
                str(request.workspace_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        handle = {
            "execution_id": request.execution_id,
            "pid": process.pid,
            "status_path": str(status_path),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "command_path": str(command_path),
            "started_at": utc_now(),
        }
        return ProviderObservation(
            status="running",
            external_task_id=str(process.pid),
            handle=handle,
        )

    def _handle_path(self, value: Any) -> Path:
        path = ensure_within(Path(str(value)).resolve(), self.state_root)
        if path.is_symlink():
            raise ValueError("provider handle path may not be a symlink")
        return path

    def _read_output(self, value: Any) -> bytes:
        path = self._handle_path(value)
        if not path.exists():
            return b""
        if not path.is_file():
            raise ValueError("provider output is not a regular file")
        size = path.stat().st_size
        if size > self.output_limit_bytes:
            raise ValueError("provider output exceeds configured limit")
        return path.read_bytes()

    @staticmethod
    def _alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def poll(self, handle: Mapping[str, Any]) -> ProviderObservation:
        status_path = self._handle_path(handle["status_path"])
        if status_path.exists():
            if not status_path.is_file() or status_path.stat().st_size > 64 * 1024:
                raise ValueError("provider status file is invalid")
            value = json.loads(status_path.read_text(encoding="utf-8"))
            if value.get("status") not in {"succeeded", "failed"}:
                raise ValueError("provider status file has unsupported state")
            stdout = self._read_output(handle["stdout_path"])
            stderr = self._read_output(handle["stderr_path"])
            result = {
                "exit_code": value.get("exit_code"),
                "finished_at": value.get("finished_at"),
            }
            return ProviderObservation(
                status=str(value["status"]),
                external_task_id=str(handle.get("pid") or ""),
                handle=dict(handle),
                result=result if value["status"] == "succeeded" else {},
                error={} if value["status"] == "succeeded" else result,
                stdout=stdout,
                stderr=stderr,
            )
        pid = int(handle.get("pid") or 0)
        if pid > 0 and self._alive(pid):
            return ProviderObservation(status="running", handle=dict(handle))
        return ProviderObservation(
            status="lost",
            handle=dict(handle),
            error={"reason": "process_exited_without_status"},
        )

    def cancel(self, handle: Mapping[str, Any]) -> ProviderObservation:
        pid = int(handle.get("pid") or 0)
        if pid > 0 and self._alive(pid):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGTERM)
        return ProviderObservation(status="cancelled", handle=dict(handle))


class CodexCLIProvider(ProcessProvider):
    """Configurable Codex CLI adapter.

    Live provider validation is environment-specific. The adapter deliberately keeps
    the executable and argument prefix configurable rather than embedding host trust or
    claiming credentials are available.
    """

    def __init__(
        self,
        state_root: str | Path,
        *,
        executable: str = "codex",
        argument_prefix: Sequence[str] = ("exec", "--json", "--full-auto"),
    ) -> None:
        def command(request: ProviderRequest) -> Sequence[str]:
            return (
                executable,
                *argument_prefix,
                "-C",
                str(request.workspace_path),
                "-",
            )

        super().__init__(state_root, command)


class ExternalAgentProvider:
    """Injected external-agent lifecycle with no process or mission authority."""

    def __init__(
        self,
        *,
        dispatch: Callable[[ProviderRequest], ProviderObservation],
        poll: Callable[[Mapping[str, Any]], ProviderObservation],
        cancel: Callable[[Mapping[str, Any]], ProviderObservation],
        max_prompt_bytes: int = 256 * 1024,
    ) -> None:
        if max_prompt_bytes <= 0:
            raise ValueError("max_prompt_bytes must be positive")
        self._dispatch = dispatch
        self._poll = poll
        self._cancel = cancel
        self.max_prompt_bytes = max_prompt_bytes

    def dispatch(self, request: ProviderRequest) -> ProviderObservation:
        _require_bounded_prompt(request, self.max_prompt_bytes)
        return _require_observation(self._dispatch(request))

    def poll(self, handle: Mapping[str, Any]) -> ProviderObservation:
        return _require_observation(self._poll(dict(handle)))

    def cancel(self, handle: Mapping[str, Any]) -> ProviderObservation:
        return _require_observation(self._cancel(dict(handle)))


def _require_bounded_prompt(request: ProviderRequest, maximum: int) -> None:
    if len(request.prompt.encode("utf-8")) > maximum:
        raise ValueError("provider prompt exceeds the configured byte limit")


def _require_observation(value: object) -> ProviderObservation:
    if not isinstance(value, ProviderObservation):
        raise TypeError("provider callback must return ProviderObservation")
    return value
