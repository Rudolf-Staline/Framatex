"""Recette Chromium des dépôts guidés, sur une installation jetable.

    python scripts/validate_document_workspace.py --output data/document-workspace
"""
from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import sys

from demo_browser_full import nav
from demo_full_platform import Browser, internal_login
import qa_platform_review as recipe
from windows_runtime import browser_executable


def native_pdf(text, attachment_size=0):
    import pymupdf as fitz
    with fitz.open() as pdf:
        pdf.new_page().insert_text((56, 72), text, fontsize=18)
        if attachment_size:
            pdf.embfile_add('piece-annexee.bin', os.urandom(attachment_size))
        return pdf.tobytes()


def word_document(title, text):
    from docx import Document
    doc = Document()
    doc.add_heading(title)
    doc.add_paragraph(text)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def workspace(qa, browser, server, captures, ocr_available):
    from playwright.sync_api import expect
    view = Browser(browser, server.base, 1440, captures)
    page = view.page
    page.set_default_timeout(12000)
    request = view.context.request
    failed = []
    expected_network_failure = set()
    page.on('requestfailed', lambda req: failed.append((req.url, req.failure)))
    internal_login(view, 'recette@framatex.test', server.password)
    base = server.base
    record = request.post(base + '/api/launches', headers=recipe.H,
                          data={'name': 'Atelier textile — recette documentaire', 'order_ref': 'CMD-RECETTE-01',
                                'client_name': 'Atelier Démonstration', 'standard_profile': True})
    assert record.ok, record.text()
    ident = record.json()['id']
    path = base + f'/api/launches/{ident}'
    other = server.ids['B']

    def test(label, fn):
        def checked():
            try:
                return fn()
            except Exception as exc:
                number = len(qa.results)
                page.screenshot(path=str(captures / f'echec-{number}.png'))
                print(qa.redact(str(exc)), flush=True)
                raise
        qa.run('Espace documentaire Chromium', label, checked)

    def capture(name):
        width = page.viewport_size['width']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, name)
        page.screenshot(path=str(captures / f'{width}-{name}.jpg'), type='jpeg', quality=86, animations='disabled')

    def open_order_dashboard():
        nav(page, 'home')
        page.select_option('#dash-order', ident)
        page.locator('#dash-select-order button[type=submit]').click()
        expect(page.locator('h1')).to_have_text('Tableau de bord de la commande')

    def open_order():
        open_order_dashboard()
        page.locator('#dj-dashboard-folders').click()
        expect(page.locator('.dj-folder')).to_have_count(4)

    def open_yellow():
        open_order()
        page.locator('.dj-folder[data-folder="jaune"]').click()
        expect(page.locator('[data-folder-panel="jaune"]')).to_be_visible()

    def line(title):
        return page.locator('.dj-checklist:not(.dj-other-table) tr').filter(has=page.get_by_text(title, exact=True))

    def select_file(name, raw):
        page.locator('#ops-file').set_input_files({'name': name, 'mimeType': 'application/octet-stream', 'buffer': raw})

    def save():
        with page.expect_response(lambda response: response.url.endswith('/publish')) as result:
            page.locator('#ops-upload-form [type=submit]').click()
        assert result.value.status == 201, result.value.text()
        return result.value.json()

    def verify_folder_tours():
        for width in (1920, 1440, 1024, 820, 390):
            page.set_viewport_size({'width': width, 'height': 960 if width > 820 else 844})
            nav(page, 'home')
            capture('tableau-general')
            open_order_dashboard()
            expect(page.locator('.dj-summary')).to_contain_text('CMD-RECETTE-01')
            expect(page.locator('.dj-dash')).not_to_contain_text('FR-DEMO-2026-0142')
            capture('tableau-commande')
            page.locator('#dj-dashboard-folders').click()
            expect(page.locator('.dj-folder')).to_have_count(4)
            assert page.locator('#dj-panel-documents .dj-checklist').count() == 0
            colors = page.locator('.dj-folder-top').evaluate_all('nodes => nodes.map(n => getComputedStyle(n).backgroundColor)')
            assert len(set(colors)) == 4 and 'rgba(0, 0, 0, 0)' not in colors, colors
            capture('quatre-sous-dossiers')
            for folder, label, count in [('jaune', 'jaune', 10), ('rose', 'rose', 4), ('bleu', 'bleu', 5), ('vert', 'vert', 3)]:
                page.locator(f'.dj-folder[data-folder="{folder}"]').click()
                expect(page.locator('h1')).to_have_text(f'Sous-dossier {label}')
                expect(page.locator('.dj-checklist:not(.dj-other-table) tbody tr')).to_have_count(count)
                expect(page.locator('[data-folder-panel]')).to_have_count(1)
                expect(page.locator('[aria-label="Fil d’Ariane"]')).to_contain_text('CMD-RECETTE-01')
                capture(f'sous-dossier-{folder}')
                if width == 390 and folder == 'jaune':
                    page.locator('#upload-doc').click()
                    expect(page.get_by_role('dialog', name='Déposer des documents')).to_be_visible()
                    capture('depot')
                    page.locator('#close-modal').click()
                page.locator('#dj-return-order' if folder == 'rose' else '#dj-folders-back').click()
                expect(page.locator('.dj-folder')).to_have_count(4)
        page.set_viewport_size({'width': 1440, 'height': 960})

    if ocr_available:
        test('Tableaux de bord isolés et cinq résolutions, quatre vues dédiées et retours', verify_folder_tours)

    def uploads():
        open_yellow()
        line('Fiche de prix').get_by_role('button', name='Déposer').click()
        expect(page.get_by_role('dialog', name='Déposer des documents')).to_be_visible()
        capture('depot')
        select_file('fiche-de-prix.pdf', native_pdf('BON DE LIVRAISON\nReference commande : CMD-RECETTE-01'))
        expect(page.locator('#ops-analysis')).to_contain_text('Bon de livraison, alors que la pièce attendue')
        expect(page.locator('#ops-analysis')).to_contain_text('Texte du PDF')
        expect(page.locator('#ops-analysis')).to_contain_text('CMD-RECETTE-01')
        capture('avertissement-type')
        assert save()['identification'] == 'incompatible'
        expect(line('Fiche de prix')).to_contain_text('Type documentaire incompatible')
        board = request.get(path + '/dashboard').json()
        assert board['kpis']['identification_documents'] == 1 and board['launches'][0]['completion']['present_due'] == 0
        line('Fiche de prix').get_by_role('button', name='Déposer une version').click()
        select_file('bl-corrige.pdf', native_pdf('BON DE LIVRAISON\nReference commande : CMD-RECETTE-01\nNouvelle pièce'))
        page.locator('#du-correct').click()
        # Rapprochement signalé (doublon potentiel avec la V1 mal classée) : aucune décision implicite.
        decision = page.locator('#du-relationship-action')
        if decision.count():
            publishes = []
            listener = lambda response: publishes.append(response.url) if response.url.endswith('/publish') else None
            page.on('response', listener)
            page.locator('#ops-upload-form [type=submit]').click()
            expect(page.locator('#ops-upload-form')).to_contain_text('Choisissez comment traiter le rapprochement documentaire proposé.')
            page.wait_for_timeout(400)
            page.remove_listener('response', listener)
            assert not publishes, publishes
            decision.select_option('new_document')
        assert save()['folder'] == 'rose'
        expect(line('Bon de livraison')).to_contain_text('Présent et conforme')
        page.locator('[data-dj-folder="jaune"]').click()
        line('Commande client').get_by_role('button', name='Déposer').click()
        select_file('reseau.pdf', native_pdf('COMMANDE CLIENT\nQuantite : 5 000 pieces'))
        assert save()['identification'] == 'matched'
        expect(line('Commande client')).to_contain_text('Présent et conforme')
        line('Fiche d’emploi').get_by_role('button', name='Déposer').click()
        select_file('emploi.docx', word_document('Fiche d’emploi', 'Quantité : 4 500 pièces'))
        expect(page.locator('#ops-analysis')).to_contain_text('Texte Word')
        assert save()['identification'] == 'matched'
        expect(line('Fiche d’emploi')).to_contain_text('En validation métier')
        line('Étude BE / Excel').get_by_role('button', name='Déposer').click()
        select_file('étude.xlsx', recipe.xlsx_bytes({'A1': 'Étude BE', 'A2': 'Quantité', 'B2': 5000, 'C2': 'pièces', 'D1': '=1+2'}))
        expect(page.locator('#ops-analysis')).to_contain_text('Cellules Excel')
        assert save()['identification'] == 'matched'
        expect(line('Étude BE / Excel')).to_contain_text('Présent et conforme')

    def ocr():
        open_yellow()
        line('Calcul du besoin').get_by_role('button', name='Déposer').click()
        select_file('scan.png', recipe.image_bytes('PNG', 'CALCUL DU BESOIN\nQuantite : 1800 pieces'))
        if ocr_available:
            expect(page.locator('#ops-analysis')).to_contain_text('OCR de l’image', timeout=25000)
            assert save()['identification'] == 'matched'
            expect(line('Calcul du besoin')).to_contain_text('Présent et conforme')
        else:
            expect(page.locator('#ops-analysis')).to_contain_text('OCR image indisponible', timeout=25000)
            assert save()['identification'] == 'to_verify'
            expect(line('Calcul du besoin')).to_contain_text('Déposé — à vérifier')

    def quality():
        rule = request.post(base + '/api/admin/quality-rules', headers=recipe.H, data={
            'name': 'Quantité commande et fiche d’emploi', 'field_key': 'quantite_lancement', 'left_doc_type': 'Commande client',
            'right_doc_type': 'Fiche d’emploi', 'left_folder': 'jaune', 'right_folder': 'jaune', 'tolerance': '0',
        })
        assert rule.status == 201, rule.text()
        open_yellow()
        for title in ('Commande client', 'Fiche d’emploi'):
            line(title).locator('[data-history]').click()
            page.locator('#ops-doc-intake').click()
            page.locator('[data-intake-confirm="quantite"]').click()
            expect(page.locator('[data-confirmed-field="quantite"]')).to_contain_text('Quantité · ')
            page.locator('#close-modal').click()
        page.locator('#dj-tab-controles').click()
        page.locator('[data-dj-module="controles:fiabilite"]').click()
        match = page.locator('.quality-item', has_text='Quantité commande et fiche d’emploi')
        expect(match).to_contain_text('écart de 500 pièce')
        expect(match).to_contain_text('Lecture documentaire confirmée')
        match.scroll_into_view_if_needed()
        capture('coherence')
        match.locator('[data-quality-source]').first.click()
        expect(page.locator('.modal')).to_contain_text('Commande client')
        page.locator('#close-modal').click()
        board = request.get(path + '/dashboard').json()
        assert board['kpis']['inconsistencies'] == 1
        assert all(item['launch_id'] == ident for item in board['activity'])
        other_quality = request.get(base + f'/api/launches/{other}/quality').json()
        assert next(item for item in other_quality['rows'] if item['rule_id'] == rule.json()['id'])['status'] == 'unavailable'

    def multi_and_errors():
        open_yellow()
        page.locator('#upload-doc').click()
        connection = view.context.new_cdp_session(page)
        connection.send('Network.enable')
        connection.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 10,
                        'downloadThroughput': -1, 'uploadThroughput': 5 * 1024 * 1024})
        page.locator('#ops-file').set_input_files([
            {'name': 'ambigu.txt', 'mimeType': 'text/plain', 'buffer': b'BON DE LIVRAISON\nFICHE DE PRIX\nQuantite : 20 pieces\nQuantite : 25 pieces'},
            {'name': 'grand.pdf', 'mimeType': 'application/pdf', 'buffer': native_pdf('DOSSIER TECHNIQUE', 21 * 1024 * 1024)},
        ])
        expect(page.locator('#ops-analysis')).to_contain_text('Type à vérifier')
        page.fill('#ops-type', 'Tests tissu')
        assert save()['identification'] == 'to_verify'
        page.wait_for_function('() => { const bar = document.querySelector("#du-progress"); return bar.value > 0 && bar.value < 99; }')
        capture('transfert-en-cours')
        expect(page.locator('#ops-analysis')).to_contain_text('Analyse automatique limitée à 12 Mo', timeout=25000)
        connection.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 0,
                        'downloadThroughput': -1, 'uploadThroughput': -1})
        connection.detach()
        page.fill('#ops-type', 'Dossier technique client')
        assert save()['latest']['size'] > 20 * 1024 * 1024
        expect(page.locator('#du-files li')).to_have_count(2)
        expect(page.locator('#du-files')).to_contain_text('Déposé · V1')
        page.locator('#cancel-modal').click()
        expect(line('Test tissu')).to_contain_text('Déposé — à vérifier')
        line('Test tissu').get_by_role('button', name='Vérifier le type').click()
        expect(page.locator('.modal')).to_contain_text('Plusieurs valeurs trouvées')
        page.locator('#close-modal').click()
        page.locator('#upload-doc').click()
        select_file('faux.pdf', b'ceci ne constitue pas un PDF')
        expect(page.locator('#du-error')).to_contain_text('ne semble pas être un PDF')
        page.locator('#du-cancel-file').click()
        route = '**/document-uploads'
        expected_network_failure.add(path + '/document-uploads')
        page.route(route, lambda request_route: request_route.abort('connectionreset'), times=1)
        select_file('interrompu.txt', b'Bon de livraison')
        expect(page.locator('#du-error')).to_contain_text('Transfert interrompu')
        page.locator('#du-cancel-file').click()
        select_file('trop-grand.pdf', b'%PDF-1.4\n' + b'x' * (25 * 1024 * 1024))
        expect(page.locator('#du-files')).to_contain_text('Limite de 24 Mo dépassée')
        response = request.post(path + '/document-uploads', headers=recipe.H, multipart={
            'folder': 'jaune', 'file': {'name': 'trop-grand.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-1.4\n' + b'x' * (25 * 1024 * 1024)},
        })
        assert response.status == 413, response.text()
        page.locator('#cancel-modal').click()

    try:
        if ocr_available:
            test('PDF natif, Word et Excel, conflit, correction de classement et compteurs', uploads)
        test('Lecture OCR réelle' if ocr_available else 'OCR réellement indisponible, aucun classement supposé', ocr)
        if ocr_available:
            test('Champs confirmés sur les versions sources, écart de 500 pièces et isolation', quality)
            test('Dépôt multiple, fichier valide >20 Mo, taille limite, ambiguïté et interruption', multi_and_errors)
        unexpected = [item for item in failed if item[0] not in expected_network_failure]
        console = [message for message in view.errors if not any(part in message for part in ('status of 422', 'ERR_CONNECTION_RESET'))]
        qa.check('Espace documentaire Chromium', 'Aucune erreur JavaScript ou requête hors scénarios d’échec', not unexpected and not console, (unexpected, console))
    finally:
        view.close()


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--without-ocr', action='store_true')
    args = parser.parse_args()
    captures = args.output / 'captures'
    captures.mkdir(parents=True, exist_ok=True)
    os.environ['FRAMATEX_UPLOAD_PDF_MIB'] = '24'
    if args.without_ocr:
        empty = args.output.resolve() / 'langues-absentes'
        empty.mkdir(exist_ok=True)
        os.environ['TESSDATA_PREFIX'] = str(empty)
    qa = recipe.QA()
    with recipe.platform_server(qa) as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=browser_executable(), headless=True)
        try:
            workspace(qa, browser, server, captures, not args.without_ocr)
        finally:
            browser.close()
    return recipe.write_report(qa, args.output, 'document-workspace-results.json')


if __name__ == '__main__':
    sys.exit(main())
