"""0.7 — Exigences client et points d'ambiguïté reliés aux versions sources."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class ClientRequirement(Base):
    __tablename__ = 'client_requirements'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    source_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(48))
    description: Mapped[str] = mapped_column(Text)
    source_excerpt: Mapped[str] = mapped_column(String(500))
    evidence_version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_source_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_evidence_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SpecificationAmbiguity(Base):
    __tablename__ = 'specification_ambiguities'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    source_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    excerpt: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(48))
    question: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default='open')
    resolution: Mapped[str] = mapped_column(Text, default='')
    clarification_version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    confirmed_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
