import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from gcp_supervision import Runtime


class FakeCodex:
    def __init__(self):
        self.queue = []
        self.history = []
        self.started = 0
        self.active = False
        self.lose_add_response = False
        self.lose_start_response = False
        self.auto_start = False

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def compact(self, identity):
        return {'id': identity, 'status': {'type': 'active' if self.active else 'idle'}, 'updatedAt': 1}

    def turns(self, *args, **kwargs):
        return {'data': self.history}

    def call(self, method, args):
        if method == 'thread/queue/list':
            return {'data': self.queue}
        if method == 'thread/queue/add':
            queued = {'id': 'queue-'+args['clientUserMessageId'], **args}
            self.queue.append(queued)
            if self.lose_add_response:
                self.lose_add_response = False
                raise TimeoutError('response lost after accepted add')
            if self.auto_start:
                self.call('thread/queue/start', {'queuedSubmissionId': queued['id']})
                self.active = True
            return {'queuedSubmission': queued}
        if method == 'thread/queue/start':
            queued = next(q for q in self.queue if q['id'] == args['queuedSubmissionId'])
            self.queue.remove(queued)
            self.started += 1
            turn = {'id': f'turn-{self.started}', 'status': 'inProgress',
                    'items': [{'type': 'userMessage', 'content': queued['input']}]}
            self.history.insert(0, turn)
            if self.lose_start_response:
                self.lose_start_response = False
                raise TimeoutError('response lost after accepted start')
            return {'turn': turn}
        raise AssertionError(method)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root/'config.json'
        self.config = {'schema_version': 1, 'target_thread_id': 'target',
                       'state_root': str(self.root), 'socket_path': '/unused',
                       'roles': {'liveness': {'thread_id': 'liveness'},
                                 'watcher': {'thread_id': 'watcher'},
                                 'reviewer': {'thread_id': 'reviewer'}}}
        self.path.write_text(json.dumps(self.config))
        self.fake = FakeCodex()
        self.runtime = Runtime(self.path, client_factory=self.fake)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def message(self):
        return self.runtime.prepare('one', 'watcher', 'Check the exact target.', 'source', 'watcher-action')

    def test_schedule_and_receipt_survive_restart(self):
        schedule = self.runtime.add_schedule('liveness', 60, first_due=time.time()-1)
        self.runtime.schedule_state(True)
        self.runtime.tick()
        self.assertEqual(self.fake.started, 1)
        self.runtime.close()
        self.runtime = Runtime(self.path, client_factory=self.fake)
        self.runtime.tick()
        state = self.runtime.status()
        self.assertEqual(state['schedules'][0]['id'], schedule)
        self.assertEqual(self.fake.started, 1)
        self.assertEqual(state['deliveries'][0]['state'], 'started')

    def test_lost_queue_response_reconciles_without_duplicate(self):
        identity = self.message()
        self.fake.lose_add_response = True
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.started, 1)
        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.started, 1)

    def test_idle_queue_auto_start_is_observed_without_second_start(self):
        self.fake.auto_start = True
        identity = self.message()
        self.assertEqual(self.runtime.deliver(identity), 'acknowledged')
        self.assertEqual(self.fake.started, 1)

    def test_recovered_receipt_advances_schedule_while_role_is_active(self):
        self.runtime.add_schedule('liveness', 60, first_due=time.time()-1)
        self.runtime.schedule_state(True)
        self.fake.auto_start = True
        self.runtime.tick()
        state = self.runtime.status()['schedules'][0]
        self.assertIsNotNone(state['last_delivery'])
        self.assertGreater(state['next_due'], time.time())

    def test_lost_start_response_reconciles_from_direct_history(self):
        identity = self.message()
        self.fake.lose_start_response = True
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(self.runtime.deliver(identity), 'acknowledged')
        self.assertEqual(self.fake.started, 1)

    def test_unresolved_delivery_is_not_resent(self):
        identity = self.message()
        self.runtime.update_delivery(identity, 'uncertain')
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.queue, [])

    def test_active_role_is_not_given_duplicate_heartbeat(self):
        self.runtime.add_schedule('liveness', 60, first_due=0)
        self.runtime.schedule_state(True)
        self.fake.active = True
        self.runtime.tick()
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.queue, [])

    def test_action_waits_in_same_role_queue_while_active(self):
        identity = self.message()
        self.fake.active = True
        self.assertEqual(self.runtime.deliver(identity), 'queued')
        self.fake.active = False
        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.started, 1)

    def test_pause_persists_and_stops_new_scheduled_wakes(self):
        self.runtime.add_schedule('liveness', 60, first_due=0)
        self.runtime.schedule_state(True)
        self.runtime.schedule_state(False)
        self.runtime.tick()
        self.assertEqual(self.fake.started, 0)

    def test_wrong_target_and_identity_reuse_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.prepare('other', 'unrelated', 'message', 's', 'p')
        self.message()
        with self.assertRaises(ValueError):
            self.runtime.prepare('one', 'watcher', 'different', 'source', 'watcher-action')

    def test_route_denial_has_no_delivery_effect(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'reviewer'}):
            with patch.object(self.runtime, 'helper', return_value={'send_allowed': False}):
                result = self.runtime.gated_send('target', 'target-action', 'source', 'bounded correction')
        self.assertFalse(result['delivered'])
        self.assertEqual(self.runtime.status()['deliveries'], [])

    def test_unbound_sender_rejected(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'unrelated'}):
            with self.assertRaises(ValueError):
                self.runtime.gated_send('target', 'target-action', 'source', 'message')

    def test_full_evidence_packet_uses_separate_bounded_action_and_replays_once(self):
        message = 'Exact evidence packet: '+('record-and-turn-reference\n'*40)
        action = 'Independently review the exact completion evidence.'
        def gate(arguments):
            self.assertEqual(arguments[arguments.index('--recipient-thread')+1], 'watcher')
            self.assertEqual(arguments[arguments.index('--source-record')+1], 'EVT-000001')
            self.assertEqual(arguments[arguments.index('--action')+1], action)
            self.assertLessEqual(len(arguments[arguments.index('--action')+1]), 240)
            return {'send_allowed': True}
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'reviewer'}):
            with patch.object(self.runtime, 'helper', side_effect=gate):
                first = self.runtime.gated_send('watcher', 'watcher-action', 'EVT-000001', message, action=action)
                again = self.runtime.gated_send('watcher', 'watcher-action', 'EVT-000001', message, action=action)
        self.assertEqual(first['delivery_id'], again['delivery_id'])
        self.assertEqual(self.fake.started, 1)
        self.assertTrue(self.fake.history[0]['items'][0]['content'][0]['text'].endswith(message))
        self.assertEqual(self.runtime.db.execute('SELECT message FROM deliveries').fetchone()[0], message)

    def test_explicit_action_does_not_bypass_denied_route(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'reviewer'}):
            with patch.object(self.runtime, 'helper', return_value={'send_allowed': False}):
                result = self.runtime.gated_send('watcher', 'watcher-action', 'source', 'evidence'*100,
                                                 action='Review exact evidence.')
        self.assertFalse(result['delivered'])
        self.assertEqual(self.runtime.status()['deliveries'], [])

    def test_status_broadcast_preserves_exact_payload_gate_binding(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'reviewer'}):
            with patch.object(self.runtime, 'helper') as helper:
                with self.assertRaisesRegex(ValueError, 'exact message payload'):
                    self.runtime.gated_send('target', 'status-broadcast', 'source', 'exact message',
                                             action='different summary')
        helper.assert_not_called()
        self.assertEqual(self.runtime.status()['deliveries'], [])


if __name__ == '__main__':
    unittest.main()
