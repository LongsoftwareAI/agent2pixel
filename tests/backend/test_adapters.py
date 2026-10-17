import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest
from services.worker.adapters import run_brain

@pytest.fixture
def provider_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.server.seen.append((self.path,body,self.headers.get('Authorization')))
            if body['model']=='failure':self.send_response(500);self.end_headers();return
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps({'message':{'content':'real HTTP answer'},'choices':[{'message':{'content':'real HTTP answer'}}],'usage':{'total_tokens':8},'eval_count':8}).encode())
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),Handler);server.seen=[]
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server
    server.shutdown();thread.join()

@pytest.mark.parametrize('provider,path',[('openai','/chat/completions'),('ollama','/api/chat')])
def test_http_adapter_success_failure(provider_server,monkeypatch,provider,path):
    monkeypatch.setenv('TEST_PROVIDER_SECRET','secret-test-only')
    agent=dict(role='Developer',system_prompt='Do work',brain=dict(provider=provider,model='test',secret_ref='TEST_PROVIDER_SECRET',endpoint=f'http://127.0.0.1:{provider_server.server_port}'))
    output,tokens=asyncio.run(run_brain(agent,'real input',200))
    assert output=='real HTTP answer' and tokens==8
    seen=provider_server.seen[-1];assert seen[0]==path and seen[1]['messages'][1]['content']=='real input'
    if provider=='openai':assert seen[2]=='Bearer secret-test-only'
    agent['brain']['model']='failure'
    with pytest.raises(ValueError,match='Provider request failed'):asyncio.run(run_brain(agent,'real input',200))

def test_missing_secret_and_budget(monkeypatch):
    agent=dict(role='Planner',system_prompt='x',brain=dict(provider='openai',model='x',secret_ref='MISSING_SECRET_TEST'))
    monkeypatch.delenv('MISSING_SECRET_TEST',raising=False)
    with pytest.raises(ValueError,match='not configured'):asyncio.run(run_brain(agent,'x',100))
    agent['brain']['provider']='mock'
    with pytest.raises(ValueError,match='budget'):asyncio.run(run_brain(agent,'x',1))
