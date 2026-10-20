"""Contextual assistant must never return unauthorized metadata."""
import os
import tempfile
os.environ.setdefault('FRAMATEX_DATA_DIR',tempfile.mkdtemp(prefix='framat-assistant-'))
os.environ.setdefault('FRAMATEX_SECRET_KEY','assistant-test-secret-'*4)
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role, RolePermission

H={'X-Framatex-Request':'1'}
PASSWORD='AssistantTests2026!'

@pytest.fixture
def workspace():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        with SessionLocal() as db:
            db.add(User(name='Admin assistant',email='assistant-admin@test.local',password_hash=hash_password(PASSWORD),roles=[Role(name='Administrateur')]))
            db.add(User(name='Lecteur technique',email='assistant-reader@test.local',password_hash=hash_password(PASSWORD),roles=[Role(name='Technique',grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='jaune')])]))
            db.commit()
        assert c.post('/api/auth/login',json={'email':'assistant-admin@test.local','password':PASSWORD},headers=H).status_code==200
        public=c.post('/api/launches',json={'name':'Collection Horizon','order_ref':'CMD-HORIZON'},headers=H).json()['id']
        hidden=c.post('/api/launches',json={'name':'Collection Secret','order_ref':'CMD-SECRET'},headers=H).json()['id']
        from app.models import Launch
        with SessionLocal() as db:
            db.get(Launch,hidden).restricted=True;db.commit()
        for lid,folder,title in [(public,'jaune','Fiche Horizon technique'),(public,'vert','Marge Horizon privée'),(hidden,'jaune','Fiche Secret technique')]:
            r=c.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':title,'doc_type':'Fiche technique'},files={'file':('fiche.txt',b'Le contenu ne doit pas etre lu','text/plain')},headers=H)
            assert r.status_code==201,r.text
        yield c,public,hidden
    Base.metadata.drop_all(engine)

def ask(c,q,**kwargs):
    r=c.post('/api/assistant/guide',json={'question':q,**kwargs},headers=H)
    assert r.status_code==200,r.text
    return r.json()

def test_real_search_respects_launch_and_folder_permissions(workspace):
    c,public,hidden=workspace
    assert c.post('/api/auth/login',json={'email':'assistant-reader@test.local','password':PASSWORD},headers=H).status_code==200
    answer=ask(c,'Recherche fiche')
    assert [r['label'] for r in answer['results']]==['Fiche Horizon technique']
    assert len(ask(c,'Cherche "CMD-HORIZON"')['results'])==1
    assert ask(c,'Recherche "CMD-SECRET"')['results']==[]
    assert ask(c,'Recherche marge')['results']==[]
    r=c.post('/api/assistant/guide',json={'question':'Résume ce dossier','launch_id':hidden},headers=H)
    assert r.status_code==404
    summary=ask(c,'Résume ce dossier',launch_id=public)
    assert '1 document(s) et 1 version(s)' in summary['answer']
    assert summary['launch_id']==public
    assert 'privée' not in str(summary)
    assert ask(c,'Recherche le contenu ne doit pas')['results']==[]

def test_context_followup_and_client_guidance(workspace):
    c,public,hidden=workspace
    assert ask(c,'Comment créer un client et son espace client ?')['destination']=='clients'
    choice=ask(c,'Quel est le statut ?')
    assert len(choice['results'])==2
    assert ask(c,'Et ensuite ?',previous_question='Où déposer une facture ?')['folder']=='vert'
    assert ask(c,'Recherche un document')['title']=='Précisez votre recherche'
    assert ask(c,'Recherche fiche',launch_id=public)['results'][0]['launch_id']==public
    assert len(ask(c,'Recherche fiche',launch_id=public)['results'])==2
