from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .core import Base, utcnow
from .models import uid


class PendingDocumentUpload(Base):
    __tablename__ = 'pending_document_uploads'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    folder: Mapped[str] = mapped_column(String(10))
    original_name: Mapped[str] = mapped_column(String(240))
    disk_name: Mapped[str] = mapped_column(String(48), unique=True)
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(String(120))
    analysis: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class DocumentIdentification(Base):
    __tablename__ = 'document_identifications'

    version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), primary_key=True)
    analysis: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24))
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
