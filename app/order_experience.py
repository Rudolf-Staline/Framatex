"""Atelier lessons, scoped by canonical order membership and folder permissions."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, inspect, or_, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from .access import must, permitted
from .audit import audit
from .core import Base, get_current_user, get_db, utcnow
from .models import uid
from .order_documents import must_order, order_access_clause
from .partner_phase2_models import BusinessOrder

router = APIRouter(prefix='/api/order-experience', tags=['Mémoire métier'])
FolderSlug = Literal['jaune', 'rose', 'bleu', 'vert']
ExperienceStatus = Literal['ouvert', 'en_cours', 'resolu']
FOLDERS = ('jaune', 'rose', 'bleu', 'vert')


class OrderExperience(Base):
    __tablename__ = 'order_experiences'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey('business_orders.id'), index=True)
    folder: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Details(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=180)
    problem: str = Field(min_length=12, max_length=8000)
    solution: str = Field(default='', max_length=6000)
    lesson: str = Field(default='', max_length=4000)
    status: ExperienceStatus = 'ouvert'

    @model_validator(mode='after')
    def resolved_needs_solution(self):
        if self.status == 'resolu' and len(self.solution) < 12:
            raise ValueError('Décrivez la solution avant de marquer le cas résolu')
        return self


class CreateExperience(Details):
    order_id: str = Field(min_length=36, max_length=36)
    folder: FolderSlug


class EditExperience(Details):
    revision: int = Field(ge=1)


def ready(db):
    if db.get_bind().dialect.name == 'postgresql' and not inspect(db.connection()).has_table(OrderExperience.__tablename__):
        raise HTTPException(503, 'La mémoire métier attend la migration de la base de données')


def output(row, reference, user):
    return {
        'id': row.id, 'order_id': row.order_id, 'reference': reference,
        'folder': row.folder, 'title': row.title, 'problem': row.problem,
        'solution': row.solution, 'lesson': row.lesson, 'status': row.status,
        'revision': row.revision, 'updated_at': row.updated_at,
        'can_edit': permitted(user, 'document.write', row.folder),
    }


@router.get('')
def list_experiences(q: str = Query('', max_length=180), status: ExperienceStatus | None = None,
                     order_id: str | None = Query(None, max_length=36), offset: int = Query(0, ge=0),
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, 'launch.read')
    ready(db)
    if order_id:
        must_order(db, user, order_id)
    read_folders = [folder for folder in FOLDERS if permitted(user, 'document.read', folder)]
    query = (select(OrderExperience, BusinessOrder.reference).join(BusinessOrder)
             .where(order_access_clause(user), OrderExperience.folder.in_(read_folders)))
    if order_id:
        query = query.where(OrderExperience.order_id == order_id)
    if status:
        query = query.where(OrderExperience.status == status)
    if q.strip():
        term = q.strip().lower()
        query = query.where(or_(*(func.lower(field).contains(term, autoescape=True) for field in
                                  (BusinessOrder.reference, OrderExperience.title, OrderExperience.problem,
                                   OrderExperience.solution, OrderExperience.lesson))))
    page_size = 15
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(OrderExperience.updated_at.desc(), OrderExperience.id).offset(offset).limit(page_size))
    return {'items': [output(row, ref, user) for row, ref in rows], 'total': total, 'limit': page_size,
            'writable_folders': [folder for folder in read_folders if permitted(user, 'document.write', folder)]}


@router.post('', status_code=201)
def create_experience(payload: CreateExperience, user=Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, 'launch.read')
    ready(db)
    must(user, 'document.read', payload.folder)
    must(user, 'document.write', payload.folder)
    order = must_order(db, user, payload.order_id)
    row = OrderExperience(**payload.model_dump(), created_by=user.id)
    db.add(row)
    db.flush()
    audit(db, user, 'experience.create', 'order_experience', row.id, {'order_id': order.id, 'folder': row.folder})
    result = output(row, order.reference, user)
    db.commit()
    return result


@router.patch('/{record_id}')
def edit_experience(record_id: str, payload: EditExperience, user=Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, 'launch.read')
    ready(db)
    row = db.get(OrderExperience, record_id)
    if not row:
        raise HTTPException(404, 'Retour d’expérience introuvable')
    order = must_order(db, user, row.order_id)
    must(user, 'document.read', row.folder)
    must(user, 'document.write', row.folder)
    values = payload.model_dump(exclude={'revision'})
    changed = db.execute(update(OrderExperience)
                         .where(OrderExperience.id == record_id, OrderExperience.revision == payload.revision)
                         .values(**values, updated_at=utcnow(), revision=payload.revision + 1))
    if changed.rowcount != 1:
        raise HTTPException(409, 'Ce retour a été modifié. Actualisez avant de l’éditer.')
    db.refresh(row)
    audit(db, user, 'experience.update', 'order_experience', row.id, {'order_id': order.id, 'status': row.status})
    result = output(row, order.reference, user)
    db.commit()
    return result
