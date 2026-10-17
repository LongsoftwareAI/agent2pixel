"""AgentVerse localhost API. Run from repository root with uvicorn."""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
from services.api.store import Store, uid, now
from services.api.policy import safe_document, validate_brain
from services.worker.runtime import Runtime, validate_graph
from services.worker.adapters import run_brain

ASSETS=[dict(id=id,name=name,kind=kind,license='CC0-1.0',author='AgentVerse contributors') for id,name,kind in [('desk','Desk','furniture'),('chair','Chair','furniture'),('plant','Plant','furniture'),('bookshelf','Bookshelf','furniture'),('sofa','Sofa','furniture')]]

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class WorkspaceInput(Input):
    name:str=Field(min_length=1,max_length=100)
class AgentInput(Input):
    workspace_id:str
    name:str=Field(min_length=1,max_length=100)
    role:str='Developer'
    system_prompt:str='Complete the assigned task faithfully.'
    brain:dict=Field(default_factory=lambda:dict(provider='mock',model='deterministic',endpoint=None,secret_ref=None))
    skin:str='blue'
    skills:list[str]=Field(default_factory=list)
    tools:list[str]=Field(default_factory=list)
    memory_policy:str='workspace'
    workstation:dict=Field(default_factory=lambda:dict(x=3,y=3))
    enabled:bool=True
class WorkflowInput(Input):
    workspace_id:str
    name:str=Field(min_length=1,max_length=100)
    graph:dict
class RunInput(Input):
    input:str=Field(min_length=1,max_length=20000)
    max_steps:int=Field(default=32,ge=1,le=128)
    token_budget:int=Field(default=12000,ge=1,le=100000)
    retry_limit:int=Field(default=1,ge=0,le=3)
class LayoutInput(Input):
    furniture:list[dict]
    assignments:dict
class MemoryInput(Input):
    workspace_id:str
    content:str=Field(min_length=1,max_length=20000)
    kind:str='note'
    agent_id:str|None=None
class ProviderInput(Input):
    provider:str
    model:str
    endpoint:str|None=None


def create_app(data_dir=None):
    @asynccontextmanager
    async def lifespan(app):
        store=Store(data_dir or os.getenv('AGENTVERSE_DATA_DIR','var/agentverse'))
        app.state.store=store;app.state.runtime=Runtime(store)
        if not store.list('workspace'):
            for name in ('Coding','Research'):
                ws=workspace_create(store,name)
                agents=[]
                for i,role in enumerate(('Planner','Developer','Reviewer')):
                    value=AgentInput(workspace_id=ws['id'],name=role,role=role,skin=('blue','purple','green')[i],workstation={'x':3+i*5,'y':5}).model_dump()
                    value.update(id=uid(),status='idle');store.put('agent',value);agents.append(value)
                room=store.list('room',ws['id'])[0]
                room['assignments']={a['id']:a['workstation'] for a in agents}
                room['furniture']=[dict(id=uid(),asset_id='desk',x=3+i*5,y=4,rotation=0) for i in range(3)]
                store.put('room',room)
                nodes=[dict(id='start',type='start')]+[dict(id=a['role'].lower(),type='agent',agent_id=a['id']) for a in agents]+[dict(id='end',type='end')]
                graph={'nodes':nodes,'edges':[{'source':a['id'],'target':b['id']} for a,b in zip(nodes,nodes[1:])]}
                store.put('workflow',dict(id=uid(),workspace_id=ws['id'],name='Planner → Developer → Reviewer',version=1,graph=graph))
        yield
        for job in list(app.state.runtime.jobs.values()):job.cancel()
        if app.state.runtime.jobs: await asyncio.gather(*list(app.state.runtime.jobs.values()),return_exceptions=True)
        store.db.close()
    app=FastAPI(title='AgentVerse localhost',version='0.1.0',lifespan=lifespan)
    def store():return app.state.store
    def get(kind,id):
        value=store().get(kind,id)
        if not value:raise HTTPException(404,f'{kind} not found')
        return value
    def workspace(id):return get('workspace',id)
    @app.get('/health')
    def health():return {'status':'ok','schema_version':1}
    @app.get('/api/workspaces')
    def workspaces():return store().list('workspace')
    @app.post('/api/workspaces')
    def new_workspace(body:WorkspaceInput):return workspace_create(store(),body.name)
    @app.get('/api/bootstrap')
    def bootstrap(workspace_id:str):
        workspace(workspace_id)
        return dict(workspaces=workspaces(),agents=store().list('agent',workspace_id),workflows=store().list('workflow',workspace_id),room=store().list('room',workspace_id)[0],assets=ASSETS,runs=store().list('run',workspace_id))
    @app.get('/api/agents')
    def agents(workspace_id:str):workspace(workspace_id);return store().list('agent',workspace_id)
    @app.post('/api/agents')
    def new_agent(body:AgentInput):
        value=body.model_dump();workspace(body.workspace_id);validate_brain(value['brain'])
        value.update(id=uid(),status='idle');store().put('agent',value)
        store().event(body.workspace_id,'agent.created',{'name':body.name},agent=value['id']);return value
    @app.get('/api/agents/{id}')
    def agent(id:str):return get('agent',id)
    @app.patch('/api/agents/{id}')
    def patch_agent(id:str,body:dict):
        value=get('agent',id)
        if 'workspace_id' in body and body['workspace_id']!=value['workspace_id']:raise HTTPException(403,'Agent workspace is immutable')
        if set(body)-set(AgentInput.model_fields):raise HTTPException(422,'Unknown agent fields')
        try:
            merged=AgentInput(**{**{k:v for k,v in value.items() if k in AgentInput.model_fields},**body}).model_dump()
        except ValidationError:
            raise HTTPException(422,'Invalid agent fields') from None
        validate_brain(merged['brain']);merged.update(id=id,status=value['status']);return store().put('agent',merged)
    @app.delete('/api/agents/{id}')
    def delete_agent(id:str):
        value=get('agent',id);value['enabled']=False;return store().put('agent',value)
    @app.get('/api/workflows')
    def workflows(workspace_id:str):workspace(workspace_id);return store().list('workflow',workspace_id)
    @app.post('/api/workflows')
    def new_workflow(body:WorkflowInput):
        workspace(body.workspace_id)
        errors=validate_graph(body.graph,store(),body.workspace_id)
        if errors:raise HTTPException(400,'; '.join(errors))
        return store().put('workflow',dict(id=uid(),version=1,**body.model_dump()))
    @app.post('/api/workflows/{id}/validate')
    def validate(id:str):
        value=get('workflow',id);errors=validate_graph(value['graph'],store(),value['workspace_id']);return dict(valid=not errors,errors=errors)
    def start_run(id,body):
        workflow=get('workflow',id)
        errors=validate_graph(workflow['graph'],store(),workflow['workspace_id'])
        if errors:raise HTTPException(400,'; '.join(errors))
        if any(r['state'] in ('queued','running') for r in store().list('run',workflow['workspace_id'])):
            raise HTTPException(409,'Workspace already has an active run')
        if len(app.state.runtime.jobs)>=16:raise HTTPException(409,'Run queue full')
        value=dict(id=uid(),workflow_id=id,workspace_id=workflow['workspace_id'],state='queued',output='',error=None,started_at=None,ended_at=None,tasks=[],graph=workflow['graph'],**body.model_dump())
        store().put('run',value);app.state.runtime.schedule(value);return value
    @app.post('/api/workflows/{id}/runs')
    async def new_run(id:str,body:RunInput):return start_run(id,body)
    @app.get('/api/runs')
    def runs(workspace_id:str):workspace(workspace_id);return store().list('run',workspace_id)
    @app.get('/api/runs/{id}')
    def run(id:str):return get('run',id)
    @app.post('/api/runs/{id}/cancel')
    async def cancel(id:str):
        value=get('run',id)
        if value['state'] in ('completed','failed','cancelled'):raise HTTPException(409,'Run is already terminal')
        value.update(state='cancelled',ended_at=now());store().put('run',value);app.state.runtime.cancel(id)
        store().event(value['workspace_id'],'workflow.cancelled',run=id);return value
    @app.post('/api/runs/{id}/retry')
    async def retry(id:str):
        value=get('run',id)
        if value['state'] not in ('failed','cancelled'):raise HTTPException(409,'Only failed or cancelled runs may retry')
        return start_run(value['workflow_id'],RunInput(**{k:value[k] for k in RunInput.model_fields}))
    @app.get('/api/runs/{id}/messages')
    def messages(id:str):
        value=get('run',id);return [m for m in store().list('message',value['workspace_id']) if m['run_id']==id]
    @app.get('/api/runs/{id}/events')
    def run_events(id:str):get('run',id);return store().events(run=id)
    @app.get('/api/events')
    def events(workspace_id:str,after:int=0):workspace(workspace_id);return store().events(workspace=workspace_id,after=after)
    @app.websocket('/ws/workspaces/{id}/events')
    async def websocket(websocket:WebSocket,id:str,after:int=0):
        origin=websocket.headers.get('origin')
        if origin and origin not in ('http://localhost:3000','http://127.0.0.1:3000'):
            await websocket.close(code=1008);return
        if not store().get('workspace',id):await websocket.close(code=1008);return
        await websocket.accept()
        try:
            while True:
                for value in store().events(workspace=id,after=after):
                    await websocket.send_json(value);after=value['seq']
                try:await asyncio.wait_for(websocket.receive_text(),timeout=.15)
                except asyncio.TimeoutError:pass
        except WebSocketDisconnect:pass
    @app.get('/api/assets')
    def assets():return ASSETS
    @app.get('/api/rooms/{id}/layout')
    def room(id:str):return get('room',id)
    @app.put('/api/rooms/{id}/layout')
    def layout(id:str,body:LayoutInput):
        value=get('room',id);occupied=set();ids=set()
        def position(item):
            x,y=item.get('x'),item.get('y')
            if type(x)!=int or type(y)!=int or not 0<=x<20 or not 0<=y<14:raise HTTPException(400,'Tile out of bounds')
            if (x,y) in occupied:raise HTTPException(409,'Tile collision')
            occupied.add((x,y))
        for item in body.furniture:
            if item.get('asset_id') not in {a['id'] for a in ASSETS}:raise HTTPException(400,'Unknown asset')
            if not item.get('id') or item['id'] in ids:raise HTTPException(400,'Duplicate or missing furniture id')
            ids.add(item['id']);position(item)
            if item.get('rotation',0) not in (0,90,180,270):raise HTTPException(400,'Invalid rotation')
        for agent_id,item in body.assignments.items():
            if get('agent',agent_id)['workspace_id']!=value['workspace_id']:raise HTTPException(403,'Agent outside room workspace')
            position(item)
        value.update(body.model_dump());return store().put('room',value)
    @app.get('/api/memories')
    def memories(workspace_id:str):workspace(workspace_id);return store().list('memory',workspace_id)
    @app.post('/api/memories')
    def memory(body:MemoryInput):
        workspace(body.workspace_id)
        if body.agent_id and get('agent',body.agent_id)['workspace_id']!=body.workspace_id:raise HTTPException(403,'Agent outside workspace')
        return store().put('memory',dict(id=uid(),created_at=now(),**body.model_dump()))
    @app.get('/api/documents')
    def documents(workspace_id:str):
        root=Path(workspace(workspace_id)['root_path']);result=[]
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root):result.append(dict(path=str(path.relative_to(root)),size=path.stat().st_size))
        return result[:1000]
    @app.get('/api/documents/content')
    def document(workspace_id:str,path:str):
        target=safe_document(workspace(workspace_id)['root_path'],path)
        try:content=target.read_text()
        except UnicodeError:raise HTTPException(400,'Document is not UTF-8 text')
        return dict(path=path,content=content)
    @app.get('/api/settings')
    def settings():
        return dict(providers=[dict(provider='mock',ready=True),dict(provider='openai',ready=bool(os.getenv('OPENAI_API_KEY') or os.getenv('AGENTVERSE_OPENAI_API_KEY'))),dict(provider='ollama',ready=False,message='Test local model connection')],policy=dict(shell=False,file_write=False,external_tools=False,read_only_tools=['documents.list','documents.read','memory.read']),data_dir=str(store().root))
    @app.post('/api/providers/test')
    async def provider_test(body:ProviderInput):
        brain=body.model_dump();brain['secret_ref']='AGENTVERSE_OPENAI_API_KEY' if os.getenv('AGENTVERSE_OPENAI_API_KEY') else 'OPENAI_API_KEY';validate_brain(brain)
        try:
            await run_brain(dict(brain=brain,role='Test',system_prompt='Reply briefly'), 'Connection check',128)
            return dict(ok=True,message='Provider connection succeeded')
        except ValueError as exc:return dict(ok=False,message=str(exc))
    @app.get('/api/audit')
    def audit(workspace_id:str):workspace(workspace_id);return store().list('audit',workspace_id)
    return app


def workspace_create(store,name):
    id=uid();root=store.root/'workspaces'/id;root.mkdir(parents=True)
    (root/'README.md').write_text(f'# {name}\n\nIsolated AgentVerse project directory.\n')
    value=store.put('workspace',dict(id=id,name=name,root_path=str(root),created_at=now()))
    store.put('room',dict(id=uid(),workspace_id=id,width=20,height=14,furniture=[],assignments={}))
    return value

app=create_app()
