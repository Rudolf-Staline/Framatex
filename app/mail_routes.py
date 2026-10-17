"""0.8 — Archivage manuel .eml, suggestions et registre des engagements.

Pas de connexion aux messageries ni d'envoi automatique. Droits de lecture
fondés sur le sous-dossier Rose, décisions humaines et journal d'audit.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core import get_current_user, get_db, utcnow
from .models import Document, DocumentVersion, Folder, User
from .mail_models import ArchivedEmail, EmailCommitment
from .mail_analysis import parse_email, suggest_commitments

router=APIRouter(tags=['0.8 — Emails et engagements'])


def _deps():
    from .main import audit, get_launch, must, STORAGE, store_upload, doc_out
    return audit,get_launch,must,STORAGE,store_upload,doc_out


def _read_email(db:Session, email_id:str, launch_id:str, user:User):
    _,_,must,_,_,_= _deps()
    must(user,'launch.read');must(user,'document.read','rose')
    x=db.get(ArchivedEmail,email_id)
    if not x or x.launch_id!=launch_id:raise HTTPException(404,'Email introuvable dans ce lancement')
    return x


def _commitment(db:Session, item_id:str, launch_id:str):
    x=db.get(EmailCommitment,item_id)
    if not x or x.launch_id!=launch_id:raise HTTPException(404,'Engagement introuvable')
    return x


def _email_out(x:ArchivedEmail):
    return {'id':x.id,'document_version_id':x.document_version_id,'subject':x.subject,'sender':x.sender,
            'recipients':x.recipients,'carbon_copy':x.carbon_copy,'message_id':x.message_id,
            'sent_at_raw':x.sent_at_raw,'body_excerpt':x.body_excerpt,'attachments':json.loads(x.attachments_json),
            'archived_at':x.archived_at.isoformat()}


def _commit_out(x:EmailCommitment):
    return {'id':x.id,'email_id':x.email_id,'description':x.description,'responsible':x.responsible,
            'due_date':x.due_date,'condition':x.condition,'source_excerpt':x.source_excerpt,
            'status':x.status,'decision_note':x.decision_note,'confirmed_at':x.confirmed_at.isoformat(),
            'updated_at':x.updated_at.isoformat() if x.updated_at else None}


class CommitmentIn(BaseModel):
    email_id:str
    description:str=Field(min_length=12,max_length=650)
    responsible:str=Field(min_length=2,max_length=250)
    due_date:date|None=None
    condition:str=Field(default='',max_length=500)
    source_excerpt:str=Field(default='',max_length=650)

class CommitmentPatch(BaseModel):
    status:str
    note:str=Field(min_length=12,max_length=1600)
    due_date:date|None=None
    @field_validator('status')
    @classmethod
    def validate_status(cls,v):
        if v not in ('pending','done','postponed','cancelled'):
            raise ValueError('Statut non autorisé')
        return v

@router.post('/api/launches/{launch_id}/emails/import',status_code=201)
async def import_email(launch_id:str,file:UploadFile=File(...),
                       user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    audit,get_launch,must,storage,store_upload,doc_out=_deps()
    must(user,'launch.read');must(user,'document.write','rose');must(user,'document.read','rose')
    launch=get_launch(db,launch_id)
    suffix=Path((file.filename or '').replace('\\','/')).suffix.lower()
    if suffix!='.eml':raise HTTPException(422,'Import réservé aux fichiers .eml')
    raw=await file.read(20*1024*1024+1)
    if len(raw)>20*1024*1024:raise HTTPException(413,'Email supérieur à 20 Mo')
    try:parsed=parse_email(raw)
    except ValueError as exc:raise HTTPException(422,str(exc))
    # Réinitialisation pour réutiliser le mécanisme éprouvé de stockage et de hash.
    await file.seek(0)
    rose=next((folder for folder in launch.folders if folder.slug=='rose'),None)
    if rose is None:raise HTTPException(409,'Sous-dossier Rose absent')
    original,disk_name,size,sha,mime=await store_upload(file)
    try:
        doc=Document(folder_id=rose.id,title=('Email · '+parsed['subject'])[:220],doc_type='Courriel',created_by=user.id)
        db.add(doc);db.flush()
        version=DocumentVersion(document_id=doc.id,number=1,original_name=original,disk_name=disk_name,
                                size=size,sha256=sha,content_type=mime,uploaded_by=user.id)
        db.add(version);db.flush()
        x=ArchivedEmail(launch_id=launch.id,document_version_id=version.id,archived_by=user.id,
                        attachments_json=json.dumps(parsed['attachments'],ensure_ascii=False),
                        **{k:parsed[k] for k in ('message_id','subject','sender','recipients','carbon_copy','sent_at_raw','body_excerpt')})
        db.add(x);db.flush()
        audit(db,user,'email.archive','archived_email',x.id,{'launch':launch.id,'version':version.id,'attachments':len(parsed['attachments'])})
        db.commit()
        return {'email':_email_out(x),'document':doc_out(doc)}
    except Exception:
        db.rollback();(storage/disk_name).unlink(missing_ok=True)
        raise

@router.get('/api/launches/{launch_id}/emails')
def list_emails(launch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    _,get_launch,must,_,_,_=_deps()
    must(user,'launch.read');get_launch(db,launch_id)
    # Pas même de métadonnées révélées sans droit de lecture du dossier Rose.
    must(user,'document.read','rose')
    emails=db.scalars(select(ArchivedEmail).where(ArchivedEmail.launch_id==launch_id).order_by(ArchivedEmail.archived_at.desc())).all()
    commitments=db.scalars(select(EmailCommitment).where(EmailCommitment.launch_id==launch_id).order_by(EmailCommitment.confirmed_at.desc())).all()
    return {'emails':[_email_out(x) for x in emails], 'commitments':[_commit_out(x) for x in commitments],
            'can_import':_may_import(user),'can_review':_may_review(user)}


def _may_import(user):
    from .main import permitted
    return permitted(user,'document.write','rose')


def _may_review(user):
    from .main import permitted
    return permitted(user,'commitment.review','rose')

@router.get('/api/launches/{launch_id}/emails/{email_id}/suggestions')
def email_suggestions(launch_id:str,email_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    x=_read_email(db,email_id,launch_id,user)
    return suggest_commitments({'body_excerpt':x.body_excerpt,'sender':x.sender})

@router.post('/api/launches/{launch_id}/commitments',status_code=201)
def create_commitment(launch_id:str,payload:CommitmentIn,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    audit,_,must,_,_,_=_deps()
    x=_read_email(db,payload.email_id,launch_id,user)
    must(user,'commitment.review','rose')
    # L'utilisateur doit confirmer une citation présente dans le courrier.
    excerpt=payload.source_excerpt.strip()
    if excerpt and excerpt not in x.body_excerpt:
        raise HTTPException(422,'Extrait source absent de ce courrier : vérifiez la transcription')
    item=EmailCommitment(launch_id=launch_id,email_id=x.id,description=payload.description.strip(),
                         responsible=payload.responsible.strip(),due_date=payload.due_date.isoformat() if payload.due_date else None,
                         condition=payload.condition.strip(),source_excerpt=excerpt,confirmed_by=user.id)
    db.add(item);db.flush()
    audit(db,user,'commitment.confirm','email_commitment',item.id,{'email':x.id,'launch':launch_id})
    db.commit()
    return _commit_out(item)

@router.patch('/api/launches/{launch_id}/commitments/{item_id}')
def update_commitment(launch_id:str,item_id:str,payload:CommitmentPatch,
                      user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    audit,_,must,_,_,_=_deps()
    must(user,'launch.read');must(user,'document.read','rose');must(user,'commitment.review','rose')
    item=_commitment(db,item_id,launch_id)
    prev=item.status
    item.status=payload.status;item.decision_note=payload.note.strip();item.updated_at=utcnow();item.updated_by=user.id
    if payload.due_date is not None:item.due_date=payload.due_date.isoformat()
    audit(db,user,'commitment.update','email_commitment',item.id,{'from':prev,'to':item.status,'launch':launch_id})
    db.commit()
    return _commit_out(item)
