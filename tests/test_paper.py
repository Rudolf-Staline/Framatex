"""Version 0.6 — QR paper bridge and version-specific integrity passport."""
import os
import tempfile
from pathlib import Path

os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-paper-')
os.environ['FRAMATEX_SECRET_KEY'] = 'paper-test-secret-key-' * 3
os.environ['FRAMATEX_PUBLIC_BASE_URL'] = 'http://127.0.0.1:8000'

import pytest
from fastapi.testclient import TestClient
from app.main import app, STORAGE
from app.core import Base, engine, SessionLocal, hash_password
from app.models import Role, RolePermission, User

H = {'X-Framatex-Request': '1'}

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            observer=Role(name='Réception',grants=[RolePermission(action='launch.read'),
                    RolePermission(action='document.read',folder_slug='rose')])
            db.add_all([User(name='Admin',email='admin@paper.local',password_hash=hash_password('StrongPassword11!'),roles=[admin]),
                        User(name='Réception',email='reception@paper.local',password_hash=hash_password('StrongPassword11!'),roles=[observer])])
            db.commit()
        login(c, 'admin@paper.local')
        yield c
    Base.metadata.drop_all(engine)


def login(c,email):
    assert c.post('/api/auth/login',json={'email':email,'password':'StrongPassword11!'},headers=H).status_code==200


def launch(c):
    r=c.post('/api/launches',json={'name':'Lancement sans ORLI'},headers=H)
    assert r.status_code==201
    return r.json()['id']


def upload(c,lid,folder='jaune',name='fiche.txt',content=b'original'):
    r=c.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':'Fiche d emploi','doc_type':'Fiche d emploi'},files={'file':(name,content)},headers=H)
    assert r.status_code==201,r.text
    return r.json()


def test_qr_is_scannable_label_not_authentication(client):
    lid=launch(client)
    result=client.get(f'/api/launches/{lid}/paper-link')
    assert result.status_code==200
    assert result.json()['url']==f'http://127.0.0.1:8000/#/launch/{lid}'
    assert result.json()['requires_authentication'] and not result.json()['is_access_token']
    pic=client.get(f'/api/launches/{lid}/paper-qr.png')
    assert pic.status_code==200 and pic.content.startswith(b'\x89PNG\r\n\x1a\n')
    assert pic.headers['cache-control']=='private, no-store'
    label=client.get(f'/api/launches/{lid}/paper-label')
    assert label.status_code==200 and lid in label.text
    assert 'data:image/png;base64' in label.text
    client.post('/api/auth/logout',headers=H)
    assert client.get(f'/api/launches/{lid}/paper-qr.png').status_code==401
    assert client.get(f'/api/launches/{lid}/paper-label').status_code==401


def test_qr_ignores_untrusted_request_host_and_checks_configuration(client,monkeypatch):
    lid=launch(client)
    r=client.get(f'/api/launches/{lid}/paper-link',headers={'host':'evil.invalid'})
    assert r.status_code==200 and 'evil.invalid' not in r.json()['url']
    monkeypatch.setenv('FRAMATEX_PUBLIC_BASE_URL','https://example.test/redirect?token=abc')
    assert client.get(f'/api/launches/{lid}/paper-link').status_code==503


def test_passport_detects_storage_tampering_and_old_versions(client):
    lid=launch(client)
    doc=upload(client,lid)
    ver=doc['latest']['id']
    passport=client.get(f'/api/document-versions/{ver}/passport')
    assert passport.status_code==200
    a=passport.json()
    assert a['version']==1 and a['is_current'] and a['integrity']['status']=='intact'
    assert len(a['sha256_registered'])==64
    assert a['uploader']['name']=='Admin'
    from app.models import DocumentVersion
    with SessionLocal() as db:
        path=STORAGE/db.get(DocumentVersion,ver).disk_name
    path.write_bytes(b'changed!')
    corrupt=client.get(f'/api/document-versions/{ver}/passport').json()
    assert corrupt['integrity']['status']=='mismatch'
    path.unlink()
    missing=client.get(f'/api/document-versions/{ver}/passport').json()
    assert missing['integrity']['status']=='missing'
    nextv=client.post(f'/api/documents/{doc["id"]}/versions',files={'file':('new.txt',b'v2')},headers=H)
    assert nextv.status_code==201
    latest=nextv.json()['latest']['id']
    fresh=client.get(f'/api/document-versions/{latest}/passport').json()
    assert fresh['is_current'] and fresh['previous_version']['id']==ver
    assert not client.get(f'/api/document-versions/{ver}/passport').json()['is_current']


def test_permission_filter_and_non_existing_passport(client):
    lid=launch(client)
    doc=upload(client,lid,'jaune')
    hidden=doc['latest']['id']
    rose=upload(client,lid,'rose')
    visible=rose['latest']['id']
    login(client,'reception@paper.local')
    assert client.get(f'/api/document-versions/{hidden}/passport').status_code==403
    assert client.get(f'/api/document-versions/{visible}/passport').status_code==200
    assert client.get('/api/document-versions/missing/passport').status_code==404
    assert client.get('/api/launches/non-existing/paper-qr.png').status_code==404
