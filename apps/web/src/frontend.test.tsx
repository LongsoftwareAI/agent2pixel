vi.mock('./office/OfficeCanvas',()=>({OfficeCanvas:()=> <div data-testid="office"/>}));
import {afterEach,describe,it,expect,vi} from 'vitest';import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';import {AgentForm,newAgent} from './AgentForm';import {api} from './api';import {validateGraph} from './WorkflowEditor';import {useStore} from './store';
afterEach(()=>{cleanup();vi.unstubAllGlobals()});
describe('Agent Studio',()=>{
it('saves provider, role and skills from the actual form',async()=>{const save=vi.fn().mockResolvedValue(undefined);render(<AgentForm agent={newAgent('workspace')} runs={[]} onSave={save} onDelete={vi.fn()}/>);fireEvent.change(screen.getByLabelText('Tên agent'),{target:{value:'Planner'}});fireEvent.change(screen.getByLabelText('Vai trò'),{target:{value:'Researcher'}});fireEvent.change(screen.getByLabelText('Skills (phân cách bằng dấu phẩy)'),{target:{value:'planning, review'}});fireEvent.click(screen.getByText('Lưu agent'));await waitFor(()=>expect(save).toHaveBeenCalledWith(expect.objectContaining({name:'Planner',role:'Researcher',skills:['planning','review']})))});
it('shows backend failure without reporting saved',async()=>{const agent={...newAgent('workspace'),name:'Planner'};render(<AgentForm agent={agent} runs={[]} onSave={vi.fn().mockRejectedValue(Error('Provider rejected'))} onDelete={vi.fn()}/>);fireEvent.click(screen.getByText('Lưu agent'));await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Provider rejected'))});
});
describe('workflow guard',()=>{it('accepts start agent end',()=>expect(validateGraph({nodes:[{id:'s',type:'start'},{id:'a',type:'agent',agent_id:'a1'},{id:'e',type:'end'}],edges:[{source:'s',target:'a'},{source:'a',target:'e'}]})).toEqual([]));it('rejects missing brain node assignment and end',()=>expect(validateGraph({nodes:[{id:'a',type:'agent'}],edges:[]})).toHaveLength(3))});
describe('API',()=>{it('returns persisted response',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({id:'saved'})}));expect(await api('/api/agents','POST',{name:'Planner'})).toEqual({id:'saved'})});it('surfaces denied policy error',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:'Access denied'})}));await expect(api('/api/documents')).rejects.toThrow('Access denied')})});
describe('event replay',()=>{it('deduplicates and orders backend seq',()=>{useStore.setState({events:[]});const event={id:'e',seq:2,schema_version:1 as const,workspace_id:'w',run_id:null,agent_id:null,event_type:'task.started',payload:{},created_at:''};useStore.getState().receive(event);useStore.getState().receive(event);useStore.getState().receive({...event,id:'e1',seq:1});expect(useStore.getState().events.map(e=>e.seq)).toEqual([1,2])});it('workspace switch clears state and marks disconnected',()=>{useStore.getState().setConnected(true);useStore.getState().setWorkspace('other');expect(useStore.getState().events).toEqual([]);expect(useStore.getState().connected).toBe(false)})});

describe('rapid workspace switching',()=>{
it('rejects a deferred old snapshot and old socket after the new room loads',async()=>{
 const {default:App}=await import('./App');
 const workspaces=[{id:'a',name:'Coding',root_path:'/a',created_at:''},{id:'b',name:'Research',root_path:'/b',created_at:''}];
 let resolveA!:(value:unknown)=>void;const delayed=new Promise(resolve=>{resolveA=resolve});
 const bootstrap=(id:string,name:string)=>({workspaces,agents:[{...newAgent(id),id:id+'-agent',name}],workflows:[],room:null,assets:[],runs:[]});
 vi.stubGlobal('fetch',vi.fn(async(path:string)=>({ok:true,json:async()=>path==='/api/workspaces'?workspaces:path.includes('workspace_id=a')?delayed:bootstrap('b','Fresh Research Agent')})));
 const sockets:{onmessage:((event:{data:string})=>void)|null;onopen:(()=>void)|null;onclose:(()=>void)|null}[]=[];
 class FakeSocket{onmessage=null;onopen=null;onclose=null;onerror=null;constructor(){sockets.push(this)}close(){}}
 vi.stubGlobal('WebSocket',FakeSocket);useStore.setState({workspaceId:'a',events:[],connected:false});
 render(<App/>);await waitFor(()=>expect(sockets.length).toBeGreaterThan(0));const stale=sockets[0];
 fireEvent.change(screen.getByLabelText('Workspace'),{target:{value:'b'}});
 await waitFor(()=>expect(screen.getByText('Fresh Research Agent')).toBeTruthy());
 resolveA(bootstrap('a','Stale Coding Agent'));await new Promise(resolve=>setTimeout(resolve,0));
 stale.onmessage?.({data:JSON.stringify({workspace_id:'a',seq:900,id:'stale',event_type:'task.completed'})});stale.onopen?.();
 expect(screen.queryByText('Stale Coding Agent')).toBeNull();expect(screen.getByText('Fresh Research Agent')).toBeTruthy();expect(useStore.getState().events).toEqual([]);expect(useStore.getState().connected).toBe(false);
});
});
