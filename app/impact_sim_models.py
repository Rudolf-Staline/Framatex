"""Scenarios de simulation indicatifs, sauvegardes en lecture seule.

Ils ne remplacent aucune valeur métier et ne créent aucun ordre ORLI.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid


class ImpactSimulation(Base):
    __tablename__ = 'impact_simulations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    launch_id: Mapped[str] = mapped_column(ForeignKey('launches.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    payload_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
