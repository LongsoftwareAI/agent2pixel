import os
import re
from pathlib import Path
from urllib.parse import urlparse
from fastapi import HTTPException


def safe_document(root, path):
    target = (Path(root) / path).resolve()
    if not target.is_relative_to(Path(root).resolve()) or Path(path).is_absolute():
        raise HTTPException(403, 'Workspace path denied')
    if not target.is_file():
        raise HTTPException(404, 'Document not found')
    if target.stat().st_size > 1_000_000:
        raise HTTPException(400, 'Document exceeds size limit')
    return target


def validate_brain(brain):
    if not isinstance(brain,dict):
        raise HTTPException(422,'Brain must be an object')
    for field in ('provider','model','endpoint','secret_ref'):
        value=brain.get(field)
        if value is not None and not isinstance(value,str):
            raise HTTPException(422,f'{field} must be a string or null')
    if brain.get('provider','mock') != 'mock' and not (brain.get('model') or '').strip():
        raise HTTPException(422,'A provider model is required')
    if set(brain) - {'provider', 'model', 'endpoint', 'secret_ref'}:
        raise HTTPException(422, 'Only environment secret references are accepted')
    if brain.get('provider', 'mock') not in ('mock', 'openai', 'ollama'):
        raise HTTPException(422, 'Unsupported provider')
    ref = brain.get('secret_ref')
    if ref and not re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}', ref):
        raise HTTPException(422, 'secret_ref must name an environment variable')
    endpoint = brain.get('endpoint')
    if endpoint:
        try:
            parsed = urlparse(endpoint)
            parsed.hostname
            parsed.port
        except ValueError:
            raise HTTPException(422,'Malformed provider endpoint') from None
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(403, 'Endpoint credentials and query denied')
        local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
        hosts = os.getenv('AGENTVERSE_PROVIDER_HOSTS', 'api.openai.com').split(',')
        if not ((local and parsed.scheme == 'http') or
                (parsed.scheme == 'https' and parsed.hostname in hosts and brain.get('provider') == 'openai')):
            raise HTTPException(403, 'Provider endpoint is not allowlisted')
    return brain
