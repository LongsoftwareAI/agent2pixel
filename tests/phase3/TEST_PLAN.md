# Phase 3 independent QA

Owner: QA. Application source is read-only for this review. Localhost only. Preserve all old data and historical evidence. Follow `docs/contracts/phase3/IMPLEMENTATION.md` at root7993475.

## Required acceptance

1. Create a dedicated QA workspace, supplied source document, agents with explicit roles, and editable workflow using distinct per-node instructions. Verify custom instructions and acceptance criteria reach actual assignment/provider requests; output is produced by runtime, not animation.
2. Create a work item with workflow and criteria. Start its linked run. Generate actual text output; before approval there is no exported file. Approval must contain the exact filename/content hash and be bound to workspace/run/agent/node. Review the generated content, approve, then verify actual file bytes/hash/size and provenance. Completed run produces `review`, never automatically accepted.
3. Explicit human review accepts latest completed run and records decision/comment/time/run; changes requested returns backlog. Editing/running active items is rejected, duplicate launch is prevented. Ordinary GET reads do not rewrite existing resources.
4. Exercise research/content/operations guidance using supplied local sources, not fabricated web research. Deterministic Brain, local provider stub and live model evidence are separate categories. No live provider claim without actual credentials/use.
5. Failure gates: no artifact grant; unsupported extension and traversal; symlink path; mismatched workspace/workflow; stale or reused approval; denial/expiry/cancel; human review before completion; foreign linked run; invalid/malformed instructions or deliverables. No unauthorized file writes or successful review state.
6. Restart at generated-output approval interrupt. Persisted output must survive without provider regeneration, duplicate charging, duplicate file or approval. Consumed approvals cannot be reused. Original IDs/history remain unchanged.
7. Actual localhost browser: Work board create/edit/launch, post-generation approval display, linked run/artifact evidence, human review; WorkflowEditor instructions/deliverable and role-mapped template. Missing grants are visible; no silent role/grant mutation. Capture screenshots and browser/HTTP errors.

QA helpers themselves require Integrator review. Final verdict pins exact application SHA, executed commands, results, evidence paths and limitations. Earlier Phase2 approval does not approve Phase3.
