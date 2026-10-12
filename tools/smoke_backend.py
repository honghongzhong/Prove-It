"""Test the distributed backend using an empty temporary workspace and real Lean."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path


def smoke(executable):
    with tempfile.TemporaryDirectory(prefix='proveit-release-test-') as directory:
        env = dict(os.environ, PROVEIT_DATA_DIR=directory, PYTHONUTF8='1')
        process = subprocess.Popen([str(Path(executable).resolve())], env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8')
        timer = threading.Timer(90, process.kill)
        timer.start()
        try:
            ready = json.loads(process.stdout.readline())
            assert ready['ready']
            base = f"http://127.0.0.1:{ready['port']}"
            def request(path, body=None, method=None):
                data = json.dumps(body).encode() if body is not None else None
                req = urllib.request.Request(base + path, data=data, method=method,
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    return json.load(response)
            assert request('/api/proofs')['proofs'] == []
            assert request('/api/settings')['settings']['language'] == 'en'
            request('/api/settings', {'language': 'zh'}, 'PUT')
            assert request('/api/settings')['settings']['language'] == 'zh'
            source = 'theorem release_target : ∀ n : Nat, n = n := by intro n; rfl'
            request('/api/proofs', {'filename': 'Smoke.lean', 'title': 'Release test', 'source': source})
            request('/api/proofs/Smoke.lean/workflow', {'revision': 0, 'goal': {
                'natural': 'Every natural number equals itself.', 'targetName': 'release_target',
                'formalType': '∀ n : Nat, n = n', 'assumptions': ''}}, 'PUT')
            result = request('/api/lean/verify', {'filename': 'Smoke.lean', 'source': source, 'projectId': 'standalone'})
            assert result['targetVerified'], result
            state = request('/api/proofs/Smoke.lean/workflow')['workflow']
            assert state['verificationCurrent'] and state['targetVerified']
            with urllib.request.urlopen(base + '/', timeout=10) as response:
                assert b'ProveIt' in response.read()
            if '--codex' in sys.argv:
                models = request('/api/codex/models')['models']
                assert models and all(model.get('model') for model in models)
                print(f'PASS: packaged Codex model discovery ({len(models)} models)')
            process.stdin.close()
            assert process.wait(timeout=15) == 0
            print('PASS: empty workspace, frozen verifier, real target validation, UI assets, clean shutdown')
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()


if __name__ == '__main__':
    smoke(sys.argv[1])
