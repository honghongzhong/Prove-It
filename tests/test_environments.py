"""Managed-environment regressions: local downloads, archive safety and product integration."""
import hashlib
import io
import json
import os
import stat
import sys
import threading
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from proveit import environments, lean, research, workspace
from proveit.codex_bridge import CodexBridge
from proveit.research_tools import tools
import test_research

class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.manager = environments.EnvironmentManager()
        self.more = [patch.object(lean, "REGISTRY", Path(self.temp.name) / "projects.json"), patch.object(environments, "manager", self.manager)]
        for item in self.more: item.start()
    def tearDown(self):
        self.manager.shutdown()
        for thread in self.manager._threads.values(): thread.join(timeout=5)
        for item in reversed(self.more): item.stop()
        test_research.ResearchTests.tearDown(self)

    def seed_job(self):
        self.manager._load()
        self.manager._jobs['test'] = {"id":"test", "preset":"core", "status":"running", "stage":"checking", "log":[], "createdAt":"", "updatedAt":"", "progress":None, "error":None, "result":None}
        self.manager._cancel['test'] = threading.Event()
        self.manager._persist()
        return 'test'

    def test_ui_snapshot_does_not_wait_for_slow_version_probes(self):
        entered, release = threading.Event(), threading.Event()
        def slow_version(command):
            entered.set()
            release.wait(3)
            return 'Lean version 4.34.1'
        with patch.object(environments, '_quick_version', side_effect=slow_version) as probe:
            try:
                started = time.monotonic()
                snapshot = environments.status_snapshot()
                self.assertLess(time.monotonic() - started, .5)
                self.assertTrue(snapshot['checking'])
                self.assertFalse(snapshot['leanReady'])
                self.assertTrue(entered.wait(1))
                for _ in range(5):
                    self.assertTrue(environments.status_snapshot()['checking'])
                self.assertEqual(probe.call_count, 1)
            finally:
                release.set()
            deadline = time.monotonic() + 3
            while environments.status_snapshot()['checking'] and time.monotonic() < deadline:
                time.sleep(.01)
            snapshot = environments.status_snapshot()
            self.assertFalse(snapshot['checking'])
            self.assertTrue(snapshot['leanReady'])
            self.assertEqual(probe.call_count, 2)

    def test_core_reuses_installed_lean_and_actually_checks(self):
        result = self.manager.wait('core')
        self.assertTrue(result['smokeVerified'])
        self.assertTrue(Path(result['lean']).is_file())
        self.assertEqual(environments.manifest()['core']['version'], environments.VERSION)
        self.assertEqual(self.manager.jobs()[-1]['status'], 'ready')

    def test_presets_reject_model_urls_and_commands(self):
        for value in ('https://example.com/script', '../core', 'core && delete', '', None):
            with self.assertRaises(ValueError): self.manager.start(value)

    def test_setup_deduplicates_and_cancel_does_not_claim_ready(self):
        entered = threading.Event()
        def core(job_id):
            entered.set()
            while True:
                self.manager._check(job_id); time.sleep(.01)
        with patch.object(self.manager, '_core', side_effect=core):
            first = self.manager.start('core'); self.assertTrue(entered.wait(3))
            self.assertEqual(self.manager.start('core')['id'], first['id'])
            self.manager.cancel(first['id'])
            self.manager._threads[first['id']].join(3)
        self.assertEqual(self.manager.job(first['id'])['status'], 'cancelled')
        self.assertNotIn('core', environments.manifest())

    def test_failed_smoke_never_registers_ready(self):
        with patch.object(self.manager, '_core', side_effect=RuntimeError('Lean smoke failed')):
            with self.assertRaisesRegex(RuntimeError, 'Lean smoke failed'): self.manager.wait('core')
        self.assertEqual(self.manager.jobs()[-1]['status'], 'failed')
        self.assertNotIn('core', environments.manifest())

    def test_restart_marks_unfinished_job_interrupted(self):
        self.seed_job()
        restarted = environments.EnvironmentManager()
        self.assertEqual(restarted.jobs()[0]['status'], 'interrupted')

    def test_archive_rejects_path_traversal_and_links(self):
        job = self.seed_job()
        for index, name in enumerate(('../outside.txt', '/outside.txt', 'C:/outside.txt', 'folder\\..\\..\\outside.txt', 'link')):
            archive = Path(self.temp.name) / f'{index}.zip'
            with zipfile.ZipFile(archive,'w') as z:
                if name == 'link':
                    info = zipfile.ZipInfo(name); info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(info, '../outside')
                else: z.writestr(name, 'unsafe')
            with self.assertRaises(ValueError): self.manager._extract(job, archive, Path(self.temp.name)/f'stage{index}')
        self.assertFalse((Path(self.temp.name)/'outside.txt').exists())

    def test_download_resume_checksum_and_cached_reuse(self):
        data = b'checked-download-content'
        ranges = []
        class Endpoint(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                value = self.headers.get('Range'); ranges.append(value)
                offset = int(value.split('=')[1].split('-')[0]) if value else 0
                self.send_response(206 if value else 200)
                if value: self.send_header('Content-Range', f'bytes {offset}-{len(data)-1}/{len(data)}')
                self.send_header('Content-Length',str(len(data)-offset)); self.end_headers(); self.wfile.write(data[offset:])
        server=ThreadingHTTPServer(('127.0.0.1',0),Endpoint)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            job=self.seed_job()
            destination=environments.root()/'downloads';destination.mkdir(parents=True)
            (destination/'fixture.zip.part').write_bytes(data[:5])
            asset={'name':'fixture.zip','url':f'http://127.0.0.1:{server.server_port}/download','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            result=self.manager._download(job,asset)
            self.assertEqual(result.read_bytes(),data)
            self.assertEqual(ranges,['bytes=5-'])
            self.assertEqual(self.manager._download(job,asset),result)
            self.assertEqual(len(ranges),1)
            bad={**asset,'name':'bad.zip','sha256':'0'*64}
            with self.assertRaisesRegex(RuntimeError,'checksum'): self.manager._download(job,bad)
            self.assertFalse((destination/'bad.zip').exists())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_auto_mathlib_selection_and_disabled_policy(self):
        with patch.object(self.manager,'wait',return_value={'projectId':'prepared-mathlib'}) as waiting:
            self.assertEqual(environments.prepare('import Mathlib\ntheorem t : True := by trivial','standalone'),'prepared-mathlib')
            waiting.assert_called_once_with('mathlib',None)
            workspace.save_settings({'autoSetupLean':False})
            waiting.reset_mock()
            self.assertEqual(environments.prepare('import Mathlib','standalone'),'standalone')
            waiting.assert_not_called()

    def test_model_setup_selects_environment_but_never_approves_goal(self):
        bridge=CodexBridge();bridge.current_proof_id='Test.lean'
        with patch.object(self.manager,'wait',return_value={'projectId':'standalone','smokeVerified':True}) as waiting:
            result=bridge._execute('proveit_setup_environment',{'preset':'core'},'Test.lean','standalone')
            self.assertTrue(result['smokeVerified']);waiting.assert_called_once()
            self.assertFalse(research.get('Test.lean')['targetVerified'])
            self.assertFalse(research.get('Test.lean')['goalReviewed'])
            workspace.save_settings({'autoSetupLean':False})
            with self.assertRaises(ValueError): bridge._execute('proveit_setup_environment',{'preset':'core'},'Test.lean','standalone')

    def test_managed_runtime_changes_invalidate_old_evidence(self):
        research.check('Test.lean',self.source,'standalone')
        self.assertTrue(research.get('Test.lean')['targetVerified'])
        binary=Path(self.temp.name)/'managed/bin/lean.exe';binary.parent.mkdir(parents=True);binary.write_bytes(b'fixture')
        lake=binary.with_name('lake.exe');lake.write_bytes(b'fixture')
        environments._write_json(environments.root()/'installed.json',{'core':{'lean':str(binary),'lake':str(lake)}})
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(environments.runtime_env()['LEAN_EXE'],str(binary))
            self.assertFalse(research.get('Test.lean')['verificationCurrent'])

    def test_proxy_is_validated(self):
        self.assertEqual(environments.validate_proxy('http://127.0.0.1:10808'),'http://127.0.0.1:10808')
        for value in ('file:///tmp','http://user:secret@example.com','https://example.com?token=a'):
            with self.assertRaises(ValueError): environments.validate_proxy(value)

    def test_thread_upgrades_environment_tool_schema_without_losing_local_goal(self):
        research.set_runtime('Test.lean',threadId='previous')
        bridge=CodexBridge();bridge.call=Mock(side_effect=[{}, {'thread':{'id':'upgraded'}}])
        bridge._select_thread('Test.lean')
        state=research.get('Test.lean')
        self.assertEqual(state['threadId'],'upgraded')
        self.assertEqual(state['previousThreadIds'],['previous'])
        self.assertEqual(state['goal'],self.goal)
        self.assertEqual(state['toolSchemaHash'],research.digest(tools()))
        self.assertIn('proveit_setup_environment',[t['name'] for t in bridge.call.call_args_list[-1].args[1]['dynamicTools']])

    def test_interrupted_git_lock_recovery_is_managed_only(self):
        job=self.seed_job()
        self.manager._jobs['previous']={'id':'previous','preset':'mathlib','status':'interrupted'}
        project=environments.root()/'projects/mathlib-4.34.1'
        git=project/'.lake/packages/aesop/.git';git.mkdir(parents=True)
        lock=git/'index.lock';lock.write_text('left by interrupted setup')
        self.manager._recover_git_locks(job,project)
        self.assertFalse(lock.exists())
        self.assertEqual(len(list(git.glob('index.lock.interrupted-*'))),1)
        outside=Path(self.temp.name)/'user-project';outside.mkdir()
        with self.assertRaises(ValueError): self.manager._recover_git_locks(job,outside)

    def test_command_timeout_stops_process_tree(self):
        job=self.seed_job()
        started=time.monotonic()
        with self.assertRaisesRegex(RuntimeError,'timed out'):
            self.manager._command(job,[sys.executable,'-c','import time; time.sleep(30)'],timeout=.2)
        self.assertLess(time.monotonic()-started,10)

    def test_windows_proxy_is_inherited_by_git_and_cache_tools(self):
        if os.name != 'nt': self.skipTest('Windows system proxy behavior')
        with patch.object(environments.urllib.request,'getproxies',return_value={'https':'http://127.0.0.1:9999'}):
            env=environments.process_env()
            self.assertEqual(env['HTTPS_PROXY'],'http://127.0.0.1:9999')
            self.assertEqual(env['HTTP_PROXY'],'http://127.0.0.1:9999')

    def test_cache_network_limits_are_local_and_progress_is_sanitized(self):
        job=self.seed_job()
        env=self.manager._cache_env({'HTTPS_PROXY':'http://127.0.0.1:9999'})
        self.assertEqual(env['HTTPS_PROXY'],'http://127.0.0.1:9999')
        config=Path(env['CURL_HOME'])/'.curlrc'
        self.assertIn('max-time = 120',config.read_text())
        self.assertIn('parallel-max = 8',config.read_text())
        self.manager._update(job,stage='dependencies',line='Downloaded [attempted 6/10 = 60%]\x1b[K')
        latest=self.manager.job(job)
        self.assertEqual(latest['progress'],60)
        self.assertNotIn('\x1b',latest['log'][-1])
