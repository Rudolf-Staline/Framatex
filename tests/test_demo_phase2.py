import os,subprocess,sys,sqlite3,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_seed_entrypoints_guard_idempotence_and_real_partner_data(tmp_path):
    env={**os.environ,'FRAMATEX_DATA_DIR':str(tmp_path),'FRAMATEX_MODE':'DEMO','FRAMATEX_DEMO_PASSWORD':'Demo-Test-Password-2026!','FRAMATEX_SECRET_KEY':'demo-test-secret-'*5}
    env.pop('DATABASE_URL',None)
    def run(*args,environment=env):
        return subprocess.run([sys.executable,*args],cwd=ROOT,env=environment,capture_output=True,text=True,timeout=90)
    for module in ('seed_demo','seed_completeness_demo','seed_workflow_demo','seed_quality_demo','seed_phase2_demo'):
        rejected=run('-m','app.'+module,environment={**env,'FRAMATEX_MODE':'PRODUCTION'})
        assert rejected.returncode!=0 and 'refus' in rejected.stderr.lower()
    first=run('-m','app.seed_phase2_demo');assert first.returncode==0,first.stderr
    def snapshot():
        with sqlite3.connect(tmp_path/'framat.db') as db:
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {name:db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in names}
    before=snapshot();second=run('-m','app.seed_phase2_demo');assert second.returncode==0,second.stderr
    assert snapshot()==before
    assert before['partners']==4 and before['partner_accounts']==4 and before['partner_deliveries']==8
    assert before['quality_decisions']==0 and before['cross_document_rules']>=1 and before['document_reviews']>=3
    with sqlite3.connect(tmp_path/'framat.db') as db:
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        for disk,sha in db.execute('SELECT disk_name,sha256 FROM document_versions'):
            assert hashlib.sha256((tmp_path/'files'/disk).read_bytes()).hexdigest()==sha
    # Exercise the actual API against the seeded, isolated database.
    probe=run('-c', '''
import os
from fastapi.testclient import TestClient
from app.main import app
H={'X-Framatex-Request':'1'}
with TestClient(app) as supplier,TestClient(app) as client,TestClient(app) as admin:
 for c,email in [(supplier,'demo-supplier-a@example.local'),(client,'demo-client-a@example.local'),(admin,'demo-admin@example.local')]:
  path='/api/auth/login' if c is admin else '/api/partner-auth/login'
  assert c.post(path,json={'email':email,'password':os.environ['FRAMATEX_DEMO_PASSWORD']},headers=H).status_code==200
 lines=supplier.get('/api/partner/order-lines').json()
 assert len(lines)==1 and float(lines[0]['received'])==35 and float(lines[0]['remaining'])==65
 orders=client.get('/api/partner/client-orders').json()
 assert len(orders)==1 and orders[0]['reference']=='CMD-DEMO-001' and orders[0]['progress_percent'] is None
 pubs=client.get('/api/partner/publications').json();assert len(pubs)==1
 assert client.get('/api/partner/publications/'+pubs[0]['id']+'/download').content.startswith(b'Fiche client fictive')
 for launch in admin.get('/api/launches').json():
  if launch['order_ref']=='CMD-DEMO-002':assert admin.get('/api/launches/'+launch['id']+'/quality').json()['counts']['difference']==1
''')
    assert probe.returncode==0,probe.stderr
