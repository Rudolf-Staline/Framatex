"""Bounded navigation sources; SQL ownership predicates precede counts and pages."""
from typing import Literal
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select,func,exists,or_,case
from sqlalchemy.orm import Session,aliased
from .core import get_db,get_current_user,utcnow
from .access import must, is_admin, permitted,launch_access_clause
from .order_documents import order_access_clause,document_access_clause,OrderDossier
from .partner_models import Partner,PartnerRequest,PartnerOrderLine
from .partner_phase2_models import BusinessOrder

router=APIRouter(tags=['Navigation métier'])

@router.get('/api/directory/{kind}')
def directory(kind:Literal['client','supplier'],q:str=Query('',max_length=150),offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),page:bool=False,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    query=select(Partner).where(Partner.kind==kind)
    order_visible=order_access_clause(user)
    request_visible=launch_access_clause(user,PartnerRequest.launch_id)
    if not is_admin(user):
        if kind=='client':query=query.where(exists(select(BusinessOrder.id).where(BusinessOrder.client_id==Partner.id,order_visible)))
        elif permitted(user,'document.read','jaune') and permitted(user,'supplier.read'):
            query=query.where(exists(select(PartnerRequest.id).where(PartnerRequest.partner_id==Partner.id,request_visible)))
        else:query=query.where(False)
    if q.strip():query=query.where(Partner.name.ilike('%'+q.strip()+'%'))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    partners=list(db.scalars(query.order_by(Partner.name,Partner.id).offset(offset).limit(limit)))
    ids=[p.id for p in partners];orders={p:[] for p in ids};requests={p:[] for p in ids};counts={}
    if ids and kind=='client':
        candidates=select(BusinessOrder.id,BusinessOrder.client_id,BusinessOrder.reference,
            func.row_number().over(partition_by=BusinessOrder.client_id,order_by=(BusinessOrder.created_at.desc(),BusinessOrder.id)).label('rank')).where(BusinessOrder.client_id.in_(ids),order_visible).subquery()
        counts=dict(db.execute(select(candidates.c.client_id,func.count()).group_by(candidates.c.client_id)).all())
        for oid,client_id,reference in db.execute(select(candidates.c.id,candidates.c.client_id,candidates.c.reference).where(candidates.c.rank<=10).order_by(candidates.c.client_id,candidates.c.rank)):
            orders[client_id].append({'id':oid,'reference':reference})
    if ids and kind=='supplier' and permitted(user,'document.read','jaune') and permitted(user,'supplier.read'):
        candidates=select(PartnerRequest.id,PartnerRequest.partner_id,PartnerRequest.title,PartnerRequest.launch_id,PartnerRequest.order_ref,PartnerRequest.status,PartnerRequest.due_date,
            func.row_number().over(partition_by=PartnerRequest.partner_id,order_by=(PartnerRequest.created_at.desc(),PartnerRequest.id)).label('rank')).where(PartnerRequest.partner_id.in_(ids),request_visible).subquery()
        counts=dict(db.execute(select(candidates.c.partner_id,func.count()).group_by(candidates.c.partner_id)).all())
        for row in db.execute(select(candidates).where(candidates.c.rank<=10).order_by(candidates.c.partner_id,candidates.c.rank)).mappings():
            requests[row['partner_id']].append({k:row[k] for k in ('id','title','launch_id','order_ref','status','due_date')})
    items=[{'id':p.id,'name':p.name,'kind':p.kind,'active':p.active,'orders':orders[p.id],'requests':requests[p.id],
        'orders_total':counts.get(p.id,0) if kind=='client' else 0,'requests_total':counts.get(p.id,0) if kind=='supplier' else 0} for p in partners]
    return {'items':items,'total':total,'offset':offset,'limit':limit} if page else items

@router.get('/api/receipts')
def receipts(user=Depends(get_current_user),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),page:bool=False):
    must(user,'launch.read');must(user,'receipt.read');must(user,'document.read','rose');must(user,'document.read','jaune')
    from .partner_delivery_routes import summaries
    query=select(PartnerOrderLine).where(launch_access_clause(user,PartnerOrderLine.launch_id))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    items=summaries(db,list(db.scalars(query.order_by(PartnerOrderLine.id).offset(offset).limit(limit))))
    return {'items':items,'total':total,'offset':offset,'limit':limit} if page else items

@router.get('/api/validation-queue')
def validation_queue(user=Depends(get_current_user),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100)):
    from .models import Document,DocumentVersion,Folder
    from .approval_models import ApprovalRun,ApprovalTemplate,ApprovalStage,ApprovalDecision
    from .partner_phase2_models import ApprovalStageAssignment
    must(user,'launch.read')
    folders=[slug for slug in ('jaune','rose','bleu','vert') if permitted(user,'document.read',slug)]
    other_version=aliased(DocumentVersion);other_run=aliased(ApprovalRun)
    latest_number=select(func.max(other_version.number)).where(other_version.document_id==Document.id).correlate(Document).scalar_subquery()
    latest_run=select(other_run.id).where(other_run.document_version_id==DocumentVersion.id).order_by(other_run.cycle.desc(),other_run.started_at.desc(),other_run.id.desc()).limit(1).correlate(DocumentVersion).scalar_subquery()
    query=select(ApprovalRun.id.label('id'),ApprovalRun.template_id,ApprovalRun.status,ApprovalRun.cycle,ApprovalRun.current_position,ApprovalRun.started_at,
        Document.id.label('document_id'),Document.title.label('document_title'),func.coalesce(Document.launch_id,Folder.launch_id).label('launch_id'),Folder.slug.label('folder'),OrderDossier.order_id,
        DocumentVersion.id.label('version_id'),DocumentVersion.number.label('version'),DocumentVersion.uploaded_by,ApprovalTemplate.name.label('template_name')).join(DocumentVersion,ApprovalRun.document_version_id==DocumentVersion.id).join(Document,DocumentVersion.document_id==Document.id).join(Folder,Document.folder_id==Folder.id).outerjoin(OrderDossier,Folder.dossier_id==OrderDossier.id).join(ApprovalTemplate,ApprovalRun.template_id==ApprovalTemplate.id).where(Folder.slug.in_(folders),document_access_clause(user),DocumentVersion.number==latest_number,ApprovalRun.id==latest_run)
    visible=query.subquery()
    total,pending=db.execute(select(func.count(),func.coalesce(func.sum(case((visible.c.status=='pending',1),else_=0)),0)).select_from(visible)).one()
    rows=list(db.execute(query.order_by(ApprovalRun.started_at.desc(),ApprovalRun.id).offset(offset).limit(limit)).mappings())
    run_ids=[r['id'] for r in rows];template_ids={r['template_id'] for r in rows}
    stages={(s.template_id,s.position):s for s in db.scalars(select(ApprovalStage).where(ApprovalStage.template_id.in_(template_ids)))} if rows else {}
    assignments={(a.run_id,a.stage_id):a for a in db.scalars(select(ApprovalStageAssignment).where(ApprovalStageAssignment.run_id.in_(run_ids)))} if rows else {}
    decided=set(db.scalars(select(ApprovalDecision.run_id).where(ApprovalDecision.run_id.in_(run_ids),ApprovalDecision.actor_id==user.id))) if rows else set()
    roles={r.id for r in user.roles};items=[]
    for row in rows:
        stage=stages.get((row['template_id'],row['current_position']));assignment=assignments.get((row['id'],stage.id)) if stage else None
        delegated=bool(assignment and assignment.delegate_id==user.id and assignment.expires_at and assignment.expires_at.replace(tzinfo=None)>utcnow().replace(tzinfo=None))
        can=bool(stage and row['status']=='pending' and permitted(user,'document.review',row['folder']) and (delegated or stage.reviewer_role_id in roles) and row['uploaded_by']!=user.id and row['id'] not in decided)
        items.append({k:v for k,v in row.items() if k not in ('uploaded_by','template_id')}|{'can_decide':can})
    return {'items':items,'pending':pending,'total':total,'offset':offset,'limit':limit}
