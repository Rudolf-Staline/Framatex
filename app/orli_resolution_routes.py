"""Explicit, auditable review of ambiguous imported rows; no automatic association."""
import hashlib
import json
from decimal import Decimal,InvalidOperation
from difflib import SequenceMatcher
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db
from .main import audit
from .models import Launch,AuditEvent
from .partner_routes import staff
from .orli_models import OrliImportedLaunch
from .orli_import import normalize_reference
from .orli_routes import record_out,confirm_link,LinkPayload
from .order_documents import launch_order
from .workflow_models import BusinessValueRevision

router=APIRouter(tags=['Résolution ORLI'])


def snapshot(row):
    return hashlib.sha256(json.dumps(record_out(row),sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def candidates(db,row):
    result=[]
    for launch in db.scalars(select(Launch).order_by(Launch.id)):
        matches=[];conflicts=[]
        for label,source,target in [('reference_orli',row.orli_ref,launch.orli_ref),('commande',row.order_ref,launch.order_ref),('client',row.client_name,launch.client_name)]:
            a=normalize_reference(source or '');b=normalize_reference(target or '')
            if a and b:
                if a==b:matches.append(label)
                else:
                    conflicts.append(label)
                    if label!='client' and SequenceMatcher(None,a,b).ratio()>=.8:matches.append(label+'_semblable')
            else:conflicts.append(label+'_absente')
        if not matches:continue
        quantity=db.scalar(select(BusinessValueRevision).where(BusinessValueRevision.launch_id==launch.id,BusinessValueRevision.key=='quantite_lancement').order_by(BusinessValueRevision.revision.desc()).limit(1))
        if quantity and row.quantity:
            try:
                if Decimal(quantity.value_text)!=Decimal(row.quantity):conflicts.append('quantite')
                else:matches.append('quantite')
            except InvalidOperation:conflicts.append('quantite_incompatible')
        link=launch_order(db,launch.id)
        result.append({'launch_id':launch.id,'launch_name':launch.name,'order_id':link.order_id if link else None,'order_ref':launch.order_ref,'client':launch.client_name,'quantity':quantity.value_text if quantity else None,'matches':matches,'conflicts':conflicts})
    return result


@router.get('/api/orli/records/{record_id}/resolution')
def review(record_id:str,user=Depends(staff),db:Session=Depends(get_db)):
    row=db.get(OrliImportedLaunch,record_id)
    if not row:raise HTTPException(404,'Ligne importée introuvable')
    options=candidates(db,row)
    history=[{'id':e.id,'actor_id':e.actor_id,'occurred_at':e.occurred_at,**json.loads(e.detail)} for e in db.scalars(select(AuditEvent).where(AuditEvent.action=='orli.association.decision',AuditEvent.target_id==record_id).order_by(AuditEvent.occurred_at.desc()))]
    return {'record':record_out(row),'snapshot':snapshot(row),'candidates':options,'ambiguous':len(options)!=1 or any(c['conflicts'] for c in options),'history':history,'automatic_association':False}


class ResolutionInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    decision:Literal['accept','reject']
    launch_id:str|None=Field(None,min_length=36,max_length=36)
    snapshot:str=Field(min_length=64,max_length=64,pattern=r'^[0-9a-f]{64}$')
    reason:str=Field(min_length=25,max_length=1500)
    acknowledge_conflicts:bool=False


@router.post('/api/orli/records/{record_id}/resolution',status_code=201)
def resolve(record_id:str,payload:ResolutionInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=db.get(OrliImportedLaunch,record_id)
    if not row:raise HTTPException(404,'Ligne importée introuvable')
    if snapshot(row)!=payload.snapshot:raise HTTPException(409,'La source a changé : réévaluer les candidats')
    if len(payload.reason.strip())<25:raise HTTPException(422,'Justification détaillée obligatoire')
    selected=None
    if payload.decision=='accept':
        selected=next((x for x in candidates(db,row) if x['launch_id']==payload.launch_id),None)
        if not selected:raise HTTPException(422,'Sélectionner un candidat actuel')
        if selected['conflicts'] and not payload.acknowledge_conflicts:raise HTTPException(409,'Les divergences doivent être examinées explicitement')
        # confirm_link commits its operation, so queue the history in that SAME transaction.
        audit(db,user,'orli.association.decision','orli_record',record_id,{**payload.model_dump(),'criteria':selected})
        result=confirm_link(payload.launch_id,LinkPayload(record_id=record_id,confirmation=True,reason=payload.reason,override_conflicts=payload.acknowledge_conflicts,selected_ambiguous=True),user,db)
        return {'decision':'accept','association':result}
    audit(db,user,'orli.association.decision','orli_record',record_id,payload.model_dump());db.commit()
    return {'decision':'reject','association':None}
