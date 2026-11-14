"""Redacted evidence for synthetic internal-browser checks; never store session state."""
from contextlib import AbstractContextManager
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

SENSITIVE = re.compile(r'cookie|authorization|password|token|secret', re.I)
JWT = re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')


def redact(value):
    if isinstance(value, dict):
        if 'name' in value and SENSITIVE.search(str(value['name'])):
            return {**value, 'value': '[redacted]'}
        return {key: '[redacted]' if SENSITIVE.search(key) else
                urlsplit(item)._replace(query='', fragment='').geturl() if key == 'url' and isinstance(item, str) else redact(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return JWT.sub('[redacted]', value)
    return value


def sanitize_trace(source, destination):
    """Strip HAR credentials, bodies and any JWTs before publishing a trace.

    Screenshots and sources are disabled at collection. Network bodies are omitted
    (the checkpoints retain the necessary public account/list fields).
    """
    with ZipFile(source) as raw, ZipFile(destination, 'w', ZIP_DEFLATED) as clean:
        for entry in raw.infolist():
            if entry.filename.startswith('resources/'):
                continue
            lines = []
            for line in raw.read(entry).decode().splitlines():
                event = json.loads(line)
                if event.get('type') == 'resource-snapshot':
                    snapshot = event['snapshot']
                    for side in ('request', 'response'):
                        data = snapshot.get(side, {})
                        data['headers'] = [h for h in data.get('headers', [])
                                           if not SENSITIVE.search(h['name'])]
                        data.pop('cookies', None)
                        data.pop('postData', None)
                        data.pop('content', None)
                lines.append(json.dumps(redact(event), ensure_ascii=False))
            clean.writestr(entry.filename, '\n'.join(lines)+'\n')


class BrowserEvidence(AbstractContextManager):
    """Trace only the internal admin journey, after activation/login is finished."""
    def __init__(self, context, base, prefix):
        self.context, self.base, self.prefix = context, base, Path(prefix)
        self.events, self.checkpoints = [], []
        self.pages = []

    def watch(self, page):
        self.pages.append(page)
        page.on('pageerror', lambda error: self.events.append({'kind': 'pageerror', 'error': str(error)}))
        page.on('console', lambda message: self.events.append({'kind': 'console', 'error': message.text})
                if message.type == 'error' else None)
        page.on('requestfailed', lambda request: self.events.append({
            'kind': 'requestfailed', 'method': request.method,
            'path': urlsplit(request.url).path, 'failure': request.failure}))
        page.on('response', lambda response: self.events.append({
            'kind': 'response', 'path': urlsplit(response.url).path, 'status': response.status}))

    def __enter__(self):
        self.context.on('page', self.watch)
        for page in self.context.pages:
            self.watch(page)
        self.context.tracing.start(screenshots=False, snapshots=True, sources=False)
        return self

    def checkpoint(self, page, name):
        snapshot = page.evaluate('''() => ({
            path: location.pathname, ready: document.readyState,
            view: typeof state === 'undefined' ? null : state.view,
            pendingRequests: typeof pendingRequests === 'undefined' ? null : pendingRequests,
            account: typeof state === 'undefined' || !state.me ? null : {
                id: state.me.id, email: state.me.email, admin: state.me.admin},
            activeNavigation: document.querySelector('[data-view][aria-current="page"]')?.dataset.view,
            heading: document.querySelector('main h1')?.textContent,
            loginVisible: !!document.querySelector('#login-form'),
            users: [...document.querySelectorAll('[data-user-access]')].map(el=>el.dataset.userAccess),
            toast: document.querySelector('#toast')?.textContent
        })''')
        session = self.context.request.get(self.base+'/api/auth/me')
        snapshot['session_status'] = session.status
        if session.ok:
            user = session.json()
            snapshot['session'] = {k: user.get(k) for k in ('id', 'email', 'admin', 'active', 'roles')}
        self.checkpoints.append({'name': name, **snapshot})
        return snapshot

    def __exit__(self, kind, error, traceback):
        if error:
            for page in self.pages:
                if not page.is_closed():
                    try:
                        self.checkpoint(page, 'failure')
                    except Exception as capture_error:
                        self.events.append({'kind': 'diagnostic-error', 'error': type(capture_error).__name__})
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='framat-private-trace-') as directory:
            raw = Path(directory)/'trace.zip'
            self.context.tracing.stop(path=raw)
            sanitize_trace(raw, self.prefix.with_suffix('.zip'))
        self.prefix.with_suffix('.json').write_text(json.dumps(redact({
            'status': 'failed' if error else 'passed',
            'error': str(error) if error else None,
            'browser': self.context.browser.version,
            'checkpoints': self.checkpoints, 'events': self.events,
        }), indent=2, ensure_ascii=False)+'\n')
        return False
