"""Explicit client order grants and conversations; no internal dossier projection."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_db
from .models import Launch
from .main import audit
from .partner_routes import staff, partner, org_get, MessageInput
from .partner_permissions import require
from .partner_phase2_models import PartnerClientOrder, PartnerThread, PartnerMessage
from .sharing_routes import norm

router=APIRouter(tags=['Commandes et clarifications client'])
class OrderInput(BaseModel):
    partner_id: str
    launch_id: str
    reference: str=Field(min_length=1,max_length=100)
    status: Literal['Non renseigné','Confirmée','En préparation','En fabrication','Expédiée','Terminée']='Non renseigné'
    confirmed_due: date | None=None
    active: bool=True
class ThreadInput(BaseModel):
    title: str=Field(min_length=3,max_length=200)
    message: str=Field(min_length=1,max_length=4000)
class StatusInput(BaseModel):
    status: Literal['open','waiting_client','closed']
    reason: str=Field(min_length=3,max_length=4000)

def order_get(db,oid,account=None):
    row=db.get(PartnerClientOrder,oid)
    if not row:raise HTTPException(404,'Commande introuvable')
    if account:
        org=org_get(db,account.partner_id,'client');launch=db.get(Launch,row.launch_id)
        if row.partner_id!=account.partner_id or not row.active or not launch or norm(launch.client_name)!=norm(org.name):raise HTTPException(404,'Commande introuvable')
    return row

def order_out(row):
    return {'id':row.id,'reference':row.reference,'status':row.status,'confirmed_due':row.confirmed_due,'progress_percent':None,'active':row.active}

def thread_get(db,tid,account=None):
    row=db.get(PartnerThread,tid)
    if not row:raise HTTPException(404,'Échange introuvable')
    order_get(db,row.order_id,account);return row

def thread_out(db,row):
    from .partner_phase2_models import PartnerAttachment
    from .partner_attachment_routes import out
    attached=[out(a) for a in db.scalars(select(PartnerAttachment).join(PartnerMessage).where(PartnerMessage.thread_id==row.id))]
    return {'attachments':attached,'id':row.id,'title':row.title,'status':row.status,'created_at':row.created_at,
            'messages':[{'id':m.id,'author':'Framatex' if m.author.startswith('staff:') else 'Client','message':m.text,'created_at':m.created_at}
                for m in db.scalars(select(PartnerMessage).where(PartnerMessage.thread_id==row.id).order_by(PartnerMessage.created_at,PartnerMessage.id))]}

@router.post('/api/partners/client-orders',status_code=201)
def create_order(payload:OrderInput,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,payload.partner_id,'client');launch=db.get(Launch,payload.launch_id)
    if not launch or not org.active or norm(launch.client_name)!=norm(org.name):raise HTTPException(409,'Client du lancement incompatible')
    row=PartnerClientOrder(**payload.model_dump());db.add(row)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Commande déjà autorisée')
    audit(db,user,'client.order.grant','partner_client_order',row.id,payload.model_dump(mode='json'));db.commit();return order_out(row)

@router.put('/api/partners/client-orders/{oid}')
def update_order(oid:str,payload:OrderInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=order_get(db,oid)
    if (row.partner_id,row.launch_id)!=(payload.partner_id,payload.launch_id):raise HTTPException(409,'Destinataire et lancement immuables')
    for k,v in payload.model_dump().items():setattr(row,k,v)
    audit(db,user,'client.order.update','partner_client_order',row.id,payload.model_dump(mode='json'));db.commit();return order_out(row)

@router.get('/api/partners/client-orders')
def staff_orders(user=Depends(staff),db:Session=Depends(get_db)):
    return [{**order_out(r),'partner_id':r.partner_id,'launch_id':r.launch_id} for r in db.scalars(select(PartnerClientOrder).order_by(PartnerClientOrder.reference))]

@router.get('/api/partner/client-orders')
def client_orders(account=Depends(partner),db:Session=Depends(get_db)):
    if org_get(db,account.partner_id).kind!='client':return []
    result=[]
    for row in db.scalars(select(PartnerClientOrder).where(PartnerClientOrder.partner_id==account.partner_id,PartnerClientOrder.active.is_(True)).order_by(PartnerClientOrder.reference)):
        try:order_get(db,row.id,account)
        except HTTPException:continue
        result.append(order_out(row))
    return result

@router.get('/api/partner/client-orders/{oid}/threads')
def client_threads(oid:str,account=Depends(partner),db:Session=Depends(get_db)):
    order_get(db,oid,account)
    return [thread_out(db,r) for r in db.scalars(select(PartnerThread).where(PartnerThread.order_id==oid).order_by(PartnerThread.created_at))]

@router.get('/api/partners/client-orders/{oid}/threads')
def staff_threads(oid:str,user=Depends(staff),db:Session=Depends(get_db)):
    order_get(db,oid)
    return [thread_out(db,r) for r in db.scalars(select(PartnerThread).where(PartnerThread.order_id==oid).order_by(PartnerThread.created_at))]

@router.post('/api/partner/client-orders/{oid}/threads',status_code=201)
def create_thread(oid:str,payload:ThreadInput,account=Depends(partner),db:Session=Depends(get_db)):
    require(db,account,'message.write');order_get(db,oid,account)
    row=PartnerThread(order_id=oid,title=payload.title);db.add(row);db.flush()
    db.add(PartnerMessage(thread_id=row.id,author='partner:'+account.id,text=payload.message))
    audit(db,None,'client.thread.create','partner_thread',row.id,{'account_id':account.id});db.commit();return thread_out(db,row)

@router.post('/api/partner/threads/{tid}/messages',status_code=201)
def client_message(tid:str,payload:MessageInput,account=Depends(partner),db:Session=Depends(get_db)):
    require(db,account,'message.write');row=thread_get(db,tid,account)
    if row.status=='closed':raise HTTPException(409,'Échange clôturé')
    db.add(PartnerMessage(thread_id=tid,author='partner:'+account.id,text=payload.message));row.status='open'
    db.commit();return thread_out(db,row)

@router.post('/api/partners/threads/{tid}/messages',status_code=201)
def staff_message(tid:str,payload:MessageInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=thread_get(db,tid)
    if row.status=='closed':raise HTTPException(409,'Échange clôturé')
    db.add(PartnerMessage(thread_id=tid,author='staff:'+user.id,text=payload.message));db.commit();return thread_out(db,row)

@router.post('/api/partners/threads/{tid}/status')
def thread_status(tid:str,payload:StatusInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=thread_get(db,tid);row.status=payload.status
    db.add(PartnerMessage(thread_id=tid,author='staff:'+user.id,text=f'{payload.status} : {payload.reason}'))
    audit(db,user,'client.thread.status','partner_thread',tid,payload.model_dump());db.commit();return thread_out(db,row)

@router.get('/api/partners/launch-options')
def launch_options(user=Depends(staff),db:Session=Depends(get_db)):
    return [{'id':l.id,'label':f'{l.order_ref or l.name} · {l.client_name or "Client non renseigné"}'} for l in db.scalars(select(Launch).order_by(Launch.created_at.desc()))]

@router.get('/api/partners/publication-options')
def publication_options(user=Depends(staff),db:Session=Depends(get_db)):
    from .sharing_models import ClientPublication
    from .sharing_routes import pub_out
    result=[]
    for p in db.scalars(select(ClientPublication).where(ClientPublication.status=='published')):
        data=pub_out(db,p,db.get(Launch,p.launch_id))
        if data['effective']:result.append({'id':p.id,'label':f'{data["client_name"]} · {data["document_title"]} · v{data["version"]}'})
    return result
