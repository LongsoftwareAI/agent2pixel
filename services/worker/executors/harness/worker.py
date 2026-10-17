"""Private outer process; its environment was sanitized before SDK import."""
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from deepseek_harness_runtime import resolve_bundled_launch_args
from deepseek_harness import DeepSeekHarness

class BudgetExceeded(ValueError): pass

def main():
    import os
    os.umask(0o077)
    request=json.load(sys.stdin)
    patch=Path(request['patch'])
    def canonical(data):
        return '\n'.join(line for line in data.decode().splitlines() if line.strip() and not line.lstrip().startswith('#'))
    expected=canonical((patch.parent/'release-0.1.5rc1.effective.yml').read_bytes())
    if request.get('tools'):
        module=Path(request['bridge_module']).resolve()
        text=patch.read_text()+'\n- insert:\n    - id: agentverse-bridge\n      name: '+json.dumps(str(module))+'\n      inject: [tools]\n'
        fd,newpatch=tempfile.mkstemp(prefix='approved-bridge-',suffix='.yml',dir=request['home'])
        import os
        with os.fdopen(fd,'w') as stream:stream.write(text)
        patch=Path(newpatch)
        expected+='\n- id: agentverse-bridge\n  name: '+module.as_uri()+'\n  inject:\n    - tools'
    effective=subprocess.run([*resolve_bundled_launch_args(), '--profile','sdk-minimal',
        '--patch',str(patch),'--dump-config'],capture_output=True,check=True,timeout=10).stdout
    if canonical(effective) != expected: raise ValueError('Unapproved effective profile')
    observed_usage=0
    def notification(n):
        nonlocal observed_usage
        e=n.payload.get('event',{})
        if n.payload.get('sessionId') != request['session_id']: raise ValueError('Foreign session event')
        maxsteps=16 if request.get('tools') else 1
        if e.get('type')=='step/start' and e.get('data',{}).get('step',1)>maxsteps:
            raise BudgetExceeded('step')
        if e.get('type')=='assistant/message':
            usage=e.get('data',{}).get('usage',{}).get('totalTokens',0)
            if type(usage) is not int or usage<0: raise ValueError('Invalid usage')
            observed_usage+=usage
            if observed_usage>request['budget']: raise BudgetExceeded('token')
    with DeepSeekHarness(cwd=request['cwd'],dsh_home=request['home'],profile='sdk-minimal',
            patches=(str(patch),),base_url=request['endpoint'],model=request['model'],
            max_tokens=min(request['budget'],4096),request_timeout_seconds=60) as harness:
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
    except BudgetExceeded: print(json.dumps({'error':'budget_exhausted'}))
    except Exception: sys.exit(1)
