"""Real browser chat, durable conversation, settings, keyboard and reconnect checks."""
import argparse
import json
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase4'))
from acceptance_support import API, ProviderFixture  # noqa: E402
from live_acceptance import agent, graph  # noqa: E402


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    api = API(args.api)
    result = {'application_sha': args.sha, 'passed': False, 'provider': 'local HTTP fixture, not live inference', 'checks': []}
    try:
        with ProviderFixture() as fixture, sync_playwright() as p:
            ws = api.ok('/api/workspaces', {'name': 'P5 Browser Synthetic '+str(time.time_ns())})
            actor = agent(api, ws, fixture, 'Synthetic Browser Analyst', ['csv.analyze'])
            source = api.ok('/api/sources', {'workspace_id': ws['id'], 'name': 'Synthetic browser CSV', 'content': 'amount\n0.10\n0.20\n', 'media_type': 'text/csv'})
            flow = api.ok('/api/workflows', {'workspace_id': ws['id'], 'name': 'Browser actual CSV', 'graph': graph([
                {'id': 'parse', 'type': 'tool', 'agent_id': actor['id'], 'tool': {'id': 'csv.analyze', 'payload': {'source_id': source['id'], 'column': 'amount'}}},
                {'id': 'answer', 'type': 'agent', 'agent_id': actor['id'], 'instructions': 'State only real supplied tool evidence.'}])})
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            context.add_init_script('localStorage.setItem("agentverse.workspace", '+json.dumps(ws['id'])+');')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.base+'/#chat')
            page.get_by_label('Bot thực thi').select_option(actor['id'])
            page.get_by_label('Workflow trò chuyện').select_option(flow['id'])
            prompt = 'Synthetic browser CSV task '+str(time.time_ns())
            page.get_by_label('Tin nhắn', exact=True).fill(prompt)
            page.get_by_role('button', name='Gửi ↑', exact=True).click()
            for _ in range(300):
                conversations = api.ok('/api/console/conversations?workspace_id='+ws['id'])
                if conversations:
                    detail = api.ok('/api/console/conversations/'+conversations[0]['id']+'?workspace_id='+ws['id'])
                    user = next((m for m in detail['messages'] if m['role'] == 'user'), None)
                    if user and user.get('run_id'):
                        break
                page.wait_for_timeout(50)
            else:
                raise AssertionError('UI send never created actual durable message/run')
            execution = api.wait(user['run_id'])
            assert execution['state'] == 'completed', execution
            assert fixture.requests, 'UI route never contacted real local adapter'
            assert len(api.ok('/api/runs/'+execution['id']+'/tool-results')) == 1
            page.reload()
            page.locator('.c-conversations').get_by_role('button', name=prompt, exact=False).click()
            page.get_by_text('[LOCAL HTTP PROVIDER FIXTURE; NOT LIVE INFERENCE]', exact=False).first.wait_for()
            page.screenshot(path=str(out/'actual-chat-persisted-1366.png'))
            result['checks'].append('UI composer dispatches actual CSV tool/native model adapter; reload/history restores same durable conversation')
            page.keyboard.press('Control+k')
            dialog = page.get_by_role('dialog', name='Điều hướng nhanh')
            dialog.wait_for()
            dialog.get_by_label('Tìm màn hình').fill('Chi phí')
            dialog.get_by_role('button', name='Chi phí & ngân sách', exact=False).click()
            page.wait_for_url('**/#usage')
            result['checks'].append('Ctrl+K command palette filters and navigates to costs')
            page.goto(args.base+'/#preferences')
            page.locator('.c-content[aria-busy="false"]').wait_for()
            page.get_by_role('button', name='Lưu cài đặt', exact=True).wait_for(state='visible')
            page.get_by_label('Giao diện', exact=True).select_option('light')
            page.get_by_label('Tự làm mới', exact=True).select_option('off')
            page.get_by_role('button', name='Lưu cài đặt', exact=True).click()
            page.get_by_role('status').filter(has_text='Đã lưu cài đặt').wait_for()
            page.reload()
            page.locator('.c-content[aria-busy="false"]').wait_for()
            assert page.get_by_label('Giao diện', exact=True).input_value() == 'light'
            assert page.get_by_label('Tự làm mới', exact=True).input_value() == 'off'
            assert page.locator('html').get_attribute('data-console-theme') == 'light'
            page.screenshot(path=str(out/'preferences-persisted-1366.png'))
            result['checks'].append('theme/refresh preferences persist actual backend and reload')
            page.goto(args.base+'/#logs')
            page.locator('.c-content[aria-busy="false"]').wait_for()
            with page.expect_download() as download_info:
                page.get_by_role('button', name='↓ Xuất JSON đã redaction', exact=True).click()
            download = download_info.value
            exported = json.loads(Path(download.path()).read_text())
            assert exported['kind'] == 'system' and exported['workspace_id'] == ws['id']
            assert all('payload' not in row and 'content' not in row for row in exported['items'])
            result['checks'].append('actual UI log export downloads scoped redacted JSON through backend')
            page.route('**/api/**', lambda route: route.abort())
            page.get_by_role('button', name='↻ Làm mới', exact=True).first.click()
            page.get_by_role('alert').first.wait_for()
            assert page.locator('.c-local').inner_text() != 'Localhost · đã đồng bộ'
            page.screenshot(path=str(out/'disconnected-explicit-1366.png'))
            page.unroute('**/api/**')
            page.get_by_role('button', name='Thử lại', exact=True).click()
            page.get_by_role('alert').wait_for(state='hidden')
            result['checks'].append('real request failure displays disconnected state; retry recovers without fabricated success')
            assert not errors, errors
            browser.close()
            result.update(passed=True, workspace_id=ws['id'], conversation_id=conversations[0]['id'], run_id=execution['id'])
    except Exception as exc:
        result['failure'] = repr(exc)
        raise
    finally:
        (out/'browser-behaviors.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--api', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', required=True)
    run(parser.parse_args())
