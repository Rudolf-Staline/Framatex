"""Scénarios indépendants pour le moteur de complétude et ses droits."""
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-completeness-')
os.environ['FRAMATEX_SECRET_KEY'] = 'completeness-secret-' * 3

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User

H = {'X-Framatex-Request': '1'}

@pytest.fixture()
def client():
    # Database par fixture avec schéma supprimé à la fermeture ; pas de dépendance aux autres tests.
    from app.core import Base, engine
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        with SessionLocal() as db:
            a = Role(name='Administrateur')
            r = Role(name='Réception')
            r.grants = [RolePermission(action='launch.read'),
                        RolePermission(action='document.read', folder_slug='rose'),
                        RolePermission(action='document.write', folder_slug='rose')]
            admin = User(name='Responsable', email='responsable@test.local', password_hash=hash_password('LongPassword2026!'), roles=[a])
            worker = User(name='Réception', email='reception@test.local', password_hash=hash_password('LongPassword2026!'), roles=[r])
            db.add_all([admin, worker]); db.commit()
        c.post('/api/auth/login', json={'email':'responsable@test.local','password':'LongPassword2026!'}, headers=H)
        yield c
    Base.metadata.drop_all(engine)


def setup(c):
    l = c.post('/api/launches', json={'name':'Lancement fictif 2026'}, headers=H).json()
    p = c.post('/api/admin/completeness/profiles', json={'name':'Profil pilote', 'description':'Données fictives'}, headers=H)
    assert p.status_code == 201, p.text
    pid = p.json()['id']
    rules = {}
    for typ, folder, phase, validate in [('Fiche d’emploi','jaune','preparation', True),
                                         ('Bon de livraison','rose','approvisionnement',False),
                                         ('Facture','vert','cloture',False)]:
        r = c.post(f'/api/admin/completeness/profiles/{pid}/rules',json={
            'title':typ, 'document_type':typ, 'folder':folder,
            'due_phase':phase, 'requires_validation':validate}, headers=H)
        assert r.status_code==201, r.text
        rules[typ] = r.json()['id']
    ctx=c.patch(f"/api/launches/{l['id']}/completeness/context",json={'profile_id':pid,'phase':'preparation'},headers=H)
    assert ctx.status_code==200,ctx.text
    return l['id'],pid,rules


def check(c, lid):
    r=c.get(f'/api/launches/{lid}/completeness')
    assert r.status_code==200, r.text
    return {row['document_type']: row for row in r.json()['rows']}


def test_unconfigured_does_not_imply_complete(client):
    c=client
    lid=c.post('/api/launches',json={'name':'Sans profil'},headers=H).json()['id']
    d=c.get(f'/api/launches/{lid}/completeness').json()
    assert not d['configured'] and d['visible_rules']==0 and d['due_count']==0


def test_document_due_and_version_validation(client):
    c=client; lid,pid,rules=setup(c)
    rows=check(c,lid)
    assert rows['Fiche d’emploi']['status']=='missing'
    assert rows['Bon de livraison']['status']=='not_due'
    assert rows['Facture']['status']=='not_due'
    doc=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche originale', 'doc_type':'Fiche d’emploi'},
               files={'file':('fiche.txt',b'ancienne valeur','text/plain')},headers=H)
    assert doc.status_code==201
    did=doc.json()['id']
    assert check(c,lid)['Fiche d’emploi']['status']=='pending_validation'
    check_review=c.post(f'/api/launches/{lid}/completeness/rules/{rules["Fiche d’emploi"]}/validate',
                        json={'document_id':did},headers=H)
    assert check_review.status_code==200,check_review.text
    assert check(c,lid)['Fiche d’emploi']['status']=='present'
    assert c.post(f'/api/launches/{lid}/completeness/rules/{rules["Fiche d’emploi"]}/validate',
                  json={'document_id':did},headers=H).status_code==409
    v=c.post(f'/api/documents/{did}/versions',files={'file':('fiche-v2.txt',b'nouvelle valeur','text/plain')},headers=H)
    assert v.status_code==201
    assert check(c,lid)['Fiche d’emploi']['status']=='pending_validation'
    assert c.post(f'/api/launches/{lid}/completeness/rules/{rules["Fiche d’emploi"]}/validate',
                  json={'document_id':did},headers=H).status_code==200
    assert check(c,lid)['Fiche d’emploi']['status']=='present'


def test_due_stage_exception_and_revocation(client):
    c=client; lid, pid, rules=setup(c)
    c.patch(f'/api/launches/{lid}/completeness/context',json={'profile_id':pid,'phase':'approvisionnement'},headers=H)
    assert check(c,lid)['Bon de livraison']['status']=='missing'
    ex=c.put(f'/api/launches/{lid}/completeness/rules/{rules["Bon de livraison"]}/exception',
             json={'active':True,'reason':'Attente du document validée par le service fournisseur.'},headers=H)
    assert ex.status_code==200,ex.text
    assert check(c,lid)['Bon de livraison']['status']=='exception'
    assert c.put(f'/api/launches/{lid}/completeness/rules/{rules["Bon de livraison"]}/exception',
                 json={'active':False},headers=H).status_code==200
    assert check(c,lid)['Bon de livraison']['status']=='missing'
    assert c.put(f'/api/launches/{lid}/completeness/rules/{rules["Bon de livraison"]}/exception',
                 json={'active':True,'reason':'Trop court'},headers=H).status_code==422
    assert c.patch(f'/api/launches/{lid}/completeness/context', json={'profile_id':pid, 'phase':'inconnue'},headers=H).status_code==422


def test_permissions_and_invalid_validation(client):
    c=client; lid,pid,rules=setup(c)
    doc=c.post(f'/api/launches/{lid}/documents',data={'folder':'rose','title':'BL','doc_type':'Bon de livraison'},
               files={'file':('bl.txt',b'bon de livraison','text/plain')},headers=H).json()
    wrong=c.post(f'/api/launches/{lid}/completeness/rules/{rules["Fiche d’emploi"]}/validate',
                 json={'document_id':doc['id']},headers=H)
    assert wrong.status_code==422
    c.post('/api/auth/login',json={'email':'reception@test.local','password':'LongPassword2026!'},headers=H)
    data=c.get(f'/api/launches/{lid}/completeness').json()
    assert [r['folder'] for r in data['rows']]==['rose']
    assert data['partial_visibility'] is True
    assert data['counts']['missing']==0  # Les exigences de Jaune sont cachées.
    assert c.get('/api/admin/completeness/profiles').status_code==403
    assert c.patch(f'/api/launches/{lid}/completeness/context',json={'profile_id':pid,'phase':'fabrication'},headers=H).status_code==403
    assert c.post(f'/api/launches/{lid}/completeness/rules/{rules["Fiche d’emploi"]}/validate',json={'document_id':doc['id']},headers=H).status_code==403
    assert c.put(f'/api/launches/{lid}/completeness/rules/{rules["Bon de livraison"]}/exception',json={'reason':'Justification test autorisation'},headers=H).status_code==403
    assert c.post('/api/admin/completeness/profiles',json={'name':'Interdit'},headers=H).status_code==403
    assert c.get(f'/api/launches/{lid}/completeness').status_code==200
