"""Document upload, version and download HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from . import document_storage
from .access import must
from .audit import audit
from .launches import get_launch, SLUGS
from .order_documents import get_doc, doc_out
from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import update,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import Document, DocumentVersion, User, Launch
from .workflow import emit_document_impacts

router = APIRouter()

@router.post("/api/launches/{launch_id}/documents", status_code=201)
async def upload_document(launch_id: str, folder: str = Form(...), title: str = Form(...), doc_type: str = Form("Autre"), file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    if folder not in SLUGS:
        raise HTTPException(422, "Sous-dossier invalide")
    must(user, "document.write", folder)
    launch = get_launch(db, launch_id)
    entity = next((f for f in launch.folders if f.slug == folder), None)
    if entity is None or not title.strip() or len(title) > 220 or len(doc_type) > 100:
        raise HTTPException(422, "Métadonnées invalides")
    actor_id = user.id
    db.rollback()
    original, disk_name, size, sha, mime = await document_storage.store_upload(file)
    try:
        # Recheck after the potentially long scan, while holding a short writer
        # transaction so concurrent revocation cannot slip between check/insert.
        db.execute(update(Launch).where(Launch.id == launch_id).values(id=Launch.id))
        db.expire_all()
        user = db.get(User, actor_id)
        if not user or not user.active:
            raise HTTPException(401, "Connexion nécessaire")
        from .access import must_access
        must(user, "launch.read"); must(user, "document.write", folder)
        launch = must_access(db, user, launch_id)
        entity = next((f for f in launch.folders if f.slug == folder), None)
        if entity is None:
            raise HTTPException(409, "Rubrique modifiée pendant le dépôt : actualisez")
        doc = Document(launch_id=launch_id, folder_id=entity.id, title=title.strip(), doc_type=doc_type.strip() or "Autre", created_by=user.id)
        db.add(doc)
        db.flush()
        from .document_types import register_type
        register_type(db, doc)
        version = DocumentVersion(document_id=doc.id, number=1, original_name=original, disk_name=disk_name, size=size, sha256=sha, content_type=mime, uploaded_by=user.id)
        db.add(version)
        db.flush()
        from .quality_routes import auto_inspect_excel
        auto_inspect_excel(db, version, user.id)
        audit(db, user, "document.upload", "document", doc.id, {"launch": launch_id, "folder": folder, "sha256": sha})
        result = doc_out(doc)
        db.commit()
        return result
    except Exception:
        db.rollback()
        document_storage.remove_blob(disk_name)
        raise


@router.post("/api/documents/{doc_id}/versions", status_code=201)
async def new_version(doc_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = get_doc(db, doc_id)
    must(user, "document.write", d.folder.slug)
    actor_id = user.id
    db.rollback()
    original, disk_name, size, sha, mime = await document_storage.store_upload(file)
    try:
        db.execute(update(Document).where(Document.id == doc_id).values(title=Document.title))
        db.expire_all()
        user = db.get(User, actor_id)
        if not user or not user.active:
            raise HTTPException(401, "Connexion nécessaire")
        d = get_doc(db, doc_id)
        from .order_documents import document_accessible
        if not document_accessible(db, user, d):
            raise HTTPException(404, "Document introuvable")
        must(user, "launch.read"); must(user, "document.write", d.folder.slug)
        db.refresh(d); db.expire(d, ["versions"])
        next_number = max((v.number for v in d.versions), default=0) + 1
        version = DocumentVersion(document_id=d.id, number=next_number, original_name=original, disk_name=disk_name, size=size, sha256=sha, content_type=mime, uploaded_by=user.id)
        d.versions.append(version)
        db.flush()
        emit_document_impacts(db, d, version)
        from .quality_routes import auto_inspect_excel
        auto_inspect_excel(db, version, user.id)
        audit(db, user, "document.version.add", "document", d.id, {"version": next_number, "sha256": sha})
        result = doc_out(d)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        document_storage.remove_blob(disk_name)
        raise HTTPException(409, "Conflit de version, recommencez le dépôt")
    except Exception:
        db.rollback()
        document_storage.remove_blob(disk_name)
        raise


@router.get("/api/documents/{doc_id}/versions/{number}/download")
def download(doc_id: str, number: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_doc(db, doc_id)
    must(user, "document.read", doc.folder.slug)
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id==doc.id,DocumentVersion.number==number))
    if not version:
        raise HTTPException(404, "Version introuvable")
    path = document_storage.STORAGE / version.disk_name
    if not path.is_file():
        raise HTTPException(503, "Fichier indisponible dans le stockage")
    audit(db, user, "document.download", "document", doc.id, {"version": number})
    db.commit()
    return FileResponse(path, filename=version.original_name, content_disposition_type="attachment", media_type="application/octet-stream", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
