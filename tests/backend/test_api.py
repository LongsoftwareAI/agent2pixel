import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as client: yield client

def bootstrap(client):
    ws=client.get('/api/workspaces').json()[0]
    return client.get('/api/bootstrap',params={'workspace_id':ws['id']}).json()

def wait(client,id):
    for _ in range(150):
        run=client.get('/api/runs/'+id).json()
        if run['state'] not in ('queued','running'):return run
        time.sleep(.01)
    pytest.fail('run did not terminate')

def start(client,b,**extra):
    return client.post('/api/workflows/'+b['workflows'][0]['id']+'/runs',json={'input':'Build a calculator for my shop',**extra}).json()

def test_workflow_handoff_events_and_persistence(client):
    assert client.get('/health').json()['status']=='ok'
    b=bootstrap(client);assert len(b['workspaces'])==2 and len(b['agents'])==3
    run=wait(client,start(client,b)['id']);assert run['state']=='completed'
    assert len(run['tasks'])==3
    assert run['tasks'][1]['input']==run['tasks'][0]['output']
    assert run['tasks'][2]['input']==run['tasks'][1]['output']
    messages=client.get('/api/runs/'+run['id']+'/messages').json();assert len(messages)==2
    events=client.get('/api/runs/'+run['id']+'/events').json()
    seq=[e['seq'] for e in events];assert seq==sorted(set(seq))
    assert events[-1]['event_type']=='workflow.completed'
    replay=client.get('/api/events',params={'workspace_id':run['workspace_id'],'after':seq[-2]}).json()
    assert [e['seq'] for e in replay]==seq[-1:]
    assert 'shop' in run['output']

def test_crud_and_secrets(client):
    b=bootstrap(client);a=b['agents'][0]
    assert client.patch('/api/agents/'+a['id'],json={'name':'New name','skin':'purple'}).json()['name']=='New name'
    assert client.patch('/api/agents/'+a['id'],json={'brain':{'provider':'openai','api_key':'do-not-store'}}).status_code==422
    assert client.patch('/api/agents/'+a['id'],json={'brain':{'provider':'openai','model':'test','endpoint':'http://169.254.169.254'}}).status_code==403
    assert client.patch('/api/agents/'+a['id'],json={'workspace_id':b['workspaces'][1]['id']}).status_code==403
    assert client.delete('/api/agents/'+a['id']).json()['enabled'] is False
    assert client.post('/api/workspaces',json={'name':''}).status_code==422

def test_workspace_paths_and_memory(client,tmp_path):
    b=bootstrap(client);ws=b['workspaces'][0];params={'workspace_id':ws['id']}
    assert client.get('/api/documents/content',params={**params,'path':'README.md'}).status_code==200
    assert client.get('/api/documents/content',params={**params,'path':'../../agentverse.sqlite3'}).status_code==403
    outside=tmp_path/'outside';outside.write_text('private')
    (Path(ws['root_path'])/'escape').symlink_to(outside)
    assert client.get('/api/documents/content',params={**params,'path':'escape'}).status_code==403
    assert client.post('/api/memories',json={**params,'content':'remember'}).status_code==200
    other=client.get('/api/bootstrap',params={'workspace_id':b['workspaces'][1]['id']}).json()['agents'][0]
    assert client.post('/api/memories',json={**params,'content':'x','agent_id':other['id']}).status_code==403

def test_budget_retry_cancel_and_policy(client):
    b=bootstrap(client)
    failed=wait(client,start(client,b,token_budget=1)['id'])
    assert failed['state']=='failed' and failed['tasks'][0]['retry_count']==1
    retry=client.post('/api/runs/'+failed['id']+'/retry');assert retry.status_code==200
    wait(client,retry.json()['id'])
    run=start(client,b);assert client.post('/api/runs/'+run['id']+'/cancel').status_code==200
    time.sleep(.2);assert client.get('/api/runs/'+run['id']).json()['state']=='cancelled'
    assert client.post('/api/runs/'+run['id']+'/cancel').status_code==409
    client.patch('/api/agents/'+b['agents'][0]['id'],json={'tools':['shell','../../write']})
    failed=wait(client,start(client,b)['id']);assert failed['state']=='failed'
    events=client.get('/api/runs/'+failed['id']+'/events').json()
    assert any(e['event_type']=='approval.required' for e in events)
    assert client.get('/api/audit',params={'workspace_id':failed['workspace_id']}).json()[0]['decision']=='denied'

def test_graph_and_condition(client):
    b=bootstrap(client);workflow=b['workflows'][0];graph=workflow['graph']
    graph['edges'].append({'source':'end','target':'start'})
    assert client.post('/api/workflows',json={**{k:workflow[k] for k in ('workspace_id','name')},'graph':graph}).status_code==400
    nodes=[{'id':'s','type':'start'},{'id':'c','type':'condition','condition':{'field':'input','equals':'yes'}},{'id':'a','type':'agent','agent_id':b['agents'][0]['id']},{'id':'e','type':'end'}]
    graph={'nodes':nodes,'edges':[{'source':'s','target':'c'},{'source':'c','target':'a','label':'true'},{'source':'c','target':'e','label':'false'},{'source':'a','target':'e'}]}
    result=client.post('/api/workflows',json={'workspace_id':workflow['workspace_id'],'name':'conditional','graph':graph})
    assert result.status_code==200
    run=client.post('/api/workflows/'+result.json()['id']+'/runs',json={'input':'no'}).json()
    run=wait(client,run['id']);assert run['state']=='completed' and not run['tasks']
    graph['nodes'][1]['condition']['field']='__class__'
    assert client.post('/api/workflows',json={'workspace_id':workflow['workspace_id'],'name':'bad','graph':graph}).status_code==400

def test_layout_and_websocket(client):
    b=bootstrap(client);room=b['room'];url='/api/rooms/'+room['id']+'/layout'
    assert client.put(url,json={'furniture':room['furniture'],'assignments':room['assignments']}).status_code==200
    duplicate=room['furniture']+[dict(room['furniture'][0],id='another')]
    assert client.put(url,json={'furniture':duplicate,'assignments':{}}).status_code==409
    room['furniture'][0]['x']=50
    assert client.put(url,json={'furniture':room['furniture'],'assignments':{}}).status_code==400
    a=b['agents'][0]
    result=client.post('/api/agents',json={k:v for k,v in a.items() if k not in ('id','status')}).json()
    with client.websocket_connect('/ws/workspaces/'+a['workspace_id']+'/events?after=0') as socket:
        assert socket.receive_json()['event_type']=='agent.created'

def test_disk_restart(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b=bootstrap(client);run=wait(client,start(client,b)['id'])
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/runs/'+run['id']).json()['output']==run['output']
        assert len(client.get('/api/workspaces').json())==2

def test_read_only_tools_and_concurrency(client):
    b=bootstrap(client);ws=b['workspaces'][0]
    client.post('/api/memories',json={'workspace_id':ws['id'],'content':'Customer requires accessibility'})
    client.patch('/api/agents/'+b['agents'][0]['id'],json={'tools':['documents.list','documents.read','memory.read']})
    run=start(client,b)
    assert client.post('/api/workflows/'+b['workflows'][0]['id']+'/runs',json={'input':'concurrent'}).status_code==409
    result=wait(client,run['id'])
    assert result['state']=='completed' and 'Customer requires accessibility' in result['output']
    assert 'README.md' in result['output']

def test_validation_failure_paths(client):
    b=bootstrap(client);a=b['agents'][0]
    assert client.patch('/api/agents/'+a['id'],json={'name':''}).status_code==422
    assert client.post('/api/workflows',json={'workspace_id':a['workspace_id'],'name':'bad','graph':{'nodes':[{'id':'s','type':'start'},{'id':'e','type':'end'}],'edges':[None]}}).status_code==400
    assert client.get('/api/runs/missing').status_code==404
    assert client.post('/api/providers/test',json={'provider':'openai','model':'test','endpoint':'https://example.invalid'}).status_code==403

def test_malformed_graph_and_restart_recovery(client,tmp_path):
    b=bootstrap(client);workflow=b['workflows'][0]
    payload={k:workflow[k] for k in ('workspace_id','name','graph')}
    payload['graph']['edges'][0]['source']=[]
    assert client.post('/api/workflows',json=payload).status_code==400
    store=client.app.state.store
    a=b['agents'][0];a['status']='working';store.put('agent',a)
    interrupted=dict(id='interrupted',workspace_id=a['workspace_id'],state='running',tasks=[dict(id='task-interrupted',agent_id=a['id'],state='running')])
    store.put('run',interrupted)
    from services.api.store import Store
    recovered=Store(tmp_path)
    value=recovered.get('run','interrupted')
    assert value['state']=='failed' and value['tasks'][0]['state']=='failed'
    assert recovered.get('agent',a['id'])['status']=='error'
    assert recovered.events(run='interrupted')[-1]['event_type']=='workflow.failed'
    recovered.db.close()

def test_sqlite_foreign_keys(client):
    import sqlite3
    store=client.app.state.store
    with pytest.raises(sqlite3.IntegrityError):
        store.put('agent',{'id':'orphan','workspace_id':'missing'})
    store.db.rollback()
    assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert len(store.db.execute('PRAGMA foreign_key_list(events)').fetchall())==3

def test_original_bookshelf_sofa_layout(client):
    b=bootstrap(client);url='/api/rooms/'+b['room']['id']+'/layout'
    assets=client.get('/api/assets').json()
    assert {'bookshelf','sofa'}.issubset({a['id'] for a in assets})
    assert all(a['license']=='CC0-1.0' for a in assets)
    furniture=[dict(id='shelf',asset_id='bookshelf',x=1,y=1,rotation=0),dict(id='sofa',asset_id='sofa',x=2,y=1,rotation=90)]
    assert client.put(url,json={'furniture':furniture,'assignments':{}}).status_code==200
    assert client.get(url).json()['furniture']==furniture
    furniture[1]['x']=1
    assert client.put(url,json={'furniture':furniture,'assignments':{}}).status_code==409

def test_store_concurrent_transactions(client):
    from concurrent.futures import ThreadPoolExecutor
    from services.api.store import uid
    store=client.app.state.store;ws=bootstrap(client)['workspaces'][0]['id']
    def transaction(index):
        value=dict(id=uid(),workspace_id=ws,kind='note',content=f'item {index}')
        store.put('memory',value)
        event=store.event(ws,'task.progress',{'index':index})
        assert store.get('memory',value['id'])==value
        assert store.list('memory',ws)
        assert store.events(workspace=ws)
        return event['seq']
    with ThreadPoolExecutor(max_workers=12) as pool:
        seq=list(pool.map(transaction,range(120)))
    persisted=store.events(workspace=ws)
    assert len(seq)==len(set(seq))==120
    assert [e['seq'] for e in persisted]==sorted(seq)
    assert len(store.list('memory',ws))==120

def test_seed_room_rich_layout_and_preserve_user_changes(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b=bootstrap(client);room=b['room'];url='/api/rooms/'+room['id']+'/layout'
        assert {'desk','chair','plant','bookshelf','sofa'}.issubset({f['asset_id'] for f in room['furniture']})
        positions=[(f['x'],f['y']) for f in room['furniture']]+[(p['x'],p['y']) for p in room['assignments'].values()]
        assert len(positions)==len(set(positions))
        assert all(0<=x<20 and 0<=y<14 for x,y in positions)
        assert client.put(url,json={'furniture':room['furniture'],'assignments':room['assignments']}).status_code==200
        custom={'furniture':[room['furniture'][0]],'assignments':{}}
        assert client.put(url,json=custom).status_code==200
    with TestClient(create_app(tmp_path)) as client:
        loaded=client.get(url).json()
        assert loaded['furniture']==custom['furniture'] and loaded['assignments']=={}

@pytest.mark.parametrize('brain',[{'provider':'ollama','model':'x','endpoint':123},{'provider':'ollama','model':'x','secret_ref':123},{'provider':[]},{'provider':'openai'},{'provider':'openai','model':None},{'provider':'ollama','model':'  '},{'provider':'ollama','model':False},{'provider':'ollama','model':'x','endpoint':'http://[bad'}])
def test_malformed_brain_rejected(client,brain):
    b=bootstrap(client);ws=b['workspaces'][0]['id']
    assert client.post('/api/agents',json={'workspace_id':ws,'name':'invalid brain','brain':brain}).status_code==422
    assert client.patch('/api/agents/'+b['agents'][0]['id'],json={'brain':brain}).status_code==422

def test_malformed_layout_and_workstation_rejected(client):
    b=bootstrap(client);url='/api/rooms/'+b['room']['id']+'/layout';a=b['agents'][0]
    assert client.put(url,json={'furniture':[],'assignments':{a['id']:[]}}).status_code==400
    assert client.put(url,json={'furniture':[{'id':[],'asset_id':'plant','x':1,'y':1}],'assignments':{}}).status_code==400
    assert client.put(url,json={'furniture':[{'id':'x','asset_id':[],'x':1,'y':1}],'assignments':{}}).status_code==400
    for point in ({'x':-1,'y':0},{'x':True,'y':1},{'x':2.5,'y':3}):
        assert client.patch('/api/agents/'+a['id'],json={'workstation':point}).status_code==422
