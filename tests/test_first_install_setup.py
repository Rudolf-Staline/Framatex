"""Use a separate temporary database; never touch a shared or production database."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import setup_routes
from app.core import Base, check_password
from app.main import app
from app.models import AuditEvent, Role, User

SECRET = "only-for-isolated-test-instance-0123456789"
H = {"X-Framatex-Request": "1", "X-Framatex-Setup-Token": SECRET}
PAYLOAD = {"name": "Test installation", "email": "first@example.test",
           "password": "Test-only-long-password-123"}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'setup.sqlite'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(setup_routes, "SessionLocal", sessions)
    monkeypatch.setenv("FRAMATEX_SETUP_SECRET", SECRET)
    yield sessions
    engine.dispose()


def test_disabled_and_wrong_secret(isolated, monkeypatch):
    c = TestClient(app)
    monkeypatch.delenv("FRAMATEX_SETUP_SECRET")
    assert c.get("/setup").status_code == 404
    assert c.post("/api/setup", headers=H, json=PAYLOAD).status_code == 404
    monkeypatch.setenv("FRAMATEX_SETUP_SECRET", "short")
    assert c.get("/setup").status_code == 404
    monkeypatch.setenv("FRAMATEX_SETUP_SECRET", SECRET)
    assert c.get("/setup").status_code == 200
    assert c.post("/api/setup", headers={**H, "X-Framatex-Setup-Token": "wrong"}, json=PAYLOAD).status_code == 404
    assert c.post("/api/setup", headers={"X-Framatex-Setup-Token": SECRET}, json=PAYLOAD).status_code == 403


def test_create_once_and_audit(isolated):
    c = TestClient(app)
    bad = dict(PAYLOAD, password="short-secret")
    result = c.post("/api/setup", headers=H, json=bad)
    assert result.status_code == 422 and bad["password"] not in result.text
    assert c.post("/api/setup", headers=H, json=PAYLOAD).status_code == 201
    with isolated() as db:
        user = db.scalar(select(User))
        assert user.email == PAYLOAD["email"] and user.active
        assert [r.name for r in user.roles] == ["Administrateur"]
        assert check_password(user.password_hash, PAYLOAD["password"])
        assert db.scalar(select(AuditEvent)).action == "installation.completed"
    assert c.get("/setup").status_code == 404
    assert c.post("/api/setup", headers=H, json=PAYLOAD).status_code == 404


def test_refuses_existing_disabled_account(isolated):
    with isolated() as db:
        db.add(User(name="Existing", email="existing@example.test", active=False,
                    password_hash="test-unused", roles=[Role(name="Administrateur")]))
        db.commit()
    c = TestClient(app)
    assert c.get("/setup").status_code == 404
    assert c.post("/api/setup", headers=H, json=PAYLOAD).status_code == 404
    with isolated() as db:
        assert len(db.scalars(select(User)).all()) == 1


def test_concurrent_initialization(isolated):
    def create(i):
        c = TestClient(app)
        return c.post("/api/setup", headers=H,
                      json=dict(PAYLOAD, email=f"first{i}@example.test")).status_code
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(create, range(2))) == [201, 404]
    with isolated() as db:
        assert len(db.scalars(select(User)).all()) == 1
