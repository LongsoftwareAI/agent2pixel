#!/usr/bin/env python3
"""Run the localhost console/API/office. --legacy starts the original v0.1 UI."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--legacy', action='store_true')
args = parser.parse_args()
python = ROOT / '.venv/bin/python'
if not python.exists():
    raise SystemExit('Dependencies missing. Run bash scripts/install.sh first.')
for app in (['web'] if args.legacy else ['web', 'office']):
    if not (ROOT / 'apps' / app / 'node_modules').is_dir():
        raise SystemExit(f'{app} dependencies missing. Run bash scripts/install.sh first.')
children = []


def signal_group(child, sig):
    try:
        os.killpg(child.pid, sig)
    except ProcessLookupError:
        pass


def cleanup():
    for child in children:
        signal_group(child, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            signal_group(child, signal.SIGKILL)
            child.wait(timeout=3)


def stop(*_):
    cleanup()
    raise SystemExit(0)


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
exit_code = 1
try:
    children.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'services.api.main:app', '--host', '127.0.0.1', '--port', '8000'], start_new_session=True))
    if args.legacy:
        children.append(subprocess.Popen(['npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '3000', '--strictPort'], start_new_session=True))
    else:
        console_env = {**os.environ, 'AGENTVERSE_CONTROL_BASE': '/',
                       'AGENTVERSE_OFFICE_PROXY': 'http://127.0.0.1:3002'}
        children.append(subprocess.Popen(['npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '3000', '--strictPort'], env=console_env, start_new_session=True))
        office_env = {**os.environ, 'AGENTVERSE_OFFICE_BASE': '/office/',
                      'AGENTVERSE_CONTROL_PROXY': 'http://127.0.0.1:3000'}
        children.append(subprocess.Popen(['npm', '--prefix', 'apps/office', 'run', 'dev', '--', '--host', '127.0.0.1', '--port', '3002', '--strictPort'], env=office_env, start_new_session=True))
    while all(child.poll() is None for child in children):
        time.sleep(.3)
    exit_code = next((child.returncode for child in children if child.poll() is not None), 1)
    print(f'A service exited ({exit_code}); stopping stack.', file=sys.stderr)
finally:
    cleanup()
sys.exit(exit_code)
