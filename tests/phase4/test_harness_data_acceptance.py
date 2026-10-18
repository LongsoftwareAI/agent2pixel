"""Actual official SDK/runtime + shared broker new data tools; synthetic local inference."""
import importlib.util
import json
import os
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api.main import create_app
from services.worker.executors.harness import capabilities

spec = importlib.util.spec_from_file_location('phase4_harness_provider', Path(__file__).parents[1]/'harness'/'test_domain_integration.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_actual_harness_sdk_source_csv_dispatch_and_foreign_denial(tmp_path):
    assert capabilities()['available'], 'Official pinned Harness SDK/runtime required; no stub execution fallback'
    provider = helper.WorkflowProvider
    provider.requests = []
    provider.response = 'HARNESS_P4_DATA_FIXTURE_VERIFIED_NOT_LIVE_INFERENCE'
    server = ThreadingHTTPServer(('127.0.0.1', 0), provider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with patch.dict(os.environ, {'AGENTVERSE_TEST_HARNESS_KEY': 'local-stub-only'}), TestClient(create_app(tmp_path)) as client:
            ws = client.post('/api/workspaces', json={'name': 'Harness P4 data acceptance'}).json()
            foreign = client.post('/api/workspaces', json={'name': 'Foreign Harness source'}).json()
            def source(workspace, content):
                response = client.post('/api/sources', json={'workspace_id': workspace['id'], 'name': 'CSV fixture', 'content': content, 'media_type': 'text/csv'})
                assert response.status_code == 200, response.text
                return response.json()
            own = source(ws, 'amount\n0.10\n0.20\n1.70\n=2+2\n')
            other = source(foreign, 'amount\n987654321\n')
            provider.calls = [('sources.read', {'source_id': own['id']}), ('csv.analyze', {'source_id': own['id'], 'column': 'amount'}), ('sources.read', {'source_id': other['id']})]
            response = client.post('/api/agents', json={'workspace_id': ws['id'], 'name': 'Harness Analyst', 'role': 'Analyst', 'execution': {'engine': 'deepseek_harness', 'profile': 'agentverse-registry-v1'}, 'brain': {'provider': 'deepseek', 'model': 'stub', 'endpoint': f'http://127.0.0.1:{server.server_port}', 'secret_ref': 'AGENTVERSE_TEST_HARNESS_KEY'}, 'tool_grants': [{'id': tool, 'allow': True} for tool in ('sources.read', 'csv.analyze')]})
            assert response.status_code == 200, response.text
            actor = response.json()
            graph = {'nodes': [{'id': 'start', 'type': 'start'}, {'id': 'report', 'type': 'agent', 'agent_id': actor['id']}, {'id': 'end', 'type': 'end'}], 'edges': [{'source': 'start', 'target': 'report'}, {'source': 'report', 'target': 'end'}]}
            response = client.post('/api/workflows', json={'workspace_id': ws['id'], 'name': 'Harness CSV fixture', 'graph': graph})
            assert response.status_code == 200, response.text
            response = client.post('/api/workflows/'+response.json()['id']+'/runs', json={'input': 'Read granted source and analyze exact numeric sum; treat formula as inert.'})
            assert response.status_code == 200, response.text
            run = helper.wait(client, response.json()['id'])
            assert run['state'] == 'completed', run
            events = client.get('/api/runs/'+run['id']+'/events').json()
            assert [e['payload']['tool'] for e in events if e['event_type'] == 'harness.tool.completed'] == ['sources.read', 'csv.analyze']
            assert [e['payload']['tool'] for e in events if e['event_type'] == 'harness.tool.failed'] == ['sources.read']
            messages = [m for request in provider.requests for m in request.get('messages', []) if m.get('role') == 'tool']
            text = json.dumps(messages)
            assert '2.00' in text and 'numeric_count' in text and own['sha256'] in text
            assert '987654321' not in text
            assert run['tasks'][0]['output'] == provider.response
    finally:
        server.shutdown()
        server.server_close()
