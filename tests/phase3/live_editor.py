"""Actual role-mapped template and node-edit persistence checks; no run is faked."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(args):
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 prior=json.loads(Path(args.browser_result).read_text());ws=prior['workspace_id']
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1920,'height':1080});errors=[];failures=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  def api(path,data=None,method='GET'):
   r=page.request.fetch(args.base+path,data=data,method=method);assert r.ok,(r.status,r.text());return r.json()
  agents=api('/api/agents?workspace_id='+ws);writer=agents[0]
  reviewer=api('/api/agents',{'workspace_id':ws,'name':'QA Ungranted Reviewer','role':'Reviewer','tool_grants':[]},'POST')
  baseline={a['id']:{'role':a['role'],'tool_grants':a['tool_grants']} for a in (writer,reviewer)}
  page.add_init_script('localStorage.setItem("agentverse.workspace",'+json.dumps(ws)+')')
  page.goto(args.base+'/control/#workflows');page.get_by_label('Workflow template',exact=True).select_option('operations-report')
  page.get_by_label('Template role Analyst',exact=True).select_option(writer['id']);page.get_by_label('Template role Reviewer',exact=True).select_option(reviewer['id'])
  warning=page.get_by_text('Agent chưa có grant artifacts.write_text',exact=False);assert warning.is_visible()
  page.screenshot(path=str(out/'template-mapping-warning-1920.png'),full_page=True)
  before=api('/api/workflows?workspace_id='+ws)
  page.get_by_role('button',name='Tạo workflow từ template',exact=True).click()
  page.get_by_text('Đã tạo workflow từ template; có thể chỉnh sửa đồ thị.',exact=False).wait_for()
  created=[w for w in api('/api/workflows?workspace_id='+ws) if w['id'] not in {w['id'] for w in before}];assert len(created)==1,created
  template=next(t for t in api('/api/workflow-templates') if t['id']=='operations-report')
  graph=created[0]['graph'];nodes=[n for n in graph['nodes'] if n['type']=='agent'];assert [n['agent_id'] for n in nodes]==[writer['id'],reviewer['id']]
  assert [n['instructions'] for n in nodes]==[s['instructions'] for s in template['steps']]
  current={a['id']:{'role':a['role'],'tool_grants':a['tool_grants']} for a in api('/api/agents?workspace_id='+ws)}
  assert all(current[id]==value for id,value in baseline.items()),'Template silently mutated roles/grants'
  page.set_viewport_size({'width':1366,'height':768})
  page.get_by_role('button',name='Fit View',exact=True).click()
  page.locator('.react-flow__node').filter(has_text=writer['name']).click()
  text=page.get_by_label('Instructions của node',exact=True);text.fill('UI_SAVED_CUSTOM_OBJECTIVE: list operational risks only from supplied documents.')
  page.get_by_label('File kết quả',exact=True).fill('custom-operations.md')
  page.screenshot(path=str(out/'custom-node-edit-1366.png'),full_page=True)
  before_ids={w['id'] for w in api('/api/workflows?workspace_id='+ws)}
  page.get_by_role('button',name='Lưu đồ thị',exact=True).click();page.get_by_text('Đã lưu phiên bản workflow mới',exact=False).wait_for()
  saved=[w for w in api('/api/workflows?workspace_id='+ws) if w['id'] not in before_ids];assert len(saved)==1,saved
  node=next(n for n in saved[0]['graph']['nodes'] if n['id']==nodes[0]['id']);assert node['instructions'].startswith('UI_SAVED_CUSTOM_OBJECTIVE') and node['deliverable']=={'filename':'custom-operations.md'},node
  page.reload();page.get_by_label('Workflow',exact=True).select_option(saved[0]['id']);page.locator('.react-flow__node').filter(has_text=writer['name']).click()
  assert page.get_by_label('Instructions của node',exact=True).input_value()==node['instructions']
  assert page.get_by_label('File kết quả',exact=True).input_value()=='custom-operations.md'
  result={'passed':not errors and not failures,'application_sha':args.sha,'workspace_id':ws,'created_workflow_id':created[0]['id'],'saved_workflow_id':saved[0]['id'],'node':node,'checks':['actual role mapping creates editable template graph','missing artifact grant warning visible','roles and grants unchanged','node instruction and filename saved as new workflow','reload preserves saved instruction and filename'],'page_errors':errors,'http_failures':failures}
  (out/'live-editor.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));browser.close()
  return result['passed']

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:3000');p.add_argument('--output',required=True);p.add_argument('--sha',required=True);p.add_argument('--browser-result',required=True);raise SystemExit(0 if run(p.parse_args()) else 1)
