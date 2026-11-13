"""Failed business transactions must clean blobs through the same storage owner."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func,select
from test_partners import app,setup,organization,post,H
from app import document_storage,quality_routes
from app.core import SessionLocal
from app.models import DocumentVersion


@pytest.mark.parametrize('surface',['launch','order','version'])
def test_failed_transaction_keeps_historical_bytes_and_removes_new_blob(tmp_path,monkeypatch,surface):
    private=tmp_path/'files';private.mkdir();historical=private/'historical';historical.write_bytes(b'Existing bytes')
    monkeypatch.setattr(document_storage,'STORAGE',private)
    monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE','disabled')
    with TestClient(app) as client:
        lid=setup(client);path=f'/api/launches/{lid}/documents';payload={'folder':'jaune','title':'Rollback'}
        expected_versions=0
        if surface=='order':
            cid=organization(client,'Storage client','client')
            order=post(client,'/api/orders',{'client_id':cid,'reference':'STORAGE-ROLLBACK'})
            path=f'/api/orders/{order["id"]}/documents'
        elif surface=='version':
            original=client.post(path,data=payload,files={'file':('original.txt',b'Original document','text/plain')},headers=H)
            assert original.status_code==201,original.text
            path=f'/api/documents/{original.json()["id"]}/versions';payload={};expected_versions=1
        before={p.name:p.read_bytes() for p in private.iterdir()}
        def fail_after_storage(*_):raise HTTPException(503,'Synthetic transaction failure')
        monkeypatch.setattr(quality_routes,'auto_inspect_excel',fail_after_storage)
        response=client.post(path,data=payload,files={'file':('new.txt',b'New document','text/plain')},headers=H)
        assert response.status_code==503,response.text
        assert {p.name:p.read_bytes() for p in private.iterdir()}==before
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(DocumentVersion))==expected_versions
