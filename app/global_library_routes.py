"""Single enterprise Dossier Jaune — compatibility-safe API.

The interface has exactly four permanent categories.  Historical documents
retain their old launch/folder/version IDs, and the old per-launch restriction
remains effective.  No implicit access widening during migration.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .core import get_current_user, get_db
from .models import Document, DocumentVersion, Folder, Launch, User
from .global_library_models import GlobalFolder, GlobalDocumentEntry, GlobalLibraryConfig
from .access import accessible

router = APIRouter(prefix="/api/dossier-jaune", tags=["Dossier Jaune unique"])
SLUGS = ("jaune", "rose", "bleu", "vert")
LABELS = {"jaune": "Technique", "rose": "Réception",
          "bleu": "Douane", "vert": "Facturation"}


def ready(db: Session):
    # A missing migration must not be mistaken for an empty document archive.
    try:
        found = set(db.scalars(select(GlobalFolder.slug)).all())
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, "Migration documentaire requise") from exc
    if found != set(SLUGS):
        raise HTTPException(503, "Structure documentaire non initialisée")


def authorized(db: Session, user: User, doc: Document, action: str):
    from .main import must  # Late import avoids a module initialization cycle.
    entry = db.get(GlobalDocumentEntry, doc.id)
    if entry is None:
        raise HTTPException(404, "Document non indexé")
    # Legacy ACL is an extra restriction, never a grant.
    if not accessible(db, user, doc.folder.launch):
        raise HTTPException(404, "Document introuvable")
    must(user, action, entry.folder_slug)
    return entry


def to_public(doc: Document, entry: GlobalDocumentEntry, uploaders=None):
    versions = sorted(doc.versions, key=lambda v: v.number)
    latest = versions[-1] if versions else None
    return {
        "id": doc.id,
        "title": doc.title,
        "doc_type": doc.doc_type,
        "folder": entry.folder_slug,
        "orli_ref": entry.orli_ref,
        "orli_overridden": bool(entry.orli_overridden),
        "created_at": doc.created_at.isoformat(),
        "latest": {
            "number": latest.number,
            "original_name": latest.original_name,
            "size": latest.size,
            "created_at": latest.created_at.isoformat(),
            "uploaded_by": (uploaders or {}).get(latest.uploaded_by),
        } if latest else None,
        "versions": [
            {"number": v.number, "original_name": v.original_name,
             "size": v.size, "created_at": v.created_at.isoformat()}
            for v in versions
        ],
    }


@router.get("")
def library(q: str = "", folder: str = "",
            user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    from .main import permitted
    ready(db)
    if folder and folder not in SLUGS:
        raise HTTPException(422, "Rubrique inconnue")
    term = q.strip().casefold()
    documents = db.scalars(
        select(Document).join(GlobalDocumentEntry)
        .order_by(Document.created_at.desc())
    ).all()
    # Only resolve authors of rows already authorized for this user.
    documents = [doc for doc in documents
                 if permitted(user, "document.read", db.get(GlobalDocumentEntry, doc.id).folder_slug)
                 and accessible(db, user, doc.folder.launch)]
    uploader_ids = {max(doc.versions, key=lambda v: v.number).uploaded_by
                    for doc in documents if doc.versions}
    uploaders = dict(db.execute(select(User.id, User.name).where(User.id.in_(uploader_ids))).all()) if uploader_ids else {}
    groups = []
    for slug in SLUGS:
        can_read = permitted(user, "document.read", slug)
        can_write = permitted(user, "document.write", slug)
        rows = []
        if can_read and (not folder or folder == slug):
            for doc in documents:
                entry = db.get(GlobalDocumentEntry, doc.id)
                if not entry or entry.folder_slug != slug:
                    continue
                if not accessible(db, user, doc.folder.launch):
                    continue
                if term and term not in " ".join((
                    doc.title, doc.doc_type, entry.orli_ref or "",
                    *[v.original_name for v in doc.versions],
                )).casefold():
                    continue
                rows.append(to_public(doc, entry, uploaders))
        groups.append({
            "slug": slug, "label": LABELS[slug],
            "can_read": can_read, "can_write": can_write,
            "count": len(rows), "documents": rows,
        })
    return {"name": "Dossier Jaune", "unique": True, "folders": groups}


def ensure_technical_container(db: Session, user: User):
    """Old upload/version services still expect a folder_id.

    This technical container is never a manufacturing dossier in the UI.
    Kept until legacy modules can be upgraded one by one.
    """
    config = db.get(GlobalLibraryConfig, "unique")
    if config:
        target = db.get(Launch, config.legacy_launch_id)
        if target is not None:
            return target
        raise HTTPException(503, "Conteneur de compatibilité manquant")
    launch = Launch(
        name="__BIBLIOTHEQUE_DOCUMENTAIRE_TECHNIQUE__",
        status="En cours", created_by=user.id, restricted=False
    )
    db.add(launch)
    db.flush()
    for slug, label in LABELS.items():
        db.add(Folder(launch_id=launch.id, slug=slug, label=label))
    db.flush()
    db.add(GlobalLibraryConfig(id="unique", legacy_launch_id=launch.id))
    db.flush()
    return launch


@router.post("/documents", status_code=201)
async def upload_global_document(
    folder: str = Form(...), title: str = Form(...),
    doc_type: str = Form("Autre"), orli_ref: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from .main import must, audit, store_upload, cloud_remove, STORAGE
    ready(db)
    if folder not in SLUGS:
        raise HTTPException(422, "Sous-dossier invalide")
    must(user, "document.write", folder)
    title = title.strip()
    doc_type = doc_type.strip() or "Autre"
    orli_ref = orli_ref.strip()
    if not (1 <= len(title) <= 220 and len(doc_type) <= 100 and len(orli_ref) <= 100):
        raise HTTPException(422, "Métadonnées invalides")
    # Storage write is performed only after all cheap checks succeeded.
    original, disk_name, size, sha, mime = await store_upload(file)
    try:
        container = ensure_technical_container(db, user)
        legacy_folder = next(x for x in container.folders if x.slug == folder)
        doc = Document(
            folder_id=legacy_folder.id, title=title,
            doc_type=doc_type, created_by=user.id
        )
        db.add(doc)
        db.flush()
        entry = GlobalDocumentEntry(
            document_id=doc.id, folder_slug=folder,
            orli_ref=orli_ref or None, orli_overridden=True,
            legacy_folder_id=legacy_folder.id,
            legacy_launch_id=container.id,
        )
        db.add(entry)
        version = DocumentVersion(
            document_id=doc.id, number=1, original_name=original,
            disk_name=disk_name, size=size, sha256=sha,
            content_type=mime, uploaded_by=user.id
        )
        db.add(version)
        db.flush()
        from .quality_routes import auto_inspect_excel
        auto_inspect_excel(db, version, user.id)
        audit(db, user, "document.upload", "document", doc.id,
              {"folder": folder, "orli": orli_ref, "sha256": sha})
        db.commit()
        return to_public(doc, entry)
    except Exception:
        db.rollback()
        cloud_remove(disk_name, STORAGE)
        raise


class OrliPatch(BaseModel):
    orli_ref: str | None = Field(default=None, max_length=100)


@router.patch("/documents/{doc_id}/reference")
def change_reference(doc_id: str, data: OrliPatch,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from .main import audit
    ready(db)
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    entry = authorized(db, user, doc, "document.write")
    before = entry.orli_ref
    after = (data.orli_ref or "").strip() or None
    entry.orli_ref = after
    entry.orli_overridden = True
    audit(db, user, "document.reference.update", "document", doc.id,
          {"previous": before, "new": after})
    db.commit()
    return to_public(doc, entry)
