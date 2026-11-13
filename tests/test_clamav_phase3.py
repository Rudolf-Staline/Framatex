"""Real engine with a synthetic EICAR-only database, never a full AV coverage claim."""
import hashlib
import shutil
import pytest
from fastapi.testclient import TestClient
from test_partners import app,setup,H
from app.document_storage import STORAGE

@pytest.mark.skipif(not shutil.which('clamscan'),reason='ClamAV executable required; installed explicitly in CI')
def test_real_clamav_eicar_clean_restart_and_missing_database(tmp_path,monkeypatch):
    binary=shutil.which('clamscan')
    eicar=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    database=tmp_path/'synthetic.hdb'
    database.write_text(f'{hashlib.md5(eicar).hexdigest()}:{len(eicar)}:Eicar-Test-Signature\n')
    monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE','required')
    monkeypatch.setenv('FRAMATEX_SCANNER_BACKEND','clamav')
    import shlex
    monkeypatch.setenv('FRAMATEX_SCANNER_COMMAND',f'{shlex.quote(binary)} --no-summary --database={shlex.quote(str(database))}')
    with TestClient(app) as c:
        lid=setup(c);before=set(STORAGE.iterdir())
        def upload(data):
            return c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Antivirus'},files={'file':('test.txt',data,'text/plain')},headers=H)
        refused=upload(eicar);assert refused.status_code==422,refused.text
        assert set(STORAGE.iterdir())==before
        for _ in range(2):assert upload(b'Document synthetique sain').status_code==201
        # Every scan starts a fresh process; no cached clean result after restart.
        assert upload(eicar).status_code==422
        database.unlink();before=set(STORAGE.iterdir())
        assert upload(b'Document synthetique sain').status_code==503
        assert set(STORAGE.iterdir())==before
