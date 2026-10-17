"""Incrément 0.4 : vérifie comparaison, versions, protection des sources, intégrité Excel."""
import os
import io
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-quality-')
os.environ['FRAMATEX_SECRET_KEY'] = 'quality-test-secret-'*3

import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from app.main import app
from app.core import Base,engine,SessionLocal,hash_password
from app.models import User,Role,RolePermission

H={'X-Framatex-Request':'1'}

@pytest.fixture()
def c():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            yellow=Role(name='Tech')
            yellow.grants=[RolePermission(action='launch.read'),
                RolePermission(action='document.read',folder_slug='jaune'),
                RolePermission(action='document.write',folder_slug='jaune'),
                RolePermission(action='quality.review',folder_slug='jaune')]
            rose=Role(name='Reception')
            rose.grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='rose')]
            db.add_all([User(name='Admin',email='admin@q.local',password_hash=hash_password('StrongPwd2026!'),roles=[admin]),
                User(name='Tech',email='tech@q.local',password_hash=hash_password('StrongPwd2026!'),roles=[yellow]),
                User(name='Reception',email='rose@q.local',password_hash=hash_password('StrongPwd2026!'),roles=[rose])])
            db.commit()
        login(client,'admin@q.local')
        yield client
    Base.metadata.drop_all(engine)

def login(c,email):
    assert c.post('/api/auth/login',json={'email':email,'password':'StrongPwd2026!'},headers=H).status_code==200

def launch(c):
    r=c.post('/api/launches',json={'name':'Vestes 2026'},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']

def doc(c,lid,type,folder='jaune',filename='data.txt',data=b'Fiche emploi de reference'):
    r=c.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':type,'doc_type':type},files={'file':(filename,data)},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id'],r.json()['latest']['id']

def put(c,version,field,value,unit='pièce'):
    return c.post(f'/api/document-versions/{version}/data',json={'field_key':field,'value':value,'unit':unit},headers=H)

def rule(c,left,right,folder_a='jaune',folder_b='jaune',tol='0'):
    r=c.post('/api/admin/quality-rules',json={'name':'Comparaison des quantités', 'field_key':'quantite_lancement',
           'left_doc_type':left,'right_doc_type':right,'left_folder':folder_a,'right_folder':folder_b,'tolerance':tol},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']


def test_cross_document_difference_and_decision_stale_on_new_version(c):
    lid=launch(c)
    a,va=doc(c,lid,'Lancement provisoire')
    b,vb=doc(c,lid,'Lancement définitif')
    rid=rule(c,'Lancement provisoire','Lancement définitif',tol='1')
    assert put(c,va,'quantite_lancement','1500').status_code==201
    assert put(c,vb,'quantite_lancement','1450').status_code==201
    assert put(c,va,'quantite_lancement','1600').status_code==409
    report=c.get(f'/api/launches/{lid}/quality').json()
    assert report['counts']['difference']==1
    mismatch=report['rows'][0]
    assert mismatch['pair'][0]['value']=='1500' and mismatch['pair'][1]['value']=='1450'
    assert c.post(f'/api/launches/{lid}/quality/{rid}/decisions',json={
        'signature':mismatch['signature'],'decision':'justified','note':'Réduction validée après le provisoire'},headers=H).status_code==201
    again=c.get(f'/api/launches/{lid}/quality').json()['rows'][0]
    assert again['decision']['status']=='justified'
    changed=c.post(f'/api/documents/{b}/versions',files={'file':('v2.txt',b'Nouvelle version definitive')},headers=H)
    assert changed.status_code==201
    next_report=c.get(f'/api/launches/{lid}/quality').json()['rows'][0]
    assert next_report['status']=='unavailable' and 'decision' not in next_report
    old=c.post(f'/api/launches/{lid}/quality/{rid}/decisions',json={
        'signature':mismatch['signature'],'decision':'justified','note':'La situation semble identique'},headers=H)
    assert old.status_code==409


def test_qualified_tolerance_and_incompatible_units(c):
    lid=launch(c)
    _,a=doc(c,lid,'Commande client')
    _,b=doc(c,lid,'Fiche contrôle')
    rule(c,'Commande client','Fiche contrôle',tol='5')
    assert put(c,a,'quantite_lancement','1450','pièce').status_code==201
    assert put(c,b,'quantite_lancement','1454','pièce').status_code==201
    assert c.get(f'/api/launches/{lid}/quality').json()['rows'][0]['status']=='consistent'
    assert put(c,b,'prix_unitaire','2','MAD/pièce').status_code==201
    assert c.post('/api/admin/quality-rules',json={'name':'Prix quantite', 'field_key':'prix_unitaire',
        'left_doc_type':'Commande client','right_doc_type':'Fiche contrôle','left_folder':'jaune','right_folder':'jaune','tolerance':'NaN'},headers=H).status_code==422
    assert c.post('/api/admin/quality-rules',json={'name':'Prix quantite', 'field_key':'prix_unitaire',
        'left_doc_type':'Commande client','right_doc_type':'Fiche contrôle','left_folder':'jaune','right_folder':'jaune','tolerance':'-1'},headers=H).status_code==422


def test_role_cannot_see_cross_folder_evidence(c):
    lid=launch(c)
    _,va=doc(c,lid,'Fiche jaune')
    _,vb=doc(c,lid,'Bon rose','rose')
    rule(c,'Fiche jaune','Bon rose','jaune','rose')
    assert put(c,va,'quantite_lancement','2').status_code==201
    assert put(c,vb,'quantite_lancement','3').status_code==201
    login(c,'tech@q.local')
    assert c.get(f'/api/launches/{lid}/quality').json()['rows']==[]
    assert c.post(f'/api/document-versions/{vb}/data',json={'field_key':'prix_unitaire','value':'4','unit':'MAD/pièce'},headers=H).status_code==403
    login(c,'rose@q.local')
    assert c.get(f'/api/launches/{lid}/quality').json()['rows']==[]


def xlsx_bytes(formula:str|None, second:bool=False):
    w=Workbook();s=w.active;s.title='Couts';s['A1']=1500;s['A2']=1.9;s['B1']=formula if formula is not None else 2850
    if second:s['B2']='=#REF!+A2'
    stream=io.BytesIO();w.save(stream);return stream.getvalue()


def test_excel_formula_replacement_and_broken_reference(c):
    lid=launch(c)
    did,v1=doc(c,lid,'Fiche emploi Excel',filename='f1.xlsx',data=xlsx_bytes('=A1*A2'))
    items=c.get(f'/api/launches/{lid}/excel-inspections').json()
    assert len(items)==1 and items[0]['inspection']['status']=='first_version'
    assert items[0]['inspection']['formula_count']==1
    uploaded=c.post(f'/api/documents/{did}/versions',files={'file':('f2.xlsx',xlsx_bytes(None,True))},headers=H)
    assert uploaded.status_code==201,uploaded.text
    rows=c.get(f'/api/launches/{lid}/excel-inspections').json()
    v2=next(x for x in rows if x['version']==2)['inspection']
    assert v2['status']=='reviewed'
    assert any(f['type']=='formula_removed' and f['cell']=='B1' for f in v2['findings'])
    assert any(f['type']=='broken_reference' and f['cell']=='B2' for f in v2['findings'])
    login(c,'rose@q.local')
    assert c.get(f'/api/launches/{lid}/excel-inspections').json()==[]


def test_excel_change_not_automatically_declared_error(c):
    lid=launch(c)
    did,_=doc(c,lid,'Prix Excel',filename='f1.xlsx',data=xlsx_bytes('=A1*A2'))
    r=c.post(f'/api/documents/{did}/versions',files={'file':('f2.xlsx',xlsx_bytes('=A1*A2+1'))},headers=H)
    assert r.status_code==201
    v2=c.get(f'/api/launches/{lid}/excel-inspections').json()[1]['inspection']
    assert any(x['type']=='formula_changed' and x['level']=='warning' for x in v2['findings'])
    assert not any(x['type']=='formula_removed' for x in v2['findings'])
