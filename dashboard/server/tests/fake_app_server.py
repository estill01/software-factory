from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


CLI_VERSION = "codex-cli 0.145.0"


def object_schema(
    *,
    required: list[str] | None = None,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required or [],
        "properties": properties or {},
    }


string = {"type": "string"}
nullable_string = {"type": ["string", "null"]}
thread_status = object_schema(required=["type"], properties={"type": string})
turn = object_schema(
    required=["id", "items", "status"],
    properties={
        "id": string,
        "items": {"type": "array"},
        "status": string,
        "startedAt": {"type": ["integer", "null"]},
        "completedAt": {"type": ["integer", "null"]},
    },
)
thread = object_schema(
    required=[
        "cliVersion",
        "createdAt",
        "cwd",
        "ephemeral",
        "id",
        "modelProvider",
        "preview",
        "sessionId",
        "source",
        "status",
        "turns",
        "updatedAt",
    ],
    properties={
        "cliVersion": string,
        "createdAt": {"type": "integer"},
        "cwd": string,
        "ephemeral": {"type": "boolean"},
        "id": string,
        "modelProvider": string,
        "preview": string,
        "sessionId": string,
        "source": string,
        "status": thread_status,
        "turns": {"type": "array", "items": turn},
        "updatedAt": {"type": "integer"},
        "name": nullable_string,
    },
)


SCHEMAS: dict[str, dict[str, Any]] = {
    "JSONRPCError.json": object_schema(
        required=["id", "error"],
        properties={
            "id": {"type": ["integer", "string"]},
            "error": object_schema(
                required=["code", "message"],
                properties={"code": {"type": "integer"}, "message": string},
            ),
        },
    ),
    "v1/InitializeParams.json": object_schema(
        required=["clientInfo"], properties={"clientInfo": {"type": "object"}}
    ),
    "v1/InitializeResponse.json": object_schema(
        required=["codexHome", "platformFamily", "platformOs", "userAgent"],
        properties={
            "codexHome": string,
            "platformFamily": string,
            "platformOs": string,
            "userAgent": string,
        },
    ),
    "v2/ThreadListParams.json": object_schema(),
    "v2/ThreadListResponse.json": object_schema(
        required=["data"],
        properties={
            "data": {"type": "array", "items": thread},
            "nextCursor": nullable_string,
            "backwardsCursor": nullable_string,
        },
    ),
    "v2/ThreadReadParams.json": object_schema(
        required=["threadId"], properties={"threadId": string}
    ),
    "v2/ThreadReadResponse.json": object_schema(
        required=["thread"], properties={"thread": thread}
    ),
    "v2/ThreadStartParams.json": object_schema(),
    "v2/ThreadStartResponse.json": object_schema(
        required=["thread"], properties={"thread": thread}
    ),
    "v2/ThreadResumeParams.json": object_schema(
        required=["threadId"], properties={"threadId": string}
    ),
    "v2/ThreadResumeResponse.json": object_schema(
        required=["thread"], properties={"thread": thread}
    ),
    "v2/TurnStartParams.json": object_schema(
        required=["threadId", "input"],
        properties={"threadId": string, "input": {"type": "array", "minItems": 1}},
    ),
    "v2/TurnStartResponse.json": object_schema(
        required=["turn"], properties={"turn": turn}
    ),
    "v2/TurnSteerParams.json": object_schema(
        required=["threadId", "expectedTurnId", "input"]
    ),
    "v2/TurnSteerResponse.json": object_schema(
        required=["turnId"], properties={"turnId": string}
    ),
    "v2/TurnInterruptParams.json": object_schema(
        required=["threadId", "turnId"],
        properties={"threadId": string, "turnId": string},
    ),
    "v2/TurnInterruptResponse.json": object_schema(),
    "v2/ThreadStartedNotification.json": object_schema(
        required=["thread"], properties={"thread": thread}
    ),
    "v2/ThreadStatusChangedNotification.json": object_schema(
        required=["threadId", "status"],
        properties={"threadId": string, "status": thread_status},
    ),
    "v2/TurnStartedNotification.json": object_schema(
        required=["threadId", "turn"], properties={"threadId": string, "turn": turn}
    ),
    "v2/TurnCompletedNotification.json": object_schema(
        required=["threadId", "turn"], properties={"threadId": string, "turn": turn}
    ),
    "v2/ItemStartedNotification.json": object_schema(
        required=["threadId", "turnId", "item", "startedAtMs"]
    ),
    "v2/ItemCompletedNotification.json": object_schema(
        required=["threadId", "turnId", "item", "completedAtMs"]
    ),
    "v2/ErrorNotification.json": object_schema(
        required=["error", "threadId", "turnId", "willRetry"],
        properties={
            "error": object_schema(
                required=["message"],
                properties={
                    "message": string,
                    "codexErrorInfo": {"type": ["string", "null"]},
                },
            ),
            "threadId": string,
            "turnId": string,
            "willRetry": {"type": "boolean"},
        },
    ),
    "CommandExecutionRequestApprovalParams.json": object_schema(
        required=["itemId", "startedAtMs", "threadId", "turnId"]
    ),
    "CommandExecutionRequestApprovalResponse.json": object_schema(
        required=["decision"], properties={"decision": {"enum": ["accept", "acceptForSession", "decline", "cancel"]}}
    ),
    "FileChangeRequestApprovalParams.json": object_schema(
        required=["itemId", "startedAtMs", "threadId", "turnId"]
    ),
    "FileChangeRequestApprovalResponse.json": object_schema(
        required=["decision"], properties={"decision": {"enum": ["accept", "acceptForSession", "decline", "cancel"]}}
    ),
    "ToolRequestUserInputParams.json": object_schema(
        required=["itemId", "questions", "threadId", "turnId"]
    ),
    "ToolRequestUserInputResponse.json": object_schema(
        required=["answers"], properties={"answers": {"type": "object"}}
    ),
}


CLIENT_REQUESTS = {
    "initialize": {
        "params_schema": "v1/InitializeParams.json",
        "response_schema": "v1/InitializeResponse.json",
    },
    "task_list": {
        "params_schema": "v2/ThreadListParams.json",
        "response_schema": "v2/ThreadListResponse.json",
    },
    "task_read": {
        "params_schema": "v2/ThreadReadParams.json",
        "response_schema": "v2/ThreadReadResponse.json",
    },
    "task_start": {
        "params_schema": "v2/ThreadStartParams.json",
        "response_schema": "v2/ThreadStartResponse.json",
    },
    "task_resume": {
        "params_schema": "v2/ThreadResumeParams.json",
        "response_schema": "v2/ThreadResumeResponse.json",
    },
    "turn_start": {
        "params_schema": "v2/TurnStartParams.json",
        "response_schema": "v2/TurnStartResponse.json",
    },
    "turn_steer": {
        "params_schema": "v2/TurnSteerParams.json",
        "response_schema": "v2/TurnSteerResponse.json",
    },
    "turn_interrupt": {
        "params_schema": "v2/TurnInterruptParams.json",
        "response_schema": "v2/TurnInterruptResponse.json",
    },
}


def canonical(value: Any, *, newline: bool = False) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + ("\n" if newline else "")
    ).encode()


def semantic_root() -> str:
    lines = []
    for relative, value in sorted(SCHEMAS.items()):
        lines.append(f"{sha256(canonical(value, newline=True)).hexdigest()}  {relative}\n")
    return sha256("".join(lines).encode()).hexdigest()


def write_contract(path: Path) -> None:
    value = {
        "schema_version": 1,
        "cli_version": CLI_VERSION,
        "generated_file_count": len(SCHEMAS),
        "semantic_manifest_sha256": semantic_root(),
        "protocol_error_schema": "JSONRPCError.json",
        "client_requests": CLIENT_REQUESTS,
        "server_notifications": {
            "task_started": "v2/ThreadStartedNotification.json",
            "task_status_changed": "v2/ThreadStatusChangedNotification.json",
            "turn_started": "v2/TurnStartedNotification.json",
            "turn_completed": "v2/TurnCompletedNotification.json",
            "item_started": "v2/ItemStartedNotification.json",
            "item_completed": "v2/ItemCompletedNotification.json",
            "error": "v2/ErrorNotification.json",
        },
        "server_requests": {
            "command_approval": {
                "params_schema": "CommandExecutionRequestApprovalParams.json",
                "response_schema": "CommandExecutionRequestApprovalResponse.json",
            },
            "file_approval": {
                "params_schema": "FileChangeRequestApprovalParams.json",
                "response_schema": "FileChangeRequestApprovalResponse.json",
            },
            "user_input": {
                "params_schema": "ToolRequestUserInputParams.json",
                "response_schema": "ToolRequestUserInputResponse.json",
            },
        },
    }
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_thread(
    cwd: str,
    *,
    active_turn: bool = False,
    terminal_turn: bool = False,
    ephemeral: bool = False,
) -> dict[str, Any]:
    turns = []
    status = {"type": "idle"}
    if active_turn:
        status = {"type": "active", "activeFlags": []}
        turns = [
            {
                "id": "turn-active-001",
                "status": "inProgress",
                "items": [
                    {"id": "item-user-001", "type": "userMessage", "content": [{"type": "text", "text": "Continue."}]}
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
                    {
                        "id": "item-agent-001",
                        "type": "agentMessage",
                        "text": "Done.",
                    }
                ],
                "startedAt": 1786279000,
                "completedAt": 1786279001,
            }
        ]
    return {
        "id": "task-fake-001",
        "sessionId": "task-fake-001",
        "name": "Fake task",
        "preview": "Bounded fake task",
        "ephemeral": ephemeral,
        "modelProvider": "openai",
        "createdAt": 1786278000,
        "updatedAt": 1786279000,
        "status": status,
        "cwd": cwd,
        "cliVersion": CLI_VERSION.removeprefix("codex-cli "),
        "source": "appServer",
        "turns": turns,
    }


def emit(value: Any) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n")
    sys.stdout.flush()


def run_server(mode: str, cwd: str) -> int:
    active_turn = mode in {"active", "approval", "user-input"}
    terminal_turn = mode == "terminal"
    ephemeral = False
    callback_sent = False
    for raw_line in sys.stdin:
        message = json.loads(raw_line)
        method = message.get("method")
        if method == "initialize":
            if mode == "malformed":
                sys.stdout.write("not-json\n")
                sys.stdout.flush()
                continue
            emit(
                {
                    "id": message["id"],
                    "result": {
                        "userAgent": "fake-app-server/0.145.0",
                        "codexHome": "/tmp/fake-codex-home",
                        "platformFamily": "unix",
                        "platformOs": "macos",
                    },
                }
            )
            if mode == "unknown-notification":
                emit({"method": "future/notification", "params": {"secret": "not-exposed"}})
        elif method == "initialized":
            pass
        elif method == "thread/list":
            if mode == "timeout":
                continue
            if mode == "invalid-error-schema":
                emit(
                    {
                        "id": message["id"],
                        "error": {"code": "not-an-integer", "message": 42},
                    }
                )
                continue
            response = {
                "id": message["id"] + 100 if mode == "mismatched-response" else message["id"],
                "result": {
                    "data": [
                        fake_thread(
                            cwd,
                            active_turn=active_turn,
                            terminal_turn=terminal_turn,
                            ephemeral=ephemeral,
                        )
                    ],
                    "nextCursor": None,
                    "backwardsCursor": None,
                },
            }
            if mode == "invalid-list-schema":
                response["result"].pop("data")
            emit(response)
            if mode == "duplicate-response":
                emit(response)
        elif method == "thread/read":
            if mode == "task-not-found":
                emit(
                    {
                        "id": message["id"],
                        "error": {
                            "code": -32600,
                            "message": f"thread not loaded: {message['params']['threadId']}",
                        },
                    }
                )
            elif ephemeral and message["params"].get("includeTurns"):
                emit(
                    {
                        "id": message["id"],
                        "error": {
                            "code": -32600,
                            "message": "ephemeral threads do not support includeTurns",
                        },
                    }
                )
            else:
                emit(
                    {
                        "id": message["id"],
                        "result": {
                            "thread": fake_thread(
                                cwd,
                                active_turn=active_turn,
                                terminal_turn=terminal_turn,
                                ephemeral=ephemeral,
                            )
                        },
                    }
                )
        elif method in {"thread/start", "thread/resume"}:
            if method == "thread/start":
                ephemeral = bool(message["params"].get("ephemeral"))
            emit(
                {
                    "id": message["id"],
                    "result": {"thread": fake_thread(cwd, ephemeral=ephemeral)},
                }
            )
        elif method == "turn/start":
            active_turn = True
            turn_value = fake_thread(cwd, active_turn=True, ephemeral=ephemeral)["turns"][0]
            emit({"id": message["id"], "result": {"turn": turn_value}})
            emit({"method": "turn/started", "params": {"threadId": "task-fake-001", "turn": turn_value}})
        elif method == "turn/steer":
            emit({"id": message["id"], "result": {"turnId": message["params"]["expectedTurnId"]}})
        elif method == "turn/interrupt":
            emit({"id": message["id"], "result": {}})
            active_turn = False
        elif "id" in message and "result" in message:
            callback_sent = True
        if method in {"initialized", "thread/list", "turn/start"} and not callback_sent:
            if mode == "approval":
                callback_sent = True
                emit(
                    {
                        "id": "callback-approval-001",
                        "method": "item/commandExecution/requestApproval",
                        "params": {
                            "threadId": "task-fake-001",
                            "turnId": "turn-active-001",
                            "itemId": "item-command-001",
                            "startedAtMs": 1786279000000,
                            "command": "printf safe",
                            "cwd": cwd,
                            "reason": "Focused fake approval",
                        },
                    }
                )
            elif mode == "user-input":
                callback_sent = True
                emit(
                    {
                        "id": "callback-input-001",
                        "method": "item/tool/requestUserInput",
                        "params": {
                            "threadId": "task-fake-001",
                            "turnId": "turn-active-001",
                            "itemId": "item-input-001",
                            "questions": [
                                {
                                    "id": "choice",
                                    "header": "Choice",
                                    "question": "Which bounded option?",
                                    "options": [
                                        {"label": "First", "description": "Use the first option."}
                                    ],
                                }
                            ],
                        },
                    }
                )
    return 0


def main(argv: list[str]) -> int:
    if "--version" in argv:
        print(CLI_VERSION)
        return 0
    if "generate-json-schema" in argv:
        output = Path(argv[argv.index("--out") + 1])
        for relative, value in SCHEMAS.items():
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    mode = argv[argv.index("--mode") + 1] if "--mode" in argv else "normal"
    cwd = argv[argv.index("--cwd") + 1] if "--cwd" in argv else "/tmp/fake-project"
    return run_server(mode, cwd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
