#!/usr/bin/env python3
"""Run current whole-system checks and optional bounded live-provider acceptance.

No credential CLI option exists. Read secure runtime environment bindings only.
Fresh output/data paths are required; prior results are never renamed as current.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/bin/python'
SECRET_NAMES = ('AGENTVERSE_GROQ_API_KEY', 'AGENTVERSE_GEMINI_API_KEY', 'AGENTVERSE_DEEPSEEK_API_KEY', 'AGENTVERSE_OPENAI_API_KEY')
API = 'http://127.0.0.1:8000'
WEB = 'http://127.0.0.1:3000'


def clean(text):
    for name in SECRET_NAMES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    return re.sub(r'gsk_[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}|AQ\.[A-Za-z0-9_-]{20,}', '[REDACTED_CREDENTIAL_PATTERN]', text)


def write(path, data):
    path.write_text(clean(json.dumps(data, ensure_ascii=False, indent=2))+'\n')


def source_sha():
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def run_command(name, command, out):
    print('CHECK '+name, flush=True)
    begin = time.monotonic()
    try:
        child = subprocess.run(command, timeout=600, cwd=ROOT, capture_output=True, text=True, env={**os.environ, 'NO_COLOR':'1','FORCE_COLOR':'0'})
    except subprocess.TimeoutExpired:
        (out/(name+'.log')).write_text('Command exceeded 600 seconds; no success inferred.\n')
        return {'name':name,'status':'FAILED','reason':'Command timeout','seconds':round(time.monotonic()-begin,2),'command':command}
    text = clean(child.stdout+'\n'+child.stderr)
    (out/(name+'.log')).write_text(text)
    counts = {}
    if name == 'python':
        summary = re.findall(r'\b(\d+) (passed|failed|skipped|error|errors)\b', text)
        counts = {kind:int(count) for count,kind in summary}
        if child.returncode == 0 and counts.get('passed', 0) == 0:
            return {'name':name,'status':'FAILED','exit_code':child.returncode,'reason':'Zero or unrecognized executed test count','counts':counts}
    if name in ('frontend-tests','office-tests'):
        matches = re.findall(r'Tests\s+(\d+) passed', text)
        if matches: counts['passed'] = int(matches[-1])
        if child.returncode == 0 and not matches:
            return {'name':name,'status':'FAILED','exit_code':0,'reason':'Missing executed test count'}
    return {'name':name,'status':'PASS' if child.returncode == 0 else 'FAILED','exit_code':child.returncode,'seconds':round(time.monotonic()-begin,2),'counts':counts,'command':command}


class Stack:
    def __init__(self, data):
        self.data = data
        self.process = None
        self.log = None

    def start(self, log):
        for port in (8000,3000,3002):
            with socket.socket() as client:
                if client.connect_ex(('127.0.0.1',port)) == 0:
                    raise RuntimeError('Test port in use; runner never kills unowned services')
        self.log = log.open('w')
        env = dict(os.environ, AGENTVERSE_DATA_DIR=str(self.data))
        original = env.get('AGENTVERSE_PROVIDER_HOSTS','api.openai.com,api.deepseek.com').split(',')
        env['AGENTVERSE_PROVIDER_HOSTS'] = ','.join(dict.fromkeys([*original,'api.groq.com','generativelanguage.googleapis.com']))
        self.process = subprocess.Popen([str(PYTHON),'scripts/dev.py'], cwd=ROOT, env=env, stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline = time.monotonic()+35
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError('Isolated stack exited during startup')
            try:
                with urllib.request.urlopen(API+'/health',timeout=1) as response:
                    if json.load(response)['status'] == 'ok': return
            except OSError: pass
            time.sleep(.2)
        raise RuntimeError('Isolated app readiness deadline exceeded')

    def stop(self):
        if self.process and self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGTERM)
            try: self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.log:
            self.log.close()


def main(args):
    os.umask(0o077)
    out = args.output.resolve()
    if out.exists() or args.data_dir.exists():
        raise SystemExit('Use new output and data paths; never overwrite prior evidence/data')
    out.mkdir(parents=True)
    report = {'test_commit':source_sha(),'application_baseline':'e9f5465756ad1ed6607d2fc8c032ef3387c43812','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile':args.profile,'checks':[],'secret_bindings':{name:bool(os.environ.get(name)) for name in SECRET_NAMES[:2]},'live':None,'overall':'RUNNING','scope':'Current implemented localhost core; known full-P5 functional gaps remain OPEN'}
    stack = Stack(args.data_dir.resolve())
    try:
        if args.profile in ('baseline','full'):
            commands = [
                ('python',[str(PYTHON),'-m','pytest','tests/backend','tests/phase2/runtime','tests/phase3/runtime','tests/phase4','tests/phase5/backend','tests/phase5/integration','tests/phase5/media','tests/phase6','tests/backup','tests/integration','tests/harness','tests/projection','tests/office_layout','-q']),
                ('frontend-tests',['npm','--prefix','apps/web','test']),
                ('frontend-build',['npm','--prefix','apps/web','run','build']),
                ('frontend-lint',['npm','--prefix','apps/web','run','lint']),
                ('office-tests',['npm','--prefix','apps/office','test']),
                ('office-types',['npm','--prefix','apps/office','run','typecheck']),
                ('office-build',['npm','--prefix','apps/office','run','build']),
                ('legacy-model',['node','--test','apps/web/src/office/model.check.ts']),
                ('correctness',[str(PYTHON),'-m','ruff','check','--select','E9,F63,F7,F82','services','tests/phase6','scripts/phase6_system_test.py']),
            ]
            for name, command in commands:
                report['checks'].append(run_command(name,command,out))
                write(out/'system.json',report)
        stack.start(out/'stack.log')
        print('STACK_READY isolated localhost',flush=True)
        if args.profile in ('baseline','full'):
            browser_python = args.browser_python
            sha = report['test_commit']
            commands = [
                ('http-company',[browser_python,'tests/phase5/e2e/console_acceptance.py','--base',API,'--sha',sha,'--output',str(out/'http')]),
                ('browser',[browser_python,'tests/phase5/e2e/browser_behaviors.py','--base',WEB,'--api',API,'--sha',sha,'--output',str(out/'browser')]),
                ('browser-regressions',[browser_python,'tests/phase5/e2e/browser_regressions.py','--base',WEB,'--api',API,'--sha',sha,'--output',str(out/'regressions')]),
                ('media-office',[browser_python,'tests/phase5/integration/visual_media_probe.py','--base',WEB,'--api',API,'--sha',sha,'--output',str(out/'media-office')]),
                ('restart-prepare',[browser_python,'tests/phase5/e2e/restart_probe.py','prepare','--base',API,'--sha',sha,'--snapshot',str(out/'restart.json')]),
            ]
            for name,command in commands:
                report['checks'].append(run_command(name,command,out))
                write(out/'system.json',report)
            stack.stop()
            stack.start(out/'stack-restarted.log')
            report['checks'].append(run_command('restart-verify',[browser_python,'tests/phase5/e2e/restart_probe.py','verify','--base',API,'--sha',sha,'--snapshot',str(out/'restart.json')],out))
        if args.profile in ('live','full'):
            spec = importlib.util.spec_from_file_location('phase6_live',ROOT/'tests/phase6/live/live_acceptance.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            report['live'] = module.run_live(API)
            write(out/'live.json',report['live'])
        failed = any(check['status'] == 'FAILED' for check in report['checks'])
        blocked = False
        if report['live']:
            for entry in report['live']['providers'].values():
                if len(entry['cases']) != 4: failed = True
                if any(row['status'] == 'UNRUN' for row in entry['cases']): blocked = True
                ready = entry['readiness']['status']
                if ready.startswith('FAILED'): failed = True
                elif ready != 'READY': blocked = True
                if any(row['status'].startswith('FAILED') for row in entry['cases']): failed = True
        report['overall'] = 'FAILED' if failed else 'BLOCKED' if blocked else 'PASS_SELECTED_SCOPE'
    except Exception as exc:
        report.update(overall='FAILED_RUNNER',error_type=type(exc).__name__,reason='Runner infrastructure failed; inspect sanitized check logs. No live success inferred.')
    finally:
        stack.stop()
        # Only sanitized startup metadata is kept, never raw exception/provider dumps.
        for log in out.glob('stack*.log'):
            log.write_text(clean(log.read_text()))
        report['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(out/'system.json',report)
    print(json.dumps({'overall':report['overall'],'report':str(out/'system.json'),'secret_bindings':report['secret_bindings']},indent=2),flush=True)
    return 2 if report['overall'].startswith('FAILED') else 3 if report['overall'] == 'BLOCKED' else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=('baseline','live','full'),default='full')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--browser-python',default='python3')
    raise SystemExit(main(parser.parse_args()))
