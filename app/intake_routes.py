"""0.5 : aperçu OCR et classement, vérification humaine avant dépôt/exploitation."""
from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .core import get_db, get_current_user
from .models import DocumentVersion, Document, User
from .intake_models import ConfirmedField
from .intake import PATTERNS
from .document_intake import read_safely
from .document_intake_models import DocumentIdentification
from .main import STORAGE, SLUGS, audit, get_doc, get_launch, must, permitted, store_upload

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
    name, disk_name, *_ = await store_upload(file)
    path = STORAGE / disk_name
    try:
        result = await run_in_threadpool(read_safely, path, name)
        original = result['classification']['suggestions']
        # Ne jamais révéler une rubrique suggérée que le collaborateur n'a pas le droit d'utiliser.
        filtered = [x for x in original if permitted(user, 'document.write', x['folder'])]
        result['classification']['suggestions'] = filtered
        result['classification']['decisive'] = bool(filtered) and original[0] == filtered[0] and result['classification']['decisive']
        return result
    finally:
        path.unlink(missing_ok=True)

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
    identification = db.get(DocumentIdentification, v.id)
    result = dict(identification.analysis) if identification and identification.analysis['method'] not in {'busy', 'analysis_failed', 'ocr_unavailable', 'pdf_unreadable'} else read_safely(path, v.original_name)
    result['identification'] = {'status': identification.status, 'justification': identification.justification} if identification else None
    result['version_id']=v.id
    result['confirmed']=[{'key':x.field_key,'value':x.value,'unit':x.unit,'confirmed_at':x.confirmed_at.isoformat()} for x in db.scalars(select(ConfirmedField).where(ConfirmedField.document_version_id==v.id)).all()]
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
