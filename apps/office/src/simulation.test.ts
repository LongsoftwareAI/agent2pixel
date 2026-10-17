import {describe,it,expect,vi} from 'vitest';
import {Sim} from '../../../vendor/habblaud/client/src/world/sim/sim';
import type {ArtModule} from '../../../vendor/habblaud/client/src/art/api';
import {DEFAULT_WORLD_OPTIONS} from '../../../vendor/habblaud/client/src/world/api';
import {parityFixture,FIXTURE_TIME} from './fixture';
// Sim geometry only requires theme + appearance; no canvas or fabricated backend is needed here.
const art={
 appearanceFromSeed:()=>({skin:'#f0c8a0',hair:'#3a2a20',hairStyle:'short',eyes:'#222',top:'#3f7fd8',topAccent:'#fff',topStyle:'tshirt',bottom:'#333',shoes:'#111',accessory:'none',accessoryColor:'#000',lanyard:null,look:'m'}),
 roomTheme:()=>({carpet:'#4f6d8f',carpet2:'#486685',wall:{base:'#e6e2da',trim:'#9a8f80',pattern:'plain'},accent:'#3f7fd8',deskVariant:'wood',chairVariant:'black'}),
} as unknown as ArtModule;
const newSim=()=>new Sim(art,()=>({...DEFAULT_WORLD_OPTIONS,liveliness:'lively',ambientSocial:false}),null);
describe('backend-driven office state',()=>{
 it('shows working/waiting/idle from snapshots without completing tasks itself',()=>{
  const sim=newSim();const snap=parityFixture();sim.applySnapshot(snap,FIXTURE_TIME);sim.update(1/30,FIXTURE_TIME+34);
  expect(sim.chars.get('agent-0')?.pose).toBe('type');
  sim.applySnapshot({...snap,rev:2,agents:snap.agents.map(a=>({...a,status:'waiting',statusSince:FIXTURE_TIME+100}))},FIXTURE_TIME+100);
  sim.update(1/30,FIXTURE_TIME+134);expect(sim.chars.get('agent-0')?.pose).toBe('raise_hand');
  sim.applySnapshot({...snap,rev:3,agents:snap.agents.map(a=>({...a,status:'idle'}))},FIXTURE_TIME+200);
  expect(sim.chars.size).toBe(4);expect(sim.chars.get('agent-0')?.info.tasks).toEqual([]);
 });
 it('does not invent social events, coins or rewards during idle activity or backend completion',()=>{
  const sim=newSim();const snap=parityFixture();const sync=vi.spyOn(sim.social,'syncAgent');const rewards=vi.spyOn(sim.social,'turnDone');
  const update=vi.spyOn(sim.social,'update');const housekeeping=vi.spyOn(sim.social,'housekeeping');const initiate=vi.spyOn(sim.social,'tryInitiate');
  sim.applySnapshot({...snap,agents:snap.agents.map(a=>({...a,status:'idle'}))},FIXTURE_TIME);
  for(let i=0;i<1800;i++) sim.update(1/30,FIXTURE_TIME+i*1000/30);
  sim.applySnapshot({...snap,rev:2,agents:snap.agents.map(a=>({...a,status:'idle',activity:{id:'done-'+a.id,kind:'done',icon:'✓',text:'Completed by backend',at:FIXTURE_TIME+60000}}))},FIXTURE_TIME+60000);
  expect(sync).not.toHaveBeenCalled();expect(rewards).not.toHaveBeenCalled();expect(update).not.toHaveBeenCalled();expect(housekeeping).not.toHaveBeenCalled();expect(initiate).not.toHaveBeenCalled();expect(sim.social.events).toEqual([]);
 });
});
