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
from app.intake import classify_document,extract_fields,preview,tesseract_diagnostics

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
    monkeypatch.setattr(intake,'_ocr_engine',lambda: object())
    monkeypatch.setattr(intake,'_ocr_image',lambda image, engine:'Quantite : 240 pieces')
    report=preview(path,'scan.pdf')
    assert report['method']=='pdf_hybrid'
    qty=next(item for item in report['fields'] if item['key']=='quantite')
    assert qty['value']=='240' and qty['page']==2 and qty['method']=='pdf_ocr'
    ref=next(item for item in report['fields'] if item['key']=='reference_commande')
    assert ref['page']==1 and ref['method']=='pdf_text'


def test_native_pdf_reads_information_after_the_former_three_page_limit(tmp_path):
    import fitz
    path=tmp_path/'long.pdf'
    with fitz.open() as pdf:
        for page_number in range(6):
            page=pdf.new_page()
            page.insert_text((50,60), f'Page {page_number + 1} - document de travail')
        pdf[5].insert_text((50,90), 'Reference commande : CMD-FIN-006')
        pdf.save(path)
    report=preview(path,path.name,allow_ocr=False)
    reference=next(item for item in report['fields'] if item['key']=='reference_commande')
    assert reference['value']=='CMD-FIN-006'
    assert reference['page']==6
    assert report['reading_status']=='success'
    assert not any('3 premières pages' in warning for warning in report['warnings'])


def test_structured_values_preserve_raw_value_normalization_and_confidence():
    fields={item['key']:item for item in extract_fields(
        'Client : Atelier Atlas\nFournisseur : Textile Maroc\n'
        'Quantité : 1 250,50 pièces\nMontant total : 1,234.50 EUR\nDate : 7/11/2026')}
    assert fields['client']['original_value']=='Atelier Atlas'
    assert fields['fournisseur']['original_value']=='Textile Maroc'
    assert fields['quantite']['normalized_value']=='1250.50'
    assert fields['montant_total']['normalized_value']=='1234.50'
    assert fields['date_document']['normalized_value']=='2026-11-07'
    assert fields['quantite']['status']=='proposed'
    assert fields['quantite']['confidence'] < 1


def test_unrelated_document_is_not_auto_classified_and_fuzzy_business_heading_is_explainable():
    assert classify_document('examen-mathematiques.pdf', 'Examen de mathématiques - intégrales')['status']=='impossible'
    result=classify_document('scan.pdf', 'BON DE LIVRAISON\nQuantité livrée : 42 pièces')
    assert result['decisive']
    assert result['suggestions'][0]['confidence'] >= .60
    assert result['suggestions'][0]['evidence'][0]['source']=='en-tête'


def test_tesseract_diagnostics_distinguish_missing_french_language(monkeypatch):
    import app.intake as intake
    monkeypatch.setattr(intake,'_tesseract_candidates',lambda:['fake-tesseract'])
    monkeypatch.setattr(intake.Path,'is_file',lambda self: True)
    class Answer:
        stdout='List of available languages in "/tmp" (1):\neng\n'
    monkeypatch.setattr(intake.subprocess,'run',lambda *args,**kwargs: Answer())
    result=tesseract_diagnostics()
    assert result['code']=='ocr_language_missing'
    assert result['missing_languages']==['fra']


def test_protected_pdf_and_missing_tesseract_are_reported_precisely(tmp_path, monkeypatch):
    import fitz
    import app.intake as intake
    protected=tmp_path/'protected.pdf'
    with fitz.open() as pdf:
        pdf.new_page().insert_text((50,60),'document protégé')
        pdf.save(protected,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='user')
    report=preview(protected,protected.name)
    assert report['method']=='pdf_protected'
    assert report['limitations'][0]['code']=='pdf_protected'

    scanned=tmp_path/'scan.pdf'
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(scanned)
    monkeypatch.setattr(intake,'_ocr_engine',lambda: (_ for _ in ()).throw(intake.OCRProblem('tesseract_missing','Tesseract absent')))
    report=preview(scanned,scanned.name)
    assert report['limitations'][0]['code']=='tesseract_missing'


@pytest.mark.parametrize(('filename','content','doc_type'),[
    ('facture-2026.pdf','FACTURE\nMontant total : 200 EUR','Facture'),
    ('fiche-emploi.pdf',"FICHE D'EMPLOI\nConsommation tissu : 1,2 m / pièce",'Fiche d’emploi'),
    ('besoin.xlsx','CALCUL DU BESOIN\nBesoin matière : 120 kg','Calcul du besoin'),
    ('reception.pdf','BON DE RÉCEPTION\nQuantité : 20 pièces','Bon de réception'),
])
def test_standard_document_types_remain_explainable(filename,content,doc_type):
    result=classify_document(filename,content)
    assert result['suggestions'][0]['doc_type']==doc_type
    assert result['suggestions'][0]['evidence']


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
    stored=client.get(f'/api/document-versions/{version}/intake').json()
    assert stored['confirmed'][0]['value']=='240'
    assert stored['document_context']['document_version_id']==version
    assert stored['document_context']['folder']=='rose'
    assert stored['sha256']==d.json()['latest']['sha256']
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
