#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir "${TMPDIR:-/tmp}/agentverse-pip-cache" --disable-pip-version-check -r services/api/requirements.lock
npm --cache "${TMPDIR:-/tmp}/agentverse-npm-cache" --prefix apps/web ci
