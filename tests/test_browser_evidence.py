"""Publish synthetic UI evidence without carrying authentication material."""
import json
from zipfile import ZipFile
from tools.browser_evidence import sanitize_trace


def test_trace_excludes_credentials_and_network_bodies(tmp_path):
    token = 'eyJsynthetic.eyJpayload.signature'
    raw, clean = tmp_path/'raw.zip', tmp_path/'clean.zip'
    network = {'type': 'resource-snapshot', 'snapshot': {
        'request': {'url': 'http://127.0.0.1/api/admin/users?token=private-query',
                    'headers': [{'name': 'Cookie', 'value': 'session=private-cookie'},
                                {'name': 'Authorization', 'value': 'private-auth'},
                                {'name': 'Accept', 'value': 'application/json'}],
                    'cookies': [{'name': 'session', 'value': 'private-cookie'}],
                    'postData': {'text': 'private-password'}},
        'response': {'status': 200, 'headers': [{'name': 'Set-Cookie', 'value': 'private-session'}],
                     'cookies': [{'value': 'private-session'}],
                     'content': {'_sha1': 'private-body'}}}}
    with ZipFile(raw, 'w') as archive:
        archive.writestr('trace.network', json.dumps(network)+'\n')
        archive.writestr('trace.trace', json.dumps({'type': 'console', 'text': token})+'\n')
        archive.writestr('trace.stacks', json.dumps({'files': ['synthetic.py']}))
        archive.writestr('resources/private-body', b'private-response-body')
    sanitize_trace(raw, clean)
    with ZipFile(clean) as archive:
        assert not any(name.startswith('resources/') for name in archive.namelist())
        serialized = '\n'.join(archive.read(name).decode() for name in archive.namelist())
        for secret in (token, 'private-cookie', 'private-auth', 'private-password',
                       'private-session', 'private-body', 'private-query'):
            assert secret not in serialized
        snapshot = json.loads(archive.read('trace.network'))['snapshot']
        assert snapshot['response']['status'] == 200
        assert snapshot['request']['url'] == 'http://127.0.0.1/api/admin/users'
        assert snapshot['request']['headers'] == [{'name': 'Accept', 'value': 'application/json'}]
