import { useConsoleEvents } from './useConsoleEvents';
import { TokenAccounting, accountingLabel } from './TokenAccounting';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, pretty } from './api';
import { useStore } from './store';
import type { Agent, Bootstrap, Workspace, Workflow, Run } from './types';
import App from './App';
import { MemoryManager } from './MemoryManager';
import './console.css';
import { VoiceDraft } from './VoiceDraft';
import { ConsoleIcon } from './ConsoleIcon';
import { Budget, RevisionHistory, LogExport } from './ConsoleOperations';
import { ArtifactPreview } from './ReviewGates';
import { SafeMarkdown } from './SafeMarkdown';
import { ConsoleTopology } from './ConsoleTopology';
type Row = Record<string, unknown>;
interface Preferences {
    theme: string;
    accent: string;
    sidebar: string;
    font: string;
    density: string;
    office_enabled: boolean;
    start_page: string;
    refresh: string;
    revision?: number;
}
interface Conversation {
    id: string;
    agent_id: string | null;
    title: string;
    messages?: ChatMessage[];
}
interface ChatMessage {
    id: string;
    role: string;
    content: string;
    created_at: string;
    run_id?: string;
    work_item_id?: string;
    state?: string;
    error?: string;
    artifacts?: Row[];
}
interface Overview {
    agents: {
        total: number;
        busy: number;
    };
    work: {
        total: number;
        pending_review: number;
        completed: number;
    };
    runs: {
        total: number;
        active: number;
    };
    usage: {
        input_tokens: number | null;
        output_tokens: number | null;
        actual_cost: null;
        estimated_cost: null;
        total_tokens?: number | null;
        token_accounting?: string;
        accounting_counts?: Record<string, number>;
        tokens_by_accounting?: Record<string, number>;
    };
    activity: Row[];
    services: Row[];
    observed_at: string;
}
const defaults: Preferences = {
    theme: 'dark', accent: 'blue', sidebar: 'full', font: 'medium', density: 'comfortable', office_enabled: true, start_page: 'overview', refresh: 'slow'
};
const groups = [{
        label: 'KHÔNG GIAN', items: [['office', '▦', 'Văn phòng AI'], ['overview', '◫', 'Tổng quan'], ['inbox', '◉', 'Cần bạn xử lý'], ['room', '▤', 'Phòng chung']]
    }, {
        label: 'ĐIỀU HÀNH', items: [['bots', '♙', 'Danh sách bot'], ['workboard', '☑', 'Giao việc & duyệt QC'], ['chat', '◇', 'Chat với bot'], ['schedules', '◷', 'Lịch tự chạy'], ['workflows', '⌘', 'Workflow']]
    }, {
        label: 'TÀI NGUYÊN BOT', items: [['skills', '▧', 'Kho skill'], ['memory', '▥', 'Bộ nhớ'], ['sources', '▱', 'Nguồn dữ liệu'], ['channels', '⌁', 'Kênh kết nối']]
    }, {
        label: 'THEO DÕI', items: [['topology', '⤢', 'Sơ đồ hệ thống'], ['usage', '▥', 'Chi phí & ngân sách'], ['sessions', '◴', 'Phiên làm việc'], ['logs', '≡', 'Log hệ thống'], ['audit', '↳', 'Nhật ký thao tác']]
    }, {
        label: '', items: [['preferences', '⚙', 'Cài đặt']]
    }];
const links = groups.flatMap(g => g.items);
const readRoute = () => {
    const raw = location.hash.slice(1).split('?')[0];
    if (raw === 'agents' && location.hash.includes('agent='))
        return 'bots';
    return links.some(x => x[0] === raw) || ['runs', 'agents', 'settings'].includes(raw) ? raw : 'overview';
};
const stamp = (value: unknown) => typeof value === 'string' ? new Date(value).toLocaleString('vi-VN') : '—';
const str = (value: unknown, fallback = '—') => value === undefined || value === null ? fallback : typeof value === 'object' ? pretty(value) : String(value);
const rows = (value: unknown): Row[] => Array.isArray(value) ? value.filter((x): x is Row => typeof x === 'object' && x !== null) : [];
const number = (value: unknown) => typeof value === 'number' ? new Intl.NumberFormat('vi-VN', {
    notation: value > 99999 ? 'compact' : 'standard', maximumFractionDigits: 1
}).format(value) : '—';
function State({ value }: {
    value: unknown;
}) {
    const text = str(value, 'unknown');
    return <span className={'c-state ' + text.replace(/[^a-z_]/g, '')}>
    {text}
    </span>;
}
function Empty({ children }: {
    children: React.ReactNode;
}) {
    return <div className="c-empty">
    <span>◇</span>
    <p>
        {children}
    </p>
    </div>;
}
function Feed({ items }: {
    items: Row[];
}) {
    return <div className="c-feed">
    {items.length ? items.map((item, i) => <article key={str(item.id, String(i))}>
        <span className="c-event-dot"/>
        <div>
            <strong>
                {str(item.action ?? item.event_type ?? item.name ?? item.kind, 'Sự kiện')}
            </strong>
            <p>
                {str(item.message ?? item.reason ?? item.summary ?? item.state, '')}
            </p>
            <small>
                {stamp(item.created_at ?? item.timestamp ?? item.observed_at)}
            </small>
            <details>
                <summary>Chi tiết</summary>
                <pre>
                    {pretty(item)}
                </pre>
            </details>
        </div>
    </article>) : <Empty>Chưa có dữ liệu trong workspace này.</Empty>}
    </div>;
}
export default function Console() { const { workspaceId, setWorkspace } = useStore(); return <ConsoleWorkspace key={workspaceId} workspaceId={workspaceId} setWorkspace={setWorkspace}/>; }
function ConsoleWorkspace({ workspaceId, setWorkspace }: {
    workspaceId: string;
    setWorkspace: (id: string) => void;
}) {
    const [route, setRoute] = useState(readRoute), [workspaces, setWorkspaces] = useState<Workspace[]>([]), [bootstrap, setBootstrap] = useState<Bootstrap | null>(null), [overview, setOverview] = useState<Overview | null>(null), [preferences, setPreferences] = useState<Preferences>(defaults), [error, setError] = useState(''), [notice, setNotice] = useState(''), [loading, setLoading] = useState(false), [observed, setObserved] = useState(''), [palette, setPalette] = useState(false), [search, setSearch] = useState('');
    const { revision: eventRevision, connection: eventConnection } = useConsoleEvents(workspaceId);
    const alive = useRef(true);
    const started = useRef(false);
    const prefsRef = useRef(preferences);
    prefsRef.current = preferences;
    const navigate = useCallback((next: string) => { location.hash = next; setRoute(next.split('?')[0]); setPalette(false); }, []);
    useEffect(() => {
        alive.current = true;
        const change = () => setRoute(readRoute());
        window.addEventListener('hashchange', change);
        const keyboard = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setPalette(v => !v);
            }
            if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
                e.preventDefault();
                if (prefsRef.current.revision == null)
                    return;
                void api<Preferences>('/api/console/preferences?workspace_id=' + encodeURIComponent(workspaceId), 'PATCH', {
                    ...prefsRef.current, sidebar: prefsRef.current.sidebar === 'full' ? 'collapsed' : 'full'
                }).then(saved => {
                    if (alive.current)
                        setPreferences({
                            ...defaults, ...saved
                        });
                }).catch(e => {
                    if (alive.current)
                        setError(String(e));
                });
            }
            if (e.key === 'Escape')
                setPalette(false);
        };
        window.addEventListener('keydown', keyboard);
        return () => { alive.current = false; window.removeEventListener('hashchange', change); window.removeEventListener('keydown', keyboard); };
    }, []);
    useEffect(() => {
        api<Workspace[]>('/api/workspaces').then(data => {
            if (!alive.current)
                return;
            setWorkspaces(data);
            const requested = new URLSearchParams(location.hash.split('?')[1]).get('workspace');
            if (requested && requested !== workspaceId && data.some(w => w.id === requested)) {
                setWorkspace(requested);
                return;
            }
            if (!data.some(w => w.id === workspaceId) && data[0])
                setWorkspace(data[0].id);
        }).catch(e => {
            if (alive.current)
                setError(String(e));
        });
    }, [workspaceId, setWorkspace]);
    const refresh = useCallback(async () => {
        if (!workspaceId)
            return;
        setLoading(true);
        try {
            const [data, summary, prefs] = await Promise.all([api<Bootstrap>('/api/bootstrap?workspace_id=' + encodeURIComponent(workspaceId)), api<Overview>('/api/console/overview?workspace_id=' + encodeURIComponent(workspaceId)), api<Preferences>('/api/console/preferences?workspace_id=' + encodeURIComponent(workspaceId))]);
            if (!alive.current)
                return;
            setBootstrap(data);
            setOverview(summary);
            setPreferences(current => (current.revision ?? 0) > (prefs.revision ?? 0) ? current : {
                ...defaults, ...prefs
            });
            setObserved(summary.observed_at);
            setError('');
            if (!started.current) {
                started.current = true;
                if (!location.hash && links.some(x => x[0] === prefs.start_page))
                    navigate(prefs.start_page);
            }
        }
        catch (e) {
            if (alive.current)
                setError(String(e));
        }
        finally {
            if (alive.current)
                setLoading(false);
        }
    }, [workspaceId, navigate]);
    useEffect(() => { void refresh(); }, [refresh]);
    useEffect(() => {
        if (!eventRevision)
            return;
        const timer = setTimeout(() => void refresh(), 120);
        return () => clearTimeout(timer);
    }, [eventRevision, refresh]);
    useEffect(() => {
        if (preferences.refresh === 'off')
            return;
        const timer = setInterval(() => void refresh(), preferences.refresh === 'fast' ? 5000 : 15000);
        return () => clearInterval(timer);
    }, [preferences.refresh, refresh]);
    useEffect(() => { const media = window.matchMedia?.('(prefers-color-scheme: light)'); const update = () => { document.documentElement.dataset.consoleTheme = preferences.theme === 'system' ? (media?.matches ? 'light' : 'dark') : preferences.theme; }; update(); media?.addEventListener?.('change', update); return () => { media?.removeEventListener?.('change', update); delete document.documentElement.dataset.consoleTheme; }; }, [preferences.theme]);
    const action = async (fn: () => Promise<void>) => {
        setError('');
        setNotice('');
        try {
            await fn();
        }
        catch (e) {
            if (alive.current)
                setError(e instanceof Error ? e.message : String(e));
        }
    };
    const savePreferences = async (next: Preferences) => {
        await action(async () => {
            const saved = await api<Preferences>('/api/console/preferences?workspace_id=' + encodeURIComponent(workspaceId), 'PATCH', next);
            if (alive.current) {
                setPreferences({
                    ...defaults, ...saved
                });
                setNotice('Đã lưu cài đặt');
            }
        });
    };
    const legacy = ['workflows', 'workboard', 'sources', 'runs', 'agents', 'settings'].includes(route);
    const title = links.find(x => x[0] === route)?.[2] ?? (route === 'runs' ? 'Run Monitor' : route === 'agents' ? 'Agent Studio' : 'Cấu hình provider');
    const agents = bootstrap?.agents ?? [];
    const workflows = bootstrap?.workflows ?? [];
    return <div className={`console c-${preferences.sidebar} c-font-${preferences.font} c-density-${preferences.density} c-accent-${preferences.accent}`}>
 <aside className="c-sidebar">
        <a href="#overview" className="c-brand">
            <span className="c-logo">A</span>
            <span>AgentVerse<small>AI operations console</small>
            </span>
        </a>
        <div className="c-workspace">
            <label htmlFor="console-workspace">WORKSPACE</label>
            <select id="console-workspace" value={workspaceId} onChange={e => setWorkspace(e.target.value)}>
                {workspaces.map(w => <option key={w.id} value={w.id}>
                    {w.name}
                </option>)}
            </select>
        </div>
        <nav aria-label="Điều hướng console">
            {groups.map((group, i) => <div className="c-nav-group" key={i}>
                {group.label && <div className="c-group-label">
                    {group.label}
                </div>}
                {group.items.map(([id, _icon, label]) => id === 'office' ? <a key={id} className="c-nav" href="/office/" aria-disabled={!preferences.office_enabled} onClick={e => {
                    if (!preferences.office_enabled)
                        e.preventDefault();
                }}>
                    <span>
                        <ConsoleIcon id={id}/>
                    </span>
                    <b>
                        {label}
                    </b>
                    <small>↗</small>
                </a> : <button className={'c-nav ' + (route === id ? 'selected' : '')} title={label} key={id} onClick={() => navigate(id)}>
                    <span>
                        <ConsoleIcon id={id}/>
                    </span>
                    <b>
                        {label}
                    </b>
                    {id === 'inbox' && !!overview?.work.pending_review && <em>
                        {overview.work.pending_review}
                    </em>}
                    {id === 'schedules' && <small>·</small>}
                </button>)}
            </div>)}
        </nav>
        <div className="c-sidebar-foot">
            <div className="c-team">
                {agents.slice(0, 6).map((a, i) => <span title={a.name} key={a.id} style={{
            background: ['#344a72', '#4c3d61', '#31564d', '#685138'][i % 4]
        }}>
                    {a.name.slice(0, 1)}
                </span>)}
                <small>
                    {agents.length} bot</small>
            </div>
            <button disabled={preferences.revision == null} onClick={() => void savePreferences({
        ...preferences, sidebar: preferences.sidebar === 'full' ? 'collapsed' : 'full'
    })}>☰ <b>Thu gọn menu</b>
                <kbd>⌘B</kbd>
            </button>
            <div className="c-local">
                <i className={error ? 'bad' : !observed ? 'unknown' : ''}/>
                <span>
                    {error ? 'Kết nối lỗi · dữ liệu có thể cũ' : observed ? 'Localhost · đã đồng bộ' : 'Đang kết nối…'}
                </span>
            </div>
        </div>
    </aside>
 <div className="c-main">
        <header className="c-header">
            <div className="c-breadcrumb">AgentVerse <span>/</span> <strong>
                    {title}
                </strong>
            </div>
            <button className="c-search" onClick={() => setPalette(true)}>⌕ <span>Tìm màn, bot, việc...</span>
                <kbd>⌘K</kbd>
            </button>
            <div className="c-header-end">
                <span className="c-local-tag">LOCAL</span>
                <button disabled={preferences.revision == null} aria-label="Đổi giao diện" title="Đổi sáng/tối" onClick={() => void savePreferences({
        ...preferences, theme: preferences.theme === 'dark' ? 'light' : 'dark'
    })}>☼</button>
                <span className="c-user">AV</span>
            </div>
        </header>
 {error && <div className="c-banner c-error" role="alert">
            {error}
            <button onClick={() => void refresh()}>Thử lại</button>
        </div>}
        {notice && <div className="c-banner" role="status">
            {notice}
            <button aria-label="Đóng thông báo" onClick={() => setNotice('')}>×</button>
        </div>}
 <main className="c-content" aria-busy={loading}>
            <div className="c-page-head">
                <div>
                    <h1>
                        {title}
                    </h1>
                    <p>
                        {route === 'overview' ? 'Một không gian để điều hành cả đội AI. Công việc thật, dấu vết rõ ràng.' : workspaces.find(w => w.id === workspaceId)?.name ?? 'Đang kết nối workspace'}
                    </p>
                </div>
                <div className="c-page-actions">
                    <small>
                        {loading ? 'Đang đồng bộ…' : observed ? 'Cập nhật ' + stamp(observed) : 'Chưa có dữ liệu'}
                    </small>
                    <button onClick={() => void refresh()} disabled={loading}>↻ Làm mới</button>
                    {route === 'overview' && <button className="c-primary" onClick={() => navigate('workboard')}>＋ Giao việc</button>}
                </div>
            </div>
 {route === 'overview' && <Dashboard overview={overview} agents={agents} workspaceId={workspaceId} navigate={navigate} runs={bootstrap?.runs ?? []}/>}
 {(route === 'room' || route === 'chat') && <Chat eventRevision={eventRevision} key={route + workspaceId} workspaceId={workspaceId} agents={agents} workflows={workflows} direct={route === 'chat'} navigate={navigate}/>}
 {route === 'bots' && <Bots workspaceId={workspaceId} agents={agents} navigate={navigate} onRefresh={refresh}/>}
 {route === 'memory' && <MemoryPage workspaceId={workspaceId} agents={agents}/>}
 {route === 'skills' && <Skills workspaceId={workspaceId} agents={agents}/>}
 {['inbox', 'schedules', 'channels', 'topology', 'usage', 'sessions', 'logs', 'audit'].includes(route) && <Resources key={route + workspaceId} route={route} workspaceId={workspaceId} navigate={navigate}/>}
 {route === 'preferences' && <PreferencesPanel key={preferences.revision ?? 'loading'} preferences={preferences} save={savePreferences} navigate={navigate}/>}
 {legacy && <div className="c-legacy">
                <App />
            </div>}
 </main>
        <footer className="c-footer">
            <span role="status">
                {eventConnection === 'live' ? 'Sự kiện runtime trực tiếp' : eventConnection === 'disconnected' ? 'Mất kết nối sự kiện · đang kết nối lại; dữ liệu có thể cũ' : 'Đang kết nối sự kiện runtime…'}
            </span>
            <span>
                <i /> AgentVerse · Local workspace</span>
            <span>Native + Harness runtime · permissions preserved</span>
        </footer>
    </div>
 {palette && <div className="c-modal-shade" onClick={() => setPalette(false)}>
        <section role="dialog" aria-modal="true" aria-label="Điều hướng nhanh" className="c-palette" onClick={e => e.stopPropagation()}>
            <input autoFocus aria-label="Tìm màn hình" placeholder="Tìm màn hình hoặc bot…" value={search} onChange={e => setSearch(e.target.value)}/>
            <div>
                {links.filter(x => x[0] !== 'office' && x[2].toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))).map(([id, icon, label]) => <button key={id} onClick={() => navigate(id)}>
                    {icon} {label}
                    <span>↵</span>
                </button>)}
                {agents.filter(a => search && a.name.toLowerCase().includes(search.toLowerCase())).map(a => <button key={a.id} onClick={() => navigate('bots')}>♙ {a.name} <small>
                        {a.role}
                    </small>
                </button>)}
            </div>
            <small>Esc để đóng · chọn một màn hình để mở</small>
        </section>
    </div>}
 </div>;
}
function Dashboard({ overview: o, agents, workspaceId, navigate, runs }: {
    overview: Overview | null;
    agents: Agent[];
    workspaceId: string;
    navigate: (p: string) => void;
    runs: Run[];
}) {
    const [usage, setUsage] = useState<Row>({}), [usageError, setUsageError] = useState('');
    useEffect(() => {
        let active = true;
        void api<Row>('/api/console/usage?workspace_id=' + encodeURIComponent(workspaceId) + '&period=30').then(d => {
            if (active) {
                setUsage(d);
                setUsageError('');
            }
        }).catch(e => {
            if (active)
                setUsageError(String(e));
        });
        return () => { active = false; };
    }, [workspaceId]);
    return <>
    <div className="c-stats">
        {[['Bot đang làm việc', o?.agents.busy, o ? '/ ' + o.agents.total + ' bot cấu hình' : 'Chưa tải'], ['Công việc hoàn thành', o?.work.completed, 'Trong workspace'], ['Token đã ghi nhận', o?.usage.total_tokens ?? (o?.usage.input_tokens != null && o?.usage.output_tokens != null ? o.usage.input_tokens + o.usage.output_tokens : undefined), accountingLabel(o?.usage.token_accounting)], ['Cần bạn xử lý', o?.work.pending_review, 'Duyệt kết quả & quyết định']].map(([label, value, hint], i) => <button className="c-stat" key={String(label)} onClick={() => navigate(['bots', 'workboard', 'usage', 'inbox'][i])}>
            <span>
                {str(label)}
            </span>
            <strong>
                {number(value)}
            </strong>
            <small>
                <i className={i === 3 ? 'amber' : ''}/>
                {hint}
            </small>
        </button>)}
    </div>
    <div className="c-dashboard-grid">
        <section className="c-card">
            <div className="c-card-head">
                <h2>Token theo ngày <small>30 ngày gần nhất</small>
                </h2>
                <button onClick={() => navigate('usage')}>Mở chi phí →</button>
            </div>
            {usageError && <p className="c-error c-padding" role="alert">Không tải được usage: {usageError}
            </p>}
            <div className="c-bar-chart c-dashboard-chart">
                {rows(usage.daily).length ? rows(usage.daily).map((d, i) => {
            const value = Number(d.total_tokens ?? 0);
            const max = Math.max(...rows(usage.daily).map(x => Number(x.total_tokens ?? 0)), 1);
            return <div key={i} title={pretty(d)}>
                    <span style={{
                height: Math.max(2, value / max * 150) + 'px'
            }}/>
                    <small>
                        {str(d.date ?? d.day)}
                    </small>
                </div>;
        }) : <Empty>Chưa có token được runtime ghi nhận.<br />Chạy công việc để xem mức sử dụng thực tế.</Empty>}
            </div>
        </section>
        <section className="c-card">
            <div className="c-card-head">
                <h2>Việc gần đây</h2>
                <button onClick={() => navigate('workboard')}>Xem hết →</button>
            </div>
            <div className="c-recent-work">
                {runs.length ? runs.slice(-6).reverse().map(run => <button key={run.id} onClick={() => navigate('runs?run=' + encodeURIComponent(run.id))}>
                    <span className="c-resource-icon">◈</span>
                    <span>
                        <strong>
                            {run.input.slice(0, 90) || run.id}
                        </strong>
                        <small>
                            {stamp(run.started_at)}
                        </small>
                    </span>
                    <State value={run.state}/>
                </button>) : <Empty>Chưa có lượt chạy.</Empty>}
            </div>
        </section>
        <section className="c-card">
            <div className="c-card-head">
                <h2>Đội ngũ của bạn <small>
                        {agents.length} bot</small>
                </h2>
                <button onClick={() => navigate('bots')}>Xem tất cả →</button>
            </div>
            <div className="c-bot-grid">
                {agents.length ? agents.map((a, i) => <button className="c-bot-tile" key={a.id} onClick={() => navigate('bots')}>
                    <Avatar agent={a} index={i}/>
                    <strong>
                        {a.name}
                    </strong>
                    <small>
                        {a.role}
                    </small>
                    <State value={a.status}/>
                    <span>
                        {a.brain.provider} · {a.brain.model}
                    </span>
                </button>) : <Empty>Chưa có bot. Tạo một bot trong Agent Studio để bắt đầu.</Empty>}
            </div>
        </section>
        <section className="c-card">
            <div className="c-card-head">
                <h2>Phiên làm việc</h2>
                <button onClick={() => navigate('sessions')}>Mở →</button>
            </div>
            <div className="c-session-summary">
                <strong>
                    {number(o?.runs.active)}
                </strong>
                <span>phiên đang thực thi</span>
            </div>
            <div className="c-summary-row">
                <span>Tổng lượt chạy</span>
                <b>
                    {number(o?.runs.total)}
                </b>
            </div>
            <div className="c-summary-row">
                <span>Chi phí thực tế</span>
                <b>—</b>
            </div>
            <p className="c-muted c-padding">Chưa có dữ liệu hóa đơn provider. Token không đồng nghĩa với chi phí thực tế.</p>
            <button className="c-wide" onClick={() => navigate('room')}>◇ Mở phòng chung</button>
        </section>
        <section className="c-card">
            <div className="c-card-head">
                <h2>Hoạt động gần đây</h2>
                <button onClick={() => navigate('audit')}>Xem hết →</button>
            </div>
            <Feed items={o?.activity?.slice(0, 8) ?? []}/>
        </section>
        <section className="c-card">
            <div className="c-card-head">
                <h2>Dịch vụ nền</h2>
                <button onClick={() => navigate('channels')}>Chi tiết →</button>
            </div>
            <Feed items={o?.services ?? []}/>
        </section>
    </div>
    </>;
}
function Avatar({ agent, index = 0 }: {
    agent: Agent;
    index?: number;
}) {
    return <span className={'c-avatar c-avatar-' + index % 4}>
    {agent.name.slice(0, 2).toUpperCase()}
    <i className={agent.enabled ? '' : 'off'}/>
    </span>;
}
function Chat({ workspaceId, agents, workflows, direct, navigate, eventRevision }: {
    eventRevision: number;
    workspaceId: string;
    agents: Agent[];
    workflows: Workflow[];
    direct: boolean;
    navigate: (p: string) => void;
}) {
    const [conversations, setConversations] = useState<Conversation[]>([]), [selected, setSelected] = useState(''), [detail, setDetail] = useState<Conversation | null>(null), [agent, setAgent] = useState(new URLSearchParams(location.hash.split('?')[1]).get('agent') ?? ''), [workflow, setWorkflow] = useState(''), [content, setContent] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false), [attachment, setAttachment] = useState<{
        id: string;
        name: string;
        preview_url?: string;
        pixel_interpretation?: string;
    }[]>([]), [uploading, setUploading] = useState(''), [runStates, setRunStates] = useState<Record<string, string>>({});
    const requestId = useRef<string | null>(null);
    const selectedRef = useRef(selected);
    selectedRef.current = selected;
    const alive = useRef(true);
    const tail = useRef<HTMLDivElement>(null);
    const scope = '?workspace_id=' + encodeURIComponent(workspaceId);
    useEffect(() => {
        alive.current = true;
        void api<Conversation[]>('/api/console/conversations' + scope).then(data => {
            if (alive.current)
                setConversations(data);
        }).catch(e => {
            if (alive.current)
                setError(String(e));
        });
        return () => { alive.current = false; };
    }, [scope]);
    const load = useCallback(async () => {
        if (!selected)
            return;
        try {
            const [data, sessions] = await Promise.all([api<Conversation>('/api/console/conversations/' + selected + scope), api<Row[]>('/api/console/sessions' + scope)]);
            if (alive.current && selectedRef.current === selected) {
                setDetail(data);
                setRunStates(Object.fromEntries(rows(sessions).map(session => [str(session.run_id ?? session.id), str(session.state, 'unknown')])));
            }
        }
        catch (e) {
            if (alive.current)
                setError(String(e));
        }
    }, [scope, selected]);
    useEffect(() => { setDetail(null); void load(); const timer = setInterval(() => void load(), 2500); return () => clearInterval(timer); }, [load]);
    useEffect(() => { if (!eventRevision)
        return; const timer = setTimeout(() => void load(), 100); return () => clearTimeout(timer); }, [eventRevision, load]);
    useEffect(() => { tail.current?.scrollIntoView?.({
        behavior: 'smooth', block: 'nearest'
    }); }, [detail?.messages?.length]);
    async function send() {
        if (!content.trim() || busy || uploading)
            return;
        if (direct && !agent && !detail?.agent_id) {
            setError('Chọn bot trước khi gửi.');
            return;
        }
        if (!direct && !workflow) {
            setError('Chọn bot hoặc workflow; phòng chung không tự cấp quyền.');
            return;
        }
        setBusy(true);
        setError('');
        try {
            let id = selected;
            if (!id) {
                const c = await api<Conversation>('/api/console/conversations', 'POST', {
                    workspace_id: workspaceId, agent_id: direct ? (agent || null) : null, title: content.trim().slice(0, 80)
                });
                id = c.id;
                if (alive.current) {
                    setConversations(cs => [c, ...cs]);
                    setSelected(id);
                }
            }
            requestId.current ??= crypto.randomUUID();
            await api('/api/console/conversations/' + id + '/messages' + scope, 'POST', {
                content, client_request_id: requestId.current, ...(workflow ? {
                    workflow_id: workflow
                } : {}), attachment_ids: attachment.map(a => a.id)
            });
            requestId.current = null;
            if (alive.current) {
                setContent('');
                setAttachment([]);
                const data = await api<Conversation>('/api/console/conversations/' + id + scope);
                if (alive.current)
                    setDetail(data);
            }
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
    async function upload(file: File) {
        setError('');
        const image = file.type === 'image/png' || /\.png$/i.test(file.name);
        const text = ['text/plain', 'text/csv', 'text/markdown'].includes(file.type) || /\.(txt|csv|md)$/i.test(file.name);
        if (!image && !text) {
            setError('Chỉ hỗ trợ PNG, TXT, CSV và Markdown.');
            return;
        }
        if (file.size > 1048576) {
            setError('Tệp vượt giới hạn 1 MiB.');
            return;
        }
        setUploading(file.name);
        try {
            const payload = image ? {
                workspace_id: workspaceId, name: file.name, media_type: 'image/png',
                content_base64: await new Promise<string>((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(String(reader.result).split(',')[1]);
                    reader.onerror = () => reject(Error('Không đọc được ảnh.'));
                    reader.readAsDataURL(file);
                }),
            } : {
                workspace_id: workspaceId, name: file.name,
                media_type: file.name.endsWith('.csv') ? 'text/csv' : file.name.endsWith('.md') ? 'text/markdown' : 'text/plain',
                content: await file.text(),
            };
            const item = await api<{
                id: string;
                name: string;
                preview_url?: string;
                pixel_interpretation?: string;
            }>('/api/console/attachments' + (image ? '/image' : ''), 'POST', payload);
            if (alive.current)
                setAttachment(items => [...items, item]);
        }
        catch (e) {
            if (alive.current)
                setError(String(e));
        }
        finally {
            if (alive.current)
                setUploading('');
        }
    }
    const list = conversations.filter(c => direct ? c.agent_id !== null && (!agent || c.agent_id === agent) : c.agent_id === null);
    return <div className="c-chat-layout">
    <aside className="c-card c-conversations">
        <button className="c-wide" onClick={() => { setSelected(''); setDetail(null); setContent(''); setAttachment([]); requestId.current = null; }}>＋ Cuộc trò chuyện mới</button>
        {list.map(c => <button className={selected === c.id ? 'selected' : ''} key={c.id} onClick={() => { setSelected(c.id); setAgent(c.agent_id ?? ''); requestId.current = null; }}>
            <span>◇</span>
            <strong>
                {c.title}
            </strong>
        </button>)}
        {!list.length && <p className="c-muted c-padding">Chưa có cuộc trò chuyện.</p>}
    </aside>
    <section className="c-card c-chat">
        <div className="c-chat-tabs">
            <button className={!direct ? 'selected' : ''} onClick={() => navigate('room')}>▤ Phòng chung</button>
            {agents.filter(a => a.enabled).map((a, i) => <button className={agent === a.id ? 'selected' : ''} key={a.id} onClick={() => {
                setAgent(a.id);
                requestId.current = null;
                if (selected && detail?.agent_id !== a.id) {
                    setSelected('');
                    setDetail(null);
                }
            }}>
                <Avatar agent={a} index={i}/>
                {a.name}
            </button>)}
        </div>
        <div className="c-chat-messages">
            {!detail?.messages?.length && <Empty>
                <strong>
                    {direct ? 'Chọn một cộng sự để bắt đầu' : 'Cùng đội AI bắt đầu công việc mới'}
                </strong>
                <br />Tin nhắn tạo công việc và lượt chạy thật. Kết quả chỉ xuất hiện khi runtime trả về.</Empty>}
            {detail?.messages?.map(message => <article className={'c-message ' + message.role} key={message.id}>
                <div className="c-message-author">
                    {message.role === 'user' ? 'Bạn' : message.role === 'assistant' ? 'AgentVerse' : 'Runtime'} <time>
                        {stamp(message.created_at)}
                    </time>
                </div>
                <div className="c-message-body">
                    <SafeMarkdown content={message.content || 'Runtime chưa có nội dung kết quả.'}/>
                </div>
                {message.run_id && <div className="c-run-card">
                    <span>◈ KẾT QUẢ CÔNG VIỆC</span>
                    <State value={runStates[message.run_id] ?? message.state ?? 'unknown'}/>
                    <code>
                        {message.run_id}
                    </code>
                    {message.error && <p className="c-error">
                        {message.error}
                    </p>}
                    {['running', 'queued', 'waiting_approval', 'waiting_review'].includes(runStates[message.run_id] ?? message.state ?? '') && <button disabled={busy} onClick={() => { void api('/api/runs/' + message.run_id + '/cancel', 'POST').then(load).catch(e => setError(String(e))); }}>Hủy lượt chạy</button>}
                    {message.artifacts?.map((artifact, i) => <details key={i}>
                        <summary>Artifact · {str(artifact.filename ?? artifact.id)}
                        </summary>
                        {typeof artifact.id === 'string' && message.run_id && <ArtifactPreview runId={message.run_id} artifactId={artifact.id}/>}
                    </details>)}
                    <button onClick={() => navigate('runs?run=' + encodeURIComponent(message.run_id ?? ''))}>Mở Run Monitor ↗</button>
                    <button onClick={() => navigate('workboard?item=' + encodeURIComponent(message.work_item_id ?? ''))}>Mở việc ↗</button>
                </div>}
            </article>)}
            <div ref={tail}/>
        </div>
        <div className="c-composer">
            {error && <p className="c-error" role="alert">
                {error}
            </p>}
            <div className="c-quick-prompts">
                {['Lập kế hoạch nghiên cứu có nguồn', 'Phân tích dữ liệu CSV', 'Soạn nội dung và đề nghị review'].map(prompt => <button key={prompt} onClick={() => { setContent(prompt); requestId.current = null; }}>
                    {prompt}
                </button>)}
            </div>
            <div className="c-composer-controls">
                <select disabled={busy} aria-label="Bot thực thi" value={agent} onChange={e => { setAgent(e.target.value); setSelected(''); setDetail(null); requestId.current = null; }}>
                    <option value="">Chọn bot</option>
                    {agents.filter(a => a.enabled).map(a => <option value={a.id} key={a.id}>
                        {a.name} · {a.brain.provider}
                    </option>)}
                </select>
                <select aria-label="Workflow trò chuyện" value={workflow} onChange={e => { setWorkflow(e.target.value); requestId.current = null; }}>
                    <option value="">Workflow một agent</option>
                    {workflows.map(w => <option value={w.id} key={w.id}>
                        {w.name}
                    </option>)}
                </select>
            </div>
            <textarea aria-label="Tin nhắn" placeholder="Giao một nhiệm vụ… gõ @ để chọn bot" value={content} onChange={e => { setContent(e.target.value); requestId.current = null; }} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
            }
        }} rows={3}/>
            {/@[^\s]*$/.test(content) && <div className="c-mentions">
                {agents.filter(a => a.enabled && a.name.toLowerCase().includes(content.split('@').pop()!.toLowerCase())).map(a => <button key={a.id} onClick={() => {
                    setContent(text => text.replace(/@[^\s]*$/, '@' + a.name + ' '));
                    setAgent(a.id);
                    if (direct && detail?.agent_id !== a.id) {
                        setSelected('');
                        setDetail(null);
                    }
                    if (!direct) {
                        const match = workflows.find(w => w.graph?.nodes.some(n => n.agent_id === a.id));
                        if (match)
                            setWorkflow(match.id);
                        else
                            setError('Bot này chưa có workflow đã lưu cho phòng chung. Chọn workflow hoặc dùng chat riêng.');
                    }
                    requestId.current = null;
                }}>@{a.name}
                </button>)}
            </div>}
            {uploading && <p role="status">Đang kiểm tra và tải: {uploading}
            </p>}
            {attachment.map(a => <div className="c-image-attachment" key={a.id}>
                {a.preview_url?.startsWith('/api/console/attachments/') && <img src={a.preview_url} alt={'Ảnh đính kèm ' + a.name}/>}
                <button onClick={() => setAttachment(xs => xs.filter(x => x.id !== a.id))}>▱ {a.name} ×</button>
                {a.pixel_interpretation === 'unsupported' && <small>Đã lưu ảnh. Agent chỉ nhận metadata; chưa có adapter đọc nội dung pixel.</small>}
            </div>)}
            <div className="c-composer-bottom">
                <label className="c-file">＋ Đính kèm<input aria-label="Đính kèm tệp" type="file" disabled={!!uploading} accept=".png,.txt,.csv,.md,image/png,text/plain,text/csv,text/markdown" onChange={e => {
            if (e.target.files?.[0])
                void upload(e.target.files[0]);
            e.target.value = '';
        }}/>
                </label>
                <VoiceDraft onTranscript={text => { setContent(previous => previous ? previous + '\n' + text : text); requestId.current = null; }}/>
                <small>Enter gửi · Shift Enter xuống dòng</small>
                <button className="c-primary" disabled={busy || !!uploading || !content.trim()} onClick={() => void send()}>
                    {busy ? 'Đang gửi…' : 'Gửi ↑'}
                </button>
            </div>
        </div>
    </section>
    </div>;
}
function Bots({ workspaceId, agents, navigate, onRefresh }: {
    workspaceId: string;
    agents: Agent[];
    navigate: (p: string) => void;
    onRefresh: () => Promise<void>;
}) {
    const [id, setId] = useState(new URLSearchParams(location.hash.split('?')[1]).get('agent') ?? agents[0]?.id ?? ''), [tab, setTab] = useState('Tổng quan'), [soul, setSoul] = useState<{
        content: string;
        revision: number;
    } | null>(null), [editing, setEditing] = useState(false), [text, setText] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState('');
    const agent = agents.find(a => a.id === id) ?? agents[0];
    useEffect(() => {
        if (!agent)
            return;
        let active = true;
        setSoul(null);
        setError('');
        setEditing(false);
        api<{
            content: string;
            revision: number;
        }>('/api/console/agents/' + agent.id + '/soul?workspace_id=' + encodeURIComponent(workspaceId)).then(data => {
            if (active) {
                setSoul(data);
                setText(data.content);
            }
        }).catch(e => {
            if (active)
                setError(String(e));
        });
        return () => { active = false; };
    }, [agent?.id, workspaceId]);
    if (!agent)
        return <Empty>Chưa có bot. <button onClick={() => navigate('agents')}>Tạo bot trong Agent Studio</button>
        </Empty>;
    return <div className="c-bots-layout">
    <aside className="c-card c-bots-list">
        <div className="c-card-head">
            <h2>Đội ngũ <small>
                    {agents.length}
                </small>
            </h2>
        </div>
        {agents.map((a, i) => <button key={a.id} className={a.id === agent.id ? 'selected' : ''} onClick={() => { setId(a.id); setNotice(''); }}>
            <Avatar agent={a} index={i}/>
            <span>
                <strong>
                    {a.name}
                </strong>
                <small>
                    {a.role}
                </small>
            </span>
            <i className={'c-status-dot ' + a.status}/>
        </button>)}
        <button className="c-wide" onClick={() => navigate('agents')}>＋ Quản lý cấu hình bot</button>
    </aside>
    <section className="c-card c-bot-detail">
        <div className="c-profile-head">
            <Avatar agent={agent}/>
            <div>
                <h2>
                    {agent.name} <State value={agent.status}/>
                </h2>
                <p>
                    {agent.role}
                </p>
                <small>
                    {agent.brain.provider} · {agent.execution?.engine ?? 'native'}
                </small>
            </div>
            <button className="c-primary" onClick={() => navigate('chat?agent=' + encodeURIComponent(agent.id))}>◇ Chat với bot</button>
        </div>
        <div className="c-tabs">
            {['Tổng quan', 'SOUL', 'Skills', 'Memory', 'Việc', 'Hoạt động', 'Kênh', 'Cron', 'Cấu hình'].map(t => <button className={tab === t ? 'selected' : ''} key={t} onClick={() => setTab(t)}>
                {t}
            </button>)}
        </div>
        {error && <p className="c-banner c-error" role="alert">
            {error}
        </p>}
        {notice && <p className="c-banner" role="status">
            {notice}
        </p>}
        <div className="c-profile-body">
            {tab === 'Tổng quan' && <>
                <h3>Hồ sơ thực thi</h3>
                <div className="c-profile-facts">
                    {[['Vai trò', agent.role], ['Engine', agent.execution?.engine ?? 'native'], ['Provider', agent.brain.provider], ['Model', agent.brain.model], ['Memory policy', agent.memory_policy], ['Trạng thái', agent.enabled ? 'Đang bật' : 'Đã tắt'], ['Skill được gán', agent.skills.length], ['Tool grants', agent.tool_grants?.length ?? agent.tools.length]].map(([label, value]) => <div key={String(label)}>
                        <span>
                            {label}
                        </span>
                        <strong>
                            {str(value)}
                        </strong>
                    </div>)}
                </div>
                <h3>Chỉ dẫn hệ thống</h3>
                <pre>
                    {soul?.content ?? agent.system_prompt}
                </pre>
                <p className="c-muted">Usage và phiên thực thi nằm trong mục theo dõi; không suy đoán PID, gateway hoặc hóa đơn từ cấu hình.</p>
            </>}
            {tab === 'SOUL' && <>
                <div className="c-card-head">
                    <h3>SOUL.md <small>revision {soul?.revision ?? '—'}
                        </small>
                    </h3>
                    <button disabled={!soul} onClick={() => setEditing(v => !v)}>
                        {editing ? 'Hủy sửa' : 'Sửa SOUL'}
                    </button>
                </div>
                {editing ? <>
                    <textarea aria-label="Nội dung SOUL" className="c-soul-editor" value={text} onChange={e => setText(e.target.value)}/>
                    <button className="c-primary" onClick={() => {
                    void api<{
                        content: string;
                        revision: number;
                    }>('/api/console/agents/' + agent.id + '/soul?workspace_id=' + encodeURIComponent(workspaceId), 'PATCH', {
                        content: text, revision: soul?.revision
                    }).then(data => { setSoul(data); void onRefresh(); setEditing(false); setNotice('Đã lưu. Chỉ các lượt chạy mới dùng revision này.'); }).catch(e => setError(String(e)));
                }}>Lưu revision mới</button>
                </> : <pre>
                    {soul?.content ?? 'Đang tải SOUL…'}
                </pre>}
                <p className="c-muted">Thay đổi không ghi đè snapshot của lượt chạy đang thực thi.</p>
                <RevisionHistory workspaceId={workspaceId} agentId={agent.id} kind="soul" currentRevision={soul?.revision} currentContent={soul?.content} onRestored={() => {
                void api<{
                    content: string;
                    revision: number;
                }>('/api/console/agents/' + agent.id + '/soul?workspace_id=' + encodeURIComponent(workspaceId)).then(d => { setSoul(d); setText(d.content); void onRefresh(); }).catch(e => setError(String(e)));
            }}/>
            </>}
            {tab === 'Skills' && <Skills key={agent.id} workspaceId={workspaceId} agents={[agent]}/>}
            {tab === 'Memory' && <MemoryManager workspaceId={workspaceId} agentId={agent.id}/>}
            {tab === 'Việc' && <button onClick={() => navigate('workboard?agent=' + encodeURIComponent(agent.id))}>Mở công việc và duyệt kết quả →</button>}
            {tab === 'Hoạt động' && <Resources route="sessions" workspaceId={workspaceId} navigate={navigate} agentId={agent.id}/>}
            {tab === 'Kênh' && <Resources route="channels" workspaceId={workspaceId} navigate={navigate} agentId={agent.id}/>}
            {tab === 'Cron' && <Resources route="schedules" workspaceId={workspaceId} navigate={navigate} agentId={agent.id}/>}
            {tab === 'Cấu hình' && <>
                <pre>
                    {pretty(agent)}
                </pre>
                <RevisionHistory workspaceId={workspaceId} agentId={agent.id} kind="config" currentRevision={agent.agent_config_revision ?? 1} currentContent={Object.fromEntries(Object.entries(agent).filter(([key]) => ['workspace_id', 'name', 'role', 'system_prompt', 'brain', 'skin', 'skills', 'tools', 'memory_policy', 'workstation', 'enabled', 'execution', 'role_config', 'skill_bindings', 'tool_grants', 'memory_config', 'appearance'].includes(key)))} onRestored={() => void onRefresh()}/>
                <button onClick={() => navigate('agents')}>Sửa trong Agent Studio →</button>
            </>}
        </div>
    </section>
    </div>;
}
function Skills({ workspaceId, agents }: {
    workspaceId: string;
    agents: Agent[];
}) {
    const [data, setData] = useState<Row>({}), [agent, setAgent] = useState(agents[0]?.id ?? ''), [query, setQuery] = useState(''), [error, setError] = useState(''), [preview, setPreview] = useState<Row | null>(null), [busy, setBusy] = useState(false), [notice, setNotice] = useState('');
    const load = useCallback(async () => { const d = await api<Row>('/api/console/skills?workspace_id=' + encodeURIComponent(workspaceId) + (agent ? '&agent_id=' + encodeURIComponent(agent) : '')); setData(d); }, [workspaceId, agent]);
    useEffect(() => {
        let active = true;
        void load().catch(e => {
            if (active)
                setError(String(e));
        });
        setPreview(null);
        return () => { active = false; };
    }, [load]);
    async function plan(packageId: string, operation: string) {
        setError('');
        setNotice('');
        setBusy(true);
        try {
            setPreview(await api<Row>('/api/console/agents/' + agent + '/skills/preview?workspace_id=' + encodeURIComponent(workspaceId), 'POST', {
                package_id: packageId, operation
            }));
        }
        catch (e) {
            setError(String(e));
        }
        finally {
            setBusy(false);
        }
    }
    const packages = rows(data.packages);
    return <section className="c-card">
    <div className="c-card-head">
        <h2>Skill packages</h2>
        <select aria-label="Bot quản lý skill" value={agent} onChange={e => setAgent(e.target.value)}>
            {agents.map(a => <option key={a.id} value={a.id}>
                {a.name}
            </option>)}
        </select>
        <input aria-label="Tìm skill" placeholder="Tìm skill…" value={query} onChange={e => setQuery(e.target.value)}/>
    </div>
    <div className="c-banner">Chỉ package khai báo đã được duyệt. Xem manifest và diff trước khi áp dụng; không chạy script cài đặt hoặc tự cấp tool.</div>
    {error && <p role="alert" className="c-error c-padding">
        {error}
    </p>}
    {notice && <p role="status" className="c-banner">
        {notice}
    </p>}
    <div className="c-skill-grid">
        {packages.filter(p => str(p.id).toLowerCase().includes(query.toLowerCase())).map(p => <article className="c-skill" key={str(p.id)}>
            <div className="c-skill-icon">▧</div>
            <h3>
                {str(p.name ?? p.id)}
            </h3>
            <small>v{str(p.version)} · {str(p.license)}
            </small>
            <p>
                {str(p.description, 'Skill khai báo từ registry cục bộ')}
            </p>
            <details>
                <summary>Manifest và quyền</summary>
                <pre>
                    {pretty(p)}
                </pre>
            </details>
            <div className="c-actions">
                {['install', 'update', 'remove'].map((operation, i) => <button disabled={busy || !agent} key={operation} onClick={() => void plan(str(p.id), operation)}>
                    {['Cài đặt', 'Cập nhật', 'Gỡ'][i]}
                </button>)}
            </div>
        </article>)}
    </div>
    {!packages.length && <Empty>Registry chưa có package phù hợp.</Empty>}
    <details className="c-padding">
        <summary>Bindings đang kích hoạt</summary>
        <pre>
            {pretty(data.bindings ?? [])}
        </pre>
    </details>
    {preview && <div className="c-review">
        <h3>Xác nhận thay đổi skill</h3>
        <pre>
            {pretty(preview)}
        </pre>
        <button onClick={() => setPreview(null)}>Hủy</button>
        <button className="c-primary" disabled={busy} onClick={() => { setBusy(true); void api('/api/console/agents/' + agent + '/skills/apply?workspace_id=' + encodeURIComponent(workspaceId), 'POST', {
            approval_id: preview.approval_id
        }).then(async () => { setPreview(null); setNotice('Đã áp dụng payload được duyệt.'); await load(); }).catch(e => setError(String(e))).finally(() => setBusy(false)); }}>Áp dụng đúng manifest này</button>
    </div>}
    </section>;
}
function Resources({ route, workspaceId, navigate, agentId }: {
    route: string;
    workspaceId: string;
    navigate: (p: string) => void;
    agentId?: string;
}) {
    const [data, setData] = useState<unknown>(null), [error, setError] = useState(''), [period, setPeriod] = useState('30'), [search, setSearch] = useState(''), [busy, setBusy] = useState(false);
    const endpoint = route === 'channels' ? 'health' : route === 'logs' || route === 'audit' ? 'logs' : route;
    const load = useCallback(async () => {
        setBusy(true);
        try {
            const result = await api('/api/console/' + endpoint + '?workspace_id=' + encodeURIComponent(workspaceId) + (route === 'usage' ? '&period=' + period : '') + (route === 'logs' || route === 'audit' ? '&kind=' + (route === 'logs' ? 'system' : 'audit') : ''));
            setData(result);
            setError('');
        }
        catch (e) {
            setError(String(e));
        }
        finally {
            setBusy(false);
        }
    }, [endpoint, workspaceId, route, period]);
    useEffect(() => { void load(); const timer = setInterval(() => void load(), 15000); return () => clearInterval(timer); }, [load]);
    const object = (data && typeof data === 'object' && !Array.isArray(data) ? data : {}) as Row;
    const items = Array.isArray(data) ? rows(data) : rows(object.items);
    const scoped = agentId ? items.filter(item => item.agent_id === agentId || (Array.isArray(item.agent_ids) && item.agent_ids.includes(agentId)) || (route === 'channels' && !item.agent_id)) : items;
    const filtered = scoped.filter(item => pretty(item).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
    return <section className={'c-card c-resource c-resource-' + route}>
    <div className="c-card-head">
        <h2>
            {route === 'usage' ? 'Mức sử dụng runtime' : route === 'topology' ? 'Sơ đồ toàn hệ thống' : route === 'schedules' ? 'Lịch chạy · chỉ theo dõi' : route === 'inbox' ? 'Các quyết định đang chờ' : 'Dữ liệu từ backend'}
        </h2>
        {route === 'usage' ? <div className="c-periods">
            {['7', '30', '90', 'all'].map(p => <button key={p} className={period === p ? 'selected' : ''} onClick={() => setPeriod(p)}>
                {p === 'all' ? 'Tất cả' : p + ' ngày'}
            </button>)}
        </div> : <input aria-label="Tìm dữ liệu" placeholder="Tìm theo tên, trạng thái, nội dung…" value={search} onChange={e => setSearch(e.target.value)}/>}
        <button disabled={busy} onClick={() => void load()}>↻ Làm mới</button>
    </div>
    {error && <p role="alert" className="c-error c-padding">
        {error}
    </p>}
    {data === null && !error && <Empty>Đang tải dữ liệu…</Empty>}
 {agentId && route === 'channels' && <p className="c-banner">Kênh của bot này và các dịch vụ dùng chung của workspace.</p>}
    {(route === 'logs' || route === 'audit') && <div className="c-padding">
        <LogExport workspaceId={workspaceId} kind={route === 'logs' ? 'system' : 'audit'}/>
    </div>}
    {route === 'usage' && data !== null && <>
        <Budget workspaceId={workspaceId}/>
        <div className="c-stats c-padding">
            {[['Chi phí thực tế', (object.totals as Row)?.actual_cost], ['Lượt gọi', (object.totals as Row)?.requests], ['Input token', (object.totals as Row)?.input_tokens], ['Output token', (object.totals as Row)?.output_tokens]].map(([label, value]) => <div className="c-stat" key={String(label)}>
                <span>
                    {str(label)}
                </span>
                <strong>
                    {number(value)}
                </strong>
                <small>
                    {label === 'Chi phí thực tế' ? 'Chưa kết nối hóa đơn provider' : accountingLabel((object.totals as Row)?.token_accounting)}
                </small>
            </div>)}
        </div>
        <p className="c-banner">Số liệu chỉ phản ánh usage đã ghi nhận. Giá ước tính và hóa đơn thực tế không được thay thế cho nhau; thiếu dữ liệu hiển thị “—”.</p>
        <div className="c-padding">
            <TokenAccounting value={object.totals as Row}/>
            <h3>Token theo ngày</h3>
            <div className="c-bar-chart">
                {rows(object.daily).length ? rows(object.daily).map((d, i) => {
                const value = Number(d.total_tokens ?? 0);
                const max = Math.max(...rows(object.daily).map(x => Number(x.total_tokens ?? 0)), 1);
                return <div key={i} title={pretty(d)}>
                    <span style={{
                    height: Math.max(2, value / max * 135) + 'px'
                }}/>
                    <small>
                        {str(d.date ?? d.day)}
                    </small>
                </div>;
            }) : <Empty>Chưa có usage theo ngày.</Empty>}
            </div>
            <h3>Theo bot</h3>
            {rows(object.by_agent).map(row => <div key={str(row.id)} className="c-padding">
                <strong>
                    {str(row.agent_id)}
                </strong>
                <TokenAccounting value={row}/>
                <span>
                    {number(row.total_tokens)} token</span>
            </div>)}
            <h3>Theo model</h3>
            {rows(object.by_model).map(row => <div key={str(row.id)} className="c-padding">
                <strong>
                    {str(row.model)}
                </strong>
                <TokenAccounting value={row}/>
                <span>
                    {number(row.total_tokens)} token</span>
            </div>)}
        </div>
    </>}
 {route === 'topology' && data !== null && <ConsoleTopology nodes={rows(object.nodes)} edges={rows(object.edges)} search={search}/>}
 {route === 'schedules' && <p className="c-banner">
        {str((object.capability as Row)?.reason, 'Chỉ giám sát lịch đã được adapter ghi nhận. Console không tạo, sửa hoặc bật/tắt lịch. Không có lịch không đồng nghĩa scheduler đang hoạt động.')}
    </p>}
 {!['usage', 'topology'].includes(route) && data !== null && <>
        {filtered.length ? <div className="c-resource-list">
            {filtered.map((item, i) => <article className="c-resource-row" key={str(item.id, String(i))}>
                <div className="c-resource-icon">
                    {route === 'inbox' ? '◉' : route === 'channels' ? '⌁' : '◴'}
                </div>
                <div>
                    <strong>
                        {str(item.title ?? item.name ?? item.action ?? item.event_type ?? item.id, 'Bản ghi')}
                    </strong>
                    <p>
                        {str(item.reason ?? item.message ?? item.summary ?? item.input, '')}
                    </p>
                    <small>
                        {stamp(item.created_at ?? item.started_at ?? item.observed_at)}
                        {item.agent_id ? ' · ' + str(item.agent_id) : ''}
                    </small>
                </div>
                <State value={item.state ?? item.status ?? item.kind}/>
                {(route === 'sessions' || route === 'inbox') && <button onClick={() => navigate(item.work_item_id ? 'workboard?item=' + encodeURIComponent(str(item.work_item_id, '')) : 'runs?run=' + encodeURIComponent(str(item.run_id ?? item.id, '')))}>
                    {route === 'inbox' ? 'Xem & quyết định' : 'Mở phiên'} ↗</button>}
                <details>
                    <summary>Chi tiết</summary>
                    <pre>
                        {pretty(item)}
                    </pre>
                </details>
            </article>)}
        </div> : <Empty>
            {route === 'inbox' ? 'Không có quyết định nào đang chờ.' : route === 'schedules' ? 'Chưa có lịch được adapter ghi nhận.' : 'Chưa có bản ghi phù hợp.'}
        </Empty>}
        {(route === 'audit' || route === 'logs') && object.next_cursor != null && <button className="c-wide" onClick={() => { void api<Row>('/api/console/logs?workspace_id=' + encodeURIComponent(workspaceId) + '&kind=' + (route === 'logs' ? 'system' : 'audit') + '&before=' + encodeURIComponent(str(object.next_cursor))).then(next => setData({
            ...next, items: [...items, ...rows(next.items)]
        })).catch(e => setError(String(e))); }}>Tải thêm bản ghi</button>}
    </>}
 </section>;
}
function PreferencesPanel({ preferences: p, save, navigate }: {
    preferences: Preferences;
    save: (p: Preferences) => Promise<void>;
    navigate: (p: string) => void;
}) {
    const [draft, setDraft] = useState(p);
    const controls: [
        keyof Preferences,
        string,
        string[][]
    ][] = [['theme', 'Giao diện', [['dark', 'Tối'], ['light', 'Sáng'], ['system', 'Theo hệ thống']]], ['accent', 'Màu nhấn', [['blue', 'Xanh'], ['black', 'Đen']]], ['sidebar', 'Thanh điều hướng', [['full', 'Đầy đủ'], ['collapsed', 'Thu gọn']]], ['font', 'Cỡ chữ', [['small', 'Nhỏ'], ['medium', 'Vừa'], ['large', 'Lớn']]], ['density', 'Mật độ', [['comfortable', 'Thoáng'], ['compact', 'Gọn']]], ['refresh', 'Tự làm mới', [['fast', 'Nhanh · 5 giây'], ['slow', 'Chậm · 15 giây'], ['off', 'Tắt']]], ['start_page', 'Trang khởi động', links.filter(x => x[0] !== 'office').map(x => [x[0], x[2]])]];
    return <div className="c-settings-layout">
    <section className="c-card">
        <div className="c-card-head">
            <h2>Cá nhân hóa console</h2>
            <small>revision {p.revision ?? '—'}
            </small>
        </div>
        {controls.map(([key, label, options]) => <div className="c-setting" key={key}>
            <label htmlFor={'pref-' + key}>
                {label}
            </label>
            <select id={'pref-' + key} value={str(draft[key])} onChange={e => setDraft({
            ...draft, [key]: e.target.value
        })}>
                {options.map(([value, text]) => <option key={value} value={value}>
                    {text}
                </option>)}
            </select>
        </div>)}
        <div className="c-setting">
            <label htmlFor="pref-office">Văn phòng AI · Habblaud 2D</label>
            <input id="pref-office" type="checkbox" checked={draft.office_enabled} onChange={e => setDraft({
        ...draft, office_enabled: e.target.checked
    })}/>
        </div>
        <div className="c-padding">
            <button className="c-primary" disabled={p.revision == null || draft.revision !== p.revision} onClick={() => void save({
        ...draft, revision: p.revision
    })}>Lưu cài đặt</button>
            <button onClick={() => setDraft(p)}>Khôi phục đã lưu</button>
        </div>
    </section>
    <aside className="c-card c-padding">
        <h2>Kết nối & quyền thực thi</h2>
        <p className="c-muted">Console giữ nguyên runtime Native/Harness, quyền công cụ và các cổng phê duyệt. Cấu hình hiển thị không thay đổi quyền của agent.</p>
        <button className="c-wide" onClick={() => navigate('settings')}>Cấu hình provider & kiểm tra kết nối ↗</button>
        <button className="c-wide" onClick={() => navigate('channels')}>Trạng thái gateway, adapter & secret ↗</button>
        <button className="c-wide" onClick={() => navigate('agents')}>Agent Studio · role, tool, memory ↗</button>
        <h3>Phạm vi hiện tại</h3>
        <p className="c-muted">Localhost, một người dùng. CRM triển khai sau. Văn phòng là view 2D hiện có; không có chế độ 3D giả lập.</p>
    </aside>
    </div>;
}
function MemoryPage({ workspaceId, agents }: {
    workspaceId: string;
    agents: Agent[];
}) {
    const [agentId, setAgentId] = useState('');
    return <section className="c-card c-padding">
    <div className="c-card-head">
        <h2>Memory store · notes & user context</h2>
        <select aria-label="Chọn bộ nhớ bot" value={agentId} onChange={e => setAgentId(e.target.value)}>
            <option value="">Workspace · dùng chung</option>
            {agents.map(a => <option key={a.id} value={a.id}>
                {a.name}
            </option>)}
        </select>
    </div>
    <p className="c-muted c-padding">Tài liệu logic MEMORY/USER được ánh xạ thành các note có scope, owner và provenance; không giả định file hệ thống Hermes.</p>
    <MemoryManager workspaceId={workspaceId} agentId={agentId || undefined}/>
    </section>;
}
