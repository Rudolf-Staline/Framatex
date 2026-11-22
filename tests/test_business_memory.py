"""Mémoire métier : identité stable, visibilité des dossiers et historique conservé."""
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, hash_password
from app.main import app
from app.models import Role, RolePermission, User
from app.internal_models import ExperienceNote

H = {'X-Framatex-Request': '1'}
PASSWORD = 'BusinessMemoryRecipe2026!'


@pytest.fixture(scope='module')
def setup():
    suffix = uuid.uuid4().hex[:10]
    with TestClient(app) as admin:
        with SessionLocal() as db:
            role = db.scalar(select(Role).where(Role.name == 'Administrateur'))
            if not role:
                role = Role(name='Administrateur'); db.add(role)
            worker_role = Role(name='Mémoire limitée ' + suffix, grants=[RolePermission(action='launch.read'),
                RolePermission(action='document.read', folder_slug='jaune'), RolePermission(action='document.write', folder_slug='jaune')])
            admin_user = User(email=f'bm-admin-{suffix}@example.test', name='Admin mémoire',
                password_hash=hash_password(PASSWORD), roles=[role])
            worker = User(email=f'bm-worker-{suffix}@example.test', name='Collaborateur mémoire',
                password_hash=hash_password(PASSWORD), roles=[worker_role])
            db.add_all([admin_user, worker]); db.commit()
        assert admin.post('/api/auth/login', headers=H, json={'email': admin_user.email, 'password': PASSWORD}).status_code == 200
        launch = admin.post('/api/launches', headers=H, json={'name': 'Commande mémoire ' + suffix}).json()
        other = admin.post('/api/launches', headers=H, json={'name': 'Commande privée ' + suffix}).json()
        assert admin.put(f"/api/launches/{other['id']}/access", headers=H, json={'restricted': True}).status_code == 200
        yield {'admin': admin, 'launch': launch, 'other': other, 'worker_email': worker.email, 'suffix': suffix}


def test_partner_unique_lookup_legacy_and_note_flow(setup):
    api, lid = setup['admin'], setup['launch']['id']
    name = 'Tissage Atlas ' + setup['suffix']
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == f"bm-admin-{setup['suffix']}@example.test"))
        old = ExperienceNote(launch_id=lid, party_type='fournisseur', party_name='  TISSAGE   ÁTLAS ' + setup['suffix'],
            category='retard', body='Livraison avec douze jours de retard.', author_id=user.id)
        db.add(old); db.commit(); old_id = old.id
    created = api.post('/api/workspace/partners', headers=H, json={'party_type':'fournisseur','name':name})
    assert created.status_code == 201, created.text
    partner = created.json()
    assert api.post('/api/workspace/partners', headers=H, json={'party_type':'fournisseur','name':'TISSAGE  ATLAS ' + setup['suffix']}).status_code == 409
    lookup = api.get('/api/workspace/partners', params={'q':name.lower()}).json()
    assert any(item['id'] == partner['id'] and item['match'] == 'exact' for item in lookup)
    assert any(item['id'] == partner['id'] for item in api.get('/api/workspace/partners', params={'q':'tissage atla ' + setup['suffix']}).json())
    detail = api.get(f"/api/workspace/partners/{partner['id']}").json()
    assert any(n['id'] == old_id for n in detail['notes'])
    similar = api.post('/api/workspace/partners', headers=H, json={'party_type':'fournisseur','name':'Tissage Atlas Sud ' + setup['suffix']})
    assert similar.status_code == 201 and similar.json()['id'] != partner['id']
    assert api.post(f'/api/launches/{lid}/partners', headers=H, json={'partner_id':partner['id']}).status_code == 201
    assert api.post(f'/api/launches/{lid}/partners', headers=H, json={'partner_id':partner['id']}).status_code == 201
    assert len(api.get(f'/api/launches/{lid}/partners').json()) == 1
    for category in ('documentaire','retour'):
        result = api.post('/api/workspace/business-memory', headers=H, json={'partner_id':partner['id'],
            'launch_id':lid,'category':category,'event_date':'2026-11-12','body':'Faits contrôlés sur la commande précédente.',
            'importance':'important','recommendation':'Confirmer les documents avant expédition.'})
        assert result.status_code == 201, result.text
    general = api.post('/api/workspace/business-memory', headers=H, json={'partner_id':partner['id'],
        'category':'incident','event_date':'2026-11-13','body':'Incident général documenté pour ce fournisseur.',
        'importance':'critique'})
    assert general.status_code == 201, general.text
    vigilance = api.get(f"/api/workspace/partners/{partner['id']}/vigilance").json()
    assert vigilance['counts']['open_vigilance'] >= 2
    assert any(item['launch_id'] is None for item in vigilance['items'])
    closed = api.patch(f"/api/workspace/business-memory/{general.json()['id']}", headers=H,
        json={'status':'resolved','reason':'Action vérifiée après réception complète.'})
    assert closed.status_code == 200 and closed.json()['status'] == 'resolved'
    decisions = api.get(f"/api/workspace/business-memory/{general.json()['id']}/decisions").json()
    assert decisions[0]['action'] == 'close'
    report = api.get('/api/workspace/business-memory', params={'q':setup['suffix'],'category':'incident','status':'resolved'}).json()
    assert any(item['id'] == general.json()['id'] for item in report['items'])
    setup['partner'] = partner


def test_internal_only_and_persistence(setup):
    api, partner = setup['admin'], setup['partner']
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/workspace/business-memory').status_code == 401
        assert anonymous.get(f"/api/workspace/partners/{partner['id']}").status_code == 401
        assert anonymous.get(f"/api/workspace/partners/{partner['id']}/vigilance").status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(ExperienceNote).where(ExperienceNote.partner_id == partner['id'])) is not None
    assert api.get(f"/api/workspace/partners/{partner['id']}").json()['counts']['documentaire'] >= 1


def test_restricted_launch_notes_are_not_in_memory_results(setup):
    admin, hidden = setup['admin'], setup['other']['id']
    partner = setup['partner']
    secret = admin.post('/api/workspace/business-memory', headers=H, json={'partner_id':partner['id'],
        'launch_id':hidden,'category':'incident','event_date':'2026-11-14',
        'body':'Incident privé lié uniquement au dossier restreint.', 'importance':'critique'})
    assert secret.status_code == 201, secret.text
    private_partner = admin.post('/api/workspace/partners', headers=H,
        json={'party_type':'atelier','name':'Atelier privé ' + setup['suffix']}).json()
    assert admin.post(f'/api/launches/{hidden}/partners', headers=H,
        json={'partner_id':private_partner['id']}).status_code == 201
    with TestClient(app) as worker:
        assert worker.post('/api/auth/login', headers=H,
            json={'email':setup['worker_email'],'password':PASSWORD}).status_code == 200
        ids = {row['id'] for row in worker.get('/api/workspace/business-memory').json()['items']}
        assert secret.json()['id'] not in ids
        assert worker.get(f"/api/workspace/business-memory/{secret.json()['id']}/decisions").status_code == 404
        assert worker.patch(f"/api/workspace/business-memory/{secret.json()['id']}", headers=H,
            json={'status':'resolved','reason':'Vérification interdite pour ce dossier.'}).status_code == 404
        assert all(row['id'] != secret.json()['id'] for row in worker.get(f"/api/workspace/partners/{partner['id']}").json()['notes'])
        assert worker.get(f"/api/workspace/partners/{private_partner['id']}").status_code == 404
        assert all(row['id'] != private_partner['id'] for row in worker.get('/api/workspace/partners').json())


def test_legacy_migration_preserves_note_and_allows_general_note(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, text, inspect
    from app.core import Base
    import app.migrate as migrator
    path = tmp_path / 'ancienne.sqlite'
    isolated = create_engine(f'sqlite:///{path}')
    Base.metadata.create_all(isolated)
    with isolated.begin() as conn:
        conn.execute(text('DROP TABLE internal_experience_notes'))
        conn.execute(text('''CREATE TABLE internal_experience_notes (
            id VARCHAR(36) PRIMARY KEY, launch_id VARCHAR(36) NOT NULL,
            party_type VARCHAR(20) NOT NULL, party_name VARCHAR(150) NOT NULL,
            category VARCHAR(30) NOT NULL, body TEXT NOT NULL,
            author_id VARCHAR(36) NOT NULL, created_at DATETIME NOT NULL)'''))
        conn.execute(text("INSERT INTO internal_experience_notes VALUES ('old', 'launch', 'fournisseur', 'Atelier ancien', 'retard', 'Historique conservé', 'author', '2026-01-01')"))
        for revision in migrator.REVISIONS[:-1]:
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'), {'v':revision,'d':'2026-01-01'})
    monkeypatch.setattr(migrator, 'engine', isolated)
    migrator.migrate()
    with isolated.connect() as conn:
        assert conn.execute(text("SELECT body, updated_at FROM internal_experience_notes WHERE id='old'")).one() == ('Historique conservé', '2026-01-01')
        assert next(c for c in inspect(conn).get_columns('internal_experience_notes') if c['name']=='launch_id')['nullable']
        assert 'business_partners' in inspect(conn).get_table_names()
    isolated.dispose()


def test_client_account_mapping_is_explicit_and_client_cannot_read_memory(setup):
    admin = setup['admin']
    name = 'Client mémoire ' + setup['suffix']
    existing = admin.post('/api/workspace/partners', headers=H,
        json={'party_type':'client','name':name})
    assert existing.status_code == 201, existing.text
    with TestClient(app) as client:
        account = client.post('/api/client/register', headers=H, json={
            'raison_sociale':name,'nom_contact':'Contact recette','email':f"bm-client-{setup['suffix']}@example.test",
            'telephone':'0600000000','adresse':'1 rue de la Recette','pays':'Maroc','password':PASSWORD})
        assert account.status_code == 201, account.text
        account_id = account.json()['id']
        assert admin.patch(f'/api/admin/clients/{account_id}/status', headers=H,
            json={'status':'active'}).status_code == 200
        candidates = admin.get('/api/workspace/partners', params={'q':name,'party_type':'client'}).json()
        assert len([row for row in candidates if row['name'] == name]) == 1
        assert candidates[0]['client_account_id'] is None
        linked = admin.post(f"/api/workspace/partners/{existing.json()['id']}/client-account",
            headers=H, json={'client_account_id':account_id})
        assert linked.status_code == 200 and linked.json()['client_account_id'] == account_id
        assert admin.post(f"/api/workspace/partners/{existing.json()['id']}/client-account",
            headers=H, json={'client_account_id':account_id}).status_code == 200
        assert client.post('/api/client/login', headers=H,
            json={'email':account.json()['email'],'password':PASSWORD}).status_code == 200
        assert client.get('/api/workspace/business-memory').status_code == 401
        assert client.get(f"/api/workspace/partners/{existing.json()['id']}").status_code == 401
        assert client.get(f"/api/workspace/partners/{existing.json()['id']}/vigilance").status_code == 401
