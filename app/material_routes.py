"""MVP 0.12 — traçabilité des matières et rapprochement prévu/commandé/reçu.

Aucune synchronisation avec ORLI ; les saisies humaines sont historisées et
référencées à une version documentaire existante dans le même lancement.
"""
from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_current_user, get_db, utcnow
from .models import User, DocumentVersion, Document, Folder
from .material_models import MaterialLine, MaterialMovement, MaterialPlanRevision
from .main import audit, get_launch, must, permitted

router = APIRouter()
UNITS = {'m', 'm²', 'kg', 'g', 'pcs', 'L'}
LIMIT = Decimal('999999999999.999')


def qty_number(value):
    if not value.is_finite() or value < 0 or value > LIMIT or value.as_tuple().exponent < -3:
        raise ValueError('Quantité non négative, au plus 3 décimales, sans notation spéciale')
    return value


class QuantityPayload(BaseModel):
    quantity: Decimal
    source_version_id: str
    note: str = Field(min_length=12, max_length=1500)

    @field_validator('quantity')
    @classmethod
    def valid_quantity(cls, v): return qty_number(v)


class LinePayload(QuantityPayload):
    reference: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=2, max_length=180)
    unit: str

    @field_validator('unit')
    @classmethod
    def valid_unit(cls, v):
        if v not in UNITS: raise ValueError('Unité non reconnue')
        return v


class MovementPayload(QuantityPayload):
    kind: str
    counterparty: str | None = Field(default=None, max_length=140)
    reference: str | None = Field(default=None, max_length=100)

    @field_validator('kind')
    @classmethod
    def valid_kind(cls, v):
        if v not in {'ordered','received'}: raise ValueError('Nature inconnue')
        return v

    @field_validator('quantity')
    @classmethod
    def positive_quantity(cls,v):
        if v <= 0: raise ValueError('Un mouvement doit avoir une quantité strictement positive')
        return qty_number(v)


class CancelPayload(BaseModel):
    reason: str = Field(min_length=12, max_length=1500)


def safe_text(value: str) -> str:
    s=value.strip()
    if not s: raise HTTPException(422,'Une référence ou une justification ne peut être vide')
    return s


def evidence(db:Session, launch_id:str, version_id:str, required_folder:str, user:User):
    version=db.get(DocumentVersion,version_id)
    if version is None: raise HTTPException(422,'Version documentaire introuvable')
    doc=db.get(Document,version.document_id)
    folder=db.get(Folder,doc.folder_id)
    if folder.launch_id!=launch_id or folder.slug!=required_folder:
        raise HTTPException(422,'Justificatif hors du lancement ou du sous-dossier requis')
    must(user,'document.read',required_folder)
    must(user,'document.write',required_folder)
    return version


def require_report_access(user:User, writable=False):
    must(user,'launch.read')
    must(user,'document.read','jaune')
    must(user,'document.read','rose')
    if writable:
        must(user,'launch.update')


def material_line(db,launch_id,line_id):
    line=db.get(MaterialLine,line_id)
    if not line or line.launch_id!=launch_id: raise HTTPException(404,'Matière introuvable dans ce lancement')
    return line


def amount(n:Decimal)->str:
    return format(n.quantize(Decimal('0.001')), 'f')


def source_info(db:Session, version_id:str):
    version=db.get(DocumentVersion,version_id)
    if not version: return {'available':False,'version_id':version_id,'stale':True}
    document=db.get(Document,version.document_id)
    if not document: return {'available':False,'version_id':version_id,'stale':True}
    newest=db.scalar(select(DocumentVersion.number).where(DocumentVersion.document_id==document.id)
                     .order_by(DocumentVersion.number.desc()).limit(1))
    return {'available':True,'document_id':document.id,'version_id':version.id,'version_number':version.number,
            'document_title':document.title,'original_name':version.original_name,
            'stale':newest!=version.number}


def output_line(line:MaterialLine,db:Session):
    revisions=db.scalars(select(MaterialPlanRevision).where(MaterialPlanRevision.line_id==line.id)
                         .order_by(MaterialPlanRevision.recorded_at,MaterialPlanRevision.id)).all()
    latest=revisions[-1]
    movements=db.scalars(select(MaterialMovement).where(MaterialMovement.line_id==line.id)
                         .order_by(MaterialMovement.recorded_at,MaterialMovement.id)).all()
    ordered=sum((m.quantity for m in movements if m.kind=='ordered' and m.cancelled_at is None),Decimal(0))
    received=sum((m.quantity for m in movements if m.kind=='received' and m.cancelled_at is None),Decimal(0))
    planned=latest.quantity
    flags=[]
    if ordered>planned: flags.append('commande_supérieure_au_prévu')
    if received>ordered: flags.append('réception_supérieure_aux_commandes')
    if received and not ordered: flags.append('réception_sans_commande_enregistrée')
    if ordered<planned: flags.append('commande_partielle_ou_non_saisie')
    if received<ordered: flags.append('réception_partielle_ou_non_saisie')
    return {'id':line.id,'reference':line.reference,'label':line.label,'unit':line.unit,
            'planned':amount(planned),'ordered':amount(ordered),'received':amount(received),
            'to_order':amount(planned-ordered),'to_receive':amount(ordered-received),
            'flags':flags,
            'plan_history':[{'id':x.id,'quantity':amount(x.quantity), 'source_version_id':x.source_version_id,
                             'note':x.note,'recorded_at':x.recorded_at.isoformat(),'recorded_by':x.recorded_by,
                             'source':source_info(db,x.source_version_id)} for x in revisions],
            'movements':[{'id':x.id,'kind':x.kind,'quantity':amount(x.quantity),'source_version_id':x.source_version_id,
                          'counterparty':x.counterparty,'reference':x.reference,'note':x.note,
                          'recorded_at':x.recorded_at.isoformat(),'recorded_by':x.recorded_by,
                          'cancelled_at':x.cancelled_at.isoformat() if x.cancelled_at else None,
                          'cancellation_reason':x.cancellation_reason,'source':source_info(db,x.source_version_id)} for x in movements]}


@router.get('/api/launches/{launch_id}/materials')
def material_report(launch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    require_report_access(user)
    get_launch(db,launch_id)
    lines=db.scalars(select(MaterialLine).where(MaterialLine.launch_id==launch_id)
                     .order_by(MaterialLine.reference)).all()
    return {'launch_id':launch_id,'source':'saisies confirmées et versions documentaires — pas un stock ORLI',
            'lines':[output_line(line,db) for line in lines]}


@router.post('/api/launches/{launch_id}/materials',status_code=201)
def create_material(launch_id:str,payload:LinePayload,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    require_report_access(user,True)
    get_launch(db,launch_id)
    evidence(db,launch_id,payload.source_version_id,'jaune',user)
    reference=safe_text(payload.reference)
    label=safe_text(payload.label)
    existing=db.scalar(select(MaterialLine).where(MaterialLine.launch_id==launch_id,
                                                  MaterialLine.reference==reference))
    if existing: raise HTTPException(409,'Cette référence matière existe déjà dans ce lancement')
    line=MaterialLine(launch_id=launch_id,reference=reference,label=label,unit=payload.unit,created_by=user.id)
    db.add(line);db.flush()
    db.add(MaterialPlanRevision(line_id=line.id,quantity=payload.quantity,source_version_id=payload.source_version_id,
                                note=safe_text(payload.note),recorded_by=user.id))
    audit(db,user,'material.create','material',line.id,{'launch_id':launch_id,'unit':payload.unit,'source_version_id':payload.source_version_id})
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Référence matière déjà enregistrée')
    return output_line(line,db)


@router.post('/api/launches/{launch_id}/materials/{line_id}/plans',status_code=201)
def revise_plan(launch_id:str,line_id:str,payload:QuantityPayload,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    require_report_access(user,True)
    line=material_line(db,launch_id,line_id)
    evidence(db,launch_id,payload.source_version_id,'jaune',user)
    db.add(MaterialPlanRevision(line_id=line.id,quantity=payload.quantity,source_version_id=payload.source_version_id,
                                note=safe_text(payload.note),recorded_by=user.id))
    audit(db,user,'material.plan.revise','material',line.id,{'new_quantity':amount(payload.quantity),'source_version_id':payload.source_version_id})
    db.commit()
    return output_line(line,db)


@router.post('/api/launches/{launch_id}/materials/{line_id}/movements',status_code=201)
def add_movement(launch_id:str,line_id:str,payload:MovementPayload,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    require_report_access(user,True)
    line=material_line(db,launch_id,line_id)
    slug='jaune' if payload.kind=='ordered' else 'rose'
    evidence(db,launch_id,payload.source_version_id,slug,user)
    movement=MaterialMovement(line_id=line.id,kind=payload.kind,quantity=payload.quantity,
         source_version_id=payload.source_version_id,counterparty=(payload.counterparty or '').strip() or None,
         reference=(payload.reference or '').strip() or None,note=safe_text(payload.note),recorded_by=user.id)
    db.add(movement);db.flush()
    audit(db,user,'material.movement.record','material_movement',movement.id,
          {'line_id':line.id,'kind':payload.kind,'quantity':amount(payload.quantity),'source_version_id':payload.source_version_id})
    db.commit()
    return output_line(line,db)


@router.post('/api/launches/{launch_id}/materials/{line_id}/movements/{movement_id}/cancel')
def cancel_movement(launch_id:str,line_id:str,movement_id:str,payload:CancelPayload,
                    user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    require_report_access(user,True)
    line=material_line(db,launch_id,line_id)
    movement=db.get(MaterialMovement,movement_id)
    if movement is None or movement.line_id!=line.id: raise HTTPException(404,'Mouvement introuvable')
    folder='jaune' if movement.kind=='ordered' else 'rose'
    must(user,'document.write',folder)
    if movement.cancelled_at: raise HTTPException(409,'Mouvement déjà annulé')
    movement.cancelled_at=utcnow()
    movement.cancelled_by=user.id
    movement.cancellation_reason=safe_text(payload.reason)
    audit(db,user,'material.movement.cancel','material_movement',movement.id,
          {'line_id':line.id,'reason':movement.cancellation_reason})
    db.commit()
    return output_line(line,db)
