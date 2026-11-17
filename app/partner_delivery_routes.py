"""Supplier declarations and employee confirmations are independent journal entries."""
from datetime import date
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .core import get_db
from .audit import audit
from .models import Launch
from .partner_models import PartnerOrderLine, PartnerDelivery, PartnerSubmission, PartnerRequest
from .partner_routes import staff, partner, org_get, receipt_reader, receipt_writer, supplier_writer
from .access import must, must_access

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
    if not row or (account and (row.partner_id!=account.partner_id or org_get(db,account.partner_id).kind!='supplier')):
        raise HTTPException(404,'Ligne introuvable')
    return row


def discrepancy_history(row,movements,cancellations):
    """Incremental immutable balances; O(n log n), including cancelled plans."""
    import heapq
    events=[(m.created_at.replace(tzinfo=None),0,m.id,m,None) for m in movements]
    events += [(c.created_at.replace(tzinfo=None),1,m.id,m,c) for m in movements if (c:=cancellations.get(m.id))]
    totals={};active=set();plans=[];result=[];sequence=0
    for timestamp,kind,mid,movement,cancellation in sorted(events,key=lambda event:event[:3]):
        if kind:
            if mid in active:
                active.remove(mid);totals[movement.kind]-=movement.quantity
        else:
            active.add(mid);totals[movement.kind]=totals.get(movement.kind,Decimal('0'))+movement.quantity
            sequence+=1
            if movement.kind=='planned':heapq.heappush(plans,(-sequence,mid,movement.quantity))
        while plans and plans[0][1] not in active:heapq.heappop(plans)
        planned=plans[0][2] if plans else None
        received=totals.get('received',Decimal('0'))-totals.get('returned',Decimal('0'))
        declared=totals.get('declared',Decimal('0'))
        fmt=lambda value:format(value,'.3f') if value is not None else None
        result.append({'date':timestamp,'movement_id':mid,'operation':'cancelled' if kind else movement.kind,
            'source_id':movement.source_id,'reason':cancellation.reason if cancellation else movement.note,
            'ordered':fmt(row.ordered),'planned':fmt(planned),'declared':fmt(declared),'received':fmt(received),
            'ordered_minus_planned':fmt(row.ordered-planned) if planned is not None else None,
            'declared_minus_received':fmt(declared-received),'received_minus_ordered':fmt(received-row.ordered),
            'remaining':fmt(max(Decimal('0'),row.ordered-received))})
    return result


def receipt_scope(db,user,row,write=False):
    must_access(db,user,row.launch_id);must(user,'launch.read')
    must(user,'receipt.write' if write else 'receipt.read')
    must(user,'document.read','jaune');must(user,'document.read','rose')
    return row


def summary_values(row,total,planned):
    received=total('received')-total('returned')
    result={'id':row.id,'partner_id':row.partner_id,'order_ref':row.order_ref,'material_ref':row.material_ref,
            'unit':row.unit,'ordered':format(row.ordered,'.3f'),'declared':format(total('declared'),'.3f'),'received':format(received,'.3f'),
            'planned':format(planned,'.3f') if planned is not None else None,'announced':format(total('announced'),'.3f'),'returned':format(total('returned'),'.3f'),
            'remaining':format(max(Decimal('0'),row.ordered-received),'.3f'), 'expected_date':row.expected_date,
            'status':'excess' if received>row.ordered else 'complete' if received==row.ordered else 'partial' if received else 'awaiting',
            'assessment':'quantity_difference' if received>row.ordered else 'awaiting_reconciliation' if row.expected_date and row.expected_date<date.today() and received<row.ordered else 'normal_progress',
            'assessment_notice':'Écart quantitatif indicatif ; la règle de tolérance et la date doivent être validées. Une réception partielle ne constitue pas en elle-même une anomalie.'}
    return result


def output(db,row,include_history=True,include_context=True):
    movements=list(db.scalars(select(PartnerDelivery).where(PartnerDelivery.line_id==row.id).order_by(PartnerDelivery.created_at,PartnerDelivery.id)))
    from .partner_phase2_models import PartnerMovementCancellation, BusinessOrderLaunch
    cancellations={c.movement_id:c for c in db.scalars(select(PartnerMovementCancellation).where(PartnerMovementCancellation.movement_id.in_([m.id for m in movements])))} if movements else {}
    total=lambda kind:sum((m.quantity for m in movements if m.kind==kind and m.id not in cancellations),Decimal('0'))
    plans=[m for m in movements if m.kind=='planned' and m.id not in cancellations]
    result=summary_values(row,total,plans[-1].quantity if plans else None)
    if include_context:
        link=db.get(BusinessOrderLaunch,row.launch_id)
        result.update(launch_id=row.launch_id,order_id=link.order_id if link else None)
    if include_history:
        result['discrepancy_history']=discrepancy_history(row,movements,cancellations)
        result['movements']=[{'id':m.id,'kind':m.kind,'quantity':str(m.quantity),'source_id':m.source_id,
                          'cancelled':m.id in cancellations,'cancellation_reason':cancellations[m.id].reason if m.id in cancellations else None,'note':m.note,'occurred_on':m.occurred_on,'created_at':m.created_at} for m in movements]
    return result


def summaries(db,rows):
    """Fixed SQL budget for a receipt page; histories stay on their own endpoint."""
    from .partner_phase2_models import PartnerMovementCancellation, BusinessOrderLaunch
    if not rows:return []
    ids=[r.id for r in rows];totals={r.id:{} for r in rows}
    active=select(PartnerDelivery.line_id,PartnerDelivery.kind,PartnerDelivery.quantity,PartnerDelivery.created_at,PartnerDelivery.id).outerjoin(PartnerMovementCancellation,PartnerMovementCancellation.movement_id==PartnerDelivery.id).where(PartnerDelivery.line_id.in_(ids),PartnerMovementCancellation.movement_id.is_(None)).subquery()
    for lid,kind,quantity in db.execute(select(active.c.line_id,active.c.kind,func.sum(active.c.quantity)).group_by(active.c.line_id,active.c.kind)):
        totals[lid][kind]=quantity
    plans_query=select(active.c.line_id,active.c.quantity,func.row_number().over(partition_by=active.c.line_id,order_by=(active.c.created_at.desc(),active.c.id.desc())).label('rank')).where(active.c.kind=='planned').subquery()
    plans=dict(db.execute(select(plans_query.c.line_id,plans_query.c.quantity).where(plans_query.c.rank==1)).all())
    links=dict(db.execute(select(BusinessOrderLaunch.launch_id,BusinessOrderLaunch.order_id).where(BusinessOrderLaunch.launch_id.in_({r.launch_id for r in rows}))).all())
    return [{**summary_values(row,lambda kind:totals[row.id].get(kind,Decimal('0')),plans.get(row.id)),
             'launch_id':row.launch_id,'order_id':links.get(row.launch_id)} for row in rows]


@router.post('/api/partners/order-lines',status_code=201)
def create_line(payload:LineInput,user=Depends(supplier_writer),db:Session=Depends(get_db)):
    org=org_get(db,payload.partner_id,'supplier')
    if not org.active or not db.get(Launch,payload.launch_id):raise HTTPException(422,'Fournisseur inactif ou lancement absent')
    must_access(db,user,payload.launch_id);must(user,'launch.read');must(user,'document.read','jaune');must(user,'document.read','rose')
    from .order_registry_routes import check_order_scope
    check_order_scope(db,payload.launch_id,reference=payload.order_ref)
    row=PartnerOrderLine(**payload.model_dump(),created_by=user.id);db.add(row)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Matière déjà liée à cette commande fournisseur')
    audit(db,user,'partner.order','partner_order_line',row.id);db.commit();return output(db,row)

@router.get('/api/partners/order-lines')
def staff_lines(user=Depends(receipt_reader),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    from .access import launch_access_clause
    must(user,'launch.read');must(user,'document.read','jaune');must(user,'document.read','rose')
    return summaries(db,list(db.scalars(select(PartnerOrderLine).where(launch_access_clause(user,PartnerOrderLine.launch_id)).order_by(PartnerOrderLine.order_ref,PartnerOrderLine.material_ref,PartnerOrderLine.id).offset(offset).limit(limit))))

@router.get('/api/partner/order-lines')
def supplier_lines(account=Depends(partner),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    if org_get(db,account.partner_id).kind!='supplier':return []
    return [output(db,r,include_context=False) for r in db.scalars(select(PartnerOrderLine).where(PartnerOrderLine.partner_id==account.partner_id).order_by(PartnerOrderLine.order_ref,PartnerOrderLine.material_ref,PartnerOrderLine.id).offset(offset).limit(limit))]

def record(db,row,payload,kind,actor,user=None):
    existing=db.scalar(select(PartnerDelivery).where(PartnerDelivery.line_id==row.id,PartnerDelivery.operation_key==payload.operation_key))
    if existing:
        if (existing.kind,existing.quantity,existing.source_id,existing.note,existing.occurred_on,existing.actor)!=(kind,payload.quantity,payload.source_id,payload.note,payload.occurred_on,actor):
            raise HTTPException(409,'Clé déjà utilisée pour une autre opération')
        return output(db,row,include_context=not actor.startswith('partner:'))
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
    db.commit();return output(db,row,include_context=not actor.startswith('partner:'))

@router.post('/api/partner/order-lines/{lid}/declarations',status_code=201)
def declare(lid:str,payload:MovementInput,account=Depends(partner),db:Session=Depends(get_db)):
    from .partner_permissions import require
    require(db,account,'delivery.write')
    return record(db,get_line(db,lid,account),payload,'declared','partner:'+account.id)

@router.post('/api/partners/order-lines/{lid}/receipts',status_code=201)
def receive(lid:str,payload:ConfirmationInput,user=Depends(receipt_writer),db:Session=Depends(get_db)):
    return record(db,receipt_scope(db,user,get_line(db,lid),write=True),payload,payload.kind,'staff:'+user.id,user)


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
    audit(db,user,'partner.delivery.cancel','partner_delivery',mid,{'actor':actor,'reason':payload.reason});db.commit();return output(db,line,include_context=not actor.startswith('partner:'))

@router.post('/api/partner/order-lines/{lid}/movements/{mid}/cancel')
def supplier_cancel(lid:str,mid:str,payload:CancellationInput,account=Depends(partner),db:Session=Depends(get_db)):
    from .partner_permissions import require
    require(db,account,'delivery.write');return cancel(db,lid,mid,payload,'partner:'+account.id,account=account)

@router.post('/api/partners/order-lines/{lid}/movements/{mid}/cancel')
def staff_cancel(lid:str,mid:str,payload:CancellationInput,user=Depends(receipt_writer),db:Session=Depends(get_db)):
    receipt_scope(db,user,get_line(db,lid),write=True)
    return cancel(db,lid,mid,payload,'staff:'+user.id,user=user)

@router.get('/api/partners/order-lines/{lid}/history')
def staff_history(lid:str,user=Depends(receipt_reader),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    row=receipt_scope(db,user,get_line(db,lid))
    history=output(db,row)['discrepancy_history']
    return {'total':len(history),'offset':offset,'limit':limit,'items':history[offset:offset+limit]}

@router.get('/api/partners/order-lines/{lid}')
def staff_line_detail(lid:str,user=Depends(receipt_reader),db:Session=Depends(get_db)):
    return output(db,receipt_scope(db,user,get_line(db,lid)))
