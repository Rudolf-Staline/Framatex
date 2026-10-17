"""0.10 : scenario sourcé, droits, confidentialité, aucun changement en base."""
from __future__ import annotations
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-sim-v10-')
os.environ['FRAMATEX_SECRET_KEY'] = 'framat-v10-test-secret-' * 4

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core import SessionLocal, hash_password
from app.models import User, Role, RolePermission
from app.workflow_models import BusinessValueRevision
from app.impact_sim_models import ImpactSimulation

H={'X-Framatex-Request':'1'}
PASS='DemoScenarioPassword2026!!'


def login(client, mail):
    res = client.post('/api/auth/login', headers=H, json={'email': mail, 'password': PASS})
    assert res.status_code == 200, res.text


def file_version(client, launch, name='Document source'):
    res = client.post(f'/api/launches/{launch}/documents', headers=H,
                      data={'folder':'jaune','title':name,'doc_type':'Fiche d’emploi'},
                      files={'file': ('source.txt', b'Valeur originale verifiee', 'text/plain')})
    assert res.status_code == 201, res.text
    return res.json()['id'], res.json()['latest']['id']


def field(client, launch, key, value, version):
    units={'quantite_lancement':'pièce','consommation_matiere':'m/pièce','cout_matiere_unitaire':'MAD/m'}
    r=client.post(f'/api/launches/{launch}/values',headers=H,json={
        'key':key, 'value':value, 'unit':units[key], 'source_version_id':version})
    assert r.status_code==201, r.text


def test_scenarios_graph_privacy_and_immutable_history():
  with TestClient(app) as c:
    with SessionLocal() as db:
      admin=Role(name='Administrateur'); rose=Role(name='Collaborateur rose')
      rose.grants=[RolePermission(action='launch.read'), RolePermission(action='document.read',folder_slug='rose')]
      tech=Role(name='Lecteur jaune')
      tech.grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='jaune')]
      people=[User(email='admin-v10@test.local',name='Administrateur',password_hash=hash_password(PASS),roles=[admin]),
              User(email='rose-v10@test.local',name='Réception',password_hash=hash_password(PASS),roles=[rose]),
              User(email='tech-v10@test.local',name='Technique',password_hash=hash_password(PASS),roles=[tech])]
      db.add_all(people);db.commit()
    login(c, 'admin-v10@test.local')
    launch=c.post('/api/launches',headers=H,json={'name':'Vestes bleues lot 2026'}).json()['id']
    doc_id,version=file_version(c,launch)
    field(c,launch,'quantite_lancement','1500',version)
    field(c,launch,'consommation_matiere','1.8',version)
    field(c,launch,'cout_matiere_unitaire','25',version)
    graph=c.get(f'/api/launches/{launch}/dependency-graph')
    assert graph.status_code==200
    assert len(graph.json()['nodes'])==5 and len(graph.json()['edges'])==4
    assert next(node for node in graph.json()['nodes'] if node['id']=='besoin_calcule')['value']=='2700.0'
    simulate=c.post(f'/api/launches/{launch}/impact-simulations',headers=H,json={
        'title':'Consommation revisee', 'changes':{'consommation_matiere':'1.9'}, 'save':True})
    assert simulate.status_code==200,simulate.text
    data=simulate.json()
    assert data['saved'] is True and data['saved_id']
    results={o['key']:o for o in data['result']['outputs']}
    assert results['besoin_calcule']['baseline']=='2700.0'
    assert results['besoin_calcule']['scenario']=='2850.0'
    assert results['besoin_calcule']['delta']=='150.0'
    assert results['cout_matiere_estime']['delta']=='3750.0'
    assert 'pièce' in data['result']['sources']['quantite_lancement']['unit']
    with SessionLocal() as db:
      revisions=db.scalars(select(BusinessValueRevision)).all()
      assert len(revisions)==3
      assert next(x for x in revisions if x.key=='consommation_matiere').value_text=='1.8'
      assert len(db.scalars(select(ImpactSimulation)).all())==1
    assert c.get(f'/api/launches/{launch}/impact-simulations').json()[0]['id']==data['saved_id']
    # Nouvelle version : la reference devient obsolete, sans recalcul retroactif du scenario archive.
    changed=c.post(f'/api/documents/{doc_id}/versions',headers=H,files={
        'file':('nouveau.txt',b'Consommation revisee a 1.9','text/plain')})
    assert changed.status_code==201
    preview=c.post(f'/api/launches/{launch}/impact-simulations',headers=H,json={
        'title':'Revue documentaire','changes':{'quantite_lancement':'1450'}})
    assert preview.status_code==200 and not preview.json()['saved']
    assert any('ancienne version' in x for x in preview.json()['result']['warnings'])
    assert len(c.get(f'/api/launches/{launch}/impact-simulations').json())==1
    # Un role Rose ne voit aucune valeur, noeud, arête, simulation ou historique.
    login(c, 'rose-v10@test.local')
    assert c.get(f'/api/launches/{launch}/dependency-graph').json()=={'nodes':[],'edges':[],'limited':True}
    assert c.get(f'/api/launches/{launch}/impact-simulations').status_code==403
    assert c.post(f'/api/launches/{launch}/impact-simulations',headers=H,json={
        'changes':{'quantite_lancement':'1400'}}).status_code==403
    # Un role lecteur Jaune peut simuler, mais pas archiver sans droit d'ecriture.
    login(c,'tech-v10@test.local')
    assert len(c.get(f'/api/launches/{launch}/dependency-graph').json()['nodes'])==5
    assert c.post(f'/api/launches/{launch}/impact-simulations',headers=H,json={
        'changes':{'quantite_lancement':'1400'},'save':False}).status_code==200
    assert c.post(f'/api/launches/{launch}/impact-simulations',headers=H,json={
        'changes':{'quantite_lancement':'1400'},'save':True}).status_code==403


def test_input_validation_and_missing_sources():
    with TestClient(app) as c:
      login(c,'admin-v10@test.local')
      launch=c.post('/api/launches',headers=H,json={'name':'Fabrication sans chiffres'}).json()['id']
      path=f'/api/launches/{launch}/impact-simulations'
      for values in ({'quantite_lancement':'2'}, {'secret':'4'}, {'quantite_lancement':'NaN'}, {}):
        res=c.post(path,headers=H,json={'changes': values})
        assert res.status_code==422,res.text
      doc,version=file_version(c,launch,'Fiche partielle')
      field(c,launch,'quantite_lancement','1500',version)
      valid=c.post(path,headers=H,json={'changes':{'quantite_lancement':'1450'}})
      assert valid.status_code==200,valid.text
      assert valid.json()['result']['outputs'][0]['scenario'] is None
      assert len(c.get(f'/api/launches/{launch}/impact-simulations').json())==0
      for invalid in ('NaN','Infinity','-1','1.00001','9999999999'):
        res=c.post(path,headers=H,json={'changes':{'quantite_lancement':invalid}})
        assert res.status_code==422,(invalid,res.text)
