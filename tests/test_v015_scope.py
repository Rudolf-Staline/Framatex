"""MVP 0.15 — deny scope to nonmembers on all launch-related endpoints."""
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-scope-')
os.environ['FRAMATEX_SECRET_KEY'] = 'scope-tests-safe-secret-2026-'*2

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core import Base, engine, SessionLocal, hash_password
from app.main import app
from app.models import User, Role, RolePermission
from app.approval_models import InternalNotification

H={'X-Framatex-Request':'1'}
PASSWORD='ScopeTests2026!'


def test_restrictions_cover_listing_indirect_objects_and_legacy_permissions():
    with TestClient(app) as c:
        Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
        with SessionLocal() as db:
            admin_role=Role(name='Administrateur'); worker_role=Role(name='Personnel de reception')
            worker_role.grants += [RolePermission(action='launch.read'),
                 RolePermission(action='document.read',folder_slug='rose'),
                 RolePermission(action='document.write',folder_slug='rose')]
            admin=User(name='Superviseur',email='scope-admin@test.local',password_hash=hash_password(PASSWORD),roles=[admin_role]);worker=User(name='Collaborateur',email='scope-worker@test.local',password_hash=hash_password(PASSWORD),roles=[worker_role])
            db.add_all([admin,worker]);db.commit(); worker_id=worker.id
        def login(identity):
            assert c.post('/api/auth/login',json={'email':f'scope-{identity}@test.local','password':PASSWORD},headers=H).status_code==200
        login('admin')
        a=c.post('/api/launches',json={'name':'Lancement alpha'},headers=H).json()['id']
        b=c.post('/api/launches',json={'name':'Lancement beta'},headers=H).json()['id']
        d=c.post(f'/api/launches/{a}/documents',data={'folder':'rose','title':'Bon de livraison'},files={'file':('bl.txt',b'secret alpha','text/plain')},headers=H).json()
        did=d['id'];vid=d['latest']['id']
        with SessionLocal() as db:
            db.add(InternalNotification(recipient_id=worker_id,event_key='scope-example',kind='approval',title='Note confidentielle alpha',message='Contenu sensible',launch_id=a,folder_slug='rose'))
            db.commit()
        assert c.put(f'/api/launches/{a}/access',json={'restricted':True},headers=H).status_code==200
        assert c.get(f'/api/launches/{a}/access').json()['restricted'] is True
        login('worker')
        ids={x['id'] for x in c.get('/api/launches').json()}
        assert ids=={b}
        dash=c.get('/api/dashboard').json()
        assert dash['launches']==1 and not any(x['id']==a for x in dash['recent'])
        assert c.get('/api/workspace/priorities').json()['launches_considered']==1
        assert c.get('/api/notifications').json()['total']==0
        for endpoint in (f'/api/launches/{a}',f'/api/launches/{a}/completeness',
                         f'/api/launches/{a}/client-publications',f'/api/launches/{a}/paper-link',
                         f'/api/documents/{did}/versions/1/download',f'/api/document-versions/{vid}/passport'):
            result=c.get(endpoint)
            assert result.status_code==404,(endpoint,result.status_code,result.text[:150])
        assert c.post(f'/api/documents/{did}/versions',files={'file':('new.txt',b'nope','text/plain')},headers=H).status_code==404
        assert c.post('/api/assistant/guide',json={'question':'où sont les documents?','launch_id':a},headers=H).status_code==404
        assert c.post(f'/api/launches/{a}/access/members',json={'user_id':worker_id},headers=H).status_code==404
        login('admin')
        assert c.post(f'/api/launches/{a}/access/members',json={'user_id':worker_id},headers=H).status_code==201
        assert c.post(f'/api/launches/{a}/access/members',json={'user_id':worker_id},headers=H).status_code==409
        login('worker')
        assert c.get(f'/api/launches/{a}').status_code==200
        assert c.get(f'/api/documents/{did}/versions/1/download').content==b'secret alpha'
        assert c.get('/api/notifications').json()['total']==1
        login('admin')
        assert c.delete(f'/api/launches/{a}/access/members/{worker_id}',headers=H).status_code==200
        login('worker')
        assert c.get(f'/api/launches/{a}').status_code==404
        login('admin')
        assert c.put(f'/api/launches/{a}/access',json={'restricted':False},headers=H).status_code==200
        login('worker')
        assert c.get(f'/api/launches/{a}').status_code==200


def test_legacy_schema_migrates_without_losing_launches(tmp_path,monkeypatch):
    from sqlalchemy import create_engine, text, inspect
    from app import migrate as migrations
    legacy=create_engine('sqlite:///'+str(tmp_path/'existing.sqlite'))
    Base.metadata.create_all(legacy)
    with legacy.begin() as conn:
        conn.execute(text("INSERT INTO users(id,email,name,password_hash,active,created_at) VALUES ('user1','one@example.local','Legacy','hash',1,'2026-10-01')"))
        conn.execute(text("INSERT INTO launches(id,name,status,created_by,created_at,updated_at) VALUES ('launch1','Initial dossier','En cours','user1','2026-10-01','2026-10-01')"))
        conn.execute(text('DROP TABLE launch_members'))
        conn.execute(text('ALTER TABLE launches DROP COLUMN restricted'))
        conn.execute(text('DELETE FROM schema_migrations'))
    monkeypatch.setattr(migrations,'engine',legacy)
    migrations.migrate()
    migrations.migrate()  # idempotent
    with legacy.connect() as conn:
        assert conn.execute(text('SELECT name FROM launches WHERE id=\'launch1\'')).scalar_one()=='Initial dossier'
        assert conn.execute(text('SELECT restricted FROM launches WHERE id=\'launch1\'')).scalar_one()==0
        assert {'restricted'}.issubset({c['name'] for c in inspect(conn).get_columns('launches')})
        assert [row[0] for row in conn.execute(text('SELECT version FROM schema_migrations ORDER BY version'))]==list(migrations.REVISIONS)
    snapshot=migrations.backup_sqlite()
    assert snapshot is not None and snapshot.is_file() and snapshot.stat().st_size>0
    legacy.dispose()
