"""Standalone CI smoke test against an isolated PostgreSQL service."""
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core import SessionLocal, hash_password, engine, PG_SCHEMA
from app.models import User, Role
from app.migrate import migrate, REVISIONS
from app.document_search import search_content

assert PG_SCHEMA == 'framatex_bilal_ci', 'Never run this smoke test against production'
migrate()
migrate()
with SessionLocal() as db:
    assert db.scalar(text('SELECT count(*) FROM schema_migrations')) == len(REVISIONS)
    role = Role(name='Administrateur')
    user = User(name='CI Admin', email='ci@example.test', password_hash=hash_password('Synthetic-Test-Password-42'))
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.execute(text("""INSERT INTO document_content_fts(version_id, content, title, "references")
        VALUES ('synthetic', 'controle textile', 'test', 'ORLI')"""))
    assert 'synthetic' in search_content(db, 'controle textile')
    db.rollback()

with TestClient(app) as client:
    for path in ('/', '/espace-framatex', '/espace-client', '/api/health'):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
    response = client.post('/api/auth/login', headers={'X-Framatex-Request': '1'},
        json={'email': 'ci@example.test', 'password': 'Synthetic-Test-Password-42'})
    assert response.status_code == 200, response.text
    response = client.get('/api/launches')
    assert response.status_code == 200, response.text
print('PostgreSQL initialization, search, pages and login OK')
