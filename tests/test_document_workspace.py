import hashlib
import io
import random
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core import Base, SessionLocal, engine, hash_password
from app.intake import classify_document, extract_fields
from app.document_intelligence_models import DocumentRelationshipDecision
from app.main import app
from app.models import Role, User


H = {'X-Framatex-Request': '1'}
PASSWORD = 'WorkspacePassword-2026!'


@pytest.fixture
def workspace():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            role = Role(name='Administrateur')
            db.add_all(User(name=name, email=email, roles=[role], password_hash=hash_password(PASSWORD))
                       for name, email in [('Alice', 'alice@workspace.test'), ('Bruno', 'bruno@workspace.test')])
            db.commit()
        login(client)
        yield client
    Base.metadata.drop_all(engine)


def login(client, name='alice'):
    assert client.post('/api/auth/login', headers=H, json={'email': name + '@workspace.test',
                                                           'password': PASSWORD}).status_code == 200


def launch(client, name):
    response = client.post('/api/launches', headers=H, json={'name': name, 'order_ref': name, 'standard_profile': True})
    assert response.status_code == 201, response.text
    return response.json()['id']


def stage(client, launch_id, name, content, folder='jaune'):
    return client.post(f'/api/launches/{launch_id}/document-uploads', headers=H, data={'folder': folder},
                       files={'file': (name, content)})


def publish(client, launch_id, staged, folder, kind, **data):
    return client.post(f'/api/launches/{launch_id}/document-uploads/{staged}/publish', headers=H,
                       json={'folder': folder, 'doc_type': kind, 'title': kind, **data})


def checklist(client, launch_id, kind):
    report = client.get(f'/api/launches/{launch_id}/completeness').json()
    return next(row for row in report['rows'] if row['document_type'] == kind)


def test_wrong_type_does_not_count_and_manual_exceptions_are_audited(workspace):
    client = workspace
    dossier = launch(client, 'CMD-WRONG')
    content = b'BON DE LIVRAISON\nReference commande : REF-2010\nQuantite : 50 pieces'
    receipt = stage(client, dossier, 'fiche_de_prix.txt', content).json()
    assert receipt['analysis']['classification']['suggestions'][0]['doc_type'] == 'Bon de livraison'
    assert receipt['sha256'] == hashlib.sha256(content).hexdigest()
    rule = checklist(client, dossier, 'Fiche de prix')
    assert rule['status'] == 'missing'
    result = publish(client, dossier, receipt['id'], 'jaune', 'Fiche de prix', rule_id=rule['id'])
    assert result.status_code == 201, result.text
    doc = result.json()
    assert doc['identification'] == 'incompatible'
    assert doc['latest']['sha256'] == receipt['sha256']
    row = checklist(client, dossier, 'Fiche de prix')
    assert row['status'] == 'incompatible' and len(row['documents']) == 1
    assert client.post(f'/api/launches/{dossier}/completeness/rules/{rule["id"]}/validate', headers=H,
                       json={'document_id': doc['id']}).status_code == 409
    assert publish(client, dossier, receipt['id'], 'rose', 'Bon de livraison').status_code == 404
    path = f'/api/document-versions/{doc["latest"]["id"]}/identification/confirm'
    assert client.post(path, headers=H, json={'justification': '            '}).status_code == 422
    assert client.post(path, headers=H, json={'justification': 'Vérification manuelle documentée par le collaborateur'}).status_code == 200
    assert checklist(client, dossier, 'Fiche de prix')['status'] == 'pending_validation'
    nouvelle = stage(client, dossier, 'nouvelle.txt', b'Contenu sans identification').json()
    result = publish(client, dossier, nouvelle['id'], 'jaune', 'Fiche de prix', document_id=doc['id'])
    assert result.status_code == 201 and result.json()['latest']['number'] == 2
    assert checklist(client, dossier, 'Fiche de prix')['status'] == 'to_verify'


def test_receipts_are_bound_to_owner_and_launch_and_can_be_corrected(workspace):
    client = workspace
    first = launch(client, 'CMD-A')
    second = launch(client, 'CMD-B')
    receipt = stage(client, first, 'scan.txt', b'Bon de livraison').json()['id']
    assert publish(client, second, receipt, 'rose', 'Bon de livraison').status_code == 404
    login(client, 'bruno')
    assert publish(client, first, receipt, 'rose', 'Bon de livraison').status_code == 404
    login(client)
    assert publish(client, first, receipt, 'rose', 'Bon de livraison').json()['identification'] == 'matched'
    assert checklist(client, first, 'Bon de livraison')['status'] == 'present'
    canceled = stage(client, first, 'canceled.txt', b'Bon de livraison #2').json()['id']
    assert client.delete(f'/api/launches/{first}/document-uploads/{canceled}', headers=H).status_code == 204
    assert publish(client, first, canceled, 'rose', 'Bon de livraison').status_code == 404
    board = client.get(f'/api/launches/{first}/dashboard').json()
    assert [row['id'] for row in board['launches']] == [first]
    assert board['kpis']['deposited_documents'] == 1
    for entries in (board['missing_documents'], board['activity'], board['priorities']['items']):
        assert all(row['launch_id'] == first for row in entries)


def test_confirmed_extraction_is_scoped_and_exposes_version_delta(workspace):
    client = workspace
    first, second = [launch(client, label) for label in ('CMD-5000', 'CMD-9000')]
    rule = {'name': 'Quantités de production comparées', 'field_key': 'quantite_lancement',
            'left_doc_type': 'Commande client', 'right_doc_type': 'Fiche d’emploi',
            'left_folder': 'jaune', 'right_folder': 'jaune', 'tolerance': '0'}
    assert client.post('/api/admin/quality-rules', headers=H, json=rule).status_code == 201
    sources = []
    for dossier, kind, quantity in [(first, 'Commande client', '5 000'), (first, 'Fiche d’emploi', '4 500'),
                                     (second, 'Commande client', '9 000')]:
        receipt = stage(client, dossier, 'document.txt', f'{kind}\nQuantité : {quantity} pièces'.encode()).json()
        doc = publish(client, dossier, receipt['id'], 'jaune', kind).json()
        source = receipt['analysis']['fields'][0]
        endpoint = f'/api/document-versions/{doc["latest"]["id"]}/intake/confirm'
        payload = {'field_key': source['key'], **{key: source[key] for key in ('value', 'unit', 'source_excerpt')}}
        result = client.post(endpoint, headers=H, json=payload)
        assert result.status_code == 201, result.text
        sources.append(doc['latest']['id'])
    alert = client.get(f'/api/launches/{first}/quality').json()['rows'][0]
    assert alert['status'] == 'difference' and alert['delta'] == '500'
    assert [item['version_id'] for item in alert['pair']] == sources[:2]
    assert all(item['provenance'] == 'Lecture documentaire confirmée' and item['source_excerpt'] for item in alert['pair'])
    assert client.get(f'/api/launches/{second}/quality').json()['rows'][0]['status'] == 'unavailable'


def test_analysis_respects_content_ambiguity_and_opaque_workbook_paths(workspace):
    from openpyxl import Workbook

    assert not classify_document('bon_de_livraison.pdf', '')['decisive']
    assert classify_document('fichier.pdf', 'Bon de livraison\nFiche de prix')['ambiguous']
    assert extract_fields('Quantité : 20 pièces\nQuantité : 25 pièces')[0]['status'] == 'ambiguous'
    book = Workbook()
    book.active.title = 'Calcul du besoin'
    book.active.append(['Quantité', 150, 'pièces'])
    book.active.append(['Quantité', '=100+500', 'pièces'])
    output = io.BytesIO()
    book.save(output)
    result = stage(workspace, launch(workspace, 'CMD-EXCEL'), 'besoin.xlsx', output.getvalue()).json()['analysis']
    assert result['method'] == 'xlsx_values'
    assert result['fields'][0]['value'] == '150'
    assert '=100+500' not in result['text_excerpt']


def test_guided_upload_distinguishes_exact_duplicate_version_and_independent_document(workspace):
    dossier = launch(workspace, 'CMD-RELATIONSHIPS')
    original = (b'COMMANDE CLIENT\nReference commande : CMD-REL-42\n'
                b'Reference article : ART-7\nQuantite : 5000 pieces')
    first_stage = stage(workspace, dossier, 'commande-initiale.txt', original).json()
    first = publish(workspace, dossier, first_stage['id'], 'jaune', 'Commande client').json()
    first_version = first['latest']['id']

    exact_stage = stage(workspace, dossier, 'copie-renommee.txt', original).json()
    exact = exact_stage['analysis']['relationships'][0]
    assert exact['kind'] == 'exact_duplicate' and exact['candidate_version_id'] == first_version
    refused = publish(workspace, dossier, exact_stage['id'], 'jaune', 'Commande client')
    assert refused.status_code == 409
    kept = publish(workspace, dossier, exact_stage['id'], 'jaune', 'Commande client',
                   relationship_action='keep_duplicate',
                   relationship_candidate_version_id=first_version,
                   relationship_reason='Copie contractuelle conservée avec justification').json()
    assert kept['id'] != first['id']
    with SessionLocal() as db:
        decision = db.query(DocumentRelationshipDecision).filter_by(uploaded_version_id=kept['latest']['id']).one()
        assert decision.relationship_kind == 'exact_duplicate' and decision.action == 'keep_duplicate'

    changed = (b'COMMANDE CLIENT\nReference commande : CMD-REL-42\n'
               b'Reference article : ART-7\nQuantite : 5200 pieces')
    version_stage = stage(workspace, dossier, 'commande-revisee.txt', changed).json()
    proposal = next(item for item in version_stage['analysis']['relationships']
                    if item['candidate_document_id'] == first['id'])
    assert proposal['kind'] == 'new_version'
    version = publish(workspace, dossier, version_stage['id'], 'jaune', 'Commande client',
                      document_id=first['id'], relationship_action='new_version',
                      relationship_candidate_version_id=proposal['candidate_version_id']).json()
    assert version['id'] == first['id'] and version['latest']['number'] == 2
    comparison=workspace.get(f"/api/document-versions/{version['latest']['id']}/compare-previous").json()
    assert any(change['field']=='quantite' and change['kind']=='changed' for change in comparison['changes'])
    assert comparison['text_changes']

    independent = (b'COMMANDE CLIENT\nReference commande : CMD-OTHER-99\n'
                   b'Reference article : ART-OTHER\nQuantite : 80 pieces')
    independent_stage = stage(workspace, dossier, 'autre-commande.txt', independent).json()
    assert independent_stage['analysis']['relationships'] == []


def test_similar_content_is_only_a_proposal_and_never_auto_merged(workspace):
    dossier = launch(workspace, 'CMD-SIMILAR')
    first_text = b'FICHE DE PRIX\nTissu coton bleu marine\nPrix unitaire : 12 MAD/piece\nTotal HT : 60000 MAD'
    first_stage = stage(workspace, dossier, 'prix-v1.txt', first_text).json()
    first = publish(workspace, dossier, first_stage['id'], 'jaune', 'Fiche de prix').json()
    similar_text = b'FICHE DE PRIX\nTissu coton bleu marine\nPrix unitaire : 13 MAD/piece\nTotal HT : 65000 MAD'
    similar_stage = stage(workspace, dossier, 'prix-copie.txt', similar_text).json()
    proposal = similar_stage['analysis']['relationships'][0]
    assert proposal['kind'] == 'potential_duplicate'
    separate = publish(workspace, dossier, similar_stage['id'], 'jaune', 'Fiche de prix',
                       relationship_action='new_document',
                       relationship_candidate_version_id=proposal['candidate_version_id']).json()
    assert separate['id'] != first['id'] and separate['latest']['number'] == 1


def test_configured_upload_limit_and_archive_without_analysis(workspace, monkeypatch):
    import pymupdf

    dossier = launch(workspace, 'CMD-SIZE')
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), 'DOSSIER TECHNIQUE')
        pdf.embfile_add('annexe.bin', random.Random(42).randbytes(21 * 1024 * 1024))
        raw = pdf.tobytes()
    result = stage(workspace, dossier, 'grand.pdf', raw)
    assert result.status_code == 201, result.text
    assert result.json()['analysis']['method'] == 'size_limit'
    assert publish(workspace, dossier, result.json()['id'], 'jaune', 'Dossier technique client').json()['identification'] == 'to_verify'
    monkeypatch.setenv('FRAMATEX_UPLOAD_PDF_MIB', '20')
    assert stage(workspace, dossier, 'grand.pdf', raw).status_code == 413


def test_archive_bomb_and_oversized_chunked_request_are_rejected(workspace, monkeypatch):
    dossier = launch(workspace, 'CMD-CAPS')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as book:
        book.writestr('[Content_Types].xml', '<Types/>')
        book.writestr('xl/workbook.xml', '<workbook/>')
        book.writestr('xl/worksheets/sheet1.xml', b'x' * (6 * 1024 * 1024))
    assert stage(workspace, dossier, 'archive.xlsx', stream.getvalue()).status_code == 422
    for kind in ('PDF', 'EXCEL', 'WORD', 'IMAGE', 'OTHER'):
        monkeypatch.setenv(f'FRAMATEX_UPLOAD_{kind}_MIB', '1')

    def chunks():
        yield (b'--bound\r\nContent-Disposition: form-data; name="folder"\r\n\r\njaune\r\n--bound\r\n'
               b'Content-Disposition: form-data; name="file"; filename="gros.txt"\r\n\r\n')
        for _ in range(9):
            yield b'x' * (256 * 1024)
        yield b'\r\n--bound--\r\n'

    response = workspace.post(f'/api/launches/{dossier}/document-uploads', content=chunks(),
                              headers={**H, 'Content-Type': 'multipart/form-data; boundary=bound'})
    assert response.status_code == 413, response.text
