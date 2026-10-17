"""Independent real Pixi pointer drag, workstation assignment, pan/zoom and persistence."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE='http://127.0.0.1:3000'
OUT=Path(__file__).parent/'evidence'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    workspace=page.get_by_label('Workspace',exact=True).input_value()
    data=page.request.get(BASE+'/api/bootstrap?workspace_id='+workspace).json()
    room=data['room'];planner=next(a for a in data['agents'] if a['role']=='Planner')
    page.get_by_role('button',name='▧ Nội thất',exact=True).click()
    canvas=page.locator('canvas');expect(canvas).to_be_visible()
    canvas.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    def tile(x,y):
        box=canvas.bounding_box()
        size=canvas.evaluate('(c)=>({width:c.width,height:c.height})')
        return (box['x']+max(12,(size['width']-20*24)//2)+(x+.5)*24,
                box['y']+max(30,(size['height']-14*24)//2)+(y+.5)*24)
    desk=room['furniture'][0]
    source=tile(desk['x'],desk['y']);target=tile(desk['x']+1,desk['y'])
    page.mouse.move(*source);page.mouse.down();page.mouse.move(*target,steps=8);page.mouse.up()
    page.get_by_role('button',name='Lưu layout',exact=True).click()
    expect(page.get_by_role('status').filter(has_text='Đã lưu layout')).to_be_visible()
    saved=page.request.get(BASE+'/api/rooms/'+room['id']+'/layout').json()
    moved=next(f for f in saved['furniture'] if f['id']==desk['id'])
    assert moved['x']==desk['x']+1 and moved['y']==desk['y'],(desk,moved)
    page.get_by_role('button',name='Planner',exact=False).first.click()
    page.get_by_label('Công cụ nội thất').select_option('assign')
    canvas.scroll_into_view_if_needed()
    page.mouse.click(*tile(4,6))
    page.get_by_role('button',name='Lưu layout',exact=True).click()
    saved=page.request.get(BASE+'/api/rooms/'+room['id']+'/layout').json()
    assert saved['assignments'][planner['id']]=={'x':4,'y':6},saved
    page.reload(wait_until='networkidle')
    reloaded=page.request.get(BASE+'/api/rooms/'+room['id']+'/layout').json()
    assert reloaded['furniture']==saved['furniture'] and reloaded['assignments']==saved['assignments']
    page.get_by_role('button',name='▧ Nội thất',exact=True).click()
    page.get_by_label('Phóng to',exact=True).click()
    expect(page.get_by_text('2×',exact=True)).to_be_visible()
    page.get_by_label('Thu nhỏ',exact=True).click()
    expect(page.get_by_text('1×',exact=True)).to_be_visible()
    page.get_by_role('button',name='Lưới',exact=True).click()
    expect(page.get_by_role('button',name='Lưới',exact=True)).to_have_attribute('aria-pressed','true')
    canvas=page.locator('canvas');canvas.scroll_into_view_if_needed();box=canvas.bounding_box()
    page.keyboard.down('Shift');page.mouse.move(box['x']+box['width']/2,box['y']+80);page.mouse.down(button='middle');page.mouse.move(box['x']+box['width']/2+35,box['y']+100,steps=6);page.mouse.up(button='middle');page.keyboard.up('Shift')
    page.screenshot(path=str(OUT/'08-furniture-interaction-1366.png'))
    restore=page.request.put(BASE+'/api/rooms/'+room['id']+'/layout',data={'furniture':room['furniture'],'assignments':room['assignments']})
    assert restore.ok,restore.text()
    result={'result':'PASS','actions':['real canvas furniture drag','backend save','selected agent assignment via canvas','reload persistence','integer zoom controls','grid toggle','middle pointer pan'], 'page_errors':errors}
    assert not errors,errors
    (OUT/'canvas-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
