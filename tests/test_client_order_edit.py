"""Client corrections before review, including stale writes and ownership."""
import secrets
import uuid
from fastapi.testclient import TestClient
from tests.test_order_sheet import H, chef
from app.main import app
from app.core import SessionLocal
from app.models import AuditEvent
from sqlalchemy import select


def make_client(admin):
    c = TestClient(app)
    email = f"order-{uuid.uuid4().hex}@example.test"
    pw = secrets.token_urlsafe(18)
    reg = c.post('/api/client/register', headers=H, json={'raison_sociale':'Client test','nom_contact':'Contact','email':email,
        'telephone':'0600000000','adresse':'Rue test','pays':'Maroc','password':pw})
    assert reg.status_code == 201, reg.text
    assert admin.patch(f"/api/admin/clients/{reg.json()['id']}/status",headers=H,json={'status':'active'}).status_code == 200
    assert c.post('/api/client/login',headers=H,json={'email':email,'password':pw}).status_code == 200
    return c


def test_client_order_edit():
    admin = chef()
    c = make_client(admin)
    other = make_client(admin)
    path = '/api/client/order-requests'
    res = c.post(path, headers=H, json={'article':'Veste','quantite':100,'date_souhaitee':'2027-01-20','status':'submitted'})
    assert res.status_code == 201, res.text
    order = res.json()
    endpoint = path + '/' + order['id']
    update = {'expected_updated_at':order['updated_at'],'quantite':150,'color':'Bleu'}
    assert other.patch(endpoint,headers=H,json=update).status_code == 404
    res = c.patch(endpoint,headers=H,json=update)
    assert res.status_code == 200, res.text
    edited = res.json()
    assert edited['quantite'] == 150 and edited['color'] == 'Bleu' and edited['status'] == 'submitted'
    assert edited['request_number'] == order['request_number']
    assert c.patch(endpoint,headers=H,json=update).status_code == 409
    assert c.patch(endpoint,headers=H,json={'expected_updated_at':edited['updated_at'],'article':None}).status_code == 422
    assert c.patch(endpoint,headers=H,json={'expected_updated_at':edited['updated_at'],'status':'accepted'}).status_code == 422
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.target_id == order['id'],AuditEvent.action == 'client.order_request.edit'))
        assert event and '"before": 100' in event.detail and '"after": 150' in event.detail
    assert admin.patch('/api/admin/client-order-requests/'+order['id']+'/status',headers=H,json={'status':'under_review'}).status_code == 200
    assert c.patch(endpoint,headers=H,json={'expected_updated_at':edited['updated_at'],'quantite':200}).status_code == 409
