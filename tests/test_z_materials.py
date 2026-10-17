"""MVP 0.12 : saisies sourcées, contrôle quantitatif, permissions et journal."""
from __future__ import annotations
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR']=tempfile.mkdtemp(prefix='framat-material-v12-')
os.environ['FRAMATEX_SECRET_KEY']='framat-material-test-secret-'*4
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User, AuditEvent
from app.material_models import MaterialPlanRevision, MaterialMovement

H={'X-Framatex-Request':'1'}
PASS='MaterialTestPassword2026!!'


def login(c,email):
    r=c.post('/api/auth/login',headers=H,json={'email':email,'password':PASS})
    assert r.status_code==200,r.text


def create_launch(c):
    r=c.post('/api/launches',headers=H,json={'name':'Lancement matière test'})
    assert r.status_code==201,r.text
    return r.json()['id']


def document(c,launch,folder):
    r=c.post(f'/api/launches/{launch}/documents',headers=H,
             data={'folder':folder,'title':f'Justificatif {folder}'},
             files={'file':(f'{folder}.txt',b'Justification documentaire pour essai', 'text/plain')})
    assert r.status_code==201,r.text
    return r.json()['latest']['id']


def create_material(c,launch,version,ref='TIS-42'):
    return c.post(f'/api/launches/{launch}/materials',headers=H,json={
        'reference':ref,'label':'Tissu jersey', 'unit':'m','quantity':'2700.000',
        'source_version_id':version,'note':'Besoin theorique calcule et verifie'})


def movement(c,launch,line,kind,quantity,version):
    return c.post(f'/api/launches/{launch}/materials/{line}/movements',headers=H,json={
        'kind':kind,'quantity':quantity,'source_version_id':version,
        'note':'Bon documentaire examine par la responsable'})


def seed_people():
    with SessionLocal() as db:
        admin=db.scalar(select(Role).where(Role.name=='Administrateur')) or Role(name='Administrateur')
        rose=Role(name='Réception seule',grants=[RolePermission(action='launch.read'),
                    RolePermission(action='document.read',folder_slug='rose')])
        jaune=Role(name='Technique seule',grants=[RolePermission(action='launch.read'),
                    RolePermission(action='document.read',folder_slug='jaune')])
        both=Role(name='Lecture des deux',grants=[RolePermission(action='launch.read'),
                    RolePermission(action='document.read',folder_slug='jaune'),
                    RolePermission(action='document.read',folder_slug='rose')])
        db.add_all([User(email='material-admin@local.test',name='Administrateur',password_hash=hash_password(PASS),roles=[admin]),
                    User(email='material-rose@local.test',name='Réception',password_hash=hash_password(PASS),roles=[rose]),
                    User(email='material-jaune@local.test',name='Technique',password_hash=hash_password(PASS),roles=[jaune]),
                    User(email='material-reader@local.test',name='Lecteur',password_hash=hash_password(PASS),roles=[both])]);db.commit()


def test_materials_evidence_math_revisions_and_cancellations():
    with TestClient(app) as c:
        seed_people();login(c,'material-admin@local.test')
        launch=create_launch(c); other=create_launch(c)
        tech=document(c,launch,'jaune'); receipt=document(c,launch,'rose'); other_doc=document(c,other,'jaune')
        url=f'/api/launches/{launch}/materials'
        assert create_material(c,launch,tech).status_code==201
        assert create_material(c,launch,tech).status_code==409
        line=c.get(url).json()['lines'][0]['id']
        assert c.get(url).json()['lines'][0]['planned']=='2700.000'
        assert movement(c,launch,line,'ordered','2800',tech).status_code==201
        assert movement(c,launch,line,'received','1300',receipt).status_code==201
        report=c.get(url).json()['lines'][0]
        assert report['to_order']=='-100.000' and report['to_receive']=='1500.000'
        assert 'commande_supérieure_au_prévu' in report['flags']
        assert movement(c,launch,line,'received','1600',receipt).status_code==201
        report=c.get(url).json()['lines'][0]
        assert report['received']=='2900.000' and 'réception_supérieure_aux_commandes' in report['flags']
        cancel_id=next(x['id'] for x in report['movements'] if x['quantity']=='1600.000')
        cancel=c.post(f'{url}/{line}/movements/{cancel_id}/cancel',headers=H,
                      json={'reason':'Saisie double identifiee dans le bon de reception'})
        assert cancel.status_code==200,cancel.text
        assert cancel.json()['received']=='1300.000'
        assert any(m['id']==cancel_id and m['cancellation_reason'] for m in cancel.json()['movements'])
        assert c.post(f'{url}/{line}/movements/{cancel_id}/cancel',headers=H,
                      json={'reason':'Deuxieme tentative non autorisee'}).status_code==409
        revise=c.post(f'{url}/{line}/plans',headers=H,json={'quantity':'2755','source_version_id':tech,
                      'note':'Recalcul controle pour changement de consommation'})
        assert revise.status_code==201 and revise.json()['planned']=='2755.000'
        assert [x['quantity'] for x in revise.json()['plan_history']]==['2700.000','2755.000']
        with SessionLocal() as db:
            assert db.scalar(select(MaterialMovement).where(MaterialMovement.id==cancel_id)).cancelled_at is not None
            assert len(db.scalars(select(MaterialPlanRevision)).all())==2
            assert any(x.action=='material.movement.cancel' for x in db.scalars(select(AuditEvent)).all())
        # Dossier indépendant: une pièce étrangère ne peut justifier la prévision.
        assert c.post(f'{url}/{line}/plans',headers=H,json={'quantity':'3000',
               'source_version_id':other_doc,'note':'Document de provenance externe interdit'}).status_code==422


def test_materials_block_disallowed_evidence_units_and_permissions():
    with TestClient(app) as c:
        login(c,'material-admin@local.test')
        launch=create_launch(c); tech=document(c,launch,'jaune');receipt=document(c,launch,'rose')
        url=f'/api/launches/{launch}/materials'
        invalid=[{'reference':'B','label':'Tissu', 'unit':'boite','quantity':'10','source_version_id':tech,'note':'Validation du justificatif technique'},
                 {'reference':'C','label':'Tissu','unit':'m','quantity':'NaN','source_version_id':tech,'note':'Validation du justificatif technique'},
                 {'reference':'D','label':'Tissu','unit':'m','quantity':'1.0001','source_version_id':tech,'note':'Validation du justificatif technique'},
                 {'reference':'E','label':'Tissu','unit':'m','quantity':'-1','source_version_id':tech,'note':'Validation du justificatif technique'}]
        for payload in invalid:
            assert c.post(url,headers=H,json=payload).status_code==422
        assert create_material(c,launch,receipt,ref='WRONG').status_code==422
        created=create_material(c,launch,tech,ref='OK')
        assert created.status_code==201,created.text
        line=created.json()['id']
        assert movement(c,launch,line,'ordered','4',receipt).status_code==422
        assert movement(c,launch,line,'received','4',tech).status_code==422
        assert movement(c,launch,line,'received','0',receipt).status_code==422
        for mail in ('material-rose@local.test','material-jaune@local.test'):
            login(c,mail)
            assert c.get(url).status_code==403
        login(c,'material-reader@local.test')
        assert c.get(url).status_code==200
        assert create_material(c,launch,tech,ref='NO').status_code==403
        assert movement(c,launch,line,'ordered','10',tech).status_code==403
        assert c.post(f'{url}/{line}/plans',headers=H,json={'quantity':'20',
               'source_version_id':tech,'note':'Tentative sans droit de modification'}).status_code==403


def test_materials_reference_boundaries_and_no_cross_launch_access():
    with TestClient(app) as c:
        login(c,'material-admin@local.test')
        first=create_launch(c); second=create_launch(c)
        technical=document(c,first,'jaune')
        line=create_material(c,first,technical).json()['id']
        assert c.post(f'/api/launches/{second}/materials/{line}/movements',headers=H,json={
          'kind':'ordered','quantity':'1','source_version_id':technical,
          'note':'Tentative de rattachement a un autre lancement'}).status_code==404
        assert c.get('/api/launches/unknown/materials').status_code==404
        # Les références et les notes ne proviennent pas d'un import ORLI automatique.
        assert c.get(f'/api/launches/{second}/materials').json()['lines']==[]
