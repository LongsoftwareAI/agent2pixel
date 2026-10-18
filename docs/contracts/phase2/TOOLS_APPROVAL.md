# Localhost approved actions, version 1

Run input accepts up to 12 actions with exact workflow agent_id, tool and payload. The LangGraph node persists a pending approval and interrupts before the action. GET `/api/runs/{id}/approvals`; POST `/api/approvals/{id}/decision` with decision `approved` or `denied`. Approval expires after 15 minutes and is single-use, bound to workspace/run/agent/tool/payload hash. Resume uses the same checkpoint. Denial fails closed; restart does not repeat committed writes. A consumed action without a durable result fails closed.

Supported actions:

- `artifacts.write_python`: only filename `calculator.py` with template `calculator-v1`, or `test_calculator.py` with template `calculator-tests-v1`.
- `tests.run_pytest`: empty payload; isolated fixed invocation with `-I`, `--noconftest`, `-c /dev/null`, sanitized environment. No arbitrary shell or code input.

Shared dispatcher enforces tool grants, scoped memory and workspace containment. Harness plugin can read documents, memory and exactly bound committed approved action results. It cannot approve itself. Native LangGraph actions currently create the reviewed fixture and run tests before Harness receives the assignment. Harness retrieves their results; this does not demonstrate autonomous model-authored code or model-originated writes. Official SDK/runtime tests use a local provider stub; live model use needs a configured credential.
