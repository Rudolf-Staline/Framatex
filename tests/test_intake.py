"""Vérifie OCR/lecture, classement assisté et confirmation sans contournement des droits."""
import os
import tempfile
os.environ['FRAMATEX_DATA_DIR']=tempfile.mkdtemp(prefix='framat-intake-')
os.environ['FRAMATEX_SECRET_KEY']='intake-secret-key-'*4

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import Base,engine,SessionLocal,hash_password
from app.models import User,Role,RolePermission
from app.intake import classify_document,extract_fields,preview

H={'X-Framatex-Request':'1'}
TEXT=(b'BON DE LIVRAISON\nReference matiere : TISSU-ABC-91\n'
      b'Quantite : 240 pieces\nDate : 17/10/2026\n')

@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            tech=Role(name='Technique',grants=[RolePermission(action='launch.read'),
                  RolePermission(action='document.read',folder_slug='jaune'),
                  RolePermission(action='document.write',folder_slug='jaune')])
            observer=Role(name='Reception',grants=[RolePermission(action='launch.read'),
                  RolePermission(action='document.read',folder_slug='rose')])
            db.add_all([User(name='Admin',email='admin@intake.local',password_hash=hash_password('StrongPassword11!'),roles=[admin]),
                        User(name='Tech',email='tech@intake.local',password_hash=hash_password('StrongPassword11!'),roles=[tech]),
                        User(name='Reception',email='recep@intake.local',password_hash=hash_password('StrongPassword11!'),roles=[observer])]);db.commit()
        login(c,'admin@intake.local')
        yield c
    Base.metadata.drop_all(engine)

def login(c,email):
    assert c.post('/api/auth/login',json={'email':email,'password':'StrongPassword11!'},headers=H).status_code==200

def setup(c):
    resp=c.post('/api/launches',json={'name':'Lancement OCR'},headers=H)
    assert resp.status_code==201,resp.text
    return resp.json()['id']

def test_rule_based_classification_and_field_provenance():
    c=classify_document('scan_BL-021.txt',TEXT.decode('utf-8'))
    assert c['suggestions'][0]['folder']=='rose'
    extracted=extract_fields('Bon de livraison\nRéférence matière : TISSU-ABC-91\nQuantité : 240 pièces\nDate : 17/10/2026')
    bykey={r['key']:r for r in extracted}
    assert bykey['quantite']['value']=='240'
    assert bykey['date_document']['value']=='17/10/2026'
    assert 'Quantité' in bykey['quantite']['source_excerpt']
    assert c['status']=='identified'
    assert classify_document('facture.pdf','')['status']=='probable'
    assert classify_document('fichier.pdf','')['status']=='impossible'
    assert classify_document('document.txt','Bon de livraison\nFiche de prix')['status']=='multiple'


def test_specific_quantities_remain_distinct_and_ambiguous_values_are_flagged():
    fields=extract_fields('Quantité commandée : 5000 pièces\nQuantité produite : 4700 pièces\n'
                          'Quantité livrée : 4500 pièces\nRéférence client : CLI-88')
    bykey={item['key']:item for item in fields}
    assert bykey['quantite_commandee']['value']=='5000'
    assert bykey['quantite_produite']['value']=='4700'
    assert bykey['quantite_livree']['value']=='4500'
    assert bykey['reference_client']['value']=='CLI-88'
    assert 'quantite' not in bykey


def test_word_and_excel_fields_include_source_locator(tmp_path):
    from docx import Document as Word
    from openpyxl import Workbook

    word=Word();word.add_paragraph('COMMANDE CLIENT');word.add_paragraph('Quantité commandée : 1250 pièces')
    word_path=tmp_path/'commande.docx';word.save(word_path)
    word_report=preview(word_path,word_path.name)
    quantity=next(item for item in word_report['fields'] if item['key']=='quantite_commandee')
    assert quantity['method']=='docx_text' and quantity['paragraph']==2

    book=Workbook();sheet=book.active;sheet.title='Production';sheet.append(['Quantité produite :', 1190, 'pièces'])
    excel_path=tmp_path/'production.xlsx';book.save(excel_path)
    excel_report=preview(excel_path,excel_path.name)
    produced=next(item for item in excel_report['fields'] if item['key']=='quantite_produite')
    assert produced['method']=='xlsx_values' and produced['sheet']=='Production' and produced['cell']=='A1:C1'


def test_hybrid_pdf_reads_native_and_scanned_pages_with_page_provenance(tmp_path, monkeypatch):
    import fitz
    import app.intake as intake
    path=tmp_path/'hybrid.pdf'
    with fitz.open() as pdf:
        first=pdf.new_page();first.insert_text((50,60),'COMMANDE CLIENT\nReference commande : CMD-501')
        pdf.new_page()
        pdf.save(path)
    monkeypatch.setattr(intake,'_ocr_image',lambda image, engine:'Quantite : 240 pieces')
    report=preview(path,'scan.pdf')
    assert report['method']=='pdf_hybrid'
    qty=next(item for item in report['fields'] if item['key']=='quantite')
    assert qty['value']=='240' and qty['page']==2 and qty['method']=='pdf_ocr'
    ref=next(item for item in report['fields'] if item['key']=='reference_commande')
    assert ref['page']==1 and ref['method']=='pdf_text'


def test_preview_is_temporary_and_does_not_create_document(client):
    lid=setup(client)
    r=client.post(f'/api/launches/{lid}/intake/preview',files={'file':('bon_de_livraison.txt',TEXT)},headers=H)
    assert r.status_code==200,r.text
    result=r.json()
    assert result['human_validation_required']
    assert result['classification']['suggestions'][0]['folder']=='rose'
    assert len(result['fields'])>=2
    assert client.get(f'/api/launches/{lid}').json()['folders'][1]['documents']==[]


def test_permissions_do_not_show_forbidden_folder_suggestion(client):
    lid=setup(client)
    login(client,'tech@intake.local')
    r=client.post(f'/api/launches/{lid}/intake/preview',files={'file':('facture_2026.txt',b'Facture numero 100')},headers=H)
    assert r.status_code==200
    assert r.json()['classification']['suggestions']==[]
    login(client,'recep@intake.local')
    r=client.post(f'/api/launches/{lid}/intake/preview',files={'file':('facture.txt',b'FACTURE')},headers=H)
    assert r.status_code==403


def test_confirmed_fields_attached_to_exact_version(client):
    lid=setup(client)
    d=client.post(f'/api/launches/{lid}/documents',data={'folder':'rose','title':'BL','doc_type':'Bon de livraison'},files={'file':('bl.txt',TEXT)},headers=H)
    assert d.status_code==201
    version=d.json()['latest']['id']
    analysis=client.get(f'/api/document-versions/{version}/intake')
    assert analysis.status_code==200 and analysis.json()['confirmed']==[]
    body={'field_key':'quantite','value':'240','unit':'pièces','source_excerpt':'Quantité : 240 pièces'}
    assert client.post(f'/api/document-versions/{version}/intake/confirm',json=body,headers=H).status_code==201
    assert client.post(f'/api/document-versions/{version}/intake/confirm',json=body,headers=H).status_code==409
    assert client.get(f'/api/document-versions/{version}/intake').json()['confirmed'][0]['value']=='240'
    assert client.post(f'/api/document-versions/{version}/intake/confirm',json={**body,'field_key':'unknown'},headers=H).status_code==422
    d2=client.post(f'/api/documents/{d.json()["id"]}/versions',files={'file':('new.txt',b'nouvelle version')},headers=H)
    assert d2.status_code==201
    assert client.post(f'/api/document-versions/{version}/intake/confirm',json={**body,'field_key':'montant'},headers=H).status_code==409
    login(client,'recep@intake.local')
    assert client.post(f'/api/document-versions/{version}/intake/confirm',json=body,headers=H).status_code==403


def test_version_comparison_is_scoped_to_same_document_and_permission(client):
    lid=setup(client)
    first=client.post(f'/api/launches/{lid}/documents',data={'folder':'rose','title':'BL compare','doc_type':'Bon de livraison'},
        files={'file':('bl1.txt',b'Quantite livree : 10 pieces')},headers=H).json()
    v1=first['latest']['id']
    assert client.get(f'/api/document-versions/{v1}/compare-previous').json()['status']=='first_version'
    second=client.post(f"/api/documents/{first['id']}/versions",files={'file':('bl2.txt',b'Quantite livree : 12 pieces')},headers=H).json()
    result=client.get(f"/api/document-versions/{second['latest']['id']}/compare-previous")
    assert result.status_code==200 and result.json()['previous_version']==1
    login(client,'tech@intake.local')
    assert client.get(f"/api/document-versions/{second['latest']['id']}/compare-previous").status_code==403


def test_upload_validation_on_preview(client):
    lid=setup(client)
    assert client.post(f'/api/launches/{lid}/intake/preview',files={'file':('bad.pdf',b'not pdf')},headers=H).status_code==422
    assert client.post(f'/api/launches/{lid}/intake/preview',files={'file':('bad.exe',b'123')},headers=H).status_code==422
