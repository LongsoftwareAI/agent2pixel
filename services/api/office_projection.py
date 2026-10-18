"""AgentVerse domain projection for the MIT Habblaud office client.

No CLI transcripts or simulated execution: only persisted domain records/events.
"""
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from services.api.store import synchronized
from services.api.office_layout import create_office_layout_router, room_furniture, seed_for_room

SCHEMA_VERSION = 2
HAIR = {'short','buzz','spiky','side_part','curly','afro','bob','long','ponytail','bun','pigtails','mohawk','bald','wavy'}
STYLES = {'hairStyle': HAIR, 'topStyle': {'tshirt','hoodie','shirt_tie','sweater','jacket','blouse','polo'}, 'bottomStyle': {'pants','shorts','skirt'}, 'accessory': {'none','glasses','sunglasses','headphones','cap','beanie','earrings','bow'}, 'facialHair': {'none','stubble','beard','mustache','goatee'}}
COLORS = {'skin','hair','eyes','top','topAccent','bottom','shoes','accessoryColor'}
EVENTS = {
    'agent.created': ('other','👤','Agent đã được tạo'),
    'agent.updated': ('other','⚙','Đã cập nhật cấu hình'),
    'task.queued': ('wait','⌛','Đang chờ nhận việc'),
    'task.started': ('plan','▶','Bắt đầu thực thi'),
    'task.progress': ('respond','⋯','Đang xử lý công việc'),
    'task.completed': ('done','✓','Hoàn thành công việc'),
    'task.failed': ('error','!','Công việc thất bại'),
    'task.cancelled': ('wait','■','Đã hủy công việc'),
    'tool.requested': ('read','⚒','Yêu cầu sử dụng tool'),
    'tool.completed': ('read','✓','Tool đã trả kết quả'),
    'tool.failed': ('error','!','Tool thất bại'),
    'review.required': ('ask','?','Chờ người dùng review'),
    'review.decided': ('respond','✓','Đã nhận quyết định review'),
    'approval.required': ('ask','?','Cần phê duyệt'),
    'skill.activated': ('skill','✦','Đã kích hoạt skill'),
    'memory.read': ('read','▤','Đọc memory được phép'),
    'workflow.completed': ('done','✓','Workflow hoàn thành'),
    'workflow.failed': ('error','!','Workflow thất bại'),
    'workflow.cancelled': ('wait','■','Workflow đã hủy'),
}


def epoch(value, default=0):
    if isinstance(value, (float,int)):
        return int(value)
    try:
        return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()*1000)
    except (TypeError, ValueError, AttributeError):
        return default


def seed_for(value):
    return int.from_bytes(hashlib.sha256(str(value).encode()).digest()[:4], 'big')


def activity(event):
    kind, icon, label = EVENTS.get(event['event_type'], ('other','·',event['event_type']))
    return dict(id=event['id'], kind=kind, icon=icon, text=label, at=epoch(event.get('created_at')),
                error=kind=='error', eventId=event['id'], seq=event['seq'], runId=event.get('run_id'))


@synchronized
def project(store, workspace_id=None):
    workspaces=store.list('workspace')
    slots={w['id']:i for i,w in enumerate(workspaces)}
    workspace_created={w['id']:epoch(w.get('created_at')) for w in workspaces}
    if workspace_id:
        workspaces=[w for w in workspaces if w['id']==workspace_id]
        if not workspaces:
            raise HTTPException(404,'Workspace not found')
    ids={w['id'] for w in workspaces}
    events=[e for e in store.events() if e['workspace_id'] in ids]
    rooms=[dict(id=w['id'],name=w['name'],path=w['root_path'],slot=slots[w['id']],
                seed=seed_for_room(w['id']),createdAt=epoch(w.get('created_at')),
                customFurniture=room_furniture(store,w['id'])['items'],layoutVersion=room_furniture(store,w['id'])['version'])
           for i,w in enumerate(workspaces)]
    agents=[]
    all_agents=[a for a in store.list('agent') if a['workspace_id'] in ids and a.get('enabled',True)]
    runs=[r for r in store.list('run') if r['workspace_id'] in ids]
    run_by_id={r['id']:r for r in runs}
    tool_records=[t for t in store.list('flow_tool_result') if t.get('workspace_id') in ids and t.get('run_id') in run_by_id and run_by_id[t['run_id']]['workspace_id']==t.get('workspace_id')]
    for a in all_agents:
        recent_events=[e for e in events if e.get('agent_id')==a['id']]
        recent=[activity(e) for e in recent_events[-30:]]
        tasks=[]
        for run in runs:
            for task in run.get('tasks',[]):
                if task.get('agent_id')==a['id']:
                    state=task['state']
                    tasks.append(dict(id=task['id'],title=task.get('node_id','Task'),status=state if state in ('completed','failed','cancelled') else 'in_progress' if state in ('running','waiting_approval') else 'pending',domainState=state))
        agent_tools=[t for t in tool_records if t.get('agent_id')==a['id'] and t['workspace_id']==a['workspace_id']]
        active_tools=[t for t in agent_tools if t.get('status')=='started' and run_by_id[t['run_id']]['state']=='running']
        for record in agent_tools:
            run_state=run_by_id[record['run_id']]['state']
            status='completed' if record['status']=='completed' else 'cancelled' if run_state=='cancelled' else 'failed' if record['status']=='failed' or run_state=='failed' else 'in_progress' if record in active_tools else 'pending'
            tasks.append(dict(id=record['id'],title='Tool: '+record.get('tool',{}).get('id','unknown'),status=status,domainState=record['status']))
        latest_run=recent_events[-1].get('run_id') if recent_events else None
        failed_tool=any(t['run_id']==latest_run and t.get('status')=='failed' and run_by_id[t['run_id']]['state']=='failed' for t in agent_tools)
        original='working' if active_tools else 'error' if failed_tool else a.get('status','idle')
        state='working' if original in ('working','running') else 'waiting' if original in ('waiting','waiting_approval','queued') else 'idle'
        appearance=a.get('appearance') or {}
        agent_seed=appearance.get('seed',seed_for(a['id']))
        if type(agent_seed)!=int or not 0<=agent_seed<=0xFFFFFFFF:
            agent_seed=seed_for(agent_seed)
        execution=a.get('execution') or {'engine':'langchain'}
        last=recent_events[-1] if recent_events else None
        start=epoch(a.get('created_at'),workspace_created.get(a['workspace_id'],0))
        agents.append(dict(id=a['id'],kind='main',provider='agentverse',roomId=a['workspace_id'],
            name=a['name'],look='f' if agent_seed%2 else 'm',role=a.get('role','Agent'),
            title=a.get('role','Agent'),sessionId=a['id'],account='agentverse',status=state,
            activity=recent[-1] if recent else None,recent=recent,tasks=tasks[-20:],
            model=(a.get('brain') or {}).get('model'),startedAt=start,lastEventAt=epoch(last.get('created_at')) if last else start,
            statusSince=epoch(last.get('created_at')) if last else start,
            stats=dict(usageKnown=False,toolCalls=sum(e['event_type']=='tool.completed' for e in recent_events),tokensIn=0,tokensOut=0,subagents=0),
            seed=agent_seed,parts=appearance.get('parts',{}),custom=bool(appearance),
            source='agentverse',executionEngine=execution.get('engine','langchain'),brainProvider=a.get('brain',{}).get('provider','mock'),
            domainStatus=original,usageKnown=False,canMessage=False,waitingFor='Phê duyệt tool' if state=='waiting' else None))
    seq=events[-1]['seq'] if events else 0
    return dict(rev=seq,seq=seq,schema_version=SCHEMA_VERSION,serverTime=int(time.time()*1000),rooms=rooms,agents=agents,accounts=[],
        meta=dict(demo=False,sources=[dict(label='AgentVerse Python runtime',provider='agentverse',path='local://agentverse',sessions=len(agents),ok=True)],
                  startedAt=epoch(workspaces[0].get('created_at')) if workspaces else 0,version='agentverse-0.2',terminal=False,messages=False,
                  world=dict(enabled=False,configured=False),features=dict(cli=False,remote=False,city=False,syntheticTasks=False)))


@synchronized
def project_feed(store, after=0, workspace_id=None):
    agents={a['id']:a for a in store.list('agent')}
    workspaces={w['id']:w for w in store.list('workspace')}
    return [dict(id=e['id'],agentId=e.get('agent_id') or '',roomId=e['workspace_id'],
                 agentName=agents.get(e.get('agent_id'),{}).get('name','Workflow'),
                 roomName=workspaces.get(e['workspace_id'],{}).get('name','Workspace'),account='agentverse',activity=activity(e))
            for e in store.events(workspace=workspace_id,after=after)[:200]]


def validate_character(body):
    if not isinstance(body,dict) or set(body)-{'name','seed','parts'}:
        raise HTTPException(422,'Invalid character fields')
    name=body.get('name')
    if not isinstance(name,str) or not name.strip() or len(name)>24 or any(ord(c)<32 for c in name):
        raise HTTPException(422,'Character name requires 1–24 visible characters')
    seed=body.get('seed')
    if type(seed)!=int or not 0<=seed<=0xFFFFFFFF:
        raise HTTPException(422,'Character seed requires unsigned 32-bit integer')
    parts=body.get('parts',{})
    if not isinstance(parts,dict) or set(parts)-(COLORS|set(STYLES)):
        raise HTTPException(422,'Unknown appearance part')
    for key,value in parts.items():
        if not isinstance(value,str) or (key in COLORS and not re.fullmatch('#[0-9a-fA-F]{6}',value)) or (key in STYLES and value not in STYLES[key]):
            raise HTTPException(422,'Invalid appearance value')
    return name.strip(),seed,parts


def create_office_router(app):
    router=APIRouter()
    def store():
        return app.state.store

    @router.get('/api/office/snapshot')
    def snapshot(workspace_id:str|None=None):
        return project(store(),workspace_id)

    @router.get('/api/office/feed')
    def feed(after:int=Query(0,ge=0),workspace_id:str|None=None):
        if workspace_id and not store().get('workspace',workspace_id):
            raise HTTPException(404,'Workspace not found')
        return project_feed(store(),after,workspace_id)

    @router.get('/api/office/agents/{id}')
    def detail(id:str):
        snap=project(store())
        agent=next((a for a in snap['agents'] if a['id']==id),None)
        if not agent:
            raise HTTPException(404,'Agent not found')
        history=[activity(e) for e in store().events() if e.get('agent_id')==id][-200:]
        return dict(agent=agent,history=history)

    @router.get('/api/access')
    def access():
        return dict(remote=False,local=True,permissions=False,messages=False,terminal=False,spawn=False,world=False)

    @router.put('/api/agents/{id}/character')
    def character(id:str,body:dict):
        agent=store().get('agent',id)
        if not agent or not agent.get('enabled',True):
            raise HTTPException(404,'Agent not found')
        name,seed,parts=validate_character(body)
        agent.update(name=name,appearance=dict(seed=seed,parts=parts))
        store().put('agent',agent)
        store().event(agent['workspace_id'],'agent.updated',{'appearance_changed':True},agent=id)
        return {'ok':True}

    @router.delete('/api/agents/{id}/character')
    def reset_character(id:str):
        agent=store().get('agent',id)
        if not agent:
            raise HTTPException(404,'Agent not found')
        agent['appearance']={}
        store().put('agent',agent)
        store().event(agent['workspace_id'],'agent.updated',{'appearance_reset':True},agent=id)
        return {'ok':True}

    @router.get('/api/office/stream')
    async def stream(request:Request,after:int=Query(0,ge=0),workspace_id:str|None=None):
        origin=request.headers.get('origin')
        if origin and origin not in {'http://localhost:3000','http://127.0.0.1:3000','http://localhost:3001','http://127.0.0.1:3001'}:
            raise HTTPException(403,'Office stream origin denied')
        if workspace_id and not store().get('workspace',workspace_id):
            raise HTTPException(404,'Workspace not found')
        last=request.headers.get('last-event-id')
        if last:
            try:
                parsed=int(last)
                if parsed<0:
                    raise ValueError('negative cursor')
                after=max(after,parsed)
            except ValueError:
                raise HTTPException(400,'Invalid last event cursor') from None
            if after<0:
                raise HTTPException(400,'Invalid last event cursor')
        async def generate():
            cursor=after
            signature=None
            heartbeat=0
            while not await request.is_disconnected():
                snap=project(store(),workspace_id)
                stable={k:v for k,v in snap.items() if k!='serverTime'}
                current=json.dumps(stable,sort_keys=True)
                if current!=signature:
                    yield 'event: snapshot\nid: '+str(cursor)+'\ndata: '+json.dumps(snap,ensure_ascii=False)+'\n\n'
                    signature=current
                items=project_feed(store(),cursor,workspace_id)
                if items:
                    cursor=max(item['activity']['seq'] for item in items)
                    yield 'event: feed\nid: '+str(cursor)+'\ndata: '+json.dumps(items,ensure_ascii=False)+'\n\n'
                heartbeat+=1
                if heartbeat%40==0:
                    yield ': heartbeat\n\n'
                await asyncio.sleep(.25)
        return StreamingResponse(generate(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
    router.include_router(create_office_layout_router(app))
    return router
