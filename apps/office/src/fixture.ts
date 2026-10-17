import type { AgentInfo, OfficeSnapshot } from '../../../vendor/habblaud/shared/types';
export const FIXTURE_TIME = 1781524800000; // 2026-06-15 12:00:00 UTC
export function parityFixture(): OfficeSnapshot {
 const rooms = [
  {id:'coding',name:'Coding',path:'/workspace/coding',slot:0,seed:42,createdAt:FIXTURE_TIME},
  {id:'research',name:'Research',path:'/workspace/research',slot:1,seed:99,createdAt:FIXTURE_TIME},
 ];
 const agents: AgentInfo[] = ['Planner','Developer','Reviewer','Researcher'].map((name,i) => ({
  id:`agent-${i}`,kind:'main',provider:'agentverse',roomId:i===3?'research':'coding',name,look:i%2?'f':'m',role:name,
  sessionId:`session-${i}`,account:'agentverse',status:'working',title:'Visual parity fixture — not live execution',
  activity:{id:`activity-${i}`,kind:i===1?'edit':i===2?'test':'read',icon:i===1?'✏️':i===2?'🧪':'📖',text:i===1?'Editing workflow.py':i===2?'Running tests':'Reading requirements',at:FIXTURE_TIME},
  recent:[],tasks:[],startedAt:FIXTURE_TIME,statusSince:FIXTURE_TIME,lastEventAt:FIXTURE_TIME,
  stats:{toolCalls:0,tokensIn:0,tokensOut:0,subagents:0},seed:[1705,92,101,584][i],
 }));
 return {rev:1,serverTime:FIXTURE_TIME,rooms,agents,accounts:[],meta:{demo:false,sources:[],startedAt:FIXTURE_TIME,version:'0.2.0-fixture',terminal:false,messages:false}};
}
