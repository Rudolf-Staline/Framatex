"""MVP 0.9 — priorités métier explicables et assistant de navigation à règles fixes.

Pas d'IA générative, de chargement de contenu de fichiers ni d'accès aux données
sans les permissions que le serveur vérifie déjà. Les actions sont des liens internes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core import get_db, get_current_user
from .models import DocumentVersion, Launch, User
from .completeness import evaluate
from .workflow_models import ImpactAlert, ImpactRule
from .spec_models import ClientRequirement, SpecificationAmbiguity
from .mail_models import EmailCommitment
from .spec_routes import _req_output, _amb_output

from .access import must, permitted

router = APIRouter(tags=["0.9 — Pilotage et aide"])


def _source_folder(db: Session, version_id: str | None) -> str | None:
    version = db.get(DocumentVersion, version_id) if version_id else None
    return version.document.folder.slug if version else None


def _add(out: list, launch: Launch, *, kind: str, title: str, description: str, rank: int,
         area: str, action: str, item_id: str, deadline: str | None = None):
    out.append({"id": f"{kind}:{item_id}", "launch_id": launch.id,
                "launch_name": launch.name, "kind": kind, "title": title,
                "description": description, "rank": rank,
                "priority": ("urgent" if rank == 0 else "high" if rank == 1 else "normal"),
                "priority_reason": ("Échéance dépassée" if rank == 0 else
                    "Vérification documentaire ou métier requise" if rank == 1 else
                    "Action à suivre"),
                "area": area, "action": action, "deadline": deadline})


@router.get("/api/workspace/priorities")
def priorities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste consolidée, seulement des éléments dont les sources sont lisibles.

    Priorités déterministes : 0 échéance dépassée, 1 anomalie/action à traiter,
    2 engagement à échéance future proche. Pas de score arbitraire ni d'automatisation.
    """
    must(user, "launch.read")
    today = datetime.now(ZoneInfo("Africa/Casablanca")).date()
    horizon = today + timedelta(days=7)
    from .access import visible
    launches = visible(db, user, db.scalars(select(Launch).order_by(Launch.created_at.desc())).all())
    items = []
    visible_launches = [l for l in launches if l.status != "Clôturé"]
    for launch in visible_launches:
        report = evaluate(db, launch, user, permitted)
        for row in report.get("rows", []):
            if row["status"] not in ("missing", "pending_validation"):
                continue
            kind = "missing" if row["status"] == "missing" else "validation"
            _add(items, launch, kind=kind,
                 title=("Pièce manquante : " if kind == "missing" else "Validation à obtenir : ") + row["title"],
                 description=f"Sous-dossier {row['folder'].capitalize()} · {row['document_type']}",
                 rank=1, area="documents", action="open_launch", item_id=row["id"])
        alerts = db.scalars(select(ImpactAlert).where(ImpactAlert.launch_id == launch.id,
                                                      ImpactAlert.status == "to_review")).all()
        for alert in alerts:
            rule = db.get(ImpactRule, alert.rule_id)
            if not rule or not (permitted(user,"document.read",rule.source_folder)
                                and permitted(user,"document.read",rule.target_folder)):
                continue
            _add(items, launch, kind="impact", title="Modification à examiner : " + rule.name,
                 description=rule.instruction[:210], rank=1, area="workflow",
                 action="open_launch", item_id=alert.id)
        for req in db.scalars(select(ClientRequirement).where(ClientRequirement.launch_id == launch.id)).all():
            source_folder = _source_folder(db, req.source_version_id)
            evidence_folder = _source_folder(db, req.evidence_version_id)
            if not source_folder or not permitted(user,"document.read",source_folder):
                continue
            if req.evidence_version_id and (not evidence_folder or not permitted(user,"document.read",evidence_folder)):
                continue
            state = _req_output(db, req, user)["state"]
            if state == "verified":
                continue
            _add(items, launch, kind="requirement", title="Exigence à vérifier : " + req.title,
                 description={"uncovered":"Justificatif absent", "to_verify":"Preuve à examiner",
                              "source_changed":"Document source modifié", "evidence_changed":"Preuve remplacée"}.get(state,"À examiner"),
                 rank=1, area="spec", action="open_launch", item_id=req.id)
        for amb in db.scalars(select(SpecificationAmbiguity).where(SpecificationAmbiguity.launch_id == launch.id)).all():
            source_folder = _source_folder(db, amb.source_version_id)
            clarification_folder = _source_folder(db, amb.clarification_version_id)
            if not source_folder or not permitted(user,"document.read",source_folder):
                continue
            if amb.clarification_version_id and (not clarification_folder or not permitted(user,"document.read",clarification_folder)):
                continue
            state = _amb_output(db,amb,user)["status"]
            if state not in ("open", "source_changed"):
                continue
            _add(items, launch, kind="ambiguity", title="Clarification requise",
                 description=amb.question[:210], rank=1, area="spec", action="open_launch", item_id=amb.id)
        if permitted(user,"document.read","rose"):
            for commitment in db.scalars(select(EmailCommitment).where(
                    EmailCommitment.launch_id == launch.id,
                    EmailCommitment.status.in_(["pending", "postponed"]))).all():
                if not commitment.due_date:
                    continue  # Date inconnue : ne pas inventer d'urgence.
                try:
                    due = datetime.strptime(commitment.due_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if due > horizon:
                    continue
                overdue = due < today
                _add(items, launch, kind="commitment", title=commitment.description[:120],
                     description=f"Engagement {('en retard' if overdue else 'à suivre')} · {commitment.responsible[:100]}",
                     rank=0 if overdue else 2, area="mail", action="open_launch",
                     item_id=commitment.id, deadline=commitment.due_date)
    items.sort(key=lambda row: (row["rank"], row["deadline"] or "9999-12-31",
                                row["launch_name"].casefold(),row["id"]))
    counts = {"urgent":sum(i["priority"] == "urgent" for i in items),
              "high":sum(i["priority"] == "high" for i in items),
              "normal":sum(i["priority"] == "normal" for i in items)}
    return {"total":len(items), "counts":counts, "items":items[:100],
            "truncated":len(items)>100,"launches_considered":len(visible_launches),
            "method":"Urgent : engagement dépassé ; prioritaire : écart ou vérification ; à suivre : échéance dans 7 jours.",
            "as_of":today.isoformat()}


class GuideRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    launch_id: str | None = Field(default=None, max_length=36)


@router.post("/api/assistant/guide")
def guide(payload: GuideRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .guide_core import Principal,GuideContext,retrieve,answer
    from .access import is_admin
    must(user,'launch.read')
    if payload.launch_id:
        from .access import must_access
        must_access(db,user,payload.launch_id)
    who=Principal('employee',user,set(),is_admin(user))
    context=GuideContext(page='detail' if payload.launch_id else 'home',launch_id=payload.launch_id)
    hits,_=retrieve(payload.question,who,context)
    result=answer(hits,who,context,db)
    p=hits[0] if hits else None;area=p.get('legacy_area') if p else None
    destination=('detail' if payload.launch_id and area else 'admin' if p and p['destination']=='admin' else 'orders') if p else None
    return {**result,'destination':destination,'launch_id':payload.launch_id if destination=='detail' else None,
            'area':area if destination=='detail' else None,'folder':None,
            'source':'Framatex Guide · catalogue local vérifié'}
