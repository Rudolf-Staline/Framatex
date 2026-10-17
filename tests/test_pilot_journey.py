"""A full synthetic launch journey: login, restricted launch, files and access."""
from io import BytesIO
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User
from app.main import app

HEADER={'X-Framatex-Request':'1'}
PASSWORD='PilotAcceptance2026!'


def test_end_to_end_document_lifecycle_and_revocation():
    marker=uuid4().hex[:10]
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin_role=db.scalar(select(Role).where(Role.name=='Administrateur'))
            if admin_role is None:
                admin_role=Role(name='Administrateur');db.add(admin_role)
            worker_role=Role(name=f'Recette lecture rose {marker}',grants=[
                RolePermission(action='launch.read'),
                RolePermission(action='document.read',folder_slug='rose')])
            admin=User(name='Recette admin',email=f'admin-{marker}@pilot.invalid',password_hash=hash_password(PASSWORD),roles=[admin_role])
            worker=User(name='Recette collaborateur',email=f'worker-{marker}@pilot.invalid',password_hash=hash_password(PASSWORD),roles=[worker_role])
            db.add_all([worker_role,admin,worker]);db.commit()
            worker_id=worker.id
        def login(email):
            response=client.post('/api/auth/login',headers=HEADER,json={'email':email,'password':PASSWORD})
            assert response.status_code==200, response.text
        login(f'admin-{marker}@pilot.invalid')
        response=client.post('/api/launches',json={'name':'Recette lot textile 2026','client_name':'Client fictif'},headers=HEADER)
        assert response.status_code==201
        launch=response.json()
        assert launch['orli_ref'] is None
        launch_id=launch['id']
        detail=client.get(f'/api/launches/{launch_id}').json()
        assert {x['slug'] for x in detail['folders']}=={'jaune','rose','bleu','vert'}
        response=client.post(f'/api/launches/{launch_id}/documents',headers=HEADER,data={
            'folder':'rose','title':'Bon de réception du pilote','doc_type':'Bon de réception'},
            files={'file':('reception-v1.txt',b'reception initiale','text/plain')})
        assert response.status_code==201,response.text
        document=response.json();doc_id=document['id']
        newer=client.post(f'/api/documents/{doc_id}/versions',headers=HEADER,
                          files={'file':('reception-v2.txt',b'reception revisee','text/plain')})
        assert newer.status_code==201,newer.text
        assert len(newer.json()['versions'])==2
        assert client.get(f'/api/documents/{doc_id}/versions/1/download').content==b'reception initiale'
        assert client.get(f'/api/documents/{doc_id}/versions/2/download').content==b'reception revisee'
        assert client.put(f'/api/launches/{launch_id}/access',headers=HEADER,json={'restricted':True}).status_code==200
        login(f'worker-{marker}@pilot.invalid')
        assert client.get(f'/api/launches/{launch_id}').status_code==404
        assert client.get(f'/api/documents/{doc_id}/versions/2/download').status_code==404
        login(f'admin-{marker}@pilot.invalid')
        assert client.post(f'/api/launches/{launch_id}/access/members',headers=HEADER,json={'user_id':worker_id}).status_code==201
        login(f'worker-{marker}@pilot.invalid')
        assert client.get(f'/api/launches/{launch_id}').status_code==200
        assert client.get(f'/api/documents/{doc_id}/versions/2/download').content==b'reception revisee'
        login(f'admin-{marker}@pilot.invalid')
        assert client.delete(f'/api/launches/{launch_id}/access/members/{worker_id}',headers=HEADER).status_code==200
        login(f'worker-{marker}@pilot.invalid')
        assert client.get(f'/api/launches/{launch_id}').status_code==404
        assert client.get(f'/api/documents/{doc_id}/versions/2/download').status_code==404
