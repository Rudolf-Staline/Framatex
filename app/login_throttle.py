"""Database-backed fixed-window throttle shared by local workers.
Reserves an attempt before Argon2 work, so concurrent requests cannot bypass the
limit. Success clears the bucket; a rejected login keeps its reservation.
"""
import hashlib
import json
import time
from sqlalchemy import select,delete,update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from .core import SessionLocal
from .partner_phase2_models import LoginBucket

WINDOW=300
LIMIT=5

def digest(key):return hashlib.sha256(json.dumps(key).encode()).hexdigest()

def reserve(key):
    now=int(time.time());hashed=digest(key)
    with SessionLocal() as db:
        db.execute(delete(LoginBucket).where(LoginBucket.window_start<=now-WINDOW))
        insert=sqlite_insert if db.bind.dialect.name=='sqlite' else postgres_insert
        db.execute(insert(LoginBucket).values(key=hashed,window_start=now,failures=0).on_conflict_do_nothing(index_elements=['key']))
        result=db.execute(update(LoginBucket).where(LoginBucket.key==hashed,LoginBucket.failures<LIMIT).values(failures=LoginBucket.failures+1))
        db.commit();return result.rowcount==1

def clear(key):
    with SessionLocal() as db:
        db.execute(delete(LoginBucket).where(LoginBucket.key==digest(key)));db.commit()
