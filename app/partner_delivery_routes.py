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
    kind: Literal['received','returned','planned']

def get_line(db, lid, account=None):
    row=db.get(PartnerOrderLine,lid)
    if not row or (account and row.partner_id!=account.partner_id):
        raise HTTPException(404,'Ligne introuvable')
    return row


def discrepancy_history(row,movements,cancellations):
    """Reconstruct each historical balance from immutable movements and cancellations."""
    events=[(m.created_at.replace(tzinfo=None),0,m.id,m,None) for m in movements]
    events += [(c.created_at.replace(tzinfo=None),1,m.id,m,c) for m in movements if (c:=cancellations[m.id])]
    active={};result=[]
    for timestamp,kind,mid,movement,cancellation in sorted(events,key=lambda event:event[:3]):
        if kind:active.pop(mid,None)
        else:active[mid]=movement
        total=lambda name:sum((m.quantity for m in active.values() if m.kind==name),Decimal('0'))
        plans=[m for m in active.values() if m.kind=='planned']
        planned=plans[-1].quantity if plans else None
        received=total('received')-total('returned');declared=total('declared')
        fmt=lambda value:format(value,'.3f') if value is not None else None
        result.append({'date':timestamp,'movement_id':mid,'operation':'cancelled' if kind else movement.kind,
            'source_id':movement.source_id,'reason':cancellation.reason if cancellation else movement.note,
            'ordered':fmt(row.ordered),'planned':fmt(planned),'declared':fmt(declared),'received':fmt(received),
            'ordered_minus_planned':fmt(row.ordered-planned) if planned is not None else None,
            'declared_minus_received':fmt(declared-received),'received_minus_ordered':fmt(received-row.ordered),
            'remaining':fmt(max(Decimal('0'),row.ordered-received))})
    return result

def output(db,row):
    movements=db.scalars(select(PartnerDelivery).where(PartnerDelivery.line_id==row.id).order_by(PartnerDelivery.created_at,PartnerDelivery.id)).all()
    from .partner_phase2_models import PartnerMovementCancellation
    cancellations={m.id:db.get(PartnerMovementCancellation,m.id) for m in movements}
    total=lambda kind:sum((m.quantity for m in movements if m.kind==kind and not cancellations[m.id]),Decimal('0'))
    plans=[m for m in movements if m.kind=='planned' and not cancellations[m.id]]
    received=total('received')-total('returned')
    return {'id':row.id,'partner_id':row.partner_id,'order_ref':row.order_ref,'material_ref':row.material_ref,
            'unit':row.unit,'ordered':format(row.ordered,'.3f'),'declared':format(total('declared'),'.3f'),'received':format(received,'.3f'),
            'planned':format(plans[-1].quantity,'.3f') if plans else None,'announced':format(total('announced'),'.3f'),'returned':format(total('returned'),'.3f'),
            'remaining':format(max(Decimal('0'),row.ordered-received),'.3f'), 'expected_date':row.expected_date,
            'status':'excess' if received>row.ordered else 'complete' if received==row.ordered else 'partial' if received else 'awaiting',
            'discrepancy_history':discrepancy_history(row,movements,cancellations),
            'movements':[{'id':m.id,'kind':m.kind,'quantity':str(m.quantity),'source_id':m.source_id,
                          'cancelled':bool(cancellations[m.id]),'cancellation_reason':cancellations[m.id].reason if cancellations[m.id] else None,'note':m.note,'occurred_on':m.occurred_on,'created_at':m.created_at} for m in movements]}

@router.post('/api/partners/order-lines',status_code=201)
def create_line(payload:LineInput,user=Depends(staff),db:Session=Depends(get_db)):
    org=org_get(db,payload.partner_id,'supplier')
    if not org.active or not db.get(Launch,payload.launch_id):raise HTTPException(422,'Fournisseur inactif ou lancement absent')
    from .order_registry_routes import check_order_scope
    check_order_scope(db,payload.launch_id,reference=payload.order_ref)
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
    from .partner_phase2_models import PartnerIntegration
    integrated=db.get(PartnerIntegration,source.id)
    if integrated and not integrated.active:raise HTTPException(409,'Justificatif retiré')
    if kind not in ('declared','announced') and source.status!='approved':
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
    from .partner_permissions import require
    require(db,account,'delivery.write')
    return record(db,get_line(db,lid,account),payload,'declared','partner:'+account.id)

@router.post('/api/partners/order-lines/{lid}/receipts',status_code=201)
def receive(lid:str,payload:ConfirmationInput,user=Depends(staff),db:Session=Depends(get_db)):
    return record(db,get_line(db,lid),payload,payload.kind,'staff:'+user.id,user)


@router.post('/api/partner/order-lines/{lid}/announcements',status_code=201)
def announce(lid:str,payload:MovementInput,account=Depends(partner),db:Session=Depends(get_db)):
    from .partner_permissions import require
    require(db,account,'delivery.write')
    return record(db,get_line(db,lid,account),payload,'announced','partner:'+account.id)

class CancellationInput(BaseModel):
    reason:str=Field(min_length=3,max_length=2000)

def cancel(db,lid,mid,payload,actor,account=None,user=None):
    from .partner_phase2_models import PartnerMovementCancellation
    line=get_line(db,lid,account);movement=db.get(PartnerDelivery,mid)
    if not movement or movement.line_id!=lid or (account and (movement.actor!=actor or movement.kind not in ('declared','announced'))):raise HTTPException(404,'Mouvement introuvable')
    changed=db.execute(update(PartnerOrderLine).where(PartnerOrderLine.id==lid,PartnerOrderLine.revision==line.revision).values(revision=line.revision+1),execution_options={'synchronize_session':False})
    if changed.rowcount!=1:raise HTTPException(409,'Ligne modifiée : actualiser')
    if db.get(PartnerMovementCancellation,mid):raise HTTPException(409,'Mouvement déjà annulé')
    if movement.kind=='received' and Decimal(output(db,line)['received'])<movement.quantity:raise HTTPException(409,'Annuler les retours associés avant cette réception')
    db.add(PartnerMovementCancellation(movement_id=mid,actor=actor,reason=payload.reason))
    audit(db,user,'partner.delivery.cancel','partner_delivery',mid,{'actor':actor,'reason':payload.reason});db.commit();return output(db,line)

@router.post('/api/partner/order-lines/{lid}/movements/{mid}/cancel')
def supplier_cancel(lid:str,mid:str,payload:CancellationInput,account=Depends(partner),db:Session=Depends(get_db)):
    from .partner_permissions import require
    require(db,account,'delivery.write');return cancel(db,lid,mid,payload,'partner:'+account.id,account=account)

@router.post('/api/partners/order-lines/{lid}/movements/{mid}/cancel')
def staff_cancel(lid:str,mid:str,payload:CancellationInput,user=Depends(staff),db:Session=Depends(get_db)):
    return cancel(db,lid,mid,payload,'staff:'+user.id,user=user)
