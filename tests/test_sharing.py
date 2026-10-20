"""MVP 0.14 — contrats confidentialité, approbation, version et pièces fournisseurs."""
import os
import tempfile

os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-sharing-tests-')
os.environ['FRAMATEX_SECRET_KEY'] = 'sharing-test-secret-'*4

from fastapi.testclient import TestClient
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role, RolePermission
from app.sharing_models import ClientPublication, SupplierDocumentRequest
from sqlalchemy import select

H={'X-Framatex-Request':'1'}
PWD='SharingTests2026!'


def setup():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        admin_role=Role(name='Administrateur')
        rose_role=Role(name='Service réception')
        jaune_role=Role(name='Service technique')
        for role,slug in ((rose_role,'rose'),(jaune_role,'jaune')):
            role.grants.extend([RolePermission(action='launch.read'),
                                RolePermission(action='document.read',folder_slug=slug),
                                RolePermission(action='document.write',folder_slug=slug)])
        for index,role in enumerate((admin_role,rose_role,jaune_role)):
            u=User(name=f'Personne {index}',email=f'personne{index}@example.local',password_hash=hash_password(PWD))
            u.roles.append(role)
            db.add(u)
        db.commit()


def login(c,n):
    r=c.post('/api/auth/login',json={'email':f'personne{n}@example.local','password':PWD},headers=H)
    assert r.status_code==200,r.text


def launch(c,name='Tissus · lancement contrôle',client='Client-test'):
    r=c.post('/api/launches',json={'name':name,'client_name':client},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']


def register_client(c, name):
    """Création d'une société réelle du répertoire avant toute publication externe."""
    r = c.post('/api/clients', json={'name': name}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


def bind_client(c, lid, name='Client partenaire'):
    client_id = register_client(c, name)
    linked = c.patch(f'/api/launches/{lid}', json={'client_id': client_id}, headers=H)
    assert linked.status_code == 200, linked.text
    return client_id


def document(c,lid,folder='jaune',kind='Fiche technique',title='Fiche de composition'):
    r=c.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':title,'doc_type':kind},
             files={'file':('fiche.txt',b'Document fictif approuve','text/plain')},headers=H)
    assert r.status_code==201,r.text
    return r.json()


def test_client_publication_approval_withdrawal_staleness():
    with TestClient(app) as c:
        setup();login(c,0)
        lid=launch(c)
        d=document(c,lid)
        url=f'/api/launches/{lid}/client-publications'
        payload={'document_version_id':d['latest']['id'],'reason':'Transmission technique explicitement approuvee'}
        assert c.post(url,json=payload,headers=H).status_code==422  # un client du répertoire est obligatoire
        bind_client(c, lid)
        assert c.post(url,json=payload,headers=H).status_code==409  # validation obligatoire
        reviewed=c.post(f'/api/documents/{d["id"]}/reviews',json={'decision':'approved'},headers=H)
        assert reviewed.status_code==201,reviewed.text
        p=c.post(url,json=payload,headers=H)
        assert p.status_code==201,p.text
        pubid=p.json()['id'];assert p.json()['effective'] is True
        assert c.post(url,json=payload,headers=H).status_code==409
        assert len(c.get(f'/api/launches/{lid}/client-preview').json()['documents'])==1
        login(c,1)
        assert c.get(f'/api/launches/{lid}/client-preview').status_code==403
        assert c.get(url).json()['items']==[]
        assert c.post(url,json=payload,headers=H).status_code==403
        login(c,0)
        changed=c.post(f'/api/documents/{d["id"]}/versions',files={'file':('revue.txt',b'Nouvelle version du document','text/plain')},headers=H)
        assert changed.status_code==201,changed.text
        assert c.get(url).json()['items'][0]['stale'] is True
        assert c.get(f'/api/launches/{lid}/client-preview').json()['documents']==[]
        assert c.post(url,json=payload,headers=H).status_code==409
        revoked=c.post(f'/api/client-publications/{pubid}/revoke',json={'reason':'Fichier remplace par une version differente'},headers=H)
        assert revoked.status_code==200
        assert c.post(f'/api/client-publications/{pubid}/revoke',json={'reason':'Fichier deja retire de publication'},headers=H).status_code==409
        assert c.get(url).json()['items'][0]['status']=='revoked'


def test_client_safe_types_and_changing_client():
    with TestClient(app) as c:
        setup();login(c,0)
        lid=launch(c)
        bind_client(c, lid)
        private=document(c,lid,kind='Fiche de prix',title='Prix matière interne')
        c.post(f'/api/documents/{private["id"]}/reviews',json={'decision':'approved'},headers=H)
        endpoint=f'/api/launches/{lid}/client-publications'
        assert c.post(endpoint,json={'document_version_id':private['latest']['id'],'reason':'Demande de transmission client pour validation'},headers=H).status_code==422
        d=document(c,lid,kind='Rapport de contrôle',title='Contrôle qualité tissu')
        c.post(f'/api/documents/{d["id"]}/reviews',json={'decision':'approved'},headers=H)
        p=c.post(endpoint,json={'document_version_id':d['latest']['id'],'reason':'Rapport technique approuvé pour partage'},headers=H)
        assert p.status_code==201,p.text
        nouveau_client_id = register_client(c, 'Nouveau client fictif')
        changed=c.patch(f'/api/launches/{lid}',json={'client_id':nouveau_client_id},headers=H)
        assert changed.status_code==200
        assert c.get(endpoint).json()['items'][0]['client_changed'] is True
        assert c.get(f'/api/launches/{lid}/client-preview').json()['documents']==[]
        assert c.get('/api/launches/'+lid+'/client-publications').status_code==200


def test_supplier_request_reception_and_access_isolation():
    with TestClient(app) as c:
        setup();login(c,0)
        lid=launch(c);other=launch(c,'Autre lancement distinct')
        rose_doc=document(c,lid,'rose','Bon de livraison','BL tissu')
        wrong=document(c,other,'rose','Bon de livraison','BL autre lancement')
        route=f'/api/launches/{lid}/supplier-requests'
        req=c.post(route,json={'folder_slug':'rose','supplier_name':'Fournisseur fictif',
                     'requested_title':'Bon de livraison lots tissu','expected_doc_type':'Bon de livraison',
                     'due_date':'2026-11-08'},headers=H)
        assert req.status_code==201,req.text
        rid=req.json()['id'];resolve=f'/api/supplier-requests/{rid}/resolve'
        assert c.post(resolve,json={'decision':'received','document_version_id':wrong['latest']['id'],
                         'note':'Mauvais justificatif par rapport au lancement'},headers=H).status_code==422
        assert c.post(resolve,json={'decision':'received','document_version_id':None,
                         'note':'Justificatif non disponible pour le moment'},headers=H).status_code==422
        login(c,2)  # rôle jaune seulement
        assert c.get(route).json()['items']==[]
        assert c.post(resolve,json={'decision':'received','document_version_id':rose_doc['latest']['id'],
                            'note':'Bon reçu au service reception'},headers=H).status_code==403
        login(c,1)  # rôle rose autorisé
        assert c.get(route).json()['items'][0]['supplier_name']=='Fournisseur fictif'
        received=c.post(resolve,json={'decision':'received','document_version_id':rose_doc['latest']['id'],
                                'note':'Bon de livraison receptionne et verifie'},headers=H)
        assert received.status_code==200,received.text
        assert received.json()['status']=='received'
        assert c.post(resolve,json={'decision':'cancelled','note':'La demande ne doit pas etre annulee'},headers=H).status_code==409
        login(c,0)
        assert c.post(f'/api/documents/{rose_doc["id"]}/versions',files={'file':('bl2.txt',b'Nouvelle livraison', 'text/plain')},headers=H).status_code==201
        assert c.get(route).json()['items'][0]['response_stale'] is True


def test_supplier_cancellation_and_no_external_auth():
    with TestClient(app) as c:
        setup();login(c,0)
        lid=launch(c)
        r=c.post(f'/api/launches/{lid}/supplier-requests',json={'folder_slug':'jaune',
                    'supplier_name':'Fabricant fictif','requested_title':'Certificat de composition',
                    'expected_doc_type':'Certificat qualité'},headers=H)
        assert r.status_code==201
        rid=r.json()['id'];url=f'/api/supplier-requests/{rid}/resolve'
        assert c.post(url,json={'decision':'cancelled','document_version_id':'autre',
                    'note':'Demande annulee car plus necessaire'},headers=H).status_code==422
        assert c.post(url,json={'decision':'cancelled','note':'Demande annulee par le responsable'},headers=H).status_code==200
        assert c.post(f'/api/launches/{lid}/supplier-requests',json={'folder_slug':'vert',
                    'supplier_name':'Un fournisseur','requested_title':'Facture interne',
                    'expected_doc_type':'Facture'},headers=H).status_code==422
        c.post('/api/auth/logout',headers=H)
        assert c.get(f'/api/launches/{lid}/client-preview').status_code==401
        assert c.get(f'/api/launches/{lid}/supplier-requests').status_code==401
        assert c.post(f'/api/launches/{lid}/client-publications',json={'document_version_id':'x','reason':'interdit aux anonymes'},headers=H).status_code==401


def test_header_and_storage_audit_trail():
    with TestClient(app) as c:
        setup();login(c,0);lid=launch(c)
        assert c.post(f'/api/launches/{lid}/supplier-requests',json={'folder_slug':'jaune','supplier_name':'A',
                      'requested_title':'Un document','expected_doc_type':'Fiche technique'}).status_code==403
        r=c.post(f'/api/launches/{lid}/supplier-requests',json={'folder_slug':'jaune',
                      'supplier_name':'Partenaire fictif','requested_title':'Une fiche technique',
                      'expected_doc_type':'Fiche technique'},headers=H)
        assert r.status_code==201
        with SessionLocal() as db:
            assert db.scalar(select(SupplierDocumentRequest).where(SupplierDocumentRequest.id==r.json()['id'])) is not None
