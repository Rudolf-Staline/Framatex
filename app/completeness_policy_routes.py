from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db,get_current_user
from .main import must,audit
from .access import must_access
from .partner_routes import staff
from .partner_phase2_models import RequirementPolicy,LaunchOrderContext
from .completeness_models import RequirementRule
router=APIRouter(tags=['Conditions de complétude'])
class PolicyInput(BaseModel):
    order_type:str=Field(default='',max_length=100)
    optional:bool=False
    days_after_launch:int|None=Field(default=None,ge=0,le=3650)
    requires_client_publication:bool=False
class ContextInput(BaseModel):
    order_type:str=Field(min_length=1,max_length=100)

@router.get('/api/admin/completeness/policies')
def policies(user=Depends(staff),db:Session=Depends(get_db)):
    rows=[]
    for r in db.scalars(select(RequirementRule).order_by(RequirementRule.title)):
        p=db.get(RequirementPolicy,r.id)
        rows.append({'rule_id':r.id,'label':f'{r.profile.name} · {r.title}',**({k:getattr(p,k) for k in PolicyInput.model_fields} if p else PolicyInput().model_dump())})
    return rows

@router.put('/api/admin/completeness/rules/{rid}/policy')
def set_policy(rid:str,payload:PolicyInput,user=Depends(staff),db:Session=Depends(get_db)):
    if not db.get(RequirementRule,rid):raise HTTPException(404,'Règle absente')
    row=db.get(RequirementPolicy,rid)
    if not row:row=RequirementPolicy(rule_id=rid);db.add(row)
    for k,v in payload.model_dump().items():setattr(row,k,v)
    audit(db,user,'completeness.policy','requirement_rule',rid,payload.model_dump());db.commit();return payload

@router.put('/api/launches/{lid}/order-context')
def set_context(lid:str,payload:ContextInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must_access(db,user,lid);must(user,'launch.update')
    row=db.get(LaunchOrderContext,lid)
    if not row:row=LaunchOrderContext(launch_id=lid,order_type=payload.order_type);db.add(row)
    else:row.order_type=payload.order_type
    audit(db,user,'launch.order_context','launch',lid,payload.model_dump());db.commit();return payload
