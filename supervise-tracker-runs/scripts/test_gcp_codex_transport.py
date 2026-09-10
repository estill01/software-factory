import base64
import hashlib
import json
from pathlib import Path
import socket
import struct
import threading
import time
import tempfile
import unittest
from unittest.mock import Mock

from gcp_codex_transport import CodexClient, RpcError, StaleReadbackError, TransportError


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


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'task.jsonl'
        self.client = CodexClient('/unused')
        self.history = [{'id': 'current', 'items': [{'id': 'last'}]}]
        self.client.call = Mock(side_effect=self.rpc)
        self.write(self.event('AgentMessage', 'last'))

    def rpc(self, method, args):
        if method == 'thread/read':
            return {'thread': {'id': 'target', 'path': str(self.path)}}
        if method == 'thread/turns/list':
            return {'data': self.history}
        self.fail('Unexpected mutating or fallback RPC: ' + method)

    @staticmethod
    def event(kind, identity, *, turn='current', **fields):
        return {'type': 'event_msg', 'payload': {'type': 'item_completed',
            'thread_id': 'target', 'turn_id': turn,
            'item': {'type': kind, 'id': identity, **fields}}}

    def write(self, *events, identity='target'):
        header = {'type': 'session_meta', 'payload': {'id': identity}}
        self.path.write_text(''.join(json.dumps(value) + '\n' for value in (header, *events)))

    def test_current_readback_retains_direct_messages_but_omits_tool_outputs(self):
        self.history[0]['items'] = [
            {'id': 'user', 'type': 'userMessage', 'content': [{'type': 'text', 'text': 'hello'}]},
            {'id': 'last', 'type': 'commandExecution', 'aggregatedOutput': 'secret output'}]
        result = self.client.turns('target')
        self.assertEqual(result['readback']['state'], 'current-at-sample')
        self.assertEqual(result['data'][0]['items'][0]['content'][0]['text'], 'hello')
        self.assertNotIn('aggregatedOutput', result['data'][0]['items'][1])

    def test_old_turn_is_rejected_even_when_api_calls_it_in_progress(self):
        self.history = [{'id': 'old', 'status': 'inProgress', 'items': []}]
        with self.assertRaises(StaleReadbackError):
            self.client.turns('target')

    def test_current_turn_with_missing_newer_item_is_rejected(self):
        self.history[0]['items'] = [{'id': 'previous'}]
        with self.assertRaises(StaleReadbackError):
            self.client.turns('target')

    def test_new_turn_without_visible_message_is_rejected(self):
        self.write({'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 'new'}})
        with self.assertRaises(StaleReadbackError):
            self.client.turns('target')

    def test_delivery_uses_exact_native_user_identity_and_text(self):
        self.write(self.event('UserMessage', 'received', client_id='delivery',
                              content=[{'type': 'text', 'text': '[marker]\nAdopt patch.'}]))
        result = self.client.confirm_delivery('target', 'delivery', '[marker]\nAdopt patch.',
                                              expected_turn_id='current')
        self.assertEqual(result['state'], 'received')
        self.assertEqual(result['item_id'], 'received')
        self.assertFalse(result['adoption_confirmed'])
        self.assertEqual([call.args[0] for call in self.client.call.call_args_list], ['thread/read'])

    def test_absent_delivery_is_unknown_and_does_not_send(self):
        result = self.client.confirm_delivery('target', 'missing', 'text')
        self.assertEqual(result['state'], 'not-observed-in-bounded-tail')
        self.assertEqual(self.client.call.call_count, 1)

    def test_copied_marker_in_assistant_or_command_is_not_receipt(self):
        for kind in ['AgentMessage', 'CommandExecution']:
            with self.subTest(kind=kind):
                self.write(self.event(kind, 'copied', client_id='delivery',
                                     content=[{'type': 'text', 'text': 'text'}]))
                self.assertEqual(self.client.confirm_delivery('target', 'delivery', 'text')['state'],
                                 'not-observed-in-bounded-tail')

    def test_different_text_or_turn_and_duplicate_identities_fail_closed(self):
        event = self.event('UserMessage', 'received', client_id='delivery',
                           content=[{'type': 'text', 'text': 'text'}])
        self.write(event)
        for message, turn in [('different', 'current'), ('text', 'different')]:
            with self.subTest(message=message, turn=turn), self.assertRaises(TransportError):
                self.client.confirm_delivery('target', 'delivery', message, expected_turn_id=turn)
        self.write(event, self.event('UserMessage', 'second', client_id='delivery',
                                    content=[{'type': 'text', 'text': 'text'}]))
        with self.assertRaises(TransportError):
            self.client.confirm_delivery('target', 'delivery', 'text')

    def test_missing_mismatched_symlink_and_malformed_logs_fail_closed(self):
        self.path.unlink()
        with self.assertRaises(TransportError):
            self.client.turns('target')
        self.write(self.event('AgentMessage', 'last'), identity='different')
        with self.assertRaises(TransportError):
            self.client.turns('target')
        actual = self.path.with_suffix('.actual')
        self.path.rename(actual)
        self.path.symlink_to(actual)
        with self.assertRaises(TransportError):
            self.client.turns('target')
        self.path.unlink()
        self.write(self.event('AgentMessage', 'last'))
        with self.path.open('a') as stream:
            stream.write('malformed\n')
        with self.assertRaises(TransportError):
            self.client.turns('target')

    def test_partial_append_is_not_a_received_message(self):
        with self.path.open('a') as stream:
            stream.write('{"type":"event_msg",')
        self.assertEqual(self.client.turns('target')['readback']['state'], 'current-at-sample')

    def test_malformed_completed_item_cannot_establish_freshness(self):
        self.write({'type': 'event_msg', 'payload': {
            'type': 'item_completed', 'turn_id': 'current', 'item': None}})
        with self.assertRaises(TransportError):
            self.client.turns('target')

    def test_new_appends_after_sample_do_not_invalidate_that_sample(self):
        def rpc(method, args):
            if method == 'thread/turns/list':
                with self.path.open('a') as stream:
                    stream.write(json.dumps(self.event('AgentMessage', 'newer')) + '\n')
            return self.rpc(method, args)
        self.client.call.side_effect = rpc
        self.assertEqual(self.client.turns('target')['readback']['state'], 'current-at-sample')

    def test_old_delivery_outside_window_stays_unknown(self):
        self.write(self.event('UserMessage', 'received', client_id='delivery',
                              content=[{'type': 'text', 'text': 'text'}]))
        with self.path.open('a') as stream:
            stream.write(json.dumps({'type': 'response_item', 'payload': 'x' * (8 << 20)}) + '\n')
            stream.write(json.dumps(self.event('AgentMessage', 'last')) + '\n')
        result = self.client.confirm_delivery('target', 'delivery', 'text')
        self.assertEqual(result['state'], 'not-observed-in-bounded-tail')
        self.assertEqual(result['bounded_tail_bytes'], 8 << 20)


if __name__ == '__main__':
    unittest.main()
