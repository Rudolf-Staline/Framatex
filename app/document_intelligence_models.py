"""Décisions humaines sur les rapprochements proposés lors d'un dépôt."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .core import Base, utcnow
from .models import uid


class DocumentRelationshipDecision(Base):
    __tablename__ = 'document_relationship_decisions'
    __table_args__ = (UniqueConstraint('uploaded_version_id', name='uq_relationship_uploaded_version'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    uploaded_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    candidate_version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    evidence_signature: Mapped[str] = mapped_column(String(64))
    relationship_kind: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text, default='')
    decided_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
