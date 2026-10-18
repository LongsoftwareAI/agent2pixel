"""Unit boundaries plus real official SDK/runtime integration against provider stub."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from services.worker.executors.harness import capabilities,execute_assignment,HarnessError
from services.worker.executors.harness.executor import isolated_environment,owned_directory

class Stub(BaseHTTPRequestHandler):
    finish_reason='stop'; requests=[]; delay=0; http_status=200
    def log_message(self,*a): pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        if self.delay:
            import time; time.sleep(self.delay)
        if self.http_status!=200:
            self.send_response(self.http_status);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(b'{"error":{"message":"provider private detail","type":"authentication_error"}}');return
        self.send_response(200); self.send_header('Content-Type','text/event-stream');self.end_headers()
        chunks=[{'id':'chat_stub','object':'chat.completion.chunk','model':'stub',
            'choices':[{'index':0,'delta':{'role':'assistant','content':'REAL_HARNESS_OK'},'finish_reason':None}]},
            {'id':'chat_stub','object':'chat.completion.chunk','model':'stub','choices':[{'index':0,'delta':{},'finish_reason':self.finish_reason}],
             'usage':{'prompt_tokens':10,'completion_tokens':6,'total_tokens':16}}]
        if body.get('tools') and not any(m.get('role')=='tool' for m in body.get('messages',[])):
            chunks=[{'id':'chat_tool','object':'chat.completion.chunk','model':'stub','choices':[{'index':0,
                'delta':{'role':'assistant','tool_calls':[{'index':0,'id':'call_one','type':'function',
                'function':{'name':'agentverse_dispatch','arguments':json.dumps({'tool_id':'memory.read','payload':{}})}}]},'finish_reason':None}]},
                {'id':'chat_tool','object':'chat.completion.chunk','model':'stub','choices':[{'index':0,'delta':{},'finish_reason':'tool_calls'}],
                 'usage':{'prompt_tokens':10,'completion_tokens':6,'total_tokens':16}}]
        with contextlib.suppress(BrokenPipeError):
            for data in chunks:self.wfile.write(('data: '+json.dumps(data)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()

class Store:
    def __init__(self,root):self.root=Path(root)
    def get(self,kind,id):return {'id':id,'workspace_id':'ws'}

class Boundaries(unittest.TestCase):
    def test_environment_does_not_inherit(self):
        with patch.dict(os.environ,{'UNRELATED_SECRET':'DO_NOT_COPY'}):
            env=isolated_environment('/tmp/home','role')
            self.assertNotIn('UNRELATED_SECRET',env);self.assertNotIn('PYTHONPATH',env)
    def test_workspace_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(HarnessError):owned_directory(root,'../escape')
            Path(root,'alias').symlink_to('/tmp',target_is_directory=True)
            with self.assertRaises(HarnessError):owned_directory(root,'alias')

@unittest.skipUnless(capabilities()['available'],'Pinned optional official Harness pair not installed')
class RealRuntime(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        Stub.finish_reason='stop';Stub.requests=[];Stub.delay=0;Stub.http_status=200
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Stub)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.agent={'id':'agent','workspace_id':'ws','system_prompt':'You are a reviewer.',
            'execution':{'profile':'agentverse-tool-less-v1'},
            'brain':{'provider':'deepseek','model':'provider-stub','endpoint':f'http://127.0.0.1:{self.server.server_port}',
                     'secret_ref':'AGENTVERSE_TEST_HARNESS_KEY'}}
        self.env=patch.dict(os.environ,{'AGENTVERSE_TEST_HARNESS_KEY':'local-stub-only'});self.env.start()
    async def asyncTearDown(self):
        self.env.stop();self.server.shutdown();self.server.server_close();self.temp.cleanup()
    async def execute(self,**kw):
        return await execute_assignment(kw.get('agent',self.agent),'Hello',kw.get('budget',256),self.store,'run',None)
    async def test_actual_runtime_smoke_and_tool_surface(self):
        output,usage=await self.execute()
        self.assertEqual(output,'REAL_HARNESS_OK');self.assertEqual(usage['tokens'],16)
        self.assertEqual(usage['token_accounting'],'provider')
        self.assertTrue(Stub.requests);self.assertFalse(Stub.requests[0].get('tools'))
        self.assertIn('You are a reviewer.',json.dumps(Stub.requests[0]))
    async def test_real_plugin_routes_to_shared_dispatch_seam(self):
        # Actual SDK/runtime/plugin/HTTP transport; domain dispatcher is a contract spy here.
        # Shared domain grants/namespace regression is covered by backend tests.
        seen=[];events=[]
        async def dispatch(store,run,agent,tool_id,payload):
            seen.append((agent['id'],run['id'],tool_id,payload));return [{'content':'shared-memory-fixture'}]
        self.agent['execution']['profile']='agentverse-registry-v1'
        self.agent['tool_grants']=[{'id':'memory.read','allow':True}]
        with patch('services.worker.tools.dispatch_tool',dispatch,create=True):
            output,usage=await execute_assignment(self.agent,'Read memory',256,self.store,'run',lambda k,p:events.append(k))
        self.assertEqual(output,'REAL_HARNESS_OK');self.assertTrue(usage['tools_enabled'])
        self.assertEqual(seen,[('agent','run','memory.read',{})])
        self.assertEqual(usage['tokens'],32)
        result_messages=[m for request in Stub.requests for m in request.get('messages',[]) if m.get('role')=='tool']
        self.assertIn('shared-memory-fixture',json.dumps(result_messages))
        self.assertIn('harness.tool.completed',events)
    async def test_max_tokens_is_not_success(self):
        Stub.finish_reason='length'
        with self.assertRaises(HarnessError):await self.execute()
    async def test_budget_rejected(self):
        with self.assertRaisesRegex(HarnessError,'budget'):await self.execute(budget=1)
    async def test_cross_workspace_rejected(self):
        agent={**self.agent,'workspace_id':'other'}
        with self.assertRaisesRegex(HarnessError,'ownership'):await self.execute(agent=agent)
    async def test_unassigned_agent_rejected_before_provider(self):
        for run_record in ({'agent_specs': {}}, {'tasks': []}):
            original = self.store.get
            def get(kind, ident):
                value = original(kind, ident)
                return {**value, **run_record} if kind == 'run' else value
            with patch.object(self.store, 'get', get):
                with self.assertRaisesRegex(HarnessError, 'not assigned'):
                    await self.execute()
        self.assertEqual(Stub.requests, [])

    async def test_profile_override_rejected(self):
        agent={**self.agent,'execution':{'profile':'sdk'}}
        with self.assertRaisesRegex(HarnessError,'profile'):await self.execute(agent=agent)
    async def test_provider_rejection_is_not_success(self):
        Stub.http_status=401
        with self.assertRaises(HarnessError) as raised:await self.execute()
        self.assertNotIn('provider private detail',str(raised.exception))
    async def test_wrong_session_response_rejected(self):
        from services.worker.executors.harness.executor import bounded_communicate
        async def foreign(process,request):
            data=json.loads(await bounded_communicate(process,request));data['session_id']='foreign'
            return json.dumps(data).encode()
        with patch('services.worker.executors.harness.executor.bounded_communicate',foreign):
            with self.assertRaisesRegex(HarnessError,'session mismatch'):await self.execute()
    async def test_cancellation_reaps_process(self):
        Stub.delay=10
        task=asyncio.create_task(self.execute())
        for _ in range(100):
            if Stub.requests:break
            await asyncio.sleep(.05)
        self.assertTrue(Stub.requests)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        # No worker session process survives cancellation.
        import subprocess
        result=subprocess.run(['pgrep','-af',str(Path('services/worker/executors/harness/worker.py').resolve())],capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stdout)

if __name__=='__main__':unittest.main()
