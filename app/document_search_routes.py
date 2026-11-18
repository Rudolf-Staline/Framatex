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
from .order_documents import OrderDossier, document_access_clause
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
           client_id:str|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read')
    folders=[f for f in ('jaune','rose','bleu','vert') if permitted(user,'document.read',f)]
    ClientPartner=aliased(Partner)
    query=select(DocumentVersion,Document,Folder,Launch,BusinessOrder.reference,ClientPartner.name,OrderDossier.order_id).join(Document,DocumentVersion.document_id==Document.id).join(Folder,Document.folder_id==Folder.id).outerjoin(Launch,func.coalesce(Document.launch_id,Folder.launch_id)==Launch.id).outerjoin(OrderDossier,Folder.dossier_id==OrderDossier.id).outerjoin(BusinessOrder,OrderDossier.order_id==BusinessOrder.id).outerjoin(ClientPartner,BusinessOrder.client_id==ClientPartner.id).where(Folder.slug.in_(folders),document_access_clause(user))
    if version is not None:query=query.where(DocumentVersion.number==version)
    else:
        other=aliased(DocumentVersion)
        query=query.where(DocumentVersion.number==select(func.max(other.number)).where(other.document_id==Document.id).scalar_subquery())
    for value,column in [(order_ref,func.coalesce(BusinessOrder.reference,Launch.order_ref)),(orli_ref,Launch.orli_ref),(client,func.coalesce(ClientPartner.name,Launch.client_name))]:
        if value:query=query.where(column.ilike('%'+value+'%'))
    if doc_type:
        from .document_types import equivalent_types,resolve_type,DocumentTypeAssignment
        resolved=resolve_type(doc_type)
        type_filter=Document.doc_type.in_(equivalent_types(doc_type))
        if resolved:
            has_assignment = exists(select(DocumentTypeAssignment.document_id).where(DocumentTypeAssignment.document_id==Document.id))
            type_filter=or_(~has_assignment & type_filter,exists(select(DocumentTypeAssignment.document_id).where(DocumentTypeAssignment.document_id==Document.id,DocumentTypeAssignment.type_id==resolved['id'])))
        query=query.where(type_filter)
    if client_id:query=query.where(BusinessOrder.client_id==client_id)
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
    total=db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows=db.execute(query.order_by(order,DocumentVersion.id).offset(offset).limit(limit)).all()
    return {'total':total,'offset':offset,'limit':limit,'items':[{'document_id':d.id,'title':d.title,'doc_type':d.doc_type,'folder':f.slug,'order_id':oid,'launch_id':d.launch_id or f.launch_id,'order_ref':reference if oid else l.order_ref if l else None,'orli_ref':l.orli_ref if l else None,'client':client_name if oid else l.client_name if l else None,'version_id':v.id,'version':v.number,'filename':v.original_name,'created_at':v.created_at,'download_url':f'/api/documents/{d.id}/versions/{v.number}/download'} for v,d,f,l,reference,client_name,oid in rows]}
