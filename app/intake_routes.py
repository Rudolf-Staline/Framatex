"""0.5 : aperçu OCR et classement, vérification humaine avant dépôt/exploitation."""
from __future__ import annotations
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .core import get_db, get_current_user
from .models import DocumentVersion, Document, User
from .intake_models import ConfirmedField
from .intake import PATTERNS, preview
from .main import STORAGE, MAX_UPLOAD, SLUGS, get_doc, get_launch, verify_file, EXTS
from .audit import audit
from .access import must, permitted

router=APIRouter()

class ConfirmField(BaseModel):
    field_key: str
    value: str = Field(min_length=1,max_length=140)
    unit: str = Field(default="",max_length=30)
    source_excerpt: str = Field(default="",max_length=180)

@router.post('/api/launches/{launch_id}/intake/preview')
async def intake_preview(launch_id:str,file:UploadFile=File(...),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    get_launch(db,launch_id)
    # On n'effectue aucune analyse si le collaborateur n'a le droit de déposer dans aucune rubrique.
    if not any(permitted(user,'document.write',f) for f in SLUGS):
        raise HTTPException(403,'Dépôt interdit')
    from .main import store_upload, STORAGE as private_storage
    from starlette.concurrency import run_in_threadpool
    name,disk_name,_size,_sha,_mime=await store_upload(file)
    path=private_storage/disk_name
    try:
        result=await run_in_threadpool(preview,path,name)
        result['classification']['suggestions']=[x for x in result['classification']['suggestions'] if permitted(user,'document.write',x['folder'])]
        return result
    finally:path.unlink(missing_ok=True)

@router.get('/api/document-versions/{version_id}/intake')
def version_intake(version_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    v=db.get(DocumentVersion,version_id)
    if not v:raise HTTPException(404,'Version introuvable')
    doc=get_doc(db,v.document_id)
    must(user,'launch.read')
    must(user,'document.read',doc.folder.slug)
    path=STORAGE/v.disk_name
    if not path.exists(): raise HTTPException(503,'Fichier indisponible')
    # Analyse demandée explicitement par l'utilisateur. Aucune extraction poussée vers l'ERP.
    result=preview(path,v.original_name)
    result['version_id']=v.id
    result['confirmed']=[{'id':x.id,'key':x.field_key,'value':x.value,'unit':x.unit,'confirmed_at':x.confirmed_at.isoformat()} for x in db.scalars(select(ConfirmedField).where(ConfirmedField.document_version_id==v.id)).all()]
    return result

@router.post('/api/document-versions/{version_id}/intake/confirm',status_code=201)
def confirm_field(version_id:str,payload:ConfirmField,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    v=db.get(DocumentVersion,version_id)
    if not v:raise HTTPException(404,'Version introuvable')
    doc=get_doc(db,v.document_id)
    must(user,'launch.read')
    must(user,'document.read',doc.folder.slug)
    must(user,'document.write',doc.folder.slug)
    if payload.field_key not in PATTERNS:raise HTTPException(422,'Champ métier inconnu')
    if not v==max(doc.versions,key=lambda x:x.number):raise HTTPException(409,'Une nouvelle version du document existe')
    item=ConfirmedField(document_version_id=v.id,field_key=payload.field_key,
          value=payload.value.strip(),unit=payload.unit.strip(),source_excerpt=payload.source_excerpt.strip(),confirmed_by=user.id)
    db.add(item)
    try:
        db.flush()
        audit(db,user,'intake.field.confirm','document_version',v.id,{'key':payload.field_key})
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Ce champ a déjà été confirmé pour cette version')
    return {'id':item.id,'key':item.field_key,'value':item.value,'unit':item.unit,'version_id':v.id}
