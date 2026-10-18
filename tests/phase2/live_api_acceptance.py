"""Independent live API acceptance; deterministic Brain is labeled, real tools execute."""
import argparse
import hashlib
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def run(base, output, sha):
    def request(path, body=None, method=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(base+path, data=data, method=method, headers={'Content-Type':'application/json', **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:return r.status, json.load(r)
        except urllib.error.HTTPError as e:return e.code, json.load(e)
    def ok(path, body=None, method=None):
        status, value=request(path,body,method)
        assert status==200,(path,status,value)
        return value
    ws=ok('/api/workspaces',{'name':'Independent Phase2 QA '+str(time.time_ns())})
    other=next(w for w in ok('/api/workspaces') if w['id']!=ws['id'])
    agents=[]
    for i,role in enumerate(('Planner','Developer','Reviewer')):
        agents.append(ok('/api/agents',dict(workspace_id=ws['id'],name='QA '+role,role=role,workstation={'x':3+i*5,'y':5})))
    developer=agents[1]
    ok('/api/agents/'+agents[0]['id'],{'tool_grants':[{'id':'memory.read','allow':True}],'memory_config':{'scope':'agent'}},'PATCH')
    ok('/api/agents/'+developer['id'],{'tool_grants':[{'id':t,'allow':True,'approval_required':True} for t in ('artifacts.write_python','tests.run_pytest')]},'PATCH')
    ok('/api/agents/'+agents[2]['id'],{'tools':['documents.list','documents.read'],'skill_bindings':[{'id':'code-report','version':1}]},'PATCH')
    ok('/api/memories',dict(workspace_id=ws['id'],scope='agent',agent_id=agents[0]['id'],content='QA_SCOPED_PRIVATE'))
    status,_=request('/api/memories?workspace_id='+other['id']+'&scope=agent&agent_id='+agents[0]['id']);assert status in (403,422),status
    status,_=request('/api/memories',dict(workspace_id=other['id'],scope='agent',agent_id=agents[0]['id'],content='DENY'));assert status in (403,422),status
    nodes=[{'id':'start','type':'start'}]+[{'id':a['role'].lower(),'type':'agent','agent_id':a['id']} for a in agents]+[{'id':'end','type':'end'}]
    wf=ok('/api/workflows',{'workspace_id':ws['id'],'name':'QA actual tools','graph':{'nodes':nodes,'edges':[{'source':a['id'],'target':b['id']} for a,b in zip(nodes,nodes[1:])]}})
    baseline=ok('/api/office/snapshot')['seq']
    actions=[{'agent_id':developer['id'],'tool':'artifacts.write_python','payload':{'filename':filename,'template':template}} for filename,template in [('calculator.py','calculator-v1'),('test_calculator.py','calculator-tests-v1')]]+[{'agent_id':developer['id'],'tool':'tests.run_pytest','payload':{}}]
    result=ok('/api/workflows/'+wf['id']+'/runs',{'input':'Independent QA real sandbox artifact and pytest','actions':actions})
    run_id=result['id']; approvals=[]
    for _ in range(1000):
        result=ok('/api/runs/'+run_id)
        if result['state']=='waiting_approval':
            pending=[a for a in ok('/api/runs/'+run_id+'/approvals') if a['status']=='pending']
            if pending:
                a=pending[0];approvals.append(a['id']);ok('/api/approvals/'+a['id']+'/decision',{'decision':'approved'})
        if result['state'] in ('completed','failed','cancelled'):break
        time.sleep(.03)
    assert result['state']=='completed',result
    assert len(approvals)==3 and len(set(approvals))==3,approvals
    status,_=request('/api/approvals/'+approvals[0]+'/decision',{'decision':'approved'});assert status==409,status
    assert len(result['artifacts'])==3 and result['artifacts'][-1]['exit_code']==0,result
    assert '2 passed' in result['artifacts'][-1]['report'] and '2 passed' in result['tasks'][-1]['output'],result
    artifacts=[]
    for artifact in result['artifacts'][:2]:
        file=Path(ws['root_path'])/artifact['path']
        digest=hashlib.sha256(file.read_bytes()).hexdigest()
        assert digest==artifact['sha256'],artifact
        artifacts.append({'path':artifact['path'],'sha256':digest})
    events=ok('/api/runs/'+run_id+'/events')
    expected=[e['seq'] for e in events]
    assert len(expected)==len(set(expected)) and expected==sorted(expected)
    assert not [e for e in ok('/api/events?workspace_id='+other['id']+'&after='+str(baseline)) if e['run_id']==run_id]
    feed=[]
    req=urllib.request.Request(base+'/api/office/stream?after='+str(baseline)+'&workspace_id='+ws['id'])
    with urllib.request.urlopen(req, timeout=15) as response:
        event=None
        for raw in response:
            line=raw.decode().strip()
            if line.startswith('event: '):event=line[7:]
            if line.startswith('data: ') and event=='feed':
                feed+=json.loads(line[6:])
                observed=[f['activity']['seq'] for f in feed if f['activity']['runId']==run_id]
                if observed==expected:break
    observed=[f['activity']['seq'] for f in feed if f['activity']['runId']==run_id]
    assert observed==expected,(observed,expected)
    status,_=request('/api/workspaces',{'name':'DENY'},headers={'Origin':'https://attacker.invalid'});assert status==403,status
    status,_=request('/api/office/stream',headers={'Origin':'https://attacker.invalid'});assert status==403,status
    counts={kind:sum(e['event_type']==kind for e in events) for kind in ['task.completed','tool.completed','skill.activated','memory.read','approval.required']}
    assert counts['memory.read'] >= 1,counts
    evidence={'passed':True,'application_sha':sha,'brain':'deterministic mock adapter; no live model asserted','runtime':'actual LangGraph + SQLite + sandbox writes + pytest subprocess','workspace_id':ws['id'],'run_id':run_id,'state':result['state'],'artifacts':artifacts,'test_report':result['artifacts'][-1]['report'],'event_counts':counts,'sse_expected':expected,'sse_observed':observed,'approval_ids':approvals,'checks':['workspace scoped memory read/write denied','event isolation','reused approval denied','artifact hashes match actual files','Reviewer output includes real pytest report','exact fresh-run SSE replay','remote Origin mutation denied','remote Origin SSE denied']}
    Path(output).write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8000');p.add_argument('--output',required=True);p.add_argument('--sha',required=True);a=p.parse_args();run(a.base,a.output,a.sha)
