"""Snapshots read-only d'exports ORLI et décisions de rapprochement humain."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class OrliImportBatch(Base):
    __tablename__ = 'orli_import_batches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    file_name: Mapped[str] = mapped_column(String(240))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    format_name: Mapped[str] = mapped_column(String(12))
    mapping_json: Mapped[str] = mapped_column(Text)
    total_rows: Mapped[int] = mapped_column(Integer)
    valid_rows: Mapped[int] = mapped_column(Integer)
    imported_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class OrliImportedLaunch(Base):
    __tablename__ = 'orli_imported_launches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(ForeignKey('orli_import_batches.id'), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    orli_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    order_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(180), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_json: Mapped[str] = mapped_column(Text, default='[]')
    raw_json: Mapped[str] = mapped_column(Text)

class OrliLink(Base):
    __tablename__ = 'orli_links'
    __table_args__ = (UniqueConstraint('launch_id'), UniqueConstraint('record_id'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey('orli_imported_launches.id'), index=True)
    confirmed_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decision_note: Mapped[str] = mapped_column(Text, default='')
    source_ref: Mapped[str] = mapped_column(String(100))
