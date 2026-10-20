"""Folder switches must enforce read-only and write scope on the real API."""
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core import Base, get_current_user, get_db
from app.main import app, permitted, STORAGE
from app.models import Role, User, DocumentVersion
from tools.migrate_global_library import apply_upgrade

HEADERS = {'X-Framatex-Request': '1'}

@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(name='Administratrice', email='admin@roles.invalid', password_hash='unused', roles=[Role(name='Administrateur')])
        db.add(admin); db.commit(); admin_id = admin.id
    apply_upgrade(engine)
    current = {'id': admin_id}
    def database():
        with Session(engine) as db:
            yield db
    def authenticated(db=Depends(get_db)):
        return db.get(User, current['id'])
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = authenticated
    try:
        yield TestClient(app), engine, current
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        with Session(engine) as db:
            for version in db.scalars(select(DocumentVersion)):
                (STORAGE / version.disk_name).unlink(missing_ok=True)
        engine.dispose()


def create_user(client, engine, name, flags):
    response = client.post('/api/admin/roles', headers=HEADERS, json={'name': name, 'folder_access': flags})
    assert response.status_code == 201, response.text
    with Session(engine) as db:
        role = db.get(Role, response.json()['id'])
        user = User(name=name, email=name+'@roles.invalid', password_hash='unused', roles=[role])
        db.add(user); db.commit(); return user.id, role.id


def test_simple_roles_enforce_folder_scope_and_read_only(setup):
    client, engine, current = setup
    admin_id = current['id']
    viewer, viewer_role = create_user(client, engine, 'Lecture', {'jaune': {'access': True, 'modify': False}})
    editor, editor_role = create_user(client, engine, 'Réception', {'rose': {'access': True, 'modify': True}})
    roles = client.get('/api/admin/roles').json()
    role = next(r for r in roles if r['id'] == viewer_role)
    assert role['folder_access']['jaune'] == {'access': True, 'modify': False}
    assert role['folder_access']['rose'] == {'access': False, 'modify': False}
    assert all(v == {'access': True, 'modify': True} for v in next(r for r in roles if r['name'] == 'Administrateur')['folder_access'].values())
    current['id'] = viewer
    folders = client.get('/api/dossier-jaune').json()['folders']
    assert next(f for f in folders if f['slug'] == 'jaune')['can_read']
    assert not next(f for f in folders if f['slug'] == 'jaune')['can_write']
    assert not next(f for f in folders if f['slug'] == 'rose')['can_read']
    def deposit(folder):
        return client.post('/api/dossier-jaune/documents', headers=HEADERS, data={'folder': folder, 'title': 'Notice', 'doc_type': 'Notice'}, files={'file': ('notice.txt', b'Contenu de test', 'text/plain')})
    assert deposit('jaune').status_code == 403
    assert client.get('/api/admin/roles').status_code == 403
    assert client.post('/api/admin/roles', headers=HEADERS, json={'name': 'Interdit', 'folder_access': {}}).status_code == 403
    current['id'] = editor
    assert deposit('jaune').status_code == 403
    saved = deposit('rose')
    assert saved.status_code == 201, saved.text
    listing = client.get('/api/dossier-jaune').json()
    rose = next(f for f in listing['folders'] if f['slug'] == 'rose')
    assert rose['documents'][0]['latest']['uploaded_by'] == 'Réception'
    assert rose['documents'][0]['latest']['size'] == len(b'Contenu de test')
    assert 'email' not in rose['documents'][0]['latest']
    # The last depositor may differ from the document creator.
    with Session(engine) as db:
        first = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == saved.json()['id']))
        db.add(DocumentVersion(document_id=first.document_id, number=2,
            original_name='notice-v2.txt', disk_name='simple-role-version-'+first.id,
            content_type='text/plain', size=42, sha256='b'*64, uploaded_by=admin_id))
        db.commit()
    latest = next(f for f in client.get('/api/dossier-jaune').json()['folders'] if f['slug'] == 'rose')['documents'][0]['latest']
    assert latest['uploaded_by'] == 'Administratrice'
    assert latest['size'] == 42 and latest['original_name'] == 'notice-v2.txt'
    current['id'] = viewer
    assert not next(f for f in client.get('/api/dossier-jaune').json()['folders'] if f['slug'] == 'rose')['documents']
    with Session(engine) as db:
        user = db.get(User, editor)
        assert permitted(user, 'document.read', 'rose')
        assert permitted(user, 'rex.write', 'rose')
        assert permitted(user, 'completeness.review', 'rose')
        assert not permitted(user, 'document.write', 'jaune')
        assert not permitted(user, 'launch.create')
        assert not permitted(user, 'launch.update')
    current['id'] = admin_id


@pytest.mark.parametrize('fields', [
    {'folder_access': {'jaune': {'access': False, 'modify': True}}},
    {'folder_access': {'jaune': {'access': 'true', 'modify': False}}},
    {'folder_access': {'inconnu': {'access': True}}},
    {'folder_access': {'jaune': {'access': True, 'admin': True}}},
    {'folder_access': {'jaune': {'access': True}}, 'permissions': [{'action': 'launch.create'}]},
])
def test_invalid_or_mixed_role_flags_rejected(setup, fields):
    client, _, _ = setup
    response = client.post('/api/admin/roles', headers=HEADERS, json={'name': 'Essai', **fields})
    assert response.status_code == 422, response.text


def test_legacy_roles_stay_compatible_and_system_role_is_reserved(setup):
    client, engine, _ = setup
    response = client.post('/api/admin/roles', headers=HEADERS, json={'name': 'Historique', 'permissions': [{'action': 'document.read', 'folder': 'vert'}]})
    assert response.status_code == 201
    exported = next(r for r in client.get('/api/admin/roles').json() if r['id'] == response.json()['id'])
    assert exported['folder_access']['vert'] == {'access': True, 'modify': False}
    assert len(exported['permissions']) == 1
    for name in [' Administrateur ', '  ']:
        assert client.post('/api/admin/roles', headers=HEADERS, json={'name': name, 'folder_access': {}}).status_code == 422
