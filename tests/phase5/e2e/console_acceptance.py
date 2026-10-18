"""Independent real-HTTP Phase5 acceptance. Only model inference uses a local fixture."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase4'))
from acceptance_support import API, ProviderFixture, tool_envelope  # noqa: E402
from live_acceptance import agent, finish, graph  # noqa: E402


def run(args):
    api = API(args.base)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {'application_sha': args.sha, 'passed': False,
              'inference': 'loopback HTTP fixture; not live inference', 'checks': []}
    try:
        with ProviderFixture() as provider:
            ws = api.ok('/api/workspaces', {'name': 'P5 Independent QA '+str(time.time_ns())})
            foreign = api.ok('/api/workspaces', {'name': 'P5 Foreign QA '+str(time.time_ns())})
            wid = ws['id']
            actor = agent(api, ws, provider, 'Synthetic QA Analyst', ['csv.analyze', 'artifacts.write_text'])
            source = api.ok('/api/sources', {'workspace_id': wid, 'name': 'Synthetic decimal evidence',
                'media_type': 'text/csv', 'content': 'team,amount\nA,0.10\nA,0.20\nB,1.70\n'})
            flow = api.ok('/api/workflows', {'workspace_id': wid, 'name': 'P5 real CSV review', 'graph': graph([
                {'id': 'calculate', 'type': 'tool', 'agent_id': actor['id'],
                 'tool': {'id': 'csv.analyze', 'payload': {'source_id': source['id'], 'column': 'amount', 'group_by': 'team'}}},
                {'id': 'report', 'type': 'agent', 'agent_id': actor['id'], 'instructions': 'Report only actual supplied CSV facts.',
                 'deliverable': {'filename': 'p5-qa-report.md'}},
                {'id': 'review', 'type': 'review', 'instructions': 'Verify supplied facts.', 'rework_target': 'report', 'max_revisions': 1}])})
            conversation = api.ok('/api/console/conversations', {'workspace_id': wid, 'agent_id': actor['id'], 'title': 'Synthetic QA conversation'})
            cid = conversation['id']
            payload = {'content': 'Analyze supplied CSV evidence, preserve unknowns.', 'client_request_id': 'qa-'+str(time.time_ns()), 'workflow_id': flow['id']}
            message = api.ok('/api/console/conversations/'+cid+'/messages?workspace_id='+wid, payload)
            duplicate = api.ok('/api/console/conversations/'+cid+'/messages?workspace_id='+wid, payload)
            assert duplicate['run_id'] == message['run_id']
            assert api.request('/api/console/conversations/'+cid+'/messages?workspace_id='+wid, {**payload, 'content': 'Changed request'})[0] == 409
            run = api.ok('/api/runs/'+message['run_id'])
            item = api.ok('/api/work-items/'+message['work_item_id'])
            completed = finish(api, item, run, provider)
            assert completed['artifacts'], completed
            assert provider.requests, 'Actual runtime did not call local HTTP adapter'
            analysis = tool_envelope(provider.requests[0])['result']
            assert Decimal(analysis['columns']['amount']['sum']) == Decimal('2.00')
            assert Decimal(analysis['groups']['A']['amount']['sum']) == Decimal('0.30')
            durable = api.ok('/api/runs/'+run['id']+'/tool-results')
            assert len(durable) == 1 and json.loads(durable[0]['output'])['result'] == analysis
            current = api.ok('/api/console/conversations/'+cid+'?workspace_id='+wid)
            assert current['messages'], current
            report['checks'].append('chat creates real CSV workflow, generated artifact, separate approvals/QC/work acceptance; duplicate same key stable and changed payload409')
            for endpoint in ('overview', 'inbox', 'sessions', 'health', 'topology', 'usage', 'schedules', 'skills', 'capabilities'):
                value = api.ok('/api/console/'+endpoint+'?workspace_id='+wid)
                report.setdefault('reads', {})[endpoint] = value
            usage = report['reads']['usage']['totals']
            assert usage['actual_cost'] is None and usage['estimated_cost'] is None, usage
            assert any(row.get('run_id', row.get('id')) == run['id'] for row in report['reads']['sessions'])
            assert api.request('/api/console/usage?workspace_id='+wid+'&period=invalid')[0] in (400, 422)
            report['checks'].append('actual read projections and unknown monetary spend; invalid usage period denied')
            attachment_body = {'workspace_id': wid, 'name': 'synthetic.csv', 'media_type': 'text/csv', 'content': 'n\n0.10\n'}
            attachment = api.ok('/api/console/attachments', attachment_body)
            assert attachment['sha256'] == hashlib.sha256(attachment_body['content'].encode()).hexdigest()
            api.denied('/api/console/attachments', {**attachment_body, 'name': '../escape.csv'})
            api.denied('/api/console/attachments', {**attachment_body, 'media_type': 'audio/mpeg'})
            report['checks'].append('attachment actual content hash; traversal and unsupported audio rejected')
            foreign_actor = agent(api, foreign, provider, 'Foreign Synthetic Analyst', [])
            api.denied('/api/console/conversations', {'workspace_id': wid, 'agent_id': foreign_actor['id'], 'title': 'Rejected mixed scope'})
            report['checks'].append('foreign agent cannot bind conversation')
            report.update(passed=True, workspace_id=wid, conversation_id=cid, run_id=run['id'], work_item_id=item['id'])
    except Exception as exc:
        report['failure'] = repr(exc)
        raise
    finally:
        (out/'console-acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('passed', 'application_sha', 'workspace_id', 'checks')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', required=True)
    run(parser.parse_args())
