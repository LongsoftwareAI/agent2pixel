"""Independent crash-window surrogate: existing orphan file never overwritten or regenerated."""
from pathlib import Path
import time
from fastapi.testclient import TestClient
from services.api.main import create_app


def settled(client, run_id):
    for _ in range(500):
        value = client.get('/api/runs/'+run_id).json()
        if value['state'] in ('waiting_approval', 'completed', 'failed', 'cancelled'):
            return value
        time.sleep(.01)
    raise AssertionError('Run did not settle')


def test_consumed_uncertain_export_requires_reconciliation_without_overwrite(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        workspace = client.post('/api/workspaces', json={'name': 'Uncertain export fixture'}).json()
        actor = client.post('/api/agents', json={'workspace_id': workspace['id'], 'name': 'Analyst',
            'role': 'Analyst', 'tool_grants': [{'id': 'artifacts.write_text', 'allow': True}]}).json()
        workflow = client.post('/api/workflows', json={'workspace_id': workspace['id'], 'name': 'Crash-window fixture',
            'graph': {'nodes': [{'id': 'start', 'type': 'start'}, {'id': 'report', 'type': 'agent', 'agent_id': actor['id'], 'deliverable': {'filename': 'report.md'}}, {'id': 'end', 'type': 'end'}],
            'edges': [{'source': 'start', 'target': 'report'}, {'source': 'report', 'target': 'end'}]}}).json()
        response = client.post('/api/workflows/'+workflow['id']+'/runs', json={'input': 'Supplied facts only'})
        assert response.status_code == 200, response.text
        run_id = response.json()['id']
        before = settled(client, run_id)
        assert before['state'] == 'waiting_approval'
        approval = client.get('/api/runs/'+run_id+'/approvals').json()[0]
        # Model an artifact already materialized but lacking its committed tool_result.
        # This is explicitly a crash-window surrogate, not an actual killed-write claim.
        orphan = Path(workspace['root_path'])/'artifacts'/run_id/'report.md'
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(b'UNCERTAIN_SIDE_EFFECT_MUST_SURVIVE')
        assert client.post('/api/approvals/'+approval['id']+'/decision', json={'decision': 'approved'}).status_code == 200
        failed = settled(client, run_id)
        assert failed['state'] == 'failed' and failed['artifacts'] == []
        assert client.app.state.store.get('approval', approval['id'])['status'] == 'consumed'
        assert orphan.read_bytes() == b'UNCERTAIN_SIDE_EFFECT_MUST_SURVIVE'
        tokens = failed['token_spent']
        assert client.post('/api/runs/'+run_id+'/resume').status_code == 200
        retried = settled(client, run_id)
        assert retried['state'] == 'failed'
        assert retried['token_spent'] == tokens
        assert retried['tasks'][0]['output'] == before['tasks'][0]['output']
        assert orphan.read_bytes() == b'UNCERTAIN_SIDE_EFFECT_MUST_SURVIVE'
        assert len(list(orphan.parent.iterdir())) == 1
