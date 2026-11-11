"""Cross-worker private storage budget. Never block an async worker on another upload."""
from contextlib import contextmanager
import fcntl
import os
from fastapi import HTTPException


@contextmanager
def upload_budget(storage):
    fd=os.open(storage.parent/'.upload-budget.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise HTTPException(409,'Un dépôt est déjà en cours. Réessayez après sa fin.')
        try:quota=int(os.getenv('FRAMATEX_STORAGE_QUOTA_BYTES',str(1024*1024*1024)))
        except ValueError:raise HTTPException(503,'Configuration du quota de stockage invalide')
        if quota<1:raise HTTPException(503,'Quota de stockage indisponible')
        used=0
        for path in storage.iterdir():
            try:
                if path.is_file():used+=path.stat().st_size
            except FileNotFoundError:continue
        yield max(0,quota-used)
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
