import {useEffect,useState} from 'react';
import {api} from './api';
import type {Agent,Graph,WorkflowTemplate} from './types';
export function templateGraph(template:WorkflowTemplate,mapping:Record<string,string>,agents:Agent[]):Graph {
 for(const role of template.roles)if(!agents.some(a=>a.id===mapping[role]&&a.enabled))throw Error('Chọn agent đang bật cho mọi vai trò');
 const nodes:Graph['nodes']=[{id:'start',type:'start',position:{x:0,y:100}},...template.steps.map((step,i)=>({id:'step-'+i,type:'agent' as const,agent_id:mapping[step.role],instructions:step.instructions,...(step.deliverable?{deliverable:step.deliverable}:{}),position:{x:(i+1)*220,y:100}})),{id:'end',type:'end',position:{x:(template.steps.length+1)*220,y:100}}];
 return {nodes,edges:nodes.slice(1).map((node,i)=>({source:nodes[i].id,target:node.id}))};
}
export function WorkflowTemplates({agents,onCreate}:{agents:Agent[];onCreate:(name:string,graph:Graph)=>Promise<void>}){
 const [templates,setTemplates]=useState<WorkflowTemplate[]>([]),[selected,setSelected]=useState(''),[mapping,setMapping]=useState<Record<string,string>>({}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;api<WorkflowTemplate[]>('/api/workflow-templates').then(data=>{if(active){setTemplates(data);setSelected(data[0]?.id??'')}}).catch(e=>{if(active)setError(String(e))});return()=>{active=false}},[]);
 const template=templates.find(t=>t.id===selected);
 const missingGrant=template?.steps.filter(s=>s.deliverable&&!agents.find(a=>a.id===mapping[s.role])?.tool_grants?.some(t=>t.id==='artifacts.write_text'&&t.allow));
 return <section className="card form-card"><h3>Workflow theo vai trò</h3><p className="muted">Dùng tài liệu nguồn được cung cấp trong workspace. Template không tự nghiên cứu web, gửi hoặc xuất bản nội dung.</p><label>Template<select aria-label="Workflow template" value={selected} onChange={e=>{setSelected(e.target.value);setMapping({})}}>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>{template&&<><p>{template.description}</p>{template.roles.map(role=><label key={role}>Vai trò {role}<select aria-label={'Template role '+role} value={mapping[role]??''} onChange={e=>setMapping({...mapping,[role]:e.target.value})}><option value="">Chọn agent hiện có</option>{agents.filter(a=>a.enabled).map(a=><option value={a.id} key={a.id}>{a.name} · {a.role}</option>)}</select></label>)}{!!missingGrant?.length&&<p role="status">Agent chưa có grant artifacts.write_text cho một số file kết quả. Tạo workflow không tự thay đổi quyền hoặc vai trò; hãy cấu hình grant trước khi chạy.</p>}<button disabled={busy} onClick={async()=>{setError('');setBusy(true);try{await onCreate(template.name,templateGraph(template,mapping,agents))}catch(e){setError(String(e))}finally{setBusy(false)}}}>Tạo workflow từ template</button></>}{error&&<p className="error" role="alert">{error}</p>}</section>
}
