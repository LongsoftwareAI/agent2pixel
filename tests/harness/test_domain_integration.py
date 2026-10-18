"""Actual Store + LangGraph + SDK/runtime/Cordis bridge, local provider only.

Approved fixture writes/tests are committed by LangGraph BEFORE the Harness turn.
The Harness calls read/retrieve results; it does not cause a new code write.
"""
import contextlib
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app
from services.worker.executors.harness import capabilities


class WorkflowProvider(BaseHTTPRequestHandler):
    requests = []
    calls = []
    response = 'HARNESS_DOMAIN_VERIFIED'

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        index = sum(m.get('role') == 'tool' for m in body.get('messages', []))
        if index < len(self.calls):
            tool, payload = self.calls[index]
            delta = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': f'call_{index}', 'type': 'function',
                'function': {'name': 'agentverse_dispatch', 'arguments': json.dumps({'tool_id': tool, 'payload': payload})}}]}
            finish = 'tool_calls'
        else:
            delta = {'role': 'assistant', 'content': self.response}
            finish = 'stop'
        chunks = [dict(id='stub', object='chat.completion.chunk', model='stub',
            choices=[dict(index=0, delta=delta, finish_reason=None)]),
            dict(id='stub', object='chat.completion.chunk', model='stub',
            choices=[dict(index=0, delta={}, finish_reason=finish)], usage={'total_tokens': 16, 'prompt_tokens': 10, 'completion_tokens': 6})]
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        with contextlib.suppress(BrokenPipeError):
            for chunk in chunks:
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')


def wait(client, run_id):
    for _ in range(1500):
        value = client.get('/api/runs/'+run_id).json()
        if value['state'] in ('completed', 'failed', 'waiting_approval', 'cancelled'):
            return value
        time.sleep(.01)
    raise AssertionError('Workflow timeout')


@pytest.mark.skipif(not capabilities()['available'], reason='Pinned official Harness pair required')
@pytest.mark.parametrize('denied_calls', [False, True])
def test_real_mixed_workflow_shared_tools_and_committed_approval(tmp_path, denied_calls):
    WorkflowProvider.requests = []
    WorkflowProvider.response = 'HARNESS_DOMAIN_VERIFIED'
    WorkflowProvider.calls = [('memory.read', {}), ('documents.read', {'path': 'fixture.txt'}), ('tests.run_pytest', {})]
    if denied_calls:
        WorkflowProvider.calls += [('documents.read', {'path': '../private.txt'}), ('tests.run_pytest', {'unapproved': True}), ('memory.read', {'agent_id': 'other'})]
    server = ThreadingHTTPServer(('127.0.0.1', 0), WorkflowProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with patch.dict(os.environ, {'AGENTVERSE_TEST_HARNESS_KEY': 'local-stub-only'}), TestClient(create_app(tmp_path)) as client:
            workspace = client.get('/api/workspaces').json()[0]
            b = client.get('/api/bootstrap', params={'workspace_id': workspace['id']}).json()
            developer = b['agents'][1]
            Path(workspace['root_path'], 'fixture.txt').write_text('REAL_DOCUMENT_EVIDENCE')
            app = client.app
            for ident, agent_id, content in [('own', developer['id'], 'OWN_MEMORY_EVIDENCE'), ('other', b['agents'][0]['id'], 'FOREIGN_AGENT_MEMORY'), ('shared', None, 'WORKSPACE_PRIVATE_MEMORY')]:
                app.state.store.put('memory', dict(id=ident, workspace_id=workspace['id'], agent_id=agent_id, kind='fact', content=content))
            tools = ['memory.read', 'documents.read', 'tests.run_pytest', 'artifacts.write_python']
            response = client.patch('/api/agents/'+developer['id'], json={
                'execution': {'engine': 'deepseek_harness', 'profile': 'agentverse-registry-v1'},
                'brain': {'provider': 'deepseek', 'model': 'stub', 'endpoint': f'http://127.0.0.1:{server.server_port}', 'secret_ref': 'AGENTVERSE_TEST_HARNESS_KEY'},
                'role_config': {'id': 'developer', 'version': 1, 'instructions': 'ROLE_CONTRACT_EVIDENCE', 'responsibilities': ['verify']},
                'skill_bindings': [{'id': 'code-report', 'version': 1}],
                'tool_grants': [{'id': t, 'allow': True} for t in tools], 'memory_config': {'scope': 'agent'}})
            assert response.status_code == 200, response.text
            actions = [dict(agent_id=developer['id'], tool='artifacts.write_python', payload={'filename': filename, 'template': template})
                for filename, template in [('calculator.py', 'calculator-v1'), ('test_calculator.py', 'calculator-tests-v1')]]
            actions.append(dict(agent_id=developer['id'], tool='tests.run_pytest', payload={}))
            response = client.post('/api/workflows/'+b['workflows'][0]['id']+'/runs', json={'input': 'Read evidence and report', 'actions': actions})
            assert response.status_code == 200, response.text
            run_id = response.json()['id']
            for _ in actions:
                current = wait(client, run_id)
                assert current['state'] == 'waiting_approval', current
                pending = [a for a in client.get('/api/runs/'+run_id+'/approvals').json() if a['status'] == 'pending']
                assert len(pending) == 1
                assert client.post('/api/approvals/'+pending[0]['id']+'/decision', json={'decision': 'approved'}).status_code == 200
            result = wait(client, run_id)
            assert result['state'] == 'completed', result
            assert result['tasks'][1]['output'] == 'HARNESS_DOMAIN_VERIFIED'
            assert len(result['tasks']) == 3
            assert result['artifacts'][-1]['exit_code'] == 0
            assert '2 passed' in result['artifacts'][-1]['report']
            requests = json.dumps(WorkflowProvider.requests)
            assert 'ROLE_CONTRACT_EVIDENCE' in requests
            assert 'Skill code-report v1' in requests
            tool_messages = json.dumps([m for request in WorkflowProvider.requests for m in request.get('messages', []) if m.get('role') == 'tool'])
            assert 'OWN_MEMORY_EVIDENCE' in tool_messages
            assert 'FOREIGN_AGENT_MEMORY' not in tool_messages
            assert 'WORKSPACE_PRIVATE_MEMORY' not in tool_messages
            assert 'REAL_DOCUMENT_EVIDENCE' in tool_messages
            assert '2 passed' in tool_messages
            events = client.get('/api/runs/'+run_id+'/events').json()
            actual_calls = [e['payload']['tool'] for e in events if e['event_type'] == 'harness.tool.completed']
            assert actual_calls == [call[0] for call in WorkflowProvider.calls[:3]]
            failures = [e for e in events if e['event_type'] == 'harness.tool.failed']
            assert len(failures) == (3 if denied_calls else 0)
            # A model may still emit a final answer after tool rejection. Durable failed
            # tool events remain explicit; a final text is not evidence of tool success.
            assert len(result['artifacts']) == 3
            assert len([e for e in events if e['event_type'] == 'task.completed']) == 3
            assert (tmp_path/'checkpoints.sqlite3').is_file()
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.skipif(not capabilities()['available'], reason='Pinned official Harness pair required')
@pytest.mark.parametrize('decision', ['approved', 'denied'])
def test_real_harness_operations_export_is_post_generation_and_restart_safe(tmp_path, decision):
    WorkflowProvider.requests = []
    WorkflowProvider.response = '# Operations report\n\nSource fixture: twelve support cases.\nRisk: reviewer capacity unknown.'
    # Even a granted model-origin write must fail before generation/approval.
    WorkflowProvider.calls = [('artifacts.write_text', {'filename': 'premature.md', 'content': 'UNAPPROVED'})]
    server = ThreadingHTTPServer(('127.0.0.1', 0), WorkflowProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    objective = 'OPERATIONS_NODE_OBJECTIVE: summarize supplied cases; identify staffing uncertainty.'
    try:
        with patch.dict(os.environ, {'AGENTVERSE_TEST_HARNESS_KEY': 'local-stub-only'}):
            with TestClient(create_app(tmp_path)) as client:
                workspace = client.get('/api/workspaces').json()[0]
                agent = client.get('/api/agents', params={'workspace_id': workspace['id']}).json()[0]
                response = client.patch('/api/agents/'+agent['id'], json={
                    'execution': {'engine': 'deepseek_harness', 'profile': 'agentverse-registry-v1'},
                    'brain': {'provider': 'deepseek', 'model': 'stub', 'endpoint': f'http://127.0.0.1:{server.server_port}', 'secret_ref': 'AGENTVERSE_TEST_HARNESS_KEY'},
                    'tool_grants': [{'id': 'artifacts.write_text', 'allow': True}],
                    'role_config': {'id': 'operations-analyst', 'version': 1, 'instructions': 'Analyze operations evidence only', 'responsibilities': ['operations']}})
                assert response.status_code == 200, response.text
                graph = {'nodes': [{'id': 'start', 'type': 'start'},
                    {'id': 'operations', 'type': 'agent', 'agent_id': agent['id'], 'instructions': objective,
                     'deliverable': {'filename': 'operations.md'}}, {'id': 'end', 'type': 'end'}],
                    'edges': [{'source': 'start', 'target': 'operations'}, {'source': 'operations', 'target': 'end'}]}
                response = client.post('/api/workflows', json={'workspace_id': workspace['id'], 'name': 'Operations Harness', 'graph': graph})
                assert response.status_code == 200, response.text
                workflow_id = response.json()['id']
                response = client.post('/api/workflows/'+workflow_id+'/runs', json={'input': 'Supplied source fixture: twelve support cases; reviewer capacity unknown.'})
                assert response.status_code == 200, response.text
                run_id = response.json()['id']
                paused = wait(client, run_id)
                assert paused['state'] == 'waiting_approval', paused
                assert paused['tasks'][0]['output'] == WorkflowProvider.response
                assert paused['tasks'][0]['tokens'] == 32
                assert objective in json.dumps(WorkflowProvider.requests)
                assert not list(Path(workspace['root_path']).rglob('operations.md'))
                assert not list(Path(workspace['root_path']).rglob('premature.md'))
                approvals = client.get('/api/runs/'+run_id+'/approvals').json()
                assert len(approvals) == 1
                approval = approvals[0]
                assert approval['tool'] == 'artifacts.write_text'
                assert approval['node_id'] == 'operations'
                assert approval['payload'] == {'filename': 'operations.md', 'content': WorkflowProvider.response}
                events = client.get('/api/runs/'+run_id+'/events').json()
                assert len([e for e in events if e['event_type'] == 'harness.tool.failed']) == 1
                request_count = len(WorkflowProvider.requests)
                assert request_count == 2
            # Actual app restart while generated output is pending exact approval.
            with TestClient(create_app(tmp_path)) as client:
                assert client.get('/api/runs/'+run_id).json()['state'] == 'waiting_approval'
                response = client.post('/api/approvals/'+approval['id']+'/decision', json={'decision': decision})
                assert response.status_code == 200, response.text
                result = wait(client, run_id)
                assert len(WorkflowProvider.requests) == request_count, 'Resume must not call model again'
                assert result['tasks'][0]['tokens'] == 32
                assert not list(Path(workspace['root_path']).rglob('premature.md'))
                if decision == 'approved':
                    assert result['state'] == 'completed', result
                    assert len(result['artifacts']) == 1
                    artifact = result['artifacts'][0]
                    assert artifact['node_id'] == 'operations'
                    assert artifact['run_id'] == run_id
                    assert artifact['agent_id'] == agent['id']
                    data = (Path(workspace['root_path'])/artifact['path']).read_bytes()
                    assert data == WorkflowProvider.response.encode()
                    import hashlib
                    assert artifact['sha256'] == hashlib.sha256(data).hexdigest()
                    assert artifact['size'] == len(data)
                    assert len(list(Path(workspace['root_path']).rglob('operations.md'))) == 1
                else:
                    assert result['state'] == 'failed', result
                    assert result['artifacts'] == []
                    assert not list(Path(workspace['root_path']).rglob('operations.md'))
    finally:
        server.shutdown()
        server.server_close()
