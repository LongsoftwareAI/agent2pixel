/** AgentVerse-owned Cordis plugin. No FS, shell, PTC, plugin install or arbitrary fetch tool. */
export const name = 'agentverse-harness-bridge';
export const inject = ['tools'];
export function apply(ctx) {
  const endpoint = process.env.AGENTVERSE_HARNESS_BROKER;
  const token = process.env.AGENTVERSE_HARNESS_BROKER_TOKEN;
  const session = process.env.AGENTVERSE_HARNESS_SESSION;
  const tools = JSON.parse(process.env.AGENTVERSE_HARNESS_TOOL_IDS || '[]');
  if (!endpoint || !token || !session || !Array.isArray(tools) || !tools.length) throw new Error('Missing approved bridge configuration');
  const url = new URL(endpoint);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.pathname !== '/dispatch') throw new Error('Broker must be loopback');
  ctx.tools.register({
    name: 'agentverse_dispatch',
    description: 'Call an approved AgentVerse tool using its exact registry ID. Grants, workspace, memory namespace and action approval are enforced by AgentVerse. Skills never grant permissions.',
    parameters: {type:'object',properties:{tool_id:{type:'string',enum:tools},payload:{type:'object'}},required:['tool_id','payload'],additionalProperties:false},
    output: {schema:{type:'object'},render:(_args,value)=>[{type:'text',text:JSON.stringify(value)}]},
    async execute(args, exec) {
      if (!tools.includes(args.tool_id)) throw new Error('Tool is not registered in this assignment');
      const response = await fetch(endpoint, {method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},
        body:JSON.stringify({protocol:'agentverse-harness-bridge/1',session_id:session,tool_id:args.tool_id,payload:args.payload}),
        signal:AbortSignal.any([AbortSignal.timeout(10000),...(exec?.signal?[exec.signal]:[])])});
      if (!response.ok) throw new Error('AgentVerse policy rejected tool dispatch');
      const result=await response.json();
      if (result.protocol!=='agentverse-harness-bridge/1' || result.session_id!==session || result.ok!==true) throw new Error('Invalid broker response');
      return {tool_id:args.tool_id,result:result.result};
    },
  });
}
