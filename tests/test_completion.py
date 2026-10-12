"""Verified goals must also persist a natural proof before research completes."""
import json
import os
import unittest
from unittest.mock import Mock, patch
from proveit import research, workspace, model_api
from proveit.codex_bridge import CodexBridge
import test_research

PROSE = "Let n be an arbitrary natural number. Equality is reflexive, so n = n. As n was arbitrary, the statement holds for every natural number."

class CompletionTests(unittest.TestCase):
    def setUp(self):
        test_research.ResearchTests.setUp(self)
        result=research.check('Test.lean',self.source,'standalone')
        self.assertTrue(result['targetVerified'],result)
        self.bridge=CodexBridge();self.bridge.current_proof_id='Test.lean'
    def tearDown(self):
        test_research.ResearchTests.tearDown(self)
    def prose_call(self, content=PROSE, source_hash=None):
        return {'content': 'Explanation saved.', 'tool_calls':[{'id':'prose','type':'function','function':{'name':'proveit_propose_natural_proof','arguments':json.dumps({'content':content,'sourceHash':source_hash or research.artifact_hash(workspace.get_proof('Test.lean'))})}}]}
    def assert_completed(self):
        state=research.get('Test.lean')
        self.assertEqual(state['runStatus'],'completed')
        self.assertTrue(state['targetVerified'])
        self.assertFalse(state['goalReviewed'])
        self.assertEqual(workspace.get_proof('Test.lean')['source'],self.source)
        self.assertTrue(workspace.get_proof('Test.lean')['natural_proof'].strip())
        self.assertEqual(len(state['checks']),1)
    def test_api_chat_explanation_triggers_persisted_prose_repair(self):
        replies=[{'content':PROSE},self.prose_call()]
        with patch.object(model_api,'complete',side_effect=replies) as complete:
            self.bridge._run_api('Prove the goal','standalone','Test.lean','en')
        self.assertEqual(complete.call_count,2)
        self.assert_completed()
    def test_api_refusal_is_bounded_and_keeps_lean_evidence(self):
        with patch.object(model_api,'complete',return_value={'content':'Lean passed.'}) as complete:
            self.bridge._run_api('Finish','standalone','Test.lean','zh')
        self.assertEqual(complete.call_count,3)
        state=research.get('Test.lean')
        self.assertEqual(state['runStatus'],'blocked')
        self.assertIn('自然语言证明',state['runReason'])
        self.assertTrue(state['targetVerified'])
        self.assertEqual(workspace.get_proof('Test.lean')['natural_proof'],'')
    def test_codex_repair_runs_beyond_single_research_turn_budget(self):
        self.bridge.start=Mock();self.bridge._select_thread=Mock()
        turns=[]
        def call(method,params):
            self.assertEqual(method,'turn/start')
            turns.append(params)
            if len(turns)==2:
                self.bridge._execute('proveit_propose_natural_proof',{'content':PROSE,'sourceHash':research.artifact_hash(workspace.get_proof('Test.lean'))},'Test.lean','standalone')
            self.bridge.turn_text=[PROSE]
            self.bridge.completed.put({'id':str(len(turns)),'status':'completed'})
            return {'turn':{'id':str(len(turns))}}
        self.bridge.call=call
        with patch.dict(os.environ,{'PROVEIT_MAX_TURNS':'1'}):
            self.bridge._run('Finish','standalone','Test.lean','en')
        self.assertEqual(len(turns),2)
        self.assertIn('natural-language proof is empty',turns[1]['input'][0]['text'])
        self.assert_completed()
    def test_codex_refusal_does_not_complete_without_prose(self):
        self.bridge.start=Mock();self.bridge._select_thread=Mock()
        def call(method,params):
            self.bridge.completed.put({'id':'turn','status':'completed'})
            return {'turn':{'id':'turn'}}
        self.bridge.call=Mock(side_effect=call)
        with patch.dict(os.environ,{'PROVEIT_MAX_TURNS':'1'}):
            self.bridge._run('Finish','standalone','Test.lean','en')
        self.assertEqual(self.bridge.call.call_count,3)
        self.assertEqual(research.get('Test.lean')['runStatus'],'blocked')
        self.assertTrue(research.get('Test.lean')['targetVerified'])
    def test_existing_prose_is_preserved(self):
        workspace.save_natural_proof('Test.lean',PROSE)
        with patch.object(model_api,'complete',return_value={'content':'Done.'}) as complete:
            self.bridge._run_api('Summarize','standalone','Test.lean','en')
        self.assertEqual(complete.call_count,1)
        self.assertEqual(workspace.get_proof('Test.lean')['natural_proof'],PROSE)
        self.assert_completed()
    def test_blank_prose_tool_write_is_rejected(self):
        for value in ('', '  \n ', None):
            with self.assertRaises(ValueError):
                self.bridge._execute('proveit_propose_natural_proof',{'content':value,'sourceHash':research.artifact_hash(workspace.get_proof('Test.lean'))},'Test.lean','standalone')
        self.assertFalse(self.bridge._complete_research('Test.lean','en'))
    def test_prose_conflict_requires_fresh_hash(self):
        replies=[self.prose_call(source_hash='stale'),self.prose_call()]
        with patch.object(model_api,'complete',side_effect=replies):
            self.bridge._run_api('Finish','standalone','Test.lean','en')
        self.assertTrue(any(e['status']=='failed' for e in research.timeline('Test.lean')))
        self.assert_completed()
    def test_pause_during_finalization_does_not_write_or_complete(self):
        def complete(*args):
            self.bridge.cancel.set()
            return self.prose_call()
        with patch.object(model_api,'complete',side_effect=complete):
            self.bridge._run_api('Finish','standalone','Test.lean','en')
        self.assertEqual(research.get('Test.lean')['runStatus'],'paused')
        self.assertTrue(research.get('Test.lean')['targetVerified'])
        self.assertEqual(workspace.get_proof('Test.lean')['natural_proof'],'')

    def test_legacy_completed_without_prose_is_resumable(self):
        research.set_runtime('Test.lean',runStatus='completed')
        state=research.get('Test.lean')
        self.assertEqual(state['runStatus'],'blocked')
        self.assertTrue(state['targetVerified'])
        self.assertFalse(state['naturalProofSaved'])
        self.assertIn('natural-language proof',state['runReason'])
        workspace.save_natural_proof('Test.lean',PROSE)
        self.assertEqual(research.get('Test.lean')['runStatus'],'completed')
