"""Cross-module regressions from the November audit, using only synthetic data."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.backup import backup, restore
from app.core import DATA_DIR, SessionLocal
from app.models import Document, DocumentVersion
from app.workflow_models import DocumentReview
from app.partner_mail import process_batch
from app.partner_models import PartnerMail
from app.quality import analyze_workbook
from app.sharing_routes import is_approved
from test_approvals import setup_roles, login
from test_consolidation_operations import mail_fixture
from test_partners import app, setup, organization, post, H


def upload(c, lid, label):
    return c.post(f'/api/launches/{lid}/documents',
                    data={'folder':'jaune','title':'Document de recette','doc_type':label},
                    files={'file':('piece.txt',b'Document de test','text/plain')}, headers=H)


def test_classification_requires_new_template_and_preserves_old_rejection_search():
    with TestClient(app) as client:
        roles, _ = setup_roles()
        login(client,0)
        lid=post(client,'/api/launches',{'name':'Atelier test'})['id']
        doc=upload(client,lid,"Fiche d'emploi").json()
        for label,stages in [('Fiche d’emploi',[roles[1]]),('Fiche technique',[roles[1],roles[2]])]:
            post(client,'/api/admin/approval-templates',
                 {'name':label,'folder_slug':'jaune','document_type':label,
                  'stages':[{'name':'Contrôle '+str(i),'reviewer_role_id':r} for i,r in enumerate(stages)]})
        runs=f'/api/documents/{doc["id"]}/approval-runs'
        original=post(client,runs)
        login(client,1)
        post(client,f'/api/approval-runs/{original["id"]}/decisions',{'decision':'approved'},200)
        login(client,0)
        change=client.patch(f'/api/documents/{doc["id"]}/classification',
                json={'type_id':'technical-sheet','expected_label':"Fiche d'emploi"},headers=H)
        assert change.status_code==200
        with SessionLocal() as db:
            assert not is_approved(db,db.get(DocumentVersion,doc['latest']['id']),db.get(Document,doc['id']))
        replacement=post(client,runs)
        assert replacement['cycle']>original['cycle'] and len(replacement['stages'])==2
        login(client,1)
        post(client,f'/api/approval-runs/{replacement["id"]}/decisions',
             {'decision':'rejected','comment':'Contrôle technique à reprendre'},200)
        assert client.get('/api/document-search?status=rejected').json()['items'][0]['document_id']==doc['id']
        assert client.get('/api/document-search?status=to_review').json()['total']==0


def test_distinct_orders_supplier_material_and_detach_both_launch_origins():
    with TestClient(app) as c:
        historical=setup(c)
        supplier=organization(c,'Fournisseur des deux ateliers')
        for name in ['Client A','Client B']:
            oid=post(c,'/api/orders',{'client_id':organization(c,name,'client'),'reference':'001'})['id']
            lid=post(c,'/api/launches',{'order_id':oid,'name':'Atelier principal'})['id']
            post(c,'/api/partners/order-lines',{'partner_id':supplier,'launch_id':lid,'order_ref':'001',
                 'material_ref':'Coton','unit':'kg','ordered':'20'})
            launches=[lid]
            if name=='Client A':
                post(c,f'/api/orders/{oid}/launches',{'launch_id':historical})
                launches.append(historical)
            for launch in launches:
                assert c.request('DELETE',f'/api/orders/{oid}/launches/{launch}',
                                 json={'reason':'Rattachement corrigé'},headers=H).status_code==200
                assert upload(c,launch,'Fiche technique').status_code==201
        assert c.post('/api/launches',json={'name':'    '},headers=H).status_code==422


def test_restore_quarantines_unsent_mail_and_rejects_unrelated_database(tmp_path):
    with TestClient(app) as staff, TestClient(app) as supplier:
        mail_fixture(staff,supplier)
        archive=backup(DATA_DIR,tmp_path/'mail.zip')
        sent=[]
        assert process_batch(transport=lambda *args:sent.append(args))['processed']==1
        restored=restore(archive,tmp_path/'restore')
        engine=create_engine('sqlite:///'+str(restored/'framat.db'))
        factory=sessionmaker(bind=engine)
        assert process_batch(factory=factory,transport=lambda *args:sent.append(args))['processed']==0
        with factory() as db:
            assert db.scalar(select(PartnerMail)).status=='uncertain'
        engine.dispose()
    other=tmp_path/'wrong';other.mkdir()
    with sqlite3.connect(other/'framat.db') as db:db.execute('CREATE TABLE inventory(id INTEGER)')
    with pytest.raises(ValueError,match='Framatex'):backup(other,tmp_path/'wrong.zip')


def test_excel_formula_tail_and_critical_cell_tail(tmp_path):
    paths=[tmp_path/'one.xlsx',tmp_path/'two.xlsx']
    for i,path in enumerate(paths):
        book=Workbook()
        book.active['A1']='='+'1+'*205+str(i)
        book.active['B1']='a'*120+str(i)
        book.save(path)
    result=analyze_workbook(paths[1],paths[0],[{'sheet':'Sheet','cell':'B1'}])
    assert {r['type'] for r in result['findings']}=={'formula_changed','critical_cell_changed'}


def test_upgrade_invalidates_legacy_approval_after_reclassification():
    from app.audit_migration import upgrade
    from app.workflow import review_status
    with TestClient(app) as client:
        launch = setup(client)
        doc = upload(client, launch, 'Fiche technique').json()
        vid = doc['latest']['id']
        with SessionLocal() as db:
            version = db.get(DocumentVersion, vid)
            db.add(DocumentReview(document_version_id=vid, decision='approved', reviewed_by=version.uploaded_by))
            db.commit()
        url = f'/api/documents/{doc["id"]}/classification'
        assert client.patch(url, json={'type_id':'certificate','expected_label':'Fiche technique'}, headers=H).status_code == 200
        with SessionLocal() as db:
            # Recreate the historical schema's decision stream on a synthetic document.
            db.execute(delete(DocumentReview).where(DocumentReview.document_version_id==vid, DocumentReview.decision=='to_review'))
            assert review_status(db, vid) == 'approved'
            upgrade(db.connection())
            assert review_status(db, vid) == 'to_review'
            assert not is_approved(db, db.get(DocumentVersion, vid), db.get(Document, doc['id']))


def test_upgrade_repairs_both_previously_detached_launches():
    from app.audit_migration import upgrade
    from app.launches import FOLDERS
    from app.models import Folder
    from app.partner_phase2_models import BusinessOrderLaunch
    with TestClient(app) as client:
        historical = setup(client)
        account = organization(client, 'Client A', 'client')
        order = post(client, '/api/orders', {'client_id':account,'reference':'001'})['id']
        direct = post(client, '/api/launches', {'order_id':order,'name':'Atelier migration'})['id']
        post(client, f'/api/orders/{order}/launches', {'launch_id':historical})
        with SessionLocal() as db:
            db.execute(delete(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id==order))
            upgrade(db.connection())
            db.commit()
        for launch in (historical, direct):
            with SessionLocal() as db:
                folders = db.scalars(select(Folder).where(Folder.launch_id==launch)).all()
                assert {f.slug for f in folders} == {slug for slug, _ in FOLDERS}
                assert all(f.canonical_id is None for f in folders)
            assert upload(client, launch, 'Fiche technique').status_code == 201
