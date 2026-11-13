"""Metadata-only document search, permission filtered before sorting/pagination."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,Query
from fastapi.responses import FileResponse
from sqlalchemy import select,func,or_,exists
from sqlalchemy.orm import Session,aliased
from .core import get_db,get_current_user,ROOT
from .access import must, permitted, is_admin
from .models import Document,DocumentVersion,Folder,Launch,LaunchMember,User
from .workflow_models import DocumentReview
from .partner_phase2_models import PartnerIntegration, BusinessOrder
from .order_documents import OrderDossier, document_accessible
from .partner_models import PartnerSubmission,PartnerRequest,Partner

router=APIRouter(tags=['Recherche documentaire'])

@router.get('/search')
def search_page():
    return FileResponse(ROOT/'static'/'document-search.html',headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"})

@router.get('/api/document-search')
def search(q:str=Query('',max_length=200),order_ref:str=Query('',max_length=100),orli_ref:str=Query('',max_length=100),
           client:str=Query('',max_length=150),supplier:str=Query('',max_length=150),doc_type:str=Query('',max_length=100),
           folder:Literal['jaune','rose','bleu','vert']|None=None,author:str=Query('',max_length=120),
           status:Literal['approved','rejected','changes_requested','to_review']|None=None,
           after:datetime|None=None,before:datetime|None=None,version:int|None=Query(None,ge=1,le=1000000),
           sort:Literal['newest','oldest','title']='newest',offset:int=Query(0,ge=0,le=1000000000),limit:int=Query(25,ge=1,le=100),
           user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    folders=[f for f in ('jaune','rose','bleu','vert') if permitted(user,'document.read',f)]
    query=select(DocumentVersion,Document,Folder,Launch).join(Document,DocumentVersion.document_id==Document.id).join(Folder,Document.folder_id==Folder.id).outerjoin(Launch,func.coalesce(Document.launch_id,Folder.launch_id)==Launch.id).outerjoin(OrderDossier,Folder.dossier_id==OrderDossier.id).outerjoin(BusinessOrder,OrderDossier.order_id==BusinessOrder.id).where(Folder.slug.in_(folders))
    if version is not None:query=query.where(DocumentVersion.number==version)
    else:
        other=aliased(DocumentVersion)
        query=query.where(DocumentVersion.number==select(func.max(other.number)).where(other.document_id==Document.id).scalar_subquery())
    for value,column in [(order_ref,func.coalesce(BusinessOrder.reference,Launch.order_ref)),(orli_ref,Launch.orli_ref),(client,Launch.client_name),(doc_type,Document.doc_type)]:
        if value:query=query.where(column.ilike('%'+value+'%'))
    if q:query=query.where(or_(Document.title.ilike('%'+q+'%'),DocumentVersion.original_name.ilike('%'+q+'%')))
    if folder:query=query.where(Folder.slug==folder)
    if author:query=query.where(exists(select(User.id).where(User.id==DocumentVersion.uploaded_by,User.name.ilike('%'+author+'%'))))
    if supplier:
        query=query.where(exists(select(PartnerIntegration.submission_id).join(PartnerSubmission,PartnerIntegration.submission_id==PartnerSubmission.id).join(PartnerRequest,PartnerSubmission.request_id==PartnerRequest.id).join(Partner,PartnerRequest.partner_id==Partner.id).where(PartnerIntegration.version_id==DocumentVersion.id,Partner.name.ilike('%'+supplier+'%'))))
    review=select(DocumentReview.decision).where(DocumentReview.document_version_id==DocumentVersion.id).order_by(DocumentReview.reviewed_at.desc(),DocumentReview.id.desc()).limit(1).scalar_subquery()
    if status:query=query.where(func.coalesce(review,'to_review')==status)
    if after:query=query.where(DocumentVersion.created_at>=after)
    if before:query=query.where(DocumentVersion.created_at<=before)
    order={'newest':DocumentVersion.created_at.desc(),'oldest':DocumentVersion.created_at.asc(),'title':Document.title.asc()}[sort]
    allowed=[r for r in db.execute(query.order_by(order,DocumentVersion.id)).all() if document_accessible(db,user,r[1])]
    total=len(allowed);rows=allowed[offset:offset+limit]
    return {'total':total,'offset':offset,'limit':limit,'items':[{'document_id':d.id,'title':d.title,'doc_type':d.doc_type,'folder':f.slug,'order_id':db.get(OrderDossier,f.dossier_id).order_id if f.dossier_id else None,'launch_id':d.launch_id,'order_ref':db.get(BusinessOrder,db.get(OrderDossier,f.dossier_id).order_id).reference if f.dossier_id else l.order_ref,'orli_ref':l.orli_ref if l else None,'client':l.client_name if l else None,'version_id':v.id,'version':v.number,'filename':v.original_name,'created_at':v.created_at,'download_url':f'/api/documents/{d.id}/versions/{v.number}/download'} for v,d,f,l in rows]}
