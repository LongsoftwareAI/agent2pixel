"""Mounted API -> catalog grants -> actual Decimal tool node -> agent handoff."""
import time
from fastapi.testclient import TestClient
from services.api.main import create_app


def test_mounted_data_tool_to_company_agent(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        workspace=c.post('/api/workspaces',json={'name':'CSV company integration'}).json()
        source=c.post('/api/sources',json={'workspace_id':workspace['id'],'name':'sales','content':'amount\n0.1\n0.2\n','media_type':'text/csv'})
        assert source.status_code==200,source.text
        source=source.json()
        assert {'sources.read','csv.analyze','web.read'} <= {t['id'] for t in c.get('/api/catalog').json()['tools']}
        agent=c.post('/api/agents',json={'workspace_id':workspace['id'],'name':'Analyst','role':'Analyst','tool_grants':[{'id':'csv.analyze','allow':True}]}).json()
        nodes=[{'id':'start','type':'start'}, {'id':'numbers','type':'tool','agent_id':agent['id'],'tool':{'id':'csv.analyze','payload':{'source_id':source['id'],'column':'amount'}}}, {'id':'report','type':'agent','agent_id':agent['id'],'instructions':'State actual computed total, no invented calculation.'}, {'id':'end','type':'end'}]
        workflow=c.post('/api/workflows',json={'workspace_id':workspace['id'],'name':'actual CSV handoff','graph':{'nodes':nodes,'edges':[{'source':a['id'],'target':b['id']} for a,b in zip(nodes,nodes[1:])]}})
        assert workflow.status_code==200,workflow.text
        response=c.post('/api/workflows/'+workflow.json()['id']+'/runs',json={'input':'ORIGINAL_BUSINESS_BRIEF'})
        assert response.status_code==200,response.text
        id=response.json()['id']
        for _ in range(300):
            run=c.get('/api/runs/'+id).json()
            if run['state'] in ('completed','failed'):break
            time.sleep(.01)
        assert run['state']=='completed',run
        evidence=c.get('/api/runs/'+id+'/tool-results').json()
        assert len(evidence)==1 and evidence[0]['status']=='completed'
        import json
        result=json.loads(evidence[0]['output'])['result']
        assert result['columns']['amount']['sum']=='0.3'
        assert result['sha256']==source['sha256']
        report=next(t for t in run['tasks'] if t['node_id']=='report')
        assert 'UNTRUSTED_TOOL_DATA' in report['input'] and source['id'] in report['input']
        assert 'ORIGINAL_BUSINESS_BRIEF' in report['output']
