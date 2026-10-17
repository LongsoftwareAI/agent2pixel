# Independent localhost acceptance

Start application using root README, using a disposable data directory for QA. Tests create uniquely named workspaces; UI tests use seeded Coding and restore edited instructions/layout. Do not point at valuable live data. Install browser test tooling separately from application:

```sh
python3 -m venv /tmp/agentverse-qa-venv
/tmp/agentverse-qa-venv/bin/python -m pip install -r tests/e2e/requirements.txt
/tmp/agentverse-qa-venv/bin/python -m playwright install chromium
/tmp/agentverse-qa-venv/bin/python tests/e2e/api_acceptance.py --base http://127.0.0.1:8000
/tmp/agentverse-qa-venv/bin/python tests/e2e/browser_acceptance.py --base http://127.0.0.1:3000 --output tests/e2e/evidence
/tmp/agentverse-qa-venv/bin/python tests/e2e/canvas_interaction.py
```

When system Chromium is installed, browser download is unnecessary. Set `CHROMIUM_PATH=/absolute/browser/path` to override; otherwise use system `chromium`/`chromium-browser`, then Playwright-managed Chromium. Root container adds Chromium no-sandbox launch only when required; application security policies are not disabled. Browser failures (including console.error) fail acceptance; initial failures are preserved as historical evidence, not counted as passing. Current structured results and pinned review report distinguish final passes from initial failures.

QA additional backend integration checks (use root application venv):

```sh
.venv/bin/python -m pytest tests/e2e/runtime_security.py -q
```

These check actual condition true routing, wrong-workspace agent rejection, max-step failure, memory isolation, and cancellation during an in-flight real local provider HTTP request with no late completion.
