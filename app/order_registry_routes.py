"""Additive order registry. Explicit links preserve all original launch data and ACLs."""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_db, get_current_user
from .main import audit
from .models import Launch,Document,Folder
from .order_documents import dossier, adopt_launch, must_order, order_accessible, OrderDossier
from .access import must_access
from .main import permitted, must
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

def out(db,row):
    return {'id':row.id,'reference':row.reference,'client_id':row.client_id,'client_name':db.get(Partner,row.client_id).name,'created_at':row.created_at,
        'launches':[{'id':l.id,'name':l.name,'order_ref':l.order_ref,'orli_ref':l.orli_ref,'status':l.status} for l in db.scalars(select(Launch).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id==row.id))]}

@router.get('/api/orders')
def list_orders(user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,"launch.read")
    return [out(db,r) for r in db.scalars(select(BusinessOrder).order_by(BusinessOrder.created_at.desc())) if order_accessible(db,user,r.id)]

@router.post('/api/orders',status_code=201)
def create(payload:OrderInput,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,payload.client_id,'client')
    if not org.active or not payload.reference.strip():raise HTTPException(422,'Client actif et référence nécessaires')
    row=BusinessOrder(client_id=org.id,reference=payload.reference.strip(),created_by=user.id);db.add(row)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Commande déjà enregistrée')
    dossier(db,row.id)
    audit(db,user,'order.create','order',row.id,payload.model_dump());db.commit();return out(db,row)

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
    return out(db,order)

@router.get('/api/orders/{oid}')
def detail(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,"launch.read")
    row=must_order(db,user,oid)
    if not row:raise HTTPException(404,'Commande absente')
    result=out(db,row);ids=[l['id'] for l in result['launches']]
    result['documents']=[{'id':d.id,'title':d.title,'folder':d.folder.slug,'launch_id':d.launch_id,'versions':[{'id':v.id,'number':v.number,'sha256':v.sha256} for v in d.versions]} for d in db.scalars(select(Document).join(Folder).where(Folder.dossier_id==db.scalar(select(OrderDossier.id).where(OrderDossier.order_id==oid)))) if permitted(user,'document.read',d.folder.slug)]
    result['supplier_requests']=[{'id':r.id,'partner_id':r.partner_id,'title':r.title,'status':r.status} for r in db.scalars(select(PartnerRequest).where(PartnerRequest.launch_id.in_(ids)))]
    from .partner_delivery_routes import output
    result['supplier_materials']=[output(db,l) for l in db.scalars(select(PartnerOrderLine).where(PartnerOrderLine.launch_id.in_(ids)))]
    from .material_routes import output_line
    result['internal_materials']=[output_line(l,db) for l in db.scalars(select(MaterialLine).where(MaterialLine.launch_id.in_(ids)))]
    result['publications']=[{'id':p.id,'version_id':p.document_version_id,'status':p.status} for p in db.scalars(select(ClientPublication).where(ClientPublication.launch_id.in_(ids)))]
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
