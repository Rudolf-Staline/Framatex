import sqlite3,hashlib
from fastapi.testclient import TestClient
from test_partners import app,setup,post,organization,activate,H
from app.backup import backup,restore
from app.core import DATA_DIR

def test_backup_restores_partner_files_history_and_revokes_sessions(tmp_path):
    with TestClient(app) as staff,TestClient(app) as supplier:
        lid=setup(staff);org=organization(staff,'Sauvegarde fournisseur')
        activate(staff,supplier,org,'backup-partner@sample.local')
        rid=post(staff,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-BACKUP','title':'Certificat','doc_type':'Certificat'})['id']
        requests=[('/api/partner/administrative-documents',{'title':'Attestation'}),
                  (f'/api/partner/requests/{rid}/attachments',{'message':'Pièce jointe privée'}),
                  (f'/api/partner/requests/{rid}/versions',{})]
        for endpoint,data in requests:
            r=supplier.post(endpoint,data=data,files={'file':('fichier.txt',b'Donnees privees fictives','text/plain')},headers=H)
            assert r.status_code==201,r.text
        archive=backup(DATA_DIR,tmp_path/'complete.zip');target=restore(archive,tmp_path/'restored')
        with sqlite3.connect(target/'framat.db') as db:
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            for table in ['partner_administrative_documents','partner_attachments','partner_submissions']:
                rows=db.execute(f'SELECT disk_name,sha256 FROM {table}').fetchall();assert len(rows)==1
                for disk,sha in rows:assert hashlib.sha256((target/'files'/disk).read_bytes()).hexdigest()==sha
            assert db.execute('SELECT count(*) FROM partner_tokens WHERE consumed=0').fetchone()==(0,)
            assert db.execute("SELECT count(*) FROM audit_events WHERE action='session.restore'").fetchone()==(1,)
            assert db.execute('SELECT request_id FROM partner_submissions').fetchone()==(rid,)
        assert archive.stat().st_mode&0o077==0
