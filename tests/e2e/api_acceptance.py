"""Independent contract acceptance against a running disposable localhost instance.
Run: python tests/e2e/api_acceptance.py --base http://127.0.0.1:8000
Creates uniquely named QA workspace; never deletes existing data.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    checks = []

    def request(path, method='GET', data=None, expected=200):
        body = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(args.base + path, data=body, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                status, payload = res.status, json.load(res)
        except urllib.error.HTTPError as error:
            status, payload = error.code, json.load(error)
        accepted = [expected] if isinstance(expected, int) else expected
        assert status in accepted, (method, path, status, payload)
        return payload

    def check(name, fn):
        try:
            fn()
            checks.append({'name': name, 'result': 'PASS'})
        except Exception as error:
            checks.append({'name': name, 'result': 'FAIL', 'error': str(error)})

    check('health schema', lambda: require(request('/health')['schema_version'] == 1))
    workspaces = request('/api/workspaces')
    assert len(workspaces) >= 2, workspaces
    workspace = request('/api/workspaces', 'POST', {'name': 'QA-' + str(uuid.uuid4())[:8]}, [200, 201])
    wid = workspace['id']
    bootstrap = request('/api/bootstrap?workspace_id=' + wid)
    agents = []
    for role in ('Planner', 'Developer', 'Reviewer'):
        agents.append(request('/api/agents', 'POST', {
            'workspace_id': wid, 'name': 'QA ' + role, 'role': role,
            'brain': {'provider': 'mock', 'model': 'mock-v1'},
        }, [200, 201]))
    nodes = [{'id': 'start', 'type': 'start'}]
    nodes += [{'id': agent['role'].lower(), 'type': 'agent', 'agent_id': agent['id']} for agent in agents]
    nodes += [{'id': 'end', 'type': 'end'}]
    edges = [{'source': left['id'], 'target': right['id']} for left, right in zip(nodes, nodes[1:])]
    wf = request('/api/workflows', 'POST', {'workspace_id': wid, 'name': 'QA handoff',
        'graph': {'nodes': nodes, 'edges': edges}}, [200, 201])
    check('seed graph validates', lambda: require(request('/api/workflows/' + wf['id'] + '/validate', 'POST')['valid']))

    def runtime():
        run = request('/api/workflows/' + wf['id'] + '/runs', 'POST', {'input': 'QA create a reproducible release checklist'}, [200, 201, 202])
        deadline = time.monotonic() + 30
        while run['state'] in ('queued', 'running') and time.monotonic() < deadline:
            time.sleep(.15)
            run = request('/api/runs/' + run['id'])
        assert run['state'] == 'completed', run
        tasks = run['tasks']
        assert len(tasks) >= 3, tasks
        assert all(task['output'] for task in tasks), tasks
        for previous, current in zip(tasks, tasks[1:]):
            assert previous['output'] in str(current['input']), (previous, current)
        messages = request('/api/runs/' + run['id'] + '/messages')
        assert len(messages) >= 2, messages
        assert all(all(key in msg for key in ('run_id', 'sender', 'recipient', 'payload', 'timestamp', 'correlation_id')) for msg in messages)
        events = request('/api/runs/' + run['id'] + '/events')
        seqs = [event['seq'] for event in events]
        assert seqs == sorted(set(seqs)), seqs
        assert any(event['event_type'] == 'workflow.completed' for event in events)
        replay = request('/api/events?workspace_id=' + wid + '&after=' + str(seqs[-2]))
        assert all(event['seq'] > seqs[-2] for event in replay), replay
    check('actual persisted handoff, message envelope and replay', runtime)

    def invalid_graph():
        graph = {'nodes': [{'id': 'start', 'type': 'start'}, {'id': 'end', 'type': 'end'}],
                 'edges': [{'source': 'start', 'target': 'end'}, {'source': 'end', 'target': 'start'}]}
        bad = request('/api/workflows', 'POST', {'workspace_id': wid, 'name': 'QA cycle', 'graph': graph}, [200, 201, 400, 422])
        if 'id' in bad:
            assert request('/api/workflows/' + bad['id'] + '/validate', 'POST')['valid'] is False
    check('cyclic graph rejected', invalid_graph)

    check('workspace traversal denied', lambda: request('/api/documents/content?workspace_id=' + wid + '&path=../outside.txt', expected=[400, 403]))
    check('metadata does not expose raw secret', lambda: require('api_key' not in json.dumps(request('/api/settings')).lower()))
    check('unknown provider rejected', lambda: request('/api/providers/test', 'POST', {'provider': 'unsafe', 'model': 'test'}, [400, 422]))
    print(json.dumps({'workspace_id': wid, 'checks': checks}, indent=2))
    if any(item['result'] == 'FAIL' for item in checks):
        raise SystemExit(1)


def require(condition):
    assert condition


if __name__ == '__main__':
    main()
