import {describe,it,expect,vi} from 'vitest';
import {AgentVerseStore,validateProjection} from './adapter';
import {parityFixture} from './fixture';
describe('live projection boundary',()=>{
 it('preserves complete upstream room and agent state without inventing agents',()=>{
  const store=new AgentVerseStore();const s=parityFixture();store.applySnapshot(s);
  expect(store.snapshot).toBe(s);expect(store.agent('agent-1')?.name).toBe('Developer');expect(store.agentsInRoom('coding')).toHaveLength(3);expect(store.mock).toBe(false);
 });
 it('rejects demonstration or malformed/orphan agent snapshots',()=>{
  const s=parityFixture();expect(()=>validateProjection({...s,meta:{...s.meta,demo:true}})).toThrow();
  expect(()=>validateProjection({...s,agents:[{...s.agents[0],roomId:'missing'}]})).toThrow();
  expect(()=>validateProjection({})).toThrow();
 });
 it('retains revision order and completed persistent agents',()=>{
  const store=new AgentVerseStore();const s=parityFixture();store.applySnapshot({...s,rev:4,agents:s.agents.map(a=>({...a,status:'idle'}))});store.applySnapshot({...s,rev:3});
  expect(store.snapshot?.rev).toBe(4);expect(store.agent('agent-1')?.status).toBe('idle');expect(store.snapshot?.agents).toHaveLength(4);
 });
 it('fetches initial real snapshot then connects SSE',async()=>{
  const store=new AgentVerseStore();const connect=vi.spyOn(store,'connect').mockImplementation(()=>{});
  const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>parityFixture()});await store.bootstrap(fetcher);
  expect(fetcher.mock.calls[0][0]).toBe('/api/office/snapshot');expect(connect).toHaveBeenCalledOnce();expect(store.snapshot?.agents).toHaveLength(4);
 });
 it('reports failed bootstrap and connects for recovery without demo fallback',async()=>{
  const store=new AgentVerseStore();const connect=vi.spyOn(store,'connect').mockImplementation(()=>{});
  await expect(store.bootstrap(vi.fn().mockResolvedValue({ok:false,status:503}))).rejects.toThrow('503');
  expect(connect).toHaveBeenCalledOnce();expect(store.snapshot).toBeNull();expect(store.mock).toBe(false);
 });
});
