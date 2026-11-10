"""Supplier declarations and employee confirmations are independent journal entries."""
from datetime import date
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .core import get_db
from .main import audit
from .models import Launch
from .partner_models import PartnerOrderLine, PartnerDelivery, PartnerSubmission, PartnerRequest
from .partner_routes import staff, partner, org_get

router=APIRouter(tags=['Livraisons partenaires'])
Quantity=Field(gt=0, max_digits=15, decimal_places=3)

class LineInput(BaseModel):
    partner_id: str
    launch_id: str
    order_ref: str=Field(min_length=1,max_length=100)
    material_ref: str=Field(min_length=1,max_length=100)
    unit: str=Field(min_length=1,max_length=20)
    ordered: Decimal=Quantity
    expected_date: date | None=None

class MovementInput(BaseModel):
    operation_key: str=Field(min_length=8,max_length=80)
    quantity: Decimal=Quantity
    source_id: str
    note: str=Field(min_length=3,max_length=2000)
    occurred_on: date

class ConfirmationInput(MovementInput):
    kind: Literal['received','returned']

def get_line(db, lid, account=None):
    row=db.get(PartnerOrderLine,lid)
    if not row or (account and row.partner_id!=account.partner_id):
        raise HTTPException(404,'Ligne introuvable')
    return row

def output(db,row):
    movements=db.scalars(select(PartnerDelivery).where(PartnerDelivery.line_id==row.id).order_by(PartnerDelivery.created_at,PartnerDelivery.id)).all()
    total=lambda kind:sum((m.quantity for m in movements if m.kind==kind),Decimal('0'))
    received=total('received')-total('returned')
    return {'id':row.id,'partner_id':row.partner_id,'order_ref':row.order_ref,'material_ref':row.material_ref,
            'unit':row.unit,'ordered':format(row.ordered,'.3f'),'declared':format(total('declared'),'.3f'),'received':format(received,'.3f'),
            'remaining':format(max(Decimal('0'),row.ordered-received),'.3f'), 'expected_date':row.expected_date,
            'status':'excess' if received>row.ordered else 'complete' if received==row.ordered else 'partial' if received else 'awaiting',
            'movements':[{'id':m.id,'kind':m.kind,'quantity':str(m.quantity),'source_id':m.source_id,
                          'note':m.note,'occurred_on':m.occurred_on,'created_at':m.created_at} for m in movements]}

@router.post('/api/partners/order-lines',status_code=201)
def create_line(payload:LineInput,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,payload.partner_id,'supplier')
    if not org.active or not db.get(Launch,payload.launch_id):raise HTTPException(422,'Fournisseur inactif ou lancement absent')
    row=PartnerOrderLine(**payload.model_dump(),created_by=user.id);db.add(row)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Matière déjà liée à cette commande fournisseur')
    audit(db,user,'partner.order','partner_order_line',row.id);db.commit();return output(db,row)

@router.get('/api/partners/order-lines')
def staff_lines(user=Depends(staff),db:Session=Depends(get_db)):
    return [output(db,r) for r in db.scalars(select(PartnerOrderLine).order_by(PartnerOrderLine.order_ref,PartnerOrderLine.material_ref))]

@router.get('/api/partner/order-lines')
def supplier_lines(account=Depends(partner),db:Session=Depends(get_db)):
    return [output(db,r) for r in db.scalars(select(PartnerOrderLine).where(PartnerOrderLine.partner_id==account.partner_id).order_by(PartnerOrderLine.order_ref,PartnerOrderLine.material_ref))]

def record(db,row,payload,kind,actor,user=None):
    existing=db.scalar(select(PartnerDelivery).where(PartnerDelivery.line_id==row.id,PartnerDelivery.operation_key==payload.operation_key))
    if existing:
        if (existing.kind,existing.quantity,existing.source_id,existing.note,existing.occurred_on,existing.actor)!=(kind,payload.quantity,payload.source_id,payload.note,payload.occurred_on,actor):
            raise HTTPException(409,'Clé déjà utilisée pour une autre opération')
        return output(db,row)
    source=db.get(PartnerSubmission,payload.source_id)
    request=db.get(PartnerRequest,source.request_id) if source else None
    if not request or request.partner_id!=row.partner_id or request.order_ref!=row.order_ref or request.launch_id!=row.launch_id:
        raise HTTPException(422,'Justificatif étranger à cette commande')
    if kind!='declared' and source.status!='approved':
        raise HTTPException(409,'Justificatif approuvé requis pour une réception ou un retour')
    changed=db.execute(update(PartnerOrderLine).where(PartnerOrderLine.id==row.id,PartnerOrderLine.revision==row.revision).values(revision=row.revision+1),execution_options={'synchronize_session':False})
    if changed.rowcount!=1:raise HTTPException(409,'Ligne modifiée : actualiser')
    if kind=='returned' and payload.quantity>Decimal(output(db,row)['received']):
        raise HTTPException(409,'Retour supérieur à la quantité réceptionnée nette')
    movement=PartnerDelivery(line_id=row.id,**payload.model_dump(exclude={'kind'}),kind=kind,actor=actor)
    db.add(movement)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Opération concurrente : actualiser')
    audit(db,user,'partner.delivery.'+kind,'partner_delivery',movement.id,{'actor':actor})
    db.commit();return output(db,row)

@router.post('/api/partner/order-lines/{lid}/declarations',status_code=201)
def declare(lid:str,payload:MovementInput,account=Depends(partner),db:Session=Depends(get_db)):
    return record(db,get_line(db,lid,account),payload,'declared','partner:'+account.id)

@router.post('/api/partners/order-lines/{lid}/receipts',status_code=201)
def receive(lid:str,payload:ConfirmationInput,user=Depends(staff),db:Session=Depends(get_db)):
    return record(db,get_line(db,lid),payload,payload.kind,'staff:'+user.id,user)
