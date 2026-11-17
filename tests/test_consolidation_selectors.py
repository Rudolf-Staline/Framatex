"""Launch selectors search authorized objects beyond their bounded first page."""
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app,setup,post,PWD
from app.core import SessionLocal,hash_password
from app.models import Launch,LaunchMember,User,Role,RolePermission


def test_launch_selectors_search_beyond_first_hundred_without_disclosing_restricted_matches():
    with TestClient(app) as admin,TestClient(app) as buyer:
        setup(admin)
        with SessionLocal() as db:
            creator=db.scalar(select(User.id).where(User.email=='admin@sample.local'))
            role=Role(name='Achats sélecteurs',grants=[RolePermission(action=action) for action in ('launch.read','document.read','supplier.read','supplier.request')])
            user=User(email='selectors@sample.local',name='Achats',password_hash=hash_password(PWD),roles=[role]);db.add(user);db.flush()
            for i in range(120):
                launch=Launch(name=f'Visible {i:03}',order_ref=f'CMD-{i:03}',client_name='Client de recherche',orli_ref=f'ORLI-{i:03}',created_by=creator,restricted=True,created_at=datetime(2026,11,17,tzinfo=timezone.utc))
                db.add(launch);db.flush();db.add(LaunchMember(launch_id=launch.id,user_id=user.id,granted_by=creator))
            target=Launch(name='A_RECHERCHER ancienne pièce',client_name='Client cible',order_ref='CMD-TARGET',orli_ref='ORLI-ANCIEN',created_by=creator,restricted=True,created_at=datetime(2000,1,1,tzinfo=timezone.utc));db.add(target);db.flush();db.add(LaunchMember(launch_id=target.id,user_id=user.id,granted_by=creator))
            secret=Launch(name='A_RECHERCHER strictement secret',client_name='Client secret',created_by=creator,restricted=True);db.add(secret);db.flush();target_id=target.id;secret_id=secret.id;db.commit()
        post(buyer,'/api/auth/login',{'email':'selectors@sample.local','password':PWD},200)
        assert len(admin.get('/api/partners/launch-options').json())==100
        assert len(admin.get('/api/partners/launch-options?offset=100').json())==23
        assert {row['id'] for row in admin.get('/api/partners/launch-options?q=A_RECHERCHER').json()}=={target_id,secret_id}
        assert admin.get('/api/partners/launch-options?limit=101').status_code==422
        # Administrative options remain administrative; daily forms use the
        # same canonical SQL launch search available to authorized employees.
        assert buyer.get('/api/partners/launch-options').status_code==403
        first=buyer.get('/api/launches?page=true').json()
        assert first['total']==122 and target_id not in {row['id'] for row in first['items']}
        assert target_id not in {row['id'] for row in buyer.get('/api/partners/staff-home').json()['launches']}
        for key,value in [('q','A_RECHERCHER'),('q','Client cible'),('q','CMD-TARGET'),('q','ORLI-ANCIEN')]:
            response=buyer.get('/api/launches',params={key:value,'page':'true','limit':100})
            assert response.status_code==200,response.text
            result=response.json();assert result['total']==1 and [row['id'] for row in result['items']]==[target_id]
            assert secret_id not in response.text and 'strictement secret' not in response.text and 'Client secret' not in response.text
        assert buyer.get('/api/launches?page=true&q=strictement%20secret').json()['total']==0
        page=buyer.get('/api/launches?page=true&offset=100').json()
        assert len(page['items'])==22 and target_id in {row['id'] for row in page['items']}
