"""MVP 0.13 : circuits de validation par version et notifications internes ciblées.

Les modèles complètent le schéma existant ; aucune colonne métier antérieure n'est réécrite.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class ApprovalTemplate(Base):
    __tablename__ = "approval_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(140))
    folder_slug: Mapped[str] = mapped_column(String(10))
    document_type: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalStage(Base):
    __tablename__ = "approval_stages"
    __table_args__ = (UniqueConstraint("template_id", "position", name="uq_approval_stage_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("approval_templates.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(140))
    reviewer_role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))


class ApprovalRun(Base):
    __tablename__ = "approval_runs"
    __table_args__ = (UniqueConstraint("document_version_id", "template_id", name="uq_approval_run_version_template"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("approval_templates.id"))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    current_position: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    started_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (UniqueConstraint("run_id", "stage_id", name="uq_approval_run_stage_decision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("approval_runs.id"), index=True)
    stage_id: Mapped[str] = mapped_column(ForeignKey("approval_stages.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InternalNotification(Base):
    __tablename__ = "internal_notifications"
    __table_args__ = (UniqueConstraint("recipient_id", "event_key", name="uq_notification_recipient_event"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text, default="")
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"))
    folder_slug: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
