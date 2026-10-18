import {describe,it,expect} from 'vitest';
import {consoleLink,selectedAgentLink} from './navigation';
import {officeBase,officeAssetPaths} from '../host-config';
describe('office console boundary',()=>{
 it('links selected agents to their actual workspace, escaping IDs',()=>{
  const link=selectedAgentLink('agent &?#',[{id:'agent &?#',roomId:'workspace /?#'}]);
  const url=new URL(link!,'http://localhost:3000');
  const params=new URLSearchParams(url.hash.split('?')[1]);
  expect(url.pathname).toBe('/');expect(params.get('agent')).toBe('agent &?#');expect(params.get('workspace')).toBe('workspace /?#');
 });
 it('does not expose stale selections or accept external navigation',()=>{
  expect(selectedAgentLink('removed',[])).toBeNull();expect(()=>consoleLink('https://example.com')).toThrow();expect(consoleLink('settings')).toBe('/#settings');
 });
 it('supports configured local bases and rejects malformed/external bases',()=>{
  expect(officeBase()).toBe('/office/');expect(officeBase('/')).toBe('/');expect(officeBase('/nested/office/')).toBe('/nested/office/');
  for(const value of ['//example.com/','https://example.com/','/office','/../','/x?y/'])expect(()=>officeBase(value)).toThrow();
 });
 it('rebases native public artwork including dynamic image paths without changing APIs or URLs',()=>{
  const source="img.src = `/assets/${file}`; fetch('/assets/manifest.json'); icon: '/assets/brand/a.png'; fetch('/api/office/snapshot'); href='https://example.com/assets/x'";
  const adapted=officeAssetPaths(source,'/office/');
  expect(adapted).toContain('`/office/assets/${file}`');expect(adapted).toContain("'/office/assets/manifest.json'");expect(adapted).toContain("'/office/assets/brand/a.png'");expect(adapted).toContain("'/api/office/snapshot'");expect(adapted).toContain("https://example.com/assets/x");
 });
});
