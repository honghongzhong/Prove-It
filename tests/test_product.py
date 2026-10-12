"""Product regressions: session ownership, ordered events and model forwarding."""
import unittest
from unittest.mock import Mock, patch
from proveit import research, workspace
from proveit.codex_bridge import CodexBridge
from proveit.instance import WorkspaceLease
import test_research

class ProductTests(unittest.TestCase):
    setUp = test_research.ResearchTests.setUp
    tearDown = test_research.ResearchTests.tearDown

    def test_writer_conflict_recovers_without_touching_original(self):
        research.set_runtime('Test.lean', threadId='owned-elsewhere')
        bridge=CodexBridge()
        bridge.call=Mock(side_effect=[RuntimeError('thread owned-elsewhere already has an active writer'), {'thread':{'id':'new-owned'}}])
        bridge._select_thread('Test.lean')
        state=research.get('Test.lean')
        self.assertEqual(state['threadId'], 'new-owned')
        self.assertEqual(state['previousThreadIds'], ['owned-elsewhere'])
        self.assertEqual(state['goal'], self.goal)
        self.assertEqual([c.args[0] for c in bridge.call.call_args_list], ['thread/resume','thread/start'])
        self.assertTrue(bridge.call.call_args_list[1].args[1]['dynamicTools'])

    def test_unrelated_resume_failure_is_not_silently_replaced(self):
        research.set_runtime('Test.lean',threadId='original')
        bridge=CodexBridge();bridge.call=Mock(side_effect=RuntimeError('authentication failed'))
        with self.assertRaises(RuntimeError): bridge._select_thread('Test.lean')
        self.assertEqual(research.get('Test.lean')['threadId'],'original')

    def test_timeline_order_updates_in_place_and_survives_rename(self):
        research.message('Test.lean','user','Question')
        bridge=CodexBridge();bridge.current_proof_id='Test.lean';bridge.thread_id='thread'
        bridge._record_timeline('item/agentMessage/delta',{'itemId':'a','delta':'First'})
        bridge._record_timeline('item/started',{'item':{'id':'tool','type':'dynamicToolCall','tool':'proveit_read_research'}})
        bridge._record_timeline('item/completed',{'item':{'id':'tool','type':'dynamicToolCall','tool':'proveit_read_research','success':False}})
        bridge._record_timeline('item/completed',{'item':{'id':'a','type':'agentMessage','text':'First completed'}})
        bridge._record_timeline('item/completed',{'item':{'id':'b','type':'agentMessage','text':'After tool'}})
        items=research.timeline('Test.lean')
        self.assertEqual([x['kind'] for x in items],['user','assistant','tool','assistant'])
        self.assertEqual(items[2]['status'],'failed')
        self.assertEqual(items[1]['content'],'First completed')
        workspace.rename_proof('Test.lean','Renamed.lean')
        self.assertEqual(len(research.timeline('Renamed.lean')),4)

    def test_model_validation_and_queue_snapshot(self):
        bridge=CodexBridge();bridge.worker=Mock();bridge.worker.is_alive.return_value=True
        bridge.models_cache=[{'model':'selected-model','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}]
        bridge.send_message('Direction','context','standalone','Test.lean','en','selected-model','high')
        self.assertEqual(bridge.requests.get_nowait(),('Direction','standalone','Test.lean','en','selected-model','high'))
        with self.assertRaises(ValueError): bridge.send_message('Bad','context','standalone','Test.lean','en','missing','high')
        self.assertEqual(len(research.messages('Test.lean')),1)

    def test_single_workspace_owner_is_released(self):
        with WorkspaceLease(1000):
            with self.assertRaises(RuntimeError):
                with WorkspaceLease(2000): pass
        with WorkspaceLease(2000): pass

    def test_unfinished_events_and_complete_export(self):
        research.timeline_write('Test.lean', 'pending', 'tool', 'partial', 'running', 'read')
        entries = research.timeline_interrupt('Test.lean')
        self.assertEqual(entries[0]['status'], 'interrupted')
        self.assertEqual(research.timeline_interrupt('Test.lean'), [])
        with research._connect() as db:
            db.executemany("INSERT INTO research_events(filename,event_key,kind,content,status,tool,created_at) VALUES(?,?,?,?,?,?,?)", [('Test.lean', str(i), 'assistant', 'x', 'completed', '', '') for i in range(1001)])
        self.assertEqual(len(research.timeline('Test.lean')), 1000)
        self.assertEqual(len(research.export('Test.lean')['timeline']), 1002)
