"""Real localhost Phase4 UI flow. MockBrain is explicitly not live inference."""
import argparse
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors, failures = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failures.append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
        def api(path, body=None, method='GET'):
            response = page.request.fetch(args.base+path, data=body, method=method)
            assert response.ok, (path, response.status, response.text())
            return response.json()
        def wait(run_id, expected='waiting_approval'):
            for _ in range(400):
                value = api('/api/runs/'+run_id)
                if value['state'] in (expected, 'failed', 'cancelled'):
                    assert value['state'] == expected, value
                    return value
                page.wait_for_timeout(50)
            raise AssertionError('Run did not settle')
        ws = api('/api/workspaces', {'name': 'P4 Browser QA '+str(time.time_ns())}, 'POST')
        actor = api('/api/agents', {'workspace_id': ws['id'], 'name': 'QA UI Analyst', 'role': 'Analyst',
            'tool_grants': [{'id': tool, 'allow': True} for tool in ('csv.analyze', 'artifacts.write_text')]}, 'POST')
        page.add_init_script('localStorage.setItem("agentverse.workspace", '+json.dumps(ws['id'])+')')
        page.goto(args.base+'/')
        page.get_by_role('link', name='Work board', exact=True).wait_for()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out/'habblaud-office-navigation-1366.png'), full_page=True)
        page.get_by_role('link', name='Work board', exact=True).click()
        page.get_by_label('Tiêu đề công việc', exact=True).wait_for()
        page.goto(args.base+'/control/#sources')
        page.get_by_label('Tên nguồn', exact=True).fill('QA UI CSV source')
        page.get_by_label('Định dạng nguồn', exact=True).select_option('text/csv')
        page.get_by_label('Nội dung nguồn', exact=True).fill('group,amount\nA,0.10\nA,0.20\nB,1.70\n')
        page.get_by_role('button', name='Lưu nguồn', exact=True).click()
        page.get_by_role('button', name='QA UI CSV source · text/csv', exact=True).click()
        page.get_by_text('ID trích dẫn:', exact=False).wait_for()
        source = next(row for row in api('/api/sources?workspace_id='+ws['id']) if row['name'] == 'QA UI CSV source')
        page.screenshot(path=str(out/'sources-csv-provenance-1366.png'), full_page=True)
        graph = {'nodes': [{'id': 'start', 'type': 'start'},
            {'id': 'calculate', 'type': 'tool', 'agent_id': actor['id'], 'tool': {'id': 'csv.analyze', 'payload': {'source_id': source['id'], 'column': 'amount', 'group_by': 'group'}}},
            {'id': 'draft', 'type': 'agent', 'agent_id': actor['id'], 'instructions': 'Report actual supplied parser numbers and unknowns.', 'deliverable': {'filename': 'ui-csv.md'}},
            {'id': 'review', 'type': 'review', 'instructions': 'Review factual evidence before completion.', 'rework_target': 'draft', 'max_revisions': 1},
            {'id': 'end', 'type': 'end'}],
            'edges': [{'source': 'start', 'target': 'calculate'}, {'source': 'calculate', 'target': 'draft'}, {'source': 'draft', 'target': 'review'}, {'source': 'review', 'target': 'end'}]}
        workflow = api('/api/workflows', {'workspace_id': ws['id'], 'name': 'QA UI CSV/review workflow', 'graph': graph}, 'POST')
        page.goto(args.base+'/control/#workboard')
        # Workflow was seeded outside this mounted UI; reload its workspace catalog.
        page.reload()
        page.get_by_label('Tiêu đề công việc', exact=True).fill('QA UI actual CSV report')
        page.get_by_label('Brief', exact=True).fill('Use only imported CSV and preserve unknown operational facts.')
        page.get_by_label('Tiêu chí nghiệm thu', exact=True).fill('Report sum2.00 from actual tool\nDo not invent additional sources')
        page.get_by_label('Workflow công việc', exact=True).select_option(workflow['id'])
        page.get_by_label('Ưu tiên', exact=True).select_option('high')
        page.get_by_label('Deadline', exact=True).fill('2030-01-01T12:00')
        page.get_by_label('Người phụ trách', exact=True).select_option(actor['id'])
        page.get_by_role('button', name='Tạo công việc', exact=True).click()
        title = page.get_by_role('heading', name='QA UI actual CSV report', exact=True)
        title.wait_for()
        card = page.locator('article.work-item').filter(has=title)
        card.get_by_role('button', name='Đưa vào hàng đợi', exact=True).click()
        page.get_by_role('button', name='Dispatch việc tiếp theo', exact=True).wait_for()
        page.screenshot(path=str(out/'queue-manual-dispatch-1366.png'), full_page=True)
        page.get_by_role('button', name='Dispatch việc tiếp theo', exact=True).click()
        item = next(item for item in api('/api/work-items?workspace_id='+ws['id']) if item['title'] == 'QA UI actual CSV report')
        run_id = item['latest_run_id']
        wait(run_id)
        tool_section = page.get_by_role('heading', name='Kết quả công cụ thực tế', exact=True).locator('..')
        tool_section.locator('pre').filter(has_text='"sum": "2.00"').first.wait_for()
        page.get_by_role('button', name='Phê duyệt payload này', exact=True).click()
        wait(run_id)
        page.get_by_label('Nhận xét checkpoint review', exact=True).fill('QA_UI_REWORK: explicitly state source count and unknowns.')
        page.screenshot(path=str(out/'actual-tool-review-gate-1366.png'), full_page=True)
        page.get_by_role('button', name='Yêu cầu làm lại', exact=True).click()
        wait(run_id)
        page.get_by_text('ui-csv-review-r1.md', exact=False).first.wait_for()
        page.get_by_role('button', name='Phê duyệt payload này', exact=True).click()
        wait(run_id)
        page.get_by_label('Nhận xét checkpoint review', exact=True).fill('QA automation approves bounded revision; not product-owner acceptance.')
        assert page.get_by_role('button', name='Yêu cầu làm lại', exact=True).count() == 0
        page.get_by_role('button', name='Duyệt bước này', exact=True).click()
        completed = wait(run_id, 'completed')
        assert len(completed['artifacts']) == 2
        page.get_by_role('button', name='Đọc artifact '+completed['artifacts'][0]['id'], exact=True).click()
        page.screenshot(path=str(out/'artifact-text-tool-trace-1366.png'), full_page=True)
        page.goto(args.base+'/control/#workboard')
        card = page.locator('article.work-item').filter(has=page.get_by_role('heading', name='QA UI actual CSV report', exact=True))
        card.get_by_label('Review QA UI actual CSV report', exact=True).fill('QA_UI_CHANGES: require revised brief before acceptance.')
        card.get_by_role('button', name='Yêu cầu sửa', exact=True).click()
        for _ in range(100):
            if api('/api/work-items/'+item['id'])['status'] == 'backlog':
                break
            page.wait_for_timeout(30)
        api('/api/work-items/'+item['id'], {'description': 'QA_UI_REVISED_BRIEF: explicitly state supplied CSV source count and unknowns.'}, 'PATCH')
        second = api('/api/work-items/'+item['id']+'/runs', {}, 'POST')
        for _ in range(5):
            wait(second['id'])
            approvals = [a for a in api('/api/runs/'+second['id']+'/approvals') if a['status'] == 'pending']
            if approvals:
                api('/api/approvals/'+approvals[0]['id']+'/decision', {'decision': 'approved'}, 'POST')
            else:
                gates = [g for g in api('/api/runs/'+second['id']+'/gates') if g['status'] == 'pending']
                assert len(gates) == 1
                api('/api/gates/'+gates[0]['id']+'/decision', {'decision': 'approved', 'comment': 'QA automation approves second run fixture.'}, 'POST')
                break
        assert wait(second['id'], 'completed')['state'] == 'completed'
        page.reload()
        card = page.locator('article.work-item').filter(has=page.get_by_role('heading', name='QA UI actual CSV report', exact=True))
        card.get_by_text('So sánh hai run gần nhất', exact=True).click()
        card.get_by_role('button', name='Tải diff và tiêu chí', exact=True).click()
        card.locator('pre').filter(has_text='--- previous/').first.wait_for()
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.screenshot(path=str(out/'actual-artifact-diff-1920.png'), full_page=True)
        page.goto(args.base+'/control/#agents')
        page.get_by_label('Nội dung memory', exact=True).fill('UI supplied CSV observation')
        page.get_by_label('Source ID của memory', exact=True).fill(source['id'])
        page.get_by_role('button', name='Lưu memory', exact=True).click()
        page.get_by_text('UI supplied CSV observation', exact=True).wait_for()
        page.get_by_role('button', name='Sửa memory', exact=True).click()
        page.get_by_label('Nội dung memory', exact=True).fill('UI revised supplied CSV observation')
        page.get_by_role('button', name='Lưu sửa memory', exact=True).click()
        page.get_by_role('button', name='Lịch sử memory', exact=True).click()
        page.get_by_text('Nguồn và dấu vết memory', exact=True).click()
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.screenshot(path=str(out/'memory-provenance-history-1920.png'), full_page=True)
        memories = api('/api/memories?workspace_id='+ws['id'])
        memory = next(m for m in memories if m['content'] == 'UI revised supplied CSV observation')
        assert len(api('/api/memories/'+memory['id']+'/history')) == 1
        page.get_by_role('button', name='Xóa memory', exact=True).click()
        assert all(m['id'] != memory['id'] for m in api('/api/memories?workspace_id='+ws['id']))
        page.goto(args.base+'/control/#workflows')
        page.get_by_label('Workflow', exact=True).select_option(workflow['id'])
        page.get_by_role('button', name='Fit View', exact=True).click()
        page.locator('.react-flow__node').filter(has_text='TOOL').click()
        page.get_by_label('Tool ID', exact=True).select_option('csv.analyze')
        page.get_by_label('Tool payload JSON', exact=True).fill(json.dumps({'source_id': source['id'], 'column': 'amount'}))
        page.get_by_label('Tool payload JSON', exact=True).press('Tab')
        page.locator('.react-flow__node').filter(has_text='REVIEW').click()
        page.get_by_label('Hướng dẫn review', exact=True).fill('QA_UI_EDITED_REVIEW: check exact numeric evidence.')
        page.get_by_label('Node cần làm lại', exact=True).select_option('draft')
        page.get_by_label('Giới hạn sửa lại', exact=True).fill('2')
        before_ids = {w['id'] for w in api('/api/workflows?workspace_id='+ws['id'])}
        page.get_by_role('button', name='Lưu đồ thị', exact=True).click()
        page.get_by_text('Đã lưu phiên bản workflow mới', exact=False).wait_for()
        saved = [w for w in api('/api/workflows?workspace_id='+ws['id']) if w['id'] not in before_ids]
        assert len(saved) == 1
        tool_node = next(n for n in saved[0]['graph']['nodes'] if n['id'] == 'calculate')
        review_node = next(n for n in saved[0]['graph']['nodes'] if n['id'] == 'review')
        assert tool_node['tool']['payload'] == {'source_id': source['id'], 'column': 'amount'}
        assert review_node['max_revisions'] == 2 and review_node['instructions'].startswith('QA_UI_EDITED_REVIEW')
        page.reload()
        page.get_by_label('Workflow', exact=True).select_option(saved[0]['id'])
        page.get_by_role('button', name='Fit View', exact=True).click()
        page.locator('.react-flow__node').filter(has_text='REVIEW').click()
        assert page.get_by_label('Giới hạn sửa lại', exact=True).input_value() == '2'
        page.screenshot(path=str(out/'tool-review-editor-persisted-1920.png'), full_page=True)
        result = {'passed': not errors and not failures, 'application_sha': args.sha, 'brain': 'actual MockBrain; no live inference',
            'workspace_id': ws['id'], 'run_id': run_id, 'source_id': source['id'], 'artifacts': completed['artifacts'],
            'checks': ['actual UI CSV import and provenance preview', 'work priority/deadline/owner and queue manual dispatch', 'actual csv tool result then generated output approval', 'human bounded review/rework then approval', 'artifact text retrieval and actual two-run diff', 'memory provenance edit/history/delete', 'tool JSON and bounded review editor save/reload'], 'page_errors': errors, 'http_failures': failures}
        (out/'live-browser.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
        browser.close()
        return result['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:3000')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sha', required=True)
    raise SystemExit(0 if run(parser.parse_args()) else 1)
