# P5-19 media handoff

Owner: p5_media_code; agent/p5-extensions. Scope: new console_media.py and tests/phase5/media.
Root integration: import create_console_media_router and app.include_router(create_console_media_router(app)). Console capability/frontend updates belong to their respective owners.
POST /api/console/attachments/image: workspace_id, name, media_type=image/png, content_base64. Max 1 MiB / 1M pixels / 2048 per side. Only 8-bit RGB/RGBA, non-interlaced, no metadata/animation.
GET /api/console/attachments/{id}/image?workspace_id=: scoped integrity-checked image/png; nosniff/no-store/sandbox headers. GET /api/console/media-capabilities?workspace_id=: explicit subset/bounds and unsupported pixel interpretation.
Metadata source integrates existing attachment_ids chat bridge; source explicitly disclaims vision/OCR. Image binary remains local separate resource; no filenames used as filesystem paths. Attachment/image/audit linked writes atomic; source may independently persist if later linked write fails.
Checks: root observed 17 PASS in 0.42s before final additive improvements. Ruff format/check PASS. Root must rerun media tests after final commit. Restricted subagent TestClient hung; own hung PID stopped. No dependency added or upstream graphics copied. Independent QA pending; not DONE.
