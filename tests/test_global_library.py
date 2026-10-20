"""Dossier Jaune V2: migration de copie, isolation des anciens droits, ORLI."""
from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException
import pytest

from app.core import Base
from app.models import Document, DocumentVersion, Folder, Launch, Role, RolePermission, User
from app.global_library_models import GlobalDocumentEntry, GlobalFolder, GlobalLibraryConfig
from app.global_library_routes import (
    OrliPatch, authorized, change_reference, ensure_technical_container, library
)
from tools.migrate_global_library import apply_upgrade


def prepare_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(name="Opérateur", grants=[
            RolePermission(action="document.read", folder_slug="jaune"),
            RolePermission(action="document.write", folder_slug="jaune"),
            RolePermission(action="document.read", folder_slug="rose"),
        ])
        admin_role = Role(name="Administrateur")
        admin = User(email="admin@example.test", name="Admin", password_hash="unused",
                     roles=[admin_role])
        viewer = User(email="view@example.test", name="Viewer", password_hash="unused",
                      roles=[role])
        db.add_all([admin, viewer])
        db.flush()
        launch_public = Launch(name="Fabrication A", created_by=admin.id,
                               restricted=False, orli_ref="ORLI-11")
        launch_private = Launch(name="Fabrication B", created_by=admin.id,
                                restricted=True, orli_ref="ORLI-77")
        db.add_all([launch_public, launch_private])
        db.flush()
        folder_pub = Folder(launch_id=launch_public.id, slug="jaune", label="Technique")
        folder_priv = Folder(launch_id=launch_private.id, slug="rose", label="Réception")
        db.add_all([folder_pub, folder_priv])
        db.flush()
        visible_doc = Document(folder_id=folder_pub.id, title="Fiche", doc_type="Fiche technique",
                               created_by=admin.id)
        private_doc = Document(folder_id=folder_priv.id, title="Facture restreinte",
                               doc_type="Facture", created_by=admin.id)
        db.add_all([visible_doc, private_doc])
        db.flush()
        version = DocumentVersion(document_id=visible_doc.id, number=1,
                                  original_name="fiche.txt", disk_name="binary-id-a",
                                  content_type="text/plain", size=12,
                                  sha256="a"*64, uploaded_by=admin.id)
        db.add(version)
        db.flush()
        ids = dict(admin=admin.id, viewer=viewer.id,
                   visible=visible_doc.id, private=private_doc.id, version=version.id)
        db.commit()
    return engine, ids


def test_migration_on_isolated_copy_is_idempotent_and_immutable():
    engine, ids = prepare_engine()
    before = set()
    with Session(engine) as db:
        before = {(v.id, v.document_id, v.number, v.sha256, v.disk_name)
                  for v in db.scalars(select(DocumentVersion))}
    first = apply_upgrade(engine)
    assert first["source_documents"] == 2
    assert first["indexed_documents"] == 2
    assert first["added"] == 2
    with Session(engine) as db:
        assert len(db.scalars(select(GlobalFolder)).all()) == 4
        entry = db.get(GlobalDocumentEntry, ids["visible"])
        assert entry.folder_slug == "jaune"
        assert entry.orli_ref == "ORLI-11"
        entry.orli_ref = "ORLI-EDIT"
        entry.orli_overridden = True
        db.commit()
    second = apply_upgrade(engine)
    assert second["added"] == 0
    with Session(engine) as db:
        assert db.get(GlobalDocumentEntry, ids["visible"]).orli_ref == "ORLI-EDIT"
        assert {(v.id, v.document_id, v.number, v.sha256, v.disk_name)
                for v in db.scalars(select(DocumentVersion))} == before
        assert db.get(Document, ids["visible"]).folder_id == db.get(
            Folder, db.get(GlobalDocumentEntry, ids["visible"]).legacy_folder_id
        ).id
    engine.dispose()


def test_existing_restricted_documents_are_not_exposed_by_new_library():
    engine, ids = prepare_engine()
    apply_upgrade(engine)
    with Session(engine) as db:
        viewer = db.get(User, ids["viewer"])
        normal = library(q="", folder="", user=viewer, db=db)
        all_docs = [d["id"] for f in normal["folders"] for d in f["documents"]]
        assert ids["visible"] in all_docs
        assert ids["private"] not in all_docs
        assert normal["unique"] is True
        with pytest.raises(HTTPException) as exc:
            authorized(db, viewer, db.get(Document, ids["private"]), "document.read")
        assert exc.value.status_code == 404
        # No launch permission is required for the global library if the folder
        # permission and historical confidentiality rules allow document access.
        assert next(f for f in normal["folders"] if f["slug"] == "jaune")["can_write"]
    engine.dispose()


def test_document_reference_edit_does_not_change_binary_or_color():
    engine, ids = prepare_engine()
    apply_upgrade(engine)
    with Session(engine) as db:
        admin = db.get(User, ids["admin"])
        entry = db.get(GlobalDocumentEntry, ids["visible"])
        original_folder = entry.folder_slug
        before = db.get(DocumentVersion, ids["version"]).sha256
        response = change_reference(ids["visible"], OrliPatch(orli_ref=None),
                                    user=admin, db=db)
        assert response["orli_ref"] is None
        assert db.get(GlobalDocumentEntry, ids["visible"]).folder_slug == original_folder
        assert db.get(DocumentVersion, ids["version"]).sha256 == before
        assert db.get(GlobalDocumentEntry, ids["visible"]).orli_overridden
        a = ensure_technical_container(db, admin)
        b = ensure_technical_container(db, admin)
        assert a.id == b.id
        assert len(a.folders) == 4
        assert db.get(GlobalLibraryConfig, "unique").legacy_launch_id == a.id
        db.rollback()
    engine.dispose()
