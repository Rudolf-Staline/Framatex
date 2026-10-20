"""HTTP deposit into the single Dossier Jaune on a disposable database."""
from io import BytesIO

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import Base, get_current_user, get_db
from app.main import app, STORAGE
from app.models import Document, DocumentVersion, Role, User, AuditEvent
from app.global_library_models import GlobalDocumentEntry, GlobalLibraryConfig
from tools.migrate_global_library import apply_upgrade


def test_global_document_http_deposit_read_and_orli_update():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(name="Test", email="global@example.invalid", password_hash="unused",
                     roles=[Role(name="Administrateur")])
        db.add(admin)
        db.commit()
        admin_id = admin.id
    apply_upgrade(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    def override_auth(db: Session = Depends(get_db)):
        return db.get(User, admin_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_auth
    try:
        client = TestClient(app)
        response = client.post(
            "/api/dossier-jaune/documents",
            headers={"X-Framatex-Request": "1"},
            data={"folder": "vert", "title": "Facture de démonstration",
                  "doc_type": "Facture", "orli_ref": ""},
            files={"file": ("demo.txt", b"Essai dossier unique", "text/plain")},
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["folder"] == "vert"
        assert saved["orli_ref"] is None
        assert saved["latest"]["number"] == 1

        listing = client.get("/api/dossier-jaune")
        assert listing.status_code == 200, listing.text
        data = listing.json()
        assert data["unique"] is True
        assert len(data["folders"]) == 4
        green = next(x for x in data["folders"] if x["slug"] == "vert")
        assert any(d["id"] == saved["id"] for d in green["documents"])

        patched = client.patch(
            f"/api/dossier-jaune/documents/{saved['id']}/reference",
            headers={"X-Framatex-Request": "1"},
            json={"orli_ref": "ORLI-NEW"}
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["orli_ref"] == "ORLI-NEW"

        with Session(engine) as db:
            assert len(db.scalars(select(GlobalLibraryConfig)).all()) == 1
            assert len(db.scalars(select(Document)).all()) == 1
            row = db.get(GlobalDocumentEntry, saved["id"])
            assert row.folder_slug == "vert"
            assert row.orli_overridden is True
            versions = db.scalars(select(DocumentVersion)).all()
            assert len(versions) == 1
            assert versions[0].number == 1
            assert any(x.action == "document.reference.update"
                       for x in db.scalars(select(AuditEvent)))
            disk_name = versions[0].disk_name
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        if "disk_name" in locals():
            (STORAGE / disk_name).unlink(missing_ok=True)
        engine.dispose()
