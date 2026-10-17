"""Real localhost browser interaction, screenshots, and console evidence.
python tests/e2e/browser_acceptance.py --base http://127.0.0.1:3000 --output /tmp/agentverse-evidence
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_browser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:3000')
    parser.add_argument('--output', default='/tmp/agentverse-evidence')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    errors, failures, steps = [], [], []
    with sync_playwright() as p:
        browser = launch_browser(p)
        context = browser.new_context(viewport={'width': 1366, 'height': 768}, device_scale_factor=1)
        context.add_init_script('''window.__qaSockets=[];const OriginalWS=window.WebSocket;
            window.WebSocket=class extends OriginalWS {constructor(...args){super(...args);window.__qaSockets.push(this)}};''')
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append({'kind': 'pageerror', 'text': str(e)}))
        page.on('console', lambda msg: errors.append({'kind': 'console.error', 'text': msg.text}) if msg.type == 'error' else None)
        page.on('response', lambda response: failures.append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
        page.goto(args.base, wait_until='networkidle')
        expect(page.get_by_role('heading', name='Văn phòng', exact=True)).to_be_visible()
        expect(page.locator('canvas')).to_be_visible()
        expect(page.get_by_text('Realtime đã kết nối', exact=True)).to_be_visible()
        page.screenshot(path=str(out/'01-office-1366.png'), full_page=False)
        steps.append('Office loaded, interactive canvas and realtime connected')
        page.get_by_role('button', name='Planner', exact=False).first.click()
        expect(page.get_by_role('button', name='Mở Agent Studio ↗')).to_be_visible()
        page.get_by_role('button', name='Mở Agent Studio ↗').click()
        expect(page.get_by_label('Tên agent', exact=True)).to_have_value('Planner')
        page.screenshot(path=str(out/'02-agent-studio-1366.png'), full_page=False)
        original = page.get_by_label('System instructions').input_value()
        page.get_by_label('System instructions').fill(original + '\nQA persistence probe')
        page.get_by_role('button', name='Lưu agent', exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Đã lưu agent')
        page.reload(wait_until='networkidle')
        page.get_by_role('button', name='Agent Studio', exact=False).click()
        page.locator('.agent-list').get_by_role('button', name='Planner', exact=False).click()
        expect(page.get_by_label('System instructions')).to_have_value(original + '\nQA persistence probe')
        page.get_by_label('System instructions').fill(original)
        page.get_by_role('button', name='Lưu agent', exact=True).click()
        steps.append('Agent system instructions edited, persisted after reload, restored')
        page.get_by_role('button', name='⌘ Workflow', exact=True).click()
        expect(page.locator('.react-flow')).to_be_visible()
        page.get_by_role('button', name='✓ Validate đã lưu', exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Đồ thị hợp lệ')
        planner_node=page.locator('.react-flow__node[data-id="planner"]')
        node_box=planner_node.bounding_box()
        page.mouse.move(node_box['x']+node_box['width']/2,node_box['y']+node_box['height']/2)
        page.mouse.down();page.mouse.move(node_box['x']+node_box['width']/2+24,node_box['y']+node_box['height']/2+20,steps=6);page.mouse.up()
        page.get_by_role('button',name='Lưu đồ thị',exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Đã lưu phiên bản workflow mới')
        chosen_workflow=page.get_by_label('Workflow',exact=True).input_value()
        current_workspace=page.get_by_label('Workspace',exact=True).input_value()
        saved_workflows=page.request.get(args.base+'/api/workflows?workspace_id='+current_workspace).json()
        saved_graph=next(w for w in saved_workflows if w['id']==chosen_workflow)['graph']
        assert next(n for n in saved_graph['nodes'] if n['id']=='planner').get('position')
        steps.append('Real workflow node drag and saved graph position persisted through API')
        page.screenshot(path=str(out/'03-workflow-1366.png'), full_page=False)
        page.get_by_label('Đầu vào workflow').fill('QA browser acceptance: create release verification checklist')
        page.get_by_role('button', name='▶ Chạy workflow đã lưu', exact=True).click()
        expect(page.get_by_role('heading', name='Run Monitor', exact=True)).to_be_visible()
        expect(page.locator('.run-list .run-row').first).to_contain_text('Hoàn thành', timeout=30000)
        expect(page.get_by_text('[MockBrain deterministic] Review:', exact=False).first).to_be_visible(timeout=10000)
        page.screenshot(path=str(out/'04-run-monitor-1366.png'), full_page=False)
        steps.append('Saved workflow validated, executed, backend completed Reviewer output visible')
        page.get_by_role('button', name='Nội thất', exact=False).click()
        workspace_id = page.get_by_label('Workspace', exact=True).input_value()
        snapshot = page.request.get(args.base + '/api/bootstrap?workspace_id=' + workspace_id).json()
        original_room = snapshot['room']
        page.get_by_label('Thêm nội thất').select_option('plant')
        page.get_by_role('button', name='Lưu layout', exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Đã lưu layout')
        page.screenshot(path=str(out/'05-furniture-1366.png'), full_page=False)
        stored_room = page.request.get(args.base + '/api/rooms/' + original_room['id'] + '/layout').json()
        assert len(stored_room['furniture']) == len(original_room['furniture']) + 1
        page.reload(wait_until='networkidle')
        after_reload = page.request.get(args.base + '/api/rooms/' + original_room['id'] + '/layout').json()
        assert after_reload['furniture'] == stored_room['furniture']
        page.request.put(args.base + '/api/rooms/' + original_room['id'] + '/layout', data={
            'furniture':original_room['furniture'], 'assignments':original_room['assignments']})
        steps.append('Original furniture inserted, backend persisted, survived reload, baseline restored')
        page.get_by_role('button', name='Cài đặt', exact=False).click()
        page.get_by_role('button', name='Kiểm tra kết nối', exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Provider connection succeeded')
        page.screenshot(path=str(out/'06-settings-1366.png'), full_page=False)
        steps.append('Settings MockBrain adapter test succeeds')
        page.get_by_role('button', name='Văn phòng', exact=False).click()
        page.set_viewport_size({'width':1920,'height':1080})
        expect(page.locator('canvas')).to_be_visible()
        page.wait_for_timeout(500)
        page.screenshot(path=str(out/'07-office-1920.png'), full_page=False)
        # Close the real runtime socket; request a run during the reconnect gap.
        page.evaluate("window.__qaSockets.filter(w=>w.url.includes('/ws/workspaces/')).forEach(w=>w.close())")
        expect(page.get_by_text('Disconnected · đang kết nối lại', exact=True)).to_be_visible()
        current_workspace = page.get_by_label('Workspace', exact=True).input_value()
        data = page.request.get(args.base+'/api/bootstrap?workspace_id='+current_workspace).json()
        response = page.request.post(args.base+'/api/workflows/'+data['workflows'][0]['id']+'/runs',data={'input':'QA reconnect replay check'})
        assert response.ok, response.text()
        expect(page.get_by_text('Realtime đã kết nối', exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_text('workflow.completed',exact=True).first).to_be_visible(timeout=10000)
        steps.append('Actual runtime WebSocket disconnected badge, reconnect and persisted missed workflow event replay')
        context.close()
        browser.close()
    evidence = {'base':args.base, 'steps':steps,'console_errors':errors,'http_failures':failures}
    (out/'browser-results.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    print(json.dumps(evidence,indent=2,ensure_ascii=False))
    assert not errors, errors
    assert not failures, failures


if __name__ == '__main__':
    main()
