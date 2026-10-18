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
from .main import STORAGE, MAX_UPLOAD, SLUGS, audit, get_doc, get_launch, must, permitted, verify_file, EXTS

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
    name=Path((file.filename or '').replace('\\','/')).name[:240]
    suffix=Path(name).suffix.lower()
    if suffix not in EXTS: raise HTTPException(422,'Format interdit')
    # Aperçu isolé, jamais conservé comme pièce du dossier. Refuser les uploads trop volumineux.
    path=STORAGE/("preview-"+secrets.token_hex(18))
    try:
        total=0
        with path.open('xb') as dest:
            while chunk:=await file.read(1024*1024):
                total+=len(chunk)
                if total>MAX_UPLOAD: raise HTTPException(413,'Fichier supérieur à 20 Mo')
                dest.write(chunk)
        if not total:raise HTTPException(422,'Fichier vide')
        verify_file(path,suffix)
        result=preview(path,name)
        # Ne jamais révéler une rubrique suggérée que le collaborateur n'a pas le droit d'utiliser.
        result['classification']['suggestions']=[x for x in result['classification']['suggestions'] if permitted(user,'document.write',x['folder'])]
        return result
    finally:
        await file.close()
        path.unlink(missing_ok=True)

@router.get('/api/document-versions/{version_id}/intake')
def version_intake(version_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    v=db.get(DocumentVersion,version_id)
    if not v:raise HTTPException(404,'Version introuvable')
    doc=get_doc(db,v.document_id)
    must(user,'launch.read')
    must(user,'document.read',doc.folder.slug)
    from .cloud_storage import ensure_local
    path=ensure_local(v.disk_name,STORAGE)
    if not path.exists(): raise HTTPException(503,'Fichier indisponible')
    # Analyse demandée explicitement par l'utilisateur. Aucune extraction poussée vers l'ERP.
    result=preview(path,v.original_name)
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
