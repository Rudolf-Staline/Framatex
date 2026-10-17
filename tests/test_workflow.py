"""Incrément 0.3 — tests des validations, valeurs, alertes et cloisonnement."""
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-workflow-')
os.environ['FRAMATEX_SECRET_KEY'] = 'workflow-test-secret-' * 3

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import SessionLocal, hash_password, Base, engine
from app.models import Role, RolePermission, User

H = {'X-Framatex-Request':'1'}

@pytest.fixture()
def c():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            yellow=Role(name='Technique')
            yellow.grants=[RolePermission(action='launch.read'),
                           RolePermission(action='document.read',folder_slug='jaune'),
                           RolePermission(action='document.review',folder_slug='jaune'),
                           RolePermission(action='value.write',folder_slug='jaune'),
                           RolePermission(action='impact.review',folder_slug='jaune')]
            rose=Role(name='Réception')
            rose.grants=[RolePermission(action='launch.read'), RolePermission(action='document.read',folder_slug='rose'),
                         RolePermission(action='impact.review',folder_slug='rose')]
            db.add_all([User(name='Admin',email='admin@t.local',password_hash=hash_password('TestPassword2026!'),roles=[admin]),
                        User(name='Technique',email='tech@t.local',password_hash=hash_password('TestPassword2026!'),roles=[yellow]),
                        User(name='Reception',email='rose@t.local',password_hash=hash_password('TestPassword2026!'),roles=[rose])])
            db.commit()
        login(client,'admin@t.local')
        yield client
    Base.metadata.drop_all(engine)

def login(c,email):
    r=c.post('/api/auth/login',json={'email':email,'password':'TestPassword2026!'},headers=H)
    assert r.status_code==200,r.text

def setup(c):
    launch=c.post('/api/launches',json={'name':'Vestes pilotes 2026'},headers=H)
    assert launch.status_code==201,launch.text
    lid=launch.json()['id']
    file=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche emploi', 'doc_type':'Fiche d’emploi'},
                files={'file':('fiche.txt',b'Consommation tissu: 1,8 m par veste','text/plain')},headers=H)
    assert file.status_code==201,file.text
    return lid,file.json()['id'],file.json()['latest']['id']


def test_decision_version_history_and_completeness(c):
    lid,did,ver1=setup(c)
    profile=c.post('/api/admin/completeness/profiles',json={'name':'Pilote avancé'},headers=H).json()['id']
    rid=c.post(f'/api/admin/completeness/profiles/{profile}/rules',json={'title':'Fiche validée','document_type':'Fiche d’emploi',
        'folder':'jaune','requires_validation':True},headers=H).json()['id']
    c.patch(f'/api/launches/{lid}/completeness/context',json={'profile_id':profile,'phase':'preparation'},headers=H)
    assert c.get(f'/api/launches/{lid}/completeness').json()['rows'][0]['status']=='pending_validation'
    rejected=c.post(f'/api/documents/{did}/reviews',json={'decision':'rejected','comment':'Erreur de matière à corriger'},headers=H)
    assert rejected.status_code==201,rejected.text
    assert c.post(f'/api/launches/{lid}/completeness/rules/{rid}/validate',json={'document_id':did},headers=H).status_code==409
    approved=c.post(f'/api/documents/{did}/reviews',json={'decision':'approved','comment':'Révision contrôlée et acceptée'},headers=H)
    assert approved.status_code==201
    assert c.get(f'/api/launches/{lid}/completeness').json()['rows'][0]['status']=='present'
    file=c.post(f'/api/documents/{did}/versions',files={'file':('fiche-v2.txt',b'Consommation 1,9 m','text/plain')},headers=H)
    assert file.status_code==201,file.text
    reviews=c.get(f'/api/launches/{lid}/reviews').json()
    assert reviews[0]['status']=='to_review' and len(reviews[0]['history'])==2
    assert c.get(f'/api/launches/{lid}/completeness').json()['rows'][0]['status']=='pending_validation'
    assert c.post(f'/api/documents/{did}/reviews',json={'decision':'changes_requested','comment':'trop court'},headers=H).status_code==422
    assert c.post(f'/api/documents/{did}/reviews',json={'decision':'changes_requested','comment':'Une quantité semble incorrecte'},headers=H).status_code==201
    assert c.get(f'/api/launches/{lid}/completeness').json()['rows'][0]['status']=='pending_validation'
    assert c.post(f'/api/documents/{did}/reviews',json={'decision':'approved'},headers=H).status_code==201
    assert c.get(f'/api/launches/{lid}/completeness').json()['rows'][0]['status']=='present'


def test_values_revision_impacts_and_decision(c):
    lid,did,ver1=setup(c)
    rule=c.post('/api/admin/impact-rules',json={'name':'Consommation vers achats','source_kind':'value',
              'source_key':'consommation_matiere','source_folder':'jaune','target_folder':'jaune',
              'instruction':'Vérifier le besoin matière et les achats'},headers=H)
    assert rule.status_code==201,rule.text
    base={'key':'consommation_matiere','value':'1,8','unit':'m/pièce','source_version_id':ver1}
    r1=c.post(f'/api/launches/{lid}/values',json=base,headers=H)
    assert r1.status_code==201,r1.text
    assert c.get(f'/api/launches/{lid}/impacts').json()==[]
    assert c.post(f'/api/launches/{lid}/values',json={**base,'value':'NaN','reason':'une modification importante'},headers=H).status_code==422
    assert c.post(f'/api/launches/{lid}/values',json={**base,'value':'1.9','unit':'km','reason':'modification justifiée'},headers=H).status_code==409
    assert c.post(f'/api/launches/{lid}/values',json={**base,'value':'1.9','reason':'court'},headers=H).status_code==422
    second=c.post(f'/api/launches/{lid}/values',json={**base,'value':'1.9','reason':'Nouvelle consommation confirmée'},headers=H)
    assert second.status_code==201,second.text
    vals=c.get(f'/api/launches/{lid}/values').json()
    assert len(vals)==1 and vals[0]['current']['value']=='1.9' and len(vals[0]['history'])==2
    alerts=c.get(f'/api/launches/{lid}/impacts').json()
    assert len(alerts)==1 and alerts[0]['old_value']=='1.8 m/pièce' and alerts[0]['new_value']=='1.9 m/pièce'
    assert alerts[0]['can_review']
    assert c.post('/api/impacts/'+alerts[0]['id']+'/decision',json={'status':'acknowledged','note':'court'},headers=H).status_code==422
    ack=c.post('/api/impacts/'+alerts[0]['id']+'/decision',json={'status':'action_required',
        'note':'Le recalcul des besoins doit être effectué'},headers=H)
    assert ack.status_code==200 and ack.json()['status']=='action_required'
    done=c.post('/api/impacts/'+alerts[0]['id']+'/decision',json={'status':'acknowledged',
        'note':'Les achats ont vérifié les besoins mis à jour'},headers=H)
    assert done.status_code==200 and done.json()['status']=='acknowledged'
    assert c.post('/api/impacts/'+alerts[0]['id']+'/decision',json={'status':'acknowledged',
        'note':'Deuxième accusé refusé'},headers=H).status_code==409


def test_document_change_triggers_specific_rule(c):
    lid,did,ver1=setup(c)
    r=c.post('/api/admin/impact-rules',json={'name':'Mise à jour fiche d’emploi','source_kind':'document',
        'source_key':'Fiche d’emploi','source_folder':'jaune','target_folder':'rose',
        'instruction':'Vérifier les documents de réception concernés'},headers=H)
    assert r.status_code==201,r.text
    new=c.post(f'/api/documents/{did}/versions',files={'file':('v2.txt',b'Valeur revisee','text/plain')},headers=H)
    assert new.status_code==201,new.text
    alerts=c.get(f'/api/launches/{lid}/impacts').json()
    assert len(alerts)==1 and alerts[0]['source_kind']=='document' and alerts[0]['target_folder']=='rose'
    assert alerts[0]['new_value']=='v2'


def test_permissions_source_and_target_not_leaked(c):
    lid,did,ver=setup(c)
    c.post('/api/admin/impact-rules',json={'name':'Alerte inter-service','source_kind':'value',
        'source_key':'consommation_matiere','source_folder':'jaune','target_folder':'rose',
        'instruction':'Comparer les quantités avec les pièces reçues'},headers=H)
    initial={'key':'consommation_matiere','value':'1.8','unit':'m/pièce','source_version_id':ver}
    c.post(f'/api/launches/{lid}/values',json=initial,headers=H)
    c.post(f'/api/launches/{lid}/values',json={**initial,'value':'1.9','reason':'Changement de consommation confirmé'},headers=H)
    alert_id=c.get(f'/api/launches/{lid}/impacts').json()[0]['id']
    login(c,'rose@t.local')
    assert c.get(f'/api/launches/{lid}/values').json()==[]
    assert c.get(f'/api/launches/{lid}/impacts').json()==[]
    assert c.get(f'/api/launches/{lid}/reviews').json()==[]
    assert c.post(f'/api/impacts/{alert_id}/decision',json={'status':'acknowledged','note':'Réception vérifiée'},headers=H).status_code==403
    assert c.post(f'/api/documents/{did}/reviews',json={'decision':'approved'},headers=H).status_code==403
    assert c.post(f'/api/launches/{lid}/values',json=initial,headers=H).status_code==403
    login(c,'tech@t.local')
    assert c.get(f'/api/launches/{lid}/values').json()[0]['current']['value']=='1.9'
    assert c.get(f'/api/launches/{lid}/impacts').json()==[]
    assert c.post(f'/api/impacts/{alert_id}/decision',json={'status':'acknowledged','note':'Vérification réalisée'},headers=H).status_code==403
    assert c.post('/api/admin/impact-rules',json={'name':'Nope','source_kind':'value','source_key':'consommation_matiere',
        'source_folder':'jaune','target_folder':'jaune','instruction':'Instruction interdite'},headers=H).status_code==403
