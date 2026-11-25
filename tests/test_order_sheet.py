"""Fiche commande complète : création, valeurs non renseignées ≠ zéro, zéros initiaux, historique
avant/après, droits, rattachement explicite au N° client, transfert d'une demande Client."""
import secrets
import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, hash_password
from app.main import app
from app.models import AuditEvent, Role, User

H = {'X-Framatex-Request': '1'}


def chef():
    client = TestClient(app)
    client.__enter__()
    pw, email = secrets.token_urlsafe(16), f'chef-{uuid.uuid4().hex[:8]}@example.test'
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == 'Administrateur')) or Role(name='Administrateur')
        db.add(User(name='Chef fiche', email=email, password_hash=hash_password(pw), roles=[role])); db.commit()
    assert client.post('/api/auth/login', headers=H, json={'email': email, 'password': pw}).status_code == 200
    return client


def test_full_sheet_create_update_history_and_rights():
    c = chef()
    created = c.post('/api/order-sheets', headers=H, json={'name': 'Costume laine — collection hiver'})
    assert created.status_code == 201, created.text
    lid = created.json()['id']
    sheet = c.get(f'/api/launches/{lid}/sheet').json()
    assert sheet['can_edit'] and sheet['values']['quantity_delivered'] is None          # non renseigné, pas 0
    body = {'description': 'Costume deux pièces', 'workshop': 'Atelier Casablanca', 'client_name': 'Client fictif',
            'article': 'Costume', 'order_ref': '000417', 'color': 'Bleu nuit', 'quantity': 1200, 'of_number': '0042',
            'quantity_launched': 1150, 'quantity_delivered': 0, 'invoice_ref': 'FA-000981', 'desired_date': '2026-12-15'}
    r = c.patch(f'/api/launches/{lid}/sheet', headers=H, json=body)
    assert r.status_code == 200, r.text
    v = r.json()['values']
    assert v['order_ref'] == '000417' and v['of_number'] == '0042' and v['quantity_delivered'] == 0
    assert v['desired_date'] == '2026-12-15'
    r = c.patch(f'/api/launches/{lid}/sheet', headers=H, json={'color': 'Gris anthracite', 'quantity_delivered': None})
    assert r.json()['changes'] == {'color': {'before': 'Bleu nuit', 'after': 'Gris anthracite'},
                                   'quantity_delivered': {'before': 0, 'after': None}}
    with SessionLocal() as db:
        events = [e for e in db.scalars(select(AuditEvent).where(AuditEvent.target_id == lid, AuditEvent.action == 'launch.sheet.update'))]
        assert len(events) == 2 and '"before": "Bleu nuit"' in events[-1].detail
    assert c.patch(f'/api/launches/{lid}/sheet', headers=H, json={'name': ' '}).status_code == 422
    assert c.patch(f'/api/launches/{lid}/sheet', headers=H, json={'client_account_id': 'inexistant'}).status_code == 422
    # Technicien sans affectation : aucune lecture ; avec lecture seule : lecture sans modification.
    tech = c.post('/api/admin/collaborators', headers=H, json={'name': 'Tech fiche', 'email': f't-{uuid.uuid4().hex[:6]}@example.test'}).json()
    t = TestClient(app)
    t.post('/api/auth/login', headers=H, json={'email': tech['collaborator']['email'], 'password': tech['temporary_password']})
    new_pw = secrets.token_urlsafe(16) + 'Aa1!'
    t.post('/api/account/password', headers=H, json={'current_password': tech['temporary_password'], 'new_password': new_pw})
    assert t.get(f'/api/launches/{lid}/sheet').status_code == 404
    c.put(f"/api/admin/collaborators/{tech['collaborator']['id']}/assignments/{lid}", headers=H, json={'folders': {'jaune': ['document.read']}})
    assert t.get(f'/api/launches/{lid}/sheet').json()['values']['of_number'] == '0042'
    assert t.get(f'/api/launches/{lid}/sheet').json()['can_edit'] is False
    assert t.patch(f'/api/launches/{lid}/sheet', headers=H, json={'color': 'Rouge'}).status_code == 403


def test_client_request_fields_transfer_to_launch_sheet():
    c = chef()
    pw = secrets.token_urlsafe(16) + 'Aa1!'
    email = f'client-{uuid.uuid4().hex[:6]}@example.test'
    cl = TestClient(app)
    reg = cl.post('/api/client/register', headers=H, json={'raison_sociale': 'Maison Fictive', 'nom_contact': 'Contact', 'email': email,
                  'telephone': '0600000000', 'adresse': '1 rue', 'pays': 'France', 'password': pw})
    assert reg.status_code == 201, reg.text
    c.patch(f"/api/admin/clients/{reg.json()['id']}/status", headers=H, json={'status': 'active'})
    assert cl.post('/api/client/login', headers=H, json={'email': email, 'password': pw}).status_code == 200
    order = cl.post('/api/client/order-requests', headers=H, json={
        'project_name': 'Costume cérémonie', 'description': 'Coupe droite', 'color': 'Marine', 'article': 'Costume',
        'quantite': 300, 'date_souhaitee': '2027-01-20', 'reference_client': '00PO-77', 'status': 'submitted'})
    assert order.status_code == 201, order.text
    assert order.json()['project_name'] == 'Costume cérémonie'
    made = c.post(f"/api/admin/client-order-requests/{order.json()['id']}/launch", headers=H)
    assert made.status_code in (200, 201), made.text
    launch_id = made.json()['launch']['id']
    v = c.get(f'/api/launches/{launch_id}/sheet').json()['values']
    assert v['name'] == 'Costume cérémonie' and v['color'] == 'Marine' and v['description'] == 'Coupe droite'
    assert v['client_order_ref'] == '00PO-77' and v['desired_date'] == '2027-01-20' and v['quantity'] == 300
    assert v['client_account']['client_code'] == reg.json()['client_code']
    assert v['order_ref'] == order.json()['request_number']           # N° commande FRAMATEX distinct de la référence Client
