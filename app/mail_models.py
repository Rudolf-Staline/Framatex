"""0.8 — Emails archivés et engagements validés par une personne habilitée."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class ArchivedEmail(Base):
    __tablename__ = 'archived_emails'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), unique=True)
    message_id: Mapped[str] = mapped_column(String(250), default='')
    subject: Mapped[str] = mapped_column(String(300))
    sender: Mapped[str] = mapped_column(String(300), default='')
    recipients: Mapped[str] = mapped_column(Text, default='')
    carbon_copy: Mapped[str] = mapped_column(Text, default='')
    sent_at_raw: Mapped[str] = mapped_column(String(180), default='')
    body_excerpt: Mapped[str] = mapped_column(Text, default='')
    attachments_json: Mapped[str] = mapped_column(Text, default='[]')
    archived_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailCommitment(Base):
    __tablename__ = 'email_commitments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    email_id: Mapped[str] = mapped_column(ForeignKey('archived_emails.id'), index=True)
    description: Mapped[str] = mapped_column(String(650))
    responsible: Mapped[str] = mapped_column(String(250))
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    condition: Mapped[str] = mapped_column(String(500), default='')
    source_excerpt: Mapped[str] = mapped_column(String(650), default='')
    status: Mapped[str] = mapped_column(String(24), default='pending')
    decision_note: Mapped[str] = mapped_column(Text, default='')
    confirmed_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
