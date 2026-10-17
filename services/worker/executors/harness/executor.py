"""Run a tool-less, pinned Harness process with an explicit isolated home.

The synchronous official SDK lives only in a sanitized outer process. All app
permissions remain in AgentVerse; this profile deliberately has no tool producer.
"""
from __future__ import annotations
import asyncio
from contextlib import AsyncExitStack
from .broker import ToolBroker
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import sys
from urllib.parse import urlparse

VERSION = '0.1.5rc1'
BRIDGE = Path(__file__).resolve().parents[4] / 'packages' / 'harness-bridge'
WORKER = Path(__file__).with_name('worker.py')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
MAX_OUTPUT = 2_000_000
CONCURRENCY = asyncio.Semaphore(2)

class HarnessError(ValueError):
    """Sanitized explicit failure, safe to return through the domain API."""


def capabilities():
    result = {'id':'deepseek_harness','available':False,'version':VERSION,
              'reason':'Pinned official SDK/runtime are not installed',
              'capabilities':{'text':False,'tools':False,'memory_bridge':False,
                              'skills_context':True,'cancellation':True}}
    try:
        if any(importlib.metadata.version(p) != VERSION for p in
               ('deepseek-harness-sdk','deepseek-harness-runtime-bin')):
            result['reason']='Harness SDK/runtime version mismatch'; return result
        from deepseek_harness_runtime import bundled_runtime_path
        artifacts = json.loads((BRIDGE/'ARTIFACTS.json').read_text())
        root = Path(importlib.metadata.distribution('deepseek-harness-sdk').locate_file(''))
        for name,digest in artifacts['file_sha256'].items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
                result['reason']='Harness artifact integrity mismatch'; return result
        for name,digest in artifacts['bridge_sha256'].items():
            if hashlib.sha256((BRIDGE/name).read_bytes()).hexdigest() != digest:
                result['reason']='Harness bridge integrity mismatch'; return result
        bundled_runtime_path()
        result.update(available=True,reason='Official tool-less runtime; plugin tools unavailable')
        result['capabilities']['text']=True
        try:
            from services.worker.tools import dispatch_tool
            if not callable(dispatch_tool): raise ImportError('Missing dispatcher')
            result['capabilities'].update(tools=True,memory_bridge=True)
            result['reason']='Official runtime with approved registry bridge'
        except ImportError: pass
    except (ImportError, importlib.metadata.PackageNotFoundError, OSError, ValueError):
        pass
    return result


def owned_directory(root, *parts):
    root=Path(root).resolve()
    current=root
    for part in parts:
        if not isinstance(part,str) or not ID.fullmatch(part):
            raise HarnessError('Invalid Harness workspace/agent/run identity')
        current=current/part
        if current.is_symlink(): raise HarnessError('Harness directory symlink rejected')
        current.mkdir(mode=0o700,exist_ok=True)
        if not current.resolve().is_relative_to(root): raise HarnessError('Harness workspace escape')
    return current


def isolated_environment(home, prompt, secret=None):
    # Never copy os.environ: SDK merges its own environment with that of this worker.
    env={'PATH':'/usr/bin:/bin','HOME':str(home),'DSH_HOME':str(home),
         'LANG':'C.UTF-8','DSH_SYSTEM_PROMPT':prompt,'PYTHONUNBUFFERED':'1'}
    if secret: env['DEEPSEEK_API_KEY']=secret
    return env


async def terminate_group(process):
    # Descendants can outlive an already-reaped SDK worker and ignore SIGTERM.
    try: os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError: return
    if process.returncode is None:
        try: await asyncio.wait_for(process.wait(),2)
        except asyncio.TimeoutError: pass
    await asyncio.sleep(.1)
    try: os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    await process.wait()


async def bounded_communicate(process,request):
    process.stdin.write(json.dumps(request).encode())
    await process.stdin.drain()
    process.stdin.close()
    chunks=[];size=0
    while True:
        chunk=await process.stdout.read(65536)
        if not chunk:break
        size+=len(chunk)
        if size>MAX_OUTPUT:raise HarnessError('Harness response exceeded limit')
        chunks.append(chunk)
    await process.wait()
    return b''.join(chunks)


async def execute_assignment(agent, text, budget, store, run_id, emit):
    state=capabilities()
    if not state['available']: raise HarnessError(state['reason'])
    if type(budget) is not int or budget < 1: raise HarnessError('Token budget exhausted')
    for key in ('workspace_id','id'):
        if not ID.fullmatch(str(agent.get(key,''))): raise HarnessError('Invalid Harness agent identity')
    run=store.get('run',run_id)
    persisted=store.get('agent',agent['id'])
    if not run or run.get('workspace_id') != agent['workspace_id'] or not persisted or persisted.get('workspace_id') != agent['workspace_id']:
        raise HarnessError('Harness assignment ownership mismatch')
    if agent.get('execution',{}).get('profile') not in (None,'agentverse-tool-less-v1','agentverse-registry-v1'):
        raise HarnessError('Unapproved Harness profile')
    brain=agent.get('brain',{})
    if brain.get('provider') not in ('deepseek','openai'):
        raise HarnessError('Harness requires a real OpenAI-compatible provider; mock is unsupported')
    endpoint=brain.get('endpoint') or 'https://api.deepseek.com'
    parsed=urlparse(endpoint)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HarnessError('Invalid Harness provider endpoint')
    if parsed.scheme=='http' and parsed.hostname not in ('127.0.0.1','localhost','::1'):
        raise HarnessError('Harness plaintext provider must be loopback')
    keyref=brain.get('secret_ref') or 'DEEPSEEK_API_KEY'
    if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}',keyref): raise HarnessError('Invalid provider secret reference')
    secret=os.environ.get(keyref)
    if not secret: raise HarnessError('Harness provider secret reference is not configured')
    base=owned_directory(store.root,'harness',agent['workspace_id'],agent['id'],run_id)
    home=owned_directory(base,'home'); cwd=owned_directory(base,'workspace')
    # Assignment has a fresh session even when the same agent is retried in a run.
    import uuid
    session='av-'+uuid.uuid4().hex
    request={'text':text,'budget':budget,'model':brain.get('model','deepseek-v4-flash'),
             'endpoint':endpoint,'session_id':session,'home':str(home),'cwd':str(cwd),
             'patch':str(BRIDGE/'tool-less.patch.yml')}
    timeout=min(120,max(1,float(agent.get('execution',{}).get('timeout_seconds',60))))
    tools=[g['id'] for g in agent.get('tool_grants',[]) if g.get('allow')]
    if agent.get('execution',{}).get('profile')=='agentverse-tool-less-v1': tools=[]
    if tools and not state['capabilities']['tools']: raise HarnessError('Harness registry bridge unavailable')
    request['tools']=tools
    request['bridge_module']=str(BRIDGE/'index.mjs')
    env=isolated_environment(home,agent.get('system_prompt',''),secret)
    async with CONCURRENCY, AsyncExitStack() as stack:
        if tools:
            from services.worker.tools import dispatch_tool
            async def dispatch(tool,payload):
                return await dispatch_tool(store,store.get('run',run_id),agent,tool,payload)
            broker=await stack.enter_async_context(ToolBroker(session,dispatch,emit))
            env.update(AGENTVERSE_HARNESS_BROKER=broker.endpoint,AGENTVERSE_HARNESS_BROKER_TOKEN=broker.token,
                       AGENTVERSE_HARNESS_SESSION=session,AGENTVERSE_HARNESS_TOOL_IDS=json.dumps(tools))
        process=await asyncio.create_subprocess_exec(sys.executable,str(WORKER),stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
            env=env,cwd=str(cwd),start_new_session=True,
            limit=MAX_OUTPUT)
        try:
            stdout=await asyncio.wait_for(bounded_communicate(process,request),timeout)
            if process.returncode != 0 or len(stdout)>MAX_OUTPUT: raise HarnessError('Harness worker failed')
            data=json.loads(stdout)
            if data.get('error')=='budget_exhausted': raise HarnessError('Harness budget exhausted')
            if data.get('session_id') != session: raise HarnessError('Harness session mismatch')
            if data.get('finish_reason') != 'completed': raise HarnessError('Harness turn did not complete: '+str(data.get('finish_reason'))[:40])
            if not isinstance(data.get('output'),str): raise HarnessError('Harness output invalid')
            used=data.get('tokens')
            if type(used) is not int or used<0 or used>budget: raise HarnessError('Token budget exhausted')
            return data['output'],{'tokens':used,'token_accounting':data['token_accounting'],
                'session_id':session,'engine_version':VERSION,'tools_enabled':bool(tools)}
        except asyncio.TimeoutError: raise HarnessError('Harness deadline exceeded') from None
        except (json.JSONDecodeError,KeyError,TypeError): raise HarnessError('Harness protocol response invalid') from None
        finally:
            await asyncio.shield(terminate_group(process))
