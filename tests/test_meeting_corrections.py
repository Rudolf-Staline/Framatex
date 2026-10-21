"""Meeting: version comments, explicit document expectations and partial receipts."""
import io
import os
import tempfile
os.environ.setdefault('FRAMATEX_DATA_DIR', tempfile.mkdtemp(prefix='framat-meeting-'))
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import select, text
import pytest
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role, RolePermission, Launch, AuditEvent
from app.document_comment_models import DocumentComment
from tools.migrate_meeting_corrections import apply_to_connection

H = {'X-Framatex-Request': '1'}
PASSWORD = 'MeetingCorrections2026!'

@pytest.fixture
def system():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin = Role(name='Administrateur')
            reader = Role(name='Lecture jaune', grants=[RolePermission(action='launch.read'), RolePermission(action='document.read', folder_slug='jaune')])
            rose = Role(name='Lecture rose', grants=[RolePermission(action='launch.read'), RolePermission(action='document.read', folder_slug='rose')])
            db.add_all([User(name='Admin', email='admin@meeting.local', password_hash=hash_password(PASSWORD), roles=[admin]),
                        User(name='Lecteur', email='reader@meeting.local', password_hash=hash_password(PASSWORD), roles=[reader]),
                        User(name='Réception', email='rose@meeting.local', password_hash=hash_password(PASSWORD), roles=[rose])])
            db.commit()
        login(client)
        yield client
    Base.metadata.drop_all(engine)


def login(c, email='admin@meeting.local'):
    assert c.post('/api/auth/login', json={'email': email, 'password': PASSWORD}, headers=H).status_code == 200


def launch(c):
    r = c.post('/api/launches', json={'name': 'Commande réunion'}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


def doc(c, lid, title='Fiche technique', folder='jaune', filename='fiche.txt', content=b'Test local'):
    r = c.post(f'/api/launches/{lid}/documents', data={'folder': folder, 'title': title, 'doc_type': title},
               files={'file': (filename, content)}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def datum(c, version, value, unit='pièce'):
    r = c.post(f'/api/document-versions/{version}/data', json={'field_key': 'quantite_lancement', 'value': str(value), 'unit': unit}, headers=H)
    assert r.status_code == 201, r.text


def cumulative_rule(c):
    r = c.post('/api/admin/quality-rules', json={'name': 'Commande et réceptions', 'field_key': 'quantite_lancement',
        'left_doc_type': 'Commande client', 'right_doc_type': 'Bon de réception', 'left_folder': 'jaune', 'right_folder': 'rose',
        'comparison_mode': 'cumulative_delivery'}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


def test_comment_version_ownership_permissions_and_history(system):
    c = system; lid = launch(c); a = doc(c, lid); b = doc(c, lid, title='Autre pièce')
    path = f'/api/documents/{a["id"]}/comments'
    payload = {'version_id': a['latest']['id'], 'body': '  Vérifier la composition annoncée.  '}
    assert c.post(path, json={**payload, 'version_id': b['latest']['id']}, headers=H).status_code == 422
    assert c.post(path, json={**payload, 'body': '  '}, headers=H).status_code == 422
    saved = c.post(path, json=payload, headers=H)
    assert saved.status_code == 201, saved.text
    assert saved.json()['body'] == payload['body'].strip()
    assert c.post(f'/api/documents/{a["id"]}/versions', files={'file': ('fiche-v2.txt', b'Composition corrigee')}, headers=H).status_code == 201
    thread = c.get(path).json()
    assert thread['items'][0]['version'] == 1
    assert thread['items'][0]['author']['name'] == 'Admin'
    login(c, 'reader@meeting.local')
    assert c.get(path).json()['can_comment'] is False
    assert c.post(path, json=payload, headers=H).status_code == 403
    with SessionLocal() as db:
        l = db.get(Launch, lid); l.restricted = True; db.commit()
    assert c.get(path).status_code == 404
    login(c, 'rose@meeting.local')
    assert c.get(path).status_code == 404
    login(c)
    with SessionLocal() as db:
        assert db.scalar(select(DocumentComment)).body == payload['body'].strip()
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == 'document.comment.create')) is not None


def test_pdf_comment_page_and_client_isolation(system):
    c = system; lid = launch(c)
    pdf = PdfWriter(); pdf.add_blank_page(width=200, height=200); output = io.BytesIO(); pdf.write(output)
    d = doc(c, lid, filename='plan.pdf', content=output.getvalue())
    path = f'/api/documents/{d["id"]}/comments'; payload = {'version_id': d['latest']['id'], 'body': 'Réviser cette page.', 'page_number': 1}
    assert c.post(path, json=payload, headers=H).status_code == 201
    for page in [0, 2, 1.5, True]:
        assert c.post(path, json={**payload, 'page_number': page}, headers=H).status_code == 422
    text_doc = doc(c, lid)
    assert c.post(f'/api/documents/{text_doc["id"]}/comments', json={**payload, 'version_id': text_doc['latest']['id']}, headers=H).status_code == 422
    company = c.post('/api/clients', json={'name': 'Client externe'}, headers=H).json()
    assert c.post(f'/api/clients/{company["id"]}/contacts', json={'name': 'Client', 'email': 'client@meeting.local', 'password': PASSWORD}, headers=H).status_code == 201
    login(c, 'client@meeting.local')
    assert c.get(path).status_code == 403
    assert c.post(path, json=payload, headers=H).status_code == 403


def test_partial_receipts_accumulate_and_overreceipt_is_reviewed(system):
    c = system; lid = launch(c); cumulative_rule(c)
    ordered = doc(c, lid, 'Commande client', content=b'Commande 100 pieces')
    first = doc(c, lid, 'Bon de réception', 'rose', content=b'Lot 1: 40 pieces')
    datum(c, ordered['latest']['id'], 100); datum(c, first['latest']['id'], 40)
    def report(): return c.get(f'/api/launches/{lid}/quality').json()['rows'][0]
    row = report(); assert row['status'] == 'partial_delivery' and row['totals']['remaining'] == '60'
    second = doc(c, lid, 'Bon de réception', 'rose', content=b'Lot 2: 60 pieces'); datum(c, second['latest']['id'], 60)
    assert report()['status'] == 'consistent'
    changed = c.post(f'/api/documents/{second["id"]}/versions', files={'file': ('lot2-v2.txt', b'Lot2 corrige: 65 pieces')}, headers=H).json()
    assert report()['status'] == 'unavailable'  # Never reuse a value from the previous version.
    datum(c, changed['latest']['id'], 65)
    row = report(); assert row['status'] == 'difference' and row['totals']['received'] == '105'
    rid = row['rule_id']
    assert c.post(f'/api/launches/{lid}/quality/{rid}/decisions', json={'signature': row['signature'], 'decision': 'to_correct', 'note': 'Dépassement à vérifier avec la réception'}, headers=H).status_code == 201
    third = doc(c, lid, 'Bon de réception', 'rose', content=b'Lot3: 1 piece'); datum(c, third['latest']['id'], 1)
    assert 'decision' not in report()  # An extra receipt changes the evidence signature.
    login(c, 'reader@meeting.local')
    assert c.get(f'/api/launches/{lid}/quality').json()['rows'] == []


def test_duplicate_receipts_and_missing_values_are_not_silently_summed(system):
    c = system; lid = launch(c); cumulative_rule(c)
    ordered = doc(c, lid, 'Commande client', content=b'Commande 100'); datum(c, ordered['latest']['id'], 100)
    first = doc(c, lid, 'Bon de réception', 'rose', content=b'Lot 20'); datum(c, first['latest']['id'], 20)
    second = doc(c, lid, 'Bon de réception', 'rose', content=b'Lot 20'); datum(c, second['latest']['id'], 20)
    row = c.get(f'/api/launches/{lid}/quality').json()['rows'][0]
    assert row['status'] == 'ambiguous' and 'doublons' in row['reason']
    invalid = c.post('/api/admin/quality-rules', json={'name': 'Cumul de prix interdit', 'field_key': 'prix_unitaire', 'left_doc_type': 'A1', 'right_doc_type': 'B1', 'left_folder': 'jaune', 'right_folder': 'rose', 'comparison_mode': 'cumulative_delivery'}, headers=H)
    assert invalid.status_code == 422


def test_list_document_checks_respect_folder_permissions_and_schema_is_repeatable(system):
    c = system; lid = launch(c)
    p = c.post('/api/admin/completeness/profiles', json={'name': 'Commande test', 'description': ''}, headers=H)
    assert p.status_code == 201, p.text
    profile = p.json()['id']
    for folder, title in [('jaune', 'Commande client'), ('vert', 'Facture interne')]:
        r = c.post(f'/api/admin/completeness/profiles/{profile}/rules', json={'folder': folder, 'title': title, 'document_type': title, 'due_phase': 'preparation', 'requires_validation': False}, headers=H)
        assert r.status_code == 201, r.text
    assert c.patch(f'/api/launches/{lid}/completeness/context', json={'profile_id': profile, 'phase': 'preparation'}, headers=H).status_code == 200
    login(c, 'reader@meeting.local')
    row = next(r for r in c.get('/api/launches').json() if r['id'] == lid)
    assert row['document_check']['missing'] == 1 and row['document_check']['partial_visibility'] is True
    with engine.begin() as conn:
        before = conn.scalar(text('select count(*) from launches'))
        apply_to_connection(conn); apply_to_connection(conn)
        assert conn.scalar(text('select count(*) from launches')) == before
