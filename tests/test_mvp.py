import io
import os
import tempfile
from pathlib import Path

os.environ["FRAMATEX_DATA_DIR"] = tempfile.mkdtemp(prefix="framat-test-")
os.environ["FRAMATEX_SECRET_KEY"] = "test-secret-" * 6

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User
from app.main import app

HEADERS = {"X-Framatex-Request": "1"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        with SessionLocal() as db:
            admin_role = Role(name="Administrateur")
            worker_role = Role(name="Service réception")
            worker_role.grants.extend([
                RolePermission(action="launch.read", folder_slug=None),
                RolePermission(action="document.read", folder_slug="rose"),
                RolePermission(action="document.write", folder_slug="rose"),
            ])
            admin = User(name="Admin", email="admin@test.local", password_hash=hash_password("AdminPassword2026!"))
            worker = User(name="Réception", email="reception@test.local", password_hash=hash_password("WorkerPassword2026!"))
            admin.roles.append(admin_role)
            worker.roles.append(worker_role)
            db.add_all([admin, worker]); db.commit()
        yield c


def login(c, email, password):
    return c.post("/api/auth/login", json={"email": email, "password": password}, headers=HEADERS)


def test_bootstrap_login_and_create_without_orli(client):
    assert client.get("/api/launches").status_code == 401
    assert login(client, "admin@test.local", "AdminPassword2026!").status_code == 200
    r = client.post("/api/launches", json={"name": "Vestes test", "client_name": "Client fictif"}, headers=HEADERS)
    assert r.status_code == 201, r.text
    assert r.json()["orli_ref"] is None
    assert r.json()["status"] == "À compléter"
    assert len(r.json()["id"]) == 36
    d = client.get("/api/launches/" + r.json()["id"]).json()
    assert {x["slug"] for x in d["folders"]} == {"jaune", "rose", "bleu", "vert"}
    client.app.state.launch_id = r.json()["id"]
    patch = client.patch("/api/launches/"+r.json()["id"], json={"orli_ref":"L-2026-031", "status":"En cours"}, headers=HEADERS)
    assert patch.status_code == 200
    assert patch.json()["orli_ref"] == "L-2026-031"


def test_upload_versions_and_download(client):
    lid = client.app.state.launch_id
    bad = client.post(f"/api/launches/{lid}/documents", data={"folder":"jaune","title":"Fiche"}, files={"file":("fake.pdf",b"not a pdf","application/pdf")}, headers=HEADERS)
    assert bad.status_code == 422
    r=client.post(f"/api/launches/{lid}/documents",data={"folder":"jaune","title":"Fiche technique","doc_type":"Fiche d’emploi"},files={"file":("fiche.txt",b"ancienne consommation 1.8 m","text/plain")},headers=HEADERS)
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    assert r.json()["latest"]["number"] == 1
    new = client.post(f"/api/documents/{doc_id}/versions",files={"file":("fiche-v2.txt",b"nouvelle consommation 1.9 m","text/plain")},headers=HEADERS)
    assert new.status_code == 201, new.text
    assert len(new.json()["versions"]) == 2
    old = client.get(f"/api/documents/{doc_id}/versions/1/download")
    now = client.get(f"/api/documents/{doc_id}/versions/2/download")
    assert old.content == b"ancienne consommation 1.8 m"
    assert now.content == b"nouvelle consommation 1.9 m"
    assert old.headers["content-disposition"].startswith("attachment")
    client.app.state.doc_id = doc_id


def test_permission_is_enforced_on_server(client):
    assert login(client,"reception@test.local","WorkerPassword2026!").status_code == 200
    lid=client.app.state.launch_id
    view=client.get(f"/api/launches/{lid}").json()
    jaune=next(f for f in view["folders"] if f["slug"]=="jaune")
    rose=next(f for f in view["folders"] if f["slug"]=="rose")
    assert jaune["can_read"] is False and jaune["documents"] == []
    assert rose["can_read"] is True
    doc_id=client.app.state.doc_id
    assert client.get(f"/api/documents/{doc_id}/versions/1/download").status_code == 403
    denied = client.post(f"/api/launches/{lid}/documents", data={"folder":"jaune","title":"Interdit"},files={"file":("test.txt",b"test","text/plain")},headers=HEADERS)
    assert denied.status_code == 403
    allowed = client.post(f"/api/launches/{lid}/documents",data={"folder":"rose","title":"BL"},files={"file":("bl.txt",b"1234","text/plain")},headers=HEADERS)
    assert allowed.status_code == 201
    assert client.get('/api/admin/users').status_code == 403
    assert client.patch(f"/api/launches/{lid}",json={"status":"Clôturé"},headers=HEADERS).status_code == 403


def test_csrf_header_and_admin_audit(client):
    assert client.post('/api/auth/logout').status_code == 403
    assert client.post('/api/auth/logout',headers=HEADERS).status_code==200
    assert login(client,"admin@test.local","AdminPassword2026!").status_code==200
    events=client.get('/api/admin/audit')
    assert events.status_code==200
    assert any(x['action']=='document.version.add' for x in events.json())
    assert client.get('/api/dashboard').json()['versions'] >= 3
