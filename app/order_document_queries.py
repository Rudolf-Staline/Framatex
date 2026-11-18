"""Bounded dossier summaries and version history, with ACLs before pagination."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session, aliased
from .core import get_current_user, get_db
from .access import must, permitted
from .models import Document, DocumentVersion, Folder
from .order_documents import OrderDossier, must_order, document_access_clause, version_out

router = APIRouter(tags=['Documents paginés'])


@router.get('/api/orders/{oid}/document-page')
def document_page(oid:str,folder:str=Query('jaune',pattern='^(jaune|rose|bleu|vert)$'),
                  document_id:str|None=None,q:str=Query('',max_length=200),origin:str=Query('',max_length=36),
                  offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),
                  user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .approval_models import ApprovalRun,ApprovalTemplate
    from .approval_routes import run_out
    must(user,'launch.read');must_order(db,user,oid)
    if not permitted(user,'document.read',folder):
        return {'items':[],'approvals':[],'total':0,'offset':offset,'limit':limit}
    other=aliased(DocumentVersion)
    latest=select(func.max(other.number)).where(other.document_id==Document.id).scalar_subquery()
    query=select(Document,DocumentVersion).join(Folder).join(OrderDossier,Folder.dossier_id==OrderDossier.id).outerjoin(DocumentVersion,(DocumentVersion.document_id==Document.id)&(DocumentVersion.number==latest)).where(OrderDossier.order_id==oid,Folder.slug==folder,document_access_clause(user))
    if document_id:query=query.where(Document.id==document_id)
    if q.strip():query=query.where((Document.title.ilike('%'+q.strip()+'%'))|(Document.doc_type.ilike('%'+q.strip()+'%')))
    if origin:query=query.where(Document.launch_id.is_(None) if origin=='unassigned' else Document.launch_id==origin)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.execute(query.order_by(Document.created_at.desc(),Document.id).offset(offset).limit(limit)).all()
    from .approval_routes import active_templates
    from .document_types import DocumentTypeAssignment, type_key, classification_out
    templates = active_templates(db, folder)
    assignments = {a.document_id:a for a in db.scalars(select(DocumentTypeAssignment).where(
        DocumentTypeAssignment.document_id.in_([doc.id for doc,_ in rows])))}
    version_ids=[version.id for _doc,version in rows if version]
    runs={}
    if version_ids:
        for run in db.scalars(select(ApprovalRun).where(ApprovalRun.document_version_id.in_(version_ids), ApprovalRun.obsolete.is_(False)).order_by(ApprovalRun.cycle.desc(),ApprovalRun.started_at.desc(),ApprovalRun.id)):
            runs.setdefault((run.document_version_id,run.template_id),run)
    items=[];approvals=[]
    for doc,version in rows:
        items.append({'classification':classification_out(doc,assignments.get(doc.id),folder),'id':doc.id,'title':doc.title,'doc_type':doc.doc_type,'folder':folder,'launch_id':doc.launch_id,'order_id':oid,'created_at':doc.created_at.isoformat(),'latest':version_out(version) if version else None})
        template=templates.get(type_key(doc.doc_type))
        run=runs.get((version.id,template.id)) if version and template else None
        approvals.append({'document_id':doc.id,'can_start':bool(version and template and not run and (permitted(user,'document.write',folder) or permitted(user,'document.review',folder))),'run':run_out(db,run,user,doc) if run else None})
    return {'items':items,'approvals':approvals,'total':total,'offset':offset,'limit':limit}


@router.get('/api/documents/{doc_id}/history')
def history(doc_id:str,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),
            user=Depends(get_current_user),db:Session=Depends(get_db)):
    from fastapi import HTTPException
    must(user,'launch.read')
    doc=db.scalar(select(Document).where(Document.id==doc_id,document_access_clause(user)))
    if not doc:raise HTTPException(404,'Document introuvable')
    must(user,'document.read',doc.folder.slug)
    total=db.scalar(select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id==doc_id))
    rows=db.scalars(select(DocumentVersion).where(DocumentVersion.document_id==doc_id).order_by(DocumentVersion.number.desc()).offset(offset).limit(limit))
    return {'document_id':doc_id,'total':total,'offset':offset,'limit':limit,'items':[version_out(v) for v in rows]}


@router.get('/api/order-clients')
def order_clients(q:str=Query('',max_length=150),offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100),
                  user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .partner_models import Partner
    must(user,'order.create')
    query=select(Partner.id,Partner.name).where(Partner.kind=='client',Partner.active.is_(True))
    if q.strip():query=query.where(Partner.name.ilike('%'+q.strip()+'%'))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return {'items':[{'id':oid,'name':name} for oid,name in db.execute(query.order_by(Partner.name,Partner.id).offset(offset).limit(limit))],
            'total':total,'offset':offset,'limit':limit}
