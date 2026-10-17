"""Real UI workspace creation, three-agent CRUD, and rapid-switch isolation."""
import json
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_browser

BASE='http://127.0.0.1:3000'
with sync_playwright() as p:
    browser=launch_browser(p)
    page=browser.new_page(viewport={'width':1366,'height':768})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.goto(BASE,wait_until='networkidle')
    original=page.get_by_label('Workspace',exact=True).input_value()
    name='QA UI '+str(uuid.uuid4())[:6]
    page.once('dialog',lambda dialog:dialog.accept(name))
    page.get_by_role('button',name='＋ Tạo workspace',exact=True).click()
    expect(page.locator('.breadcrumb')).to_contain_text(name)
    workspace=page.get_by_label('Workspace',exact=True).input_value()
    assert workspace!=original
    page.get_by_role('button',name='Agent Studio',exact=False).click()
    for role,skin in [('Planner','teal'),('Developer','coral'),('Reviewer','gold')]:
        page.get_by_role('button',name='＋ Tạo agent',exact=True).click()
        page.get_by_label('Tên agent',exact=True).fill('QA '+role)
        page.get_by_label('Vai trò',exact=True).fill(role)
        page.get_by_label('Skin',exact=True).select_option(skin)
        page.get_by_label('Brain provider',exact=True).select_option('mock')
        page.get_by_role('button',name='Lưu agent',exact=True).click()
        expect(page.get_by_role('status')).to_contain_text('Đã lưu agent')
    data=page.request.get(BASE+'/api/bootstrap?workspace_id='+workspace).json()
    assert len(data['agents'])==3
    assert {a['skin'] for a in data['agents']}=={'teal','coral','gold'}
    marker='QA namespace '+str(uuid.uuid4())
    page.get_by_label('Nội dung memory',exact=True).fill(marker)
    page.get_by_role('button',name='Lưu memory',exact=True).click()
    expect(page.get_by_text(marker,exact=True)).to_be_visible()
    page.get_by_label('Workspace',exact=True).select_option(original)
    page.get_by_label('Workspace',exact=True).select_option(workspace)
    page.get_by_label('Workspace',exact=True).select_option(original)
    expect(page.locator('.breadcrumb')).not_to_contain_text(name)
    page.get_by_role('button',name='Agent Studio',exact=False).click()
    expect(page.get_by_text(marker,exact=True)).to_have_count(0)
    expect(page.get_by_text('QA Planner',exact=True)).to_have_count(0)
    page.get_by_label('Workspace',exact=True).select_option(workspace)
    page.get_by_role('button',name='Agent Studio',exact=False).click()
    page.locator('.agent-list').get_by_role('button',name='QA Reviewer',exact=False).click()
    page.get_by_role('button',name='Vô hiệu hóa agent',exact=True).click()
    expect(page.locator('.agent-list')).to_contain_text('Đã vô hiệu hóa')
    data=page.request.get(BASE+'/api/bootstrap?workspace_id='+workspace).json()
    assert len([a for a in data['agents'] if a['enabled']])==2
    result={'result':'PASS','workspace':workspace,'actions':['UI workspace creation','three agent creation with role/brain/skin','memory persistence','rapid workspace switch has no foreign agent/memory','agent soft disable'],'console_errors':errors}
    assert not errors,errors
    (Path(__file__).parent/'evidence'/'workspace-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
