"""Private outer process; its environment was sanitized before SDK import."""
import json
import sys
import hashlib
import subprocess
from pathlib import Path
from deepseek_harness_runtime import resolve_bundled_launch_args
from deepseek_harness import DeepSeekHarness

def main():
    request=json.load(sys.stdin)
    patch=Path(request['patch'])
    effective=subprocess.run([*resolve_bundled_launch_args(), '--profile','sdk-minimal',
        '--patch',str(patch),'--dump-config'],capture_output=True,check=True,timeout=10).stdout
    expected=(patch.parent/'release-0.1.5rc1.effective.yml').read_bytes()
    if effective != expected: raise ValueError('Unapproved effective profile')
    def notification(n):
        e=n.payload.get('event',{})
        if n.payload.get('sessionId') != request['session_id']: raise ValueError('Foreign session event')
        if e.get('type')=='step/start' and e.get('data',{}).get('step',1)>1:
            raise ValueError('Unexpected tool-loop step in tool-less profile')
    with DeepSeekHarness(cwd=request['cwd'],dsh_home=request['home'],profile='sdk-minimal',
            patches=(request['patch'],),base_url=request['endpoint'],model=request['model'],
            max_tokens=request['budget'],request_timeout_seconds=60) as harness:
        result=harness.run(request['text'],session_id=request['session_id'],on_notification=notification)
    # Release events include raw requests; never expose them or exception strings.
    # Provider usage is preserved only after known event schema checks; otherwise estimate.
    used=max(1,(len(request['text'])+len(result.final_response))//4)
    accounting='estimated'
    usages=[e.get('data',{}).get('usage',{}) for e in result.events if e.get('type')=='assistant/message']
    if usages and all(type(u.get('totalTokens')) is int and u['totalTokens']>=0 for u in usages):
        used=sum(u['totalTokens'] for u in usages); accounting='provider'
    print(json.dumps({'output':result.final_response,'session_id':result.session_id,
        'finish_reason':result.finish_reason,'tokens':used,'token_accounting':accounting}))

if __name__=='__main__':
    try: main()
    except Exception: sys.exit(1)
