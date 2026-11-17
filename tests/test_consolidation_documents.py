"""Identification, conservative taxonomy, and exact-version internal comments."""
import json
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app, setup, post, organization, H, PWD
from app.core import SessionLocal, hash_password
from app.models import User, Role, RolePermission
from app.order_fields import OrderIdentification
from app.document_types import DocumentTypeAssignment, resolve_type, equivalent_types


def order_with_document(c, label='Fiche d’emploi'):
    lid=setup(c); client=organization(c,'Client A','client')
    order=post(c,'/api/orders',{'client_id':client,'reference':'DOCS-1'})
    r=c.post(f'/api/orders/{order["id"]}/documents',data={'folder':'jaune','title':'Pièce commune','doc_type':label},files={'file':('fiche.txt',b'Version une','text/plain')},headers=H)
    assert r.status_code==201,r.text
    return lid,order,r.json()


def test_identification_order_launch_separation_conflict_and_legacy_keys():
    with TestClient(app) as c:
        lid,order,doc=order_with_document(c)
        url=f'/api/orders/{order["id"]}/identification'
        initial=c.get(url).json()
        assert initial['revision']==0 and initial['canonical']['reference']=='DOCS-1'
        assert 'workshop' not in {f['key'] for f in initial['fields']}
        payload={'expected_revision':0,'values':{'quantity':'123.125','quantity_unit':'pièces','program':'Collection A'}}
        r=c.patch(url,json=payload,headers=H);assert r.status_code==200,r.text
        assert r.json()['values']['quantity']=='123.125'
        assert c.patch(url,json=payload,headers=H).status_code==409
        assert c.patch(url,json={'expected_revision':1,'values':{'workshop':'Atelier'}},headers=H).status_code==422
        with SessionLocal() as db:
            row=db.get(OrderIdentification,order['id']);v=json.loads(row.fields_json);v['retired_key']='historique';row.fields_json=json.dumps(v);db.commit()
        r=c.patch(url,json={'expected_revision':1,'values':{'notes':'À confirmer'}},headers=H)
        assert r.status_code==200 and r.json()['values']['retired_key']=='historique'
        lu=f'/api/launches/{lid}/identification'
        assert c.patch(lu,json={'expected_revision':0,'values':{'workshop':'Atelier B'}},headers=H).status_code==200
        assert 'workshop' not in c.get(url).json()['values']
        assert c.patch(url,json={'expected_revision':2,'values':{'quantity':'-1'}},headers=H).status_code==422


def test_taxonomy_preserves_unknown_labels_explicit_classification_and_conflict():
    with TestClient(app) as c:
        lid,order,doc=order_with_document(c,'Type historique libre')
        assert doc['classification']['id']=='unclassified'
        with SessionLocal() as db:
            assert db.get(DocumentTypeAssignment,doc['id']).original_label=='Type historique libre'
        url=f'/api/documents/{doc["id"]}/classification'
        assert c.patch(url,json={'type_id':'invoice','expected_label':'Type historique libre'},headers=H).status_code==422
        r=c.patch(url,json={'type_id':'technical-sheet','expected_label':'Type historique libre'},headers=H)
        assert r.status_code==200 and r.json()['doc_type']=='Fiche technique'
        assert r.json()['classification']['original_label']=='Type historique libre'
        assert c.patch(url,json={'type_id':'employment-sheet','expected_label':'Type historique libre'},headers=H).status_code==409
        rows=c.get('/api/document-types?folder=bleu').json()['items']
        assert 'invoice' not in {row['id'] for row in rows}
    assert resolve_type(" Fiche d'emploi ")['id']=='employment-sheet'
    assert resolve_type('BL') is None  # no unvalidated acronym merge
    assert resolve_type('Dossier technique')['id']!=resolve_type('Dossier technique client')['id']
    assert 'Fiche d’emploi' in equivalent_types("Fiche d'emploi")


def test_internal_comments_exact_version_acl_and_no_external_identity():
    with TestClient(app) as c, TestClient(app) as reader, TestClient(app) as outsider:
        lid,order,doc=order_with_document(c)
        v1=doc['latest']['id'];url=f'/api/document-versions/{v1}/comments'
        row=post(c,url,{'text':'Vérifier la mesure avant approbation'})
        assert row['kind']=='comment' and row['version_id']==v1
        version2=c.post(f'/api/documents/{doc["id"]}/versions',files={'file':('fiche2.txt',b'Version deux','text/plain')},headers=H)
        assert version2.status_code==201,version2.text
        v2=version2.json()['latest']['id']
        assert c.get(f'/api/document-versions/{v2}/comments').json()['total']==0
        assert c.get(url).json()['items'][0]['text']=='Vérifier la mesure avant approbation'
        assert post(c,url,{'text':'   '},422)
        with SessionLocal() as db:
            role=Role(name='Lecteur documentaire')
            role.grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='jaune')]
            a=User(name='Lecteur',email='lecteur-docs@sample.local',password_hash=hash_password(PWD));a.roles.append(role)
            b=User(name='Exclu',email='exclu-docs@sample.local',password_hash=hash_password(PWD));b.roles.append(role)
            db.add_all([a,b]);db.commit();reader_id=a.id
        post(c,f'/api/orders/{order["id"]}/members',{'user_id':reader_id,'reason':'Lecture pour contrôle documentaire'})
        for client,email in [(reader,'lecteur-docs@sample.local'),(outsider,'exclu-docs@sample.local')]:
            post(client,'/api/auth/login',{'email':email,'password':PWD},200)
        assert reader.get(url).status_code==200
        post(reader,url,{'text':'Une lecture ne donne pas écriture'},403)
        assert outsider.get(url).status_code==404
        assert outsider.get(f'/api/orders/{order["id"]}/identification').status_code==404
        c.delete(f'/api/orders/{order["id"]}/members/{reader_id}',headers=H)
        assert reader.get(url).status_code==404


def test_historical_identification_migration_preserves_retired_keys_idempotently():
    from sqlalchemy import create_engine, text
    from app.core import Base, utcnow
    from app.models import Launch
    from app.order_fields import LaunchIdentification, migrate_historical_identification
    isolated=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(isolated)
    raw='{"workshop":"Atelier historique","retired_field":"à conserver","quantity":125}'
    with isolated.begin() as conn:
        conn.execute(User.__table__.insert().values(id='historic-user',name='Auteur historique',email='historic@example.local',password_hash='not-an-authentic-hash',active=True,created_at=utcnow()))
        conn.execute(Launch.__table__.insert().values(id='historic-launch',name='Historique',created_by='historic-user',created_at=utcnow(),updated_at=utcnow(),restricted=False,status='En cours'))
        conn.execute(text('ALTER TABLE launches ADD COLUMN identification_json TEXT'))
        conn.execute(text('UPDATE launches SET identification_json=:raw WHERE id=:id'),{'raw':raw,'id':'historic-launch'})
        migrate_historical_identification(conn);migrate_historical_identification(conn)
        rows=conn.execute(select(LaunchIdentification.__table__)).mappings().all()
        assert len(rows)==1 and rows[0]['fields_json']==raw and rows[0]['revision']==1
