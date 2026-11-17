"""Daily supplier guide remains available to explicitly permitted employees."""
from fastapi.testclient import TestClient
from test_partners import app, setup, post, H, PWD
from app.core import SessionLocal, hash_password
from app.models import User, Role, RolePermission


def test_received_document_guide_non_admin_permissions_and_closed_navigation():
    with TestClient(app) as admin, TestClient(app) as purchasing, TestClient(app) as other:
        setup(admin)
        with SessionLocal() as db:
            for name,email,actions in [('Achats','guide-purchasing@sample.local',['launch.read','supplier.read','supplier.request']),('Sans droits achats','guide-other-purchasing@sample.local',['launch.read'])]:
                role=Role(name=name,grants=[RolePermission(action=a) for a in actions])
                user=User(name=name,email=email,password_hash=hash_password(PWD),roles=[role]);db.add(user)
            db.commit()
        for c,email in [(purchasing,'guide-purchasing@sample.local'),(other,'guide-other-purchasing@sample.local')]:
            post(c,'/api/auth/login',{'email':email,'password':PWD},200)
        ids={p['id'] for p in purchasing.get('/api/guide/catalog').json()['procedures']}
        assert 'record_received_supplier_document' in ids
        assert 'invite_supplier' not in ids and 'supplier_integration' not in ids
        result=purchasing.post('/api/guide/actions/open_record_received_supplier_document/resolve',json={'page':'home'},headers=H)
        assert result.status_code==200,result.text
        assert result.json()['navigation']['id']=='supplier_work' and result.json()['navigation']['route']=='/partners'
        assert other.get('/api/guide/procedures/record_received_supplier_document').status_code==404
        assert other.post('/api/guide/actions/open_record_received_supplier_document/resolve',json={'page':'home'},headers=H).status_code==404
