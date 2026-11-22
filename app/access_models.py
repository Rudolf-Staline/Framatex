"""Collaborateurs et habilitations : profil, affectations par commande, droits hérités.

Tables additives (migration ``0013_access_management``) ; les tables ``users``,
``roles`` et ``role_permissions`` existantes ne sont pas modifiées.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .core import Base, utcnow
from .models import uid

# Un profil sans ligne (bases de test historiques) garde l'ancien comportement par rôles.
SCOPE_ASSIGNMENTS = "assignments"
SCOPE_LEGACY = "legacy"


class CollaboratorProfile(Base):
    """Données de compte propres à l'administration des accès (une ligne par utilisateur)."""
    __tablename__ = "collaborator_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    job_title: Mapped[str] = mapped_column(String(120), default="")
    access_scope: Mapped[str] = mapped_column(String(20), default=SCOPE_ASSIGNMENTS)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # Toute session émise avant cette date est refusée (réinitialisation, révocation).
    sessions_valid_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_prefs: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LaunchAssignment(Base):
    """Un collaborateur, une commande, un sous-dossier, et les actions autorisées."""
    __tablename__ = "launch_assignments"
    __table_args__ = (UniqueConstraint("launch_id", "user_id", "folder_slug", name="uq_launch_assignment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    folder_slug: Mapped[str] = mapped_column(String(10))
    actions: Mapped[str] = mapped_column(Text, default="[]")   # liste JSON normalisée
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LegacyAccessProposal(Base):
    """Droit d'avant la migration, à confirmer ou écarter par le chef (jamais appliqué seul)."""
    __tablename__ = "legacy_access_proposals"
    __table_args__ = (UniqueConstraint("launch_id", "user_id", name="uq_legacy_access_proposal"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    origin: Mapped[str] = mapped_column(String(40))            # role | member | creator
    folders: Mapped[str] = mapped_column(Text, default="{}")    # {slug: [actions]} proposé
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending | applied | dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
