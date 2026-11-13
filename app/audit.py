"""Append audit events in the caller’s transaction; never commit here."""
import json
from sqlalchemy.orm import Session
from .models import AuditEvent, User


def audit(db: Session, user: User | None, action: str, entity: object, target_id: str, detail: dict | None = None):
    db.add(AuditEvent(actor_id=user.id if user else None, action=action, target_type=str(entity), target_id=target_id, detail=json.dumps(detail or {}, ensure_ascii=False)))
