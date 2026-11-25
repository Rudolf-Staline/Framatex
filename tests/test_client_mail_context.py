"""A manual client-email draft can only use the explicitly linked client."""
import secrets
import uuid
from fastapi.testclient import TestClient
from tests.test_order_sheet import H, chef
from tests.test_document_preview import upload
from app.main import app


def test_mail_context_is_explicit_admin_only_and_not_a_send():
    c = chef()
    suffix = uuid.uuid4().hex[:8]
    lid = c.post('/api/order-sheets', headers=H, json={'name': 'Clarification ' + suffix, 'order_ref': '000417'}).json()['id']
    doc = upload(c, lid, 'fiche.txt', b'Confidential technical information')
    endpoint = f"/api/document-versions/{doc['latest']['id']}/client-mail-context"
    assert c.get(endpoint).json()['available'] is False
    cl = TestClient(app)
    pw = secrets.token_urlsafe(16) + 'Aa1!'
    address = f'client-{suffix}@example.test'
    reg = cl.post('/api/client/register', headers=H, json={'raison_sociale': 'Client de test', 'nom_contact': 'Contact',
        'email': address, 'telephone': '0600000000', 'adresse': '1 rue', 'pays': 'France', 'password': pw})
    assert reg.status_code == 201, reg.text
    cid = reg.json()['id']
    assert c.patch(f'/api/launches/{lid}/sheet', headers=H, json={'client_account_id': cid}).status_code == 200
    assert c.get(endpoint).json()['available'] is False
    assert c.patch(f'/api/admin/clients/{cid}/status', headers=H, json={'status': 'active'}).status_code == 200
    response = c.get(endpoint)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['available'] and data['email'] == address
    assert 'fiche.txt' in data['subject'] and '000417' in data['subject']
    assert 'Confidential' not in response.text and 'body' not in data
    tech = c.post('/api/admin/collaborators', headers=H, json={'name': 'Lecteur', 'email': f't-{suffix}@example.test'}).json()
    t = TestClient(app)
    t.post('/api/auth/login', headers=H, json={'email': tech['collaborator']['email'], 'password': tech['temporary_password']})
    t.post('/api/account/password', headers=H, json={'current_password': tech['temporary_password'], 'new_password': pw})
    c.put(f"/api/admin/collaborators/{tech['collaborator']['id']}/assignments/{lid}", headers=H,
        json={'folders': {'jaune': ['document.read']}})
    assert t.get(endpoint).status_code == 403
    assert c.request('DELETE', f"/api/documents/{doc['id']}", headers={**H, 'Content-Type': 'application/json'}, content=b'{}').status_code == 204
    assert c.get(endpoint).status_code == 404
