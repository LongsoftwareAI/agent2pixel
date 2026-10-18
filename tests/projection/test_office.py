from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.api.store import Store
from services.api.office_projection import project,project_feed,create_office_router


def setup(tmp_path):
    s=Store(tmp_path)
    s.put('workspace',dict(id='coding',name='Coding',root_path=str(tmp_path/'coding'),created_at='2026-10-17T00:00:00Z'))
    s.put('workspace',dict(id='research',name='Research',root_path=str(tmp_path/'research'),created_at='2026-10-17T00:00:00Z'))
    s.put('agent',dict(id='planner',workspace_id='coding',name='Planner',enabled=True,status='completed',role='Planner',brain={'provider':'mock','model':'deterministic'}))
    s.put('agent',dict(id='other',workspace_id='research',name='Other',enabled=True,status='idle',brain={}))
    app=FastAPI();app.state.store=s;app.include_router(create_office_router(app))
    return s,TestClient(app)


def test_snapshot_real_state_and_workspace_scope(tmp_path):
    s,client=setup(tmp_path)
    e=s.event('coding','task.completed',{'output':'PRIVATE OUTPUT NOT IN OFFICE FEED'},agent='planner')
    value=client.get('/api/office/snapshot?workspace_id=coding').json()
    assert value['seq']==e['seq'] and value['meta']['demo'] is False
    assert len(value['agents'])==len(value['rooms'])==1
    agent=value['agents'][0]
    assert agent['status']=='idle' and agent['domainStatus']=='completed'
    assert agent['provider']=='agentverse' and value['accounts']==[]
    assert agent['activity']['kind']=='done' and agent['usageKnown'] is False
    assert agent['stats']['usageKnown'] is False
    assert 'PRIVATE OUTPUT' not in str(value)
    assert client.get('/api/office/snapshot?workspace_id=missing').status_code==404
    assert client.get('/api/office/agents/planner').json()['history'][-1]['seq']==e['seq']
    assert client.get('/api/office/agents/missing').status_code==404
    s.db.close()


def test_character_roundtrip_validation_and_revision(tmp_path):
    s,client=setup(tmp_path)
    response=client.put('/api/agents/planner/character',json={'name':'Mai','seed':42,'parts':{'hairStyle':'bob','skin':'#aabbcc'}})
    assert response.status_code==200
    a=project(s,'coding')['agents'][0]
    assert a['name']=='Mai' and a['seed']==42 and a['parts']['hairStyle']=='bob'
    assert project(s)['seq']>0
    for bad in [{'name':'','seed':1},{'name':'Mai','seed':True},{'name':'Mai','seed':1,'parts':{'shell':'rm -rf'}},{'name':'Mai','seed':1,'parts':{'skin':'red'}}]:
        assert client.put('/api/agents/planner/character',json=bad).status_code==422
    assert client.delete('/api/agents/planner/character').status_code==200
    assert project(s,'coding')['agents'][0]['parts']=={}
    s.db.close()


def test_feed_cursor_and_safety_surface(tmp_path):
    s,client=setup(tmp_path)
    first=s.event('coding','task.started',agent='planner')
    second=s.event('coding','task.failed',{'raw':'sensitive'},agent='planner')
    feed=project_feed(s,first['seq'],'coding')
    assert len(feed)==1 and feed[0]['activity']['seq']==second['seq']
    assert feed[0]['activity']['error'] and 'sensitive' not in str(feed)
    assert project_feed(s,0,'research')==[]
    caps=client.get('/api/access').json()
    assert caps['local'] and not any(caps[k] for k in ['world','spawn','terminal','permissions','messages'])
    assert client.get('/api/office/stream',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/office/stream',headers={'Last-Event-ID':'bad'}).status_code==400
    assert client.get('/api/office/feed?after=-1').status_code==422
    s.db.close()


def test_replay_pages_never_drop_earliest_missing_event(tmp_path):
    s,client=setup(tmp_path)
    for _ in range(205):
        s.event('coding','task.progress',agent='planner')
    page=project_feed(s,0,'coding')
    assert len(page)==200 and page[0]['activity']['seq']==1
    second=project_feed(s,page[-1]['activity']['seq'],'coding')
    assert len(second)==5 and second[-1]['activity']['seq']==205
    assert client.get('/api/office/stream',headers={'Last-Event-ID':'-1'}).status_code==400
    s.db.close()


def test_room_slots_seed_and_terminal_task_semantics(tmp_path):
    s,client=setup(tmp_path)
    s.put('run',dict(id='run',workspace_id='coding',tasks=[dict(id='bad',agent_id='planner',node_id='review',state='failed'),dict(id='cancel',agent_id='planner',node_id='review',state='cancelled')]))
    a=s.get('agent','planner');a['status']='error';a['appearance']={'seed':'configured-text-seed'};s.put('agent',a)
    snapshot=project(s)
    agent=next(a for a in snapshot['agents'] if a['id']=='planner')
    assert [t['status'] for t in agent['tasks']]==['failed','cancelled']
    assert agent['domainStatus']=='error' and type(agent['seed'])==int
    assert agent['startedAt']>0
    other=project(s,'research')['rooms'][0]
    assert other['slot']==1 and 1<=other['seed']<=8
    assert other['customFurniture']==[] and other['layoutVersion']==0
    layout=client.get('/api/office/rooms/coding/furniture')
    assert layout.status_code==200 and layout.json()['version']==0
    s.db.close()
