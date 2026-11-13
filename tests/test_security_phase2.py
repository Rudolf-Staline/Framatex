import os,sys,subprocess,hashlib
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_partners import app,setup,post,H,PWD,organization,activate
from app.core import engine,SessionLocal,COOKIE

def test_employee_access_changes_revoke_sessions_and_preserve_last_administrator():
    with TestClient(app) as admin,TestClient(app) as employee:
        setup(admin)
        roles=admin.get('/api/admin/roles').json();admin_role=next(r['id'] for r in roles if r['name']=='Administrateur')
        role=post(admin,'/api/admin/roles',{'name':'Lecture seule','permissions':[{'action':'launch.read'}]})
        user=post(admin,'/api/admin/users',{'name':'Collaborateur','email':'employee-security@sample.local','password':PWD,'role_ids':[role['id']]})
        post(employee,'/api/auth/login',{'email':user['email'],'password':PWD},200)
        cookie=employee.cookies.get(COOKIE)
        path=f'/api/admin/users/{user["id"]}/access';payload={'active':False,'role_ids':[role['id']],'reason':'Départ confirmé du collaborateur'}
        assert employee.patch(path,json=payload,headers=H).status_code==403
        assert admin.patch(path,json=payload,headers=H).status_code==200
        assert employee.get('/api/auth/me').status_code==401
        assert admin.patch(path,json={**payload,'active':True,'password':PWD+'new'},headers=H).status_code==200
        employee.cookies.set(COOKIE,cookie)
        assert employee.get('/api/auth/me').status_code==401  # reactivation cannot revive copied sessions
        post(employee,'/api/auth/login',{'email':user['email'],'password':PWD},401)
        employee.cookies.clear();post(employee,'/api/auth/login',{'email':user['email'],'password':PWD+'new'},200)
        me=admin.get('/api/auth/me').json()
        assert admin.patch(f'/api/admin/users/{me["id"]}/access',json={**payload,'role_ids':[admin_role]},headers=H).status_code==409
        audit=admin.get('/api/admin/audit').text
        invalid=admin.post('/api/admin/users',json={'name':'X','email':'invalid','password':PWD,'role_ids':[]},headers=H)
        assert invalid.status_code==422 and PWD not in invalid.text
        assert PWD not in audit and 'password_hash' not in audit and cookie not in audit
        # Restoration invalidates even a correctly signed cookie with a shared deployment secret.
        with SessionLocal() as db:
            from app.audit import audit as record
            record(db,None,'session.restore','session','all');db.commit()
        assert employee.get('/api/auth/me').status_code==401

def test_foreign_keys_and_rollback_are_enforced_by_sqlite():
    with TestClient(app) as admin:
        setup(admin)
        with engine.connect() as db:assert db.exec_driver_sql('PRAGMA foreign_keys').scalar_one()==1
        with pytest.raises(IntegrityError),engine.begin() as db:
            db.execute(text("INSERT INTO business_orders(id,client_id,reference,created_by,created_at) VALUES ('orphan','missing','TEST','missing','2026-01-01')"))
        with engine.connect() as db:
            assert db.execute(text("SELECT count(*) FROM business_orders WHERE id='orphan'")).scalar_one()==0
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all()==[]

def test_cookies_cross_origin_denials_and_required_scanner_cover_all_uploads(monkeypatch):
    monkeypatch.setenv('FRAMATEX_COOKIE_SECURE','1')
    with TestClient(app,base_url='https://testserver') as admin,TestClient(app,base_url='https://testserver') as supplier:
        lid=setup(admin)
        response=admin.post('/api/auth/login',json={'email':'admin@sample.local','password':PWD},headers=H)
        assert all(x in response.headers['set-cookie'].lower() for x in ['secure','httponly','samesite=strict'])
        org=organization(admin,'Sécurité');activate(admin,supplier,org,'secure-cookie@sample.local')
        response=supplier.post('/api/partner-auth/login',json={'email':'secure-cookie@sample.local','password':PWD},headers=H)
        assert 'secure' in response.headers['set-cookie'].lower()
        assert admin.post('/api/launches',json={'name':'Cross origin'},headers={'Origin':'https://evil.example'}).status_code==403
        preflight=admin.options('/api/launches',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-Framatex-Request'})
        assert 'access-control-allow-origin' not in preflight.headers
        monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE','required');monkeypatch.delenv('FRAMATEX_SCANNER_COMMAND',raising=False)
        from app.main import STORAGE
        before=set(STORAGE.iterdir())
        for path in [f'/api/launches/{lid}/documents',f'/api/launches/{lid}/intake/preview']:
            r=admin.post(path,data={'folder':'jaune','title':'Refus'},files={'file':('x.txt',b'Texte','text/plain')},headers=H)
            assert r.status_code==503,r.text
        assert set(STORAGE.iterdir())==before
        assert all(not f['documents'] for f in admin.get(f'/api/launches/{lid}').json()['folders'])

def test_secret_creation_is_atomic_across_processes_and_private(tmp_path):
    env={**os.environ,'FRAMATEX_DATA_DIR':str(tmp_path)};env.pop('FRAMATEX_SECRET_KEY',None);env.pop('DATABASE_URL',None)
    command=[sys.executable,'-c','from app.core import SECRET_KEY; import hashlib; print(hashlib.sha256(SECRET_KEY.encode()).hexdigest())']
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:subprocess.run(command,env=env,text=True,capture_output=True,timeout=20),range(6)))
    assert all(r.returncode==0 for r in results)
    assert len({r.stdout.strip() for r in results})==1
    secret=tmp_path/'.session_secret';assert secret.stat().st_mode&0o077==0
    secret.write_text('short')
    assert subprocess.run(command,env=env,capture_output=True,timeout=20).returncode!=0


def test_concurrent_worker_migrations_and_upload_size_cleanup(tmp_path,monkeypatch):
    import sqlite3
    from app.migrate import REVISIONS
    env={**os.environ,'FRAMATEX_DATA_DIR':str(tmp_path),'FRAMATEX_SECRET_KEY':'migration-worker-key-'*4};env.pop('DATABASE_URL',None)
    command=[sys.executable,'-c','from app.migrate import migrate; migrate()']
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:subprocess.run(command,env=env,text=True,capture_output=True,timeout=30),range(4)))
    assert all(r.returncode==0 for r in results),[r.stderr for r in results]
    with sqlite3.connect(tmp_path/'framat.db') as db:
        assert db.execute('SELECT count(*) FROM schema_migrations').fetchone()==(len(REVISIONS),)
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert 'ix_audit_action_target_time' in {r[1] for r in db.execute('PRAGMA index_list(audit_events)')}
    from app import main
    monkeypatch.setattr(main,'MAX_UPLOAD',32)
    with TestClient(app) as admin:
        lid=setup(admin);before=set(main.STORAGE.iterdir())
        r=admin.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Trop grand'},files={'file':('large.txt',b'x'*33,'text/plain')},headers=H)
        assert r.status_code==413 and set(main.STORAGE.iterdir())==before
