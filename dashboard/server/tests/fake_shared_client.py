from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


def fake_thread(
    cwd: str,
    *,
    session_path: str | None = None,
    active_turn: bool = False,
    terminal_turn: bool = False,
    ephemeral: bool = False,
    turn_text: str = "Continue.",
) -> dict[str, Any]:
    turns: list[dict[str, Any]] = []
    status: dict[str, Any] = {"type": "idle"}
    if active_turn:
        status = {"type": "active", "activeFlags": []}
        turns = [
            {
                "id": "turn-active-001",
                "status": "inProgress",
                "items": [
                    {
                        "id": "item-user-001",
                        "type": "userMessage",
                        "content": [{"type": "text", "text": turn_text}],
                    }
                ],
                "startedAt": 1786279000,
            }
        ]
    elif terminal_turn:
        turns = [
            {
                "id": "turn-complete-001",
                "status": "completed",
                "items": [
                    {"id": "item-agent-001", "type": "agentMessage", "text": "Done."}
                ],
                "startedAt": 1786279000,
                "completedAt": 1786279001,
            }
        ]
    return {
        "id": "task-fake-001",
        "sessionId": "task-fake-001",
        "path": session_path,
        "name": "Fake task",
        "preview": "Bounded fake task",
        "ephemeral": ephemeral,
        "modelProvider": "openai",
        "createdAt": 1786278000,
        "updatedAt": 1786279000,
        "status": status,
        "cwd": cwd,
        "cliVersion": "0.147.0",
        "source": "appServer",
        "turns": turns,
    }


class FakeModel:
    def __init__(self, value: Mapping[str, Any] | None = None) -> None:
        self.value = dict(value or {})

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> FakeModel:
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.value)


class ClientIdentity:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version


class ClientLimits:
    def __init__(self, **values: Any) -> None:
        self.values = values


class StdioTransport:
    def __init__(self, binary: Any) -> None:
        self.binary = binary


class RemoteRpcError(RuntimeError):
    pass


class InitializationError(RuntimeError):
    pass


class _Callback:
    def __init__(self, params: Mapping[str, Any]) -> None:
        self.params = FakeModel(params)
        self.response: dict[str, Any] | None = None

    async def respond(self, response: FakeModel) -> None:
        self.response = response.to_dict()


class CommandExecutionApprovalCallback(_Callback):
    pass


class FileChangeApprovalCallback(_Callback):
    pass


class UserInputCallback(_Callback):
    pass


def _named_model(name: str) -> type[FakeModel]:
    return type(name, (FakeModel,), {})


@dataclass(frozen=True)
class FakePin:
    record: dict[str, Any]


class FakeSession:
    def __init__(self, module: FakeSharedClientModule) -> None:
        self.module = module
        self.active_turn = module.mode in {
            "active",
            "approval",
            "user-input",
            "large-task-response",
        }
        self.terminal_turn = module.mode == "terminal"
        self.ephemeral = False
        self.turn_text = "Continue."
        self.closed = False
        self.event_queue: asyncio.Queue[Any] = asyncio.Queue()
        self.callback_queue: asyncio.Queue[Any] = asyncio.Queue()
        self.session_path = self._session_path()

    def _session_path(self) -> Path:
        directory = self.module.codex_home / "sessions" / "2026" / "08" / "10"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "rollout-2026-08-10T00-00-00-task-fake-001.jsonl"
        if not path.exists():
            path.write_text(
                '{"type":"session_meta","payload":{"id":"task-fake-001"}}\n'
                '{"type":"turn_context","payload":{"model":"gpt-5.6-sol","effort":"xhigh"}}\n',
                encoding="utf-8",
            )
            path.chmod(0o600)
        return path

    def _thread(
        self, *, cwd: str | None = None, turn_text: str | None = None
    ) -> dict[str, Any]:
        value = fake_thread(
            cwd or str(self.module.cwd),
            session_path=str(self.session_path),
            active_turn=self.active_turn,
            terminal_turn=self.terminal_turn,
            ephemeral=self.ephemeral,
            turn_text=turn_text or self.turn_text,
        )
        value["cliVersion"] = "0.147.0"
        return value

    async def initialize(self) -> None:
        if self.module.mode == "approval":
            await self.callback_queue.put(
                CommandExecutionApprovalCallback(
                    {
                        "threadId": "task-fake-001",
                        "turnId": "turn-active-001",
                        "itemId": "item-command-001",
                        "command": "git status --short",
                        "cwd": str(self.module.cwd),
                        "reason": "Inspect exact state",
                        "startedAtMs": 1,
                    }
                )
            )
        elif self.module.mode == "user-input":
            await self.callback_queue.put(
                UserInputCallback(
                    {
                        "threadId": "task-fake-001",
                        "turnId": "turn-active-001",
                        "itemId": "item-input-001",
                        "questions": [
                            {
                                "id": "choice",
                                "header": "Choice",
                                "question": "Which bounded option?",
                                "options": [
                                    {
                                        "label": "First",
                                        "description": "Use the first option.",
                                    }
                                ],
                            }
                        ],
                    }
                )
            )

    async def list_threads(self, params: FakeModel, *, timeout: float) -> FakeModel:
        if self.module.mode == "timeout":
            await asyncio.sleep(timeout * 10)
        return FakeModel(
            {"data": [self._thread()], "nextCursor": None, "backwardsCursor": None}
        )

    async def read_thread(self, params: FakeModel, *, timeout: float) -> FakeModel:
        if self.module.mode == "task-not-found":
            raise RemoteRpcError("thread not found")
        text = (
            "x" * (5 * 1024 * 1024)
            if self.module.mode == "large-task-response"
            else None
        )
        return FakeModel({"thread": self._thread(turn_text=text)})

    async def start_thread(self, params: FakeModel, *, timeout: float) -> FakeModel:
        self.ephemeral = bool(params.value.get("ephemeral"))
        cwd = str(params.value.get("cwd") or self.module.cwd)
        return FakeModel({"thread": self._thread(cwd=cwd)})

    async def resume_thread(self, params: FakeModel, *, timeout: float) -> FakeModel:
        return FakeModel(
            {
                "thread": self._thread(
                    cwd=str(params.value.get("cwd") or self.module.cwd)
                )
            }
        )

    async def start_turn(self, params: FakeModel, *, timeout: float) -> FakeModel:
        if self.module.mode == "turn-start-fails":
            raise RemoteRpcError("focused turn start failure")
        self.active_turn = True
        raw_input = params.value.get("input")
        if (
            isinstance(raw_input, list)
            and raw_input
            and isinstance(raw_input[0], Mapping)
        ):
            self.turn_text = str(raw_input[0].get("text", ""))
        turn = self._thread()["turns"][0]
        await self.event_queue.put(
            self.module.TurnStartedNotification.from_dict(
                {"threadId": "task-fake-001", "turn": turn}
            )
        )
        return FakeModel({"turn": turn})

    async def steer_turn(self, params: FakeModel, *, timeout: float) -> FakeModel:
        return FakeModel({"turnId": params.value["expectedTurnId"]})

    async def interrupt_turn(self, params: FakeModel, *, timeout: float) -> FakeModel:
        self.active_turn = False
        return FakeModel({})

    async def events(self):
        while not self.closed:
            value = await self.event_queue.get()
            if value is None:
                return
            yield value

    async def callbacks(self):
        while not self.closed:
            value = await self.callback_queue.get()
            if value is None:
                return
            yield value

    async def close(self) -> None:
        self.closed = True
        await self.event_queue.put(None)
        await self.callback_queue.put(None)


class FakeOwner:
    def __init__(self, module: FakeSharedClientModule) -> None:
        self.module = module
        self.session: FakeSession | None = None

    async def initialize(self, identity: ClientIdentity) -> FakeSession:
        if self.module.mode == "malformed":
            raise InitializationError("malformed initialization response")
        self.session = FakeSession(self.module)
        await self.session.initialize()
        self.module.last_session = self.session
        return self.session

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()


class _Connector:
    def __init__(self, module: FakeSharedClientModule) -> None:
        self.module = module

    async def connect(
        self, transport: StdioTransport, compatibility: Any, *, limits: Any
    ) -> FakeOwner:
        return FakeOwner(self.module)


class FakeSharedClientModule:
    def __init__(self, *, cwd: Path, codex_home: Path, mode: str = "normal") -> None:
        self.cwd = cwd.resolve()
        self.codex_home = codex_home.resolve()
        self.mode = mode
        self.last_session: FakeSession | None = None
        self.ClientLimits = ClientLimits
        self.ClientIdentity = ClientIdentity
        self.StdioTransport = StdioTransport
        self.AppServerClient = _Connector(self)
        for name in (
            "ThreadListParams",
            "ThreadReadParams",
            "ThreadStartParams",
            "ThreadResumeParams",
            "TurnStartParams",
            "TurnSteerParams",
            "TurnInterruptParams",
            "CommandExecutionRequestApprovalResponse",
            "FileChangeRequestApprovalResponse",
            "ToolRequestUserInputResponse",
            "ThreadStartedNotification",
            "ThreadStatusChangedNotification",
            "TurnStartedNotification",
            "TurnCompletedNotification",
            "ItemStartedNotification",
            "ItemCompletedNotification",
            "ErrorNotification",
            "WarningNotification",
        ):
            setattr(self, name, _named_model(name))

    @staticmethod
    def resolve_codex_binary(executable: Any) -> Any:
        return SimpleNamespace(
            path=Path(executable or "/usr/bin/true"),
            sha256="f" * 64,
            reported_version="0.147.0",
        )

    @staticmethod
    def inspect_compatibility(binary: Any) -> Any:
        return SimpleNamespace(
            binary=binary,
            target=SimpleNamespace(
                schema_tree_root_sha256="e" * 64,
                selected_surface_root_sha256="9" * 64,
            ),
        )


def fake_client_binding(
    root: Path,
    cwd: Path,
    *,
    mode: str = "normal",
) -> tuple[Path, Path, Any, FakeSharedClientModule]:
    wheel = (root / "fake-qualified-client.whl").resolve()
    wheel.touch(exist_ok=True)
    codex_home = (root / "fake-codex-home").resolve()
    codex_home.mkdir(exist_ok=True)
    module = FakeSharedClientModule(cwd=cwd, codex_home=codex_home, mode=mode)
    pin = FakePin(
        {
            "distribution": "codex-app-server-client",
            "version": "0.1.0",
            "qualified_producer_revision": "a" * 40,
            "accepted_source_commit": "b" * 40,
            "package_tree_object": "c" * 40,
            "wheel_sha256": "d" * 64,
            "release_posture": "no-license-selected/unpublished",
            "rights_boundary": "internal exact-revision qualification only",
            "protocol": {
                "codex_version": "0.147.0",
                "schema_tree_root_sha256": "e" * 64,
                "selected_surface_root_sha256": "9" * 64,
            },
        }
    )

    def loader(_path: Path) -> tuple[Any, Any]:
        return module, pin

    return wheel, codex_home, loader, module
