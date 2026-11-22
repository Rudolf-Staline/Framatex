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


@router.get('/api/document-versions/{version_id}/compare-previous')
def compare_previous(version_id: str, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    """Compare une version uniquement à sa précédente version du même document."""
    current=db.get(DocumentVersion,version_id)
    if not current: raise HTTPException(404,'Version introuvable')
    document=get_doc(db,current.document_id)
    must(user,'launch.read');must(user,'document.read',document.folder.slug)
    previous=next((item for item in document.versions if item.number==current.number-1),None)
    if not previous: return {'status':'first_version','current_version':current.number,'changes':[],'notice':'Première version : aucune comparaison disponible.'}
    before=db.get(DocumentIdentification,previous.id);after=db.get(DocumentIdentification,current.id)
    def field_map(item):
        if not item:return {}
        return {entry['key']:entry for entry in item.analysis.get('fields',[])}
    old,new=field_map(before),field_map(after)
    changes=[]
    for key in sorted(set(old)|set(new)):
        a,b=old.get(key),new.get(key)
        av=(a.get('value'),a.get('unit')) if a else None
        bv=(b.get('value'),b.get('unit')) if b else None
        if av!=bv:
            changes.append({'field':key,'kind':'added' if a is None else 'removed' if b is None else 'changed',
                'previous':a,'current':b,'explanation':'Valeur extraite automatiquement; confirmer avec le document source.'})
    from .quality_models import ExcelInspection
    inspection=db.scalar(select(ExcelInspection).where(ExcelInspection.document_version_id==current.id))
    formulas=[]
    if inspection:
        formulas=[item for item in json.loads(inspection.findings_json) if item.get('type') in {'formula_changed','formula_removed','broken_reference'}]
    return {'status':'compared','document_id':document.id,'previous_version':previous.number,
        'current_version':current.number,'changes':changes,'excel_formula_changes':formulas,
        'notice':'La comparaison est indicative et limitée aux champs analysés et aux inspections Excel disponibles.'}

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
