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
from sqlalchemy import create_engine,event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("FRAMATEX_DATA_DIR", str(ROOT / "data"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'framat.db'}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
if engine.dialect.name=='sqlite':
    @event.listens_for(engine,'connect')
    def sqlite_integrity(connection,_record):
        cursor=connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=10000')
        cursor.close()
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
        # Publish a fully written key atomically, including simultaneous workers.
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w',dir=DATA_DIR,prefix='.secret-') as file:
            file.write(secrets.token_urlsafe(48));file.flush();os.fsync(file.fileno())
            try:os.link(file.name,path)
            except FileExistsError:pass
    value=path.read_text().strip()
    if len(value)<32:raise RuntimeError('Clé de session locale invalide : au moins 32 caractères requis')
    return value

SECRET_KEY = secret_key()
PASSWORDS = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)
COOKIE = "framat_session"

# Compatibility names retained for old callers; actual attempt budgets are in SQLite.
_LOGIN_FAILURES: dict[tuple[str, str], list[float]] = {}
_LOGIN_FAILURE_LOCK = Lock()
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5


def login_limit_key(ip: str, email: str) -> tuple[str, str]:
    # Do not trust X-Forwarded-For unless a trusted proxy is configured.
    return (ip, email.strip().lower()[:254])


def login_attempt_allowed(key: tuple[str, str]) -> bool:
    from .login_throttle import reserve
    return reserve(key)


def record_login_failure(key: tuple[str, str]):
    # The attempt is reserved before password verification, including concurrent workers.
    pass


def clear_login_failures(key: tuple[str, str]):
    from .login_throttle import clear
    clear(key)


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise HTTPException(422, "Le mot de passe doit contenir entre 12 et 256 caractères")
    return PASSWORDS.hash(password)


def check_password(digest: str, plain: str) -> bool:
    try:
        return PASSWORDS.verify(digest, plain)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def session_generation(db,user_id):
    from .models import AuditEvent
    from sqlalchemy import select
    def latest(action,target):
        return db.scalar(select(AuditEvent.id).where(AuditEvent.action==action,AuditEvent.target_id==target)
            .order_by(AuditEvent.occurred_at.desc(),AuditEvent.id.desc()).limit(1))
    return [latest('session.restore','all'),latest('session.revoke_all',user_id)]


def cookie_secure():
    return os.getenv('FRAMATEX_COOKIE_SECURE')=='1' or os.getenv('FRAMATEX_SECURE_COOKIE')=='1'


def make_token(user_id: str, db:Session) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "iat": now, "exp": now + timedelta(hours=8), "jti": secrets.token_hex(16),
        'generation':session_generation(db,user_id)}, SECRET_KEY, algorithm="HS256")


def utcnow():
    return datetime.now(timezone.utc)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    from .models import User
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Connexion nécessaire")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        session_id = payload.get("jti")
        if not isinstance(session_id, str) or len(session_id) != 32:
            raise HTTPException(401, "Session précédente expirée : veuillez vous reconnecter")
        from .models import AuditEvent
        from sqlalchemy import select
        revoked = db.scalar(select(AuditEvent.id).where(
            AuditEvent.action == "session.logout",
            AuditEvent.target_id == session_id).limit(1))
        if revoked is not None:
            raise HTTPException(401, "Session révoquée : veuillez vous reconnecter")
        if payload.get('generation',[None,None])!=session_generation(db,payload['sub']):
            raise HTTPException(401,'Session révoquée après modification des accès ou restauration')
        user = db.get(User, payload["sub"])
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(401, "Session expirée ou invalide")
    if not user or not user.active:
        raise HTTPException(401, "Compte désactivé")
    return user
