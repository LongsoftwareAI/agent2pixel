"""Actual pointer/form office furniture + character persistence acceptance."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(base, output, sha):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1366,'height':768});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base);page.wait_for_function("window.agentverseOffice?.store.connection==='open'")
  page.get_by_text('Edit room furniture',exact=True).click();page.wait_for_timeout(300)
  room=page.get_by_label('Furniture room',exact=True).input_value()
  endpoint=base+'/api/office/rooms/'+room+'/furniture'
  initial=page.request.get(endpoint).json()
  assert not initial['items'],'QA must preserve pre-existing decorations; choose an empty room'
  page.get_by_label('Furniture kind',exact=True).select_option('floor_lamp')
  points=page.evaluate('''async room=>{const {validateFurniture}=await import('/src/furniture.ts');const b=agentverseOffice.world.roomLayout(room),points=[];for(let y=2;y<b.rect.h-1;y++)for(let x=1;x<b.rect.w-1;x++){try{validateFurniture(b,[{id:'qa-find',kind:'floor_lamp',x,y}]);points.push({x,y});}catch{}}return points.slice(0,2)}''',room)
  assert len(points)==2,points
  def fill(point):
   page.get_by_label('Tile X',exact=True).fill(str(point['x']));page.get_by_label('Tile Y',exact=True).fill(str(point['y']))
  fill(points[0]);page.get_by_role('button',name='Add',exact=True).click()
  page.wait_for_function("document.querySelector('.av-furniture-toggle [role=status]').textContent.startsWith('Saved')")
  added=page.request.get(endpoint).json();assert len(added['items'])==1 and added['version']==initial['version']+1,added
  page.get_by_role('button',name='Add',exact=True).click();page.wait_for_timeout(300)
  rejected=page.locator('.av-furniture-toggle [role=status]').inner_text()
  assert 'overlap' in rejected.lower(),rejected
  assert page.request.get(endpoint).json()==added
  fill(points[1]);page.get_by_role('button',name='Move selected',exact=True).click();page.wait_for_timeout(400)
  moved=page.request.get(endpoint).json();assert moved['items'][0]['x']==points[1]['x'] and moved['items'][0]['y']==points[1]['y'],moved
  page.reload();page.wait_for_function("window.agentverseOffice?.store.connection==='open'")
  page.get_by_text('Edit room furniture',exact=True).click();page.wait_for_timeout(400)
  assert page.request.get(endpoint).json()==moved
  page.screenshot(path=str(out/'live-furniture-persisted-1366.png'))
  page.get_by_role('button',name='Delete selected',exact=True).click();page.wait_for_timeout(400)
  assert page.request.get(endpoint).json()['items']==[]
  page.get_by_text('Edit room furniture',exact=True).click()
  agent=page.evaluate('agentverseOffice.store.snapshot.agents[0]')
  page.evaluate('(id)=>agentverseOffice.world.focusAgent(id)',agent['id']);page.wait_for_timeout(500)
  point=page.evaluate('''id=>{const w=agentverseOffice.world,c=w.debug.sim.chars.get(id);return w.debug.camera.worldToScreen(c.x,c.y-10)}''',agent['id'])
  page.mouse.click(point['x'],point['y']);page.get_by_role('button',name='Edit character',exact=True).click()
  page.locator('.ui-char__name').fill('QA Appearance')
  page.get_by_role('button',name='Randomize',exact=True).click()
  page.locator('.ui-char').get_by_role('button',name='Save',exact=True).click();page.wait_for_timeout(700)
  edited=page.request.get(base+'/api/office/agents/'+agent['id']).json()['agent'];assert edited['name']=='QA Appearance' and edited['custom'],edited
  page.reload();page.wait_for_function("window.agentverseOffice?.store.connection==='open'")
  assert page.request.get(base+'/api/office/agents/'+agent['id']).json()['agent']['seed']==edited['seed']
  page.screenshot(path=str(out/'live-character-persisted-1366.png'))
  # Restore prior user-owned appearance/name via supported endpoint after recording proof.
  response=page.request.put(base+'/api/agents/'+agent['id']+'/character',data={'name':agent['name'],'seed':agent['seed'],'parts':agent.get('parts',{})});assert response.ok
  if not agent['custom']:assert page.request.delete(base+'/api/agents/'+agent['id']+'/character').ok
  result={'passed':not errors,'application_sha':sha,'fixture':False,'room_id':room,'initial':initial,'added':added,'moved':moved,'collision_rejection':rejected,'reload_persisted':True,'appearance_agent_id':agent['id'],'appearance_seed':edited['seed'],'appearance_reload_persisted':True,'restored_original_user_data':True,'page_errors':errors}
  (out/'live-office-edit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));browser.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:3000');p.add_argument('--output',required=True);p.add_argument('--sha',required=True);a=p.parse_args();run(a.base,a.output,a.sha)
