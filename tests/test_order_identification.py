"""Fiche commande : préparation progressive, conservation et contrôle des droits."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import Base, get_db, make_token, COOKIE
from app.main import app
from app.models import Role, RolePermission, User
from tools.migrate_order_identification import apply_to_connection


@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        admin = User(email='order-admin@example.test', name='Admin', password_hash='unused', roles=[Role(name='Administrateur')])
        reader = User(email='order-reader@example.test', name='Lecture', password_hash='unused', roles=[Role(name='Lecture commandes', grants=[RolePermission(action='launch.read')])])
        db.add_all([admin, reader]);db.commit()
        ids = admin.id, reader.id
    from app import access
    monkeypatch.setattr(access, 'SessionLocal', sessions)
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    c = TestClient(app)
    c.cookies.set(COOKIE, make_token(ids[0]))
    try:
        yield c, ids
    finally:
        c.close()
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


HEADERS = {'X-Framatex-Request': '1'}


def test_create_complete_and_clear_provisional_fields(client):
    c, _ = client
    fields = c.get('/api/launch-fields').json()['fields']
    assert {'workshop', 'order_ref', 'client_name'} <= {f['key'] for f in fields}
    assert [f['key'] for f in fields if f.get('required')] == ['name']
    created = c.post('/api/launches', json={'name': 'Commande à préparer'}, headers=HEADERS)
    assert created.status_code == 201, created.text
    data = created.json();lid = data['id']
    assert data['identification'] == {} and data['orli_ref'] is None
    saved = c.patch('/api/launches/'+lid, json={'client_name': 'Maison test', 'order_ref': 'CMD-012', 'identification': {'workshop':' Atelier A ', 'quantity':1200, 'program':'Automne', 'delivery_date':'2026-12-01'}}, headers=HEADERS)
    assert saved.status_code == 200, saved.text
    assert saved.json()['identification']['workshop'] == 'Atelier A'
    patch = c.patch('/api/launches/'+lid, json={'identification': {'quantity':1500, 'program':None}}, headers=HEADERS)
    assert patch.status_code == 200, patch.text
    info = c.get('/api/launches/'+lid).json()
    assert info['identification'] == {'workshop':'Atelier A', 'quantity':1500, 'program':None, 'delivery_date':'2026-12-01'}
    assert info['order_ref'] == 'CMD-012'
    assert {f['slug'] for f in info['folders']} == {'jaune','rose','bleu','vert'}


@pytest.mark.parametrize('identification', [{'quantity':-1}, {'quantity':True}, {'quantity':1.5}, {'delivery_date':'invalid'}, {'workshop':'x'*151}, {'unexpected':'value'}])
def test_invalid_field_values_do_not_create_orders(client, identification):
    c, _ = client
    assert c.post('/api/launches', json={'name':'Test', 'identification':identification}, headers=HEADERS).status_code == 422
    assert c.get('/api/launches').json() == []


def test_reader_cannot_modify_identification(client):
    c, (_, reader) = client
    saved = c.post('/api/launches', json={'name':'Commande visible'}, headers=HEADERS).json()
    c.cookies.set(COOKIE, make_token(reader))
    assert c.get('/api/launches/'+saved['id']).status_code == 200
    assert c.patch('/api/launches/'+saved['id'], json={'identification':{'workshop':'Interdit'}}, headers=HEADERS).status_code == 403


def test_migration_preserves_existing_rows_and_is_repeatable():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE launches (id TEXT PRIMARY KEY, name TEXT NOT NULL)'))
        conn.execute(text("INSERT INTO launches VALUES ('old', 'Historique')"))
        apply_to_connection(conn);apply_to_connection(conn)
        assert conn.execute(text('SELECT id, name, identification_json FROM launches')).one() == ('old','Historique','{}')
        assert 'identification_json' in {c['name'] for c in inspect(conn).get_columns('launches')}
    engine.dispose()
