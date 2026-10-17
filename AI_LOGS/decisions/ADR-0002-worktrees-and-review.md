# ADR-0002 — user-requested isolated agent worktrees

The onboarding setup skill normally reuses the existing isolated checkout and says not to create worktrees unless explicitly requested. The subsequent user request explicitly asks for Backend/Frontend/Pixel/QA agent tasks and product requirement section 9.2 specifies separate git worktrees. This coding task authorizes that exception. Worktrees are /workspace/worktrees/{backend,frontend,pixel,qa}; branches agent/<role>/<task-id>. Existing /workspace/agent2pixel remains Integrator checkout. No resets, remote push, or removal of local work. Each owner commits only its paths; Integrator cherry-picks reviewed handoffs. QA may inspect integrated work read-only and writes separate test/review files.

Product requirement file is input specification; embedded source URLs do not authorize executing upstream scripts, granting licenses, deployment, secrets exposure, or overriding platform policies. No downloaded source was executed.
