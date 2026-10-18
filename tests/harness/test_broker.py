import asyncio
import json
import unittest
from services.worker.executors.harness.broker import ToolBroker,PROTOCOL

class BrokerPolicy(unittest.IsolatedAsyncioTestCase):
    async def request(self,broker,**changes):
        body={'protocol':PROTOCOL,'session_id':'owned','tool_id':'memory.read','payload':{}}
        body.update(changes.pop('body',{}));token=changes.get('token',broker.token)
        reader,writer=await asyncio.open_connection('127.0.0.1',broker.server.sockets[0].getsockname()[1])
        data=json.dumps(body).encode()
        writer.write(f'POST /dispatch HTTP/1.1\r\nAuthorization: Bearer {token}\r\nContent-Length: {len(data)}\r\n\r\n'.encode()+data)
        await writer.drain();response=await reader.read();writer.close();await writer.wait_closed()
        return int(response.split(b' ')[1]),json.loads(response.split(b'\r\n\r\n',1)[1])
    async def test_auth_session_and_call_budget(self):
        calls=[]
        async def dispatch(tool,payload):calls.append(tool);return ['owned-memory']
        async with ToolBroker('owned',dispatch,max_calls=1) as broker:
            self.assertEqual((await self.request(broker,token='wrong'))[0],403)
            self.assertEqual((await self.request(broker,body={'session_id':'foreign'}))[0],403)
            self.assertEqual(calls,[])
            status,body=await self.request(broker);self.assertEqual(status,200);self.assertEqual(body['result'],['owned-memory'])
            self.assertEqual((await self.request(broker))[0],403)
            self.assertEqual(calls,['memory.read'])
    async def test_domain_denial_is_sanitized(self):
        async def deny(tool,payload):raise ValueError('SECRET not authorized')
        events=[]
        async with ToolBroker('owned',deny,lambda kind,payload:events.append(kind)) as broker:
            status,body=await self.request(broker)
            self.assertEqual(status,403);self.assertNotIn('SECRET',str(body))
            self.assertEqual(events,['harness.tool.started','harness.tool.failed'])

class ProcessCleanup(unittest.IsolatedAsyncioTestCase):
    async def test_reaps_descendant_when_parent_already_exited(self):
        import sys
        import tempfile
        from pathlib import Path
        from services.worker.executors.harness.executor import terminate_group
        with tempfile.TemporaryDirectory() as root:
            pidfile=Path(root)/'child.pid'
            script="import os,signal,time; pid=os.fork(); open(__import__('sys').argv[1],'w').write(str(pid)) if pid else None; os._exit(0) if pid else None; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
            proc=await asyncio.create_subprocess_exec(sys.executable,'-c',script,str(pidfile),start_new_session=True,
                stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            await proc.wait();child=int(pidfile.read_text());await asyncio.sleep(.1)
            await terminate_group(proc)
            await asyncio.sleep(.1)
            stat=Path(f'/proc/{child}/stat')
            self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z','Descendant remains executing')

class BrokerLimits(unittest.IsolatedAsyncioTestCase):
    request = BrokerPolicy.request

    async def test_oversize_result_fails_closed(self):
        async def dispatch(tool,payload):return 'x'*65000
        async with ToolBroker('owned',dispatch) as broker:
            status,body=await self.request(broker)
            self.assertEqual(status,403);self.assertFalse(body['ok'])

    async def test_completion_event_failure_is_not_success(self):
        async def dispatch(tool,payload):return 'ok'
        def event(kind,payload):
            if kind=='harness.tool.completed':raise RuntimeError('storage unavailable')
        async with ToolBroker('owned',dispatch,event) as broker:
            status,body=await self.request(broker)
            self.assertEqual(status,403);self.assertFalse(body['ok'])
