import json
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db
from .main import audit
from .models import AuditEvent
from .partner_models import PartnerAccount
from .partner_phase2_models import PartnerProfile, PartnerRole, PartnerRoleAssignment
from .partner_routes import staff, org_get
from .partner_permissions import PERMISSIONS

router=APIRouter(tags=['Référentiel partenaires'])

class ProfileInput(BaseModel):
    name: str=Field(min_length=1,max_length=150)
    trade_name: str=Field(default='',max_length=150)
    contact: str=Field(default='',max_length=2000)
    address: str=Field(default='',max_length=2000)
    domains: list[str]=Field(default_factory=list,max_length=100)
    administrative: dict[str,str]=Field(default_factory=dict,max_length=50)
    @field_validator('domains')
    @classmethod
    def validate_domains(cls,value):
        normalized=sorted(set(d.strip().lower() for d in value))
        if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\.[a-z]{2,63}',d) for d in normalized):raise ValueError('Domaines invalides')
        return normalized
    @field_validator('administrative')
    @classmethod
    def validate_fields(cls,value):
        if any(len(k)>100 or len(v)>2000 for k,v in value.items()):raise ValueError('Informations administratives trop longues')
        return value

class RoleInput(BaseModel):
    name: str=Field(min_length=1,max_length=100)
    permissions: list[str]=Field(max_length=4)
    @field_validator('permissions')
    @classmethod
    def valid_permissions(cls,value):
        if not set(value)<=PERMISSIONS or 'read' not in value:raise ValueError('Droits invalides ; read est obligatoire')
        return sorted(set(value))

class AssignmentInput(BaseModel):
    role_id: str

@router.get('/api/partners/organizations/{oid}/profile')
def profile(oid:str,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,oid);p=db.get(PartnerProfile,oid)
    history=db.scalars(select(AuditEvent).where(AuditEvent.target_id==oid).order_by(AuditEvent.occurred_at.desc()).limit(100)).all()
    return {'name':org.name,'contact':org.contact,'trade_name':p.trade_name if p else '',
            'address':p.address if p else '', 'domains':json.loads(p.domains_json) if p else [],
            'administrative':json.loads(p.administrative_json) if p else {},
            'history':[{'action':e.action,'date':e.occurred_at,'actor_id':e.actor_id,'detail':json.loads(e.detail)} for e in history]}

@router.put('/api/partners/organizations/{oid}/profile')
def update_profile(oid:str,payload:ProfileInput,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,oid);previous=profile(oid,user,db)
    row=db.get(PartnerProfile,oid)
    if not row:row=PartnerProfile(partner_id=oid);db.add(row)
    org.name=payload.name;org.contact=payload.contact
    row.trade_name=payload.trade_name;row.address=payload.address
    row.domains_json=json.dumps(payload.domains);row.administrative_json=json.dumps(payload.administrative)
    audit(db,user,'partner.profile','partner',oid,{'before':{k:v for k,v in previous.items() if k!='history'},'after':payload.model_dump()})
    db.commit();return profile(oid,user,db)

@router.get('/api/partners/organizations/{oid}/roles')
def roles(oid:str,user=Depends(staff),db:Session=Depends(get_db)):
    org_get(db,oid)
    return [{'id':r.id,'name':r.name,'permissions':json.loads(r.permissions_json)} for r in db.scalars(select(PartnerRole).where(PartnerRole.partner_id==oid))]

@router.post('/api/partners/organizations/{oid}/roles',status_code=201)
def create_role(oid:str,payload:RoleInput,user=Depends(staff),db:Session=Depends(get_db)):
    org_get(db,oid);row=PartnerRole(partner_id=oid,name=payload.name,permissions_json=json.dumps(payload.permissions))
    db.add(row);db.flush();audit(db,user,'partner.role.create','partner',oid,{'role_id':row.id,**payload.model_dump()});db.commit()
    return {'id':row.id,**payload.model_dump()}

@router.put('/api/partners/accounts/{aid}/role')
def assign_role(aid:str,payload:AssignmentInput,user=Depends(staff),db:Session=Depends(get_db)):
    account=db.get(PartnerAccount,aid);role=db.get(PartnerRole,payload.role_id)
    if not account or not role or role.partner_id!=account.partner_id:raise HTTPException(404,'Compte ou rôle introuvable dans cette organisation')
    row=db.get(PartnerRoleAssignment,aid)
    if not row:row=PartnerRoleAssignment(account_id=aid,role_id=role.id);db.add(row)
    else:row.role_id=role.id
    audit(db,user,'partner.role.assign','partner',account.partner_id,{'account_id':aid,'role_id':role.id});db.commit()
    return {'role_id':role.id}
