"""No tool dispatch is inferred from model text. Providers only return text."""
import asyncio
import hashlib
import os
from urllib.parse import urlparse
import httpx
from services.api.policy import validate_brain


async def run_brain(agent, text, budget, metadata=None):
    if metadata is not None: metadata['token_accounting']='estimated'
    brain = validate_brain(agent['brain'])
    provider = brain.get('provider', 'mock')
    if budget < 1:
        raise ValueError('Token budget exhausted')
    if provider == 'mock':
        await asyncio.sleep(0.06)
        role = agent['role'].lower()
        digest = hashlib.sha256(text.encode()).hexdigest()[:10]
        if 'plan' in role:
            output = f'[MockBrain deterministic] Plan for: {text}\n1. Analyze requirements\n2. Implement isolated solution\n3. Verify acceptance criteria ({digest})'
        elif 'review' in role:
            output = f'[MockBrain deterministic] Review: received {len(text)} characters, trace {digest}. Check scope, isolation and tests.\nReviewed input:\n{text}'
        else:
            output = f'[MockBrain deterministic] {agent["role"]} work product for input {digest}:\n{text}\nDeliverable: task-specific implementation outline and verification checklist.'
        used = max(1, (len(text)+len(output))//4)
        if used > budget:
            raise ValueError('Token budget exhausted')
        return output, used
    endpoint = brain.get('endpoint') or ('https://api.openai.com/v1' if provider == 'openai' else 'http://127.0.0.1:11434')
    messages = [{'role':'system','content':agent['system_prompt']}, {'role':'user','content':text}]
    headers = {}
    if provider == 'openai':
        key = os.getenv(brain['secret_ref']) if brain.get('secret_ref') else (os.getenv('AGENTVERSE_OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY'))
        if not key:
            raise ValueError('Provider secret reference is not configured')
        headers['Authorization'] = 'Bearer '+key
        url = endpoint.rstrip('/')+'/chat/completions'
        body = dict(model=brain['model'], messages=messages, max_tokens=min(budget,4096))
    else:
        url = endpoint.rstrip('/')+'/api/chat'
        body = dict(model=brain['model'], messages=messages, stream=False, options={'num_predict': min(budget,4096)})
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=urlparse(endpoint).hostname not in ('localhost', '127.0.0.1', '::1')) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        if provider == 'openai':
            output = data['choices'][0]['message']['content']
            used = data.get('usage',{}).get('total_tokens', max(1,(len(text)+len(output))//4))
            if metadata is not None and 'total_tokens' in data.get('usage',{}): metadata['token_accounting']='provider'
        else:
            output = data['message']['content']
            used = data.get('prompt_eval_count',0)+data.get('eval_count',max(1,len(output)//4))
            if metadata is not None and 'eval_count' in data: metadata['token_accounting']='provider'
        if not isinstance(output,str) or type(used) is not int or used < 0:
            raise RuntimeError('Malformed provider response')
        if used > budget:
            raise ValueError('Token budget exhausted')
        return output, used
    except ValueError as exc:
        if str(exc) == 'Token budget exhausted': raise
        raise ValueError('Provider response was invalid') from None
    except Exception:
        # Do not surface HTTP bodies, URLs or headers that may contain secrets.
        raise ValueError('Provider request failed; check readiness and endpoint') from None
