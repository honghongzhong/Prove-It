"""Frozen API completion regression against a local model stub and real Lean."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE="theorem target : ∀ n : Nat, n = n := by intro n; rfl"
PROSE="Let n be arbitrary. Reflexivity of equality yields n = n. Since no additional assumption on n was used, the statement holds for all natural numbers."
requests=[]
class Model(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(payload)
        if len(requests)==1:
            name,args='proveit_verify_lean',{'code':SOURCE}
        elif len(requests)==2:
            reply={'role':'assistant','content':PROSE}
            self.respond(reply);return
        else:
            digest=hashlib.sha256(json.dumps([SOURCE,''],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            name,args='proveit_propose_natural_proof',{'content':PROSE,'sourceHash':digest}
        self.respond({'role':'assistant','content':'Saved.', 'tool_calls':[{'id':'call-'+str(len(requests)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]})
    def respond(self,reply):
        data=json.dumps({'choices':[{'message':reply}]}).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

if __name__=='__main__':
    model=ThreadingHTTPServer(('127.0.0.1',0),Model)
    thread=threading.Thread(target=model.serve_forever,daemon=True);thread.start()
    with tempfile.TemporaryDirectory(prefix='proveit-prose-smoke-') as directory:
        p=subprocess.Popen([str(Path(sys.argv[1]).resolve())],env={**os.environ,'PROVEIT_DATA_DIR':directory,'PYTHONUTF8':'1'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        try:
            ready=json.loads(p.stdout.readline());base=f"http://127.0.0.1:{ready['port']}"
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def request(path,body=None,method='GET'):
                req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json'})
                with opener.open(req,timeout=30) as response:return json.load(response)
            request('/api/settings',{'provider':'api','baseUrl':f'http://127.0.0.1:{model.server_port}/v1','apiModel':'local-test','apiKey':'fake-local-key'},'PUT')
            request('/api/proofs',{'filename':'Test.lean','title':'Natural proof completion','source':SOURCE},'POST')
            request('/api/proofs/Test.lean/workflow',{'revision':0,'goal':{'natural':'Every natural equals itself.','formalType':'∀ n : Nat, n = n','targetName':'target','assumptions':''}},'PUT')
            request('/api/codex/message',{'filename':'Test.lean','message':'Prove the goal.','context':SOURCE,'projectId':'standalone','language':'en'},'POST')
            deadline=time.monotonic()+90
            while True:
                state=request('/api/proofs/Test.lean/workflow')['workflow']
                if state['runStatus'] in {'completed','failed','blocked'}:break
                assert time.monotonic()<deadline,'completion timeout'
                time.sleep(.3)
            proof=request('/api/proofs/Test.lean')['proof']
            assert state['runStatus']=='completed' and state['targetVerified'],state
            assert proof['natural_proof']==PROSE and proof['source']==SOURCE
            assert len(requests)==3 and not state['goalReviewed']
            report={'frozen':True,'modelCalls':len(requests),'targetVerified':state['targetVerified'],'naturalProofSaved':state['naturalProofSaved'],'sourcePreserved':proof['source']==SOURCE,'goalReviewed':state['goalReviewed']}
            Path('build/completion-0.7.1-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:
            p.stdin.close()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            model.shutdown();model.server_close();thread.join()
