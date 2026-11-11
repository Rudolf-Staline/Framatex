"""Persisted canonical ownership, historical conversion, isolation and concurrency."""
import hashlib
import sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, create_engine, text
from sqlalchemy.orm import Session
from test_partners import app,setup,post,organization,H,PWD
from app.core import SessionLocal
from app.models import Document,Folder,Launch,Role,RolePermission,User
from app.order_documents import OrderDossier,dossier


def put(c,oid,origin=None):
    r=c.post(f'/api/orders/{oid}/documents',data={'folder':'jaune','title':'Même nom','doc_type':'Dossier technique',**({'launch_id':origin} if origin else {})},files={'file':('identique.txt',b'document synthetique','text/plain')},headers=H)
    assert r.status_code==201,r.text
    return r.json()


def test_single_dossier_multiple_launches_optional_origin_and_interorder_acl():
    with TestClient(app) as c:
        setup(c);cid=organization(c,'Client A','client')
        a=post(c,'/api/orders',{'client_id':cid,'reference':'CMD-A'})['id']
        b=post(c,'/api/orders',{'client_id':cid,'reference':'CMD-B'})['id']
        lids=[post(c,'/api/launches',{'name':f'Lancement {i}','order_id':a})['id'] for i in range(2)]
        docs=[put(c,a,lids[0]),put(c,a,lids[1]),put(c,a)]
        other=put(c,b)
        roots=[c.get(f'/api/orders/{oid}/dossier').json() for oid in [a,b]]
        assert roots[0]['id']!=roots[1]['id']
        assert len(roots[0]['sections'])==4
        items=next(f for f in roots[0]['sections'] if f['slug']=='jaune')['documents']
        assert len(items)==3 and len({d['id'] for d in items})==3
        assert {d['order_id'] for d in items}=={a}
        assert len(next(f for f in c.get(f'/api/orders/{a}/dossier',params={'launch_id':lids[0]}).json()['sections'] if f['slug']=='jaune')['documents'])==1
        assert c.post(f'/api/orders/{b}/documents',data={'folder':'rose','title':'Étranger','launch_id':lids[0]},files={'file':('x.txt',b'non','text/plain')},headers=H).status_code==422
        assert c.post(f'/api/documents/{docs[0]["id"]}/versions',files={'file':('identique.txt',b'v2','text/plain')},headers=H).status_code==201
        assert c.get(f'/api/documents/{docs[0]["id"]}/versions/1/download').content==b'document synthetique'
        # Restricted launch in an order restricts the entire shared dossier.
        with SessionLocal() as db:
            role=Role(name='Lecteur');role.grants.extend([RolePermission(action='launch.read'),RolePermission(action='document.read')])
            from app.core import hash_password
            user=User(name='Lecteur',email='reader@sample.local',password_hash=hash_password(PWD));user.roles.append(role);db.add(user)
            db.get(Launch,lids[1]).restricted=True;db.commit()
        post(c,'/api/auth/login',{'email':'reader@sample.local','password':PWD},200)
        assert c.get(f'/api/orders/{a}').status_code==404
        assert c.get(f'/api/orders/{a}/dossier').status_code==404
        for d in docs+[other]:
            assert c.get(f'/api/documents/{d["id"]}/versions/1/download').status_code==404
        assert c.get(f'/api/launches/{lids[0]}').status_code==404
        assert c.get('/api/document-search').json()['total']==0
        assert c.get('/api/orders').json()==[]


def test_concurrent_creation_is_idempotent_and_unique():
    with TestClient(app) as c:
        setup(c);cid=organization(c,'Client A','client');oid=post(c,'/api/orders',{'client_id':cid,'reference':'CMD-THREAD'})['id']
        with SessionLocal() as db:
            root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==oid))
            for section in db.scalars(select(Folder).where(Folder.dossier_id==root.id)):db.delete(section)
            db.flush();db.delete(root);db.commit()
        def create(_):
            with SessionLocal() as db:
                root=dossier(db,oid);db.commit();return root.id
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert len(set(pool.map(create,range(12))))==1
        with SessionLocal() as db:
            root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==oid))
            assert len(list(db.scalars(select(Folder).where(Folder.dossier_id==root.id))))==4


def legacy_fixture(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'files').mkdir()
    file=b'historique immuable';digest=hashlib.sha256(file).hexdigest();(source/'files/blob').write_bytes(file)
    path=source/'framat.db'
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent/'fixtures/phase2-schema.sql').read_text())
        db.execute("INSERT INTO users VALUES ('u','u@example.local','Auteur','hash',1,'2026-01-01')")
        db.execute("INSERT INTO partners VALUES ('c','client','Client A',1,'')")
        db.execute("INSERT INTO business_orders VALUES ('o','c','CMD-A','u','2026-01-01')")
        for i in range(3):
            db.execute("INSERT INTO launches VALUES (?,?,?,'Client A',NULL,'En cours','u','2026-01-01','2026-01-01',0)",(f'l{i}',f'LF-{i}','CMD-A'))
            if i<2:db.execute("INSERT INTO business_order_launches VALUES (?,'o','u','2026-01-01')",(f'l{i}',))
            db.execute("INSERT INTO folders VALUES (?,?,'jaune','Technique')",(f'f{i}',f'l{i}'))
            db.execute("INSERT INTO documents VALUES (?,?,'Même nom','Dossier technique','u','2026-01-01')",(f'd{i}',f'f{i}'))
            db.execute("INSERT INTO document_versions VALUES (?,?,1,'identique.txt',?,'text/plain',?,?,'u','2026-01-01')",(f'v{i}',f'd{i}',f'blob{i}',len(file),digest))
            (source/f'files/blob{i}').write_bytes(file)
        db.execute("INSERT INTO roles VALUES ('r','Validation')")
        db.execute("INSERT INTO approval_templates VALUES ('t','Circuit historique','jaune','Dossier technique',1,'u','2026-01-01')")
        db.execute("INSERT INTO approval_stages VALUES ('s','t',1,'Contrôle','r')")
        db.execute("INSERT INTO approval_runs VALUES ('run','t','v0',1,'approved','u','2026-01-01','2026-01-01')")
        db.execute("INSERT INTO approval_decisions VALUES ('decision','run','s','u','approved','Décision historique','2026-01-01')")
        db.execute("INSERT INTO internal_notifications VALUES ('n','u','historic','approval','Historique','Notification','l0','jaune','2026-01-01',NULL)")
        db.execute("INSERT INTO client_publications VALUES ('pub','l0','v0','Client A','Publication historique','published','u','2026-01-01',NULL,NULL,NULL)")
        db.execute("INSERT INTO document_reviews VALUES ('review','v0','approved','Contrôlé','u','2026-01-01')")
    return source


def test_real_phase2_schema_backup_migrate_twice_and_restore(tmp_path):
    from app.backup import backup,restore,validate
    from app.order_migration import upgrade,preflight
    source=legacy_fixture(tmp_path);archive=backup(source,tmp_path/'backup.zip')
    restored=restore(archive,tmp_path/'restored');validate(restored/'framat.db',restored/'files')
    eng=create_engine(f'sqlite:///{restored / "framat.db"}')
    with eng.connect() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=OFF');conn.commit();conn.exec_driver_sql('BEGIN IMMEDIATE')
        before=list(conn.exec_driver_sql('SELECT * FROM document_versions'))
        assert preflight(conn)['unlinked_launches']==['l2']
        upgrade(conn);upgrade(conn)
        from app.approval_migration import upgrade as approvals_upgrade
        approvals_upgrade(conn);approvals_upgrade(conn)
        assert list(conn.exec_driver_sql('SELECT * FROM document_versions'))==before
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM order_dossiers').scalar()==1
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM folders WHERE dossier_id IS NOT NULL').scalar()==4
        assert conn.exec_driver_sql("SELECT COUNT(DISTINCT folder_id) FROM documents WHERE id IN ('d0','d1')").scalar()==1
        assert conn.exec_driver_sql("SELECT folder_id FROM documents WHERE id='d2'").scalar()=='f2'
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM document_reviews').scalar()==1
        assert conn.exec_driver_sql("SELECT cycle FROM approval_runs WHERE id='run'").scalar()==1
        assert conn.exec_driver_sql("SELECT comment FROM approval_decisions WHERE id='decision'").scalar()=='Décision historique'
        assert conn.exec_driver_sql("SELECT document_version_id FROM client_publications WHERE id='pub'").scalar()=='v0'
        assert conn.exec_driver_sql("SELECT launch_id FROM internal_notifications WHERE id='n'").scalar()=='l0'
        assert not list(conn.exec_driver_sql('PRAGMA foreign_key_check'))
        conn.commit();conn.exec_driver_sql('PRAGMA foreign_keys=ON')
    validate(restored/'framat.db',restored/'files')
    # Original remains unchanged and independently restorable.
    with sqlite3.connect(source/'framat.db') as db:
        assert db.execute("SELECT folder_id FROM documents WHERE id='d1'").fetchone()[0]=='f1'


def test_incompatible_historical_link_aborts_without_partial_conversion(tmp_path):
    from app.order_migration import upgrade
    source=legacy_fixture(tmp_path)
    with sqlite3.connect(source/'framat.db') as db:db.execute("UPDATE launches SET client_name='Autre client' WHERE id='l1'")
    eng=create_engine(f'sqlite:///{source / "framat.db"}')
    with eng.connect() as conn:
        with pytest.raises(RuntimeError,match='incompatibles'):upgrade(conn)
        assert conn.exec_driver_sql("SELECT folder_id FROM documents WHERE id='d1'").scalar()=='f1'
        assert 'dossier_id' not in {r[1] for r in conn.exec_driver_sql('PRAGMA table_info(folders)')}


def test_four_sections_canonical_search_versions_approval_and_completeness():
    with TestClient(app) as c:
        setup(c);cid=organization(c,'Client rubriques','client')
        oid=post(c,'/api/orders',{'client_id':cid,'reference':'CMD-FOUR'})['id']
        profile=post(c,'/api/admin/completeness/profiles',{'name':'Quatre rubriques','description':'Synthétique'})
        for slug in ('jaune','rose','bleu','vert'):
            post(c,f'/api/admin/completeness/profiles/{profile["id"]}/rules',{'title':f'Pièce {slug}','folder':slug,'document_type':f'Type {slug}','due_phase':'preparation','requires_validation':True,'guidance':'Règle synthétique à confirmer'})
            response=c.post(f'/api/orders/{oid}/documents',data={'folder':slug,'title':'Même nom','doc_type':f'Type {slug}'},files={'file':('meme.txt',slug.encode(),'text/plain')},headers=H)
            assert response.status_code==201,response.text
            doc=response.json();assert doc['launch_id'] is None and doc['order_id']==oid
            assert c.post(f'/api/documents/{doc["id"]}/versions',files={'file':('meme.txt',b'v2','text/plain')},headers=H).status_code==201
            post(c,f'/api/documents/{doc["id"]}/reviews',{'decision':'approved','comment':'Vérification synthétique conforme'})
            result=c.get('/api/document-search',params={'folder':slug,'order_ref':'CMD-FOUR'}).json()
            assert result['total']==1 and result['items'][0]['order_id']==oid
            assert c.get(f'/api/documents/{doc["id"]}/versions/1/download').content==slug.encode()
        config=c.put(f'/api/orders/{oid}/completeness/context',json={'profile_id':profile['id'],'phase':'preparation'},headers=H)
        assert config.status_code==200,config.text
        assert config.json()['counts']['ready']==4 and config.json()['counts']['missing']==0
        assert not config.json()['business_rules_confirmed']
        qr=c.get(f'/api/orders/{oid}/paper-link').json()
        assert qr['url'].endswith('/#/order/'+oid) and not qr['is_access_token']


def test_business_navigation_sources_and_api_validation():
    with TestClient(app) as c:
        setup(c);cid=organization(c,'Client navigation','client')
        oid=post(c,'/api/orders',{'client_id':cid,'reference':'CMD-NAVIGATION'})['id']
        assert c.get('/api/directory/client').json()[0]['orders'][0]['id']==oid
        assert c.get('/api/directory/supplier').json()==[]
        assert c.get('/api/receipts').json()==[]
        assert c.get('/api/directory/unknown').status_code==422
        post(c,'/api/orders',{'client_id':cid,'reference':'x'*101},422)
        post(c,'/api/orders',{'client_id':'malformed','reference':'CMD'},422)
        post(c,'/api/orders',{'client_id':cid,'reference':'CMD','unexpected':'value'},422)
        assert c.put(f'/api/orders/{oid}/completeness/context',json={'phase':'unknown'},headers=H).status_code==422
        assert c.put(f'/api/orders/{oid}/completeness/context',json={'profile_id':'x'*36,'phase':'preparation'},headers=H).status_code==422
