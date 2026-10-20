"""Portal isolation across clients, internal APIs and publication lifecycle."""
import os
import tempfile
os.environ.setdefault('FRAMATEX_DATA_DIR', tempfile.mkdtemp(prefix='framat-clients-'))
os.environ.setdefault('FRAMATEX_SECRET_KEY', 'clients-test-secret-' * 4)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role, RolePermission, Client

H={'X-Framatex-Request':'1'}
PASSWORD='ClientsPortal2026!'

@pytest.fixture
def system():
    Base.metadata.drop_all(engine)
    with TestClient(app) as admin:
        with SessionLocal() as db:
            db.add(User(name='Admin',email='clients-admin@test.local',password_hash=hash_password(PASSWORD),roles=[Role(name='Administrateur')]))
            db.commit()
        assert admin.post('/api/auth/login',json={'email':'clients-admin@test.local','password':PASSWORD},headers=H).status_code==200
        yield admin
    Base.metadata.drop_all(engine)

def add_client(admin,name,email):
    row=admin.post('/api/clients',json={'name':name},headers=H)
    assert row.status_code==201, row.text
    client_id=row.json()['id']
    contact=admin.post(f'/api/clients/{client_id}/contacts',json={'name':name+' contact','email':email,'password':PASSWORD},headers=H)
    assert contact.status_code==201,contact.text
    return client_id,contact.json()['id']

def login(email):
    c=TestClient(app)
    r=c.post('/api/auth/login',json={'email':email,'password':PASSWORD},headers=H)
    assert r.status_code==200,r.text
    assert r.json()['client_account'] is True
    return c

def launch(admin,cid,name='Dossier client'):
    r=admin.post('/api/launches',json={'name':name,'client_id':cid,'client_name':'Texte ignoré','order_ref':'CMD-01'},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']

def publish(admin,lid):
    d=admin.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche technique finale','doc_type':'Fiche technique'},files={'file':('fiche.txt',b'Donnees autorisees','text/plain')},headers=H)
    assert d.status_code==201,d.text
    vid=d.json()['latest']['id']
    # Use the same business review model as the normal approval endpoint.
    from app.workflow_models import DocumentReview
    with SessionLocal() as db:
        uid=db.scalar(select(User.id).where(User.email=='clients-admin@test.local'))
        db.add(DocumentReview(document_version_id=vid,decision='approved',comment='Validation client de test',reviewed_by=uid))
        db.commit()
    p=admin.post(f'/api/launches/{lid}/client-publications',json={'document_version_id':vid,'reason':'Partage validé pour le client'},headers=H)
    assert p.status_code==201,p.text
    return p.json()['id'],d.json()['id']

def test_portal_isolation_and_lifecycle(system):
    admin=system
    a,uid=add_client(admin,'Atelier Alpha','alpha@test.local')
    b,_=add_client(admin,'Atelier Beta','beta@test.local')
    la=launch(admin,a);lb=launch(admin,b,'Dossier confidentiel Beta');unassigned=launch(admin,None,'Dossier sans client')
    pid,did=publish(admin,la)
    alpha=login('alpha@test.local');beta=login('beta@test.local')
    home=alpha.get('/api/portal/home').json()
    assert [l['id'] for l in home['launches']]==[la]
    assert 'orli_ref' not in home['launches'][0]
    assert alpha.get('/api/portal/launches/'+lb).status_code==404
    assert alpha.get('/api/portal/launches/'+unassigned).status_code==404
    assert len(alpha.get('/api/portal/launches/'+la).json()['documents'])==1
    assert alpha.get(f'/api/portal/documents/{pid}/download').content==b'Donnees autorisees'
    assert beta.get(f'/api/portal/documents/{pid}/download').status_code==404
    for path in ['/api/launches',f'/api/launches/{la}',f'/api/documents/{did}/versions/1/download','/api/clients','/api/admin/users','/api/workspace/priorities']:
        assert alpha.get(path).status_code==403,path
    # Granting internal roles to a client must never turn a portal account into staff.
    with SessionLocal() as db:
        user=db.get(User,uid);role=db.scalar(select(Role).where(Role.name=='Administrateur'));user.roles.append(role);db.commit()
    assert alpha.get('/api/admin/users').status_code==403
    # Rename keeps identity and publications; reassignment removes the former client's access.
    assert admin.patch('/api/clients/'+a,json={'name':'Atelier Alpha renommé'},headers=H).status_code==200
    assert len(alpha.get('/api/portal/launches/'+la).json()['documents'])==1
    assert admin.patch('/api/launches/'+la,json={'client_id':b},headers=H).status_code==200
    assert alpha.get('/api/portal/launches/'+la).status_code==404
    assert beta.get('/api/portal/launches/'+la).json()['documents']==[]
    assert beta.get(f'/api/portal/documents/{pid}/download').status_code==404
    # Disable client takes effect for an already connected browser.
    assert admin.patch(f'/api/clients/{b}/active',json={'active':False},headers=H).status_code==200
    assert beta.get('/api/portal/home').status_code==403
    assert beta.post('/api/auth/logout',headers=H).status_code==200
    assert beta.post('/api/auth/login',json={'email':'clients-admin@test.local','password':PASSWORD},headers=H).status_code==200

def test_revision_revocation_and_contact_deactivation(system):
    a,uid=add_client(system,'Client Gamma','gamma@test.local');lid=launch(system,a)
    pid,did=publish(system,lid);c=login('gamma@test.local')
    r=system.post(f'/api/documents/{did}/versions',files={'file':('new.txt',b'Nouvelle version','text/plain')},headers=H)
    assert r.status_code==201
    assert c.get('/api/portal/launches/'+lid).json()['documents']==[]
    assert c.get(f'/api/portal/documents/{pid}/download').status_code==404
    assert system.post(f'/api/client-publications/{pid}/revoke',json={'reason':'Retrait demandé par le responsable'},headers=H).status_code==200
    assert c.get(f'/api/portal/documents/{pid}/download').status_code==404
    assert system.patch(f'/api/clients/{a}/contacts/{uid}/active',json={'active':False},headers=H).status_code==200
    assert c.get('/api/portal/home').status_code in (401,403)

def test_client_validation_and_permissions(system):
    a,_=add_client(system,'Validation client','validation@test.local')
    assert system.post('/api/clients',json={'name':' validation client '},headers=H).status_code==409
    assert system.post('/api/clients',json={'name':'  '},headers=H).status_code==422
    assert system.post('/api/clients',json={'name':'Autre client','contact_email':'mauvais email'},headers=H).status_code==422
    assert system.post('/api/launches',json={'name':'Mauvais client','client_id':'missing'},headers=H).status_code==404
    assert system.post(f'/api/clients/{a}/contacts',json={'name':'Doublon','email':'validation@test.local','password':PASSWORD},headers=H).status_code==409
    with SessionLocal() as db:
        role=Role(name='Lecteur clients',grants=[RolePermission(action='launch.read')])
        db.add(User(name='Personnel',email='staff-clients@test.local',password_hash=hash_password(PASSWORD),roles=[role]));db.commit()
    staff=TestClient(app);staff.post('/api/auth/login',json={'email':'staff-clients@test.local','password':PASSWORD},headers=H)
    assert 'contacts' not in staff.get('/api/clients').json()[0]
    assert staff.post('/api/clients',json={'name':'Interdit'},headers=H).status_code==403
    assert staff.get('/api/portal/home').status_code==403


def test_disabled_client_can_sign_in_as_another_account(system):
    client_id, _ = add_client(system, 'Atelier Temporaire', 'temp@portal.test')
    client = login('temp@portal.test')
    assert system.patch(f'/api/clients/{client_id}/active',
                        json={'active':False},headers=H).status_code == 200
    assert client.get('/api/portal/home').status_code == 403
    # Stale HTTP-only cookie must not prevent changing accounts.
    result=client.post('/api/auth/login',json={'email':'clients-admin@test.local',
                                                'password':PASSWORD},headers=H)
    assert result.status_code == 200, result.text
    assert result.json()['client_account'] is False
