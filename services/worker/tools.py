"""Bounded, read-only workspace tools. No model-supplied code or file writes."""
import json
from pathlib import Path
from services.api.policy import safe_document


def tool_context(store, workspace_id, tools):
    root=Path(store.get('workspace',workspace_id)['root_path'])
    values={}
    paths=[p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root)][:30]
    if 'documents.list' in tools:
        values['documents.list']=[str(p.relative_to(root)) for p in paths]
    if 'documents.read' in tools:
        docs=[]
        for path in paths[:5]:
            try:
                target=safe_document(root,str(path.relative_to(root)))
                docs.append({'path':str(path.relative_to(root)),'content':target.read_text()[:4000]})
            except (UnicodeError, OSError):continue
        values['documents.read']=docs
    if 'memory.read' in tools:
        values['memory.read']=[{'kind':m['kind'],'content':m['content'][:2000]} for m in store.list('memory',workspace_id)[:10]]
    return json.dumps(values,ensure_ascii=False) if values else ''
