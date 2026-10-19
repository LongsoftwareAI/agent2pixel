import { ArchiveWork } from './ConsoleOperations';
import { CompanyOperations, VersionComparison } from './CompanyOperations';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api as request } from './api';
import type { Agent, Run, WorkItem, Workflow } from './types';
const labels: Record<string, string> = {
    queued: 'Trong hàng đợi', backlog: 'Chưa bắt đầu', running: 'Đang chạy', waiting_approval: 'Chờ phê duyệt công cụ', review: 'Chờ người dùng review', done: 'Đã nghiệm thu', failed: 'Thất bại', cancelled: 'Đã hủy'
};
type Props = {
    workspaceId: string;
    workflows: Workflow[];
    agents?: Agent[];
    onRun: (run: Run) => void;
};
export function WorkBoard(props: Props) { return <WorkspaceWorkBoard key={props.workspaceId} {...props}/>; }
function WorkspaceWorkBoard({ workspaceId, workflows, agents = [], onRun }: Props) {
    const active = useRef(true);
    useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
    const api = async <T,>(...args: Parameters<typeof request>): Promise<T> => {
        if (!active.current)
            throw Error('Workspace đã thay đổi');
        const value = await request<T>(...args);
        if (!active.current)
            throw Error('Workspace đã thay đổi');
        return value;
    };
    const [items, setItems] = useState<WorkItem[]>([]), [editing, setEditing] = useState<WorkItem | null>(null), [title, setTitle] = useState(''), [description, setDescription] = useState(''), [criteria, setCriteria] = useState(''), [workflow, setWorkflow] = useState(''), [comments, setComments] = useState<Record<string, string>>({}), [busy, setBusy] = useState(false), [error, setError] = useState(''), [priority, setPriority] = useState('normal'), [due, setDue] = useState(''), [owner, setOwner] = useState(''), [search, setSearch] = useState(''), [archived, setArchived] = useState(false);
    const refresh = useCallback(async () => setItems(await api<WorkItem[]>('/api/work-items?workspace_id=' + encodeURIComponent(workspaceId))), [workspaceId]);
    useEffect(() => {
        let active = true;
        const update = () => api<WorkItem[]>('/api/work-items?workspace_id=' + encodeURIComponent(workspaceId)).then(data => {
            if (active)
                setItems(data);
        }).catch(e => {
            if (active)
                setError(String(e));
        });
        void update();
        const timer = setInterval(update, 2000);
        return () => { active = false; clearInterval(timer); };
    }, [workspaceId]);
    useEffect(() => {
        const item = new URLSearchParams(location.hash.split('?')[1]).get('item');
        if (item)
            document.getElementById('work-item-' + item)?.scrollIntoView?.({
                block: 'center'
            });
    }, [items]);
    const action = async (fn: () => Promise<void>) => {
        setBusy(true);
        setError('');
        try {
            await fn();
            await refresh();
        }
        catch (e) {
            if (active.current)
                setError(String(e));
        }
        finally {
            if (active.current)
                setBusy(false);
        }
    };
    const reset = () => { setEditing(null); setTitle(''); setDescription(''); setCriteria(''); setPriority('normal'); setDue(''); setOwner(''); };
    return <>
    <div className="section-heading">
        <div>
            <h2>Bảng công việc của công ty</h2>
            <p>Brief → workflow → output và bằng chứng → người dùng nghiệm thu. Run hoàn thành vẫn cần review.</p>
        </div>
    </div>
    {error && <p className="banner error" role="alert">
        {error}
    </p>}
    <CompanyOperations workspaceId={workspaceId} onRun={onRun}/>
    <section className="card form-card">
        <a href="#workflows">Tạo / chỉnh sửa workflow và template ↗</a>
        <h3>
            {editing ? 'Sửa brief' : 'Giao công việc mới'}
        </h3>
        <label>Tiêu đề công việc<input aria-label="Tiêu đề công việc" maxLength={200} value={title} onChange={e => setTitle(e.target.value)}/>
        </label>
        <label>Brief<textarea aria-label="Brief" value={description} onChange={e => setDescription(e.target.value)}/>
        </label>
        <label>Tiêu chí nghiệm thu (mỗi dòng)<textarea aria-label="Tiêu chí nghiệm thu" value={criteria} onChange={e => setCriteria(e.target.value)}/>
        </label>
        <label>Workflow công việc<select aria-label="Workflow công việc" disabled={!!editing} value={editing?.workflow_id ?? workflow} onChange={e => setWorkflow(e.target.value)}>
                <option value="">Chọn workflow đã lưu</option>
                {workflows.map(w => <option key={w.id} value={w.id}>
                    {w.name} · v{w.version}
                </option>)}
            </select>
        </label>
        <label>Ưu tiên<select aria-label="Ưu tiên" value={priority} onChange={e => setPriority(e.target.value)}>
                <option value="low">Thấp</option>
                <option value="normal">Bình thường</option>
                <option value="high">Cao</option>
            </select>
        </label>
        <label>Deadline<input aria-label="Deadline" type="datetime-local" value={due} onChange={e => setDue(e.target.value)}/>
        </label>
        <label>Người phụ trách<select aria-label="Người phụ trách" value={owner} onChange={e => setOwner(e.target.value)}>
                <option value="">Chưa giao</option>
                {agents.map(a => <option key={a.id} value={a.id}>
                    {a.name}
                </option>)}
            </select>
        </label>
        <button className="primary" disabled={busy || !title.trim() || !description.trim() || !criteria.trim() || (!editing && !workflow)} onClick={() => void action(async () => { const body = {
        priority, due_at: due ? new Date(due).toISOString() : null, owner_agent_id: owner || null, title: title.trim(), description: description.trim(), acceptance_criteria: criteria.split('\n').map(s => s.trim()).filter(Boolean)
    }; await api(editing ? '/api/work-items/' + editing.id : '/api/work-items', editing ? 'PATCH' : 'POST', editing ? body : {
        ...body, workspace_id: workspaceId, workflow_id: workflow
    }); reset(); })}>
            {editing ? 'Lưu brief' : 'Tạo công việc'}
        </button>
        {editing && <button onClick={reset}>Hủy sửa</button>}
    </section>
    <section className="card form-card">
        <h3>Công việc · {items.length}
        </h3>
        <label>Tìm công việc<input aria-label="Tìm công việc" value={search} onChange={e => setSearch(e.target.value)}/>
        </label>
        <label>
            <input type="checkbox" checked={archived} onChange={e => setArchived(e.target.checked)}/>Hiện công việc đã lưu trữ</label>
        {!items.length && <p>Chưa có công việc trong workspace này.</p>}
        {items.filter(item => { const agent = new URLSearchParams(location.hash.split('?')[1]).get('agent'); return (!agent || item.owner_agent_id === agent) && (!search || (item.title + ' ' + item.description).toLowerCase().includes(search.toLowerCase())) && (archived || !(item as unknown as Record<string, unknown>).archived); }).map(item => <article key={item.id} id={'work-item-' + item.id} className={'work-item ' + (new URLSearchParams(location.hash.split('?')[1]).get('item') === item.id ? 'c-selected-item' : '')}>
            <div className="toolbar">
                <h3>
                    {item.title}
                </h3>
                <span className={'status ' + item.status}>
                    {labels[item.status] ?? item.status}
                </span>
            </div>
            <p>
                {item.description}
            </p>
            <p>Ưu tiên: {item.priority ?? 'normal'} · Hạn: {item.due_at ?? 'không có'} · Phụ trách: {agents.find(a => a.id === item.owner_agent_id)?.name ?? 'chưa giao'}
            </p>
            <button disabled={busy || ['running', 'waiting_approval', 'done', 'review'].includes(item.status)} onClick={() => void action(async () => { await api('/api/work-items/' + item.id + (item.queue_requested ? '/dequeue' : '/enqueue'), 'POST', {}); })}>
                {item.queue_requested ? 'Rút khỏi hàng đợi' : 'Đưa vào hàng đợi'}
            </button>
            <ArchiveWork workspaceId={workspaceId} item={item as unknown as Record<string, unknown>} onChanged={refresh}/>
            <VersionComparison item={item}/>
            {(item.brief_revision ?? 1) > 1 && <p className="muted">Brief phiên bản {item.brief_revision}. {item.status === 'backlog' ? 'Cần chạy lại để nghiệm thu brief đã sửa; run và review cũ được giữ làm lịch sử.' : 'Bằng chứng và review được lưu theo từng run.'}
            </p>}
            <ul>
                {item.acceptance_criteria.map((c, i) => <li key={i}>
                    {c}
                </li>)}
            </ul>
            <small>Workflow: {workflows.find(w => w.id === item.workflow_id)?.name ?? item.workflow_id}
            </small>
            <div className="toolbar">
                <button disabled={busy || ['running', 'waiting_approval'].includes(item.status)} onClick={() => { setEditing(item); setTitle(item.title); setDescription(item.description); setCriteria(item.acceptance_criteria.join('\n')); setPriority(item.priority ?? 'normal'); setDue(item.due_at ? new Date(new Date(item.due_at).getTime() - new Date(item.due_at).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ''); setOwner(item.owner_agent_id ?? ''); }}>Sửa brief</button>
                <button disabled={busy || ['running', 'waiting_approval', 'done', 'review'].includes(item.status)} onClick={() => void action(async () => onRun(await api<Run>('/api/work-items/' + item.id + '/runs', 'POST', {})))}>Chạy công việc</button>
                {item.latest_run_id && <button onClick={() => onRun({
            id: item.latest_run_id
        } as Run)}>Xem run và bằng chứng ↗</button>}
            </div>
            {item.status === 'review' && <>
                <label>Nhận xét review<textarea aria-label={'Review ' + item.title} value={comments[item.id] ?? ''} onChange={e => setComments({
                ...comments, [item.id]: e.target.value
            })}/>
                </label>
                {(['accepted', 'changes_requested'] as const).map(decision => <button key={decision} disabled={busy || !comments[item.id]?.trim()} onClick={() => void action(async () => { await api('/api/work-items/' + item.id + '/review', 'POST', {
                    decision, comment: comments[item.id].trim()
                }); })}>
                    {decision === 'accepted' ? 'Nghiệm thu kết quả' : 'Yêu cầu sửa'}
                </button>)}
            </>}
            {item.reviews?.map((r, i) => <p key={i}>
                {r.decision}: {r.comment} {r.run_id && <code>
                    {r.run_id}
                </code>}
            </p>)}
        </article>)}
    </section>
    </>;
}
