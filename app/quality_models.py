"""Incrément 0.4 : valeurs sourcées inter-documents et constats Excel immuables."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class DocumentDatum(Base):
    __tablename__ = 'document_data'
    __table_args__ = (UniqueConstraint('document_version_id', 'field_key', name='uq_document_datum_field'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    field_key: Mapped[str] = mapped_column(String(70))
    value_text: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(30))
    recorded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrossDocumentRule(Base):
    __tablename__ = 'cross_document_rules'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(140))
    field_key: Mapped[str] = mapped_column(String(70))
    left_doc_type: Mapped[str] = mapped_column(String(100))
    right_doc_type: Mapped[str] = mapped_column(String(100))
    left_folder: Mapped[str] = mapped_column(String(10))
    right_folder: Mapped[str] = mapped_column(String(10))
    comparison_mode: Mapped[str] = mapped_column(String(32), default='equality', server_default='equality')
    tolerance_text: Mapped[str] = mapped_column(String(35), default='0')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QualityDecision(Base):
    __tablename__ = 'quality_decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey('cross_document_rules.id'))
    evidence_signature: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))  # justified, to_correct
    note: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExcelInspection(Base):
    __tablename__ = 'excel_inspections'
    __table_args__ = (UniqueConstraint('document_version_id', name='uq_excel_inspection_version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_version_id: Mapped[str] = mapped_column(ForeignKey('document_versions.id'), index=True)
    baseline_version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(24))  # reviewed, first_version, limited, error
    scanned_cells: Mapped[int] = mapped_column(Integer, default=0)
    formula_count: Mapped[int] = mapped_column(Integer, default=0)
    findings_json: Mapped[str] = mapped_column(Text, default='[]')
    inspected_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
