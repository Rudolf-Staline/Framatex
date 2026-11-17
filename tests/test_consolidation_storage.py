"""Cross-process quota safety, quarantine and restart recovery, synthetic only."""
import asyncio
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException, UploadFile
os.environ.setdefault('FRAMATEX_DATA_DIR', tempfile.mkdtemp(prefix='framat-storage-'))
os.environ.setdefault('FRAMATEX_SECRET_KEY', 'storage-tests-' * 5)
from app import document_storage
from app.storage_budget import Reservation, reconcile, upload_budget


@pytest.fixture
def storage(tmp_path, monkeypatch):
    path = tmp_path / 'files'; path.mkdir()
    monkeypatch.setattr(document_storage, 'STORAGE', path)
    monkeypatch.setenv('FRAMATEX_STORAGE_QUOTA_BYTES', '64')
    monkeypatch.setenv('FRAMATEX_UPLOAD_CONCURRENCY', '2')
    monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE', 'disabled')
    monkeypatch.setattr(document_storage, 'verify_file', lambda *_: None)
    return path


def upload(data):
    return asyncio.run(document_storage.store_upload(UploadFile(io.BytesIO(data), size=len(data), filename='sample.txt')))


def test_two_uploads_validate_concurrently_and_stay_quarantined(storage, monkeypatch):
    barrier = threading.Barrier(2)
    def scan(path):
        assert path.parent.name == '.upload-quarantine'
        assert path.read_bytes() in (b'a'*16, b'b'*16)
        assert not list(storage.iterdir())
        barrier.wait(timeout=5)
    monkeypatch.setattr(document_storage, 'scan', scan)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(upload, (b'a'*16, b'b'*16)))
    assert {r[2] for r in results} == {16}
    assert len(list(storage.iterdir())) == 2
    assert not list((storage.parent / '.upload-quarantine').iterdir())
    assert reconcile(storage)['bytes'] == 32


def test_atomic_quota_and_slot_limit_cross_process(storage, monkeypatch):
    monkeypatch.setenv('FRAMATEX_STORAGE_QUOTA_BYTES', '16')
    first = Reservation(storage, 'first', 12)
    script = '''
import sys
from fastapi import HTTPException
from app.storage_budget import Reservation
try:
    Reservation(sys.argv[1], 'second', 12)
except HTTPException as exc:
    print(exc.status_code)
'''
    result = subprocess.run([sys.executable, '-c', script, str(storage)], text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '413'
    first.release()
    monkeypatch.setenv('FRAMATEX_UPLOAD_CONCURRENCY', '1')
    with upload_budget(storage, 'first', 1):
        with pytest.raises(HTTPException) as error:
            Reservation(storage, 'second', 1)
        assert error.value.status_code == 429
    assert reconcile(storage)['bytes'] == 0


def test_failure_and_business_rollback_release_quota(storage, monkeypatch):
    def unavailable(_):
        raise HTTPException(503, 'Synthetic scanner unavailable')
    monkeypatch.setattr(document_storage, 'scan', unavailable)
    with pytest.raises(HTTPException) as error:
        upload(b'x'*32)
    assert error.value.status_code == 503
    assert list(storage.iterdir()) == []
    assert not list((storage.parent / '.upload-quarantine').iterdir())
    monkeypatch.setattr(document_storage, 'scan', lambda _: None)
    result = upload(b'x'*64)
    document_storage.remove_blob(result[1])
    assert upload(b'y'*64)[2] == 64


def test_abandoned_reservation_recovered_without_deleting_original(storage):
    abandoned = Reservation(storage, 'not-published', 64)
    abandoned.path.write_bytes(b'partial')
    (storage / 'historical').write_bytes(b'original')
    report = reconcile(storage, referenced={'historical'}, now=time.time()+1000)
    assert report['expired_reservations'] == 1
    assert report['unreferenced_files'] == []
    assert not abandoned.path.exists()
    assert (storage / 'historical').read_bytes() == b'original'
    abandoned.release()
    assert upload(b'x'*56)[2] == 56


def test_restart_rebuilds_ledger_and_only_reports_orphans(storage):
    (storage / 'historical').write_bytes(b'history')
    (storage / 'orphan').write_bytes(b'never linked')
    report = reconcile(storage, referenced={'historical', 'missing'})
    assert report['unreferenced_files'] == ['orphan']
    assert report['missing_files'] == ['missing']
    assert report['bytes'] == 19
    with pytest.raises(HTTPException) as error:
        upload(b'x'*46)
    assert error.value.status_code == 413
    assert (storage / 'historical').read_bytes() == b'history'
    assert (storage / 'orphan').read_bytes() == b'never linked'


def test_required_unavailable_scanner_never_publishes(storage, monkeypatch):
    monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE', 'required')
    monkeypatch.setenv('FRAMATEX_SCANNER_COMMAND', '/does/not/exist')
    with pytest.raises(HTTPException) as error:
        upload(b'synthetic')
    assert error.value.status_code == 503
    assert not list(storage.iterdir())
    assert not list((storage.parent / '.upload-quarantine').iterdir())


@pytest.mark.parametrize('surface', ['launch', 'version'])
def test_revocation_during_scan_rejects_upload_and_releases_quota(storage, monkeypatch, surface):
    from fastapi.testclient import TestClient
    from sqlalchemy import select, func
    from test_partners import app, setup, H
    from app.core import SessionLocal
    from app.models import User, DocumentVersion
    with TestClient(app) as client:
        launch_id = setup(client)
        path = f'/api/launches/{launch_id}/documents'
        payload = {'folder': 'jaune', 'title': 'Synthetic revocation'}
        expected = 0
        if surface == 'version':
            response = client.post(path, data=payload, files={'file': ('base.txt', b'base', 'text/plain')}, headers=H)
            assert response.status_code == 201, response.text
            path = f'/api/documents/{response.json()["id"]}/versions'; payload = {}; expected = 1
        def revoke(_path):
            with SessionLocal() as db:
                actor = db.scalar(select(User).where(User.email == 'admin@sample.local'))
                actor.active = False; db.commit()
        monkeypatch.setattr(document_storage, 'scan', revoke)
        result = client.post(path, data=payload, files={'file': ('new.txt', b'new', 'text/plain')}, headers=H)
        assert result.status_code == 401, result.text
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(DocumentVersion)) == expected
        assert reconcile(storage)['bytes'] == (4 if expected else 0)


def test_crash_between_publication_link_and_accounting_preserves_quota(storage):
    abandoned = Reservation(storage, 'linked-before-crash', 64)
    abandoned.path.write_bytes(b'x'*64)
    os.link(abandoned.path, storage / abandoned.name)
    # Simulate restarting after its lease expired, without a successful commit.
    with sqlite3.connect(storage.parent / '.storage-budget.sqlite3') as db:
        db.execute('UPDATE reservations SET expires=0')
    with pytest.raises(HTTPException) as error:
        Reservation(storage, 'second', 1)
    assert error.value.status_code == 413
    assert (storage / abandoned.name).read_bytes() == b'x'*64
    assert not abandoned.path.exists()


def test_completed_uploads_do_not_rescan_the_file_corpus(storage, monkeypatch):
    calls = []
    original = Path.iterdir
    def counted(path):
        if path == storage:
            calls.append(path)
        return original(path)
    monkeypatch.setattr(Path, 'iterdir', counted)
    upload(b'first'); upload(b'second'); upload(b'third')
    assert len(calls) == 1  # First-use rebuild only; subsequent budgets use counters.


def test_unknown_size_is_reserved_before_writing_and_low_disk_refuses(storage, monkeypatch):
    unknown = UploadFile(io.BytesIO(b'x'*65), filename='unknown.txt')
    with pytest.raises(HTTPException) as error:
        asyncio.run(document_storage.store_upload(unknown))
    assert error.value.status_code == 413
    assert not list(storage.iterdir())
    from app import storage_budget
    monkeypatch.setattr(storage_budget.shutil, 'disk_usage', lambda _: type('Usage', (), {'free': 8})())
    monkeypatch.setenv('FRAMATEX_STORAGE_MIN_FREE_BYTES', '8')
    with pytest.raises(HTTPException) as error:
        upload(b'a')
    assert error.value.status_code == 507
    assert not list(storage.iterdir())


def test_cancelled_request_releases_quarantine_and_reservation(storage, monkeypatch):
    started, resume = threading.Event(), threading.Event()
    def paused_check(_path, _suffix):
        started.set()
        assert resume.wait(timeout=5)
    monkeypatch.setattr(document_storage, 'verify_file', paused_check)
    async def interrupted():
        task = asyncio.create_task(document_storage.store_upload(UploadFile(io.BytesIO(b'synthetic'), size=9, filename='cancelled.txt')))
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=2)
        finally:
            resume.set()
    asyncio.run(interrupted())
    assert not list(storage.iterdir())
    assert not list((storage.parent / '.upload-quarantine').iterdir())
    with sqlite3.connect(storage.parent / '.storage-budget.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM reservations').fetchone()[0] == 0
