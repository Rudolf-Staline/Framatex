"""Shared launch lookup, legacy section labels and API representation."""
from fastapi import HTTPException
from sqlalchemy.orm import Session, object_session
from .models import Launch

FOLDERS = [("jaune", "Technique"), ("rose", "Réception"), ("bleu", "Douane"), ("vert", "Facturation")]
SLUGS = {slug for slug, _ in FOLDERS}
STATUSES = {"À compléter", "En cours", "En validation", "Clôturé"}


def get_launch(db: Session, launch_id: str) -> Launch:
    l = db.get(Launch, launch_id)
    if not l:
        raise HTTPException(404, "Lancement introuvable")
    return l


def launch_out(l: Launch):
    from .order_documents import launch_order
    db=object_session(l);link=launch_order(db,l.id) if db else None
    return {"order_id":link.order_id if link else None, "restricted": bool(l.restricted), "id": l.id, "name": l.name, "order_ref": l.order_ref, "client_name": l.client_name, "orli_ref": l.orli_ref, "status": l.status, "created_at": l.created_at.isoformat(), "updated_at": l.updated_at.isoformat()}
