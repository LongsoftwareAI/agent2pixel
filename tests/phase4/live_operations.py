"""Independent actual HTTP queue, provenance, memory audit and evidence comparison acceptance."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from difflib import unified_diff
import hashlib
import json
from pathlib import Path
import time

from acceptance_support import API, ProviderFixture
from live_acceptance import agent, graph


def run(args):
    api = API(args.base)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    result = {'passed': False, 'application_sha': args.sha, 'provider': 'local HTTP fixture, not live inference'}
    with ProviderFixture() as provider:
        provider.delay = 1.5
        ws = api.ok('/api/workspaces', {'name': 'P4 Ops QA '+str(time.time_ns())})
        actor = agent(api, ws, provider, 'QA Queue Analyst', [])
        workflow = api.ok('/api/workflows', {'workspace_id': ws['id'], 'name': 'QA queue actual work',
            'graph': graph([{'id': 'analysis', 'type': 'agent', 'agent_id': actor['id'], 'instructions': 'Report only supplied briefing.'}])})
        items = []
        for title, priority, due in [('low', 'low', '2000-01-01T00:00:00Z'), ('high-later', 'high', '2030-01-01T00:00:00Z'), ('high-first', 'high', '2020-01-01T00:00:00Z')]:
            item = api.ok('/api/work-items', {'workspace_id': ws['id'], 'workflow_id': workflow['id'], 'title': title,
                'description': 'Supplied queue briefing '+title, 'acceptance_criteria': ['State unknowns'],
                'priority': priority, 'due_at': due, 'owner_agent_id': actor['id']})
            api.ok('/api/work-items/'+item['id']+'/enqueue', {})
            items.append(item)
        ordered = api.ok('/api/work-queue?workspace_id='+ws['id'])
        assert [i['title'] for i in ordered] == ['high-first', 'high-later', 'low'], ordered
        with ThreadPoolExecutor(max_workers=2) as pool:
            dispatches = list(pool.map(lambda _index: api.request('/api/work-queue/dispatch', {'workspace_id': ws['id']}), range(2)))
        assert sorted(status for status, _body in dispatches) == [200, 409], dispatches
        execution = next(body for status, body in dispatches if status == 200)
        assert execution['work_item_id'] == items[2]['id']
        for _ in range(1000):
            if provider.requests:
                break
            time.sleep(.005)
        assert provider.requests, 'Actual adapter must contact local provider'
        operations = api.ok('/api/operations?workspace_id='+ws['id'])
        assert execution['id'] in operations['active_run_ids']
        load = next(value for value in operations['agents'] if value['agent_id'] == actor['id'])
        assert execution['id'] in load['active_run_ids']
        assert [i['id'] for i in api.ok('/api/work-queue?workspace_id='+ws['id'])] == [items[1]['id'], items[0]['id']]
        completed = api.wait(execution['id'])
        assert completed['state'] == 'completed', completed
        operations = api.ok('/api/operations?workspace_id='+ws['id'])
        assert operations['active_run_ids'] == [] and operations['queue_count'] == 2
        api.ok('/api/work-items/'+items[0]['id']+'/dequeue', {})
        assert [i['id'] for i in api.ok('/api/work-queue?workspace_id='+ws['id'])] == [items[1]['id']]

        if args.queue_only:
            result.update(passed=True, scope='queue-only; source/memory/diff not run', workspace_id=ws['id'], dispatch_statuses=[s for s, _ in dispatches], chosen_work_item_id=execution['work_item_id'], queue_order=[i['title'] for i in ordered], checks=['actual priority/due queue', 'concurrent dispatch200/409 and pending retention', 'worker load from actual run states'])
            (out/'live-queue.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result, indent=2))
            return True
        source_text = 'QA_PROVENANCE: only twelve supplied cases'
        source = api.ok('/api/sources', {'workspace_id': ws['id'], 'name': 'Provenance fixture', 'content': source_text, 'media_type': 'text/plain'})
        memory = api.ok('/api/memories', {'workspace_id': ws['id'], 'scope': 'agent', 'agent_id': actor['id'], 'content': 'Initial supplied observation', 'source_id': source['id']})
        assert memory['provenance']['sha256'] == hashlib.sha256(source_text.encode()).hexdigest()
        assert any(m['id'] == memory['id'] for m in api.ok('/api/memories?workspace_id='+ws['id']+'&scope=agent&agent_id='+actor['id']))
        foreign_ws = api.ok('/api/workspaces', {'name': 'Foreign source QA '+str(time.time_ns())})
        foreign_source = api.ok('/api/sources', {'workspace_id': foreign_ws['id'], 'name': 'Foreign source', 'content': 'must not become own provenance', 'media_type': 'text/plain'})
        api.denied('/api/memories/'+memory['id'], {'source_id': foreign_source['id']}, 'PATCH')
        api.denied('/api/memories/'+memory['id'], {'agent_id': 'another-agent'}, 'PATCH')
        updated = api.ok('/api/memories/'+memory['id'], {'content': 'Revised supplied observation', 'source_id': source['id']}, 'PATCH')
        assert updated['scope'] == 'agent' and updated['agent_id'] == actor['id']
        history = api.ok('/api/memories/'+memory['id']+'/history')
        assert len(history) == 1 and history[0]['before']['content'] == 'Initial supplied observation'
        api.ok('/api/memories/'+memory['id'], method='DELETE')
        history = api.ok('/api/memories/'+memory['id']+'/history')
        assert [entry['action'] for entry in history] == ['edited', 'deleted']
        assert all(m['id'] != memory['id'] for m in api.ok('/api/memories?workspace_id='+ws['id']+'&scope=agent&agent_id='+actor['id']))

        # Compare two genuinely generated completed runs of one revised work item.
        provider.delay = 0
        item_id = items[2]['id']
        api.ok('/api/work-items/'+item_id+'/review', {'decision': 'changes_requested', 'comment': 'Need revised briefing evidence.'})
        api.ok('/api/work-items/'+item_id, {'description': 'QA_REVISED_BRIEF: focus on pending operational uncertainties.'}, 'PATCH')
        revised = api.ok('/api/work-items/'+item_id+'/runs', {})
        revised_result = api.wait(revised['id'])
        assert revised_result['state'] == 'completed'
        comparison = api.ok('/api/work-items/'+item_id+'/comparison?previous_run_id='+execution['id']+'&current_run_id='+revised['id'])
        expected_diff = ''.join(unified_diff(completed['output'].splitlines(keepends=True), revised_result['output'].splitlines(keepends=True), fromfile='previous/output', tofile='current/output'))
        assert comparison['diffs'][0]['diff'] == expected_diff and expected_diff
        assert comparison['acceptance_criteria'] == ['State unknowns']
        foreign_workflow = api.ok('/api/workflows', {'workspace_id': foreign_ws['id'], 'name': 'Foreign completed', 'graph': graph([])})
        foreign_run = api.ok('/api/workflows/'+foreign_workflow['id']+'/runs', {'input': 'Foreign run'})
        assert api.wait(foreign_run['id'])['state'] == 'completed'
        api.denied('/api/work-items/'+item_id+'/comparison?previous_run_id='+execution['id']+'&current_run_id='+foreign_run['id'])
        result.update(passed=True, workspace_id=ws['id'], dispatch_statuses=[s for s, _ in dispatches], chosen_work_item_id=execution['work_item_id'], queue_order=[i['title'] for i in ordered], memory_history=history, comparison=comparison,
            checks=['actual priority/due queue', 'concurrent dispatch200/409 and pending retention', 'worker load from actual run states', 'same-scope provenance and foreign source denial', 'memory edit/delete retained history and hidden deleted item', 'actual revised-run exact unified diff and foreign-run denial'])
        (out/'live-operations.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--queue-only', action='store_true', help='Explicit partial acceptance while Sources API is not yet integrated')
    raise SystemExit(0 if run(parser.parse_args()) else 1)
