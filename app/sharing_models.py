"""MVP 0.14 — partage simulé client / échanges fournisseurs, internes uniquement."""
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Index
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class ClientPublication(Base):
    __tablename__ = 'client_publications'
    __table_args__ = (Index('idx_client_publication_launch', 'launch_id', 'status'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'))
    client_id: Mapped[str | None] = mapped_column(ForeignKey('clients.id'), nullable=True, index=True)
    client_name: Mapped[str] = mapped_column(String(150))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default='published')
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

class SupplierDocumentRequest(Base):
    __tablename__ = 'supplier_document_requests'
    __table_args__ = (Index('idx_supplier_request_launch', 'launch_id', 'status'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    folder_slug: Mapped[str] = mapped_column(String(10))
    supplier_name: Mapped[str] = mapped_column(String(150))
    requested_title: Mapped[str] = mapped_column(String(200))
    expected_doc_type: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(Text, default='')
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default='requested')
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    response_version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
