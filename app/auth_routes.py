"""Employee login, logout and current-session HTTP endpoints."""
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import (COOKIE, get_current_user, get_db, check_password, make_token,
                   login_limit_key, login_attempt_allowed, record_login_failure, clear_login_failures)
from .models import User
from .audit import audit
from .employees import user_out

router = APIRouter()

class LoginPayload(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=1,max_length=256)


@router.post("/api/auth/login")
def login(payload: LoginPayload, response: Response, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    key = login_limit_key(ip, payload.email)
    if not login_attempt_allowed(key):
        raise HTTPException(429, "Trop de tentatives : réessayez dans quelques minutes")
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not user.active or not check_password(user.password_hash, payload.password):
        record_login_failure(key)
        raise HTTPException(401, "Identifiants incorrects")
    clear_login_failures(key)
    from .core import cookie_secure
    response.set_cookie(COOKIE, make_token(user.id,db), max_age=8*3600, httponly=True, secure=cookie_secure(), samesite="strict", path="/")
    audit(db, user, "session.login", "user", user.id)
    db.commit()
    return user_out(user)


@router.post("/api/auth/logout")
def logout(response: Response, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Deleting a cookie alone does not invalidate a copied signed JWT.
    # Record its unique identifier server-side so reuse is denied immediately.
    import jwt
    from .core import SECRET_KEY
    token = request.cookies.get(COOKIE)
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    audit(db, user, "session.logout", "session", payload["jti"])
    db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    perms = [{"action": g.action, "folder": g.folder_slug} for r in user.roles for g in r.grants]
    return {**user_out(user), "permissions": perms}
