"""Two-step actual-process restart check. Operator restarts app between prepare/verify.

This script never restarts any process itself and never claims TestClient reloads
are process restarts. Evidence identifies deterministic mock inference explicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase4'))
from acceptance_support import API  # noqa: E402
from live_acceptance import graph  # noqa: E402


def prepare(api, args):
    ws = api.ok('/api/workspaces', {'name': 'P5 Process Restart Synthetic '+str(time.time_ns())})
    actor = api.ok('/api/agents', {'workspace_id': ws['id'], 'name': 'Synthetic Restart Analyst', 'role': 'Analyst',
        'tool_grants': [{'id': 'artifacts.write_text', 'allow': True}]})
    flow = api.ok('/api/workflows', {'workspace_id': ws['id'], 'name': 'Restart human review', 'graph': graph([
        {'id': 'draft', 'type': 'agent', 'agent_id': actor['id'], 'deliverable': {'filename': 'restart-synthetic.md'}},
        {'id': 'review', 'type': 'review', 'instructions': 'Human review after actual restart', 'rework_target': 'draft', 'max_revisions': 1}])})
    conversation = api.ok('/api/console/conversations', {'workspace_id': ws['id'], 'agent_id': actor['id'], 'title': 'Synthetic restart conversation'})
    path = '/api/console/conversations/'+conversation['id']+'/messages?workspace_id='+ws['id']
    payload = {'content': 'Synthetic restart evidence; deterministic mock inference only.', 'client_request_id': 'restart-probe', 'workflow_id': flow['id']}
    dispatch = api.ok(path, payload)
    paused = api.wait(dispatch['run_id'])
    assert paused['state'] == 'waiting_approval', paused
    approvals = api.ok('/api/runs/'+paused['id']+'/approvals')
    approval = next(row for row in approvals if row['status'] == 'pending')
    api.ok('/api/approvals/'+approval['id']+'/decision', {'decision': 'approved'})
    paused = api.wait(paused['id'])
    gates = api.ok('/api/runs/'+paused['id']+'/gates')
    gate = next(row for row in gates if row['status'] == 'pending')
    assert len(paused['artifacts']) == 1
    detail = api.ok('/api/console/conversations/'+conversation['id']+'?workspace_id='+ws['id'])
    return {'application_sha': args.sha, 'prepared_at': time.time(), 'provider': 'deterministic mock; not live inference',
        'workspace_id': ws['id'], 'conversation_id': conversation['id'], 'dispatch': dispatch, 'payload': payload,
        'gate_id': gate['id'], 'artifacts': paused['artifacts'], 'message_ids': sorted(m['id'] for m in detail['messages']),
        'passed': False, 'state': 'AWAITING_ACTUAL_PROCESS_RESTART'}


def verify(api, before, args):
    assert before['application_sha'] == args.sha
    wid = before['workspace_id']
    cid = before['conversation_id']
    run_id = before['dispatch']['run_id']
    paused = api.ok('/api/runs/'+run_id)
    assert paused['state'] == 'waiting_approval' and paused['artifacts'] == before['artifacts']
    detail = api.ok('/api/console/conversations/'+cid+'?workspace_id='+wid)
    assert sorted(m['id'] for m in detail['messages']) == before['message_ids']
    duplicate = api.ok('/api/console/conversations/'+cid+'/messages?workspace_id='+wid, before['payload'])
    assert duplicate['run_id'] == run_id and duplicate['work_item_id'] == before['dispatch']['work_item_id']
    gates = api.ok('/api/runs/'+run_id+'/gates')
    assert any(row['id'] == before['gate_id'] and row['status'] == 'pending' for row in gates)
    for artifact in paused['artifacts']:
        value = api.ok('/api/runs/'+run_id+'/artifacts/'+artifact['id'])
        assert hashlib.sha256(value['content'].encode()).hexdigest() == artifact['sha256']
    api.ok('/api/gates/'+before['gate_id']+'/decision', {'decision': 'approved', 'comment': 'Independent synthetic restart verification'})
    finished = api.wait(run_id)
    assert finished['state'] == 'completed' and finished['artifacts'] == before['artifacts']
    item = api.ok('/api/work-items/'+before['dispatch']['work_item_id']+'/review', {'decision': 'accepted', 'comment': 'QA acceptance after actual restart'})
    assert item['status'] == 'done'
    return {**before, 'passed': True, 'verified_at': time.time(), 'state': 'VERIFIED_AFTER_OPERATOR_PROCESS_RESTART',
        'checks': ['stable conversation/message/run/work/gate IDs', 'same-key duplicate dispatch after restart deduplicates', 'artifact hashes unchanged', 'pending QC resumes to completed and separate human acceptance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'verify'])
    parser.add_argument('--base', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--snapshot', required=True)
    args = parser.parse_args()
    api = API(args.base)
    path = Path(args.snapshot)
    if args.mode == 'prepare':
        assert not path.exists(), 'Never overwrite prior restart evidence'
        value = prepare(api, args)
    else:
        value = verify(api, json.loads(path.read_text()), args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps({'state': value['state'], 'run_id': value['dispatch']['run_id'], 'passed': value['passed']}))
