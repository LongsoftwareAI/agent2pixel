/** Same-origin navigation only: callers supply registry IDs, never URL fragments. */
export function consoleLink(page: string, agentId?: string, workspaceId?: string): string {
 if (!['overview','agents','workboard','workflows','runs','settings'].includes(page)) throw new Error('Unknown console page');
 const query = new URLSearchParams();
 if(agentId) query.set('agent', agentId);
 if(workspaceId) query.set('workspace', workspaceId);
 return `/#${page}${query.size ? `?${query}` : ''}`;
}
/** Office projection room IDs are workspace IDs; never reuse a stale selected workspace. */
export function selectedAgentLink(id: string, agents: readonly {id:string;roomId:string}[]): string | null {
 const agent = agents.find(a=>a.id===id);
 return agent ? consoleLink('agents', agent.id, agent.roomId) : null;
}
