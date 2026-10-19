"""Actual UI regression checks for independently discovered Phase5 defects."""
import argparse
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase4'))
from acceptance_support import API


def run(args):
    api = API(args.api)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {'application_sha': args.sha, 'passed': False, 'checks': [],
              'inference': 'deterministic mock; tests actual routing/store/UI, not model intelligence'}
    try:
        ws = api.ok('/api/workspaces', {'name': 'P5 Regression Synthetic '+str(time.time_ns())})
        actors = [api.ok('/api/agents', {'workspace_id': ws['id'], 'name': 'Synthetic Bot '+name,
                  'role': 'QA original role '+name, 'system_prompt': 'QA original SOUL '+name}) for name in ('A', 'B')]
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            context.add_init_script('localStorage.setItem("agentverse.workspace", '+json.dumps(ws['id'])+');')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(args.base+'/#chat')
            for actor in actors:
                page.get_by_label('Bot thực thi').select_option(actor['id'])
                prompt = 'Synthetic dispatch to '+actor['name']+' '+str(time.time_ns())
                page.get_by_label('Tin nhắn', exact=True).fill(prompt)
                page.get_by_role('button', name='Gửi ↑', exact=True).click()
                for _ in range(200):
                    conversations = api.ok('/api/console/conversations?workspace_id='+ws['id'])
                    target = next((c for c in conversations if c['agent_id'] == actor['id']), None)
                    if target:
                        detail = api.ok('/api/console/conversations/'+target['id']+'?workspace_id='+ws['id'])
                        message = next((m for m in detail['messages'] if m.get('content') == prompt), None)
                        if message:
                            break
                    page.wait_for_timeout(50)
                else:
                    raise AssertionError('Bot selector did not dispatch a new conversation to '+actor['name'])
                execution = api.wait(message['run_id'])
                assert execution['state'] == 'completed' and set(execution['agent_specs']) == {actor['id']}, execution
                page.get_by_role('button', name='Gửi ↑', exact=True).wait_for()
            assert len(conversations) == 2, conversations
            report['checks'].append('A→B bot dropdown creates separately bound conversations and exact actual run agent snapshots')
            page.screenshot(path=str(out/'chat-agent-switch-1366.png'))
            actor = actors[0]
            changed = api.ok('/api/agents/'+actor['id'], {'role': 'QA changed role A'}, 'PATCH')
            actual_revision = changed['agent_config_revision']
            history_path = '/api/console/agents/'+actor['id']+'/config/history?workspace_id='+ws['id']
            history = api.ok(history_path)
            assert history and all(h['revision'] < actual_revision for h in history), history
            page.goto(args.base+'/#bots?agent='+actor['id'])
            page.locator('.c-tabs').get_by_role('button', name='Cấu hình', exact=True).click()
            page.get_by_role('button', name='revision 1', exact=True).click()
            diff = page.locator('.c-revision-diff')
            assert 'QA changed role A' in diff.locator('pre').nth(0).inner_text()
            assert 'QA original role A' in diff.locator('pre').nth(1).inner_text()
            page.get_by_role('button', name='Khôi phục nội dung revision 1 thành revision mới', exact=True).click()
            for _ in range(100):
                restored = api.ok('/api/agents/'+actor['id'])
                if restored['role'] == actor['role']:
                    break
                page.wait_for_timeout(50)
            else:
                raise AssertionError('Actual config rollback did not restore original role')
            assert restored['agent_config_revision'] == actual_revision + 1
            report['checks'].append('config UI displays actual current/prior diff and rollback uses current revision with prior-only backend history')
            page.locator('.c-tabs').get_by_role('button', name='SOUL', exact=True).click()
            page.get_by_role('button', name='Sửa SOUL', exact=True).click()
            page.get_by_label('Nội dung SOUL', exact=True).fill('QA changed SOUL after save')
            page.get_by_role('button', name='Lưu revision mới', exact=True).click()
            page.get_by_role('button', name='revision 1', exact=True).click()
            diff = page.locator('.c-revision-diff')
            assert 'QA changed SOUL after save' in diff.locator('pre').nth(0).inner_text()
            assert actor['system_prompt'] in diff.locator('pre').nth(1).inner_text()
            page.screenshot(path=str(out/'actual-revision-diff-1366.png'))
            report['checks'].append('SOUL save refreshes prior-only history and displays saved current content against previous revision')
            grants_before = {a['id']: api.ok('/api/agents/'+a['id'])['tool_grants'] for a in actors}
            page.goto(args.base+'/#topology')
            node = page.locator('.react-flow__node').first
            node.wait_for()
            total_nodes = page.locator('.react-flow__node').count()
            viewport = page.locator('.react-flow__viewport')
            initial_transform = viewport.get_attribute('style')
            page.get_by_role('button', name='Zoom In', exact=True).click()
            page.wait_for_timeout(300)
            assert viewport.get_attribute('style') != initial_transform
            page.get_by_role('button', name='Fit View', exact=True).click()
            page.wait_for_timeout(300)
            node.click()
            page.locator('.c-topology-inspector').wait_for()
            page.get_by_role('button', name='Đóng chi tiết node', exact=True).click()
            page.get_by_label('Tìm dữ liệu', exact=True).fill('Synthetic Bot A')
            page.wait_for_timeout(200)
            assert page.locator('.react-flow__node').count() < total_nodes
            assert page.locator('.react-flow__node').count() > 0
            page.get_by_label('Tìm dữ liệu', exact=True).fill('')
            page.get_by_role('button', name='Xếp lại', exact=True).click()
            assert {a['id']: api.ok('/api/agents/'+a['id'])['tool_grants'] for a in actors} == grants_before
            page.screenshot(path=str(out/'actual-topology-controls-1366.png'))
            report['checks'].append('actual topology search/zoom/fit/detail/rearrange leaves backend tool grants unchanged')
            assert not errors, errors
            browser.close()
            report.update(passed=True, workspace_id=ws['id'])
    except Exception as exc:
        report['failure'] = repr(exc)
        raise
    finally:
        (out/'browser-regressions.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', required=True)
    run(parser.parse_args())
