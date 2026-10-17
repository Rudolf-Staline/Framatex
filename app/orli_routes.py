"""Module 0.11 — snapshots ORLI en lecture seule et rapprochement contrôlé.

N'écrit jamais dans ORLI ; ne crée pas de lancement automatiquement.
"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_db, get_current_user
from .models import Launch, User
from .orli_models import OrliImportBatch, OrliImportedLaunch, OrliLink
from .orli_import import MAX_BYTES, parse_mapping, read_export, normalize_reference
from .main import audit, get_launch, must, admin_only

router = APIRouter()


def batch_out(b):
    return {'id':b.id,'file_name':b.file_name,'file_sha256':b.file_sha256,
            'format':b.format_name,'total_rows':b.total_rows,'valid_rows':b.valid_rows,
            'imported_at':b.imported_at.isoformat(),'imported_by':b.imported_by}


def record_out(r):
    return {'id':r.id,'batch_id':r.batch_id,'row_number':r.row_number,'orli_ref':r.orli_ref,
            'order_ref':r.order_ref,'client_name':r.client_name,'designation':r.designation,
            'quantity':r.quantity,'status':r.status,'errors':json.loads(r.error_json)}


def current_link(db, launch_id):
    return db.scalar(select(OrliLink).where(OrliLink.launch_id == launch_id))


@router.post('/api/orli/imports', status_code=201)
async def import_export(file: UploadFile=File(...), mapping: str=Form(...),
                        user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    admin_only(user)
    original=(file.filename or '').replace('\\','/').split('/')[-1][:240]
    try:
        data=await file.read(MAX_BYTES+1)
    finally:
        await file.close()
    normalized_map=parse_mapping(mapping)
    parsed=read_export(data,original,normalized_map)
    if not parsed['rows']:
        raise HTTPException(422, 'Aucune ligne métier à importer')
    prior=db.scalar(select(OrliImportBatch).where(OrliImportBatch.file_sha256==parsed['sha256']))
    if prior: raise HTTPException(409, 'Ce fichier a déjà été importé : '+prior.id)
    batch=OrliImportBatch(file_name=original,file_sha256=parsed['sha256'],
                          format_name=parsed['format'],mapping_json=json.dumps(normalized_map,ensure_ascii=False),
                          total_rows=parsed['total_rows'],valid_rows=parsed['valid_rows'],imported_by=user.id)
    db.add(batch);db.flush()
    for row in parsed['rows']:
        values=row['fields']
        db.add(OrliImportedLaunch(batch_id=batch.id,row_number=row['row_number'],
                orli_ref=values.get('orli_ref'),order_ref=values.get('order_ref'),
                client_name=values.get('client_name'),designation=values.get('designation'),
                quantity=values.get('quantity'),status=values.get('status'),
                error_json=json.dumps(row['errors'],ensure_ascii=False),
                raw_json=json.dumps(values,ensure_ascii=False)))
    audit(db,user,'orli.import','orli_batch',batch.id,
          {'rows':batch.total_rows,'valid_rows':batch.valid_rows,'sha256':batch.file_sha256})
    db.commit()
    return {**batch_out(batch),'errors':sum(bool(r['errors']) for r in parsed['rows'])}


@router.get('/api/orli/imports')
def list_imports(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    rows=db.scalars(select(OrliImportBatch).order_by(OrliImportBatch.imported_at.desc()).limit(30)).all()
    return [batch_out(b) for b in rows]


@router.get('/api/orli/imports/{batch_id}')
def inspect_import(batch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    batch=db.get(OrliImportBatch,batch_id)
    if not batch: raise HTTPException(404,'Import introuvable')
    rows=db.scalars(select(OrliImportedLaunch).where(OrliImportedLaunch.batch_id==batch_id)
                  .order_by(OrliImportedLaunch.row_number)).all()
    links=db.scalars(select(OrliLink).where(OrliLink.record_id.in_([r.id for r in rows]))).all() if rows else []
    linked={x.record_id:x.launch_id for x in links}
    return {**batch_out(batch),'mapping':json.loads(batch.mapping_json),
            'rows':[{**record_out(r),'linked_launch_id':linked.get(r.id)} for r in rows]}


@router.get('/api/launches/{launch_id}/orli-reconciliation')
def reconcile(launch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    launch=get_launch(db,launch_id)
    link=current_link(db,launch_id)
    if not (any(role.name=='Administrateur' for role in user.roles) or 
            any(grant.action=='launch.update' and grant.folder_slug is None for role in user.roles for grant in role.grants)):
        return {'launch_id':launch_id,'launch_orli_ref':launch.orli_ref,
                'linked':{'id':link.id,'source_ref':link.source_ref,'confirmed_at':link.confirmed_at.isoformat()} if link else None,
                'candidates':[],'truncated':False,'restricted':True}
    rows=db.scalars(select(OrliImportedLaunch).order_by(OrliImportedLaunch.row_number).limit(3000)).all()
    all_links=db.scalars(select(OrliLink)).all()
    used={x.record_id:x.launch_id for x in all_links}
    candidates=[]
    for row in rows:
        if row.error_json!='[]' or not row.orli_ref: continue
        evidence=[]
        if launch.orli_ref and normalize_reference(launch.orli_ref)==normalize_reference(row.orli_ref): evidence.append('reference_orli')
        if launch.order_ref and row.order_ref and normalize_reference(launch.order_ref)==normalize_reference(row.order_ref): evidence.append('commande')
        if not evidence: continue
        conflicts=[]
        if launch.order_ref and row.order_ref and normalize_reference(launch.order_ref)!=normalize_reference(row.order_ref): conflicts.append('commande')
        if launch.client_name and row.client_name and normalize_reference(launch.client_name)!=normalize_reference(row.client_name): conflicts.append('client')
        candidates.append({**record_out(row),'matches':evidence,'conflicts':conflicts,
                           'already_linked':row.id in used,
                           'linked_launch_id':used.get(row.id)})
    candidates.sort(key=lambda x:(0 if 'reference_orli' in x['matches'] else 1,
                                  0 if not x['conflicts'] else 1,x['batch_id'],x['row_number']))
    return {'launch_id':launch_id,'launch_orli_ref':launch.orli_ref,
            'linked': {'id':link.id,'record_id':link.record_id,'source_ref':link.source_ref,
                       'confirmed_at':link.confirmed_at.isoformat(), 'decision_note':link.decision_note} if link else None,
            'candidates':candidates[:100], 'truncated':len(candidates)>100}


class LinkPayload(BaseModel):
    record_id: str = Field(min_length=36,max_length=36)
    confirmation: bool
    reason: str = Field(min_length=12,max_length=1500)
    override_conflicts: bool = False


@router.post('/api/launches/{launch_id}/orli-reconciliation/link',status_code=201)
def confirm_link(launch_id:str,payload:LinkPayload,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.update')
    launch=get_launch(db,launch_id)
    if launch.status=='Clôturé': raise HTTPException(409,'Lancement clôturé : rapprochement interdit')
    if not payload.confirmation: raise HTTPException(422,'Une confirmation humaine explicite est requise')
    if not payload.reason.strip() or len(payload.reason.strip())<12:
        raise HTTPException(422,'Justification attendue (au moins 12 caractères)')
    row=db.get(OrliImportedLaunch,payload.record_id)
    if not row: raise HTTPException(404,'Ligne ORLI introuvable')
    if json.loads(row.error_json) or not row.orli_ref:
        raise HTTPException(422,'Ligne importée invalide ou ambiguë')
    if current_link(db,launch_id):
        raise HTTPException(409,'Ce lancement est déjà rapproché : aucun remplacement automatique')
    if db.scalar(select(OrliLink).where(OrliLink.record_id==row.id)):
        raise HTTPException(409,'Ligne ORLI déjà rattachée à un autre lancement')
    norm=normalize_reference(row.orli_ref)
    if launch.orli_ref and normalize_reference(launch.orli_ref)!=norm:
        raise HTTPException(409,'Référence ORLI actuelle différente : corriger manuellement le dossier au préalable')
    # La même référence ORLI ne doit pas représenter deux lancements numériques.
    all_launches=db.scalars(select(Launch).where(Launch.id!=launch_id)).all()
    if any(l.orli_ref and normalize_reference(l.orli_ref)==norm for l in all_launches):
        raise HTTPException(409,'Cette référence ORLI est déjà utilisée sur un autre lancement')
    evidence=((launch.orli_ref and normalize_reference(launch.orli_ref)==norm) or
              (launch.order_ref and row.order_ref and normalize_reference(launch.order_ref)==normalize_reference(row.order_ref)))
    if not evidence:
        raise HTTPException(409, 'Aucune référence ORLI ou de commande ne correspond à ce dossier')
    conflicts=[]
    if launch.order_ref and row.order_ref and normalize_reference(launch.order_ref)!=normalize_reference(row.order_ref): conflicts.append('commande')
    if launch.client_name and row.client_name and normalize_reference(launch.client_name)!=normalize_reference(row.client_name): conflicts.append('client')
    if conflicts and not payload.override_conflicts:
        raise HTTPException(409,'Écarts à justifier explicitement : '+', '.join(conflicts))
    if conflicts and len(payload.reason.strip())<25:
        raise HTTPException(422,'La dérogation à une divergence exige une justification détaillée')
    link=OrliLink(launch_id=launch.id,record_id=row.id,source_ref=row.orli_ref,
                  decision_note=payload.reason.strip(),confirmed_by=user.id)
    db.add(link)
    if not launch.orli_ref: launch.orli_ref=row.orli_ref
    audit(db,user,'orli.link.confirm','launch',launch.id,
          {'record_id':row.id,'batch_id':row.batch_id,'reference':row.orli_ref,
           'conflicts':conflicts,'override':payload.override_conflicts,'reason':payload.reason.strip()})
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Rapprochement déjà effectué par une autre opération')
    return {'id':link.id,'launch_id':launch.id,'orli_ref':launch.orli_ref,
            'record_id':row.id,'conflicts_accepted':conflicts,'written_to_orli':False}
