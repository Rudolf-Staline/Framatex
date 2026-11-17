"""Versioned optional identification, separated between canonical order and launches.

Adapted from feat/commande-identification (371c259); no launch/atelier is
invented for a shared order. Unknown historical JSON keys are retained.
"""
from datetime import date, datetime
from decimal import Decimal
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, update, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base, utcnow, get_db, get_current_user
from .models import uid, Launch
from .access import must, permitted, must_access
from .audit import audit
from .order_documents import must_order

router = APIRouter(tags=['Fiches identification'])
ORDER_FIELDS = [
    {'key':'program','label':'Programme / collection','type':'text','max_length':150},
    {'key':'article_ref','label':'Article / modèle','type':'text','max_length':150},
    {'key':'quantity','label':'Quantité commandée','type':'number','min':0,'step':'any'},
    {'key':'quantity_unit','label':'Unité de quantité','type':'text','max_length':30},
    {'key':'delivery_date','label':'Livraison prévue','type':'date'},
    {'key':'notes','label':'Observations','type':'textarea','max_length':2000},
]
LAUNCH_FIELDS = [
    {'key':'workshop','label':'Atelier du lancement','type':'text','max_length':150},
] + ORDER_FIELDS

class OrderIdentification(Base):
    __tablename__ = 'order_identifications'
    order_id: Mapped[str] = mapped_column(ForeignKey('business_orders.id'), primary_key=True)
    fields_json: Mapped[str] = mapped_column(Text, default='{}')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class LaunchIdentification(Base):
    __tablename__ = 'launch_identifications'
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), primary_key=True)
    fields_json: Mapped[str] = mapped_column(Text, default='{}')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class IdentificationValues(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    program: str | None = Field(None,max_length=150)
    article_ref: str | None = Field(None,max_length=150)
    quantity: Decimal | None = Field(None,ge=0,max_digits=18,decimal_places=6)
    quantity_unit: str | None = Field(None,max_length=30)
    delivery_date: date | None = None
    notes: str | None = Field(None,max_length=2000)

class LaunchIdentificationValues(IdentificationValues):
    workshop: str | None = Field(None,max_length=150)

class IdentificationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0)
    values: IdentificationValues

class LaunchIdentificationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0)
    values: LaunchIdentificationValues

@router.get('/api/order-fields')
def catalogue(user=Depends(get_current_user)):
    must(user,'launch.read')
    return {'order':ORDER_FIELDS,'launch':LAUNCH_FIELDS,'provisional':True,
            'notice':'Champs facultatifs ; obligations métier à valider par Framatex.'}

def identification_out(row, fields, canonical, can_write):
    return {'values':json.loads(row.fields_json) if row else {},'revision':row.revision if row else 0,
            'fields':fields,'canonical':canonical,'can_write':can_write,'provisional':True,
            'updated_at':row.updated_at if row else None,'updated_by':row.updated_by if row else None}

@router.get('/api/orders/{oid}/identification')
def order_identification(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .partner_models import Partner
    must(user,'launch.read');order=must_order(db,user,oid)
    return identification_out(db.get(OrderIdentification,oid),ORDER_FIELDS,
        {'reference':order.reference,'client_id':order.client_id,'client':db.get(Partner,order.client_id).name},permitted(user,'launch.update'))

@router.get('/api/launches/{lid}/identification')
def launch_identification(lid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');launch=must_access(db,user,lid)
    return identification_out(db.get(LaunchIdentification,lid),LAUNCH_FIELDS,
        {'name':launch.name,'reference':launch.order_ref,'client':launch.client_name,'orli_ref':launch.orli_ref},permitted(user,'launch.update'))

def save_identification(db, user, model, key, payload, scope):
    # Serialize first creation against owning row, then compare the optimistic revision.
    from .partner_phase2_models import BusinessOrder
    owner=BusinessOrder if model is OrderIdentification else Launch
    db.execute(update(owner).where(owner.id==key).values(id=owner.id))
    row=db.get(model,key,populate_existing=True)
    if payload.expected_revision != (row.revision if row else 0):
        raise HTTPException(409,'Fiche modifiée par un autre collaborateur. Actualisez avant de reprendre vos modifications.')
    values=json.loads(row.fields_json) if row else {}
    previous=dict(values)
    changes=payload.values.model_dump(mode='json',exclude_unset=True)
    values.update(changes)  # old/retired keys are never silently deleted
    if not row:
        row=model(**{('order_id' if model is OrderIdentification else 'launch_id'):key},updated_by=user.id)
        db.add(row)
        row.revision=0
    row.fields_json=json.dumps(values,ensure_ascii=False);row.revision+=1
    row.updated_by=user.id;row.updated_at=utcnow()
    audit(db,user,'identification.update',scope,key,{'revision':row.revision,'fields':list(changes),'previous_values':previous,'values':values})
    db.commit()

@router.patch('/api/orders/{oid}/identification')
def update_order_identification(oid:str,payload:IdentificationInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.update');must_order(db,user,oid)
    save_identification(db,user,OrderIdentification,oid,payload,'order')
    return order_identification(oid,user,db)

@router.patch('/api/launches/{lid}/identification')
def update_launch_identification(lid:str,payload:LaunchIdentificationInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.update');must_access(db,user,lid)
    save_identification(db,user,LaunchIdentification,lid,payload,'launch')
    return launch_identification(lid,user,db)


def migrate_historical_identification(conn):
    """Retain optional JSON added by the old identification branch, if present."""
    from sqlalchemy import inspect, text
    columns={column['name'] for column in inspect(conn).get_columns('launches')}
    if 'identification_json' not in columns:return
    table=LaunchIdentification.__table__
    for launch_id,raw,creator in conn.execute(text('SELECT id, identification_json, created_by FROM launches')):
        if not raw or conn.scalar(select(table.c.launch_id).where(table.c.launch_id==launch_id)):continue
        # Preserve original JSON including retired keys; malformed historical data
        # aborts the migration, rather than silently replacing it.
        values=json.loads(raw)
        if not isinstance(values,dict):raise ValueError('Fiche historique invalide : '+launch_id)
        conn.execute(table.insert().values(launch_id=launch_id,fields_json=raw,revision=1,updated_by=creator,updated_at=utcnow()))
