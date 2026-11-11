from fastapi.testclient import TestClient
from test_partners import app,setup,post,H,PWD
from app.core import SessionLocal,hash_password
from app.models import User,Role,RolePermission

def test_metadata_search_applies_acl_before_pagination_and_counts():
    with TestClient(app) as admin, TestClient(app) as limited:
        lid=setup(admin)
        admin.patch(f'/api/launches/{lid}',json={'order_ref':'CMD-SEARCH','orli_ref':'ORLI-SEARCH'},headers=H)
        with SessionLocal() as db:
            role=Role(name='Lecteur rose uniquement',grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='rose')])
            u=User(name='Lecteur',email='reader-search@sample.local',password_hash=hash_password(PWD),roles=[role]);db.add(u);db.commit()
        post(limited,'/api/auth/login',{'email':'reader-search@sample.local','password':PWD},200)
        documents=[]
        for folder in ['jaune','rose']:
            r=admin.post(f'/api/launches/{lid}/documents',data={'folder':folder,'title':'Certificat '+folder,'doc_type':'Certificat'},files={'file':('fiche.txt',b'Fiche fictive','text/plain')},headers=H)
            assert r.status_code==201;r=r.json();documents.append(r)
            post(admin,f'/api/documents/{r["id"]}/reviews',{'decision':'approved'})
        result=limited.get('/api/document-search?order_ref=CMD-SEARCH&orli_ref=ORLI&client=Client%20A&author=Admin&status=approved&doc_type=Certificat&limit=1').json()
        assert result['total']==1 and result['items'][0]['folder']=='rose'
        assert limited.get('/api/document-search?folder=jaune').json()['total']==0
        assert limited.get('/api/document-search?offset=1').json()['items']==[]
        admin.post(f'/api/documents/{documents[1]["id"]}/versions',files={'file':('v2.txt',b'Nouvelle fiche','text/plain')},headers=H)
        assert limited.get('/api/document-search').json()['items'][0]['version']==2
        assert limited.get('/api/document-search?version=1').json()['items'][0]['version']==1
        assert limited.get('/api/document-search?status=approved').json()['total']==0
        assert limited.get('/api/document-search?after=2099-01-01T00:00:00Z').json()['total']==0
        assert limited.get('/api/document-search?before=2000-01-01T00:00:00Z').json()['total']==0
        assert limited.get('/api/document-search?after=2000-01-01T00:00:00Z&before=2099-01-01T00:00:00Z&sort=title&q=rose').json()['total']==1
        assert [d['title'] for d in admin.get('/api/document-search?sort=title').json()['items']]==['Certificat jaune','Certificat rose']
        admin.put(f'/api/launches/{lid}/access',json={'restricted':True},headers=H)
        assert limited.get('/api/document-search').json()['total']==0
        with TestClient(app) as anonymous:assert anonymous.get('/api/document-search').status_code==401
