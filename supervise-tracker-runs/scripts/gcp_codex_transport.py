"""Bounded JSON-RPC client for the existing local Codex control socket.

The daemon's Unix socket uses WebSocket framing, not JSONL. This module owns
only its connection, never the daemon, task lifecycle, or supervision policy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import time
from pathlib import Path


class TransportError(RuntimeError):
    pass


class RpcError(TransportError):
    def __init__(self, method: str, error: dict):
        self.method, self.error = method, error
        super().__init__(f"{method}: {error.get('code')}: {error.get('message')}")


class CodexClient:
    """One synchronous local connection; callers serialize access."""

    def __init__(self, path: str, *, timeout: float = 15, max_bytes: int = 32 << 20):
        self.path = path
        self.timeout, self.max_bytes = timeout, max_bytes
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.next_id = 1

    def __enter__(self):
        if not Path(self.path).is_absolute():
            raise TransportError("control socket must be absolute")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        try:
            self.sock.connect(self.path)
            self._upgrade()
            self.call("initialize", {
                "clientInfo": {"name": "gcp_supervision", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            })
            self.notify("initialized", {})
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def _upgrade(self):
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Key: {key}\r\n\r\n"
        ).encode())
        deadline = time.monotonic() + self.timeout
        while b"\r\n\r\n" not in self.buffer:
            self._receive_bytes(deadline)
            if len(self.buffer) > 65536:
                raise TransportError("oversized WebSocket upgrade")
        raw, rest = bytes(self.buffer).split(b"\r\n\r\n", 1)
        self.buffer = bytearray(rest)
        lines = raw.decode("ascii").split("\r\n")
        headers = {k.lower(): v.strip() for k, v in
                   (line.split(":", 1) for line in lines[1:] if ":" in line)}
        expected = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
        ).digest()).decode()
        if (lines[0].split()[1:2] != ["101"]
                or headers.get("sec-websocket-accept") != expected
                or headers.get("upgrade", "").lower() != "websocket"
                or "upgrade" not in headers.get("connection", "").lower()):
            raise TransportError("invalid WebSocket upgrade")

    def _receive_bytes(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex response deadline exceeded")
        self.sock.settimeout(remaining)
        try:
            data = self.sock.recv(65536)
        except TimeoutError:
            raise
        except OSError as exc:
            raise TransportError("Codex connection failed") from exc
        if not data:
            raise TransportError("Codex connection closed")
        self.buffer.extend(data)

    def _read(self, count, deadline):
        while len(self.buffer) < count:
            self._receive_bytes(deadline)
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def _send(self, payload: bytes, opcode: int = 1):
        if len(payload) > self.max_bytes:
            raise TransportError("outgoing message exceeds bound")
        if self.sock is None:
            raise TransportError("connection is closed")
        n = len(payload)
        header = bytes([0x80 | opcode])
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", n)
        mask = os.urandom(4)
        self.sock.settimeout(self.timeout)
        self.sock.sendall(header + mask + bytes(
            value ^ mask[i % 4] for i, value in enumerate(payload)
        ))

    def _message(self, deadline):
        parts = bytearray()
        started = False
        while True:
            first, second = self._read(2, deadline)
            opcode, final = first & 15, bool(first & 128)
            if first & 112 or second & 128:
                raise TransportError("unsupported server frame flags")
            length = second & 127
            if length == 126:
                length = struct.unpack("!H", self._read(2, deadline))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read(8, deadline))[0]
            if length > self.max_bytes or length + len(parts) > self.max_bytes:
                raise TransportError("incoming message exceeds bound")
            if opcode >= 8 and (not final or length > 125):
                raise TransportError("invalid control frame")
            data = self._read(length, deadline)
            if opcode == 8:
                raise TransportError("Codex closed WebSocket")
            if opcode == 9:
                self._send(data, 10)
                continue
            if opcode == 10:
                continue
            if opcode == 1 and not started:
                started = True
            elif opcode != 0 or not started:
                raise TransportError("unexpected WebSocket message fragment")
            parts.extend(data)
            if final:
                result = json.loads(parts)
                if not isinstance(result, dict):
                    raise TransportError("RPC message is not an object")
                return result

    def notify(self, method, params):
        self._send(json.dumps({"method": method, "params": params}).encode())

    def call(self, method, params):
        request_id = self.next_id
        self.next_id += 1
        self._send(json.dumps({"id": request_id, "method": method, "params": params}).encode())
        deadline = time.monotonic() + self.timeout
        while True:
            response = self._message(deadline)
            # These clients supply no dynamic tools or approvals. Never silently
            # approve a callback or leave a server request hanging.
            if "method" in response:
                if "id" in response:
                    self._send(json.dumps({"id": response["id"], "error": {
                        "code": -32601, "message": "No handler on read/control connection"
                    }}).encode())
                continue
            if response.get("id") != request_id:
                raise TransportError("unexpected RPC response identity")
            if "error" in response:
                raise RpcError(method, response["error"])
            if "result" not in response:
                raise TransportError("RPC response has no result")
            return response["result"]

    def compact(self, thread_id):
        thread = self.call("thread/read", {"threadId": thread_id, "includeTurns": False})["thread"]
        return {key: thread.get(key) for key in
                ("id", "status", "updatedAt", "createdAt", "cwd", "name")}

    def turns(self, thread_id, *, limit=1):
        if not 1 <= limit <= 4:
            raise ValueError("direct evidence is bounded to one through four turns")
        value = self.call("thread/turns/list", {
            "threadId": thread_id, "limit": limit,
            "itemsView": "full", "sortDirection": "desc",
        })
        # Preserve direct user/assistant text and call identities. Tool results
        # are deliberately omitted; there is no substituted semantic summary.
        for turn in value.get("data", []):
            for item in turn.get("items", []):
                for key in ("aggregatedOutput", "output", "stdout", "stderr", "result",
                            "contentItems", "diff", "content", "data"):
                    if key in item and item.get("type") not in ("userMessage", "agentMessage"):
                        item.pop(key)
                        item["outputsOmitted"] = True
        return value
