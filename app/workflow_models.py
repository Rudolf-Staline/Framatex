"""MVP 0.3 — décisions sur versions, valeurs métier, règles et alertes d'impact.

Tables complémentaires uniquement : le schéma 0.1/0.2 n'est pas modifié.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class DocumentReview(Base):
    __tablename__ = 'document_reviews'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    decision: Mapped[str] = mapped_column(String(30))  # approved, rejected, changes_requested
    comment: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BusinessValueRevision(Base):
    __tablename__ = 'business_value_revisions'
    __table_args__ = (UniqueConstraint('launch_id', 'key', 'revision', name='uq_business_value_revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    key: Mapped[str] = mapped_column(String(70))
    revision: Mapped[int] = mapped_column(Integer)
    value_text: Mapped[str] = mapped_column(String(45))  # decimal exact, jamais de float
    unit: Mapped[str] = mapped_column(String(30))
    source_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'))
    reason: Mapped[str] = mapped_column(Text, default='')
    recorded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImpactRule(Base):
    __tablename__ = 'impact_rules'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(130))
    source_kind: Mapped[str] = mapped_column(String(20))  # value, document
    source_key: Mapped[str] = mapped_column(String(100))  # valeur ou doc_type exact
    source_folder: Mapped[str] = mapped_column(String(10))
    target_folder: Mapped[str] = mapped_column(String(10))
    instruction: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImpactAlert(Base):
    __tablename__ = 'impact_alerts'
    __table_args__ = (UniqueConstraint('rule_id', 'source_ref_id', name='uq_rule_source_alert'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey('impact_rules.id'))
    source_ref_id: Mapped[str] = mapped_column(String(36))
    old_value: Mapped[str | None] = mapped_column(String(70), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(70), nullable=True)
    status: Mapped[str] = mapped_column(String(35), default='to_review')
    resolution_note: Mapped[str] = mapped_column(Text, default='')
    resolved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
