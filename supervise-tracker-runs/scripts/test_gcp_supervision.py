import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from gcp_supervision import Runtime
from gcp_codex_transport import RpcError, StaleReadbackError


class FakeCodex:
    def __init__(self):
        self.queue = []
        self.history = []
        self.started = 0
        self.active = False
        self.lose_add_response = False
        self.lose_start_response = False
        self.auto_start = False
        self.not_loaded = False
        self.resume_arguments = None
        self.resume_writable = True
        self.resume_error = None
        self.steered = []
        self.lose_steer_response = False
        self.active_turn_id = 'native-current-owner-turn'

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def compact(self, identity):
        if self.not_loaded:
            return {'id': identity, 'status': {'type': 'notLoaded'}, 'updatedAt': 1}
        return {'id': identity, 'status': {'type': 'active' if self.active else 'idle'}, 'updatedAt': 1}

    def turns(self, *args, **kwargs):
        return {'data': self.history}

    def call(self, method, args):
        if method == 'turn/start':
            if not self.active:
                raise AssertionError('active-owner test unexpectedly started idle work')
            self.steered.append(args)
            turn = next((turn for turn in self.history if turn['id'] == self.active_turn_id), None)
            if turn is None:
                turn = {'id': self.active_turn_id, 'status': 'inProgress', 'items': []}
                self.history.insert(0, turn)
            turn['items'].append({'type': 'userMessage', 'content': args['input']})
            if self.lose_steer_response:
                self.lose_steer_response = False
                raise TimeoutError('response lost after accepted active input')
            return {'turn': turn}
        if method == 'turn/steer':
            if not self.active or not self.history or args['expectedTurnId'] != self.history[0]['id']:
                raise RpcError(method, {'code': -1, 'message': 'active turn changed'})
            self.steered.append(args)
            self.history[0]['items'].append({'type': 'userMessage', 'content': args['input']})
            if self.lose_steer_response:
                self.lose_steer_response = False
                raise TimeoutError('response lost after accepted steer')
            return {'turnId': args['expectedTurnId']}
        if method == 'thread/resume':
            if self.resume_error is not None:
                error, self.resume_error = self.resume_error, None
                raise error
            self.resume_arguments = args
            self.not_loaded = False
            return {'sandbox': {'type': 'dangerFullAccess' if self.resume_writable else 'readOnly'},
                    'approvalPolicy': 'never'}
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

    def test_delivery_status_confirms_exact_item_without_resend(self):
        identity = self.message()
        self.assertEqual(self.runtime.deliver(identity), 'started')
        with patch.object(self.fake, 'confirm_delivery', create=True,
                          return_value={'state': 'received', 'turn_id': 'turn-1'}) as confirm:
            result = self.runtime.delivery_status(identity)
        confirm.assert_called_once_with('watcher', identity,
            self.runtime.marker(identity, 'watcher-action') + '\nCheck the exact target.',
            expected_turn_id='turn-1')
        self.assertEqual(result['state'], 'acknowledged')
        self.assertFalse(result['adoption_confirmed'])
        self.assertEqual(self.runtime.deliver(identity), 'acknowledged')
        self.assertEqual(self.fake.started, 1)

    def test_unobserved_receipt_preserves_accepted_state_without_resend(self):
        identity = self.message()
        self.runtime.deliver(identity)
        with patch.object(self.fake, 'confirm_delivery', create=True,
                          return_value={'state': 'not-observed-in-bounded-tail'}):
            result = self.runtime.delivery_status(identity)
        self.assertEqual(result['state'], 'started')
        self.assertFalse(result['adoption_confirmed'])
        self.assertEqual(self.fake.started, 1)

    def test_stale_history_can_reconcile_only_an_exact_native_transport_receipt(self):
        identity = self.message()
        self.runtime.update_delivery(identity, 'uncertain', turn_id='current')
        with patch.object(self.fake, 'turns', side_effect=StaleReadbackError('stale')):
            with patch.object(self.fake, 'confirm_delivery', create=True,
                              return_value={'state': 'not-observed-in-bounded-tail'}):
                self.assertEqual(self.runtime.deliver(identity), 'uncertain')
            with patch.object(self.fake, 'confirm_delivery', create=True,
                              return_value={'state': 'received', 'turn_id': 'current'}):
                self.assertEqual(self.runtime.deliver(identity), 'acknowledged')
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.steered, [])

    def test_unloaded_role_restores_original_helper_access_before_delivery(self):
        role = {'thread_id': 'watcher', 'model': 'gpt-5.6-terra',
                'cwd': str(self.root), 'reasoning': 'max',
                'instructions': 'Bound watcher instructions'}
        self.runtime.config['roles']['watcher'] = role
        self.fake.not_loaded = True
        self.assertEqual(self.runtime.deliver(self.message()), 'started')
        args = self.fake.resume_arguments
        self.assertEqual(args['sandbox'], 'danger-full-access')
        self.assertEqual(args['approvalPolicy'], 'never')
        self.assertEqual(args['threadId'], 'watcher')
        self.assertEqual(args['developerInstructions'], role['instructions'])
        self.assertEqual(args['config']['model_reasoning_effort'], 'max')
        self.assertEqual(self.fake.started, 1)

    def test_unrestored_role_does_not_receive_queued_work(self):
        self.runtime.config['roles']['watcher'].update(
            model='gpt-5.6-terra', cwd=str(self.root), reasoning='max', instructions='Bound')
        self.fake.not_loaded = True
        self.fake.resume_writable = False
        identity = self.message()
        self.assertEqual(self.runtime.deliver(identity), 'failed')
        self.assertEqual(self.runtime.deliver(identity), 'failed')
        self.assertEqual(self.fake.queue, [])
        self.assertEqual(self.fake.started, 0)

    def test_target_resume_does_not_replace_its_permissions_or_instructions(self):
        self.fake.not_loaded = True
        self.fake.resume_writable = False
        identity = self.runtime.prepare('target-wake', 'target', 'Continue.', 'source', 'target-action')
        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.resume_arguments, {'threadId': 'target'})

    def test_rejected_role_restore_preserves_uncertain_existing_delivery(self):
        self.runtime.config['roles']['watcher'].update(
            model='gpt-5.6-terra', cwd=str(self.root), reasoning='max', instructions='Bound')
        self.fake.lose_add_response = True
        identity = self.message()
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(len(self.fake.queue), 1)
        self.fake.not_loaded = True
        self.fake.resume_writable = False
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.assertEqual(len(self.fake.queue), 1)
        self.assertEqual(self.fake.started, 0)
        self.fake.resume_writable = True
        self.assertEqual(self.runtime.deliver(identity), 'started')

    def test_failed_role_posture_applies_to_new_deliveries(self):
        self.runtime.config['roles']['watcher'].update(
            model='gpt-5.6-terra', cwd=str(self.root), reasoning='max', instructions='Bound')
        self.fake.not_loaded = True
        self.fake.resume_writable = False
        self.assertEqual(self.runtime.deliver(self.message()), 'failed')
        later = self.runtime.prepare('later', 'watcher', 'Later wake.', 'source', 'watcher-action')
        self.assertEqual(self.runtime.deliver(later), 'failed')
        self.assertEqual(self.fake.queue, [])
        self.assertEqual(self.fake.started, 0)
        self.fake.resume_writable = True
        restored = self.runtime.prepare('restored', 'watcher', 'Restored wake.', 'source', 'watcher-action')
        self.assertEqual(self.runtime.deliver(restored), 'started')
        self.assertEqual(self.fake.started, 1)

    def test_restore_posture_survives_rpc_errors_and_runtime_restart(self):
        self.runtime.config['roles']['watcher'].update(
            model='gpt-5.6-terra', cwd=str(self.root), reasoning='max', instructions='Bound')
        self.path.write_text(json.dumps(self.runtime.config))
        self.fake.lose_add_response = True
        identity = self.message()
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.fake.not_loaded = True
        self.fake.resume_writable = False
        self.assertEqual(self.runtime.deliver(identity), 'uncertain')
        self.runtime.close()
        self.runtime = Runtime(self.path, client_factory=self.fake)
        for error in (TimeoutError('lost resume'), RpcError('thread/resume', {'code': -1, 'message': 'rejected'})):
            self.fake.resume_error = error
            self.assertEqual(self.runtime.deliver(identity), 'uncertain')
            self.assertEqual(self.runtime.deliver(identity), 'uncertain')
            self.assertEqual(self.fake.started, 0)
            self.assertEqual(len(self.fake.queue), 1)
        self.fake.resume_writable = True
        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.started, 1)
        self.assertEqual(self.fake.queue, [])
        self.assertEqual(self.runtime.deliver(identity), 'started')

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

    def owner_message(self, **overrides):
        record = self.root / 'existing-owner-response.json'
        if not record.exists():
            record.write_text(json.dumps({'owner_task': 'project-owner',
                                          'requesting_task': 'target'}))
        self.runtime.config['mission_source_record'] = 'direct-user:target:mission'
        arguments = dict(recipient='project-owner', source='direct-user:target:mission',
                         message='Please arrange one stable read interval. Release checks remain required.',
                         owner_record=str(record),
                         owner_record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),
                         owner_field='owner_task', sender_field='requesting_task')
        arguments.update(overrides)
        return self.runtime.owner_send(**arguments)

    def test_owner_coordination_works_with_all_schedules_stopped(self):
        for role in ('liveness', 'watcher', 'reviewer'):
            self.runtime.add_schedule(role, 60, first_due=0)
        before = [dict(row) for row in self.runtime.db.execute('SELECT * FROM schedules')]
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}), patch.object(self.runtime, 'helper') as helper:
            result = self.owner_message()
        helper.assert_not_called()
        self.assertEqual(result['state'], 'started')
        self.assertFalse(result['operation_authorized'])
        self.assertEqual(before, [dict(row) for row in self.runtime.db.execute('SELECT * FROM schedules')])
        self.assertEqual(self.fake.started, 1)
        self.assertIn('[gcp-owner-delivery:', self.fake.history[0]['items'][0]['content'][0]['text'])

    def test_owner_route_cannot_impersonate_supervision_or_change_authority(self):
        for caller, overrides in [('watcher', {}), ('unknown', {}),
                                  ('target', {'recipient': 'reviewer'}),
                                  ('target', {'recipient': 'different-owner'}),
                                  ('target', {'source': 'different-authority'}),
                                  ('target', {'owner_record_sha256': '0'*64})]:
            with self.subTest(caller=caller, overrides=overrides):
                with patch.dict(os.environ, {'CODEX_THREAD_ID': caller}), self.assertRaises(ValueError):
                    self.owner_message(**overrides)
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.runtime.status()['deliveries'], [])

    def test_unloaded_owner_preserves_its_own_settings(self):
        self.fake.not_loaded = True
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            self.assertEqual(self.owner_message()['state'], 'started')
        self.assertEqual(self.fake.resume_arguments, {'threadId': 'project-owner'})

    def test_owner_admission_validates_the_exact_hashed_snapshot(self):
        record = self.root / 'existing-owner-response.json'
        read_bytes = Path.read_bytes
        def replace_after_hash_read(path):
            snapshot = read_bytes(path)
            if path == record:
                record.write_text(json.dumps({'owner_task': 'project-owner', 'requesting_task': 'target'}))
            return snapshot
        self.runtime.config['mission_source_record'] = 'direct-user:target:mission'
        for invalid in ({'owner_task': 'different-owner', 'requesting_task': 'target'}, None, []):
            with self.subTest(hashed_record=invalid):
                record.write_text(json.dumps(invalid))
                expected_sha = hashlib.sha256(record.read_bytes()).hexdigest()
                with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}), patch.object(Path, 'read_bytes', replace_after_hash_read):
                    with self.assertRaisesRegex(ValueError, 'exact pair'):
                        self.runtime.owner_send('project-owner', 'direct-user:target:mission', 'Arrange the interval.',
                            owner_record=str(record), owner_record_sha256=expected_sha,
                            owner_field='owner_task', sender_field='requesting_task')
        self.assertEqual(self.runtime.status()['deliveries'], [])
        self.assertEqual(self.fake.started, 0)

    def test_active_owner_receives_coordination_without_waiting_for_mission_end(self):
        self.fake.active = True
        self.fake.history = [{'id': 'stale-persisted-turn', 'status': 'inProgress', 'items': []}]
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}), patch.object(
                self.fake, 'turns', side_effect=AssertionError('history is not a live-turn precondition')):
            first = self.owner_message()
            again = self.owner_message()
        self.assertEqual(first['state'], 'started')
        self.assertEqual(again['delivery_id'], first['delivery_id'])
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.queue, [])
        self.assertEqual(len(self.fake.steered), 1)
        self.assertEqual(self.fake.steered[0]['threadId'], 'project-owner')
        self.assertEqual(set(self.fake.steered[0]), {'threadId', 'clientUserMessageId', 'input'})
        receipt = self.runtime.db.execute('SELECT turn_id FROM deliveries WHERE id=?',
                                          (first['delivery_id'],)).fetchone()
        self.assertEqual(receipt['turn_id'], 'native-current-owner-turn')

    def test_active_owner_native_rejection_is_preserved_without_resend(self):
        self.fake.active = True
        self.fake.history = [{'id': 'existing-owner-turn', 'status': 'inProgress', 'items': []}]
        native_call = self.fake.call
        def change_turn(method, args):
            if method == 'turn/start':
                raise RpcError(method, {'code': -32600, 'message': 'native active input rejected'})
            return native_call(method, args)
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}), patch.object(
                self.fake, 'call', side_effect=change_turn) as calls:
            result = self.owner_message()
            rejection = self.runtime.db.execute('SELECT error FROM deliveries').fetchone()[0]
            self.assertEqual(self.runtime.deliver(result['delivery_id']), 'uncertain')
        self.assertEqual(sum(call.args[0] == 'turn/start' for call in calls.call_args_list), 1)
        self.assertEqual(result['state'], 'uncertain')
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.steered, [])
        self.assertEqual(self.fake.queue, [])
        self.assertIn('native active input rejected', rejection)

    def test_lost_active_owner_steer_response_does_not_duplicate_work(self):
        self.fake.active = True
        self.fake.lose_steer_response = True
        self.fake.history = [{'id': 'existing-owner-turn', 'status': 'inProgress', 'items': []}]
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            first = self.owner_message()
            again = self.owner_message()
        self.assertEqual(first['state'], 'uncertain')
        self.assertEqual(again['state'], 'acknowledged')
        self.assertEqual(len(self.fake.steered), 1)
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(self.fake.queue, [])

    def test_preexisting_queued_owner_request_is_not_steered_again(self):
        self.fake.lose_add_response = True
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            original = self.owner_message()
        self.assertEqual(original['state'], 'uncertain')
        queued = list(self.fake.queue)
        self.fake.active = True

        self.assertEqual(self.runtime.deliver(original['delivery_id']), 'queued')
        self.assertEqual(self.fake.queue, queued)
        self.assertEqual(self.fake.steered, [])
        self.assertEqual(self.fake.started, 0)

    def test_supervisor_target_steer_keeps_exact_turn_precondition(self):
        self.fake.active = True
        self.fake.history = [{'id': 'supervised-turn', 'status': 'inProgress', 'items': []}]
        identity = self.runtime.prepare('supervisor-action', 'target', 'Recheck exact scope.',
                                        'record', 'target-action')

        self.assertEqual(self.runtime.deliver(identity), 'started')
        self.assertEqual(self.fake.steered[0]['expectedTurnId'], 'supervised-turn')
        self.assertEqual(self.fake.started, 0)

    def test_owner_receipt_survives_unrelated_checkpoint_without_duplicate(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            first = self.owner_message()
            record = self.root / 'existing-owner-response.json'
            data = json.loads(record.read_text())
            data['unrelated_checkpoint'] = 'later-commit'
            record.write_text(json.dumps(data))
            again = self.owner_message()
        self.assertEqual(first['delivery_id'], again['delivery_id'])
        self.assertEqual(self.fake.started, 1)

    def test_changed_owner_blocks_pending_send_and_retains_evidence(self):
        # Preserve a legacy queued owner receipt; native active-turn resolution
        # for new messages must never replay this already-owned queue.
        self.fake.lose_add_response = True
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            result = self.owner_message()
        record = self.root / 'existing-owner-response.json'
        record.write_text(json.dumps({'owner_task': 'new-owner', 'requesting_task': 'target'}))
        self.assertEqual(self.runtime.deliver(result['delivery_id']), 'uncertain')
        self.assertEqual(self.fake.started, 0)
        self.assertEqual(len(self.fake.queue), 1)
        self.assertIn('exact pair', self.runtime.db.execute('SELECT error FROM deliveries').fetchone()[0])

    def test_ambiguous_owner_send_reconciles_after_restart_without_resend(self):
        self.fake.auto_start = True
        self.fake.lose_start_response = True
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'target'}):
            result = self.owner_message()
        self.assertEqual(result['state'], 'uncertain')
        self.path.write_text(json.dumps(self.runtime.config))
        self.runtime.close()
        self.runtime = Runtime(self.path, client_factory=self.fake)
        self.assertEqual(self.runtime.deliver(result['delivery_id']), 'acknowledged')
        self.assertEqual(self.fake.started, 1)


if __name__ == '__main__':
    unittest.main()
