"""Additive order registry. Explicit links preserve all original launch data and ACLs."""
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,func,or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_db, get_current_user
from .audit import audit
from .models import Launch,Document,Folder,DocumentVersion
from .order_documents import dossier, adopt_launch, must_order, order_accessible, OrderDossier, document_accessible, order_access_clause
from .access import must_access, accessible
from .access import permitted, must
from .partner_routes import staff,org_get
from .partner_models import PartnerRequest,PartnerOrderLine,Partner
from .partner_phase2_models import BusinessOrder,BusinessOrderLaunch,PartnerClientOrder
from .sharing_models import ClientPublication
from .sharing_routes import norm
from .orli_models import OrliLink
from .material_models import MaterialLine
router=APIRouter(tags=['Référentiel commandes'])

class OrderInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    client_id:str=Field(min_length=36,max_length=36)
    reference:str=Field(min_length=1,max_length=100)
class LinkInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    launch_id:str=Field(min_length=36,max_length=36)

def check_order_scope(db,lid,reference=None,client_id=None):
    link=db.get(BusinessOrderLaunch,lid)
    if not link:return
    order=db.get(BusinessOrder,link.order_id)
    if reference is not None and reference!=order.reference:raise HTTPException(409,'Référence incompatible avec la commande de rattachement')
    if client_id is not None and client_id!=order.client_id:raise HTTPException(409,'Client incompatible avec la commande de rattachement')

def out(db,row,user):
    return {'id':row.id,'reference':row.reference,'client_id':row.client_id,'client_name':db.get(Partner,row.client_id).name,'created_at':row.created_at,
        'launches':[{'id':l.id,'name':l.name,'order_ref':l.order_ref,'orli_ref':l.orli_ref,'status':l.status} for l in db.scalars(select(Launch).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id==row.id)) if accessible(db,user,l)]}

@router.get('/api/orders')
def list_orders(response:Response,q:str=Query('',max_length=200),
                sort:str=Query('newest',pattern='^(newest|reference|client)$'),
                offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100),page:bool=False,
                user=Depends(get_current_user),db:Session=Depends(get_db)):
    """Bounded SQL page; legacy list consumers retain their item representation."""
    from .access import launch_access_clause
    must(user,"launch.read")
    query=select(BusinessOrder,Partner.name).join(Partner,BusinessOrder.client_id==Partner.id).where(order_access_clause(user))
    if q.strip():
        term='%'+q.strip()+'%'
        query=query.where(or_(BusinessOrder.reference.ilike(term),Partner.name.ilike(term)))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    ordering={'newest':BusinessOrder.created_at.desc(),'reference':BusinessOrder.reference.asc(),'client':Partner.name.asc()}[sort]
    rows=db.execute(query.order_by(ordering,BusinessOrder.id).offset(offset).limit(limit)).all()
    ids=[r.id for r,_name in rows];launches={oid:[] for oid in ids}
    if ids:
        for lid,lname,ref,orli,status,oid in db.execute(select(Launch.id,Launch.name,Launch.order_ref,Launch.orli_ref,Launch.status,BusinessOrderLaunch.order_id).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id.in_(ids),launch_access_clause(user,Launch.id)).order_by(Launch.created_at,Launch.id)):
            launches[oid].append({'id':lid,'name':lname,'order_ref':ref,'orli_ref':orli,'status':status})
    items=[{'id':r.id,'reference':r.reference,'client_id':r.client_id,'client_name':name,'created_at':r.created_at,'launches':launches[r.id]} for r,name in rows]
    response.headers['X-Total-Count']=str(total)
    return {'items':items,'total':total,'offset':offset,'limit':limit} if page else items

@router.post('/api/orders',status_code=201)
def create(payload:OrderInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'order.create')
    org=org_get(db,payload.client_id,'client')
    if not org.active or not payload.reference.strip():raise HTTPException(422,'Client actif et référence nécessaires')
    row=BusinessOrder(client_id=org.id,reference=payload.reference.strip(),created_by=user.id);db.add(row)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Commande déjà enregistrée')
    dossier(db,row.id)
    audit(db,user,'order.create','order',row.id,payload.model_dump());db.commit();return out(db,row,user)

@router.post('/api/orders/{oid}/launches',status_code=201)
def link(oid:str,payload:LinkInput,user=Depends(staff),db:Session=Depends(get_db)):
    order=must_order(db,user,oid);launch=must_access(db,user,payload.launch_id)
    if not order or not launch:raise HTTPException(404,'Commande ou lancement absent')
    if (launch.order_ref and launch.order_ref!=order.reference) or norm(launch.client_name)!=norm(db.get(Partner,order.client_id).name):raise HTTPException(409,'Référence ou client du lancement incompatible')
    if db.get(BusinessOrderLaunch,launch.id):raise HTTPException(409,'Lancement déjà rattaché')
    references=list(db.scalars(select(PartnerRequest.order_ref).where(PartnerRequest.launch_id==launch.id)))+list(db.scalars(select(PartnerOrderLine.order_ref).where(PartnerOrderLine.launch_id==launch.id)))
    if any(ref!=order.reference for ref in references):raise HTTPException(409,'Échanges fournisseurs historiques incompatibles : rapprochement manuel requis')
    clients=list(db.scalars(select(PartnerClientOrder.partner_id).where(PartnerClientOrder.launch_id==launch.id)))
    if any(cid!=order.client_id for cid in clients):raise HTTPException(409,'Accès client historique incompatible')
    db.add(BusinessOrderLaunch(launch_id=launch.id,order_id=oid,linked_by=user.id))
    db.flush();adopt_launch(db,launch.id,oid)
    audit(db,user,'order.launch.link','order',oid,{'launch_id':launch.id})
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Rattachement concurrent : actualiser')
    return out(db,order,user)

@router.get('/api/orders/{oid}')
def detail(oid:str,summary:bool=False,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,"launch.read")
    row=must_order(db,user,oid)
    if not row:raise HTTPException(404,'Commande absente')
    result=out(db,row,user)
    if summary:return result
    ids=[l['id'] for l in result['launches']]
    result['documents']=[{'id':d.id,'title':d.title,'folder':d.folder.slug,'launch_id':d.launch_id,'versions':[{'id':v.id,'number':v.number,'sha256':v.sha256} for v in d.versions]} for d in db.scalars(select(Document).join(Folder).where(Folder.dossier_id==db.scalar(select(OrderDossier.id).where(OrderDossier.order_id==oid)))) if permitted(user,'document.read',d.folder.slug) and document_accessible(db,user,d)]
    result['supplier_requests']=[{'id':r.id,'partner_id':r.partner_id,'title':r.title,'status':r.status} for r in db.scalars(select(PartnerRequest).where(PartnerRequest.launch_id.in_(ids)))] if permitted(user,'supplier.read') and permitted(user,'document.read','jaune') else []
    from .partner_delivery_routes import output
    result['supplier_materials']=[output(db,l) for l in db.scalars(select(PartnerOrderLine).where(PartnerOrderLine.launch_id.in_(ids)))] if permitted(user,'receipt.read') and all(permitted(user,'document.read',f) for f in ('jaune','rose')) else []
    from .material_routes import output_line, material_line_accessible
    result['internal_materials']=[output_line(l,db) for l in db.scalars(select(MaterialLine).where(MaterialLine.launch_id.in_(ids))) if material_line_accessible(db,user,l)] if all(permitted(user,'document.read',f) for f in ('jaune','rose')) else []
    result['publications']=[{'id':p.id,'version_id':p.document_version_id,'status':p.status} for p in db.scalars(select(ClientPublication).where(ClientPublication.launch_id.in_(ids))) if (v:=db.get(DocumentVersion,p.document_version_id)) and document_accessible(db,user,v.document) and permitted(user,'document.read',v.document.folder.slug)]
    result['orli_links']=[{'launch_id':l.launch_id,'record_id':l.record_id,'reference':l.source_ref} for l in db.scalars(select(OrliLink).where(OrliLink.launch_id.in_(ids)))]
    return result

class UnlinkInput(BaseModel):
    reason:str=Field(min_length=3,max_length=1500)

@router.delete('/api/orders/{oid}/launches/{lid}')
def unlink(oid:str,lid:str,payload:UnlinkInput,user=Depends(staff),db:Session=Depends(get_db)):
    must_order(db,user,oid);must_access(db,user,lid)
    relation=db.get(BusinessOrderLaunch,lid)
    if not relation or relation.order_id!=oid:raise HTTPException(404,'Rattachement absent')
    if db.scalar(select(Document.id).where(Document.launch_id==lid).limit(1)):
        raise HTTPException(409,'Ce lancement porte des documents : détachement interdit, migration explicite requise')
    db.delete(relation);audit(db,user,'order.launch.unlink','order',oid,{'launch_id':lid,'reason':payload.reason});db.commit()
    return {'unlinked':True,'documents_preserved':True}
