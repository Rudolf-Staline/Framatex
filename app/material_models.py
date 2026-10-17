"""V0.12 — Traçabilité matières par lancement et journaux non destructifs.

Les quantités sont déclarées par un humain et justifiées par une version de
pièce, jamais interprétées comme un stock ERP ou une réception vérifiée.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class MaterialLine(Base):
    __tablename__ = 'material_lines'
    __table_args__ = (UniqueConstraint('launch_id', 'reference'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    reference: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(180))
    unit: Mapped[str] = mapped_column(String(12))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MaterialPlanRevision(Base):
    __tablename__ = 'material_plan_revisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    line_id: Mapped[str] = mapped_column(ForeignKey('material_lines.id'), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3))
    source_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'))
    note: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MaterialMovement(Base):
    __tablename__ = 'material_movements'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    line_id: Mapped[str] = mapped_column(ForeignKey('material_lines.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # ordered | received
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3))
    source_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'))
    counterparty: Mapped[str | None] = mapped_column(String(140), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
