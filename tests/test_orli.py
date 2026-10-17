"""0.11 : aucune synchro ORLI implicite, permissions et confirmation explicite."""
from __future__ import annotations
import io
import json
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR']=tempfile.mkdtemp(prefix='framat-orli-v11-')
os.environ['FRAMATEX_SECRET_KEY']='temporary-test-orli-secret-'*3
from fastapi.testclient import TestClient
from sqlalchemy import select
from openpyxl import Workbook
from app.main import app
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User, Launch
from app.orli_models import OrliLink, OrliImportBatch

H={'X-Framatex-Request':'1'}
PASS='AReallyLongDemoPassword2026!'
MAP={'orli_ref':'Lancement','order_ref':'Commande','client_name':'Client','designation':'Article','quantity':'Quantite'}


def auth(c,email):
    r=c.post('/api/auth/login',headers=H,json={'email':email,'password':PASS})
    assert r.status_code==200,r.text


def launch(c,name,**kwargs):
    r=c.post('/api/launches',headers=H,json={'name':name,**kwargs})
    assert r.status_code==201,r.text
    return r.json()['id']


def post_csv(c,body,mapping=MAP):
    return c.post('/api/orli/imports',headers=H,
                  data={'mapping':json.dumps(mapping)},
                  files={'file':('export_orli.csv',body.encode('utf-8'),'text/csv')})


def init():
    with SessionLocal() as db:
        admin=db.scalar(select(Role).where(Role.name=='Administrateur')) or Role(name='Administrateur')
        reader=Role(name='Lecteur ORLI')
        reader.grants=[RolePermission(action='launch.read')]
        editor=Role(name='Éditeur ORLI')
        editor.grants=[RolePermission(action='launch.read'),RolePermission(action='launch.update')]
        db.add_all([User(email='orli-admin@demo.local',name='Admin',password_hash=hash_password(PASS),roles=[admin]),
                    User(email='orli-viewer@demo.local',name='Lecteur',password_hash=hash_password(PASS),roles=[reader]),
                    User(email='orli-editor@demo.local',name='Éditeur',password_hash=hash_password(PASS),roles=[editor])]);db.commit()


def test_import_reconciliation_non_destructive_and_roles():
 with TestClient(app) as c:
    init();auth(c,'orli-admin@demo.local')
    l1=launch(c,'Vestes test',order_ref='CMD-42',client_name='Client bleu')
    l2=launch(c,'Vestes second',order_ref='CMD-99')
    raw='Lancement;Commande;Client;Article;Quantite\nOR-001;CMD-42;Client bleu;Vestes;1500\nOR-002;CMD-99;Autre Client;Vestes;900\n'
    r=post_csv(c,raw);assert r.status_code==201,r.text
    assert r.json()['total_rows']==2 and r.json()['valid_rows']==2
    batch=r.json()['id'];items=c.get('/api/orli/imports/'+batch).json()['rows']
    rec=items[0]
    assert c.get(f'/api/launches/{l1}').json()['orli_ref'] is None
    view=c.get(f'/api/launches/{l1}/orli-reconciliation').json()
    assert len(view['candidates'])==1 and view['candidates'][0]['id']==rec['id']
    assert c.post(f'/api/launches/{l1}/orli-reconciliation/link',headers=H,json={
        'record_id':rec['id'],'confirmation':False,'reason':'Correspondance vérifiée en interne'}).status_code==422
    assert c.post(f'/api/launches/{l1}/orli-reconciliation/link',headers=H,json={
        'record_id':rec['id'],'confirmation':True,'reason':'Correspondance vérifiée en interne'}).status_code==201
    assert c.get(f'/api/launches/{l1}').json()['orli_ref']=='OR-001'
    assert c.post(f'/api/launches/{l2}/orli-reconciliation/link',headers=H,json={
        'record_id':rec['id'],'confirmation':True,'reason':'Rapprochement volontaire mais incorrect'}).status_code==409
    assert c.patch(f'/api/launches/{l1}',headers=H,json={'orli_ref':'OR-XXX'}).status_code==409
    assert c.get('/api/orli/imports/'+batch).json()['rows'][0]['linked_launch_id']==l1
    with SessionLocal() as db:
        assert db.scalar(select(OrliLink).where(OrliLink.launch_id==l1))
        assert db.scalar(select(Launch).where(Launch.id==l1)).order_ref=='CMD-42'
    auth(c,'orli-viewer@demo.local')
    assert c.get('/api/orli/imports').status_code==403
    assert c.get('/api/orli/imports/'+batch).status_code==403
    assert post_csv(c,raw).status_code==403
    assert c.get(f'/api/launches/{l1}/orli-reconciliation').status_code==200
    assert c.post(f'/api/launches/{l2}/orli-reconciliation/link',headers=H,json={
        'record_id':items[1]['id'],'confirmation':True,'reason':'La commande correspond exactement'}).status_code==403
    auth(c,'orli-editor@demo.local')
    assert c.post(f'/api/launches/{l2}/orli-reconciliation/link',headers=H,json={
        'record_id':items[1]['id'],'confirmation':True,'reason':'La commande est vérifiée avec le responsable'}).status_code==201


def test_invalid_duplicates_and_conflicts():
 with TestClient(app) as c:
    auth(c,'orli-admin@demo.local')
    l=launch(c,'Lot avec conflit',order_ref='ABC-10',client_name='Client A')
    duplicates='Lancement;Commande;Client;Article;Quantite\n OR-3 ;ABC-10;Client A;Vestes;12\nor-3;ABC-11;Client A;Vestes;13\n;ABC-13;Client A;Vestes;14\n'
    r=post_csv(c,duplicates);assert r.status_code==201,r.text
    assert r.json()['valid_rows']==0
    rows=c.get('/api/orli/imports/'+r.json()['id']).json()['rows']
    assert all(x['errors'] for x in rows)
    assert c.post(f'/api/launches/{l}/orli-reconciliation/link',headers=H,json={
        'record_id':rows[0]['id'],'confirmation':True,'reason':'Justification vérifiée par les services'}).status_code==422
    r=post_csv(c,'Lancement;Commande;Client;Article;Quantite\nOR-4;ABC-10;Client B;Vestes;42\n')
    assert r.status_code==201
    record=c.get('/api/orli/imports/'+r.json()['id']).json()['rows'][0]
    suggestions=c.get(f'/api/launches/{l}/orli-reconciliation').json()['candidates']
    assert any(x['id']==record['id'] and 'client' in x['conflicts'] for x in suggestions)
    req={'record_id':record['id'],'confirmation':True,'reason':'Les personnes ont validé ce rapprochement'}
    assert c.post(f'/api/launches/{l}/orli-reconciliation/link',headers=H,json=req).status_code==409
    assert c.post(f'/api/launches/{l}/orli-reconciliation/link',headers=H,json={**req,'override_conflicts':True}).status_code==201


def test_schema_csv_xlsx_errors():
 with TestClient(app) as c:
    auth(c,'orli-admin@demo.local')
    assert post_csv(c,'Inconnue,Commande\nOR-1,CMD-1\n').status_code==422
    assert post_csv(c,'Lancement,Commande\nOR-1,CMD-1\n',mapping={'orli_ref':'Lancement','ordre_mauvais':'Commande'}).status_code==422
    assert post_csv(c,'Lancement,Commande\nOR-1,CMD-1\n',mapping={'orli_ref':'Lancement','order_ref':'Lancement'}).status_code==422
    wb=Workbook();ws=wb.active
    ws.append(['Lancement','Commande','Client','Article','Quantite'])
    ws.append(['OR-XL','CMD-XL','Client XLSX','Veste','1450'])
    stream=io.BytesIO();wb.save(stream)
    resp=c.post('/api/orli/imports',headers=H,data={'mapping':json.dumps(MAP)},
          files={'file':('export_orli.xlsx',stream.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert resp.status_code==201,resp.text
    batch=c.get('/api/orli/imports/'+resp.json()['id']).json()
    assert batch['rows'][0]['orli_ref']=='OR-XL'
