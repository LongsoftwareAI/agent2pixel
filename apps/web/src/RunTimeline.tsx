import {useEffect,useState} from 'react';
import {api,pretty} from './api';
import type {Agent,RuntimeEvent} from './types';
type Props={workspaceId:string;runId:string;agents:Agent[];liveEvents:RuntimeEvent[]};
export function RunTimeline(props:Props){return <ScopedTimeline key={props.workspaceId+':'+props.runId} {...props}/>}
function ScopedTimeline({workspaceId,runId,agents,liveEvents}:Props){
 const [events,setEvents]=useState<RuntimeEvent[]>([]),[filter,setFilter]=useState(''),[error,setError]=useState('');
 const belongs=(event:RuntimeEvent)=>event.workspace_id===workspaceId&&event.run_id===runId;
 const merge=(previous:RuntimeEvent[],incoming:RuntimeEvent[])=>Array.from(new Map([...previous,...incoming.filter(belongs)].map(event=>[event.id,event])).values()).sort((a,b)=>a.seq-b.seq);
 useEffect(()=>{let active=true;const load=()=>api<RuntimeEvent[]>('/api/runs/'+encodeURIComponent(runId)+'/events').then(rows=>{if(active){setEvents(previous=>merge(previous,rows));setError('')}}).catch(e=>{if(active)setError(String(e))});void load();const timer=setInterval(load,3000);return()=>{active=false;clearInterval(timer)}},[workspaceId,runId]);
 useEffect(()=>{setEvents(previous=>merge(previous,liveEvents))},[liveEvents,workspaceId,runId]);
 return <section><h3>Event timeline</h3><p className="muted">Lịch sử bền vững của run kết hợp sự kiện trực tiếp. Chi phí không quan sát được hiển thị là chưa biết.</p>{error&&<p className="error" role="alert">Không tải được lịch sử event: {error}</p>}<select aria-label="Lọc event theo agent" value={filter} onChange={e=>setFilter(e.target.value)}><option value="">Mọi agent</option>{agents.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select>{events.filter(e=>!filter||e.agent_id===filter).map(e=><details key={e.id}><summary>#{e.seq} · {e.event_type}</summary><p>Thời gian quan sát: {typeof e.payload.duration_ms==='number'?e.payload.duration_ms+' ms':'chưa biết'} · Token: {e.payload.tokens==null?'chưa biết':String(e.payload.tokens)} · Chi phí: {e.payload.cost==null?'chưa biết':String(e.payload.cost)}</p><pre>{pretty(e.payload)}</pre></details>)}{!events.length&&!error&&<p>Chưa có sự kiện của run này.</p>}</section>
}
