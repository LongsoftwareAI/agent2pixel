"""Additional exact-viewport detail and trace screenshots; no app mutation."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_browser
out=Path(__file__).parent/'evidence'
with sync_playwright() as p:
    browser=launch_browser(p)
    page=browser.new_page(viewport={'width':1366,'height':768})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
    page.goto('http://127.0.0.1:3000',wait_until='networkidle')
    page.get_by_role('button',name='Agent Studio',exact=False).click()
    page.locator('.agent-list').get_by_role('button',name='Planner',exact=False).click()
    page.get_by_label('Skin',exact=False).scroll_into_view_if_needed()
    expect(page.get_by_label('Skin',exact=False)).to_be_visible()
    page.screenshot(path=str(out/'02b-agent-capabilities-1366.png'))
    page.get_by_role('button',name='Run Monitor',exact=False).click()
    page.locator('.run-list .run-row').first.click()
    page.get_by_role('heading',name='Event timeline',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(out/'04b-run-events-1366.png'))
    assert not errors,errors
    print('PASS detail screenshots; no console errors')
    browser.close()
