"""Short, cross-process quota reservations; no lock is held during file checks.

The sidecar is derived accounting, rebuilt on first use after a restore. Only the
explicit reconciliation command scans stored files after initialization.
"""
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
import os
import sqlite3
import shutil
import time
import uuid
from fastapi import HTTPException


def _settings():
    try:
        quota = int(os.getenv('FRAMATEX_STORAGE_QUOTA_BYTES', str(1024**3)))
        concurrent = int(os.getenv('FRAMATEX_UPLOAD_CONCURRENCY', '4'))
        lease = int(os.getenv('FRAMATEX_UPLOAD_LEASE_SECONDS', '900'))
        minimum_free = int(os.getenv('FRAMATEX_STORAGE_MIN_FREE_BYTES', '0'))
        if quota < 1 or minimum_free < 0 or not 1 <= concurrent <= 64 or not 180 <= lease <= 86400:
            raise ValueError()
        return quota, concurrent, lease, minimum_free
    except ValueError:
        raise HTTPException(503, 'Configuration du stockage invalide')


def quarantine(storage):
    path = Path(storage).parent / '.upload-quarantine'
    path.mkdir(mode=0o700, exist_ok=True)
    return path


@contextmanager
def _transaction(storage):
    path = Path(storage).parent / '.storage-budget.sqlite3'
    # Explicit mode at creation prevents the accounting file being world-readable.
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS blobs (name TEXT PRIMARY KEY, size INTEGER NOT NULL CHECK(size >= 0))')
        db.execute('CREATE TABLE IF NOT EXISTS reservations (token TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, size INTEGER NOT NULL CHECK(size >= 0), expires REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        if not db.execute("SELECT 1 FROM metadata WHERE key='initialized'").fetchone():
            db.executemany('INSERT INTO blobs(name,size) VALUES (?,?)',
                           [(p.name, p.stat().st_size) for p in Path(storage).iterdir() if p.is_file()])
            db.execute("INSERT INTO metadata VALUES ('initialized','1')")
        if not db.execute("SELECT 1 FROM metadata WHERE key='used_bytes'").fetchone():
            db.execute("INSERT INTO metadata(key,value) SELECT 'used_bytes',coalesce(sum(size),0) FROM blobs")
        yield db
        db.commit()
    except sqlite3.Error as exc:
        db.rollback()
        raise HTTPException(503, 'Comptabilité du stockage indisponible : réessayez') from exc
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def _expire(db, storage, now):
    expired = list(db.execute('SELECT token,name FROM reservations WHERE expires<=?', (now,)))
    for token, name in expired:
        # A process may die after the link but before committing accounting.
        # Preserve and count those bytes; business references need operator review.
        target = Path(storage) / name
        if target.is_file():
            size = target.stat().st_size
            inserted = db.execute('INSERT OR IGNORE INTO blobs(name,size) VALUES (?,?)', (name, size)).rowcount
            if inserted:
                db.execute("UPDATE metadata SET value=cast(value AS INTEGER)+? WHERE key='used_bytes'", (size,))
        (quarantine(storage) / token).unlink(missing_ok=True)
    db.execute('DELETE FROM reservations WHERE expires<=?', (now,))
    return len(expired)


class Reservation:
    def __init__(self, storage, name, expected=0):
        self.storage, self.name = Path(storage), name
        self.token = uuid.uuid4().hex
        self.path = quarantine(storage) / self.token
        self.finished = False
        self.quota, concurrent, self.lease, self.minimum_free = _settings()
        with _transaction(storage) as db:
            now = time.time()
            _expire(db, storage, now)
            count, reserved = db.execute('SELECT count(*), coalesce(sum(size),0) FROM reservations').fetchone()
            if count >= concurrent:
                raise HTTPException(429, 'Capacité de dépôt occupée : réessayez dans un instant', headers={'Retry-After': '1'})
            used = int(db.execute("SELECT value FROM metadata WHERE key='used_bytes'").fetchone()[0])
            if expected < 0 or used + reserved + expected > self.quota:
                raise HTTPException(413, 'Quota du stockage privé dépassé')
            if shutil.disk_usage(self.storage).free < self.minimum_free + reserved + expected:
                raise HTTPException(507, 'Espace disque disponible insuffisant pour ce dépôt')
            db.execute('INSERT INTO reservations VALUES (?,?,?,?)',
                       (self.token, name, expected, now + self.lease))

    def reserve(self, size):
        """Reserve bytes before writing and renew the lease during streaming."""
        with _transaction(self.storage) as db:
            now = time.time()
            row = db.execute('SELECT size,expires FROM reservations WHERE token=?', (self.token,)).fetchone()
            if not row or row[1] <= now:
                raise HTTPException(409, 'Dépôt expiré : recommencez le dépôt')
            if size > row[0]:
                used = int(db.execute("SELECT value FROM metadata WHERE key='used_bytes'").fetchone()[0])
                reserved = db.execute('SELECT coalesce(sum(size),0) FROM reservations WHERE token<>?', (self.token,)).fetchone()[0]
                if used + reserved + size > self.quota:
                    raise HTTPException(413, 'Quota du stockage privé dépassé')
                if shutil.disk_usage(self.storage).free < self.minimum_free + reserved + size - row[0]:
                    raise HTTPException(507, 'Espace disque disponible insuffisant pour ce dépôt')
            db.execute('UPDATE reservations SET size=?, expires=? WHERE token=?',
                       (max(size, row[0]), now + self.lease, self.token))

    def publish(self, size):
        """Atomically expose checked bytes without overwriting an existing blob."""
        target = self.storage / self.name
        linked = False
        try:
            with _transaction(self.storage) as db:
                row = db.execute('SELECT size,expires FROM reservations WHERE token=?', (self.token,)).fetchone()
                if not row or row[1] <= time.time() or row[0] < size:
                    raise HTTPException(409, 'Dépôt expiré : recommencez le dépôt')
                os.link(self.path, target)
                linked = True
                directory = os.open(self.storage, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
                db.execute('INSERT INTO blobs(name,size) VALUES (?,?)', (self.name, size))
                db.execute("UPDATE metadata SET value=cast(value AS INTEGER)+? WHERE key='used_bytes'", (size,))
                db.execute('DELETE FROM reservations WHERE token=?', (self.token,))
            self.finished = True
        except BaseException:
            if linked:
                target.unlink(missing_ok=True)
            raise
        finally:
            self.path.unlink(missing_ok=True)

    def release(self):
        self.path.unlink(missing_ok=True)
        if not self.finished:
            with _transaction(self.storage) as db:
                db.execute('DELETE FROM reservations WHERE token=?', (self.token,))


@contextmanager
def upload_budget(storage, name, expected=0):
    reservation = Reservation(storage, name, expected)
    try:
        yield reservation
    finally:
        reservation.release()


def remove_blob(storage, name):
    """Release checked bytes after a failed business transaction or preview."""
    if Path(name).name != name:
        raise ValueError('Nom de fichier privé invalide')
    with _transaction(storage) as db:
        (Path(storage) / name).unlink(missing_ok=True)
        row = db.execute('SELECT size FROM blobs WHERE name=?', (name,)).fetchone()
        if row:
            db.execute("UPDATE metadata SET value=cast(value AS INTEGER)-? WHERE key='used_bytes'", (row[0],))
        db.execute('DELETE FROM blobs WHERE name=?', (name,))


def reconcile(storage, *, referenced=None, now=None):
    """Repair derived accounting and report orphan blobs; never delete history.

    Run with writers stopped when comparing with business database references.
    Expired quarantine files can be discarded since they were never published.
    """
    storage = Path(storage)
    with _transaction(storage) as db:
        expired = _expire(db, storage, time.time() if now is None else now)
        files = {p.name: p.stat().st_size for p in storage.iterdir() if p.is_file()}
        db.execute('DELETE FROM blobs')
        db.executemany('INSERT INTO blobs VALUES (?,?)', files.items())
        db.execute("UPDATE metadata SET value=? WHERE key='used_bytes'", (sum(files.values()),))
        active = {r[0] for r in db.execute('SELECT token FROM reservations')}
        discarded = 0
        for path in quarantine(storage).iterdir():
            if path.is_file() and path.name not in active:
                path.unlink(); discarded += 1
        return {'files': len(files), 'bytes': sum(files.values()), 'expired_reservations': expired,
                'discarded_quarantine_files': discarded,
                'unreferenced_files': sorted(set(files) - set(referenced)) if referenced is not None else None,
                'missing_files': sorted(set(referenced) - set(files)) if referenced is not None else None}


@asynccontextmanager
async def upload_reservation(storage, name, expected=0):
    from starlette.concurrency import run_in_threadpool
    reservation = await run_in_threadpool(Reservation, storage, name, expected)
    try:
        yield reservation
    finally:
        await run_in_threadpool(reservation.release)
