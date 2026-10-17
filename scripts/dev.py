#!/usr/bin/env python3
"""Run the loopback-only development stack; Ctrl-C stops both children."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if not (ROOT / "apps/web/node_modules").is_dir():
    raise SystemExit("Dependencies missing. Run bash scripts/install.sh first.")
python = ROOT / ".venv/bin/python"
if not python.exists():
    raise SystemExit("Python environment missing. Run bash scripts/install.sh first.")
children = []
def stop(*_):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
    raise SystemExit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
try:
    children.append(subprocess.Popen([str(python), "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8000"]))
    children.append(subprocess.Popen(["npm", "--prefix", "apps/web", "run", "dev", "--", "--host", "127.0.0.1", "--port", "3000", "--strictPort"]))
    while all(child.poll() is None for child in children):
        time.sleep(0.4)
    code = next((child.returncode for child in children if child.poll() is not None), 1)
    print(f"A service exited ({code}); stopping stack.", file=sys.stderr)
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
sys.exit(code)
