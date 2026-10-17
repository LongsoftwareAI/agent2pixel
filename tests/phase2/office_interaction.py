"""Real pointer interaction evidence; fixture labels are never runtime claims."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1366,'height':768});errors=[];failures=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('response',lambda response:failures.append({'url':response.url,'status':response.status}) if response.status>=400 else None)
        page.goto(url,wait_until='networkidle');page.wait_for_function('window.agentverseOffice?.world');page.wait_for_timeout(1200)
        assert page.get_by_text('TEST FIXTURE — no live execution',exact=True).is_visible()
        point=page.evaluate('''()=>{const w=agentverseOffice.world,c=w.debug.sim.chars.get('agent-0');return w.debug.camera.worldToScreen(c.x,c.y-10)}''')
        page.mouse.click(point['x'],point['y']);page.wait_for_timeout(600)
        selection=page.evaluate('agentverseOffice.world.getSelection()')
        assert selection=={'type':'agent','id':'agent-0'},selection
        page.screenshot(path=str(out/'office-selected-1366.png'))
        page.keyboard.press('Escape');page.wait_for_timeout(300)
        before=page.evaluate('agentverseOffice.world.debug.camera.zoom')
        page.get_by_role('button',name='Zoom in (+)',exact=True).click();page.wait_for_timeout(650)
        after=page.evaluate('agentverseOffice.world.debug.camera.zoom');assert after>before,(before,after)
        # Drag an empty outdoor canvas area, not the DOM shell.
        old=page.evaluate('({x:agentverseOffice.world.debug.camera.x,y:agentverseOffice.world.debug.camera.y})')
        page.mouse.move(1250,550);page.mouse.down();page.mouse.move(1150,515,steps=10);page.mouse.up();page.wait_for_timeout(200)
        new=page.evaluate('({x:agentverseOffice.world.debug.camera.x,y:agentverseOffice.world.debug.camera.y})');assert new!=old,(old,new)
        page.screenshot(path=str(out/'office-pan-zoom-1366.png'))
        assert not errors and not failures,(errors,failures)
        result=dict(passed=True,url=url,selection=selection,zoom=[before,after],pan=[old,new],page_errors=errors,http_failures=failures,fixture=True,runtime_execution=False)
        (out/'office-interactions.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));browser.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:3103/?fixture=parity');p.add_argument('--output',default='tests/phase2/evidence');a=p.parse_args();run(a.url,a.output)
