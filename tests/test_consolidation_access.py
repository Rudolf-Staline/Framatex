"""Canonical membership and historical source restrictions remain independent."""
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app, setup, post, organization, H, PWD
from app.core import SessionLocal, hash_password
from app.models import User, Role, RolePermission, Launch, Document
from app.order_documents import OrderMember, order_accessible, document_accessible, document_access_clause, order_access_clause
from app.access import launch_access_clause
from app.partner_phase2_models import BusinessOrder


def reader():
    with SessionLocal() as db:
        role = Role(name='Lecture consolidation', grants=[RolePermission(action='launch.read'),
            RolePermission(action='document.read'), RolePermission(action='document.write')])
        row = User(name='Lecteur consolidation', email='consolidation-reader@sample.local',
                   password_hash=hash_password(PWD), roles=[role])
        db.add(row); db.commit()
        return row.id


def grant(admin, oid, uid):
    return post(admin, f'/api/orders/{oid}/members',
                {'user_id':uid,'reason':'Accès de recette synthétique explicite'})


def doc(admin, oid, title, lid=None):
    data = {'folder':'jaune','title':title,'doc_type':'Fiche technique'}
    if lid: data['launch_id']=lid
    response = admin.post(f'/api/orders/{oid}/documents', data=data,
        files={'file':('synthese.txt',title.encode(),'text/plain')},headers=H)
    assert response.status_code==201, response.text
    return response.json()


def test_membership_revocation_cannot_be_undone_by_launch_attachment():
    with TestClient(app) as admin, TestClient(app) as limited:
        lid=setup(admin); cid=organization(admin,'Client A','client'); uid=reader()
        oid=post(admin,'/api/orders',{'client_id':cid,'reference':'CANON-ACL'})['id']
        grant(admin,oid,uid)
        post(limited,'/api/auth/login',{'email':'consolidation-reader@sample.local','password':PWD},200)
        common=doc(admin,oid,'Pièce commune')
        assert limited.get(f'/api/documents/{common["id"]}/versions/1/download').status_code==200
        admin.patch(f'/api/launches/{lid}',json={'order_ref':'CANON-ACL'},headers=H)
        post(admin,f'/api/orders/{oid}/launches',{'launch_id':lid})
        assert limited.get(f'/api/orders/{oid}/dossier').status_code==200
        assert admin.delete(f'/api/orders/{oid}/members/{uid}',headers=H).status_code==200
        for url in [f'/api/orders/{oid}',f'/api/orders/{oid}/dossier',
                    f'/api/documents/{common["id"]}/versions/1/download',f'/api/launches/{lid}']:
            assert limited.get(url).status_code==404, url
        assert limited.get('/api/document-search').json()['total']==0
        assert limited.get('/api/orders').json()==[]
        assert admin.get(f'/api/orders/{oid}/dossier').status_code==200
        with SessionLocal() as db:
            owner=db.get(User,db.get(BusinessOrder,oid).created_by)
            assert order_accessible(db,owner,oid)


def test_heterogeneous_sources_are_filtered_without_hiding_common_dossier():
    with TestClient(app) as admin, TestClient(app) as limited:
        first=setup(admin);cid=organization(admin,'Client A','client');uid=reader()
        second=post(admin,'/api/launches',{'name':'Secret source','client_name':'Client A','order_ref':'MIXED'})['id']
        oid=post(admin,'/api/orders',{'client_id':cid,'reference':'MIXED'})['id']
        admin.patch(f'/api/launches/{first}',json={'order_ref':'MIXED'},headers=H)
        for lid in (first,second):post(admin,f'/api/orders/{oid}/launches',{'launch_id':lid})
        grant(admin,oid,uid)
        common=doc(admin,oid,'Commune');open_doc=doc(admin,oid,'Ouverte',first);secret=doc(admin,oid,'Titre confidentiel',second)
        post(admin,f'/api/documents/{secret["id"]}/reviews',{'decision':'approved'})
        post(admin,f'/api/launches/{first}/values',{'key':'quantite_lancement','value':'12','unit':'pièce','source_version_id':secret['latest']['id']})
        post(admin,f'/api/launches/{first}/requirements',{'source_version_id':secret['latest']['id'],'title':'Exigence source cachée','description':'Exigence synthétique confidentielle'})
        admin.put(f'/api/launches/{second}/access',json={'restricted':True},headers=H)
        post(limited,'/api/auth/login',{'email':'consolidation-reader@sample.local','password':PWD},200)
        payload=limited.get(f'/api/orders/{oid}/dossier').json()
        assert {d['id'] for s in payload['sections'] for d in s['documents']}=={common['id'],open_doc['id']}
        detail=limited.get(f'/api/orders/{oid}').json()
        assert [l['id'] for l in detail['launches']]==[first]
        assert secret['id'] not in str(detail) and secret['title'] not in str(detail)
        assert limited.get(f'/api/documents/{secret["id"]}/versions/1/download').status_code==404
        assert limited.get(f'/api/launches/{first}/approval-overview').status_code==200
        assert secret['id'] not in limited.get(f'/api/launches/{first}/approval-overview').text
        for suffix in ['reviews','values','specifications','dependency-graph','quality','excel-inspections','workflow-summary']:
            response=limited.get(f'/api/launches/{first}/{suffix}')
            assert response.status_code==200,response.text
            assert secret['id'] not in response.text and secret['title'] not in response.text
        bad_source=limited.post(f'/api/launches/{first}/values',json={'key':'quantite_lancement','value':'20','unit':'pièce','source_version_id':secret['latest']['id']},headers=H)
        assert bad_source.status_code==404
        assert limited.get(f'/api/orders/{oid}/dossier?launch_id={second}').status_code==404
        rejected=limited.post(f'/api/orders/{oid}/documents',data={'folder':'jaune','title':'Intrus','launch_id':second},
            files={'file':('x.txt',b'x','text/plain')},headers=H)
        assert rejected.status_code==404
        with SessionLocal() as db:
            who=db.get(User,uid)
            all_docs=list(db.scalars(select(Document)))
            assert {d.id for d in all_docs if document_accessible(db,who,d)}==set(db.scalars(select(Document.id).where(document_access_clause(who))))=={common['id'],open_doc['id']}
            assert list(db.scalars(select(Launch.id).where(launch_access_clause(who,Launch.id))))==[first]
            d=db.get(Document,common['id']);assert d.context_launch_id is None and d.context_order_id==oid
            who.active=False;db.commit()
            assert not order_accessible(db,who,oid)
            assert not list(db.scalars(select(Document.id).where(document_access_clause(who))))
        assert limited.get(f'/api/orders/{oid}/dossier').status_code==401


def test_conservative_acl_migration_materializes_only_previous_full_access():
    from app.order_migration import conservative_acl_upgrade
    from app.core import engine
    with TestClient(app) as admin:
        lid=setup(admin);cid=organization(admin,'Client A','client');uid=reader()
        oid=post(admin,'/api/orders',{'client_id':cid,'reference':'MIGRATED'})['id']
        admin.patch(f'/api/launches/{lid}',json={'order_ref':'MIGRATED'},headers=H)
        post(admin,f'/api/orders/{oid}/launches',{'launch_id':lid})
        with engine.begin() as conn:
            conservative_acl_upgrade(conn);conservative_acl_upgrade(conn)
        with SessionLocal() as db:
            assert db.get(OrderMember,(oid,uid)) is not None
            db.delete(db.get(OrderMember,(oid,uid)));db.commit()
        admin.put(f'/api/launches/{lid}/access',json={'restricted':True},headers=H)
        with engine.begin() as conn:conservative_acl_upgrade(conn)
        with SessionLocal() as db:assert db.get(OrderMember,(oid,uid)) is None
