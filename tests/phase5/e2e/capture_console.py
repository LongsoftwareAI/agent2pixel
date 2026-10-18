"""Capture real localhost screens from an explicitly supplied route inventory.

No API mocking, external video frames or fabricated metrics. Screenshots demonstrate
rendering only; independent behavior checks are recorded separately.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

VIEWPORTS = ((1108, 636), (1366, 768), (1920, 1080))


def run(args):
    assert urlparse(args.base).hostname in ('127.0.0.1', 'localhost', '::1'), 'Localhost evidence only'
    routes = json.loads(Path(args.routes).read_text())
    assert routes and all(row.get('id') and row.get('path') and row.get('ready') for row in routes)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    result = {'application_sha': args.sha, 'base': args.base, 'workspace_id': args.workspace,
              'captured_at': datetime.now(timezone.utc).isoformat(), 'images': [], 'page_errors': [], 'passed': False}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chromium, headless=True, args=['--no-sandbox'])
            for width, height in VIEWPORTS:
                context = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce')
                context.add_init_script('localStorage.setItem("agentverse.workspace", '+json.dumps(args.workspace)+');')
                page = context.new_page()
                page.on('pageerror', lambda error: result['page_errors'].append(str(error)))
                for row in routes:
                    assert row['path'].startswith('/'), row
                    response = page.goto(args.base.rstrip('/')+row['path'])
                    assert response is None or response.ok, (row, response.status)
                    page.locator(row['ready']).first.wait_for(state='visible')
                    page.get_by_text('Đang tải dữ liệu…', exact=True).wait_for(state='hidden')
                    assert page.get_by_role('alert').count() == 0, (row['id'], page.get_by_role('alert').all_text_contents())
                    page.evaluate('document.fonts.ready')
                    page.wait_for_timeout(400)
                    # Exact viewport screenshots preserve comparison geometry; no full-page resizing.
                    name = f"{row['id']}-{width}x{height}.png"
                    image_path = out/name
                    page.screenshot(path=str(image_path), full_page=False)
                    with Image.open(image_path) as image:
                        assert image.size == (width, height)
                        rgb = image.convert('RGB')
                        spread = max(ImageStat.Stat(rgb).stddev)
                        assert spread > 3, (name, 'blank or near-solid image', spread)
                        assert len(rgb.getcolors(maxcolors=2048) or range(2049)) > 32, (name, 'insufficient rendered colors')
                    result['images'].append({'file': name, 'route': row['path'], 'screen_id': row['id'],
                        'viewport': [width, height], 'sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
                        'nonblank_stddev': spread, 'manual_review': 'PENDING'})
                context.close()
            browser.close()
        assert not result['page_errors'], result['page_errors']
        result['passed'] = True
    finally:
        (out/'screenshots.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f"Captured {len(result['images'])} nonblank viewport images at {args.sha}; manual inspection still required")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--routes', required=True, help='JSON array of {id,path,ready CSS selector}')
    parser.add_argument('--output', required=True)
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    run(parser.parse_args())
