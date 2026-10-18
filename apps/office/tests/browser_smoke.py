"""Dev-host integration smoke. Explicit fixture; never real execution evidence.

Run office dev server, then OFFICE_TEST_URL=http://127.0.0.1:3002/office/ \
python apps/office/tests/browser_smoke.py. Uses existing Playwright + system Chromium.
"""
import os
from urllib.parse import urlsplit, parse_qs
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
        headless=True,
    )
    page = browser.new_page(viewport={'width': 1366, 'height': 768})
    errors, failed_assets = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: failed_assets.append(response.url)
            if response.status >= 400 and '/assets/' in response.url else None)
    base = os.environ.get('OFFICE_TEST_URL', 'http://127.0.0.1:3002/office/')
    page.goto(base + '?fixture=parity')
    page.wait_for_selector('.av-fixture')
    page.evaluate("window.agentverseOffice.world.select({type:'agent',id:'agent-1'})")
    link = page.get_by_role('link', name='Open selected agent in AI console')
    assert link.is_visible()
    route = urlsplit(link.get_attribute('href')).fragment
    assert route.split('?')[0] == 'agents'
    assert parse_qs(route.split('?')[1]) == {'agent': ['agent-1'], 'workspace': ['coding']}
    page.evaluate('window.agentverseOffice.world.select(null)')
    assert not link.is_visible()
    assert not errors, errors
    assert not failed_assets, failed_assets
    print('PASS: fixture host, artwork loading, scoped agent link, deselection; not execution evidence')
    browser.close()
