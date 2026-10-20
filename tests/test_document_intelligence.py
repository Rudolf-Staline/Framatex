"""Parcours dossier unique : mémoire, questions sourcées et contrôles par ORLI."""
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core import Base, get_current_user, get_db
from app.main import app
from app.models import User, Role, RolePermission, Launch, Folder, Document, DocumentVersion, AuditEvent
from app.global_library_models import GlobalFolder, GlobalDocumentEntry
from app.experience_models import ExperienceRecord
from tools.migrate_document_intelligence import apply_to_connection

H = {"X-Framatex-Request": "1"}


@pytest.fixture
def workspace():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(name="Responsable", email="intelligence-admin@example.invalid", password_hash="unused",
                     roles=[Role(name="Administrateur")])
        reader = User(name="Réception", email="intelligence-reader@example.invalid", password_hash="unused",
                      roles=[Role(name="Réception", grants=[
                          RolePermission(action=a, folder_slug="rose") for a in
                          ("document.read", "document.write", "rex.read", "rex.write", "completeness.review")
                      ])])
        db.add_all([admin, reader])
        db.add_all(GlobalFolder(slug=s, label=s) for s in ("jaune", "rose", "bleu", "vert"))
        db.commit()
        identities = {"admin": admin.id, "reader": reader.id}
    active = {"id": identities["admin"]}

    def override_db():
        with Session(engine) as db:
            yield db

    def override_auth(db: Session = Depends(get_db)):
        return db.get(User, active["id"])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_auth
    try:
        yield TestClient(app), engine, active, identities
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def document(engine, admin_id, *, folder="rose", ref="ORLI-100", doc_type="Bon de livraison",
             title="Livraison coton", restricted=False):
    with Session(engine) as db:
        launch = Launch(name="Compatibilité documentaire", created_by=admin_id, restricted=restricted)
        db.add(launch); db.flush()
        part = Folder(launch_id=launch.id, slug=folder, label=folder)
        db.add(part); db.flush()
        doc = Document(folder_id=part.id, title=title, doc_type=doc_type, created_by=admin_id)
        db.add(doc); db.flush()
        version = DocumentVersion(document_id=doc.id, number=1, original_name="test.txt",
                                  disk_name=doc.id, size=1, sha256="0"*64,
                                  content_type="text/plain", uploaded_by=admin_id)
        entry = GlobalDocumentEntry(document_id=doc.id, folder_slug=folder, orli_ref=ref,
                                    orli_overridden=True, legacy_folder_id=part.id, legacy_launch_id=launch.id)
        db.add_all([version, entry]); db.commit()
        return doc.id, version.id, launch.id


def payload(**changes):
    return dict(folder="rose", title="Écart de quantité à la réception",
                problem="La quantité livrée diffère de la quantité du bon de livraison.",
                context="Contrôle avant rangement", cause="Une ligne du bon avait été omise.",
                solution="Recompter les colis et rapprocher chaque ligne du bon corrigé.",
                lesson="Contrôler les quantités ligne par ligne.", tags=["quantité", "réception"],
                orli_ref="ORLI-100", status="resolu", **changes)


def create_record(client, **changes):
    data = payload(); data.update(changes)
    result = client.post("/api/experience", json=data, headers=H)
    assert result.status_code == 201, result.text
    return result.json()


def test_record_question_resolution_and_concurrent_edit(workspace):
    c, engine, active, ids = workspace
    row = create_record(c)
    assert row["revision"] == 1
    asked = c.post("/api/experience/ask", json={"question": "Comment résoudre une divergence de quantités reçues ?"}, headers=H)
    assert asked.status_code == 200, asked.text
    assert asked.json()["sources"][0]["id"] == row["id"]
    assert row["solution"] in asked.json()["answer"]
    absent = c.post("/api/experience/ask", json={"question": "Quel réglage du moteur de la machine à coudre ?"}, headers=H).json()
    assert absent["sources"] == [] and "Aucun" in absent["answer"]
    invalid = payload(); invalid.update(status="resolu", solution=" ")
    assert c.post("/api/experience", json=invalid, headers=H).status_code == 422
    invalid = payload(); invalid.update(title="   ")
    assert c.post("/api/experience", json=invalid, headers=H).status_code == 422
    changed = payload(); changed.update(revision=1, lesson="Photographier le comptage avant de valider la réception.")
    updated = c.put("/api/experience/"+row["id"], json=changed, headers=H)
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert c.put("/api/experience/"+row["id"], json=changed, headers=H).status_code == 409
    assert c.post("/api/experience/ask", json={"question": "quantité"}).status_code == 403
    with Session(engine) as db:
        actions = db.scalars(select(AuditEvent.action).where(AuditEvent.target_id == row["id"])).all()
        assert set(actions) == {"experience.create", "experience.update"}


def test_folder_and_source_acl_applies_to_lists_questions_and_direct_reads(workspace):
    c, engine, active, ids = workspace
    public_doc, original_version, _ = document(engine, ids["admin"])
    private_doc, _, launch_id = document(engine, ids["admin"], restricted=True, title="Pièce confidentielle")
    linked = create_record(c, document_id=private_doc, title="Incident confidentiel quantités")
    visible = create_record(c, document_id=public_doc)
    secret = create_record(c, folder="jaune", title="Secret technique sur les quantités")
    wrong = payload(); wrong.update(document_id=public_doc, folder="jaune")
    assert c.post("/api/experience", json=wrong, headers=H).status_code == 422
    with Session(engine) as db:
        db.add(DocumentVersion(document_id=public_doc, number=2, original_name="v2.txt",
                               disk_name="v2-"+public_doc, size=2, sha256="1"*64,
                               content_type="text/plain", uploaded_by=ids["admin"]))
        db.commit()
    assert c.get("/api/experience/"+visible["id"]).json()["source"]["version"] == 1
    active["id"] = ids["reader"]
    listing = c.get("/api/experience").json()
    assert [r["id"] for r in listing["items"]] == [visible["id"]]
    assert listing["total"] == 1
    for record in (linked, secret):
        assert c.get("/api/experience/"+record["id"]).status_code == 404
    asked = c.post("/api/assistant/chat", json={"question": "Une solution pour les quantités ?", "mode": "memory"}, headers=H).json()
    assert [r["id"] for r in asked["sources"]] == [visible["id"]]
    assert "confidentiel" not in str(asked)
    denied = payload(); denied.update(document_id=private_doc)
    assert c.post("/api/experience", json=denied, headers=H).status_code == 404
    denied["document_id"] = None; denied["folder"] = "vert"
    assert c.post("/api/experience", json=denied, headers=H).status_code == 403
    # Global document permissions suffice; legacy launch.read is not required.
    assert c.post("/api/experience", json=payload(), headers=H).status_code == 201


def test_expectations_follow_orli_and_refresh_after_deposit(workspace):
    c, engine, active, ids = workspace
    assert c.get("/api/dossier-jaune/controls").json()["counts"]["missing"] == 0
    requirement = {"folder": "rose", "title": "Bon fournisseur attendu",
                   "document_type": "Bon de livraison", "orli_ref": "ORLI-101"}
    saved = c.post("/api/dossier-jaune/expectations", json=requirement, headers=H)
    assert saved.status_code == 201, saved.text
    document(engine, ids["admin"], ref="ORLI-100")
    assert c.get("/api/dossier-jaune/controls").json()["expectations"][0]["status"] == "missing"
    document(engine, ids["admin"], ref="orli-101")
    report = c.get("/api/dossier-jaune/controls").json()
    assert report["expectations"][0]["status"] == "present" and report["counts"]["missing"] == 0
    assert c.delete("/api/dossier-jaune/expectations/"+saved.json()["id"], headers=H).status_code == 200
    assert c.get("/api/dossier-jaune/controls").json()["expectations"] == []
    with engine.begin() as conn:
        apply_to_connection(conn); apply_to_connection(conn)
    # Idempotent migration never destroys an existing record or document.
    assert len(c.get("/api/dossier-jaune/controls").json()["documents"]) == 2


def test_global_coherence_decimal_units_current_versions_and_ambiguity(workspace):
    c, engine, active, ids = workspace
    left, _, _ = document(engine, ids["admin"], folder="jaune", doc_type="Fiche de lancement", title="Lancement")
    right, _, _ = document(engine, ids["admin"], folder="rose", title="Livraison")
    for doc_id, value in ((left, "1500,5"), (right, "1450")):
        result = c.post("/api/dossier-jaune/documents/"+doc_id+"/data",
                        json={"field_key": "quantite_lancement", "value": value, "unit": "pièce"}, headers=H)
        assert result.status_code == 201, result.text
    rule = c.post("/api/admin/quality-rules", json={"name": "Rapprochement des quantités",
                 "field_key": "quantite_lancement", "left_doc_type": "Fiche de lancement",
                 "right_doc_type": "Bon de livraison", "left_folder": "jaune", "right_folder": "rose",
                 "tolerance": "0,5"}, headers=H)
    assert rule.status_code == 201, rule.text
    comparison = c.get("/api/dossier-jaune/controls").json()["comparisons"][0]
    assert comparison["status"] == "difference" and comparison["difference"] == "50.5"
    assert {p["value"] for p in comparison["pair"]} == {"1500.5", "1450"}
    # A nonmatching ORLI must never become the counterpart in a comparison.
    document(engine, ids["admin"], folder="rose", ref="ORLI-OTHER", title="Autre livraison")
    rows = c.get("/api/dossier-jaune/controls").json()["comparisons"]
    assert next(x for x in rows if x["orli_ref"] == "ORLI-OTHER")["status"] == "unavailable"
    with Session(engine) as db:
        version = DocumentVersion(document_id=right, number=2, original_name="revision.txt",
                                  disk_name="revised-"+right, size=2, sha256="2"*64,
                                  content_type="text/plain", uploaded_by=ids["admin"])
        db.add(version); db.commit()
    rows = c.get("/api/dossier-jaune/controls").json()["comparisons"]
    assert next(x for x in rows if x["orli_ref"] == "ORLI-100")["status"] == "unavailable"
    c.post("/api/dossier-jaune/documents/"+right+"/data",
           json={"field_key": "quantite_lancement", "value": "1500.5", "unit": "colis"}, headers=H)
    rows = c.get("/api/dossier-jaune/controls").json()["comparisons"]
    assert next(x for x in rows if x["orli_ref"] == "ORLI-100")["status"] == "unit_mismatch"
    document(engine, ids["admin"], folder="rose", ref="ORLI-100", title="Deuxième candidat")
    rows = c.get("/api/dossier-jaune/controls").json()["comparisons"]
    assert next(x for x in rows if x["orli_ref"] == "ORLI-100")["status"] == "ambiguous"
    active["id"] = ids["reader"]
    report = c.get("/api/dossier-jaune/controls").json()
    assert report["comparisons"] == [] and report["counts"]["differences"] == 0
    assert all(d["folder"] == "rose" for d in report["documents"])
    assert c.post("/api/dossier-jaune/documents/"+left+"/data",
                  json={"field_key": "prix_unitaire", "value": "1", "unit": "MAD"}, headers=H).status_code == 403


def test_chat_navigation_and_empty_memory(workspace):
    c, _, active, ids = workspace
    for phrase, destination in (("Où déposer une facture ?", "dossier"),
                               ("Comment trouver les pièces manquantes ?", "controls"),
                               ("Comment interroger la mémoire métier ?", "rex")):
        response = c.post("/api/assistant/chat", json={"question": phrase}, headers=H)
        assert response.status_code == 200, response.text
        assert response.json()["destination"] == destination
    empty = c.post("/api/assistant/chat", json={"question": "Comment résoudre un écart de tissu ?", "mode": "memory"}, headers=H).json()
    assert empty["sources"] == [] and empty["destination"] is None
    active["id"] = ids["reader"]
    denied = c.post("/api/assistant/chat", json={"question": "Où déposer une facture ?"}, headers=H).json()
    assert denied["destination"] is None
