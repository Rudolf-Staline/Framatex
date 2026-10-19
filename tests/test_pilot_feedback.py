"""0.17: controlled feedback, session revocation, migration and privacy."""
from uuid import uuid4
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select, text, create_engine, inspect
from app.main import app
from app.core import COOKIE, SessionLocal, hash_password, Base, engine
from app.models import Role, RolePermission, User, AuditEvent

H = {'X-Framatex-Request':'1'}
PASSWORD = 'PiloteQualite2026!'


def setup_users():
    Base.metadata.create_all(engine)
    tag=uuid4().hex[:10]
    with SessionLocal() as db:
        admin_role = db.scalar(select(Role).where(Role.name=='Administrateur'))
        if admin_role is None:
            admin_role = Role(name='Administrateur'); db.add(admin_role)
        worker_role = Role(name=f'Pilote recettant {tag}', grants=[RolePermission(action='launch.read')])
        admin = User(name='Coordination pilote', email=f'admin-{tag}@test.invalid', password_hash=hash_password(PASSWORD), roles=[admin_role])
        worker = User(name='Opérateur pilote', email=f'worker-{tag}@test.invalid', password_hash=hash_password(PASSWORD), roles=[worker_role])
        outsider = User(name='Tiers pilote', email=f'outsider-{tag}@test.invalid', password_hash=hash_password(PASSWORD), roles=[worker_role])
        db.add_all([worker_role, admin, worker, outsider]); db.commit()
        return {name:f'{name}-{tag}@test.invalid' for name in ('admin','worker','outsider')}, {'worker':worker.id,'outsider':outsider.id}


def login(client, email):
    r=client.post('/api/auth/login', headers=H, json={'email':email,'password':PASSWORD})
    assert r.status_code==200,r.text
    return client.cookies.get(COOKIE)


def report(launch_id=None):
    return {'title':'La pièce ne s’affiche pas après dépôt', 'module':'Documents et versions',
            'steps':'1. Ouvrir un lancement fictif. 2. Déposer une pièce. 3. Recharger la page.',
            'expected':'La pièce est visible dans le dossier.',
            'observed':'Le tableau reste vide après actualisation.',
            'severity':'majeur', 'launch_id':launch_id}


def test_feedback_lifecycle_triage_and_cross_user_privacy():
    emails, ids=setup_users()
    with TestClient(app) as c:
        login(c,emails['admin'])
        r=c.post('/api/launches',headers=H,json={'name':'Recette pilote privée'})
        assert r.status_code==201;r_id=r.json()['id']
        assert c.put(f'/api/launches/{r_id}/access',headers=H,json={'restricted':True}).status_code==200
        assert c.post(f'/api/launches/{r_id}/access/members',headers=H,json={'user_id':ids['worker']}).status_code==201
        login(c,emails['worker'])
        creation=c.post('/api/pilot/reports',headers=H,json=report(r_id))
        assert creation.status_code==201,creation.text
        rid=creation.json()['id']
        assert creation.json()['status']=='ouvert'
        assert len(c.get('/api/pilot/reports').json())==1
        assert c.patch(f'/api/pilot/reports/{rid}',headers=H,json={'status':'resolu','resolution_note':'Erreur corrigée par changement d’interface.'}).status_code==403
        login(c,emails['outsider'])
        assert c.post('/api/pilot/reports',headers=H,json=report(r_id)).status_code==404
        assert c.get('/api/pilot/reports').json()==[]
        login(c,emails['admin'])
        assert c.patch(f'/api/pilot/reports/{rid}',headers=H,json={'status':'resolu','resolution_note':'Trop court'}).status_code==422
        fix=c.patch(f'/api/pilot/reports/{rid}',headers=H,json={'status':'resolu','resolution_note':'Le problème a été reproduit puis corrigé en version pilote.'})
        assert fix.status_code==200 and fix.json()['status']=='resolu'
        assert len(c.get('/api/pilot/reports').json())==1
        assert c.delete(f'/api/launches/{r_id}/access/members/{ids["worker"]}',headers=H).status_code==200
        login(c,emails['worker'])
        assert c.get('/api/pilot/reports').json()==[]
        assert c.post('/api/pilot/reports',headers=H,json=report(r_id)).status_code==404
        # A general non-scoped UX report remains available to the reporter.
        generic=c.post('/api/pilot/reports',headers=H,json=report(None))
        assert generic.status_code==201
        assert len(c.get('/api/pilot/reports').json())==1


def test_logout_revokes_copied_cookie_and_login_creates_new_session():
    emails, _=setup_users()
    with TestClient(app) as c:
        cookie=login(c,emails['admin'])
        assert c.get('/api/auth/me').status_code==200
        logout=c.post('/api/auth/logout',headers=H)
        assert logout.status_code==200
        with TestClient(app,cookies={COOKIE:cookie}) as old:
            assert old.get('/api/auth/me').status_code==401
            assert old.get('/api/launches').status_code==401
        new_cookie=login(c,emails['admin'])
        assert new_cookie!=cookie
        assert c.get('/api/auth/me').status_code==200
        with SessionLocal() as db:
            rows=db.scalars(select(AuditEvent).where(AuditEvent.action=='session.logout')).all()
            assert rows


def test_old_pilot_schema_upgrade_keeps_data_and_makes_backup(tmp_path, monkeypatch):
    from app import migrate as migrations
    db_path=tmp_path/'legacy0.16.sqlite'
    legacy=create_engine('sqlite:///'+str(db_path))
    Base.metadata.create_all(legacy)
    with legacy.begin() as conn:
        conn.execute(text('DROP TABLE pilot_reports'))
        conn.execute(text('DELETE FROM schema_migrations'))
        for revision in ('0001_baseline','0002_launch_scope'):
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :date)'),{'v':revision,'date':'2026-10-17'})
        conn.execute(text("INSERT INTO users(id,email,name,password_hash,active,created_at) VALUES ('u1','old@example.local','Ancien','x',1,'2026-10-17')"))
    monkeypatch.setattr(migrations,'engine',legacy)
    migrations.migrate()
    migrations.migrate()
    with legacy.connect() as conn:
        assert 'pilot_reports' in inspect(conn).get_table_names()
        assert conn.execute(text("SELECT name FROM users WHERE id='u1'")).scalar_one()=='Ancien'
        assert [v for v, in conn.execute(text('SELECT version FROM schema_migrations ORDER BY version'))]==list(migrations.REVISIONS)
    assert len(list(tmp_path.glob('legacy0.16.sqlite.backup-*')))==1
    legacy.dispose()


def test_pilot_frontend_is_discoverable_and_data_is_escaped():
    root=Path(__file__).resolve().parents[1]
    app_js=(root/'static/app.js').read_text()
    pilot_js=(root/'static/pilot.js').read_text()
    index=(root/'static/index.html').read_text()
    assert 'Signaler un problème' in app_js and "await pilotPage()" in app_js
    assert 'pilot.js' in index
    assert "${e(r.title)}" in pilot_js
    assert "${e(r.steps)}" in pilot_js
    assert "${e(r.observed)}" in pilot_js
