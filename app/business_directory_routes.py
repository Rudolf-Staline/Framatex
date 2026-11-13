"""Navigation sources filtered by business ownership before display/counting."""
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db,get_current_user
from .access import must, is_admin, permitted
from .models import Launch
from .access import accessible
from .order_documents import order_accessible
from .partner_models import Partner,PartnerRequest,PartnerOrderLine
from .partner_phase2_models import BusinessOrder

router=APIRouter(tags=['Navigation métier'])

@router.get('/api/directory/{kind}')
def directory(kind:Literal['client','supplier'],user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    orders=[o for o in db.scalars(select(BusinessOrder)) if order_accessible(db,user,o.id)]
    requests=[r for r in db.scalars(select(PartnerRequest)) if accessible(db,user,db.get(Launch,r.launch_id))]
    ids={o.client_id for o in orders} if kind=='client' else {r.partner_id for r in requests}
    return [{'id':p.id,'name':p.name,'kind':p.kind,'active':p.active,
             'orders':[{'id':o.id,'reference':o.reference} for o in orders if o.client_id==p.id] if kind=='client' else [],
             'requests':[{'id':r.id,'title':r.title,'launch_id':r.launch_id,'order_ref':r.order_ref,'status':r.status,'due_date':r.due_date} for r in requests if r.partner_id==p.id and permitted(user,'document.read','jaune')] if kind=='supplier' else []}
            for p in db.scalars(select(Partner).where(Partner.kind==kind).order_by(Partner.name)) if is_admin(user) or p.id in ids]

@router.get('/api/receipts')
def receipts(user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');must(user,'document.read','rose');must(user,'document.read','jaune')
    from .partner_delivery_routes import output
    return [output(db,line) for line in db.scalars(select(PartnerOrderLine).order_by(PartnerOrderLine.id)) if accessible(db,user,db.get(Launch,line.launch_id))]

@router.get('/api/validation-queue')
def validation_queue(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .models import Document,DocumentVersion
    from .order_documents import document_accessible,document_order_id
    from .approval_models import ApprovalRun
    from .approval_routes import run_out
    must(user,'launch.read');items=[]
    for doc in db.scalars(select(Document)):
        if not permitted(user,'document.read',doc.folder.slug) or not document_accessible(db,user,doc) or not doc.versions:continue
        version=max(doc.versions,key=lambda v:v.number)
        run=db.scalar(select(ApprovalRun).where(ApprovalRun.document_version_id==version.id).order_by(ApprovalRun.cycle.desc(),ApprovalRun.started_at.desc()).limit(1))
        if run:items.append({**run_out(db,run,user,doc),'order_id':document_order_id(db,doc),'launch_id':doc.context_launch_id})
    return {'items':items,'pending':sum(r['status']=='pending' for r in items)}
