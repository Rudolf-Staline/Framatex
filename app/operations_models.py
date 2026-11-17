"""Operational state independent of mutable audit history and SMTP attempts."""
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base


class SessionGeneration(Base):
    __tablename__ = 'session_generations'
    scope: Mapped[str] = mapped_column(String(80), primary_key=True)
    generation: Mapped[str] = mapped_column(String(36))


class SessionRevocation(Base):
    __tablename__ = 'session_revocations'
    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Retained independently of audit. An explicit retention decision is required
    # before purging; keeping these small tombstones cannot revive old tokens.
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PartnerMailLease(Base):
    __tablename__ = 'partner_mail_leases'
    mail_id: Mapped[str] = mapped_column(ForeignKey('partner_mail.id'), primary_key=True)
    token: Mapped[str] = mapped_column(String(36))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    phase: Mapped[str] = mapped_column(String(20), default='reserved')
