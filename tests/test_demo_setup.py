"""One-time guarded demo administrator setup: never a public sign-up route."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core import Base, get_db
from app.main import app
from app.models import User


def test_first_admin_requires_token_and_closes(monkeypatch, tmp_path):
    monkeypatch.setenv('FRAMATEX_SETUP_TOKEN', 'T' * 48)
    eng=create_engine('sqlite:///' + str(tmp_path/'setup.db'))
    Base.metadata.create_all(eng)

    def override_db():
        with Session(eng) as session:
            yield session

    app.dependency_overrides[get_db]=override_db
    try:
        client=TestClient(app)
        payload={'token':'T'*48,'email':'Demo@framat.invalid','name':'Administrateur Démo','password':'StrongDemoPassword2026!'}
        headers={'X-Framatex-Request':'1'}
        assert client.get('/setup').status_code == 200
        assert client.post('/api/setup/first-admin',json=payload).status_code == 403
        assert client.post('/api/setup/first-admin',json={**payload,'token':'A'*48},headers=headers).status_code == 403
        made=client.post('/api/setup/first-admin',json=payload,headers=headers)
        assert made.status_code == 200, made.text
        assert made.json()['email'] == 'demo@framat.invalid'
        again=client.post('/api/setup/first-admin',json=payload,headers=headers)
        assert again.status_code == 409
        with Session(eng) as db:
            user=db.scalar(select(User).where(User.email=='demo@framat.invalid'))
            assert user is not None
            assert [role.name for role in user.roles] == ['Administrateur']
    finally:
        app.dependency_overrides.clear()
        eng.dispose()
