import asyncio
from collections import deque
from services.api.store import now, uid
from services.worker.adapters import run_brain
from services.worker.tools import tool_context


def validate_graph(graph, store, workspace):
    errors = []
    if not isinstance(graph,dict): return ['Graph must be an object']
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    if not isinstance(nodes, list) or not isinstance(edges, list) or not 2 <= len(nodes) <= 32:
        return ['Graph requires 2–32 nodes']
    if any(not isinstance(n, dict) or not isinstance(n.get('id'), str) for n in nodes):
        return ['Node IDs must be strings']
    by_id = {n['id']: n for n in nodes}
    if len(by_id) != len(nodes): errors.append('Duplicate node IDs')
    starts = [n for n in nodes if n.get('type') == 'start']
    if len(starts) != 1: errors.append('Exactly one start required')
    if not any(n.get('type') == 'end' for n in nodes): errors.append('End required')
    incoming = {id: [] for id in by_id}
    outgoing = {id: [] for id in by_id}
    if any(not isinstance(e,dict) for e in edges): return ['Edges must be objects']
    if any(not isinstance(e.get('source'),str) or not isinstance(e.get('target'),str) for e in edges): return ['Edge IDs must be strings']
    if any('label' in e and e['label'] not in ('true','false') for e in edges): return ['Edge label must be true or false']
    for e in edges:
        if not isinstance(e,dict) or e.get('source') not in by_id or e.get('target') not in by_id:
            errors.append('Edge references missing node'); continue
        outgoing[e['source']].append(e); incoming[e['target']].append(e)
    for n in nodes:
        if n.get('type') not in ('start','agent','condition','end'): errors.append('Unknown node type')
        if n.get('type') == 'agent':
            agent = store.get('agent', n.get('agent_id')) if isinstance(n.get('agent_id'),str) else None
            if not agent or agent['workspace_id'] != workspace or not agent['enabled']:
                errors.append('Agent missing, disabled or outside workspace')
        if n.get('type') == 'start' and incoming[n['id']]: errors.append('Start has incoming edges')
        if n.get('type') == 'end' and outgoing[n['id']]: errors.append('End has outgoing edges')
        if n.get('type') != 'end' and not outgoing[n['id']]: errors.append('Non-end node has no outgoing edge')
        if n.get('type') == 'condition':
            if sorted(e.get('label','') for e in outgoing[n['id']]) != ['false','true']:
                errors.append('Condition requires one true and one false edge')
            condition = n.get('condition', {})
            if not isinstance(condition,dict) or condition.get('field') not in ('input','output') or not isinstance(condition.get('equals'),str):
                errors.append('Condition requires field input/output and string equals')
    degree = {id:len(incoming[id]) for id in by_id}
    queue = deque(id for id in by_id if not degree[id]); order=[]
    while queue:
        id = queue.popleft(); order.append(id)
        for e in outgoing[id]:
            degree[e['target']] -= 1
            if degree[e['target']] == 0: queue.append(e['target'])
    if len(order) != len(nodes): errors.append('Cycles are forbidden')
    reached=set()
    def visit(id):
        if id in reached: return
        reached.add(id)
        for e in outgoing[id]: visit(e['target'])
    if starts: visit(starts[0]['id'])
    if reached != set(by_id): errors.append('Unreachable nodes')
    return sorted(set(errors))


class Runtime:
    def __init__(self, store):
        self.store=store; self.jobs={}; self.semaphore=asyncio.Semaphore(2)

    def schedule(self, run):
        job=asyncio.create_task(self.execute(run['id']))
        self.jobs[run['id']]=job
        job.add_done_callback(lambda _: self.jobs.pop(run['id'],None))

    def cancel(self, id):
        job=self.jobs.get(id)
        if job: job.cancel()

    async def execute(self, id):
        store=self.store; run=store.get('run',id)
        ws=run['workspace_id']
        def event(kind,payload=None,agent=None): store.event(ws,kind,payload,id,agent)
        task=None; agent=None
        try:
            async with self.semaphore:
                if store.get('run',id)['state']=='cancelled': return
                run.update(state='running',started_at=now()); store.put('run',run)
                graph=run['graph']; nodes={n['id']:n for n in graph['nodes']}
                # Topological processing, filtering inactive conditional paths.
                pending=set(nodes); outputs={}; active_edges=set(); steps=0; tokens=run['token_budget']
                while pending:
                    progressed=False
                    for node_id in list(nodes):
                        if node_id not in pending: continue
                        incoming=[(i,e) for i,e in enumerate(graph['edges']) if e['target']==node_id]
                        if any(e['source'] in pending for _,e in incoming): continue
                        pending.remove(node_id); progressed=True
                        node=nodes[node_id]
                        if incoming and not any(i in active_edges for i,_ in incoming): continue
                        steps+=1
                        if steps>run['max_steps']: raise ValueError('Maximum workflow steps exceeded')
                        text='\n\n'.join(outputs[e['source']] for i,e in incoming if i in active_edges) if incoming else run['input']
                        output=text
                        if node['type']=='agent':
                            agent=store.get('agent',node['agent_id'])
                            if not agent or not agent['enabled']: raise ValueError('Agent disabled')
                            task=dict(id=uid(),node_id=node_id,agent_id=agent['id'],state='queued',input=text,output='',retry_count=0,error=None)
                            run['tasks'].append(task);store.put('run',run);event('task.queued',{'task_id':task['id']},agent['id'])
                            for edge_index,edge in incoming:
                                if edge_index not in active_edges: continue
                                sender=nodes[edge['source']].get('agent_id')
                                if sender:
                                    store.put('message',dict(id=uid(),workspace_id=ws,run_id=id,sender=sender,recipient=agent['id'],payload=outputs.get(edge['source'],''),timestamp=now(),correlation_id=task['id']))
                            task['state']='running';agent['status']='working';store.put('agent',agent);store.put('run',run)
                            event('task.started',{'task_id':task['id'],'node_id':node_id},agent['id'])
                            denied=[t for t in agent['tools'] if t not in ('documents.list','documents.read','memory.read')]
                            if denied:
                                event('tool.requested',{'tools':denied},agent['id']);event('approval.required',{'decision':'denied','tools':denied},agent['id'])
                                store.put('audit',dict(id=uid(),workspace_id=ws,actor=agent['id'],action='tool.execute',target=denied,decision='denied',created_at=now()))
                                raise ValueError('Tool policy denied; side effects cannot execute')
                            context=tool_context(store,ws,agent['tools'])
                            if context:
                                event('tool.requested',{'tools':agent['tools'],'decision':'read_only'},agent['id'])
                                event('task.progress',{'tool_result':'Workspace context loaded'},agent['id'])
                            model_input=text+('\n\nRead-only workspace context:\n'+context if context else '')
                            for attempt in range(run['retry_limit']+1):
                                try:
                                    accounting={}
                                    output,used=await run_brain(agent,model_input,tokens,accounting);tokens-=used;break
                                except ValueError:
                                    if attempt>=run['retry_limit']: raise
                                    task['retry_count']+=1;store.put('run',run)
                                    event('task.progress',{'retry_count':task['retry_count']},agent['id'])
                                    await asyncio.sleep(.05)
                            task.update(state='completed',output=output)
                            agent['status']='completed';store.put('agent',agent);store.put('run',run)
                            event('task.completed',{'task_id':task['id'],'output':output,'tokens':used,'token_accounting':accounting['token_accounting']},agent['id'])
                            task=None
                        outputs[node_id]=output
                        for i,edge in enumerate(graph['edges']):
                            if edge['source']!=node_id: continue
                            if node['type']=='condition':
                                condition=node['condition']; matched=(text if condition['field']=='input' else output)==condition['equals']
                                if edge.get('label')!=str(matched).lower(): continue
                            active_edges.add(i)
                        await asyncio.sleep(0)
                    if not progressed: raise ValueError('Invalid dependency graph')
                run.update(state='completed',output='\n\n'.join(outputs[n['id']] for n in graph['nodes'] if n['type']=='end' and n['id'] in outputs),ended_at=now())
                store.put('run',run);event('workflow.completed',{'output':run['output']})
        except asyncio.CancelledError:
            run=store.get('run',id);run.update(state='cancelled',ended_at=now())
            for item in run['tasks']:
                if item['state'] in ('running','queued'):
                    item['state']='cancelled';event('task.cancelled',{'task_id':item['id']},item['agent_id'])
            store.put('run',run);event('workflow.cancelled')
            if agent: agent['status']='idle';store.put('agent',agent)
        except Exception as exc:
            error=str(exc) if isinstance(exc,ValueError) else 'Runtime execution failed'
            if task: task.update(state='failed',error=error);event('task.failed',{'task_id':task['id'],'error':error},task['agent_id'])
            run.update(state='failed',error=error,ended_at=now());store.put('run',run);event('workflow.failed',{'error':error})
            if agent: agent['status']='error';store.put('agent',agent)
