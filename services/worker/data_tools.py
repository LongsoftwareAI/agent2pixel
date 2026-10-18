"""Bounded data tools. Imported text is evidence, never authority or executable code."""
import csv
import hashlib
import http.client
import io
import ipaddress
import json
import os
import socket
import time
import ssl
from decimal import Decimal, InvalidOperation, localcontext
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin

from services.api.store import now, uid

MAX_BYTES = 1024 * 1024
MAX_ROWS = 10000
MAX_COLUMNS = 100
MAX_CELL = 16000
DEFAULT_WEB_HOSTS = frozenset({'en.wikipedia.org', 'vi.wikipedia.org', 'www.python.org', 'docs.python.org', 'raw.githubusercontent.com'})


def schema(properties, required):
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}


DATA_TOOLS = [
    dict(id='sources.read', version=1, name='Read scoped source (untrusted evidence)', approval_required=False,
         input_schema=schema({'source_id': {'type': 'string'}}, ['source_id'])),
    dict(id='csv.analyze', version=1, name='Analyze CSV with exact decimal summaries', approval_required=False,
         input_schema=schema({k: {'type': 'string'} for k in ('source_id', 'column', 'group_by')}, ['source_id'])),
    dict(id='web.read', version=1, name='Read bounded allowlisted HTTPS URL', approval_required=False,
         input_schema=schema({'url': {'type': 'string'}}, ['url'])),
]


def scoped_source(store, workspace_id, source_id):
    if not isinstance(source_id, str):
        raise ValueError('source_id must be a string')
    source = store.get('source', source_id)
    if not source or source['workspace_id'] != workspace_id:
        raise ValueError('Source not found in assigned workspace')
    return source


def parse_csv(content):
    try:
        reader = csv.reader(io.StringIO(content, newline=''), strict=True)
        headers = next(reader)
        if not 1 <= len(headers) <= MAX_COLUMNS or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
            raise ValueError('CSV needs 1..100 unique nonempty column names')
        if any(len(h) > MAX_CELL for h in headers):
            raise ValueError('CSV column name exceeds cell limit')
        rows = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(headers):
                raise ValueError('CSV row width does not match header')
            if any(len(cell) > MAX_CELL for cell in row):
                raise ValueError('CSV cell exceeds 16000 characters')
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise ValueError('CSV exceeds 10000 rows')
        return headers, rows
    except (csv.Error, StopIteration) as exc:
        raise ValueError('Malformed or empty CSV') from exc


def create_source(store, workspace_id, name, content, media_type, url=None, retrieved_at=None):
    if not store.get('workspace', workspace_id):
        raise ValueError('Workspace not found')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200:
        raise ValueError('Source name requires 1..200 characters')
    if media_type not in ('text/plain', 'text/csv', 'text/markdown'):
        raise ValueError('Unsupported source media_type')
    if not isinstance(content, str) or not content.strip() or len(content.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Source content requires nonempty UTF8 text at most1MiB')
    result = dict(id=uid(), workspace_id=workspace_id, name=name.strip(), content=content,
                  media_type=media_type, sha256=hashlib.sha256(content.encode()).hexdigest(),
                  created_at=now(), retrieved_at=retrieved_at, url=url, untrusted=True)
    if media_type == 'text/csv':
        headers, rows = parse_csv(content)
        result['preview'] = dict(columns=headers, rows=rows[:10], row_count=len(rows))
    store.put('source', result)
    store.event(workspace_id, 'source.created', {'source_id': result['id'], 'sha256': result['sha256']})
    return result


def decimal_value(cell):
    # Decimal accepts NaN/Infinity and exponents: exclude nonfinite and excessive scale.
    if not cell.strip():
        return None
    try:
        value = Decimal(cell.strip())
    except InvalidOperation:
        return False
    if not value.is_finite() or len(value.as_tuple().digits) > 100 or abs(value.as_tuple().exponent) > 100:
        return False
    return value


def summarize(cells):
    numbers, missing, invalid = [], 0, 0
    for cell in cells:
        value = decimal_value(cell)
        if value is None:
            missing += 1
        elif value is False:
            invalid += 1
        else:
            numbers.append(value)
    with localcontext() as ctx:
        ctx.prec = 220
        total = sum(numbers, Decimal(0))
        return dict(count=len(cells), numeric_count=len(numbers), missing=missing, non_numeric=invalid,
                    min=str(min(numbers)) if numbers else None, max=str(max(numbers)) if numbers else None,
                    sum=str(total) if numbers else None, mean=str(total / len(numbers)) if numbers else None)


def analyze_csv(source, payload):
    if source['media_type'] != 'text/csv':
        raise ValueError('csv.analyze requires a text/csv source')
    headers, rows = parse_csv(source['content'])
    column, group_by = payload.get('column'), payload.get('group_by')
    if column is not None and column not in headers or group_by is not None and group_by not in headers:
        raise ValueError('Requested column/group_by is absent from CSV header')
    columns = [column] if column else headers
    result = dict(source_id=source['id'], sha256=source['sha256'], row_count=len(rows),
                  columns={c: summarize([row[headers.index(c)] for row in rows]) for c in columns},
                  numeric_representation='decimal strings; repeating means rounded to 220 significant digits', untrusted=True)
    if group_by:
        grouped = {}
        index = headers.index(group_by)
        for row in rows:
            grouped.setdefault(row[index], []).append(row)
            if len(grouped) > 100:
                raise ValueError('Grouping exceeds 100 groups; choose another column')
        result['groups'] = {key: {c: summarize([row[headers.index(c)] for row in values]) for c in columns} for key, values in grouped.items()}
    return result


def allowed_hosts():
    # Explicit deployment configuration only; no model/client supplied allowlist.
    configured = os.getenv('AGENTVERSE_WEB_ALLOWED_HOSTS')
    return frozenset(x.strip().lower() for x in configured.split(',') if x.strip()) if configured is not None else DEFAULT_WEB_HOSTS


def validate_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError('URL must be a bounded HTTPS URL without whitespace')
    try:
        parts = urlsplit(url)
        if parts.scheme != 'https' or not parts.hostname or parts.port not in (None, 443) or parts.username or parts.password or parts.query or parts.fragment or '\\' in url:
            raise ValueError('Only HTTPS:443 without credentials, query or fragment is supported')
        host = parts.hostname.lower()
        if host not in allowed_hosts():
            raise ValueError('URL hostname is not explicitly allowlisted')
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ips = sorted({item[4][0] for item in addresses})
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError('URL resolves to a nonpublic address')
        return parts, ips
    except (OSError, ValueError) as exc:
        raise ValueError('URL denied or DNS resolution failed: ' + str(exc)) from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip):
        super().__init__(host, timeout=8, context=ssl.create_default_context())
        self.pinned_ip = ip

    def connect(self):
        # Connect to the validated IP, keep original TLS hostname + certificate checks.
        self.sock = self._context.wrap_socket(socket.create_connection((self.pinned_ip, 443), self.timeout), server_hostname=self.host)


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored += 1
        if tag in ('p', 'br', 'div', 'li', 'h1', 'h2', 'h3'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def fetch_web(url):
    original = url
    deadline = time.monotonic() + 25
    for _ in range(4):
        if time.monotonic() >= deadline:
            raise ValueError("Web fetch exceeded25s deadline")
        parts, ips = validate_url(url)
        connection = PinnedHTTPS(parts.hostname, ips[0])
        connection.timeout = max(0.01, min(8, deadline - time.monotonic()))
        try:
            connection.request('GET', parts.path or '/', headers={'User-Agent': 'AgentVerse/0.4 evidence-fetch', 'Accept': 'text/plain,text/html,text/markdown,text/csv', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise ValueError('Redirect missing location')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError('Web source returned HTTP ' + str(response.status))
            media = (response.getheader('Content-Type') or '').split(';')[0].strip().lower()
            if media not in ('text/plain', 'text/html', 'text/markdown', 'text/csv') or response.getheader('Content-Encoding') not in (None, 'identity'):
                raise ValueError('Web response must be uncompressed supported text')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > MAX_BYTES):
                raise ValueError('Web source exceeds1MiB')
            chunks = []
            size = 0
            while size <= MAX_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("Web fetch exceeded25s deadline")
                if connection.sock:
                    connection.sock.settimeout(min(8, remaining))
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            data = b"".join(chunks)
            if len(data) > MAX_BYTES:
                raise ValueError('Web source exceeds1MiB')
            content = data.decode('utf-8', errors='strict')
            if media == 'text/html':
                parser = PlainHTML()
                parser.feed(content)
                content = ''.join(parser.parts).strip()
                media = 'text/plain'
            if not content.strip():
                raise ValueError('Web source returned empty text')
            return dict(url=url, original_url=original, content=content, media_type=media, retrieved_at=now(),
                        sha256=hashlib.sha256(content.encode()).hexdigest(), untrusted=True)
        except (OSError, UnicodeError, http.client.HTTPException) as exc:
            raise ValueError('Web fetch failed: ' + type(exc).__name__) from None
        finally:
            connection.close()
    raise ValueError('Web source exceeded3 redirects')
