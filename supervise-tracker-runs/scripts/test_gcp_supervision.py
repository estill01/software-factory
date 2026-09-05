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


if __name__ == '__main__':
    unittest.main()
