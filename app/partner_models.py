"""Additive partner tables; partner accounts can never authenticate as employees."""
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class Partner(Base):
    __tablename__ = 'partners'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    contact: Mapped[str] = mapped_column(Text, default='')

class PartnerAccount(Base):
    __tablename__ = 'partner_accounts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    partner_id: Mapped[str] = mapped_column(ForeignKey('partners.id'), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class PartnerToken(Base):
    __tablename__ = 'partner_tokens'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('partner_accounts.id'), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)

class PartnerRequest(Base):
    __tablename__ = 'partner_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    partner_id: Mapped[str] = mapped_column(ForeignKey('partners.id'), index=True)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    order_ref: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(100))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='requested')
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revision: Mapped[int] = mapped_column(Integer, default=0)

class PartnerSubmission(Base):
    __tablename__ = 'partner_submissions'
    __table_args__ = (UniqueConstraint('request_id', 'number'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey('partner_requests.id'), index=True)
    number: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[str] = mapped_column(ForeignKey('partner_accounts.id'))
    original_name: Mapped[str] = mapped_column(String(240))
    disk_name: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    reason: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PartnerEvent(Base):
    __tablename__ = 'partner_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey('partner_requests.id'), index=True)
    actor: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PartnerPublication(Base):
    __tablename__ = 'partner_publications'
    __table_args__ = (UniqueConstraint('publication_id', 'partner_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    publication_id: Mapped[str] = mapped_column(ForeignKey('client_publications.id'))
    partner_id: Mapped[str] = mapped_column(ForeignKey('partners.id'), index=True)
