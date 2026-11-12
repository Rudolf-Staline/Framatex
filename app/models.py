from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Integer, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from .core import Base, utcnow


def uid(): return str(uuid.uuid4())

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    roles: Mapped[list[Role]] = relationship(secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles")
    grants: Mapped[list[RolePermission]] = relationship(back_populates="role", cascade="all, delete-orphan")

class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    folder_slug: Mapped[str | None] = mapped_column(String(10), nullable=True)
    role: Mapped[Role] = relationship(back_populates="grants")

class Launch(Base):
    __tablename__ = "launches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(180))
    order_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    orli_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="À compléter")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    legacy_folders: Mapped[list[Folder]] = relationship(back_populates="launch")

    @property
    def folders(self):
        from .order_documents import folders_for_launch
        return folders_for_launch(object_session(self), self)

class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("launch_id", "slug"), UniqueConstraint("dossier_id", "slug"), CheckConstraint("(launch_id IS NOT NULL) != (dossier_id IS NOT NULL)",name="folder_single_owner"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str | None] = mapped_column(ForeignKey("launches.id"), nullable=True, index=True)
    dossier_id: Mapped[str | None] = mapped_column(ForeignKey("order_dossiers.id"), nullable=True, index=True)
    canonical_id: Mapped[str | None] = mapped_column(ForeignKey("folders.id"), nullable=True)
    slug: Mapped[str] = mapped_column(String(10))
    label: Mapped[str] = mapped_column(String(70))
    launch: Mapped[Launch | None] = relationship(back_populates="legacy_folders", foreign_keys=[launch_id])
    documents: Mapped[list[Document]] = relationship(back_populates="folder")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    folder_id: Mapped[str] = mapped_column(ForeignKey("folders.id"), index=True)
    launch_id: Mapped[str | None] = mapped_column(ForeignKey("launches.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    doc_type: Mapped[str] = mapped_column(String(100), default="Autre")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    folder: Mapped[Folder] = relationship(back_populates="documents")
    launch: Mapped[Launch | None] = relationship()

    @property
    def context_launch_id(self):
        if self.launch_id: return self.launch_id
        if self.folder.launch_id: return self.folder.launch_id
        from .partner_phase2_models import BusinessOrderLaunch
        from .order_documents import OrderDossier
        from sqlalchemy import select
        db=object_session(self)
        return db.scalar(select(BusinessOrderLaunch.launch_id).join(OrderDossier, OrderDossier.order_id==BusinessOrderLaunch.order_id).where(OrderDossier.id==self.folder.dossier_id).order_by(BusinessOrderLaunch.launch_id).limit(1))
    versions: Mapped[list[DocumentVersion]] = relationship(back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.number")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    original_name: Mapped[str] = mapped_column(String(250))
    disk_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    document: Mapped[Document] = relationship(back_populates="versions")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__=(Index('ix_audit_action_target_time','action','target_id','occurred_at'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    action: Mapped[str] = mapped_column(String(70))
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_type: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LaunchMember(Base):
    """A user explicitly allowed to access a restricted manufacturing launch.

    Role + folder permissions are still required for every action.
    """
    __tablename__ = "launch_members"
    __table_args__ = (UniqueConstraint("launch_id", "user_id", name="uq_launch_member"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey("launches.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
