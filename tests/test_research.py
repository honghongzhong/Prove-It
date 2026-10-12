"""Regression tests use a temporary workspace and the actually installed Lean."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from proveit import workspace, research
from proveit.codex_bridge import CodexBridge


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch.object(workspace, 'STATE_DIR', root / '.proveit'),
                        patch.object(workspace, 'DATABASE', root / '.proveit/state.sqlite3'),
                        patch.object(workspace, 'PROOFS', root / 'proofs')]
        for p in self.patches: p.start()
        self.source = 'theorem target : ∀ n : Nat, n = n := by intro n; rfl'
        workspace.create_proof('Test.lean', title='Reflexivity', source=self.source)
        self.goal = {'natural':'Every natural equals itself', 'formalType':'∀ n : Nat, n = n',
                     'targetName':'target', 'assumptions':'Natural numbers'}
        research.update('Test.lean', {'revision':0, 'goal':self.goal})

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_research_projects_preserve_conversation_identity(self):
        project = workspace.save_research_project('Number theory')
        proof = workspace.move_conversation('Test.lean', project['id'])
        self.assertEqual(proof['project_id'], project['id'])
        original_hash = proof['source_hash']
        workspace.rename_conversation('Test.lean', 'A new title')
        workspace.save_research_project('Arithmetic', project['id'])
        self.assertEqual(workspace.list_research_projects()[0]['conversation_count'], 1)
        self.assertEqual(workspace.get_proof('Test.lean')['source_hash'], original_hash)
        self.assertEqual(research.get('Test.lean')['goal'], self.goal)
        workspace.move_conversation('Test.lean', None)
        self.assertEqual(workspace.list_research_projects()[0]['conversation_count'], 0)
        with self.assertRaises(ValueError):
            workspace.move_conversation('Test.lean', 'missing')
        with self.assertRaises(ValueError):
            workspace.create_proof('Missing.lean', title='Missing', project_id='missing')
        self.assertFalse((workspace.PROOFS / 'Missing.lean').exists())

    def test_language_and_theme_persist(self):
        workspace.save_settings({'language':'en','theme':'dark'})
        self.assertEqual(workspace.get_settings()['language'], 'en')
        self.assertEqual(workspace.get_settings()['theme'], 'dark')

    def test_real_lean_target_and_staleness(self):
        result = research.check('Test.lean', self.source, 'standalone')
        self.assertTrue(result['targetVerified'], result)
        self.assertTrue(research.get('Test.lean')['targetVerified'])
        state = research.get('Test.lean')
        research.update('Test.lean', {'revision':state['revision'], 'review':True})
        self.assertTrue(research.get('Test.lean')['goalReviewed'])
        state = research.get('Test.lean')
        research.update('Test.lean', {'revision':state['revision'], 'goal':{**self.goal,'formalType':'True'}})
        self.assertFalse(research.get('Test.lean')['targetVerified'])
        self.assertFalse(research.get('Test.lean')['goalReviewed'])

    def test_wrong_target_is_rejected(self):
        result = research.check('Test.lean', 'theorem target : True := by trivial', 'standalone')
        self.assertFalse(result['targetVerified'])
        self.assertEqual(result['status'], 'rejected')
        self.assertTrue(result['diagnostics'])

    def test_sorry_not_a_proof(self):
        result = research.check('Test.lean', 'theorem target : ∀ n : Nat, n = n := by sorry', 'standalone')
        self.assertFalse(result['targetVerified'])

    def test_extra_axiom_not_a_proof(self):
        source = 'axiom invented : ∀ n : Nat, n = n\ntheorem target : ∀ n : Nat, n = n := invented'
        result = research.check('Test.lean', source, 'standalone')
        self.assertFalse(result['targetVerified'])
        self.assertIn('invented', result['axioms'])

    def test_only_helper_is_not_target(self):
        result = research.check('Test.lean', 'theorem helper : True := by trivial', 'standalone')
        self.assertFalse(result['targetVerified'])

    def test_comment_sorry_does_not_reject(self):
        result = research.check('Test.lean', self.source + '\n-- sorry is not used', 'standalone')
        self.assertTrue(result['targetVerified'], result)

    def test_revision_and_human_review(self):
        with self.assertRaises(ValueError):
            research.update('Test.lean', {'revision':0, 'review':True})
        with self.assertRaises(ValueError):
            research.update('Test.lean', {'revision':1, 'review':True}, 'codex')

    def test_step_cycles(self):
        steps=[{'id':'a','title':'A','status':'planned','dependsOn':['b']},
               {'id':'b','title':'B','status':'planned','dependsOn':['a']}]
        with self.assertRaises(ValueError):
            research.update('Test.lean', {'revision':1,'steps':steps})

    def test_source_write_conflict(self):
        proof=workspace.get_proof('Test.lean')
        with self.assertRaises(ValueError):
            workspace.save_proof('Test.lean', {**proof,'expectedSourceHash':'outdated','source':'-- changed'})
        bridge=CodexBridge()
        with self.assertRaises(ValueError):
            bridge._execute('proveit_modify_lean_code',{'code':'-- changed','sourceHash':'outdated'},'Test.lean','standalone')
        self.assertEqual(workspace.get_proof('Test.lean')['source'],self.source)

    def test_rename_retains_research_and_messages(self):
        research.message('Test.lean','user','Try induction')
        workspace.rename_proof('Test.lean','Renamed.lean')
        self.assertEqual(research.get('Renamed.lean')['goal'],self.goal)
        self.assertEqual(research.messages('Renamed.lean')[0]['content'],'Try induction')

    def test_recover_interrupted_run(self):
        research.set_runtime('Test.lean',runStatus='running',threadId='saved-thread')
        research.recover_runs()
        state=research.get('Test.lean')
        self.assertEqual(state['runStatus'],'paused')
        self.assertEqual(state['threadId'],'saved-thread')

    def test_natural_proof_conflict_and_history(self):
        workspace.save_natural_proof('Test.lean','First argument',expected_content='')
        with self.assertRaises(ValueError):
            workspace.save_natural_proof('Test.lean','Overwrite',expected_content='')
        workspace.save_natural_proof('Test.lean','Revised argument',expected_content='First argument')
        self.assertEqual(research.export('Test.lean')['naturalProofHistory'][-1]['content'],'First argument')

    def test_restore_plan_preserves_new_revision(self):
        state=research.get('Test.lean')
        research.update('Test.lean',{'revision':state['revision'],'goal':{**self.goal,'natural':'Changed wording'}})
        state=research.get('Test.lean')
        restored=research.restore('Test.lean',1,state['revision'])
        self.assertEqual(restored['goal'],self.goal)
        self.assertGreater(restored['revision'],state['revision'])
        self.assertFalse(restored['goalReviewed'])

    def test_source_changes_invalidate_evidence(self):
        research.check('Test.lean',self.source,'standalone')
        proof=workspace.get_proof('Test.lean')
        workspace.save_proof('Test.lean',{**proof,'source':self.source+'\n-- edit'})
        self.assertFalse(research.get('Test.lean')['targetVerified'])




class BridgeTests(unittest.TestCase):
    def test_schema_names_are_unique_and_review_is_not_exposed(self):
        from proveit.research_tools import tools
        names=[x['name'] for x in tools()]
        self.assertEqual(len(names),len(set(names)))
        update=next(x for x in tools() if x['name']=='proveit_update_research')
        self.assertNotIn('review',update['inputSchema']['properties'])

    def test_pause_drops_queued_work(self):
        bridge=CodexBridge()
        bridge.requests.put(('test','standalone','Test.lean'))
        bridge.pause()
        self.assertTrue(bridge.cancel.is_set())
        self.assertEqual(bridge.requests.qsize(),0)


class HttpTests(unittest.TestCase):
    setUp = ResearchTests.setUp
    tearDown = ResearchTests.tearDown
    # HTTP integration shares the isolated workspace, but avoids inherited Lean cases.
    def test_http_boundaries_and_round_trip(self):
        import threading
        import urllib.request
        import urllib.error
        from proveit.http_server import ProveItHTTPServer, Handler
        server=ProveItHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base+'/api/proofs/Test.lean/workflow') as response:
                value=json.load(response)
            self.assertEqual(value['workflow']['goal'],self.goal)
            body=json.dumps({'source':self.source,'result':{'status':'verified'}}).encode()
            forged=urllib.request.Request(base+'/api/proofs/Test.lean/verification',data=body,headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(forged)
            self.assertEqual(caught.exception.code,403)
            cross_origin=urllib.request.Request(base+'/api/settings',data=b'{}',method='PUT',headers={'Origin':'https://untrusted.example'})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(cross_origin)
            self.assertEqual(caught.exception.code,403)
            with urllib.request.urlopen(base+'/api/proofs/Test.lean/bundle') as response:
                bundle=json.load(response)['bundle']
            self.assertEqual(bundle['proof']['source'],self.source)
            self.assertEqual(bundle['researchHistory'][0]['state']['goal'],self.goal)
            def request(path, payload=None, method='GET'):
                req = urllib.request.Request(base+path, data=json.dumps(payload).encode() if payload is not None else None,
                    method=method, headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req) as response:
                    return json.load(response)
            project = request('/api/projects', {'name':'Topology'}, 'POST')['project']
            request('/api/projects/'+project['id'], {'name':'Geometry'}, 'PUT')
            request('/api/proofs/Test.lean/project', {'projectId':project['id']}, 'PUT')
            request('/api/proofs/Test.lean/title', {'title':'A new display title'}, 'PUT')
            listing = request('/api/projects')['projects']
            self.assertEqual(listing[0]['name'], 'Geometry')
            self.assertEqual(listing[0]['conversation_count'], 1)
            saved = request('/api/proofs/Test.lean')['proof']
            self.assertEqual(saved['source'], self.source)
            self.assertEqual(saved['id'], 'Test.lean')
            self.assertEqual(saved['title'], 'A new display title')
            request('/api/settings', {'language':'en','theme':'dark'}, 'PUT')
            self.assertEqual(request('/api/settings')['settings']['language'], 'en')

        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
