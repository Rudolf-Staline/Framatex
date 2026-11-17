"""Append audit events in the caller’s transaction; never commit here."""
import json
from sqlalchemy.orm import Session
from .models import AuditEvent, User


def audit(db: Session, user: User | None, action: str, entity: object, target_id: str, detail: dict | None = None):
    event=AuditEvent(actor_id=user.id if user else None, action=action, target_type=str(entity), target_id=target_id, detail=json.dumps(detail or {}, ensure_ascii=False))
    db.add(event)
    if action in {'session.logout','session.revoke_all','session.restore'}:
        # Security state survives any separately authorized audit export/purge.
        from .core import utcnow
        from .models import uid
        from .operations_models import SessionGeneration, SessionRevocation
        event.id=uid()
        if action=='session.logout':
            db.merge(SessionRevocation(session_id=target_id,revoked_at=utcnow()))
        else:
            scope='all' if action=='session.restore' else 'user:'+target_id
            db.merge(SessionGeneration(scope=scope,generation=event.id))
