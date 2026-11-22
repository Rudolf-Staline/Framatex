"""Informations de pilotage et collaboration strictement internes."""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class LaunchOperations(Base):
    __tablename__ = "launch_operations"
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"), primary_key=True)
    article: Mapped[str | None] = mapped_column(String(180), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provisional_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    definitive_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InternalComment(Base):
    __tablename__ = "internal_document_comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExperienceNote(Base):
    __tablename__ = "internal_experience_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str | None] = mapped_column(ForeignKey("launches.id"), index=True, nullable=True)
    partner_id: Mapped[str | None] = mapped_column(ForeignKey("business_partners.id"), index=True, nullable=True)
    party_type: Mapped[str] = mapped_column(String(20), index=True)
    party_name: Mapped[str] = mapped_column(String(150), index=True)
    category: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    importance: Mapped[str] = mapped_column(String(20), default="information", server_default="information")
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BusinessPartner(Base):
    __tablename__ = "business_partners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    party_type: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(180))
    normalized_name: Mapped[str] = mapped_column(String(180), index=True)
    business_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_account_id: Mapped[str | None] = mapped_column(ForeignKey("client_accounts.id"), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PartnerAlias(Base):
    __tablename__ = "business_partner_aliases"
    __table_args__ = (UniqueConstraint("partner_id", "normalized_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    partner_id: Mapped[str] = mapped_column(ForeignKey("business_partners.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    normalized_name: Mapped[str] = mapped_column(String(180), index=True)


class LaunchPartner(Base):
    __tablename__ = "launch_partners"
    __table_args__ = (UniqueConstraint("launch_id", "partner_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"), index=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("business_partners.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExperienceDecision(Base):
    __tablename__ = "internal_experience_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    note_id: Mapped[str] = mapped_column(ForeignKey("internal_experience_notes.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
