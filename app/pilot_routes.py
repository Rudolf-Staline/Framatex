"""Capture and triage of real user observations during a controlled pilot."""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import User, Launch
from .access import accessible, must_access
from .pilot_models import PilotReport

router = APIRouter(prefix="/api/pilot", tags=["0.17 — Retours recette"])


class ReportInput(BaseModel):
    module: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=6, max_length=180)
    steps: str = Field(min_length=12, max_length=4000)
    expected: str = Field(min_length=5, max_length=2000)
    observed: str = Field(min_length=5, max_length=2000)
    severity: Literal["bloquant", "majeur", "mineur", "suggestion"]
    launch_id: str | None = None


class TriageInput(BaseModel):
    status: Literal["ouvert", "en_cours", "resolu", "ecarte"]
    resolution_note: str = Field(default="", max_length=2000)


def functions():
    from .main import is_admin, must, audit
    return is_admin, must, audit


def out(r: PilotReport):
    return {"id": r.id, "reporter_id": r.reporter_id,
            "launch_id": r.launch_id, "module": r.module, "title": r.title,
            "steps": r.steps, "expected": r.expected, "observed": r.observed,
            "severity": r.severity, "status": r.status,
            "resolution_note": r.resolution_note, "resolved_by": r.resolved_by,
            "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}


@router.get("/reports")
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_admin, _, _ = functions()
    rows = db.scalars(select(PilotReport).order_by(PilotReport.created_at.desc()).limit(250)).all()
    if is_admin(user):
        return [out(r) for r in rows]
    # When a person's launch membership is revoked, its report contents also
    # disappear from their own listing, even if they originally filed it.
    return [out(r) for r in rows if r.reporter_id == user.id and
            (r.launch_id is None or accessible(db, user, db.get(Launch, r.launch_id)))]


@router.post("/reports", status_code=201)
def create_report(payload: ReportInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_admin, must, audit = functions()
    if payload.launch_id:
        must(user, "launch.read")
        must_access(db, user, payload.launch_id)
    r = PilotReport(reporter_id=user.id, launch_id=payload.launch_id,
                    module=payload.module.strip(), title=payload.title.strip(),
                    steps=payload.steps.strip(), expected=payload.expected.strip(),
                    observed=payload.observed.strip(), severity=payload.severity)
    db.add(r); db.flush()
    audit(db, user, "pilot.report.create", "pilot_report", r.id,
          {"severity": r.severity, "module": r.module, "launch_id": r.launch_id})
    db.commit(); db.refresh(r)
    return out(r)


@router.patch("/reports/{report_id}")
def triage(report_id: str, payload: TriageInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_admin, _, audit = functions()
    if not is_admin(user):
        raise HTTPException(403, "Suivi réservé à l'administration")
    r = db.get(PilotReport, report_id)
    if r is None:
        raise HTTPException(404, "Signalement introuvable")
    if payload.status in {"resolu", "ecarte"} and len(payload.resolution_note.strip()) < 12:
        raise HTTPException(422, "Une justification d'au moins 12 caractères est requise")
    before = r.status
    r.status = payload.status
    r.resolution_note = payload.resolution_note.strip()
    r.resolved_by = user.id if payload.status in {"resolu", "ecarte"} else None
    audit(db, user, "pilot.report.triage", "pilot_report", r.id,
          {"from": before, "to": r.status})
    db.commit(); db.refresh(r)
    return out(r)
