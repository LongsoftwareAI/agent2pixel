"""A production uvicorn handshake catches missing protocol dependencies."""
import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
import websockets
from websockets.exceptions import InvalidStatus


def test_real_uvicorn_websocket_replay_and_origin(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=dict(os.environ,AGENTVERSE_DATA_DIR=str(tmp_path/'live'))
    process=subprocess.Popen([sys.executable,'-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port',str(port)],
                             cwd=Path(__file__).resolve().parents[2],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get('/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.03)
            else:raise AssertionError('uvicorn failed to start')
            ws=client.get('/api/workspaces').json()[0]
            agent=client.post('/api/agents',json={'workspace_id':ws['id'],'name':'Replay test'}).json()
        async def check():
            url=f'ws://127.0.0.1:{port}/ws/workspaces/{ws["id"]}/events?after=0'
            async with websockets.connect(url,origin='http://localhost:3000',proxy=None) as connection:
                import json
                event=json.loads(await asyncio.wait_for(connection.recv(),2))
                assert event['event_type']=='agent.created' and event['agent_id']==agent['id']
            try:
                async with websockets.connect(url,origin='https://foreign.example',proxy=None):
                    raise AssertionError('foreign Origin accepted')
            except InvalidStatus as exc:
                assert exc.response.status_code==403
        asyncio.run(check())
    finally:
        process.terminate();process.wait(timeout=5)
