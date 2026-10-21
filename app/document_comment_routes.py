"""Versioned internal commentary. Clients cannot access these employee APIs."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import DocumentVersion, User
from .document_comment_models import DocumentComment
from .main import get_doc, must, permitted, audit, STORAGE
from .access import must_access

router = APIRouter()


class CommentInput(BaseModel):
    version_id: str = Field(min_length=1, max_length=36)
    body: str = Field(min_length=2, max_length=4000)
    page_number: int | None = Field(default=None, ge=1, le=10000, strict=True)

    @field_validator('body', mode='before')
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


def authorize(db, user, doc_id, write=False):
    must(user, 'launch.read')
    doc = get_doc(db, doc_id)
    must_access(db, user, doc.folder.launch_id)
    must(user, 'document.read', doc.folder.slug)
    if write:
        must(user, 'document.write', doc.folder.slug)
    return doc


@router.get('/api/documents/{doc_id}/comments')
def list_comments(doc_id: str, offset: int = Query(default=0, ge=0),
                  limit: int = Query(default=50, ge=1, le=100),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = authorize(db, user, doc_id)
    # Joining on version ownership prevents cross-document links and exposes only this thread.
    query = select(DocumentComment, DocumentVersion, User).join(
        DocumentVersion, DocumentComment.document_version_id == DocumentVersion.id).join(
        User, DocumentComment.created_by == User.id).where(DocumentVersion.document_id == doc.id)
    rows = db.execute(query.order_by(DocumentComment.created_at.desc(), DocumentComment.id.desc())
                      .offset(offset).limit(limit + 1)).all()
    return {'document_id': doc.id, 'can_comment': permitted(user, 'document.write', doc.folder.slug),
            'offset': offset, 'has_more': len(rows) > limit,
            'items': [{'id': c.id, 'version_id': v.id, 'version': v.number,
                       'body': c.body, 'page_number': c.page_number,
                       'author': {'id': u.id, 'name': u.name}, 'created_at': c.created_at.isoformat()}
                      for c, v, u in rows[:limit]]}


@router.post('/api/documents/{doc_id}/comments', status_code=201)
def create_comment(doc_id: str, payload: CommentInput,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = authorize(db, user, doc_id, write=True)
    version = db.get(DocumentVersion, payload.version_id)
    if not version or version.document_id != doc.id:
        raise HTTPException(422, 'La version doit appartenir à ce document')
    if payload.page_number is not None:
        if Path(version.original_name).suffix.lower() != '.pdf':
            raise HTTPException(422, 'Un repère de page est réservé aux fichiers PDF')
        from .cloud_storage import ensure_local
        from pypdf import PdfReader
        try:
            with ensure_local(version.disk_name, STORAGE).open('rb') as stream:
                page_count = len(PdfReader(stream).pages)
        except Exception:
            raise HTTPException(422, 'Le nombre de pages de ce PDF ne peut pas être vérifié')
        if payload.page_number > page_count:
            raise HTTPException(422, f'Ce PDF contient {page_count} page(s)')
    row = DocumentComment(document_version_id=version.id, body=payload.body,
                          page_number=payload.page_number, created_by=user.id)
    db.add(row); db.flush()
    audit(db, user, 'document.comment.create', 'document_version', version.id,
          {'comment_id': row.id, 'page_number': row.page_number})
    db.commit()
    return {'id': row.id, 'version_id': version.id, 'version': version.number,
            'body': row.body, 'page_number': row.page_number,
            'author': {'id': user.id, 'name': user.name}, 'created_at': row.created_at.isoformat()}
