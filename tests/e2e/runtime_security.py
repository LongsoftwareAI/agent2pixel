"""QA-authored integration regression, run with application Python environment.
.venv/bin/python -m pytest tests/e2e/runtime_security.py -q
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from fastapi.testclient import TestClient
from services.api.main import create_app


def wait(client, run_id):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        run=client.get('/api/runs/'+run_id).json()
        if run['state'] not in ('queued','running'):
            return run
        time.sleep(.02)
    raise AssertionError('run timeout')


def test_condition_true_cross_workspace_and_step_bound(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        workspaces=client.get('/api/workspaces').json()
        data=client.get('/api/bootstrap',params={'workspace_id':workspaces[0]['id']}).json()
        graph={'nodes':[{'id':'s','type':'start'},{'id':'c','type':'condition','condition':{'field':'input','equals':'yes'}},
                        {'id':'a','type':'agent','agent_id':data['agents'][0]['id']},{'id':'e','type':'end'}],
               'edges':[{'source':'s','target':'c'},{'source':'c','target':'a','label':'true'},
                        {'source':'c','target':'e','label':'false'},{'source':'a','target':'e'}]}
        wf=client.post('/api/workflows',json={'workspace_id':workspaces[0]['id'],'name':'QA branch','graph':graph}).json()
        run=client.post('/api/workflows/'+wf['id']+'/runs',json={'input':'yes'}).json()
        result=wait(client,run['id'])
        assert result['state']=='completed' and len(result['tasks'])==1
        assert 'yes' in result['output']
        bounded=client.post('/api/workflows/'+wf['id']+'/runs',json={'input':'yes','max_steps':1}).json()
        assert wait(client,bounded['id'])['state']=='failed'
        foreign=client.post('/api/workflows',json={'workspace_id':workspaces[1]['id'],'name':'QA foreign','graph':graph})
        assert foreign.status_code==400 and 'workspace' in foreign.text
        client.post('/api/memories',json={'workspace_id':workspaces[0]['id'],'content':'QA namespace secret-like marker'})
        assert client.get('/api/memories',params={'workspace_id':workspaces[1]['id']}).json()==[]


def test_cancel_during_real_provider_http_and_no_late_success(tmp_path):
    received=threading.Event()
    release=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            received.set();release.wait(timeout=5)
            body=json.dumps({'message':{'content':'late answer'},'eval_count':1}).encode()
            try:
                self.send_response(200);self.end_headers();self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):
                pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with TestClient(create_app(tmp_path)) as client:
            ws=client.get('/api/workspaces').json()[0]
            data=client.get('/api/bootstrap',params={'workspace_id':ws['id']}).json()
            agent=data['agents'][0]
            response=client.patch('/api/agents/'+agent['id'],json={'brain':{'provider':'ollama','model':'stub','endpoint':f'http://127.0.0.1:{server.server_port}'}})
            assert response.status_code==200
            run=client.post('/api/workflows/'+data['workflows'][0]['id']+'/runs',json={'input':'QA cancel real HTTP'}).json()
            assert received.wait(timeout=5)
            assert client.post('/api/runs/'+run['id']+'/cancel').status_code==200
            release.set();time.sleep(.25)
            value=client.get('/api/runs/'+run['id']).json()
            assert value['state']=='cancelled'
            events=client.get('/api/runs/'+run['id']+'/events').json()
            assert not any(e['event_type']=='workflow.completed' for e in events)
            assert all(task['state']=='cancelled' for task in value['tasks'])
    finally:
        release.set();server.shutdown();server.server_close();thread.join(timeout=2)
