"""Internal comments tied to an immutable documentary version."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class DocumentComment(Base):
    __tablename__ = 'document_comments'
    __table_args__ = (Index('ix_document_comments_version_date', 'document_version_id', 'created_at'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
