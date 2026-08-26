from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ProviderError
from .provider_provenance import QualifiedClientPin, load_qualified_client
from .providers import ProviderObservation, ProviderRequest, _require_bounded_prompt


@dataclass
class _LiveSession:
    execution_id: str
    client: Any
    session: Any
    thread_id: str
    turn_id: str
    handle: dict[str, Any]
    event_task: asyncio.Task[None] | None = None
    callback_task: asyncio.Task[None] | None = None
    event_count: int = 0
    rejected_callback_count: int = 0
    error: dict[str, Any] = field(default_factory=dict)


class _AsyncOwner:
    def __init__(self, shutdown: Any, *, timeout_seconds: float) -> None:
        self._shutdown = shutdown
        self._timeout_seconds = timeout_seconds
        self._ready = threading.Event()
        self._closed = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = threading.Thread(
            target=self._run,
            name="software-factory-codex-app-server",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise ProviderError("codex app-server event-loop owner did not start")

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
            raise ProviderError("codex app-server provider is closed")
        future = asyncio.run_coroutine_threadsafe(awaitable, self._loop)
        try:
            return future.result(timeout=self._timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise ProviderError("codex app-server operation exceeded its bound") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        failure: Exception | None = None
        if self._loop is not None:
            future = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
            try:
                future.result(timeout=self._timeout_seconds)
            except concurrent.futures.TimeoutError as exc:
                future.cancel()
                failure = ProviderError("codex app-server cleanup exceeded its bound")
                failure.__cause__ = exc
            except Exception as exc:
                failure = ProviderError(
                    f"codex app-server cleanup failed closed: {type(exc).__name__}"
                )
                failure.__cause__ = exc
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise ProviderError("codex app-server event-loop owner did not stop")
        if failure is not None:
            raise failure


class CodexAppServerProvider:
    """Factory adapter over the exact qualified shared app-server client wheel.

    The provider owns transport/process lifecycle and external thread/turn mapping.
    Factory still owns reservations, assignments, callbacks, retry budgets, QA, and
    acceptance; provider turn completion is only submitted evidence.
    """

    def __init__(
        self,
        *,
        wheel_path: str | Path,
        codex_executable: str | Path | None = None,
        owner_key: str = "standalone",
        max_prompt_bytes: int = 256 * 1024,
        max_events: int = 256,
        max_callbacks: int = 8,
        operation_timeout_seconds: float = 60.0,
    ) -> None:
        if not owner_key.strip():
            raise ValueError("owner_key is required")
        if max_prompt_bytes <= 0:
            raise ValueError("max_prompt_bytes must be positive")
        if max_events <= 0 or max_callbacks <= 0:
            raise ValueError("provider event and callback bounds must be positive")
        if operation_timeout_seconds <= 0:
            raise ValueError("operation_timeout_seconds must be positive")
        self._client_module, self.pin = load_qualified_client(wheel_path)
        self._codex_executable = codex_executable
        self._max_prompt_bytes = max_prompt_bytes
        self._max_events = max_events
        self._max_callbacks = max_callbacks
        self._operation_timeout_seconds = operation_timeout_seconds
        self.process_owner_key = f"codex-app-server:{owner_key}"
        self._sessions: dict[str, _LiveSession] = {}
        self._owner: _AsyncOwner | None = None
        self._owner_lock = threading.Lock()
        self._closed = False

    def _runtime(self) -> _AsyncOwner:
        with self._owner_lock:
            if self._closed:
                raise ProviderError("codex app-server provider is closed")
            if self._owner is None:
                self._owner = _AsyncOwner(
                    self._shutdown,
                    timeout_seconds=self._operation_timeout_seconds,
                )
            return self._owner

    def dispatch(self, request: ProviderRequest) -> ProviderObservation:
        _require_bounded_prompt(request, self._max_prompt_bytes)
        try:
            handle = self._runtime().call(self._dispatch(request))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"codex app-server dispatch failed closed: {type(exc).__name__}"
            ) from exc
        return ProviderObservation(
            status="running",
            external_thread_id=str(handle["thread_id"]),
            external_task_id=str(handle["turn_id"]),
            handle=handle,
        )

    def poll(self, handle: dict[str, Any] | Any) -> ProviderObservation:
        durable = dict(handle)
        self._verify_handle(durable)
        try:
            return self._runtime().call(self._poll(durable))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"codex app-server poll failed closed: {type(exc).__name__}"
            ) from exc

    def cancel(self, handle: dict[str, Any] | Any) -> ProviderObservation:
        durable = dict(handle)
        self._verify_handle(durable)
        try:
            return self._runtime().call(self._cancel(durable))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"codex app-server cancellation failed closed: {type(exc).__name__}"
            ) from exc

    def diagnose(self) -> dict[str, Any]:
        """Run one bounded, non-generative compatibility and thread-list probe."""

        try:
            return dict(self._runtime().call(self._diagnose()))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"codex app-server diagnostic failed closed: {type(exc).__name__}"
            ) from exc

    def close(self) -> None:
        with self._owner_lock:
            if self._closed:
                return
            self._closed = True
            owner = self._owner
            self._owner = None
        if owner is not None:
            owner.close()

    def _pin_handle(self) -> dict[str, str]:
        record = self.pin.record
        return {
            "producer_revision": str(record["qualified_producer_revision"]),
            "accepted_source_commit": str(record["accepted_source_commit"]),
            "package_tree_object": str(record["package_tree_object"]),
            "wheel_sha256": str(record["wheel_sha256"]),
            "protocol_schema_root": str(record["protocol"]["schema_tree_root_sha256"]),
            "selected_surface_root": str(record["protocol"]["selected_surface_root_sha256"]),
        }

    def _verify_handle(self, handle: dict[str, Any]) -> None:
        required = {
            "execution_id",
            "thread_id",
            "turn_id",
            "workspace_path",
            *self._pin_handle(),
        }
        if any(not isinstance(handle.get(key), str) or not handle[key] for key in required):
            raise ProviderError("codex app-server handle is missing immutable identity")
        for key, value in self._pin_handle().items():
            if handle.get(key) != value:
                raise ProviderError("codex app-server handle is bound to stale producer material")

    async def _connect(self) -> tuple[Any, Any]:
        client = self._client_module
        binary = client.resolve_codex_binary(self._codex_executable)
        compatibility = client.inspect_compatibility(binary)
        limits = client.ClientLimits(
            max_message_bytes=8 * 1024 * 1024,
            max_pending_calls=16,
            max_events=self._max_events,
            max_callbacks=self._max_callbacks,
            max_backoff_seconds=5.0,
        )
        owner = await client.AppServerClient.connect(
            client.StdioTransport(binary), compatibility, limits=limits
        )
        try:
            session = await owner.initialize(client.ClientIdentity("software-factory", "2.0"))
        except Exception:
            await owner.close()
            raise
        return owner, session

    async def _diagnose(self) -> dict[str, Any]:
        client = self._client_module
        binary = client.resolve_codex_binary(self._codex_executable)
        compatibility = client.inspect_compatibility(binary)
        limits = client.ClientLimits(
            max_message_bytes=8 * 1024 * 1024,
            max_pending_calls=2,
            max_events=1,
            max_callbacks=1,
            max_backoff_seconds=1.0,
        )
        owner = await client.AppServerClient.connect(
            client.StdioTransport(binary), compatibility, limits=limits
        )
        try:
            session = await owner.initialize(
                client.ClientIdentity("software-factory-diagnostic", "2.0")
            )
            response = await session.list_threads(
                client.ThreadListParams(limit=1),
                timeout=self._operation_timeout_seconds,
            )
            return {
                "operation": "thread/list",
                "generative_turn_started": False,
                "observed_thread_count": len(response.data),
                "binary_path": str(compatibility.binary.path),
                "binary_sha256": str(compatibility.binary.sha256),
                "codex_version": str(compatibility.binary.reported_version),
                "producer_revision": str(self.pin.record["qualified_producer_revision"]),
                "wheel_sha256": str(self.pin.record["wheel_sha256"]),
                "schema_tree_root_sha256": str(compatibility.target.schema_tree_root_sha256),
                "selected_surface_root_sha256": str(
                    compatibility.target.selected_surface_root_sha256
                ),
            }
        finally:
            await owner.close()

    async def _dispatch(self, request: ProviderRequest) -> dict[str, Any]:
        if request.execution_id in self._sessions:
            raise ProviderError("codex app-server execution already has a live owner")
        client_owner, session = await self._connect()
        workspace_path = str(request.workspace_path.resolve())
        attribution = (
            "Software Factory assignment. Provider completion is evidence only, never QA or "
            f"acceptance. execution={request.execution_id} assignment={request.assignment_id} "
            f"work={request.work_item_id} role={request.role}."
        )
        try:
            thread = await session.start_thread(
                self._client_module.ThreadStartParams(
                    approvalPolicy="never",
                    cwd=workspace_path,
                    developerInstructions=attribution,
                    sandbox="workspace-write",
                ),
                timeout=self._operation_timeout_seconds,
            )
            thread_id = str(thread.thread.id)
            turn = await session.start_turn(
                self._client_module.TurnStartParams(
                    approvalPolicy="never",
                    cwd=workspace_path,
                    input=({"type": "text", "text": request.prompt},),
                    threadId=thread_id,
                ),
                timeout=self._operation_timeout_seconds,
            )
            turn_id = str(turn.turn.id)
        except Exception:
            await client_owner.close()
            raise
        handle: dict[str, Any] = {
            "provider": "codex-app-server",
            "execution_id": request.execution_id,
            "assignment_id": request.assignment_id,
            "work_item_id": request.work_item_id,
            "thread_id": thread_id,
            "turn_id": turn_id,
            "workspace_path": workspace_path,
            "lease_generation": request.lease_generation,
            **self._pin_handle(),
        }
        record = _LiveSession(
            execution_id=request.execution_id,
            client=client_owner,
            session=session,
            thread_id=thread_id,
            turn_id=turn_id,
            handle=handle,
        )
        self._sessions[request.execution_id] = record
        self._start_drainers(record)
        return handle

    def _start_drainers(self, record: _LiveSession) -> None:
        record.event_task = asyncio.create_task(self._drain_events(record))
        record.callback_task = asyncio.create_task(self._drain_callbacks(record))

    async def _drain_events(self, record: _LiveSession) -> None:
        try:
            async for _event in record.session.events():
                record.event_count += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            record.error = {"phase": "events", "error_type": type(exc).__name__}

    async def _drain_callbacks(self, record: _LiveSession) -> None:
        try:
            async for callback in record.session.callbacks():
                name = type(callback).__name__
                if name == "CommandExecutionApprovalCallback":
                    response = self._client_module.CommandExecutionRequestApprovalResponse(
                        decision="decline"
                    )
                elif name == "FileChangeApprovalCallback":
                    response = self._client_module.FileChangeRequestApprovalResponse(
                        decision="decline"
                    )
                else:
                    record.error = {
                        "phase": "callback",
                        "error_type": "ExternalInputRequired",
                    }
                    await record.session.interrupt_turn(
                        self._client_module.TurnInterruptParams(
                            threadId=record.thread_id,
                            turnId=record.turn_id,
                        ),
                        timeout=self._operation_timeout_seconds,
                    )
                    return
                await callback.respond(response)
                record.rejected_callback_count += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            record.error = {"phase": "callbacks", "error_type": type(exc).__name__}

    async def _reattach(self, handle: dict[str, Any]) -> _LiveSession:
        execution_id = str(handle["execution_id"])
        existing = self._sessions.get(execution_id)
        if existing is not None:
            return existing
        client_owner, session = await self._connect()
        try:
            await session.resume_thread(
                self._client_module.ThreadResumeParams(
                    approvalPolicy="never",
                    cwd=str(handle["workspace_path"]),
                    threadId=str(handle["thread_id"]),
                ),
                timeout=self._operation_timeout_seconds,
            )
        except Exception:
            await client_owner.close()
            raise
        record = _LiveSession(
            execution_id=execution_id,
            client=client_owner,
            session=session,
            thread_id=str(handle["thread_id"]),
            turn_id=str(handle["turn_id"]),
            handle=handle,
        )
        self._sessions[execution_id] = record
        self._start_drainers(record)
        return record

    @staticmethod
    def _status_value(value: Any) -> str:
        return str(getattr(value, "value", value))

    async def _poll(self, handle: dict[str, Any]) -> ProviderObservation:
        record = await self._reattach(handle)
        if record.error:
            error = dict(record.error)
            await self._close_record(record)
            return ProviderObservation(status="failed", handle=handle, error=error)
        response = await record.session.read_thread(
            self._client_module.ThreadReadParams(
                includeTurns=True,
                threadId=record.thread_id,
            ),
            timeout=self._operation_timeout_seconds,
        )
        if record.error:
            error = dict(record.error)
            await self._close_record(record)
            return ProviderObservation(status="failed", handle=handle, error=error)
        turn = next(
            (value for value in response.thread.turns if str(value.id) == record.turn_id),
            None,
        )
        if turn is None:
            return ProviderObservation(
                status="running",
                external_thread_id=record.thread_id,
                external_task_id=record.turn_id,
                handle=handle,
            )
        status = self._status_value(turn.status)
        if status == "inProgress":
            return ProviderObservation(
                status="running",
                external_thread_id=record.thread_id,
                external_task_id=record.turn_id,
                handle=handle,
            )
        result = {
            "provider_success_only": status == "completed",
            "thread_id": record.thread_id,
            "turn_id": record.turn_id,
            "turn_status": status,
            "item_count": len(turn.items),
            "event_count": record.event_count,
            "rejected_callback_count": record.rejected_callback_count,
        }
        await self._close_record(record)
        return ProviderObservation(
            status="succeeded" if status == "completed" else "failed",
            external_thread_id=record.thread_id,
            external_task_id=record.turn_id,
            handle=handle,
            result=result if status == "completed" else {},
            error={} if status == "completed" else result,
        )

    async def _cancel(self, handle: dict[str, Any]) -> ProviderObservation:
        record = await self._reattach(handle)
        await record.session.interrupt_turn(
            self._client_module.TurnInterruptParams(
                threadId=record.thread_id,
                turnId=record.turn_id,
            ),
            timeout=self._operation_timeout_seconds,
        )
        await self._close_record(record)
        return ProviderObservation(
            status="cancelled",
            external_thread_id=record.thread_id,
            external_task_id=record.turn_id,
            handle=handle,
        )

    async def _close_record(self, record: _LiveSession) -> None:
        self._sessions.pop(record.execution_id, None)
        current = asyncio.current_task()
        tasks = [
            task
            for task in (record.event_task, record.callback_task)
            if task is not None and task is not current
        ]
        for task in tasks:
            task.cancel()
        try:
            await record.client.close()
        finally:
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _shutdown(self) -> None:
        for record in list(self._sessions.values()):
            await self._close_record(record)


__all__ = ["CodexAppServerProvider", "QualifiedClientPin"]
