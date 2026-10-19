import { useEffect, useRef, useState } from 'react';
import { api, pretty } from './api';
interface Memory {
    id: string;
    revision?: number;
    content: string;
    source_id?: string;
    updated_at?: string;
    scope?: string;
    agent_id?: string;
    provenance?: {
        source_id: string;
        sha256?: string;
        url?: string;
        recorded_at?: string;
    };
}
export function MemoryManager({ workspaceId, agentId }: {
    workspaceId: string;
    agentId?: string;
}) { return <Memories key={workspaceId + (agentId ?? '')} workspaceId={workspaceId} agentId={agentId}/>; }
function Memories({ workspaceId, agentId }: {
    workspaceId: string;
    agentId?: string;
}) {
    const alive = useRef(true);
    useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
    const [rows, setRows] = useState<Memory[]>([]), [content, setContent] = useState(''), [source, setSource] = useState(''), [editing, setEditing] = useState<Memory | null>(null), [history, setHistory] = useState<unknown>(), [error, setError] = useState(''), [busy, setBusy] = useState(false);
    async function load() {
        const data = await api<Memory[]>('/api/memories?workspace_id=' + encodeURIComponent(workspaceId) + (agentId ? '&scope=agent&agent_id=' + encodeURIComponent(agentId) : ''));
        if (alive.current)
            setRows(data);
    }
    useEffect(() => {
        void load().catch(e => {
            if (alive.current)
                setError(String(e));
        });
    }, [workspaceId, agentId]);
    async function action(fn: () => Promise<void>) {
        setBusy(true);
        setError('');
        try {
            await fn();
            if (alive.current)
                await load();
        }
        catch (e) {
            if (alive.current)
                setError(String(e));
        }
        finally {
            if (alive.current)
                setBusy(false);
        }
    }
    return <section className="card form-card">
    <h3>Memory có nguồn gốc</h3>
    {error && <p role="alert" className="error">
        {error}
    </p>}
    <label>Nội dung memory<input aria-label="Nội dung memory" value={content} onChange={e => setContent(e.target.value)}/>
    </label>
    <label>Source ID của memory<input aria-label="Source ID của memory" value={source} onChange={e => setSource(e.target.value)} placeholder="Tùy chọn; cùng workspace"/>
    </label>
    <button disabled={busy || !content.trim()} onClick={() => void action(async () => {
            await api(editing ? '/api/memories/' + editing.id + '?workspace_id=' + encodeURIComponent(workspaceId) : '/api/memories', editing ? 'PATCH' : 'POST', {
                ...(!editing ? {
                    workspace_id: workspaceId, kind: 'note', ...(agentId ? {
                        scope: 'agent', agent_id: agentId
                    } : {})
                } : {
                    expected_revision: editing.revision ?? 1
                }), content, source_id: source || null
            });
            if (alive.current) {
                setEditing(null);
                setContent('');
                setSource('');
            }
        })}>
        {editing ? 'Lưu sửa memory' : 'Lưu memory'}
    </button>
    {editing && <button onClick={() => { setEditing(null); setContent(''); setSource(''); }}>Hủy sửa memory</button>}
    {rows.map(m => <article key={m.id}>
        <p>
            {m.content}
        </p>
        <small>Scope {m.scope ?? 'workspace'} · Owner {m.agent_id ?? 'workspace'} · Nguồn {m.source_id ?? 'chưa có'} · {m.updated_at ?? ''}
        </small>
        {m.provenance && <details>
            <summary>Nguồn và dấu vết memory</summary>
            <pre>
                {pretty(m.provenance)}
            </pre>
        </details>}
        <div className="toolbar">
            <button disabled={busy} onClick={() => { setEditing(m); setContent(m.content); setSource(m.source_id ?? ''); }}>Sửa memory</button>
            <button disabled={busy} onClick={() => void action(async () => {
                await api('/api/memories/' + m.id + '?workspace_id=' + encodeURIComponent(workspaceId) + '&expected_revision=' + (m.revision ?? 1), 'DELETE');
                if (editing?.id === m.id && alive.current) {
                    setEditing(null);
                    setContent('');
                    setSource('');
                }
            })}>Xóa memory</button>
            <button onClick={() => void action(async () => {
                const data = await api('/api/memories/' + m.id + '/history');
                if (alive.current)
                    setHistory(data);
            })}>Lịch sử memory</button>
        </div>
    </article>)}
    {history !== undefined && <pre>
        {pretty(history)}
    </pre>}
    </section>;
}
