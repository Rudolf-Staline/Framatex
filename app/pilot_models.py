"""Pilot acceptance feedback (fictional datasets only until Framatex authorization)."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class PilotReport(Base):
    __tablename__ = "pilot_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    launch_id: Mapped[str | None] = mapped_column(ForeignKey("launches.id"), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(180))
    steps: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)
    observed: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), default="ouvert")
    resolution_note: Mapped[str] = mapped_column(Text, default="")
    resolved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
