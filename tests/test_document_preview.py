"""Visionneuse : aperçus PDF (pages, recherche), Excel (valeurs, formules), Word, email, image ;
consultation sans téléchargement ; refus sans accès ; version supprimée inaccessible."""
import io
import secrets
import uuid

import fitz
from docx import Document as Docx
from fastapi.testclient import TestClient
from openpyxl import Workbook

from tests.test_order_sheet import H, chef
from app.main import app


def pdf_bytes(pages):
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(); page.insert_text((72, 90), text, fontsize=14)
    return doc.tobytes()


def xlsx_bytes():
    wb = Workbook(); ws = wb.active; ws.title = 'Besoin'
    ws.append(['Article', 'Quantité', 'Prix', 'Total']); ws.append(['Costume', 120, 85.5, '=B2*C2'])
    wb.create_sheet('Notes')['A1'] = 'Coloris : Écru'
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def docx_bytes():
    d = Docx(); d.add_heading('Fiche technique', 1); d.add_paragraph('Tissu laine 100 %')
    t = d.add_table(rows=1, cols=2); t.rows[0].cells[0].text = 'Taille'; t.rows[0].cells[1].text = '48'
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


def upload(c, lid, name, data, folder='jaune'):
    r = c.post(f'/api/launches/{lid}/documents', headers=H, data={'folder': folder, 'title': name, 'doc_type': 'Autre'},
               files={'file': (name, data, 'application/octet-stream')})
    assert r.status_code == 201, r.text
    return r.json()


def test_preview_formats_rights_and_deleted_versions():
    c = chef()
    lid = c.post('/api/order-sheets', headers=H, json={'name': f'Visionneuse {uuid.uuid4().hex[:5]}'}).json()['id']
    pdf = upload(c, lid, 'fiche.pdf', pdf_bytes(['Page un : tissu laine', 'Page deux : doublure satin']))
    meta = c.get(f"/api/document-versions/{pdf['latest']['id']}/preview").json()
    assert meta['kind'] == 'pdf' and meta['pages'] == 2 and meta['can_download']
    page = c.get(f"/api/document-versions/{pdf['latest']['id']}/preview/page/2?zoom=1")
    assert page.status_code == 200 and page.headers['content-type'] == 'image/png' and page.content[:4] == b'\x89PNG'
    hits = c.get(f"/api/document-versions/{pdf['latest']['id']}/preview/search", params={'q': 'satin'}).json()['hits']
    assert [h['page'] for h in hits] == [2]
    xl = upload(c, lid, 'besoin.xlsx', xlsx_bytes())
    m = c.get(f"/api/document-versions/{xl['latest']['id']}/preview").json()
    assert [s['name'] for s in m['sheets']] == ['Besoin', 'Notes']
    sheet = c.get(f"/api/document-versions/{xl['latest']['id']}/preview/sheet", params={'sheet': 'Besoin'}).json()
    assert sheet['rows'][1][3]['f'] == '=B2*C2' and sheet['columns'][:4] == ['A', 'B', 'C', 'D']
    word = upload(c, lid, 'fiche.docx', docx_bytes())
    blocks = c.get(f"/api/document-versions/{word['latest']['id']}/preview").json()['blocks']
    assert blocks[0] == {'type': 'h1', 'text': 'Fiche technique'} and blocks[-1]['rows'] == [['Taille', '48']]
    eml = upload(c, lid, 'mail.eml', b'Subject: Livraison <b>lot</b>\r\nFrom: atelier@example.test\r\nTo: chef@example.test\r\nDate: Mon, 1 Dec 2026 10:00:00 +0000\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nLivraison confirmee.\r\n')
    mail = c.get(f"/api/document-versions/{eml['latest']['id']}/preview").json()['email']
    assert mail['subject'].startswith('Livraison') and 'Livraison confirmee' in mail['body']
    # Consultation sans téléchargement : aperçus oui, fichier original non.
    tech = c.post('/api/admin/collaborators', headers=H, json={'name': 'Lecteur', 'email': f'l-{uuid.uuid4().hex[:6]}@example.test'}).json()
    t = TestClient(app); pw = secrets.token_urlsafe(16) + 'Aa1!'
    t.post('/api/auth/login', headers=H, json={'email': tech['collaborator']['email'], 'password': tech['temporary_password']})
    t.post('/api/account/password', headers=H, json={'current_password': tech['temporary_password'], 'new_password': pw})
    assert t.get(f"/api/document-versions/{pdf['latest']['id']}/preview").status_code == 404          # sans affectation
    c.put(f"/api/admin/collaborators/{tech['collaborator']['id']}/assignments/{lid}", headers=H, json={'folders': {'jaune': ['document.read']}})
    assert t.get(f"/api/document-versions/{pdf['latest']['id']}/preview").json()['can_download'] is False
    assert t.get(f"/api/document-versions/{pdf['latest']['id']}/preview/page/1").status_code == 200
    assert t.get(f"/api/documents/{pdf['id']}/versions/1/download").status_code == 403
    # Version supprimée : plus d'aperçu (la corbeille reste le seul accès).
    assert c.request('DELETE', f"/api/documents/{pdf['id']}", headers={**H, 'Content-Type': 'application/json'}, content=b'{}').status_code == 204
    assert c.get(f"/api/document-versions/{pdf['latest']['id']}/preview").status_code == 404


def test_history_details_before_after_reason_and_version():
    c = chef()
    lid = c.post('/api/order-sheets', headers=H, json={'name': f'Historique {uuid.uuid4().hex[:5]}', 'color': 'Bleu'}).json()['id']
    c.patch(f'/api/launches/{lid}/sheet', headers=H, json={'color': 'Vert', 'of_number': '007'})
    doc = upload(c, lid, 'note.txt', b'v1')
    c.post(f"/api/documents/{doc['id']}/versions", headers=H, files={'file': ('note.txt', b'v2', 'text/plain')})
    c.request('DELETE', f"/api/documents/{doc['id']}", headers={**H, 'Content-Type': 'application/json'}, content=b'{"reason": "Erreur de classement"}')
    items = c.get('/api/workspace/activity', params={'launch_id': lid}).json()['items']
    sheet = next(i for i in items if i['action'] == 'launch.sheet.update')
    assert {(x['field'], x['before'], x['after']) for x in sheet['changes']} == {('color', 'Bleu', 'Vert'), ('of_number', None, '007')}
    deletion = next(i for i in items if i['action'] == 'document.delete')
    assert deletion['reason'] == 'Erreur de classement' and deletion['doc_deleted'] is True
    upload_event = next(i for i in items if i['action'] == 'document.upload')
    assert upload_event['original_name'] == 'note.txt' and upload_event['version_number'] in (1, None)
