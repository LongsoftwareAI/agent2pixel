"""Actual browser PNG preview, light contrast and nonfixture office bridge probe.

Uses system Python Playwright/Pillow, not an application dependency or live vision.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs

from PIL import Image
from playwright.sync_api import sync_playwright, expect

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase4'))
from acceptance_support import API  # noqa: E402


def luminance(rgb):
    values = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in (n/255 for n in rgb)]
    return sum(a*b for a, b in zip(values, (0.2126, 0.7152, 0.0722)))


def run(args):
    api = API(args.api)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {'application_sha': args.sha, 'passed': False, 'checks': []}
    try:
        ws = api.ok('/api/workspaces', {'name': 'Synthetic PNG and theme QA'})
        actor = api.ok('/api/agents', {'workspace_id': ws['id'], 'name': 'Synthetic image metadata bot', 'role': 'Evidence recorder'})
        png = io.BytesIO()
        Image.new('RGB', (2, 2), (35, 96, 160)).save(png, format='PNG')
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            context.add_init_script('localStorage.setItem("agentverse.workspace", '+json.dumps(ws['id'])+');')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.base+'/#chat')
            page.get_by_label('Bot thực thi').select_option(actor['id'])
            page.get_by_label('Đính kèm tệp').set_input_files({'name': 'synthetic.png', 'mimeType': 'image/png', 'buffer': png.getvalue()})
            image = page.get_by_alt_text('Ảnh đính kèm synthetic.png')
            image.wait_for()
            page.wait_for_function('document.querySelector(".c-image-attachment img")?.naturalWidth === 2')
            assert 'chưa có adapter đọc nội dung pixel' in page.locator('.c-image-attachment').inner_text()
            preview = image.get_attribute('src')
            foreign = api.ok('/api/workspaces', {'name': 'Synthetic foreign image scope'})
            api.denied(preview.split('?')[0]+'?workspace_id='+foreign['id'])
            page.screenshot(path=str(out/'png-real-preview-1366.png'))
            page.get_by_label('Tin nhắn', exact=True).fill('Record metadata only; no image content interpretation.')
            page.get_by_role('button', name='Gửi ↑', exact=True).click()
            expect(page.get_by_label('Tin nhắn', exact=True)).to_have_value('')
            conversations = api.ok('/api/console/conversations?workspace_id='+ws['id'])
            detail = api.ok('/api/console/conversations/'+conversations[0]['id']+'?workspace_id='+ws['id'])
            request = next(m for m in detail['messages'] if m['role'] == 'user')
            execution = api.wait(request['run_id'])
            assert execution['state'] == 'completed'
            assert 'Image pixels not interpreted' in execution['input'] and hashlib.sha256(png.getvalue()).hexdigest() in execution['input']
            report['checks'].append('real PNG upload/browser decoded preview/hash/context; no vision claim; foreign preview denied')
            prefs = api.ok('/api/console/preferences?workspace_id='+ws['id'])
            api.ok('/api/console/preferences?workspace_id='+ws['id'], {**prefs, 'theme':'light'}, method='PATCH')
            page.goto(args.base+'/#preferences')
            page.wait_for_function('document.documentElement.dataset.consoleTheme === "light"')
            page.get_by_label('Giao diện', exact=True).wait_for()
            color = page.locator('.c-setting label').first.evaluate('(el)=>getComputedStyle(el).color')
            bg = page.locator('.c-settings-layout .c-card').first.evaluate('(el)=>getComputedStyle(el).backgroundColor')
            rgb = lambda s: [int(n.strip()) for n in s[s.index('(')+1:s.index(')')].split(',')[:3]]
            a, b = sorted((luminance(rgb(color)), luminance(rgb(bg))))
            ratio = (b+0.05)/(a+0.05)
            assert ratio >= 4.5, (color, bg, ratio)
            report['light_label_contrast'] = ratio
            page.screenshot(path=str(out/'light-contrast-1366.png'))
            report['checks'].append('actual light setting-label foreground/background contrast >=4.5 after legacy CSS override')
            page.goto(args.base+'/office/')
            page.wait_for_function('window.agentverseOffice?.store?.snapshot?.agents?.length > 0')
            assert page.locator('.av-fixture').count() == 0
            assert page.evaluate('window.agentverseOffice.fixture') is False
            assert page.locator('canvas#world').is_visible()
            selected = page.evaluate('''() => {
                const host=window.agentverseOffice;
                const agent=host.store.snapshot.agents[0];
                host.world.select({type:'agent',id:agent.id});
                return agent.id;
            }''')
            link = page.get_by_role('link', name='Open selected agent in AI console')
            link.wait_for()
            href = link.get_attribute('href')
            assert parse_qs(urlsplit(href).fragment.split('?')[1])['agent'] == [selected]
            page.screenshot(path=str(out/'office-actual-backend-1366.png'))
            link.click()
            page.locator('.console .c-content[aria-busy="false"]').wait_for()
            assert urlsplit(page.url).fragment.startswith('agents?agent=')
            assert not errors, errors
            browser.close()
            report.update(passed=True, workspace_id=ws['id'], checks=report['checks']+['nonfixture Habblaud real backend snapshot, canvas, selected actual agent→console profile bridge'])
    finally:
        (out/'visual-media-office.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--api', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--output', required=True)
    run(parser.parse_args())
