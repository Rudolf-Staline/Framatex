"""Append-only internal comments tied to an exact document version.

Decisions/correction requests remain in the existing approval modules.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, Text, ForeignKey, DateTime, select, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base, utcnow, get_db, get_current_user
from .models import uid, DocumentVersion, User
from .access import must, permitted
from .order_documents import document_accessible
from .audit import audit
router=APIRouter(tags=['Commentaires documentaires internes'])

class DocumentComment(Base):
    __tablename__='document_comments'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    version_id: Mapped[str]=mapped_column(ForeignKey('document_versions.id'),index=True)
    author_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    text: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class CommentInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    text:str=Field(min_length=1,max_length=4000)

def version_scope(db,user,version_id,write=False):
    version=db.get(DocumentVersion,version_id)
    if not version or not document_accessible(db,user,version.document):raise HTTPException(404,'Version introuvable')
    must(user,'document.read',version.document.folder.slug)
    if write:must(user,'document.write',version.document.folder.slug)
    return version

def comment_out(row,author):
    return {'id':row.id,'version_id':row.version_id,'author_id':row.author_id,'author':author.name,
            'text':row.text,'created_at':row.created_at,'kind':'comment'}

@router.get('/api/document-versions/{version_id}/comments')
def comments(version_id:str,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),user=Depends(get_current_user),db:Session=Depends(get_db)):
    version=version_scope(db,user,version_id)
    where=DocumentComment.version_id==version_id
    total=db.scalar(select(func.count()).select_from(DocumentComment).where(where))
    rows=db.execute(select(DocumentComment,User).join(User,User.id==DocumentComment.author_id).where(where).order_by(DocumentComment.created_at,DocumentComment.id).offset(offset).limit(limit))
    return {'version_id':version_id,'version':version.number,'document_id':version.document_id,'offset':offset,'limit':limit,'total':total,
            'items':[comment_out(row,author) for row,author in rows],'can_write':permitted(user,'document.write',version.document.folder.slug)}

@router.post('/api/document-versions/{version_id}/comments',status_code=201)
def add_comment(version_id:str,payload:CommentInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    version_scope(db,user,version_id,True)
    row=DocumentComment(version_id=version_id,author_id=user.id,text=payload.text)
    db.add(row);db.flush();audit(db,user,'document.comment','document_version',version_id,{'comment_id':row.id})
    db.commit();return comment_out(row,user)
