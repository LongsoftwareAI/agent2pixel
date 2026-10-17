"""Capture independent upstream and AgentVerse fixture canvases identically."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from compare_visual import compare


def run(reference, candidate, output):
    output=Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,args=['--no-sandbox'])
        for width,height in [(1366,768),(1920,1080)]:
            records=[]
            for label,url,hook in [('upstream',reference,'qaReference'),('agentverse',candidate,'agentverseOffice')]:
                context=browser.new_context(viewport={'width':width,'height':height}, device_scale_factor=1,locale='en-US',timezone_id='UTC')
                # Same initial global entropy and Date; animation clock comes from the shared fixture.
                context.add_init_script('''Date.now=()=>1781524800000; Math.random=()=>0.5;''')
                page=context.new_page(); errors=[]; failures=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('response',lambda response:failures.append({'url':response.url,'status':response.status}) if response.status>=400 else None)
                page.goto(url,wait_until='networkidle')
                page.wait_for_function(f'window.{hook}?.world')
                page.wait_for_timeout(1000)
                canvas=page.locator('#world')
                # Canvas-only PNG excludes deliberate branding/control changes; raw pixel data remains full scene.
                data=canvas.evaluate('(canvas)=>canvas.toDataURL("image/png").split(",")[1]')
                import base64
                image=output/f'{label}-{width}.png';image.write_bytes(base64.b64decode(data))
                page.screenshot(path=str(output/f'{label}-full-{width}.png'))
                records.append({'label':label,'url':url,'errors':errors,'http_failures':failures,
                                'camera':page.evaluate(f'JSON.stringify(window.{hook}.world.debug.camera)')})
                context.close()
            result=compare(output/f'upstream-{width}.png',output/f'agentverse-{width}.png',output/f'comparison-{width}.png')
            result['browser']=browser.version;result['records']=records
            result['passed']=result['passed'] and all(not r['errors'] and not r['http_failures'] for r in records)
            results.append(result)
        browser.close()
    (output/'visual-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    return all(r['passed'] for r in results)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',default='http://127.0.0.1:3102/')
    parser.add_argument('--candidate',default='http://127.0.0.1:3103/?fixture=parity')
    parser.add_argument('--output',default='tests/phase2/evidence')
    args=parser.parse_args()
    raise SystemExit(0 if run(args.reference,args.candidate,args.output) else 1)
