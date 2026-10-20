"""Additive global Dossier Jaune mapping.

A document keeps its original folder, launch and immutable version identifiers
through the transition.  GlobalDocumentEntry is the authoritative category
for the new UI; legacy access controls must still apply to every object.
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .core import Base, utcnow


class GlobalFolder(Base):
    __tablename__ = "global_folders"
    slug: Mapped[str] = mapped_column(String(10), primary_key=True)
    label: Mapped[str] = mapped_column(String(70), nullable=False)


class GlobalDocumentEntry(Base):
    __tablename__ = "global_document_entries"
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), primary_key=True
    )
    folder_slug: Mapped[str] = mapped_column(
        ForeignKey("global_folders.slug"), index=True, nullable=False
    )
    orli_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    orli_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    legacy_folder_id: Mapped[str] = mapped_column(String(36), nullable=False)
    legacy_launch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class GlobalLibraryConfig(Base):
    """Only technical compatibility container; never a manufacturing dossier."""
    __tablename__ = "global_library_config"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    legacy_launch_id: Mapped[str] = mapped_column(
        ForeignKey("launches.id"), unique=True, nullable=False
    )
