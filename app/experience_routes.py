"""Retours d'expérience : saisie, résolution et questions sur les cas accessibles."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from .core import get_current_user, get_db
from .models import Document, DocumentVersion, User
from .experience_models import ExperienceRecord
from .experience_search import rank_records
from .global_library_routes import SLUGS, authorized, ready
from .access import accessible

router = APIRouter(prefix="/api/experience", tags=["Mémoire métier"])


class ExperienceInput(BaseModel):
    folder: Literal["jaune", "rose", "bleu", "vert"]
    title: str = Field(min_length=3, max_length=180)
    problem: str = Field(min_length=12, max_length=8000)
    context: str = Field(default="", max_length=4000)
    cause: str = Field(default="", max_length=4000)
    solution: str = Field(default="", max_length=6000)
    lesson: str = Field(default="", max_length=4000)
    orli_ref: str | None = Field(default=None, max_length=100)
    document_id: str | None = Field(default=None, max_length=36)
    tags: list[str] = Field(default_factory=list, max_length=10)
    status: Literal["ouvert", "en_cours", "resolu"] = "ouvert"

    @field_validator("title", "problem", "context", "cause", "solution", "lesson", "orli_ref", mode="before")
    @classmethod
    def clean(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags):
        if any(not tag.strip() or len(tag.strip()) > 40 for tag in tags):
            raise ValueError("Chaque mot-clé doit contenir entre 1 et 40 caractères")
        return list(dict.fromkeys(tag.strip() for tag in tags))

    @model_validator(mode="after")
    def require_solution(self):
        if self.status == "resolu" and len(self.solution) < 12:
            raise ValueError("Décrivez la solution avant de déclarer le problème résolu")
        return self


class ExperienceUpdate(ExperienceInput):
    revision: int = Field(ge=1)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    folder: Literal["jaune", "rose", "bleu", "vert"] | None = None
    orli_ref: str | None = Field(default=None, max_length=100)


def can_read(db, user, row):
    from .main import permitted
    if not (permitted(user, "document.read", row.folder_slug)
            and permitted(user, "rex.read", row.folder_slug)):
        return False
    if row.source_version_id:
        version = db.get(DocumentVersion, row.source_version_id)
        if not version or not accessible(db, user, version.document.folder.launch):
            return False
        from .global_library_models import GlobalDocumentEntry
        entry = db.get(GlobalDocumentEntry, version.document_id)
        if not entry or not permitted(user, "document.read", entry.folder_slug):
            return False
    return True


def visible_records(db, user, folder=None, orli_ref=None):
    from .main import permitted
    folders = [s for s in SLUGS if permitted(user, "document.read", s) and permitted(user, "rex.read", s)]
    statement = select(ExperienceRecord).where(ExperienceRecord.folder_slug.in_(folders))
    if folder:
        statement = statement.where(ExperienceRecord.folder_slug == folder)
    rows = db.scalars(statement.order_by(ExperienceRecord.updated_at.desc(), ExperienceRecord.id)).all()
    return [row for row in rows if can_read(db, user, row)
            and (not orli_ref or (row.orli_ref or "").casefold() == orli_ref.strip().casefold())]


def output(db, user, row):
    from .main import permitted
    source = db.get(DocumentVersion, row.source_version_id) if row.source_version_id else None
    return {"id": row.id, "folder": row.folder_slug, "orli_ref": row.orli_ref,
            "title": row.title, "problem": row.problem, "context": row.context,
            "cause": row.cause, "solution": row.solution, "lesson": row.lesson,
            "tags": json.loads(row.tags_json), "status": row.status,
            "source": {"document_id": source.document_id, "title": source.document.title,
                       "version": source.number} if source else None,
            "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat(),
            "revision": row.revision, "can_edit": permitted(user, "rex.write", row.folder_slug)}


def source_version(db, user, payload, existing=None):
    if not payload.document_id:
        return None
    doc = db.get(Document, payload.document_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    entry = authorized(db, user, doc, "document.read")
    if entry.folder_slug != payload.folder:
        raise HTTPException(422, "Le document source doit appartenir au sous-dossier choisi")
    if existing and existing.source_version_id:
        previous = db.get(DocumentVersion, existing.source_version_id)
        if previous and previous.document_id == doc.id:
            return previous.id  # Keep the exact version witnessed when the issue was recorded.
    version = max(doc.versions, key=lambda v: v.number, default=None)
    if not version:
        raise HTTPException(422, "Document sans version")
    return version.id


def apply_fields(row, payload):
    for field in ("title", "problem", "context", "cause", "solution", "lesson", "status"):
        setattr(row, field, getattr(payload, field))
    row.folder_slug = payload.folder
    row.orli_ref = payload.orli_ref or None
    row.tags_json = json.dumps(payload.tags, ensure_ascii=False)


@router.get("")
def listing(folder: Literal["jaune", "rose", "bleu", "vert"] | None = None,
            q: str = Query(default="", max_length=500), orli_ref: str | None = Query(default=None, max_length=100),
            offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ready(db)
    from .main import permitted
    rows = visible_records(db, user, folder, orli_ref)
    if q.strip():
        rows = rank_records(rows, q)
    return {"items": [output(db, user, row) for row in rows[offset:offset+limit]],
            "total": len(rows), "offset": offset, "limit": limit,
            "writable_folders": [s for s in SLUGS if permitted(user, "document.read", s)
                                 and permitted(user, "rex.read", s) and permitted(user, "rex.write", s)]}


@router.post("", status_code=201)
def create(payload: ExperienceInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import must, audit
    ready(db)
    for action in ("document.read", "rex.read", "rex.write"):
        must(user, action, payload.folder)
    source = source_version(db, user, payload)
    row = ExperienceRecord(created_by=user.id, updated_by=user.id, source_version_id=source)
    apply_fields(row, payload)
    db.add(row); db.flush()
    audit(db, user, "experience.create", "experience", row.id, {"folder": row.folder_slug, "revision": row.revision})
    db.commit(); db.refresh(row)
    return output(db, user, row)


def get_record(db, user, record_id):
    row = db.get(ExperienceRecord, record_id)
    if not row or not can_read(db, user, row):
        raise HTTPException(404, "Retour d’expérience introuvable")
    return row


@router.get("/{record_id}")
def read(record_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return output(db, user, get_record(db, user, record_id))


@router.put("/{record_id}")
def update(record_id: str, payload: ExperienceUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import must, audit
    row = get_record(db, user, record_id)
    must(user, "rex.write", row.folder_slug)
    for action in ("document.read", "rex.read", "rex.write"):
        must(user, action, payload.folder)
    if row.revision != payload.revision:
        raise HTTPException(409, "Cette fiche a changé. Rechargez-la avant de l’enregistrer.")
    row.source_version_id = source_version(db, user, payload, row)
    before = row.revision
    apply_fields(row, payload); row.updated_by = user.id
    try:
        db.flush()
        audit(db, user, "experience.update", "experience", row.id, {"previous_revision": before, "revision": row.revision})
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(409, "Cette fiche a changé. Rechargez-la.") from exc
    db.refresh(row)
    return output(db, user, row)


def answer_question(db, user, payload: Question):
    rows = rank_records(visible_records(db, user, payload.folder, payload.orli_ref), payload.question)[:3]
    sources = [output(db, user, row) for row in rows]
    if not rows:
        answer = "Aucun retour d’expérience accessible ne correspond à cette question. Précisez la référence ORLI, le document ou le problème rencontré."
    else:
        best = rows[0]
        answer = ("Cas enregistré : " + best.title + ".\n" +
                  ("Solution consignée : " + best.solution if best.status == "resolu" else
                   "Problème encore ouvert. " + ("Piste consignée : " + best.solution if best.solution else best.problem)))
        if best.lesson:
            answer += "\nÀ retenir : " + best.lesson
    return {"answer": answer, "sources": sources, "method": "Recherche locale par mots-clés et synonymes ; extraits des fiches enregistrées.",
            "source": "Mémoire métier · fiches enregistrées", "destination": "rex" if rows else None,
            "title": "Retours d’expérience", "requires_human_action": True}


@router.post("/ask")
def ask(payload: Question, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return answer_question(db, user, payload)
