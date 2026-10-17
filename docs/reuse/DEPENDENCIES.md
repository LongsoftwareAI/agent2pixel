# Dependency decision record — installed versions

Original application implementation; third-party packages retain their own notices in distributions. Versions below come from installed metadata and the committed lockfiles. This is a license inventory, not a vulnerability-free guarantee.

## Browser/toolchain

| Package | Installed version | Declared license | Purpose |
|---|---|---|---|
| @xyflow/react | 12.12.0 | MIT | runtime UI |
| pixi.js | 8.22.0 | MIT | runtime UI |
| react | 19.3.1 | MIT | runtime UI |
| react-dom | 19.3.1 | MIT | runtime UI |
| zustand | 5.0.15 | MIT | runtime UI |
| @eslint/js | 10.0.1 | MIT | development/test tool |
| @testing-library/react | 16.3.3 | MIT | development/test tool |
| @types/node | 26.6.5 | MIT | development/test tool |
| @types/react | 19.3.0 | MIT | development/test tool |
| @types/react-dom | 19.3.0 | MIT | development/test tool |
| @vitejs/plugin-react | 5.2.0 | MIT | development/test tool |
| eslint | 10.13.0 | MIT | development/test tool |
| jsdom | 27.4.0 | MIT | development/test tool |
| typescript | 5.9.3 | Apache-2.0 | development/test tool |
| typescript-eslint | 8.71.2 | MIT | development/test tool |
| vite | 7.3.7 | MIT | development/test tool |
| vitest | 3.2.7 | MIT | development/test tool |

## Python runtime and development

Exact resolved transitive versions: `services/api/requirements.lock`. Main decisions: FastAPI MIT (REST/WS validation), Uvicorn BSD-3-Clause (ASGI), websockets BSD-3-Clause (real server upgrade support), httpx BSD-3-Clause (bounded HTTP providers), python-dotenv BSD-3-Clause (local config), pytest MIT (tests), Ruff MIT (correctness lint). SQLite is Python standard library. Playwright Apache-2.0 in `tests/e2e/requirements.txt` is QA-only.

## Maintenance and size tradeoffs

Established maintained libraries replace bulk upstream runtime imports. Redis, provider SDK bundles, native PTY, arbitrary shell bridges and city runtimes are excluded. The production Vite build emits a ~732kB minified entry warning (~233kB gzip) because Pixi and ReactFlow share the main bundle; warning is retained, not suppressed. Optimize through lazy imports in a later performance task if measured use warrants it. No dependency audit/security scan was run; test success does not establish absence of advisories. Root Docker base images use verified pull digests recorded in their Dockerfiles.
