"""Independent HTTP acceptance helpers; no app adapters or dispatchers are replaced."""
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ProviderFixture:
    """Only inference is synthetic. Native adapter/tool/Store/runtime remain real."""
    def __init__(self):
        self.requests = []
        self.outputs = []
        self.delay = 0
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.requests.append(body)
                if fixture.delay:
                    time.sleep(fixture.delay)
                content = body['messages'][-1]['content']
                output = ('[LOCAL HTTP PROVIDER FIXTURE; NOT LIVE INFERENCE]\n'
                          + 'Assignment SHA256: ' + hashlib.sha256(content.encode()).hexdigest()
                          + '\nRevision feedback present: ' + str('QA_REWORK_COMMENT' in content)
                          + '\nReport supplied evidence only; all unprovided facts remain unknown.')
                fixture.outputs.append(output)
                encoded = json.dumps({'message': {'content': output}, 'prompt_eval_count': 13, 'eval_count': 17}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                try:
                    self.wfile.write(encoded)
                except BrokenPipeError:
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}'

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()


class API:
    def __init__(self, base):
        self.base = base.rstrip('/')

    def request(self, path, body=None, method=None):
        request = urllib.request.Request(self.base + path,
            data=None if body is None else json.dumps(body).encode(), method=method,
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def ok(self, path, body=None, method=None):
        status, value = self.request(path, body, method)
        assert status == 200, (path, status, value)
        return value

    def denied(self, path, body=None, method=None):
        status, value = self.request(path, body, method)
        assert status in (400, 403, 404, 409, 422), (path, status, value)
        return status

    def wait(self, run_id, states=('completed', 'failed', 'cancelled', 'waiting_approval')):
        for _ in range(2500):
            value = self.ok('/api/runs/' + run_id)
            if value['state'] in states:
                return value
            time.sleep(.02)
        raise AssertionError('Runtime did not settle')


def tool_envelope(provider_request):
    text = provider_request['messages'][-1]['content']
    start = text.index('{"classification": "UNTRUSTED_TOOL_DATA"')
    envelope, _end = json.JSONDecoder().raw_decode(text[start:])
    assert envelope['classification'] == 'UNTRUSTED_TOOL_DATA'
    return envelope
