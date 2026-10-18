"""Independent Phase3 real-HTTP acceptance; local provider stub, never live-model evidence."""
import argparse
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class LocalProvider(BaseHTTPRequestHandler):
    requests = []
    outputs = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        content = body['messages'][-1]['content']
        output = '[LOCAL PROVIDER STUB — not live inference]\n' + content
        self.outputs.append(output)
        encoded = json.dumps({'message': {'content': output}, 'prompt_eval_count': 13, 'eval_count': 17}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class API:
    def __init__(self, base):
        self.base = base.rstrip('/')

    def request(self, path, body=None, method=None):
        encoded = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=encoded, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def ok(self, path, body=None, method=None):
        status, value = self.request(path, body, method)
        assert status == 200, (path, status, value)
        return value

    def denied(self, path, body=None, method=None):
        status, value = self.request(path, body, method)
        assert status in (400, 403, 404, 409, 422), (path, status, value)
        return status

    def wait(self, run_id):
        for _ in range(1000):
            run = self.ok('/api/runs/' + run_id)
            if run['state'] in ('completed', 'failed', 'cancelled', 'waiting_approval'):
                return run
            time.sleep(.03)
        raise AssertionError('Runtime did not settle')


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    api = API(args.base)
    LocalProvider.requests = []
    LocalProvider.outputs = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), LocalProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        templates = api.ok('/api/workflow-templates')
        assert len(templates) >= 4 and all(t['steps'] for t in templates), templates
        ws = api.ok('/api/workspaces', {'name': 'P3 Independent QA ' + str(time.time_ns())})
        source = Path(ws['root_path']) / 'qa-source.txt'
        source.write_text('LOCAL_SOURCE_QA: Customer satisfaction is 82 percent; 17 support cases remain open. No other facts supplied.\n')
        agents = []
        for role in ('Researcher', 'Editor'):
            agents.append(api.ok('/api/agents', {
                'workspace_id': ws['id'], 'name': 'P3 QA ' + role, 'role': role,
                'brain': {'provider': 'ollama', 'model': 'qa-local-stub', 'endpoint': f'http://127.0.0.1:{server.server_port}'},
                'tool_grants': [{'id': t, 'allow': True} for t in ('documents.read', 'documents.list', 'artifacts.write_text')]}))
        instructions = ['NODE_RESEARCH_QA: summarize only supplied source facts; identify missing information.',
                        'NODE_EDIT_QA: edit the preceding handoff; preserve factual limitations and list acceptance evidence.']
        nodes = [{'id': 'start', 'type': 'start'}]
        nodes += [{'id': 'step-' + str(i), 'type': 'agent', 'agent_id': agent['id'],
                   'instructions': instructions[i], 'deliverable': {'filename': ('brief.md', 'edited.txt')[i]}}
                  for i, agent in enumerate(agents)]
        nodes += [{'id': 'end', 'type': 'end'}]
        graph = {'nodes': nodes, 'edges': [{'source': a['id'], 'target': b['id']} for a, b in zip(nodes, nodes[1:])]}
        workflow = api.ok('/api/workflows', {'workspace_id': ws['id'], 'name': 'P3 QA Research to Editorial', 'graph': graph})
        brief = {'workspace_id': ws['id'], 'title': 'P3_QA_CUSTOM_BRIEF', 'description': 'BRIEF_QA: prepare a factual internal service report.',
                 'workflow_id': workflow['id'], 'acceptance_criteria': ['CRITERION_QA: report both satisfaction and unresolved cases', 'Explicitly disclose missing data']}
        item = api.ok('/api/work-items', brief)
        assert item['status'] == 'backlog', item
        run = api.ok('/api/work-items/' + item['id'] + '/runs', {})
        run_id = run['id']
        api.denied('/api/work-items/' + item['id'] + '/runs', {})
        api.denied('/api/work-items/' + item['id'], {'title': 'Cannot edit active brief'}, 'PATCH')
        api.denied('/api/work-items/' + item['id'] + '/review', {'decision': 'accepted', 'comment': 'Premature review forbidden'})
        approvals = []
        restart_checked = False
        for index in range(2):
            current = api.wait(run_id)
            assert current['state'] == 'waiting_approval', current
            pending = [a for a in api.ok('/api/runs/' + run_id + '/approvals') if a['status'] == 'pending']
            assert len(pending) == 1, pending
            approval = pending[0]
            assert approval['tool'] == 'artifacts.write_text', approval
            assert approval['workspace_id'] == ws['id'] and approval['run_id'] == run_id and approval['agent_id'] == agents[index]['id'], approval
            payload = approval['payload']
            assert payload['filename'] == ('brief.md', 'edited.txt')[index], payload
            assert payload['content'] == LocalProvider.outputs[index], (payload, LocalProvider.outputs)
            expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            assert expected == approval['payload_hash'], approval
            assert instructions[index] in LocalProvider.requests[index]['messages'][-1]['content']
            assert 'LOCAL_SOURCE_QA' in LocalProvider.requests[index]['messages'][-1]['content']
            assert 'BRIEF_QA' in LocalProvider.requests[index]['messages'][-1]['content']
            assert 'CRITERION_QA' in LocalProvider.requests[index]['messages'][-1]['content']
            assert not list(Path(ws['root_path']).rglob(payload['filename'])), 'Export happened before approval'
            if index == 0 and args.restart_marker:
                marker = Path(args.restart_marker)
                assert not marker.exists(), 'Restart marker must be new'
                checkpoint = {'workspace_id': ws['id'], 'item_id': item['id'], 'run_id': run_id,
                              'approval_id': approval['id'], 'provider_requests': len(LocalProvider.requests), 'state': 'waiting_for_integrator_restart'}
                (out / 'restart-checkpoint.json').write_text(json.dumps(checkpoint, indent=2) + '\n')
                print('READY_FOR_RESTART ' + json.dumps(checkpoint), flush=True)
                deadline = time.monotonic() + 180
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.2)
                assert marker.exists(), 'Integrator restart was not signaled'
                current = api.wait(run_id)
                assert current['state'] == 'waiting_approval', current
                assert len(LocalProvider.requests) == 1, 'Provider called again during paused restart'
                assert api.ok('/api/runs/' + run_id + '/approvals') == [approval]
                restart_checked = True
            approvals.append(approval['id'])
            api.ok('/api/approvals/' + approval['id'] + '/decision', {'decision': 'approved'})
        result = api.wait(run_id)
        assert result['state'] == 'completed', result
        assert len(LocalProvider.requests) == 2, 'Output regenerated after approval'
        assert len(result['artifacts']) == 2, result
        artifacts = []
        for index, artifact in enumerate(result['artifacts']):
            file = Path(ws['root_path']) / artifact['path']
            data = file.read_bytes()
            assert data.decode() == LocalProvider.outputs[index], artifact
            assert hashlib.sha256(data).hexdigest() == artifact['sha256'] and len(data) == artifact['size'], artifact
            artifacts.append(artifact)
        review_item = api.ok('/api/work-items/' + item['id'])
        assert review_item['status'] == 'review', review_item
        accepted = api.ok('/api/work-items/' + item['id'] + '/review', {'decision': 'accepted', 'comment': 'HUMAN_QA: inspected exact generated exports and source limitations'})
        assert accepted['status'] == 'done', accepted
        api.denied('/api/approvals/' + approvals[0] + '/decision', {'decision': 'approved'})
        other = api.ok('/api/workspaces', {'name': 'P3 Foreign QA ' + str(time.time_ns())})
        api.denied('/api/work-items', {**brief, 'workspace_id': other['id']})
        for filename in ('../escape.md', 'script.py', '/tmp/escape.txt'):
            bad_nodes = [dict(node) for node in nodes]
            bad_nodes[1] = {**bad_nodes[1], 'deliverable': {'filename': filename}}
            api.denied('/api/workflows', {'workspace_id': ws['id'], 'name': 'Invalid export', 'graph': {**graph, 'nodes': bad_nodes}})
        evidence = {'passed': True, 'application_sha': args.sha, 'provider': 'local HTTP Ollama-compatible stub; no live inference',
                    'runtime': 'actual API/LangGraph/SQLite/output export', 'workspace_id': ws['id'], 'work_item_id': item['id'], 'run_id': run_id,
                    'provider_requests': len(LocalProvider.requests), 'restart_checked': restart_checked, 'approvals': approvals,
                    'artifacts': artifacts, 'human_review': accepted, 'checks': ['custom instructions/source docs/brief/criteria reach actual provider',
                    'exact actual output export after approval only', 'no regeneration or duplicate file', 'artifact bytes/hash/size', 'completed means review, human accepted means done',
                    'active duplicate/edit and premature review denied', 'cross-workspace workflow denied', 'traversal/executable/absolute filename denied', 'approval reuse denied']}
        (out / 'live-acceptance.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2), flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--restart-marker')
    run(parser.parse_args())
