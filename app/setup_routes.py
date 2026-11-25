"""Opt-in first installation, never an account recovery endpoint."""
from __future__ import annotations

import json
import os
import re
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from .client_models import ClientAccount
from .core import ROOT, SessionLocal, hash_password
from .models import AuditEvent, Role, User

router = APIRouter(include_in_schema=False)


def configured_secret():
    # No default, no fallback to a session secret. Opt-in on each installation.
    secret = os.environ.get("FRAMATEX_SETUP_SECRET", "")
    return secret if len(secret) >= 32 else None


def closed():
    return HTTPException(404, "Installation indisponible")


def pristine(db):
    # Even a disabled user or a prior audit trail closes installation.
    # This endpoint must never be used for account recovery.
    return all(db.scalar(select(model.id).limit(1)) is None
               for model in (User, ClientAccount, AuditEvent))


@router.get("/setup")
def setup_page():
    if not configured_secret():
        raise closed()
    with SessionLocal() as db:
        if not pristine(db):
            raise closed()
    return FileResponse(ROOT / "app" / "setup_page.html",
                        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


def initialize(name, email, password):
    with SessionLocal() as db:
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            # Serialize against ordinary inserts, not just other /setup calls.
            # Table names are resolved in the app's private search_path.
            db.execute(text("LOCK TABLE users, client_accounts, audit_events, roles, user_roles "
                            "IN SHARE ROW EXCLUSIVE MODE"))
        elif dialect == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        else:
            raise closed()
        if not pristine(db):
            raise closed()
        role = db.scalar(select(Role).where(Role.name == "Administrateur"))
        if role is None:
            role = Role(name="Administrateur")
        user = User(name=name, email=email, password_hash=hash_password(password),
                    active=True, roles=[role])
        db.add(user)
        try:
            db.flush()
            db.add(AuditEvent(action="installation.completed", actor_id=user.id,
                              target_type="user", target_id=user.id,
                              detail=json.dumps({"source": "first_installation"})))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise closed()
    return {"ok": True}


@router.post("/api/setup", status_code=201)
async def setup(request: Request):
    secret = configured_secret()
    token = request.headers.get("X-Framatex-Setup-Token", "")
    if not secret or not secrets.compare_digest(token.encode(), secret.encode()):
        raise closed()
    if request.headers.get("X-Framatex-Request") != "1":
        raise HTTPException(403, "En-tête de protection manquant")
    # Do not use automatic validation here: validation errors must never echo
    # submitted passwords. Bound the body even if Content-Length is absent.
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > 8192:
            raise HTTPException(413, "Requête trop volumineuse")
        data.extend(chunk)
    try:
        body = json.loads(data)
        name, email, password = (body[key] for key in ("name", "email", "password"))
        if not all(isinstance(value, str) for value in (name, email, password)):
            raise ValueError()
        name, email = name.strip(), email.strip().lower()
        if (not 2 <= len(name) <= 120 or len(email) > 254
                or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
                or not 12 <= len(password) <= 256):
            raise ValueError()
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise HTTPException(422, "Nom, email ou mot de passe invalide") from None
    return await run_in_threadpool(initialize, name, email, password)
