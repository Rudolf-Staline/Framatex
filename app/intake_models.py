"""Traçabilité des métadonnées explicitement confirmées."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class ConfirmedField(Base):
    __tablename__ = "confirmed_extracted_fields"
    __table_args__ = (UniqueConstraint("document_version_id", "field_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"),index=True)
    field_key: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(140))
    unit: Mapped[str] = mapped_column(String(30),default="")
    source_excerpt: Mapped[str] = mapped_column(String(180),default="")
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
