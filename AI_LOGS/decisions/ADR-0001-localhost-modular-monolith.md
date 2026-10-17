# ADR-0001 — localhost MVP foundation

Accepted by Architect/Integrator for user-authorized MVP. React+TypeScript+Vite, PixiJS, React Flow and Zustand; Python FastAPI and SQLite using versioned SQL migration, no Redis. A background task worker module executes validated DAGs with cancellation, bounded retries, step/token budgets and provider adapters. Keep renderer independent from runtime. Only loopback binds; no shell execution. Two isolated project roots and room namespaces.

Dependencies: React (MIT), Vite (MIT), TypeScript (Apache-2.0), PixiJS (MIT), @xyflow/react (MIT), Zustand (MIT), FastAPI (MIT), Uvicorn (BSD-3-Clause), httpx (BSD-3-Clause), pytest (MIT), Playwright (Apache-2.0). These established libraries avoid copying reference implementations. Runtime versions locked after install; inspect package metadata and retain installed license files. Browser bundle limited to UI dependencies. SQLite is standard library. Risks: external provider API availability, browser binary download, cancellation during HTTP requests; validate failure paths.

Artwork: generate original procedural tile/sprite drawings in source, CC0, do not copy reference pixels. Screenshots of reference sources are research evidence only unless rights confirmed. No public deployment.
