"""0.7 — exigences traçables, ambiguïtés et autorisations croisées."""
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-spec-')
os.environ['FRAMATEX_SECRET_KEY'] = 'spec-test-secret-long-and-private'*2

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role, RolePermission
from app.spec_analysis import analyze_text

H={'X-Framatex-Request':'1'}
PASSWORD='StrongSpecification11!'

@pytest.fixture
def c():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            tech=Role(name='Technique',grants=[RolePermission(action='launch.read'),
                 RolePermission(action='document.read',folder_slug='jaune'),
                 RolePermission(action='document.write',folder_slug='jaune')])
            reviewer=Role(name='Contrôle technique',grants=[RolePermission(action='launch.read'),
                 RolePermission(action='document.read',folder_slug='jaune'),
                 RolePermission(action='document.write',folder_slug='jaune'),
                 RolePermission(action='requirement.review',folder_slug='jaune'),
                 RolePermission(action='ambiguity.review',folder_slug='jaune')])
            reception=Role(name='Réception',grants=[RolePermission(action='launch.read'),
                 RolePermission(action='document.read',folder_slug='rose'),
                 RolePermission(action='document.write',folder_slug='rose')])
            for email,name,role in [('admin@spec.test','Admin',admin),('tech@spec.test','Technicien',tech),
                                     ('review@spec.test','Contrôle',reviewer),('rose@spec.test','Réception',reception)]:
                db.add(User(name=name,email=email,password_hash=hash_password(PASSWORD),roles=[role]))
            db.commit()
        login(client,'admin@spec.test')
        yield client
    Base.metadata.drop_all(engine)


def login(client,email):
    r=client.post('/api/auth/login',json={'email':email,'password':PASSWORD},headers=H)
    assert r.status_code==200,r.text


def launch(c,name='Chemises tests'):
    r=c.post('/api/launches',json={'name':name},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']


def upload(c,lid,title,text,folder='jaune',doctype='Dossier technique'):
    r=c.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':title,'doc_type':doctype},
             files={'file':(title+'.txt',text.encode('utf8'),'text/plain')},headers=H)
    assert r.status_code==201,r.text
    return r.json()


def requirement(c,lid,vid):
    r=c.post(f'/api/launches/{lid}/requirements',json={'source_version_id':vid,
             'title':'Tolérance des manches', 'category':'Dimensions',
             'description':'La longueur des manches doit respecter une tolérance de +/- 0,5 cm.',
             'source_excerpt':'Longueur manches : tolérance +/- 0,5 cm'},headers=H)
    assert r.status_code==201,r.text
    return r.json()


def test_suggestions_are_only_suggestions_and_human_confirmations(c):
    lid=launch(c)
    doc=upload(c,lid,'TechPack','Boutons référence B-21 obligatoires.\nUtiliser une fermeture légèrement plus résistante que le modèle précédent.')
    vid=doc['latest']['id']
    result=c.get(f'/api/document-versions/{vid}/spec-suggestions')
    assert result.status_code==200,result.text
    body=result.json()
    assert body['human_confirmation_required'] and len(body['requirements'])>=1
    assert any(a['kind']=='intensite_imprecise' for a in body['ambiguities'])
    assert c.get(f'/api/launches/{lid}/specifications').json()['coverage']['visible_total']==0
    row=requirement(c,lid,vid)
    assert row['state']=='uncovered'
    assert c.get(f'/api/launches/{lid}/specifications').json()['coverage']['uncovered']==1


def test_proof_human_review_stale_after_replaced_version(c):
    lid=launch(c)
    source=upload(c,lid,'TechPack','Composition tissu : coton 100% obligatoire.')
    proof=upload(c,lid,'TestTissu','Tissu livré : coton 100%',doctype='Essai laboratoire')
    x=requirement(c,lid,source['latest']['id'])
    rid=x['id']
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Une vérification est réalisée'},headers=H).status_code==409
    evidence=c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':proof['latest']['id']},headers=H)
    assert evidence.status_code==200 and evidence.json()['state']=='to_verify'
    verified=c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Composition vérifiée sur le certificat'},headers=H)
    assert verified.status_code==200 and verified.json()['state']=='verified'
    revised=c.post(f'/api/documents/{proof["id"]}/versions',files={'file':('test-v2.txt',b'Nouvel essai')},headers=H)
    assert revised.status_code==201
    state=c.get(f'/api/launches/{lid}/specifications').json()
    assert state['coverage']['verified']==0 and state['requirements'][0]['state']=='evidence_changed'
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Ancienne preuve revalidee a tort'},headers=H).status_code==409
    new=c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':revised.json()['latest']['id']},headers=H)
    assert new.status_code==200 and new.json()['state']=='to_verify'
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Nouvelle composition vérifiée par contrôle'},headers=H).json()['state']=='verified'
    c.post(f'/api/documents/{source["id"]}/versions',files={'file':('tech-v2.txt',b'Nouveau cahier des charges')},headers=H)
    assert c.get(f'/api/launches/{lid}/specifications').json()['requirements'][0]['state']=='source_changed'


def test_ambiguity_clarification_is_traceable_and_stale(c):
    lid=launch(c)
    doc=upload(c,lid,'TechPack','Fermeture légèrement plus résistante que celle du modèle précédent.')
    vid=doc['latest']['id']
    r=c.post(f'/api/launches/{lid}/ambiguities',json={'source_version_id':vid,
         'excerpt':'Fermeture légèrement plus résistante', 'kind':'intensite_imprecise',
         'question':'Quelle résistance mesurable doit-on utiliser ?'},headers=H)
    assert r.status_code==201 and r.json()['status']=='open'
    aid=r.json()['id']
    assert c.post(f'/api/launches/{lid}/ambiguities/{aid}/resolve',json={'decision':'resolved','note':'non'},headers=H).status_code==422
    resolved=c.post(f'/api/launches/{lid}/ambiguities/{aid}/resolve',json={'decision':'resolved',
        'note':'La fermeture B-21 est retenue par le responsable'},headers=H)
    assert resolved.status_code==200 and resolved.json()['status']=='resolved'
    assert c.post(f'/api/launches/{lid}/ambiguities/{aid}/resolve',json={'decision':'dismissed','note':'Nouveau passage non necessaire'},headers=H).status_code==409
    c.post(f'/api/documents/{doc["id"]}/versions',files={'file':('tech2.txt',b'Nouvelle reference')},headers=H)
    assert c.get(f'/api/launches/{lid}/specifications').json()['ambiguities'][0]['status']=='source_changed'


def test_permissions_and_cross_launch_scope(c):
    lid=launch(c);other=launch(c,'Autre lancement')
    source=upload(c,lid,'TechPack','Boutons spécifiques obligatoires.')
    rose=upload(c,lid,'BL','Bon de livraison 100 pièces','rose','Bon de livraison')
    outsider=upload(c,other,'Tissu','Tissu pour un autre lancement')
    rid=requirement(c,lid,source['latest']['id'])['id']
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':outsider['latest']['id']},headers=H).status_code==404
    assert c.post(f'/api/launches/{lid}/requirements',json={'source_version_id':outsider['latest']['id'],
          'title':'Exigence indue','description':'Ne doit pas exister'},headers=H).status_code==404
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':rose['latest']['id']},headers=H).status_code==200
    login(c,'tech@spec.test')
    report=c.get(f'/api/launches/{lid}/specifications').json()
    assert report['requirements']==[] and report['coverage']['visible_total']==0
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Le technicien n est pas approbateur'},headers=H).status_code==403
    assert c.get(f'/api/document-versions/{rose["latest"]["id"]}/spec-suggestions').status_code==403
    login(c,'rose@spec.test')
    assert c.get(f'/api/document-versions/{source["latest"]["id"]}/spec-suggestions').status_code==403
    assert c.get(f'/api/launches/{lid}/specifications').json()['requirements']==[]


def test_only_reviewer_may_verify_and_close(c):
    lid=launch(c)
    doc=upload(c,lid,'TechPack','Tolérance dimensionnelle : +/- 0,5 cm obligatoire')
    proof=upload(c,lid,'Essai','Résultat : +/- 0,3 cm')
    rid=requirement(c,lid,doc['latest']['id'])['id']
    c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':proof['latest']['id']},headers=H)
    aid=c.post(f'/api/launches/{lid}/ambiguities',json={'source_version_id':doc['latest']['id'],
        'excerpt':'Tolérance dimensionnelle non précisée', 'kind':'precision',
        'question':'Quelle tolérance retenir dans les tests ?'},headers=H).json()['id']
    login(c,'tech@spec.test')
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Approuver sans autorisation métier'},headers=H).status_code==403
    assert c.post(f'/api/launches/{lid}/ambiguities/{aid}/resolve',json={'decision':'resolved',
        'note':'Tentative de résolution sans habilitation'},headers=H).status_code==403
    login(c,'review@spec.test')
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Rapport dimensionnel examiné par le contrôle'},headers=H).status_code==200
    assert c.post(f'/api/launches/{lid}/ambiguities/{aid}/resolve',json={'decision':'dismissed',
        'note':'La valeur figure en réalité en annexe'},headers=H).status_code==200


def test_no_false_guarantee_from_lexical_analysis():
    r=analyze_text('Informations fournies à titre de résumé sans phrase normative.')
    assert r['requirements']==[] and r['ambiguities']==[]
    assert 'absence de résultat' in r['limits']

def test_refresh_source_requires_human_review_and_preserves_version_audit(c):
    lid=launch(c)
    source=upload(c,lid,'TechPack','Légèrement plus épais que le précédent')
    proof=upload(c,lid,'Essai','Épaisseur 5 mm',doctype='Test épaisseur')
    req=requirement(c,lid,source['latest']['id']);rid=req['id']
    c.post(f'/api/launches/{lid}/requirements/{rid}/evidence',json={'evidence_version_id':proof['latest']['id']},headers=H)
    c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Épaisseur confirmée sur le rapport'},headers=H)
    amb=c.post(f'/api/launches/{lid}/ambiguities',json={'source_version_id':source['latest']['id'],
        'excerpt':'Légèrement plus épais que le précédent', 'kind':'intensite_imprecise',
        'question':'Quelle épaisseur exacte est attendue ?'},headers=H).json()
    new=c.post(f'/api/documents/{source["id"]}/versions',files={'file':('nouveau.txt','Épaisseur minimum : 5 mm'.encode('utf8'))},headers=H).json()['latest']['id']
    assert c.get(f'/api/launches/{lid}/specifications').json()['requirements'][0]['state']=='source_changed'
    payload={'new_source_version_id':new,'title':'Épaisseur minimale du tissu',
       'description':'La matière doit présenter une épaisseur supérieure à 5 mm',
       'source_excerpt':'Épaisseur minimum : 5 mm'}
    rr=c.post(f'/api/launches/{lid}/requirements/{rid}/refresh-source',json=payload,headers=H)
    assert rr.status_code==200,rr.text
    assert rr.json()['state']=='to_verify'
    assert c.post(f'/api/launches/{lid}/requirements/{rid}/verify',json={'note':'Nouvelle mesure examinée correctement'},headers=H).json()['state']=='verified'
    aa=c.post(f'/api/launches/{lid}/ambiguities/{amb["id"]}/refresh-source',json={
        'new_source_version_id':new,'excerpt':'Épaisseur minimum : 5 mm','question':'La limite est-elle inclusive ?'},headers=H)
    assert aa.status_code==200,aa.text
    assert aa.json()['status']=='open'
    audit=c.get('/api/admin/audit').json()
    assert any(x['action']=='spec.requirement.source.refresh' for x in audit)
    assert any(x['action']=='spec.ambiguity.source.refresh' for x in audit)
