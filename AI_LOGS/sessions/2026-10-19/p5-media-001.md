# P5 image media implementation

Owner: p5_media_code. Branch/worktree: agent/p5-extensions, /workspace/worktrees/p5-extensions.
Task: P5-19 safe bounded image attachment and preview, metadata-only source bridge.
Inputs: Phase 5 requirement; uploaded media is untrusted data, not authority.
Ownership: new services/api/console_media.py and tests/phase5/media only; root mounts router.
Reference/license: no reference code or graphics copied; Python stdlib only, no dependency added.
Decision: deliberately narrow PNG subset; reject metadata and animated images. Max 1 MiB, 1M pixels, 2048/side; bounded decompression and CRC validation. No model vision claim.
Permissions: no shell execution, external sending or media publication. Local workspace-scoped persistence.
Verification: root ran identical initial implementation tests with granted network: 17 PASS in 0.42s. Agent TestClient execution stalled under restricted sandbox; own hanging PID stopped. Final additive atomic persistence/corrupt-base64/capability changes require root rerun. Ruff format/check PASS.
Status: READY_FOR_REVIEW; independent approval required. Limitation: narrow PNG subset only; metadata-only agent context, no image interpretation or ASR.
