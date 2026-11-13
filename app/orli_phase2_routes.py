"""Persistent file mapping profiles and explicit immutable snapshot reconciliation."""
import json
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .core import get_db,utcnow
from .audit import audit
from .partner_routes import staff
from .partner_phase2_models import OrliMappingProfile,OrliRefreshDecision
from .orli_models import OrliImportBatch,OrliImportedLaunch,OrliLink
from .orli_import import parse_mapping,normalize_reference
from .orli_routes import record_out
router=APIRouter(tags=['Profils et réimports ORLI'])

class ProfileInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    mapping:dict[str,str]

@router.post('/api/orli/profiles',status_code=201)
def create_profile(payload:ProfileInput,user=Depends(staff),db:Session=Depends(get_db)):
    mapping=parse_mapping(json.dumps(payload.mapping));row=OrliMappingProfile(name=payload.name,mapping_json=json.dumps(mapping),created_by=user.id)
    db.add(row);db.flush();audit(db,user,'orli.profile.create','orli_profile',row.id);db.commit();return {'id':row.id,'name':row.name,'mapping':mapping}

@router.get('/api/orli/profiles')
def profiles(user=Depends(staff),db:Session=Depends(get_db)):
    return [{'id':r.id,'name':r.name,'mapping':json.loads(r.mapping_json)} for r in db.scalars(select(OrliMappingProfile).order_by(OrliMappingProfile.name))]

def indexed(db,bid):
    if not db.get(OrliImportBatch,bid):raise HTTPException(404,'Instantané absent')
    result={}
    for row in db.scalars(select(OrliImportedLaunch).where(OrliImportedLaunch.batch_id==bid)):
        key=normalize_reference(row.orli_ref or '')
        result.setdefault(key,[]).append(row)
    return result

@router.get('/api/orli/compare')
def compare(previous:str,current:str,user=Depends(staff),db:Session=Depends(get_db)):
    before=indexed(db,previous);after=indexed(db,current);rows=[]
    for key in sorted(set(before)|set(after)):
        old=before.get(key,[]);new=after.get(key,[])
        ambiguous=not key or len(old)>1 or len(new)>1 or any(json.loads(r.error_json) for r in old+new)
        fields=['order_ref','client_name','designation','quantity','status']
        changes={f:{'before':getattr(old[0],f),'after':getattr(new[0],f)} for f in fields if old and new and getattr(old[0],f)!=getattr(new[0],f)}
        rows.append({'reference':key,'status':'ambiguous' if ambiguous else 'added' if not old else 'removed' if not new else 'changed' if changes else 'unchanged',
            'before':[record_out(r) for r in old],'after':[record_out(r) for r in new],'changes':changes})
    return {'previous':previous,'current':current,'rows':rows,'writes_to_orli':False}

class RefreshInput(BaseModel):
    expected_record_id:str
    record_id:str
    decision:Literal['keep','accept']
    reason:str=Field(min_length=12,max_length=1500)

@router.post('/api/orli/launches/{lid}/refresh',status_code=201)
def refresh(lid:str,payload:RefreshInput,user=Depends(staff),db:Session=Depends(get_db)):
    link=db.scalar(select(OrliLink).where(OrliLink.launch_id==lid));new=db.get(OrliImportedLaunch,payload.record_id)
    if not link or not new:raise HTTPException(404,'Association ou instantané absent')
    if link.record_id!=payload.expected_record_id:raise HTTPException(409,'Association modifiée : actualiser')
    old=db.get(OrliImportedLaunch,link.record_id)
    if new.id==old.id or new.batch_id==old.batch_id or json.loads(new.error_json) or normalize_reference(old.orli_ref)!=normalize_reference(new.orli_ref):raise HTTPException(409,'Nouvel instantané valide de la même référence requis')
    if payload.decision=='accept' and db.scalar(select(OrliLink.id).where(OrliLink.record_id==new.id,OrliLink.id!=link.id)):
        raise HTTPException(409,'Instantané déjà associé à un autre lancement')
    # CAS for both decisions: even keeping a source cannot attest a stale link.
    try:
        changed=db.execute(update(OrliLink).where(OrliLink.id==link.id,OrliLink.record_id==payload.expected_record_id).values(
            record_id=new.id if payload.decision=='accept' else old.id,
            confirmed_by=user.id,confirmed_at=utcnow(),decision_note=payload.reason),execution_options={'synchronize_session':False})
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Association concurrente : actualiser')
    if changed.rowcount!=1:raise HTTPException(409,'Association modifiée par un autre utilisateur')
    row=OrliRefreshDecision(launch_id=lid,previous_record_id=old.id,next_record_id=new.id,decision=payload.decision,reason=payload.reason,decided_by=user.id)
    db.add(row);db.flush();audit(db,user,'orli.refresh.decision','launch',lid,payload.model_dump());db.commit()
    return {'id':row.id,'selected_record_id':new.id if payload.decision=='accept' else old.id,'written_to_orli':False,'internal_values_changed':False}

@router.get('/api/orli/refresh-decisions')
def history(user=Depends(staff),db:Session=Depends(get_db)):
    return [{k:getattr(r,k) for k in ('id','launch_id','previous_record_id','next_record_id','decision','reason','decided_by','created_at')} for r in db.scalars(select(OrliRefreshDecision).order_by(OrliRefreshDecision.created_at.desc()).limit(100))]
