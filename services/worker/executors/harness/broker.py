"""Ephemeral authenticated bridge; all permission decisions use domain dispatcher."""
from __future__ import annotations
import asyncio
import hmac
import inspect
import json
import secrets

PROTOCOL='agentverse-harness-bridge/1'
MAX_BODY=64_000

class ToolBroker:
    def __init__(self,session,dispatch,emit=None,max_calls=16):
        self.session=session;self.dispatch=dispatch;self.emit=emit
        self.token=secrets.token_urlsafe(32);self.max_calls=max_calls;self.calls=0
        self.server=None;self.endpoint=None;self.clients=set()
    async def __aenter__(self):
        self.server=await asyncio.start_server(self._handle,'127.0.0.1',0,limit=MAX_BODY)
        self.endpoint=f'http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}/dispatch'
        return self
    async def __aexit__(self,*exc):
        self.server.close();await self.server.wait_closed()
        tasks=list(self.clients)
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
    async def event(self,kind,payload):
        if self.emit:
            result=self.emit(kind,payload)
            if inspect.isawaitable(result):await result
    async def _handle(self,reader,writer):
        task=asyncio.current_task();self.clients.add(task)
        tool=None
        status=403;body={'ok':False,'error':'Tool request rejected'}
        try:
            raw=await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),2)
            lines=raw.decode('ascii').split('\r\n')
            if lines[0]!='POST /dispatch HTTP/1.1':raise ValueError('route')
            headers={}
            for line in lines[1:]:
                if not line:continue
                name,value=line.split(':',1);name=name.lower().strip()
                if name in headers:raise ValueError('duplicate header')
                headers[name]=value.strip()
            if not hmac.compare_digest(headers.get('authorization',''),'Bearer '+self.token):raise ValueError('auth')
            if 'transfer-encoding' in headers:raise ValueError('encoding')
            size=int(headers.get('content-length','0'))
            if size<1 or size>MAX_BODY:raise ValueError('size')
            request=json.loads(await asyncio.wait_for(reader.readexactly(size),2))
            if set(request)!={'protocol','session_id','tool_id','payload'} or request['protocol']!=PROTOCOL or request['session_id']!=self.session:
                raise ValueError('session')
            if not isinstance(request['tool_id'],str) or not isinstance(request['payload'],dict):raise ValueError('schema')
            self.calls+=1
            if self.calls>self.max_calls:raise ValueError('budget')
            tool=request['tool_id']
            await self.event('harness.tool.started',{'tool':request['tool_id'],'session_id':self.session})
            result=await self.dispatch(request['tool_id'],request['payload'])
            body={'protocol':PROTOCOL,'session_id':self.session,'ok':True,'result':result}
            encoded=json.dumps(body).encode()
            if len(encoded)>MAX_BODY:raise ValueError('result too large')
            status=200
            await self.event('harness.tool.completed',{'tool':request['tool_id'],'session_id':self.session})
        except (Exception,asyncio.CancelledError):
            # Never expose model text, SQL, filesystem paths, secret refs or dispatcher errors.
            status=403;body={'ok':False,'error':'Tool request rejected'}
            if tool is not None:
                try: await self.event('harness.tool.failed',{'tool':tool,'session_id':self.session,'error':'Policy or tool rejected request'})
                except Exception: pass
        finally:
            encoded=json.dumps(body).encode()
            writer.write(f'HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\nContent-Length: {len(encoded)}\r\nConnection: close\r\n\r\n'.encode()+encoded)
            try:await writer.drain()
            except (ConnectionError,asyncio.CancelledError):pass
            writer.close();await writer.wait_closed();self.clients.discard(task)
