"""Independent live localhost captures: never substitute fixture data for backend state."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(base, output, sha):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width, height in [(1366, 768), (1920, 1080)]:
            context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
            for screen in ['office', 'agents', 'workflows', 'runs', 'settings']:
                page = context.new_page()
                errors, failures = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda r: failures.append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
                url = base + ('/' if screen == 'office' else '/control/#' + screen)
                page.goto(url, wait_until='domcontentloaded')
                if screen == 'office':
                    page.wait_for_function('window.agentverseOffice?.world && agentverseOffice.store.snapshot?.agents?.length > 0')
                    page.wait_for_function("agentverseOffice.store.connection === 'open'")
                    state = page.evaluate('''() => ({fixture:agentverseOffice.fixture,connection:agentverseOffice.store.connection,agents:agentverseOffice.store.snapshot.agents.length,rooms:agentverseOffice.store.snapshot.rooms.length,meta:agentverseOffice.store.snapshot.meta})''')
                    assert state['fixture'] is False and state['meta']['demo'] is False, state
                    assert state['rooms'] >= 2, state
                    page.wait_for_timeout(1500)
                else:
                    page.locator('h1').wait_for()
                    page.wait_for_timeout(1500)
                    state = {'heading': page.locator('h1').inner_text(), 'workspace': page.get_by_label('Workspace', exact=True).input_value()}
                    assert state['workspace'], state
                page.screenshot(path=str(out / f'live-{screen}-{width}.png'), full_page=True)
                checks.append(dict(screen=screen, width=width, url=url, state=state, page_errors=errors, http_failures=failures, passed=not errors and not failures))
                page.close()
            context.close()
        browser.close()
    result = {'application_sha': sha, 'fixture': False, 'provider_execution': 'not asserted by screenshots', 'checks': checks, 'passed': all(c['passed'] for c in checks)}
    (out / 'live-browser.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:3000')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sha', required=True)
    a = parser.parse_args()
    raise SystemExit(0 if run(a.base, a.output, a.sha) else 1)
