"""Real failed/cancelled execution projected into Habblaud drawer; no injected snapshots."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(base,output,sha):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1366,'height':768});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  def req(path,data=None,method='GET'):
   r=page.request.fetch(base+path,method=method,data=data);assert r.ok,(path,r.status,r.text());return r.json()
  ws=req('/api/workspaces',{'name':'QA failure and cancellation '+str(time.time_ns())},'POST')
  a=req('/api/agents',{'workspace_id':ws['id'],'name':'QA Missing Key','execution':{'engine':'deepseek_harness'},'brain':{'provider':'deepseek','model':'deepseek-v4-flash','secret_ref':'AGENTVERSE_QA_INTENTIONALLY_ABSENT_KEY'}},'POST')
  graph={'nodes':[{'id':'start','type':'start'},{'id':'work','type':'agent','agent_id':a['id']},{'id':'end','type':'end'}],'edges':[{'source':'start','target':'work'},{'source':'work','target':'end'}]}
  w=req('/api/workflows',{'workspace_id':ws['id'],'name':'QA error states','graph':graph},'POST')
  run=req('/api/workflows/'+w['id']+'/runs',{'input':'Explicit configuration failure; do not call provider'},'POST')
  for _ in range(200):
   run=req('/api/runs/'+run['id'])
   if run['state']=='failed':break
   time.sleep(.03)
  assert run['state']=='failed' and 'secret' in run['error'].lower(),run
  page.goto(base);page.wait_for_function("window.agentverseOffice?.store.connection==='open'")
  def select():
   page.evaluate('(id)=>agentverseOffice.world.focusAgent(id)',a['id']);page.wait_for_timeout(700)
   pt=page.evaluate('''id=>{const w=agentverseOffice.world,c=w.debug.sim.chars.get(id);return w.debug.camera.worldToScreen(c.x,c.y-10)}''',a['id'])
   page.mouse.click(pt['x'],pt['y']);page.wait_for_timeout(400)
  select();snapshot=page.request.get(base+'/api/office/agents/'+a['id']).json()['agent']
  assert snapshot['domainStatus']=='error' and snapshot['tasks'][-1]['status']=='failed',snapshot
  assert page.get_by_text('Execution failed',exact=True).is_visible()
  page.screenshot(path=str(out/'live-failed-drawer-1366.png'))
  text=page.locator('body').inner_text();unknown_usage=text.count('N/A')>=2
  req('/api/agents/'+a['id'],{'execution':{'engine':'langchain'},'brain':{'provider':'mock','model':'deterministic'},'tool_grants':[{'id':'artifacts.write_python','allow':True,'approval_required':True}]},'PATCH')
  cancel=req('/api/workflows/'+w['id']+'/runs',{'input':'Cancel at real approval wait','actions':[{'agent_id':a['id'],'tool':'artifacts.write_python','payload':{'filename':'calculator.py','template':'calculator-v1'}}]},'POST')
  for _ in range(200):
   cancel=req('/api/runs/'+cancel['id'])
   if cancel['state']=='waiting_approval':break
   time.sleep(.03)
  assert cancel['state']=='waiting_approval',cancel
  cancel=req('/api/runs/'+cancel['id']+'/cancel',{},'POST');assert cancel['state']=='cancelled',cancel
  page.wait_for_function("(id)=>agentverseOffice.store.agent(id)?.tasks.some(t=>t.status==='cancelled')",arg=a['id'])
  page.screenshot(path=str(out/'live-cancelled-drawer-1366.png'))
  snapshot=req('/api/office/agents/'+a['id'])['agent'];assert any(t['status']=='cancelled' for t in snapshot['tasks'])
  result={'passed':not errors and unknown_usage,'application_sha':sha,'fixture':False,'failed_run_id':run['id'],'failed_error':run['error'],'cancelled_run_id':cancel['id'],'failed_badge_visible':True,'cancelled_task_projected':True,'unknown_usage_NA':unknown_usage,'agent_stats':snapshot['stats'],'page_errors':errors}
  (out/'live-office-status.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));browser.close()
  return result['passed']

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:3000');p.add_argument('--output',required=True);p.add_argument('--sha',required=True);a=p.parse_args();raise SystemExit(0 if run(a.base,a.output,a.sha) else 1)
