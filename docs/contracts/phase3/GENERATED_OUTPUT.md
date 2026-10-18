# Generated deliverables and human acceptance

Backend milestone452763f plus correction978c0f5. Existing Phase2 fixed executable fixtures remain separate and compatible. Text export never executes its contents.

Each agent assignment receives upstream output, immutable original run input and work-item brief/acceptance snapshot, node-specific instructions, granted source/memory context and committed evidence. Native and Harness engines share this orchestration. A template is a normal editable graph and does not grant tools or provide external data.

For a node declaring deliverable.filename, actual final output and token accounting are persisted as node_output and task.output/output_generated_at BEFORE approval. Pending approval includes exact filename/content and SHA256 canonical payload, workspace/run/agent/action identity and node provenance. No file exists until explicit approval. Same generated snapshot is used on resume/restart; no second model call or charge. A crash while an external model call itself is in flight is not exactly-once inference; this guarantee starts after durable output is saved.

artifacts.write_text requires explicit grant, even if node declares a deliverable. Safe ASCII basename <=100 characters, extension md/txt/json/csv; content <=128KiB UTF8. No traversal, executable export, symlink parent/file or overwrite. Files under workspace/artifacts/run_id, exclusive create, SHA256/size/run/agent/node metadata. JSON/CSV extension does not assert semantic validation; use a role output_schema for validated JSON. Denial/expiry/cancellation fails closed. A consumed approval without durable result requires reconciliation; never automatically repeat an uncertain write.

Harness model-originated writes remain denied by the shared dispatcher. It produces the final text; the orchestrator subsequently asks for approval and exports it. This is now arbitrary generated text rather than the Phase2 calculator-only output, but is not permission to run arbitrary generated code.

Work-item status is a read-only projection of latest run and current brief_revision. Completed -> review; only explicit human accepted decision -> done. changes_requested -> backlog. Modifying brief/title/criteria increments revision and returns backlog while preserving old runs/reviews as history; old evidence cannot accept revised work. Atomic run/item linkage and serialized transitions prevent duplicate active launches/reviews. Workspace currently permits one active run; multiple department workspaces can run subject to bounded scheduler concurrency.

External research, email, publishing, financial actions, arbitrary-code sandbox, unbounded cycles and general browser automation are not implemented by this slice. They require specific tools, permissions, credentials and tests. Existing DAG flow supports branches and joins with bounded sequential scheduling, not parallel execution of every branch.
