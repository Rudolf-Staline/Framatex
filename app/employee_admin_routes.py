"""Employee roles, accounts and audit HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from .access import admin_only
from .audit import audit
from .employees import user_out
from .launches import SLUGS
from .access import ACTIONS
import json
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_current_user, get_db, hash_password
from .models import AuditEvent, Role, RolePermission, User

router = APIRouter()

class Grant(BaseModel):
    action: str
    folder: str | None = None


class RolePayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    permissions: list[Grant] = Field(default_factory=list)


class UserPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    role_ids: list[str] = Field(default_factory=list)


@router.get("/api/admin/roles")
def list_roles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    return [{"id": r.id, "name": r.name, "permissions": [{"action": g.action, "folder": g.folder_slug} for g in r.grants]} for r in db.scalars(select(Role).order_by(Role.name)).all()]


@router.post("/api/admin/roles", status_code=201)
def create_role(payload: RolePayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    if payload.name.strip().lower() == "administrateur":
        raise HTTPException(422, "Ce rôle est réservé au système")
    for p in payload.permissions:
        if p.action not in ACTIONS or p.folder not in (None, *SLUGS) or (p.folder and not (p.action.startswith("document.") or p.action in {"completeness.review", "value.write", "impact.review", "quality.review", "requirement.review", "ambiguity.review", "commitment.review"})):
            raise HTTPException(422, "Permission inconnue")
    role = Role(name=payload.name.strip())
    seen = set()
    for p in payload.permissions:
        if (p.action, p.folder) not in seen:
            role.grants.append(RolePermission(action=p.action, folder_slug=p.folder))
            seen.add((p.action, p.folder))
    db.add(role)
    try:
        db.flush()
        audit(db, user, "role.create", "role", role.id, {"name": role.name})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Nom de rôle déjà utilisé")
    return {"id": role.id, "name": role.name}


@router.get("/api/admin/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    return [user_out(u) for u in db.scalars(select(User).order_by(User.name)).all()]


@router.post("/api/admin/users", status_code=201)
def create_user(payload: UserPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    if "@" not in payload.email:
        raise HTTPException(422, "Email invalide")
    roles = [db.get(Role, id_) for id_ in set(payload.role_ids)]
    if not roles or any(r is None for r in roles):
        raise HTTPException(422, "Indiquez au moins un rôle existant")
    new_user = User(name=payload.name.strip(), email=payload.email.strip().lower(), password_hash=hash_password(payload.password), roles=roles)
    db.add(new_user)
    try:
        db.flush()
        audit(db, user, "user.create", "user", new_user.id, {"roles": [r.name for r in roles]})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Un compte utilise déjà cette adresse")
    return user_out(new_user)


@router.get("/api/admin/audit")
def list_audit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(100)).all()
    return [{"id": x.id, "action": x.action, "actor_id": x.actor_id, "target_type": x.target_type, "target_id": x.target_id, "detail": json.loads(x.detail), "occurred_at": x.occurred_at.isoformat()} for x in rows]
