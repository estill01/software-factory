import base64
import hashlib
import json
import socket
import struct
import threading
import time
import unittest

from gcp_codex_transport import CodexClient, RpcError, TransportError


def frame(data, opcode=1, final=True):
    data = data if isinstance(data, bytes) else json.dumps(data).encode()
    first = (128 if final else 0) | opcode
    if len(data) < 126:
        return bytes([first, len(data)]) + data
    return bytes([first, 126]) + struct.pack('!H', len(data)) + data


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.left, self.right = socket.socketpair()
        self.client = CodexClient('/unused', timeout=.15, max_bytes=1024)
        self.client.sock = self.left

    def tearDown(self):
        self.client.close()
        self.right.close()

    def test_handshake_checks_accept_and_preserves_trailing_frame(self):
        def serve():
            request = self.right.recv(4096).decode()
            key = next(line.split(': ', 1)[1] for line in request.split('\r\n')
                       if line.startswith('Sec-WebSocket-Key:'))
            accept = base64.b64encode(hashlib.sha1(
                (key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()
            ).digest()).decode()
            self.right.sendall((f'HTTP/1.1 101 Switching Protocols\r\n'
                                f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                                f'Sec-WebSocket-Accept: {accept}\r\n\r\n').encode()
                               + frame({'id': 1, 'result': {}}))
        t = threading.Thread(target=serve)
        t.start()
        self.client._upgrade()
        self.assertEqual(self.client.call('example', {}), {})
        t.join()

    def test_bad_upgrade_fails(self):
        self.right.sendall(b'HTTP/1.1 403 Forbidden\r\n\r\n')
        with self.assertRaises(TransportError):
            self.client._upgrade()

    def test_fragmentation_and_ping(self):
        self.right.sendall(frame(b'{"ok":', final=False) + frame(b'ping', opcode=9)
                           + frame(b'true}', opcode=0))
        self.assertEqual(self.client._message(time.monotonic()+1), {'ok': True})
        self.assertEqual(self.right.recv(4096)[0], 138)

    def test_size_bound_before_body_read(self):
        self.right.sendall(bytes([129, 126])+struct.pack('!H', 1025))
        with self.assertRaisesRegex(TransportError, 'bound'):
            self.client._message(time.monotonic()+1)

    def test_deadline_and_eof(self):
        with self.assertRaises(TimeoutError):
            self.client.call('example', {})
        self.right.close()
        with self.assertRaises(TransportError):
            self.client._message(time.monotonic()+1)

    def test_notifications_do_not_replace_response(self):
        self.right.sendall(frame({'method': 'thread/status/changed', 'params': {}})
                           + frame({'id': 1, 'result': {'value': 3}}))
        self.assertEqual(self.client.call('example', {}), {'value': 3})

    def test_rpc_error_retains_code(self):
        self.right.sendall(frame({'id': 1, 'error': {'code': -1, 'message': 'bad'}}))
        with self.assertRaises(RpcError) as caught:
            self.client.call('example', {})
        self.assertEqual(caught.exception.error['code'], -1)

    def test_wrong_response_identity_fails(self):
        self.right.sendall(frame({'id': 12, 'result': {}}))
        with self.assertRaisesRegex(TransportError, 'identity'):
            self.client.call('example', {})


if __name__ == '__main__':
    unittest.main()
