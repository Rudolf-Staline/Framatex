"""Mémoire métier et pièces attendues du Dossier Jaune unique."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid
from .global_library_models import GlobalFolder  # noqa: F401 — register FK target for the migration CLI


class ExperienceRecord(Base):
    __tablename__ = "experience_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    folder_slug: Mapped[str] = mapped_column(String(10), ForeignKey("global_folders.slug"), index=True)
    orli_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    problem: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    lesson: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="ouvert")
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    __mapper_args__ = {"version_id_col": revision}


class DocumentExpectation(Base):
    __tablename__ = "document_expectations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    folder_slug: Mapped[str] = mapped_column(String(10), ForeignKey("global_folders.slug"), index=True)
    orli_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    document_type: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
