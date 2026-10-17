# Independent Phase2 QA

Existing host tools: Python with Playwright/Pillow, `/usr/bin/chromium`. No globally installed dependencies. Comparator regression: `python tests/phase2/test_compare_visual.py`.

Start the separate **raw upstream** fixture host with the already installed office Vite binary:

```sh
QA_UPSTREAM=/workspace/reference-checkouts/marmottajr--habblaud QA_APP=/workspace/worktrees/p2-pixel /workspace/worktrees/p2-pixel/apps/office/node_modules/.bin/vite --config tests/phase2/reference/vite.config.mjs
python tests/phase2/capture_visual.py --reference http://127.0.0.1:3102/ --candidate 'http://127.0.0.1:3103/?fixture=parity'
python tests/phase2/audit_vendor.py --app /workspace/worktrees/p2-pixel --upstream /workspace/reference-checkouts/marmottajr--habblaud --output tests/phase2/evidence/vendor-audit.json
python tests/phase2/office_interaction.py
```

The upstream host imports original checkout modules; only snapshot fixture data is shared with candidate. Browser/DPR1/UTC/locale/Date/global entropy/camera are identical. Per-agent/per-room seeded RNG is unchanged. Global `Math.random=()=>0.5` neutralizes different UI consumption of non-agent exterior-car randomness; initial seeded-stream test differed only172/415 exterior car pixels and was diagnosed before correction. No masks; full canvas equality threshold remains0pixels. PNG contact sheets amplify the difference4x for review. Full-page captures preserve branding/control differences.

Fixtures are labeled and do not prove real backend execution. Real pointer test is separate from screenshot parity, and live runtime acceptance remains separate. A clean source commit and app SHA must accompany review.
