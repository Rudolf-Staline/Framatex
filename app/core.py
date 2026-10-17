from __future__ import annotations

import os
import secrets
import time
from threading import Lock
from datetime import datetime, timezone, timedelta
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("FRAMATEX_DATA_DIR", str(ROOT / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'framat.db'}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db


def secret_key() -> str:
    env = os.getenv("FRAMATEX_SECRET_KEY")
    if env:
        if len(env) < 32:
            raise RuntimeError("FRAMATEX_SECRET_KEY doit contenir au moins 32 caractères")
        return env
    path = DATA_DIR / ".session_secret"
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write(secrets.token_urlsafe(48))
    return path.read_text().strip()

SECRET_KEY = secret_key()
PASSWORDS = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)
COOKIE = "framat_session"

# Local pilot protection against repeated password guesses. This deliberately
# remains process-local; a production multi-worker setup needs a shared store.
_LOGIN_FAILURES: dict[tuple[str, str], list[float]] = {}
_LOGIN_FAILURE_LOCK = Lock()
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5


def login_limit_key(ip: str, email: str) -> tuple[str, str]:
    # Do not trust X-Forwarded-For unless a trusted proxy is configured.
    return (ip, email.strip().lower()[:254])


def login_attempt_allowed(key: tuple[str, str]) -> bool:
    current = time.monotonic()
    with _LOGIN_FAILURE_LOCK:
        recent = [t for t in _LOGIN_FAILURES.get(key, ()) if t > current - LOGIN_WINDOW_SECONDS]
        if recent:
            _LOGIN_FAILURES[key] = recent
        else:
            _LOGIN_FAILURES.pop(key, None)
        return len(recent) < LOGIN_MAX_FAILURES


def record_login_failure(key: tuple[str, str]):
    current = time.monotonic()
    with _LOGIN_FAILURE_LOCK:
        # Bound the number of tracked pairs to limit memory abuse.
        if len(_LOGIN_FAILURES) > 4000:
            for pair, times in list(_LOGIN_FAILURES.items()):
                if all(t < current - LOGIN_WINDOW_SECONDS for t in times):
                    _LOGIN_FAILURES.pop(pair, None)
        if len(_LOGIN_FAILURES) <= 5000 or key in _LOGIN_FAILURES:
            _LOGIN_FAILURES.setdefault(key, []).append(current)


def clear_login_failures(key: tuple[str, str]):
    with _LOGIN_FAILURE_LOCK:
        _LOGIN_FAILURES.pop(key, None)


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise HTTPException(422, "Le mot de passe doit contenir entre 12 et 256 caractères")
    return PASSWORDS.hash(password)


def check_password(digest: str, plain: str) -> bool:
    try:
        return PASSWORDS.verify(digest, plain)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def make_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "iat": now, "exp": now + timedelta(hours=8)}, SECRET_KEY, algorithm="HS256")


def utcnow():
    return datetime.now(timezone.utc)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    from .models import User
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Connexion nécessaire")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = db.get(User, payload["sub"])
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(401, "Session expirée ou invalide")
    if not user or not user.active:
        raise HTTPException(401, "Compte désactivé")
    return user
