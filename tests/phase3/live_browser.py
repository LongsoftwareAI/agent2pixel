"""Actual localhost Work board interaction/screenshots; deterministic backend Brain labeled."""
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors, failures = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: failures.append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
        def api(path, body=None, method='GET'):
            response = page.request.fetch(args.base + path, data=body, method=method)
            assert response.ok, (path, response.status, response.text())
            return response.json()
        ws = api('/api/workspaces', {'name': 'P3 Browser QA ' + str(time.time_ns())}, 'POST')
        a = api('/api/agents', {'workspace_id': ws['id'], 'name': 'QA Report Writer', 'role': 'Researcher',
                              'tool_grants': [{'id': 'artifacts.write_text', 'allow': True}]}, 'POST')
        graph = {'nodes': [{'id': 'start', 'type': 'start'}, {'id': 'report', 'type': 'agent', 'agent_id': a['id'],
                           'instructions': 'UI_CUSTOM_OBJECTIVE: prepare a report from the brief; disclose unverified facts.',
                           'deliverable': {'filename': 'browser-report.md'}}, {'id': 'end', 'type': 'end'}],
                 'edges': [{'source': 'start', 'target': 'report'}, {'source': 'report', 'target': 'end'}]}
        workflow = api('/api/workflows', {'workspace_id': ws['id'], 'name': 'UI Report Flow', 'graph': graph}, 'POST')
        page.add_init_script('localStorage.setItem("agentverse.workspace", ' + json.dumps(ws['id']) + ')')
        page.goto(args.base + '/')
        page.wait_for_function("window.agentverseOffice?.store.connection==='open'")
        page.get_by_role('link', name='Work board', exact=True).click()
        page.get_by_role('heading', name='Công việc', exact=True).wait_for()
        title = 'UI company operations report'
        page.get_by_label('Tiêu đề công việc', exact=True).fill(title)
        page.get_by_label('Brief', exact=True).fill('Prepare a report for the supplied operations brief; this is deterministic QA execution.')
        page.get_by_label('Tiêu chí nghiệm thu', exact=True).fill('Keep factual limitations explicit\nExport the generated report after approval')
        page.get_by_label('Workflow công việc', exact=True).select_option(workflow['id'])
        page.get_by_role('button', name='Tạo công việc', exact=True).click()
        card = page.locator('article.work-item').filter(has=page.get_by_role('heading', name=title, exact=True))
        card.wait_for()
        card.get_by_role('button', name='Sửa brief', exact=True).click()
        page.get_by_label('Brief', exact=True).fill('UPDATED_UI_BRIEF: list known and missing operational facts. Do not invent research.')
        page.get_by_role('button', name='Lưu brief', exact=True).click()
        card.get_by_text('UPDATED_UI_BRIEF:', exact=False).wait_for()
        page.screenshot(path=str(out / 'workboard-created-edited-1366.png'), full_page=True)
        card.get_by_role('button', name='Chạy công việc', exact=True).click()
        page.get_by_role('heading', name='Run Monitor', exact=True).wait_for()
        page.get_by_role('button', name='Phê duyệt payload này', exact=True).wait_for(timeout=30000)
        assert page.get_by_text('artifacts.write_text', exact=False).count() > 0
        page.screenshot(path=str(out / 'generated-output-approval-1366.png'), full_page=True)
        item = api('/api/work-items?workspace_id=' + ws['id'])[0]
        run_id = item['latest_run_id']
        pending = [r for r in api('/api/runs/' + run_id + '/approvals') if r['status'] == 'pending']
        assert len(pending) == 1 and 'UPDATED_UI_BRIEF' in pending[0]['payload']['content'], pending
        page.get_by_role('button', name='Phê duyệt payload này', exact=True).click()
        for _ in range(200):
            run = api('/api/runs/' + run_id)
            if run['state'] == 'completed':
                break
            time.sleep(.05)
        assert run['state'] == 'completed' and len(run['artifacts']) == 1, run
        page.wait_for_timeout(1300)
        page.screenshot(path=str(out / 'actual-export-evidence-1366.png'), full_page=True)
        page.get_by_role('button', name='Công việc', exact=False).click()
        card = page.locator('article.work-item').filter(has=page.get_by_role('heading', name=title, exact=True))
        card.get_by_label('Review ' + title, exact=True).fill('Human QA reviewed generated output and its limitations; approved exact payload.')
        card.get_by_role('button', name='Nghiệm thu kết quả', exact=True).click()
        card.get_by_text('Đã nghiệm thu', exact=True).wait_for()
        page.screenshot(path=str(out / 'human-reviewed-done-1366.png'), full_page=True)
        done = api('/api/work-items/' + item['id'])
        assert done['status'] == 'done' and done['reviews'], done
        page.get_by_role('button', name='Workflow', exact=False).first.click()
        page.get_by_label('Workflow', exact=True).select_option(workflow['id'])
        page.locator('.react-flow__node').filter(has_text='QA Report Writer').click()
        page.get_by_label('Instructions của node', exact=True).wait_for()
        assert 'UI_CUSTOM_OBJECTIVE' in page.get_by_label('Instructions của node', exact=True).input_value()
        page.screenshot(path=str(out / 'workflow-node-instructions-1366.png'), full_page=True)
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.screenshot(path=str(out / 'workflow-templates-1920.png'), full_page=True)
        result = {'passed': not errors and not failures, 'application_sha': args.sha,
                  'brain': 'actual deterministic MockBrain backend; no live model inference', 'workspace_id': ws['id'],
                  'work_item_id': item['id'], 'run_id': run_id, 'artifact': run['artifacts'][0], 'human_review': done['reviews'],
                  'checks': ['office header Work board link', 'actual UI create and edit brief', 'actual UI launch',
                             'post-generation exact payload approval', 'actual export evidence', 'human review done', 'editable node instructions'],
                  'page_errors': errors, 'http_failures': failures}
        (out / 'live-browser.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        browser.close()
        return result['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:3000')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sha', required=True)
    raise SystemExit(0 if run(parser.parse_args()) else 1)
